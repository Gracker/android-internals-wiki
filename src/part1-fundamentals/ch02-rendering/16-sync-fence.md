---
title: Sync Fence 框架与帧同步机制
chapter: 2.16
section: 2.16
applicable_versions: Android 7 (API 24) - Android 17 (API 37); earlier Android
  sync terminology retained only as version history
last_verified: 2026-07-25
last_verified_against: Android 17 / API 37 / android-17.0.0_r1; android17-6.18-2026-06_r6;
  Writer rendering_pipelines S01 diagram/S08/S11/S12
confidence: high
drafted_date: 2026-04-05
drafted_by: openclaw-task2a
sources:
- type: official
  path: https://source.android.com/docs/core/graphics/sync
- type: official
  path: https://source.android.com/docs/core/graphics/architecture
- type: official
  path: https://github.com/KhronosGroup/Vulkan-Docs/blob/v1.4.335/chapters/synchronization.adoc
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/native/+/android-17.0.0_r1/libs/ui/Fence.cpp
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/native/+/android-17.0.0_r1/libs/ui/FenceTime.cpp
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/native/+/android-17.0.0_r1/libs/gui/Surface.cpp
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/native/+/android-17.0.0_r1/libs/gui/BufferQueueProducer.cpp
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/native/+/android-17.0.0_r1/libs/gui/BufferQueueConsumer.cpp
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/native/+/android-17.0.0_r1/libs/gui/BLASTBufferQueue.cpp
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/native/+/android-17.0.0_r1/libs/gui/BufferReleaseChannel.cpp
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/native/+/android-17.0.0_r1/services/surfaceflinger/Layer.cpp
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/native/+/android-17.0.0_r1/services/surfaceflinger/DisplayHardware/HWC2.h
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/native/+/android-17.0.0_r1/services/surfaceflinger/DisplayHardware/HWComposer.cpp
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/libs/hwui/pipeline/skia/SkiaOpenGLPipeline.cpp
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/libs/hwui/pipeline/skia/SkiaVulkanPipeline.cpp
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/libs/hwui/renderthread/EglManager.cpp
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/libs/hwui/renderthread/VulkanManager.cpp
- type: aosp
  path: https://android.googlesource.com/platform/system/core/+/android-8.1.0_r81/libsync/sync.c
- type: kernel
  path: https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/drivers/dma-buf/dma-fence.c
- type: kernel
  path: https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/drivers/dma-buf/sync_file.c
- type: kernel
  path: https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/drivers/dma-buf/sw_sync.c
- type: kernel
  path: https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/include/trace/events/dma_fence.h
- type: material
  path: /Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Writer/rendering_pipelines/diagrams/S01_baseline_12_anchor_pipeline/source.md
- type: material
  path: /Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Writer/rendering_pipelines/S08_native_graphics_type.md
- type: material
  path: /Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Writer/rendering_pipelines/S11_camera_type.md
- type: material
  path: /Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Writer/rendering_pipelines/S12_video_overlay_hwc_type.md
