#!/usr/bin/env python3
"""Deploy an already verified official ARM64 binary, without online mise.
Run as the target desktop user. This is a pinned, manually staged install.
No authentication or model task is performed. Backup/receipt enables rollback.
"""
import hashlib,json,os,re,shutil,sys
from pathlib import Path

def digest(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
    return h.hexdigest()

def paths(home):
    return (home/'.local/bin/claude',home/'.local/state/oriole-claude-offline')

def install(home,source,version,sha,wrapper_sha):
    home=home.resolve()
    if not re.fullmatch(r'[0-9]+\.[0-9]+\.[0-9]+',version):raise ValueError('Invalid pinned version')
    if digest(source)!=sha:raise ValueError('Binary checksum mismatch')
    with source.open('rb') as f:header=f.read(20)
    if header[:6]!=b'\x7fELF\x02\x01' or header[18:20]!=b'\xb7\0':raise ValueError('Expected ELF64 little-endian AArch64')
    launcher,state=paths(home);target=home/'.local/share/claude/versions'/version
    receipt=state/'receipt.json';backup=state/'original-wrapper'
    if receipt.exists():
        record=json.loads(receipt.read_text())
        if record['target']==str(target) and launcher.is_symlink() and launcher.resolve()==target and digest(target)==sha:return 'already installed'
        raise ValueError('Previous receipt exists; review it before modifying')
    if launcher.is_symlink() or not launcher.is_file() or digest(launcher)!=wrapper_sha:raise ValueError('Launcher no longer matches inspected wrapper')
    if target.exists() or target.is_symlink() or state.exists():raise ValueError('Existing destination; manual review required')
    state.mkdir(parents=True,mode=0o700);shutil.copy2(launcher,backup)
    target.parent.mkdir(parents=True,exist_ok=True)
    with source.open('rb') as src,target.open('xb') as dst:shutil.copyfileobj(src,dst)
    target.chmod(0o755)
    if digest(target)!=sha:raise ValueError('Installed binary checksum mismatch')
    tmp=launcher.with_name('.claude-oriole-install')
    if tmp.exists() or tmp.is_symlink():raise ValueError('Temporary link exists')
    tmp.symlink_to(target)
    try:
        if launcher.is_symlink() or digest(launcher)!=wrapper_sha:raise ValueError('Launcher changed during install')
        receipt.write_text(json.dumps({'target':str(target),'sha256':sha,'version':version,'wrapper_sha256':wrapper_sha},indent=2)+'\n')
        os.replace(tmp,launcher)
    finally:
        if tmp.is_symlink():tmp.unlink()
    return 'installed'

def rollback(home):
    home=home.resolve()
    launcher,state=paths(home);record=json.loads((state/'receipt.json').read_text());target=Path(record['target']);backup=state/'original-wrapper'
    if not launcher.is_symlink() or launcher.resolve()!=target or digest(target)!=record['sha256']:raise ValueError('Installation edited; refusing rollback')
    if digest(backup)!=record['wrapper_sha256']:raise ValueError('Backup checksum mismatch')
    tmp=launcher.with_name('.claude-oriole-rollback')
    with tmp.open('xb') as f:f.write(backup.read_bytes())
    shutil.copymode(backup,tmp);os.replace(tmp,launcher)
    return 'restored; binary and receipt retained for inspection'

if __name__=='__main__':
    if len(sys.argv)==3 and sys.argv[1]=='rollback':print(rollback(Path(sys.argv[2])))
    elif len(sys.argv)==7 and sys.argv[1]=='install':print(install(Path(sys.argv[2]),Path(sys.argv[3]),*sys.argv[4:]))
    else:raise SystemExit('Usage: install-offline-claude.py install HOME BINARY VERSION SHA256 WRAPPER_SHA256 | rollback HOME')
