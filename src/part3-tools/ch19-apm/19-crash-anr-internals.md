---
title: "崩溃与 ANR 捕获机制"
chapter: "19"
section: "19.19"
applicable_versions: "Android 8 (API 26) - Android 17 (API 37)"
last_verified: "2026-04-24"
confidence: high
tags: [apm, crash, anr, stability, crashpad]
related_chapters: ["19.0", "19.03", "19.13"]
task6_state: reviewed
sources:
- type: official
  path: https://developer.android.com/reference/java/lang/Thread.UncaughtExceptionHandler
- type: official
  path: https://developer.android.com/reference/android/app/ApplicationExitInfo
- type: official
  path: https://developer.android.com/reference/android/app/ActivityManager#getHistoricalProcessExitReasons(java.lang.String,int,int)
- type: reference
  path: https://raw.githubusercontent.com/chromium/crashpad/main/doc/overview_design.md
- type: official
  path: https://developer.android.com/ndk/guides/gwp-asan
- type: aosp
  path: https://android.googlesource.com/platform/art/+/android-17.0.0_r1/runtime/signal_catcher.cc
- type: aosp
  path: https://android.googlesource.com/platform/system/core/+/android-17.0.0_r1/debuggerd/proto/tombstone.proto
- type: aosp
  path: https://android.googlesource.com/platform/bionic/+/android-17.0.0_r1/libc/include/signal.h
status: finalized
pipeline_stage: ready-to-publish
task9_state: reviewed
task2b_state: fixed
---


# 崩溃与 ANR 捕获机制

稳定性 APM 面对的不是一种“崩溃”。Java 未捕获异常、Native 同步致命信号、系统判定的 ANR、lmkd 杀进程和资源耗尽，发生时的线程状态、权限与剩余执行时间都不同。采集器应先回答“当前还能安全做什么”，再决定采哪些数据。

以下内容以 Android 17 / API 37 / `android-17.0.0_r1` 为平台源码基线，涉及内核资源边界时以 `android17-6.18-2026-06_r6` 为基线。Android 8—10 的兼容路径会保留，但不会把厂商权限、root 能力或旧时代可读文件写成普通应用的通用能力。

## 1. 四类现场，四种证据强度

| 现场 | 主要入口 | 进程状态 | 最可信的证据 |
| --- | --- | --- | --- |
| Java Crash | `Thread.UncaughtExceptionHandler`、Android `RuntimeInit` 默认处理器 | VM 仍在运行，资源可能已耗尽 | `Throwable`、crashing thread、预存 breadcrumb、系统退出记录 |
| Native Crash | debuggerd/Crashpad signal path | 堆、锁或栈可能已经损坏 | `siginfo_t`、`ucontext_t`、tombstone/minidump、ELF build id |
| ANR | system_server 判定、ART `SignalCatcher`、`ApplicationExitInfo` | 进程可能仍存活，也可能稍后被杀 | 系统 ANR trace、触发类型、同时间窗 Perfetto/ProfilingTrigger |
| 资源耗尽与 LMK | 周期资源采样、lmkd、退出历史 | 临界点可能无法执行用户代码 | 预采样趋势、系统 reason、RSS/PSS、FD/线程/VMA 水位 |

“主线程卡了 5 秒”是端侧 watchdog 事件，不自动等于系统 ANR；`SIGKILL` 也不自动等于 LMK。稳定性样本要保存 `evidence_source` 与 `confidence`，避免后端把推断当成系统结论。

## 2. Java Crash：代理默认处理器，不能截断系统终止链

### 2.1 Android 17 的默认处理路径

Android 17 的 `RuntimeInit.commonInit()` 安装两层处理器：

- `LoggingHandler` 作为 VM 的 uncaught-exception pre-handler，负责输出 fatal exception。
- `KillApplicationHandler` 作为 `Thread` 的 default handler，向 ActivityManager 报告崩溃，并终止进程。

应用调用 `Thread.setDefaultUncaughtExceptionHandler()` 会替换第二层，不能替换内部 pre-handler。APM 安装前必须保存当前 default handler，采样后调用它。Android 17 的 `ProfilingTrigger.TRIGGER_TYPE_OOM` 也明确要求自定义 handler 链回 default handler，否则系统无法在 OOM 路径提供触发式 heap dump。

下面的代码展示 Java 层代理的最小骨架。`CrashEnvelopeStore.tryWriteBounded()` 表示项目预先初始化的有界存储；它不能在崩溃时打开数据库、创建线程或等待网络。

