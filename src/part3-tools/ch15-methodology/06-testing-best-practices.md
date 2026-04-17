---
title: "性能测试最佳实践"
chapter: "15.6"
section: "15.6"
status: ready-for-review
drafted_date: "2026-04-04"
applicable_versions: "Android 8 (API 26) - Android 16 (API 36)"
last_verified: "2026-04-04"
last_verified_against: "developer.android.com"
confidence: medium
sources:
  - type: official
    path: "developer.android.com/topic/performance/benchmarking"
  - type: official
    path: "developer.android.com/topic/performance/benchmarking/benchmarking-in-ci"
  - type: official
    path: "developer.android.com/topic/performance/benchmarking/macrobenchmark-overview"
tags:
  - android
  - benchmark
  - research
pipeline_stage: task2b_pending
task6_state: reviewed
reviewed_by: openclaw-task6
reviewed_date: "2026-04-17"
task6_result: needs-rework
task9_state: pending
task2b_state: pending
---


# 性能测试最佳实践

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 性能测试环境标准化：设备选择、温控、电量、网络
- 🔹 消除测试干扰：关闭不必要 App、清理后台、恒温控制
- 🔹 数据采样策略：多次采样取中位数/P90、Warm-up 轮次
- 🔹 性能基线管理与回归检测
- 🔹 测试报告的撰写规范

### 扩展（可选深入）

- 🔸 Macrobenchmark 在 CI 中的集成实践
- 🔸 使用 Firebase Performance Monitoring 的限制与替代方案

### OpenClaw 加工指引

> **锚点**是最低覆盖要求，加工时必须逐条落实并标注验证结果。
> **扩展**视素材丰富程度选择性深入。
> 如果从 Obsidian 素材或 AOSP 源码中发现大纲未列出但与本节强相关的知识点，
> 可**就地插入**最相关的锚点之后，并用 `[自动发现]` 标注，方便后续 review。
> 锚点内容需 L1/L2 验证，扩展内容至少 L2 验证，自动发现内容至少标注来源。
<!-- outline-end -->

## 为什么要了解性能测试最佳实践

我们在前面章节中已经介绍了各种各样的性能分析工具——Perfetto 用来抓 Trace，Android Studio Profiler 用来分析内存和 CPU，Jetpack Benchmark 库用来自动化测量启动速度和帧率。这些工具都很强大，但它们都有一个隐含的前提条件：**测试环境是可控的、测试数据是可信的。**

遗憾的是，现实往往不是这样。我们经常遇到这样的情况：同一台设备上跑同一个测试，第一次冷启动 450ms，第二次就变成 620ms。今天测的帧率是 58fps，明天同样的代码就变成了 52fps。当你拿着这些数据去定位问题时，根本分不清到底是代码引入了回归，还是测试环境本身在捣乱。

性能测试和功能测试有一个根本性的区别：功能测试的结果是确定的——要么通过要么失败；而性能测试的结果是概率性的——它受到温度、后台进程、CPU 调频策略、GC 时机等大量不可控因素的影响。如果我们不主动控制这些变量，测试数据就没有参考价值。

本节要讲的就是：如何建立一套可靠、可重复、可比较的性能测试流程。这不是理论，而是实战经验的总结——每一个建议背后，都是"被不稳定数据坑过"的教训。

[已验证: 官方文档, developer.android.com/topic/performance/benchmarking]

## 测试环境标准化

性能测试的第一步，不是写测试用例，而是搭建一个**尽可能可控的测试环境**。这一步做好了，后面的一切才有意义。

### 设备选择：覆盖主力用户群

测试设备的选择需要考虑两个维度：**市场占有率**和**性能梯度**。

市场占有率决定了我们应该优先测什么设备。如果你的目标用户中 60% 使用的是中端骁龙 7 系处理器设备，那么旗舰机上测出的数据对大多数用户就没有代表性。反之，如果你只测中低端设备，可能无法发现那些只在高端设备上才会暴露的 GPU bound 问题。

