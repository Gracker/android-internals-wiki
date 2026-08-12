---
title: "Android 17 Vulkan 管线编译与调度策略"
chapter: "22.23"
status: ready-for-review
applicable_versions: "Android 16 (API 35) - Android 17 (API 37)"
last_verified: "2026-06-28"
last_verified_against: "AOSP android-17.0.0_r1"
confidence: medium
sources:
  - type: aosp
    path: "frameworks/base/libs/hwui/renderthread/VulkanManager.cpp (android-17.0.0_r1)"
  - type: aosp
    path: "frameworks/base/libs/hwui/renderthread/VulkanManager.h (android-17.0.0_r1)"
  - type: aosp
    path: "external/skia/src/gpu/graphite/PipelineManager.cpp (android-17.0.0_r1)"
  - type: aosp
    path: "external/skia/src/gpu/graphite/ResourceProvider.cpp (android-17.0.0_r1)"
  - type: aosp
    path: "frameworks/native/services/surfaceflinger/FrameTracer/FrameTracer.cpp (android-17.0.0_r1)"
  - type: aosp
    path: "external/perfetto/protos/perfetto/trace/android/graphics_frame_event.proto"
  - type: official
    path: "https://developer.android.com/guide/topics/graphics/opengl"
  - type: official
    path: "https://source.android.com/docs/core/graphics"
tags: [Vulkan, GPU, 异步编译, 管线调度, PipelineManager, AGI, Perfetto]
related_chapters: ["2.10", "2.14", "2.24", "22.8"]
---

# Android 17 Vulkan 管线编译与调度策略

“异步编译管线管理器”适合作为工程问题的名称，却不是 Android 17 对所有应用公开的一项系统能力。普通 View/Compose 应用、直接使用 Vulkan 的游戏，以及经 ANGLE 运行的 OpenGL ES 应用，管线由不同组件创建，应用可控制的范围也不同。若一开始没有分清路径，后续看到的缓存、线程、Trace 和优化建议很容易互相错配。

平台锚点固定为 Android 17 / API 37 / `android-17.0.0_r1`，kernel 锚点固定为 `android17-6.18-2026-06_r6`。以下回答四个问题：

1. 管线创建时间消耗在哪一侧，为什么它会造成帧停顿；
2. Android 17 的 HWUI、Skia Graphite、原生 Vulkan 和 ANGLE 各自负责什么；
3. 应用怎样安排创建任务、保存缓存并设计降级；
4. Perfetto、FrameTimeline、FrameMetrics 和 AGI 分别能证明什么。

## 一、先确认应用走哪条图形路径

| 应用类型 | Android 17 中的典型路径 | 管线创建的直接控制者 | 应用可直接管理 `VkPipelineCache` |
| --- | --- | --- | --- |
| View / Compose 标准窗口 | UI 线程 → RenderThread → HWUI → Skia Ganesh → GL 或 Vulkan | HWUI、Skia 和驱动 | 否 |
| 原生 Vulkan / 游戏引擎 | 应用线程 → Vulkan loader → 厂商驱动 | 应用与驱动 | 是 |
| OpenGL ES | 应用 → EGL/GLES → 原生 GLES 驱动，或 ANGLE → Vulkan | GLES 驱动或 ANGLE | 否 |

同一个 APK 里也可能同时存在多条路径。例如，Activity 的控件由 HWUI 绘制，`SurfaceView` 内的游戏画面由原生 Vulkan 绘制，视频再由独立生产者提交缓冲。排查时要以发生慢帧的 Surface 和进程线程为准。

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

这两处代码把平台边界说得很清楚：AOSP 仓库里虽然包含 Graphite 源码，Android 17 的标准 HWUI Vulkan 上下文仍由 Ganesh 创建。普通 View 或 Compose 页面不能依据 `external/skia/src/gpu/graphite` 的实现细节，推断自己的 RenderThread 已经使用 Graphite。

### 2. Vulkan 后端不等于应用拥有 Vulkan

HWUI 选择 Vulkan 后端时，应用仍然向 `Canvas`、`RenderNode` 或 Compose UI 提交绘制描述。`VkDevice`、`VkQueue`、管线缓存和提交同步均由平台管理。应用无法取得 HWUI 内部的 `VkPipelineCache`，也不应通过反射或私有符号干预它。

