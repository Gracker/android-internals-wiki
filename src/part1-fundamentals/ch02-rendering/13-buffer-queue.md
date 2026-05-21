---
title: 图形缓冲区管理 (BufferQueue)
chapter: '2.13'
section: '2.13'
status: "finalized"
applicable_versions: Android 4.1 (API 16) - Android 17 (API 37)
tags:
- BufferQueue
- BLASTBufferQueue
- GraphicBuffer
- Surface
- 渲染管线
- Gralloc
- SurfaceFlinger
- 三缓冲
related_chapters:
- '2.1'
- '2.4'
- '2.5'
- '2.6'
- '2.9'
- '2.16'
- '7.2'
created_by: task2a-knowledge-gap
created_date: '2026-04-04'
gap_source: AOSP结构+官方文档+研究素材
gap_score: 14/20
drafted_by: openclaw-task2a
drafted_date: '2026-04-04'
reviewed_by: "openclaw-task6"
reviewed_date: "2026-04-28"
last_verified: '2026-05-08'
last_verified_against: AOSP main + android-16.0.0_r1 + android-14.0.0_r1 + android-12/11/10/4.1 tags + external review
confidence: high
sources:
- type: aosp
  path: frameworks/native/libs/gui/include/gui/IGraphicBufferProducer.h
- type: aosp
  path: frameworks/native/libs/gui/include/gui/IGraphicBufferConsumer.h
- type: aosp
  path: frameworks/native/libs/gui/include/gui/BufferSlot.h
- type: aosp
  path: frameworks/native/libs/gui/include/gui/BufferItem.h
- type: aosp
  path: frameworks/native/libs/gui/BufferQueue.cpp
- type: aosp
  path: frameworks/native/libs/gui/BufferQueueCore.cpp
- type: aosp
  path: frameworks/native/libs/gui/BufferQueueProducer.cpp
- type: aosp
  path: frameworks/native/libs/gui/BufferQueueConsumer.cpp
- type: aosp
  path: frameworks/native/libs/gui/BLASTBufferQueue.cpp
- type: aosp
  path: frameworks/base/core/java/android/view/ViewRootImpl.java
- type: official
  path: https://source.android.com/docs/core/graphics/architecture
pipeline_stage: "ready-to-publish"
task6_result: "pass-light-edit"
task6_state: reviewed
task9_state: "reviewed"
task2b_state: "fixed"
task9_result: "pass-tech-review"
task2b_result: "fixed"
task9_reviewed_date: 2026-05-19
task9_reviewed_by: openclaw-task9
last_task9_at: "2026-05-19T00:30:02+08:00"
last_task9_audit: "2026-05-18"
last_task6_at: "2026-05-21T09:08:00+08:00"
last_task6_audit: "2026-05-21"
last_task6_audit_result: l1-light-edit
last_task6_audit_log: "logs/review/2026-05-21-09-audit.md"
review_round: 1
last_task9_review_log: logs/deep-review/2026-05-19-00-deep-review.md
task9_review_notes: "2026-05-19 Task9 00:20：pass-tech-review。无 P0/P1；P2 2 处已写入 suggestions；Task6 pass 且 queue 无 pending，保持 finalized 并自动标记 ready-to-publish。"
---

# 2.13 图形缓冲区管理 (BufferQueue)

<!-- outline-start -->
## 本节要点大纲

### 锚点(必须覆盖)

- 🔹 BufferQueue 为什么存在,它解决的是跨进程共享 GraphicBuffer 和同步问题,不是"传像素数组"
- 🔹 `dequeueBuffer()` → `requestBuffer()` → `queueBuffer()` 的真实调用链
- 🔹 `BufferSlot::BufferState` 如何描述 FREE / DEQUEUED / QUEUED / ACQUIRED / SHARED
- 🔹 Sync Fence 如何决定 buffer 何时可写、可读、可复用
- 🔹 BLASTBufferQueue 如何把 buffer 与 `SurfaceControl.Transaction` 绑到同一帧
- 🔹 BufferQueue 在 Perfetto 中的正常与异常读法

### 扩展(可选深入)

- 🔸 三缓冲与 `setMaxDequeuedBufferCount(2)` 的关系
- 🔸 从 Project Butter 到 BLAST 的两次大变化

### OpenClaw 加工指引

> 锚点是最低覆盖要求。
> 没有实测 Trace 的地方,用 `[图:...]` 或 `[需补充素材:...]` 明确占位,不写假截图。
> 涉及版本结论,只保留能在 AOSP tag 或官方文档中落下来的事实。

<!-- outline-end -->

## 为什么要了解 BufferQueue

如果我们在 Perfetto 里看到 RenderThread 卡在 `dequeueBuffer()`,或者看到 App 已经 `queueBuffer()` 了,但 SurfaceFlinger 很晚才把这一帧合成上屏,问题往往不在"画得快不快"这一层,而在 BufferQueue 这一层。它决定了一帧图像怎样在 producer 和 consumer 之间流转,也决定了什么时候能复用旧 buffer,什么时候必须继续等。

