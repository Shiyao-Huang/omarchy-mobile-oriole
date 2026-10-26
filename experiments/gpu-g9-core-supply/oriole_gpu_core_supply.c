// SPDX-License-Identifier: GPL-2.0-only
#include <linux/module.h>
#include <linux/device.h>
#include <linux/of.h>
#include <linux/of_platform.h>
#include <linux/platform_device.h>
#include <linux/err.h>
#include <linux/delay.h>
#include <linux/firmware/samsung/exynos-acpm-protocol.h>
#include <linux/mfd/samsung/s2mpg10.h>
#include <linux/mfd/samsung/s2mpg11.h>
struct snapshot_reg { u8 speedy, reg, expected; };
static const struct snapshot_reg snapshot[] = {
 {0,S2MPG10_PMIC_B7M_CTRL,0x58},
 {0,S2MPG10_PMIC_B7M_OUT1,0x58},
 {0,S2MPG10_PMIC_B7M_OUT2,0x58},
 {1,S2MPG11_PMIC_B2S_CTRL,0x38},
 {1,S2MPG11_PMIC_B2S_OUT1,0x40},
 {1,S2MPG11_PMIC_B2S_OUT2,0x30},
 {1,S2MPG11_PMIC_B8S_CTRL,0xd8},
 {1,S2MPG11_PMIC_B8S_OUT1,0x40},
 {1,S2MPG11_PMIC_B8S_OUT2,0x30},
 {1,S2MPG11_PMIC_L1S_CTRL1,0x24},
 {1,S2MPG11_PMIC_L1S_CTRL2,0x18},
 {1,S2MPG11_PMIC_LDO_CTRL1,0xf0},
 {1,S2MPG11_PMIC_PCTRLSEL1,0x73},
 {1,S2MPG11_PMIC_PCTRLSEL3,0x07},
 {1,S2MPG11_PMIC_PCTRLSEL5,0x07},
};
static struct device *diag_dev;
static struct acpm_handle *acpm;
static bool attempted;

static int verify_snapshot(bool enabled)
{
 unsigned int i,j;
 u8 val,expected;
 int ret;
 for (i=0;i<ARRAY_SIZE(snapshot);i++) {
  expected=snapshot[i].expected;
  if (enabled && snapshot[i].speedy==1 && snapshot[i].reg==S2MPG11_PMIC_B2S_CTRL) expected=0xf8;
  for (j=0;j<2;j++) {
   ret=acpm->ops->pmic.read_reg(acpm,2,1,snapshot[i].reg,snapshot[i].speedy,&val);
   if (ret) return ret;
   if (val!=expected) return -EINVAL;
  }
 }
 return 0;
}

static int restore_core(void)
{
 u8 val;
 int ret;
 if (!attempted) return 0;
 ret=acpm->ops->pmic.read_reg(acpm,2,1,S2MPG11_PMIC_B2S_CTRL,1,&val);
 if (ret) return ret;
 if (val!=0x38 && val!=0xf8) return -EBUSY;
 ret=acpm->ops->pmic.update_reg(acpm,2,1,S2MPG11_PMIC_B2S_CTRL,1,0,0xc0);
 if (ret) return ret;
 ret=acpm->ops->pmic.read_reg(acpm,2,1,S2MPG11_PMIC_B2S_CTRL,1,&val);
 if (!ret && val!=0x38) ret=-EIO;
 if (!ret) attempted=false;
 pr_info("ORIOLE_GPU_G9 restore ret=%d value=%02x\n",ret,val);
 return ret;
}

static int enable_core(void)
{
 unsigned int id,j;
 int ret,undo;
 ret=verify_snapshot(false);
 if (ret) return ret;
 for (id=5;id<=6;id++)
  for (j=0;j<2;j++)
   if (acpm->ops->dvfs.get_rate(acpm,0,id)!=151000000) return -ERANGE;
 attempted=true;
 ret=acpm->ops->pmic.update_reg(acpm,2,1,S2MPG11_PMIC_B2S_CTRL,1,0xc0,0xc0);
 if (!ret) { msleep(2); ret=verify_snapshot(true); }
 if (ret) {
  undo=restore_core();
  pr_err("ORIOLE_GPU_G9 enable failure=%d restore=%d\n",ret,undo);
  return ret;
 }
 pr_info("ORIOLE_GPU_G9 B2S_CTRL 38 -> f8; selectors/routing unchanged; HELD\n");
 return 0;
}

static int __init oriole_gpu_core_supply_init(void)
{
 struct device_node *node;
 struct platform_device *gpu;
 int ret;
 if (!of_machine_is_compatible("google,gs101-oriole")) return -ENODEV;
 node=of_find_node_by_path("/soc@0/gpu@1c500000");
 if (!node) return -ENODEV;
 gpu=of_find_device_by_node(node);
 of_node_put(node);
 if (!gpu) return -ENODEV;
 device_lock(&gpu->dev);
 ret=gpu->dev.driver ? -EBUSY : 0;
 device_unlock(&gpu->dev);
 put_device(&gpu->dev);
 if (ret) return ret;
 node=of_find_compatible_node(NULL,NULL,"google,gs101-acpm-ipc");
 if (!node) return -ENODEV;
 diag_dev=root_device_register("oriole-gpu-core-supply");
 if (IS_ERR(diag_dev)) {of_node_put(node);return PTR_ERR(diag_dev);}
 acpm=devm_acpm_get_by_node(diag_dev,node);
 of_node_put(node);
 if (IS_ERR(acpm)) ret=PTR_ERR(acpm);
 else ret=enable_core();
 if (ret) root_device_unregister(diag_dev);
 return ret;
}
static void __exit oriole_gpu_core_supply_exit(void)
{
 int ret=restore_core();
 pr_info("ORIOLE_GPU_G9 exit restore=%d\n",ret);
 root_device_unregister(diag_dev);
}
module_init(oriole_gpu_core_supply_init);
module_exit(oriole_gpu_core_supply_exit);
MODULE_LICENSE("GPL");
MODULE_DESCRIPTION("Pixel6 bounded B2S core-rail hold; no voltage changes; unload GPU before release");
