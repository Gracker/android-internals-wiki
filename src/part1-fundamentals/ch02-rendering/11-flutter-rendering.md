---
title: "2.11 Flutter 渲染管线与性能"
chapter: "2.11"
status: reviewed
drafted_date: "2026-04-01"
reviewed_date: "2026-04-02"
reviewed_by: "openclaw-task6"
applicable_versions: "Android 10 (API 29) - Android 17 (API 35)" <!-- [存疑: Android 17 对应的 API Level 不应是 35，项目其他章节中 Android 16 = API 36，请确认实际范围] -->
last_verified: "2026-04-01"
last_verified_against: "Flutter 3.27 / Impeller default on Android API 29+"
confidence: medium
sources:
  - type: official
    path: "https://docs.flutter.dev/perf/rendering-performance"
  - type: official
    path: "https://docs.flutter.dev/perf/impeller"
  - type: blog
    path: "https://github.com/flutter/flutter/wiki/Impeller"
tags: [flutter, rendering, impeller, skia, cross-platform, shader-compilation, jank]
related_chapters: ["2.1", "2.3", "2.4", "2.5", "7.1", "7.7"]
---

<!-- [需补充: 本章缺少 outline 块（<!-- outline-start -->...<!-- outline-end -->），与项目大部分章节的格式不统一，建议 task2 加工时补充] -->

# 2.11 Flutter 渲染管线与性能

## 为什么要了解 Flutter 的渲染

如果你在 Perfetto 中看过一个 Flutter 应用的 Trace，你会发现一件奇怪的事：看不到熟悉的 Choreographer.doFrame，看不到 RenderThread，甚至连 ViewRootImpl.Traversal 都没有。取而代之的是一些你不太认识的线程——一个叫 `1.platform`，一个叫 `1.raster`，还有一个叫 `1.ui`。

这不是因为 Flutter 出了问题，而是因为 Flutter 从根本上走了另一条路：它不使用 Android 原生的 View 体系来渲染 UI。Flutter 自己管理整个渲染管线，从 Widget 树的构建到最终的像素输出，全部在 Flutter Engine 内部完成。这意味着我们在本书前面章节学到的 Choreographer、MainThread/RenderThread 协作、Hardware Layer 这些机制，对 Flutter 应用来说大部分不适用。

这种"另起炉灶"的设计带来了一个直接的后果：当 Flutter 应用出现性能问题时，我们不能直接用分析原生 Android 应用的那一套方法。如果 Flutter 应用在列表滚动时掉帧，你盯着 MainThread 的 CPU slice 看，很可能什么异常都找不到——因为真正干活的是 `1.raster` 线程。

所以这一章要解决的问题是：Flutter 在 Android 上到底是怎么渲染的？它的渲染管线和原生 Android 有什么本质区别？当 Flutter 应用出现性能问题时，我们应该看哪里、怎么分析？

## Flutter 的渲染架构

Flutter 的渲染架构可以分为三层：Framework 层（Dart）、Engine 层（C++）和平台嵌入层（Platform Embedder）。

Framework 层是我们作为 Flutter 开发者直接接触的部分。我们写的 Widget、State、Element，以及 Rendering 目录下的 RenderObject，都在这一层。当 UI 需要更新时，Framework 层会经历 Build → Layout → Paint 三个阶段：Build 阶段根据状态构建 Widget 树；Layout 阶段计算每个 RenderObject 的大小和位置；Paint 阶段将绘制指令记录到一个 DisplayList 中。

Engine 层是 Flutter 的核心引擎，用 C++ 编写。它负责两件事：一是把 Framework 层产生的 DisplayList 光栅化为实际的像素数据；二是管理与底层图形 API（Vulkan 或 OpenGL ES）的交互。Engine 层还包含了 Dart 虚拟机、文本排版引擎（最近从 libtxt 迁移到了 SkParagraph）、以及网络、文件等基础能力。

平台嵌入层是一个比较薄的层，负责把 Flutter Engine 嵌入到具体的平台中。在 Android 上，它创建和管理 FlutterView（通常是一个 SurfaceView 或 TextureView），处理 Android 的生命周期事件，并将触摸等输入事件转发给 Flutter Engine。

这种三层架构的关键在于：从 Framework 层到 Engine 层，Flutter 完全掌控了渲染过程。它不需要经过 Android 的 measure/layout/draw 流程，不需要经过 Choreographer 调度，也不需要通过 SurfaceFlinger 的 BufferQueue 机制来和系统合成器交互——至少在 Flutter 自己的渲染部分是这样。Flutter 直接在自己的 Surface 上绘制，然后把绘制好的帧通过 Android 的 Surface 机制提交给 SurfaceFlinger。

