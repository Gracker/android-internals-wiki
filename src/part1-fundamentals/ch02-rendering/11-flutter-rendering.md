---
title: Flutter 渲染管线与性能
chapter: 2.11
section: 2.11
status: finalized
pipeline_stage: ready-to-publish
applicable_versions: Android 10 (API 29) - Android 17 (API 37)
tags: [flutter, rendering, impeller, skia, cross-platform, shader-compilation, jank]
confidence: high
last_verified: 2026-07-25
last_verified_against: Flutter 3.44.8 (058e0af2c2b57e369d905a03ac9748b0ebf543c6, engine 0cd610717bde95fd88343c64f81c11ba4e5c0010) + AOSP android-17.0.0_r1 + kernel android17-6.18-2026-06_r6 + Writer rendering_pipelines/S10_flutter_type.md + official Flutter and Android documentation
sources:
- type: source
  path: https://github.com/flutter/flutter/tree/3.44.8/engine/src/flutter/shell/platform/android
- type: source
  path: https://github.com/flutter/flutter/tree/3.44.8/engine/src/flutter/impeller
- type: source
  path: https://github.com/flutter/flutter/blob/3.44.8/engine/src/flutter/shell/platform/android/flutter_main.cc
- type: source
  path: https://github.com/flutter/flutter/blob/3.44.8/engine/src/flutter/shell/platform/android/android_context_dynamic_impeller.cc
- type: official
  path: https://docs.flutter.dev/resources/architectural-overview
- type: official
  path: https://docs.flutter.dev/perf/impeller
- type: official
  path: https://docs.flutter.dev/platform-integration/android/platform-views
- type: official
  path: https://github.com/flutter/flutter/issues/150525
- type: official
  path: https://source.android.com/docs/core/graphics/implement-vulkan
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/view/
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/native/+/android-17.0.0_r1/services/surfaceflinger/
- type: aosp
  path: https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/drivers/dma-buf/
- type: material
  path: /Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Writer/rendering_pipelines/S10_flutter_type.md
related_chapters: ['2.1', '2.3', '2.4', '2.5', '7.1', '7.7', '18.12']
task9_state: reviewed
task2b_state: fixed
task6_state: reviewed
---
# 2.11 Flutter 渲染管线与性能

Flutter 页面进入 Perfetto 后，不能只找一条“Flutter UI 线程”。页面最终怎样显示，由三组配置共同决定：

- Flutter root 使用 `surface`、`texture` 还是 `image` render mode；
- 相机、视频或原生渲染器是否通过 external texture 提供内容；
- PlatformView 使用 TLHC、Hybrid Composition、旧 Virtual Display 还是 HCPP。

同一页面可以同时存在 Flutter root Surface、相机输入、原生地图 View、Flutter overlay 和系统窗口。每个对象都有自己的 producer、buffer、fence 与节拍。

先约定这些名称：Flutter root 是 Flutter 主画面的输出目标，RenderMode 决定它接到独立 Surface、宿主纹理还是 ImageReader；external texture 是由相机、视频或原生渲染器生产、再交给 Flutter Raster 采样的外部图像；PlatformView 是嵌入 Flutter 页面中的原生 Android View。TLHC 是 Texture Layer Hybrid Composition，HC 是 Hybrid Composition，旧 VD 是 Virtual Display，HCPP 是 Hybrid Composition++。这四种路径分别决定原生 View 是先变成 Flutter 可采样纹理，还是保留 Android Surface/View 身份参与最终合成。

Producer 负责生成并提交 buffer，Consumer 负责取得并使用它；fence 表示异步读写何时完成。这里的 overlay 指为了遮挡或组合 PlatformView 而额外生成的 Flutter/Android 图层，不是泛指页面上所有浮层。

分析固定三条版本线：

- Android 平台：Android 17 / API 37 / `android-17.0.0_r1`；
- kernel：`android17-6.18-2026-06_r6`；
- Flutter：用稳定 tag `3.44.8`、framework commit `058e0af2c2b57e369d905a03ac9748b0ebf543c6`、engine revision `0cd610717bde95fd88343c64f81c11ba4e5c0010` 验证当前实现。

Android 决定 Surface、BufferQueue、SurfaceFlinger、HWC 与 kernel 的同步规则。Flutter framework、engine、Android embedding（Flutter engine 接入 Android 的宿主层）和插件随 App 发布；分析线上问题时，仍要回到 APK 实际携带的 Flutter SDK、engine revision、renderer（渲染器）、backend（连接 Vulkan/OpenGL ES 与驱动的后端）和插件版本。

## 三层架构与一帧的公共前半段

### Framework：生成绘制意图

Framework 层运行 Dart 代码，主要对象包括 Widget、Element、RenderObject 与 Layer。Widget 是不可变的界面配置，Element 保存 Widget 在树中的实例与生命周期，RenderObject 负责布局和绘制，Layer 则组织可送往 engine 的合成结果。

- Build 根据状态更新 Element/Widget 配置；
- Layout 根据父节点约束计算 RenderObject 的尺寸和位置；
- Paint 把绘制操作记录为 DisplayList（可供 engine 重放的绘制指令列表），并组织 Layer tree；
- semantics（无障碍语义）、animation 和输入回调也会占用同一帧的 CPU 预算。

Widget rebuild 只表示相关 Widget 配置被重新计算，不等于整页 layout 或 repaint（重绘）。Element 更新后，只有相应 RenderObject 被标记为需要 layout/paint，后续阶段才会继续执行。判断“重建过多”时，应同时看 rebuild 数量、layout/paint 范围和帧耗时。

### Engine：把 DisplayList 变成 GPU 工作

Engine 用 C++ 实现，承接 Dart runtime（Dart 代码执行环境）、frame scheduling、DisplayList、Rasterizer、文本、图片与图形 backend。Rasterizer 消费 Layer tree/DisplayList，通过 Impeller 或 legacy renderer（旧渲染器）生成 GPU 命令，最终面向 Android render target（接收渲染结果的目标图像）提交 buffer。

