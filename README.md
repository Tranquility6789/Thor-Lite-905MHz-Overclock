# EPIC Thor Lite 905MHz Overclock

## [Open the patcher page](https://tranquility6789.github.io/Thor-Lite-905MHz-Overclock/)

Raises the GPU top level of an **AYN Thor Lite** (Snapdragon 865) from 670MHz to 905MHz. It also changes the GPU steps to be more gradual to the 905MHz increase (587-670-780-905). It's a small Python tool that patches **your own** `boot.img`; no firmware is included or redistributed.

> **Use at your own risk.**
> This changes how your device runs its GPU. While this has been tested thoroughly, it will generate extra heat and make your battery drain faster, and may void any potential warranty. Not affiliated with AYN. Read the whole page first pls 

## Tested on
AYN Thor Lite, firmware build `eng.ThorLi.20251223.153027` (Android 13, kernel 4.19.157), update 1.0.0.257, chip revision `20001`. 
Nothing else has been verified; other builds may differ, and the tool stops if the table
layout isn't what it expects. 

Benchmark results (3DMark Wild Life Extreme): 670MHz scored about 1339; 905MHz at voltage
level 336 scored 1600, with peak draw around 8.7W (vs 9.3W at level 416). Your chip may differ.

# Web version (no Python needed)
Use the hosted page: https://tranquility6789.github.io/Thor-Lite-905MHz-Overclock/
It walks through the whole process and patches your `boot.img` in the browser; the file never leaves your computer. The Python tool below produces byte-identical output.

## What you need
- Unlocked bootloader, which should already be the case on your device (`fastboot getvar unlocked` says `yes`) and Android platform-tools (`adb`, `fastboot`)
- Python 3.8+
- **Know how to reach fastboot with the hardware buttons** before you flash anything
- Average intelligence and ability to read and follow instructions

## 1. Dump your boot image (read-only)

**(if you haven't already)** Enable Developer Options. Go to settings (it's in the notification drop down if you can't find it), About handheld console, then go all the way down to the build number and press it 7 times. Go back into settings, then system, then developer options. Enable it and scroll down to USB debugging and enable it. Now plug in your Thor Lite.

1. `adb push scripts/dump_boot.sh /sdcard/`
2. On the device: Go to settings, scroll down to the Thor/Handheld settings menu, scroll down till you see **Run Script as Root**, and pick `dump_boot.sh` (it's in the root directory)
3. `adb shell cat /sdcard/thor_dump_log.txt` should show a size of 100663296 bytes and a checksum
4. `adb pull /sdcard/thor_backup/boot.img .` then run `shasum -a 256 boot.img` and compare with the log

**Keep the original `boot.img` safe, in two places. If anything goes wrong, you can revert your way back to stock with it.**

## 2. Patch it
```
python3 thor_gpu_oc.py boot.img --info
python3 thor_gpu_oc.py boot.img -o boot_gpu_ladder.img --freq 905 --level 336
```
Defaults are 905MHz and voltage level 336. Values outside what has been verified are refused unless you add
`--force`. If 336 happens to be unstable on your chip, try `--level 384`.
Also, `--mode top` gives the old behavior of going from 587 straight to 905.

## 3. Test without installing anything
```
adb reboot bootloader
fastboot boot boot_gpu_ladder.img
adb shell cat /sys/class/kgsl/kgsl-3d0/gpu_available_frequencies
```
The first value should be `905000000`. This loads the image for one boot only; a restart returns to stock.
If the screen stays blank or it hangs, hold the power button about 15 seconds. Run games and a stress test
before going further.

## 4. Flash permanently (optional)
Only after step 3 has been stable for a while.
```
fastboot getvar current-slot          # e.g. a
fastboot flash boot_a boot_gpu_ladder.img
fastboot reboot
```
Use the slot that `current-slot` reports. **Back to stock:** boot to fastboot and run
`fastboot flash boot_a boot.img` with your original dump. An AYN firmware update will replace the boot image
and remove the overclock; make sure to restore stock before updating.

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

## Credits
Inspired by the community's Retroid Pocket 5 GPU overclock (670MHz to 905MHz). Thanks to Gamma and Dexamph, who made the RP5 overclock images, and to the r/retroid tutorial that described them: <https://www.reddit.com/r/retroid/comments/1jjdejr/>

This project does not use or include any of their files. It patches the user's own Thor Lite boot image. Just wanted to credit them for giving me the idea.

MIT licensed.
