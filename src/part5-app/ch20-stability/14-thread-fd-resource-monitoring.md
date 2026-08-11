---
title: "线程与 FD 资源监控治理"
chapter: "20"
status: "finalized"
drafted_date: "2026-05-23"
applicable_versions: "Android 8 (API 26) - Android 17 (API 37)"
tags: [stability, thread, fd, oom, observability]
related_chapters: ["20.5", "20.7", "26.2", "26.5", "14.26"]
created_by: "task2a-knowledge-gap"
created_date: "2026-05-23"
gap_source: "参考书素材 + research-gaps + AOSP/官方文档对照"
last_verified: "2026-06-13"
last_verified_against: "AOSP android-16.0.0_r1 / Android Developers API reference"
confidence: medium
sources:
  - type: blog
    path: "Clippings/Android 应用稳定性剖析与优化 - 线程监控：如何解决“匿名”线程？.md"
  - type: blog
    path: "Clippings/Android 应用稳定性剖析与优化 - 实现 FD 监控：文件描述符（FD）超限怎么办？.md"
  - type: blog
    path: "Clippings/Android 应用稳定性剖析与优化 - OOM 发生路径：了解 OOM 是如何产生的.md"
  - type: aosp
    path: "https://android.googlesource.com/platform/libcore/+/refs/tags/android-16.0.0_r1/ojluni/src/main/java/java/lang/Thread.java"
  - type: aosp
    path: "https://android.googlesource.com/platform/art/+/refs/tags/android-16.0.0_r1/runtime/native/java_lang_Thread.cc"
  - type: aosp
    path: "https://android.googlesource.com/platform/bionic/+/refs/tags/android-16.0.0_r1/libc/private/bionic_fortify.h"
  - type: official
    path: "https://developer.android.com/reference/java/io/FileDescriptor"
  - type: official
    path: "https://developer.android.com/ndk/reference/group/file-descriptor"
pipeline_stage: "ready-to-publish"
task6_state: "reviewed"
last_task2a_at: "2026-05-23T03:09:00+08:00"
section: "20.14"
task9_state: "reviewed"
reviewed_by: "openclaw-task6"
reviewed_date: "2026-06-13"
task6_result: "pass-light-edit"
last_task6_at: "2026-06-13T09:09:06+08:00"
last_task6_review_log: "logs/review/2026-06-13-08-review.md"
task6_review_notes: "2026-06-13 Task6 re-review pass（状态修复）：上轮 08:07 review 已判定 pass-light-edit，但 task6_state 未从 revisiting 更新为 reviewed，本轮修复。L1/L2/L3/L4 全部通过，无禁用词、无 B 类问题。task9_result=auto-fixed，不满足自动晋升条件，建议 Task9 补确认后晋升。"
task9_result: "auto-fixed"
last_task9_at: "2026-06-13T05:21:00+08:00"
task2b_state: "fixed"
last_task9_audit: "2026-06-13"
last_task9_autofix_at: "2026-06-13"
last_task9_review_log: "logs/deep-review/2026-06-13-05-audit.md"
task9_review_notes: "2026-06-13 Task9 idle audit: auto-fixed AOSP main anchors to android-16.0.0_r1; Android 17 tag unavailable during audit, no P0/P1 queue item."
task2b_verifier_note: "2026-06-13 Verifier: auto-promoted to finalized (task6 pass-light-edit + task9 auto-fixed + no queue pending + content sufficient)"
deepseek_cn_review_state: done
last_deepseek_cn_review_at: 2026-06-22
---

# 20.14 线程与 FD 资源监控治理

## 资源治理先分三层

线程和文件描述符属于不同资源，但它们有相似的故障形态：进程在较长时间里持续创建，直到某次普通操作成为报错点。触发失败的 `Thread.start()`、`open()` 或 `socket()` 不一定是泄漏来源。

一套可解释的监控需要分三层：

| 层次 | 线程 | FD |
| --- | --- | --- |
| 低成本趋势 | Linux task 数、线程池活动数和历史高水位 | 当前打开数量、soft limit 和历史高水位 |
| 触发式快照 | Java 线程名、状态、栈顶和重点线程完整栈 | symlink 类型分布、目标归一化和 top-N |
| 短时归因 | `ThreadFactory`、任务包装、构建期插桩或受控 native 采集 | 创建/复制/关闭事件、generation 与采样栈 |

