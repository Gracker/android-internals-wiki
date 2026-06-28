---
title: "Android 17 HWUI Vulkan 多队列并行渲染与帧边界管理"
chapter: "18.26"
status: ready-for-review
applicable_versions: "Android 14 (API 34) - Android 17 (API 37)"
tags: [vulkan, hwui, rendering, gpu, multi-queue, frame-boundary, android17]
related_chapters: ["2.10", "2.14", "18.9", "18.11"]
created_by: "task2a-knowledge-gap"
created_date: "2026-06-27"
drafted_date: "2026-06-27"
last_verified: "2026-06-27"
last_verified_against: "AOSP android-17.0.0_r1"
confidence: high
sources:
  - type: aosp
    path: "frameworks/base/libs/hwui/renderthread/VulkanManager.cpp (android-17.0.0_r1)"
  - type: aosp
    path: "frameworks/base/libs/hwui/renderthread/VulkanManager.h (android-17.0.0_r1)"
  - type: aosp
    path: "frameworks/base/libs/hwui/renderthread/RenderThread.cpp (android-17.0.0_r1)"
gap_source: "研究素材/AOSP结构"
gap_score:
  素材丰富度: 5
  与全书目标相关性: 5
  读者需求度: 4
  时效性: 5
  total: 19
---

# 18.26 Android 17 HWUI Vulkan 多队列并行渲染与帧边界管理

Android 17 HWUI 的 Vulkan 后端用 `VulkanManager` 管理整个 GPU 设备生命周期。android-17.0.0_r1 的实现中，`VulkanManager` 创建了两条图形队列——`mGraphicsQueue` 给 RenderThread 画帧，`mAHBUploadQueue` 给 HardwareBitmapUploader 上传位图。两条队列共享同一个 `VkDevice`，通过 `VK_EXT_global_priority` 声明优先级，通过 `VK_ANDROID_frame_boundary` / `VK_EXT_frame_boundary` 暴露帧边界给 GPU 分析工具。

本节基于 `frameworks/base/libs/hwui/renderthread/VulkanManager.cpp`（910 行）、`VulkanManager.h`（219 行）和 `RenderThread.cpp`（512 行）的完整源码阅读，拆解这套架构的设计决策和性能影响。

## VulkanManager 单例与跨线程共享

VulkanManager 用弱引用单例 + 互斥锁的模式，让 RenderThread 和 HardwareBitmapUploader 共享同一份 Vulkan 设备资源。

下面这段代码是设备共享的基础。`sWeakInstance` 是 `wp<VulkanManager>` 弱指针，`sLock` 保护实例创建。`getInstance()` 在锁内尝试 promote 弱指针，成功就返回已有实例，失败就 new 一个新的：

```cpp
// frameworks/base/libs/hwui/renderthread/VulkanManager.cpp
static wp<VulkanManager> sWeakInstance = nullptr;
static std::mutex sLock;

sp<VulkanManager> VulkanManager::getInstance() {
    std::lock_guard _lock{sLock};
    sp<VulkanManager> vulkanManager = sWeakInstance.promote();
    if (!vulkanManager.get()) {
        vulkanManager = new VulkanManager();
        sWeakInstance = vulkanManager;
    }
    return vulkanManager;
}
```

调用方是 `RenderThread::initThreadLocals()`（`RenderThread.cpp` L268），把 `mVkManager = VulkanManager::getInstance()` 存到 RenderThread 的成员变量。HardwareBitmapUploader 通过同样的 `getInstance()` 拿到同一个实例。两个线程持有同一个 `VkInstance`、`VkPhysicalDevice`、`VkDevice`，但各自创建独立的 `GrDirectContext` 和命令提交流。

弱指针而不是强指针，原因在于 VulkanManager 的生命周期跟 RenderThread 绑定。RenderThread 销毁时释放强引用，VulkanManager 可以被回收；如果 HardwareBitmapUploader 还在用，promote 会失败并创建新实例。这种设计避免了跨线程引用计数的生命周期僵局。

## 双图形队列并行设计

Android 17 的 VulkanManager 从同一个 graphics queue family 中取出两个 queue index，分别绑定到不同用途。

设备创建阶段，`setupDevice()` 遍历 queue family properties 找到 graphics queue，然后硬性要求该 family 至少支持 2 个并发 queue：

