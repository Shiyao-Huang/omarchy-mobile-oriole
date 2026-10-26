<!-- SPDX-License-Identifier: MIT -->
# Pixel 6 (oriole) bring-up notes

This is a community, experimental Pixel 6 port following the device descriptor and release layout used by Omarchy Mobile for the Pixel 7 Pro. The source snapshot records real tests on one unlocked test phone; it does not claim a daily driver or a complete installer.

## Current checkpoint

The phone has booted Linux B with systemd, Omarchy, Hyprland, hardware Mali-G78 rendering and an experimental touch input path. The B slot successful flag was set once with an off-device backup, a full partition comparison and a fresh read-only verification. A reboot acceptance is still pending.

Wi-Fi W2 brought up the GS101 PCIe path, BCM4389 firmware and `wlan0`; W3 fixes the join allocation contract and passes source-level ASan RED/GREEN tests and the exact kernel `W=1` build. A bounded diagnostic run then proved WPA association, DHCP, DNS, HTTPS API traffic and reconnect; the temporary radio state was torn down cleanly. Persistent desktop startup, timekeeping after cold boot, DMA confinement and the rest of the mobile network remain open. Cellular modem, voice, camera, suspend and thermal behavior remain open.

The association evidence is [wifi-w3-association-evidence](../../experiments/wifi-w3-association-evidence.json), with the gated plan in [wifi-w3-association-plan](../../experiments/wifi-w3-association-plan.json). The authorized network name, credentials, BSSID, MAC address and private serial logs are intentionally excluded.

The latest evidence is [oriole-bringup-2026.10.26.9](../../releases/oriole-bringup-2026.10.26.9.json). Private partition images, factory firmware, calibration, serial numbers, credentials and host logs are deliberately excluded.

## Device facts

- Codename: `oriole`; SoC: Google GS101; panel: 1080x2400.
- Boot images: `boot_b`, `vendor_boot_b`, `dtbo_b`; Android remains the recovery slot A.
- The storage guard keeps calibration and modem partitions read-only. Hardware experiments require a fresh private backup and a watchdog.
- Use the descriptor and overlay as source inputs. Do not flash this repository directly; the current snapshot is source and evidence, not a release bundle.
