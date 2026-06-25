---
title: 2.11 Flutter 渲染管线与性能
chapter: 2.11
section: 2.11
status: finalized
pipeline_stage: ready-to-publish
applicable_versions: Android 10 (API 29) - Android 17 (API 37)
tags: [flutter, rendering, impeller, skia, cross-platform, shader-compilation, jank]
confidence: medium-low
last_verified: 2026-05-09
last_verified_against: Flutter 3.29 architecture/thread merge docs + Flutter Impeller docs/engine impeller README + Flutter Engine main (VsyncWaiter.java / PlatformViewsController.java / FlutterRenderer.java) + Android 16 Vulkan 1.4 VPA16 specs + ADPF PerformanceHintManager
sources: [{'type': 'official', 'path': 'https://docs.flutter.dev/perf/rendering-performance'}, {'type': 'official', 'path': 'https://docs.flutter.dev/perf/impeller'}, {'type': 'blog', 'path': 'https://github.com/flutter/flutter/wiki/Impeller'}, {'type': 'source', 'path': 'https://github.com/flutter/engine/blob/main/shell/platform/android/io/flutter/view/VsyncWaiter.java'}, {'type': 'source', 'path': 'https://github.com/flutter/engine/blob/main/shell/platform/android/io/flutter/plugin/platform/PlatformViewsController.java'}, {'type': 'source', 'path': 'https://github.com/flutter/engine/blob/main/shell/platform/android/io/flutter/embedding/engine/renderer/FlutterRenderer.java'}]
drafted_date: 2026-04-01
drafted_by: openclaw-task2a
finalized_date: 2026-05-22
finalized_by: openclaw-task9-auto-promote
auto_promoted_date: 2026-05-22
auto_promoted_by: openclaw-task9
polish_count: 1
polish_date: 2026-04-05
polish_by: task2b-polish
related_chapters: ['2.1', '2.3', '2.4', '2.5', '7.1', '7.7', '18.12']
task2b_result: fixed
last_task2b_at: "2026-05-22T19:18:14+08:00"
last_task9_audit: 2026-06-13
last_task9_audit_log: logs/deep-review/2026-06-13-20-audit.md
last_task6_audit: 2026-06-13
task9_state: reviewed
task9_result: pass-tech-review
task2b_state: fixed
task9_reviewed_date: 2026-05-22
task9_reviewed_by: openclaw-task9
last_task9_at: "2026-05-22T19:26:00+08:00"
last_task9_review_log: logs/deep-review/2026-05-22-19-deep-review.md
task9_review_notes: "2026-05-22 Task9 deep review: pass-tech-review。无 P0/P1/P2；16KB plugin 合规链路已拆清 AGP zip alignment、ELF p_align 与 native 4KB 假设。queue 无 pending，Task6 已通过，自动晋升 finalized。"
reviewed_date: 2026-05-22
reviewed_by: openclaw-task6
task6_state: reviewed
task6_result: pass-light-edit
last_task6_at: "2026-05-22T16:06:00+08:00"
last_task6_review_log: logs/review/2026-05-22-16-review.md
review_notes: "2026-05-09 task6 re-review (revisiting): pass-light-edit。L1 禁用词 4 处已修复。无 B 类大问题。评分：结构 5/5·措辞 4/5·一致性 5/5·验证 4/5·元数据 5/5。2026-05-22 Task6 re-review: L1/L2 pass-light-edit，修复 frontmatter 重复 key、结构性元叙述与口语化表达 7 处；Task9 P1/P2 queue 已存在，保持 task2b_pending。2026-05-22 Task6 re-review: pass-light-edit。L1/L2 小修 14 处（结构性元叙述、ASCII 破折号、标点与几处过度口语表达）。Task9 P1/P2 queue 已存在，保持 task2b_pending。 2026-05-22 16:06 Task6 re-review: pass-light-edit。L1/L2 小修 5 处；压掉不必要的“我们”第一人称和开头问题句式；既有 Task9 P1（16KB plugin packaging/ELF/runtime 边界）queue 保留，保持 task2b_pending。 2026-05-22 19:26 Task9 re-review: pass-tech-review，P0/P1/P2=0；queue 无 pending，自动晋升 finalized。"
updated_by: openclaw-task9
updated_date: 2026-05-22
p0: 0
p1: 0
p2: 0
auto_promoted: True
deepseek_cn_review_state: done
last_deepseek_cn_review_at: 2026-06-23
---
<!-- outline-start -->
## 本节要点大纲

### 锚点(必须覆盖)

- 🔹 Flutter 的渲染架构:Framework(Dart) → Engine(C++) → Platform Embedder 三层模型
- 🔹 Flutter 的线程模型:Flutter 3.29+ 的 Main(UI+Platform) / Raster / IO,以及 Flutter 3.28- 或定制 Embedder 的旧四线程模型
- 🔹 与原生 Android 渲染管线的根本区别:通过 Choreographer 获取 VSync、跳过 ViewRootImpl Traversal、无 RenderThread
- 🔹 PlatformView 的 Virtual Display / Hybrid Composition / TLHC 多路径及性能影响
- 🔹 常见性能问题:Shader 编译卡顿、Widget 过度重建、列表滚动卡顿
- 🔹 Impeller 引擎的 AOT shader 编译设计与 Skia 的对比
- 🔹 性能分析工具:Flutter DevTools + Perfetto 系统级分析的结合使用

### 扩展(可选深入)

- 🔸 Impeller 在 Android 上的 Vulkan 后端与 OpenGL ES 回退策略
- 🔸 PlatformView 对 Main(UI+Platform)、Raster 与 SurfaceFlinger 的性能影响
- 🔸 Flutter 自定义 Trace event 在 DevTools 和 Perfetto 中的使用

### OpenClaw 加工指引

> **锚点**是最低覆盖要求,加工时必须逐条落实并标注验证结果。
> **扩展**视素材丰富程度选择性深入。
> 如果从 Obsidian 素材或 AOSP 源码中发现大纲未列出但与本节强相关的知识点,
> 可作为"自动发现"补充,但需标注来源。
<!-- outline-end -->

# 2.11 Flutter 渲染管线与性能

## 为什么要了解 Flutter 的渲染

在 Perfetto 中分析 Flutter 应用，第一个要切换的是线程视角。原生应用里熟悉的 `ViewRootImpl.Traversal`、RenderThread 绘制阶段，在 Flutter 自绘 UI 路径上不会出现；trace 中 `1.platform` 或 `io.flutter.platform` 上有时能看到 `Choreographer#doFrame`，那只是 Flutter 订阅系统 VSync 的入口，不等于回到了原生 View 绘制流程。

