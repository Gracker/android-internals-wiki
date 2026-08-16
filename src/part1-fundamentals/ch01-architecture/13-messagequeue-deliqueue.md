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
task6_state: reviewed
task9_state: reviewed
task2b_state: fixed
pipeline_stage: ready-to-publish
last_consolidated_at: "2026-08-11"
consolidated_from:
  - "src/part1-fundamentals/ch01-architecture/01.26-messagqueue-deliqueue-optimization.md"
---

# 1.13 MessageQueue 机制与 DeliQueue 无锁优化

Android 17 没有改变 `Handler`、`Looper` 和同步屏障对应用呈现的基本语义，改变的是 `MessageQueue` 内部的并发结构。对于运行在 Android 17 且 `targetSdkVersion >= 37` 的应用，平台默认启用 DeliQueue：生产者不再与 Looper 争用同一个 Java 监视器锁（monitor），而是先把消息压入无锁栈，再由 Looper 整理到自己独占的最小堆。最小堆是一种能快速取出最早到期消息的树形数据结构。

这项改造解决的是队列操作的锁竞争，不会让界面布局（`layout`）、绘制（`draw`）、数据库查询或 Binder 调用自动变快。分析卡顿时，可以把一轮消息处理分成三段：

1. **入队**：生产者通过 `Handler` 把 `Message` 放进队列。
2. **出队**：Looper 等待并选择下一条到期消息。
3. **分发**：`Handler.dispatchMessage()` 执行回调或业务代码。

DeliQueue 直接优化前两段的队列管理。第三段如果耗时，仍然要沿业务调用栈继续排查。

## 1. MessageQueue 在事件循环中的位置

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

## 2. 旧实现的问题：一把锁保护一条有序链表

传统 MessageQueue 使用一条按执行时间 `when` 排序的单链表保存消息。`enqueueMessage()`、`next()`、移除消息和同步屏障操作都要进入同一个 `synchronized (this)` 临界区，也就是同一时刻只允许一个线程修改受保护状态。

这种设计容易理解，也适合消息量较小、生产者不多的场景，但有两个结构性成本：

- **插入最坏为 O(N)**：队列中有 N 条消息时，新消息最坏要检查全部节点，才能找到按 `when` 排序的位置。
- **生产者与消费者互斥**：后台线程入队时，可能挡住正在取消息的主线程；主线程检查队列时，也可能挡住生产者。

一次普通的短暂加锁通常问题不大，锁竞争与调度叠加后却可能形成优先级反转。例如：

1. 后台低优先级线程取得 MessageQueue 的监视器锁。
2. 中优先级线程抢占 CPU，使后台线程暂时无法继续运行和释放锁。
3. 高优先级 UI 线程回到 `next()`，却必须等那个后台线程。

UI 线程表面上被低优先级线程阻塞，实际等待时间还被中优先级任务放大，这就是优先级反转。Perfetto 中常见的证据是主线程出现 `monitor contention with ...`，并且能定位持锁线程和加锁代码位置。

### 哪些业务更容易暴露旧结构的上限

- 多个后台线程高频向主线程 `post()`。
- 队列已经积压大量延时消息，生产者需要在长链表中寻找插入位置。
- 大范围调用 `removeCallbacksAndMessages()` 或各种 `removeMessages()` 重载。
- 同步屏障存在时，Looper 需要越过同步消息继续寻找可执行的异步消息。

“主线程很忙”不等于“MessageQueue 锁竞争”。只有性能轨迹中出现对应的锁等待，或 A/B 测试能稳定复现差异，才能把问题归到队列同步结构。

## 3. `next()` 不只是取链表头

无论新旧实现，`next()` 都要同时处理等待、消息时序、同步屏障和空闲回调。

### 3.1 原生轮询：没有到期消息时让线程休眠

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

### 3.2 同步屏障：暂缓同步消息，让异步消息越过

同步屏障也是一条 `Message`，区别是 `target == null`。屏障生效时：

- 同步消息即使已经到期，也暂时不能分发。
- 到期的异步消息可以越过屏障。
- 移除屏障后，同步消息恢复正常选择。

`Choreographer` 的调度路径会使用异步 `Handler` 或异步消息，从而在渲染调度需要时越过屏障。这里的“异步”不表示启动新线程；消息仍由原 Looper 线程执行，只是在同步屏障存在时可以优先通过。

### 3.3 IdleHandler：队列准备休眠时执行

