---
title: "Android 17 Vulkan 管线编译与调度策略"
chapter: "22.23"
status: finalized
applicable_versions: "Android 16 (API 36) - Android 17 (API 37)"
last_verified: "2026-08-15"
last_verified_against: "AOSP android-17.0.0_r1"
confidence: high
task6_state: reviewed
task9_state: reviewed
pipeline_stage: finalized
sources:
  - type: aosp
    path: "https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/libs/hwui/renderthread/VulkanManager.cpp"
  - type: aosp
    path: "https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/libs/hwui/renderthread/VulkanManager.h"
  - type: aosp
    path: "https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/libs/hwui/jni/android_graphics_HardwareRenderer.cpp"
  - type: aosp
    path: "https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/libs/hwui/pipeline/skia/PersistentGraphicsCache.cpp"
  - type: aosp
    path: "https://android.googlesource.com/platform/external/skia/+/refs/tags/android-17.0.0_r1/src/gpu/graphite/PipelineManager.cpp"
  - type: aosp
    path: "https://android.googlesource.com/platform/external/skia/+/refs/tags/android-17.0.0_r1/src/gpu/graphite/ResourceProvider.cpp"
  - type: aosp
    path: "https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/services/surfaceflinger/FrameTracer/FrameTracer.cpp"
  - type: aosp
    path: "https://android.googlesource.com/platform/external/perfetto/+/refs/tags/android-17.0.0_r1/protos/perfetto/trace/android/graphics_frame_event.proto"
  - type: official
    path: "https://developer.android.com/guide/topics/graphics/opengl"
  - type: official
    path: "https://source.android.com/docs/core/graphics"
  - type: official
    path: "https://docs.vulkan.org/spec/latest/chapters/pipelines.html"
  - type: official
    path: "https://developer.android.com/about/versions/16/reference/compat-framework-changes"
  - type: official
    path: "https://developer.android.com/about/versions/17/behavior-changes-all"
previous_sources:
  # 旧版元数据值原样保留，便于追溯迁移前的来源配置。
  - "frameworks/base/libs/hwui/renderthread/VulkanManager.cpp (android-17.0.0_r1)"
  - "frameworks/base/libs/hwui/renderthread/VulkanManager.h (android-17.0.0_r1)"
  - "external/skia/src/gpu/graphite/PipelineManager.cpp (android-17.0.0_r1)"
  - "external/skia/src/gpu/graphite/ResourceProvider.cpp (android-17.0.0_r1)"
  - "frameworks/native/services/surfaceflinger/FrameTracer/FrameTracer.cpp (android-17.0.0_r1)"
  - "external/perfetto/protos/perfetto/trace/android/graphics_frame_event.proto"
tags: [Vulkan, GPU, 异步编译, 管线调度, PipelineManager, AGI, Perfetto]
related_chapters: ["2.10", "2.14", "2.24", "22.8"]
---

# Android 17 Vulkan 管线编译与调度策略

“异步编译管线管理器”可以概括一类工程方案，却不是 Android 17 面向所有应用提供的系统接口。普通 View/Compose 应用、直接使用 Vulkan 的游戏，以及经 ANGLE 运行的 OpenGL ES 应用，分别由不同组件创建图形管线，应用可控制的范围也不同。若没有先分清渲染路径，后续看到的缓存、线程、系统跟踪和优化建议很容易互相错配。

本文按 Android 17 / API 37 / `android-17.0.0_r1` 核查平台实现，按 `android17-6.18-2026-06_r6` 核查 Android 内核。内容回答四个问题：

1. 管线创建时间消耗在哪一侧，为什么它会造成帧停顿；
2. Android 17 的 HWUI、Skia Graphite、原生 Vulkan 和 ANGLE 各自负责什么；
3. 应用怎样安排创建任务、保存缓存并设计降级；
4. Perfetto、FrameTimeline、FrameMetrics 和 Android GPU Inspector（AGI）分别能证明什么。

## 一、先确认应用走哪条图形路径

| 应用类型 | Android 17 中的典型路径 | 管线创建的直接控制者 | 应用可直接管理 `VkPipelineCache` |
| --- | --- | --- | --- |
| View / Compose 标准窗口 | UI 线程 → HWUI 渲染线程 `RenderThread` → HWUI → Skia Ganesh → GL 或 Vulkan | HWUI、Skia 和驱动 | 否 |
| 原生 Vulkan / 游戏引擎 | 应用线程 → Vulkan 加载器（loader）→ GPU 厂商驱动 | 应用与驱动 | 是 |
| OpenGL ES | 应用 → EGL/GLES → 原生 GLES 驱动，或 ANGLE → Vulkan | GLES 驱动或 ANGLE | 否 |

同一个 APK 里也可能同时存在多条路径。例如，Activity 的控件由 HWUI 绘制，`SurfaceView` 内的游戏画面由原生 Vulkan 绘制，视频再由独立的缓冲生产者提交。排查时要以发生慢帧的 `Surface` 和进程线程为准。

### 1. Android 17 的 HWUI 仍使用 Ganesh

`android-17.0.0_r1` 的 `Properties.h` 只声明了 `SkiaGL`、`SkiaVulkan` 和 `SkiaCpu` 三种 HWUI 渲染管线。`VulkanManager::createContext()` 返回的是 `GrDirectContexts::MakeVulkan(...)`，其中 `GrDirectContext` 属于 Skia Ganesh。

下面的源码摘录用于确认 Android 17 HWUI 的后端类型，不用于演示应用 API。