Flutter 3.44.8 的 Impeller 目录把职责分成 compiler、renderer、backend、entity（可渲染实体）、display_list、typographer（文字排版与字形资源）和 shader_archive（预编译 shader 归档）等子系统。离线 shader compiler `impellerc` 在 engine 构建期处理 Impeller 自带 shader；运行时 renderer 仍要处理 pipeline（图形管线状态组合）、纹理、buffer、render pass（围绕一个渲染目标组织的一组 GPU 绘制）、同步和具体 GPU driver。

### Android Embedder：接入系统对象

Android embedding 负责：

- Activity/Fragment 与 `FlutterView` 生命周期；
- `SurfaceView`、`TextureView` 或 `ImageReader` render target；
- `Choreographer` VSync；
- 输入、IME（输入法）与无障碍交互；
- Platform Channel（Dart 与宿主平台之间的消息通道）、插件与 PlatformView；
- 把 engine 输出接到 Android `Surface`/`ANativeWindow`。

纯 Flutter Widget 不进入 Android View 的 measure/layout/draw。Android View hierarchy（原生 View 对象树）仍负责宿主窗口、`FlutterView` 容器、输入、系统栏与 PlatformView。

下面的简化链路用于确定责任边界：

```text
Android Choreographer
  → Flutter VsyncWaiter
  → Dart animation / build / layout / paint
  → Layer tree / DisplayList
  → Rasterizer
  → Impeller or legacy renderer
  → selected Android render target
  → BufferQueue / host HWUI
  → SurfaceFlinger
  → HWC or RenderEngine
  → display present
```

这条链只覆盖 Flutter root 的公共主干。external texture 与 PlatformView 会在中间或显示端加入额外 producer 和 layer。

## VSync 与线程模型

### Android 入口优先走 NDK `AChoreographer`

NDK 是 Android 提供给 C/C++ 代码的原生开发接口，`AChoreographer` 则是其中订阅显示 VSync 的 API。Flutter 3.44.8 的 `VsyncWaiterAndroid::AwaitVSync()` 先检查 `impeller::android::Choreographer::IsAvailableOnPlatform()`。可用时，它在 UI task runner（engine 的 UI 任务队列）上调用 NDK `AChoreographer_postFrameCallback64()` 或旧版回调；回调进入 `OnVsyncFromNDK()`，计算本帧起始时刻和目标显示时刻，再由 `FireCallback()` 交给 engine。

NDK 路径不可用时，engine 才把任务投到 platform task runner（平台任务队列），通过 Java `VsyncWaiter.asyncWaitForVsync()` 获取 `Choreographer` 回调，再经 `FlutterJNI.onVsync()` 和 native callback 返回 C++。这里的 JNI 是 Java 与 C/C++ 代码互相调用的接口。

trace 中出现 `PlatformVsync`、`VsyncProcessCallback` 或 Java `Choreographer#doFrame`，只能证明 Flutter 在订阅系统 VSync。纯 Flutter Widget 后面不会出现 Android ViewRoot 的 traversal（测量、布局、绘制等遍历流程）与 HWUI RenderThread 绘制。

### Flutter 3.32 stable 起默认合并 UI 与 Platform 线程

Flutter 官方材料对这个版本边界存在冲突：架构概览仍写 3.29，而 Flutter 团队维护的跟踪 issue #150525 在 2025-05-20 的更新中明确写明，Android 和 iOS 从 Flutter 3.32 stable 起默认合并 UI thread 与 platform thread。这里采用后者作为稳定版边界；3.29—3.31 包含实现进入主线和逐步启用的过程，分析这些版本时必须核对 engine revision 与启动参数，不能只看 SDK 版本号。

在合并模型中，独立 UI thread 被移除，Dart main isolate（Dart 应用主执行单元）在原生 platform thread 上运行。Flutter 3.44.8 的源码通过三处实现这一行为：

- `Settings::merged_platform_ui_thread` 默认取 `kEnabled`；
- Android `FlutterMain::Init()` 调用 `SettingsFromCommandLine(command_line, true)`，不再允许用启动参数关闭线程合并；
- `AndroidShellHolder` 仅在线程合并未启用时创建独立 UI thread，3.44.8 的默认 `ThreadHost` 只创建 Raster 与 IO 线程。

当前移动端主线可按三组执行者理解：

| 执行者 | 主要工作 | 常见风险 |
| --- | --- | --- |
| Platform + Dart UI | Android 回调、Platform Channel、插件、animation、build、layout、paint | 同步插件、Dart 计算、View/PlatformView 工作互相争用 |
| Raster | 重放 DisplayList、上传纹理、准备 pipeline、提交 GPU 工作 | 复杂效果、首次使用的资源、GPU/driver back-pressure（下游处理不及造成的反压） |
| IO | 图片与资源 I/O、解码、GPU resource context（资源上下文）相关工作 | 大图解码、磁盘 I/O、资源准备迟到 |

Flutter 3.31 及更早版本、部分过渡构建、定制 Embedder 或旧 trace 仍可能看到 Platform/UI/Raster/IO 分离形态。不要只凭 `1.ui`、`1.platform` 等线程名判断版本；线程名还会受到 Linux 16 字符限制和 engine 命名变化影响。

### 合并线程改变了卡顿归因

在合并模型中，以下几类工作会占用同一条 platform/Dart UI 时间线：

- Dart build/layout/paint；
- Android 生命周期和输入回调；
- 同步 Platform Channel/插件调用；
- PlatformView 的创建、布局和 View hierarchy 工作；
- 某些 FFI（Dart 直接调用 C 接口的 Foreign Function Interface）或主线程限定 API。

