// SPDX-License-Identifier: GPL-2.0-only
#include <linux/module.h>
#include <linux/unaligned.h>
#include <linux/of_address.h>
#include <linux/mfd/syscon.h>
#include <linux/regmap.h>
#include <linux/pm_runtime.h>
#include <linux/property.h>
#include <linux/spi/spi.h>
#include <linux/of.h>
#include <linux/gpio/consumer.h>
#include <linux/pinctrl/consumer.h>
#include <linux/delay.h>
#include <linux/clk.h>
#include <linux/io.h>
#include <linux/gpio/driver.h>
#include "pinctrl-samsung.h"



static int read_usi_route(struct spi_device *spi)
{
 struct device *parent = spi->controller->dev.parent;
 struct device_node *np = of_get_parent(parent->of_node), *sysnp;
 struct resource res;
 struct regmap *map;
 void __iomem *regs;
 u32 offset, value;
 int ret;
 if (!np) return -ENODEV;
 ret = of_address_to_resource(np, 0, &res);
 if (ret || res.start != 0x10d400c0 || resource_size(&res) != 0x20) { ret = -EINVAL; goto out; }
 ret = of_property_read_u32_index(np, "samsung,sysreg", 1, &offset);
 if (ret || offset != 0x100c) { ret = -EINVAL; goto out; }
 sysnp = of_parse_phandle(np, "samsung,sysreg", 0);
 if (!sysnp) { ret = -ENODEV; goto out; }
 ret = of_address_to_resource(sysnp, 0, &res);
 if (ret || res.start != 0x10c20000 || resource_size(&res) != 0x10000) { of_node_put(sysnp); ret = -EINVAL; goto out; }
 map = syscon_node_to_regmap(sysnp);
 of_node_put(sysnp);
 if (IS_ERR(map)) { ret = PTR_ERR(map); goto out; }
 regs = of_iomap(np, 0);
 if (!regs) { ret = -ENOMEM; goto out; }
 ret = pm_runtime_resume_and_get(parent);
 if (ret < 0) goto unmap;
 ret = regmap_read(map, offset, &value);
 if (!ret) dev_info(&spi->dev, "USIREAD con=%08x option=%08x route=%08x\n", readl(regs+4), readl(regs+8), value);
 pm_runtime_put(parent);
unmap:
 iounmap(regs);
out:
 of_node_put(np);
 return ret;
}

static int read_touch_mux(struct device *dev)
{
 const char *labels[] = {"gpp26", "gpa8", "gpp23", "gpp23", "gpp23", "gpp23", "gpp26"};
 const unsigned int offsets[] = {1, 6, 0, 1, 2, 3, 0};
 int i, ret;
 for (i = 0; i < ARRAY_SIZE(labels); i++) {
  struct gpio_device *gdev = gpio_device_find_by_label(labels[i]);
  struct gpio_desc *desc;
  struct gpio_chip *gc;
  struct samsung_pin_bank *bank;
  unsigned int func, pud, fw, pw;
  unsigned long flags;
  void __iomem *base;
  if (!gdev) return -ENODEV;
  desc = gpio_device_get_desc(gdev, offsets[i]);
  if (IS_ERR(desc)) { gpio_device_put(gdev); return PTR_ERR(desc); }
  gc = gpiod_to_chip(desc);
  if (!gc || strcmp(dev_name(gc->parent), i == 1 ? "174e0000.pinctrl" : "10c40000.pinctrl")) {
   gpio_device_put(gdev); return -ENODEV;
  }
  bank = gpiochip_get_data(gc);
  fw = bank->type->fld_width[PINCFG_TYPE_FUNC]; pw = bank->type->fld_width[PINCFG_TYPE_PUD];
  if (!fw || !pw || fw * (offsets[i] + 1) > 32 || pw * (offsets[i] + 1) > 32) {
   gpio_device_put(gdev); return -EINVAL;
  }
  ret = clk_enable(bank->drvdata->pclk);
  if (ret) { gpio_device_put(gdev); return ret; }
  base = bank->pctl_base + bank->pctl_offset;
  raw_spin_lock_irqsave(&bank->slock, flags);
  func = (readl(base + bank->type->reg_offset[PINCFG_TYPE_FUNC]) >> (fw * offsets[i])) & ((1U << fw) - 1);
  pud = (readl(base + bank->type->reg_offset[PINCFG_TYPE_PUD]) >> (pw * offsets[i])) & ((1U << pw) - 1);
  raw_spin_unlock_irqrestore(&bank->slock, flags);
  clk_disable(bank->drvdata->pclk);
  dev_info(dev, "PINMUX %s.%u func=%u pud=%u raw=%d\n", labels[i], offsets[i], func, pud, gpiod_get_raw_value_cansleep(desc));
  gpio_device_put(gdev);
 }
 return 0;
}


struct saved_spi_speed { struct spi_device *spi; u32 hz; };
static void restore_spi_speed(void *data)
{
 struct saved_spi_speed *saved = data;
 int ret;
 saved->spi->max_speed_hz = saved->hz;
 ret = spi_setup(saved->spi);
 dev_info(&saved->spi->dev, "MINID speed restored to%u ret=%d\n", saved->hz, ret);
}

