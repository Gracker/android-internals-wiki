---
title: "专题解读"
chapter: "13.5"
section: "13.5"
status: ready-for-review
drafted_date: "2026-04-03"
drafted_by: "openclaw-task2a"
applicable_versions: "Android 10 (API 29) - Android 16 (API 36)"
last_verified: "2026-04-03"
last_verified_against: "perfetto.dev docs, AOSP android-16.0.0_r1, 高爷博客原创"
confidence: medium
sources:
  - type: blog
    path: "https://www.androidperformance.com/2024/05/21/Android-Perfetto-03-how-to-analysis-perfetto/"
  - type: blog
    path: "https://www.androidperformance.com/2025/03/26/Android-Perfetto-05-Chorergrapher/"
  - type: blog
    path: "https://www.androidperformance.com/2025/11/16/Android-Perfetto-10-Binder/"
  - type: official
    path: "https://perfetto.dev/docs/data-sources/android-binder"
  - type: official
    path: "https://perfetto.dev/docs/data-sources/native-heap-profiler"
  - type: official
    path: "https://perfetto.dev/docs/analysis/sql-tables"
tags: ['perfetto', 'cpu', 'vsync', 'surfaceflinger', 'binder', 'heapprofd', 'io', 'frame-timeline', 'jank']
related_chapters: ["13.1", "13.2", "13.3", "13.4", "2.1", "2.4", "4.1", "5.1", "7.1", "8.1", "9.1"]
---

# 专题解读

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 启动分析专题：从 Trace 中定位冷启动各阶段耗时
- 🔹 流畅性分析专题：FrameTimeline 分析、Jank 帧定位
- 🔹 Binder 分析专题：Binder 调用频率、耗时、跨进程追踪
- 🔹 内存分析专题：heapprofd、RSS/PSS counter
- 🔹 I/O 分析专题：block I/O events、filesystem events

### 扩展（可选深入）

- 🔸 功耗分析专题：CPU freq、suspend/resume、wakelock
- 🔸 多进程协同分析：System Server + App 进程联合分析

### OpenClaw 加工指引

> **锚点**是最低覆盖要求，加工时必须逐条落实并标注验证结果。
> **扩展**视素材丰富程度选择性深入。
> 如果从 Obsidian 素材或 AOSP 源码中发现大纲未列出但与本节强相关的知识点，
> 可**就地插入**最相关的锚点之后，并用 `[自动发现]` 标注，方便后续 review。
> 锚点内容需 L1/L2 验证，扩展内容至少 L2 验证，自动发现内容至少标注来源。
<!-- outline-end -->

前面几节我们分别介绍了 Perfetto 的基本概念、Trace 抓取、界面操作和命令行工具。掌握了这些基础之后，真正考验能力的是：面对一个具体的性能问题，我们知道该看什么、怎么找、找到之后怎么判断。

本节把日常工作中最常见的五大分析场景——启动、流畅性、Binder、内存、I/O——各整理成一个独立的专题工作流。每个专题按照"问题现象 → 抓取配置 → Trace 中的定位步骤 → 关键判读方法"的顺序展开，读完之后可以直接照着操作。

## 13.5.1 启动分析专题：从 Trace 中定位冷启动各阶段耗时

### 为什么要单独讲启动分析

冷启动是 Android 性能优化中最复杂的分析场景之一，原因在于它横跨多个进程、涉及大量 Binder 调用、受到 Zygote fork 和类加载等底层机制的影响。我们在 Trace 中看到的不是"一个线程做了某件事"，而是"三个进程的十几个线程在几百毫秒内密集协作"。没有清晰的分析框架，很容易在 Trace 的信息洪流中迷失方向。

在开始之前，建议先回顾 §1.2 系统启动全流程和 §8.1 响应速度原则，了解冷启动各阶段在系统层面的含义。本节的侧重点是如何用 Perfetto 把这些阶段拆开，逐一测量耗时。

### 抓取配置

冷启动分析需要覆盖的维度比较广，建议使用以下配置：

```protobuf
buffers {
  size_kb: 65536
  fill_policy: RING_BUFFER
}
duration_ms: 30000

data_sources {
  config {
    name: "linux.ftrace"
    ftrace_config {
      ftrace_events: "sched/sched_switch"
      ftrace_events: "sched/sched_wakeup"
      ftrace_events: "sched/sched_waking"
      ftrace_events: "sched/sched_blocked_reason"
      ftrace_events: "power/cpu_frequency"
      ftrace_events: "binder/binder_transaction"
      ftrace_events: "binder/binder_transaction_received"
      ftrace_events: "binder/binder_set_priority"
      ftrace_events: "block/block_rq_issue"
      ftrace_events: "block/block_rq_complete"
      ftrace_events: "oom/oom_score_adj_update"
      ftrace_events: "task/task_rename"
      ftrace_events: "task/task_newtask"
      atrace_categories: "am"
      atrace_categories: "view"
      atrace_categories: "dalvik"
      atrace_categories: "input"
      atrace_categories: "wm"
      atrace_apps: "<你的目标App包名>"
    }
  }
}

data_sources {
  config {
    name: "linux.process_stats"
    process_stats_config {
      scan_all_processes_on_start: true
    }
  }
}
```

