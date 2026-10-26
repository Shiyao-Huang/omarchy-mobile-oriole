#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Fixture tests for the explicit NetworkManager recovery wrapper."""
from pathlib import Path
import os
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools/omamobile-network-recover"

with tempfile.TemporaryDirectory() as td:
    root = Path(td)
    bindir = root / "bin"
    bindir.mkdir()
    state = root / "state"
    state.write_text("disconnected\n")
    calls = root / "calls"
    calls.write_text("")

    def write(name, body):
        path = bindir / name
        path.write_text("#!/bin/sh\n" + body + "\n")
        path.chmod(0o755)

    write("nmcli", f'''printf '%s\\n' "$*" >> {calls}
case "$*" in
*"device status"*)
  if grep -q connected {state}; then echo "wlan0:wifi:connected:"; else echo "wlan0:wifi:disconnected:"; fi ;;
*"device connect wlan0"*) echo connected > {state} ;;
*) exit 0 ;;
esac''')
    write("ip", "exit 0")
    tool_dir = root / "tools"
    tool_dir.mkdir()
    (tool_dir / "omamobile-network-recover").write_text(SCRIPT.read_text())
    (tool_dir / "omamobile-network-recover").chmod(0o755)
    (tool_dir / "agent-network-smoke").write_text(
        "#!/bin/sh\nprintf 'PASS Agent network smoke test\\n'\n"
    )
    (tool_dir / "agent-network-smoke").chmod(0o755)
    env = dict(os.environ, PATH=str(bindir) + os.pathsep + os.environ["PATH"])
    result = subprocess.run(
        [str(tool_dir / "omamobile-network-recover"), "--reconnect", "wifi"],
        env=env, text=True, capture_output=True, check=True,
    )
    assert "PASS NetworkManager accepted reconnect transport=wifi" in result.stdout
    assert "PASS Agent network smoke test" in result.stdout
    assert "SSID" not in result.stdout and "MAC" not in result.stdout
    assert "device connect" in calls.read_text()

    calls.write_text("")
    result = subprocess.run(
        [str(tool_dir / "omamobile-network-recover"), "--check"],
        env=env, text=True, capture_output=True, check=True,
    )
    assert "PASS Agent network smoke test" in result.stdout
    assert "device connect" not in calls.read_text()
print("PASS explicit NetworkManager recovery fixture")
