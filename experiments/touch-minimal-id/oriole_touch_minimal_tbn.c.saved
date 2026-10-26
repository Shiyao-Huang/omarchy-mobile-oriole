// SPDX-License-Identifier: GPL-2.0-only
#include <linux/module.h>
#include <linux/spi/spi.h>
#include <linux/of.h>
#include <linux/gpio/consumer.h>
#include <linux/pinctrl/consumer.h>
#include <linux/delay.h>
#include <linux/clk.h>
#include <linux/io.h>
#include <linux/gpio/driver.h>
#include <linux/gpio/machine.h>
#include "pinctrl-samsung.h"


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


struct touch_request { struct gpio_device *gdev; struct gpio_desc *desc; struct device *dev; };
static void restore_touch_request(void *data)
{
 struct touch_request *req = data;
 int ret = gpiod_direction_input(req->desc);
 dev_info(req->dev, "TBN restored request input ret=%d raw=%d\n", ret, gpiod_get_raw_value_cansleep(req->desc));
 gpiochip_free_own_desc(req->desc);
 gpio_device_put(req->gdev);
}
static int request_touch_ap(struct device *dev)
{
 struct touch_request *req;
 struct gpio_chip *gc;
 struct samsung_pin_bank *bank;
 unsigned int func, width;
 unsigned long flags;
 int ret;
 req = devm_kzalloc(dev, sizeof(*req), GFP_KERNEL);
 if (!req) return -ENOMEM;
 req->dev = dev;
 req->gdev = gpio_device_find_by_label("gpp26");
 if (!req->gdev) return -ENODEV;
 req->desc = gpio_device_get_desc(req->gdev, 1);
 if (IS_ERR(req->desc)) { ret = PTR_ERR(req->desc); goto put; }
 gc = gpiod_to_chip(req->desc);
 if (!gc || strcmp(dev_name(gc->parent), "10c40000.pinctrl")) { ret = -ENODEV; goto put; }
 bank = gpiochip_get_data(gc); width = bank->type->fld_width[PINCFG_TYPE_FUNC];
 if (width != 4) { ret = -EINVAL; goto put; }
 ret = clk_enable(bank->drvdata->pclk);
 if (ret) goto put;
 raw_spin_lock_irqsave(&bank->slock, flags);
 func = (readl(bank->pctl_base + bank->pctl_offset + bank->type->reg_offset[PINCFG_TYPE_FUNC]) >> width) & 15;
 raw_spin_unlock_irqrestore(&bank->slock, flags);
 clk_disable(bank->drvdata->pclk);
 if (func != 0 || gpiod_get_raw_value_cansleep(req->desc) != 0) { ret = -EBUSY; goto put; }
 req->desc = gpiochip_request_own_desc(gc, 1, "oriole-tbn-diag", GPIO_LOOKUP_FLAGS_DEFAULT, GPIOD_ASIS);
 if (IS_ERR(req->desc)) { ret = PTR_ERR(req->desc); goto put; }
 ret = devm_add_action_or_reset(dev, restore_touch_request, req);
 if (ret) return ret;
 ret = gpiod_direction_output_raw(req->desc, 0);
 if (ret) return ret;
 msleep(100);
 dev_info(dev, "TBN request driven low raw=%d\n", gpiod_get_raw_value_cansleep(req->desc));
 return 0;
put:
 gpio_device_put(req->gdev);
 return ret;
}

static int oriole_minimal_probe(struct spi_device *spi)
{
 struct device *dev = &spi->dev;
 struct pinctrl *pins;
 struct pinctrl_state *active;
 struct gpio_desc *reset, *irq;
 u8 *tx, *rx;
 int i, ret;
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
 spi->max_speed_hz = min(spi->max_speed_hz, 1000000U);
 ret = spi_setup(spi);
 if (ret) return ret;
 tx = devm_kzalloc(dev, 14, GFP_KERNEL);
 rx = devm_kzalloc(dev, 14, GFP_KERNEL);
 if (!tx || !rx) return -ENOMEM;
 tx[0] = 0xfb; tx[1] = 0x20;
 ret = request_touch_ap(dev);
 if (ret) return ret;
 ret = gpiod_direction_output_raw(reset, 0);
 if (ret) return ret;
 msleep(100);
 gpiod_set_raw_value_cansleep(reset, 1);
 msleep(500);
 ret = read_touch_mux(dev);
 if (ret) return ret;
 dev_info(dev, "MINID reset=%d irq=%d mode=%x maxhz=%u\n",
  gpiod_get_raw_value_cansleep(reset), gpiod_get_raw_value_cansleep(irq), spi->mode, spi->max_speed_hz);
 for (i = 0; i < 3; i++) {
  struct spi_transfer split[2] = {
   { .tx_buf = tx, .len = 5 },
   { .rx_buf = rx, .len = 9 },
  };
  struct spi_transfer single = { .tx_buf = tx, .rx_buf = rx, .len = 14 };
  memset(rx, 0xee, 14);
  ret = spi_sync_transfer(spi, split, 2);
  dev_info(dev, "MINID split%d ret=%d raw=%*ph\n", i, ret, 9, rx);
  if (ret) return ret;
  msleep(10);
  memset(rx, 0xee, 14);
  ret = spi_sync_transfer(spi, &single, 1);
  dev_info(dev, "MINID single%d ret=%d raw=%*ph\n", i, ret, 14, rx);
  if (ret) return ret;
  msleep(10);
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
MODULE_DESCRIPTION("Pixel6 bounded independent read-only touch identity probe");
