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
reviewed_date: "2026-06-12"
last_verified: '2026-07-25'
last_verified_against: 'AOSP android-17.0.0_r1 + kernel android17-6.18-2026-06_r6 + Android 4.1/11/12 historical tags + Writer rendering_pipelines S01/S02/S05/S06'
confidence: high
sources:
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/native/+/android-17.0.0_r1/libs/gui/include/gui/IGraphicBufferProducer.h
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/native/+/android-17.0.0_r1/libs/gui/include/gui/IGraphicBufferConsumer.h
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/native/+/android-17.0.0_r1/libs/gui/include/gui/BufferSlot.h
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/native/+/android-17.0.0_r1/libs/gui/include/gui/BufferItem.h
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/native/+/android-17.0.0_r1/libs/gui/include/gui/BufferQueueCore.h
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/native/+/android-17.0.0_r1/libs/gui/BufferQueueProducer.cpp
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/native/+/android-17.0.0_r1/libs/gui/BufferQueueConsumer.cpp
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/native/+/android-17.0.0_r1/libs/gui/BLASTBufferQueue.cpp
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/native/+/android-17.0.0_r1/libs/gui/BufferReleaseChannel.cpp
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/native/+/android-17.0.0_r1/libs/gui/Surface.cpp
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/native/+/android-17.0.0_r1/services/surfaceflinger/Layer.cpp
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/native/+/android-17.0.0_r1/services/surfaceflinger/SurfaceFlinger.cpp
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/native/+/android-17.0.0_r1/services/surfaceflinger/FrontEnd/RequestedLayerState.cpp
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/view/ViewRootImpl.java
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/view/Choreographer.java
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/window/SurfaceSyncGroup.java
- type: kernel
  path: https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/drivers/dma-buf/sync_file.c
- type: kernel
  path: https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/drivers/dma-buf/dma-fence.c
- type: material
  path: /Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Writer/rendering_pipelines/S01_rendering_types_overview.md
- type: material
  path: /Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Writer/rendering_pipelines/S02_aosp_standard_type.md
- type: material
  path: /Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Writer/rendering_pipelines/S05_mixed_rendering_type.md
- type: material
  path: /Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Writer/rendering_pipelines/S06_multi_window_type.md
- type: official
  path: https://source.android.com/docs/core/graphics/architecture
- type: official
  path: https://source.android.com/docs/core/graphics/unsignaled-buffer-latch
- type: official
  path: https://perfetto.dev/docs/data-sources/frametimeline
pipeline_stage: "ready-to-publish"
task6_state: "reviewed"
task9_state: "reviewed"
task2b_state: "fixed"
task9_result: "auto-fixed"
task2b_result: "fixed"
task9_reviewed_date: 2026-05-19
task9_reviewed_by: openclaw-task9
last_task9_at: "2026-06-11T12:39:21+08:00"
last_task9_audit: "2026-06-11"
last_task6_at: "2026-06-12T01:08:00+08:00"
last_task6_audit: "2026-06-12"
last_task6_audit_result: l1-light-edit
last_task6_audit_log: "logs/review/2026-05-21-09-audit.md"
review_round: 1
last_task9_review_log: logs/deep-review/2026-06-11-12-audit.md
task9_review_notes: "2026-06-11 Task9 闲时抽检：AUTO-FIX。修正 Perfetto android.monitor_contention 误用于 native BufferQueueCore::mMutex 的诊断口径；回到 Task6 复审。"
deepseek_cn_review_state: done
last_deepseek_cn_review_at: 2026-06-12
last_task9_autofix_at: "2026-06-11"
task6_result: "pass-light-edit"
task6_reviewed_date: "2026-06-12"
---

# 2.13 图形缓冲区管理 (BufferQueue)

## 先把问题放到正确的一段

Perfetto 中出现以下现象时，BufferQueue 是必须检查的一层：