static int oriole_minimal_probe(struct spi_device *spi)
{
 struct device *dev = &spi->dev;
 struct pinctrl *pins;
 struct pinctrl_state *active;
 struct gpio_desc *reset, *irq;
 u8 *tx, *rx, *reply_tx, *data;
 int seen=0,j,phase;
 int i, ret;
 u32 dt_hz;
 struct saved_spi_speed *saved;
 if (!of_machine_is_compatible("google,gs101-oriole") ||
     strcmp(dev_name(spi->controller->dev.parent), "10d40000.spi"))
  return -ENODEV;
 pins = devm_pinctrl_get(dev);
 if (IS_ERR(pins)) return PTR_ERR(pins);
 active = pinctrl_lookup_state(pins, "pmx_ts_active");
 if (IS_ERR(active)) return PTR_ERR(active);
 ret = pinctrl_select_state(pins, active);
 if (ret) return ret;
 reset = devm_gpiod_get(dev, "fts,reset", GPIOD_ASIS);
 if (IS_ERR(reset)) return PTR_ERR(reset);
 irq = devm_gpiod_get(dev, "fts,irq", GPIOD_IN);
 if (IS_ERR(irq)) return PTR_ERR(irq);
 spi->mode = SPI_MODE_0;
 spi->bits_per_word = 8;
 ret = device_property_read_u32(dev, "spi-max-frequency", &dt_hz);
 if (ret || dt_hz != 10000000U) return -EINVAL;
 saved = devm_kzalloc(dev, sizeof(*saved), GFP_KERNEL);
 if (!saved) return -ENOMEM;
 saved->spi = spi; saved->hz = spi->max_speed_hz;
 ret = devm_add_action_or_reset(dev, restore_spi_speed, saved);
 if (ret) return ret;
 spi->max_speed_hz = dt_hz;
 ret = spi_setup(spi);
 if (ret) return ret;
 tx = devm_kzalloc(dev, 256, GFP_KERNEL);
 rx = devm_kzalloc(dev, 256, GFP_KERNEL);
 reply_tx = devm_kzalloc(dev, 256, GFP_KERNEL);
 if (!tx || !rx || !reply_tx) return -ENOMEM;
 data=devm_kzalloc(dev,216,GFP_KERNEL);
 if(!data) return -ENOMEM;
 ret = gpiod_direction_output_raw(reset, 0);
 if (ret) return ret;
 msleep(100);
 gpiod_set_raw_value_cansleep(reset, 1);
 msleep(500);
 ret = read_usi_route(spi);
 if (ret) return ret;
 ret = read_touch_mux(dev);
 if (ret) return ret;
 dev_info(dev, "MINID reset=%d irq=%d mode=%x maxhz=%u\n",
  gpiod_get_raw_value_cansleep(reset), gpiod_get_raw_value_cansleep(irq), spi->mode, spi->max_speed_hz);
 /* First obtain a scoped SysInfo observation, never bypass into input. */
 tx[0]=0x87;
 for(j=0;j<16;j++) {
  struct spi_transfer tr[2]={{.tx_buf=tx,.len=1},{.rx_buf=rx,.len=9}};
  ret=spi_sync_transfer(spi,tr,2); if(ret)return ret;
  if(rx[1]==3){seen=1;break;} msleep(20);
 }
 memset(tx,0,256);tx[0]=0xa7;
 {
  struct spi_transfer tr[2]={{.tx_buf=tx,.len=3},{.tx_buf=reply_tx,.rx_buf=rx,.len=217}};
  ret=spi_sync_transfer(spi,tr,2); if(ret)return ret;
  memcpy(data,rx+1,216);
  dev_info(dev,"FIFO22 identity ready=%d header=%02x/%02x chip=%04x fw=%04x x=%u y=%u\n",seen,data[0],data[1],get_unaligned_le16(data+10),get_unaligned_le16(data+16),get_unaligned_le16(data+80),get_unaligned_le16(data+82));
 }
 for(phase=0;phase<3;phase++) {
  if(phase) {
   struct spi_transfer write={.tx_buf=tx,.len=7};
   memset(tx,0,256);tx[0]=0xfa;tx[1]=0x20;
   ret=spi_sync_transfer(spi,&write,1);if(ret)return ret;
   memset(tx,0,256);
   if(phase==1){tx[0]=0xa4;tx[1]=0;tx[2]=1;}
   else {tx[0]=0xa0;tx[1]=0;tx[2]=0xff;}
   write.len=3;
   ret=spi_sync_transfer(spi,&write,1);if(ret)return ret;
  }
  for(i=0;i<(phase==2?32:16);i++) {
   struct spi_transfer tr[2]={{.tx_buf=tx,.len=1},{.rx_buf=rx,.len=9}};
   tx[0]=0x87;memset(rx,0xee,256);
   ret=spi_sync_transfer(spi,tr,2);if(ret)return ret;
   dev_info(dev,"FIFO22 phase=%d sample=%d irqraw=%d data=%*ph\n",phase,i,gpiod_get_raw_value_cansleep(irq),8,rx+1);
   msleep(20);
  }
 }
 return -ENODEV; /* Diagnostic only: never expose a usable touchscreen. */
}
static const struct of_device_id oriole_minimal_of[] = {
 { .compatible = "st,spi" }, {}
};
MODULE_DEVICE_TABLE(of, oriole_minimal_of);
static const struct spi_device_id oriole_minimal_ids[] = { { "spi", 0 }, {} };
MODULE_DEVICE_TABLE(spi, oriole_minimal_ids);
static struct spi_driver oriole_minimal_driver = {
 .driver = { .name = "oriole-touch-minimal", .of_match_table = oriole_minimal_of },
 .probe = oriole_minimal_probe, .id_table = oriole_minimal_ids,
};
module_spi_driver(oriole_minimal_driver);
MODULE_LICENSE("GPL");
MODULE_DESCRIPTION("Pixel6 bounded volatile FIFO/scan diagnostic; no firmware writes");
