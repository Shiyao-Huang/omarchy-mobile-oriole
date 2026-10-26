set -eu
cat > /run/network-enum-watchdog.sh <<'WD'
#!/bin/sh
exec 3>/dev/watchdog0
trap 'printf V >&3; exit 0' TERM INT
i=0
while test "$i" -lt 60; do printf k >&3; sleep 2; i=$((i+1)); done
while :; do sleep 1; done
WD
cat > /run/network-enum-trial.sh <<'TRIAL'
#!/bin/sh
set -eu
test "$(cat /proc/1/comm)" = init
test "$(cat /proc/sys/kernel/modules_disabled)" = 0
test ! -e /run/oriole-stage-continue
test "$(uname -r)" = 7.3.0-rc6-omamobile-oriole-m1
test -e /run/network-v4a-backup-verified
d=/newroot/opt/oriole-experiments/network-v4a/wifi
test "$(sha256sum "$d/pcie-gs101.ko" | cut -d ' ' -f1)" = 33c10ea596b6eb063007626b746e256b030d754c882a18a4f835f0756b89ea72
test "$(sha256sum "$d/phy-gs101-pcie.ko" | cut -d ' ' -f1)" = 265facd5f95c2a5924008a474dadfb6261ec7084239ab2bd8d75aad86e639928
test "$(sha256sum "$d/oriole_wifi_overlay.ko" | cut -d ' ' -f1)" = 2f5e7606d3a783ef071cc1f80fb67f8a9382e8c21d6a3213f83d271ae41ecf65
for n in brcmfmac bcmdhd cpif pcie_gs101 phy_gs101_pcie oriole_wifi_overlay; do test ! -d "/sys/module/$n"; done
test -z "$(ls /sys/bus/pci/devices)"
for f in /proc/[0-9]*/fd/*; do test "$(readlink "$f" 2>/dev/null || true)" != /dev/watchdog0; done
cat /proc/sys/kernel/modprobe > /run/network-modprobe.saved
printf '\n' > /proc/sys/kernel/modprobe
sh /run/network-enum-watchdog.sh </dev/null >/run/network-enum-watchdog.log 2>&1 &
wp=$!
echo "$wp" > /run/network-enum-watchdog.pid
sleep 1
test "$(readlink /proc/$wp/fd/3)" = /dev/watchdog0
rail=''
cleanup() {
 rc=$?
 trap - EXIT
 set +e
 fail=0
 if test -d /sys/module/pcie_gs101; then rmmod pcie_gs101 || fail=1; fi
 if test -d /sys/module/phy_gs101_pcie; then rmmod phy_gs101_pcie || fail=1; fi
 test -z "$(ls /sys/bus/pci/devices)" || fail=1
 if test -n "$rail"; then
  printf 'SUPPLY_AFTER '; cat "$rail/state" || fail=1
  test "$(cat "$rail/state" 2>/dev/null)" = disabled || fail=1
 fi
 dmesg | sed -n '/ORIOLE_NETWORK_ENUM_BEGIN/,$p' > "$d/enum-kernel.log"
 cat "$d/enum-kernel.log"
 if grep -iE 'ufshcd_err_handler|PCIe teardown failed|supply disable failed|BUG:|Oops:' "$d/enum-kernel.log"; then fail=1; fi
 if test "$fail" != 0; then echo NETWORK_ENUM_CLEANUP_FAILED_WATCHDOG_ARMED; exit 125; fi
 cat /run/network-modprobe.saved > /proc/sys/kernel/modprobe
 kill -TERM "$wp"
 sleep 3
 if test -e /proc/$wp/fd/3; then echo WATCHDOG_DISARM_FAILED; exit 125; fi
 echo NETWORK_ENUM_CLEANED_rc_$rc
 exit "$rc"
}
trap cleanup EXIT
echo '<6>ORIOLE_NETWORK_ENUM_BEGIN' > /dev/kmsg
insmod "$d/oriole_wifi_overlay.ko"
for p in /sys/class/regulator/regulator.*; do
 if test "$(cat "$p/name" 2>/dev/null || true)" = trial-wlan-en; then rail="$p"; fi
done
test -n "$rail"
printf 'SUPPLY_BEFORE '; cat "$rail/state"
test "$(cat "$rail/state")" = disabled
insmod "$d/phy-gs101-pcie.ko"
test -L /sys/bus/platform/devices/14550000.phy/driver
insmod "$d/pcie-gs101.ko"
sleep 1
printf 'SUPPLY_DURING '; cat "$rail/state"
test -L /sys/bus/platform/devices/14520000.pcie/driver
found=0
for p in /sys/bus/pci/devices/*; do
 test -e "$p/vendor" || continue
 echo PCI_NODE "$(basename "$p")" "$(cat "$p/vendor")" "$(cat "$p/device")" "$(cat "$p/class")"
 if test "$(cat "$p/vendor")" = 0x14e4; then
  test "$(cat "$p/device")" = 0x4441
  test ! -L "$p/driver"
  command_word="$(od -An -tu2 -j4 -N2 "$p/config" | tr -d ' \n')"
  echo ENDPOINT_COMMAND "$command_word"
  test "$((command_word & 4))" = 0
  found=$((found+1))
 fi
done
test "$found" = 1
echo NETWORK_ENUM_ENDPOINT_PASS_NO_DRIVER_NO_BUSMASTER
TRIAL
cat /proc/kmsg >&2 &
logger=$!
trap 'kill "$logger" 2>/dev/null || true' EXIT
sh /run/network-enum-trial.sh