```kotlin
class ChainedCrashHandler private constructor(
    private val previous: Thread.UncaughtExceptionHandler?,
    private val store: CrashEnvelopeStore,
) : Thread.UncaughtExceptionHandler {
    private val handling = AtomicBoolean(false)

    override fun uncaughtException(thread: Thread, throwable: Throwable) {
        if (!handling.compareAndSet(false, true)) {
            // 同时崩溃或 previous 链成环时，立即结束，避免递归和死锁。
            hardTerminate()
        }

        try {
            store.tryWriteBounded(
                threadId = thread.id,
                threadName = thread.name,
                throwable = throwable,
            )
        } catch (_: Throwable) {
            // 采集失败不能替换原始崩溃。
        }

        try {
            previous?.uncaughtException(thread, throwable)
        } catch (_: Throwable) {
            hardTerminate()
        }

        // 正常的 RuntimeInit handler 不会返回；空 handler 或第三方返回都在这里终止。
        hardTerminate()
    }

    private fun hardTerminate(): Nothing {
        Process.killProcess(Process.myPid())
        exitProcess(10)
    }

    companion object {
        fun install(store: CrashEnvelopeStore) {
            val previous = Thread.getDefaultUncaughtExceptionHandler()
            val handler = ChainedCrashHandler(previous, store)
            Thread.setDefaultUncaughtExceptionHandler(handler)
        }
    }
}
```

这段代理保留系统默认 handler，并用 CAS 阻止采集器重入。`previous` 自身若返回，代码才执行防御性终止；正常 Android 路径会在系统 handler 中结束进程。实际安装还要拒绝 `previous === handler` 一类循环，并在集成测试中验证 Java exception、Java heap OOM、后台线程崩溃和多个 SDK 安装顺序。

### 2.2 崩溃当下只写 envelope

Java handler 比 Native signal handler 宽松，但不能假设堆和锁可用。`Throwable.printStackTrace()`、JSON 序列化、数据库事务和压缩都会分配对象；遇到 OOM 或 corrupted runtime 时，它们可能再次失败。

推荐把采集拆为两段：

- 正常运行期维护固定容量 breadcrumb ring buffer，并周期写入版本、进程、前后台、资源水位等低敏快照。
- crash handler 只写 magic、schema version、时间、线程 id、异常类型和对预存 breadcrumb 的序号；栈序列化设置深度、cause 数和字节上限。
- 冷启动后校验 checksum 与完整标记，再做符号化所需字段补充、压缩、去重和上传。
- crash store 使用独立小文件或预分配区域；不能与业务数据库共用锁和事务。

“立即发网络请求确保上报”成功率低，还会拉长系统崩溃处理。同步等待应有很小的硬超时，队列满或存储异常时宁可丢 APM 附件，也不能阻塞系统终止链。

## 3. Native Crash：signal handler 只负责交接

### 3.1 debuggerd、tombstone 与 Crashpad

Android 上常见的致命信号包括 `SIGSEGV`、`SIGABRT`、`SIGBUS`、`SIGILL`、`SIGFPE` 和 `SIGTRAP`。Bionic/debuggerd 的系统处理路径会采集寄存器、线程、maps、backtrace、abort message 等信息，经 `tombstoned` 保存 tombstone。普通应用不能直接读取 `/data/tombstones`；Android 12 / API 31 起，可在 `ApplicationExitInfo.REASON_CRASH_NATIVE` 的 `getTraceInputStream()` 中取得对应 tombstone protobuf，前提是系统环形存储仍保留它。

Breakpad 常见进程内 handler 生成 minidump。Crashpad 的 Linux/Android 设计把客户端与独立 handler 进程分开：客户端预先注册，崩溃时只把异常上下文位置通知 handler，后者读取目标进程并写 dump。out-of-process 设计能避开一部分崩溃进程堆与锁损坏，但 handler 进程启动、注册、权限和生命周期仍要在正常运行期准备好。

三种产物不要混称：

- tombstone 是 Android 系统诊断产物，Android 17 protobuf schema 位于 debuggerd。
- minidump 是 Breakpad/Crashpad 的跨平台 dump 格式，便于 APM 上传和服务端处理。
- symbol file、未剥离 ELF 或符号服务器负责把 PC 还原为函数和源码行。每个 so 必须保存 build id；只按 version name 选符号会在热修复或重打包后误符号化。

