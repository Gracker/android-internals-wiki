---
title: "崩溃与 ANR 捕获机制"
chapter: "19.24"
section: "19.24"
drafted_date: "2026-04-24"
drafted_by: "gemini"
applicable_versions: "Android 8 (API 26) - Android 17 (API 37)"
last_verified: "2026-04-24"
confidence: high
tags: [apm, crash, anr, stability, crashpad]
related_chapters: ["19.0", "19.03", "19.16"]
task6_state: reviewed
task6_result: "pass-light-edit"
reviewed_date: "2026-06-02"
reviewed_by: "openclaw-task6"
task6_reviewed_date: "2026-06-03"
sources:
  - "https://developer.android.com/reference/java/lang/Thread.UncaughtExceptionHandler"
  - "https://developer.android.com/reference/android/app/ApplicationExitInfo"
  - "https://developer.android.com/reference/android/app/ActivityManager#getHistoricalProcessExitReasons(java.lang.String,int,int)"
  - "https://raw.githubusercontent.com/chromium/crashpad/main/doc/overview_design.md"
  - "https://developer.android.com/ndk/guides/gwp-asan"
  - "https://android.googlesource.com/platform/art/+/android16-release/runtime/signal_catcher.cc"
  - "https://android.googlesource.com/platform/system/core/+/android16-release/debuggerd/proto/tombstone.proto"
  - "https://android.googlesource.com/platform/bionic/+/android16-release/libc/include/signal.h"
last_task2b_at: "2026-05-25T15:18:38+08:00"
repaired_date: "2026-04-27"
repaired_by: "openclaw-task2b"
status: finalized
pipeline_stage: ready-to-publish
task9_result: "auto-fixed"
task9_state: "reviewed"
task2b_state: fixed
task2b_result: "fixed-lite"
last_task2b_lite_at: "2026-06-03T07:35:00+08:00"
task9_reviewed_date: "2026-06-02"
task9_reviewed_by: "openclaw-task9"
last_task9_at: "2026-06-03T07:20:00+08:00"
task9_review_notes: "2026-06-02 Task9 deep-review: auto-fixed。修正 /data/anr 权限口径、ProfilingTrigger 36.1/API37 分层、Crashpad out-of-process handler 描述；回到 Task6 复审。"
last_task6_audit: "2026-07-15"
last_task6_at: "2026-06-03T09:15:06+08:00"
last_task9_audit: 2026-05-25
last_task9_audit_at: "2026-05-25T13:20:00+08:00"
last_task9_audit_log: "logs/deep-review/2026-05-25-13-audit.md"
last_task6_review_log: "logs/review/2026-06-03-09-09-review.md"
task6_review_notes: "2026-06-03 09:11 Task6 revisiting-review：无新增 L1/L2 问题。Task9 auto-fix 已确认无写作质量问题。满足 auto-promotion 条件，晋升 finalized。（frontmatter 空行、表述收束、ASCII 流程图代码围栏），锚点 7/7 覆盖，未新增 L3/L4 回炉项。Task9 result 为 auto-fixed，送 Task9 复核。"
task6_l1_l2_fixes: 0
task6_l3_l4_issues: 0
task6_new_rework: false
task6_auto_promoted: true
last_task9_review_log: "logs/deep-review/2026-06-03-07-deep-review.md"
last_task2b_verifier_at: "2026-05-31T23:25:00+08:00"
last_task2b_verifier_log: "logs/rework/2026-05-31-23-task2b-verifier.md"
last_task9_autofix_at: "2026-06-02"
deepseek_cn_review_state: done
last_deepseek_cn_review_at: 2026-06-29
---


# 崩溃与 ANR 捕获机制

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 [定位] 说明 APM 稳定性基础设施的底层实现，解析 Java Crash、Native Crash 与 ANR 的捕获路径。
- 🔹 [Java Crash 捕获] 展开 `Thread.setDefaultUncaughtExceptionHandler` 的原理，以及如何保证自身上报逻辑不被 Crash 截断。
- 🔹 [Native Crash 捕获] 解析 Google Breakpad / Crashpad 在 Android 端的应用，说明 Linux 信号（Signal）拦截机制与 Tombstone 文件的生成与解析。
- 🔹 [ANR 捕获演进史] 从早期读取 `/data/anr/traces.txt`，到监听 SIGQUIT 信号 (Signal Catcher Hook)，再到 Android 11+ 官方 `ApplicationExitInfo` 方案。
- 🔹 [OOM 细分与防范] 展开非 Java Heap OOM 的监控：文件描述符 (FD) 溢出、线程池暴增 (Thread Exhaustion)、虚拟内存地址空间 (VMA) 耗尽的监控与预警。
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

