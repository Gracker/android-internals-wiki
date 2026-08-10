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
- [25.9 功耗与包体积案例集](09-power-size-case-studies.md)
- [25.10 Hybrid/WebView 功耗与原生化取舍](10-hybrid-webview-power.md)
- [25.11 ADPF Hint Session 与协程线程迁移](11-adpf-coroutine-thread-migration.md)
- [25.12 Android 17 Excessive CPU Kill 与后台任务功耗治理](12-android17-excessive-cpu-kill.md)
- [25.13 Foreground Service 超时与 JobScheduler 配额治理](13-fgs-timeout-jobscheduler-quota.md)
- [25.14 JobScheduler 调试：Pending Reasons 与 JobDebugInfo](14-jobdebuginfo-jobscheduler-diagnostics.md)
- [25.15 Android 16 固定频率任务补偿执行与后台 CPU 峰值治理](15-scheduledexecutor-fixedrate-android16.md)
- [25.16 ADPF Power Efficiency Mode 与 PowerMonitor 能耗验证](16-adpf-power-efficiency-powermonitor.md)
- [25.17 Android 17 后台音频 Hardening 与播放功耗治理](17-background-audio-hardening-power.md)
- [25.18 音频 Offload 与 AudioTrack 精确控制功耗实践](18-audio-offload-audiotrack-power.md)
- [25.19 Android Vitals 过度 WakeLock 指标与治理](19-android-vitals-wakelock-governance.md)
- [25.20 Android 17 allow-while-idle Listener Alarm 与短生命周期唤醒治理](20-android17-allow-while-idle-listener-alarm.md)
- [25.21 Android 12+ PerformanceHintManager 实战：Java/NDK 集成与 Android 17 源码校准](21-performance-hint-manager-practice.md)
- [25.22 定位服务功耗与性能实战：FusedLocationProvider、Geofencing 与 Location Batching](22-location-services-performance.md)
- [25.23 应用层 CPU 优化实战指南](23-application-cpu-optimization.md)
- [25.25 OEM 厂商差异化后台限制与功耗诊断实战](25-android17-oem-background-restriction-power-diagnosis.md)
- [25.26 Android 17 Foreground Service 类型执行模型与后台启动性能边界](26-android17-fgs-type-execution-model-background-launch-performance.md)
- [25.27 Android 17 BatteryUsageStats 与功耗归因管线](27-android17-battery-usage-stats-power-attribution.md)
- [25.28 ThermalManager Thermal Throttling 适配与性能降级治理实战](28-thermal-manager-throttling-performance.md)
- [25.29 DEX 体积优化实战](29-dex-size-optimization.md)
- [25.30 Native SO 体积优化实战](30-native-so-size-optimization.md)
- [25.31 资源文件体积优化实战](31-resource-file-size-optimization.md)

## 阅读建议

- 后台耗电可从 25.2、25.3、25.4 和 25.13 开始，音频与定位问题分别进入 25.18 和 25.22。
- 功耗测试应固定设备、温度、网络和使用时长，并同时保留系统功耗归因数据。
- 包体积优化可按 DEX、Native SO、资源和分发四个方向拆分验证。
