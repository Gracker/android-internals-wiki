---
title: MessageQueue 机制与 DeliQueue 无锁优化
chapter: '1.13'
section: '1.13'
status: finalized
applicable_versions: Android 1.0 (API 1) - Android 17 (API 37)
last_verified: '2026-07-25'
last_verified_against: AOSP android-17.0.0_r1 + Android 17 official documentation
confidence: high
sources:
  - type: aosp
    path: "frameworks/base/core/java/android/os/CombinedDeliMessageQueue/README.md @ android-17.0.0_r1"
  - type: aosp
    path: "frameworks/base/core/java/android/os/CombinedDeliMessageQueue/MessageQueue.java @ android-17.0.0_r1"
  - type: aosp
    path: "frameworks/base/core/java/android/os/MessageStack.java @ android-17.0.0_r1"
  - type: aosp
    path: "frameworks/base/core/java/android/os/MessageHeap.java @ android-17.0.0_r1"
  - type: aosp
    path: "frameworks/base/core/java/android/os/Message.java @ android-17.0.0_r1"
  - type: aosp
    path: "frameworks/base/core/java/android/os/Looper.java @ android-17.0.0_r1"
  - type: aosp
    path: "frameworks/base/core/java/android/app/ActivityThread.java @ android-17.0.0_r1"
  - type: aosp
    path: "frameworks/base/core/java/android/os/ZygoteProcess.java @ android-17.0.0_r1"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/am/ProcessList.java @ android-17.0.0_r1"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/compat/PlatformCompat.java @ android-17.0.0_r1"
  - type: aosp
    path: "frameworks/base/core/jni/android_os_MessageQueue.cpp @ android-17.0.0_r1"
  - type: aosp
    path: "system/core/libutils/Looper.cpp @ android-17.0.0_r1"
  - type: official
    path: "https://developer.android.com/about/versions/17/changes/messagequeue"
  - type: official
    path: "https://developer.android.com/about/versions/17/behavior-changes-17"
  - type: official
    path: "https://developer.android.com/reference/android/os/MessageQueue.IdleHandler"
  - type: official
    path: "https://android-developers.googleblog.com/2026/02/under-hood-android-17s-lock-free.html"
tags:
  - android
  - looper
  - handler
  - messagequeue
  - deliqueue
  - perfetto
related_chapters:
  - '1.5'
  - '1.14'
  - '2.4'
  - '2.5'
  - '7.1'