Flutter 的 Android Embedder 通过 `VsyncWaiter` 调用 `Choreographer.postFrameCallback()`。回调到达后,`VsyncWaiter.FrameCallback#doFrame()` 把时间戳交给 `FlutterJNI.onVsync()`,后续的 Build、Layout、Paint 和 Raster 调度由 Flutter Engine 接管。Flutter 不使用 Android 原生 View 树渲染自己的 Widget,也没有原生应用里的 RenderThread 分工。

这个差异直接影响排查入口。列表滚动卡顿时，Flutter 3.29+ 要同时看 Android 主线程上的 Dart / Platform 工作和 `1.raster` / `io.flutter.raster`；如果是 Flutter 3.28- 或定制 Embedder，才需要单独看 `1.ui` / `io.flutter.ui`。

排查 Flutter 卡顿时，需要先定清三个问题：Flutter 在 Android 上怎么渲染，它的渲染管线和原生 Android 有什么差异，性能问题出现时应该看哪里、怎么分析？

## Flutter 的渲染架构

Flutter 的渲染架构分三层：Framework 层（Dart）、Engine 层（C++）和平台嵌入层（Platform Embedder）。

Framework 层是应用开发者直接接触的部分。Widget、State、Element,以及 Rendering 目录下的 RenderObject,都在这一层。当 UI 需要更新时,Framework 层会经历 Build → Layout → Paint 三个阶段:Build 阶段根据状态构建 Widget 树;Layout 阶段计算每个 RenderObject 的大小和位置;Paint 阶段将绘制指令记录到一个 DisplayList 中。

Engine 层是 Flutter 的核心引擎,用 C++ 编写。它负责两件事:一是把 Framework 层产生的 DisplayList 光栅化为实际的像素数据;二是管理与底层图形 API(Vulkan 或 OpenGL ES)的交互。Engine 层还包含了 Dart 虚拟机、文本排版引擎(最近从 libtxt 迁移到了 SkParagraph)、以及网络、文件等基础能力。

平台嵌入层相对较薄，负责把 Flutter Engine 嵌入到具体平台中。在 Android 上,它创建和管理 FlutterView(通常是一个 SurfaceView 或 TextureView),处理 Android 的生命周期事件,并将触摸等输入事件转发给 Flutter Engine。

这套三层结构把原生 View 体系留在 Android Embedder 边界。Widget 的 Build/Layout/Paint 不走 `ViewRootImpl.performTraversals()`,Raster 也不走原生应用的 RenderThread;但 Flutter 仍然通过 Android `Surface` / `ANativeWindow` 向 BufferQueue 提交 buffer,SurfaceFlinger 仍负责最终合成。差异在 producer:原生应用通常由 HWUI/RenderThread 生产图层内容,Flutter 自绘 UI 由 Engine 的 Raster 路径生产。

`[图:Flutter 三层架构与 Android 系统服务的关系。展示 Framework(Dart) → Engine(C++) → Platform Embedder(Android) 的层次关系,以及与 SurfaceFlinger、InputManager 的交互点]`

### 线程模型

Flutter 3.29 之后,Android / iOS 的主线线程模型改成 Main(UI+Platform) / Raster / IO。原先单独的 UI 线程不再作为移动端主线存在,Dart main isolate 与 Platform Embedder 运行在同一个原生平台主线程上。旧文档、旧 Trace 或定制 Embedder 仍可能出现 Platform / UI / Raster / IO 四线程形态,读 Trace 时先用 Flutter 版本判断。

**Main(UI + Platform)线程**(Android 主线程,Perfetto 中可能显示为 `1.platform`、`io.flutter.platform` 或进程主线程):承接 Android 生命周期、输入、Platform Channel、插件回调,也执行 Dart main isolate 上的 Widget Build、Layout、Paint,生成 DisplayList。这个线程被同步插件调用、Dart 计算或 View / PlatformView 工作占满时,都会直接压缩本帧预算。

**Raster 线程**(`1.raster` / `io.flutter.raster`):接收 DisplayList,调用 Skia 或 Impeller 生成 GPU 命令并提交到 Surface。Raster 线程 CPU 占用高,通常说明光栅化、纹理上传、shader / pipeline 或 GPU 提交工作偏重。

**IO 线程**(`1.io` / `io.flutter.io`):负责图片、文件等资源加载与部分 GPU 资源准备。它不直接执行 Widget Build,但图片解码、上传或资源等待会间接拖慢后续帧。

**Flutter 3.28- 旧模型**:Platform 线程处理 Android 主线程事件,UI 线程单独运行 Dart main isolate,Raster 与 IO 线程保持独立。读旧 Trace 时,`1.ui` / `io.flutter.ui` 上的 Build/Layout/Paint 是 Dart 侧主入口;读 3.29+ Trace 时,这些工作会并入 Main(UI+Platform) 线程观察。

在 Perfetto 中,线程名受内核 16 字符限制和 Embedder 命名影响。搜索 `io.flutter`、`flutter`、`BeginFrame`、`DrawFrame` 比只搜 `1.ui` 更稳。一个 3.29+ Flutter 应用的一帧大致是:Main(UI+Platform) 收到 VSync → Dart Build/Layout/Paint 生成 DisplayList → Raster 线程光栅化并提交 Surface → SurfaceFlinger 合成。

`[图:Flutter 3.29+ 线程模型在 Perfetto 中的表现。展示 Main(UI+Platform)、1.raster / io.flutter.raster、1.io / io.flutter.io 三组 Track,旁注 Flutter 3.28- 或定制 Embedder 中 1.ui / io.flutter.ui 仍可能独立出现]`

## 与 Android 原生渲染的差异

理解 Flutter 的渲染架构后，再和原生 Android 的渲染管线做系统对比。这个对比的用途是帮助实际排查快速定位问题，不做路线优劣判断。

### 渲染管线的根本区别

原生 Android 的渲染管线在 §2.3 和 §2.5 已经展开:VSync → Choreographer → MainThread(doFrame: Input/Animation/Traversal) → RenderThread → SurfaceFlinger。这条管线有几个特征:它由系统的 VSync-app 信号触发;MainThread 和 RenderThread 是流水线式的协作关系;最终的帧提交要通过 BufferQueue 和 SurfaceFlinger。

