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
related_chapters: ["1.13", "7.8", "13.13", "19.11", "22.2"]
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

RecyclerView 的滑动卡顿可能来自 item 创建与绑定、measure/layout、图片回调、主线程消息积压、线程调度或显示链路。Android 17 又改变了其中一小段：对 `targetSdkVersion >= 37` 的应用，平台默认启用无锁 `MessageQueue` 实现 DeliQueue，旧队列核心消息路径上的单一 Java monitor 不再参与生产者入队与 Looper 取消息。[Android 17 MessageQueue 行为变更](https://developer.android.com/about/versions/17/changes/messagequeue)｜[DeliQueue 技术说明](https://developer.android.com/blog/posts/under-the-hood-android-17-lock-free-message-queue)

源码与版本边界分为三层：

| 层级 | 锚点 | 用途 |
|---|---|---|
| Android 平台 | Android 17 / API 37 / `android-17.0.0_r1` | `CombinedDeliMessageQueue`、兼容开关、Looper 与 FrameTimeline |
| RecyclerView | `androidx.recyclerview:recyclerview:1.4.0` sources jar | `GapWorker`、预取 deadline、create/bind 预算和 trace section |
| Android common kernel | `android17-6.18-2026-06_r6` | 线程 Runnable、抢占和 CPU 调度现象；内核不实现 DeliQueue 或 RecyclerView |

RecyclerView 是独立发布的 AndroidX artifact，不能用 `android-17.0.0_r1` 代替它的版本。截至 2026-07-29，官方发布页仍把 1.4.0 列为稳定版，并已将 RecyclerView 标记为 maintenance mode。[RecyclerView release notes](https://developer.android.com/jetpack/androidx/releases/recyclerview)

DeliQueue 机制见 [1.13 MessageQueue 与 DeliQueue](../../part1-fundamentals/ch01-architecture/13-messagequeue-deliqueue.md)，RecyclerView 通用优化见 [7.8 RecyclerView 性能](../../part2-performance/ch07-smoothness/08-recyclerview-performance.md) 和 [22.2 RecyclerView 实战](02-recyclerview-practice.md)。这里聚焦一个应用侧问题：DeliQueue 改变了列表预取时序中的哪一段，怎样用对照实验避免错误归因。

## 问题边界：列表卡顿里的 MessageQueue 锁竞争

一帧列表工作可以按证据分成五段：

1. 后台线程通过 `Handler`、AsyncListDiffer、图片库或分页组件提交结果。
2. 主 Looper 从 `MessageQueue` 取消息并进入 `dispatchMessage()`。
3. RecyclerView 处理滚动、adapter update、create、bind 与 `GapWorker` 预取。
4. ViewRoot/HWUI 完成 traversal、绘制和 App Window buffer 提交。
5. SurfaceFlinger 采纳目标 buffer，完成合成与 present。

DeliQueue 只改变前两段中的队列数据结构。它不能缩短 `onBindViewHolder()`、item measure/layout、图片解码、GC、RenderThread 或 SurfaceFlinger 的工作。

legacy `MessageQueue` 用一个 monitor 保护按 `when` 排序的链表。生产者插入消息、Looper 取消息和部分维护操作都会进入该临界区。低优先级后台线程持锁期间若被其他 Runnable 线程抢占，主线程可能等待它继续运行并释放锁，形成优先级反转。Android 17 的 DeliQueue 把生产者提交改成 `MessageStack` 上的 CAS push，再由 Looper 独占的同步/异步 `MessageHeap` 按 `when` 与插入序号排序。

排查列表卡顿时，可以用下表先排除不受 DeliQueue 影响的路径：

| 证据 | 说明 | 后续方向 |
|---|---|---|
| 主线程出现 `monitor contention with ...`，阻塞方法指向 legacy `MessageQueue` | 队列 monitor 可能占用了帧预算 | 查 owner 线程、持锁调用点，并做兼容开关 A/B |
| `RV Prefetch` 很晚才开始，但没有 MessageQueue monitor contention | 可能是前序消息积压、长 callback 或主线程未获 CPU | 查 Looper 前序 slice、Runnable 状态与调度轨道 |
| create/bind slice 很长 | item 创建、绑定或数据转换超时 | 回到 ViewHolder、payload、对象分配和图片请求 |
| `RV OnLayout` 很长，prefetch create/bind 正常 | 预取没有覆盖 measure/layout | 优化 item 约束、尺寸稳定性与嵌套层级 |
| App SurfaceFrame 按期，DisplayFrame 或目标 layer present 超时 | 问题位于应用交帧之后 | 转到 SurfaceFlinger、GPU、HWC、buffer 和 fence |

线程优先级和绑核不适合作为列表卡顿的通用修复。随意提高图片、数据库或网络线程优先级，可能增加与主线程、RenderThread 和系统进程的 CPU 竞争。没有 scheduler trace、实验分组和功耗数据时，优先减少工作与投递量。

## Android 17 DeliQueue 的生效条件

Android 17 的默认启用条件包含运行平台与 target SDK：应用运行在 Android 17，且 `targetSdkVersion >= 37`。`android-17.0.0_r1` 的 [`CombinedDeliMessageQueue/MessageQueue.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/os/CombinedDeliMessageQueue/MessageQueue.java) 同时保留 DeliQueue 与 legacy 两条路径，`next()` 和 `enqueueMessage()` 根据进程启动时确定的选择进入对应实现。

兼容性 change id `USE_NEW_MESSAGEQUEUE` 的值是 `421623328L`，声明使用 `@EnabledAfter(targetSdkVersion = Build.VERSION_CODES.BAKLAVA)`。`BAKLAVA` 是 API 36，因此 “after” 对应 API 37。应用进程会在主 Looper 创建前收到并设置 DeliQueue 选择；切换兼容开关后必须重启进程。

DeliQueue 的兼容风险集中在私有实现依赖。Android 17 为二进制兼容保留 `MessageQueue.mMessages`，但 DeliQueue 路径中该字段始终为 `null`。反射它来判断 idle、遍历待处理消息或驱动测试同步的代码会得到错误结果。[MessageQueue 迁移说明](https://developer.android.com/about/versions/17/changes/messagequeue)

灰度前至少查三类依赖：

- UI 自动化测试：Espresso、Robolectric、内部 idle 检测库是否仍反射 `mMessages`。官方要求 Espresso 3.7.0+；Robolectric 应升级到 4.17+，并从 `@LooperMode(LEGACY)` 迁到 `@LooperMode(PAUSED)`。
- 性能监控 SDK：是否通过反射遍历 `MessageQueue` 来推断 `doFrame` 前后消息。
- 业务工具库：是否在 Debug 面板、慢消息检测或 ANR 辅助工具里读取私有字段。

下面的命令用于在可调试应用上切换实现并强制重启进程，以同一个 APK 做 A/B：

```bash
adb shell am compat enable USE_NEW_MESSAGEQUEUE com.example.app
adb shell am force-stop com.example.app

adb shell am compat disable USE_NEW_MESSAGEQUEUE com.example.app
adb shell am force-stop com.example.app
```

每次切换后使用同一条脚本重新冷启动并采集多份 trace。这个实验只隔离 MessageQueue 实现；target 36 与 target 37 两个 APK 的比较还会叠加其他 target 行为变更，适合升级回归，不能单独证明 DeliQueue 收益。兼容开关用于开发验证和故障隔离，应用不应依赖它作为长期产品配置。

## GapWorker、postFromTraversal 与预取 deadline

以下 `GapWorker.java` 和 `RecyclerView.java` 行为基于 `androidx.recyclerview:recyclerview:1.4.0` sources jar。该 source jar 的 SHA-256 为 `cad83357a7003b5903197be0494f6e8f6825fa1338ee6b09b06a8dea32a97cb8`，可从 [Google Maven](https://dl.google.com/dl/android/maven2/androidx/recyclerview/recyclerview/1.4.0/recyclerview-1.4.0-sources.jar) 复核。

`GapWorker.postFromTraversal()` 的行为包含两个细节：

- 第一次请求把 `GapWorker` 通过 `recyclerView.post(this)` 投到主线程队列，并用 `mPostTimeNs` 避免重复 post。
- 后续滚动即使没有新增 Runnable，也会更新 prefetch vector；`run()` 读取的是较新的方向与距离。

这次 `post()` 通常发生在主线程的滚动路径中。legacy 队列下，主线程入队也可能等待正持有 MessageQueue monitor 的后台生产者；DeliQueue 移除了这条核心 monitor 竞争。不过，从 `post()` 到 `GapWorker.run()` 的总延迟还包含当前 callback 剩余时间、前序消息积压、同步屏障规则和线程调度。DeliQueue 不提供“立即运行”保证。

`GapWorker.run()` 读取可见 RecyclerView 中最新的 `getDrawingTime()`，加 `mFrameIntervalNs` 估算下一帧 deadline，再按是否预计供下一帧使用、列表速度和 item 距离排序任务。预计供下一帧使用的 task 使用 `FOREVER_NS` 强制 create/bind，并可能出现 `RV Prefetch forced - needed next frame`；其他 task 才受估算 deadline 限制。

进入 `tryGetViewHolderForPositionByDeadline()` 后，RecyclerView 使用 `RecycledViewPool` 中按 `viewType` 维护的 create/bind 运行均值判断 `willCreateInTime()` 与 `willBindInTime()`。这套预算只覆盖 ViewHolder 获取、create 和 bind，不覆盖下一帧的 item measure/layout。因此：

- 只有 `RV Prefetch`，没有 create/bind：目标可能已经 attached、缓存命中，或普通 task 被预算拒绝。
- 出现 `RV Prefetch forced - needed next frame`：任务即使预计超出 gap 也会执行，不能把这段长耗时理解为“deadline 保护失效”。
- create/bind 很短而下一帧 `RV OnLayout` 很长：item 约束或测量仍是主因。

`LinearLayoutManager.setInitialPrefetchItemCount()` 只控制嵌套 RecyclerView 初次进入视口前的 item 数。官方 API 文档建议设置为内层列表初次可见的 item 数；超过可见数量会增加 View 创建、bind 与活跃对象数量。[LinearLayoutManager API](https://developer.android.com/reference/androidx/recyclerview/widget/LinearLayoutManager#setInitialPrefetchItemCount%28int%29)

混合 Compose/View item 还要单独观察 composition、layout、状态读取和 `ComposeView` 生命周期。`RV onBindViewHolder` 只覆盖 adapter bind 的外层 slice，无法完整表达之后发生的重组与 Compose measure。相关边界见 [22.15 Compose First 迁移](15-compose-first-view-migration-performance.md)。

## Perfetto 取证：从 monitor contention 到帧时间线

DeliQueue 官方文章给出了 `android.monitor_contention` 与 jank process 的 PerfettoSQL。下面的查询用于筛选“trace 中发生过 app jank 的进程”，并汇总这些进程里主线程的 MessageQueue monitor contention：

```sql
INCLUDE PERFETTO MODULE android.monitor_contention;
INCLUDE PERFETTO MODULE android.frames.jank_type;

SELECT
  process_name,
  SUM(dur) / 1000000 AS sum_dur_ms,
  COUNT(*) AS count_contention
FROM android_monitor_contention
WHERE is_blocked_thread_main
  AND short_blocked_method LIKE '%MessageQueue%'
  AND upid IN (
    SELECT DISTINCT(upid)
    FROM actual_frame_timeline_slice
    WHERE android_is_app_jank_type(jank_type) = TRUE
  )
GROUP BY process_name
ORDER BY SUM(dur) DESC;
```

这段官方查询只按 `upid` 限定“进程在该 trace 中有 jank”，没有把每条 contention 与某一帧做时间区间关联。它适合批量初筛，不能据此宣称某次 contention 导致了某一帧超时。进入单条 trace 后，应按以下顺序对齐时间：

1. 在 `android_monitor_contention` 读取 waiter、owner、阻塞方法、持锁方法和持续时间。
2. 对齐 `RV Prefetch`、`RV Prefetch forced - needed next frame`、`RV onCreateViewHolder type=0x...`、`RV onBindViewHolder type=0x...`、`RV PartialInvalidate`、`RV FullInvalidate` 与 `RV OnLayout`。
3. 检查主线程在目标区间是 Running、Runnable、Sleeping 还是被其他锁阻塞；Runnable 很久属于调度问题，不是 Java monitor 证据。
4. 对齐 App `SurfaceFrame` 与 SurfaceFlinger `DisplayFrame`。`jank_type` 描述超期原因，`present_type` 描述显示时序；App 超期与目标 layer 未按期 present 需要分别验证。
5. 用 JankStats state 或自定义 trace 标记页面、列表类型、数据规模、图片来源、Diff 批次和滚动动作。

FrameTimeline 与 CUJ 的字段用法见 [13.13 Perfetto DataGrid 与 Jank CUJ](../../part3-tools/ch13-perfetto/13-perfetto-data-explorer-jank-cuj.md)，JankStats 场景标记见 [19.11 JankStats](../../part3-tools/ch19-apm/11-jankstats.md)。第三方应用不会自动获得完整的系统 CUJ 业务名称，需要自己维护 state。

官方博客还提供 `track_event` 的 `mq` category，用于观察 `system_server` 的 MessageQueue tracing。普通应用应以 monitor contention、Looper/RecyclerView slice、scheduler、FrameTimeline 与自定义 trace 为主，不能把 system_server 专用配置当作应用 SDK。

## 业务线程投递治理

DeliQueue 降低队列管理成本，不会替应用清理消息积压。每条消息进入 `dispatchMessage()` 后，业务 callback 仍占主线程时间。列表场景可以采用三条约束：

- 合并可合并的 UI 结果：分页、图片状态和同一 item 的多次字段变化整理成一次最小 adapter update。
- 延后低优先级装饰更新：快速 fling 期间减少非首屏标签、推荐理由、日志和曝光回调，滚动减速或停止后再处理。
- 后台只做纯计算：diff、文本预处理和图片尺寸计算可放后台；View、adapter notification 和 Compose state 的写入仍要遵守各自线程规则。

下面的泛型骨架演示如何让多个生产者共享一次主线程 drain，并处理 `scheduled` 复位期间的新入队：

```kotlin
class MainThreadBatcher<T>(
    private val mainHandler: Handler,
    private val maxBatchSize: Int = 128,
    private val applyBatch: (List<T>) -> Unit,
) {
    private val pending = ConcurrentLinkedQueue<T>()
    private val scheduled = AtomicBoolean(false)

    init {
        require(maxBatchSize > 0)
    }

    fun enqueue(value: T) {
        pending.add(value)
        schedule()
    }

    private fun schedule() {
        if (scheduled.compareAndSet(false, true)) {
            if (!mainHandler.post(::drain)) {
                scheduled.set(false)
            }
        }
    }

    private fun drain() {
        val batch = ArrayList<T>(maxBatchSize)
        while (batch.size < maxBatchSize) {
            val item = pending.poll() ?: break
            batch += item
        }

        try {
            if (batch.isNotEmpty()) applyBatch(batch)
        } finally {
            scheduled.set(false)
            if (pending.isNotEmpty()) schedule()
        }
    }
}
```

`finally` 先释放 scheduled 标志，再检查队列；若生产者在复位前入队，末尾检查会重新 post；若生产者在复位后入队，它会自行取得标志。`maxBatchSize` 防止一次 drain 吞掉过多帧预算。工程实现还要补 lifecycle 取消、相同 key 合并、失败策略和线程安全测试，不能直接把所有 adapter notification 放进一个无界批次。

`Process.setThreadPriority()` 只能在 trace 已证明调度延迟、任务又确有时限时评估。把图片、数据库和网络线程全部提升到接近显示线程的优先级，可能增加前台 CPU 竞争和功耗。对 `android17-6.18-2026-06_r6` 来说，`kernel/sched/core.c` 与 `kernel/sched/fair.c` 可以解释线程为何长时间 Runnable；它们不能说明哪条 RecyclerView 消息应被合并。

## Android 17 适配与灰度验证

target 37 灰度不能只看总慢帧率。官方博客的数字来自合成 benchmark 和 Google 内部 beta tester trace：

| 指标 | 官方结果 | 证据边界 |
|---|---:|---|
| 多线程向繁忙队列插入 | 最高 5,000× | 极端合成 benchmark，未公开完整设备、线程数和消息规模 |
| App 主线程锁竞争时间 | -15% | 内部 beta tester Perfetto trace |
| App missed frames | -4% | 同批测试设备和 workload |
| System UI / Launcher missed frames | -7.7% | 同批测试设备和 workload |
| 启动到首帧 P95 | -9.1% | 同批测试设备和 workload |

这些数字用于说明优化方向，不能当成 RecyclerView 专项收益或业务 SLA。[DeliQueue impact](https://developer.android.com/blog/posts/under-the-hood-android-17-lock-free-message-queue)

灰度实验建议按下面的表格跑：

| 场景 | 对照组 | 观察指标 | 通过标准 |
| --- | --- | --- | --- |
| 大列表快速 fling | 同一 APK，DeliQueue compat on/off | `MessageQueue` contention、各类 `RV Prefetch`、JankStats 慢帧率 | monitor 等待下降；bind/layout 回归单独记录 |
| DiffUtil 批量更新 | 小批量 payload vs 整表刷新 | `RV PartialInvalidate` / `RV FullInvalidate`、主线程消息数 | target 37 只改善队列等待，不掩盖整表刷新问题 |
| 图片加载完成回调 | 单图回调 vs 批量 drain | 主线程 post 数、`onBind` 后图片设置耗时 | 快速滑动期间低优先级图片状态不挤占帧预算 |
| 数据库分页 | 弱网/慢查询回包 | 页面状态、adapter 更新批次、FrameTimeline | 回包集中到达时没有主线程消息风暴 |
| 混合 Compose/View item | ComposeView item vs 纯 View item | 自定义 trace、JankStats state、`RV OnLayout` | DeliQueue 收益和 composition 成本分开统计 |

每轮记录设备、Android build、APK commit、target SDK、兼容开关、刷新率、thermal 状态、数据规模、操作脚本、trace 配置和样本数。业务批量投递开关应与平台 compat 开关分开，避免一次实验改变两个变量。

target 37 的完整回归还应覆盖：

- Espresso、Robolectric、内部 idle 工具和性能 SDK；
- 快速 fling 中的 Diff 提交、图片完成回调和分页回包；
- 同步屏障、异步 Handler、IdleHandler 与 delayed message；
- 进程冷启动、后台恢复、Activity 重建与测试超时；
- 分配率与 GC，避免只观察 monitor contention。

## 与相关章节的关系

相关内容的分工如下：

- [1.13 MessageQueue 与 DeliQueue](../../part1-fundamentals/ch01-architecture/13-messagequeue-deliqueue.md)：Treiber stack、双堆、同步屏障、tombstone、Message 回收与 compat 选择。
- [7.8 RecyclerView 性能](../../part2-performance/ch07-smoothness/08-recyclerview-performance.md)：RecyclerView 1.4.0 的 GapWorker、缓存、DiffUtil、payload 与 trace。
- [22.2 RecyclerView 实战](02-recyclerview-practice.md)：业务页面中的 ViewHolder 复用、列表更新、图片和 ARR。
- [13.13 Perfetto DataGrid 与 Jank CUJ](../../part3-tools/ch13-perfetto/13-perfetto-data-explorer-jank-cuj.md)：FrameTimeline、jank 类型和 CUJ 查询。
- [19.11 JankStats](../../part3-tools/ch19-apm/11-jankstats.md)：应用侧帧状态与线上分桶。

## 小结

Android 17 DeliQueue 移除了 legacy MessageQueue 核心消息路径的单一 monitor，降低多生产者入队与 Looper 取消息之间的竞争。RecyclerView 1.4.0 的 `GapWorker` 调度、task 排序、create/bind 预算和 measure/layout 边界没有随之改变。

列表排查应保持四条证据线独立：MessageQueue monitor、Looper 前序消息与调度、RecyclerView create/bind/layout、FrameTimeline 与目标 layer present。只有 compat on/off 的同 APK 对照和时间对齐都支持同一结论，才能把改善归给 DeliQueue。

## Android 17 与 AndroidX 源码索引

- [`CombinedDeliMessageQueue/MessageQueue.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/os/CombinedDeliMessageQueue/MessageQueue.java)：compat change、Deli/legacy 分派、`mMessages` 兼容字段与 `next()`。
- [`MessageStack.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/os/MessageStack.java)：生产者 CAS push、Looper sweep 与并发遍历。
- [`MessageHeap.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/os/MessageHeap.java)：Looper 独占的最小堆与消息排序。
- [`Message.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/os/Message.java)：插入序号、flags 与 DeliQueue 下的回收边界。
- [RecyclerView 1.4.0 sources jar](https://dl.google.com/dl/android/maven2/androidx/recyclerview/recyclerview/1.4.0/recyclerview-1.4.0-sources.jar)：`GapWorker.java`、`RecyclerView.java` 与 `LinearLayoutManager.java`。
- [`kernel/sched/core.c`](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/kernel/sched/core.c) 与 [`kernel/sched/fair.c`](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/kernel/sched/fair.c)：Runnable、抢占与 CFS/EEVDF 调度观察边界。
