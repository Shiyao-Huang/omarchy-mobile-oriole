#!/usr/bin/env python3
import hashlib
import importlib.util
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

p = Path(__file__).resolve().parents[1] / 'tools/stage-wifi-w2-firmware.py'
spec = importlib.util.spec_from_file_location('fw', p)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
with tempfile.TemporaryDirectory() as td:
    root = Path(td)
    src = root / 'stock'
    src.mkdir()
    expected = {}
    for i, (name, (suffix, _)) in enumerate(m.EXPECTED.items()):
        b = ('synthetic-component-' + str(i)).encode()
        (src / name).write_bytes(b)
        expected[name] = (suffix, hashlib.sha256(b).hexdigest())
    dst = root / 'map'
    wrong = dict(expected)
    wrong['bcmdhd.cal'] = ('.txt', '0' * 64)
    try:
        m.stage(src, dst, wrong)
    except ValueError:
        assert not dst.exists()
    else:
        raise AssertionError('Mismatched calibration accepted')
    for board in ('google,gs201-cheetah', '../bad'):
        try:
            m.stage(src, dst, expected, board)
        except ValueError:
            assert not dst.exists()
        else:
            raise AssertionError('Wrong board accepted')
    original = os.symlink
    count = 0
    def fail_second(a, b):
        global count
        count += 1
        if count == 2:
            raise OSError('injected link failure')
        return original(a, b)
    with patch.object(m.os, 'symlink', fail_second):
        try:
            m.stage(src, dst, expected)
        except OSError:
            assert not dst.exists()
        else:
            raise AssertionError('Fault injection did not fire')
    links = m.stage(src, dst, expected)
    assert len(links) == 3
    for link in map(Path, links):
        assert link.is_symlink() and not os.readlink(link).startswith('/')
        assert link.resolve().parent == src.resolve()
    saved = {x.name: x.read_bytes() for x in src.iterdir()}
    try:
        m.stage(src, dst, expected)
    except FileExistsError:
        assert all(x.read_bytes() == saved[x.name] for x in src.iterdir())
    else:
        raise AssertionError('Existing target overwritten')
    # The same relative map resolves when mounted below /newroot.
    moved = root / 'mounted'
    moved.mkdir()
    src.rename(moved / 'stock')
    dst.rename(moved / 'map')
    for link in (moved / 'map/brcm').iterdir():
        assert link.resolve().parent == (moved / 'stock').resolve()
print('PASS digest/board guards, partial-failure rollback, existing-path preservation and init/root-relative mapping')
