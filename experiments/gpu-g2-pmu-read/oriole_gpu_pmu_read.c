// SPDX-License-Identifier: GPL-2.0-only
#include <linux/module.h>
#include <linux/of.h>
#include <linux/err.h>
#include <linux/regmap.h>
#include <linux/soc/samsung/exynos-pmu.h>
#include <linux/soc/samsung/exynos-regs-pmu.h>
static unsigned int which;
module_param(which,uint,0444);
MODULE_PARM_DESC(which,"0 G3D status;1 embedded G3D status; read-only");
static int oriole_gpu_status_read(struct regmap *map,unsigned int index)
{
 const unsigned int offsets[]={GS101_SUBBLK_STATUS(GS101_SUBBBLK_OFFSET_G3D),
                               GS101_SUBBLK_STATUS(GS101_SUBBBLK_OFFSET_EMBEDDED_G3D)};
 unsigned int a,b;
 int ret;
 if(index>=ARRAY_SIZE(offsets))return -EINVAL;
 pr_info("ORIOLE_GPU_G2 begin index=%u offset=%x\n",index,offsets[index]);
 ret=regmap_read(map,offsets[index],&a);if(ret)return ret;
 ret=regmap_read(map,offsets[index],&b);if(ret)return ret;
 pr_info("ORIOLE_GPU_G2 index=%u offset=%x first=%08x second=%08x\n",index,offsets[index],a,b);
 return a==b?0:-EIO;
}
static int __init oriole_gpu_pmu_read_init(void)
{
 struct regmap *map;
 int ret;
 if(!of_machine_is_compatible("google,gs101-oriole"))return -ENODEV;
 if(which>1)return -EINVAL;
 map=exynos_get_pmu_regmap();
 if(IS_ERR(map))return PTR_ERR(map);
 if(!map)return -ENODEV;
 ret=oriole_gpu_status_read(map,which);
 pr_info("ORIOLE_GPU_G2 finished ret=%d (read-only PMU status)\n",ret);
 return ret;
}
static void __exit oriole_gpu_pmu_read_exit(void){}
module_init(oriole_gpu_pmu_read_init);
module_exit(oriole_gpu_pmu_read_exit);
MODULE_LICENSE("GPL");
MODULE_DESCRIPTION("Pixel6 single-register PMU G3D status read");
