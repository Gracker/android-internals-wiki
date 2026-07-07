---
title: PerfDog
chapter: '19'
section: '19.19'
status: ready-for-review
drafted_date: '2026-04-24'
drafted_by: codex
applicable_versions: Android 8 (API 26) - Android 17 (API 37)
last_verified: '2026-07-08'
last_verified_against: PerfDog official site + AOSP android-17.0.0_r1 PowerStats/Thermal/SurfaceFlinger source anchors
confidence: medium-high
tags:
- apm
- perfdog
- testing
- benchmark
- tools
related_chapters:
- '19.0'
sources:
- type: official
  path: https://perfdog.qq.com/
- type: official
  path: https://perfdog.qq.com/help/faq
pipeline_stage: task9_pending
task6_state: reviewed
reviewed_by: openclaw-task6
reviewed_date: 2026-04-24
last_task6_audit: '2026-07-03'
task6_result: pass-light-edit
task6_review_notes: "2026-07-08 Task6 复审:pass-light-edit。Task9 auto-fix 后文稿复查：L1/L2 无新增问题；outline 10/10 覆盖。Task9 result 为 auto-fixed，送 Task9 终审。"
last_task6_at: "2026-07-08T04:05:00+08:00"
task9_state: pending
task2b_state: fixed
task9_result: auto-fixed
task9_reviewed_date: '2026-07-08'
task9_reviewed_by: openclaw-task9
last_task9_at: '2026-07-08T03:28:36+08:00'
last_task9_audit: '2026-07-08'
last_task9_autofix_at: '2026-07-08'
last_task9_audit_log: 'logs/deep-review/2026-07-08-03-audit.md'
task9_review_notes: '2026-07-08 Task9 idle audit auto-fix: 修正 Thermal AIDL 方法、SurfaceFlinger --latency 数据源、Restricted Settings 特殊访问入口；AOSP 锚定 android-17.0.0_r1，回到 Task6 复审。'
task2b_result: fixed
rework_count: 1
rework_date: "2026-04-27"
rework_by: "task2b-rework"
last_task2b_at: "2026-04-27T07:58:00+08:00"
deepseek_polish_state: done
last_deepseek_polish_at: 2026-05-26
last_task2b_verifier_at: "2026-07-08T03:31:42+08:00"
task2b_verifier_result: "status-corrected-ready-for-task6"
task2b_verifier_notes: "2026-07-08 Task2B Verifier: status finalized→ready-for-review; auto-fixed by Task9, pipeline=task6_pending, queue clear. Ready for Task6 re-review."
---


# PerfDog

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 [定位] 说明 PerfDog 是非嵌入式性能测试工具，适合 QA、竞品对比和实验室回归，不替代端侧 APM。
- 🔹 [指标范围] 列 FPS、frame time、jank、CPU、GPU、memory、power、temperature、network、battery 等指标和可用条件。
- 🔹 [测试条件] 写设备型号、系统版本、刷新率、电量、温度、网络、亮度、后台进程、账号状态和操作脚本。
- 🔹 [报告字段] 设计报告模板，至少包含 app version、device、scene、duration、metric median/p95、thermal state、notes。
- 🔹 [帧时间] 说明为什么平均 FPS 不够，需要看 frame time 分布、长帧、稳定性和波动区间。
- 🔹 [功耗温度] 写功耗、温度、频率降档对帧率和 CPU/GPU 指标的影响；要求记录起止温度。
- 🔹 [工具关系] 和 Perfetto、Android Studio Profiler、Macrobenchmark 分工，说明 PerfDog 发现问题后如何深查。
- 🔹 [自动化] 说明和 adb、UIAutomator、monkey、录制脚本结合时如何保证操作一致。
- 🔹 [竞品边界] 写竞品对比必须统一设备、版本、场景、账号、网络和温度，不能只比较单次峰值。
- 🔹 [使用建议] 给发版前回归、专项优化、竞品分析三种使用流程。

### 扩展（可选深入）

