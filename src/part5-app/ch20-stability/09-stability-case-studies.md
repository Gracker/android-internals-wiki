---
title: "稳定性治理案例集"
chapter: "20.9"
section: "20.9"
status: finalized
applicable_versions: "Android 10 (API 29) - Android 17 (API 37)"
last_verified: "2026-07-07T13:10:07+08:00"
last_verified_against: "AOSP android-17.0.0_r1 debuggerd_handler/linker_main/Process.java/ActivityThread/ComputerEngine；task9 2026-07-07 Android 17 boundary auto-fix"
confidence: high
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
pipeline_stage: ready-to-publish
task6_state: reviewed
task9_state: reviewed
task2b_state: fixed
task2b_result: fixed
reviewed_by: openclaw-task6
reviewed_date: "2026-05-28"
task6_result: pass-light-edit
task6_review_notes: 2026-07-07 Task6 复审：pass-light-edit。L1 修正 12 处禁用词（5×链路→路径/调用链, 4×可以看到→会看到/能观察到/存在, 3×问题是→核心疑问是/直接删除/本身）。无 L3/L4 回炉项。Task9 result 为 auto-fixed，需 Task9 最终确认。 | 2026-05-28 Task6：Task9/Task2B 回流后写作复审通过；L1/L2 小修 6 处；无 L3/L4 回炉项，送 Task9 复核。
task9_result: auto-fixed
task9_reviewed_by: "openclaw-task9"
task9_reviewed_date: "2026-07-07"
last_task9_at: "2026-07-07T13:10:07+08:00"
last_task9_audit: "2026-07-06"
last_task2b_lite_at: "2026-07-06"
last_task2b_verifier_at: "2026-05-27T23:28:16+08:00"
task2b_verifier_note: "queue 无 pending 且正文充分，回流 Task6 复审；仅修正状态流转。"
last_task9_autofix_at: "2026-07-07"
last_task9_review_log: "logs/deep-review/2026-07-07-13-deep-review.md"
task9_review_notes: "2026-05-28 Task9：auto-fix ContentProvider initOrder 顺序口径；发现 Native signal handler 示例在 handler 内执行 dlopen/dladdr/write_crash_report 等非 async-signal-safe 工作，已写入 queue P95。2026-05-28 Task2B：重写 handler 示例为最小 async-signal-safe 快照、altstack 注册、默认动作恢复与 re-raise，回流 Task6。 | 2026-05-28 Task9 deep-review: pass-tech-review。复核 Task6 回流后的技术口径；P0 0 / P1 0 / P2 0；queue 无 pending，自动晋升 finalized。 | 2026-07-07 Task9：auto-fix Android 17 版本边界错误；移除/改写未进入 android-17.0.0_r1 的信号线程亲和性、动态 altstack、perf_event crash 上下文、getThreadCpuTime(tid)、cgroup v2 cpu.weight 透出口径；回到 Task6 复审。"
last_task2b_at: "2026-07-06T12:50:00+08:00"
last_task2b_source: "task9-deep-tech-review (2026-07-06 re-review)"
last_task2b_priority: 95
task2b_note: "2026-07-06 Task2B 回流后，2026-07-07 Task9 auto-fix 删除未进入 android-17.0.0_r1 的信号线程亲和性、动态 altstack、perf_event crash 上下文、getThreadCpuTime(tid) 与 cgroup v2 cpu.weight 透出口径；保留虚拟内存碎片化 OOM、ContentProvider initOrder、debuggerd SA_EXPOSE_TAGBITS/MTE/GWP-ASan 等已验证内容。"
last_task6_at: "2026-05-28T03:16:00+08:00"
last_task6_audit: "2026-07-06"
last_task6_review_log: "logs/review/2026-05-28-03-review.md"
task6_l1_l2_fixes: 6
task6_l3_l4_issues: 0
finalized_date: "2026-07-06"
finalized_by: "openclaw-task9-auto-promote"
deepseek_cn_review_state: done
last_deepseek_cn_review_at: 2026-07-11
---

# 稳定性治理案例集

