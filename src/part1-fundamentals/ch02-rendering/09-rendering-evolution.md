---
title: 渲染机制的版本演进
chapter: '2.9'
section: '2.9'
status: ready-for-review
drafted_date: 2026-03-30
drafted_by: openclaw-task2a
task6_reviewed_date: "2026-05-14"
reviewed_date: "2026-05-14"
reviewed_by: "openclaw-task6"
applicable_versions: Android 3.0 (API 11) ~ Android 16 (API 36)
last_verified: '2026-04-23'
last_verified_against: AOSP android-16.0.0_r1 + external/perfetto + developer.android.com
confidence: medium
polish_count: 1
polish_date: '2026-04-05'
polish_by: task2b-polish
task6_state: revisiting
task6_result: needs-rework
task9_state: pending
task9_result: needs-rework
task2b_state: fixed
task2b_result: fixed-lite
last_task2b_at: "2026-05-13T23:35:47+08:00"
pipeline_stage: task6_pending
last_task2b_lite_at: '2026-05-27'
sources:
- type: official
  path: developer.android.com/about/versions
- type: official
  path: developer.android.com/about/versions/16/features
- type: official
  path: source.android.com
- type: aosp
  path: external/perfetto/protos/perfetto/trace/android/frame_timeline_event.proto
- type: aosp
  path: frameworks/base/graphics/java/android/graphics/RuntimeColorFilter.java
- type: aosp
  path: frameworks/base/graphics/java/android/graphics/animation/RenderNodeAnimator.java
- type: aosp
  path: frameworks/base/graphics/java/android/graphics/RuntimeXfermode.java
task9_reviewed_by: "openclaw-task9"
task9_reviewed_date: "2026-05-14"
last_task9_at: "2026-05-14T02:37:00+08:00"
task9_review_notes: "2026-05-14 task9 deep-review: needs-rework。P0 1 / P1 0 / P2 3;Vulkan profile 口径仍混淆,另有 RenderThread/FrameTimeline 表述、BLAST 版本总结和 16KB 页数据支撑需修正。"
task6_review_notes: "2026-05-14 Task6：L1/L2 小修（Vulkan profile 术语、BLAST 版本总结、标点）；发现 16KB Page Size 收益数据缺少测试条件/来源，已标注并写入 queue 回炉。"
last_task6_review_log: "logs/review/2026-05-14-08-review.md"
last_task6_at: "2026-05-14T08:11:00+08:00"
last_task2b_verifier_at: "2026-05-27T11:44:00+08:00"
task2b_verifier_result: ready-for-task6
---
# 渲染机制的版本演进

打开 Perfetto 抓一份 Trace,通常会看到 `RenderThread` 在主线程旁边执行 GPU 命令,`VSYNC-app` 和 `VSYNC-sf` 的信号整齐排列——这套"主线程构建 DisplayList → RenderThread 执行 GPU 命令 → SurfaceFlinger 合成上屏"的流水线,经历了十多个 Android 大版本的持续重构。

理解这段演进历史,是性能分析的前置知识:Perfetto 中的每一个 Track 名称、每一项 API 行为,都带着版本烙印。面对一份来自 Android 12 设备的 Trace 时,如果不知道 `BLASTBufferQueue` 已经取代了旧的 `BufferQueue`,就可能对着一个不存在的概念去排查问题。

这条演进线从硬件加速的引入开始,到 Vulkan 统一渲染堆栈为止,覆盖了 Perfetto 分析中会遇到的关键版本变化。

## 硬件加速的诞生(Android 3.0)与默认开启(Android 4.0)

### 问题的起点

Android 2.x 时代,所有 UI 绘制都依赖 CPU 完成。`Canvas` 的 `drawXXX` 操作最终走到 Skia 的软件光栅化路径,主线程负责从 Measure/Layout/Draw 到像素生成的全部工作。这套方案在低分辨率设备上勉强够用,但随着屏幕分辨率提升和 UI 复杂度增加,CPU 很快成为瓶颈。

### Android 3.0 Honeycomb:HWUI 登场

Android 3.0(API 11,2011 年)引入了基于 OpenGL ES 2.0 的硬件加速渲染管线 **HWUI**。这是 Android 首次将 GPU 引入 UI 渲染管线,从此 CPU 不再是唯一的渲染路径。

HWUI 带来了三个核心概念:

1. **DisplayList(后更名为 RenderNode)**:将 `View` 的绘制操作录制为一份命令列表,而非直接执行。当一个 `View` 只有位置变化(平移、旋转、缩放)时,无需重新录制所有 draw 命令,只需修改变换配置即可。这在 Perfetto 中体现为:同一个 `View` 的连续帧,主线程 `draw` 阶段的耗时会明显减少——因为只需修改配置参数,跳过了整个命令录制过程。

2. **硬件层(Hardware Layer)**:将复杂的 `View` 内容缓存为 GPU 纹理,后续帧只需做纹理合成,不再重复光栅化。适合频繁做动画但内容不变的 `View`。

3. **GPU 加速的 Canvas**:`Canvas` 的绘制操作不再走 Skia 软件路径,而是通过 OpenGL ES 驱动 GPU 完成。常见操作如 `drawRect`、`drawBitmap`、`clipPath` 等被编译为 GL 命令。

不过 Android 3.0 主要是面向平板的过渡版本,硬件加速需要开发者手动开启。

> [已验证: L2 - developer.android.com/guide/topics/graphics/hardware-accel]

### Android 4.0 ICS:默认开启

Android 4.0 Ice Cream Sandwich(API 14,2011 年)将硬件加速设为 **所有 targetSdk ≥ 14 应用的默认行为**。开发者不再需要手动添加 `android:hardwareAccelerated="true"`,GPU 渲染成为 Android UI 的标准路径。

Android 4.0 同时要求搭载该版本的设备在硬件层面支持 GPU 加速的 2D 绘制——这部分取决于 SoC 的 GPU 能力,而非单纯由 Android 版本决定。对 `targetSdk ≥ 14` 的应用,硬件加速是默认行为;对更低 targetSdk 的应用,仍需手动开启或依赖设备兼容策略。

