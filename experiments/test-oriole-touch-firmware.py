#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Test real pinned ST functions; requires the reference fts_spi directory."""
import importlib.util
import subprocess
import sys
import tempfile
from pathlib import Path

spec = importlib.util.spec_from_file_location('touch', Path(__file__).resolve().parents[1] / 'tools/prepare-oriole-touch.py')
touch = importlib.util.module_from_spec(spec)
spec.loader.exec_module(touch)
root = Path(sys.argv[1])
old = {name: (root / name).read_text() for name in touch.HASHES}
new = touch.transform(old)
assert '#define FTS_FW_UPDATE\n' not in new['fts.h']
assert '#undef FTS_FW_UPDATE\n' in new['fts.h']
assert new['fts.c'].count('#if !FTS_INPUT_ONLY_BRINGUP') == 3
for signature in ['static int fts_init_sensing(struct fts_ts_info *info)\n{',
                  'static int fts_mode_handler(struct fts_ts_info *info, int force)\n{']:
    a, b = touch.body_span(old['fts.c'], signature)
    x, y = touch.body_span(new['fts.c'], signature)
    assert old['fts.c'][a:b] == new['fts.c'][x:y]

def function(source, signature):
    a, b = touch.body_span(source, signature)
    return source[source.index(signature):b]

source = '#include <assert.h>\n#define FTS_INPUT_ONLY_BRINGUP 1\n#define ERROR_OP_NOT_ALLOW (-1)\ntypedef struct {int unused;} Firmware;\n'
for signature in ['int flashProcedure(', 'int flash_burn(']:
    source += function(new['fts_lib/ftsFlash.c'], signature) + '\n'
source += 'int main(void) { Firmware f={0}; assert(flashProcedure(0,1,0)==-1); assert(flash_burn(f,1,0)==-1); return 0; }\n'
with tempfile.TemporaryDirectory() as td:
    d = Path(td)
    (d/'test.c').write_text(source)
    subprocess.run(['cc', '-Wall', '-Werror', str(d/'test.c'), '-o', str(d/'test')], check=True)
    subprocess.run([str(d/'test')], check=True)
try:
    touch.transform(dict(old, **{'fts.h': old['fts.h'] + '\n'}))
except ValueError:
    pass
else:
    raise AssertionError('Changed source accepted')
print('PASS actual flash functions refuse writes without hardware references; sensing unchanged; wrong source refused')
