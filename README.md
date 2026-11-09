# thor-lite-gpu-oc

Raise the GPU top level of an **AYN Thor Lite** (Snapdragon 865) from 670MHz to 905MHz, with a lower voltage
than a naive overclock needs. It is a small Python tool that patches **your own** `boot.img`; no firmware is
included or redistributed.

> **Use at your own risk.** This changes how your device runs its GPU. It can cause crashes, extra heat and
> faster battery drain, and may void your warranty. Not affiliated with AYN. Read the whole page first.

## Tested on
AYN Thor Lite, firmware build `eng.ThorLi.20251223.153027` (Android 13, kernel 4.19.157), bootloader unlocked,
chip revision `20001`. Nothing else has been verified; other builds may differ, and the tool stops if the table
layout isn't what it expects.

Author's results on one unit (3DMark Wild Life Extreme): stock 670MHz scored about 1340; 905MHz at voltage
level 336 scored about 1584 to 1592, with peak draw around 8.7W (vs 9.3W at level 416). Your chip may differ.

## Web version (no Python needed)
Open `docs/index.html` in Chrome, Edge or Firefox, or use the hosted copy on GitHub Pages. It walks through the
whole process and patches your `boot.img` in the browser; the file never leaves your computer. The Python tool
below produces byte-identical output.

## What you need
- Unlocked bootloader (`fastboot getvar unlocked` says `yes`) and Android platform-tools (`adb`, `fastboot`)
- Python 3.8+
- **Know how to reach fastboot with the hardware buttons** before you flash anything

## 1. Dump your boot image (read-only)
1. `adb push scripts/dump_boot.sh /sdcard/`
2. On the device: Settings, the Thor/Handheld settings menu, **Run Script as Root**, pick `dump_boot.sh`
3. `adb shell cat /sdcard/thor_dump_log.txt` should show a size of 100663296 bytes and a checksum
4. `adb pull /sdcard/thor_backup/boot.img .` then run `shasum -a 256 boot.img` and compare with the log

**Keep `boot.img` safe, in two places. It is your way back to stock.**

## 2. Patch it
```
python3 thor_gpu_oc.py boot.img --info
python3 thor_gpu_oc.py boot.img -o boot_gpu905_lv336.img --freq 905 --level 336
```
Defaults are 905MHz and voltage level 336. Values outside what has been verified are refused unless you add
`--force`. If 336 is unstable on your chip, try `--level 384`.

## 3. Test without installing anything
```
adb reboot bootloader
fastboot boot boot_gpu905_lv336.img
adb shell cat /sys/class/kgsl/kgsl-3d0/gpu_available_frequencies
```
The first value should be `905000000`. This loads the image for one boot only; a restart returns to stock.
If the screen stays blank or it hangs, hold the power button about 15 seconds. Run games and a stress test
before going further.

## 4. Flash permanently (optional)
Only after step 3 has been stable for a while.
```
fastboot getvar current-slot          # e.g. a
fastboot flash boot_a boot_gpu905_lv336.img
fastboot reboot
```
Use the slot that `current-slot` reports. **Back to stock:** boot to fastboot and run
`fastboot flash boot_a boot.img` with your original dump. An AYN firmware update will replace the boot image
and remove the overclock; restore stock before updating.

## How it works
The GPU frequency table lives in the device-tree blobs inside `boot.img`. The kernel checks two tables
against each other, so both must change together: `qcom,gpu-pwrlevel@0` (`qcom,gpu-freq`) and
`/soc/gpu-opp-table_v2` (`opp-hz`, plus `opp-microvolt`, which holds the voltage level). Changing only one
makes the GPU driver fail to start and the screen stays blank. The tool patches both in the chip-revision
blobs that have a GPU table, then refreshes the boot header checksum.

## Going further
Higher frequencies are not verified. `--force` lets you experiment, but test with `fastboot boot` only.

## Contributing
Reports of other firmware builds, chip revisions and stable voltage levels are welcome. Please never attach
firmware images, only checksums and the output of `--info`.

MIT licensed.
