---
title: Vulkan 原生管线与 HWUI 多队列
chapter: '18.5'
applicable_versions: Android 10 (API 29) - Android 17 (API 37)
section: '18.5'
last_verified: '2026-07-31'
last_verified_against: AOSP android-17.0.0_r1 swapchain.cpp / VP_ANDROID_17_requirements.json / Surface.cpp / BufferQueueProducer.cpp / SurfaceFlinger FrontEnd / HWComposer.cpp / RenderEngine.h / GraphiteVkRenderEngine.cpp / RenderEngineThreaded.cpp + kernel android17-6.18-2026-06_r6 dma-buf.c / sync_file.c / dma-fence.c
confidence: high
tags:
- Vulkan
- VkSwapchainKHR
- Android-WSI
- ANativeWindow
- BufferQueue
- explicit-control
- AVP
- Swappy
- frame-pacing
- VkQueue
- Presentation-Mode
- VK_EXT_present_timing
- vulkan
- hwui
- rendering
- gpu
- multi-queue
- frame-boundary
- android17
related_chapters:
- '2.1'
- '2.5'
- '2.8'
- '2.7'
- '16.1'
- '18.3'
- '18.4'
- '18.6'
sources:
- type: internal-reference
  path: /Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Writer/rendering_pipelines/S08_native_graphics_type.md
  role: Native Graphics 类型边界、Vulkan swapchain、frame pacing、显示后半段与 Perfetto 证据链
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/vulkan/libvulkan/swapchain.cpp
  role: surface capabilities、present modes、AcquireImageANDROID、QueueSignalReleaseImageANDROID、queueBuffer 与 present timing
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/vulkan/vkprofiles/profiles/VP_ANDROID_17_requirements.json
  role: VRA17 适用芯片、父 profile、Vulkan 版本、extension 与 feature 集合
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/libs/gui/Surface.cpp
  role: ANativeWindow dequeue/queue、frame timestamp、present mode 与 fences
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/libs/gui/BufferQueueProducer.cpp
  role: slot、dequeue、queue、outstanding 限制与 backpressure
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/services/surfaceflinger/FrontEnd/
  role: layer state、snapshot 与 transaction readiness
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/services/surfaceflinger/DisplayHardware/HWComposer.cpp
  role: composition strategy、validate、present 与 release fences
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/libs/renderengine/include/renderengine/RenderEngine.h
  role: SurfaceFlinger RenderEngine backend 枚举与 Ganesh 默认值
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/libs/renderengine/skia/GraphiteVkRenderEngine.cpp
  role: Graphite Recording、wait/signal semaphore、submit 与 sync fd 导出
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/libs/renderengine/threaded/RenderEngineThreaded.cpp
  role: SFRenderEnginePolicy、SCHED_FIFO 与 threaded task
- type: kernel
  path: https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/drivers/dma-buf/dma-buf.c
  role: 跨模块共享 buffer 基础
- type: kernel
  path: https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/drivers/dma-buf/sync_file.c
  role: dma-fence 的 sync_file fd 接口
- type: kernel
  path: https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/drivers/dma-buf/dma-fence.c
  role: fence signal、callback 与 wait
- type: official
  path: https://developer.android.com/ndk/guides/graphics/android-vulkan-profile
  role: AVP 2025 的兼容性定位
- type: official
  path: https://developer.android.com/games/develop/vulkan/frame-pacing-extensions
  role: Android 17 VK_EXT_present_timing、VK_KHR_present_id2、swapchain flag 与 fallback
- type: official
  path: https://developer.android.com/games/sdk/frame-pacing
  role: Swappy Vulkan、presentation timing 与 pipeline mode
- type: official
  path: https://developer.android.com/games/develop/vulkan/native-engine-support
  role: surface、swapchain、同步、pre-rotation 与运行时能力查询
- type: official
  path: https://registry.khronos.org/vulkan/specs/latest/html/vkspec.html#fundamentals-threadingbehavior
  role: host access 与 external synchronization 规范
- type: official
  path: https://perfetto.dev/docs/data-sources/frametimeline
  role: SurfaceFrame、DisplayFrame 与 jank 字段
- type: internal-reference
  path: /Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Writer/rendering_pipelines/S01_rendering_types_overview.md
  role: 标准 App Window 从应用生产 buffer 到 SurfaceFlinger、HWC 和 present 的公共基线
- type: internal-reference
  path: /Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Writer/rendering_pipelines/S02_aosp_standard_type.md
  role: Choreographer、UI Thread、RenderThread、BufferQueue 与 FrameTimeline 的标准 HWUI 路径
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/libs/hwui/renderthread/VulkanManager.cpp
  role: VkDevice、双 graphics queue、Skia context、global priority、frame boundary 与 sync-fd 导入导出
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/libs/hwui/renderthread/VulkanManager.h
  role: VulkanManager 对象边界、queue 字段、Vulkan 1.1 上限与 AGI 私有扩展说明
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/libs/hwui/HardwareBitmapUploader.cpp
  role: GL/Vulkan hardware bitmap 上传、GrallocUploadThread、CPU 同步等待与 60 秒闲置回收
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/libs/hwui/hwui/Bitmap.cpp
  role: allocateHardwareBitmap 的内容复制语义
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/libs/hwui/pipeline/skia/SkiaVulkanPipeline.cpp
  role: 窗口 dequeue、draw、finishFrame 与 swapBuffers 的调用顺序
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/libs/hwui/renderthread/VulkanSurface.cpp
  role: ANativeWindow buffer、dequeue fence、buffer age、surface damage 与 queueBuffer
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/libs/hwui/renderthread/CanvasContext.cpp
  role: FrameTimeline 元数据、damage history、dequeue/queue duration 与帧完成时间
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/libs/hwui/Properties.cpp
  role: partial update、buffer age、render pipeline 与 context priority 的属性入口
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/libs/hwui/pipeline/skia/VkFunctorDrawable.cpp
  role: WebView Vulkan functor 在 RenderThread 上的私有互操作边界
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/libs/gui/Surface.cpp
  role: ANativeWindow dequeueBuffer、queueBuffer 与 fence fd 传递
- type: aosp-history
  path: https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-14.0.0_r1/libs/hwui/renderthread/VulkanManager.cpp
  role: Android 14 双 graphics queue 与 global priority 基线
- type: aosp-history
  path: https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-15.0.0_r1/libs/hwui/renderthread/VulkanManager.cpp
  role: Android 15 对照
- type: aosp-history
  path: https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-16.0.0_r1/libs/hwui/renderthread/VulkanManager.cpp
  role: Android 16 frame-boundary 与 global-priority query 对照
- type: specification
  path: https://registry.khronos.org/vulkan/specs/latest/man/html/VkFrameBoundaryEXT.html
  role: VK_EXT_frame_boundary 的 submission annotation 语义
- type: specification
  path: https://registry.khronos.org/vulkan/specs/latest/man/html/VkDeviceQueueCreateInfo.html
  role: 同一 queue family 创建多条 VkQueue 的规范字段
- type: official
  path: https://perfetto.dev/docs/data-sources/gpu
  role: GPU counter 与 render stage 数据源
- type: official
  path: https://perfetto.dev/docs/data-sources/frametimeline
  role: FrameTimeline expected/actual 时间线与 jank 分类
- type: official
  path: https://developer.android.com/agi/frame-trace/frame-profiler
  role: AGI 单帧 Vulkan/GL 调用、资源和 pipeline state 分析
- type: kernel
  path: https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/drivers/dma-buf/dma-fence.c
  role: Android 17 内核 dma_fence 状态、回调与等待基线
- type: kernel
  path: https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/drivers/dma-buf/sync_file.c
  role: sync_file fd 对 dma_fence 的封装与用户空间边界
- type: kernel
  path: https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/kernel/sched/core.c
  role: RenderThread 与上传线程的 CPU 调度基线；不定义 Vulkan queue 的 GPU 执行顺序
