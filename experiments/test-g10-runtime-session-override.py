import importlib.util,tempfile
from pathlib import Path
p=Path(__file__).resolve().parents[1]/'tools/g10-runtime-session-override.py'
s=importlib.util.spec_from_file_location('c1',p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
with tempfile.TemporaryDirectory() as d:
 p=Path(d)/m.REL
 assert m.change(d,False)=='already-removed'
 assert m.change(d,True)=='enabled';assert p.read_bytes()==m.CONTENT
 assert m.change(d,True)=='already-enabled'
 assert m.change(d,False)=='removed';assert not p.exists()
 assert m.change(d,False)=='already-removed'
 m.change(d,True);p.write_text('manual edit\n')
 for enable in (True,False):
  try:m.change(d,enable);raise AssertionError('manual edit overwritten')
  except RuntimeError:pass
 assert p.read_text()=='manual edit\n';p.unlink();p.symlink_to(Path(d)/'missing')
 for enable in (True,False):
  try:m.change(d,enable);raise AssertionError('symlink followed')
  except RuntimeError:pass
print('PASS enable, idempotence, rollback, absent, manual edits, symlink refusal')
