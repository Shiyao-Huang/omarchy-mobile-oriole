// SPDX-License-Identifier: GPL-2.0-only
#include <linux/module.h>
#include <linux/gpio/consumer.h>
#include <linux/gpio/driver.h>
#include <linux/gpio/machine.h>
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
static struct gpio_device *reset_gdev;
static struct gpio_desc *reset_desc;
static void release_reset(void)
{
 if (reset_desc) {
  gpiod_set_raw_value_cansleep(reset_desc, 1);
  msleep(5);
  pr_info("oriole-touch-supply-hold: POWERSEQ reset release raw=%d\n", gpiod_get_raw_value_cansleep(reset_desc));
  gpiochip_free_own_desc(reset_desc);
  reset_desc = NULL;
 }
 if (reset_gdev) { gpio_device_put(reset_gdev); reset_gdev = NULL; }
}
static int assert_reset(void)
{
 struct gpio_desc *d;
 struct gpio_chip *gc;
 int ret;
 reset_gdev = gpio_device_find_by_label("gpp26");
 if (!reset_gdev) return -ENODEV;
 d = gpio_device_get_desc(reset_gdev, 0);
 if (IS_ERR(d)) return PTR_ERR(d);
 gc = gpiod_to_chip(d);
 if (!gc || strcmp(dev_name(gc->parent), "10c40000.pinctrl")) return -ENODEV;
 if (gpiod_get_raw_value_cansleep(d) != 1) return -EBUSY;
 d = gpiochip_request_own_desc(gc, 0, "oriole-powerseq-reset", GPIO_LOOKUP_FLAGS_DEFAULT, GPIOD_ASIS);
 if (IS_ERR(d)) return PTR_ERR(d);
 reset_desc = d;
 ret = gpiod_direction_output_raw(d, 0);
 if (ret) return ret;
 pr_info("oriole-touch-supply-hold: POWERSEQ reset asserted raw=%d\n", gpiod_get_raw_value_cansleep(d));
 msleep(100);
 ret = gpiod_get_raw_value_cansleep(d);
 pr_info("oriole-touch-supply-hold: POWERSEQ reset settled raw=%d\n", ret);
 return ret == 0 ? 0 : -EIO;
}


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
	ret = assert_reset();
	if (ret) goto fail;
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
	msleep(15);
	release_reset();
	return 0;
fail:
	release_reset();
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
