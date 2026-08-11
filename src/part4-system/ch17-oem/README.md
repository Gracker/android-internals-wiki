# 第 17 章：OEM 与设备差异

AOSP 给出公共契约，量产设备还会叠加 SoC、Power HAL、内核、固件和整机散热差异。本章不用品牌名替代证据，而是把公开接口、厂商实现、目标机观测和应用策略分层处理。

## 内容索引

- [17.1 OEM 性能优化的通用思路](01-oem-overview.md)
- [17.2 SoC 平台差异](02-soc-differences.md)
- [17.3 OEM 与大型应用协作案例](03-industry-cases.md)
- [17.4 sched_ext 与 OEM 调度实践](04-sched-ext-oem-bpf-scheduler.md)
- [17.5 OEM 游戏模式输入优先级与触控调度](05-oem-game-mode-input-priority.md)
- [17.6 Media Performance Class 与设备能力分级](06-media-performance-class-device-capability.md)
- [17.7 Private Space 与应用锁的兼容性边界](07-private-space-app-lock-boundary.md)
- [17.8 SoC 功耗控制：Power HAL、schedutil 与厂商差异](08-power-hal-schedutil-soc-power.md)
- [17.9 Android 17 Power Stats HAL 的 OEM 实现差异](09-power-stats-hal-oem-implementation.md)
- [17.10 Android Auto 与 Android Automotive OS 性能优化](10-android-auto-car-os-performance.md)

## 阅读建议

- 刚发现机型差异：先读 17.1～17.2，建立分层证据和 SoC 事实表。
- 追调度、触控或功耗控制：分别进入 17.4、17.5 和 17.8，不把产品模式名当成内核机制。
- 评估设备能力或数据可信度：使用 17.6 的公开分级和 17.9 的 PowerStats 能力分级。
- 每次实验先记录 build fingerprint、SoC、kernel、Power HAL、thermal、电源模式和版本边界，再判断差异是否具有设备分布。
