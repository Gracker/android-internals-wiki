---
title: "性能测试最佳实践"
chapter: "15.6"
section: "15.6"
status: finalized
drafted_date: "2026-04-04"
applicable_versions: "Android 8 (API 26) - Android 16 (API 36)"
last_verified: "2026-04-27"
last_verified_against: "developer.android.com, firebase.google.com, androidx-main, AOSP android-14.0.0_r1 ThermalManagerService / DisplayModeDirector / PackageManagerShellCommand / BackgroundDexOptService / BackgroundDexOptJobService; AOSP android-16.0.0_r1 PackageManagerShellCommand / ArtManagerLocal"
confidence: medium
sources:
  - type: official
    path: "developer.android.com/topic/performance/benchmarking"
  - type: official
    path: "developer.android.com/topic/performance/benchmarking/benchmarking-in-ci"
  - type: official
    path: "developer.android.com/topic/performance/benchmarking/macrobenchmark-overview"
  - type: official
    path: "developer.android.com/reference/kotlin/androidx/benchmark/macro/CompilationMode"
  - type: official
    path: "firebase.google.com/docs/perf-mon/troubleshooting#performance-monitoring-limits"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/power/ThermalManagerService.java"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/display/mode/DisplayModeDirector.java"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/pm/PackageManagerShellCommand.java"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/pm/BackgroundDexOptService.java"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/pm/BackgroundDexOptJobService.java"
  - type: aosp
    path: "art/libartservice/service/java/com/android/server/art/ArtManagerLocal.java"
tags:
  - android
  - benchmark
  - research
related_chapters:
  - "14.6"
  - "15.5"
  - "8.3"
  - "13.2"
  - "5.5"
pipeline_stage: ready-to-publish
task6_state: reviewed
reviewed_by: openclaw-task6
reviewed_date: "2026-05-07"
last_task6_audit: "2026-05-23"
task6_result: pass-light-edit
task9_state: reviewed
task2b_state: fixed
task2b_result: fixed
last_task2b_at: "2026-05-07T17:40:00+08:00"
review_notes: "2026-05-07 task2b rework: P90/FPS 分位语义已修正（FPS 用 P10/慢帧占比）；Macrobenchmark 自动稳定化已改为 IsolationActivity + sustained perf mode 源码级描述。"
task9_result: pass-tech-review
task9_reviewed_by: openclaw-task9
task9_reviewed_date: "2026-05-07"
last_task9_at: "2026-05-07T18:28:30+08:00"
repaired_date: "2026-04-27"
repaired_by: "openclaw-task2b"
task9_review_notes: "2026-05-07 Task9 18:28：pass-tech-review。P0 0 / P1 0 / P2 1；Macrobenchmark 分位数与自动稳定化 P1 已闭环，JSON schema 口径 P2 已写入 suggestions。满足 Task6 通过且 queue 无 pending，自动晋升 finalized。"
deepseek_polish_state: done
last_deepseek_polish_at: "2026-05-25"
---


# 性能测试最佳实践

<!-- outline-start -->
## 本节要点大纲

### 锚点(必须覆盖)

- 🔹 性能测试环境标准化:设备选择、温控、电量、网络
- 🔹 消除测试干扰:关闭不必要 App、清理后台、恒温控制
- 🔹 数据采样策略:多次采样取中位数/P90、Warm-up 轮次
- 🔹 性能基线管理与回归检测
- 🔹 测试报告的撰写规范

### 扩展(可选深入)

- 🔸 Macrobenchmark 在 CI 中的集成实践
- 🔸 使用 Firebase Performance Monitoring 的限制与替代方案

### OpenClaw 加工指引

> **锚点**是最低覆盖要求,加工时必须逐条落实并标注验证结果。
> **扩展**视素材丰富程度选择性深入。
> 如果从 Obsidian 素材或 AOSP 源码中发现大纲未列出但与本节强相关的知识点,
> 可**就地插入**最相关的锚点之后,并用 `[自动发现]` 标注,方便后续 review。
> 锚点内容需 L1/L2 验证,扩展内容至少 L2 验证,自动发现内容至少标注来源。
<!-- outline-end -->

## 为什么性能测试需要「最佳实践」

性能测试的工具链——Perfetto、Profiler、Benchmark——本身没有问题，测试方式更容易出问题。同一台设备、同一段代码，第一次冷启动 450ms，第二次变成 620ms；今天帧率 58fps，明天同样的代码变成 52fps。拿着这些数据定位问题，很难分清是代码引入了回归，还是测试环境本身在波动。

性能测试和功能测试的区别在于：功能测试的结果是确定的，要么通过，要么失败；性能测试的结果是概率性的，会受到温度、后台进程、CPU 调频策略、GC 时机等变量影响。测试不主动控制这些变量，数据就没有参考价值。

本节先处理比「怎么写一个 benchmark」更前面的事：把测试环境、采样方法和结果解释做对。没有这一步，后面的数据就没有足够的参考价值。

[已验证: 官方文档, developer.android.com/topic/performance/benchmarking]

## 测试环境标准化

性能测试的第一步是搭建一个**尽可能可控的测试环境**，这一步做好了，后面的一切才有意义。

### 设备选择：覆盖主力用户群

测试设备的选择需要考虑两个维度：**市场占有率**和**性能梯度**。