Flutter 的帧起点仍来自系统 VSync。Android 侧 `VsyncWaiter` 注册 `FlutterJNI.AsyncWaitForVsyncDelegate`,在 `asyncWaitForVsync()` 中调用 `Choreographer.getInstance().postFrameCallback()`;回调进入 `FrameCallback#doFrame()` 后再调用 `flutterJNI.onVsync(delay, refreshPeriodNanos, cookie)`。Flutter 使用 Choreographer 获取系统帧信号,随后由 Engine 接管 Dart 与 Raster 调度。它没有脱离 Choreographer 自己计时,也不会进入原生 View 的 traversal 流程。

拿到帧信号之后,Dart 层的 `setState()` 只负责标记需要重建的 Element;Build/Layout/Paint 在 Flutter Framework 内生成 DisplayList,再交给 Raster 线程执行 Skia 或 Impeller 绘制。在 Perfetto 中,如果开启 `view`/`gfx` 相关 atrace 类别,`1.platform` 或 `io.flutter.platform` 上可能出现 `Choreographer#doFrame`。判断是否走原生 View 绘制,不看有没有 Choreographer,而看后面有没有 `ViewRootImpl.Traversal`、HWUI / RenderThread 绘制和对应的 Android View 层级工作。Flutter 自绘 UI 的主路径会更多显示为 `BeginFrame`、`DrawFrame`、`GPURasterizer::DrawToSurface` 等 Engine 事件。

### Surface 的使用方式

Flutter 在 Android 上通过一个 Surface(通常是 SurfaceView 或 TextureView 提供的 Surface)来输出渲染结果。Flutter Engine 在 Raster 线程上完成光栅化后,直接将帧 buffer queue 到这个 Surface 中。SurfaceFlinger 在 VSYNC-SF 到来时,像合成其他任何 Surface 一样合成 Flutter 的 Surface。

还有一个细节:Flutter 没有绕过 BufferQueue。原生 Android 中,App 通过 `queueBuffer` 将 `GraphicBuffer` 提交给 BufferQueue,然后 SurfaceFlinger 通过 `acquireBuffer` 拿到 buffer 进行合成;Flutter 也走 Surface/BufferQueue 这条系统边界。Flutter 的 buffer producer 在 Engine Raster 路径里,提交动作来自 Engine 对 `Surface` / `ANativeWindow` 的使用,不经过 Android Framework 的 HWUI / RenderThread。

`[已验证: Flutter Engine 通过 Android Surface/ANativeWindow 提交帧,SurfaceFlinger 仍按普通 layer 合成;Engine VSync 入口见 VsyncWaiter.java, flutter/engine]`

### PlatformView:Flutter 与原生 View 的桥梁

Flutter 应用有时候需要嵌入原生的 Android View，比如 WebView、MapView，或者某些只有 Android 原生实现的控件。这就是 PlatformView 的工作。

PlatformView 不能再只按"两种模式"理解。Flutter Engine 源码里至少有三条可核对路径:

- **Virtual Display**:早期路径,把原生 View 渲染到 VirtualDisplay 的 Surface,再通过 Texture Widget 显示。Android 10 之前常见的额外拷贝来自这条路径,滚动和输入同步也更容易出问题。
- **Hybrid Composition / PlatformViewLayer**:把原生 View 放回 Android View 层级,适合承载 `SurfaceView` 这类无法稳定投影到 TextureLayer 的 View。`PlatformViewsController#createForPlatformViewLayer()` 会进入 `configureForHybridComposition()`,这条路径仍可能带来 Platform 线程上的布局、offset 和同步开销。
- **TextureLayer Hybrid Composition(TLHC)**:`PlatformViewsController#createForTextureLayer()` 的默认路径。源码注释把它标为 default / recommended for better performance;条件是 API 23+,且嵌入 View 不能包含需要 Virtual Display 的类型(典型是 `SurfaceView`)。Android 侧用 `PlatformViewWrapper` 把 View 放在 View 层级中,再把画面投影到 `PlatformViewRenderTarget`,由 Engine 以 TextureLayer 方式合成。

现代 Flutter 的 PlatformView 性能边界还要看 render target。`FlutterRenderer#createSurfaceProducer()` 在 API 29+ 且 AHB 可用时优先使用 `ImageReaderSurfaceProducer`,否则回退到 `SurfaceTextureSurfaceProducer`;`ImageReaderPlatformViewRenderTarget` 在 API 33+ 才能通过 `Image.getFence()` 等待同步 fence。这个分支解释了为什么 Android 10、Android 13 以后 PlatformView 的表现不能只套用早期 Hybrid Composition 结论。

分析 PlatformView 卡顿时,不要直接把所有问题归因成"线程合并"。如果走 PlatformViewLayer / Hybrid fallback,`1.platform` 上通常会出现更重的 View hierarchy、layout/offset/sync 工作;如果走 TLHC + ImageReader/SurfaceProducer,开销更多体现在 render target resize、image acquire、fence 等待和 SurfaceFlinger 合成上。WebView、MapView、SurfaceView、叠加动画和滚动列表会触发不同路径,Perfetto 里要同时看 `io.flutter.platform`、`io.flutter.raster` 和 SurfaceFlinger。

到了 Android 14 这一代,公开可核对的 Flutter 官方资料并没有给出"Hybrid Composition 再减少一次拷贝"这类新的通用结论。PlatformView 相关路径经历了一轮兼容性修复,Flutter 3.24 release notes 记录了 `Workaround HardwareRenderer breakage in Android 14` 和 `Fix another instance of platform view breakage on Android 14` 等修复项。Android 14+ 的收益更偏向 PlatformView / Surface 管理路径的稳定性修复,Hybrid Composition 的基本合成模型没有被重新设计。`[已验证: Flutter 3.24 release notes, https://docs.flutter.dev/release/release-notes-3.24.0]`

### 16KB Page Size 合规与 Flutter 原生插件

Flutter 的渲染最终通过 Android Surface 提交帧，但 Flutter 应用里如果引入原生插件（PlatformView、FFI 或预编译 .so），Android 15+ 的 16KB page size 要求就会直接影响这些原生代码的兼容性。这一点不是渲染管线本身的问题，但多数 Flutter 应用都会用到原生插件，排查异常崩溃时经常要回到这里。

