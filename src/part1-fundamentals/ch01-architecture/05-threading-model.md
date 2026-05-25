---
title: 线程模型
chapter: '1.5'
section: '1.5'
status: ready-for-review
pipeline_stage: task2b_pending
task6_state: reviewed
task6_result: pass-light-edit
reviewed_by: openclaw-task6
reviewed_date: '2026-05-12'
reviewed_at: '2026-05-12T20:10:00+08:00'
last_task6_at: '2026-05-12T20:10:00+08:00'
last_task6_audit: '2026-05-21'
task6_reviewed_date: '2026-05-12'
review_round: 9
task6_review_notes: '2026-05-12 task6 review: 修复 frontmatter、禁用元叙述词和轻量措辞；L1/L2 通过，无新增回炉项。'
task9_state: reviewed
task9_result: needs-rework
task9_reviewed_date: "2026-05-25"
task9_reviewed_by: openclaw-task9
last_task9_at: "2026-05-25T19:34:07+08:00"
task9_review_notes: "2026-05-25 task9 deep-review: needs-rework。P0 2 / P1 0 / P2 0；Binder 线程池等待机制误写成 epoll，硬件加速默认启用版本误写为 Android 4.4。详见 logs/deep-review/2026-05-25-19-deep-review.md。"
last_task9_audit: "2026-05-25"
last_task9_audit_at: "2026-05-25T17:26:00+08:00"
last_task9_audit_log: "logs/deep-review/2026-05-25-17-audit.md"
last_task9_audit_result: "p1-source-accuracy"
task9_audit_notes: "2026-05-25 Task9 idle audit: fixed。P1 1：已删除不可验证的 MQ.DispatchBatches 断言，替换为官方可核验的队列区分信号。"
task2b_state: pending
task2b_result: pending
last_task2b_at: '2026-05-12T19:36:00+08:00'
applicable_versions: Android 5.0 (API 21) - Android 16 (API 36)
last_verified: '2026-04-24'
last_verified_against: AOSP android-16.0.0_r1, Android SDK android-Baklava stubs
confidence: high
sources:
- type: blog
  path: Personal-Knowlodge/source/Android-Perfetto-07-MainThread-And-RenderThread.md
- type: blog
  path: Personal-Knowlodge/source/Android-Systrace-MainThread-And-RenderThread.md
- type: blog
  path: Personal-Knowlodge/source/2026-03-05_wechat_Looper到底在等什么.md
- type: blog
  path: Personal-Knowlodge/source/2026-03-07_wechat_万字解析Android_Handler实现原理.md
- type: blog
  path: Personal-Knowlodge/source/2026-03-06_wechat_Android性能优化之绑定RenderThread到大核CPU.md
- type: aosp
  path: frameworks/base/core/java/android/os/Looper.java
- type: aosp
  path: frameworks/base/core/java/android/os/LegacyMessageQueue/MessageQueue.java
- type: aosp
  path: frameworks/base/core/java/android/os/CombinedMessageQueue/MessageQueue.java
- type: aosp
  path: frameworks/base/core/java/android/os/ConcurrentMessageQueue/MessageQueue.java
- type: aosp
  path: frameworks/base/core/java/android/os/Handler.java
- type: aosp
  path: frameworks/base/core/java/android/app/ActivityThread.java
- type: aosp
  path: frameworks/base/graphics/java/android/graphics/HardwareRenderer.java
- type: aosp
  path: frameworks/base/libs/hwui/renderthread/RenderThread.cpp
- type: aosp
  path: frameworks/native/libs/binder/ProcessState.cpp
- type: aosp
  path: frameworks/base/core/java/android/os/Process.java
- type: official
  path: developer.android.com/guide/components/processes-and-threads
- type: official
  path: developer.android.com/reference/android/os/Process#setThreadPriority(int,int)