原生 Vulkan 应用的责任完全不同。它创建 `VkDevice`、管线布局、图形管线、命令缓冲和同步对象，也要决定何时编译、怎样并发以及何时保存缓存。以下涉及编译线程、`VK_PIPELINE_COMPILE_REQUIRED` 和缓存文件的代码只适用于这条路径。

### 3. ANGLE 必须先证明后端已启用

OpenGL ES 应用可能使用设备的原生 GLES 驱动，也可能经 ANGLE 翻译为 Vulkan。开发者选项、系统配置、应用包配置和采集工具都可能影响选择结果。

因此，ANGLE 内部的状态缓存不能当作所有 GLES 应用共有的“四级缓存”。应记录 `GL_VENDOR`、`GL_RENDERER`、`GL_VERSION` 和 EGL 信息，并结合设备配置或 AGI 采集方式确认后端。ANGLE 的内部缓存也不等于应用可持久化的原生 `VkPipelineCache`。

## 二、管线创建消耗的是主机端时间

一个 Vulkan 图形管线通常由以下输入共同决定：

- 着色器阶段及其 SPIR-V；
- 管线布局、descriptor set layout 和 push constant 范围；
- vertex input、拓扑、光栅化、深度模板和混合状态；
- render pass / subpass，或 dynamic rendering 的 attachment 格式；
- sample count、specialization constant 和未声明为 dynamic 的状态；
- 驱动版本、GPU 设备及驱动内部策略。

构建时把 GLSL 或 HLSL 编译成 SPIR-V，可以去掉应用进程里的着色器前端编译。厂商驱动仍可能在 `vkCreateGraphicsPipelines()` 中校验、优化并生成设备指令。SPIR-V 文件存在，不代表运行时创建成本已经消失。

`vkCreateGraphicsPipelines()` 是主机端命令。它可以在 RenderThread 或编译线程上消耗 CPU 和驱动时间，但这段工作没有作为命令提交到某个 `VkQueue`。增加 graphics queue 数量不会自动提高管线编译并行度。

一次卡顿可能出现以下时间关系。

下面的时间线用于区分主机端创建、GPU 提交和显示完成。

```text
CPU / driver:  build state -> vkCreateGraphicsPipelines -> record -> vkQueueSubmit
GPU:                                                        wait -> execute
BufferQueue:                                                              queue
SurfaceFlinger / display:                                                     latch -> compose -> present
```

`vkCreateGraphicsPipelines()` 过长会推迟录制或提交。GPU 可能在前一段时间处于空闲状态，随后又因提交过晚错过显示期限。它与“GPU 执行着色器太慢”是两种问题，需要不同证据。

### Uniform 值通常不会增加管线变体

同一着色器程序和固定状态下，修改普通 uniform 值通常不需要新建图形管线。以下变化更容易产生新变体：

- 着色器源码或入口发生变化；
- specialization constant 改变；
- attachment 格式或 sample count 改变；
- blend、depth/stencil、topology 等静态状态改变；
- 管线布局不兼容；
- render pass 兼容性条件改变。

优化前应记录管线键的组成。把圆角半径、模糊半径或颜色值一概视为“新着色器”，会夸大变体数量；只有这些值被写进着色器源码、specialization constant 或其他管线状态时，才会改变对应键。

## 三、标准 View / Compose 应用能做什么

### 1. 平台负责 HWUI 缓存

Android 17 的 `android_graphics_HardwareRenderer.cpp` 会为 OpenGL shader cache、Skia shader cache 和 Skia pipeline cache 配置不同路径。`PersistentGraphicsCache.cpp` 在 `separate_pipeline_cache` 开关启用时使用独立管线缓存，并在 Vulkan 帧 flush 后检查是否出现新数据。该版本源码把一次保存的数据上限写为 2 MiB。

这些都是 `android-17.0.0_r1` 的平台实现细节，不是 SDK 契约。系统可以在后续版本修改文件格式、上限、写入节奏和失效策略。应用无需也无法自行加载这份 HWUI 缓存。

### 2. 应用控制的是变体来源和首次出现时机

标准 UI 应用可从以下位置减少首次使用成本：

- `RuntimeShader` 源码保持稳定，把可变化参数放在 uniform；
- 重用已经创建的 `RuntimeShader`、`RenderEffect`、`Shader` 和 `Paint`，避免在每帧重新构造对象；
- 避免在一次关键点击里同时出现大量此前未渲染的效果、字体、图片格式和图层组合；
- 对必须首用的复杂效果，用目标设备上的真实用户操作衡量是否需要提前初始化；
- 让图片解码尺寸、色彩格式和实际显示需求一致，减少不必要的上传与内存带宽；
- 对可接受的视觉效果准备简单实现，并根据实测帧结果选择。