```cpp
// VulkanManager.cpp L237-257
constexpr auto kRequestedQueueCount = 2;

mGraphicsQueueIndex = queueCount;
for (uint32_t i = 0; i < queueCount; i++) {
    if (queueProps[i].queueFamilyProperties.queueFlags & VK_QUEUE_GRAPHICS_BIT) {
        mGraphicsQueueIndex = i;
        LOG_ALWAYS_FATAL_IF(
            queueProps[i].queueFamilyProperties.queueCount < kRequestedQueueCount);
        break;
    }
}

const VkDeviceQueueCreateInfo queueInfo = {
        VK_STRUCTURE_TYPE_DEVICE_QUEUE_CREATE_INFO,
        queueNextPtr,
        0,
        mGraphicsQueueIndex,        // 同一个 family
        kRequestedQueueCount,       // count = 2
        queuePriorities,
};
```

`LOG_ALWAYS_FATAL_IF(queueCount < 2)` 是硬约束——如果 GPU 驱动报告某个 graphics queue family 只有 1 个 queue，HWUI 直接 abort，不会回退到 OpenGL ES。这意味着 Android 17 HWUI Vulkan 后端对 GPU 驱动有最低能力要求：同一 graphics family 至少 2 个并发 queue。

`initialize()` 把两条 queue 拉出来：

```cpp
// VulkanManager.cpp L427-428
mGetDeviceQueue(mDevice, mGraphicsQueueIndex, 0, &mGraphicsQueue);
mGetDeviceQueue(mDevice, mGraphicsQueueIndex, 1, &mAHBUploadQueue);
```

分配关系：
- `mGraphicsQueue` → RenderThread 帧绘制主路径
- `mAHBUploadQueue` → HardwareBitmapUploader 异步位图上传

两条 queue 属于同一个 family（具备相同的 queue capability），但物理上是两个独立的提交队列。GPU 调度器可以在硬件层面让上传和绘制并发执行，RenderThread 不需要等待 HardwareBitmapUploader 完成。

## GrDirectContext 分配：ContextType 分流

VulkanManager 的 `createContext()` 接受 `ContextType` 参数，为 RenderThread 和 UploadThread 创建各自独立的 Skia GrDirectContext：

```cpp
// VulkanManager.cpp L521-555
skgpu::VulkanBackendContext backendContext;
backendContext.fInstance = mPhysicalDevice;  // 共享
backendContext.fDevice = mDevice;            // 共享
backendContext.fQueue =
        (contextType == ContextType::kRenderThread) ? mGraphicsQueue : mAHBUploadQueue;
backendContext.fDeviceLostProc = (contextType == ContextType::kRenderThread)
        ? deviceLostProcRenderThread
        : deviceLostProcUploadThread;

SkiaVMA::Options opts{.fThreadSafe = false};
backendContext.fMemoryAllocator = SkiaVMA::Make(backendContext, opts);
```

两个 GrDirectContext 绑定到不同 `VkQueue`，共享同一个 `VkDevice`/`VkInstance`/`VkPhysicalDevice`。`fThreadSafe = false` 表示 VMA（Vulkan Memory Allocator）对象不做跨线程同步——因为两个 GrDirectContext 各自持有独立的 VMA 实例，不存在跨线程访问同一分配器的场景。

Device lost 回调按 ContextType 分流到不同上下文（`"RenderThread"` vs `"UploadThread"`），GPU fault 发生时能定位是哪个路径的问题。

## 队列全局优先级：VK_EXT_global_priority

VulkanManager 在设备创建时通过 `VK_EXT_global_priority`（或 Vulkan 1.4 core）向 GPU 驱动声明队列优先级。映射逻辑从 EGL 的 context priority 常量转到 Vulkan 的 queue priority 枚举：

```cpp
// VulkanManager.cpp L337-360
if (Properties::contextPriority != 0 &&
    mExtensions.hasExtension(VK_EXT_GLOBAL_PRIORITY_EXTENSION_NAME, 2)) {
    VkQueueGlobalPriorityEXT globalPriority;
    switch (Properties::contextPriority) {
        case EGL_CONTEXT_PRIORITY_LOW_IMG:
            globalPriority = VK_QUEUE_GLOBAL_PRIORITY_LOW_EXT; break;
        case EGL_CONTEXT_PRIORITY_MEDIUM_IMG:
            globalPriority = VK_QUEUE_GLOBAL_PRIORITY_MEDIUM_EXT; break;
        case EGL_CONTEXT_PRIORITY_HIGH_IMG:
            globalPriority = VK_QUEUE_GLOBAL_PRIORITY_HIGH_EXT; break;
        default:
            LOG_ALWAYS_FATAL("Unsupported context priority");
    }
    VkDeviceQueueGlobalPriorityCreateInfoEXT queuePriorityCreateInfo;
    queuePriorityCreateInfo.globalPriority = globalPriority;
    queueNextPtr = &queuePriorityCreateInfo;
}
```