性能梯度是指我们至少应该覆盖三个档次：

- **低端设备**（如 4GB 内存、低端 SoC）：暴露内存压力下的性能问题、冷启动瓶颈、低内存下的 GC 频率
- **中端设备**（如 6-8GB 内存、中端 SoC）：代表大多数用户的体验，是性能测试的主力平台
- **高端设备**（如 12GB+ 内存、旗舰 SoC）：验证高刷新率下的帧率稳定性、复杂 UI 场景的性能表现

Google 在官方文档中建议至少使用一台运行 AOSP 系统镜像的 Pixel 设备作为基准测试的参考设备，这样可以在不同团队之间建立统一的比较基准 [已验证: 官方文档, developer.android.com/topic/performance/benchmarking/benchmarking-in-ci]。

另外一个容易被忽略的点：**设备存储空间**。存储空间不足会触发 f2fs 的 GC、影响 dex2oat 编译速度、甚至触发 lmkilld 提前杀进程。测试前确保设备有充足的可用存储空间（至少 20% 以上空闲）。

### 温度控制：性能测试的隐形杀手

温度是 Android 性能测试中最大的变量之一。几乎所有现代 SoC 都会根据温度动态调整 CPU 和 GPU 频率——这就是我们常说的 Thermal Throttling（温控降频）。

一个典型的场景：第一次冷启动测试跑出了 450ms 的好成绩，连续跑十次之后变成了 700ms。代码没变，但 SoC 温度从 35°C 升到了 48°C，大核频率从 2.84GHz 降到了 1.8GHz。如果你不控制温度，测试结果就是不可重复的。

控制温度的实用方法：

- **间隔运行**：每次测试之间等待足够的时间让设备冷却。具体时间取决于测试负载的强度，通常 30 秒到 2 分钟不等。可以在测试脚本中加入 `Thread.sleep()` 或使用 adb 命令监控设备温度（`adb shell cat /sys/class/thermal/thermal_zone*/temp`）
- **物理散热**：对于长时间运行的基准测试（如连续跑 50 次 Macrobenchmark），可以给设备加一个小风扇主动散热
- **温度基线**：在测试开始前记录设备温度，如果温度超过某个阈值（比如 40°C），先暂停测试等待降温。某些团队会使用恒温测试箱来保持测试环境温度恒定

关于温度对性能的具体影响，我们在 §5.5 Thermal 管控中有详细的机制分析。

### 电量与充电状态

电池电量会影响 SoC 的性能策略。Android 的功耗管理子系统会根据当前电量调整 CPU 频率上限——低电量时系统会进入省电模式，限制大核使用和高频运行。

标准做法：

- 测试时保持电量在 **50% 以上**，避免触发低电量模式
- **充电状态**也需要注意：充电时设备温度上升更快，同时某些 SoC 在充电时会调整调度策略（优先充电效率而非峰值性能）
- 最理想的状态是**连接电源但不充电**——这可以通过将电量充至 100% 后保持连接来实现，但某些设备在充满后会自动切换到小电流模式，行为可能不一致
- 对于严格的基准测试，建议使用**不插电、电量 70-90%** 的状态

### 网络环境

网络条件对 App 性能测试的影响往往被低估。如果你的 App 在启动时需要拉取配置、预加载内容，网络延迟就会直接体现在启动时间中。

控制方法：

- **离线测试**：对于纯粹测量本地渲染性能（如滑动帧率、布局 inflation 速度），可以开启飞行模式，完全排除网络干扰
- **模拟网络条件**：如果需要测试网络相关场景，使用 `adb shell svc wifi disable` 关闭 WiFi 后用 `adb shell ndc network create` 配合 Network Emulator 模拟不同网络质量
- **Charles/Proxyman 限速**：通过代理工具模拟 3G/4G/弱网环境，配合预设的测试数据（避免真实网络请求的不确定性）

