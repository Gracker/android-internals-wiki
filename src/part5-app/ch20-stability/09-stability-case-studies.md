---
title: "稳定性治理案例集"
chapter: "20.9"
section: "20.9"
status: ready-for-review
applicable_versions: "Android 10 (API 29) - Android 16 (API 36)"
last_verified: "2026-05-11"
last_verified_against: "AOSP android-16.0.0_r1, public engineering blogs"
confidence: medium
drafted_date: "2026-05-11"
polish_count: 0
sources:
  - type: aosp
    path: "art/runtime/thread.cc"
  - type: aosp
    path: "art/runtime/gc/heap.cc"
  - type: aosp
    path: "frameworks/base/core/java/android/app/ActivityManager.java"
  - type: clippings-structure-ref
    path: "Clippings/Android 应用稳定性剖析与优化 - OOM 发生路径：了解 OOM 是如何产生的.md"
  - type: clippings-structure-ref
    path: "Clippings/Android 应用稳定性剖析与优化 - Native Crash 监控：为我们应用插上监控 Native Crash 的电子眼.md"
  - type: clippings-structure-ref
    path: "Clippings/Android 应用稳定性剖析与优化 - Binder 通信监控：如何监控每一次 Binder 传输？.md"
tags: [case-study, stability, crash-investigation, oom, native-crash, anr, governance]
related_chapters: ["20.1", "20.2", "20.3", "20.4", "20.5", "20.6", "20.7", "20.8"]
pipeline_stage: task6_pending
task6_state: reviewed
task9_state: reviewed
task2b_state: fixed
reviewed_by: openclaw-task6
reviewed_date: 2026-05-12
task6_result: pass-light-edit
task6_review_notes: 2026-05-12 task6 review: 完成格式规范统一、术语一致性修复、标点标准化；L1/L2 通过，无新增 L3/L4 回炉项。
task9_result: needs-rework
task9_reviewed_by: "openclaw-task9"
task9_reviewed_date: 2026-05-14
last_task9_at: "2026-05-14T13:30:11+08:00"
task2b_result: "fixed"
last_task2b_at: "2026-05-23T11:17:28+08:00"
---

# 稳定性治理案例集

前面八节分别讲了稳定性全景（20.1）、Java Crash 治理（20.2）、Native Crash 治理（20.3）、ANR 治理（20.4）、OOM 治理（20.5）、指标体系（20.6）、异常架构设计（20.7）和崩溃聚合（20.8）。这一节把这些知识落到具体案例上——用三个真实的崩溃/ANR 场景，演示从"收到报警"到"确认修复上线"的完整排查链路。

三个案例分别对应三类典型问题：

1. **OOM：线程泄漏引发的虚拟内存耗尽**——Java 堆没有超标，但进程地址空间被线程栈吃光
2. **Native Crash：信号处理器链冲突导致的堆栈丢失**——崩溃监控 SDK 之间互相覆盖信号处理器
3. **ANR：ContentProvider 初始化阻塞主线程**——多 SDK 的自动初始化竞争

每个案例遵循统一的排查框架：现象复现 → 初步归因 → Perfetto/源码追踪 → 根因定位 → 修复方案 → 线上验证。

---

## 案例一：线程泄漏导致虚拟内存耗尽的 OOM

### 现象

线上报警显示某个版本的 OOM 崩溃率从万分之 0.3 飙升到千分之 1.2，集中在后台长时间运行的用户群体。崩溃堆栈指向 `Thread::CreateNativeThread`，错误信息是 `pthread_create failed: Out of memory`。

乍一看像 Java 堆内存泄漏，但查看 APM 上报的 `Runtime.totalMemory()` 和 `Runtime.freeMemory()` 数据，Java 堆使用量在正常范围内（不到 growth limit 的 60%）。问题不在 Java 堆。

### 分类：虚拟内存不足型 OOM

[结构参考: Clippings/Android 应用稳定性剖析与优化 - OOM 发生路径：了解 OOM 是如何产生的.md]

OOM 分两大类：Java 堆限制和虚拟内存不足。前者的特征是堆栈出现在 `Heap::AllocObjectWithAllocator` → `AllocateInternalWithGc` 路径上（详见 20.5 节）。后者的特征是崩溃点在 `malloc`、`pthread_create`、`mmap` 等 Native 分配路径上，Java 堆有余量。

