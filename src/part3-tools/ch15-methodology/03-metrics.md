---
title: "性能指标体系"
chapter: "15.3"
status: finalized
drafted_date: "2026-04-04"
applicable_versions: "Android 8.0 (API 26) - Android 16 (API 36)"
last_verified: "2026-04-25"
last_verified_against: "developer.android.com/topic/performance/vitals/render, FrameMetrics.DEADLINE, Macrobenchmark FrameTimingMetric, ApplicationExitInfo, lmkd 官方文档"
confidence: medium
sources:
  - type: official
    path: "https://developer.android.com/topic/performance/vitals"
  - type: official
    path: "https://developer.android.com/topic/performance/vitals/render"
  - type: official
    path: "https://developer.android.com/topic/performance/launch-time"
  - type: official
    path: "https://support.google.com/googleplay/android-developer/answer/9844476"
  - type: official
    path: "https://developer.android.com/reference/android/view/FrameMetrics"
  - type: official
    path: "https://developer.android.com/reference/androidx/core/app/FrameMetricsAggregator"
  - type: official
    path: "https://developer.android.com/reference/android/os/ProfilingManager"
  - type: official
    path: "https://developer.android.com/reference/android/view/FrameMetrics#DEADLINE"
  - type: official
    path: "https://developer.android.com/reference/androidx/benchmark/macro/FrameTimingMetric"
  - type: official
    path: "https://developer.android.com/reference/android/app/ApplicationExitInfo"
  - type: official
    path: "https://source.android.com/docs/core/perf/lmkd"
tags:
  - android
  - research
pipeline_stage: ready-to-publish
task6_state: "reviewed"
task9_state: reviewed
task9_result: pass-tech-review
task9_reviewed_date: "2026-04-26"
task9_reviewed_by: openclaw-task9
last_task9_at: "2026-04-26T23:27:38+08:00"
task2b_state: fixed
task2b_result: fixed
reviewed_by: "openclaw-task6"
reviewed_date: "2026-04-25"
task6_result: "pass-light-edit"
last_task6_audit: "2026-05-20"
repaired_date: "2026-04-25"
repaired_by: "openclaw-task2b"
last_task2b_at: "2026-04-25T08:51:01+08:00"
section: "15.3"
related_chapters: ['7.1', '7.2', '7.3', '8.1', '8.2', '9.1', '10.1', '11.1', '15.5', '15.9', '15.10']
review_round: 5
review_notes_5: "2026-04-25 task6 re-review (round 5): pass-light-edit. L1: 1 banned-word cleanup in 03-metrics; AI句式 3→1 in 03-metrics. 01-rendering-overview and 05-leakcanary clean. No B-class issues across all 3 chapters."
last_task9_audit: '2026-05-21'
last_task9_audit_at: '2026-05-21T01:46:24+08:00'
last_task9_audit_log: 'logs/deep-review/2026-05-21-01-audit.md'
---


# 性能指标体系

<!-- outline-start -->
## 本节要点大纲

### 锚点(必须覆盖)

- 🔹 流畅性指标:FPS、Janky Frame Rate、Frame Time P90/P99、Frozen Frame Rate
- 🔹 响应速度指标:TTID、TTFD、Click-to-Display
- 🔹 稳定性指标:ANR Rate、Crash Rate
- 🔹 内存指标:PSS、Java Heap Usage、OOM Rate
- 🔹 功耗指标:Battery Drain Rate、Active/Idle Power
- 🔹 指标体系设计:线上 vs 线下、聚合粒度、分位数选择

### 扩展(可选深入)

- 🔸 Google Play Console 中的 Android Vitals 指标
- 🔸 自定义业务性能指标的设计原则

### OpenClaw 加工指引

> **锚点**是最低覆盖要求,加工时必须逐条落实并标注验证结果。
> **扩展**视素材丰富程度选择性深入。
> 如果从 Obsidian 素材或 AOSP 源码中发现大纲未列出但与本节强相关的知识点,
> 可**就地插入**最相关的锚点之后,并用 `[自动发现]` 标注,方便后续 review。
> 锚点内容需 L1/L2 验证,扩展内容至少 L2 验证,自动发现内容至少标注来源。
<!-- outline-end -->

## 为什么要先讲指标

性能优化最容易掉进一个陷阱:花了很多时间分析和修改,最后却说不清到底好没好。

如果一轮优化结束后，只能说"感觉顺了一点""看起来没那么卡了"，那这轮工作还没有完成验证。性能问题要回答的是"比之前好多少""影响了多少人""值得不值得优先修"——这些判断都离不开指标。

所以这一节先把"什么数字值得长期盯、什么数字适合拿来诊断、什么数字适合做发布门禁"讲清楚。

## 指标体系不是"多几个数字",而是决策接口

