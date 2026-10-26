#!/usr/bin/env python3
"""Exercise the actual borrowed MSI demultiplexer with independent IRQ oracles.

Host-side MMIO stubs cannot prove GS101 interrupt delivery or recovery.
"""
from pathlib import Path
import subprocess
import tempfile

helper = Path(__file__).parent / 'connectivity-n2/msi-demux.inc'
prefix = r'''
#include <assert.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#define MAX_MSI_IRQS_PER_CTRL 32
#define MSI_REG_CTRL_BLOCK_SIZE 12
#define PCIE_MSI_INTR0_STATUS 0x830
#define for_each_set_bit(pos, ptr, limit) \
 for ((pos)=0; (pos)<(limit); ++(pos)) if ((*(ptr)) & (1UL << (pos)))
struct dw_pcie_rp { unsigned num_vectors; void *irq_domain; };
struct dw_pcie { struct dw_pcie_rp pp; };
#define to_dw_pcie_from_pp(p) ((struct dw_pcie *)(p))
static uint32_t banks[8];
static unsigned seen[256], reads;
static uint32_t dw_pcie_readl_dbi(struct dw_pcie *p, unsigned addr) {
 (void)p;
 assert(addr >= PCIE_MSI_INTR0_STATUS);
 unsigned off=addr-PCIE_MSI_INTR0_STATUS;
 assert(off % MSI_REG_CTRL_BLOCK_SIZE == 0);
 assert(off/MSI_REG_CTRL_BLOCK_SIZE < 8);
 ++reads;
 return banks[off/MSI_REG_CTRL_BLOCK_SIZE];
}
static void generic_handle_demux_domain_irq(void *domain, unsigned irq) {
 assert(domain == (void *)0x1234);
 assert(irq < 256);
 ++seen[irq];
}
'''
suffix = r'''
static void reset(void) {
 for(unsigned i=0;i<8;i++) banks[i]=0;
 for(unsigned i=0;i<256;i++) seen[i]=0;
 reads=0;
}
int main(void) {
 struct dw_pcie pci={.pp={.num_vectors=256,.irq_domain=(void *)0x1234}};
 reset();
 oriole_n2_handle_msi_irq(&pci.pp);
 assert(reads==8);
 for(unsigned i=0;i<256;i++) assert(seen[i]==0);
 reset(); banks[0]=0x80000001U; banks[1]=1U; banks[7]=0x80000000U;
 oriole_n2_handle_msi_irq(&pci.pp);
 for(unsigned i=0;i<256;i++) assert(seen[i]==(i==0||i==31||i==32||i==255));
 reset(); for(unsigned i=0;i<8;i++) banks[i]=0xffffffffU;
 oriole_n2_handle_msi_irq(&pci.pp);
 for(unsigned i=0;i<256;i++) assert(seen[i]==1);
 reset(); pci.pp.num_vectors=32; banks[0]=4U; banks[1]=0xffffffffU;
 oriole_n2_handle_msi_irq(&pci.pp);
 assert(reads==1);
 for(unsigned i=0;i<256;i++) assert(seen[i]==(i==2));
 puts("PASS: empty, bank boundaries, dense MSI, unused-bank exclusion");
}
'''
with tempfile.TemporaryDirectory(prefix='oriole-msi-') as tmp:
    path = Path(tmp)
    (path / 'probe.c').write_text(prefix + helper.read_text() + suffix)
    subprocess.run(['cc', '-std=c11', '-Wall', '-Wextra', '-Werror',
                    '-fsanitize=address,undefined', '-g', str(path / 'probe.c'),
                    '-o', str(path / 'probe')], check=True)
    subprocess.run([str(path / 'probe')], check=True)
