---
title: "各 Android 版本性能变更追踪"
chapter: "16.2"
applicable_versions: "Android 12 (API 31) - Android 16 (API 36)"
drafted_date: "2026-04-04"
last_verified: "2026-05-29"
last_verified_against: "developer.android.com API reference + AOSP android-16.0.0_r1 SystemHealthManager / Display / packages/modules/Profiling"
confidence: medium
sources:
  - type: official
    path: "developer.android.com/about/versions/12/behavior-changes-12"
  - type: official
    path: "developer.android.com/about/versions/13/behavior-changes-13"
  - type: official
    path: "developer.android.com/about/versions/14/behavior-changes-14"
  - type: official
    path: "developer.android.com/about/versions/15/behavior-changes-15"
  - type: official
    path: "developer.android.com/about/versions/16/behavior-changes-16"
  - type: official
    path: "developer.android.com/reference/android/os/ProfilingManager"
  - type: official
    path: "developer.android.com/reference/android/os/ProfilingTrigger"
  - type: official
    path: "developer.android.com/reference/android/os/health/SystemHealthManager"
  - type: official
    path: "developer.android.com/reference/android/view/Display"
  - type: official
    path: "https://android.googlesource.com/platform/frameworks/base/+/android-16.0.0_r1/core/java/android/os/health/SystemHealthManager.java"
  - type: official
    path: "https://android.googlesource.com/platform/packages/modules/Profiling/+/android-16.0.0_r1/framework/java/android/os/ProfilingManager.java"
  - type: official
    path: "https://android.googlesource.com/platform/frameworks/base/+/android-16.0.0_r1/core/java/android/view/Display.java"
  - type: official
    path: "developer.android.com/reference/android/view/Choreographer"
  - type: official
    path: "developer.android.com/reference/android/view/FrameMetrics"
  - type: blog
    path: "android-developers.googleblog.com (ADPF updates)"
tags: ['version-changes', 'behavior-changes', 'api-evolution', 'migration', 'performance-api']
related_chapters: ["1.6", "2.9", "4.6", "5.7", "6.4", "9.2", "13.1", "14.7"]
task6_state: reviewed
task6_result: pass-light-edit
reviewed_by: openclaw-task6
reviewed_date: "2026-05-29"
last_task6_audit: "2026-05-18"
section: "16.2"
status: finalized
pipeline_stage: ready-to-publish
task9_state: reviewed
task9_result: pass-tech-review
task2b_state: fixed
task2b_result: fixed-lite
last_task2b_lite_at: "2026-05-29"
task9_reviewed_by: "openclaw-task9"
task9_reviewed_date: "2026-04-21"
last_task9_at: "2026-05-29T06:27:31+08:00"
last_task9_audit: "2026-05-18"
task6_reviewed_date: "2026-05-29"
task6_reviewed_by: openclaw-task6
last_task6_at: "2026-05-29T07:07:00+08:00"
last_task6_review_log: "logs/review/2026-05-29-07-review.md"
task6_review_notes: "2026-05-29 07:07 Task6 revisiting review: pass-light-edit；清理 1 处否定纠正式句型与参考材料中英文间距；Task9 auto-fixed 后无 queue pending，晋升 finalized；无新增 L3/L4 回炉项。"
last_task9_autofix_at: "2026-05-29"
last_task9_review_log: "logs/deep-review/2026-05-29-06-deep-review.md"
task9_review_notes: "2026-05-29 Task9 deep-review: auto-fixed。修正 Android 15 FGS timeout 处理、Android 14/15 低 targetSdk 安装限制与 Google Play target API 政策边界；无 queue P0/P1。"
task6_reviewed_at: "2026-05-29T07:07:00+08:00"
task6_l1_l2_fixes: 3
task6_l3_l4_issues: 0
deepseek_cn_review_state: done
last_deepseek_cn_review_at: 2026-05-29
---

# 各 Android 版本性能变更追踪

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 Android 12-16 各版本性能相关 Release Notes 摘要
- 🔹 Behavior Changes 对 App 性能的影响（后台限制、权限变化、进程管理）
- 🔹 新增 API 的性能意义（FrameMetrics 增强、ProfilingManager、Dynamic Performance 等）
- 🔹 Deprecated API 及替代方案
- 🔹 迁移注意事项：targetSdkVersion 升级对性能行为的影响

### 扩展（可选深入）

- 🔸 Android 16 Beta/DP 中的实验性特性
- 🔸 向前兼容策略：如何在支持多版本的同时利用新特性

### OpenClaw 加工指引

> **锚点**是最低覆盖要求，加工时必须逐条落实并标注验证结果。
> **扩展**视素材丰富程度选择性深入。
> 如果从 Obsidian 素材或 AOSP 源码中发现大纲未列出但与本节强相关的知识点，
> 可**就地插入**最相关的锚点之后，并用 `[自动发现]` 标注，方便后续 review。
> 锚点内容需 L1/L2 验证，扩展内容至少 L2 验证，自动发现内容至少标注来源。
<!-- outline-end -->

## 为什么要关注版本变更

每个 Android 版本发布时，开发者注意力通常集中在新 API 和新功能上。但影响 App 性能表现的，往往是那些藏在 Behavior Changes 文档角落里的"小字"——后台执行限制变多了、前台服务的超时变短了、某个性能 API 的行为改了。如果你的 App 还在用旧版本的假设跑在新系统上，性能表现可能在你不知不觉中退化。

