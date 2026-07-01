---
title: "MessageQueue 机制与 DeliQueue 无锁优化"
chapter: "1.13"
section: "1.13"
status: ready-for-review
applicable_versions: "传统 MessageQueue:Android 1.0 (API 1)+;并发实现公开源码:Android 16;面向应用默认启用:Android 17 (API 37)"
drafted_date: "2026-04-04"
reviewed_date: "2026-05-27"
reviewed_by: openclaw-task6
last_verified: "2026-04-24"
last_verified_against: "AOSP android-17.0.0_r1"
confidence: medium
sources:
  - type: doc
    path: "https://developer.android.com/about/versions/17/changes/messagequeue"
  - type: doc
    path: "https://developer.android.com/reference/android/os/MessageQueue.IdleHandler"
  - type: blog
    path: "https://android-developers.googleblog.com/2026/02/under-hood-android-17s-lock-free.html"
  - type: aosp
    path: "frameworks/base/core/java/android/os/Looper.java (android-16.0.0_r1)"
  - type: aosp
    path: "frameworks/base/core/java/android/os/MessageQueue.java (android-15.0.0_r1)"
  - type: aosp
    path: "frameworks/base/core/java/android/os/CombinedMessageQueue/MessageQueue.java (android-16.0.0_r1)"
  - type: aosp
    path: "frameworks/base/core/java/android/os/ConcurrentMessageQueue/MessageQueue.java (android-16.0.0_r1)"
  - type: aosp
    path: "frameworks/base/core/java/android/os/LegacyMessageQueue/MessageQueue.java (android-16.0.0_r1)"
  - type: wiki
    path: "https://en.wikipedia.org/wiki/Treiber_Stack"
tags:
  - android
  - looper
  - messagequeue
  - deliqueue
related_chapters: ["1.5", "1.14", "2.4", "2.5", "7.1"]
task6_state: reviewed
task6_result: pass-light-edit
last_task6_review_log: "logs/review/2026-06-14-08-review.md"
task9_state: reviewed
task9_result: needs-rework
last_task9_autofix_at: "2026-06-14"
last_task9_at: "2026-07-01T20:36:16+08:00"
task9_reviewed_by: openclaw-task9
task9_reviewed_date: "2026-07-01"
task2b_state: pending
task2b_result: "fixed"
pipeline_stage: task2b_pending
last_task2b_at: "2026-05-27T12:50:00+08:00"
task9_review_notes: "2026-05-27 13:20 Task9：pass-tech-review。复核 Android 16 Combined/Concurrent/Legacy MessageQueue 路径、Android 17 行为变更页、DeliQueue 官方性能数据；未发现 P0/P1，自动晋升 finalized。 | 2026-06-14 08 Task9 deep-review: pass-tech-review。P0 0 / P1 0 / P2 0 / P3 0；复核 Android 16 Combined/Concurrent/Legacy MessageQueue 源码路径、Android 17 MessageQueue 行为变更页、官方 DeliQueue 性能数据与内部交叉引用；无阻断问题，Task6 已通过且 queue 无 pending，自动晋升 finalized。 | 2026-06-22 16 Task9 deep-review: pass-tech-review。P0 0 / P1 0 / P2 0 / P3 0；复核 AOSP android-16.0.0_r1 Combined/Concurrent/Legacy MessageQueue、Android 17 MessageQueue 行为变更页与官方性能数据；Android 17/API 37 边界清楚，无 P0/P1。 | 2026-07-01 20 Task9 deep-review: needs-rework。P0 0 / P1 1 / P2 0；正文仍以 Android 16 ConcurrentMessageQueue/ConcurrentSkipListSet 作为 Android 17 新 MessageQueue 的主要源码说明，缺少 android-17.0.0_r1 CombinedDeliMessageQueue/MessageStack/MessageHeap 主线锚点，已写入 Task2B queue。"
task6_reviewed_date: "2026-07-01"
last_task6_at: "2026-07-01T22:13:00+08:00"
task6_review_notes: "06-14 08 Task6 revisiting：pass-light-edit。L1 小修 3 处（3.3.9 形容词+冒号起手式 ×3）；outline 5/5 覆盖。07-01 22 Task6 revisiting：pass-light-edit。L1 小修 2 处（3.3.9 形容词+冒号 ×2：分工很清晰→按固定顺序执行、区分很关键→在trace里直接体现）；outline 5/5 覆盖；Task9 needs-rework P1:1（android-17 源码锚点缺失），待 Task2B 修复。"
last_task9_audit: "2026-06-14"
last_task9_audit_log: "logs/deep-review/2026-06-14-04-audit.md"
task9_audit_notes: "2026-06-14 Task9 idle audit: auto-fixed。P0 1：将不可定位的 `ConcurrentMessageQueue.java` 文件名修正为 AOSP android-16.0.0_r1 实际路径 `ConcurrentMessageQueue/MessageQueue.java`。"
last_task9_review_log: "logs/deep-review/2026-07-01-20-deep-review.md"
p0: 0
p1: 1
p2: 0
finalized_by: "openclaw-task9-auto-promote"
finalized_date: "2026-06-14"
updated_by: "openclaw-task9"
updated_date: "2026-06-22"
deepseek_cn_review_state: done
last_deepseek_cn_review_at: 2026-06-23
last_task6_audit: "2026-06-20"
---

