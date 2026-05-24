---
title: "Android 17 DeliQueue 与 RecyclerView 预取时序优化"
chapter: "22.16"
section: "22.16"
status: ready-for-review
applicable_versions: "Android 11 (API 30) - Android 17 (API 37); DeliQueue targetSdkVersion >= 37"
drafted_date: "2026-05-24"
last_verified: "2026-05-24"
last_verified_against: "Android Developers MessageQueue behavior change page + Android Developers Blog 2026-02-17 + AndroidX RecyclerView API docs"
confidence: medium
tags: [recyclerview, deliqueue, messagequeue, android17, jank, rendering]
related_chapters: ["1.13", "7.8", "13.14", "19.11", "22.2"]
created_by: "task2a-knowledge-gap"
created_date: "2026-05-24"
gap_source: "研究素材/官方文档/章节深挖/Clippings结构参考"
gap_score: 18
material_count: 5
sources:
  - type: official
    path: "https://developer.android.com/about/versions/17/changes/messagequeue"
  - type: official
    path: "https://developer.android.com/blog/posts/under-the-hood-android-17-lock-free-message-queue"
  - type: official
    path: "https://developer.android.com/reference/androidx/recyclerview/widget/RecyclerView.LayoutManager"
  - type: official
    path: "https://developer.android.com/reference/androidx/recyclerview/widget/LinearLayoutManager"
  - type: research
    path: "DeepResearch/2026-05-24-android17-deli-queue-recyclerview-prefetch.md"
  - type: research
    path: "DeepResearch/2026-05-23-android17-deliqueue-messagequeue-recyclerview.md"
  - type: clippings-structure
    path: "[结构参考: Clippings/Android 性能优化 - 任务调度优化：线程+CPU，提升任务调度优先级.md]"
  - type: clippings-structure
    path: "[结构参考: Clippings/Android 性能优化 - CPU 优化（下）：减少 CPU 闲置时刻和等待，提升利用率.md]"
---

# 22.16 Android 17 DeliQueue 与 RecyclerView 预取时序优化

<!-- outline-start -->
## 要点

### 🔹 问题边界：列表卡顿里的 MessageQueue 锁竞争
区分 RecyclerView 自身布局/绑定耗时、GapWorker 预取命中率、后台线程 `Handler.post()` 造成的主线程队列竞争，避免把所有滑动卡顿都归因到 RecyclerView。

### 🔹 Android 17 DeliQueue 的生效条件
梳理 `targetSdkVersion >= 37`、旧 target 兼容行为、`MessageQueue.mMessages` 反射兼容风险，以及上线前需要覆盖的回归场景。

### 🔹 GapWorker、postFromTraversal 与预取 deadline
说明 GapWorker 的预取机制本身没有变，DeliQueue 改善的是消息入队和主线程取消息的等待成本，重点观察 prefetch deadline 是否被主线程队列延迟拖垮。

### 🔹 Perfetto 取证：从 monitor contention 到帧时间线
建立取证路径：`android.monitor_contention`、FrameTimeline、RecyclerView trace section、自定义 `Trace.beginSection()` 和 JankStats，判断锁等待、绑定耗时、布局耗时和 GPU/HWC 降级分别占多少。

### 🔹 业务线程投递治理
把参考书中的线程优先级、CPU 空闲利用和等待时间思路转成列表场景实践：减少后台线程集中投递、控制主线程回调批量、分离高频 UI 更新和低优先级数据刷新。

### 🔹 Android 17 适配与灰度验证
设计 targetSdk 36/37 对照实验，覆盖大列表快速滑动、DiffUtil 批量更新、图片加载回调、数据库分页、弱网回包和混合 Compose/View 列表。

## 扩展

### 🔸 与 1.13 MessageQueue 机制章节的关系
机制细节放在 1.13，本节只保留应用侧排查、验证和灰度动作。

### 🔸 与 13.14 Perfetto DataGrid / Jank CUJ 的关系
第三方 App 不能直接依赖系统 CUJ 标准库，需要结合 JankStats、自定义 trace section 和 FrameTimeline 还原列表场景。

### 🔸 与 22.2 RecyclerView 最佳实践的关系
22.2 负责通用优化动作，本节聚焦 Android 17 队列实现变化带来的新排障入口。

<!-- outline-end -->

RecyclerView 卡顿排查经常停在 `onBindViewHolder()`、布局层级和图片加载上。Android 17 以后还要补一个入口：主线程消息队列自身的等待成本。`GapWorker` 仍然按原来的方式预取，变化发生在 `recyclerView.post(this)` 到主线程开始执行之间。

这一节只处理应用侧问题：怎么识别队列锁竞争，怎么确认 DeliQueue 是否生效，怎么把 RecyclerView 预取、业务线程投递和灰度验证放到同一组实验里。DeliQueue 内部数据结构详见 1.13 节，本节不重复展开。

