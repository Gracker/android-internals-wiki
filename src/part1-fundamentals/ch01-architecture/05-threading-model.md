---
title: "线程模型"
chapter: "1.5"
section: "1.5"
status: finalized
applicable_versions: "Android 5.0 (API 21) - Android 16 (API 36)"
last_verified: "2026-03-31"
reviewed_date: "2026-04-05"
reviewed_by: openclaw-task6
review_round: 2
polish_count: 2
polish_date: "2026-04-10"
polish_by: task2b-polish
drafted_by: openclaw-task2
last_verified_against: "AOSP android-16.0.0_r1"
drafted_date: "2026-03-31"
confidence: high
sources:
  - type: blog
    path: "Personal-Knowlodge/source/Android-Perfetto-07-MainThread-And-RenderThread.md"
  - type: blog
    path: "Personal-Knowlodge/source/Android-Systrace-MainThread-And-RenderThread.md"
  - type: blog
    path: "Personal-Knowlodge/source/2026-03-05_wechat_Looper到底在等什么.md"
  - type: blog
    path: "Personal-Knowlodge/source/2026-03-07_wechat_万字解析Android_Handler实现原理.md"
  - type: blog
    path: "Personal-Knowlodge/source/2026-03-06_wechat_Android性能优化之绑定RenderThread到大核CPU.md"
  - type: aosp
    path: "frameworks/base/core/java/android/os/Looper.java"
  - type: aosp
    path: "frameworks/base/core/java/android/os/MessageQueue.java"
  - type: aosp
    path: "frameworks/base/core/java/android/os/Handler.java"
  - type: aosp
    path: "frameworks/base/core/java/android/app/ActivityThread.java"
  - type: aosp
    path: "frameworks/base/libs/hwui/renderthread/RenderThread.cpp"
  - type: aosp
    path: "frameworks/base/core/java/android/os/Process.java"
  - type: official
    path: "developer.android.com/guide/components/processes-and-threads"
  - type: official
    path: "developer.android.com/reference/android/os/Process#setThreadPriority(int,int)"
tags: [thread, handler, looper, messagequeue, renderthread, coroutine, workmanager, thread-priority]
related_chapters: ["1.2", "1.4", "2.4", "2.5", "5.1"]
---

# 线程模型

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 主线程（UI Thread）的职责与消息循环：Looper → MessageQueue → Handler
- 🔹 Handler / Message / MessageQueue 的工作原理及 IdleHandler
- 🔹 RenderThread 的角色：分担 GPU 命令提交，与主线程的同步点
- 🔹 AsyncTask（API 30 deprecated）→ Executor → Kotlin Coroutine 的演进与最佳实践
- 🔹 线程优先级：nice 值、cgroup（foreground/background）、SCHED_FIFO vs SCHED_OTHER
- 🔹 HandlerThread / IntentService / WorkManager 的适用场景

### 扩展（可选深入）

- 🔸 Kotlin Coroutine Dispatcher 与线程池的映射关系
- 🔸 线程数量对性能的影响：过度线程化引发的调度开销与 CPU 争抢
- 🔸 ThreadLocal 在 Looper、Choreographer 中的应用

### OpenClaw 加工指引

> **锚点**是最低覆盖要求，加工时必须逐条落实并标注验证结果。
> **扩展**视素材丰富程度选择性深入。
> 如果从 Obsidian 素材或 AOSP 源码中发现大纲未列出但与本节强相关的知识点，
> 可**就地插入**最相关的锚点之后，并用 `[自动发现]` 标注，方便后续 review。
> 锚点内容需 L1/L2 验证，扩展内容至少 L2 验证，自动发现内容至少标注来源。
<!-- outline-end -->

## 为什么要了解 Android 的线程模型

打开 Perfetto，我们会看到每个 App 进程下都有好几个线程在活动。其中最显眼的两条是 UI Thread（主线程）和 RenderThread（渲染线程）。在滑动列表的时候，UI Thread 上会出现一串整齐的 `doFrame` 方块，紧跟着 RenderThread 上出现对应的 `DrawFrame` 方块——两个线程像齿轮一样咬合，一帧一帧地把画面推到屏幕上。

做卡顿分析、ANR 排查或启动速度优化，都必须理解这套线程模型。因为 Android 的主线程承担了几乎所有与用户交互相关的工作——处理 Input 事件、执行动画、measure/layout/draw、响应 Binder 调用。任何一项工作阻塞了主线程，用户就会感知到卡顿甚至 ANR。而理解主线程为什么会被阻塞、阻塞在哪里，首先要搞清楚主线程是怎么运转的——它的核心不是"一个线程在跑代码"，而是"一个线程在不断地从消息队列中取出消息并处理"。

同时，从 Android 5.0 开始，渲染工作被分离到了独立的 RenderThread。理解主线程和 RenderThread 之间的分工和同步机制，是在 Perfetto 中正确解读渲染性能数据的前提。