`MessageQueue.IdleHandler` 从 API 1 起就存在。当队列没有立即可执行的消息、准备等待下一条消息时，Looper 可以调用已注册的 IdleHandler。回调返回 `false` 时会被移除，返回 `true` 时继续保留。

IdleHandler 与同步屏障解决的是两类问题：

- 同步屏障决定“当前哪些消息可以越过”。
- IdleHandler 决定“没有立即可执行消息时，是否做一点空闲工作”。

IdleHandler 运行在 Looper 所在线程，耗时操作照样会阻塞后续消息，不能把它当后台执行器。

## 4. Android 17 如何决定使用 DeliQueue

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

## 5. DeliQueue 的数据结构

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

### 5.1 入队：Treiber 栈与 CAS

`MessageStack` 的源码注释将其定义为 “Treiber stack of Message objects”。Treiber 栈是一种后进先出的无锁栈，生产者通过比较并交换（Compare-And-Set，CAS）原子更新栈顶。下面的代码使用 release 内存顺序发布新节点，读取方则用 acquire 顺序读取，以保证节点内容在线程间可见：

```java
// frameworks/base/core/java/android/os/MessageStack.java
// AOSP android-17.0.0_r1，省略退出哨兵判断
do {
    current = (Message) sTop.getAcquire(this);
    m.next = current;
} while (!sTop.weakCompareAndSetRelease(this, current, m));
```

CAS 失败说明栈顶已被其他线程改变，当前线程会重新读取并重试。它避免了旧实现中“先取得全局监视器锁才能入队”的互斥等待，但不代表每次入队只执行一条指令：高竞争下仍可能多次重试，还要处理消息计数、插入序号和原生唤醒协调。

调用线程的提交路径是 O(1)，不随队列长度线性增长；随后 Looper 把消息放入最小堆时，仍要付出 O(log N) 的排序成本。排序成本没有消失，只是从“生产者在带锁链表中线性查找”改为“生产者快速提交，由单个消费者集中排序”。

### 5.2 出队：Looper 独占两个最小堆

`MessageStack.heapSweep()` 从当前栈顶遍历尚未处理的消息，建立供清理使用的反向链接，并按消息类型放入：

- `mSyncHeap`：同步消息和同步屏障。
- `mAsyncHeap`：异步消息。

`MessageHeap` 是用数组实现的最小堆，主要按 `when` 排序；执行时间相同时，再用插入序号 `insertSeq` 保持确定的提交顺序。只有 Looper 线程会实际调整堆结构，因此每次向上或向下调整时不需要再取得 Java 锁。

下一条消息的选择仍遵守旧语义：

1. 没有生效的同步屏障时，从已到期候选中选择应最先执行的消息。
2. 同步屏障生效时，同步消息被暂缓，只能选择到期的异步消息。
3. 没有消息到期时，计算等待时间并回到 `nativePollOnce()`。

DeliQueue 没有引入业务优先级、机器学习调度或新的线程优先级策略。应用能观察到的主要排序依据仍是 `when`、同时间的插入顺序、同步屏障和异步标记。

### 5.3 移除：先做逻辑删除，再由 Looper 清结构

`removeMessages()` 这类 API 按 `Handler`、`what`、`obj` 或 `Runnable` 匹配消息。因为 API 要删除所有匹配项，查找仍可能遍历已有消息，整体不能宣称为 O(1)。

找到目标后，DeliQueue 不让任意线程直接重排堆，而是分三步：

1. 对 `Message.flags` 做 CAS，设置 `FLAG_REMOVED`，完成逻辑删除。
2. 清理会造成对象滞留的引用字段，并把墓碑节点（tombstone，表示消息已删除但节点尚未物理移除）放进另一条无锁空闲列表（freelist）。
3. Looper 在 `drainFreelist()` 中把节点从栈和相应的堆里物理移除。

非 Looper 线程只负责把消息标记为无效，Looper 再清理自己独占的数据结构。读取线程即使短暂看到墓碑节点，也会根据已删除标记忽略它。

### 5.4 DeliQueue 为什么不复用 Message 池

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

### 5.5 睡眠、唤醒与退出也要无竞争地协同

消息容器之外还要处理唤醒竞争。生产者入队时可能让一条更早的消息成为新队首，需要唤醒正在执行原生轮询的 Looper；Looper 准备休眠时，也可能恰好有另一个线程入队。

DeliQueue 使用原子等待状态（wait state）协调“预计睡到何时”和“期间发生过多少次需要重新判断的事件”，避免遗漏唤醒信号。同步屏障也有独立的原子状态，用来判断新增异步消息是否需要唤醒消费者。