指标体系的价值在于它能不能支持决策。一个好的指标至少要回答下面三个问题中的一个:

- 现在有没有问题?
- 这个问题影响面多大?
- 它更像哪一类问题,应该先找谁?

如果一个指标既不能决定优先级,也不能帮助归因,那它大概率只是"好看但不好用"。

## 流畅性指标

流畅性是用户最先感知到的性能维度。界面顺不顺,动画跟不跟手,列表是不是一滑就顿,最后都要落到流畅性指标上。

### FPS(每秒帧数)

FPS 是最直觉的流畅性指标:一秒钟内屏幕上成功渲染了多少帧。60Hz 屏幕的理论上限是 60 FPS,120Hz 屏幕是 120 FPS。在 Perfetto 中,你可以通过统计 RenderThread 和 SurfaceFlinger 的工作周期来计算实际 FPS。

但 FPS 的问题也很明显:它是平均值。平均值看起来漂亮,不代表体验稳定。

这就是为什么我们做性能分析时,很少只用 FPS。

FPS 更像展示指标,不太适合做治理主指标。治理时更有价值的,通常是帧时间分位数、jank rate 和 frozen frame rate 这类更能反映尾部体验的指标。

[已验证: 官方文档, developer.android.com/topic/performance/vitals/render]

### Frame Time 与分位数(P90 / P99)

Frame Time 是单帧渲染耗时。它比 FPS 更有分析价值,因为它保留了"每一帧到底花了多久"这件事,而不是把一切都摊平。

在做线上监控时,我们通常关心的是分位数--P50(中位数)、P90、P99。P50 告诉你"大多数用户看到的帧有多快",P90 告诉你"10% 的帧有多慢",P99 则暴露最差的 1% 的尾部延迟。

为什么 P90 和 P99 这么重要?因为在高刷设备上,用户对偶发卡顿的敏感度反而更高。120Hz 屏幕的帧预算只有 8.33ms,一个 20ms 的长帧就会造成肉眼可见的跳帧。如果 P99 超过了帧预算的 2 倍(约 16ms@120Hz),说明每 100 帧里就有一帧会让用户感到顿挫。这个频率在快速滑动列表时会被明显感知到。

采集方式上,线下可以通过 `dumpsys gfxinfo` 获取逐帧耗时,线上则推荐使用 `FrameMetrics` API(Android 7.0+, API 24)或 AndroidX 的 `FrameMetricsAggregator`。后者底层仍然依赖 `FrameMetrics`,可用范围同样是 API 24+,但更适合做批量聚合,可以按 Input、Animation、Layout、Draw 等阶段拆分耗时。

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

这段代码注册了帧时间监听器,每帧回调一次。`TOTAL_DURATION` 给出从 VSync-app 到帧提交的完整耗时,你可以把它收集起来计算分位数。

[已验证: 官方文档, developer.android.com/reference/android/view/FrameMetrics; developer.android.com/reference/androidx/core/app/FrameMetricsAggregator]

这里有一个常见误区:直接把所有帧混在一起算全局 P90。更稳的做法是至少按页面 / 场景分桶,再计算分位数。否则首页、详情页、播放页、后台恢复全混在一起,结论很容易失真。

### Janky Frame Rate(慢帧率)

Google 在 Android Vitals 中把 slow rendering 定义为单帧渲染时间落在 16ms 到 700ms 之间,700ms 以上则单独记为 frozen frame。这里的 16ms 是 Vitals 的统一口径,不会因为设备是 90Hz 或 120Hz 就改成 11ms / 8ms。`Janky Frame Rate` 更适合描述"超过当前刷新率预算的帧比例",但在看 Play Console 时,最好直接按 slow rendering 和 frozen frames 两套指标理解。

高刷设备的帧预算仍然要单独看。90Hz 的预算约 11.1ms,120Hz 约 8.3ms,这些阈值适合做线下 trace 和机型专项诊断;如果讨论的是游戏 slow sessions 或高刷机型掉帧,就单列一段,不要把它和 Android Vitals 的定义混在一起。

[已验证: 官方文档, developer.android.com/topic/performance/vitals/render]

从治理角度看,`Janky Frame Rate` 更像平台监控指标,`Frame Time P90/P99` 更像工程诊断指标。前者便于横向比较版本和机型,后者更适合回到具体页面或 trace 做深入分析。

### Frame Overrun(Deadline 超限)

在 Android 12(API 31)之后,帧诊断可以从"耗时有没有超过固定 16ms"前进到"这一帧有没有错过系统给它的 deadline"。`FrameMetrics.DEADLINE` 给出本帧应完成的截止时间,`TOTAL_DURATION` 给出实际耗时。二者相减得到 overrun:正值表示帧晚于 deadline,负值表示还有余量。