status: ready-to-publish
task6_state: reviewed
task9_state: reviewed
task2b_state: fixed
pipeline_stage: ready-to-publish
last_consolidated_at: '2026-08-24'
consolidated_from:
- src/part2-performance/ch18-rendering-pipelines/09-vulkan-native.md
- src/part2-performance/ch18-rendering-pipelines/24-android17-hwui-vulkan-multi-queue.md
---

# Vulkan 原生管线与 HWUI 多队列

Vulkan 把资源、命令和同步的管理责任交给应用，但 Android 的显示后半段仍然存在。App 要通过 `VK_KHR_android_surface`，把代表显示目标的 `VkSurfaceKHR` 连接到 `ANativeWindow`；swapchain image（循环用于渲染和显示的图像）仍映射到 Android GraphicBuffer/BufferQueue，提交后还要经过 SurfaceFlinger、HWC 和 Display present。

本文以 `android-17.0.0_r1` 中的 Android WSI（Window System Integration，Vulkan 与窗口系统的连接层）、SurfaceFlinger/RenderEngine 为平台基线，以 `android17-6.18-2026-06_r6` 中的 dma-buf/dma-fence 为内核基线。Vulkan 驱动和 GPU job scheduler 由设备厂商实现；AOSP 可以说明接口与所有权，却无法代替目标设备回答 GPU 工作何时完成。

Vulkan 应用自行管理实例、设备、交换链、命令缓冲区和同步；HWUI 的 Vulkan 后端则由 framework 组织这些对象。Android 17 多队列优化改变提交并行度，但不改变最终 buffer 和 fence 边界。

## 交换链、命令提交与呈现

### 为什么选择 Vulkan

#### 显式控制带来的价值

OpenGL ES 把较多状态验证、资源转换和同步决策放在驱动中；Vulkan 则要求应用预先描述 pipeline（固定功能与着色器状态组合）、descriptor（着色器访问资源的绑定）、resource usage、command buffer 和执行依赖。组织得当时，Vulkan 可以：

- 降低高 draw-call 场景中的 CPU 驱动开销；
- 把 shader/pipeline 创建从关键帧移到加载或缓存阶段；
- 用多个 command pool（命令缓冲分配池）并行准备命令；
- 精确表达执行依赖、内存可见性和 image layout（图像当前用途对应的状态）；
- 让帧内 GPU 工作和错误更容易通过 Validation Layer/AGI 定位。

这些能力不会自动转化为性能收益。引擎如果频繁创建 pipeline、把提交切得过碎、设置过度保守的 barrier，或者积压太多 in-flight frame（已提交但尚未完成显示的帧），Vulkan 同样会产生较高 CPU 开销、GPU bubble（依赖导致的硬件空闲间隙）和输入延迟。比较 GLES 与 Vulkan 时，应保持内容、分辨率、pacing 和设备温度一致。

#### 应用侧的责任

| 领域 | 应用需要管理的内容 |
|---|---|
| 资源 | 内存 allocation/binding、生命周期、aliasing（内存复用）和预算 |
| 命令 | command pool/buffer、record/reset 和 queue submit |
| 同步 | semaphore、fence、stage/access mask 和 queue ownership |
| 图像 | format、usage、layout、subresource（图像的 mip/layer 子范围）和 compression |
| 窗口 | surface capabilities、swapchain、resize、rotation、present mode |
| 节奏 | 输入采样、目标 present、in-flight 数量和刷新率提示 |
| 恢复 | `OUT_OF_DATE`、`SUBOPTIMAL`、surface lost、device lost |

Validation Layer 能发现许多 API、同步和对象生命周期误用，但无法证明性能达标，也无法覆盖所有跨帧业务所有权。Release 构建还要通过 trace、GPU counter、内存预算和长时间温度测试验证。

#### Vulkan 与承载结构是两个维度

Vulkan 描述 Producer 如何生成内容。它可以绘制到 SurfaceView/GameActivity/NativeActivity 提供的独立 Surface，也可以写入 TextureView 的输入 Surface 或离屏 `AHardwareBuffer`。SurfaceFlinger 是否能看到独立 layer，取决于目标 `ANativeWindow` 连接到哪个 Consumer，不能根据 API 名判断。

常见游戏页面会同时包含 Vulkan 主体 Surface、宿主 HWUI、系统栏和弹窗。如果引擎 HUD（抬头显示界面）已经画入同一个 swapchain image，SurfaceFlinger 仍只看到一个主体 buffer layer；画面中存在按钮，无法证明还有额外的 SF layer。

### Android Vulkan Profile (AVP)

Vulkan Profile 是一组可以由工具检查的 extension、feature、property、format 和 limit。工程可以用一个 profile 表达所需能力集合，但运行时查询仍不可省略；安装同一 Android 版本的设备也不一定具有相同 GPU 能力。

#### Android 17 的两类口径

Android 17 中要区分面向存量设备的兼容性 profile 和面向新芯片的要求 profile：

- `VP_ANDROID_vulkan_profile_2025`：Android Vulkan Profile 2025，面向广泛的现役设备能力，延续原 Android Baseline Profile 的兼容性用途。
- `VP_ANDROID_17_requirements`：由 `android-17.0.0_r1` 中 `vulkan/vkprofiles/profiles/VP_ANDROID_17_requirements.json` 定义，也称 VRA17；其 label 为 “Vulkan Minimum Requirements for Android 17”，面向随 Android 17 发布或续期 Google Requirements Freeze 的芯片。

`VP_ANDROID_17_requirements` 的 `api-version` 是 Vulkan 1.4.335，并以 `VP_ANDROID_vulkan_profile_2025` 为父 profile。它包含 `VK_KHR_present_id2`、`VK_KHR_present_wait2`、`VK_EXT_present_timing` 和 `VK_EXT_present_mode_fifo_latest_ready` 等要求。该文件约束的是相应新芯片档位，不能据此认定所有升级到 Android 17 的旧设备都支持完整 VRA17。

#### 工程使用方式

建议把能力分三层：

1. 用目标市场的兼容性 profile 定义广覆盖的能力下限；
2. 对 Android 17 新芯片档位检查 `VP_ANDROID_17_requirements`；
3. 继续在运行时查询应用必需的 extension/feature/format/limit，并为缺失能力设计 fallback（降级路径）或明确拒绝启动。

Profile 检查通过，也不代表每种 surface、format、present mode 或 protected 路径都可用。swapchain 能力属于物理设备与具体 `VkSurfaceKHR` 的组合，仍要调用 surface capability/format/present-mode query 获取运行时结果。

#### Dynamic Rendering 例子

某项功能进入 Vulkan core version，不代表创建设备后会自动启用。以 Dynamic Rendering（无须预先创建 RenderPass/Framebuffer 的渲染方式）为例，应用仍需通过 `VkPhysicalDeviceVulkan13Features` 或对应 extension feature 查询 `dynamicRendering`，并在 device creation feature chain 中显式启用。Profile JSON 是否要求该 bit，应以实际文件为准，不能只看 API version。

### 渲染流程详解

#### 创建 surface 与 swapchain

进入帧循环前，应用至少要完成以下初始化：

1. 用 `VK_KHR_android_surface` 从 `ANativeWindow` 创建 `VkSurfaceKHR`；
2. 查询 queue family（具有相同能力的一组硬件队列）是否支持向该 surface present；
3. 查询 surface capabilities、formats 和 present modes；
4. 选择 extent（图像尺寸）、format/colorspace、usage、preTransform、compositeAlpha 和 image count；
5. 创建 swapchain 并取得 images；
6. 为每个 in-flight frame 准备 command buffer、acquire semaphore、render-finished semaphore 和供 CPU 查询完成状态的 fence。

`minImageCount` 只能在 `minImageCount..maxImageCount` 范围内选择；`maxImageCount == 0` 表示规范没有给出显式上限，并非数量无限。Android WSI 还受 native window 的 min-undequeued/max-buffer-count 约束，因此不能把 swapchain 固定描述为双缓冲或三缓冲。

#### 第一阶段：Acquire