Android 15+ 已支持 16KB page-size 设备。Google Play 从 2025-11-01 起要求所有面向 Android 15+ 的新应用和更新兼容 16KB page sizes。对 Flutter 开发者来说，影响的是包含原生代码的第三方插件，而不是 Dart 代码本身。

Flutter plugin 中的 `.so` 文件对齐要求取决于 NDK 版本：

- **NDK r28+**：默认生成 16KB-aligned shared libraries，无需额外配置
- **NDK r27 及以下**：必须显式配置 linker flags（如 `-Wl,-z,max-page-size=16384` / `-Wl,-z,common-page-size=16384`），否则在 16KB 环境下会出现内存对齐错误和运行时崩溃

排查清单：

- `flutter pub deps` 列出所有依赖，逐个检查含原生代码的 plugin 是否已适配 16KB
- 搜索 plugin 的 `build.gradle` / `CMakeLists.txt`，优先升级 NDK r28+（默认生成 16KB-aligned `.so`）
- 若必须使用 NDK r27 或更低版本，在 `CMakeLists.txt` 或 `android` 块中显式配置 linker flags，并确保 AGP 8.5.1+ packaging 对齐
- 在 16KB 模拟器（`--16kb-page-size`）或 16KB 真机上跑集成测试，验证 native 层行为
- 重点检查 PlatformView、FFI、`dart:ffi` 直连 native 库这三类路径——对齐错误在这些场景下最容易触发
- 复测预编译 `.so` 和 `libc++_shared.so` 的对齐状态

如果某个关键 plugin 还没有适配，需要区分两类问题：若是 AGP/APK zip alignment 问题，可升级 AGP 8.5.1+（自动处理 uncompressed shared libraries 的 16KB 对齐），或在旧版 AGP 下临时使用 compressed shared libraries；若是 plugin 内含未重新编译的 `.so`（ELF `p_align` 仍为 4KB）或 native 代码中 hardcoded `PAGE_SIZE=4096`，必须等待 plugin 作者更新、本地 fork 用 NDK r28+ 重编、或替换 plugin。`packagingOptions` 不能修复 ELF segment alignment 和 native 代码的 4KB 假设。

`[已验证: Android 15+ 16KB page size requirements, developer.android.com/guide/practices/page-sizes; NDK r28 release notes]`

## 性能分析方法

分析 Flutter 应用的性能有一个天然难点：Flutter Engine 内部的 Dart/C++ 层面和 Android 系统的内核/GPU 层面各管一摊，问题可能出在任何一层。因此需要两套工具配合：Flutter DevTools 看 Engine 内部的执行细节，Perfetto 看系统层面的调度和合成状态。

### Flutter DevTools

Flutter DevTools 是 Flutter 官方的性能分析套件。它提供了几个关键的分析面板:

**Performance 面板**(集成 Perfetto trace viewer):这是最常用的面板。它记录每一帧的 UI / Main 侧和 Raster 线程耗时,用火焰图展示。Flutter DevTools 在 2.21.1 版本就已经把旧的 timeline trace viewer 替换成 Perfetto trace viewer。DevTools 的演进节奏和 Flutter SDK 版本不一一绑定，分析问题时以 DevTools 自身版本为准。`[已验证: Flutter DevTools 2.21.1 release notes, https://docs.flutter.dev/tools/devtools/release-notes/release-notes-2.21.1]`Performance 面板中展示的信息包括：

- 每一帧在 UI / Main 侧的 Build、Layout、Paint 各自花了多少时间
- Raster 线程的光栅化耗时
- 是否有帧超出了帧预算(60Hz 下 16ms,120Hz 下 8ms)
- 具体是哪个 Widget 或哪个 Dart 函数消耗了最多的时间

**CPU Profiler 面板**:提供 Dart 代码的 CPU 采样分析,展示 Dart 函数级别的 CPU 占用。

**Memory 面板**:监控 Dart 堆的内存使用,帮助发现内存泄漏。

使用 DevTools 分析时有一个前提：必须在 Profile 模式下运行。Debug 模式引入了大量调试断言和 JIT 编译开销，性能数据不能代表真实发布环境。在命令行中用 `flutter run --profile` 启动即可。

### Perfetto 系统级分析

当 Flutter 应用出现性能问题,但 DevTools 中找不到明显的 Dart 层面瓶颈时,问题可能出在系统层面。这时就需要用 Perfetto 抓取系统级 Trace。

抓取 Flutter 应用的 Perfetto Trace 和抓取原生应用的没有本质区别。一个推荐的抓取配置:

```bash
# 抓取包含 Flutter 线程和 SurfaceFlinger 的 Trace(持续 10 秒)
adb shell perfetto -c - --txt <<EOF
buffers: { size_kb: 63488 }
data_sources: {
  config {
    name: "linux.ftrace"
    ftrace_config {
      ftrace_events: "sched/sched_switch"
      ftrace_events: "power/cpu_frequency"
      atrace_categories: "view"
      atrace_categories: "gfx"
      atrace_categories: "input"
    }
  }
}
duration_ms: 10000
EOF
```

在 Perfetto UI 中查看时,需要关注不同的 Track:

- Flutter 3.29+ 的 Main(UI+Platform) 线程:看 Dart Build/Layout/Paint、Platform Channel、插件同步调用和 PlatformView 工作是否挤占同一帧预算
- Flutter 3.28- 或定制 Embedder 的 `1.ui` / `io.flutter.ui`:看 Dart 代码执行耗时、Widget 重建和 Dart VM GC
- `1.raster` / `io.flutter.raster`:看光栅化、纹理上传、shader / pipeline 和 GPU 提交耗时
- `1.io` / `io.flutter.io`:看图片解码、资源加载和 GPU 资源准备是否拖慢后续帧
- CPU 整体使用率:看 Flutter 线程和系统服务是否在争抢 CPU 时间
- SurfaceFlinger Track:看 Flutter 的 Surface 合成是否正常

在 Perfetto 中,Flutter Engine 会输出自己的 trace event。系统抓 trace 时要保留 `gfx`、`view` 这类 atrace 类别,并在 UI 里同时搜索 `flutter`、`io.flutter`、`BeginFrame`、`DrawFrame`。常见 slice 包括 `FlutterEngine::BeginFrame`、`GPURasterizer::DrawToSurface`;不同 Flutter 版本的事件名会变化,过滤时不要只依赖单个字符串。

### ADPF 系统级调频（待验证）

