#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Read-only Oriole hardware presence snapshot."""
import json
import os
from pathlib import Path

SYS = Path(os.environ.get("ORIOLE_SYS_ROOT", "/sys"))
DEV = Path(os.environ.get("ORIOLE_DEV_ROOT", "/dev"))
PROC = Path(os.environ.get("ORIOLE_PROC_ROOT", "/proc"))

def read(path):
    try:
        return path.read_text().strip("\x00\n ")
    except (OSError, UnicodeError):
        return None

def names(pattern):
    return sorted(p.name for p in pattern.parent.glob(pattern.name))

def symlink_target(path):
    try:
        return path.resolve().name
    except OSError:
        return None

net_root = SYS / "class/net"
interfaces = names(net_root / "*") if net_root.exists() else []
wireless = [name for name in interfaces if (net_root / name / "wireless").exists()]
cellular = [name for name in interfaces if name.startswith(("wwan", "rmnet", "ccmni", "pdp"))]
usb_or_ethernet = [name for name in interfaces if name.startswith(("usb", "en", "eth"))]

drm = SYS / "class/drm"
drm_drivers = {}
if drm.exists():
    for driver in drm.glob("card*/device/driver"):
        target = symlink_target(driver)
        if target:
            drm_drivers[driver.parents[1].name] = target

governors = {}
cpufreq = SYS / "devices/system/cpu/cpufreq"
if cpufreq.exists():
    for policy in sorted(cpufreq.glob("policy*")):
        value = read(policy / "scaling_governor")
        if value:
            governors[policy.name] = value

input_root = SYS / "class/input"
touch_names = []
if input_root.exists():
    touch_names = sorted(value for value in (read(path / "name") for path in input_root.glob("input*/")) if value)

data = {
    "schema_version": 1,
    "interpretation": "Observed presence only; functional acceptance is separate.",
    "gpu": {
        "render_nodes": names(DEV / "dri" / "renderD*"),
        "drm_drivers": drm_drivers,
        "devfreq_current_hz": read(SYS / "class/devfreq/1c500000.gpu/cur_freq"),
        "devfreq_max_hz": read(SYS / "class/devfreq/1c500000.gpu/max_freq"),
    },
    "cpu": {
        "online": read(SYS / "devices/system/cpu/online"),
        "governors": governors,
        "schedutil_rate_limit_us": read(SYS / "devices/system/cpu/cpufreq/schedutil/rate_limit_us"),
        "rt_uclamp_min": read(PROC / "sys/kernel/sched_util_clamp_min_rt_default"),
        "loadavg": read(PROC / "loadavg"),
    },
    "network": {
        "interfaces": interfaces,
        "wireless": wireless,
        "cellular_candidates": cellular,
        "usb_or_ethernet": usb_or_ethernet,
    },
    "cellular": {
        "control_nodes": names(DEV / "cdc-wdm*"),
        "serial_candidates": names(DEV / "ttyUSB*") + names(DEV / "ttyACM*"),
    },
    "camera": {
        "video_nodes": names(DEV / "video*"),
        "media_nodes": names(DEV / "media*"),
    },
    "input": {
        "event_nodes": names(DEV / "input" / "event*"),
        "touch_names": touch_names,
    },
    "limits": [
        "No modules, radios, routes, camera frames or GPU jobs are started.",
        "No SSID, MAC, IMEI, serial number or credential is emitted.",
        "Device-node presence does not prove cellular registration, camera capture or smooth frames.",
    ],
}
print(json.dumps(data, indent=2, sort_keys=True))