这个口径更适合高刷和可变刷新率设备。120Hz 的单帧预算约 8.3ms,一帧耗时 10ms 时仍低于 Android Vitals 的 16ms slow rendering 口径,但已经可能错过本轮刷新窗口。线下门禁和 Macrobenchmark 更适合看 `frameOverrunMs`,Play Console 报表仍按 Android Vitals 的 slow / frozen frames 口径解释。

Macrobenchmark 的 `FrameTimingMetric` 会同时输出两类信号:

- `frameDurationCpuMs`:App 侧 UI Thread 与 RenderThread 为单帧消耗的 CPU 时间,适合判断 CPU 侧工作是否过重。
- `frameOverrunMs`:帧完成时间相对 deadline 的偏移,正值说明 missed deadline,负值说明在预算内完成。API 31+ 上这个指标更贴近高刷和 VRR 场景。

用这组指标做门禁时,不要只写"P99 小于 16ms"。更稳的写法是按场景和刷新率分开设阈值:60Hz 先看 Vitals slow frame 口径,90Hz / 120Hz 专项再看 `frameOverrunMs` 的 P90/P99 和正值占比。

[已验证: FrameMetrics.DEADLINE; Macrobenchmark FrameTimingMetric]

### Frozen Frame Rate(冻帧率)

冻帧(Frozen Frame)是慢帧的极端形态:渲染耗时超过 700ms 的帧。当一帧超过 700ms 时,用户会感觉 App 卡死了将近一秒--在这段时间内,屏幕完全不动,触摸事件也无法响应。在 Android Vitals 中,冻帧是独立于慢帧之外单独统计的核心指标。

冻帧几乎总是由主线程上的长阻塞操作造成:同步 I/O(如直接在 UI 线程读文件或数据库)、锁竞争(等另一个线程释放 synchronized 块)、或者在前台执行了大量的序列化/反序列化操作。如果你在 Perfetto 中看到一段超过 700ms 的主线程连续运行(没有 Sleep/Blocked 状态切换),那大概率是冻帧的候选对象。

[已验证: 官方文档, developer.android.com/topic/performance/vitals]

这类指标的治理价值通常比平均 FPS 更高,因为它更接近"用户真的会抱怨"的那部分体验。

## 响应速度指标

响应速度关注的是"从用户发出操作到看到结果"的延迟。它和流畅性的区别在于观察窗口不同:流畅性看的是持续渲染,响应速度看的是单次反馈。

### TTID(Time to Initial Display)

TTID 是 App 启动过程中,从进程创建到第一帧绘制完成的时间。这帧通常是启动画面(Splash Screen)或主界面的初始布局,标志着"App 已经打开了"。

Android 系统通过 ActivityManager 内部的 `reportActivityLaunched` 事件自动记录 TTID。在 `logcat` 中过滤 `Displayed` 关键字就能看到:

```
ActivityManager: Displayed com.example.app/.MainActivity: +1s234ms
```

从 Android 12 开始,SplashScreen API 让系统默认在 TTID 之前就显示一个启动画面,使得用户感知的等待时间变短--但 TTID 本身的度量起点仍然是进程创建,这个不会变。

Google Play 的 Android Vitals 将 TTID 作为核心启动指标之一。冷启动 TTID 的不良行为阈值是:超过 5 秒。如果你的 App 冷启动 TTID 中位数超过 2 秒,就应该认真优化了。

[已验证: 官方文档, developer.android.com/topic/performance/launch-time]

### TTFD(Time to Full Display)

TTFD 度量的是 App 从启动到"内容完全可用"的时间。和 TTID 的区别在于:TTID 只管第一帧画出来,但那可能只是一个空壳布局(加载中的骨架屏、空白列表);TTFD 关注的是完整业务内容加载完成--列表数据拿到了、图片显示了、用户可以开始交互了。

开发者需要手动调用 `reportFullyDrawn()` 来标记 TTFD:

```java
// 在数据加载完成、UI 完全就绪后调用
@Override
public void onDataLoaded(List<Item> items) {
    recyclerView.setAdapter(new ItemAdapter(items));
    // 数据就绪后立即标记 Fully Drawn
    reportFullyDrawn();
}
```

这个调用时机需要斟酌:太早则 TTFD 失去意义(内容还没加载完),太晚则会把首屏问题掩盖掉。TTFD 本身是启动指标,和是否抓 trace 是两回事。

Android 16 的 system-triggered profiling 建立在 `ProfilingManager` 之上。应用可以注册 `TRIGGER_TYPE_APP_FULLY_DRAWN` 这类触发器,让系统在 `reportFullyDrawn()` 发生时自动收集一段 Perfetto profile。它适合调试启动问题,但不改变 TTID / TTFD 的定义,也不应该拿来充当启动指标的证据来源。

[已验证: 官方文档, developer.android.com/topic/performance/launch-time; developer.android.com/reference/android/os/ProfilingManager]