tags:
- thread
- handler
- looper
- messagequeue
- renderthread
- coroutine
- workmanager
- thread-priority
related_chapters:
- '1.2'
- '1.4'
- '1.13'
- '2.4'
- '2.5'
- '5.1'
drafted_date: '2026-03-31'
drafted_by: openclaw-task2
polish_count: 2
polish_date: '2026-04-10'
polish_by: task2b-polish
last_task9_review_log: "logs/deep-review/2026-05-25-19-deep-review.md"
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

做卡顿分析、ANR 排查或启动速度优化，都必须理解这套线程模型。因为 Android 的主线程承担了几乎所有与用户交互相关的工作——处理 Input 事件、执行动画、measure/layout/draw、响应 Binder 调用。任何一项工作阻塞了主线程，用户就会感知到卡顿甚至 ANR。而理解主线程为什么会被阻塞、阻塞在哪里，先要搞清楚主线程是怎么运转的。主线程会不断地从消息队列中取出消息并处理，代码执行只是这个循环中的一个片段。

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

注意最后一行 `throw new RuntimeException`，这行代码直接表明了一个事实：`Looper.loop()` 正常情况下永远不会返回。主线程进入消息循环之后，就一直在循环中取消息、处理消息，直到进程被杀掉。

高爷在他的 Perfetto 系列文章中指出，ActivityThread 这个名字很容易引起误解。它表示的是运行在主线程上的一组调度逻辑，不是一个独立的 Thread 对象。真正的主线程是 fork 出来的那个 Linux 线程，ActivityThread 只是在这个线程上初始化了消息机制，并通过其内部类 `H`（继承自 Handler）来处理四大组件相关的消息。所以当我们说"主线程在处理 Activity 生命周期"时，更精确的说法是"主线程的 Looper 从 MessageQueue 中取出了一条 BIND_APPLICATION 或 RECEIVER 消息，然后由 ActivityThread 的 Handler 分发处理"。

[已验证: 来源见 obsidian/Personal-Knowlodge/source/Android-Perfetto-07-MainThread-And-RenderThread.md]

### Looper → MessageQueue → Handler：消息驱动模型

Android 主线程的运行模型可以用一句话概括：**一个线程，一个 Looper，一个 MessageQueue，无数个 Handler**。

**Looper** 是线程的消息循环引擎。它的核心工作就是一个无限循环：不断从 MessageQueue 中取出下一条 Message，分发给对应的 Handler 去处理。每个线程最多只能有一个 Looper，它通过 `ThreadLocal` 存储在线程本地（后面我们会展开讲 ThreadLocal 的妙用）。

**MessageQueue** 对外暴露的语义一直没变，仍然是“按到期时间取下一条消息，再交给对应 Handler 处理”。如果只看经典实现，它可以理解成一个按 `when` 排序的链式队列，很多 Handler / Looper 教程也是按这个模型展开的。这里要补一个版本边界：章节适用范围已经覆盖到 Android 16，而 android-16 源树里已经并存 `LegacyMessageQueue`、`CombinedMessageQueue`、`ConcurrentMessageQueue` 三套实现。经典链表这套理解方式仍然有用，但它只准确描述 legacy 路径；android-16 的队列实现演进和锁策略变化放到 §1.13《MessageQueue 机制与 DeliQueue 无锁优化》展开。

兼容性边界也要补上。android-16 公开源码已经把 `CombinedMessageQueue` 和 `ConcurrentMessageQueue` 放进源树，但普通应用默认仍走 legacy；面向应用的默认启用边界在 Android 17，细节放到 §1.13《MessageQueue 机制与 DeliQueue 无锁优化》展开。对工程实践更直接的影响，是不要再把 `MessageQueue.mMessages` 当成稳定观察点。旧版 Espresso、Robolectric 或自定义测试脚本如果靠反射读取这个私有字段判断队列是否空闲，后续迁移会出兼容性问题。测试代码优先改到公开接口，如 `TestLooperManager`、IdlingResource，或者升级到已经去掉私有字段依赖的测试库。

