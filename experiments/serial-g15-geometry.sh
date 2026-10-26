cat > /run/gpu-g9-gles-run.sh <<'RUN'
#!/bin/sh
set -eu
grep -q GPU_G9_BIND_READY_NO_POWER_ERRORS /run/gpu-g9-bind.log
test "$(cat /proc/1/comm)" = init
test -c /dev/dri/renderD128
test "$(sha256sum /newroot/var/tmp/oriole-g10/gles-probe.py | cut -d ' ' -f1)" = 27ffb055b332c99e4a6b42c223a05aab47e9531b56b671efa26b6cd0bb66679e
test "$(cat /sys/bus/platform/devices/1c500000.gpu/power/control)" = on
! grep -q ' /newroot/dev ' /proc/mounts
! grep -q ' /newroot/proc ' /proc/mounts
! grep -q ' /newroot/sys ' /proc/mounts
mkdir -p /newroot/dev /newroot/proc /newroot/sys /newroot/var/tmp/oriole-g15
sh /run/gpu-g1-watchdog.sh </dev/null >/run/gpu-g9-gles-watchdog.log 2>&1 &
wp=$!
echo "$wp" > /run/gpu-g9-gles-watchdog.pid
sleep 1
test "$(readlink /proc/$wp/fd/3)" = /dev/watchdog0
cleanup() {
 trap - EXIT
 for name in sys proc dev; do
  if grep -q " /newroot/$name " /proc/mounts; then umount "/newroot/$name"; fi
 done
 kill -TERM "$wp"
 sleep 3
 test ! -e /proc/$wp/fd/3
 echo GPU_G9_GLES_WATCHDOG_DISARMED
 dmesg | tail -25
}
trap cleanup EXIT
mount --bind /dev /newroot/dev
mount --bind /proc /newroot/proc
mount --bind /sys /newroot/sys
echo '<6>ORIOLE_GPU_G15_GLES_BEGIN' > /dev/kmsg
grep -iE 'gpu|mmu|job' /proc/interrupts || true
for n in 1 2 3; do
 chroot /newroot /usr/bin/env -u LIBGL_ALWAYS_SOFTWARE -u GALLIUM_DRIVER -u MESA_LOADER_DRIVER_OVERRIDE \
  LD_LIBRARY_PATH=/opt/oriole-experiments/mesa-g10/lib \
  LIBGL_DRIVERS_PATH=/opt/oriole-experiments/mesa-g10/lib/dri \
  GBM_BACKENDS_PATH=/opt/oriole-experiments/mesa-g10/lib/gbm \
  __EGL_VENDOR_LIBRARY_FILENAMES=/opt/oriole-experiments/mesa-g10/share/glvnd/egl_vendor.d/50_mesa.json \
  MESA_SHADER_CACHE_DISABLE=true HOME=/var/tmp/oriole-g15 \
  /usr/bin/timeout -s KILL 60 /usr/bin/python3 -u /var/tmp/oriole-g10/gles-probe.py /dev/dri/renderD128 > /newroot/var/tmp/oriole-g15/geometry-$n.log 2>&1
 cat /newroot/var/tmp/oriole-g15/geometry-$n.log
 chroot /newroot /usr/bin/python3 -c 'import json,sys; a=[json.loads(x) for x in open(sys.argv[1]) if x.startswith("{")]; assert a[-1].get("pass_shader_readback") is True and a[-1]["pixels_verified"]==768' /var/tmp/oriole-g15/geometry-$n.log
 dmesg | sed -n '/ORIOLE_GPU_G9_BIND_BEGIN/,$p' > /run/gpu-g15-since-bind.log
 if grep -iE 'panfrost.*(fault|error|timeout|timed out)|Unhandled fault|gpu sched timeout' /run/gpu-g15-since-bind.log; then exit 92; fi
 echo G15_GEOMETRY_PASS_$n
done
grep -iE 'gpu|mmu|job' /proc/interrupts || true
echo GPU_G15_COLD_FIRST_DRAW_PASS

RUN
cat /proc/kmsg >&2 &
logger=$!
trap 'kill "$logger" 2>/dev/null || true' EXIT
sh /run/gpu-g9-gles-run.sh > /run/gpu-g15-gles-run.log 2>&1
rc=$?
cat /run/gpu-g15-gles-run.log
exit "$rc"