```cpp
enum class RenderPipelineType {
    SkiaGL,
    SkiaVulkan,
    SkiaCpu,
    NotInitialized = 128
};

return GrDirectContexts::MakeVulkan(backendContext, options);
```

这两处代码界定了平台边界：AOSP 仓库里虽然包含 Graphite 源码，Android 17 的标准 HWUI Vulkan 上下文仍由 Ganesh 创建。普通 View 或 Compose 页面不能依据 `external/skia/src/gpu/graphite` 的实现细节，推断自己的 `RenderThread` 已经使用 Graphite。

### 2. Vulkan 后端不等于应用拥有 Vulkan

HWUI 选择 Vulkan 后端时，应用仍然向 `Canvas`、`RenderNode` 或 Compose UI 提交绘制描述。`VkDevice`、`VkQueue`、管线缓存和提交同步均由平台管理。应用无法取得 HWUI 内部的 `VkPipelineCache`，也不应通过反射或私有符号干预它。

原生 Vulkan 应用的责任完全不同。它创建 `VkDevice`、管线布局、图形管线、命令缓冲和同步对象，也要决定何时编译、怎样并发以及何时保存缓存。以下涉及编译线程、`VK_PIPELINE_COMPILE_REQUIRED` 和缓存文件的代码只适用于这条路径。

### 3. ANGLE 必须先证明后端已启用

OpenGL ES 应用可能使用设备的原生 GLES 驱动，也可能经 ANGLE 把 GLES 调用翻译为 Vulkan。开发者选项、系统配置、应用包配置和采集工具都可能影响选择结果。

因此，ANGLE 内部的状态缓存不能当作所有 GLES 应用共有的“四级缓存”。应记录 `GL_VENDOR`、`GL_RENDERER`、`GL_VERSION` 和 EGL 信息，并结合设备配置或 AGI 采集方式确认后端。ANGLE 的内部缓存也不等于应用可持久化的原生 `VkPipelineCache`。

## 二、管线创建消耗的是主机端时间

一个 Vulkan 图形管线通常由以下输入共同决定：

- 着色器阶段及其 SPIR-V；
- 管线布局、描述符集布局（descriptor set layout，用于规定着色器怎样绑定缓冲与图像）和推送常量（push constant，用于随命令直接传入少量数据）的范围；
- 顶点输入（vertex input）、图元拓扑、光栅化、深度/模板和混合状态；
- 渲染过程及其子过程（render pass / subpass），或动态渲染（dynamic rendering）所用颜色、深度等附件（attachment）的格式；
- 采样数（sample count）、创建管线时固定的专门化常量（specialization constant），以及未声明为动态状态（dynamic state）的其他状态；
- 驱动版本、GPU 设备及驱动内部策略。

构建时把 GLSL 或 HLSL 编译成 SPIR-V，可以去掉应用进程里的着色器前端编译。厂商驱动仍可能在 `vkCreateGraphicsPipelines()` 中校验、优化并生成设备指令。SPIR-V 文件存在，不代表运行时创建成本已经消失。

`vkCreateGraphicsPipelines()` 是主机端命令。它可以在 `RenderThread` 或编译线程上消耗 CPU 和驱动时间，但这段工作不会作为 GPU 命令提交到某个 `VkQueue`。增加图形队列（graphics queue）数量不会自动提高管线编译并行度。

一次卡顿可能出现以下时间关系。

下面的时间线用于区分主机端创建、GPU 提交和显示完成。

```text
CPU / driver:  build state -> vkCreateGraphicsPipelines -> record -> vkQueueSubmit
GPU:                                                        wait -> execute
BufferQueue:                                                              queue
SurfaceFlinger / display:                                                     latch -> compose -> present
```

`vkCreateGraphicsPipelines()` 过长会推迟录制或提交。GPU 可能在前一段时间处于空闲状态，随后又因提交过晚错过显示期限。它与“GPU 执行着色器太慢”是两种问题，需要不同证据。

### 普通 `uniform` 值通常不会增加管线变体

同一着色器程序和固定状态下，修改普通 `uniform` 变量——绘制时传给着色器、但不写入管线静态状态的数据——通常不需要新建图形管线。下列变化更容易产生新变体：

- 着色器源码或入口发生变化；
- 专门化常量改变；
- 附件格式或采样数改变；
- 混合、深度/模板、图元拓扑等静态状态改变；
- 管线布局不兼容；
- 渲染过程的兼容性条件改变。

优化前应记录管线键由哪些字段组成。把圆角半径、模糊半径或颜色值一概视为“新着色器”，会夸大变体数量；只有这些值被写进着色器源码、专门化常量或其他管线状态时，才会改变对应键。

## 三、标准 View / Compose 应用能做什么

### 1. 平台负责 HWUI 缓存

Android 17 的 `android_graphics_HardwareRenderer.cpp` 会为 OpenGL 着色器缓存、Skia 着色器缓存和 Skia 管线缓存配置不同路径。`PersistentGraphicsCache.cpp` 在 `separate_pipeline_cache` 开关启用时使用独立管线缓存，并在 Vulkan 帧完成刷新（flush）后检查是否出现新数据。该版本源码把一次保存的数据上限写为 2 MiB。

这些都是 `android-17.0.0_r1` 的平台实现细节，不是 SDK 契约。系统可以在后续版本修改文件格式、上限、写入节奏和失效策略。应用无需也无法自行加载这份 HWUI 缓存。

### 2. 应用控制的是变体来源和首次出现时机

标准 UI 应用可从以下位置减少首次使用成本：