排查 Flutter 性能时，还有一种情况是 Raster 线程本身负载正常，但帧仍然超时——可能是系统没有及时给到足够的 CPU / GPU 频率。Android 的 ADPF 框架提供了一种机制来解决这个问题，下面说明 Flutter Engine 当前对它的支持程度。

ADPF（Adaptive Performance Framework）的 `PerformanceHintManager` 是 Android 平台提供的动态调频接口。App 或引擎可以创建 HintSession,逐帧调用 `reportActualWorkDuration()` 反馈渲染负载,系统根据反馈调整 CPU/GPU 频率。

Flutter 应用中 Raster 线程的工作量波动比原生应用更大。原生应用可以靠 Hardware Layer 缓存跳过部分帧的重绘,Flutter 自绘每一帧的内容,因此负载波动更剧烈。ADPF 的动态调频在理论上能更好地匹配这种波动特征。

截至当前,Flutter Engine 主干（ae5c360）的 `shell/platform/android`、`impeller`、`fml`、`runtime`、`lib/ui`、`common` 目录中未检索到 `PerformanceHint`、`APerformanceHint`、`reportActualWorkDuration`、`HintSession` 等符号；Flutter issue #155097（[Android] Determine if Android Performance Hint Manager is useful）已关闭为 not_planned。当前公开源码不能支撑“Flutter Engine 已自动启用 ADPF HintSession”这一结论。

在 Perfetto 中观察 ADPF 效果的方法：检查 `ADPF` 相关 slice 与 CPU frequency counter 的联动。当 Raster 线程进入高负载区间时,后续帧的 CPU 频率应该被拉高。如果频率没有响应,可能是设备的 ADPF 实现存在延迟或厂商定制限制。

如果后续 Flutter Engine 显式接入了 ADPF,排查性能问题时可以把调频响应时间作为一个辅助诊断维度——如果调频延迟超过了当前帧的剩余预算,提频就来不及挽救当前帧。

### 自定义 Trace

Flutter 支持在 Dart 代码中插入自定义的 trace event,这些 event 会同时出现在 DevTools 和 Perfetto 中:

```dart
import 'dart:developer' as developer;

// 在需要追踪的代码块前后添加
developer.Timeline.startSync('my_custom_operation');
// ... 需要追踪的代码
developer.Timeline.finishSync();
```

这在定位某个特定操作的耗时时非常有用。比如怀疑某个列表的 item builder 太慢时,可以在 builder 中添加 trace event,然后在 DevTools 或 Perfetto 中直接看到它的耗时。

## 常见性能问题

这些工具可以对应到 Flutter 在 Android 上最常见的几类性能问题。不同问题在 Perfetto 和 DevTools 中有不同表现,识别这些特征是定位问题的关键。

### Shader 编译卡顿(Skia 时代)

这是 Flutter 使用 Skia 渲染引擎时长期最容易被提到的问题。Skia 在运行时编译 shader 程序，这些 shader 是 GPU 用来执行特定绘制操作的小程序。当 Flutter 应用首次遇到一种新的绘制操作(比如第一次使用某个复杂的 BlendMode、第一次绘制带有特定 path 操作的裁剪)时,Skia 需要在 Raster 线程上编译对应的 shader。

这个编译过程可能明显超出一帧预算。常见现象是:应用启动后第一次滚动到某个页面时,或者第一次播放某个动画时出现卡顿;第二次经过同样的页面或动画时,shader 已经进入缓存,卡顿会减轻或消失。具体耗时要以目标设备和驱动为准。

在 Perfetto 中,这种现象表现为 Raster 线程上突然出现一个很长的 slice,内部包含 `ShaderCompile` 相关的标记。整个 Raster 线程在这段时间被阻塞,UI / Main 侧虽然已经准备好了 DisplayList,但必须等 Raster 线程完成 shader 编译才能继续。

Flutter 团队曾提供 `flutter drive` 配合 SkSL warm-up 的方案来预热 shader,但这个方案使用复杂,效果也不稳定。更稳的方向是切换到 Impeller 引擎。

### Widget 过度重建

这是 Dart 层面最常见的性能问题。Flutter 的声明式 UI 框架在状态变化时会重建 Widget 树,但如果不注意控制重建范围,很容易导致整棵树都在重建。

最常见的表现是:在 Perfetto 或 DevTools 中,UI / Main 侧每一帧耗时都很长,火焰图显示大量的 `build` 方法在执行。但 Raster 线程很空闲，因为 UI / Main 侧虽然生成了大量 DisplayList，很多内容并没有变化。

这类问题的诊断和修复属于 Flutter 开发层面的优化,核心思路是:用 `const` 构造函数标记不需要重建的 Widget、将大的 build 方法拆分为小组件、使用合适的 State 管理方案限制重建范围。DevTools 的 "Rebuild Tracker" 功能可以帮助定位哪些 Widget 被频繁重建。

### PlatformView 相关的性能问题

当 Flutter 应用中嵌入了原生 View(如 WebView、MapView),性能特征会发生显著变化。

一是 Main(UI+Platform) 线程压力。旧模型里常把 Hybrid Composition 的回退称为 thread merging:当 Flutter 内容和 PlatformView 内容重叠时,部分渲染与 View hierarchy 工作会压到 Platform 线程。Flutter 3.29+ 已把 Dart UI 与 Platform 主线程合并,表现会变成同一条主线程同时承担 Dart Build/Layout/Paint、插件回调、View 布局和 PlatformView 同步工作。Perfetto 中要同时看 Main(UI+Platform) 与 `1.raster` 是否一忙一闲,不能只套用旧的 `1.ui` / `1.platform` 分离模型。

另一个常见场景是可滚动列表中嵌入多个 PlatformView。每个 PlatformView 在滚动时都需要更新 offset、size 或 Surface 状态,这会触发布局、同步 fence 或 SurfaceControl transaction。如果列表快速滚动,这些操作可能超出帧预算。

### 列表滚动卡顿

Flutter 的 ListView/GridView/CustomScrollView 在数据量大时可能出现卡顿。原因通常是 item builder 太慢：每个 item 在构建时做了太多工作（网络请求、图片解码、复杂的 Widget 树等）。

在 Perfetto 中的表现是 UI / Main 侧在滚动时持续高负载,每一帧的 Build 阶段耗时过长。Flutter 提供了 `ListView.builder` 和 `cacheExtent` 等机制来缓解这个问题：builder 只构建可见区域附近的 item，cacheExtent 控制预构建范围。

## Impeller 引擎