# 1.13 MessageQueue 机制与 DeliQueue 无锁优化

<!-- outline-start -->
## 本节要点大纲

### 锚点(必须覆盖)

- 🔹 MessageQueue 在主线程事件循环中的角色
- 🔹 传统 `synchronized` 链表为什么会带来锁竞争
- 🔹 `Looper.next()` 的工作机制,包括 epoll、同步屏障与 IdleHandler
- 🔹 Android 16 公开源码里的 Combined/ConcurrentMessageQueue 与 Android 17 默认启用边界
- 🔹 新实现里 barrier、async queue、取消路径如何配合，以及 Perfetto 中的观察方法

### 扩展(可选深入)

- 🔸 兼容性影响:`mMessages` 反射、Espresso、Robolectric
- 🔸 Choreographer 的异步消息为什么仍然能越过同步屏障

### OpenClaw 加工指引

> 这一节要把三件事分开写清楚:消息入队、消息出队、消息分发。
> 旧实现的问题集中在前两者共用一把 monitor;耗时 layout/draw 发生在分发阶段。
> Android 17 的公开页面只确认"新的 lock-free MessageQueue 默认启用",
> 数据结构细节要以公开 AOSP tag 为准,不用二手文章替代源码。
<!-- outline-end -->

## 为什么要了解 MessageQueue

主线程卡顿并不都发生在 `doFrame()` 里面。很多 trace 往下展开后,会先看到主线程在等一把锁,随后 `doFrame()` 才被整体推迟。排查这类问题时,如果把注意力只放在 layout、draw 或 Binder 调用上,容易漏掉调度层本身的竞争。

MessageQueue 就在这个位置上。Input 事件、`Handler.post()`、`Choreographer` 的 VSync 回调,最终都要先进入 MessageQueue,再由 `Looper` 取出并分发。只要入队和出队的同步方式出现瓶颈，主线程的帧预算首先就会消耗在队列入口。

本文沿用社区里对新实现的称呼 **DeliQueue**。公开官方页面用的名字更朴素,就是 **lock-free MessageQueue**。两个名字指向同一件事:Android 17 面向 `targetSdk 37` 的应用,把旧的单一 monitor 方案换成了新的无锁实现。

## MessageQueue 在主线程里扮演什么角色

先把队列操作和业务执行分开。`Looper.loopOnce()` 在 Android 16 中按固定顺序执行：先调用 `me.mQueue.next()` 取消息，拿到消息后才进入 `msg.target.dispatchMessage(msg)`：

```java
// frameworks/base/core/java/android/os/Looper.java
// @ AOSP android-16.0.0_r1
private static boolean loopOnce(final Looper me, /* 省略其他参数 */) {
    Message msg = me.mQueue.next(); // 取消息，可能阻塞
    if (msg == null) {
        return false;
    }
    // 省略日志、观察者回调等无关代码
    msg.target.dispatchMessage(msg); // 分发 Handler / Runnable
    // 省略消息回收等无关代码
}
```

这条边界很重要。复杂 layout、draw、Binder 回调、数据库访问,都发生在 `dispatchMessage()` 之后。它们会拖慢一帧,也会推迟下一次 `next()` 的时点;它们不会直接拉长本次 `MessageQueue` 的锁持有时间。如果把这两段混在一起看，后续因果分析会走偏。

## 传统实现为什么容易出现锁竞争

