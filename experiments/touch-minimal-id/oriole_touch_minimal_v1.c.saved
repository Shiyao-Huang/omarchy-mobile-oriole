// SPDX-License-Identifier: GPL-2.0-only
#include <linux/module.h>
#include <linux/spi/spi.h>
#include <linux/of.h>
#include <linux/gpio/consumer.h>
#include <linux/pinctrl/consumer.h>
#include <linux/delay.h>

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
 ret = gpiod_direction_output_raw(reset, 0);
 if (ret) return ret;
 msleep(100);
 gpiod_set_raw_value_cansleep(reset, 1);
 msleep(500);
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
