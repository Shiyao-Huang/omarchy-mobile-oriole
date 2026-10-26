import importlib.util,os,select,tempfile,threading,hashlib,time,termios
from pathlib import Path
spec=importlib.util.spec_from_file_location('rx',str(Path(__file__).resolve().parents[1]/'tools/serial-receive-file.py'));rx=importlib.util.module_from_spec(spec);spec.loader.exec_module(rx)
def case(kind):
 with tempfile.TemporaryDirectory() as d:
  target=Path(d)/'payload';target.write_bytes(b'OLD');part=Path(str(target)+'.part');m,s=os.openpty();old=termios.tcgetattr(s);errors=[]
  data=bytes(range(256))*256;expected=hashlib.sha256(data).hexdigest()
  if kind=='existing_part':part.write_bytes(b'KEEP')
  def worker():
   try:rx.receive(s,target,len(data),expected,.6)
   except Exception as e:errors.append(type(e).__name__)
  t=threading.Thread(target=worker);t.start();buf=b'';end=time.monotonic()+1
  while time.monotonic()<end and b'ORIOLE_TRANSFER_READY\n' not in buf and t.is_alive():
   if select.select([m],[],[],.05)[0]:buf+=os.read(m,65536)
  if b'ORIOLE_TRANSFER_READY\n' in buf:
   send=data if kind=='valid' else (b'X'+data[1:] if kind=='bad_digest' else data[:100])
   while send:n=os.write(m,send);send=send[n:]
  t.join(2);assert not t.is_alive();new=termios.tcgetattr(s);new[3] &= ~getattr(termios,'PENDIN',0);old[3] &= ~getattr(termios,'PENDIN',0);assert new==old, (old,new,errors)
  if kind=='valid':assert not errors and target.read_bytes()==data and not part.exists()
  elif kind=='existing_part':assert errors==['FileExistsError'] and target.read_bytes()==b'OLD' and part.read_bytes()==b'KEEP'
  else:assert errors and target.read_bytes()==b'OLD' and not part.exists()
  os.close(m);os.close(s);print('PASS',kind,'data/old-file/part ownership/TTY restoration')
for x in ['valid','bad_digest','truncated','existing_part']:case(x)
