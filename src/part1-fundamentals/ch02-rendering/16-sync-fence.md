---
title: "Sync Fence 框架与帧同步机制"
chapter: "2.16"
section: "2.16"
status: ready-for-review
applicable_versions: "Android 8 (API 26) - Android 17 (API 37)"
last_verified: "2026-04-05"
last_verified_against: "AOSP android-16.0.0_r1, Linux kernel 6.12"
confidence: medium
drafted_date: "2026-04-05"
drafted_by: "openclaw-task2a"
sources:
  - type: aosp
    path: "frameworks/native/libs/ui/Fence.cpp"
  - type: aosp
    path: "system/core/libsync/"
  - type: aosp
    path: "frameworks/native/services/surfaceflinger/DisplayHardware/HWComposer.cpp"
  - type: aosp
    path: "hardware/interfaces/graphics/composer/"
  - type: official
    path: "https://source.android.com/docs/core/graphics/architecture"
tags: [sync-fence, fence, hwui, rendering, synchronization, timeline]
related_chapters: ["2.4", "2.5", "2.6", "2.13", "2.15"]
---

# 2.16 Sync Fence 框架与帧同步机制

在 Android 渲染管线中，App 画一帧、SurfaceFlinger 合成一帧、Display 显示一帧——这三个动作分布在三个不同的硬件单元上（CPU/GPU、GPU/HWC、Display Controller），而且全是异步的。如果没有一种机制来协调「谁先谁后」，SurfaceFlinger 可能会在 GPU 还没画完的时候就开始读 buffer，读到半成品画面，这就是我们常说的画面撕裂（tearing）。

Fence 就是解决这个问题的核心机制。它是一个由内核管理的信号量，告诉我们「某个硬件单元对某个 buffer 的操作完成了」。读完这一节，我们在 Perfetto 里看到 SurfaceFlinger 进程中那些 Fence wait 的色块时，就能精确判断：这个等待是正常的同步开销，还是已经构成了掉帧的瓶颈。

## 为什么需要 Fence：异步世界里的同步问题

渲染管线的每一步都是异步的。App 主线程执行完 measure/layout/draw 之后，把 draw call 提交给 GPU，然后主线程就继续干别的事了——GPU 在后台慢慢画。这意味着当 App 调用 `queueBuffer()` 把 buffer 交给 SurfaceFlinger 时，GPU 很可能还没画完。

如果没有 Fence，SurfaceFlinger 只有两个选择：

1. **直接读 buffer**——但 GPU 可能还在写，读到的是不完整的帧（撕裂）
2. **等一段时间再读**——但等多久？等短了还是撕裂，等长了浪费时间

Fence 给出了第三个选择：**等一个信号**。GPU 画完后自动发信号，SurfaceFlinger 收到信号再读。既不浪费等待时间，也不会读到不完整的帧。

这就像餐厅的出餐铃：点完菜不用一直盯着厨房，铃响了去取就行。Fence 就是这个铃——而且不需要你手动按铃，是厨房（GPU/Display Controller）自己按的。

[图：渲染管线中 3 个 Fence 的时序图——App 渲染完成后 GPU 发出 acquire fence signal，SurfaceFlinger 合成完成后 HWC 发出 release fence signal，Display 显示完成后发出 retire fence signal。标注三者的时间关系和 buffer 状态变迁]

## Fence 的内核基础：sync_timeline 与 sync_pt

### Linux dma-buf fence

Android 的 Fence 机制建立在 Linux 内核的 `dma-buf fence` 框架之上。`dma-buf`（Direct Memory Access Buffer）是内核提供的跨设备/跨进程内存共享机制（我们在 [2.15 DMA-BUF 与 Gralloc](part1-fundamentals/ch02-rendering/15-dmabuf-gralloc.md) 中详细讨论过它的内存管理层面），而 `dma-fence` 是附在 `dma-buf` 上的同步原语。

内核中的核心概念有三个：

