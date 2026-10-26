#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Fixture test for host preflight command and output redaction."""
from pathlib import Path
import os
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools/oriole-host-preflight"

with tempfile.TemporaryDirectory() as td:
    bindir = Path(td) / "bin"
    bindir.mkdir()
    for name, text in {
        "adb": "#!/bin/sh\nexit 0\n",
        "fastboot": "#!/bin/sh\nexit 0\n",
        "git": "#!/bin/sh\nexit 0\n",
        "clang": "#!/bin/sh\nexit 0\n",
        "aarch64-linux-gnu-gcc": "#!/bin/sh\nexit 0\n",
        "make": "#!/bin/sh\necho 'GNU Make 4.4'\n",
    }.items():
        path = bindir / name
        path.write_text(text)
        path.chmod(0o755)
    env = dict(os.environ, PATH=str(bindir) + os.pathsep + os.environ["PATH"],
               ORIOLE_CASE_CHECK="skip")
    result = subprocess.run([str(SCRIPT), "--all"], env=env,
                            text=True, capture_output=True, check=True)
    assert "PASS GNU make=4.4" in result.stdout
    assert "INFO build filesystem case check skipped" in result.stdout
    assert "IMEI" not in result.stdout and "SSID" not in result.stdout
print("PASS Oriole host preflight fixture")
