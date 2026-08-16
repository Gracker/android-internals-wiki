---
title: "多进程启动优化"
chapter: "21.7"
section: "21.7"
status: finalized
applicable_versions: "Android 10 (API 29) - Android 17 (API 37)"
last_verified: "2026-08-14"
last_verified_against: "AOSP android-17.0.0_r1 ActivityThread.java / ZygoteProcess.java / Context.java; current Android Developers process, Binder, ServiceConnection, ApplicationStartInfo, memory, WebView docs"
confidence: high
sources:
  - type: aosp
    path: "frameworks/base/core/java/android/app/ActivityThread.java (handleBindApplication, installContentProviders, callApplicationOnCreate)"
  - type: aosp
    path: "frameworks/base/core/java/android/os/ZygoteProcess.java (startViaZygote)"
  - type: official
    path: "https://developer.android.com/guide/components/processes-and-threads"
  - type: official
    path: "https://developer.android.com/topic/performance/vitals/launch-time"
  - type: official
    path: "https://developer.android.com/topic/libraries/app-startup"
  - type: clippings-structure-ref
    path: "Clippings/Android 性能优化 - 虚拟内存优化(上):线程+多进程优化.md"
  - type: clippings-structure-ref
    path: "Clippings/Android 性能优化 - 原理:重新认识应用的速度优化.md"
  - type: clippings-structure-ref
    path: "Clippings/Android 性能优化 - CPU 优化(上):合理使用线程池,提升 CPU 利用率.md"
  - type: clippings-structure-ref
    path: "Clippings/Android 性能优化 - 任务调度优化:线程+CPU,提升任务调度优先级.md"
tags: [multiprocess, startup, process-priority, ipc, app-startup]
related_chapters: ["21.1", "1.3", "5.8"]
task2b_state: fixed
pipeline_stage: finalized
task6_state: reviewed
task9_state: reviewed
---

# 多进程启动优化

多进程可以隔离崩溃、内存峰值和重型 native（C/C++ 等本地代码）模块，也会新增一套进程运行时、初始化链路和 IPC（Inter-Process Communication，进程间通信）边界。它是一项架构取舍，不能代替主进程自身的启动治理。

App 可以控制的部分包括：是否拆进程、何时启动、每个进程初始化什么、调用方怎样等待远程能力，以及如何在 Android 17 上验证收益。进程优先级与回收规则见 [进程模型](../../part1-fundamentals/ch01-architecture/03-process-model.md)，冷启动分段与 TTID（App 第一帧时间）、TTFD（主要内容可用时间）见 [启动分析](./01-startup-analysis.md)，后台任务约束见 [后台执行限制](../../part1-fundamentals/ch05-cpu-power/07-background-execution.md)。

## 1. 先确认拆进程的目的

在 Manifest 中给组件设置 `android:process=":worker"`，会让它运行在名为“应用包名`:worker`”的私有远程进程中。这个进程通常仍使用应用的 UID（Linux 用户身份）和权限，但拥有独立的 ART（Android Runtime）实例、Java/Kotlin 堆（托管对象内存）、native 堆（C/C++ 动态分配内存）、静态字段、线程、ClassLoader 类加载状态和 Binder 线程池。主进程里的单例不会自动出现在远程进程，远程进程修改的内存对象也不会同步回来。

拆进程常见的合理目标包括：

- 隔离 WebView 宿主、地图、音视频、图片处理或插件运行时的 native 崩溃与内存峰值；
- 让需要独立生命周期的组件脱离主进程，但仍遵守后台启动和前台服务限制；
- 在 32 位设备上减轻单个进程的虚拟地址空间压力；
- 把需要处理不可信输入、且权限需求很少的 Service 放进 isolated process。

普通私有进程与 isolated process 的语义不同：

| 形式 | manifest 示例 | 身份与权限 | 适用场景 |
| --- | --- | --- | --- |
| 应用私有远程进程 | `android:process=":worker"` | 通常沿用应用 UID、权限和数据目录访问能力 | WebView 宿主、播放、上传、插件容器等应用内能力 |
| isolated service | `android:isolatedProcess="true"` | 使用隔离 UID，没有自身应用权限；只能通过 Service API 与外界通信 | 处理不可信输入、需要更小权限面的计算服务 |