`[图：Flutter 三层架构与 Android 系统服务的关系。展示 Framework(Dart) → Engine(C++) → Platform Embedder(Android) 的层次关系，以及与 SurfaceFlinger、InputManager 的交互点]`

### 线程模型

Flutter 的线程模型和原生 Android 差异很大，理解它对性能分析至关重要。Flutter Engine 主要使用四个线程：

**Platform 线程**（对应 Android 主线程 / `1.platform`）：这是 Flutter 应用的"主线程"，但实际上它的工作和原生 Android 的主线程有所不同。Platform 线程负责处理 Android 的生命周期事件、输入事件分发、以及 Platform Channel 的消息传递。但关键的是——UI 的渲染计算不在这个线程上完成。

**UI 线程**（`1.ui`）：也叫 Dart 线程，这是 Dart 虚拟机运行 Isolate 的地方。我们写的 Dart 代码——Widget 的 build、状态管理、业务逻辑——都在这个线程上执行。当 UI 需要更新时，UI 线程会执行 Build → Layout → Paint 流程，生成 DisplayList，然后把它发送给 Raster 线程。

**Raster 线程**（`1.raster`，旧称 GPU 线程）：这个线程负责实际的像素光栅化。它从 UI 线程接收 DisplayList，然后调用 Skia 或 Impeller 的 API 将绘制指令转换为 GPU 命令，最终输出到 Surface 上。如果你在 Perfetto 中看到 Raster 线程 CPU 占用很高，说明 GPU 光栅化工作量很大。

**IO 线程**（`1.io`）：主要负责从磁盘或网络加载图片资源，并将解码后的图片数据上传到 GPU 内存。这个线程的任务比较单一，通常不会成为性能瓶颈。

在 Perfetto 中，我们可以清晰地看到这四个线程。一个正常运行的 Flutter 应用，每一帧的工作流程大致是这样的：UI 线程执行 Build/Layout/Paint 生成 DisplayList → Raster 线程接收 DisplayList 并执行光栅化 → 通过 Surface 提交给 SurfaceFlinger。

`[图：Flutter 线程模型在 Perfetto 中的表现。展示 1.platform、1.ui、1.raster、1.io 四个线程的 Track，标注一帧在 UI 线程和 Raster 线程上的时序关系]`

## 与 Android 原生渲染的差异

理解了 Flutter 的渲染架构后，我们把它和原生 Android 的渲染管线做一个系统性的对比。这个对比不是用来评判哪个更好的，而是帮助我们在实际工作中快速定位问题。

### 渲染管线的根本区别

原生 Android 的渲染管线我们已经在前面章节详细讲过了：VSync → Choreographer → MainThread(doFrame: Input/Animation/Traversal) → RenderThread → SurfaceFlinger。这条管线有几个关键特征：它是 VSync 驱动的，渲染工作由系统的 VSync-app 信号触发；MainThread 和 RenderThread 是流水线式的协作关系；最终的帧提交要通过 BufferQueue 和 SurfaceFlinger。

Flutter 的渲染管线则完全由自己的 Engine 驱动。UI 线程不需要等待 VSync 信号来开始工作——当 Dart 代码调用 setState() 时，Framework 会标记需要重建的 Element，然后在下一帧的回调中执行 Build/Layout/Paint。这个"下一帧的回调"虽然也通过 vsync waiter 来同步（Flutter Engine 内部会监听 VSync 信号），但整个调度逻辑是 Engine 自己管理的，不经过 Choreographer。

这意味着在 Perfetto 中，我们看不到 Choreographer 的 doFrame 标记。取而代之的是 Flutter Engine 自己的 trace event，比如 `FrameRequest`、`BeginFrame`、`DrawFrame` 等。

### Surface 的使用方式

Flutter 在 Android 上通过一个 Surface（通常是 SurfaceView 或 TextureView 提供的 Surface）来输出渲染结果。Flutter Engine 在 Raster 线程上完成光栅化后，直接将帧 buffer queue 到这个 Surface 中。SurfaceFlinger 在 VSYNC-SF 到来时，像合成其他任何 Surface 一样合成 Flutter 的 Surface。

