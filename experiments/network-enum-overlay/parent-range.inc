/* SPDX-License-Identifier: GPL-2.0-only */
static bool oriole_parent_range_valid(const u32 *cells, int bytes,
                                     u32 address_cells, u32 size_cells)
{
	return bytes == 16 && address_cells == 1 && size_cells == 1 &&
	       cells[0] == 0 && cells[1] == 0 && cells[2] == 0 &&
	       cells[3] == 0x40000000;
}
