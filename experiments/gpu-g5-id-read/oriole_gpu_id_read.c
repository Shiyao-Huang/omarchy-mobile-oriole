// SPDX-License-Identifier: GPL-2.0-only
#include <linux/module.h>
#include <linux/of.h>
#include <linux/of_address.h>
#include <linux/err.h>
#include <linux/io.h>
#include <linux/ioport.h>
#include <linux/regmap.h>
#include <linux/soc/samsung/exynos-pmu.h>
#include <linux/soc/samsung/exynos-regs-pmu.h>

static int oriole_gpu_check_power(struct regmap *map)
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
			if (ret)
				return ret;
			if (val != 1)
				return -EAGAIN;
		}
	}
	return 0;
}

static int oriole_gpu_read_id(void __iomem *io)
{
	u32 first = readl(io);
	u32 second = readl(io);

	pr_info("ORIOLE_GPU_G5 id_first=%08x id_second=%08x\n", first, second);
	if (first != second)
		return -EIO;
	return (first & 0xffff0000) == 0x92020000 ? 0 : -ENODEV;
}

static int __init oriole_gpu_id_read_init(void)
{
	struct device_node *node;
	struct regmap *pmu;
	struct resource res;
	void __iomem *io;
	int ret;

	if (!of_machine_is_compatible("google,gs101-oriole"))
		return -ENODEV;
	node = of_find_compatible_node(NULL, NULL, "google,gs101-mali");
	if (!node)
		return -ENODEV;
	if (of_device_is_available(node)) {
		of_node_put(node);
		return -EBUSY;
	}
	ret = of_address_to_resource(node, 0, &res);
	of_node_put(node);
	if (ret)
		return ret;
	if (res.start != 0x1c500000 || resource_size(&res) != 0x5000)
		return -EINVAL;
	pmu = exynos_get_pmu_regmap();
	if (IS_ERR(pmu))
		return PTR_ERR(pmu);
	if (!pmu)
		return -ENODEV;
	ret = oriole_gpu_check_power(pmu);
	if (ret)
		return ret;
	if (!request_mem_region(res.start, sizeof(u32), "oriole-gpu-id-read"))
		return -EBUSY;
	io = ioremap(res.start, sizeof(u32));
	if (!io) {
		release_mem_region(res.start, sizeof(u32));
		return -ENOMEM;
	}
	pr_info("ORIOLE_GPU_G5 power_gate_pass; reading GPU_ID only\n");
	ret = oriole_gpu_read_id(io);
	iounmap(io);
	release_mem_region(res.start, sizeof(u32));
	pr_info("ORIOLE_GPU_G5 finished ret=%d (read-only; no DMA)\n", ret);
	return ret;
}

static void __exit oriole_gpu_id_read_exit(void) {}
module_init(oriole_gpu_id_read_init);
module_exit(oriole_gpu_id_read_exit);
MODULE_LICENSE("GPL");
MODULE_DESCRIPTION("Pixel6 gated read-only Mali-G78 identity probe");