市场占有率决定了我们应该优先测什么设备。如果你的目标用户中 60% 使用的是中端骁龙 7 系处理器设备,那么旗舰机上测出的数据对大多数用户就没有代表性。反之,如果你只测中低端设备,可能无法发现那些只在高端设备上才会暴露的 GPU bound 问题。

性能梯度是指我们至少应该覆盖三个档次:

- **低端设备**(如 4GB 内存、低端 SoC):暴露内存压力下的性能问题、冷启动瓶颈、低内存下的 GC 频率
- **中端设备**(如 6-8GB 内存、中端 SoC):代表大多数用户的体验,是性能测试的主力平台
- **高端设备**(如 12GB+ 内存、旗舰 SoC):验证高刷新率下的帧率稳定性、复杂 UI 场景的性能表现

Google 在官方文档中建议至少使用一台运行 AOSP 系统镜像的 Pixel 设备作为基准测试的参考设备,这样可以在不同团队之间建立统一的比较基准 [已验证: 官方文档, developer.android.com/topic/performance/benchmarking/benchmarking-in-ci]。

另外一个容易被忽略的点:**设备存储空间**。存储空间不足会触发 f2fs 的 GC、影响 dex2oat 编译速度、甚至触发 lmkilld 提前杀进程。测试前确保设备有充足的可用存储空间(至少 20% 以上空闲)。

### 温度控制:性能测试的隐形杀手

温度是 Android 性能测试中最大的变量之一。几乎所有现代 SoC 都会根据温度动态调整 CPU 和 GPU 频率——这就是我们常说的 Thermal Throttling（温控降频）。

一个典型的场景:第一次冷启动测试跑出了 450ms 的好成绩,连续跑十次之后变成了 700ms。代码没变,但 SoC 温度从 35°C 升到了 48°C,大核频率从 2.84GHz 降到了 1.8GHz。如果你不控制温度,测试结果就是不可重复的。

控制温度的实用方法:

- **间隔运行**:每次测试之间等待足够的时间让设备冷却。具体时间取决于测试负载的强度,通常 30 秒到 2 分钟不等。可以在测试脚本中加入 `Thread.sleep()` 或使用 adb 命令监控设备温度(`adb shell cat /sys/class/thermal/thermal_zone*/temp`)
- **物理散热**:对于长时间运行的基准测试(如连续跑 50 次 Macrobenchmark),可以给设备加一个小风扇主动散热
- **温度基线**:在测试开始前记录设备温度,如果温度超过某个阈值(比如 40°C),先暂停测试等待降温。某些团队会使用恒温测试箱来保持测试环境温度恒定

关于温度对性能的具体影响,我们在 §5.5 Thermal 管控中有详细的机制分析。

### 峰值性能和热稳定态分开测

同一个 App 可以有两套性能画像:冷机短时间的峰值表现,以及设备升温后的稳定表现。启动回归、单页面滑动回归更适合看峰值;游戏、视频、直播、长列表连续浏览更适合看热稳定态。两类测试混在一起,报告会把短时间调频收益和长期温控成本混成一个结论。

| 场景 | 测试目标 | 前置状态 | 结束条件 | 报告字段 |
|------|----------|----------|----------|----------|
| 峰值性能测试 | 判断新版本是否引入短路径回归 | 设备冷却到温度阈值以下,清理后台任务 | 固定迭代次数完成,通常 10-30 轮 | 起始温度、结束温度、P50/P90、是否触发 thermal status |
| 热稳定态测试 | 判断持续负载下的体感下限 | 先运行 10-30 分钟目标 workload,等频率和温度进入平台期 | 帧率、时延或功耗曲线进入稳定区间 | 稳态温度、CPU/GPU 频率区间、99th percentile 时延、掉帧率 |

报告里要写清测试属于哪一类。短跑回归不能替代稳态测试,稳态测试也不能用来判断冷启动首轮体验。

### 电量与充电状态

电池电量会影响 SoC 的性能策略。Android 的功耗管理子系统会根据当前电量调整 CPU 频率上限——低电量时系统会进入省电模式，限制大核使用和高频运行。

标准做法:

- 测试时保持电量在 **50% 以上**,避免触发低电量模式
- **充电状态**也需要注意:充电时设备温度上升更快,同时某些 SoC 在充电时会调整调度策略(优先充电效率而非峰值性能)
- 最理想的状态是**连接电源但不充电**——这可以通过将电量充至 100% 后保持连接来实现，但某些设备在充满后会自动切换到小电流模式，行为可能不一致
- 对于严格的基准测试,建议使用**不插电、电量 70-90%** 的状态

### 刷新率与显示模式

高刷新率设备上,60Hz、90Hz、120Hz 的帧 deadline 不同。Adaptive Refresh Rate / Variable Refresh Rate 还可能在测试过程中动态换档,导致滑动帧率、FrameTimeline deadline 和 Macrobenchmark 帧指标不可横比。性能测试前要记录并固定刷新率。

```bash
# 记录原始值,便于测试结束后恢复
adb shell settings get system peak_refresh_rate
adb shell settings get system min_refresh_rate

# 按测试计划固定刷新率;60Hz 是最常见的跨设备基准
adb shell settings put system peak_refresh_rate 60.0
adb shell settings put system min_refresh_rate 60.0

# 验证系统是否接受设置
adb shell dumpsys display | grep -i "refresh"
```

部分 OEM 会忽略这两个 setting,或者在 LTPO 面板上继续做面板级动态刷新率调整。遇到这种设备,要在 Perfetto 的 FrameTimeline 中确认 `expected_display_time` 的间隔是否稳定,并把 `dumpsys display` 的当前 mode 写进报告。测试结束后恢复原始设置;原始值为 `null` 时,用 `settings delete system peak_refresh_rate` / `min_refresh_rate` 清理临时值。