tags: [sync-fence, fence, hwui, rendering, synchronization, timeline]
related_chapters: ["2.4", "2.5", "2.6", "2.13", "2.15"]
task2b_state: fixed
task9_result: pass-tech-review
task2b_result: fixed
task9_reviewed_date: 2026-07-03
task9_reviewed_by: openclaw-task9
last_task9_at: 2026-07-03T12:32:56+08:00
last_task2b_at: 2026-05-05T23:51:15+08:00
repaired_date: 2026-04-26
repaired_by: openclaw-task2b
task9_review_notes: "2026-05-05 task9 deep-review: needs-rework。2.16 P0 1；12.1 P1 1；P2 3 随队列记录。 | 2026-05-24 Task9 闲时抽检：needs-rework。P1 1：Vulkan Timeline Semaphore 不能直接导出 Android sync fd / Perfetto fence track 只能观察 native fence；P2 1：dequeueBuffer fence 命名需改为 dequeue/release fence。 | 2026-07-03 Task9 idle audit AUTO-FIX: P1 1；将 Sync Fence 主线源码验证从 android-16.0.0_r1 更新到 android-17.0.0_r1，复核 Fence::merge/libsync/HWC2/HWUI GL+Vulkan release fence/Binary Semaphore sync fd 边界；回到 Task6 复审。详见 logs/deep-review/2026-07-03-09-audit.md。 | 2026-07-03 12 Task9 deep-review: pass-tech-review。Task6 复审后复核 android-17.0.0_r1 Fence.cpp/libsync/HWUI GL+Vulkan release fence/Binary Semaphore 边界；P0 0 / P1 0 / P2 0；queue 无 pending，自动晋升 finalized。"
status: finalized
pipeline_stage: ready-to-publish
task6_state: reviewed
task6_result: pass-light-edit
task9_state: reviewed
reviewed_by: openclaw-task6
reviewed_date: 2026-07-03
task6_reviewed_date: 2026-05-06
last_task6_at: 2026-07-03T12:13:55+08:00
last_task6_audit: 2026-07-03
review_notes: "2026-04-27 task9 deep-review: pass-tech-review。无 P0/P1；Task6 已通过且 queue 无 pending，自动晋升 finalized。P2 2 写入 suggestions。 | 2026-05-05 Task6 23:26：revisiting 写作复审，清理 fence 章节 L1/L2 表达（填充词、否定纠正式、参考资料重复块）；写作层通过。Task9 已有 P0 queue pending，等待 Task2B。 | 2026-05-06 Task6 01:05：Task2B 修复后写作复审，清理 L1/L2 表达与格式；无新增 L3/L4 回炉项，送 Task9 复审。 | 2026-05-06 Task9 01:28：复审通过。复核 HWC2 fence 语义、libsync merge、HWUI GL/Vulkan release fence、Timeline Semaphore 边界；无新增 P0/P1；Task6 已通过且 queue 无 pending，自动晋升 finalized。 | 2026-05-24 Task9 deep-review: pass-tech-review。P0 0 / P1 0 / P2 1；Vulkan native fence 边界已改为 Binary Semaphore → sync fd 桥接，dequeue fence 命名已修正；仅留 Binary Semaphore reset 语义 P2 建议；queue 无 pending，Task6 已通过，自动晋升 finalized。"
last_task9_audit: 2026-07-03
last_task9_review_log: logs/deep-review/2026-07-03-12-deep-review.md
deepseek_cn_review_state: done
last_deepseek_cn_review_at: 2026-07-03
last_task9_audit_at: 2026-07-03T09:45:13+08:00
last_task9_audit_log: logs/deep-review/2026-07-03-09-audit.md
last_task9_autofix_at: 2026-07-03
updated_by: openclaw-task9
updated_date: 2026-07-03
task9_p0_issues: 0
task9_p1_issues: 0
task9_p2_issues: 0
p0: 0
p1: 0
p2: 0
---

# 2.16 Sync Fence 框架与帧同步机制

Fence 是异步工作的完成凭证。它不保存像素、不拥有 BufferQueue slot，也不让两个线程自动互斥；它只表达一条依赖：“在这项工作完成前，后续访问不能越过这个点。”

Android 图形链路需要栅栏，因为 CPU、GPU、Camera ISP、codec、SurfaceFlinger、HWC 和 display controller 可以并行工作。Producer 可以先把缓冲与栅栏交给 consumer，再让 GPU 继续写；consumer 也可以先安排显示，再返回一条稍后才 signal 的 release fence。这样既避免 CPU 在每个阶段同步阻塞，也避免 consumer 读到尚未写完的像素。

分析以 Android 17/API 37、`android-17.0.0_r1` 为平台锚点，kernel 侧以 `android17-6.18-2026-06_r6` 为锚点。栅栏名称由观察边界决定，同一个同步对象从 producer 传到 consumer 后，角色名称可能变化。