- `RuntimeShader` 源码保持稳定，把可变化参数放在 `uniform` 变量中；
- 重用已经创建的 `RuntimeShader`、`RenderEffect`、`Shader` 和 `Paint`，避免在每帧重新构造对象；
- 避免在一次关键点击里同时出现大量此前未渲染的效果、字体、图片格式和图层组合；
- 对必须首用的复杂效果，用目标设备上的真实用户操作衡量是否需要提前初始化；
- 让图片解码尺寸、色彩格式和实际显示需求一致，减少不必要的上传与内存带宽；
- 对可接受的视觉效果准备简单实现，并根据实测帧结果选择。

“在冷启动首帧前绘制不可见的 1×1 View”不是可靠的预编译接口。不可见节点可能不进入绘制，1×1 目标也可能产生不同的裁剪区域（clip）、渲染目标（render target）或图层状态；即使触发了某些编译，它也会把额外工作放进启动关键路径。

若业务需要预热，应使用与线上相同的页面、尺寸、颜色空间和效果组合，放在用户可接受的非关键阶段，并用 Macrobenchmark 证明首个关键操作改善且启动没有退化。标准 HWUI 没有公开 API 保证“预热完成了全部目标管线”。

### 3. Baseline Profile 不保存 GPU 管线

Baseline Profile（基准配置文件）能改善应用 Java/Kotlin 与部分原生代码的编译和执行状态。它不包含厂商 GPU 指令，也不会替代 Skia 或 Vulkan 管线缓存。一次优化同时加入 Baseline Profile 和页面预热后，需要分别验证 CPU 方法执行与图形首次使用成本，避免把收益归错原因。

### 4. `FrameMetrics.GPU_DURATION` 只描述 GPU 完成时间

API 31 起，`FrameMetrics.GPU_DURATION` 表示该帧在 GPU 上完成所用的总时间；`getMetric()` 在指标不可用时返回 `-1`。它没有提供“着色器编译耗时”分类。主机端管线创建发生在提交之前，可能让帧整体变晚，但不一定让 `GPU_DURATION` 变大。

下面的 Kotlin 代码用于正确采集窗口帧指标，并把回调移出主线程。

```kotlin
class WindowFrameMetricsCollector(
    private val window: Window,
    private val onGpuDuration: (gpuDurationNanos: Long, droppedCallbacks: Int) -> Unit,
) : AutoCloseable {
    private val thread = HandlerThread("frame-metrics").apply { start() }
    private val handler = Handler(thread.looper)

    private val listener = Window.OnFrameMetricsAvailableListener {
            _: Window,
            metrics: FrameMetrics,
            droppedSinceLastInvocation: Int,
        ->
        val gpuDuration = metrics.getMetric(FrameMetrics.GPU_DURATION)
        if (gpuDuration >= 0L) {
            onGpuDuration(gpuDuration, droppedSinceLastInvocation)
        }
    }

    fun start() {
        window.addOnFrameMetricsAvailableListener(listener, handler)
    }

    override fun close() {
        window.removeOnFrameMetricsAvailableListener(listener)
        thread.quitSafely()
    }
}
```

监听器注册在 `Window` 上，参数类型是 `android.view.FrameMetrics`。代码只上报可用值，并保留回调丢失数量。线上阈值应来自同一设备组、刷新率和用户操作的分布，不能用固定的 15 ms 推断管线编译。

## 四、HWUI 的两个 Vulkan 队列解决什么问题

`VulkanManager.cpp` 从同一个图形队列族（graphics queue family，一组能力和调度属性相同的队列）请求两个 `VkQueue`：索引 0 保存到 `mGraphicsQueue`，索引 1 保存到 `mAHBUploadQueue`。`HardwareBitmapUploader` 创建上传用的 Ganesh 上下文时选择后者。

下面的源码摘录用于核对队列数量、优先级数组和索引。

```cpp
constexpr auto kRequestedQueueCount = 2;
float queuePriorities[kRequestedQueueCount] = {0.0};

// 同一个 VkDeviceQueueCreateInfo:
// queueFamilyIndex = mGraphicsQueueIndex
// queueCount = kRequestedQueueCount
// pQueuePriorities = queuePriorities

mGetDeviceQueue(mDevice, mGraphicsQueueIndex, 0, &mGraphicsQueue);
mGetDeviceQueue(mDevice, mGraphicsQueueIndex, 1, &mAHBUploadQueue);
```

这段实现有四个边界：

1. 两个队列来自同一个队列族；
2. `queuePriorities` 的两个元素都为 `0.0f`；
3. 可选的全局队列优先级（global priority）挂在同一份 `VkDeviceQueueCreateInfo` 上，没有为上传队列设置单独的低优先级；
4. Vulkan 允许多个队列独立提交，但设备可以在同一硬件引擎上串行执行，源码无法保证物理并行。

`VK_EXT_global_priority` 也不是普通应用可依赖的“渲染高、上传低”策略。HWUI 只有在上下文优先级非零、扩展可用且请求值满足设备条件时，才会附加全局队列优先级；不支持时会放弃该请求或由驱动返回错误。

`HardwareBitmapUploader` 的 Vulkan 路径使用专用上传线程和上传队列，但代码内部还会调用 `queue().runSync(...)`，提交时使用 `GrSyncCpu::kYes`。这表示上传工作与 `RenderThread` 使用不同上下文和队列，不表示每个调用都能让调用者立即返回。

两个队列的价值在于隔离提交状态，并减少相互等待的机会。最终能否并行、内存带宽是否竞争、上传是否延迟渲染，仍要在目标设备上查看 GPU 阶段和同步栅栏（fence）。

## 五、Graphite `PipelineManager` 的准确边界

### 1. `PipelineCreationTask` 先处理重复请求

