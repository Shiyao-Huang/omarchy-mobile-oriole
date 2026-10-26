set -eu
cat > /run/wifi-w2-watchdog.sh <<'WD'
#!/bin/sh
exec 3>/dev/watchdog0
trap 'printf V >&3; exit 0' TERM INT
i=0
while test "$i" -lt 60; do printf k >&3; sleep 2; i=$((i+1)); done
while :; do sleep 1; done
WD
cat > /run/wifi-w2-trial.sh <<'TRIAL'
#!/bin/sh
set -eu
test "$(cat /proc/1/comm)" = init
test "$(uname -r)" = 7.3.0-rc6-omamobile-oriole-m1
test "$(cat /proc/sys/kernel/modules_disabled)" = 0
test ! -e /run/oriole-stage-continue
test -e /run/network-v4a-backup-verified
test -d /sys/module/oriole_wifi_overlay
for n in brcmfmac brcmfmac_wcc brcmutil cfg80211 rfkill pcie_gs101 phy_gs101_pcie; do test ! -d /sys/module/$n; done
test -z "$(ls /sys/bus/pci/devices)"
for f in /proc/[0-9]*/fd/*; do test "$(readlink "$f" 2>/dev/null || true)" != /dev/watchdog0; done
d=/newroot/opt/oriole-experiments/wifi-w2
h=/newroot/opt/oriole-experiments/network-v4a/wifi
k=/newroot/usr/lib/modules/$(uname -r)/kernel
chroot /newroot /usr/bin/python3 - <<'PY'
from pathlib import Path
import json,hashlib
p=Path('/opt/oriole-experiments/wifi-w2')
for n,h in json.loads((p/'manifest.json').read_text()).items():assert hashlib.sha256((p/n).read_bytes()).hexdigest()==h
for n,h in {'pcie-gs101.ko':'33c10ea596b6eb063007626b746e256b030d754c882a18a4f835f0756b89ea72','phy-gs101-pcie.ko':'265facd5f95c2a5924008a474dadfb6261ec7084239ab2bd8d75aad86e639928'}.items():assert hashlib.sha256((Path('/opt/oriole-experiments/network-v4a/wifi')/n).read_bytes()).hexdigest()==h
PY
rail=''
for p in /sys/class/regulator/regulator.*; do
 if test "$(cat "$p/name" 2>/dev/null || true)" = trial-wlan-en; then rail="$p"; fi
done
test -n "$rail"; test "$(cat "$rail/state")" = disabled
cat /proc/sys/kernel/modprobe > /run/wifi-w2-modprobe.saved
cat /sys/module/firmware_class/parameters/path > /run/wifi-w2-fwpath.saved
printf '\n' > /proc/sys/kernel/modprobe
printf '%s\n' "$d/firmware" > /sys/module/firmware_class/parameters/path
sh /run/wifi-w2-watchdog.sh </dev/null >/run/wifi-w2-watchdog.log 2>&1 &
wp=$!; echo "$wp" > /run/wifi-w2-watchdog.pid
sleep 1; test "$(readlink /proc/$wp/fd/3)" = /dev/watchdog0
ep=''
. "$d/wifi-w2-teardown.sh"
wifi_endpoint_unbind() {
 if test -n "$ep" && test -L "$ep/driver"; then
  test "$(basename "$(readlink "$ep/driver")")" = brcmfmac || return 1
  printf '%s\n' "$(basename "$ep")" > "$ep/driver/unbind" || return 1
 fi
}
wifi_endpoint_unbound() { test -z "$ep" || test ! -L "$ep/driver"; }
wifi_radio_unload() {
 for n in brcmfmac_wcc brcmfmac brcmutil cfg80211 rfkill; do
  if test -d "/sys/module/$n"; then rmmod "$n" || return 1; fi
 done
}
wifi_host_unload() {
 if test -d /sys/module/pcie_gs101; then rmmod pcie_gs101 || return 1; fi
 test -z "$(ls /sys/bus/pci/devices)"
}
wifi_phy_unload() {
 if test -d /sys/module/phy_gs101_pcie; then rmmod phy_gs101_pcie || return 1; fi
}
wifi_rail_off() { test "$(cat "$rail/state")" = disabled; }
cleanup() {
 rc=$?; trap - EXIT; set +e
 if ! wifi_w2_teardown; then echo WIFI_W2_TEARDOWN_FAILED_WATCHDOG_ARMED; exit 125; fi
 cat /run/wifi-w2-fwpath.saved > /sys/module/firmware_class/parameters/path
 cat /run/wifi-w2-modprobe.saved > /proc/sys/kernel/modprobe
 dmesg | sed -n '/ORIOLE_WIFI_W2_BEGIN/,$p' > "$d/kernel-private.log"
 cat "$d/kernel-private.log"
 if grep -iE 'ufshcd_err_handler|PCIe teardown failed|supply disable failed|BUG:|Oops:|Unable to handle kernel' "$d/kernel-private.log"; then
  echo WIFI_W2_KERNEL_FAULT_WATCHDOG_ARMED; exit 125
 fi
 kill -TERM "$wp"; sleep 3
 test ! -e /proc/$wp/fd/3 || exit 125
 echo WIFI_W2_CLEANED_rc_$rc
 exit "$rc"
}
trap cleanup EXIT
echo '<6>ORIOLE_WIFI_W2_BEGIN' > /dev/kmsg
insmod "$h/phy-gs101-pcie.ko"
insmod "$h/pcie-gs101.ko"
ep=/sys/bus/pci/devices/0001:01:00.0
test "$(cat "$ep/vendor")" = 0x14e4
test "$(cat "$ep/device")" = 0x4441
test ! -L "$ep/driver"
printf 'wifi-w2-hold\n' > "$ep/driver_override"
insmod "$k/net/rfkill/rfkill.ko"
insmod "$k/net/wireless/cfg80211.ko"
insmod "$d/brcmutil.ko"
insmod "$d/brcmfmac.ko"
insmod "$d/brcmfmac-wcc.ko"
test ! -L "$ep/driver"
printf 'brcmfmac\n' > "$ep/driver_override"
printf '%s\n' "$(basename "$ep")" > /sys/bus/pci/drivers/brcmfmac/bind
found=0
for i in $(seq 1 30); do
 for p in /sys/class/net/*; do
  if test -d "$p/wireless"; then echo WIRELESS_INTERFACE "$(basename "$p")"; found=1; fi
 done
 test "$found" = 0 || break
 sleep 1
done
test "$found" = 1
dmesg | sed -n '/ORIOLE_WIFI_W2_BEGIN/,$p' > /run/wifi-w2-probe.log
grep 'Firmware: BCM4389' /run/wifi-w2-probe.log
! grep -iE 'Dongle setup failed|firmware.*crash|FW trap|BUG:|Oops:' /run/wifi-w2-probe.log
echo WIFI_W2_FIRMWARE_INTERFACE_PASS_NO_ASSOCIATION
TRIAL
cat /proc/kmsg >&2 &
logger=$!
trap 'kill "$logger" 2>/dev/null || true' EXIT
sh /run/wifi-w2-trial.sh