> [已验证: L2 - developer.android.com/about/versions/android-4.0-highlights]

## Project Butter 与 VSync/Choreographer(Android 4.1)

### 60 FPS 的承诺

Android 4.1 Jelly Bean(API 16,2012 年)的 **Project Butter** 是渲染流畅度的一次标志性升级。Google 承诺"vsync 时代的 60 FPS",核心改动有三个:

**Choreographer** 是整个改动的枢纽。它接收来自 SurfaceFlinger 的 VSync 信号(在 Perfetto 中对应 `VSYNC-app`),在信号到来时触发 `doFrame()`。Android 4.1 当年的回调队列是 `INPUT → ANIMATION → TRAVERSAL`;现代 AOSP 在这条顺序中加入了 `INSETS_ANIMATION` 与 `COMMIT`,读现代源码和 Trace 时要把它们看作后续版本演进。`TRAVERSAL` 阶段执行 `performTraversals()`,即 `measure → layout → draw`。

在 Perfetto 中,Choreographer 的调度可以通过 `Choreographer#doFrame` slice 观察。每个 `doFrame` 的开始时间应该紧贴 `VSYNC-app` 信号,如果出现明显延迟,说明主线程被阻塞。

**三重缓冲(Triple Buffering)**:当一帧超过 16.67ms(60Hz)时,双缓冲会导致下一个 VSync 周期也被阻塞(因为 CPU 要等 GPU 释放 Buffer)。三重缓冲引入第三个 Buffer,允许 CPU 在 GPU 仍在渲染上一帧时就开始准备当前帧,减少连续丢帧。

**VSync 信号分发模型**:Project Butter 当年的实现以 `DispSync` 为核心。SurfaceFlinger 从硬件 Composer(HWC)接收硬件 VSync,再推导出两路带 offset 的软件节拍:
- `VSYNC-app`:分发给应用进程的 Choreographer,触发 UI 线程的 measure/layout/draw
- `VSYNC-sf`:分发给 SurfaceFlinger 自身,触发合成

两者的时间偏移(在 Perfetto 中可以观察 `VSYNC-app` 和 `VSYNC-sf` 的间距)决定了 App 渲染和 SF 合成之间的流水线配合。

`DispSync` 的实现方式是:SurfaceFlinger 从 HWC 接收硬件 VSync 中断,用软件模型(基于历史时间戳的线性回归)推导出两路带 offset 的软件节拍。这个模型在 VSync 周期稳定时工作良好,但在刷新率动态切换(如 ARR)或 VSync 偏移需要频繁调整的场景下,线性回归的收敛速度和精度都有限。

Android 12 开始逐步将 `DispSync` 替换为 `VsyncPredictor`。`VsyncPredictor` 使用更灵活的预测算法(支持非线性和突变适应),能更快跟上刷新率切换带来的 VSync 周期变化,这在 Android 15+ 的 ARR 设备上尤为重要。对外接口不变——Perfetto 中仍然是 `VSYNC-app` 和 `VSYNC-sf` 两路节拍,变的是内部预测器的实现。排查 Trace 时不需要区分 `DispSync` 和 `VsyncPredictor`,但读到旧版 AOSP 源码时要知道实现已换。

[图:VSync 信号分发时序图,展示 HWC → DispSync → VSYNC-app/VSYNC-sf 的分发流程与 offset 关系]

[待高爷补充:Perfetto 中 VSYNC-app 和 VSYNC-sf 信号的 Track 截图,标注 offset 间距]

> [已验证: L2 - source.android.com/devices/graphics]



## RenderThread:主线程与 GPU 命令的分离(Android 5.0)

### 为什么需要 RenderThread

在 Android 4.x 中,硬件加速虽然已经默认开启,但 GPU 命令的提交和节流仍然发生在主线程。`draw` 阶段不仅要构建 DisplayList,还要把 GL 命令送进 EGL / GLES 管线。`eglSwapBuffers()` 不保证立即返回:当可用 back buffer 不足、前一帧的 release fence 还没就绪,或 swap interval / VSYNC 节流要求当前线程等待时,它会直接阻塞调用线程。`glFinish()` 则是更强的显式同步,调用点会一直等到此前提交的 GPU 工作全部完成。

在 Android 5.0 之前,这两类等待都可能落在主线程上。排查里看到的 swap stall 往往对应显示管线的 back-pressure,`glFinish()` 只是其中一类显式同步点。Android 5.0 引入 RenderThread 之后,GL 命令提交和大部分 GPU 等待被挪到独立线程,主线程主要保留 UI 树遍历和 DisplayList 录制。

### RenderThread 的工作方式

Android 5.0 Lollipop(API 21,2014 年)引入了 **RenderThread**——一个系统管理的专用渲染线程。

新的流程变成:

1. **主线程**执行 `measure → layout → draw`,在 `draw` 阶段将绘制操作录制到 `DisplayListCanvas`(后改为 `RecordingCanvas`),生成 `RenderNode` 树
2. 主线程将 `RenderNode` 树**同步**到 RenderThread
3. **RenderThread** 独立执行 GPU 命令:遍历 `RenderNode` 树,将 Skia draw 命令转为 GL/Vulkan 调用,提交给 GPU
4. RenderThread 完成 DisplayList 回放和 buffer 提交；帧耗时随后可通过 `FrameMetrics`(App 侧)或 `FrameTimeline` / Perfetto(系统侧)观察

在 Perfetto 中,`UI Thread` 和 `RenderThread` 是两个独立的 Track。`UI Thread` 上的 `performTraversals` 结束后,`RenderThread` 上的 `DrawFrame` 才开始执行 GPU 工作。如果 `DrawFrame` 耗时长,但 `UI Thread` 已经空闲,说明 GPU 是瓶颈,而非主线程代码问题。反过来,如果 `DrawFrame` 还没开始,`UI Thread` 上的 `performTraversals` 就已经超了帧预算,那瓶颈在主线程的 measure/layout/draw——RenderThread 再快也救不回来。

[图:Perfetto 中 UI Thread 与 RenderThread 的 Track 分离示意图,标注 performTraversals 和 DrawFrame 的时序关系]

