#!/bin/sh
# SPDX-License-Identifier: MIT
# Run inside the Oriole diagnostic initramfs after the bounded input/GPU stage.
# The serial service must exist before stage-continue: otherwise systemd can
# start the desktop while dropping the only recovery shell and USB network.
set -eu

test -e /etc/omamobile-touch-stage
test -e /etc/omamobile-disable-modules
test "$(cat /proc/sys/kernel/modules_disabled)" = 0
test ! -e /run/oriole-stage-continue
ready=$(dmesg | sed -n 's/^\[ *\([0-9.]*\)\].*INPUT30_READY.*/\1/p' | tail -1)
test -n "$ready"
awk -v start="$ready" '$1-start >= 60 {ok=1} END {exit !ok}' /proc/uptime
test -L /sys/bus/spi/devices/spi0.0/driver
test -d /sys/module/oriole_touch_supply_hold
test -x /newroot/usr/bin/bash
for n in $(seq 1 26); do test "$(cat /sys/class/block/sda${n}/ro)" = 1; done
test "$(cat /sys/class/block/sda27/ro)" = 0
! dmesg | grep -c INPUT30_END >/dev/null

mkdir -p /run/systemd/system/multi-user.target.wants
cat > /run/systemd/system/oriole-bringup-serial.service <<'UNIT'
[Unit]
Description=Current-boot Pixel 6 USB bringup shell
After=systemd-udevd.service
ConditionPathExists=/dev/ttyGS0

[Service]
Type=simple
User=root
WorkingDirectory=/root
Environment=TERM=vt100 HISTFILE=/dev/null
ExecStart=/usr/bin/bash --noprofile --norc -i
StandardInput=tty
StandardOutput=tty
StandardError=tty
TTYPath=/dev/ttyGS0
TTYReset=yes
Restart=always
RestartSec=1

[Install]
WantedBy=multi-user.target
UNIT
chmod 644 /run/systemd/system/oriole-bringup-serial.service
ln -s ../oriole-bringup-serial.service \
  /run/systemd/system/multi-user.target.wants/oriole-bringup-serial.service

kill -TERM "$(cat /run/oriole-touch-wd.pid)"
sleep 3
test ! -e /proc/$(cat /run/oriole-touch-wd.pid)/fd/3
cat /run/oriole-modprobe.saved > /proc/sys/kernel/modprobe
sync
echo GUI_HANDOFF_WATCHDOG_DISARMED
touch /run/oriole-stage-continue