- RenderThread 的 `dequeueBuffer()` 变长；
- App 已调用 `queueBuffer()`，SurfaceFlinger 迟迟没有采用新内容；
- 窗口尺寸、crop 或位置已经改变，内容仍像上一帧；
- 连续几帧越积越深，输入响应随之变迟；
- 某个图层的释放栅栏很晚，后续生产者拿不到合适的缓冲。

这些现象横跨“取缓冲、写缓冲、交缓冲、合成、释放”五个阶段。只看应用 CPU、GPU 忙碌状态或 SurfaceFlinger 任意一条轨道，都不足以判断责任位置。分析以 Android 17/API 37、`android-17.0.0_r1` 为平台锚点；fence 的内核语义固定到 `android17-6.18-2026-06_r6`。

## 一组槽位如何代替整帧复制

BufferQueue 连接一个 Producer 和一个 Consumer。Producer 写入内容，Consumer 读取内容；`BufferQueueCore` 维护槽位、各槽位绑定的 `GraphicBuffer`、队列元数据和同步对象。

`GraphicBuffer` 底层通常关联可跨进程、跨设备共享的 dma-buf。双方传递槽位、buffer 引用、时间戳、crop、transform、dataspace 和栅栏，无需在每次交接时复制整帧像素。这里的“零拷贝”只描述 BufferQueue 的交接方式。TextureView 回流、截图、格式转换或 SurfaceFlinger 的 client composition 仍可能增加采样和输出缓冲。

Android 的可见 Surface 也不都采用同一种拓扑：

| 场景 | 常见 Producer | BufferQueue 消费者所在处 | 最终去向 |
|---|---|---|---|
| 标准 App Window | HWUI RenderThread | App 进程内的 BLAST | `SurfaceControl.Transaction` 进入 SF |
| `SurfaceView`/视频/ Camera 输出 | 应用、codec HAL | 取决于该 Surface 的创建路径 | 独立 SF 图层或中间消费者 |
| `TextureView` 输入 | 外部 Producer | App 进程中的 `SurfaceTexture` | 被宿主 HWUI 再采样 |
| Vulkan swapchain | Vulkan queue | Android WSI/BufferQueue 路径 | 对应 Surface 的消费链 |

因此，“App 是 Producer、SF 是 Consumer”只适用于一部分历史或独立 Surface 模型。Android 17 的标准 App Window 要按应用内 BLAST 消费者分析。

## Producer 的三个主调用

`IGraphicBufferProducer` 把选 slot、取得缓冲引用和提交内容分成不同操作。以下接口片段用于说明职责边界。

```cpp
// android-17.0.0_r1
virtual status_t requestBuffer(int slot, sp<GraphicBuffer>* buf) = 0;

virtual status_t dequeueBuffer(
        int* slot, sp<Fence>* fence,
        uint32_t width, uint32_t height,
        PixelFormat format, uint64_t usage,
        uint64_t* outBufferAge,
        FrameEventHistoryDelta* outTimestamps) = 0;

virtual status_t queueBuffer(
        int slot, const QueueBufferInput& input,
        QueueBufferOutput* output) = 0;
```

三步分别回答“用哪个槽位”“这个槽位绑定哪块内存”“本帧何时可供 Consumer 读取”。

### 1. `dequeueBuffer()`：选出满足约束的槽位

`BufferQueueProducer::dequeueBuffer()` 优先从 `mFreeBuffers` 选择已经分配内存的 FREE slot；没有合适对象且允许分配时，再从 `mFreeSlots` 选一个空槽位。返回值包括槽位编号和上一位所有者留下的栅栏。

这里有两个容易混淆的边界：

- FREE 表示槽位已回到 BufferQueue 的可选集合；
- 返回 fence signal 后，Producer 才能安全覆盖缓冲的旧内容。

`BufferQueueProducer` 可以先返回槽位和栅栏。EGL、Vulkan、HWUI 或其他 Producer 负责等待栅栏，或把栅栏导入后续 GPU 工作。一次高层 `dequeue` 时长可能同时包含“等 free slot”和图形后端处理栅栏的时间，分析调用栈时要把两者分开。

