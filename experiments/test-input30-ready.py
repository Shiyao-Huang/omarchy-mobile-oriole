from pathlib import Path
import sys,tempfile,subprocess
s=Path(sys.argv[1]).read_text();a=s.index('static bool oriole_ready_event(');b=s.index('\nstatic unsigned int session_seconds;',a)
code='''#include <stdbool.h>
#include <stddef.h>
#include <assert.h>
#include <stdio.h>
typedef unsigned char u8;
'''+s[a:b]+'''
int main(void) {
 u8 ready[9]={0x87,3}, bad[9]={0,3}, empty[9]={0x87,0};
 assert(oriole_ready_event(ready,9,0));
 assert(!oriole_ready_event(ready,9,1));
 assert(!oriole_ready_event(ready,9,-1));
 assert(!oriole_ready_event(bad,9,0));
 assert(!oriole_ready_event(empty,9,0));
 assert(!oriole_ready_event(ready,8,0));
 unsigned count=0;
 for(int i=0;i<1024;i++)count+=oriole_ready_event(ready,9,1);
 assert(count==0);
 for(int i=0;i<7;i++)count+=oriole_ready_event(ready,9,0);
 assert(count<8);count+=oriole_ready_event(ready,9,0);assert(count==8);
 puts("PASS actualready predicate: idle/invalid rejected, eightqualifiedready guard preserved; ASanUBSan");
}
'''
with tempfile.TemporaryDirectory(prefix='input30-ready-') as td:
 p=Path(td);(p/'t.c').write_text(code)
 subprocess.run(['clang','-std=c11','-Wall','-Wextra','-Werror','-fsanitize=address,undefined',str(p/'t.c'),'-o',str(p/'t')],check=True)
 subprocess.run([str(p/'t')],check=True)