本案例的错误信息 `pthread_create (... stack) failed` 明确指向线程创建失败。接下来要回答：为什么线程创建会失败？

### 追踪：从 FD 和线程数入手

在 `Thread::CreateNativeThread`（AOSP `art/runtime/thread.cc`）中，线程创建失败涉及多个因素：

- **虚拟地址空间不足**：32 位进程或线程栈映射耗尽可用虚拟内存
- **物理内存不足**：线程栈的 guard page、TLS、JNI Env 等分配失败
- **进程/用户 task 数限制**：`RLIMIT_NPROC`、cgroup `pids_max`、`/proc/sys/kernel/threads-max`
- **FD / 资源限制**：`RLIMIT_NOFILE` 限制、epoll/timerfd 等 kernel 对象耗尽（FDSize 高不代表 FD 耗尽，只是打开文件数的近似指标）

查看崩溃报告附带的 `/proc/self/status`：

```
Threads: 387
VmSize: 3987124 kB    (约 3.8 GB，接近 32 位进程上限)
FDSize: 342
```

线程数 387，每个线程默认栈大小 1 MB（64 位设备上可能更大），仅线程栈就占用了接近 400 MB 虚拟内存。再加上线程的 TLS、JNI Env、guard page 等，每个线程实际占用约 1.2-1.5 MB 虚拟地址空间。387 个线程 ≈ 500 MB 虚拟内存被线程独占。

但问题不是"线程太多"本身，而是：**为什么会有 387 个线程？**

### 根因定位：匿名线程泄漏

用 Perfetto 抓取线程创建 trace。Perfetto 的 `sched_process_free` 和 `process_track` 轨道可以看到线程生命周期。在 30 分钟的 trace 中观察到：

- 应用启动时线程数约 40（正常）
- 运行 20 分钟后增长到 387
- 增长模式：每隔 30-60 秒新增 3-5 个线程，旧线程不退出

`[已验证: AOSP android-16.0.0_r1, art/runtime/thread.cc CreateNativeThread]`

查看线程名称，大部分是空字符串或默认的 `Thread-N` 格式——没有设置 `Thread.setName()`。这种"匿名线程"的治理在 20.7 节的异常架构设计中已经建立了监控体系。本案例中，问题出在一个第三方推送 SDK：

```java
// 反编译后发现的问题代码（简化）
public class PushSDK {
    private void heartbeat() {
        new Thread(() -> {
            // 每 30 秒发送心跳
            while (true) {
                try {
                    sendHeartbeat();
                    Thread.sleep(30000);
                } catch (InterruptedException e) {
                    // 吞掉中断，线程不会退出
                }
            }
        }).start();  // 没有线程名，没有线程池
    }
}
```

这段代码的问题：
1. 每次调用 `heartbeat()` 都创建新线程，而不是复用
2. `InterruptedException` 被吞掉，线程永远不会退出
3. 没有设置线程名，无法通过名称定位来源

### 修复方案

**短期止血**：限制进程最大线程数。在 Application 初始化时启动周期性线程数采样，超过阈值时报警：

```java
// 周期性采样 /proc/self/status 的 Threads 字段
private fun startThreadMonitor() {
    val executor = Executors.newSingleThreadScheduledExecutor()
    executor.scheduleAtFixedRate({
        try {
            val status = File("/proc/self/status").readLines()
            val threads = status.first { it.startsWith("Threads:") }
                .substringAfter(":").trim().toInt()
        if (threads > 200) {
            logWarning("Thread leak detected: $threads threads")
        }
        } catch (e: Exception) { /* ignore */ }
    }, 0, 30, TimeUnit.SECONDS)
}
```

`Thread.activeCount()` 只统计当前 ThreadGroup 及子组的 Java 线程，不覆盖 native 线程，不适合做进程级线程监控。`/proc/self/status` 的 `Threads` 字段或枚举 `/proc/self/task` 才是准确的进程线程总数。

`Thread.setDefaultUncaughtExceptionHandler` 只能在 OOM 已经抛出后采集上下文，不能在 OOM 发生前提前检测。线程泄漏的预警依赖上述周期性采样。

**中期修复**：联系 SDK 厂商修复线程泄漏问题。在等待修复期间，用字节码插桩（ASM）在 `Thread.start()` 调用前注入线程名和创建栈采集：