这部分知识的价值在于把"GPU 太慢"、"SurfaceFlinger 太慢"、"buffer 没有及时释放"、"geometry transaction 和 buffer 落在不同帧"这几类问题拆开,而不是记住几个 API 名字。拆开之后,我们在 Trace 里看到的长等待,才知道该往哪条链路继续挖。

## BufferQueue 不是"传一帧像素",而是"共享一组 slot"

BufferQueue 的基本角色没有什么花哨的地方。producer 负责写入一帧内容,consumer 负责读取这一帧去合成或显示,中间那层 BufferQueue 负责维护一组 slot、这些 slot 上绑定的 `GraphicBuffer`,以及双方交接时需要的同步信息。

在经典窗口路径里,App 是 producer,SurfaceFlinger 是 consumer。两边不直接拷贝整帧像素,而是共享同一块 `GraphicBuffer`。这样一来,1080p 一帧八九 MB 的像素不会在进程之间来回复制,跨进程传的主要是 slot、fence 和元数据。

这也是很多文章最容易写歪的地方。BufferQueue 的核心动作是把某个 slot 里已经存在的那块 buffer 交给下一方，并告诉对方什么时候可以安全地读写。

[已验证:AOSP main `frameworks/native/libs/gui/include/gui/IGraphicBufferProducer.h`、`frameworks/native/libs/gui/include/gui/BufferItem.h`]

## `dequeueBuffer()` → `requestBuffer()` → `queueBuffer()` 的真实链路

把 `queueBuffer()` 写成"每帧把 binder handle 传给 SurfaceFlinger",这个说法不对。AOSP 的 producer 接口把"选 slot"和"取 buffer 句柄"拆成了两个步骤:先 `dequeueBuffer()`,必要时再 `requestBuffer()`。

```cpp
// frameworks/native/libs/gui/include/gui/IGraphicBufferProducer.h
virtual status_t requestBuffer(int slot, sp<GraphicBuffer>* buf) = 0;
virtual status_t dequeueBuffer(int* slot, sp<Fence>* fence, uint32_t w, uint32_t h,
                               PixelFormat format, uint64_t usage,
                               uint64_t* outBufferAge,
                               FrameEventHistoryDelta* outTimestamps) = 0;
virtual status_t queueBuffer(int slot, const QueueBufferInput& input,
                             QueueBufferOutput* output) = 0;
```

这三个调用连起来,真实语义是这样的。

第一步,`dequeueBuffer()` 先从 BufferQueue 里挑一个可用 slot 出来,同时返回一个 fence。AOSP 注释写得很直接,producer 在这个 fence signal 之前不能覆盖旧内容。这条 fence 代表的是"上一次 consumer 对这块 buffer 的使用已经结束了没有"。

第二步,如果 `dequeueBuffer()` 返回的 slot 需要重新分配,producer 会看到 `BUFFER_NEEDS_REALLOCATION`,这时再调用 `requestBuffer(slot, &buf)` 把这个 slot 当前绑定的 `GraphicBuffer` 取出来。也就是说,slot 和 `GraphicBuffer` 的映射不是每帧都重新传一次,只有首次分配、尺寸变化、格式变化,或者 attach/detach 这类场景,才需要同步新的句柄。

第三步,producer 把内容画到这块 `GraphicBuffer` 里。等 GPU 或 CPU 写完以后,调用 `queueBuffer(slot, QueueBufferInput)` 把 slot 放回队列。这次 `queueBuffer()` 一起提交的是 slot 编号、时间戳、crop、transform、dataspace,以及 `QueueBufferInput::fence`。AOSP 对这个 fence 的注释也很明确,它是"consumer 在读取这个 buffer 之前必须等待的 fence"。

高频流转的是 slot 编号、metadata（时间戳、crop、transform）和 fence——不是完整的 `GraphicBuffer` handle。把这条链路说准，后面讨论阻塞和掉帧才不会偏。

[已验证:AOSP main `frameworks/native/libs/gui/include/gui/IGraphicBufferProducer.h`]

## `BufferSlot::BufferState` 不是单一 enum

另一个常见误解,是把 slot 状态机写成一个互斥 enum,然后假设一个 slot 在任何时刻只能是 FREE、DEQUEUED、QUEUED、ACQUIRED 中的一个。普通窗口路径大多数时候看起来像这样,但 AOSP 现在的实现不是这么建模的。

```cpp
// frameworks/native/libs/gui/include/gui/BufferSlot.h
struct BufferState {
    uint32_t mDequeueCount;
    uint32_t mQueueCount;
    uint32_t mAcquireCount;
    bool mShared;

    inline bool isFree() const { return !isAcquired() && !isDequeued() && !isQueued(); }
    inline bool isDequeued() const { return mDequeueCount > 0; }
    inline bool isQueued() const { return mQueueCount > 0; }
    inline bool isAcquired() const { return mAcquireCount > 0; }
    inline bool isShared() const { return mShared; }
};
```

AOSP 注释给出的状态表很清楚。正常模式下,FREE、DEQUEUED、QUEUED、ACQUIRED 这些状态看起来还是互斥的,但实现层面已经换成了计数器。原因是 shared buffer mode 允许 `mShared` 和其他状态并存,一个 slot 可以一边 shared,一边仍然处在 dequeued、queued 或 acquired 计数不为 0 的状态。

