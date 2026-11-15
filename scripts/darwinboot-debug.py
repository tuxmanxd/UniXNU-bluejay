#!/usr/bin/env python3
"""TEMPORARY: make DarwinBoot's failure path stay on the panel.

The boot menu reports only the EFI status of a failed xnu entry, and
DarwinBoot's own diagnostics go to the console, which the menu repaints
immediately. This patch draws the entry conditions and the failing stage on
the framebuffer and halts, so a photo of the screen names the exact lookup
that failed.

Remove this script from [firmware] preflight once the failure is understood.
Run from the build tree (the firmware preflight cwd).
"""
import sys
from pathlib import Path

TREE = Path.cwd()
SRC = TREE / "drivers/DarwinBoot/DarwinBootPkg/Driver/DarwinBoot.c"
if not SRC.is_file():
    sys.exit(f"darwinboot-debug: {SRC} is missing")

text = SRC.read_text()
if "mDbgStage" in text:
    print("darwinboot-debug: already patched")
    sys.exit(0)

MARKS = [
    ("  Status = gBS->HandleProtocol (Request->Volume, &gEfiSimpleFileSystemProtocolGuid, (VOID **)&Fs);", "volume"),
    ("  Status = ReadFile (Root, Request->KernelPath, KERNEL_LIMIT, &Image, &ImageSize);", "read-kernel"),
    ("  Status = ParseKernel (Image, ImageSize, &Kernel);", "parse-kernel"),
    ("  Status = ReadFile (Root, TreePath, SIZE_16MB, &Tree, &TreeSize);", "read-adt"),
    ("  if (!AdtNode (Tree, TreeSize, &Offset, 0, 3,", "adt"),
    ("  Status = ReadBootVideo (Video);", "video"),
    ("  if (ExcludedOffset == MAX_UINTN) {", "window"),
    ("  Status = GetMap (&Map, &Capacity, &MapSize, &Key, &Stride);", "map"),
]

STATIC = "STATIC EFI_HANDLE  mImage;"
if STATIC not in text:
    sys.exit("darwinboot-debug: mImage anchor missing")
text = text.replace(STATIC, STATIC + '\nSTATIC CONST CHAR8  *mDbgStage = "start";', 1)

# Reached only when Boot() is entered at all: its absence means the loader
# protocol was never found, or the entry conditions below rejected the boot.
ENTER = "  (VOID)This;"
if ENTER not in text:
    sys.exit("darwinboot-debug: Boot() entry anchor missing")
text = text.replace(ENTER, ENTER + '''
  {
    CHAR16  DbEntry[96];
    UnicodeSPrint (DbEntry, sizeof (DbEntry), L"BOOT ENTERED EL=%lx DT=%lx KX=%lx",
                   DarwinCurrentEl (), (UINT64)(UINTN)Request->DeviceTree, (UINT64)Request->KextCount);
    DiagDraw (DbEntry, 9);
  }''', 1)

# The early rejection in Boot(): draw its inputs before the menu repaints.
EARLY = """    Print (L"DARWINBOOT: unsupported inputs or exception level; firmware retained\\n");
    return EFI_UNSUPPORTED;"""
if EARLY not in text:
    sys.exit("darwinboot-debug: early-rejection anchor missing")
text = text.replace(EARLY, """    Print (L"DARWINBOOT: unsupported inputs or exception level; firmware retained\\n");
    {
      CHAR16  DbEarly[96];
      UnicodeSPrint (DbEarly, sizeof (DbEarly), L"EARLY CHECK FAILED EL=%lx DT=%lx KX=%lx",
                     DarwinCurrentEl (), (UINT64)(UINTN)Request->DeviceTree, (UINT64)Request->KextCount);
      DiagDraw (DbEarly, 0);
      CpuDeadLoop ();
    }
    return EFI_UNSUPPORTED;""", 1)

for anchor, stage in MARKS:
    if anchor not in text:
        sys.exit(f"darwinboot-debug: anchor missing for {stage}")
    text = text.replace(anchor, f'  mDbgStage = "{stage}";\n' + anchor, 1)

FAIL = "Fail:\n  if (Root != NULL) { Root->Close (Root); }"
if FAIL not in text:
    sys.exit("darwinboot-debug: Fail anchor missing")
text = text.replace(FAIL, '''Fail:
  {
    CHAR16  DbLine[96];
    CHAR16  DbPath[96];
    UnicodeSPrint (DbLine, sizeof (DbLine), L"FAIL %r AT %a", Status, mDbgStage);
    DiagDraw (DbLine, 0);
    UnicodeSPrint (DbPath, sizeof (DbPath), L"%s", (Request->KernelPath != NULL) ? Request->KernelPath : L"(no path)");
    DiagDraw (DbPath, 1);
    CpuDeadLoop ();
  }
  if (Root != NULL) { Root->Close (Root); }''', 1)

SRC.write_text(text)
print("darwinboot-debug: entry conditions and failure stage drawn to the framebuffer, then halt")
