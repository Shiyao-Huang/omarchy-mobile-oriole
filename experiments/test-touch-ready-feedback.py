from pathlib import Path
import tempfile,subprocess,sys
s=Path(sys.argv[1]).read_text();a=s.index('static void fts_controller_ready_event_handler(');b=s.index('\n/**',a);fn=s[a:b]
pre=r'''
#include <assert.h>
#include <stdio.h>
#define FTS_INPUT_ONLY_BRINGUP 1
#define OK 0
#define logError(...) ((void)0)
#define dev_err(...) ((void)0)
struct fts_ts_info {int bringup_ready_count;};
static int modes,disabled,releases,up,down;
static void fts_disableInterruptNoSync(void){disabled++;}
static void release_all_touches(struct fts_ts_info *i){(void)i;releases++;}
static void setSystemResetedUp(int v){assert(v==1);up++;}
static void setSystemResetedDown(int v){assert(v==1);down++;}
static int fts_mode_handler(struct fts_ts_info *i,int force){(void)i;assert(force==0);modes++;return 0;}
'''
post=r'''
int main(void){struct fts_ts_info i={0};unsigned char e[8]={3};
 for(int n=0;n<7;n++)fts_controller_ready_event_handler(&i,e);
 assert(modes==0&&disabled==0&&releases==7&&up==7&&down==7);
 fts_controller_ready_event_handler(&i,e);assert(disabled==1&&modes==0&&releases==7);
 puts("PASS actual callback: no rescan feedback, bookkeeping retained, eighth ready disables IRQ");}
'''
with tempfile.TemporaryDirectory(prefix='oriole-ready-test-') as td:
 p=Path(td);(p/'test.c').write_text(pre+fn+post)
 subprocess.run(['clang','-std=c11','-Wall','-Wextra','-Werror','-Wno-unused-parameter','-fsanitize=address,undefined',str(p/'test.c'),'-o',str(p/'test')],check=True)
 r=subprocess.run([str(p/'test')],capture_output=True,text=True)
 if len(sys.argv)>2 and sys.argv[2]=='red':assert r.returncode!=0;print('RED:21 resends scan in ready callback')
 else:print(r.stdout);assert r.returncode==0,r.stderr
