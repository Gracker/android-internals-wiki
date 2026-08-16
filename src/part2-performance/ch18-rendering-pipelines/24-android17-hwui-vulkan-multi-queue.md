---
title: "Android 17 HWUI Vulkan 多队列并行渲染与帧边界管理"
chapter: "18.24"
section: "18.24"
section_title: "Android 17 HWUI Vulkan 多队列并行渲染与帧边界管理"
status: ready-for-review
applicable_versions: "Android 14 (API 34) - Android 17 (API 37)"
tags: [vulkan, hwui, rendering, gpu, multi-queue, frame-boundary, android17]
related_chapters: ["2.10", "2.14", "18.9", "18.11"]
last_verified: "2026-07-31"
last_verified_against: "AOSP android-17.0.0_r1 / android-14.0.0_r1 至 android-16.0.0_r1 历史标签 / Writer rendering_pipelines S01、S02 / Vulkan 规范 / android17-6.18-2026-06_r6"
confidence: high
sources:
  - type: internal-reference
    path: "/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Writer/rendering_pipelines/S01_rendering_types_overview.md"
    role: "标准 App Window 从应用生产 buffer 到 SurfaceFlinger、HWC 和 present 的公共基线"
  - type: internal-reference
    path: "/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Writer/rendering_pipelines/S02_aosp_standard_type.md"
    role: "Choreographer、UI Thread、RenderThread、BufferQueue 与 FrameTimeline 的标准 HWUI 路径"
  - type: aosp
    path: "https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/libs/hwui/renderthread/VulkanManager.cpp"
    role: "VkDevice、双 graphics queue、Skia context、global priority、frame boundary 与 sync-fd 导入导出"
  - type: aosp
    path: "https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/libs/hwui/renderthread/VulkanManager.h"
    role: "VulkanManager 对象边界、queue 字段、Vulkan 1.1 上限与 AGI 私有扩展说明"
  - type: aosp
    path: "https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/libs/hwui/HardwareBitmapUploader.cpp"
    role: "GL/Vulkan hardware bitmap 上传、GrallocUploadThread、CPU 同步等待与 60 秒闲置回收"
  - type: aosp
    path: "https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/libs/hwui/hwui/Bitmap.cpp"
    role: "allocateHardwareBitmap 的内容复制语义"
  - type: aosp
    path: "https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/libs/hwui/pipeline/skia/SkiaVulkanPipeline.cpp"
    role: "窗口 dequeue、draw、finishFrame 与 swapBuffers 的调用顺序"
  - type: aosp
    path: "https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/libs/hwui/renderthread/VulkanSurface.cpp"
    role: "ANativeWindow buffer、dequeue fence、buffer age、surface damage 与 queueBuffer"
  - type: aosp
    path: "https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/libs/hwui/renderthread/CanvasContext.cpp"
    role: "FrameTimeline 元数据、damage history、dequeue/queue duration 与帧完成时间"
  - type: aosp
    path: "https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/libs/hwui/Properties.cpp"
    role: "partial update、buffer age、render pipeline 与 context priority 的属性入口"
  - type: aosp
    path: "https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/libs/hwui/pipeline/skia/VkFunctorDrawable.cpp"
    role: "WebView Vulkan functor 在 RenderThread 上的私有互操作边界"
  - type: aosp
    path: "https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/libs/gui/Surface.cpp"
    role: "ANativeWindow dequeueBuffer、queueBuffer 与 fence fd 传递"
  - type: aosp-history
    path: "https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-14.0.0_r1/libs/hwui/renderthread/VulkanManager.cpp"
    role: "Android 14 双 graphics queue 与 global priority 基线"
  - type: aosp-history
    path: "https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-15.0.0_r1/libs/hwui/renderthread/VulkanManager.cpp"
    role: "Android 15 对照"
  - type: aosp-history
    path: "https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-16.0.0_r1/libs/hwui/renderthread/VulkanManager.cpp"
    role: "Android 16 frame-boundary 与 global-priority query 对照"
  - type: specification
    path: "https://registry.khronos.org/vulkan/specs/latest/man/html/VkFrameBoundaryEXT.html"
    role: "VK_EXT_frame_boundary 的 submission annotation 语义"
  - type: specification
    path: "https://registry.khronos.org/vulkan/specs/latest/man/html/VkDeviceQueueCreateInfo.html"
    role: "同一 queue family 创建多条 VkQueue 的规范字段"
  - type: official
    path: "https://perfetto.dev/docs/data-sources/gpu"
    role: "GPU counter 与 render stage 数据源"
  - type: official
    path: "https://perfetto.dev/docs/data-sources/frametimeline"
    role: "FrameTimeline expected/actual 时间线与 jank 分类"
  - type: official
    path: "https://developer.android.com/agi/frame-trace/frame-profiler"
    role: "AGI 单帧 Vulkan/GL 调用、资源和 pipeline state 分析"
  - type: kernel
    path: "https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/drivers/dma-buf/dma-fence.c"
    role: "Android 17 内核 dma_fence 状态、回调与等待基线"
  - type: kernel
    path: "https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/drivers/dma-buf/sync_file.c"
    role: "sync_file fd 对 dma_fence 的封装与用户空间边界"
  - type: kernel
    path: "https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/kernel/sched/core.c"
    role: "RenderThread 与上传线程的 CPU 调度基线；不定义 Vulkan queue 的 GPU 执行顺序"