前面八节分别讨论了稳定性全景、Java Crash、Native Crash、ANR、OOM、指标、异常恢复和崩溃聚合。下面把这些能力放进三个排障案例。案例中的代码路径来自 Android 17 / API 37 / `android-17.0.0_r1` 与 `android17-6.18-2026-06_r6`；症状由多类线上问题组合而成，数值不代表某个项目的生产数据。

复合案例既能复现推理过程，也不会把缺少来源的改善比例当成结论。这里关心的是证据怎样排除假设、修复怎样通过反证，而非讲一个总能命中答案的故事。

三个案例覆盖：

1. `pthread_create` 失败：线程数持续增长，Java 堆仍有余量；
2. Native Crash 产物缺失：接入多个采集器后，信号处理互相干扰；
3. 启动阶段 ANR：清单合并引入的 ContentProvider 在主线程做重活。

---

## 一套可复用的排障记录

稳定性事件经常跨越 Java、Native、系统服务和内核。只保存一个堆栈，很容易把“崩溃发生的位置”误写成“资源耗尽的原因”。建议每次调查都保留下面七项：

| 项目 | 要回答的问题 | 常见误区 |
| --- | --- | --- |
| 事件定义 | Crash、ANR、OOM、系统杀进程还是主动退出？ | 把进程消失都算作 Crash |
| 影响范围 | 哪个版本、ABI、进程、设备档位、运行时长和功能开关？ | 只报事件数，不报分母 |
| 时间关系 | 变化从哪个发布、依赖升级或配置变更开始？ | 把首次观测日期当作引入日期 |
| 候选假设 | 每个假设需要什么支持证据和反证？ | 看到相关性便停止调查 |
| 决定性证据 | 哪一份 trace、退出记录、映射表或符号文件能区分假设？ | 无限制地增加采样字段 |
| 修复层级 | 止血、根因修复、预防措施分别是什么？ | 用告警阈值代替修复 |
| 验证方式 | 怎样在同一分群下证明风险下降且没有回归？ | 只比较两个总量 |

调查笔记应允许另一个工程师推翻当前结论。若结论无法被反证，它通常也无法被可靠验证。

---

## 案例一：线程泄漏与 `pthread_create` OOM

### 1. 症状不要过早定性

某版本在长时间后台运行后出现下面一类异常：

```text
java.lang.OutOfMemoryError:
pthread_create (...) failed: Try again
    at java.lang.Thread.nativeCreate(Native Method)
    at java.lang.Thread.start(Thread.java:...)
```

这段文本只证明“创建 Java 线程失败，ART 将失败转换成了 `OutOfMemoryError`”。它没有证明 Java 堆已满，也没有证明一定是虚拟地址碎片。`Try again` 通常对应 `EAGAIN`，但失败可以发生在多个层次。

先按版本、ABI、进程名、设备内存档位、进程存活时长和功能开关分群。若 32 位进程占比高，需要单列；它的虚拟地址空间约束与 64 位进程差异很大。

### 2. 从 Android 17 源码拆开失败点

Android 17 的 Java 线程创建路径可以简化为：

```text
Thread.start()
  -> ART Thread::CreateNativeThread()
     -> 分配 JNIEnvExt
     -> 调整 pthread 栈属性
     -> bionic pthread_create()
        -> mmap 栈、guard、TLS 与 Bionic 线程结构
        -> clone()
           -> Linux copy_process()
```

这个调用序列说明 `OutOfMemoryError` 是上层表现，候选原因至少有四组：

| 失败位置 | Android 17 源码行为 | 需要的证据 |
| --- | --- | --- |
| ART 分配 `JNIEnvExt` | 分配失败后抛出 `Could not allocate JNI Env` | 完整异常文本、Native 内存压力 |
| Bionic 线程映射 | `mmap` 或 guard 页 `mprotect` 失败，`__allocate_thread()` 返回 `EAGAIN` | ABI、`/proc/self/maps`、地址空洞、提交限制 |
| Bionic 调用 `clone` | `clone()` 失败，Bionic 记录 `clone failed` 并返回原始 `errno` | logcat、`errno`、task 与 pid 限制 |
| 内核创建 task | `RLIMIT_NPROC`、全局线程上限以及分配 task 结构等路径均可能失败 | `/proc/self/limits`、cgroup pids、系统内存压力 |

