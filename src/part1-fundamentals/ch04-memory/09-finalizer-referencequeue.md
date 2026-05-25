---
title: "ART FinalizerDaemon 与 ReferenceQueue 性能边界"
chapter: "4.9"
section: "4.9"
status: "ready-for-review"
drafted_date: "2026-05-15"
drafted_by: "openclaw-task2a"
applicable_versions: "Android 8 (API 26) - Android 16 (API 36), Android 17 preview 待复核"
last_verified: "2026-05-15"
last_verified_against: "AOSP android-16.0.0_r1 libcore + Android Developers API reference + Oracle Java SE 8 ReferenceQueue API"
confidence: medium
sources:
  - type: research
    path: "/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/DeepResearch/2026-05-09-art-finalizerdaemon-referencequeue-concurrency.md"
  - type: aosp
    path: "platform/libcore/android-16.0.0_r1/ojluni/src/main/java/java/lang/ref/ReferenceQueue.java"
  - type: aosp
    path: "platform/libcore/android-16.0.0_r1/libart/src/main/java/java/lang/Daemons.java"
  - type: official
    path: "https://developer.android.com/reference/android/util/CloseGuard"
  - type: official
    path: "https://developer.android.com/reference/android/os/StrictMode"
  - type: official
    path: "https://docs.oracle.com/javase/8/docs/api/java/lang/ref/ReferenceQueue.html"
tags: ["art", "gc", "memory", "finalizer", "referencequeue", "performance"]
related_chapters: ["4.3", "4.5", "10.2", "23.1"]
created_by: "task2a-knowledge-gap"
created_date: "2026-05-15"
gap_source: "素材驱动/章节深挖"
pipeline_stage: "task2b_pending"
task2b_result: "fixed"
task2b_state: "pending"
task6_state: "revisiting"
last_task6_review_log: "logs/review/2026-05-25-05-review.md"
last_task6_at: "2026-05-25T05:08:00+08:00"
reviewed_date: "2026-05-25"
reviewed_by: "openclaw-task6"
task6_result: "pass-light-edit"
task9_state: "reviewed"
task9_reviewed_date: "2026-05-26"
task9_reviewed_by: "openclaw-task9"
last_task9_at: "2026-05-26T03:20:00+08:00"
task9_review_notes: "2026-05-26 Task9 deep-review: needs-rework。P0：延伸阅读摘要仍保留 Cleaner 旧错误路径，与正文和 AOSP android-16 口径冲突。"
last_task9_review_log: "logs/deep-review/2026-05-26-03-deep-review.md"
task9_result: "needs-rework"
task9_p0_issues: 1
task9_p1_issues: 0
task9_p2_issues: 0
task6_l1_l2_fixes: 0
task6_l3_l4_issues: 0
task6_new_rework: false
review_type: "task6-writing-quality-review"
task6_review_notes: "2026-05-25 Task6 revisiting review: pass-light-edit。L1 禁用词/高频词扫描通过，outline 锚点均有正文覆盖；正文无新增 L1/L2 小修，无新增 Task6 回炉。既有 Task9 技术问题仍在 queue pending，保持 task2b_pending。"
---
# 4.9 ART FinalizerDaemon 与 ReferenceQueue 性能边界

<!-- outline-start -->
## 要点

### 🔹 ReferenceQueue 与 FinalizerDaemon 的职责边界
区分 Java 引用队列、对象终结、ART daemon 线程和应用资源释放责任，避免把内存泄漏、终结延迟和 GC 暂停混成一个问题。

### 🔹 从 GC 标记到 finalizer 执行的路径
梳理对象进入待终结队列、FinalizerDaemon 取出并执行 finalize()、异常处理和超时监控的观察点。

### 🔹 ReferenceQueue 并发优化的版本口径
记录 Android 16/17 ART 对 ReferenceQueue / ConcurrentMessageQueue 相关优化的公开证据、源码路径和未验证边界。

### 🔹 队列堆积对内存与卡顿的影响
分析 finalizer 堆积、CloseGuard 警告、FD 泄漏、native handle 泄漏在 heap、threads、Perfetto 中的表现。

