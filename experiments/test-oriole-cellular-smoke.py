#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Fixture test for the read-only cellular state probe."""
from pathlib import Path
import os
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools/oriole-cellular-smoke"

with tempfile.TemporaryDirectory() as td:
    bindir = Path(td) / "bin"
    bindir.mkdir()
    mmcli = bindir / "mmcli"
    mmcli.write_text("""#!/bin/sh
case "$*" in
  *--list-modems*) echo '/org/freedesktop/ModemManager1/Modem/0' ;;
  *'--modem 0'*) cat <<'KV'
modem.generic.state: 'registered'
modem.3gpp.registration-state: 'home'
modem.generic.access-technologies: 'lte'
modem.3gpp.packet-service-state: 'attached'
modem.generic.bearers: '/org/freedesktop/ModemManager1/Bearer/0'
modem.3gpp.imei: 'must-not-print'
KV
    ;;
  *'--bearer 0'*) echo "bearer.status.connected: 'yes'" ;;
  *) exit 1 ;;
esac
""")
    mmcli.chmod(0o755)
    env = dict(os.environ, PATH=str(bindir) + os.pathsep + os.environ["PATH"])
    result = subprocess.run([str(SCRIPT)], env=env, text=True,
                            capture_output=True, check=True)
    assert "PASS cellular registration and bearer present" in result.stdout
    assert "access=lte" in result.stdout
    assert "must-not-print" not in result.stdout

    mmcli.write_text("""#!/bin/sh
if echo "$*" | grep -q -- '--list-modems'; then
  echo '/org/freedesktop/ModemManager1/Modem/0'
elif echo "$*" | grep -q -- '--modem 0'; then
  echo "modem.3gpp.registration-state: 'searching'"
else
  exit 1
fi
""")
    result = subprocess.run([str(SCRIPT)], env=env, text=True,
                            capture_output=True)
    assert result.returncode == 4
    assert "FAIL cellular registration unavailable" in result.stdout
print("PASS cellular registration/bearer probe and redaction fixtures")
