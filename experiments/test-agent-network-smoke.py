#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Exercise the read-only Agent connectivity probe with command fixtures."""
from pathlib import Path
import os
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools/agent-network-smoke"

def write_bin(directory, name, body):
    path = directory / name
    path.write_text("#!/bin/sh\n" + body + "\n")
    path.chmod(0o755)

with tempfile.TemporaryDirectory() as td:
    root = Path(td)
    fakebin = root / "bin"
    fakebin.mkdir()
    net = root / "sys/class/net/wlan0"
    net.mkdir(parents=True)
    (net / "operstate").write_text("up\n")
    write_bin(fakebin, "ip", """
if [ "$1" = "-4" ] && [ "$2" = "route" ]; then
  echo 'default via 192.0.2.1 dev wlan0 proto dhcp'
elif [ "$1" = "-4" ] && [ "$2" = "addr" ]; then
  echo '    inet 192.0.2.10/24 scope global wlan0'
else
  exit 2
fi
""")
    write_bin(fakebin, "getent", """[ "$1" = ahostsv4 ] && exit 0; exit 2""")
    write_bin(fakebin, "curl", """printf 401""")
    env = dict(os.environ, PATH=str(fakebin) + os.pathsep + os.environ["PATH"])
    result = subprocess.run([str(SCRIPT)], env=env, text=True, capture_output=True)
    assert result.returncode == 0, result.stderr + result.stdout
    assert "PASS Agent network smoke test" in result.stdout
    assert "transport=wifi" in result.stdout
    assert "SSID" not in result.stdout and "MAC" not in result.stdout

    write_bin(fakebin, "curl", """exit 1""")
    result = subprocess.run([str(SCRIPT), "--attempts", "2", "--delay", "0"], env=env,
                            text=True, capture_output=True)
    assert result.returncode != 0
    assert "FAIL HTTPS transport" in result.stdout
print("PASS Agent connectivity probe success, retry failure and redaction fixtures")