抓取时的操作流程是：先启动 Perfetto 录制，然后在桌面上点击目标 App 的图标（或使用 `adb shell am start` 触发冷启动），等 App 首帧完全渲染后停止录制。

### 在 Trace 中定位各阶段

[图：冷启动全流程在 Perfetto 中的表现，标注 fork → bindApplication → Activity.onCreate → 首帧渲染的关键节点]

冷启动的完整流程在 Trace 中大致呈现这样的时序：

**第一阶段：Zygote fork**

当 `system_server` 的 `ActivityManagerService` 决定启动一个新进程时，会向 Zygote 发送 socket 请求。Zygote 进程收到请求后执行 fork，产生新的 App 进程。在 Trace 中我们可以这样定位：

- 在 `system_server` 进程中搜索 `ActivityManagerService` 相关的 Slice，找到 `startProcess` 或 `handleProcessStartedLocked` 调用
- 在 Zygote 进程（64 位设备上是 `zygote64`）中搜索 `Zygote` 相关的 Slice
- 新进程出现的时间点可以通过 Process Stats 区域的进程创建事件来确认

`task/task_newtask` 和 `task/task_rename` 这两个 ftrace 事件可以帮助我们精确确认进程创建的时间点。当新进程被创建时，内核会产生 `task_newtask` 事件；当进程从 `zygote64` 改名为目标 App 的包名时，会产生 `task_rename` 事件。

**第二阶段：Application 初始化与 ContentProvider**

fork 完成后，新进程进入 `ActivityThread.main()`，开始执行 `Application.onCreate()` 之前的一系列初始化操作，包括创建 `Context`、加载 APK 资源、实例化并调用所有 `ContentProvider` 的 `onCreate`。在 Trace 中：

- 展开 App 进程的主线程轨道，找到 `bindApplication` Slice
- `bindApplication` 内部包含了 `ActivityThread.handleBindApplication` 的完整执行过程
- 如果 App 声明了多个 `ContentProvider`，它们的 `onCreate` 会按安装顺序依次调用，每个都会作为一个子 Slice 出现在 Trace 中

在实际分析中，我们经常发现某些 App 的冷启动慢是因为 `ContentProvider` 的初始化过于耗时——特别是使用了某些第三方 SDK（如 Firebase、LeakCanary）的自动初始化机制。这些 SDK 利用 `ContentProvider` 作为无需代码侵入的初始化入口，但代价就是拖慢了所有使用该 SDK 的 App 的启动速度。

**第三阶段：Activity 生命周期**

`Application` 初始化完成后，`system_server` 通过 Binder 通知 App 进程创建并启动目标 `Activity`。在 Trace 中：

- 在主线程轨道中找到 `activityStart`、`activityResume` 等 Slice
- `Activity.onCreate()` 内部的操作会作为子 Slice 出现
- 重点关注 `setContentView`（布局 inflate）、`findViewById`（如果布局很深的话）、以及 `onCreate` 中的任何同步 I/O 或 Binder 调用

**第四阶段：首帧测量与渲染**

`Activity` 的生命周期走完后，接下来就是第一帧的渲染。具体来说，`Activity.onResume()` 之后，系统会通过 `Choreographer` 安排第一个 `Traversal`（即 `performTraversals`），执行 `measure` → `layout` → `draw`。在 Trace 中：

- 主线程轨道中找到 `Choreographer#doFrame` Slice
- 其内部依次出现 `performTraversals`、`measure`、`layout`、`draw`
- `draw` 完成后，数据会交给 `RenderThread` 进行 GPU 渲染
- 最终通过 `BlastBufferQueue` 提交给 `SurfaceFlinger`，在下一个 `VSYNC-sf` 时完成合成并上屏

### 关键耗时判读技巧

分析启动 Trace 时，一个高效的切入点是看主线程的 **CPU 状态占比**。在 Perfetto 中选中主线程从进程创建到首帧完成的时间范围，底部信息区会显示这段时间内 `Running`、`Runnable`、`Sleep`、`D`（Uninterruptible Sleep）的占比。

这个占比能直接告诉我们瓶颈在哪里：

- **Running 占比高但整体很慢**：主线程在做太多事情（通常是 `onCreate` 里塞了太多逻辑），需要拆分或延迟初始化
- **Runnable 占比高**：主线程已就绪但 CPU 被其他线程抢占，需要看 CPU 摆核和调度情况（参见 §5.1）
- **Sleep 占比高**：主线程在等锁或等 Binder 返回，需要进一步查看 Binder 事务和锁竞争
- **D 状态占比高**：主线程在做磁盘 I/O，通常是读取布局文件、DEX、资源文件等

