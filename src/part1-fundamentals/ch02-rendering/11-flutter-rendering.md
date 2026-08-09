---
title: 2.11 Flutter 渲染管线与性能
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
last_task2b_at: "2026-07-01T18:54:04+08:00"
last_task9_audit: 2026-07-05
last_task9_audit_log: logs/deep-review/2026-07-05-10-audit.md
last_task6_audit: 2026-06-13
task9_state: reviewed
task9_result: pass-tech-review
task2b_state: fixed
task9_reviewed_date: 2026-07-02
task9_reviewed_by: openclaw-task9
last_task9_at: "2026-07-02T10:41:17+08:00"
last_task9_review_log: logs/deep-review/2026-07-02-10-deep-review.md
task9_review_notes: "2026-05-22 Task9 deep review: pass-tech-review。无 P0/P1/P2；16KB plugin 合规链路已拆清 AGP zip alignment、ELF p_align 与 native 4KB 假设。queue 无 pending，Task6 已通过，自动晋升 finalized。 | 2026-07-02 Task9 deep-review AUTO-FIX: P0 0 / P1 1 / P2 0；修正 Flutter Android VSync 入口为 NDK AChoreographer 优先、Java VsyncWaiter fallback，并同步 Perfetto trace 关键词；回到 Task6 复审。详见 logs/deep-review/2026-07-02-10-deep-review.md。"
reviewed_date: 2026-07-02
reviewed_by: openclaw-task6
task6_state: reviewed
task6_result: pass-light-edit
last_task6_at: 2026-07-02T20:11:00+08:00
last_task6_review_log: logs/review/2026-05-22-16-review.md
review_notes: "2026-05-09 task6 re-review (revisiting): pass-light-edit。L1 禁用词 4 处已修复。无 B 类大问题。评分：结构 5/5·措辞 4/5·一致性 5/5·验证 4/5·元数据 5/5。2026-05-22 Task6 re-review: L1/L2 pass-light-edit，修复 frontmatter 重复 key、结构性元叙述与口语化表达 7 处；Task9 P1/P2 queue 已存在，保持 task2b_pending。2026-05-22 Task6 re-review: pass-light-edit。L1/L2 小修 14 处（结构性元叙述、ASCII 破折号、标点与几处过度口语表达）。Task9 P1/P2 queue 已存在，保持 task2b_pending。 2026-05-22 16:06 Task6 re-review: pass-light-edit。L1/L2 小修 5 处；压掉不必要的“我们”第一人称和开头问题句式；既有 Task9 P1（16KB plugin packaging/ELF/runtime 边界）queue 保留，保持 task2b_pending。 2026-05-22 19:26 Task9 re-review: pass-tech-review，P0/P1/P2=0；queue 无 pending，自动晋升 finalized。"
updated_by: openclaw-task9
updated_date: 2026-07-02
p0: 0
p1: 1
p2: 0
auto_promoted: True
deepseek_cn_review_state: done
last_deepseek_cn_review_at: 2026-07-03
task2b_fix_source: task9-deep-tech-review
task2b_fix_summary: "Flutter merged UI+Platform 线程模型版本边界从 3.29+→3.32 stable+，旧模型边界从 3.28-→3.31-，与 2.11/18.12 交叉引用闭环（依据 Flutter issue #150525 + release-notes-3.32.0）"
last_task9_autofix_at: "2026-07-02"
---
# 2.11 Flutter 渲染管线与性能

Flutter 页面进入 Perfetto 后，不能只找一条“Flutter UI 线程”。页面最终怎样显示，由三组配置共同决定：

- Flutter 根视图使用 `surface`、`texture` 还是 `image` 渲染模式；
- 相机、视频或原生渲染器是否通过外部纹理提供内容；
- PlatformView 使用 TLHC、Hybrid Composition、旧 Virtual Display 还是 HCPP。

同一页面可以同时存在 Flutter 根 Surface、相机输入、原生地图 View、Flutter 叠加层和系统窗口。每个对象都有自己的生产者、缓冲、栅栏与节拍。

分析固定两条版本线：

- Android 平台：Android 17 / API 37 / `android-17.0.0_r1`；
- 内核：`android17-6.18-2026-06_r6`；
- Flutter：用稳定标签 `3.44.8`、框架提交 `058e0af2c2b57e369d905a03ac9748b0ebf543c6`、引擎版本 `0cd610717bde95fd88343c64f81c11ba4e5c0010` 验证当前实现。

Android 决定 Surface、BufferQueue、SurfaceFlinger、HWC 与内核同步语义。Flutter 框架、引擎、Android 嵌入层和插件随应用发布；分析线上问题时，仍要回到 APK 实际携带的 Flutter SDK、引擎版本、渲染器/后端与插件版本。

## 三层架构与一帧的公共前半段

### Framework：生成绘制意图

Framework 层运行 Dart 代码，主要对象包括 Widget、Element、RenderObject 与 Layer。

- 构建阶段根据状态更新 Element/Widget 配置；
- 布局阶段计算 RenderObject 的约束、尺寸和位置；
- 绘制阶段把绘制操作记录为 DisplayList，并组织图层树；
- 语义、动画和输入回调也会占用同一帧的 CPU 预算。