这里有一个值得注意的细节：Flutter 的 Surface 不经过 BufferQueue 的 Android 原生渲染管线。原生 Android 中，App 通过 queueBuffer 将 GraphicBuffer 提交给 BufferQueue，然后 SurfaceFlinger 通过 acquireBuffer 拿到 buffer 进行合成。Flutter 也走这个路径，但 Flutter 的 queueBuffer 是 Engine 层直接调用的，不经过 Framework 层的 RenderThread。

`[已验证: Flutter Engine 使用 Skia/Impeller 直接在 Surface 上绘制并通过 ANativeWindow_queueBuffer 提交帧, flutter.dev]`

### PlatformView：Flutter 与原生 View 的桥梁

Flutter 应用有时候需要嵌入原生的 Android View——比如 WebView、MapView、或者某些只有 Android 原生实现的控件。这就是 PlatformView 的工作。

PlatformView 有两种合成模式：**Virtual Display** 模式和 **Hybrid Composition** 模式。

Virtual Display 模式是早期方案，它将原生 View 的内容渲染到一个 VirtualDisplay 的 Surface 上，然后 Flutter 通过 Texture Widget 来显示这个 Surface 的内容。这种方式有一个严重的性能问题：数据需要经过 GPU → CPU → GPU 的往返传输（在 Android 10 之前），导致每帧有显著的额外开销。

Hybrid Composition 模式是当前的推荐方案。它不再通过 Texture 中转，而是直接将原生 View 添加到 Android 的 View 树中，让 Flutter 的 Surface 和原生 View 在 SurfaceFlinger 层面进行合成。这种方式在 Android 10+ 上性能更好，因为 Android 10 引入了 GPU 内存共享优化，避免了 GPU → CPU → GPU 的拷贝。

但 Hybrid Composition 也有代价。当 Flutter 内容和 PlatformView 内容需要同时显示时（比如 Flutter 的 UI 叠加在 WebView 上方），Flutter 必须在 Platform 线程（也就是 Android 主线程）上完成自己的 UI 合成。这意味着此时 Flutter 的渲染会退回到和原生应用一样的主线程依赖，之前提到的线程模型优势就不复存在了。在 Perfetto 中，你会看到此时 `1.platform` 线程的 CPU 占用明显增加，而 `1.raster` 线程可能处于等待状态。

`[待验证：Hybrid Composition 在 Android 14+ 上是否有进一步的优化]`

## 性能分析方法

分析 Flutter 应用的性能，需要结合 Flutter 自带的工具和 Android 系统级的工具。不能只用一套，因为 Flutter 层面的性能数据和系统层面的性能数据讲述的是同一个故事的不同侧面。

### Flutter DevTools

Flutter DevTools 是 Flutter 官方的性能分析套件。它提供了几个关键的分析面板：

**Performance 面板**（集成 Perfetto 渲染）：这是最常用的面板。它记录每一帧的 UI 线程和 Raster 线程的耗时，并用火焰图展示。从 Flutter 3.19 开始，Performance 面板已经集成了 Perfetto 的 trace viewer 作为其时间线后端，这意味着我们在 DevTools 中看到的时间线视图本质上就是 Perfetto。在 Performance 面板中，我们可以看到：

- 每一帧在 UI 线程上的 Build、Layout、Paint 各自花了多少时间
- Raster 线程的光栅化耗时
- 是否有帧超出了帧预算（60Hz 下 16ms，120Hz 下 8ms）
- 具体是哪个 Widget 或哪个 Dart 函数消耗了最多的时间

**CPU Profiler 面板**：提供 Dart 代码的 CPU 采样分析，可以看到 Dart 函数级别的 CPU 占用。

**Memory 面板**：监控 Dart 堆的内存使用，帮助发现内存泄漏。

使用 DevTools 分析时有一个重要前提：必须在 Profile 模式下运行。Debug 模式引入了大量的调试断言和 JIT 编译开销，性能数据完全不可信。在命令行中用 `flutter run --profile` 启动即可。

### Perfetto 系统级分析

当 Flutter 应用出现性能问题，但 DevTools 中找不到明显的 Dart 层面瓶颈时，问题可能出在系统层面。这时就需要用 Perfetto 抓取系统级 Trace。

抓取 Flutter 应用的 Perfetto Trace 和抓取原生应用的没有本质区别，使用 `adb shell perfetto` 命令即可。但在 Perfetto UI 中查看时，我们需要关注不同的 Track：

