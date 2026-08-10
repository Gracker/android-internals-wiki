---
title: 渲染机制的版本演进
chapter: 2.9
section: 2.9
status: finalized
pipeline_stage: ready-to-publish
applicable_versions: Android 3.0 (API 11) ~ Android 17 (API 37)
tags: [rendering, gpu, vsync]
confidence: medium
last_verified: 2026-07-25
last_verified_against: AOSP android-17.0.0_r1 + kernel android17-6.18-2026-06_r6 + historical AOSP tags + Android 17 official docs + AndroidX WebGPU 1.0.0-alpha05 + Writer rendering_pipelines S01-S14
sources:
  - type: official
    path: developer.android.com/about/versions
  - type: official
    path: developer.android.com/about/versions/16/features
  - type: official
    path: developer.android.com/about/versions/17/summary
  - type: official
    path: developer.android.com/develop/ui/views/graphics/hardware-accel
  - type: official
    path: developer.android.com/develop/ui/views/animations/adaptive-refresh-rate
  - type: official
    path: developer.android.com/develop/ui/views/graphics/webgpu
  - type: official
    path: developer.android.com/jetpack/androidx/releases/webgpu#1.0.0-alpha05
  - type: official
    path: developer.android.com/reference/androidx/webgpu/GPUSurface
  - type: official
    path: developer.android.com/reference/android/view/Choreographer.FrameTimeline
  - type: official
    path: developer.android.com/reference/android/view/Display
  - type: official
    path: developer.android.com/reference/android/view/FrameMetrics
  - type: official
    path: developer.android.com/games/develop/vulkan/overview
  - type: official
    path: developer.android.com/ndk/guides/graphics/android-vulkan-profile
  - type: official
    path: perfetto.dev/docs/data-sources/frametimeline
  - type: official
    path: source.android.com
  - type: official
    path: source.android.com/docs/compatibility/16/android-16-cdd
  - type: official
    path: source.android.com/docs/core/graphics/implement-vulkan
  - type: official
    path: github.com/KhronosGroup/Vulkan-Profiles/blob/1e7889df491ae9284ca096fcc1eb2bfcd1f367cb/profiles/VP_ANDROID_16_minimums.json
  - type: aosp
    path: frameworks/base/core/java/android/view/Choreographer.java (android-5.0.0_r1)
  - type: aosp
    path: frameworks/base/core/java/android/view/Choreographer.java (android-6.0.0_r1)
  - type: aosp
    path: frameworks/base/libs/hwui/Properties.cpp (android-8.0.0_r1)
  - type: aosp
    path: frameworks/base/libs/hwui/Properties.cpp (android-9.0.0_r1)
  - type: aosp
    path: frameworks/base/core/java/android/view/Choreographer.java (android-17.0.0_r1)
  - type: aosp
    path: frameworks/base/core/java/android/view/Display.java (android-17.0.0_r1)
  - type: aosp
    path: frameworks/base/core/java/android/view/FrameRateVelocityPoint.java (android-17.0.0_r1)
  - type: aosp
    path: frameworks/base/core/java/android/view/FrameMetrics.java (android-17.0.0_r1)
  - type: aosp
    path: frameworks/base/graphics/java/android/graphics/RuntimeColorFilter.java (android-17.0.0_r1)
  - type: aosp
    path: frameworks/base/graphics/java/android/graphics/RuntimeXfermode.java (android-17.0.0_r1)
  - type: aosp
    path: frameworks/base/graphics/java/android/graphics/animation/RenderNodeAnimator.java (android-17.0.0_r1)
  - type: aosp
    path: frameworks/base/libs/hwui/pipeline/skia/SkiaOpenGLPipeline.cpp (android-17.0.0_r1)
  - type: aosp
    path: frameworks/base/libs/hwui/pipeline/skia/SkiaVulkanPipeline.cpp (android-17.0.0_r1)
  - type: aosp
    path: frameworks/native/libs/gui/BLASTBufferQueue.cpp (android-17.0.0_r1)
  - type: aosp
    path: frameworks/native/services/surfaceflinger/Scheduler/FrameTimeline.cpp (android-17.0.0_r1)
  - type: aosp
    path: frameworks/native/services/surfaceflinger/Scheduler/FrameTimeline.h (android-17.0.0_r1)
  - type: aosp
    path: external/perfetto/protos/perfetto/trace/android/frame_timeline_event.proto (android-17.0.0_r1)
  - type: kernel
    path: kernel/common/drivers/dma-buf/dma-buf.c (android17-6.18-2026-06_r6)
  - type: kernel
    path: kernel/common/drivers/dma-buf/dma-fence.c (android17-6.18-2026-06_r6)
  - type: kernel
    path: kernel/common/drivers/dma-buf/sync_file.c (android17-6.18-2026-06_r6)
  - type: writer
    path: Writer/rendering_pipelines/S01_rendering_types_overview.md
  - type: writer
    path: Writer/rendering_pipelines/S02_aosp_standard_type.md
  - type: writer
    path: Writer/rendering_pipelines/S03_surfaceview_type.md
  - type: writer
    path: Writer/rendering_pipelines/S04_textureview_type.md
  - type: writer
    path: Writer/rendering_pipelines/S05_mixed_rendering_type.md
  - type: writer
    path: Writer/rendering_pipelines/S06_multi_window_type.md
  - type: writer
    path: Writer/rendering_pipelines/S07_software_offscreen_type.md
  - type: writer
    path: Writer/rendering_pipelines/S08_native_graphics_type.md
  - type: writer
    path: Writer/rendering_pipelines/S09_webview_type.md
  - type: writer
    path: Writer/rendering_pipelines/S10_flutter_type.md
  - type: writer
    path: Writer/rendering_pipelines/S11_camera_type.md
  - type: writer
    path: Writer/rendering_pipelines/S12_video_overlay_hwc_type.md
  - type: writer
    path: Writer/rendering_pipelines/S13_game_type.md
  - type: writer
    path: Writer/rendering_pipelines/S14_react_native_type.md
  - type: writer
    path: Writer/rendering_pipelines/images/DIAGRAM_MANIFEST.md
