from pathlib import Path
import subprocess,time,os,hashlib,json,sys,re
label=sys.argv[1];assert label in ('baseline','candidate','rollback')
d=Path('/var/tmp/oriole-aquamarine-c1');logs=list(Path('/run/user/1000/hypr').glob('*/hyprland.log'));assert logs
log=max(logs,key=lambda p:p.stat().st_mtime);offset=log.stat().st_size
names={'Hyprland','quickshell'}
def cpu():
 out={}
 for p in Path('/proc').glob('[0-9]*'):
  try:
   s=(p/'stat').read_text();comm=s[s.index('(')+1:s.rindex(')')];a=s[s.rindex(')')+2:].split()
   if comm in names:out[p.name]=(comm,int(a[11])+int(a[12]))
  except (OSError,ValueError):pass
 return out
start=cpu();t=time.monotonic();hashes=[];scanout_ids=[];screenshots=[]
cmd=['runuser','-u','agent','--','env','XDG_RUNTIME_DIR=/run/user/1000','WAYLAND_DISPLAY=wayland-1','foot','--app-id=oriole-c1-test','--title=Oriole-render-test','sh','-c','i=0; while [ "$i" -lt 30 ]; do printf "\\033[2J\\033[HRendering check %s\\n" "$i"; i=$((i+1)); sleep 0.5; done']
p=subprocess.Popen(cmd,stdout=subprocess.DEVNULL,stderr=(d/(label+'-foot.log')).open('w'),start_new_session=True,cwd="/home/agent")
for i in range(16):
 time.sleep(1)
 state=Path('/sys/kernel/debug/dri/0/state').read_text()
 match=re.search(r'\n\s*fb=(\d+)',state);scanout_ids.append(int(match.group(1)) if match else None)
 if i in (3,11):
  shot=d/(label+'-frame'+str(i)+'.png')
  r=subprocess.run(['runuser','-u','agent','--','env','XDG_RUNTIME_DIR=/run/user/1000','WAYLAND_DISPLAY=wayland-1','grim',str(shot)],capture_output=True,timeout=10)
  if r.returncode==0:screenshots.append(hashlib.sha256(shot.read_bytes()).hexdigest())
  else:screenshots.append('capture-failed')
try:rc=p.wait(timeout=5)
except subprocess.TimeoutExpired:p.terminate();rc=p.wait(timeout=3)
end=cpu();dt=time.monotonic()-t
with log.open('rb') as f:f.seek(offset);data=f.read(16*1024*1024)
res={'label':label,'duration_s':round(dt,2),'foot_exit':rc,'scanout_samples':len(scanout_ids),'unique_scanout_fb_ids':len(set(scanout_ids)),'screenshots':screenshots,'distinct_screenshots':len(set(screenshots)),'cpu_percent_one_core':{v[0]:round((v[1]-start[k][1])/os.sysconf('SC_CLK_TCK')/dt*100,2) for k,v in end.items() if k in start},'new_log_bytes':log.stat().st_size-offset,'initMgpu_errors':data.count(b'initMgpu: no renderer'),'applyCommit_errors':data.count(b'Failed to update renderer state'),'log_sample_capped':log.stat().st_size-offset>len(data),'limits':'DRM framebuffer IDs and compositor screenshots do not prove physical panel output or touch latency; /dev/fb0 emulation buffer was not the active Hyprland framebuffer'}
(d/(label+'-benchmark.json')).write_text(json.dumps(res,indent=2));print(json.dumps(res))
