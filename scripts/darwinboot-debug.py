#!/usr/bin/env python3
"""TEMPORARY board patch: let DarwinBoot boot from a firmware running at EL2.

Mu-Silicium's SEC takes the exception level ABL hands it (EL1_OR_EL2 ->
SetupExceptionLevel2 on Tensor), so the whole firmware, DarwinBoot included,
runs at EL2. DarwinBoot rejects anything but EL1, and it hands the kernel off
with `br x1` -- still at EL2 -- which iPadOS 17 XNU does not accept.

This patch does three things, all in the tree the firmware build uses:

  * accepts EL2 at the entry check instead of rejecting it (drawing and
    halting if a device tree or kext list is what the check rejects),
  * drops to EL1h inside DarwinEnter, at the last moment, with the MMU off
    and interrupts masked (HCR_EL2.RW=1, CPTR_EL2=0, CNTHCTL_EL2=3,
    CNTVOFF_EL2=0, SPSR_EL2=EL1h|DAIF, ELR_EL2=entry),
  * draws the entry conditions and the failing stage on the framebuffer and
    halts, so a photo of the panel still names a lookup that fails.

Remove it once the port carries these changes properly.
Run from the build tree (the firmware preflight cwd).
"""
import sys
from pathlib import Path

TREE = Path.cwd()
SRC = TREE / "drivers/DarwinBoot/DarwinBootPkg/Driver/DarwinBoot.c"
ASM = TREE / "drivers/DarwinBoot/DarwinBootPkg/Driver/Entry.S"
for path in (SRC, ASM):
    if not path.is_file():
        sys.exit(f"darwinboot-debug: {path} is missing")

text = SRC.read_text()
asm = ASM.read_text()

# ---------------------------------------------------------------------------
# 1. Accept EL2: the firmware runs there, see the module docstring.
# ---------------------------------------------------------------------------
OLD_EL = """  if ((Request->KextCount != 0) || (Request->DeviceTree != NULL) || (Request->DeviceTreeSize != 0) ||
      (DarwinCurrentEl () != 4)) {"""
NEW_EL = """  if ((Request->KextCount != 0) || (Request->DeviceTree != NULL) || (Request->DeviceTreeSize != 0)) {"""
if OLD_EL in text:
    text = text.replace(OLD_EL, NEW_EL, 1)
elif NEW_EL not in text:
    sys.exit("darwinboot-debug: early-rejection anchor missing")

REJECT = '    Print (L"DARWINBOOT: unsupported inputs or exception level; firmware retained\\n");\n    return EFI_UNSUPPORTED;'
if "REJECTED EL=" not in text:
    if REJECT not in text:
        sys.exit("darwinboot-debug: early-rejection body anchor missing")
    text = text.replace(REJECT, '''    Print (L"DARWINBOOT: unsupported inputs or exception level; firmware retained\\n");
    {
      CHAR16  DbEarly[96];
      UnicodeSPrint (DbEarly, sizeof (DbEarly), L"REJECTED EL=%lx DT=%lx KX=%lx",
                     DarwinCurrentEl (), (UINT64)(UINTN)Request->DeviceTree, (UINT64)Request->KextCount);
      DiagDraw (DbEarly, 0);
      CpuDeadLoop ();
    }
    return EFI_UNSUPPORTED;''', 1)