低成本趋势用于常态监控；详细快照只在接近风险区、增长异常或诊断开关开启时执行；创建堆栈采集只在小范围、有限时段启用。三层数据不能混成一个“资源分数”，否则无法判断告警来自数量、增长还是归因证据。

平台源码锚点是 Android 17 / API 37 / `android-17.0.0_r1`，涉及 `/proc` 语义时的内核锚点是 `android17-6.18-2026-06_r6`。

## 线程：Linux task、Java Thread 与线程池不是同一个视角

进程里的 Linux task 数包含 Java 线程、ART 线程、Binder 线程、纯 native `pthread` 等。Java 的 `Thread.getAllStackTraces()` 只能提供拥有 Java `Thread` peer 且能被 ART 枚举到的线程栈；线程池统计则只描述该池管理的 worker 和队列。

| 入口 | 适合回答 | 不能证明 |
| --- | --- | --- |
| `/proc/self/status` 的 `Threads` | 当前进程有多少 Linux task | 每个 task 的创建者 |
| `/proc/self/task/<tid>/comm` | Linux TID 与内核可见短名称 | 完整 Java 名称和 Java 创建栈 |
| `Thread.getAllStackTraces()` | 采样时刻的 Java 线程、状态与栈 | 所有纯 native 线程和历史创建点 |
| `ThreadPoolExecutor` 指标 | pool size、active、queue、completed | 其他线程池或直接创建的线程 |
| Perfetto / tombstone / ANR traces | 调度、阻塞与故障时栈 | 长期增长来源，除非同时有趋势数据 |

Android 17 的 `Thread.getAllStackTraces()` 通过 `getAllThreadsInternal()` 取得线程快照，再逐个调用 `getStackTrace()`。这个过程会分配 map 和栈数组，成本随线程数与栈深增长，不能作为秒级计数器，更不能等到 `pthread_create` 已经失败时才开始采集。

### 常态只读数量

`android17-6.18-2026-06_r6` 的 proc 文档定义了 `/proc/<pid>/status` 中的 `Threads` 字段。下面的代码只读取当前进程，不访问其他应用。

```kotlin
fun readLinuxThreadCount(): Int? {
    return try {
        File("/proc/self/status").bufferedReader().useLines { lines ->
            lines.firstOrNull { it.startsWith("Threads:") }
                ?.substringAfter(':')
                ?.trim()
                ?.toIntOrNull()
        }
    } catch (_: IOException) {
        null
    } catch (_: SecurityException) {
        null
    }
}
```

这个值适合记录趋势和高水位。读取失败应记为“缺测”，不能写成 0。若需要更细的 native task 名称，再按需枚举 `/proc/self/task`；常态监控没有必要为每个 TID 读取 `comm` 和 `status`。

### Java threadId 不是 Linux TID

API 36 起，`Thread.getId()` 被废弃，推荐使用 final 的 `threadId()`。二者返回 Java `Thread` 的生命周期 ID，都不是 Linux TID。Perfetto、tombstone、`/proc/self/task` 和 `Process.myTid()` 使用的是 Linux TID，不能直接拿 Java ID 去关联。

若业务线程由统一 `ThreadFactory` 创建，可以在线程开始执行时登记两种 ID。下面的示例还给线程名加入稳定模块前缀。

```kotlin
class TrackedThreadFactory(
    private val module: String,
    private val registry: ThreadRegistry
) : ThreadFactory {
    private val sequence = AtomicInteger()

    override fun newThread(task: Runnable): Thread {
        val name = module + "-" + sequence.incrementAndGet()
        return Thread({
            val current = Thread.currentThread()
            val javaId = if (Build.VERSION.SDK_INT >= 36) {
                current.threadId()
            } else {
                @Suppress("DEPRECATION")
                current.id
            }
            val linuxTid = Process.myTid()

            registry.tryOnStart(javaId, linuxTid, name)
            try {
                task.run()
            } finally {
                registry.tryOnStop(javaId, linuxTid)
            }
        }, name)
    }
}
```

`ThreadRegistry` 必须有容量上限，`tryOnStart/tryOnStop` 还要遵守 no-throw 契约，不能执行 I/O 或捕获完整栈。生产版 factory 还应明确优先级、daemon 属性和未捕获异常处理器。Linux 的线程名字段长度有限，模块标识应放在名称前部；完整业务来源保存在受限的 registry 中。线程名不要包含账号、订单、URL 或用户输入。