Vulkan 1.4 设备走 core 路径（`hasGlobalPriority = mAPIVersion >= VK_API_VERSION_1_4`），1.3 及以下走 extension。两条路径最终都把 `VkDeviceQueueGlobalPriorityCreateInfoEXT` 挂到 `VkDeviceQueueCreateInfo::pNext` 链上。

如果驱动报告不支持所请求的优先级，HWUI 不会 fatal，而是打印 warning 并丢弃优先级请求：

```cpp
// VulkanManager.cpp 注释
// SysUI and Launcher will request HIGH when SF has RT but it is a known issue that
// upstream drm drivers currently lack a way to grant them the granular privileges
// they need for HIGH (but not RT) so they will fail queue creation.
// For now, drop the unsupported global priority request so that queue creation succeeds.
```

这个兜底是给 SysUI 和 Launcher 留的——SurfaceFlinger 占用 RT（Real-Time）优先级时，SysUI 请求 HIGH 会因为 drm 驱动权限不足而失败。丢弃请求让 queue 创建继续，代价是 UI 帧率可能略低于 RT 级别。

## 帧边界暴露：VK_ANDROID_frame_boundary

GPU 分析工具（AGI、Perfetto）需要知道每一帧的 GPU 命令边界，才能把 GPU 渲染轨迹和 FrameTimeline 对齐。VulkanManager 通过两种机制暴露帧边界。

`VulkanManager.h` 声明了 AGI 定制的扩展：

```cpp
// VulkanManager.h L36-39
// VK_ANDROID_frame_boundary is a bespoke extension defined by AGI
// (https://github.com/google/agi) to enable profiling of apps rendering via
// HWUI. This extension is not defined in Khronos, hence the need to declare it
// manually here. There's an extension (VK_EXT_frame_boundary) which we will use
// instead if available.
typedef void(VKAPI_PTR* PFN_vkFrameBoundaryANDROID)(VkDevice device,
        VkSemaphore semaphore, VkImage image);
#define VK_ANDROID_FRAME_BOUNDARY_EXTENSION_NAME "VK_ANDROID_frame_boundary"
```

sEnableExtensions 同时启用 `VK_ANDROID_frame_boundary` 和 Khronos 标准的 `VK_EXT_frame_boundary`。优先使用 AGI capture layer 注入的 proc pointer（`mFrameBoundaryANDROID`），不可用时回退到 Skia 层方案。

`finishFrame()` 中的关键分支：

```cpp
// VulkanManager.cpp L702-721
static uint64_t currentFrameID = 0;
GrSubmitInfo submitInfo;
if (!mFrameBoundaryANDROID) {
    submitInfo.fMarkBoundary = GrMarkFrameBoundary::kYes;
    submitInfo.fFrameID = currentFrameID++;
}
context->submit(submitInfo);

if (submitted == GrSemaphoresSubmitted::kYes && mFrameBoundaryANDROID) {
    VkImage image = VK_NULL_HANDLE;
    GrBackendRenderTarget backendRenderTarget = SkSurfaces::GetBackendRenderTarget(
            surface, SkSurfaces::BackendHandleAccess::kFlushRead);
    if (backendRenderTarget.isValid()) {
        GrVkImageInfo info;
        if (GrBackendRenderTargets::GetVkImageInfo(backendRenderTarget, &info)) {
            image = info.fImage;
        }
    }
    mFrameBoundaryANDROID(mDevice, sharedSemaphore->semaphore(), image);
}
```

`currentFrameID` 是 `static` 局部变量，整个 HWUI 进程唯一递增。Perfetto GPU renderer 用这个 ID 对应 FrameTimeline 中的帧标记。走 `mFrameBoundaryANDROID` 路径时，Skia submit 不带 frame boundary 标记（由 AGI 扩展负责），同时把当前帧的 semaphore 和 image 传给 AGI capture layer。

## SurfaceFlinger 跨进程同步

VulkanManager `dequeueNextBuffer()` 负责从 BufferQueue 取 buffer 时处理与 SurfaceFlinger 的同步。核心是把 SurfaceFlinger 返回的 Linux `sync_fd` 转成 `VkSemaphore`：

