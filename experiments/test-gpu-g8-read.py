from pathlib import Path
import re,sys,tempfile,subprocess
s=Path(sys.argv[1]).read_text();assert not re.search(r'write_reg|update_reg|bulk_write|writel|iowrite|devmem',s)
a=s.index('struct oriole_supply_reg');b=s.index('static int __init',a);body=s[a:b]
regs=re.findall(r'\{"([A-Z0-9_]+)",([01]),(S2MPG\d+_PMIC_[A-Z0-9_]+)\}',body)
expected=['B7M_CTRL','B7M_OUT1','B7M_OUT2','B2S_CTRL','B2S_OUT1','B2S_OUT2','B8S_CTRL','B8S_OUT1','B8S_OUT2','L1S_CTRL1','L1S_CTRL2','LDO_CTRL1','PCTRLSEL1','PCTRLSEL3','PCTRLSEL5']
assert [x[0] for x in regs]==expected;assert [x[1] for x in regs]==['0']*3+['1']*12
pre='''#include <stdbool.h>
#include <stdint.h>
#include <stddef.h>
#include <assert.h>
#include <stdio.h>
typedef uint8_t u8;
#define EIO 5
#define ARRAY_SIZE(a) (sizeof(a)/sizeof((a)[0]))
#define pr_info(...) ((void)0)
struct acpm_handle;
struct mock_ops { struct {int (*read_reg)(struct acpm_handle *,unsigned int,unsigned int,u8,u8,u8*);}pmic;};
struct acpm_handle {const struct mock_ops *ops;};
'''+''.join('#define '+x[2]+' '+str(i+1)+'\n' for i,x in enumerate(regs))
post='''
static unsigned int calls,fail_at,mismatch_at;
static int fake_read(struct acpm_handle *a,unsigned int ch,unsigned int type,u8 reg,u8 speedy,u8 *v){
 (void)a;calls++;assert(ch==2 && type==1);assert(reg==(calls+1)/2);assert(speedy==(reg<=3?0:1));
 if(calls==fail_at)return -17;
 *v=reg+((calls==mismatch_at)?1:0);return 0;
}
int main(void){const struct mock_ops ops={.pmic={.read_reg=fake_read}};struct acpm_handle a={.ops=&ops};
 assert(oriole_read_snapshot(&a)==0);assert(calls==30);
 for(unsigned int n=1;n<=30;n++){calls=0;fail_at=n;assert(oriole_read_snapshot(&a)==-17);assert(calls==n);}
 fail_at=0;
 for(unsigned int n=2;n<=30;n+=2){calls=0;mismatch_at=n;assert(oriole_read_snapshot(&a)==-EIO);assert(calls==n);}
 puts("PASS actual read loop:30orderedreads;30read-fault shortcircuits;15double-read mismatch stops; no write API; ASanUBSan");}
'''
with tempfile.TemporaryDirectory(prefix='gpu-g1-read-') as td:
 p=Path(td);(p/'t.c').write_text(pre+body+post)
 subprocess.run(['clang','-std=c11','-Wall','-Wextra','-Werror','-fsanitize=address,undefined',str(p/'t.c'),'-o',str(p/'t')],check=True)
 subprocess.run([str(p/'t')],check=True)
