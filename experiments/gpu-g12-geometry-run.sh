#!/bin/bash
set -euo pipefail
test "$(cat /proc/1/comm)" = systemd
test -c /dev/dri/renderD128
test "$(cat /sys/bus/platform/devices/1c500000.gpu/power/control)" = on
python3 -c 'import json; assert json.load(open("/var/tmp/oriole-g10/abi-result.json"))["candidate_dependencies"] == "pass"'
prefix=/opt/oriole-experiments/mesa-g10
test -f "$prefix/share/glvnd/egl_vendor.d/50_mesa.json"
wp=; kp=
cleanup() {
 rc=$?
 trap - EXIT
 if test -n "$kp"; then kill "$kp" 2>/dev/null || true; fi
 if test -n "$wp"; then
  kill -TERM "$wp" 2>/dev/null || true
  sleep 3
  if test -e "/proc/$wp/fd/3"; then echo WATCHDOG_NOT_DISARMED; exit 91; fi
 fi
 echo "GPU_G12_GLES_FINISHED rc=$rc WATCHDOG_DISARMED"
 exit "$rc"
}
trap cleanup EXIT
sh /run/gpu-g1-watchdog.sh </dev/null >/var/tmp/oriole-g10/gles-watchdog.log 2>&1 &
wp=$!; echo "$wp" > /var/tmp/oriole-g10/gles-watchdog.pid
sleep 1
test "$(readlink /proc/$wp/fd/3)" = /dev/watchdog0
dmesg --follow-new --time-format=raw &
kp=$!
sleep 1
kill -0 "$kp"
echo '<6>ORIOLE_GPU_G12_GLES_BEGIN' > /dev/kmsg
env -u LIBGL_ALWAYS_SOFTWARE -u GALLIUM_DRIVER -u MESA_LOADER_DRIVER_OVERRIDE \
 LD_LIBRARY_PATH="$prefix/lib" LIBGL_DRIVERS_PATH="$prefix/lib/dri" \
 GBM_BACKENDS_PATH="$prefix/lib/gbm" \
 __EGL_VENDOR_LIBRARY_FILENAMES="$prefix/share/glvnd/egl_vendor.d/50_mesa.json" \
 MESA_SHADER_CACHE_DISABLE=true HOME=/var/tmp/oriole-g10 \
 timeout -s KILL 60 python3 -u /var/tmp/oriole-g10/gles-probe.py /dev/dri/renderD128 \
 2>&1 | tee /var/tmp/oriole-g10/geometry-recheck-result.log
python3 - <<'CHECK'
import json
from pathlib import Path
rows=[json.loads(x) for x in Path('/var/tmp/oriole-g10/geometry-recheck-result.log').read_text().splitlines() if x.startswith('{')]
assert rows[-1].get('pass_shader_readback') is True and rows[-1]['pixels_verified']==768
CHECK
dmesg | sed -n '/ORIOLE_GPU_G12_GLES_BEGIN/,$p' > /var/tmp/oriole-g10/geometry-recheck-kernel.log
if grep -iE 'panfrost.*(fault|error|timeout|timed out)|Unhandled fault' /var/tmp/oriole-g10/geometry-recheck-kernel.log; then exit 92; fi
echo GPU_G12_HARDWARE_SHADER_PASS
