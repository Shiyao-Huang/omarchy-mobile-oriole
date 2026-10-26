#!/bin/bash
# SPDX-License-Identifier: MIT
# One-time bring-up step: requires verified off-device backup receipt.
set -euo pipefail
d=/opt/oriole-experiments/boot-b2
[[ $# == 1 && "$1" =~ ^[0-9a-f]{64}$ ]] || exit 2
export BOOT_B2_EXPECTED_BACKUP_SHA="$1"
mkdir /run/oriole-boot-b2-write-lock
cleanup() {
 local rc=$?
 trap - EXIT
 if [[ -f /run/oriole-boot-b2-relock.sh ]]; then
   /bin/bash /run/oriole-boot-b2-relock.sh || rc=97
 fi
 rmdir /run/oriole-boot-b2-write-lock || rc=98
 exit "$rc"
}
trap cleanup EXIT
python3 - <<'CHECK'
from pathlib import Path
import hashlib,os,json,re,subprocess
assert Path('/proc/1/comm').read_text().strip()=='systemd'
assert re.search(r'^androidboot.slot_suffix = "_b"$',Path('/proc/bootconfig').read_text(),re.M)
assert float(Path('/proc/uptime').read_text().split()[0])>60
assert Path('/sys/bus/spi/devices/spi0.0/driver').is_symlink()
assert Path('/sys/class/drm/renderD128').exists()
ids=subprocess.check_output(['pgrep','-x','Hyprland'],text=True).split();assert len(ids)==1
assert '/opt/oriole-experiments/mesa-g10/lib/libgallium' in Path('/proc/'+ids[0]+'/maps').read_text()
p=Path('/opt/oriole-experiments/boot-b2')
assert json.loads((p/'copy-test.json').read_text())['ARM64_copy_test'] is True
assert hashlib.sha256((p/'omamobile-bootctl').read_bytes()).hexdigest()=='21fb2b187be1a5f5bc5b1bcc4f8a05c9418be669ac60d1635779ce3010048ee6'
b=(p/'devinfo-before.img').read_bytes()
assert len(b)==8192 and hashlib.sha256(b).hexdigest()==os.environ['BOOT_B2_EXPECTED_BACKUP_SHA']
assert b[:8]==bytes.fromhex('4445564903000f00') and b[0x34:0x38]==bytes([0,4,0,0])
parts=[q for q in Path('/sys/class/block').glob('*') if (q/'uevent').is_file() and 'PARTNAME=devinfo' in (q/'uevent').read_text().splitlines()]
assert len(parts)==1;q=parts[0];parent=q.resolve().parent
assert re.fullmatch(r'sd[a-z][0-9]+',q.name) and re.fullmatch(r'sd[a-z]',parent.name)
assert (q/'ro').read_text().strip()=='1' and (parent/'ro').read_text().strip()=='1'
assert Path('/dev',q.name).read_bytes()==b
Path('/run/oriole-boot-b2-paths').write_text('/dev/'+q.name+'\n/dev/'+parent.name+'\n')
script='#!/bin/bash\nset -euo pipefail\nblockdev --setro /dev/'+q.name+'\nblockdev --setro /dev/'+parent.name+'\ntest "$(blockdev --getro /dev/'+q.name+')" = 1\ntest "$(blockdev --getro /dev/'+parent.name+')" = 1\n'
Path('/run/oriole-boot-b2-relock.sh').write_text(script)
print('B2_HEALTH_BACKUP_AND_LAYOUT_GATE_PASS')
CHECK
mapfile -t paths < /run/oriole-boot-b2-paths
dev=${paths[0]};disk=${paths[1]}
systemd-run --unit=oriole-boot-b2-relock --on-active=20s --timer-property=AccuracySec=1s --property=Type=oneshot /bin/bash /run/oriole-boot-b2-relock.sh
systemctl is-active --quiet oriole-boot-b2-relock.timer
blockdev --setrw "$disk"
blockdev --setrw "$dev"
"$d/omamobile-bootctl" mark-successful "$dev" b --i-understand > "$d/write-private.log" 2>&1
/bin/bash /run/oriole-boot-b2-relock.sh
python3 - <<'VERIFY'
from pathlib import Path
import json
p=Path('/opt/oriole-experiments/boot-b2');before=(p/'devinfo-before.img').read_bytes()
dev,disk=Path('/run/oriole-boot-b2-paths').read_text().splitlines();after=Path(dev).read_bytes()
assert len(after)==len(before)==8192
assert [i for i,(a,b) in enumerate(zip(before,after)) if a!=b]==[0x35]
assert after[0x35]==6
for name in [dev,disk]:assert Path('/sys/class/block',Path(name).name,'ro').read_text().strip()=='1'
r={'successful_B':True,'active_B':True,'changed_offsets':[53],'A_unchanged':True,'all_other_bytes_unchanged':True,'partition_and_parent_readonly':True,'reboot_tested':False,'automatic_startup_installed':False}
(p/'write-result.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
VERIFY
# Timer may already have completed: a missing unit is acceptable only after RO readback above.
if [[ $(systemctl show oriole-boot-b2-relock.timer -p LoadState --value) != not-found ]]; then
 systemctl stop oriole-boot-b2-relock.timer
fi
echo BOOT_B2_WRITE_AND_RELOCK_PASS