排查问题时,不能再把 `mBufferState == FREE` 这种老口径当成今天的源码事实。更稳妥的说法是,普通路径里 slot 大多数时候呈现为单状态流转,shared buffer mode 下状态会叠加,源码判断应以 `isFree()`、`isDequeued()`、`isQueued()`、`isAcquired()`、`isShared()` 这几组方法为准。

[已验证:AOSP main `frameworks/native/libs/gui/include/gui/BufferSlot.h`]

### 三缓冲通常怎么出现

"三缓冲"是最常见的窗口表现,不是唯一合法配置。对 App 窗口来说,我们经常会看到 producer 最多同时 dequeue 两块 buffer,consumer 再持有一块正在显示或等待 release 的 buffer,于是整体表现成三缓冲。

在 BLAST 路径里,`BLASTBufferQueue::onFirstRef()` 设置 `maxDequeuedBufferCount`。Android 14 及更早版本默认值为 2,配上 consumer 侧的一块已 acquire buffer,形成三缓冲工作形态。android-16.0.0_r1 的默认值仍为 2,并未提升至 3;不同 Surface 类型、async mode、consumer 约束都可能让上限变化。

## Sync Fence 决定"状态变了"和"真的能碰这块内存"不是一回事

只看 slot 状态,我们最多知道 buffer 的所有权大概在谁手里;只看 fence,我们才知道它是不是已经真的可以读写。这两件事必须放在一起看。

先看 producer 这一侧。`dequeueBuffer()` 返回的 fence 说明上一位使用者是不是已经结束使用。slot 已经回到了 producer 这边,不代表 producer 立刻就能覆盖旧内容,必须等这条 fence signal。

再看 consumer 这一侧。producer 调 `queueBuffer()` 时会把 `QueueBufferInput::fence` 一起交出去。这个 fence 说明"我把 slot 交给你了,但 GPU 可能还没把最后几笔写完,你要等到 fence signal 才能读"。所以,slot 进入 QUEUED 不代表 SurfaceFlinger 这一刻就能安全合成。

最后是回收。consumer 处理完成后会走 `releaseBuffer(..., releaseFence)`。这个 release fence 会在下一次 producer `dequeueBuffer()` 这块 slot 时回到 producer 手里,告诉它"现在这块内存真的空了,可以重写"。

AOSP 在 `BufferItem.h` 里把 `mFence` 注释为"buffer idle 时 signal 的 fence",在 `IGraphicBufferConsumer.h` 里又把 `releaseBuffer()` 的 `releaseFence` 明确成 consumer 归还 buffer 时携带的同步信息。光看 FREE / QUEUED / ACQUIRED 这些字面状态,不足以解释为什么某个 buffer 明明已经 release 了,producer 还要再等一会儿才能复用,原因就在 fence。

这一层和 §2.16 Sync Fence 框架与帧同步机制是同一件事的两个切面。§2.16 解释 fence 在内核和 SurfaceFlinger 里的同步意义,这一节更关心 fence 怎样把 BufferQueue 的 slot 状态变成"可写、可读、可复用"的时间边界。

[已验证:AOSP main `frameworks/native/libs/gui/include/gui/IGraphicBufferProducer.h`、`frameworks/native/libs/gui/include/gui/IGraphicBufferConsumer.h`、`frameworks/native/libs/gui/include/gui/BufferItem.h`]

## BLASTBufferQueue 解决的是 buffer 与 geometry transaction 落在同一帧

如果把 BLAST 只概括成"少了一次 Binder hop",说轻了。它解决的是 buffer 提交和 geometry transaction 以前走两条线的问题:窗口尺寸、crop、transform、buffer 内容不一定能落在同一帧。

AOSP tag 只能说明 BLAST 的代码进入时间,不能直接等同于所有窗口的默认路径。`android-10.0.0_r47` 里没有 `frameworks/native/libs/gui/BLASTBufferQueue.cpp`,`android-11.0.0_r48` 已经有这个文件,`ViewRootImpl.java` 里也能看到 `mBlastBufferQueue` 和 `new BLASTBufferQueue(...)`。Android 11 可以确认已有 BLAST 窗口提交流程;常规 Activity 窗口全面转向 BLAST,要按 Android 12(S)作为默认分界更稳。

```java
// frameworks/base/core/java/android/view/ViewRootImpl.java
mBlastBufferQueue = new BLASTBufferQueue(mTag, mSurfaceControl,
        mSurfaceSize.x, mSurfaceSize.y, mWindowAttributes.format);
```

```cpp
// frameworks/native/libs/gui/BLASTBufferQueue.cpp
createBufferQueue(&mProducer, &mConsumer);
mBufferItemConsumer = new BLASTBufferItemConsumer(...);
mBufferItemConsumer->setFrameAvailableListener(this);
...
t->setBuffer(mSurfaceControl, buffer, fence, bufferItem.mFrameNumber, mProducerId,
             releaseBufferCallback, dequeueTime);
```

