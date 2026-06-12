---
title: "线程与 FD 资源监控治理"
chapter: "20"
status: "ready-for-review"
drafted_date: "2026-05-23"
applicable_versions: "Android 8 (API 26) - Android 17 (API 37)"
tags: [stability, thread, fd, oom, observability]
related_chapters: ["20.5", "20.7", "26.2", "26.5", "14.13"]
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
pipeline_stage: "task6_pending"
task6_state: "revisiting"
last_task2a_at: "2026-05-23T03:09:00+08:00"
section: "20.14"
task9_state: "reviewed"
reviewed_by: "openclaw-task6"
reviewed_date: "2026-05-23"
task6_result: "pass-light-edit"
last_task6_at: "2026-05-23T04:05:00+08:00"
last_task6_review_log: "logs/review/2026-05-23-04-review.md"
task6_review_notes: "2026-05-23 Task6 first review: pass-light-edit。L1/L2 小修 2 处（frontmatter 补 section/chapter，outline 禁用词替换），无回炉项；进入 Task9 技术审查。"
task9_result: "auto-fixed"
last_task9_at: "2026-06-13T05:21:00+08:00"
task2b_state: "fixed"
last_task9_audit: "2026-06-13"
last_task9_autofix_at: "2026-06-13"
last_task9_review_log: "logs/deep-review/2026-06-13-05-audit.md"
task9_review_notes: "2026-06-13 Task9 idle audit: auto-fixed AOSP main anchors to android-16.0.0_r1; Android 17 tag unavailable during audit, no P0/P1 queue item."
---

# 20.14 线程与 FD 资源监控治理

<!-- outline-start -->
## 要点

### 🔹 线程与 FD 为什么要放在同一套资源治理里
线程数失控、FD 泄漏、虚拟地址空间不足和 OOM / Native Crash 常常在同一组稳定性问题里出现。本节从「资源数量 → 创建来源 → 关闭/回收 → 崩溃补偿」四层建立治理入口，避免只在崩溃栈上找最后一次触发点。

### 🔹 线程快照：数量、名称、状态与调用栈
覆盖 `Thread.getAllStackTraces()`、线程名规范、线程池命名策略、匿名线程识别和采样频率边界。重点说明快照适合回答「当前有哪些线程」，不适合单独回答「是谁创建了线程」。[结构参考: Clippings/Android 应用稳定性剖析与优化 - 线程监控：如何解决“匿名”线程？.md]

### 🔹 匿名线程归因：字节码插桩与运行时兜底
整理无参 `Thread()` / `Thread(Runnable)` 构造的归因方案：编译期 ASM 改写、统一 ThreadFactory、运行时监控三种路径。需要区分可控业务代码、三方库代码、动态加载代码的覆盖边界。[结构参考: Clippings/Android 应用稳定性剖析与优化 - 线程监控：如何解决“匿名”线程？.md]

### 🔹 FD 快照：`/proc/$pid/fd`、`Os.readlink()` 与类型聚合
覆盖普通文件、socket、pipe、anon_inode、ashmem/memfd、eventfd/epoll 等 FD 类型的线上采集字段。重点说明采集要保留数量、目标路径、进程、线程、采样时间和 top-N 聚合结果。[结构参考: Clippings/Android 应用稳定性剖析与优化 - 实现 FD 监控：文件描述符（FD）超限怎么办？.md]

### 🔹 FD 创建归因：open/pipe/socket/dup/close 的 hook 边界
整理 FD 创建函数监控的最小集合、堆栈采样策略、性能开销和安全边界。hook 方案只作为灰度诊断能力，常态监控优先使用低频快照和阈值触发。[结构参考: Clippings/Android 应用稳定性剖析与优化 - 实现 FD 监控：文件描述符（FD）超限怎么办？.md]

### 🔹 与 OOM、ANR、Native Crash 的关联判定
把线程创建失败、FD 超限、Looper/epoll 相关 FD、Binder 线程池耗尽、日志 mmap 文件泄漏放到同一张判定表。结论要回连 20.5 OOM 治理、20.4 ANR 治理和 20.3 Native Crash 分析，不重复展开底层机制。[结构参考: Clippings/Android 应用稳定性剖析与优化 - OOM 发生路径：了解 OOM 是如何产生的.md]