`art/runtime/thread.cc` 的 `Thread::CreateNativeThread()` 会先创建 `JNIEnvExt`，再调用 `pthread_create()`；失败后清理 peer 并抛出 OOM。Bionic 的 `pthread_create.cpp` 会把栈、guard、静态 TLS、`pthread_internal_t` 等放进线程映射，映射失败返回 `EAGAIN`；映射成功后才调用 `clone()`。内核锚点 `android17-6.18-2026-06_r6/kernel/fork.c` 中，`copy_process()` 对 `RLIMIT_NPROC` 和系统线程上限返回 `-EAGAIN`，其他分配步骤还可能返回 `-ENOMEM`。

所以，“线程很多”是强信号，不是单独的根因证明。

### 3. 最小证据集

发生前后的采样应使用同一个单调时钟，并至少保留：

- `/proc/self/status` 的 `Threads`、`VmSize`、`VmRSS`、`VmData`；
- `/proc/self/task` 中的 tid 数量与线程名；
- `/proc/self/maps`，32 位进程还要分析可用地址空洞，而不是只看 `VmSize`；
- `/proc/self/limits` 中的进程数、地址空间和打开文件限制；
- 设备允许读取时的 cgroup `pids.current`、`pids.max`；
- `/proc/self/fd` 的实际条目数；
- 完整异常文本、logcat 中的 Bionic 警告、进程 ABI 和存活时长。

`FDSize` 表示文件描述符表的容量，不等于当前打开的 FD 数。FD 泄漏通常不会直接让 `pthread_create()` 失败；若每个泄漏线程同时持有 socket、eventfd 或 timerfd，它才会成为同源症状。应枚举 `/proc/self/fd`，不要用 `FDSize` 代替。

`VmSize` 高、RSS 增长慢，可能来自线程栈、保留映射、共享库或其他匿名映射。要证明虚拟地址碎片，需要结合 ABI、映射区间和新线程所需的连续映射大小做 gap analysis。单条 `VmSize` 不能完成这一步。

Perfetto 的调度数据源适合观察线程何时出现、运行多久、是否退出。它不会自动给出每个 Java 线程的创建调用栈。若需要创建来源，应用或 SDK 要主动命名线程，在受控构建中记录采样后的创建栈，或通过已验证的字节码插桩采集调用点。

### 4. 用一个有意带缺陷的样例复现

下面的代码用于复现“功能被重复启动，每次都留下一个常驻线程”的模式：

```java
final class LeakyHeartbeat {
    void start() {
        new Thread(() -> {
            while (true) {
                try {
                    sendHeartbeat();
                    Thread.sleep(30_000L);
                } catch (InterruptedException ignored) {
                    // 错误示例：吞掉中断后继续循环。
                }
            }
        }).start();
    }

    private void sendHeartbeat() {
        // 模拟一次有界的网络请求。
    }
}
```

如果页面重建、账号切换或组件重连都会调用 `start()`，线程数便会阶梯式上升。线程没有名字会增加定位成本；更严重的是没有所有权、没有幂等启动、没有停止协议。仅注入线程名无法修复泄漏。

下面的修复示例把调度器作为依赖传入，保证重复 `start()` 不会创建新任务，并提供对称的停止动作：

```kotlin
class HeartbeatLoop(
    private val scheduler: ScheduledExecutorService,
    private val sendHeartbeat: () -> Unit,
) : Closeable {
    private val started = AtomicBoolean(false)

    @Volatile
    private var future: ScheduledFuture<*>? = null

    @Synchronized
    fun start() {
        if (!started.compareAndSet(false, true)) return

        future = scheduler.scheduleWithFixedDelay(
            { sendHeartbeat() },
            0L,
            30L,
            TimeUnit.SECONDS,
        )
    }

    @Synchronized
    override fun close() {
        future?.cancel(true)
        future = null
    }
}
```

