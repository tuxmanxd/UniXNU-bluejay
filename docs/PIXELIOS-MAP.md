# pixelios-kernel to UniXNU mapping

What was taken from [pixelios-kernel](https://github.com/PixOS-Project/pixelios-kernel)
(mit, research port) and where it lands in this UniXNU tree. Nothing here is
copied code unless stated; the reusable output of the pixelios port is measured
hardware facts and sequences.

## Layers

| pixelios | UniXNU layer / artifact | Reused | Not reused |
| --- | --- | --- | --- |
| `shim/` (bare-metal EL2 loader) | 1 boot image, 2 firmware | Android boot image geometry (`shim/build.sh`), framebuffer and memory handoff facts | The loader itself; UniXNU starts from UEFI, not `fastboot boot` |
| `shim/ufs*.c`, `soc/google/gs101/shim/ufsinit.c` | storage component (missing) | Cold re-init, vendor HCI/UNIPRO/PHY windows, HS-G4 sequence | Bare-metal MMIO code; needs an XNU-side driver |
| `shim/loader.c`, `mmu.c`, `payload.c` | DarwinBoot | `boot_args` and payload layout observations | The hand-written jump into XNU |
| `shim/touch*.c`, `ftm5_host_test.c` | input component (missing) | FTM5 protocol, USI setup, pins, rails | Code |
| `shim/usb*.c` | USB component (missing) | DWC3 identity, event-buffer behaviour, device-mode proof | Code |
| `shim/wlan*.c`, `soc/google/gs101/wlan_seq.json` | network component (missing) | Cited PCIe/PMU/CMU/pin sequences | Code |
| `shim/gpu*.c`, `shim/acpm.c` | GPU, power (missing) | Rail and power-domain sequences | Code; no Mali component in UniXNU |
| `xnu/patches/` (137 files, XNU 8796) | `patches/xnu/series` | The list of behaviours the port needed | The patches: different XNU revision and UniXNU patch order |
| `tools/mkadt.py` | `[payload.adt]`, ADT generator | Chip id `0x8015`, owned memory, button names | The generator; UniXNU has a common ADT path |
| `tools/mkpayload.py` | `[payload]`, DarwinBoot | Payload fields, command line limits | The emitter |
| `device/google/bluejay/board.json` | `board.toml`, `dts/bluejay.dts` | DRAM, framebuffer, GPT, keys, touch, USB DMA range | Board JSON format |
| `soc/google/gs101/soc.json` | `UniXNU-gs101-common/dts/gs101.dtsi`, `soc.toml` | GIC, timer, UFS, USB, UART, WLAN and GPU bases | JSON format |
| `qrlog/`, `tools/qr*`, `shim/ramlog.c`, `pstore.c` | diagnostics area | The log-transport designs and the encoder constraint (no SHA3) | Code |
| `docs/research/*`, `docs/reviews/*` | citations in `porting.toml` | Measurements, vendor-source confirmations, safety constraints | - |

## Facts that drive the configuration

1. XNU only gets the high 4 GiB (`0x880000000`); the low bank is carved up by
   ABL, including a 16 MiB USB DMA region whose event buffer moves between boots.
2. The framebuffer at `0xfac00000` is in the low bank and needs a no-map
   reservation but does not fragment owned memory.
3. `userdata` is a fixed GPT entry; the root lives there read-only.
4. UFS needs a cold re-init and an HS-G4 gear change before it is usable.
5. Touch works on hardware under pixelios, so the input wiring is proven even
   though the driver is not ported.
6. The port has no Apple PMGR/SEP, hence `vmm-present` and `kernel-ctrr-to-be-enabled = 0`.

## Deliberate differences

- OS profile: UniXNU ships no iOS 16.7 profile, so the scaffold selects
  `ipados-17.7.11-21H461`. A real port needs an iPhone profile upstream.
- XNU version: pixelios pins 8796; UniXNU pins a newer kernel with its own
  ordered series. The port must re-derive each patch as a component setting.
- Firmware: pixelios has no UEFI; `uefi-bluejay` must be created.
