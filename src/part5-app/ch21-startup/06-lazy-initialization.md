---
title: "延迟初始化与按需加载"
chapter: "21.6"
section: "21.6"
status: finalized
applicable_versions: "Android 10 (API 29) - Android 17 (API 37)"
last_verified: "2026-08-14"
last_verified_against: "AOSP android-17.0.0_r1 LegacyMessageQueue / CombinedDeliMessageQueue; Android 17 MessageQueue behavior change; current Android Developers launch-time / App Startup / Play Feature Delivery docs"
confidence: high
sources:
  - type: aosp
    path: "frameworks/base/core/java/android/os/LegacyMessageQueue/MessageQueue.java + frameworks/base/core/java/android/os/CombinedDeliMessageQueue/MessageQueue.java (android-17.0.0_r1, IdleHandler / next())"
  - type: official
    path: "https://developer.android.com/about/versions/17/changes/messagequeue"
  - type: official
    path: "https://developer.android.com/topic/performance/vitals/launch-time"
  - type: official
    path: "https://developer.android.com/topic/libraries/app-startup"
  - type: official
    path: "https://developer.android.com/guide/playcore/feature-delivery"
  - type: clippings-structure-ref
    path: "Clippings/Android 性能优化 - CPU 优化（下）：减少 CPU 闲置时刻和等待，提升利用率.md"
  - type: clippings-structure-ref
    path: "Clippings/Android 性能优化 - 原理：重新认识应用的速度优化.md"
  - type: clippings-structure-ref
    path: "Clippings/Android 性能优化 - so 文件的体积优化实战.md"
tags: [lazy-init, idlehandler, on-demand-loading, app-startup]
related_chapters: ["21.2", "21.3", "1.13"]
pipeline_stage: finalized
task6_state: reviewed
task9_state: reviewed
task2b_state: fixed
---

# 延迟初始化与按需加载

## 范围

延迟初始化的目标是减少启动关键区间内的工作，同时保证任务在使用前完成、失败时可恢复。这里的关键区间包括从系统收到启动请求到 App 第一帧的 TTID（Time to Initial Display），以及到主要内容可用的 TTFD（Time to Full Display）。把 `Application.onCreate()` 中的代码统一移进线程池，只会改变执行线程；让一批任务在首帧后同时开始，还会制造新的 CPU 和 I/O 竞争。

平台源码锚点为 Android 17 / API 37 / `android-17.0.0_r1`。重点讨论五件事：

- 如何判断任务能否延后；
- 如何识别“首帧已经提交”；
- `IdleHandler` 能提供什么信号；
- 首次使用和动态 Feature（按需交付的功能模块）怎样管理状态；
- 进程退出、失败、多进程和资源竞争如何处理。

启动依赖图和 Provider 治理分别见 [启动任务编排](./02-startup-framework.md) 与 [ContentProvider 启动治理](./03-contentprovider-optimization.md)。

## 1. 异步、延迟、懒加载不是同一件事

| 手段 | 改变什么 | 没有解决什么 |
| --- | --- | --- |
| 异步执行 | 执行线程 | 任务仍可能与启动争 CPU、I/O、Binder 跨进程通信或锁 |
| 首帧后执行 | 开始时机 | 工作总量没有减少，后续帧仍可能受影响 |
| 首次使用 | 触发条件 | 用户第一次进入功能时可能等待 |
| 按需交付 | 安装包中是否已有代码/资源 | 需要下载、安装、失败和渠道处理 |
| 持久后台任务 | 进程退出后仍可调度 | 不能保证某个精确帧后立即开始 |

“从主线程移到后台”只能消除主线程直接执行时间。若后台任务占满 CPU 性能核、触发大量 page fault（所需内存页尚未驻留而引发的缺页处理）、争用同一数据库，或把结果同步回主线程，它仍会拖慢 TTID、TTFD 或前几帧。

## 2. 先给初始化任务分级

### 2.1 判断问题

每项初始化都要回答：

1. 不执行时，首个 Activity 能否画出正确第一帧？
2. 不执行时，主要内容能否在 TTFD 前达到可用状态？
3. 哪个用户动作会首次需要它？
4. 失败后能否跳过、重试或显示降级页？
5. 任务依赖进程、Activity、账户还是某个动态功能模块的生命周期？
6. 它消耗主线程、CPU、I/O、Binder、网络还是内存？
7. 多个触发者同时到达时，是否会重复初始化？
8. 另一个进程是否也需要独立初始化？