### 3.2 signal 上下文的硬边界

致命 signal handler 中只能依赖 async-signal-safe 操作和预先准备的内存、FD、备用栈。下面这些动作不应出现：

- `malloc/new/free`、STL 容器扩容、普通日志与 JSON。
- `pthread_mutex`、Java/JNI 回调、数据库与线程池。
- 在未知栈状态下调用通用 libunwind 并假设它不分配、不加锁。
- 直接上传网络、解析 `/proc` 大文件或遍历所有线程。

handler 可读取 `siginfo_t`、`ucontext_t` 与当前 tid，把定长结构写入预打开 pipe/socket，或通知 Crashpad handler。完整 unwind、maps 读取和 minidump 生成应由受控的外部 handler 或系统 debuggerd 完成。

如果自研 reporter 必须与前一个 handler 共存，还要处理 `SA_SIGINFO` 签名、`SIG_DFL`、`SIG_IGN`、signal mask、`SA_RESETHAND`、备用栈和重入。同步产生的 `SIGSEGV`/`SIGBUS` 被忽略后通常会再次触发，不能靠 `SIG_IGN` 让进程继续。未经系统版本与 ABI 测试的几行 `sigaction()` 链接代码不具备生产可靠性。

### 3.3 从 fault 到上报的顺序

一条可维护的 Crashpad 路径通常是：

1. 应用正常启动时创建 handler 进程、注册 socket、备用栈、共享内存与注解区。
2. 崩溃线程收到同步致命信号，客户端 handler 读取 signal、fault address 与寄存器上下文。
3. 客户端通过预建 IPC 通知外部 handler，崩溃线程停在可被读取的状态。
4. 外部 handler 读取线程、maps、模块与内存片段，写 minidump。
5. 客户端恢复或转交系统 signal 处理语义，让 debuggerd/tombstoned 继续生成系统证据并终止进程。
6. 下次启动扫描完整 dump，按 build id 符号化、聚类和上传。

第 5 步必须按所用 Crashpad/Breakpad 版本的官方实现验证。自研 handler 吞掉 signal 会同时损失系统 tombstone、Android Vitals 归因和后续 SDK 的处理机会。

## 4. ANR 捕获演进：权限变化比文件名更重要

### 4.1 `/data/anr` 从来不是量产 App API

旧版调试资料常以 `/data/anr/traces.txt` 为入口，较新系统则在 `/data/anr/` 下保存独立 trace 文件。Android 17 的 `init.rc` 以 `0775 system system` 创建目录，具体 trace 仍由系统侧控制。目录模式不代表普通应用能读取内部文件；SELinux、文件 owner/mode 与系统服务访问控制共同限制它。

因此：

- adb/bugreport、root、userdebug 或厂商系统组件可以直接取证。
- 三方量产应用不能把轮询、inotify 或反射系统服务当成稳定方案。
- 文件名、压缩方式和保留数量都是实现细节，不应写进端侧协议。

### 4.2 SIGQUIT 与 ART SignalCatcher

系统收集 Java 线程 dump 时会向进程发送 `SIGQUIT`。ART 在进程内专门启动 SignalCatcher 线程；Android 17 的 `signal_catcher.cc` 明确说明，`SIGQUIT` 在各线程被 block，再由等待线程通过 `sigwait()` 同步消费，因此普通 `sigaction` handler 不会被调用。

这解释了两个看似矛盾的现象：

- ANR 取证路径会使用 `SIGQUIT`。
- 应用再注册一个 `SIGQUIT` handler，却不能稳定收到系统的 ANR dump 信号。

所谓 Signal Catcher Hook 往往需要改信号掩码、拦 ART 内部符号、改 libsigchain 或参与系统 ANR 流程。它与 Android 版本、ART 实现和其他 SDK 强耦合，适合厂商 ROM、root/userdebug 诊断或可回滚的实验，不适合作为普通应用默认能力。

端侧 main-looper watchdog 可以在卡顿期间多次采主线程栈，用于提前发现长消息、锁等待和 Binder 阻塞。它没有 system_server 的输入分发、广播、service、content provider 等超时上下文，只能标记 `suspected_anr`。系统 ANR 结论仍以后续 `ApplicationExitInfo`、Vitals 或系统 trace 为准。

### 4.3 Android 11+ 的 ApplicationExitInfo

