---
title: "崩溃与 ANR 捕获机制"
chapter: "19"
section: "19.24"
drafted_date: "2026-04-24"
drafted_by: "gemini"
applicable_versions: "Android 8 (API 26) - Android 17 (API 37)"
last_verified: "2026-04-24"
confidence: high
tags: [apm, crash, anr, stability, crashpad]
related_chapters: ["19.0", "19.03", "19.16"]
task6_state: reviewed
task6_result: pass-light-edit
reviewed_date: "2026-05-03"
reviewed_by: openclaw-task6
sources:
  - "https://developer.android.com/reference/java/lang/Thread.UncaughtExceptionHandler"
  - "https://developer.android.com/reference/android/app/ApplicationExitInfo"
  - "https://developer.android.com/reference/android/app/ActivityManager#getHistoricalProcessExitReasons(java.lang.String,int,int)"
  - "https://raw.githubusercontent.com/chromium/crashpad/main/doc/overview_design.md"
  - "https://developer.android.com/ndk/guides/gwp-asan"
  - "https://android.googlesource.com/platform/art/+/refs/heads/main/runtime/signal_catcher.cc"
  - "https://android.googlesource.com/platform/system/core/+/refs/heads/main/debuggerd/proto/tombstone.proto"
  - "https://android.googlesource.com/platform/bionic/+/refs/heads/main/libc/include/signal.h"
last_task2b_at: "2026-04-27T19:40:00+08:00"
repaired_date: "2026-04-27"
repaired_by: "openclaw-task2b"
status: finalized
pipeline_stage: ready-to-publish
task9_result: pass-tech-review
task9_state: reviewed
task2b_state: fixed
task2b_result: fixed
task9_reviewed_date: 2026-05-06
task9_reviewed_by: openclaw-task9
last_task9_at: "2026-05-06T10:38:04+08:00"
task9_review_notes: "2026-05-06 Task9 10:24：pass-tech-review。复核 Java Crash handler 链、Crashpad/sigaction、SIGQUIT/SignalCatcher、ApplicationExitInfo API30/API31 边界、LMK 静态 API；无 P0/P1/P2。Task6 已通过且 queue 无 pending，自动晋升 finalized。"
---

# 崩溃与 ANR 捕获机制

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 [定位] 揭秘 APM 稳定性基建的最底层逻辑，解析 Java Crash、Native Crash 与 ANR 的捕获黑魔法。
- 🔹 [Java Crash 捕获] 展开 `Thread.setDefaultUncaughtExceptionHandler` 的原理，以及如何保证自身上报逻辑不被 Crash 截断。
- 🔹 [Native Crash 捕获] 解析 Google Breakpad / Crashpad 在 Android 端的应用，说明 Linux 信号（Signal）拦截机制与 Tombstone 文件的生成与解析。
- 🔹 [ANR 捕获演进史] 从早期读取 `/data/anr/traces.txt`，到监听 SIGQUIT 信号 (Signal Catcher Hook)，再到 Android 11+ 官方 `ApplicationExitInfo` 的终极方案。
- 🔹 [OOM 细分与防范] 拆解非 Java Heap OOM 的监控：文件描述符 (FD) 溢出、线程池暴增 (Thread Exhaustion)、虚拟内存地址空间 (VMA) 耗尽的监控与预警。
- 🔹 [现场快照留存] 说明崩溃瞬间如何收集寄存器状态、内存使用率、Logcat 尾部日志、以及用户 Session 操作轨迹。
- 🔹 [多 SDK 冲突] 解释当项目中同时存在多个 APM (如 Bugly + Firebase + 自研) 时，Crash Handler 被覆盖或死锁的风险及链接链处理方案。

### 扩展（可选深入）

- 🔸 绘制一张 Native Signal 从发生到 Crashpad 捕获上报的完整时序图。
- 🔸 提供针对 Android 11+ `ApplicationExitInfo` 捞取 ANR 与 LMK (Low Memory Killer) 历史记录的代码片段。
- 🔸 介绍对于 C/C++ 内存破坏 (如 Use-After-Free) 的 GWP-ASan 线上灰度检测方案。

### 流水线加工要求