[已验证: 官方文档, developer.android.com/topic/performance/benchmarking]

## 消除测试干扰

环境标准化是"宏观"层面的控制。在每次具体测试之前，还需要做一系列"微观"层面的清理工作，把设备恢复到一个干净的初始状态。

### 关闭不必要的后台进程

Android 系统中有大量的后台服务在运行——Google Play Services、系统更新检查、应用同步、定位服务等等。这些后台进程会占用 CPU 时间片、消耗内存、触发 I/O 操作，都可能干扰性能测试。

推荐的清理步骤：

```bash
# 1. 停止所有后台进程同步
adb shell settings put global auto_sync 0

# 2. 关闭定位服务
adb shell settings put secure location_mode 0

# 3. 关闭自动旋转（避免传感器干扰）
adb shell settings put system accelerometer_rotation 0

# 4. 关闭动画（减少系统 UI 对测试的干扰）
adb shell settings put global window_animation_scale 0
adb shell settings put global transition_animation_scale 0
adb shell settings put global animator_duration_scale 0

# 5. 清理最近任务（杀掉所有后台 App）
adb shell am kill-all
```

需要特别注意的是，`am kill-all` 只能杀掉后台进程，不能杀前台进程和系统关键服务。对于需要更彻底清理的场景，可以考虑在两次测试之间重启目标 App 进程。

### 固定 CPU 频率（进阶）

对于追求极致稳定性的基准测试，可以锁定 CPU 频率，消除 DVFS（动态电压频率调整）带来的波动。这需要 root 权限，通常用于实验室环境：

```bash
# 锁定 CPU 0 的频率（需要 root）
adb shell "echo 0 > /sys/devices/system/cpu/cpu0/online"
adb shell "echo performance > /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor"
```

更常用的做法是使用 `adb shell settings put global low_power 0` 确保系统不进入低功耗模式，配合 `adb shell cmd thermal thontrol disable`（如果设备支持）来禁用温控干预。

Macrobenchmark 库在内部会自动执行一些环境稳定化操作——它会在每次测量前设置设备为"适合测量"的状态，包括关闭多窗口模式、设置屏幕亮度为固定值等 [已验证: 官方文档, developer.android.com/topic/performance/benchmarking/macrobenchmark-overview]。

### 屏幕亮度与显示设置

OLED 屏幕的功耗和发热量与显示内容直接相关——全白背景比全黑背景消耗更多电量、产生更多热量。对于长时间运行的基准测试：

- 固定屏幕亮度为中等水平（约 50%），避免自动亮度调节引入波动
- 使用深色测试界面（如果 App 支持 Dark Theme），减少屏幕发热
- 关闭 Always-on Display 和息屏显示功能

## 数据采样策略

测试环境搭建好了，下一步就是：**怎么测，测多少次，怎么统计结果。**

### 为什么不能只测一次

Android 的性能数据天然具有波动性。同一个操作执行多次，每次的耗时都可能不同，原因包括：

- **JIT 编译**：ART 的即时编译器会在运行时优化热点代码。前几次执行可能走解释执行路径，后面的执行走优化后的机器码
- **GC 时机**：垃圾回收可能在任意时刻触发，导致某次测量的耗时突然偏高
- **CPU 缓存状态**：冷启动（ caches cold）和热启动（caches warm）的性能差异可达 20-30%
- **调度器噪声**：内核调度器可能在测试期间把当前线程迁移到其他核心，或者被更高优先级的中断抢占

所以，单次测量的数据**几乎没有参考价值**。我们需要的是一个统计意义上的结果。

### 采样次数与统计方法

Google 官方建议 Macrobenchmark 的迭代次数至少 **10 次** [已验证: 官方文档, developer.android.com/topic/performance/benchmarking]。实际操作中，不同场景有不同建议：