这里的实例是一次性的：`close()` 后若要重新启动，应由新的所有者创建新实例，避免旧任务尚未响应中断时又调度一份。`scheduler` 应由进程级组件统一管理，线程工厂要设置可识别的名字。`sendHeartbeat()` 仍需连接、读取和总超时，并在内部处理可预期的网络异常，否则周期任务抛出异常后可能停止后续调度。取消能否中止请求，取决于网络库的取消语义。若任务属于页面或账号，所有者销毁时必须调用 `close()`。

### 5. 监控要看基线和斜率

下面的函数只读取进程线程总数，不会为采样再创建一个常驻线程：

```kotlin
fun readProcessThreadCount(): Int? {
    return try {
        File("/proc/self/status").useLines { lines ->
            lines.firstOrNull { it.startsWith("Threads:") }
                ?.substringAfter(':')
                ?.trim()
                ?.toIntOrNull()
        }
    } catch (e: IOException) {
        null
    } catch (e: SecurityException) {
        null
    }
}
```

调用方应复用已有的监控调度器。采样失败需要计数，不能静默吞掉；上报时携带进程存活时长、前后台状态、ABI 和功能分群。

固定写死“200 个线程就报警”不适用于所有应用。更有用的规则是：

- 与同进程、同设备档位的稳定基线比较；
- 同时判断绝对值和一段时间内的持续正斜率；
- 按线程名前缀统计存量、创建量和退出量；
- 为 SDK 升级与功能开关保留版本维度；
- 限制采样频率和上传量，避免监控自身放大资源压力。

### 6. 验证结论

本地长稳测试要覆盖重复进入/退出功能、账号切换、网络抖动、前后台切换和进程存活。合格条件不由“两个小时后低于某个通用数字”定义。每轮生命周期结束后，属于该功能的线程应回到稳定区间，进程总线程数不再单调增长。

线上验证要比较同一版本窗口和同一分群的：

- `pthread_create` OOM 用户率与会话率；
- 进程存活时长分桶中的线程数分位数；
- 32 位与 64 位进程的差异；
- 新旧 SDK 或功能开关的对照；
- Java heap OOM、FD 耗尽和网络失败是否出现反向回归。

---

## 案例二：多个 Native Crash 采集器互相覆盖

### 1. 症状先拆成采集阶段

接入第二个 Native Crash SDK 后，后台只收到信号编号，或收到无法符号化的地址。这个现象不能直接归因于“信号处理器冲突”。Native Crash 产物可能在四个阶段丢失：

1. 崩溃时没有生成足够的寄存器、线程和映射快照；
2. 产物写入不完整，进程已被终止；
3. Build ID、ABI 或符号文件不匹配；
4. 产物已生成，但扫描、上传、去重或服务端解析失败。

先验证 Build ID 和原始产物，再调查信号 disposition。否则，符号归档错误会被误诊为 handler 覆盖。

### 2. 信号模型中的边界

对一个进程中的某个信号，内核维护一个 disposition。后调用的 `sigaction()` 会替换前一个 disposition，并可通过 `oldact` 取回旧值。每个线程另有自己的 signal mask，因此“每个信号只有一个处理器”不能扩写成“所有线程的信号状态完全相同”。

旧 handler 也不会由系统自动组成安全的调用序列。下面几种情况会破坏采集：

- SDK B 覆盖 SDK A，却没有保留旧 disposition；
- SDK B 盲目调用旧 handler，形成递归、重复转发或次生崩溃；
- handler 内执行分配内存、加普通业务锁、动态加载、格式化复杂日志等不适合信号上下文的工作；
- 栈已损坏却没有可用的备用信号栈；
- handler 试图用 `longjmp` 恢复业务执行，继续使用已损坏的进程状态；
- SDK 拦截后没有保留系统 tombstone/debuggerd 所需的终止行为。