## 1. Fence 描述完成，不描述开始

一个 fence 通常经历三种状态：

- pending：异步工作尚未完成；
- signaled：工作已完成，依赖可以继续；
- error：工作以错误结束，等待方必须按接口约定处理。

signal 是单向状态变化。已经 signal 的栅栏不会回到 pending。多个帧需要多个完成点；驱动可以在同一 execution context 中用递增 seqno 表示顺序，但用户空间拿到的 sync_file 文件描述符仍代表一个固定完成条件。

`-1` 在 Android native fence API 中通常表示 `NO_FENCE`，即没有待等待的依赖。它不是“未知栅栏”或错误 fd。具体函数仍要以其参数约定为准。

## 2. Android 17 的三层实现

### 2.1 Kernel：dma-fence

`struct dma_fence` 是内核中的跨驱动完成原语。Android 17 内核的 `drivers/dma-buf/dma-fence.c` 定义了 context、seqno、signal、error、timestamp、callback 与等待语义。

同一 context 中的栅栏按 seqno 完全有序；不同 context 可能来自独立 GPU engine、display pipeline 或 codec queue，不能只比较 seqno 大小。驱动还必须保证栅栏在合理时间内结束，并提供 hang recovery 或强制完成策略，防止等待永久卡住内存管理和其他设备。

### 2.2 Kernel 到 userspace：sync_file

`sync_file` 把一个 `dma_fence` 或栅栏集合包装成匿名文件，用户空间通过 fd 传递、poll、wait 和查询。`drivers/dma-buf/sync_file.c` 的主要职责包括：

- `sync_file_create()`：持有栅栏引用并建立文件；
- `sync_file_get_fence()`：从 fd 取得栅栏引用；
- `SYNC_IOC_MERGE`：建立新的合并 sync_file；
- `SYNC_IOC_FILE_INFO`：返回 sync_file 名称、整体状态，以及内部栅栏的驱动、timeline、状态与 signal timestamp；
- poll callback：fence signal 后唤醒等待者。

关闭 sync_file 文件描述符会释放该文件持有的栅栏引用。它不会自动释放 GraphicBuffer，也不会改变 BufferQueue 槽位状态；buffer 和栅栏是两类对象。

### 2.3 Framework：`android::Fence`

`frameworks/native/libs/ui/Fence.cpp` 用 `unique_fd` 管理一个 sync_file fd：

- `Fence::wait()` 向下调用 `sync_wait()`；
- `waitForever()` 先等 3 秒，超时后打印 fence 信息，再继续无限等待；
- `Fence::merge()` 调用 `sync_merge()`；
- `getSignalTime()` 通过 `sync_file_info()` 读取状态与最晚 signal timestamp；
- flatten / unflatten 只传 0 或 1 个 fd；
- `Fence::NO_FENCE` 内部持有 `-1`。

这层 RAII 能减少框架内的 fd 泄漏，但跨 API 交接时仍要遵守所有权规则。

## 3. 旧 sync 术语与当前内核对象

Android 官方同步文档仍用 `sync_timeline`、`sync_pt`、`sync_fence` 解释早期模型。它们适合帮助理解“时间线、完成点、完成点集合”，但 Android 17 内核的主线类型已经是 `dma_fence`、`sync_file` 与 `dma_resv`。

| 历史/文档术语 | Android 17 对应理解 |
|---|---|
| `sync_timeline` | 某个执行上下文的有序工作序列；kernel fence 使用 context / seqno 表达 |
| `sync_pt` | 序列中的一个完成点；由具体 `dma_fence` 表达 |
| `sync_fence` | 旧 Android 同步对象名称；现代 userspace 边界主要看到 sync_file fd |
| `sync_file_info`/`sync_fence_info` | userspace 查询 sync_file 及其内部栅栏的 UAPI |
| `dma_resv` | 随 dma-buf 保存 implicit fence 集合，和 Android 显式传 fd 的路径要分开分析 |