TTID 和 TTFD 的治理分工也应分开:

- **TTID** 更适合看"框架、初始化、首帧渲染"这段问题
- **TTFD** 更适合看"首屏数据、可交互时机、骨架屏停留时间"这段问题

如果把二者混成一个"启动时长",大概率会丢失很多定位价值。

### Click-to-Display(点击到显示延迟)

Click-to-Display 是一个端到端的延迟指标:从用户手指触碰屏幕的那一刻,到屏幕上显示对应的视觉反馈,经历了多少毫秒。这个指标覆盖了完整的事件路径:触摸中断 → InputDispatcher 分发 → App 主线程处理事件 → UI 更新 → RenderThread 渲染 → SurfaceFlinger 合成 → 显示硬件输出。

在 Perfetto 中,一次 Click-to-Display 的完整路径跨越多个 Track:从 `Input` track 上的触摸事件,到主线程的 `Choreographer.doFrame`,再到 `RenderThread` 的绘制和 `SurfaceFlinger` 的合成。你可以在这些 Track 之间手动量取时间差来估算这个延迟。

这个指标在线上很难直接采集(需要硬件辅助或特殊测量工具),但它对用户感知的影响非常直接。Google 在内部测试中使用的标准是:触摸响应延迟应控制在 100ms 以内,超过 200ms 用户会明显感到迟钝。

[待验证: 100ms/200ms 阈值为行业经验值,未找到 Google 官方公开文档确认]

## 稳定性指标

稳定性是最基础的质量指标。一个频繁崩溃或无响应的 App,性能再好也没用。

这也是为什么很多团队在绩效或版本门禁里,会把 crash / ANR 作为硬性红线,而把流畅性和启动作为持续优化目标。

### ANR Rate(应用无响应率)

ANR(Application Not Responding)发生在 App 的主线程被阻塞超过一定时间时。最常见的触发条件是:输入事件在 5 秒内未处理完毕(Input dispatching timed out),或 Service 在规定时间内未执行完毕。

Android Vitals 度量的是"用户感知到的 ANR 率"(User-Perceived ANR Rate),即每日活跃用户中经历过至少一次用户可感知 ANR 的百分比。所谓"用户可感知",主要指 App 在前台时发生的 ANR--后台 Service 超时导致的 ANR 虽然也会统计,但对用户体验的影响不同。

Google Play 设定的不良行为阈值(截至 2026 年):

- **全机型不良行为**:用户感知 ANR 率 ≥ 0.47%
- **单机型不良行为**:用户感知 ANR 率 ≥ 8%

超过阈值后,Play Store 会在 App 详情页显示警告标签,同时降低在搜索结果和推荐中的排名。

[已验证: 官方文档, support.google.com/googleplay/android-developer/answer/9844476]

线上治理时,不要只盯总 ANR rate,还应看:

- user-perceived ANR rate
- 单机型 ANR rate
- 前台 / 后台分布
- 版本回归趋势

### Crash Rate(崩溃率)

Crash Rate 的统计方式与 ANR Rate 类似,度量的是每日活跃用户中经历过至少一次崩溃的比例。Android Vitals 同样区分"用户感知的崩溃"(App 在前台时崩溃)和后台崩溃。

Google Play 设定的不良行为阈值:

- **全机型不良行为**:用户感知崩溃率 ≥ 1.09%
- **单机型不良行为**:用户感知崩溃率 ≥ 8%

注意这两个指标的分子定义:崩溃次数不等于受影响用户比例(前者按次数计,后者按会话占比计)。这个定义更贴近用户体验--一个用户一天崩溃 10 次和一个用户崩溃 1 次,在 Crash Rate 中都是"1 个受影响用户"。但如果你要评估严重程度,需要同时看崩溃次数和受影响用户数。

采集崩溃数据的方式主要有三种:Google Play Console 自动收集(Java 崩溃和 Native 崩溃都能捕获)、Firebase Crashlytics(支持实时上报和聚合分析)、自建监控 SDK(可以采集更丰富的上下文信息如内存状态、线程堆栈)。

[已验证: 官方文档, support.google.com/googleplay/android-developer/answer/9844476]

Crash rate 和 ANR rate 的治理方法也不同。Crash 更适合按错误簇、版本、堆栈聚类;ANR 更依赖线程状态、等待链路和系统负载背景。

### 进程退出原因分析(ApplicationExitInfo)

Crash / ANR 只回答"有没有失败",`ApplicationExitInfo` 回答进程为什么退出。Android 11(API 30)开始,`ActivityManager.getHistoricalProcessExitReasons()` 可以读取系统保存的进程退出记录,用来区分 crash、ANR、LMK、用户或系统主动结束进程。

这段代码展示采集入口,主要看 `reason`、退出前内存采样和 trace 取法:

