#!/usr/bin/env python3
"""Install tuxmanxd/uefi-bluejay into the Mu-Silicium checkout named by UNIXNU_UEFI.

Run by the UniXNU firmware step as a [firmware] preflight entry. The overlay
repository is looked up next to this device repository (../uefi-bluejay) or at
$UNIXNU_UEFI_OVERLAY. The release copies this script into its build tree, so the
device root comes from $UNIXNU_DEVICE when the release sets it.
"""
import os
import subprocess
import sys
from pathlib import Path

DEVICE = Path(os.environ.get("UNIXNU_DEVICE") or Path(__file__).resolve().parent.parent).resolve()
UEFI = Path(os.environ["UNIXNU_UEFI"]).resolve()
OVERLAY = Path(os.environ.get("UNIXNU_UEFI_OVERLAY", DEVICE.parent / "uefi-bluejay")).resolve()

apply = OVERLAY / "scripts/apply.sh"
if not apply.is_file():
    sys.exit(f"uefi-bluejay not found at {OVERLAY}: clone tuxmanxd/uefi-bluejay next to this "
             f"repository or set UNIXNU_UEFI_OVERLAY")

subprocess.run(["bash", str(apply), str(UEFI), "copy"], check=True)