`external/skia` 的 Graphite `PipelineManager::createHandle()` 按以下次序处理请求：

1. 查询同一个管线键是否已有正在执行的任务；
2. 查询全局缓存是否已有管线；
3. 在自旋锁（spinlock，等待期间持续检查锁状态的轻量锁）保护下再次确认，并创建或复用任务。

这个设计避免并发请求为同一个键重复创建管线。`SkSpinlock` 只保护正在执行的任务表及其短临界区；它不是管线编译队列，也没有“先到请求拥有更高优先级”的语义。

### 2. Android 17 标签中的 Vulkan 基础实现是同步调用

`PipelineCreationTask.h` 把任务描述为“可能交给线程的工作单元”。“可能”不能省略。`PipelineManager::startPipelineCreationTask()` 在当前实现中直接调用 `SharedContext::findOrCreateGraphicsPipeline()`，完成后设置 `fCompleted`。`resolveHandle()` 还明确说明，非线程版本在执行到这里之前已经完成任务。

`DrawPass::prepareResources()` 的当前顺序是：

- 创建句柄（handle）；
- 立即调用 `startPipelineCreationTask()`；
- 随后调用 `resolveHandle()`。

所以，不能把它概括为“在 `snap` 时派发到后台，到 `insertRecording` 时统一等待”。是否异步取决于具体后端、执行器（executor，即负责把任务交给线程运行的调度实现）和调用方式；`android-17.0.0_r1` 的这条 Vulkan 基础路径没有展示一个通用的后台编译调度器。

### 3. Graphite 跟踪名称不能套到 HWUI

该标签中的 Graphite Vulkan 源码使用 `skia.shaders` 跟踪类别，并包含下列已核对的区间名称：

- `CreateGraphicsPipeline`
- `CreateGraphicsPipeline-CacheLookup`
- `CreateGraphicsPipeline-CompileAfterCacheMiss`
- `CreateGraphicsPipeline-CacheLookupOrCompile`

这些名称只在相应 Graphite 构建和跟踪配置中有意义。AOSP 没有一个可对所有应用保证的 `gpu.graphite` 轨道（track，即 Perfetto 中按线程或数据源组织的一行时间数据）。标准 Android 17 HWUI 使用 Ganesh；即使看到 `RenderThread` 的 `flush` 区间变长，也不足以认定 Graphite 任务正在等待。

Graphite 的 Vulkan 实现仍提供了一种可参考的控制方式：设备支持管线创建缓存控制（pipeline creation cache control）时，它先带 `FAIL_ON_PIPELINE_COMPILE_REQUIRED` 查询缓存；收到 `VK_PIPELINE_COMPILE_REQUIRED` 后，去掉该标志，再执行允许编译的调用。原生 Vulkan 引擎可以采用相同思路，但必须自行安排编译线程和降级管线。

## 六、原生 Vulkan 的任务调度

### 1. 构建稳定的管线键

应用应先为每个可执行管线定义稳定键。键至少覆盖：

- 着色器内容哈希、入口和专门化常量；
- 管线布局版本；
- 附件格式、采样数与渲染模式；
- 所有静态光栅化、深度/模板和混合状态；
- 会影响兼容性的引擎版本。

管线键用于任务去重、缓存统计和回归定位。不要把整个 `VkGraphicsPipelineCreateInfo` 直接浅拷贝进工作队列，它含有大量指针；调用者离开作用域后，编译线程可能读到失效内存。队列应保存 `PipelineKey`，或持有完整、不可变的创建配方，并由编译线程在调用时重建创建信息结构（create info）。

### 2. 队列只接收缺失且仍需要的任务

一个实用状态机可以包含：

| 状态 | 含义 | 前台渲染行为 |
| --- | --- | --- |
| `Unknown` | 尚未查询内存表或驱动缓存 | 发起仅缓存查询 |
| `Ready` | 已有可绑定的 `VkPipeline` | 直接使用 |
| `Queued` | 管线键已进入编译队列 | 使用兼容的降级管线或延后该物体 |
| `Compiling` | 编译线程正在创建 | 不重复提交 |
| `Failed` | 创建失败，保留 `VkResult` 和上下文 | 选择明确降级，限制重试 |

任务优先级应来自用户可见性和截止时间。例如，当前加载界面即将结束的场景高于远处尚未加载的关卡。优先级不能从“着色器代码越短越高”推导；源码长度与驱动创建成本没有稳定对应关系。

编译线程数量也没有通用答案。过多线程会争用 CPU、驱动内部锁和管线缓存。应在代表设备上比较 1、2、4 个编译线程的总完成时间、关键线程调度和峰值内存，再决定上限。

### 3. 用仅缓存查询保护渲染线程

Vulkan 1.3 核心功能包含管线创建缓存控制；较旧实现可通过 `VK_EXT_pipeline_creation_cache_control` 提供同类能力。应用必须查询并启用对应功能位（feature），不能仅凭 API 版本字符串使用标志。

下面的 C++ 函数用于执行一次“不允许现场编译”的图形管线查询。

```cpp
VkResult tryCreateCachedGraphicsPipeline(
        VkDevice device,
        VkPipelineCache cache,
        const VkGraphicsPipelineCreateInfo& baseInfo,
        VkPipeline* pipeline) {
    VkGraphicsPipelineCreateInfo queryInfo = baseInfo;
    queryInfo.flags |=
            VK_PIPELINE_CREATE_FAIL_ON_PIPELINE_COMPILE_REQUIRED_BIT;
    *pipeline = VK_NULL_HANDLE;
    return vkCreateGraphicsPipelines(
            device,
            cache,
            1,
            &queryInfo,
            nullptr,
            pipeline);
}
```