[待高爷补充:Android 5.0+ 设备的 Perfetto Trace 截图,清晰展示 UI Thread 与 RenderThread Track 分离]

RenderThread 能独立推进的,是 `RenderNodeAnimator` 和基于 `CanvasProperty` 的 RT animation。`RippleDrawable`、circular reveal 一类效果走这条路时,启动后可以继续在 RenderThread 上推进。普通 `ObjectAnimator`、`ValueAnimator`、`ViewPropertyAnimator` 仍由 UI 线程的 `Choreographer` 驱动;它们只是把结果写回 `RenderNode`,再由 RenderThread 去绘制。主线程一旦卡住,这类动画也会一起掉帧。

> [已验证: L2 - developer.android.com/about/versions/android-5.0-changes, AOSP frameworks/base/libs/hwui/renderthread]

## HWUI 后端演进:OpenGL ES → SkiaGL → SkiaVulkan

HWUI 的 GPU 后端经历了一条清晰的替换路径:

### OpenGL ES 直接后端(Android 3.0 ~ 7.x)

最初的 HWUI 直接使用 OpenGL ES 2.0 API 作为渲染后端。`GLES20Canvas`(后改名为 `DisplayListCanvas`)将 `Canvas` 的 draw 命令直接编译为 GL 调用。Skia 仍然存在,但只在特定场景(如路径光栅化)中被调用。

### SkiaGL 后端(Android 8.0 测试,9.0 默认)

Android Oreo(8.0)开始测试将 Skia 作为统一的渲染后端,通过 Skia 的 OpenGL ES 后端(`SkiaGL`,内部使用 `SKIA_GL_THREADED`)执行所有 2D 绘制。Android Pie(9.0)正式将 SkiaGL 设为默认路径。

这个改动简化了架构:HWUI 不再直接管理 OpenGL ES 上下文,而是将所有绘制命令交给 Skia,由 Skia 统一调度 GPU。好处是 Skia 团队可以独立优化渲染管线,无需 HWUI 逐版本调整 GL 调用。

### Skia Graphite:方向性后端演进

Skia 的下一代渲染后端 **Graphite** 是 Skia 团队的长期演进方向。Graphite 对渲染管线的设计思路是:将传统的 Back-to-Front(画家算法)绘制顺序改为 **Front-to-Back**,配合 GPU 硬件的 **Early-Z 深度测试**,跳过被遮挡像素的片元着色。

传统画家算法下,GPU 按从后到前的顺序逐层绘制,每一层都会实际执行片元着色并写入颜色缓冲。被遮挡的像素白白消耗了 GPU 算力。Graphite 的设计是先画前面的层,深度缓冲记录已写入像素的深度值;后续层在着色前先做 Early-Z 测试,如果当前像素深度更大(被遮挡),直接跳过着色。

**当前启用状态**:截至 AOSP android-16.0.0_r1,`frameworks/base/libs/hwui/pipeline/skia/` 目录下只有 SkiaOpenGLPipeline、SkiaVulkanPipeline、SkiaGpuPipeline 等 HWUI 后端,未检出 Graphite 后端或 HWUI 侧的启用路径。Graphite 是 Skia 方向上的重要能力,但 Android 应用 UI 渲染是否默认走 Graphite,取决于后续版本的 HWUI 集成进度和设备厂商的驱动适配,不能假设 Android 16 设备已统一启用。开发者应关注 HWUI 后端选择逻辑来判断实际使用的渲染管线:`adb shell getprop debug.hwui.renderer` 返回当前后端(`skiagl` / `skiavk` / `angle` 等),`adb shell getprop ro.hwui.renderer` 返回系统默认值。如果返回空或 `skiagl`,说明设备仍走 OpenGL ES 后端;返回 `skiavk` 则是 Vulkan 后端。

### SkiaVulkan 后端(Android 10+ 可测试,2024+ 扩大部署)

Skia 同时实现了 Vulkan GPU 后端。从 Android Q(10.0)开始,开发者可以通过调试参数启用 `SkiaVulkan` 管线。到 2024 年,新芯片组开始默认使用 SkiaVulkan 后端。

Vulkan 后端相比 OpenGL ES 的具体改进:
- **减少驱动侧隐式开销**:Vulkan 的命令缓冲区(Command Buffer)允许多线程并行构建和提交 GPU 命令,减少 OpenGL ES 驱动层的隐式状态验证和同步等待。不同 SoC、驱动版本和 workload 的收益差异很大,正文不保留缺少测试条件的百分比结论
- **显式内存管理**:应用可以精确控制 GPU 内存的分配时机(通过 `VkAllocateMemory`)、绑定和释放,而非依赖 GL 驱动的隐式管理。内存生命周期与帧调度因此可以精确配合,减少显存浪费
- **扩展图形特性集**:Vulkan 1.1+ 提供计算着色器(Compute Shader)、多通道渲染(Multi-pass Rendering)、异步计算队列等 OpenGL ES 3.x 不具备或受限的能力

> [已验证: L2 - developer.android.com/ndk/guides/graphics, skia.org, XDA-developers.com]

### Vulkan 兼容性要求

- Android 10(API 29):64 位设备必须支持 Vulkan 1.1
- Android 13(API 33):新设备必须支持 Vulkan 1.3
- Android 16（API 36）：新设备必须支持 Vulkan 1.4（CDD 平台要求）。Khronos 为此定义了两层 profile：① **VP_ANDROID_16_minimums**（Android 16 最低要求 profile），profile api-version 为 1.3.276，强制扩展包括 `VK_EXT_host_image_copy` 等，代表 Android 16 设备准入的最低 Vulkan 能力；② **VP_ANDROID_vulkan_profile_2025**（Android Vulkan Profile 2025），profile api-version 为 1.1.128，代表在 Android 设备上广泛支持的兼容性 profile。两者是不同层面的要求：Vulkan 1.4 是新设备准入门槛；VP_ANDROID_16_minimums 是 CDD 侧的最低强制扩展集；VP_ANDROID_vulkan_profile_2025 是跨版本广泛兼容的推荐 profile。