“在冷启动首帧前绘制不可见的 1×1 View”不是可靠的预编译接口。不可见节点可能不进入绘制，1×1 目标也可能产生不同的 clip、render target 或图层状态；即使触发了某些编译，它也会把额外工作放进启动关键路径。

若业务需要预热，应使用与线上相同的页面、尺寸、颜色空间和效果组合，放在用户可接受的非关键阶段，并用 Macrobenchmark 证明首个关键操作改善且启动没有退化。标准 HWUI 没有公开 API 保证“预热完成了全部目标管线”。

### 3. Baseline Profile 不保存 GPU 管线

Baseline Profile 能改善应用 Java/Kotlin 与部分 native 代码的编译和执行状态。它不包含厂商 GPU 指令，也不会替代 Skia 或 Vulkan pipeline cache。一次优化同时加入 Baseline Profile 和页面预热后，需要分别验证 CPU 方法执行与图形首次使用成本，避免把收益归错原因。

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

## 四、HWUI 的两个 Vulkan queue 解决什么问题

`VulkanManager.cpp` 从同一个 graphics queue family 请求两个 queue：index 0 保存到 `mGraphicsQueue`，index 1 保存到 `mAHBUploadQueue`。`HardwareBitmapUploader` 创建上传用的 Ganesh 上下文时选择后者。

下面的源码摘录用于核对 queue 数量、优先级数组和索引。

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

1. 两个 queue 来自同一个 family；
2. `queuePriorities` 的两个元素都为 `0.0f`；
3. 可选的 global priority 挂在同一份 `VkDeviceQueueCreateInfo` 上，没有为上传 queue 设置单独的低优先级；
4. Vulkan 允许多个 queue 独立提交，但设备可以在同一硬件引擎上串行执行，源码无法保证物理并行。

`VK_EXT_global_priority` 也不是普通应用可依赖的“渲染高、上传低”策略。HWUI 只有在 context priority 非零、扩展可用且请求值满足设备条件时才附加 global priority；不支持时会放弃该请求或由驱动返回错误。

`HardwareBitmapUploader` 的 Vulkan 路径使用专用上传线程和 upload queue，但代码内部还会调用 `queue().runSync(...)`，提交时使用 `GrSyncCpu::kYes`。这表示上传工作与 RenderThread 使用不同上下文和 queue，不表示每个调用都对其调用者完全异步。

两条 queue 的价值在于隔离提交状态和减少相互等待的机会。最终能否并行、内存带宽是否竞争、上传是否延迟渲染，仍要在目标设备上看 GPU 阶段和 fence。

## 五、Graphite `PipelineManager` 的准确边界

### 1. `PipelineCreationTask` 先处理去重

`external/skia` 的 Graphite `PipelineManager::createHandle()` 按以下次序处理请求：

1. 查询同一 key 是否已有 active task；
2. 查询 global cache 是否已有 pipeline；
3. 在 spinlock 保护下再次确认，并创建或复用 task。

这个设计避免并发请求为同一个键重复创建管线。`SkSpinlock` 只保护 active task 表的短临界区，不是管线编译队列，也没有“先到请求拥有更高优先级”的语义。

### 2. Android 17 标签中的 Vulkan 基础实现是同步调用

`PipelineCreationTask.h` 把 task 描述为“可能交给线程的工作单元”。“可能”不能省略。`PipelineManager::startPipelineCreationTask()` 在当前实现中直接调用 `SharedContext::findOrCreateGraphicsPipeline()`，完成后设置 `fCompleted`。`resolveHandle()` 还明确说明非线程版本在到达这里前已经执行过任务。

`DrawPass::prepareResources()` 的当前顺序是：

- 创建 handle；
- 立即调用 `startPipelineCreationTask()`；
- 随后调用 `resolveHandle()`。

因此，不能把它概括为“snap 时派发到后台，insertRecording 时统一等待”。是否异步取决于具体后端、executor 和调用实现；`android-17.0.0_r1` 的这条 Vulkan 基础路径没有展示一个通用的后台编译调度器。

### 3. Graphite Trace 名称不能套到 HWUI