```kotlin
val activityManager = context.getSystemService(ActivityManager::class.java)
val exits = activityManager.getHistoricalProcessExitReasons(
    context.packageName,
    0, // 0 means all pids for this package.
    20
)

for (exit in exits) {
    when (exit.reason) {
        ApplicationExitInfo.REASON_LOW_MEMORY -> handleLmk(exit.getRss(), exit.getPss())
        ApplicationExitInfo.REASON_ANR -> exit.traceInputStream?.use(::saveAnrTrace)
        ApplicationExitInfo.REASON_CRASH,
        ApplicationExitInfo.REASON_CRASH_NATIVE -> handleCrashExit(exit)
    }
}
```

`REASON_LOW_MEMORY` 用来把 LMK 与普通 crash 分开。设备是否支持低内存杀进程报告,要通过 `ActivityManager.isLowMemoryKillReportSupported()` 判断;不支持的设备可能只给出 `REASON_SIGNALED` 和 `SIGKILL` 状态。`getTraceInputStream()` 可用于读取 ANR trace 或 native crash tombstone,`getRss()` / `getPss()` 是系统最近一次内存采样,不等于进程死亡瞬间的精确值。

把这个指标放进稳定性看板后,Crash Rate、ANR Rate 和"系统杀进程后用户回到 App 看到重启"的问题才能分开治理。

[已验证: ActivityManager.getHistoricalProcessExitReasons; ApplicationExitInfo]

## 内存指标

内存指标的重要性常常被低估。在 Android 上,内存问题不只是 OOM--一个 App 占用内存过多,会触发系统更频繁的 GC、增加 LMK(Low Memory Killer)杀进程的概率、影响其他 App 的可用内存,最终以卡顿或闪退的形式呈现给用户。

所以内存指标最容易出现的误区,就是"只在 OOM 时才看"。很多性能差评在发生 OOM 之前很久就已经开始了。

### PSS(Proportional Set Size)

PSS 是 Android 上度量 App 真实物理内存占用的标准指标。它的计算方式是:App 独占的内存页(Private Clean + Private Dirty)加上按比例分摊的共享内存页。所谓"按比例分摊",是指如果一个 4KB 的内存页被 4 个进程共享,那么每个进程的 PSS 只计算 1KB。

这种统计方式的好处是:把系统上所有进程的 PSS 加总,约等于实际使用的物理内存总量。PSS 适合做进程占用归因,但不要把它写成 lmkd 的杀进程优先级。现代 lmkd 先由 PSI / vmpressure 等信号判断内存压力,再用 `oom_score_adj` 限定可杀进程范围;具体目标还受 `ro.lmk.kill_heaviest_task` 等策略影响。PSS / RSS 能帮助估算回收收益,不是单独的优先级规则。

你可以通过 `dumpsys meminfo <package_name>` 获取 App 的详细内存分布:

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

这个输出中最值得关注的几个维度:Native Heap(Native 层分配)、.art mmap(ART 运行时堆)、.so mmap(共享库映射)、.dex mmap(DEX 代码映射)。如果某个维度异常偏高,就是你接下来排查的方向。

[已验证: 官方文档, developer.android.com/studio/profile/memory]

从线上治理角度,PSS 更适合作为"系统压力代理指标",而 Java Heap Usage 更适合作为"应用内部堆行为指标"。二者不要混用。

### PSS 与 RSS 的分工

PSS 和 RSS 都在描述内存占用,但统计口径不同。PSS 会把共享页按进程数量分摊,适合回答"这个 App 应该承担多少物理内存成本"。RSS 统计进程当前驻留在内存中的页,包含共享页的完整大小,适合观察 resident 内存增长、瞬时抖动和内核侧回收压力。

| 维度 | PSS | RSS |
|---|---|---|
| 统计口径 | 独占页 + 按比例分摊的共享页 | 进程 resident 页总量,共享页不分摊 |
| 适合用途 | 线上内存占用归因、跨进程汇总、发布门禁 | Perfetto / kernel 侧趋势、瞬时增长、LMK 前后对照 |
| 常见入口 | `dumpsys meminfo`、`Debug.MemoryInfo`、Android Studio Profiler | Perfetto `rss_stat`、`/proc/<pid>/status`、`ApplicationExitInfo.getRss()` |

Perfetto 里看到 `rss_stat` 抬升时,不要直接拿它和 PSS 门禁阈值对比。更稳的做法是:RSS 用来定位哪个时间段 resident 内存增长,PSS 用来评估该场景最终给系统带来的占用成本。

[已验证: Perfetto rss_stat; ApplicationExitInfo.getRss; source.android.com/docs/core/perf/lmkd]

### Java Heap Usage