## BLASTBufferQueue:统一的 Buffer 管理(Android 11+)

### 从 BufferQueue 到 BLASTBufferQueue

在 Android 10 及之前,App 进程与 SurfaceFlinger 之间的 Buffer 流转通过 `BufferQueue` 管理。`BufferQueue` 的设计存在一些问题:当多个 App 进程同时提交 Buffer 时,窗口几何变化(如旋转、resize)和 Buffer 内容的同步缺乏统一机制,可能导致 ANR(因为 View 事务已更新但 Buffer 回调未释放)。

**BLASTBufferQueue**(BLAST = Buffer Layer Async Synced Transfer)在 Android 11(API 30)开始进入主线:`ViewRootImpl` 中的 `mBlastBufferQueue` 在 AOSP android-11.0.0_r1 已可见,主窗口路径率先迁移。Android 12(API 31)的重点是 FrameTimeline/VSyncId/窗口同步观测口径的完善,以及 BLAST 覆盖范围从主窗口扩展到更多 Surface 类型。

### BLASTBufferQueue 的核心改进

1. **Buffer 与 Transaction 绑定提交**:BLAST 将 buffer 与 `SurfaceControl.Transaction` 绑定到同一帧边界提交,改善了几何变化(位置/大小/裁剪)与 buffer 内容的同步。buffer 复用等待仍由 BufferQueue slot 与 release fence 决定——当 slot 耗尽或 release fence 未 signal 时,App 在 `dequeueBuffer` 仍可能被 back-pressure 卡住。
2. **多进程同步优化**:当多个 App 进程向同一个 SurfaceFlinger 提交内容时,`BLASTBufferQueue` 提供了更健壮的同步机制

在 Perfetto 中,这个变化主要体现在 Buffer 流转相关的事件和 Fence 时间线上。如果仍沿用 Android 11 及之前的 `BufferQueue` Track 经验,在 Android 12+ 上需要关注 `BLASTBufferQueue` 相关的 slice。实际排查中,如果 Android 12+ 设备的 Trace 里出现 `dequeueBuffer` 等待时间异常拉长,不要急着按旧经验去查 BufferQueue slot 状态——先确认走的是 BLAST 路径还是旧路径,再决定排查方向。

[图:Android 11 BufferQueue 与 Android 12 BLASTBufferQueue 的 Buffer 流转对比示意图]

[待高爷补充:可用文字流程图 + Perfetto 中 BufferQueue/BLASTBufferQueue 相关 slice 截图]

> [已验证: L2 - source.android.com/devices/graphics, AOSP frameworks/native/libs/gui/BLASTBufferQueue.cpp]

## Android 16:图形 API 演进

### Vulkan 的地位提升

Android 16 在图形 API 方面有几个变化,但需要把不同层面拆开看。

**Vulkan Profile 要求加严。** Android 16 对新设备提出了更高的 Vulkan 能力要求：新设备必须支持 Vulkan 1.4，并满足 `VP_ANDROID_16_minimums` profile 的强制扩展集（如 `VK_EXT_host_image_copy`）。这是对新设备的能力门槛，不等于现有设备的 OpenGL ES App 自动切换到 Vulkan 后端。`VP_ANDROID_vulkan_profile_2025` 是另一层面向广泛设备兼容的 profile，两者不要混用。

**OpenGL ES 进入维护模式。** Khronos 已明确 OpenGL ES 不再接受新特性开发。但"OpenGL ES 进入维护模式"和"ANGLE 系统级翻译已默认启用"是两件事。ANGLE 在 Android 上的部署状态取决于设备厂商和系统配置,不能写成 Android 16 的统一行为。

**ANGLE 的实际部署情况。** ANGLE(Almost Native Graphics Layer Engine)是一个将 OpenGL ES 调用翻译为 Vulkan 的兼容层,Google 在多个版本中持续推动其集成。但截至 Android 16,ANGLE 的系统级启用仍受设备白名单和系统属性控制,不是所有 OpenGL ES App 的调用都默认经过 ANGLE 翻译。排查时可通过 `adb shell getprop persist.graphics.angle.enabled` 和 `adb shell dumpsys gfxinfo` 确认当前设备的 ANGLE 状态。

对开发者的影响:
- 新设备需要满足 `VP_ANDROID_16_minimums` 的 Vulkan 最低能力要求
- 游戏和图形密集型应用应优先使用 Vulkan API
- OpenGL ES App 不需要改代码,但不要假设系统已自动切换到 ANGLE/Vulkan 后端
- 可通过 `VP_ANDROID_vulkan_profile_2025`（Android Vulkan Profile 2025）确保跨版本设备兼容性

### AGSL 图形着色能力增强

Android 16 把 **AGSL**(Android Graphics Shading Language)从 `RuntimeShader` 继续扩展到 `RuntimeColorFilter` 和 `RuntimeXfermode`。这两个类分别对应颜色过滤阶段与 source/destination 混合阶段,适合写阈值、褐色调、自定义混合等效果。

```java
// 示例:使用 Android 16 的 RuntimeColorFilter
RuntimeColorFilter filter = new RuntimeColorFilter(
    "vec4 main(half4 inColor) {\n" +
    "  return vec4(inColor.rgb * half3(1.0, 0.9, 0.8), inColor.a);\n" +
    "}"
);
paint.setColorFilter(filter);
canvas.drawRect(rect, paint);
```

`RuntimeShader` 仍用于生成着色结果;`RuntimeColorFilter` 处理的是上一阶段已经算出的颜色;`RuntimeXfermode` 处理 source / destination 的混合。三者在管线里的位置不同,代码示例也应分开写。

### 自适应刷新率(ARR)

Android 15 引入、Android 16 进一步完善的 **自适应刷新率**(Adaptive Refresh Rate, ARR)是渲染管线的又一次重大变革。

ARR 将**显示刷新率与内容帧率解耦**:内容只有 30 FPS 时,系统可以把刷新率压到相同或接近的档位;用户开始滚动时,再回到高刷新率。对支持 1Hz-120Hz 之类大范围降频的 LTPO 面板,静态阅读或停留场景把刷新率从高档降到 10Hz 以下时,显示侧功耗通常能降到原先的一半左右,具体幅度取决于面板、亮度、DDIC 和 SoC。