drafted_date: '2026-04-04'
reviewed_date: '2026-07-25'
reviewed_by: Codex
task6_state: reviewed
task6_result: pass-light-edit
task9_state: reviewed
task9_result: pass-tech-review
task2b_state: fixed
task2b_result: fixed
pipeline_stage: ready-to-publish
deepseek_cn_review_state: done
last_task6_review_log: "logs/review/2026-07-14-22-review.md"
last_task9_review_log: "logs/deep-review/2026-07-02-02-deep-review.md"
last_task9_at: "2026-07-14T22:20:00+08:00"
last_task9_review_notes: "2026-07-14 Task9 deep-review: pass-tech-review。P0 0 / P1 1 / P2 1。已修复单指针 CAS ABA 表述；Android 17 源码锚点完整，性能数据引用口径准确。"
last_task9_autofix_at: "2026-07-14"
task9_reviewed_by: "openclaw-task9"
task9_reviewed_date: "2026-07-02"
last_task2b_at: "2026-05-27T12:50:00+08:00"
last_task2b_lite_at: "2026-07-14"
task2b_main_at: "2026-07-02T00:57:10.552430+08:00"
task9_review_notes: "2026-05-27 13:20 Task9：pass-tech-review。复核 Android 16 Combined/Concurrent/Legacy MessageQueue 路径、Android 17 行为变更页、DeliQueue 官方性能数据；未发现 P0/P1，自动晋升 finalized。 | 2026-06-14 08 Task9 deep-review: pass-tech-review。P0 0 / P1 0 / P2 0 / P3 0；复核 Android 16 Combined/Concurrent/Legacy MessageQueue 源码路径、Android 17 MessageQueue 行为变更页、官方 DeliQueue 性能数据与内部交叉引用；无阻断问题，Task6 已通过且 queue 无 pending，自动晋升 finalized。 | 2026-06-22 16 Task9 deep-review: pass-tech-review。P0 0 / P1 0 / P2 0 / P3 0；复核 AOSP android-16.0.0_r1 Combined/Concurrent/Legacy MessageQueue、Android 17 MessageQueue 行为变更页与官方性能数据；Android 17/API 37 边界清楚，无 P0/P1。 | 2026-07-01 20 Task9 deep-review: needs-rework。P0 0 / P1 1 / P2 0；正文仍以 Android 16 ConcurrentMessageQueue/ConcurrentSkipListSet 作为 Android 17 新 MessageQueue 的主要源码说明，缺少 android-17.0.0_r1 CombinedDeliMessageQueue/MessageStack/MessageHeap 主线锚点，已写入 Task2B queue。"
task6_reviewed_date: "2026-07-14"
last_task6_at: 2026-07-14T22:18:30+08:00
task6_review_notes: 06-14 08 Task6 revisiting：pass-light-edit。L1 小修 3 处（3.3.9 形容词+冒号起手式 ×3）；outline 5/5 覆盖。07-01 22 Task6 revisiting：pass-light-edit。L1 小修 2 处（3.3.9 形容词+冒号 ×2：分工很清晰→按固定顺序执行、区分很关键→在trace里直接体现）；outline 5/5 覆盖；Task9 needs-rework P1:1（android-17 源码锚点缺失），待 Task2B 修复。07-02 01 Task6 revisiting：pass-light-edit。L1 小修 4 处（禁用词"落地"×4 → 实现/发布）；Task2B 已补充 android-17.0.0_r1 源码锚点（MessageStack/MessageHeap/CombinedDeliMessageQueue）；outline 5/5 覆盖、2/2 扩展；待 Task9 确认 Task2B 修复后可晋升。 07-14 18 Task6 revisiting：pass-light-edit。L1 无新增问题（禁用词扫描全清）；outline 5/5 覆盖、2/2 扩展；Task9 2026-07-14 needs-rework（P1:3），待 Task9 修复后重新复审。 07-14 22 Task6 revisiting：pass-light-edit。L1 小修 1 处（AI 清嗓词"需要明确的是"→直接陈述）；outline 5/5 覆盖、2/2 扩展；Task2B 已修复 Task9 P1 问题（fixed-lite），待 Task9 复审确认。
last_task9_audit: "2026-07-08"
last_task9_audit_log: "logs/deep-review/2026-07-08-22-audit.md"
task9_audit_notes: "2026-06-14 Task9 idle audit: auto-fixed。P0 1：将不可定位的 `ConcurrentMessageQueue.java` 文件名修正为 AOSP android-16.0.0_r1 实际路径 `ConcurrentMessageQueue/MessageQueue.java`。 | 2026-07-08 Task9 idle audit: pass-tech-review。P0 0 / P1 0 / P2 0；复核 android-17.0.0_r1 CombinedDeliMessageQueue/MessageStack/MessageHeap/Message 与 android-16.0.0_r1 rollout 边界；未发现 Android 18/API38+ 或主线源码漂移。"
p0: 0
p1: 0
p2: 0
finalized_by: "openclaw-task9-auto-promote"
finalized_date: "2026-07-02"
updated_by: "openclaw-task9"
updated_date: "2026-07-02"
last_deepseek_cn_review_at: 2026-07-14
last_task6_audit: "2026-06-20"
last_task9_issues: "P0:0 P1:0 P2:0; post-Task6 confirmation pass"
last_task2b_verifier_at: "2026-07-14T23:27:08+08:00"
task2b_verifier_notes: "2026-07-14 23:25 Task2B Verifier: auto-promote to finalized. task6_result=pass-light-edit, task9_result=pass-tech-review, queue clear, body 208 lines. pipeline_stage was stuck at task9_pending."
---

# 1.13 MessageQueue 机制与 DeliQueue 无锁优化

Android 17 没有改变 `Handler`、`Looper` 和同步屏障对应用呈现的基本语义，改的是 `MessageQueue` 内部的并发结构。对运行在 Android 17、且 `targetSdkVersion >= 37` 的应用，平台默认启用 DeliQueue：生产者不再与 Looper 围绕同一个 Java monitor 互斥，而是先把消息压入无锁栈，再由 Looper 整理到自己独占的最小堆。