- 要把不同 Android 版本对底层 `/data/anr` 或进程内存文件的权限封堵作为重要背景交代。
- OOM 监控部分不能只写 Java 堆内存，必须写清 FD 和线程数溢出的底层原因。
- 强调异常处理函数中绝对不能做复杂的内存分配与锁操作，以防二次 Crash。

### OpenClaw 加工指引

> **锚点**是最低覆盖要求，加工时必须逐条落实并标注验证结果。
> **扩展**视素材丰富程度选择性深入。
<!-- outline-end -->

稳定性 APM 要解决的不是“进程挂了”这一件事，而是四类不同现场：Java 未捕获异常、Native 信号崩溃、ANR、以及没有抛异常却把进程拖死的资源耗尽。四类现场的采样入口、线程上下文、权限边界都不同，统一看板只是收尾阶段，前面必须先把捕获路径搭对。

## 1. 稳定性采样面：先分清谁在什么时刻还有执行机会

| 现场类型 | 典型入口 | 进程当时是否还可控 | 适合采什么 |
| --- | --- | --- | --- |
| Java Crash | `Thread.setDefaultUncaughtExceptionHandler` | 部分可控，当前线程即将退出 | 异常类型、线程名、Java 栈、轻量 breadcrumb |
| Native Crash | `sigaction` / Crashpad client | 风险很高，只能做极少操作 | 寄存器、signal、native backtrace、so build id |
| ANR | 系统生成 traces / `ApplicationExitInfo` | ANR 发生时应用未必有回调机会 | 主线程栈、binder wait、锁竞争、退出原因 |
| 资源耗尽 | 周期采样 + 下次启动补拉 | 多数发生前仍可观测 | FD、线程数、RSS、VMA、LMK 历史 |

这张表决定了后面的实现风格：Java Crash 可以做一点点同步收尾；Native Crash 只能写最小快照；ANR 更依赖系统产物和下次启动拉取；资源耗尽要靠日常采样，而不是等进程要死时临时补救。

## 2. Java Crash：`setDefaultUncaughtExceptionHandler` 是第一入口，不是终点

Java 层未捕获异常最终会走到 `Thread.UncaughtExceptionHandler`。全局 APM 一般在 `Application` 里调用 `Thread.setDefaultUncaughtExceptionHandler(...)`，把默认处理器替换成自己的代理，再把原处理器保存下来。

### 2.1 代理式处理比“完全接管”更稳

这段代码的用途是把异常摘要写入本地 crash store，然后把控制权交回系统或上一个 SDK 的 handler。重点看 `previous` 链接，避免把系统默认退出逻辑吞掉。

```kotlin
class CrashHandlerInstaller {
    fun install(context: Context) {
        val previous = Thread.getDefaultUncaughtExceptionHandler()
        Thread.setDefaultUncaughtExceptionHandler { thread, throwable ->
            try {
                CrashStore.persist(
                    context = context,
                    threadName = thread.name,
                    throwable = throwable,
                    timestampMs = System.currentTimeMillis()
                )
            } catch (_: Throwable) {
                // 这里只做兜底，不能再抛异常。
            } finally {
                previous?.uncaughtException(thread, throwable)
            }
        }
    }
}
```

这类 handler 里有三条硬约束：

- 不做复杂内存分配。进程可能已经接近 OOM，再分配大对象只会更早崩。
- 不做锁竞争。日志系统、数据库、线程池都可能正处在不一致状态。
- 不做实时网络上报。最稳的方案是本地落一份轻量 envelope，下次启动再传。

### 2.2 如何保证上报逻辑不被 Crash 截断

一个稳妥的 Java Crash 方案通常分成两段：

1. **崩溃当下**：只写本地文件或 mmap ring buffer，内容包含异常摘要、线程名、时间戳、版本号、最近 breadcrumb id。
2. **下次启动**：应用冷启动后扫描 crash store，做压缩、补充设备信息、再异步上传。

这样设计有两个好处：

- 主线程崩溃时，系统马上会结束进程，本次网络请求大概率发不完。
- 现场收集和真正上报解耦，便于后面统一做限流、重试和隐私裁剪。

## 3. Native Crash：信号处理器只负责“保命级”快照