实现要求:
- 硬件:支持离散或自适应步进的显示面板
- 系统:HWC HAL v3(`android.hardware.graphics.composer3`)承接 ARR 管线
- 公共 API 分工:
  - `Display.hasArrSupport()` 用于判断设备是否支持 ARR,`Display.getSuggestedFrameRate(int)` 用于按帧率类别查询系统建议值
  - `View.setRequestedFrameRate(float)` 用于内容侧表达目标帧率偏好
  - `Window.setFrameRatePowerSavingsBalanced(boolean)` 用于窗口级调整功耗与流畅度之间的平衡策略

应用把目标帧率告诉系统之后,是否真的切到对应档位,仍由系统按电量、温度、面板能力和当前场景统一决策。

在 Perfetto 中,ARR 的变化体现在 **`VSYNC-app` 信号不再固定间隔**。当 App 请求 30 FPS 时,`VSYNC-app` 的周期间隔会变为约 33.3ms 而非 8.33ms(120Hz)。这让 Perfetto 分析需要更仔细地识别帧率切换场景。拿到一份 ARR 设备的 Trace 时,先检查 VSync 间隔是否在切换;如果帧率档位变了,对应的帧预算也要跟着换。

[图:ARR 开启前后 VSYNC-app 信号间隔对比,展示 120Hz→30Hz 切换时的 Trace 表现]

[待高爷补充:支持 ARR 的设备上 VSYNC-app 间隔动态变化的 Perfetto 截图]

> [已验证: L2 - developer.android.com/about/versions/16/features, developer.android.com/about/versions/15/features]

## Choreographer 与 FrameMetrics API 的演进

### Choreographer 的版本变化

从 Android 4.1 引入到 Android 16,Choreographer 的核心职责未变——在 VSync 信号到来时调度帧工作。但实现细节在持续优化:

- Android 4.1:引入 `Choreographer`,VSync 信号通过 `DisplayEventReceiver` 的 native 层接收
- Android 5.0:与 RenderThread 协作,`doFrame()` 的 `CALLBACK_COMMIT` 阶段将帧提交给 RenderThread
- Android 16:配合 ARR,Choreographer 需要适应动态的 VSync 周期,帧节奏库(Frame Pacing Library / Swappy)也相应更新

### FrameMetrics API:量化每一帧的"慢"在哪里

分析卡顿时,核心冲突在于:"这帧为什么超了 16.67ms"。FrameMetrics 就是回答这个问题的工具——它把一帧的完整生命周期划分为多个阶段,标出时间究竟花在哪里。

FrameMetrics 在 Android 7.0(API 24)引入,通过 `Window.addOnFrameMetricsAvailableListener()` 注册回调,系统会在每帧渲染完成后回调一次,附带该帧各阶段的精确耗时。开发者不需要在代码里手动打点,就能拿到完整的帧耗时分布。

FrameMetrics 将一帧的渲染划分为以下阶段:

| 阶段 | 含义 |
|------|------|
| `INTENDED_VSYNC_TIMESTAMP` | 本帧期望的 VSync 时间 |
| `UNKNOWN_DELAY_DURATION` | 未知延迟 |
| `INPUT_HANDLING_DURATION` | Input 事件处理耗时 |
| `ANIMATION_DURATION` | 动画计算耗时 |
| `LAYOUT_MEASURE_DURATION` | measure + layout 耗时 |
| `DRAW_DURATION` | draw(录制 DisplayList)耗时 |
| `SYNC_DURATION` | 主线程与 RenderThread 同步耗时 |
| `COMMANDS_DURATION` | RenderThread 执行 GPU 命令耗时 |
| `SWAP_BUFFERS_DURATION` | 提交 Buffer 耗时 |
| `TOTAL_DURATION` | 总耗时 |

实际分析通常关注两个层面:

第一是**单帧瓶颈定位**。如果 `LAYOUT_MEASURE_DURATION` 占比最高,说明 View 层级过深或 layout 逻辑过重;如果 `COMMANDS_DURATION` 高,说明 GPU 是瓶颈;如果 `SYNC_DURATION` 异常,可能是主线程和 RenderThread 之间的同步出了问题(常见于大量 RenderNode 变更的场景)。

第二是**整体帧率趋势**。通过持续收集 FrameMetrics 数据,可以建立帧耗时的时间线,发现哪些场景出现规律性 Jank。Android 12 的 `FrameTimeline` Track 在 Perfetto 中直观地展示了这一点——每一帧都有"预期完成时间"和"实际完成时间"的对比,绿色表示准时,红色表示 Jank。FrameMetrics 的阶段数据与 FrameTimeline 的视觉表现结合起来,就能精确定位 Jank 的根因。

FrameMetrics 只在 App 进程内可用(它是 per-window 的 API)。如果要分析系统级的帧率问题(如 SurfaceFlinger 合成延迟),需要结合 Perfetto Trace 中的 SurfaceFlinger Track 和 FrameTimeline 数据。

<!-- AIW-源码调研-2026-04-18: FrameTimeline 机制补充 - 基于 AOSP android-14 源码调研 -->

### FrameTimeline:系统级 Jank 检测框架(Android 12+)

FrameTimeline 是 Android 12 引入的 SurfaceFlinger 内置系统级 Jank 检测框架,本章前文多次引用但未展开解释。它的核心价值是提供「预期帧时间 vs 实际帧时间」的精确对比,是 Perfetto 中渲染性能分析的基石。

#### 核心数据结构

FrameTimeline 围绕三个核心类展开:

**TimelineItem**:最小时间单元,记录一帧的时间点:
```cpp
// frameworks/native/services/surfaceflinger/FrameTimeline/FrameTimeline.h
struct TimelineItem {
    int64_t startTime;        // 帧工作开始时间(nano)
    int64_t endTime;          // 帧工作结束时间
    int64_t presentTime;      // 实际呈现时间
    int64_t desiredPresentTime; // 期望呈现时间
};
```

