---
title: "应用稳定性全景"
chapter: "20.1"
section: "20.1"
applicable_versions: "Android 10 (API 29) - Android 17 (API 37)"
last_verified: "2026-06-21"
last_verified_against: "AOSP android-16.0.0_r1, Android Developers ANR documentation, ApplicationExitInfo API reference"
confidence: medium
drafted_date: "2026-05-11"
polish_count: 1
sources:
  - type: official
    path: "https://support.google.com/googleplay/android-developer/answer/9844476"
  - type: official
    path: "https://developer.android.com/reference/android/app/ApplicationExitInfo"
  - type: official
    path: "https://developer.android.com/topic/performance/anrs/diagnose-and-fix-anrs"
  - type: aosp
    path: "frameworks/base/core/java/android/app/ActivityManager.java"
  - type: clippings-structure-ref
    path: "Clippings/Android 应用稳定性剖析与优化 - 开篇词：欢迎加入 Android 优化之旅，你将走进稳定性优化的世界！.md"
tags: [stability, crash, anr, oom, app-quality]
related_chapters: ["20.2", "20.4", "20.5", "15.3", "9.1"]
task9_reviewed_by: "openclaw-task9"
task9_reviewed_date: "2026-06-21"
last_task9_at: "2026-06-01T18:21:00+08:00"
last_task9_audit: "2026-06-21"
task9_review_notes: "2026-06-21 Task9 06:25 闲时抽检：auto-fixed。用 AOSP android-17.0.0_r1 复核 Java crash、ANR/Broadcast timeout、ART heap 分配源码锚点；修正 RuntimeInit 退出调用、Broadcast timeout 源码文件、Heap::AllocObjectWithAllocator 所在文件，回到 Task6 复审。"
task6_reviewed_date: "2026-05-14"
last_task9_review_log: "logs/deep-review/2026-06-21-06-audit.md"
status: "finalized"
reviewed_by: openclaw-task6
reviewed_date: "2026-06-21"
task6_state: reviewed
task6_result: pass-light-edit
task9_state: "reviewed"
task9_result: "auto-fixed"
task2b_state: "fixed"
task2b_result: fixed
pipeline_stage: "ready-to-publish"
last_task2b_at: "2026-06-01T08:50:00+08:00"
task2b_fixed_at: "2026-06-01T08:50:00+08:00"
last_task6_at: "2026-06-21T08:09:43+08:00"
last_task6_review_log: "logs/review/2026-06-21-08-review.md"
task6_l1_l2_fixes: 1
task6_l3_l4_issues: 0
task6_review_notes: "2026-06-21 Task6 复审（revisiting→reviewed）：L1 小修 1 处（applicable_versions 补 Android 17），锚点 5/5 覆盖，无 L3/L4 回炉项。Task9 auto-fixed 已完成，queue 无 pending，自动晋升 finalized。"
last_task9_autofix_at: "2026-06-21"
deepseek_cn_review_state: done
last_deepseek_cn_review_at: 2026-07-06
---

# 应用稳定性全景

稳定性排查最怕一开始就把现象归错类。用户看到的“闪退、卡死、白屏、重新启动”，可能来自应用进程崩溃、系统判定 ANR、低内存杀进程，也可能只是 WebView 渲染进程退出。只有把事件、进程结局和证据来源分开，后面的指标与修复才有意义。

平台源码锚点是 Android 17 / API 37 / `android-17.0.0_r1`；涉及内核内存回收时，以 `android17-6.18-2026-06_r6` 为 kernel 锚点。

## 先区分“故障事件”和“进程退出”

Crash、ANR、OOM 描述的不是同一层概念：