Native Crash 在 Linux / Android 上通常表现为 `SIGSEGV`、`SIGABRT`、`SIGBUS`、`SIGILL`、`SIGFPE`、`SIGTRAP` 等信号。`SIGTRAP` 常见于断点、调试陷阱，以及 GWP-ASan 等内存破坏检测路径。AOSP 系统侧会通过 `debuggerd` / `tombstoned` 生成 tombstone。应用侧 APM 如果也要采样，常见做法是安装 `sigaction` handler，再把最小现场交给 Breakpad 或 Crashpad。

### 3.1 Breakpad / Crashpad 的角色分工

- Breakpad 时代常见的是进程内信号处理，再生成 minidump。
- Crashpad 的设计更稳：客户端库在应用进程内注册，真正的 handler 运行在独立进程。崩溃发生后，信号处理器把异常信息位置通过 socket 交给 handler，由 handler 去快照进程状态并写 crash dump。

这类 out-of-process 设计有一个直接收益：崩溃线程的栈、堆、锁都可能已经损坏，但独立 handler 进程还活着，写 dump 的成功率更高。

### 3.2 Signal handler 里能做什么

Signal handler 的工作应当收缩到最小集合：

- 记录 signal number、fault address、thread id
- 读取 `ucontext_t` 中的寄存器上下文
- 将必要信息写入预分配缓冲区或通知 Crashpad handler
- 恢复前一个 handler 或重新抛出 signal，让系统继续生成 tombstone

不该做的事同样明确：

- 不能依赖 malloc/new
- 不能拿互斥锁
- 不能调用不满足 async-signal-safe 的复杂库函数
- 不能在 handler 内直接拼大 JSON 或访问 Java VM

如果项目里既想保留系统 tombstone，又想拿自定义 minidump，顺序应收缩为：应用侧记录最小信息 → 交给 Crashpad / Breakpad → 按 `sigaction` 的旧配置链到前一个 handler；没有旧 handler 时恢复默认动作并重新抛出 signal。这里不能把旧 handler 一律当成单参数函数调用，`SA_SIGINFO` 会改变回调签名。

这段伪代码只展示链式分发的分支。其中 `SA_SIGINFO`、`SIG_DFL`、`SIG_IGN` 三类处理决定后续调用方式，处理错会导致二次崩溃。

```cpp
static void DispatchToPreviousOrSystem(
        int signum, siginfo_t* info, void* ucontext,
        const struct sigaction& old_action) {
    if ((old_action.sa_flags & SA_SIGINFO) && old_action.sa_sigaction != nullptr) {
        old_action.sa_sigaction(signum, info, ucontext);
        return;
    }

    if (old_action.sa_handler == SIG_IGN) {
        return;
    }

    if (old_action.sa_handler != nullptr && old_action.sa_handler != SIG_DFL) {
        old_action.sa_handler(signum);
        return;
    }

    // 交回系统默认诊断链，让 debuggerd / tombstoned 继续生成 tombstone。
    sigaction(signum, &old_action, nullptr);
    raise(signum);
}
```

线上实现还要处理重入保护、备用栈、信号掩码恢复和 handler 返回后的终止策略。应用级 APM 不应吞掉 crash signal，否则系统 tombstone、logcat fatal 记录和其他 SDK 的收尾逻辑都会缺失。

### 3.3 Tombstone、minidump、符号化各自管什么

- **tombstone**：系统产物，适合看 native backtrace、寄存器、maps、abort message
- **minidump**：APM 自定义产物，便于统一上传和后台解析
- **符号化**：把 PC 地址还原到函数、源文件、行号，需要 build id、符号表、版本管理配套

线上如果只收地址不收 build id，后端就很难把同一类 Native Crash 聚合稳定。

## 4. ANR 捕获演进：从读文件到官方退出历史

ANR 的捕获链变化最大，原因是权限边界一直在收紧。

### 4.1 早期：读 `/data/anr/traces.txt`

早期调试环境里，开发者常直接读取 `/data/anr/traces.txt`，或者从 `/data/anr/` 拉 `anr_*` 文件。它的优点是内容直观，能直接看到主线程和 Binder 线程堆栈。

它的问题也很明显：

- 生产环境应用进程通常没有这一路径的读取权限
- 文件格式和命名跨版本有差异
- 这是离线取证手段，不是稳定的 App 内实时方案

所以，这条路适合调试机和实验环境，不适合作为线上端侧默认实现。

### 4.2 中期：SIGQUIT / Signal Catcher Hook

