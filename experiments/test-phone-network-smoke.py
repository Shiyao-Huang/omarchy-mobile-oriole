#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Fixture tests for the read-only Wi-Fi network smoke command."""
from pathlib import Path
import os
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools/phone-network-smoke"

with tempfile.TemporaryDirectory() as td:
    root = Path(td)
    bindir = root / "bin"
    bindir.mkdir()
    wireless = root / "sys/class/net/wlan0/wireless"
    wireless.mkdir(parents=True)
    (root / "sys/class/net/wlan0/operstate").write_text("up\n")
    def write(name, body):
        path = bindir / name
        path.write_text("#!/bin/sh\n" + body + "\n")
        path.chmod(0o755)

    write("ip", """
if [ "$1" = "-4" ] && [ "$2" = "addr" ]; then
  echo 'inet 192.0.2.10/24 scope global wlan0'
elif [ "$1" = "-4" ] && [ "$2" = "route" ]; then
  echo 'default via 192.0.2.1 dev wlan0'
else
  exit 2
fi
""")
    write("getent", "[ \"$1\" = ahosts ] && exit 0; exit 2")
    write("curl", "exit 0")
    env = dict(os.environ, PATH=str(bindir) + os.pathsep + os.environ["PATH"],
               ORIOLE_SYS_ROOT=str(root / "sys"))
    result = subprocess.run([str(SCRIPT)], env=env, text=True,
                            capture_output=True, check=True)
    assert "PASS wireless IPv4 address present" in result.stdout
    assert "PASS network smoke test" in result.stdout

    write("ip", """
if [ "$1" = "-4" ]; then exit 0
elif [ "$1" = "-6" ] && [ "$2" = "addr" ]; then
  echo 'inet6 2001:db8::10/64 scope global wlan0'
elif [ "$1" = "-6" ] && [ "$2" = "route" ]; then
  echo 'default via 2001:db8::1 dev wlan0'
else exit 2; fi
""")
    result = subprocess.run([str(SCRIPT)], env=env, text=True,
                            capture_output=True, check=True)
    assert "PASS wireless IPv6 address present" in result.stdout
print("PASS Wi-Fi smoke IPv4/IPv6 fixture")
