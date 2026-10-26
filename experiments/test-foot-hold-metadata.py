import importlib.util,unittest
from pathlib import Path
p=Path(__file__).resolve().parents[1]/'tools/foot-hold-metadata.py';s=importlib.util.spec_from_file_location('hold',p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
class Contract(unittest.TestCase):
 def test_preserves_fields_and_actions(self):
  a='[Desktop Entry]\n# comment\nExec=foot\nX-TerminalArgAppId=--app-id=\n[Desktop Action other]\nExec=other\n';b=m.with_hold(a);self.assertEqual(b.replace('X-TerminalArgHold=--hold\n',''),a);self.assertEqual(m.with_hold(b),b)
 def test_rejects_unknown(self):
  for a in ['[Desktop Entry]\nExec=other\n','[Desktop Entry]\nExec=foot\nTerminalArgHold=-x\n','bad']:
   with self.assertRaises(ValueError):m.with_hold(a)
unittest.main()