### 🔹 诊断流程与证据采集
给出 heap dump、`adb shell dumpsys meminfo`、ART log、Perfetto 线程轨道和 simpleperf 的组合观察方式。

### 🔹 工程治理边界
给出 `AutoCloseable`、显式 close、Cleaner、资源池和测试门禁的适用条件，说明 finalize() 不适合作为主释放路径。

## 扩展

### 🔸 Cleaner / CloseGuard / StrictMode 的组合使用
补充不同 API level 下可用性、误报来源和 CI 接入方式。

### 🔸 Native 资源释放与 Java wrapper 生命周期
补 JNI global ref、fd、GraphicBuffer、Bitmap native allocation 的排查模板。

<!-- outline-end -->

`finalize()`、`ReferenceQueue`、`Cleaner` 和资源泄漏经常出现在同一类问题里：内存没有降、FD 数持续涨、日志里出现 CloseGuard 警告，Trace 里还能看到 `FinalizerDaemon` 在忙。本节把这条路径拆清楚：哪些工作由 GC 和 ART 守护线程完成，哪些工作必须由应用显式释放，遇到队列堆积时该采集哪些证据。

本节的判断基于 AOSP `android-16.0.0_r1` 的 libcore 源码。结论边界也要写在前面：Android 16 的 `ReferenceQueue` 仍是带锁 FIFO 队列，未找到它接入 `ConcurrentMessageQueue` 或无锁投递路径的证据；Android 17 preview 后续还要按公开源码重新复核。

[已验证: AOSP android-16.0.0_r1, platform/libcore/ojluni/src/main/java/java/lang/ref/ReferenceQueue.java]
[已验证: AOSP android-16.0.0_r1, platform/libcore/libart/src/main/java/java/lang/Daemons.java]
[来源: /Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/DeepResearch/2026-05-09-art-finalizerdaemon-referencequeue-concurrency.md]

## ReferenceQueue 和 FinalizerDaemon 负责不同阶段

`ReferenceQueue` 只是一个引用对象队列。GC 判断某个 `Reference` 可以进入后续处理阶段后，会把它放入 pending list；`ReferenceQueueDaemon` 再把这批引用转移到对应的 `ReferenceQueue`。如果引用对应的是带 `finalize()` 的对象，后续由 `FinalizerDaemon` 取出 `FinalizerReference`，调用对象的 `finalize()`。

这几个角色不能混成一个“GC 清理资源”的动作：

- GC: 判断对象可达性，生成待处理引用列表，触发引用入队。它不负责关闭业务资源。
- `ReferenceQueueDaemon`: 把 GC 提供的 pending list 转移到 Java 层队列；对 `sun.misc.Cleaner` 类型的引用直接调用 `Cleaner.clean()`，无需经过 `FinalizerDaemon`。
- `FinalizerDaemon`: 从 `FinalizerReference.queue` 取对象，执行 `finalize()`，处理异常和超时监控。
- 应用代码: 对 FD、socket、数据库 cursor、native handle、图形 buffer 等资源执行确定性释放。

`ReferenceQueue` 在源码里用一个实例锁保护队列状态，`poll()`、`remove()`、`enqueue()` 都围绕同一个 `lock` 工作。它保证的是队列结构一致，不保证释放动作及时完成。

这段源码展示了 `ReferenceQueue` 的同步边界，重点看 `lock` 和 FIFO 头尾指针：

```java
// platform/libcore, android-16.0.0_r1
// ojluni/src/main/java/java/lang/ref/ReferenceQueue.java
private Reference<? extends T> head = null;
private Reference<? extends T> tail = null;

private final Object lock = new Object();

public Reference<? extends T> poll() {
    synchronized (lock) {
        return reallyPollLocked();
    }
}

public Reference<? extends T> remove(long timeout)
        throws IllegalArgumentException, InterruptedException {
    synchronized (lock) {
        Reference<? extends T> r = reallyPollLocked();
        if (r != null) return r;
        for (;;) {
            lock.wait(timeout);
            r = reallyPollLocked();
            if (r != null) return r;
            // Timeout handling omitted.
        }
    }
}
```