# ---------------------------------------------------------------------------
# 2. Drop to EL1 in DarwinEnter. x0 (boot args), x2, x3 and x5 survive; the
#    kernel is branched to through ELR_EL2 instead of `br x1`.
# ---------------------------------------------------------------------------
BR = "  br x1\n"
DROP = """  //
  // The firmware runs at EL2; the kernel is entered at EL1. Drop one level
  // here, at the last moment: MMU off, caches off, interrupts masked.
  //
  mrs x9, CurrentEL
  cmp x9, #8
  b.ne 4f
  mov x9, #0x80000000            // HCR_EL2.RW: EL1 is AArch64
  msr hcr_el2, x9
  msr cptr_el2, xzr              // no EL1 traps on FP/SIMD access
  mov x9, #3                     // EL1 may use the physical counter/timer
  msr cnthctl_el2, x9
  msr cntvoff_el2, xzr
  mov x9, #0x3c5                 // EL1h, DAIF masked
  msr spsr_el2, x9
  msr elr_el2, x1
  mov x9, sp
  msr sp_el1, x9
  isb
  eret
4:
  br x1
"""
if DROP not in asm:
    if asm.count(BR) != 1:
        sys.exit("darwinboot-debug: DarwinEnter branch anchor missing")
    asm = asm.replace(BR, DROP, 1)

# ---------------------------------------------------------------------------
# 3. Diagnostics: entry conditions at Boot() and the failing stage, halted.
# ---------------------------------------------------------------------------
STATIC = "STATIC EFI_HANDLE  mImage;"
if "mDbgStage" not in text:
    if STATIC not in text:
        sys.exit("darwinboot-debug: mImage anchor missing")
    text = text.replace(STATIC, STATIC + '\nSTATIC CONST CHAR8  *mDbgStage = "start";', 1)

ENTER = "  (VOID)This;"
if "BOOT ENTERED" not in text:
    if ENTER not in text:
        sys.exit("darwinboot-debug: Boot() entry anchor missing")
    text = text.replace(ENTER, ENTER + '''
  {
    CHAR16  DbEntry[96];
    UnicodeSPrint (DbEntry, sizeof (DbEntry), L"BOOT ENTERED EL=%lx DT=%lx KX=%lx",
                   DarwinCurrentEl (), (UINT64)(UINTN)Request->DeviceTree, (UINT64)Request->KextCount);
    DiagDraw (DbEntry, 9);
  }''', 1)

MARKS = [
    ("  Status = gBS->HandleProtocol (Request->Volume, &gEfiSimpleFileSystemProtocolGuid, (VOID **)&Fs);", "volume"),
    ("  Status = ReadFile (Root, Request->KernelPath, KERNEL_LIMIT, &Image, &ImageSize);", "read-kernel"),
    ("  Status = ParseKernel (Image, ImageSize, &Kernel);", "parse-kernel"),
    ("  Status = ReadFile (Root, TreePath, SIZE_16MB, &Tree, &TreeSize);", "read-adt"),
    ("  Status = ReadBootVideo (Video);", "video"),
    ("  if (ExcludedOffset == MAX_UINTN) {", "window"),
    ("  Status = GetMap (&Map, &Capacity, &MapSize, &Key, &Stride);", "map"),
]
for anchor, stage in MARKS:
    if anchor not in text:
        sys.exit(f"darwinboot-debug: anchor missing for {stage}")
    if f'mDbgStage = "{stage}"' not in text:
        text = text.replace(anchor, f'  mDbgStage = "{stage}";\n' + anchor, 1)

FAIL = "Fail:\n  if (Root != NULL) { Root->Close (Root); }"
if "FAIL %r AT %a" not in text:
    if FAIL not in text:
        sys.exit("darwinboot-debug: Fail anchor missing")
    text = text.replace(FAIL, '''Fail:
  {
    CHAR16  DbLine[96];
    CHAR16  DbPath[96];
    UnicodeSPrint (DbLine, sizeof (DbLine), L"FAIL %r AT %a", Status, mDbgStage);
    DiagDraw (DbLine, 18);
    UnicodeSPrint (DbPath, sizeof (DbPath), L"%s", (Request->KernelPath != NULL) ? Request->KernelPath : L"(no path)");
    DiagDraw (DbPath, 19);
    CpuDeadLoop ();
  }
  if (Root != NULL) { Root->Close (Root); }''', 1)

SRC.write_text(text)
ASM.write_text(asm)
print("darwinboot-debug: EL2 accepted, EL1h handoff in DarwinEnter, failure stage drawn then halted")