该标签中的 Graphite Vulkan 源码使用 `skia.shaders` 类别，并包含以下名称：

- `CreateGraphicsPipeline`
- `CreateGraphicsPipeline-CacheLookup`
- `CreateGraphicsPipeline-CompileAfterCacheMiss`
- `CreateGraphicsPipeline-CacheLookupOrCompile`
- `GraphitePipelineUse`

这些名称只在相应 Graphite 构建和 Trace 配置中有意义。AOSP 没有一个可对所有应用保证的 `gpu.graphite` track。标准 Android 17 HWUI 使用 Ganesh，看到 RenderThread `flush` 变长也不足以认定 Graphite task 正在等待。

Graphite 的 Vulkan 实现仍提供了值得参考的控制方式：设备支持 pipeline creation cache control 时，它先带 `FAIL_ON_PIPELINE_COMPILE_REQUIRED` 查询缓存；收到 `VK_PIPELINE_COMPILE_REQUIRED` 后，去掉该标志并执行允许编译的调用。原生 Vulkan 引擎可以采用相同思路，但必须自己安排编译线程和降级管线。

## 六、原生 Vulkan 的任务调度

### 1. 构建稳定的管线键

应用应先为每个可执行管线定义稳定键。键至少覆盖：

- 着色器内容哈希、入口和 specialization constant；
- 管线布局版本；
- attachment 格式、sample count 与渲染模式；
- 所有静态 raster、depth/stencil 和 blend 状态；
- 会影响兼容性的引擎版本。

管线键用于任务去重、缓存统计和回归定位。不要把整个 `VkGraphicsPipelineCreateInfo` 直接浅拷贝进工作队列，它含有大量指针；调用者离开作用域后，编译线程可能读到失效内存。队列应保存 `PipelineKey` 或持有完整不可变创建配方的所有权，由编译线程在调用时重建 create info。

### 2. 队列只接收缺失且仍需要的任务

一个实用状态机可以包含：

| 状态 | 含义 | 前台渲染行为 |
| --- | --- | --- |
| `Unknown` | 尚未查询内存表或驱动 cache | 发起仅缓存查询 |
| `Ready` | 已有可绑定的 `VkPipeline` | 直接使用 |
| `Queued` | 管线键已进入编译队列 | 使用兼容的降级管线或延后该物体 |
| `Compiling` | 编译线程正在创建 | 不重复提交 |
| `Failed` | 创建失败，保留 `VkResult` 和上下文 | 选择明确降级，限制重试 |

任务优先级应来自用户可见性和截止时间。例如，当前加载界面即将结束的场景高于远处尚未加载的关卡。优先级不能从“着色器代码越短越高”推导；源码长度与驱动创建成本没有稳定对应关系。

编译线程数量也没有通用答案。过多线程会争用 CPU、驱动内部锁和 pipeline cache。应在代表设备上比较 1、2、4 个编译线程的总完成时间、关键线程调度和峰值内存，再决定上限。

### 3. 用仅缓存查询保护渲染线程

Vulkan 1.3 核心功能包含 pipeline creation cache control；较旧实现可通过 `VK_EXT_pipeline_creation_cache_control` 提供同类能力。应用必须查询并启用对应 feature，不能仅凭 API 版本字符串使用标志。

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

调用期间，`baseInfo` 引用的所有数组和 `pNext` 结构必须保持有效。返回 `VK_SUCCESS` 时可发布管线；返回 `VK_PIPELINE_COMPILE_REQUIRED` 时，应把对应键交给编译线程，并让它用不带该标志的 create info 执行允许编译的调用。其他错误要按 `VkResult` 处理，不能全部当成 cache miss。

这个标志只避免当前调用执行昂贵编译，不会自动创建后台任务，也不提供降级管线。降级管线必须与 render pass、pipeline layout、descriptor 绑定和资源格式兼容；兼容条件无法满足时，延后绘制比绑定错误管线安全。

### 4. 控制并发与发布

编译线程完成 `vkCreateGraphicsPipelines()` 后，应通过互斥锁、原子状态或线程安全队列把结果发布给渲染线程。发布前不能让其他线程看到半初始化的业务对象。`VkPipeline` 的销毁要跟随使用它的 GPU 工作完成，不能因为业务键被替换就立即销毁仍被 command buffer 引用的管线。

