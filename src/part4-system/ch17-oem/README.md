# 第 17 章：OEM 与设备差异

这里的 OEM 指基于 Android 开放源代码项目（AOSP）开发量产设备的厂商；SoC 是把 CPU、GPU 等模块集成在一颗芯片上的片上系统。AOSP 提供公共 API 和平台行为基线，量产设备还会叠加 Power HAL、内核、固件和整机散热差异。

Power HAL 是 Android framework 与厂商电源管理实现之间的硬件抽象层。本章按公开接口、厂商实现、目标设备观测和应用策略四类整理证据，不用品牌名代替测量结果。

## 内容索引

- [17.1 OEM 性能优化与应用协作](01-oem-performance-app-collaboration.md)
- [17.2 SoC 平台差异](02-soc-differences.md)
- [17.3 OEM 调度、游戏模式与输入优先级](03-oem-scheduling-game-input.md)
- [17.4 Power HAL、schedutil 与 Power Stats](04-power-hal-schedutil-power-stats.md)
- [17.5 Media Performance Class 与设备能力分级](05-media-performance-class-device-capability.md)
- [17.6 Private Space 与应用锁的兼容性边界](06-private-space-app-lock-boundary.md)
- [17.7 Android Auto 与 Android Automotive OS 性能优化](07-android-auto-car-os-performance.md)

## 阅读建议

- 刚发现机型差异：先读 17.1～17.2，按来源区分 AOSP 接口、厂商实现和目标设备观测，再建立 SoC 事实表。
- 排查调度、触控或功耗控制问题：调度与触控进入 17.3，功耗控制和统计进入 17.4，不把产品模式名当成内核机制。
- 评估设备公开能力或系统隔离差异：分别使用 17.5 的 Media Performance Class 和 17.6 的 Private Space / 应用锁边界。
- 每次实验先记录 `Build.FINGERPRINT`（构建指纹）、SoC、内核版本、Power HAL、Thermal HAL 与温控配置、电源模式和测试版本，再区分现象属于单机异常、同一机型共性，还是跨机型规律。