API 30 起，`ActivityManager.getHistoricalProcessExitReasons()` 提供当前 UID/包的历史退出记录。常用字段包括 reason、status、importance、process name、timestamp、description、PSS/RSS 和 process state summary。

读取时要遵守这些口径：

- `REASON_ANR` 的 trace 通常是系统 ANR 文本流；流可能为空。
- API 31 起，`REASON_CRASH_NATIVE` 可返回按 `tombstone.proto` 编码的 protobuf，不能按 UTF-8 文本解析。
- trace 位于独立的全局环形存储，其他应用的新记录也可能覆盖它。
- 一个进程曾发生 ANR、随后恢复并因其他原因退出时，该退出记录仍可能带 ANR trace。trace 存在不等于 `reason == REASON_ANR`。
- PSS/RSS 是系统最近采样值，不保证等于死亡前一刻；0 也可能表示来不及采样。
- 不支持 LMK report 的设备会把低内存 kill 记为 `REASON_SIGNALED + SIGKILL`。这个组合只能在该能力不受支持时标成“可能 LMK”，不能无条件归因。

下面的代码展示启动后拉取、去重和有界读取。`ExitEnvelope` 与 `ExitKind` 是项目自己的上传 DTO 和枚举；代码保留二进制 trace，不在端上把 tombstone protobuf 误转为字符串。

```kotlin
@RequiresApi(30)
fun readRecentExits(
    context: Context,
    seen: Set<String>,
    traceLimitBytes: Int = 2 * 1024 * 1024,
): List<ExitEnvelope> {
    val am = context.getSystemService(ActivityManager::class.java)
    val supportsLmkReason = ActivityManager.isLowMemoryKillReportSupported()

    return am.getHistoricalProcessExitReasons(
        context.packageName,
        0,   // all pids belonging to this package
        20,
    ).mapNotNull { info ->
        val key = listOf(
            info.processName,
            info.pid,
            info.timestamp,
            info.reason,
            info.status,
        ).joinToString(":")
        if (key in seen) return@mapNotNull null

        val kind = when (info.reason) {
            ApplicationExitInfo.REASON_ANR -> ExitKind.ANR
            ApplicationExitInfo.REASON_CRASH -> ExitKind.JAVA_CRASH
            ApplicationExitInfo.REASON_CRASH_NATIVE -> ExitKind.NATIVE_CRASH
            ApplicationExitInfo.REASON_LOW_MEMORY -> ExitKind.LMK
            ApplicationExitInfo.REASON_SIGNALED ->
                if (!supportsLmkReason && info.status == OsConstants.SIGKILL) {
                    ExitKind.POSSIBLE_LMK
                } else {
                    ExitKind.SIGNAL
                }
            else -> ExitKind.OTHER
        }

        val trace = try {
            info.traceInputStream?.use { it.readAtMost(traceLimitBytes) }
        } catch (_: IOException) {
            null
        }

        ExitEnvelope(
            dedupKey = key,
            kind = kind,
            processName = info.processName,
            timestampMs = info.timestamp,
            status = info.status,
            pssKb = info.pss,
            rssKb = info.rss,
            traceBytes = trace,
            traceEncoding = when {
                trace == null -> null
                info.reason == ApplicationExitInfo.REASON_CRASH_NATIVE ->
                    "tombstone-protobuf"
                else -> "anr-text"
            },
        )
    }
}

private fun InputStream.readAtMost(limit: Int): ByteArray {
    val output = ByteArrayOutputStream(minOf(limit, 32 * 1024))
    val buffer = ByteArray(8 * 1024)
    var remaining = limit
    while (remaining > 0) {
        val count = read(buffer, 0, minOf(buffer.size, remaining))
        if (count <= 0) break
        output.write(buffer, 0, count)
        remaining -= count
    }
    return output.toByteArray()
}
```

这段代码仍会分配内存和执行 Binder/文件 I/O，只能在冷启动后的后台任务运行。生产实现要给总记录数、单 trace、单次任务时长和本地磁盘设置上限；解析失败保存 schema/version 与少量摘要，不反复上传同一条损坏记录。

## 5. 资源耗尽：OOM 只是结果名的一部分

### 5.1 Java heap、Native RSS、FD、线程和 VMA