- **sync_timeline**：一个单调递增的计数器，通常对应一个硬件驱动上下文（比如 GPU 的一个 ring buffer，或者 Display Controller 的一个 pipeline）。每个驱动可以有自己的 timeline。
- **sync_pt（sync point）**：timeline 上的一个具体值，代表某个异步操作的完成时刻。sync_pt 有三种状态：active（未完成）、signaled（已完成）、error（出错）。
- **sync_fence**：一个或多个 sync_pt 的集合，用文件描述符（fd）表示。一个 fence 只有在它包含的所有 sync_pt 都 signaled 之后才会变成 signaled 状态。

这三者的关系可以用一条时间线来理解：

```
sync_timeline (GPU timeline):  0 ---- 1 ---- 2 ---- 3 ---- 4 ---->
                                ^                    ^
                           sync_pt A            sync_pt B
                           (frame N 完成)       (frame N+1 完成)

sync_fence = {sync_pt B}  → 当 GPU 推进到值 4 时 signal
```

### sw_sync：软件模拟的 timeline

不是所有场景都有硬件 fence 支持。Android 提供了 `sw_sync`（software sync），一个基于 `/dev/sw_sync` 设备节点的软件 timeline 实现。它允许用户空间手动推进 timeline（调用 `sw_sync_timeline_inc()`），主要用于：

- 测试和调试
- 不支持硬件 fence 的设备上的 fallback
- Camera、Video 解码器等需要软件参与的管线

在正常运行的设备上，GPU 和 HWC 都有各自的硬件 timeline，`sw_sync` 只在测试场景中出现。

### Fence 的关键特性

几个需要特别注意的设计决策：

1. **用户空间不能创建或 signal fence**。Fence 只能由内核驱动创建和 signal。这保证了 forward progress——即使 App 崩溃或卡死，硬件的 fence 仍然会正常 signal（因为硬件不依赖用户空间进程）。

2. **Fence 用 fd 表示**。这意味着可以通过 Binder（`BnGraphicBufferProducer` 的 `queueBuffer` 调用）在进程间传递，利用内核的 fd 生命周期管理。

3. **Fence 可以 merge**。两个 fence 可以合并成一个新的 fence，新 fence 包含两个原始 fence 的所有 sync_pt，只有全部 signal 才算 signal。这在 SurfaceFlinger 合成多个 Layer 时非常重要——每个 Layer 有自己的 acquire fence，SurfaceFlinger 需要等所有 Layer 都画完才能开始合成。

### AOSP 用户空间的 Fence 封装

内核提供了底层的 fence 机制，AOSP 在此之上做了 C++ 封装：

```
// frameworks/native/libs/ui/Fence.cpp
// frameworks/native/include/ui/Fence.h
class Fence {
    // 核心就是包装一个 fence fd
    int mFenceFd;
    
    // 等待 fence signal，支持超时
    status_t wait(int timeoutMs);
    
    // 合并两个 fence
    static sp<Fence> merge(const sp<Fence>& f1, const sp<Fence>& f2);
    
    // 获取 signal 时间戳
    nsecs_t getSignalTime() const;
};
```

用户空间库 `system/core/libsync/` 提供了与内核交互的底层 C 接口（`sync_merge`、`sync_wait`、`sync_file_info` 等）。

[已验证: AOSP android-16.0.0_r1, frameworks/native/libs/ui/Fence.cpp]

## 渲染管线中的三种 Fence

了解了 Fence 的底层机制后，我们来看它在渲染管线中的实际使用。一帧从 App 渲染到屏幕显示，会经过三个关键 Fence：

### Acquire Fence：「GPU 画完了，你可以读了」

**产生者**：App（更准确地说，是 GPU 或 RenderThread 的 Skia/HWUI pipeline）

**消费者**：SurfaceFlinger / HWC

当 App 调用 `queueBuffer()` 把一帧交给 BufferQueue 时，会附带上一个 acquire fence。这个 fence 代表「GPU 对这个 buffer 的写入操作」。SurfaceFlinger 在拿到 buffer 后不能直接读——它必须等 acquire fence signal 之后才能开始合成。

