---
title: "启动框架设计与任务编排"
chapter: "21.2"
section: "21.2"
status: finalized
applicable_versions: "Android 10 (API 29) - Android 17 (API 37)"
last_verified: "2026-07-03"
last_verified_against: "AOSP android-17.0.0_r1, Jetpack App Startup 1.2.0 sources, alibaba/alpha 04fe7f2 (artifact 1.0.0.1)"
task9_result: fixed
task9_reviewed_date: "2026-07-06"
task9_reviewed_by: "openclaw-task9-idle-audit"
last_task9_audit: "2026-07-06"
pipeline_stage: ready-to-publish
confidence: medium
drafted_date: "2026-05-12"
polish_count: 1
sources:
  - type: aosp
    path: "frameworks/base/core/java/android/app/Application.java"
  - type: aosp
    path: "frameworks/base/core/java/android/app/ActivityThread.java"
  - type: official
    path: "developer.android.com/topic/libraries/app-startup"
  - type: blog
    path: "Clippings/Android 性能优化 - 任务调度优化：线程+CPU，提升任务调度优先级.md"
  - type: blog
    path: "Clippings/Android 性能优化 - 原理：重新认识应用的速度优化.md"
  - type: aosp
    path: "androidx.startup:AppInitializer.java"
  - type: github
    path: "github.com/alibaba/alpha/tree/04fe7f22c469de66fed98c341334c954dfabafb2"
tags: [startup-framework, dag, app-startup, async-init, thread-pool, task-scheduling]
related_chapters: ["21.1", "21.6", "8.3", "1.5"]
consolidated_from:
  - "src/part5-app/ch21-startup/20-modular-startup-dependency-graph.md"
  - "src/part5-app/ch21-startup/09-startup-case-studies.md#案例二"
task6_state: reviewed
task6_review_notes_final: "2026-07-02 Task6 round3 (post-Task9-autofix): pass-light-edit. L1 fix×1 (真正→删). L2 pass. Anchors all covered. Auto-promoted: task9=pass, queue=completed."
task6_review_notes_round4: "2026-07-03 Task6 round4 (re-confirm): pass-light-edit. L1 clean. L2 pass. No new L3/L4 issues. AUTO-PROMOTED: task6=pass-light-edit, task9=auto-fixed(=pass), queue=completed."
task9_state: reviewed
task2b_state: fixed
task2b_result: fixed-lite
last_task2b_lite_at: "2026-07-06"
reviewed_by: openclaw-task6
reviewed_date: 2026-06-21
task6_result: pass-light-edit

last_task9_autofix_at: "2026-07-02"
task6_reviewed_date: "2026-05-22"
task9_review_notes: "2026-07-02 Task9 normal deep-review AUTO-FIX：对照 AOSP android-17.0.0_r1 ActivityThread、Android Developers TTID/TTFD 文档和 alibaba/alpha 04fe7f2 源码，修正 ContentProvider 生命周期边界、Alpha 超时封装示例、await 封装示例和 TTID 指标说明；回到 Task6 复审。"
last_task9_review_log: "logs/deep-review/2026-07-02-19-deep-review.md"
last_task6_at: "2026-07-02T19:14:49+08:00"
last_task6_review_log: "logs/review/2026-06-21-20-review.md"
task6_review_notes: '2026-07-02 18:10 Task6 revisiting-review: needs-rework。L1/L2复扫通过, 无新增小修。L3/L4问题已在queue.json(pending)。保持ready-for-review, 送Task2B。 | 2026-06-01 23:07 Task6 revisiting-review：L1/L2 复扫无新增小修，锚点覆盖完整，未新增 L3/L4 回炉项，送 Task9 复审。'
last_task2b_at: "2026-07-02T18:50:00+08:00"
task2b_notes: "2026-06-01 Task2B fallback: 按 logs/deep-review/2026-05-22-03-deep-review.md 修正 Alpha Project.Builder/getInstance/默认 ExecutorService/执行模型，并收窄线程优先级建议。2026-07-02 Task2B round2: 补充 Alpha 错误处理与超时机制、Application 生命周期集成方式、启动框架选型常见陷阱与场景化引导。"
task6_review_notes_round2: "2026-07-02 Task6 revisiting-review round2: pass-light-edit. L1 fix: remove banned word. L2 pass. No new L3/L4 issues."
task6_l1_l2_fixes: 1
task6_l3_l4_issues: 0
task6_new_rework: false
last_task2b_verify_at: "2026-06-21T19:30:09+08:00"
task2b_verifier_notes: "状态修正：Task9 auto-fix 后 status 应为 ready-for-review，原 finalized 已回退。"
deepseek_cn_review_state: done
last_deepseek_cn_review_at: 2026-07-04
---

