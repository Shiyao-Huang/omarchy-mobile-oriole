/* SPDX-License-Identifier: GPL-2.0-only */
#define GS101_PCIE_PMU_OWNED (PCIE_PHY_ISOLATION | PCIE_PHY_CTRL_LINK)

static int gs101_pcie_pmu_begin(struct gs101_pcie *pcie)
{
	int ret;

	/* Exact GS101 PCIe0/1 PMU controls; reject a miswired DT. */
	if (pcie->ch_num < 0 || pcie->ch_num > 1 ||
	    pcie->pmu_offset != 0x3ec0U + 4U * pcie->ch_num)
		return -EINVAL;
	if (pcie->pmu_saved_valid)
		return -EBUSY;
	ret = regmap_read(pcie->pmureg, pcie->pmu_offset, &pcie->pmu_saved);
	if (ret)
		return ret;
	pcie->pmu_saved &= GS101_PCIE_PMU_OWNED;
	pcie->pmu_saved_valid = true;
	return 0;
}

static int gs101_pcie_pmu_update(struct gs101_pcie *pcie, u32 mask, u32 val)
{
	u32 observed;
	int ret;

	if (!pcie->pmu_saved_valid || !mask || (mask & ~GS101_PCIE_PMU_OWNED))
		return -EINVAL;
	ret = regmap_update_bits(pcie->pmureg, pcie->pmu_offset, mask, val);
	if (ret)
		return ret;
	ret = regmap_read(pcie->pmureg, pcie->pmu_offset, &observed);
	if (ret)
		return ret;
	return (observed & mask) == (val & mask) ? 0 : -EIO;
}

static int gs101_pcie_pmu_restore(struct gs101_pcie *pcie)
{
	int ret;

	if (!pcie->pmu_saved_valid)
		return 0;
	/* Restore even after a failed secure call: it may have changed a bit. */
	ret = gs101_pcie_pmu_update(pcie, GS101_PCIE_PMU_OWNED, pcie->pmu_saved);
	if (!ret)
		pcie->pmu_saved_valid = false;
	return ret;
}
