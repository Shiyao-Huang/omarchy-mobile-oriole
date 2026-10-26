// SPDX-License-Identifier: GPL-2.0-only
/* Enumeration only. DT stays until reboot; unload host/PHY to release power.
 * Deliberately no module_exit: prevent unsafe live node removal under a driver.
 */
#include <linux/module.h>
#include <linux/of.h>
#include "wifi_dtbo.h"
#include "parent-range.inc"

static int overlay_id;
static int __init oriole_wifi_overlay_init(void)
{
	static const char * const paths[] = {
		"/soc@0/pcie@14520000", "/soc@0/phy@14550000",
		"/regulator-trial-wlan",
	};
	struct device_node *node;
	u32 cells[4], address_cells, size_cells;
	int length;
	unsigned int i;
	int ret;

	if (!of_machine_is_compatible("google,gs101-oriole"))
		return -ENODEV;
	for (i = 0; i < ARRAY_SIZE(paths); i++) {
		node = of_find_node_by_path(paths[i]);
		if (node) {
			of_node_put(node);
			return -EBUSY;
		}
	}
	node = of_find_node_by_path("/soc@0");
	if (!node)
		return -ENODEV;
	ret = -EINVAL;
	if (of_find_property(node, "ranges", &length) &&
	    !of_property_read_u32_array(node, "ranges", cells, ARRAY_SIZE(cells)) &&
	    !of_property_read_u32(node, "#address-cells", &address_cells) &&
	    !of_property_read_u32(node, "#size-cells", &size_cells) &&
	    oriole_parent_range_valid(cells, length, address_cells, size_cells))
		ret = 0;
	of_node_put(node);
	if (ret)
		return ret;
	ret = of_overlay_fdt_apply(wifi_dtbo, sizeof(wifi_dtbo), &overlay_id, NULL);
	if (ret && overlay_id) {
		int undo = of_overlay_remove(&overlay_id);
		pr_err("ORIOLE_WIFI_ENUM apply=%d undo=%d\n", ret, undo);
	}
	pr_info("ORIOLE_WIFI_ENUM overlay ret=%d id=%d (DT lifetime: until reboot)\n", ret, overlay_id);
	return ret;
}
module_init(oriole_wifi_overlay_init);
MODULE_LICENSE("GPL");
MODULE_DESCRIPTION("Pixel6 temporary PCIe1 enumeration wiring; reboot to remove DT");
