/* SPDX-License-Identifier: GPL-2.0-only */
/* Exact running-kernel DWC helper, renamed for module-local use. */
static void oriole_n2_handle_msi_irq(struct dw_pcie_rp *pp)
{
	struct dw_pcie *pci = to_dw_pcie_from_pp(pp);
	unsigned int i, num_ctrls;

	num_ctrls = pp->num_vectors / MAX_MSI_IRQS_PER_CTRL;

	for (i = 0; i < num_ctrls; i++) {
		unsigned int reg_off = i * MSI_REG_CTRL_BLOCK_SIZE;
		unsigned int irq_off = i * MAX_MSI_IRQS_PER_CTRL;
		unsigned long status, pos;

		status = dw_pcie_readl_dbi(pci, PCIE_MSI_INTR0_STATUS + reg_off);
		if (!status)
			continue;

		for_each_set_bit(pos, &status, MAX_MSI_IRQS_PER_CTRL)
			generic_handle_demux_domain_irq(pp->irq_domain, irq_off + pos);
	}
}