### 2. `requestBuffer()`：按需取得新映射

首次分配、尺寸/格式/usage 变化、Consumer 重新附着缓冲等情况，会让 `dequeueBuffer()` 返回 `BUFFER_NEEDS_REALLOCATION`。`Surface::dequeueBuffer()` 收到该标志，或者本地槽位尚未缓存 `GraphicBuffer` 时，才调用 `requestBuffer()`。

稳定渲染时，Producer 已缓存槽位到 `GraphicBuffer` 的映射。每帧都传一份完整 native handle 会浪费 Binder 和句柄映射成本，AOSP 的槽位设计用于避免这项开销。

### 3. `queueBuffer()`：提交槽位、元数据和生产完成栅栏

Producer 生成内容后调用 `queueBuffer()`。`QueueBufferInput` 携带生产完成栅栏、时间戳、crop、transform、dataspace、surface damage 等信息。该栅栏到达下游后充当获取栅栏：消费者读取像素前必须遵守它。

`queueBuffer()` 返回只说明 CPU 侧提交完成。此后还可能发生：

- GPU 继续执行写入命令；
- App 内 BLAST 尚未获取 `BufferItem`；
- buffer transaction 尚未到达 SurfaceFlinger；
- 本轮 SF 锁存没有采用该缓冲；
- HWC 尚未显示。

## slot 状态与栅栏要分开读

Android 17 的 `BufferState` 使用计数器和共享标志表达状态。以下片段解释源码为何用 `isFree()` 等方法判断。

```cpp
// frameworks/native/libs/gui/include/gui/BufferSlot.h
struct BufferState {
    uint32_t mDequeueCount;
    uint32_t mQueueCount;
    uint32_t mAcquireCount;
    bool mShared;

    bool isFree() const {
        return !isAcquired() && !isDequeued() && !isQueued();
    }
    bool isDequeued() const { return mDequeueCount > 0; }
    bool isQueued() const { return mQueueCount > 0; }
    bool isAcquired() const { return mAcquireCount > 0; }
    bool isShared() const { return mShared; }
};
```

普通单 Producer、单 Consumer 路径通常呈现以下顺序：

```text
FREE
  -> dequeueBuffer()
DEQUEUED
  -> queueBuffer()
QUEUED
  -> acquireBuffer()
ACQUIRED
  -> releaseBuffer(releaseFence)
FREE + releaseFence
```

shared buffer mode 允许 `mShared` 与出队、queued、acquired 计数并存，也允许相关计数大于 1。诊断当前源码时，应使用 `isFree()`、`isDequeued()`、`isQueued()`、`isAcquired()` 和 `isShared()`，不能套用旧版互斥枚举。

状态和访问权限的对应关系如下：

| 状态/动作 | 所有权含义 | fence 约束 |
|---|---|---|
| FREE | BufferQueue 可把槽位交给 Producer | slot 仍可能保存上一轮 release fence |
| DEQUEUED | Producer 已取得槽位 | 写入前等待 `dequeueBuffer()` 返回的栅栏 |
| QUEUED | Producer 已提交，等待 Consumer | Consumer 读取前等待生产完成栅栏 |
| ACQUIRED | Consumer 已取得 `BufferItem` | Consumer/HWC/RenderEngine 继续遵守 acquire fence |
| `releaseBuffer()` | Consumer 归还槽位 | release fence 表示何时可安全复用旧内容 |

`releaseBuffer()` 会把槽位放回 FREE 集合并保存 release fence，无需先等待 fence signal。下一次 Producer 可能马上取到该槽位，同时取得尚未 signal 的栅栏。因此，“已经 FREE”和“已经可写”是两个时间点。

## buffer 数量没有固定答案

“三缓冲”适合描述常见现象，不适合作为 Android 17 的固定配置。`BufferQueueCore::getMaxBufferCountLocked()` 由下式约束：

```text
maxBufferCount =
    maxAcquiredBufferCount
  + maxDequeuedBufferCount
  + (asyncMode || dequeueBufferCannotBlock ? 1 : 0)

最终结果还受 mMaxBufferCount 上限限制
```