- `1.platform`（Platform 线程）：看是否有长时间的 Platform Channel 调用、PlatformView 合成开销
- `1.ui`（UI 线程）：看 Dart 代码的执行耗时，是否有频繁的 GC（Dart VM 的 GC 也会在这个线程上标记）
- `1.raster`（Raster 线程）：看光栅化耗时，是否存在 shader 编译导致的卡顿
- CPU 整体使用率：看 Flutter 的多个线程是否在争抢 CPU 时间
- SurfaceFlinger Track：看 Flutter 的 Surface 合成是否正常

在 Perfetto 中，Flutter Engine 会输出自己的 trace event。你可以通过搜索 `flutter` 关键字来快速定位相关的 slice。常见的有 `FlutterEngine::BeginFrame`、`GPURasterizer::DrawToSurface` 等。

### 自定义 Trace

Flutter 支持在 Dart 代码中插入自定义的 trace event，这些 event 会同时出现在 DevTools 和 Perfetto 中：

```dart
import 'dart:developer' as developer;

// 在需要追踪的代码块前后添加
developer.Timeline.startSync('my_custom_operation');
// ... 你的代码
developer.Timeline.finishSync();
```

这在定位某个特定操作的耗时时非常有用。比如你怀疑某个列表的 item builder 太慢，可以在 builder 中添加 trace event，然后在 DevTools 或 Perfetto 中直接看到它的耗时。

## 常见性能问题

了解了工具之后，我们来看 Flutter 应用在 Android 上最常见的几类性能问题。

### Shader 编译卡顿（Skia 时代）

这是 Flutter 在使用 Skia 渲染引擎时最臭名昭著的问题。Skia 在运行时编译 shader 程序——这些 shader 是 GPU 用来执行特定绘制操作的小程序。当 Flutter 应用首次遇到一种新的绘制操作（比如第一次使用某个复杂的 BlendMode、第一次绘制带有特定 path 操作的裁剪）时，Skia 需要在 Raster 线程上编译对应的 shader。

这个编译过程可能需要几十到几百毫秒，远超一帧的预算。表现出来的现象就是：应用启动后第一次滚动到某个页面时，或者第一次播放某个动画时，会出现明显的卡顿。但第二次经过同样的页面或同样的动画时，卡顿就消失了——因为 shader 已经编译好了，缓存在内存中。

在 Perfetto 中，这种现象表现为 Raster 线程上突然出现一个很长的 slice，内部包含 `ShaderCompile` 相关的标记。整个 Raster 线程在这段时间被阻塞，UI 线程虽然已经准备好了 DisplayList，但必须等 Raster 线程完成 shader 编译才能继续。

Flutter 团队曾提供 `flutter drive` 配合 SkSL warm-up 的方案来预热 shader，但这个方案使用复杂，效果也不稳定。根本的解决方案是切换到 Impeller 引擎（后面会详细讲）。

### Widget 过度重建

这是 Dart 层面最常见的性能问题。Flutter 的声明式 UI 框架在状态变化时会重建 Widget 树，但如果不注意控制重建范围，很容易导致整棵树都在重建。

最常见的表现是：在 Perfetto 或 DevTools 中，UI 线程的每一帧耗时都很长，火焰图显示大量的 `build` 方法在执行。但 Raster 线程很空闲——因为虽然 UI 线程生成了大量的 DisplayList，但很多都是没变化的。

这类问题的诊断和修复属于 Flutter 开发层面的优化，核心思路是：用 `const` 构造函数标记不需要重建的 Widget、将大的 build 方法拆分为小组件、使用合适的 State 管理方案限制重建范围。DevTools 的 "Rebuild Tracker" 功能可以帮助定位哪些 Widget 被频繁重建。

### PlatformView 相关的性能问题

当 Flutter 应用中嵌入了原生 View（如 WebView、MapView），性能特征会发生显著变化。

首先是线程合并（thread merging）问题。Hybrid Composition 模式下，当 Flutter 内容和 PlatformView 内容重叠时，Flutter 的渲染会退回到 Platform 线程执行。在 Perfetto 中你会看到 `1.platform` 线程上出现了渲染相关的工作，而 `1.raster` 线程处于空闲。每帧大约会增加 2ms 的额外开销。

其次，在可滚动的列表中嵌入多个 PlatformView 是一个已知的性能陷阱。因为每个 PlatformView 在滚动时都需要调用 setOffset() 来更新位置，这会触发昂贵的布局和绘制操作。如果列表快速滚动，这些操作可能超出帧预算。

### 列表滚动卡顿

Flutter 的 ListView/GridView/CustomScrollView 在数据量大时可能出现卡顿。原因通常不是渲染管线的性能问题，而是 item builder 太慢——每个 item 在构建时做了太多的工作（网络请求、图片解码、复杂的 Widget 树等）。