这一节不是简单罗列 Release Notes（你可以直接去 developer.android.com 看）。我们要做的是把这些变更**按对性能的实际影响**组织起来，告诉你在分析性能问题时，哪些版本行为差异是你需要考虑的变量。

本章按两条线展开：先按版本走一遍性能相关的关键变更（从 Android 12 到 Android 16），再按主题（后台限制、性能 API、废弃 API、迁移策略）横向梳理，方便你带着具体问题来查。

## Android 12（API 31）：后台执行限制增多

Android 12 在性能方面的影响，主要集中在**后台执行限制**和**前台服务约束**上。这些变化通常不提升 App 运行速度，但会改变它"在后台能做多少事"。

### 后台启动前台服务被禁止

从 Android 12 开始，App 在后台运行时一般不能再启动前台服务（Foreground Service）。如果强行调用 `startForegroundService()`，系统会抛出 `ForegroundServiceStartNotAllowedException`。这意味着：你不能再依赖后台服务来维持长时间运行的性能监控或数据上传任务。

替代方案是使用 `WorkManager`。对于需要在后台执行的性能分析任务（如定期采样 CPU 使用率、上报 ANR 统计），`WorkManager` 的约束调度机制是更合适的方案，因为它与系统的 Doze 模式和 App Standby Bucket 配合工作，不会触发系统限制。