| 类别 | 触发条件 | 进程是否必然退出 | 首选证据 |
|---|---|---:|---|
| Java Crash | 未捕获的 `Throwable` 到达线程顶层 | 是，默认处理链会终止应用进程 | Java 堆栈、异常链、日志、版本映射 |
| Native Crash | 致命信号，如 `SIGSEGV`、`SIGABRT`、`SIGBUS` | 是 | tombstone、原始符号、Build ID |
| ANR | 系统监测的输入分发或组件执行期限被突破 | 否；进程可能恢复、被用户关闭或被系统处理 | ANR trace、原因文本、Perfetto、系统日志 |
| Java 堆 OOM | ART 无法满足对象分配 | 不一定；未捕获时通常转成 Java Crash | OOM message、堆水位、heap dump、分配轨迹 |
| Native 分配失败 | `malloc`、映射或线程创建等资源申请失败 | 不一定；取决于调用方是否正确处理 | tombstone、errno、maps、线程与映射数量 |
| LMKD kill | 系统内存压力下，`lmkd` 选择进程终止 | 是，且应用没有可靠的临终回调 | `ApplicationExitInfo`、Android Vitals、系统内存状态 |
| WebView renderer 退出 | 渲染进程崩溃或被系统回收 | 宿主进程可以存活 | `onRenderProcessGone()`、`RenderProcessGoneDetail` |

这张表给出一个重要边界：`OutOfMemoryError` 是进程内的分配失败，`REASON_LOW_MEMORY` 是系统终止进程的历史记录，两者不能互相替代。ANR 也不等于“主线程卡住五秒”，因为 BroadcastReceiver 可以运行在自定义 `Handler`，系统还会针对 Service、Provider 等组件维护不同的期限。

## Crash 的两条终止链

### Java Crash：未捕获异常到默认处理器