**SurfaceFrame**:App 侧渲染一帧的工作。每个 App 进程产生自己的 SurfaceFrame,通过 `display_frame_token` 与 DisplayFrame 关联。

**DisplayFrame**:SurfaceFlinger 合成一帧的工作。内部维护两个 TimelineItem:
- `mSurfaceFlingerPredictions` - SF 的预期时间线(包含 Composer + DisplayHAL)
- `mSurfaceFlingerActuals` - SF 的实际时间线(帧处理过程中逐步更新)

一个 DisplayFrame 可以对应多个 SurfaceFrame(多窗口场景),关系通过 `SurfaceFrame.display_frame_token` 重建。

#### TokenManager 与 vsyncId 生成

`TokenManager` 负责给预测时间线生成 vsyncId,并在短时间内保存这组 prediction。android-14.0.0_r1 与 android-16.0.0_r1 中,`TokenManager` 声明在 `FrameTimeline.h` 内;AOSP 对应版本没有独立的 `TokenManager.h`。

```cpp
// frameworks/native/services/surfaceflinger/FrameTimeline/FrameTimeline.h
class TokenManager {
public:
    virtual ~TokenManager() = default;

    // Generates a token for the given set of predictions.
    // Stores the predictions for 120ms and destroys it later.
    virtual int64_t generateTokenForPredictions(TimelineItem&& prediction) = 0;

    virtual std::optional<TimelineItem> getPredictionsForToken(int64_t token) const = 0;
};
```

调用关系可以按数据流理解:VSync 预测器先产出一组 `TimelineItem`,`TokenManager::generateTokenForPredictions(TimelineItem&& prediction)` 返回 token,App 侧通过 `Choreographer.FrameTimeline.getVsyncId()` 拿到同一个标识;帧完成后,SurfaceFlinger 再用这个 token 把 App 的 `SurfaceFrame` 与显示侧的 `DisplayFrame` 关联起来。源码注释里 prediction 的保存窗口是 120ms,超过窗口后通过 token 取回 prediction 会进入 expired 分支。

#### PresentState 与 JankType 判定

帧完成时通过 `setPresentState()` 判定:
- `PRESENT_ON_TIME` - 帧在预期时间呈现
- `PRESENT_LATE` - 帧晚于预期(常见 Jank)
- `PRESENT_EARLY` - 帧早于预期(可能过度渲染)
- `PRESENT_UNKNOWN` - 状态未知

Perfetto 中的 `JankType` 定义在 `protos/perfetto/trace/android/frame_timeline_event.proto`,它是一个 bitmask。`JANK_UNSPECIFIED = 0` 只是缺省值,表示原因未知的枚举是 `JANK_UNKNOWN = 256`。

| JankType | 值 | 含义 |
|----------|---|------|
| `JANK_NONE` | 1 | 无 jank |
| `JANK_SF_SCHEDULING` | 2 | SurfaceFlinger 调度导致 |
| `JANK_PREDICTION_ERROR` | 4 | 预测误差 |
| `JANK_DISPLAY_HAL` | 8 | Display HAL / 显示子系统侧延迟 |
| `JANK_SF_CPU_DEADLINE_MISSED` | 16 | SF CPU 侧超时 |
| `JANK_SF_GPU_DEADLINE_MISSED` | 32 | SF GPU 侧超时 |
| `JANK_APP_DEADLINE_MISSED` | 64 | App 错过渲染截止时间 |
| `JANK_BUFFER_STUFFING` | 128 | Buffer stuffing |
| `JANK_UNKNOWN` | 256 | 原因未知 |
| `JANK_SF_STUFFING` | 512 | SurfaceFlinger stuffing |
| `JANK_DROPPED` | 1024 | 帧被丢弃 |

Perfetto 中 Frame Timeline track 的 Actual Timeline 结束时间是 `max(GPU 时间, postTime)`,postTime 是 App 帧发送到 SurfaceFlinger 的时间。

#### vsync-appSf 解耦(Android 13)

Android 13 之前,`vsync-sf` 同时负责唤醒 SurfaceFlinger 合成和部分 Choreographer 客户端。这导致时序歧义。Android 13 引入独立的 `vsync-appSf` 信号,专门服务需要与 SurfaceFlinger 内部状态精确同步的 Choreographer 客户端:

```text
Android 12- : vsync-sf 双重职责
Android 13+ : vsync-sf → 仅唤醒 SF 合成
              vsync-appSf → 专门服务 Choreographer 客户端精确同步
```

#### App 侧 API

`Choreographer.FrameTimeline`(Android 13 / API 33):

```java
// android.view.Choreographer.FrameTimeline
public long getDeadlineNanos();          // 帧必须准备好的截止时间
public long getExpectedPresentationTimeNanos();  // 预期呈现时间
public long getVsyncId();               // 关联 SF 侧时间线的 vsyncId
```

Android 13(API 33)同批新增 NDK API:`AChoreographer_postVsyncCallback()` + `AChoreographerFrameCallbackData_*`,允许 App 从多条候选时间线中选择,再通过 `ASurfaceTransaction_setFrameTimeline()` 通知 SurfaceFlinger。

#### Android 14 对 FrameTimeline 的演进

- `SurfaceFrame` 构造函数新增 `predictionState` 和 `gameMode` 参数(commit `603a15d2`)
- `actualSurfaceFrameStartEvent` 开始设置 `prediction_type`(commit `757f24e3`)
- `Predictor` 类(在 `CompositionEngine/src/planner/`)与 FrameTimeline 深度集成,用于运动预测和 vsync 模拟

#### Perfetto 中的可观测性

Perfetto 中 SurfaceView 的 FrameTimeline 尚未完全支持。DisplayFrame 被选中时,FrameTimeline 会绘制箭头,指向所有被合成进该 DisplayFrame 的 SurfaceFrame(可能跨多进程)。

> [源码: frameworks/native/services/surfaceflinger/FrameTimeline/FrameTimeline.h/cpp (android-14/android-16); perfetto.dev docs; AOSP Gerrit commits 757f24e3, 603a15d2] **[一手:AOSP 源码 + Perfetto 官方文档]**