Java Heap 是 ART 虚拟机管理的堆内存,App 中所有 Java/Kotlin 对象分配都在这里。每个 App 的 Java Heap 有一个上限(由 `dalvik.vm.heapsize` 系统属性决定,不同设备从 128MB 到 512MB 不等),超过上限就会抛出 `OutOfMemoryError`。

Java Heap Usage 在 Perfetto 中可以通过 `Memory` track 观察。在 Android Studio 的 Memory Profiler 中,你能看到实时堆使用曲线和 GC 事件。频繁的 GC(特别是 Young GC)通常是内存抖动的信号--大量短命对象被反复创建和回收,导致主线程暂停。

线上监控 Java Heap 的推荐方式是通过 `Runtime.getRuntime().totalMemory()` 和 `Runtime.getRuntime().freeMemory()` 定期采样,或者使用 `android.os.Debug.getMemoryInfo()` 获取更详细的内存分类数据。

[已验证: 官方文档, developer.android.com/topic/performance/memory]

实际使用时,Java Heap 更适合做趋势观察,而不是做绝对门禁。因为它太容易受场景、设备和采样点影响。

### OOM Rate

OOM(OutOfMemoryError)率度量的是 App 因内存不足而崩溃的频率。在 Android 8.0 之前,OOM 主要由 Java Heap 超限引起;8.0 之后,大部分 Bitmap 像素数据移到了 Native 堆,Java Heap 的压力有所缓解,但 Native OOM 的风险增加了。

OOM Rate 的计算通常是:OOM 崩溃次数 / 总会话数。在线上监控中,你需要区分两种 OOM:Java 层的 `java.lang.OutOfMemoryError`(可以通过 Crashlytics 等工具捕获)和 Native 层的分配失败(通常表现为 SIGABRT 或 malloc 返回 NULL)。

## 功耗指标

功耗指标的特殊之处在于:它们通常需要系统级权限或硬件辅助才能准确测量,App 端能做的更多是间接估算。

### Battery Drain Rate(电池消耗速率)

Battery Drain Rate 度量的是 App 在单位时间内的电池消耗量,通常以 mAh/hour 或百分比/hour 表示。线上采集依赖 `BatteryManager` API 读取电池电量变化,线下可以通过 Batterystats 工具(`dumpsys batterystats`)或 Battery Historian 做更详细的分析。

2026 年 3 月起,Google Play 将"过度部分 WakeLock"(Excessive Partial Wake Lock)纳入核心 Android Vitals 指标。如果一个 App 在 24 小时内持有非豁免的部分 WakeLock 累计超过 2 小时,且 28 天内 5% 以上的用户会话达到这个标准,就会被认定为不良行为,面临 Play Store 降权和警告标签的处罚。

非豁免 WakeLock 是指那些没有明确用户收益的后台保活行为--音乐播放、导航、用户主动发起的下载等属于豁免类别。

[已验证: 官方文档, support.google.com/googleplay/android-developer/answer/9844476]

### Active / Idle Power

Active Power 是 App 在前台活跃使用时的功耗,主要由 CPU 计算、GPU 渲染、屏幕刷新和网络通信组成。Idle Power 是 App 在后台时的功耗,理想情况下应该趋近于零--但在实践中,后台同步、推送接收、定位更新等都会消耗电量。

做功耗分析时,一个有效的思路是"归因分析":把总功耗拆解到各个子系统的消耗(CPU/GPU/屏幕/网络/传感器),找出占比最高的那个子系统,然后针对性地优化。Perfetto 的 Power track 提供了各电源轨的电流曲线和子系统功耗分布。

在 Perfetto 中观察功耗数据,主要使用以下 Track:

- **Power Rails track**:显示各电源轨(如 VDD_CPU、VDD_GPU、VDD_DDR)的实时电流和电压数据,单位为 mW。通过它可以定位功耗峰值对应的子系统。
- **Battery track**:显示电池电量和充放电状态的变化曲线。
- **CPU Frequency track**:与 Power track 对照查看,可以确认功耗上升是否对应 CPU 频率提升。
- **Energy Consumer track**(Android 12+):按子系统(CPU cluster、Display、GPU、Radio 等)拆分能量消耗,直接给出各子系统的功耗占比。

使用方法:在 Perfetto UI 中搜索 `power` 或 `energy`,即可找到相关 Track。将功耗曲线与 CPU/GPU 活动时间对齐,就能看到哪个子系统在什么时间段消耗了最多电量。

[待补充: Perfetto Power track 截图示例]

## 指标体系设计原则

讨论完单个指标,我们需要回答一个更上层的问题:怎么把这么多指标组织成一套可用的体系。

### 线上 vs 线下

线上指标(Online Metrics)和线下指标(Offline Metrics)的定位完全不同,不能互相替代。