`remove()` 阻塞在队列锁上，`poll()` 走非阻塞路径。两者都只回答“有没有引用可处理”，不回答“资源是否已经释放”。把资源释放寄托给这条路径，就会把释放时机交给 GC、队列转移、守护线程调度和 `finalize()` 执行速度。

[已验证: AOSP android-16.0.0_r1, ReferenceQueue.java lines 46-51, 170-217]

## 从 GC 标记到 finalize 执行的路径

带 `finalize()` 的对象在分配/构造阶段就通过 `FinalizerReference.add()` 注册了对应的 `FinalizerReference` 链表节点（参见 `FinalizerReference.java` L33-L45）。GC 判定对象不可达后，不会重新创建引用，只是把已有 `FinalizerReference` 的 referent 置为 zombie 状态，然后挂到 `ReferenceQueue.unenqueued`。`ReferenceQueueDaemon` 再通过 `enqueuePending()` 把这批引用转移到 `FinalizerReference.queue`，`FinalizerDaemon` 才能取出并调用 `object.finalize()`。

这条路径按四段排查：

1. 对象构造时注册 `FinalizerReference`（`FinalizerReference.add()`），此时引用节点已在链表中，referent 仍指向存活对象。
2. GC 判定对象不可达，把 referent 移到 zombie，将已有引用挂到 `ReferenceQueue.unenqueued`，唤醒 `ReferenceQueueDaemon`。
3. `ReferenceQueueDaemon` 调用 `ReferenceQueue.enqueuePending()`，按队列分组批量入队。
4. `FinalizerDaemon` 从队列取出引用，调用 `object.finalize()`，完成后清掉对对象的强引用。

`FinalizerDaemon` 的运行循环用了快慢两条路径。有待处理对象时走 `queue.poll()`，少做一次 watchdog 通信；没有对象时切到 `queue.remove()` 阻塞等待，避免空闲设备被周期性唤醒。

下面的片段只保留运行循环的骨架：

```java
// platform/libcore, android-16.0.0_r1
// libart/src/main/java/java/lang/Daemons.java
private static class FinalizerDaemon extends Daemon {
    private final ReferenceQueue<Object> queue = FinalizerReference.queue;
    private final AtomicInteger progressCounter = new AtomicInteger(0);
    private Object finalizingObject = null;

    @Override public void runInternal() {
        int localProgressCounter = progressCounter.get();
        FinalizerWatchdogDaemon.INSTANCE.monitoringNeeded(
                FinalizerWatchdogDaemon.FINALIZER_DAEMON);
        while (isRunning()) {
            Object nextReference = queue.poll();
            if (nextReference != null) {
                progressCounter.lazySet(++localProgressCounter);
                processReference(nextReference);
            } else {
                finalizingObject = null;
                FinalizerWatchdogDaemon.INSTANCE.monitoringNotNeeded(
                        FinalizerWatchdogDaemon.FINALIZER_DAEMON);
                nextReference = queue.remove();
                FinalizerWatchdogDaemon.INSTANCE.monitoringNeeded(
                        FinalizerWatchdogDaemon.FINALIZER_DAEMON);
                processReference(nextReference);
            }
        }
    }
}
```

`processReference()` 遇到 `FinalizerReference` 时会取出对象并调用 `doFinalize()`。`doFinalize()` 里先把引用从 finalizer 链表移除，再调用 `object.finalize()`；如果 `finalize()` 抛异常，Android 会记录日志，而不是让异常静默消失。

这解释了一个常见现象：堆里对象已经不可达，但 native 内存或 FD 还没降。对象要经过 finalizer 执行后才可能释放资源；如果队列堆积，释放动作会继续拖后。

[已验证: AOSP android-16.0.0_r1, Daemons.java lines 295-401]

## ReferenceQueue 的并发优化边界

Android 的 `ReferenceQueue` 和 OpenJDK 的实现有一个结构差异：Android 版本在源码注释里标明是 FIFO，OpenJDK 版本是 LIFO。FIFO 让引用按入队顺序处理，更适合 Android 的对象生命周期语义；代价是队列头尾都要受同一把实例锁保护。

