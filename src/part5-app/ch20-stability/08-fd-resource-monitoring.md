---
title: FD 耗尽监控与故障排查
chapter: '20.8'
status: finalized
applicable_versions: Android 8 (API 26) - Android 17 (API 37)
tags:
- stability
- fd
- resource-exhaustion
- observability
related_chapters:
- '20.5'
- '20.2'
- '20.12'
- '26.2'
- '26.3'
- '14.7'
consolidated_from:
- src/part5-app/ch20-stability/14-thread-fd-resource-monitoring.md
last_verified: '2026-08-14'
last_verified_against: AOSP android-17.0.0_r1 bionic, libcore, and ART sources; android17-6.18-2026-06_r6 procfs documentation; current Android Developers API and Android 11 fdsan guidance through 2026-08-13
confidence: medium-high
sources:
- type: blog
  path: Clippings/Android 应用稳定性剖析与优化 - 实现 FD 监控：文件描述符（FD）超限怎么办？.md
  availability: not present in the current vault as of 2026-08-14; retained as legacy provenance and not used as current evidence
- type: blog
  path: Clippings/Android 应用稳定性剖析与优化 - OOM 发生路径：了解 OOM 是如何产生的.md
  availability: not present in the current vault as of 2026-08-14; retained as legacy provenance and not used as current evidence
- type: aosp-legacy
  path: https://android.googlesource.com/platform/bionic/+/refs/tags/android-16.0.0_r1/libc/private/bionic_fortify.h
  availability: retained as the original source anchor; current statements are verified against android-17.0.0_r1
- type: official
  path: https://developer.android.com/reference/java/io/FileDescriptor
- type: official
  path: https://developer.android.com/ndk/reference/group/file-descriptor
- type: aosp
  path: https://android.googlesource.com/platform/bionic/+/refs/tags/android-17.0.0_r1/libc/private/bionic_fortify.h
- type: aosp
  path: https://android.googlesource.com/platform/bionic/+/refs/tags/android-17.0.0_r1/libc/include/sys/select.h
- type: aosp
  path: https://android.googlesource.com/platform/bionic/+/refs/tags/android-17.0.0_r1/libc/bionic/fdsan.cpp
- type: aosp
  path: https://android.googlesource.com/platform/bionic/+/refs/tags/android-17.0.0_r1/libfdtrack/
- type: official
  path: https://developer.android.com/reference/android/system/Os#readlink(java.lang.String)
- type: official
  path: https://developer.android.com/about/versions/11/behavior-changes-all#fdsan
- type: aosp-kernel
  path: https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/Documentation/filesystems/proc.rst
- type: aosp-thread-legacy
  path: https://android.googlesource.com/platform/libcore/+/refs/tags/android-17.0.0_r1/ojluni/src/main/java/java/lang/Thread.java
- type: aosp-thread-legacy
  path: https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/runtime/native/java_lang_Thread.cc
- type: official-thread-legacy
  path: https://developer.android.com/reference/java/lang/Thread
- type: official-thread-legacy
  path: https://developer.android.com/reference/tools/gradle-api/com/android/build/api/instrumentation/AsmClassVisitorFactory
pipeline_stage: ready-to-publish
task6_state: reviewed
section: '20.8'
task9_state: reviewed
task2b_state: fixed
note: 'Consolidated-source availability: source page not present in the current vault as of 2026-08-14; FD content is retained here and thread-specific guidance is covered by chapter 20.19'
---

# FD 耗尽监控与故障排查

FD（file descriptor，文件描述符）是进程用来引用内核对象的整数编号。文件、socket（网络套接字）、pipe（管道）、eventfd（事件通知描述符）和 epoll（事件监听器）都会占用 FD。FD 接近进程限额时，新建对象会失败；即使打开数量不多，把编号过高的 FD 交给旧式 `select()`，也可能触发 bionic（Android 的 C 标准库及底层运行时）FORTIFY 主动中止进程。

排查时要区分打开数量、FD 编号、对象类型、generation（创建代次）与 owner（负责释放资源的所有者）。`/proc/self/fd` 只能提供某一时刻的近似快照，无法单独回答每个 FD 由谁创建、应由谁关闭。