[已验证: 版本边界见 §1.13；Android SDK android-Baklava stubs, android/os/TestLooperManager.java]

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
[已验证: AOSP android-16.0.0_r1, frameworks/base/core/java/android/os/LegacyMessageQueue/MessageQueue.java、frameworks/base/core/java/android/os/CombinedMessageQueue/MessageQueue.java、frameworks/base/core/java/android/os/ConcurrentMessageQueue/MessageQueue.java]

`msg.target` 就是发送这条消息的 Handler——这条消息的发送者。因此，同一条 MessageQueue 可以被多个 Handler 共享。不同 Handler 发送的消息都会进入同一个队列，但每条消息都会被自己的 Handler 处理。主线程上，ActivityThread 的内部类 `H` 就是最核心的 Handler，它处理 BIND_APPLICATION、CREATE_SERVICE、RECEIVER、BIND_SERVICE 等消息，驱动四大组件的生命周期。

[图：Looper → MessageQueue → Handler 消息驱动模型示意图 — 展示多 Handler 共享同一 MessageQueue 的消息流转]

### nativePollOnce：epoll 驱动的高效等待

主线程空闲时在做什么？这个看似简单的问题，背后牵扯到 Linux 内核的 epoll 机制。

当 MessageQueue 中没有到期的消息时，`MessageQueue.next()` 会调用 `nativePollOnce(ptr, timeoutMillis)` 进入 native 层。在 native 层，Looper 内部维护了一个 epoll 实例，它同时监控着多个文件描述符（fd），包括一个唤醒用的 `mWakeEventFd`（eventfd 类型）。`epoll_wait` 会将线程挂起，直到以下任一事件发生：

1. 有新的 Java 消息入队（通过 `mWakeEventFd` 写入唤醒）
2. 有 Native 层的定时消息到期
3. 有 native 层通过 `Looper.addFd()` 注册的 fd 变为可读状态（Input 事件 socket fd、VSync 信号 fd 等在 JNI/native 层通过 `messageQueue->getLooper()->addFd(...)` 注册到同一个 epoll 实例）；App 自定义 fd 可通过 `MessageQueue.addOnFileDescriptorEventListener()` 接入

这种设计让主线程的 Looper 同时承担了 Java 消息泵和统一事件分发中心这两个角色。Input 事件、VSync 信号等系统事件，通过 `addFd` 注册到 epoll 后被统一监控，再通过回调机制分发到各自的处理路径。注意：Binder 通信的 fd 不在主线程 Looper 的默认 epoll 监控集合中——Binder 线程池有自己独立的 epoll 循环处理跨进程调用。

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

[已验证: AOSP android-16.0.0_r1, frameworks/base/core/java/android/os/LegacyMessageQueue/MessageQueue.java 的 addIdleHandler/removeIdleHandler]

## RenderThread：渲染工作的分离

### 为什么需要独立的渲染线程

在 Android 4.4 及更早的版本中，所有的 UI 渲染工作都在主线程完成：measure、layout、draw，然后调用 OpenGL API 提交绘制命令，并与 SurfaceFlinger 交互。结果是 GPU 命令提交会同步阻塞主线程。如果 GPU 处理慢了，主线程也会一起被拖慢。

Android 5.0（Lollipop）引入了 RenderThread，将渲染工作从主线程分离出去。这个改动的核心思想是：主线程只负责构建绘制指令（DisplayList），构建完成后通过 `syncAndDrawFrame()` 将 DisplayList（一组平台无关的绘制指令序列）同步给 RenderThread，然后主线程就可以解放出来处理下一个 VSync 周期的消息。RenderThread 在自己的线程上独立执行 GPU 渲染命令、管理 Buffer、与 SurfaceFlinger 交互。

这种"生产者-消费者"模式让主线程和 GPU 可以并行工作：主线程在构建第 N+1 帧的 DisplayList 时，RenderThread 可能在渲染第 N 帧。这就是为什么在 Perfetto 中我们会看到主线程和 RenderThread 的活动是交叠的，而非串行的。

[图：主线程与 RenderThread 的生产者-消费者模式示意图 — 展示 DisplayList 构建与 GPU 渲染的并行时间线]