## 问题边界：列表卡顿里的 MessageQueue 锁竞争

列表滑动慢通常落在四类位置：主线程布局和绑定太重，GapWorker 预取没有赶上，后台线程密集投递主线程回调，渲染提交或合成阶段超时。DeliQueue 只影响第三类的一部分，也就是多个线程围着同一个 `MessageQueue` 入队和出队时产生的等待。

旧 `MessageQueue` 使用一把 monitor 保护内部链表。后台线程通过 `Handler.post()` 把网络结果、数据库分页结果或图片加载完成回调投到主线程时，要进入同一段同步区域；主线程回到 `next()` 取下一条消息时，也会碰到这把锁。后台线程先拿到锁，主线程就可能在帧预算内多等几百微秒到几毫秒。列表里这种等待最容易和 `onBindViewHolder()`、`RV OnLayout` 混在一起。

排查时先把三段时间分开：

- 队列口等待：Perfetto 里出现主线程被 `MessageQueue` 相关 monitor 阻塞，或者 `Handler.post()` 高峰和掉帧同一时间段出现。
- 预取执行：`RV Prefetch` 后面是否跟着 `RV onCreateViewHolder type=...`、`RV onBindViewHolder type=...`，以及这些 slice 是否在 deadline 之前完成。
- 帧提交：FrameTimeline 显示 App deadline、SurfaceFlinger deadline、Late Present 或 Buffer Stuffing 等类型时，继续按 7.2 和 13.14 的取证路径查渲染和合成。

[结构参考: Clippings/Android 性能优化 - 任务调度优化：线程+CPU，提升任务调度优先级.md] 这类资料的价值在于提醒排查时不要只看单个函数耗时，还要看任务优先级和等待关系。本节不采用其中的线程提权和绑核方案作为通用建议；普通应用盲目提高 UI 相关线程优先级，容易挤压系统服务、图片解码和 I/O 线程，收益也难复现。

## Android 17 DeliQueue 的生效条件

Android 17 的公开行为变更页面给出的边界很清楚：运行在 Android 17 上、并且 `targetSdkVersion >= 37` 的应用，会收到新的 lock-free `android.os.MessageQueue` 实现。[已验证: 官方文档, developer.android.com/about/versions/17/changes/messagequeue]

旧 target 应用仍按兼容路径运行。这个边界很适合做 A/B：同一台 Android 17 设备上，用 target 36 和 target 37 两个构建包对照同一组滑动场景，观察 `MessageQueue` contention、FrameTimeline、JankStats 和业务埋点的变化。

DeliQueue 对兼容性的影响集中在反射。官方文档说明，Android 17 为了二进制兼容仍保留 `MessageQueue.mMessages` 字段，但在新实现中这个字段始终为 null。依赖 `mMessages` 链表判断主线程 idle、读取待处理消息或实现测试同步的库，需要升级到公开 API 路径。[已验证: 官方文档, developer.android.com/about/versions/17/changes/messagequeue]

灰度前至少查三类依赖：

- UI 自动化测试：Espresso、Robolectric、公司内部 idle 检测库是否仍反射 `mMessages`。
- 性能监控 SDK：是否通过反射遍历 `MessageQueue` 来推断 `doFrame` 前后消息。
- 业务工具库：是否在 Debug 面板、慢消息检测或 ANR 辅助工具里读取私有字段。

Android 17 还提供兼容开关，适合定位问题归因。遇到 target 37 后才出现的测试挂起或列表行为差异，可以用 `adb am compat disable USE_NEW_MESSAGEQUEUE <package>` 暂时退回旧实现，再复测同一条脚本。[已验证: 官方文档, developer.android.com/about/versions/17/changes/messagequeue]

这条命令只用于验证 MessageQueue 归因，不能当成发布策略：

```bash
adb am compat disable USE_NEW_MESSAGEQUEUE com.example.app
adb am compat enable USE_NEW_MESSAGEQUEUE com.example.app
```

如果关闭开关后问题消失，下一步应定位反射、idle 判断或主线程投递节奏里的具体依赖点；target 37 仍要按发布计划完成适配。

## GapWorker、postFromTraversal 与预取 deadline

RecyclerView 的预取路径没有因为 DeliQueue 改成新的 API。滚动过程中，RecyclerView 会记录滚动方向和距离，并把 `GapWorker` 作为 Runnable 投递到主线程。通用机制见 22.2 和 7.8；本节只看它和消息队列等待的关系。

`GapWorker` 能不能帮上忙，取决于两个条件。请求要及时到达主线程，随后 create/bind 要在剩余预算内完成。DeliQueue 改善的是前者：减少后台线程投递消息时和主线程取消息时的锁等待。它不会让 `onBindViewHolder()` 变短，也不会改变 `willCreateInTime()` / `willBindInTime()` 的预算判断。

