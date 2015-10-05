#!/usr/bin/env python
#
# Get some basic information about one or more Virtual Machines
# running in XenServer.
#
# ./vm-info.py        - Get information about all VMs
# ./vm-info.py <uuid> - Get information about a spesific VM
#
# Ex: ./vm-info.py UUID > /tmp/vm-foo.log
# You can also append --debug to the command for verbose output
#
# ---
#
# Author    Anders Evenrud <anders.evenrud@copyleft.no>
# Author    Anders Evenrud <andersevenrud@gmail.com>
# Git       https://github.com/copyleft/xen-vm-info
#
# Docs      http://docs.vmd.citrix.com/XenServer/6.1.0/1.0/en_gb/
# SDK       http://docs.vmd.citrix.com/XenServer/6.1.0/1.0/en_gb/sdk.html
# API       http://docs.vmd.citrix.com/XenServer/6.1.0/1.0/en_gb/api/
#
# ---
#

###############################################################################
# CONFIGURATION
###############################################################################

import XenAPI, sys, os, datetime
from config import *

DEBUG     = False   # '--debug'

###############################################################################
# APPLICATION
###############################################################################

def get_desc(info, key):
    """
      Get the description of an item
      @return String
    """

    try:
      desc = info[key]
      if not desc:
        raise TypeError("no value")
    except:
      desc = "<no description>"

    return desc

def get_confmode(confmode, ntype):
    """
      Get the configuration mode for network
      @return String
    """
    if not confmode or confmode == "None":
      confmode = "Unset %s configuration" % ntype
    elif confmode == "Static":
      confmode = "Static %s configuration" % ntype
    elif confmode == "DHCP":
      confmode = "Dynamic %s configuraion" % ntype

    return confmode

def get_vm_info(session, vm):
    """
      Populate VM iter and return info
      @return dict or None
    """

    record = session.xenapi.VM.get_record(vm)
    if record["is_a_template"] or record["is_control_domain"]:
      return None

    # Host information
    label = session.xenapi.VM.get_name_label(vm)
    vhost = ""

    if HOSTNAME:
      vhost = HOSTNAME
    else:
      if record["power_state"] == "Running":
        vhost_ref = session.xenapi.VM.get_resident_on(vm)
        vhost = session.xenapi.host.get_name_label(vhost_ref) or "<unknown host>"

    #record["VCPUs_params"] = session.xenapi.VM_metrics.get_VCPUs_params(record["metrics"])

    if record["metrics"] != "OpaqueRef:NULL":
      record["metrics"] = session.xenapi.VM_metrics.get_record(record["metrics"])
    else:
      record["metrics"] = None

    if record["guest_metrics"] != "OpaqueRef:NULL":
      record["guest_metrics"] = session.xenapi.VM_guest_metrics.get_record(record["guest_metrics"])
    else:
      record["guest_metrics"] = None

    # Network interfaces
    vifs = session.xenapi.VM.get_VIFs(vm)
    record["VIFs"] = []
    for vif in vifs:
      vrecord = session.xenapi.VIF.get_record(vif)
      if vrecord["metrics"] != "OpaqueRef:NULL":
        try:
          vrecord["metrics"] = session.xenapi.VIF_metrics.get_record(vrecord["metrics"])
        except XenAPI.Failure, e:
          vrecord["metrics"] = None
          # FIXME -- Error handling?!
      else:
        vrecord["metrics"] = None

      vrecord["network"] = session.xenapi.network.get_record(vrecord['network'])

      pifs_ref = vrecord["network"]["PIFs"]
      pifs = []

      for p in pifs_ref:
        precord = session.xenapi.PIF.get_record(p)
        if precord["metrics"] != "OpaqueRef:NULL":
          precord["metrics"] = session.xenapi.PIF_metrics.get_record(precord["metrics"])
        else:
          precord["metrics"] = None
        pifs.append(precord)

      vrecord["network"]["PIFs"] = pifs

      record["VIFs"].append(vrecord)

    # Disk images
    vbds = session.xenapi.VM.get_VBDs(vm)
    record["VBDs"] = []
    for vbd in vbds:
      brecord = session.xenapi.VBD.get_record(vbd)
      if brecord["metrics"] != "OpaqueRef:NULL":
        try:
          brecord["metrics"] = session.xenapi.VBD_metrics.get_record(brecord["metrics"])
        except XenAPI.Failure, e:
          brecord["metrics"] = None
          # FIXME -- Error handling?!
      else:
        brecord["metrics"] = None

      if brecord["VDI"] != "OpaqueRef:NULL":
        vdi = session.xenapi.VDI.get_record(brecord["VDI"])
        #other_config = session.xenapi.VDI.get_other_config(brecord["VDI"])

        if vdi["SR"] != "OpaqueRef:NULL":
          vdi["SR"] = session.xenapi.SR.get_record(vdi["SR"])
        else:
          vdi["SR"] = None

        brecord["VDI"] = vdi
      else:
        brecord["VDI"] = None

      record["VBDs"].append(brecord)

    return {
      'label'   : label,
      'vhost'   : vhost,
      'record'  : record
    }


