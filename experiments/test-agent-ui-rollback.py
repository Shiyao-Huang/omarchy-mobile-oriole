import importlib.util,tempfile,unittest,hashlib,json,os
from pathlib import Path
p=Path(__file__).resolve().parents[1]/'tools/rollback-agent-ui.py';s=importlib.util.spec_from_file_location('rollback',p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
class Contract(unittest.TestCase):
 def make(self,t):
  r=Path(t);items={'usr/bin/omarchy-launch-tui':b'original','usr/local/bin/omarchy-launch-tui':b'override','home/agent/.local/share/applications/foot.desktop':b'after','home/agent/.local/share/applications/foot.desktop.oriole-before-hold':b'before'}
  for n,b in items.items():p=r/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b)
  l=r/'usr/share/omarchy/bin/omarchy-launch-tui';l.parent.mkdir(parents=True);l.symlink_to('/usr/local/bin/omarchy-launch-tui');rec={'original_symlink':'/usr/bin/omarchy-launch-tui'}
  for k,n in zip(['original_sha256','override_sha256','foot_entry_after_sha256','foot_entry_before_sha256'],items):rec[k]=hashlib.sha256(items[n]).hexdigest()
  p=r/'var/lib/oriole-agent-terminal-hold/receipt.json';p.parent.mkdir(parents=True);p.write_text(json.dumps(rec));return r,l
 def test_check_and_restore(self):
  with tempfile.TemporaryDirectory() as t:
   r,l=self.make(t);m.restore(r);self.assertEqual(os.readlink(l),'/usr/local/bin/omarchy-launch-tui');m.restore(r,True);self.assertEqual(os.readlink(l),'/usr/bin/omarchy-launch-tui');self.assertEqual((r/'home/agent/.local/share/applications/foot.desktop').read_bytes(),b'before');self.assertFalse((r/'usr/local/bin/omarchy-launch-tui').exists())
 def test_refuses_manual_change(self):
  with tempfile.TemporaryDirectory() as t:
   r,l=self.make(t);(r/'home/agent/.local/share/applications/foot.desktop').write_bytes(b'manual')
   with self.assertRaises(ValueError):m.restore(r,True)
   self.assertEqual(os.readlink(l),'/usr/local/bin/omarchy-launch-tui')
unittest.main()