Platform 回调很长时，Dart frame 可能迟到；Dart 计算很长时，Android 回调也会等待。排查时要看 task 的调用来源和 Running/Runnable 状态：Running 表示线程正在 CPU 上执行，Runnable 表示线程可以运行、但仍在等待 CPU 调度。不能把整条线程统一归为“Dart 慢”。

## 与原生 Android HWUI 的边界

原生 View 页面的一般路径是：

```text
Choreographer
  → ViewRootImpl traversal
  → View measure / layout / draw
  → RenderNode / DisplayList
  → HWUI RenderThread
  → App Window buffer
```

Flutter 自绘 UI 的路径跳过 `ViewRootImpl.performTraversals()` 对 Widget tree 的绘制，也没有 App HWUI 的 RenderThread 分工。它由 Flutter framework 生成 DisplayList，再由 Flutter Raster thread 写入 root target。

两条路径仍共享 Android 显示后半段：

- engine 通过 `Surface`/`ANativeWindow` 连接 BufferQueue；
- SurfaceFlinger latch（取得并选定用于本轮合成的 buffer）可见 layer 的新 buffer；
- HWC（Hardware Composer，硬件合成器）尝试 DEVICE composition，即让显示硬件直接合成；必要时由 RenderEngine 做 CLIENT composition，即先由 GPU 合成 client target；
- dma-buf 负责在进程和设备之间共享 buffer，dma-fence 表示异步硬件工作完成与否，sync_file 则把 fence 封装成可跨进程传递的文件描述符。

PlatformView、`RenderMode.texture`、`RenderMode.image` 和宿主 Android UI 会重新引入 ViewRoot/HWUI，因此上述区别只适用于纯 Flutter root 主路径。

## Root RenderMode：surface、texture、image

Flutter 3.44.8 的 `RenderMode.java` 定义三种 root 输出。它描述 Flutter 主画面接到哪种 Android View，不描述 PlatformView 的合成策略。

### `RenderMode.surface`

`FlutterSurfaceView` 继承 `SurfaceView`，背后有独立 Surface。engine 直接面向这条 BufferQueue 生成 root buffer，GPU 完成状态通过 producer fence 传给 Consumer，SurfaceFlinger 通常看到独立的 child layer（隶属于宿主窗口层级的子图层）。

优点：

- 少一次回到宿主窗口的纹理采样；
- `RenderMode.java` 将其标为性能首选；
- 不透明的 `FlutterActivity` 默认返回 `RenderMode.surface`。

边界：

- 独立 layer 的 z-order（前后层级）、alpha（透明度）、生命周期和 transition（转场）需要协调；
- 不能像普通 View 内容一样任意夹在两个 Android View 之间做变换；
- Surface 创建、销毁或尺寸变化时，engine 必须切换输出 target。

### `RenderMode.texture`

`FlutterTextureView` 让 engine 先写入 `SurfaceTexture`。Android 17 `TextureView` 由宿主 HWUI 取得最新纹理图像，再采样进 host App Window buffer（宿主应用窗口的最终 buffer）。

这条路径至少包含两个节拍：

```text
Flutter Raster / GPU
  → SurfaceTexture producer buffer
  → onFrameAvailable / TextureView update
  → host ViewRoot traversal + HWUI draw
  → host App Window buffer
  → SurfaceFlinger
```

Flutter 中间图像 ready 后，宿主窗口还要及时发起 traversal、取得纹理、完成 HWUI draw 并提交 host buffer。透明背景的 `FlutterActivity` 默认使用 texture mode，因为它需要与其他 Android View 协调前后层级和变换。

### `RenderMode.image`

`FlutterImageView` 通过 `ImageReader` 接收 engine 输出，再把图像作为 Android View 内容画回宿主 Canvas。它主要用于切换渲染 Surface，以及处理 PlatformView 等特定交互场景。

分析时要检查：

- ImageReader 是否有新图像；
- acquire（取得图像）、fence wait 与 image release（释放图像）；
- `HardwareBuffer`/Bitmap 包装；
- 宿主 View draw 与 App Window buffer。

它不应被当作普通 Flutter 页面默认的高性能模式。

### 从 layer tree 识别三种模式

| RenderMode | 中间对象 | SurfaceFlinger 主要可见对象 | 常见等待 |
| --- | --- | --- | --- |
| surface | 独立 Surface buffer | Flutter root child layer | dequeue、GPU fence、SF latch |
| texture | SurfaceTexture image | host App Window | image acquire、host traversal/HWUI |
| image | ImageReader image | host App Window | image acquire/release、host draw |

只看进程名不够。还要检查 Android View hierarchy、SurfaceFlinger layer tree、buffer 尺寸和格式、frame number（队列中的帧序号）以及 fence。

## External texture 与 SurfaceProducer

相机、视频或原生渲染器可以通过 `TextureRegistry`（Flutter 管理外部纹理句柄的注册表）向 Flutter scene 提供 external texture。这里有两级 producer：

1. 插件侧 producer 把 GL 等原生内容写入 Android Surface；
2. Flutter Raster 采样最新 image，再生成 Flutter root buffer。

插件 buffer ready 不表示 Flutter 已经采样；Flutter root 已提交也不表示显示器已经 present（实际显示）。插件帧率、Flutter 帧率和 display 刷新率可以不同。

### 3.44.8 的 backing 选择

这里的 backing 是 `SurfaceProducer` 底层采用的具体实现；同一套插件接口可能由 `ImageReader` 或 `SurfaceTexture` 承担。

`FlutterRenderer.createSurfaceProducer()` 的稳定 tag 实现是：

- 未强制使用 GL texture；
- Android API 29+；
- 设备不命中 Flutter 记录的已知 `HardwareBuffer` 兼容性问题；
- 满足以上条件时创建 `ImageReaderSurfaceProducer`；
- 其他情况回退 `SurfaceTextureSurfaceProducer`。