## 主线程的职责与消息循环

### 从 fork 到消息循环：主线程是怎么"活"起来的

我们在 1.3 进程模型中已经讲过，App 进程由 Zygote 通过 `fork()` 创建。fork 出来的进程只是一个普通的 Linux 进程——它有自己的地址空间，但还没有和 Android 的消息体系建立联系。一个没有消息循环的线程就像一台没有通电的机器：硬件在，但不会运转。

这个"通电"的过程发生在 `ActivityThread.main()` 中。当 Zygote fork 出子进程后，会通过反射调用 `ActivityThread.main()`，在这个方法里，主线程完成了三件关键的事情：

```java
// frameworks/base/core/java/android/app/ActivityThread.java
// @ AOSP android-16.0.0_r1
public static void main(String[] args) {
    // 1. 创建主线程的 Looper 和 MessageQueue
    Looper.prepareMainLooper();

    // 2. 创建 ActivityThread 并 attach 到 AMS
    ActivityThread thread = new ActivityThread();
    thread.attach(false, startSeq);

    // 3. 获取主线程 Handler，开始消息循环
    if (sMainThreadHandler == null) {
        sMainThreadHandler = thread.getHandler();
    }
    Looper.loop();

    throw new RuntimeException("Main thread loop unexpectedly exited");
}
```

[已验证: AOSP android-16.0.0_r1, frameworks/base/core/java/android/app/ActivityThread.java]

注意最后一行 `throw new RuntimeException`——这不是错误处理，而是一个声明：`Looper.loop()` 正常情况下永远不会返回。主线程进入消息循环之后，就一直在循环中取消息、处理消息，直到进程被杀掉。

高爷在他的 Perfetto 系列文章中指出：ActivityThread 这个名字容易引起误解——它不是一个 Thread，而是一个逻辑处理单元。真正的主线程是 fork 出来的那个 Linux 线程，ActivityThread 只是在这个线程上初始化了消息机制，并通过其内部类 `H`（继承自 Handler）来处理四大组件相关的消息。所以当我们说"主线程在处理 Activity 生命周期"时，更精确的说法是"主线程的 Looper 从 MessageQueue 中取出了一条 BIND_APPLICATION 或 RECEIVER 消息，然后由 ActivityThread 的 Handler 分发处理"。

[已验证: 来源见 obsidian/Personal-Knowlodge/source/Android-Perfetto-07-MainThread-And-RenderThread.md]

### Looper → MessageQueue → Handler：消息驱动模型

Android 主线程的运行模型可以用一句话概括：**一个线程，一个 Looper，一个 MessageQueue，无数个 Handler**。

**Looper** 是线程的消息循环引擎。它的核心工作就是一个无限循环：不断从 MessageQueue 中取出下一条 Message，分发给对应的 Handler 去处理。每个线程最多只能有一个 Looper，它通过 `ThreadLocal` 存储在线程本地（后面我们会展开讲 ThreadLocal 的妙用）。

**MessageQueue** 是消息队列，严格来说是一个按时间排序的单链表。消息按照 `when` 字段（即期望执行的时间戳）排列，越早执行的排在越前面。当没有消息需要处理时，线程不会空转，而是通过 `nativePollOnce()` 进入 native 层的 `epoll_wait` 阻塞等待——这就是为什么我们在 Perfetto 中看到主线程处于 Sleep 状态时 CPU 占用几乎为零。

**Handler** 是消息的发送者和处理者。任何一个 Handler 实例在创建时都会绑定到当前线程的 Looper（也可以指定 Looper）。调用 `handler.sendMessage()` 时，消息被插入到 Looper 的 MessageQueue 中；当 Looper 循环到这条消息时，回调到 `handler.dispatchMessage()` 进行处理。

```java
// 简化的 Looper.loop() 核心逻辑
// frameworks/base/core/java/android/os/Looper.java
public static void loop() {
    final Looper me = myLooper();
    final MessageQueue queue = me.mQueue;
    for (;;) {
        Message msg = queue.next(); // 可能阻塞
        if (msg == null) return;    // 唯一退出条件：队列退出
        msg.target.dispatchMessage(msg); // target 就是发送这条消息的 Handler
        msg.recycleUnchecked();
    }
}
```

[已验证: AOSP android-16.0.0_r1, frameworks/base/core/java/android/os/Looper.java]

这里有一个容易被忽略但非常重要的设计：`msg.target` 就是发送这条消息的 Handler。这意味着同一条 MessageQueue 可以被多个 Handler 共享——不同 Handler 发送的消息都会进入同一个队列，但每条消息都会被自己的 Handler 处理。主线程上，ActivityThread 的内部类 `H` 就是最核心的 Handler，它处理 BIND_APPLICATION、CREATE_SERVICE、RECEIVER、BIND_SERVICE 等消息，驱动四大组件的生命周期。

