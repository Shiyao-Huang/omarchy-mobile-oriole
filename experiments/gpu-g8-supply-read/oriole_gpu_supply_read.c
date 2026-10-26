// SPDX-License-Identifier: GPL-2.0-only
#include <linux/module.h>
#include <linux/device.h>
#include <linux/of.h>
#include <linux/err.h>
#include <linux/firmware/samsung/exynos-acpm-protocol.h>
#include <linux/mfd/samsung/s2mpg10.h>
#include <linux/mfd/samsung/s2mpg11.h>

struct oriole_supply_reg { const char *name; u8 speedy; u8 reg; };
static const struct oriole_supply_reg oriole_gpu_regs[] = {
 {"B7M_CTRL",0,S2MPG10_PMIC_B7M_CTRL},
 {"B7M_OUT1",0,S2MPG10_PMIC_B7M_OUT1},
 {"B7M_OUT2",0,S2MPG10_PMIC_B7M_OUT2},
 {"B2S_CTRL",1,S2MPG11_PMIC_B2S_CTRL},
 {"B2S_OUT1",1,S2MPG11_PMIC_B2S_OUT1},
 {"B2S_OUT2",1,S2MPG11_PMIC_B2S_OUT2},
 {"B8S_CTRL",1,S2MPG11_PMIC_B8S_CTRL},
 {"B8S_OUT1",1,S2MPG11_PMIC_B8S_OUT1},
 {"B8S_OUT2",1,S2MPG11_PMIC_B8S_OUT2},
 {"L1S_CTRL1",1,S2MPG11_PMIC_L1S_CTRL1},
 {"L1S_CTRL2",1,S2MPG11_PMIC_L1S_CTRL2},
 {"LDO_CTRL1",1,S2MPG11_PMIC_LDO_CTRL1},
 {"PCTRLSEL1",1,S2MPG11_PMIC_PCTRLSEL1},
 {"PCTRLSEL3",1,S2MPG11_PMIC_PCTRLSEL3},
 {"PCTRLSEL5",1,S2MPG11_PMIC_PCTRLSEL5},
};
static int oriole_read_snapshot(struct acpm_handle *acpm)
{
 unsigned int i;
 int ret;
 for (i=0;i<ARRAY_SIZE(oriole_gpu_regs);i++) {
  const struct oriole_supply_reg *r=&oriole_gpu_regs[i];
  u8 first,second;
  ret=acpm->ops->pmic.read_reg(acpm,2,1,r->reg,r->speedy,&first);
  if(ret)return ret;
  ret=acpm->ops->pmic.read_reg(acpm,2,1,r->reg,r->speedy,&second);
  if(ret)return ret;
  pr_info("ORIOLE_GPU_G8 %s speedy=%u reg=%02x first=%02x second=%02x\n",
          r->name,r->speedy,r->reg,first,second);
  if(first!=second)return -EIO;
 }
 return 0;
}
static int __init oriole_gpu_supply_read_init(void)
{
 struct device *dev;
 struct device_node *node;
 struct acpm_handle *acpm;
 int ret;
 if(!of_machine_is_compatible("google,gs101-oriole"))return -ENODEV;
 node=of_find_compatible_node(NULL,NULL,"google,gs101-acpm-ipc");
 if(!node)return -ENODEV;
 dev=root_device_register("oriole-gpu-supply-read");
 if(IS_ERR(dev)){of_node_put(node);return PTR_ERR(dev);}
 acpm=devm_acpm_get_by_node(dev,node);
 of_node_put(node);
 if(IS_ERR(acpm))ret=PTR_ERR(acpm);
 else ret=oriole_read_snapshot(acpm);
 root_device_unregister(dev);
 pr_info("ORIOLE_GPU_G8 finished ret=%d (read-only)\n",ret);
 return ret;
}
static void __exit oriole_gpu_supply_read_exit(void) {}
module_init(oriole_gpu_supply_read_init);
module_exit(oriole_gpu_supply_read_exit);
MODULE_LICENSE("GPL");
MODULE_DESCRIPTION("Pixel6 bounded read-only GPU supply snapshot");
