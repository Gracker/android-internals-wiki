---
title: "ADPF Hint Session 与协程线程迁移"
chapter: "25.11"
section: "25.11"
pipeline_stage: ready-for-review
task6_state: pending-review
task6_result: pass-light-edit
reviewed_by: openclaw-task6
reviewed_date: 2026-06-05
task9_state: rework-fixed
last_task6_review_log: "logs/review/2026-06-05-13-review.md"
last_task6_at: "2026-06-05T13:11:00+08:00"
task9_result: 'auto-fixed'
task6_review_notes: '2026-06-04 Task6 01:08: pass-light-edit(revisit). Task9 auto-fix writing quality OK; replaced forbidden word 矩阵 in section title. No new rework items.'
task9_reviewed_by: 'openclaw-task9'
task9_reviewed_date: '2026-06-04'
last_task9_at: '2026-06-04T00:20:00+08:00'
last_task9_review_log: 'logs/deep-review/2026-06-04-00-deep-review.md'
task2b_state: 'fixed'
task2b_result: fixed
status: ready-for-review
drafted_date: "2026-05-16"
applicable_versions: "Android 12 (API 31) - Android 17 (API 37)"
last_verified: "2026-08-07"
last_verified_against: "AOSP android-17.0.0_r1 PerformanceHintManager.java + Android Performance Hint API + Android SDK PerformanceHintManager.Session/WorkDuration/NDK references; 2026-08-07 rework cleared stale verification marker and strengthened source anchors without adding measured benefit claims"
confidence: medium
last_rework_at: "2026-08-07T17:36:17+08:00"
last_rework_run_id: "20260807-173540-rework-bf0a3299"
last_rework_log: "logs/rework/2026-08-07-20260807-173540-rework-bf0a3299-rework.md"
rework_result: "ready-for-review"
rework_summary: "清理旧验证标记：将扩展实验段改为正式证据边界说明；补强来源标记：frontmatter 与正文增加 android-17.0.0_r1、SDK Session/WorkDuration、NDK 与两份 DeepResearch 素材的明确锚点；状态回退 ready-for-review 等待复审。"
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
    path: "DeepResearch/2026-05-17-kotlin-coroutine-adpf-hint-engineering.md"
  - type: material
    path: "DeepResearch/2026-05-27-adpf-performancehintmanager-api-version-boundary.md"
  - type: structure
    path: "Cubox/速度优化：任务调度优化 - 掘金-2024-02-02.md"
task2b_fixed_at: "2026-06-03T08:56:35+08:00"
last_task9_autofix_at: '2026-06-04'
task9_review_notes: '2026-06-04 Task9 00:20：auto-fixed。修正线程优先级权限说明，并把参考摘要里的 WorkDuration API 边界校正为 API 35 flagged；回到 Task6 复审。'
deepseek_cn_review_state: done
last_deepseek_cn_review_at: 2026-06-08
---

# 25.11 ADPF Hint Session 与协程线程迁移

Kotlin 协程在挂起和恢复之间可能更换执行线程，ADPF 的 `PerformanceHintManager.Session` 却用一组 Linux 线程 ID 描述周期性工作。两者能够配合，但必须同时满足三个条件：工作有明确周期，执行线程长期存在，应用能持续上报每个周期的实际耗时。默认协程调度器不保证线程身份，因此不能在任意 `suspend` 函数外面简单套一层 Hint Session。

ADPF 不允许应用指定 CPU 频点，也不保证工作一定运行在某个核心。应用提供线程集合、目标时长和实际时长，系统再结合调度、动态电压频率调整和温控状态分配资源。源码锚点为 Android 17 / API 37 的框架实现，公开能力边界则以 Android SDK 文档为准。线程调度基础见 5.9 节。

## PerformanceHintManager Session 的线程绑定模型