def main(session, vms):
    """
      Main function to fetch and output information
    """

    # TODO: More DEBUG info
    for vm in vms:
      info = get_vm_info(session, vm)

      if info is not None:
        now = str(datetime.datetime.now()).split(".")[0]
        label = "%s@%s [%s]" % (info["label"], info["vhost"], info["record"]["power_state"])

        print "-------------------------------------------------------------------------------"
        print "Generated on:    %s" % (now)
        print "Virtual Machine: %s" % (label)
        print "                 %s" % (get_desc(info, "name_description"))
        print "                 %s" % (info["record"]["uuid"])
        print "-------------------------------------------------------------------------------"

        mem_min = int(info["record"]["memory_static_min"])
        mem_max = int(info["record"]["memory_static_max"])
        cpu_max = int(info["record"]["VCPUs_max"])
        cpu_int = int(info["record"]["VCPUs_at_startup"])

        if DEBUG:
          print "CPUs: %d (%d on startup)" % (cpu_max, cpu_int)
          print "MEM : %d / %d (min/max static)" % (mem_min, mem_max)
        else:
          print "CPUs: %d maximum" % (cpu_max)
          print "MEM : %d MiB (%d) maximum static" % ((mem_max / 1024 / 1024), mem_max)

        if info["record"]["guest_metrics"] is not None:
          os = info["record"]["guest_metrics"]["os_version"]
          nets = info["record"]["guest_metrics"]["networks"]

          try:
            uname = os["uname"]
          except KeyError, e:
            uname = "<unknown>"

          print "\nOS:   %s - %s" % (os["name"], uname)
          if len(nets):
            for i in nets:
              print "NET:  %s %s" % (i, nets[i])


        for net in info["record"]["VIFs"]:
          print "\nVIF%s: Has MAC Address %s" % (net["device"], net["MAC"])

          print "\n      NET: Bridged on %s" % (net["network"]["bridge"])
          print "           Name: %s" % (net["network"]["name_label"])
          print "           Desc: %s" % (get_desc(net["network"], "name_description"))

          if len(net["network"]["PIFs"]):
            for pif in net["network"]["PIFs"]:
              print "\n      PIF: Using %s with %s as primary config" % (pif["device"] or "<unknown device>", pif["primary_address_type"])

              if DEBUG:
                if pif["metrics"] is not None:
                  x = pif["metrics"]
                  if x["device_id"] and x["vendor_id"]:
                    print "           Card:   %s (%s)" % (x["device_name"], x["vendor_name"])
                  else:
                    print "           Card:   <unknown>"
                  print "           Link:   %smbps duplex=%s" % (x["speed"], x["duplex"])

                print "           MAC:    %s" % (pif["MAC"] or "<none>")

              print "           MTU:    %s" % (pif["MTU"] or "<none>")
              print "           VLAN:   %s" % (pif["VLAN"] or "<none>")
              print "\n           --- %s ---" % (get_confmode(pif["ip_configuration_mode"], "IPv4"))
              print "           IP:     %s" % (pif["IP"] or "<none>")
              print "           MASK:   %s" % (pif["netmask"] or "<none>")
              print "           DNS:    %s" % (pif["DNS"] or "<none>")
              print "           GW:     %s" % (pif["gateway"] or "<none>")
              print "\n           --- %s ---" % (get_confmode(pif["ipv6_configuration_mode"], "IPv6"))
              if len(pif["IPv6"]) and pif["IPv6"][0]: # FIXME: Multiple ?!
                print "           IP:     %s" % (pif["IPv6"][0] or "<none>")
                print "           GW:     %s" % (pif["ipv6_gateway"] or "<none>")
              else:
                print "           IP:     <not available>"
                print "           GW:     <not available>"

        for dsk in info["record"]["VBDs"]:
          print "\nVBD%s: %s - %s (%s)" % (dsk["userdevice"], dsk["type"], dsk["device"] or "<no device>", dsk["mode"])
          if dsk["type"].lower() == "disk":
            sr_size = int(dsk["VDI"]["SR"]["physical_size"])
            vdi_size = int(dsk["VDI"]["virtual_size"])

            print "\n      VDI: %d MiB virtual size (%d)" % ((vdi_size / 1024 / 1024), (vdi_size))
            print "           Name: %s" % (dsk["VDI"]["name_label"])
            print "           Desc: %s" % (get_desc(dsk["VDI"], "name_description"))
            print "           UUID: %s" % (dsk["VDI"]["uuid"])

            print "\n      SR: %d MiB physical size (%d)" % ((sr_size / 1024 / 1024), (sr_size))
            print "           Type: %s" % (dsk["VDI"]["SR"]["type"])
            print "           Name: %s" % (dsk["VDI"]["SR"]["name_label"])
            print "           Desc: %s" % (get_desc(dsk["VDI"]["SR"], "name_description"))
            print "           UUID: %s" % (dsk["VDI"]["SR"]["uuid"])

        print ""

#
# Main
#
if __name__ == "__main__":
    if "--help" in sys.argv:
      from subprocess import call
      call(["head", "-n", str(25), sys.argv[0]])
      sys.exit(0)

    if not USERNAME or not PASSWORD:
      print "Check your config.py!"
      sys.exit(1)

    if sys.argv[len(sys.argv) - 1] == "--debug":
      DEBUG = True

    result = 0
    session = None
    try:
      session = XenAPI.Session(URL)
      session.xenapi.login_with_password(USERNAME, PASSWORD)

      if len(sys.argv) > 1:
        vms = [session.xenapi.VM.get_by_uuid(sys.argv[1])]
      else:
        vms = session.xenapi.VM.get_all()

      main(session, vms)
    except XenAPI.Failure, e:
      result = 1
      print e

    if session is not None:
      session.xenapi.session.logout()

    sys.exit(result)

