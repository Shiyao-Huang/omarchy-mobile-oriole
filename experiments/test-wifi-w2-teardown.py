#!/usr/bin/env python3
"""Fault-inject every teardown boundary; later operations must not run."""
from pathlib import Path
import subprocess
import tempfile

source = Path(__file__).with_name('wifi-w2-teardown.sh').read_text()
steps = ['endpoint_unbind', 'endpoint_unbound', 'radio_unload',
         'host_unload', 'phy_unload', 'rail_off']
for failing in [None] + steps:
    script = source + '\n'
    for step in steps:
        script += 'wifi_' + step + '() { echo ' + step + '; return ' + str(int(step == failing)) + '; }\n'
    result = subprocess.run(['sh'], input=script+'wifi_w2_teardown\n', text=True, capture_output=True)
    expected = steps if failing is None else steps[:steps.index(failing)+1]
    assert result.stdout.splitlines() == expected, (failing, result)
    assert result.returncode == int(failing is not None), (failing, result)
print('PASS six teardown fault boundaries; no host removal after unbind failure')