Android 8.1 的 `libsync` 已同时处理旧版与新版 ioctl。读历史代码时可以保留旧名；分析 Android 17 跟踪数据时，应以 driver / timeline / context / seqno 和实际 fd 流向为准。

## 4. Acquire、release、present：先看方向

三种名称描述的是接口角色，并非三种不同的 kernel 类。

| 名称 | 谁产生或返回 | 谁等待 | 保护的访问 |
|---|---|---|---|
| acquire fence | producer 随新缓冲提交 | consumer、SurfaceFlinger、HWC 或下一处理级 | producer 对新缓冲的写入尚未完成 |
| release fence | consumer 释放旧缓冲时返回 | producer 再次写旧缓冲前 | consumer 对旧缓冲的读取尚未完成 |
| present fence | HWC `present`/`presentDisplay` 每个 display frame 返回 | SurfaceFlinger、时间统计与后续显示资源管理 | 本轮 display composition 的完成条件 |

### 4.1 生产完成栅栏到消费者侧称为获取栅栏

应用调用 `queueBuffer(buffer, fence)` 时，这条栅栏表示 producer 的写入可能仍在进行。`BufferQueueProducer::queueBuffer()` 把 `QueueBufferInput` 中的字段命名为 `acquireFence`，保存到槽位，并随 `BufferItem` 交给 consumer。

这里有两个常见说法：

- 从生产者看：GPU 完成栅栏、渲染完成栅栏；
- 从 consumer 看：acquire fence，读取缓冲前要遵守的依赖。

两种说法可以指向同一个 fd。判断语义时要注明观察方。

### 4.2 消费者释放栅栏到生产者侧称为出队/释放栅栏

`BufferQueueConsumer::releaseBuffer(slot, frameNumber, releaseFence)` 把 release fence 保存回槽位。之后 producer 再次 `dequeueBuffer()` 选中该槽位，`BufferQueueProducer` 把同一字段作为 `outFence` 返回并清空槽位中的引用。

Vulkan、EGL 和 `ANativeWindow` 代码常把这个返回值叫 `dequeue_fence`。它的语义仍是“上一位 consumer 何时不再使用旧内容”。Producer 可以把它导入 GPU queue，让 GPU 等待；也可以由 CPU wait，后者会占用调用线程。

### 4.3 Present fence 的边界

Android 官方文档说明：物理显示的 present fence 表示当前帧出现在屏幕上的完成点；虚拟显示则表示 output buffer 可以安全读取。它按显示、per-frame，不是 per-layer release fence。

present fence 很接近显示完成边界，但仍不是面板光学测量值，也不能代替输入到显示延迟测试。可变刷新率、panel scanout 与厂商 display pipeline 会影响“用户看到”的细节。

## 5. 一帧中的栅栏流向

下面的图以标准应用窗口的 BLAST 路径为基线，用于区分生产完成、显示消费与旧 buffer 回收。

```mermaid
sequenceDiagram
    participant RT as App RenderThread
    participant GPU
    participant BBQ as BLASTBufferQueue
    participant SF as SurfaceFlinger
    participant HWC
    participant D as Display

    RT->>BBQ: dequeueBuffer()
    BBQ-->>RT: old buffer + dequeue/release fence
    RT->>GPU: 导入并等待旧缓冲释放依赖，随后渲染
    RT->>BBQ: queueBuffer(new buffer, producer completion fence)
    BBQ->>BBQ: acquire BufferItem
    BBQ->>SF: Transaction.setBuffer(buffer, acquire fence)
    SF->>HWC: set layer state + DEVICE candidate buffer/fence
    SF->>HWC: validate or presentOrValidate
    opt CLIENT composition required
        SF->>GPU: RenderEngine waits source fences and composes
        GPU-->>SF: client target completion fence
        SF->>HWC: setClientTarget(buffer, fence)
    end
    HWC->>D: present
    HWC-->>SF: display present fence + per-layer release fences
    SF-->>BBQ: buffer release callback(release fence)
    BBQ-->>RT: release fence later returned by dequeueBuffer() 返回
```