调用期间，`baseInfo` 引用的所有数组和 `pNext` 结构必须保持有效。返回 `VK_SUCCESS` 时可发布管线；返回 `VK_PIPELINE_COMPILE_REQUIRED` 时，应把对应键交给编译线程，并让它用不带该标志的创建信息执行允许编译的调用。其他错误要按 `VkResult` 处理，不能全部当成缓存未命中（cache miss）。

这个标志只阻止当前调用执行昂贵编译，不会自动创建后台任务，也不提供降级管线。降级管线必须与渲染过程、管线布局、描述符绑定和资源格式兼容；兼容条件无法满足时，应延后绘制，不能绑定错误管线。

### 4. 控制并发与发布

编译线程完成 `vkCreateGraphicsPipelines()` 后，应通过互斥锁、原子状态或线程安全队列把结果发布给渲染线程。发布前不能让其他线程看到只初始化了一部分的业务对象。`VkPipeline` 的销毁要等待使用它的 GPU 工作完成，不能因为业务键被替换，就立即销毁仍被命令缓冲（command buffer）引用的管线。

默认创建的 `VkPipelineCache` 可由多个线程同时传给管线创建命令，规范要求驱动对这种使用做内部同步。如果创建缓存时设置了 `VK_PIPELINE_CACHE_CREATE_EXTERNALLY_SYNCHRONIZED_BIT`，应用就接管了修改命令的同步责任，所有会修改该缓存的调用都要按规范串行化。

驱动的内部同步仍可能限制扩展性。两种常见方案都需要实测：

- 多个编译线程共用一个默认缓存，代码简单，驱动负责同步；
- 每个编译线程使用独立缓存，在受控时点用 `vkMergePipelineCaches()` 合并。

后一种方案会增加内存、合并和持久化复杂度。没有测量结果时，共用默认缓存更容易保持正确。

## 七、正确保存 `VkPipelineCache`

### 1. 缓存数据是不透明的驱动数据

`vkGetPipelineCacheData()` 返回的内容可以在后续运行中作为初始数据传给 `VkPipelineCacheCreateInfo::pInitialData`。除文件头（header）外，其余字节都是驱动定义的不透明数据；应用不能自行解释，也不能把一个设备的数据分发给所有设备。

版本一文件头包含：

- `headerSize`；
- `headerVersion`；
- `vendorID`；
- `deviceID`；
- `pipelineCacheUUID`。

驱动会忽略不兼容的初始数据。应用仍应在加载前校验文件头，以便删除损坏文件、记录失效原因，并避免把无关数据反复交给驱动。缓存文件名还应包含应用的图形资源版本；着色器或管线布局发生不兼容变更时，应使用新的命名空间。

下面的 C++ 函数按 Vulkan 规定的小端字节布局，校验版本一文件头。

```cpp
bool isCompatiblePipelineCache(
        std::span<const std::byte> data,
        const VkPhysicalDeviceProperties& properties) {
    constexpr size_t kHeaderSize = 4 * sizeof(uint32_t) + VK_UUID_SIZE;
    if (data.size() < kHeaderSize) {
        return false;
    }

    const auto readLe32 = [&data](size_t offset) {
        return static_cast<uint32_t>(std::to_integer<uint8_t>(data[offset])) |
                (static_cast<uint32_t>(
                         std::to_integer<uint8_t>(data[offset + 1]))
                 << 8) |
                (static_cast<uint32_t>(
                         std::to_integer<uint8_t>(data[offset + 2]))
                 << 16) |
                (static_cast<uint32_t>(
                         std::to_integer<uint8_t>(data[offset + 3]))
                 << 24);
    };

    return readLe32(0) == kHeaderSize &&
            readLe32(4) == VK_PIPELINE_CACHE_HEADER_VERSION_ONE &&
            readLe32(8) == properties.vendorID &&
            readLe32(12) == properties.deviceID &&
            std::memcmp(
                    data.data() + 4 * sizeof(uint32_t),
                    properties.pipelineCacheUUID,
                    VK_UUID_SIZE) == 0;
}
```

这段代码没有依赖 C++ 结构体的填充字节（padding）。调用文件需要包含 `<cstddef>`、`<cstdint>`、`<cstring>` 和 `<span>`。检查通过后仍要处理 `vkCreatePipelineCache()` 的返回值；文件头兼容只说明数据可以尝试使用，不保证每次创建或后续查询都会命中缓存。

### 2. 写文件要服从 Vulkan 对象生命周期

可靠的保存流程如下：

1. 停止接收新的管线创建任务，并等待当前编译线程到达约定的安全点；
2. 第一次调用 `vkGetPipelineCacheData()` 取得所需大小；
3. 分配缓冲并再次调用，接受 `VK_SUCCESS`，按设计处理 `VK_INCOMPLETE`；
4. 写到同目录临时文件，`fsync` 需求由产品的数据耐久策略决定；
5. 原子替换正式文件；
6. 保存成功后再更新业务版本标记。

这里暂停编译线程，主要是为了得到与当前引擎版本一致、便于复现的快照，并避免与缓存或设备销毁过程交错。若使用外部同步缓存，即设置了 `VK_PIPELINE_CACHE_CREATE_EXTERNALLY_SYNCHRONIZED_BIT`，还必须满足对应的主机端同步要求。

不要在每一帧写缓存。适合的时机包括加载阶段结束、累计产生新管线后的受控后台时点，以及正常退出流程中仍有足够生命周期时。Android 进程可能被直接终止，缓存正确性不能依赖退出回调一定执行。