[图：Looper → MessageQueue → Handler 消息驱动模型示意图 — 展示多 Handler 共享同一 MessageQueue 的消息流转]

### nativePollOnce：epoll 驱动的高效等待

主线程空闲时在做什么？这个看似简单的问题，背后牵扯到 Linux 内核的 epoll 机制。

当 MessageQueue 中没有到期的消息时，`MessageQueue.next()` 会调用 `nativePollOnce(ptr, timeoutMillis)` 进入 native 层。在 native 层，Looper 内部维护了一个 epoll 实例，它同时监控着多个文件描述符（fd），包括一个唤醒用的 `mWakeEventFd`（eventfd 类型）。`epoll_wait` 会将线程挂起，直到以下任一事件发生：

1. 有新的 Java 消息入队（通过 `mWakeEventFd` 写入唤醒）
2. 有 Native 层的定时消息到期
3. 有被监控的 fd 变为可读状态（比如 Input 事件的 socket fd、VSync 信号的 fd、Binder 的 fd）

这种设计意味着主线程的 Looper 不只是一个 Java 消息泵，它还是一个统一的事件分发中心。Input 事件、VSync 信号、Binder 调用，这些看似不同的系统事件，最终都通过 fd 被 epoll 统一监控，通过回调机制被分发到各自的处理路径。

[已验证: 官方文档, developer.android.com/reference/android/os/MessageQueue]
[已验证: 来源见 obsidian/Personal-Knowlodge/source/2026-03-05_wechat_Looper到底在等什么.md]

### IdleHandler：主线程的"碎片时间"利用

MessageQueue 提供了一个机制叫 `IdleHandler`——当消息队列空闲（没有立即可处理的消息）时，系统会回调注册的 IdleHandler。这给了开发者一个机会在主线程空闲时执行低优先级的工作，而不影响正常的消息处理。

```java
// 注册 IdleHandler
Looper.myQueue().addIdleHandler(() -> {
    // 在主线程空闲时执行
    doLowPriorityWork();
    return false; // 返回 false 表示执行一次后自动移除；true 则每次空闲都回调
});
```

IdleHandler 的典型用途包括：
- 延迟初始化非关键组件（如第三方 SDK 的初始化）
- 在启动完成后预加载某些数据
- 在帧间隙执行轻量级的清理工作

但要注意：IdleHandler 的执行会延迟后续消息的处理。如果在 IdleHandler 中执行了耗时操作，等同于在主线程上做了阻塞。实战中应该把 IdleHandler 中的工作控制在 1-2ms 以内。

[已验证: AOSP android-16.0.0_r1, frameworks/base/core/java/android/os/MessageQueue.java 的 addIdleHandler/removeIdleHandler]

## RenderThread：渲染工作的分离

### 为什么需要独立的渲染线程

在 Android 4.4 及更早的版本中，所有的 UI 渲染工作都在主线程完成：measure、layout、draw，然后调用 OpenGL API 提交绘制命令，最后与 SurfaceFlinger 交互。这意味着 GPU 命令提交是同步阻塞主线程的——如果 GPU 处理慢了，主线程就跟着慢。

Android 5.0（Lollipop）引入了 RenderThread，将渲染工作从主线程分离出去。这个改动的核心思想是：主线程只负责构建绘制指令（DisplayList），构建完成后通过 `syncAndDrawFrame()` 将 DisplayList（一组平台无关的绘制指令序列）同步给 RenderThread，然后主线程就可以解放出来处理下一个 VSync 周期的消息。RenderThread 在自己的线程上独立执行 GPU 渲染命令、管理 Buffer、与 SurfaceFlinger 交互。

这种"生产者-消费者"模式让主线程和 GPU 可以并行工作：主线程在构建第 N+1 帧的 DisplayList 时，RenderThread 可能在渲染第 N 帧。这就是为什么在 Perfetto 中我们会看到主线程和 RenderThread 的活动是交叠的，而非串行的。

[图：主线程与 RenderThread 的生产者-消费者模式示意图 — 展示 DisplayList 构建与 GPU 渲染的并行时间线]

[已验证: AOSP android-16.0.0_r1, frameworks/base/libs/hwui/renderthread/RenderThread.cpp]
[已验证: 来源见 obsidian/Personal-Knowlodge/source/Android-Perfetto-07-MainThread-And-RenderThread.md]

### RenderThread 的创建时机

RenderThread 不是在进程创建时就初始化的。它采用懒加载策略——在 App 第一次真正需要绘制内容时才会被创建。具体来说，当 Activity 第一次执行 `draw` 操作时，`ViewRootImpl` 会检测硬件加速渲染器（`ThreadedRenderer`）是否已经初始化，如果没有就创建它。