这项改造解决的是队列操作的锁竞争，不会让 `layout`、`draw`、数据库查询或 Binder 调用凭空变快。分析卡顿时，先把一轮消息处理拆成三段：

1. **入队**：生产者通过 `Handler` 把 `Message` 放进队列。
2. **出队**：Looper 等待并选择下一条到期消息。
3. **分发**：`Handler.dispatchMessage()` 执行回调或业务代码。

DeliQueue 直接优化前两段。第三段如果耗时，仍然要回到业务调用栈继续查。

## 1. MessageQueue 在事件循环中的位置

一个线程调用 `Looper.prepare()` 后会得到一个 `Looper` 和与之绑定的 `MessageQueue`。随后 `Looper.loop()` 持续取消息、分发消息，直到队列退出。Android 17 的 `Looper.loopOnce()` 仍然把“出队”和“执行”分成两个明确步骤：

```java
// frameworks/base/core/java/android/os/Looper.java
// AOSP android-17.0.0_r1，省略观测与日志代码
private static boolean loopOnce(final Looper me,
        final long ident, final int thresholdOverride) {
    Message msg = me.mQueue.next(); // 可能阻塞
    if (msg == null) {
        return false;
    }

    msg.target.dispatchMessage(msg);
    // ...
    msg.recycleUnchecked();
    return true;
}
```

`next()` 返回前，关注点是消息排序、屏障、唤醒和队列并发；`dispatchMessage()` 开始后，才进入 `Handler.handleMessage()` 或 `Runnable.run()`。因此：

- 主线程在 `MessageQueue.next()` 附近出现 monitor contention，才可能是旧队列锁竞争。
- `dispatchMessage()` 下方的 `layout`、I/O 或 Binder 调用很长，是消息执行慢，不是 MessageQueue 持锁太久。
- 一条消息执行太久会推迟下一次 `next()`，但这是时间上的连锁影响，不能倒推出队列内部的锁持有时间变长。

## 2. 旧实现的问题：一把锁保护一条有序链表

传统 MessageQueue 用一条按执行时间 `when` 排序的单链表保存消息。`enqueueMessage()`、`next()`、移除消息和同步屏障操作都要进入同一个 `synchronized (this)` 临界区。

这种设计容易理解，也适合消息量较小、生产者不多的场景，但有两个结构性成本：

- **插入最坏为 O(N)**：新消息需要沿链表找到按 `when` 排序的位置。
- **生产者与消费者互斥**：后台线程入队时，可能挡住正在取消息的主线程；主线程检查队列时，也可能挡住生产者。

一次普通的短暂加锁通常问题不大，锁竞争与调度叠加后却可能形成优先级反转。例如：

1. 后台低优先级线程拿到 MessageQueue 的 monitor。
2. 中优先级线程抢占 CPU，使后台线程暂时无法继续运行和释放锁。
3. 高优先级 UI 线程回到 `next()`，却必须等那个后台线程。

UI 线程表面上被低优先级线程阻塞，实际等待时间还被中优先级任务放大。Perfetto 中常见的证据是主线程出现 `monitor contention with ...`，同时能定位持锁线程和加锁代码位置。

### 哪些业务更容易暴露旧结构的上限

- 多个后台线程高频向主线程 `post()`。
- 队列已经积压大量延时消息，生产者需要在长链表中寻找插入位置。
- 大范围调用 `removeCallbacksAndMessages()` 或各种 `removeMessages()` 重载。
- 同步屏障存在时，Looper 需要越过同步消息继续寻找可执行的异步消息。

“主线程很忙”本身不等于“MessageQueue 锁竞争”。只有 trace 里出现对应的锁等待，或 A/B 测试能稳定复现差异，才能把问题归到队列同步结构。

## 3. `next()` 不只是取链表头

无论新旧实现，`next()` 都要同时处理等待、消息时序、同步屏障和空闲回调。

### 3.1 native poll：没有到期消息时让线程休眠

MessageQueue 的 Java 层通过 JNI 调用 `nativePollOnce()`。native `MessageQueue` 再交给 `libutils::Looper` 等待文件描述符事件或超时；Linux 实现最终使用 epoll。新消息可能改变下一次唤醒时间，入队线程便通过 `nativeWake()` 唤醒 Looper。