drafted_date: 2026-03-30
drafted_by: openclaw-task2a
task6_reviewed_date: 2026-06-15
reviewed_date: 2026-06-15
reviewed_by: openclaw-task6
polish_count: 1
polish_date: 2026-04-05
polish_by: task2b-polish
task6_state: reviewed
task6_result: pass-light-edit
task9_state: reviewed
task9_result: auto-fixed
task2b_state: fixed
task2b_result: fixed-lite
last_task2b_at: "2026-06-15T06:50:00+08:00"
last_task2b_lite_at: 2026-06-29
task9_reviewed_by: openclaw-task9
task9_reviewed_date: 2026-06-15
last_task9_at: "2026-06-15T07:26:56+08:00"
task9_review_notes: "2026-06-15 Task9 re-review: AUTO-FIX。修正 FrameMetrics 常量 COMMANDS_DURATION -> COMMAND_ISSUE_DURATION；修正 Android 16 Vulkan 1.4、VP_ANDROID_16_minimums 与 AVP 2025 的层级边界；移除 Android 17 Choreographer 新增帧控制接口的无证据断言。P0/P1 已局部修复，queue 无新增 pending，回到 Task6 复审。"
task6_review_notes: "2026-06-15 08:06 Task6 revisiting re-review: pass-light-edit。Task9 auto-fix 全部验证通过（COMMAND_ISSUE_DURATION 常量修正、Vulkan 1.4/VP_ANDROID_16_minimums/AVP 2025 层级边界澄清、Android 17 Choreographer 无证据断言已移除）。L1 禁用词/高频词扫描无命中；否定-纠正结构 2 次卡线但未超限。修标题括号一致性 （Android 4.1）→(Android 4.1)。无 L3/L4 新增回炉项，queue 无 pending。自动晋升 finalized。 2026-05-27 12:06 Task6 revisiting：pass-light-edit。移除源码调研 HTML 注释，统一正文中文标点与中英文混排；L1 禁用词与高频词扫描无命中；无新增 L3/L4 回炉项，送 Task9 复审。"
last_task6_review_log: logs/review/2026-05-27-12-review.md
last_task6_at: "2026-06-15T08:06:00+08:00"
last_task2b_verifier_at: "2026-05-27T11:44:00+08:00"
task2b_verifier_result: ready-for-task6
deepseek_cn_review_state: done
last_deepseek_cn_review_at: 2026-06-15
last_task9_audit: 2026-06-15
last_task9_audit_log: logs/deep-review/2026-06-15-06-audit.md
last_task9_autofix_at: 2026-06-15
last_task9_review_log: logs/deep-review/2026-06-15-07-deep-review.md
---

# 渲染机制的版本演进

Android 渲染史不能只记成一串版本号。拿到 Perfetto 后，工程师需要回答三个问题：

1. 这一版由哪个线程记录 View 绘制命令，又由哪个线程准备和提交 GPU 工作？
2. App buffer 经过哪种队列与事务交给 SurfaceFlinger，页面里是否还有独立 Surface？
3. 当时有哪些 VSync、帧截止时间和 jank 数据可以使用？

这三条线的变化速度不同。Android 5.0 增加 RenderThread，没有改变每个页面都通过 SurfaceFlinger 显示这一事实；Android 11 引入 BLAST，也没有删除 BufferQueue；Android 12 增加 FrameTimeline，更没有让每个红色帧自动带上唯一根因。

当前平台源码锚点是 Android 17 / API 37 的 `android-17.0.0_r1`，kernel 锚点是 `android17-6.18-2026-06_r6`。旧版本只用于说明演进，当前类名与行为以 Android 17 为准。

## 时间线速查