`SurfaceProducer` 在 Flutter 3.24 稳定可用。插件应通过该抽象取得 Surface，不应假设 backing 永远是 `SurfaceTexture`。

### 生命周期与 fence

默认 `createSurfaceProducer()` 使用 `SurfaceLifecycle.manual`，表示插件自行管理 Surface 生命周期。显式选择 `resetInBackground` 时，ImageReader 路径会注册 trim-memory listener（系统内存回收通知监听器），在应用进入后台或系统清理内存时通过 `onSurfaceCleanup()` 通知插件，恢复时再调用 `onSurfaceAvailable()`。

`SurfaceTextureSurfaceProducer.setCallback()` 在 3.44.8 中为空，它不会收到相同的平台清理回调。插件必须按实际 backing 契约处理 Surface 重建，不能只验证其中一条路径。

`ImageReaderSurfaceProducer` 只在 Android API 33+ 使用 `Image.getFence()` 等待图像 fence；低版本没有同一套 Java fence API。`handlesCropAndRotation()` 在 ImageReader 路径返回 `false`，在 SurfaceTexture 路径返回 `true`；相机插件因此还要按 backing 处理传感器方向与裁剪差异。

## PlatformView：四类路径

PlatformView 用于嵌入 WebView、地图、广告或其他原生 Android View。Flutter Widget tree 与 Android View hierarchy 是两套对象树，合成策略决定原生 View 被转成 Flutter 可采样的纹理，还是保留 Android layer 身份。

### Texture Layer Hybrid Composition（TLHC）

TLHC 把 Android View 的绘制结果送入 Flutter 可采样 texture，再由 Flutter scene 合入 root target。

优势：

- Flutter 的 transform（变换）、clip（裁剪）和 opacity（透明度）更容易保持；
- 当前官方文档把 texture layer 列为默认路径；
- Flutter 与普通 Android View 的视觉组合较直接。

成本：

- 多一段 buffer/texture acquire（取得纹理图像）的处理；
- 快速滚动的 WebView 可能出现 jank；
- 包含 `SurfaceView` 的控件会遇到无障碍、文本放大镜或绘制重定向限制；
- invalidate（请求重绘）、输入与无障碍事件需要在两套对象树之间桥接。

`PlatformViewsController.createForTextureLayer()` 会先判断是否支持 texture layer；不满足条件时再回退到 Hybrid Composition 或 Virtual Display。

### 旧 Virtual Display

Virtual Display 把原生 View 放进虚拟显示，通过中转 Surface/texture 给 Flutter 使用。它可能增加 buffer、内存、输入与延迟成本。

旧插件、包含特殊 Surface 的 View，或触发 fallback（备用路径）的情况仍可能使用该方案。看到 `AndroidView` 时，应查创建 API、engine 版本和 layer tree，不能直接推断合成模式。

### Hybrid Composition（HC）

HC 让平台 View 按 Android View 的常规流程绘制，Flutter 内容和 overlay 通过 Android/SurfaceFlinger 与平台 View 组合。

它能较完整地保留原生 View 的行为、画面一致性、无障碍能力和 `SurfaceView` 支持。代价是 Flutter root、overlay、host window 与带独立 Surface 的 child 可能形成多条提交节拍。Flutter 官方文档仍提示 HC 会降低 Flutter FPS；分析时要看 platform/raster 调度、两套 View traversal、Surface transaction（图层属性与 buffer 的原子更新）以及 layer latch。

### Hybrid Composition++（HCPP）

HCPP 从 Flutter 3.44 起提供，目前仍是需要显式开启的实验能力（opt-in）。官方要求：

- Android API 34+；
- 使用 Vulkan 渲染；
- Impeller；
- 通过 manifest 或本地运行 flag（启动参数）显式开启。

发布版本可在 `<application>` 下使用下面的配置：

```xml
<meta-data
    android:name="io.flutter.embedding.android.EnableHcpp"
    android:value="true" />
```

这项配置只是在请求 HCPP；设备不满足条件时，Flutter 会回退到 App 原先配置的平台 View 策略。3.44.8 的 `PlatformViewAndroid` 先检查 flag、API 34+ 与 Impeller，`IsSurfaceControlEnabled()` 随后还要求实际 backend 是 `kImpellerVulkan`，并且 Vulkan context（Vulkan 设备、队列和资源的运行上下文）允许创建 SurfaceControl swapchain（面向 `SurfaceControl` 轮换提交的一组图像）。只看到 manifest、API level 或“Impeller 已启用”中的任一项，都不能证明运行时进入了 HCPP。

HCPP 使用 Android 14 起的 native transaction synchronization，让原生事务与 Flutter 帧更直接地同步，以减少旧 HC 的同步开销。页面仍可能包含多个 Surface/layer，复杂透明 overlay 也仍有已知限制。

Android 14、15、16 或 17 不会自动开启 HCPP。问题报告应记录 Flutter 版本、flag、API level、Vulkan/Impeller 状态与实际采用的 fallback 路径。

## Impeller 与 legacy renderer

### 默认范围

Flutter 3.27 起，Android API 29+ 默认启用 Impeller。官方网页把不满足条件的情况概括为回退到旧版 legacy OpenGL renderer；Flutter 3.44.8 的代码把这条规则拆得更细：

- `FlutterMain::SelectedRenderingAPI()` 在 Impeller 已启用、API 29+ 且设备不是采用 Vivante GPU 的已知例外机型时选择 `kImpellerAutoselect`，让 engine 在运行时选择后端；
- `AndroidContextDynamicImpeller` 先尝试 Vulkan。模拟器、部分 Huawei/MediaTek/已知问题 SoC、缺少必需 Vulkan extension/feature（扩展或硬件能力）或 Vulkan context 无效时，会改建 `AndroidContextGLImpeller`。此时渲染器仍是 Impeller，只是 backend 变为 OpenGL ES；
- API 低于 29、Vivante 设备或显式关闭 Impeller 时，非 slimpeller 构建才选择 `kSkiaOpenGLES`。slimpeller 是裁去 Skia 渲染路径的 engine 构建变体；software rendering（纯软件渲染）则是另一条独立路径。

