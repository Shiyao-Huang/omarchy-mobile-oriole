/* SPDX-License-Identifier: GPL-2.0-only */
/*
 * GS101 exynos_pcie_rc_establish_link(), pinned in gs101-stock-pcie-source.json.
 * Caller holds PERST asserted, clocks enabled and PHY initialized. Run this
 * on initial bring-up as well as relink, before any DBI setup or training.
 */
static void gs101_pcie_reset_rc(struct gs101_pcie *pcie)
{
	u32 val;

	val = gs101_elbi_read(pcie, PCIE_SOFT_RESET);
	val &= ~SOFT_PWR_RESET;
	gs101_elbi_write(pcie, val, PCIE_SOFT_RESET);
	usleep_range(1000, 1100);
	val |= SOFT_PWR_RESET;
	gs101_elbi_write(pcie, val, PCIE_SOFT_RESET);

	gs101_elbi_write(pcie, DEVICE_TYPE_RC, PCIE_DEVICE_TYPE);

	val = gs101_elbi_read(pcie, PCIE_SOFT_RESET);
	val |= SOFT_NON_STICKY_RESET;
	gs101_elbi_write(pcie, val, PCIE_SOFT_RESET);
	usleep_range(10, 12);
	val &= ~SOFT_NON_STICKY_RESET;
	gs101_elbi_write(pcie, val, PCIE_SOFT_RESET);
	usleep_range(1000, 1100);
	val |= SOFT_NON_STICKY_RESET;
	gs101_elbi_write(pcie, val, PCIE_SOFT_RESET);
}