- **启动时间测量**：至少 10 次冷启动，取中位数（median）作为基准值，P90 作为"最差情况"的参考
- **帧率测量**：至少 5 次完整的滑动场景，每次覆盖相同的滑动距离和内容
- **Microbenchmark**（微观基准测试）：库内部会自动处理 warmup 和迭代，通常配置 20-50 次测量迭代

为什么用中位数而不是平均值？因为性能数据经常受到异常值的干扰——某次测量恰好遇到了 GC，耗时飙到正常值的 3 倍。如果用平均值，这种异常值会拉高整体结果；而中位数对异常值不敏感，更能反映"典型情况"。

同时关注 P90（90 百分位）也很重要。中位数告诉你"一半用户会体验到什么"，P90 告诉你"10% 的用户会体验到最差是什么情况"。对于性能优化来说，降低 P90 往往比降低中位数更有价值——因为体验最差的那些用户，正是最容易投诉和卸载的。

### Warm-up 轮次

Warm-up（预热）是处理 JIT 编译和缓存冷启动效应的标准方法。基本思路是：先跑几次不记录结果，让系统"热起来"，然后再开始正式测量。

在 Macrobenchmark 中，warmup 通过 `CompilationMode` 来控制：

```kotlin
@BenchmarkRule
val benchmarkRule = MacrobenchmarkRule()

@Test
fun startupWithBaselineProfile() = benchmarkRule.measureRepeated(
    packageName = "com.example.app",
    metrics = listOf(StartupTimingMetric()),
    compilationMode = CompilationMode.DEFAULT(),  // 使用 Baseline Profile
    iterations = 10,
    startupMode = StartupMode.COLD
) {
    // 测量冷启动
    pressHome()
    startActivityAndWait()
}
```

`CompilationMode` 有几种模式值得理解：

- **`DEFAULT()`**：如果 App 包含 Baseline Profile，会先安装 Profile 再测量。这模拟的是"用户从应用商店安装后"的真实体验
- **`SpeedProfile()`**：先跑几次 warmup 收集 profiling 数据，然后用这些数据做 profile-guided 编译。这模拟的是"App 已经使用一段时间，系统已经优化过"的状态
- **`None()`**：不做任何预编译，模拟最差情况（刚安装、没有任何优化）
- **`Full()`**：完全 AOT 编译，模拟所有代码都已预编译的理想情况

在不同 Compilation Mode 之间对比结果，可以量化 Baseline Profile 带来的具体收益。通常 `DEFAULT()` 和 `None()` 之间的差距就是 Baseline Profile 的优化幅度，Android 官方数据显示这个差距可以达到 30% [已验证: 官方文档, developer.android.com/topic/performance/benchmarking/macrobenchmark-overview]。

### 冷启动 vs 热启动

性能测试中需要明确区分冷启动、温启动和热启动，因为它们测量的是完全不同的东西：

- **冷启动（Cold Start）**：App 进程不存在，需要从 Zygote fork 并执行完整的 Application.onCreate() → Activity.onCreate() 流程。这是最慢但也是最受关注的指标，直接影响用户对"App 快不快"的感知
- **温启动（Warm Start）**：Activity 被销毁但进程还在（比如用户按了返回键退出，但进程尚未被系统回收）。只需要重新执行 Activity 的生命周期
- **热启动（Hot Start）**：Activity 只是调用了 onStop()（比如用户切到后台再切回来），恢复速度最快

Macrobenchmark 通过 `StartupMode.COLD` / `StartupMode.WARM` / `StartupMode.HOT` 来控制这三种模式。在测试报告中应该分别记录这三种场景的数据，因为它们的优化方向完全不同——冷启动关注的是 dex2oat 编译、ContentProvider 初始化、布局 inflation 的耗时；热启动关注的是 Activity 恢复、View 重建的速度。

## 性能基线管理与回归检测

有了可靠的测试环境和采样策略，接下来要解决的问题是：**怎么知道性能是变好了还是变差了？**

