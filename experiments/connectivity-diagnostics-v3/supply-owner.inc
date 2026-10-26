/* SPDX-License-Identifier: GPL-2.0-only */
static void gs101_pcie_vpcie_disable(void *data)
{
	struct gs101_pcie *pcie = data;
	int ret;

	if (!pcie->vpcie_enabled)
		return;
	ret = regulator_disable(pcie->vpcie);
	if (ret) {
		dev_err(pcie->pci.dev, "WLAN supply disable failed (%d); reboot recovery required\n", ret);
		return;
	}
	pcie->vpcie_enabled = false;
}

static int gs101_pcie_vpcie_enable(struct gs101_pcie *pcie)
{
	int ret;

	/* Modem channel power belongs to CPIF, not this WLAN trial. */
	if (pcie->ch_num == 0)
		return 0;
	if (pcie->ch_num != 1)
		return -EINVAL;
	pcie->vpcie = devm_regulator_get(pcie->pci.dev, "vpcie");
	if (IS_ERR(pcie->vpcie))
		return PTR_ERR(pcie->vpcie);
	ret = regulator_enable(pcie->vpcie);
	if (ret)
		return ret;
	pcie->vpcie_enabled = true;
	/* Registered before DWC/IRQ lifetime: their teardown runs first. */
	return devm_add_action_or_reset(pcie->pci.dev,
				       gs101_pcie_vpcie_disable, pcie);
}
