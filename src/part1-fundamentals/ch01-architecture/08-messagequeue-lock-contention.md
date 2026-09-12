---
title: MessageQueue 与锁竞争：从 DeliQueue 到系统等待链
chapter: '1.8'
section: '1.8'
status: finalized
applicable_versions: Android 1.0 (API 1) - Android 17 (API 37)
last_verified: '2026-09-12'
last_source_verified_at: '2026-09-12'
last_verified_against: AOSP android-17.0.0_r1 (CombinedDeliMessageQueue/MessageQueue/MessageStack/MessageHeap/Message/Looper, ART monitor/lock_word, bionic pthread_mutex, libbinder, AMS/OomAdjuster) + Android 17 official MessageQueue/TestLooperManager docs + Perfetto stdlib + ACK android17-6.18-2026-06_r6
confidence: high
sources:
- type: aosp
  path: frameworks/base/core/java/android/os/CombinedDeliMessageQueue/README.md @ android-17.0.0_r1
- type: aosp
  path: frameworks/base/core/java/android/os/CombinedDeliMessageQueue/MessageQueue.java @ android-17.0.0_r1
- type: aosp
  path: frameworks/base/core/java/android/os/MessageStack.java @ android-17.0.0_r1
- type: aosp
  path: frameworks/base/core/java/android/os/MessageHeap.java @ android-17.0.0_r1
- type: aosp
  path: frameworks/base/core/java/android/os/Message.java @ android-17.0.0_r1
- type: aosp
  path: frameworks/base/core/java/android/os/Looper.java @ android-17.0.0_r1
- type: aosp
  path: frameworks/base/core/java/android/app/ActivityThread.java @ android-17.0.0_r1
- type: aosp
  path: frameworks/base/core/java/android/os/ZygoteProcess.java @ android-17.0.0_r1
- type: aosp
  path: frameworks/base/services/core/java/com/android/server/am/ProcessList.java @ android-17.0.0_r1
- type: aosp
  path: frameworks/base/services/core/java/com/android/server/compat/PlatformCompat.java @ android-17.0.0_r1
- type: aosp
  path: frameworks/base/core/jni/android_os_MessageQueue.cpp @ android-17.0.0_r1
- type: aosp
  path: system/core/libutils/Looper.cpp @ android-17.0.0_r1
- type: official
  path: https://developer.android.com/about/versions/17/changes/messagequeue
- type: official
  path: https://developer.android.com/about/versions/17/behavior-changes-17
- type: official
  path: https://developer.android.com/reference/android/os/MessageQueue.IdleHandler
- type: official
  path: https://developer.android.com/reference/android/os/TestLooperManager
- type: official
  path: https://android-developers.googleblog.com/2026/02/under-hood-android-17s-lock-free.html
- type: aosp
  path: art/runtime/monitor.cc @ android-17.0.0_r1
- type: aosp
  path: art/runtime/lock_word.h @ android-17.0.0_r1
- type: aosp
  path: bionic/libc/bionic/pthread_mutex.cpp @ android-17.0.0_r1
- type: aosp
  path: frameworks/native/libs/binder/ProcessState.cpp @ android-17.0.0_r1
- type: aosp
  path: frameworks/base/services/core/java/com/android/server/am/ActivityManagerService.java @ android-17.0.0_r1
- type: aosp
  path: frameworks/base/services/core/java/com/android/server/am/psc/OomAdjuster.java @ android-17.0.0_r1
- type: kernel
  path: kernel/common/drivers/android/binder.c @ android17-6.18-2026-06_r6
- type: kernel
  path: kernel/common/Documentation/locking/rt-mutex.rst @ android17-6.18-2026-06_r6
- type: kernel
  path: kernel/common/Documentation/locking/pi-futex.rst @ android17-6.18-2026-06_r6
- type: kernel
  path: kernel/common/kernel/futex/pi.c @ android17-6.18-2026-06_r6
- type: official
  path: https://perfetto.dev/docs/analysis/stdlib-docs#androidmonitor_contention
- type: official
  path: https://perfetto.dev/docs/analysis/stdlib-docs#androidbinder
- type: article
  path: https://juejin.cn/post/7682633827692658740
  role: 外部技术文章入口；性能数字按官方博客边界校正
- type: article
  path: 技术文章/source/juejin-android/2026-09-10-76826338-Android17 重写 Message.md
  role: 主线程投递入口和旧队列争锁场景提示
tags:
- android
- looper
- handler
- messagequeue
- deliqueue
- perfetto
- lock-contention
- monitor
- mutex
- futex
- priority-inversion
- binder
related_chapters:
- '1.1'
- '2.3'
- '2.4'
- '7.1'
- '1.9'
- '9.1'
task6_state: reviewed
task9_state: reviewed
task2b_state: body-applied
pipeline_stage: finalized
last_review_finalize_at: '2026-09-12T12:10:17+08:00'
last_review_finalize_run_id: '20260912-120507-4559ea76'
last_body_apply_at: '2026-09-10T09:15:21+08:00'
last_body_apply_run_id: '20260910-091521-ffbe6333'
last_consolidated_at: '2026-08-24'
consolidated_from:
- src/part1-fundamentals/ch01-architecture/01.26-messagqueue-deliqueue-optimization.md
- src/part1-fundamentals/ch01-architecture/13-messagequeue-deliqueue.md
- src/part1-fundamentals/ch01-architecture/14-lock-contention.md
---

# MessageQueue 与锁竞争：从 DeliQueue 到系统等待链

Android 17 没有改变 `Handler`、`Looper` 和同步屏障对应用呈现的基本语义，改变的是 `MessageQueue` 内部的并发结构。对于运行在 Android 17 且 `targetSdkVersion >= 37` 的应用，平台默认启用 DeliQueue：生产者不再与 Looper 争用同一个 Java 监视器锁（monitor），而是先把消息压入无锁栈，再由 Looper 整理到自己独占的最小堆。最小堆是一种能快速取出最早到期消息的树形数据结构。

这项改造解决的是队列操作的锁竞争，不会让界面布局（`layout`）、绘制（`draw`）、数据库查询或 Binder 调用自动变快。分析卡顿时，可以把一轮消息处理分成三段：

1. **入队**：生产者通过 `Handler` 把 `Message` 放进队列。
2. **出队**：Looper 等待并选择下一条到期消息。
3. **分发**：`Handler.dispatchMessage()` 执行回调或业务代码。

DeliQueue 直接优化前两段的队列管理。第三段如果耗时，仍然要沿业务调用栈继续排查。

本文先用 DeliQueue 解释 MessageQueue 如何减少生产者与 Looper 的结构性争锁，再把视角扩展到 Java Monitor、futex、Binder 与 system_server 锁。两部分共享同一个诊断问题：等待链中究竟哪个节点无法推进。分析时先区分消息尚未得到执行，还是执行线程已经运行但正在等待其他资源。

## Looper 队列、唤醒与 DeliQueue

### 1. MessageQueue 在事件循环中的位置

线程调用 `Looper.prepare()` 后，会得到一个 `Looper` 和与之绑定的 `MessageQueue`。随后，`Looper.loop()` 构成事件循环，持续取出并分发消息，直到队列退出。Android 17 的 `Looper.loopOnce()` 仍然把“出队”和“执行”分成两个明确步骤：

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

- 主线程在 `MessageQueue.next()` 附近出现监视器锁竞争（monitor contention），才可能是旧队列的锁竞争。
- `dispatchMessage()` 下方的 `layout`、I/O 或 Binder 调用耗时很长，说明消息执行缓慢，不能归因于 MessageQueue 长时间持锁。
- 一条消息执行太久会推迟下一次 `next()`，但这是时间上的连锁影响，不能倒推出队列内部的锁持有时间变长。

