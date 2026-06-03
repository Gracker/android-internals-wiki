---
title: "ADPF Hint Session 与协程线程迁移"
chapter: "25.11"
section: "25.11"
pipeline_stage: task6_pending
task6_state: revisiting
task6_result: pass-light-edit
reviewed_by: openclaw-task6
reviewed_date: "2026-05-16"
task9_state: pending
last_task6_at: "2026-05-16T02:11:00+08:00"
task9_result: needs-rework
task9_reviewed_by: openclaw-task9
task9_reviewed_date: "2026-05-16"
last_task9_at: "2026-05-16T02:30:40+08:00"
last_task9_review_log: "logs/deep-review/2026-05-16-02-deep-review.md"
task2b_state: fixed
task2b_result: fixed
status: ready-for-review
drafted_date: "2026-05-16"
applicable_versions: "Android 12 (API 31) - Android 16 (API 36)"
last_verified: "2026-05-16"
last_verified_against: "AOSP android-16.0.0_r1"
confidence: medium
tags: ["adpf", "performancehintmanager", "coroutine", "power", "threading"]
related_chapters: ["5.9", "8.6", "11.2", "25.1", "25.2"]
created_by: "task2a-knowledge-gap"
created_date: "2026-05-15"
gap_source: "素材驱动/官方文档"
sources:
  - type: aosp
    path: "frameworks/base/core/java/android/os/PerformanceHintManager.java"
  - type: official
    path: "source.android.com/docs/core/perf/performance-hint-api"
  - type: official
    path: "developer.android.com/reference/android/os/PerformanceHintManager.Session"
  - type: official
    path: "developer.android.com/ndk/reference/group/a-performance-hint"
  - type: material
    path: "DeepResearch/2026-05-13-adpf-performancehint-session-kotlin-coroutine-analysis.md"
  - type: structure
    path: "Cubox/速度优化：任务调度优化 - 掘金-2024-02-02.md"
task2b_fixed_at: "2026-06-03T08:56:35+08:00"
---

# 25.11 ADPF Hint Session 与协程线程迁移

Kotlin Coroutine 会让业务代码在挂起、恢复之间跨线程执行，ADPF 的 `PerformanceHintManager.Session` 又要求同一组 Linux tid 持续表达周期性负载。两者放在一起时，工程约束落在三项条件上：ADPF 适合周期固定、线程稳定、能持续上报耗时的工作；协程默认调度器的线程迁移会削弱这个前提。读完本节，应该能判断哪些协程任务适合接入 ADPF，哪些场景继续用线程池、优先级和常规功耗治理更稳。

[结构参考: Cubox/速度优化：任务调度优化 - 掘金-2024-02-02.md] 参考书把任务调度优化放在线程优先级、CPU 利用率和大核绑定这一组问题下讨论。这里不沿用绑核方案，原因是 Android 公开 API 不允许应用直接指定 CPU 频点或稳定绑核；现代做法是把工作周期、目标耗时和线程集合交给系统，由系统结合 DVFS、调度器和温控状态决定资源分配。详见 5.9 节。

## PerformanceHintManager Session 的线程绑定模型

`PerformanceHintManager.Session` 绑定的是 Linux 线程 ID，也就是 `android.os.Process.myTid()` 返回的 tid；`Thread.currentThread().getId()` 返回的是 JVM 线程 ID，不能作为 session 线程列表传入。[已验证: 官方文档, source.android.com/docs/core/perf/performance-hint-api] 官方示例也明确要求使用 `Process.myTid()`。

Session 的设计目标是同一组线程共同完成一个周期性工作。例如一帧渲染、一次固定频率的音视频处理、一个需要稳定 deadline 的推理周期。AOSP android-16.0.0_r1 中 `createHintSession(int[] tids, long initialTargetWorkDurationNanos)` 对两个参数有硬校验：线程列表不能为空，目标时长必须为正数；如果设备不支持 hint session，或者 tid 不属于当前应用进程，创建结果可以是 `null`。[已验证: AOSP android-16.0.0_r1, frameworks/base/core/java/android/os/PerformanceHintManager.java]

这几个约束决定了 App 侧不能把 ADPF 当成“临时加速开关”：