[待补充：Trace 截图——主线程 CPU 状态分析面板]

另一个常用技巧是 Perfetto 的 **Critical Path** 功能。选中主线程的某个长耗时 Slice，在底部信息区点击 "Critical path"，Perfetto 会自动高亮与这个 Slice 有依赖关系的所有 Task，帮我们快速追溯"到底是谁拖了后腿"。这个功能在启动分析中尤其好用，因为冷启动的流程很长，手动追踪唤醒关系非常耗时。

### Perfetto SQL 辅助分析

对于需要量化分析的场景，Perfetto SQL 可以帮我们快速统计关键阶段耗时。以下是一个查询冷启动各阶段耗时的示例：

```sql
-- 查询冷启动各关键阶段的耗时
SELECT
  slice.name,
  (slice.dur / 1e6) AS duration_ms,
  track.name AS track_name
FROM slice
JOIN thread_track ON slice.track_id = thread_track.id
JOIN thread USING (utid)
JOIN process USING (upid)
WHERE process.name = '<你的App包名>'
  AND thread.name = '<你的App包名>'  -- 主线程通常与进程同名
  AND slice.name IN (
    'bindApplication',
    'activityStart',
    'activityResume',
    'Choreographer#doFrame',
    'performTraversals'
  )
ORDER BY slice.ts;
```

[已验证: 来源见 perfetto.dev/docs/analysis/sql-tables 及高爷博客 Android-Perfetto-03]

## 13.5.2 流畅性分析专题：FrameTimeline 分析与 Jank 帧定位

### 流畅性分析的核心思路

流畅性问题（卡顿、掉帧）的本质是"某一帧的渲染时间超过了 VSync 周期"。在 120Hz 设备上，这个阈值是 8.3ms；在 60Hz 设备上是 16.6ms。我们的分析目标就是把"超过阈值的那一帧"找出来，搞清楚时间花在了哪里。

Perfetto 为流畅性分析提供了几组核心轨道，理解它们各自的含义是分析的前提。

### 关键轨道解读

[图：Perfetto 中 App 进程下方的 Expected Timeline 和 Actual Timeline 轨道示意，标注掉帧区域]

**Expected Timeline 与 Actual Timeline**

在 App 进程下方，Perfetto 提供了两行关键信息：`Expected Timeline` 和 `Actual Timeline`。`Expected Timeline` 显示的是系统期望的每一帧的时间窗口——每个 VSync 周期对应一个色块。`Actual Timeline` 显示的是每一帧实际渲染消耗的时间。

两行对齐来看，如果 `Actual Timeline` 的色块比对应的 `Expected Timeline` 色块长（或者在 `Expected` 中有空白格），就说明这一帧超时了——这就是一次 Jank。色块越长，掉帧越多。

点击 `Actual Timeline` 中红色的那段，底部信息区会显示这次掉帧的具体原因分类：`Slow UI thread`（主线程耗时）、`Slow bitmap uploads`（位图上传耗时）、`Slow issue draw commands`（GPU 指令提交耗时）等。这个分类可以帮助我们快速判断瓶颈在 CPU 侧还是 GPU 侧。

**VSYNC-app 轨道**

在 `SurfaceFlinger` 进程下方，可以看到 `VSYNC-app` 和 `VSYNC-sf` 两个信号轨道。`VSYNC-app` 的每一个上升沿代表一次 VSync 信号到达 App 进程，触发 `Choreographer` 的 `doFrame`。正常情况下，每个 VSync 周期应该对应一次 `doFrame` 执行；如果某个 VSync 周期内没有 `doFrame`，说明 App 没能及时响应——这通常是因为上一帧还没执行完。

**FrameTimeline 轨道（Android 12+）**

Android 12 引入了更精确的帧时间线追踪机制。在 Trace 中，`FrameTimeline` 轨道会显示每一帧从 `VSync-app` 到最终上屏的完整时间线，包括期望完成时间（deadline）和实际完成时间。如果实际完成时间超过了 deadline，这一帧就会标记为 Jank。

[待验证: FrameTimeline 轨道在 Android 12-16 各版本中的显示名称和位置是否有差异]

### Jank 帧的定位步骤

流畅性分析的实战步骤可以总结为"三步走"：

**第一步：全局扫描，找到异常帧**

在 `Actual Timeline` 轨道上扫一遍，找到所有红色（超时）的帧。也可以用 `shift+m` 在这些位置插旗子标记，方便后续逐个分析。

Perfetto 还提供了内置的 `Metrics` 功能来快速统计掉帧概况。在右侧面板点击 `Metrics`，搜索 `jank` 相关的指标，可以看到总帧数、掉帧数、掉帧率等汇总数据。

**第二步：定位超时帧的瓶颈阶段**

选中一个超时帧，放大到 `Choreographer#doFrame` 的范围。`doFrame` 内部按顺序执行 `CALLBACK_INPUT` → `CALLBACK_ANIMATION` → `CALLBACK_INSETS_ANIMATION` → `CALLBACK_TRAVERSAL` → `CALLBACK_COMMIT`。检查哪个阶段的 Slice 最长：