[已验证: AOSP android-16.0.0_r1, frameworks/base/libs/hwui/renderthread/RenderThread.cpp]
[已验证: 来源见 obsidian/Personal-Knowlodge/source/Android-Perfetto-07-MainThread-And-RenderThread.md]

### RenderThread 的创建时机

RenderThread 不是在进程创建时就初始化的。它采用懒加载策略——在 App 第一次需要绘制内容时才会被创建。具体来说，当 Activity 第一次执行 `draw` 操作时，`ViewRootImpl` 会检测硬件加速渲染器（`ThreadedRenderer`）是否已经初始化，如果没有就创建它。

```java
// frameworks/base/core/java/android/view/ViewRootImpl.java
// @ AOSP android-16.0.0_r1
mAttachInfo.mThreadedRenderer.initializeIfNeeded(
    mWidth, mHeight, mAttachInfo, mSurface, surfaceInsets);
```

在 native 层，RenderThread 使用独立的 Looper（不是主线程的 Looper，而是 native 层自己的 `Looper` 实现），通过内部的 WorkQueue 接收来自主线程的 `DrawFrameTask`。主线程调用 `DrawFrameTask::postAndWait()` 时，通过 `mRenderThread->queue().post()` 将任务投递到 RenderThread 的 WorkQueue，并用 Condition 同步等待 `syncFrameState` 完成。RenderThread 的 `threadLoop()` 在 `waitForWork()` / `processQueue()` 循环中依次取出并执行任务。RenderThread 仍然是单线程渲染引擎，按顺序处理每一帧，不会出现多线程并发操作 GPU 的场景。

[已验证: AOSP android-16.0.0_r1, frameworks/base/libs/hwui/renderthread/RenderThread.cpp]

### 主线程与 RenderThread 的同步点：syncAndDrawFrame

主线程和 RenderThread 之间的核心交互点是 `syncAndDrawFrame()`。这个调用发生在主线程的 `Choreographer.doFrame()` 流程的最后阶段——Traversal（measure/layout/draw）完成之后。

```java
// frameworks/base/graphics/java/android/graphics/HardwareRenderer.java
// @ AOSP android-16.0.0_r1
int syncResult = syncAndDrawFrame(choreographer.mFrameInfo);
```

`syncAndDrawFrame()` 不是简单的 fire-and-forget。主线程调用它之后，会先把本帧的 `RenderNode` 树和 `FrameInfo` 同步给 RenderThread，并在 `DrawFrameTask::postAndWait()` 这一段同步等待 RenderThread 接管本帧。RenderThread 完成 `syncFrameState`、判断本帧是否需要真正绘制之后，会通过 `unblockUiThread()` 让主线程继续往前跑。

因此，主线程和 RenderThread 的配合要拆成两个阶段看：

1. **同步阶段**：主线程在 `syncAndDrawFrame()` 内等待 RenderThread 完成帧状态同步，并拿到 `syncResult`。
2. **异步阶段**：主线程解阻塞后，RenderThread 继续执行 `DrawFrame`，包括申请 Buffer、提交 GPU 命令、`queueBuffer()` 和通知 SurfaceFlinger。

在 Perfetto 里，主线程上的 `syncAndDrawFrame` 不是“纯异步发包”的零成本 slice，它包含一段可见的同步等待；RenderThread 上更长的 `DrawFrame` slice 则对应后半段渲染开销。把这两段分开看，才能判断瓶颈是在主线程卡住，还是 RenderThread / GPU 把一帧拖长了。

[已验证: AOSP android-16.0.0_r1, frameworks/base/graphics/java/android/graphics/HardwareRenderer.java 和 frameworks/base/libs/hwui/renderthread/RenderProxy.cpp]
[已验证: 来源见 obsidian/Personal-Knowlodge/source/Android-Perfetto-07-MainThread-And-RenderThread.md]

### 软件绘制：没有 RenderThread 的世界

如果在 AndroidManifest 中设置了 `android:hardwareAccelerated="false"`，系统就不会创建 RenderThread。所有的绘制工作都在主线程上通过 CPU 调用 libSkia 完成。

