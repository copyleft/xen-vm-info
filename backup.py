#!/usr/bin/env python
#
# Write backup and VM information of all VHDs
# in a XenServer StoragePool
#
# Mainly used in cron-jobs
#
# ./backup.py        - Run as normal
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

###############################################################################
# APPLICATION
###############################################################################

def get_sr_info(session, sr):
    """
      Populate StorageRecord iter and return info
      @return dict or None
    """
    record = session.xenapi.SR.get_record(sr)
    if record:
      vdis = []
      for r in record["VDIs"]:
        vdi = session.xenapi.VDI.get_record(r)
        if vdi:
          vbds = []
          for b in vdi["VBDs"]:
            vbd = session.xenapi.VBD.get_record(b)
            if vbd:
              vbds.append(vbd)

          vdi["VBDs"] = vbds

          vdis.append(vdi)

      record["VDIs"] = vdis

    return {
      'record' : record
    }

def main(session, srs):
    """
      Main function to fetch and output information
    """
    path = os.path.dirname(os.path.abspath(__file__))

    result = {}
    for sr in srs:
      info = get_sr_info(session, sr)
      fstype = info["record"]["type"].lower()
      if fstype in FS_LOOKUP:
        sr_uuid = info["record"]["uuid"]

        #DEBUG PATH:
        #cmd = "mkdir %s/%s" % (OUTPATH, sr_uuid)
        #os.system(cmd)

        for vdi_ref in info["record"]["VDIs"]:
          disk_uuid = vdi_ref["uuid"]

          #vdi_copy = session.xenapi.VDI.snapshot(vdi_ref)

          for vbd_ref in vdi_ref["VBDs"]:
            vm_ref = vbd_ref["VM"]
            vm = session.xenapi.VM.get_record(vm_ref)
            vm_uuid = vm["uuid"]

            #DEBUG PATH:
            #cmd = "touch %s/%s/%s.vhd" % (OUTPATH, sr_uuid, disk_uuid)
            #os.system(cmd)

            cmd = "%s/vm-info.py %s > %s/%s/%s.xenserver_info" % (path, vm_uuid, OUTPATH, sr_uuid, disk_uuid)
            os.system(cmd)

            print "Wrote SR:%s VDI:%s VM:%s <%s>" % (sr_uuid, disk_uuid, vm_uuid, fstype)

#
# Main
#
if __name__ == "__main__":
    if "--help" in sys.argv:
      from subprocess import call
      call(["head", "-n", str(23), sys.argv[0]])
      sys.exit(0)

    if not USERNAME or not PASSWORD:
      print "Check your config.py!"
      sys.exit(1)

    result = 0
    session = None
    try:
      session = XenAPI.Session(URL)
      session.xenapi.login_with_password(USERNAME, PASSWORD)

      srs = session.xenapi.SR.get_all()
      main(session, srs)

    except XenAPI.Failure, e:
      result = 1
      print e

    if session is not None:
      session.xenapi.session.logout()

    sys.exit(result)