---

# 18.24 Android 17 HWUI Vulkan 多队列并行渲染与帧边界管理

Android 17 的 HWUI Vulkan 后端会从同一个 graphics queue family 取得两条 `VkQueue`。queue family 是一组具有相同能力标志的 Vulkan 队列，`VkQueue` 则是向设备提交命令批次的接口。queue 0 服务 RenderThread 的窗口绘制，queue 1 服务 `HardwareBitmapUploader` 的 AHardwareBuffer 上传。二者共享同一个逻辑设备 `VkDevice`，并分别绑定一个 Skia `GrDirectContext`；后者是 Skia 管理 GPU 资源与提交工作的上下文。

源码能够证明 HWUI 创建了两条 queue，也能证明 CPU 线程可以分别向它们执行 host submission（主机侧命令提交）。GPU 是否并行执行这些命令则由驱动与硬件决定；GPU 引擎、依赖、内存带宽、频率和调度策略都可能让工作交错或串行。分析时要分别标明接口保证、由源码推导的结论，以及仍需 trace 验证的硬件行为。

对 `android-14.0.0_r1` 至 `android-17.0.0_r1` 的 `VulkanManager.cpp` 做标签对比后，可以确认双 queue 在 Android 14 基线中已经存在。标题中的 Android 17 表示本文采用的源码版本，不能据此把双 queue 写成 Android 17 新增特性。

## 复核基线

| 层级 | 基线 | 负责内容 |
| --- | --- | --- |
| Android 平台 | Android 17 / API 37 / `android-17.0.0_r1` | HWUI、VulkanManager、SkiaVulkanPipeline、ANativeWindow、FrameTimeline |
| Android 内核 | `android17-6.18-2026-06_r6` | CPU 线程调度、dma-buf、dma-fence 与 sync_file；厂商 GPU 调度仍由具体驱动实现，内核不包含 `VulkanManager` 或 Skia 逻辑 |
| 历史对照 | `android-14.0.0_r1`、`android-15.0.0_r1`、`android-16.0.0_r1` | 判断双 queue 与 frame-boundary 代码何时已出现 |

分析范围限定为 HWUI 选择 `SkiaVulkan` 的应用进程。应用自行创建的 Vulkan device/queue、SurfaceFlinger 的 RenderEngine Vulkan 上下文，以及厂商 GPU 服务，都不属于这里的 `VulkanManager` 实例。

## 完整路径

下面的流程图标出两条 queue 在 HWUI 以及窗口显示路径中的位置：

```mermaid
flowchart LR
    UI["UI 线程录制 RenderNode display list"] --> RT["RenderThread / SkiaVulkanPipeline"]
    DEC["Bitmap decode / createBitmap"] --> UP["GrallocUploadThread / VkUploader"]
    subgraph DEV["同一个 VkDevice / graphics queue family"]
        Q0["VkQueue 0: mGraphicsQueue"]
        Q1["VkQueue 1: mAHBUploadQueue"]
    end
    RT --> Q0
    UP --> Q1
    Q1 --> HBM["Hardware Bitmap AHardwareBuffer"]
    HBM --> TEX["供后续窗口帧作为纹理采样"]
    Q0 --> WIN["App Window AHardwareBuffer"]
    WIN --> BQ["ANativeWindow queueBuffer + producer completion fence"]
    BQ --> SF["SurfaceFlinger latch / composition"]
    SF --> HWC["HWC / RenderEngine / present"]
```

应用进程生产窗口 buffer，SurfaceFlinger 负责 latch（选定本轮合成使用的 buffer）与合成决策，HWC/显示设备完成 present。图中只展开应用进程内的 HWUI Vulkan 双 queue，后半段仍沿用 BufferQueue、SurfaceFlinger 与显示路径。

