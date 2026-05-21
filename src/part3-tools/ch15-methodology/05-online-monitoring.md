---
title: "线上性能监控"
chapter: "15.5"
last_task6_review_log: "logs/review/2026-05-21-20-review.md"
last_task6_at: "2026-05-21T20:11:00+08:00"
reviewed_date: "2026-05-21"
reviewed_by: openclaw-task6
task6_result: pass-light-edit
section: 15.5
status: ready-for-review
drafted_date: "2026-04-04"
drafted_by: "openclaw-task2a"
applicable_versions: "Android 7 (API 24) - Android 16 (API 36)"
last_verified: "2026-04-25"
last_verified_against: "AOSP android-16.0.0_r1, Android ProfilingManager / ProfilingTrigger / ApplicationExitInfo docs, art/runtime/signal_catcher.cc"
confidence: medium
sources:
  - type: official
    path: "developer.android.com/topic/performance/metrics"
  - type: official
    path: "developer.android.com/reference/android/view/FrameMetrics"
  - type: official
    path: "developer.android.com/reference/android/app/ApplicationExitInfo"
  - type: official
    path: "developer.android.com/reference/android/os/ProfilingManager"
  - type: official
    path: "developer.android.com/reference/android/os/ProfilingTrigger"
  - type: official
    path: "developer.android.com/topic/libraries/architecture/startup"
  - type: official
    path: "developer.android.com/jetpack/androidx/releases/jankstats"
  - type: official
    path: "perfetto.dev/docs/instrumentation/tracing-sdk"
  - type: aosp
    path: "art/runtime/signal_catcher.cc"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/am/ProcessErrorStateRecord.java"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/am/AnrHelper.java"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/am/ActivityManagerService.java"
tags: [monitoring, APM, FrameMetrics, JankStats, ANR, startup, production]
related_chapters: ["7.1", "7.3", "8.1", "9.3", "14.1", "14.6", "14.12", "15.3", "15.4", "15.9", "15.10"]
pipeline_stage: task2b_pending
task2b_result: pending
task2b_state: pending
task6_state: reviewed
task9_state: reviewed
last_task9_at: "2026-05-21T20:31:42+08:00"
task9_reviewed_by: openclaw-task9
task9_reviewed_date: "2026-05-21"
task9_result: needs-rework
repaired_date: "2026-04-25"
repaired_by: "openclaw-task2b"
last_task2b_at: "2026-04-25T19:43:07+08:00"
last_task9_audit: "2026-05-21"
last_task9_audit_at: "2026-05-21T13:31:48+08:00"
last_task9_audit_log: "logs/deep-review/2026-05-21-13-audit.md"
last_task9_review_log: "logs/deep-review/2026-05-21-20-deep-review.md"
review_notes: "2026-05-21 Task9 deep review: needs-rework。P0：FrameMetrics 指标表使用不存在的公开常量名；P1：GPU_DURATION/API31 版本边界与 ANR 触发口径需补。"
task9_review_notes: "2026-05-21 Task9 deep review: P0 FrameMetrics 常量名错误写入 queue；P1 GPU_DURATION/API31 版本边界、ANR 系统触发分类与 ApplicationExitInfo trace 处理写入 queue；P2 App Startup 2ms 数据口径写入 suggestions。"
---
# 线上性能监控

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 线上性能监控的必要性：发现线下测试无法覆盖的问题
- 🔹 帧率监控：Choreographer FrameCallback、FrameMetrics API
- 🔹 启动耗时监控：手动埋点 vs Jetpack App Startup 集成
- 🔹 ANR 监控：FileObserver 监听 traces.txt / ANR signal handler
- 🔹 监控数据的采样、聚合与报警策略

### 扩展（可选深入）

- 🔸 使用 Perfetto SDK 做线上 tracing
- 🔸 监控数据的可视化与归因分析平台

### OpenClaw 加工指引

> **锚点**是最低覆盖要求，加工时必须逐条落实并标注验证结果。
> **扩展**视素材丰富程度选择性深入。
> 如果从 Obsidian 素材或 AOSP 源码中发现大纲未列出但与本节强相关的知识点，
> 可**就地插入**最相关的锚点之后，并用 `[自动发现]` 标注，方便后续 review。
> 锚点内容需 L1/L2 验证，扩展内容至少 L2 验证，自动发现内容至少标注来源。
<!-- outline-end -->

## 为什么要做线上性能监控

我们在第 7 章讲卡顿分析、第 9 章讲 ANR 分析时，讨论的都是"拿到了 Trace 怎么看"。那些分析工作有一个共同的前提：你得先知道出了问题。在开发阶段，我们靠 Systrace/Perfetto 手动抓 Trace、靠 StrictMode 拦截主线程 IO、靠开发者选项里的 GPU 呈现模式分析来发现异常。但这些手段都有一个明显局限：**它们只能覆盖开发者在实验室里主动测试的场景。**

真实用户面对的情况远比测试环境复杂。不同 SoC 平台（高通、联发科、三星）的 GPU 驱动行为有差异；不同内存配置（4GB vs 12GB）下的后台压力不同；不同网络条件（弱网切换、VPN 连接）对数据加载的影响各异；不同 Android 版本（厂商 ROM 定制层）的系统调度策略也有出入。一个在 Pixel 上完全流畅的列表滚动，在某款低端机上可能频繁掉帧；一个在 WiFi 下秒开的页面，在 4G 弱信号下可能要等 3 秒。这些问题如果不在线上采集数据，开发者很难发现。