Android 16 的 `enqueuePending()` 已经做了批处理优化。它会把同一个 `ReferenceQueue` 的连续引用放在一次 `synchronized (queue.lock)` 里处理，并用 `MAX_ITERS = 100` 限制单次持锁时间。这个优化减少重复加锁，但没有改变“同一个队列同一时间只有一个线程修改队列”的约束。

`enqueuePending()` 的关键路径如下：

```java
// platform/libcore, android-16.0.0_r1
// ojluni/src/main/java/java/lang/ref/ReferenceQueue.java
public static void enqueuePending(Reference<?> list,
        AtomicInteger progressCounter) {
    Reference<?> start = list;
    do {
        ReferenceQueue queue = list.queue;
        if (queue == null || sun.misc.Cleaner.isCleanerQueue(queue)) {
            // Cleaner path omitted.
        } else {
            final int MAX_ITERS = 100;
            int i = 0;
            synchronized (queue.lock) {
                do {
                    Reference<?> next = list.pendingNext;
                    list.pendingNext = list;
                    queue.enqueueLocked(list);
                    list = next;
                } while (list != start
                        && list.queue == queue
                        && ++i < MAX_ITERS);
                queue.lock.notifyAll();
            }
        }
        progressCounter.incrementAndGet();
    } while (list != start);
}
```

这段实现给出三个排查结论：

- 高并发分配很多可终结对象时，排查重点通常不在“GC 有没有工作”，而在引用入队和 finalizer 执行速度是否跟得上对象产生速度。
- `queue.lock` 是每个 `ReferenceQueue` 的实例锁，不同队列之间可以分开处理，同一个队列仍可能出现竞争。
- `ConcurrentMessageQueue` 这类消息队列优化不能直接外推到 `ReferenceQueue`。在 Android 16 libcore 源码里，没有看到 `ReferenceQueue` 接入无锁队列的证据。

[已验证: AOSP android-16.0.0_r1, ReferenceQueue.java lines 236-278]
[待验证: Android 17 preview 公开源码发布后的 ReferenceQueue 实现差异]

## 队列堆积带来的内存和卡顿表现

Finalizer 堆积最容易误判成“GC 没回收”。更准确的排查对象是资源释放延迟：Java 对象已经进入 finalization 路径，但它持有的 native 资源、FD 或外部句柄还没释放。

常见表现有四类：

- FD 数上涨: `/proc/<pid>/fd` 里的文件描述符数量持续增加，日志里可能伴随 CloseGuard “A resource was acquired but never released” 类警告。
- native 内存上涨: Java heap 变化不大，`dumpsys meminfo` 里的 Native Heap、Graphics 或 Unknown 项持续上升。
- 守护线程忙: Trace 或线程 dump 里 `FinalizerDaemon` 长时间运行，`ReferenceQueueDaemon` 也可能频繁被唤醒。
- 偶发卡顿: finalizer 里执行文件、Binder、JNI 或复杂清理逻辑时，虽然不直接跑在主线程，也会争抢 CPU、触发锁等待，间接影响帧预算。

FD 泄漏的证据采集可以从最小命令开始，不要一上来只看 Java heap：

```bash
# 取目标进程 pid 后，观察 FD 数是否随操作次数单调上涨
adb shell pidof com.example.app
adb shell 'ls -l /proc/<pid>/fd | wc -l'
adb shell dumpsys meminfo com.example.app
```

如果 FD 数每轮操作后都增加，heap dump 里再去找对应 wrapper 对象才有意义。常见对象包括 `FileInputStream`、`ParcelFileDescriptor`、`CursorWindow`、`SQLiteClosable` 子类、自定义 JNI wrapper。只看到 `FinalizerDaemon` 忙，不能反推出具体泄漏源。

CloseGuard 的价值在于把“资源获取点”留下来。Android 官方 API 文档把它定位为调试资源泄漏的工具：资源获取后调用 `open()`，正常释放后调用 `close()`，对象终结时用 `warnIfOpen()` 发出警告。生产治理仍要靠显式释放和测试门禁，不能把 CloseGuard 当成兜底释放器。