`PerformanceHintManager.Session` 绑定的是 Linux 线程 ID，即 `android.os.Process.myTid()` 返回的 tid。`Thread.currentThread().id` 是 Java 线程标识，不能代替 tid。Android 官方的 [Performance Hint API 指南](https://source.android.com/docs/core/perf/performance-hint-api) 也在 Java 示例中使用 `Process.myTid()`。

Session 用来描述一组共同完成周期性工作的线程，例如一帧自研渲染、一次音频处理或一个固定频率的本地推理周期。Android 17 的 [`PerformanceHintManager.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/os/PerformanceHintManager.java) 对创建参数有明确校验：

- `tids` 不能为 `null` 或空数组；
- `initialTargetWorkDurationNanos` 必须大于零；
- 设备不支持 Hint Session，或传入的 tid 不属于本应用时，`createHintSession()` 可以返回 `null`。

这些约束说明 ADPF 不是一次性任务的“加速开关”。使用 Session 时还要遵守以下规则：

- 线程要长期存在。API 31～33 创建后不能修改线程列表；固定线程池重建时，需要关闭旧 Session 并重新创建。
- 目标时长只在目标帧率、采样率或业务周期改变时更新，不要在每个周期重复调用 `updateTargetWorkDuration()`。
- 每完成一个有效工作周期，再调用 `reportActualWorkDuration()`。没有完成的周期不应伪造耗时样本。
- Session 的状态修改由应用负责串行化。Android 17 源码注释明确要求调用方处理线程安全。

API 34 起，`setThreads(int[])` 会用新数组替换整个线程集合，不是在原集合上追加。它是同步调用，空数组会触发 `IllegalArgumentException`；线程不属于当前应用、Session 不在前台等情况也可能进入异常路径。线程集合更新应当跟随工作线程或固定线程池的生命周期，不能放进每个工作周期的热路径。

## 协程调度导致 tid 变化时的失效场景

协程是可挂起的任务，Linux 线程只是它在某一时刻的执行载体。`Dispatchers.Default`、`Dispatchers.IO` 和 `limitedParallelism()` 约束并行度或调度策略，却不承诺同一协程始终使用同一个 tid。挂起函数恢复后可以被另一个工作线程继续执行。详见 8.6 节。

ADPF 与协程组合的主要风险在于：Session 记录的 tid 和实际执行工作的 tid 分离。常见失效场景有三类：

- 任务在 `Dispatchers.Default` 上创建 Session 并登记当前 tid，挂起恢复后却由另一个工作线程执行；系统观察到的仍是旧线程。
- 周期性任务运行在面向阻塞操作的 `Dispatchers.IO` 上，参与工作的线程集合持续变化，Session 很难表达固定负载。
- 每次进入 `withContext()` 都重新取 tid、调用 `setThreads()` 并上报耗时；线程集合更新和业务工作挤在同一热路径，样本也混入了管理开销。

适合接入 ADPF 的协程任务通常使用专用固定线程。线程身份由单线程 `Executor`、固定大小的 `Executor` 或 `HandlerThread` 管理；协程只负责结构化调用。`Process.myTid()` 在线程启动后采集，工作和耗时上报都在登记过的线程上执行。

下面的示例展示单线程周期任务的最小封装。它有意把 `block` 声明为非挂起函数，防止一个周期执行到中间时切换调度器；`start()`、`runCycle()` 和 `shutdown()` 也必须由同一个生命周期管理者按顺序调用。

```kotlin
@RequiresApi(Build.VERSION_CODES.S)
class AdpfWorker(
    private val context: Context,
    private val targetNanos: Long,
) {
    private val executor = Executors.newSingleThreadExecutor { task ->
        Thread(task, "adpf-worker")
    }
    private val dispatcher = executor.asCoroutineDispatcher()
    private val manager =
        context.getSystemService(PerformanceHintManager::class.java)

    private var session: PerformanceHintManager.Session? = null
    private var started = false
    private var closed = false

    init {
        require(targetNanos > 0) { "targetNanos must be positive" }
    }

    suspend fun start(): Boolean = withContext(dispatcher) {
        check(!closed) { "worker is closed" }
        if (!started) {
            session = manager?.createHintSession(
                intArrayOf(Process.myTid()),
                targetNanos,
            )
            started = true
        }
        session != null
    }

    suspend fun runCycle(block: () -> Unit) = withContext(dispatcher) {
        check(started) { "call start() before runCycle()" }
        check(!closed) { "worker is closed" }

        val start = SystemClock.uptimeNanos()
        block()
        val actual = SystemClock.uptimeNanos() - start
        session?.reportActualWorkDuration(actual)
    }

    suspend fun shutdown() {
        withContext(dispatcher) {
            check(!closed) { "shutdown() must be called once" }
            session?.close()
            session = null
            closed = true
        }
        dispatcher.close()
    }
}
```

`start()` 即使返回 `false`，`runCycle()` 仍会执行工作，只是不再上报 ADPF 数据，这是设备不支持 Session 时的正常降级。`block` 抛出异常时，本周期不会上报完成耗时。`shutdown()` 先在专用线程关闭 Session，再关闭协程调度器，关闭后禁止继续调用任何 Session 方法。

这个封装不允许多个调用者并发操作生命周期。生产代码可以让一个拥有者协程串行调用，也可以在外层增加互斥保护。如果任务必须由多个线程并行完成，应创建小规模固定线程池，收集全部 tid 后统一创建 Session；线程池变化时再用 `setThreads()` 替换线程集合。

## `setThreads`、`close`、`reportActualWorkDuration` 的边界

`setThreads()` 只处理线程生命周期变化。它会替换 Session 的线程列表，而且是同步调用，不适合每周期调用。Android SDK 的 [`Session.setThreads()`](https://developer.android.com/reference/android/os/PerformanceHintManager.Session#setThreads(int%5B%5D)) 文档列出了空数组、线程归属和前台状态等异常条件，调用方需要有明确的失败策略。

`close()` 表示永久释放 Session，不能充当暂停操作。公开文档要求调用 `close()` 后不再调用该 Session 的其他方法。页面、相机或渲染模块退出时应关闭 Session；再次开始工作时创建新实例。

`reportActualWorkDuration(long)` 从 API 31 起可用，参数是刚结束周期的总耗时。API 35 起，公开的 `reportActualWorkDuration(WorkDuration)` 可以同时描述周期开始时间、总时长、CPU 时长和 GPU 时长。Android 17 实现会校验这些字段：开始时间和总时长必须大于零，CPU、GPU 时长不能为负，二者也不能同时为零。时间戳应使用与框架一致的 `SystemClock.uptimeNanos()` 时间基准。

上报频率按工作周期走，不按函数调用次数走。UI 或渲染类任务可以按帧上报；音视频、传感器、推理任务按自己的批次或采样周期上报。普通列表分页、一次性 JSON 解析、后台同步任务不适合为每个小任务创建 Session。它们更应该先解决线程池大小、任务合并、I/O 约束和后台执行策略，详见 25.1、25.2 节。

`PerformanceHintManager.getPreferredUpdateRateNanos()` 返回设备软件支持的首选更新周期信息。这个值不是业务截止时间，也不替代 Session 文档要求的逐周期耗时上报；业务 target 仍应来自刷新周期、采样周期或协议约束。

## ADPF API 版本边界

`PerformanceHintManager.Session` 的公开 API 随 Android 版本逐步增加。判断应用能否调用某个方法时，应查看 SDK API 参考文档和 `Build.VERSION.SDK_INT`；AOSP 实现里的构建期注解不能替代公开 SDK 契约。

| API 级别 | Android 版本 | 可用能力 | 说明 |
|----------|-------------|---------|------|
| 31 | Android 12 | `createHintSession()`、`getPreferredUpdateRateNanos()`、`reportActualWorkDuration(long)`、`updateTargetWorkDuration()`、`close()` | 基础能力：创建 Session、查询首选更新周期、上报单值耗时、更新目标和关闭。线程列表在创建时一次性传入，不可事后替换 |
| 34 | Android 14 | 增加 `setThreads(int[])` | 允许在 Session 存活期间替换线程列表。API 31-33 只能通过重建 Session 来更换线程 |
| 35 | Android 15 | 增加 `setPreferPowerEfficiency(boolean)`、`reportActualWorkDuration(WorkDuration)` | 两个方法都是公开 SDK API。`WorkDuration` 可以分别提供总时长、CPU 时长、GPU 时长和周期开始时间 |
| 36～37 | Android 16～17 | 沿用 API 35 的公开 Session 能力 | 相比 API 35，没有新增公开的 `Session` 方法；实现细节核对到 `android-17.0.0_r1` |

API 31～33 应在运行时判断 `PerformanceHintManager` 和创建结果是否为空；API 34、35 新增方法还要做对应版本保护。接口存在只表示可以调用，不表示所有设备和所有负载都有收益。

## 公开 SDK 与隐藏 GPU hint 的边界

Android 17 的框架源码中，`setPreferPowerEfficiency()` 和 `reportActualWorkDuration(WorkDuration)` 仍可见 `@FlaggedApi` 注解；但它们已经从 API 35 开始进入公开 SDK，应用应按 [Session API 参考文档](https://developer.android.com/reference/android/os/PerformanceHintManager.Session) 所列的 `Added in API level` 判断可用性。这里的源码注解参与平台构建和 API 演进管理，不能据此宣称公开方法还需要应用检查某个运行时功能标志。

同一源码中的 `GPU_LOAD_UP`、`GPU_LOAD_DOWN` 和 `GPU_LOAD_RESET` 带有 `@TestApi`，不属于第三方应用可依赖的公开 SDK。应用不应通过反射或复制常量调用隐藏的 GPU 提示。需要表达 CPU/GPU 工作拆分时，API 35 的公开 [`WorkDuration`](https://developer.android.com/reference/android/os/WorkDuration) 已经提供相应字段。

`setPreferPowerEfficiency(true)` 只是告诉系统：在满足目标时长的前提下，当前工作可以偏向能效。它不是固定低频、固定核心或保证省电的开关。是否启用仍要通过设备测试比较周期耗时、能量和温控表现。

## 非游戏业务使用 ADPF 的判定条件

非游戏业务接入 ADPF 前，可以用四个问题判断负载是否匹配：

| 条件 | 适合接入 | 不适合接入 |
| --- | --- | --- |
| 周期性 | 每帧渲染、音视频处理、固定批次推理 | 一次性网络请求、偶发 JSON 解析 |
| 线程稳定性 | 固定 `Executor`、RenderThread、长期工作线程 | `Dispatchers.IO` 弹性线程、临时线程 |
| 目标耗时 | 能从刷新周期、采样周期或业务协议得到明确截止时间 | 只要求“尽快完成” |
| 验证方式 | 能采 Perfetto、帧耗时、功耗和温控 | 只能看主观流畅度 |

这些条件都与 ADPF 的反馈模型有关，缺少任意一项都应先补测或选择别的优化手段。首页启动阶段的大量初始化更适合任务编排、Baseline Profile 和懒加载；后台同步更适合 WorkManager 约束与批量网络；长列表滑动应先减少主线程工作、布局次数和图片解码成本。

适合尝试 ADPF 的非游戏案例通常有一个共同点：工作本身像“帧”。例如相机预览上的实时滤镜、低延迟音频处理、持续传感器融合、固定频率本地推理。这些任务有周期、有截止时间、有长期线程，也能通过 Perfetto 对照 CPU 频率、线程运行状态和实际耗时。

## 功耗、温控与响应速度的联合验证方法

ADPF 的评估不能只看耗时下降。它让系统提前知道工作截止时间，以便在性能、能量和温控约束之间调度资源。某个高分位耗时改善，并不自动代表单位任务能耗或持续运行表现也改善。详见 11.2 与 25.1 节。

验证应覆盖三类证据：

- 响应速度：用 Macrobenchmark 或业务基准记录周期耗时分布。渲染任务还要检查 FrameTimeline、错过截止时间的帧，以及实际时长与目标时长的差值。
- 系统调度：用 Perfetto 观察目标线程的 `thread_state`、所用 CPU、频率、唤醒延迟和迁移情况，再与 Session 登记的 tid 对照。
- 功耗与温控：在支持的设备上用 Macrobenchmark `PowerMetric` 观察测试窗口的系统级能量或功率变化，同时记录 Thermal API 或 `dumpsys thermalservice` 的热状态。`PowerMetric` 是实验性且依赖设备支持的系统级指标，不能直接解释为某个线程的能耗。

团队应根据业务目标预先定义耗时分位、能量和热状态的回归门限，并在相同设备状态与工作负载下比较启用前后结果。没有实机数据时，只能说明接入方案和待核验假设，不能写成已经取得的优化收益。

## 扩展：主线程、RenderThread、业务线程的 Session 组织方式

主线程通常不适合作为独立 Hint Session 的工作线程。它同时处理输入、消息、生命周期、绘制调度和业务回调，难以对应单一周期。应先减少主线程工作，再把适合迁移的周期性重负载放到可控工作线程。

标准 View 或 Compose 渲染主要走平台渲染管线，应用通常不拥有 RenderThread 的生命周期和 tid，因此不能把它当作普通业务线程直接登记。自研图形、相机滤镜、游戏循环或原生渲染引擎可以管理自己的渲染线程、计算线程和资源上传线程，但只有共同服务同一个周期截止时间的线程才应进入同一 Session。

业务侧应让一个 Session 对应一种周期性工作。把多个模块、多个截止时间放进全局 Session 会混淆目标时长与实际耗时，也不利于判断哪一类负载受益。

## 扩展：与 Macrobenchmark / Perfetto 的验证脚本

最小实验可以设置两个行为一致的组：对照组不创建 Hint Session，实验组使用固定线程、Session 和周期上报。两组必须使用同一设备、系统构建、供电方式、初始热状态、业务输入和测试时长。测试窗口应覆盖业务关心的持续运行阶段，避免只观察启动后的短暂调度行为。

Perfetto 分析要回答三个问题：登记的 tid 是否执行了目标工作，工作周期是否满足目标时长，调度变化是否伴随能量或温控代价。可以按线程名和 tid 查询 `thread_state`，再与 `Trace.beginSection()` 标记的工作周期对齐。能量数据来自支持该指标的设备测试，并与耗时和热状态一起判断。

这里没有附带实机跟踪数据，因此不提供收益百分比，也不声称 ADPF 在某类非游戏业务中已经带来确定收益。任何新增的 Pixel 或厂商机型数据都应同时记录设备型号、Android 版本、刷新率、温度起点、测试时长、目标周期、所选耗时分位和能量指标。

## 小结

ADPF 与 Kotlin 协程可以配合，条件是周期性工作始终由已登记的长期线程执行。Session 绑定 Linux tid，默认协程调度器却允许任务迁移；需要 ADPF 的任务应使用专用固定线程，并在同一线程上创建 Session、执行工作和上报耗时。公开 API 按 SDK 版本判断，隐藏 GPU 提示不属于应用接口。没有明确周期、稳定线程和实机验证条件时，应优先处理任务调度、渲染成本和后台功耗。

## 参考资料

- [Android 17 `PerformanceHintManager.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/os/PerformanceHintManager.java)
- [Android Performance Hint API](https://source.android.com/docs/core/perf/performance-hint-api)
- [`PerformanceHintManager` API reference](https://developer.android.com/reference/android/os/PerformanceHintManager)
- [`PerformanceHintManager.Session` API reference](https://developer.android.com/reference/android/os/PerformanceHintManager.Session)
- [`WorkDuration` API reference](https://developer.android.com/reference/android/os/WorkDuration)
- [NDK Performance Hint API](https://developer.android.com/ndk/reference/group/a-performance-hint)