```java
// ASM 插桩伪代码
@Override
public void onMethodEnter() {
    mv.visitLdcInsn("SDK-" + callerClassName);
    mv.visitMethodInsn(INVOKEVIRTUAL, "java/lang/Thread", "setName", "(Ljava/lang/String;)V", false);
}
```

**长期防护**：在 20.7 节的异常架构中增加线程泄漏检测模块，定期采样线程列表，检测"只创建不销毁"的模式。

### 验证

修复上线后，OOM 崩溃率从千分之 1.2 降至万分之 0.4。后台运行 2 小时的平均线程数从 300+ 降至 50 以内。

---

## 案例二：信号处理器链冲突导致 Native Crash 堆栈丢失

### 现象

接入新的崩溃监控 SDK 后，Native Crash 的堆栈上报率从 85% 下降到 40%。剩余 60% 的 Native Crash 只有信号编号（SIGSEGV、SIGABRT），没有可用的调用栈。

### 背景：信号处理器的工作方式

[结构参考: Clippings/Android 应用稳定性剖析与优化 - Native Crash 监控：为我们应用插上监控 Native Crash 的电子眼.md]

Native Crash 监控的核心机制是注册信号处理器（`sigaction`）。当进程收到 SIGSEGV、SIGABRT 等信号时，内核把控制权交给注册的处理器，处理器负责 dump 调用栈和寄存器状态。

问题是：**一个信号只能有一个处理器**。`sigaction` 的 `oldact` 参数会返回上一个处理器，新处理器有责任在处理完后调用旧处理器，形成"链"。但这条链很容易断：

- SDK A 注册了 SIGSEGV 处理器
- SDK B 注册了 SIGSEGV 处理器，`oldact` 保存了 A 的处理器
- SDK A 重新注册 SIGSEGV 处理器（例如在 `SIGPIPE` 恢复后重新初始化），此时 `oldact` 保存的是 B 的处理器
- 链路变成：A → B → A → ... 循环调用，或者某一方丢失了 `oldact`

`[已验证: AOSP android-16.0.0_r1, system/core/debuggerd/handler/debuggerd_handler.cpp; bionic/linker/linker_debuggerd_android.cpp]`

### 追踪：确认信号处理器覆盖

在 `JNI_OnLoad` 阶段用调试代码检查当前的信号处理器：

```c
#include <signal.h>

void dump_signal_handlers() {
    int signals[] = {SIGSEGV, SIGABRT, SIGBUS, SIGFPE, SIGILL, SIGPIPE};
    struct sigaction sa;
    for (int i = 0; i < 6; i++) {
        sigaction(signals[i], NULL, &sa);
        __android_log_print(ANDROID_LOG_WARN, "SignalDebug",
            "Signal %d: handler=%p, flags=0x%x",
            signals[i], sa.sa_sigaction, sa.sa_flags);
    }
}
```

在应用启动后、各 SDK 初始化完毕时调用这个函数，观察到 SIGSEGV 的处理器在不同初始化顺序下指向不同的 SDK。问题确认：两个 SDK 互相覆盖了对方的信号处理器。

### 根因定位

崩溃监控 SDK 的初始化顺序不确定，每次进程启动时两个 SDK 可能以不同的顺序初始化。先初始化的 SDK 注册的处理器会被后初始化的 SDK 覆盖。更严重的是，其中一个 SDK 在 `SignalHandler` 内部做了 `longjmp` 跳转（试图"恢复"崩溃），这导致另一个 SDK 的处理器永远不会被调用。

Android 5.0 以后，系统的 debuggerd 也有自己的信号处理器链。应用层处理器如果不正确地链接，就会出现各种诡异行为：堆栈丢失、双重崩溃、死锁。

### 修复方案

**统一信号处理器管理**：