系统在处理 ANR 时会对目标进程发送 `SIGQUIT`，ART 的 SignalCatcher 线程负责生成 Java 线程 dump。SignalCatcher 不是普通的 `sigaction` handler；AOSP `art/runtime/signal_catcher.cc` 中的等待逻辑使用 `sigwait()` 同步消费 `SIGQUIT`。

`sigwait()` 的前提是目标信号在相关线程中被屏蔽。信号到达后，等待线程被唤醒，内核不会再把同一个信号分发给普通 `sigaction` handler。这也是很多端侧方案“注册了 SIGQUIT handler，却抓不到稳定 ANR 信号”的原因。

APM 里所谓的 SIGQUIT Hook，通常需要改动以下环节之一；简单注册 handler 不足以稳定截获 ANR：

- 影响 SignalCatcher 线程或 ART dump 流程
- 调整进程内线程的信号掩码
- 在系统 dump 前后插入采样逻辑
- 在厂商 ROM、root/test 环境中改造系统侧 ANR 流程

这类方案能拿到更早的现场，但维护成本很高：

- 与 ART、libsigchain、其他 SDK 的信号处理逻辑互相影响
- Android 版本演进后，信号掩码和 dump 行为可能变化
- 普通 App 量产环境缺少稳定权限边界，容易干扰系统 ANR 诊断

量产 App 的默认路径应优先使用 `ApplicationExitInfo` 和下次启动补拉；SIGQUIT Hook 更适合自研系统、厂商 ROM、root/test 环境或强控制灰度。

### 4.3 Android 11+：`ApplicationExitInfo`

Android 11 起，`ActivityManager.getHistoricalProcessExitReasons()` 提供了更稳的官方方案。应用可以在每次启动时拉最近的退出历史，识别 `REASON_ANR`、`REASON_LOW_MEMORY`、`REASON_CRASH`、`REASON_CRASH_NATIVE` 等原因。`ApplicationExitInfo.getTraceInputStream()` 的返回内容要按 API 版本和 `reason` 分支处理。

| API / Android 版本 | `reason` | `getTraceInputStream()` 常见内容 | 端侧处理 |
| --- | --- | --- | --- |
| API 30 / Android 11 | `REASON_ANR` | 系统保留的 ANR traces 文本流 | 后台线程读取，按线程 dump 解析 |
| API 31+ / Android 12+ | `REASON_CRASH_NATIVE` | tombstone protobuf 二进制流 | 按 `system/core/debuggerd/proto/tombstone.proto` 解析，不要当纯文本处理 |
| API 30+ | `REASON_LOW_MEMORY`、`REASON_CRASH`、其他 reason | 通常没有 trace stream，或设备侧保留策略不同 | 使用 reason、status、description、RSS/PSS 与自研 breadcrumb 拼样本 |

读取 trace stream 要放到后台线程，并用 `timestamp + reason + pid/processName` 或自研事件 id 去重。系统保留的是环形历史，重复启动、重复上传和流读取失败都要作为正常分支处理。

这段代码的用途是拉取最近一次 ANR 或 LMK 记录。重点看两点：一是每次启动都拉，因为系统使用环形缓冲；二是 LMK 仍要结合设备是否支持低内存杀报告来解释。

```kotlin
@RequiresApi(30)
fun readRecentExitRecords(context: Context): List<String> {
    val activityManager = context.getSystemService(ActivityManager::class.java)
    val infos = activityManager.getHistoricalProcessExitReasons(null, 0, 10)
    val lowMemoryReportSupported = ActivityManager.isLowMemoryKillReportSupported()

    return infos.map { info ->
        val reason = when (info.reason) {
            ApplicationExitInfo.REASON_ANR -> "ANR"
            ApplicationExitInfo.REASON_LOW_MEMORY -> "LOW_MEMORY"
            ApplicationExitInfo.REASON_CRASH -> "JAVA_CRASH"
            ApplicationExitInfo.REASON_CRASH_NATIVE -> "NATIVE_CRASH"
            ApplicationExitInfo.REASON_SIGNALED -> {
                if (!lowMemoryReportSupported && info.status == android.system.OsConstants.SIGKILL) {
                    "SIGNALED_SIGKILL_POSSIBLY_LMK"
                } else {
                    "SIGNALED"
                }
            }
            else -> "OTHER(${info.reason})"
        }
        "reason=$reason timestamp=${info.timestamp} description=${info.description}"
    }
}
```

