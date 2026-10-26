# BCM4389 W2: firmware and interface checkpoint

This is a development runbook, not an automatic Wi-Fi installer. Read the
six-field plan and evidence JSON beside this file before replay. W2 passed
firmware boot, creation of `wlan0`, clean teardown, and a fresh serial check.
It did not test association, DHCP, DNS, API access, reconnect or suspend.

## Reproduce the source checks

The module comes from the `drivers/net/wireless/broadcom/brcm80211` subtree of
[Omarchy Mobile kernel commit 1cb4bd36](https://github.com/derekross/linux-omarchy-mobile/commit/1cb4bd36f3befa4f331bc4e08fe58becb41e4926).
No GS201 host, PMU or device-tree implementation is imported into Oriole.
The accompanying patch records differences against the captured installed
kernel sources; build from the pinned subtree, rather than assuming the patch
applies to another kernel revision.

Extract that subtree into a new directory, separate from the kernel source.
With `KERNEL_DIR`, `KERNEL_OUT` and `WIFI_SOURCE` set to the exact matching
kernel, its configured build output, and that extracted subtree:

```sh
make -C "$KERNEL_DIR" O="$KERNEL_OUT" ARCH=arm64 \
  CROSS_COMPILE=aarch64-linux-gnu- M="$WIFI_SOURCE" W=1 -j2 modules
python3 experiments/test-wifi-w2-source.py \
  experiments/wifi-w2-base "$WIFI_SOURCE/brcmfmac"
python3 experiments/test-wifi-w2-firmware-map.py
python3 experiments/test-wifi-w2-teardown.py
```

The actual decoder from the captured old source must fail the BCM4389 RAM
oracle (exit42); the pinned decoder must pass. The actual new chunker is
compiled with ASan/UBSan and exercised across the 4MiB BAR boundary. These
tests mock register reads; they do not prove hardware timing or DMA safety.

## Hardware gate

`serial-wifi-w2-trial.sh` is the exact bounded phone-side trial, not a host
connection tool. Do not run it against a graphical session or another device.
It requires the reviewed GS101 v4a overlay already loaded, unlocked modules
in diagnostic init, fresh verified off-device calibration backups, the
matching staged modules, and firmware symlinks verified from this phone's
stock image. Original firmware and calibration are not distributed here.

Start host-side serial capture before executing the trial. It arms a hardware
watchdog before driver load. It holds the endpoint with `driver_override`
until the base and vendor modules are loaded, then binds only `14e4:4441`.
The firmware loader path is temporary. Signed regulatory database validation
remains enabled. Unexpected channels169/173/177 were ignored by this kernel;
this warning remains recorded, not bypassed.

Expect firmware version20.101.90 and `wlan0`, then
`WIFI_W2_FIRMWARE_INTERFACE_PASS_NO_ASSOCIATION` and `WIFI_W2_CLEANED_rc_0`.
After completion, use a new serial invocation to verify: no brcmfmac/host/PHY,
no PCI devices, WLAN rail disabled, loader path and modprobe restored, and
watchdog descriptor closed. A shell success alone is insufficient.

Stop on firmware crash, storage error, kernel fault or teardown failure.
The teardown helper refuses to remove the host if endpoint unbind fails.
Do not force-unload after such a failure; keep the watchdog recovery path.
If recovery falls back to Android, take fresh calibration backups before
another radio trial. Never select factory reset as a debugging shortcut.

The current overlay does not confine DMA with a restricted pool. This trial
is development-only; default-on packaging requires a separate DMA decision.
`CONFIG_BRCMDBG=y`, but the tested module used the default zero debug mask;
do not enable broad debug MMIO/alias probes without a new review.

## Exit gate

W2's runtime gate passed. The pinned-source checkpatch run still reports one
one-element-array error, one missing-message warning on the raw diff and
12 style checks. This is not a clean upstream or production patch release.
The tested snapshot is preserved; association structure changes require
layout and length validation before W3. W3 still needs an authorized Wi-Fi network, a
bounded association/traffic/reconnect experiment, and explicit recovery.
The phone currently has no saved NetworkManager profiles. Keep this checkpoint
separate from a claim that Wi-Fi, cellular, voice or camera is usable.