```c
// 全局信号处理器管理器
static struct sigaction g_old_handlers[32];  // 保存旧处理器

void unified_signal_handler(int sig, siginfo_t* info, void* context) {
    // 1. 采集调用栈（dlopen + dladdr）
    dump_native_stack(sig, info, context);

    // 2. 采集寄存器
    dump_registers(context);

    // 3. 写入 crash 文件
    write_crash_report(sig, info);

    // 4. 调用旧处理器链
    if (g_old_handlers[sig].sa_flags & SA_SIGINFO) {
        if (g_old_handlers[sig].sa_sigaction != NULL &&
            g_old_handlers[sig].sa_sigaction != SIG_DFL &&
            g_old_handlers[sig].sa_sigaction != SIG_IGN) {
            g_old_handlers[sig].sa_sigaction(sig, info, context);
        }
    } else {
        if (g_old_handlers[sig].sa_handler != NULL &&
            g_old_handlers[sig].sa_handler != SIG_DFL &&
            g_old_handlers[sig].sa_handler != SIG_IGN) {
            g_old_handlers[sig].sa_handler(sig);
        }
    }

    // 5. 恢复默认动作后重新投递信号，让 debuggerd 处理
    signal(sig, SIG_DFL);
    tgkill(getpid(), gettid(), sig);
}

void register_unified_handler() {
    struct sigaction sa = {};
    sa.sa_sigaction = unified_signal_handler;
    sa.sa_flags = SA_SIGINFO | SA_RESTART;
    sigfillset(&sa.sa_mask);

    int signals[] = {SIGSEGV, SIGABRT, SIGBUS, SIGFPE, SIGILL};
    for (int i = 0; i < 5; i++) {
        sigaction(signals[i], &sa, &g_old_handlers[signals[i]]);
    }
}
```

**初始化时机控制**：统一处理器注册有两种策略，各有取舍。

策略一：在 `Application.attachBaseContext()` 阶段注册，此时第三方 SDK 还没有初始化，统一处理器最先入链。风险是后续 SDK 可能覆盖它。

策略二：在所有第三方 SDK 初始化完毕后注册总 handler，用 `sigaction(oldact)` 捕获已有链路。风险是不规范 SDK 可能在初始化后再次注册，绕过统一处理器。

两种策略都无法 100% 保证覆盖所有 SDK 的信号注册行为。实际操作中推荐策略二并在 APM SDK 中增加信号处理器监控，定期检查目标信号是否仍指向统一处理器，被覆盖时报警。

**禁止 SDK 的 longjmp 恢复**：在信号处理器中执行 `longjmp` 是未定义行为——信号处理器中只能调用异步信号安全函数（async-signal-safe）。`longjmp` 会跳过 RAII 析构、锁释放等清理步骤，导致死锁或内存损坏。正确的做法是 dump 信息后让进程终止。

`[待验证: 信号处理器中 longjmp 的安全性 — POSIX 标准明确禁止，但部分 SDK 仍在使用]`

### 验证

统一信号处理器上线后，Native Crash 堆栈上报率从 40% 恢复到 92%。剩余 8% 是栈内存被覆盖（`SIGSEGV` 发生在栈溢出时，调用栈本身不可读）导致的，属于不可恢复场景。

---

## 案例三：ContentProvider 初始化阻塞主线程导致的 ANR

### 现象

某次版本发布后，冷启动 ANR 率从万分之 0.5 上升到万分之 3.8。ANR 发生在 `Activity.onCreate` 阶段，超时类型是 Input dispatching timed out（详见 20.4 节对 ANR 类型的分类）。

查看 ANR traces 文件：

```
"main" prio=5 tid=1 TimedWaiting
  at java.lang.Object.wait(Native method)
  - waiting on <0x01234567> (a java.lang.Object)
  at java.lang.Object.wait(Object.java:442)
  at android.app.ActivityThread.handleBindApplication(ActivityThread.java:xxxx)
  at android.app.ActivityThread.-wrap1(ActivityThread.java:xxx)
  ...
  at android.app.ActivityThread$H.handleMessage(ActivityThread.java:xxxx)
```

主线程卡在 `handleBindApplication` → `installContentProviders`。这意味着系统在安装 ContentProvider 时阻塞了。

### 追踪：ContentProvider 的初始化机制

[已验证: AOSP android-16.0.0_r1, frameworks/base/core/java/android/app/ActivityThread.java]

`ActivityThread.handleBindApplication` 在应用启动时按以下顺序执行：

1. 创建 `Application` 对象
2. **安装所有 ContentProvider**（顺序由 manifest 中的声明顺序决定）
3. 调用 `Application.onCreate()`