只用“耗时是否超过 10 ms”分类会漏掉依赖与失败语义。一个 1 ms 的首屏路由状态可能不能延后；一次 100 ms 的低频编辑器加载则可以留到用户进入编辑页。

### 2.2 四档执行时机

| 时机 | 适合任务 | 验收重点 |
| --- | --- | --- |
| TTID 前 | 首屏主题、同步路由所需的最小本地状态、首帧必需依赖 | TTID、正确性、StrictMode |
| 首帧提交后 | 用户很快会用到，但不参与第一帧的进程级准备 | 前几帧、TTFD、CPU/磁盘竞争 |
| 首次使用 | 低频第三方 SDK、二级页面、可恢复功能 | 首次点击时延、失败率、取消 |
| 持久后台 | 可延后且需要跨进程存活的同步、上传、维护任务 | 约束、功耗、重试、幂等 |

这里的 StrictMode 是用于发现主线程磁盘、网络等违规访问的开发期诊断工具；“幂等”表示同一任务重复执行仍得到可接受的同一业务结果。

“后台空闲”不是稳定的业务截止时间。任务若必须在用户十秒后点击前准备好，就要声明 deadline（必须完成的最晚业务时点），并在靠近入口时预触发；不能只等一次时机不确定的 IdleHandler。

## 3. 首帧后执行

### 3.1 不要用 `Handler.post` 猜首帧

`setContentView()` 后调用 `view.post { ... }`，只能说明 Runnable（可执行任务）进入了主线程消息队列，不能证明第一帧已经提交。`Traversal` 是 View 系统执行测量、布局和绘制的一帧任务；同步屏障会暂时拦住普通同步消息，让显示相关的异步消息先运行。队列中已有的消息、屏障和 Traversal 调度都会影响这个 Runnable 的执行位置。

适用版本从 API 29 开始。硬件渲染窗口可以用 `ViewTreeObserver.registerFrameCommitCallback()` 观察当前渲染内容已提交到 swap chain，也就是等待显示的一组图形缓冲区。下面的回调只打开调度门（允许后续任务开始的条件开关），不在回调里执行初始化：

```kotlin
val root = findViewById<View>(android.R.id.content)

root.viewTreeObserver.registerFrameCommitCallback {
    startupScheduler.openGate(Trigger.AFTER_FIRST_FRAME_COMMITTED)
}
```

这个信号针对注册后参与提交的帧；注册太晚只能观察后续帧。回调表示帧已进入 swap chain，不保证显示系统已经把它 present 到物理屏幕。软件渲染时该 API 不会回调。它适合性能调度，不应成为业务正确性的唯一条件。若应用允许软件渲染，要提供独立的保守触发，或把任务改成首次使用时再执行。

### 3.2 打开门后也要限流

首帧后队列至少要控制：

- 同时运行的 CPU 任务数；
- I/O 任务是否访问同一文件、数据库或 mmap（文件到内存的映射）区域；
- 主线程回调是否分散到多个帧；
- Activity 退出后，页面级任务是否取消；
- 进程级任务是否只触发一次；
- 前台出现 jank（可感知的卡顿帧）、thermal（设备发热或降频）或低电量信号时，能否暂停非必要预热。

任务应声明资源类型和 deadline。调度器再根据设备与运行状态安排执行；项目自定的 `maxCostMs` 只是成本估计，不是系统保证的空闲预算。

### 3.3 TTFD 仍然要守住

从 TTID 前移走的任务可能延长 TTFD。首帧后任务应区分：

- TTFD 必需：主要内容和主要交互依赖；
- 入口预热：只降低未来第一次点击成本；
- 无用户时限：日志上传、索引维护等。

只有第一类进入 TTFD 完成条件。`reportFullyDrawn()` 用来通知系统“主要内容已绘制且可用”，其余任务不应阻止这个调用，也不应在 TTFD 前集中占用资源。

## 4. 首次使用：共享一次初始化结果

### 4.1 统一入口必须有状态

首次使用的判断不能散落成多处 `if (!initialized) init()`。统一入口需要表达：

- `NotLoaded`：尚未加载；
- `Loading`：正在加载；
- `Ready`：结果可用；
- `Failed`：加载失败，并保留失败原因。

下面的示例用互斥保证同一时刻只有一个 loader（执行初始化的函数）运行，并把成功结果共享给同一进程内的后续调用者。显式重试或取消后的再次调用仍可能重新执行 loader：