### 3. 缓存失效要使用图形身份

推荐的缓存身份至少包含：

- `vendorID`、`deviceID` 和 `pipelineCacheUUID`；
- 应用或引擎的管线结构版本；
- 着色器包内容版本；
- 影响创建信息的渲染配置版本。

`Build.SOC_MODEL` 表示片上系统（system-on-chip，SoC）的型号，适合用作诊断标签，不适合单独决定缓存兼容性。系统升级后若 `pipelineCacheUUID` 改变，应丢弃旧数据；如果 UUID 没变，仍由驱动判断初始数据是否可用。

## 八、可选 Vulkan 能力怎样使用

### 1. 管线创建反馈

Vulkan 1.3 核心类型 `VkPipelineCreationFeedback`（或对应的扩展别名）用于返回管线创建耗时和状态标志。只有 `VK_PIPELINE_CREATION_FEEDBACK_VALID_BIT` 置位时，其余字段才有定义；`duration` 的单位是纳秒。

`VK_PIPELINE_CREATION_FEEDBACK_APPLICATION_PIPELINE_CACHE_HIT_BIT` 表示驱动从应用传入的管线缓存中找到了可立即使用的结果，从而避开了大部分创建工作。这个反馈适合统计真实管线键的命中率和创建耗时分布，比预设“单条管线必须小于多少毫秒”更可靠。

反馈是驱动对一次创建调用的报告，不是 GPU 执行时间。使用时应同时记录管线键、线程、场景、创建结果、是否命中缓存和调用耗时，但线上日志不要包含着色器源码，也不要生成数量不受控的动态名称。

### 2. 图形管线库

`VK_EXT_graphics_pipeline_library` 可以把图形管线分为四部分：顶点输入接口（vertex input interface）、光栅化前着色器（pre-rasterization shaders）、片段着色器（fragment shader）和片段输出接口（fragment output interface）。应用可以复用公共部分，再把它们链接为可执行管线。该扩展依赖 `VK_KHR_pipeline_library`，并提供独立的功能位和属性（properties，描述设备支持程度但不能由应用启用的只读值）。

应用需要查询并启用 `graphicsPipelineLibrary` 功能位。`graphicsPipelineLibraryFastLinking` 属性会影响即时链接策略：值为 `VK_TRUE` 时，不使用链接时优化的链接成本应与录制一条命令相近；值为 `VK_FALSE` 时，链接通常仍比完整编译便宜，但不能再假定成本接近命令录制。链接时优化（link-time optimization）还可能用更长的创建时间换取更好的运行性能。

该扩展适合材质组合多、公共状态复用明显的引擎。它不会消除变体数量，也不保证所有 Android 17 设备支持。接入前要比较：

- 加载总时间；
- 首次使用的长尾；
- 管线缓存体积；
- 链接后 GPU 执行时间；
- 驱动稳定性和内存增长。

### 3. 动态状态

设备支持相应动态状态时，把频繁变化的固定功能状态改为录制命令时设置，可以减少管线组合数。代价可能包括驱动路径差异、录制复杂度和运行时性能变化。应从实际管线键统计中找出取值种类很多的维度，再选择设备能力允许的状态，不能一次性启用所有动态状态。

## 九、把创建任务放在合适的用户阶段

### 普通 UI

普通 UI 没有公开的管线编译队列。优化重点是减少不必要的效果变体，让目标效果在可接受阶段首次出现，并以真实页面的帧结果验证。若某效果只在低频入口出现，提前初始化它可能只会增加大多数用户的启动与内存成本。

### 游戏和原生渲染器

游戏可以在加载界面、关卡流式加载或资源包安装后创建下一阶段必需的管线。进度条应由已完成的必要任务驱动，不能只按已提交任务数量推进。加载结束前要确认当前场景的必需集合进入 `Ready`，可选集合可以延迟创建或使用兼容的降级管线。

任务优先级建议考虑：

- 距离可见的帧数或场景阶段；
- 是否存在视觉可接受的降级管线；
- 资源依赖是否已经就绪；
- 该管线键是否正在创建；
- 最近的创建耗时分布；
- 当前 CPU 热状态和编译队列长度。

设备策略应基于运行时功能位、属性和实测分布。按“高端、中端、低端”写死 SoC 名单很快会失效，也无法反映同一 GPU 在不同驱动和散热状态下的差异。

### 热更新

着色器包或原生引擎更新后，应提升业务管线结构版本或着色器包版本。只删除发生变化的逻辑键可以减少重建量，但驱动缓存本身是整体不透明数据；应用不能从二进制文件中安全移除单个条目。

灰度期间应比较相同设备身份、相同场景和相同刷新率下的：

- 仅缓存查询命中率；
- 管线创建反馈的长尾耗时；
- 加载时长；
- 首次交互慢帧；
- GPU 执行时间；
- 缓存文件体积和创建失败率。

## 十、诊断时按时间域收集证据

### 1. 原生 Vulkan：在调用点添加固定跟踪标记

原生引擎能直接测量自己的管线创建。跟踪标记（trace marker）名称应固定，动态管线键应写入结构化遥测字段，避免为每个键生成新的跟踪名称。

下面的 C++ 代码用于测量一次主机端创建调用，并在 Perfetto 中留下可定位的区间。

