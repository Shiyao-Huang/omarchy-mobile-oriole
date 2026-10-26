#!/usr/bin/env python3
"""Read-only Pixel6 bringup snapshot; presence is never functional acceptance."""
import json
import platform
import subprocess
from pathlib import Path


def read(path):
    try:
        return Path(path).read_text().strip('\x00\n ')
    except (OSError, UnicodeError):
        return None


def run(args):
    try:
        p = subprocess.run(args, capture_output=True, text=True, timeout=8)
        return p.stdout if p.returncode == 0 else None
    except (OSError, subprocess.TimeoutExpired):
        return None


names = [read(p) for p in Path('/sys/class/input').glob('input*/name')]
log = run(['dmesg'])
marks = None if log is None else [
    line for line in log.splitlines()
    if 'INPUT30_READY' in line or 'INPUT30_END' in line
    or 'INPUT30 ready guard reached' in line
][-5:]
monitors_raw = run(['runuser', '-u', 'agent', '--', 'env',
                    'XDG_RUNTIME_DIR=/run/user/1000', 'hyprctl', '-i', '0',
                    'monitors', '-j'])
try:
    monitors = [{k: m.get(k) for k in ['width', 'height', 'scale', 'dpmsStatus']}
                for m in json.loads(monitors_raw)] if monitors_raw else None
except (TypeError, ValueError):
    monitors = None
out = {
    'schema_version': 1,
    'interpretation': 'Observed presence only; functional acceptance is separate.',
    'kernel': platform.release(),
    'touch': {
        'polling_device_present': 'Oriole polling touchscreen' in names,
        'module_session_seconds': read('/sys/module/oriole_touch_minimal/parameters/session_seconds'),
        'lifecycle_markers': marks,
    },
    'graphics': {
        'gpu_dt_status': read('/sys/firmware/devicetree/base/soc@0/gpu@1c500000/status'),
        'render_nodes': sorted(p.name for p in Path('/dev/dri').glob('renderD*')),
        'card_drivers': {p.parents[1].name: p.resolve().name for p in
                         Path('/sys/class/drm').glob('card*/device/driver')},
        'monitors': monitors,
    },
    'network_interface_names': sorted(p.name for p in Path('/sys/class/net').iterdir()),
    'camera_device_nodes': sorted(p.name for pattern in ['video*', 'media*']
                                  for p in Path('/dev').glob(pattern)),
    'modules_disabled': read('/proc/sys/kernel/modules_disabled'),
    'limits': ['No network packet/association test', 'No camera frame test',
               'No screen latency/FPS test', 'No boot persistence proof',
               'No user-identifying fields are emitted'],
}
print(json.dumps(out, indent=2))
