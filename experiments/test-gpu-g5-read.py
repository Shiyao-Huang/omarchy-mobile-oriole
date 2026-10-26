from pathlib import Path
import re,subprocess,tempfile,sys
s=Path(sys.argv[1]).read_text();assert not re.search(r'writel|iowrite|regmap_write|set_rate|enable_irq|dma_alloc',s);s='\n'.join(x for x in s.splitlines() if not x.startswith('#include'))
pre=r'''
#include <assert.h>
#include <stdint.h>
#include <stddef.h>
#include <stdio.h>
#define __iomem
#define __init
#define __exit
#define ENODEV 19
#define EAGAIN 11
#define EIO 5
#define EBUSY 16
#define EINVAL 22
#define ENOMEM 12
#define ARRAY_SIZE(a) (sizeof(a)/sizeof((a)[0]))
#define GS101_SUBBBLK_OFFSET_G3D 0x1e00
#define GS101_SUBBBLK_OFFSET_EMBEDDED_G3D 0x2000
#define GS101_SUBBLK_STATUS(x) ((x)+4)
#define pr_info(...) ((void)0)
#define IS_ERR(p) ((intptr_t)(p)<0)
#define PTR_ERR(p) ((int)(intptr_t)(p))
#define module_init(x)
#define module_exit(x)
#define MODULE_LICENSE(x)
#define MODULE_DESCRIPTION(x)
typedef uint32_t u32;
struct device_node{int unused;};struct regmap{int unused;};struct resource{unsigned long start,end;};
static struct device_node node;static struct regmap map;static int mem;
static unsigned wrong_board,missing_node,enabled,bad_resource,no_map,request_busy,iomap_fail,pmu_error_at,pmu_bad_at,node_puts,pmu_calls,requests,releases,maps,unmaps,reads;
static u32 vals[2];
static int of_machine_is_compatible(const char*s){(void)s;return !wrong_board;}
static struct device_node*of_find_compatible_node(void*a,void*b,const char*c){(void)a;(void)b;(void)c;return missing_node?NULL:&node;}
static int of_device_is_available(struct device_node*n){assert(n==&node);return enabled;}
static void of_node_put(struct device_node*n){assert(n==&node);node_puts++;}
static int of_address_to_resource(struct device_node*n,int i,struct resource*r){assert(n==&node&&i==0);r->start=0x1c500000+bad_resource;r->end=r->start+0x4fff;return 0;}
static unsigned long resource_size(struct resource*r){return r->end-r->start+1;}
static struct regmap*exynos_get_pmu_regmap(void){return no_map?NULL:&map;}
static int regmap_read(struct regmap*m,unsigned int off,unsigned int*v){assert(m==&map);assert(off==(pmu_calls<2?0x1e04:0x2004));pmu_calls++;if(pmu_calls==pmu_error_at)return -EIO;*v=pmu_calls==pmu_bad_at?2:1;return 0;}
static void*request_mem_region(unsigned long a,unsigned n,const char*s){(void)s;assert(a==0x1c500000&&n==4);assert(pmu_calls==4);requests++;return request_busy?NULL:&mem;}
static void release_mem_region(unsigned long a,unsigned n){assert(a==0x1c500000&&n==4);releases++;}
static void*ioremap(unsigned long a,unsigned n){assert(a==0x1c500000&&n==4&&requests==1);maps++;return iomap_fail?NULL:&mem;}
static void iounmap(void*p){assert(p==&mem);unmaps++;}
static u32 readl(void*p){assert(p==&mem&&reads<2&&pmu_calls==4);return vals[reads++];}
static void reset(void){wrong_board=missing_node=enabled=bad_resource=no_map=request_busy=iomap_fail=pmu_error_at=pmu_bad_at=node_puts=pmu_calls=requests=releases=maps=unmaps=reads=0;vals[0]=vals[1]=0x92020001;}
'''
post=r'''
int main(void){reset();assert(oriole_gpu_id_read_init()==0);assert(reads==2&&pmu_calls==4&&node_puts==1&&releases==1&&unmaps==1);
for(unsigned i=1;i<=4;i++){reset();pmu_error_at=i;assert(oriole_gpu_id_read_init()==-EIO);assert(reads==0&&requests==0);reset();pmu_bad_at=i;assert(oriole_gpu_id_read_init()==-EAGAIN);assert(reads==0&&requests==0);}
unsigned*flags[]={&wrong_board,&missing_node,&enabled,&bad_resource,&no_map,&request_busy,&iomap_fail};
for(unsigned i=0;i<ARRAY_SIZE(flags);i++){reset();*flags[i]=1;assert(oriole_gpu_id_read_init()!=0);assert(reads==0);if(i==6)assert(releases==1&&unmaps==0);}
u32 invalid[]={0,0xffffffff,0x92030000};for(unsigned i=0;i<ARRAY_SIZE(invalid);i++){reset();vals[0]=vals[1]=invalid[i];assert(oriole_gpu_id_read_init()==-ENODEV);assert(unmaps==1&&releases==1);}
reset();vals[1]++;assert(oriole_gpu_id_read_init()==-EIO);assert(unmaps==1&&releases==1);oriole_gpu_id_read_exit();puts("PASS actual G5 init: power-before-MMIO, invalid ID, ownership/resource guards, map failure and cleanup; ASan/UBSan");}
'''
with tempfile.TemporaryDirectory() as d:
 p=Path(d);(p/'t.c').write_text(pre+s+post);subprocess.run(['clang','-std=c11','-Wall','-Wextra','-Werror','-fsanitize=address,undefined',str(p/'t.c'),'-o',str(p/'t')],check=True);subprocess.run([str(p/'t')],check=True)
