import importlib.util,json,tempfile,unittest
from pathlib import Path
p=Path(__file__).resolve().parent/'enable-agent-menu.py'
s=importlib.util.spec_from_file_location('fix',p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
class Contract(unittest.TestCase):
 def test_preserves_mobile_and_manual_fields(self):
  a={'version':1,'bar':{'id':'omamobile.bar','layout':{'left':[]}},'plugins':[{'id':'custom','x':7}],'custom':{'a':1},'disabledPlugins':['other','omarchy.menu']}
  b=m.updated(a);self.assertEqual(b['bar'],a['bar']);self.assertEqual(b['custom'],a['custom']);self.assertEqual(b['plugins'][0],a['plugins'][0]);self.assertEqual(b['disabledPlugins'],['other']);self.assertEqual(b['plugins'][-1],{'id':'omarchy.menu'});self.assertIn('omarchy.menu',a['disabledPlugins']);self.assertEqual(m.updated(b),b)
 def test_existing_entry(self):
  a={'version':1,'plugins':[{'id':'omarchy.menu','custom':True}]};self.assertEqual(m.updated(a),a)
 def test_bad_shape(self):
  for a in ({'version':2},{'version':1,'plugins':'bad'},{'version':1,'disabledPlugins':False}):
   with self.assertRaises(ValueError):m.updated(a)
 def test_backup_and_rollback_manual_edit_guard(self):
  with tempfile.TemporaryDirectory() as t:
   p=Path(t)/'shell.json';p.write_text('{"version":1,"plugins":[]}\n');before=p.read_bytes();m.apply(p);self.assertEqual(m.apply(p),'unchanged');p.write_text(p.read_text()+' ')
   with self.assertRaises(ValueError):m.rollback(p)
   p.write_bytes(Path(str(p)+'.oriole-menu-after').read_bytes());m.rollback(p);self.assertEqual(p.read_bytes(),before)
unittest.main()