在代码层面，`BufferQueueProducer::queueBuffer()` 会把 fence fd 传给 BufferQueue 的消费者侧。SurfaceFlinger 在 `Layer::onFrameAvailable()` 中收到这个 fence，在合成前调用 `fence->wait()` 或把它传给 HWC 让硬件等。

```
// 简化的 SurfaceFlinger 合成流程
void SurfaceFlinger::compose() {
    for (auto& layer : layers) {
        // 从 BufferQueue 拿 buffer + acquire fence
        auto buffer = layer->acquireBuffer();
        
        if (useHWC) {
            // 传给 HWC，让硬件等 fence
            hwc->setLayerBuffer(layer, buffer, buffer->acquireFence);
        } else {
            // GPU 合成，需要自己等
            buffer->acquireFence->wait(100); // 最多等 100ms
            // 开始 GPU 合成...
        }
    }
}
```

### Release Fence：「我用完了，你可以回收了」

**产生者**：HWC / SurfaceFlinger（GPU 合成时）

**消费者**：BufferQueue → App

SurfaceFlinger 合成完一帧后，会得到一个 release fence（从 HWC 的 `getReleaseFences()` 或 GPU 合成完成时产生）。这个 fence 告诉 App：「之前你用来渲染的那个 buffer，HWC/GPU 不再使用了」。App 在下次 `dequeueBuffer()` 时如果拿到这个 buffer，需要等 release fence signal 之后才能写入。

Release fence 的存在是因为 HWC 可能采用了异步合成策略——`presentDisplay()` 返回了不代表 HWC 真的合成完了，HWC 可能在后台还在用这个 buffer。

### Retire Fence（Present Fence）：「屏幕显示完了」

**产生者**：Display Controller

**消费者**：SurfaceFlinger（用于统计和时序计算）

Retire fence（也叫 present fence）在 `presentDisplay()` 调用后由 HWC 返回。它代表「这一帧已经被 Display Controller 送上屏幕显示了」。SurfaceFlinger 用这个 fence 来：

- 计算「从 queueBuffer 到实际显示」的端到端延迟
- 驱动 VSync 偏移量（VSYNC-offset）的动态调整
- 判断是否掉帧

在 Perfetto 中，SurfaceFlinger 的 `onFramePresented()` 回调就是等 retire fence signal 之后触发的。

[图：三种 fence 在 BufferQueue 状态流转中的位置——FREE→DEQUEUED（App dequeue）→QUEUED（App queue + acquire fence）→ACQUIRED（SF acquire）→FREE（SF release + release fence）。标注每种 fence 对应的状态转换]

## Fence 与掉帧：性能分析的关键

Fence 本身不是性能问题，但 fence 等待时间的异常增长是掉帧的重要信号。我们在分析 Perfetto Trace 时，Fence wait 是定位渲染管线瓶颈的关键线索。

### Acquire fence 延迟 → App 渲染瓶颈

如果 acquire fence 迟迟不 signal，说明 GPU 渲染慢。这会导致：

- SurfaceFlinger 在合成时等不到 buffer → `latchBuffer` 超时 → 使用旧 buffer 合成 → 用户看到重复帧
- 下一帧 App 调用 `dequeueBuffer()` 时 buffer 全被占着 → 阻塞等 release fence → App 主线程被卡

在 Perfetto 中的表现：
- SurfaceFlinger 的 `latchBuffer` 切片中出现大段 `fence wait`
- App 的 `dequeueBuffer` 切片中出现 `dequeueBuffer` 耗时异常

### Release fence 延迟 → SurfaceFlinger/HWC 瓶颈

如果 release fence 迟迟不 signal，说明 HWC 合成慢或 Display Controller 处理不过来。这会导致：

- BufferQueue 中可用的 buffer 减少 → 三缓冲退化为双缓冲甚至单缓冲
- App `dequeueBuffer` 阻塞等待 → 帧渲染被推迟

### Fence merge 的放大效应

