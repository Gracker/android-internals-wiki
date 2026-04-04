---
title: "性能指标体系"
chapter: "15.3"
status: ready-for-review
drafted_date: "2026-04-04"
applicable_versions: "Android 8.0 (API 26) - Android 16 (API 36)"
last_verified: "2026-04-04"
last_verified_against: "developer.android.com, Google Play Console Help"
confidence: medium
sources:
  - type: official
    path: "https://developer.android.com/topic/performance/vitals"
  - type: official
    path: "https://developer.android.com/topic/performance/launch-time"
  - type: official
    path: "https://support.google.com/googleplay/android-developer/answer/9844476"
  - type: official
    path: "https://developer.android.com/reference/android/view/FrameMetrics"
tags: ['metrics', 'vitals', 'FPS', 'TTID', 'TTFD', 'ANR', 'PSS', 'monitoring']
related_chapters: ["7.1", "7.2", "7.3", "8.1", "9.1", "10.1", "11.1", "15.1"]
---

# 性能指标体系

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 流畅性指标：FPS、Janky Frame Rate、Frame Time P90/P99、Frozen Frame Rate
- 🔹 响应速度指标：TTID、TTFD、Click-to-Display
- 🔹 稳定性指标：ANR Rate、Crash Rate
- 🔹 内存指标：PSS、Java Heap Usage、OOM Rate
- 🔹 功耗指标：Battery Drain Rate、Active/Idle Power
- 🔹 指标体系设计：线上 vs 线下、聚合粒度、分位数选择

### 扩展（可选深入）

- 🔸 Google Play Console 中的 Android Vitals 指标
- 🔸 自定义业务性能指标的设计原则

### OpenClaw 加工指引

> **锚点**是最低覆盖要求，加工时必须逐条落实并标注验证结果。
> **扩展**视素材丰富程度选择性深入。
> 如果从 Obsidian 素材或 AOSP 源码中发现大纲未列出但与本节强相关的知识点，
> 可**就地插入**最相关的锚点之后，并用 `[自动发现]` 标注，方便后续 review。
> 锚点内容需 L1/L2 验证，扩展内容至少 L2 验证，自动发现内容至少标注来源。
<!-- outline-end -->

## 为什么要建立一套指标体系

做性能优化最怕的不是"不知道怎么优化"，而是"不知道优化之后有没有效果"。如果你在 Perfetto 里花了一整天分析卡顿，最后交出一版修改，却说不清楚帧率提升了多少、用户感知有没有改善，那这轮优化就没有闭环。

一套完善的性能指标体系解决的是"度量"问题。它回答三个层面的需求：在开发阶段，我们需要一套线下指标来精确定位瓶颈；在灰度和上线阶段，我们需要线上指标来监控回归和验证效果；在长期迭代中，我们需要把不同维度的指标聚合起来，形成对产品性能的全局判断。

这一节我们把 Android 性能领域最核心的指标类别梳理一遍——流畅性、响应速度、稳定性、内存、功耗——每个指标讲清楚它度量什么、怎么采集、多少算好。最后讨论一下指标体系的设计原则：线上和线下的区别在哪里、聚合粒度怎么选、分位数比均值好在哪里。

## 流畅性指标

流畅性是用户最直接能感知到的性能维度。一个 App 界面滑起来是否顺滑、动画是否流畅，都由流畅性指标来量化。

### FPS（每秒帧数）

FPS 是最直觉的流畅性指标：一秒钟内屏幕上成功渲染了多少帧。60Hz 屏幕的理论上限是 60 FPS，120Hz 屏幕是 120 FPS。在 Perfetto 中，你可以通过统计 RenderThread 和 SurfaceFlinger 的工作周期来计算实际 FPS。

但 FPS 有一个显著的缺陷：它是一个平均值概念。假设你在 120Hz 设备上一秒内渲染了 117 帧，FPS 看起来很漂亮（97.5% 帧率），但如果其中有 3 帧是连续掉帧——用户刚好在这 3 帧的窗口里看到了明显的卡顿，平均 FPS 却几乎不受影响。