图中 BLASTBufferQueue 位于应用进程，先作为窗口 BufferQueue 的 consumer，再把缓冲与窗口状态放进 `SurfaceControl.Transaction`。`BLASTBufferQueue.cpp` 会复制 `BufferItem.mFence` 作为事务的 acquire fence；SurfaceFlinger 返回 release fence 后，BLAST 进入 `releaseBufferCallback()`，再调用本地 consumer 的 `releaseBuffer()`。

Android 17 还为 BLAST 建立了 `BufferReleaseChannel`。SurfaceFlinger 可把回调 ID、release fence 和当前最大 acquired buffer 数写入通道；应用侧既会非阻塞排空，也能在没有空闲槽位时由 `BBQBufferQueueProducer::waitForBufferRelease()` 做可中断的阻塞读取。旧的 transaction listener / completion 信息仍参与释放与兜底，排查时不能把所有释放都归成一次同步 Binder callback。

`SurfaceView`、Camera、codec 和自定义 native producer 可以有不同进程拓扑。三类栅栏的方向仍相同，但 producer、consumer 与 IPC 边界要从对应 BufferQueue 和图层确认。Camera 还会有 HAL output acquire/release fence，不能用 display present fence 替代 camera frame completion。

## 6. SurfaceFlinger 与 HWC 的栅栏

SurfaceFlinger 交给 HWC 的 layer buffer 和 client target 都带 acquire fence。HWC 在显示后提供：

- 每层 release fence：该层上一张缓冲何时不再被 HWC 使用；
- 显示栅栏：本轮显示帧的完成条件。

Android 17 `HWComposer.cpp` 有两条 present 路径：

1. `presentOrValidate()` 返回状态 1 时，present 已在快路径完成，代码直接保存 `outPresentFence` 并获取 release fences；
2. 普通路径在验证/ accept 后，由 `presentAndGetReleaseFences()` 调用 `present()`，再调用 `getReleaseFences()`。

因此，不能把所有帧固定画成“validate → presentOrValidate → 再 present”。分析 trace 时先看 `validateWasSkipped`/PresentSucceeded 语义。

CLIENT 合成还会引入 RenderEngine GPU 工作和 client target。Layer acquire fence 保护源缓冲；RenderEngine 完成 client target 的栅栏再交给 HWC。此时 trace 里可能同时存在应用 GPU、SurfaceFlinger GPU 与 display fence，不能把所有 GPU 栅栏归到应用。

## 7. Fence merge 的语义

一个操作若依赖两项或更多异步工作，可以合并栅栏。Android 17 `Fence::merge(name, f1, f2)` 调用 `sync_merge()`；kernel `sync_file` merge 建立一个新文件，并通过 `dma_fence_unwrap_merge()` 组合输入栅栏。

合并后的依赖在所有输入完成后才满足。原输入 sync_file 仍独立有效，merge 不会替调用者关闭它们。输入之一为 `NO_FENCE` 时，framework 会用另一条有效栅栏与自身合并，从而获得指定名称的新栅栏；两条都无效时返回 `NO_FENCE`。

merge 适合表达“等待所有前置工作”，但不应无条件合并整条显示管线：

- HWC 图层释放栅栏本来就按图层生成；
- 显示栅栏按显示生成；
- 为了方便只保留一个 fd 而合并无关栅栏，会扩大等待范围并掩盖慢依赖；
- debug 名称、driver / timeline 与内部栅栏列表要保留，便于定位哪一项最晚发出信号。

## 8. EGL 与 Vulkan 怎样桥接 native fence

### 8.1 EGL

`EGL_ANDROID_native_fence_sync` 能把 Android 原生栅栏文件描述符包装成 `EGLSyncKHR`，也能从 EGL 同步对象导出 fd。`EGL_KHR_wait_sync`/`EGL_ANDROID_wait_sync` 允许 GPU 等待，减少 CPU 阻塞。