[已验证: 官方文档, developer.android.com/reference/android/util/CloseGuard]
[已验证: 官方文档, developer.android.com/reference/android/os/StrictMode]

## 诊断流程与证据采集

遇到疑似 finalizer 或 `ReferenceQueue` 问题时，排查顺序要从“资源是否持续增长”开始，再看 ART 守护线程。只看一次 heap dump 很容易漏掉时间维度。

建议采集五组证据：

- 资源计数: 每轮复现前后记录 FD 数、`dumpsys meminfo`、native heap、graphics memory。观察是否随操作次数增长，还是 GC 后能回落。
- Java heap: 导出 hprof，按 dominator tree 找持有资源 wrapper 的对象；关注已经不可达但仍等待 finalization 的对象，必要时对比两次 dump。
- 线程状态: 抓 `debuggerd -b <pid>` 或 ANR trace，查看 `FinalizerDaemon`、`ReferenceQueueDaemon`、`FinalizerWatchdogDaemon` 的栈。
- Perfetto: 查看目标进程里的 daemon 线程轨道、CPU running 区间、主线程卡顿区间是否重叠；如果资源释放触发 Binder 或文件操作，还要看对应线程的阻塞状态。
- 日志: 收集 CloseGuard、StrictMode VM policy、`Uncaught exception thrown by finalizer`、`FinalizerWatchdogDaemon` 相关日志。

一轮较稳的现场记录模板：

```bash
# 复现前
adb shell pidof com.example.app
adb shell dumpsys meminfo com.example.app > meminfo_before.txt
adb shell 'ls -l /proc/<pid>/fd | wc -l' > fd_before.txt

# 执行 N 轮打开/关闭/切换/退出操作后
adb shell dumpsys meminfo com.example.app > meminfo_after.txt
adb shell 'ls -l /proc/<pid>/fd | wc -l' > fd_after.txt
adb shell debuggerd -b <pid> > threads_after.txt
```

证据判读要区分三种情况：

| 现象 | 更可能的原因 | 下一步 |
|---|---|---|
| FD 数持续上涨，CloseGuard 有资源未关闭警告 | 显式 `close()` 缺失或异常路径漏关 | 查资源获取栈和关闭路径，补 `try/finally` 或 Kotlin `use {}` |
| Java heap 可回落，Native Heap 不回落 | Java wrapper 生命周期和 native 释放脱节 | 查 JNI 引用、native handle 所有权、析构函数是否只放在 finalizer |
| `FinalizerDaemon` 长时间卡在业务清理 | `finalize()` 做了慢操作或拿了业务锁 | 移走慢操作，改成显式关闭和后台释放队列 |

`FinalizerWatchdogDaemon` 的存在说明 ART 也把 finalizer 卡住视为 VM 级风险。源码注释写明：如果 `FinalizerDaemon` 处理一个实例超过阈值，或者 `ReferenceQueueDaemon` 长时间卡在 `enqueuePending()`，watchdog 会构造超时异常并结束 VM。应用侧不应该把复杂清理逻辑放进 `finalize()`。

[已验证: AOSP android-16.0.0_r1, Daemons.java lines 414-449]

## 工程治理边界

资源治理的原则很直接：拥有资源的一方负责确定性释放，finalizer 只能用于发现遗漏或兜底报警。

更稳的做法有几类：

- `AutoCloseable` / `Closeable`: Java 用 `try-with-resources`，Kotlin 用 `use {}`，把释放动作绑定到语法结构，避免异常路径漏关。
- `StrictMode.VmPolicy`: 调试包启用 leaked closable / leaked registration 等检测，把资源泄漏尽早变成日志或测试失败。
- CloseGuard: 自定义资源 wrapper 可以在获取资源后 `open()`，正常释放时 `close()`，终结阶段只报警，不承担主释放路径。
- 资源池: 对昂贵对象做复用时要有最大容量、空闲回收和生命周期 owner，不能只依赖对象不可达后的清理。
- JNI wrapper: native 资源要明确所有权。Java 对象关闭时调用 native release；native 层不能长期持有不释放的 global ref。