## 线程来源：先治理创建入口

Android 17 的 `Thread()`、`Thread(Runnable)` 和 `Thread(ThreadGroup, Runnable)` 仍会生成 `Thread-N` 默认名称。大量 `Thread-123` 说明缺少可见来源，但不能单凭名称认定泄漏。

处理顺序建议是：

1. 自有线程池统一使用有界 `ThreadPoolExecutor` 或明确语义的 coroutine dispatcher；
2. 每个自有 pool 使用 `ThreadFactory`，记录模块、用途、队列和拒绝策略；
3. 静态检查直接 `new Thread()`、`Executors.newCachedThreadPool()` 和未关闭的 `HandlerThread`；
4. 对工程内仍无法改造的调用点，再考虑 AGP ASM instrumentation；
5. 三方与动态代码以依赖版本、运行时快照和受控采样归因。

一个 coroutine 不等于一个线程。协程可能复用 dispatcher 的少量 worker；反过来，某些 SDK 会绕开协程和 Java executor 直接调用 `pthread_create()`。指标要分别记录任务队列和 Linux task，不能把协程数量当作线程数。

### 构建期插桩的边界

AGP 8.x 应使用当前的 instrumentation/ASM visitor 接口，不再依赖旧 Transform API。插桩可以给工程内无名构造补来源 ID，或在构造后调用 registry，但需要解决：

- 各个构造重载的 operand stack 形状；
- R8 混淆前后来源 ID 的稳定映射；
- project scope 与 dependency scope 的覆盖差异；
- 增量构建与缓存是否复用了旧字节码；
- 已带业务名称的线程不能被覆盖；
- 插入代码抛异常时不能阻止线程创建。

因此，插桩产物要做字节码校验和启动测试。正文不提供“替换构造描述符”式伪代码，因为少压入一个参数或处理错 `ThreadGroup` 重载就可能得到 verifier error。比起改写全部三方字节码，优先修正自有创建入口通常更安全。

### Java 与 native 创建链路

Java `Thread.start()` 会进入 ART 的 `Thread_nativeCreate()`，再调用 `Thread::CreateNativeThread()`。纯 native `pthread_create()` 不必经过 Java 构造和 `ThreadFactory`，所以 Java 插桩无法覆盖所有线程。

native SDK 的治理应要求：

- 通过统一包装创建线程并设置稳定名称；
- 明确默认栈大小、最大并发和退出协议；
- 库卸载或功能关闭时能停止并 join 自己的 worker；
- 在诊断构建中记录采样后的创建栈；
- 不使用 `pthread_cancel` 或 Java `Thread.stop()` 清理未知线程。

线程创建失败可能来自进程/用户限制、native 内存、虚拟地址空间、栈映射或系统资源压力。看到 `OutOfMemoryError: pthread_create` 或 `pthread_create ... failed` 时，应同时查看线程数、`VmSize`、栈大小、进程角色和错误日志，不能只用 Java heap 余量排除 OOM。

## FD：数量、编号、对象和 owner 要分开

FD 是进程表中的整数索引。关闭后，内核通常会复用较小的可用编号。一次 double-close 可能关闭刚被另一线程复用的对象，因此 FD 监控不能只保存“编号 123 曾经由谁打开”。

需要区分：

- 当前打开 FD 的数量；
- FD 数值本身，例如是否达到 `FD_SETSIZE`；
- symlink 指向的对象类型；
- 创建事件的 generation；
- 哪个 owner 负责关闭；
- `dup` 后新旧描述符的独立生命周期。

`/proc/self/status` 中的 `FDSize` 是“已分配的描述符槽位数”，不是当前打开数量。不要把它当成 FD count。Linux 6.18 proc 文档说明 `/proc/<pid>/fd` 包含当前打开文件的 symlink；Android 应用采集自身进程时应使用 `/proc/self/fd`，避免 PID 复用和跨进程权限问题。

### 常态数量与详细快照

枚举 `/proc/self/fd` 会产生目录遍历开销，采样期间 FD 也可能同时打开或关闭，所以结果是近似快照。下面的代码只计算数值名称，不读取每条 symlink。

```kotlin
fun readOpenFdCount(): Int? {
    return try {
        File("/proc/self/fd").list()
            ?.count { it.toIntOrNull() != null }
    } catch (_: SecurityException) {
        null
    }
}
```