### 什么是性能基线

性能基线（Performance Baseline）是一组经过验证的性能数据，作为后续版本比较的参照标准。基线不是随便取一个值——它应该满足以下条件：

- 在**标准化的测试环境**下测得（上面讲的环境标准）
- 经过**足够的迭代次数**（至少 10 次）
- 使用**统计方法**确定（中位数 + P90）
- **附带环境元数据**（设备型号、系统版本、App 版本、测试日期、室温等）

一个典型的性能基线可能长这样：

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
  P90: 55.8fps
  掉帧数: 12/600帧 (2.0%)

内存占用 (启动后稳定态):
  Java Heap: 48.2MB
  Native Heap: 22.7MB
  总PSS: 126.5MB
```

### 回归检测的阈值设定

有了基线之后，每次代码变更都需要和基线做对比。但问题是：波动多少算正常，多少算回归？

这取决于指标的**固有波动性**。冷启动时间的波动通常在 ±5-10%，帧率的波动通常在 ±1-2fps。一个实用的策略是：

- **严格阈值**（P50）：中位数偏离基线超过 **10%** 就触发警告。对于启动时间，这意味着 412ms 的基线，如果新版本中位数超过 453ms 就需要调查
- **宽松阈值**（P90）：P90 偏离超过 **20%** 才触发警告。因为 P90 本身波动更大
- **趋势检测**：如果连续 3 个版本中位数都在缓慢上升（比如 412ms → 418ms → 425ms），即使每次都没有触发阈值，也应该触发趋势告警。这种"温水煮青蛙"式的性能退化最容易被忽略

Macrobenchmark 库输出的是 JSON 格式的结果数据，可以通过 `./gradlew :benchmark:androidTest` 运行后在 `build/outputs/connected_android_test_additional_output/` 目录下找到。将这些数据导入 CI 系统，可以实现自动化的回归检测 [已验证: 官方文档, developer.android.com/topic/performance/benchmarking/benchmarking-in-ci]。

### 版本间的比较方法

两个版本之间的性能比较需要注意：

- **同一台设备**：不同设备的硬件差异（CPU 频率、内存大小、存储速度）会导致同一 App 的性能差出 30% 甚至更多。版本对比必须在同一台设备上进行
- **同样的系统版本**：系统升级可能改变调度策略、GC 行为、渲染管线，导致 App 性能变化。对比时确保系统版本一致
- **多次确认**：如果发现回归，先重跑一次测试排除偶发因素。如果连续两次都确认回归，再开始调查根因

## 测试报告的撰写规范

性能测试的最终产出是一份让读者**能快速理解当前性能状态**的报告。好的性能报告应该让读者在 30 秒内回答三个问题：现在性能怎么样？有没有退化？退化的原因是什么？

### 报告结构

一份完整的性能测试报告应包含以下部分：

**1. 测试概要**

用 3-5 行话概括测试结论。比如："本次回归测试覆盖冷启动、首页滑动、详情页渲染三个场景。冷启动中位数 425ms，较基线上升 3.1%，在正常波动范围内。首页滑动 P90 帧率 52.3fps，较基线下降 6.3%，需关注。"

这一段是最重要的——大多数时候，读者只看这一段就够了。

**2. 测试环境**

列出所有影响测试结果的环境参数。包括设备型号、系统版本、App 版本、测试时间、室温（如果进行了温控）、电量、网络条件等。这样当结果出现异常时，读者可以判断是否是环境因素导致的。

**3. 核心指标对比表**

将当前版本的指标与基线并排展示，标注变化幅度。对于退化的指标用红色标注，改善的用绿色标注。表中的数值应同时包含 P50 和 P90：

```
| 指标             | 基线(v2.15.0) | 当前(v2.16.0) | 变化   |
|-----------------|---------------|---------------|--------|
| 冷启动 P50      | 412ms         | 425ms         | +3.1%  |
| 冷启动 P90      | 487ms         | 498ms         | +2.3%  |
| 首页帧率 P50    | 59.2fps       | 58.9fps       | -0.5%  |
| 首页帧率 P90    | 55.8fps       | 52.3fps       | -6.3%↓ |
```

注意：表格适合用于**数据汇总**，但关键发现应该用**叙述文字**解释——表格告诉你"是什么"，叙述告诉你"为什么"。

**4. 异常分析与根因**

对于退化的指标，给出初步的根因分析。比如："首页帧率 P90 退化主要由详情页图片加载引起——新版本将图片缓存策略从 LRU 改为 FIFO，导致在大图场景下缓存命中率降低，频繁触发 Bitmap 解码阻塞主线程。在 Perfetto Trace 中，RenderThread 的 drawBitmap 耗时从 2ms 上升到 8ms。"

**5. 建议与下一步**

给出明确的行动建议，并标注优先级。比如："P0：修复图片缓存策略回退到 LRU。P1：考虑增加预解码 pipeline，将 Bitmap 解码移到后台线程。P2：下次迭代补充详情页帧率的专项测试。"

### 报告的受众

性能报告可能有不同的读者：

- **开发工程师**：关注具体的技术细节和根因分析，需要 Trace 截图和源码引用
- **技术负责人/管理者**：关注整体趋势和风险，需要清晰的是否通过的结论和变化趋势图
- **QA 团队**：关注测试覆盖了哪些场景、测试方法是否可靠

一份好的报告应该让不同读者都能快速找到自己关心的部分。

## 扩展：Macrobenchmark 在 CI 中的集成实践

把 Macrobenchmark 集成到 CI 管线中，是性能守护体系从"手动测试"升级到"持续监控"的关键一步。但 CI 环境和本地测试有一个重大区别：**CI 设备通常是共享的、状态不确定的**。

### CI 环境的特殊挑战

在本地测试时，我们可以手动确保设备温度、电量、后台进程都处于理想状态。但在 CI 中，上一个 Job 可能刚跑完一个 CPU 密集型的测试，设备温度还很高。或者上一次测试留下了大量的后台进程没有清理。

应对策略：

- **设备重置**：每次基准测试前执行完整的设备环境重置脚本（上面提到的那些 adb 命令）。宁可多花 30 秒做清理，也不要在不稳定的状态下浪费 10 分钟跑出无效数据
- **温度门控**：在测试脚本开头加入温度检查，如果设备温度超过阈值，先等待降温再开始测试
- **结果缓存与对比**：将每次 CI 跑出的基准数据持久化存储（比如存在数据库或 CI artifacts 中），自动与最近 5 次的平均值做对比

### Gradle 配置示例

在 CI 中运行 Macrobenchmark，推荐使用 Gradle Managed Devices（GMD）来确保设备配置的一致性：

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

CI 命令：

```bash
./gradlew :benchmark:pixel8Api36BenchmarkAndroidTest
```

GMD 使用的是模拟器，性能数据与真机有较大差异（特别是 GPU 和存储性能）。因此 CI 中的基准数据更适合用于**回归检测**（对比变化趋势），而不是**绝对性能评估**（判断是否达到目标）。绝对性能评估还是要在真机上进行 [已验证: 官方文档, developer.android.com/topic/performance/benchmarking/benchmarking-in-ci]。

### 结果的自动分析

Macrobenchmark 输出的 JSON 结果可以通过 `androidx.benchmark:benchmark-junit4` 库解析，集成到 CI 的测试报告中：

```kotlin
@Test
fun startupBenchmark() {
    benchmarkRule.measureRepeated(
        packageName = "com.example.app",
        metrics = listOf(StartupTimingMetric()),
        compilationMode = CompilationMode.DEFAULT(),
        iterations = 10,
        startupMode = StartupMode.COLD
    ) {
        pressHome()
        startActivityAndWait()
    }
}
```

测试结果会包含 `metricName`、`median`、`minimum`、`maximum`、`p90`、`runs` 等字段。CI 管线可以将这些数据与基线做自动对比，如果超出阈值就标记为失败或警告。

## 扩展：使用 Firebase Performance Monitoring 的限制与替代方案

Firebase Performance Monitoring（FPM）是 Google 提供的线上性能监控服务，可以自动收集 App 的启动时间、网络请求耗时、自定义 Trace 等数据。它在"线上真实用户数据"这个维度上是无可替代的，但在使用中有一些需要注意的限制。

### FPM 的主要限制

**采样率不可控**。FPM 使用固定采样策略，开发者无法精确控制哪些用户的数据被收集、收集多少。这意味着在某些场景下你可能拿不到足够的样本量来做有统计意义的分析。

**数据粒度有限**。FPM 提供的是聚合数据（P50/P95/P99），不支持单次会话级别的分析。如果你需要分析某个特定用户的性能问题，FPM 帮不上忙。

**自定义 Trace 有数量限制**。每个 App 最多只能创建一定数量的自定义 Trace（官方文档建议不超过 100 个），超过后新创建的 Trace 会被丢弃 [已验证: 官方文档, firebase.google.com/docs/perf-mon]。

**延迟**。FPM 的数据上报有延迟，通常在 24-48 小时后才能在 Dashboard 上看到。这对快速迭代的开发节奏来说太慢了——你今天发布的版本，后天才能看到性能数据。

### 替代方案

对于需要更细粒度、更低延迟的线上性能监控，可以考虑以下方案：

- **自建性能数据采集**：通过 `Choreographer.FrameCallback` 采集帧时间、通过 `System.nanoTime()` 标记关键时间点、通过 `ActivityManager.RunningAppProcessInfo` 监控内存状态，将数据批量上报到自建服务端。这就是 §15.5 线上性能监控中介绍的方法
- **APM 平台**：使用第三方 APM（Application Performance Monitoring）平台，如 Matrix（微信开源）、Booster、DoKit 等。这些工具通常提供比 FPM 更细粒度的数据采集和分析能力
- **Google Chrome UX Report (CrUX)**：虽然 CrUX 主要是 Web 性能指标，但 Android 上也可以通过 `WebView` 相关的 API 获取类似的用户体验数据

在实际项目中，通常的做法是：**FPM 作为基础的线上监控（零接入成本），自建或 APM 平台作为深度分析工具**。两者互补，不互斥。

## 在 Perfetto 中的表现

性能测试的数据虽然主要来自 Macrobenchmark 和自定义采集，但 **Perfetto Trace 是验证测试结果的最佳工具**。当你发现某个版本的启动时间退化了 50ms，第一步就是抓一个 Trace 看这 50ms 花在哪里。

在 Perfetto 中验证性能测试数据的方法：

- **启动时间验证**：在 Trace 中定位目标进程的启动时间点（搜索 `proc_start` 或 `ActivityManager: Start proc`），到首帧绘制完成（搜索 `Choreographer#doFrame` 或 `firstDraw`）之间的时间差，应该与 Macrobenchmark 报告的 `timeToInitialDisplay` 基本一致
- **帧率验证**：在 RenderThread track 中检查 `DrawFrame` 切片的耗时分布。正常情况下 60fps 设备的 DrawFrame 应该在 16ms 以内，120fps 设备应该在 8ms 以内。超过阈值的 DrawFrame 就是掉帧
- **内存占用验证**：在 Trace 的 `memtrack` track 或 `Process Stats` 中查看目标进程的内存使用情况，与测试报告中的内存数据做交叉验证