AHardwareBuffer 是可跨系统组件共享的图形缓冲区。queue 1 负责把 CPU 侧 bitmap 像素复制进新分配的 AHardwareBuffer，窗口帧仍由 queue 0 生成。上传完成的 hardware bitmap 后续可以作为纹理由 queue 0 采样；两条 queue 不会共同 present 同一个 App Window 帧。

## VulkanManager：共享 device，分别持有 Skia context

`VulkanManager` 通过进程内弱引用缓存，让 RenderThread 与上传线程复用仍然存活的 Vulkan device。弱引用不延长对象生命周期，但可以在对象仍存活时取得它。下面的代码展示实例获取规则：

```cpp
static wp<VulkanManager> sWeakInstance = nullptr;
static std::mutex sLock;

sp<VulkanManager> VulkanManager::getInstance() {
    std::lock_guard _lock{sLock};
    sp<VulkanManager> manager = sWeakInstance.promote();
    if (!manager.get()) {
        manager = new VulkanManager();
        sWeakInstance = manager;
    }
    return manager;
}
```

RenderThread、`VkUploader` 以及各 `GrDirectContext` 会持有强引用，确保使用期间 manager 不被销毁；`createContext()` 还通过 context delete callback 增减 `VulkanManager` 的强引用。只要上传 context 仍存活，RenderThread 即使释放自己的引用，也不会另建一份 manager。所有强引用都释放后，下一次 `getInstance()` 才会创建新实例。

共享范围包括：

- `VkInstance`；
- `VkPhysicalDevice`；
- `VkDevice`；
- graphics queue family index；
- 已启用的 Vulkan extension 与 feature 信息。

隔离范围包括：

- RenderThread 和 UploadThread 各自的 `GrDirectContext`；
- 两个 context 各自创建的 Skia Vulkan memory allocator（GPU 内存分配器）；
- device-lost（Vulkan 设备不可继续使用）回调中的上下文标签；
- queue 0 与 queue 1 各自的提交顺序。

`SkiaVMA::Options{.fThreadSafe = false}` 只表示每个 context 的 allocator 不负责协调多线程并发访问，不能推导整个 `VkDevice` 无需跨线程同步。共享 Vulkan 对象、queue 和跨 queue 资源依赖仍要遵守 external synchronization（由调用方避免并发访问同一对象），并使用 semaphore 或 fence 表达执行依赖。

## 两条 graphics queue 如何创建

### 同一 queue family，两个 queue index

`setupDevice()` 选中第一个带 `VK_QUEUE_GRAPHICS_BIT` 的 family，并要求该 family 至少提供两个 queue。下面的缩写代码保留能力检查、请求数量和取得 queue handle 的关键点：

```cpp
constexpr uint32_t kRequestedQueueCount = 2;

for (uint32_t i = 0; i < queueFamilyCount; i++) {
    if (queueProps[i].queueFamilyProperties.queueFlags & VK_QUEUE_GRAPHICS_BIT) {
        mGraphicsQueueIndex = i;
        LOG_ALWAYS_FATAL_IF(
            queueProps[i].queueFamilyProperties.queueCount < kRequestedQueueCount);
        break;
    }
}

VkDeviceQueueCreateInfo queueInfo{
    .queueFamilyIndex = mGraphicsQueueIndex,
    .queueCount = kRequestedQueueCount,
    .pQueuePriorities = queuePriorities,
};

mGetDeviceQueue(mDevice, mGraphicsQueueIndex, 0, &mGraphicsQueue);
mGetDeviceQueue(mDevice, mGraphicsQueueIndex, 1, &mAHBUploadQueue);
```

两条 queue 具有相同 capability 和同一个 family index，因此跨 queue 使用资源时不涉及 queue-family ownership 转移。`setupDevice()` 没有在 queue 数量不足时复用 queue 0 的分支；HWUI 一旦进入这段 Vulkan device 初始化，能力不满足会触发 fatal 并中止进程。是否选择 Vulkan 后端由更上层的设备配置与进程策略决定，所以这段代码不能证明所有 Android 17 设备都会启动 Vulkan HWUI。

### 两个 Skia context 绑定不同 queue

`createContext(ContextType)` 把同一组 device 信息交给 Skia，只替换 `fQueue`：

- `kRenderThread` → `mGraphicsQueue`；
- `kUploadThread` → `mAHBUploadQueue`。