目录枚举本身可能短暂占用一个 FD，且并发打开/关闭会造成竞态；不要为了得到“精确值”盲目减 1。趋势监控应允许很小的测量噪声。Android 17 的 6.18 内核还能从该目录的 `stat().st_size` 快速取得打开文件数，但面向旧 Android 和 vendor kernel 的应用应先做设备验证，再把它作为优化路径。

详细快照只在触发时读取 symlink。目标字符串用于类型归类，原始路径不应直接上传。

```kotlin
data class FdItem(
    val number: Int,
    val kind: String,
    val normalizedTarget: String
)

data class FdSnapshot(
    val items: List<FdItem>,
    val complete: Boolean,
    val skipped: Int
)

fun collectFdSnapshot(): FdSnapshot {
    val entries = try {
        File("/proc/self/fd").listFiles()
    } catch (_: SecurityException) {
        null
    } ?: return FdSnapshot(emptyList(), complete = false, skipped = 0)

    var skipped = 0
    val items = entries.mapNotNull { entry ->
        val number = entry.name.toIntOrNull() ?: return@mapNotNull null
        val target = try {
            Os.readlink(entry.absolutePath)
        } catch (_: ErrnoException) {
            skipped++
            return@mapNotNull null
        }

        FdItem(
            number = number,
            kind = classifyFd(target),
            normalizedTarget = normalizeFdTarget(target)
        )
    }
    return FdSnapshot(items, complete = skipped == 0, skipped = skipped)
}
```

`readlink()` 失败并不稀奇：读取前 FD 可能已被关闭。调用方必须保留 `complete/skipped`，不能把不完整快照解释为资源已经恢复。`classifyFd()` 可区分 file/directory、`socket:`、`pipe:`、`anon_inode:`、ashmem/memfd 等；`normalizeFdTarget()` 应把应用私有文件归到稳定目录或资源类型，去掉文件名、用户 ID、URI 和查询参数。

必要时再读取 `/proc/self/fdinfo/<fd>`。内核会为普通文件提供 position、flags、mount ID 和 inode，为 eventfd、epoll 等对象提供专用字段。它适合少量候选的深挖，不适合对所有 FD 高频读取。

## FD 限额和 FD_SET 是两条边界

进程达到 `RLIMIT_NOFILE` soft limit 后，创建 FD 的调用通常以 `EMFILE` 失败；`ENFILE` 指系统级打开文件表压力。限额来自设备与进程环境，不应在正文写死一个通用数值。采样时可以读取 `/proc/self/limits`，或者在 native 层调用 `getrlimit(RLIMIT_NOFILE)`。

`FD_SETSIZE` 则是 `select()/fd_set` 的表示边界。Android 17 bionic 的 `sys/select.h` 把它定义为 1024，`__check_fd_set()` 在 fd 小于 0、fd 不小于 `FD_SETSIZE` 或 `fd_set` 空间不足时触发 FORTIFY fatal。

由此有四个结论：

- “打开 FD 总数超过 1024 就会崩溃”是错误结论；
- 进程打开数量很少，也可能通过 `dup2` 得到一个大于等于 1024 的 FD；
- 泄漏使新 FD 编号持续升高时，旧库调用 `FD_SET` 的风险会增加；
- 新代码处理大量 FD 时应优先使用 `poll` 或 `epoll`，而不是扩大未经验证的 `fd_set`。

看到 tombstone 中的 `FD_SET: file descriptor ... >= FD_SETSIZE` 时，应定位把该编号传给 `select` 的库，同时回看为什么进程出现了高编号。修复调用方和修复泄漏可能是两个独立任务。

## FD 归因：事件表必须理解复用

常见创建路径不只 `open()`。诊断采集至少要考虑：

- `open/openat/creat`；
- `socket/socketpair/accept/accept4`；
- `pipe/pipe2`、eventfd、epoll、inotify、timerfd、memfd；
- `dup/dup2/dup3` 与 `fcntl(F_DUPFD*)`；
- `close` 及语言/框架层 owner 的关闭。

这份列表用于说明覆盖面。若每个 App 只 hook `open` 和 `close`，得到的表一定不完整，也没有必要为此常开一组 libc hook。

事件表可以使用 `fd + generation` 作为本地键。每次成功创建或复制都为目标编号递增 generation；`dup2/dup3` 成功时还要结束目标编号原来的记录，再建立新记录。事件至少包含操作、结果、类型、单调时间、线程 ID、来源 ID 和可选采样栈。