Android 17 仍保留这条链路：

```text
MessageQueue.next()
  └─ nativePollOnce()
      └─ android_os_MessageQueue.cpp
          └─ libutils::Looper::pollOnce()/pollInner()
              └─ epoll_wait()
```

DeliQueue 不是忙等队列。没有可执行消息时，Looper 仍然阻塞在 native poll；变化主要发生在 Java 层共享队列的组织和唤醒协调方式上。

### 3.2 同步屏障：暂缓同步消息，让异步消息越过

同步屏障也是一条 `Message`，区别是 `target == null`。屏障生效时：

- 同步消息即使已经到期，也暂时不能分发。
- 到期的异步消息可以越过屏障。
- 移除屏障后，同步消息恢复正常选择。

`Choreographer` 的调度路径会使用异步 `Handler` 或异步消息，从而在渲染调度需要时越过屏障。这里的“异步”不是启动新线程；消息仍由原 Looper 线程执行，只是它在屏障选择规则中享有通行资格。

### 3.3 IdleHandler：队列准备休眠时执行

`MessageQueue.IdleHandler` 从 API 1 就存在。队列没有立即可执行的消息、准备等待下一条消息时，Looper 可以调用已注册的 IdleHandler。回调返回 `false` 会被移除，返回 `true` 则保留。

IdleHandler 与同步屏障解决的是两类问题：

- 同步屏障决定“当前哪些消息可以越过”。
- IdleHandler 决定“没有立即可执行消息时，是否做一点空闲工作”。

IdleHandler 运行在 Looper 所在线程，耗时操作照样会阻塞后续消息，不能把它当后台执行器。

## 4. Android 17 如何决定使用 DeliQueue

Android 17 的入口不是“只要系统版本是 17 就一定启用”。普通应用默认切换需要同时满足运行系统和 target SDK 边界。

在 `android-17.0.0_r1` 中，兼容性变更定义为：

```java
// CombinedDeliMessageQueue/MessageQueue.java
@ChangeId
@EnabledAfter(targetSdkVersion = Build.VERSION_CODES.BAKLAVA)
public static final long USE_NEW_MESSAGEQUEUE = 421623328L;
```

`BAKLAVA` 对应 Android 16 / API 36，`@EnabledAfter` 因而把默认边界放在 API 37。进程启动时，选择结果沿着下面的路径传递：

```text
PlatformCompat.getUseDeliQueue(appInfo)
  └─ ProcessList 启动应用进程
      └─ ZygoteProcess 添加 --use-deliqueue=<boolean>
          └─ ActivityThread.main() 解析参数
              └─ MessageQueue.setUseDeliQueue(...)
                  └─ Looper.prepareMainLooper() 创建队列
```

`ActivityThread.main()` 特意在 `Looper.prepareMainLooper()` 之前设置该值。`MessageQueue` 内部把选择保存为进程级静态状态；同一进程里的 MessageQueue 走同一种实现。

当前 `CombinedDeliMessageQueue/MessageQueue.java` 同时保留 Deli 与 legacy 两条路径：

```java
Message next() {
    if (sUseDeliQueue) {
        return nextDeliQueue();
    } else {
        return nextLegacy();
    }
}
```

“Android 17 源码只有 DeliQueue”与“每个 Android 17 应用都使用 DeliQueue”都不准确。平台用同一个组合类承载两种实现，再按进程启动时确定的兼容性结果选择路径。系统进程、测试环境和 feature flag 还有平台内部的启用入口，普通应用不应把这些内部条件当稳定 API。

## 5. DeliQueue 的数据结构

DeliQueue 把“并发提交”和“按时间排序”拆开：

```text
生产者线程
  └─ CAS push
      └─ MessageStack（共享 Treiber 栈）

Looper 线程
  ├─ heapSweep()：把新消息纳入堆
  ├─ mSyncHeap：同步消息与 barrier
  └─ mAsyncHeap：异步消息
```

这不是一棵所有线程共同修改的并发优先队列。共享部分尽量缩小为无锁栈和少量原子状态，两个 `MessageHeap` 的物理增删及排序由 Looper 线程独占。

### 5.1 入队：Treiber stack 与 CAS

`MessageStack` 的源码注释将其定义为由 “Treiber stack of Message objects”。生产者用释放语义的 CAS 更新栈顶：