Android 17 的 `BLASTBufferQueue::initialize()` 给 Producer 设置安全默认值 `setMaxDequeuedBufferCount(2)`，但 Producer 可以按能力覆盖。BLAST 还会向 SurfaceComposer 服务查询最大刷新率下建议的 acquired 数，再设置内部 `BLASTBufferItemConsumer` 的 `maxAcquiredBufferCount`。SurfaceFlinger 根据 present latency 与刷新周期计算建议值，并受 `min_acquired_buffers`/`max_acquired_buffers` 属性约束。

SF 的释放信息还会携带当前刷新率对应的 acquired 数。对于 EGL Producer，BLAST 可能暂存一部分已收到释放信息的缓冲，以适应当前刷新率低于设备最大刷新率的情况。可用深度因此取决于：

- 最大出队数与最大获取数；
- 异步/非阻塞配置；
- DEQUEUED、QUEUED、ACQUIRED 的实时数量；
- BLAST 的 pending release；
- buffer 是否需要重分配；
- release fence 的完成时间。

看到三个缓冲时，可以称其为三缓冲工作形态；不能由此反推所有 Surface 都固定分配三块。

## `dequeueBuffer()` 等待的精确条件

`waitForFreeSlotThenRelock()` 先统计当前 dequeued/acquired 数，再选择 free buffer 或 free slot。Android 17 需要区分三种结果：

1. 历史标志 `mBufferHasBeenQueued` 已为 true，且 `dequeuedCount >= mMaxDequeuedBufferCount`：直接返回 `INVALID_OPERATION`。它表示 Producer 试图超过出队上限，不要求当前 `mQueue` 非空，也不会等待 Consumer release。
2. 没有满足条件的 free slot，或 `mQueue.size() > maxBufferCount`：进入重试。
3. 重试时处于 async/non-blocking 模式，且 acquired 数未超过允许的临时额外值：返回 `WOULD_BLOCK`；其余情况等待缓冲状态变化，超时配置生效时也可能返回 `TIMED_OUT`。

下面的结构示意用于记住分支，不代表完整源码。

```text
waitForFreeSlotThenRelock()
  count DEQUEUED / ACQUIRED

  if max DEQUEUED already reached
      return INVALID_OPERATION

  find FREE buffer or allocatable FREE slot

  if none found or queue is over its limit
      if async / non-blocking conditions match
          return WOULD_BLOCK
      waitForBufferRelease()
      retry
```

把 `INVALID_OPERATION`、`WOULD_BLOCK` 和长时间等待混成一种“背压”，会得到错误结论。需要同时记录返回码、Surface 模式、slot 数量和 Consumer 进度。

## 通用 BufferQueue 与 Android 17 BLAST 的等待方式

### 通用路径：条件变量

`BufferQueueCore::mMutex` 保护槽位、free lists、FIFO、计数和大部分队列配置。Producer 与 Consumer 操作共享 core 时都会短暂持有这把锁。BufferQueue 还有 callback lock、allocation condition、BLAST 自身 mutex 等其他锁，因此 `mCore->mMutex` 不能代表整条图形管线的唯一锁。

通用 `BufferQueueProducer::waitForBufferRelease()` 使用 `mDequeueCondition.wait()`/`wait_for()`。等待期间 `std::unique_lock` 会释放 `mCore->mMutex`，Consumer 才能进入 `acquireBuffer()` 或 `releaseBuffer()` 改变状态。`releaseBuffer()`、`cancelBuffer()`、队列消费及部分配置变化都会调用 `notifyBufferReleased()`，默认实现再调用 `notify_all()`。

listener callback 也会在 core lock 之外执行。Perfetto 中一条较长的 `dequeueBuffer` slice，不能直接解释为 `mCore->mMutex` 全程被占用。

### 标准 App Window：`BufferReleaseChannel`

Android 17 的 BLAST 创建 `BBQBufferQueueCore` 和 `BBQBufferQueueProducer`。它们仍复用通用槽位状态机，但等待释放时走了专门路径：