- 🔸 增加一份 PerfDog 测试报告 Markdown 模板。
- 🔸 补一个 frame time 分布解读案例，区分稳定低 FPS 和偶发长帧。
- 🔸 对 PerfDog 官方站点、指标解释和平台支持状态做核对。
- 🔸 增加自动化脚本与 PerfDog 报告命名规范。
- 🔸 补充隐私和账号数据处理要求，避免竞品测试报告泄漏内部信息。

### 流水线加工要求

- 所有指标解释必须绑定测试条件。
- 竞品对比段落要写限制条件，不得直接从单次分数推出产品结论。
- 报告模板要能直接用于 QA 发版记录。

### OpenClaw 加工指引

> **锚点**是最低覆盖要求，加工时必须逐条落实并标注验证结果。
> **扩展**视素材丰富程度选择性深入。
> 如果从 Obsidian 素材或 AOSP 源码中发现大纲未列出但与本节强相关的知识点，
> 可**就地插入**最相关的锚点之后，并用 `[自动发现]` 标注，方便后续 review。
> 锚点内容需 L1/L2 验证，扩展内容至少 L2 验证，自动发现内容至少标注来源。
<!-- outline-end -->

## PerfDog 是非嵌入式性能测试工具

PerfDog 是腾讯 WeTest 的全平台性能测试分析工具，官网定位为 iOS、Android、PC、主机等平台性能测试和分析。它的关键特点是非嵌入式：被测 App 不需要接入 SDK，测试设备通常也不需要 root 或越狱。

这让 PerfDog 很适合测试、竞品分析、游戏性能验证和外部包测量。它不是线上 APM SDK，也不负责把真实用户设备的性能数据持续采回来。

### Android 测试模式与权限边界

Android 端使用 PerfDog 时，要先确认当前是免安装模式还是安装模式。两者都会保持“被测 App 不接 SDK”的前提，但设备侧权限和现场观察方式不同。

| 项目 | 免安装模式 | 安装模式 |
|---|---|---|
| 设备侧组件 | 不安装 PerfDog.apk，依赖 PC 端和 ADB 采集 | 安装 PerfDog.apk / PerfDog Service，设备端可显示实时指标 |
| 权限重点 | USB 调试、ADB 连接稳定 | USB 调试、悬浮窗、辅助功能、通知访问、DUMP 等按官方引导授予 |
| 适用场景 | 实验室回归、竞品包测试、减少被测环境扰动 | 现场调试、端上实时观察、需要 Service 辅助采集的指标 |
| 风险 | 不能在手机端直接看实时悬浮指标 | 高版本系统可能拦截侧载 APK 的敏感权限 |

Android 13+ 对侧载 APK 的敏感权限有 Restricted Settings 限制。PerfDog Service 如果拿不到辅助功能、通知访问或相关授权，现象通常是连接成功但指标缺失。处理顺序是先确认设备由官方渠道安装或信任，再到系统“应用信息”里允许受限设置，并按 PerfDog 提示重新授予权限。

## 它能测什么

PerfDog 的测试场景包括这些类型：

- FPS、帧时间、卡顿、平均帧率等帧率相关指标。
- CPU、内存、GPU、温度、功耗等设备资源指标。
- 网络带宽、延迟、丢包率等网络相关测试。
- 实验室性能基线测试、深度问题分析、云端数据汇总和团队协作工具集成。
- 支持脚本化的自动化性能测试服务。

官网强调无需修改硬件、游戏或应用，即插即用。对第三方 App、竞品包、游戏包测试很有用，因为你通常拿不到源码，也不能让对方集成 SDK。

帧率类指标要按采集对象理解。普通 Activity 窗口可以从 SurfaceFlinger 主窗口的 BufferQueue 时间戳推导，手工核验时可参考 `adb shell dumpsys SurfaceFlinger --latency <WindowName>`、Perfetto FrameTimeline 或 Winscope；游戏和视频常用 SurfaceView / TextureView 独立 Surface，窗口名和帧源可能不同，报告里要写清采集对象。

几个常用指标的口径要在报告里写清：