- 线程集合要稳定：AOSP 注释写明 session 里的线程应当是 long-lived，不适合动态频繁创建或销毁。API 31-33 不支持 `setThreads()`，线程列表只能在 `createHintSession()` 时一次性传入；线程池重建时需要关闭旧 session 并重新创建。
- 目标周期要稳定：`updateTargetWorkDuration()` 只在目标帧率、采样率或业务周期变化时调用，不适合每个任务都改一次。
- 耗时上报要成对：使用 work duration API 时，每个周期完成后调用 `reportActualWorkDuration()`，系统才有反馈样本去调整核心选择和频率。
- 调用方自己保证线程安全：`Session` 文档说明方法调用会改变内部状态，跨线程并发调用需要 App 侧串行化。

`setThreads(int[] tids)`（API 34+）会替换当前线程列表，并不会在原列表上追加。AOSP android-16.0.0_r1 还写了两条边界：session 已关闭时 `mNativeSessionPtr == 0`，`setThreads()`（API 34+）直接返回；传空数组会抛 `IllegalArgumentException`。因此，线程列表更新应该是低频的生命周期动作，例如 worker 线程创建完成后登记，或固定线程池重建后替换，不应该放在每个协程任务开始前。

## 协程调度导致 tid 变化时的失效场景

Coroutine 的执行单元是 coroutine；Linux 线程只是它某一次运行时所在的载体。`Dispatchers.Default`、`Dispatchers.IO`、`limitedParallelism()` 都只能约束协程调度策略，不能自然等价为“同一个 tid 持续执行同一类工作”。一个 suspend 函数在挂起前后可能恢复到不同 worker；IO dispatcher 还可能因为阻塞任务扩展线程。详见 8.6 节。

ADPF 与协程组合的主要风险在于：session 记录的 tid 和实际执行工作的 tid 分离。常见失效场景有三类：

- 任务在 `Dispatchers.Default` 上运行，创建 session 时登记了当前 tid，下一次恢复却落到另一个 worker；系统仍按旧 tid 的负载理解这个 session。
- 在 `Dispatchers.IO` 上处理周期性工作，线程池因为阻塞 I/O 扩展或收缩，`setThreads()` 更新频率跟不上实际 worker 变化。
- 每次 `withContext()` 进入后用 `Process.myTid()` 更新 session，再立刻上报耗时；这会把调度开销、native 调用和工作耗时混在一起，反馈样本会变脏。

适合接 ADPF 的协程模型通常采用固定线程：为这类周期性工作准备固定线程，协程只是把代码写成 suspend 形式。线程身份由固定 `Executor` 或 `HandlerThread` 管住，`Process.myTid()` 只在线程启动后采集一次；业务周期结束后在同一条线程上上报耗时。

这段代码只展示线程身份稳定的组织方式，重点看 `Process.myTid()` 的采集位置和 session 的生命周期；异常处理、版本判断和空值降级需要按业务封装。

```kotlin
@RequiresApi(Build.VERSION_CODES.S)
class AdpfWorker(
    private val context: Context,
    private val targetNanos: Long,
) : Closeable {
    private val executor = Executors.newSingleThreadExecutor { task ->
        Thread {
            // 线程优先级按场景设定；THREAD_PRIORITY_DISPLAY 可能因缺少 SCHED_FIFO 权限抛 SecurityException
            // 建议在验证权限后选定优先级，或在 catch 后降级到 THREAD_PRIORITY_DEFAULT
            task.run()
        }.apply { name = "adpf-worker" }
    }
    private val dispatcher = executor.asCoroutineDispatcher()
    private var session: PerformanceHintManager.Session? = null

    suspend fun start() = withContext(dispatcher) {
        val tid = Process.myTid()
        val manager = context.getSystemService(PerformanceHintManager::class.java)
        session = manager?.createHintSession(intArrayOf(tid), targetNanos)
    }

    suspend fun runCycle(block: suspend () -> Unit) = withContext(dispatcher) {
        val start = SystemClock.uptimeNanos()
        block()
        val actual = SystemClock.uptimeNanos() - start
        session?.reportActualWorkDuration(actual)
    }

    override fun close() {
        session?.close()
        dispatcher.close()
        executor.shutdown()
    }
}
```