“不支持 Vulkan 就一定退回 Skia”不适用于 3.44.8。排查时应同时记录 renderer 与 backend：`Impeller/Vulkan`、`Impeller/OpenGLES`、`Skia/OpenGLES` 代表三种不同状态。`--no-enable-impeller` 和 manifest opt-out 可用于当前版本诊断，engine 已提示未来会移除 Impeller opt-out。

renderer 由 App 携带的 Flutter engine 决定。Android 15、16 或 17 系统升级不会替旧 APK 切换 renderer。

### 离线 shader 解决什么

shader 是运行在 GPU 上的着色程序。这里的“离线”指在构建 engine 时预先编译 Flutter 自带 shader，而非等到 App 某一帧绘制时才临时编译。

Impeller 3.44.8 README 的目标包括：

- shader compilation 与 reflection（提取 shader 的资源和参数布局）在 engine build 期完成；
- pipeline state object（PSO，一组固定渲染管线状态）提前构建；
- cache（缓存）的创建和复用由 engine 显式控制；
- 资源有标签，便于工具分析；
- 单帧 workload（待执行的渲染工作）可以在需要时分给多个线程。

`impellerc` 处理 Impeller 自带的 GLSL 4.60 shader，生成 SPIR-V（Vulkan 可使用的中间指令格式）、后端 shader archive，以及供 C++ 代码访问资源布局的 reflection bindings。该编译器不随 App 运行时发布。

这能减少 legacy Skia/OpenGL 路径中常见的运行时 shader compilation jank，但不能消除首帧成本。以下工作仍可能迟到：

- Vulkan context 和驱动初始化；
- pipeline/cache miss（所需管线或缓存项尚未创建）与驱动机器码准备；
- 字体 atlas（把多个字形集中存放的纹理图集）、图片解码与上传；
- 大纹理、blur、`saveLayer` 和多个 render pass；
- external texture fence；
- GPU 队列、内存带宽与温控。

Flutter 3.44.8 的 `ShellSetupGPUSubsystem` 还明确把某些 Android Vulkan context 创建移出启动关键路径，因为它可能超过 100 ms。shader 离线编译不会消除所有 GPU 初始化工作。

### 怎样做 renderer A/B

这里的 A/B 是在其余条件相同的前提下，只更换 renderer 或 backend 的对照测试。

诊断时固定同一设备、build、页面数据、分辨率、刷新率和温度。先比较自动选择得到的 Impeller/Vulkan 与 Impeller/OpenGLES；需要隔离 renderer 差异时，再加入 Skia/OpenGLES opt-out：

1. 分开冷启动、首次进入和热路径；
2. 比较 platform/Dart、Raster、GPU completion 与 display deadline；
3. 检查画面正确性、内存、功耗与持续运行温度；
4. 记录实际 Vulkan/GLES backend 与 GPU driver；
5. 不使用跨设备百分比作为结论。

如果只有首次 Vulkan context 初始化改善，不能写成列表长期帧率提升；如果 Raster CPU 时间下降但 GPU fence 仍晚，还要继续检查像素处理量和内存带宽。

## 常见性能问题

### Widget rebuild 范围过大

先用 DevTools 的 rebuild/layout/paint 信息确认哪一阶段超时。常见修复包括：

- 把状态放到最小更新范围；
- 对稳定子树使用 `const`；
- 避免在构建阶段做同步 I/O、JSON 解析或大计算；
- 把大计算移到额外 isolate（独立 Dart 执行单元）前，评估消息复制与调度成本；
- 不为减少 rebuild 引入更昂贵的 layout 或 repaint。

rebuild 数量只是线索。一个很小但高频的 Widget rebuild 可能便宜，一个触发全屏 layout/paint 的单次更新可能更贵。

### 列表滚动卡顿

列表问题常混合多种成本：

- item build/layout 过重；
- intrinsic layout（为取得内容固有尺寸而增加的布局计算）或高度反复变化；
- 图片解码、缩放、上传和 cache miss；
- blur、clip、opacity、`saveLayer` 与大阴影；
- PlatformView、WebView 或地图；
- GC（垃圾回收）、Dart heap（Dart 对象堆）与 native/GPU 内存压力；
- 合并线程上的 Android 回调与插件竞争。

排查时固定列表数据与滚动手势，分别关闭图片、复杂效果、PlatformView 和业务计算。一次只改变一个变量，再比较 UI/Raster/GPU/display。

### Raster 或 GPU 慢

Raster thread 上的长 slice（trace 中的一段持续事件）不一定表示 GPU 正在执行；线程也可能在准备 DisplayList、上传资源、创建 pipeline、提交工作或等待下游解除 back-pressure。

证据上要分开：

- Raster CPU Running/Runnable；
- driver/pipeline 相关 slice；
- GPU submission（提交）与 completion（完成）；
- root producer fence；
- SurfaceFlinger latch 与 display present。

降低特效覆盖面积或 render target 像素数后，GPU completion 时间同步下降，才支持 fragment shader（逐像素着色）或带宽成为瓶颈的判断。只看到 Raster thread 忙，不能直接归因 GPU。

### Platform Channel 与 plugin

同步 Platform Channel、只能在主线程执行的插件代码、FFI 和 native callback 都可能占用合并后的 platform/Dart UI 线程。需要记录：

- 调用方向与 payload（消息携带的数据）；
- serialization/deserialization（序列化与反序列化）；
- Dart 与 Java/Kotlin/native 执行时间；
- task 是否处于 Runnable、但尚未得到 CPU 的状态；
- 是否等待 Surface、Binder IPC、锁或 I/O。