典型调用通过 semaphore 或 fence 接收 image 可用信号：

```c
VkResult result = vkAcquireNextImageKHR(
    device,
    swapchain,
    timeoutNs,
    imageAvailableSemaphore,
    VK_NULL_HANDLE,
    &imageIndex
);
```

这段调用只负责取得一块可用于后续渲染和 present 的 image。`timeoutNs == 0` 时可能返回 `VK_NOT_READY`，使用有限 timeout 时可能返回 `VK_TIMEOUT`；窗口变化还可能导致 `VK_ERROR_OUT_OF_DATE_KHR`。

在 Android 17 WSI 中，普通 swapchain 的 `AcquireNextImageKHR()` 会：

1. 把 Vulkan timeout 映射为 native window 的 dequeue timeout；
2. 调用 `ANativeWindow::dequeueBuffer()`，取得 buffer 和 dequeue fence fd；
3. 找到或绑定对应 swapchain image；
4. 把 fence fd 的副本交给驱动私有入口 `AcquireImageANDROID()`；
5. 由驱动把该依赖连接到应用提供的 semaphore/fence。

`AcquireImageANDROID()` 是 Android loader 与驱动之间的集成钩子，应用不会直接调用它。应用也不应手工 import 这条 fd，否则会与 loader 已建立的同步关系重复。

Acquire 耗时较长，可能因为没有可用 image、native window release 较慢、FIFO 节拍限制、surface 正在重新配置，或者驱动内部处理。dequeue fence 来自该 buffer 的前序 Consumer 完成依赖，但 `vkAcquireNextImageKHR()` 的 wall time 不能全部归因于某一条 release fence。应分别观察 dequeue 调用是否阻塞，以及返回后 fence/GPU 依赖何时满足。

#### 第二阶段：Record 与 Submit

Command Buffer recording 是 host（CPU）工作，只负责记录命令和对象引用，不代表 GPU 已经执行。并行录制时要遵守 Vulkan 的 external synchronization（由应用负责的线程同步）规则：

- 每个 worker 线程使用独立的 `VkCommandPool`；
- 同一 `VkCommandBuffer` 的 begin/record/end/reset 不得并发；
- 同一 `VkQueue` 的 host access 需要由应用串行保护；
- descriptor pool、query pool 和其他标记为 externally synchronized 的对象也要按规范加锁或分离所有权。

下面的 synchronization2 骨架等待 acquired image，并在渲染完成后 signal present semaphore：

```c
VkSemaphoreSubmitInfo acquireWait = {
    .sType = VK_STRUCTURE_TYPE_SEMAPHORE_SUBMIT_INFO,
    .semaphore = imageAvailableSemaphore,
    .stageMask = VK_PIPELINE_STAGE_2_COLOR_ATTACHMENT_OUTPUT_BIT,
};

VkCommandBufferSubmitInfo commandInfo = {
    .sType = VK_STRUCTURE_TYPE_COMMAND_BUFFER_SUBMIT_INFO,
    .commandBuffer = commandBuffer,
};

VkSemaphoreSubmitInfo renderSignal = {
    .sType = VK_STRUCTURE_TYPE_SEMAPHORE_SUBMIT_INFO,
    .semaphore = renderFinishedSemaphore,
    .stageMask = VK_PIPELINE_STAGE_2_ALL_COMMANDS_BIT,
};

VkSubmitInfo2 submit = {
    .sType = VK_STRUCTURE_TYPE_SUBMIT_INFO_2,
    .waitSemaphoreInfoCount = 1,
    .pWaitSemaphoreInfos = &acquireWait,
    .commandBufferInfoCount = 1,
    .pCommandBufferInfos = &commandInfo,
    .signalSemaphoreInfoCount = 1,
    .pSignalSemaphoreInfos = &renderSignal,
};

vkQueueSubmit2(graphicsQueue, 1, &submit, frameFence);
```

这段代码只展示依赖关系，并非完整 renderer。`frameFence` 让 CPU 判断本次 submit 何时完成，以便安全复用这一帧的 command/descriptor 资源；`renderFinishedSemaphore` 则让 present engine 等待 GPU 渲染完成。前者连接 GPU 与 CPU，后者连接 GPU 工作与 present。

#### 第三阶段：Present

Present 把 image index 和需要等待的 semaphore 交给 presentation engine（负责把 swapchain image 送入窗口系统的实现）：

```c
VkPresentInfoKHR present = {
    .sType = VK_STRUCTURE_TYPE_PRESENT_INFO_KHR,
    .waitSemaphoreCount = 1,
    .pWaitSemaphores = &renderFinishedSemaphore,
    .swapchainCount = 1,
    .pSwapchains = &swapchain,
    .pImageIndices = &imageIndex,
};

VkResult presentResult = vkQueuePresentKHR(presentQueue, &present);
```

Android 17 的 `PresentOneSwapchain()` 会调用驱动的 `QueueSignalReleaseImageANDROID()`，把 present waits 转换为 producer completion fence；随后设置 damage/timing 等 native window 状态，并由 CPU 调用 `queueBuffer(buffer, fence)`。`queueBuffer()` 接管 fence fd 的所有权，SurfaceFlinger/BLAST 再把它作为 buffer acquire dependency，等待 Producer 完成写入。

`vkQueuePresentKHR()` 返回时，用户通常还没有看到画面。应用仍需处理 `VK_ERROR_OUT_OF_DATE_KHR`、`VK_SUBOPTIMAL_KHR` 和 surface lost；显示时序还要继续追踪 SF latch、HWC validate/present 和 Display fence。Android WSI 当前只在 window transform/rotation 变化时返回 `VK_SUBOPTIMAL_KHR`，不能把所有 extent 变化都等同于该返回值。

#### 完整时序

下面的图按 CPU API、GPU 依赖和 Android queue 三条线描述一帧：

```mermaid
sequenceDiagram
    participant App as "App / RHI thread"
    participant WSI as "Android Vulkan WSI"
    participant BQ as "ANativeWindow / BufferQueue"
    participant Driver as "Vulkan driver / GPU"
    participant SF as "SurfaceFlinger"
    participant HWC as "Composer / Display"

    App->>WSI: "vkAcquireNextImageKHR"
    WSI->>BQ: "dequeueBuffer"
    BQ-->>WSI: "image buffer + dequeue fence"
    WSI->>Driver: "AcquireImageANDROID(fence, semaphore)"
    WSI-->>App: "imageIndex"
    App->>App: "record command buffer"
    App->>Driver: "vkQueueSubmit(wait imageAvailable, signal renderFinished)"
    App->>WSI: "vkQueuePresentKHR(wait renderFinished)"
    WSI->>Driver: "QueueSignalReleaseImageANDROID"
    Driver-->>WSI: "producer completion fence"
    WSI->>BQ: "queueBuffer(image, fence)"
    BQ->>SF: "buffer update + acquire dependency"
    SF->>HWC: "validate / present"
    HWC-->>SF: "present + per-layer release fences"
    SF-->>BQ: "future image reuse dependency"
```

图中 WSI 调用驱动取得 fence 后，再由 CPU 调用 `queueBuffer()`。GPU 通过 semaphore/fence 表达完成依赖，CPU 负责发起 API 调用和转移 fd 所有权；`queueBuffer()` 不是 GPU 自行执行的操作。

### Pipeline Barrier 与 Image Layout

#### 三种同步对象解决不同问题

- Semaphore：连接 queue submit、acquire 和 present 等 GPU/WSI 执行依赖；
- Fence：把某次 queue 工作的完成状态暴露给 host（CPU）；
- Pipeline barrier/event：在 command stream 内定义执行顺序、内存可见性、image layout 和 queue-family ownership。

Semaphore signal 只能表达执行依赖，不能代替 image layout transition；barrier 也不能代替 present 对 render-finished semaphore 的等待。分析同步时，要同时检查 execution dependency（谁先执行）、memory dependency（写入何时对读取可见）和 resource state（资源处于哪种 layout/ownership）。