### 🔹 线上治理策略：阈值、分位值、灰度和止血动作
给出线程数、FD 数、增长斜率、重复路径、创建堆栈聚类的指标设计。止血动作只讨论降级、限流、关闭非关键模块、重启子进程，不把强杀进程写成默认治理手段。

## 扩展

### 🔸 与 20.7 异常处理架构的边界
20.7 负责异常捕获和恢复策略，本节只负责资源监控与归因数据。后续加工时用「详见 20.7 节」交叉引用，不重复写异常框架设计。

### 🔸 与 26.2 / 26.5 线上证据包的衔接
本节产出的线程快照、FD 快照、FD 创建堆栈需要进入 crash/ANR 证据包，作为 ApplicationExitInfo、tombstone、traces.txt 的补充材料。

### 🔸 待验证：Android 16/17 bionic fortify 与 FD_SETSIZE 触发路径
需要复核 `__FD_SET_chk`、`FD_SETSIZE`、厂商 libc 差异和目标 SDK 行为边界，避免把老设备现象写成所有 Android 版本的通用结论。

### 🔸 待验证：字节码插桩与现代 AGP/ASM Transform 接入方式
需要补齐 AGP 8.x 插件接入方式、Transform API 退场后的替代路径，以及 R8/混淆对线程归因类名的影响。

<!-- outline-end -->

## 资源问题为什么要一起看

线程数和 FD 数不是同一种资源，但线上排查时经常同时出现。线程创建会消耗 Java 对象、native thread、栈空间和调度资源；FD 泄漏会让文件、socket、pipe、epoll、eventfd 等对象持续留在进程里。两类问题积累到阈值后，崩溃现场常常只剩最后一次 `Thread.start()`、`open()`、`socket()` 或 `FD_SET()` 调用，不能直接说明来源。

更稳的排查方式是把资源分成四层：数量、类型、创建来源、关闭/回收。数量回答“现在有多少”；类型回答“主要是哪一类”；创建来源回答“谁在持续制造”；关闭/回收回答“为什么没有释放”。线程和 FD 都按这四层采集，Crash、ANR、OOM 证据包里才有足够信息做归因。

| 资源 | 数量入口 | 类型入口 | 创建归因 | 常见后果 |
|------|----------|----------|----------|----------|
| 线程 | `Thread.getAllStackTraces()`、线程池统计、native 线程采样 | 名称、状态、线程组、栈顶模块 | `ThreadFactory`、字节码插桩、pthread 创建监控 | 线程创建失败、调度拥塞、Binder 线程池耗尽、ANR |
| FD | `/proc/$pid/fd`、`/proc/$pid/limits`、端侧计数器 | 普通文件、socket、pipe、anon_inode、ashmem / memfd | `open` / `socket` / `pipe` / `dup` / `close` 监控 | `EMFILE`、`FD_SET` FORTIFY abort、日志/网络/数据库异常 |

[结构参考: Clippings/Android 应用稳定性剖析与优化 - 线程监控：如何解决“匿名”线程？.md]
[结构参考: Clippings/Android 应用稳定性剖析与优化 - 实现 FD 监控：文件描述符（FD）超限怎么办？.md]

## 线程快照：先拿到“当前有哪些线程”

`Thread.getAllStackTraces()` 返回所有存活线程到栈数组的映射。AOSP `java.lang.Thread` 的 Android 实现会先从 `ThreadGroup.systemThreadGroup.activeCount()` 估算线程数，再枚举系统线程组并逐个调用 `getStackTrace()`。它适合低频采样，适合在资源阈值触发、Crash 前置采样或线上诊断开关打开时执行；不适合在高频路径里持续运行。

