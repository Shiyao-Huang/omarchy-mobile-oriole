#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Fixture test for the read-only hardware presence snapshot."""
import json
import os
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools/oriole-hardware-smoke.py"

with tempfile.TemporaryDirectory() as td:
    root = Path(td)
    sys = root / "sys"
    dev = root / "dev"
    (sys / "class/net/wlan0/wireless").mkdir(parents=True)
    (sys / "class/net/usb0").mkdir(parents=True)
    (sys / "devices/system/cpu/cpufreq/policy0").mkdir(parents=True)
    (sys / "devices/system/cpu/cpufreq/policy0/scaling_governor").write_text("schedutil\n")
    (sys / "devices/system/cpu/online").parent.mkdir(parents=True, exist_ok=True)
    (sys / "devices/system/cpu/online").write_text("0-7\n")
    (dev / "dri").mkdir(parents=True)
    (dev / "dri/renderD128").touch()
    (dev / "cdc-wdm0").touch()
    (dev / "video0").touch()
    (dev / "media0").touch()
    (dev / "input").mkdir()
    (dev / "input/event0").touch()
    env = dict(os.environ, ORIOLE_SYS_ROOT=str(sys), ORIOLE_DEV_ROOT=str(dev))
    result = subprocess.run(["python3", str(SCRIPT)], env=env, text=True,
                            capture_output=True, check=True)
    data = json.loads(result.stdout)
    assert data["gpu"]["render_nodes"] == ["renderD128"]
    assert data["network"]["wireless"] == ["wlan0"]
    assert data["network"]["usb_or_ethernet"] == ["usb0"]
    assert data["cellular"]["control_nodes"] == ["cdc-wdm0"]
    assert data["camera"]["video_nodes"] == ["video0"]
    assert data["camera"]["media_nodes"] == ["media0"]
    assert data["cpu"]["governors"]["policy0"] == "schedutil"
print("PASS Oriole hardware snapshot fixture and redaction")
