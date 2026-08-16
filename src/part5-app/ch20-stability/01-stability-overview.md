---
title: "应用稳定性全景"
chapter: "20.1"
section: "20.1"
applicable_versions: "Android 10 (API 29) - Android 17 (API 37)"
last_verified: "2026-08-14"
last_verified_against: "AOSP android-17.0.0_r1 and android17-6.18-2026-06_r6; Android Developers ANR, ApplicationExitInfo, ProfilingManager/ProfilingTrigger, and Android vitals docs current on 2026-08-14"
confidence: medium-high
sources:
  - type: official
    path: "https://support.google.com/googleplay/android-developer/answer/9844476"
    note: "保留自旧版元数据；当前 Android vitals 帮助页编号为 9844486。"
  - type: official
    path: "https://support.google.com/googleplay/android-developer/answer/9844486"
  - type: official
    path: "https://developer.android.com/reference/android/app/ApplicationExitInfo"
  - type: official
    path: "https://developer.android.com/topic/performance/anrs/diagnose-and-fix-anrs"
  - type: official
    path: "https://developer.android.com/reference/android/os/ProfilingManager"
  - type: official
    path: "https://developer.android.com/reference/android/os/ProfilingTrigger"
  - type: aosp
    path: "frameworks/base/core/java/android/app/ActivityManager.java"
  - type: clippings-structure-ref
    path: "Clippings/Android 应用稳定性剖析与优化 - 开篇词：欢迎加入 Android 优化之旅，你将走进稳定性优化的世界！.md"
tags: [stability, crash, anr, oom, app-quality]
related_chapters: ["20.2", "20.4", "20.5", "15.3", "9.1"]
status: "finalized"
task6_state: reviewed
task9_state: "reviewed"
task2b_state: "fixed"
pipeline_stage: "ready-to-publish"
---

# 应用稳定性全景

稳定性排查先要区分用户现象和进程结局。用户看到的“闪退、卡死、白屏、重新启动”，可能来自应用崩溃（Crash）、系统判定应用无响应（ANR，Application Not Responding）、内存不足（OOM，Out of Memory）或低内存杀进程，也可能只是 WebView 网页渲染进程退出。把故障事件、进程是否退出和证据来源分开后，才能选择合适的指标与修复方法。

平台源码按 Android 17 / API 37 / `android-17.0.0_r1` 核对；涉及内核内存回收的内容按 `android17-6.18-2026-06_r6` 核对。

## 先区分“故障事件”和“进程退出”

Crash、ANR、OOM 描述的不是同一层概念：

| 类别 | 触发条件 | 进程是否必然退出 | 首选证据 |
|---|---|---:|---|
| Java Crash | 未捕获的 `Throwable` 到达线程顶层 | 是，默认处理链会终止应用进程 | Java 堆栈、异常链、日志、版本映射 |
| Native Crash | 致命信号，如 `SIGSEGV`、`SIGABRT`、`SIGBUS` | 是 | tombstone（系统生成的 Native 崩溃报告）、原始符号、Build ID（用于匹配二进制文件与符号版本的构建标识） |
| ANR | 系统监测的输入分发或组件执行期限被突破 | 否；进程可能恢复、被用户关闭或被系统处理 | ANR trace（线程堆栈等诊断记录）、原因文本、Perfetto、系统日志 |
| Java 堆 OOM | ART（Android Runtime，Android 运行时）无法满足对象分配 | 不一定；未捕获时通常转成 Java Crash | OOM 异常消息、堆水位、堆转储、分配轨迹 |
| Native 分配失败 | `malloc`、映射或线程创建等资源申请失败 | 不一定；取决于调用方是否正确处理 | tombstone、`errno`（系统错误码）、内存映射表、线程与映射数量 |
| LMKD 终止 | 系统内存压力下，低内存终止守护进程 `lmkd` 选择目标进程 | 是，且应用没有可靠的临终回调 | `ApplicationExitInfo`、Android vitals、系统内存状态 |
| WebView 渲染进程退出 | 渲染进程崩溃或被系统回收 | 宿主进程可以存活 | `onRenderProcessGone()`、`RenderProcessGoneDetail` |