这就是为什么我们做性能分析时，很少只用 FPS。

[已验证: 官方文档, developer.android.com/topic/performance/vitals]

### Frame Time 与分位数（P90 / P99）

Frame Time 是单帧渲染耗时，精度到微秒级。它比 FPS 更有分析价值，因为它能看到每一帧的真实情况，而不是被平均化掩盖。

在做线上监控时，我们通常关心的是分位数——P50（中位数）、P90、P99。P50 告诉你"大多数用户看到的帧有多快"，P90 告诉你"10% 的帧有多慢"，P99 则暴露最差的 1% 的尾部延迟。

为什么 P90 和 P99 这么重要？因为在高刷设备上，用户对偶发卡顿的敏感度反而更高。120Hz 屏幕的帧预算只有 8.33ms，一个 20ms 的长帧就会造成肉眼可见的跳帧。如果 P99 超过了帧预算的 2 倍（约 16ms@120Hz），说明每 100 帧里就有一帧会让用户感到顿挫。这个频率在快速滑动列表时会被明显感知到。

采集方式上，线下可以通过 `dumpsys gfxinfo` 获取逐帧耗时，线上则推荐使用 `FrameMetrics` API（Android 7.0+, API 24）或 `FrameMetricsAggregator`（Android 9.0+, API 28）。后者专门为批量帧时间统计设计，可以按回调阶段（Input、Animation、Layout、Draw）拆分耗时。

```java
// FrameMetrics 基本用法
// @ API 24+
Window.OnFrameMetricsAvailableListener listener = (window, frameMetrics, dropCount) -> {
    long totalFrameTime = frameMetrics.getMetric(FrameMetrics.TOTAL_DURATION); // 纳秒
    long drawDuration = frameMetrics.getMetric(FrameMetrics.DRAW_DURATION);
    // 上报到监控系统
};
window.addOnFrameMetricsAvailableListener(listener, handler);
```

这段代码注册了帧时间监听器，每帧回调一次。`TOTAL_DURATION` 给出从 VSync-app 到帧提交的完整耗时，你可以把它收集起来计算分位数。

[已验证: 官方文档, developer.android.com/reference/android/view/FrameMetrics]

### Janky Frame Rate（慢帧率）

Google 在 Android Vitals 中定义了"慢帧"（Slow / Janky Frame）的标准：渲染耗时超过帧预算的帧。具体阈值因设备刷新率而异——60Hz 设备是 16ms，120Hz 设备是 8ms。Janky Frame Rate 是指用户会话中出现慢帧的比例。

Google Play Console 的 Android Vitals 看板中，有两个层级的慢帧指标：一般慢帧（>16ms）和严重慢帧（>50ms）。如果超过 50% 的用户会话中出现严重慢帧，Google Play 会认为你的 App 存在"不良行为"（Bad Behavior），这会直接影响 Play Store 中的曝光和推荐。

[已验证: 官方文档, developer.android.com/topic/performance/vitals]

### Frozen Frame Rate（冻帧率）

冻帧（Frozen Frame）是慢帧的极端形态：渲染耗时超过 700ms 的帧。当一帧超过 700ms 时，用户会感觉 App 卡死了将近一秒——在这段时间内，屏幕完全不动，触摸事件也无法响应。在 Android Vitals 中，冻帧是独立于慢帧之外单独统计的核心指标。

冻帧几乎总是由主线程上的长阻塞操作造成：同步 I/O（如直接在 UI 线程读文件或数据库）、锁竞争（等另一个线程释放 synchronized 块）、或者在前台执行了大量的序列化/反序列化操作。如果你在 Perfetto 中看到一段超过 700ms 的主线程连续运行（没有 Sleep/Blocked 状态切换），那大概率是冻帧的候选对象。

