#!/usr/bin/env python3
"""Check or restore only the recorded Agent terminal UI changes.
Run on the phone as root; no CLI binary, user default, or credentials are removed.
"""
from pathlib import Path
import hashlib,json,os,sys

def restore(root,apply=False):
    def p(s):return root/s.lstrip('/')
    receipt=json.loads(p('/var/lib/oriole-agent-terminal-hold/receipt.json').read_text())
    link=p('/usr/share/omarchy/bin/omarchy-launch-tui');target=p('/usr/local/bin/omarchy-launch-tui');original=p('/usr/bin/omarchy-launch-tui')
    foot=p('/home/agent/.local/share/applications/foot.desktop');backup=foot.with_name('foot.desktop.oriole-before-hold')
    def check(path,expected):
        if path.is_symlink() or hashlib.sha256(path.read_bytes()).hexdigest()!=expected:raise ValueError('File changed; refusing rollback: '+str(path))
    if not link.is_symlink() or os.readlink(link)!='/usr/local/bin/omarchy-launch-tui':raise ValueError('Launcher link changed')
    check(target,receipt['override_sha256']);check(original,receipt['original_sha256']);check(foot,receipt['foot_entry_after_sha256']);check(backup,receipt['foot_entry_before_sha256'])
    if not apply:return 'rollback preflight passed; no changes'
    tmp=link.with_name('.omarchy-launch-tui-restore')
    tmp.symlink_to(receipt['original_symlink']);os.replace(tmp,link)
    tempfoot=foot.with_name('.foot.desktop-restore')
    with tempfoot.open('xb') as out:out.write(backup.read_bytes())
    st=foot.stat();tempfoot.chmod(st.st_mode&0o777)
    if os.geteuid()==0:os.chown(tempfoot,st.st_uid,st.st_gid)
    os.replace(tempfoot,foot);target.unlink()
    return 'UI restored; backup and receipt retained'

if __name__=='__main__':
    if len(sys.argv)!=2 or sys.argv[1] not in ('--check','--apply'):raise SystemExit('Usage: rollback-agent-ui.py --check|--apply')
    print(restore(Path('/'),sys.argv[1]=='--apply'))