退出阶段的竞争更敏感：其他线程可能正在通过 `mPtr` 调用原生唤醒，而 Looper 正准备销毁原生对象。Android 17 使用带退出标志的引用计数，确保仍有线程使用时不会销毁 `mPtr` 指向的对象。`quitSafely()` 仍然只处理已经到期的消息并移除未来消息；销毁原生对象则要等正在使用它的线程离开临界阶段。

## 6. “无锁 MessageQueue”不代表整个类没有锁

官方把 DeliQueue 称为无锁（lock-free）MessageQueue，因为消息的核心并发提交、检查和移除不再依赖旧的单一全局监视器锁。这里的“无锁”描述一种进展保证：即使某个参与线程暂停，其他线程仍能继续完成操作。

但 `android-17.0.0_r1` 的组合实现仍能看到：

- `mIdleHandlersLock`：保护 IdleHandler 集合。
- `mFileDescriptorRecordsLock`：保护文件描述符监听记录。
- 旧版路径里的 `synchronized (this)`。
- 原生轮询、唤醒和退出阶段的协调。

准确的表述是：DeliQueue 消除了旧 MessageQueue 核心消息路径上的单一全局监视器锁，并使用无锁共享结构与 Looper 私有堆协作。若把它理解成“MessageQueue 内任何操作都不加锁”，就会与源码冲突。

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

图中的 `enqueue`、`next`、`sweep` 分别表示入队、取下一条消息和把新消息整理进堆；`sync/async` 表示同步/异步，`barrier` 表示同步屏障，`tombstone` 表示逻辑删除标记。屏障行为没有改变：同步消息等待，异步消息可以越过。变化在于生产者提交消息时，不再为了修改同一条链表而与 Looper 互斥。

这会改善 `VSYNC-app` 到 `doFrame()` 之间因为队列锁竞争造成的抖动，但不能保证每一帧都更快：

- `doFrame()` 中的测量、布局或绘制（measure/layout/draw）太慢时，DeliQueue 无法修复。
- 主线程被别的应用锁、Binder 或调度延迟挡住，仍要查各自根因。
- 队列积压来自业务过量投递时，新结构能降低管理成本，却不会替应用丢弃无意义工作。

## 8. 官方性能数字应该怎样解读

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

## 9. Android 17 迁移风险

### 9.1 反射 `mMessages` 得不到真实队列

为了兼容已有二进制，Android 17 仍保留私有字段 `mMessages`。DeliQueue 路径不使用它，官方迁移文档明确说明该字段会一直是 `null`。任何通过反射遍历 `mMessages` 的测试、监控或调试工具都不再可靠。

不要改为反射 `MessageStack` 或 `MessageHeap`。这些同样是私有实现，后续版本可以继续变化。测试代码应迁移到公开或测试专用 API。

### 9.2 测试框架版本

官方给出的最低建议是：

- Espresso 3.7.0 或更高版本。
- Robolectric 4.17 或更高版本，并从 `@LooperMode(LEGACY)` 迁移到 `@LooperMode(PAUSED)`。
- 设备端插桩测试（instrumentation test）使用 `TestLooperManager`，包括 Android 17 增加的 `peekWhen()`、`poll()` 等能力，不再依赖 MessageQueue 私有字段。

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

- 关闭后崩溃消失：优先排查反射和测试工具对内部结构的假设。
- 开启后监视器锁竞争消失：说明旧队列锁是原链路的一部分。
- 两边 `dispatchMessage()` 都很长：继续修业务代码，别把它算成 DeliQueue 问题。

兼容开关用于开发验证和故障隔离，不应成为应用长期依赖的产品配置。

## 10. 用 Perfetto 验证，避免凭体感归因

### 第一步：确认等待发生在哪里

旧实现的典型证据是主线程出现 `monitor contention with ...` 轨迹区段，阻塞方法指向 `MessageQueue`。官方文章给出的 PerfettoSQL 使用 `android_monitor_contention` 表，并以 `short_blocked_method LIKE "%MessageQueue%"` 筛选主线程等待。

主线程仅处于休眠（Sleeping）状态不能证明存在锁竞争。它可能只是正常阻塞在 `nativePollOnce()`，等待下一条消息；只有结合竞争区段、持锁者和调用点，才能确认是 Java 监视器锁。

### 第二步：分开统计队列等待和消息执行