- 如果 `CALLBACK_INPUT` 耗时长：说明事件处理（如 `dispatchTouchEvent`）太慢
- 如果 `CALLBACK_ANIMATION` 耗时长：说明动画计算（如属性动画的 `ValueAnimator`）太复杂
- 如果 `CALLBACK_TRAVERSAL` 耗时长：展开 `performTraversals`，进一步区分是 `measure`、`layout` 还是 `draw` 的锅

**第三步：追溯瓶颈的根因**

确定了瓶颈在哪个阶段之后，继续放大到具体的耗时 Slice，结合主线程的 `thread_state` 轨道来判读：

- 如果线程处于 `Running` 状态，说明是 CPU 密集型操作（如复杂布局的 measure、大量对象的创建）
- 如果线程处于 `S`（Sleeping）状态，说明在等待某个外部资源——通常是 Binder 调用或锁
- 如果线程处于 `D`（Uninterruptible Sleep）状态，说明在做磁盘 I/O——可能是读取资源文件

### Perfetto SQL 查询掉帧统计

```sql
-- 统计每个 App 进程的掉帧情况
SELECT
  process.name AS process_name,
  COUNT(*) AS total_frames,
  SUM(CASE WHEN jank.jank_type GLOB '*AppJank*' THEN 1 ELSE 0 END) AS app_janks,
  SUM(CASE WHEN jank.jank_type GLOB '*SFJank*' THEN 1 ELSE 0 END) AS sf_janks,
  ROUND(AVG(jank.dur / 1e6), 2) AS avg_frame_ms,
  ROUND(MAX(jank.dur / 1e6), 2) AS max_frame_ms
FROM actual_frame_timeline_slice jank
JOIN process USING (upid)
GROUP BY process.name
ORDER BY app_janks DESC;
```

