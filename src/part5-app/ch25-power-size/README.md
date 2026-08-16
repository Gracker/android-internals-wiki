# 第 25 章：功耗与包体积优化

功耗优化关注 CPU（Central Processing Unit，中央处理器）、网络、定位、传感器、音频和后台任务的资源占用；包体积优化关注 DEX、Native SO、资源文件与分发方式。两类工作都需要在相同设备和测试条件下，用可重复的数据比较改动前后的收益。

第 5 章和第 11 章分析系统调度与功耗管理，第 12 章讨论 APK（Android 应用安装包）体积；这里聚焦应用侧的诊断、平台接口使用和工程优化。

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

## 术语提示

- DEX（Dalvik Executable）是 Android 应用字节码的文件格式，APK 中常见的 `classes.dex` 就是 DEX 文件。
- Native SO（原生共享库）指 `.so` 文件，通常由 C 或 C++ 代码按不同 ABI（Application Binary Interface，应用二进制接口）编译生成。
- R8 是 Android 构建链中的代码收缩、优化和混淆工具；Android App Bundle（AAB）是应用发布格式，应用商店可据此为具体设备生成所需 APK。
- WakeLock 是应用向电源管理器申请的唤醒锁，用于在必要时间内阻止设备进入特定睡眠状态；Alarm 是系统在指定时间触发任务的定时机制。WorkManager 是 Jetpack 提供的持久后台任务调度库。
- Hybrid（混合开发）通常指原生界面与 WebView（应用内嵌网页组件）内容并存；音频 Offload（硬件卸载）是在设备支持时，把音频解码和持续播放交给专用音频硬件，以减少主处理器占用。
- ADPF（Android Dynamic Performance Framework，Android 动态性能框架）让应用与系统交换性能和温度信息；`PerformanceHintManager` 是应用提交工作负载时长提示的接口。
- OEM（Original Equipment Manufacturer，原始设备制造商）在本章指设备厂商；热节流是设备温度升高后主动限制 CPU、GPU（图形处理器）等部件性能的保护机制。

## 阅读建议

- 后台耗电可从 25.2、25.3、25.4 和 25.15 开始，音频与定位问题分别进入 25.11/25.12 和 25.5。
- 功耗测试应固定设备、温度、网络和使用时长，并保留系统将耗电量分摊到应用和组件的统计数据。
- 包体积优化可按 DEX、Native SO、资源和分发四个方向拆分验证。
- 早期独立案例已并入对应主题：`BatteryUsageStats`（系统电量归因统计）见 25.1；Android vitals（Google Play Console 中的应用质量指标）和 listener alarm（通过监听器回调交付的定时任务）见 25.3；`JobDebugInfo`（Android 后台任务调度器的调试信息）见 25.4；定位服务见 25.5。
- ADPF 相关案例并入 25.10；Excessive CPU（CPU 使用过量）与固定频率任务并入 25.13；前台服务（Foreground Service，FGS）超时和 `JobScheduler` 任务配额（系统授予后台调度任务的执行预算）并入 25.15。
