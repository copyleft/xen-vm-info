#!/usr/bin/env python
#
# Config file for 'vm-info.py' and 'backup.py'
#
# ---
#
# Author    Anders Evenrud <anders.evenrud@copyleft.no>
# Author    Anders Evenrud <andersevenrud@gmail.com>
# Git       https://github.com/copyleft/xen-vm-info
#
# ---
#

URL       = "https://localhost"

#FS_LOOKUP = ["nfs", "ext4", "ext", "LO"]
FS_LOOKUP = ["nfs", "ext4", "ext"]

USERNAME  = "root"
HOSTNAME  = "xs01.local.lan"
PASSWORD  = "secret"
#OUTPATH   = "/var/run/sr-info"
OUTPATH   = "/var/run/sr-mount"