Android 17 HWUI 的 `EglManager::createReleaseFence()` 优先创建 `EGL_SYNC_NATIVE_FENCE_ANDROID`，`glFlush()` 后通过 `eglDupNativeFenceFDANDROID()` 导出 fd。设备不支持 native fence、但支持普通 EGL 栅栏同步时，`SkiaOpenGLPipeline::flush()` 会在 CPU 侧等待 EGLSync，然后返回 `-1`，表示同步已经在本地完成。

### 8.2 Vulkan

Android 原生栅栏使用 `VK_EXTERNAL_SEMAPHORE_HANDLE_TYPE_SYNC_FD_BIT` 与 Vulkan 二进制信号量互操作。Android 17 HWUI 展示了两个方向：

- dequeue 返回的 fence fd 被临时导入 binary `VkSemaphore`，GPU 在写缓冲前等待；
- Skia 刷新操作发出一个可导出的 binary `VkSemaphore` 信号，随后用 `vkGetSemaphoreFdKHR()` 取出 sync fd，随缓冲提交。

源码中的 `VkSemaphoreCreateInfo` 没有挂 `VkSemaphoreTypeCreateInfo`，因此这条边界使用 binary semaphore。变量 `VkDrawResult.presentFence` 最终传给 `presentCurrentBuffer()`，站在 BufferQueue 消费者侧看，它是新缓冲的 acquire fence；它不是 HWC display present fence。

`SYNC_FD` 的导入只支持临时、copy-transference payload。成功调用 `vkImportSemaphoreFdKHR()` 后，fd 所有权交给 Vulkan；binary semaphore 的 wait 消费临时载荷，随后恢复原来的 permanent payload。对 `SYNC_FD` 调用 `vkGetSemaphoreFdKHR()` 也具有 copy-transference 的消费语义，不能把同一次信号当成可重复导出的状态。Android 17 HWUI 为每次桥接创建 semaphore，交给 Skia 等待/ signal 后销毁，避免把一次性载荷当成可复用计数器。

Timeline semaphore 是 Vulkan 1.2 的计数器型同步，可用于应用或引擎内部的多轮队列依赖。Vulkan 1.4.335 规范要求 copy-transference handle 从 binary semaphore 导出。因此，时间线信号量不能直接替代 BufferQueue、SurfaceFlinger 与 HWC 的 native fence fd 协议。设备是否支持 timeline feature 仍需运行时查询。

## 9. fd 所有权与错误处理

Fence fd 的所有权由每个 API 约定。Android 官方 HAL 约定可以概括为：

- API 把 fd 提供给调用方时，接收方负责关闭；
- 调用方把 fd 传给会接管所有权的 API 后，不再关闭；
- 还需要继续使用时，先 `dup()`，再传副本。

`Fence`、`unique_fd`、EGL 和 Vulkan 导入的接管规则不同，不能用一条“调用后总要关闭”覆盖。Android 17 `VulkanManager` 在成功导入 temporary semaphore 后，由 semaphore 持有并关闭 fd；导入失败的分支显式关闭。

Fence fd 泄漏会消耗 fd 表并延长栅栏引用寿命，但不等价于 GraphicBuffer 泄漏。BufferQueue 是否把槽位放回空闲集合取决于 consumer release 协议；GraphicBuffer 底层存储是否回收取决于句柄、Mapper、attachment 与缓冲引用。两类问题可以同时出现，也可以互不相关。

error fence 也不能按普通信号静默忽略。`sync_file_info.status` 小于 0 表示错误；`Fence::getSignalTime()` 会返回 invalid。驱动 hang recovery 可能强制完成栅栏并附带错误，等待结束不代表 GPU 输出内容有效。

## 10. Perfetto：先确定谁在等哪条栅栏

Fence wait 是因果链的观察点，并不自动等同于缺陷。先确定 waiter、目标栅栏和被保护的缓冲，再看 signal 之前发生了什么。