直接效果是分开主机侧提交顺序：硬件位图上传不会进入 RenderThread 所用 queue 的同一顺序链。实际性能收益仍取决于驱动和硬件：

- GPU 有可重叠的 copy/graphics 执行资源时，上传可能与窗口绘制部分重叠；
- 两条 queue 争用内存带宽、cache 或同一图形引擎时，驱动可能交错甚至串行；
- AHardwareBuffer 上传涉及的分配、页映射和 cache 维护也可能拖慢窗口渲染；
- 两条 queue 使用同一个 global priority 请求，queue 1 没有天然的低优先级。

双 queue 提供的是独立提交能力，并减少同一 queue 内的顺序约束。它不保证硬件并行，也不能隔离上传引起的全部资源争用。

## HardwareBitmapUploader：上传隔离不等于异步返回

### CPU 像素会被复制

`Bitmap.Config.HARDWARE` 的这条创建路径先分配带 `AHARDWAREBUFFER_USAGE_GPU_SAMPLED_IMAGE` 的 AHardwareBuffer，再调用 `SkImages::TextureFromAHardwareBufferWithData()` 把 `SkPixmap` 数据写入。`Bitmap.cpp` 也明确把 `allocateHardwareBitmap()` 描述为复制 bitmap contents。

因此，这条路径不属于已有像素直接变成 GPU 纹理的 zero-copy。AHardwareBuffer 可以避免后续再创建一份应用可见像素存储，但首次创建仍要把 CPU 源像素传输到 gralloc 分配的图形 buffer。

### GrallocUploadThread 与调用方等待

Vulkan 上传在 `GrallocUploadThread` 上执行：

1. 取得或创建共享 `VulkanManager`；
2. 创建绑定 queue 1 的 `GrDirectContext`；
3. 调用 `TextureFromAHardwareBufferWithData()` 记录上传；
4. 执行 `mGrContext->submit(GrSyncCpu::kYes)`；
5. `runSync()` 返回后，`uploadHardwareBitmap()` 才把结果交回调用方。

`GrSyncCpu::kYes` 表示上传线程会等待 GPU 完成。这样可以保证返回的 hardware bitmap 已经写完，但调用仍是同步的。主线程若同步创建大图，仍可能依次等待解码、AHB（AHardwareBuffer）分配、上传和 GPU 完成。

queue 1 与 queue 0 在这段时间可以分别提交工作。GPU 资源争用是否拉长 RenderThread 的 queue 0 工作，仍要通过 trace 验证。

### 60 秒闲置回收

`HardwareBitmapUploader.cpp` 把 `kThreadTimeout` 设为 60000 ms。没有 pending upload（待处理上传）且空闲时间超过该值后，`VkUploader::onIdle()` 会释放上传 `GrDirectContext` 与 manager 强引用；下一次上传再按需重建。

源码只能证明上传 context 及其持有资源被释放。具体回收多少 GPU 内存，还取决于驱动、Skia cache、AHardwareBuffer 的其他持有者和设备内存策略，不能写成固定容量。

## Global priority：可选请求，不是实时保证

`Properties::contextPriority` 默认值为 0。只有系统代码在 Vulkan context 创建前通过隐藏的 `HardwareRenderer.setContextPriority()` 设置 EGL priority 常量，`VulkanManager` 才会尝试映射到：

- `VK_QUEUE_GLOBAL_PRIORITY_LOW_EXT`；
- `VK_QUEUE_GLOBAL_PRIORITY_MEDIUM_EXT`；
- `VK_QUEUE_GLOBAL_PRIORITY_HIGH_EXT`。

Android 17 源码仅在 `contextPriority != 0` 且识别到 `VK_EXT_global_priority` v2 时附加 `VkDeviceQueueGlobalPriorityCreateInfoEXT`。如果 global-priority query 可用，代码会先确认选中的 queue family 是否报告了目标档位；不支持时记录 warning，但继续创建 device。

还要注意三点：

- `mAPIVersion` 固定为 Vulkan 1.1；源码检查 `VK_API_VERSION_1_4`，不能证明 HWUI 在 Android 17 使用 Vulkan 1.4 core priority；
- 两条 queue 来自同一个 `VkDeviceQueueCreateInfo`，global priority 请求对这次创建的两条 queue 一起生效；
- global priority 是提交给驱动的队列调度请求，还受系统权限控制。它与 Linux 线程实时优先级无关，也不承诺具体的 GPU 抢占时延。

## 两种“帧边界”记录不同对象

### Vulkan frame-boundary 是 GPU 工具标记