在 Perfetto 中，这种模式的特征是：主线程的 `draw` 阶段会显著拉长，帧与帧之间的空闲间隔变短，其他 Message 的执行时间被压缩。这也是为什么 Android 从 4.4 之后默认开启硬件加速——把渲染工作交给 GPU 和独立线程，主线程才能保持响应。

[已验证: 来源见 obsidian/Personal-Knowlodge/source/Android-Systrace-MainThread-And-RenderThread.md]

## 线程优先级：nice 值、cgroup 和调度策略

Android 的线程调度建立在 Linux 内核的调度机制之上，但在此基础上做了一层重要的封装。理解这层封装，是分析 Perfetto 中线程行为的前提。

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

仅仅用 nice 值来区分优先级还不够。Android 还会通过线程组和 cgroup 配置把前台、后台线程拆开调度。当一个线程被设置成 `THREAD_PRIORITY_BACKGROUND`（10）这类后台优先级时，系统会把它放进 background thread group。AOSP `Process.java` 对这个组的定义是“scheduled with a reduced share of the CPU”。

这里没有一个跨版本都成立的固定比例。不同设备会再叠加 `cpu.shares`、cpuset、uclamp 甚至 cgroup v2 的控制参数，所以不要把它理解成通用的 95:5。分析实机时，直接查看设备上的 `/dev/cpuctl/`、`/dev/stune/` 或 cgroup v2 对应目录参数，更可靠。这样解读 Perfetto 也更稳妥：后台线程的 CPU slice 往往更短、更稀疏，但具体压缩到什么程度，取决于设备配置。

在 Perfetto 的 CPU 视图中，我们可以观察到这个效果：后台线程的 CPU slice 通常很短且稀疏，而前台线程的 CPU slice 更长且连续。如果看到一个后台线程意外地占用了大量 CPU，先检查的是它的优先级设置是否正确。

### SCHED_OTHER vs SCHED_FIFO

Linux 提供了多种调度策略，Android 中最常用的有两种：

**SCHED_OTHER**（也叫 SCHED_NORMAL）是默认的调度策略，使用完全公平调度器（CFS）。所有使用 nice 值的线程都属于这个策略。CFS 会根据 nice 值动态调整线程的 CPU 份额，确保所有线程在长期内获得公平的 CPU 时间。

**SCHED_FIFO** 是实时调度策略，使用固定优先级。SCHED_FIFO 线程一旦开始运行，就会一直运行直到它主动让出 CPU（比如阻塞在 I/O 上）或者被更高优先级的实时线程抢占。Android 里更典型的例子是 AudioFlinger 这类对 deadline 敏感的实时音频线程。App 侧 RenderThread 在 AOSP 常见路径下并不会切到 `SCHED_FIFO`，而是在 `RenderThread::threadLoop()` 里通过 `setpriority(PRIO_PROCESS, 0, PRIORITY_DISPLAY)` 提升到 display nice priority，调度策略仍然属于 `SCHED_OTHER`。

在 Perfetto 中，如果一个线程长时间占据 CPU 不释放，而且它不是 `SCHED_FIFO`，那通常说明它只是拿到了较高的 nice priority，或者代码路径本身有问题。只有在明确看到实时调度线程时，我们才应该按 `SCHED_FIFO` / `SCHED_RR` 的思路去解释它的行为。

[已验证: AOSP android-16.0.0_r1, frameworks/base/libs/hwui/renderthread/RenderThread.cpp]
[已验证: 官方文档, source.android.com/docs/core/performance]

### 实战：绑定 RenderThread 到大核 CPU

在一些性能敏感的场景中（如滑动列表、游戏），开发者可以通过 `sched_setaffinity` 将 RenderThread 绑定到频率最高的大核 CPU 上，以减少因线程在不同核心间迁移导致的性能波动。严振杰的实践文章详细介绍了如何通过读取 `/sys/devices/system/cpu/cpu*/cpufreq/cpuinfo_max_freq` 来识别大核，然后通过 native 调用 `sched_setaffinity` 绑定线程。

