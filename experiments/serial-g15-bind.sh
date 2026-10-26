cat > /run/gpu-g9-fresh-probe.sh <<'PROBE'
#!/bin/sh
set -eu
test -e /run/g15-backup-verified
test "$(cat /proc/1/comm)" = init
test "$(cat /proc/sys/kernel/modules_disabled)" = 0
grep -q GPU_G1_PROBE_CLEANED /run/gpu-g1-probe.log
test ! -d /sys/module/panfrost
test ! -d /sys/module/clk_acpm
archive=/newroot/var/tmp/oriole-g10/transfer/chunk-045
test "$(sha256sum "$archive" | cut -d ' ' -f1)" = 0c2ad847851e59b31123c3327dc76d2b88458c899b9eca0375138bd65004535b
tar -xf "$archive" -C /opt/touch-stage
test "$(sha256sum /opt/touch-stage/oriole-gpu-g9-core-supply.ko | cut -d ' ' -f1)" = 1851a937db42b12192533388de7b993a19d63507cb3824fd3ab87ddf72ed62f0
cp /newroot/var/tmp/oriole-g10/transfer/chunk-044 /opt/touch-stage/panfrost-g15.ko
test "$(sha256sum /opt/touch-stage/panfrost-g15.ko | cut -d ' ' -f1)" = 7dbb248923672bda34ef35a0d822498d16bb09d1029dde9ab8aa13c99ff8d95c
test "$(sha256sum /opt/touch-stage/oriole-gpu-g6-overlay.ko | cut -d ' ' -f1)" = b8e4d9dbaa016d5f0c33f781ca9977aceeb84246c21676b53cc554a330fea669
sh /run/gpu-g1-watchdog.sh </dev/null >/run/gpu-g9-bind-watchdog.log 2>&1 &
wp=$!
echo "$wp" > /run/gpu-g9-bind-watchdog.pid
sleep 1
test "$(readlink /proc/$wp/fd/3)" = /dev/watchdog0
cat /proc/sys/kernel/modprobe > /run/gpu-g9-modprobe.saved
printf '\n' > /proc/sys/kernel/modprobe
cleanup() {
 trap - EXIT
 if test -d /sys/module/panfrost; then rmmod panfrost; fi
 if test -d /sys/module/oriole_gpu_core_supply; then rmmod oriole_gpu_core_supply; fi
 if test -d /sys/module/oriole_gpu_overlay; then rmmod oriole_gpu_overlay; fi
 cat /run/gpu-g9-modprobe.saved > /proc/sys/kernel/modprobe
 kill -TERM "$wp"
 sleep 3
 test ! -e /proc/$wp/fd/3
 echo GPU_G9_FRESH_ROLLED_BACK
 dmesg | tail -40
}
trap cleanup EXIT
k=/newroot/usr/lib/modules/$(uname -r)/kernel
insmod "$k/drivers/clk/samsung/clk-acpm.ko"
insmod /opt/touch-stage/oriole-gpu-g6-overlay.ko
printf on > /sys/bus/platform/devices/1c500000.gpu/power/control
for r in /sys/class/regulator/*; do
 case "$(cat "$r/name")" in regulator-dummy|placeholder_reg|ufs-vcc) ;; trial-wlan-en) test "$(cat "$r/state")" = disabled ;; *) exit 1;; esac
done
test ! -d /sys/module/sec_acpm
insmod /opt/touch-stage/oriole-gpu-g9-core-supply.ko
insmod "$k/drivers/gpu/drm/scheduler/gpu-sched.ko"
echo '<6>ORIOLE_GPU_G9_BIND_BEGIN' > /dev/kmsg
insmod /opt/touch-stage/panfrost-g15.ko
sleep 2
dmesg | sed -n '/ORIOLE_GPU_G9_BIND_BEGIN/,$p' > /run/gpu-g9-bind-kernel.log
cat /run/gpu-g9-bind-kernel.log
grep -q 'ORIOLE_GPU_G7 L2 ret=0 expected=1 ready=00000001 transition=00000000' /run/gpu-g9-bind-kernel.log
grep -q 'ORIOLE_GPU_G7 shader ret=0 expected=779fff ready=00779fff transition=00000000' /run/gpu-g9-bind-kernel.log
grep -q 'ORIOLE_GPU_G7 tiler ret=0' /run/gpu-g9-bind-kernel.log
! grep -iE 'timed out|timeout|error|fault' /run/gpu-g9-bind-kernel.log
test -c /dev/dri/renderD128
test "$(cat /sys/bus/platform/devices/1c500000.gpu/power/control)" = on
cat /run/gpu-g9-modprobe.saved > /proc/sys/kernel/modprobe
kill -TERM "$wp"
sleep 3
test ! -e /proc/$wp/fd/3
trap - EXIT
echo GPU_G9_BIND_READY_NO_POWER_ERRORS
PROBE
cat /proc/kmsg >&2 &
logger=$!
trap 'kill "$logger" 2>/dev/null || true' EXIT
sh /run/gpu-g9-fresh-probe.sh > /run/gpu-g9-bind.log 2>&1
rc=$?
cat /run/gpu-g9-bind.log
exit "$rc"