Android 17 的 `finishFrame()` 在提交 Skia 工作时有两条帧标记路径：

1. AGI capture layer 提供私有 `VK_ANDROID_frame_boundary` 时，HWUI 把本帧的 signal semaphore（GPU 完成相应工作时置为已触发的同步对象）和 render-target image 传给 `vkFrameBoundaryANDROID()`；
2. 该私有入口不存在时，HWUI 设置 `GrSubmitInfo.fMarkBoundary = Yes` 与进程内递增的 `fFrameID`，由 Skia 和可用的 `VK_EXT_frame_boundary` 支持向工具描述 frame boundary。

Khronos `VK_EXT_frame_boundary` 给 queue submission 附加应用定义的 frame ID、结果 image/buffer 和工具 tag。它是 profiling annotation（供分析工具使用的元数据），不会创建新的执行依赖，也不能替代 present semaphore。

`VK_ANDROID_frame_boundary` 在 AOSP 头文件中被明确描述为 AGI 专用扩展，由 AGI Vulkan capture layer 在抓帧时提供。普通运行时查不到该 proc pointer（Vulkan 函数入口指针）属于预期情况。

### FrameTimeline 是窗口 present 时间线

FrameTimeline 的 `vsyncId` 走另一条路径。`CanvasContext::draw()` 取得 `FrameTimelineVsyncId`，构造 `ANativeWindowFrameTimelineInfo`，再由 render pipeline 在 `queueBuffer()` 前设置给 ANativeWindow。SurfaceFlinger 用它关联 App `SurfaceFrame` 和显示 `DisplayFrame` 的 expected/actual 时间线。

两类 ID 的差异如下：

| 对象 | 生成位置 | 主要消费者 | 是否直接表示 expected present |
| --- | --- | --- | --- |
| Vulkan `currentFrameID` | HWUI `VulkanManager::finishFrame()` 的进程内计数器 | Skia、Vulkan 工具、AGI capture | 否 |
| FrameTimeline `vsyncId` | Choreographer / 平台帧时间线传入 HWUI | ANativeWindow、SurfaceFlinger、Perfetto FrameTimeline | 是 |
| BufferQueue frame number | Producer queue 次序 | BLAST、SurfaceFlinger、transaction/trace | 不单独表示 |

AOSP 没有把 `currentFrameID` 赋值为 `FrameTimelineVsyncId`。工具可以根据时间、submission、render target 或其他元数据关联两者，但不能假设二者数值相同。

### Frame boundary 也不等于 present

Vulkan frame-boundary 标记发生在 queue submission 附近，离屏幕显示仍有以下步骤：

- GPU 完成对窗口 image 的写入；
- producer completion fence signal；
- `ANativeWindow::queueBuffer()`；
- BLAST buffer transaction；
- SurfaceFlinger latch；
- HWC DEVICE 或 RenderEngine CLIENT 合成；
- display present。

GPU 工具把 draw call 归到某帧，只能回答这些 GPU 命令属于哪组提交工作。用户何时看到结果，仍要结合 FrameTimeline 与 present fence 判断。

## dequeue fence 与 producer completion fence

### dequeue fence：等待旧消费者释放 buffer

`VulkanSurface::dequeueNativeBuffer()` 从 App Window 的 ANativeWindow 取得 buffer 和 dequeue fence。该 fence 表示 Consumer（buffer 消费方）何时结束对这块旧 buffer 的使用；Producer（buffer 生产方）要等它 signal 后才能安全复用并写入。

当 fence 尚未 signal 时，`VulkanManager::dequeueNextBuffer()` 会尝试：

1. `dup()` fence fd；
2. 创建 `VkSemaphore`；
3. 以 `VK_EXTERNAL_SEMAPHORE_HANDLE_TYPE_SYNC_FD_BIT` 和 `VK_SEMAPHORE_IMPORT_TEMPORARY_BIT` 把 fd 临时导入 semaphore；
4. 让 Skia surface 的后续 GPU 工作等待该 semaphore；
5. 立即调用 `FlushAndSubmit()`，确保 wait 真正进入 GPU submission。

导入或创建失败时，源码改由 CPU 调用 `sync_wait()`。这条 fence 的方向是 Consumer/HWC 把旧 buffer 释放给 App Producer 复用，并非 SurfaceFlinger 作为 Producer 通知 App 新内容已经准备好。

### finishFrame：导出本轮 GPU 完成 fence

