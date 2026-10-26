from pathlib import Path
import importlib.util, unittest, hashlib, base64
spec=importlib.util.spec_from_file_location('decoder',Path(__file__).with_name('serial-backup-decoder.py'));m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class Decoder(unittest.TestCase):
 def setUp(self):
  self.token='a'*32;self.data=b'\x00test\xff\n'*20;self.sha=hashlib.sha256(self.data).hexdigest();self.begin=f'BACKUP_{self.token}_BEGIN';self.end=f'BACKUP_{self.token}_END';self.frame=self.begin+'\n'+base64.encodebytes(self.data).decode()+self.end+'\n'
 def decode(self,s):return m.decode_frame(s,self.token,len(self.data),self.sha)
 def test_roundtrip(self):self.assertEqual(self.decode('shell noise\n'+self.frame+'prompt\n'),self.data)
 def test_missing_end(self):
  with self.assertRaises(ValueError):self.decode(self.frame.replace(self.end,''))
 def test_duplicate(self):
  with self.assertRaises(ValueError):self.decode(self.frame+self.frame)
 def test_size(self):
  with self.assertRaises(ValueError):m.decode_frame(self.frame,self.token,len(self.data)+1,self.sha)
 def test_digest(self):
  with self.assertRaises(ValueError):m.decode_frame(self.frame,self.token,len(self.data),'0'*64)
 def test_corrupt(self):
  with self.assertRaises(ValueError):self.decode(self.frame.replace('\n', '\n!',1))
 def test_bound(self):
  with self.assertRaises(ValueError):m.decode_frame(self.frame,self.token,2*1024*1024+1,self.sha)
 def test_reversed(self):
  with self.assertRaises(ValueError):self.decode(self.end+'\n'+self.begin)
unittest.main()
