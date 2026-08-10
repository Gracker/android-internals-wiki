# 第 17 章：厂商优化实践

AOSP 描述公共实现，量产设备还会叠加 OEM 与 SoC 差异。

同一个应用在 Pixel、其他 OEM ROM 和不同 SoC 平台上的表现可能不同。系统策略、后台限制、调度参数、图形栈和整机 thermal policy 都会影响结果。

当问题呈现明显的设备分布时，应从单段代码耗时扩展到目标设备的系统策略、配置和运行状态。

## 内容索引

- [17.1 OEM 性能优化的通用思路](01-oem-overview.md)
- [17.2 SoC 平台差异](02-soc-differences.md)
- [17.3 行业案例](03-industry-cases.md)
- [17.4 sched_ext 与 OEM BPF 调度器](04-sched-ext-oem-bpf-scheduler.md)
- [17.5 OEM 游戏模式输入优先级与触控调度](05-oem-game-mode-input-priority.md)
- [17.6 Media Performance Class 与设备能力分级](06-media-performance-class-device-capability.md)
- [17.7 Private Space 与应用锁的兼容性边界](07-private-space-app-lock-boundary.md)
- [17.8 MUSCHED 调度实践](08-musched-vip-scheduling-practice.md)
- [17.9 SoC 特异性功耗优化策略](09-soc-specific-power-optimization.md)
- [17.21 Android 17 SoC 厂商 Power HAL 与 schedutil 控制路径](17.21-android17-soc-vendor-power-hal-schedutil-loop.md)
- [17.23 Android 17 Power Stats HAL OEM 实现差异](17.23-power-stats-hal-oem-implementation.md)
- [25.21 Android Auto 与 Android Automotive OS 性能优化](25.21-android-auto-car-os-performance.md)

## 阅读建议

- 已出现明显机型差异：结合第 15 章的方法与对应 OEM/SoC 条目分析。
- 单机 trace：先记录 build fingerprint、SoC、kernel、Power HAL、thermal 和系统配置，再判断差异是否具有设备分布。