这套接口的意义不只是“替代 traces.txt”。它把 ANR、LMK、Java Crash、Native Crash 都拉回了同一份退出历史模型，适合和自研 breadcrumb、前后台状态、版本号一起拼成稳定性样本。

## 5. OOM 不能只盯 Java Heap

线上很多“无崩溃退出”往往不是 `OutOfMemoryError`，而是资源被耗空后被系统杀掉，或者关键系统调用失败。只盯 Java Heap，很多问题会漏。

### 5.1 需要分开的几类资源耗尽

| 类型 | 典型表现 | 观测入口 | 常见原因 |
| --- | --- | --- | --- |
| Java Heap OOM | `OutOfMemoryError` | JVM 异常、heap 指标 | 大对象、泄漏、Bitmap 失控 |
| Native 内存增长 | 无 Java 异常，RSS 持续涨 | `Debug.MemoryInfo`、`/proc/self/status` | C/C++ buffer、图形内存、解码器 |
| FD 耗尽 | `EMFILE`、文件或 socket 打不开 | `/proc/self/fd` 计数 | socket 未关闭、文件流泄漏、inotify 过多 |
| 线程耗尽 | 新线程创建失败、调度抖动 | `/proc/self/status` 的 `Threads` | 无界线程池、阻塞任务堆积 |
| VMA / 地址空间耗尽 | `mmap` 失败、地址空间碎片、maps 行数异常 | `/proc/self/maps` 行数、`VmSize`、RSS/PSS | 32 位地址空间紧张；64 位多见极端映射泄漏、图形/ashmem 资源异常 |
| LMK | 进程被系统杀掉 | `ApplicationExitInfo`、Vitals | 后台占用过高、整机内存压力 |

32 位和 64 位进程的 VMA 风险口径不同。32 位进程地址空间上限低，连续映射碎片、so/JIT/ashmem 分布都可能变成真实故障；64 位进程地址空间大，单纯 `VmSize` 变大不一定等价于风险，排查时更应看 maps 行数增长、RSS/PSS、图形内存、ashmem 和异常 mmap 泄漏。

### 5.2 端侧怎么做预警

一套实用的做法是日常轻采样，而不是等进程快死时才采：

- 周期读取 `/proc/self/fd`，记录 FD 总数和增长速度
- 周期读取 `/proc/self/status`，记录 `Threads`、`VmSize`、`VmRSS`
- 高风险模块打点分桶，例如图片解码、数据库、WebView、音视频、日志系统
- 应用重启后拉 `ApplicationExitInfo`，补齐 LMK 历史

这样，后台才能区分“Java Heap 已爆”“Native RSS 持续长高”“FD 泄漏导致 socket 创建失败”“线程数冲上去以后调度雪崩”这些完全不同的问题。

## 6. 现场快照：崩溃当下只收最小集合，其余留到下次启动补齐

现场快照的目标是帮后端聚类和复盘，不是把整台设备所有信息都塞进一条记录。一个可执行的最小集合可以是：

- 线程或 signal 基本信息：线程名、tid、signal、异常类型
- 关键栈：Java 主线程栈、crashing thread native backtrace
- 进程资源快照：RSS、PSS、FD 数、线程数、前后台状态
- Build 信息：version code、ABI、build id、设备型号、系统版本
- 最近日志：本地 ring buffer 里的最近 N 条内部日志
- 用户 breadcrumb：页面跳转、点击、网络请求摘要、实验组

这里最容易犯的错，是在 crash handler 里临时去抓 Logcat、扫全量数据库、请求远端配置。稳妥做法是平时就维护一份锁自由或低锁竞争的 ring buffer，把最近操作轨迹写进去。崩溃时只存指针或切片，下次启动再异步整理。

## 7. 多 SDK 冲突：默认假设 handler 会被覆盖

项目同时接 Bugly、Firebase、自研 SDK 时，最常见的麻烦在于谁在收尾安装 handler，谁把前面的回调关系断了——“谁采得更多”反而不是重点。

### 7.1 Java 层冲突

Java Crash handler 的冲突模式通常有三种：