这段示意代码把 ADPF 的线程集合限制在一个固定 worker 上。线程优先级按业务场景设定，`THREAD_PRIORITY_DISPLAY` 等高优先级可能因缺少 `SCHED_FIFO` 权限抛 `SecurityException`；生产代码应在 catch 后降级到 `THREAD_PRIORITY_DEFAULT` 或其他可用优先级。牺牲调度弹性换 tid 可解释性是工程上合理的取舍。如果任务本身需要在多个线程并行，应显式维护一个小规模固定 executor，在线程全部启动后一次性 `setThreads(intArrayOf(...))`。

## `setThreads`、`close`、`reportActualWorkDuration` 的边界

`setThreads()`（API 34+）的更新成本和语义都不适合高频调用。它会替换 session 的线程列表，AOSP 注释还标明它是同步调用（非 oneway）；线程列表为空、线程不属于本应用、session 不在前台等情况会走异常路径。工程上按生命周期分开处理：线程生命周期变化时更新，工作周期变化时上报，不把两件事混在一个热路径里。

`close()` 表示释放资源，不能当暂停使用。session 关闭后再调用 `setThreads()` 会直接返回，后续上报也失去意义。比较稳的封装是把 session 绑定到 worker 组件生命周期：页面或渲染模块创建时启动，模块销毁时关闭；如果后台任务被取消，就直接关闭 session，下一次前台工作重新创建。

`reportActualWorkDuration(long)` 适用于 Android 12 起的基础路径，参数是上一周期总耗时。Android 16 源码中还存在 `reportActualWorkDuration(WorkDuration)` 重载，可以把总时长、CPU 时长、GPU 时长和工作周期开始时间分开上报；同一份源码对这些字段做了严格校验：周期开始时间和总时长必须大于 0，CPU / GPU 时长不能为负，二者不能同时为 0。[已验证: AOSP android-16.0.0_r1, frameworks/base/core/java/android/os/PerformanceHintManager.java]

上报频率按工作周期走，不按函数调用次数走。UI 或渲染类任务可以按帧上报；音视频、传感器、推理任务按自己的 batch 或采样周期上报。普通列表分页、一次性 JSON 解析、后台同步任务不适合为每个小任务创建 session。它们更应该先解决线程池大小、任务合并、I/O 约束和后台执行策略，详见 25.1、25.2 节。

## ADPF API 版本边界矩阵

`PerformanceHintManager.Session` 的公开 API 随 Android 版本逐步放出，不能按最新的源码直接认为所有设备都能用。

| API 级别 | Android 版本 | 可用能力 | 说明 |
|----------|-------------|---------|------|
| 31 | Android 12 | `createHintSession(int[], long)` + `reportActualWorkDuration(long)` + `close()` | 基础能力：创建 session、上报单值耗时、关闭。线程列表在创建时一次性传入，不可事后替换 |
| 34 | Android 14 | 增加 `setThreads(int[])` | 允许在 session 存活期间替换线程列表。API 31-33 只能通过重建 session 来更换线程 |
| 35 | Android 15 | 增加 `setPreferPowerEfficiency(boolean)`（flagged）、`reportActualWorkDuration(WorkDuration)`（flagged） | `WorkDuration` 可拆分上报总时长、CPU 时长、GPU 时长和周期开始时间。均为 flagged API，需运行时 flag 判断 |
| 36 | Android 16 | `WorkDuration` / `setPreferPowerEfficiency` 继续 flagged | `GPU_LOAD_UP/DOWN/RESET` 常量与 GPU hint 相关 flag 在 android-16.0.0_r1 源码中存在，受 `FLAG_ADPF_GPU_REPORT_ACTUAL_WORK_DURATION` 控制 |

发布侧按三层判断：编译期看 SDK 是否暴露 API，运行期看 manager/session 是否非 null 且 API 可用，灰度期看 Perfetto/帧耗时/功耗是否真的改善。

## Android 15/16 flagged API 与 GPU hint 差异

公开文档把 ADPF 放在 CPU 性能 hint 的框架下讲：应用提供目标周期和实际耗时，系统尝试让线程组在合适的核心和频率上运行。Android 16 源码显示，GPU 相关能力开始出现更细粒度的接口，但其中一部分仍带 `@FlaggedApi`：`GPU_LOAD_UP`、`GPU_LOAD_DOWN`、`GPU_LOAD_RESET` 以及 `reportActualWorkDuration(WorkDuration)` 都标注了 `FLAG_ADPF_GPU_REPORT_ACTUAL_WORK_DURATION`；`setPreferPowerEfficiency(boolean)` 标注了 `FLAG_ADPF_PREFER_POWER_EFFICIENCY`。[已验证: AOSP android-16.0.0_r1, frameworks/base/core/java/android/os/PerformanceHintManager.java]