异步 API 只能释放调用方等待，不会自动减少总工作量。高频小消息还可能被调度和序列化成本放大。

## DevTools 与 Perfetto 怎样配合

### DevTools：区分 Framework 与 Raster

性能测试应使用 Profile 或 Release build：Profile 保留性能分析能力，Release 更接近正式发布配置。Debug build 使用 JIT（即时编译），还带有 assert、service protocol（调试工具通信协议）和额外工具插桩，会明显改变时序。

DevTools 适合回答：

- 哪一帧的 UI/Framework 或 Raster 时间超预算；
- 哪些 Dart 函数占 CPU；
- Widget rebuild、layout、paint 是否异常；
- 内存/GC、图片与 shader 事件是否相关。

DevTools 的“帧完成”不等于 panel 已显示。它不能单独解释 CPU 调度、GPU fence、SurfaceFlinger、HWC 与 present。

### Perfetto：补齐系统责任边界

Perfetto 用于把 Flutter 事件与 Android 调度、图形栈和硬件状态放到同一条系统时间线上。采集至少关注：

- process/thread scheduling、Running/Runnable；
- `PlatformVsync`、Flutter frame、Rasterizer/Impeller 事件；
- GPU render stages/counters（设备支持时）；
- BufferQueue、BLAST（SurfaceFlinger 用于批量提交 buffer 与图层事务的队列机制）、fence 和 FrameTimeline（Android 记录应用帧预期与实际显示时间的数据源）；
- SurfaceFlinger、RenderEngine、HWC；
- CPU/GPU frequency、thermal、memory 与 I/O。

线程名会变化，应优先根据事件、task runner、slice 调用关系和 Surface/layer 对象定位。`Rasterizer::DrawToSurfaces` 等 engine 事件也不能代替 GPU completion 证据。

### 自定义 trace event

Dart 可用 `dart:developer` 的 `Timeline.startSync()` / `finishSync()` 或 `TimelineTask` 标注业务阶段。标记应覆盖可验证的工作边界，例如“解析一页数据”“等待插件返回”“生成一批列表模型”。

事件名保持稳定，并附 request/frame id，才能与 native callback、buffer id 和 FrameTimeline 对齐。request/frame id 是把同一次业务请求和同一帧跨语言关联起来的标识。不要把整次交互包成一个大 slice，否则仍无法判断内部等待。

## 一套可复现的 Flutter 帧排查流程

### 1. 固定版本与配置

记录：

- Android build、API level、设备、GPU/driver；
- kernel 版本；
- Flutter SDK、engine revision、Dart SDK；
- Profile/Release、Impeller 与 Vulkan/GLES backend；
- root RenderMode；
- PlatformView API、HCPP flag 与 plugin 版本；
- 刷新率、分辨率、温度和页面数据。

### 2. 画出 View、Surface 与 layer 对象树

确认 root 是 `FlutterSurfaceView`、`FlutterTextureView` 还是 `FlutterImageView`；列出 external texture、PlatformView、overlay 与系统窗口。每个对象写清 Producer、Consumer、buffer 尺寸和格式，以及对应的 SurfaceFlinger layer。

### 3. 锁定 Flutter frame

从 DevTools 或 engine trace 选出一帧，记录 frame id 和：

- VSync callback；
- Dart animation/build/layout/paint；
- Raster begin/end；
- GPU submit/completion；
- root buffer queue；
- SF latch；
- display present。

### 4. 按现象补证据

| 现象 | 优先检查 | 直接证据 |
| --- | --- | --- |
| Platform/Dart 晚 | build、layout、paint、plugin、Runnable | Dart CPU、task slice、scheduler |
| Raster 晚 | display list、resource upload、pipeline、submit | Raster/Impeller、driver、GPU queue |
| Raster 已交付但 fence 晚 | GPU workload、frequency、bandwidth | GPU stage/counter、producer fence |
| external texture 不更新 | camera/codec/plugin producer、Surface lifecycle | texture id、queue、callback |
| texture root 已 ready，但 host 仍晚 | SurfaceTexture、ViewRoot、HWUI | host traversal、DrawFrame、host queue |
| PlatformView 错位 | 两套 traversal/transaction/latch | layer id、transaction、fence、present |

### 5. 做单变量 A/B

可控制的变量包括：

- Widget 更新范围；
- 图片 decode 尺寸；
- blur/saveLayer/opacity/clip；
- PlatformView 数量与策略；
- Impeller opt-out；
- root RenderMode；
- external texture 帧率与尺寸；
- 页面分辨率和刷新率。

比较 P50/P95/P99 frame time（分别有 50%、95%、99% 的帧不超过该耗时）、missed deadline（错过显示截止时间的次数）、input-to-present（从输入事件到画面显示的延迟）、内存、功耗和画面正确性。平均 FPS 会掩盖少量长帧。

## Fence、FrameTimeline 与最终显示

### 不同 root 有不同 fence 链

`surface` root 有独立 producer fence 与 layer release fence。`texture`/`image` root 先产生中间图像的 ready/release fence，再由宿主 HWUI 生成新的 App Window producer fence。PlatformView 与 overlay 还会加入各自的 buffer 与 transaction。

SurfaceFlinger 在 Android 17 FrontEnd 中处理 layer snapshot（某一时刻用于合成的图层状态快照）。CompositionEngine 与 HWC 协商 DEVICE/CLIENT composition；需要 CLIENT 时，RenderEngine 生成 client target。display present fence 表示整屏何时完成显示，per-layer release fence 表示某个图层的 buffer 何时可由生产者复用，二者都属于显示端反馈。

### FrameTimeline token 不一定一一对应

Flutter root Surface、host App Window 和独立 PlatformView layer 可能有不同 frame number/token。这里的 token 是 FrameTimeline 用来关联一帧预期显示时间和实际显示结果的标识；external texture 的中间帧也可能没有标准 App FrameTimeline token。