如果在 Trace 中发现的数据与基准测试报告不一致，通常意味着测试环境存在未被控制的变量——比如后台有大量 I/O 活动、系统正在进行 dex2oat 编译等。这时需要回到环境标准化步骤，排查干扰源。

## 与其他机制的关系

性能测试最佳实践不是孤立的，它与本书其他章节有紧密的关联：

- **§14.6 自动化测试工具**：介绍了 Macrobenchmark、Microbenchmark、UI Automator 等具体工具的使用方法。本节侧重的是"怎么用好这些工具"的方法论层面
- **§15.5 线上性能监控**：基准测试是实验室环境下的测量，线上监控是真实用户环境下的测量。两者互补——基线管"回归检测"，线上管"真实体验"
- **§8.3 启动优化策略**：冷启动是最核心的性能指标之一，本节讲怎么可靠地测量启动时间，§8.3 讲怎么优化它
- **§13.2 Trace 抓取**：当基准测试发现性能退化时，需要用 Trace 定位根因。两章配合使用
- **§5.5 Thermal 管控**：理解温控机制才能理解为什么温度控制对测试如此重要

## 常见问题与误区

### "性能测试应该用最高端的设备"

恰恰相反。如果你的目标用户中高端设备只占 20%，那在旗舰机上跑出来的数据对 80% 的用户都没有参考价值。选择测试设备时应该优先覆盖主力用户群的设备档次。