### 网络环境

网络条件对 App 性能测试的影响往往被低估。如果你的 App 在启动时需要拉取配置、预加载内容,网络延迟就会直接体现在启动时间中。

控制方法:

- **离线测试**:对于纯粹测量本地渲染性能(如滑动帧率、布局 inflation 速度),可以开启飞行模式,完全排除网络干扰
- **模拟网络条件**:如果需要测试网络相关场景,使用 `adb shell svc wifi disable` 关闭 WiFi 后通过代理工具限速(见下一条),或使用 `adb shell cmd connectivity` (Android 9+)管理网络连接状态。`ndc`(Network Daemon Connector)需要 root 权限且参数随版本变化较大,不建议在非 root 环境下依赖
- **Charles/Proxyman 限速**:通过代理工具模拟 3G/4G/弱网环境,配合预设的测试数据(避免真实网络请求的不确定性)

[已验证: 官方文档, developer.android.com/topic/performance/benchmarking]

## 消除测试干扰

环境标准化是"宏观"层面的控制。在每次具体测试之前,还需要做一系列"微观"层面的清理工作,把设备恢复到一个干净的初始状态。

### 关闭不必要的后台进程

Android 系统中有大量的后台服务在运行——Google Play Services、系统更新检查、应用同步、定位服务等等。这些后台进程会占用 CPU 时间片、消耗内存、触发 I/O 操作，都可能干扰性能测试。

推荐的清理步骤:

```bash
# 1. 停止所有后台进程同步
adb shell settings put global auto_sync 0

# 2. 关闭定位服务
adb shell settings put secure location_mode 0

# 3. 关闭自动旋转(避免传感器干扰)
adb shell settings put system accelerometer_rotation 0

# 4. 关闭动画(减少系统 UI 对测试的干扰)
adb shell settings put global window_animation_scale 0
adb shell settings put global transition_animation_scale 0
adb shell settings put global animator_duration_scale 0

# 5. 清理最近任务(杀掉所有后台 App)
adb shell am kill-all

# 6. 处理后台 dexopt 干扰(Android 14+ / 部分版本命令名不同)
adb shell cmd package bg-dexopt-job --cancel 2>/dev/null || \
  adb shell cmd package cancel-bg-dexopt-job 2>/dev/null || true

# 只在可恢复的实验设备上临时禁止后台 dexopt;测试结束后恢复为 false
adb shell setprop pm.dexopt.disable_bg_dexopt true 2>/dev/null || true
adb shell cmd package bg-dexopt-job --disable 2>/dev/null || true
```

`am kill-all` 只能杀掉后台 App 进程,拦不住系统维护任务。后台 dexopt 的控制面和执行面要按 Android 版本分开看。Android 14 中,`cmd package bg-dexopt-job` / `cancel-bg-dexopt-job` 的 shell 分发在 `PackageManagerShellCommand.java`,JobScheduler 调度在 `BackgroundDexOptService.java` / `BackgroundDexOptJobService.java`。Android 16 中,`PackageManagerShellCommand.java` 仍保留 `bg-dexopt-job` / `cancel-bg-dexopt-job` 命令入口,ART Service 执行侧落在 `art/libartservice/service/java/com/android/server/art/ArtManagerLocal.java`。设备空闲或充电时的 background dexopt 会带来 CPU 和 I/O 波动,启动、安装后首次运行、CI 基准测试都容易被影响。

`bg-dexopt-job --cancel` / `--disable`、`cancel-bg-dexopt-job` 和 `pm.dexopt.disable_bg_dexopt` 的可用性会随系统版本、权限和厂商实现变化。CI 脚本要记录命令是否执行成功；执行失败时，把 ART 后台优化状态写进测试报告。测试结束后恢复 `pm.dexopt.disable_bg_dexopt=false`，避免长期影响设备的正常优化。

### 固定 CPU 频率(进阶)

对于追求极致稳定性的基准测试,可以锁定 CPU 频率,消除 DVFS(动态电压频率调整)带来的波动。这需要 root 权限,通常用于实验室环境:

```bash
# 确保 CPU 0 在线,再设置调度策略(需要 root)
adb shell "echo 1 > /sys/devices/system/cpu/cpu0/online"
adb shell "echo performance > /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor"
# 也可以同时锁定最低和最高频率(单位 kHz)
adb shell "echo 1785600 > /sys/devices/system/cpu/cpu0/cpufreq/scaling_min_freq"
adb shell "echo 1785600 > /sys/devices/system/cpu/cpu0/cpufreq/scaling_max_freq"
```

[已验证: AOSP sysfs 接口, /sys/devices/system/cpu/cpu*/cpufreq/ 路径在 ARM64 内核中通用。具体频率值因 SoC 而异,可通过 `cat scaling_available_frequencies` 查询。]

