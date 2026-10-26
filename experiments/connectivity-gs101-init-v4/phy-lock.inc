/* SPDX-License-Identifier: GPL-2.0-only */
/* Stock GS101 checks each status for at most 10000 iterations, 1us apart.
 * These checks are diagnostic in stock, not a reason to skip link training.
 * Caller has enabled PHY clocks and completed calibration/reset release.
 */
static bool gs101_pcie_phy_poll(struct gs101_pcie_phy *phy, u32 offset,
			       u32 mask, u32 *last)
{
	int i;

	for (i = 0; i < 10000; i++) {
		udelay(1);
		*last = readl(phy->phy_base + offset);
		if ((*last & mask) == mask)
			return true;
	}
	return false;
}