Widget 重建不等于整页布局或重绘。Element 更新后，只有相应 RenderObject 被标记为需要布局/绘制，后续阶段才会继续执行。判断“重建过多”时，应同时看重建数量、布局/绘制范围和帧耗时。

### Engine：把 DisplayList 变成 GPU 工作

Engine 用 C++ 实现，承接 Dart 运行时、帧调度、DisplayList、光栅器、文本、图片与图形后端。Rasterizer 消费图层树/DisplayList，通过 Impeller 或旧版渲染器创建 GPU 命令，最终面向 Android 渲染目标提交缓冲。

Flutter 3.44.8 的 Impeller 目录把职责分成编译器、渲染器、后端、实体、显示列表、排版和着色器归档等子系统。离线着色器编译器 `impellerc` 在引擎构建期处理 Impeller 自带着色器；运行时渲染器仍要处理管线、纹理、缓冲、渲染轮次、同步和具体 GPU 驱动。

### Android 嵌入层：接入系统对象

Android 嵌入层负责：

- Activity/Fragment 与 `FlutterView` 生命周期；
- `SurfaceView`、`TextureView` 或 `ImageReader` 渲染目标；
- `Choreographer` VSync；
- 输入、IME、无障碍与系统 UI；
- Platform Channel、插件与 PlatformView；
- 把引擎输出接到 Android `Surface`/`ANativeWindow`。

纯 Flutter Widget 不进入 Android View 的测量、布局与绘制。Android View 层级仍负责宿主窗口、`FlutterView` 容器、输入、系统栏与 PlatformView。

下面的简化链路用于确定责任边界：

```text
Android Choreographer
  → Flutter VsyncWaiter
  → Dart 动画 / 构建 / 布局 / 绘制
  → 图层树 / DisplayList
  → Rasterizer
  → Impeller 或旧版渲染器
  → 选定的 Android 渲染目标
  → BufferQueue / 宿主 HWUI
  → SurfaceFlinger
  → HWC 或 RenderEngine
  → 显示提交
```

这条链只覆盖 Flutter 根视图的公共主干。外部纹理与 PlatformView 会在中间或显示端加入额外生产者和图层。

## VSync 与线程模型

### Android 入口优先走 NDK AChoreographer

Flutter 3.44.8 的 `VsyncWaiterAndroid::AwaitVSync()` 先检查 `impeller::android::Choreographer::IsAvailableOnPlatform()`。可用时，它在 UI 任务运行器上调用 NDK `AChoreographer_postFrameCallback64()` 或旧回调；回调进入 `OnVsyncFromNDK()`，计算帧起点与目标时间，再由 `FireCallback()` 交给引擎。

NDK 路径不可用时，引擎才把任务投到平台任务运行器，通过 Java `VsyncWaiter.asyncWaitForVsync()` 获取 `Choreographer` 回调，再经 `FlutterJNI.onVsync()`/原生回调返回 C++。

跟踪数据中出现 `PlatformVsync`、`VsyncProcessCallback` 或 Java `Choreographer#doFrame`，只能证明 Flutter 在订阅系统 VSync。纯 Flutter Widget 后面不会出现 Android ViewRoot 的遍历与 HWUI RenderThread 绘制。

### Flutter 3.32 stable 起默认合并 UI 与 Platform 线程

Flutter 官方材料对这个版本边界存在冲突：架构概览仍写 3.29，而 Flutter 团队维护的跟踪问题 #150525 在 2025-05-20 的更新中明确写明，Android 和 iOS 从 Flutter 3.32 稳定版起默认合并 UI 线程与平台线程。这里采用后者作为稳定版边界；3.29—3.31 包含实现进入主线和逐步启用的过程，分析这些版本时必须核对引擎版本与启动参数，不能只看 SDK 版本号。

在合并模型中，独立 UI 线程被移除，Dart 主 isolate 在原生平台线程上运行。Flutter 3.44.8 的源码通过三处实现这一行为：

- `Settings::merged_platform_ui_thread` 默认取 `kEnabled`；
- Android `FlutterMain::Init()` 调用 `SettingsFromCommandLine(command_line, true)`，不再允许用启动参数关闭线程合并；
- `AndroidShellHolder` 仅在线程合并未启用时创建独立 UI 线程，3.44.8 的默认 `ThreadHost` 只创建 Raster 与 IO 线程。

当前移动端主线可按三组执行者理解：

| 执行者 | 主要工作 | 常见风险 |
| --- | --- | --- |
| Platform + Dart UI | Android 回调、Platform Channel、插件、动画、构建、布局、绘制 | 同步插件、Dart 计算、View/PlatformView 工作互相争用 |
| Raster | DisplayList 光栅化、纹理上传、管线、GPU 提交 | 复杂效果、首次资源、GPU/驱动背压 |
| IO | 图片与资源 I/O、解码、GPU 资源上下文相关工作 | 大图解码、磁盘 I/O、资源准备迟到 |

Flutter 3.31 及更早版本、部分过渡构建、定制 Embedder 或旧跟踪数据仍可能看到 Platform/UI/Raster/IO 分离形态。不要只凭 `1.ui`、`1.platform` 等线程名判断版本；线程名还会受到 Linux 16 字符限制和引擎命名变化影响。