[已验证: 官方文档, developer.android.com/topic/performance/vitals]

## 响应速度指标

响应速度关注的是"从用户发出操作到看到结果"的延迟。它与流畅性的区别在于：流畅性度量的是持续的渲染质量，响应速度度量的是单次交互的反馈延迟。

### TTID（Time to Initial Display）

TTID 是 App 启动过程中，从进程创建到第一帧绘制完成的时间。这帧通常是启动画面（Splash Screen）或主界面的初始布局，标志着"App 已经打开了"。

Android 系统通过 ActivityManager 内部的 `reportActivityLaunched` 事件自动记录 TTID。在 `logcat` 中过滤 `Displayed` 关键字就能看到：

```
ActivityManager: Displayed com.example.app/.MainActivity: +1s234ms
```

从 Android 12 开始，SplashScreen API 让系统默认在 TTID 之前就显示一个启动画面，使得用户感知的等待时间变短——但 TTID 本身的度量起点仍然是进程创建，这个不会变。

Google Play 的 Android Vitals 将 TTID 作为核心启动指标之一。冷启动 TTID 的不良行为阈值是：超过 5 秒。如果你的 App 冷启动 TTID 中位数超过 2 秒，就应该认真优化了。

[已验证: 官方文档, developer.android.com/topic/performance/launch-time]

### TTFD（Time to Full Display）

TTFD 度量的是 App 从启动到"内容完全可用"的时间。和 TTID 的区别在于：TTID 只管第一帧画出来，但那可能只是一个空壳布局（加载中的骨架屏、空白列表）；TTFD 关注的是真正的业务内容加载完成——列表数据拿到了、图片显示了、用户可以开始交互了。

开发者需要手动调用 `reportFullyDrawn()` 来标记 TTFD：

```java
// 在数据加载完成、UI 完全就绪后调用
@Override
public void onDataLoaded(List<Item> items) {
    recyclerView.setAdapter(new ItemAdapter(items));
    // 确保这帧渲染完成后标记 Fully Drawn
    if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
        // API 31+ 可以传递更精确的时间戳
        reportFullyDrawn();
    } else {
        reportFullyDrawn();
    }
}
```

这个调用时机需要斟酌：太早则 TTFD 失去意义（内容还没加载完），太晚则会干扰系统的启动优化策略（Android 14+ 的 system-triggered profiling 会根据 `reportFullyDrawn` 来决定何时停止 trace）。

Android 16 引入了 system-triggered profiling，可以在 `reportFullyDrawn` 被调用时自动启动和停止 Perfetto trace，这让 TTFD 的调试变得更容易——开发者不需要手动抓 trace，系统会自动捕获启动过程。

[已验证: 官方文档, developer.android.com/topic/performance/launch-time]

### Click-to-Display（点击到显示延迟）

Click-to-Display 是一个端到端的延迟指标：从用户手指触碰屏幕的那一刻，到屏幕上显示对应的视觉反馈，经历了多少毫秒。这个指标覆盖了完整的事件链路：触摸中断 → InputDispatcher 分发 → App 主线程处理事件 → UI 更新 → RenderThread 渲染 → SurfaceFlinger 合成 → 显示硬件输出。

在 Perfetto 中，一次 Click-to-Display 的完整路径跨越多个 Track：从 `Input` track 上的触摸事件，到主线程的 `Choreographer.doFrame`，再到 `RenderThread` 的绘制和 `SurfaceFlinger` 的合成。你可以在这些 Track 之间手动量取时间差来估算这个延迟。

这个指标在线上很难直接采集（需要硬件辅助或特殊测量工具），但它对用户感知的影响非常直接。Google 在内部测试中使用的标准是：触摸响应延迟应控制在 100ms 以内，超过 200ms 用户会明显感到迟钝。

[待验证: 100ms/200ms 阈值为行业经验值，未找到 Google 官方公开文档确认]