### 2. 旧实现的问题：一把锁保护一条有序链表

传统 MessageQueue 使用一条按执行时间 `when` 排序的单链表保存消息。`enqueueMessage()`、`next()`、移除消息和同步屏障操作都要进入同一个 `synchronized (this)` 临界区，也就是同一时刻只允许一个线程修改受保护状态。

这种设计容易理解，也适合消息量较小、生产者不多的场景，但有两个结构性成本：

- **插入最坏为 O(N)**：队列中有 N 条消息时，新消息最坏要检查全部节点，才能找到按 `when` 排序的位置。
- **生产者与消费者互斥**：后台线程入队时，可能挡住正在取消息的主线程；主线程检查队列时，也可能挡住生产者。

一次普通的短暂加锁通常问题不大，锁竞争与调度叠加后却可能形成优先级反转。例如：

1. 后台低优先级线程取得 MessageQueue 的监视器锁。
2. 中优先级线程抢占 CPU，使后台线程暂时无法继续运行和释放锁。
3. 高优先级 UI 线程回到 `next()`，却必须等那个后台线程。

UI 线程表面上被低优先级线程阻塞，实际等待时间还被中优先级任务放大，这就是优先级反转。Perfetto 中常见的证据是主线程出现 `monitor contention with ...`，并且能定位持锁线程和加锁代码位置。

#### 哪些业务更容易暴露旧结构的上限