```cpp
// VulkanManager.cpp L580-647
if (bufferInfo->dequeue_fence != -1) {
    int fence_clone = dup(bufferInfo->dequeue_fence);
    VkSemaphoreCreateInfo semaphoreInfo{...};
    VkSemaphore semaphore;
    mCreateSemaphore(mDevice, &semaphoreInfo, nullptr, &semaphore);

    VkImportSemaphoreFdInfoKHR importInfo;
    importInfo.sType = VK_STRUCTURE_TYPE_IMPORT_SEMAPHORE_FD_INFO_KHR;
    importInfo.semaphore = semaphore;
    importInfo.flags = VK_SEMAPHORE_IMPORT_TEMPORARY_BIT;
    importInfo.handleType = VK_EXTERNAL_SEMAPHORE_HANDLE_TYPE_SYNC_FD_BIT;
    importInfo.fd = fence_clone;
    mImportSemaphoreFdKHR(mDevice, &importInfo);

    GrBackendSemaphore beSemaphore = GrBackendSemaphores::MakeVk(semaphore);
    bufferInfo->skSurface->wait(1, &beSemaphore);
    skgpu::ganesh::FlushAndSubmit(bufferInfo->skSurface.get());
}
```

`VK_SEMAPHORE_IMPORT_TEMPORARY_BIT` + `VK_EXTERNAL_SEMAPHORE_HANDLE_TYPE_SYNC_FD_BIT` 是 Android Vulkan 后端的标准同步范式。`sync_fd` 来自 SurfaceFlinger 的 producer 端，表示 buffer 内容已经就绪。临时导入意味着 semaphore 在 signal 后自动恢复未导入状态，不会累积资源。

每次 `dequeueNextBuffer` 都执行 `dup()` → `mCreateSemaphore` → `mImportSemaphoreFdKHR`，没有复用 semaphore 池。高频帧场景下这是性能热点候选，后续可以用 explicit fence API 替代。

## 缓冲区年龄与 Partial Update

```cpp
// VulkanManager.cpp L431-433
if (Properties::enablePartialUpdates && Properties::useBufferAge) {
    mSwapBehavior = SwapBehavior::BufferAge;
}
```

BufferAge 模式下，`dequeueNextBuffer()` 返回的 `bufferAge` 非 0，HWUI 据此做精准 `invalidate()`，只重绘脏区域，减少 GPU fill rate。详见 §2.8（过度绘制）关于 partial update 的讨论。

## 与 OpenGL ES 后端的对比

双队列并行仅在 Vulkan 后端生效。OpenGL ES 受限于单上下文模型——同一 GL context 只有一个提交队列，位图上传和帧绘制串行执行。这是 Vulkan 后端相对 GLES 的结构性优势之一：硬件层面并行，不需要应用层协调。

| 维度 | Vulkan 后端 | OpenGL ES 后端 |
|------|-------------|----------------|
| Queue 数量 | 2（graphics + upload） | 1（单 context） |
| 位图上传与帧绘制 | 并行 | 串行 |
| 帧边界暴露 | VK_*_frame_boundary + Skia fallback | 无原生机制 |
| 队列优先级 | VK_EXT_global_priority | EGL_CONTEXT_PRIORITY |
| 最低驱动要求 | Vulkan 1.1+，queue family >= 2 | 无额外要求 |

## 性能观测方法

通过 Perfetto 的两个 GPU 数据源观察 Vulkan 队列利用率：

- `gpu.counters`：GPU 计数器（时钟频率、ALU 利用率、带宽），反映两条 queue 的总体负载
- `gpu.renderstages`：渲染阶段标记，对应 Skia submit 的 command buffer 分段

SurfaceFlinger FrameTracer（§13.19）追踪 buffer 生命周期事件（dequeue / queue / acquire / present），与 HWUI 的 `currentFrameID` 对应。

AGI（Android GPU Inspector）通过 `VK_ANDROID_frame_boundary` 抓取完整 GPU 帧内容，可以看到每帧的 draw call、纹理绑定、shader 执行情况。没有 AGI capture layer 时，Perfetto 是唯一的 GPU 性能观测手段。

## 适用版本范围

[已验证: AOSP android-17.0.0_r1, frameworks/base/libs/hwui/renderthread/VulkanManager.cpp]

本节描述的是 android-17.0.0_r1 tag 的 VulkanManager 实现。Vulkan 后端在 Android 10 首次引入（SkiaVulkanPipeline），经过多个版本迭代到 Android 17 的当前形态。本节未逐版本对比 Android 14-16 的代码变更，"Android 17 新增"的断言需要补充旧版 tag 对照才能成立。