```text
BBQBufferQueueProducer::waitForBufferRelease()
  清除待处理的中断
  unlock mCore->mMutex
  BufferReleaseReader::readBlocking()
    epoll waits for:
      - SF buffer release message
      - local interrupt
  BLASTBufferQueue::releaseBufferCallback()
  BLASTBufferItemConsumer::releaseBuffer(releaseFence)
  reacquire mCore->mMutex and retry
```

BLAST 初始化时创建 `BufferReleaseChannel` 两端，并通过独立的 `SurfaceControl.Transaction::setBufferReleaseChannel()` 把 Producer endpoint 交给 SF。`Layer::callReleaseBufferCallback()` 将 `ReleaseCallbackId`、release fence 和当前刷新率的 acquired 数写回通道；transaction 的 release callback 入口仍然存在，BLAST 会对重复的释放信息去重。channel 传回“哪块缓冲被释放以及对应栅栏”，后续仍可能需要等待栅栏。

`BBQBufferQueueCore::notifyBufferReleased()` 的当前实现会中断阻塞读取，让等待线程重新检查本地 free slot。标准 App Window 的长 dequeue 不能只按 `mDequeueCondition` 分析。

正常归还主要来自 SF 的 release callback / release channel。BLAST 注册的 transaction-completed callback 还有一条兜底：如果较新的事务已越过仍留在 `mSubmitted` 中的旧缓冲，它会以 `fakeRelease=true` 补发 stale-buffer release，再由同一个 `releaseBufferCallbackLocked()` 去重和归还。这个“fake”只处理漏掉正常释放的旧提交，不能据此把每次缓冲回收都归到 transaction-completed callback。

## BLAST 如何把缓冲变成事务

Android 17 的 `ViewRootImpl.updateBlastSurfaceIfNeeded()` 在应用进程创建或更新 `BLASTBufferQueue`，再把它生成的 `Surface` 交给 HWUI。BLAST 内部包含 Producer、`BufferQueueCore`、`BufferQueueConsumer` 和 `BLASTBufferItemConsumer`。

以下调用骨架用于区分应用侧入队、BLAST 获取和 SF buffer transaction。

```text
RenderThread / Producer
  Surface::dequeueBuffer()
  绘制或提交 GPU 工作
  Surface::queueBuffer(producerCompletionFence)

BLASTBufferQueue::onFrameAvailable()
  acquireNextBufferLocked()
    BLASTBufferItemConsumer::acquireBuffer()
    Transaction::setBuffer(
        surfaceControl,
        graphicBuffer,
        acquireFence,
        frameNumber,
        producerId,
        releaseBufferCallback,
        dequeueTime)
    设置数据空间 / HDR 元数据 / 受损区域 / 裁剪 / 变换
    merge pending transactions up to frameNumber
    Transaction::apply()

SurfaceFlinger
  接收待处理的缓冲事务
  评估就绪状态并为显示帧选择缓冲
  合成 / 显示
  向 BLAST 返回各缓冲的释放信息
```

`queueBuffer()` 的 frame-available callback 先到应用内 BLAST；BLAST acquire `BufferItem` 后，才调用 `Transaction::setBuffer()` 把 buffer update 发送给 SF。本地 Consumer 直接通知 SF acquire buffer”。

### geometry 同步能保证到哪里

`mergeWithNextTransaction(transaction, frameNumber)` 允许窗口尺寸、crop、position 或其他受控 `SurfaceControl` 状态按帧号与目标缓冲合并。`syncNextTransaction()`、transition sync 和 `SurfaceSyncGroup` 还能协调参与相同同步协议的对象。

这些机制只覆盖已经加入事务或 sync group 的状态与缓冲。外部 codec、Camera、另一个进程的独立帧循环、未加入同步组的 Surface，不会因为同屏显示就自动采用同一业务帧。acquire fence 未满足时，目标更新也可能被推迟。

