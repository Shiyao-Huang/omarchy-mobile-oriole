from pathlib import Path
import subprocess,tempfile,sys
s=Path(sys.argv[1]).read_text();a=s.index('    if (driver == AQ_BACKEND_GPU_DRIVER_EVDI');b=s.index('\n    }',a)+6;branch=s[a:b]
h='''#include <cassert>
#include <cstring>
#include <cstdio>
constexpr int AQ_BACKEND_GPU_DRIVER_EVDI=1;
struct GPU { int renderNodeFd; };
bool actual(const char* drmVerName, int driver, bool secondary, int fd) {
 bool primary=secondary, rendererRequired=true; GPU g{fd};GPU*gpu=&g;
'''
t='''
 return rendererRequired;
}
int main(){
 assert(!actual("simpledrm",0,false,-1));
 assert(actual("simpledrm",0,true,-1));
 assert(actual("simpledrm",0,false,5));
 assert(actual("simpledrm-other",0,false,-1));
 assert(actual("unknown",0,false,-1));
 assert(actual("panfrost",0,false,8));
 assert(actual("amdgpu",0,false,-1));
 assert(!actual("evdi",1,true,-1));
 puts("PASS actual registerGPU guard: simpledrm primary/no-render only; GPU, secondary and existing evdi preserved");
}
'''
with tempfile.TemporaryDirectory() as d:
 p=Path(d)
 for name,block,want in [('baseline','if(driver==AQ_BACKEND_GPU_DRIVER_EVDI){primary={};rendererRequired=false;}',False),('candidate',branch,True)]:
  (p/(name+'.cpp')).write_text(h+block+t);subprocess.run(['c++','-std=c++17','-fsanitize=address,undefined',str(p/(name+'.cpp')),'-o',str(p/name)],check=True)
  r=subprocess.run([str(p/name)],capture_output=True,text=True);assert (r.returncode==0)==want
  print(name,'GREEN' if r.returncode==0 else 'RED expected: primary simpledrm still requests EGL DRM renderer');print(r.stdout.strip())