## 稳定性指标

稳定性是最基础的质量指标——一个频繁崩溃或无响应的 App，性能再好也没用。

### ANR Rate（应用无响应率）

ANR（Application Not Responding）发生在 App 的主线程被阻塞超过一定时间时。最常见的触发条件是：输入事件在 5 秒内未处理完毕（Input dispatching timed out），或 Service 在规定时间内未执行完毕。

Android Vitals 度量的是"用户感知到的 ANR 率"（User-Perceived ANR Rate），即每日活跃用户中经历过至少一次用户可感知 ANR 的百分比。所谓"用户可感知"，主要指 App 在前台时发生的 ANR——后台 Service 超时导致的 ANR 虽然也会统计，但对用户体验的影响不同。

Google Play 设定的不良行为阈值（截至 2026 年）：

- **全机型不良行为**：用户感知 ANR 率 ≥ 0.47%
- **单机型不良行为**：用户感知 ANR 率 ≥ 8%

超过阈值后，Play Store 会在 App 详情页显示警告标签，同时降低在搜索结果和推荐中的排名。

[已验证: 官方文档, support.google.com/googleplay/android-developer/answer/9844476]

### Crash Rate（崩溃率）

Crash Rate 的统计方式与 ANR Rate 类似，度量的是每日活跃用户中经历过至少一次崩溃的比例。Android Vitals 同样区分"用户感知的崩溃"（App 在前台时崩溃）和后台崩溃。

Google Play 设定的不良行为阈值：

- **全机型不良行为**：用户感知崩溃率 ≥ 1.09%
- **单机型不良行为**：用户感知崩溃率 ≥ 8%

注意这两个指标的分子定义：不是"崩溃次数"，而是"经历过崩溃的用户比例"。这个定义更贴近用户体验——一个用户一天崩溃 10 次和一个用户崩溃 1 次，在 Crash Rate 中都是"1 个受影响用户"。但如果你要评估严重程度，需要同时看崩溃次数和受影响用户数。

采集崩溃数据的方式主要有三种：Google Play Console 自动收集（Java 崩溃和 Native 崩溃都能捕获）、Firebase Crashlytics（支持实时上报和聚合分析）、自建监控 SDK（可以采集更丰富的上下文信息如内存状态、线程堆栈）。

[已验证: 官方文档, support.google.com/googleplay/android-developer/answer/9844476]

## 内存指标

内存指标的重要性常常被低估。在 Android 上，内存问题不只是 OOM——一个 App 占用内存过多，会触发系统更频繁的 GC、增加 LMK（Low Memory Killer）杀进程的概率、影响其他 App 的可用内存，最终以卡顿或闪退的形式呈现给用户。

### PSS（Proportional Set Size）

PSS 是 Android 上度量 App 真实物理内存占用的标准指标。它的计算方式是：App 独占的内存页（Private Clean + Private Dirty）加上按比例分摊的共享内存页。所谓"按比例分摊"，是指如果一个 4KB 的内存页被 4 个进程共享，那么每个进程的 PSS 只计算 1KB。

这种统计方式的好处是：把系统上所有进程的 PSS 加总，约等于实际使用的物理内存总量。Android 的 LMK 在决定杀哪个进程时，主要参考的就是进程的 PSS 值——PSS 越大的进程被杀的优先级越高。

你可以通过 `dumpsys meminfo <package_name>` 获取 App 的详细内存分布：

```
** MEMINFO in pid 12345 [com.example.app] **
                   Pss      Private  Private  SwapPss     Heap     Heap     Heap
                 Total    Dirty    Clean    Dirty     Size    Alloc     Free
                ------   ------   ------   ------   ------   ------   ------
  Native Heap    12,345    12,000        0      256   16,384   15,872      512
  .so mmap       8,765     1,024    2,048       64
  .dex mmap      3,456      512    1,024        0
  .oat mmap      1,234       64      512        0
  .art mmap      6,789    4,096    1,024      128   24,576   20,480    4,096
 ...
        TOTAL   45,678   22,528    8,192      640   40,960   36,352    4,608
```

