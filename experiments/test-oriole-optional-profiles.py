#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Check optional Oriole profiles for safe, public configuration only."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
base = ROOT / "packages/omamobile-device-oriole/optional"
required = [
    base / "wifi/90-bcmdhd-unmanaged.conf",
    base / "camera/oriole-camera.modules-load",
    base / "camera/oriole-camera.modprobe",
    base / "camera/90-oriole-camera.rules",
    base / "camera/90-oriole-camera.wireplumber.conf",
    base / "performance/90-oriole-sched.conf",
    base / "performance/oriole-cpufreq-ratelimit.service",
]
for path in required:
    assert path.is_file(), path
    text = path.read_text()
    assert "password" not in text.lower()
    assert "ssid" not in text.lower()
    assert "imei" not in text.lower()
assert "unmanaged-devices=interface-name:wlan1" in (base / "wifi/90-bcmdhd-unmanaged.conf").read_text()
assert "blacklist s5kg" in (base / "camera/oriole-camera.modprobe").read_text()
assert "rate_limit_us" in (base / "performance/oriole-cpufreq-ratelimit.service").read_text()
print("PASS Oriole optional Wi-Fi, camera and performance profiles")