“保存旧 handler，再手动调用它”只是一种机制，不是通用兼容方案。采集 SDK 必须明确处理 `SIG_DFL`、`SIG_IGN`、`SA_SIGINFO`、线程 mask、重复进入和重新发送信号等状态。业务团队不要自行拼接多个闭源 SDK 的 handler。

### 3. Android 17 的 debuggerd 注册方式

在 `android-17.0.0_r1` 中，`bionic/linker/linker_main.cpp` 在 linker 初始化阶段调用 `linker_debuggerd_init()`。它是启动触发点；debuggerd 的完整处理仍位于 `system/core/debuggerd/handler/debuggerd_handler.cpp`。

`debuggerd_init()` 为伪线程预留一段 `mmap` 内存，中间 8 页可读写，前后页保留为 guard；随后注册 fatal signal handler。注册 flags 包含：

```text
SA_RESTART | SA_SIGINFO | SA_ONSTACK | SA_EXPOSE_TAGBITS
```

`SA_EXPOSE_TAGBITS` 让 arm64 MTE fault address 的 tag 信息进入诊断上下文。`SA_ONSTACK` 用于可用时的备用信号栈；不要把源码中的伪线程栈描述成“每个应用线程都动态获得了 8 页 altstack”。这两个结构用途不同。

AOSP handler 还会处理 debuggerd 私有协议、crash_dump 协作、MTE 和 GWP-ASan 等平台能力。应用侧采集器无法仅靠复制一个 `sigaction` 示例得到同等语义。

### 4. 在正常执行环境中检查覆盖

下面的代码仅用于 debuggable 集成测试，在 SDK 初始化前后读取当前 disposition；不要把它放进 crash handler：

```cpp
struct HandlerSnapshot {
  int flags;
  uintptr_t entry;
};

int SnapshotHandler(int signo, HandlerSnapshot* out) {
  struct sigaction current = {};
  if (sigaction(signo, nullptr, &current) != 0) {
    return errno;
  }

  out->flags = current.sa_flags;
  out->entry =
      (current.sa_flags & SA_SIGINFO)
          ? reinterpret_cast<uintptr_t>(current.sa_sigaction)
          : reinterpret_cast<uintptr_t>(current.sa_handler);
  return 0;
}
```

测试可以比较“初始化前、SDK A 后、SDK B 后”的进程内快照，确认谁改写了 disposition。函数地址受 ASLR 影响，只适合同一进程中的诊断；不要把地址当成跨设备标识，也不要在生产日志中上传它。

若 SDK 文档声称会兼容其他采集器，测试还要验证行为结果，不能只比较函数指针。一个 handler 可能保留了旧入口，却在错误时机或错误线程状态下调用它。

### 5. 修复策略

优先选择一个负责 fatal signal 的 Native Crash 采集器。其他 SDK 关闭 Native 捕获，只保留 Java、性能或上传能力。构建阶段维护依赖清单，记录哪些 AAR 或 `.so` 会注册 fatal signal；升级 SDK 时自动运行冲突测试。

不要在 fatal signal handler 中尝试修复业务状态、弹窗、发网络请求或继续执行。更稳妥的工作划分是：

- crash 时只做采集器设计允许的最小操作；
- 将完整解析、符号化、压缩和上传延后到下次安全启动；
- 使用 Build ID 选择准确符号，不以版本名猜测；
- 保留系统终止与 tombstone 生成路径；
- 对产物设置大小、保留期、加密和隐私字段约束。

闭源 SDK 无法说明 handler 行为时，兼容性要靠受控崩溃试验确认，不要把未知旧 handler 直接串起来。

### 6. 验证用例表

每个支持的 ABI 和主要 Android 版本至少覆盖：

| 用例 | 要验证的产物 |
| --- | --- |
| `abort()` | 信号、寄存器、线程、映射、Build ID |
| 空指针读写 | fault address、崩溃线程栈、符号 |
| 栈溢出 | 备用栈场景仍能产出可解析记录 |
| 多线程同时触发 | 只产生一个主事件，其他线程不会把产物写坏 |
| MTE 或 GWP-ASan（设备支持时） | fault 类型与平台诊断信息被保留 |
| 离线后重启 | 本地产物能被发现、去重并在网络恢复后上传 |

