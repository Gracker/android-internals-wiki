# 第 22 章：渲染优化实战

渲染优化需要把布局、绘制、动画、图片、列表和页面切换放进同一帧预算中分析。帧预算是当前刷新周期留给一帧按时完成的时间：60 Hz 下约为 16.7 ms，120 Hz 下约为 8.3 ms；设备采用动态刷新率时，应以实际帧时间线为准。改动要用 Perfetto 或 System Trace（记录线程、渲染和系统事件的时间线）以及线上卡顿率验证。

[第 2 章](../../part1-fundamentals/ch02-rendering/README.md)和[第 18 章](../../part2-performance/ch18-rendering-pipelines/README.md)分析系统渲染管线，[第 7 章](../../part2-performance/ch07-smoothness/README.md)讨论卡顿定位；这里聚焦 View、Jetpack Compose、WebView、Flutter、视频播放和 CameraX 等 App 侧场景。

## 内容索引

- [22.1 View 布局与自定义绘制优化](01-view-layout-custom-drawing.md)
- [22.2 RecyclerView 与 Compose LazyList 性能](02-recyclerview-compose-lazylist.md)
- [22.3 Compose 性能、Compiler 与 Modifier.Node 诊断](03-compose-compiler-modifier-diagnostics.md)
- [22.4 View、Compose 动画与共享元素性能](04-view-compose-animation-shared-transition.md)
- [22.5 图片加载、Bitmap 解码与 RenderNode](05-image-bitmap-rendernode.md)
- [22.6 WebView 性能优化实战](06-webview-optimization.md)
- [22.7 帧率监控与线上卡顿治理](07-frame-monitoring.md)
- [22.8 Runtime 图形效果与 Compose Canvas](08-runtime-effects-compose-canvas.md)
- [22.9 Fragment、Predictive Back 与 Navigation Compose 页面切换](09-fragment-predictive-back-navigation.md)
- [22.10 自适应布局、桌面窗口与多形态设备性能](10-adaptive-layout-multi-form-factor.md)
- [22.11 Compose First 与 View/Compose 互操作性能实战](11-compose-view-interop.md)
- [22.12 自适应刷新率与帧率策略实战](12-adaptive-refresh-rate.md)
- [22.13 App Widget 更新性能：RemoteViews IPC 与 Glance 渲染](13-app-widget-performance.md)
- [22.14 Compose 布局、测量与文字渲染](14-compose-layout-text-rendering.md)
- [22.15 Compose Snapshot、状态一致性与并发](15-compose-snapshot-state-consistency.md)
- [22.16 Vulkan 管线与 Impeller 着色器编译](16-vulkan-impeller-shader-compilation.md)
- [22.17 SurfaceView 与 TextureView：渲染路径、选型与排障](17-surfaceview-textureview.md)
- [22.18 Media3 视频播放：解码、帧时序与渲染](18-media3-video-rendering.md)
- [22.19 CameraX：UseCase、Camera2 映射与性能](19-camerax-rendering.md)

## 阅读建议

- 按使用的 UI 框架或卡顿场景选择条目，无须按编号顺序阅读。
- View 项目可先读 22.1、22.2 和 22.7；Compose 项目可从 22.3、22.2、22.14 和 22.15 开始。
- 改动前后都应保留 Trace、卡顿率、帧时间分布和设备配置，避免只凭主观体验判断效果。
- 相机预览、分析、拍照和录像的应用侧配置见 22.18；HAL3 request/result（应用提交给相机硬件抽象层的请求及其返回元数据）、BufferQueue（生产者与消费者传递图形缓冲区的队列）和 fence（表示异步读写何时完成的同步信号）等系统链路继续阅读 [18.10 Android Camera 平台管线：HAL3、Buffer、ZSL 与显示](../../part2-performance/ch18-rendering-pipelines/10-camera-pipeline.md)。