### 合并线程改变了卡顿归因

在合并模型中，以下几类工作会占用同一条平台/Dart UI 时间线：

- Dart 构建/布局/绘制；
- Android 生命周期和输入回调；
- 同步 Platform Channel/插件调用；
- PlatformView 的创建、布局和 View hierarchy 工作；
- 某些 FFI 或主线程限定 API。

平台回调很长时，Dart 帧可能迟到；Dart 计算很长时，Android 回调也会等待。排查时要看任务的调用来源和运行/可运行状态，不能把整条线程统一归为“Dart 慢”。

## 与原生 Android HWUI 的边界

原生 View 页面的一般路径是：

```text
Choreographer
  → ViewRootImpl traversal
  → View measure / layout / draw
  → RenderNode / DisplayList
  → HWUI RenderThread
  → 应用窗口缓冲
```

Flutter 自绘 UI 的路径跳过 `ViewRootImpl.performTraversals()` 对 Widget 树的绘制，也没有应用 HWUI 的 RenderThread 分工。它由 Flutter 框架生成 DisplayList，再由 Flutter Raster 线程生产根目标。

两条路径仍共享 Android 显示后半段：

- 引擎通过 `Surface`/`ANativeWindow` 连接 BufferQueue；
- SurfaceFlinger 锁存可见图层；
- HWC 尝试 DEVICE 合成，必要时由 RenderEngine 做 CLIENT 合成；
- dma-buf 与 dma-fence/sync_file 负责跨进程、跨设备共享与同步。

PlatformView、`RenderMode.texture`、`RenderMode.image` 和宿主 Android UI 会重新引入 ViewRoot/HWUI，因此上述区别只适用于纯 Flutter 根视图主路径。

## 根视图 RenderMode：surface、texture、image

Flutter 3.44.8 的 `RenderMode.java` 定义三种根视图输出。它描述 Flutter 主画面接到哪种 Android View，不描述 PlatformView 的合成策略。

### `RenderMode.surface`

`FlutterSurfaceView` 继承 `SurfaceView`，背后有独立 Surface。引擎直接面向这条 BufferQueue 生产根缓冲，GPU 完成状态通过生产者栅栏传给消费者，SurfaceFlinger 通常看到独立的子图层。

优点：

- 少一次回到宿主窗口的纹理采样；
- `RenderMode.java` 将其标为性能首选；
- 不透明 `FlutterActivity` 默认返回 `RenderMode.surface`。

边界：

- 独立图层的 Z 序、透明度、生命周期和过渡需要协调；
- 不能像普通 View 内容一样任意夹在两个 Android View 之间做变换；
- Surface 创建、销毁或尺寸变化时，引擎必须切换输出目标。

### `RenderMode.texture`

`FlutterTextureView` 让引擎先写入 `SurfaceTexture`。Android 17 `TextureView` 由宿主 HWUI 取得最新纹理图像，再采样进宿主应用窗口缓冲。

这条路径至少包含两个节拍：

```text
Flutter Raster / GPU
  → SurfaceTexture 生产者缓冲
  → onFrameAvailable / TextureView 更新
  → 宿主 ViewRoot 遍历 + HWUI 绘制
  → 宿主应用窗口缓冲
  → SurfaceFlinger
```

Flutter 中间图像就绪后，宿主窗口还要及时发起遍历、取得纹理、完成 HWUI 绘制并提交宿主缓冲。透明背景的 `FlutterActivity` 默认使用 texture 模式，因为它需要与其他 Android View 做 Z 序与变换。

### `RenderMode.image`

`FlutterImageView` 通过 `ImageReader` 接收引擎输出，再把图像作为 Android View 内容画回宿主 Canvas。它主要服务渲染 Surface 切换和 PlatformView 等特定交互场景。

分析时要检查：

- ImageReader 是否有新图像；
- 获取、栅栏等待与图像释放；
- `HardwareBuffer`/Bitmap 包装；
- 宿主 View 绘制与应用窗口缓冲。

它不应被当作普通 Flutter 页面默认的高性能模式。

### 从图层树识别三种模式

| RenderMode | 中间对象 | SurfaceFlinger 主要可见对象 | 常见等待 |
| --- | --- | --- | --- |
| surface | 独立 Surface 缓冲 | Flutter 根视图子图层 | 出队、GPU 栅栏、SF 锁存 |
| texture | SurfaceTexture 图像 | 宿主应用窗口 | 图像获取、宿主遍历/HWUI |
| image | ImageReader 图像 | 宿主应用窗口 | 图像获取/释放、宿主绘制 |

只看进程名不够。需要同时检查 Android View 层级、SurfaceFlinger 图层树、缓冲大小/格式、帧号和栅栏。

## External texture 与 SurfaceProducer

相机、视频或原生渲染器可以通过 `TextureRegistry` 向 Flutter 场景提供外部纹理。这里有两级生产者：

1. 插件生产者把相机、编解码器或 GL 内容写入 Android Surface；
2. Flutter Raster 采样最新图像，再生成 Flutter 根缓冲。