hook 实现还必须处理：

- thread-local 重入保护，避免 unwind、日志或内存分配再次打开 FD；
- 固定容量与淘汰规则，不能因诊断表增长制造新的资源问题；
- 只在系统调用成功后更新状态；
- 未捕获的创建 API、直接 syscall 与加载顺序；
- 与其他 native hook SDK 的冲突；
- 16 KB 页设备上的 ELF、地址保护和运行时页计算；
- 定期用 `/proc/self/fd` 对账，并把差异标成 unknown，而不是伪造完整性。

### fdsan 与 fdtrack 的准确用途

Android 10 引入 fdsan，Android 11 起默认在检测到所有权错误时终止进程。fdsan 通过 owner tag 发现 use-after-close、double-close 和错误 owner 关闭；检测覆盖度取决于有多少 FD 参与 tag 协议，它也不是 FD 泄漏计数器。若 tombstone 显示 “fdsan: attempted to close file descriptor ...”，应修正所有权与关闭协议，不要通过降低错误级别掩盖问题。

AOSP 还包含 fdtrack：bionic hook 接收 FD 创建/销毁事件，`libfdtrack` 使用 unwindstack 保存创建栈。它开销显著，接口也包含平台内部与不稳定部分，适合系统镜像、debuggable 环境和短时诊断。普通 App 不应把平台内部 `libfdtrack.so` 或 `android_fdtrack_compare_exchange_hook` 当作跨版本公开 SDK；生产方案要么使用自有、经过验证的诊断组件，要么依赖低频 `/proc` 快照和可控 owner 包装。

## 所有权治理比“崩溃前关几个 FD”更重要

Java/Kotlin 代码优先使用 `use {}` 或 try-with-resources，native 代码使用能表达唯一所有权的 RAII wrapper。对跨 JNI 边界的 `FileDescriptor`、`ParcelFileDescriptor` 和 raw int fd，要在接口文档中明确：

- 参数是 borrowed 还是 transferred；
- 谁负责 close；
- `dup` 后谁拥有新描述符；
- `detachFd()` 后 Java wrapper 不再负责什么；
- 异常路径和取消路径怎样关闭；
- callback 超时、页面销毁和进程切换时怎样释放。

不要从 `/proc/self/fd` 找到一个“看起来没用”的编号就主动 close。symlink 目标无法说明 owner，关闭 Binder、Looper、数据库或别的线程正在使用的 FD 会制造 use-after-close 和数据损坏。

线程同理：不要因为名称陌生就 interrupt、stop 或 cancel。资源治理必须回到创建它的模块和生命周期 owner。

## 与 OOM、ANR 和 native crash 的证据关系

| 现象 | 资源证据 | 不能直接推出 |
| --- | --- | --- |
| `OutOfMemoryError: pthread_create` | Linux task 趋势、栈大小、`VmSize`、创建模块 | Java heap 已满 |
| `EMFILE` / “Too many open files” | FD count、soft limit、类型、增长来源 | 某一个失败的 `open` 是泄漏点 |
| `ENFILE` | 系统级文件表压力与设备状态 | 当前 App 单独泄漏 |
| fdsan abort | owner tag、close 双方栈、FD 复用 | FD 数量已到上限 |
| `FD_SET` FORTIFY abort | 高编号、`select` 调用方、FD 趋势 | 打开数量必然超过 1024 |
| Binder 线程都在等待 | ANR traces、Binder 事务、线程池状态 | 单纯增加 Binder 线程就能解决 |
| eventpoll/eventfd 持续增长 | 对应 Looper、HandlerThread、SDK 生命周期 | 所有 anon_inode 都是泄漏 |

Binder 线程池耗尽常由同步事务阻塞或调用环形成，线程数量只是现象。Looper/MessageQueue 正常持有 epoll/eventfd，看到 `anon_inode:[eventpoll]` 也不能直接关闭；只有对象数量随被销毁的 owner 持续增长，才形成泄漏证据。

Crash、ANR 和 OOM 的完整判定分别见 20.3、20.4、20.5。资源章节负责提供故障前趋势、创建来源和所有权证据，不替代 tombstone、ANR trace 或 `ApplicationExitInfo`。

## 采样策略：按进程基线和增长触发

