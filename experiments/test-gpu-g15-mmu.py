#!/usr/bin/env python3
"""Compile actual G7/G15 init/fini C with IRQ failures and ordered MMIO stubs."""
import importlib.util
import subprocess
import sys
import tempfile
from pathlib import Path

spec = importlib.util.spec_from_file_location('g15', Path(__file__).with_name('apply-gpu-g15.py'))
g15 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(g15)
old = Path(sys.argv[1]).read_text()
new = g15.transform(old)


def function(source, signature):
    start = source.index(signature)
    brace = source.index('{', start)
    depth = 1
    i = brace + 1
    while depth:
        depth += (source[i] == '{') - (source[i] == '}')
        i += 1
    return source[start:i]


prelude = r'''
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <errno.h>
#include <string.h>
struct device {int unused;};
struct panfrost_device {struct {struct device *dev;} base; int mmu_irq;};
#define MMU_INT_CLEAR 1
#define MMU_INT_MASK 2
#define IRQF_SHARED 4
#define KBUILD_MODNAME "panfrost"
static int lookup, request_result, requests, writes, owned;
static int regs[8]; static uint32_t values[8];
static void *to_platform_device(struct device *d) {return d;}
static int platform_get_irq_byname(void *d, const char *name) {
    assert(d && !strcmp(name,"mmu")); return lookup;
}
static int panfrost_mmu_irq_handler(void) {return 0;}
static int panfrost_mmu_irq_handler_thread(void) {return 0;}
static int devm_request_threaded_irq(struct device *d,int irq,int (*top)(void),int (*thread)(void),int flags,const char *name,void *data) {
    assert(d && data && irq==lookup && flags==IRQF_SHARED);
    assert(top==panfrost_mmu_irq_handler && thread==panfrost_mmu_irq_handler_thread);
    assert(!strcmp(name,"panfrost-mmu")); requests++; owned=!request_result;
    return request_result;
}
static void dev_err(struct device *d,const char *msg) {assert(d && msg);}
static void mmu_write(struct panfrost_device *d,int reg,uint32_t value) {
    assert(d && owned && writes<8); regs[writes]=reg; values[writes++]=value;
}
static void reset_stubs(void) {lookup=12;request_result=requests=writes=owned=0;}
'''
main = r'''
int main(void) {
    struct device dev={0}; struct panfrost_device pf={.base={&dev}};
    int failures[]={-ENODEV,-EIO,-517};
    for(unsigned i=0;i<sizeof(failures)/sizeof(failures[0]);i++) {
        reset_stubs(); lookup=failures[i];
        assert(panfrost_mmu_init(&pf)==failures[i] && !requests && !writes);
        reset_stubs(); request_result=failures[i];
        assert(panfrost_mmu_init(&pf)==failures[i] && requests==1 && !writes);
    }
    for(int i=0;i<3;i++) {
        reset_stubs(); assert(panfrost_mmu_init(&pf)==0 && requests==1);
        assert(writes==2 && regs[0]==MMU_INT_CLEAR && regs[1]==MMU_INT_MASK);
        assert(values[0]==UINT32_MAX && values[1]==UINT32_MAX);
        panfrost_mmu_fini(&pf);
        assert(writes==3 && regs[2]==MMU_INT_MASK && values[2]==0);
    }
    puts("PASS G15 actual C: lookup/request failures, ownership, ordered IRQ clear/unmask, teardown, repeated init/fini");
}
'''
with tempfile.TemporaryDirectory() as td:
    p = Path(td)
    for label, source in [('RED', old), ('GREEN', new)]:
        helper = function(source, 'static void panfrost_mmu_enable_interrupts(') if label == 'GREEN' else ''
        c = prelude + helper + function(source, 'int panfrost_mmu_init(') + function(source, 'void panfrost_mmu_fini(') + main
        (p/'t.c').write_text(c)
        subprocess.run(['clang','-std=c11','-Wall','-Wextra','-Werror','-fsanitize=address,undefined',str(p/'t.c'),'-o',str(p/'t')],check=True)
        run = subprocess.run([str(p/'t')],capture_output=True,text=True)
        if label == 'RED':
            assert run.returncode != 0 and 'writes==2' in run.stderr, run.stderr
            print('RED: original successful probe lacks required MMU interrupt writes')
        else:
            assert run.returncode == 0, run.stderr
            print(run.stdout.strip())
# The reset body is byte-identical after expanding the new helper call.
reset_old = function(old, 'void panfrost_mmu_reset(')
reset_new = function(new, 'void panfrost_mmu_reset(').replace('\tpanfrost_mmu_enable_interrupts(pfdev);','\tmmu_write(pfdev, MMU_INT_CLEAR, ~0);\n\tmmu_write(pfdev, MMU_INT_MASK, ~0);')
assert reset_new == reset_old
try:
    g15.transform(old + '\n')
except ValueError:
    print('PASS reset behavior preserved; unexpected source refused')
else:
    raise AssertionError('Source guard failed')

# Match the workflow's output-file contract, including non-overwrite behavior.
with tempfile.TemporaryDirectory() as td:
    output = Path(td) / 'mmu.c'
    command = [sys.executable, str(Path(__file__).with_name('apply-gpu-g15.py')), sys.argv[1], str(output)]
    subprocess.run(command, check=True)
    before = output.read_bytes()
    run = subprocess.run(command, capture_output=True, text=True)
    assert run.returncode != 0 and 'FileExistsError' in run.stderr
    assert output.read_bytes() == before
    print('PASS new output succeeds; existing output refused and preserved')