平台源码固定到 Android 17 / API 37 / `android-17.0.0_r1`；涉及 `/proc`、rlimit 与 FD 分配语义时，内核源码固定到 `android17-6.18-2026-06_r6`。线程与协程见 20.12，Native 内存见 20.13；本文只在它们与 FD 出现在同一故障现场时说明证据关系。

## FD：数量、编号、对象和所有者要分开

FD 是进程文件描述符表中的整数索引。关闭一个 FD 后，内核通常会把较小的空闲编号分配给后续对象。double-close 指同一编号被关闭两次：第二次关闭时，该编号可能已经指向另一线程刚创建的对象，最终造成 use-after-close（关闭后仍使用）或数据损坏。因此，监控记录不能只保存“编号 123 曾由谁打开”。

需要区分：

- 当前打开 FD 的数量；
- FD 数值本身，例如是否达到 `FD_SETSIZE`；
- symlink（symbolic link，符号链接）指向的对象类型；
- 创建事件的 generation；
- 哪个所有者负责关闭；
- `dup` 复制后，新旧描述符各自的生命周期。

generation 是同一编号每次重新创建或复用时递增的代次，用于区分“旧的 123”和“新的 123”。所有者可以是创建该 FD 的对象、模块或任务，其职责是保证每条成功创建路径都有且只有一次关闭。

`/proc/self/status` 中的 `FDSize` 表示已分配的描述符槽位数，并非当前打开数量。procfs 是内核通过 `/proc` 暴露进程和系统状态的虚拟文件系统。Linux 6.18 的 procfs 文档说明，`/proc/<pid>/fd` 目录包含进程当前打开 FD 的符号链接；应用采集自身进程时应使用 `/proc/self/fd`，这样可避开 PID（进程编号）复用和跨进程访问权限问题。

### 常规计数与触发式详细快照

枚举 `/proc/self/fd` 需要遍历目录；采样期间，其他线程仍可能打开或关闭 FD，所以结果只能视为近似快照。下面的代码只计算名称为数字的目录项，不读取每条符号链接。

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

目录枚举本身可能短暂占用一个 FD，并发打开或关闭还会造成竞态，因此不要为了追求“精确值”固定减 1。趋势监控应容忍少量测量误差。

Android 17 的 6.18 内核文档还规定，`/proc/<pid>/fd` 的 `stat().st_size` 保存进程的打开文件数，可用于快速读取。旧 Android 或 vendor kernel（设备厂商使用的内核）未必具有相同语义；应用要先按设备验证，再把它作为优化路径。

只有在计数、增长速度等条件触发诊断时，才读取各条符号链接。链接目标可用于类型归类，原始路径不应直接上传。

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

`readlink()` 读取符号链接目标；读取前 FD 可能已经关闭，所以失败并不罕见。调用方要保留 `complete`（快照是否完整）和 `skipped`（跳过条目数），不能把缺少条目的快照解释为资源已恢复。

`classifyFd()` 可区分文件或目录、`socket:`、`pipe:`、`anon_inode:`（没有普通文件路径的内核对象）、ashmem 和 memfd 等类型。`normalizeFdTarget()` 应把应用私有文件归入稳定的目录或资源类别，并去掉文件名、用户 ID、URI 和查询参数。

需要进一步判断少量可疑 FD 时，再读取 `/proc/self/fdinfo/<fd>`。普通文件至少包含当前位置 `pos`、打开标志 `flags`、挂载点编号 `mnt_id` 和 inode（文件系统对象编号）；eventfd、epoll 等对象还会提供各自字段。逐个读取所有 FD 的 `fdinfo` 成本较高，不适合高频采样。

## FD 限额和 FD_SET 是两条边界

`RLIMIT_NOFILE` 规定进程可打开的最大 FD 编号加一；由于内核通常分配最小可用编号，它也约束同时打开的 FD 数量。soft limit 是当前生效上限，hard limit 是普通进程可提高 soft limit 的最大值。

新建 FD 会超出 soft limit 时，调用通常返回 `EMFILE`；`ENFILE` 表示系统级打开文件表承受压力。限额取决于设备与进程环境，不应写死统一数值。采样时可以读取 `/proc/self/limits`，或在 Native 层调用 `getrlimit(RLIMIT_NOFILE)`。

`FD_SETSIZE` 是 `select()` 所用 `fd_set` 位集合的默认表示边界。Android 17 bionic 的 `sys/select.h` 将它定义为 1024；`__check_fd_set()` 发现 FD 小于 0、FD 不小于 `FD_SETSIZE`，或调用方提供的 `fd_set` 空间不足时，会触发 FORTIFY fatal。