前面讨论的性能问题里，shader 编译卡顿是最难绕过的一类：即使 Dart 代码已经优化到位，Widget 树管理得很干净，用户第一次看到某个动画时依然可能卡顿。这就是 Flutter 团队开发 Impeller 的原因。

### 为什么需要 Impeller

Impeller 是 Flutter 的新一代渲染引擎,从 Flutter 3.16 开始在 iOS 上默认启用,从 Flutter 3.27 开始在 Android API 29+ 上默认启用。它的目标是把 shader compilation jank 从移动端运行时路径里移出去。

Skia 时代,某些 shader / pipeline 在首次遇到时才由驱动编译,复杂 path、blend、mask、clip 或特定 GPU 驱动组合可能让 Raster 线程出现长 slice。耗时没有通用数字,受 GPU、驱动、shader 类型、缓存状态影响;排查时以目标设备的 DevTools / Perfetto 为准。

Impeller 的离线处理发生在 engine build 阶段;应用构建阶段不会把业务里所有可能 shader 逐个预编译。engine 的 `impellerc` 将 Impeller 源码树中的 GLSL 4.60 shader 转成后端格式,生成 shader archive / binary blob,并通过 reflector 生成 C++ translation units,减少运行时 shader reflection。应用运行时使用随 engine 打包的 shader 资产和生成代码,再按绘制场景创建或复用 pipeline state object。官方文档把它概括为:shader compilation and reflection offline at build time,pipeline state objects built upfront,缓存由 engine 显式控制。

### Impeller 的架构

Impeller 的内部架构可以分为几个层次:

**DisplayList / Entity 层**负责接收 Flutter Framework 生成的 DisplayList,并把绘图意图转换为 Impeller 内部的 2D render entity。每个 entity 描述一次绘制操作,包括变换、裁剪、纹理、颜色和 shader 参数等信息,后续再由 renderer 转成具体后端命令。

**Renderer / backend 层**管理纹理、buffer、render pass、pipeline state object(PSO)和后端 API 适配。Impeller 支持 Vulkan、Metal 和 OpenGL ES 等后端;具体后端实现位于 `//impeller/renderer/backend` 之下,上层通过 backend-agnostic 的接口组织绘制。

**离线 shader 管线**由 `//impeller/compiler`、`//impeller/shader_archive` 和生成的 C++ translation units 组成。`impellerc` 不随应用发布;它在 engine build 阶段把 shader 与 reflection 信息处理成 engine 可打包的资产和代码,运行时再用这些资产创建或复用 PSO。

**渲染执行**阶段,Impeller 按 render pass / command buffer 组织绘制,并尽量利用现代图形 API 的并发和显式资源管理。公开 README 说明 Impeller 可以在需要时把单帧 workload 分发到多线程,以及 entity 层有 pass optimization / pass rewriting;"只光栅化变化 Tile"缺少一手资料支撑,本节不把它当成 Android 通用行为。

`[图:Impeller 渲染管线的层次结构。展示 DisplayList / Entity → Renderer → backend → GPU (Vulkan/Metal/OpenGL ES) 的数据流,标注 engine build 阶段的 impellerc、shader archive 与 C++ translation units]`

### Impeller 在 Android 上的表现

Impeller 在 Android 上优先使用 Vulkan 后端。Flutter 3.27 起,Android API 29+ 默认启用 Impeller;低于 API 29、设备不支持 Vulkan,或 API 29+ 但 AHB / 后端条件不满足时,会回退到 legacy OpenGL / SurfaceTexture 路径。

从公开可核对的资料看,Impeller 相比 Skia 最明确的收益是更可预测的渲染时序。Flutter 官方文档强调的是两件事:一是 shader 在 engine build 阶段就完成预编译,不再把编译压力留到运行时;二是 pipeline state object 会提前构建好,所以复杂动画第一次出现时更不容易被 shader compilation jank 打断。`[已验证: Flutter Impeller 文档, https://docs.flutter.dev/perf/impeller]`

这也是为什么前文的"30-50% 改善"不适合当作通用结论。那组数字更接近 2024-2025 年第三方样本中的经验区间,受 GPU 型号、驱动版本、场景复杂度、是否夹杂 PlatformView 等因素影响很大。更稳妥的写法是:社区测试经常观察到光栅化时间下降、jank 帧减少,但 Flutter 官方并没有给出一个对所有 Android 设备都成立的统一基准。

项目评估 Impeller 时,需要关注两类现象:第一,首次进入复杂页面或首次播放动画时,Raster 线程是否还会被 shader 编译长时间阻塞;第二,在同一段动画里,帧时间分布是否比 Skia 更稳定。提升幅度最好直接用目标机型的 Perfetto 和 Flutter DevTools 做实测,不套用别人的百分比。

#### Vulkan 1.4 Host Image Copy 与纹理上传

Impeller 在 Android 上优先使用 Vulkan 后端，而 Android 16+ 出厂设备强制支持 Vulkan 1.4，这带来了纹理上传路径的潜在优化空间。虽然 Flutter Engine 当前尚未启用这个能力，但了解它的原理有助于判断未来版本中的纹理上传性能变化。（升级到 Android 16 的旧设备可选支持,需运行时查询 `vkEnumerateInstanceVersion` / device extension / feature bit）。`VK_EXT_host_image_copy` 扩展允许 CPU 直接把纹理数据写入 GPU 可访问的内存,省掉了传统路径中的 Staging Buffer 中转和 GPU 搬运命令。这属于 Android/Vulkan 通用能力,不作为 Flutter 当前可依赖能力。

但截至当前 Flutter Engine 主干（ae5c360）,Impeller Vulkan 后端的 capability 枚举只包含 `VK_EXT_pipeline_creation_feedback`、`VK_KHR_portability_subset`、`VK_EXT_image_compression_control` 三个可选扩展,未启用 `VK_EXT_host_image_copy`。`impeller/renderer/backend/vulkan/texture_vk.cc` L75-L130 仍创建 staging buffer 并调用 `vk_cmd_buffer.copyBufferToImage()`。全局搜索 `host_image_copy` / `CopyMemoryToImage` 无命中。

Android Developers 公开的 Vulkan benchmark 数据显示,启用该扩展后纹理上传速度提升约 45%,上传期间的内存峰值降低约 50%——这是 Android/Vulkan 层面的合成 benchmark,不是 Flutter 实测结果。Impeller 未来可能采纳该扩展作为优化方向,但当前 Flutter 场景下的纹理上传仍走传统 Staging Buffer 路径。

