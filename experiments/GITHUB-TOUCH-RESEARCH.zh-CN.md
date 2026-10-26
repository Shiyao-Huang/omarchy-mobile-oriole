# Pixel 6 触屏：GitHub 对照与实机门槛

2026-10-24。触摸尚未修复，所有新代码只作为诊断实验保存。

## 找到的直接参考

- [gs101-mainline/linux PR #1](https://github.com/gs101-mainline/linux/pull/1)：作者及另一位参与者报告 Pixel 6a（bluejay）实测成功。改动是设备树供电依赖、初始化失败后的 GPIO 释放、ALIX 芯片型号和分辨率。合入提交 `ba8d738e01aa17a61dcb302be6c9b7b4f4d0efe9`。这支持继续参考 GS101/FTS 路线，不证明我们的 Pixel 6 已可用。
- [Omarchy 内核 PR #32](https://github.com/derekross/linux-omarchy-mobile/pull/32)：Pixel Fold 的 SALIXP 芯片身份读取。提供显式零字节 TX 缓冲区、复位先于供电的顺序和片选延迟。该芯片 ID 为 `36 40`，我们的原厂配置为 `36 48`；只能借鉴传输和时序，不能复制型号判断。
- [Omarchy 内核 PR #8](https://github.com/derekross/linux-omarchy-mobile/pull/8)：Pixel 6 Pro 的三星触屏，作者报告真实触摸与桌面使用。不同的 SPI mode 3 和三星命令格式不能用于 Pixel 6 的 ST FTS。共享总线选择脚 gpp26.1 的输出低电平可以对照，但我们此前已做过该控制实验，未修复身份读取。
- [Omarchy Pixel 6 跟踪 issue #2](https://github.com/derekross/omarchy-mobile/issues/2)：仍是社区移植工作记录；其中对 pmOS 的描述明确区分“源码启用”与“实机验证”，未提供可以直接替代我们当前镜像的、已验证完整 Pixel 6 安装包。
- [2022 年 Android 同机型触摸问题](https://github.com/freak07/Kirisakura_Raviole/issues/2)：最终归因于 vendor_dlkm 模块安装目标。与当前原生 Linux 下的 SPI 身份读取问题不同，不能据此清空 super 分区。

## 本机测试

`touch-explicit-tx-plan.json` 记录了单变量对照：原控制器、请求上限 10MHz、相同复位等待，只给分段接收补上独立的零字节 TX 缓冲区。编译通过，但三次身份读取仍失败，供电控制寄存器恢复并经独立双读核验。

`touch-power-order-plan.json` 记录上电顺序实验及观测限制。具体结果以该文件和 `diagnostic-results.json` 为准。没有把其他机型的测试报告或本机 insmod 返回零当作触摸成功。

## 验证与下一步门槛

用户旅程仍停在“手指点按/滑动不能产生事件”；先前真实手指测试得到 0 字节输入。端到端 USB→内核→SPI→芯片身份读取仍失败。源码推演和 W=1 编译检查通过的范围仅是构建与控制流程；无可独立模拟电气行为的单元测试，不能把编译算作硬件测试。

下一项需要区分的是：USI/SPI 的实际路由与引脚状态、芯片上电后的真实响应。驱动已绑定和软件寄存器读回不等于实际电压、片选或时钟波形已正确。若继续读 USI/sysreg，只能在核对精确资源范围和时钟后读取已知无副作用的配置寄存器；若仍冲突，应采用已知能工作的完整 GS101 基线作受控对照或测量电气信号。

晋升条件依次是：稳定读出 `36 48`，有效系统信息，真实手指坐标与释放事件，Omarchy 点按/滑动/虚拟键盘，重启后复现。此前不发布“触摸已修复”的一键包。