- FTime：单帧耗时，比平均 FPS 更容易暴露偶发长帧。
- Jank：帧时间偏离目标节奏的卡顿事件，不同刷新率下阈值不同。
- Stutter：连续帧节奏不稳带来的抖动感，适合和 P95 / P99 frame time 一起看。
- Smooth Index：平滑度综合指标，只适合同机、同模式、同场景比较。

GPU 利用率、频率、显存类指标受 SoC 和驱动暴露程度影响。高通 Adreno 机型可读项通常更完整；Mali、联发科或低端芯片可能只有部分字段，甚至没有稳定口径。跨芯片报告不要横比 GPU 利用率绝对值，更适合看同一台设备同一场景的版本变化。

## 结果解释要看测试条件

PerfDog 数据常被横向比较，但这种比较最易出错。至少要固定这些条件：

- 设备型号、系统版本、刷新率、性能模式。
- 电量、充电状态、温度和散热方式。
- 网络环境和服务器区域。
- 测试脚本、操作路径和持续时间。
- App 版本、账号状态、缓存状态。

尤其是游戏和视频场景，温度和降频会明显影响后半段数据。只截取前 1 分钟的 FPS，很可能看不出热稳定性问题。

## 和 Android Studio Profiler、Perfetto 的关系

PerfDog 适合快速拿到外部指标和测试报告。Perfetto 适合深入看系统时间线。Profiler 适合开发机上看进程内 CPU、内存和网络。

三者可以按这个顺序配合：

1. PerfDog 发现某段操作 FPS 下跌、CPU 或功耗异常。
2. 在同一设备上抓 Perfetto，确认主线程、RenderThread、GPU、SurfaceFlinger、调度是否参与。
3. 如果能改源码，再用 Profiler、simpleperf、日志或业务 trace 定位到具体代码。

PerfDog 给的是外部观察，Perfetto 给的是系统证据。不要用外部指标直接推断某个函数慢。

## 使用建议

PerfDog 最适合纳入测试基线。比如每个大版本选固定机型和固定场景跑一次，保存 FPS、卡顿、功耗、温度和内存报告。版本之间只在测试条件一致时比较。

如果用于竞品分析，报告里必须写清设备、系统、网络、场景、时长、环境温度和账号状态。少了这些条件，数据只剩“看起来像比较”，不能支撑工程判断。

## 测试报告应包含哪些字段

PerfDog 报告要能复现，至少记录：

| 字段 | 示例 |
|---|---|
| 设备 | Pixel 8 / Snapdragon 8 Gen 2 / 12GB RAM |
| 系统 | Android 15，安全补丁日期 |
| App | 包名、版本、build number、渠道 |
| 场景 | 首页滑动 3 分钟、游戏战斗 10 分钟、视频播放 15 分钟 |
| 网络 | Wi-Fi / 5G / 弱网参数 / 服务器区域 |
| 状态 | 电量、是否充电、性能模式、屏幕亮度、刷新率 |
| 环境 | 室温、是否散热、设备初始温度 |
| 指标 | FPS、jank、CPU、GPU、内存、温度、功耗、网络 |

缺少这些字段，PerfDog 数据很难和下一次测试对比。性能测试报告的可复现性比单次分数更重要。

## FPS 之外还要看帧时间

平均 FPS 会掩盖抖动。测试报告里至少要保留：

- 平均 FPS。
- P95 / P99 frame time。
- jank 次数或卡顿时长。
- 连续低 FPS 时间段。
- 前半段和后半段对比。

游戏和视频场景尤其要看长时间曲线。前 2 分钟帧率稳定，8 分钟后温度上来开始降频，这类问题平均值很容易被掩盖。

## 功耗和温度的读法

PerfDog 能采功耗和温度类指标时，要把它们当成性能稳定性的上下文：

- FPS 下降同时温度上升，可能是热降频。
- CPU 不高但 GPU 高，问题更偏图形渲染。
- 网络和功耗同时高，可能是重试、长连接或大流量下载。
- 内存持续上涨后出现卡顿，可能是 GC、swap 或系统回收压力。