多进程也有固定成本：

- 系统要创建进程并绑定应用；
- 每个进程都要建立自己的运行时和堆；
- 该进程中的 Provider、`Application` 和目标组件需要初始化；
- 数据交换改走 Binder、Provider、文件或数据库；
- 系统可能随时回收远程进程，客户端必须恢复连接和请求状态。

WebView 在多进程模式下会把网页内容放进 renderer process（Chromium 渲染进程），多个 WebView 还可能共享同一个 renderer。把 WebView 宿主 Activity 或 Service 放进应用远程进程，新增的是宿主侧 WebView、业务代码和部分 native 状态的隔离，并没有再增加一层 renderer 隔离。评估拆分时，应同时测量主进程峰值、远程进程峰值和全应用 PSS（Proportional Set Size，按比例分摊共享页后的内存），不能只看主进程数字变小。

## 2. Android 17 的进程启动链路

当系统需要运行一个尚无进程可用的组件时，system_server（运行 Android 核心系统服务的进程）会请求 Zygote 创建应用进程。Zygote 是预加载了通用框架代码的进程，可通过 fork（用写时复制派生子进程，修改内存页时才生成私有副本）快速创建 App 进程。Android 17 的 `ZygoteProcess.startViaZygote()` 负责整理参数，并通过 Zygote socket（进程间通信端点）发送创建请求；新进程随后进入 `ActivityThread` 的应用绑定流程。`ActivityThread` 是 App 进程接收组件与生命周期调度的核心类。

相关链路可以压缩成下面几步：

```text
组件请求
  -> system_server 判断目标进程尚未运行
  -> ZygoteProcess.startViaZygote()
  -> Zygote fork 应用进程
  -> ActivityThread.handleBindApplication()
       -> 创建 Application
       -> 安装分配给该进程的 ContentProvider
       -> 调用 Application.onCreate()
  -> 创建目标 Activity / Service / Receiver / Provider 客户端能力
```

这段链路有两个容易混淆的边界。

第一，Provider 按 Manifest 声明的进程归属安装。系统不会把应用里的所有 Provider 安装到每一个进程；默认进程 Provider 属于主进程，声明了 `android:process=":worker"` 的 Provider 属于对应远程进程。一个进程只要分配到了自动初始化 Provider，系统就会在该进程的 `Application.onCreate()` 之前创建并调用它们。

第二，在 `Application.onCreate()` 中按进程名分支，只能约束分支之后的工作，无法撤销已经执行的 Provider 初始化。第三方 SDK 通过 Provider 或 AndroidX App Startup 自动初始化时，需要同时检查 Manifest 进程归属、initializer（组件初始化器）依赖和自动初始化开关。

这也解释了同步 IPC 对首屏的影响：主进程在首帧前访问远程 Provider，或调用异步 `bindService()` 后又同步等待连接结果，都可能触发远程进程冷启动。等待方会把进程创建、Provider 安装、`Application.onCreate()` 和目标服务准备时间计入自己的启动路径。

## 3. 给每个进程定义最小初始化集

`Application.getProcessName()` 从 Android 9（API 28）开始提供，本文覆盖的 Android 10～17 均可直接使用。它比读取 `/proc` 伪文件或枚举运行进程更简单，也避开了系统实现与权限条件差异带来的误判。

下面的代码用于把进程名映射成稳定的角色，并让每个进程只初始化自己的能力：

```kotlin
enum class ProcessRole {
    MAIN,
    WEB,
    UPLOAD,
    OTHER,
}

private fun Application.processRole(): ProcessRole {
    val current = Application.getProcessName()
    return when (current) {
        packageName -> ProcessRole.MAIN
        "$packageName:web" -> ProcessRole.WEB
        "$packageName:upload" -> ProcessRole.UPLOAD
        else -> ProcessRole.OTHER
    }
}

class App : Application() {
    override fun onCreate() {
        super.onCreate()

        when (processRole()) {
            ProcessRole.MAIN -> initMainProcess()
            ProcessRole.WEB -> initWebProcess()
            ProcessRole.UPLOAD -> initUploadProcess()
            ProcessRole.OTHER -> initMinimalProcess()
        }
    }
}
```