稳定性 APM 要覆盖四类不同现场：Java 未捕获异常、Native 信号崩溃、ANR、以及没有抛异常却把进程拖死的资源耗尽。四类现场的采样入口、线程上下文、权限边界都不同，统一看板只是收尾阶段，前面必须先把捕获路径搭对。

## 1. 稳定性采样面：不同现场的执行机会

| 现场类型 | 典型入口 | 进程当时是否还可控 | 适合采什么 |
| --- | --- | --- | --- |
| Java Crash | `Thread.setDefaultUncaughtExceptionHandler` | 部分可控，当前线程即将退出 | 异常类型、线程名、Java 栈、轻量 breadcrumb |
| Native Crash | `sigaction` / Crashpad client | 风险很高，只能做极少操作 | 寄存器、signal、native backtrace、so build id |
| ANR | 系统生成 traces / `ApplicationExitInfo` | ANR 发生时应用未必有回调机会 | 主线程栈、binder wait、锁竞争、退出原因 |
| 资源耗尽 | 周期采样 + 下次启动补拉 | 多数发生前仍可观测 | FD、线程数、RSS、VMA、LMK 历史 |

这张表决定了后面的实现风格：Java Crash 可以做一点点同步收尾；Native Crash 只能写最小快照；ANR 更依赖系统产物和下次启动拉取；资源耗尽要靠日常采样，不能等进程要死时临时补救。

## 2. Java Crash：`setDefaultUncaughtExceptionHandler` 是入口，也只是入口

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
- 现场收集和后续上报解耦，便于后面统一做限流、重试和隐私裁剪。

## 3. Native Crash：信号处理器只负责最小现场快照

Native Crash 在 Linux / Android 上通常表现为 `SIGSEGV`、`SIGABRT`、`SIGBUS`、`SIGILL`、`SIGFPE`、`SIGTRAP` 等信号。`SIGTRAP` 常见于断点、调试陷阱，以及 GWP-ASan 等内存破坏检测路径。AOSP 系统侧会通过 `debuggerd` / `tombstoned` 生成 tombstone。应用侧 APM 如果也要采样，常见做法是安装 `sigaction` handler，再把最小现场交给 Breakpad 或 Crashpad。

### 3.1 Breakpad / Crashpad 的角色分工

- Breakpad 时代常见的是进程内信号处理，再生成 minidump。
- Crashpad 的设计更稳：客户端库在应用进程内注册，实际写 dump 的 handler 运行在独立进程。崩溃发生后，信号处理器把异常信息位置通过 socket 交给 handler，由 handler 去快照进程状态并写 crash dump。

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

如果项目里既想保留系统 tombstone，又想拿自定义 minidump，顺序应控制为：应用侧记录最小信息 → 交给 Crashpad / Breakpad → 按 `sigaction` 的旧配置链到前一个 handler；没有旧 handler 时恢复默认动作并重新抛出 signal。这里不能把旧 handler 一律当成单参数函数调用，`SA_SIGINFO` 会改变回调签名。

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

ANR 的捕获链变化最大，原因是系统对相关文件和进程信号的访问权限持续变严格。

### 4.1 早期：读 `/data/anr/traces.txt`

早期调试环境里，开发者常直接读取 `/data/anr/traces.txt`，或者从 `/data/anr/` 拉 `anr_*` 文件。它的优点是内容直观，能直接看到主线程和 Binder 线程堆栈。

它的问题也很明显：

- 生产环境应用进程通常没有这一路径的读取权限
- 文件格式和命名跨版本有差异
- 这是离线取证手段，不能作为稳定的 App 内实时方案

所以，这条路适合调试机和实验环境，不适合作为线上端侧默认实现。

### 4.2 中期：SIGQUIT / Signal Catcher Hook

系统在处理 ANR 时会对目标进程发送 `SIGQUIT`，ART 的 SignalCatcher 线程负责生成 Java 线程 dump。SignalCatcher 走独立等待线程路径；AOSP `art/runtime/signal_catcher.cc` 中的等待逻辑使用 `sigwait()` 同步消费 `SIGQUIT`。

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

