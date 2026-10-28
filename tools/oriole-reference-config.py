#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Read pinned Nura build settings as data, without executing APKBUILD."""
import re
import subprocess
import sys
from pathlib import Path

REVISION = 'a74e18dec7598f65cd504f0c75c10b8d7fc4422b'
PREFIX = 'device/testing/linux-postmarketos-gs101/'


def assignments(recipe, name):
    matches = re.findall(r'^' + re.escape(name) + r'="\n(.*?)\n"$', recipe, re.M | re.S)
    if len(matches) != 1:
        raise ValueError('Missing or ambiguous configuration block: ' + name)
    result = []
    for line in matches[0].splitlines():
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        if not re.fullmatch(r'CONFIG_[A-Z0-9_]+=(?:[ymn]|[0-9]+)', line):
            raise ValueError('Non-literal configuration assignment in ' + name)
        result.append(line)
    if not result:
        raise ValueError('Empty configuration block: ' + name)
    return result


def pinned_file(root, name):
    actual = subprocess.check_output(['git', '-C', str(root), 'rev-parse', 'HEAD'], text=True).strip()
    if actual != REVISION:
        raise ValueError('Nura revision mismatch')
    return subprocess.check_output(['git', '-C', str(root), 'show', REVISION + ':' + PREFIX + name], text=True)


def merge(base, extra):
    keys = {line.split('=', 1)[0] for line in extra}
    kept = []
    for line in base.splitlines():
        key = re.match(r'^(?:# )?(CONFIG_[A-Z0-9_]+)(?:=| is not set$)', line)
        if not key or key[1] not in keys:
            kept.append(line)
    return '\n'.join(kept + extra) + '\n'


if __name__ == '__main__':
    root = Path(sys.argv[1])
    recipe = pinned_file(root, 'APKBUILD')
    mode = sys.argv[2]
    if mode == 'base':
        output = Path(sys.argv[3])
        base = pinned_file(root, 'config-postmarketos-gs101.aarch64')
        with output.open('x') as f:
            f.write(merge(base, assignments(recipe, '_extra_config')))
    elif mode in ('_iommu_config', '_modem_config', '_audio_config', '_gps_config'):
        print('\n'.join(assignments(recipe, mode)))
    else:
        raise ValueError('Unknown configuration mode')