| 资源 | 常见失败 | 应用可观测信号 | 容易误判的地方 |
| --- | --- | --- | --- |
| Java heap | `OutOfMemoryError`、GC thrash | heap used/max、GC、对象增长 | Java heap 正常不能排除 Native/graphics 增长 |
| Native/graphics | RSS/PSS 上升、分配失败 | `Debug.MemoryInfo`、`/proc/self/status`、模块计数 | RSS 上升不自动等于泄漏 |
| FD table | `open/socket/dup` 返回 `EMFILE` | `/proc/self/fd` 数、`RLIMIT_NOFILE`、失败 errno | 扫目录本身也短暂占用 FD |
| 线程 | `pthread_create` 返回 `EAGAIN`、Java 创建线程失败 | `Threads`、线程创建率、pool active/queue | 线程数只是一个维度，还要看 stack、地址空间和调度 |
| VMA/地址空间 | `mmap` 返回 `ENOMEM` | `/proc/self/maps` 条目、`VmSize`、ABI、映射来源 | 64 位 `VmSize` 含大块 reserve，不能单独作为内存压力 |
| 系统低内存 kill | 进程无回调地消失 | `ApplicationExitInfo`、Vitals、预存水位 | `SIGKILL` 还可能来自 force-stop、shell 或其他系统策略 |

FD 泄漏会先破坏 socket、文件、eventfd、pipe、Binder 辅助资源等创建路径。预警阈值应相对当前 `RLIMIT_NOFILE` 计算，并保留 FD 类型分布；只写“超过 1024”无法跨设备和进程配置复用。

线程耗尽常由无界 executor、每请求建线程、阻塞任务堆积或 Native 库私建线程引起。每个线程还消耗用户栈映射、内核 task 资源与调度预算。Android/内核最终可能以 `EAGAIN` 或内存失败表现，不能把所有创建失败都标成 Java heap OOM。

VMA 风险在 32 位进程更早暴露：有限地址空间会受 so、JIT、线程栈、ashmem、graphics 与碎片共同影响。64 位进程也可能碰到异常映射增长或 `vm.max_map_count` 一类限制，但很大的 `VmSize` 可能只是保留地址，不代表对应物理内存已经驻留。

Android 17 现代设备的低内存处置主要由用户态 lmkd 结合 PSI、内存压力、swap 状态和 `oom_score_adj` 选择目标，不应继续用早期 kernel lowmemorykiller 的固定 minfree 模型解释所有设备。`oom_score_adj` 是 kill 优先级输入，不是“达到此值立即杀”的触发阈值。

### 5.2 预警靠正常运行期采样

建议按前后台与业务阶段做低频、错峰采样：

- 读取 `/proc/self/status` 的 `VmRSS`、`VmSize`、`Threads`，结合 `Debug.MemoryInfo`。
- 统计 `/proc/self/fd`，并在诊断抽样中解析 symlink 类型；接近 FD 上限时停止高成本分类。
- 统计 maps 行数与主要映射类别，不在高频任务中上传完整 `/proc/self/maps`。
- 记录线程创建速率、pool size、queue depth、任务最长等待，而非只记录瞬时线程总数。
- 给 WebView、图片、数据库、音视频、模型与图形资源建立模块计数。
- 使用分位数和增长斜率设告警，同时保留设备 RAM、ABI、前后台和进程类型。

临界水位出现后，采样器应降载。继续频繁扫描 `/proc`、抓 heap dump 或拼大日志，可能成为压垮进程的额外负担。

### 5.3 Android 8—10 没有退出历史时

API 26—29 无 `ApplicationExitInfo`。Java crash、Native crash 仍可由 handler/reporting library 捕获；系统 ANR 与 LMK 对普通应用没有等价的官方本地补拉 API。

可用方案及其证据强度如下：

- main-looper watchdog 和周期主线程栈用于 `suspected_anr`，不能冒充 system_server ANR。
- 上次运行的 heartbeat、clean-shutdown marker 与资源水位可识别“非正常消失”，但 force-stop、系统更新、重启、LMK 和外部 SIGKILL 可能相同，应归为 unknown/possible LMK。
- Play Console Android Vitals 或厂商服务端数据可补系统 ANR/LMK，但不属于端侧即时 API。
- bugreport、root、userdebug 和厂商合作能提供系统 trace，能力必须按部署环境单列。
- KOOM 一类 fork-dump 是版本敏感的工程方案，不是 Android 平台保证；适用版本、ART suspend 和 fork 后行为应以项目实测及第 19.3 章为准。

不存在“低版本下次启动继续补拉 ANR/LMK”的通用端侧接口。把未知退出硬归为 LMK，会让稳定性率看起来完整，却失去诊断可信度。