Android 11 / API 30 起可用 `ApplicationExitInfo` 查询历史退出原因和 trace；Android 12 / API 31 起，`REASON_CRASH_NATIVE` 的 `getTraceInputStream()` 可返回 tombstone protobuf，但记录位于有限的全局环形缓冲区，流仍可能为空。它是独立的验证面，不能替代应用采集器，也不能保证每次都有结果。

通过标准应同时覆盖应用产物、系统退出记录、符号化结果和服务端接收。缺少其中一项时，先标记具体失败阶段，不要用一个“堆栈完整率”掩盖原因。

---

## 案例三：ContentProvider 初始化拖慢启动并诱发 ANR

### 1. 为什么 Provider 会抢在 Application 前面

Android 17 的 `ActivityThread.handleBindApplication()` 在创建 `Application` 对象后，会先调用 `installContentProviders(app, data.providers)`，之后才调用 `Instrumentation.callApplicationOnCreate(app)`。

安装本地 Provider 时，`ActivityThread.installProvider()` 会实例化 Provider，并通过 `attachInfo()` 进入 `ContentProvider.onCreate()`。这段工作发生在主线程。对同一进程中的 Provider，清单属性 `android:initOrder` 数值越大，初始化越早；`installContentProviders()` 按系统传入的列表依次安装。

因此，第三方 SDK 通过清单合并加入 Provider 后，即使应用代码没有主动调用 SDK，它也可能在 `Application.onCreate()` 之前执行。进程也未必由桌面 Activity 启动：外部访问 Provider、Job、Service、Broadcast 或推送都可能触发进程创建。分析时必须带上启动原因和进程名。

### 2. 症状与候选假设

假设一次依赖升级后，冷启动尾延迟和“启动附近的 ANR”同时上升。ANR 主线程栈落在某个 SDK Provider 的 `onCreate()`，这份栈是重要证据，但仍要区分：

| 假设 | 支持证据 | 反证 |
| --- | --- | --- |
| Provider 同步磁盘 I/O | Perfetto 中主线程文件系统事件与 Provider trace section 重合 | 移除该 I/O 后时长不变 |
| Provider 等待网络或 Binder | 主线程处于 socket、futex 或 Binder 等待，服务端线程也可定位 | 离线与替身服务下现象不变 |
| 数据库打开或迁移 | SQLite section、锁等待、首次升级集中 | 全新安装与升级路径表现相同 |
| 类加载、解压或 dex 工作 | class loading、CPU 与页错误集中 | 预热或依赖裁剪后没有变化 |
| `Application.onCreate()` 自身阻塞 | 时间区间发生在 Provider 安装之后 | Provider 区间已覆盖主要耗时 |

不要把所有启动 ANR 都称为“Input dispatch 5 秒超时”。ANR 类型和超时受触发场景、组件、系统状态及版本影响。应从系统报告、Play vitals 和 trace 判断类型。普通应用也不能直接读取 `/data/anr/`；应用可用的是平台公开 API、Play/厂商后台、测试设备导出的 bugreport，以及自己埋下的轻量 trace section。

### 3. 收集启动与 ANR 证据

Android 11 / API 30 起，`ApplicationExitInfo` 可提供 `REASON_ANR` 和可能存在的 `getTraceInputStream()`。Android 17 / API 37 新增 `ApplicationExitInfo.getAnrInfo()`，只在 `REASON_ANR` 时填充，可用于获得结构化 ANR 信息；代码必须继续兼容字段为空和历史记录被覆盖。

Android 15 / API 35 起，`ApplicationStartInfo` 提供启动原因、启动类型和单调时钟时间戳。它能描述进程启动、`bindApplication`、`Application.onCreate()`、首帧等系统节点，但不会自动给出每个 Provider 的单独耗时。Provider 粒度需要 Perfetto、系统 trace 或应用自己的 `Trace` section。

下面的 Provider 示例只给自有代码加 trace 标记，用于在 Perfetto 中定位区间：

