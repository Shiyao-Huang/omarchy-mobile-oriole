// SPDX-License-Identifier: GPL-2.0-only
#include <linux/module.h>
#include <linux/kthread.h>
#include <linux/input.h>
#include <linux/input/mt.h>
#include <linux/ktime.h>
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

struct oriole_contact { unsigned int slot, x, y; bool active; };
static bool oriole_decode_contact(const u8 *frame, size_t len,
 unsigned int max_x, unsigned int max_y, struct oriole_contact *out)
{
 const u8 *b;
 unsigned int kind,slot,x,y;
 if (len != 9 || frame[0] != 0x87) return false;
 b=frame+1;kind=b[0]>>4;slot=b[1]>>4;
 if ((b[0]&3)!=3 || kind<1 || kind>3 || slot>=10 || (b[1]&15)!=1)
  return false;
 x=((b[3]&15)<<8)|b[2];y=(b[4]<<4)|(b[3]>>4);
 if (kind!=3 && (x>max_x || y>max_y)) return false;
 out->slot=slot;out->x=x;out->y=y;out->active=kind!=3;
 return true;
}

static void oriole_release_contacts(struct input_dev *input)
{
 unsigned int slot;
 for(slot=0;slot<10;slot++) {
  input_mt_slot(input,slot);
  input_mt_report_slot_state(input,MT_TOOL_FINGER,false);
 }
 input_mt_report_pointer_emulation(input,false);
 input_sync(input);
}

/* Only an asserted IRQ and a valid FIFO prefix establish a ready event.
 * Idle reads can repeat 03 without a controller interrupt. */
static bool oriole_ready_event(const u8 *frame, size_t len, int irq_before)
{
 return len == 9 && irq_before == 0 && frame[0] == 0x87 && frame[1] == 0x03;
}

static unsigned int session_seconds;
module_param(session_seconds,uint,0400);
MODULE_PARM_DESC(session_seconds,"0 continuous;1..3600 finite test then idle untilremove");
struct oriole_poll_context {
 struct spi_device *spi;
 struct gpio_desc *irq;
 struct input_dev *input;
 u8 *tx,*rx,*reply_tx;
 u32 screen_x,screen_y;
 struct task_struct *task;
};

static int oriole_poll_thread(void *arg)
{
 struct oriole_poll_context *ctx=arg;
 struct spi_device *spi=ctx->spi;
 struct device *dev=&spi->dev;
 struct gpio_desc *irq=ctx->irq;
 struct input_dev *input=ctx->input;
 u8 *tx=ctx->tx,*rx=ctx->rx,*reply_tx=ctx->reply_tx;
 u32 screen_x=ctx->screen_x,screen_y=ctx->screen_y;
 unsigned int i,empty=0,ready=0,touch=0,other=0,logged=0,polls=0,reports=0;
 unsigned int before_low=0,after_low=0;
 int phase,ret=0;
 ktime_t deadline;
 u8 last_frame[9]={0};
 bool have_last=false;
 for(phase=0;phase<3;phase++) {
  if(phase) {
   struct spi_transfer write={.tx_buf=tx,.len=7};
   memset(tx,0,256);tx[0]=0xfa;tx[1]=0x20;
   ret=spi_sync_transfer(spi,&write,1);if(ret)goto input_out;
   memset(tx,0,256);
   if(phase==1){tx[0]=0xa4;tx[1]=0;tx[2]=1;}
   else {tx[0]=0xa0;tx[1]=0;tx[2]=0xff;}
   write.len=3;
   ret=spi_sync_transfer(spi,&write,1);if(ret)goto input_out;
  }
  deadline=ktime_add_ms(ktime_get(),session_seconds*1000U);
  if(phase==2) dev_info(dev,"INPUT30_READY seconds=%u (0=continuous)\n",session_seconds);
  for(i=0;phase==2 || i<16;i++) {
   int irq_before,irq_after;
   if(kthread_should_stop()){ret=0;goto input_out;}
   if(phase==2 && session_seconds && ktime_compare(ktime_get(),deadline)>=0)break;
   struct spi_transfer tr[2]={{.tx_buf=tx,.len=1},{.tx_buf=reply_tx,.rx_buf=rx,.len=9}};
   tx[0]=0x87;memset(rx,0xee,256);
   irq_before=gpiod_get_raw_value_cansleep(irq);
   if(irq_before<0){ret=irq_before;goto input_out;}
   ret=spi_sync_transfer(spi,tr,2);if(ret)goto input_out;
   irq_after=gpiod_get_raw_value_cansleep(irq);
   if(irq_after<0){ret=irq_after;goto input_out;}
   if(phase==2) {
    struct oriole_contact contact;
    u8 id=rx[1];polls++;
    if(!irq_before && oriole_decode_contact(rx,9,screen_x-1,screen_y-1,&contact)) {
     input_mt_slot(input,contact.slot);
     input_mt_report_slot_state(input,MT_TOOL_FINGER,contact.active);
     if(contact.active) {
      input_report_abs(input,ABS_MT_POSITION_X,contact.x);
      input_report_abs(input,ABS_MT_POSITION_Y,contact.y);
     }
     input_mt_report_pointer_emulation(input,false);
     input_sync(input);reports++;
    }
    before_low+=!irq_before;after_low+=!irq_after;
    if(!id)empty++;
    else if(oriole_ready_event(rx,9,irq_before))ready++;
    else if((id&3)==3 && (id>>4)>=1 && (id>>4)<=3)touch++;
    else other++;
    if((!have_last || memcmp(last_frame,rx,9)) && logged<256) {
     dev_info(dev,"INPUT30 raw sample=%u irq_before=%d irq_after=%d full9=%*ph\n",i,irq_before,irq_after,9,rx);
     logged++;
    }
    memcpy(last_frame,rx,9);have_last=true;
    if(ready>=8){dev_err(dev,"INPUT30 ready guard reached\n");break;}
   } else
    dev_info(dev,"INPUT30 phase=%d sample=%u irqraw=%d data=%*ph\n",phase,i,gpiod_get_raw_value_cansleep(irq),8,rx+1);
   msleep_interruptible(20);
  }
 }
 dev_info(dev,"INPUT30_FINISHED polls=%u empty=%u ready=%u touch=%u other=%u before_low=%u after_low=%u logged=%u\n",polls,empty,ready,touch,other,before_low,after_low,logged);
 ret=0;
input_out:
 oriole_release_contacts(input);
 dev_info(dev,"INPUT30_END reports=%u ret=%d\n",reports,ret);
 while(!kthread_should_stop())msleep_interruptible(100);
 return ret;
}