### "一次测试就够了，多跑几次浪费时间"

单次测试的数据没有任何统计意义。一次冷启动 350ms 的数据不能说明你的启动速度就是 350ms——可能是刚好这次 GC 没有触发、CPU 频率刚好最高、缓存刚好命中。至少 10 次采样、取中位数和 P90，才能得到有参考价值的数据。

### "CI 里跑的基准测试和本地跑的不一致，一定是 CI 有问题"

不一定。首先检查 CI 和本地的测试环境差异——设备是否相同、系统版本是否一致、温度条件是否接近。如果环境确认一致但结果仍然不一致，可能是因为 CI 的并行执行导致了额外的资源竞争。CI 基准数据更适合看趋势，而不是看绝对值。

### "性能基线不需要更新"

性能基线不是一成不变的。当 App 引入了重大的新功能（比如全新的首页设计），旧的基线可能就不再适用了。每次大版本发布后，都应该重新建立基线。但要注意：新基线和旧基线之间要有清晰的交接记录，避免"基线漂移"——每次重新建基线都放宽一点标准，几个版本下来标准就形同虚设了。

### "自动化测试可以替代手动性能分析"

自动化基准测试能告诉你"有没有退化"，但不能告诉你"为什么退化"。它是一个"报警器"，不是"诊断仪"。当自动化测试发现回归时，还是需要工程师手动抓 Trace、分析日志、定位根因。自动化和手动分析是互补的，不是替代关系。