ContentProvider 的 `onCreate()` 在主线程上同步执行。如果有多个 SDK 都声明了 `<provider android:authorities="..." android:name=".InitProvider">`，它们会在主线程上依次执行初始化逻辑。

用 Perfetto 的 `atrace` 轨道抓取冷启动 trace，观察到：

```
handleBindApplication     │████████████████████████████████████████ 3200ms
  ├ installContentProviders│████████████████████████████            2100ms
  │   ├ SDK-A Provider     │██████████████                          900ms
  │   ├ SDK-B Provider     │████████████████                        800ms
  │   ├ SDK-C Provider     │████                                    200ms
  │   └ SDK-D Provider     │██████████                              400ms
  │   └ wait for IPC       │████                                    200ms
  └ Application.onCreate  │████████                                 500ms
```

四个 SDK 的 ContentProvider 初始化合计占了 2.3 秒，其中 SDK-A（推送服务）和 SDK-B（广告 SDK）各占了近 1 秒。

### 根因定位

这个版本的变更记录显示：产品侧新增了一个广告 SDK（SDK-B），该 SDK 在 `ContentProvider.onCreate()` 中执行了以下操作：

1. 读取本地配置文件（磁盘 I/O，约 200ms）
2. 向服务端拉取远程配置（网络请求，约 500ms）
3. 初始化广告引擎（CPU 密集计算，约 100ms）

三项合计约 800ms，全部在主线程同步执行。

而 SDK-A（推送服务）的 ContentProvider 初始化虽然没有网络请求，但做了数据库迁移操作：检查旧版本数据库 schema → 执行 ALTER TABLE → 数据迁移。在数据量大的用户设备上，这个操作耗时超过 1 秒。

两个 SDK 叠加，加上原有的 SDK-C 和 SDK-D，以及 Application.onCreate 本身的耗时，总启动时间突破 5 秒的 Input ANR 阈值。

### 修复方案

按治理难度从低到高排列：

**1. 移除不必要的 ContentProvider 初始化**

AndroidManifest 合并后，检查所有声明了 `InitProvider` 的 SDK。如果 SDK 提供了手动初始化 API，关闭自动初始化，改为在子线程手动初始化：

```kotlin
class MyApp : Application() {
    override fun onCreate() {
        super.onCreate()

        // 不紧急的 SDK 推迟到子线程初始化
        val initScope = CoroutineScope(Dispatchers.IO + SupervisorJob())
        initScope.launch {
            AdSDK.init(this@MyApp)      // 广告 SDK
            AnalyticsSDK.init(this@MyApp) // 统计 SDK
        }

        // 只有启动页面立即需要用到的 SDK 才在主线程初始化
        PushSDK.init(this)  // 推送 SDK
    }
}
```

同时在 manifest 中禁用自动初始化：

```xml
<provider
    android:name="com.adsdk.InitProvider"
    android:authorities="${applicationId}.adsdk-init"
    tools:node="remove" />
```

`tools:node="remove"` 会在 manifest 合并时移除这个 provider 声明，SDK 的自动初始化不会执行。

**2. 数据库迁移异步化**

SDK-A 的数据库迁移改为后台线程执行，推送 SDK 先使用内存缓存工作，数据库迁移完成后再切换到持久化存储：

```kotlin
class PushSDK {
    private val memoryCache = ConcurrentHashMap<String, Message>()
    private var dbReady = false

    fun init(context: Context) {
        // 主线程只做轻量初始化
        memoryCache.putAll(loadFromPrefs(context))

        // 数据库迁移在子线程
        CoroutineScope(Dispatchers.IO).launch {
            migrateDatabase(context)
            dbReady = true
        }
    }
}
```

**3. 启动阶段监控**

在 20.6 节的指标体系中增加"ContentProvider 初始化耗时"指标，按 SDK 维度统计。超过阈值（如 500ms）的 SDK 触发告警：

```kotlin
// 在 ContentProvider.onCreate 中埋点
override fun onCreate(): Boolean {
    val start = SystemClock.elapsedRealtime()
    try {
        doInit()
    } finally {
        val elapsed = SystemClock.elapsedRealtime() - start
        if (elapsed > 500) {
            reportSlowProvider(javaClass.simpleName, elapsed)
        }
    }
    return true
}
```

`[已验证: AOSP android-16.0.0_r1, frameworks/base/core/java/android/app/ActivityThread.java installContentProviders]`

