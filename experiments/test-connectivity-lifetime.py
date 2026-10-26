#!/usr/bin/env python3
"""Exercise actual PCIe C helpers with independent resource/IRQ oracles.

Stubs prove software ordering only, not interrupt delivery or hardware recovery.
"""
from pathlib import Path
import subprocess, tempfile, sys

d = Path(sys.argv[1])
s = (d / 'pcie-gs101.c').read_text()
start = s.index('static irqreturn_t gs101_pcie_irq_handler(')
begin = s.index('{', start)
depth, end = 1, begin + 1
while depth:
    depth += (s[end] == '{') - (s[end] == '}')
    end += 1
handler = s[start:end]
helper = d / 'irq-lifetime.inc'
prefix = r'''
#include <assert.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <string.h>
#include <stdio.h>
typedef uint32_t u32;
typedef int irqreturn_t;
#define IRQ_NONE 0
#define IRQ_HANDLED 1
#define IRQF_SHARED 128
#define PCIE_IRQ2 8
#define PCIE_IRQ2_EN 24
#define IRQ_MSI_RISING_ASSERT (1U<<17)
#define IRQ_MSI_CTRL_EN_RISING_EDG (1U<<17)
struct device {int unused;};
struct pci_host_bridge {void *bus;};
struct dw_pcie_rp {struct pci_host_bridge *bridge;};
struct gs101_pcie {struct {struct device *dev; struct dw_pcie_rp pp;} pci;
 int irq, ch_num; bool irq_registered;};
static struct gs101_pcie *gs101_pcie_ch[2];
static u32 status, enable_bits, acknowledged;
static int writes, dispatched, request_error, action_error, freed, deinit;
static void (*saved_cleanup)(void *);
static void *saved_data;
static char order[32]; static unsigned n;
static int locked;
static void pci_lock_rescan_remove(void) {assert(!locked);locked=1;}
static void pci_stop_root_bus(void *bus) {assert(locked && bus);order[n++]='C';}
static void pci_unlock_rescan_remove(void) {assert(locked);locked=0;}
static u32 gs101_elbi_read(struct gs101_pcie *p, u32 reg) {
 (void)p; assert(reg==PCIE_IRQ2 || reg==PCIE_IRQ2_EN);
 return reg==PCIE_IRQ2?status:enable_bits;
}
static void gs101_elbi_write(struct gs101_pcie *p,u32 val,u32 reg) {
 (void)p; ++writes;
 if(reg==PCIE_IRQ2) acknowledged=val;
 else {assert(reg==PCIE_IRQ2_EN);enable_bits=val;order[n++]=(val & IRQ_MSI_CTRL_EN_RISING_EDG)?'E':'M';}
}
static void oriole_n2_handle_msi_irq(struct dw_pcie_rp *p) {(void)p;++dispatched;}
static int request_irq(int irq,irqreturn_t (*fn)(int,void*),unsigned flags,const char *name,void *data) {
 assert(irq==42 && fn && flags==IRQF_SHARED && name && data);return request_error;
}
static void free_irq(int irq,void *data) {
 assert(irq==42 && data && !(enable_bits & IRQ_MSI_CTRL_EN_RISING_EDG));
 ++freed;order[n++]='F';
}
static void dw_pcie_host_deinit(struct dw_pcie_rp *p) {(void)p;++deinit;order[n++]='H';}
static int devm_add_action_or_reset(struct device *dev,void (*fn)(void*),void *data) {
 assert(dev); if(action_error)fn(data);else {saved_cleanup=fn;saved_data=data;}return action_error;
}
static void reset(void) {
 status=0;enable_bits=1U<<9;acknowledged=0;writes=dispatched=request_error=action_error=freed=deinit=0;
 n=0;memset(order,0,sizeof(order));saved_cleanup=NULL;saved_data=NULL;
 gs101_pcie_ch[0]=gs101_pcie_ch[1]=NULL;
}
'''
irq_cases = r'''
int main(void) {
 struct device dev={0};struct pci_host_bridge bridge={.bus=&dev};
 struct gs101_pcie p={.pci.dev=&dev,.pci.pp.bridge=&bridge,.ch_num=1};
 reset(); assert(gs101_pcie_irq_handler(42,&p)==IRQ_NONE);assert(writes==0&&dispatched==0);
 reset();status=1U<<3;assert(gs101_pcie_irq_handler(42,&p)==IRQ_NONE);assert(writes==0&&dispatched==0);
 reset();status=IRQ_MSI_RISING_ASSERT|(1U<<3);assert(gs101_pcie_irq_handler(42,&p)==IRQ_HANDLED);
 assert(acknowledged==IRQ_MSI_RISING_ASSERT && dispatched==1);
'''
lifetime_cases = r'''
 reset();request_error=-16;assert(gs101_pcie_attach_irq(&p,42)==-16);
 assert(deinit==1 && freed==0 && !strcmp(order,"H") && !p.irq_registered);
 reset();action_error=-12;assert(gs101_pcie_attach_irq(&p,42)==-12);
 assert(deinit==1 && freed==1 && !strcmp(order,"CMFH") && !p.irq_registered);
 reset();assert(gs101_pcie_attach_irq(&p,42)==0);assert(saved_cleanup && p.irq_registered);
 assert(gs101_pcie_ch[1]==&p && enable_bits==((1U<<9)|IRQ_MSI_CTRL_EN_RISING_EDG));
 saved_cleanup(saved_data);assert(gs101_pcie_ch[1]==NULL && freed==1 && deinit==1);
 assert(!strcmp(order,"ECMFH") && !p.irq_registered && enable_bits==(1U<<9));
 reset();assert(gs101_pcie_attach_irq(&p,42)==0);
 struct gs101_pcie other={0};gs101_pcie_ch[1]=&other;
 saved_cleanup(saved_data);assert(gs101_pcie_ch[1]==&other);
 puts("PASS: shared IRQ ownership, request/action failure, teardown order, registry ownership");
'''
suffix = irq_cases + (lifetime_cases if helper.exists() else '') + '\nreturn 0;\n}\n'
with tempfile.TemporaryDirectory(prefix='oriole-pcie-life-') as tmp:
    path=Path(tmp)
    (path/'probe.c').write_text(prefix+handler+'\n'+(helper.read_text() if helper.exists() else '')+suffix)
    subprocess.run(['cc','-std=c11','-Wall','-Wextra','-Wno-unused-function','-Wno-unused-parameter',
                    '-fsanitize=address,undefined','-g',str(path/'probe.c'),'-o',str(path/'probe')],check=True)
    subprocess.run([str(path/'probe')],check=True)