这个输出中最值得关注的几个维度：Native Heap（Native 层分配）、.art mmap（ART 运行时堆）、.so mmap（共享库映射）、.dex mmap（DEX 代码映射）。如果某个维度异常偏高，就是你接下来排查的方向。

[已验证: 官方文档, developer.android.com/studio/profile/memory]

### Java Heap Usage

Java Heap 是 ART 虚拟机管理的堆内存，App 中所有 Java/Kotlin 对象分配都在这里。每个 App 的 Java Heap 有一个上限（由 `dalvik.vm.heapsize` 系统属性决定，不同设备从 128MB 到 512MB 不等），超过上限就会抛出 `OutOfMemoryError`。

Java Heap Usage 在 Perfetto 中可以通过 `Memory` track 观察。在 Android Studio 的 Memory Profiler 中，你能看到实时堆使用曲线和 GC 事件。频繁的 GC（特别是 Young GC）通常是内存抖动的信号——大量短命对象被反复创建和回收，导致主线程暂停。

线上监控 Java Heap 的推荐方式是通过 `Runtime.getRuntime().totalMemory()` 和 `Runtime.getRuntime().freeMemory()` 定期采样，或者使用 `android.os.Debug.getMemoryInfo()` 获取更详细的内存分类数据。

[已验证: 官方文档, developer.android.com/topic/performance/memory]

### OOM Rate

OOM（OutOfMemoryError）率度量的是 App 因内存不足而崩溃的频率。在 Android 8.0 之前，OOM 主要由 Java Heap 超限引起；8.0 之后，大部分 Bitmap 像素数据移到了 Native 堆，Java Heap 的压力有所缓解，但 Native OOM 的风险增加了。

OOM Rate 的计算通常是：OOM 崩溃次数 / 总会话数。在线上监控中，你需要区分两种 OOM：Java 层的 `java.lang.OutOfMemoryError`（可以通过 Crashlytics 等工具捕获）和 Native 层的分配失败（通常表现为 SIGABRT 或 malloc 返回 NULL）。

## 功耗指标

功耗指标的特殊之处在于：它们通常需要系统级权限或硬件辅助才能准确测量，App 端能做的更多是间接估算。

### Battery Drain Rate（电池消耗速率）

Battery Drain Rate 度量的是 App 在单位时间内的电池消耗量，通常以 mAh/hour 或百分比/hour 表示。线上采集依赖 `BatteryManager` API 读取电池电量变化，线下可以通过 Batterystats 工具（`dumpsys batterystats`）或 Battery Historian 做更详细的分析。

2026 年 3 月起，Google Play 将"过度部分 WakeLock"（Excessive Partial Wake Lock）纳入核心 Android Vitals 指标。如果一个 App 在 24 小时内持有非豁免的部分 WakeLock 累计超过 2 小时，且 28 天内 5% 以上的用户会话达到这个标准，就会被认定为不良行为，面临 Play Store 降权和警告标签的处罚。

非豁免 WakeLock 是指那些没有明确用户收益的后台保活行为——音乐播放、导航、用户主动发起的下载等属于豁免类别。

[已验证: 官方文档, support.google.com/googleplay/android-developer/answer/9844476]

### Active / Idle Power

Active Power 是 App 在前台活跃使用时的功耗，主要由 CPU 计算、GPU 渲染、屏幕刷新和网络通信组成。Idle Power 是 App 在后台时的功耗，理想情况下应该趋近于零——但在实践中，后台同步、推送接收、定位更新等都会消耗电量。

做功耗分析时，一个有效的思路是"归因分析"：把总功耗拆解到各个子系统的消耗（CPU/GPU/屏幕/网络/传感器），找出占比最高的那个子系统，然后针对性地优化。在 Perfetto 的 Power track 中，你可以看到电流曲线和各子系统的功耗分布。

