// SPDX-License-Identifier: GPL-2.0-only
#include <linux/module.h>
#include <linux/device.h>
#include <linux/of.h>
#include <linux/err.h>
#include <linux/firmware/samsung/exynos-acpm-protocol.h>
#include <linux/mfd/samsung/s2mpg10.h>

static int __init oriole_touch_supply_read_init(void)
{
	struct device *dev;
	struct device_node *node;
	struct acpm_handle *acpm;
	const u8 regs[] = { S2MPG10_PMIC_L25M_CTRL, S2MPG10_PMIC_L26M_CTRL };
	u8 first[2], second[2];
	int i, ret = 0;
	if (!of_machine_is_compatible("google,gs101-oriole"))
		return -ENODEV;
	node = of_find_compatible_node(NULL, NULL, "google,gs101-acpm-ipc");
	if (!node)
		return -ENODEV;
	dev = root_device_register("oriole-touch-supply-read");
	if (IS_ERR(dev)) {
		of_node_put(node);
		return PTR_ERR(dev);
	}
	acpm = devm_acpm_get_by_node(dev, node);
	of_node_put(node);
	if (IS_ERR(acpm)) {
		ret = PTR_ERR(acpm);
		goto out;
	}
	for (i = 0; i < ARRAY_SIZE(regs); i++) {
		ret = acpm->ops->pmic.read_reg(acpm, 2, 1, regs[i], 0, &first[i]);
		if (ret)
			goto out;
		ret = acpm->ops->pmic.read_reg(acpm, 2, 1, regs[i], 0, &second[i]);
		if (ret)
			goto out;
		pr_info("oriole-touch-supply-read: L%dM reg=%02x first=%02x second=%02x\n",
			25 + i, regs[i], first[i], second[i]);
		if (first[i] != second[i]) {
			ret = -EIO;
			goto out;
		}
	}
out:
	root_device_unregister(dev);
	pr_info("oriole-touch-supply-read: finished ret=%d (no rail writes)\n", ret);
	return ret;
}
static void __exit oriole_touch_supply_read_exit(void) {}
module_init(oriole_touch_supply_read_init);
module_exit(oriole_touch_supply_read_exit);
MODULE_LICENSE("GPL");
MODULE_DESCRIPTION("Oriole bounded read-only touch supply diagnostic");