旧实现的公开参考可以直接看 `android-15.0.0_r1` 的 `MessageQueue.java`。它的核心结构是一条按 `when` 排序的单链表,`enqueueMessage()` 和 `next()` 都围着同一个 `synchronized (this)` 运转。

```java
// frameworks/base/core/java/android/os/MessageQueue.java
// @ AOSP android-15.0.0_r1
boolean enqueueMessage(Message msg, long when) {
    // 省略参数校验、消息标记等无关代码
    synchronized (this) {
        // 省略退出状态检查等无关代码
        Message p = mMessages;
        if (p == null || when == 0 || when < p.when) {
            msg.next = p;
            mMessages = msg;
        } else {
            // 省略在链表中间按时间插入的遍历代码
        }
        if (needWake) nativeWake(mPtr);
    }
    return true;
}
```

竞争发生在三处：

1. 后台线程往主线程 `post` 消息时,要抢这把 monitor。
2. 主线程调用 `next()` 扫描队列、处理同步屏障时,也要抢这把 monitor。
3. `removeMessages()`、`removeCallbacksAndMessages()`、`removeSyncBarrier()` 这类操作同样会碰这把 monitor。

一旦多个线程同时高频 `post`,旧实现就会把它们串行化。主线程如果刚好也在 `next()` 里扫描队列,后台线程就得等;后台线程先拿到锁,主线程也得等。调度层的延迟就这样叠起来了。

[图:旧 MessageQueue 的典型竞争流程。多个生产者线程同时调用 `enqueueMessage()`,UI 线程在 `next()` 里扫描链表,三者共用一把 monitor。]

### 哪些场景更容易把问题放大

有两类场景经常把这个瓶颈放大:

- 后台线程密集往主线程发消息,比如实时流、频繁状态刷新、复杂初始化。
- 主线程业务很忙,导致它下一次回到 `next()` 的时间被推迟。这里受影响的是"回到队列口的时机",不是"当前这次 queue 锁持有得更久"。

这个区分在 trace 里直接体现：如果看到 `dispatchMessage()` 很长,那是业务执行慢;如果看到 `enqueueMessage()` 或 `next()` 周边出现 monitor contention,那才是队列竞争。

## `next()` 里面到底做了什么

`next()` 不只是"拿链表头部元素"。旧实现至少有三层逻辑:native poll、同步屏障、IdleHandler。

```java
// frameworks/base/core/java/android/os/MessageQueue.java
// @ AOSP android-15.0.0_r1(节选)
Message next() {
    // 省略空闲处理和超时计算等无关代码
    nativePollOnce(mPtr, nextPollTimeoutMillis);
    synchronized (this) {
        Message msg = mMessages;
        if (msg != null && msg.target == null) {
            do {
                prevMsg = msg;
                msg = msg.next;
            } while (msg != null && !msg.isAsynchronous());
        }
        // 省略消息返回和 IdleHandler 调度等无关代码
    }
}
```

### 1. `nativePollOnce()` / epoll

队列空闲时,Looper 不会忙等,而是进入 native poll。新消息插入后,`nativeWake()` 把它唤醒。这一层在 Android 17 也保留了下来。变的是 Java 层队列结构，Looper 并没有被改成自旋线程。

### 2. 同步屏障

旧实现里,`target == null` 的消息就是同步屏障。队列头如果是 barrier,`next()` 会跳过同步消息,继续找第一个异步消息。`Choreographer` 发出来的 VSync 回调就是靠异步消息走这条通道。

### 3. IdleHandler

`MessageQueue.IdleHandler` 不是 Android 5.0 才有。官方 API 文档明确写的是 **Added in API level 1**。它和同步屏障也不是一回事。IdleHandler 处理的是"队列准备休眠前的空闲回调",同步屏障处理的是"同步消息先别过,先放异步消息走"。

把这两件事拆开后,版本演进才不会写乱:IdleHandler 从 API 1 就在,Choreographer 大规模使用同步屏障是 API 16 之后的事情。

## Android 16 和 Android 17 要分成两步看

这里最容易写乱。

### Android 16:公开源码里已经有并发实现,但默认范围很窄

`android-16.0.0_r1` 的 `CombinedMessageQueue/MessageQueue.java` 注释写道：

- **legacy implementation is used by default**
- **concurrent implementation is used for system processes**
- **SystemUI 也被显式放进允许名单**

也就是说,Android 16 公开源码已经把新旧两套实现放进来了,但不是所有应用都默认切过去。它更像 rollout 阶段:先给 system processes 和 SystemUI 用,普通应用为了兼容性仍然默认走 legacy。

