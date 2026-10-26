#!/usr/bin/env python3
"""Backport upstream 8a597d099b8b onto the exact captured G7 MMU source."""
import hashlib
import sys
from pathlib import Path

BASE_SHA = '57f03c626bdef56726bbe14ea6fd36e1229761688ddfd8da6ec3b5ec2851e1b2'


def transform(source):
    if hashlib.sha256(source.encode()).hexdigest() != BASE_SHA:
        raise ValueError('Unexpected G7 MMU source; refusing fuzzy application')
    writes = '\tmmu_write(pfdev, MMU_INT_CLEAR, ~0);\n\tmmu_write(pfdev, MMU_INT_MASK, ~0);'
    assert source.count(writes) == 1
    result = source.replace(writes, '\tpanfrost_mmu_enable_interrupts(pfdev);')
    anchor = 'void panfrost_mmu_reset(struct panfrost_device *pfdev)'
    helper = 'static void panfrost_mmu_enable_interrupts(struct panfrost_device *pfdev)\n{\n' + writes + '\n}\n\n'
    assert result.count(anchor) == 1
    result = result.replace(anchor, helper + anchor)
    start = result.index('int panfrost_mmu_init(')
    end = result.index('\nvoid panfrost_mmu_fini(', start)
    init = result[start:end]
    assert init.count('\treturn 0;') == 1
    result = result[:start] + init.replace('\treturn 0;', '\tpanfrost_mmu_enable_interrupts(pfdev);\n\n\treturn 0;') + result[end:]
    return result


if __name__ == '__main__':
    src, dst = map(Path, sys.argv[1:])
    if dst.exists():
        raise FileExistsError(dst)
    dst.write_text(transform(src.read_text()))