| 版本 | 已验证的里程碑 | 分析 Trace 时的影响 |
| --- | --- | --- |
| Android 3.0 / API 11 | View 2D 硬件加速、显示列表模型、`View.setLayerType()` | 同一个 `Canvas` API 可能走软件或 HWUI 路径 |
| Android 4.0 / API 14 | 对 target API 14 及以上应用默认启用硬件加速 | 不能只按设备版本判断某个 Window 是否硬件加速 |
| Android 4.1 / API 16 | Project Butter、Choreographer、VSync 驱动的 UI 节拍、三重缓冲策略 | 帧工作开始与显示节拍建立明确关系 |
| Android 5.0 / API 21 | HWUI RenderThread | UI 线程记录与同步、RenderThread 执行需要分开看 |
| Android 6.0 / API 23 | Choreographer 增加 COMMIT 回调阶段 | 现代回调顺序开始接近当前形态 |
| Android 7.0 / API 24 | Vulkan NDK API、`FrameMetrics` | 原生渲染多一种底层 API；App 可按 Window 取得帧阶段数据 |
| Android 8.x / API 26–27 | AOSP HWUI 可通过 `debug.hwui.renderer` 选择 SkiaGL/SkiaVulkan，未设置时仍使用旧 OpenGL renderer | 看到 Skia 后端类不等于该版本默认启用 |
| Android 9 / API 28 | AOSP 将 `debug.hwui.renderer` 的默认值改为 `skiagl` | 不要把旧 `OpenGLRenderer` 类名套到 Android 9 以后的 AOSP 默认主路径 |
| Android 11 / API 30 | 主窗口路径开始使用 BLASTBufferQueue | buffer 与 SurfaceControl transaction 的关系更紧 |
| Android 12 / API 31 | FrameTimeline；`FrameMetrics` 增加 GPU duration 与 deadline | 可关联 App SurfaceFrame 和 DisplayFrame，并区分 CPU/GPU/显示责任 |
| Android 13 / API 33 | `Choreographer.FrameData` / `FrameTimeline` 公共 API；AGSL `RuntimeShader` | App 可获取候选帧时间线；Canvas 增加运行时 shader |
| Android 15 / API 35 | ARR 在支持 Android 15 QPR1 与相应 HAL 的设备上可用；ANGLE 成为可选的 GLES-on-Vulkan 层 | VSync 间隔和 render rate 不能再假设固定；GLES 后端需看设备选择 |
| Android 16 / API 36 | `Display.hasArrSupport()`、`getSuggestedFrameRate()`；`RuntimeColorFilter` / `RuntimeXfermode`；Vulkan 1.4 launch-device 要求 | App 能查询 ARR；AGSL 可用于滤镜与混合；设备能力仍需运行时查询 |
| Android 17 / API 37 | Jetpack WebGPU；GLES `prefer_angle` manifest 请求；`Display.getFrameRateVelocityMapping()` | WebGPU 增加现代 GPU 接口但仍需独立依赖；ANGLE 仍是偏好请求；滚动帧率可结合速度映射 |

表中“引入”表示平台或 API 的版本边界，不保证所有升级到该版本的设备拥有相同 GPU、显示 HAL、驱动能力和默认后端。

## Android 3.0–4.0：View 硬件加速成为标准路径

### Android 3.0：HWUI 与显示列表

Android 3.0 以前，普通 View 的 `Canvas` 主路径使用 Skia 软件光栅化。应用仍可以通过 OpenGL ES 等 API 自行使用 GPU，所以“Android 2.x 所有图形都由 CPU 绘制”并不准确。

API 11 开始，Android 2D View 管线支持硬件加速。硬件加速 Window 中，View 的绘制操作会记录到显示列表；未失效的 View 可以复用已有记录，位置、缩放、旋转或 alpha 等属性也可以作为 RenderNode 状态处理。

这里要区分两件事：

- `View.draw()` / `onDraw()` 的 Java 调用负责描述绘制；
- GPU 何时光栅化这些命令，取决于 HWUI 后续回放、buffer 和驱动调度。

“调用 `canvas.drawRect()` 就立即执行一条 GL 命令”不符合显示列表模型。

API 11 同时提供 `View.setLayerType()`。`LAYER_TYPE_HARDWARE` 可以把稳定内容放入硬件层，便于后续做合成属性动画；它会占用图形内存。内容失效后仍要重新绘制并更新 layer，尺寸或渲染上下文变化时还可能重新分配，因此不能长期给所有 View 强制开启。

### Android 4.0：默认值与 target API 有关

硬件加速从 API 11 可用，从 target API 14 起默认启用。以下两种情况下都可能出现软件 Canvas：

- 应用或 Activity 显式关闭硬件加速；
- 硬件加速 View 被绘制到 Bitmap 等软件 Canvas。

自定义 View 判断当前绘制路径时，应看 `Canvas.isHardwareAccelerated()`。`View.isHardwareAccelerated()` 只表示 View 附着的 Window 是否硬件加速。

## Android 4.1：Project Butter 建立 VSync 驱动的帧节拍

Project Butter 把输入、动画和 View traversal 放到统一的帧节拍中。`Choreographer` 在 API 16 成为公共 API，早期 AOSP 的回调队列是：

```text
INPUT → ANIMATION → TRAVERSAL
```

Android 6.0 加入 COMMIT，后续又加入 INSETS_ANIMATION。Android 17 的顺序是：

```text
INPUT → ANIMATION → INSETS_ANIMATION → TRAVERSAL → COMMIT
```

这些队列运行在 Choreographer 所属的 Looper 线程。应用主 ViewRoot 通常在主线程上，但 native engine、SurfaceFlinger 客户端或其他 Looper 也可以拥有不同用途的 Choreographer。

### `VSYNC-app` 与 `VSYNC-sf` 是调度事件

Perfetto 里的 `VSYNC-app`、`VSYNC-sf` 或相关预测轨道描述调度节拍。它们不应被逐条解释成“应用直接收到一次硬件中断”。现代系统会根据硬件 VSync 样本、显示模式与工作时长预测 App 和 SurfaceFlinger 的唤醒时间。

