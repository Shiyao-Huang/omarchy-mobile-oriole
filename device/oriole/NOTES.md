<!-- SPDX-License-Identifier: MIT -->
# Pixel 6 (oriole) bring-up notes

This is a community, experimental Pixel 6 port following the device descriptor and release layout used by Omarchy Mobile for the Pixel 7 Pro. The source snapshot records real tests on one unlocked test phone; it does not claim a daily driver or a complete installer.

## Current checkpoint

The phone has booted Linux B with systemd, Omarchy, Hyprland, hardware Mali-G78 rendering and an experimental touch input path. The B slot successful flag was set once with an off-device backup, a full partition comparison and a fresh read-only verification. A reboot acceptance is still pending.

Wi-Fi W2 brought up the GS101 PCIe path, BCM4389 firmware and `wlan0`; W3 fixes the join allocation contract and passes source-level ASan RED/GREEN tests and the exact kernel `W=1` build. A bounded diagnostic run then proved WPA association, DHCP, DNS, HTTPS API traffic and reconnect; the temporary radio state was torn down cleanly. Persistent desktop startup, timekeeping after cold boot, DMA confinement and the rest of the mobile network remain open. Cellular modem, voice, camera, suspend and thermal behavior remain open.

The association evidence is [wifi-w3-association-evidence](../../experiments/wifi-w3-association-evidence.json), with the gated plan in [wifi-w3-association-plan](../../experiments/wifi-w3-association-plan.json). The authorized network name, credentials, BSSID, MAC address and private serial logs are intentionally excluded.

The device package now includes a read-only Agent connectivity probe. It reports the active transport (Wi-Fi, USB-shared or cellular), IPv4, route, DNS and HTTPS reachability for the public GitHub, Anthropic and npm endpoints, with bounded retries. This diagnoses the failure layer behind Agent installers such as mise without configuring a network or exposing credentials. It is a userspace diagnostic only; it does not close the cold Omarchy desktop gate.

The package also includes `omamobile-network-recover`. Its default `--check` path is read-only. An explicit `--reconnect wifi|usb|cellular` retries only an existing NetworkManager device and then delegates to the same Agent probe; it does not create profiles or handle credentials. This gives the normal desktop a bounded recovery step after a transient link loss while keeping Wi-Fi association, cellular bearer and cold-boot acceptance as separate hardware gates.

The optional profiles under `packages/omamobile-device-oriole/optional/` carry the Pixel 6 reference fixes for BCM4389 helper-interface isolation, the libcamera system dma-buf heap/raw-CSIS policy, the unusable GN1 blacklist, and the ACPM schedutil update limit. They are staged under `/usr/share/omamobile/device-oriole/optional/` and remain inactive until the corresponding cold-boot, camera and thermal gates are approved.

`oriole-optional-profile --apply wifi|camera|performance` copies one profile into the normal system configuration and records a backup; `--rollback` restores the newest backup. It never reloads a module or restarts a service, so the operator can arm a watchdog and validate one change per boot.

The source boundary is now explicit: the current Omarchy kernel head is rejected for Oriole because it lacks the Pixel 6 GS101 driver baseline. `tools/check-oriole-kernel-source` accepts M8's `850061c7` tree only when the GS101 DRM/Panfrost, BCM4389 PCIe, CPIF modem and MIPI-CSIS/IMX355/IMX386 paths are present. The corresponding configuration fragment is kept under `kernel/configs/`; this source check does not build or boot a phone.

The latest evidence is [oriole-bringup-2026.10.26.19](../../releases/oriole-bringup-2026.10.26.19.json). Private partition images, factory firmware, calibration, serial numbers, credentials and host logs are deliberately excluded.

## Device facts

- Codename: `oriole`; SoC: Google GS101; panel: 1080x2400.
- Boot images: `boot_b`, `vendor_boot_b`, `dtbo_b`; Android remains the recovery slot A.
- The storage guard keeps calibration and modem partitions read-only. Hardware experiments require a fresh private backup and a watchdog.
- Use the descriptor and overlay as source inputs. Do not flash this repository directly; the current snapshot is source and evidence, not a release bundle.
