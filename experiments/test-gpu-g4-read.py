from pathlib import Path
import subprocess,tempfile,sys,re
s=Path(sys.argv[1]).read_text();assert not re.search(r'set_rate|writel|regmap_write|iowrite|devmem',s)
a=s.index('static int oriole_rate_read');b=s.index('static int __init',a)
pre='''#include <assert.h>
#include <stddef.h>
#include <stdio.h>
#define EINVAL 22
#define ENODEV 19
#define EIO 5
#define EAGAIN 11
#define ARRAY_SIZE(a) (sizeof(a)/sizeof((a)[0]))
#define GS101_CLK_ACPM_DVFS_G3D 5
#define GS101_CLK_ACPM_DVFS_G3DL2 6
#define GS101_CLK_ACPM_DVFS_CPUCL0 2
#define GS101_CLK_ACPM_DVFS_CPUCL1 3
#define GS101_CLK_ACPM_DVFS_CPUCL2 4
#define pr_info(...) ((void)0)
struct acpm_handle;
struct ops {struct {unsigned long (*get_rate)(struct acpm_handle*,unsigned int,unsigned int);}dvfs;};
struct acpm_handle {struct ops*ops;};
static unsigned expected,calls,zero_at;static int differ;
static unsigned long get(struct acpm_handle*h,unsigned int ch,unsigned int id){(void)h;assert(ch==0);assert(id==expected);calls++;return calls==zero_at?0:100000000+(differ?calls:0);}
'''
post='''int main(void){struct ops op={.dvfs={get}},empty={0};struct acpm_handle h={&op};unsigned ids[]={5,6,2,3,4};
for(unsigned i=0;i<5;i++){expected=ids[i];calls=zero_at=differ=0;assert(oriole_rate_read(&h,i)==0&&calls==2);
for(unsigned j=1;j<=2;j++){calls=0;zero_at=j;assert(oriole_rate_read(&h,i)==-EIO&&calls==j);}
calls=zero_at=0;differ=1;assert(oriole_rate_read(&h,i)==-EAGAIN&&calls==2);}
calls=0;assert(oriole_rate_read(&h,5)==-EINVAL&&calls==0);assert(oriole_rate_read(&h,~0U)==-EINVAL);assert(oriole_rate_read(NULL,0)==-ENODEV);h.ops=NULL;assert(oriole_rate_read(&h,0)==-ENODEV);h.ops=&empty;assert(oriole_rate_read(&h,0)==-ENODEV);assert(calls==0);puts("PASS actual G4 read function: allowed IDs/channel, bounds, zero, changed rate, absent ops; ASan/UBSan");}
'''
with tempfile.TemporaryDirectory() as d:
 p=Path(d);(p/'t.c').write_text(pre+s[a:b]+post);subprocess.run(['clang','-std=c11','-Wall','-Wextra','-Werror','-fsanitize=address,undefined',str(p/'t.c'),'-o',str(p/'t')],check=True);subprocess.run([str(p/'t')],check=True)