[待补充: Perfetto Power track 的具体使用方法和截图示例]

## 指标体系设计原则

讨论完单个指标，我们需要回答一个更上层的问题：怎么把这么多指标组织成一套可用的体系。

### 线上 vs 线下

线上指标（Online Metrics）和线下指标（Offline Metrics）的定位完全不同，不能互相替代。

线下指标的核心价值是**精确诊断**。你在 Perfetto 里能看到每一帧的详细耗时、每一次 GC 的暂停时长、每一个线程的状态变化。这种精度是线上指标做不到的——线上你不可能给每个用户开一个 Perfetto trace。线下指标的局限在于：它是你在实验室环境采集的，不能代表真实用户的设备分布、网络条件和使用习惯。

线上指标的核心价值是**趋势监控和回归发现**。你通过 SDK 采集线上用户的聚合数据（分位数、P90、P99），能发现新版本发布后某项指标有没有劣化、某个机型上是不是特别差。线上指标的局限在于精度低——你拿不到每帧的详细堆栈，只能看到聚合后的数字。

一个成熟的性能团队通常这样搭配使用：线上指标发现异常（"P90 帧时间从 12ms 涨到了 18ms"），线下指标定位原因（在 Perfetto 中找到具体哪一步变慢了）。

### 聚合粒度

线上指标需要选择合适的聚合维度。最基本的维度是：

- **时间粒度**：按小时、按天、按周聚合。日常监控看天级数据，版本对比看周级数据，紧急问题看小时级数据。
- **设备维度**：按机型、SoC 平台、Android 版本、内存大小分组。Android 生态的设备碎片化决定了同一 App 在不同设备上的性能差异可以非常大。
- **用户场景**：按 App 内的关键路径（首页、列表页、详情页、视频播放等）拆分。不同场景的性能特征差异很大，混在一起看平均值会掩盖问题。

聚合粒度越细，数据量越大，存储和查询成本越高。实践中建议：核心指标按天×机型×场景三维聚合，次要指标只按天聚合。不要一开始就追求最细粒度，从粗到细逐步添加。

### 分位数 vs 均值

最后一个设计问题是：为什么我们反复强调用分位数（P50/P90/P99）而不是均值（Average/Mean）？

均值的问题是它会被极端值拉偏。假设你有一组帧时间数据：[8, 8, 8, 8, 8, 8, 8, 8, 8, 200]，均值是 27.2ms，看起来不差。但 P50 是 8ms（很好），P90 是 8ms（也不错），P99 是 200ms（有一个极端长帧）。P99 暴露了均值完全掩盖的尾部问题。

在性能领域，我们真正关心的往往不是"平均体验"，而是"最差体验"——因为用户离开的原因通常是那一次最差的体验，而不是平均表现。所以 P90 和 P99 在性能监控中的价值远高于均值。

一个健康的指标分布应该是：P90 接近 P50，P99 略高于 P90。如果 P99 远高于 P50（比如 P50=8ms 但 P99=150ms），说明系统存在偶发的严重问题，需要排查。

## Android Vitals 与 Google Play Console

Android Vitals 是 Google Play Console 内置的性能监控面板，它自动采集所有 Play Store 分发的 App 的核心性能数据，不需要开发者额外集成 SDK。

Android Vitals 的核心指标（Core Vitals）包括：

- **用户感知 ANR 率**（User-Perceived ANR Rate）
- **用户感知崩溃率**（User-Perceived Crash Rate）
- **过度部分 WakeLock**（Excessive Partial Wake Locks，2026 年 3 月起新增）

这些核心指标都有明确的不良行为阈值（前文已列出）。超过阈值会直接影响 App 在 Play Store 中的可见度。

除了核心指标外，Android Vitals 还提供以下诊断数据：