FORTIFY 是 bionic 的运行时参数检查；fatal 表示检查失败后主动中止进程。

由此有四个结论：

- “打开 FD 总数超过 1024 就会崩溃”是错误结论；
- 进程打开数量很少，也可能通过 `dup2` 得到一个大于等于 1024 的 FD；
- 泄漏使新 FD 编号持续升高时，旧库调用 `FD_SET` 的风险会增加；
- 新代码处理大量 FD 时应优先使用 `poll` 或 `epoll`，避免自行扩大未经验证的 `fd_set`。

tombstone 是 Android 系统生成的 Native 崩溃记录。看到其中出现 `FD_SET: file descriptor ... >= FD_SETSIZE` 时，应先定位把高编号传给 `select()` 的库，再检查进程为何产生该编号。改用合适的等待接口与修复 FD 泄漏可能是两个独立任务。

## 用创建代次处理 FD 编号复用

FD 的创建入口不限于 `open()`。诊断采集至少要考虑：

- `open/openat/creat`；
- `socket/socketpair/accept/accept4`；
- `pipe/pipe2`、eventfd、epoll、inotify、timerfd、memfd；
- `dup/dup2/dup3` 与 `fcntl(F_DUPFD*)`；
- `close` 及语言或框架层所有者发起的关闭。

eventfd、epoll、inotify 和 timerfd 都是通过 FD 暴露能力的内核接口；`dup*` 和 `fcntl(F_DUPFD*)` 会复制描述符。Hook 指在运行时拦截函数调用。如果只拦截 `open()` 与 `close()`，事件表必然缺少其他入口；在所有用户进程长期启用一组 libc（C 标准库）Hook，开销和兼容风险也很高。

事件表可以使用 `fd + generation` 作为本地键。每次成功创建或复制，都为目标编号递增 generation；`dup2()` / `dup3()` 成功覆盖目标编号时，要先结束该编号的旧记录，再建立新记录。每条事件至少包含操作、结果、类型、单调时间、线程 ID、来源 ID，以及按采样规则选取的调用栈。

Hook 实现还要处理：

- 使用 thread-local（每线程独立）标志防止重入，避免展开调用栈、写日志或分配内存时再次打开 FD；
- 设置固定容量和淘汰规则，避免诊断表自身无限增长；
- 只在系统调用成功后更新状态；
- 记录未拦截的创建 API、直接 syscall（系统调用）与 hook 加载顺序造成的盲区；
- 验证与其他 Native Hook SDK 的兼容性；
- 在 16 KB 页设备上验证 ELF 对齐、内存权限和运行时页计算；
- 定期用 `/proc/self/fd` 交叉核对，并把无法匹配的条目标成 `unknown`（来源未知），不要声称事件表完整。

### fdsan 与 fdtrack 的准确用途

Android 10 引入 fdsan（file descriptor sanitizer，文件描述符检查器），Android 11 起默认在检测到所有权错误时中止进程。fdsan 用 owner tag（所有者标签）发现关闭后使用、重复关闭和错误所有者关闭。

只有参与标签协议的 FD 才能获得完整检查，fdsan 也不负责统计泄漏数量。若 tombstone 显示 “fdsan: attempted to close file descriptor ...”，应修正所有权与关闭协议，不要通过降低错误级别隐藏问题。

AOSP（Android Open Source Project，Android 开源项目）还包含 fdtrack。bionic 内部 Hook 接收 FD 创建与关闭事件，`libfdtrack` 使用 unwindstack（Native 调用栈展开库）保存最多 32 帧的创建栈。这个实现需要为事件展开调用栈，并维护固定的 FD 表，适合系统镜像、可调试构建和短时诊断。

`libfdtrack.so` 与 `android_fdtrack_compare_exchange_hook` 属于平台内部接口，不能作为跨 Android 版本稳定可用的 App SDK。线上方案应使用经过验证、开销有上限的自有诊断组件，或采用低频 `/proc` 快照并在资源封装层记录所有者。

## 修复所有权比“崩溃前关几个 FD”更重要

Java/Kotlin 代码优先使用 `use {}` 或 try-with-resources，让作用域结束时自动关闭资源。Native 代码可使用 RAII wrapper：RAII 把资源生命周期绑定到 C++ 对象生命周期，wrapper（封装类）的析构函数负责关闭 FD。