`Cleaner` 的使用要看 API level、desugaring 和团队规范。Android 上有三条 Cleaner 执行路径：

- `sun.misc.Cleaner`（API 26+）：在 `ReferenceQueueDaemon` 的 `enqueuePending()` 中，检测到引用的 queue 是 `Cleaner` 队列时直接调用 `Cleaner.clean()`。不存在独立的 `CleanerDaemon` 线程。
- `java.lang.ref.Cleaner.create()`（API 33 公开）：通过 `CleanerImpl.start()` 创建名为 `Cleaner-N` 的独立 daemon 线程执行清理，不经过 `FinalizerDaemon`。
- Android 隐藏的 system cleaner（`Cleaner.createSystemCleaner()` / `SystemCleaner.cleaner()`）：把 queue 设为 `FinalizerReference.queue`，由 `FinalizerDaemon.processReference()` 中的 `doClean()` 执行。

三条路径都不提供确定性执行时间。对 FD、socket、数据库 cursor、GraphicBuffer、Bitmap native allocation 这类资源，主路径仍然是显式关闭。

一个资源 wrapper 的最小结构应该像这样：

```kotlin
class NativeHandleOwner(
    private var handle: Long
) : AutoCloseable {
    private var closed = false

    override fun close() {
        if (closed) return
        closed = true
        val h = handle
        handle = 0L
        if (h != 0L) nativeRelease(h)
    }
}
```

这段代码只表达所有权转移和幂等释放，不把释放逻辑放进 `finalize()`。如果必须加 CloseGuard，也应该只在未调用 `close()` 时报警，不能在报警路径里补做复杂业务清理。

## Cleaner / CloseGuard / StrictMode 的组合使用

三者的职责可以分开：

| 工具 | 适合做什么 | 不适合做什么 |
|---|---|---|
| `Closeable` / `AutoCloseable` | 主释放路径，保证正常和异常分支都释放资源 | 发现调用方忘记释放后的来源栈 |
| CloseGuard | 调试期记录资源获取点，在对象终结时报警 | 代替 `close()` 释放资源 |
| StrictMode VM policy | 在 debug、CI、灰度包里暴露泄漏类问题 | 在 release 包里无差别开启高噪声策略 |
| Cleaner | 给少数资源做兜底清理，避免 `finalize()` 语义 | 保证释放延迟、承载慢操作或业务锁 |

CI 里可以把资源泄漏测试写成固定复现脚本：执行 N 轮打开/关闭，记录 FD 数和 `dumpsys meminfo`，再配合 StrictMode 日志判断是否有未关闭资源。测试失败条件不要只看单次绝对值，最好看增长斜率；一次启动里的基线 FD 数受系统版本、WebView、厂商组件影响较大。

[已验证: 官方文档, developer.android.com/reference/android/os/StrictMode]

## Cleaner / CloseGuard 的版本对照表与源码路径

三个机制在不同 API level 的可用性有明确边界，源码路径也不同。`dalvik.system.CloseGuard`（非公开）和 `android.util.CloseGuard`（API 30 公开）是两套独立的 CloseGuard 实现，分别服务于虚拟机层和应用层；`sun.misc.Cleaner`（API 26+）和 `java.lang.ref.Cleaner`（API 33 公开）是两条 Cleaner 路径：前者在 `ReferenceQueueDaemon.enqueuePending()` 中直接执行清理，后者由 `CleanerImpl` 创建的独立 daemon 线程处理。Android system cleaner 复用 `FinalizerReference.queue`，由 `FinalizerDaemon#doClean()` 触发。

**版本对照表**:

| 机制 | API 26-29 | API 30-32 | API 33+ |
|------|-----------|-----------|---------|
| `dalvik.system.CloseGuard` | ✅ 非公开 | ✅ 非公开 | ✅ 非公开 |
| `android.util.CloseGuard` | ❌ | ✅ 公开 | ✅ 公开 |
| `sun.misc.Cleaner` | ✅ | ✅ | ⚠️ 已废弃（推荐迁移） |
| `java.lang.ref.Cleaner` | ❌（需 desugaring） | ❌（需 desugaring） | ✅ 公开 |
| `FinalizerDaemon` | ✅ | ✅ | ✅ |