## 6. 现场快照：把高成本信息提前准备

### 6.1 分三种时机采集

| 时机 | 可做的事 | 不应做的事 |
| --- | --- | --- |
| 正常运行期 | breadcrumb、资源水位、network/UI 摘要、预开 store、模块表 | 持续抓全量 logcat 或保存敏感内容 |
| Java crash handler | 有界异常 envelope、已有 ring buffer 序号、链回系统 handler | 数据库、压缩、网络、无限栈展开 |
| Native signal handler | signal、fault address、tid、ucontext 位置、通知外部 handler | malloc、锁、JNI、通用日志、进程内复杂 unwind |
| 下次启动 | `ApplicationExitInfo`、trace/minidump 校验、补设备/版本、上传 | 在主线程解析大 trace |

寄存器来自 `ucontext_t` 或系统 tombstone，不应由 Java handler 伪造。RSS/PSS、FD、线程数适合使用崩溃前最近一次采样；在 signal handler 里临时扫描 `/proc` 风险很高。

### 6.2 Breadcrumb 与日志

breadcrumb 应记录低基数事件，不记录原始输入：

- 页面/组件 id、生命周期和前后台切换。
- 点击 action id，不保存控件文本、账号或输入内容。
- 网络 route pattern、结果类别和 request id，不保存 URL query/header/body。
- 关键开关、实验枚举、权限或配置版本。

Logcat 不是稳定的私有 crash store。权限、ring buffer 覆盖和设备策略都会影响可用性，读取过程本身也有成本。应用内部应维护有界、脱敏的日志 ring buffer；crash envelope 只引用最近序号，冷启动后再读已落盘片段。

每条附件要有 schema、长度、checksum、complete flag 和隐私版本。写入顺序通常是 payload → checksum → complete flag，冷启动只处理完整记录。

## 7. 多 SDK 冲突：链条正确也可能互相拖死

### 7.1 Java default handler

后安装的 SDK 会覆盖先安装者。即使每家都保存 `previous`，仍可能出现：

- A → B → A 的循环链。
- 多个 handler 依次等待 I/O，超过系统容忍时间。
- 某个 handler 捕获异常后返回，截断 `RuntimeInit` 默认终止与 OOM ProfilingTrigger。
- SDK 延迟初始化，应用在 `Application.onCreate()` 后检查时正常，稍后又被覆盖。

工程上应设一个 owner：

1. 由应用 stability hub 安装唯一代理并保存系统 default handler。
2. 自研 sink 只接受内存事件或有界 store，不各自安装 default handler。
3. 第三方 SDK 优先使用“不接管 handler”或 callback 模式。
4. 无法关闭接管时，固定初始化顺序，启动后和首个 Activity 后校验 handler identity。
5. 测试崩溃进程是否按预期退出、系统退出历史是否存在、各 SDK 是否各收到一次。

不能并行调用多个 Java crash sink。它们可能访问同一日志锁、数据库或 executor；崩溃线程应按预算串行调用，超时或失败立即跳过剩余附件并进入系统 handler。

### 7.2 Native signal handler

Native 冲突更难靠安装顺序解决：

- 库可能拦截 `sigaction`，或通过 libsigchain 与 ART/system handler 交互。
- `SA_SIGINFO` 和单参数 handler 混调会直接二次崩溃。
- handler 可能使用同一备用栈、修改 signal mask，或在重入时覆盖静态缓冲。
- Crashpad、GWP-ASan、MTE 与系统 debuggerd 对特定 fault 有自己的处理语义。

不要编写一个“万能 signal hub”去同步回调所有 SDK。选定一个经过 Android 版本验证的 Native reporter，其他 SDK 改为导入它产出的 tombstone/minidump 或只做启动后处理。无法控制第三方库时，至少在 CI 中枚举已安装 signal action、制造各类 fault，并验证系统 tombstone 和 build-id 符号化没有丢失。

## 8. GWP-ASan：Android 17 默认走 Recoverable 抽样

GWP-ASan 用少量 guard-page allocation 捕获 heap use-after-free 与 heap-buffer-overflow。它不要求重编译第三方 Native 库，CPU 开销设计得很低，但会为命中进程保留一小块固定内存。它是线上取证工具，不是内存安全缓解机制。

公开配置应使用 manifest：