`OutOfMemoryError` 表示进程内分配失败，`REASON_LOW_MEMORY` 是系统在进程退出历史中记录的低内存终止原因，两者不能互相替代。ANR 也不能简化成“主线程卡住五秒”：`BroadcastReceiver` 可以运行在自定义 `Handler` 对应的线程，系统还会为 Service、Provider 等组件使用不同的期限。

## Crash 的两条终止链

### Java Crash：未捕获异常到默认处理器

当 `Throwable` 逃出线程入口，Java 层会进入 [`Thread.dispatchUncaughtException()`](https://android.googlesource.com/platform/libcore/+/refs/tags/android-17.0.0_r1/ojluni/src/main/java/java/lang/Thread.java)。Android 进程初始化时，[`RuntimeInit.commonInit()`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/com/android/internal/os/RuntimeInit.java) 安装两个处理器：

1. `LoggingHandler` 被注册为 pre-handler（前置未捕获异常处理器），负责写入致命异常日志。应用可以替换默认处理器，但不能通过公开的 `Thread` API 替换这个前置处理器。
2. `KillApplicationHandler` 被注册为 default handler（默认未捕获异常处理器）。它向 ActivityManager 报告 `ParcelableCrashInfo`，并在 `finally` 代码块中依次调用 `Process.killProcess(Process.myPid())` 和 `System.exit(10)`。

应用或第三方崩溃采集 SDK（Software Development Kit，软件开发工具包）调用 `Thread.setDefaultUncaughtExceptionHandler()` 后，会替换 `KillApplicationHandler` 的默认位置。自定义处理器应保存并调用安装前的处理器；若只写文件或发网络请求后直接返回，就会改变系统默认语义，也无法确认进程还能安全运行。

致命路径还要接受三个限制：

- 任意线程都可能触发，主线程、线程池和第三方 SDK 线程都要覆盖。
- 进程可能处于锁状态异常、内存紧张或 Binder（Android 进程间通信机制）不可用状态，上传只能尽力而为。
- 应在崩溃前持续写入少量 breadcrumb（用户操作和状态变化线索）；崩溃时只保存固定大小、可校验的数据，重启后再补传。

Java 堆栈需要与当前版本的 R8 混淆映射文件（mapping）、动态特性模块和热修复版本对应。堆栈可读不代表根因就在栈顶：异步切换、反射、协程恢复和异常包装都可能丢失上游调用信息。[20.2 Java Crash 治理](02-java-crash-governance.md) 会继续讨论异常架构、反混淆和聚类。

### Native Crash：信号处理器、`crash_dump` 与 `tombstoned`

Android 17 的 Native Crash 不能概括为“debuggerd 守护进程捕获信号”。更准确的链路是：

1. Android C 库 bionic 与 debuggerd 诊断组件在进程内安装致命信号处理器，处理 `SIGSEGV`、`SIGABRT`、`SIGBUS` 等信号。
2. [`debuggerd_signal_handler`](https://android.googlesource.com/platform/system/core/+/refs/tags/android-17.0.0_r1/debuggerd/handler/debuggerd_handler.cpp) 保存 `siginfo_t` 与 `ucontext_t`，派生子进程并执行相应位数的 `crash_dump32` 或 `crash_dump64`。
3. [`crash_dump`](https://android.googlesource.com/platform/system/core/+/refs/tags/android-17.0.0_r1/debuggerd/crash_dump.cpp) 通过 `ptrace`（进程跟踪接口）暂停并读取目标线程，连接 `tombstoned` 取得输出文件描述符，生成文本和 Protocol Buffers（protobuf，结构化二进制格式）形式的 tombstone。
4. [`tombstoned`](https://android.googlesource.com/platform/system/core/+/refs/tags/android-17.0.0_r1/debuggerd/tombstoned/tombstoned.cpp) 管理 tombstone 的存储与轮转；栈回溯使用的是 Android 的 `libunwindstack`，不应写成泛指的 `libunwind`。

tombstone 的诊断价值来自信号、`si_code`、故障地址、寄存器、线程栈、内存映射、Build ID 和内存标签等信息。线上符号化必须按 ABI（Application Binary Interface，二进制接口约定）、Build ID 和发布版本取回未剥离符号；只按 `.so` 文件名匹配，很容易把地址解析到错误源码。系统信号与 debuggerd 链路见 [20.3 Native Crash 治理](03-native-crash-governance.md)，更深入的栈回溯（unwind）与符号解析见 [20.16 Native 栈回溯与符号化](16-native-stack-unwinding-symbolication.md)。

## ANR：系统的超时判定

ANR 表示系统认定应用没有在规定时间内完成某类交互或组件工作。它是一段诊断与策略流程，不是某个异常类，也不保证进程立刻退出。

常见入口及其边界如下：

| 入口 | Android 17 下应怎样理解 |
|---|---|
| Input dispatching timeout（输入分发超时） | AOSP 与 Pixel 的默认期限是 5 秒，设备厂商可以调整。输入事件没有得到可继续分发的响应时，由 InputDispatcher 发起判定。 |
| BroadcastReceiver timeout（广播接收超时） | Android 13 及更低版本中，带 `FLAG_RECEIVER_FOREGROUND` 的广播默认 10 秒，其他广播默认 60 秒；Android 14 起，进程因调度得不到足够 CPU 时间时可分别放宽到 10～20 秒和 60～120 秒。 |
| Service execution timeout（Service 执行超时） | AOSP 与 Pixel 的默认期限是前台 Service 20 秒、后台 Service 200 秒；设备配置可以调整，各类前台服务还有独立的执行期限。 |
| ContentProvider 响应超时 | 调用方可通过 `ContentProviderClient.setDetectNotResponding()` 设置检测期限；Provider 启动、发布和访问还涉及 `system_server` 内的其他等待路径。 |

“主线程栈看起来空闲”不能直接排除 ANR。以广播为例，广播接收器可以通过自定义 `Handler` 运行在非主线程，也可以调用 `goAsync()` 转交异步工作；同步接收器以 `onReceive()` 返回为完成点，异步接收器以 `PendingResult.finish()` 为完成点。应检查实际执行线程、Binder 对端和 CPU 调度情况。输入 ANR 也可能来自无焦点窗口、窗口尚未就绪、主线程等待 Binder 或锁。

进入 [`AnrHelper`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/am/AnrHelper.java) 后，Android 核心系统服务进程 `system_server` 会协调堆栈与进程状态采集，再依据可见性、后台策略和用户操作处理事件。前台可能出现“应用无响应”对话框；后台静默 ANR 可能只留下报告。用户选择等待后，进程可以继续运行，因此不能把每次 ANR 都计为一次退出。

诊断 ANR 时至少对齐以下信息：

- ANR 原因文本与发生时间；
- 主线程及相关工作线程的完整栈；
- 持锁线程、Binder 对端和进程 CPU 状态；
- 当时的窗口、组件与进程重要性；
- 同一时间段的 Perfetto（Android 系统级性能轨迹工具）调度、Binder、I/O 和 GC（垃圾回收）轨迹。

官方的 [ANR 诊断指南](https://developer.android.com/topic/performance/anrs/diagnose-and-fix-anrs) 给出了不同入口的判定方法；[20.4 ANR 治理](04-anr-governance.md)会按输入、广播、Service 和 Provider 分析证据。

## OOM 与低内存杀进程：四条资源路径

### Java 堆分配失败

ART 对象分配通常先走分配器的快速路径；空间不足时会触发与分配相关的 GC、尝试扩展堆，并在仍无法满足请求时抛出 `OutOfMemoryError`。异常消息可能指出 Java 堆空间不足、线程创建失败或其他分配场景，不能只凭异常类型判定为“内存泄漏”。

`Runtime.maxMemory()` 与 `ActivityManager.getMemoryClass()`、`getLargeMemoryClass()` 的值取决于设备和运行时配置。`android:largeHeap="true"` 只请求较大的应用堆类别，没有固定的 512 MB 保证，也不会消除 Native 内存、图形内存或系统内存压力。它通常只是推迟故障并增加 GC 成本，应先修正对象生命周期和峰值内存设计。

在局部操作里捕获 `OutOfMemoryError` 只适用于准备充分的降级路径，例如图片解码失败后释放临时资源并返回占位图。未捕获 OOM 到达线程顶层时，进程可能已经缺少再次分配、加锁或启动线程所需的资源，不应在未捕获异常处理器中创建大对象、生成完整堆转储或同步上传。

### Native 堆、映射与地址空间

Native `malloc` 分配失败通常返回 `nullptr` 并设置错误码；调用方若未检查，后续空指针访问会表现为 Native crash。连续映射、地址空间碎片、地址空间布局限制、驱动映射和 Native 泄漏也可能使申请失败。此时只看 Java 堆曲线会得出错误结论。

### 线程和文件描述符

创建线程需要线程控制结构、栈映射和内核任务资源。`pthread_create` 返回 `EAGAIN`（当前资源不足）或其他错误后，Java 层可能抛出带有 `pthread_create` 信息的 `OutOfMemoryError`。这种故障应同时检查线程数量、线程来源、栈大小和进程资源限制。

FD（File Descriptor，文件描述符）耗尽通常表现为 `EMFILE`（进程打开的文件描述符达到上限），随后文件或网络套接字创建失败。它与虚拟地址空间耗尽是两类故障。FD 泄漏还会引发数据库、网络、资源加载或 Binder 相关异常，监控时应单列 FD 数量与类别。[20.12 FD 资源监控](12-fd-resource-monitoring.md)会展开这类资源故障。

### LMKD 与内核 OOM

内存压力下，Android 的 [`lmkd`](https://android.googlesource.com/platform/system/memory/lmkd/+/refs/tags/android-17.0.0_r1/lmkd.cpp) 会读取 PSI（Pressure Stall Information，资源压力导致任务停顿的内核统计）等信号，结合 `oom_score_adj`、进程重要性和预计回收量选择目标进程。被选中的应用没有可靠的 Java 临终回调，进程可能直接以 `SIGKILL` 结束。这类结果简称 LMK（low-memory kill，低内存终止）。

内核 OOM killer 是系统无法释放足够内存时的更底层终止机制，Android 17 对应实现见 [`android17-6.18-2026-06_r6/mm/oom_kill.c`](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/mm/oom_kill.c)。排查线上 LMK 时，应优先使用 `ApplicationExitInfo`、Android vitals 和设备内存分层数据；每次应用低内存退出不一定都有内核 OOM 日志。

[20.5 OOM 治理](05-oom-governance.md)会继续区分 Java heap、Native heap、线程、映射、图形内存与 LMK。

## 用 `ApplicationExitInfo` 读取“上一次进程发生了什么”

API 30 引入的 [`ApplicationExitInfo`](https://developer.android.com/reference/android/app/ApplicationExitInfo) 是进程退出后留下的系统记录，不是实时崩溃回调。常见原因码（reason）的解释如下：

| reason | 含义与使用边界 |
|---|---|
| `REASON_CRASH` | 未处理的 Java 异常导致进程退出；结合应用侧异常堆栈确认。 |
| `REASON_CRASH_NATIVE` | Native crash；API 31 起 `getTraceInputStream()` 可能返回 tombstone protobuf。 |
| `REASON_ANR` | 进程因 ANR 被记录为退出；trace 可能存在，也可能因轮转等原因返回 `null`。 |
| `REASON_LOW_MEMORY` | 系统低内存终止进程；设备不支持精确上报时，可能只看到 `REASON_SIGNALED` 与 `SIGKILL`。可用 `ActivityManager.isLowMemoryKillReportSupported()` 检查支持情况。 |
| `REASON_SIGNALED` | 进程因信号退出；必须结合 `getStatus()` 与上下文判断，不能一律归为 Native crash。 |
| `REASON_INITIALIZATION_FAILURE` | 进程在初始化或 attach 阶段失败。 |
| `REASON_DEPENDENCY_DIED` | 依赖进程死亡导致本进程退出。 |
| `REASON_EXCESSIVE_RESOURCE_USAGE` | 系统因资源使用过量终止进程。 |
| `REASON_USER_REQUESTED` | 用户强行停止应用或将其移出最近任务。Android 13 及更低版本还可能用它记录应用更新或组件状态变化。 |
| `REASON_PACKAGE_STATE_CHANGE` / `REASON_PACKAGE_UPDATED` | API 34 起分别记录组件状态变化和应用更新，避免再与用户操作混为一类。 |

下面的代码只演示重启后枚举退出记录；生产实现还需要持久化已消费的时间戳或唯一键，并在后台读取大 trace。

```kotlin
@RequiresApi(30)
fun readRecentExits(context: Context): List<ApplicationExitInfo> {
    val am = context.getSystemService(ActivityManager::class.java)
    return am.getHistoricalProcessExitReasons(
        /* packageName = */ null,
        /* pid = */ 0,
        /* maxNum = */ 20,
    )
}
```

返回列表应按 `processName`、`timestamp`、`reason`、`status` 和 `importance` 处理。`getPss()` 返回按比例分摊共享内存后的驻留量，`getRss()` 返回全部驻留物理内存；两者都是系统最近一次采样值，可能为 0，也不是死亡瞬间的精确快照。`getTraceInputStream()` 的数据保存在全局环形缓冲区中，可能被其他应用的新记录覆盖而返回 `null`。如果进程发生 ANR 后恢复，随后因别的原因死亡，该退出记录仍可能附带之前的 ANR trace，所以原因码与 trace 内容要分别判断。

从事件到证据，可以用下面这条路径做快速分流。

```text
用户现象
  ├─ 应用进程退出
  │    ├─ 未捕获 Throwable ── Java stack ── Java Crash
  │    ├─ 致命 signal ────── tombstone ─── Native Crash
  │    └─ 无临终回调 ─────── ExitInfo ──── LMKD / 系统终止 / 用户操作
  ├─ 应用进程仍在
  │    └─ 系统超时报告 ───── ANR trace ─── Input / Broadcast / Service / Provider
  └─ 宿主仍在但页面消失
       └─ onRenderProcessGone ──────────── WebView renderer 退出
```

这条分流只负责选择证据，不直接判定根因。例如 `SIGABRT` 可能来自显式 `abort()`、内存分配器自检或运行时主动终止；`REASON_LOW_MEMORY` 也不能单独证明应用存在泄漏。

## Google Play Android vitals 与内部指标

### Play 的口径和阈值

截至 2026-08-14，Google Play 将用户感知崩溃率和用户感知 ANR 率列为稳定性 core vitals（影响应用在 Play 中可见性的核心指标）：

| 指标 | 口径 | 全机型不良行为阈值 | 单手机型号阈值 |
|---|---|---:|---:|
| 用户感知崩溃率（User-perceived crash rate） | 每日用户中，至少一次在活跃使用期间遇到崩溃的用户占比 | 1.09% | 8% |
| 用户感知 ANR 率（User-perceived ANR rate） | 每日活跃用户中，至少一次遇到用户感知 ANR 的用户占比 | 0.47% | 8% |

对用户感知崩溃，官方给出的活跃使用示例包括显示 Activity 或运行前台服务（foreground service）。当前用户感知 ANR 率只统计 input dispatching timed out（输入分发超时）类型。daily active user（DAU，每日活跃用户）按“设备上的一个用户在一天内使用过应用”计数；同一用户、同一设备当天打开多次仍计一次。Google Play 通常使用最近 28 天数据评估质量，出现突增时也可能提前采取措施。达到或超过阈值可能降低应用在 Play 的可见性，也可能在商店详情页显示警告；官方没有把它表述为固定的审核拒绝线。当前阈值以 [Play Console Android vitals 帮助页](https://support.google.com/googleplay/android-developer/answer/9844486) 为准。

Android vitals 与 SDK 看板出现不同结果很常见。这里的 session 指按团队规则划定的一次连续使用，会话中的 event 指一次具体故障事件：

- Android vitals 来自 Android 系统，能够覆盖 SDK 初始化前的部分故障；
- 只纳入符合 Play 数据条件的认证设备、Play 安装和同意共享数据的用户；
- 受隐私最小样本与展示延迟影响；
- Play 以每日用户或每日活跃用户为主要分母，很多 SDK 使用会话数或事件数作为分母。

不应期待两个系统使用相同数据源或得到接近的数值。团队需要明确每张看板回答的问题，无须强行对齐数字。定义与数据条件见 [Android Vitals](https://developer.android.com/topic/performance/vitals) 和 [Crash 指标说明](https://developer.android.com/topic/performance/vitals/crash)。

### 团队内部指标必须写清分子与分母

内部没有适用于所有应用的“0.2% 红线”或“99.5% 行业基线”。业务使用时长、进程模型、会话定义和设备分布不同，直接复制一个百分比没有比较价值。建议至少维护以下指标：

| 指标 | 计算方式 | 适合回答的问题 |
|---|---|---|
| 受影响用户率 | 发生目标事件的去重用户数 ÷ 同窗口活跃用户数 | 有多少用户受到影响 |
| 无崩溃用户率（Crash-free users） | 1 − Crash 受影响用户率 | 版本总体体验 |
| 无崩溃会话率（Crash-free sessions） | 无崩溃的会话数 ÷ 全部会话数 | 一次使用能否完成；前提是固定会话边界 |
| 事件率 | 事件次数 ÷ 会话数，可换算为每万次会话 | 高频重复故障是否恶化 |
| 启动致命故障率 | 启动阶段致命崩溃次数 ÷ 启动次数 | 用户是否无法进入核心页面 |
| ANR 受影响用户率 | 发生目标 ANR 的去重用户数 ÷ 活跃用户数 | ANR 的用户影响 |
| LMK 退出率 | `REASON_LOW_MEMORY` 等受支持记录 ÷ 可观测进程运行或活跃用户 | 内存压力是否导致进程丢失 |
| 新增故障簇影响 | 新版本新增问题簇的用户数、事件数和关键路径占比 | 是否由本次发布引入 |

每个指标都要附版本、渠道、机型或内存容量档位、ABI、时间窗口、分子、分母和最小样本量。样本很少时，单个百分比会剧烈波动；发版门禁应同时参考历史基线、表示统计不确定范围的置信区间，以及故障严重度。

## 采集方式怎么选

| 方式 | 覆盖重点 | 优势 | 主要缺口 |
|---|---|---|---|
| Google Play Android vitals | Crash、ANR、LMK 等系统质量信号 | 不依赖应用 SDK 存活；能看 Play 设备与型号分布 | 有数据条件、延迟和隐私阈值；自定义业务上下文少 |
| Crashlytics 等崩溃 SDK | Java/Native Crash、部分 ANR 与业务上下文 | 接入快，具备版本、用户影响与聚类能力 | 能力随 SDK、Android 版本和配置变化；致命路径上传仍受进程死亡限制 |
| 自建 Java 异常处理器 | 未捕获 Java `Throwable` | 可以保存业务 breadcrumb 与自有事件模型 | 只能尽力写入；替换默认处理器必须保留委托链 |
| 自建 Native 捕获 | Native 信号、采样与自有 minidump（只保存诊断所需信息的小型转储） | 可控制上下文和符号体系 | 只能使用异步信号安全（signal-safe）操作、处理器可能冲突，且系统迁移和兼容成本高 |
| `ApplicationExitInfo` | API 30+ 的历史退出原因与部分 trace | 能补上 LMK、ANR、信号退出等进程外证据 | 只能在后续进程读取；记录和 trace 可能缺失 |
| `ProfilingManager` | API 35+ 的按请求采集；API 36+ 的系统事件触发采集 | 系统管理速率、存储与结果交付 | 请求与触发都不保证产生结果；必须做版本与能力检测 |

Android 17 / API 37 增加 `ProfilingTrigger.TRIGGER_TYPE_OOM`：发生 Java `OutOfMemoryError` 时，系统可以返回 Java 堆转储。应用需用 `addProfilingTriggers()` 注册触发器，并用 `registerForAllProfilingResults()` 注册结果监听器。若应用安装了自定义 `Thread.UncaughtExceptionHandler`，它必须继续调用默认处理器，否则该 OOM 触发器无法工作。应用设置的触发间隔和系统限流会同时生效，结果不保证交付。API 演进与接入方式见 [19.13 ProfilingManager](../../part3-tools/ch19-apm/13-profiling-manager.md)。

是否建设自研采集，不应只看 DAU。更有用的判断标准是：现有平台缺少的证据是否反复导致问题无法定位，团队能否长期维护 Android 版本兼容、隐私治理、符号服务、去重和成本控制。

## 稳定性治理流程

稳定性治理可以按下面的顺序循环，每一步都有可检查的输入和产物。

```text
预防 → 发现 → 证据分类 → 诊断 → 修复 → 分阶段验证
  ↑                                      │
  └──────── 规则、测试与设计约束更新 ─────┘
```

这个流程把“证据分类”单独列出，是为了避免拿 Java Crash 的处理方式分析 ANR，或把所有 `SIGKILL` 都算作 LMK。

### 预防

- 用 Lint、Detekt 等静态检查工具、编译器检查和自定义规则约束空值、资源关闭、线程创建与主线程 I/O。
- 在调试或测试构建中启用 StrictMode（在运行时发现主线程磁盘或网络访问等问题）、sanitizer（运行时错误检查工具）、GWP-ASan、MTE 等能力，尽早暴露错误。GWP-ASan 与 MTE 用于发现部分 Native 内存安全问题，设备、构建和性能要求见 [20.10 MTE 与 GWP-ASan](10-mte-gwp-asan-native-memory-safety.md)。
- 为主线程任务、Binder 调用、启动阶段、缓存和并发数量制定时间或资源预算。
- 主动制造低内存、进程重建、网络失败、磁盘满、FD 或线程耗尽、服务端降级等条件，验证故障处理路径。这类测试称为故障注入。
- 对高风险变更使用可远程关闭的功能开关、限制高风险功能的安全模式、逐步扩大用户比例的灰度发布，以及能够恢复旧值的配置。

异常捕获不能替代这些设计。给 `WebView` 初始化包一层异常捕获无法处理网页渲染进程退出；把 `SharedPreferences.commit()` 包装起来也不会消除主线程同步 I/O 引起的 ANR。

### 发现与证据分类

- 看板按版本、渠道、机型、内存容量档位、ABI 和关键路径拆分。
- 告警同时考虑绝对影响用户数、相对历史基线、增长速度和严重度。
- Java/Native Crash 按去除易变地址和行号后的堆栈、异常或信号、Build ID 聚类；ANR 按原因文本、阻塞关系和主线程状态聚类。
- 对重启后的 `ApplicationExitInfo` 去重，避免每次启动重复上报同一条历史记录。
- 区分新出现的问题簇、已有问题再次恶化和单机型异常，避免总体均值掩盖局部故障。

### 诊断

诊断的目标是提出能够被证据验证或推翻的根因假设：

- Java Crash：异常因果链、异步来源、R8 混淆映射文件、breadcrumb 和输入数据；
- Native Crash：tombstone、Build ID、完整符号、故障地址、寄存器和相关内存工具报告；
- ANR：原因文本、全线程栈、锁与 Binder 关系、CPU 调度、I/O 和 GC；
- OOM/LMK：Java、Native 和图形内存，线程、FD、映射、进程重要性、设备内存容量与退出历史。

堆栈顶帧只能说明故障在哪里被观察到。若假设是“锁竞争导致输入 ANR”，还要找到持锁线程、持锁区间及其 I/O 或 Binder 依赖；若假设是“泄漏导致 LMK”，还要证明保留对象或 Native 分配随生命周期持续增长。

### 修复与验证

修复方案要同时写明根因、受影响的功能与用户、兼容范围、回归风险和撤回条件。发布时先覆盖内部用户与小比例外部用户，再逐步扩大；验证要比较同一口径下的修复组、历史基线和未修复版本。

以下情况不应只凭一天的百分比宣布修复完成：

- 样本量不足，置信区间仍覆盖历史水平；
- 原故障簇下降，但同根因迁移到了新堆栈；
- 总体指标改善，特定机型、Android 版本或内存容量档位恶化；
- Crash 数下降，但启动失败、ANR 或 LMK 上升。

验证通过后，把能自动检查的经验写入静态规则、测试、资源预算或发布检查项；无法自动检查的部分，要写清负责团队和复查时机。

## 发版门禁与组织责任

发版门禁指扩大用户覆盖前必须满足的一组检查条件，至少包含三类：

1. **绝对条件**：关键路径不可用、启动 Crash、数据损坏或安全问题达到约定严重度时停止扩大发布。
2. **相对条件**：新版本相对可比基线的 Crash、ANR、LMK 或新增问题簇影响显著恶化。
3. **证据条件**：样本达到最低要求，版本、渠道和设备分布可比，监控与符号文件已经就绪。

门禁阈值要来自本产品历史分布与风险承受能力，并定期回看，不能使用来源不明的行业数字。

组织上应明确：

- 每类事件和关键模块的负责团队；
- P0/P1 等团队自定义严重度级别、响应时限与升级路径；
- Native 符号、R8 混淆映射文件、系统性能轨迹和发布配置的保留周期；
- 灰度暂停、配置撤回和紧急发版的决策人；
- 修复验证的结束条件，不能只记录“代码已合入”。

## 后续章节阅读顺序

- [20.2 Java Crash 治理](02-java-crash-governance.md)：异常处理器、反混淆、异步异常与恢复边界。
- [20.3 Native Crash 治理](03-native-crash-governance.md)：tombstone、符号化和内存安全工具。
- [20.4 ANR 治理](04-anr-governance.md)：不同 ANR 入口的诊断记录与系统链路。
- [20.5 OOM 治理](05-oom-governance.md)：Java、Native、线程、映射与 LMK。
- [20.6 稳定性指标](06-stability-metrics.md)：分子、分母、聚类、基线与发版门禁。
- [20.9 WebView renderer OOM 恢复](09-webview-renderer-oom-recovery.md)：宿主进程与网页渲染进程的故障隔离。

## 源码与官方文档

- 平台：AOSP [`android-17.0.0_r1`](https://android.googlesource.com/platform/manifest/+/refs/tags/android-17.0.0_r1/)
- Java 致命异常处理：[`RuntimeInit.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/com/android/internal/os/RuntimeInit.java)
- ART 堆：[`heap-inl.h`](https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/runtime/gc/heap-inl.h) · [`heap.cc`](https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/runtime/gc/heap.cc)
- Native crash：[`debuggerd/handler`](https://android.googlesource.com/platform/system/core/+/refs/tags/android-17.0.0_r1/debuggerd/handler/) · [`crash_dump.cpp`](https://android.googlesource.com/platform/system/core/+/refs/tags/android-17.0.0_r1/debuggerd/crash_dump.cpp) · [`tombstoned`](https://android.googlesource.com/platform/system/core/+/refs/tags/android-17.0.0_r1/debuggerd/tombstoned/) · [`libunwindstack`](https://android.googlesource.com/platform/system/unwinding/+/refs/tags/android-17.0.0_r1/libunwindstack/)
- ANR：[`AnrHelper.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/am/AnrHelper.java) · [官方 ANR 诊断指南](https://developer.android.com/topic/performance/anrs/diagnose-and-fix-anrs)
- 退出历史：[`ApplicationExitInfo`](https://developer.android.com/reference/android/app/ApplicationExitInfo)
- 进程隔离：[`WebViewClient.onRenderProcessGone()`](https://developer.android.com/reference/android/webkit/WebViewClient#onRenderProcessGone(android.webkit.WebView,android.webkit.RenderProcessGoneDetail))
- 系统性能采集：[`ProfilingManager`](https://developer.android.com/reference/android/os/ProfilingManager) · [`ProfilingTrigger`](https://developer.android.com/reference/android/os/ProfilingTrigger)
- 内存回收：[`lmkd.cpp`](https://android.googlesource.com/platform/system/memory/lmkd/+/refs/tags/android-17.0.0_r1/lmkd.cpp) · 内核 [`android17-6.18-2026-06_r6/mm/oom_kill.c`](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/mm/oom_kill.c)
- 指标：[Android Vitals](https://developer.android.com/topic/performance/vitals) · [User-perceived crash rate](https://developer.android.com/topic/performance/vitals/crash) · [Play Console Android vitals 帮助](https://support.google.com/googleplay/android-developer/answer/9844486)