默认创建的 `VkPipelineCache` 可由多个线程同时传给 pipeline creation 命令，规范要求实现对这种使用做内部同步。如果创建 cache 时设置了 `VK_PIPELINE_CACHE_CREATE_EXTERNALLY_SYNCHRONIZED_BIT`，应用接管了修改命令的同步责任，所有会修改该 cache 的调用都要按规范串行化。

驱动的内部同步仍可能限制扩展性。两种常见方案都需要实测：

- 多个编译线程共用一个默认 cache，代码简单，驱动负责同步；
- 每个编译线程使用独立 cache，在受控时点用 `vkMergePipelineCaches()` 合并。

后一种方案会增加内存、合并和持久化复杂度。没有测量结果时，共用默认 cache 更容易保持正确。

## 七、正确保存 `VkPipelineCache`

### 1. 缓存数据是不透明的驱动数据

`vkGetPipelineCacheData()` 返回的内容可以在后续运行中传给 `VkPipelineCacheCreateInfo::pInitialData`。应用不应解释 header 以外的字节，也不能把一个设备的数据分发给所有设备。

版本一 header 包含：

- `headerSize`；
- `headerVersion`；
- `vendorID`；
- `deviceID`；
- `pipelineCacheUUID`。

驱动会忽略不兼容的 initial data。应用仍应在加载前校验 header，以便删除损坏文件、记录失效原因，并避免把无关数据反复交给驱动。缓存文件名还应包含应用的图形资源版本；着色器或管线布局发生不兼容变更时，创建新的命名空间。

下面的 C++ 函数用于按 Vulkan 规定的小端字节布局校验 version-one header。

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

这段代码避免依赖 C++ 结构体 padding。调用文件需要包含 `<cstddef>`、`<cstdint>`、`<cstring>` 和 `<span>`。检查通过后仍要处理 `vkCreatePipelineCache()` 的返回值；header 兼容只说明数据可尝试使用，不保证每次创建或每次后续查询都命中。

### 2. 写文件要服从 Vulkan 对象生命周期

可靠的保存流程如下：

1. 停止接收新的管线创建任务，并等待当前编译线程到达约定的安全点；
2. 第一次调用 `vkGetPipelineCacheData()` 取得所需大小；
3. 分配缓冲并再次调用，接受 `VK_SUCCESS`，按设计处理 `VK_INCOMPLETE`；
4. 写到同目录临时文件，`fsync` 需求由产品的数据耐久策略决定；
5. 原子替换正式文件；
6. 保存成功后再更新业务版本标记。

这里暂停编译线程主要为了得到与当前引擎版本一致、便于复现的快照，并避免与 cache 和 device 销毁交错。若使用 externally synchronized cache，还必须满足对应主机端同步要求。

不要在每一帧写缓存。适合的时机包括 loading 阶段结束、累计产生新管线后的受控后台时点，以及正常退出流程中仍有足够生命周期时。Android 进程可能被直接终止，缓存正确性不能依赖退出回调一定执行。

### 3. 缓存失效要使用图形身份

推荐的缓存身份至少包含：

- `vendorID`、`deviceID` 和 `pipelineCacheUUID`；
- 应用或引擎的管线结构版本；
- 着色器包内容版本；
- 影响 create info 的渲染配置版本。

`Build.SOC_MODEL` 适合做诊断标签，不适合单独决定 cache 兼容性。系统升级后若 `pipelineCacheUUID` 改变，旧数据应被丢弃；如果 UUID 没变，驱动仍负责判断 initial data 是否可用。

## 八、可选 Vulkan 能力怎样使用

### 1. Pipeline creation feedback

Vulkan 1.3 核心 `VkPipelineCreationFeedback`（或扩展别名）可以返回创建耗时和标志。只有 `VK_PIPELINE_CREATION_FEEDBACK_VALID_BIT` 置位时，其他字段才有定义。`duration` 的单位是纳秒。

`VK_PIPELINE_CREATION_FEEDBACK_APPLICATION_PIPELINE_CACHE_HIT_BIT` 可以帮助判断命中是否来自应用提供的 pipeline cache。这个反馈适合统计真实管线键的命中和创建分布，比固定“单管线应小于多少毫秒”更可靠。

反馈是驱动对一次创建调用的报告，不是 GPU 执行时间。使用时应同时记录管线键、线程、场景、创建结果、是否命中 cache 和调用耗时，但线上日志不要包含着色器源码或无限增长的动态名称。