这套接口把 ANR、LMK、Java Crash、Native Crash 都纳入同一份退出历史模型，不只替代 `traces.txt`，也适合和自研 breadcrumb、前后台状态、版本号一起拼成稳定性样本。

## 5. OOM 不能只盯 Java Heap

线上很多“无崩溃退出”没有 `OutOfMemoryError`，常见原因是资源被耗空后被系统杀掉，或者关键系统调用失败。只盯 Java Heap，很多问题会漏。

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

一套实用的做法是日常轻采样，不能等进程快死时才采：

- 周期读取 `/proc/self/fd`，记录 FD 总数和增长速度
- 周期读取 `/proc/self/status`，记录 `Threads`、`VmSize`、`VmRSS`
- 高风险模块打点分桶，例如图片解码、数据库、WebView、音视频、日志系统
- 应用重启后拉 `ApplicationExitInfo`，补齐 LMK 历史

这样，后台才能区分“Java Heap 已耗尽”“Native RSS 持续增长”“FD 泄漏导致 socket 创建失败”“线程数过高导致调度抖动加重”这些不同问题。

## 6. 现场快照：崩溃当下只收最小集合，其余留到下次启动补齐

现场快照的目标是帮后端聚类和复盘，不需要把整台设备所有信息都写进一条记录。一个可执行的最小集合可以是：

- 线程或 signal 基本信息：线程名、tid、signal、异常类型
- 关键栈：Java 主线程栈、crashing thread native backtrace
- 进程资源快照：RSS、PSS、FD 数、线程数、前后台状态
- Build 信息：version code、ABI、build id、设备型号、系统版本
- 最近日志：本地 ring buffer 里的最近 N 条内部日志
- 用户 breadcrumb：页面跳转、点击、网络请求摘要、实验组

这里最容易犯的错，是在 crash handler 里临时去抓 Logcat、扫全量数据库、请求远端配置。稳妥做法是平时就维护一份锁自由或低锁竞争的 ring buffer，把最近操作轨迹写进去。崩溃时只存指针或切片，下次启动再异步整理。

## 7. 多 SDK 冲突：默认假设 handler 会被覆盖

项目同时接 Bugly、Firebase、自研 SDK 时，最常见的风险在于谁在收尾安装 handler，谁把前面的回调关系断了，重点不在“谁采得更多”。

### 7.1 Java 层冲突

Java Crash handler 的冲突模式通常有三种：

- 后安装的 SDK 覆盖前一个 handler，却没有回调 `previous`
- 多个 SDK 都在 `uncaughtException` 里做阻塞 I/O，互相拖慢
- 某个 SDK 为了“吃掉崩溃”直接不再交给系统默认 handler

处理方式是建立一个统一 hub：应用只安装一个默认 handler，内部把事件分发给多个 sink。第三方 SDK 如果无法改造，就把安装顺序和链式回调在接入层统一封装。

### 7.2 Native 层冲突

Native signal handler 的冲突更难排：

- 多个库同时 hook `sigaction`
- 某个库没有保存旧 handler
- handler 中使用非 async-signal-safe 调用，死锁或二次崩溃

Native 层要额外做两件事：

- 明确安装顺序，并保存旧 handler 指针
- 对同一 signal 做重入保护，避免 handler 自己再触发 signal

如果项目无法完全控制第三方 SDK，优先选择它们的“只采集、不接管终止逻辑”模式，把退出链保留给系统。

## 8. Android 11+ 之后的一套推荐组合

面向 Android 11 及以上设备，稳定性 APM 的默认组合可以整理成这张表：

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

它不适合全量开启：调试价值高，运行时开销也更高。对 C/C++ 模块占比较重的应用，推荐作为专项灰度开关，不推荐默认全量配置。

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

## 12. Android 11 以下：ApplicationExitInfo 缺失时的替代方案

<!-- AIW-源码调研-2026-05-08 -->
### 12.1 核心矛盾

低版本缺失的不只是 `ApplicationExitInfo` 这一套 API，背后还缺整套机制：

- **无统一存储**：进程退出时 system_server 不会写 Proto 文件
- **无官方 trace 路径**：`/data/anr/` 对普通 App 始终不可读
- **ANR 无信号**：`SIGQUIT` 由系统发送，但普通 App 无法通过 `sigaction` 截获（SignalCatcher 用 `sigwait()` 消费）

### 12.2 Signal Handler 自注册（Native Crash）

**原理**：在 JNI 层注册 `sigaction`，捕获 `SIGSEGV` / `SIGABRT` / `SIGFPE` 等信号，获取 native crash 时的寄存器上下文和调用栈。

