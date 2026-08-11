# 第 25 章：功耗与包体积优化

功耗优化关注 CPU、网络、定位、传感器、音频和后台任务的资源占用；包体积优化关注 DEX、Native SO、资源文件与分发方式。两类工作都需要用可重复的数据比较改动前后的收益。

第 5 章和第 11 章分析系统调度与功耗管理，第 12 章讨论 APK 体积；这里聚焦 App 侧的诊断、API 使用和工程优化。

## 内容索引

- [25.1 功耗诊断与分析方法](01-power-diagnosis.md)
- [25.2 后台功耗治理](02-background-power.md)
- [25.3 WakeLock 与 Alarm 管理](03-wakelock-alarm.md)
- [25.4 WorkManager 实战与后台任务调度](04-workmanager-practice.md)
- [25.5 定位与传感器功耗优化](05-location-sensor.md)
- [25.6 APK 体积分析与瘦身](06-apk-analysis.md)
- [25.7 R8 与资源优化](07-r8-resource-optimization.md)
- [25.8 App Bundle 与按需分发](08-app-bundle-delivery.md)
- [25.9 Hybrid/WebView 功耗与原生化取舍](09-hybrid-webview-power.md)
- [25.10 PerformanceHintManager 与 ADPF 能效验证](10-performance-hint-adpf-power.md)
- [25.11 Android 17 后台音频硬化与播放功耗治理](11-background-audio-hardening-power.md)
- [25.12 音频 Offload 与 AudioTrack 精确控制功耗实践](12-audio-offload-audiotrack-power.md)
- [25.13 应用层 CPU 优化实战指南](13-application-cpu-optimization.md)
- [25.14 OEM 厂商差异化后台限制与功耗诊断实战](14-oem-background-restriction-power-diagnosis.md)
- [25.15 Android 17 前台服务类型执行模型与后台启动性能边界](15-foreground-service-execution-model.md)
- [25.16 热节流适配与性能降级治理](16-thermal-throttling-performance.md)
- [25.17 DEX 体积优化实战](17-dex-size-optimization.md)
- [25.18 Native SO 体积优化实战](18-native-so-size-optimization.md)
- [25.19 资源文件体积优化实战](19-resource-file-size-optimization.md)

## 阅读建议

- 后台耗电可从 25.2、25.3、25.4 和 25.15 开始，音频与定位问题分别进入 25.11/25.12 和 25.5。
- 功耗测试应固定设备、温度、网络和使用时长，并同时保留系统功耗归因数据。
- 包体积优化可按 DEX、Native SO、资源和分发四个方向拆分验证。
- 原案例集已按主题回收到诊断、WakeLock/Alarm 与体积主文；BatteryUsageStats 并入 25.1，Vitals 与 listener alarm 并入 25.3，JobDebugInfo 并入 25.4，定位服务并入 25.5，ADPF 三篇并为 25.10，Excessive CPU 与固定频率任务并入 25.13，FGS 超时与 Job 配额并入 25.15。
