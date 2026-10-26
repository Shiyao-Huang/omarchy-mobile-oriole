#!/usr/bin/env python3
"""Compile the actual bank decoder and window chunker with MMIO mocks.

Usage: test-wifi-w2-source.py BASE_BRCMFMAC CANDIDATE_BRCMFMAC
Hardware, DMA, locking and firmware behavior remain separate acceptance gates.
"""
from pathlib import Path
import re
import subprocess
import sys
import tempfile


def function(source, name):
    match = re.search(r'\b' + name + r'\([^;]*?\)\s*\{', source, re.S)
    assert match, name
    start = match.start()
    opening = source.index('{', start)
    depth = 1
    end = opening + 1
    while depth:
        depth += (source[end] == '{') - (source[end] == '}')
        end += 1
    return 'static unsigned int ' + source[start:end]


PRELUDE = r'''
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
typedef uint32_t u32;
#define BRCM_CC_4389_CHIP_ID 4389
#define SYSMEMREGOFFS(x) 0
#define brcmf_dbg(...) ((void)0)
struct chip { struct {u32 chip;} pub; };
struct core {u32 rev;};
struct brcmf_core_priv {struct core pub; struct chip *chip;};
static u32 info, banks[256], seen[256], count;
static int brcmf_chip_iscoreup(struct core *c) {(void)c;return 1;}
static void brcmf_chip_resetcore(struct core *c,int a,int b,int d)
{(void)c;(void)a;(void)b;(void)d;}
static u32 brcmf_chip_core_read32(struct brcmf_core_priv *c,int r)
{(void)c;(void)r;return info;}
static void brcmf_chip_socram_banksize(struct brcmf_core_priv *c,u32 i,u32 *s)
{(void)c;if(i>=256||count>=256)abort();seen[count++]=i;*s=banks[i];}
'''
BANK_MAIN = r'''
int main(void) {
 struct chip chip={{4389}}; struct brcmf_core_priv c={{11},&chip};
 for (u32 i=0;i<256;i++) banks[i]=i<8?262144:131072;
 info=0x115; count=0;
 u32 size=brcmf_chip_sysmem_ramsize(&c);
 if(size!=2752512 || count!=21 || seen[0]!=8 || seen[20]!=28) return 42;
 c.pub.rev=12; info=(21<<16)|(8<<24);count=0;
 if(brcmf_chip_sysmem_ramsize(&c)!=2752512 || seen[0]!=8) return 43;
 info=0;count=0;if(brcmf_chip_sysmem_ramsize(&c)!=0||count!=0)return 44;
 chip.pub.chip=4350; info=3<<SRCI_SRNB_SHIFT;count=0;
 if(brcmf_chip_sysmem_ramsize(&c)!=3*262144||seen[0]!=0)return 45;
 puts("bank decoder PASS: rev11/rev12/empty/legacy");return 0;
}
'''


def compile_run(code, folder, name):
    src, binary = folder / (name + '.c'), folder / name
    src.write_text(code)
    subprocess.run(['cc', '-std=c11', '-Wall', '-Wextra', '-Werror',
                    '-fsanitize=address,undefined', str(src), '-o', str(binary)], check=True)
    return subprocess.run([str(binary)], capture_output=True, text=True)


base, candidate = map(Path, sys.argv[1:])
with tempfile.TemporaryDirectory() as tmp:
    folder = Path(tmp)
    for label, root in [('base', base), ('candidate', candidate)]:
        source = (root / 'chip.c').read_text()
        defs = '\n'.join(line for line in source.splitlines()
                         if re.match(r'#define\s+(SYSMEM_SRCI_|SRCI_SRNB)', line))
        assert re.search(r'#define\s+SRCI_SRNB_MASK\s', defs)
        result = compile_run(PRELUDE + defs + '\n' +
                             function(source, 'brcmf_chip_sysmem_ramsize') + BANK_MAIN,
                             folder, label)
        assert result.returncode == (42 if label == 'base' else 0), (label, result)
        print(label, 'expected RED' if label == 'base' else result.stdout.strip())
    source = (candidate / 'pcie.c').read_text()
    defs = '\n'.join(line for line in source.splitlines()
                     if re.match(r'#define\s+BRCMF_PCIE_TCM_COPY_CHUNK\s', line))
    chunk = r'''
#include <stdint.h>
#include <stdio.h>
typedef uint32_t u32;
#define min_t(t,a,b) ((t)(a)<(t)(b)?(t)(a):(t)(b))
struct brcmf_pciedev_info {u32 tcm_size; int tcm_win_switch;};
'''+ defs + '\n' + function(source, 'brcmf_pcie_tcm_chunk') + r'''
int main(void) {
 struct brcmf_pciedev_info d={0x400000,1};
 const u32 starts[]={0,0x200000,0x3fffff,0x3ff800,0x400000,0x49ffff};
 const u32 lengths[]={0,1,2,4096,8193};
 for(unsigned i=0;i<sizeof(starts)/sizeof(*starts);i++)
  for(unsigned j=0;j<sizeof(lengths)/sizeof(*lengths);j++) {
   u32 addr=starts[i],left=lengths[j],total=0;
   while(left){u32 n=brcmf_pcie_tcm_chunk(&d,addr,left);
    if(!n||n>left||n>4096||(addr% d.tcm_size)+n>d.tcm_size)return 1;
    addr+=n;left-=n;total+=n;}
   if(total!=lengths[j])return 2;
  }
 d.tcm_win_switch=0;
 if(brcmf_pcie_tcm_chunk(&d,0x3fffff,4096)!=4096)return 3;
 puts("window chunker PASS: boundaries, zero, multi-chunk, legacy");return 0;
}
'''
    result = compile_run(chunk, folder, 'chunk')
    assert result.returncode == 0, result
    print(result.stdout.strip())