SurfaceFlinger 合成一帧时，需要等所有可见 Layer 的 acquire fence 全部 signal。假设屏幕上有 10 个 Layer，其中一个 Layer 的 GPU 渲染特别慢，SurfaceFlinger 就会为这个慢 Layer 的 fence 等待，延迟了整帧的合成。

Fence merge 的代码路径：

```cpp
// frameworks/native/services/surfaceflinger/
// SurfaceFlinger::computeWorkingSet()
for (auto& layer : layers) {
    // 合并所有 layer 的 acquire fence
    auto fence = layer->acquireFence;
    if (readyFence) {
        readyFence = Fence::merge(readyFence, fence);
    } else {
        readyFence = fence;
    }
}
// 等待合并后的 fence
readyFence->wait(kAcquireTimeoutMs);
```

[已验证: AOSP android-16.0.0_r1, SurfaceFlinger 合成流程]

### 实战分析路径

当我们在 Perfetto 中怀疑是 fence 导致的掉帧时，分析路径如下：

1. **找到掉帧的帧号**：在 Janky Frames track 或 `Frames` track 中定位具体的掉帧
2. **看 App 侧**：Main Thread / RenderThread 是否有 `dequeueBuffer` 阻塞？如果有，说明 release fence 没及时 signal
3. **看 SurfaceFlinger 侧**：`latchBuffer` / `composition` 中是否有大段 fence wait？如果有，说明 acquire fence 没及时 signal
4. **看 GPU 侧**：GPU track 中对应时间段的 GPU 利用率和耗时是否异常
5. **看 BufferQueue 状态**：BufferQueue track 中 buffer 数量是否降为 0（说明所有 buffer 都被占着）

## 在 Perfetto 中的 Fence 表现

### BufferQueue Track

BufferQueue track（通常在 App 进程或 SurfaceFlinger 进程下）是观察 Fence 最直接的窗口。它显示了每个 buffer 的状态（free/queued/acquired）和数量变化。

正常情况下，在 60fps 场景中 BufferQueue 的 queued 数量在 0-1 之间波动。如果持续为 2（三缓冲满载），说明 SurfaceFlinger 消费速度跟不上 App 生产速度——很可能是 fence 等待导致的。

### SurfaceFlinger Composition Timeline

在 SurfaceFlinger 进程的 track 中，能看到：

- `setClientComposition` / `GPU composition`：GPU 合成时的 fence wait 时间
- `presentDisplay`：HWC 合成时的 fence 交互
- fence 对象的名称通常包含窗口名和 buffer 索引（如 `SurfaceView:0`），帮助定位是哪个 Surface 的 fence

### GPU Completion

GPU track 中能看到 GPU 对每个 frame 的处理时间。如果 GPU 渲染耗时超过一个 VSync 周期（16.6ms @60Hz），对应的 acquire fence 就会延迟 signal。

## 版本演进

### Android 8 (API 26)：引入 HWC2

HWC2 重新定义了 fence 的交互接口。之前 HWC1 使用 `set()` + `prepare()` 两步，fence 管理较粗；HWC2 改为 per-Layer per-Frame 的 fence 传递，通过 `setLayerBuffer()` 带 acquire fence，通过 `getReleaseFences()` 取回 release fence，精确度更高。

### Android 10 (API 29)：迁移到 libsync

`system/core/libsync` 被重构，旧的 `sw_sync` 接口逐渐被 `dma-buf fence` 的标准接口替代。用户空间的 Fence 操作更统一。

### Android 12 (API 31)：BufferQueue 增强与 Fence 调试

- BufferQueue 的 fence 调试信息增强，`dumpsys SurfaceFlinger` 中能看到更详细的 fence 状态
- Fence 泄漏检测机制改进

### Android 14-16 (API 34-36)：Skia 渲染管线与 Fence 优化

随着 HWUI 全面切换到 Skia 渲染管线（RenderThread 使用 Skia + Vulkan/OpenGL），fence 的创建和管理路径有了一些变化。Skia 的 `GrDirectContext` 在 flush 时生成 fence，通过 `flushAndSignal()` 与 fence 交互。Android 16 的 ARR（Adaptive Refresh Rate）引入了动态 VSync 步进，fence 的时间戳计算需要适配不同的刷新率。