AndroidX 文档对 prefetch 的边界有两处能直接落到实战：`collectInitialPrefetchPositions()` 只在嵌套 RecyclerView 将要进入屏幕时调用，LayoutManager 通过 `LayoutPrefetchRegistry.addPosition()` 提交要提前准备的位置；`LinearLayoutManager.setInitialPrefetchItemCount()` 建议把数量设为内层列表首次可见时会展示的 item 数，设得超过可见数量会增加无意义的 bind 和 View 创建。[已验证: 官方文档, developer.android.com/reference/androidx/recyclerview/widget/RecyclerView.LayoutManager] [已验证: 官方文档, developer.android.com/reference/androidx/recyclerview/widget/LinearLayoutManager]

排查时不要把 `setInitialPrefetchItemCount()` 当成越大越好。它只是增加候选 position，最终能执行多少还要看 deadline。如果列表 item 复杂、图片占位创建重、payload 没做局部刷新，GapWorker 可能拿到更多候选，却在预算判断处提前停下。Android 17 降低队列等待后，这类问题会更暴露：队列口不再等了，剩下的慢点会集中落到 create/bind 和布局里。

[自动发现] 对混合 Compose/View 列表，DeliQueue 只能改善主线程消息调度。`ComposeView` 的 composition、measure 和 state 更新仍要单独埋点。用同一个 RecyclerView trace 看不出 Compose 内部重组成本时，应在 item 内部加 `Trace.beginSection()`，或结合 Compose tooling 和 JankStats state 标记。

## Perfetto 取证：从 monitor contention 到帧时间线

DeliQueue 官方博客建议用 Perfetto 分析锁竞争，并给出了 `android.monitor_contention` 模块的方向。对 RecyclerView 场景，取证顺序可以压成四步。[已验证: 官方博客, developer.android.com/blog/posts/under-the-hood-android-17-lock-free-message-queue]

一是确认主线程是否在队列口等待。下面这段 SQL 的用途是找主线程被 `MessageQueue` 相关 monitor 阻塞的总时长和次数，适合先在 target 36 包上跑一遍，再和 target 37 包对照：

```sql
INCLUDE PERFETTO MODULE android.monitor_contention;

SELECT
  process_name,
  SUM(dur) / 1000000.0 AS blocked_ms,
  COUNT(*) AS blocked_count
FROM android_monitor_contention
WHERE is_blocked_thread_main
  AND short_blocked_method LIKE '%MessageQueue%'
GROUP BY process_name
ORDER BY blocked_ms DESC;
```

如果 target 37 后这组数据明显下降，但 jank 没有下降，说明瓶颈已经转移到队列之后。

二是定位 RecyclerView 自身切片。当前 AndroidX 常见 trace section 包括 `RV Prefetch`、`RV onCreateViewHolder type=...`、`RV onBindViewHolder type=...`、`RV FullInvalidate`、`RV PartialInvalidate`、`RV OnLayout`。缺少这些 slice 时，要检查是否打开了应用 trace、是否走到 RecyclerView 路径，以及列表 item 内部是否被 Compose、自定义 View 或图片库包住。

三是对齐 FrameTimeline。FrameTimeline 负责告诉这帧晚在哪里：App 端提交晚、SurfaceFlinger 端处理晚、Present 晚，还是 Buffer Stuffing。不要用不存在的字段做 SQL 条件；按 13.14 的字段口径查 `actual_frame_timeline_slice` 的 `jank_type`、`present_type`、`on_time_finish`、`layer_name` 等公开字段，再回到线程轨道查原因。

四是补业务状态。JankStats 适合把线上样本按页面、列表类型、网络状态、图片来源、DiffUtil 批量大小分组。第三方 App 不能假设系统 CUJ 标准库会自动给出业务列表场景名，state 需要应用自己维护。详见 19.11。

如果要观察系统进程里的 MessageQueue tracing，官方博客给出的 Perfetto 配置使用 `track_event` 的 `mq` category。应用侧排查优先用 monitor contention、RecyclerView section 和自定义 trace，不要把 system_server 的配置当成普通 App SDK 能力。[已验证: 官方博客, developer.android.com/blog/posts/under-the-hood-android-17-lock-free-message-queue]

## 业务线程投递治理

DeliQueue 减少队列锁等待，不等于后台线程可以无节制向主线程投递。投递量过大时，主线程仍要逐条分发消息，`dispatchMessage()` 之后的业务代码仍会占用帧预算。参考书里关于“减少等待”和“利用 CPU 空闲窗口”的思路，可以转成列表场景里的三条规则。[结构参考: Clippings/Android 性能优化 - CPU 优化（下）：减少 CPU 闲置时刻和等待，提升利用率.md]