插件缓冲就绪不表示 Flutter 已采样；Flutter 根视图提交也不表示显示已经呈现。插件帧率、Flutter 帧率和显示刷新率可以不同。

### 3.44.8 的底层载体选择

`FlutterRenderer.createSurfaceProducer()` 的稳定标签实现是：

- 未强制使用 GL 纹理；
- Android API 29+；
- 设备不命中已知 `HardwareBuffer` 缺陷；
- 满足以上条件时创建 `ImageReaderSurfaceProducer`；
- 其他情况回退 `SurfaceTextureSurfaceProducer`。

`SurfaceProducer` 在 Flutter 3.24 稳定可用。插件应使用该抽象取得 Surface，不应假设底层载体永远是 `SurfaceTexture`。

### 生命周期与栅栏

默认 `createSurfaceProducer()` 使用 `SurfaceLifecycle.manual`。显式选择 `resetInBackground` 时，ImageReader 路径会注册内存整理监听器，在后台或内存压力清理时通过 `onSurfaceCleanup()` 通知插件，恢复时再调用 `onSurfaceAvailable()`。

`SurfaceTextureSurfaceProducer.setCallback()` 在 3.44.8 中为空，它不会收到相同的平台清理回调。插件必须按实际底层载体契约处理 Surface 重建，不能只验证其中一条路径。

`ImageReaderSurfaceProducer` 只在 Android API 33+ 使用 `Image.getFence()` 等待图像栅栏；低版本没有同一套 Java 栅栏 API。`handlesCropAndRotation()` 在 ImageReader 路径返回 `false`，SurfaceTexture 路径返回 `true`，相机插件还要处理传感器方向与裁剪差异。

## PlatformView：四类路径

PlatformView 用于嵌入 WebView、地图、广告或其他原生 Android View。Flutter Widget 树与 Android View 层级是两套对象树，合成策略决定原生 View 被转成纹理，还是保留为 Android 图层。

### Texture Layer Hybrid Composition（TLHC）

TLHC 把 Android View 的绘制结果送入 Flutter 可采样纹理，再由 Flutter 场景合入根目标。

优势：

- Flutter 变换、裁剪和透明度更容易保持；
- 当前官方文档把纹理层列为默认路径；
- Flutter 与普通 Android View 的视觉组合较直接。

成本：

- 多一段缓冲/纹理获取；
- 快速滚动的 WebView 可能出现卡顿；
- 包含 `SurfaceView` 的控件会遇到无障碍、文本放大镜或重定向限制；
- 失效、输入与无障碍需要桥接。

`PlatformViewsController.createForTextureLayer()` 会先判断是否支持纹理层；不满足时再回退 Hybrid Composition 或 Virtual Display。

### 旧 Virtual Display

Virtual Display 把原生 View 放进虚拟显示，通过中转 Surface/纹理给 Flutter 使用。它可能增加缓冲、内存、输入与延迟成本。

旧插件、包含特殊 Surface 的 View 或回退条件仍可能使用该路径。看到 `AndroidView` 时，应查创建 API、引擎版本和图层树，不能直接推断合成模式。

### Hybrid Composition（HC）

HC 让平台 View 按 Android View 正常绘制，Flutter 内容和叠加层通过 Android/SurfaceFlinger 与平台 View 组合。

优点是原生保真度、无障碍与 `SurfaceView` 支持较完整。代价是 Flutter 根视图、叠加层、宿主窗口和 Surface 子视图可能形成多条提交节拍。Flutter 官方文档仍提示 HC 会降低 Flutter FPS；分析时要看平台/Raster 调度、两套 View 遍历、事务与图层锁存。

### Hybrid Composition++（HCPP）

HCPP 从 Flutter 3.44 起提供，当前仍为实验性选择启用功能。官方要求：

- Android API 34+；
- Vulkan 渲染；
- Impeller；
- 清单或本地运行标志显式开启。

发布版本可在 `<application>` 下使用下面的配置：

```xml
<meta-data
    android:name="io.flutter.embedding.android.EnableHcpp"
    android:value="true" />
```

这项配置只是在请求 HCPP；设备不满足条件时，Flutter 会回退到应用原先配置的平台 View 策略。3.44.8 的 `PlatformViewAndroid` 先检查标志、API 34+ 与 Impeller，`IsSurfaceControlEnabled()` 随后还要求实际后端是 `kImpellerVulkan`，并且 Vulkan 上下文允许 SurfaceControl 交换链。只看到清单、API 级别或“Impeller 已启用”中的任一项，都不能证明运行时进入了 HCPP。

HCPP 使用 Android 14 起的原生事务同步改善旧 HC 的同步开销，但仍可能存在多个 Surface/图层，也有复杂透明叠加层的已知限制。

Android 14、15、16 或 17 不会自动开启 HCPP。问题报告应记录 Flutter 版本、标志、API 级别、Vulkan/Impeller 状态与实际回退路径。

## Impeller 与旧版渲染器

### 默认范围

Flutter 3.27 起，Android API 29+ 默认启用 Impeller。官方网页把不满足条件的情况概括为回退到旧版 OpenGL 渲染器；Flutter 3.44.8 的代码把这条规则拆得更细：

