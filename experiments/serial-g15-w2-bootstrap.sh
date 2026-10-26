cat > /run/gpu-g1-probe.sh <<'PROBE'
#!/bin/sh
set -eu
test -e /run/network-v4a-backup-verified
test "$(uname -r)" = 7.3.0-rc6-omamobile-oriole-m1
test "$(cat /proc/sys/kernel/modules_disabled)" = 0
test ! -e /run/oriole-stage-continue
test -f /newroot/opt/oriole-experiments/network-v4a/previous-boot-id
test "$(cat /proc/sys/kernel/random/boot_id)" != "$(cat /newroot/opt/oriole-experiments/network-v4a/previous-boot-id)"
for n in $(seq 1 26); do test "$(cat /sys/class/block/sda${n}/ro)" = 1; done
mkdir -p /opt/touch-stage
cp /newroot/opt/oriole-experiments/network-v4a/recovery/*.ko /opt/touch-stage/
test "$(sha256sum /opt/touch-stage/oriole-gpu-g1-read.ko | cut -d ' ' -f1)" = 578295546701d6eac1b2fbd8a961c264258aed3e9ce34bc353dac6986835e082
cat > /run/gpu-g1-watchdog.sh <<'WD'
#!/bin/sh
exec 3>/dev/watchdog0
trap 'printf V >&3; exit 0' TERM INT
i=0
while [ "$i" -lt 60 ]; do printf k >&3; sleep 2; i=$((i+1)); done
while :; do sleep 1; done
WD
sh /run/gpu-g1-watchdog.sh </dev/null >/run/gpu-g1-watchdog.log 2>&1 &
wp=$!
echo "$wp" > /run/gpu-g1-watchdog.pid
sleep 1
test "$(readlink /proc/$wp/fd/3)" = /dev/watchdog0
cat /proc/sys/kernel/modprobe > /run/gpu-g1-modprobe.saved
printf '\n' > /proc/sys/kernel/modprobe
cleanup() {
 trap - EXIT
 if test -d /sys/module/oriole_gpu_supply_read; then rmmod oriole_gpu_supply_read; fi
 cat /run/gpu-g1-modprobe.saved > /proc/sys/kernel/modprobe
 kill -TERM "$wp"
 sleep 3
 test ! -e /proc/$wp/fd/3
 echo GPU_G1_PROBE_CLEANED
}
trap cleanup EXIT
insmod /newroot/usr/lib/modules/7.3.0-rc6-omamobile-oriole-m1/kernel/drivers/mailbox/exynos-mailbox.ko
insmod /newroot/usr/lib/modules/7.3.0-rc6-omamobile-oriole-m1/kernel/drivers/firmware/samsung/acpm-protocol.ko
insmod /opt/touch-stage/oriole_touch_supply_read2.ko
insmod /opt/touch-stage/oriole-gpu-g1-read.ko
dmesg | grep ORIOLE_GPU_G1 > /run/gpu-g1-snapshot.txt
grep -q 'finished ret=0' /run/gpu-g1-snapshot.txt
test "$(grep -c 'speedy=' /run/gpu-g1-snapshot.txt)" = 11
cat /run/gpu-g1-snapshot.txt
echo GPU_G1_READ_PASS
PROBE
cat /proc/kmsg >&2 &
logger=$!
trap 'kill "$logger" 2>/dev/null || true' EXIT
sh /run/gpu-g1-probe.sh > /run/gpu-g1-probe.log 2>&1
rc=$?
cat /run/gpu-g1-probe.log
exit "$rc"
