#!/usr/bin/env python3
"""Stage the boot image kernel field: board.toml [bootimg] dtb.

Tensor ABL refuses a boot image whose ramdisk is larger than 32 MiB (measured;
see uefi-bluejay docs/EVIDENCE.md), and the prelinked kernel alone is 49.5 MiB,
so this board cannot carry the payload as the ramdisk. The payload travels in
the kernel field instead:

    shim | UEFI FD (2 MiB) | 4 KiB FDT envelope | FAT payload volume

BootShim.S (patched by uefi-bluejay scripts/apply.sh) copies the volume from
`_Payload + FD_SIZE + 0x1000` to its reserved window at 0x880000000, and the
firmware's PayloadBlockIo publishes it. The pack stage only appends ONE file to
the kernel field ([bootimg] dtb) and validates it as an FDT: magic at 0, total
size at 4 equal to the file length. The envelope satisfies that check; nothing
parses it as a tree (the firmware gets ABL's own FDT in x0).

The payload itself is the real `payload/payload.img` from the payload step. It
is preserved as `payload/payload.full.img` because the pack stage would
otherwise place it in the ramdisk; `payload/payload.img` is left as an empty
file so the boot image has no ramdisk.

The payload step runs before the firmware step, so this preflight (a firmware
preflight in board.toml) sees the finished volume.

Run from the build tree; UNIXNU_DEVICE is the device checkout.
"""
import os
import shutil
import struct
import sys
from pathlib import Path

DEVICE = Path(os.environ.get("UNIXNU_DEVICE") or Path(__file__).resolve().parent.parent).resolve()
TREE = Path.cwd()
WORK = TREE.parent

output = TREE / "build/bluejay/bluejay.dtb"
output.parent.mkdir(parents=True, exist_ok=True)

payload = WORK / "payload/payload.img"
full = WORK / "payload/payload.full.img"

if payload.is_file() and payload.stat().st_size:
    shutil.copyfile(payload, full)
    payload.write_bytes(b"")
    print(f"payload staged: {full.relative_to(WORK)} ({full.stat().st_size} bytes), ramdisk left empty")
elif full.is_file():
    print(f"payload already staged: {full.relative_to(WORK)} ({full.stat().st_size} bytes)")
else:
    sys.exit(f"payload volume missing: run the payload step first ({payload} is absent or empty)")

volume = full.read_bytes()
envelope = bytearray(0x1000)
# FDT header fields the pack stage checks: magic and total size. The offsets
# point at the empty reservation map and structure area inside this page; the
# volume follows at 0x1000.
struct.pack_into(
    ">IIIIIIIIII", envelope, 0,
    0xD00DFEED, 0x1000 + len(volume), 0x38, 0x38, 0x28, 17, 16, 0, 0, 0,
)
output.write_bytes(bytes(envelope) + volume)
print(f"boot kernel field: {output.relative_to(TREE)} "
      f"(envelope 0x1000 + volume {len(volume)} = {output.stat().st_size} bytes)")
