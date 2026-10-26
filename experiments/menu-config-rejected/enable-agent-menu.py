#!/usr/bin/env python3
"""Enable the Agent picker's menu without changing the mobile bar layout.
Run as the desktop user. Rollback refuses to overwrite subsequent manual edits.
"""
import copy,json,os,sys,tempfile
from pathlib import Path

def updated(config):
    if not isinstance(config,dict) or config.get('version')!=1:
        raise ValueError('Expected shell config version 1')
    result=copy.deepcopy(config)
    plugins=result.setdefault('plugins',[])
    disabled=result.get('disabledPlugins',[])
    if not isinstance(plugins,list) or not isinstance(disabled,list):
        raise ValueError('Invalid plugin configuration')
    if not any(isinstance(p,dict) and p.get('id')=='omarchy.menu' for p in plugins):
        plugins.append({'id':'omarchy.menu'})
    if 'disabledPlugins' in result:
        result['disabledPlugins']=[x for x in disabled if x!='omarchy.menu']
    return result

def replace_checked(path,old,new):
    stat=path.stat()
    if path.is_symlink():raise ValueError('Symlink config requires explicit resolution')
    fd,name=tempfile.mkstemp(dir=path.parent,prefix='.oriole-menu-')
    try:
        with os.fdopen(fd,'wb') as f:
            f.write(new);f.flush();os.fsync(f.fileno())
        os.chmod(name,stat.st_mode&0o777)
        if path.read_bytes()!=old:raise ValueError('Config changed concurrently')
        os.replace(name,path)
    finally:
        if os.path.exists(name):os.unlink(name)

def apply(path):
    old=path.read_bytes();config=json.loads(old);newconfig=updated(config)
    if config==newconfig:return 'unchanged'
    before=Path(str(path)+'.oriole-menu-before');after=Path(str(path)+'.oriole-menu-after')
    new=(json.dumps(newconfig,ensure_ascii=False,indent=2)+'\n').encode()
    if before.exists() or after.exists():raise ValueError('Previous backup exists; review before applying')
    for p,data in [(before,old),(after,new)]:
        with p.open('xb') as f:f.write(data)
        os.chmod(p,0o600)
    replace_checked(path,old,new)
    return 'enabled'

def rollback(path):
    before=Path(str(path)+'.oriole-menu-before');after=Path(str(path)+'.oriole-menu-after')
    current=path.read_bytes()
    if current!=after.read_bytes():raise ValueError('Config edited since patch; refusing rollback')
    replace_checked(path,current,before.read_bytes())
    return 'restored; backup files retained'

if __name__=='__main__':
    if len(sys.argv)!=3 or sys.argv[1] not in ('apply','rollback'):raise SystemExit('Usage: enable-agent-menu.py apply|rollback SHELL_JSON')
    print((apply if sys.argv[1]=='apply' else rollback)(Path(sys.argv[2])))