- `FlutterMain::SelectedRenderingAPI()` 在 Impeller 已启用、API 29+ 且设备不是 Vivante 时选择 `kImpellerAutoselect`；
- `AndroidContextDynamicImpeller` 先尝试 Vulkan。模拟器、部分 Huawei/MediaTek/已知问题 SoC、缺少必需 Vulkan 扩展/功能或 Vulkan 上下文无效，会改建 `AndroidContextGLImpeller`，此时仍是 Impeller，只是后端变为 OpenGL ES；
- API 低于 29、Vivante 设备或显式关闭 Impeller 时，非 slimpeller 构建才选择 `kSkiaOpenGLES`；软件渲染是另一条独立路径。

“不支持 Vulkan 就一定退回 Skia”不适用于 3.44.8。排查时应同时记录渲染器与后端：`Impeller/Vulkan`、`Impeller/OpenGLES`、`Skia/OpenGLES` 代表三种不同状态。`--no-enable-impeller` 和清单退出选项可用于当前版本诊断，引擎已提示未来会移除 Impeller 退出选项。

渲染器由应用携带的 Flutter 引擎决定。Android 15、16 或 17 系统升级不会替旧 APK 切换渲染器。

### 离线着色器编译解决什么

Impeller 3.44.8 README 的目标包括：

- 着色器编译与反射在引擎构建期完成；
- 管线状态对象提前构建；
- 缓存由引擎显式控制；
- 资源有标签，便于工具分析；
- 单帧负载可以在需要时分给多个线程。

`impellerc` 处理 Impeller 自带的 GLSL 4.60 着色器，生成 SPIR-V、后端着色器归档与 C++ 反射绑定。编译器不随应用运行时发布。

这能减少旧版 Skia/OpenGL 路径中常见的运行时着色器编译卡顿，但不能消除首帧成本。以下工作仍可能迟到：

- Vulkan 上下文和驱动初始化；
- 管线/缓存未命中与驱动机器码准备；
- 字形图集、图片解码/上传；
- 大纹理、模糊、saveLayer 和多轮渲染；
- 外部纹理栅栏；
- GPU 队列、内存带宽与温控。

Flutter 3.44.8 的 `ShellSetupGPUSubsystem` 还明确把某些 Android Vulkan 上下文创建移出启动关键路径，因为它可能超过 100 ms。着色器离线编译不会消除所有 GPU 初始化工作。

### 怎样做渲染器 A/B

诊断时固定同一设备、构建版本、页面数据、分辨率、刷新率和温度。先比较自动选择得到的 Impeller/Vulkan 与 Impeller/OpenGLES；需要隔离渲染器差异时，再加入 Skia/OpenGLES 退出选项：

1. 分开冷启动、首次进入和热路径；
2. 比较平台/Dart、Raster、GPU 完成与显示截止时间；
3. 检查画面正确性、内存、功耗与持续运行温度；
4. 记录实际 Vulkan/GLES 后端与 GPU 驱动；
5. 不使用跨设备百分比作为结论。

如果只有首次 Vulkan 上下文初始化改善，不能写成列表长期帧率提升；如果 Raster CPU 下降但 GPU 栅栏仍晚，还要继续查像素和带宽。

## 常见性能问题

### Widget 重建范围过大

先用 DevTools 的重建、布局和绘制信息确认哪一阶段超时。常见修复包括：

- 把状态放到最小更新范围；
- 对稳定子树使用 `const`；
- 避免在构建阶段做同步 I/O、JSON 解析或大计算；
- 大计算移到 isolate 前，评估消息复制与调度成本；
- 不为减少重建引入更昂贵的布局或重绘。

重建数量只是线索。一个很小但高频的 Widget 重建可能便宜，一个触发全屏布局/绘制的单次更新可能更贵。

### 列表滚动卡顿

列表问题常混合多种成本：

- 列表项构建/布局过重；
- 固有尺寸布局或高度反复变化；
- 图片解码、缩放、上传和缓存未命中；
- 模糊、裁剪、透明度、`saveLayer` 与大阴影；
- PlatformView、WebView 或地图；
- GC、Dart 堆与原生/GPU 内存压力；
- 合并线程上的 Android 回调/插件竞争。

排查时固定列表数据与滚动手势，分别关闭图片、复杂效果、PlatformView 和业务计算。一次只改变一个变量，再比较 UI/Raster/GPU/显示端。

### Raster 或 GPU 慢

Raster 线程的长切片不一定表示 GPU 正在执行；它可能在准备显示列表、上传资源、创建管线、提交或等待背压。

证据上要分开：

- Raster CPU 运行/可运行状态；
- 驱动/管线相关切片；
- GPU 提交与完成；
- 根视图生产者栅栏；
- SurfaceFlinger 锁存与显示提交。

降低效果面积或渲染目标像素后 GPU 完成时间同步下降，才支持片元/带宽方向。只看到 Raster 线程忙，不能直接归因 GPU。

### Platform Channel 与插件

同步 Platform Channel、主线程限定插件、FFI 和原生回调都可能占用合并后的平台/Dart UI 线程。需要记录：