- 后安装的 SDK 覆盖前一个 handler，却没有回调 `previous`
- 多个 SDK 都在 `uncaughtException` 里做阻塞 I/O，互相拖慢
- 某个 SDK 为了“吃掉崩溃”直接不再交给系统默认 handler

处理方式是建立一个统一 hub：应用只安装一个默认 handler，内部把事件 fan-out 给多个 sink。第三方 SDK 如果无法改造，就把安装顺序和链式回调在接入层统一封装。

### 7.2 Native 层冲突

Native signal handler 的冲突更难排：

- 多个库同时 hook `sigaction`
- 某个库没有保存旧 handler
- handler 中使用非 async-signal-safe 调用，死锁或二次崩溃

Native 层要额外做两件事：

- 明确安装顺序，并保存旧 handler 指针
- 对同一 signal 做重入保护，避免 handler 自己再触发 signal

如果项目无法完全控制第三方 SDK，优先选择它们的“只采集、不接管终止逻辑”模式，把真正的退出链保留给系统。

## 8. Android 11+ 之后的一套推荐组合

面向 Android 11 及以上设备，稳定性 APM 的默认组合可以压成下面这张表：

| 现场 | 默认方案 | 备注 |
| --- | --- | --- |
| Java Crash | `setDefaultUncaughtExceptionHandler` 代理 + 本地 crash store | 只做轻量落盘，启动后上传 |
| Native Crash | Crashpad / 自研 signal handler + 系统 tombstone 链接 | 记 build id，保留链到系统 |
| ANR | 启动时拉 `ApplicationExitInfo` + traces 输入流 | 比读 `/data/anr` 更稳 |
| LMK / 资源耗尽 | 周期轻采样 + 启动时退出历史补拉 | 结合 `isLowMemoryKillReportSupported()` 解释 |
| C/C++ 内存破坏 | GWP-ASan 灰度 | 适合低比例线上侦错 |

这套组合的优点是职责清楚。Java Crash、Native Crash、ANR、LMK 各走最稳的入口，不强迫一个 handler 同时解决所有现场。

## 9. GWP-ASan：线上抓 C/C++ 内存破坏的补充手段

常规 Crash 报告能看到“已经崩了之后”的栈，但对 use-after-free、heap corruption 这类问题，单靠普通 minidump 有时还不够。GWP-ASan 的定位是低比例灰度抽样，提前把部分分配切到带保护页的路径，命中后给出更明确的内存破坏证据。

它不适合全量开启，原因很简单：调试价值高，运行时开销也更高。对 C/C++ 模块占比较重的应用，推荐作为专项灰度开关，而不是默认全量配置。

## 10. 参考资料与延伸阅读

- `art/runtime/signal_catcher.cc`：ART SignalCatcher 使用 `sigwait()` 处理 `SIGQUIT` 的实现
- `system/core/debuggerd/proto/tombstone.proto`：API 31+ native tombstone protobuf 的结构参考
- `bionic/libc/include/signal.h`：`struct sigaction`、`SA_SIGINFO` 与 handler 签名
- `Thread.UncaughtExceptionHandler`：Java 未捕获异常的官方处理契约
- `ApplicationExitInfo` 与 `ActivityManager.getHistoricalProcessExitReasons()`：Android 11+ 统一退出历史入口
- Crashpad Overview Design：out-of-process handler、socket 通知、crash dump 流程
- GWP-ASan：线上低比例捕获 C/C++ 内存破坏

## 11. 锚点覆盖核对

- [已覆盖] 定位：区分 Java Crash、Native Crash、ANR、资源耗尽四类现场
- [已覆盖] Java Crash 捕获：解释 `setDefaultUncaughtExceptionHandler` 与本地落盘方案
- [已覆盖] Native Crash 捕获：补齐 signal handler、Crashpad、tombstone、minidump 关系
- [已覆盖] ANR 捕获演进史：覆盖 `traces.txt`、SIGQUIT、`ApplicationExitInfo`
- [已覆盖] OOM 细分与防范：补齐 FD、线程、VMA、LMK 监控
- [已覆盖] 现场快照留存：定义最小快照集合与 ring buffer 方案
- [已覆盖] 多 SDK 冲突：说明 Java / Native handler 链接链处理方式
- [扩展已覆盖] `ApplicationExitInfo` 代码片段
- [扩展已覆盖] GWP-ASan 灰度方案