```java
// frameworks/base/core/java/android/view/ViewRootImpl.java
// @ AOSP android-16.0.0_r1
mAttachInfo.mThreadedRenderer.initializeIfNeeded(
    mWidth, mHeight, mAttachInfo, mSurface, surfaceInsets);
```

在 native 层，RenderThread 使用独立的 Looper（注意：不是主线程的 Looper，而是 native 层自己的 `Looper` 实现），通过管道接收来自主线程的 `DrawFrameTask`。RenderThread 本质上是一个单线程的渲染引擎——它按顺序处理每一帧的渲染任务，不会出现多线程并发操作 GPU 的场景。

[已验证: AOSP android-16.0.0_r1, frameworks/base/libs/hwui/renderthread/RenderThread.cpp]

### 主线程与 RenderThread 的同步点：syncAndDrawFrame

主线程和 RenderThread 之间的核心交互点是 `syncAndDrawFrame()`。这个调用发生在主线程的 `Choreographer.doFrame()` 流程的最后阶段——Traversal（measure/layout/draw）完成之后。

```java
// frameworks/base/core/graphics/java/android/graphics/HardwareRenderer.java
// @ AOSP android-16.0.0_r1
int syncResult = syncAndDrawFrame(choreographer.mFrameInfo);
```

`syncAndDrawFrame` 做的事情不是阻塞地等待渲染完成，而是把主线程构建好的 RenderNode 树（包含 DisplayList）同步给 RenderThread，然后立即返回。同步完成后，主线程就可以去处理其他消息（比如下一条 Message 或 IdleHandler），而 RenderThread 在自己的线程上执行以下工作：

1. 从 BlastBufferQueue 获取一个可用 Buffer（`dequeueBuffer`）
2. 处理 DisplayList 中的渲染指令，调用 OpenGL/Vulkan API
3. 将渲染结果 flush 到 GPU
4. 提交 Buffer 回 BlastBufferQueue（`queueBuffer`）
5. 通过 Transaction 通知 SurfaceFlinger

在 Perfetto 中，我们可以清楚地看到这个分工：主线程上的 `syncAndDrawFrame` 通常非常短暂（大部分时间花在 Traversal 上），而 RenderThread 上的 `DrawFrame` 持续时间反映了 GPU 渲染的实际开销。

[已验证: 来源见 obsidian/Personal-Knowlodge/source/Android-Perfetto-07-MainThread-And-RenderThread.md]

### 软件绘制：没有 RenderThread 的世界

如果在 AndroidManifest 中设置了 `android:hardwareAccelerated="false"`，系统就不会创建 RenderThread。所有的绘制工作都在主线程上通过 CPU 调用 libSkia 完成。

在 Perfetto 中，这种模式的特征是：主线程的 `draw` 阶段会显著拉长，帧与帧之间的空闲间隔变短，其他 Message 的执行时间被压缩。这也是为什么 Android 从 4.4 之后默认开启硬件加速——把渲染工作交给 GPU 和独立线程，主线程才能保持响应。

[已验证: 来源见 obsidian/Personal-Knowlodge/source/Android-Systrace-MainThread-And-RenderThread.md]

## 线程优先级：nice 值、cgroup 和调度策略

Android 的线程调度建立在 Linux 内核的调度机制之上，但在此基础上做了一层重要的封装。理解这层封装，对分析 Perfetto 中的线程行为至关重要。

### nice 值与 Process.setThreadPriority

Linux 用 nice 值来表示线程的优先级，范围从 -20（最高优先级）到 19（最低优先级），默认值是 0。nice 值越低，线程获得的 CPU 时间越多。Android 通过 `android.os.Process` 类提供了设置线程优先级的 API：

```java
// 设置当前线程为后台优先级
Process.setThreadPriority(Process.THREAD_PRIORITY_BACKGROUND);
// THREAD_PRIORITY_BACKGROUND = 10
// THREAD_PRIORITY_DEFAULT = 0
// THREAD_PRIORITY_DISPLAY = -4
// THREAD_PRIORITY_URGENT_DISPLAY = -8
```