旧 AOSP 资料常出现 `DispSync`，Android 17 的主线使用 Scheduler 与 `VsyncPredictor` 等组件。内部预测器跨版本持续变化，Trace 分析应关注本帧的 expected/actual timeline、deadline 和 present，不要靠预测器类名判断问题。

### 三重缓冲解决的是流水线容量

Project Butter 将三重缓冲作为流畅性策略之一。它允许 Producer、GPU 与 Consumer 在更多情况下并行推进，减少“前一块 buffer 未释放，下一帧无处可画”的概率。

三重缓冲不表示所有 Surface 永远只有三个固定 slot，也不保证卡顿后无额外延迟。现代 BufferQueue 的 slot 数、dequeue 上限、异步模式和使用者约束会共同决定可用容量。Producer 持续快于显示消费时，队列会积压，FrameTimeline 可能标记 buffer stuffing，用户看到的输入延迟也会增加。

## Android 5.0–6.0：RenderThread 接管 HWUI 的渲染执行

Android 5.0 的 `libs/hwui/renderthread/RenderThread.cpp` 已包含独立 RenderThread。普通硬件加速 View 的主线变成：

1. UI 线程执行输入、动画、measure、layout，并更新失效 View 的显示列表；
2. `ThreadedRenderer` / `HardwareRenderer` 通过 native RenderProxy 把帧任务交给 RenderThread；
3. `DrawFrameTask::syncFrameState()` 同步 RenderNode 树、Surface 与资源状态；
4. RenderThread 准备 Skia/GPU 工作，并 dequeue/queue App Window buffer；
5. GPU completion fence 随 buffer 交给下游，SurfaceFlinger 再处理 transaction、latch 和合成。

主线程与 RenderThread 不是严格首尾相接的两段。同步阶段必须处理本帧状态；在条件满足时，UI 线程可以在 RenderThread 完成本帧 GPU 工作前继续运行。不同 Android 版本与场景的阻塞点也不相同。

Perfetto 中 `DrawFrame` 很长只能说明 RenderThread 这段跨度较长。它可能包含：

- RenderThread 的 CPU 工作；
- RenderNode 或资源同步；
- shader / pipeline 准备与纹理上传；
- `dequeueBuffer`、fence 或 buffer back-pressure；
- GPU 命令提交与 GPU 完成等待。

需要 GPU slices、completion fence、`FrameMetrics.GPU_DURATION`、设备 counter 或 AGI 才能进一步确认 GPU 工作量。

### RenderThread 动画有明确范围

`RenderNodeAnimator` 和基于 `CanvasProperty` 的部分动画可以在 RenderThread 上推进。普通 `ValueAnimator`、大部分 `ObjectAnimator` 和业务状态更新仍由 UI 线程的 Choreographer 驱动。看到 RenderThread 存在，不代表主线程卡住时所有动画都能继续。

Android 5.0 的 Choreographer 源码仍有 INPUT、ANIMATION、TRAVERSAL 三类回调；Android 6.0 增加 COMMIT。这个差异会影响阅读早期源码，但不改变 RenderThread 由 HWUI 自己管理这一事实。

## Android 7.0–10：观测 API 与 GPU 后端扩展

### Android 7.0：FrameMetrics

API 24 增加 `Window.addOnFrameMetricsAvailableListener()` 和 `FrameMetrics`。它按 Window 报告 UI/HWUI 的时间里程碑：

| 指标 | 主要含义 |
| --- | --- |
| `UNKNOWN_DELAY_DURATION` | UI 线程未及时开始处理帧的等待 |
| `INPUT_HANDLING_DURATION` | 输入回调 |
| `ANIMATION_DURATION` | 动画回调 |
| `LAYOUT_MEASURE_DURATION` | measure/layout |
| `DRAW_DURATION` | 显示列表计算 |
| `SYNC_DURATION` | 显示列表与 RenderThread 同步 |
| `COMMAND_ISSUE_DURATION` | 向 GPU 发出绘制命令 |
| `SWAP_BUFFERS_DURATION` | 把帧 buffer 交给显示子系统 |
| `TOTAL_DURATION` | 从 intended VSync 到 frame completed 的跨度 |

这些阶段可能并行，`TOTAL_DURATION` 不等于其他 duration 的算术和。`COMMAND_ISSUE_DURATION` 长也不等于 GPU execution 长；前者观察 CPU 侧发命令阶段。

API 31 又增加：

- `GPU_DURATION`：该帧在 GPU 上完成所需时间；
- `DEADLINE`：系统分配给 App 生产该帧的时间预算。

API 36 增加 `FRAME_TIMELINE_VSYNC_ID`，可与 compositor 的帧时间线数据关联。Listener 回调还会给出自上次回调以来丢弃的报告数量；需要跨线程保存时，应复制 `FrameMetrics` 对象。

### Android 7.0：Vulkan 进入 NDK

Vulkan 从 API 24 可供 native 应用使用。它减少驱动隐式状态，把命令缓冲、资源同步和内存管理交给应用显式控制。代价是同步、生命周期和跨设备能力判断更复杂。

Vulkan API 可用，不表示 View/HWUI 一定使用 Vulkan。应用 Vulkan renderer、HWUI SkiaVulkan、ANGLE-on-Vulkan 是三条不同路径。