## 参考资料

- [Benchmarking in CI | Android Developers](https://developer.android.com/topic/performance/benchmarking/benchmarking-in-ci) — 官方 CI 集成指南
- [Macrobenchmark | Android Developers](https://developer.android.com/topic/performance/benchmarking/macrobenchmark-overview) — Macrobenchmark 使用文档
- [Microbenchmark | Android Developers](https://developer.android.com/topic/performance/benchmarking/microbenchmark-overview) — Microbenchmark 使用文档
- [Baseline Profiles | Android Developers](https://developer.android.com/topic/performance/baselineprofiles) — Baseline Profiles 生成与使用
- [Measure performance | Android Developers](https://developer.android.com/topic/performance) — 性能测量总入口
- AOSP 路径：`frameworks/base/core/java/android/app/Activity.java`（启动时间相关 API）
- AOSP 路径：`frameworks/base/core/java/android/view/Choreographer.java`（帧回调 API）


### 性能分析误区：峰值帧率 vs 稳态帧率
- 来源：https://android-developers.googleblog.com/performance-methodology
- 类型：article
- 摘要：骁龙8 Elite持续负载下30%性能衰减。有意义的指标：30分钟游戏后帧率、99th percentile延迟、冷启动后5分钟内响应。Benchmark应包含热稳定态测试。
- 入库时间：2026-04-08