- 调用方向与载荷；
- 序列化/反序列化；
- Dart 与 Java/Kotlin/原生执行时间；
- 任务是否处于可运行但未调度状态；
- 是否等待 Surface、binder、锁或 I/O。

异步 API 只能释放调用方等待，不会自动减少总工作量。高频小消息还可能被调度和序列化成本放大。

## DevTools 与 Perfetto 怎样配合

### DevTools：区分 Framework 与 Raster

性能测试应使用 Profile 或 Release 构建。Debug/JIT、断言、服务协议与工具插桩会改变时序。

DevTools 适合回答：

- 哪一帧的 UI/Framework 或 Raster 时间超预算；
- 哪些 Dart 函数占 CPU；
- Widget 重建、布局、绘制是否异常；
- 内存/GC、图片与着色器事件是否相关。

DevTools 的“帧完成”不等于面板已显示。它不能单独解释 CPU 调度、GPU 栅栏、SurfaceFlinger、HWC 与显示提交。

### Perfetto：补齐系统责任边界

Perfetto 采集至少关注：

- 进程/线程调度、运行/可运行状态；
- `PlatformVsync`、Flutter 帧、Rasterizer/Impeller 事件；
- GPU 渲染阶段/计数器（设备支持时）；
- BufferQueue、BLAST、栅栏和 FrameTimeline；
- SurfaceFlinger、RenderEngine、HWC；
- CPU/GPU 频率、温控、内存与 I/O。

线程名会变化，优先从事件、任务运行器、切片调用关系和 Surface/图层对象定位。`Rasterizer::DrawToSurfaces` 等引擎事件也不能替代 GPU 完成事件。

### 自定义跟踪事件

Dart 可用 `dart:developer` 的 `Timeline.startSync()` / `finishSync()` 或 `TimelineTask` 标注业务阶段。标记应覆盖可验证的工作边界，例如“解析一页数据”“等待插件返回”“生成一批列表模型”。

事件名保持稳定，并附请求/帧 ID，才能与原生回调、缓冲 ID 和 FrameTimeline 对齐。不要把整次交互包成一个大切片，否则仍无法判断内部等待。

## 一套可复现的 Flutter 帧排查流程

### 1. 固定双版本与配置

记录：

- Android 构建、API 级别、设备、GPU/驱动；
- Flutter SDK、引擎版本、Dart SDK；
- Profile/Release、Impeller 与 Vulkan/GLES 后端；
- 根视图 RenderMode；
- PlatformView API、HCPP 标志与插件版本；
- 刷新率、分辨率、温度和页面数据。

### 2. 画出 View、Surface 与图层对象树

确认根视图是 `FlutterSurfaceView`、`FlutterTextureView` 还是 `FlutterImageView`；列出外部纹理、PlatformView、叠加层与系统窗口。每个对象写清生产者、消费者、缓冲大小/格式和 SurfaceFlinger 图层。

### 3. 锁定 Flutter 帧

从 DevTools 或引擎跟踪数据选出一帧，记录帧 ID 和：

- VSync 回调；
- Dart 动画/构建/布局/绘制；
- Raster 开始/结束；
- GPU 提交/完成；
- 根缓冲入队；
- SF 锁存；
- 显示提交。

### 4. 按现象补证据

| 现象 | 优先检查 | 直接证据 |
| --- | --- | --- |
| Platform/Dart 晚 | 构建、布局、绘制、插件、可运行状态 | Dart CPU、任务切片、调度器 |
| Raster 晚 | 显示列表、资源上传、管线、提交 | Raster/Impeller、驱动、GPU 队列 |
| Raster 已交付但栅栏晚 | GPU 负载、频率、带宽 | GPU 阶段/计数器、生产者栅栏 |
| 外部纹理不更新 | 相机/编解码器/插件生产者、Surface 生命周期 | 纹理 ID、队列、回调 |
| texture 根视图就绪但宿主晚 | SurfaceTexture、ViewRoot、HWUI | 宿主遍历、DrawFrame、宿主入队 |
| PlatformView 错位 | 两套遍历/事务/锁存 | 图层 ID、事务、栅栏、显示提交 |

### 5. 做单变量 A/B

可控制的变量包括：

- Widget 更新范围；
- 图片 decode 尺寸；
- 模糊/saveLayer/透明度/裁剪；
- PlatformView 数量与策略；
- Impeller 退出选项；
- 根视图 RenderMode；
- 外部纹理帧率与尺寸；
- 页面分辨率和刷新率。

比较 P50/P95/P99 帧时间、错过截止时间、输入到显示延迟、内存、功耗和画面正确性。平均 FPS 会掩盖少量长帧。

## 栅栏、FrameTimeline 与最终显示

### 不同根视图有不同栅栏链

`surface` 根视图有独立生产者栅栏与图层释放栅栏。`texture`/`image` 根视图先产生中间图像就绪/释放事件，再由宿主 HWUI 生成新的应用窗口生产者栅栏。PlatformView 与叠加层还会加入各自缓冲与事务。

SurfaceFlinger 在 Android 17 FrontEnd 中处理图层快照。CompositionEngine 与 HWC 协商 DEVICE/CLIENT 合成；需要 CLIENT 时，RenderEngine 生成客户端目标。显示栅栏与各图层释放栅栏属于显示端反馈。