当 `Throwable` 逃出线程入口，Java 层会进入 [`Thread.dispatchUncaughtException()`](https://android.googlesource.com/platform/libcore/+/refs/tags/android-17.0.0_r1/ojluni/src/main/java/java/lang/Thread.java)。Android 进程初始化时，[`RuntimeInit.commonInit()`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/com/android/internal/os/RuntimeInit.java) 安装两个处理器：

1. `LoggingHandler` 被注册为 pre-handler，负责写入 fatal exception 日志。应用可以替换 default handler，但不能通过公开的 `Thread` API 替换这个 pre-handler。
2. `KillApplicationHandler` 被注册为 default handler。它向 ActivityManager 报告 `ParcelableCrashInfo`，并在 `finally` 中依次调用 `Process.killProcess(Process.myPid())` 和 `System.exit(10)`。

应用或崩溃 SDK 调用 `Thread.setDefaultUncaughtExceptionHandler()` 后，会替换 `KillApplicationHandler` 的默认位置。自定义 handler 应保存并调用安装前的 handler；若只写文件或发网络请求后直接返回，既改变了系统默认语义，也不能保证进程处于可继续运行的状态。

致命路径还要接受三个限制：

- 任意线程都可能触发，主线程、线程池和第三方 SDK 线程都要覆盖。
- 进程可能处于锁损坏、内存紧张或 Binder 不可用状态，上传只能尽力而为。
- 适合在崩溃前持续写入小型 breadcrumb；崩溃时只保存固定大小、可校验的数据，重启后再补传。

Java 堆栈需要与当前版本的 R8 mapping、动态特性模块和热修复版本对应。堆栈可读不代表根因就在栈顶：异步边界、反射、协程恢复和异常包装都可能丢失上游上下文。[20.2 Java Crash 治理](02-java-crash-governance.md)会继续讨论异常架构、反混淆和聚类。

### Native Crash：信号处理器、`crash_dump` 与 `tombstoned`

Android 17 的 Native crash 不能概括为“debuggerd 守护进程捕获信号”。更准确的链路是：

1. bionic/debuggerd 代码在进程内安装致命信号处理器，处理 `SIGSEGV`、`SIGABRT`、`SIGBUS` 等信号。
2. [`debuggerd_signal_handler`](https://android.googlesource.com/platform/system/core/+/refs/tags/android-17.0.0_r1/debuggerd/handler/debuggerd_handler.cpp) 保存 `siginfo_t` 与 `ucontext_t`，派生并执行相应位数的 `crash_dump32` 或 `crash_dump64`。
3. [`crash_dump`](https://android.googlesource.com/platform/system/core/+/refs/tags/android-17.0.0_r1/debuggerd/crash_dump.cpp) 通过 `ptrace` 暂停并读取目标线程，连接 `tombstoned` 取得输出文件描述符，生成文本与 protobuf 形式的 tombstone。
4. [`tombstoned`](https://android.googlesource.com/platform/system/core/+/refs/tags/android-17.0.0_r1/debuggerd/tombstoned/tombstoned.cpp) 管理 tombstone 的存储与轮转；栈回溯使用的是 Android 的 `libunwindstack`，不应写成泛指的 `libunwind`。

tombstone 的诊断价值来自信号、`si_code`、fault address、寄存器、线程栈、内存映射、Build ID 和内存标签等信息。线上符号化必须按 ABI、Build ID 和发布版本取回未剥离符号；只按 `.so` 文件名匹配，很容易把地址解析到错误源码。系统信号与 debuggerd 链路见 [20.3 Native Crash 治理](03-native-crash-governance.md)，更深入的 unwind 与符号解析见 [20.16 Native 栈回溯与符号化](16-native-stack-unwinding-symbolication.md)。

## ANR：系统的存活性判定

ANR 表示系统认定应用没有在规定时间内完成某类交互或组件工作。它是一段诊断与策略流程，不是某个异常类，也不保证进程立刻退出。

常见入口及其边界如下：

| 入口 | Android 17 下应怎样理解 |
|---|---|
| Input dispatching timeout | 常见默认期限是 5 秒，但系统可根据窗口和应用状态选择具体 timeout。输入事件没有得到可继续分发的响应时，由 InputDispatcher 发起判定。 |
| BroadcastReceiver timeout | Android 13 及更低版本通常是前台 10 秒、后台 60 秒；Android 14 起，CPU-starved 进程可放宽到前台 10～20 秒、后台 60～120 秒。 |
| Service execution timeout | AOSP 经典路径存在前台约 20 秒、后台约 200 秒的默认值，但设备配置和版本实现可以调整；各类 foreground service 还有独立的执行期限。 |
| ContentProvider 响应超时 | 调用方可通过 `ContentProviderClient.setDetectNotResponding()` 设置检测期限；Provider 启动、发布和访问还涉及 system_server 内的其他等待路径。 |

“主线程栈看起来空闲”不能直接排除 ANR。以广播为例，receiver 可以通过自定义 `Handler` 运行，也可以调用 `goAsync()` 延长异步工作；应检查实际执行线程、`PendingResult` 是否完成、Binder 对端和 CPU 调度情况。输入 ANR 也可能来自无焦点窗口、窗口尚未就绪、主线程等待 Binder 或锁，而不是一段明显的耗时代码。

进入 [`AnrHelper`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/am/AnrHelper.java) 后，system_server 会协调堆栈与进程状态采集，再依据可见性、后台策略和用户操作处理事件。前台可能出现“应用无响应”对话框；后台或 silent ANR 可能只留下报告。用户选择等待后，进程可以继续运行，因此不能把每次 ANR 都计为一次退出。

诊断 ANR 时至少对齐以下信息：

- ANR reason 与发生时间；
- 主线程及相关工作线程的完整栈；
- 锁 owner、Binder 对端和进程 CPU 状态；
- 当时的窗口、组件与进程重要性；
- 同一时间段的 Perfetto 调度、Binder、I/O 和 GC 轨迹。

官方的 [ANR 诊断指南](https://developer.android.com/topic/performance/anrs/diagnose-and-fix-anrs)给出了不同入口的判定方法；[20.4 ANR 治理](04-anr-governance.md)会按输入、广播、Service 和 Provider 分析证据。

## OOM 与低内存杀进程：四条资源路径

### Java 堆分配失败

ART 对象分配会经过 allocator 快路径；空间不足时触发与分配相关的 GC、尝试扩展堆，并在无法满足请求时抛出 `OutOfMemoryError`。OOM message 可能提示普通堆空间不足、无法创建线程或其他分配场景，不能只按异常类型归成“内存泄漏”。

`Runtime.maxMemory()` 与 `ActivityManager.getMemoryClass()`、`getLargeMemoryClass()` 的值取决于设备和运行时配置。`android:largeHeap="true"` 只请求较大的应用堆类别，没有固定的 512 MB 保证，也不会消除 Native 内存、图形内存或系统内存压力。它通常会延后故障并增加 GC 成本，应先修正对象生命周期和峰值设计。

在局部操作里捕获 `OutOfMemoryError` 只适用于准备充分的降级路径，例如图片解码失败后释放临时资源并返回占位图。未捕获 OOM 到达顶层时，进程可能已经缺少再次分配、加锁或启动线程所需的资源，不应在 handler 中创建大对象、dump 全堆或同步上传。

### Native heap、映射与地址空间

Native `malloc` 失败通常返回 `nullptr` 并设置错误状态；调用方若未检查，后续空指针访问会表现为 Native crash。连续映射、碎片、地址空间布局限制、驱动映射和 Native 泄漏也可能使申请失败。此时只看 Java heap 曲线会得出错误结论。

### 线程和文件描述符

创建线程需要线程控制结构、栈映射和内核任务资源。`pthread_create` 返回 `EAGAIN` 或其他失败后，Java 层可能抛出带有 `pthread_create` 信息的 `OutOfMemoryError`。这种故障应同时检查线程数量、线程来源、栈大小和进程资源限制。

文件描述符耗尽通常表现为 `EMFILE`、打开文件或 socket 失败，它与虚拟地址空间耗尽不是一回事。FD 泄漏可能继续引发数据库、网络、资源加载或 Binder 相关异常，监控时应单列 FD 数量与类别。[20.12 FD 资源监控](12-fd-resource-monitoring.md)会展开这类资源故障。

### LMKD 与 kernel OOM

内存压力下，Android 的 [`lmkd`](https://android.googlesource.com/platform/system/memory/lmkd/+/refs/tags/android-17.0.0_r1/lmkd.cpp) 会读取 PSI 等压力信号，结合 `oom_score_adj`、进程重要性和回收收益选择牺牲进程。被选中的应用没有可靠的 Java 临终回调，进程可能直接以 `SIGKILL` 结束。

kernel OOM killer 是更底层的兜底机制。内核依据是 [`android17-6.18-2026-06_r6/mm/oom_kill.c`](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/mm/oom_kill.c)。排查应用线上 LMK 时应优先使用 `ApplicationExitInfo`、Android Vitals 和设备内存分层数据，不能把 kernel OOM 日志当作每次应用低内存退出都一定存在的证据。

[20.5 OOM 治理](05-oom-governance.md)会继续区分 Java heap、Native heap、线程、映射、图形内存与 LMK。

## 用 `ApplicationExitInfo` 读取“上一次进程发生了什么”

API 30 引入的 [`ApplicationExitInfo`](https://developer.android.com/reference/android/app/ApplicationExitInfo) 是退出后的系统证据，不是实时崩溃回调。常见 reason 的解释如下：

| reason | 含义与使用边界 |
|---|---|
| `REASON_CRASH` | Java 等运行时崩溃；结合应用侧异常堆栈确认。 |
| `REASON_CRASH_NATIVE` | Native crash；API 31 起 `getTraceInputStream()` 可能返回 tombstone protobuf。 |
| `REASON_ANR` | 进程因 ANR 被记录为退出；trace 可能存在，也可能因轮转等原因返回 `null`。 |
| `REASON_LOW_MEMORY` | 系统低内存杀进程；设备不支持精确上报时，可能只看到 `REASON_SIGNALED` 与 `SIGKILL`。 |
| `REASON_SIGNALED` | 进程因信号退出；必须结合 `getStatus()` 与上下文判断，不能一律归为 Native crash。 |
| `REASON_INITIALIZATION_FAILURE` | 进程在初始化或 attach 阶段失败。 |
| `REASON_DEPENDENCY_DIED` | 依赖进程死亡导致本进程退出。 |
| `REASON_EXCESSIVE_RESOURCE_USAGE` | 系统因资源使用过量终止进程。 |
| `REASON_USER_REQUESTED` | 用户强行停止或执行了系统归入该类的操作，不应算成应用缺陷。 |

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

返回列表应按 `processName`、`timestamp`、`reason`、`status` 和 `importance` 处理。`getPss()`、`getRss()` 是系统近期采样值，不是死亡瞬间的精确快照；`getTraceInputStream()` 也可能因全局缓冲轮转、权限或没有 trace 而返回 `null`。如果进程发生 ANR 后恢复，随后因别的原因死亡，该记录仍可能附带之前的 ANR trace，所以 reason 与 trace 内容要分别判断。

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

这条分流只负责选择证据，不直接判定根因。例如 `SIGABRT` 可能来自显式 `abort()`、allocator 检查或运行时主动终止；`REASON_LOW_MEMORY` 也不能单独证明应用存在泄漏。

## Google Play Vitals 与内部指标

### Play 的口径和阈值

截至 Android 17，Google Play 将 user-perceived crash rate 与 user-perceived ANR rate 作为 core vitals：

| 指标 | 口径 | 全机型不良行为阈值 | 单手机型号阈值 |
|---|---|---:|---:|
| User-perceived crash rate | 每日活跃用户中，至少一次在应用活跃使用期间遇到 crash 的用户占比 | 1.09% | 8% |
| User-perceived ANR rate | 每日活跃用户中，至少一次遇到用户感知 ANR 的用户占比 | 0.47% | 8% |

这里的“活跃使用”包括显示 Activity 或运行 foreground service。一个用户在同一设备同一天内打开多次，Play 的 daily active user 分母仍按一个用户设备日计算。Play 使用最近 28 天数据评估当前质量；超过阈值可能降低应用在 Play 的可见性，也可能在商店详情页显示警告。官方没有把该阈值表述为固定的审核拒绝线。

Play Vitals 与 SDK 看板出现不同结果很常见：

- Vitals 来自 Android 系统，能够覆盖 SDK 初始化前的部分故障；
- 只纳入符合 Play 数据条件的认证设备、Play 安装和同意共享数据的用户；
- 受隐私最小样本与展示延迟影响；
- Play 以 daily active user 为主要分母，很多 SDK 使用 session 或 event 作为分母。

因此，数据源相同或数值接近都不是必要条件。团队需要明确每张看板回答的问题，而不是要求两边数字相等。阈值与口径以 [Android Vitals](https://developer.android.com/topic/performance/vitals)和 [Crash 指标说明](https://developer.android.com/topic/performance/vitals/crash)为准。

### 团队内部指标必须写清分子与分母

内部没有适用于所有应用的“0.2% 红线”或“99.5% 行业基线”。业务使用时长、进程模型、会话定义和设备分布不同，直接复制一个百分比没有比较价值。建议至少维护以下指标：

| 指标 | 计算方式 | 适合回答的问题 |
|---|---|---|
| 受影响用户率 | 发生目标事件的去重用户数 ÷ 同窗口活跃用户数 | 有多少用户受到影响 |
| Crash-free users | 1 − Crash 受影响用户率 | 版本总体体验 |
| Crash-free sessions | 无 crash 的 session 数 ÷ 全部 session 数 | 一次使用能否完成；前提是固定 session 边界 |
| 事件率 | 事件次数 ÷ session 数，可换算为每万 session | 高频重复故障是否恶化 |
| 启动致命故障率 | 启动阶段 fatal 次数 ÷ 启动次数 | 用户是否无法进入核心页面 |
| ANR 受影响用户率 | 发生目标 ANR 的去重用户数 ÷ 活跃用户数 | ANR 的用户影响 |
| LMK 退出率 | `REASON_LOW_MEMORY` 等受支持记录 ÷ 可观测进程运行或活跃用户 | 内存压力是否导致进程丢失 |
| 新增故障簇影响 | 新版本新增簇的用户数、事件数和关键路径占比 | 是否由本次发布引入 |

每个指标都要附版本、渠道、机型或 RAM 档、ABI、时间窗口、分子、分母和最小样本量。低基数版本只看点估计会剧烈波动，门禁应参考历史基线、置信区间和故障严重度。

## 采集方式怎么选

| 方式 | 覆盖重点 | 优势 | 主要缺口 |
|---|---|---|---|
| Google Play Vitals | Crash、ANR、LMK 等系统质量信号 | 不依赖应用 SDK 存活；能看 Play 设备与型号分布 | 有数据条件、延迟和隐私阈值；自定义业务上下文少 |
| Crashlytics 等崩溃 SDK | Java/Native crash、部分 ANR 与业务上下文 | 接入快，具备版本、用户影响与聚类能力 | 能力随 SDK、Android 版本和配置变化；致命路径上传仍受进程死亡限制 |
| 自建 Java handler | 未捕获 Java `Throwable` | 可以保存业务 breadcrumb 与自有事件模型 | 只能尽力写入；替换默认 handler 必须保留委托链 |
| 自建 Native 捕获 | Native 信号、采样与自有 minidump | 可控制上下文和符号体系 | signal-safe、handler 冲突、系统迁移和兼容成本高 |
| `ApplicationExitInfo` | API 30+ 的历史退出原因与部分 trace | 能补上 LMK、ANR、signal 等进程外证据 | 只能在后续进程读取；记录和 trace 可能缺失 |
| `ProfilingManager` | API 35+ 的按请求采集，以及较新版本的系统触发采集 | 系统管理速率、存储与结果交付 | 触发不保证一定产生结果；必须做版本与能力检测 |

Android 17 / API 37 的 `ProfilingTrigger` 增加了 OOM 等触发类型。应用需要注册感兴趣的 trigger，并接受“系统可能因速率、资源或策略不返回结果”的约束，不能把它当作每次 OOM 必达的回调。API 演进与接入方式见 [19.13 ProfilingManager](../../part3-tools/ch19-apm/13-profiling-manager.md)。

是否建设自研采集，不应只看 DAU。更有用的判断标准是：现有平台缺少的证据是否持续阻塞定位，能否长期维护 Android 版本兼容、隐私治理、符号服务、去重和成本控制。

## 稳定性治理流程

稳定性治理可以按下面的顺序循环，每一步都有可检查的输入和产物。

```text
预防 → 发现 → 证据分类 → 诊断 → 修复 → 分阶段验证
  ↑                                      │
  └──────── 规则、测试与设计约束更新 ─────┘
```

这个流程把“证据分类”单独列出，是为了避免拿 Java Crash 的处理方式分析 ANR，或把所有 `SIGKILL` 都算作 LMK。

### 预防

- 用 Lint、Detekt、编译器检查和自定义规则约束空值、资源关闭、线程创建与主线程 I/O。
- 在 debug 或测试构建启用 StrictMode、sanitizer、GWP-ASan、MTE 等工具，尽早暴露错误。不同工具的设备、构建和性能要求要单独评估。
- 为主线程任务、Binder 调用、启动阶段、缓存和并发数量制定时间或资源预算。
- 做低内存、进程重建、网络失败、磁盘满、FD/线程耗尽和服务端降级等故障注入。
- 对高风险变更使用功能开关、安全模式、灰度发布和可回滚配置。

`try-catch` 不能替代这些设计。给 `WebView` 初始化包一层异常捕获无法处理 renderer 退出；把 `SharedPreferences.commit()` 包装起来也不会消除主线程同步 I/O 引起的 ANR。

### 发现与证据分类

- 看板按版本、渠道、机型、RAM 档、ABI 和关键路径拆分。
- 告警同时考虑绝对影响用户数、相对历史基线、增长速度和严重度。
- Java/Native crash 按归一化堆栈、异常或信号、Build ID 聚类；ANR 按 reason、阻塞关系和主线程状态聚类。
- 对重启后的 `ApplicationExitInfo` 去重，避免每次启动重复上报同一条历史记录。
- 区分新增簇、存量簇回归和单机型异常，避免总体均值掩盖局部故障。

### 诊断

诊断的目标是形成可证伪的根因假设：

- Java Crash：异常因果链、异步来源、mapping、breadcrumb 和输入数据；
- Native Crash：tombstone、Build ID、完整符号、fault address、寄存器和相关内存工具报告；
- ANR：reason、全线程栈、锁与 Binder 关系、CPU 调度、I/O 和 GC；
- OOM/LMK：Java/Native/graphics 内存、线程、FD、映射、进程重要性、设备 RAM 和退出历史。

堆栈顶帧只能说明故障在哪里被观察到。若假设是“锁竞争导致输入 ANR”，还要找到 owner 线程、持锁区间及其 I/O 或 Binder 依赖；若假设是“泄漏导致 LMK”，还要证明保留对象或 Native 分配随生命周期持续增长。

### 修复与验证

修复方案要同时写明根因、影响面、兼容范围、回归风险和撤回条件。发布时先覆盖内部与小比例用户，再逐步扩大；验证要比较同一口径下的修复组、历史基线和未修复版本。

以下情况不应只凭一天的百分比宣布修复完成：

- 样本量不足，置信区间仍覆盖历史水平；
- 原故障簇下降，但同根因迁移到了新堆栈；
- 总体指标改善，特定机型、Android 版本或 RAM 档恶化；
- crash 数下降，但启动失败、ANR 或 LMK 上升。

验证通过后，把能机械检查的经验写入静态规则、测试、资源预算或发布检查项；无法自动检查的部分，要写清 owner 和复查时机。

## 发版门禁与组织责任

发版门禁至少包含三类条件：

1. **绝对条件**：关键路径不可用、启动 crash、数据损坏或安全问题达到约定严重度时停止扩大发布。
2. **相对条件**：新版本相对可比基线的 crash、ANR、LMK 或新增簇影响显著恶化。
3. **证据条件**：样本达到最低要求，版本、渠道和设备分布可比，监控与符号文件已经就绪。

门禁阈值要来自本产品历史分布与风险承受能力，并定期回看，不能使用来源不明的行业数字。

组织上应明确：

- 每类事件和关键模块的 owner；
- P0/P1 等严重度定义、响应时限与升级路径；
- 符号、mapping、系统 trace 和发布配置的保留周期；
- 灰度暂停、配置撤回和紧急发版的决策人；
- 修复验证的结束条件，而不是只记录“代码已合入”。

## 后续章节阅读顺序

- [20.2 Java Crash 治理](02-java-crash-governance.md)：异常处理器、反混淆、异步异常与恢复边界。
- [20.3 Native Crash 治理](03-native-crash-governance.md)：tombstone、符号化和内存安全工具。
- [20.4 ANR 治理](04-anr-governance.md)：不同 ANR 入口的 trace 与系统链路。
- [20.5 OOM 治理](05-oom-governance.md)：Java、Native、线程、映射与 LMK。
- [20.6 稳定性指标](06-stability-metrics.md)：分子、分母、聚类、基线与发版门禁。
- [20.9 WebView renderer OOM 恢复](09-webview-renderer-oom-recovery.md)：宿主与渲染进程的故障隔离。

## 源码与文档锚点

- 平台：AOSP [`android-17.0.0_r1`](https://android.googlesource.com/platform/manifest/+/refs/tags/android-17.0.0_r1/)
- Java fatal handler：[`RuntimeInit.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/com/android/internal/os/RuntimeInit.java)
- ART heap：[`heap-inl.h`](https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/runtime/gc/heap-inl.h) · [`heap.cc`](https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/runtime/gc/heap.cc)
- Native crash：[`debuggerd/handler`](https://android.googlesource.com/platform/system/core/+/refs/tags/android-17.0.0_r1/debuggerd/handler/) · [`crash_dump.cpp`](https://android.googlesource.com/platform/system/core/+/refs/tags/android-17.0.0_r1/debuggerd/crash_dump.cpp) · [`tombstoned`](https://android.googlesource.com/platform/system/core/+/refs/tags/android-17.0.0_r1/debuggerd/tombstoned/) · [`libunwindstack`](https://android.googlesource.com/platform/system/unwinding/+/refs/tags/android-17.0.0_r1/libunwindstack/)
- ANR：[`AnrHelper.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/am/AnrHelper.java) · [官方 ANR 诊断指南](https://developer.android.com/topic/performance/anrs/diagnose-and-fix-anrs)
- 退出历史：[`ApplicationExitInfo`](https://developer.android.com/reference/android/app/ApplicationExitInfo)
- 进程隔离：[`WebViewClient.onRenderProcessGone()`](https://developer.android.com/reference/android/webkit/WebViewClient#onRenderProcessGone(android.webkit.WebView,android.webkit.RenderProcessGoneDetail))
- 系统 profiling：[`ProfilingManager`](https://developer.android.com/reference/android/os/ProfilingManager) · [`ProfilingTrigger`](https://developer.android.com/reference/android/os/ProfilingTrigger)
- 内存回收：[`lmkd.cpp`](https://android.googlesource.com/platform/system/memory/lmkd/+/refs/tags/android-17.0.0_r1/lmkd.cpp) · kernel [`android17-6.18-2026-06_r6/mm/oom_kill.c`](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/mm/oom_kill.c)
- 指标：[Android Vitals](https://developer.android.com/topic/performance/vitals) · [User-perceived crash rate](https://developer.android.com/topic/performance/vitals/crash)