线下指标的核心价值是**精确诊断**。你在 Perfetto 里能看到每一帧的详细耗时、每一次 GC 的暂停时长、每一个线程的状态变化。这种精度是线上指标做不到的--线上你不可能给每个用户开一个 Perfetto trace。线下指标的局限在于:它是你在实验室环境采集的,不能代表真实用户的设备分布、网络条件和使用习惯。

线上指标的核心价值是**趋势监控和回归发现**。你通过 SDK 采集线上用户的聚合数据(分位数、P90、P99),能发现新版本发布后某项指标有没有劣化、某个机型上是不是特别差。线上指标的局限在于精度低--你拿不到每帧的详细堆栈,只能看到聚合后的数字。

一个成熟的性能团队通常这样搭配使用:线上指标发现异常("P90 帧时间从 12ms 涨到了 18ms"),线下指标定位原因(在 Perfetto 中找到具体哪一步变慢了)。

### 聚合粒度

线上指标需要选择合适的聚合维度。最基本的维度是:

- **时间粒度**:按小时、按天、按周聚合。日常监控看天级数据,版本对比看周级数据,紧急问题看小时级数据。
- **设备维度**:按机型、SoC 平台、Android 版本、内存大小分组。Android 生态的设备碎片化决定了同一 App 在不同设备上的性能差异可以非常大。
- **用户场景**:按 App 内的关键路径(首页、列表页、详情页、视频播放等)拆分。不同场景的性能特征差异很大,混在一起看平均值会掩盖问题。

聚合粒度越细,数据量越大,存储和查询成本越高。实践中建议:核心指标按天×机型×场景三维聚合,次要指标只按天聚合。不要一开始就追求最细粒度,从粗到细逐步添加。

### 分位数 vs 均值

还有一个重要问题:为什么我们反复强调用分位数(P50/P90/P99)而不是均值(Average/Mean)?

均值的问题在于它会被极端值拉偏。假设你有一组帧时间数据:[8, 8, 8, 8, 8, 8, 8, 8, 8, 200],均值是 27.2ms,看起来不差。但 P50 是 8ms(很好),P90 是 8ms(也不错),P99 是 200ms(有一个极端长帧)。P99 暴露了均值完全掩盖的尾部问题。

在性能领域,更该关注的是最差体验,而非平均体验--因为用户离开的原因通常是那一次最差的体验,而不是平均表现。所以 P90 和 P99 在性能监控中的价值远高于均值。

一个健康的指标分布应该是:P90 接近 P50,P99 略高于 P90。如果 P99 远高于 P50(比如 P50=8ms 但 P99=150ms),说明系统存在偶发的严重问题,需要排查。

## 线上 vs 线下:不要用一套指标打天下

同一个名字的指标,在线上和线下的职责经常不同:

| 指标 | 线下更关注 | 线上更关注 |
|---|---|---|
| Frame Time | 具体帧、具体阶段、具体 trace | P90/P99、机型差异、版本回归 |
| TTID / TTFD | 单次启动链路和阶段耗时 | 中位数、P95、冷温热分布 |
| ANR / Crash | 复现条件和线程状态 | 受影响用户比例、机型 / 版本趋势 |
| PSS / Java Heap | 场景峰值和增长曲线 | 分布、异常版本、设备聚类 |

如果直接把线下单次结果当成线上结论,或把线上聚合指标拿来替代线下分析,都会出偏差。

## Android Vitals 与 Google Play Console

Android Vitals 是 Google Play Console 内置的性能监控面板,它自动采集所有 Play Store 分发的 App 的核心性能数据,不需要开发者额外集成 SDK。

Android Vitals 的核心指标(Core Vitals)包括:

- **用户感知 ANR 率**(User-Perceived ANR Rate)
- **用户感知崩溃率**(User-Perceived Crash Rate)
- **过度部分 WakeLock**(Excessive Partial Wake Locks,2026 年 3 月起新增)

这些核心指标都有明确的不良行为阈值(前文已列出)。超过阈值会直接影响 App 在 Play Store 中的可见度。

除了核心指标外,Android Vitals 还提供以下诊断数据:

- **启动时间**(TTID/TTFD)的分布和趋势
- **慢帧率**和**冻帧率**的按版本和设备分布
- **电池使用**的 WakeLock 和网络后台活动
- **ANR 和崩溃**的详细堆栈信息(经过混淆符号表解析后)

对于大多数 App 团队来说,Android Vitals 是最基础的性能监控入口--在建设自有的线上监控体系之前,先把 Android Vitals 看板用起来。

[已验证: 官方文档, developer.android.com/topic/performance/vitals]

## 一个更可执行的指标分层

比较稳的做法,是把指标分成三层:

### 1. 门禁指标

- 启动预算
- 核心场景 frame time / jank 阈值
- Crash / ANR 红线

### 2. 诊断指标

- 分阶段 frame metrics
- 启动子阶段耗时
- 内存维度拆解
- trace / stack / exit reason

### 3. 治理指标