#### acquired image 的 layout

swapchain image 会被循环复用。第一次使用且应用明确丢弃旧内容时，可以从 `VK_IMAGE_LAYOUT_UNDEFINED` 转换到颜色附件 layout；后续 acquire 到的 image 通常要从 `VK_IMAGE_LAYOUT_PRESENT_SRC_KHR` 转回渲染所需 layout。只有旧内容允许完全丢弃，并且符合规范与渲染设计时，才能把 `oldLayout` 设为 `UNDEFINED`，不能无条件每帧都这样写。

一次常见的 layout 序列是：

```text
acquire
PRESENT_SRC_KHR（或首次 UNDEFINED）
→ COLOR_ATTACHMENT_OPTIMAL
→ PRESENT_SRC_KHR
present
```

这条序列只说明最简状态变化，不包含 MSAA resolve、transfer、compute post-process 或多 queue ownership。涉及这些阶段时，还要增加对应的 layout transition 与 queue-family transfer。

#### synchronization2 barrier

下面的 barrier 把颜色附件写入收束到 present layout：

```c
VkImageMemoryBarrier2 toPresent = {
    .sType = VK_STRUCTURE_TYPE_IMAGE_MEMORY_BARRIER_2,
    .srcStageMask = VK_PIPELINE_STAGE_2_COLOR_ATTACHMENT_OUTPUT_BIT,
    .srcAccessMask = VK_ACCESS_2_COLOR_ATTACHMENT_WRITE_BIT,
    .dstStageMask = VK_PIPELINE_STAGE_2_NONE,
    .dstAccessMask = 0,
    .oldLayout = VK_IMAGE_LAYOUT_COLOR_ATTACHMENT_OPTIMAL,
    .newLayout = VK_IMAGE_LAYOUT_PRESENT_SRC_KHR,
    .srcQueueFamilyIndex = VK_QUEUE_FAMILY_IGNORED,
    .dstQueueFamilyIndex = VK_QUEUE_FAMILY_IGNORED,
    .image = swapchainImages[imageIndex],
    .subresourceRange = {
        VK_IMAGE_ASPECT_COLOR_BIT, 0, 1, 0, 1
    },
};

VkDependencyInfo dependency = {
    .sType = VK_STRUCTURE_TYPE_DEPENDENCY_INFO,
    .imageMemoryBarrierCount = 1,
    .pImageMemoryBarriers = &toPresent,
};

vkCmdPipelineBarrier2(commandBuffer, &dependency);
```

这段示例适用于 graphics/present 使用同一 queue family，并且颜色附件写入是最后一项操作的简化场景。如果两类 queue family 不同，应按 surface sharing mode 和 ownership transfer 设计；如果后续还有 transfer/compute，`srcStageMask` 和 `srcAccessMask` 必须覆盖真正的最后一次写入。Validation Layer 只能发现部分错误，仍需使用 GPU-assisted validation 和目标设备测试补充验证。

#### 过度同步

把 stage mask 一律设为 `ALL_COMMANDS`、频繁调用 queue idle、每个 pass 都使用 host fence，或者在没有依赖需要时拆成多个 submit，都会减少 GPU 可并行执行的空间。优化步骤应是：

1. 画出资源的生产者和消费者；
2. 找到必须等待该资源的最早 Consumer stage；
3. 让 access mask 只覆盖真实的写入和读取；
4. 合并无意义的小 submit；
5. 用 GPU trace 验证 bubble 是否减少。

### Presentation Mode

Vulkan 规范定义了多种 present mode，但应用只能使用 `vkGetPhysicalDeviceSurfacePresentModesKHR()` 为当前 surface 实际枚举出的模式。

Android 17 AOSP native WSI 的普通 surface 路径如下：

| Mode | Android 17 返回条件 | 语义与边界 |
|---|---|---|
| `FIFO_KHR` | 始终加入返回集合 | 按顺序显示队列中的 image；Vulkan 规范要求支持 |
| `MAILBOX_KHR` | `min_undequeued_buffers + 1 < max_buffer_count` | 新 image 可以替换尚未显示的旧 image；仍需评估 pacing、功耗与 in-flight 数量 |
| `FIFO_LATEST_READY_EXT` | `present_mode_fifo_latest_ready_ext2` flag 开启 | 从 FIFO 中选择已经 ready 的较新 image；必须通过枚举确认支持 |
| `SHARED_DEMAND_REFRESH_KHR` / `SHARED_CONTINUOUS_REFRESH_KHR` | physical-device presentation properties 报告 `sharedImage` | 使用共享 image 的专用模式，生命周期不同于普通 swapchain |

普通 Android Surface 路径不会把 `IMMEDIATE_KHR` 或 `FIFO_RELAXED_KHR` 加入该返回集合，因此桌面 Vulkan 的常见选择建议不能直接移植到 Android。

#### 运行时选择

选择流程应包括：

1. 枚举 modes；
2. 结合业务目标选择 FIFO、MAILBOX 或 FIFO latest ready；
3. 用 surface capabilities 选择合法 image count；
4. 记录 swap interval/present mode 和 Display refresh mode；
5. 在目标设备测量 input-to-present、帧间隔、功耗和丢帧；
6. surface 重建后重新查询，不能一直沿用上一窗口的能力结果。

MAILBOX 不一定带来最低时延，更多可用 image 也不一定更流畅。如果应用过早采样输入并持续积压工作，即使 presentation engine 丢弃旧帧，CPU/GPU 仍然会为这些帧付出成本。

#### Android 17 present timing

`android-17.0.0_r1` 增加了 `VK_EXT_present_timing` 平台支持，并把它列入 `VP_ANDROID_17_requirements`。AOSP WSI 可以查询 queue-operations-end、request-dequeued、image-first-pixel-out 和 image-first-pixel-visible 等显示阶段时间。应用还要完成以下步骤：

- 枚举并启用 extension；
- 查询 `VkPhysicalDevicePresentTimingFeaturesEXT`；
- 按规范启用 `VK_KHR_present_id2` 等依赖；
- 查询具体 surface 的 timing capabilities；
- 创建 swapchain 时设置 `VK_SWAPCHAIN_CREATE_PRESENT_TIMING_BIT_EXT`；
- 处理 timing queue full 和查询结果延迟到达。

该扩展提供 Android 显示链路中的阶段反馈，不是外部仪器测得的光学显示时间。旧设备可以继续评估 `VK_GOOGLE_display_timing`；两套 API 支持的阶段和时间域不同，不能混用。

### Swappy Frame Pacing

Swappy 是 Android Game Development Kit（AGDK）中的帧节奏库，不属于平台源码 `android-17.0.0_r1`。应用打包的 Swappy 版本、初始化结果和运行时配置都会影响行为，因此记录系统版本时还要单独记录库版本。

#### 它解决什么

Swappy Vulkan 接口包装 `vkQueuePresentKHR()`，结合 Display refresh、presentation timestamp、Choreographer 和 sync fence 调整提交节奏。它主要用于：

- 避免 Producer 持续过早提交造成 queue-stuffing（待显示帧长期积压）；
- 让目标帧率与显示周期形成稳定关系；
- 在需要时调整 pipeline mode 和 swap interval；
- 为多刷新率设备提供可复用的 pacing 机制。

Swappy 中出现等待，不一定代表卡顿。如果它在合适的位置暂停 render thread，减少 in-flight frame 并推迟输入采样，端到端时延反而可能下降。判断时应比较等待前后的 present 间隔、missed frame、queue depth、GPU idle 和 input-to-present 时延。

#### 接入边界

每个 swapchain 都要单独完成 Swappy 初始化，并在重建时更新对应状态。`SwappyVk_queuePresent()` 仍会返回 `VkResult`，应用必须处理 `OUT_OF_DATE`/`SUBOPTIMAL`；初始化失败时，也要切换到自研 pacing 或明确的降级策略。

下面的骨架只展示调用位置，具体签名与配置以应用锁定的 AGDK 版本为准：