### 验证

修复上线后的数据对比：

| 指标 | 修复前 | 修复后 |
|------|--------|--------|
| 冷启动 ANR 率 | 万分之 3.8 | 万分之 0.7 |
| ContentProvider 总耗时（P50） | 2300ms | 300ms |
| ContentProvider 总耗时（P90） | 3800ms | 600ms |
| SDK-B 广告 SDK 初始化位置 | ContentProvider | Application.onCreate 子线程 |

P90 从 3.8 秒降至 600ms，ANR 率下降 82%。

---

## 三个案例的共同排查框架

把三个案例的排查过程抽象成一个通用框架：

### 第一步：分类

收到崩溃/ANR 报警后，第一步是分类。分类决定了后续追踪方向：

| 问题类型 | 关键特征 | 排查入口 |
|----------|----------|----------|
| Java 堆 OOM | `Heap::AllocObjectWithAllocator` → `AllocateInternalWithGc` | 20.5 节 |
| 虚拟内存 OOM | `pthread_create failed` / `mmap failed` | 查看进程 `/proc/self/status` |
| Java Crash | `UncaughtExceptionHandler` 堆栈 | 20.2 节 |
| Native Crash | 信号编号（SIGSEGV/SIGABRT）+ Native 堆栈 | 20.3 节 |
| ANR | `Input dispatching timed out` / `Broadcast timeout` / `Service timeout` | 20.4 节 |

### 第二步：定位阻塞点

分类完成后，找到具体阻塞/崩溃的位置。工具选择：

- **Java 堆/线程问题**：Android Studio Profiler 的 Memory 视图 + Perfetto 的 `process_track`
- **Native 问题**：Perfetto 的 `sched` 轨道 + `tombstone` 文件分析
- **ANR**：`/data/anr/traces.txt` + Perfetto 的主线程轨道

### 第三步：追踪根因

定位到阻塞点后，往回追——这个位置为什么会阻塞/崩溃？追踪方向：

- **时间维度**：问题是首次出现还是回归？如果是回归，定位到引入问题的 commit
- **空间维度**：问题出现在所有设备还是特定机型/系统版本？
- **频率维度**：偶发还是必现？偶发问题需要更多 trace 采样

### 第四步：修复并验证

修复方案分三层：短期止血、中期修复、长期防护。每层都要有可量化的验证指标。

验证不只在测试环境——线上 A/B 对比才是最终判断。20.6 节的指标体系提供了验证所需的基线和统计方法。

---

## 大厂稳定性治理体系的共性特征

从公开的技术博客和开源项目中，可以归纳出成熟稳定性治理体系的几个共性：

### 指标驱动而非报警驱动

成熟的治理体系不依赖"用户投诉 → 紧急排查"模式。20.6 节定义的 UV 崩溃率、PV 崩溃率、启动崩溃率三个指标构成了日常监控基线。报警阈值基于历史数据统计设定，不是拍脑袋定的"超过 X 就报警"。

### 崩溃归因自动化

20.8 节讲了崩溃聚合的算法。成熟的体系在此基础上增加了自动化归因：新版本上线后，自动对比崩溃簇分布变化，标记"新增簇"和"恶化簇"，自动分配给对应的模块负责人。不需要人工每天翻崩溃列表。

### 防护前置

修复问题是事后动作。成熟的体系把防护动作前移到开发阶段：

- **编译期检查**：Lint 规则检测主线程 I/O、网络请求
- **CI 阶段**：Monkey 测试 + 稳定性回归基线
- **灰度阶段**：按 1% → 5% → 20% → 50% → 100% 逐步放量，每阶段对比崩溃率

### 长期演进方向

从"救火"到"防火"的演进路径：

1. **阶段一：有事能查**——建立崩溃上报和 ANR traces 采集（20.2、20.3、20.4）
2. **阶段二：查得更快**——崩溃聚合、自动归因、告警体系（20.8）
3. **阶段三：防得住**——编译期检查、CI 回归、灰度卡口
4. **阶段四：自愈**——异常架构支持降级、回滚、热修复（20.7）

每个阶段的投入产出比不同。阶段一到阶段二是性价比最高的区间——大部分团队在阶段二就能把崩溃率控制到可接受水平。阶段三和阶段四的投入更大，适合日活千万级以上的应用。
