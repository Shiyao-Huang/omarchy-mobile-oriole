from pathlib import Path
import os,subprocess,json,hashlib,struct
prefix=Path('/opt/oriole-experiments/mesa-g10');lib=prefix/'lib'
assert prefix.is_dir() and (prefix/'oriole-stage.json').is_file()
files=sorted({p.resolve() for p in lib.rglob('*.so*') if p.is_file()})
assert any('gallium' in p.name for p in files) and any('gbm' in p.name for p in files)
env=dict(os.environ,LD_LIBRARY_PATH=str(lib));checks=[]
for p in files:
 b=p.read_bytes();assert b[:6]==b'\x7fELF\x02\x01' and struct.unpack_from('<H',b,18)[0]==183,p.name
 r=subprocess.run(['ldd','-r',str(p)],env=env,capture_output=True,text=True,timeout=30)
 text=r.stdout+r.stderr
 checks.append({'library':str(p),'sha256':hashlib.sha256(b).hexdigest(),'returncode':r.returncode,'relocations':text})
 assert r.returncode==0 and 'not found' not in text and 'undefined symbol' not in text,text
stock={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for pattern in ['libEGL_mesa.so.*','libgbm.so.*','libgallium-*.so'] for p in Path('/usr/lib').glob(pattern) if p.is_file() and not p.is_symlink()}
result={'candidate_dependencies':'pass','checks':checks,'stock_libraries':stock,'limits':'Relocation success is not real GPU execution'}
Path('/var/tmp/oriole-g10/abi-result.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({'candidate_dependencies':'pass','libraries':[p.name for p in files],'stock_library_count':len(stock)}))
print('PRIVATE_LAYOUT')
for p in sorted(prefix.rglob('*')):
 if p.is_symlink():print('LINK',str(p.relative_to(prefix)),os.readlink(p))
 elif p.suffix=='.json':print(str(p.relative_to(prefix)),p.read_text()[:2000])