**典型实现**：
```cpp
// 伪代码，参考 KOOM native-hook 和 Breakpad 思路
#include <signal.h>

static struct sigaction g_old_handlers[64];

// sa_sigaction 签名：void (*)(int, siginfo_t*, void*)
// 第三参是 void*，需要自行强转为 ucontext_t*
void crash_handler(int sig, siginfo_t* info, void* context) {
    ucontext_t* ctx = (ucontext_t*)context;

    // 1. 获取 fault address（SIGSEGV 的 si_addr）
    void* fault_addr = info->si_addr;

    // 2. 获取 instruction pointer (ARM64: ctx->uc_mcontext.pc)
    uint64_t pc = ctx->uc_mcontext.pc;

    // 3. 通过 libunwind / libgcc 获取 native backtrace
    // 4. 写入预分配 ring buffer（不可依赖 malloc）
    // 5. 按旧 handler 类型转发（三分支模型）
    struct sigaction* old = &g_old_handlers[sig];
    if (old->sa_flags & SA_SIGINFO) {
        // 旧 handler 也是三参 sigaction 型
        old->sa_sigaction(sig, info, context);
    } else if (old->sa_handler == SIG_IGN) {
        // 旧 handler 设了忽略，不转发
    } else if (old->sa_handler != SIG_DFL) {
        // 旧 handler 是单参 sa_handler 型，只传 signum
        old->sa_handler(sig);
    }
}

// 安装
struct sigaction sa;
sa.sa_sigaction = crash_handler;
sa.sa_flags = SA_SIGINFO;
sigemptyset(&sa.sa_mask);
sigaction(SIGSEGV, &sa, &g_old_handlers[SIGSEGV]);
sigaction(SIGABRT, &sa, &g_old_handlers[SIGABRT]);
```

**局限**：
- 只能捕获 native crash，不能捕获纯 Java OOM
- 信号到来时进程状态已不稳定，上报通道本身可能受损
- ANR 不发信号，无法通过此路径获取 ANR trace

### 12.3 LMKd 监听（进程被 LMK 杀死）

**源码位置**：`system/core/lmkd/`、`frameworks/base/services/core/java/com/android/server/am/ProcessList.java`

LMK 决策使用 `oom_score_adj` 表示进程 kill 优先级，lmkd 再结合内存压力、PSI 与 adj 档位选择目标；`ProcessList` 里的 adj 常量只是优先级输入，不是触发阈值：

```java
// frameworks/base/services/core/java/com/android/server/am/ProcessList.java
// @ AOSP android-14.0.0_r1
static final int ZOMBIE_ADJ = 1000;
static final int CACHED_APP_MAX_ADJ = 999;   // 缓存进程上限
static final int CACHED_APP_MIN_ADJ = 900;   // 缓存进程下限
static final int SERVICE_B_ADJ = 800;
static final int HOME_APP_ADJ = 600;
static final int FOREGROUND_APP_ADJ = 0;
```

因果链：AMS/OomAdjuster 计算进程 `oom_score_adj` → ProcessList 配置 lmkd adj/minfree 档位 → lmkd 结合内存压力和 adj 选择 kill 目标。`computeOomAdj()` 负责计算 adj 值，不是 lmkd 的触发阈值来源。

**低版本 APM 监听方式**：
| 方式 | 权限要求 | 精度 | 实现难度 |
|------|---------|------|---------|
| 轮询 `/proc/<pid>/oom_score_adj` | 需目标进程权限，普通 App 不可行 | 低 | 低 |
| 监听 LMKd socket | 需 root 或厂商合作 | 高 | 高 |
| cgroup v2 `memory.high` (Android 12+) | 系统服务才可读 | 高 | 高 |
| `ActivityManager.isLowMemoryKillReportSupported()` (API 30) | 普通 API，查 LMK 是否上报到退出原因 | 中 | 低 |

`IBinder.FrozenStateChangeCallback` 属于 Binder 冻结/解冻通知，不是 LMK kill 监听入口。普通 App 没有权限读取他进程的 `/proc/<pid>/oom_score_adj`，只能通过系统 API 间接判断。

### 12.4 /data/anr/ 目录不可读的处理

**路径**：`/data/anr/`（现代版本按 `anr_<yyyy-MM-dd-HH-mm-ss-SSS>` 生成单次 ANR trace 文件，权限 0600；早期版本存在 `traces.txt` 路径，文件名和保留策略跨版本不同）

