# 第 22 章：渲染优化实战

渲染优化需要把布局、绘制、动画、图片、列表和页面切换放进同一帧预算中分析，并通过 Trace 与线上帧率数据验证改动。

第 2 章和第 18 章分析系统渲染管线，第 7 章讨论卡顿定位；这里聚焦 View、Jetpack Compose、WebView、Flutter 和视频播放等 App 侧场景。

## 内容索引

- [22.1 布局优化策略](01-layout-optimization.md)
- [22.2 RecyclerView 最佳实践](02-recyclerview-practice.md)
- [22.3 Jetpack Compose 性能优化](03-compose-performance.md)
- [22.4 自定义 View 性能优化](04-custom-view-optimization.md)
- [22.5 动画性能优化](05-animation-performance.md)
- [22.6 图片加载与显示优化](06-image-loading.md)
- [22.7 WebView 性能优化实战](07-webview-optimization.md)
- [22.8 帧率监控与线上卡顿治理](08-frame-monitoring.md)
- [22.9 渲染优化案例集](09-rendering-case-studies.md)
- [22.10 RenderEffect 与 RuntimeShader 性能实践](10-rendereffect-runtime-shader-performance.md)
- [22.11 AnimatedVectorDrawable 线程退化与动画卡顿](11-animated-vector-drawable-performance.md)
- [22.12 FragmentTransaction 提交链路与页面切换性能](12-fragment-transaction-performance.md)
- [22.13 Predictive Back 动画与页面切换性能](13-predictive-back-performance.md)
- [22.14 桌面窗口化与大屏渲染性能实践](14-desktop-windowing-large-screen-performance.md)
- [22.15 Compose First 与 View/Compose 混合迁移性能边界](15-compose-first-view-migration-performance.md)
- [22.16 Android 17 DeliQueue 与 RecyclerView 预取时序优化](16-deliqueue-recyclerview-prefetch.md)
- [22.17 Hardware Bitmap 与 RenderNode 缓存策略](17-hardware-bitmap-rendernode.md)
- [22.18 Adaptive Refresh Rate 与帧率策略实战](18-adaptive-refresh-rate-practice.md)
- [22.19 RuntimeColorFilter 与 RuntimeXfermode 性能实践](19-runtimecolorfilter-runtimexfermode-performance.md)
- [22.20 Jetpack Compose 性能优化盲区：rememberCoroutineScope、produceState 与 Strong Skipping](20-compose-performance-blind-spots.md)
- [22.21 Jetpack Compose 动画性能深度优化](21-compose-animation-performance.md)
- [22.22 Compose LazyList/LazyGrid 滑动性能深度优化](22-compose-lazylist-performance.md)
- [22.23 Navigation Compose 性能优化](22.23-navigation-compose-performance.md)
- [22.24 App Widget 更新性能：RemoteViews IPC 与 Glance 渲染](24-app-widget-performance.md)
- [22.25 Compose 布局系统：测量阶段、缓存机制与 Intrinsic 性能](25-compose-layout-measurement-performance.md)
- [22.27 Compose Text 性能：从文本布局缓存到整帧证据](25-compose-text-performance.md)
- [22.27 补充：Adaptive Layout 与多形态设备渲染适配性能](27-adaptive-layout-multi-form-factor-performance.md)
- [22.28 Compose Compiler Metrics 与 Recomposition 诊断体系](28-compose-compiler-metrics-recomposition-diagnostics.md)
- [22.29 Jetpack Compose 并发安全机制](22.29-jetpack-compose-并发安全机制.md)
- [22.29 补充：Android 17 GPU Vulkan 异步编译管线管理器调度策略](29-android17-GPU-Vulkan-异步编译管线管理器调度策略.md)
- [22.30 Impeller Shader 编译性能与 Flutter 渲染稳定性](30-impeller-shader-compilation-flutter.md)
- [22.31 Compose Modifier.Node 架构与性能迁移](31-compose-modifier-node-architecture-performance.md)
- [22.32 Compose 无限动画与 VectorConverter 性能优化](32-compose-infinite-animation-vector-converter-performance.md)
- [22.33 Compose PausableComposition 性能机制与 Choreographer 预算边界](33-compose-pausable-composition-performance.md)
- [22.34 Compose SubcomposeLayout 性能分析：层级测量、Intrinsic 与重组陷阱](34-compose-subcompose-layout-performance.md)
- [22.35 Bitmap 解码管线性能与 ImageDecoder 实战](35-bitmap-decode-pipeline-imagedecoder.md)
- [22.36 SharedTransitionLayout：Compose 共享元素过渡动画性能优化](36-shared-transition-layout-performance.md)
- [22.37 Compose Runtime Tracing：runtime-tracing 与 Perfetto 组合阶段追踪](37-compose-runtime-tracing-perfetto-integration.md)
- [22.38 Compose Canvas 自定义绘制性能实战](38-compose-canvas-custom-drawing-performance.md)
- [22.39 Compose Snapshot 系统：状态一致性模型与性能开销](22.39-compose-snapshot-system-state-consistency-performance.md)
- [22.40 Compose Compiler v2 / K2 编译器迁移与 @Composable 编译优化](22.40-compose-compiler-v2-k2-migration-performance.md)
- [22.41 Compose 与 View 互操作性能实战](41-compose-view-interop-performance.md)
- [22.42 SurfaceView 与 TextureView 渲染性能选型实战](42-surfaceview-textureview-rendering-performance.md)
- [22.43 Media3 视频播放渲染管线性能实战](43-media3-video-rendering-pipeline-performance.md)
- [22.44 Compose Pager 从基础到高级动画](44-compose-pager-advanced-animations.md)

## 阅读建议

- 按 UI 技术栈或卡顿场景选择条目，无须按编号顺序阅读。
- View 项目可先读 22.1、22.2、22.4 和 22.8；Compose 项目可从 22.3、22.20 和 22.28 开始。
- 改动前后都应保留 Trace、帧率和设备配置，避免只凭主观体验判断效果。
