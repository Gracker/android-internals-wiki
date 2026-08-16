# 第 18 章：渲染管线专题

Android 渲染没有一条适用于所有场景的固定流水线。分析前，先确认由谁生产 buffer（Producer）、数据写入哪个 Surface、layer（合成图层）如何组织，以及合成发生在应用内部、SurfaceFlinger 的 GPU 路径还是 HWC 硬件路径，再进入对应专项。框架名、控件名或某个很长的 trace slice（追踪时间区间），都不能代替对实际对象和调用路径的确认。

## 内容索引

- [18.1 渲染管线分类、选型与分析方法](01-pipeline-overview.md)
- [18.2 Android View 标准管线（BLAST 深入）](02-android-view-standard.md)
- [18.3 Android 17 软件与离屏渲染路径](03-android-view-software.md)
- [18.4 Android 17 混合渲染链路](04-android-view-mixed.md)
- [18.5 Android 17 多窗口、PiP 与自由窗口渲染](05-android-view-multi-window.md)
- [18.6 Android 17 SurfaceView 独立 Surface 路径](06-surfaceview.md)
- [18.7 Android 17 TextureView 宿主合成链路](07-textureview.md)
- [18.8 Android 17 EGL / OpenGL ES 渲染链路](08-opengl-es.md)
- [18.9 Android 17 Vulkan 原生渲染管线](09-vulkan-native.md)
- [18.10 Android 17 SurfaceControl NDK API](10-surface-control-api.md)
- [18.11 Android 17 ANGLE（GLES-over-Vulkan 翻译层）](11-angle-gles-vulkan.md)
- [18.12 Android 17 Flutter 渲染管线](12-flutter-rendering.md)
- [18.13 Android 17 WebView 渲染管线](13-webview-rendering.md)
- [18.14 Android 17 Camera 渲染管线](14-camera-pipeline.md)
- [18.15 Android 17 视频叠加与 HWC](15-video-overlay-hwc.md)
- [18.16 Android 17 游戏引擎渲染链路](16-game-engine.md)
- [18.17 Android 17 HardwareBufferRenderer](17-hardware-buffer-renderer.md)
- [18.18 Android 17 可变刷新率（ARR/VRR）渲染管线](18-variable-refresh-rate.md)
- [18.19 Android 17 EyeDropper API 与跨设备协作性能](19-eyedropper-crossdevice.md)
- [18.20 Android 17 / Android XR 空间 UI 与环境资产渲染性能](20-android-xr-spatial-ui-rendering.md)
- [18.21 Android 17 多媒体播放管线：Codec2、Tunneled Playback 与 Media3 ABR](21-media-codec2-tunneled-media3-abr.md)
- [18.22 Android 17 Advanced Professional Video 与专业视频编解码管线](22-advanced-professional-video-apv.md)
- [18.23 Android 17 Jetpack Compose 渲染管线架构](23-compose-rendering-pipeline.md)
- [18.24 Android 17 HWUI Vulkan 多队列并行渲染与帧边界管理](24-android17-hwui-vulkan-multi-queue.md)
- [18.25 Android 17 Jetpack WebGPU 渲染与计算管线](25-webgpu-android-pipeline.md)

## 阅读建议

- 普通 View 或 Compose：先读 [18.1](01-pipeline-overview.md)，再按 [18.2](02-android-view-standard.md) → [18.23](23-compose-rendering-pipeline.md) 进入具体框架。
- Surface、图形 API 与多 layer：按 [18.4](04-android-view-mixed.md) → [18.6](06-surfaceview.md) / [18.7](07-textureview.md) → [18.8](08-opengl-es.md) / [18.9](09-vulkan-native.md) → [18.10](10-surface-control-api.md) 阅读。
- 视频、Camera 与游戏：分别从 [18.14](14-camera-pipeline.md)、[18.15](15-video-overlay-hwc.md)、[18.16](16-game-engine.md) 切入，再补 [18.18](18-variable-refresh-rate.md) 和 [18.21](21-media-codec2-tunneled-media3-abr.md)。
- 任一性能问题都回到 [18.1 的统一分析方法](01-pipeline-overview.md#统一分析方法)，沿同一帧的时间线核对 Producer、BufferQueue（缓冲区队列）、fence（表示操作完成或资源可用的同步信号）、SurfaceFlinger、HWC（硬件合成器）与 present（帧呈现）事件。

原独立 PiP/Freeform 正文已并入 18.5，原独立分析方法正文已并入 18.1；其余专项保持一篇一主题。
