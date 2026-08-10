# 第 11 章：功耗

功耗问题通常跨越较长时间窗口，并与卡顿、启动、后台执行和设备温度相互影响。

用户可感知的现象包括前台耗电、后台掉电和发热后的性能下降。分析时需要同时记录工作量、调度、thermal、后台限制、WakeLock、网络行为与设备状态。

应用侧优化与系统侧策略需要分别取证，不能只用电量百分比归因。

## 内容索引

- [11.1 Android 功耗模型](01-power-model.md)
- [11.2 App 耗电优化](02-app-power-optimization.md)
- [11.3 系统级功耗优化](03-system-power-optimization.md)
- [11.4 案例集](04-case-studies.md)
- [11.5 WakeLock 机制与功耗分析](05-wakelock.md)
- [11.6 Bluetooth 扫描与连接功耗分析](06-bluetooth-scan-connection-power.md)
- [11.7 用户设置对能耗的影响](07-user-settings-energy-impact.md)
- [11.8 TARE 退场：Android 17 后台任务预算与电量归因](08-tare-economic-model.md)

## 阅读建议

- App 侧耗电：先读 11.1 和 11.2，再进入对应专项。
- 系统或整机分析：结合 11.3、11.4 与 CPU/thermal 章节。