这段分支适合控制日志、线程池、业务 SDK、native 库和缓存等 `Application` 阶段工作。它不控制 Provider 阶段；每个自动初始化 Provider 仍要检查 `android:process`，AndroidX App Startup initializer 还要检查依赖关系，并判断是否改为手动初始化。

初始化清单可以按以下原则收缩：

- 主进程只保留首屏展示、路由、安全校验和首屏必需数据；
- Web 进程只准备 Web 宿主所需的桥接、Cookie 或安全策略，不复制整套主进程 SDK；
- 上传进程只准备任务数据库、网络栈和通知能力，不创建图片 UI、页面路由或主进程业务线程池；
- 所有进程共用的日志与崩溃采集也要有进程预算，不能因为“公共基础设施”就在每个进程启动完整线程和周期任务。

静态初始化同样受进程边界影响。Kotlin `object`、Java 静态字段和 JNI（Java 与 native 代码的调用接口）全局状态都是“每个进程一份”。类第一次加载时触发的重工作不会被 `Application` 分支自动拦住，应通过懒加载或显式入口控制。

## 4. 控制远程进程的拉起时机

Android 没有面向普通应用的通用“只创建进程、暂不运行组件”接口。启动 Activity、`startService()`、`bindService()`、访问远程 Provider、接收广播或运行调度任务，都可能创建进程；每种入口同时受对应组件和后台执行规则约束。

可以按用户路径把拉起时机分成四档：

| 时机 | 判断标准 | 建议 |
| --- | --- | --- |
| 首屏前 | 缺少远程结果就无法展示可交互首屏 | 缩小协议和初始化集；优先采用异步协议、deadline（最晚完成时点）和降级路径，并把等待计入 TTID/TTFD |
| 首帧后 | 首屏不依赖，但用户很快可能进入相关功能 | 等首帧完成后再绑定或发送轻量探测，观察是否与主线程争抢 CPU、I/O |
| 临近入口 | 已出现页面曝光、Tab 切换或点击前置动作 | 用明确的产品信号拉起，过期后取消，不做长期无条件预热 |
| 系统调度 | 上传、同步、清理等不依赖当前页面 | 交给 WorkManager、JobScheduler 或符合规则的前台服务 |

首帧后执行不等于“对启动无影响”。低端设备上，新进程会与主进程竞争 CPU、存储 I/O、页缓存（内存中暂存的文件数据）和内存。预热实验至少要比较以下三组：

1. 不预热，用户进入功能时冷启动；
2. 首帧后立即预热；
3. 临近功能入口再预热。

比较指标应包括主进程 TTID/TTFD、远程能力 ready（协议已经可以接受请求的时点）、用户进入功能后的等待、全应用 PSS、低内存回收次数和失败率。只有用户等待时间的下降覆盖资源与稳定性代价，预热才有保留价值。

## 5. 把 Binder ready 建模为异步能力

同步 Binder 调用会阻塞客户端调用线程，直到服务端返回或调用失败。跨进程事务通常由服务端 Binder 线程池执行，多个客户端可能并发进入同一实现，所以服务端状态要满足线程安全。`oneway` 只让跨进程调用方立即返回；同一 Binder 对象的多次 oneway 调用仍按发送顺序逐个分发，而且“已返回”不表示业务已经完成。结果、超时和取消仍需由协议定义。

客户端不能假设远程服务会一直存在。连接状态至少要区分连接中、可用、断开和失败，并处理 Binder 所在进程死亡。

下面的示例展示一个最小连接状态机。业务协程可以异步等待 ready；主线程不能用 `CountDownLatch`（让线程等待计数归零的同步器）、自旋（循环检查状态并持续占用 CPU）或无限期同步调用来等待：