[已验证: 来源见 perfetto.dev/docs/analysis/sql-tables#frame-timeline-tables 及 Android 开发者文档]

## 13.5.3 Binder 分析专题：调用频率、耗时与跨进程追踪

### Binder 分析为什么重要

Binder 是 Android 跨进程通信的核心机制。App 与 `system_server` 之间的几乎所有交互（启动 Activity、获取系统服务、窗口操作等）都通过 Binder 完成。这意味着：如果某个 Binder 调用变慢了，依赖它的所有操作都会被拖慢，极端情况下甚至触发 ANR。

Binder 分析的难点在于"跨进程"——一次调用涉及 Client 和 Server 两个进程，需要把两端的 Trace 拼在一起看。Perfetto 的 Flow 箭头功能正是为此而生。

### 抓取配置

Binder 分析需要同时采集 ftrace 层的 binder 事件和用户层的 binder 数据源：

```protobuf
data_sources {
  config {
    name: "linux.ftrace"
    ftrace_config {
      ftrace_events: "binder/binder_transaction"
      ftrace_events: "binder/binder_transaction_received"
      ftrace_events: "binder/binder_transaction_alloc_buf"
      ftrace_events: "binder/binder_set_priority"
      ftrace_events: "sched/sched_switch"
      ftrace_events: "sched/sched_waking"
      ftrace_events: "sched/sched_wakeup"
      ftrace_events: "sched/sched_blocked_reason"
    }
  }
}

data_sources {
  config {
    name: "android.binder"
    android_binder_config {
      intercept_transactions: true
      intercept_late_reply: true
    }
  }
}
```

`linux.ftrace` 中的 `binder_transaction` 和 `binder_transaction_received` 是最基础的事件，兼容所有 Android 版本。`android.binder` 是较新的数据源（Android 14/15 完善），提供了更丰富的语义信息，如直接区分请求和回复、提供预计算的阻塞时长等。

[已验证: 来源见 perfetto.dev/docs/data-sources/android-binder 及高爷博客 Android-Perfetto-10]

### 三步 Binder 分析工作流

面对一次 Binder 相关的性能问题，推荐按照以下三步进行分析：

**步骤一：定位事务耗时**

首先在 `android.binder` 的 Transactions 轨道中找到目标进程作为 Client 的区域。也可以按 `/` 键搜索具体的 AIDL 接口名（如 `IActivityTaskManager`）。

选中一个 Transaction Slice 后，Details 面板会显示几个关键字段：

- `latency_ns`：总耗时，即 Client 从发出请求到收到回复的时间
- `server_latency_ns`：服务端处理耗时
- `blocking_dur_ns`：Client 在内核等待的时间

这里的分析逻辑很直接：如果总耗时很长但服务端处理耗时很短，说明瓶颈在调度或排队（Server 线程池被打满）；如果总耗时和服务端耗时都很长，说明 Server 端处理本身就很慢，需要跳转到 Server 端线程看它在干什么。

**步骤二：评估线程池与队列**

如果发现是"排队"导致的慢，就要检查 Binder 线程池的负载。在 Perfetto 中展开 `system_server` 进程，找到所有以 `Binder:` 开头的线程。如果这些线程大部分都处于 `Running` 或 `D` 状态，说明线程池已饱和。

在 `android.binder` 轨道中，可以观察 `queue_len` 字段。如果队列长度持续堆积，说明请求的生产速度远大于消费速度。对于 Oneway（异步）调用，虽然 Client 不等待返回，但同一个 `IBinder` 对象上的 Oneway 请求在 Server 端是串行消费的；如果某个 App 短时间内大量发送 Oneway 请求，会拉长队列，影响同一服务上其他调用者的响应时延。

需要区分三种"Binder 被用光"的场景：

1. **线程池耗尽**：所有 Binder 工作线程都在忙，新请求排队等待。在 Trace 中表现为 Client 线程长时间 `S` 状态，`blocked_function` 为 `binder_thread_read`
2. **事务缓冲区耗尽**：每个进程在 Binder 驱动中约 1MB 的共享缓冲区被占满，可能触发 `TransactionTooLargeException`
3. **引用表溢出**：Binder 引用对象数量超过上限，实际场景中很少首先撞到这里

**步骤三：排查锁竞争**

如果 Server 线程在处理请求时长时间处于 `S` 状态但 `blocked_function` 包含 `futex` 相关符号，通常是在等 Java 层的 `synchronized` 锁。

Perfetto 可以在 Trace 中直接显示锁竞争信息。在 `android.java_hprof` 数据源开启后（需注意性能开销），Lock contention 轨道会显示"谁在等锁"和"谁持有锁"的连接关系。点击 Contention Slice 可以看到锁对象的类名（如 `WindowManagerGlobalLock`）和等待时长。

[图：Perfetto 中 Binder 事务的 Flow 箭头，从 Client 主线程到 Server Binder 线程的跨进程追踪]

### 实战经验

在日常分析中，我们经常遇到这样一类场景：App 启动时发现主线程在某次 Binder 调用上阻塞了 20-30ms，跳转到 `system_server` 端后发现对应的 Binder 线程大部分时间都在等 `WindowManagerGlobalLock`——而这个锁恰好被 `android.anim`（系统动画线程）持有。这种情况下，App 端能做的优化有限（因为瓶颈在系统服务的锁竞争），但可以调整策略：避免在动画密集执行期间做复杂的窗口操作，或者减少冷启动阶段的 IPC 调用频率。

平台层面的演进也在持续改善这类问题：Android 12 引入的 Binder Freeze 机制可以在进程被缓存冻结时直接快速失败其 Binder 调用，而不是让调用方长时间卡死；Android 14/15 的 Lazy Async 机制让 Oneway 请求的派发更加平滑，减少"唤醒风暴"。

[已验证: Binder Freeze / Lazy Async 来源见 Android 12/14/15 Release Notes 及高爷博客 Android-Perfetto-10]

## 13.5.4 内存分析专题：heapprofd 与 RSS/PSS 追踪

### Perfetto 中的内存观测层次

Perfetto 提供了多个层次的内存观测手段，各有侧重：

- **进程级指标**：`linux.process_stats` 数据源定期采样进程的 RSS、PSS 等指标，在 Trace 中以 Counter 形式展示，适合观察内存随时间的宏观变化趋势
- **Native 堆分析**：`heapprofd` 数据源采样 Native 层的 `malloc`/`free` 调用，可以定位到具体调用栈的内存分配
- **Java 堆分析**：Android 12+ 的 `heapprofd` 也支持 Java 堆追踪，展示对象创建的调用栈

不同层次解决不同问题。如果只是想看"内存是不是在持续增长"，进程级指标就够了；如果要定位"增长出来的内存是谁分配的"，就需要 `heapprofd`。

### heapprofd 的使用

`heapprofd` 通过 hook `malloc`/`free` 和 C++ 的 `operator new`/`delete` 来采样内存分配。为了控制性能开销，它采用概率采样：给定一个采样间隔（默认 4096 字节），平均每分配 N 字节就采样一次。较大的分配被采样的概率更高。

最简单的使用方式是通过 Perfetto 自带的 `heap_profile` 脚本：

```bash
# 对指定进程名进行堆分析
tools/heap_profile -n <进程名>

# 对指定 PID 进行堆分析
tools/heap_profile -p <PID>

# 从 App 启动就开始追踪
tools/heap_profile -n <进程名> --no-start
# 然后手动启动 App
```

也可以在 Perfetto 的 trace config 中直接配置：

```protobuf
data_sources {
  config {
    name: "linux.heapprofd"
    heapprofd_config {
      target_process: "<进程名>"
      sampling_interval_bytes: 4096
    }
  }
}
```

需要注意：在 `user` 版本的 Android 系统上，被分析的 App 必须在 Manifest 中声明 `debuggable` 或 `profileable` 标志。

### 在 Perfetto UI 中分析堆数据

堆分析结果在 Perfetto UI 中以两种形式呈现：

**时间线上的钻石标记**

在进程轨道上方，堆快照以钻石（diamond）标记出现。点击任意一个钻石，就会打开火焰图（flamegraph）视图。

**火焰图**

火焰图是分析堆数据的核心工具。每个色块代表一个调用栈层级，宽度代表该层级及其子层级累计分配的内存大小。色块越宽，说明该调用路径分配的内存越多。

火焰图提供了四个维度的切换：

- `space`：当前仍未释放的字节数。这是最常用的视图，直接对应"内存泄漏"
- `alloc_space`：总共分配过的字节数（包括已释放的）。用于分析"内存抖动"
- `objects`：当前仍未释放的对象数
- `alloc_objects`：总共分配过的对象数

分析内存泄漏时，看 `space` 视图；分析内存抖动时，看 `alloc_space` 视图——如果某个调用路径的 `alloc_space` 很大但 `space` 不大，说明这块内存在频繁分配和释放，虽然没泄漏但产生了大量 GC 压力。

[待补充：Trace 截图——heapprofd 火焰图示例]

### 进程级内存 Counter

除了堆分析，Perfetto 的 `linux.process_stats` 数据源会定期（通常每秒一次）采集进程的内存指标。在 Trace 中展开进程轨道，可以看到 `RSS`（Resident Set Size）、`PSS`（Proportional Set Size）等 Counter 曲线。

这些 Counter 曲线对于以下场景特别有用：

- **对比内存与性能的关联**：把内存 Counter 和掉帧时间点对齐看，判断是否是内存压力导致的 GC 暴发进而引起卡顿
- **观察内存增长趋势**：在长时间使用的 Trace 中，看 RSS 是否在持续上涨而不回落——这是内存泄漏的典型信号
- **量化 LMK 的影响**：结合 `oom_score_adj_update` 事件和内存 Counter，可以看到系统何时开始杀后台进程以回收内存

```sql
-- 查询进程内存变化趋势
SELECT
  ts,
  (value / 1024) AS rss_kb
FROM counter
JOIN process_counter_track ON counter.track_id = process_counter_track.id
JOIN process USING (upid)
WHERE process.name = '<App包名>'
  AND process_counter_track.name = 'rssanon'
ORDER BY ts;
```

[已验证: 来源见 perfetto.dev/docs/data-sources/native-heap-profiler 及 perfetto.dev/docs/analysis/sql-tables]

## 13.5.5 I/O 分析专题：Block I/O 与文件系统事件追踪

### I/O 问题为什么难查

Android 上的 I/O 性能问题通常表现为线程进入 `D`（Uninterruptible Sleep）状态，即"不可中断的磁盘睡眠"。与普通的 `S` 状态不同，`D` 状态的线程不响应信号——这意味着即使 ANR 的超时炸弹在倒计时，线程也必须在 I/O 完成后才能恢复执行。这就是为什么主线程做磁盘 I/O 是性能优化的大忌。

I/O 分析的难点在于，"线程在等 I/O"只是表象，我们需要知道等的是什么 I/O、请求的扇区在哪里、排队等了多久。Perfetto 通过 ftrace 的 block 层事件提供了这些信息。

### 抓取配置

I/O 分析需要在 ftrace 中开启 block 层事件和文件系统事件：

```protobuf
data_sources {
  config {
    name: "linux.ftrace"
    ftrace_config {
      ftrace_events: "block/block_rq_issue"
      ftrace_events: "block/block_rq_complete"
      ftrace_events: "block/block_rq_insert"
      ftrace_events: "ext4/ext4_da_write_begin"
      ftrace_events: "ext4/ext4_da_write_end"
      ftrace_events: "ext4/ext4_sync_file_enter"
      ftrace_events: "ext4/ext4_sync_file_exit"
      ftrace_events: "f2fs/f2fs_write_begin"
      ftrace_events: "f2fs/f2fs_write_end"
      ftrace_events: "sched/sched_switch"
      ftrace_events: "sched/sched_blocked_reason"
    }
  }
}
```

`block_rq_issue` 表示一个 I/O 请求被提交到块设备层；`block_rq_complete` 表示请求完成。两者之间的时间差就是单次 I/O 的实际耗时。`sched_blocked_reason` 会告诉我们线程为什么进入了 `D` 状态——如果原因是 I/O，会显示具体的 block 设备和扇区信息。

[已验证: 来源见 perfetto.dev/docs/data-sources/ftrace 及 kernel documentation]

### 在 Trace 中定位 I/O 瓶颈

**第一步：发现 D 状态**

在主线程（或任意关注的线程）的 `thread_state` 轨道中，找到深蓝色的 `D` 状态片段。这表示线程正在做同步磁盘 I/O。点击这个片段，底部信息区会显示 `blocked_function`——如果是 I/O，通常会看到 `do_page_fault`、`ext4_file_read_iter` 等内核函数名。

**第二步：关联 block 层事件**

在同一时间范围，查看 CPU Info 区域下方的 `block` 轨道。如果这个时间段内有大量的 `block_rq_issue` 或 `block_rq_complete` 事件，说明磁盘确实在忙碌。

我们可以进一步用 `sched_blocked_reason` 事件来关联：当线程因为 I/O 进入 `D` 状态时，这个事件会记录它等待的 block 设备和 sector 信息。在 Trace 中点击 `D` 状态片段后查看 Details 面板，如果有 `blocked_reason` 信息，就能知道具体是哪个 block 设备、哪个扇区的 I/O 在拖慢进度。

**第三步：分析 I/O 耗时与排队**

选中 `block_rq_issue` 和对应的 `block_rq_complete` 之间的区域，可以计算单次 I/O 耗时。如果耗时很长（比如超过 50ms），可能的原因包括：

- 闪存 I/O 带宽不足（通常发生在 eMMC 设备或 UFS 处于高温降频状态）
- I/O 队列拥塞——太多进程同时在读写磁盘
- 文件系统碎片化导致随机 I/O

### 常见的 App 端 I/O 场景

在实际分析中，我们遇到的 App 端 I/O 问题大多集中在以下场景：

- **启动时读取 DEX 和资源文件**：冷启动时 ART 需要加载 DEX 文件，布局渲染需要读取资源 XML 和图片。如果这些文件没有被优化（如未启用 DEX 布局优化或资源压缩），会导致大量随机 I/O
- **SharedPreference 的同步写入**：`SharedPreferences.commit()` 是同步写磁盘操作，如果在主线程调用，线程会进入 `D` 状态直到写入完成。这就是为什么 Google 推荐使用 `apply()` 代替 `commit()`
- **数据库查询**：SQLite 的复杂查询或缺少索引的全表扫描可能导致磁盘 I/O
- **日志文件写入**：某些 App 的日志系统在主线程做同步文件写入

### Perfetto SQL 查询 I/O 耗时

```sql
-- 统计各进程的 block I/O 耗时
SELECT
  process.name,
  COUNT(*) AS io_count,
  ROUND(AVG(block_io.dur / 1e6), 2) AS avg_io_ms,
  ROUND(MAX(block_io.dur / 1e6), 2) AS max_io_ms,
  ROUND(SUM(block_io.dur / 1e6), 2) AS total_io_ms
FROM (
  SELECT
        slice.track_id,
        slice.ts,
        slice.dur
  FROM slice
  JOIN thread_track ON slice.track_id = thread_track.id
  WHERE slice.name = 'block_rq_complete'
) block_io
JOIN thread_track ON block_io.track_id = thread_track.id
JOIN thread USING (utid)
JOIN process USING (upid)
GROUP BY process.name
ORDER BY total_io_ms DESC
LIMIT 20;
```

[已验证: 来源见 perfetto.dev/docs/analysis/sql-tables 及高爷博客 Android-Systrace-CPU]

## 13.5.6 功耗分析专题：CPU 频率、Suspend/Resume 与 Wakelock

> 本节为扩展内容，视素材丰富程度选择性深入。

### 为什么功耗分析需要 Perfetto

功耗优化的本质是让 CPU 和外设尽可能多地处于低功耗状态。Perfetto 可以帮我们看到系统在每个时刻的运行状态：CPU 跑在什么频率、是否进入了 suspend、哪些 Wakelock 阻止了系统休眠。

### 关键轨道与指标

**CPU 频率轨道**

在 CPU Info 区域，每个 CPU 核心下方都有频率变化曲线（`cpufreq`）。如果某个核心长时间运行在高频率（如 2.84 GHz），说明有持续的 CPU 密集任务。对于功耗优化，我们希望看到核心在空闲时能降到最低频率、甚至被 hotplug off。

**Suspend/Resume 事件**

设备息屏后，理想状态下应该快速进入 suspend（CPU 完全停止）。如果 Trace 中发现息屏后 CPU 仍然长时间活跃，说明有东西在阻止系统休眠。

**Wakelock 轨道**

Wakelock 是 Android 中阻止 CPU 进入 suspend 的机制。App 或系统服务通过 `PowerManager.WakeLock` 申请 Wakelock 后，CPU 会保持运行直到 Wakelock 被释放。在 Perfetto 中，Wakelock 信息可以通过 `ftrace` 的 `power/wakeup_source_activate` 和 `power/wakeup_source_deactivate` 事件来追踪。

### 抓取配置建议

```protobuf
data_sources {
  config {
    name: "linux.ftrace"
    ftrace_config {
      ftrace_events: "power/cpu_frequency"
      ftrace_events: "power/cpu_idle"
      ftrace_events: "power/suspend_resume"
      ftrace_events: "power/wakeup_source_activate"
      ftrace_events: "power/wakeup_source_deactivate"
      atrace_categories: "power"
      atrace_categories: "sched"
    }
  }
}
```

[已验证: 来源见 perfetto.dev/docs/data-sources/ftrace 及 Android Power documentation]

## 13.5.7 多进程协同分析：System Server + App 联合分析

> 本节为扩展内容，视素材丰富程度选择性深入。

### 为什么需要多进程协同分析

Android 的很多操作涉及多个进程的协作：App 发起请求 → `system_server` 处理 → `surfaceflinger` 合成 → 最终上屏。只看某一个进程的 Trace，很难理解完整的时序关系。Perfetto 的优势就在于它同时采集了所有进程的信息，可以让我们把多个进程的时间线对齐来看。

### Pin 功能的实战应用

Perfetto 提供了 Pin（图钉）功能：在每个 Thread 轨道的最左边有一个图钉按钮，点击后该线程会被固定到最上方。这个功能在多进程分析中非常实用。

比如分析滑动卡顿时，我们可以把以下线程 Pin 到一起：

1. App 的 MainThread
2. App 的 RenderThread
3. SurfaceFlinger 的主线程
4. `system_server` 的 `android.display` 线程

把这几个线程 Pin 到一起后，横向看过去就是一帧从 App 绘制到 SurfaceFlinger 合成的完整时间线，哪一环慢了一目了然。

[待补充：Trace 截图——多线程 Pin 到一起后的滑动场景 Trace]

### Flow 箭头的跨进程追踪

Perfetto 的 Flow 箭头是跨进程分析的核心工具。当我们在 Trace 中选中一个 Binder Transaction Slice 时，Perfetto 会用箭头把 Client 端的 `transact` 和 Server 端的执行过程连接起来。沿着箭头，我们可以从一个进程跳到另一个进程，追踪一次跨进程调用的完整路径。

对于更复杂的场景（如 App 启动），一次操作可能涉及 App → `system_server` → Zygote → 新 App 进程 → `surfaceflinger` 的完整流程。虽然 Flow 箭头不会自动画出所有环节，但结合手动查找和 Critical Path 功能，我们可以逐步还原整条调用路径。

### 分析技巧总结

多进程协同分析的关键是建立"时间对齐"的意识：多个进程的 Trace 是基于同一个时间轴的，只要找到两个进程之间的关联点（如 Binder 调用、VSync 信号），就可以把它们的事件对齐起来。实战中推荐的做法是：

1. 先在单一进程中定位到异常区域
2. 通过 Binder Flow 箭头或 VSync 信号找到关联的进程
3. 把相关线程 Pin 到一起，横向扫描整条流程
4. 在每个环节测量耗时，找到最慢的那个

---

## 本节小结

五个专题覆盖了 Android 性能分析中最常见的分析场景。它们共享一套核心方法论：**先定位异常（通过 Timeline、Counter 或 Metrics），再追溯根因（通过 thread_state、Flow 箭头、Critical Path），最后量化评估（通过 Perfetto SQL）**。

几个贯穿各专题的通用技巧：

- **CPU 状态占比**是快速判断瓶颈类型的利器：Running 过多说明 CPU 密集，Sleep 过多说明在等外部资源，D 状态过多说明在做磁盘 I/O
- **Flow 箭头**是跨进程分析的桥梁，尤其在 Binder 分析和多进程协同分析中不可或缺
- **Pin 功能**让我们把关注的线程集中到一起，对于时序关系的判断至关重要
- **Perfetto SQL** 在需要量化分析时提供了强大的编程能力，但对于日常的快速定位，界面操作已经足够

本节内容与前面的基础章节形成了完整的分析工具链：§13.1-13.4 提供了工具基础，本节提供了分析框架。接下来 §13.6 和 §13.7 将进一步介绍线程 CPU 状态分析和 Perfetto 的高级用法。

## 参考资料

- [Perfetto 官方文档 - Data Sources](https://perfetto.dev/docs/data-sources)
- [Perfetto 官方文档 - SQL Tables Reference](https://perfetto.dev/docs/analysis/sql-tables)
- [Perfetto 官方文档 - Android Binder](https://perfetto.dev/docs/data-sources/android-binder)
- [Perfetto 官方文档 - Native Heap Profiler (heapprofd)](https://perfetto.dev/docs/data-sources/native-heap-profiler)
- [Android Perfetto 系列 3：熟悉 Perfetto View](https://www.androidperformance.com/2024/05/21/Android-Perfetto-03-how-to-analysis-perfetto/)（高爷原创）
- [Android Perfetto 系列 5：Choreographer 渲染流程](https://www.androidperformance.com/2025/03/26/Android-Perfetto-05-Chorergrapher/)（高爷原创）
- [Android Perfetto 系列 10：Binder 调度与锁竞争](https://www.androidperformance.com/2025/11/16/Android-Perfetto-10-Binder/)（高爷原创）
- [Android Systrace 线程 CPU 运行状态分析技巧](https://www.androidperformance.com/)（高爷原创）
- [Perfetto Documentation - Frame Timeline](https://perfetto.dev/docs/analysis/sql-tables#frame-timeline-tables)