BLAST 提供明确的事务边界，不能保证所有窗口始终使用同一帧。

### latch 与读取是两个同步边界

Android 13 起，`AutoSingleLayer` 允许 SurfaceFlinger 在严格条件下先 latch 尚未 signal 的缓冲。Android 17 的 `transactionReadyBufferCheck()` 会检查 `shouldLatchUnsignaled()`；`AutoSingleLayer` 路径要求本次只更新一个图层、位于事务队首、不使用提前 VSync 配置，并且通过 `RequestedLayerState::isSimpleBufferUpdate()`。包含 geometry change 或 sync transaction 的更新不符合该模型。

满足这些条件，只表示 transaction readiness 阶段可以先采纳缓冲状态。RenderEngine 或 HWC 开始读取像素前仍需遵守 acquire fence。因此，trace 中“buffer 已锁存”和“Producer 写入已完成”是两个时间点；入队时栅栏尚未 signal，也不能直接断言本轮一定无法锁存。

## 三类栅栏的方向

这里讨论 BufferQueue 交接，§2.16 继续解释 sync_file 与 dma-fence。排障时至少要标明以下三类对象：

| 名称 | 粒度 | 产生方与流向 | 能证明什么 |
|---|---|---|---|
| Producer completion / acquire fence | 每块输入缓冲 | Producer 随 `queueBuffer()` 提交，交给 Consumer/SF/HWC | 写入何时完成、下游何时可读 |
| layer release fence | 每个被消费的 layer buffer | HWC/RenderEngine 经 SF 回到 BLAST/BufferQueue | 下游何时不再读、何时可复用 |
| display present fence | 每个 display frame | HWC 显示后返回给 SF | 本轮显示到达 Android 显示栈可观察边界 |

显示栅栏不由某个应用缓冲独享；释放栅栏也不等同于显示栅栏。客户端合成时，RenderEngine 会消费输入图层栅栏，并为客户端目标产生自己的获取栅栏。SF 还可能按图层使用方式合并或选择释放栅栏。

进入内核后，native fence fd 由 `sync_file` 暴露，底层依赖 `dma_fence` 的信号、callback 与等待。公共内核只能说明通用同步机制，无法解释厂商 GPU、DPU 或 codec 为何在某台设备上晚 signal；这部分需要设备驱动、vendor trace 和调用现场。

## Android 17 的 buffer-stuffing recovery

标准 App Window 因没有 free buffer 而等待时，`BBQBufferQueueProducer::waitForBufferRelease()` 会统计阻塞时长。`ViewRootImpl` 通过 `ThreadedRenderer` 把回调接到 `Choreographer.onWaitForBufferRelease()`。

等待超过上一帧间隔的一半后，`Choreographer` 标记堆积状态。随后的 `doFrame()` 可以：

- 主动推迟一个 VSync，给队列释放空间；
- 恢复期间给动画 frame time 加一个负偏移；
- 检测到空闲后结束恢复。

`buffer_stuffing_multi_recovery` 控制同一段动画能否多次触发恢复；`buffer_stuffing_recovery_threshold` 启用时，累计主动延迟受 `MAX_BUFFER_STUFFING_DELAY_NS = 100 ms` 限制。这些是可变 aconfig flag，设备取值必须从配置或 trace 确认。

这套策略在队列已经过深时用少产一帧换取更低的后续延迟。Perfetto 中出现 `Buffer stuffing recovery`、`buffer stuffed` 或 `Negative offset`，说明系统正在恢复排队状态，不能把那次主动延迟直接归因于 CPU 执行过慢。

## 在 Perfetto 中建立证据链

绝对毫秒阈值会随刷新率、Surface 类型、GPU/HWC、热状态和跟踪开销变化。应先采集同机型、同刷新率、同场景的顺畅基线，再比较异常段。

### 三个时间点需要分开

对标准 App Window，至少分开：

1. App `queueBuffer()` 返回；
2. 应用内 BLAST 获取缓冲并应用缓冲事务；
3. SF 收到待处理缓冲事务，随后锁存、选择并显示。