[已验证: AOSP android-16.0.0_r1, libcore/ojluni/src/main/java/java/lang/Thread.java, `Thread.getAllStackTraces()`]
[已验证: 官方文档, developer.android.com/reference/java/lang/Thread#getAllStackTraces()]

这段示意代码只表达采集字段。线上实现应当把调用频率、线程数阈值和上传采样率放到远程配置里。

```kotlin
// 示意代码：线程快照采集，只保留诊断字段。
data class ThreadSnapshotItem(
    val name: String,
    val id: Long,
    val state: Thread.State,
    val topFrame: String?,
    val stackDepth: Int
)

fun collectThreadSnapshot(): List<ThreadSnapshotItem> {
    return Thread.getAllStackTraces().map { (thread, stack) ->
        ThreadSnapshotItem(
            name = thread.name ?: "<unnamed>",
            id = thread.id,
            state = thread.state,
            topFrame = stack.firstOrNull()?.toString(),
            stackDepth = stack.size
        )
    }
}
```

这段采集能回答三个问题：线程总数是否异常、异常线程集中在哪些名字、栈顶是否集中在同一模块。Android API 36 起 `Thread.getId()` 已标记废弃，官方建议使用 `threadId()`；兼容旧系统时可以继续保留 `id` 字段，但上报协议要预留新字段，避免后续迁移破坏聚合口径。[已验证: 官方文档, developer.android.com/reference/java/lang/Thread#getId()]

线程快照的边界也要写清：它只能描述采样时刻的存活线程。短生命周期线程可能已经结束，创建者信息也不会自动出现在被创建线程的栈里。看到一批 `Thread-12`、`Thread-13`、`Thread-14` 时，快照只能说明命名失控和数量增长，不能单独证明创建点。

## 匿名线程归因：命名规范、ThreadFactory、字节码插桩

`new Thread()` 和 `new Thread(Runnable)` 在 AOSP `Thread.java` 中会生成 `Thread-` 加递增数字的默认名称；带 `String name` 的构造函数才会写入业务可识别的名称。匿名线程治理的入口应前移到创建阶段，给线程留下来源，避免崩溃后只能靠线程名猜测模块。

[已验证: AOSP android-16.0.0_r1, libcore/ojluni/src/main/java/java/lang/Thread.java, `Thread()` / `Thread(Runnable)` / `Thread(String name)`]

推荐按可控程度分三层处理：

| 场景 | 方案 | 适用边界 |
|------|------|----------|
| 业务线程池 | 统一 `ThreadFactory`，名称包含模块、用途、序号 | 成本最低，覆盖自有线程池 |
| 业务代码直接 `new Thread()` | 静态检查 + 字节码插桩，把无名构造改成带名构造 | 适合工程内代码，需要配合 AGP 8.x instrumentation API |
| 三方库或动态加载代码 | 运行时快照 + 堆栈聚类 + SDK 维度归因 | 覆盖不完整，适合诊断和灰度止血 |

字节码插桩的思路来自参考书：无参构造和带名构造的差异集中在构造函数签名和调用前多压入的字符串参数。工程实现不要只替换 `Thread()`，还要覆盖 `Thread(Runnable)`、`Thread(ThreadGroup, Runnable)` 等常见重载，并跳过已经带业务名的调用。

[结构参考: Clippings/Android 应用稳定性剖析与优化 - ASM 与字节码插桩：改写字节码的“神器”.md]

这段伪代码表达插桩规则，重点是“只补无业务名构造”。

```kotlin
// 伪代码：ASM visitor 规则，不代表可直接运行。
fun shouldRewriteThreadConstructor(owner: String, name: String, desc: String): Boolean {
    if (owner != "java/lang/Thread" || name != "<init>") return false

    val constructorsWithoutBusinessName = setOf(
        "()V",
        "(Ljava/lang/Runnable;)V",
        "(Ljava/lang/ThreadGroup;Ljava/lang/Runnable;)V"
    )
    return desc in constructorsWithoutBusinessName
}

fun buildThreadName(className: String, methodName: String): String {
    return "${className.substringAfterLast('/')}.${methodName}"
}
```

插桩落到生产前，要处理四个边界：R8 混淆后类名是否还能定位模块、三方库是否允许改写、增量编译缓存是否污染、动态加载代码是否绕过构建期处理。现代 AGP 中旧 Transform API 已退场，新插件应走 Android Gradle Plugin instrumentation / ASM visitor 能力；这部分需要按项目 AGP 版本验证接入方式。[待验证: AGP 8.x instrumentation API 在目标工程中的接入细节]

native 线程也要单独处理。Java `Thread.start()` 在 ART 里会进入 `Thread_nativeCreate()`，随后调用 `Thread::CreateNativeThread()`；纯 native 侧的 `pthread_create()` 不一定经过 Java 命名体系。对 native SDK，可通过统一线程创建封装、SDK 接入规范或灰度 hook 记录创建堆栈。[已验证: AOSP android-16.0.0_r1, art/runtime/native/java_lang_Thread.cc, `Thread_nativeCreate()`]

## FD 快照：从 `/proc/$pid/fd` 建立类型分布

FD 快照的入口是 `/proc/$pid/fd`。每个条目是一个符号链接，`Os.readlink()` 可以读取它指向的目标。目标字符串能把 FD 粗分成普通文件、socket、pipe、anon_inode、ashmem / memfd、eventfd、epoll 等类型。数量异常时，先看类型分布，再看 top-N 路径或对象。

[已验证: 官方文档, developer.android.com/reference/android/system/Os#readlink(java.lang.String)]

这段代码用于说明 FD 快照字段。采集时要控制频率，避免在 FD 已经紧张的进程里再制造额外压力。

```kotlin
// 示意代码：FD 快照采集，生产环境需要采样率和异常保护。
data class FdSnapshotItem(
    val fd: Int,
    val target: String,
    val kind: String
)

fun collectFdSnapshot(pid: Int = android.os.Process.myPid()): List<FdSnapshotItem> {
    val dir = java.io.File("/proc/$pid/fd")
    val files = dir.listFiles() ?: return emptyList()

    return files.mapNotNull { file ->
        val fd = file.name.toIntOrNull() ?: return@mapNotNull null
        val target = try {
            android.system.Os.readlink(file.absolutePath)
        } catch (error: android.system.ErrnoException) {
            return@mapNotNull null
        }
        FdSnapshotItem(fd = fd, target = target, kind = classifyFdTarget(target))
    }
}

fun classifyFdTarget(target: String): String = when {
    target.startsWith("socket:") -> "socket"
    target.startsWith("pipe:") -> "pipe"
    target.startsWith("anon_inode:") -> "anon_inode"
    target.contains("ashmem") || target.contains("memfd:") -> "shared_memory"
    else -> "file_or_directory"
}
```

FD 快照至少保留六类字段：采样时间、进程名、FD 总数、类型分布、top-N 目标、最近一次阈值变化。只上传 FD 总数价值有限；只上传完整路径又容易带出隐私数据。路径要做脱敏和归一化，例如把用户 ID、文件名哈希、缓存目录前缀拆开处理。

| 类型 | 典型目标 | 排查方向 |
|------|----------|----------|
| 普通文件 / 目录 | `/data/data/<pkg>/files/...`、日志目录、缓存目录 | 文件流关闭、日志滚动、数据库游标 |
| socket | `socket:[12345]` | 网络连接池、WebSocket、DNS、IPC socket |
| pipe | `pipe:[67890]` | 子进程通信、日志管道、shell 命令执行 |
| anon_inode | `anon_inode:[eventpoll]`、`anon_inode:[eventfd]` | Looper、epoll、InputChannel、协程/线程调度辅助对象 |
| ashmem / memfd | `memfd:...`、`/dev/ashmem/...` | 图像、共享内存、跨进程 buffer |

[结构参考: Clippings/Android 应用稳定性剖析与优化 - 实现 FD 监控：文件描述符（FD）超限怎么办？.md]

## FD 创建归因：常态快照优先，hook 只做灰度诊断

FD 泄漏要定位创建点，光靠 `/proc/$pid/fd` 不够。可监控的函数包括 `open` / `openat`、`socket` / `accept`、`pipe` / `pipe2`、`dup` / `dup2` / `dup3`、`eventfd`、`epoll_create` / `epoll_create1`、`close`。记录创建堆栈时，`close` 同样要监控，否则本地表只会增长，无法区分“还没关闭”和“已经关闭但表没删”。

| 函数族 | 记录字段 | 风险 |
|--------|----------|------|
| `open` / `openat` | fd、路径摘要、flags、调用栈 | 路径含隐私，需脱敏 |
| `socket` / `accept` | fd、domain、type、protocol、调用栈 | 高频网络场景开销高 |
| `pipe` / `eventfd` / `epoll_create` | fd、对象类型、调用栈 | Looper / 调度组件会产生正常基线 |
| `dup` 系列 | 新旧 fd、调用栈 | 只盯 open 会漏掉复制后的引用 |
| `close` | fd、关闭栈、关闭结果 | hook 失败会让归因表失真 |

PLT / GOT hook 能把这些函数接入端侧诊断，但它不应成为默认常开能力。理由有三点：一是所有线程都可能打开 FD，本地归因表要处理并发；二是采集 backtrace 有成本，高频 socket 或日志写入会放大开销；三是 hook 本身受系统版本、加载顺序、SDK 冲突和 16 KB page size 适配影响。14.13 节已经讲过 hook 基础设施边界，这里只把它作为 FD 诊断手段引用。

[结构参考: Clippings/Android 应用稳定性剖析与优化 - 实现 FD 监控：文件描述符（FD）超限怎么办？.md]
[交叉引用: 详见 14.13 节]

灰度诊断的推荐策略：常态只做低频 FD 快照；达到阈值后对命中设备打开短时 hook；hook 只记录 top-K 创建堆栈和增长最快的 FD 类型；诊断窗口结束后自动关闭。这样能把成本控制在问题设备上，也能减少与其他 native hook SDK 的冲突。

Android NDK 提供 `AFileDescriptor_create()`、`AFileDescriptor_getFd()`、`AFileDescriptor_setFd()` 这组 JNI 辅助函数，API 31 起可在 native 层创建和读写 `java.io.FileDescriptor` 对应的 Unix fd。混合栈 SDK 排查 FD 问题时，需要把 Java `FileDescriptor` 和 native int fd 放到同一套编号体系里。[已验证: 官方文档, developer.android.com/ndk/reference/group/file-descriptor]

## 与 OOM、ANR、Native Crash 的关联判定

线程和 FD 问题不要直接按崩溃类型归类。更可靠的做法是看资源曲线、错误码、系统记录和业务上下文是否互相支持。

| 现象 | 可能资源原因 | 证据 | 处理入口 |
|------|--------------|------|----------|
| `OutOfMemoryError: pthread_create` 或线程创建失败 | 线程数过高、虚拟地址空间不足、栈空间不足 | 线程数曲线、native 线程栈大小、`Thread::CreateNativeThread()` 附近错误 | 详见 20.5 节，本节补线程来源 |
| `java.io.FileNotFoundException: Too many open files` / `EMFILE` | 进程 FD 表耗尽 | FD 数量、top-N 目标、创建堆栈、`/proc/$pid/limits` | 本节补 FD 快照和创建归因 |
| `FORTIFY: FD_SET: file descriptor >= FD_SETSIZE` | 代码把过大的 fd 放进 `fd_set` | tombstone、bionic `__check_fd_set()`、触发库 | Native Crash 分析详见 20.3 节 |
| ANR 伴随 Binder 线程池耗尽 | 线程池等待、同步调用堆积 | `traces.txt`、Binder 线程状态、业务请求量 | 20.4 / 26.5 处理 ANR 证据包 |
| 日志、图片、数据库异常集中出现 | 文件或 mmap 相关 FD 泄漏 | FD 类型分布、路径聚合、模块版本 | 本节定位泄漏来源，20.7 处理降级 |

bionic `__check_fd_set()` 会在 fd 小于 0、fd 大于等于 `FD_SETSIZE`、`fd_set` 空间不足时触发 FORTIFY fatal。这里的 `FD_SETSIZE` 是 `select` / `fd_set` 使用边界，不等同于进程可打开 FD 的总上限。把它写成“FD 总数超过 1024 就必崩”会误导排查；准确说法是：某个 fd 值进入 `FD_SET` 时超出 `fd_set` 可表达范围，bionic fortify 触发 abort。[已验证: AOSP android-16.0.0_r1, bionic/libc/private/bionic_fortify.h, `__check_fd_set()`]

[结构参考: Clippings/Android 应用稳定性剖析与优化 - OOM 发生路径：了解 OOM 是如何产生的.md]
[交叉引用: 详见 20.3、20.4、20.5、20.7、26.2、26.5 节]

## 线上治理策略：阈值、分位值、灰度和止血

线程和 FD 的治理不要只设一个固定阈值。不同业务、设备、进程角色的基线差异很大：主进程、播放器进程、WebView 进程、下载进程天然资源模型不同。指标应当按进程、版本、设备档位、前后台状态拆开看。

推荐保留这些指标：

- 线程总数：记录 P50 / P90 / P99、增长斜率、匿名线程占比、top-N 线程名前缀。
- FD 总数：记录 P50 / P90 / P99、增长斜率、类型分布、top-N 目标摘要。
- 创建归因：记录 top-K 创建堆栈、模块名、版本、灰度实验分组。
- 关闭质量：记录打开后长时间未关闭的 fd、线程池 shutdown 缺失、重复创建但未复用的对象。
- 事件关联：记录 Crash、ANR、OOM、网络失败、日志写入失败前后的资源曲线。

止血动作要按影响面分级。L1 是关闭高频采集、降低日志级别、缩短网络连接保活；L2 是关闭可选模块、暂停图片预加载、限制并发下载；L3 是进入 SafeMode、重启独立子进程或引导用户升级。主进程强杀只能作为末级兜底，不能写成常规治理动作。

阈值建议用“绝对值 + 增长斜率 + 分位异常”组合。举例：FD 总数达到设备基线 P99 并且 10 分钟持续增长，同时 top-N 目标集中在同一日志目录，可以触发短时 hook；只是在播放器启动时 FD 短暂升高，随后回落，不应触发重型诊断。

## 扩展：与 20.7 异常处理架构的边界

20.7 负责异常捕获、SafeMode、降级和热修复接入。本节只提供资源证据：线程快照、FD 快照、创建堆栈、资源曲线和归因结论。异常框架拿到这些证据后，可以决定是否打开降级开关、是否进入 SafeMode、是否暂停灰度。

[交叉引用: 详见 20.7 节]

## 扩展：与 26.2 / 26.5 线上证据包的衔接

Crash 上报和线上排查系统需要把资源证据作为附件，而不是只保存崩溃栈。资源附件建议拆成三份：

| 附件 | 写入时机 | 内容 |
|------|----------|------|
| `thread_snapshot.json` | 阈值触发或 Crash 前置采样 | 线程数量、名称、状态、栈顶摘要、匿名线程占比 |
| `fd_snapshot.json` | FD 阈值触发 | FD 总数、类型分布、top-N 目标摘要、采样时间 |
| `resource_trend.json` | 下次启动补齐 | 最近 N 次采样的时间序列、版本、进程、前后台状态 |

Crash 当下只写最小文件，上传、符号化、聚合和告警放到 26.2；线上复现、动态日志、远程 trace 和用户反馈放到 26.5。这样资源治理不会把 Crash handler 变成复杂业务逻辑。

[交叉引用: 详见 26.2、26.5 节]

## 扩展：Android 16 / 17 仍需复核的点

两处内容需要在后续 Task9 或实机验证中继续补证：

- `FD_SET` 触发路径：当前已验证 AOSP android-16.0.0_r1 的 bionic FORTIFY 检查，但不同厂商 libc、目标 SDK、老设备 `select` 使用方式可能存在差异。线上结论要同时看 tombstone、设备系统版本和触发库。
- AGP 插桩接入：线程命名插桩的字节码规则已经明确，但 AGP 8.x instrumentation API、R8 混淆、增量编译和三方库处理需要在目标工程里验证。

[待验证: 厂商 libc / 目标 SDK 对 `FD_SET` 触发路径的影响]
[待验证: AGP 8.x instrumentation API 与 R8 对线程命名插桩的影响]
