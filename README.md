# Omarchy Mobile on Pixel 6 (oriole)

This repository publishes the Pixel 6 native Omarchy port as a source and evidence snapshot. It follows the public Pixel 7 Pro project layout: a device descriptor under `device/oriole/`, a device package under `packages/`, isolated kernel/driver changes, dated evidence, and explicit gates before a feature is called usable.

**Status: experimental.** The phone has booted Linux B and reached an Omarchy/Hyprland desktop with Mali-G78 rendering. Touch input is experimental; a bounded diagnostic run now proves Wi-Fi association, DHCP, DNS, HTTPS and reconnect. Cellular data/voice, camera, suspend, thermal behavior, persistent graphical startup and a complete one-click installer remain unfinished. The repository does not contain proprietary firmware, calibration partitions, credentials, private logs or flashable images.

## What is here

- `device/oriole/`: Pixel 6 descriptor, overlay and current bring-up notes.
- `kernel/`: the minimal GS101 source/configuration boundary required for GPU, Wi-Fi, cellular and camera work; the checker rejects the GS201-oriented Omarchy tree.
- `packages/omamobile-device-oriole/`: conservative device package skeleton adapted to the GS101 layout.
- `drivers/`: GPL-licensed touchscreen source and the source changes under test.
- `experiments/`: six-field plans, source tests, build evidence and recovery records. Each result states what it proves and what it does not prove.
- `releases/`: dated checkpoint manifests. The latest is [oriole-bringup-2026.10.26.14](releases/oriole-bringup-2026.10.26.14.json).
- `tools/`: read-only collectors and guarded helpers. `tools/phone-network-smoke` checks a normal desktop boot for Wi-Fi, IPv4, route, DNS and HTTPS without printing credentials or radio identifiers. `tools/agent-network-smoke` checks the active Wi-Fi, USB-shared or cellular route against GitHub, Anthropic and npm endpoints so an Agent launch can distinguish missing hardware, routing, DNS and remote-service failures.

## Reproduce the offline checks

These commands exercise source contracts and do not touch a phone:

```sh
python3 experiments/test-boot-b1-decode.py
cc -O2 -Wall -Wextra -Werror experiments/boot-b2/omamobile-bootctl.c -o /tmp/omamobile-bootctl
python3 experiments/test-boot-b2-write.py /tmp/omamobile-bootctl
python3 experiments/test-cpu-m3-rate-guard.py
python3 experiments/test-wifi-w3-join.py experiments/wifi-w3-fixture/brcmfmac
python3 experiments/test-agent-network-smoke.py
```

A real hardware run needs the exact configured Linux kernel, the user's own factory image and private calibration backups. Read `AGENTS.md`, `CONTRIBUTING.md` and the relevant plan before any phone operation. Keep Android slot A as the recovery path and never flash an unsuffixed partition. The next network gate is [network-desktop-boot-plan](experiments/network-desktop-boot-plan.json); the diagnostic Wi-Fi result does not close it. After a normal desktop boot, run `omamobile-agent-network-smoke --attempts 3` to diagnose the route used by Agent tools; it does not configure Wi-Fi or print credentials.

## Evidence policy

The user journey is the acceptance oracle: boot, recover from a failed or interrupted experiment, reach the desktop, touch the UI, connect Wi-Fi and run a small Agent workload. Unit tests cover deterministic contracts; source/build checks cover the kernel boundary; hardware evidence covers only the stated run. A passing source test never upgrades an unverified camera, modem or network claim.

The touchscreen code retains upstream ST notices and GPL terms. Boot-control code retains its Apache-2.0 notice. See `LICENSE` and file SPDX headers for the applicable terms.

## Upstream references

- [Omarchy Mobile](https://github.com/derekross/omarchy-mobile), the Pixel 7 Pro reference layout.
- [GS101 mainline touchscreen source](https://github.com/m8l8th814n-eng/gs101-mainline/tree/850061c79264d018317e9f849701f165e138e20c/drivers/input/touchscreen/fts_spi).
- [Linux Omarchy Mobile kernel](https://github.com/derekross/linux-omarchy-mobile/tree/97a6b87a87cb0102a84d3996349801fccbed2bb6).