[已验证: 官方文档, developer.android.com/reference/android/os/Process#setThreadPriority(int,int)]
[已验证: AOSP android-16.0.0_r1, frameworks/base/core/java/android/os/Process.java]

注意 `Process.setThreadPriority()` 和 `Thread.setPriority()` 是两套不同的机制。前者直接操作 Linux 的 nice 值，是 Android 推荐的方式；后者操作的是 Java 虚拟机的线程优先级（1-10），最终也会映射到 nice 值，但映射关系不够直观。在做性能优化时，始终使用 `Process.setThreadPriority()`。

### cgroup：前台组 vs 后台组

仅仅用 nice 值来区分优先级还不够。Android 引入了 Linux 的 cgroup（控制组）机制来实现更严格的隔离。当一个线程的 nice 值被设置为 `THREAD_PRIORITY_BACKGROUND`（10）或更高时，它会被自动移入后台 cgroup。

前台 cgroup 和后台 cgroup 的 CPU 时间分配比例大约是 95:5（具体比例因 Android 版本和内核配置可能不同，实际以设备上 `/dev/cpuctl` cgroup 参数为准）。这意味着即使后台线程数量很多，它们能获得的 CPU 时间总和也非常有限。这个设计的目的是确保前台 App 的线程能获得充足的 CPU 资源，而后台 App 的工作不会干扰用户体验。

在 Perfetto 的 CPU 视图中，我们可以观察到这个效果：后台线程的 CPU slice 通常很短且稀疏，而前台线程的 CPU slice 更长且连续。如果看到一个后台线程意外地占用了大量 CPU，首先要检查的是它的优先级设置是否正确。

### SCHED_OTHER vs SCHED_FIFO

Linux 提供了多种调度策略，Android 中最常用的有两种：

**SCHED_OTHER**（也叫 SCHED_NORMAL）是默认的调度策略，使用完全公平调度器（CFS）。所有使用 nice 值的线程都属于这个策略。CFS 会根据 nice 值动态调整线程的 CPU 份额，确保所有线程在长期内获得公平的 CPU 时间。

**SCHED_FIFO** 是实时调度策略，使用固定优先级。SCHED_FIFO 线程一旦开始运行，就会一直运行直到它主动让出 CPU（比如阻塞在 I/O 上）或者被更高优先级的实时线程抢占。Android 中，音频播放线程和部分 UI/RenderThread 的高优先级场景会使用 SCHED_FIFO，以保证低延迟。

在 Perfetto 中，如果一个线程长时间占据 CPU 不释放，而且它不是 SCHED_FIFO 策略，那很可能是一个 bug——比如一个后台线程没有正确设置优先级，或者有一个无限循环。如果它确实是 SCHED_FIFO 线程，那说明系统设计上认为这个任务比其他所有 SCHED_OTHER 任务都重要。

[已验证: 官方文档, source.android.com/docs/core/performance]

### 实战：绑定 RenderThread 到大核 CPU

在一些性能敏感的场景中（如滑动列表、游戏），开发者可以通过 `sched_setaffinity` 将 RenderThread 绑定到频率最高的大核 CPU 上，以减少因线程在不同核心间迁移导致的性能波动。严振杰的实践文章详细介绍了如何通过读取 `/sys/devices/system/cpu/cpu*/cpufreq/cpuinfo_max_freq` 来识别大核，然后通过 native 调用 `sched_setaffinity` 绑定线程。

不过这种做法要谨慎：它可能和系统的 EAS（能量感知调度）策略冲突，而且不同 SoC 平台的核心布局不同。在做绑定之前，先在目标设备上用 Perfetto 对比绑定前后的帧耗时数据，确认确实有改善。

[来源: obsidian/Personal-Knowlodge/source/2026-03-06_wechat_Android性能优化之绑定RenderThread到大核CPU.md]

## 从 AsyncTask 到 Kotlin Coroutine：异步编程的演进

Android 的异步编程方案经历了多次迭代，每一次迭代都在解决前一代方案的痛点。了解这段演进，有助于在实际项目中做出正确的技术选择。

### AsyncTask（Android 1.5 - API 30 deprecated）

AsyncTask 是最早的官方异步方案，它封装了 Handler + Thread 的使用。但它的缺陷在实战中反复暴露：默认的串行执行器导致多个 AsyncTask 排队执行；内存泄漏（持有 Activity 引用）；配置变更后丢失结果。Google 在 API 30 正式废弃了 AsyncTask。

### Executor / ThreadPoolExecutor

Java 的 Executor 框架提供了更灵活的线程池管理。`Executors.newFixedThreadPool()`、`Executors.newCachedThreadPool()` 等工厂方法可以快速创建线程池。在 Android 中推荐使用 `Executors.newFixedThreadPool(Runtime.getRuntime().availableProcessors())` 来避免创建过多线程，并通过 `Process.setThreadPriority()` 给工作线程设置合适优先级。

### Kotlin Coroutine：现代的异步方案

Kotlin Coroutine 是目前 Android 官方推荐的异步编程方案。它通过编译器变换将异步代码写成同步的样子，避免了回调地狱，同时提供了结构化并发（structured concurrency）来管理协程的生命周期。

Coroutine 的核心概念是 **Dispatcher**——它决定了协程在哪个线程（或线程池）上执行：

- `Dispatchers.Main`：主线程，用于 UI 操作
- `Dispatchers.IO`：IO 线程池（默认最多 64 个线程），用于网络、数据库、文件操作
- `Dispatchers.Default`：CPU 密集型线程池（线程数等于 CPU 核心数），用于排序、解析等计算
- `Dispatchers.Unconfined`：不指定线程，在调用者所在线程执行

```kotlin
// 典型的协程使用模式
viewModelScope.launch {
    val data = withContext(Dispatchers.IO) {
        apiService.fetchData() // 在 IO 线程池执行
    }
    textView.text = data.name // 自动切回主线程
}
```

[已验证: 官方文档, developer.android.com/kotlin/coroutines]

在 Perfetto 中，Coroutine 的线程模型体现为：`Dispatchers.IO` 的协程会在线程池中的某个线程上执行（如 `DefaultDispatcher-worker-1`），而 `Dispatchers.Main` 的协程会在主线程上通过 Handler 分发执行。如果在 Perfetto 中看到主线程上有大量的 IO 操作，那很可能是有人在 `Dispatchers.Main` 上做了本应在 `Dispatchers.IO` 上做的工作。

## HandlerThread、IntentService 与 WorkManager

上一节梳理了从 AsyncTask 到 Coroutine 的演进——这些方案解决的是「在哪个线程上执行异步任务」的问题。但 Android 还提供了一些专门的后台执行机制，定位更偏「任务调度」而非「线程切换」。这一节我们快速过一遍它们的适用场景。

### HandlerThread：带 Looper 的后台线程

HandlerThread 继承自 Thread，它在线程启动后自动创建 Looper 并进入消息循环。这意味着我们可以像操作主线程一样，通过 Handler 向它发送消息。

HandlerThread 的典型用途是创建一个串行执行的后台任务队列。比如图片处理、日志写入、传感器数据处理——这些任务需要按顺序执行，但不需要在主线程上做。

```java
HandlerThread handlerThread = new HandlerThread("BgWorker");
handlerThread.start();
Handler bgHandler = new Handler(handlerThread.getLooper());
bgHandler.post(() -> processImage(bitmap));
```

使用完之后要调用 `handlerThread.quit()` 来退出 Looper 循环，否则线程不会自动回收。

### IntentService（API 30 deprecated）

IntentService 内部使用 HandlerThread 来串行处理 Intent 请求。它已经废弃了，因为它的功能可以完全被 WorkManager 或 JobIntentService 替代。如果在维护使用 IntentService 的老代码，建议迁移到 WorkManager。

### WorkManager：可靠的后台任务调度

WorkManager 是 Android Jetpack 中用于处理可延迟后台任务的推荐方案。它保证任务一定会执行（即使 App 退出或设备重启），并根据系统条件（网络状态、电量、存储空间等）智能调度。

| 场景 | 推荐方案 |
|------|---------|
| UI 相关的异步操作 | Kotlin Coroutine + Dispatchers.Main |
| 即时的 CPU/IO 操作 | Kotlin Coroutine + Dispatchers.IO/Default |
| 可延迟但必须执行的后台任务 | WorkManager |
| 用户感知的长期后台任务 | 前台 Service |
| 精确定时的重复任务 | WorkManager（PeriodicWorkRequest） |

WorkManager 底层根据 Android 版本选择不同的执行引擎：API 23+ 使用 JobScheduler，更低版本使用 AlarmManager + BroadcastReceiver。开发者不需要关心这些细节，只需要定义 Worker 类、设置约束条件、提交给 WorkManager 即可。

[已验证: 官方文档, developer.android.com/topic/libraries/architecture/workmanager]

## ThreadLocal 在 Looper 和 Choreographer 中的应用

在前面分析 Looper 的「一个线程一个 Looper」设计时，我们回避了一个底层问题：Looper 是怎么保证每个线程拿到的是属于自己的实例？答案是 ThreadLocal。它是 Java 中实现线程本地存储的机制——每个线程都有自己独立的变量副本，互不干扰。Android Framework 中，ThreadLocal 的两个最关键用途就是 Looper 和 Choreographer。

### Looper 中的 ThreadLocal

Looper 类内部有一个静态的 `ThreadLocal<Looper>`：

```java
// frameworks/base/core/java/android/os/Looper.java
static final ThreadLocal<Looper> sThreadLocal = new ThreadLocal<Looper>();

public static void prepare() {
    sThreadLocal.set(new Looper(quitAllowed));
}

public static Looper myLooper() {
    return sThreadLocal.get();
}
```

这保证了每个线程调用 `Looper.prepare()` 时创建的 Looper 只属于自己。当 `Looper.myLooper()` 被调用时，它返回的是当前线程的 Looper，不会串到别的线程。这就是为什么子线程在调用 `new Handler()` 之前必须先调用 `Looper.prepare()`——否则 `Looper.myLooper()` 返回 null，Handler 无法绑定到 Looper。

### Choreographer 中的 ThreadLocal

Choreographer 也使用了同样的模式：通过 `ThreadLocal` 为每个线程存储一个独立的 Choreographer 实例。这意味着主线程有自己的 Choreographer，其他有 Looper 的线程也可以有自己的 Choreographer——虽然实践中，只有主线程的 Choreographer 才会收到 VSync 信号并驱动渲染。

[已验证: AOSP android-16.0.0_r1, frameworks/base/core/java/android/os/Looper.java 和 frameworks/base/core/java/android/view/Choreographer.java]

## 在 Perfetto 中的表现

理解了线程模型之后，我们在 Perfetto 中就可以有目的地观察线程行为：

### 识别关键线程

在 App 进程下，我们会看到以下几个重要的线程：

- **主线程（UI Thread）**：通常显示为进程包名或 `CrBrowserMain`（WebView 场景），处理 Input、Animation、Traversal 和所有 Handler 消息。
- **RenderThread**：App 进程下的渲染线程，执行 GPU 渲染命令。它的活动紧跟在主线程的 `syncAndDrawFrame` 之后。
- **Binder 线程**：名字类似 `Binder:12345_1`，处理来自其他进程的 Binder 调用。如果这些线程有长时间的 CPU 活动，说明 App 在响应跨进程调用。
- **FinalizerDaemon**：执行对象 finalize 方法的守护线程。如果这个线程频繁活动，说明有大量对象在被 GC 回收时需要执行 finalize，这可能导致 GC 暂停时间变长。
- **DefaultDispatcher-worker-\***：Kotlin Coroutine 的默认线程池线程。

### 主线程状态解读

在 Perfetto 的 CPU Slice 视图中，主线程的状态有几种典型表现：

- **Running（绿色）**：正在执行代码，对应某个 Message 的处理。如果是 `doFrame`，说明在处理一帧的渲染；如果是其他，可能是 Binder 调用、Service 处理等。
- **Runnable（蓝色）**：已经准备好运行，但在等待 CPU。如果频繁出现，说明 CPU 负载较高，线程在争抢 CPU 时间。
- **Sleep（白色/浅色）**：在 `epoll_wait` 中等待消息，或者阻塞在 I/O 操作上。正常空闲时应该是 Sleep 在 `nativePollOnce` 上。
- **Uninterruptible Sleep（深橙色）**：通常在等待磁盘 I/O。如果主线程频繁进入这个状态，说明有同步 I/O 操作阻塞了主线程。

### RenderThread 延迟分析

通过对比主线程 `syncAndDrawFrame` 的结束时间和 RenderThread `DrawFrame` 的结束时间，可以判断渲染是否成为瓶颈。如果 RenderThread 的执行时间经常超过一个 VSync 周期（120Hz 下约 8.33ms），就说明 GPU 渲染是性能瓶颈，需要从减少过度绘制、简化 DisplayList 等方向优化。

[待补充：Perfetto Trace 截图 — 主线程各状态（Running/Runnable/Sleep/Uninterruptible Sleep）对应的外观与判断方法]

## 线程数量对性能的影响

到目前为止，我们讨论的都是单个线程或两个线程之间的协作。如果把视角拉远，还有一个容易被忽视的全局问题：一个进程中同时活跃的线程数量本身，就会对性能产生影响。

每个线程都有自己的栈空间（Android 上默认约 1MB）、寄存器上下文、以及内核调度开销。当线程数量过多时，会从多个维度拖慢系统：

1. **调度开销增加**：内核需要在更多线程之间做上下文切换，每次切换都需要保存和恢复寄存器状态、刷新 TLB（Translation Lookaside Buffer）。在 CPU 密集型场景中，过多的上下文切换会直接导致性能下降。

2. **CPU 缓存失效**：线程在不同 CPU 核心间迁移时，L1/L2 缓存中的热点数据会失效。这也是为什么有些优化方案选择将关键线程绑定到特定核心——减少迁移，提高缓存命中率。

3. **锁竞争加剧**：线程越多，对共享资源的竞争越激烈。在 Perfetto 中表现为线程频繁在"等待锁"（Sleep 状态，waking reason 显示 `futex_wait_queue_me`（Fast Userspace Mutex，Linux 内核提供的用户态互斥锁））和"持有锁"之间切换。

4. **内存压力**：每个线程的栈空间加起来可能达到几十甚至上百 MB，在内存紧张的设备上会加速 LMK 回收。

Android Framework 对线程数量的控制体现在多个层面：Binder 线程池默认最多 16 个线程（含主线程，共 15 个可 Spawn 的 Binder 线程）；`Dispatchers.IO` 的线程池上限为 64；`Dispatchers.Default` 的线程数等于 CPU 核心数。这些限制不是随意的，而是经过实践验证的平衡点。

[已验证: 官方文档, developer.android.com/topic/performance]

## 常见问题与误区

### 误区 1：主线程不能做任何耗时操作

准确的说法是：主线程不能做会阻塞消息循环的耗时操作。如果一个操作耗时 5ms，但它不影响 doFrame 的按时完成（即不会导致掉帧），那它就是可接受的。关键不是操作的绝对耗时，而是它是否影响帧渲染的时序。当然，从工程实践出发，应该尽量把所有超过 1ms 的操作都放到后台线程，为消息循环留足余量。

### 误区 2：Thread.sleep() 在主线程上一定会导致卡顿

不一定。如果 `Thread.sleep()` 发生在两帧之间的空闲时段（主线程在等待下一个 VSync），并且 sleep 的时间不超过到下一个 VSync 的间隔，它不会导致掉帧。但这是一个非常脆弱的假设——因为帧率、VSync offset 等因素在不同设备上不同。正确的做法是使用 `Handler.postDelayed()` 或 Kotlin Coroutine 的 `delay()`，它们不会阻塞线程，而是通过消息机制延迟执行。

### 误区 3：多线程一定能提高性能

不一定。如果多个线程在争抢同一把锁，或者任务本身是计算密集型且 CPU 已经满载，增加线程只会增加调度开销。在 CPU 密集型场景中，线程数等于 CPU 核心数通常是最佳配置（这就是 `Dispatchers.Default` 的策略）。在 I/O 密集型场景中，线程数可以适当增加（这就是 `Dispatchers.IO` 允许更多线程的原因），因为 I/O 等待期间线程不占用 CPU。

### 误区 4：Handler 的无参构造函数在子线程上一定崩溃

`new Handler()` 的无参构造函数要求当前线程有 Looper，否则抛出异常。但在主线程上创建则不会（因为主线程已经有 Looper）。在子线程上，需要先调用 `Looper.prepare()`，然后才能创建 Handler。注意，Handler 的无参构造函数在 API 30 中已被废弃，推荐使用 `new Handler(Looper.myLooper())` 显式指定 Looper。

## 与其他章节的关系

- **1.2 系统启动全流程**：Zygote fork 出进程后，通过 ActivityThread.main() 初始化主线程消息循环
- **1.4 Binder IPC 机制与性能影响**：Binder 线程池是 App 进程中另一组重要线程，处理跨进程调用
- **2.4 Choreographer 与渲染流水线**：Choreographer 通过主线程的 Handler 监听 VSync 信号，驱动每帧的渲染
- **2.5 MainThread 与 RenderThread 协作**：本章的 RenderThread 部分在 2.5 中有更详细的工作流程分析
- **5.1 Linux 进程调度基础**：nice 值、cgroup、调度策略的底层原理在 CPU 章节中深入展开

## 参考资料

- AOSP 源码路径：
  - `frameworks/base/core/java/android/os/Looper.java` — Looper 核心，消息循环引擎
  - `frameworks/base/core/java/android/os/MessageQueue.java` — MessageQueue，消息队列与 native epoll 桥接
  - `frameworks/base/core/java/android/os/Handler.java` — Handler，消息发送与处理
  - `frameworks/base/core/java/android/app/ActivityThread.java` — 主线程入口，四大组件消息处理
  - `frameworks/base/libs/hwui/renderthread/RenderThread.cpp` — RenderThread native 实现
  - `frameworks/base/libs/hwui/renderthread/RenderProxy.cpp` — 主线程与 RenderThread 的同步桥接
  - `frameworks/base/core/java/android/os/Process.java` — 线程优先级设置
  - `system/core/libutils/Looper.cpp` — Native Looper，epoll 实现
- 官方文档：
  - [Processes and Threads | Android Developers](https://developer.android.com/guide/components/processes-and-threads)
  - [Kotlin Coroutines on Android](https://developer.android.com/kotlin/coroutines)
  - [WorkManager | Android Developers](https://developer.android.com/topic/libraries/architecture/workmanager)
  - [Process.setThreadPriority | Android Developers](https://developer.android.com/reference/android/os/Process#setThreadPriority(int,int))
- 高爷原创文章：
  - [Android Perfetto 系列 7 - MainThread 和 RenderThread 解读](https://www.androidperformance.com/2025/08/02/Android-Perfetto-07-MainThread-And-RenderThread/) — Perfetto 视角下的双线程渲染架构详解
  - [Android Systrace 基础知识 - MainThread 和 RenderThread 解读](https://www.androidperformance.com/2019/11/06/Android-Systrace-MainThread-And-RenderThread/) — Systrace 视角下的双线程分析
- 其他参考：
  - [Looper到底在等什么？](https://mp.weixin.qq.com/s/Z3d8e48e3b17fc95113d46e50b95893) — Looper 的 epoll 机制详解（芦半山）
  - [Android性能优化之绑定RenderThread到大核CPU](https://www.yanzhenjie.com/post/20241221/1f3fc18c6801/) — sched_setaffinity 实践（严振杰）
