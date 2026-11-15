#!/usr/bin/env python3
"""Build the boot image's device tree: board.toml [bootimg] dtb.

The pack stage appends this FDT to the boot image kernel field, so the file has
to exist inside the release's build tree before `unixnu release` reaches pack.
The payload step compiles the same DTS for the kernel's own hardware tree, but
writes it under out/.../device-tree, which is not the path [bootimg] names.

Run by the firmware preflight list; UNIXNU_DEVICE is the device checkout and
the working directory is the build tree.
"""
import os
import subprocess
import sys
from pathlib import Path

DEVICE = Path(os.environ.get("UNIXNU_DEVICE") or Path(__file__).resolve().parent.parent).resolve()
TREE = Path.cwd()
DTS_DIR = DEVICE / "dts"

output = TREE / "build/bluejay/bluejay.dtb"
output.parent.mkdir(parents=True, exist_ok=True)
command = ["dtc", "-I", "dts", "-O", "dtb", "-i", str(DTS_DIR), "-o", str(output),
           str(DTS_DIR / "bluejay.dts")]
try:
    subprocess.run(command, check=True)
except FileNotFoundError:
    sys.exit("dtc not found: install device-tree-compiler (brew install dtc)")
except subprocess.CalledProcessError as error:
    sys.exit(f"dtc failed ({error.returncode}): {' '.join(command)}")

print(f"boot device tree: {output.relative_to(TREE)}")
