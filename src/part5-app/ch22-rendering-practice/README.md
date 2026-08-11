# 第 22 章：渲染优化实战

渲染优化需要把布局、绘制、动画、图片、列表和页面切换放进同一帧预算中分析，并通过 Trace 与线上帧率数据验证改动。

第 2 章和第 18 章分析系统渲染管线，第 7 章讨论卡顿定位；这里聚焦 View、Jetpack Compose、WebView、Flutter、视频播放和 CameraX 等 App 侧场景。

## 内容索引

- [22.1 布局优化策略](01-layout-optimization.md)
- [22.2 RecyclerView 最佳实践](02-recyclerview-practice.md)
- [22.3 Jetpack Compose 性能优化实战](03-compose-performance.md)
- [22.4 自定义 View 性能优化](04-custom-view-optimization.md)
- [22.5 动画性能优化](05-animation-performance.md)
- [22.6 图片加载与显示优化](06-image-loading.md)
- [22.7 WebView 性能优化实战](07-webview-optimization.md)
- [22.8 帧率监控与线上卡顿治理](08-frame-monitoring.md)
- [22.9 RenderEffect 与 Runtime 图形 API 性能实践](09-runtime-graphics-effects.md)
- [22.10 FragmentTransaction 提交链路与页面切换性能](10-fragment-transaction-performance.md)
- [22.11 Predictive Back 动画与页面切换性能](11-predictive-back-performance.md)
- [22.12 Adaptive Layout、桌面窗口与多形态设备性能](12-adaptive-layout-multi-form-factor.md)
- [22.13 Compose First 与 View/Compose 互操作性能实战](13-compose-view-interop.md)
- [22.14 Adaptive Refresh Rate 与帧率策略实战](14-adaptive-refresh-rate.md)
- [22.15 Jetpack Compose 动画性能实战](15-compose-animation-performance.md)
- [22.16 Compose LazyList 与预取调度性能](16-compose-lazylist-performance.md)
- [22.17 Navigation Compose 性能优化](17-navigation-compose-performance.md)
- [22.18 App Widget 更新性能：RemoteViews IPC 与 Glance 渲染](18-app-widget-performance.md)
- [22.19 Compose 布局、SubcomposeLayout 与测量性能](19-compose-layout-measurement.md)
- [22.20 Compose Text 性能深度优化](20-compose-text-performance.md)
- [22.21 Compose Snapshot、状态一致性与并发](21-compose-snapshot-state-consistency.md)
- [22.22 Compose Compiler、Runtime Tracing 与重组诊断](22-compose-compiler-recomposition-diagnostics.md)
- [22.23 Android 17 Vulkan 管线编译与调度策略](23-vulkan-pipeline-compilation.md)
- [22.24 Impeller Shader 编译性能与 Flutter 渲染稳定性](24-flutter-impeller-shader-compilation.md)
- [22.25 Compose Modifier.Node 架构与性能迁移](25-compose-modifier-node.md)
- [22.26 Bitmap 解码、Hardware Bitmap 与 RenderNode](26-bitmap-decode-imagedecoder.md)
- [22.27 Compose SharedTransitionLayout 共享元素性能](27-compose-shared-transition.md)
- [22.28 Compose Canvas 自定义绘制性能实战](28-compose-canvas-custom-drawing.md)
- [22.29 SurfaceView 与 TextureView 渲染性能选型实战](29-surfaceview-textureview.md)
- [22.30 Media3 视频播放渲染管线性能实战](30-media3-video-rendering.md)
- [22.31 CameraX 性能边界与实战（Android 15-17）](31-camerax-performance.md)

## 阅读建议

- 按 UI 技术栈或卡顿场景选择条目，无须按编号顺序阅读。
- View 项目可先读 22.1、22.2、22.4 和 22.8；Compose 项目可从 22.3、22.16 和 22.22 开始。
- 改动前后都应保留 Trace、帧率和设备配置，避免只凭主观体验判断效果。
- 相机预览、分析、拍照和录像的应用侧配置见 22.31；HAL3 request/result、BufferQueue 与 fence 的系统链路继续回到 18.14。