```kotlin
sealed interface RemoteState {
    data object Disconnected : RemoteState
    data object Connecting : RemoteState
    data class Ready(
        val service: IWorkerService,
        val binder: IBinder,
    ) : RemoteState
    data class Failed(val cause: Throwable?) : RemoteState
}

class WorkerConnection :
    ServiceConnection,
    IBinder.DeathRecipient {

    private val _state =
        MutableStateFlow<RemoteState>(RemoteState.Disconnected)
    val state: StateFlow<RemoteState> = _state.asStateFlow()

    fun markConnecting() {
        _state.value = RemoteState.Connecting
    }

    override fun onServiceConnected(
        name: ComponentName,
        binder: IBinder,
    ) {
        try {
            binder.linkToDeath(this, 0)
            _state.value = RemoteState.Ready(
                service = IWorkerService.Stub.asInterface(binder),
                binder = binder,
            )
        } catch (error: RemoteException) {
            _state.value = RemoteState.Disconnected
        }
    }

    override fun onServiceDisconnected(name: ComponentName) {
        _state.value = RemoteState.Disconnected
    }

    override fun onBindingDied(name: ComponentName) {
        _state.value = RemoteState.Disconnected
    }

    override fun onNullBinding(name: ComponentName) {
        _state.value = RemoteState.Failed(null)
    }

    override fun binderDied() {
        _state.value = RemoteState.Disconnected
    }

    suspend fun awaitReady(timeoutMillis: Long): IWorkerService =
        withTimeout(timeoutMillis) {
            state
                .filterIsInstance<RemoteState.Ready>()
                .first()
                .service
        }
}
```

这段代码只展示连接骨架。调用方仍需成对执行 bind/unbind。`onServiceDisconnected()` 表示连接意外丢失，原绑定仍然有效，服务重新运行后可能再次收到 `onServiceConnected()`；`onBindingDied()` 表示这条绑定不会自动恢复，必须先解绑再按业务需要重绑；`onNullBinding()` 也要解绑以释放跟踪资源。不用仍存活的旧 Binder 时，还要解除 `linkToDeath()` 注册。`binderDied()` 可能在 Binder 线程执行，并与新连接回调并发，生产实现应给每次连接分配代次，忽略旧代次回调，避免旧死亡通知覆盖新的 `Ready` 状态。状态更新之外的重工作应切换到受控协程或执行器。

远程事务可能包含磁盘、网络或重计算。AIDL（Android Interface Definition Language）用于声明跨进程接口；客户端应把同步 AIDL 调用放到允许阻塞的调度器，并给业务请求单独设置超时：

```kotlin
suspend fun transcode(
    connection: WorkerConnection,
    request: TranscodeRequest,
): TranscodeResult = withTimeout(3_000) {
    withContext(Dispatchers.IO) {
        connection.awaitReady(timeoutMillis = 1_000)
            .transcode(request)
    }
}
```

内层超时约束连接等待，外层超时为调用方协程设置业务 deadline。但同步 Binder 一旦进入阻塞，`withTimeout` 不能强制中断正在执行的事务，因此这段代码不能提供严格的墙钟时间上限，也就是从调用开始计算的实际耗时上限。需要硬超时的耗时协议，应改成异步请求加回调，并提供请求 ID、显式 `cancel(requestId)` 和服务端 deadline；服务端还要让重复请求可安全重试。

如果首屏允许降级，超时后应返回本地占位、稍后重试或跳过非核心能力。不要在主线程用同步 Binder、文件锁或数据库锁把远程冷启动串到首帧之前。

## 6. 跨进程状态要有唯一所有者

`Context.MODE_MULTI_PROCESS` 从 API 23 起已废弃。Android 17 的 `Context` 文档明确说明，它不能可靠协调跨进程 `SharedPreferences`；不同进程各自缓存数据，并发修改也没有可依赖的冲突合并规则。

跨进程状态应明确唯一写入者和一致性协议：

- 小型查询或受控写入可以由一个 Provider 统一管理，让其他进程通过 IPC 访问唯一的数据实现；
- 高频、强类型调用可以使用 AIDL，并在服务端串行化关键状态；
- 大对象使用文件、数据库、共享内存或文件描述符传递，Binder 只传请求 ID、状态等控制信息，避免占满事务缓冲区；
- 配置变更携带 `version` 或 `generation`（状态代次），客户端重连时重新拉取快照；
- 一次性事件携带请求 ID，避免进程死亡后的重复提交产生副作用。