| 现象 | 初步解释 | 需要补的证据 |
|---|---|---|
| SF/HWC 等 layer acquire fence | producer 写入未到完成点 | 应用 submit、GPU renderstage、buffer ID |
| App `dequeueBuffer()` 变长 | 无可用槽位，或选中槽位的 release fence 未完成 | queue depth、release callback、HWC layer release、pacing |
| present fence 晚 | display present 链路晚 | HWC 验证/ present、display mode、FrameTimeline |
| CPU 上 `sync_wait` 很长 | 调用线程被同步阻塞 | 调用栈、是否可改为 GPU-side wait、driver forward progress |
| fence 已 signal 但帧仍晚 | 同步完成后还有调度、latch、composition 或显示延迟 | sched、SF snapshot、HWC 与 display |
| fence 长期 pending 且 driver 无进展 | GPU / display hang 或依赖环 | driver error、reset、IOMMU fault、kernel log |

标准 App Window 还要区分本地 `queueBuffer()` 与 SF 收到 BLAST 事务的时间。`queueBuffer()` 返回只说明帧进入应用侧 BLAST consumer，不代表 SurfaceFlinger 已看到 BufferTX。

### 10.1 可用的 trace 事件

Android 17 kernel 的 `include/trace/events/dma_fence.h` 定义了 emit、init、destroy、enable_signal、signaled、wait_start 和 wait_end。下面的 Perfetto ftrace 配置用于 userdebug/root 环境验证 fence 生命周期。

```text
data_sources {
  config {
    name: "linux.ftrace"
    ftrace_config {
      ftrace_events: "dma_fence/dma_fence_emit"
      ftrace_events: "dma_fence/dma_fence_signaled"
      ftrace_events: "dma_fence/dma_fence_wait_start"
      ftrace_events: "dma_fence/dma_fence_wait_end"
      atrace_categories: "gfx"
      atrace_categories: "view"
    }
  }
}
```

设备必须先检查 tracefs `available_events`。vendor kernel 可能裁剪事件，user build 也可能限制访问。缺少 dma_fence 事件时，可以结合 `gfx` atrace、`FenceMonitor`、BufferQueue/BufferTX、FrameTimeline、GPU renderstage、HWC 切片与 kernel log补齐。

### 10.2 四步归因

1. 锁定 Surface ID、buffer ID、slot 和帧号。
2. 标出入队、事务、锁存、验证/显示、释放回调与下一次出队。
3. 找出长等待对应的驱动、时间线、上下文、序列号和信号时刻。
4. 回到信号方之前的 CPU 调度、GPU queue、HWC、display 或错误事件。

只看等待时长无法区分生产者晚、消费者持有过久、queue-stuffing、线程抢占或硬件挂起。

## 11. `sw_sync` 的边界

kernel `drivers/dma-buf/sw_sync.c` 提供软件 timeline，主要用于测试、selftest 与受控软件路径。普通应用不应创建可任意 signal 的栅栏去伪造 GPU/HWC 完成；设备节点权限和 SELinux 通常也会阻止这类访问。

测试代码使用 `sw_sync` 时，仍需保证依赖图会向前推进。由用户空间任意决定 signal 的栅栏进入内核资源回收或设备依赖后，容易形成内核无法观察完整因果的死锁。

## 12. 版本演进

### Android 7 / API 24

HWC2 已明确图层/ client target acquire fence、各图层释放栅栏与显示栅栏的接口职责，因此 Android 7 可作为现代基线。

### Android 8–11

libsync 用户空间同时兼容旧 Android sync ioctl 与新版 sync_file UAPI；kernel 主线逐步收敛到 dma-fence/sync_file。Skia 的 GL/Vulkan 后端在这一阶段发展，但具体 release fence 路径应按对应标签读取。

### Android 12 / API 31

BLAST 与 FrameTimeline 成为现代应用窗口诊断基线。应用 RenderThread 的 queue 先进入进程内 BLAST consumer，再通过 buffer transaction 到 SurfaceFlinger；fence 方向未改变，观察点增加了一层。