```text
create swapchain
  → initialize Swappy for this swapchain
  → configure target swap interval / auto mode

per frame
  acquire → record → submit
  → SwappyVk_queuePresent(...)

swapchain recreate
  → destroy/reinitialize Swappy state
```

这份骨架说明 Swappy 只控制 present 附近的节奏，不会替应用管理 resource barrier、command buffer fence 或业务线程同步。

#### 自研 pacing 与 Swappy

Vulkan 应用可以使用 `VK_EXT_present_timing`、`VK_GOOGLE_display_timing`、present id/wait、frame-rate hint 和引擎时钟自行实现 pacing。同一个 swapchain 不应同时由多套 pacing 控制器调度；接入 Swappy 后，要明确由谁决定目标时间、由谁等待，以及由谁统计历史 present。

### Trace 视角

#### 建立逐帧证据

从目标 Surface 和 Producer tid 开始，每帧至少记录：

```text
input sample
→ logic/update
→ command recording
→ vkAcquireNextImageKHR result + image index
→ vkQueueSubmit + GPU execution
→ producer completion fence
→ vkQueuePresentKHR / queueBuffer
→ SF buffer selection
→ HWC validate/present
→ display timing / present fence
→ per-layer release
```

这条时间线把 CPU API、GPU execution 和显示阶段分开。带有调用名的 slice 可能来自应用 marker、Vulkan layer、AGI 或驱动数据源；没有标准 slice 时，可以用 present id、buffer/frame number、fence 和 FrameTimeline token 补齐关联。

#### 等待归因

| 现象 | 候选原因 | 证据 |
|---|---|---|
| `vkAcquireNextImageKHR()` 耗时长 | 没有 available image、FIFO cadence、Consumer release 较晚、surface resize | image count、BufferQueue state、dequeue/release fence 和返回码 |
| command recording 迟到 | logic/RHI/worker 依赖、pipeline 编译、CPU 调度 | worker slice、Runnable latency（可运行线程等待 CPU 的时间）和 pipeline cache |
| `vkQueueSubmit*()` host 调用耗时长 | queue 外部同步竞争、驱动工作、过多小 submit | host mutex、调用栈和 submit 数量 |
| submit 较早但 GPU fence 迟到 | shader、overdraw、带宽、barrier bubble、温控/频率 | GPU stages/counters、job queue 和 fence signal |
| `vkQueuePresentKHR()` 耗时长 | 驱动/WSI、Swappy、present waits、window queue | Swappy marker、QueueSignalReleaseImage 和 BufferQueue queue |
| buffer 已 queue 但 SF 使用旧帧 | Producer fence 未 ready、目标显示时刻未到、visibility/transaction 条件 | layer trace、fence 和 present timing |
| SF 已选新帧但 present 仍晚 | CLIENT composition、HWC/Display 资源竞争 | RenderEngine、composition type 和 HWC/present fence |

`vkAcquireNextImageKHR()` 和 `vkQueuePresentKHR()` 只管理 swapchain image 的取得与交付，不适合充当业务线程或通用 GPU 同步器。其阻塞行为会随驱动、present mode 和 presentation engine 状态变化。

#### queue-stuffing

典型证据是 pending/in-flight 数量长期处于高位，应用仍按最大速度 acquire/submit/present，随后周期性等待 available image；帧率接近目标，input-to-present 时延却持续上升。修复方向包括：

- 用 Swappy 或自研 timing 控制 submit；
- 降低 in-flight frame 数；
- 把输入采样推迟到更靠近目标帧；
- 减少 GPU workload，确保 Producer fence 在 deadline 前 ready；
- 选择经设备验证的 present mode/image count。

#### FrameTimeline、present timing 与光学时间

FrameTimeline 可以帮助对齐 App SurfaceFrame 与 SurfaceFlinger DisplayFrame，但独立 native Surface 是否提供完整的 expected/actual 信息，取决于 Producer 传入的 timeline/desired-present 数据和 trace 配置。`VK_EXT_present_timing` 提供 WSI/Display 各阶段的反馈，present fence 提供显示栈同步完成边界；这三者都不是用户实际看到光线变化的光学时间。

#### SurfaceFlinger Graphite 不属于 App WSI

Android 17 的 SurfaceFlinger RenderEngine 包含可选的 Graphite Vulkan backend；`RenderEngine::SkiaBackend` 仍以 Ganesh 为默认值，是否启用 Graphite 取决于 flag、property 和 OEM 配置。`RenderEngineThreaded` 会尝试使用 `SFRenderEnginePolicy` 和实时调度策略 `SCHED_FIFO` priority 2，在 `primeCache`（预热渲染缓存）期间暂时切回普通策略 `SCHED_OTHER`。

这条 Vulkan 工作只在 SurfaceFlinger 需要 RenderEngine 生成 client target、blur、tone-map 等内容时出现。它与 App 的 `vkQueueSubmit()`/swapchain 使用不同的 device、context、queue 和线程。如果主体 layer 使用 HWC DEVICE composition，SF 未必会通过 RenderEngine 重绘它。trace 中应把 App queue、`REThreaded::drawLayers`、Graphite/Ganesh submit 和 HWC present 分组，不能把 SF Graphite 的时间计入 App command recording。

Graphite 的 `flushAndSubmit()` 使用 Recording、wait/signal backend semaphores 和导出的 sync fd 表达 RenderEngine GPU 何时完成。这是 SF CLIENT composition 生成 client target 时的输出 fence，与 App swapchain 的 `VkFence` 无关。

#### Validation 与工具

- Validation Layers：在开发构建中检查 API、同步和对象生命周期；按 Android 官方 GPU debug layers 流程打包和启用，不使用未经版本核实的全局属性片段。
- AGI（Android GPU Inspector）：关联 Vulkan API、GPU queue、counter 和 frame capture。
- RenderDoc：在目标设备和构建支持时，检查单帧资源与 DrawCall。
- Perfetto：关联线程调度、BufferQueue、SurfaceFlinger、FrameTimeline、fence 和 HWC。

这些工具会改变 CPU/GPU 成本。确定性能基线时，应关闭 validation/capture 后重新测量。

#### Android 12—17 边界

| 平台 | 变化 | 分析重点 |
|---|---|---|
| Android 12 / API 31 | BLAST 与 FrameTimeline 形成现代显示诊断基线 | 区分 App submit、SF latch 和 Display present |
| Android 13 / API 33 | Composer AIDL（稳定的进程间接口定义）成为主线；Game Mode/FPS intervention 可能改变游戏帧率 | 判断目标 cadence 时要包含系统 intervention（干预） |
| Android 14 / API 34 | Android WSI acquire/queue 主结构延续 | 不要虚构 API 34 专属 present 流程 |
| Android 15 / API 35 | 年度 Vulkan requirements/profile 体系继续推进；16 KB page-size 兼容影响 native 库发布 | 能力 profile 与应用可运行性要分开验证 |
| Android 16 / API 36 | ADPF（Android Dynamic Performance Framework）、性能 headroom 与 ARR（Adaptive Refresh Rate）能力扩展，Vulkan 主链不变 | workload 自适应无法替代正确的 pacing |
| Android 17 / API 37 | 增加 `VP_ANDROID_17_requirements`、`VK_EXT_present_timing` 和有条件支持的 FIFO latest ready；SF 包含可选 Graphite backend | 运行时查询 surface/feature，并把 App WSI 与 SF RenderEngine 分组分析 |

#### Android 17 源码锚点