**权限约束**：普通 App 不能直接读写。AOSP android16-release `init.rc` 以 `0775 system system` 创建 `/data/anr`，ANR trace 由系统侧写入；量产 App 只能通过 `ApplicationExitInfo`、bugreport、root/厂商合作等路径获取。

**APM 获取方式**：
| 方式 | 权限要求 | 可靠性 | 备注 |
|------|---------|--------|------|
| strace 监控 `openat/write` | 需 root | 高 | 与系统版本耦合 |
| wormhole 方案（利用 inotify） | 需厂商合作 | 中 | 文件系统事件通知 |
| 启动时读 `ApplicationExitInfo` (API 30+) | 普通 API | 高 | 官方方案 |
| 反射 `ActivityManagerService` 内部接口 | 违反 Android 安全设计 | 高 | 不推荐量产 |

**注**：ANR 不发信号（详见 §4.2），`sigaction` 无法截获。

### 12.5 KOOM fork-dump 对低版本 OOM 的补偿

KOOM 的核心贡献是解决"Java heap OOM 时进程状态已经不稳定"的问题，不依赖 `ApplicationExitInfo`：

```text
主进程 Java heap 接近阈值（连续 N 次超过 heapThreshold）
  → KOOM HeapOOMTracker 连续检测
  → SuspendVM（暂停 ART 虚拟机）
  → fork() 子进程（copy-on-write，冻结时间 < 20ms）
  → ResumeVM
  → 子进程执行 hprof dump
  → ForkStripHeapDumper 裁剪 Hprof（二进制截断 system heap）
  → 上报
  → 子进程退出
```

这个模式在 Android 5.0 (API 21) 起可用，不依赖 `ApplicationExitInfo`，是 Android 低版本 OOM 现场保留的优先方案。

### 12.6 版本能力对比

| 能力 | < API 21 | API 21-28 | API 29 | API 30+ |
|------|---------|---------|--------|---------|
| ApplicationExitInfo | ❌ | ❌ | ❌ | ✅ |
| Signal Handler 捕获 native crash | ✅ | ✅ | ✅ | ✅ |
| LMK 退出原因查询 | ❌ | ❌ | ❌ | ✅ (`getHistoricalProcessExitReasons` + `REASON_LOW_MEMORY`) |
| /data/anr/ 读取 | ❌ | ❌ | ❌ | ❌ (仍不可读) |
| strace 监控 | 需 root | 需 root | 需 root | 需 root |
| KOOM fork-dump | ✅ | ✅ | ✅ | ✅ |

**推荐策略**：
- API 30+：优先使用 `ApplicationExitInfo`
- API 21-29：Signal Handler 覆盖 native crash；KOOM fork-dump 覆盖 Java OOM；ANR 和 LMK 主要靠下次启动补拉
- < API 21：同 API 21-29，KOOM 可能需要额外适配


---

## 13. 版本能力补充：Android 线上诊断能力总览

*关联章节：§26.5、§26.2*

### 13.1 ApplicationExitInfo 版本行为差异

| API Level | ANR Trace | Native Tombstone | 备注 |
|-----------|-----------|------------------|------|
| 30 | `getTraceInputStream()` ✅ | ❌ | 仅 Java ANR trace |
| 31+ | ✅ | ✅ (`tombstone.proto`) | `REASON_CRASH_NATIVE` 返回 protobuf |

关键源码路径：
- `frameworks/base/core/java/android/app/ApplicationExitInfo.java`
- `system/core/debuggerd/tombstone_proto.cc`

### 13.2 ProfilingManager（API 35+）

Android 15 引入 `ProfilingManager.requestProfiling()`，支持 App-driven profiling：

**关键方法**：
```java
public void requestProfiling(
    int profilingType,        // PROFILING_TYPE_SYSTEM_TRACE | PROFILING_TYPE_JAVA_HEAP_DUMP | PROFILING_TYPE_HEAP_PROFILE | PROFILING_TYPE_STACK_SAMPLING
    Bundle options,
    String tag,
    CancellationSignal signal,
    Executor executor,
    Consumer<ProfilingResult> resultCallback
)
```

**结果获取**：
```java
ProfilingResult#getResultFilePath()  // trace 文件路径
ProfilingResult#getErrorCode()       // ERROR_NONE 或失败错误码
```

关键限制：
- Rate limiter 存在（结果去重、频率控制）
- 连续 profiling 类型建议提前开始、及时取消
- 结果文件路径由系统管理，应用只读

