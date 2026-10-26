// SPDX-License-Identifier: GPL-2.0-only
#include <linux/module.h>
#include <linux/of.h>
#include <linux/err.h>
#include <linux/clk.h>
#include <linux/clk-provider.h>
#include <dt-bindings/clock/google,gs101.h>
static unsigned int which;
module_param(which,uint,0444);
MODULE_PARM_DESC(which,"0 BUSD;1 GLB;2 SWITCH; CMU_TOP read-only");
static const unsigned int ids[]={CLK_GOUT_CMU_G3D_BUSD,CLK_GOUT_CMU_G3D_GLB,CLK_GOUT_CMU_G3D_SWITCH};
static int __init oriole_gpu_clock_read_init(void)
{
 struct device_node *np;
 struct of_phandle_args args={};
 struct clk *clk;
 unsigned long rate;
 bool enabled;
 if(!of_machine_is_compatible("google,gs101-oriole"))return -ENODEV;
 if(which>=ARRAY_SIZE(ids))return -EINVAL;
 np=of_find_compatible_node(NULL,NULL,"google,gs101-cmu-top");
 if(!np)return -ENODEV;
 args.np=np;args.args_count=1;args.args[0]=ids[which];
 clk=of_clk_get_from_provider(&args);
 of_node_put(np);
 if(IS_ERR(clk))return PTR_ERR(clk);
 pr_info("ORIOLE_GPU_G3 begin index=%u clock_id=%u\n",which,ids[which]);
 rate=clk_get_rate(clk);
 enabled=__clk_is_enabled(clk);
 pr_info("ORIOLE_GPU_G3 index=%u clock_id=%u rate=%lu hw_enabled=%u\n",which,ids[which],rate,enabled);
 clk_put(clk);
 return 0;
}
static void __exit oriole_gpu_clock_read_exit(void){}
module_init(oriole_gpu_clock_read_init);
module_exit(oriole_gpu_clock_read_exit);
MODULE_LICENSE("GPL");
MODULE_DESCRIPTION("Pixel6 CMU_TOP G3D input clock read-only probe");