### 2. Graphics pipeline library

`VK_EXT_graphics_pipeline_library` 可以把图形管线分为 vertex input interface、pre-rasterization shaders、fragment shader 和 fragment output interface 四部分，重用公共部分后再链接为可执行管线。它依赖 `VK_KHR_pipeline_library`，并暴露独立的 feature 和 properties。

应用需要查询并启用 `graphicsPipelineLibrary`。`graphicsPipelineLibraryFastLinking` 会影响即时链接策略；未支持该 property 时，链接仍可能比完整编译便宜，但不应假定其成本接近命令录制。link-time optimization 还可能用更长的创建时间换取更好的运行性能。

该扩展适合材质组合多、公共状态复用明显的引擎。它不会消除变体数量，也不保证所有 Android 17 设备支持。接入前要比较：

- loading 总时间；
- 首次使用的长尾；
- pipeline cache 体积；
- 链接后 GPU 执行时间；
- 驱动稳定性和内存增长。

### 3. Dynamic state

设备支持相应 dynamic state 时，把频繁变化的固定功能状态改为动态命令，可以减少管线组合数。代价可能包括驱动路径差异、录制复杂度和运行时性能变化。应从实际 key 统计中找出高基数维度，再选择设备能力允许的状态，不能一次性把所有可动态状态全部启用。

## 九、把创建任务放在合适的用户阶段

### 普通 UI

普通 UI 没有公开的管线编译队列。优化重点是减少不必要的效果变体，让目标效果在可接受阶段首次出现，并以真实页面的帧结果验证。若某效果只在低频入口出现，提前初始化它可能只会增加大多数用户的启动与内存成本。

### 游戏和原生渲染器

游戏可以在加载界面、关卡流式加载或资源包安装后创建下一阶段必需的管线。进度条应由已完成的必要任务驱动，而不是仅按已提交任务数量推进。加载结束前要确认当前场景的必需集合进入 `Ready`，可选集合允许延迟或使用兼容的降级管线。

任务优先级建议考虑：

- 距离可见的帧数或场景阶段；
- 是否存在视觉可接受的降级管线；
- 资源依赖是否已经就绪；
- 该管线键是否正在创建；
- 最近的创建耗时分布；
- 当前 CPU 热状态和编译队列长度。

设备策略应基于运行时 feature、properties 和实测分布。按“高端、中端、低端”写死 SoC 名单很快会失效，也无法反映同一 GPU 在不同驱动和散热状态下的差异。

### 热更新

着色器包或 native 引擎更新后，应提升业务管线结构或 shader bundle 版本。只删除发生变化的逻辑键可以减少重建量，但驱动 cache 本身是整体不透明数据；应用不能从二进制文件里安全移除单个条目。

灰度期间应比较相同设备身份、相同场景和相同刷新率下的：

- 仅缓存查询命中率；
- pipeline creation feedback 长尾；
- loading 时长；
- 首次交互慢帧；
- GPU 执行时间；
- cache 文件体积和创建失败率。

## 十、诊断时按时间域收集证据

### 1. 原生 Vulkan：在调用点放固定 Trace marker

原生引擎能直接测量自己的管线创建。Trace 标记名称应固定，动态管线键进入结构化遥测字段，避免为每个键生成新的 Trace 名称。

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

调用文件需要包含 `<android/trace.h>`、`<chrono>` 和 `<cstdint>`。显式转换保证 `wallTimeNanos` 使用纳秒单位。`ATrace` 区间和调用耗时都描述调用线程上的主机端时间；GPU 是否忙、该管线后续执行多久，需要 GPU Trace、timestamp query 或 AGI 的独立证据。

### 2. 标准 HWUI：只能做关联，不能越级归因

在标准 View/Compose 页面中，应用看不到 HWUI 内部每个 `vkCreateGraphicsPipelines()` 调用。排查顺序可以是：

1. 用 FrameTimeline 找到同一用户操作中的慢帧，并区分 App 与 SurfaceFlinger 侧；
2. 检查主线程是否及时完成 UI、测量、布局和绘制记录；
3. 检查 RenderThread 是否在同一帧出现异常长区间或提交变晚；
4. 比较效果首次出现与重复出现；
5. 用可控开关移除某个 `RuntimeShader`、`RenderEffect` 或图层组合后复测；
6. 需要源码级结论时，使用带对应平台 Trace 的系统构建或 vendor 工具。

