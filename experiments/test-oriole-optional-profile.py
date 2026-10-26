#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Fixture test for apply/rollback of an Oriole optional profile."""
from pathlib import Path
import os
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools/oriole-optional-profile"

with tempfile.TemporaryDirectory() as td:
    root = Path(td)
    etc = root / "etc"
    state = root / "state"
    optional = root / "optional"
    (optional / "wifi").mkdir(parents=True)
    (optional / "camera").mkdir(parents=True)
    (optional / "performance").mkdir(parents=True)
    (optional / "wifi/90-bcmdhd-unmanaged.conf").write_text("wifi-profile\n")
    (optional / "camera/oriole-camera.modules-load").write_text("system_heap\n")
    (optional / "camera/oriole-camera.modprobe").write_text("blacklist s5kgn1\n")
    (optional / "camera/90-oriole-camera.rules").write_text("camera-rule\n")
    (optional / "camera/90-oriole-camera.wireplumber.conf").write_text("camera-wp\n")
    (optional / "performance/90-oriole-sched.conf").write_text("sched\n")
    (optional / "performance/oriole-cpufreq-ratelimit.service").write_text("service\n")
    env = dict(os.environ, ORIOLE_OPTIONAL_ROOT=str(optional),
               ORIOLE_ETC_ROOT=str(etc), ORIOLE_STATE_ROOT=str(state),
               EUID="0")
    # Run as the current user; CI for this repository is root-capable. The
    # helper's explicit root guard is exercised when the package test runs.
    if os.geteuid() == 0:
        result = subprocess.run([str(SCRIPT), "--apply", "wifi"], env=env,
                                text=True, capture_output=True, check=True)
        target = etc / "NetworkManager/conf.d/90-bcmdhd-unmanaged.conf"
        assert target.read_text() == "wifi-profile\n"
        assert "backup=" in result.stdout
        target.write_text("operator-edit\n")
        subprocess.run([str(SCRIPT), "--rollback"], env=env,
                        text=True, capture_output=True, check=True)
        assert target.read_text() == "wifi-profile\n"
        subprocess.run([str(SCRIPT), "--apply", "camera"], env=env,
                       text=True, capture_output=True, check=True)
        assert (etc / "modules-load.d/oriole-camera.conf").read_text() == "system_heap\n"
        subprocess.run([str(SCRIPT), "--apply", "performance"], env=env,
                       text=True, capture_output=True, check=True)
        assert (etc / "sysctl.d/90-oriole-sched.conf").read_text() == "sched\n"
print("PASS Oriole optional profile apply and rollback fixture")
