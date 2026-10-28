#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Pinned AoC C compatibility fixes; no phone access or firmware changes."""
import hashlib
import sys
from pathlib import Path

HASHES = {
    'aoc/aoc_ramdump_regions.h': 'cbb03b02e316b34dfae5a655f4a9c320343884ac379c8e9a939a5376a11d7321',
    'aoc/alsa/aoc_alsa_hw.c': '548809a9e4a8873a25a27e97b9c8c0883705feb86e3b8ff45550ad6263488f74',
}


def transform(files):
    for name, digest in HASHES.items():
        if hashlib.sha256(files[name].encode()).hexdigest() != digest:
            raise ValueError('Unexpected pinned AoC source: ' + name)
    result = dict(files)
    header = files['aoc/aoc_ramdump_regions.h']
    for name, kind in [('core_ramdump_status', 'u32'), ('ramdump_section_type', 'u32'),
                       ('ramdump_section_flag', 'u32'), ('RamdumpPlatform', 'uint32_t')]:
        header = header.replace('enum ' + name + ' : ' + kind + ' {', 'enum ' + name + ' {')
    # Keep firmware-facing storage explicitly 32-bit even with short enums.
    header = header.replace('enum ramdump_section_type type;', 'u32 type; /* enum ramdump_section_type */')
    header = header.replace('enum RamdumpPlatform platform;', 'u32 platform; /* enum RamdumpPlatform */')
    result['aoc/aoc_ramdump_regions.h'] = header
    source = files['aoc/alsa/aoc_alsa_hw.c']
    source = source.replace('#include <linux/uio.h>', '#include <linux/uio.h>\n#include <linux/string.h>')
    source = source.replace('cmd.coeffs[i] = *(float *)(&tmp);', 'memcpy(&cmd.coeffs[i], &tmp, sizeof(tmp));')
    result['aoc/alsa/aoc_alsa_hw.c'] = source
    return result


if __name__ == '__main__':
    root = Path(sys.argv[1])
    result = transform({name: (root/name).read_text() for name in HASHES})
    for name, content in result.items():
        (root/name).write_text(content)
    print('PASS pinned AoC compatibility transform; hardware unverified')