关联时使用多组标识：

- Flutter engine frame id；
- texture id；
- buffer id/frame number；
- SurfaceFlinger layer id；
- expected/actual present time（预期/实际显示时刻）；
- producer/acquire/release/present fence。

Dart frame end 只表示 framework/engine 的一个阶段结束，不能作为上屏时间。

### kernel 边界

`android17-6.18-2026-06_r6` 提供通用 dma-buf、dma-heap、dma-fence 与 sync_file 规则。dma-heap 是分配共享 buffer 的内核接口。内核源码可以解释 buffer 共享、引用和 fence 传递方式，却不能证明某台设备具体使用哪种 GPU scheduler（调度器）、allocator（内存分配器）、压缩方案或 fence tracepoint（可供 trace 采集的内核事件点）。

fence wait 表示某个依赖尚未完成。判断原因还要找到 fence owner（创建该 fence，并在工作结束后把它标记为完成的组件）、对应的 GPU/display submission、运行频率、queue depth（队列中尚未完成的工作数量）和 workload。

## 16 KB page size 与 Flutter plugin

Android 15 起支持 16 KB page-size（内存页大小）设备。Flutter App 中的 engine、AOT native library（Dart 提前编译生成的原生库）、FFI library 和含 `.so` 的插件都要同时满足：

- APK 中未压缩 `.so` 的 ZIP 对齐；
- ELF load segment（可执行文件的装载段）的 `p_align` 对齐要求；
- native 代码不能假定 `PAGE_SIZE == 4096`；
- `mmap`（内存映射）、shared memory 与自定义 allocator 按运行时 page size 工作。

工程检查可按下面执行：

- 使用支持 16 KB 打包对齐的 AGP（Android Gradle Plugin）；Android 官方建议 AGP 8.5.1+；
- 使用 NDK r28+ 让新构建的 shared library 默认适配 16 KB；
- 旧 NDK 明确配置 linker（链接器）的 page-size 选项，并用 ELF 工具复核；
- 检查所有预编译 plugin `.so` 与 `libc++_shared.so`；
- 在 16 KB emulator/真机运行启动、PlatformView、camera/video、FFI 和后台恢复测试。

`packagingOptions` 只能影响 APK 打包方式，不能修复 ELF `p_align` 或 native 代码中的 4 KB 常量。Android 17 平台锚点也不会替未重新编译的插件修复这些问题。

## Android 12—17 与 Flutter 版本边界

两条版本线需要分开记录：

| 平台/Flutter 版本 | 与 Flutter 渲染直接相关的变化 |
| --- | --- |
| Android 12 / API 31 | BLAST 与 FrameTimeline 形成现代显示分析基线；App 仍携带自己的 Flutter engine。 |
| Android 13 / API 33 | Image fence Java API 可供当前 ImageReader producer 路径使用；显示 HAL（硬件抽象层）接口转向 AIDL（Android 接口定义语言）。 |
| Android 14 / API 34 | 提供 HCPP 所需的 transaction synchronization 平台前提，但不会自动开启 HCPP。 |
| Android 15 / API 35 | 16 KB page-size 兼容成为 Flutter engine 和插件中原生库的约束。 |
| Android 16 / API 36 | AOSP 要求支持 64-bit ABI 且不属于 low-memory（低内存规格）的设备提供其硬件可支持的最高 Vulkan feature set（功能级别集合）；Android 16+ 出厂设备要求 Vulkan 1.4。旧 APK 的 Flutter renderer/thread 模型不会随 OS 更新。 |
| Android 17 / API 37 | 当前平台源码锚点；继续按 Surface、FrontEnd、CompositionEngine、AIDL Composer 与 kernel fence 分析。 |
| Flutter 3.24 | `SurfaceProducer` 稳定可用。 |
| Flutter 3.27 | Android API 29+ 默认启用 Impeller。 |
| Flutter 3.32 stable | Android/iOS 默认合并 UI 与 platform thread；3.29—3.31 的过渡构建按 engine revision 与参数确认。 |
| Flutter 3.38 | Android/iOS 移除关闭 UI/platform 线程合并的选项。 |
| Flutter 3.44 | HCPP 作为 API 34+、Vulkan/Impeller 条件下的实验性 opt-in 能力。 |
| Flutter 3.44.8 | Flutter 源码验证 tag。 |

运行在 Android 17 上的旧 Flutter App 仍可能使用旧线程模型、legacy renderer、Virtual Display 或旧插件。OS 版本不能替代 APK/engine 版本识别。

## 常见误判

| 误判 | 应怎样验证 |
| --- | --- |
| Flutter 固定有独立 UI、Platform、Raster 三线程 | 以 Flutter 3.32 stable 为默认合并边界；3.29—3.31 按 engine revision 与启动参数确认 |
| Flutter frame end 就是上屏 | 继续追 GPU fence、root/host queue、SF latch 与 present |
| `RenderMode.surface` 内容属于 host App Window | 查 `FlutterSurfaceView` child layer |
| `RenderMode.texture` 只有一个 BufferQueue | 分开 SurfaceTexture producer 与 host App Window |
| external texture ready 等于画面已更新 | 还要等待 Raster 采样、root 提交与 display present |
| `AndroidView` 固定使用 Hybrid Composition | 查 TLHC、VD、HC、HCPP 与 fallback |
| Android 14+ 自动使用 HCPP | 还需 Flutter 3.44+、opt-in、API 34+、Vulkan 和 Impeller |
| Android 15+ 自动切到 Impeller | renderer 由 APK 携带的 Flutter engine 决定 |
| Impeller 消除了所有首次卡顿 | 继续检查 context、pipeline、atlas、upload、driver 和 GPU |
| Raster thread 长就是 GPU 慢 | 分开 Raster CPU、submit、GPU completion 与 fence |

