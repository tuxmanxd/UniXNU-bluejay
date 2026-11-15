#!/usr/bin/env python3
"""Build the boot image's device tree: board.toml [bootimg] dtb.

The pack stage reads this file as `<tree>/<bootimg>.dtb` and appends it to the
boot image kernel field. The payload step has already compiled the board's DTS
to `<out>/<device>/<profile>/<config>/device-tree/hardware.dtb` (the same DTS,
with the SoC include directory resolved), so the firmware preflight copies it.

Run from the build tree; UNIXNU_DEVICE is the device checkout. If the payload
tree is absent (a bare `unixnu bootimg` run), the DTS is compiled directly.
"""
import os
import shutil
import subprocess
import sys
from pathlib import Path

DEVICE = Path(os.environ.get("UNIXNU_DEVICE") or Path(__file__).resolve().parent.parent).resolve()
TREE = Path.cwd()
DTS_DIR = DEVICE / "dts"

output = TREE / "build/bluejay/bluejay.dtb"
output.parent.mkdir(parents=True, exist_ok=True)

hardware = TREE.parent / "device-tree/hardware.dtb"
if hardware.is_file():
    shutil.copyfile(hardware, output)
    print(f"boot device tree: {output.relative_to(TREE)} (from {hardware.name})")
    sys.exit(0)

# No payload tree: compile the same source. gs101.dtsi lives in the SoC feed
# checkout under out/feeds; find it the way the release lays it out.
includes = [DTS_DIR]
for parent in TREE.parents:
    feeds = parent / "feeds"
    if feeds.is_dir():
        includes += sorted(path for path in feeds.glob("UniXNU-gs101-common-*/dts") if path.is_dir())
        break

command = ["dtc", "-I", "dts", "-O", "dtb", "-o", str(output)]
for directory in includes:
    command += ["-i", str(directory)]
command.append(str(DTS_DIR / "bluejay.dts"))
try:
    subprocess.run(command, check=True)
except FileNotFoundError:
    sys.exit("dtc not found: install device-tree-compiler (brew install dtc)")
except subprocess.CalledProcessError as error:
    sys.exit(f"dtc failed ({error.returncode}): {' '.join(command)}")

print(f"boot device tree: {output.relative_to(TREE)}")
