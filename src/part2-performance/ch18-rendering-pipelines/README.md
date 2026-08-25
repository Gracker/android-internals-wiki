# 第 18 章：渲染管线专题

Android 渲染没有一条适用于所有场景的固定流水线。分析前，先确认由谁生产 buffer（Producer）、数据写入哪个 Surface、layer（合成图层）如何组织，以及合成发生在应用内部、SurfaceFlinger 的 GPU 路径还是 HWC 硬件路径，再进入对应专项。框架名、控件名或某个很长的 trace slice（追踪时间区间），都不能代替对实际对象和调用路径的确认。

## 内容索引

- [18.1 Android View 渲染管线与分析方法](01-android-view-pipeline-analysis.md)
- [18.2 Android 软件、离屏与混合渲染路径](02-android-software-offscreen-mixed-rendering.md)
- [18.3 SurfaceView 与 TextureView 渲染管线](03-surfaceview-textureview-pipelines.md)
- [18.4 OpenGL ES、EGL 与 ANGLE](04-opengl-egl-angle.md)
- [18.5 Vulkan 原生管线与 HWUI 多队列](05-vulkan-hwui-multi-queue.md)
- [18.6 SurfaceControl 与 HardwareBufferRenderer](06-surfacecontrol-hardwarebuffer-renderer.md)
- [18.7 Flutter 渲染管线：Engine、Impeller 与 Surface](07-flutter-rendering-pipeline.md)
- [18.8 Jetpack Compose 渲染管线：Composition、Layout 与 RenderNode](08-compose-rendering-pipeline.md)
- [18.9 Android 17 WebView 渲染管线](09-webview-rendering.md)
- [18.10 Android Camera 平台管线：HAL3、Buffer、ZSL 与显示](10-camera-pipeline.md)
- [18.11 视频 Overlay、Media3 与专业编解码管线](11-video-overlay-media3-codec-pipeline.md)
- [18.12 Android 17 游戏引擎渲染链路](12-game-engine.md)
- [18.13 Android 17 EyeDropper API 与跨设备协作性能](13-eyedropper-crossdevice.md)
- [18.14 Android 17 / Android XR 空间 UI 与环境资产渲染性能](14-android-xr-spatial-ui-rendering.md)
- [18.15 Android 17 Jetpack WebGPU 渲染与计算管线](15-webgpu-android-pipeline.md)

## 阅读建议

- 普通 View 先读 [18.1 Android View 渲染管线与分析方法](01-android-view-pipeline-analysis.md)；Flutter 或 Compose 再进入 [18.7](07-flutter-rendering-pipeline.md)。
- Surface、图形 API 与多 layer：按 [18.2](02-android-software-offscreen-mixed-rendering.md) → [18.3](03-surfaceview-textureview-pipelines.md) → [18.4](04-opengl-egl-angle.md) / [18.5](05-vulkan-hwui-multi-queue.md) → [18.6](06-surfacecontrol-hardwarebuffer-renderer.md) 阅读。
- 视频、Camera 与游戏：分别从 [18.10 Android Camera 平台管线：HAL3、Buffer、ZSL 与显示](10-camera-pipeline.md)、[18.11 视频 Overlay、Media3 与专业编解码管线](11-video-overlay-media3-codec-pipeline.md)、[18.12 Android 17 游戏引擎渲染链路](12-game-engine.md) 切入；刷新率联动问题再补 [2.2 帧率、刷新率与显示模式选择](../../part1-fundamentals/ch02-rendering/02-framerate-refresh-display-mode.md)。
- 任一性能问题都回到 [18.1 Android View 渲染管线与分析方法](01-android-view-pipeline-analysis.md#统一分析方法)，沿同一帧的时间线核对 Producer、BufferQueue（缓冲区队列）、fence（表示操作完成或资源可用的同步信号）、SurfaceFlinger、HWC（硬件合成器）与 present（帧呈现）事件。

原独立 PiP/Freeform 与多窗口管线正文已并入 2.10，原独立分析方法正文已并入 18.1；其余专项保持一篇一主题。