这段流程拆开看,一共五步。

第一,`ViewRootImpl` 在 App 进程里创建 `BLASTBufferQueue`。这一步说明 BLASTBufferQueue 是窗口提交路径上的新组件，而不是旧 BufferQueue 的一个简单参数配置。

第二,BLAST 在本地创建自己的 producer / consumer 对。`createBufferQueue(&mProducer, &mConsumer)` 做的就是这件事。producer 还是给渲染线程 dequeue / queue 用,consumer 则是 App 进程里的 `BLASTBufferItemConsumer`。

第三,本地 consumer 把 `setFrameAvailableListener(this)` 挂到自己身上。producer 一旦 `queueBuffer()`，回调先在 App 进程内的 BLAST 层触发 `onFrameAvailable()`，再由 BLAST 决定何时通知远端 SurfaceFlinger。

第四,BLAST 在 `acquireNextBufferLocked()` 里拿到下一块 buffer,再通过 `Transaction::setBuffer(..., frameNumber, ...)` 把 buffer、fence 和 `frameNumber` 一起塞进 `SurfaceControl.Transaction`。这里的 `frameNumber` 很关键,它把"这块 buffer 属于哪一帧"说死了。

第五,如果这一帧还有窗口大小、裁剪区域、alpha、z-order 之类的 geometry 变化,BLAST 会把它们先放进 pending transaction,后面通过 `mergeWithNextTransaction(frameNumber)` 和 `applyPendingTransactions(frameNumber)` 按 frame number 归到同一帧再统一 apply。这样一来,buffer 和 geometry 就不会错帧。

所以,BLAST 的核心价值不是一句"跨进程更少,所以更快"就能讲完的。它做的是把"这一帧的内容"和"这一帧的窗口状态"绑在一起,减少内容已经更新了、窗口属性却还停在上一帧的错位。

[已验证:AOSP `android-10.0.0_r47`、`android-11.0.0_r48`、main 的 `ViewRootImpl.java` 与 `BLASTBufferQueue.cpp`]

## Legacy vs BLASTBufferQueue:Consumer 端驻留位置的架构差异

<!-- AIW-源码调研-2026-04-19 -->

### BufferQueue 内部锁架构:mCore->mMutex 是 producer-consumer 共享的唯一锁

<!-- AIW-源码调研-2026-04-29 -->
这一小节专门补齐 BufferQueue 内部的锁竞争架构,是 §7.2 "BufferQueue 内部的锁竞争机制"盲区的源码级答案。

#### BufferQueueCore::mMutex 中心锁

`BufferQueueCore` 是 producer 和 consumer 共享的底层队列核心,持有所有共享状态。`mMutex` 是这些状态的唯一保护锁:

```cpp
// frameworks/native/libs/gui/include/gui/BufferQueueCore.h (android-14)
class BufferQueueCore {
    mutable std::mutex mMutex;

    // 共享数据结构
    BufferQueueDefs::SlotsType mSlots; // NUM_BUFFER_SLOTS = 64
    std::set<int> mFreeSlots;
    std::list<int> mFreeBuffers;
    uint64_t mFrameCounter;
    std::condition_variable mDequeueCondition;
    // ...
};
```

所有访问 `mSlots`、`mFrameCounter`、`mFreeSlots`、`mFreeBuffers` 的代码路径,必须先 `std::lock_guard<std::mutex> lock(mCore->mMutex)`。Producer 端和 Consumer 端通过同一个 `sp<BufferQueueCore>` 引用操作,因此竞争的是同一个 mutex 实例。

#### Producer 端锁路径:BufferQueueProducer

`BufferQueueProducer` 持有 `sp<BufferQueueCore> mCore`。以下操作均在 `mCore->mMutex` 保护下:

| 方法 | 关键操作 | 锁内行为 |
|------|---------|----------|
| `dequeueBuffer()` | 选 slot → 状态置 DEQUEUED | 从 mFreeBuffers/mFreeSlots 找可用 slot;waitForFreeSlotThenRelock() 阻塞时释放锁 |
| `queueBuffer()` | `++mCore->mFrameCounter` | 原子递增;状态置 QUEUED;mSlots[slot].mFrameNumber 赋值 |
| `detachBuffer()` | slot 从 mActiveBuffers 移除 | 状态恢复 FREE;slot index 归还 mFreeSlots/mFreeBuffers |
| `connect()` | `std::lock_guard<std::mutex> lock(mCore->mMutex)` | 设置 listener 和 api 版本 |

`waitForFreeSlotThenRelock()` 的阻塞机制:AOSP 使用 `mDequeueCondition.wait(lock, predicate)` C++11 RAII 条件变量。Predicate 检查 `dequeuedCount >= mMaxDequeuedBufferCount` 或 `tooManyBuffers`。唤醒来自 `releaseBuffer()` 或 `cancelBuffer()` 的 `notify_all()`。

#### Consumer 端锁路径:BufferQueueConsumer

`BufferQueueConsumer` 同样持有 `sp<BufferQueueCore> mCore`:

| 方法 | 关键操作 | 锁内行为 |
|------|---------|----------|
| `acquireBuffer()` | 从 mQueue(FIFO) 取 BufferItem | 状态置 ACQUIRED |
| `releaseBuffer()` | 状态置 FREE | 归还到 mFreeBuffers/mFreeSlots;`mDequeueCondition.notify_all()` 唤醒 producer |

#### BufferState 状态机(计数器版本)

AOSP android-14+ 的 `BufferSlot::BufferState` 已从互斥 enum 演进为计数器:

```cpp
// frameworks/native/libs/gui/include/gui/BufferSlot.h
struct BufferState {
    uint32_t mDequeueCount;  // dequeue 次数
    uint32_t mQueueCount;    // queue 次数
    uint32_t mAcquireCount;  // acquire 次数
    bool mShared;

    inline bool isFree()    const { return !isAcquired() && !isDequeued() && !isQueued(); }
    inline bool isDequeued() const { return mDequeueCount > 0; }
    inline bool isQueued()  const { return mQueueCount > 0; }
    inline bool isAcquired() const { return mAcquireCount > 0; }
    inline bool isShared()  const { return mShared; }
};
```

正常单生产者-单消费者路径呈现为互斥状态,但 shared buffer mode 下计数可叠加。判断应以 `isFree()` / `isDequeued()` 等方法为准,不能直接比较 `mBufferState == FREE`。

#### Perfetto 观测点

`libgui_bufferqueue_dequeueBuffer`、`libgui_bufferqueue_queueBuffer`、`libgui_bufferqueue_acquireBuffer`、`libgui_bufferqueue_releaseBuffer` slice 可直接观察各端持锁时间。`android.monitor_contention` 表通过 `lock_class_name` 可定位 `BufferQueueCore::mMutex` 争用。

[已验证:AOSP android14-release `BufferQueueCore.h`、`BufferQueueProducer.cpp`、`BufferQueueConsumer.cpp`、`BufferSlot.h`]


本节前面描述了 BLAST 的行为特征,这一小节专门对比 Legacy 路径和 Android 12+ 常规窗口默认 BLAST 路径在 **Consumer 端驻留位置** 这一维度上的差异。这是理解 BLAST 解决了什么问题的前提。

### Legacy 模式:Consumer 在 SurfaceFlinger 进程

在 Legacy 模型中,当 App 请求一个 Surface 时,WindowManagerService 通过 `SurfaceFlinger::createLayer()` 在 SF 进程内创建 `BufferQueue`。这个 BufferQueue 的 Consumer 端--`BufferQueueCore` + `BufferItemConsumer`--属于 SF 进程。Producer 端(`IGraphicBufferProducer`)通过 Binder IPC 暴露给 App。

关键特征:
- **Consumer 端在 SF**:SF 通过 `BufferQueueConsumer` 管理 buffer 的 acquire/release
- **两条分离的提交路径**:App 的 buffer 提交走 `queueBuffer()`(Binder 到 SF),几何属性变更走 `SurfaceControl.Transaction`(单独 Binder 调用)。两条路径**无原子性保证**
- **多进程场景缺陷**:当多个进程各自持有 SurfaceControl、都想更新同一窗口的 buffer 时,无法在帧级别同步

### BLAST 模式:Consumer 移入 App 进程

Android S(12)开始,常规 Activity 窗口默认使用 BLASTBufferQueue,Consumer 端移入 App 进程:

**BLASTBufferQueue 内部组件**(`platform/frameworks/native/libs/gui/BLASTBufferQueue.cpp`,android-14.0.0_r1):

```
BLASTBufferQueue
├── BufferQueueCore              // 队列核心(可跨进程共享)
├── BBQBufferQueueProducer       // Producer 端(在 App 进程)
│   └── 继承 BufferQueueProducer,实现异步 IProducerListener 回调
│   └── 构造签名:BBQBufferQueueProducer(core, wp<BLASTBufferQueue>)
│   └── connect() 时 consumerIsSurfaceFlinger = false
└── BLASTBufferItemConsumer     // Consumer 端(在 App 进程)
    ├── 继承 BufferItemConsumer
    ├── 管理 frame event history(addAndGetFrameTimestamps / updateFrameTimestamps)
    ├── 处理 sideband stream 变更(onSidebandStreamChanged)
    └── 新 frame 可用时,通过 mConsumerListener 回调通知 SF
```

关键变化:
- **Consumer 端在 App**:App 内 BLASTBufferItemConsumer 持有 `mConsumerListener`,当新 frame 可用时通知 SF
- **事务统一**:Buffer + 几何属性通过 `SurfaceControl.Transaction::setBuffer()` + geometry setters 合并为一次原子提交
- **`frameNumber` 绑定**:每帧 buffer 和 geometry 共享同一个 `frameNumber`,保证在同一帧 apply

**App 进程内创建路径**(`ViewRootImpl.java` → `relayoutWindow()` → `updateBlastSurfaceIfNeeded()` → `new BLASTBufferQueue(...)`):
```java
// frameworks/base/core/java/android/view/ViewRootImpl.java
mBlastBufferQueue = new BLASTBufferQueue(mTag, mSurfaceControl,
        mSurfaceSize.x, mSurfaceSize.y, mWindowAttributes.format);
```