static void oriole_minimal_remove(struct spi_device *spi)
{
 struct oriole_poll_context *ctx=spi_get_drvdata(spi);
 if(ctx && ctx->task)kthread_stop(ctx->task);
}

static int oriole_minimal_probe(struct spi_device *spi)
{
 struct device *dev = &spi->dev;
 struct pinctrl *pins;
 struct pinctrl_state *active;
 struct gpio_desc *reset, *irq;
 u8 *tx, *rx, *reply_tx, *data;
 int seen=0,j,ret;
 struct input_dev *input;
 struct oriole_poll_context *ctx;
 u32 screen_x,screen_y;
 u32 dt_hz;
 struct saved_spi_speed *saved;
 if(session_seconds>3600)return -EINVAL;
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
  struct spi_transfer tr[2]={{.tx_buf=tx,.len=1},{.tx_buf=reply_tx,.rx_buf=rx,.len=9}};
  ret=spi_sync_transfer(spi,tr,2); if(ret)return ret;
  if(rx[1]==3){seen=1;break;} msleep(20);
 }
 memset(tx,0,256);tx[0]=0xa7;
 {
  struct spi_transfer tr[2]={{.tx_buf=tx,.len=3},{.tx_buf=reply_tx,.rx_buf=rx,.len=217}};
  ret=spi_sync_transfer(spi,tr,2); if(ret)return ret;
  memcpy(data,rx+1,216);
  dev_info(dev,"INPUT30 identity ready=%d header=%02x/%02x chip=%04x fw=%04x x=%u y=%u\n",seen,data[0],data[1],get_unaligned_le16(data+10),get_unaligned_le16(data+16),get_unaligned_le16(data+80),get_unaligned_le16(data+82));
 }
 if (!seen || data[0]!=0xa5 || data[1]!=1 ||
     get_unaligned_le16(data+10)!=0x3648 || get_unaligned_le16(data+16)!=0x0049 ||
     get_unaligned_le16(data+80)!=2399 || get_unaligned_le16(data+82)!=1079) {
  dev_err(dev,"INPUT30 identity mismatch; no scan or physical test\n");
  return -ENODEV;
 }
 ret=device_property_read_u32(dev,"fts,x-max",&screen_x);
 if(ret)return ret;
 ret=device_property_read_u32(dev,"fts,y-max",&screen_y);
 if(ret)return ret;
 if(screen_x!=1080 || screen_y!=2400)return -EINVAL;
 input=devm_input_allocate_device(dev);
 if(!input)return -ENOMEM;
 input->name="Oriole polling touchscreen";
 input->id.bustype=BUS_SPI;
 input_set_capability(input,EV_KEY,BTN_TOUCH);
 input_set_abs_params(input,ABS_MT_POSITION_X,0,screen_x-1,0,0);
 input_set_abs_params(input,ABS_MT_POSITION_Y,0,screen_y-1,0,0);
 ret=input_mt_init_slots(input,10,INPUT_MT_DIRECT);
 if(ret)return ret;
 ret=input_register_device(input);
 if(ret)return ret;
 ctx=devm_kzalloc(dev,sizeof(*ctx),GFP_KERNEL);
 if(!ctx)return -ENOMEM;
 ctx->spi=spi;ctx->irq=irq;ctx->input=input;
 ctx->tx=tx;ctx->rx=rx;ctx->reply_tx=reply_tx;
 ctx->screen_x=screen_x;ctx->screen_y=screen_y;
 spi_set_drvdata(spi,ctx);
 ctx->task=kthread_run(oriole_poll_thread,ctx,"oriole-touch-poll");
 if(IS_ERR(ctx->task))return PTR_ERR(ctx->task);
 return 0;
}
static const struct of_device_id oriole_minimal_of[] = {
 { .compatible = "st,spi" }, {}
};
MODULE_DEVICE_TABLE(of, oriole_minimal_of);
static const struct spi_device_id oriole_minimal_ids[] = { { "spi", 0 }, {} };
MODULE_DEVICE_TABLE(spi, oriole_minimal_ids);
static struct spi_driver oriole_minimal_driver = {
 .driver = { .name = "oriole-touch-minimal", .of_match_table = oriole_minimal_of },
 .probe = oriole_minimal_probe, .remove = oriole_minimal_remove, .id_table = oriole_minimal_ids,
};
module_spi_driver(oriole_minimal_driver);
MODULE_LICENSE("GPL");
MODULE_DESCRIPTION("Pixel6 bounded volatile bounded input polling diagnostic; no firmware writes");