对于性能基准测试,更实际的做法是先用 `adb shell settings put global low_power 0` 确保系统不进入低功耗模式。`adb shell cmd thermalservice override-status 0` 可以把 framework 侧的 thermal status 锁到 `THERMAL_STATUS_NONE`,但要注意:这个命令只覆盖 `ThermalManagerService` 的 `mIsStatusOverride`,影响 framework 向 App 投递的 `ThermalStatusChanged` 回调;它不会关闭 vendor 侧的 Thermal HAL、kernel cpufreq/GPU throttling 或 vendor thermal engine。设备仍然会根据真实温度降频。因此这个命令适合用来测试 App 自身的 thermal callback 逻辑,不能当作"锁定 CPU/GPU 峰值性能"的工具。性能基准测试的稳定化应优先依靠温度控制(间隔冷却、物理散热、温度门控),再配合 CPU 频率锁定(需要 root)。测试结束后用 `adb shell cmd thermalservice reset` 恢复默认热控。[已验证: AOSP android-14.0.0_r1 & android-16.0.0_r1, `frameworks/base/services/core/java/com/android/server/power/ThermalManagerService.java` 的 `override-status` 只设置 `mIsStatusOverride` 并覆盖 framework thermal status,不影响 HAL/kernel 侧温控]

Macrobenchmark 库在内部会自动执行一些环境稳定化操作。每次测量前,`AndroidBenchmarkRunner` 通过 `IsolationActivity` 降低窗口干扰(接近全屏、固定亮度);设备支持时启用 **sustained performance mode**(通知调度器/thermal 策略降低频率波动);可选的 side effects 还包括 disable 指定后台 package、暂停 background dexopt 等。[已验证: AOSP androidx-main, benchmark/benchmark-macro/AndroidBenchmarkRunner, IsolationActivity, developer.android.com/topic/performance/benchmarking/macrobenchmark-overview]。

### 环境控制的源码锚点

这些步骤背后对应的源码入口要一并记录,后续排查脚本失效时可以直接回到实现层核对:

- 刷新率设置:`frameworks/base/services/core/java/com/android/server/display/mode/DisplayModeDirector.java` 监听 `Settings.System.PEAK_REFRESH_RATE` / `MIN_REFRESH_RATE`,再参与 display mode 选择。
- 热状态 shell:`frameworks/base/services/core/java/com/android/server/power/ThermalManagerService.java` 暴露 `override-status` / `reset` shell 命令,用于实验环境下临时固定 thermal status。
- 后台 dexopt:shell 命令入口在 `frameworks/base/services/core/java/com/android/server/pm/PackageManagerShellCommand.java`;Android 14 的 JobScheduler 调度代码在 `frameworks/base/services/core/java/com/android/server/pm/BackgroundDexOptService.java` / `BackgroundDexOptJobService.java`;Android 16 的 ART Service 执行入口在 `art/libartservice/service/java/com/android/server/art/ArtManagerLocal.java`。不要沿用旧文中的过期路径。
- Macrobenchmark:`androidx-main/benchmark/benchmark-macro/src/main/java/androidx/benchmark/macro/Macrobenchmark.kt` 中的 `MacrobenchmarkRule.measureRepeated(...)` 负责迭代、编译模式、启动模式和指标采集的编排。

### 屏幕亮度与显示设置

OLED 屏幕的功耗和发热量与显示内容直接相关——全白背景比全黑背景消耗更多电量、产生更多热量。对于长时间运行的基准测试：

- 固定屏幕亮度为中等水平(约 50%),避免自动亮度调节引入波动
- 使用深色测试界面(如果 App 支持 Dark Theme),减少屏幕发热
- 关闭 Always-on Display 和息屏显示功能

## 数据采样策略

测试环境搭建好了,下一步就是:**怎么测,测多少次,怎么统计结果。**

### 为什么不能只测一次

Android 的性能数据天然具有波动性。同一个操作执行多次,每次的耗时都可能不同,原因包括:

- **JIT 编译**:ART 的即时编译器会在运行时优化热点代码。前几次执行可能走解释执行路径,后面的执行走优化后的机器码
- **GC 时机**:垃圾回收可能在任意时刻触发,导致某次测量的耗时突然偏高
- **CPU 缓存状态**:冷启动( caches cold)和热启动(caches warm)的性能差异可达 20-30%
- **调度器噪声**:内核调度器可能在测试期间把当前线程迁移到其他核心,或者被更高优先级的中断抢占

所以,单次测量的数据**几乎没有参考价值**。我们需要的是一个统计意义上的结果。

### 采样次数与统计方法

Google 官方建议 Macrobenchmark 的迭代次数至少 **10 次** [已验证: 官方文档, developer.android.com/topic/performance/benchmarking]。实际操作中,不同场景有不同建议:

- **启动时间测量**:至少 10 次冷启动,取中位数(median)作为基准值,P90 作为"最差情况"的参考
- **帧率测量**:至少 5 次完整的滑动场景,每次覆盖相同的滑动距离和内容
- **Microbenchmark**(微观基准测试):库内部会自动处理 warmup 和迭代,通常配置 20-50 次测量迭代

为什么用中位数而不是平均值？性能数据经常受到异常值的干扰——某次测量恰好遇到了 GC，耗时飙到正常值的 3 倍。如果用平均值，这种异常值会拉高整体结果；而中位数对异常值不敏感，更能反映「典型情况」。

同时关注 P90（90 百分位）也很重要。中位数告诉你「一半用户会体验到什么」，P90 告诉你「10% 的用户会体验到最差是什么情况」。对于性能优化来说，降低 P90 往往比降低中位数更有价值——体验最差的那些用户，正是最容易投诉和卸载的。

