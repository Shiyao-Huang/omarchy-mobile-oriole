set -eu
d=/opt/oriole-experiments/g15-w2-desktop
test "$(cat /proc/1/comm)" = systemd
test -c /dev/dri/renderD128
test ! -e "$d/geometry-1.log"
test "$(sha256sum /var/tmp/oriole-g10/gles-probe.py | cut -d ' ' -f1)" = 27ffb055b332c99e4a6b42c223a05aab47e9531b56b671efa26b6cd0bb66679e
for f in /proc/[0-9]*/fd/*; do test "$(readlink "$f" 2>/dev/null || true)" != /dev/watchdog0; done
cat > "$d/preflight-watchdog.sh" <<'WD'
#!/bin/sh
exec 3>/dev/watchdog0
trap 'printf V >&3; exit 0' TERM INT
i=0
while [ "$i" -lt 30 ]; do printf k >&3; sleep 2; i=$((i+1)); done
while :; do sleep 1; done
WD
setsid sh "$d/preflight-watchdog.sh" </dev/null >"$d/preflight-watchdog.log" 2>&1 &
wp=$!;echo "$wp" > "$d/preflight-watchdog.pid"
sleep 1; test "$(readlink /proc/$wp/fd/3)" = /dev/watchdog0
dmesg --follow-new --time-format=raw &
kp=$!
trap 'kill "$kp" 2>/dev/null || true' EXIT
/usr/bin/env -u LIBGL_ALWAYS_SOFTWARE -u GALLIUM_DRIVER -u MESA_LOADER_DRIVER_OVERRIDE \
 LD_LIBRARY_PATH=/opt/oriole-experiments/mesa-g10/lib \
 LIBGL_DRIVERS_PATH=/opt/oriole-experiments/mesa-g10/lib/dri \
 GBM_BACKENDS_PATH=/opt/oriole-experiments/mesa-g10/lib/gbm \
 __EGL_VENDOR_LIBRARY_FILENAMES=/opt/oriole-experiments/mesa-g10/share/glvnd/egl_vendor.d/50_mesa.json \
 MESA_SHADER_CACHE_DISABLE=true HOME="$d" \
 /usr/bin/timeout -s KILL 20 /usr/bin/python3 -u /var/tmp/oriole-g10/gles-probe.py /dev/dri/renderD128 > "$d/geometry-1.log" 2>&1
python3 - <<'PY'
from pathlib import Path
import json
p=Path('/opt/oriole-experiments/g15-w2-desktop/geometry-1.log')
a=[json.loads(x) for x in p.read_text().splitlines() if x.startswith('{')]
assert a[-1]['pass_shader_readback'] and a[-1]['pixels_verified']==768
print(json.dumps(a[-1]))
PY
dmesg | sed -n '/ORIOLE_GPU_G9_BIND_BEGIN/,$p' > "$d/preflight-kernel.log"
! grep -iE 'panfrost.*(fault|error|timeout|timed out)|Unhandled fault' "$d/preflight-kernel.log"
kill -TERM "$wp";sleep 3; test ! -e /proc/$wp/fd/3
echo G15_W2_DESKTOP_PREFLIGHT_PASS_WATCHDOG_DISARMED