queue 0 的窗口绘制工作准备提交时，`finishFrame()` 创建可导出为 sync-fd 的 semaphore，并把它放入 `GrFlushInfo.fSignalSemaphores`。flush/submit 后，代码通过 `vkGetSemaphoreFdKHR()` 取得 fd。sync-fd 是用户空间传递内核 `dma_fence` 的文件描述符封装。`VulkanSurface::presentCurrentBuffer()` 再把这个 fd 传给 `ANativeWindow::queueBuffer()`。

这个 fd 在 BufferQueue 消费侧成为当前 buffer 的 acquire fence。SurfaceFlinger 可以先接收 buffer 元数据，但读取像素前必须等待 fence signal，确认 GPU 已经写完。`presentCurrentBuffer()` 的函数名容易误导；这里执行的是 queue buffer，还没有完成屏幕 present。

创建可导出 semaphore 失败、导致 `sharedSemaphore` 为空时，`finishFrame()` 会调用 `mQueueWaitIdle(mGraphicsQueue)`，保守地等待 queue 0 空闲。若 GPU 已成功提交，只有后续 `vkGetSemaphoreFdKHR()` 导出 fd 失败，Android 17 源码只记录错误并返回无效 fd。这两类失败不能合并成同一条 fallback。正常路径无需 RenderThread 在 CPU 上等待整帧 GPU 完成。

下面的时序图按 buffer 所有权变化标出 fence 方向：

```mermaid
sequenceDiagram
    participant BQ as "ANativeWindow / BufferQueue"
    participant RT as "RenderThread"
    participant VK as "VkQueue 0 / GPU"
    participant SF as "SurfaceFlinger"
    participant D as "HWC / Display"

    BQ-->>RT: "dequeueBuffer(buffer, release/dequeue fence)"
    RT->>VK: "import fence as wait semaphore"
    RT->>VK: "Skia draw + signal exportable semaphore"
    VK-->>RT: "export sync_fd（producer completion）"
    RT->>BQ: "queueBuffer(buffer, sync_fd)"
    BQ-->>SF: "buffer + acquire fence"
    SF->>D: "latch / compose / present"
    D-->>BQ: "release fence for later reuse"
```

由此可以解释两个现象：`queueBuffer()` 可以在 GPU 完成前返回；下一次 `dequeueBuffer()` 也可能因旧 buffer 仍被 GPU/HWC 使用而等待。

## Buffer age 与 partial update

当 `Properties::enablePartialUpdates` 和 `Properties::useBufferAge` 同时开启时，`VulkanManager` 使用 `SwapBehavior::BufferAge`。buffer age 表示一块 buffer 距离上次成功入队经历了多少次窗口提交。`VulkanSurface` 根据本进程的 present count 与该 buffer 上次成功 queue 的 count 计算 age；新 buffer、内容无效或 transform 改变时返回 0。

HWUI 会结合 buffer age 与 swap history，计算本次需要恢复的 damage（发生变化、需要更新的区域），再通过 `native_window_set_surface_damage()` 把窗口 damage 交给 ANativeWindow。这里有三个限制：

- buffer age 只表示内容可复用历史，不能保证系统仅执行脏矩形内的 GPU 指令；
- age 为 0 时需要按完整内容处理；
- driver、tile 架构、offscreen layer、blend 和 SurfaceFlinger 合成仍会影响最终带宽。

因此，partial update 的收益要结合 GPU counter、render stage 与功耗数据评估。`bufferAge != 0` 本身不能证明 fill rate（每秒实际填充的像素量）已按 damage 面积同比例下降。

## VkFunctor 只说明 WebView 私有互操作

`getVkFunctorInitParams()` 会向 HWUI 的 WebView Vulkan functor 回调提供 `VkInstance`、`VkPhysicalDevice`、`VkDevice`、queue 0、queue family index 和已启用的 feature/extension。这里的 functor 是 WebView 与 HWUI 之间的私有绘制回调对象；`VkFunctorDrawable` 明确持有 `WebViewFunctor::Handle`，并在 RenderThread 上调用它。

这不是面向普通应用的通用 Vulkan 接口，也不能让 SurfaceView 的自定义渲染自动复用 HWUI device。普通 native renderer 无法据此取得 HWUI 私有 device；应用应通过公开 Vulkan/ANativeWindow API 管理自己的 instance、device、queue 与同步对象。

## 与 SkiaGL 的正确比较方式

一种常见误解是 SkiaGL 只有一个 context，因此 hardware bitmap 上传必然与 RenderThread 串行。Android 17 的 `HardwareBitmapUploader` 在 GL 路径同样使用独立的 `EGLUploader`、`GrallocUploadThread` 与 EGL context，并通过 EGL fence 等待上传完成。