[已验证: 官方文档, developer.android.com/about/versions/12/behavior-changes-12#foreground-service-launch-restrictions]

### 精确闹钟需要权限

Android 12 要求 App 声明 `SCHEDULE_EXACT_ALARM` 权限才能设置精确闹钟。如果你的性能监控框架使用 `AlarmManager.setExact()` 来定时采集数据，在 Android 12+ 上需要检查这个权限是否已授予。对于大多数性能分析场景，`setAndAllowWhileIdle()` 或 `WorkManager` 的周期任务已经够用，不需要精确闹钟。

[已验证: 官方文档, developer.android.com/about/versions/12/behavior-changes-12#exact-alarm-permission]

### 通知跳板被禁用

Android 12 禁止通过通知的 `PendingIntent` 启动 Service 或 BroadcastReceiver，再从这些组件中启动 Activity（即"通知跳板"）。如果你的 App 使用这种方式在通知点击后跳转到性能分析结果页面，需要改为直接在通知的 `PendingIntent` 中使用 `Activity` intent。

### App 休眠

长时间不使用的 App 会被系统重置权限并进入休眠状态。这对性能分析框架意味着：如果你的 App 被休眠了，它注册的所有 `JobScheduler` 任务和 `AlarmManager` 闹钟都会被取消。在 Perfetto 中，你会看到被休眠 App 的进程完全消失，所有后台活动停止。

### Stretch Overscroll

Android 12 将过度滚动（overscroll）效果从旧的 Glow 效果改为 Stretch（拉伸）效果。如果你在 Trace 中看到滚动边缘有额外的渲染工作，部分原因可能是新的 Stretch 动画计算。这个变化本身对性能影响很小，但如果你的 App 自定义了 overscroll 行为，需要注意新效果可能引入额外的 `draw()` 调用。

### Game Mode API

Android 12 引入了 Game Mode API，允许游戏根据用户选择的模式（性能优先/省电优先）调整渲染策略。这是 Android Dynamic Performance Framework（ADPF）的起点。如果你的游戏支持 Game Mode，可以在不同模式下对比 Perfetto Trace，观察 CPU 频率和帧时间的变化。

[已验证: 官方文档, developer.android.com/about/versions/12/features/game-mode]

## Android 13（API 33）：通知权限与 ART 优化

Android 13 的性能相关变更集中在**通知权限**、**ART 运行时优化**和**JobScheduler 改进**三个方面。

### 运行时通知权限

Android 13 引入了 `POST_NOTIFICATIONS` 运行时权限。如果你的性能监控框架通过通知栏展示实时性能数据（如 FPS 计数器、内存使用量），在 Android 13+ 上需要先获取这个权限。用户拒绝后，通知不会展示，但你的代码不会崩溃——只是数据推送变得无声无息。

[已验证: 官方文档, developer.android.com/about/versions/13/behavior-changes-13#notification-permission]

### ART 运行时更新

Android 13 包含了 ART 运行时的性能优化，这些优化通过 Google Play 系统更新推送到 Android 12+ 的设备上。关键改进包括更快的类查找和改进的垃圾回收调度。这些优化是全局性的，不需要 App 做任何修改就能受益。在 Perfetto 中，你可能会观察到 GC 事件的持续时间略有减少。

### JobScheduler 预取优化

Android 13 改进了 `JobScheduler` 的预取（prefetch）任务调度。系统会尝试预测 App 的下一次启动时间，并在此之前的合适窗口执行 prefetch 任务。如果你的 App 使用 prefetch 任务来预热缓存或预加载资源，这个改进意味着预热操作更有可能在用户实际启动 App 之前完成，从而减少冷启动耗时。

[已验证: 官方文档, developer.android.com/about/versions/13/behavior-changes-13#jobScheduler]

### 断字性能大幅提升

Android 13 将 `TextView` 的断字（hyphenation）性能提升了约 200%。如果你的 App 之前因为断字开销大而禁用了断字功能，Android 13+ 上可以重新启用，对渲染性能的影响已经微乎其微。在 Trace 中，这表现为 `measure()` 阶段中文字布局相关操作的耗时减少。

[已验证: 官方文档, developer.android.com/about/versions/13/features#hyphenation]

### Choreographer API 的关键里程碑

Android 13 在 Choreographer 的演进中是一个重要节点。它引入了 `Choreographer.VsyncCallback` 和 NDK 端的 `AChoreographer_postVsyncCallback`，允许 App 接收更详细的帧时间信息。`AChoreographerFrameCallbackData` 负载还提供了多个候选帧时间线（frame timelines），App 可以根据渲染截止时间和期望呈现时间选择合适的时间线。

在 Android 13+ 上，App 可以在渲染截止时间过近时动态简化渲染（比如跳过某些非关键绘制），而不必总是努力在下一个 VSync 前完成所有工作。这个能力是后续版本中 Frame Pacing 和自适应刷新率的基础。

[已验证: 官方文档, developer.android.com/reference/android/view/Choreographer.VsyncCallback]

## Android 14（API 34）：冻结缓存应用与前台服务类型

Android 14 对后台进程管理做了迄今为止最大的调整——**冻结缓存应用**，同时对前台服务增加了类型声明要求。

### 缓存应用冻结

Android 14 引入了对缓存应用（cached app）的冻结机制。当 App 进入缓存状态一段时间后，系统会冻结其进程，使其完全不能使用 CPU。Google 官方数据显示，这一机制使缓存应用的 CPU 占用减少了约 50%。

这对性能分析有直接意义：如果你的 App 在后台有周期性工作（如定时采样、日志上报），在 Android 14+ 上这些工作会被冻结。你需要在 Trace 中看到 App 进程从 "Running" 变为 "Sleeping" 再到被冻结（frozen 状态），这不是 bug，是系统行为。

冻结机制配合广播队列化（queued broadcasts）一起工作：缓存 App 注册的上下文广播会被排队，在 App 回到前台时一次性投递。如果你依赖广播来触发性能数据采集，在 Android 14+ 上这些广播可能延迟到 App 回到前台才投递。

[已验证: 官方文档, developer.android.com/about/versions/14/behavior-changes-14#freeze-cached-apps]

### 前台服务必须声明类型

Android 14 要求每个前台服务声明至少一个 `foregroundServiceType`，并请求对应的权限。这个变化对性能分析工具尤其重要：如果你的 App 使用前台服务来保持性能数据采集（如持续 Perfetto 抓取），需要选择合适的服务类型。常见选择是 `specialUse`（需要在 Google Play Console 中说明理由）或 `dataSync`（但 Android 15 开始有 6 小时限制）。

还有个类型值得留意：`shortService`：它有严格的大约 3 分钟生命周期限制。超时后系统会调用 `Service.onTimeout()`，如果 App 没有在短时间内调用 `stopSelf()`，会触发 ANR。这个机制是全新的——以前前台服务没有这种硬超时。

[已验证: 官方文档, developer.android.com/about/versions/14/behavior-changes-14#fgs-types]

### JobScheduler 对 ANR 的惩罚

Android 14 引入了新的限制：如果一个 App 的 `JobService` 在 `onStartJob()`、`onStopJob()` 或 `onBind()` 中反复导致 ANR，系统会将该 App 的所有 Job 放入受限的 standby bucket。你的后台任务执行窗口会被大幅压缩。如果你的性能分析框架使用 `JobScheduler`，需要确保 `onStartJob()` 在主线程上的工作量极小，耗时操作放到后台线程。

[已验证: 官方文档, developer.android.com/about/versions/14/behavior-changes-14#jobScheduler-anr]

### 非线性字体缩放

Android 14 支持字体缩放至 200%，但对大字号采用非线性缩放——文本越大，缩放比例越小。如果你的 App 在性能分析中关注布局耗时，需要知道：200% 字体缩放不等于所有文本面积翻倍。非线性缩放减少了极端字号下的布局计算量，但也意味着你不能简单地用线性关系估算字体缩放对布局性能的影响。

[已验证: 官方文档, developer.android.com/about/versions/14/features#non-linear-font-scaling]

## Android 15（API 35）：ADPF 深化与 ProfilingManager 诞生

Android 15 引入了两个会改变性能分析工作流的 API：**ProfilingManager** 和 **ApplicationStartInfo**，同时继续深化 ADPF。

### ProfilingManager：App 内性能数据采集

Android 15 首次引入 `ProfilingManager` API。在此之前，获取 Perfetto trace 或 heap dump 需要通过 `adb` 命令或 `Debug` 类的方法，只能在开发阶段使用。`ProfilingManager` 让 App 可以在运行时请求系统采集 profiling 数据，包括 Java heap dump、stack sample 和 system trace。

这个 API 更适合做**线上性能诊断**。你可以在 App 的性能监控框架中集成 `ProfilingManager`，当检测到异常指标（如帧时间突然飙高）时，自动触发一次 trace 采集。采集到的数据保存在 App 的 data 目录，可以在后续启动时上传分析。

```java
// API 35 基础用法：手动触发
ProfilingManager pm = getSystemService(ProfilingManager.class);
pm.registerForAllProfilingResults(
    Executors.newSingleThreadExecutor(),
    result -> {
        // result.getResultFilePath() 包含 trace 文件路径
        // 上传或本地分析
    }
);
```

[已验证: 官方文档, developer.android.com/reference/android/os/ProfilingManager]

### ApplicationStartInfo：启动分析的数据基础

Android 15 引入了 `ApplicationStartInfo` 类，提供 App 启动的详细信息，包括启动类型（冷/温/热）、各阶段耗时、启动时间戳等。这是启动优化分析（见 §8.2）的重要数据来源。

之前，开发者需要手动在 `Application.onCreate()` 和各 Activity 的生命周期中打点来测量启动耗时。`ApplicationStartInfo` 提供了系统视角的启动数据，包含了从进程创建到 `Application.onCreate()` 之前的系统开销（如 Zygote fork、ClassLoader 初始化），这些是手动打点无法覆盖的。

[已验证: 官方文档, developer.android.com/reference/android/app/ApplicationStartInfo]

### ADPF 能力扩展

Android 15 在 ADPF 中引入了两个重要增强：

第一，hint session 支持**省电模式**。App 可以标记某些 hint session 为省电优先，系统会降低对应线程的 CPU 频率目标。这适用于长时间运行的后台计算任务（如视频编码、大数据处理），在不需要极致性能时可以显著减少功耗。

第二，hint session 可以**同时报告 GPU 和 CPU 工作时长**。在此之前，ADPF 主要关注 CPU 调度。现在 App 可以告诉系统 GPU 端的负载情况，系统据此同时调整 CPU 和 GPU 频率，实现更均衡的性能-功耗权衡。

[已验证: 官方文档, developer.android.com/about/versions/15/behavior-changes-15#adpf]

### 前台服务时间限制

Android 15 对 `dataSync` 和 `mediaProcessing` 类型的前台服务引入了 6 小时的时间上限。超过这个时间后，系统会调用 `Service.onTimeout(int, int)`；服务需要在回调里调用 `stopSelf()` 或停止前台状态收尾，否则会进入前台服务超时错误。若配额已经耗尽，继续启动同类型前台服务会抛出 `ForegroundServiceStartNotAllowedException`。如果性能数据同步任务依赖 `dataSync` 前台服务，需要设计成能在 6 小时内完成，或者改用 `WorkManager` 分批处理。

[已验证: 官方文档, developer.android.com/about/versions/15/behavior-changes-15#fgs-time-limit]

### 16KB 页面大小支持

Android 15 开始支持 16KB 内存页面大小。这对 App 性能有几个影响：内存分配更粗粒度（每个页 16KB 而不是 4KB），但 TLB miss 减少，大内存访问性能可能提升。如果你的 App 使用 NDK 库，需要重新编译以支持 16KB 页面对齐。未重新编译的库在 16KB 页面设备上可能导致内存使用增加和性能退化。

[已验证: 官方文档, developer.android.com/about/versions/15/behavior-changes-15#16kb]

## Android 16（API 36）：系统触发式 Profiling 与自适应应用

Android 16 在性能分析工具链上的突破比在性能机制本身更大。它引入了**系统触发式 Profiling**、**ApplicationStartInfo 增强**和**自适应应用**要求，同时带来了 FrameMetrics 和 ADPF 的增量改进。

### 系统触发式 Profiling

Android 16 把 `ProfilingManager` 从手动抓取扩展到系统触发式采样。App 先通过 `registerForAllProfilingResults()` 注册全局结果监听，再用 `addProfilingTriggers(List<ProfilingTrigger>)` 声明自己关心的系统事件。API 36 公开的触发器包括 `TRIGGER_TYPE_ANR` 和 `TRIGGER_TYPE_APP_FULLY_DRAWN`。`TRIGGER_TYPE_COLD_START` 要到 API 37 才出现在公开参考页里，所以不能把它写成 Android 16 的稳定接口。

```java
// Imports are omitted.
ProfilingManager pm = getSystemService(ProfilingManager.class);

pm.registerForAllProfilingResults(
    getMainExecutor(),
    result -> Log.d(
        "Profiling",
        result.getTriggerType() + " -> " + result.getResultFilePath())
);

pm.addProfilingTriggers(
    List.of(
        new ProfilingTrigger.Builder(ProfilingTrigger.TRIGGER_TYPE_ANR)
            .setRateLimitingPeriodHours(12)
            .build(),
        new ProfilingTrigger.Builder(ProfilingTrigger.TRIGGER_TYPE_APP_FULLY_DRAWN)
            .setRateLimitingPeriodHours(12)
            .build()
    )
);
```

`addProfilingTriggers()` 不带 request-scoped callback，系统触发结果要靠 `registerForAllProfilingResults()` 接收。对于线上偶发 ANR 和启动路径抖动，这类结果比事后手工复现更接近现场。

[已验证: 官方文档, developer.android.com/reference/android/os/ProfilingManager ; developer.android.com/reference/android/os/ProfilingTrigger]

### ApplicationStartInfo.getStartComponent()

Android 16 在 `ApplicationStartInfo` 上新增了 `getStartComponent()` 方法，返回触发进程启动的具体组件类型（Activity / BroadcastReceiver / ContentProvider / Service / Other）。

启动优化需要先区分触发组件。

多数开发者假设冷启动由 Activity 触发，但 ContentProvider 初始化（多个 SDK 各自注册的 ContentProvider）和 BroadcastReceiver 也会触发进程创建。不同触发路径的初始化逻辑和优化策略差异很大。

有了 `getStartComponent()`，你可以精确区分并分别优化每条启动路径。

[已验证: 官方文档, developer.android.com/reference/android/app/ApplicationStartInfo#getStartComponent()]

### 自适应应用：大屏强制可调整

Android 16 对大屏设备（smallest width ≥ 600dp）强制忽略 `screenOrientation`、`resizableActivity="false"`、`minAspectRatio`、`maxAspectRatio` 以及对应的 runtime API（`setRequestedOrientation()` / `getRequestedOrientation()`）。

从性能角度看，Activity 因窗口尺寸变化会更频繁地 recreate。如果你的 App 在配置变更时没有正确保存和恢复 UI 状态（通过 ViewModel + `rememberSaveable`），用户会感知到界面闪烁和数据丢失——这不只是功能 bug，也是响应速度的退化。

[已验证: 官方文档, developer.android.com/about/versions/16/behavior-changes-16#adaptive-apps]

### Predictive Back 默认启用

Android 16 将 Predictive Back（预测性返回）设为默认启用。系统会在用户手势进行中就开始准备目标 UI，这对 App 的响应速度提出了更高要求——你不能再等到 `onBackPressed()` 被调用时才准备返回动画，因为 Predictive Back 在手势阶段就需要目标 UI 的预览。

新增的 `finishAndRemoveTaskCallback()` 和 `moveTaskToBackCallback()` 让 App 可以精确控制 back 手势在不同层级的行为。`PRIORITY_SYSTEM_NAVIGATION_OBSERVER` 优先级允许 App 观察（但不消费）系统级 back 事件，用于分析统计。

`onBackPressed()` 在 Android 16 中被进一步标记为废弃。如果你还在用旧 API，建议迁移到 `OnBackInvokedDispatcher`。

[已验证: 官方文档, developer.android.com/about/versions/16/behavior-changes-16#predictive-back]

### FrameMetrics 新增 FRAME_TIMELINE_VSYNC_ID

Android 16 在 `FrameMetrics` 中新增了 `FRAME_TIMELINE_VSYNC_ID` 字段。这个字段提供了一个 ID，将 HWUI 生成的帧与 SurfaceFlinger 中的时间线数据关联起来。之前要追踪一帧从 App 端到 SurfaceFlinger 的完整生命周期需要靠时间戳做模糊匹配，现在有了精确的关联 ID，帧分析会可靠得多。

[已验证: 官方文档, developer.android.com/reference/android/view/FrameMetrics]

### ADPF：SystemHealthManager 余量 API

Android 16 在 `android.os.health.SystemHealthManager` 中放入了 `getCpuHeadroom()` 和 `getGpuHeadroom()`。这组接口在 android-16.0.0_r1 里仍带 `@FlaggedApi(android.os.Flags.FLAG_CPU_GPU_HEADROOMS)`，设备不支持时会抛 `UnsupportedOperationException`，服务端暂时拿不到稳定估算时也可能返回 `Float.NaN`。返回值本身是 0 到 100 的 `float`，更适合做低频采样或场景切换时的热约束判断。

源码实现会同步调用 `IHintManager` 获取结果，调用路径带 binder 往返成本，不适合放在每帧热点路径里轮询。游戏或重计算场景可以把它当作降档辅助信号，再配合 FrameTimeline、Perfetto 和温控日志做交叉判断。

[已验证: 官方文档, developer.android.com/reference/android/os/health/SystemHealthManager]
[已验证: AOSP, android-16.0.0_r1 frameworks/base/core/java/android/os/health/SystemHealthManager.java]

### JobScheduler 配额优化

Android 16 调整了 `JobScheduler` 的配额计算方式，基于 App 的 standby bucket 和是否以前台服务启动来动态调整运行时间配额。新增的 `getPendingJobReasons()` 和 `getPendingJobReasonsHistory()` API 让开发者可以查询 Job 未执行的具体原因（如待机桶限制、电量不足、网络不可用等），不再只能靠猜测。

[已验证: 官方文档, developer.android.com/about/versions/16/behavior-changes-16#jobscheduler]

## 新增性能 API 的演进脉络

上面按版本走了一遍关键变更。现在我们换个视角，按 API 家族纵向梳理它们的演进路径，帮助你理解 Google 在每个性能领域的设计意图。

### FrameMetrics 演进

`FrameMetrics` 在 Android 7.0（API 24）引入，提供了帧渲染各阶段的耗时数据。此后各个版本的改进如下：

在 Android 12-15 期间，`FrameMetrics` 类本身没有新增字段。但周边的渲染管线持续演进——Android 13 的 `Choreographer.VsyncCallback` 和 `FrameTimeline` 提供了更丰富的帧调度信息，Android 14 的缓存冻结减少了后台进程对帧渲染的干扰，Android 15 的 ADPF 省电模式让系统在调度时有了更多选择。

Android 16 是 `FrameMetrics` 的一次实质更新：`FRAME_TIMELINE_VSYNC_ID` 字段让帧追踪跨越了 App↔SurfaceFlinger 的边界。配合 `Choreographer` 的多时间线选择（API 33 引入），开发者现在可以精确知道：我选了哪条时间线渲染这一帧，这一帧最终在 SurfaceFlinger 端是否按时合成。

[已验证: 官方文档, developer.android.com/reference/android/view/FrameMetrics]

### ProfilingManager 演进

`ProfilingManager` 是 Android 近几年在性能工具链上的重点投入。它的演进路径很清楚：

**Android 15（API 35）**：基础 API。App 可以手动请求 heap dump、stack sample 和 system trace，采集数据保存在 App 的 data 目录。

**Android 16（API 36）**：系统触发式 profiling 进入公开 API。公开参考页里的 API 36 触发器包括 `TRIGGER_TYPE_ANR` 和 `TRIGGER_TYPE_APP_FULLY_DRAWN`。

**Android 17（API 37）**：触发类型继续扩展，公开参考页新增 `TRIGGER_TYPE_COLD_START`、`TRIGGER_TYPE_OOM`、`TRIGGER_TYPE_KILL_EXCESSIVE_CPU_USAGE` 和 `TRIGGER_TYPE_APP_COMPAT`。冷启动场景从 `reportFullyDrawn()` 时点前移到“尽早捕获冷启动路径”，触发器边界也更完整。

[已验证: 官方文档, developer.android.com/reference/android/os/ProfilingManager ; developer.android.com/reference/android/os/ProfilingTrigger]

### ADPF / Dynamic Performance 演进

ADPF（Android Dynamic Performance Framework）从 Android 12 开始逐步构建，是 Google 让 App 参与系统性能调度的核心框架：

**Android 12**：引入 Performance Hint API，App 可以告诉系统"我接下来有重负载"。引入 Game Mode API，用户可选择性能优先或省电优先。

**Android 13**：引入 Game State API，App 可以告诉系统当前状态（加载中/游戏中/后台），帮助系统做更智能的资源分配。

**Android 14**：ADPF 在更多厂商设备上得到支持（如 UNISOC），框架的可用性从旗舰 SoC 扩展到中低端平台。

**Android 15**：Hint session 支持省电模式，可同时报告 GPU 和 CPU 工作时长。

**Android 16**：`android.os.health.SystemHealthManager` 中加入 CPU / GPU headroom 查询接口，`Display` 中也出现了 `hasArrSupport()` / `getSuggestedFrameRate()` 这组 ARR 相关入口。它们在 android-16.0.0_r1 里都带 feature flag，是否可用还取决于 framework 开关和设备实现，迁移代码时要先做 API level 与能力探测。

[已验证: 官方文档, developer.android.com/reference/android/os/health/SystemHealthManager ; developer.android.com/reference/android/view/Display]
[已验证: AOSP, android-16.0.0_r1 frameworks/base/core/java/android/view/Display.java]

### Choreographer 演进

Choreographer 的 API 演进是理解 Android 渲染调度演进的最佳切入点：

**API 16（Android 4.1, Project Butter）**：引入 `FrameCallback`，首次让 App 能接收 VSync 回调。doFrame 按固定顺序执行回调：INPUT → ANIMATION → INSETS_ANIMATION → TRAVERSAL → COMMIT。

**API 24（Android 7.0）**：NDK 端 Choreographer 可用，Native 代码可直接接收 VSync 回调。

**API 30（Android 11）**：引入刷新率回调，App 可以感知屏幕刷新率变化。

**API 33（Android 13）**：引入 `VsyncCallback`，提供多帧时间线选择。这是 Frame Pacing 的基础——App 可以选择一个合适的呈现时间，而不是盲目追赶下一个 VSync。

**Android 16（API 36）**：与帧率策略相关的新增接口更多落在 `Display`，例如 `hasArrSupport()` / `getSuggestedFrameRate()`。这组 ARR 接口仍带 flag，只有系统打开功能且设备实现支持时才可用。

[已验证: 官方文档, developer.android.com/reference/android/view/Display]
[已验证: AOSP, android-16.0.0_r1 frameworks/base/core/java/android/view/Display.java]

## 废弃 API 与替代方案

以下是 Android 12-16 中与性能分析直接相关的废弃 API，以及推荐替代方案：

### onBackPressed() → OnBackInvokedDispatcher

`onBackPressed()` 从 Android 13 开始被标记为废弃，Android 16 进一步强化了 Predictive Back 的默认启用。如果你的 App 依赖 `onBackPressed()` 处理返回逻辑，在 Android 16+ 上可能遇到返回动画和手势行为不一致的问题。

替代方案：使用 `OnBackInvokedDispatcher` 注册 `OnBackInvokedCallback`。如果你需要观察（但不拦截）系统返回事件，使用 `PRIORITY_SYSTEM_NAVIGATION_OBSERVER` 优先级。

[已验证: 官方文档, developer.android.com/guide/navigation/custom-back/predictive-back]

### WebView.setForceDark() → prefers-color-scheme

Android 13 废弃了 `WebView.setForceDark()`。对于 Web 内容的深色模式渲染，WebView 现在会根据 App 的 `isLightTheme` 属性自动设置 `prefers-color-scheme` CSS 媒体查询。如果你的 App 手动调用了 `setForceDark()`，在 Android 13+ 上调用无效，需要改为通过主题设置。

[已验证: 官方文档, developer.android.com/about/versions/13/behavior-changes-13#webview-force-dark]

### windowOptOutEdgeToEdgeEnforcement → 正确处理 insets

Android 16 移除了 `windowOptOutEdgeToEdgeEnforcement` 属性。如果你的 App 之前用这个属性来避免边到边显示带来的 UI 遮挡问题，现在必须正确处理 WindowInsets。从性能角度看，正确的 insets 处理避免了不必要的布局重算——错误处理 insets 会导致 `measure()` 和 `layout()` 被触发多次。

[已验证: 官方文档, developer.android.com/about/versions/16/behavior-changes-16#edge-to-edge]

### elegantTextHeight → 废弃

Android 16 废弃了 `elegantTextHeight` 属性，在 targetSdkVersion 36+ 上该属性被忽略。如果你的布局依赖这个属性来控制文本高度，需要测试在 Android 16 上的实际显示效果。

[已验证: 官方文档, developer.android.com/about/versions/16/behavior-changes-16]

## targetSdkVersion 升级的性能影响

每次提升 `targetSdkVersion`，你的 App 就会进入新版本的行为约束框架。以下是按版本梳理的性能相关影响清单。

### 升级到 targetSdkVersion 31（Android 12）

- 后台不能启动前台服务：检查所有从后台调用 `startForegroundService()` 的路径，改用 `WorkManager`。
- 精确闹钟需要权限：如果使用了 `AlarmManager.setExact()` 系列，声明 `SCHEDULE_EXACT_ALARM` 权限或改用非精确闹钟。
- 通知跳板被禁用：通知的点击处理必须直接启动 Activity。

### 升级到 targetSdkVersion 33（Android 13）

- 需要请求 `POST_NOTIFICATIONS` 权限：如果通过通知展示性能数据或 ANR 告警。
- `WebView.setForceDark()` 调用无效：检查是否有相关代码。

### 升级到 targetSdkVersion 34（Android 14）

- 前台服务必须声明类型：逐个检查所有 `startForeground()` 调用点，补充 `foregroundServiceType` 声明和对应权限。
- `shortService` 类型有 3 分钟超时 + `onTimeout()` 回调：如果使用此类型，实现超时处理。
- JobScheduler 反复 ANR 会被降级：确保 `onStartJob()` 不做耗时操作。
- 缓存 App 广播队列化：如果依赖实时广播触发后台性能采集，改为前台触发或 `WorkManager`。
- Android 14 设备不允许安装 `targetSdkVersion < 23` 的新包；已安装旧包保留，测试旧包可通过 `adb install --bypass-low-target-sdk-block` 绕过。这个限制是系统安装限制，不是 Google Play 上架门槛。

### 升级到 targetSdkVersion 35（Android 15）

- Android 15 设备不允许安装 `targetSdkVersion < 24` 的新包；Google Play target API 要求按当年 Play 政策单独检查，例如 2025-08-31 起新应用和更新需 target Android 15（API 35）或更高。
- `dataSync` 和 `mediaProcessing` 前台服务有 6 小时上限：检查是否有超过此时长的任务。
- `FLAG_STOPPED` 状态变化：被强制停止的 App 的状态会持续到用户主动重新打开。
- 16KB 页面大小：如果使用 NDK 库，需要重新编译。

### 升级到 targetSdkVersion 36（Android 16）

- 大屏设备忽略方向和宽高比限制：如果你的 App 是固定方向的，需要测试在大屏设备上的表现，确保 `onConfigurationChanged()` 正确处理。
- Predictive Back 默认启用：检查返回手势的处理是否使用了 `onBackPressed()`，如果是，迁移到 `OnBackInvokedDispatcher`。
- `windowOptOutEdgeToEdgeEnforcement` 被移除：处理 WindowInsets。
- `elegantTextHeight` 被废弃：检查文本布局。
- Intent 重定向保护增强：检查是否有通过 `PendingIntent` 或 `Intent` 传递组件名的代码。

[已验证: 官方文档, 各版本 behavior-changes 页面]

## 在 Perfetto 中的表现

了解版本差异对 Perfetto 分析有直接帮助。以下是一些关键的可观测变化：

**缓存 App 冻结（Android 14+）**：在 Perfetto 的 CPU 视图中，被冻结的 App 进程的线程状态会变为 "S"（Sleeping）且长时间不变化。你不会看到这些进程的任何 CPU 活动，直到用户重新打开 App。

**前台服务超时（Android 14+）**：`shortService` 类型的前台服务超时后，在 Perfetto 中你会看到 Service 的 `onTimeout()` 被调用（如果 App 有对应 trace 点），随后可能看到 ANR 事件。

**系统触发式 Profiling（Android 16+）**：当 `ProfilingManager` 的触发器被激活时，在 Perfetto 中你会看到系统自动开始和结束 trace 采集的标记。这些 trace 文件可以在 `ui.perfetto.dev` 中分析。

**Predictive Back（Android 16+）**：在 Perfetto 的 Input Track 中，你会看到 back 手势的处理时间线变长——系统在手势进行中就开始准备目标 Activity 的布局，而不是等到手势完成后才触发。

## 与其他机制的关系

本节内容与全书的多个章节交叉关联：

- **§1.6 Android 版本演进中的架构变化**：从架构层面追踪版本变化，本节侧重性能相关的 API 和行为变更。
- **§2.9 渲染机制的版本演进**：Choreographer 和 FrameMetrics 的演进细节。
- **§4.6 内存相关的版本演进**：16KB 页面大小、ART GC 演进等。
- **§5.7 CPU 相关的版本演进**：EEVDF 调度器、UClamp 等系统级变化。
- **§6.4 存储相关的版本演进**：文件系统和 I/O 调度的版本变化。
- **§9.2 ANR 类型与触发条件**：前台服务 ANR 超时的版本演进。
- **§13.1 Perfetto 简介与演进**：ProfilingManager 产生的 trace 如何在 Perfetto 中分析。
- **§14.7 ProfilingManager**：ProfilingManager 的完整使用指南。

## 常见问题与误区

### "升级 targetSdkVersion 不会影响性能"

这是一个危险的假设。每个版本的 behavior changes 都可能改变系统对 App 后台活动、进程管理、前台服务的约束。即使你的代码没变，App 在新系统上的性能表现也可能因为系统行为变化而不同。建议每次升级 targetSdkVersion 后，做一轮完整的性能回归测试。

### "新 API 在低版本设备上不能用就不集成"

ADPF、ProfilingManager、ApplicationStartInfo 等新 API 都设计为增量可用的——你可以在高版本设备上使用它们获取更好的性能数据，同时保持低版本设备的基本功能。推荐的做法是使用 `Build.VERSION.SDK_INT` 检查后优雅降级，而不是完全放弃新 API。

### "缓存 App 冻结等于 App 被杀"

不是。冻结（freeze）和被杀（kill）是完全不同的状态。冻结只是暂停了 App 的 CPU 执行，进程的内存空间还在。当 App 回到前台时，从冻结恢复比从被杀恢复快得多（不需要重新 fork Zygote、初始化 ART、加载 classes）。在 Perfetto 中，冻结的进程仍然存在，只是没有任何 CPU 活动。

### "Predictive Back 只影响动画，和性能无关"

Predictive Back 要求 App 在手势阶段就准备好目标 UI。如果你的返回目标需要重新加载大量数据或执行复杂布局，Predictive Back 的"预准备"阶段可能成为新的性能瓶颈。这类问题不属于传统卡顿（用户看不到帧丢失），更接近手势响应不够流畅。

### "ProfilingManager 能替代 adb 抓取 Perfetto"

不能完全替代。`ProfilingManager` 目前支持的 trace 类型有限（system trace、heap dump、stack sample），而且采集范围主要由系统控制。对于需要精细配置的 Perfetto 抓取（如自定义 data source、特定的 buffer size），`adb perfetto` 仍然是不可替代的。`ProfilingManager` 的优势在于**线上**和**自动触发**，不是开发阶段的替代品。

## 参考资料

### 官方文档
- Android 12 Behavior Changes: developer.android.com/about/versions/12/behavior-changes-12
- Android 13 Behavior Changes: developer.android.com/about/versions/13/behavior-changes-13
- Android 14 Behavior Changes: developer.android.com/about/versions/14/behavior-changes-14
- Android 15 Behavior Changes: developer.android.com/about/versions/15/behavior-changes-15
- Android 16 Behavior Changes: developer.android.com/about/versions/16/behavior-changes-16
- ProfilingManager API Reference: developer.android.com/reference/android/os/ProfilingManager
- ProfilingTrigger API Reference: developer.android.com/reference/android/os/ProfilingTrigger
- ApplicationStartInfo API Reference: developer.android.com/reference/android/app/ApplicationStartInfo
- SystemHealthManager API Reference: developer.android.com/reference/android/os/health/SystemHealthManager
- Display API Reference: developer.android.com/reference/android/view/Display
- Choreographer API Reference: developer.android.com/reference/android/view/Choreographer
- FrameMetrics API Reference: developer.android.com/reference/android/view/FrameMetrics
- ADPF Documentation: developer.android.com/topic/performance/adpf
- Predictive Back Guide: developer.android.com/guide/navigation/custom-back/predictive-back
- Game Mode API: developer.android.com/about/versions/12/features/game-mode

### AOSP 源码路径
- ProfilingManager: packages/modules/Profiling/framework/java/android/os/ProfilingManager.java
- SystemHealthManager: frameworks/base/core/java/android/os/health/SystemHealthManager.java
- Display: frameworks/base/core/java/android/view/Display.java
- ApplicationStartInfo: frameworks/base/core/java/android/app/ApplicationStartInfo.java
- Choreographer: frameworks/base/core/java/android/view/Choreographer.java
- FrameMetrics: frameworks/base/core/java/android/view/FrameMetrics.java
- ActiveServices (前台服务超时): frameworks/base/services/core/java/com/android/server/am/ActiveServices.java

### 研究素材
-
-
-
-
-
-
-
-
### Android15适配之targetSdkVersion升到35后全是坑
- 来源：https://juejin.cn/post/7584295332340858943
- 类型：技术文章
- 摘要：详尽记录将 targetSdkVersion 升级到 35（Android 15）过程中遇到的所有适配问题。涵盖隐私变更、前台服务类型强制分类、16KB 页面大小对 native 库的影响。
- 入库时间：2026-04-06
### Android 17 有什么需要适配的？
- 来源：https://juejin.cn/post/7610233341305389099
- 类型：技术文章
- 摘要：Android 17 官方适配文档解读：隐私沙箱要求、更严格的后台限制、Predictive Back强制适配、禁止侧载政策详解。
- 入库时间：2026-04-06
### 了解一下Android16更新事项
- 来源：https://juejin.cn/post/7595053284915822632
- 类型：技术文章
- 摘要：Android 16 主要更新事项：照片权限细分、Notification权限、后台服务限制、预测性返回手势。
- 入库时间：2026-04-06

## 附录：Android 16 ART Generational CMC / userfaultfd GC 机制源码调研

**调研时间**：2026-05-18
**来源选题**：daily-topics.json id=4

### 关键源码发现

**DeviceConfig 属性名**：`enable_uffd_gc_2`（非题目中的 gUseUserfaultfd）

```cpp
// art/runtime/gc/heap.cc DeviceConfig 读取逻辑
bool phenotype_enable = GetCachedBoolProperty(
    cached_properties, "persist.device_config.runtime_native_boot.enable_uffd_gc_2", false);
bool phenotype_force_disable = GetCachedBoolProperty(
    cached_properties, "persist.device_config.runtime_native_boot.force_disable_uffd_gc", false);
bool build_enable = GetBoolProperty("ro.dalvik.vm.enable_uffd_gc", false);
return (phenotype_enable || build_enable) && !phenotype_force_disable;
```

**版本历史**：
- Android T（API 33）+：CMC GC 默认启用（需要 kernel userfaultfd 支持）
- Android S（API 31）+：CMC GC 扩展为默认启用（commit 854cb7d）

**userfaultfd 用途**：ART runtime 利用 Linux userfaultfd 系统调用在 GC 压缩期间延迟复制页面，实现并发压缩而不 stop-the-world。

**信息源**：AOSP platform/art commit 854cb7d、8222aa2d；platform/build commit 53dd895