# 启动框架设计与任务编排

## 范围

21.1 节说明了怎样测量启动。测量后的工程问题，是把必须执行的初始化工作建成可验证的任务图，在满足依赖、线程和故障边界的前提下缩短关键路径。

平台锚点为 Android 17 / API 37 / `android-17.0.0_r1`。Jetpack App Startup 固定到 1.2.0；Alpha 的代码结论固定到仓库提交 `04fe7f22c469de66fed98c341334c954dfabafb2`。

`ApplicationStartInfo` 的准确分析见 [启动监控与度量](./08-startup-monitoring.md)。

## 1. 编排前先删任务

启动框架不能把不必要的工作变便宜。拿到初始化清单后，先逐项回答：

- 当前进程是否需要它？
- 当前入口是否需要它？
- 第一帧之前是否必须完成？
- TTFD 之前是否必须完成？
- 失败时能否显示降级界面？
- 能否在功能首用、用户同意或空闲阶段再初始化？

建议把任务分为四个阶段：

| 阶段 | 完成边界 | 典型内容 |
| --- | --- | --- |
| `PRE_APP` | `Application.onCreate()` 之前 | 少量由 Provider 强制触发的初始化 |
| `PRE_FIRST_FRAME` | TTID 之前 | 首屏渲染不可缺少的同步状态 |
| `PRE_FULLY_DRAWN` | TTFD 之前 | 首要操作所需的数据和能力 |
| `DEFERRED` | 页面可用之后 | 二级功能、预取、非必要 SDK |

`PRE_APP` 是被组件生命周期强制出来的阶段，不应作为追求“更早”的优化手段。Android 17 的 [`ActivityThread.handleBindApplication()`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/app/ActivityThread.java)先安装 Provider，再调用 `Application.onCreate()`；放进 Provider 的重活会直接进入更早的主线程关键路径。

启动任务只应包含“初始化完成”可以清晰定义的工作。长期轮询、常驻连接和周期任务属于运行期调度，不应让启动 DAG 一直保持未完成。

## 2. DAG 表达依赖，不表达愿望

### 2.1 节点契约

一个可调度节点至少要声明：

| 字段 | 含义 |
| --- | --- |
| `id` | 稳定且唯一的标识，用于依赖和观测 |
| `process` | 允许执行的进程 |
| `phase` | TTID、TTFD 或延后阶段 |
| `dependencies` | 硬依赖与软依赖 |
| `executionContext` | Main、CPU、I/O 或供应商指定线程 |
| `run` | 任务逻辑及完成信号 |
| `failurePolicy` | 失败、降级、跳过后继或终止启动 |
| `timeoutPolicy` | 超时后的协作取消与替代结果 |
| `traceName` | 固定低基数的诊断名称 |

下面的接口用于说明任务完成必须带结果，不能只返回“已提交异步工作”：

```kotlin
interface StartupTask<T> {
    val id: String
    val process: String
    val phase: StartupPhase
    val dependencies: Set<Dependency>
    val executionContext: ExecutionContext

    suspend fun run(scope: StartupScope): TaskResult<T>
}

sealed interface TaskResult<out T> {
    data class Success<T>(val value: T) : TaskResult<T>
    data class Degraded<T>(val fallback: T, val cause: Throwable) : TaskResult<T>
    data class Failed(val cause: Throwable) : TaskResult<Nothing>
}
```

这里用 `suspend` 表达逻辑完成点，框架也可以用 `ListenableFuture`、`CompletionStage` 或回调实现。关键要求是：后继只能在前驱产生允许传播的终态后就绪。某个 SDK 的 `startAsync()` 返回，不代表 SDK 已可供后继使用。

### 2.2 边的语义

约定 `A → B` 表示 B 等待 A。依赖需要区分：