两种后端的可观察差异应这样描述：

| 维度 | SkiaVulkan | SkiaGL |
| --- | --- | --- |
| HWUI 明确管理的提交对象 | 同一 VkDevice 上两条 graphics `VkQueue` | RenderThread 与 uploader 各自的 EGL/GL context；驱动内部 queue 拓扑不可由 GL API 直接得知 |
| AHB 上传完成等待 | UploadThread `GrSyncCpu::kYes` | UploadThread `eglClientWaitSyncKHR()` |
| 窗口完成 fence | Vulkan semaphore 导出 sync fd | EGL/GL native fence 路径 |
| GPU frame annotation | 可使用 `VK_EXT_frame_boundary` 或 AGI 私有扩展 | 依赖 GL/驱动/工具支持，不能概括成“无分析能力” |
| 是否保证上传与绘制并行 | 否 | 否 |

Vulkan API 会显式表达 queue、semaphore 与外部句柄之间的关系，便于建立同步证据，但同一负载不会因此自动变快。性能对比仍需固定设备、内容、刷新率与热状态。

## 性能观测：分清 queue、GPU 与 present

### Perfetto

建议同时采集以下证据，并用 submission ID、时间区间和 frame token（关联同一帧的标识）串起各数据源：

- Main thread 与 RenderThread 调度、`syncAndDrawFrame`、`Vulkan finish frame`、`flush commands`；
- `GrallocUploadThread` 的 hardware bitmap 上传 slice；
- `dequeueBuffer` / `queueBuffer` duration；
- FrameTimeline expected/actual 与 jank type；
- `gpu.renderstages`：设备 producer 支持时，可以通过 `hw_queue_iid`、context、submission ID 与 render stage 查看 GPU 活动；
- `gpu.counters`：设备支持时查看频率、busy、带宽、cache 等计数器；
- GPU/DRM ftrace 与 dma-buf/fence 事件：用来判断驱动调度和 fence 等待。

Perfetto 的 GPU data source 由设备或驱动侧 producer（向 Perfetto 写入 trace 数据的组件）提供，名称可能带 `.adreno`、`.mali` 等后缀，可用字段也因设备而异。HWUI 创建两条 `VkQueue`，不保证 trace 会显示两条可独立命名的硬件 queue。

### AGI

AGI frame profiling 可以检查单帧中的 Vulkan API call、render pass、shader、texture、pipeline state 与资源。抓取 HWUI 渲染时，`VK_ANDROID_frame_boundary` 由 AGI capture layer 注入，用于帮助工具划分窗口帧。

AGI 适合解释单帧 GPU 命令做了什么，但不能替代系统 trace。FrameTimeline、BufferQueue、SurfaceFlinger、HWC 与 present timing 仍要通过 Perfetto、dumpsys 或厂商显示工具观察。

### 常见症状与证据

| 症状 | 先看 | 避免的误判 |
| --- | --- | --- |
| hardware bitmap 创建卡住调用线程 | decode、AHB allocation、GrallocUploadThread、`GrSyncCpu` wait | 看到 queue 1 就认定调用异步返回 |
| RenderThread 慢且 upload 同期发生 | queue 0/1 submission、GPU busy、带宽、频率、调度 | 把两个 queue 直接当成两套 GPU 引擎 |
| `dequeueBuffer` 长等待 | 上一轮 release fence、buffer 数量、SF/HWC/GPU 使用期 | 直接归因于 Vulkan command recording |
| `queueBuffer` 按时但帧晚 | acquire fence、SF latch、composition、present | 把 queue 时间当上屏时间 |
| AGI 有清晰 frame boundary，Perfetto token 对不上 | Vulkan frame ID 与 FrameTimeline vsyncId 分开对齐 | 假设两个 ID 数值相同 |
| partial update 开启但 GPU 仍重 | buffer age、damage、offscreen layer、overdraw、tile load/store | 认为 surface damage 会裁掉所有上游工作 |

## 版本演进

下表只陈述固定 release tag 对照能够证明的结果：

