#!/bin/bash
set -euo pipefail
python3 /var/tmp/oriole-g10/session-override.py rollback --restart
python3 - <<'PY'
from pathlib import Path
import subprocess,time,json,hashlib
for i in range(30):
 p=subprocess.run(['pgrep','-x','Hyprland'],capture_output=True,text=True)
 if p.returncode==0:
  ids=p.stdout.split();maps='\n'.join(Path('/proc/'+pid+'/maps').read_text() for pid in ids)
  if '/opt/oriole-experiments/mesa-g10/' not in maps:break
 time.sleep(1)
else:raise RuntimeError('software compositor not restored')
j=json.load(open('/var/tmp/oriole-g10/abi-result.json'))
for name,h in j['stock_libraries'].items():assert hashlib.sha256(Path(name).read_bytes()).hexdigest()==h
assert not Path('/home/agent/.config/systemd/user/wayland-wm@hyprland.desktop.service.d/90-oriole-mesa-g10.conf').exists()
Path('/var/tmp/oriole-g10/g13-rollback-passed.json').write_text(json.dumps({'stock_library_hashes':'unchanged','private_override':'removed','fresh_Hyprland_uses_private_Mesa':False}))
print('G13_ROLLBACK_SOFTWARE_AND_HASHES_VERIFIED')
PY
wp=$(cat /var/tmp/oriole-g10/g13-watchdog.pid)
kill -TERM "$wp"
sleep 3
test ! -e "/proc/$wp/fd/3"
touch /var/tmp/oriole-g10/g13-rollback-complete
echo G13_WATCHDOG_DISARMED
