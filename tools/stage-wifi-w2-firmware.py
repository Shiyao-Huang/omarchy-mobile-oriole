#!/usr/bin/env python3
"""Create a private BCM4389 filename map; never select the firmware loader path."""
import argparse
import hashlib
import os
from pathlib import Path

BOARD = 'google,gs101-oriole'
EXPECTED = {
    'fw_bcmdhd.bin': ('.bin', '8a52ffe1d71d29f3729247a31be912ff9e9b9959effa36fe94f2e3f5cccf916b'),
    'bcmdhd.cal': ('.txt', 'b369f94cf7b8c8534c3e955bcca4c7297043c12b0759ee1dffc66133c350da4f'),
    'bcmdhd_clm.blob': ('.clm_blob', '70b790397a3d6b952821d2459e19ae9c0e69a7f61392204e4e6dd7378fa0abf1'),
}


def stage(source, target, expected=EXPECTED, board=BOARD):
    if board != BOARD:
        raise ValueError('This firmware map is for verified Oriole stock files only')
    source, target = Path(source), Path(target)
    if target.exists() or target.is_symlink():
        raise FileExistsError('Preserve existing firmware map')
    entries = []
    for name, (suffix, digest) in expected.items():
        if name not in EXPECTED or suffix != EXPECTED[name][0]:
            raise ValueError('Unexpected firmware name')
        p = source / name
        if p.is_symlink() or not p.is_file():
            raise ValueError('Firmware source must be a regular file')
        if hashlib.sha256(p.read_bytes()).hexdigest() != digest:
            raise ValueError('Firmware digest mismatch: ' + name)
        entries.append((p.resolve(), 'brcmfmac4389c1-pcie.' + board + suffix))
    if set(expected) != set(EXPECTED):
        raise ValueError('Require all three verified firmware components')
    target.mkdir(mode=0o755)
    links = []
    brcm = target / 'brcm'
    try:
        brcm.mkdir(mode=0o755)
        for src, name in entries:
            link = brcm / name
            relative = os.path.relpath(src, brcm.resolve())
            os.symlink(relative, link)
            links.append((link, relative))
        for src, name in entries:
            if (brcm / name).resolve() != src:
                raise RuntimeError('Firmware link resolution mismatch')
    except BaseException:
        # Remove only links created by this attempt and still unchanged.
        for link, relative in reversed(links):
            if link.is_symlink() and os.readlink(link) == relative:
                link.unlink()
        for directory in (brcm, target):
            try:
                directory.rmdir()
            except OSError:
                pass  # Preserve any concurrent/manual contents.
        raise
    return [str(brcm / name) for _, name in entries]


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('source', type=Path)
    ap.add_argument('target', type=Path)
    args = ap.parse_args()
    for path in stage(args.source, args.target):
        print(path)