### Android 13–16

Composer HAL 向 Stable AIDL 演进，Vulkan、EGL 与 native fence 互操作继续使用 sync fd。Timeline semaphore 适合 Vulkan 内部同步，未替代 Android 显示边界的 binary semaphore /sync_file。

### Android 17 / API 37

`android-17.0.0_r1` 的 BufferQueue、BLAST release callback、SurfaceFlinger `presentOrValidate` 快路径、HWUI GL/Vulkan 栅栏桥接仍遵循 acquire / release / present 三类方向。`android17-6.18-2026-06_r6` 继续以 dma-fence、sync_file 与对应 tracepoint 提供内核同步基础。Android 17 没有在 16 KB 页大小与 fence signal latency 建立通用性能保证。

## 13. 常见误区

### `queueBuffer()` 的栅栏一定叫 release fence

站在 producer 局部代码中，它可能被描述为“释放给下一阶段”的栅栏；进入 BufferQueue 消费者后，接口字段与语义是 acquire fence。描述时应注明方向。

### `dequeueBuffer()` 返回的是 acquire fence

代码里常叫 dequeue fence，表示该缓冲上一轮 consumer 访问尚未结束。站在 producer 即将写入的视角，它是 consumer release fence。

### Present fence 等于屏幕每个像素完成发光

它是 HWC/display 协议的完成点。面板扫描与光学响应仍需专用测量。

### 栅栏发出信号后缓冲一定空闲

signal 只满足同步依赖。slot 状态、GraphicBuffer 引用、Mapper handle、HWC/GPU / GPU cache 与应用对象仍会影响缓冲生命周期。

### Timeline semaphore 能直接导出 Android sync fd

`SYNC_FD` 桥接使用 binary semaphore。Timeline semaphore 可用于 Vulkan 内部计数同步，不能直接替换 native fence fd。

### 长 fence wait 的问题在栅栏框架

Fence 让等待可见。GPU 工作慢、HWC 持有、display 迟到、queue 深度、调度延迟与 driver hang 都可能让它变长；根因位于信号方或依赖拓扑时，修改等待本身没有帮助。

## 14. Android 17 源码入口

| 目标 | 源码 |
|---|---|
| userspace Fence wait / merge / signal time | `frameworks/native/libs/ui/Fence.cpp` |
| BufferQueue producer acquire fence | `frameworks/native/libs/gui/BufferQueueProducer.cpp` |
| consumer release fence 回传 | `frameworks/native/libs/gui/BufferQueueConsumer.cpp` |
| BLAST transaction、release callback 与通道 | `frameworks/native/libs/gui/BLASTBufferQueue.cpp`、`BufferReleaseChannel.cpp` |
| HWC 显示/ release fence | `frameworks/native/services/surfaceflinger/DisplayHardware/HWComposer.cpp` |
| HWUI EGL bridge | `frameworks/base/libs/hwui/renderthread/EglManager.cpp` |
| HWUI Vulkan binary semaphore bridge | `frameworks/base/libs/hwui/renderthread/VulkanManager.cpp` |
| kernel fence contract | `drivers/dma-buf/dma-fence.c`、`include/linux/dma-fence.h` |
| sync_file UAPI | `drivers/dma-buf/sync_file.c`、`include/uapi/linux/sync_file.h` |
| fence tracepoints | `include/trace/events/dma_fence.h` |

## 参考资料

- [Android synchronization framework](https://source.android.com/docs/core/graphics/sync)
- [Android graphics architecture](https://source.android.com/docs/core/graphics/architecture)
- [Linux DMA-BUF/dma-fence / dma-fence documentation](https://docs.kernel.org/6.18/driver-api/dma-buf.html)
- [Vulkan 1.4.335 synchronization specification](https://github.com/KhronosGroup/Vulkan-Docs/blob/v1.4.335/chapters/synchronization.adoc)