**分位数的指标方向**：P90 语义对「越小越好」的指标（耗时、延迟、TTID/TTFD）可以直接使用——P90 耗时越高，尾部越慢。对「越大越好」的指标（FPS、吞吐），P90 反而是「最好的 10%」，不表示尾部劣化。FPS 应改用 **P10/P5**（10%/5% 分位的帧率），或直接换用 **frame duration / jank / slow frames** 这类越小越好的指标来衡量尾部体验。[已验证: 统计学定义, AndroidX Metrics / JankStats frame duration 分位用法]

### Warm-up 轮次

Warm-up(预热)用于消除 JIT 和 profile 收集阶段的初始波动。Macrobenchmark 当前通过 `CompilationMode` 明确控制预编译状态,示例代码也要跟着当前 API 一起更新:

```kotlin
private const val TARGET_PACKAGE = "com.example.app"

@get:Rule
val benchmarkRule = MacrobenchmarkRule()

@Test
fun startupWithPartialCompilation() = benchmarkRule.measureRepeated(
    packageName = TARGET_PACKAGE,
    metrics = listOf(StartupTimingMetric()),
    compilationMode = CompilationMode.Partial(
        baselineProfileMode = BaselineProfileMode.Require,
        warmupIterations = 3,
    ),
    iterations = 10,
    startupMode = StartupMode.COLD,
) {
    pressHome()
    startActivityAndWait(
        Intent(Intent.ACTION_MAIN).apply {
            setPackage(TARGET_PACKAGE)
            addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
        }
    )
}
```

`CompilationMode` 现在主要看四种口径:

- **`CompilationMode.DEFAULT`**:平台默认安装态。API 24+ 上等价于 `Partial(BaselineProfileMode.UseIfAvailable)`,适合模拟用户刚安装后的常见状态
- **`CompilationMode.Partial(...)`**:显式指定部分预编译。可以用 `BaselineProfileMode.Require` 校验 Baseline Profile 是否真的生效,也可以用 `warmupIterations` 模拟 profile guided 编译后的状态
- **`CompilationMode.None()`**:不做预编译,适合观察 fresh install 的最差启动路径
- **`CompilationMode.Full()`**:完全 AOT 编译,适合在实验环境里压低 JIT 噪声,但不代表大多数用户设备上的默认状态

旧资料里常见的 `SpeedProfile()` 已经不在当前公开 API 中。如果你想表达"先跑几轮再按热点编译",现在应改用 `CompilationMode.Partial(warmupIterations = N)` 这组参数。

对比 `DEFAULT`、`Partial(...)` 和 `None()` 可以量化 Baseline Profile 与 warm-up 的收益。具体提升幅度要看你的 App、构建配置和测试设备,不要直接套用固定百分比。

### 冷启动 vs 热启动

性能测试中需要明确区分冷启动、温启动和热启动,因为它们测量的是完全不同的东西:

- **冷启动(Cold Start)**:App 进程不存在,需要从 Zygote fork 并执行完整的 Application.onCreate() → Activity.onCreate() 流程。这是最慢但也是最受关注的指标,直接影响用户对"App 快不快"的感知
- **温启动(Warm Start)**:Activity 被销毁但进程还在(比如用户按了返回键退出,但进程尚未被系统回收)。只需要重新执行 Activity 的生命周期
- **热启动(Hot Start)**:Activity 只是调用了 onStop()(比如用户切到后台再切回来),恢复速度最快

Macrobenchmark 通过 `StartupMode.COLD` / `StartupMode.WARM` / `StartupMode.HOT` 来控制这三种模式。在测试报告中应该分别记录这三种场景的数据，因为它们的优化方向完全不同——冷启动关注的是 dex2oat 编译、ContentProvider 初始化、布局 inflation 的耗时；热启动关注的是 Activity 恢复、View 重建的速度。

## 性能基线管理与回归检测

有了可靠的测试环境和采样策略,下一个要回答的问题:**怎么知道性能是变好了还是变差了?**

### 什么是性能基线

性能基线（Performance Baseline）是一组经过验证的性能数据，作为后续版本比较的参照标准。基线不是随便取一个值——它应该满足以下条件：

- 在**标准化的测试环境**下测得(上面讲的环境标准)
- 经过**足够的迭代次数**(至少 10 次)
- 使用**统计方法**确定(中位数 + P90)
- **附带环境元数据**(设备型号、系统版本、App 版本、测试日期、室温等)

一个典型的性能基线可能长这样:

```
基准设备: Pixel 8, Android 16 (API 36)
测试版本: com.example.app v2.15.0 (release, 2026-03-15)
测试环境: 室温 25°C, 电量 85%, 飞行模式

冷启动:
  中位数: 412ms (P50)
  P90: 487ms
  采样次数: 10

首页滑动帧率:
  中位数: 59.2fps (P50)
  P10: 56.1fps
  慢帧占比: 12/600帧 (2.0%)

内存占用 (启动后稳定态):
  Java Heap: 48.2MB
  Native Heap: 22.7MB
  总 PSS: 126.5MB
```

### 回归检测的阈值设定

有了基线之后,每次代码变更都需要和基线做对比。但波动多少算正常,多少算回归?

这取决于指标的**固有波动性**。冷启动时间的波动通常在 ±5-10%,帧率的波动通常在 ±1-2fps。一个实用的策略是:

- **严格阈值**（P50）：中位数偏离基线超过 **10%** 就触发警告。对于启动时间，412ms 的基线如果新版本中位数超过 453ms，就需要调查
- **宽松阈值**（耗时类 P90 / FPS 类 P10）：耗时类 P90 偏离超过 **20%** 才触发警告，因为 P90 本身波动更大；FPS/吞吐类用 P10 或慢帧占比衡量尾部，偏离 20% 触发警告
- **趋势检测**：如果连续 3 个版本中位数都在缓慢上升（比如 412ms → 418ms → 425ms），即使每次都没有触发阈值，也应该触发趋势告警。这种「温水煮青蛙」式的性能退化最容易被忽略

Macrobenchmark 库输出的是 JSON 格式的结果数据,可以通过 `./gradlew :benchmark:androidTest` 运行后在 `build/outputs/connected_android_test_additional_output/` 目录下找到。将这些数据导入 CI 系统,可以实现自动化的回归检测 [已验证: 官方文档, developer.android.com/topic/performance/benchmarking/benchmarking-in-ci]。

### 版本间的比较方法

两个版本之间的性能比较需要注意:

- **同一台设备**:不同设备的硬件差异(CPU 频率、内存大小、存储速度)会导致同一 App 的性能差出 30% 甚至更多。版本对比必须在同一台设备上进行
- **同样的系统版本**:系统升级可能改变调度策略、GC 行为、渲染管线,导致 App 性能变化。对比时确保系统版本一致
- **多次确认**:如果发现回归,先重跑一次测试排除偶发因素。如果连续两次都确认回归,再开始调查根因

## 测试报告的撰写规范

性能测试的最终产出是一份让读者**能快速理解当前性能状态**的报告。好的性能报告应该让读者在 30 秒内回答三个问题:现在性能怎么样?有没有退化?退化的原因是什么?

### 报告结构

一份完整的性能测试报告应包含以下部分:

**1. 测试概要**

用 3-5 行话概括测试结论。比如:"本次回归测试覆盖冷启动、首页滑动、详情页渲染三个场景。冷启动中位数 425ms,较基线上升 3.1%,在正常波动范围内。首页滑动帧率 P10 降至 52.3fps,慢帧占比翻倍至 4.1%,需关注。"

这一段最影响读者判断——大多数时候，读者只看这一段就够了。

**2. 测试环境**

列出所有影响测试结果的环境参数。包括设备型号、系统版本、App 版本、测试时间、室温(如果进行了温控)、电量、网络条件等。这样当结果出现异常时,读者可以判断是否是环境因素导致的。

**3. 核心指标对比表**

将当前版本的指标与基线并排展示,标注变化幅度。对于退化的指标用红色标注,改善的用绿色标注。表中的数值应同时包含 P50 和 P90:

```
| 指标             | 基线(v2.15.0) | 当前(v2.16.0) | 变化   |
|-----------------|---------------|---------------|--------|
| 冷启动 P50      | 412ms         | 425ms         | +3.1%  |
| 冷启动 P90      | 487ms         | 498ms         | +2.3%  |
| 首页帧率 P50    | 59.2fps       | 58.9fps       | -0.5%  |
| 首页帧率 P10    | 56.1fps       | 52.3fps       | -6.8%↓ |
| 慢帧占比 (>16ms)| 2.0%          | 4.1%          | +105%↑ |
```

注意：表格适合用于**数据汇总**，但关键发现应该用**叙述文字**解释——表格告诉你「是什么」，叙述告诉你「为什么」。

**4. 异常分析与根因**

对于退化的指标，给出初步的根因分析。比如：「首页帧率 P10 退化主要由详情页图片加载引起——新版本将图片缓存策略从 LRU 改为 FIFO，导致在大图场景下缓存命中率降低，频繁触发 Bitmap 解码阻塞主线程。在 Perfetto Trace 中，RenderThread 的 drawBitmap 耗时从 2ms 上升到 8ms。」

**5. 建议与下一步**

给出明确的行动建议,并标注优先级。比如:"P0:修复图片缓存策略回退到 LRU。P1:考虑增加预解码 pipeline,将 Bitmap 解码移到后台线程。P2:下次迭代补充详情页帧率的专项测试。"

### 报告的受众

性能报告可能有不同的读者:

- **开发工程师**:关注具体的技术细节和根因分析,需要 Trace 截图和源码引用
- **技术负责人/管理者**:关注整体趋势和风险,需要清晰的是否通过的结论和变化趋势图
- **QA 团队**:关注测试覆盖了哪些场景、测试方法是否可靠

一份好的报告应该让不同读者都能快速找到自己关心的部分。

## 扩展:Macrobenchmark 在 CI 中的集成实践

把 Macrobenchmark 集成到 CI 管线中,是性能守护体系从"手动测试"升级到"持续监控"的关键一步。但 CI 环境和本地测试有一个重大区别:**CI 设备通常是共享的、状态不确定的**。

### CI 环境的特殊挑战

在本地测试时,我们可以手动确保设备温度、电量、后台进程都处于理想状态。但在 CI 中,上一个 Job 可能刚跑完一个 CPU 密集型的测试,设备温度还很高。或者上一次测试留下了大量的后台进程没有清理。

应对策略:

- **设备重置**:每次基准测试前执行完整的设备环境重置脚本(上面提到的那些 adb 命令)。宁可多花 30 秒做清理,也不要在不稳定的状态下浪费 10 分钟跑出无效数据
- **温度门控**:在测试脚本开头加入温度检查,如果设备温度超过阈值,先等待降温再开始测试
- **结果缓存与对比**:将每次 CI 跑出的基准数据持久化存储(比如存在数据库或 CI artifacts 中),自动与最近 5 次的平均值做对比

### Gradle 配置示例