> 注：`Daemons.DAEMONS` 数组只包含 `HeapTaskDaemon`、`ReferenceQueueDaemon`、`FinalizerDaemon`、`FinalizerWatchdogDaemon` 四个 daemon（android-16.0.0_r1 `Daemons.java` L59-L64），不存在 `CleanerDaemon`。`sun.misc.Cleaner` 的清理动作在 `ReferenceQueueDaemon.enqueuePending()` 内完成；`java.lang.ref.Cleaner` 使用 `CleanerImpl` 自有线程。

**源码路径**:

- `libcore/libart/src/main/java/java/lang/Daemons.java` — 四个 daemon 定义（L59-L64 `HeapTaskDaemon`/`ReferenceQueueDaemon`/`FinalizerDaemon`/`FinalizerWatchdogDaemon`），L363-L411 `processReference()`/`doFinalize()`/`doClean()`
- `libcore/ojluni/src/main/java/java/lang/ref/ReferenceQueue.java` — `enqueuePending()` 批量入队与 `sun.misc.Cleaner` 清理触发，L236-L279
- `libcore/ojluni/src/main/java/java/lang/ref/FinalizerReference.java` — `FinalizerReference.add()`、`queue` 字段
- `libcore/ojluni/src/main/java/sun/misc/Cleaner.java` — 旧版 Cleaner，在 `ReferenceQueueDaemon.enqueuePending()` 中由 `isCleanerQueue(queue)` 分支直接 `clean()`，L178-L221 `create()`/`createSystemCleaner()`
- `libcore/ojluni/src/main/java/java/lang/ref/Cleaner.java` — API 33 公开 Cleaner，`Cleaner.Cleanable` 接口
- `libcore/ojluni/src/main/java/jdk/internal/ref/CleanerImpl.java` — `CleanerImpl.start()` 创建独立 daemon 线程，L113-L144
- `frameworks/base/core/java/android/util/CloseGuard.java` — API 30 公开 CloseGuard，应用层泄漏检测
- `libcore/dalvik/src/main/java/dalvik/system/CloseGuard.java` — API 26+ 非公开 CloseGuard，Dalvik 内部使用

**Cleaner 三条执行路径**:

路径 A — `sun.misc.Cleaner`（`ReferenceQueueDaemon.enqueuePending()` 直接执行）:
```
ReferenceQueueDaemon.enqueuePending(list, progressCounter)
  → if (sun.misc.Cleaner.isCleanerQueue(queue))
      → cleaner.clean()
        → thunk.run()
```
路径 B — `java.lang.ref.Cleaner.create()`（`CleanerImpl` 自有线程）:
```
Cleaner.create() → CleanerImpl.start()
  → Cleaner-N daemon thread
    → CleanableChain.clean()
      → Cleaner.Cleanable.clean()
```
路径 C — Android system cleaner（`FinalizerDaemon` 触发）:
```
FinalizerDaemon.processReference()
  → FinalizerReference.doClean()
    → SystemCleaner 的 queue 上引用执行清理
```

关键区别：`sun.misc.Cleaner` 不经过独立线程，在 `ReferenceQueueDaemon` 的入队循环中直接执行；`java.lang.ref.Cleaner.create()` 使用 `CleanerImpl` 创建的独立线程，不经过 `FinalizerDaemon`；只有 Android 隐藏的 system cleaner 才走 `FinalizerReference.queue` + `FinalizerDaemon#doClean()` 路径。

**Core Library Desugaring 影响**: `java.lang.ref.Cleaner` 可通过 AGP 8.0+ `coreLibraryDesugaring` 在 API 26+ 设备上使用，需要在 `build.gradle` 中添加 `coreLibraryDesugaring("com.android.tools:desugar_jdk_libs:2.x")` 依赖。但 desugared Cleaner 的每次清理调用会增加桥接层开销，且运行时语义不保证与原生实现完全一致（例如线程调度、异常处理路径可能有差异）；对 FD、GraphicBuffer 这类高频资源，建议用 `AutoCloseable` 显式关闭，不依赖 desugared Cleaner。