[待验证：Android 17 对 fence 机制是否有进一步的优化]

## 常见问题与排查

### Fence 泄漏：fd 没关导致 buffer 泄漏

每个 fence 是一个 fd（文件描述符）。如果拿到 fence fd 后忘记 close，就会导致：

- fd 数量持续增长，最终耗尽进程的 fd 限制
- Buffer 对应的 fence 引用不释放，buffer 永远不回到 free pool
- SurfaceFlinger 的 `dumpsys SurfaceFlinger` 中能看到大量 active fence

排查方法：`ls /proc/<pid>/fd/ | wc -l` 观察 fd 数量，结合 `dumpsys SurfaceFlinger` 中的 fence 信息定位泄漏来源。

### HWC Fence 回退：硬件 fence 不可用

某些低端设备的 HWC 实现可能不完全支持 fence（特别是 video/camera 等特殊 Layer 类型）。此时 SurfaceFlinger 会走 fallback 路径：

- 用 `sw_sync` 创建软件 fence
- 或者用 `-1`（invalid fence）表示不需要等待

fallback 路径的性能影响取决于实现——软件 fence 通常比硬件 fence 有额外开销，但现代设备上这个问题已经很少见了。

### GPU Hang：Fence 永远不 Signal

最严重的 fence 异常是 GPU hang——GPU 崩溃后停止工作，所有等待 GPU fence 的操作都会卡住。系统级的处理方式：

- GPU 驱动的 watchdog 检测到 hang 后 reset GPU
- reset 后 fence 被置为 error 状态
- SurfaceFlinger 检测到 fence error 后上报 `FENCE_ERROR`，可能触发 Surface 重建

在 Perfetto 中表现为：SurfaceFlinger 的 fence wait 持续到超时，GPU track 中出现大段空白（GPU 停止工作）。

## 与其他机制的关系

- **VSync（[2.3](part1-fundamentals/ch02-rendering/03-vsync.md)）**：VSync 决定「什么时候开始」，Fence 决定「什么时候结束」。两者共同构成了帧渲染的时间约束。
- **Choreographer（[2.4](part1-fundamentals/ch02-rendering/04-choreographer.md)）**：Choreographer 在 VSync-app 到来时开始渲染，渲染完成后通过 Fence 通知 SurfaceFlinger。
- **MainThread 与 RenderThread（[2.5](part1-fundamentals/ch02-rendering/05-main-render-thread.md)）**：RenderThread 提交 GPU 命令后生成 acquire fence，MainThread 的 `dequeueBuffer` 可能被 release fence 阻塞。
- **SurfaceFlinger（[2.6](part1-fundamentals/ch02-rendering/06-surfaceflinger.md)）**：SurfaceFlinger 是 fence 的核心消费者——它等 acquire fence，产生 release fence，接收 retire fence。
- **BufferQueue（[2.13](part1-fundamentals/ch02-rendering/13-buffer-queue.md)）**：BufferQueue 的每次状态转换都伴随着 fence 的传递，fence 是 buffer 状态机的同步保障。
- **DMA-BUF 与 Gralloc（[2.15](part1-fundamentals/ch02-rendering/15-dmabuf-gralloc.md)）**：Fence 的底层实现基于 dma-buf fence，Gralloc 分配的 GraphicBuffer 通过 dma-buf 跨进程共享，fence 负责同步对这些 buffer 的访问。

## 参考资料

- AOSP 源码：`frameworks/native/libs/ui/Fence.cpp`、`system/core/libsync/`
- AOSP 源码：`frameworks/native/services/surfaceflinger/DisplayHardware/HWComposer.cpp`
- AOSP 源码：`hardware/interfaces/graphics/composer/`（HWC HAL 定义）
- Linux 内核：`include/linux/dma-fence.h`、`drivers/dma-buf/`
- [Android Graphics Architecture](https://source.android.com/docs/core/graphics/architecture)
- [Android Sync Framework](https://source.android.com/docs/core/graphics/sync)
