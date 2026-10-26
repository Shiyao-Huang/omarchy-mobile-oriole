from pathlib import Path
import re,tempfile,subprocess
s=Path('gpu-g9-core-supply/oriole_gpu_core_supply.c').read_text();assert not re.search(r'write_reg|writel|iowrite|set_rate',s)
body=s[s.index('struct snapshot_reg'):s.index('static int __init')].replace('static struct device *diag_dev;','')
regs=re.findall(r'\{([01]),(S2MPG\d+_PMIC_[A-Z0-9_]+),(0x[0-9a-f]+)\}',body);assert len(regs)==15
pre=r'''
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <assert.h>
#include <errno.h>
typedef uint8_t u8;
#define ARRAY_SIZE(a) (sizeof(a)/sizeof((a)[0]))
#define pr_info(...) do {if(0)printf(__VA_ARGS__);}while(0)
#define pr_err(...) do {if(0)printf(__VA_ARGS__);}while(0)
#define msleep(n) ((void)(n))
struct acpm_handle;
struct ops {struct{int(*read_reg)(struct acpm_handle*,unsigned,unsigned,u8,u8,u8*);int(*update_reg)(struct acpm_handle*,unsigned,unsigned,u8,u8,u8,u8);}pmic;struct{unsigned long(*get_rate)(struct acpm_handle*,unsigned,unsigned);}dvfs;};
struct acpm_handle{struct ops*ops;};
'''+''.join('#define '+name+' '+str(i)+'\n' for i,(_,name,_) in enumerate(regs))
post=r'''
static unsigned reads,writes,rates,read_fail,read_mismatch,update_fail,rate_wrong;static bool update_applies;static u8 state[15];
static int rd(struct acpm_handle*a,unsigned ch,unsigned type,u8 reg,u8 speedy,u8*v){assert(a==acpm&&ch==2&&type==1&&reg<15&&speedy==snapshot[reg].speedy);reads++;if(reads==read_fail)return -EIO;*v=state[reg]^(reads==read_mismatch?1:0);return 0;}
static int wr(struct acpm_handle*a,unsigned ch,unsigned type,u8 reg,u8 speedy,u8 val,u8 mask){assert(a==acpm&&ch==2&&type==1&&reg==S2MPG11_PMIC_B2S_CTRL&&speedy==1&&mask==0xc0&&(val==0||val==0xc0));writes++;if(writes==update_fail&&!update_applies)return -EIO;state[reg]=(state[reg]&~mask)|(val&mask);return writes==update_fail?-EIO:0;}
static unsigned long rate(struct acpm_handle*a,unsigned ch,unsigned id){assert(a==acpm&&ch==0&&id==5+rates/2);rates++;return rates==rate_wrong?0:151000000;}
static struct ops ops={.pmic={rd,wr},.dvfs={rate}};static struct acpm_handle handle={&ops};
static void reset(void){acpm=&handle;attempted=false;reads=writes=rates=read_fail=read_mismatch=update_fail=rate_wrong=0;update_applies=false;for(unsigned i=0;i<15;i++)state[i]=snapshot[i].expected;}
int main(void){reset();assert(enable_core()==0&&attempted&&writes==1&&state[3]==0xf8);assert(restore_core()==0&&!attempted&&state[3]==0x38&&writes==2);
for(unsigned i=1;i<=30;i++){reset();read_fail=i;assert(enable_core()!=0&&writes==0&&!attempted);reset();read_mismatch=i;assert(enable_core()!=0&&writes==0&&!attempted);}
for(unsigned i=1;i<=4;i++){reset();rate_wrong=i;assert(enable_core()==-ERANGE&&writes==0);}
for(unsigned i=0;i<2;i++){reset();update_fail=1;update_applies=i;assert(enable_core()==-EIO&&writes==2&&!attempted&&state[3]==0x38);}
for(unsigned i=31;i<=60;i++){reset();read_fail=i;assert(enable_core()==-EIO&&writes==2&&!attempted&&state[3]==0x38);reset();read_mismatch=i;assert(enable_core()==-EINVAL&&writes==2&&!attempted&&state[3]==0x38);}
reset();assert(enable_core()==0);state[3]=0x78;assert(restore_core()==-EBUSY&&attempted&&writes==1);state[3]=0xf8;assert(restore_core()==0);
reset();assert(enable_core()==0);update_fail=2;assert(restore_core()==-EIO&&attempted);update_fail=0;assert(restore_core()==0&&!attempted);
reset();assert(enable_core()==0);read_fail=reads+1;assert(restore_core()==-EIO&&writes==1&&attempted);read_fail=0;assert(restore_core()==0);
printf("PASS G9 actual core logic:60preflightfailures,4ratefailures,ambiguouswrites,60postreadfailures,restoreconflict/retry; allwritesonecontrolmask; ASan/UBSan\n");}
'''
with tempfile.TemporaryDirectory() as td:
 p=Path(td)
 for label,b in [('red',body.replace('if (val!=expected) return -EINVAL;','/* mutant missing snapshot guard */')),('green',body)]:
  (p/'t.c').write_text(pre+b+post);subprocess.run(['clang','-std=c11','-Wall','-Wextra','-Werror','-Wno-unused-but-set-variable','-fsanitize=address,undefined',str(p/'t.c'),'-o',str(p/'t')],check=True)
  r=subprocess.run([str(p/'t')],capture_output=True,text=True)
  if label=='red':assert r.returncode!=0;print('RED missing-snapshot-guard mutant rejected')
  else:assert r.returncode==0,r.stderr;print(r.stdout.strip())
