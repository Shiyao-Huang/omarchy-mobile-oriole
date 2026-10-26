"""Execute the actual regulator-owner C against fault-injected kernel APIs."""
from pathlib import Path
import subprocess,sys,tempfile
d=Path(sys.argv[1]);source=(d/'pcie-gs101.c').read_text()
helper=(d/'supply-owner.inc').read_text()
probe=source[source.index('static int gs101_pcie_probe('):source.index('void exynos_pcie_set_perst_gpio(int ch_num, bool on)\n{')]
assert probe.index('devm_gpiod_get')<probe.index('gs101_pcie_vpcie_enable(pcie)')<probe.index('dw_pcie_host_init(pp)')<probe.index('gs101_pcie_attach_irq(pcie, irq)')
prefix=r'''
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <errno.h>
#include <stddef.h>
struct device {int n;};struct regulator {int n;};
struct gs101_pcie {struct {struct device *dev;} pci;int ch_num;struct regulator *vpcie;bool vpcie_enabled;};
static struct regulator rail;static int get_error,enable_error,action_error,disable_error,gets,enables,disables,logs;
static void (*cleanup)(void *);static void *cleanup_data;
#define ERR_PTR(n) ((void *)(intptr_t)(n))
#define IS_ERR(p) ((intptr_t)(p)<0)
#define PTR_ERR(p) ((intptr_t)(p))
#define dev_err(dev,...) ((void)(dev),++logs)
static struct regulator *devm_regulator_get(struct device *d,const char *s) {(void)d;assert(s[0]=='v');++gets;return get_error?ERR_PTR(get_error):&rail;}
static int regulator_enable(struct regulator *r) {assert(r==&rail);++enables;return enable_error;}
static int regulator_disable(struct regulator *r) {assert(r==&rail);++disables;return disable_error;}
static int devm_add_action_or_reset(struct device *d,void(*fn)(void *),void *data) {(void)d;if(action_error){fn(data);return action_error;}cleanup=fn;cleanup_data=data;return 0;}
static void reset(struct gs101_pcie *p) {get_error=enable_error=action_error=disable_error=gets=enables=disables=logs=0;cleanup=NULL;cleanup_data=NULL;p->vpcie=NULL;p->vpcie_enabled=false;}
'''
cases=r'''
int main(void) {
 struct device dev={0};struct gs101_pcie p={.pci.dev=&dev,.ch_num=1};
 reset(&p);get_error=-EIO;assert(gs101_pcie_vpcie_enable(&p)==-EIO);assert(gets==1 && enables==0 && !cleanup);
 reset(&p);enable_error=-EIO;assert(gs101_pcie_vpcie_enable(&p)==-EIO);assert(enables==1 && disables==0 && !p.vpcie_enabled && !cleanup);
 reset(&p);action_error=-ENOMEM;assert(gs101_pcie_vpcie_enable(&p)==-ENOMEM);assert(enables==1 && disables==1 && !p.vpcie_enabled);
 reset(&p);assert(gs101_pcie_vpcie_enable(&p)==0);assert(p.vpcie_enabled && cleanup);cleanup(cleanup_data);assert(disables==1 && !p.vpcie_enabled);cleanup(cleanup_data);assert(disables==1);
 reset(&p);assert(gs101_pcie_vpcie_enable(&p)==0);disable_error=-EIO;cleanup(cleanup_data);assert(logs==1 && p.vpcie_enabled && disables==1);
 reset(&p);p.ch_num=0;assert(gs101_pcie_vpcie_enable(&p)==0 && gets==0);
 reset(&p);p.ch_num=-1;assert(gs101_pcie_vpcie_enable(&p)==-EINVAL && gets==0);
 return 0;
}
'''
with tempfile.TemporaryDirectory() as t:
 p=Path(t)/'test.c';p.write_text(prefix+helper+cases);binary=Path(t)/'test'
 subprocess.run(['cc','-Wall','-Wextra','-Werror','-fsanitize=address,undefined',str(p),'-o',str(binary)],check=True);subprocess.run([str(binary)],check=True)
print('SUPPLY_OWNER_FAULT_TESTS_PASS')