### Android 8.x–9：HWUI 转向 Skia GPU 后端

早期 HWUI 自己维护大量 OpenGL renderer 逻辑。Android 8.0/8.1 的 `Properties.cpp` 已识别 `skiagl` 和 `skiavk`，但 `debug.hwui.renderer` 未设置时仍回退旧 OpenGL renderer；Android 9.0 的同一文件把属性默认值明确改为 `skiagl`。绘制 API 仍是 View/Canvas/RenderNode，底层由 HWUI 直接管理 GL 的路径逐步转向 Skia GPU backend。

Android 17 的 `libs/hwui/pipeline/skia/` 仍有 `SkiaOpenGLPipeline`、`SkiaVulkanPipeline` 和公共 `SkiaGpuPipeline`。设备可以按产品配置、驱动和调试设置选择后端，不能按 Android 版本断言所有设备都走同一个 backend。

Skia 项目中的 Graphite 是后端研发方向。`android-17.0.0_r1` 的 HWUI pipeline 目录没有 Graphite pipeline 或默认启用路径，因此不将它列为 Android 平台里程碑。

### Vulkan 版本要求要看 launch-device 条件

官方 Vulkan 实现文档给出的主要版本阶段是：

- Android 7：Vulkan 1.0；
- Android 9：Vulkan 1.1；
- Android 13：Vulkan 1.3；
- Android 16：Vulkan 1.4。

对设备要求的严谨说法是：64 位、非 low-memory 且以相应版本 launch 的设备，需要支持该版本要求的高级 Vulkan feature set。OTA 升级后的旧硬件不会因系统版本号自动获得新 GPU 能力。应用仍应查询 `FEATURE_VULKAN_HARDWARE_VERSION`、extension、profile 与 dEQP level。

`VP_ANDROID_16_minimums`、Android Baseline Profile 和 Compatibility Definition 解决的问题不同：profile 描述一组可查询能力，CDD 定义设备兼容要求，应用的最低 Vulkan version/extension 则由自己的渲染器决定。

## Android 11：BLAST 改变 buffer 与 transaction 的配合

Android 11 的 AOSP 已包含 `BLASTBufferQueue.cpp`，主窗口路径也开始迁移到 BLAST。BLAST 的名称来自 Buffer Layer And Surface Transactions。

它没有删除 BufferQueue。BLAST 内部仍使用 Producer/Consumer buffer queue，并把 buffer update 变成 `SurfaceControl::Transaction` 的一部分，便于把 buffer、frame number、crop、transform 和窗口几何状态按帧关系提交给 SurfaceFlinger。

现代 App Window 的简化路径是：

```text
RenderThread
  → Surface / BufferQueue producer
  → BLASTBufferQueue consumer
  → Transaction::setBuffer() / apply()
  → SurfaceFlinger FrontEnd
```

这条路径说明 BLAST 位于 App producer 与 SurfaceFlinger transaction 之间。`queueBuffer()` 只表示 Producer 提交了一块 buffer；SurfaceFlinger 还要收到 transaction、检查 acquire fence、选择/latch buffer，随后完成本轮显示合成。

Android 12 以后 BLAST 覆盖更多窗口与 Surface 场景，但旧 BufferQueue 类型和非 BLAST 队列继续存在。Perfetto 中应按 layer、connection、transaction 和 buffer id 识别对象，不要只搜索某个固定 slice 名称。

## Android 12–14：FrameTimeline 把 App 帧与显示帧关联起来

### Android 12：SurfaceFrame 与 DisplayFrame

FrameTimeline 在系统侧维护 App `SurfaceFrame` 与 SurfaceFlinger `DisplayFrame` 的 expected/actual timing：

- `SurfaceFrame` 观察某个 Layer 的 App buffer 是否按选定时间线完成；
- `DisplayFrame` 观察 SurfaceFlinger/HWC 组织的显示帧是否按时 present；
- VSyncId / token 用来建立 App 帧和显示帧的关系；
- jank type 用于区分 App deadline、SurfaceFlinger CPU/GPU、display HAL、prediction、stuffing 等类别。

`Actual Timeline` 迟到是诊断入口。Perfetto 文档说明 App 帧结束会考虑 buffer post 和 GPU completion；SurfaceFlinger 侧还可能因 layer readiness、client composition、HWC 或 present 迟到。

私有 `TimelineItem`、`SurfaceFrame` 和 token 保存策略会随版本调整。应用开发者应依赖 Perfetto schema、公共 API 和目标版本源码，不应复制某个旧版本的私有结构体定义当作长期接口。

### Android 13：App 可以读取候选帧时间线

API 33 增加：

- `Choreographer.postVsyncCallback()`；
- `Choreographer.FrameData`；
- `Choreographer.FrameTimeline`；
- `getDeadlineNanos()`、`getExpectedPresentationTimeNanos()` 和 `getVsyncId()`。

一份 `FrameData` 可以包含多个候选 timeline，并标出平台偏好的 timeline。native 应用有对应的 AChoreographer frame callback data API，可以为 Surface transaction 选择 frame timeline。

这些 API 提供时间目标，不保证应用一定在 deadline 前完成，也不替代 buffer/fence/present 证据。

