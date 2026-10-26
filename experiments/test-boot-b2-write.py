# SPDX-License-Identifier: MIT
"""Test actual compiled upstream C on regular temporary files only."""
from pathlib import Path
import sys,subprocess,tempfile,struct
exe=str(Path(sys.argv[1]).resolve())
with tempfile.TemporaryDirectory() as td:
 p=Path(td)/'synthetic-devinfo'
 original=bytearray((n*17)%256 for n in range(8192))
 struct.pack_into('<IHH',original,0,0x49564544,3,15)
 original[0x30:0x38]=bytes([2,10,0,0,0,4,0,0])
 def run(confirm):
  return subprocess.run([exe,'mark-successful',str(p),'b']+(['--i-understand'] if confirm else []),capture_output=True)
 p.write_bytes(original);assert run(False).returncode!=0;assert p.read_bytes()==original
 assert run(True).returncode==0
 after=p.read_bytes();assert [i for i,(a,b) in enumerate(zip(original,after)) if a!=b]==[0x35]
 assert after[0x35]==6 and len(after)==len(original)
 assert run(True).returncode==0 and p.read_bytes()==after
 for bad in [original[:127],bytes(8192),original[:6]+bytes([14,0])+original[8:],original+bytes(1024*1024)]:
  p.write_bytes(bad);assert run(True).returncode!=0;assert p.read_bytes()==bad
 print('BOOT_B2_ACTUAL_C_PASS: dryrun,exact-byte,idempotence,malformed,unsupported,oversize')