Android 17 中常见的观测对象包括：

| 观测项 | 所在处 | 解读 |
|---|---|---|
| `dequeueBuffer - <surface>`/`queueBuffer` | App Producer | Producer 取出或提交槽位 |
| `QueuedBuffer - <name>BLAST#<id>` | App 内 BLAST counter | BLAST 可用、acquired、pending release 的组合计数 |
| `BufferTX - <layerName>` | SurfaceFlinger | SF 服务端的待处理缓冲事务数 |
| FrameTimeline `SurfaceFrame` | App/目标 Surface | expected/actual 与卡顿分类 |
| FrameTimeline `DisplayFrame` | SurfaceFlinger/display | 整屏 expected/actual present |
| release/present fence | SF/HWC/display | buffer 回收和显示完成边界 |

`BufferTX` 增加只说明 SF 记录了一笔 pending buffer update。它没有直接给出 acquire fence 是否就绪、sync barrier 是否满足或 display 是否已使用新缓冲。计数在锁存或丢弃后下降，也不能单独区分两种结果。

BLAST 在 `acquireNextBufferLocked()` 中按帧号查找待处理的 pending FrameTimeline info，并调用 `Transaction::setFrameTimelineInfo()`；相关 trace 会带帧号和 VSync ID。`queueBuffer` slice 本身没有 VSync ID 后缀。对齐时应结合 BLAST transaction、FrameTimeline token、layer/buffer id 和相邻 SF 显示帧判断。

### `dequeueBuffer()` 变长

按以下顺序检查：

1. 返回码是成功、`INVALID_OPERATION`、`WOULD_BLOCK` 还是 `TIMED_OUT`；
2. 当前 Surface 是应用窗口 BLAST、SurfaceView、SurfaceTexture、codec 还是 Vulkan swapchain；
3. 最大出队/获取数、异步模式和已分配缓冲数；
4. `QueuedBuffer` 与 `BufferTX` 是否持续堆高；
5. SF 是否迟迟未选用或释放旧缓冲；
6. release fence 是否晚到，返回槽位后又在哪里等待栅栏；
7. 是否出现缓冲堆积恢复。

单个 Producer 长 dequeue 通常只说明对应队列缺少可用缓冲。多窗口中的其他应用有独立队列和主线程，不能直接推断所有窗口都被同一个锁阻塞。

### `queueBuffer()` 后很久才显示

沿下游逐段确认：

1. BLAST 是否及时 acquire；
2. SF 的 `BufferTX` 何时增加；
3. 事务是否受同步组、屏障、期望显示时间或获取栅栏影响；
4. 本轮 display frame 采用新缓冲还是沿用旧内容；
5. HWC 策略是否发生 DEVICE/CLIENT 切换；
6. present fence 与 FrameTimeline 实际显示时间位于哪里。

Producer 完成早而 `BufferTX` 晚，优先查应用内 BLAST 与事务；`BufferTX` 已到而锁存晚，查 transaction readiness 和栅栏；latch 已完成而显示晚，继续查 CompositionEngine、RenderEngine、HWC 和 display。

### native 锁竞争

`android.monitor_contention` 面向 Java/Kotlin monitor，不能证明 `BufferQueueCore::mMutex` 发生争用。native BufferQueue 需要结合函数切片、thread state、futex/scheduler blocked reason、调用栈与 Consumer 时序。由于等待会释放 core mutex，一条 sleeping `dequeueBuffer` 也不能自动归类为 mutex contention。

## 版本演进