- 队列侧：MessageQueue 监视器锁竞争次数、总时长、P95/P99，以及持锁线程。
- 执行侧：Looper/Handler 轨迹区段下的具体回调、`doFrame()`、Binder、I/O 和锁。
- 帧侧：实际帧时间线、丢帧原因，以及 `VSYNC-app` 到 `doFrame()` 的延迟。

Android 17 新实现消除旧队列的监视器锁竞争后，主线程仍可能处于可运行状态却拿不到 CPU，也可能在其他锁上阻塞。线程状态必须结合调度和调用栈一起检查。

### 第三步：做控制变量明确的 A/B

应在同一台 Android 17 设备、同一构建版本、同一 APK 和同一套操作脚本上，只切换 `USE_NEW_MESSAGEQUEUE`。每轮强制停止并冷启动进程，收集多份性能轨迹，再比较分位数。不能直接对比 Android 16 与 Android 17 两个完整系统，再把所有差异都归给 DeliQueue。

对 `system_server` 做平台开发时，Android 17 还提供 `mq` 轨迹事件（track event）分类，可在 Perfetto 配置中启用 MessageQueue 跟踪。分析普通应用时，仍应优先使用稳定的 Looper、调度、锁竞争和帧时间线证据，不要依赖隐藏实现字段。

## 11. 版本演进

| 版本 | MessageQueue 相关变化 |
| --- | --- |
| Android 1.0（API 1） | `MessageQueue`、`Looper` 与 `IdleHandler` 已存在 |
| Android 4.1（API 16） | `Choreographer` 使用同步屏障与异步消息组织渲染调度 |
| Android 15（API 35） | 旧版主线仍是单链表加单一监视器锁 |
| Android 16（API 36） | 公开源码出现组合版、并发版和旧版多种实现，处于优先为系统进程逐步启用的阶段 |
| Android 17（API 37） | DeliQueue 面向 `targetSdkVersion >= 37` 的应用默认启用；当前源码锚点为 `CombinedDeliMessageQueue`、`MessageStack`、`MessageHeap` 与扩展后的 `Message` |

Android 16 的并发实现适合解释演进，不能替代 Android 17 的当前源码。Android 17 的 `MessageStack` 本身就是 Treiber 栈，不能描述成“用 MessageStack 替换 Treiber 栈”；真正的变化是并发原型最终采用共享 Treiber 栈、Looper 私有双堆、墓碑删除，以及完整的休眠和退出协调。

## 12. 常见误判

### “无锁就是没有任何 `synchronized`”

不是。核心消息路径不再依赖旧的全局监视器锁，但 IdleHandler、文件描述符记录和旧版路径仍有各自的锁。

### “CAS 一定比锁快”

不是。竞争较少且临界区很短时，锁可能已经足够快；高竞争下 CAS 也会不断重试。DeliQueue 的收益来自重新设计 MessageQueue 的整体结构，不能简单归结为把每个 `synchronized` 替换成原子变量。

### “MessageStack 解决了所有 ABA 问题”

不准确。`MessageStack` 就是 Treiber 栈。Android 17 通过禁止 DeliQueue 中的 `Message` 对象池复用、保留墓碑节点的生命周期，并限定只有 Looper 修改实际结构，来规避节点复用引发的 ABA 问题。

### “新队列给渲染消息增加了更高业务优先级”

没有。同步屏障与异步消息语义沿用既有模型；DeliQueue 改的是并发容器和协调算法，不是应用任务优先级系统。

### “主线程处于休眠状态就是队列锁竞争”

不成立。空闲 Looper 正常阻塞在原生轮询中。只有看到 `android_monitor_contention`、持锁线程和 MessageQueue 调用点，才能确认存在旧版监视器锁竞争。

## 结论

阅读 Android 17 MessageQueue，需要抓住两条边界。

第一，DeliQueue 优化的是入队和出队：生产者通过 CAS 把消息提交到 `MessageStack`，Looper 再把消息整理进自己独占的同步/异步最小堆；移除操作先做逻辑删除，再由 Looper 清理结构。同步屏障、异步消息、IdleHandler 和原生轮询的对外语义都没有改变。

第二，官方所说的无锁，指核心消息并发路径不再依赖旧的单一全局监视器锁；它不代表整个类没有锁，也不代表业务回调会自动变快。迁移时应检查反射和测试框架；性能分析时，要把队列等待与 `dispatchMessage()` 之后的业务执行分开，并通过同版本兼容开关和 Perfetto 证据完成 A/B 测试。

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