```java
// frameworks/base/core/java/android/os/MessageStack.java
// AOSP android-17.0.0_r1，省略退出哨兵判断
do {
    current = (Message) sTop.getAcquire(this);
    m.next = current;
} while (!sTop.weakCompareAndSetRelease(this, current, m));
```

CAS 失败说明栈顶已被其他线程改变，当前线程重新读取并重试。它避免了旧实现中“先获得全局 monitor 才能入队”的互斥等待，但不代表每次入队只执行一条指令：高竞争下仍可能发生 CAS 重试，还要处理消息计数、插入序号和 native wake 协调。

调用线程的提交路径是 O(1)；随后 Looper 把消息放入最小堆时还会付出 O(log N) 的排序成本。成本没有消失，而是从“生产者在带锁链表里线性查找”改成“生产者快速提交，单消费者集中排序”。

### 5.2 出队：Looper 独占两个最小堆

`MessageStack.heapSweep()` 从当前栈顶遍历尚未处理的消息，创建反向链接，并按消息类型放入：

- `mSyncHeap`：同步消息和同步屏障。
- `mAsyncHeap`：异步消息。

`MessageHeap` 是数组实现的最小堆，主要按 `when` 排序；相同时间再用 `insertSeq` 保持确定的提交顺序。堆只由 Looper 线程做物理调整，所以不需要在每次向上或向下调整时加一把 Java 锁。

下一条消息的选择仍遵守旧语义：

1. 没有生效的 barrier 时，从已到期候选中选择应最先执行的消息。
2. barrier 生效时，同步消息被挡住，只能选择到期的异步消息。
3. 没有消息到期时，计算等待时间并回到 `nativePollOnce()`。

DeliQueue 没有引入业务优先级、机器学习调度或新的线程优先级策略。应用能观察到的主要排序依据仍是 `when`、同时间的插入顺序、同步屏障和异步标记。

### 5.3 移除：先做逻辑删除，再由 Looper 清结构

`removeMessages()` 这类 API 按 `Handler`、`what`、`obj` 或 `Runnable` 匹配消息。因为 API 要删除所有匹配项，查找仍可能遍历已有消息，整体不能宣称为 O(1)。

找到目标后，DeliQueue 不让任意线程直接重排堆，而是分三步：

1. 对 `Message.flags` 做 CAS，设置 `FLAG_REMOVED`，完成逻辑删除。
2. 清理会造成对象滞留的引用字段，并把 tombstone 放进另一条无锁 freelist。
3. Looper 在 `drainFreelist()` 中把节点从栈和相应的堆里物理移除。

非 Looper 线程负责声明消息已经无效，Looper 负责修复自己独占的数据结构。读取线程即使短暂看到 tombstone，也会按 removed 标记忽略它。

### 5.4 DeliQueue 为什么不复用 Message 池

Treiber 栈需要处理 ABA 问题：线程第一次看到栈顶是对象 A，暂停期间 A 被移除、复用，又重新成为栈顶；单看引用仍像“没有变化”。

Android 17 没有声称单指针 CAS 天然消除了 ABA。DeliQueue 的处理与对象生命周期绑定：进入并发队列的 `Message` 可能长期仍被某个移除遍历引用，所以不能马上回收到全局池再作为另一条消息复用。

源码中的行为很直接：

```java
public static Message obtain() {
    if (!MessageQueue.getUseConcurrent()) {
        synchronized (sPoolSync) {
            // legacy 路径才尝试从全局池取 Message
        }
    }
    return new Message();
}
```

DeliQueue 下，`recycleUnchecked()` 会清除 `obj`、`callback`、`data` 等引用，但不把这个对象放回共享消息池，也不会把并发删除所需的标志和链路当作普通新消息状态重用。这个选择避免了经典的“节点对象被回收后以新身份重新出现”的 ABA 场景，代价是比旧路径产生更多 `Message` 分配。评估收益时应同时观察锁竞争、分配速率和 GC，不能只看队列操作时长。

### 5.5 睡眠、唤醒与退出也要无竞争地协同

消息容器之外还需要处理唤醒竞争。生产者入队时可能让一条更早的消息成为新队首，需要唤醒正在 native poll 的 Looper；Looper 准备休眠时，又可能与刚入队的线程交错。