- **硬依赖**：A 成功或给出满足契约的降级结果后，B 才能运行。
- **软依赖**：B 希望在 A 之后运行；A 失败时，B 有明确的独立路径。
- **顺序约束**：两者不共享结果，只因线程安全或供应商契约需要排序。

“A 超时就当作完成”会破坏硬依赖语义。安全做法是把超时映射成 `Degraded` 或 `Failed`，再由 B 的契约决定能否继续。

条件任务也不能简单从运行期跳过。构图时移除节点后，需要重新检查所有后继：依赖是否仍有提供者、是否存在备用节点、图是否仍然连通。

### 2.3 构图阶段必须拒绝无效输入

在任何任务执行前检查：

- 重复 ID 和不存在的依赖；
- 自依赖与环；
- 被禁用的节点仍被硬依赖；
- Main 任务等待一个需要 Main 才能完成的 worker；
- 当前进程不允许的节点；
- phase 倒挂，例如首帧任务硬依赖 `DEFERRED`；
- 多个节点写同一非线程安全状态却没有顺序约束。

DFS 的 GRAY 集或 Kahn 拓扑排序都能检测环。错误信息应输出完整环路径，例如 `A → B → C → A`，方便配置和模块负责人定位。

## 3. 关键路径决定理论下界

### 3.1 最长依赖链

在一个不考虑资源竞争的 DAG 中，结束节点的最早完成时间由最长依赖路径决定：

```text
Logger(8 ms) ─→ Crash(20 ms) ─┐
                               ├→ HomeState(15 ms) → FirstFrame
Device(12 ms) → Config(10 ms) ┘
```

上例两条前驱路径分别是 28 ms 和 22 ms，汇合后的理论关键路径是 43 ms。缩短不在关键路径上的任务，不一定改变第一帧结束时间。

这只是理论模型。设备上的完成时间还受以下因素影响：

- 就绪任务在 executor 队列中等待；
- CPU 核心、频率、热状态和其他进程竞争；
- 多个任务争用磁盘、Binder、类加载锁或同一连接池；
- Main 与 RenderThread 被后台初始化抢占；
- GC 和大量对象分配；
- 任务时长会随缓存、网络和入口变化。

因此，关键路径应从每次 Trace 的真实开始/结束和依赖关系重建，而非把代码评审中的估计耗时写死。P50 的关键路径也可能与 P95 不同。

### 3.2 优先级只影响已经就绪的任务

优先级不能越过依赖。它只在多个任务同时就绪且争用同一执行资源时决定谁先运行。

需要区分三种概念：

1. **业务阶段**：TTID 前、TTFD 前、延后。
2. **executor 排队优先级**：同一队列中先取哪个任务。
3. **Linux 线程 nice 值**：线程被内核调度时的 CPU 权重。

把三者压成一个 `priority` 整数，会让“高优任务在后台队列靠前”和“把线程 nice 调高”混成同一操作。框架 API 应分别建模。

## 4. 失败、超时和取消属于任务协议

### 4.1 超时不等于停止

Java/Kotlin 的超时通常只让等待方停止等待。底层网络、Binder、文件 I/O 或供应商线程可能继续运行。`Future.cancel(true)` 和线程 interrupt 也是协作信号，代码若不响应，工作不会消失。

每个可超时任务要回答：

- 超时后能否取消底层操作？
- 晚到结果是否还允许写共享状态？
- 重试会不会与旧请求并发？
- 后继使用什么备用值？
- 下一次启动能否安全重试？

不要为每个任务临时创建一个线程，再用 `CountDownLatch.await(timeout)` 包住它。这样会让 executor 中的工作线程等待另一个线程，增加线程和栈内存，还无法停止被包裹任务。

### 4.2 失败传播

建议至少支持这些策略：

| 策略 | 行为 |
| --- | --- |
| `FAIL_GRAPH` | 终止依赖该结果的关键路径，展示可恢复错误 |
| `USE_FALLBACK` | 产出类型一致的本地或默认结果 |
| `SKIP_DEPENDENTS` | 跳过所有无法满足硬依赖的后继 |
| `CONTINUE_SOFT` | 仅软依赖继续，记录能力缺失 |