在 CI 中运行 Macrobenchmark,推荐使用 Gradle Managed Devices(GMD)来确保设备配置的一致性:

```groovy
// build.gradle (benchmark module)
android {
    testOptions {
        managedDevices {
            devices {
                pixel8Api36(com.android.build.api.dsl.ManagedVirtualDevice) {
                    device = "Pixel 8"
                    apiLevel = 36
                    systemImageSource = "aosp"
                }
            }
        }
    }
}
```

CI 命令:

```bash
./gradlew :benchmark:pixel8Api36BenchmarkAndroidTest
```

GMD 使用的是模拟器,性能数据与真机有较大差异(特别是 GPU 和存储性能)。因此 CI 中的基准数据更适合用于**回归检测**(对比变化趋势),而不是**绝对性能评估**(判断是否达到目标)。绝对性能评估还是要在真机上进行 [已验证: 官方文档, developer.android.com/topic/performance/benchmarking/benchmarking-in-ci]。

### 结果的自动分析

Macrobenchmark 输出的 JSON 结果可以通过 `androidx.benchmark:benchmark-junit4` 库解析,集成到 CI 的测试报告中:

```kotlin
@Test
fun startupBenchmark() {
    benchmarkRule.measureRepeated(
        packageName = "com.example.app",
        metrics = listOf(StartupTimingMetric()),
        compilationMode = CompilationMode.DEFAULT,
        iterations = 10,
        startupMode = StartupMode.COLD,
    ) {
        pressHome()
        startActivityAndWait(
            Intent(Intent.ACTION_MAIN).apply {
                setPackage("com.example.app")
                addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            }
        )
    }
}
```

测试结果会包含 `metricName`、`median`、`minimum`、`maximum`、`p90`、`runs` 等字段。CI 管线可以将这些数据与基线做自动对比,如果超出阈值就标记为失败或警告。

## 扩展:使用 Firebase Performance Monitoring 的限制与替代方案

Firebase Performance Monitoring(FPM)是 Google 提供的线上性能监控服务,可以自动收集 App 的启动时间、网络请求耗时、自定义 Trace 等数据。它在"线上真实用户数据"这个维度上是无可替代的,但在使用中有一些需要注意的限制。

### FPM 的主要限制

**采样策略不透明**。FPM 的采样由平台侧控制,开发者不能按实验批次或设备分层精确指定样本量。它更适合看整体趋势,不适合拿来做严格的实验设计。