DeliQueue 用原子 wait state 协调“预计睡到何时”和“期间发生过多少次需要重新判断的事件”，避免丢失唤醒。同步屏障也有独立的原子状态，用来判断新增异步消息是否需要唤醒消费者。

退出阶段的竞争更敏感：其他线程可能正在通过 `mPtr` 调用 native wake，而 Looper 正准备销毁原生对象。Android 17 用带退出位的引用计数保护 `mPtr` 生命周期。`quitSafely()` 仍只处理已经到期的消息并移除未来消息；安全销毁原生对象则要等正在使用它的线程退出临界阶段。

## 6. “lock-free MessageQueue”不代表整个类没有锁

官方把 DeliQueue 称为 lock-free MessageQueue，因为消息的核心并发提交、检查和移除不再依赖旧的单一全局 monitor，相关算法满足无锁进展性质：即使某个线程停住，系统中仍有线程能够继续推进。

但 `android-17.0.0_r1` 的组合实现仍能看到：

- `mIdleHandlersLock`：保护 IdleHandler 集合。
- `mFileDescriptorRecordsLock`：保护文件描述符监听记录。
- legacy 路径里的 `synchronized (this)`。
- native poll/wake 和退出阶段的协调。

准确的表述是：**DeliQueue 消除了旧 MessageQueue 核心消息路径上的单一全局 monitor，并使用无锁共享结构与 Looper 私有堆协作**。把它扩写成“MessageQueue 内任何操作都不加锁”会与源码冲突。

## 7. 同步屏障与 Choreographer：语义不变，容器变了

从渲染角度看，新旧实现的差别可以压缩为：

```text
旧实现
生产者 enqueue ─┐
Looper next     ├─ 同一个 monitor + 有序链表
移除/barrier    ┘

Android 17 DeliQueue
生产者 enqueue ── CAS 压入 MessageStack
Looper next    ── sweep + 私有 sync/async 最小堆
移除         ── CAS tombstone + Looper 延迟清理
```

barrier 的行为没有改变：同步消息等待，异步消息可以越过。变化在于生产者提交消息时不再为了修改同一条链表而与 Looper 互斥。

这会改善 `VSYNC-app` 到 `doFrame()` 之间因为队列锁竞争造成的抖动，但不能保证每一帧都更快：

- `doFrame()` 里 measure/layout/draw 太慢，DeliQueue 无法修复。
- 主线程被别的应用锁、Binder 或调度延迟挡住，仍要查各自根因。
- 队列积压来自业务过量投递时，新结构能降低管理成本，却不会替应用丢弃无意义工作。

## 8. 官方性能数字应该怎样解读

Android Developers Blog 给出了 DeliQueue 的内部验证结果：

| 指标 | 官方结果 | 适用边界 |
| --- | ---: | --- |
| 多线程向繁忙队列插入 | 最高 5,000× | 合成高竞争基准，不代表普通应用 |
| App 主线程锁竞争耗时 | 降低 15% | Google 内部测试用户的 Perfetto trace |
| App 掉帧 | 降低 4% | 同批内部测试设备与工作负载 |
| System UI / Launcher 交互掉帧 | 降低 7.7% | 同批内部测试设备与工作负载 |
| 启动到首帧 P95 | 缩短 9.1% | 同批内部测试设备与工作负载 |

`5,000×` 来自多线程向已经繁忙的队列插入消息的极端合成基准。官方没有在文章中公开完整线程数、消息规模、设备与参数，不能把它写成“应用普遍快 5,000 倍”。`15%` 和掉帧数据也描述 Google 的内部样本，不是 Android 17 对每台设备的性能承诺。

项目自己的结论至少要记录：

- 设备和 Android build。
- `targetSdkVersion` 与兼容开关状态。
- 生产者线程数、消息量和队列积压程度。
- Perfetto 配置、操作步骤、样本数与统计口径。
- 除队列外的 CPU、GC、Binder 和帧流水线变化。

## 9. Android 17 迁移风险

### 9.1 反射 `mMessages` 得不到真实队列

为了兼容已有二进制，Android 17 仍保留私有字段 `mMessages`。DeliQueue 路径不使用它，官方迁移文档明确说明该字段会一直是 `null`。任何通过反射遍历 `mMessages` 的测试、监控或调试工具都不再可靠。