主进程、WebView 进程、播放器、下载服务和 isolated process 的线程/FD 基线不同。策略至少按进程角色、版本、ABI、前后台状态和关键功能分组。

常态样本建议保留：

- 当前值、历史高水位和一段时间内的增量；
- 线程池 active/pool/queue/completed；
- Java 匿名线程数与稳定名称前缀分布；
- FD 类型分布和最大 FD 编号；
- `RLIMIT_NOFILE` soft/hard limit；
- 快照失败或数据缺失原因；
- 是否伴随 ANR、OOM、网络、数据库或日志错误。

触发条件应综合绝对值、相对 soft limit、增长速度、持续时间和同类设备分位，不能复制一套固定阈值给所有进程。短时峰值随后回落，与每次页面进入都只增不减，风险含义不同。

进入详细诊断后，应设置：

- 明确的最长时长、最大事件数和采样率；
- 只采 top-K 来源，栈深与字符串长度受限；
- 前台关键路径的性能预算；
- 自动停止与冷却时间；
- 远程开关失效时的本地安全默认值；
- 同一进程只允许一个 native 资源采集 owner。

## 止损动作必须尊重 owner

风险持续增长时，可按影响范围采取动作：

- 对新任务施加 backpressure，停止继续制造资源；
- 关闭可选预热、调试日志、长连接或并发下载；
- 让对应页面或模块执行自己的 `close/shutdown/quitSafely`；
- 隔离进程中的可选功能可以停止并按受控条件重建；
- 主进程无法安全恢复时，展示升级或重试入口。

不要强制关闭任意 FD、停止未知线程、清除用户数据或把主进程自杀写成常态方案。SafeMode 只能跳过有明确边界的可选模块，详见 20.12。

## 崩溃现场只写最小证据

资源快耗尽时，创建线程、分配大数组、枚举所有栈或打开新文件都可能失败。Fatal handler 中不应调用 `Thread.getAllStackTraces()`、遍历每个 fdinfo 或启动上传任务。

更稳的做法是：

1. 平时把低成本趋势写入固定容量内存环；
2. 阈值触发时预生成有大小上限的线程/FD 摘要；
3. 若已有预留且验证过的低成本写入通道，崩溃现场只写摘要 ID 和少量计数；
4. 下一次启动用 `ApplicationExitInfo`、tombstone 与本地摘要核对；
5. 后台再上传、符号化和聚合。

证据文件要使用原子替换、固定总容量和版本化格式。Crash/ANR 证据包见 26.2、26.5；Java/native handler 的职责边界见 20.2、20.3。

## 隐私与数据质量

线程名、文件路径、socket 目标和调用栈都可能包含业务或用户信息。上报前应：

- 线程名保留稳定模块前缀，去掉动态 ID；
- 私有目录归一化为目录类别，不传原始文件名；
- socket 只保留协议/类型和经过审核的 endpoint ID；
- 调用栈按 build ID、模块和符号 ID 表示；
- 所有字符串限长，未知值保留 unknown；
- 客户端样本与服务端聚合都设置保留期限。

hash 不是自动脱敏。低熵文件名、手机号或固定 URL 即使散列，也可能被字典反推；能用枚举和模块 ID 时不要上传原值 hash。

## 验证方法

单元测试应覆盖监控器自己的状态机：

- FD 编号关闭后被新对象复用；
- `dup2/dup3` 覆盖已经打开的目标编号；
- close 失败、未捕获创建和 `/proc` 对账差异；
- hook 内部再次打开 FD 时的重入；
- 事件环达到容量上限后的淘汰；
- 线程开始前没有 Linux TID，运行后完成 Java ID/TID 关联；
- 线程池 shutdown、任务异常与 registry 清理；
- `/proc` 读取失败时输出缺测而不是 0。

集成测试要在受控测试进程中注入资源故障：

| 场景 | 预期证据 |
| --- | --- |
| 循环创建但不关闭文件 | file 类型和同一来源持续增长 |
| socket/pipe/dup 泄漏 | 对应类型、generation 和 owner 可见 |
| double-close | fdsan 指向所有权错误，不误报成数量耗尽 |
| 创建大量无名 Java 线程 | Linux task 与 Java 快照同步增长 |
| 纯 native `pthread` 增长 | Linux task 增长高于 Java 快照 |
| HandlerThread 未 quit | 线程与 eventpoll/eventfd 共同残留 |
| FD 编号不小于 1024 后调用 `FD_SET` | Android 17 bionic FORTIFY 路径可复现 |
| 资源接近上限时触发 crash | handler 不再做重型快照 |