不过这种做法要谨慎：它可能和系统的 EAS（能量感知调度）策略冲突，而且不同 SoC 平台的核心布局不同。在做绑定之前，先在目标设备上用 Perfetto 对比绑定前后的帧耗时数据，确认有改善。

Android 12 引入的 ADPF（Adaptive Performance Framework）通过 `PerformanceHintManager` 让应用向系统反馈工作负载目标。ADPF hint session 主要影响 CPU 频率决策——当 `reportActualWorkDuration()` 上报的耗时超过 `getTargetWorkDuration()` 的目标值时，系统会提高对应线程的运行频率。核心放置（哪个 CPU 核心执行线程）仍然由内核 EAS 调度器基于 load/capacity 信息决定，ADPF 不直接控制核心迁移。手动 `sched_setaffinity` 会锁定线程的核心选择范围，ADPF 的频率调整在绑核范围内仍然生效，但调度器无法再自由选择最优核心。在新设备上，优先使用 `PerformanceHintManager` 让系统做频率调度决策，而不是手动绑核。只有在不支持 ADPF 的旧设备上，或者 ADPF 调度效果经过实测确认不如手动绑核时，才考虑 `sched_setaffinity`。

[来源: obsidian/Personal-Knowlodge/source/2026-03-06_wechat_Android性能优化之绑定RenderThread到大核CPU.md]

## 从 AsyncTask 到 Kotlin Coroutine：异步编程的演进

Android 的异步编程方案经历了多次迭代，每一次迭代都在修正前一代方案暴露出来的问题。了解这段演进，有助于在实际项目中做出正确的技术选择。

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

### Java 21 虚拟线程：SDK 露出，不代表已经可用

Android 16 的 SDK stubs 已经带上 `Thread.isVirtual()`，但 `java/lang/Thread.java` 的注释写得很直白：`virtual thread isn't implemented on Android yet`。在 Android 上，这个方法只会返回 `false`。它的主要作用是给跨平台库补齐 API 面，让代码可以编译，不是 Android 侧已经提供了 Project Loom 运行时。当前 SDK 里也没有公开的 `Thread.startVirtualThread(...)` 入口，所以不要把 Android 16 视为“已经支持虚拟线程”。

应用侧如果需要轻量级并发，Kotlin Coroutine 仍然是当前可用的主方案。多平台共享库可以把 `isVirtual()` 当能力探测点，但不要在 Android 上按虚拟线程的调度语义设计线程模型。

[已验证: Android SDK android-Baklava stubs, java/lang/Thread.java]

## HandlerThread、IntentService 与 WorkManager

上一节梳理了从 AsyncTask 到 Coroutine 的演进——这些方案解决的是「在哪个线程上执行异步任务」的问题。但 Android 还提供了一些专门的后台执行机制，定位更偏「任务调度」而非「线程切换」。这一节我们快速过一遍它们的适用场景。

### HandlerThread：带 Looper 的后台线程

HandlerThread 继承自 Thread，它在线程启动后自动创建 Looper 并进入消息循环。因此我们可以像操作主线程一样，通过 Handler 向它发送消息。

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
| 精确定时的重复任务 | AlarmManager（需要 `SCHEDULE_EXACT_ALARM` 权限，API 31+） |

> **WorkManager `PeriodicWorkRequest` 的限制**：最小周期间隔 15 分钟，执行时间受 Doze 省电模式和电池优化影响，不保证精确触发。业务要求精确定时（闹钟、定时提醒）时，使用 `AlarmManager` 的 `setExactAndAllowWhileIdle()`，并在 Android 12（API 31）及以上声明 `SCHEDULE_EXACT_ALARM` 权限（用户可在系统设置中撤销）。API 33+ 对闹钟类应用提供 `USE_EXACT_ALARM` 权限，不需要用户授权。

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