| `android:gwpAsanMode` | Android 17 行为 | 使用建议 |
| --- | --- | --- |
| 未设置 / `default` | Recoverable GWP-ASan，约 1% 进程启动被选中 | 常规生产默认 |
| `always` | 每次启动启用基础 GWP-ASan；命中后终止进程 | 专项灰度、测试或能接受 crash 的进程 |
| `never` | 禁用 | 仅在兼容故障明确且有替代诊断时使用 |

Recoverable 模式命中后会生成 native crash report，然后允许进程继续；该进程已经发生内存破坏，后续行为没有保证，可能稍后以另一个症状崩溃。一次进程生命周期只生成一份 Recoverable 报告。官方文档还明确指出：代表 Recoverable GWP-ASan fault 的 `SIGSEGV` 不会调用应用自定义 signal handler。因此，APM 不应依赖“自己的 SIGSEGV handler 先判断并放行”来维持 recovery。

Android 17 源码中的默认内部参数是：

| 参数 | `android-17.0.0_r1` 默认值 | 含义 |
| --- | --- | --- |
| `SampleRate` | `2500` | 被选中进程约每 2500 次 allocation 采一个 |
| `ProcessSampling` | default/system app 模式为 `128`，`always` 等模式为 `1` | 进程抽样分母 |
| `MaxSimultaneousAllocations` | `32` | guard pool 同时保留的 allocation 上限 |
| `Recoverable` | `true` 的内部默认 | 具体是否使用还受 manifest mode 与初始化路径控制 |

这些数值来自 Bionic 实现，不是应用可长期依赖的 SDK 契约。普通应用也不应尝试写 `libc.debug.gwp_asan.*` 系统属性或环境变量作为线上配置。Android 17 的 `SetDefaultGwpAsanOptions()` 还把 `InstallSignalHandlers` 设为 false，由 Android debuggerd/Bionic 的既有路径协作完成报告。

源码中的 recoverable path 会在 fault 前后调用 GWP-ASan pre/post crash hook，并通过 `recoverable_crash` 避免按普通致命 signal 重发。Permissive MTE 也使用 recoverable 出口，但 fault 识别和恢复逻辑独立。APM 只需要保留系统 tombstone、GWP-ASan cause、allocation/deallocation/access trace 和模块 build id，不能复制系统 handler 内部实现到应用 signal handler。

## 9. Android 17 ProfilingTrigger 是补充证据

ProfilingManager 从 API 35 提供 app-driven profiling。ProfilingTrigger 从 API 36 加入系统事件触发，并在 36.1 与 API 37 扩充。与稳定性相关的主要能力是：

| 版本 | trigger | 产物与边界 |
| --- | --- | --- |
| API 36 | `TRIGGER_TYPE_ANR` | 系统识别 ANR 后、可能杀进程前截取运行中的 system trace；触发不代表进程必然被杀 |
| 36.1 | request-running-trace、force-stop、recents、task-manager kill | 适合解释用户或系统终止，不是 crash handler |
| API 37 | `OOM`、`ANOMALY`、`KILL_EXCESSIVE_CPU_USAGE`、`COLD_START`、`APP_COMPAT` | OOM 返回 Java heap dump；其他 trigger 的 artifact 按类型变化 |

触发器要预先注册，并受应用配置与系统 rate limit 共同约束。它们提高了“事故前后有 trace”的概率，不能替代 Java handler、Native tombstone 或 `ApplicationExitInfo`。

API 37 的 OOM trigger 有一条容易被多 SDK 破坏的前置条件：自定义 `UncaughtExceptionHandler` 必须调用 default handler。若稳定性 SDK 吞掉 `OutOfMemoryError`，系统 trigger 无法工作；应用只能在资源尚可时自行调用 `requestProfiling()`，而 crash 当下再请求通常太晚。

Profiling API 的完整请求、回调、36.1 扩展版本判断与 rate-limit 处理见第 19.13 章。这里只把它作为稳定性证据源接入同一 incident id。

## 10. 版本化接入建议

