"""Run actual scan-start function with errors; does not simulate the touchscreen."""
from pathlib import Path
import tempfile,subprocess,sys
s=Path(sys.argv[1]).read_text();a=s.index('static int fts_init_sensing(struct fts_ts_info *info)\n{');b=s.index('\n/**',a);fn=s[a:b]
pre=r'''
#include <assert.h>
#include <stdio.h>
#define OK 0
struct fts_ts_info {int unused;};
static int phase,install_result,mode_result,enable_result;
static int fts_interrupt_install(struct fts_ts_info *i){(void)i;assert(phase==0);phase++;return install_result;}
static int fts_mode_handler(struct fts_ts_info *i,int force){(void)i;assert(force==0&&phase==1);phase++;return mode_result;}
static int fts_enableInterrupt(void){assert(phase==2);phase++;return enable_result;}
'''
post=r'''
int main(void){struct fts_ts_info i={0};
 install_result=-16;assert(fts_init_sensing(&i)==-16&&phase==1);
 phase=0;install_result=0;mode_result=-5;assert(fts_init_sensing(&i)==-5&&phase==2);
 phase=0;mode_result=0;enable_result=-6;assert(fts_init_sensing(&i)==-6&&phase==3);
 phase=0;enable_result=0;assert(fts_init_sensing(&i)==0&&phase==3);
 puts("PASS actual scan-start order, install/mode fail-stop, enable-error propagation");}
'''
with tempfile.TemporaryDirectory(prefix='oriole-scan-test-') as td:
 p=Path(td);(p/'test.c').write_text(pre+fn+post)
 subprocess.run(['clang','-std=c11','-Wall','-Wextra','-Werror','-fsanitize=address,undefined',str(p/'test.c'),'-o',str(p/'test')],check=True)
 subprocess.run([str(p/'test')],check=True)