数据库能够被多个进程打开，不等于业务事务已经具备一致性保证。需要核对所用数据库库的多进程能力、WAL（Write-Ahead Logging，预写日志）与锁行为、数据失效通知和迁移时序。数据库升级只能有一个受控入口；其他进程在 schema（数据库结构）准备完成前，应等待带超时的状态，不能并发发起迁移。

## 7. 按“会死亡”设计，不做进程保活技巧

远程进程可能因内存压力、组件生命周期结束、崩溃或系统策略而消失。应用不能依赖 `Application.onTerminate()` 做生产环境清理；官方 API 文档明确说明，量产设备结束进程时不会调用这个方法，也不会执行其他应用清理代码。

绑定关系、正在运行的前台服务和用户可感知组件会影响系统对进程重要性的判断，但不能用来任意延长进程寿命。前台服务只适合用户能够感知的持续任务，并要声明正确的服务类型、权限和通知；从后台启动时还要满足对应版本的豁免条件。空 Service、循环广播、主辅进程互相启动和没有业务意义的前台服务会增加功耗与内存，也可能触发系统限制。

更可靠的恢复路径包含：

- 客户端监听 Binder 死亡，清掉旧代理并按当前页面需求决定是否重连；
- 服务端把必要状态持久化，让请求具备幂等键或可恢复检查点（中断后可继续的位置）；
- 客户端保存可序列化、可重建的请求描述，不保存只能由旧进程内存解释的对象引用；
- 连接失败、初始化失败和业务失败使用不同错误码，分别制定逐步延长重试间隔的退避、降级和用户提示；
- 不再有页面或任务需要服务时及时解绑，让系统回收空闲进程。

如果一次冷启动很贵，应优先减少远程进程初始化量、缩短协议握手和缓存可复用产物。是否在首帧后预热，应由命中率和资源数据决定。

## 8. Android 17 上怎样观测

没有 Activity 的远程服务进程不会绘制应用界面，因此没有有意义的 TTID/TTFD。主进程继续观察 TTID、TTFD 和首帧前同步等待；远程进程应定义自己的 `binder_ready`、`provider_ready` 或首个业务结果时间，并写清每个时点代表的可用能力。

Android 15（API 35）加入 `ApplicationStartInfo`，可以读取进程名、启动原因和启动时间戳；Android 16（API 36）又加入 `getStartComponent()`，用于区分 Activity、Service、Broadcast 和 ContentProvider。`getReason()` 给出 launcher、Job、Push 等更细的触发原因，不能单独替代组件类型。Android 17 上可通过 `ActivityManager.getHistoricalProcessStartReasons()` 读取按时间倒序保存的近期记录，其中可能包含仍在启动的未完整记录。它适合解释“为什么创建进程”，应用自己的 trace 和埋点仍要解释初始化阶段耗时。

每次远程进程启动建议至少记录：

| 维度 | 字段 | 诊断目的 |
| --- | --- | --- |
| 身份 | processName、pid（进程 ID）、versionName、启动代次 | 区分多次重启与版本差异 |
| 原因 | `ApplicationStartInfo.reason`、start component、业务入口 | 找出意外 Provider、广播或后台任务拉起 |
| 阶段 | Application 入口/出口、Provider、自定义 SDK、binder ready | 找出远程冷启动的长任务 |
| 主进程影响 | 首帧前 IPC 次数、同步等待、超时与降级 | 判断是否把远程成本传回主线程 |
| 资源 | PSS、RSS、Java/native heap、线程、FD（文件描述符） | 衡量拆分和预热的常驻代价 |
| 稳定性 | `binderDied`、重绑、崩溃、请求重放、失败率 | 验证进程死亡后的恢复质量 |

PSS 会按共享进程数分摊共享内存页，适合估算多个进程合计对系统内存的压力。RSS（Resident Set Size，常驻内存大小）包含该进程映射的全部共享页，适合观察单进程分配趋势；直接相加多个进程的 RSS 会重复计算共享页。报告“多进程节省内存”时，需要说明使用了哪一种统计口径。

本地排查可以先用下面的命令确认进程、内存和长期存活情况：

```bash
adb shell dumpsys activity processes
adb shell dumpsys meminfo com.example.app
adb shell dumpsys procstats --hours 3
```

