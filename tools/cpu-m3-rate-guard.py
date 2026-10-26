#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Task-scoped compare-before-write for the observed global schedutil rate."""
from pathlib import Path
import sys

RATE = Path('/sys/devices/system/cpu/cpufreq/schedutil/rate_limit_us')


def change(path, expected, target):
    if expected not in (750, 10000) or target not in (750, 10000):
        raise ValueError('Unreviewed rate')
    path = Path(path)
    if path.read_text().strip() != str(expected):
        raise RuntimeError('Rate changed independently; preserve it')
    path.write_text(str(target) + '\n')
    if path.read_text().strip() != str(target):
        raise RuntimeError('Rate readback mismatch')
    return target


def restore(path):
    value = Path(path).read_text().strip()
    if value == '10000':
        change(path, 10000, 750)
        return 'restored'
    return 'already-original' if value == '750' else 'preserved-manual-change'


if __name__ == '__main__':
    if sys.argv[1:] == ['candidate']:
        print(change(RATE, 750, 10000))
    elif sys.argv[1:] == ['original']:
        print(change(RATE, 10000, 750))
    elif sys.argv[1:] == ['restore']:
        print(restore(RATE))
    else:
        raise SystemExit('Use candidate, original or restore')
