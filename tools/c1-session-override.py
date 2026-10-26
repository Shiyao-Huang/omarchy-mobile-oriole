#!/usr/bin/env python3
"""Reversible, task-owned Aquamarine user-service override. Original library untouched."""
import argparse,hashlib,os,subprocess
from pathlib import Path
REL='home/agent/.config/systemd/user/wayland-wm@hyprland.desktop.service.d/90-oriole-aquamarine-c1.conf'
CONTENT=b'[Service]\nEnvironment=LD_LIBRARY_PATH=/opt/oriole-experiments/aquamarine-c1/lib\n'

def change(root,enable):
 p=Path(root)/REL
 if p.is_symlink():raise RuntimeError('Refuse symlink override')
 if p.exists() and p.read_bytes()!=CONTENT:raise RuntimeError('Override manually changed; preserve and stop')
 if enable:
  p.parent.mkdir(parents=True,exist_ok=True)
  if p.exists():return 'already-enabled'
  fd=os.open(p,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o644)
  with os.fdopen(fd,'wb') as f:f.write(CONTENT);f.flush();os.fsync(f.fileno())
  return 'enabled'
 if p.exists():p.unlink();return 'removed'
 return 'already-removed'

def main():
 ap=argparse.ArgumentParser();ap.add_argument('action',choices=['enable','rollback']);ap.add_argument('--restart',action='store_true');a=ap.parse_args()
 assert os.geteuid()==0,'Requires root'
 print(change('/',a.action=='enable'),flush=True)
 subprocess.run(['runuser','-u','agent','--','env','XDG_RUNTIME_DIR=/run/user/1000','systemctl','--user','daemon-reload'],check=True,timeout=20)
 if a.restart:subprocess.run(['systemctl','restart','sddm'],check=True,timeout=35)
if __name__=='__main__':main()