### Android 13–16：AGSL 扩展 Canvas 效果

Android 13 的 `RuntimeShader` 让应用用 Android Graphics Shading Language 编写运行时 shader，并作为 Canvas `Shader` 使用。Android 16 增加 `RuntimeColorFilter` 和 `RuntimeXfermode`，把 AGSL 扩展到颜色过滤和 source/destination 混合。

AGSL 属于 Canvas/HWUI 效果接口。复杂 shader、离屏 layer、模糊或多 pass 的成本仍由实际内容与 GPU 决定，API 版本本身不提供性能保证。

## Android 15–16：ARR、ANGLE 与 Vulkan 1.4

### ARR 改变了“固定 VSync 间隔”的假设

ARR 从 Android 15 开始提供，官方文档把可用条件写为支持相应 HAL 且运行 Android 15 QPR1 及以上。它可以让显示刷新节奏按内容 render rate 的离散 VSync 步进变化，减少不必要的高刷新率驻留和 mode switch。

Android 16 / API 36 增加 `Display.hasArrSupport()` 和 `getSuggestedFrameRate()`。应用还可以通过 View、Surface、ANativeWindow 的 frame-rate API 表达偏好。系统会综合同一显示上的多个 View、Layer、系统 UI、触摸和功耗策略，调用成功不等于立刻切到指定 Hz。

在 ARR 设备上看到 8.33 ms、16.67 ms 或更长 VSync 间隔变化时，应检查选定时间线、deadline、requested frame rate 和 active display mode，再判断是否异常。

### ANGLE 是可选 GLES-on-Vulkan 路径

Android 15 起，ANGLE 作为可选层把 OpenGL ES 映射到 Vulkan。它能改善兼容性，并可能改变 CPU/GPU 工作分布，但性能结果取决于设备、驱动和负载。

GLES 应用、原生 Vulkan 应用和 HWUI 页面不能混为一个类型。ANGLE 的启用也不代表应用源码已经迁移到 Vulkan API。

### Android 16 launch device 的 Vulkan 1.4

设备以 Android 16 及更高版本 launch，并满足 64 位、非 low-memory 等条件时，需要支持 Vulkan 1.4。GPU 驱动由 SoC/IHV 提供，framework 版本不能替代运行时 capability 查询。

## Android 17：WebGPU、ANGLE 偏好与滚动帧率映射

### WebGPU

Android 17 的发布说明把 WebGPU 列为图形新能力。公开接口来自独立发布的 Jetpack `androidx.webgpu:webgpu`，当前核验版本为 `1.0.0-alpha05`，不属于 `android.*` framework API；alpha 阶段的接口仍可能变化。该库提供 Kotlin/Java 绑定，以比 Vulkan 更高层的对象组织 adapter、device、queue、command buffer 与 WGSL shader。

WebGPU 不会让 View/Compose、WebView 或现有 GLES 应用自动换后端。分析使用 WebGPU 的应用时，应把它按独立 GPU API 和工作提交路径处理：离屏 compute 只跟踪 buffer、texture 与 queue；绘制到屏幕时，再沿 `GPUSurface` 的 current texture、`present()`、目标 `ANativeWindow`、BufferQueue 和最终 SurfaceFlinger Layer 追踪。

### `prefer_angle` 只表达偏好

Android 17 起，游戏可以在 manifest 中请求优先使用 ANGLE 作为 GLES driver：

```xml
<application android:appCategory="game">
    <meta-data
        android:name="com.android.graphics.driver.prefer_angle"
        android:value="true" />
</application>
```

平台无法使用 ANGLE 时会回到厂商 GLES driver。排查问题要记录实际 renderer/driver，不能只看 manifest。

### API 37 的 frame-rate/velocity mapping

`Display.getFrameRateVelocityMapping()` 返回当前 Display 的滚动速度阈值与可行 frame rate 组成的只读、非空映射。例如一个点可以表达“速度超过 300 dp/s 时使用 120 fps”。官方契约主要面向 RecyclerView、ScrollView、AbsListView、NestedScrollView 等 fling 场景。设备从内屏切到外屏，或收到 `DisplayListener.onDisplayChanged()` 后，需要针对当前 Window 所在 Display 重新查询。

这些点是 display-specific 策略输入，系统不会据此替 App 自动完成帧率切换。调用方仍要按速度选择映射点，并通过 View、Surface 或其他 frame-rate API 表达请求；列表也仍需在每个选定 deadline 前完成 UI、RenderThread、GPU 与 buffer 提交。

### Android 17 的标准 HWUI 主线

回到当前版本，普通 View/Compose App Window 可按以下对象分析：

```text
Choreographer / UI Thread
  → View traversal + RenderNode display list
  → HardwareRenderer / RenderProxy
  → RenderThread / DrawFrameTask / CanvasContext
  → SkiaOpenGL or SkiaVulkan pipeline
  → App Window BLAST buffer transaction
  → SurfaceFlinger FrontEnd RequestedLayerState / LayerSnapshot
  → CompositionEngine / HWComposer / Composer3
  → display present
```

页面有 `SurfaceView`、`TextureView`、视频、Camera、WebView、Flutter、游戏或 React Native 时，要先确认 Producer、Consumer 与最终 Layer。`SurfaceView` 常有独立 child Surface；`TextureView` 会先被宿主 HWUI 采样进 App Window；框架名无法替代 Surface 拓扑。

