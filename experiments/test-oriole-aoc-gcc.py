#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Compile real transformed wire declarations and coefficient copy."""
import importlib.util
import subprocess
import sys
import tempfile
from pathlib import Path

repo = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location('aoc', repo/'tools/prepare-oriole-aoc.py')
aoc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(aoc)
root = Path(sys.argv[1])
original = {name: (root/name).read_text() for name in aoc.HASHES}
updated = aoc.transform(original)
bad = dict(original)
bad[next(iter(bad))] += '\n'
try:
    aoc.transform(bad)
    raise AssertionError('changed source accepted')
except ValueError:
    pass
source = updated['aoc/alsa/aoc_alsa_hw.c']
copy = next(line.strip() for line in source.splitlines() if 'memcpy(&cmd.coeffs[i], &tmp,' in line)
with tempfile.TemporaryDirectory() as tmpdir:
    d = Path(tmpdir)
    (d/'wire.h').write_text(updated['aoc/aoc_ramdump_regions.h'])
    c = '''#include <stdint.h>
#include <stddef.h>
#include <string.h>
#include <assert.h>
typedef uint32_t u32;
#include "wire.h"
_Static_assert(sizeof(struct aoc_section_header) == 44, "section size");
_Static_assert(offsetof(struct aoc_section_header, type) == 16, "type offset");
_Static_assert(offsetof(struct aoc_section_header, lma) == 40, "lma offset");
_Static_assert(RAMDUMP_NUM_SECTIONS == 17, "sections");
_Static_assert(offsetof(struct aoc_ramdump_header, sections) == 36, "sections offset");
_Static_assert(offsetof(struct aoc_ramdump_header, platform) == 784, "platform offset");
_Static_assert(offsetof(struct aoc_ramdump_header, debug_authorized) == 856, "debug offset");
_Static_assert(sizeof(struct aoc_ramdump_header) == 860, "header size");
void copy_coeff(void *dest, uint32_t tmp) {
 struct { float coeffs[1]; } cmd;
 int i = 0;
 COPY
 memcpy(dest, &cmd, sizeof(tmp));
}
int main(void) {
 uint32_t patterns[] = {0, 0x80000000u, 0x3f800000u, 0x7fc01234u, 0xffffffffu};
 for (unsigned i = 0; i < sizeof(patterns)/sizeof(patterns[0]); i++) {
  uint32_t out;
  copy_coeff(&out, patterns[i]);
  assert(out == patterns[i]);
 }
 return 0;
}
'''.replace('COPY', copy)
    (d/'test.c').write_text(c)
    # The unmodified fixed-enum header is valid C++; verify its original ABI
    # independently of the C transformation using the same layout assertions.
    (d/'original.h').write_text(original['aoc/aoc_ramdump_regions.h'])
    original_check = c[:c.index('void copy_coeff')].replace('wire.h', 'original.h').replace('_Static_assert', 'static_assert') + 'int main() { return 0; }\n'
    (d/'original.cc').write_text(original_check)
    subprocess.run(['c++','-std=c++11','-Wall','-Wextra','-Werror',str(d/'original.cc'),'-o',str(d/'original')],check=True)
    subprocess.run([str(d/'original')],check=True)
    for flags in [[], ['-fshort-enums']]:
        subprocess.run(['cc','-std=gnu11','-O2','-Wall','-Wextra','-Werror',*flags,str(d/'test.c'),'-o',str(d/'test')],check=True)
        subprocess.run([str(d/'test')],check=True)
    subprocess.run(['aarch64-linux-gnu-gcc','-std=gnu11','-O2','-mgeneral-regs-only','-S',str(d/'test.c'),'-o',str(d/'test.s')],check=True)
print('PASS actual AoC wire ABI, bit-pattern copies, source guard and AArch64 general-register compilation')