功耗数据先看连接方式。设备通过 USB 连 PC 时，`/sys/class/power_supply/battery/current_now` 读到的是充电电流和设备耗电的净值，不等于 App 的真实耗电。要比较功耗，优先使用 Wi-Fi 模式或官方支持的断开充电采集方案，并记录是否充电、初始电量、屏幕亮度和环境温度。

功耗指标受设备、系统和采集方式影响很大，不能跨设备直接比较绝对值。更适合在同一设备、同一场景、同一测试条件下做版本对比。报告里可以增加 FPower（每帧功耗）字段，计算口径是 `Total Power / FPS`。它能把“同样帧率下谁更省电”表达得更清楚，但仍然要求功耗采集方式一致。

热降频判断不要只看 FPS 下跌。更稳的证据组合是：Temperature 接近设备热阈值，CPU / GPU Frequency 出现阶梯式下调，P95 / P99 frame time 同步恶化。如果这三项同时出现，FPS 下跌更可能来自系统 thermal 调度；如果温度和频率稳定，才继续回到业务逻辑、渲染或网络路径排查。

## 与自动化脚本结合

PerfDog 这类工具最好和自动化脚本结合。人工滑动或操作的波动太大。推荐方式：

1. 用 UIAutomator、SoloPi、内部自动化工具固定操作路径。
2. PerfDog 同步采集性能数据。
3. 每个场景跑多轮，丢弃明显异常轮次。
4. 保存原始曲线和摘要。
5. 对比当前版本和基线版本。

自动化环境要把 PerfDog Service 的安装和授权写进前置步骤。常见授权包括悬浮窗、辅助功能、通知访问，以及通过 ADB 授予 `android.permission.DUMP`（以官方版本提示为准）。这些权限缺失时，脚本仍会执行，但报告字段会少或为空。

这样测试结果才能进入发版门禁。手工跑一次 PerfDog 更适合快速判断，不适合做严肃回归标准。

## 竞品分析的边界

竞品分析时，PerfDog 可以测外部 App，但不能知道对方内部做了什么。报告结论要写成外部观察：

- “竞品 A 在同一设备同一路径下 P95 frame time 更低。”
- “竞品 B 长时间播放后温度上升更慢。”
- “竞品 C 首屏网络流量更小。”

不要写成内部推断：

- “竞品用了某个缓存策略。”
- “竞品没有主线程 I/O。”
- “竞品 GPU 优化更好。”

外部工具只给现象。内部原因要么来自逆向分析，要么只能作为假设。


<!-- AIW-源码调研-2026-06-24 -->
## 一手源码数据源底层实现

根据 AOSP 源码调研，PerfDog 的 Android 平台性能数据采集依赖四大底层系统接口，这些是 PerfDog 能测到数据的技术基础：

### PowerStats HAL - 核心能耗和功率统计

源码路径：`frameworks/base/services/core/java/com/android/server/powerstats/PowerStatsService.java`

外部工具可通过 `dumpsys powerstats` 交叉核验的能耗数据来自 PowerStats HAL。Android 17 的 `PowerStatsHALWrapper` 会优先绑定 AIDL `android.hardware.power.stats.IPowerStats/default`，不可用时回退到旧 HAL 1.0 JNI wrapper。

- **AIDL / HAL 2.0 wrapper**：调用 `android.hardware.power.stats.IPowerStats`，支持 `PowerEntity`、`EnergyConsumer`、`EnergyMeter` 三类数据
- **HAL 1.0 wrapper**：通过 JNI native 方法提供兼容路径

关键数据类型：
```java
// PowerEntity - 功耗实体（CPU/GPU 等子系统）
PowerEntity[] getPowerEntityInfo();

// EnergyConsumer - 能耗消费者（GPS/display/wifi 等模块）
EnergyConsumer[] getEnergyConsumerInfo();

// EnergyMeter - 能量表（硬件计量器）
Channel[] getEnergyMeterInfo();
```

### Thermal AIDL HAL - 温度和散热监控

源码路径：`hardware/interfaces/thermal/aidl/android/hardware/thermal/IThermal.aidl`