一个容易漏看的入口是“切回主线程”本身。后台线程不需要直接改 UI；只要它调用 `Handler.post()`，或经 `runOnUiThread()`、RxJava 主线程调度、协程主线程调度等封装把回调送到主线程，它就是在给主 Looper 增加生产者压力。[来源: https://juejin.cn/post/7682633827692658740] 对旧实现来说，这类入口最终会汇聚到同一条 MessageQueue 入队路径；对 DeliQueue 来说，优化的也是这段投递与排序的结构，而不是回调自身的工作量。[已验证: frameworks/base/core/java/android/os/CombinedDeliMessageQueue/MessageQueue.java @ android-17.0.0_r1]

- 多个后台线程高频向主线程 `post()`。
- 队列已经积压大量延时消息，生产者需要在长链表中寻找插入位置。
- 大范围调用 `removeCallbacksAndMessages()` 或各种 `removeMessages()` 重载。
- 同步屏障存在时，Looper 需要越过同步消息继续寻找可执行的异步消息。

“主线程很忙”不等于“MessageQueue 锁竞争”。只有性能轨迹中出现对应的锁等待，或 A/B 测试能稳定复现差异，才能把问题归到队列同步结构。

### 3. `next()` 不只是取链表头

无论新旧实现，`next()` 都要同时处理等待、消息时序、同步屏障和空闲回调。

#### 3.1 原生轮询：没有到期消息时让线程休眠

MessageQueue 的 Java 层通过 JNI（Java 与原生代码的调用桥梁）调用 `nativePollOnce()`。原生层的 `MessageQueue` 再交给 `libutils::Looper`，等待文件描述符事件或超时；Linux 实现最终使用 epoll 统一等待多个事件源。新消息可能改变下一次唤醒时间，入队线程便通过 `nativeWake()` 唤醒 Looper。

Android 17 仍保留这条链路：

```text
MessageQueue.next()
  └─ nativePollOnce()
      └─ android_os_MessageQueue.cpp
          └─ libutils::Looper::pollOnce()/pollInner()
              └─ epoll_wait()
```

DeliQueue 不会让 Looper 循环占用 CPU 检查消息。没有可执行消息时，Looper 仍然阻塞在原生轮询中；变化主要发生在 Java 层共享队列的组织方式和唤醒协调上。

#### 3.2 同步屏障：暂缓同步消息，让异步消息越过

同步屏障也是一条 `Message`，区别是 `target == null`。屏障生效时：

- 同步消息即使已经到期，也暂时不能分发。
- 到期的异步消息可以越过屏障。
- 移除屏障后，同步消息恢复正常选择。

`Choreographer` 的调度路径会使用异步 `Handler` 或异步消息，从而在渲染调度需要时越过屏障。这里的“异步”不表示启动新线程；消息仍由原 Looper 线程执行，只是在同步屏障存在时可以优先通过。

#### 3.3 IdleHandler：队列准备休眠时执行

`MessageQueue.IdleHandler` 从 API 1 起就存在。当队列没有立即可执行的消息、准备等待下一条消息时，Looper 可以调用已注册的 IdleHandler。回调返回 `false` 时会被移除，返回 `true` 时继续保留。

IdleHandler 与同步屏障解决的是两类问题：

- 同步屏障决定“当前哪些消息可以越过”。
- IdleHandler 决定“没有立即可执行消息时，是否做一点空闲工作”。

IdleHandler 运行在 Looper 所在线程，耗时操作照样会阻塞后续消息，不能把它当后台执行器。

### 4. Android 17 如何决定使用 DeliQueue

系统版本达到 Android 17，并不表示所有应用都会启用 DeliQueue。普通应用的默认切换还受目标 SDK（target SDK，表示应用适配的平台行为版本）约束。

在 `android-17.0.0_r1` 中，兼容性变更定义为：

```java
// CombinedDeliMessageQueue/MessageQueue.java
@ChangeId
@EnabledAfter(targetSdkVersion = Build.VERSION_CODES.BAKLAVA)
public static final long USE_NEW_MESSAGEQUEUE = 421623328L;
```

`BAKLAVA` 对应 Android 16 / API 36，因此 `@EnabledAfter` 把默认启用边界放在 API 37。应用进程启动时，这个兼容性判断会沿下面的路径传递：

```text
PlatformCompat.getUseDeliQueue(appInfo)
  └─ ProcessList 启动应用进程
      └─ ZygoteProcess 添加 --use-deliqueue=<boolean>
          └─ ActivityThread.main() 解析参数
              └─ MessageQueue.setUseDeliQueue(...)
                  └─ Looper.prepareMainLooper() 创建队列
```

`ActivityThread.main()` 特意在 `Looper.prepareMainLooper()` 之前设置该值。`MessageQueue` 内部把选择保存为进程级静态状态；同一进程里的 MessageQueue 走同一种实现。

当前的 `CombinedDeliMessageQueue/MessageQueue.java` 同时保留 DeliQueue 和旧版（legacy）两条路径。下面的分支根据进程级状态选择实现：

```java
Message next() {
    if (sUseDeliQueue) {
        return nextDeliQueue();
    } else {
        return nextLegacy();
    }
}
```

所以，“Android 17 源码只有 DeliQueue”与“每个 Android 17 应用都使用 DeliQueue”都不准确。平台用同一个组合类承载两种实现，再按进程启动时确定的兼容性结果选择路径。系统进程、测试环境和功能开关（feature flag）还有平台内部的启用入口，普通应用不应把这些内部条件当作稳定 API。

### 5. DeliQueue 的数据结构

DeliQueue 把“并发提交”和“按时间排序”分开处理：

```text
生产者线程
  └─ CAS push
      └─ MessageStack（共享 Treiber 栈）

Looper 线程
  ├─ heapSweep()：把新消息纳入堆
  ├─ mSyncHeap：同步消息与 barrier
  └─ mAsyncHeap：异步消息
```

所有线程不会共同修改同一棵并发优先队列。线程间共享的部分只保留无锁栈和少量原子状态，两个 `MessageHeap` 的实际增删和排序则只由 Looper 线程执行。

#### 5.1 入队：Treiber 栈与 CAS

`MessageStack` 的源码注释将其定义为 “Treiber stack of Message objects”。Treiber 栈是一种后进先出的无锁栈，生产者通过比较并交换（Compare-And-Set，CAS）原子更新栈顶。入队路径把新节点发布到栈顶时使用 release CAS；后续的 `isQuitting()`、`heapSweep()` 和删除遍历再通过 acquire 读取当前栈顶或空闲链表，以保证节点内容在线程间可见：

```java
// frameworks/base/core/java/android/os/MessageStack.java
// AOSP android-17.0.0_r1，省略退出哨兵判断
do {
    current = mTopValue;
    m.next = current;
} while (!sTop.weakCompareAndSetRelease(this, current, m));
```

CAS 失败说明栈顶已被其他线程改变，当前线程会重新读取并重试。它避免了旧实现中“先取得全局监视器锁才能入队”的互斥等待，但不代表每次入队只执行一条指令：高竞争下仍可能多次重试，还要处理消息计数、插入序号和原生唤醒协调。

调用线程的提交路径是 O(1)，不随队列长度线性增长；随后 Looper 把消息放入最小堆时，仍要付出 O(log N) 的排序成本。排序成本没有消失，只是从“生产者在带锁链表中线性查找”改为“生产者快速提交，由单个消费者集中排序”。

#### 5.2 出队：Looper 独占两个最小堆

`MessageStack.heapSweep()` 从当前栈顶遍历尚未处理的消息，建立供清理使用的反向链接，并按消息类型放入：

- `mSyncHeap`：同步消息和同步屏障。
- `mAsyncHeap`：异步消息。

`MessageHeap` 是用数组实现的最小堆，主要按 `when` 排序；普通消息执行时间相同时，再用插入序号 `insertSeq` 保持 FIFO。`sendMessageAtFrontOfQueue()` 是例外，源码用递减的负序号让队首消息按 LIFO 顺序排列。只有 Looper 线程会实际调整堆结构，因此每次向上或向下调整时不需要再取得 Java 锁。

下一条消息的选择仍遵守旧语义：

1. 没有生效的同步屏障时，从已到期候选中选择应最先执行的消息。
2. 同步屏障生效时，同步消息被暂缓，只能选择到期的异步消息。
3. 没有消息到期时，计算等待时间并回到 `nativePollOnce()`。

DeliQueue 没有引入业务优先级、机器学习调度或新的线程优先级策略。应用能观察到的主要排序依据仍是 `when`、同时间的插入顺序、同步屏障和异步标记。

#### 5.3 移除：先做逻辑删除，再由 Looper 清结构

`removeMessages()` 这类 API 按 `Handler`、`what`、`obj` 或 `Runnable` 匹配消息。因为 API 要删除所有匹配项，查找仍可能遍历已有消息，整体不能宣称为 O(1)。

找到目标后，DeliQueue 不让任意线程直接重排堆，而是分三步：

1. 对 `Message.flags` 做 CAS，设置 `FLAG_REMOVED`，完成逻辑删除。
2. 清理会造成对象滞留的引用字段，并把墓碑节点（tombstone，表示消息已删除但节点尚未物理移除）放进另一条无锁空闲列表（freelist）。
3. Looper 在 `drainFreelist()` 中把节点从栈和相应的堆里物理移除。

非 Looper 线程只负责把消息标记为无效，Looper 再清理自己独占的数据结构。读取线程即使短暂看到墓碑节点，也会根据已删除标记忽略它。

#### 5.4 DeliQueue 为什么不复用 Message 池

Treiber 栈需要处理 ABA 问题：线程第一次看到栈顶是对象 A，暂停期间 A 被移除、复用，又重新成为栈顶；如果只比较对象引用，栈顶看起来仍是 A，线程就可能误判为“没有变化”。

单指针 CAS 本身无法消除 ABA。DeliQueue 把处理方式与对象生命周期绑定：进入并发队列的 `Message` 可能仍被某次删除遍历引用，因此不能立即回收到全局池，再作为另一条新消息复用。

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

在 DeliQueue 路径中，`recycleUnchecked()` 会清除 `obj`、`callback`、`data` 等引用，但不会把对象放回共享消息池，也不会把并发删除所需的标志位和链路当作普通新消息状态复用。这样可以避免“节点对象被回收后以新身份重新出现”的经典 ABA 场景，代价是比旧版路径产生更多 `Message` 分配。评估收益时应同时观察锁竞争、对象分配速率和垃圾回收（GC），不能只看队列操作时长。

#### 5.5 睡眠、唤醒与退出也要无竞争地协同

消息容器之外还要处理唤醒竞争。生产者入队时可能让一条更早的消息成为新队首，需要唤醒正在执行原生轮询的 Looper；Looper 准备休眠时，也可能恰好有另一个线程入队。

DeliQueue 使用原子等待状态（wait state）协调“预计睡到何时”和“期间发生过多少次需要重新判断的事件”，避免遗漏唤醒信号。同步屏障也有独立的原子状态，用来判断新增异步消息是否需要唤醒消费者。

退出阶段的竞争更敏感：其他线程可能正在通过 `mPtr` 调用原生唤醒，而 Looper 正准备销毁原生对象。Android 17 使用带退出标志的引用计数，确保仍有线程使用时不会销毁 `mPtr` 指向的对象。`quitSafely()` 仍然只处理已经到期的消息并移除未来消息；销毁原生对象则要等正在使用它的线程离开临界阶段。

### 6. “无锁 MessageQueue”不代表整个类没有锁

官方把 DeliQueue 称为无锁（lock-free）MessageQueue，因为消息的核心并发提交、检查和移除不再依赖旧的单一全局监视器锁。这里的“无锁”描述一种进展保证：即使某个参与线程暂停，其他线程仍能继续完成操作。

但 `android-17.0.0_r1` 的组合实现仍能看到：

- `mIdleHandlersLock`：保护 IdleHandler 集合。
- `mFileDescriptorRecordsLock`：保护文件描述符监听记录。
- 旧版路径里的 `synchronized (this)`。
- 原生轮询、唤醒和退出阶段的协调。

准确的表述是：DeliQueue 消除了旧 MessageQueue 核心消息路径上的单一全局监视器锁，并使用无锁共享结构与 Looper 私有堆协作。若把它理解成“MessageQueue 内任何操作都不加锁”，就会与源码冲突。

### 7. 同步屏障与 Choreographer：语义不变，容器变了

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

图中的 `enqueue`、`next`、`sweep` 分别表示入队、取下一条消息和把新消息整理进堆；`sync/async` 表示同步/异步，`barrier` 表示同步屏障，`tombstone` 表示逻辑删除标记。屏障行为没有改变：同步消息等待，异步消息可以越过。变化在于生产者提交消息时，不再为了修改同一条链表而与 Looper 互斥。

这会改善 `VSYNC-app` 到 `doFrame()` 之间因为队列锁竞争造成的抖动，但不能保证每一帧都更快：

- `doFrame()` 中的测量、布局或绘制（measure/layout/draw）太慢时，DeliQueue 无法修复。
- 主线程被别的应用锁、Binder 或调度延迟挡住，仍要查各自根因。
- 队列积压来自业务过量投递时，新结构能降低管理成本，却不会替应用丢弃无意义工作。

### 8. 官方性能数字应该怎样解读

外部技术文章常把 DeliQueue 的收益压缩成“多线程入队速度提升 5000 倍、主线程锁等待减少 15%”这类结论。[来源: https://juejin.cn/post/7682633827692658740] 这些数字可以引用，但必须回到官方博客的 `Impact` 边界：`5,000×` 是合成高竞争基准里“多线程向繁忙队列插入”的最高值，`15%` 是 Google 内部 beta 测试 Perfetto 轨迹中的应用主线程锁竞争耗时下降。[已验证: https://android-developers.googleblog.com/2026/02/under-hood-android-17s-lock-free.html]

Android Developers Blog 给出了 DeliQueue 的内部验证结果：

| 指标 | 官方结果 | 适用边界 |
| --- | ---: | --- |
| 多线程向繁忙队列插入 | 最高 5,000× | 合成高竞争基准，不代表普通应用 |
| App 主线程锁竞争耗时 | 降低 15% | Google 内部测试用户的 Perfetto 轨迹 |
| App 掉帧 | 降低 4% | 同批内部测试设备与工作负载 |
| System UI / Launcher 交互掉帧 | 降低 7.7% | 同批内部测试设备与工作负载 |
| 启动到首帧 P95 | 缩短 9.1% | 同批内部测试设备与工作负载 |

`5,000×` 来自多线程向已经繁忙的队列插入消息的极端合成基准。官方没有在文章中公开完整线程数、消息规模、设备与参数，不能把它写成“应用普遍快 5,000 倍”。`15%` 和掉帧数据也描述 Google 的内部样本，不是 Android 17 对每台设备的性能承诺。

项目自己的结论至少要记录：

- 设备和 Android 构建版本。
- `targetSdkVersion` 与兼容开关状态。
- 生产者线程数、消息量和队列积压程度。
- Perfetto 配置、操作步骤、样本数与统计口径。
- 除队列外的 CPU、GC、Binder 和帧流水线变化。

### 9. Android 17 迁移风险

#### 9.1 反射 `mMessages` 得不到真实队列

为了兼容已有二进制，Android 17 仍保留私有字段 `mMessages`。DeliQueue 路径不使用它，官方迁移文档明确说明该字段会一直是 `null`。任何通过反射遍历 `mMessages` 的测试、监控或调试工具都不再可靠。

不要改为反射 `MessageStack` 或 `MessageHeap`。这些同样是私有实现，后续版本可以继续变化。测试代码应迁移到公开或测试专用 API。

#### 9.2 测试框架版本

官方给出的最低建议是：

- Espresso 3.7.0 或更高版本。
- Robolectric 4.17 或更高版本，并从 `@LooperMode(LEGACY)` 迁移到 `@LooperMode(PAUSED)`。
- 设备端插桩测试（instrumentation test）使用 `TestLooperManager`，包括 Android 16（API 36）引入的 `peekWhen()`、`poll()` 等能力，不再依赖 MessageQueue 私有字段。

#### 9.3 用兼容性开关做同版本 A/B

在可调试应用上，可以执行：

```bash
adb shell am compat enable USE_NEW_MESSAGEQUEUE com.example.app
adb shell am force-stop com.example.app

adb shell am compat disable USE_NEW_MESSAGEQUEUE com.example.app
adb shell am force-stop com.example.app
```

每次切换后重新启动应用。实现选择发生在进程初始化、主 Looper 创建之前；只切开关而保留旧进程，无法得到可信对照。

A/B 结果的解释也要克制：

- 关闭后崩溃消失：优先排查反射和测试工具对内部结构的假设。
- 开启后监视器锁竞争消失：说明旧队列锁是原链路的一部分。
- 两边 `dispatchMessage()` 都很长：继续修业务代码，别把它算成 DeliQueue 问题。

兼容开关用于开发验证和故障隔离，不应成为应用长期依赖的产品配置。

### 10. 用 Perfetto 验证，避免凭体感归因

#### 第一步：确认等待发生在哪里

旧实现的典型证据是主线程出现 `monitor contention with ...` 轨迹区段，阻塞方法指向 `MessageQueue`。官方文章给出的 PerfettoSQL 使用 `android_monitor_contention` 表，并以 `short_blocked_method LIKE "%MessageQueue%"` 筛选主线程等待。

主线程仅处于休眠（Sleeping）状态不能证明存在锁竞争。它可能只是正常阻塞在 `nativePollOnce()`，等待下一条消息；只有结合竞争区段、持锁者和调用点，才能确认是 Java 监视器锁。

#### 第二步：分开统计队列等待和消息执行

- 队列侧：MessageQueue 监视器锁竞争次数、总时长、P95/P99，以及持锁线程。
- 执行侧：Looper/Handler 轨迹区段下的具体回调、`doFrame()`、Binder、I/O 和锁。
- 帧侧：实际帧时间线、丢帧原因，以及 `VSYNC-app` 到 `doFrame()` 的延迟。

Android 17 新实现消除旧队列的监视器锁竞争后，主线程仍可能处于可运行状态却拿不到 CPU，也可能在其他锁上阻塞。线程状态必须结合调度和调用栈一起检查。

#### 第三步：做控制变量明确的 A/B

应在同一台 Android 17 设备、同一构建版本、同一 APK 和同一套操作脚本上，只切换 `USE_NEW_MESSAGEQUEUE`。每轮强制停止并冷启动进程，收集多份性能轨迹，再比较分位数。不能直接对比 Android 16 与 Android 17 两个完整系统，再把所有差异都归给 DeliQueue。

对 `system_server` 做平台开发时，Android 17 还提供 `mq` 轨迹事件（track event）分类，可在 Perfetto 配置中启用 MessageQueue 跟踪。分析普通应用时，仍应优先使用稳定的 Looper、调度、锁竞争和帧时间线证据，不要依赖隐藏实现字段。

### 版本与实现边界

| 版本 | MessageQueue 相关变化 |
| --- | --- |
| Android 1.0（API 1） | `MessageQueue`、`Looper` 与 `IdleHandler` 已存在 |
| Android 4.1（API 16） | `Choreographer` 使用同步屏障与异步消息组织渲染调度 |
| Android 15（API 35） | 旧版主线仍是单链表加单一监视器锁 |
| Android 16（API 36） | 公开源码出现组合版、并发版和旧版多种实现，处于优先为系统进程逐步启用的阶段 |
| Android 17（API 37） | DeliQueue 面向 `targetSdkVersion >= 37` 的应用默认启用；当前源码锚点为 `CombinedDeliMessageQueue`、`MessageStack`、`MessageHeap` 与扩展后的 `Message` |

Android 16 的并发实现适合解释演进，不能替代 Android 17 的当前源码。Android 17 的 `MessageStack` 本身就是 Treiber 栈，不能描述成“用 MessageStack 替换 Treiber 栈”；真正的变化是并发原型最终采用共享 Treiber 栈、Looper 私有双堆、墓碑删除，以及完整的休眠和退出协调。

### 常见误区

#### “无锁就是没有任何 `synchronized`”

不是。核心消息路径不再依赖旧的全局监视器锁，但 IdleHandler、文件描述符记录和旧版路径仍有各自的锁。

#### “CAS 一定比锁快”

不是。竞争较少且临界区很短时，锁可能已经足够快；高竞争下 CAS 也会不断重试。DeliQueue 的收益来自重新设计 MessageQueue 的整体结构，不能简单归结为把每个 `synchronized` 替换成原子变量。

#### “MessageStack 解决了所有 ABA 问题”

不准确。`MessageStack` 就是 Treiber 栈。Android 17 通过禁止 DeliQueue 中的 `Message` 对象池复用、保留墓碑节点的生命周期，并限定只有 Looper 修改实际结构，来规避节点复用引发的 ABA 问题。

#### “新队列给渲染消息增加了更高业务优先级”

没有。同步屏障与异步消息语义沿用既有模型；DeliQueue 改的是并发容器和协调算法，不是应用任务优先级系统。

#### “主线程处于休眠状态就是队列锁竞争”

不成立。空闲 Looper 正常阻塞在原生轮询中。只有看到 `android_monitor_contention`、持锁线程和 MessageQueue 调用点，才能确认存在旧版监视器锁竞争。

### 结论

阅读 Android 17 MessageQueue，需要抓住两条边界。

第一，DeliQueue 优化的是入队和出队：生产者通过 CAS 把消息提交到 `MessageStack`，Looper 再把消息整理进自己独占的同步/异步最小堆；移除操作先做逻辑删除，再由 Looper 清理结构。同步屏障、异步消息、IdleHandler 和原生轮询的对外语义都没有改变。

第二，官方所说的无锁，指核心消息并发路径不再依赖旧的单一全局监视器锁；它不代表整个类没有锁，也不代表业务回调会自动变快。迁移时应检查反射和测试框架；性能分析时，要把队列等待与 `dispatchMessage()` 之后的业务执行分开，并通过同版本兼容开关和 Perfetto 证据完成 A/B 测试。

## 锁竞争的识别与治理

队列结构可以降低生产者竞争，但不能消除消息处理过程中的业务锁。锁持有者、等待者和调度状态需要在同一时间窗口内还原。

线程显示为等待（Waiting）或休眠（Sleeping），只能证明它当时没有在 CPU 上执行，不能直接证明发生了锁竞争。它可能在等待 Java 监视器锁、原生互斥锁（native mutex）、条件变量、Binder 回复、I/O 或定时器，也可能只是 Looper 正常阻塞在 `epoll_wait()`，等待新事件。

诊断锁问题时，先回答四个问题，不要从猜测“哪种锁更快”开始：

1. **谁在等**：主线程、RenderThread、Binder 工作线程，还是普通后台线程？
2. **等什么**：Java 监视器锁、原生同步原语、Binder 回复，还是正常事件？
3. **谁能让它继续**：实际持锁线程或服务端线程是谁？
4. **这个线程为什么没有及时推进**：正在运行、排队等待 CPU、阻塞在另一把锁，还是执行 I/O？

这四个答案拼起来，才是一条可修复的等待链。

### 1. 先把几类“等”分开

Android 性能轨迹中，下面五类等待最容易混淆。

| 类型 | 常见入口 | 主要实现 | 首要证据 |
| --- | --- | --- | --- |
| Java 监视器锁 | `synchronized`、`Object.wait()` | ART Monitor / LockWord | `android_monitor_contention`、等待者与持锁者的方法 |
| Java 并发包 | `ReentrantLock`、`Condition`、`LockSupport.park()` | 抽象队列同步器（AQS）、线程挂起/唤醒、原生等待 | Java 调用栈、线程状态、相关业务埋点 |
| 原生锁 | `pthread_mutex`、`std::mutex`、条件变量 | bionic + futex | 原生调用栈、`blocked_function`、锁埋点 |
| Binder IPC | 同步 AIDL、服务端线程池 | libbinder + Binder 驱动 | Binder 事务/回复、调用端/服务端线程状态 |
| Looper 等待 | `MessageQueue.next()` | Java 队列 + 原生 Looper + epoll | 是否有到期消息、`nativePollOnce()`、MessageQueue 锁竞争 |

它们都可能在内核线程状态里表现为睡眠，但优化方式完全不同。

- Java 监视器锁要找到持有同一对象锁的线程。
- `ReentrantLock` 不属于 ART Monitor，不能指望 `android_monitor_contention` 自动给出持锁者。
- 原生 `futex_wait` 只说明线程进入了 futex 的内核等待路径，无法据此确认它对应互斥锁或启用了优先级继承。
- 同步 Binder 调用的调用端等待服务端回复；服务端内部可能又阻塞在 Java 或原生锁上。
- 空闲 Looper 睡在原生轮询中属于正常行为，无需消除。

### 2. ART Monitor：`synchronized` 在 Android 17 中怎样工作

Java 字节码使用 `monitorenter` 和 `monitorexit` 表达 `synchronized`。ART 在对象头的 32 位 LockWord（锁状态字）中记录轻量锁状态，必要时再关联完整的 `Monitor` 对象。

`art/runtime/lock_word.h` 在 `android-17.0.0_r1` 中定义了这些状态：

```cpp
enum LockState {
  kUnlocked,
  kThinLocked,
  kFatLocked,
  kHashCode,
  kForwardingAddress,
};
```

这些枚举说明 LockWord 还要容纳对象身份哈希值和垃圾回收所用的转发地址。分析 `synchronized` 时，不能把对象头始终解释成持锁线程 ID 和重入计数。

#### 2.1 无竞争路径：轻量锁

对象未加锁时，ART 可以把当前线程用于 Monitor 的线程 ID 和重入计数编码进 LockWord。线程通过原子更新取得轻量锁（thin lock）；同一线程再次进入同一把锁时，只增加重入计数。

轻量锁的优势是，不必为每个使用过 `synchronized` 的对象都分配完整 Monitor。没有竞争时，这条路径很短，不会让线程休眠，也不会触发内核调度切换。

“无竞争的 `synchronized` 开销较小”，不表示任何 `synchronized` 都只执行一次比较并交换（CAS）。对象可能已经膨胀为重量级 Monitor，可能带有身份哈希值（identity hash code），也可能发生重入和其他运行时状态变化。性能结论要结合实际对象和竞争形态。

#### 2.2 竞争、`wait()` 与身份哈希：Monitor 膨胀

`art/runtime/monitor.cc` 的源码注释列出需要完整 Monitor 的三类典型情况：

- 出现真实竞争。
- 在对象上调用 `wait()`。
- 一个需要加锁的对象同时带有身份哈希值。

竞争线程遇到已被其他线程持有的轻量锁时，ART 会与持锁线程协调，并尝试把锁膨胀为重量级 Monitor。重量级 Monitor 会记录完整的持锁者、等待者、条件等待和诊断信息。

`Object.wait()` 的语义也不能简化成“睡一会”：

1. 调用线程必须已经持有该对象的监视器锁。
2. `wait()` 把线程放入等待集合，并释放监视器锁。
3. `notify()` / `notifyAll()`、中断或超时使它具备继续条件。
4. `wait()` 返回前还必须重新取得同一个监视器锁。

因此，被唤醒不等于马上执行。线程可能从“等通知”转成“等重新拿锁”。

#### 2.3 `kLongWaitMs` 是日志阈值，不是统一的 Perfetto 阈值

Android 17 源码定义：

```cpp
static constexpr uint64_t kDebugThresholdFudgeFactor =
        kIsDebugBuild ? 10 : 1;
static constexpr uint64_t kLongWaitMs =
        100 * kDebugThresholdFudgeFactor;
```

也就是发布（release）构建为 100ms，调试（debug）构建为 1000ms。这个常量服务于 ART 的长时间竞争告警；是否记录日志，还会受采样和持锁者方法能否解析等条件影响。

它不能用来推导以下结论：

- “小于 100ms 的锁竞争不会进 Perfetto。”
- “没有长等待日志就没有锁问题。”
- “100ms 是 Android 所有锁的统一严重阈值。”

一帧在 60Hz 下只有约 16.7ms，几毫秒的主线程锁等待已经可能造成掉帧，远不到 ART 长等待日志的量级。

### 3. Futex：用户态快路径与内核慢路径

futex（fast userspace mutex）是让用户态原子状态与内核等待队列协作的基础机制，本身并不是某一种具体的 C++ 锁。没有竞争时通常只操作用户态内存；需要让线程休眠或唤醒时，才进入内核。

普通互斥锁（mutex）的典型流程如下：

```text
尝试用户态原子加锁
  ├─ 成功：直接进入临界区
  └─ 失败：标记存在竞争，通过 futex 进入内核等待

解锁
  ├─ 没有 waiter：用户态完成
  └─ 存在 waiter：通过 futex 唤醒等待线程
```

`bionic/libc/bionic/pthread_mutex.cpp` 中未启用优先级继承（PI）的互斥锁，在发生竞争时调用 `__futex_wait_ex()`，释放有等待者的锁时调用 `__futex_wake_ex()`。没有竞争时，不需要每次都进入内核。

这也是为什么 `blocked_function` 里看到 `futex_*` 仍然不能直接下结论：

- 它可能来自 `pthread_mutex`；
- 可能来自条件变量；
- 可能来自 ART 或其他运行时内部同步；
- 可能是 Java 并发包最终触发的线程挂起（park）；
- 只能证明线程在某个 futex 等待点休眠，不能单凭函数名还原锁对象和持锁者。

要定位原生锁，通常还需要原生调用栈、业务锁埋点和同进程线程状态，或者在可复现环境中为该锁增加 Trace 区段。

### 4. 优先级反转与 PI-futex

优先级反转的经典链条是：

```text
低优先级线程 L：持有锁
中优先级线程 M：持续占用 CPU
高优先级线程 H：等待 L 的锁

结果：H 的进度被 M 间接拖慢
```

即使 L 的临界区只执行 1ms，如果 L 长时间得不到 CPU，H 实际经历的等待时间也可能远大于 1ms。

#### 4.1 优先级继承的作用

ACK `android17-6.18-2026-06_r6` 的实时互斥锁（rt-mutex）文档描述了优先级继承（Priority Inheritance，PI）：

- 高优先级等待者阻塞在 rt-mutex 上时，低优先级持锁者临时继承更高优先级；
- 持锁者释放锁后撤销这次提升；
- 持锁者又阻塞在另一把 rt-mutex 上时，优先级提升可以沿依赖链传播；
- 等待者按优先级组织，同优先级使用先进先出（FIFO）顺序。

PI 缩短的是“高优先级线程被低优先级持锁者挡住，而持锁者又得不到 CPU”的时间。它无法缩短持锁者在临界区内执行的 I/O、长计算或同步 Binder 调用。

#### 4.2 Android 17 bionic 怎样选择 PI 互斥锁

bionic 通过下面的属性显式启用优先级继承：

```c
pthread_mutexattr_setprotocol(&attr, PTHREAD_PRIO_INHERIT);
pthread_mutex_init(&mutex, &attr);
```

只有互斥锁属性显式选择 `PTHREAD_PRIO_INHERIT`，bionic 才会调用 `__futex_pi_lock_ex()` / `__futex_pi_unlock()`，由内核 PI-futex 和 rt-mutex 提升持锁者优先级。普通互斥锁仍走普通 futex 路径。

所以：

- “Android 内核支持 PI-futex”只说明具备这项能力；
- 判断“这把锁启用了 PI”，必须检查它的初始化属性；
- 某线程停在 `futex_wait`，不能证明该锁走的是 PI 路径。

PI 不能替代合理的锁设计。临界区过大、锁顺序混乱、持锁执行 I/O 等问题，仍应从设计上修复。

### 5. Binder 等待与 Java 锁等待是两条不同路径

同步 Binder 调用跨越调用端（client）、Binder 驱动和服务端（server）：

```text
Client thread
  └─ binder transaction
      └─ Binder driver 选择/唤醒 server thread
          └─ Server Binder thread 执行服务代码
              └─ binder reply
                  └─ Client 继续执行
```

调用端等待回复时，并没有持有一把所谓的“Binder Java 监视器锁”。驱动使用自己的锁和等待队列管理事务、线程与工作项；服务端业务代码则可能再次遇到 Java 监视器锁或原生互斥锁。

一次同步 Binder 延迟可以拆成：

```text
总墙上时间
= client 入驱动与排队
+ server thread 获得运行机会
+ server 业务执行
+ server 内部锁 / I/O / 嵌套 Binder 等待
+ reply 返回与 client 再次被调度
```

只看到调用端休眠在 Binder 相关内核函数上，无法判断哪一项耗时占主导。

#### 5.1 Binder 有自己的优先级传播

`drivers/android/binder.c` 在当前 ACK tag 中包含：

- `binder_select_thread_ilocked()`：为进程中的工作选择等待线程；
- `binder_wakeup_thread_ilocked()`：唤醒具体线程，或通知进程需要增加线程；
- `binder_transaction_priority()`：根据事务和 Binder 节点（binder node）的限制，设置服务端处理线程的优先级。

这是 Binder 自身的事务调度机制，不等同于 `PTHREAD_PRIO_INHERIT`，也不会自动提升“服务端线程正在等待的某个 Java 监视器锁持有者”。如果 Binder 工作线程进入服务代码后又阻塞在业务锁上，仍要沿 Java 或原生锁的持有关系继续排查。

#### 5.2 默认 15 不代表进程里固定只有 15 条 Binder 线程

Android 17 的 `ProcessState.cpp` 定义：

```cpp
#define DEFAULT_MAX_BINDER_THREADS 15
```

初始化 Binder 驱动时，libbinder 通过 `BINDER_SET_MAX_THREADS` 把这个默认最大值设为 15。与此同时，`startThreadPool()` 会调用 `spawnPooledThread(true)`，主动启动一条主线程池线程（main pooled thread）。

因此应该这样读：

- 15 是 libbinder 传给驱动的默认“可按需请求启动的线程”上限；
- 主动启动的主线程池线程要单独计入线程总数；
- 业务线程也可以进入 Binder 调用上下文；
- 服务可以在启动线程池前通过 API 配置不同上限。

所以，把 Binder 线程池概括成“固定 15 条”或“固定 16 条”都会误导性能分析。线程数只是容量的一部分；一个工作线程长时间持锁或执行缓慢 I/O，仍可能让其他事务排队。

### 6. `system_server`：Binder 慢经常只是表象

应用主线程调用 AMS、WMS 或 PMS 后长时间等待回复，常见根因位于服务端，而非 Binder 驱动本身：

- Binder 工作线程等待 `system_server` 的全局对象锁；
- 持锁线程在锁内执行长计算或磁盘 I/O；
- 持锁线程在锁内发起另一个同步 Binder 调用；
- 多把系统锁形成长等待链；
- Binder 工作线程接近饱和，新事务迟迟没有线程处理。

分析时，应从调用端事务跟到服务端回复，再检查服务端线程的状态；如果它在等锁，就继续找持锁线程，不能停留在“Binder 调用耗时”这个表面结论。

#### 6.1 Android 17 AMS 的 `mGlobalLock` 与 `mProcLock`

`ActivityManagerService.java` 当前源码明确给出：

```java
final ActivityManagerGlobalLock mGlobalLock = ActivityManagerService.this;

private static final boolean ENABLE_PROC_LOCK = true;

final ActivityManagerGlobalLock mProcLock = ENABLE_PROC_LOCK
        ? new ActivityManagerProcLock() : mGlobalLock;
```

源码注释规定了锁的获取顺序：先取得 `mGlobalLock`，再取得 `mProcLock`；不能在只持有 `mProcLock` 时反向获取 `mGlobalLock`，否则可能形成死锁。

`@CompositeRWLock({"mService", "mProcLock"})` 表达的是供静态分析和代码审查使用的组合锁契约，不会在运行时创建新的读写锁对象：相关状态的读取可由两把锁中的任意一把保护，写入通常要求同时持有两把锁。方法后缀也能提示调用者需要持有哪些锁：

- `LOSP`：通常表示持有列出的任意一把锁；
- `LSP`：通常表示同时持有服务全局锁和进程锁。

例如 Android 17 的 `OomAdjuster`：

```java
@GuardedBy("mServiceLock")
void updateOomAdjLocked(@OomAdjReason int oomAdjReason) {
    synchronized (mProcLock) {
        updateOomAdjLSP(oomAdjReason);
    }
}
```

这里调用者已经持有 `mServiceLock`，随后再进入 `mProcLock`，符合从全局锁到进程锁的顺序。`ProcessList.mLruProcesses` 也标注为由组合锁保护。

这些源码能证明哪些状态由哪些锁保护，以及锁的获取顺序，却不能单独证明某个固定的性能提升比例。锁持有时间必须来自具体设备的性能轨迹；没有可定位的一手基准时，不应写“从 25ms 降到 8ms”或“吞吐提升 3 倍”。

### 7. 把 DeliQueue 放回等待链中

前半篇已经完整解释 DeliQueue 的旧锁、新栈与双堆实现；这里不重复数据结构，只提炼诊断意义。若 Android 17 / target API 37 上的证据表明生产者入队争锁明显下降，但消息仍然迟到，就应继续检查 Looper 前序任务、执行线程调度、业务锁、Binder 与 I/O。反过来，在旧实现或兼容开关未启用时，MessageQueue 自身的 monitor contention 仍可能是等待链中的关键节点。

DeliQueue 因此是一个有边界的去锁案例，而不是“无锁一定更快”的证明。Google 公布的 15% 锁竞争时间下降只描述其内部样本；CAS 重试、缓存行争用、内存分配和延迟清理仍需在目标负载中测量。

### 8. Perfetto：先找证据，再解释原因

#### 8.1 Java 监视器锁

当前 Perfetto 标准库（stdlib）的模块名是 `android.monitor_contention`，查询表名是 `android_monitor_contention`。下面的 SQL 列出 `system_server` 中耗时最长的 30 次 Java 监视器锁竞争：

```sql
INCLUDE PERFETTO MODULE android.monitor_contention;

SELECT
  process_name,
  blocked_thread_name AS waiter,
  blocking_thread_name AS owner,
  short_blocked_method AS waiter_method,
  short_blocking_method AS owner_method,
  lock_name,
  dur / 1e6 AS wait_ms
FROM android_monitor_contention
WHERE process_name = 'system_server'
ORDER BY dur DESC
LIMIT 30;
```

查询结果能给出等待线程（waiter）、持锁线程（owner）、双方方法、源码位置、是否为主线程、锁名和等待时长。`android_monitor_contention_chain` 还能表达多段锁竞争之间的依赖关系；配套的线程状态表可以继续检查持锁者在锁内是正在运行（Running）、可运行但等待 CPU（Runnable），还是又阻塞在其他内核函数中。

注意两个边界：

- 表中没有记录，不等于设备上完全没有竞争；性能轨迹配置、运行时采样和符号解析都会影响数据完整性；
- 这张表针对 ART Java Monitor，不覆盖所有 `ReentrantLock` 和原生互斥锁。

#### 8.2 原生 futex 等待

没有专门的锁埋点时，可以先从 `thread_state.blocked_function` 查找耗时较长的 futex 等待。下面的 SQL 列出最长的 50 个候选区间：

```sql
SELECT
  p.name AS process_name,
  t.name AS thread_name,
  ts.ts,
  ts.dur / 1e6 AS blocked_ms,
  ts.state,
  ts.blocked_function
FROM thread_state ts
JOIN thread t ON t.utid = ts.utid
LEFT JOIN process p ON p.upid = t.upid
WHERE ts.blocked_function GLOB '*futex*'
ORDER BY ts.dur DESC
LIMIT 50;
```

这一步只负责找候选。随后还要结合原生调用栈或源码，确认它对应互斥锁、条件变量（condvar）还是其他等待，并寻找真正能使其继续的线程。不能只根据 `futex_wait` 这个函数名，就断定发生了 Java 锁竞争。

#### 8.3 Binder 调用端与服务端

Perfetto 的 `android.binder` 模块可以把事务与回复关联到调用端和服务端。下面的 SQL 按调用端总耗时列出最长的 30 笔同步 Binder 事务：

```sql
INCLUDE PERFETTO MODULE android.binder;

SELECT
  client_process,
  client_thread,
  server_process,
  server_thread,
  interface,
  method_name,
  is_sync,
  client_dur / 1e6 AS client_ms,
  server_dur / 1e6 AS server_ms
FROM android_binder_txns
WHERE is_sync
ORDER BY client_dur DESC
LIMIT 30;
```

找到慢事务后，可以再用 `android_sync_binder_thread_state_by_txn` 或 `android_sync_binder_blocked_functions_by_txn` 分解调用端与服务端的线程状态。若服务端处理区间叠加 Java 监视器锁竞争，就继续查询 `android_monitor_contention` 给出的持锁者。

“调用端时间长、服务端时间短”可能意味着事务排队、线程调度或回复返回延迟；“服务端时间长”也不等同于一直执行 CPU 计算，服务端可能大部分时间都在等待锁、I/O 或嵌套 Binder 调用。

### 9. 三个常见现场怎样推理

#### 现场一：主线程出现 `monitor contention with ...`

1. 在 `android_monitor_contention` 中找到等待者方法、持锁线程和持锁者方法；
2. 查看持锁者在等待区间内的 `thread_state`；
3. 如果持锁者处于 Runnable 状态却长时间没有运行，检查 CPU 压力与优先级反转；
4. 如果持锁者又等待另一把锁或 Binder，继续沿依赖链排查；
5. 回源码确认临界区，检查能否移出 I/O、IPC 或长计算。

#### 现场二：主线程睡在同步 Binder 调用

1. 用 `android_binder_txns` 找到服务端进程、线程和方法；
2. 比较调用端与服务端区间，确认时间主要花在哪一端；
3. 服务端工作线程若等待 Java Monitor，用竞争表找持锁者；
4. 服务端工作线程若停在原生 futex，结合原生调用栈找具体同步对象；
5. 多个事务都在排队时，检查工作线程是否饱和，以及某个长事务是否占用线程过久。

#### 现场三：线程停在 `futex_wait`

1. 先确认 Java 调用栈来自 ART Monitor、AQS/线程挂起，还是 JNI/原生代码；
2. 检查是否有对应的 `android_monitor_contention` 事件；
3. 没有 Java Monitor 证据时，按原生锁或条件等待调查；
4. 找到锁的初始化代码，确认是否为 PI 互斥锁，不能根据函数名猜测；
5. 如果这是正常的条件变量等待，就继续查“为什么条件迟迟没有满足”，无需优化 futex 本身。

### 10. 锁优化的工程顺序

#### 10.1 先缩短临界区

最常见的有效改动，是把不需要维持共享状态一致性的工作移出锁：

- 日志格式化和大对象构建；
- 磁盘、网络和数据库 I/O；
- 同步 Binder 调用；
- 可以先在锁内复制输入、锁外计算、再在锁内提交结果的长计算；
- 不需要共享状态保护的回调。

把代码移出锁前，要重新确认临界区保护的不变量，也就是共享状态始终必须满足的约束。盲目缩小范围可能产生“先检查、后操作”之间状态已被其他线程改变的竞态（check-then-act race），性能改善不能以破坏正确性为代价。

#### 10.2 再减少共享状态

- 用线程封闭（只允许一个线程访问状态）或消息传递代替共享可变对象；
- 把一把全局锁拆成按对象、按分片（shard）或按子系统的锁；
- 读多写少时考虑不可变快照、写时复制（copy-on-write）或读写分离；
- 高频计数器考虑分片，减少多个 CPU 写入同一缓存行。

拆锁会引入锁顺序和跨锁一致性问题。应先写清哪些字段共同构成一个必须原子维护的不变量，再决定能否拆分。

#### 10.3 明确锁顺序

跨多把锁时，项目应定义全局顺序，并在代码审查中阻止反向获取。Android 17 AMS 对 `mGlobalLock` → `mProcLock` 的注释就是这种契约。

超时只能限制单次等待时间，不能修复潜在死锁；`tryLock()` 获取失败后的状态恢复同样需要正确设计。

#### 10.4 最终才比较锁类型或无锁结构

选择 `synchronized`、`ReentrantLock`、读写锁或无锁结构，应由需求决定：

- 是否需要可中断的锁获取或超时；
- 是否需要多个条件队列（`Condition`）；
- 是否允许公平锁按等待顺序分配锁所带来的吞吐成本；
- 读写比例和临界区大小；
- 竞争线程数、优先级和 CPU 核心布局；
- 失败重试与内存回收成本是否可控。

微基准要覆盖真实的竞争形态。只测试单线程获取/释放锁（acquire/release），无法预测主线程与多个后台生产者同时竞争时，高百分位请求的尾延迟。

#### 10.5 增加 Binder 线程数不是首选修复手段

增加工作线程可能缓解排队，也可能让更多线程同时争用同一把全局锁，增加内存和调度压力。应先找最长事务、持锁 I/O、嵌套同步 IPC 和锁依赖链，再判断线程池容量是否不足。

### 版本与实现边界

| 版本 | 可确认的同步相关变化 | 阅读方式 |
| --- | --- | --- |
| Android 5.0（API 21） | 应用运行时切换到 ART，Java Monitor 分析以 ART `monitor.cc` / `lock_word.h` 为准 | 不沿用 Dalvik 时代实现细节解释当前系统 |
| Android 9（API 28） | bionic 已提供 `PTHREAD_PRIO_INHERIT` 互斥锁属性接口 | 只说明这项能力可用；具体锁是否启用仍要看初始化 |
| Android 17（API 37） | 当前 bionic 的 PI 互斥锁走 PI-futex；当前 ACK 为 `android17-6.18-2026-06_r6`；DeliQueue 对目标 SDK 37 及以上应用默认启用 | 平台、bionic 与内核源码按本知识库的统一锚点核对 |

Binder 默认线程配置在历史上容易被误传。在当前 Android 17 锚点下，`DEFAULT_MAX_BINDER_THREADS` 为 15，`startThreadPool()` 还会另行启动主线程池线程；这个数值并非进程的固定 Binder 线程总数。

### 常见误区

#### “Waiting / Sleeping 就是锁竞争”

不成立。Looper、条件变量、Binder、I/O 和定时器都会让线程睡眠。先找等待对象和唤醒条件。

#### “`synchronized` 一定比 `ReentrantLock` 慢”

不成立。它们的功能、运行时路径和竞争行为不同。没有实际工作负载和性能轨迹，单凭锁类型无法判断。

#### “看到 `futex_wait` 就找 Java Monitor 的持锁者”

不成立。应先看 `android_monitor_contention` 和调用栈。futex 是底层等待机制，不是 Java Monitor 的专属标志。

#### “内核支持 PI，所以 Android 关键锁都有优先级继承”

不成立。bionic 互斥锁必须使用 `PTHREAD_PRIO_INHERIT` 初始化；Binder 的事务优先级传播又是另一套机制。

#### “Binder 调用慢就是驱动慢”

只看到 Binder 调用耗时，通常证据还不够。服务端工作线程可能阻塞在业务锁、I/O、CPU 调度或嵌套 IPC 上。应先把调用端与服务端的时间线连起来。

#### “无锁一定更快”

不成立。CAS 重试、多个 CPU 核反复争用同一缓存行、垃圾回收（GC）和算法复杂度都可能成为新成本。DeliQueue 的价值来自针对具体队列结构的重构，不能只归结为“无锁”两个字。

### 结论

锁竞争分析要还原完整的等待链。Java Monitor 使用 `android_monitor_contention` 查找等待者与持锁者；原生互斥锁要从 futex 候选回到原生调用栈和初始化代码；Binder 要用事务与回复连起调用端和服务端；MessageQueue 还要区分正常的原生轮询与旧版监视器锁竞争。

找到持锁者后还要继续判断：它正在 CPU 上运行，还是处于 Runnable 状态却没有被调度？它是否阻塞在另一把锁、I/O 或 Binder 上？找到整条等待链中无法推进的节点后，缩短临界区、拆锁、调整线程模型、启用 PI 或采用无锁结构才有明确目标。

## 参考资料

- [Android Developers：MessageQueue behavior change guidance](https://developer.android.com/about/versions/17/changes/messagequeue)
- [Android Developers：Android 17 target behavior changes](https://developer.android.com/about/versions/17/behavior-changes-17)
- [Android Developers：MessageQueue.IdleHandler](https://developer.android.com/reference/android/os/MessageQueue.IdleHandler)
- [Android Developers：TestLooperManager](https://developer.android.com/reference/android/os/TestLooperManager)
- [Android Developers Blog：Under the hood: Android 17's lock-free MessageQueue](https://android-developers.googleblog.com/2026/02/under-hood-android-17s-lock-free.html)
- [掘金：Android17 重写 MessageQueue，解决 Handler 隐性卡顿](https://juejin.cn/post/7682633827692658740)
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

- [AOSP：ART monitor.cc（android-17.0.0_r1）](https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/runtime/monitor.cc)
- [AOSP：ART lock_word.h（android-17.0.0_r1）](https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/runtime/lock_word.h)
- [AOSP：bionic pthread_mutex.cpp（android-17.0.0_r1）](https://android.googlesource.com/platform/bionic/+/refs/tags/android-17.0.0_r1/libc/bionic/pthread_mutex.cpp)
- [AOSP：libbinder ProcessState.cpp（android-17.0.0_r1）](https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/libs/binder/ProcessState.cpp)
- [AOSP：ActivityManagerService.java（android-17.0.0_r1）](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/am/ActivityManagerService.java)
- [AOSP：OomAdjuster.java（android-17.0.0_r1）](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/am/psc/OomAdjuster.java)
- [ACK：Binder driver（android17-6.18-2026-06_r6）](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/drivers/android/binder.c)
- [ACK：rt-mutex 文档（android17-6.18-2026-06_r6）](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/Documentation/locking/rt-mutex.rst)
- [ACK：PI-futex 文档（android17-6.18-2026-06_r6）](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/Documentation/locking/pi-futex.rst)
- [ACK：futex PI 实现（android17-6.18-2026-06_r6）](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/kernel/futex/pi.c)
- [Perfetto：`android.monitor_contention` stdlib](https://perfetto.dev/docs/analysis/stdlib-docs#androidmonitor_contention)
- [Perfetto：`android.binder` stdlib](https://perfetto.dev/docs/analysis/stdlib-docs#androidbinder)
- [Android Developers Blog：Android 17 lock-free MessageQueue](https://android-developers.googleblog.com/2026/02/under-hood-android-17s-lock-free.html)