### FrameTimeline 令牌不一定一一对应

Flutter 根 Surface、宿主应用窗口和独立 PlatformView 图层可能有不同帧号/令牌。外部纹理的中间帧也可能没有标准应用 FrameTimeline。

关联时使用多组标识：

- Flutter 引擎帧 ID；
- 纹理 ID；
- 缓冲 ID/帧号；
- SurfaceFlinger 图层 ID；
- 预期/实际呈现时间；
- 生产者/获取/释放/显示栅栏。

Dart 帧结束只表示框架/引擎的一个阶段结束，不能作为上屏时间。

### 内核边界

`android17-6.18-2026-06_r6` 提供通用 dma-buf、dma-heap、dma-fence 与 sync_file 语义。它能解释缓冲共享、引用和栅栏传递，不能证明设备具体使用哪种 GPU 调度器、分配器、压缩或栅栏跟踪点。

栅栏等待表示某个依赖未完成。判断根因还要找到栅栏所有者、对应提交、频率、队列深度和负载。

## 16 KB 页大小与 Flutter 插件

Android 15 起支持 16 KB 页大小设备。Flutter 应用中的引擎/AOT 原生库、FFI 库和含 `.so` 的插件都要同时满足：

- APK 中未压缩 `.so` 的 ZIP 对齐；
- ELF 加载段的 `p_align`；
- 原生代码不能假定 `PAGE_SIZE == 4096`；
- mmap、共享内存与自定义分配器按运行时页大小工作。

工程检查可按下面执行：

- 使用支持 16 KB 打包的 AGP；Android 官方建议 AGP 8.5.1+；
- 使用 NDK r28+ 让新构建的共享库默认适配 16 KB；
- 旧 NDK 明确配置链接器页大小选项，并用 ELF 工具复核；
- 检查所有预编译插件 `.so` 与 `libc++_shared.so`；
- 在 16 KB 模拟器/真机运行启动、PlatformView、相机/视频、FFI 和后台恢复测试。

`packagingOptions` 只能影响 APK 打包，不能修复 ELF `p_align` 或原生代码中的 4 KB 常量。Android 17 平台锚点也不会替未重编译的插件修复这些问题。

## Android 12—17 与 Flutter 版本边界

两条版本线需要分开记录：

| 平台/Flutter 版本 | 与 Flutter 渲染直接相关的变化 |
| --- | --- |
| Android 12 / API 31 | BLAST 与 FrameTimeline 形成现代显示分析基线；应用仍携带自己的 Flutter 引擎。 |
| Android 13 / API 33 | 图像栅栏 Java API 可供当前 ImageReader 生产者路径使用；显示 HAL 进入 AIDL 时代。 |
| Android 14 / API 34 | 提供 HCPP 所需的事务同步平台前提，但不会自动开启 HCPP。 |
| Android 15 / API 35 | 16 KB 页大小兼容成为 Flutter 引擎/插件的原生约束。 |
| Android 16 / API 36 | AOSP 对支持 64 位 ABI 且非低内存的设备要求可用的最高 Vulkan 功能集；Android 16+ 出厂设备要求 Vulkan 1.4。旧 APK 的 Flutter 渲染器/线程模型不会随系统更新。 |
| Android 17 / API 37 | 当前平台源码锚点；继续按 Surface、FrontEnd、CompositionEngine、AIDL Composer 与内核栅栏分析。 |
| Flutter 3.24 | `SurfaceProducer` 稳定可用。 |
| Flutter 3.27 | Android API 29+ 默认启用 Impeller。 |
| Flutter 3.32 稳定版 | Android/iOS 默认合并 UI 与平台线程；3.29—3.31 的过渡构建按引擎版本与参数确认。 |
| Flutter 3.38 | Android/iOS 移除关闭 UI/platform 线程合并的选项。 |
| Flutter 3.44 | HCPP 作为 API 34+、Vulkan/Impeller 条件下的实验性选择启用能力。 |
| Flutter 3.44.8 | Flutter 源码验证标签。 |

运行在 Android 17 上的旧 Flutter 应用仍可能使用旧线程模型、旧版渲染器、Virtual Display 或旧插件。系统版本不能替代 APK/引擎版本识别。

## 常见误判

| 误判 | 应怎样验证 |
| --- | --- |
| Flutter 固定有独立 UI、Platform、Raster 三线程 | 以 Flutter 3.32 稳定版为默认合并边界；3.29—3.31 按引擎版本与启动参数确认 |
| Flutter 帧结束就是上屏 | 继续追 GPU 栅栏、根视图/宿主入队、SF 锁存与显示提交 |
| `RenderMode.surface` 内容属于宿主应用窗口 | 查 `FlutterSurfaceView` 子图层 |
| `RenderMode.texture` 只有一个 BufferQueue | 分开 SurfaceTexture 生产者与宿主应用窗口 |
| 外部纹理就绪等于画面已更新 | 还要等待 Raster 采样、根视图提交与显示提交 |
| `AndroidView` 固定使用 Hybrid Composition | 查 TLHC、VD、HC、HCPP 与回退路径 |
| Android 14+ 自动使用 HCPP | 还需 Flutter 3.44+、选择启用、API 34+、Vulkan 和 Impeller |
| Android 15+ 自动切到 Impeller | 渲染器由 APK 携带的 Flutter 引擎决定 |
| Impeller 消除了所有首次卡顿 | 继续检查上下文、管线、图集、上传、驱动和 GPU |
| Raster 线程长就是 GPU 慢 | 分开 Raster CPU、提交、GPU 完成与栅栏 |

