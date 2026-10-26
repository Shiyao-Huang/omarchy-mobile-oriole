#!/bin/bash
set -euo pipefail
d=/var/tmp/oriole-g10
test ! -e "$d/g13r-rollback-complete"
python3 - <<'PY'
from pathlib import Path
import json,hashlib
p=Path('/home/agent/.config/systemd/user/wayland-wm@hyprland.desktop.service.d/85-oriole-g10-baseline.conf')
assert p.read_bytes()==b'[Service]\nEnvironment=LIBGL_ALWAYS_SOFTWARE=1\nEnvironment=GALLIUM_DRIVER=llvmpipe\nEnvironment=MESA_LOADER_DRIVER_OVERRIDE=swrast\nEnvironment=AQ_DRM_DEVICES=/dev/dri/card0\n'
rows=[json.loads(x) for x in Path('/var/tmp/oriole-g10/geometry-recheck-result.log').read_text().splitlines() if x.startswith('{')]
assert rows[-1]['pass_shader_readback']
assert not Path('/home/agent/.config/systemd/user/wayland-wm@hyprland.desktop.service.d/90-oriole-mesa-g10.conf').exists()
for name,h in json.load(open('/var/tmp/oriole-g10/abi-result.json'))['stock_libraries'].items():assert hashlib.sha256(Path(name).read_bytes()).hexdigest()==h
PY
runuser -u agent -- env LD_LIBRARY_PATH=/opt/oriole-experiments/mesa-g10/lib python3 -c 'from pathlib import Path; import ctypes,os; paths=sorted({p.resolve() for p in Path("/opt/oriole-experiments/mesa-g10/lib").rglob("*.so*") if p.is_file()}); assert len(paths)==6; handles=[ctypes.CDLL(str(p)) for p in paths]; assert os.access("/dev/dri/renderD128",os.R_OK|os.W_OK); print("DESKTOP_USER_LIBRARY_PREFLIGHT_PASS")'
cat > "$d/g13r-watchdog.sh" <<'WD'
#!/bin/sh
exec 3>/dev/watchdog0
trap 'printf V >&3; exit 0' TERM INT
i=0
while [ "$i" -lt 90 ]; do printf k >&3; sleep 2; i=$((i+1)); done
while :; do sleep 1; done
WD
setsid sh "$d/g13r-watchdog.sh" </dev/null >"$d/g13r-watchdog.log" 2>&1 &
wp=$!; echo "$wp" > "$d/g13r-watchdog.pid"
sleep 1
test "$(readlink /proc/$wp/fd/3)" = /dev/watchdog0
kp=; armed=0
cleanup() {
 if test -n "$kp"; then kill "$kp" 2>/dev/null || true; fi
 if test "$armed" = 0; then kill -TERM "$wp" 2>/dev/null || true; fi
}
trap cleanup EXIT
systemd-run --unit=oriole-g13r-rollback --on-active=90s --timer-property=AccuracySec=1s /bin/bash "$d/rollback-r.sh"
systemctl is-active oriole-g13r-rollback.timer
armed=1
dmesg --follow-new --time-format=raw &
kp=$!
echo '<6>ORIOLE_GPU_G13R_DESKTOP_BEGIN' > /dev/kmsg
python3 "$d/session-override.py" enable --restart
sleep 8
python3 - <<'PY'
from pathlib import Path
import subprocess,json
ids=subprocess.check_output(['pgrep','-x','Hyprland'],text=True).split();assert len(ids)==1
maps=Path('/proc/'+ids[0]+'/maps').read_text();assert '/opt/oriole-experiments/mesa-g10/lib/libgallium' in maps
logs=list(Path('/run/user/1000/hypr').glob('*/hyprland.log'));log=max(logs,key=lambda p:p.stat().st_mtime);s=log.read_text(errors='replace')
rows=[x for x in s.splitlines() if any(k in x for k in ('GL_RENDERER','GL_VERSION','Mali-G78','llvmpipe'))]
print(json.dumps({'desktop_renderer_rows':rows}),flush=True)
assert any('Mali-G78' in x for x in rows)
Path('/var/tmp/oriole-g10/g13r-desktop-renderer.json').write_text(json.dumps({'rows':rows,'private_Gallium_mapped':True},indent=2))
PY
python3 "$d/benchmark/run.py" candidate
cat "$d/benchmark/candidate-foot.log"
dmesg | sed -n '/ORIOLE_GPU_G13R_DESKTOP_BEGIN/,$p' > "$d/g13r-desktop-kernel.log"
if grep -iE 'panfrost.*(fault|error|timeout|timed out)|Unhandled fault' "$d/g13r-desktop-kernel.log"; then echo G13R_GPU_FAILURE; exit 92; fi
for i in $(seq 1 110); do test ! -e "$d/g13r-rollback-complete" || break; sleep 1; done
test -e "$d/g13r-rollback-complete"
cat "$d/g13r-rollback-passed.json"
systemctl is-active sddm oriole-bringup-serial
printf '\nG13R_TRIAL_AND_AUTOMATIC_ROLLBACK_COMPLETE\n'