Choreographer 也使用了同样的模式：通过 `ThreadLocal` 为每个线程存储一个独立的 Choreographer 实例。AOSP `Choreographer` 的 `sThreadInstance.initialValue()` 会对任何已有 Looper 的线程创建实例，构造函数里会注册 `FrameDisplayEventReceiver(looper, VSYNC_SOURCE_APP)` 来接收 VSync 信号。任何有 Looper 的线程调用了 `Choreographer.getInstance()` 之后，都能收到 VSync 回调，没有主线程限制。

日常分析中通常只看到主线程的 Choreographer 驱动渲染，原因是 `ViewRootImpl.scheduleTraversals()` 通过 `Choreographer.getInstance()` 拿到的是主线程的实例，`doFrame()` → Traversal 调度链绑在主线程上。如果其他线程也创建了自己的 Choreographer 并通过 `postFrameCallback` 注册回调，那个线程的 Choreographer 同样会收到 VSync 并执行回调。Perfetto 里看到非主线程出现 `Choreographer#doFrame` slice 时，先检查该线程是否注册了自己的 Choreographer，不要直接当成异常。

[已验证: AOSP android-16.0.0_r1, frameworks/base/core/java/android/view/Choreographer.java — sThreadInstance.initialValue() 创建 FrameDisplayEventReceiver; frameworks/base/core/java/android/os/Looper.java]

## 在 Perfetto 中的表现

理解了线程模型之后，我们在 Perfetto 中就可以有目的地观察线程行为：

### 识别关键线程

在 App 进程下，我们会看到以下几个重要的线程：

- **主线程（UI Thread）**：通常显示为进程包名或 `CrBrowserMain`（WebView 场景），处理 Input、Animation、Traversal 和所有 Handler 消息。
- **RenderThread**：App 进程下的渲染线程，执行 GPU 渲染命令。它的活动紧跟在主线程的 `syncAndDrawFrame` 之后。
- **Binder 线程**：名字类似 `Binder:12345_1`，处理来自其他进程的 Binder 调用。如果这些线程有长时间的 CPU 活动，说明 App 在响应跨进程调用。
- **FinalizerDaemon**：执行对象 finalize 方法的守护线程。如果这个线程频繁活动，说明有大量对象在被 GC 回收时需要执行 finalize，这可能导致 GC 暂停时间变长。
- **DefaultDispatcher-worker-\***：Kotlin Coroutine 的默认线程池线程。
- **MQ.Delivered 计数器**：Perfetto 中 `mq` 类别下的 `MQ.Delivered` 计数器，记录 MessageQueue 中消息的投递频率。`LegacyMessageQueue`、`CombinedMessageQueue`、`ConcurrentMessageQueue` 三种实现都会记录该计数器，不能用它区分队列实现。区分队列实现的可靠信号：① targetSdk 37 + `USE_NEW_MESSAGEQUEUE` compat change 标志（新队列启用边界）；② `mMessages` 在新实现下恒为 null 的兼容性行为；③ MessageQueue monitor contention 是否消失（新队列消除了 `mMessages` 锁争用）；④ FrameTimeline / jank_type 与 Looper dispatch 片段同窗对齐。

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

Android Framework 对线程数量的控制体现在多个层面。Binder 这里要把两个数字拆开看。`ProcessState.cpp` 里的 `DEFAULT_MAX_BINDER_THREADS=15`，指的是通过 `BINDER_SET_MAX_THREADS` 告诉内核最多再拉起 15 个额外的 Binder worker。与此同时，`startThreadPool()` 会先启动 1 个 pooled thread。于是常见默认配置下，我们会看到 1 个已启动 worker，加上最多 15 个内核追加 worker，也就是最多 16 个 pooled worker。§1.4 写“默认上限 15 个”时，指的是 `DEFAULT_MAX_BINDER_THREADS` 这个驱动配置值；这里写 16，指的是把 `startThreadPool()` 先启动的那个 worker 一起算进去。两种口径说的是同一件事，这里同样不把 App 主线程算进去。`Dispatchers.IO` 和 `Dispatchers.Default` 也各自有并行度上限，目的都是在吞吐量和调度开销之间取平衡。

