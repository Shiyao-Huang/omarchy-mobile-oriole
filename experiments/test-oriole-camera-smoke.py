#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Fixture test for read-only Oriole camera topology classification."""
from pathlib import Path
import os
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools/oriole-camera-smoke"

with tempfile.TemporaryDirectory() as td:
    sys = Path(td) / "sys"
    (sys / "class/video4linux/video0").mkdir(parents=True)
    (sys / "class/video4linux/video0/name").write_text("GS101 IMX355 capture\n")
    (sys / "class/media/media0").mkdir(parents=True)
    env = dict(os.environ, ORIOLE_SYS_ROOT=str(sys))
    result = subprocess.run([str(SCRIPT)], env=env, text=True,
                            capture_output=True, check=True)
    assert "sensor=front-imx355" in result.stdout
    assert "PASS supported camera topology present" in result.stdout

    (sys / "class/video4linux/video0/name").write_text("GS101 S5KGN1 capture\n")
    result = subprocess.run([str(SCRIPT)], env=env, text=True,
                            capture_output=True)
    assert result.returncode == 4
    assert "main-gn1-unsupported" in result.stdout
print("PASS camera topology classification fixture")
