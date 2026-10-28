#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Restrict the pinned ST driver to input bring-up; no device operations."""
import hashlib
import sys
from pathlib import Path

HASHES = {
    'fts.h': 'e04d97eef10f34c6291971e60b39f443e346984ed42c033c65dad167b6b1948b',
    'fts.c': '4a858666ff7083894eb3a274ed7d0b9e3caa1407865c833cd08555edcb0bff3d',
    'fts_lib/ftsFlash.c': '6d42a81c136a7b0a9e304e68738b75464e28b5c30a478daa618a43ed62322b53',
}


def body_span(source, signature):
    start = source.index('{', source.index(signature))
    depth, end = 1, start + 1
    while depth:
        depth += (source[end] == '{') - (source[end] == '}')
        end += 1
    return start, end


def transform(files):
    for name, digest in HASHES.items():
        if hashlib.sha256(files[name].encode()).hexdigest() != digest:
            raise ValueError('Unexpected pinned touch source: ' + name)
    result = dict(files)
    result['fts.h'] = files['fts.h'].replace(
        '#define FTS_FW_UPDATE\n',
        '/* Keep the installed controller firmware during native Linux bring-up. */\n'
        '#undef FTS_FW_UPDATE\n#define FTS_INPUT_ONLY_BRINGUP 1\n')
    s = files['fts.c']
    # Keep diagnostic code in the GPL source but omit its registration. This
    # also avoids logging the controller's private lockdown bytes at probe.
    a = s.index('\terror = fts_get_lockdown_info(info->lockdown_info, info);', s.index('static int fts_probe('))
    b = s.index('\n#ifdef FTS_FW_UPDATE', a)
    s = s[:a] + '#if !FTS_INPUT_ONLY_BRINGUP\n' + s[a:b].rstrip() + '\n#endif\n' + s[b:]
    a = s.index('\tlogError(0, "%s SET Device File Nodes:')
    b = s.index('\n\tdevice_init_wakeup', a)
    s = s[:a] + '#if !FTS_INPUT_ONLY_BRINGUP\n' + s[a:b].rstrip() + '\n#endif\n' + s[b:]
    a = s.index('\n#ifdef FTS_DEBUG_FS', a)
    b = s.index('\n#ifndef FW_UPDATE_ON_PROBE', a)
    s = s[:a] + '\n#if !FTS_INPUT_ONLY_BRINGUP\n' + s[a:b].strip('\n') + '\n#endif\n' + s[b:]
    s = s.replace('\tfts_proc_remove();', '\tif (!FTS_INPUT_ONLY_BRINGUP)\n\t\tfts_proc_remove();')
    s = s.replace('\tsysfs_remove_group(&client->dev.kobj, &info->attrs);',
                  '\tif (!FTS_INPUT_ONLY_BRINGUP)\n\t\tsysfs_remove_group(&client->dev.kobj, &info->attrs);')
    s = s.replace('\tdevice_destroy(info->fts_tp_class, DCHIP_ID_0);',
                  '\tif (info->fts_tp_class)\n\t\tdevice_destroy(info->fts_tp_class, DCHIP_ID_0);')
    result['fts.c'] = s
    s = files['fts_lib/ftsFlash.c']
    for signature in ['int flashProcedure(const char *path, int force, int keep_cx)',
                      'int flash_burn(Firmware fw, int force_burn, int keep_cx)']:
        a, b = body_span(s, signature)
        s = s[:a+1] + '\n#if FTS_INPUT_ONLY_BRINGUP\n\treturn ERROR_OP_NOT_ALLOW;\n#else' + s[a+1:b-1] + '\n#endif\n' + s[b-1:]
    result['fts_lib/ftsFlash.c'] = s
    return result


if __name__ == '__main__':
    root = Path(sys.argv[1]) / 'drivers/input/touchscreen/fts_spi'
    original = {name: (root / name).read_text() for name in HASHES}
    updated = transform(original)  # Validate every source before writing any.
    for name, source in updated.items():
        (root / name).write_text(source)
    print('PASS pinned touch source restricted; physical input remains unverified')