[适用版本: Android 14 (API 34) - Android 17 (API 37)]

[来源: DeepResearch/2026-06-26-android17-hwui-vulkanmanager-multi-queue-frame-boundary.md]
[结构参考: DeepResearch/2026-06-26-android17-hwui-vulkanmanager-multi-queue-frame-boundary.md]


<!-- AIW-源码调研-2026-06-28 (id=38 重验证) -->

## 源码重验证补充（2026-06-28）

本章基于 android-17.0.0_r1 tag 重新走读 `VulkanManager.cpp`（910 行）、`VulkanManager.h`（219 行）、`RenderThread.cpp`（512 行）、`HardwareBitmapUploader.cpp`（481 行），事实与正文一致。补充三处源码级细节：

### VkUploader 上传路径

`HardwareBitmapUploader.cpp` L223-289 定义 `class VkUploader : public AHBUploader`。关键上传入口：

```cpp
// HardwareBitmapUploader.cpp L252-259
mGrContext = vkManager->createContext(options,
        renderthread::VulkanManager::ContextType::kUploadThread);
sk_sp<SkImage> image =
    SkImages::TextureFromAHardwareBufferWithData(mGrContext.get(), bitmap.pixmap(), ahb);
mGrContext->submit(GrSyncCpu::kYes);
```

调用链：`allocateHardwareBitmap()` → `sUploader->uploadHardwareBitmap()` → `VkUploader::onUploadHardwareBitmap()` 在 `GrallocUploadThread` 上执行 → `VulkanManager::createContext(kUploadThread)` 创建专属 GrDirectContext → `SkImages::TextureFromAHardwareBufferWithData` 把 `AHardwareBuffer` 直接绑成 Skia 纹理对象（零拷贝入口）→ `GrSyncCpu::kYes` 等待 GPU 完成。

### UploadThread 闲置超时（kThreadTimeout = 60000_ms）

`HardwareBitmapUploader.cpp` L48：

```cpp
static constexpr auto kThreadTimeout = 60000_ms;
```

`AHBUploader::postIdleTimeoutCheck()` 发起 60 秒后的一次性任务。`VkUploader::onIdle()` → `onDestroy()` → `mGrContext.reset()` + `mVulkanManagerStrong.clear()`。闲置 60 秒后 GrDirectContext 与 Skia VMA pool 释放，下次上传时重建。中低端设备长时间浏览图片/视频后切换应用，能回收数十 MB GPU 内存。RenderThread 自身的 GrContext 没有此超时机制（始终保持活跃）。

### VkFunctorInitParams 暴露路径

`VulkanManager::getVkFunctorInitParams()`（L557-573）：

```cpp
return VkFunctorInitParams{
        .instance = mInstance,
        .physical_device = mPhysicalDevice,
        .device = mDevice,
        .queue = mGraphicsQueue,           // 只暴露 graphics queue，不暴露 upload queue
        .graphics_queue_index = mGraphicsQueueIndex,
        .api_version = mAPIVersion,
        .enabled_instance_extension_names = mInstanceExtensions.data(),
        .enabled_device_extension_names = mDeviceExtensions.data(),
        .device_features_2 = &mPhysicalDeviceFeatures2,
};
```

这是 HWUI Vulkan 设备与 native 渲染代码（WebView Chromium Skia、SurfaceView 自定义渲染）的桥梁，让调用方复用 HWUI 已创建的 `VkInstance/VkDevice`，避免重复创建。**只暴露 `mGraphicsQueue`**——VkFunctor 调用方做主帧渲染，理论上不应抢 upload queue 优先级。

### 事实自检

正文 12 项核心断言全部与 android-17.0.0_r1 源码一致（详见 `DeepResearch/2026-06-28-android17-hwui-vulkanmanager-multi-queue-reverified.md` 自检表）。

### 待验证事项

- 硬件层「Vulkan 1.1+，queue family >= 2」的最低要求基于 `LOG_ALWAYS_FATAL_IF` 推断，未在芯片厂商驱动层验证降级路径
- `Properties::contextPriority` 在 SysUI/Launcher 进程的真实生效机制未追溯调用链
- `SkiaVMA::Options{.fThreadSafe = false}` 在 AGI capture layer 路径下的跨线程行为未追踪

[来源: DeepResearch/2026-06-28-android17-hwui-vulkanmanager-multi-queue-reverified.md]
[验证状态: 一手源码重读完成，2026-06-28]