第一条查看当前进程与组件状态，第二条分项显示应用内存，第三条读取 `procstats`（系统长期记录的进程状态与内存统计）。不同 Android 版本与设备厂商的 `dumpsys` 文本格式可能变化，自动化采集更适合使用稳定 API、Perfetto 数据源或只解析明确支持的系统版本。

Perfetto 是系统级时间线分析工具。分析时要把主进程和远程进程放在同一时间轴上，关注进程创建、`bindApplication`、Provider 初始化、自定义 trace、Binder 阻塞、I/O 和 CPU 竞争。一次优化至少回答三个问题：主进程首帧有没有改善，远程能力可用时间有没有变慢，合计资源与失败率是否可以接受。

## 检查清单

- [ ] 每个远程组件的 `android:process` 都有明确理由。
- [ ] 普通远程进程与 isolated process（隔离 UID、无自身权限）的权限假设已分别验证。
- [ ] Provider 的进程归属和自动初始化项已检查。
- [ ] `Application.getProcessName()` 分支覆盖所有已声明进程。
- [ ] 每个进程只创建本进程需要的 SDK、线程池和 native 状态。
- [ ] 首帧前没有无上限的同步 Binder、Provider 或锁等待。
- [ ] Binder 客户端处理超时、死亡、重绑、取消和请求幂等。
- [ ] 跨进程状态有唯一所有者，没有依赖 `MODE_MULTI_PROCESS`。
- [ ] 远程进程可被回收，恢复路径不依赖 `onTerminate()`。
- [ ] 预热实验同时比较命中率、TTID/TTFD、remote ready（远程能力可用时点）、PSS 和失败率。
- [ ] PSS/RSS 的统计口径和聚合方法已在报告中说明。
- [ ] `ApplicationStartInfo`、应用 trace 与线上埋点能解释进程启动原因和阶段。

## 小结

多进程优化可以按这个顺序推进：确认隔离目标，明确组件归属，压缩每个进程的初始化集，再把远程能力设计成可超时、可取消、可重连的异步协议。Android 17 的源码时序给出了一条明确边界：属于该进程的 Provider 先于 `Application.onCreate()` 执行，因此进程名分支和 Provider 治理都要检查。验收时同时观察主进程首帧、远程能力 ready、全应用内存与进程死亡恢复，才能判断这次拆分是否值得。

## 参考资料

- [Android 17 `ActivityThread.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/app/ActivityThread.java)：`handleBindApplication()`、`installContentProviders()` 与 `callApplicationOnCreate()` 的调用顺序。
- [Android 17 `ZygoteProcess.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/os/ZygoteProcess.java)：`startViaZygote()` 与 Zygote 请求路径。
- [Android 17 `Context.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/content/Context.java)：`MODE_MULTI_PROCESS` 的废弃说明与跨进程限制。
- [Processes and threads overview](https://developer.android.com/guide/components/processes-and-threads)：组件进程、Binder 线程与 Provider 调用规则。
- [`Application` API reference](https://developer.android.com/reference/android/app/Application)：`getProcessName()` 与 `onCreate()` 生命周期边界。
- [Bound services overview](https://developer.android.com/develop/background-work/services/bound-services)：绑定生命周期与跨进程服务调用。
- [`ServiceConnection` API reference](https://developer.android.com/reference/android/content/ServiceConnection)：断连、binding 失效和重新绑定要求。
- [`IBinder` API reference](https://developer.android.com/reference/android/os/IBinder)：同步事务、`linkToDeath()` 与死亡通知。
- [`ApplicationStartInfo` API reference](https://developer.android.com/reference/android/app/ApplicationStartInfo)：启动原因、进程名、组件和时间戳。
- [Memory management overview](https://developer.android.com/topic/performance/memory-management)：PSS、RSS 与 Android 内存统计口径。
- [Handle WebView termination](https://developer.android.com/develop/ui/views/layout/webapps/handle-termination)：renderer process 退出与宿主恢复边界。
- [App Startup](https://developer.android.com/topic/libraries/app-startup)：initializer 依赖、自动初始化和手动初始化。
- [App startup time](https://developer.android.com/topic/performance/vitals/launch-time)：TTID、TTFD 与启动测量边界。