```cpp
struct PipelineCreateSample {
    VkResult result;
    VkPipeline pipeline;
    int64_t wallTimeNanos;
};

PipelineCreateSample createMeasuredGraphicsPipeline(
        VkDevice device,
        VkPipelineCache cache,
        const VkGraphicsPipelineCreateInfo& createInfo) {
    ATrace_beginSection("NativeVulkan::CreateGraphicsPipeline");
    const auto begin = std::chrono::steady_clock::now();

    VkPipeline pipeline = VK_NULL_HANDLE;
    const VkResult result = vkCreateGraphicsPipelines(
            device,
            cache,
            1,
            &createInfo,
            nullptr,
            &pipeline);

    const auto end = std::chrono::steady_clock::now();
    const auto wallTimeNanos =
            std::chrono::duration_cast<std::chrono::nanoseconds>(
                    end - begin)
                    .count();
    ATrace_endSection();
    return PipelineCreateSample{result, pipeline, wallTimeNanos};
}
```

调用文件需要包含 `<android/trace.h>`、`<chrono>` 和 `<cstdint>`。显式转换保证 `wallTimeNanos` 使用纳秒单位。`ATrace` 区间和调用耗时都描述调用线程上的主机端时间；GPU 是否繁忙、该管线后续执行多久，需要 GPU 跟踪、时间戳查询（timestamp query）或 AGI 提供独立证据。

### 2. 标准 HWUI：只能做关联，不能越级归因

在标准 View/Compose 页面中，应用看不到 HWUI 内部每个 `vkCreateGraphicsPipelines()` 调用。排查顺序可以是：

1. 用 FrameTimeline 找到同一用户操作中的慢帧，并区分应用与 SurfaceFlinger 两侧；
2. 检查主线程是否及时完成 UI、测量、布局和绘制记录；
3. 检查 `RenderThread` 是否在同一帧出现异常长区间或提交变晚；
4. 比较效果首次出现与重复出现；
5. 用可控开关移除某个 `RuntimeShader`、`RenderEffect` 或图层组合后复测；
6. 需要源码级结论时，使用带对应平台跟踪点的系统构建或 GPU 厂商工具。

“首次出现时 `RenderThread` 变长、第二次恢复”是缓存或初始化问题的线索，还可能来自字形栅格化、图片上传、图层分配、驱动初始化等工作。没有调用级证据时，结论应写成相关性。

### 3. AGI 的适用范围

AGI 的帧分析器（Frame Profiler）可以展示 Vulkan API 调用、管线数据、渲染状态、着色器资源和 GPU 性能数据。它适合直接使用 Vulkan 的应用；对 OpenGL ES，AGI 会使用定制 ANGLE，把调用翻译为 Vulkan 后再采集单帧。这个采集环境可能不同于用户设备原本的 GLES 后端，结论要标明条件。

AGI 能看到一帧内的 API 调用和 GPU 工作，但长时间加载阶段不能只靠单帧采集解释。大量管线预编译应同时使用系统跟踪、引擎遥测和阶段统计。

### 4. 缓冲生命周期只能缩小范围

渲染链路中常见的时间段可以这样读取：

| 时间段 | 可以说明 | 不能单独说明 |
| --- | --- | --- |
| `DEQUEUE → QUEUE` | 缓冲生产者（producer）从取得缓冲到提交缓冲的总区间变长 | 具体由管线创建、CPU 绘制、GPU 执行还是等待造成 |
| `QUEUE → LATCH` | 缓冲提交后没有在预期时点被 SurfaceFlinger 采用 | 着色器编译发生在 GPU，或 SurfaceFlinger 一定在等待该编译 |
| `LATCH → PRESENT` | 合成、显示调度和呈现相关区间变长 | 应用的 `RenderThread` 正在编译着色器 |

`queueBuffer()` 返回只表示缓冲生产者完成了提交动作。`vkQueueSubmit()` 和 `vkQueuePresentKHR()` 返回也不等于 GPU 工作完成或像素已经显示。还要查看获取、释放和呈现同步栅栏（acquire/release/present fence）、FrameTimeline 与显示事件。

### 5. 内核证据的责任范围

`android17-6.18-2026-06_r6` 可用于解释：

- 编译线程或 `RenderThread` 是否获得 CPU；
- 唤醒后是否长时间等待调度；
- `dma-fence` / `sync_file`（Linux 内核与用户空间传递同步完成状态的机制）何时发出完成信号；
- CPU 频率、空闲状态、热限制和内存压力是否影响主机端调用；
- GPU 厂商驱动线程是否出现可观察的等待。

通用内核代码不知道业务 `PipelineKey`，也无法仅凭一个同步栅栏名称判断驱动正在编译哪段着色器。GPU 指令编译和执行的详细原因通常需要厂商驱动跟踪、AGI 或应用自己的调用标记。

## 十一、常见错误结论

| 错误结论 | 修正后的判断 |
| --- | --- |
| Android 17 HWUI 默认使用 Graphite | `android-17.0.0_r1` 的 HWUI 创建 Ganesh `GrDirectContext` |
| `PipelineCreationTask` 一定在后台线程执行 | 当前 Graphite 基础实现可在调用线程直接创建并立即解析句柄（resolve） |
| 两个 Vulkan 队列能并行编译管线 | 管线创建是主机端命令，队列承载 GPU 提交 |
| HWUI 给渲染队列高优先级、上传队列低优先级 | 两个队列使用同一份创建信息，优先级数组均为 `0.0f` |
| 有 SPIR-V 就没有运行时编译 | 厂商驱动仍可能在管线创建中生成设备代码 |
| `GPU_DURATION` 变高可确认着色器编译 | 该指标描述 GPU 完成时间，不提供主机端编译归因 |
| `DEQUEUE → QUEUE` 长就能确认编译卡顿 | 它只限定缓冲生产者区间，仍需调用级和线程证据 |
| 改变普通 `uniform` 一定生成新管线 | 普通 `uniform` 值通常不进入管线键 |
| Android 17 设备都支持图形管线库 | 必须在运行时查询该设备扩展和功能位 |
| Baseline Profile 会预编译 GPU 管线 | 它针对应用代码执行，不保存厂商 GPU 管线 |