FD 跨越 JNI（Java 与 Native 代码的调用接口）时，`FileDescriptor`、`ParcelFileDescriptor` 和原始 `int fd` 的接口文档要明确：

- 参数是 borrowed（调用方仍持有，接收方不能关闭）还是 transferred（所有权转给接收方）；
- 哪一方负责调用 `close()`；
- `dup()` 后哪一方拥有新的描述符；
- `detachFd()` 取出原始 FD 后，Java 封装对象不再负责关闭哪些资源；
- 异常与取消路径怎样关闭；
- callback（异步回调）超时、页面销毁和进程切换时怎样释放。

不要根据 `/proc/self/fd` 中“看起来没用”的编号直接调用 `close()`。符号链接目标无法说明所有者；关闭 Binder（Android 进程间通信）、Looper（线程消息循环）、数据库或其他线程正在使用的 FD，会造成关闭后使用和数据损坏。

线程也不能因为名称陌生就强制 `interrupt`、`stop` 或 `cancel`。线程生命周期的排查与修复见 20.12；两类资源都应回到创建模块和明确的生命周期所有者。

## 与 OOM、ANR 和 Native Crash 的证据关系

| 现象 | 资源证据 | 不能直接推出 |
| --- | --- | --- |
| `OutOfMemoryError: pthread_create` | Linux task 趋势、栈大小、`VmSize`、创建模块 | Java heap 已满 |
| `EMFILE` / “Too many open files” | FD count、soft limit、类型、增长来源 | 某一个失败的 `open` 是泄漏点 |
| `ENFILE` | 系统级文件表压力与设备状态 | 当前 App 单独泄漏 |
| fdsan abort | owner tag、close 双方栈、FD 复用 | FD 数量已到上限 |
| `FD_SET` FORTIFY abort | 高编号、`select` 调用方、FD 趋势 | 打开数量必然超过 1024 |
| Binder 线程都在等待 | ANR traces、Binder 事务、线程池状态 | 单纯增加 Binder 线程就能解决 |
| eventpoll/eventfd 持续增长 | 对应 Looper、HandlerThread、SDK 生命周期 | 所有 anon_inode 都是泄漏 |

Linux task 是内核调度的任务实体，线程会各自对应一个 task；`VmSize` 是进程虚拟地址空间总量。表中的这些字段需要和 FD 证据共同判断，单独一项不能确定根因。

Binder 线程池无法继续处理请求，常由同步事务阻塞或调用环造成，线程数量只是伴随现象。HandlerThread 是自带 Looper 的线程，Looper/MessageQueue 会正常持有 epoll/eventfd；看到 `anon_inode:[eventpoll]` 只能确定对象类型。只有这些对象随着所属页面或模块反复销毁而持续增长，才构成泄漏证据。

Crash、ANR（应用无响应）和 OOM（内存不足）的完整判定分别见 20.3、20.4、20.5。本文只提供故障前的 FD 趋势、创建来源和所有权证据，不能代替 tombstone、ANR trace（ANR 线程记录）或 `ApplicationExitInfo`（系统保存的应用退出信息）。

## 按进程基线和增长速度触发采样

主进程、WebView 进程、播放器、下载服务和 isolated process（权限与组件范围受限的隔离进程）的 FD 基线不同。采样策略至少按进程角色、应用版本、ABI（处理器架构与二进制接口）、前后台状态和关键功能分组。

常规样本建议保留：

- 当前打开数、历史最高值和一段时间内的增量；
- FD 类型分布和最大 FD 编号；
- `RLIMIT_NOFILE` 的 soft limit 与 hard limit；
- 快照失败或字段缺失的原因；
- 是否同时出现 ANR、OOM、网络、数据库或日志错误。

触发条件应综合绝对值、占 soft limit 的比例、增长速度、持续时间和同类设备分位数。分位数用于表示样本在同类设备分布中的位置，例如 P95 高于 95% 的样本。所有进程共用固定阈值会掩盖进程角色差异；短时峰值随后回落，与每次进入页面都只增不减，代表的风险也不同。

进入详细诊断后，应设置：