线上性能监控要解决的核心问题就三个：**感知**（知道出了问题）、**定位**（知道问题在哪）、**量化**（知道问题有多严重、影响多少用户）。三者缺一不可——只感知不定位等于废话，只定位不量化等于没有优先级。

整套监控体系通常围绕四个维度展开：帧率（流畅性）、启动耗时（响应速度）、ANR/卡死（可用性）、以及内存异常（稳定性）。下面我们逐个展开，看看在 Android 上怎么把这些数据从用户设备上可靠地采集回来。

## 先把线上监控拆成三层

很多团队在做线上性能监控时，会把“埋点”“SDK”“平台”“报警”混成一件事。更稳的理解方式是先分三层：

| 层次 | 解决的问题 | 常见载体 |
|---|---|---|
| 信号层 | 能不能采到帧、启动、ANR、exit、trace 这些原始信号 | `JankStats`、`FrameMetrics`、`ApplicationExitInfo`、自定义埋点 |
| 客户端增强层 | 能不能在异常时补充更细粒度的证据 | `Matrix`、`btrace`、自定义 trace / session 记录 |
| 平台层 | 能不能按版本 / 机型 / 页面聚合、告警和回查 | Firebase、Measure、自建平台 |

如果一开始就不分层，后面常见的结果是：客户端采集越来越重，但平台依然回查困难；或者平台图表很好看，但一出具体 case 仍然拿不到现场。

## 帧率监控：从 FrameCallback 到 JankStats

帧率监控是线上性能监控中信息密度最高的一环。它回答的是"用户看到画面时，到底有多少帧是掉帧的"。

### Choreographer.FrameCallback：最直接的帧率感知方式

我们在 §2.4 已经详细讲过 Choreographer 的工作原理：它基于 VSync 信号驱动每一帧的渲染，在 doFrame() 回调中执行 Input、Animation、Traversal 三类任务。既然每一帧都会经过 Choreographer 的 doFrame()，那我们只要注册一个 FrameCallback，在每次回调中记录时间戳，就能算出相邻两帧的间隔——这就是最基本的帧率监控。

```java
// 基于 Choreographer.FrameCallback 的帧率监测核心逻辑
Choreographer.getInstance().postFrameCallback(new Choreographer.FrameCallback() {
    private long lastFrameTimeNanos = 0;

    @Override
    public void doFrame(long frameTimeNanos) {
        if (lastFrameTimeNanos > 0) {
            long intervalMs = (frameTimeNanos - lastFrameTimeNanos) / 1_000_000;
            if (intervalMs > 16) {
                reportJank(intervalMs);
            }
        }
        lastFrameTimeNanos = frameTimeNanos;
        Choreographer.getInstance().postFrameCallback(this);
    }
});
```

[已验证: 官方文档, developer.android.com/reference/android/view/Choreographer.FrameCallback]

这段代码的核心逻辑只有三步：记录上一帧时间戳、计算帧间隔、判断是否掉帧。但实际使用中有几个需要注意的细节。

第一，`postFrameCallback()` 只会注册一次回调。如果想持续监听，必须在每次 `doFrame()` 末尾重新注册，就像上面代码中那样。忘记重新注册是最常见的初学者错误。

第二，`frameTimeNanos` 是 VSync 信号到达的时间，而不是你的 `doFrame()` 被执行的时间。因此，帧间隔测量的是"两个相邻 VSync 之间的距离"，而不是"你的代码执行耗时"。这恰好是我们想要的——它反映的是用户实际感知到的帧率。

第三，`doFrame()` 运行在所属 `Choreographer` 的 Looper 线程上。应用通常在主线程调用 `Choreographer.getInstance()`，所以这个回调在所有 API 版本里通常都在主线程执行。回调里只做时间戳采集和计数，写文件、序列化、上报都放到后台线程。

FrameCallback 的方式虽然简单直接，但它有一个明显的短板：只知道"掉了多少帧"，不知道"为什么掉"。它是纯时序层面的感知，没有渲染管线内部的细节。

### FrameMetrics API：拿到每一帧的完整耗时拆解

Android 7.0（API 24）引入的 `FrameMetrics` API 解决了"只知道掉帧、不知道原因"的问题。它提供了每一帧从 VSync 到最终上屏的完整耗时分项，包括以下几个维度：

| 指标 | 含义 | 对应渲染阶段 |
|------|------|-------------|
| `UNKNOWN_DELAY` | VSync 到开始处理之间的等待 | 消息队列延迟 |
| `INPUT_HANDLING` | Input 事件处理耗时 | Input 回调 |
| `ANIMATION` | 动画计算耗时 | Animation 回调 |
| `LAYOUT_MEASURE` | measure/layout 耗时 | Traversal 回调 |
| `DRAW` | draw 耗时 | Traversal 回调 |
| `SYNC` | 同步阶段耗时 | RenderThread |
| `COMMAND_ISSUE_DURATION` | 向图形驱动下发绘制命令耗时 | RenderThread / graphics driver command issue |
| `SWAP_BUFFERS` | Buffer 交换耗时 | BufferQueue |
| `TOTAL_DURATION` | 帧总耗时 | 全流程 |
| `FIRST_DRAW_FRAME` | 首帧绘制标记 | 冷启动首帧 |

