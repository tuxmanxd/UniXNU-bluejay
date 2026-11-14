# UniXNU bluejay (Google Pixel 6a)

UniXNU device repository for the Google Pixel 6a (bluejay, Tensor G1 / GS101).
It describes one board, selects shared GS101 and ARM64 support, and packages
the OS for the phone's `userdata` partition.

**Status: scaffold, never built or booted with UniXNU.** The values are taken
from the [pixelios-kernel](https://github.com/PixOS-Project/pixelios-kernel)
research port, which boots XNU 8796 with the iOS 16.7 userland on this phone
using a bare-metal shim. What that port proves about the hardware is reusable;
its shim and patch stack are not UniXNU components.

## What is real here

| Input | Value | Source |
| --- | --- | --- |
| DRAM handed to XNU | `0x880000000` + `0x100000000` | `board.json`, measured |
| Low bank | `0x80000000` + 2 GiB, carve-outs, not handed over | `board.json` notes |
| Framebuffer | `0xfac00000`, `0x9e3400`, 1080x2400, stride 4320 | `board.json`, measured |
| `userdata` GPT | `0x22F1E6`..`0x1DC03FA`, 4096-byte LBAs | UFS GPT capture |
| UFS | HCI `0x14700000`, UNIPRO `0x14780000`, PHY `0x14704000` | `ufsinit.c` |
| GIC / timer | GICD `0x10400000`, GICR `0x10440000`, 24.576 MHz | research notes |
| Boot image | base 0, kernel 0x8000, tags 0x100, page 4096 | `shim/build.sh` |
| ADT chip id | `0x8015` | `tools/mkadt.py` |

## What is missing

- No `uefi-bluejay` Mu-Silicium platform: `[firmware]` paths are a target layout.
- No GS101 UFS, FTM5 touch, PMIC or DWC3 component; those areas are `planned`.
- UniXNU ships no iPhone/iOS 16.7 profile. This repository selects the oldest
  shipped profile, `ipados-17.7.11-21H461`, as a placeholder.
- No IPSW pin, firmware hashes or `unixnu.lock` yet.

## Build

```sh
git clone https://github.com/UniXNU/UniXNU ../UniXNU
cp local.toml.example local.toml        # points the gs101 source at the sibling checkout
../UniXNU/unixnu defconfig bluejay_defconfig -D .
../UniXNU/unixnu fetch -D .
../UniXNU/unixnu status --json -D .
scripts/package.sh --check --os 17
```

The sibling SoC repository is [UniXNU-gs101-common](../UniXNU-gs101-common).
Hardware provenance and the pixelios mapping are in
[docs/PIXELIOS-MAP.md](docs/PIXELIOS-MAP.md).

## Required reading

- [Port a device](https://unixnu.com/porting/steps)
- [Device repository](https://unixnu.com/porting/device-repository)
- [Device tree](https://unixnu.com/porting/device-tree)
- [Component catalog](https://unixnu.com/reference/components)
- [Porting records](https://unixnu.com/porting/records)

## Licensing

Repository content is BSD-2-Clause-Patent (see `LICENSE` when added). Hardware
facts are attributed to pixelios-kernel, which is MIT, and to the Google GS101
vendor tree. XNU patches, when added, remain under Apple's APSL 2.0.