- 明确最长运行时间、最大事件数和采样率；
- 只保留出现次数最多的 K 个来源，并限制调用栈深度与字符串长度；
- 为前台关键路径设置可接受的 CPU、内存和耗时开销；
- 到期自动停止，并设置两次详细诊断之间的冷却时间；
- 远程开关不可用时采用本地安全默认值；
- 同一进程只启用一个 Native FD 事件采集器，避免多个 hook 争用。

## 资源接近上限时，由所有者负责释放

FD 持续增长且接近上限时，可按影响范围采取以下动作：

- 对新任务施加 backpressure（背压），通过限速、排队或拒绝新任务减少继续创建 FD；
- 停止可选预热、调试日志、长连接或并发下载；
- 由对应页面或模块执行自己的 `close()`、`shutdown()` 或 `quitSafely()`；
- 停止隔离进程中的可选功能，并在满足预设条件后重建该进程；
- 主进程无法安全恢复时，向用户展示升级或重试入口。

不要强制关闭任意 FD、停止未知线程、清除用户数据，也不要把主动终止主进程当作日常恢复方案。SafeMode（安全模式）只能跳过边界明确的可选模块，详见 20.2。

## 资源接近上限时只记录最小证据

资源接近耗尽时，创建线程、分配大数组、枚举全部调用栈或打开新文件都可能失败。fatal handler（致命故障处理器）中不应调用 `Thread.getAllStackTraces()`、遍历每个 `fdinfo` 或启动上传任务。

更稳的做法是：

1. 平时把低成本趋势写入固定容量环形缓冲区，写满后覆盖最旧记录；
2. 阈值触发时预生成有大小上限的 FD 摘要；
3. 如果已有预留并验证过的低成本写入通道，崩溃现场只写摘要 ID 和少量计数；
4. 下一次启动用 `ApplicationExitInfo`、tombstone 与本地摘要核对；
5. 后台再上传、符号化和聚合；符号化是把机器地址还原为函数名与源码位置。

证据文件要使用原子替换，确保读取方只能看到完整旧版本或完整新版本；还要限制总容量，并为格式设置版本号。Crash/ANR 证据包见 26.2、26.3；Java/Native handler 的职责边界见 20.2、20.3。

## 隐私与数据质量

线程名、文件路径、socket 目标和调用栈都可能包含业务或用户信息。上报前应：

- 线程名保留稳定模块前缀，去掉动态 ID；
- 私有目录归一化为目录类别，不传原始文件名；
- socket 只保留协议、类型和经过审核的 endpoint ID（服务端点编号）；
- 调用栈按 build ID、模块和符号 ID 表示；build ID 是链接器写入二进制的构建标识，用于匹配正确的符号文件；
- 所有字符串限制长度，来源不明时使用 `unknown`；
- 客户端样本与服务端聚合都设置保留期限。

hash（散列值）不能自动完成脱敏。低熵文件名、手机号或固定 URL 的候选范围很小，即使散列也可能被字典逐一猜出；能使用枚举类别和模块 ID 时，不要上传原值的 hash。

## 验证方法

单元测试应覆盖监控器内部的状态机，也就是一条 FD 记录从创建、复制到关闭的状态变化：

- FD 编号关闭后被新对象复用；
- `dup2()` / `dup3()` 覆盖已经打开的目标编号；
- `close()` 失败、未拦截创建和 `/proc` 交叉核对差异；
- Hook 内部再次打开 FD 时的重入；
- 事件环达到容量上限后的淘汰；
- `/proc` 读取失败时明确标记缺少数据，不能写成 0。

集成测试要在受控测试进程中注入资源故障：

| 场景 | 预期证据 |
| --- | --- |
| 循环创建但不关闭文件 | 文件类型和同一来源持续增长 |
| socket/pipe/dup 泄漏 | 对应类型、generation（创建代次）和所有者可见 |
| double-close | fdsan 指向所有权错误，不误报成数量耗尽 |
| FD 编号不小于 1024 后调用 `FD_SET` | Android 17 bionic FORTIFY 路径可复现 |
| 资源接近上限时触发崩溃 | 故障处理器不再生成高开销快照 |

故障注入完成后，要让测试进程退出或显式释放资源，避免污染后续用例。不要在承载用户数据的进程中降低 limit 或制造真实泄漏来验证线上告警。

## 复核清单

线程、线程池、`pthread` 与协程的专项清单见 20.12。FD 复核只检查以下项目：