该扩展仅在出厂搭载 Android 16+ 且 GPU 驱动支持 Vulkan 1.4 的设备上生效；升级到 Android 16 的旧设备需运行时查询 device extension 是否可用。低于该版本的设备不受影响。

`[已验证: Impeller 默认状态基于 Flutter 3.27 release notes, flutter.dev]`

不过,Impeller 在 Android 上的成熟度不如 iOS。在 Flutter 3.27 刚发布时,一些开发者报告了 Impeller 在 Android 上的兼容性问题,包括某些 ListView 场景下的性能退化、首次启动时的视觉质量问题等。Flutter 团队在持续修复这些问题,如果在使用中遇到问题,可以通过 `--no-enable-impeller` 参数回退到 Skia 来验证是否是 Impeller 导致的。

## 常见误区

分析 Flutter 应用性能时,下面几个认知陷阱最容易干扰判断:

**误区一:"Flutter 不卡,因为渲染不走 Android 主线程"**

Flutter 3.29+ 的 Dart UI 工作就在 Android 主线程上运行;旧模型里 Dart UI 即使在独立 UI 线程,也仍受固定帧预算约束。Dart Build/Layout/Paint、Raster、Platform Channel、PlatformView 任一段超预算,用户都会感知到卡顿。120Hz 下每帧预算约 8.33ms,在 Perfetto 中看到 Main(UI+Platform)、`1.ui` 或 `1.raster` 上的长 slice,都需要继续拆。

**误区二:"DevTools 够用了,不需要 Perfetto"**

DevTools 能看到 Dart 层面的性能数据,但看不到系统层面的问题。如果 Flutter 应用因为内存压力被系统杀掉、因为 CPU 调度被限频、或者因为 SurfaceFlinger 合成延迟导致掉帧,DevTools 完全看不到这些信息。两者结合使用才能拼出完整的性能图景。

**误区三:"换成 Impeller 就不需要优化了"**

Impeller 解决的是 shader 编译卡顿这一类特定问题。Widget 过度重建、PlatformView 主线程压力、列表 item builder 过慢仍然要单独优化。Impeller 让渲染管线的性能更可预测,每帧工作量仍然要控制。

**误区四:"Flutter 的帧率和原生应用用同一套方法分析"**

虽然最终都是 SurfaceFlinger 合成,但 Flutter 的线程模型和原生不同。原生应用主要看 MainThread、RenderThread 和 SurfaceFlinger;Flutter 3.29+ 要看 Main(UI+Platform)、Raster、IO 与 SurfaceFlinger,旧模型还要单独看 `1.ui`。工具和分析思路都需要切换。

## 优化策略

Flutter 渲染性能优化可以先抓三个要点。

### 必须做的事

**始终在 Profile/Release 模式下测试性能**。Debug 模式的性能数据没有参考价值——JIT 编译、调试断言、DevTools 的通信开销会让性能看起来比实际差得多。

**优先使用 Impeller**。运行在 Android API 29+ 的 Flutter 3.27+ 应用默认启用 Impeller;低版本系统、无 Vulkan 支持或后端条件不满足时会回退到 legacy OpenGL。评估时用 `--no-enable-impeller` 做 A/B,对比 Raster 线程首次进入复杂页面或动画时是否仍有 shader / pipeline 长 slice。

**控制 Widget 重建范围**。使用 `const` 构造函数、拆分大 Widget、选择合适的状态管理方案。用 DevTools 的 Rebuild Tracker 来定位不必要的重建。

### 分析策略

遇到 Flutter 性能问题时,按照以下步骤排查:

1. **先在 DevTools Performance 面板看**:是 Main / UI 侧慢,还是 Raster 线程慢?这会决定后续排查方向。
2. **Main(UI+Platform) 或 UI 侧慢**:打开 CPU Profiler 看 Dart 函数热点,检查 Widget 重建、同步 IO、插件同步调用和耗时计算。重计算应移到 Isolate,插件同步调用要拆成可等待的异步路径。
3. **Raster 线程慢**:检查是否还有 shader / pipeline 长 slice;检查过度绘制、纹理上传、复杂 Clip / Opacity / ShaderMask 和 PlatformView 合成。
4. **两边都不慢但帧率仍低**:可能是系统层面的问题。用 Perfetto 抓系统 Trace,看 CPU 调度、GC、内存压力等。

### PlatformView 的优化

- 尽量减少可滚动区域中 PlatformView 的数量
- 在 PlatformView 上方执行 Flutter 动画时,考虑使用截图纹理(snapshot texture)替代实时渲染
- 确保目标 Android 版本为 10+,以获得 Hybrid Composition 的 GPU 内存优化
- 如果使用自定义 Plugin 渲染到 Surface,优先使用 `SurfaceProducer` API(API 29+)

## 与其他章节的关联

Flutter 的渲染虽然自成体系,但它仍然运行在 Android 系统之上。理解本书前面讲的基础知识对分析 Flutter 性能同样重要:

- **§2.3 VSync 机制**:Flutter 的 VSync 监听最终依赖 Android 的 VSync-app 信号,理解 VSync 的调度逻辑有助于排查帧同步问题
- **§2.5 MainThread 与 RenderThread 协作**:Flutter 3.29+ 的 Dart UI 与 Platform 主线程已经合并;PlatformView、插件同步调用和原生 View 工作会直接影响同一条主线程的帧预算
- **§4.4 Low Memory Killer**:Flutter 应用占用内存通常比原生应用高(Dart VM 堆 + Skia/Impeller 资源),在低内存场景下更容易被 LMK 杀掉
- **§5.4 DVFS**:Flutter 的多线程模型(UI + Raster 同时运行)对 CPU 频率调度有影响,可能导致 DVFS 策略不如预期
- **§7.1 卡顿的定义与分类**:Flutter 应用的掉帧表现和原生应用在 Perfetto 中的 Track 不同,但卡顿的分类框架同样适用——理解 jank 的分类有助于在 DevTools 中快速判断是 UI / Main 侧 jank 还是 Raster 线程 jank
- **§7.7 Jetpack Compose 性能**:Compose 和 Flutter 都是"自绘引擎"路线(不依赖原生 View 体系),两者在 PlatformView/互操作场景下遇到类似的主线程压力和合成性能问题,优化思路可以互相参考
- **§18.12 Flutter 渲染路径**:该章节按 Flutter 3.29+ 的 Main(UI+Platform) / Raster / IO 口径展开,可作为本章实践分析部分的延伸阅读


