#!/usr/bin/env python3
"""TEMPORARY board patch: a post-MMU probe signal that works on GS101.

The UniXNU entry probe's stage 3 proves that the kernel got past its MMU enable
by waiting and then resetting through PSCI SYSTEM_RESET. Measured on the phone
(panel rows from the firmware query): PSCI_VERSION = 0x10001, but
FEATURES(SYSTEM_RESET) and FEATURES(SYSTEM_OFF) both return -1, "not
supported", so stage 3 can never fire here and a frozen panel says nothing
about the MMU.

This replaces SOURCES[3] in the tree's scripts/patch-xnu-entry-probe.py with a
stage 3 that needs no platform support:

  * at that point the kernel still executes at the physical address it was
    booted at (translation has just been switched on over the identity
    mapping), so the cave can switch the MMU off again safely,
  * with translation off, the cave fills the framebuffer through its physical
    address (0xFAC00000, GS101.h:GS101_FRAMEBUFFER_BASE, GS101_FRAMEBUFFER_SIZE
    0x9E3400) with white and halts,
  * a white panel means the CPU ran instructions after `msr SCTLR_EL1` with the
    new tables, i.e. the MMU enable and the identity mapping work,
  * the probe bands left unchanged mean the first fetch after the MMU enable
    faulted: the bootstrap page tables or the boot_args memory fields.

Run from the build tree (the firmware preflight cwd). Idempotent.
"""
from pathlib import Path

TOOL = Path.cwd() / "scripts/patch-xnu-entry-probe.py"
MARK = "# MMU-PROBE bluejay"

if not TOOL.is_file():
    raise SystemExit(f"xnu-mmu-probe: {TOOL} is missing")

text = TOOL.read_text()
if MARK in text:
    print("xnu-mmu-probe: stage 3 already replaced")
    raise SystemExit(0)

ANCHOR = "if __name__ == '__main__':"
if ANCHOR not in text:
    raise SystemExit("xnu-mmu-probe: main guard anchor missing")

STAGE3 = '''# MMU-PROBE bluejay: stage 3 paints the framebuffer with the MMU off and
# halts. The cave runs at the physical address the kernel booted at, so
# switching translation off is safe; a white panel then proves the post-MMU
# path ran, without depending on PSCI (SYSTEM_RESET is unsupported here).
SOURCES[3] = """.text
.global _start
_start:
  mrs  x9, sctlr_el1
  bic  x10, x9, #1
  msr  sctlr_el1, x10
  isb
  movz x11, #0xFAC0, lsl #16
  movz x12, #0xC680
  movk x12, #0x0013, lsl #16
  movn w13, #0
1:
  stp  w13, w13, [x11], #8
  subs x12, x12, #8
  b.hi 1b
2:
  wfe
  b 2b
"""

'''

if len(STAGE3) == 0:
    raise SystemExit("xnu-mmu-probe: empty replacement")

TOOL.write_text(text.replace(ANCHOR, STAGE3 + ANCHOR, 1))
print("xnu-mmu-probe: stage 3 replaced with the MMU-off framebuffer paint")