这带来一个发布侧边界：不要只按 Android 版本号写死能力表。发布侧按三层判断：编译期看 SDK 是否暴露 API，运行期看设备返回的 manager/session 是否可用，灰度期看 Perfetto、帧耗时和功耗指标是否真的改善。对于 flagged API，发布稿里只能写“android-16.0.0_r1 源码存在并受 flag 控制”，不能写成所有 Android 16 设备稳定可用。

GPU hint 与 CPU hint 的使用重点也不同。CPU hint 更适合“这组线程每 16.6 ms / 8.3 ms 要完成一次工作”这类周期信号；GPU hint 面向渲染负载的突变和 CPU/GPU 耗时拆分。非游戏业务如果只是偶发动画、普通 RecyclerView 滑动或 WebView 内容刷新，优先用 FrameTimeline、渲染优化和 WebView 功耗治理；只有周期性图形工作已经被验证为瓶颈时，再评估 GPU hint。

## 非游戏业务使用 ADPF 的判定条件

非游戏业务接 ADPF 前，先用四个条件筛掉不合适的场景：

| 条件 | 适合接入 | 不适合接入 |
| --- | --- | --- |
| 周期性 | 每帧渲染、音视频处理、固定 batch 推理 | 一次性网络请求、偶发 JSON 解析 |
| 线程稳定性 | 固定 executor、RenderThread、长期 worker | `Dispatchers.IO` 弹性线程、临时线程 |
| 目标耗时 | 有明确 deadline，例如 16.6 ms 或业务自定义周期 | 只要求“尽快完成” |
| 验证方式 | 能采 Perfetto、帧耗时、功耗和温控 | 只能看主观流畅度 |

如果四项里有两项不满足，ADPF 多半排不到第一选择。比如首页启动阶段的大量初始化任务更适合任务编排、Baseline Profile、懒加载和线程优先级治理；后台同步更适合 WorkManager 约束、批量网络和省电策略；长列表滑动更适合减少主线程工作、降低布局和图片解码成本。

适合尝试 ADPF 的非游戏案例通常有一个共同点：工作本身像“帧”。例如相机预览上的实时滤镜、低延迟音频处理、持续传感器融合、固定频率本地推理。这些任务有周期、有 deadline、有长期线程，也能通过 Perfetto 对照 CPU 频率、线程运行状态和实际耗时。

## 功耗、温控与响应速度的联合验证方法

ADPF 的收益不能只看耗时下降。它的目标是让系统更早知道工作 deadline，在性能和功耗之间做资源分配；如果 P95 耗时下降但平均功耗、热状态和降频概率变差，方案仍然可能不值得上线。详见 11.2 与 25.1 节。

验证分三层做：

- 响应速度：用 Macrobenchmark 或自建基准记录 P50 / P90 / P95 周期耗时，渲染类任务同时看 FrameTimeline jank、missed deadline 和 `actualDuration - targetDuration`。
- 系统调度：用 Perfetto 看目标线程的 `thread_state`、CPU core、频率、sched wakeup 延迟和是否频繁迁移；对照 session 登记的 tid，确认工作没有跑到未登记线程。
- 功耗与温控：用 Macrobenchmark `PowerMetric` 记录测试窗口内能量或功率变化，用 `dumpsys thermalservice` / Thermal API 观察热状态，用 batterystats 做长时间回归。

上线门禁建议同时设置三条线：P95 周期耗时不能退化，单位任务能耗不能上升到超过业务阈值，热状态不能更早进入 throttling。没有实机功耗数据时，章节只能标为实验方案，不能把 ADPF 接入写成既定优化收益。

## 扩展：主线程、RenderThread、业务线程的 session 组织方式

主线程不建议单独作为 ADPF session 的主对象。主线程同时处理输入、消息、生命周期、绘制调度和业务回调，负载来源太杂；把它登记到 session 里，系统收到的是混合信号。更合适的做法是优化主线程工作量，把周期性重负载放到可控 worker 或 RenderThread 相关路径，主线程只保留调度和状态提交。