| 平台标签 | 双 graphics queue | frame-boundary 相关代码 | global-priority 相关代码 |
| --- | --- | --- | --- |
| `android-14.0.0_r1` | 已有 queue 0 + AHB upload queue 1 | 本次对照未见 Android 17 形态的 boundary 分支 | 已有 `VK_EXT_global_priority` 请求 |
| `android-15.0.0_r1` | 保持双 queue | 本次对照未见 Android 17 形态的 boundary 分支 | 保持 extension 请求 |
| `android-16.0.0_r1` | 保持双 queue | 已有 `VK_EXT_frame_boundary`、AGI 私有扩展与 `fFrameID` | 增加 global-priority query/KHR 相关处理 |
| `android-17.0.0_r1` | 保持双 queue | 保持两条 boundary 路径 | 保持 query 与不支持时的降级处理 |

这张表可以说明 Android 17 固定 tag 中有哪些实现，也能证明双 queue 至少在 Android 14 基线已经存在。若要定位某个提交首次进入主线，还需继续检查相关开发分支与 Git history，不能只根据四个 release tag 推断精确日期。

## 源码核对索引

- [`VulkanManager.cpp`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/libs/hwui/renderthread/VulkanManager.cpp) / [`VulkanManager.h`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/libs/hwui/renderthread/VulkanManager.h)：device、两条 queue、context、global priority、frame boundary、fence 导入导出；
- [`HardwareBitmapUploader.cpp`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/libs/hwui/HardwareBitmapUploader.cpp) / [`Bitmap.cpp`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/libs/hwui/hwui/Bitmap.cpp)：GL/Vulkan 上传线程、首次内容复制、CPU 等待与 60 秒 idle timeout；
- [`SkiaVulkanPipeline.cpp`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/libs/hwui/pipeline/skia/SkiaVulkanPipeline.cpp)：dequeue、draw、finishFrame、swapBuffers 的调用关系；
- [`VulkanSurface.cpp`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/libs/hwui/renderthread/VulkanSurface.cpp)：ANativeWindow buffer、dequeue fence、buffer age、surface damage 与 queueBuffer；
- [`CanvasContext.cpp`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/libs/hwui/renderthread/CanvasContext.cpp)：FrameTimeline info、damage history、dequeue/queue duration；
- 历史标签：[`android-14.0.0_r1`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-14.0.0_r1/libs/hwui/renderthread/VulkanManager.cpp)、[`android-15.0.0_r1`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-15.0.0_r1/libs/hwui/renderthread/VulkanManager.cpp)、[`android-16.0.0_r1`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-16.0.0_r1/libs/hwui/renderthread/VulkanManager.cpp)：双 queue、frame-boundary 与 global-priority query 的版本对照；
- [Khronos `VkFrameBoundaryEXT`](https://registry.khronos.org/vulkan/specs/latest/man/html/VkFrameBoundaryEXT.html)：Vulkan frame annotation 的规范语义；
- [内核 `dma-fence.c`](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/drivers/dma-buf/dma-fence.c) / [`sync_file.c`](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/drivers/dma-buf/sync_file.c)：`android17-6.18-2026-06_r6` 的 fence 与 sync-file 边界；
- [Perfetto GPU data sources](https://perfetto.dev/docs/data-sources/gpu)：GPU counter、render stage 与设备 producer 的观察口径；
- [Perfetto FrameTimeline](https://perfetto.dev/docs/data-sources/frametimeline)：expected/actual 时间线与 jank 分类；
- [AGI Frame Profiler](https://developer.android.com/agi/frame-trace/frame-profiler)：单帧 Vulkan/GL 调用和 GPU 资源分析。

上述平台源码均固定在 `android-17.0.0_r1`。内核侧采用 `android17-6.18-2026-06_r6`，只用于解释线程调度、GPU driver、dma-buf 与 fence 机制。厂商 driver 的具体调度行为不能写成 AOSP HWUI 保证。

## 总结

Android 17 HWUI Vulkan 的双 queue 架构可以概括为四点：

1. queue 0 供 RenderThread 生成 App Window 帧，queue 1 供 GrallocUploadThread 上传 hardware bitmap；
2. 两条 queue 共享 VkDevice，但使用独立 Skia context 与 allocator，可以独立提交，不能保证硬件同时执行；
3. Vulkan frame-boundary 是 GPU 工具标记，FrameTimeline `vsyncId` 才关联窗口的 expected/actual present；
4. dequeue fence 保护旧 buffer 的安全复用，`queueBuffer()` 携带的 producer completion fence 保护 SurfaceFlinger 的安全读取，二者方向相反。

分析问题时，应把 RenderThread、GrallocUploadThread、两条 queue、GPU completion fence、BufferQueue、FrameTimeline 与 present 放进同一时间区间。queue 数量只能说明可独立提交的接口结构，无法单独判断硬件并行度、卡顿原因或用户看到帧的时刻。
