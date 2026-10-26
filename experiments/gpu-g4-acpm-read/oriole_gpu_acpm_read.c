// SPDX-License-Identifier: GPL-2.0-only
#include <linux/module.h>
#include <linux/device.h>
#include <linux/of.h>
#include <linux/err.h>
#include <linux/firmware/samsung/exynos-acpm-protocol.h>
#include <dt-bindings/clock/google,gs101-acpm.h>

static unsigned int which;
module_param(which, uint, 0444);
MODULE_PARM_DESC(which, "Read only: 0 G3D, 1 G3DL2, 2 CPUCL0, 3 CPUCL1, 4 CPUCL2");

static int oriole_rate_read(struct acpm_handle *acpm, unsigned int index)
{
	static const unsigned int ids[] = {
		GS101_CLK_ACPM_DVFS_G3D, GS101_CLK_ACPM_DVFS_G3DL2,
		GS101_CLK_ACPM_DVFS_CPUCL0, GS101_CLK_ACPM_DVFS_CPUCL1,
		GS101_CLK_ACPM_DVFS_CPUCL2,
	};
	unsigned long first, second;

	if (index >= ARRAY_SIZE(ids))
		return -EINVAL;
	if (!acpm || !acpm->ops || !acpm->ops->dvfs.get_rate)
		return -ENODEV;
	first = acpm->ops->dvfs.get_rate(acpm, 0, ids[index]);
	if (!first)
		return -EIO;
	second = acpm->ops->dvfs.get_rate(acpm, 0, ids[index]);
	if (!second)
		return -EIO;
	pr_info("ORIOLE_GPU_G4 clock_id=%u first_hz=%lu second_hz=%lu\n",
		ids[index], first, second);
	return first == second ? 0 : -EAGAIN;
}

static int __init oriole_gpu_acpm_read_init(void)
{
	struct device_node *node;
	struct acpm_handle *acpm;
	struct device *dev;
	int ret;

	if (!of_machine_is_compatible("google,gs101-oriole"))
		return -ENODEV;
	if (which > 4)
		return -EINVAL;
	node = of_find_compatible_node(NULL, NULL, "google,gs101-acpm-ipc");
	if (!node)
		return -ENODEV;
	dev = root_device_register("oriole-gpu-acpm-read");
	if (IS_ERR(dev)) {
		of_node_put(node);
		return PTR_ERR(dev);
	}
	acpm = devm_acpm_get_by_node(dev, node);
	of_node_put(node);
	ret = IS_ERR(acpm) ? PTR_ERR(acpm) : oriole_rate_read(acpm, which);
	root_device_unregister(dev);
	pr_info("ORIOLE_GPU_G4 finished ret=%d (GET only)\n", ret);
	return ret;
}

static void __exit oriole_gpu_acpm_read_exit(void) {}
module_init(oriole_gpu_acpm_read_init);
module_exit(oriole_gpu_acpm_read_exit);
MODULE_LICENSE("GPL");
MODULE_DESCRIPTION("Pixel6 bounded read-only ACPM frequency query");
