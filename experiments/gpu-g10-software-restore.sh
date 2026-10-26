set -eu
python3 - <<'PY'
from pathlib import Path
import os,json
p=Path('/home/agent/.config/systemd/user/wayland-wm@hyprland.desktop.service.d/85-oriole-g10-baseline.conf')
b=b'[Service]\nEnvironment=LIBGL_ALWAYS_SOFTWARE=1\nEnvironment=GALLIUM_DRIVER=llvmpipe\nEnvironment=MESA_LOADER_DRIVER_OVERRIDE=swrast\nEnvironment=AQ_DRM_DEVICES=/dev/dri/card0\n'
assert not p.is_symlink()
if p.exists():assert p.read_bytes()==b,'manual edit: preserve and stop'
else:
 p.parent.mkdir(parents=True,exist_ok=True)
 fd=os.open(p,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o644)
 with os.fdopen(fd,'wb') as f:f.write(b);f.flush();os.fsync(f.fileno())
 os.chown(p,1000,1000)
d=Path('/var/tmp/oriole-g10');d.mkdir(exist_ok=True)
(d/'temporary-baseline.json').write_text(json.dumps({'override':str(p),'purpose':'restore software desktop while private G78Mesa build pending; remove before hardware-render acceptance'}))
print('G10_SOFTWARE_BASELINE_OVERRIDE_READY')
PY
setsid sh -c 'sleep 2; systemctl restart sddm' </dev/null >/var/tmp/oriole-g10/restart.log 2>&1 &