<!-- /AIW-源码调研-2026-04-18 -->

### Frame Pacing Library(Swappy)

Frame Pacing Library 是 Android Game Development Kit(AGDK)的一部分,专门为游戏场景设计。它通过精确控制 `swap` 时机来确保帧均匀分布:
- 自动检测设备的最佳帧率(如 60/90/120Hz)
- 为短帧补偿等待时间,避免显示重复帧
- 为长帧添加 `present timestamp`,确保在正确的 VSync 周期显示
- 在 ARR 设备上自动适配动态刷新率

Unreal Engine 已集成 Swappy。

> [已验证: L2 - developer.android.com/reference/android/view/FrameMetrics, developer.android.com/games/sdk/frame-pacing]

## 版本演进时间线总览

| 版本 | 年份 | 关键里程碑 | 对 Perfetto 分析的影响 |
|------|------|-----------|----------------------|
| 3.0 | 2011 | HWUI + OpenGL ES 2.0 硬件加速引入 | `RenderNode`(DisplayList)概念诞生 |
| 4.0 | 2011 | 硬件加速默认开启 | GPU 渲染成为基线 |
| 4.1 | 2012 | Project Butter:Choreographer + VSync + 三重缓冲 | `VSYNC-app` / `VSYNC-sf` Track 首次出现 |
| 5.0 | 2014 | RenderThread 引入 | `UI Thread` 与 `RenderThread` 分离为独立 Track |
| 7.0 | 2016 | FrameMetrics API | 可量化每帧各阶段耗时 |
| 8.0 | 2017 | SkiaGL 后端测试 | HWUI 渲染路径变更(OpenGL → SkiaGL) |
| 9.0 | 2018 | SkiaGL 正式默认 | `hwui` Task 线程行为变化 |
| 10 | 2019 | Vulkan 1.1 强制要求(64位) | SkiaVulkan 可测试 |
| 11 | 2020 | BLASTBufferQueue 主窗口迁移 | App 端主窗口 Buffer 流转开始走 BLAST 路径 |
| 12 | 2021 | BLAST 扩展 + FrameTimeline | BLAST 覆盖更多 Surface 类型;FrameTimeline 可精确对比预期/实际帧时间 |
| 13 | 2022 | vsync-appSf 解耦 + AGSL 引入 | Choreographer 同步精度提升;自定义图形着色器可用 |
| 15 | 2024 | ARR 自适应刷新率引入 | `VSYNC-app` 间隔不再固定 |
| 16 | 2025 | VP_ANDROID_16_minimums Vulkan 最低要求 profile + OpenGL ES 维护模式 + ANGLE 持续集成（设备级） + ARR 增强 | Vulkan 1.4 新设备准入 + VP_ANDROID_16_minimums 强制扩展集；帧率动态切换更频繁；Graphite 为 Skia 方向性后端，HWUI 侧启用路径待后续版本 |

> [已验证: Android 16 于 2025 年 6 月 10 日正式发布(稳定版 BP2A.250605.031.A2),确认年份为 2025。验证来源: Wikipedia + androidcentral.com + androidauthority.com。验证时间: 2026-04-03]



## 常见问题与误区

### "硬件加速从 Android 4.0 才开始"——不准确

Android 3.0 就引入了 HWUI 硬件加速,4.0 只是将它设为默认开启。如果分析的是 targetSdk < 14 的老应用,它可能仍在走 CPU 软件渲染路径——在 Perfetto 中表现为 `draw` 阶段没有对应的 GPU 工作,主线程负责全部光栅化。

### "RenderThread 是 App 自己创建的线程"——不是

RenderThread 是 `hwui` 库内部管理的系统线程,每个拥有硬件加速 Window 的进程都会自动创建一个。它不是 `Thread` 的子类,而是通过 native 代码(`renderthread::RenderThread.cpp`)实现的。在 Perfetto 中它的线程名通常是 `RenderThread`。

### "BLASTBufferQueue 在 Android 12 就完全替代了 BufferQueue"——部分替代,且起点是 Android 11

BLASTBufferQueue 的主窗口迁移从 Android 11 就开始了(`ViewRootImpl.mBlastBufferQueue`),Android 12 扩展到更多 Surface 类型并引入 FrameTimeline 观测。BLAST 替代的是 **App 端**与 SurfaceFlinger 之间的 Buffer 流转。SurfaceFlinger 内部以及系统服务之间的 Buffer 管理仍然使用 `BufferQueue`。在 Perfetto 中,两者的 Track 共存是正常的。

**BLAST 与旧 BufferQueue 的关键机制差异**:旧 BufferQueue 中,buffer 的几何属性(位置、大小、裁剪)通过独立的 `setGeometryAppliesWithResize` / `setCrop` 等调用传递,与 buffer 本身的提交是分离的——窗口旋转或 resize 时,几何变化可能比 buffer 内容早到或晚到,导致短暂的帧不一致。BLAST 将 buffer 和 `SurfaceControl.Transaction` 绑定到同一帧边界:几何属性和 buffer 内容在同一个 Transaction 中原子提交,SurfaceFlinger 按帧边界对齐处理。Buffer 生命周期管理也有差异:旧 BufferQueue 的 `dequeueBuffer` 阻塞条件由 slot 数量和 consumer 的 release 速度决定;BLAST 的 `dequeueBuffer` 仍受 slot/fence 约束,但通过 Transaction 绑定,release 时机与 SF 的合成节奏更紧密地耦合——SF 完成一帧合成后才 release 对应的 Transaction 和 buffer。

### "VSync 信号间隔永远固定"——ARR 打破了这个假设

在支持 ARR 的设备上(Android 15+),`VSYNC-app` 的间隔会随内容帧率动态调整。分析 Perfetto Trace 时,如果看到 `VSYNC-app` 间隔在 8.33ms 和 33.3ms 之间跳变,这不是异常,而是 ARR 在工作。需要结合 `FrameTimeline` Track 来判断帧是否准时完成,而非单纯看 VSync 间距。

### "FrameMetrics 能分析系统级问题"——不能

