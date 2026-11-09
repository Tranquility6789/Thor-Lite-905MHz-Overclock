#!/system/bin/sh
# Run on the Thor Lite via Settings -> (Thor/Handheld settings) -> "Run Script as Root".
# Read-only: copies the ACTIVE slot's boot partition to /sdcard/thor_backup/boot.img.
# One command per line on purpose: the script runner does not handle multi-line blocks or loops.
echo "dump started" > /sdcard/thor_dump_log.txt
mkdir -p /sdcard/thor_backup
getprop ro.build.fingerprint >> /sdcard/thor_dump_log.txt
getprop ro.boot.slot_suffix >> /sdcard/thor_dump_log.txt
dd if=/dev/block/by-name/boot$(getprop ro.boot.slot_suffix) of=/sdcard/thor_backup/boot.img bs=1048576 >> /sdcard/thor_dump_log.txt 2>&1
sha256sum /sdcard/thor_backup/boot.img >> /sdcard/thor_dump_log.txt 2>&1
ls -l /sdcard/thor_backup >> /sdcard/thor_dump_log.txt 2>&1
echo "dump finished" >> /sdcard/thor_dump_log.txt