**BBQBufferQueueProducer 异步回调**(android-14 commit `f982044859e`):`BLASTBufferQueue.cpp` 中的 `AsyncProducerListener` 会把 `IProducerListener` 回调投递到 `AsyncWorker`。传统同步回调如果在 listener 内部再次触发 `queueBuffer()` 一类路径,容易形成锁等待;异步包装把 producer 的 dequeue 路径和 listener 执行解耦,减少渲染线程被回调反向拖住的风险。

### 架构差异总结

| 维度 | Legacy 路径 | BLAST 常规窗口路径(Android 12+ 默认) |
|------|---------------------|---------------------|
| Consumer 端位置 | SurfaceFlinger 进程 | App 进程(BLASTBufferItemConsumer) |
| Buffer/Geometry 提交 | 两条独立路径,无原子性 | 合并为 Transaction,原子 apply |
| 跨进程帧同步 | 不支持 | BLAST SyncEngine 支持 |
| SF 负担 | BufferQueue 管理集中在 SF | 卸荷到 App,SF 只合成 |
| 多 SurfaceControl 同步 | 各自 queueBuffer,无协调 | Transaction 合并统一 apply |

**为什么这个区别对性能分析重要**:当我们在 Perfetto 中看到 App 侧 `dequeueBuffer()` 阻塞,Legacy 路径通常来自 SF 进程的 Consumer release 延迟;BLAST 路径还要检查 App 进程内 `BLASTBufferItemConsumer` 的 acquire/release 延迟。判断是哪一层的问题,需要先确认当前窗口是否运行在 Android 12+ 默认 BLAST 模型下。

[已验证:AOSP `android-11.0.0_r48`、`android-14.0.0_r1` 的 BLASTBufferQueue.cpp/BBQBufferQueueProducer commit (f982044859e, d8b3d5f056)]

---

## 在 Perfetto 中怎么读 BufferQueue

BufferQueue 的等待时间强依赖刷新率、Surface 类型和系统负载。`dequeueBuffer()` 等 3ms 在 120Hz 游戏场景里可能已经很扎眼,在 60Hz、复杂合成、SurfaceView 或视频路径里却未必能直接下结论。分析 BufferQueue 问题,需要先在同机型、同刷新率、同 Surface 类型上建立一条正常基线,再看偏离。

### 正常路径长什么样

正常情况下,App 这边 `queueBuffer()` 之后,consumer 会在接下来的合成周期里把它消费掉。BLAST 路径下,AOSP 还会把 trace 名字拼成 `QueuedBuffer - {windowName}BLAST#{producerId}`,这给我们把 app 侧提交和窗口消费对应起来提供了一个很实用的锚点。

在 Perfetto 中排查帧对齐问题时,可以利用 vsyncId 关联不同轨道的数据。vsyncId 出现在 `BLASTBufferQueue::acquireNextBufferLocked()` 的 `ATRACE_FORMAT` 中（Android 14 已存在）,配合 FrameTimeline 可以把 App 侧提交、SurfaceFlinger 合成周期和实际呈现时间串到同一个 vsync 周期。排查“App 以为自己交了帧但 SF 没合成”这类问题时,vsyncId 比时间戳对齐更可靠。注意 `queueBuffer` 本身的 trace 名称不会携带 vsyncId 后缀；vsyncId 关联入口在 BLAST 层和 FrameTimeline。

如果同机型的平滑滑动 trace 里,`QueuedBuffer - ...BLAST#...` 到 FrameTimeline 实际呈现之间通常只隔一个合成周期,而某次卡顿 trace 连续跨了多个周期,这就说明问题已经不只是"这一帧画慢了",而是 buffer 提交之后在下游又堆住了。

[图:正常场景。同机型、同刷新率下的窗口渲染 trace,标出 RenderThread 的 `queueBuffer()`、BLAST 的 `QueuedBuffer - <window>BLAST#<id>`,以及下一次合成周期里的呈现位置。]

[需补充素材:正常场景 Perfetto 截图 1 张,要求同机型、同刷新率,并标注 App 提交和实际呈现的对应关系。]

### 异常 1:`dequeueBuffer()` 等不到可复用 buffer

这类问题最典型的表现,是 App 或 RenderThread 想拿下一块 buffer 开工,却一直等不到。原因通常不是一个名字能概括的,它可能是 consumer 还没 release,也可能是 release 了但 release fence 还没 signal,还可能是 SurfaceFlinger / HWC 下游太慢,整条链都在往后推。

这时不要只盯着 `dequeueBuffer()` 本身。要把它和 consumer 侧一起看。假如 SurfaceFlinger 合成周期也在拉长,或者上一帧 present 很晚才完成,那么 `dequeueBuffer()` 等待往往只是结果,不是根因。反过来,如果 consumer 并不忙,却还是迟迟拿不到可复用 buffer,就该回头查 slot 数量、shared mode、buffer count 约束这些上游配置。