在 Perfetto 中的表现是 UI 线程在滚动时持续高负载，每一帧的 Build 阶段耗时过长。Flutter 提供了 `ListView.builder` 和 `cacheExtent` 等机制来缓解这个问题——builder 只构建可见区域附近的 item，cacheExtent 控制预构建的范围。

## Impeller 引擎

到目前为止我们讨论的性能问题中，shader 编译卡顿是最难绕过的一个——即使你把 Dart 代码优化到了极致，把 Widget 树管理得井井有条，用户第一次看到某个动画时依然会卡。这就是 Flutter 团队开发 Impeller 的原因。

### 为什么需要 Impeller

Impeller 是 Flutter 的新一代渲染引擎，从 Flutter 3.16 开始在 iOS 上默认启用，从 Flutter 3.27 开始在 Android API 29+ 上默认启用。它的核心设计目标只有一个：**消除 shader 编译导致的运行时卡顿**。

为了理解 Impeller 的设计，我们先回顾 Skia 的问题。Skia 是一个功能强大的 2D 图形库，被 Chrome、Android 等众多项目使用。但它的 shader 管理是运行时（JIT，Just-In-Time）的：只有在实际需要某个 shader 时才编译它。这在桌面平台上影响不大——桌面 GPU 的 shader 编译速度足够快。但在移动平台上，特别是中低端 Android 设备上，shader 编译可能非常慢。

Impeller 的核心改变是把 shader 编译从运行时移到了构建时（AOT，Ahead-Of-Time）。在 Flutter 应用的构建过程中，Impeller 会预编译所有可能用到的 shader，生成针对目标平台的编译产物（Vulkan 上是 SPIR-V，Metal 上是 MSL）。这样应用运行时，所有 shader 都已经准备好了，不需要任何运行时编译。

### Impeller 的架构

Impeller 的内部架构可以分为几个层次：

**Aiks 层**是 Impeller 对外暴露的高级绘图 API，相当于 Skia 的 SkCanvas。它提供了路径绘制、图片渲染、文本绘制等常见操作。Aiks 层的设计比 Skia 的 API 更简洁，去掉了 Skia 中大量 Flutter 不需要的功能，降低了维护成本。

**Entity/DisplayList 层**负责将 Aiks 层的绘图命令转换为一种中间表示——Entity。每个 Entity 描述了一个绘制操作（包括它的变换矩阵、裁剪区域、shader 参数等）。这种中间表示是 GPU 无关的，可以在任何后端上执行。

**HAL（Hardware Abstraction Layer）层**是对底层图形 API 的抽象。Impeller 通过 HAL 支持 Vulkan（Android）、Metal（iOS）和 OpenGL ES（Android 回退）。HAL 层管理纹理、缓冲区、Pipeline State Object（PSO）等 GPU 资源的生命周期。关键的是，PSO 的创建（其中包括 shader 的编译）在 HAL 层完成，而 Impeller 在构建时就把所有 PSO 创建好了。

**渲染执行**阶段，Impeller 采用了一种基于 Tile 的渲染策略。它将一帧的画面划分为多个 Tile（通常是 256×256 像素），然后对每个 Tile 独立执行光栅化。这种方式和移动 GPU 的硬件架构高度匹配——移动 GPU 本身就是 tile-based 的。只光栅化内容发生变化的 Tile，避免了对整帧画面重新光栅化。

`[图：Impeller 渲染管线的层次结构。展示 Aiks → Entity → HAL → GPU (Vulkan/Metal/OpenGL ES) 的数据流，标注 AOT shader 编译发生的位置]`

### Impeller 在 Android 上的表现

Impeller 在 Android 上优先使用 Vulkan 后端。对于不支持 Vulkan 的设备（主要是 Android API 28 及以下），Impeller 会回退到 OpenGL ES 后端。

从性能数据来看，Impeller 相比 Skia 有几个明显改善：

**光栅化时间降低**：Flutter 团队的基准测试显示，Impeller 在复杂渲染场景下可以将平均每帧的 GPU 光栅化时间降低约 30%。<!-- [需补充素材: 该数据缺乏具体来源/基准测试引用，请补充 Flutter 官方 benchmark 或第三方测试报告链接] -->这主要得益于 Impeller 对移动 GPU 的 tiling 架构做了针对性优化。