不要改为反射 `MessageStack` 或 `MessageHeap`。这些同样是私有实现，后续版本可以继续变化。测试代码应迁移到公开或测试专用 API。

### 9.2 测试框架版本

官方给出的最低建议是：

- Espresso 3.7.0 或更高版本。
- Robolectric 4.17 或更高版本，并从 `@LooperMode(LEGACY)` 迁移到 `@LooperMode(PAUSED)`。
- instrumentation 测试使用 `TestLooperManager`，包括 Android 17 增加的 `peekWhen()`、`poll()` 等能力，不再依赖 MessageQueue 私有字段。

### 9.3 用兼容性开关做同版本 A/B

在可调试应用上，可以执行：

```bash
adb shell am compat enable USE_NEW_MESSAGEQUEUE com.example.app
adb shell am force-stop com.example.app

adb shell am compat disable USE_NEW_MESSAGEQUEUE com.example.app
adb shell am force-stop com.example.app
```

每次切换后重新启动应用。实现选择发生在进程初始化、主 Looper 创建之前；只切开关而保留旧进程，无法得到可信对照。

A/B 结果的解释也要克制：

- 关闭后 crash 消失：优先排查反射和测试工具假设。
- 开启后 monitor contention 消失：说明旧队列锁是原链路的一部分。
- 两边 `dispatchMessage()` 都很长：继续修业务代码，别把它算成 DeliQueue 问题。

兼容开关用于开发验证和故障隔离，不应成为应用长期依赖的产品配置。

## 10. 用 Perfetto 验证，避免凭体感归因

### 第一步：确认等待发生在哪里

旧实现的典型证据是主线程出现 `monitor contention with ...` 片段，阻塞方法指向 `MessageQueue`。官方文章给出的 PerfettoSQL 使用 `android_monitor_contention` 表，并以 `short_blocked_method LIKE "%MessageQueue%"` 筛选主线程等待。

主线程只处于休眠状态不能证明存在锁竞争。它可能正常睡在 `nativePollOnce()` 等下一条消息；只有结合竞争片段、持锁者和调用点，才能确认是 Java monitor。

### 第二步：分开统计队列等待和消息执行

- 队列侧：MessageQueue monitor contention 次数、总时长、P95/P99，以及持锁线程。
- 执行侧：Looper/Handler 跟踪片段下的具体回调、`doFrame()`、Binder、I/O 和锁。
- 帧侧：实际帧时间线、missed frame 原因、`VSYNC-app` 到 `doFrame()` 的延迟。

Android 17 新实现让旧 monitor contention 消失后，主线程仍可能处于可运行状态却拿不到 CPU，也可能在其他锁上阻塞。线程状态必须和调度、调用栈一起检查。

### 第三步：做控制变量明确的 A/B

同一台 Android 17 设备、同一个构建、同一个 APK 和同一套操作脚本，只切 `USE_NEW_MESSAGEQUEUE`。每轮强制停止并冷启动进程，收集多份 trace，再比较分位数。不能直接对比 Android 16 与 Android 17 两个完整系统，再把所有差异都归给 DeliQueue。

对 `system_server` 做平台开发时，Android 17 还提供 `mq` track event 分类，可在 Perfetto 配置中启用 MessageQueue tracing。普通应用分析仍应优先使用稳定的 Looper、调度、锁竞争和帧时间线证据，不要依赖隐藏实现字段。

## 11. 版本演进

| 版本 | MessageQueue 相关变化 |
| --- | --- |
| Android 1.0（API 1） | `MessageQueue`、`Looper` 与 `IdleHandler` 已存在 |
| Android 4.1（API 16） | `Choreographer` 使用同步屏障与异步消息组织渲染调度 |
| Android 15（API 35） | legacy 主线仍是单链表加单一 monitor |
| Android 16（API 36） | 公开源码出现 Combined / Concurrent / Legacy 多种实现，处于系统进程优先的受控 rollout 阶段 |
| Android 17（API 37） | DeliQueue 面向 `targetSdkVersion >= 37` 的应用默认启用；当前源码锚点为 `CombinedDeliMessageQueue`、`MessageStack`、`MessageHeap` 与扩展后的 `Message` |