- 版本趋势
- 机型聚类
- 页面 / 场景榜单
- 回归是否修复

当指标被这样分层后,团队就不容易再问"到底应该看哪个数",而是先问"我现在是在做门禁、诊断,还是治理"。

## 自定义业务性能指标的设计原则

除了系统级指标,App 团队通常还需要定义自己的业务性能指标。比如:信息流列表从触发刷新到内容展示完成的耗时、视频从点击播放到首帧渲染的耗时、搜索从输入到结果返回的延迟。

设计自定义指标时有几个原则:

第一,指标要对应真实的用户体验,而不是技术实现细节。"Feed 加载完成"比"网络请求返回"更有意义,因为前者是用户真正感知到的。

第二,要有明确的起点和终点。起终点定义不一致是自定义指标最常见的坑--同样是"搜索耗时",如果有人从输入框 change 事件算起,有人从请求发送算起,数据就不具备可比性。建议在团队内明确约定每个自定义指标的起终点,并写进文档。

第三,采样率要合理。不是每个事件都需要 100% 上报。高频事件(如每帧的 Frame Time)可以采样 1%-10%,低频关键事件(如启动耗时)应该 100% 上报。采样率的选择需要平衡数据精度和上报成本。

第四,维度标签要稳定。每个指标应该附带固定的维度标签(App 版本、设备型号、场景名称),但不要把用户 ID 等高基数(high-cardinality)值作为标签--这会导致聚合爆炸。

## 常见问题与误区

**"FPS 够高就说明流畅"**--不一定。120 FPS 的 App 可能存在偶发的 50ms 长帧,平均 FPS 看起来很好,但用户在滑动列表时会感觉到间歇性卡顿。看 P99 Frame Time 比 FPS 更能反映真实体验。

**"启动时间只要 TTID 够快就行"**--TTID 快只说明启动画面出来得快,如果 TTFD 慢(内容加载了 3 秒才出来),用户看到的是一个空壳页面转圈。同时优化 TTID 和 TTFD 才是完整的启动体验优化。

**"ANR 率低就不用担心主线程"**--ANR 的阈值是 5 秒,但主线程上 500ms 的阻塞就会造成明显的冻帧。即使你的 ANR 率为零,也可能存在大量影响用户体验的主线程卡顿。

**"内存指标只要不 OOM 就行"**--PSS 过高的 App 会挤压系统中其他 App 的可用内存,增加 LMK 杀进程的概率。当用户切换回你的 App 时发现它被杀了需要重新启动,这就是"内存性能差"的间接表现。

**"线上监控加个均值就够了"**--均值无法反映尾部延迟。一个 P50=10ms、P99=500ms 的指标和 P50=10ms、P99=12ms 的指标,均值可能差不多,但前者意味着每 100 次操作有一次严重卡顿,用户体验完全不同。

## 参考资料

- [Android Vitals | developer.android.com](https://developer.android.com/topic/performance/vitals)
- [App startup time | developer.android.com](https://developer.android.com/topic/performance/launch-time)
- [FrameMetrics API | developer.android.com](https://developer.android.com/reference/android/view/FrameMetrics)
- [FrameMetricsAggregator | developer.android.com](https://developer.android.com/reference/androidx/core/app/FrameMetricsAggregator)
- [ProfilingManager | developer.android.com](https://developer.android.com/reference/android/os/ProfilingManager)
- [FrameMetrics.DEADLINE | developer.android.com](https://developer.android.com/reference/android/view/FrameMetrics#DEADLINE)
- [FrameTimingMetric | developer.android.com](https://developer.android.com/reference/androidx/benchmark/macro/FrameTimingMetric)
- [ApplicationExitInfo | developer.android.com](https://developer.android.com/reference/android/app/ApplicationExitInfo)
- [Low memory killer daemon | source.android.com](https://source.android.com/docs/core/perf/lmkd)
- [Android Vitals bad behavior thresholds | support.google.com](https://support.google.com/googleplay/android-developer/answer/9844476)
- [Investigate RAM usage | developer.android.com](https://developer.android.com/studio/profile/memory)
- [Manage your app's memory | developer.android.com](https://developer.android.com/topic/performance/memory)
- [Battery Historian | developer.android.com](https://developer.android.com/topic/performance/power/battery-historian)
- [Macrobenchmark | developer.android.com](https://developer.android.com/topic/performance/benchmarking/macrobenchmark-overview)


### 性能分析误区:峰值帧率 vs 稳态帧率
- 来源:https://android-developers.googleblog.com/performance-methodology
- 类型:article
- 摘要:骁龙8 Elite持续负载下30%性能衰减。有意义的指标:30分钟游戏后帧率、99th percentile延迟、冷启动后5分钟内响应。Benchmark应包含热稳定态测试。
- 入库时间:2026-04-08