`android-16.0.0_r1` 里实际存在的是 `CombinedMessageQueue/MessageQueue.java` 和 `ConcurrentMessageQueue/MessageQueue.java`。`CombinedMessageQueue` 内部通过 `mUseConcurrent` 标志和进程 allowlist 决定走 concurrent 还是 legacy 路径——这是一种中间态：生产者侧尽量无锁，Looper 侧继续集中整理 ready 消息。把它和 `LegacyMessageQueue`、`ConcurrentMessageQueue` 放在一起看，Android 16 的真实状态更接近"多变体并存的 rollout"，系统会按进程类型和兼容性风险选择不同实现。

### Android 17:面向应用的默认启用

Android 17 的行为变更页面把面向应用的边界写清楚了:

- `targetSdk 37` 的应用默认启用新的 lock-free MessageQueue。
- 调试时可以用 `adb am compat enable USE_NEW_MESSAGEQUEUE <package>` 提前打开。
- 如果要排查兼容性,也可以用 `adb am compat disable USE_NEW_MESSAGEQUEUE <package>` 临时退回旧实现。

因此本文里的版本边界要这样理解:

- **Android 16**：公开源码出现 CombinedMessageQueue 和 ConcurrentMessageQueue，属于内部试点和受控 rollout。
- **Android 17**:新的 MessageQueue 对 `targetSdk 37` 的应用默认生效,进入 app-facing 阶段。

## 公开源码里能确认哪些并发结构

如果只看 `android-16.0.0_r1` 公开源码,能确认的事情有四件。

### 1. 生产者路径是 Treiber 风格的无锁栈

`ConcurrentMessageQueue` 维护了一组 stack state node。非 Looper 线程入队时,通过 CAS 把新的 `MessageNode` 挂到栈顶。这里属于典型的 Treiber stack 家族:单指针、CAS、失败就重试。

这个结论能说明两件事:

- 它不是 CLH 队列。
- "单指针 CAS 完全避免 ABA"这种表述不成立。Treiber stack 本来就是 ABA 讨论最常出现的对象。单指针让实现更直,生命周期、可见性和删除竞争仍然要靠额外设计处理。

Android 的公开实现里,相关处理分散在 state node、取消路径、`nextMessage()` 的重试逻辑和消息生命周期管理里。源码没有支持"天然完全避免 ABA"这个结论。

### 2. 消费者端不是单一优先队列模型,公开源码里至少有两组有序优先队列

`ConcurrentMessageQueue/MessageQueue.java` 直接引入了 `ConcurrentSkipListSet`。`nextMessage()` 里的注释也写明白了:

> We have two queues to juggle and the presence of barriers throws an additional wrench into our plans.

公开源码里至少有两组队列:

- `mPriorityQueue`
- `mAsyncPriorityQueue`

这和"Treiber 栈 + 一个最小堆"的单线条描述不一样。Barrier、同步消息、异步消息,要在两组有序队列之间一起调度。

### 3. barrier 和 async queue 仍然存在,而且逻辑被保留下来了

`nextMessage()` 的分支：

- 如果普通队列头部是 barrier,就优先从 `mAsyncPriorityQueue` 里挑 ready 的异步消息。
- 如果没有 barrier,就在普通队列和异步队列里选 `when` 更早的那个。

所以新实现没有把"VSync 回调如何越过同步屏障"这条语义抹掉。它只是把底层同步方式换了。`Choreographer` 这类异步消息仍然能拿到自己的优先通道。

### 4. 取消路径会和 drain / 遍历竞争,源码里明确提到 tombstone

公开源码注释里能直接看到 `tombstoned messages`,也能看到 `remove()` 可能在 `nextMessage()` 遍历期间把节点删掉,所以 `nextMessage()` 需要在竞争下重试。

这一点足够支撑保守表述:取消路径已经不再是旧时代那种"围着同一条链表和同一把 monitor 反复遍历"。它会和 drain、遍历、唤醒一起协同工作。把它简化成"单线程最小堆,只有 Looper 线程访问"会把公开源码里已经存在的并发细节抹掉。

## Choreographer、同步屏障和新队列怎么接起来

这部分顺着 VSync 回调看更清楚。

旧实现里,`Choreographer` 通过异步消息越过同步屏障。新实现里,这条语义没有变,只是实现层从"链表 + monitor"换成了"无锁入栈 + drain + 两组有序优先队列"。