## 十二、版本边界

| 项目 | 采用的边界 |
| --- | --- |
| Android 平台 | Android 17 / API 37 / `android-17.0.0_r1` |
| HWUI | 标准路径按 Skia Ganesh 核查；不把 Graphite 源码等同于 HWUI 默认实现 |
| Vulkan | 以设备实际报告并启用的 API、扩展、功能位和属性为准 |
| Android 内核 | `android17-6.18-2026-06_r6`，用于调度、同步栅栏和驱动线程证据 |
| 厂商驱动 | 设备相关；AOSP 公共源码无法保证编译并行度、缓存命中成本和 GPU 队列的物理并行 |

Android 16 的历史数据可以用于对比，但相关源码名称、跟踪标记和 HWUI 缓存实现只对 Android 17 锚点作核查。后续平台若把 HWUI 切换到 Graphite，应重新核对 `RenderPipelineType`、上下文创建点、管线任务执行方式和跟踪类别，不能沿用这里的结论。

## 十三、工程检查清单

### 标准 View / Compose

- [ ] 已确认慢帧属于目标应用窗口和目标 `Surface`；
- [ ] 已区分 UI 主线程、`RenderThread`、GPU、SurfaceFlinger 和显示阶段；
- [ ] 没有把 Graphite 源码当成 Android 17 HWUI 默认路径；
- [ ] `RuntimeShader` 的变化参数优先使用 `uniform`；
- [ ] 没有用不可见 1×1 View 代替真实场景验证；
- [ ] `FrameMetrics.GPU_DURATION` 只用于 GPU 时间统计；
- [ ] 优化前后使用相同设备、刷新率和用户操作复测。

### 原生 Vulkan

- [ ] 管线键覆盖着色器、管线布局、附件和静态状态；
- [ ] 编译线程持有不可变创建配方，未浅拷贝悬空指针；
- [ ] 已查询并启用管线创建缓存控制；
- [ ] 仅缓存查询未命中时会进入去重队列，不会在渲染线程直接编译；
- [ ] 降级管线与管线布局、渲染过程和资源绑定兼容；
- [ ] 编译线程数量来自目标设备实测；
- [ ] 管线缓存文件头校验厂商 ID、设备 ID 和 UUID；
- [ ] 缓存通过临时文件和原子替换保存；
- [ ] 外部同步缓存有明确同步策略；
- [ ] 管线销毁等待相关 GPU 使用完成；
- [ ] 创建反馈、`ATrace` 和 GPU 数据分别记录主机端创建与 GPU 执行。

## 参考资料

- [AOSP `Properties.h`：HWUI RenderPipelineType（android-17.0.0_r1）](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/libs/hwui/Properties.h)
- [AOSP `VulkanManager.cpp`：HWUI Vulkan device、queue 与 Ganesh context](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/libs/hwui/renderthread/VulkanManager.cpp)
- [AOSP `HardwareBitmapUploader.cpp`：上传线程与 upload context](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/libs/hwui/HardwareBitmapUploader.cpp)
- [AOSP `android_graphics_HardwareRenderer.cpp`：三类持久化图形缓存路径](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/libs/hwui/jni/android_graphics_HardwareRenderer.cpp)
- [AOSP `PersistentGraphicsCache.cpp`：HWUI 持久化图形缓存](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/libs/hwui/pipeline/skia/PersistentGraphicsCache.cpp)
- [Skia Graphite `PipelineManager.cpp`（android-17.0.0_r1）](https://android.googlesource.com/platform/external/skia/+/refs/tags/android-17.0.0_r1/src/gpu/graphite/PipelineManager.cpp)
- [Skia Graphite `DrawPass.cpp`（android-17.0.0_r1）](https://android.googlesource.com/platform/external/skia/+/refs/tags/android-17.0.0_r1/src/gpu/graphite/DrawPass.cpp)
- [Skia Graphite `VulkanGraphicsPipeline.cpp`（android-17.0.0_r1）](https://android.googlesource.com/platform/external/skia/+/refs/tags/android-17.0.0_r1/src/gpu/graphite/vk/VulkanGraphicsPipeline.cpp)
- [Vulkan Pipeline Cache 规范](https://docs.vulkan.org/spec/latest/chapters/pipelines.html#pipelines-cache)
- [Vulkan pipeline creation cache control](https://docs.vulkan.org/refpages/latest/refpages/source/VK_EXT_pipeline_creation_cache_control.html)
- [Vulkan pipeline creation feedback](https://docs.vulkan.org/refpages/latest/refpages/source/VK_EXT_pipeline_creation_feedback.html)
- [Vulkan graphics pipeline library](https://docs.vulkan.org/refpages/latest/refpages/source/VK_EXT_graphics_pipeline_library.html)
- [Android 16（API 36）兼容性框架变更](https://developer.android.com/about/versions/16/reference/compat-framework-changes)
- [Android 17（API 37）行为变更](https://developer.android.com/about/versions/17/behavior-changes-all)
- [Android Vulkan 原生引擎支持](https://developer.android.com/games/develop/vulkan/native-engine-support)
- [Android `FrameMetrics` API](https://developer.android.com/reference/android/view/FrameMetrics)
- [Android GPU Inspector Frame Profiler](https://developer.android.com/agi/frame-trace/frame-profiler)