- [ ] `FDSize` 是否没有被误当成当前 FD count？
- [ ] FD 快照是否使用 `/proc/self/fd` 并容忍并发竞态？
- [ ] 事件表是否处理 FD 编号复用、`dup2()` / `dup3()` 和 generation（创建代次）？
- [ ] 是否区分 `EMFILE`、`ENFILE`、fdsan 与 `FD_SET` 主动中止？
- [ ] 是否由明确的所有者关闭资源，避免根据符号链接目标猜测？
- [ ] Native Hook 是否限时、限量、防重入，并与 `/proc` 交叉核对？
- [ ] fatal handler（致命故障处理器）是否只写预生成且大小受限的摘要？
- [ ] 阈值是否按进程基线、soft limit、增长和持续时间计算？
- [ ] 所有路径、线程名和调用栈是否限长、归一化并脱敏？

## 源码与官方资料

### 当前 FD 依据

- [Java `FileDescriptor` API](https://developer.android.com/reference/java/io/FileDescriptor)：Java 封装对象的有效性检查与同步接口。
- [Android NDK：File Descriptor](https://developer.android.com/ndk/reference/group/file-descriptor)：API 31 起 Java `FileDescriptor` 与 Native `int fd` 之间的 JNI 转换接口。
- [AOSP `bionic_fortify.h`（android-16.0.0_r1，旧锚点）](https://android.googlesource.com/platform/bionic/+/refs/tags/android-16.0.0_r1/libc/private/bionic_fortify.h)：保留原稿来源；本轮结论以下一条 Android 17 源码为准。
- [AOSP `bionic_fortify.h`（android-17.0.0_r1）](https://android.googlesource.com/platform/bionic/+/refs/tags/android-17.0.0_r1/libc/private/bionic_fortify.h)：`__check_fd_set()` 的 FORTIFY 条件。
- [AOSP `sys/select.h`（android-17.0.0_r1）](https://android.googlesource.com/platform/bionic/+/refs/tags/android-17.0.0_r1/libc/include/sys/select.h)：`FD_SETSIZE=1024` 与 `poll` 建议。
- [AOSP `fdsan.cpp`（android-17.0.0_r1）](https://android.googlesource.com/platform/bionic/+/refs/tags/android-17.0.0_r1/libc/bionic/fdsan.cpp)：FD 所有者标签检查实现。
- [AOSP `libfdtrack`（android-17.0.0_r1）](https://android.googlesource.com/platform/bionic/+/refs/tags/android-17.0.0_r1/libfdtrack/)：平台 FD 创建栈追踪实现及其内部边界。
- [Android Developers：`Os.readlink()`](https://developer.android.com/reference/android/system/Os#readlink(java.lang.String))：应用读取自身 FD 符号链接的公开接口。
- [Android 11 behavior changes：fdsan](https://developer.android.com/about/versions/11/behavior-changes-all#fdsan)：fdsan 默认中止与所有权错误语义。
- [Android Common Kernel `proc.rst`（android17-6.18-2026-06_r6）](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/Documentation/filesystems/proc.rst)：`Threads`、`FDSize`、`fd` 和 `fdinfo` 的内核接口语义。

### 旧合并稿中的线程来源

以下链接只保留合并历史。线程监控的当前说明与完整资料表见 20.12。

- [AOSP `Thread.java`（android-17.0.0_r1）](https://android.googlesource.com/platform/libcore/+/refs/tags/android-17.0.0_r1/ojluni/src/main/java/java/lang/Thread.java)：Java 线程 API 的旧稿来源。
- [AOSP `java_lang_Thread.cc`（android-17.0.0_r1）](https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/runtime/native/java_lang_Thread.cc)：ART 线程创建入口的旧稿来源。
- [Android Developers：`Thread` API](https://developer.android.com/reference/java/lang/Thread)：Java 线程 ID API 的旧稿来源。
- [Android Developers：`AsmClassVisitorFactory`](https://developer.android.com/reference/tools/gradle-api/com/android/build/api/instrumentation/AsmClassVisitorFactory)：AGP 字节码插桩接口的旧稿来源。

FD 监控应提前保存少量、可信且能关联所有者的证据。打开数量说明资源压力，快照说明对象构成，创建与关闭事件说明生命周期责任；三类证据分开记录，既能控制监控成本，也能避免在资源紧张时引发新的故障。
