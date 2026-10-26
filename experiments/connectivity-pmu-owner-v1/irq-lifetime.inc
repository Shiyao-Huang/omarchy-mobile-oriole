/* SPDX-License-Identifier: GPL-2.0-only */
/* One managed owner for the post-host-init IRQ and host lifetime. */
static void gs101_pcie_host_cleanup(void *data)
{
	struct gs101_pcie *pcie = data;
	u32 val;

	/* Child shutdown may require live MSI; stop children before masking it.
	 * DWC deinit repeats stop_root_bus before removal; stopped devices are
	 * skipped by the PCI core. No CPIF users are permitted in this trial.
	 */
	pci_lock_rescan_remove();
	pci_stop_root_bus(pcie->pci.pp.bridge->bus);
	pci_unlock_rescan_remove();

	if (pcie->ch_num >= 0 && gs101_pcie_ch[pcie->ch_num] == pcie)
		gs101_pcie_ch[pcie->ch_num] = NULL;

	val = gs101_elbi_read(pcie, PCIE_IRQ2_EN);
	gs101_elbi_write(pcie, val & ~IRQ_MSI_CTRL_EN_RISING_EDG,
			 PCIE_IRQ2_EN);
	if (pcie->irq_registered) {
		/* Synchronize the handler before DWC removes its MSI domain. */
		free_irq(pcie->irq, pcie);
		pcie->irq_registered = false;
	}
	dw_pcie_host_deinit(&pcie->pci.pp);
}

/* Called only after dw_pcie_host_init succeeds, with MSI forwarding masked. */
static int gs101_pcie_attach_irq(struct gs101_pcie *pcie, int irq)
{
	int ret;
	u32 val;

	pcie->irq = irq;
	ret = request_irq(irq, gs101_pcie_irq_handler, IRQF_SHARED,
			  "gs101-pcie", pcie);
	if (ret) {
		dw_pcie_host_deinit(&pcie->pci.pp);
		return ret;
	}
	pcie->irq_registered = true;
	ret = devm_add_action_or_reset(pcie->pci.dev,
				       gs101_pcie_host_cleanup, pcie);
	if (ret)
		return ret;

	if (pcie->ch_num >= 0)
		gs101_pcie_ch[pcie->ch_num] = pcie;
	val = gs101_elbi_read(pcie, PCIE_IRQ2_EN);
	gs101_elbi_write(pcie, val | IRQ_MSI_CTRL_EN_RISING_EDG,
			 PCIE_IRQ2_EN);
	return 0;
}