[图:异常场景。RenderThread 在 `dequeueBuffer()` 处长时间等待,同时标出 SurfaceFlinger 合成和上一帧 release 的时间位置。]

[需补充素材:异常场景 Perfetto 截图 1 张,要求标出 `dequeueBuffer()` 长等待,以及与上一帧 release / present 的关系。]

### 阻塞根因:mDequeueCondition、非阻塞返回与 releaseBuffer 唤醒链

`dequeueBuffer()` 的等待可以落到 `waitForFreeSlotThenRelock()` 的条件变量路径上。

AOSP 源码里,Producer 线程先在 `BufferQueueProducer::waitForFreeSlotThenRelock()` 查找可用 slot。进入重试的原因主要有两类:

- **没有可用 slot**:`getFreeBufferLocked()` / `getFreeSlotLocked()` 都返回无效 slot,常见原因是已 dequeue 或已 acquire 的 buffer 达到上限。
- **队列积压过多**:`mQueue.size() > maxBufferCount`,producer 已经提交过多 buffer,consumer 还没有及时消费。

进入重试后,源码会先判断非阻塞模式。如果 `mCore->mDequeueBufferCannotBlock` 或 `mCore->mAsyncMode` 为 true,且 `acquiredCount <= mCore->mMaxAcquiredBufferCount`,函数直接返回 `WOULD_BLOCK`。这类场景里 RenderThread 可能拿到错误或跳过本帧,`mDequeueCondition.wait()` 上不一定出现长等待。分析 trace 时,不能只按"有没有 dequeue wait slice"判断 BufferQueue 背压,还要看返回状态、drop frame、Surface 类型和 producer 是否开启 async / non-blocking 配置。

只有需要阻塞时,路径才会进入 `mCore->mDequeueCondition.wait_for(...)` 或 `wait(...)`。唤醒来自 consumer 侧归还或取消 buffer:`BufferQueueConsumer::releaseBuffer()` 和 `BufferQueueProducer::cancelBuffer()` 都会触发 `mCore->mDequeueCondition.notify_all()`(或新版 buffer release channel 的等价通知)。等待中的 producer 线程被唤醒后,再次尝试获取 free slot。

**Jank 场景的 backpressure 链**:SurfaceFlinger / HWC 合成耗时超过刷新周期 → `releaseBuffer()` 延迟 → `mFreeBuffers` 为空 → Producer(RenderThread)在 `waitForFreeSlotThenRelock()` 中阻塞或收到 `WOULD_BLOCK` → 本帧无法按时开始渲染。这条链的根因在上游 SF / HWC,`dequeueBuffer()` 的等待或返回错误只是下游症状。

[已验证:AOSP main `BufferQueueProducer.cpp` 行 330-405、`BufferQueueConsumer.cpp` release 路径、`BufferQueueCore.h` 的 `mDequeueCondition` / `mDequeueBufferCannotBlock` 字段]

### Perfetto 里的 BufferQueue counters

除了 slice,Perfetto 里还应看 BufferQueue 相关 counter。不同版本和厂商的命名会有差异,通常可以先搜索 `BufferQueue`、`buffer_count`、`dequeued`、`queued` 这几类名字,再把 counter 变化和 RenderThread 的 `dequeueBuffer()` / `queueBuffer()` slice 放在同一段时间线里。

这些 counter 的价值在于把"等待"拆成数量变化:已分配 buffer 数是否上升、已 dequeue 数是否长期接近上限、queued 数是否持续堆积。只看一条长 slice,只能知道 producer 等了多久;配合 counter 才能判断是 slot 上限、consumer release 慢,还是非阻塞模式直接返回 `WOULD_BLOCK`。

### 异常 2:`queueBuffer()` 之后很久才被消费

另一类情况是 producer 已经把这一帧交出去了,但 consumer 过了很久才消费。BLAST 路径下,这时要重点看两件事:一是 `QueuedBuffer - ...BLAST#...` 到实际呈现之间隔了几帧,二是这段时间里有没有 geometry transaction 一起排队,等着同一个 `frameNumber` 被 apply。

如果 trace 里没有直接露出 `acquireBuffer` 这种 slice 名字,也不要硬猜。更稳妥的办法,是把 App 侧提交点、BLAST trace、SurfaceFlinger 合成周期和 FrameTimeline 的实际呈现摆到同一条时间线上。只要这些时间轴能对应上,哪怕设备厂商改了 slice 名字,我们照样能看清"是 queue 之后就堵住了",还是"consumer 早就拿到 buffer 了,只是后面的合成或显示又慢了一拍"。

## 与其他机制的关系

如果把一帧从输入到上屏拆开看,§2.4 Choreographer 决定这一帧什么时候启动,§2.5 MainThread 与 RenderThread 决定 DisplayList 和 GPU 命令怎样生成,§2.13 BufferQueue 决定生成好的内容怎样在 producer 和 consumer 之间流转,§2.16 Sync Fence 决定每一步交接什么时候真的生效,§2.6 SurfaceFlinger 决定这些 layer 何时被合成到屏幕上。