[已验证: 官方文档, developer.android.com/reference/android/view/FrameMetrics]

有了这些分项数据，才能区分掉帧是因为布局太复杂、GPU 渲染太慢、还是主线程消息队列堵塞——没有这个粒度的拆解，性能优化就是盲人摸象。

从 API 31 开始，FrameMetrics 还新增了 `DEADLINE` 指标，直接告诉你这一帧的 deadline 是多少（取决于当前屏幕刷新率）。有了 deadline，判断掉帧就不再需要硬编码 16ms，而是直接比较 `TOTAL_DURATION` 和 `DEADLINE`：

```java
// 所有值单位为纳秒 (ns)
long totalDurationNanos = metrics.getMetric(FrameMetrics.TOTAL_DURATION);

if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
    // API 31+：直接读取系统给出的 deadline
    long deadlineNanos = metrics.getMetric(FrameMetrics.DEADLINE);
    boolean isJank = totalDurationNanos > deadlineNanos;
} else {
    // API 24-30：通过屏幕刷新率计算 deadline
    Display display = context.getSystemService(DisplayManager.class)
            .getDisplay(Display.DEFAULT_DISPLAY);
    float refreshRate = display.getRefreshRate();
    long deadlineNanos = (long) (1_000_000_000.0 / refreshRate);
    boolean isJank = totalDurationNanos > deadlineNanos;
}
```

[已验证: 官方文档, developer.android.com/reference/android/view/FrameMetrics]
[已验证: AOSP android-16.0.0_r1, frameworks/base/core/java/android/view/FrameMetrics.java]

FrameMetrics 的数据通过 `Window.OnFrameMetricsAvailableListener` 回调获取。这个回调运行在 `addOnFrameMetricsAvailableListener()` 传入的 `Handler` 所属 Looper 线程上。接入时通常会准备专用 `HandlerThread`，在回调里复制或聚合数据后再异步上报；如果传的是主线程 `Handler`，回调本身也会占用主线程时间。

### JankStats：Google 官方的帧率监控库

2022 年 Google 发布了 `JankStats` 库（AndroidX），它是 FrameMetrics 的上层封装，解决了直接使用 FrameMetrics 时的几个工程问题。

**版本兼容**。FrameMetrics 从 API 24 才有，JankStats 在低版本上回退到 `ViewTreeObserver.OnPreDrawListener` 来近似监测帧率，对开发者屏蔽了版本差异。

**UI 状态关联**。JankStats 提供了 `PerformanceMetricsState` API，允许你在代码中标记当前的 UI 状态（比如"正在滚动首页列表"、"详情页加载中"）。这样当掉帧事件上报时，就能直接知道"用户在做什么的时候掉帧了"。这是定位和复现掉帧问题的前提。低版本回退到 `ViewTreeObserver.OnPreDrawListener` 时，这个监听点还承担同步锚点的作用：业务侧写入的页面、操作、列表状态，会和帧信号重新匹配，避免纯 FrameMetrics 上报只有耗时而缺少业务上下文。

```java
performanceMetricsState.putState("navigation", "HomeFragment");
performanceMetricsState.putState("user_action", "scrolling_feed");
```

[已验证: AndroidX androidx-main, metrics/metrics-performance/src/main/java/androidx/metrics/performance/JankStatsApi24Impl.kt, JankStatsApi31Impl.kt]

**掉帧判定策略的可配置性**。JankStats 默认的 `jankHeuristicMultiplier` 是 `2.0f`。API 24-30 会先按刷新率估算期望帧时长，API 31+ 直接读取 `FrameMetrics.DEADLINE`，再用 `uiDuration` 和这个阈值比较。业务侧可以按自己的流畅度目标调整这个 multiplier。

在实际项目中，如果你的 App 最低支持 API 24+，直接使用 FrameMetrics 就够用了；如果需要覆盖更低的版本，或者想要 UI 状态关联和开箱即用的掉帧判定逻辑，JankStats 是更省心的选择。

再往前走一步，线上体系通常会把二者的职责切开：

- `JankStats` 负责更统一的帧级感知与 UI 上下文
- `FrameMetrics` 负责在高版本设备上补更细的分阶段耗时

不要把二者理解成非此即彼。对大多数团队，更合理的是“用 `JankStats` 做主信号，用 `FrameMetrics` 做高版本增强”。

## 启动耗时监控：从手动埋点到自动化度量

启动耗时是另一个需要线上监控的核心指标。与帧率不同，启动耗时的监控难点不在 API 调用，而在于**怎么定义"启动完成"这个时刻**。

### 冷启动、温启动、热启动

Android 把 App 启动分为三种类型，线上监控需要分别度量：

- **冷启动**：App 进程不存在，从 Zygote fork 开始到首帧渲染完成。这是最慢的启动路径，也是优化价值最高的场景。Google Play Console 的 Android Vitals 将冷启动超过 5 秒定义为"过长"。
- **温启动**：App 进程仍在内存中，但 Activity 需要重新创建（用户按了返回键退出后重新打开）。通常比冷启动快得多。
- **热启动**：App 在后台被带回前台，Activity 不需要重建。用户感知为"瞬间恢复"。

