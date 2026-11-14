# Device agent guide (bluejay)

This repository owns the board DTS, peripheral wiring, component selections,
firmware inputs, partition layout and packaging for the Pixel 6a.

## Read first

| Task | Required reading |
| --- | --- |
| Every change | [Porting](https://unixnu.com/porting/), [device repository](https://unixnu.com/porting/device-repository), UniXNU `components.toml` |
| Hardware | [Device tree](https://unixnu.com/porting/device-tree), [SoC support](https://unixnu.com/porting/soc-support), `UniXNU-gs101-common` |
| Kernel | [Source and patches](https://unixnu.com/xnu/source-and-patches), selected OS profile |
| Verification | [Building](https://unixnu.com/building), [bring-up](https://unixnu.com/porting/bring-up) |

## Rules

- `board.toml`, `porting.toml`, `feeds.toml` and `dts/` are the source of truth.
  Keep the device identity identical in `board.toml` and `porting.toml`.
- Every hardware value needs a citation: a pixelios path, a pixelios log, a
  vendor DTS line, or a measurement from this phone. Never invent a register,
  interrupt, hash or partition bound.
- Status stays honest. `planned` until code exists, `implemented` only with a
  source reference, `device-verified` only with a command, a full commit and a
  log from this phone.
- Shared GS101 resources belong in `UniXNU-gs101-common`; board differences
  belong here.
- `scripts/package.sh` is byte-identical to the UniXNU template. Never edit it.
- Do not add a component to `[components]` before its repository exists and
  the record covers it.

## Commands

```sh
../UniXNU/unixnu defconfig bluejay_defconfig -D .
../UniXNU/unixnu status --json -D .
scripts/package.sh --check --os 17
python3 ../UniXNU/scripts/porting-record.py check --device .
```