RenderThread 与渲染 worker 的边界要按业务类型区分。标准 View / Compose 渲染主要走系统渲染管线，App 侧通常不直接管理 RenderThread 的 tid；自研图形、相机滤镜、游戏循环或 native 渲染引擎可以把渲染线程、物理线程、资源上传线程纳入同一个 session。多线程 session 只有在线程共同服务一个周期性 deadline 时才成立，不能把所有“看起来重要”的线程都塞进去。

业务线程接入 ADPF 时，推荐一个 session 对应一种周期性工作，不要用全局 session 覆盖多个模块。全局 session 会把不同 deadline 的任务混在一起，系统无法判断哪类工作需要资源。模块化 session 虽然管理成本更高，但更容易定位收益和副作用。

## 扩展：与 Macrobenchmark / Perfetto 的验证脚本

最小验证脚本可以按 AB 两组跑：A 组不启用 ADPF，B 组启用固定线程 + session + 周期上报。每组至少覆盖冷机、温机、持续运行三种状态；如果只测前 30 秒，容易把 boost 误判为长期收益。

Perfetto 查询重点放在三个事实是否同时成立：登记的 tid 正在执行目标工作，工作周期耗时贴近 target，CPU 频率和迁移形态没有带来额外功耗。SQL 侧可按线程名和 tid 聚合 `thread_state` 运行时间，再与自定义 `Trace.beginSection()` 标记的 work cycle 对应到同一时间窗口。PowerMetric 侧记录测试窗口能量变化，作为上线前的回归门禁。

[待验证] 当前章节没有本地实机 trace，因此不写固定收益百分比。后续如果补 Pixel / 厂商机型数据，应同时记录设备型号、Android 版本、刷新率、温度起点、测试时长、目标周期、P95 耗时和能量指标。

## 小结

ADPF 与 Coroutine 可以组合，但前提是把“协程代码”落到稳定线程身份上。Session 绑定的是 Linux tid，适合长期线程和周期性 deadline；默认协程调度器的弹性迁移会让 tid 信号失真。非游戏业务接入前，先确认周期、线程、目标耗时和验证工具都成立；否则继续用常规任务调度、渲染优化和功耗治理，收益更可控。

## 参考资料

### Kotlin Coroutine 线程迁移与 ADPF Hint 工程化边界
- 来源：/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/DeepResearch/2026-05-17-kotlin-coroutine-adpf-hint-engineering.md
- 类型：DeepResearch 调研结果
- 摘要：ADPF hint session 基于 TID 绑定，Kotlin 协程线程迁移导致无法精确绑定 hint。API 33 只能重建 session，API 34 支持 setThreads 动态调整。评估了 Dispatchers.Default/IO 场景下 ADPF IPC 开销与工程化约束。
- 注入时间：2026-05-17
- 价值：建立 ADPF TID 绑定与协程调度的工程化边界，指导 ADPF 在 Kotlin 协程场景下的正确使用策略

<!-- AIW-源码调研-2026-05-27: ADPF API 版本边界修正 -->
> **源码调研修正**：Session.setThreads() 为 API 34 公开方法（非 flagged API）。setPreferPowerEfficiency() 和 WorkDuration 分离上报为 flagged API，需运行时 flag 判断。详见 [DeepResearch/2026-05-27-adpf-performancehintmanager-api-version-boundary.md](DeepResearch/2026-05-27-adpf-performancehintmanager-api-version-boundary.md)

### ADPF PerformanceHintManager Session API 版本边界与 Kotlin 协程协同约束
- 来源：/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/DeepResearch/2026-05-27-adpf-performancehintmanager-api-version-boundary.md
- 类型：DeepResearch 调研结果
- 摘要：PerformanceHintManager（ADPF）从 API 31 公开，但各子 API 版本边界差异显著。Session.setThreads() 为 API 34 公开 API 非 flagged；setPreferPowerEfficiency 为 API 35 FlaggedApi；WorkDuration 为 API 36 FlaggedApi。纠正了此前将 setThreads 标注为 flagged 的版本判断错误。Binder IPC 单次约 1ms。
- 注入时间：2026-05-27
- 价值：源码级验证 ADPF hint session 版本边界，纠正 AIW 章节中的版本标注错误，含 AOSP android-16.0.0_r1 锚点