```kotlin
sealed interface LoadState {
    data object NotLoaded : LoadState
    data object Loading : LoadState
    data object Ready : LoadState
    data class Failed(val cause: Throwable) : LoadState
}

class FeatureGate<T : Any>(
    private val timeout: Duration,
    private val loader: suspend () -> T,
) {
    @Volatile
    private var instance: T? = null

    private val mutex = Mutex()
    private val _state = MutableStateFlow<LoadState>(LoadState.NotLoaded)
    val state: StateFlow<LoadState> = _state.asStateFlow()

    suspend fun getOrLoad(): T {
        instance?.let { return it }
        (_state.value as? LoadState.Failed)?.let { throw it.cause }

        return mutex.withLock {
            instance?.let { return it }
            (_state.value as? LoadState.Failed)?.let { throw it.cause }
            _state.value = LoadState.Loading

            try {
                withTimeout(timeout) { loader() }.also {
                    instance = it
                    _state.value = LoadState.Ready
                }
            } catch (cancelled: CancellationException) {
                _state.value = LoadState.NotLoaded
                throw cancelled
            } catch (failure: Exception) {
                _state.value = LoadState.Failed(failure)
                throw failure
            }
        }
    }

    suspend fun retry(): T {
        mutex.withLock {
            if (_state.value is LoadState.Failed) {
                _state.value = LoadState.NotLoaded
            }
        }
        return getOrLoad()
    }
}
```

loader 要自行选择 `Dispatchers.IO`、受控 CPU dispatcher（协程的执行线程配置）或主线程；统一入口不应猜测线程。超时值应来自功能允许的最长等待时间和设备实验，不宜写成全项目共用常量。

这个示例在调用者 coroutine（协程）中执行 loader。页面级初始化可以随页面取消；进程级初始化应由 application scope，也就是与 App 进程同生命周期的 `CoroutineScope` 发起，避免第一个 Activity 销毁时取消所有等待者。失败会被缓存，只有显式调用 `retry()` 才会再执行 loader；生产实现还要加入逐步延长等待时间的退避策略和重试次数上限。

### 4.2 预触发要靠近入口

预触发的目标是利用用户即将进入功能前的自然间隔。例如：

- 进入“发布”页后预热拍摄模块；
- 详情页出现编辑权限后准备编辑器；
- 用户打开支付确认页后准备非敏感展示资源。

预触发仍要可取消。不要把 hover（鼠标或触控笔指针悬停）、滚动经过或一次曝光都变成不可取消的重型初始化。

## 5. `IdleHandler` 的准确语义

### 5.1 它表示队列将要等待