## 源码与官方资料

### Flutter 3.44.8

- [`VsyncWaiterAndroid`](https://github.com/flutter/flutter/blob/3.44.8/engine/src/flutter/shell/platform/android/vsync_waiter_android.cc)、[`Choreographer`](https://github.com/flutter/flutter/blob/3.44.8/engine/src/flutter/impeller/toolkit/android/choreographer.cc)、[Java `VsyncWaiter`](https://github.com/flutter/flutter/blob/3.44.8/engine/src/flutter/shell/platform/android/io/flutter/view/VsyncWaiter.java)：NDK 优先与 Java fallback。
- [`settings.h`](https://github.com/flutter/flutter/blob/3.44.8/engine/src/flutter/common/settings.h)、[`switches.cc`](https://github.com/flutter/flutter/blob/3.44.8/engine/src/flutter/shell/common/switches.cc)、[`flutter_main.cc`](https://github.com/flutter/flutter/blob/3.44.8/engine/src/flutter/shell/platform/android/flutter_main.cc)、[`android_shell_holder.cc`](https://github.com/flutter/flutter/blob/3.44.8/engine/src/flutter/shell/platform/android/android_shell_holder.cc)：3.44.8 的线程合并、渲染器选择与 Android API 29 边界。
- [`RenderMode.java`](https://github.com/flutter/flutter/blob/3.44.8/engine/src/flutter/shell/platform/android/io/flutter/embedding/android/RenderMode.java)、[`FlutterSurfaceView`](https://github.com/flutter/flutter/blob/3.44.8/engine/src/flutter/shell/platform/android/io/flutter/embedding/android/FlutterSurfaceView.java)、[`FlutterTextureView`](https://github.com/flutter/flutter/blob/3.44.8/engine/src/flutter/shell/platform/android/io/flutter/embedding/android/FlutterTextureView.java)、[`FlutterImageView`](https://github.com/flutter/flutter/blob/3.44.8/engine/src/flutter/shell/platform/android/io/flutter/embedding/android/FlutterImageView.java)：根视图目标。
- [`FlutterRenderer.java`](https://github.com/flutter/flutter/blob/3.44.8/engine/src/flutter/shell/platform/android/io/flutter/embedding/engine/renderer/FlutterRenderer.java)、[`TextureRegistry.java`](https://github.com/flutter/flutter/blob/3.44.8/engine/src/flutter/shell/platform/android/io/flutter/view/TextureRegistry.java)、[`SurfaceTextureSurfaceProducer.java`](https://github.com/flutter/flutter/blob/3.44.8/engine/src/flutter/shell/platform/android/io/flutter/embedding/engine/renderer/SurfaceTextureSurfaceProducer.java)：外部纹理、底层载体、生命周期与栅栏。
- [`PlatformViewsController.java`](https://github.com/flutter/flutter/blob/3.44.8/engine/src/flutter/shell/platform/android/io/flutter/plugin/platform/PlatformViewsController.java)、[`PlatformViewsController2.java`](https://github.com/flutter/flutter/blob/3.44.8/engine/src/flutter/shell/platform/android/io/flutter/plugin/platform/PlatformViewsController2.java)：TLHC、HC、VD 与 HCPP。
- [`android_context_dynamic_impeller.cc`](https://github.com/flutter/flutter/blob/3.44.8/engine/src/flutter/shell/platform/android/android_context_dynamic_impeller.cc)、[Impeller README](https://github.com/flutter/flutter/blob/3.44.8/engine/src/flutter/impeller/README.md)：Vulkan/OpenGLES 自动选择、离线着色器、管线、缓存与子系统边界。

### Android 17 与内核

- Android 17 [`SurfaceView.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/view/SurfaceView.java)、[`TextureView.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/view/TextureView.java)、[`ImageReader.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/media/java/android/media/ImageReader.java)：根视图/宿主目标。
- 原生图形 [`BufferQueueProducer.cpp`](https://android.googlesource.com/platform/frameworks/native/+/android-17.0.0_r1/libs/gui/BufferQueueProducer.cpp)、[`Surface.cpp`](https://android.googlesource.com/platform/frameworks/native/+/android-17.0.0_r1/libs/gui/Surface.cpp)、[`SurfaceFlinger.cpp`](https://android.googlesource.com/platform/frameworks/native/+/android-17.0.0_r1/services/surfaceflinger/SurfaceFlinger.cpp)：缓冲提交与显示。
- 内核 [`dma-buf.c`](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/drivers/dma-buf/dma-buf.c)、[`dma-fence.c`](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/drivers/dma-buf/dma-fence.c)、[`sync_file.c`](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/drivers/dma-buf/sync_file.c)：共享缓冲与栅栏。

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
