#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
from pathlib import Path
import importlib.util
import tempfile

p = Path(__file__).resolve().parents[1] / 'tools/cpu-m3-rate-guard.py'
spec = importlib.util.spec_from_file_location('guard', p)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
with tempfile.TemporaryDirectory() as tmp:
    p = Path(tmp) / 'rate'
    p.write_text('750\n')
    assert m.change(p, 750, 10000) == 10000
    assert m.restore(p) == 'restored'
    assert p.read_text().strip() == '750'
    assert m.restore(p) == 'already-original'
    for value in ['7777', 'not-a-rate']:
        p.write_text(value)
        try:
            m.change(p, 750, 10000)
        except RuntimeError:
            pass
        else:
            raise AssertionError('Independent change overwritten')
        assert m.restore(p) == 'preserved-manual-change'
        assert p.read_text() == value
    for expected, target in [(0, 10000), (750, 0), (750, 10001)]:
        try:
            m.change(p, expected, target)
        except ValueError:
            pass
        else:
            raise AssertionError('Unreviewed value accepted')
print('PASS exact rate roundtrip, interruption restore, manual/malformed preservation')
