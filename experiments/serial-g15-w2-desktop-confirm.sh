set -eu
python3 - <<'PY'
from pathlib import Path
import subprocess,json,hashlib
p=Path('/run/systemd/user/wayland-wm@hyprland.desktop.service.d/90-oriole-mesa-g10.conf');assert p.is_file()
ids=subprocess.check_output(['pgrep','-x','Hyprland'],text=True).split();assert len(ids)==1
s=Path('/proc/'+ids[0]+'/maps').read_text();assert '/opt/oriole-experiments/mesa-g10/lib/libgallium' in s
assert json.loads(Path('/opt/oriole-experiments/g15-w2-desktop/g15-desktop-renderer.json').read_text())['private_Gallium_mapped']
for name,h in json.load(open('/var/tmp/oriole-g10/abi-result.json'))['stock_libraries'].items():assert hashlib.sha256(Path(name).read_bytes()).hexdigest()==h
print('G15_FRESH_SERIAL_GPU_MAP_AND_STOCK_HASH_PASS')
PY
runuser -u agent -- env XDG_RUNTIME_DIR=/run/user/1000 systemctl --user show wayland-wm@hyprland.desktop.service -p DropInPaths -p ActiveState
systemctl is-active sddm oriole-bringup-serial oriole-g15-rollback.timer
wp=$(cat /opt/oriole-experiments/g15-w2-desktop/g15-watchdog.pid)
test "$(readlink /proc/$wp/fd/3)" = /dev/watchdog0
dmesg | sed -n '/ORIOLE_GPU_G15_DESKTOP_BEGIN/,$p' > /opt/oriole-experiments/g15-w2-desktop/g15-confirm-kernel.log
if grep -iE 'panfrost.*(fault|error|timeout|timed out)|Unhandled fault' /opt/oriole-experiments/g15-w2-desktop/g15-confirm-kernel.log; then exit 92; fi
systemctl stop oriole-g15-rollback.timer
test "$(systemctl is-active oriole-g15-rollback.timer)" = inactive
kill -TERM "$wp"
sleep 3
test ! -e "/proc/$wp/fd/3"
echo G15_CURRENT_BOOT_GPU_RETAINED_WATCHDOG_DISARMED
python3 - <<'PY'
from pathlib import Path
import json,subprocess,os
base=Path('/sys/devices/system/cpu');cpus=[]
for p in sorted(base.glob('cpu[0-9]*')):
 def read(path):return path.read_text().strip() if path.exists() else None
 cpus.append({'cpu':p.name,'capacity':read(p/'cpu_capacity'),'cluster_id':read(p/'topology/cluster_id'),'core_id':read(p/'topology/core_id')})
policies=[]
for p in sorted((base/'cpufreq').glob('policy*')):
 policies.append({'policy':p.name,**{n:(p/n).read_text().strip() for n in ['related_cpus','scaling_driver','scaling_governor','scaling_min_freq','scaling_max_freq','scaling_cur_freq']}})
dt=[p.read_bytes().replace(b'\0',b',').decode() for p in Path('/sys/firmware/devicetree/base/cpus').glob('cpu@*/compatible')]
pid=subprocess.check_output(['pgrep','-x','Hyprland'],text=True).strip();allowed=[x for x in Path('/proc/'+pid+'/status').read_text().splitlines() if x.startswith('Cpus_allowed_list')]
r={'online':(base/'online').read_text().strip(),'cores':cpus,'policies':policies,'DT_CPU_compatibles':dt,'Hyprland_affinity':allowed,'cgroup_controllers':Path('/sys/fs/cgroup/cgroup.controllers').read_text().strip(),'shell_affinity':sorted(os.sched_getaffinity(0))}
Path('/var/tmp/oriole-g10/cpu-topology.json').write_text(json.dumps(r,indent=2));print(json.dumps(r))
PY