```kotlin
class DiagnosticsProvider : ContentProvider() {
    override fun onCreate(): Boolean {
        Trace.beginSection("DiagnosticsProvider#onCreate")
        return try {
            installLightweightHooks(requireNotNull(context).applicationContext)
            true
        } finally {
            Trace.endSection()
        }
    }
}
```

`installLightweightHooks()` 必须是主线程可接受的短操作。trace 标记负责测量，不会让初始化变快；section 名应稳定且数量受控，不能携带用户数据。

清单调查还要检查 Android Studio 的 merged manifest，而不是只搜索主模块的 `AndroidManifest.xml`。记录 Provider 来源依赖、authority、process、`initOrder`、是否 direct-boot aware，以及 SDK 是否提供关闭自动初始化的正式选项。

### 4. 修复要尊重 SDK 的线程约束

把所有 SDK 初始化统一扔到 `Dispatchers.IO` 会制造新的竞态。有些 SDK 要求主线程注册回调或访问 Looper；有些组件必须在首次 API 调用前完成准备。正确拆分方式取决于 SDK 文档：

- 必须同步且要求主线程的部分，压缩到最小；
- 明确支持后台执行的磁盘或解析工作，移出 Provider；
- 可延迟功能在首次使用前按需初始化；
- 调用方需要显式的 readiness，而不是读一个没有同步语义的布尔值；
- 初始化失败要有可观察状态、重试策略和降级行为；
- 用户、进程或测试生命周期结束时，能取消的任务要被取消。

下面的门闩只适用于 SDK 明确允许后台准备的部分，调用方通过 `awaitReady()` 获得一致结果：

```kotlin
class SdkReadiness(
    private val appScope: CoroutineScope,
    private val prepareOffMain: suspend () -> Unit,
) {
    private val started = AtomicBoolean(false)
    private val ready = CompletableDeferred<Unit>()

    fun start() {
        if (!started.compareAndSet(false, true)) return

        val job = appScope.launch(Dispatchers.IO) {
            try {
                prepareOffMain()
                ready.complete(Unit)
            } catch (e: CancellationException) {
                ready.cancel(e)
                throw e
            } catch (e: Exception) {
                ready.completeExceptionally(e)
            }
        }
        job.invokeOnCompletion { cause ->
            if (cause != null && !ready.isCompleted) {
                ready.completeExceptionally(cause)
            }
        }
    }

    suspend fun awaitReady() {
        ready.await()
    }
}
```

`appScope` 应由应用进程所有，并在测试中可替换；不要在 Provider 内临时创建一个无法管理的全局 scope。若 SDK 的某一步要求主线程，就把那一步留在主线程，并把可分离的工作交给后台。`CompletableDeferred` 解决等待一致性，不负责超时、重试和产品降级，这些策略要由上层定义。

若 SDK 使用 Jetpack App Startup，可按官方文档声明 initializer 依赖，或在支持时改为按需初始化。用 `tools:node="remove"` 删除第三方 Provider 前，必须确认 SDK 文档提供手动初始化入口及调用时机；直接删除可能让 SDK 悄悄失效。

数据库迁移也不能只改成“后台打开数据库”。在准备完成前，所有读取方需要等待或走受控降级；多进程场景还要处理文件锁、重复迁移和 direct boot 存储边界。

### 5. 验证修复

本地验证至少包含：

- 全新安装、覆盖升级和跨多个 schema 版本升级；
- 冷启动、温启动，以及 Provider、Service、Broadcast、Job、推送触发的进程启动；
- 主进程和独立进程；
- 低端与主流设备、不同存储压力；
- 在线、离线、弱网和依赖服务不可用；
- 初始化完成前立即调用 SDK API；
- 多个调用方同时等待和初始化失败后的行为。

Macrobenchmark 适合比较冷启动分布，Perfetto 用来确认主线程区间和等待对象，`ApplicationStartInfo` 用来对齐系统启动节点。测试结果要报告样本量和分位数，不要只贴一次录屏。