[已验证: 官方文档, developer.android.com/topic/performance/vitals/launch-time]

### 关键指标：TTID 与 TTFD

启动监控中有两个核心指标：

**TTID（Time To Initial Display）**：从 App 启动到第一帧渲染完成的时间。它反映的是"用户看到画面需要等多久"。系统会在 logcat 中输出 `Displayed` 日志记录这个时间，你也可以通过 `adb shell am start -W` 命令获取。但 TTID 有一个陷阱：第一帧可能是一个空白 loading 页面或闪屏，用户虽然"看到了东西"，但 App 还不能交互。

**TTFD（Time To Full Display）**：从 App 启动到内容完全加载并可交互的时间。它反映的是"用户要等多久才能开始使用"。这个指标需要开发者自己定义"完全可交互"的时机，并通过调用 `Activity.reportFullyDrawn()` 来标记。

```java
@Override
protected void onCreate(Bundle savedInstanceState) {
    super.onCreate(savedInstanceState);
    setContentView(R.layout.activity_main);

    loadDataAsync(new Callback() {
        @Override
        public void onComplete() {
            reportFullyDrawn();
        }
    });
}
```

[已验证: 官方文档, developer.android.com/reference/android/app/Activity#reportFullyDrawn()]

在线上监控中，TTID 和 TTFD 都应该被采集。如果 TTID 正常但 TTFD 过长，说明首帧虽然画出来了但内容还没好；如果两者都长，说明从进程创建到第一帧渲染这条路上就有问题。

### 手动埋点 vs 自动化采集

获取启动耗时有两种方式：手动埋点和系统 API 自动采集。

**手动埋点**是最传统的方式：在 `Application.attachBaseContext()` 记录起点时间戳，在 `Activity.onWindowFocusChanged()` 或自定义的"可交互"时刻记录终点时间戳，两者之差就是启动耗时。这种方式灵活但维护成本高——如果有人改了启动流程忘了更新埋点，数据就不准了。

手动埋点最大的价值是可以拆分启动子阶段：初始化 SDK 花了多少时间、加载首屏数据花了多少时间、渲染首帧花了多少时间。这些细粒度数据对定位启动瓶颈是直接输入。

**系统 API 自动采集**则依赖 Android 框架提供的能力。从 API 24 开始，系统在 logcat 中输出的 `Displayed` 日志就包含了 TTID 信息。更现代的做法是使用 Jetpack Macrobenchmark 库在 CI 环境中持续度量启动时间，但这属于测试侧，不是线上监控。

**Jetpack App Startup** 库本身不直接提供启动耗时监控能力，但它在启动优化中扮演重要角色：它通过合并多个 ContentProvider 的初始化到单一的 `InitializationProvider` 中，减少了每个 ContentProvider 约 2ms 的开销。在使用 App Startup 后，启动流程变得更加结构化，也更容易在关键节点插入埋点。

[已验证: 官方文档, developer.android.com/topic/libraries/architecture/startup]

工程上更推荐的做法，是把启动监控拆成两层：

- **基础指标层**：TTID、TTFD、冷 / 温 / 热启动分类
- **阶段指标层**：Application 初始化、首屏数据、首屏可交互、首个网络请求完成等

只采总启动时长，往往只能知道“慢了”；拆出阶段，才能知道“慢在 Application、数据、还是渲染”。

## ANR 监控：从 Watchdog 到 ApplicationExitInfo

ANR（Application Not Responding）是线上监控中优先级最高的一类问题。用户遇到 ANR 时会看到"应用无响应"的系统对话框，这直接冲击用户信任——比偶尔掉帧严重得多。

### 为什么 ANR 监控比想象的困难

ANR 监控面临一个主要矛盾：**ANR 的定义是主线程被阻塞超过阈值（通常 5 秒），而你要监控 ANR 的代码也运行在同一个 App 里。** 如果主线程卡死了，你的监控代码怎么执行？

这催生了两种截然不同的监控思路。

### 思路一：Watchdog 线程（ANR Watchdog）

最经典的方案是用一个独立的后台线程充当"看门狗"。它的工作方式很直观：每隔一段时间（比如 5 秒）向主线程的 Handler 投递一个 Runnable，然后 sleep 等待。如果主线程在超时前执行了这个 Runnable，说明主线程还活着，一切正常；如果超时了还没执行，说明主线程被阻塞了，很可能发生了 ANR。

开源库 `ANR-WatchDog` 就实现了这个思路。当检测到主线程无响应时，它会抓取所有线程的堆栈信息并上报。

这个方案的优点是实现简单、兼容性好（所有 Android 版本都能用）。缺点是**精度有限**——5 秒的轮询间隔意味着检测延迟至少是 5 秒，而且有较高的误报率。如果主线程只是偶尔卡了一下（比如 GC 暂停 200ms），但还没到 ANR 的程度，Watchdog 可能不会触发；反过来，如果轮询间隔设得太短，又容易把短暂的 UI 卡顿误判为 ANR。

### 思路二：系统级监控（ApplicationExitInfo）

Android 11（API 30）引入了 `ApplicationExitInfo` API，这是 ANR 监控领域的一次质变。系统会在 App 进程退出时记录退出原因，其中就包括 ANR（`REASON_ANR`）。通过这个 API，我们可以直接获取系统认定的 ANR 事件，无需自己猜测"是不是 ANR"。

```java
ActivityManager am = context.getSystemService(ActivityManager.class);
List<ApplicationExitInfo> exitInfos = am.getHistoricalProcessExitReasons(
        context.getPackageName(), 0, 10
);

for (ApplicationExitInfo info : exitInfos) {
    if (info.getReason() == ApplicationExitInfo.REASON_ANR) {
        InputStream traceStream = info.getTraceInputStream();
        if (traceStream != null) {
            parseAndReportAnrTrace(traceStream);
        }
        long timestamp = info.getTimestamp();
        int importance = info.getImportance();
        int pid = info.getPid();
    }
}
```

[已验证: 官方文档, developer.android.com/reference/android/app/ApplicationExitInfo]
[适用版本: Android 11 (API 30)+]

`ApplicationExitInfo` 的优势在于数据来自系统，与 Google Play Console 的 ANR 统计口径一致。对 `REASON_ANR`，`getTraceInputStream()` 通常返回系统保留的 ANR traces；对 `REASON_CRASH` / `REASON_CRASH_NATIVE`，它能把 Java Crash、Native Crash 和 ANR 纳入同一套退出历史模型。Android 12（API 31）之后，Native Crash 场景可能返回 Protobuf 格式的 tombstone trace，解析流程要按二进制 tombstone 处理，不能假设它一定是纯文本。`getTraceInputStream()` 不是所有退出原因都有值，线上代码要把 `null` 当成正常分支。

`ApplicationExitInfo` 只有在 API 30+ 的设备上才可用。对于覆盖 API 30 以下设备的应用，需要同时保留 Watchdog 方案作为兜底。大多数成熟的 APM SDK（如 Firebase Crashlytics、Sentry）都采用了这种分层策略：API 30+ 用 ApplicationExitInfo，低版本回退到 Watchdog。

### 关于 FileObserver 监听 traces.txt

大纲中提到的 `FileObserver` 监听 `/data/anr/traces.txt` 是一种较早期的 ANR 监控方案。它的原理是：当系统检测到 ANR 时，会向 `/data/anr/` 目录写入 traces 文件。通过 FileObserver 监听这个目录的文件创建事件，App 就能在 ANR 发生时被通知到。

这个方案在现代 Android 上已经不太实用了，原因有三：

1. **权限限制**：从 Android 10 开始，`/data/anr/` 目录的访问权限被大幅收紧。普通 App 无法直接读取其他进程的 traces 文件。即使通过 FileObserver 检测到了文件创建，也未必能读取内容。
2. **SELinux 策略**：许多厂商 ROM 的 SELinux 策略阻止 App 进程访问 ANR traces 目录。
3. **ApplicationExitInfo 更优**：在 API 30+ 设备上，`ApplicationExitInfo.getTraceInputStream()` 直接提供了 traces 数据，无需自行处理文件访问。

所以今天线上 ANR 监控的最佳实践是：API 30+ 用 ApplicationExitInfo，低版本用 Watchdog 线程兜底，FileObserver 方案仅在特殊场景（如系统级 App 或有平台签名权限的 App）下考虑。

### 思路三：SIGQUIT / SignalCatcher 自采栈

系统处理 ANR 时会让目标进程 dump 线程栈，ART 侧入口是 `art/runtime/signal_catcher.cc` 中的 `SignalCatcher::HandleSigQuit()`。`SignalCatcher` 线程通过 `sigwait` 消费 `SIGQUIT`，再生成 Java 线程 dump。自研 APM 所说的 ANR signal handler，通常是在这个信号现场补采进程状态、主线程栈、最近页面和业务 breadcrumb。

这类方案的边界要写清：

- 它只补现场，不负责判定系统是否已经认定 ANR；最终口径仍以系统 ANR、`ApplicationExitInfo` 和 Android Vitals 为准。
- 普通 `sigaction(SIGQUIT, ...)` 不一定稳定收到信号，因为 ART 的 `SignalCatcher` 使用 `sigwait` 消费 `SIGQUIT`。SDK 如果改动信号掩码或 hook SignalCatcher 路径，必须保证系统 dump 线程栈的流程继续执行。
- signal 现场只做轻量记录，例如时间戳、tid、主线程栈快照、ring buffer 指针。文件 IO、JSON 序列化、网络上报放到后续线程或下次启动。
- 面向普通 App 的量产版本，API 30+ 默认优先用 `ApplicationExitInfo`；SIGQUIT 自采栈更适合作为低版本、内测包、厂商合作或强控制环境下的补充方案。

[已验证: AOSP android-16.0.0_r1, art/runtime/signal_catcher.cc]

## 监控数据的采样、聚合与报警策略

把数据从用户设备上采集回来只是第一步。如果每帧、每次启动、每个 ANR 都全量上报，后端的存储和计算成本会很快失控，用户的流量和电量消耗也会成为问题。所以线上监控必须有一套合理的采样和聚合策略。

### 分层采样

成熟的 APM 系统通常采用三层采样策略：

**第一层：全量采集基础指标（低开销）**。每个用户会话都采集聚合数据：会话总帧数、掉帧总数、冷启动 TTID/TTFD、ANR 次数、崩溃次数。这些数据量很小（每次会话几十字节），但对建立性能基线是必需的。它能回答"我们的 App 整体性能怎么样"这个问题。

**第二层：采样采集详细数据（中等开销）**。对一部分用户（通常 5%-10%）启用详细帧率监控（FrameMetrics 拆解数据）和启动子阶段埋点。采样比例可以根据用户量动态调整——日活 100 万的 App 采 5% 就够了，日活 1 万的 App 可能需要采 50% 才能获得统计意义。要保证采样是随机的，不能只采高端设备。

**第三层：定向全量采集（高开销）**。对于异常会话（发生 ANR、崩溃、或启动超过阈值），不受采样比例限制，全量采集所有数据。这是"发现问题"的关键——你不需要所有用户的详细数据，但你绝对需要出问题的那些用户的详细数据。

### 异常触发补证据：ProfilingManager

Android 15（API 35）开始提供 `android.os.ProfilingManager`，应用可以请求 system trace、Java heap dump、heap profile、stack sampling 等重样本。Android 16（API 36）加入 `ProfilingTrigger` 的系统触发模式，例如 `TRIGGER_TYPE_ANR`、`TRIGGER_TYPE_APP_FULLY_DRAWN`。系统命中事件后返回正在运行的 system trace snapshot，适合放在第三层采样里作为“异常触发补证据”的默认候选。

它和自建 APM trace 的分工很清楚：轻量指标负责长期覆盖，`ProfilingManager` 负责在异常样本上拿一份系统视角的重证据。ANR、启动超标这类场景里，running trace snapshot 可以利用系统环形缓冲区回看事件发生前的一小段时间，比异常之后再临时开始抓 trace 更有价值。

接入时要把三个边界写进客户端策略：

- **版本边界**：API 35 支持应用主动请求 profiling；API 36 起才有系统触发器。Android 14 及以下仍要走自建 trace、Perfetto SDK 或实验包抓取流程。
- **限流边界**：系统会按进程和系统预算限流，结果不保证每次都返回。客户端要记录 request type、trigger type、error code 和设备上下文，不在前台循环重试。
- **隐私边界**：trace、heap dump、tombstone 都是诊断 artifact，可能包含路径、线程名、业务 tag 或对象信息。上传前要做大小限制、加密、过期清理和合规审查。

### 数据聚合

上报到服务端的原始数据需要聚合才能变成可操作的信息。聚合维度通常包括：

- **App 版本**：每次发版后对比关键指标，发现性能回归
- **设备型号/SoC 平台**：识别特定设备的性能问题
- **Android 版本**：发现系统版本相关的性能差异
- **地域/网络类型**：区分网络相关和数据无关的问题
- **用户操作路径**：结合 UI 状态标记，知道"哪个页面/哪个操作"有问题

聚合后的核心指标应该包括 P50/P90/P95/P99 分位数。平均值在性能监控中几乎无用——100 个 16ms 的帧和 1 个 1600ms 的帧平均下来是 31.7ms，看起来还算正常，但那个 1600ms 的帧对应的正是用户体验最差的时刻。

### 报警策略

报警负责把监控结果推到处理流程里。一个好的报警系统应该做到：**及时发现、低误报率、附带上下文**。

典型做法是设置滑动窗口报警：比如"过去 1 小时内，某 App 版本 + 某设备组的 P95 冷启动时间超过 3 秒，且影响的用户数 > 50"。单纯的阈值报警（"P95 > 3s 就报警"）容易被异常值干扰，加上最小影响用户数的条件可以过滤掉统计噪声。

另一个重要实践是**报警分级**。ANR 率超过 0.5% 是 P0 级别的紧急事件，需要立即处理；P95 启动时间从 1.5s 退化到 2s 是 P1 级别的性能回归，需要当天排查；帧率 P90 从 58fps 降到 55fps 可能是 P2 级别的趋势变化，放在周报里跟踪就好。

## 扩展：使用 Perfetto SDK 做线上 tracing

我们在 §13 章详细介绍了 Perfetto 作为 Trace 分析工具的用法。但 Perfetto 不仅仅是一个离线分析工具——它提供了 C++ SDK，可以在 App 内部集成轻量级的自定义 tracing，用于线上性能监控的深度场景。

Perfetto SDK 的核心概念是 **Track Event**：你可以用 `TRACE_EVENT` 宏在代码中标记自定义的开始/结束事件，这些事件会被写入共享内存 buffer，最终序列化为 protobuf 格式的 trace 文件。

它有两种运行模式：

- **In-process 模式**：只记录 App 自身的事件，不需要系统权限，适合线上场景。App 完全控制 tracing 的生命周期——什么时候开始、什么时候停止、上传到哪个服务器。
- **System 模式**：连接系统的 `traced` 守护进程，同时采集内核 ftrace、atrace 等系统事件，能看到完整的 CPU 调度、IO、内存等上下文。这个模式主要用于开发和测试阶段，不太适合线上。

线上使用 Perfetto SDK 的典型场景是"按需深度追踪"：当线上监控发现某个用户的性能指标异常时，可以远程下发指令，对该用户启用 Perfetto tracing，采集一个短时间窗口（比如 10 秒）的详细 trace，然后上传分析。这种"发现问题 → 深入追踪"的模式，比全量采集高效得多。

[已验证: 官方文档, perfetto.dev/docs/instrumentation/tracing-sdk]

Perfetto SDK 主要面向 C/C++ 代码。对于纯 Java/Kotlin 的 Android App，直接使用 FrameMetrics + JankStats + 自定义埋点通常更实用。Perfetto SDK 更适合有 Native 层的 App（比如游戏引擎、音视频处理、大厂的跨平台框架）。

## 扩展：监控数据的可视化与归因分析平台

采集了数据、设计了采样策略、搭建了报警，剩下的一块拼图是**可视化与归因分析**。原始数据堆在数据库里没有任何价值，必须变成可交互的图表和报告，才能驱动决策。

### Google Play Console — Android Vitals

对于发布到 Google Play 的 App，Android Vitals 是最基础的线上性能数据来源。它提供了：

- **ANR 率和崩溃率**：按日/周维度，与 Google Play 的"表现不佳"阈值对比
- **启动时间分布**：冷/温/热启动的 P50/P90/P95
- **渲染性能**：掉帧率、慢帧比例、冻结帧比例
- **电量消耗**：后台 wakeup、部分 wake lock 持有时间

Android Vitals 的数据来自所有 Play Store 用户，不需要在 App 中集成任何 SDK，这是它的最大优势。但它也有局限：数据粒度较粗（无法看到单个用户的详细 trace），且无法自定义指标和维度。

[已验证: 官方文档, developer.android.com/topic/performance/vitals]

### Firebase Performance Monitoring

Firebase 提供了更细粒度的线上性能监控能力。它的核心优势是与 Android 生态深度集成：自动采集 App 启动时间、网络请求耗时、Screen 渲染性能等指标，同时支持自定义 Trace 和 Metric。

Firebase 的局限在于它是 Google 生态内的服务，在国内使用存在网络访问问题。对于面向国内市场的 App，需要考虑其他方案。

### 自建 APM 平台

大型 App（日活百万级以上）通常会自建 APM 平台。核心组件包括：

- **客户端 SDK**：采集帧率、启动耗时、ANR、内存等数据
- **数据管道**：Kafka/Pulsar 等消息队列 + 实时计算（Flink/Spark Streaming）
- **存储层**：时序数据库（InfluxDB/ClickHouse）存储聚合指标 + 对象存储（S3/OSS）存储原始 trace
- **可视化**：Grafana/自建 Dashboard 展示趋势图和分布图
- **报警引擎**：基于规则或机器学习的异常检测

自建平台的投入很大，但好处是可以完全按照自己的业务需求定制采集维度和分析逻辑。比如电商 App 可能需要在下单流程的每个步骤插入埋点，社交 App 可能需要监控消息列表的滚动帧率分布——这些是通用 APM 平台做不到的。

无论选择哪种方案，有几个原则是通用的：

第一，**数据要和用户行为关联**。纯技术指标（帧率 55fps）不如带上下文的指标（首页信息流滚动时帧率 55fps）有价值。第二，**关注趋势而不是绝对值**。一个从 50fps 稳定退化到 45fps 的趋势，比一次偶然掉到 30fps 的异常更值得关注。第三，**让数据驱动优化决策**。不是所有掉帧都值得修——如果某个低频操作偶尔掉 2 帧，但只影响 0.1% 的用户，优先级应该低于影响 5% 用户的高频操作卡顿。


## 平台与客户端的边界

客户端最擅长的是感知和取证，平台最擅长的是聚合和回查。成熟方案通常会明确这个边界：

- **客户端**：采集信号、记录上下文、在异常时补现场
- **平台**：聚合趋势、机型对比、版本回归、报警、问题榜单

二者任何一边过弱，线上监控都会失真。只有客户端、平台、修复流程一起成立，线上性能监控才有治理价值。

## 在 Perfetto 中的表现

线上监控数据在 Perfetto 中没有直接对应的 Track（因为 Perfetto 是离线分析工具），但线上监控的各维度指标可以在 Perfetto 中找到对应的验证方式：

- **帧率监控**：对应 Perfetto 中的 `Choreographer#doFrame` slice 和 RenderThread 的 `DrawFrames` slice。线上监控报告的掉帧，在 Perfetto 中能看到完整的渲染管线分项耗时
- **启动耗时**：对应 Perfetto 中的冷启动 Trace（从 Zygote fork 到首帧 doFrame）。`reportFullyDrawn()` 的调用时刻在 Perfetto 中会显示为 `ActivityManager: Fully drawn <package_name>` 的日志事件
- **ANR 监控**：对应 Perfetto 中主线程的长时间 block（能看到具体阻塞在哪个方法）以及 `am_anr` 的 logcat 事件

线上监控发现异常后，用 Perfetto 抓一条对应的 Trace 来做深度分析，这是"线上监控 + 线下分析"的标准工作流。

## 最常见的四个误区

- **误区 1：把线上监控当成线下工具的替代品**  
  它们是互补，不是替换关系。

- **误区 2：只采总指标，不采上下文**  
  没有页面、场景、版本、机型上下文，后续归因会非常难。

- **误区 3：异常证据全量上传**  
  成本和隐私都会迅速失控。

- **误区 4：指标平台和 backlog 脱节**  
  能看到问题，不代表问题真的进入治理流程。

## 与其他章节的关系

本章作为方法论章节，与全书的多个技术章节形成上下游关系：

- **§2.4 Choreographer 与渲染流水线**：理解帧率监控 API 的前提是理解 Choreographer 的工作原理
- **§7.3 卡顿分析方法论**：线上监控发现卡顿后，用 §7.3 的方法做深度分析
- **§9.3 ANR 分析方法**：线上监控发现 ANR 后，用 §9.3 的方法做根因分析
- **§14.1 Android Studio Profiler** 和 **§14.6 自动化测试工具**：开发阶段的性能分析工具，与线上监控互补
- **§15.4 竞品分析方法**：线上监控数据也常用于竞品对比

如果换一个更强的主线视角，也可以这么理解：

- `7/8/9` 定义了用户到底在抱怨什么
- `15.3` 定义了我们该看哪些数字
- 本节负责把这些数字稳定地从线上拿回来
- `15.9` 负责构建从数据到修复的完整流程
- `15.10` 负责把这套流程变成团队机制

## 常见问题与误区

**"线上帧率监控会拖慢 App"**——如果实现得当，帧率监控的开销非常小。FrameMetrics 的回调线程由注册时传入的 `Handler` 决定，把它放到专用 `HandlerThread` 上时，主线程压力很小；如果传的是主线程 `Handler`，回调本身也会占用主线程时间。拖慢 App 的通常是回调中的 IO 操作或复杂计算。正确做法是：回调中只做数据采集，上报操作放到后台线程批量执行。

**"ANR Watchdog 能替代 ApplicationExitInfo"**——不能完全替代。Watchdog 是基于启发式的（"主线程 N 秒没响应就认为 ANR"），而 ApplicationExitInfo 提供的是系统认定的 ANR 事件。两者的数据口径不同，Watchdog 的误报率更高。在 API 30+ 设备上应该优先使用 ApplicationExitInfo。

**"采样率越高质量越好"**——不是。5% 的随机采样对于日活百万级的 App 已经能提供统计意义上足够精确的 P95 估计。盲目提高采样率只会增加成本，不增加决策价值。需要全量采集的是异常会话（ANR/崩溃/严重卡顿），而不是正常用户的行为。

**"启动耗时只需要监控冷启动"**——不够。虽然冷启动是优化重点，但温启动和热启动的用户体验同样重要。很多 App 的温启动因为 Activity 重建时的数据加载而变慢，这个问题只有监控温启动才能发现。

**"有了 Firebase/第三方 APM 就不需要自己做了"**——第三方 APM 提供通用能力，但无法覆盖业务特有的监控需求。比如"商品详情页图片加载到可交互的耗时"这样的业务指标，只能自己埋点。最佳实践是第三方 APM 做基础监控 + 自定义埋点做业务监控，两者互补。

## 参考资料

- AOSP 源码路径：
  - `frameworks/base/core/java/android/view/Choreographer.java` — FrameCallback 和 doFrame 实现
  - `frameworks/base/core/java/android/view/FrameMetrics.java` — 帧耗时分项 API
  - `frameworks/base/core/java/android/view/Window.java` — OnFrameMetricsAvailableListener 注册
  - `frameworks/base/core/java/android/app/ApplicationExitInfo.java` — 进程退出信息 API
  - `frameworks/base/services/core/java/com/android/server/am/ProcessErrorStateRecord.java` — `appNotResponding` 入口
  - `frameworks/base/services/core/java/com/android/server/am/AnrHelper.java` — ANR 排队与处理辅助逻辑
  - `frameworks/base/services/core/java/com/android/server/am/ActivityManagerService.java` — ANR 与进程管理入口
  - `frameworks/base/services/core/java/com/android/server/am/ProcessRecord.java` — 进程状态记录，作为 ANR 上下文补充
  - `art/runtime/signal_catcher.cc` — ART `SignalCatcher::HandleSigQuit()`
- 官方文档：
  - [FrameMetrics API](https://developer.android.com/reference/android/view/FrameMetrics)
  - [JankStats Library](https://developer.android.com/jetpack/androidx/releases/jankstats)
  - [ApplicationExitInfo](https://developer.android.com/reference/android/app/ApplicationExitInfo)
  - [ProfilingManager](https://developer.android.com/reference/android/os/ProfilingManager)
  - [ProfilingTrigger](https://developer.android.com/reference/android/os/ProfilingTrigger)
  - [App Startup Time](https://developer.android.com/topic/performance/vitals/launch-time)
  - [Jetpack App Startup](https://developer.android.com/topic/libraries/architecture/startup)
  - [Android Vitals](https://developer.android.com/topic/performance/vitals)
  - [Perfetto SDK](https://perfetto.dev/docs/instrumentation/tracing-sdk)
- 深入阅读：
  - Google I/O 2022: "Measuring and improving performance with JankStats"
  - Android Performance Patterns 系列 (youtube.com/playlist?list=PLWz5rJ2EKKc9CBxr3BVjPTPoDPLdPIFCE)
