#!/bin/sh
# SPDX-License-Identifier: MIT
# Load the Oriole touch prerequisites in the only safe order for the
# diagnostic kernel. This does not continue the GUI handoff or write a
# partition; serial-input30-gui-handoff.sh remains the separate guarded gate.
set -eu

module_root=${MODULE_ROOT:-/newroot/lib/modules/$(uname -r)}
experiment_root=${EXPERIMENT_ROOT:-/newroot/opt/oriole-experiments/network-v4a/recovery}
mailbox="$module_root/kernel/drivers/mailbox/exynos-mailbox.ko"
acpm="$module_root/kernel/drivers/firmware/samsung/acpm-protocol.ko"
hold="$experiment_root/oriole_touch_supply_hold.ko"
touch="$experiment_root/oriole-input30.ko"

[ "$(cat /proc/sys/kernel/modules_disabled)" = 0 ]
[ ! -e /run/oriole-stage-continue ]
[ -r "$mailbox" ]
[ -r "$acpm" ]
[ -r "$hold" ]
[ -r "$touch" ]

# ACPM exports the symbols used by the reversible touch rail hold. The
# mailbox module must be present first; loading acpm alone can leave the
# diagnostic boot unresponsive.
[ -d /sys/module/exynos_mailbox ] || insmod "$mailbox"
[ -d /sys/module/acpm_protocol ] || insmod "$acpm"
[ -d /sys/module/oriole_touch_supply_hold ] || insmod "$hold"
[ -d /sys/module/oriole_touch_minimal ] || insmod "$touch" session_seconds=0

sleep 3
[ -L /sys/bus/spi/devices/spi0.0/driver ]
[ -e /sys/bus/spi/devices/spi0.0/input/input*/event* ]
dmesg | grep -q 'INPUT30_READY'
! dmesg | grep -q 'INPUT30_END'
echo INPUT30_MODULE_STAGE_READY