### Flutter 3.44 源码侧补充（2026-06-25 AIW-源码调研）

> 说明：选题 daily-topics.json id 17 标的章节为 §7.8（实际指向 RecyclerView），Flutter 3.44 主题与本节（2.11）和 §18.12 强相关，反哺在 2.11。

**版本锚点**

- 稳定版序列（git tag，按版本号倒排）：`3.46.0-0.1.pre` → `3.45.0-0.1.pre` → `3.44.4` → `3.44.3` → `3.44.2` → `3.44.1` → `3.44.0`
- 引擎版本（`bin/internal/engine.version`，3.44.0 与 3.44.4 一致）：`4c525dac5ebe5971c5708ef73558ed8edcf4a362`
- Dart SDK（DEPS 中）：`98116461144f4429ab873f8497023a5ec3b08127`
- AGP 模板（CP-beta #186099）：3.44 起 **Android 模板升级到 AGP 9**

**Agentic 能力——源码中实际能验证的只有这两块**

1. `agent-artifacts/` 顶层目录：`agent-artifacts/README.md` 明确为 AI 编码代理的临时文件沙箱，`.gitignore` 排除所有非 README 文件。
2. `.agents/skills/` 顶层目录：遵循 [agentskills.io 开放标准](https://agentskills.io/specification) 与 [Claude Agent Skills 命名约定](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices#naming-conventions)。首个落地 skill 为 `find-release/SKILL.md`，调用契约：

   ```
   dart run ${FIND_RELEASE_TOOL_PATH:-engine/src/flutter/third_party/dart/tools/find_release.dart} \
     --commit=<SHA> --channel=<CHANNEL>
   ```

   **.agents/skills/README.md 的关键约束**：
   - 提交 PR 时必须附 agent 实际使用 prompt 与产出示例
   - "One Skill Per CLI Tool""Read-Only Mode by default""Dart Scripts"
   - 作者负责制（Ownership），不可无主修改

   **重要**："Agentic Hot Reload""GenUI 生成式 UI" 这两个选题描述的特性，在 3.44 稳定版源码中**无对应运行时类/Service Extension**（`git tree --recursive 3.44.0` 全量扫描，`agent` 命中 6 个文件全是 devicelab/skills 文档；`genui` 零命中）。属于 keynote 营销口径。

**性能侧实质改进（可源码验证）**

`packages/flutter_tools/lib/src/run_hot.dart`：

- line 44–45：`HotRunnerConfig.asyncScanning` 新增字段
- line 524：调用点 `asyncScanning: hotRunnerConfig!.asyncScanning`
- line 1576–1643：`invalidateForReloadSources(..., bool asyncScanning = false)` 用 `package:pool` 的 `Pool` 做并发受控文件扫描，缩短 `findInvalidationTimer` 阶段耗时

默认 `asyncScanning: false`（向后兼容），需在 `HotRunnerConfig` 注入开启。**仅影响 dev mode 热重载延迟，不影响生产帧率**。

**3.44 hotfix 链的"性能"相关修复**

| PR       | 描述                                                                         |
| -------- | ---------------------------------------------------------------------------- |
| #188192  | 修 `FlAccessibleTextField` bounds checking                                  |
| #186899  | 修 Android 平台 GLES fence 释放时序导致 texture 崩溃                          |
| #186953  | 修 SwiftPM 并发 build 目录竞争                                                |
| #183179  | 修 animated PNG 帧的 pixel buffer overflow                                   |
| #186723  | 修 `SystemUiMode → edge-to-edge` 切换后 system bars 不显示（2.11 全屏边界更新） |

**Impeller 边界**

3.44 稳定版（engine `4c525dac5e…`）**未携带** Impeller 新特性合并。3.44 之后的 master 才有大动作：

- `#188056 [Impeller] Add anisotropic filtering support to samplers`（2026-06-25）
- `#187573 Turn linux impeller on by default`（2026-06-24）
- `#188188 Migrates flutter windows test to impeller`（2026-06-24）

本节（2.11）原有的 Impeller 描述（"Android API 29+ 默认启用""低版本/无 Vulkan 回退 legacy OpenGL"）**继续有效**，3.44 不改这条边界。

**AGP 9 模板的实操影响**

切到 3.44 模板后，`./gradlew assembleRelease` 走 AGP 9 的 R8/dexopt 路径；本节（2.11）的"Profile/Release 模式"实践应同步做一次 APK 体积 + 启动类初始化 A/B。配合 `#186040`（AGP 9 报错文档链接修正）与 `#186106`（Broken Flutter Docs Link 修正），3.44 模板属于稳定的工程动作，不是实验。

**与 2.11 章节"必须做的事"的更新建议**

- 新增一条：**3.44 后的项目首次构建时做一次 AGP 9 → AGP 8 体积/启动 A/B**（按 minSdk 区间分别测）。
- 已有"hot reload 文件扫描慢"现象的开发者可注入 `HotRunnerConfig.asyncScanning = true` 测试加速比；典型受益场景是大型项目（> 5k Dart 文件）首次扫描。


## 参考资料

- Flutter 官方性能文档:https://docs.flutter.dev/perf/rendering-performance
- Impeller 文档:https://docs.flutter.dev/perf/impeller
- Impeller engine README:https://github.com/flutter/engine/blob/main/impeller/README.md
- Flutter 3.29 线程模型说明:https://docs.flutter.dev/release/release-notes/release-notes-3.29.0
- Flutter 性能最佳实践:https://docs.flutter.dev/perf/best-practices
- PlatformView 性能:https://docs.flutter.dev/platform-integration/android/platform-views
- Flutter Engine 源码(Impeller 目录):https://github.com/flutter/engine/tree/main/impeller
- Flutter Engine VSyncWaiter 源码:https://github.com/flutter/engine/blob/main/shell/platform/android/io/flutter/view/VsyncWaiter.java
- Flutter Engine PlatformViewsController 源码:https://github.com/flutter/engine/blob/main/shell/platform/android/io/flutter/plugin/platform/PlatformViewsController.java
- Flutter Engine FlutterRenderer SurfaceProducer 源码:https://github.com/flutter/engine/blob/main/shell/platform/android/io/flutter/embedding/engine/renderer/FlutterRenderer.java
- Flutter DevTools 文档:https://docs.flutter.dev/tools/devtools