- 合并同一帧内的 UI 回调：分页、图片状态、点赞状态、曝光上报不要各自 `post` 一次；用单个主线程 drain 把本帧变化合并成最小 adapter 更新集。
- 限制低优先级刷新：弱网回包、推荐理由、非首屏装饰信息可以等滑动停止或进入 idle 后刷新；不要和快速 fling 期间的 `GapWorker` 抢主线程分发时间。
- 把 diff 和预处理留在后台：`DiffUtil.calculateDiff()`、图片尺寸计算、富文本预解析应在后台完成，主线程只接收结果和最小 payload。

下面的示例展示一种合并投递方式。重点在于让多个后台来源共享一次主线程 drain，减少队列消息数量：

```kotlin
class MainThreadBatcher(
    private val mainHandler: Handler,
    private val apply: (List<ListMutation>) -> Unit,
) {
    private val pending = ConcurrentLinkedQueue<ListMutation>()
    private val scheduled = AtomicBoolean(false)

    fun enqueue(mutation: ListMutation) {
        pending.add(mutation)
        if (scheduled.compareAndSet(false, true)) {
            mainHandler.post {
                val batch = buildList {
                    while (true) {
                        val item = pending.poll() ?: break
                        add(item)
                    }
                }
                scheduled.set(false)
                if (batch.isNotEmpty()) apply(batch)
            }
        }
    }
}
```

这段代码把多个后台线程的结果合并成一个主线程消息。真实工程里还要补生命周期取消、最大批次大小、滑动中降级策略和线程安全测试。

线程优先级治理要谨慎。`Process.setThreadPriority()` 可以让关键后台任务更快结束，但不要把图片解码、数据库和网络回调都提到显示线程等级。列表场景里更常见的有效动作，是降低非首屏预热、日志、埋点和低优先级刷新任务的竞争强度，把主线程消息数量压下来。

## Android 17 适配与灰度验证

target 37 灰度不要只看总掉帧率。官方博客给出的收益数字来自 Google 的合成基准和内部 beta tester trace：高竞争插入忙队列最高提升 5000 倍，主线程锁竞争时间下降 15%，应用 missed frames 下降 4%，System UI 和 Launcher 交互 missed frames 下降 7.7%，首帧 P95 下降 9.1%。这些数字能作为预期方向，不能直接写进业务 OKR。[已验证: 官方博客, developer.android.com/blog/posts/under-the-hood-android-17-lock-free-message-queue]

灰度实验建议按下面的表格跑：

| 场景 | 对照组 | 观察指标 | 通过标准 |
| --- | --- | --- | --- |
| 大列表快速 fling | target 36 vs target 37 | `MessageQueue` contention、`RV Prefetch` 命中、JankStats 慢帧率 | contention 下降后，慢帧不因 bind/layout 反弹 |
| DiffUtil 批量更新 | 小批量 payload vs 整表刷新 | `RV PartialInvalidate` / `RV FullInvalidate`、主线程消息数 | target 37 只改善队列等待，不掩盖整表刷新问题 |
| 图片加载完成回调 | 单图回调 vs 批量 drain | 主线程 post 数、`onBind` 后图片设置耗时 | 快速滑动期间低优先级图片状态不挤占帧预算 |
| 数据库分页 | 弱网/慢查询回包 | 页面状态、adapter 更新批次、FrameTimeline | 回包集中到达时没有主线程消息风暴 |
| 混合 Compose/View item | ComposeView item vs 纯 View item | 自定义 trace、JankStats state、`RV OnLayout` | DeliQueue 收益和 composition 成本分开统计 |

上线前保留两组开关：一组控制 target 37 构建的兼容开关验证，另一组控制业务侧批量投递策略。前者验证平台变更归因，后者控制应用逻辑风险。两组开关分开，问题定位会更快。

## 与相关章节的关系

1.13 负责解释 MessageQueue、同步屏障、DeliQueue 数据结构和兼容风险。本节只引用生效条件、反射影响和 Perfetto 入口，避免重复写机制。

22.2 负责 RecyclerView 通用实践：ViewHolder 复用、DiffUtil、payload、预取数量、共享 `RecycledViewPool`。本节的判断都建立在这些基础优化已经完成之后；如果 22.2 的清单没过，DeliQueue 很难救回列表体验。

13.14 和 19.11 负责工具口径。Perfetto 用来定位一帧晚在哪里，JankStats 用来给线上帧附业务状态。第三方 App 做不到系统 CUJ 那种完整标注时，就用自定义 trace section 和 state 把列表场景补齐。

## 收束

Android 17 DeliQueue 给 RecyclerView 带来的变化，是减少 `GapWorker` 和业务回调进入主线程前的队列等待；预取算法本身仍沿用 AndroidX 路径。排查时按队列口、RecyclerView create/bind/layout、FrameTimeline 三段拆开，target 37 的收益和应用自身的列表成本才不会混在一起。
