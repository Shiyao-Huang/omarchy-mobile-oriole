from pathlib import Path
import re,subprocess,tempfile
s=Path('gpu-g6-overlay/oriole_gpu_overlay.c').read_text();assert not re.search(r'writel|iowrite|regmap_write|clk_set_rate|dma_alloc',s)
s='\n'.join(x for x in s.splitlines() if not x.startswith('#include'))
pre=r'''
#include <assert.h>
#include <stdint.h>
#include <stddef.h>
#include <stdio.h>
#include <string.h>
#include <errno.h>
#define __init
#define __exit
#define ARRAY_SIZE(a) (sizeof(a)/sizeof((a)[0]))
#define GS101_SUBBBLK_OFFSET_G3D 0x1e00
#define GS101_SUBBBLK_OFFSET_EMBEDDED_G3D 0x2000
#define GS101_SUBBLK_STATUS(x) ((x)+4)
#define pr_info(...) do { if (0) printf(__VA_ARGS__); } while(0)
#define pr_err(...) ((void)(undo))
#define IS_ERR(p) ((intptr_t)(p)<0)
#define PTR_ERR(p) ((int)(intptr_t)(p))
#define module_init(x)
#define module_exit(x)
#define MODULE_LICENSE(x)
#define MODULE_DESCRIPTION(x)
struct device_node{int n;};struct regmap{int n;};struct resource{unsigned long start,end;};struct clk{int n;};
struct of_phandle_args{struct device_node*np;int args_count;unsigned args[16];};
static const unsigned char gpu_dtbo[]={1,2};
static struct device_node node,acpm;static struct regmap map;static struct clk clk;
static unsigned wrong_board,missing_node,wrong_compat,enabled,bad_resource,no_map,missing_acpm,pmu_error_at,pmu_bad_at,clk_error_at,clk_zero_at,apply_fail,partial_apply;
static unsigned puts,pmu_calls,clk_calls,clk_puts,applies,removes;
static int of_machine_is_compatible(const char*s){(void)s;return !wrong_board;}
static struct device_node*of_find_node_by_path(const char*s){if(strstr(s,"gpu@"))return missing_node?NULL:&node;assert(!strcmp(s,"/firmware/power-management"));return missing_acpm?NULL:&acpm;}
static int of_device_is_compatible(struct device_node*n,const char*s){assert(n==&node);(void)s;return !wrong_compat;}
static int of_device_is_available(struct device_node*n){assert(n==&node);return enabled;}
static void of_node_put(struct device_node*n){assert(n==&node||n==&acpm);puts++;}
static int of_address_to_resource(struct device_node*n,int i,struct resource*r){assert(n==&node&&i==0);r->start=0x1c500000+bad_resource;r->end=r->start+0x4fff;return 0;}
static unsigned long resource_size(struct resource*r){return r->end-r->start+1;}
static struct regmap*exynos_get_pmu_regmap(void){return no_map?NULL:&map;}
static int regmap_read(struct regmap*m,unsigned off,unsigned*v){assert(m==&map);assert(off==(pmu_calls<2?0x1e04:0x2004));pmu_calls++;if(pmu_calls==pmu_error_at)return -EIO;*v=pmu_calls==pmu_bad_at?2:1;return 0;}
static struct clk*of_clk_get_from_provider(struct of_phandle_args*s){assert(s->np==&acpm&&s->args_count==1&&s->args[0]==5+clk_calls&&pmu_calls==4);clk_calls++;return clk_calls==clk_error_at?(void*)(intptr_t)-EAGAIN:&clk;}
static unsigned long clk_get_rate(struct clk*c){assert(c==&clk);return clk_calls==clk_zero_at?0:151000000;}
static void clk_put(struct clk*c){assert(c==&clk);clk_puts++;}
static int of_overlay_fdt_apply(const void*p,unsigned n,int*id,const struct device_node*b){assert(p==gpu_dtbo&&n==sizeof(gpu_dtbo)&&!b&&pmu_calls==4&&clk_calls==2&&clk_puts==2);applies++;*id=(!apply_fail||partial_apply)?1:0;return apply_fail?-EINVAL:0;}
static int of_overlay_remove(int*id){assert(*id==1);*id=0;removes++;return 0;}
static void reset(void){wrong_board=missing_node=wrong_compat=enabled=bad_resource=no_map=missing_acpm=pmu_error_at=pmu_bad_at=clk_error_at=clk_zero_at=apply_fail=partial_apply=puts=pmu_calls=clk_calls=clk_puts=applies=removes=0;}
'''.replace('puts,','node_puts,').replace('puts++;','node_puts++;').replace('=puts=','=node_puts=').replace('clk_node_puts','clk_puts')
post=r'''
int main(void){reset();assert(oriole_gpu_overlay_init()==0);assert(applies==1&&overlay_id==1);oriole_gpu_overlay_exit();assert(removes==1&&overlay_id==0);
unsigned*flags[]={&wrong_board,&missing_node,&wrong_compat,&enabled,&bad_resource,&no_map,&missing_acpm};for(unsigned i=0;i<ARRAY_SIZE(flags);i++){reset();*flags[i]=1;assert(oriole_gpu_overlay_init()!=0);assert(applies==0);}
for(unsigned i=1;i<=4;i++){reset();pmu_error_at=i;assert(oriole_gpu_overlay_init()==-EIO);assert(applies==0&&clk_calls==0);reset();pmu_bad_at=i;assert(oriole_gpu_overlay_init()==-EAGAIN);assert(applies==0&&clk_calls==0);}
for(unsigned i=1;i<=2;i++){reset();clk_error_at=i;assert(oriole_gpu_overlay_init()==-EAGAIN);assert(applies==0&&clk_puts==i-1);reset();clk_zero_at=i;assert(oriole_gpu_overlay_init()==-EIO);assert(applies==0&&clk_puts==i);}
reset();apply_fail=1;assert(oriole_gpu_overlay_init()==-EINVAL);assert(removes==0);reset();apply_fail=partial_apply=1;assert(oriole_gpu_overlay_init()==-EINVAL);assert(removes==1&&overlay_id==0);
printf("PASS actual G6 guard/init/cleanup source ASan UBSan\n");}
'''
with tempfile.TemporaryDirectory() as td:
 p=Path(td);(p/'t.c').write_text(pre+s+post);subprocess.run(['clang','-std=c11','-Wall','-Wextra','-Werror','-fsanitize=address,undefined',str(p/'t.c'),'-o',str(p/'t')],check=True);subprocess.run([str(p/'t')],check=True)