线上观察应分开看启动用户率、ANR 用户率、ANR 会话率、启动类型、启动原因、进程名、设备档位和版本。若尾延迟下降但 SDK 初始化失败率上升，修复仍不合格。

---

## 三个案例共用的判断边界

| 看到的现象 | 可以立即确认 | 仍需验证 |
| --- | --- | --- |
| `pthread_create` 抛 OOM | 线程创建失败并被 ART 转成 OOM | JNIEnv、映射、task 限制还是系统内存压力 |
| 线程数持续上升 | 有线程生命周期异常 | 哪个所有者创建、为何没有退出 |
| Native 只有地址没有符号 | 符号化结果不可用 | 采集缺失还是 Build ID / 符号归档错误 |
| 初始化 SDK 后 handler 改变 | SDK 改写了 disposition | 是否破坏旧采集器与系统 tombstone |
| ANR 栈在 Provider | 主线程采样时位于 Provider 工作 | 它是否覆盖主要阻塞区间、ANR 属于哪一类 |
| `Application.onCreate()` 很慢 | 系统节点之间存在较长区间 | Provider、类加载还是 Application 代码占用 |

调查完成前，给结论加上置信度和待反证项。修复提交中把证据、风险和回滚开关写清楚；验证阶段沿用调查时的分群和指标定义，避免统计口径改变后产生虚假的改善。

---

## 发布前检查表

- [ ] 事件数同时配有用户、会话或启动次数分母
- [ ] 版本、ABI、进程、设备档位和存活时长能够分群
- [ ] 原始异常文本、退出原因、trace 与符号版本可追溯
- [ ] 每个候选假设都有支持证据和反证
- [ ] 源码结论固定到 `android-17.0.0_r1`
- [ ] 内核结论固定到 `android17-6.18-2026-06_r6`
- [ ] 止血、根因修复与预防措施没有混写
- [ ] 示例代码有所有者、取消、超时和失败语义
- [ ] 验证使用同一分群，并检查反向回归
- [ ] 没有用虚构的线上比例证明修复成功

---

## 源码与官方资料

- [ART `Thread::CreateNativeThread()`：`runtime/thread.cc`](https://android.googlesource.com/platform/art/+/android-17.0.0_r1/runtime/thread.cc)
- [Bionic `pthread_create()`：`libc/bionic/pthread_create.cpp`](https://android.googlesource.com/platform/bionic/+/android-17.0.0_r1/libc/bionic/pthread_create.cpp)
- [Linux task 创建：`kernel/fork.c`](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/kernel/fork.c)
- [Android 17 debuggerd handler](https://android.googlesource.com/platform/system/core/+/android-17.0.0_r1/debuggerd/handler/debuggerd_handler.cpp)
- [Android 17 linker 启动入口](https://android.googlesource.com/platform/bionic/+/android-17.0.0_r1/linker/linker_main.cpp)
- [Android 17 `ActivityThread`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/app/ActivityThread.java)
- [ContentProvider 清单属性与 `initOrder`](https://developer.android.com/guide/topics/manifest/provider-element)
- [Jetpack App Startup](https://developer.android.com/topic/libraries/app-startup)
- [`ApplicationExitInfo`](https://developer.android.com/reference/android/app/ApplicationExitInfo)
- [`ApplicationStartInfo`](https://developer.android.com/reference/android/app/ApplicationStartInfo)
- [Perfetto CPU scheduling 数据源](https://perfetto.dev/docs/data-sources/cpu-scheduling)

---

## 小结

稳定性治理的难点不在于记住某个堆栈对应某个答案，而在于守住证据边界：

- `pthread_create` OOM 要沿 ART、Bionic 和内核逐层区分失败点；
- Native Crash 产物缺失要拆开采集、持久化、符号化和上传，再验证 signal handler 是否冲突；
- Provider 启动 ANR 要对齐系统启动顺序、清单合并结果、主线程 trace 和 SDK 初始化契约。

源码提供机制边界，trace 提供时间关系，线上指标提供影响范围。三者能够互相校验时，修复结论才足以进入发布流程。