源码路径：`packages/modules/Profiling/framework/java/android/os/ProfilingManager.java`（Mainline 模块，不在 `frameworks/base/`）

### 13.3 ProfilingTrigger（API 36+）

Android 16 引入 `ProfilingTrigger` 事件触发采集：

**Trigger 类型**（按 API 版本分层）：

API 36：
- `TRIGGER_TYPE_APP_FULLY_DRAWN`：app 报告首帧完成并可交互
- `TRIGGER_TYPE_ANR`：ANR 发生时

API 36.1：
- `TRIGGER_TYPE_APP_REQUEST_RUNNING_TRACE`：app 请求运行时 trace
- `TRIGGER_TYPE_KILL_FORCE_STOP` / `TRIGGER_TYPE_KILL_RECENTS` / `TRIGGER_TYPE_KILL_TASK_MANAGER`：用户主动停止、移出最近任务或任务管理器停止触发

API 37 (Android 17)：
- `TRIGGER_TYPE_OOM`：OOM 发生时
- `TRIGGER_TYPE_COLD_START`：冷启动时
- `TRIGGER_TYPE_KILL_EXCESSIVE_CPU_USAGE`：CPU 过量使用时
- `TRIGGER_TYPE_ANOMALY`：系统异常检测触发时
- `TRIGGER_TYPE_APP_COMPAT`：应用兼容性异常场景触发时
- `TRIGGER_TYPE_APP_FULLY_DRAWN`：应用绘制完成时可交互
- `TRIGGER_TYPE_APP_REQUEST_RUNNING_TRACE`：应用请求运行时 trace
- `TRIGGER_TYPE_KILL_FORCE_STOP` / `TRIGGER_TYPE_KILL_RECENTS` / `TRIGGER_TYPE_KILL_TASK_MANAGER`：用户主动停止、移出最近任务或任务管理器停止触发

**使用模式**：
```java
// 注册触发器：通过 addProfilingTriggers 批量添加
val triggers = listOf(
    ProfilingTrigger.Builder(ProfilingTrigger.TRIGGER_TYPE_ANR)
        .setRateLimitingPeriodHours(1)
        .build()
)
profilingManager.addProfilingTriggers(triggers)

// 接收结果：通过 registerForAllProfilingResults 注册回调
profilingManager.registerForAllProfilingResults(executor) { result ->
    // 处理 profiling 结果
}
```

源码路径：`packages/modules/Profiling/framework/java/android/os/ProfilingTrigger.java`、`packages/modules/Profiling/framework/java/android/os/ProfilingManager.java`

### 13.4 Android 10-17 线上诊断能力版本表

| 能力 | Android 10 (API 29) | Android 11-14 (API 30-34) | Android 15 (API 35) | Android 16-17 (API 36-37) |
|------|---------------------|----------------------------|---------------------|----------------------|
| 退出原因查询 | ❌ | `getHistoricalProcessExitReasons()` ✅ | ✅ | ✅ |
| ANR Trace | App 内不可读 `/data/anr` | `ApplicationExitInfo#getTraceInputStream()` ✅ | ✅ | ✅ |
| Native Tombstone | ❌ | API 31+ 通过 `REASON_CRASH_NATIVE` 返回 protobuf ✅ | ✅ | ✅ |
| App-driven Profiling | ❌ | ❌ | `ProfilingManager` ✅ | ✅ |
| Trigger-based Profiling | ❌ | ❌ | ❌ | `ProfilingTrigger` ✅ |
| 系统 trace 路径 | Perfetto / bugreport | Perfetto / bugreport + `ApplicationExitInfo` | `ProfilingManager` + Perfetto | trigger-based profiling + Perfetto |

### 13.5 Native Crash Signal Handler 边界

- Signal handler 必须是 async-signal-safe：不能调用 `malloc`/`free`、不能使用锁、不能分配内存
- Crashpad Linux/Android client 使用 out-of-process handler 模型：客户端和 handler 通过 socket 注册；崩溃时 signal handler 把异常信息位置发给 handler，由 handler 抓取进程状态并写 minidump。
- `sigaction()` 设置 `SA_SIGINFO` 获取 signal number 和 siginfo_t 地址

源码/文档锚点：
- Crashpad Overview Design：Linux/Android registration 与 crash capture 流程
- `bionic/libc/include/signal.h`

<!-- AIW-源码调研-2026-05-15 -->
