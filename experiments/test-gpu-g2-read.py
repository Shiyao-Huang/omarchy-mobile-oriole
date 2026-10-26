from pathlib import Path
import sys,re,tempfile,subprocess
s=Path(sys.argv[1]).read_text();assert not re.search(r'regmap_write|update_bits|writel|iowrite|arm_smccc|pmu_raw_readl',s);a=s.index('static int oriole_gpu_status_read');b=s.index('static int __init',a)
pre='''#include <assert.h>
#include <stdio.h>
#define EIO 5
#define EINVAL 22
#define ARRAY_SIZE(a) (sizeof(a)/sizeof((a)[0]))
#define GS101_SUBBBLK_OFFSET_G3D 0x1e00
#define GS101_SUBBBLK_OFFSET_EMBEDDED_G3D 0x2000
#define GS101_SUBBLK_STATUS(x) ((x)+4)
#define pr_info(...) ((void)0)
struct regmap {unsigned int expected,calls,fail_at,mismatch_at;};
static int regmap_read(struct regmap*m,unsigned int off,unsigned int *v){assert(off==m->expected);m->calls++;if(m->calls==m->fail_at)return -19;*v=m->calls==m->mismatch_at?1:0;return 0;}
'''
post='''int main(void){for(unsigned int i=0;i<2;i++){struct regmap m={.expected=i?0x2004:0x1e04};assert(oriole_gpu_status_read(&m,i)==0 && m.calls==2);for(unsigned int j=1;j<=2;j++){m.calls=0;m.fail_at=j;assert(oriole_gpu_status_read(&m,i)==-19 && m.calls==j);}m.calls=0;m.fail_at=0;m.mismatch_at=2;assert(oriole_gpu_status_read(&m,i)==-EIO);}struct regmap m={0};assert(oriole_gpu_status_read(&m,2)==-EINVAL && m.calls==0);assert(oriole_gpu_status_read(&m,~0U)==-EINVAL && m.calls==0);puts("PASS actual PMU read function: bounds, exact offsets, read faults, mismatch; ASanUBSan");}'''
with tempfile.TemporaryDirectory(prefix='gpu-g2-') as td:
 p=Path(td);(p/'t.c').write_text(pre+s[a:b]+post);subprocess.run(['clang','-std=c11','-Wall','-Wextra','-Werror','-fsanitize=address,undefined',str(p/'t.c'),'-o',str(p/'t')],check=True);subprocess.run([str(p/'t')],check=True)