外部工具可通过 `dumpsys thermal` 核验的温度数据最终来自 Thermal HAL。Android 17 的 AIDL 接口定义如下；降频状态不是单独的 `getThrottlingStatus()` 方法，而是 `Temperature` 数据结构里的字段：
```aidl
interface IThermal {
    Temperature[] getTemperatures();
    Temperature[] getTemperaturesWithType(in TemperatureType type);
    CoolingDevice[] getCoolingDevices();
    CoolingDevice[] getCoolingDevicesWithType(in CoolingType type);
}
```

关键温度类型枚举（TemperatureType.aidl）：
```aidl
enum TemperatureType {
    CPU = 0, GPU = 1, BATTERY = 2,    // 基础组件
    NPU = 9, TPU = 10, SOC = 13,      // AI/ML 处理器
    WIFI = 14, DISPLAY = 11           // 其他硬件
}
```

### SurfaceFlinger 帧追踪 - GPU 帧率和渲染性能

源码路径：`frameworks/native/services/surfaceflinger/FrameTracer/FrameTracer.h`

手工核验 `dumpsys SurfaceFlinger --latency` 时，Android 17 的路径是 `SurfaceFlinger::dumpStats()` → `Layer::dumpFrameStats()` → `Layer::getFrameStats()`，输出 desired / actual / ready 三列帧时间。`FrameTracer` 同时记录 dequeue / queue / latch / present fence 等事件并进入 Perfetto，但不是 `--latency` 输出的直接数据源：

```cpp
void SurfaceFlinger::dumpStats(const DumpArgs& args, std::string& result) const;
void Layer::dumpFrameStats(std::string& result) const;
void Layer::getFrameStats(FrameStats* outStats) const;
void FrameTracer::traceTimestamp(...);
void FrameTracer::traceFence(...);
```

因此报告中的帧率、长帧和 Perfetto FrameTimeline 可以互相校验，但不能把 `--latency` 三列数据直接等同于 FrameTracer 事件。

### Restricted Settings 与特殊访问授权

源码位置：`frameworks/base/core/java/android/provider/Settings.java` 及 Settings / PermissionController 相关实现

PerfDog Service 需要的某些敏感权限会受到 Android 13+ Restricted Settings 和特殊访问页面约束。Android 17 的 `Settings.java` 没有 `android.settings.action.REQUEST_MANAGE_SPECIAL_APP_ACCESS` 这个公开 action，实际要按权限类型进入对应入口：
- `Settings.ACTION_ACCESSIBILITY_SETTINGS`
- `Settings.ACTION_NOTIFICATION_LISTENER_SETTINGS`
- `Settings.ACTION_MANAGE_OVERLAY_PERMISSION`
- `android.permission.DUMP` 按官方指引通过 ADB 或设备授权流程处理

### 数据采集流程

PerfDog 的数据采集调用链：
1. **能耗/功率**：`adb shell dumpsys powerstats` → PowerStatsService → PowerStats HAL → 硬件驱动
2. **温度/散热**：`adb shell dumpsys thermal` → ThermalService → Thermal HAL → 温度传感器
3. **帧时间**：`adb shell dumpsys SurfaceFlinger --latency` → SurfaceFlinger → FrameTracer → BufferQueue
4. **GPU 统计**：`adb shell dumpsys gfxinfo` → GraphicsStatsService → 图形统计模块

### 版本适配说明

- **Android 11 (API 30)**：引入 PowerStats HAL 2.0，支持能耗细分
- **Android 12 (API 31)**：重构 Thermal HAL，移除旧版 ThermalManagerService
- **Android 13 (API 33)**：增强 FrameTracer，集成 Perfetto 跨进程追踪
- **当前限制**：部分芯片厂商可能不完全实现 HAL 接口（此为行业普遍现象，非 Android 17 特有）

这些源码分析验证了 PerfDog 能够采集 Android 底层性能数据的理论依据，也为理解不同设备间的数据差异提供了技术解释。
<!-- /AIW-源码调研-2026-06-24 -->