“首次出现时 RenderThread 变长、第二次恢复”是缓存或初始化问题的线索，还可能来自字形栅格化、图片上传、图层分配、驱动初始化等工作。没有调用级证据时，结论应写成相关性。

### 3. AGI 的适用范围

AGI Frame Profiler 可以展示 Vulkan API 调用、pipeline data、render state、shader 资源和 GPU 性能数据。它适合直接 Vulkan 应用；对 OpenGL ES，AGI 的 frame profiling 使用定制 ANGLE 把调用翻译为 Vulkan 后采集。这个采集环境可能不同于用户设备原本的 GLES 后端，结论要标明条件。

AGI 能看到一帧内 API 和 GPU 工作，不代表一次长时间的 loading 阶段可以只靠单帧采集解释。大量管线预编译应同时使用系统 Trace、引擎遥测和阶段统计。

### 4. Buffer 生命周期只能缩小范围

渲染链路中常见的时间段可以这样读取：

| 时间段 | 可以说明 | 不能单独说明 |
| --- | --- | --- |
| `DEQUEUE → QUEUE` | producer 从取得缓冲到提交缓冲的总区间变长 | 具体由管线创建、CPU 绘制、GPU 执行还是等待造成 |
| `QUEUE → LATCH` | 缓冲提交后没有在预期时点被 SurfaceFlinger 采用 | 着色器编译发生在 GPU，或 SurfaceFlinger 一定在等待该编译 |
| `LATCH → PRESENT` | 合成、显示调度和呈现相关区间变长 | 应用 RenderThread 正在编译着色器 |

`queueBuffer()` 返回只表示 producer 完成了提交动作。`vkQueueSubmit()` 和 `vkQueuePresentKHR()` 返回也不等于 GPU 工作完成或像素已经显示。应继续看 acquire/release/present fence、FrameTimeline 和显示事件。

### 5. kernel 证据的责任范围

`android17-6.18-2026-06_r6` 可用于解释：

- 编译线程或 RenderThread 是否获得 CPU；
- 唤醒后是否长时间等待调度；
- dma-fence / sync_file 何时发信号；
- CPU 频率、idle、热限制和内存压力是否影响主机端调用；
- vendor GPU 驱动线程是否出现可观察的等待。

通用 kernel 代码不知道业务 `PipelineKey`，也无法仅凭一个 fence 名称判断驱动正在编译哪段着色器。GPU 指令编译和执行的详细原因通常需要厂商驱动 Trace、AGI 或应用自己的调用标记。

## 十一、常见错误结论

| 错误结论 | 修正后的判断 |
| --- | --- |
| Android 17 HWUI 默认使用 Graphite | `android-17.0.0_r1` 的 HWUI 创建 Ganesh `GrDirectContext` |
| `PipelineCreationTask` 一定在后台线程执行 | 当前 Graphite 基础实现可在调用线程直接创建并立即 resolve |
| 两个 Vulkan queue 能并行编译管线 | 管线创建是主机端命令，queue 承载 GPU 提交 |
| HWUI 给渲染 queue 高优先级、上传 queue 低优先级 | 两个 queue 使用同一 create info，优先级数组均为 `0.0f` |
| 有 SPIR-V 就没有运行时编译 | 厂商驱动仍可能在管线创建中生成设备代码 |
| `GPU_DURATION` 变高可确认着色器编译 | 该指标描述 GPU 完成时间，不提供主机端编译归因 |
| `DEQUEUE → QUEUE` 长就能确认编译卡顿 | 它只限定 producer 区间，仍需调用级和线程证据 |
| 改变普通 uniform 一定生成新管线 | 普通 uniform 值通常不进入管线键 |
| Android 17 设备都支持 graphics pipeline library | 该 device extension 和 feature 必须运行时查询 |
| Baseline Profile 会预编译 GPU 管线 | 它针对应用代码执行，不保存厂商 GPU 管线 |

## 十二、版本边界

| 项目 | 采用的边界 |
| --- | --- |
| Android 平台 | Android 17 / API 37 / `android-17.0.0_r1` |
| HWUI | 标准路径按 Skia Ganesh 核查；不把 Graphite 源码等同于 HWUI 默认实现 |
| Vulkan | 以设备实际报告并启用的 API、extension、feature 和 property 为准 |
| kernel | `android17-6.18-2026-06_r6`，用于调度、fence 和驱动线程证据 |
| 厂商驱动 | 设备相关；AOSP 公共源码无法保证编译并行度、缓存命中成本和 GPU queue 物理并行 |

