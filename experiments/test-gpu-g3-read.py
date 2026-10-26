from pathlib import Path
import subprocess,tempfile,sys
src=Path(sys.argv[1]).read_text();body=src[src.index('static int __init'):src.index('static void __exit')]
h=r'''
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#define __init
#define ENODEV 19
#define EINVAL 22
#define ARRAY_SIZE(a) (sizeof(a)/sizeof((a)[0]))
#define IS_ERR(p) ((intptr_t)(p)<0)
#define PTR_ERR(p) ((int)(intptr_t)(p))
#define pr_info(...) ((void)0)
struct device_node {int unused;}; struct clk {int unused;};
struct of_phandle_args {struct device_node *np; unsigned args_count,args[1];};
static struct device_node node;static struct clk clock1;
static unsigned which,ids[]={11,22,33},lookups,nodeput,clkput,ratecalls,enabledcalls;
static bool compatible,found;static int error;
static bool of_machine_is_compatible(const char*s){return compatible;}
static struct device_node* of_find_compatible_node(void*a,void*b,const char*c){lookups++;return found?&node:0;}
static struct clk* of_clk_get_from_provider(struct of_phandle_args*a){assert(a->np==&node);assert(a->args_count==1);assert(a->args[0]==ids[which]);return error?(struct clk*)(intptr_t)error:&clock1;}
static void of_node_put(struct device_node*n){assert(n==&node);nodeput++;}
static unsigned long clk_get_rate(struct clk*c){assert(c==&clock1);ratecalls++;return 123;}
static bool __clk_is_enabled(struct clk*c){assert(c==&clock1);enabledcalls++;return true;}
static void clk_put(struct clk*c){assert(c==&clock1);clkput++;}
static void reset(void){which=0;lookups=nodeput=clkput=ratecalls=enabledcalls=0;compatible=found=true;error=0;}
'''
t=r'''
int main(void){
 reset();compatible=false;assert(oriole_gpu_clock_read_init()==-ENODEV);assert(!lookups);
 reset();which=3;assert(oriole_gpu_clock_read_init()==-EINVAL);assert(!lookups);
 reset();which=~0u;assert(oriole_gpu_clock_read_init()==-EINVAL);assert(!lookups);
 reset();found=false;assert(oriole_gpu_clock_read_init()==-ENODEV);assert(!nodeput);
 reset();error=-517;assert(oriole_gpu_clock_read_init()==-517);assert(nodeput==1&&!clkput&&!ratecalls);
 for(unsigned i=0;i<3;i++){reset();which=i;assert(oriole_gpu_clock_read_init()==0);assert(nodeput==1&&clkput==1&&ratecalls==1&&enabledcalls==1);}
 puts("PASS actual G3 init guards, provider errors, reference lifecycle and three clock selections; hardware values excluded");
}
'''
for bad in ('clk_prepare(', 'clk_enable(', 'clk_prepare_enable(', 'clk_set_rate(', 'writel(', 'ioremap('):assert bad not in src,bad
with tempfile.TemporaryDirectory() as d:
 p=Path(d);(p/'test.c').write_text(h+body+t);subprocess.run(['cc','-fsanitize=address,undefined','-g',str(p/'test.c'),'-o',str(p/'test')],check=True);subprocess.run([str(p/'test')],check=True)
