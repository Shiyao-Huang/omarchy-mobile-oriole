// SPDX-License-Identifier: GPL-2.0-only
/* Current-boot bringup only. Keep runtime PM forbidden; unload Panfrost first. */
#include <linux/module.h>
#include <linux/of.h>
#include <linux/of_address.h>
#include <linux/clk.h>
#include <linux/clk-provider.h>
#include <linux/err.h>
#include <linux/regmap.h>
#include <linux/soc/samsung/exynos-pmu.h>
#include <linux/soc/samsung/exynos-regs-pmu.h>
#include "gpu_dtbo.h"

static int overlay_id;

static int check_power(struct regmap *map)
{
 static const unsigned int offsets[] = {
  GS101_SUBBLK_STATUS(GS101_SUBBBLK_OFFSET_G3D),
  GS101_SUBBLK_STATUS(GS101_SUBBBLK_OFFSET_EMBEDDED_G3D),
 };
 unsigned int i, j, val;
 int ret;
 for (i = 0; i < ARRAY_SIZE(offsets); i++) {
  for (j = 0; j < 2; j++) {
   ret = regmap_read(map, offsets[i], &val);
   if (ret) return ret;
   if (val != 1) return -EAGAIN;
  }
 }
 return 0;
}

static int check_clocks(struct device_node *node)
{
 struct of_phandle_args spec = { .np = node, .args_count = 1 };
 struct clk *clk;
 unsigned int id;
 unsigned long rate;
 for (id = 5; id <= 6; id++) {
  spec.args[0] = id;
  clk = of_clk_get_from_provider(&spec);
  if (IS_ERR(clk)) return PTR_ERR(clk);
  rate = clk_get_rate(clk);
  clk_put(clk);
  if (!rate) return -EIO;
  pr_info("ORIOLE_GPU_G6 clock%u=%lu\n", id, rate);
 }
 return 0;
}

static int __init oriole_gpu_overlay_init(void)
{
 struct device_node *node, *acpm;
 struct resource res;
 struct regmap *pmu;
 int ret;
 if (!of_machine_is_compatible("google,gs101-oriole")) return -ENODEV;
 node = of_find_node_by_path("/soc@0/gpu@1c500000");
 if (!node) return -ENODEV;
 if (!of_device_is_compatible(node, "google,gs101-mali")) {
  of_node_put(node); return -ENODEV;
 }
 if (of_device_is_available(node)) {
  of_node_put(node); return -EBUSY;
 }
 ret = of_address_to_resource(node, 0, &res);
 of_node_put(node);
 if (ret) return ret;
 if (res.start != 0x1c500000 || resource_size(&res) != 0x5000) return -EINVAL;
 pmu = exynos_get_pmu_regmap();
 if (IS_ERR(pmu)) return PTR_ERR(pmu);
 if (!pmu) return -ENODEV;
 ret = check_power(pmu);
 if (ret) return ret;
 acpm = of_find_node_by_path("/firmware/power-management");
 if (!acpm) return -ENODEV;
 ret = check_clocks(acpm);
 of_node_put(acpm);
 if (ret) return ret;
 ret = of_overlay_fdt_apply(gpu_dtbo, sizeof(gpu_dtbo), &overlay_id, NULL);
 if (ret && overlay_id) {
  int undo = of_overlay_remove(&overlay_id);
  pr_err("ORIOLE_GPU_G6 failed apply=%d undo=%d\n", ret, undo);
 }
 pr_info("ORIOLE_GPU_G6 overlay ret=%d id=%d\n", ret, overlay_id);
 return ret;
}

static void __exit oriole_gpu_overlay_exit(void)
{
 int ret = of_overlay_remove(&overlay_id);
 pr_info("ORIOLE_GPU_G6 overlay remove ret=%d\n", ret);
}
module_init(oriole_gpu_overlay_init);
module_exit(oriole_gpu_overlay_exit);
MODULE_LICENSE("GPL");
MODULE_DESCRIPTION("Pixel6 guarded current-boot GPU clock overlay for Panfrost bringup");