我们在性能分析里经常会遇到一种错觉,看见掉帧就先怀疑主线程太慢。BufferQueue 这一节帮我们拆掉的,就是这类错觉。主线程、RenderThread、SurfaceFlinger、HWC,谁都可能是瓶颈,但它们会通过同一条 buffer 流转链暴露出来。懂这条链,问题才有机会分层。

## 版本演进

这一节只保留已经能在 AOSP tag 上落下来的里程碑,不强写没有把握的版本表。

| 版本 | 已核实的变化 | 对理解 BufferQueue 的意义 |
|------|--------------|----------------------------|
| Android 4.1 (API 16) | `android-4.1.2_r1` 已存在 `frameworks/native/libs/gui/BufferQueue.cpp` | 说明 BufferQueue 从 Project Butter 时代起就已经是 native 图形管线的一部分,不存在"Android 7 才从 Java 迁到 native"这回事 |
| Android 11 (API 30) | `android-11.0.0_r48` 已存在 `BLASTBufferQueue.cpp`,`ViewRootImpl.java` 已创建 `new BLASTBufferQueue(...)` | BLAST 代码进入窗口提交流程,但常规 Activity 窗口是否默认使用要按具体分支和设备实现核对 |
| Android 12 (API 31) | 常规 Activity 窗口默认转向 BLAST 路径 | 读 trace 时应优先按 App 进程内 `BLASTBufferItemConsumer` + `SurfaceControl.Transaction::setBuffer()` 模型分析 |
| Android 14 (API 34) | `BLASTBufferQueue.cpp` 引入 `AsyncProducerListener` 包装 `IProducerListener` 回调 | producer dequeue 路径与 listener 执行解耦,降低同步回调造成锁等待的风险 |
| Android 16 (API 36) | vsyncId 关联入口在 `BLASTBufferQueue::acquireNextBufferLocked()` (Android 14 已存在),`queueBuffer` 本身不携带 vsyncId 名称 | 跨进程帧对齐追踪仍依赖 BLAST 层 + FrameTimeline,`queueBuffer` slice 不变 |

Android 12 之后还有持续演进,但 `frame rate override`、`maxBufferCount`、以及"无锁 MessageQueue 与 BLAST 协同优化"这些说法,必须分别拿 release note、commit 或源码落点来支撑,不能因为它们听起来合理就先写进版本表。当前素材还不足以把这些结论稳稳地归因到 BufferQueue 本身,所以这里先不展开。

[已验证:AOSP `android-4.1.2_r1`、`android-10.0.0_r47`、`android-11.0.0_r48`、`android-14.0.0_r1`、AOSP main `BufferQueueProducer.cpp` / `BLASTBufferQueue.cpp`]

## 常见问题与误区

### `queueBuffer()` 不是"每帧重新传一份 GraphicBuffer handle"

`queueBuffer()` 的高频动作是提交 slot、metadata 和 fence。同步新的 `GraphicBuffer` 句柄给对端,通常发生在首次分配、重分配、attach / detach 这些低频路径上。把这两类路径混成一件事,会直接把 BufferQueue 的成本模型看错。

### slot 状态变化,不等于这块内存已经能安全访问

slot 从 DEQUEUED 变成 QUEUED,不代表 consumer 立刻能读;slot 从 ACQUIRED 变回 FREE,也不代表 producer 这一刻就能重写。状态只告诉我们所有权大致在哪,"现在能不能碰"还要看 fence。

### BLAST 不只是"更快"

少一次远端交互当然有帮助,但 BLAST 最重要的价值是把 buffer 和 geometry transaction 绑定到同一个 `frameNumber`。如果只把它理解成一层加速器,就解释不了为什么它会直接影响窗口尺寸变化、crop 更新、多窗口切换这些场景的稳定性。

### 绝对毫秒阈值不能脱离设备基线使用

BufferQueue 的等待时间强依赖刷新率、Surface 类型、GPU / HWC 驱动、系统负载。脱离同机型基线去说"超过几毫秒就异常",这种结论很容易误导。更稳的做法,是先抓一条同场景正常 trace,再拿问题 trace 去做相对比较。

## 参考资料

- **AOSP 源码路径**
  - `frameworks/native/libs/gui/include/gui/IGraphicBufferProducer.h`
  - `frameworks/native/libs/gui/include/gui/IGraphicBufferConsumer.h`
  - `frameworks/native/libs/gui/include/gui/BufferSlot.h`
  - `frameworks/native/libs/gui/include/gui/BufferItem.h`
  - `frameworks/native/libs/gui/BufferQueue.cpp`
  - `frameworks/native/libs/gui/BufferQueueCore.cpp`
  - `frameworks/native/libs/gui/BLASTBufferQueue.cpp`
  - `frameworks/base/core/java/android/view/ViewRootImpl.java`

- **官方文档**
  - <https://source.android.com/docs/core/graphics/architecture>

- **交叉引用**
  - §2.1 Android 渲染架构全景
  - §2.4 Choreographer 与渲染流水线
  - §2.5 MainThread 与 RenderThread 协作
  - §2.6 SurfaceFlinger 与合成
  - §2.16 Sync Fence 框架与帧同步机制
  - §7.2 卡顿原因体系