[已验证: AOSP android-16.0.0_r1, frameworks/native/libs/binder/ProcessState.cpp, DEFAULT_MAX_BINDER_THREADS=15；startThreadPool()；getThreadPoolMaxTotalThreadCount()]
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
- **1.13 MessageQueue 机制与 DeliQueue 无锁优化**：本章先用经典 Looper / Handler 理解方式讲清主线，android-16 以后队列内部实现的演进在 1.13 展开
- **2.4 Choreographer 与渲染流水线**：Choreographer 通过主线程的 Handler 监听 VSync 信号，驱动每帧的渲染
- **2.5 MainThread 与 RenderThread 协作**：本章的 RenderThread 部分在 2.5 中有更详细的工作流程分析
- **5.1 Linux 进程调度基础**：nice 值、cgroup、调度策略的底层原理在 CPU 章节中深入展开

## 参考资料

- AOSP 源码路径：
  - `frameworks/base/core/java/android/os/Looper.java` — Looper 核心，消息循环引擎
  - `frameworks/base/core/java/android/os/LegacyMessageQueue/MessageQueue.java` — android-16 中保留经典链式语义的 MessageQueue 实现
  - `frameworks/base/core/java/android/os/CombinedMessageQueue/MessageQueue.java` — android-16 并存的 MessageQueue 实现之一
  - `frameworks/base/core/java/android/os/ConcurrentMessageQueue/MessageQueue.java` — android-16 并存的 MessageQueue 实现之一
  - `frameworks/base/core/java/android/os/Handler.java` — Handler，消息发送与处理
  - `frameworks/base/core/java/android/app/ActivityThread.java` — 主线程入口，四大组件消息处理
  - `frameworks/base/graphics/java/android/graphics/HardwareRenderer.java` — `syncAndDrawFrame()` Java 入口
  - `frameworks/base/libs/hwui/renderthread/RenderThread.cpp` — RenderThread native 实现
  - `frameworks/base/libs/hwui/renderthread/RenderProxy.cpp` — 主线程与 RenderThread 的同步桥接
  - `frameworks/native/libs/binder/ProcessState.cpp` — Binder pool 默认线程上限
  - `frameworks/base/core/java/android/os/Process.java` — 线程优先级设置
  - `system/core/libutils/Looper.cpp` — Native Looper，epoll 实现
- 官方文档：
  - [Processes and Threads | Android Developers](https://developer.android.com/guide/components/processes-and-threads)
  - [Kotlin Coroutines on Android](https://developer.android.com/kotlin/coroutines)
  - [WorkManager | Android Developers](https://developer.android.com/topic/libraries/architecture/workmanager)
  - [Process.setThreadPriority | Android Developers](https://developer.android.com/reference/android/os/Process#setThreadPriority(int,int))
  - [TestLooperManager | Android Developers](https://developer.android.com/reference/android/os/TestLooperManager)
- 高爷原创文章：
  - [Android Perfetto 系列 7 - MainThread 和 RenderThread 解读](https://www.androidperformance.com/2025/08/02/Android-Perfetto-07-MainThread-And-RenderThread/) — Perfetto 视角下的双线程渲染架构详解
  - [Android Systrace 基础知识 - MainThread 和 RenderThread 解读](https://www.androidperformance.com/2019/11/06/Android-Systrace-MainThread-And-RenderThread/) — Systrace 视角下的双线程分析
- 其他参考：
  - [Looper到底在等什么？](https://mp.weixin.qq.com/s/Z3d8e48e3b17fc95113d46e50b95893) — Looper 的 epoll 机制详解（芦半山）
  - [Android性能优化之绑定RenderThread到大核CPU](https://www.yanzhenjie.com/post/20241221/1f3fc18c6801/) — sched_setaffinity 实践（严振杰）
  - Android SDK `platforms/android-Baklava/android-stubs-src.jar` 中的 `java/lang/Thread.java` — `isVirtual()` 注释明确写明虚拟线程尚未在 Android 上实现