## 怎样用版本信息读 Perfetto

### 1. 记录设备与构建信息

记录：

- `Build.VERSION.SDK_INT`、build fingerprint 和 vendor image；
- app target SDK、图形 API 与 renderer；
- display mode、刷新率、ARR 支持；
- 页面里的 Window、SurfaceView、TextureView 和其他独立 Surface；
- Perfetto/Android Studio/AGI 版本与采集配置。

Track 名和 atrace slice 属于实现细节，厂商也会增加或改名。找不到旧教程中的名字，不代表对应机制不存在。

### 2. Android 5.0+ 分开 UI 与 RenderThread

UI 线程慢时看 input、animation、traversal、measure/layout 和 display-list record。RenderThread 慢时继续分辨 CPU、资源、buffer、fence、GPU submit 和 completion。不要用“哪个 slice 最长”直接给出 GPU/CPU 结论。

### 3. Android 11+ 同时看 BLAST、BufferQueue 和 transaction

需要回答四个问题：

1. Producer 何时 queue 哪个 frame number；
2. BLAST 何时把 buffer 放入哪次 transaction；
3. SurfaceFlinger 何时认为 transaction ready 并 latch；
4. 对应 DisplayFrame 何时 present。

`BufferTX - <layerName>` 只表示 SurfaceFlinger server 侧的 pending buffer transaction 发生变化，不表示屏幕已经显示。

### 4. Android 12+ 用 FrameTimeline 锁定帧

选中目标 janky `SurfaceFrame` 后，再跟到对应 `DisplayFrame`。App deadline missed、SF deadline missed 和 display HAL 问题需要不同证据。多 Surface 页面不能只看宿主 App Window 的一条 timeline。

### 5. Android 15+ 分开渲染帧率与显示刷新率

App 可能以 30 fps 更新，显示以 60/90/120 Hz 或 ARR 步进工作；多个 Layer 也可能按不同 cadence。帧是否准时应按选 timeline 和 deadline 判断，不能固定拿 16.67 ms 作为所有设备、所有帧的预算。

## API、平台实现与设备能力是三层约束

| 层次 | 例子 | 正确检查方式 |
| --- | --- | --- |
| 公共 API | `FrameMetrics`、`FrameTimeline`、WebGPU、`hasArrSupport()` | 看 API level、feature flag 与官方契约 |
| AOSP 平台实现 | RenderThread、BLAST、SurfaceFlinger FrontEnd、Skia pipeline | 看目标 tag 的源码和系统属性 |
| 设备能力 | GPU/Vulkan extension、ANGLE、HWC plane、ARR HAL、counter | 看运行时查询、dumpsys、driver 与目标设备 Trace |

“Android 17 支持某 API”只覆盖第一层；“AOSP 有某 pipeline”只覆盖第二层。具体手机是否启用、性能如何，仍由第三层决定。

## Kernel 与厂商边界

kernel 源码锚点是 `android17-6.18-2026-06_r6`。其中 `drivers/dma-buf/dma-buf.c` 管理共享 buffer 对象，`dma-fence.c` 定义异步完成依赖，`sync_file.c` 把 fence 暴露为可跨进程传递和等待的文件描述符；通用 kernel 还提供线程调度、内存回收和频率框架等基础机制。

HWUI backend、Vulkan/GLES driver、GPU job 调度、图形内存分配、DPU/HWC plane 与 ARR HAL 含有大量厂商实现。一个 framework 版本里程碑不保证 vendor driver 同步采用相同策略。Kernel fence 只能说明异步依赖是否完成；要解释迟到原因，还需找到 fence owner、提交者和对应硬件工作。

## 常见误区

### “BLAST 已经替代 BufferQueue”

BLAST 使用并管理 BufferQueue，把 buffer update 纳入 Surface transaction。现代系统里两者同时存在。

### “RenderThread 的 DrawFrame 长就是 GPU 慢”

`DrawFrame` 跨度包含 RenderThread CPU、资源、buffer、fence 和 GPU 相关阶段。需要 GPU completion 或直接 GPU 证据。

### “Android 16/17 设备都用 SkiaVulkan 或 Graphite”

Android 17 AOSP 提供 SkiaOpenGL 与 SkiaVulkan pipeline，产品选择与设备配置有关；当前 tag 没有 HWUI Graphite pipeline。

### “Vulkan 1.4 要求适用于所有升级设备”

launch-device 条件、64 位与 low-memory 条件决定兼容要求。旧设备 OTA 后仍以硬件和驱动上报为准。

### “ARR 让 VSync 随意变化”

ARR 按设备支持、内容投票和离散步进工作。间隔变化可以是正常策略，也可能是 mode switch 或调度问题，需要结合 display mode 与 FrameTimeline。

### “FrameMetrics 可以解释 SurfaceFlinger”

FrameMetrics 是 App Window 的渲染里程碑。SurfaceFlinger、HWC 和多 Layer 显示问题需要 Perfetto、layer state、composition type 与 present/fence 证据。

## 源码与官方资料

### 历史版本锚点