[已验证: AOSP android-16.0.0_r1, Daemons.java L59-L64 (四个 daemon), L363-L411 (processReference/doFinalize/doClean)]
[已验证: AOSP android-16.0.0_r1, ReferenceQueue.java L236-L278]
[已验证: 官方文档, developer.android.com/reference/android/util/CloseGuard — Added in API 30]
[待验证: `java.lang.ref.Cleaner` 在 API 33 的具体添加版本，建议交叉核 android-developer-preview 文档]

## Native 资源释放与 Java wrapper 生命周期

Native 资源问题通常来自“小 wrapper 持有大资源”，不一定对应 Java heap 里最大的对象。Java wrapper 只有几十字节，却可能指向一个 FD、ashmem、GraphicBuffer、Bitmap native allocation 或 JNI global ref。wrapper 生命周期稍微拉长，native 侧就会积压。

排查时要把所有权写成表格：

| 资源 | Java 入口 | Native 所有者 | 释放动作 | 证据 |
|---|---|---|---|---|
| FD / socket | `FileInputStream`、`ParcelFileDescriptor`、OkHttp socket | Linux fd table | `close()` | `/proc/<pid>/fd`、CloseGuard |
| Cursor / SQLite | `CursorWindow`、`SQLiteClosable` | sqlite / ashmem | `close()` | `dumpsys meminfo`、logcat |
| Bitmap native allocation | `Bitmap` wrapper | native heap / gralloc | 引用释放后由运行时处理，业务缓存要主动移除 | heap dump、meminfo Graphics/Native |
| GraphicBuffer / Surface | Surface / ImageReader / Camera buffer | gralloc / BufferQueue | `close()`、`release()`、生命周期回调 | Perfetto、meminfo Graphics |
| JNI global ref | 自定义 Java wrapper | native 全局引用表 | `DeleteGlobalRef` | native heap、debug log、JNI 检查 |

这张表的作用是防止排查过程只在 Java heap 里绕圈。`ReferenceQueue` 和 `FinalizerDaemon` 能解释“为什么释放滞后”，但不能替业务代码决定资源什么时候释放。工程治理要把释放动作前移到生命周期边界：页面销毁、请求结束、图片解码完成、Camera session 关闭、数据库 cursor 用完。

[自动发现] 对 Camera、WebView、Bitmap、SQLite 这类模块，finalizer 堆积往往只是表象。排查重点是 owner 生命周期和异常路径：页面退出时有没有释放，失败回调有没有释放，缓存淘汰有没有释放，native 层有没有引用环。

## 小结

`ReferenceQueue` 是 ART 引用处理路径里的队列设施，`FinalizerDaemon` 是执行 finalizer 的守护线程。Android 16 源码显示，这条路径仍然依赖 `ReferenceQueue` 实例锁、批量入队和 watchdog 进度监控；没有证据表明 `ReferenceQueue` 已接入无锁消息队列。

工程上的结论是：不要把 finalizer 当成资源释放方案。发现 FD、native 内存或图形资源上涨时，先采集资源计数和线程证据，再回到 owner 生命周期修关闭路径。finalizer 只能提示“有对象没被及时处理”，不能替代显式释放。

## 延伸阅读
### ART FinalizerDaemon 与 ReferenceQueue 版本矩阵补全
- 来源：/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/DeepResearch/2026-05-24-art-finalizer-referencequeue-cleaner-close-guard-version-matrix.md
- 类型：DeepResearch 调研结果
- 摘要：补全 Android 8-16 区间 sun.misc.Cleaner（CleanerDaemon 独立线程）、java.lang.ref.Cleaner（FinalizerDaemon 路径）、dalvik.system.CloseGuard 与 android.util.CloseGuard 四条清理路径的版本边界、源码位置和执行触发链。ReferenceQueue enqueuePending() 批处理逻辑与 FIFO 队列实现已验证。
- 注入时间：2026-05-25
- 价值：完整的 Cleaner/Finalizer/CloseGuard 版本矩阵和源码路径，填补 §4.9 多版本边界空白