| 版本 | 可由标签确认的变化 | 排障模型 |
|---|---|---|
| Android 4.1/API 16 | `android-4.1.2_r1` 已包含原生 `BufferQueue.cpp` | BufferQueue 是 Project Butter 时代已有的图形基础组件 |
| Android 11 / API 30 | `android-11.0.0_r48` 已包含 `BLASTBufferQueue.cpp`，`ViewRootImpl` 已有 BLAST 创建路径 | 可确认 BLAST 已进入窗口代码，不能由文件存在推断所有设备都默认采用 |
| Android 12/API 31 | BLAST 与 FrameTimeline 构成现代 App Window 分析基线 | 分开 App queue、BLAST transaction、SF `BufferTX` 和 display present |
| Android 13—16/API 33—36 | 主体仍沿 BLAST/SurfaceControl 事务演进，公开同步与事务 API 继续增加 | 版本差异应落到具体 API、flag、Surface 类型和设备实现 |
| Android 17/API 37 | 当前实现包含 `BufferReleaseChannel`、动态 acquired-count反馈、buffer-stuffing recovery 与现行 FrontEnd/SF 观测 | 等待路径不能只套经典 `mDequeueCondition`，队列深度也不能写成固定三缓冲 |

版本表只陈述能从固定标签或官方文档确认的内容。Android 17 源码中存在某个实现，不足以证明它从 Android 17 首次引入；判断引入版本时，还需比较历史标签和提交。

## 常见误判

### 把 FREE 当成栅栏已 signal

`releaseBuffer()` 可以先把槽位归还 FREE，再把尚未 signal 的 release fence 交给 Producer。FREE 描述所有权，fence 描述访问时序。

### 把 `queueBuffer()` 当成已经上屏

它只完成生产者提交。BLAST 获取、SF 事务、锁存、合成和显示仍在后面。

### 把三缓冲当成常量

Android 17 的 max dequeued、max acquired、async extra、SF 刷新率反馈和 pending release 共同决定可用深度。

### 把 BLAST 当成纯性能加速器

BLAST 的职责是把缓冲、frame number、fence 和受控图层状态放入明确的事务边界。它无法替未参与同步的外部 Producer 保证业务帧一致。

### 由一条切片判断责任方

长 `dequeueBuffer` 可能在等待 free slot，也可能在更高层处理 release fence；`BufferTX` 高可能来自 pending、readiness 或 drop；present 晚还可能发生在 HWC/display。责任结论需要相邻阶段互相印证。

## 参考资料

- Android 17 AOSP：
  - [`IGraphicBufferProducer.h`](https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/libs/gui/include/gui/IGraphicBufferProducer.h)
  - [`BufferSlot.h`](https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/libs/gui/include/gui/BufferSlot.h)
  - [`BufferQueueProducer.cpp`](https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/libs/gui/BufferQueueProducer.cpp)
  - [`BufferQueueConsumer.cpp`](https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/libs/gui/BufferQueueConsumer.cpp)
  - [`BLASTBufferQueue.cpp`](https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/libs/gui/BLASTBufferQueue.cpp)
  - [`BufferReleaseChannel.cpp`](https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/libs/gui/BufferReleaseChannel.cpp)
  - [`Surface.cpp`](https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/libs/gui/Surface.cpp)
  - [`Layer.cpp`](https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/services/surfaceflinger/Layer.cpp)
  - [`SurfaceFlinger.cpp`](https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/services/surfaceflinger/SurfaceFlinger.cpp)
  - [`RequestedLayerState.cpp`](https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/services/surfaceflinger/FrontEnd/RequestedLayerState.cpp)
  - [`ViewRootImpl.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/view/ViewRootImpl.java)
  - [`Choreographer.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/view/Choreographer.java)
- Kernel `android17-6.18-2026-06_r6`：
  - [`sync_file.c`](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/drivers/dma-buf/sync_file.c)
  - [`dma-fence.c`](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/drivers/dma-buf/dma-fence.c)
  - [`dma-buf.c`](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/drivers/dma-buf/dma-buf.c)
- 官方文档：
  - [Graphics architecture](https://source.android.com/docs/core/graphics/architecture)
  - [Unsignaled buffer latching](https://source.android.com/docs/core/graphics/unsignaled-buffer-latch)
  - [Perfetto FrameTimeline](https://perfetto.dev/docs/data-sources/frametimeline)
- 交叉阅读：§2.1、§2.4、§2.5、§2.6、§2.16、§7.2。
