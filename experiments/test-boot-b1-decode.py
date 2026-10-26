# SPDX-License-Identifier: MIT
from pathlib import Path
import runpy, struct
p=Path(__file__).resolve().parents[1]
decode=runpy.run_path(str(p/'tools/boot-b1-decode.py'))['decode']
b=bytearray(128);struct.pack_into('<IHH',b,0,0x49564544,3,15)
b[0x30:0x38]=bytes([3,2,0,0,0,4,0,0])
r=decode(b)
assert r['slots']['a']['successful'] and not r['slots']['a']['active']
assert r['slots']['b']['active'] and not r['slots']['b']['successful']
assert r['slots']['b']['retry_count']==0
for bit,name in [(1,'unbootable'),(2,'successful'),(4,'active'),(8,'fastboot_ok')]:
 c=bytearray(b);c[0x35]=bit;assert decode(c)['slots']['b'][name]
for bad in [b[:127],b+b'x',bytes(128),b[:6]+bytes([14,0])+b[8:]]:
 try:decode(bad)
 except ValueError:pass
 else:raise AssertionError('malformed header accepted')
assert bytes(b[0x30:0x38])==bytes([3,2,0,0,0,4,0,0])
print('BOOT_B1_DECODE_PASS; no write API')