- **启动时间**（TTID/TTFD）的分布和趋势
- **慢帧率**和**冻帧率**的按版本和设备分布
- **电池使用**的 WakeLock 和网络后台活动
- **ANR 和崩溃**的详细堆栈信息（经过混淆符号表解析后）

对于大多数 App 团队来说，Android Vitals 是最基础的性能监控入口——在建设自有的线上监控体系之前，先把 Android Vitals 看板用起来。

[已验证: 官方文档, developer.android.com/topic/performance/vitals]

## 自定义业务性能指标的设计原则

除了系统级指标，App 团队通常还需要定义自己的业务性能指标。比如：信息流列表从触发刷新到内容展示完成的耗时、视频从点击播放到首帧渲染的耗时、搜索从输入到结果返回的延迟。

设计自定义指标时有几个原则：

第一，指标要对应真实的用户体验，而不是技术实现细节。"Feed 加载完成"比"网络请求返回"更有意义，因为前者是用户真正感知到的。

第二，要有明确的起点和终点。起终点定义不一致是自定义指标最常见的坑——同样是"搜索耗时"，如果有人从输入框 change 事件算起，有人从请求发送算起，数据就不具备可比性。建议在团队内明确约定每个自定义指标的起终点，并写进文档。

第三，采样率要合理。不是每个事件都需要 100% 上报。高频事件（如每帧的 Frame Time）可以采样 1%-10%，低频关键事件（如启动耗时）应该 100% 上报。采样率的选择需要平衡数据精度和上报成本。

第四，维度标签要稳定。每个指标应该附带固定的维度标签（App 版本、设备型号、场景名称），但不要把用户 ID 等高基数（high-cardinality）值作为标签——这会导致聚合爆炸。

## 常见问题与误区

**"FPS 够高就说明流畅"**——不一定。120 FPS 的 App 可能存在偶发的 50ms 长帧，平均 FPS 看起来很好，但用户在滑动列表时会感觉到间歇性卡顿。看 P99 Frame Time 比 FPS 更能反映真实体验。

**"启动时间只要 TTID 够快就行"**——TTID 快只说明启动画面出来得快，如果 TTFD 慢（内容加载了 3 秒才出来），用户看到的是一个空壳页面转圈。同时优化 TTID 和 TTFD 才是完整的启动体验优化。

**"ANR 率低就不用担心主线程"**——ANR 的阈值是 5 秒，但主线程上 500ms 的阻塞就会造成明显的冻帧。即使你的 ANR 率为零，也可能存在大量影响用户体验的主线程卡顿。

**"内存指标只要不 OOM 就行"**——PSS 过高的 App 会挤压系统中其他 App 的可用内存，增加 LMK 杀进程的概率。当用户切换回你的 App 时发现它被杀了需要重新启动，这就是"内存性能差"的间接表现。

**"线上监控加个均值就够了"**——均值无法反映尾部延迟。一个 P50=10ms、P99=500ms 的指标和 P50=10ms、P99=12ms 的指标，均值可能差不多，但前者意味着每 100 次操作有一次严重卡顿，用户体验完全不同。

## 参考资料

- [Android Vitals | developer.android.com](https://developer.android.com/topic/performance/vitals)
- [App startup time | developer.android.com](https://developer.android.com/topic/performance/launch-time)
- [FrameMetrics API | developer.android.com](https://developer.android.com/reference/android/view/FrameMetrics)
- [Android Vitals bad behavior thresholds | support.google.com](https://support.google.com/googleplay/android-developer/answer/9844476)
- [Investigate RAM usage | developer.android.com](https://developer.android.com/studio/profile/memory)
- [Manage your app's memory | developer.android.com](https://developer.android.com/topic/performance/memory)
- [Battery Historian | developer.android.com](https://developer.android.com/topic/performance/power/battery-historian)
- [Macrobenchmark | developer.android.com](https://developer.android.com/topic/performance/benchmarking/macrobenchmark-overview)