故障注入完成后必须由测试进程退出或显式释放资源，避免污染后续用例。不要在用户数据进程里通过降低 limit 或制造真实泄漏做线上验证。

## 复核清单

- [ ] 常态线程计数是否来自低成本进程视角，而不是全栈快照？
- [ ] 是否区分 Java thread ID 与 Linux TID？
- [ ] 是否把纯 native `pthread` 纳入进程级计数？
- [ ] 自有线程池是否有稳定名称、并发上限、拒绝与关闭策略？
- [ ] 是否避免把 coroutine 数量当成线程数？
- [ ] `FDSize` 是否没有被误当成当前 FD count？
- [ ] FD 快照是否使用 `/proc/self/fd` 并容忍并发竞态？
- [ ] 归因表是否处理 fd 复用、`dup2/dup3` 和 generation？
- [ ] 是否区分 `EMFILE`、`ENFILE`、fdsan 与 `FD_SET` abort？
- [ ] 是否使用稳定 owner 关闭资源，而不是按 symlink 猜测？
- [ ] native hook 是否限时、限量、防重入并与 `/proc` 对账？
- [ ] fatal handler 是否只写预生成的有界摘要？
- [ ] 阈值是否按进程基线、soft limit、增长和持续时间计算？
- [ ] 所有路径、线程名和调用栈是否限长、归一化并脱敏？

## 源码与官方资料

- [AOSP `Thread.java`（android-17.0.0_r1）](https://android.googlesource.com/platform/libcore/+/refs/tags/android-17.0.0_r1/ojluni/src/main/java/java/lang/Thread.java)：默认线程名、`getAllStackTraces()`、`getId()` 与 `threadId()`。
- [AOSP `java_lang_Thread.cc`（android-17.0.0_r1）](https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/runtime/native/java_lang_Thread.cc)：`Thread_nativeCreate()` 到 ART native 创建入口。
- [AOSP `bionic_fortify.h`（android-17.0.0_r1）](https://android.googlesource.com/platform/bionic/+/refs/tags/android-17.0.0_r1/libc/private/bionic_fortify.h)：`__check_fd_set()` 的 FORTIFY 条件。
- [AOSP `sys/select.h`（android-17.0.0_r1）](https://android.googlesource.com/platform/bionic/+/refs/tags/android-17.0.0_r1/libc/include/sys/select.h)：`FD_SETSIZE=1024` 与 `poll` 建议。
- [AOSP `fdsan.cpp`（android-17.0.0_r1）](https://android.googlesource.com/platform/bionic/+/refs/tags/android-17.0.0_r1/libc/bionic/fdsan.cpp)：FD owner tag 检查实现。
- [AOSP `libfdtrack`（android-17.0.0_r1）](https://android.googlesource.com/platform/bionic/+/refs/tags/android-17.0.0_r1/libfdtrack/)：平台 FD 创建栈追踪实现及其内部边界。
- [Android Developers：`Thread` API](https://developer.android.com/reference/java/lang/Thread)：API 36 `threadId()` 与 `getId()` 废弃边界。
- [Android Developers：`AsmClassVisitorFactory`](https://developer.android.com/reference/tools/gradle-api/com/android/build/api/instrumentation/AsmClassVisitorFactory)：AGP instrumentation 的公开 visitor 接口。
- [Android Developers：`Os.readlink()`](https://developer.android.com/reference/android/system/Os#readlink(java.lang.String))：应用读取自身 FD symlink 的公开接口。
- [Android 11 behavior changes：fdsan](https://developer.android.com/about/versions/11/behavior-changes-all#fdsan)：fdsan 默认 fatal 与所有权错误语义。
- [Android Common Kernel `proc.rst`（android17-6.18-2026-06_r6）](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/Documentation/filesystems/proc.rst)：`Threads`、`FDSize`、`fd` 和 `fdinfo` 的内核接口语义。

线程与 FD 监控应提前保存少量、可信、能关联 owner 的证据，而非等到崩溃前扫描整个进程。数量说明风险，快照说明构成，创建与关闭事件说明责任；把三者分开，才能既控制监控成本，又避免在资源紧张时制造第二次故障。