工程上可以这样理解:

1. `Choreographer` 仍然投递异步消息。
2. 如果队列头部存在 barrier,`nextMessage()` 仍然会优先检查异步队列。
3. 变化发生在入队和取消阶段。生产者线程不再和主线程争抢同一把 Java monitor。

对渲染流程的影响也要这样写:新实现减少的是 **queue operation 的竞争**,不是把 layout、draw、measure 本身做快了。布局开销仍在 `dispatchMessage()` 之后;VSync 到 `doFrame()` 的抖动,则有机会因为队列竞争减少而更稳定。

[图:传统实现与并发实现的 VSync 调度对比。上半部分画 barrier + async message 如何越过同步消息;下半部分画 Android 16 legacy 与 Android 17 新实现下的入队路径差异,重点标出后台线程 `enqueueMessage()`、主线程 `next()`、VSync-app 到 `doFrame()` 之间的等待位置。]

如果手里暂时没有同机型双版本 trace,这里先用等价图示更稳。图里只需要标三处:`VSYNC-app` 的到达点、主线程从 `nativePollOnce()` 返回到 `doFrame` 的间隔、以及旧实现里可能出现的 main thread monitor contention / blocked 片段。这样读者至少知道要去哪里看,而不是只看一句"锁竞争减少了"。

## 量化数据现在该怎么写

这一节可以恢复一组公开可追溯的数字,但要把实验场景一起写出来。Android Developers Blog 在 2026-02-17 发布的《Under the hood: Android 17's lock-free MessageQueue》中给了三类数据:

- **Synthetic benchmarks**:多线程向 busy queues 插入消息,最高可到 **5,000x faster**。这个数字对应极端竞争压测,用来说明新队列把生产者竞争从 monitor 切到了无锁结构。
- **Perfetto traces acquired from internal beta testers**:App 主线程花在 lock contention 上的时间下降 **15%**。
- **On the same test devices**:应用 missed frames 下降 **4%**,System UI 和 Launcher 交互的 missed frames 下降 **7.7%**,应用启动到首帧绘制的 95 分位缩短 **9.1%**。

正文引用时要把边界一起写上:

- `5,000x` 属于合成基准,不代表普通业务代码会得到同量级收益。
- `15%` 和掉帧改善来自 Google 内部 beta 设备与既定 workload,适合说明方向,不适合外推成所有机型的统一收益。
- 如果要写自己项目的结果,仍然要补设备、系统版本、并发模型、trace 口径和统计窗口。

## 兼容性和迁移影响

Android 17 行为变更页面已经把兼容性风险点写得很具体。

### `mMessages` 反射会失效

旧实现里,很多测试框架或自定义工具会反射 `MessageQueue.mMessages`。Android 17 为了二进制兼容把这个字段保留下来,但官方页面明确说明:

- 新实现里 `mMessages` **always null**
- 即使队列里真的有消息,它也不会再反映真实内容

如果项目里还有这类反射逻辑,迁移到 `targetSdk 37` 后先查这里,不要先怀疑系统调度器本身坏了。

### 测试框架需要升级

官方建议是:

- Espresso 升到 **3.7.0+**,改用 `TestLooperManager` 等公开 API。
- Robolectric 升到 **4.17+**,`@LooperMode(LEGACY)` 迁到 `@LooperMode(PAUSED)`。

### 兼容开关可以拿来做 A/B 排查

如果 retarget 到 Android 17 后出现 crash、UI 异常、测试不稳定，可以先做一项对照:

```bash
adb am compat enable USE_NEW_MESSAGEQUEUE <your-package-name>
adb am compat disable USE_NEW_MESSAGEQUEUE <your-package-name>
```

同一 workload 下切换开关,能很快分出结论会落在新队列语义、反射兼容,还是业务本身。

## 在 Perfetto 里怎么用这节知识

这节内容落到 trace 里,重点看三处。

### 1. 先分清卡顿发生在队列口,还是发生在消息分发里

- `enqueueMessage()` / `next()` 周边出现 monitor contention,说明旧实现的队列竞争在放大问题。
- `dispatchMessage()` 很长,说明业务本身慢,问题不在队列锁。

### 2. 升到 Android 17 后，如果 contention 消失但帧还是慢，继续检查后续路径

这时该回头看后续慢路径：layout、draw、Binder、数据库、I/O、锁竞争、GPU backpressure。

