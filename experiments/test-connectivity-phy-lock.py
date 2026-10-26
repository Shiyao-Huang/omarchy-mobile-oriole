#!/usr/bin/env python3
"""Bounded polling of actual PHY C; no live MMIO."""
from pathlib import Path
import subprocess,sys,tempfile
p=Path(sys.argv[1]);code=(p/'phy-lock.inc').read_text()
prefix=r'''
#include <stdint.h>
#include <stdbool.h>
#include <assert.h>
#include <stdio.h>
typedef uint32_t u32;
struct gs101_pcie_phy {char *phy_base;};
static char regs[0x2000];
static unsigned reads,delays,ready_after,expected_offset,value;
static void udelay(unsigned us) {assert(us==1);++delays;}
static u32 readl(char *addr) {assert(addr==regs+expected_offset);++reads;return reads>=ready_after?value:0;}
'''
cases=r'''
int main(void) {
 struct gs101_pcie_phy phy={regs};u32 last;
 unsigned offsets[]={0x3f0,0xe0c,0xde8},masks[]={8,4,15};
 for(unsigned i=0;i<3;i++) {
  expected_offset=offsets[i];value=masks[i];reads=delays=0;ready_after=1;
  assert(gs101_pcie_phy_poll(&phy,offsets[i],masks[i],&last));assert(reads==1 && delays==1 && last==masks[i]);
  reads=delays=0;ready_after=10000;
  assert(gs101_pcie_phy_poll(&phy,offsets[i],masks[i],&last));assert(reads==10000 && delays==10000);
  reads=delays=0;ready_after=10001;
  assert(!gs101_pcie_phy_poll(&phy,offsets[i],masks[i],&last));assert(reads==10000 && delays==10000 && last==0);
 }
 expected_offset=0xde8;value=7;reads=delays=0;ready_after=1;
 assert(!gs101_pcie_phy_poll(&phy,0xde8,15,&last));assert(reads==10000 && last==7);
 puts("PASS: exact PHY polling, first/last iteration, timeout and partial mask");
}
'''
with tempfile.TemporaryDirectory() as tmp:
 t=Path(tmp);(t/'test.c').write_text(prefix+code+cases)
 subprocess.run(['cc','-std=c11','-Wall','-Wextra','-Werror','-fsanitize=address,undefined',str(t/'test.c'),'-o',str(t/'test')],check=True)
 subprocess.run([str(t/'test')],check=True)
