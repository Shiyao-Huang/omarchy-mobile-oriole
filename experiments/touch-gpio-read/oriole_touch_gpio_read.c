// SPDX-License-Identifier: GPL-2.0-only
#include <linux/module.h>
#include <linux/of.h>
#include <linux/gpio/driver.h>
#include <linux/gpio/consumer.h>
#include <linux/delay.h>
static int __init oriole_touch_gpio_read_init(void)
{
 const char *labels[] = {"gpp26", "gpa8", "gpa9", "gpp26", "gpp23"};
 const unsigned int offsets[] = {1, 6, 0, 0, 3};
 int i, j;
 if (!of_machine_is_compatible("google,gs101-oriole")) return -ENODEV;
 for (i = 0; i < ARRAY_SIZE(labels); i++) {
  struct gpio_device *gdev = gpio_device_find_by_label(labels[i]);
  struct gpio_desc *desc;
  if (!gdev) return -ENODEV;
  desc = gpio_device_get_desc(gdev, offsets[i]);
  if (IS_ERR(desc)) { gpio_device_put(gdev); return PTR_ERR(desc); }
  for (j = 0; j < 2; j++) {
   pr_info("oriole-touch-gpio-read: %s.%u sample%d raw=%d\n", labels[i], offsets[i], j,
    gpiod_get_raw_value_cansleep(desc));
   msleep(10);
  }
  gpio_device_put(gdev);
 }
 return 0;
}
static void __exit oriole_touch_gpio_read_exit(void) {}
module_init(oriole_touch_gpio_read_init);
module_exit(oriole_touch_gpio_read_exit);
MODULE_LICENSE("GPL");
MODULE_DESCRIPTION("Read-only Pixel6 touch handshake GPIO diagnostic");
