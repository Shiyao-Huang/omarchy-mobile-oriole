import importlib.util,tempfile,unittest,hashlib
from pathlib import Path
p=Path(__file__).resolve().parents[1]/'tools/install-offline-claude.py'
s=importlib.util.spec_from_file_location('installer',p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
class Contract(unittest.TestCase):
 def fixture(self,t):
  home=Path(t)/'home';launcher=home/'.local/bin/claude';launcher.parent.mkdir(parents=True);launcher.write_bytes(b'original mise wrapper\n');blob=Path(t)/'binary';blob.write_bytes(b'\x7fELF\x02\x01'+b'\0'*12+b'\xb7\0'+b'payload');return home,launcher,blob,hashlib.sha256(blob.read_bytes()).hexdigest(),hashlib.sha256(launcher.read_bytes()).hexdigest()
 def test_reject_before_mutation(self):
  with tempfile.TemporaryDirectory() as t:
   h,l,b,d,w=self.fixture(t)
   with self.assertRaises(ValueError):m.install(h,b,'2.1.1','0'*64,w)
   self.assertEqual(l.read_bytes(),b'original mise wrapper\n');self.assertFalse((h/'.local/share/claude').exists())
 def test_install_repeat_and_manual_rollback_guard(self):
  with tempfile.TemporaryDirectory() as t:
   h,l,b,d,w=self.fixture(t);m.install(h,b,'2.1.1',d,w);self.assertTrue(l.is_symlink());self.assertEqual(l.read_bytes(),b.read_bytes());self.assertEqual(m.install(h,b,'2.1.1',d,w),'already installed')
   l.unlink();l.write_text('manual edit')
   with self.assertRaises(ValueError):m.rollback(h)
   l.unlink();l.symlink_to(h/'.local/share/claude/versions/2.1.1');m.rollback(h);self.assertEqual(l.read_bytes(),b'original mise wrapper\n')
 def test_refuse_changed_wrapper_and_bad_arch(self):
  with tempfile.TemporaryDirectory() as t:
   h,l,b,d,w=self.fixture(t);l.write_text('custom install')
   with self.assertRaises(ValueError):m.install(h,b,'2.1.1',d,w)
   b.write_bytes(b'wrong arch')
   with self.assertRaises(ValueError):m.install(h,b,'2.1.1',hashlib.sha256(b.read_bytes()).hexdigest(),w)
unittest.main()