FrameMetrics 是 per-window、per-process 的 API,只能报告当前 App 进程内某一帧的各阶段耗时。如果要分析 SurfaceFlinger 合成延迟、HWC 行为等系统级问题,必须使用 Perfetto Trace。两者的定位完全不同:FrameMetrics 用于 App 端自省,Perfetto 用于全系统分析。

## 参考资料

### AOSP 源码路径
- `frameworks/base/libs/hwui/` - HWUI 渲染引擎(含 RenderThread、RenderNode)
- `frameworks/base/core/java/android/view/Choreographer.java` - Choreographer 实现
- `frameworks/base/core/java/android/view/FrameMetrics.java` - FrameMetrics API
- `frameworks/native/libs/gui/BLASTBufferQueue.cpp` - BLASTBufferQueue 实现
- `external/perfetto/protos/perfetto/trace/android/frame_timeline_event.proto` - FrameTimeline `JankType` bitmask 定义
- `frameworks/base/graphics/java/android/graphics/RuntimeColorFilter.java` - Android 16 AGSL color filter API
- `frameworks/base/graphics/java/android/graphics/RuntimeXfermode.java` - Android 16 AGSL xfermode API
- `frameworks/base/core/java/android/view/Display.java` - ARR 公共 API(`hasArrSupport()` / `getSuggestedFrameRate()`)
- `frameworks/base/core/java/android/view/Window.java` - Window 级 ARR 偏好设置
- `frameworks/native/services/surfaceflinger/FrameTimeline/` - FrameTimeline 系统(Jank 检测框架)
  - `FrameTimeline.h/cpp` - FrameTimeline / DisplayFrame / SurfaceFrame 主实现;`TokenManager` 声明也在 `FrameTimeline.h`,`generateTokenForPredictions(TimelineItem&&)` 负责生成 vsyncId
- `frameworks/native/services/surfaceflinger/` - SurfaceFlinger 合成逻辑

> [已验证: 上述源码路径经 web 搜索验证,在 android-16.0.0_r1 分支中存在。hwui 目录下可见 StatsUtils.cpp、AutoBackendTextureRelease.cpp、JankTracker.cpp 等文件;Choreographer.java、FrameMetrics.java、BLASTBufferQueue.cpp、SurfaceFlinger/ 均为 AOSP 稳定路径,跨版本未变。验证时间: 2026-04-03]

### 官方文档
- [Hardware Acceleration](https://developer.android.com/guide/topics/graphics/hardware-accel)
- [Android Versions](https://developer.android.com/about/versions)
- [Android 16 Features](https://developer.android.com/about/versions/16/features)
- [Graphics Architecture](https://source.android.com/devices/graphics)
- [Frame Pacing Library](https://developer.android.com/games/sdk/frame-pacing)
- [FrameMetrics API](https://developer.android.com/reference/android/view/FrameMetrics)
- [Vulkan on Android](https://developer.android.com/ndk/guides/graphics)

## 总结

回看这段从 Android 3.0 到 16 的渲染演进,有一条清晰的线索:**把更多工作交给 GPU,把主线程解放出来**。

最初,CPU 包揽了从 Measure/Layout/Draw 到像素生成的全部工作。OpenGL ES 硬件加速把像素生成交给了 GPU;RenderThread 把 GPU 命令提交从主线程剥离出去;SkiaGL/SkiaVulkan 统一了 GPU 后端;BLASTBufferQueue 让 Buffer 提交变成异步操作。每一步都在减轻主线程的负担——这也是为什么在 Perfetto 中,现代 Android 的主线程 `performTraversals` 可以非常短:它只需要录制 RenderNode,GPU 工作全部在 `RenderThread` Track 上执行。

另一条线索是**渲染节奏从固定到自适应**。Project Butter 确立了 VSync 驱动 60 FPS 的模型,但固定刷新率在高帧率设备上浪费功耗。ARR 让刷新率跟随内容帧率动态调整,`VSYNC-app` 不再是均匀的节拍器。Perfetto 分析也需要相应调整:不能只看 VSync 间隔是否均匀,还要结合 `FrameTimeline` 判断帧是否在预期时间内完成。

理解这些版本差异,是分析 Perfetto Trace 的前提条件。下面是几个在实战中踩过的版本认知坑。

**坑 1：对着 Android 12+ 的 Trace 找 "BufferQueue" slice。** Android 11 起主窗口路径逐步迁移到 BLASTBufferQueue，Android 12 后覆盖范围扩大。旧版 Perfetto 教程里提到的 `BufferQueue` Track 在新设备上可能只剩副窗口或系统内部路径。如果盯着一个已经不存在的 Track 做分析，结论必然跑偏。排查时先确认设备版本，再决定用哪个 Buffer 管理概念去解读 Trace。

**坑 2:认为 VSYNC-app 间隔永远是固定值。** 在支持 ARR 的设备(Android 15+)上,当 App 请求 30 FPS 时,`VSYNC-app` 间隔会从 8.33ms(120Hz)跳到 33.3ms(30Hz)。如果仍然按"每 16.67ms 一个 VSync"的经验去判断是否掉帧,会把 ARR 正常的帧率切换误判为渲染异常。遇到 VSync 间隔不均匀时,先检查 `FrameTimeline` Track 里对应帧的 `PRESENT_ON_TIME` 状态,再下结论。

**坑 3:在 Android 4.x 的 Trace 里找 RenderThread。** RenderThread 从 Android 5.0 才引入。如果分析的是一台跑 Android 4.4 的老设备,GPU 命令提交仍在主线程上。这时候 `performTraversals` 里面会包含 `eglSwapBuffers` 的等待——这是 Android 4.x 架构下 GPU 同步的必然行为,拿 Android 5.0+ 的 RenderThread 模型去套就会误判。

`RenderThread` Track 从 Android 5.0 才存在；`BLASTBufferQueue` 主窗口迁移从 Android 11 开始，Android 12 后覆盖范围扩大；ARR 设备上的 `VSYNC-app` 间隔会动态变化。拿到一份 Trace 的第一件事，是确认设备系统版本，再决定用哪套概念模型解读。