**帧率稳定性提升**：因为消除了 shader 编译卡顿，帧率的波动大幅减小。在 120Hz 设备上，Impeller 能够更稳定地在 8ms 帧预算内完成渲染。

**内存效率改善**：一些报告指出 Impeller 的内存使用比 Skia 低约 100MB（在复杂应用中）。<!-- [需补充素材: "一些报告"缺乏具体来源，请补充引用] -->这可能与 Impeller 更紧凑的资源管理和不需要运行时 shader 缓存有关。

`[已验证: Impeller 默认状态基于 Flutter 3.27 release notes, flutter.dev]`

不过，Impeller 在 Android 上的成熟度不如 iOS。在 Flutter 3.27 刚发布时，一些开发者报告了 Impeller 在 Android 上的兼容性问题，包括某些 ListView 场景下的性能退化、首次启动时的视觉质量问题等。Flutter 团队在持续修复这些问题，如果你在使用中遇到问题，可以通过 `--no-enable-impeller` 参数回退到 Skia 来验证是否是 Impeller 导致的。

## 优化策略

最后，我们把 Flutter 渲染性能优化的要点整理成一个系统性的框架。

### 必须做的事

**始终在 Profile/Release 模式下测试性能**。Debug 模式的性能数据毫无参考价值——JIT 编译、调试断言、DevTools 的通信开销会让性能看起来比实际差得多。

**优先使用 Impeller**。如果你的应用 targetSdk 是 29+（Android 10+），Impeller 已经默认启用。如果还没有升级 Flutter 版本，尽快升级到 3.27+ 以获得 Impeller 的 Android 支持。

**控制 Widget 重建范围**。使用 `const` 构造函数、拆分大 Widget、选择合适的状态管理方案。用 DevTools 的 Rebuild Tracker 来定位不必要的重建。

### 分析策略

遇到 Flutter 性能问题时，按照以下步骤排查：

1. **先在 DevTools Performance 面板看**：是 UI 线程慢还是 Raster 线程慢？这直接决定了解决方向。
2. **UI 线程慢**：打开 CPU Profiler 看 Dart 函数热点，检查是否有不必要的 Widget 重建、同步 IO 操作、或耗时的计算。用 Isolate 把重计算移出 UI 线程。
3. **Raster 线程慢**：检查是否还有 shader 编译卡顿（如果还在用 Skia）；检查是否有过度绘制；简化复杂的 Clip/Opacity/ShaderMask 操作。
4. **两边都不慢但帧率仍低**：可能是系统层面的问题。用 Perfetto 抓系统 Trace，看 CPU 调度、GC、内存压力等。

### PlatformView 的优化

- 尽量减少可滚动区域中 PlatformView 的数量
- 在 PlatformView 上方执行 Flutter 动画时，考虑使用截图纹理（snapshot texture）替代实时渲染
- 确保目标 Android 版本为 10+，以获得 Hybrid Composition 的 GPU 内存优化
- 如果使用自定义 Plugin 渲染到 Surface，优先使用 `SurfaceProducer` API（API 29+）

## 与其他章节的关联

Flutter 的渲染虽然自成体系，但它仍然运行在 Android 系统之上。理解本书前面讲的基础知识对分析 Flutter 性能同样重要：

- **§2.3 VSync 机制**：Flutter 的 VSync 监听最终依赖 Android 的 VSync-app 信号，理解 VSync 的调度逻辑有助于排查帧同步问题
- **§2.5 MainThread 与 RenderThread 协作**：当 PlatformView 导致线程合并时，Flutter 退回到类似原生 Android 的渲染模式，此时 MainThread 的性能特征就和原生一样了
- **§4.4 Low Memory Killer**：Flutter 应用占用内存通常比原生应用高（Dart VM 堆 + Skia/Impeller 资源），在低内存场景下更容易被 LMK 杀掉
- **§5.4 DVFS**：Flutter 的多线程模型（UI + Raster 同时运行）对 CPU 频率调度有影响，可能导致 DVFS 策略不如预期

## 参考资料

- Flutter 官方性能文档：https://docs.flutter.dev/perf/rendering-performance
- Impeller 设计文档：https://github.com/flutter/flutter/wiki/Impeller
- Flutter 性能最佳实践：https://docs.flutter.dev/perf/best-practices
- PlatformView 性能：https://docs.flutter.dev/platform-integration/android/platform-views
- Flutter Engine 源码（Impeller 目录）：https://github.com/flutter/engine/tree/main/impeller
- Flutter DevTools 文档：https://docs.flutter.dev/tools/devtools