| 版本 | Java / Native Crash | ANR | LMK / 资源耗尽 |
| --- | --- | --- | --- |
| Android 8—10 / API 26—29 | chained Java handler + Crashpad/系统 tombstone | watchdog 只做疑似事件；系统证据依赖 Vitals/bugreport/OEM | 周期预采样；未知退出保持 unknown |
| Android 11 / API 30 | 同左 | `ApplicationExitInfo` ANR text trace | `REASON_LOW_MEMORY` 或受限条件下 possible LMK |
| Android 12—14 / API 31—34 | native tombstone protobuf 可经退出历史取得 | 同 API 30 | 同 API 30；Android 14+ 默认 Recoverable GWP-ASan |
| Android 15 / API 35 | 加入 app-driven ProfilingManager | 可主动采 profile，但不是 ANR 结论 | 高水位时可按预算主动 profiling |
| Android 16 / API 36、36.1 | 同左 | 预注册 ANR ProfilingTrigger | 增加用户终止类 trigger |
| Android 17 / API 37 | 保持系统 handler 链，使用 API 37 trigger | ANR trigger + 退出历史互证 | OOM/anomaly/excessive CPU trigger + 资源趋势 |

上线前应建立故障用例表：Java exception、Java OOM、Native UAF/abort/SEGV、后台与前台 ANR、FD 上限、线程创建失败、mmap 失败、LMK、force-stop，以及多个 SDK 的不同初始化顺序。每个用例同时核对进程是否按预期终止、系统 reason、trace/dump、APM envelope、重复上报和隐私裁剪。

## 11. Android 17 与 6.18 r6 源码锚点

### Java Crash、ANR 与退出历史

- [Android 17 `RuntimeInit.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/com/android/internal/os/RuntimeInit.java)：`LoggingHandler`、`KillApplicationHandler` 与默认终止链。
- [Android 17 `ApplicationExitInfo.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/app/ApplicationExitInfo.java)：reason、PSS/RSS、ANR trace、API 31+ tombstone protobuf 与环形存储边界。
- [Android 17 ART `signal_catcher.cc`](https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/runtime/signal_catcher.cc)：`SIGQUIT` 被 block 后由 `sigwait()` 消费的实现。
- [Android 17 `init.rc`](https://android.googlesource.com/platform/system/core/+/refs/tags/android-17.0.0_r1/rootdir/init.rc)：`/data/anr` 与 tombstone 目录的系统侧创建。
- [Android 17 tombstone schema](https://android.googlesource.com/platform/system/core/+/refs/tags/android-17.0.0_r1/debuggerd/proto/tombstone.proto)：Native tombstone protobuf 解析依据。

### Native reporter、GWP-ASan 与系统能力

- [Crashpad Overview Design](https://chromium.googlesource.com/crashpad/crashpad/+/main/doc/overview_design.md)：客户端、外部 handler、注册与 crash capture。
- [Android 17 Bionic signal header](https://android.googlesource.com/platform/bionic/+/refs/tags/android-17.0.0_r1/libc/include/signal.h)：`sigaction`、`SA_SIGINFO` 与 signal 类型定义。
- [Android 17 debuggerd handler](https://android.googlesource.com/platform/system/core/+/refs/tags/android-17.0.0_r1/debuggerd/handler/debuggerd_handler.cpp)：致命 signal、GWP-ASan/MTE recoverable path 与系统报告交接。
- [Android 17 GWP-ASan wrapper](https://android.googlesource.com/platform/bionic/+/refs/tags/android-17.0.0_r1/libc/bionic/gwp_asan_wrappers.cpp)：`2500/128/32` 默认参数与 pre/post crash hook。
- [Android GWP-ASan 官方指南](https://developer.android.com/ndk/guides/gwp-asan)：manifest mode、Recoverable 行为、开销与自定义 signal handler 边界。
- [Android 17 ProfilingTrigger](https://android.googlesource.com/platform/packages/modules/Profiling/+/refs/tags/android-17.0.0_r1/framework/java/android/os/ProfilingTrigger.java)：API 37 trigger 类型与 artifact 说明。
- [ProfilingTrigger API 参考](https://developer.android.com/reference/android/os/ProfilingTrigger)：API 36、36.1 与 37 的公开版本边界。
- [Android 17 lmkd](https://android.googlesource.com/platform/system/memory/lmkd/+/refs/tags/android-17.0.0_r1/)：PSI、内存压力与 `oom_score_adj` 选 victim 的用户态实现。

### `android17-6.18-2026-06_r6`

- [FD table：`fs/file.c`](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/fs/file.c)：进程 FD table 的分配与扩展。
- [线程/进程创建：`kernel/fork.c`](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/kernel/fork.c)：task、clone/fork 与资源失败路径。
- [VMA：`mm/mmap.c`](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/mm/mmap.c)：mmap 与 VMA 管理的核心实现。