框架要保存原始异常、任务 ID、进程、线程和已运行时长。捕获 `Throwable` 后无条件继续会掩盖 `OutOfMemoryError` 等进程级风险，也会让后继在半初始化状态运行。

### 4.3 幂等与重入

初始化任务可能因配置变化、进程恢复、失败重试或测试重复执行。理想任务应：

- 多次调用返回同一有效状态；
- 部分失败后能清理临时资源；
- 注册监听器时能成对注销；
- 不把“对象已创建”误当作“初始化已完成”；
- 并发调用由单一状态机合并。

若供应商 SDK 不支持重入，适配层应串行化调用并保存明确状态，禁止多个业务模块各自初始化。

## 5. App Startup：同步依赖图

### 5.1 1.2.0 的执行模型

[Jetpack App Startup](https://developer.android.com/topic/libraries/app-startup) 用一个 `InitializationProvider` 发现 manifest `<meta-data>` 中的 `Initializer`。1.2.0 源码中的 `AppInitializer`：

1. 读取 Provider 的 metadata，找到值为 `androidx.startup` 的类名；
2. 通过反射创建 `Initializer`；
3. 深度优先初始化 `dependencies()`；
4. 用 `initializing` 集合检测环；
5. 调用 `create(context)` 并缓存结果；
6. 用 AndroidX Trace 包住发现和每个 Initializer。

自动初始化发生在 `InitializationProvider.onCreate()`，也就是应用主线程上的 Provider 安装阶段。它不是 Binder 线程回调，也不会自动把 `create()` 移到 worker。

下面的初始化器声明 Logger 依赖本地配置：

```kotlin
class LoggerInitializer : Initializer<Logger> {
    override fun create(context: Context): Logger {
        return Logger.create(context)
    }

    override fun dependencies(): List<Class<out Initializer<*>>> {
        return listOf(LocalConfigInitializer::class.java)
    }
}
```

App Startup 会先完成 `LocalConfigInitializer.create()`，再调用 Logger。`create()` 必须同步返回可用实例；内部若只提交异步任务，依赖顺序对逻辑就绪没有保证。

### 5.2 适用范围与限制

App Startup 适合：

- 合并多个自动初始化 Provider；
- 用静态、同步依赖表达少量必要初始化；
- 提供可手动触发的惰性初始化入口；
- 让库与应用通过 manifest merger 合并初始化声明。

它没有任务优先级、内建超时、取消、异步结果或运行期改图。所有 eager initializer 仍占用 Provider 启动阶段的主线程时间。

需要惰性初始化时，从最终 Manifest 删除对应 `<meta-data>`，再在需要处调用 `AppInitializer.initializeComponent()`。官方文档明确指出，关闭一个组件的自动初始化也会关闭由它带入的依赖；手动初始化时依赖会一并初始化。

### 5.3 多进程边界

`AppInitializer` 是进程内单例，但 `InitializationProvider` 是否运行由 Manifest 的 `android:process` 决定：

- 未声明 `android:process` 时，Provider 属于应用默认进程；
- 若应用显式为多个进程声明不同 Provider，相关进程各有自己的单例和结果；
- 一个默认 Provider 不会因为应用存在四个子进程就自动执行四次。

1.2.0 修复了 Provider 定义在 secondary process 时的 metadata 查找问题，这表示库支持显式的多进程 Provider 配置，不表示所有 initializer 默认复制到每个进程。最终行为必须以 merged manifest 为准。

需要在命名进程运行独立初始化图时，应使用单独的 `InitializationProvider` 子类、唯一 authority 和只属于该进程的 metadata：

```kotlin
class WorkerInitializationProvider : InitializationProvider()
```

```xml
<provider
    android:name=".WorkerInitializationProvider"
    android:authorities="${applicationId}.androidx-startup.worker"
    android:exported="false"
    android:process=":worker">

    <meta-data
        android:name="com.example.worker.WorkerInitializer"
        android:value="androidx.startup" />
</provider>
```

这会在 `:worker` 进程形成独立的 `AppInitializer`、依赖遍历和结果缓存，不会与默认进程共享“已初始化”状态。跨进程完成关系仍要用 Binder、Provider 或持久状态表达，不能画成一条进程内 DAG 边。

### 5.4 发现、遍历与动态特性边界

App Startup 1.2.0 的 manifest discovery 先读取当前 `InitializationProvider` 的 `ProviderInfo.metaData`，只接受 value 等于 `androidx.startup` 标记的条目，再对 key 执行 `Class.forName()` 并收集实现了 `Initializer` 的类。发现结束后才进入依赖初始化。

初始化算法是进程内的深度优先遍历：

1. 节点进入递归路径时加入 `initializing` 集合；
2. 先递归执行 `dependencies()`；
3. 依赖完成后同步调用当前节点的 `create()`；
4. 返回值写入 `mInitialized`，当前进程后续请求直接复用；
5. 路径再次遇到同一类时抛出循环依赖异常。

这套算法不保证同层无依赖节点的稳定顺序。metadata 与集合遍历顺序都不是业务契约；有先后要求就必须写进 `dependencies()`。`isEagerlyInitialized()` 只表示节点是否来自 manifest 主动发现，不表示组件健康、异步准备完成或跨进程可用。

主动发现会在 Provider 阶段直接加载 initializer 类。若 metadata 指向尚未安装的动态特性模块，`Class.forName()` 失败会被包装成 `StartupException`，进程可能在 `Application.onCreate()` 之前终止。可选模块的桥接 initializer 应留在 base，或等模块安装完成后从明确业务入口手动初始化；不要假设 ClassLoader 会跳过缺失类。

App Startup 会为发现过程和 initializer 创建 Trace section。排查时同时检查 merged manifest、每个进程的 Provider、`Startup`/initializer slice、主线程 I/O/Binder/锁和首个消费者的延迟。`create()` slice 结束只证明同步方法返回；内部提交的异步工作仍需自己的完成事件。

## 6. Alpha：旧代码可以参考，不能按现代库假设

### 6.1 固定提交中的行为

Alpha 的选定提交 `04fe7f2` 日期为 2018-12-14，当前仓库默认分支仍停在这一提交。它提供：

- `Project.Builder.add(task).after(predecessors)` 构建任务图；
- `Task(name, true)` 通过 Main `Handler` 执行；
- 后台 Task 使用 `AlphaConfig` 的共享 `ExecutorService`；
- `MAIN_PROCESS_MODE`、`SECONDARY_PROCESS_MODE`、`ALL_PROCESS_MODE` 和精确进程名选图；
- 任务耗时记录与 Project 完成回调。

下面的写法与该提交的 Builder 和 Manager 签名一致：

```java
Task config = new LocalConfigTask();
Task logger = new LoggerTask();

Project project = new Project.Builder()
        .setProjectName("app-init")
        .add(config)
        .add(logger).after(config)
        .create();

AlphaManager manager = AlphaManager.getInstance(appContext);
manager.addProject(project, AlphaManager.MAIN_PROCESS_MODE);
manager.start();
```

`addProject()` 返回 `void`，因此不能与 `start()` 链式调用。`after(config)` 表示 Logger 等待 Config。

### 6.2 源码中需要补强的边界

采用 Alpha 时至少核对这些实现事实：

- 默认 executor 的 core/max 都是 `availableProcessors()`，队列是无界 `LinkedBlockingQueue`；max 与 core 相同，且所有后台任务共用一池。
- `Task.run()` 返回后立刻标记完成并通知后继，不支持异步完成信号。
- 用户 `run()` 外层没有 `try/finally`；异常会阻止完成通知，后继可能永远不启动。
- `waitUntilFinish()` 与 Main Task 同时使用会死锁，源码注释已经警告。
- execute priority 只在通知 successor 时排序；后台任务提交到普通 FIFO executor 后，没有全局优先队列保证。
- 状态机把非 IDLE 的重复 `start()` 报告为可能存在循环，但没有在执行前输出完整环路径。
- 没有内建的类型化结果、取消和单任务超时协议。

这些问题不说明 DAG 思想无效，只说明该仓库更适合作为源码参考或内部 fork 的起点。直接引入前要评估 target API 37、构建工具、并发安全、维护责任和依赖供应链。

## 7. 什么时候需要自研

任务数不是选型的决定条件。十个带异步完成、跨进程和复杂失败语义的任务，可能比一百个同步任务更需要专用框架。

自研通常由这些需求触发：

- 异步结果必须成为依赖图的一等状态；
- 需要类型化的失败、降级、超时和协作取消；
- 每个进程使用不同任务图；
- 编译期聚合多模块声明，并在构建阶段检查图；
- 需要基于真实 Trace 重建关键路径；
- 远程实验只能在受控白名单内改变阶段或开关；
- crash loop 后要进入安全图；
- 现有库的生命周期、维护或供应链风险不可接受。

自研成本包括调度状态机、可观测性、故障注入、并发测试、进程测试和长期兼容。若需求只是统一几个同步 initializer，App Startup 更简单。

一个最小架构应包含：

```text
声明层 → Graph Validator → Scheduler → Main / CPU / I/O executors
             │                │
             ├─ 环与契约检查   ├─ 结果、超时、取消
             └─ 进程/阶段校验  └─ Trace 与指标
```

声明层不应允许业务直接拿 executor；调度器才能记录排队时间、运行时间和依赖状态，并在退出或降级时保持一致行为。

## 8. 异步初始化与 executor 策略

### 8.1 Main 是 Looper，不是线程池

Main 任务通过当前调用或 `Handler`/dispatcher 排队。`post()` 只表示入队，执行时间取决于前方消息、同步屏障和 frame callback。把十个任务从 `Application.onCreate()` 改成十次 `mainHandler.post()`，可能只是把成本移动到首帧附近。

Main 线程上禁止：

- 等待 worker 的 `CountDownLatch`、`Future.get()` 或阻塞式 `await`；
- 让 worker 依赖 Main 回调后完成，形成反向等待；
- 在 rejection handler 中执行原本要去后台的任务；
- 用 SplashScreen 无限覆盖尚未结束的初始化。

必须在 Main 调用但可拆分的 API，应只把很短的状态切换留在 Main，准备工作在 worker 完成后通过非阻塞状态机继续。

### 8.2 CPU 任务

CPU 并发不是 `availableProcessors() + 1` 的固定公式。`availableProcessors()` 只报告当前可用逻辑处理器数量，不能表达大小核性能、调频、温度、RenderThread 竞争和设备负载。

CPU executor 应：

- 使用有限并发和有界队列；
- 把首帧关键计算与延后预计算分开；
- 避免多个库各建一个“按核数”线程池造成过度并发；
- 在低、中、高设备档位用 Perfetto 检查 Main/RenderThread 的 Runnable 等待；
- 记录 submit-to-start 排队时间与 run 时间。

线程更多只会在有可用 CPU 时提高并行度。首帧期间把所有核心占满，可能让 Main 与 RenderThread 更慢。

### 8.3 I/O 任务

I/O 会阻塞，不代表线程数可以无限增加。启动时大量并发读会放大：

- 存储队列和 page fault；
- 数据库锁与连接池等待；
- Binder 服务排队；
- TLS、DNS 和服务端限流；
- 每个线程的栈内存。

磁盘、数据库、Binder 和网络最好按资源设置并发上限，避免一个慢域名占满所有 worker。网络配置也不应成为首帧硬依赖；使用上一份已验证缓存或本地默认值更稳妥。

### 8.4 队列与拒绝策略

[`ThreadPoolExecutor`](https://developer.android.com/reference/java/util/concurrent/ThreadPoolExecutor) 在 core 线程满后先尝试入队。无界 `LinkedBlockingQueue` 会让线程数停在 core，`maximumPoolSize` 不再发挥扩容作用，同时允许积压无限增长。

有界队列便于限制资源，但拒绝策略必须符合启动语义。`CallerRunsPolicy` 会在提交线程直接执行被拒任务；若调用者是 Main，后台重活会回到 UI 线程。因此：

- 关键任务被拒应记录并走明确降级或失败路径；
- 延后任务可以丢弃、合并或稍后重试；
- 主线程提交禁止使用会执行重活的 caller-runs；
- 同一 key 的预热任务应去重，避免队列重复。

### 8.5 线程优先级

[`Process.setThreadPriority()`](https://developer.android.com/reference/android/os/Process)设置当前线程的 Linux nice；它不改变 DAG 依赖，也不保证 I/O 顺序。

低紧迫度 worker 可使用 `THREAD_PRIORITY_BACKGROUND`，但首帧关键 worker 是否保留默认优先级要通过 Trace 验证。盲目提升后台线程会抢占 Main 和 RenderThread。新线程可能继承创建线程的调度属性，线程工厂应显式命名，并在线程执行体内设置允许的优先级。

## 9. 多进程任务图

### 9.1 每个进程只构建自己的图

Android 10+ 可用 `Application.getProcessName()` 获取当前进程。推荐先选择进程配置，再实例化任务，避免子进程加载主进程 initializer 类及其静态依赖。

| 进程 | 常见必要任务 | 不应默认加载 |
| --- | --- | --- |
| 主进程 | UI、首屏状态、核心观测 | push 专用连接、独立下载器 |
| `:push` | 消息解析、最小存储与上报 | UI、图片、广告、主页数据 |
| `:web` | WebView 所需配置 | 主进程全部 SDK |
| 隔离/远端服务 | 服务契约所需能力 | 宿主业务单例 |

跨进程依赖不能用进程内 DAG 边表达。应使用 Binder/Provider 等明确协议，包含 Ready、Degraded、Dead、超时和版本状态。主进程首帧尽量不阻塞等待子进程启动。

### 9.2 Provider 与 App Startup

检查 merged manifest 中每个 Provider 的进程。某个库若把 `InitializationProvider` 显式放到子进程，该进程会有独立 App Startup 图；默认 Provider 只属于默认进程。

不要在 `Initializer.create()` 里加载全量模块后再用 `if (processName...)` 跳过，这时类加载和静态初始化可能已经发生。更好的方式是：

- 不在该进程声明 initializer；
- 该进程使用专用 Provider/graph；
- 或在更早、依赖更少的入口选择专用实现类。

## 10. 动态配置与 A/B 实验

### 10.1 远程配置只能调整已知安全空间

启动不能等待当次网络配置。客户端使用上一轮持久化且校验通过的配置；缺失、过期或解析失败时回到内置图。

远程配置建议只允许：

- 开关一个已有且可独立禁用的任务；
- 在预定义 phase 集合中选择；
- 在安全范围内调整 executor 排队优先级；
- 选择客户端内置的完整图版本。

远程数据不应提供类名、任意依赖边或可执行代码。对配置执行真实性/完整性校验、schema 和客户端版本校验，并设置有效期与一键回退。

### 10.2 客户端验证

启用配置前检查：

1. 图版本与当前应用版本兼容。
2. 所有 task ID 来自本地白名单。
3. 硬依赖存在且没有被禁用。
4. 图无环、phase 合法、进程匹配。
5. 关键功能保留可用路径。
6. 配置未过期，实验分组稳定。

校验失败只上报低基数错误码和图版本，不执行部分配置。默认图要随客户端一起经过功能与性能测试。

### 10.3 实验指标

实验同时观察：

- 冷/温/热启动 TTID 与 TTFD 分布；
- 每个任务的排队、运行、结果和关键路径；
- 启动 crash、ANR、进程异常退出；
- 首屏错误、降级率和关键操作成功率；
- CPU、内存、线程、I/O 与首帧 FrameTimeline；
- 按入口、设备档位、系统版本和进程分组的长尾。

样本量和持续时间由基线方差、最小可检测差异、分流比例和业务周期决定，不能统一写成“一周且 p < 0.05”。要预先定义主指标、护栏指标和停止条件，避免在多个分位与分组中反复挑选有利结果。

### 10.4 crash loop 与回退

启动图变更可能在监控 SDK启动前崩溃。应用应在框架外保存很小的启动状态：

- 本次图版本；
- 进入启动与成功到达可用态的标记；
- 连续失败计数和过期时间；
- 安全图版本。

检测到连续早期失败时，下一次启动使用内置安全图并禁用实验配置。状态写入本身要轻量、原子且不放大主线程 I/O。

## 11. 可观测性：测量排队和结果

每个任务至少记录：

| 时间/状态 | 用途 |
| --- | --- |
| graph ready | 图验证完成 |
| task ready | 依赖已经满足 |
| task start | executor 开始运行 |
| task finish | 逻辑结果产生 |
| outcome | success/degraded/failed/cancelled/timeout |
| thread/process | 解释调度与进程路径 |

`task start - task ready` 是排队时间，`task finish - task start` 是运行时间。只记录运行时间会漏掉 executor 饱和和优先级反转。

使用 `androidx.tracing` 给任务增加稳定 slice，并把依赖关系与 Task ID 一同保存在本地基准结果中。线上指标控制采样和维度，不把动态 URL、用户 ID 或异常全文作为标签。

验证优化时使用与 21.1 相同配置的 Macrobenchmark：

1. A/B 产物只改变任务图或 executor 策略。
2. 编译模式、入口、数据、设备和温度条件一致。
3. 同时比较 TTID、TTFD、FrameTimeline 与任务图关键路径。
4. 打开回归样本 Trace，确认收益来自预期任务，而非首屏内容减少。
5. 在小流量中确认稳定性和功能护栏。

Android 17 的 `ApplicationStartInfo` 适合补充历史启动类型、原因和系统时间戳。完成监听或历史记录不能回到过去改变当前启动图；当前进程的 DAG 选择应基于已知入口、进程和本地安全配置。

## 12. 选型结论

| 需求 | App Startup 1.2.0 | Alpha `04fe7f2` | 自研 |
| --- | --- | --- | --- |
| 合并自动 Provider | 适合 | 不负责 | 可实现，但收益有限 |
| 同步静态依赖 | 适合 | 支持 | 支持 |
| worker 并发 | 不支持 | 支持单共享池 | 可按契约实现 |
| 异步完成信号 | 不支持 | 不支持 | 可实现 |
| 类型化失败/降级 | 不支持 | 不支持 | 可实现 |
| 超时/取消 | 不支持 | 无内建协议 | 可实现 |
| 多进程选图 | 依赖 Manifest | 内建模式 | 可实现 |
| 动态安全配置 | 不支持 | 本地 Builder/XML | 可实现受控版本 |
| 维护责任 | AndroidX | 团队需接管旧代码风险 | 团队完全负责 |

推荐从需求出发：

- 少量必须 eager 的同步组件，用 App Startup，并移除不必要的自动 initializer。
- 需要简单 worker DAG 且团队愿意维护 fork，可参考 Alpha 的图模型，同时补齐结果、异常、环检测和 executor。
- 需要异步结果、复杂失败、多进程和安全实验时，再建设自研框架。

无论选哪一种，收益都来自减少首屏工作、缩短真实关键路径和控制资源竞争。框架名称本身不会改善 TTID。

## 检查清单

- [ ] 每个任务有 owner、进程、phase、线程和完成定义。
- [ ] 硬依赖、软依赖、失败和降级语义明确。
- [ ] 构图阶段检查缺失节点、环、phase 与进程。
- [ ] Main 不阻塞等待 worker，worker 不反向依赖 Main。
- [ ] 异步 API 的逻辑完成点进入任务状态。
- [ ] 超时不会把硬依赖伪装成成功。
- [ ] executor 有界，并记录排队与运行时间。
- [ ] caller-runs 不会把后台重活带回 Main。
- [ ] 每个进程只构建所需图，Provider 归属已核对。
- [ ] 远程配置来自本地白名单，失败回到内置图。
- [ ] 具备早期 crash 安全图和回退演练。
- [ ] Macrobenchmark 同时验证 TTID、TTFD、帧与功能。

## 参考资料

- [AOSP Android 17 `ActivityThread`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/app/ActivityThread.java)
- [Jetpack App Startup 指南](https://developer.android.com/topic/libraries/app-startup)
- [Jetpack Startup 1.2.0 发布说明](https://developer.android.com/jetpack/androidx/releases/startup)
- [Jetpack Startup 1.2.0 源码包](https://dl.google.com/dl/android/maven2/androidx/startup/startup-runtime/1.2.0/startup-runtime-1.2.0-sources.jar)
- [Alibaba Alpha 固定提交](https://github.com/alibaba/alpha/tree/04fe7f22c469de66fed98c341334c954dfabafb2)
- [`ThreadPoolExecutor` 队列与拒绝策略](https://developer.android.com/reference/java/util/concurrent/ThreadPoolExecutor)
- [Android 线程性能指南](https://developer.android.com/topic/performance/threads)
- [`android.os.Process` 线程优先级](https://developer.android.com/reference/android/os/Process)