- [`swapchain.cpp`](https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/vulkan/libvulkan/swapchain.cpp)：surface capabilities、present modes、AcquireImageANDROID、QueueSignalReleaseImageANDROID、queueBuffer 和 present timing；
- [`VP_ANDROID_17_requirements.json`](https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/vulkan/vkprofiles/profiles/VP_ANDROID_17_requirements.json)：Android 17 芯片要求 profile 和 Vulkan 1.4.335 能力集合；
- [`Surface.cpp`](https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/libs/gui/Surface.cpp)、[`BufferQueueProducer.cpp`](https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/libs/gui/BufferQueueProducer.cpp)：dequeue/queue、slot、fence 和 buffer age；
- [`SurfaceFlinger.cpp`](https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/services/surfaceflinger/SurfaceFlinger.cpp)、[`HWComposer.cpp`](https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/services/surfaceflinger/DisplayHardware/HWComposer.cpp)：buffer selection、composition 和 present；
- [`RenderEngine.h`](https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/libs/renderengine/include/renderengine/RenderEngine.h)、[`GraphiteVkRenderEngine.cpp`](https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/libs/renderengine/skia/GraphiteVkRenderEngine.cpp)、[`RenderEngineThreaded.cpp`](https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/libs/renderengine/threaded/RenderEngineThreaded.cpp)：SF 可选 Graphite、threaded task 和 client-target fence；
- [`dma-buf.c`](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/drivers/dma-buf/dma-buf.c)、[`sync_file.c`](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/drivers/dma-buf/sync_file.c)、[`dma-fence.c`](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/drivers/dma-buf/dma-fence.c)：共享 buffer 和 fence fd；
- [Android Vulkan Profiles](https://developer.android.com/ndk/guides/graphics/android-vulkan-profile)、[Native/proprietary engine Vulkan guide](https://developer.android.com/games/develop/vulkan/native-engine-support)、[Android Frame Pacing](https://developer.android.com/games/sdk/frame-pacing)：profile、WSI 同步和 Swappy 的官方边界。

相关章节：

- [18.4 OpenGL ES、EGL 与 ANGLE](04-opengl-egl-angle.md)
- [18.6 SurfaceControl 与 HardwareBufferRenderer](06-surfacecontrol-hardwarebuffer-renderer.md)
- [2.8 BufferQueue、Gralloc 与 Sync Fence](../../part1-fundamentals/ch02-rendering/08-bufferqueue-gralloc-sync-fence.md)
- [2.7 GPU 渲染与图形 API 选型](../../part1-fundamentals/ch02-rendering/07-gpu-rendering-graphics-api.md)


## HWUI Vulkan 多队列与帧边界

原生 Vulkan 由应用显式管理队列，HWUI 多队列由框架在渲染任务之间分配并行度。诊断时要区分应用队列和 HWUI 内部队列。

Android 17 的 HWUI Vulkan 后端会从同一个 graphics queue family 取得两条 `VkQueue`。queue family 是一组具有相同能力标志的 Vulkan 队列，`VkQueue` 则是向设备提交命令批次的接口。queue 0 服务 RenderThread 的窗口绘制，queue 1 服务 `HardwareBitmapUploader` 的 AHardwareBuffer 上传。二者共享同一个逻辑设备 `VkDevice`，并分别绑定一个 Skia `GrDirectContext`；后者是 Skia 管理 GPU 资源与提交工作的上下文。

源码能够证明 HWUI 创建了两条 queue，也能证明 CPU 线程可以分别向它们执行 host submission（主机侧命令提交）。GPU 是否并行执行这些命令则由驱动与硬件决定；GPU 引擎、依赖、内存带宽、频率和调度策略都可能让工作交错或串行。分析时要分别标明接口保证、由源码推导的结论，以及仍需 trace 验证的硬件行为。

对 `android-14.0.0_r1` 至 `android-17.0.0_r1` 的 `VulkanManager.cpp` 做标签对比后，可以确认双 queue 在 Android 14 基线中已经存在。标题中的 Android 17 表示本文采用的源码版本，不能据此把双 queue 写成 Android 17 新增特性。

### 复核基线

| 层级 | 基线 | 负责内容 |
| --- | --- | --- |
| Android 平台 | Android 17 / API 37 / `android-17.0.0_r1` | HWUI、VulkanManager、SkiaVulkanPipeline、ANativeWindow、FrameTimeline |
| Android 内核 | `android17-6.18-2026-06_r6` | CPU 线程调度、dma-buf、dma-fence 与 sync_file；厂商 GPU 调度仍由具体驱动实现，内核不包含 `VulkanManager` 或 Skia 逻辑 |
| 历史对照 | `android-14.0.0_r1`、`android-15.0.0_r1`、`android-16.0.0_r1` | 判断双 queue 与 frame-boundary 代码何时已出现 |

分析范围限定为 HWUI 选择 `SkiaVulkan` 的应用进程。应用自行创建的 Vulkan device/queue、SurfaceFlinger 的 RenderEngine Vulkan 上下文，以及厂商 GPU 服务，都不属于这里的 `VulkanManager` 实例。

### 完整路径

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

### VulkanManager：共享 device，分别持有 Skia context

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

### 两条 graphics queue 如何创建

#### 同一 queue family，两个 queue index

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

#### 两个 Skia context 绑定不同 queue

`createContext(ContextType)` 把同一组 device 信息交给 Skia，只替换 `fQueue`：

- `kRenderThread` → `mGraphicsQueue`；
- `kUploadThread` → `mAHBUploadQueue`。

直接效果是把主机侧提交顺序分开：硬件位图上传不会进入 RenderThread 所用 queue 的顺序链。实际性能收益仍取决于驱动和硬件：

- GPU 有可重叠的 copy/graphics 执行资源时，上传可能与窗口绘制部分重叠；
- 两条 queue 争用内存带宽、cache 或同一图形引擎时，驱动可能交错甚至串行；
- AHardwareBuffer 上传涉及的分配、页映射和 cache 维护也可能拖慢窗口渲染；
- 两条 queue 使用同一个 global priority 请求，queue 1 没有天然的低优先级。

双 queue 提供的是独立提交能力，并减少同一 queue 内的顺序约束。它不保证硬件并行，也不能隔离上传引起的全部资源争用。

### HardwareBitmapUploader：上传隔离不等于异步返回

#### CPU 像素会被复制

`Bitmap.Config.HARDWARE` 的这条创建路径先分配带 `AHARDWAREBUFFER_USAGE_GPU_SAMPLED_IMAGE` 的 AHardwareBuffer，再调用 `SkImages::TextureFromAHardwareBufferWithData()` 把 `SkPixmap` 数据写入。`Bitmap.cpp` 也明确把 `allocateHardwareBitmap()` 描述为复制 bitmap contents。

因此，这条路径不属于已有像素直接变成 GPU 纹理的 zero-copy。AHardwareBuffer 可以避免后续再创建一份应用可见像素存储，但首次创建仍要把 CPU 源像素传输到 gralloc 分配的图形 buffer。

#### GrallocUploadThread 与调用方等待

Vulkan 上传在 `GrallocUploadThread` 上执行：

1. 取得或创建共享 `VulkanManager`；
2. 创建绑定 queue 1 的 `GrDirectContext`；
3. 调用 `TextureFromAHardwareBufferWithData()` 记录上传；
4. 执行 `mGrContext->submit(GrSyncCpu::kYes)`；
5. `runSync()` 返回后，`uploadHardwareBitmap()` 才把结果交回调用方。

`GrSyncCpu::kYes` 表示上传线程会等待 GPU 完成。这样可以保证返回的 hardware bitmap 已经写完，但调用仍是同步的。主线程若同步创建大图，仍可能依次等待解码、AHB（AHardwareBuffer）分配、上传和 GPU 完成。

queue 1 与 queue 0 在这段时间可以分别提交工作。GPU 资源争用是否拉长 RenderThread 的 queue 0 工作，仍要通过 trace 验证。

#### 60 秒闲置回收

`HardwareBitmapUploader.cpp` 把 `kThreadTimeout` 设为 60000 ms。没有 pending upload（待处理上传）且空闲时间超过该值后，`VkUploader::onIdle()` 会释放上传 `GrDirectContext` 与 manager 强引用；下一次上传再按需重建。

源码只能证明上传 context 及其持有资源被释放。具体回收多少 GPU 内存，还取决于驱动、Skia cache、AHardwareBuffer 的其他持有者和设备内存策略，不能写成固定容量。

### Global priority：可选请求，不是实时保证

`Properties::contextPriority` 默认值为 0。只有系统代码在 Vulkan context 创建前通过隐藏的 `HardwareRenderer.setContextPriority()` 设置 EGL priority 常量，`VulkanManager` 才会尝试映射到：

- `VK_QUEUE_GLOBAL_PRIORITY_LOW_EXT`；
- `VK_QUEUE_GLOBAL_PRIORITY_MEDIUM_EXT`；
- `VK_QUEUE_GLOBAL_PRIORITY_HIGH_EXT`。

Android 17 源码仅在 `contextPriority != 0` 且识别到 `VK_EXT_global_priority` v2 时附加 `VkDeviceQueueGlobalPriorityCreateInfoEXT`。如果 global-priority query 可用，代码会先确认选中的 queue family 是否报告了目标档位；不支持时记录 warning，但继续创建 device。

还要注意三点：

- `mAPIVersion` 固定为 Vulkan 1.1；源码检查 `VK_API_VERSION_1_4`，不能证明 HWUI 在 Android 17 使用 Vulkan 1.4 core priority；
- 两条 queue 来自同一个 `VkDeviceQueueCreateInfo`，global priority 请求对这次创建的两条 queue 一起生效；
- global priority 是提交给驱动的队列调度请求，还受系统权限控制。它与 Linux 线程实时优先级无关，也不承诺具体的 GPU 抢占时延。

### 两种“帧边界”记录不同对象

#### Vulkan frame-boundary 是 GPU 工具标记

Android 17 的 `finishFrame()` 在提交 Skia 工作时有两条帧标记路径：

1. AGI capture layer 提供私有 `VK_ANDROID_frame_boundary` 时，HWUI 把本帧的 signal semaphore（GPU 完成相应工作时置为已触发的同步对象）和 render-target image 传给 `vkFrameBoundaryANDROID()`；
2. 该私有入口不存在时，HWUI 设置 `GrSubmitInfo.fMarkBoundary = Yes` 与进程内递增的 `fFrameID`，由 Skia 和可用的 `VK_EXT_frame_boundary` 支持向工具描述 frame boundary。

Khronos `VK_EXT_frame_boundary` 给 queue submission 附加应用定义的 frame ID、结果 image/buffer 和工具 tag。它是 profiling annotation（供分析工具使用的元数据），不会创建新的执行依赖，也不能替代 present semaphore。

`VK_ANDROID_frame_boundary` 在 AOSP 头文件中被明确描述为 AGI 专用扩展，由 AGI Vulkan capture layer 在抓帧时提供。普通运行时查不到该 proc pointer（Vulkan 函数入口指针）属于预期情况。

#### FrameTimeline 是窗口 present 时间线

FrameTimeline 的 `vsyncId` 走另一条路径。`CanvasContext::draw()` 取得 `FrameTimelineVsyncId`，构造 `ANativeWindowFrameTimelineInfo`，再由 render pipeline 在 `queueBuffer()` 前设置给 ANativeWindow。SurfaceFlinger 用它关联 App `SurfaceFrame` 和显示 `DisplayFrame` 的 expected/actual 时间线。

两类 ID 的差异如下：

| 对象 | 生成位置 | 主要消费者 | 是否直接表示 expected present |
| --- | --- | --- | --- |
| Vulkan `currentFrameID` | HWUI `VulkanManager::finishFrame()` 的进程内计数器 | Skia、Vulkan 工具、AGI capture | 否 |
| FrameTimeline `vsyncId` | Choreographer / 平台帧时间线传入 HWUI | ANativeWindow、SurfaceFlinger、Perfetto FrameTimeline | 是 |
| BufferQueue frame number | Producer queue 次序 | BLAST、SurfaceFlinger、transaction/trace | 不单独表示 |

AOSP 没有把 `currentFrameID` 赋值为 `FrameTimelineVsyncId`。工具可以根据时间、submission、render target 或其他元数据关联两者，但不能假设二者数值相同。

#### Frame boundary 也不等于 present

Vulkan frame-boundary 标记发生在 queue submission 附近，离屏幕显示仍有以下步骤：

- GPU 完成对窗口 image 的写入；
- producer completion fence signal；
- `ANativeWindow::queueBuffer()`；
- BLAST buffer transaction；
- SurfaceFlinger latch；
- HWC DEVICE 或 RenderEngine CLIENT 合成；
- display present。

GPU 工具把 draw call 归到某帧，只能回答这些 GPU 命令属于哪组提交工作。用户何时看到结果，仍要结合 FrameTimeline 与 present fence 判断。

### dequeue fence 与 producer completion fence

#### dequeue fence：等待旧消费者释放 buffer

`VulkanSurface::dequeueNativeBuffer()` 从 App Window 的 ANativeWindow 取得 buffer 和 dequeue fence。该 fence 表示 Consumer（buffer 消费方）何时结束对这块旧 buffer 的使用；Producer（buffer 生产方）要等它 signal 后才能安全复用并写入。

当 fence 尚未 signal 时，`VulkanManager::dequeueNextBuffer()` 会尝试：

1. `dup()` fence fd；
2. 创建 `VkSemaphore`；
3. 以 `VK_EXTERNAL_SEMAPHORE_HANDLE_TYPE_SYNC_FD_BIT` 和 `VK_SEMAPHORE_IMPORT_TEMPORARY_BIT` 把 fd 临时导入 semaphore；
4. 让 Skia surface 的后续 GPU 工作等待该 semaphore；
5. 立即调用 `FlushAndSubmit()`，确保 wait 进入 GPU submission。

导入或创建失败时，源码改由 CPU 调用 `sync_wait()`。这条 fence 的方向是 Consumer/HWC 把旧 buffer 释放给 App Producer 复用，并非 SurfaceFlinger 作为 Producer 通知 App 新内容已经准备好。

#### finishFrame：导出本轮 GPU 完成 fence

queue 0 的窗口绘制工作准备提交时，`finishFrame()` 创建可导出为 sync-fd 的 semaphore，并把它放入 `GrFlushInfo.fSignalSemaphores`。flush/submit 后，代码通过 `vkGetSemaphoreFdKHR()` 取得 fd。sync-fd 是用户空间传递内核 `dma_fence` 的文件描述符封装。`VulkanSurface::presentCurrentBuffer()` 再把这个 fd 传给 `ANativeWindow::queueBuffer()`。

这个 fd 在 BufferQueue 消费侧成为当前 buffer 的 acquire fence。SurfaceFlinger 可以先接收 buffer 元数据，但读取像素前必须等待 fence signal，确认 GPU 已经写完。`presentCurrentBuffer()` 的函数名容易误导；这里执行的是 queue buffer，还没有完成屏幕 present。

创建可导出 semaphore 失败、导致 `sharedSemaphore` 为空时，`finishFrame()` 会调用 `mQueueWaitIdle(mGraphicsQueue)`，保守地等待 queue 0 空闲。若 GPU 已成功提交，但后续 `vkGetSemaphoreFdKHR()` 导出 fd 失败，Android 17 源码只记录错误并返回无效 fd。这两类失败不能合并成同一条 fallback。正常路径无需 RenderThread 在 CPU 上等待整帧 GPU 完成。

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

### Buffer age 与 partial update

当 `Properties::enablePartialUpdates` 和 `Properties::useBufferAge` 同时开启时，`VulkanManager` 使用 `SwapBehavior::BufferAge`。buffer age 表示一块 buffer 距离上次成功入队经历了多少次窗口提交。`VulkanSurface` 根据本进程的 present count 与该 buffer 上次成功入队时的 count 计算 age；新 buffer、内容无效或 transform 改变时返回 0。

HWUI 会结合 buffer age 与 swap history，计算本次需要恢复的 damage（发生变化、需要更新的区域），再通过 `native_window_set_surface_damage()` 把窗口 damage 交给 ANativeWindow。这里有三个限制：

- buffer age 只表示内容可复用历史，不能保证系统仅执行脏矩形内的 GPU 指令；
- age 为 0 时需要按完整内容处理；
- driver、tile 架构、offscreen layer、blend 和 SurfaceFlinger 合成仍会影响最终带宽。

因此，partial update 的收益要结合 GPU counter、render stage 与功耗数据评估。`bufferAge != 0` 本身不能证明 fill rate（每秒实际填充的像素量）已按 damage 面积同比例下降。

### VkFunctor 只说明 WebView 私有互操作

`getVkFunctorInitParams()` 会向 HWUI 的 WebView Vulkan functor 回调提供 `VkInstance`、`VkPhysicalDevice`、`VkDevice`、queue 0、queue family index 和已启用的 feature/extension。这里的 functor 是 WebView 与 HWUI 之间的私有绘制回调对象；`VkFunctorDrawable` 明确持有 `WebViewFunctor::Handle`，并在 RenderThread 上调用它。

这不是面向普通应用的通用 Vulkan 接口，也不能让 SurfaceView 的自定义渲染自动复用 HWUI device。普通 native renderer 无法据此取得 HWUI 私有 device；应用应通过公开 Vulkan/ANativeWindow API 管理自己的 instance、device、queue 与同步对象。

### 与 SkiaGL 的正确比较方式

一种常见误解是 SkiaGL 只有一个 context，因此 hardware bitmap 上传必然与 RenderThread 串行。Android 17 的 `HardwareBitmapUploader` 在 GL 路径同样使用独立的 `EGLUploader`、`GrallocUploadThread` 与 EGL context，并通过 EGL fence 等待上传完成。

两种后端的可观察差异如下：

| 维度 | SkiaVulkan | SkiaGL |
| --- | --- | --- |
| HWUI 明确管理的提交对象 | 同一 VkDevice 上两条 graphics `VkQueue` | RenderThread 与 uploader 各自的 EGL/GL context；驱动内部 queue 拓扑不可由 GL API 直接得知 |
| AHB 上传完成等待 | UploadThread `GrSyncCpu::kYes` | UploadThread `eglClientWaitSyncKHR()` |
| 窗口完成 fence | Vulkan semaphore 导出 sync fd | EGL/GL native fence 路径 |
| GPU frame annotation | 可使用 `VK_EXT_frame_boundary` 或 AGI 私有扩展 | 依赖 GL/驱动/工具支持，不能概括成“无分析能力” |
| 是否保证上传与绘制并行 | 否 | 否 |

Vulkan API 会显式表达 queue、semaphore 与外部句柄之间的关系，便于建立同步证据，但同一负载不会因此自动变快。性能对比仍需固定设备、内容、刷新率与热状态。

### 性能观测：分清 queue、GPU 与 present

#### Perfetto

建议同时采集以下证据，并用 submission ID、时间区间和 frame token（关联同一帧的标识）串起各数据源：

- Main thread 与 RenderThread 调度、`syncAndDrawFrame`、`Vulkan finish frame`、`flush commands`；
- `GrallocUploadThread` 的 hardware bitmap 上传 slice；
- `dequeueBuffer` / `queueBuffer` duration；
- FrameTimeline expected/actual 与 jank type；
- `gpu.renderstages`：设备 producer 支持时，可以通过 `hw_queue_iid`、context、submission ID 与 render stage 查看 GPU 活动；
- `gpu.counters`：设备支持时查看频率、busy、带宽、cache 等计数器；
- GPU/DRM ftrace 与 dma-buf/fence 事件：用来判断驱动调度和 fence 等待。

Perfetto 的 GPU data source 由设备或驱动侧 producer（向 Perfetto 写入 trace 数据的组件）提供，名称可能带 `.adreno`、`.mali` 等后缀，可用字段也因设备而异。HWUI 创建两条 `VkQueue`，不保证 trace 会显示两条可独立命名的硬件 queue。

#### AGI

AGI frame profiling 可以检查单帧中的 Vulkan API call、render pass、shader、texture、pipeline state 与资源。抓取 HWUI 渲染时，`VK_ANDROID_frame_boundary` 由 AGI capture layer 注入，用于帮助工具划分窗口帧。

AGI 适合解释单帧 GPU 命令做了什么，但不能替代系统 trace。FrameTimeline、BufferQueue、SurfaceFlinger、HWC 与 present timing 仍要通过 Perfetto、dumpsys 或厂商显示工具观察。

#### 常见症状与证据

| 症状 | 先看 | 避免的误判 |
| --- | --- | --- |
| hardware bitmap 创建卡住调用线程 | decode、AHB allocation、GrallocUploadThread、`GrSyncCpu` wait | 看到 queue 1 就认定调用异步返回 |
| RenderThread 慢且 upload 同期发生 | queue 0/1 submission、GPU busy、带宽、频率、调度 | 把两个 queue 直接当成两套 GPU 引擎 |
| `dequeueBuffer` 长等待 | 上一轮 release fence、buffer 数量、SF/HWC/GPU 使用期 | 直接归因于 Vulkan command recording |
| `queueBuffer` 按时但帧晚 | acquire fence、SF latch、composition、present | 把 queue 时间当上屏时间 |
| AGI 有清晰 frame boundary，Perfetto token 对不上 | Vulkan frame ID 与 FrameTimeline vsyncId 分开对齐 | 假设两个 ID 数值相同 |
| partial update 开启但 GPU 仍重 | buffer age、damage、offscreen layer、overdraw、tile load/store | 认为 surface damage 会裁掉所有上游工作 |

### 源码核对索引

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


## 版本与实现边界

下表只陈述固定 release tag 对照能够证明的结果：

| 平台标签 | 双 graphics queue | frame-boundary 相关代码 | global-priority 相关代码 |
| --- | --- | --- | --- |
| `android-14.0.0_r1` | 已有 queue 0 + AHB upload queue 1 | 本次对照未见 Android 17 形态的 boundary 分支 | 已有 `VK_EXT_global_priority` 请求 |
| `android-15.0.0_r1` | 保持双 queue | 本次对照未见 Android 17 形态的 boundary 分支 | 保持 extension 请求 |
| `android-16.0.0_r1` | 保持双 queue | 已有 `VK_EXT_frame_boundary`、AGI 私有扩展与 `fFrameID` | 增加 global-priority query/KHR 相关处理 |
| `android-17.0.0_r1` | 保持双 queue | 保持两条 boundary 路径 | 保持 query 与不支持时的降级处理 |

这张表可以说明 Android 17 固定 tag 中有哪些实现，也能证明双 queue 至少在 Android 14 基线已经存在。若要定位某个提交首次进入主线，还需继续检查相关开发分支与 Git history，不能只根据四个 release tag 推断精确日期。


## 结论

原生 Vulkan 与 HWUI Vulkan 的显示后半段最终都收束到 Android buffer/fence、SurfaceFlinger 与 Display present。原生路径由应用管理 swapchain、submit、barrier 和 pacing；HWUI 路径则由 framework 管理窗口 buffer、Skia context 与内部队列。两者都不能把 API 返回、GPU frame boundary 或 `queueBuffer()` 当成已经上屏。

Android 17 HWUI Vulkan 的双 queue 架构可以概括为四点：

1. queue 0 供 RenderThread 生成 App Window 帧，queue 1 供 GrallocUploadThread 上传 hardware bitmap；
2. 两条 queue 共享 VkDevice，但使用独立 Skia context 与 allocator，可以独立提交，不能保证硬件同时执行；
3. Vulkan frame-boundary 是 GPU 工具标记，FrameTimeline `vsyncId` 才关联窗口的 expected/actual present；
4. dequeue fence 保护旧 buffer 的安全复用，`queueBuffer()` 携带的 producer completion fence 保护 SurfaceFlinger 的安全读取，二者方向相反。

分析问题时，应把 RenderThread、GrallocUploadThread、两条 queue、GPU completion fence、BufferQueue、FrameTimeline 与 present 放进同一时间区间。queue 数量只能说明可独立提交的接口结构，无法单独判断硬件并行度、卡顿原因或用户看到帧的时刻。