## 源码与官方资料

### Flutter 3.44.8

- [`VsyncWaiterAndroid`](https://github.com/flutter/flutter/blob/3.44.8/engine/src/flutter/shell/platform/android/vsync_waiter_android.cc)、[`Choreographer`](https://github.com/flutter/flutter/blob/3.44.8/engine/src/flutter/impeller/toolkit/android/choreographer.cc)、[Java `VsyncWaiter`](https://github.com/flutter/flutter/blob/3.44.8/engine/src/flutter/shell/platform/android/io/flutter/view/VsyncWaiter.java)：NDK 优先与 Java fallback。
- [`settings.h`](https://github.com/flutter/flutter/blob/3.44.8/engine/src/flutter/common/settings.h)、[`switches.cc`](https://github.com/flutter/flutter/blob/3.44.8/engine/src/flutter/shell/common/switches.cc)、[`flutter_main.cc`](https://github.com/flutter/flutter/blob/3.44.8/engine/src/flutter/shell/platform/android/flutter_main.cc)、[`android_shell_holder.cc`](https://github.com/flutter/flutter/blob/3.44.8/engine/src/flutter/shell/platform/android/android_shell_holder.cc)：3.44.8 的线程合并、renderer 选择与 Android API 29 边界。
- [`RenderMode.java`](https://github.com/flutter/flutter/blob/3.44.8/engine/src/flutter/shell/platform/android/io/flutter/embedding/android/RenderMode.java)、[`FlutterSurfaceView`](https://github.com/flutter/flutter/blob/3.44.8/engine/src/flutter/shell/platform/android/io/flutter/embedding/android/FlutterSurfaceView.java)、[`FlutterTextureView`](https://github.com/flutter/flutter/blob/3.44.8/engine/src/flutter/shell/platform/android/io/flutter/embedding/android/FlutterTextureView.java)、[`FlutterImageView`](https://github.com/flutter/flutter/blob/3.44.8/engine/src/flutter/shell/platform/android/io/flutter/embedding/android/FlutterImageView.java)：root target。
- [`FlutterRenderer.java`](https://github.com/flutter/flutter/blob/3.44.8/engine/src/flutter/shell/platform/android/io/flutter/embedding/engine/renderer/FlutterRenderer.java)、[`TextureRegistry.java`](https://github.com/flutter/flutter/blob/3.44.8/engine/src/flutter/shell/platform/android/io/flutter/view/TextureRegistry.java)、[`SurfaceTextureSurfaceProducer.java`](https://github.com/flutter/flutter/blob/3.44.8/engine/src/flutter/shell/platform/android/io/flutter/embedding/engine/renderer/SurfaceTextureSurfaceProducer.java)：external texture、backing、lifecycle 与 fence。
- [`PlatformViewsController.java`](https://github.com/flutter/flutter/blob/3.44.8/engine/src/flutter/shell/platform/android/io/flutter/plugin/platform/PlatformViewsController.java)、[`PlatformViewsController2.java`](https://github.com/flutter/flutter/blob/3.44.8/engine/src/flutter/shell/platform/android/io/flutter/plugin/platform/PlatformViewsController2.java)：TLHC、HC、VD 与 HCPP。
- [`android_context_dynamic_impeller.cc`](https://github.com/flutter/flutter/blob/3.44.8/engine/src/flutter/shell/platform/android/android_context_dynamic_impeller.cc)、[Impeller README](https://github.com/flutter/flutter/blob/3.44.8/engine/src/flutter/impeller/README.md)：Vulkan/OpenGLES 自动选择、离线 shader、pipeline、cache 与子系统边界。

### Android 17 与 kernel

- Android 17 [`SurfaceView.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/view/SurfaceView.java)、[`TextureView.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/view/TextureView.java)、[`ImageReader.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/media/java/android/media/ImageReader.java)：root/host target。
- Native [`BufferQueueProducer.cpp`](https://android.googlesource.com/platform/frameworks/native/+/android-17.0.0_r1/libs/gui/BufferQueueProducer.cpp)、[`Surface.cpp`](https://android.googlesource.com/platform/frameworks/native/+/android-17.0.0_r1/libs/gui/Surface.cpp)、[`SurfaceFlinger.cpp`](https://android.googlesource.com/platform/frameworks/native/+/android-17.0.0_r1/services/surfaceflinger/SurfaceFlinger.cpp)：buffer 提交与显示。
- Kernel [`dma-buf.c`](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/drivers/dma-buf/dma-buf.c)、[`dma-fence.c`](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/drivers/dma-buf/dma-fence.c)、[`sync_file.c`](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/drivers/dma-buf/sync_file.c)：共享 buffer 与 fence。

### 官方文档

- [Flutter architectural overview](https://docs.flutter.dev/resources/architectural-overview)
- [Flutter thread merge tracking issue #150525](https://github.com/flutter/flutter/issues/150525)
- [Flutter 3.38 release notes](https://docs.flutter.dev/release/release-notes/release-notes-3.38.0)
- [Impeller rendering engine](https://docs.flutter.dev/perf/impeller)
- [Android Platform Views and HCPP](https://docs.flutter.dev/platform-integration/android/platform-views)
- [SurfaceProducer migration](https://docs.flutter.dev/release/breaking-changes/android-surface-plugins)
- [Flutter rendering performance](https://docs.flutter.dev/perf/rendering-performance)
- [Flutter performance best practices](https://docs.flutter.dev/perf/best-practices)
- [Flutter DevTools Performance view](https://docs.flutter.dev/tools/devtools/performance)
- [Android 16 KB page-size support](https://developer.android.com/guide/practices/page-sizes)
- [AOSP Vulkan implementation requirements](https://source.android.com/docs/core/graphics/implement-vulkan)
- [Perfetto FrameTimeline](https://perfetto.dev/docs/data-sources/frametimeline)