`Looper` 是线程持续从 `MessageQueue` 取消息并执行的循环。[`MessageQueue.IdleHandler`](https://developer.android.com/reference/android/os/MessageQueue.IdleHandler)会在所属 Looper 没有可立即分发的消息、准备等待更多消息时收到 `queueIdle()`。即使队列里仍有未来时间点才到期的消息，它也可能被调用。

返回值含义：

- `false`：本次调用后移除；
- `true`：以后进入 idle 状态时仍可调用。

它不表示：

- CPU 利用率低；
- RenderThread 或 GPU 空闲；
- 下一次输入或 VSync（屏幕垂直同步信号）很远；
- 系统给了固定执行预算；
- 设备适合做预解压或大对象构建。

### 5.2 Android 17 的两条实现路径

Android 17 的 [`CombinedDeliMessageQueue/MessageQueue.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/os/CombinedDeliMessageQueue/MessageQueue.java)同时包含 legacy 与 DeliQueue 分支。DeliQueue 是 Android 17 新的并发消息队列实现。`USE_NEW_MESSAGEQUEUE` 由 `@EnabledAfter(targetSdkVersion = BAKLAVA)` 标注，因此面向 Android 17、`targetSdkVersion >= 37` 的应用默认进入 DeliQueue；开发者选项或 `adb am compat` 仍可临时切换这项兼容变更。官方说明见 [Android 17 MessageQueue 行为变更](https://developer.android.com/about/versions/17/changes/messagequeue)。

两条路径的 IdleHandler 外部语义保持一致：

| 路径 | idle 判断 | handler 集合 |
| --- | --- | --- |
| legacy | 队列为空或头消息尚未到期 | 在 `synchronized(this)` 对象锁内复制列表 |
| DeliQueue | `looperCheckIsIdle()` 检查可投递消息 | `mIdleHandlersLock` 下复制列表 |

官方把 DeliQueue 称为无锁 MessageQueue，指的是核心消息数据结构；源码仍用 `mIdleHandlersLock` 保护 IdleHandler 列表，不能推导出类内每项操作都无锁。IdleHandler 回调仍在 Looper 线程执行，回调期间到达的新消息要等它返回。旧实现可对照 [`LegacyMessageQueue/MessageQueue.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/os/LegacyMessageQueue/MessageQueue.java)，更多结构见 [MessageQueue 与 DeliQueue](../../part1-fundamentals/ch01-architecture/13-messagequeue-deliqueue.md)。

不要用反射读取 `MessageQueue` 私有字段。DeliQueue 为兼容二进制仍保留 `mMessages`，但该字段固定为 `null`，旧式队列探测会失效。Android 17 官方指南当前要求相关测试环境至少升级到 Espresso 3.7.0 或 Robolectric 4.17，并把 Robolectric 的 `LEGACY` Looper 模式迁到 `PAUSED`。

### 5.3 只把它当一次性信号

下面的 IdleHandler 只通知调度器“主队列曾进入 idle”，不在主线程执行预热：

```kotlin
Looper.getMainLooper().queue.addIdleHandler {
    startupScheduler.signal(Trigger.MAIN_QUEUE_IDLE)
    false
}
```

调度器收到信号后仍要检查首帧状态、页面可见性、任务 deadline 和资源冲突。返回 `false` 避免每次 idle 都重复触发。

这些写法应禁止：

- 在 `queueIdle()` 读取数据库或文件；
- 在回调中解析大 JSON、创建大量对象或加载 native 库；
- 返回 `true` 轮询业务状态；
- 每个 SDK 各自注册 IdleHandler；
- 把一次 idle 当成进程持续低负载。

`/proc/stat` 和 `/proc/<pid>/stat` 是内核导出的系统级与进程级统计文件。CPU 采样受时间窗口和设备差异影响，只反映历史占用，无法说明主线程 deadline、I/O 队列、GPU、thermal 或马上到来的输入。专用调度器应组合多项运行信号并在目标设备上验证；单个 CPU 百分比不足以作为任务开关。

## 6. Jetpack App Startup 的手动初始化

App Startup 默认通过库提供的 `InitializationProvider` 发现并运行 initializer，也就是实现 `Initializer` 接口的组件初始化器。发现依据来自 Manifest 的 `<meta-data>`。若组件不需要在进程启动时运行，必须先从合并后的 Manifest 移除对应声明；合并后的 Manifest 是 App 与各依赖清单合成后的最终结果。

下面从 Provider 中移除一个 initializer 的 `<meta-data>`：

```xml
<provider
    android:name="androidx.startup.InitializationProvider"
    android:authorities="${applicationId}.androidx-startup"
    android:exported="false"
    tools:node="merge">

    <meta-data
        android:name="com.example.AnalyticsInitializer"
        tools:node="remove" />
</provider>
```

`tools:node="remove"` 会连同依赖库 Manifest 合并进来的 `<meta-data>` 一起处理。只从自己源码里删一行，不能证明最终 Manifest 已移除自动初始化。

需要时再通过 `AppInitializer` 执行组件及其依赖：

```kotlin
val analytics = AppInitializer.getInstance(context)
    .initializeComponent(AnalyticsInitializer::class.java)
```

调用前要确认该组件没有通过另一个 Manifest initializer 的依赖关系提前运行。关闭某个 initializer 的自动初始化，也会关闭它所声明依赖的自动初始化，需要重新检查整张初始化图和首次使用路径。

`AppInitializer` 负责发现组件、按依赖顺序执行并缓存结果，不替应用选择线程、deadline 或失败界面。第三方 SDK 如果还有自己的 Provider 或其他自动初始化开关，也要单独处理。

## 7. 按需 Feature 与 native 库

### 7.1 交付状态机

Play Feature Delivery 的 on-demand module（按需下载的动态功能模块）不会保证随 base module 一起安装；base module 是首次安装时始终存在的基础模块。`startInstall()` 成功只会返回安装 session ID，表示请求已被平台接受，不表示模块已经安装。应用需要监听 session（本次安装会话）状态，并处理：

- 等待与下载；
- 需要用户确认；
- 安装完成；
- 网络、存储、Play 能力或内部错误；
- 取消；
- Activity 重建和进程退出后的状态恢复。

访问代码和资源前要再次检查 `installedModules`。为让基础 `Context` 和动态模块中的 Activity 访问新安装的代码与资源，应按官方接入方式启用 SplitCompat；已有的 `Context` 或 Activity 还可能需要刷新或重建。

`deferredInstall()` 是后台 best-effort（尽力执行、不保证完成时间）请求，不能跟踪进度。功能有明确使用 deadline 时，不能只依赖 deferred install。

### 7.2 外部组件必须留在 base

`exported` 组件允许其他应用或系统通过 Intent 调用。可选模块中的 Activity、Service 或 Receiver 可能在模块尚未安装时就被外部调用，因此官方文档要求这类组件留在 base module，不能放进 optional module（非必装模块）。

需要外部入口时，在 base module 放一个轻量 proxy（代理组件）：

1. 校验 Intent 和权限；
2. 检查模块是否安装；
3. 已安装则转发到内部组件；
4. 未安装则启动下载或返回可恢复错误。

通知、shortcut（桌面快捷方式）和系统 UI 立即需要的资源也应留在 base。新模块的 Manifest 条目不会立即被平台采用，系统组件在一段时间内也可能访问不到新资源。

### 7.3 不要自行实现 `.so` 失败后解压

`.so` 是 Android 使用的 native 共享库文件。“`System.loadLibrary()` 失败后从自定义压缩包解压，再 `System.load()`”会让应用自行处理 ABI（CPU 架构对应的二进制接口）选择、依赖顺序、更新原子性、文件权限、完整性、存储空间和并发加载。这里的更新原子性指切换版本时只能完整成功或完整失败，不能留下半套文件。

低频 native 能力优先随 on-demand feature module 交付，并按官方说明处理 SplitCompat 和 native loader（负责装载 `.so` 的组件）。当前 Play Feature Delivery 文档建议用 ReLinker 加载可选模块中的 native 库；如果使用 `System.loadLibrary()`，还要显式处理模块内依赖库的加载顺序。若业务不经 Google Play 分发，要为对应渠道设计受支持的交付方案，不能假设 Play 路径适用于所有安装来源。

## 8. 何时使用 WorkManager

进程内的首帧后预热适合 application scope 和受控 executor（限制线程数与排队方式的执行器）。WorkManager 是面向可靠持久任务的 Jetpack 调度器，任务可以跨 App 重启和设备重启重新调度。以下情况更适合使用它：

- 用户离开前台后仍应继续；
- 进程被杀或设备重启后需要重调度；
- 需要网络、充电、空闲或存储约束；
- 需要唯一任务、退避重试或任务链。

WorkManager 的调度时机不是精确的“首帧后 500 ms”。不要用它准备马上要点击的功能，也不要为了延迟初始化创建大量没有持久化价值的 `WorkRequest`（一次或周期任务请求）。

任务必须幂等。WorkManager 可以重试或重新调度；若业务只允许产生一次效果，还要用唯一工作、数据库事务或服务端幂等键去重。

## 9. 任务契约与兜底

延迟任务至少声明这些字段：

```yaml
task_id: preload_secondary_route
trigger: AFTER_FIRST_FRAME | FIRST_USE | MAIN_QUEUE_IDLE | PERSISTENT_WORK
scope: PROCESS | ACTIVITY | ACCOUNT | FEATURE
dependencies: [base_config, account_state]
resource: MAIN | IO | CPU | BINDER | NETWORK
deadline: before_feature_entry
failure: SKIP | RETRY | DEGRADE
idempotency_key: account_and_app_version
```

这些字段用于回答任务何时触发、由谁持有、与谁争资源、失败后怎样继续。具体 schema（字段结构定义）可以按项目实现，字段含义应保持稳定，并写入 trace 或日志。

### 9.1 主要风险

| 风险 | 常见原因 | 处理 |
| --- | --- | --- |
| 首次使用卡顿 | loader 太晚或没有预触发 | 靠近入口预触发，提供加载态和取消 |
| 重复初始化 | 多入口、重建、多线程同时触发 | 共享状态入口、互斥、幂等键 |
| 永久未初始化 | 只依赖一次 idle 或一次页面回调 | deadline 触发和首次使用兜底 |
| Activity 泄漏 | 进程级任务持有 Activity/View | 使用不绑定页面的 application context，明确生命周期范围 |
| 取消传播错误 | 页面退出取消了进程级共享加载 | 按任务所有者选择对应的 `CoroutineScope` |
| 多进程不一致 | 每个进程有独立静态状态 | 每进程初始化或通过受控 IPC（进程间通信）协调 |
| 成本后移 | TTID 下降，TTFD/首次点击变慢 | 三个区间一起验收 |
| 资源冲突 | 首帧后任务并发抢 CPU/I/O/Binder | 统一队列、并发上限、暂停机制 |
| 失败风暴 | 自动重试没有退避和上限 | 逐步延长重试间隔；连续失败后暂停自动重试；保留用户触发入口 |

## 10. 验证方法

### 10.1 本地与实验室

每次移动任务后，至少验证下列场景。cold start 表示进程尚不存在，warm start 表示进程仍在但 Activity 需要创建，hot start 表示目标 Activity 已存在并回到前台：

1. cold/warm/hot 启动的 TTID、TTFD；
2. 首帧后直到启动任务稳定期间的 FrameTimeline（每帧预期与实际时间线）和 runnable 排队竞争；
3. 首次进入目标功能的等待、取消、失败和重试；
4. Activity 重建、后台切回和进程重启；
5. 多进程各自的初始化状态；
6. 离线、慢网、低存储和低内存；
7. 不同设备性能档位、刷新率和 thermal 状态；
8. 动态 Feature 的本地安装、用户确认和错误模拟。

性能对照要保持代码、数据、编译模式和入口一致。不能只比较 `Application.onCreate()`，因为延迟任务的成本已经移到后续区间。

### 10.2 Trace 与线上指标

每项任务记录：

- `task_id`、trigger 和 scope；
- 排队、开始、结束时间；
- 执行线程与资源类型；
- 成功、取消、超时、失败原因；
- 首次使用是否等待；
- 策略版本和 App 版本。

Perfetto 用时间线确认主线程、CPU、I/O、Binder 与帧的关系；Android Vitals 汇总线上设备的启动耗时分布；业务指标记录首次入口成功率。验收时要同时查看三组结果，避免一处变快却把成本移到另一处。

## 检查清单

- [ ] 平台锚点为 Android 17 / API 37 / `android-17.0.0_r1`。
- [ ] 每项任务已区分异步、首帧后、首次使用、按需交付和持久后台。
- [ ] TTID 前只保留首帧正确性必需工作。
- [ ] 首帧信号有明确语义，不用普通 `Handler.post` 猜测。
- [ ] 首帧后任务有并发限制、deadline、暂停和取消策略。
- [ ] 首次使用由共享状态入口管理互斥、超时和失败。
- [ ] IdleHandler 只做有界检查或发送信号。
- [ ] 没有用 CPU 百分比代替 UI/系统资源状态。
- [ ] App Startup 自动 `<meta-data>` 已从合并后的 Manifest 验证移除。
- [ ] Dynamic Feature 已处理下载、确认、安装、失败和进程恢复。
- [ ] optional module（非必装模块）没有 exported 组件。
- [ ] 没有自建 `.so` 失败解压加载链路。
- [ ] 需要跨进程存活的任务使用合适的持久调度。
- [ ] TTID、TTFD、首次使用、帧、功耗和异常一起验收。

## 参考资料

- [Android Developers：App startup best practices](https://developer.android.com/topic/performance/appstartup/best-practices)
- [Android Developers：App startup time](https://developer.android.com/topic/performance/vitals/launch-time)
- [Android Developers：App Startup](https://developer.android.com/topic/libraries/app-startup)
- [Android Developers：`MessageQueue.IdleHandler`](https://developer.android.com/reference/android/os/MessageQueue.IdleHandler)
- [Android Developers：`registerFrameCommitCallback`](https://developer.android.com/reference/android/view/ViewTreeObserver#registerFrameCommitCallback%28java.lang.Runnable%29)
- [Android 17：MessageQueue 行为变更](https://developer.android.com/about/versions/17/changes/messagequeue)
- [Android Developers：Play Feature Delivery](https://developer.android.com/guide/playcore/feature-delivery)
- [Android Developers：on-demand delivery](https://developer.android.com/guide/playcore/feature-delivery/on-demand)
- [Android Developers：WorkManager task scheduling](https://developer.android.com/develop/background-work/background-tasks/persistent)
- [AOSP Android 17：Combined Deli MessageQueue](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/os/CombinedDeliMessageQueue/MessageQueue.java)
- [AOSP Android 17：Legacy MessageQueue](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/os/LegacyMessageQueue/MessageQueue.java)