Android 16 的并发实现适合解释演进，不能替代 Android 17 的当前源码。Android 17 的 `MessageStack` 本身就是 Treiber stack，不是“用 MessageStack 替换 Treiber stack”；变化是原型结构收敛为共享 Treiber stack、Looper 私有双堆、tombstone 删除和完整的休眠/退出协调。

## 12. 常见误判

### “lock-free 就是没有任何 `synchronized`”

不是。核心消息路径不再依赖旧的全局 monitor，但 IdleHandler、文件描述符记录和 legacy 路径仍有各自的锁。

### “CAS 一定比锁快”

不是。低竞争、短临界区里，锁可能足够快；高竞争 CAS 也会不断重试。DeliQueue 的收益来自针对 MessageQueue 的整体结构重排，而不是把每个 `synchronized` 机械替换成一个原子变量。

### “MessageStack 解决了所有 ABA 问题”

不准确。`MessageStack` 就是 Treiber stack。Android 17 通过禁止 DeliQueue 中的 `Message` 对象池复用、保留 tombstone 生命周期和限制物理结构修改者来规避其设计中的节点复用问题。

### “新队列给渲染消息增加了更高业务优先级”

没有。同步屏障与异步消息语义沿用既有模型；DeliQueue 改的是并发容器和协调算法，不是应用任务优先级系统。

### “主线程处于休眠状态就是队列锁竞争”

不成立。空闲 Looper 正常睡在 native poll。要看到 `android_monitor_contention`、持锁线程和 MessageQueue 调用点，才能确认旧 monitor 竞争。

## 结论

阅读 Android 17 MessageQueue，抓住两条边界就够了。

第一，DeliQueue 优化的是入队和出队：生产者通过 CAS 提交到 `MessageStack`，Looper 把消息整理进自己独占的同步/异步最小堆，移除操作先做 tombstone，再由 Looper 清理结构。同步屏障、异步消息、IdleHandler 和 native poll 的外部语义仍然存在。

第二，官方所说的无锁指核心消息并发路径摆脱旧的单一全局 monitor，不代表整个类没有锁，也不代表业务回调会自动变快。迁移时检查反射和测试框架；性能分析时把队列等待与 `dispatchMessage()` 之后的业务执行分开，用同版本兼容开关和 Perfetto 证据完成 A/B 测试。

## 参考资料

- [Android Developers：MessageQueue behavior change guidance](https://developer.android.com/about/versions/17/changes/messagequeue)
- [Android Developers：Android 17 target behavior changes](https://developer.android.com/about/versions/17/behavior-changes-17)
- [Android Developers：MessageQueue.IdleHandler](https://developer.android.com/reference/android/os/MessageQueue.IdleHandler)
- [Android Developers Blog：Under the hood: Android 17's lock-free MessageQueue](https://android-developers.googleblog.com/2026/02/under-hood-android-17s-lock-free.html)
- [AOSP：CombinedDeliMessageQueue README（android-17.0.0_r1）](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/os/CombinedDeliMessageQueue/README.md)
- [AOSP：CombinedDeliMessageQueue/MessageQueue.java（android-17.0.0_r1）](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/os/CombinedDeliMessageQueue/MessageQueue.java)
- [AOSP：MessageStack.java（android-17.0.0_r1）](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/os/MessageStack.java)
- [AOSP：MessageHeap.java（android-17.0.0_r1）](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/os/MessageHeap.java)
- [AOSP：Message.java（android-17.0.0_r1）](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/os/Message.java)
- [AOSP：Looper.java（android-17.0.0_r1）](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/os/Looper.java)
- [AOSP：ActivityThread.java（android-17.0.0_r1）](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/app/ActivityThread.java)
- [AOSP：ZygoteProcess.java（android-17.0.0_r1）](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/os/ZygoteProcess.java)
- [AOSP：ProcessList.java（android-17.0.0_r1）](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/am/ProcessList.java)
- [AOSP：PlatformCompat.java（android-17.0.0_r1）](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/compat/PlatformCompat.java)
- [AOSP：android_os_MessageQueue.cpp（android-17.0.0_r1）](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/jni/android_os_MessageQueue.cpp)
- [AOSP：libutils Looper.cpp（android-17.0.0_r1）](https://android.googlesource.com/platform/system/core/+/refs/tags/android-17.0.0_r1/libutils/Looper.cpp)