### 3. 迁移问题和性能问题要分开

如果 `targetSdk 37` 后测试挂了、反射拿不到队列内容、旧监控脚本失效,这更像兼容性问题。它和"主线程调度有没有更稳"是两类事。

[图:Perfetto 观察路径示意。左侧画 Android 16 legacy 场景,标出 `VSYNC-app`、`doFrame`、main thread 的 blocked/monitor contention 片段;右侧画 Android 17 新实现场景,标出 contention 缩短或消失后,仍需继续检查 `dispatchMessage()`、layout、draw 的位置。]

## 版本演进

| Android 版本 | 变化 |
| --- | --- |
| Android 1.0 (API 1) | `MessageQueue` 和 `IdleHandler` 已存在 |
| Android 4.1 (API 16) | `Choreographer` 开始大规模使用同步屏障 + 异步消息 |
| Android 15 (API 35) | 公开 legacy 参考仍是单链表 + `synchronized` |
| Android 16 (API 36) | 公开源码出现 `CombinedMessageQueue`,内部通过 `mUseConcurrent` 标志和 allowlist 选择 legacy 或 concurrent 实现;同时放出 `LegacyMessageQueue`、`ConcurrentMessageQueue` 多种实现;legacy 默认,concurrent 先给 system processes / SystemUI |
| Android 17 (API 37) | `targetSdk 37` 的应用默认启用新的 lock-free MessageQueue |

## 常见误区

### "复杂 layout 会让 `next()` 持锁更久"

不会。复杂 layout 会把主线程卡在 `dispatchMessage()` 这段业务执行里,影响下一次取消息和整帧预算。`loopOnce()` 在 `me.mQueue.next()` 和 `msg.target.dispatchMessage(msg)` 之间有明确边界,这两段要分开看。

### "Android 16 已经把所有应用都切到 DeliQueue 了"

没有。公开源码写的是 legacy 默认,并发实现先给 system processes 和 SystemUI。`CombinedMessageQueue` 内部的 `mUseConcurrent` allowlist 也说明 Android 16 仍处在受控 rollout 阶段。把 Android 16 的内部 rollout 和 Android 17 的 app-facing default 写成一条线,版本边界就会失真。

### "新实现里还是能从 `mMessages` 看见真实队列"

官方页面已经明确：这个字段还在，但值固定不再代表真实队列内容。

### "DeliQueue 引入了新的任务优先级重排机制"

公开源码能确认的调度语义还是 `when`、barrier、async message 这三件事。它换的是队列结构和同步方式，不是给应用层额外加入新的优先级系统。

## 收尾

排查主线程调度问题，先把流程切成三段：**入队、出队、分发**。旧 MessageQueue 的瓶颈集中在前两段共用一把 monitor；Android 16 公开源码已经能看到 legacy / concurrent 多变体试点；Android 17 把这件事推到了面向应用的默认行为。

这节最值得带走的判断有两个：

- trace 里 `dispatchMessage()` 长是业务执行慢，不要先归因到 MessageQueue。
- retarget 到 Android 17 后，测试框架、反射代码、旧监控脚本先出问题，先查 `mMessages` 和测试库版本，再查业务逻辑。

## 参考资料

- DeepResearch, Android 17 DeliQueue 无锁 MessageQueue 与 RecyclerView 预取机制
  `/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/DeepResearch/2026-05-24-android17-deli-queue-recyclerview-prefetch.md`

- Android Developers, MessageQueue behavior change guidance
  https://developer.android.com/about/versions/17/changes/messagequeue
- Android Developers, `MessageQueue.IdleHandler`
  https://developer.android.com/reference/android/os/MessageQueue.IdleHandler
- AOSP `android-15.0.0_r1`
  `frameworks/base/core/java/android/os/MessageQueue.java`
- AOSP `android-16.0.0_r1`
  `frameworks/base/core/java/android/os/Looper.java`
- AOSP `android-16.0.0_r1`
  `frameworks/base/core/java/android/os/CombinedMessageQueue/MessageQueue.java`
- AOSP `android-16.0.0_r1`
  `frameworks/base/core/java/android/os/ConcurrentMessageQueue/MessageQueue.java`
- AOSP `android-16.0.0_r1`
  `frameworks/base/core/java/android/os/LegacyMessageQueue/MessageQueue.java`
- Treiber stack
  https://en.wikipedia.org/wiki/Treiber_Stack
