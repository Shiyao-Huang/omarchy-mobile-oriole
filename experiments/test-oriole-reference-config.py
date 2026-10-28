#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
import importlib.util
from pathlib import Path

path = Path(__file__).resolve().parents[1] / 'tools/oriole-reference-config.py'
spec = importlib.util.spec_from_file_location('reference_config', path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
valid = '_test="\n# comment\n CONFIG_FOO=m\nCONFIG_BAR=384\n"\n'
assert module.assignments(valid, '_test') == ['CONFIG_FOO=m', 'CONFIG_BAR=384']
assert module.merge('# CONFIG_FOO is not set\nCONFIG_BAR=1\nCONFIG_OTHER=y\n',
                    ['CONFIG_FOO=m', 'CONFIG_BAR=384']) == 'CONFIG_OTHER=y\nCONFIG_FOO=m\nCONFIG_BAR=384\n'
for bad in ['', valid + valid, '_test="\nCONFIG_FOO=$(touch /tmp/bad)\n"\n', '_test="\nCONFIG_FOO=m;exit\n"\n']:
    try:
        module.assignments(bad, '_test')
    except ValueError:
        pass
    else:
        raise AssertionError('Accepted invalid config')
print('PASS literal config extraction; missing, duplicate and executable values refused')