Android 16 的历史数据可以用于对比，但相关源码名称、Trace 标记和 HWUI 缓存实现只对 Android 17 锚点作核查。后续平台若把 HWUI 切换到 Graphite，应重新核对 `RenderPipelineType`、context 创建点、pipeline task 执行方式和 Trace 类别，不能沿用这里的结论。

## 十三、工程检查清单

### 标准 View / Compose

- [ ] 已确认慢帧属于目标 App Window 和目标 Surface；
- [ ] 已区分 UI 主线程、RenderThread、GPU、SurfaceFlinger 和显示阶段；
- [ ] 没有把 Graphite 源码当成 Android 17 HWUI 默认路径；
- [ ] `RuntimeShader` 的变化参数优先使用 uniform；
- [ ] 没有用不可见 1×1 View 代替真实场景验证；
- [ ] `FrameMetrics.GPU_DURATION` 只用于 GPU 时间统计；
- [ ] 优化前后使用相同设备、刷新率和用户操作复测。

### 原生 Vulkan

- [ ] 管线键覆盖着色器、layout、attachment 和静态状态；
- [ ] 编译线程持有不可变创建配方，未浅拷贝悬空指针；
- [ ] 已查询并启用 pipeline creation cache control；
- [ ] 仅缓存查询未命中时会进入去重队列，不会在渲染线程直接编译；
- [ ] 降级管线与 layout、render pass 和资源绑定兼容；
- [ ] 编译线程数量来自目标设备实测；
- [ ] pipeline cache header 校验 vendor、device 和 UUID；
- [ ] 缓存通过临时文件和原子替换保存；
- [ ] externally synchronized cache 有明确同步策略；
- [ ] 管线销毁等待相关 GPU 使用完成；
- [ ] feedback、ATrace 和 GPU 数据分别记录主机端创建与 GPU 执行。

## 参考资料

- [AOSP `Properties.h`：HWUI RenderPipelineType（android-17.0.0_r1）](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/libs/hwui/Properties.h)
- [AOSP `VulkanManager.cpp`：HWUI Vulkan device、queue 与 Ganesh context](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/libs/hwui/renderthread/VulkanManager.cpp)
- [AOSP `HardwareBitmapUploader.cpp`：上传线程与 upload context](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/libs/hwui/HardwareBitmapUploader.cpp)
- [AOSP `PersistentGraphicsCache.cpp`：HWUI 持久化图形缓存](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/libs/hwui/pipeline/skia/PersistentGraphicsCache.cpp)
- [Skia Graphite `PipelineManager.cpp`（android-17.0.0_r1）](https://android.googlesource.com/platform/external/skia/+/refs/tags/android-17.0.0_r1/src/gpu/graphite/PipelineManager.cpp)
- [Skia Graphite `DrawPass.cpp`（android-17.0.0_r1）](https://android.googlesource.com/platform/external/skia/+/refs/tags/android-17.0.0_r1/src/gpu/graphite/DrawPass.cpp)
- [Skia Graphite `VulkanGraphicsPipeline.cpp`（android-17.0.0_r1）](https://android.googlesource.com/platform/external/skia/+/refs/tags/android-17.0.0_r1/src/gpu/graphite/vk/VulkanGraphicsPipeline.cpp)
- [Vulkan Pipeline Cache 规范](https://docs.vulkan.org/spec/latest/chapters/pipelines.html#pipelines-cache)
- [Vulkan pipeline creation cache control](https://docs.vulkan.org/refpages/latest/refpages/source/VK_EXT_pipeline_creation_cache_control.html)
- [Vulkan pipeline creation feedback](https://docs.vulkan.org/refpages/latest/refpages/source/VK_EXT_pipeline_creation_feedback.html)
- [Vulkan graphics pipeline library](https://docs.vulkan.org/refpages/latest/refpages/source/VK_EXT_graphics_pipeline_library.html)
- [Android Vulkan 原生引擎支持](https://developer.android.com/games/develop/vulkan/native-engine-support)
- [Android `FrameMetrics` API](https://developer.android.com/reference/android/view/FrameMetrics)
- [Android GPU Inspector Frame Profiler](https://developer.android.com/agi/frame-trace/frame-profiler)
