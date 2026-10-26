#!/usr/bin/env python3
"""Execute actual GS101 initialisation C with failure-injected kernel APIs."""
from pathlib import Path
import subprocess, sys, tempfile
d=Path(sys.argv[1]);s=(d/'pcie-gs101.c').read_text()
def function(signature):
    a=s.index(signature);b=s.index('{',a)+1;depth=1;i=b
    while depth:
        depth+=(s[i]=='{')-(s[i]=='}');i+=1
    return s[a:i]+'\n'
code=(d/'pmu-owner.inc').read_text()
if (d/'reset-rc.inc').exists():code+=(d/'reset-rc.inc').read_text()
code+=function('static int gs101_pcie_host_init(')
code+=function('static void gs101_pcie_host_deinit(')
prefix=r'''
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stddef.h>
#include <stdio.h>
#include <errno.h>
typedef uint32_t u32;
#define PCIE_PHY_ISOLATION 1U
#define PCIE_PHY_CTRL_LINK (1U<<10)
struct device {int dummy;};
struct dw_pcie_rp {int dummy;};
struct dw_pcie {struct dw_pcie_rp pp;struct device *dev;};
struct gs101_pcie {struct dw_pcie pci;void *pmureg,*clks,*perst,*phy;
 int num_clks,ch_num;u32 pmu_offset,pmu_saved;bool pmu_saved_valid;};
#define to_dw_pcie_from_pp(pp) ((struct dw_pcie *)(pp))
#define to_gs101_pcie(pci) ((struct gs101_pcie *)(pci))
#define dev_err(dev,...) ((void)(dev))
static u32 reg;
static unsigned expected_offset=0x3ec4, delay_calls, endpoint_delay=20000;
static unsigned soft_reset, device_type, reset_writes;
#define PCIE_SOFT_RESET 0x3a4
#define PCIE_DEVICE_TYPE 0x80
#define DEVICE_TYPE_RC 4
#define SOFT_PWR_RESET 2U
#define SOFT_NON_STICKY_RESET 8U
static int reads,writes,read_fail,write_fail,write_fail2,ambiguous,ignored;
static int clocks,disabled,clock_error,phy_calls,phy_exits,phy_error,phy_exit_error,setup,reset_level;
static int regmap_read(void *m,unsigned off,u32 *out) {
 (void)m;assert(off==expected_offset);++reads;if(reads==read_fail)return -EIO;*out=reg;return 0;
}
static int regmap_update_bits(void *m,unsigned off,u32 mask,u32 value) {
 (void)m;assert(off==expected_offset && !(mask & ~1U));++writes;
 if(writes==write_fail || writes==write_fail2) {
  if(ambiguous)reg=(reg & ~mask)|(value & mask);
  return -EIO;
 }
 if(writes!=ignored)reg=(reg & ~mask)|(value & mask);
 return 0;
}
static int clk_bulk_prepare_enable(int n,void *p) {(void)n;(void)p;if(clock_error)return clock_error;++clocks;return 0;}
static void clk_bulk_disable_unprepare(int n,void *p) {(void)n;(void)p;assert(clocks==1);--clocks;++disabled;}
static void gpiod_set_value_cansleep(void *p,int v) {(void)p;reset_level=v;}
static int phy_init(void *p) {(void)p;++phy_calls;return phy_error;}
static int phy_exit(void *p) {(void)p;++phy_exits;return phy_exit_error;}
static void usleep_range(int a,int b) {
 static const unsigned min_delays[]={1000,10,1000},max_delays[]={1100,12,1100};
 if(delay_calls<3){assert(a==(int)min_delays[delay_calls] && b==(int)max_delays[delay_calls]);assert(reset_level==1);}
 else {assert(delay_calls==3 && a==(int)endpoint_delay && b==(int)endpoint_delay+2000 && reset_level==0);}
 ++delay_calls;
}
static void gs101_pcie_setup_elbi(struct gs101_pcie *p) {(void)p;assert(reset_level==0 && device_type==4 && reset_writes==5);++setup;}
static u32 gs101_elbi_read(struct gs101_pcie *p,u32 off) {(void)p;assert(reset_level==1 && clocks==1 && phy_calls==1 && !setup);assert(off==PCIE_SOFT_RESET);return soft_reset;}
static void gs101_elbi_write(struct gs101_pcie *p,u32 val,u32 off) {
 (void)p;assert(reset_level==1 && clocks==1 && phy_calls==1 && !setup);
 if(off==PCIE_DEVICE_TYPE){assert(val==4 && reset_writes==2);device_type=val;return;}
 assert(off==PCIE_SOFT_RESET && (val & ~10U)==0x100U);
 static const unsigned sequence[]={0x100,0x102,0x10a,0x102,0x10a};
 assert(reset_writes<5 && val==sequence[reset_writes++]);soft_reset=val;
}
static void reset(struct gs101_pcie *p) {
 delay_calls=0;reg=0x2400;soft_reset=0x102;device_type=reset_writes=0;reads=writes=read_fail=write_fail=write_fail2=ambiguous=ignored=0;
 clocks=disabled=clock_error=phy_calls=phy_exits=phy_error=phy_exit_error=setup=reset_level=0;
 p->pmu_saved=0;p->pmu_saved_valid=false;
}
'''
cases=r'''
int main(void) {
 struct device dev={0};struct gs101_pcie p={.pci.dev=&dev,.pmu_offset=0x3ec4,.ch_num=1};
 /* Stock mask is independent of the implementation: bit10 must not be owned. */
 assert(GS101_PCIE_PMU_OWNED==1U);
 reset(&p);assert(gs101_pcie_pmu_begin(&p)==0);
 assert(gs101_pcie_pmu_update(&p,1U<<10,1U<<10)==-EINVAL && writes==0);
 reset(&p);clock_error=-EAGAIN;
 assert(gs101_pcie_host_init(&p.pci.pp)==-EAGAIN && reads==0 && writes==0 && disabled==0);
 reset(&p);read_fail=1;
 assert(gs101_pcie_host_init(&p.pci.pp)==-EIO && writes==0 && phy_calls==0 && disabled==1);
 reset(&p);write_fail=1;ambiguous=1;
 assert(gs101_pcie_host_init(&p.pci.pp)==-EIO && phy_calls==0 && setup==0 && reg==0x2400 && disabled==1);
 reset(&p);ignored=1;
 assert(gs101_pcie_host_init(&p.pci.pp)==-EIO && phy_calls==0 && setup==0 && reg==0x2400 && disabled==1);
 reset(&p);read_fail=2;
 assert(gs101_pcie_host_init(&p.pci.pp)==-EIO && phy_calls==0 && setup==0 && reg==0x2400 && disabled==1);
 reset(&p);phy_error=-ENODEV;
 assert(gs101_pcie_host_init(&p.pci.pp)==-ENODEV && setup==0 && reg==0x2400 && disabled==1);
 reset(&p);phy_error=-ENODEV;write_fail=2;
 assert(gs101_pcie_host_init(&p.pci.pp)==-ENODEV && setup==0 && disabled==0 && clocks==1 && p.pmu_saved_valid);
 reset(&p);assert(gs101_pcie_host_init(&p.pci.pp)==0);
 assert(reg==0x2401 && setup==1 && clocks==1 && p.pmu_saved_valid && delay_calls==4);
 /* Simulate an independent owner's change while PCIe is active. */
 reg=0x6001;
 gs101_pcie_host_deinit(&p.pci.pp);
 assert(reg==0x6000 && reset_level==1 && phy_exits==1 && disabled==1 && !p.pmu_saved_valid);
 reset(&p);assert(gs101_pcie_host_init(&p.pci.pp)==0);write_fail=2;
 gs101_pcie_host_deinit(&p.pci.pp);
 assert(disabled==0 && clocks==1 && p.pmu_saved_valid);
 reset(&p);assert(gs101_pcie_host_init(&p.pci.pp)==0);phy_exit_error=-EIO;
 gs101_pcie_host_deinit(&p.pci.pp);assert(disabled==0 && clocks==1);
 reset(&p);p.pmu_offset=0x3ec0;
 assert(gs101_pcie_host_init(&p.pci.pp)==-EINVAL && writes==0 && reads==0 && disabled==1);
 reset(&p);p.ch_num=0;p.pmu_offset=expected_offset=0x3ec0;endpoint_delay=18000;
 assert(gs101_pcie_host_init(&p.pci.pp)==0 && delay_calls==4 && reg==0x2401);
 gs101_pcie_host_deinit(&p.pci.pp);assert(reg==0x2400 && disabled==1);
 puts("PASS: GS101 bit0-only ownership, initial reset/RC ordering, failure cleanup and independent-bit preservation");
}
'''
with tempfile.TemporaryDirectory(prefix='oriole-pmu-') as tmp:
    p=Path(tmp);(p/'probe.c').write_text(prefix+code+cases)
    subprocess.run(['cc','-std=c11','-Wall','-Wextra','-Werror','-Wno-unused-function',
                    '-fsanitize=address,undefined','-g',str(p/'probe.c'),'-o',str(p/'probe')],check=True)
    subprocess.run([str(p/'probe')],check=True)