- [Android 5.0 `RenderThread.cpp`](https://android.googlesource.com/platform/frameworks/base/+/android-5.0.0_r1/libs/hwui/renderthread/RenderThread.cpp)：RenderThread 已进入 HWUI。
- [Android 5.0 `Choreographer.java`](https://android.googlesource.com/platform/frameworks/base/+/android-5.0.0_r1/core/java/android/view/Choreographer.java)：INPUT、ANIMATION、TRAVERSAL。
- [Android 6.0 `Choreographer.java`](https://android.googlesource.com/platform/frameworks/base/+/android-6.0.0_r1/core/java/android/view/Choreographer.java)：COMMIT 回调阶段。
- [Android 8.0 `Properties.cpp`](https://android.googlesource.com/platform/frameworks/base/+/android-8.0.0_r1/libs/hwui/Properties.cpp)、[Android 9.0 `Properties.cpp`](https://android.googlesource.com/platform/frameworks/base/+/android-9.0.0_r1/libs/hwui/Properties.cpp)：SkiaGL/SkiaVulkan 可选路径与 SkiaGL 默认值的版本分界。
- [Android 11 `BLASTBufferQueue.cpp`](https://android.googlesource.com/platform/frameworks/native/+/android-11.0.0_r1/libs/gui/BLASTBufferQueue.cpp)：BLAST 初期实现。

### Android 17 / `android-17.0.0_r1`

- [`Choreographer.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/view/Choreographer.java)：当前回调顺序、FrameData 与 FrameTimeline。
- [`FrameMetrics.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/view/FrameMetrics.java)：当前指标、GPU duration、deadline 与 VSyncId。
- [`Display.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/view/Display.java)、[`FrameRateVelocityPoint.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/view/FrameRateVelocityPoint.java)：ARR 查询、建议帧率与速度映射的 API 37 实现。
- [`DrawFrameTask.cpp`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/libs/hwui/renderthread/DrawFrameTask.cpp)、[`CanvasContext.cpp`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/libs/hwui/renderthread/CanvasContext.cpp)：UI/RenderThread 同步、绘制和 buffer 提交。
- [`SkiaOpenGLPipeline.cpp`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/libs/hwui/pipeline/skia/SkiaOpenGLPipeline.cpp)、[`SkiaVulkanPipeline.cpp`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/libs/hwui/pipeline/skia/SkiaVulkanPipeline.cpp)：当前 HWUI GPU backend。
- [`BLASTBufferQueue.cpp`](https://android.googlesource.com/platform/frameworks/native/+/android-17.0.0_r1/libs/gui/BLASTBufferQueue.cpp)：buffer 与 transaction。
- [SurfaceFlinger `FrameTimeline.h`](https://android.googlesource.com/platform/frameworks/native/+/android-17.0.0_r1/services/surfaceflinger/Scheduler/FrameTimeline.h)、[`FrameTimeline.cpp`](https://android.googlesource.com/platform/frameworks/native/+/android-17.0.0_r1/services/surfaceflinger/Scheduler/FrameTimeline.cpp)：SurfaceFrame、DisplayFrame 与 jank classification。
- [SurfaceFlinger FrontEnd](https://android.googlesource.com/platform/frameworks/native/+/android-17.0.0_r1/services/surfaceflinger/FrontEnd/)、[`HWComposer.cpp`](https://android.googlesource.com/platform/frameworks/native/+/android-17.0.0_r1/services/surfaceflinger/DisplayHardware/HWComposer.cpp)：RequestedLayerState、LayerSnapshot、validate/present。

### Kernel / `android17-6.18-2026-06_r6`

- [`dma-buf.c`](https://android.googlesource.com/kernel/common/+/android17-6.18-2026-06_r6/drivers/dma-buf/dma-buf.c)：共享 buffer 对象与 attachment/map 边界。
- [`dma-fence.c`](https://android.googlesource.com/kernel/common/+/android17-6.18-2026-06_r6/drivers/dma-buf/dma-fence.c)、[`sync_file.c`](https://android.googlesource.com/kernel/common/+/android17-6.18-2026-06_r6/drivers/dma-buf/sync_file.c)：异步完成依赖与 sync_file fd。

### 官方文档

- [Hardware acceleration](https://developer.android.com/develop/ui/views/graphics/hardware-accel)
- [FrameMetrics](https://developer.android.com/reference/android/view/FrameMetrics)
- [FrameTimeline in Perfetto](https://perfetto.dev/docs/data-sources/frametimeline)
- [Choreographer.FrameTimeline](https://developer.android.com/reference/android/view/Choreographer.FrameTimeline)
- [Adaptive refresh rate](https://developer.android.com/develop/ui/views/animations/adaptive-refresh-rate)
- [Android 16 graphics features](https://developer.android.com/about/versions/16/features#graphics)
- [Implement Vulkan](https://source.android.com/docs/core/graphics/implement-vulkan)
- [Vulkan and ANGLE on Android](https://developer.android.com/games/develop/vulkan/overview)
- [Android 17 features and changes](https://developer.android.com/about/versions/17/summary)
- [WebGPU for Android](https://developer.android.com/develop/ui/views/graphics/webgpu)、[AndroidX WebGPU releases](https://developer.android.com/jetpack/androidx/releases/webgpu)、[`GPUSurface`](https://developer.android.com/reference/androidx/webgpu/GPUSurface)
- [Display API](https://developer.android.com/reference/android/view/Display)