**自定义 Trace 的限制是按单条 trace 计算**。官方约束包括：trace name 最长 100 个字符、每条 custom code trace 最多 5 个 custom attributes、最多 32 个 metrics（含默认的 Duration）。需要控制的是字段数量和名称基数，不能简单记成「应用最多 100 个 Trace」[已验证: Firebase Performance Monitoring limits, firebase.google.com/docs/perf-mon/troubleshooting#performance-monitoring-limits]。

**数据粒度有限**。FPM 提供的是聚合指标,适合看 P50/P95/P99 和版本趋势,不适合还原单个会话的完整上下文。

**数据延迟**。FPM 的数据上报通常存在小时级到天级延迟,适合版本趋势观察,不适合发布后立刻做小时级回归判定。

### 替代方案

对于需要更细粒度或更低延迟的线上性能监控,可以考虑以下方案:

- **自建性能数据采集**:通过 `Choreographer.FrameCallback`、`System.nanoTime()`、自定义埋点和批量上报拿到会话级数据。这是 §15.5 线上性能监控里展开的方法
- **APM 平台**:使用 Matrix、Booster、DoKit 等工具补足更细粒度的端侧采样与聚合
- **Android vitals / Play Console**:用来观察慢帧、卡帧、ANR 等版本级趋势,适合和实验室基准测试做交叉验证
- **CrUX**:只适用于公开网页在 Chrome 侧的真实用户指标,不覆盖 Android WebView 容器内的页面。App 内嵌 WebView 仍然要靠自埋点或 APM 采集

实战里常见的组合是:实验室基准测试负责回归闸门,FPM 或 Android vitals 负责版本趋势,自建/APM 负责会话级排查。

## 在 Perfetto 中的表现

性能测试的数据虽然主要来自 Macrobenchmark 和自定义采集,但 **Perfetto Trace 是验证测试结果的最佳工具**。当你发现某个版本的启动时间退化了 50ms,第一步就是抓一个 Trace 看这 50ms 花在哪里。

在 Perfetto 中验证性能测试数据的方法:

- **启动时间验证**:在 Trace 中定位目标进程的启动时间点(搜索 `proc_start` 或 `ActivityManager: Start proc`),到首帧绘制完成(搜索 `Choreographer#doFrame` 或 `firstDraw`)之间的时间差,应该与 Macrobenchmark 报告的 `timeToInitialDisplay` 基本一致。TTFD 要求 App 在首屏业务内容可用时调用 `Activity.reportFullyDrawn()`;Macrobenchmark 才能稳定产出 `timeToFullDisplay`。报告里要把 TTID 和 TTFD 分开列,避免把两个指标都写成"启动时间"
- **帧率验证**:在 RenderThread track 中检查 `DrawFrame` 切片的耗时分布。正常情况下 60fps 设备的 DrawFrame 应该在 16ms 以内,120fps 设备应该在 8ms 以内。超过阈值的 DrawFrame 就是掉帧
- **内存占用验证**:在 Trace 的 `memtrack` track 或 `Process Stats` 中查看目标进程的内存使用情况,与测试报告中的内存数据做交叉验证

如果在 Trace 中发现的数据与基准测试报告不一致，通常说明测试环境存在未被控制的变量——比如后台有大量 I/O 活动、系统正在进行 dex2oat 编译等。这时需要回到环境标准化步骤，排查干扰源。

## 与其他机制的关系

性能测试最佳实践不是孤立的,它与本书其他章节有紧密的关联:

- **§14.6 自动化测试工具**:介绍了 Macrobenchmark、Microbenchmark、UI Automator 等具体工具的使用方法。本节侧重的是"怎么用好这些工具"的方法论层面
- **§15.5 线上性能监控**：基准测试是实验室环境下的测量，线上监控是真实用户环境下的测量。两者互补——基线管「回归检测」，线上管「真实体验」
- **§8.3 启动优化策略**:冷启动是最核心的性能指标之一,本节讲怎么可靠地测量启动时间,§8.3 讲怎么优化它
- **§13.2 Trace 抓取**:当基准测试发现性能退化时,需要用 Trace 定位根因。两章配合使用
- **§5.5 Thermal 管控**:理解温控机制才能理解为什么温度控制对测试如此重要

## 常见问题与误区

### "性能测试应该用最高端的设备"

不应该只看最高端设备。如果目标用户中高端设备只占 20%，旗舰机上跑出来的数据对 80% 的用户都没有参考价值。选择测试设备时应该优先覆盖主力用户群的设备档次。

### "一次测试就够了,多跑几次浪费时间"

单次测试的数据没有任何统计意义。一次冷启动 350ms 的数据不能说明你的启动速度就是 350ms——可能是刚好这次 GC 没有触发、CPU 频率刚好最高、缓存刚好命中。至少 10 次采样、取中位数和尾部分位（耗时类用 P90，帧率类用 P10 或慢帧占比），才能得到有参考价值的数据。

### "CI 里跑的基准测试和本地跑的不一致,一定是 CI 有问题"

不一定。先检查 CI 和本地的测试环境差异——设备是否相同、系统版本是否一致、温度条件是否接近。如果环境确认一致但结果仍然不一致，可能是 CI 并行执行带来了额外的资源竞争。CI 基准数据更适合看趋势，不适合看绝对值。

### "性能基线不需要更新"

性能基线不是一成不变的。当 App 引入了重大的新功能（比如全新的首页设计），旧的基线可能就不再适用了。每次大版本发布后，都应该重新建立基线。但要注意：新基线和旧基线之间要有清晰的交接记录，避免「基线漂移」——每次重新建基线都放宽一点标准，几个版本下来标准就形同虚设了。

### "自动化测试可以替代手动性能分析"

自动化基准测试能告诉你"有没有退化",但不能告诉你"为什么退化"。它是一个"报警器",不是"诊断仪"。当自动化测试发现回归时,还是需要工程师手动抓 Trace、分析日志、定位根因。自动化和手动分析是互补的,不是替代关系。

## 参考资料

- [Benchmarking in CI | Android Developers](https://developer.android.com/topic/performance/benchmarking/benchmarking-in-ci) - 官方 CI 集成指南
- [Macrobenchmark | Android Developers](https://developer.android.com/topic/performance/benchmarking/macrobenchmark-overview) - Macrobenchmark 使用文档
- [CompilationMode | Android Developers](https://developer.android.com/reference/kotlin/androidx/benchmark/macro/CompilationMode) - Macrobenchmark 编译模式定义
- [Firebase Performance Monitoring limits | Firebase](https://firebase.google.com/docs/perf-mon/troubleshooting#performance-monitoring-limits) - 自定义 Trace 的字段限制
- [Microbenchmark | Android Developers](https://developer.android.com/topic/performance/benchmarking/microbenchmark-overview) - Microbenchmark 使用文档
- [Baseline Profiles | Android Developers](https://developer.android.com/topic/performance/baselineprofiles) - Baseline Profiles 生成与使用
- [Measure performance | Android Developers](https://developer.android.com/topic/performance) - 性能测量总入口
- AOSP 路径:`frameworks/base/services/core/java/com/android/server/power/ThermalManagerService.java`(thermalservice shell 命令)
- AOSP 路径:`frameworks/base/services/core/java/com/android/server/display/mode/DisplayModeDirector.java`(刷新率 setting 与 mode 选择)
- AOSP 路径:`frameworks/base/services/core/java/com/android/server/pm/PackageManagerShellCommand.java`(`bg-dexopt-job` / `cancel-bg-dexopt-job` shell 命令分发)
- AOSP 路径:`frameworks/base/services/core/java/com/android/server/pm/BackgroundDexOptService.java`(Android 14 后台 dexopt 服务调度)
- AOSP 路径:`frameworks/base/services/core/java/com/android/server/pm/BackgroundDexOptJobService.java`(Android 14 JobService 调度入口)
- AOSP 路径:`art/libartservice/service/java/com/android/server/art/ArtManagerLocal.java`(Android 16 ART Service 优化执行入口)
- AOSP 路径:`frameworks/base/core/java/android/app/Activity.java`(`reportFullyDrawn()` / 启动时间相关 API)
- AOSP 路径:`frameworks/base/core/java/android/view/Choreographer.java`(帧回调 API)
- AndroidX 路径:`androidx-main/benchmark/benchmark-macro/src/main/java/androidx/benchmark/macro/CompilationMode.kt`(CompilationMode 定义)
