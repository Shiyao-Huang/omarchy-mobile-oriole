// SPDX-License-Identifier: GPL-2.0-only
#include <linux/module.h>
#include <linux/device.h>
#include <linux/of.h>
#include <linux/err.h>
#include <linux/delay.h>
#include <linux/firmware/samsung/exynos-acpm-protocol.h>
#include <linux/mfd/samsung/s2mpg10.h>

static struct device *diag_dev;
static struct acpm_handle *diag_acpm;
static const u8 regs[] = { S2MPG10_PMIC_L25M_CTRL, S2MPG10_PMIC_L26M_CTRL };
static const u8 original[] = { 0x2c, 0x3c };
static bool attempted[2];

static int restore_rails(void)
{
	int i, ret, result = 0;
	u8 value;
	for (i = ARRAY_SIZE(regs) - 1; i >= 0; i--) {
		if (!attempted[i])
			continue;
		ret = diag_acpm->ops->pmic.update_reg(diag_acpm, 2, 1, regs[i], 0,
						     original[i] & BIT(7), BIT(7));
		if (!ret)
			ret = diag_acpm->ops->pmic.read_reg(diag_acpm, 2, 1, regs[i], 0, &value);
		if (!ret && value != original[i])
			ret = -EIO;
		pr_info("oriole-touch-supply-hold: restore L%dM ret=%d\n", 25+i, ret);
		if (ret)
			result = ret;
	}
	return result;
}
static int __init oriole_touch_supply_hold_init(void)
{
	struct device_node *node;
	int i, ret;
	u8 value;
	if (!of_machine_is_compatible("google,gs101-oriole"))
		return -ENODEV;
	node = of_find_compatible_node(NULL, NULL, "google,gs101-acpm-ipc");
	if (!node)
		return -ENODEV;
	diag_dev = root_device_register("oriole-touch-supply-hold");
	if (IS_ERR(diag_dev)) {
		of_node_put(node);
		return PTR_ERR(diag_dev);
	}
	diag_acpm = devm_acpm_get_by_node(diag_dev, node);
	of_node_put(node);
	if (IS_ERR(diag_acpm)) {
		ret = PTR_ERR(diag_acpm);
		goto fail;
	}
	/* Read and validate BOTH originals before the first enable. */
	for (i = 0; i < ARRAY_SIZE(regs); i++) {
		ret = diag_acpm->ops->pmic.read_reg(diag_acpm, 2, 1, regs[i], 0, &value);
		if (ret)
			goto fail;
		if (value != original[i]) {
			ret = -EINVAL;
			goto fail;
		}
	}
	for (i = 0; i < ARRAY_SIZE(regs); i++) {
		attempted[i] = true;
		ret = diag_acpm->ops->pmic.update_reg(diag_acpm, 2, 1, regs[i], 0,
						     BIT(7), BIT(7));
		if (!ret)
			ret = diag_acpm->ops->pmic.read_reg(diag_acpm, 2, 1, regs[i], 0, &value);
		if (!ret && value != (original[i] | BIT(7)))
			ret = -EIO;
		if (ret) {
			restore_rails();
			goto fail;
		}
		pr_info("oriole-touch-supply-hold: L%dM %02x -> %02x (voltage preserved)\n",
			25+i, original[i], value);
		msleep(10);
	}
	return 0;
fail:
	root_device_unregister(diag_dev);
	return ret;
}
static void __exit oriole_touch_supply_hold_exit(void)
{
	restore_rails();
	root_device_unregister(diag_dev);
}
module_init(oriole_touch_supply_hold_init);
module_exit(oriole_touch_supply_hold_exit);
MODULE_LICENSE("GPL");
MODULE_DESCRIPTION("Oriole two-rail reversible touch diagnostic, no voltage changes");
