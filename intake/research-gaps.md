# Knowledge Gaps and Research Areas
**external. 二、总体结论**
- 搜索关键词：`Android 16 GPU Counter Perfetto Profileable`
- 建议查 AOSP / 官方文档：perfetto.dev 官方文档关于 profileable 追踪的最新支持范围

**external. 二、总体结论**
- 搜索关键词：`Android 15 16KB page size NDK max-page-size`，`Matrix android 15 compatibility issue`
- 建议查：Android 官方 16KB 文档，Tencent Matrix 的 GitHub issues。

**external. 二、总体结论**
- 搜索关键词：`Android 16 UprobeStats Mainline module`
- 建议查 AOSP / 官方文档：source.android.com 模块化系统更新文档

**external. 二、总体结论**
- 搜索关键词：`Android 15 16KB page size mprotect`，`Android linker namespace bypass proc maps`。
- 建议查 AOSP / 官方文档 / Perfetto / blog / issue tracker 哪类来源：`developer.android.com` 16KB 适配指南，Bionic linker 源码。

**external. 二、总体结论**
- 搜索关键词：`Android 14 macrobenchmark reset compilation state without reinstalling`
- 建议查：Android Developers Blog 或 Macrobenchmark release notes (1.3 / 1.4 / 1.5)。

**external. 二、总体结论**
- 搜索关键词：`Android 15 16KB page size memory tools PSS`
- 搜索关键词：`Android 15 MTE async asymm`

**external. 二、总体结论**
- 搜索关键词：`Android 15 ProfilingManager Simpleperf`
- 搜索关键词：`Android 15 16KB page size NDK Simpleperf`

**external. 二、总体结论**
- 搜索关键词：`Android Studio 2025 Callstack Sample new engine`
- 建议查 AOSP / 官方文档 / Perfetto / blog / issue tracker 哪类来源：查阅 Android Studio 2025 (Ladybug/Meerkat) 的 release notes，确认新采样引擎的具体改进。

**external. 二、总体结论**
- 搜索关键词：`AppExitInfoTracker aosp`，`KOOM fork dump hprof`。
- 建议查 AOSP / 官方文档 / Perfetto / blog / issue tracker 哪类来源：`cs.android.com`。

**external. 二、总体结论**
- 核验已完成：通过查阅 `androidx.core.os.Profiling` 和 `ProfilingManager` 的 API (API 35/36/37) 变更，文章的归类完全正确。Android 15 (API 35) 提供显式调用，Android 16 (API 36) 提供 System-triggered triggers，Android 17 (API 37) 扩展 Anomaly detection。

**external. 二、总体结论**
- 搜索关键词：`Android 16 CameraX HAL3 ZSL latency`
- 建议查 AOSP / 官方文档：CameraX 官方 release notes 和 AOSP 提交记录。

**external. 二、总体结论**
- 搜索关键词：`Android 15 dumpsys SurfaceFlinger RequestedLayerState`
- 搜索关键词：`dumpsys SurfaceFlinger --latency format Android 15`

**external. 二、总体结论**
- 搜索关键词：`Android 15 BatteryStats STATS_SINCE_UNPLUGGED deprecated`
- 建议查 AOSP / 官方文档 / Perfetto / blog / issue tracker 哪类来源：`developer.android.com` API Reference。

## [2026-04-22] 3.1 Input 事件分发全流程 — 知识盲区

### 盲区描述
Android 12-16 之间 stale-event 判定、WindowInfosListener 协作和 InputFlinger 目录/线程模型的逐版本源码证据不足，正文把多版行为合并成了单一路径。

### 重要程度
高

### 建议研究方向
- 对比 android-12/13/14/15/16 的 InputDispatcher stale-event 实现，确认何时改为 policy 决策
- 核验 WindowInfosListener / WindowInfosUpdate / AnrTracker 的关键提交与 API 变更
- 补齐 InputFlinger 线程/进程边界在各版本中的源码锚点

### 关联章节
3.1, 9.1, 9.2

## [2026-04-22] 7.1 卡顿的定义与分类 — 知识盲区

### 盲区描述
VSync Offset 机制细节

### 重要程度
中

### 建议研究方向
- 梳理 Android 10+ 之后 DispSync 到 VSyncPredictor 的演进，以及厂商如何调整 appPhase / sfPhase 来优化延迟


### 外部 review 来源
- Gemini 外部 review (2026-04-22-15.1-01-jank-definition-external-review.md)


## [2026-04-22] 7.10 图片与 Bitmap 性能优化 — 知识盲区

### 盲区描述
Hardware Bitmap 对 RenderNode 和 SurfaceFlinger composition 的具体影响

### 重要程度
中

### 建议研究方向
- 探讨 Hardware Bitmap 是否可以绕过 RenderThread 的某些流程，直接作为单独图层交给 SurfaceFlinger 合成，从而进一步省去 GPU 拷贝。


### 外部 review 来源
- Gemini 外部 review (2026-04-22-15.10-10-image-bitmap-performance-external-review.md)


## [2026-04-22] 7.11 WebView 渲染性能 — 知识盲区

### 盲区描述
WebView 独立进程崩溃（Render Process Gone）的优雅恢复

### 重要程度
高

### 建议研究方向
- 当 Renderer 进程因为 OOM 被杀时，App 进程虽然不崩溃，但 WebView 会显示白屏。如何通过 `onRenderProcessGone()` 正确销毁旧 WebView 并重建是实战盲区。


### 外部 review 来源
- Gemini 外部 review (2026-04-22-15.11-11-webview-performance-external-review.md)


## [2026-04-22] 7.12 View 体系性能优化 — 知识盲区

### 盲区描述
`ViewDebug` 与系统级 Layout Trace

### 重要程度
中

### 建议研究方向
- 研究 AOSP 中 `ViewDebug.java` 的 trace 机制及 `debug.layout` / `debug.view` 等系统属性的使用，补充至 Perfetto 观测手段中。


### 外部 review 来源
- Gemini 外部 review (2026-04-22-15.12-12-view-layout-performance-external-review.md)


## [2026-04-22] 7.13 SystemUI 性能分析 — 知识盲区

### 盲区描述
SystemUI SceneContainer (Flexiglass) 架构

### 重要程度
高

### 建议研究方向
- 研究 AOSP 中 `com.android.systemui.scene` 下的代码，了解 Compose 如何接管原本属于 `NotificationShadeWindowView` 的动画和状态路由。


### 外部 review 来源
- Gemini 外部 review (2026-04-22-15.13-13-systemui-performance-external-review.md)


## [2026-04-22] 7.13 SystemUI 性能分析 — 知识盲区

### 盲区描述
Foldable 设备下的 SystemUI 渲染模型

### 重要程度
中

### 建议研究方向
- 多 Display 状态下 StatusBar 与 NavigationBar 的多实例管理机制。


### 外部 review 来源
- Gemini 外部 review (2026-04-22-15.13-13-systemui-performance-external-review.md)


## [2026-04-22] 7.14 GAPS 动态分析 — 知识盲区

### 盲区描述
GAPS 在高混淆及加壳 App 中的有效性

### 重要程度
中

### 建议研究方向
- 研究静态路径重建工具如何应对真实市场中经过 ProGuard / R8 高度混淆或 VMP 加壳的应用。


### 外部 review 来源
- Gemini 外部 review (2026-04-22-15.14-14-gaps-dynamic-analysis-external-review.md)


## [2026-04-22] 7.15 场景化性能作战手册 — 知识盲区

### 盲区描述
BufferQueue 堵塞在 Perfetto 中的直观特征识别

### 重要程度
中

### 建议研究方向
- 针对“视频列表、SurfaceView场景卡”场景，提炼出 BufferQueue / dequeueBuffer / queueBuffer 超时的典型可视化特征。


### 外部 review 来源
- Gemini 外部 review (2026-04-22-15.15-15-scenario-playbooks-external-review.md)


## [2026-04-22] 7.2 卡顿原因体系 — 知识盲区

### 盲区描述
Hardware Composer 厂商差异

### 重要程度
中

### 建议研究方向
- 分析高通与联发科 HWC 策略及 dumpsys SurfaceFlinger 中 DEVICE / CLIENT 分配规则的具体厂商实现限制


### 外部 review 来源
- Gemini 外部 review (2026-04-22-15.2-02-jank-causes-external-review.md)


## [2026-04-22] 7.3 卡顿分析方法论 — 知识盲区

### 盲区描述
Binder Transaction Trace 分析

### 重要程度
低

### 建议研究方向
- 深入总结 Perfetto 中 `binder_transaction` flow events 的各种表现形式及异常情况


### 外部 review 来源
- Gemini 外部 review (2026-04-22-15.3-03-jank-methodology-external-review.md)


## [2026-04-22] 7.4 典型场景的卡顿根因分析 — 知识盲区

### 盲区描述
FragmentTransaction commit 源码链路

### 重要程度
高

### 建议研究方向
- 分析 FragmentManager 的 `execPendingActions()` 及其与 Choreographer 回调的先后顺序


### 外部 review 来源
- Gemini 外部 review (2026-04-22-15.4-04-typical-scenarios-external-review.md)


## [2026-04-22] 7.4 典型场景的卡顿根因分析 — 知识盲区

### 盲区描述
WebView / Chromium 渲染管线与 Perfetto 的结合

### 重要程度
中

### 建议研究方向
- 梳理 Chromium IPC、GPU 进程与 Android SurfaceFlinger 的合成关系


### 外部 review 来源
- Gemini 外部 review (2026-04-22-15.4-04-typical-scenarios-external-review.md)


## [2026-04-22] 7.5 流畅性优化策略 — 知识盲区

### 盲区描述
RenderEffect 的底层 GPU 渲染管线

### 重要程度
高

### 建议研究方向
- 结合 RenderNode 和 OpenGL/Vulkan，分析 RenderEffect 触发 offscreen buffer 的代价


### 外部 review 来源
- Gemini 外部 review (2026-04-22-15.5-05-optimization-external-review.md)


## [2026-04-22] 7.5 流畅性优化策略 — 知识盲区

### 盲区描述
AMS 锁竞争对 Binder 耗时的影响

### 重要程度
中

### 建议研究方向
- 分析常见系统服务在并发调用时的锁粒度和阻塞现象


### 外部 review 来源
- Gemini 外部 review (2026-04-22-15.5-05-optimization-external-review.md)


## [2026-04-22] 7.6 案例实战分析 — 知识盲区

### 盲区描述
AnimatedVectorDrawable 的线程退化机制

### 重要程度
高

### 建议研究方向
- 研究 AOSP 中 AVD 何时会被判定为不支持 RenderThread 而回退到主线程（`VectorDrawableAnimatorRT` vs 软件动画引擎）


### 外部 review 来源
- Gemini 外部 review (2026-04-22-15.6-06-case-studies-external-review.md)


## [2026-04-22] 7.7 Compose 性能优化 — 知识盲区

### 盲区描述
Compose State 的 Snapshot 阶段订阅机制

### 重要程度
高

### 建议研究方向
- 分析 `SnapshotStateObserver` 是如何区分 Composition、Layout 和 Draw 三个阶段的


### 外部 review 来源
- Gemini 外部 review (2026-04-22-15.7-07-compose-performance-external-review.md)


## [2026-04-22] 7.8 RecyclerView 深度优化 — 知识盲区

### 盲区描述
复杂 ConstraintLayout 对预取时间估算的影响

### 重要程度
高

### 建议研究方向
- ConstraintLayout 在 RecyclerView 中因为多次 measure（尤其带 match_constraint），会导致 bind 后的首帧 measure 极长，这部分时间可能未被 GapWorker 的 bindTime 均值涵盖。


### 外部 review 来源
- Gemini 外部 review (2026-04-22-15.8-08-recyclerview-performance-external-review.md)


## [2026-04-22] 7.9 感知流畅性 — 知识盲区

### 盲区描述
输入重采样（Motion Resampling）对跟手滑动的影响机制

### 重要程度
中

### 建议研究方向
- 探讨 Android Input 系统的 resampling 算法如何平滑 touch 事件点，结合本章的位移波动，形成更完整的触控-动画闭环。


### 外部 review 来源
- Gemini 外部 review (2026-04-22-15.9-09-perceived-smoothness-external-review.md)

## [2026-04-22] 15.10 eBPF 性能分析 — 知识盲区

### 盲区描述
sched_ext 在手机端 OEM 的落地实况

### 重要程度
高

### 建议研究方向
- 哪些 OEM 正在生产环境中实际应用 sched_ext 自定义 BPF 调度器，以及其采取的具体调度策略。


### 外部 review 来源
- Gemini 外部 review (2026-04-22-15.10-external-review.md)


## [2026-04-22] 15.11 Battery Historian — 知识盲区

### 盲区描述
ADPF 能效模式与功耗测量闭环

### 重要程度
高

### 建议研究方向
- 研究 API 35 `PerformanceHintManager.Session` 增加的 power efficiency 提示，如何与 PowerMonitor 数据变化结合评估。


### 外部 review 来源
- Gemini 外部 review (2026-04-22-15.11-external-review.md)


## [2026-04-22] 15.11 Battery Historian — 知识盲区

### 盲区描述
Doze 模式 / App Standby 极低功耗状态的 Profiler 表现

### 重要程度
中

### 建议研究方向
- 验证当设备强行进入 Doze (`adb shell dumpsys deviceidle force-idle`) 时，Power Profiler 记录的系统基础底噪。


### 外部 review 来源
- Gemini 外部 review (2026-04-22-15.11-external-review.md)


## [2026-04-22] 15.12 APM 可观测性平台 — 知识盲区

### 盲区描述
ApplicationExitInfo 在 Android 11 以下的替代方案

### 重要程度
高

### 建议研究方向
- 研究大厂如何通过读取 `/data/anr/`、监听 LMKd 甚至自身设置 Signal Handler 来弥补低版本能力的。


### 外部 review 来源
- Gemini 外部 review (2026-04-22-15.12-external-review.md)


## [2026-04-22] 15.12 APM 可观测性平台 — 知识盲区

### 盲区描述
Android 14/15 下的 FrameTimeline

### 重要程度
中

### 建议研究方向
- Perfetto 的 FrameTimeline 如何与线上 JankStats 数据对齐。


### 外部 review 来源
- Gemini 外部 review (2026-04-22-15.12-external-review.md)


## [2026-04-22] 15.13 Hook 基础设施 — 知识盲区

### 盲区描述
Android 14 W^X (Write XOR Execute) 与 Inline Hook

### 重要程度
高

### 建议研究方向
- 现代 Android 系统对 JIT 和 AOT 代码内存区域实施严格的 W^X 保护，Inline Hook 在刷新 I-Cache 时如何安全规避。


### 外部 review 来源
- Gemini 外部 review (2026-04-22-15.13-external-review.md)


## [2026-04-22] 15.3 内存分析工具 — 知识盲区

### 盲区描述
16KB Page Size 带来的内存碎片及 PSS 增量核算

### 重要程度
高

### 建议研究方向
- 研究在 16KB 设备上，各个分区的内存自然增长率，以及如何在性能基准测试中消除 16KB 带来的干扰。


### 外部 review 来源
- Gemini 外部 review (2026-04-22-15.3-external-review.md)


## [2026-04-22] 15.3 内存分析工具 — 知识盲区

### 盲区描述
MTE ASYMM (Asymmetric) 模式

### 重要程度
中

### 建议研究方向
- 研究 ASYMM 的工作原理及其在最新 SoC 上的表现。


### 外部 review 来源
- Gemini 外部 review (2026-04-22-15.3-external-review.md)


## [2026-04-22] 15.4 dumpsys 系列命令 — 知识盲区

### 盲区描述
Android 15 SurfaceFlinger FrontEnd 架构细节

### 重要程度
中

### 建议研究方向
- 深入研究 `RequestedLayerState` 引入的原因，以及它是如何优化主合成线程锁争用的。


### 外部 review 来源
- Gemini 外部 review (2026-04-22-15.4-external-review.md)


## [2026-04-22] 15.5 三方性能库 — 知识盲区

### 盲区描述
Android 15 16KB 内存页对 Hook 的影响

### 重要程度
高

### 建议研究方向
- 研究 `mprotect` 和 PLT Hook 库（如 xHook/bhook）在 16KB 页面的调整


### 外部 review 来源
- Gemini 外部 review (2026-04-22-15.5-external-review.md)


## [2026-04-22] 15.9 Camera 性能分析 — 知识盲区

### 盲区描述
CameraX 在 Android 16/17 下的深度优化

### 重要程度
中

### 建议研究方向
- CameraX 库中是否利用了系统新的 HAL 特性来进一步降低多流并发延迟


### 外部 review 来源
- Gemini 外部 review (2026-04-22-15.9-external-review.md)

## [2026-04-22] 7.1 卡顿的定义与分类 — 知识盲区

### 盲区描述
VSync Offset (appPhase / sfPhase) 在高刷屏下的动态调整策略

### 重要程度
中

### 建议研究方向
- AOSP VSyncPredictor 源码及 `dumpsys SurfaceFlinger` 中的 offset 配置
- 关联章节: 2.3 VSync 机制

### 外部 review 来源
- Gemini 外部 review (2026-04-22-15.1-01-jank-definition-external-review.md)


## [2026-04-22] 7.10 图片与 Bitmap 性能优化 — 知识盲区

### 盲区描述
图片加载库如何计算最优并发线程数，并在不同设备配置下避免 CPU 饥饿。

### 重要程度
中

### 建议研究方向
- 结合 `Glide` 的 `GlideExecutor` 的核心数评估算法。

### 外部 review 来源
- Gemini 外部 review (2026-04-22-15.10-10-image-bitmap-performance-external-review.md)


## [2026-04-22] 15.10 eBPF 性能分析 — 知识盲区

### 盲区描述
sched_ext 在各大 Android OEM 上的实际落地策略和 BPF 调度代码。

### 重要程度
高

### 建议研究方向
- 关注高通、联发科和 Google Pixel 在 GKI 6.12 及以上版本设备中的定制 BPF 调度代码实践。
- 关联章节: 无

### 外部 review 来源
- Gemini 外部 review (2026-04-22-15.10-external-review.md)


## [2026-04-22] 7.11 WebView 渲染性能 — 知识盲区

### 盲区描述
WebView Renderer 进程 OOM 被杀后的白屏恢复策略（`onRenderProcessGone`）。

### 重要程度
高

### 建议研究方向
- 查阅 `WebViewClient.onRenderProcessGone` 的正确处理方式，如何避免 App 也随之崩溃或永远处于白屏状态。

### 外部 review 来源
- Gemini 外部 review (2026-04-22-15.11-11-webview-performance-external-review.md)


## [2026-04-22] 15.11 Battery Historian — 知识盲区

### 盲区描述
ADPF 的能效模式与 PowerMonitor 闭环。

### 重要程度
高

### 建议研究方向
- 串联第 11 章或性能框架篇的 ADPF 内容。
- 关联章节: 性能优化相关章节。

### 外部 review 来源
- Gemini 外部 review (2026-04-22-15.11-external-review.md)


## [2026-04-22] 15.12 APM 可观测性平台 — 知识盲区

### 盲区描述
各大 APM 客户端 SDK 的底层“黑科技”（例如 KOOM 的 fork 子进程 dump）。

### 重要程度
中

### 建议研究方向
- 提炼开源 APM 库中的核心 hook/hack 原理。
- 关联章节: 15.13 Hook 基础设施。

### 外部 review 来源
- Gemini 外部 review (2026-04-22-15.12-external-review.md)


## [2026-04-22] 7.13 SystemUI 性能分析 — 知识盲区

### 盲区描述
Android 15+ SystemUI 正在进行的 SceneContainer (Flexiglass) 重构，基于 Compose 的全局状态机如何改变现有的 View 层级追踪。

### 重要程度
高

### 建议研究方向
- AOSP 最新主线 SystemUI Scene 架构的代码走读与 Trace 抓取比对。
- 关联章节: 无，需补充未来架构展望。

### 外部 review 来源
- Gemini 外部 review (2026-04-22-15.13-13-systemui-performance-external-review.md)


## [2026-04-22] 15.13 Hook 基础设施 — 知识盲区

### 盲区描述
Android Linker Namespace (Android 7+) 对 `dlopen` 的限制，以及各大 Hook 库通过解析 `/proc/self/maps` 和内存态 ELF 的绕过手段。

### 重要程度
高

### 建议研究方向
- 研究 `bhook` 或 `ShadowHook` 的代码中关于 linker 限制规避的部分。
- 关联章节: 无。

### 外部 review 来源
- Gemini 外部 review (2026-04-22-15.13-external-review.md)


## [2026-04-22] 7.14 GAPS 动态分析 — 知识盲区

### 盲区描述
静态反向调用图构建在面对反射 (Reflection)、依赖注入 (DI / Dagger / Hilt) 及动态代理时的穿透能力。

### 重要程度
低

### 建议研究方向
- 调研 DroidReach 与 GAPS 在处理非显式方法调用时的静态分析补偿策略。
- 关联章节: 无特定章节，属于通用静态分析范畴。

### 外部 review 来源
- Gemini 外部 review (2026-04-22-15.14-14-gaps-dynamic-analysis-external-review.md)


## [2026-04-22] 7.15 场景化性能作战手册 — 知识盲区

### 盲区描述
在复杂的 SurfaceView / 多窗口场景中，如何准确通过 Perfetto 中的 HWC (Hardware Composer) layer 判断双重合成 (Double Composition) 的发生及其性能消耗。

### 重要程度
中

### 建议研究方向
- 深入分析 SurfaceFlinger 中的 composition type (Device / Client) 及其在 Trace 上的映射。
- 关联章节: 18.4, 18.6

### 外部 review 来源
- Gemini 外部 review (2026-04-22-15.15-15-scenario-playbooks-external-review.md)


## [2026-04-22] 7.2 卡顿原因体系 — 知识盲区

### 盲区描述
BufferQueue 内部的锁竞争机制

### 重要程度
中

### 建议研究方向
- AOSP `BufferQueueProducer` / `BufferQueueConsumer` 源码
- 关联章节: 2.6 SurfaceFlinger 与合成

### 外部 review 来源
- Gemini 外部 review (2026-04-22-15.2-02-jank-causes-external-review.md)


## [2026-04-22] 7.3 卡顿分析方法论 — 知识盲区

### 盲区描述
Perfetto 中的 Binder 调用链路分析技巧

### 重要程度
低

### 建议研究方向
- Perfetto UI Flow events 操作及 Trace Processor 的 binder_transaction 表
- 关联章节: 1.4 进程间通信

### 外部 review 来源
- Gemini 外部 review (2026-04-22-15.3-03-jank-methodology-external-review.md)


## [2026-04-22] 15.3 内存分析工具 — 知识盲区

### 盲区描述
MTE 在 Android 15 上的默认应用范围及 ASYMM 硬件升级特性。

### 重要程度
中

### 建议研究方向
- 进一步查阅 Android 15 的 MTE 安全特性。

### 外部 review 来源
- Gemini 外部 review (2026-04-22-15.3-external-review.md)


## [2026-04-22] 7.4 典型场景卡顿根因 — 知识盲区

### 盲区描述
MediaCodec 视频播放帧率分析，SurfaceFlinger VSync 同步。

### 重要程度
中

### 建议研究方向
- 研究 MediaCodec 直接输出到 Surface 时的 BufferQueue 工作机制，结合 FrameTimeline 进行说明。

### 外部 review 来源
- Gemini 外部 review (2026-04-22-15.4-04-typical-scenarios-external-review.md)


## [2026-04-22] 7.5 流畅性优化策略 — 知识盲区

### 盲区描述
System_server 中系统服务方法调用引发的内部锁竞争，如 AMS。

### 重要程度
中

### 建议研究方向
- 分析常见跨进程 API（如获取包信息、内存信息）在 system_server 中的耗时痛点。

### 外部 review 来源
- Gemini 外部 review (2026-04-22-15.5-05-optimization-external-review.md)


## [2026-04-22] 15.5 三方性能库 — 知识盲区

### 盲区描述
Android 15 ART 机制及 16KB 页对 APM SDK 兼容性的深层拦截机制。

### 重要程度
高

### 建议研究方向
- AOSP 官方文档对于 16KB Page Size 的介绍及 NDK 工具链调整。

### 外部 review 来源
- Gemini 外部 review (2026-04-22-15.5-external-review.md)


## [2026-04-22] 7.6 案例实战分析 — 知识盲区

### 盲区描述
RenderThread 对各类动画（属性动画、AVD、Lottie）的支持与退化机制。

### 重要程度
高

### 建议研究方向
- 梳理 RenderThread 动画支持的边界条件。

### 外部 review 来源
- Gemini 外部 review (2026-04-22-15.6-06-case-studies-external-review.md)


## [2026-04-22] 7.7 Compose 性能优化 — 知识盲区

### 盲区描述
Compose 互操作中 `ViewCompositionStrategy` 对性能的巨大影响。

### 重要程度
中

### 建议研究方向
- 分析在复杂 RecyclerView 嵌套 ComposeView 时，生命周期解绑导致的对象重建开销。

### 外部 review 来源
- Gemini 外部 review (2026-04-22-15.7-07-compose-performance-external-review.md)


## [2026-04-22] 7.8 RecyclerView 深度优化 — 知识盲区

### 盲区描述
GapWorker 均值收集未覆盖的 measure 耗时（如 ConstraintLayout 多次测量引发的突变）。

### 重要程度
高

### 建议研究方向
- 通过 Trace 分析 bindTime 均值与实际完整帧绘制耗时（包含 onMeasure）的差异。
- 关联章节: 7.4 布局与测量性能。

### 外部 review 来源
- Gemini 外部 review (2026-04-22-15.8-08-recyclerview-performance-external-review.md)


## [2026-04-22] 7.9 感知流畅性 — 知识盲区

### 盲区描述
Input Resampling 在触摸跟手阶段是如何与 VSync 节奏协同工作的。

### 重要程度
中

### 建议研究方向
- 结合 `InputDispatcher` 源码研究。
- 关联章节: 3.2 触摸响应的性能分析。

### 外部 review 来源
- Gemini 外部 review (2026-04-22-15.9-09-perceived-smoothness-external-review.md)


## [2026-04-22] 15.9 Camera 性能分析 — 知识盲区

### 盲区描述
CameraX 最新版本的底层延迟优化和 HAL 对接变化

### 重要程度
中

### 建议研究方向
- 关注 Jetpack CameraX 的官方文档更新。
- 关联章节: 无

### 外部 review 来源
- Gemini 外部 review (2026-04-22-15.9-external-review.md)

## [2026-04-22] 1.0 架构全景导读 — 知识盲区

### 盲区描述
Cloud Compilation（云端编译）对 Android 16 OOBE 性能的影响；16KB Page Size 兼容层的性能损耗。

### 重要程度
高

### 建议研究方向
- AOSP art 模块如何处理云端下载的编译产物及其与本地 dex2oat 的优先级关系
- 16KB Page Size 兼容模式下 4KB 应用的性能损耗量化

### 关联章节
1.0, 1.6, 1.12

### 外部 review 来源
- Gemini 外部 review (2026-04-22-21-1.0-external-review.md)


## [2026-04-22] 1.2 系统启动全流程 — 知识盲区

### 盲区描述
16KB Page Size 对系统启动期内存分页的影响；GBL Rust 实现对启动性能的影响。

### 重要程度
中

### 建议研究方向
- 对比 4KB 与 16KB 下 mmap 系统分区的性能表现
- 调研 GBL 如何通过 Rust 实现跨架构引导标准化

### 关联章节
1.2, 1.6

### 外部 review 来源
- Gemini 外部 review (2026-04-22-20-1.2-external-review.md)


## [2026-04-22] 1.3 进程模型 — 知识盲区

### 盲区描述
SDK Sandbox 在 Android 16 中的实际采用率；Modern OomAdjuster 大规模 Service 绑定的性能压测数据。

### 重要程度
中

### 建议研究方向
- 调研主流广告 SDK 在 Android 16 上的沙箱迁移进度
- 验证 Modern 算法在进程数 > 200 时的计算耗时与 Legacy 算法的量化对比

### 关联章节
1.3

### 外部 review 来源
- Gemini 外部 review (2026-04-22-20-1.3-external-review.md)


## [2026-04-22] 1.4 Binder IPC — 知识盲区

### 盲区描述
Binder 解冻风暴对系统整体调度的瞬时冲击量化；Binder 吞吐量瓶颈。

### 重要程度
中

### 建议研究方向
- 结合 Android 14 的 binder-freezer 统计指标进行实验
- 研究高频率小包下的中断压力

### 关联章节
1.4, 1.17

### 外部 review 来源
- Gemini 外部 review (2026-04-22-20-1.4-external-review.md)


## [2026-04-22] 1.5 线程模型 — 知识盲区

### 盲区描述
Android 16 并发队列对反射的破坏；Java 虚拟线程在 ART 中的实现障碍；16KB Page Size 对线程栈内存的影响。

### 重要程度
高

### 建议研究方向
- ConcurrentMessageQueue.mMessages 字段行为变更
- ART Continuations 现状与 Kotlin 协程的差异
- PTHREAD_STACK_MIN 变化对线程开销的量化影响

### 关联章节
1.5, 1.13, 1.14

### 外部 review 来源
- Gemini 外部 review (2026-04-22-20-1.5-external-review.md)


## [2026-04-22] 1.6 版本演进 — 知识盲区

### 盲区描述
Android 15 前台服务 onTimeout 回调的精确生命周期；GBL Rust 实现安全性。

### 重要程度
中

### 建议研究方向
- 在 Service 类中搜索 onTimeout 的调用链
- Android 16 GBL 采用 Rust 对引导阶段内存安全性的提升

### 关联章节
1.6, 1.2

### 外部 review 来源
- Gemini 外部 review (2026-04-22-20-1.6-external-review.md)


## [2026-04-22] 1.7 ART 编译管线 — 知识盲区

### 盲区描述
Instrumentation 导致的去优化机制；Secondary Dex 优化策略；Cloud Compilation 分发细节。

### 重要程度
中

### 建议研究方向
- 研究 ClassFileLoadHook 或 RedefineClasses 如何触发全量去优化
- ART Service 如何处理插件化框架动态加载的 DEX

### 关联章节
1.7, 1.9, 1.12

### 外部 review 来源
- Gemini 外部 review (2026-04-22-20-1.7-external-review.md)


## [2026-04-22] 1.8 AMS — 知识盲区

### 盲区描述
Phantom Process Killer 对复杂工具类应用的影响；mService 全局锁竞争在 Perfetto 中的识别。

### 重要程度
高

### 建议研究方向
- Android 12+ 对 Runtime.exec() 子进程数量限制（32 个）的影响
- AMS 内部 mService 锁的竞争深度如何通过 Perfetto 识别

### 关联章节
1.8

### 外部 review 来源
- Gemini 外部 review (2026-04-22-20-1.8-external-review.md)


## [2026-04-22] 1.9 PMS — 知识盲区

### 盲区描述
App Archiving 对 ActivityStarter 的拦截逻辑；SDM 签名校验流程；Archiving 对 LMK 的影响。

### 重要程度
高

### 建议研究方向
- PackageArchiver.java 及其对 ActivityStarter 的拦截逻辑
- Android 16 模拟器或源码中对 .sdm 文件的 verify 流程

### 关联章节
1.9

### 外部 review 来源
- Gemini 外部 review (2026-04-22-21-1.9-external-review.md)


## [2026-04-22] 1.10 ContentProvider — 知识盲区

### 盲区描述
Android 15 引入的 ApplicationStartInfo 如何量化 installContentProviders 对冷启动的贡献；AttributionSource 调用链审计原理。

### 重要程度
中

### 建议研究方向
- 调研 API 35 的新启动分析接口
- 研究 AttributionSource.Builder.setNext() 的多进程传递

### 关联章节
1.10

### 外部 review 来源
- Gemini 外部 review (2026-04-22-21-1.10-external-review.md)


## [2026-04-22] 1.11 Zygote — 知识盲区

### 盲区描述
Android 16 新增的 PreloadAppProcessHALs 预加载了哪些具体 HAL 接口；Updatable GPU Driver 的 Preload 策略。

### 重要程度
高

### 建议研究方向
- 阅读 ZygoteInit.java 中 preloadAppProcessHALs() 内部实现
- Zygote 如何根据 com.android.graphics.driver 动态选择驱动并执行 PreloadGraphicsDriver

### 关联章节
1.11

### 外部 review 来源
- Gemini 外部 review (2026-04-22-21-1.11-external-review.md)


## [2026-04-22] 1.12 AutoFDO — 知识盲区

### 盲区描述
ETM/ETE 硬件过滤机制对采样精度的影响；GKI Module AutoFDO。

### 重要程度
中

### 建议研究方向
- 阅读 drivers/hwtracing/coresight 下地址范围过滤实现
- 关注 Android 17 如何对 vendor module 独立分发 profile

### 关联章节
1.12, 1.7

### 外部 review 来源
- Gemini 外部 review (2026-04-22-21-1.12-external-review.md)


## [2026-04-22] 1.13 MessageQueue/DeliQueue — 知识盲区

### 盲区描述
SemiConcurrentMessageQueue 与 Concurrent 版本的具体差异；Trebier Stack 在多核体系下消息的内存可见性保证。

### 重要程度
高

### 建议研究方向
- 研究两种变体在生产者/消费者端锁策略的差异
- Treiber Stack CAS 操作隐含的 Store-Store/Load-Load barrier 分析

### 关联章节
1.13, 1.5, 1.14

### 外部 review 来源
- Gemini 外部 review (2026-04-22-21-1.13-external-review.md)


## [2026-04-22] 1.14 锁竞争 — 知识盲区

### 盲区描述
DeliQueue 反射失效后的主线程 Idle 判断替代方案；PI-Mutex 在 32 位架构下的 ID 映射机制与上限。

### 重要程度
高

### 建议研究方向
- 研究 API 37 后如何正确判断主线程 Idle 状态（isIdle() 接口或监听器）
- Bionic PIMutex 结构体分配与回收策略

### 关联章节
1.14, 1.5, 1.13

### 外部 review 来源
- Gemini 外部 review (2026-04-22-21-1.14-external-review.md)


## [2026-04-22] 1.15 JNI/NDK — 知识盲区

### 盲区描述
Linker 与 16KB Page Size 下 PT_LOAD 段偏移对齐对磁盘占用的影响；Project Mainline 带来的 ART 动态更新对 JNI 性能的影响。

### 重要程度
高

### 建议研究方向
- 研究 16KB 模式下 binary size 增长
- Android 12+ 后 JNI 性能随 ART 模块热更新变化

### 关联章节
1.15, 1.6

### 外部 review 来源
- Gemini 外部 review (2026-04-22-21-1.15-external-review.md)


## [2026-04-22] 1.16 Audio Pipeline — 知识盲区

### 盲区描述
FAST Mixer 槽位竞争（多 App 同时请求低延迟流时的优先级分配）；LE Audio 延迟实测数据；Audio Hardening 豁免规则。

### 重要程度
高

### 建议研究方向
- 多 App 同时请求低延迟流的优先级分配策略
- 2026 年主流设备 LC3 编码的真实链路延迟
- 除了 FGS WIU，哪些系统级 App 或特定权限可豁免限制

### 关联章节
1.16

### 外部 review 来源
- Gemini 外部 review (2026-04-22-21-1.16-external-review.md)


## [2026-04-22] 1.17 IPC 全景 — 知识盲区

### 盲区描述
memfd Sealing 机制（F_SEAL_FUTURE_WRITE 在零拷贝场景下的安全保障）；Stable AIDL HAL 的线程模型。

### 重要程度
高

### 建议研究方向
- 研究 F_SEAL_FUTURE_WRITE 在零拷贝场景下的安全保障
- 对比 HIDL 在 /dev/hwbinder 和 AIDL 在 /dev/binder 的实时调度差异

### 关联章节
1.17, 1.4

### 外部 review 来源
- Gemini 外部 review (2026-04-22-21-1.17-external-review.md)


## [2026-04-22] 2.1 渲染架构全景 — 知识盲区

### 盲区描述
AGSL RuntimeShader 对低端 GPU 的填充率影响；硬件合成器中哪些混合模式会强制回退到 GPU Composition。

### 重要程度
高

### 建议研究方向
- 复杂 RuntimeShader 对低端 GPU 的填充率影响
- HWC 中 Blend Mode 对 Composition 类型的影响

### 关联章节
2.1, 2.6

### 外部 review 来源
- Gemini 外部 review (2026-04-22-21-2.1-external-review.md)


## [2026-04-22] 2.2 帧率与刷新率 — 知识盲区

### 盲区描述
View 投票冲突解决机制（多个 View 请求不同 Category 时 SF 的合并算法）；ARR 对 WebView 渲染节奏的影响。

### 重要程度
高

### 建议研究方向
- SurfaceFlinger 在多 View 不同帧率请求时的合并算法
- WebView 内部渲染节奏与系统 ARR 的同步机制

### 关联章节
2.2, 2.3

### 外部 review 来源
- Gemini 外部 review (2026-04-22-21-2.2-external-review.md)

## [2026-04-22] 2.10 GPU 渲染深入 — 知识盲区

### 盲区描述
GPU 内存管理一节缺少 App 可见对象与系统内部图形缓冲对象之间的边界：Surface / SurfaceTexture / HardwareBuffer / ANativeWindow 如何进入 BufferQueue，再映射到 GraphicBuffer / GraphicBufferMapper / Gralloc / HWC。缺少这层后，读者很难把源码路径、内存占用、Perfetto / dumpsys 观测点连成一条可验证链。

### 重要程度
高

### 建议研究方向
- 梳理 Surface / SurfaceTexture / HardwareBuffer / ANativeWindow 与 BufferQueue 的对象边界和所有权流转
- 补齐 GraphicBuffer / Mapper / Gralloc / HWC 的内部角色分工，以及 meminfo / Perfetto / dumpsys 各自能看到什么

### 关联章节
2.6、18.6



## [2026-04-23] External Review 知识盲区批量整合

### 2.5 Vulkan 路径下的 Sync

- **重要程度**：高
- **建议研究方向**：ANGLE 开启后，同步逻辑是否从 EGL Sync 切换到 Vulkan Semaphore 及其对 Trace 切片名称的影响。
- **来源**：External AI Review

### 2.5 RenderThread CPU Affinity

- **重要程度**：中
- **建议研究方向**：Android 15+ 是否通过进程组（cgroup）对 RenderThread 进行了更激进的 CPU 大核绑定。
- **来源**：External AI Review




## [2026-04-23] 18.14 Camera 渲染管线 — 知识盲区

### 盲区描述
配置流与版本演进没有纳入 Android 13+ 的 stream use case（`OutputConfiguration.setStreamUseCase` / `SCALER_AVAILABLE_STREAM_USE_CASES`）。这会漏掉一个直接影响 HAL sensor mode、ISP pipeline、多流 guaranteed combinations 和 low-latency snapshot 行为的关键调优入口。

### 重要程度
高

### 建议研究方向
- 核对 stream use case 与 capture intent 的职责边界，以及 `MandatoryStreamCombination` 的官方保证矩阵
- 梳理 `PREVIEW` / `VIDEO_RECORD` / `STILL_CAPTURE` / `PREVIEW_VIDEO_STILL` / `LOW_LATENCY_SNAPSHOT` 对多流组合、功耗和时延的影响
- 补 Android 13-16 在 OEM HAL 中常见的忽略、降级与回退行为，以及 Perfetto / cameraserver 的观测点

### 关联章节
18.14, 14.9, 18.6

---

## [2026-04-23] 4.0 4.0 内存章节导读 — 知识盲区

### 盲区描述
16KB Page Size 对现有三方库的破坏性影响评估

### 重要程度
高

### 建议研究方向
整理受影响常见三方库清单

### 关联章节
4.7

### 外部 review 来源
Gemini 外部 review (4.0)

---

## [2026-04-23] 4.0 4.0 内存章节导读 — 知识盲区

### 盲区描述
MGLRU 运行时监控方法

### 重要程度
中

### 建议研究方向
通过 sysfs 接口观察多代 LRU 实际回收效率

### 关联章节
4.0

### 外部 review 来源
Gemini 外部 review (4.0)

---

## [2026-04-23] 4.0 4.0 内存章节导读 — 知识盲区

### 盲区描述
MTE 硬件级防御机制细节

### 重要程度
中

### 建议研究方向
硬件 Tag 与物理内存 1/32 映射关系及性能代价

### 关联章节
4.6

### 外部 review 来源
Gemini 外部 review (4.0)

---

## [2026-04-23] 4.5 4.5 App 内存优化 — 知识盲区

### 盲区描述
dmabuf 追踪

### 重要程度
中

### 建议研究方向
Perfetto 中 dmabuf track 如何反映 GPU 内存分配

### 关联章节
4.5

### 外部 review 来源
Gemini 外部 review (4.5)

---

## [2026-04-23] 4.5 4.5 App 内存优化 — 知识盲区

### 盲区描述
ActivityManager.getMyMemoryState 性能开销

### 重要程度
中

### 建议研究方向
主动获取 trimLevel 的性能开销与适用场景

### 关联章节
4.5

### 外部 review 来源
Gemini 外部 review (4.5)

---

## [2026-04-23] 4.5 4.5 App 内存优化 — 知识盲区

### 盲区描述
16KB 对齐下内存浪费量化

### 重要程度
低

### 建议研究方向
大量小图场景内部碎片增量估算

### 关联章节
4.5, 4.7

### 外部 review 来源
Gemini 外部 review (4.5)

---

## [2026-04-23] 4.7 4.7 16KB Page Size — 知识盲区

### 盲区描述
Bionic Linker 16KB Compat Mode 内存重映射逻辑

### 重要程度
高

### 建议研究方向
阅读 bionic/linker/linker.cpp 中 Linker 类对页大小对齐失败的处理

### 关联章节
4.7

### 外部 review 来源
Gemini 外部 review (4.7)

---

## [2026-04-23] 4.7 4.7 16KB Page Size — 知识盲区

### 盲区描述
RELRO 填充 Bug 对 16KB 系统的影响

### 重要程度
中

### 建议研究方向
研究旧版 lld 链接器产生的 RELRO 对齐错误

### 关联章节
4.7

### 外部 review 来源
Gemini 外部 review (4.7)

---

## [2026-04-23] 4.8 4.8 ART 分代 GC — 知识盲区

### 盲区描述
userfaultfd 在 CMC 中的页错误开销

### 重要程度
中

### 建议研究方向
深入研究 SIGBUS 处理器在 CMC 中的性能损耗

### 关联章节
4.8

### 外部 review 来源
Gemini 外部 review (4.8)

---

## [2026-04-23] 4.8 4.8 ART 分代 GC — 知识盲区

### 盲区描述
mid_generation 具体晋升阈值

### 重要程度
高

### 建议研究方向
确认是否硬编码为 1 次或存在动态调整逻辑

### 关联章节
4.8

### 外部 review 来源
Gemini 外部 review (4.8)

---

## [2026-04-23] 4.8 4.8 ART 分代 GC — 知识盲区

### 盲区描述
Android 17 DeliQueue 与 GC 优化协同

### 重要程度
中

### 建议研究方向
ART 调度器如何利用 DeliQueue 规避 GC 高峰

### 关联章节
4.8

### 外部 review 来源
Gemini 外部 review (4.8)

---

## [2026-04-23] 5.0 5.0 CPU 与功耗章节导读 — 知识盲区

### 盲区描述
ADPF (Adaptive Performance Framework) 架构

### 重要程度
高

### 建议研究方向
PerformanceHintManager 如何通过 PowerHAL 影响 CPU 频率

### 关联章节
5.9

### 外部 review 来源
Gemini 外部 review (5.0)

---

## [2026-04-23] 5.0 5.0 CPU 与功耗章节导读 — 知识盲区

### 盲区描述
UClamp (Utilization Clamping) 应用逻辑

### 重要程度
中

### 建议研究方向
Android 12+ 如何使用 uclamp 替代 SchedTune

### 关联章节
5.2

### 外部 review 来源
Gemini 外部 review (5.0)

---

## [2026-04-23] 5.0 5.0 CPU 与功耗章节导读 — 知识盲区

### 盲区描述
WALT vs PELT 负载追踪差异

### 重要程度
中

### 建议研究方向
高通平台 WALT 与 AOSP 标准 PELT 的差异

### 关联章节
5.1

### 外部 review 来源
Gemini 外部 review (5.0)

---

## [2026-04-23] 5.1 5.1 Linux 进程调度基础 — 知识盲区

### 盲区描述
EEVDF lag 衰减细节

### 重要程度
中

### 建议研究方向
reweight_entity 逻辑如何防止任务通过睡眠重置 lag

### 关联章节
5.1

### 外部 review 来源
Gemini 外部 review (5.1)

---

## [2026-04-23] 5.1 5.1 Linux 进程调度基础 — 知识盲区

### 盲区描述
Android 16 调度新特性

### 重要程度
高

### 建议研究方向
API 36/37 是否引入针对 EEVDF 的专门 NDK 接口

### 关联章节
5.1

### 外部 review 来源
Gemini 外部 review (5.1)

---

## [2026-04-23] 5.2 5.2 EAS 能量感知调度 — 知识盲区

### 盲区描述
CPU 唤醒成本 (Waking vs Using already awake CPU)

### 重要程度
中

### 建议研究方向
find_energy_efficient_cpu 是否考虑唤醒 Deep Idle CPU 的静态能量开销

### 关联章节
5.2

### 外部 review 来源
Gemini 外部 review (5.2)

---

## [2026-04-23] 5.2 5.2 EAS 能量感知调度 — 知识盲区

### 盲区描述
厂商自定义 Boost Hook

### 重要程度
高

### 建议研究方向
高通 sched_boost 标志位如何强制绕过 EAS 逻辑

### 关联章节
5.2, 5.3

### 外部 review 来源
Gemini 外部 review (5.2)

---

## [2026-04-23] 5.3 5.3 大小核架构 — 知识盲区

### 盲区描述
EEVDF 调度器对调频的影响

### 重要程度
中

### 建议研究方向
Linux 6.6 EEVDF 后 util 信号平滑处理变化

### 关联章节
5.3

### 外部 review 来源
Gemini 外部 review (5.3)

---

## [2026-04-23] 5.3 5.3 大小核架构 — 知识盲区

### 盲区描述
ADPF 与大小核联动

### 重要程度
高

### 建议研究方向
ADPF 如何影响任务在超大核上的停留时间

### 关联章节
5.3, 5.9

### 外部 review 来源
Gemini 外部 review (5.3)

---

## [2026-04-23] 5.4 5.4 DVFS 动态调频 — 知识盲区

### 盲区描述
uclamp_min 对启动耗时的影响

### 重要程度
高

### 建议研究方向
Android Framework 如何通过 CPUSet/CGroup 设置 uclamp_min

### 关联章节
5.4

### 外部 review 来源
Gemini 外部 review (5.4)

---

## [2026-04-23] 5.4 5.4 DVFS 动态调频 — 知识盲区

### 盲区描述
SCMI Fastchannels

### 重要程度
中

### 建议研究方向
ARM 官方 SCMI 规范 MMIO 调频通道

### 关联章节
5.4

### 外部 review 来源
Gemini 外部 review (5.4)

---

## [2026-04-23] 5.8 5.8 后台执行限制 — 知识盲区

### 盲区描述
Binder Freezer Driver 协同机制

### 重要程度
高

### 建议研究方向
FrozenStateChangeCallback 在 AOSP 中的具体应用场景

### 关联章节
5.8

### 外部 review 来源
Gemini 外部 review (5.8)

---

## [2026-04-23] 5.8 5.8 后台执行限制 — 知识盲区

### 盲区描述
Android 16 UIDT 额度详情

### 重要程度
中

### 建议研究方向
UIDT 是否受 App Standby Bucket 进一步限制

### 关联章节
5.8, 5.10

### 外部 review 来源
Gemini 外部 review (5.8)

---

## [2026-04-23] 5.9 5.9 ADPF 自适应性能框架 — 知识盲区

### 盲区描述
GPU 目标设定的 WorkDuration 分拆版本

### 重要程度
中

### 建议研究方向
updateTargetWorkDuration 是否也有类似 WorkDuration 的分拆

### 关联章节
5.9

### 外部 review 来源
Gemini 外部 review (5.9)

---

## [2026-04-23] 5.9 5.9 ADPF 自适应性能框架 — 知识盲区

### 盲区描述
ADPF 非游戏场景策略

### 重要程度
高

### 建议研究方向
ProfilingManager TRIGGER_TYPE_ANOMALY 如何利用 ADPF 信号

### 关联章节
5.9, 5.11

### 外部 review 来源
Gemini 外部 review (5.9)

---

## [2026-04-23] 5.10 5.10 JobScheduler/WorkManager 性能 — 知识盲区

### 盲区描述
updateEstimatedNetworkBytes API

### 重要程度
中

### 建议研究方向
Android 14+ 估算带宽 API 对调度优先级的影响

### 关联章节
5.10

### 外部 review 来源
Gemini 外部 review (5.10)

---

## [2026-04-23] 5.10 5.10 JobScheduler/WorkManager 性能 — 知识盲区

### 盲区描述
TRANSFER_THROUGHPUT_UTILIZATION

### 重要程度
中

### 建议研究方向
Android 16+ 对大文件传输 job 的吞吐量监测逻辑

### 关联章节
5.10

### 外部 review 来源
Gemini 外部 review (5.10)

---

## [2026-04-23] 5.11 5.11 端侧 AI 推理性能 — 知识盲区

### 盲区描述
PODAI (Play for On-device AI) 动态分发

### 重要程度
高

### 建议研究方向
通过 Play Services 动态分发 NPU 加速库解决 APK 体积

### 关联章节
5.11

### 外部 review 来源
Gemini 外部 review (5.11)

---

## [2026-04-23] 5.11 5.11 端侧 AI 推理性能 — 知识盲区

### 盲区描述
零拷贝 TensorBuffer

### 重要程度
中

### 建议研究方向
HardwareBuffer 与 LiteRT NPU 直接内存共享

### 关联章节
5.11

### 外部 review 来源
Gemini 外部 review (5.11)

---

## [2026-04-23] 5.12 5.12 热管理深度分析 — 知识盲区

### 盲区描述
皮肤温度估算模型 (Thermal Model)

### 重要程度
中

### 建议研究方向
OEM 如何利用 power_allocator tzp 在 sysfs 中暴露物理参数

### 关联章节
5.12

### 外部 review 来源
Gemini 外部 review (5.12)

---

## [2026-04-23] 5.12 5.12 热管理深度分析 — 知识盲区

### 盲区描述
Android 16 NDK AThermal_getThermalHeadroomThresholds

### 重要程度
高

### 建议研究方向
原生代码直接获取 Throttling 状态切换精确数值

### 关联章节
5.12

### 外部 review 来源
Gemini 外部 review (5.12)

---

## [2026-04-23] 6.0 6.0 存储章节导读 — 知识盲区

### 盲区描述
16KB Page Size 对底层存储性能的变革

### 重要程度
中

### 建议研究方向
结合 Android 15 行为变更，评估对 I/O 吞吐量的影响

### 关联章节
6.0, 4.7

### 外部 review 来源
Gemini 外部 review (6.0)

---

## [2026-04-23] 6.1 6.1 存储架构 — 知识盲区

### 盲区描述
F2FS 前台 GC 触发水位线

### 重要程度
中

### 建议研究方向
研究 f2fs/segment.c 中 has_not_enough_free_secs 逻辑

### 关联章节
6.1

### 外部 review 来源
Gemini 外部 review (6.1)

---

## [2026-04-23] 6.1 6.1 存储架构 — 知识盲区

### 盲区描述
Metadata Encryption Inline Crypto 映射

### 重要程度
中

### 建议研究方向
blk-crypto 如何在不同 SoC 上落地

### 关联章节
6.1

### 外部 review 来源
Gemini 外部 review (6.1)

---

## [2026-04-23] 6.2 6.2 文件系统 — 知识盲区

### 盲区描述
Project Quota (存储配额) 工作原理

### 重要程度
高

### 建议研究方向
内核 PRID 映射与 StorageStatsService 交互

### 关联章节
6.2

### 外部 review 来源
Gemini 外部 review (6.2)

---

## [2026-04-23] 6.2 6.2 文件系统 — 知识盲区

### 盲区描述
Casefolding (大小写折叠) 性能影响

### 重要程度
高

### 建议研究方向
Unicode 折叠算法在内核层的性能影响

### 关联章节
6.2

### 外部 review 来源
Gemini 外部 review (6.2)

---

## [2026-04-23] 6.2 6.2 文件系统 — 知识盲区

### 盲区描述
Inline Encryption (fscrypt) 与 UFS Keyslot

### 重要程度
高

### 建议研究方向
blk-crypto 与 UFS Keyslot 管理

### 关联章节
6.2

### 外部 review 来源
Gemini 外部 review (6.2)

---

## [2026-04-23] 6.4 6.4 存储版本演进 — 知识盲区

### 盲区描述
16KB 页对 F2FS 挂载参数的影响

### 重要程度
高

### 建议研究方向
Android 15 16KB 模式下 F2FS block_size 限制

### 关联章节
6.4, 4.7

### 外部 review 来源
Gemini 外部 review (6.4)

---

## [2026-04-23] 6.4 6.4 存储版本演进 — 知识盲区

### 盲区描述
MediaProvider 位置脱敏 (Redaction) 对 FUSE 读延迟的量化影响

### 重要程度
中

### 建议研究方向
对比有/无位置信息照片的 CPU 周期消耗

### 关联章节
6.4

### 外部 review 来源
Gemini 外部 review (6.4)

---

## [2026-04-23] 6.5 6.5 SP/DataStore 优化 — 知识盲区

### 盲区描述
16KB Page Size 对 I/O 密集型存储的影响

### 重要程度
中

### 建议研究方向
Android 15 强制 16KB 页对 XML 解析和文件落盘的性能提升

### 关联章节
6.5, 4.7

### 外部 review 来源
Gemini 外部 review (6.5)

---

## [2026-04-23] 6.5 6.5 SP/DataStore 优化 — 知识盲区

### 盲区描述
MultiProcessDataStoreFactory 锁机制

### 重要程度
中

### 建议研究方向
核实基于 FileLock 的实现及极端竞争下性能

### 关联章节
6.5

### 外部 review 来源
Gemini 外部 review (6.5)

---

## [2026-04-23] 7.2 7.2 卡顿原因体系 — 知识盲区

### 盲区描述
Android 17 Generational GC STW 表现

### 重要程度
高

### 建议研究方向
验证 ART Mainline 演进对 UI 线程暂停时间的实际压制效果

### 关联章节
7.2, 4.8

### 外部 review 来源
Gemini 外部 review (7.2)

---

## [2026-04-23] 7.2 7.2 卡顿原因体系 — 知识盲区

### 盲区描述
SkiaVulkan 在 RenderThread 的 Trace 表现

### 重要程度
中

### 建议研究方向
Android 15 默认 SkiaVulkan 的 drawOp 细分 Slice 差异

### 关联章节
7.2

### 外部 review 来源
Gemini 外部 review (7.2)

---

## [2026-04-23] 7.3 7.3 卡顿分析方法论 — 知识盲区

### 盲区描述
Android 16 AppJankStats 监控新范式

### 重要程度
中

### 建议研究方向
调研 android.app.jank 软件包

### 关联章节
7.3

### 外部 review 来源
Gemini 外部 review (7.3)

---

## [2026-04-23] 7.3 7.3 卡顿分析方法论 — 知识盲区

### 盲区描述
ADPF 与 FrameTimeline 反馈闭环

### 重要程度
高

### 建议研究方向
ADPF 如何根据 FrameTimeline Expected Deadline 动态调整 CPU 频率

### 关联章节
7.3, 5.9

### 外部 review 来源
Gemini 外部 review (7.3)

---

## [2026-04-23] 7.6 7.6 案例实战分析 — 知识盲区

### 盲区描述
Cached App Freezer 完整机制

### 重要程度
高

### 建议研究方向
Android 14+ 后台进程管理策略详解

### 关联章节
7.6, 5.8

### 外部 review 来源
Gemini 外部 review (7.6)

---

## [2026-04-23] 7.6 7.6 案例实战分析 — 知识盲区

### 盲区描述
MGLRU vs 传统双级 LRU 锁竞争差异

### 重要程度
中

### 建议研究方向
对比 pgdat->lru_lock 竞争解决效果

### 关联章节
7.6, 4.0

### 外部 review 来源
Gemini 外部 review (7.6)

---

## [2026-04-23] 7.7 7.7 Compose 性能优化 — 知识盲区

### 盲区描述
Inline Composable 重组穿透机制

### 重要程度
高

### 建议研究方向
startReplaceableGroup vs startRestartGroup IR 转换差异

### 关联章节
7.7

### 外部 review 来源
Gemini 外部 review (7.7)

---

## [2026-04-23] 7.7 7.7 Compose 性能优化 — 知识盲区

### 盲区描述
SlotTable Gap Buffer 机制

### 重要程度
中

### 建议研究方向
SlotTable.kt insert/move 操作对性能的实际影响

### 关联章节
7.7

### 外部 review 来源
Gemini 外部 review (7.7)

---

## [2026-04-23] 7.8 7.8 RecyclerView 深度优化 — 知识盲区

### 盲区描述
hasTransientState 导致的 ViewHolder 回收阻断

### 重要程度
中

### 建议研究方向
哪些三方动画库会意外触发该状态导致 RV 缓存失效

### 关联章节
7.8

### 外部 review 来源
Gemini 外部 review (7.8)


## [2026-04-23] 8.1 响应速度原理 — 知识盲区

### 盲区描述
------

### 重要程度
---------

### 建议研究方向
-------------

### 关联章节
- 8.1


### 外部 review 来源
- 外部 AI review (Gemini)


## [2026-04-23] 8.1 响应速度原理 — 知识盲区

### 盲区描述
Input 事件与 VSync 信号的处理优先级

### 重要程度
中

### 建议研究方向
在同一个 Looper 唤醒周期内，如果有 fd 事件（如 Input）和普通的 Message 同时就绪，底层的处理顺序是如何决定的。

### 关联章节
- 8.1


### 外部 review 来源
- 外部 AI review (Gemini)


## [2026-04-23] 8.1 响应速度原理 — 知识盲区

### 盲区描述
Native 层 Looper 处理 Input socket fd 唤醒与 Java 层 MessageQueue 之间的精确调度关系。

### 重要程度
中

### 建议研究方向
阅读 `Looper.cpp` 了解 `epoll` 响应流程。

### 关联章节
- 8.1
- 消息机制或事件分发章节。

### 外部 review 来源
- 外部 AI review (Gemini)


## [2026-04-23] 8.2 App 启动全流程 — 知识盲区

### 盲区描述
TTID 的终点回调 BLASTSync 机制

### 重要程度
中

### 建议研究方向
现代 Android 引入 BLASTBufferQueue 后，TTID 的终点是如何从 SurfaceFlinger 真正通过 transaction callback 回传给 WMS 以判定 `windowsDrawn` 的。

### 关联章节
- 8.2


### 外部 review 来源
- 外部 AI review (Gemini)


## [2026-04-23] 8.2 App 启动全流程 — 知识盲区

### 盲区描述
Android 12/13+ 引入 BLAST 架构后，WMS 是如何通过 Transaction Callback 接收首帧绘制完成信号以结束 TTID 计时的。

### 重要程度
中

### 建议研究方向
结合 AOSP 中 `BLASTBufferQueue` 的演进，分析 `windowsDrawn` 事件的具体触发链路。

### 关联章节
- 8.2
- 渲染流水线章节。

### 外部 review 来源
- 外部 AI review (Gemini)


## [2026-04-23] 8.3 启动优化策略 — 知识盲区

### 盲区描述
ProfileInstaller 的强制同步编译 API

### 重要程度
中

### 建议研究方向
`profileinstaller` 库是否提供了强制同步编译的 API，以便在特定的业务场景（如首充、重要升级后）主动触发 AOT 编译。

### 关联章节
- 8.3


### 外部 review 来源
- 外部 AI review (Gemini)


## [2026-04-23] 8.3 启动优化策略 — 知识盲区

### 盲区描述
ProfileInstaller 在各家国产 ROM 上的 `bg-dexopt-job` 触发时机是否存在被深度定制（魔改）导致不执行的情况。

### 重要程度
低

### 建议研究方向
收集国内头部 ROM 对 `bg-dexopt-job` 的调度策略差异。

### 关联章节
- 8.3
- 无。

### 外部 review 来源
- 外部 AI review (Gemini)


## [2026-04-23] 8.4 其他响应速度场景 — 知识盲区

### 盲区描述
FragmentFactory 预加载数据的生命周期边界

### 重要程度
中

### 建议研究方向
在 `FragmentFactory.instantiate` 中直接注入耗时的预加载数据，是否会阻塞宿主 Activity/Fragment 的事务提交流程？

### 关联章节
- 8.4


### 外部 review 来源
- 外部 AI review (Gemini)


## [2026-04-23] 8.4 其他响应速度场景 — 知识盲区

### 盲区描述
FragmentFactory 的实例化与 FragmentManager 的异步事务机制之间的执行时序关系。

### 重要程度
中

### 建议研究方向
深入研究 FragmentManager 的 `commit()` 到 `executePendingTransactions()` 的状态机流转。

### 关联章节
- 8.4
- 无。

### 外部 review 来源
- 外部 AI review (Gemini)


## [2026-04-23] 8.6 Kotlin Coroutine 性能实践 — 知识盲区

### 盲区描述
Perfetto 中 Coroutine 挂起状态的精准还原

### 重要程度
低

### 建议研究方向
在缺乏 JVM Instrument API 支持的 Android 上，如何通过自定义 Trace 脚本或 BPF 技术，无缝对接 Kotlin 状态机以在 Perfetto 中精准可视化挂起时间。

### 关联章节
- 8.6


### 外部 review 来源
- 外部 AI review (Gemini)


## [2026-04-23] 8.7 Baseline Profiles 与编译优化实践 — 知识盲区

### 盲区描述
dex2oat 编译失败的静默回退机制

### 重要程度
中

### 建议研究方向
当 Baseline Profile 规则文件中存在已经失效的类或方法签名时，ART 的 `dex2oat` 是如何处理的（容错机制），是否会导致整个 Profile 失效。

### 关联章节
- 8.7


### 外部 review 来源
- 外部 AI review (Gemini)


## [2026-04-23] 8.7 Baseline Profiles 与编译优化实践 — 知识盲区

### 盲区描述
由于代码混淆（R8）或版本迭代导致 HRF 规则与实际 DEX 方法签名不匹配时，安装端的 `dex2oat` 编译表现。

### 重要程度
中

### 建议研究方向
梳理 R8 插件是如何自动将 HRF 中的人类可读签名重写为混淆后签名的，以及匹配失败时的 ART 日志。

### 关联章节
- 8.7
- 构建优化相关章节。

### 外部 review 来源
- 外部 AI review (Gemini)


## [2026-04-23] 8.8 Android 多媒体管线性能 — 知识盲区

### 盲区描述
视频播放中的 A/V Sync 底层机制

### 重要程度
中

### 建议研究方向
详细梳理 ExoPlayer / Media3 是如何通过 `AudioTimestamp` 动态调整视频帧的 presentation time（PTS）以实现音画同步的。

### 关联章节
- 8.8


### 外部 review 来源
- 外部 AI review (Gemini)


## [2026-04-23] 8.8 Android 多媒体管线性能 — 知识盲区

### 盲区描述
在存在蓝牙耳机等外部输出设备时，Audio HAL 报告的硬件延迟（Hardware Latency）如何影响 ExoPlayer 的音画同步策略。

### 重要程度
中

### 建议研究方向
研究 `AudioTrack.getTimestamp()` 的返回值在通过蓝牙 A2DP 协议传输时的补偿机制。

### 关联章节
- 8.8
- 无。

### 外部 review 来源
- 外部 AI review (Gemini)


## [2026-04-23] 8.10 ProfilingManager 系统触发式性能追踪 — 知识盲区

### 盲区描述
ProfilingManager 在各家国产 ROM 的落地一致性

### 重要程度
高

### 建议研究方向
国内定制 ROM 对 `system_server` 和 `lmkd` 等底层组件魔改较多，这些改动是否会破坏 `KILL_EXCESSIVE_CPU_USAGE` 等系统触发器的感知与回调。

### 关联章节
- 8.10


### 外部 review 来源
- 外部 AI review (Gemini)


## [2026-04-23] 8.10 ProfilingManager 系统触发式性能追踪 — 知识盲区

### 盲区描述
由于系统级 Trace 会带有部分 Redaction（数据脱敏），`COLD_START` 收集到的 trace 在缺乏 root 权限时，其调用栈采样（stack sampling）的深度是否会被截断，导致业务侧排障信息不全。

### 重要程度
中

### 建议研究方向
测试 Android 16 非 root 手机上 System-triggered trace 的 Redaction 边界。

### 关联章节
- 8.10
- 无。

### 外部 review 来源
- 外部 AI review (Gemini)


## [2026-04-23] 8.9 Android 游戏性能与 Game Mode/State API — 知识盲区

### 盲区描述
GameState 触发 GAME_LOADING boost 的内核态映射

### 重要程度
中

### 建议研究方向
`PowerManagerInternal.setPowerMode(Mode.GAME_LOADING, true)` 在底层是如何映射到 Power HAL 并最终影响 CPU cpufreq 调度策略的（是提频还是锁大核）。

### 关联章节
- 8.9


### 外部 review 来源
- 外部 AI review (Gemini)


## [2026-04-23] 7.11 WebView 渲染性能与优化 — 知识盲区

### 盲区描述
Android 13 Samsung 设备 Chromium bug

### 重要程度
中

### 建议研究方向
验证该 `AwContents` native lambda 强引用 bug 在最新 Chromium WebView 版本（如 M120+）中是否已被彻底修复。

### 关联章节
- 7.11


### 外部 review 来源
- 外部 AI review (Gemini)


## [2026-04-23] 7.11 WebView 渲染性能与优化 — 知识盲区

### 盲区描述
Android 13 部分设备上的 WebView 销毁延迟 Bug 的最新修复状态。

### 重要程度
中

### 建议研究方向
查阅 Chromium Issue Tracker 确认修复情况。

### 关联章节
- 7.11


### 外部 review 来源
- 外部 AI review (Gemini)


## [2026-04-23] 7.12 View 体系性能优化 — 知识盲区

### 盲区描述
硬件加速下的 invalidate 机制

### 重要程度
高

### 建议研究方向
现代 Android (API 29+) 开启硬件加速时，`invalidate()` 是如何通过 RenderNode 传递 damage 信号而无需重绘整个 View 树的。

### 关联章节
- 7.12


### 外部 review 来源
- 外部 AI review (Gemini)


## [2026-04-23] 7.12 View 体系性能优化 — 知识盲区

### 盲区描述
现代 Android 版本中，RenderNode 对 `invalidate()` 传播机制的改变及性能优化。

### 重要程度
高

### 建议研究方向
深入分析硬件加速下的 DisplayList 构建过程及 `damage` 分发。

### 关联章节
- 7.12
- 渲染架构篇。

### 外部 review 来源
- 外部 AI review (Gemini)


## [2026-04-23] 7.13 SystemUI 性能分析 — 知识盲区

### 盲区描述
Perfetto SQL 在多进程转场分析中的应用

### 重要程度
低

### 建议研究方向
总结一套用于同时拉齐 SystemUI、Launcher3、WM Shell 和 SurfaceFlinger 关键 slice 的标准 SQL 查询脚本。

### 关联章节
- 7.13


### 外部 review 来源
- 外部 AI review (Gemini)


## [2026-04-23] 7.13 SystemUI 性能分析 — 知识盲区

### 盲区描述
在复杂的跨进程转场（WM Shell + Launcher3 + SystemUI + App）中，如何利用 Perfetto SQL 快速清洗出导致卡顿的关键路径。

### 重要程度
低

### 建议研究方向
研究并沉淀一套针对 App 启动/退出动画卡顿的 Perfetto 分析模板或脚本。

### 关联章节
- 7.13
- 13.7 Perfetto 高级用法。

### 外部 review 来源
- 外部 AI review (Gemini)


## [2026-04-23] 7.14 GAPS：Android 动态分析目标可达性路径重建 — 知识盲区

### 盲区描述
GAPS 等自动化测试工具对 Jetpack Compose 的支持进展

### 重要程度
中

### 建议研究方向
持续关注基于 UIAutomator 体系的最新学术工具如何解决 Compose 节点语义树重建的问题。

### 关联章节
- 7.14


### 外部 review 来源
- 外部 AI review (Gemini)


## [2026-04-23] 7.14 GAPS：Android 动态分析目标可达性路径重建 — 知识盲区

### 盲区描述
学术界现有 GUI 动态遍历工具（如 GAPS、APE、Guardian 等）在处理 Jetpack Compose 应用时的技术瓶颈及突破方案。

### 重要程度
中

### 建议研究方向
梳理 Compose Semantics 树与传统 View 树在 Accessibility Service 解析上的差异，跟进最新解决方案。

### 关联章节
- 7.14
- 7.7 Compose 性能优化。

### 外部 review 来源
- 外部 AI review (Gemini)


## [2026-04-23] 7.15 场景化性能作战手册 — 知识盲区

### 盲区描述
BufferStuffing 在 Perfetto 中的精确定位

### 重要程度
中

### 建议研究方向
详细总结如何在 Perfetto 中通过 SurfaceFlinger 的 Latch 行为和 App 侧的 `FrameTimeline` 确诊 BufferStuffing。

### 关联章节
- 7.15


### 外部 review 来源
- 外部 AI review (Gemini)


## [2026-04-23] 7.15 场景化性能作战手册 — 知识盲区

### 盲区描述
排障手册中提到的现象（如 BufferStuffing、调度饥饿、LMKD 杀进程）对应的具体 Perfetto SQL 查询或 UI 视图特征。

### 重要程度
中

### 建议研究方向
沉淀一份《Perfetto 高频排障字典》，将现象映射到具体的 SQL 查询语句。

### 关联章节
- 7.15
- 13.7 Perfetto 高级用法。

### 外部 review 来源
- 外部 AI review (Gemini)


## [2026-04-23] 9.1 ANR 设计思想 — 知识盲区

### 盲区描述
ANR 过程中的 Dump 卡顿阻塞：当目标进程极其卡顿或遭遇长时间锁等待时，SIGQUIT 触发的虚拟机 dump 过程本身是否会因为超时而被截断，从而留下不完整的 traces.txt。

### 重要程度
中

### 建议研究方向
- art/runtime/signal_catcher.cc 中 SIGQUIT 后的线程暂停与挂起等待超时机制
- traces.txt 不完整场景的系统侧证据

### 关联章节
- 9.1, 9.3

### 外部 review 来源
- Gemini 外部 review
## [2026-04-23] 9.2 ANR 类型与触发条件 — 知识盲区

### 盲区描述
ContentProvider 客户端查询超时机制：官方引入了 CancellationSignal 和 API 31+ 的 getProviderMimeTypeAsync()，但系统侧是否有主动的 Watchdog 机制干预客户端长时阻塞。

### 重要程度
中

### 建议研究方向
- ContentProviderNative.java 和 ContentResolver.java 中的客户端超时处理
- Binder 枯竭之外是否有系统侧主动干预

### 关联章节
- 9.2, 9.4

### 外部 review 来源
- Gemini 外部 review
## [2026-04-23] 9.3 ANR 分析方法 — 知识盲区

### 盲区描述
GWP-ASan 与 Native 层 ANR 排查：当 traces.txt 长期卡在 Native 层某个库调用时，如何结合 GWP-ASan 或 HWASan 确认是否因内存踩踏或死锁导致不可恢复阻塞。

### 重要程度
中

### 建议研究方向
- Android 11+ GWP-ASan 生产环境 Native 内存错误采样
- ApplicationExitInfo.getTraceInputStream 在多进程共享场景下的读取限制

### 关联章节
- 9.3, 10.1

### 外部 review 来源
- Gemini 外部 review
## [2026-04-23] 9.4 特殊场景的 ANR — 知识盲区

### 盲区描述
FileObserver 与隐性 I/O ANR：部分第三方 SDK 过度使用 FileObserver 监听文件变化，是否会在高频 I/O 时引发内核层面的 inotify 锁竞争并导致主线程 ANR。

### 重要程度
中

### 建议研究方向
- Linux kernel fsnotify 机制在极高并发下的表现
- AOSP bug tracker 中 inotify 相关 ANR issue

### 关联章节
- 9.4

### 外部 review 来源
- Gemini 外部 review
## [2026-04-23] 9.5 案例集 — 知识盲区

### 盲区描述
Looper.Observer 在 Android 16+ 的合规性：文章使用 Hidden API 实现 LooperMonitor，在 Android 16+ 收紧 Non-SDK 接口后，是否有官方 Looper Profiling API 替代。

### 重要程度
低

### 建议研究方向
- Android 16+ 非 SDK 接口灰/黑名单更新
- APM 厂商是否有特权接口

### 关联章节
- 9.5

### 外部 review 来源
- Gemini 外部 review
## [2026-04-23] 9.6 Notification 性能与 ANR — 知识盲区

### 盲区描述
大量图片通知导致 SystemUI 崩溃：应用滥用大图且频繁更新时，是否会引发 TransactionTooLargeException 或导致 SystemUI 进程 OOM。

### 重要程度
中

### 建议研究方向
- NotificationManager.java 中 Parcel 序列化大小限制
- RemoteViews 跨进程膨胀的内存边界

### 关联章节
- 9.6

### 外部 review 来源
- Gemini 外部 review
## [2026-04-23] 9.7 ANR 非技术故障诊断 — 知识盲区

### 盲区描述
厂商定制的 App 冻结策略黑盒：国产 ROM 的"神仙秒杀"、"墓碑机制"通常绕过标准 am_freeze 日志，如何在 Perfetto 或内核日志中识别这些私有冻结行为引发的"伪 ANR"。

### 重要程度
高

### 建议研究方向
- Linux kernel cgroup v1/v2 freezer 状态在 Perfetto ftrace 中的特征
- 各大厂商 ROM 冻结机制的逆向分析

### 关联章节
- 9.7, 17.1

### 外部 review 来源
- Gemini 外部 review
## [2026-04-23] 10.1 App 内存分析 — 知识盲区

### 盲区描述
GWP-ASan 在生产环境的应用：Android 11+ 引入的 GWP-ASan 专为线上生产环境 Native 内存错误采样设计，开销极低，可作为 ASan/HWASan 的线上补充。

### 重要程度
中

### 建议研究方向
- Android 官方 GWP-ASan 集成与崩溃日志上报指南
- 与 ASan/HWASan 的定位差异

### 关联章节
- 10.1, 10.2

### 外部 review 来源
- Gemini 外部 review
## [2026-04-23] 10.2 内存泄漏 — 知识盲区

### 盲区描述
fork 子进程 Dump 的底层限制：线上 OOM 监控常使用 fork 子进程抓取 Hprof（如 Koom），但在 Android 10+ 部分厂商魔改系统上，fork 可能受 SELinux 或 cgroup 限制而失败。

### 重要程度
中

### 建议研究方向
- Koom 官方 GitHub Issue 中各种定制 ROM 兼容性填坑经验
- SELinux / cgroup 对 fork 子进程的约束边界

### 关联章节
- 10.2

### 外部 review 来源
- Gemini 外部 review
## [2026-04-23] 10.3 内存持续增长 — 知识盲区

### 盲区描述
GKI 2.0 对 Native 内存碎片的透明整合：Android 12+ 引入的 GKI 及 MGLRU 等内核特性是否在系统底层进一步缓解了 App 视角的物理碎片化感知。

### 重要程度
中

### 建议研究方向
- Linux 内核 MGLRU 与 Android GKI 的协同
- App 视角下物理碎片化的可观测性变化

### 关联章节
- 10.3, 10.4

### 外部 review 来源
- Gemini 外部 review
## [2026-04-23] 10.4 低内存对系统性能的影响 — 知识盲区

### 盲区描述
eBPF 在内存压力精准归因中的应用：现代 Android 性能团队是否开始使用 eBPF 来精确统计哪行代码触发了最多的 Direct Reclaim 耗时。

### 重要程度
中

### 建议研究方向
- AOSP system/bpf 目录中 BPF 工具
- Linux BPF 社区针对 Android 内存延迟监控的实践

### 关联章节
- 10.4

### 外部 review 来源
- Gemini 外部 review
## [2026-04-23] 10.5 案例集 — 知识盲区

### 盲区描述
GWP-ASan 对闭源 GPU 驱动内部泄漏的可见性：类似 renderD128 驱动层缓存池导致的虚拟内存爆掉，在开启 GWP-ASan 或 hwasan 时能否在内核崩溃日志中提供更多线索。

### 重要程度
中

### 建议研究方向
- Linux kernel DRM 驱动子系统的缓冲分配
- GKI 对闭源 GPU 驱动的约束

### 关联章节
- 10.5

### 外部 review 来源
- Gemini 外部 review
## [2026-04-23] 10.6 内存抖动与频繁 GC — 知识盲区

### 盲区描述
userfaultfd 在 ART CMC GC 中的具体应用：Android 15 引入 CMC GC 的核心依赖是 Linux 内核的 userfaultfd 机制，该机制如何在对像搬移（compaction）阶段实现对应用线程的零停顿缺页陷入接管。

### 重要程度
高

### 建议研究方向
- art/runtime/gc/collector/mark_compact.cc 源码
- Linux 内核 userfaultfd 特性文档

### 关联章节
- 10.6, 4.8

### 外部 review 来源
- Gemini 外部 review
## [2026-04-23] 10.7 SQLite/Room 数据库性能优化 — 知识盲区

### 盲区描述
io_uring 在 SQLite I/O 路径上的应用：近期 Linux 和 Android 内核对 io_uring 异步 I/O 的支持逐渐成熟，SQLite 未来是否可能利用 io_uring 进一步降低 WAL 写入和 fsync() 阻塞。

### 重要程度
低

### 建议研究方向
- SQLite 官方邮件列表关于 io_uring 的讨论
- Android Bionic C 库对 io_uring 接口的开放情况

### 关联章节
- 10.7

### 外部 review 来源
- Gemini 外部 review


## [2026-04-24] 18.13 WebView 渲染管线 — 知识盲区

### 盲区描述
SurfaceControl 独立子 Surface 在不同 WebView provider / Chromium milestone / channel 下的启用边界缺少版本矩阵。当前只按 Android major version 讨论，无法回答“这台设备当前 provider 是否真的具备这条路径”。

### 重要程度
高

### 建议研究方向
- 对比 Android System WebView Stable / Beta / Canary 与不同 Chromium milestone 下的 SurfaceControl overlay rollout
- 收集 `dumpsys webviewupdate`、provider version、Perfetto、`dumpsys SurfaceFlinger` 的成组样本
- 核验 `OverlayProcessorWebView` 相关默认条件在不同 provider 版本中的变化

### 关联章节
18.13, 18.10, 7.11


## [2026-04-24] 综合外部 Review 知识盲区

- **盲区描述**: ---
- **重要程度**: ---
- **建议研究方向**: ---
- **关联章节**: 19.01
- **外部 review 来源**: 2026-04-24

- **盲区描述**: APM 自身引发的性能退化
- **重要程度**: 高
- **建议研究方向**: APM 的采集开销（如频繁 dump Hprof、高频 trace）如何量化，线上应如何设计自保/降级策略。
- **关联章节**: 19.01
- **外部 review 来源**: 2026-04-24

- **盲区描述**: Session ID 与 Trace ID 的链路追踪
- **重要程度**: 高
- **建议研究方向**: 客户端一次滑动卡顿，如何通过 session id 关联到当次的网络请求和日志。
- **关联章节**: 19.01
- **外部 review 来源**: 2026-04-24

- **盲区描述**: ---
- **重要程度**: ---
- **建议研究方向**: ---
- **关联章节**: 19.11
- **外部 review 来源**: 2026-04-24

- **盲区描述**: Compose 局部重组（Recomposition）与 JankStats 回调的触发关系
- **重要程度**: 高
- **建议研究方向**: Compose 的 Phase（Composition, Layout, Draw）发生耗时时，如果局部重组没有引发底层的 View `draw`，JankStats 是否能全量捕获，或是否会存在监控盲区。
- **关联章节**: 19.11
- **外部 review 来源**: 2026-04-24

- **盲区描述**: ---
- **重要程度**: ---
- **建议研究方向**: ---
- **关联章节**: 19.12
- **外部 review 来源**: 2026-04-24

- **盲区描述**: FrameMetrics 的 C++ 层 API 替代方案
- **重要程度**: 高
- **建议研究方向**: 在 Android 早期，FrameMetrics Java API 存在一定的 JNI 转换和对象分配开销。是否可以通过底层 Hook `Choreographer` 或直接使用 NDK `AChoreographer` 获取同等数据以降低线上开销。
- **关联章节**: 19.12
- **外部 review 来源**: 2026-04-24

- **盲区描述**: ---
- **重要程度**: ---
- **建议研究方向**: ---
- **关联章节**: 19.02
- **外部 review 来源**: 2026-04-24

- **盲区描述**: PLT Hook 在高版本 Android 的兼容性
- **重要程度**: 高
- **建议研究方向**: Matrix 等 APM 强依赖 PLT Hook / Inline Hook。需调研 Android 14/15 之后 linker namespace 限制对这部分功能的影响。
- **关联章节**: 19.02
- **外部 review 来源**: 2026-04-24

- **盲区描述**: ---
- **重要程度**: ---
- **建议研究方向**: ---
- **关联章节**: 19.14
- **外部 review 来源**: 2026-04-24

- **盲区描述**: Android Studio 对 Benchmark 报告的集成展示
- **重要程度**: 中
- **建议研究方向**: 目前的 Benchmark 除了输出 JSON 以外，在 AS 内的直接查看（特别是指向 Perfetto 的超链接）体验如何。
- **关联章节**: 19.14
- **外部 review 来源**: 2026-04-24

- **盲区描述**: ---
- **重要程度**: ---
- **建议研究方向**: ---
- **关联章节**: 19.09
- **外部 review 来源**: 2026-04-24

- **盲区描述**: Measure 与 OpenTelemetry 规范的具体对接
- **重要程度**: 中
- **建议研究方向**: 移动端 Session 事件是否能通过 OpenTelemetry Collector 直接转发至 Jaeger / Grafana 等通用后端，以降低自研后端的成本。
- **关联章节**: 19.09
- **外部 review 来源**: 2026-04-24

- **盲区描述**: ---
- **重要程度**: ---
- **建议研究方向**: ---
- **关联章节**: 19.04
- **外部 review 来源**: 2026-04-24

- **盲区描述**: ART 方法追踪在 Android 15 (API 35) 上的兼容性
- **重要程度**: 高
- **建议研究方向**: btrace 3.0 README 提到 Android 15 限制，需调研后续版本的插桩或 tracing API 是否受限于系统安全策略的收紧。
- **关联章节**: 19.04
- **外部 review 来源**: 2026-04-24

- **盲区描述**: ---
- **重要程度**: ---
- **建议研究方向**: ---
- **关联章节**: 19.07
- **外部 review 来源**: 2026-04-24

- **盲区描述**: DoKit 获取 CPU 信息的兼容性限制
- **重要程度**: 中
- **建议研究方向**: 随着高版本 Android 对 `/proc/stat` 读取权限的收紧，这类工具获取系统级负载的手段是否依然有效。
- **关联章节**: 19.07
- **外部 review 来源**: 2026-04-24

- **盲区描述**: ---
- **重要程度**: ---
- **建议研究方向**: ---
- **关联章节**: 19.06
- **外部 review 来源**: 2026-04-24

- **盲区描述**: Looper 机制在 Android 14+ 的微调
- **重要程度**: 低
- **建议研究方向**: Android 框架层是否有绕过 Printer 或改变 Message 投递顺序的新优化，对 BlockCanary 的精度影响。
- **关联章节**: 19.06
- **外部 review 来源**: 2026-04-24

- **盲区描述**: ---
- **重要程度**: ---
- **建议研究方向**: ---
- **关联章节**: 19.08
- **外部 review 来源**: 2026-04-24

- **盲区描述**: ASM AOP 织入在 AGP 8.0+ 移除 Transform 后的替代方案
- **重要程度**: 高
- **建议研究方向**: 老 APM 最大的兼容性痛点。需整理 `AsmClassVisitorFactory` 的迁移成本。
- **关联章节**: 19.08
- **外部 review 来源**: 2026-04-24

- **盲区描述**: ---
- **重要程度**: ---
- **建议研究方向**: ---
- **关联章节**: 19.05
- **外部 review 来源**: 2026-04-24

- **盲区描述**: LeakCanary (Shark) 的 Hprof 解析开销
- **重要程度**: 中
- **建议研究方向**: Shark 是如何改进早期 HAHA 库的内存占用的，这对于理解本地 dump 时的内存飙升（OutOfMemoryError 甚至会发生在解析阶段本身）有帮助。
- **关联章节**: 19.05
- **外部 review 来源**: 2026-04-24

- **盲区描述**: ---
- **重要程度**: ---
- **建议研究方向**: ---
- **关联章节**: 19.15
- **外部 review 来源**: 2026-04-24

- **盲区描述**: 国内各大应用市场对 AAB 及 Cloud Profiles 的支持现状
- **重要程度**: 高
- **建议研究方向**: 在脱离 Google Play 的国内碎片化商店分发环境下，Baseline Profiles 的首装 AOT 收益到底能保留多少？这直接决定了国内大厂的投入产出比。
- **关联章节**: 19.15
- **外部 review 来源**: 2026-04-24

- **盲区描述**: ---
- **重要程度**: ---
- **建议研究方向**: ---
- **关联章节**: 19.03
- **外部 review 来源**: 2026-04-24

- **盲区描述**: Android 15 ProfilingManager 与 KOOM 的功能重叠
- **重要程度**: 中
- **建议研究方向**: Android 15 引入了原生的 ProfilingManager 支持按需 heap dump。需评估未来 KOOM 的架构是否会向系统 API 迁移，或如何与之共存。
- **关联章节**: 19.03
- **外部 review 来源**: 2026-04-24

- **盲区描述**: ---
- **重要程度**: ---
- **建议研究方向**: ---
- **关联章节**: 19.13
- **外部 review 来源**: 2026-04-24

- **盲区描述**: Kotlin 协程与 Async Trace 的结合
- **重要程度**: 高
- **建议研究方向**: 协程是挂起/恢复执行的，跨线程跳跃频繁，如何用 `beginAsyncSection` 优雅地包装一个 Coroutine Job 的完整耗时。
- **关联章节**: 19.13
- **外部 review 来源**: 2026-04-24

- **盲区描述**: ---
- **重要程度**: ---
- **建议研究方向**: ---
- **关联章节**: 19.10
- **外部 review 来源**: 2026-04-24

- **盲区描述**: 高版本 Android 对开源轻量级采集手段的封堵
- **重要程度**: 高
- **建议研究方向**: 例如 `TrafficStats` 在更高版本受限于网络命名空间或 eBPF 流量统计的演进，旧方案可能失效。
- **关联章节**: 19.10
- **外部 review 来源**: 2026-04-24


## [2026-04-24] 19.16 ProfilingManager — 知识盲区

### 盲区描述
Android 16+ trigger 式 profiling 的设备覆盖、API level 36 与 extension version 36.1 的落点，以及 trigger 自身的冷却/限流配置边界仍需继续核对。external-review 已命中这一点。

### 重要程度
中

### 建议研究方向
- 核对 addProfilingTriggers / clearProfilingTriggers / removeProfilingTriggersByType 的 API 36 边界
- 核对 addAllProfilingTriggers 的 extension version 36.1 条件与实际设备覆盖
- 梳理 ProfilingTrigger 的 trigger 级 rate limiting 与系统级 rate limiting 的关系

### 关联章节
19.1, 19.16

### 外部 review 来源
- external-review 已命中（2026-04-24-15-19.16-external-review.md)

## [2026-04-24] 19.17 Firebase Performance — 知识盲区

### 盲区描述
Firebase 自动网络采集对不同 Android 网络栈的覆盖边界没有在章节里展开，尤其是自研网络层、Cronet 或 JNI/C++ 网络库是否需要手工补 trace。external-review 已命中这一点。

### 重要程度
中

### 建议研究方向
- 核对 Firebase Android SDK 对自动 network trace 的覆盖前提
- 梳理自动采集失效时的手工 network trace 兜底方式
- 补一张“自动采集 / 手工采集 / 无法采集”的网络栈边界表

### 关联章节
12.7, 19.17

### 外部 review 来源
- external-review 已命中（2026-04-24-15-19.17-external-review.md)

## [2026-04-24] 19.18 商业 APM 平台 — 知识盲区

### 盲区描述
商业 APM 的 profiling / tracing 采样在真实设备上的稳定性折损还缺少一手实测，尤其是 Sentry Android profiling 对 Android runtime tracer 的已知 crash 风险与厂商设备差异。external-review 已命中这一点。

### 重要程度
中

### 建议研究方向
- 收集 Sentry Android profiling 在真实机型上的已知问题与采样建议
- 对比商业 APM SDK 在低端机上的线程数、启动耗时和电量开销
- 把“可开功能清单”和“建议默认关闭功能清单”拆出来

### 关联章节
19.18

### 外部 review 来源
- external-review 已命中（2026-04-24-15-19.18-external-review.md)


## [2026-04-24] 19.23 网络 APM 底层捕获原理 — 知识盲区

### 盲区描述
OkHttp 最新版中 EventListener 的生命周期回调与 APM 埋点的时序对应关系尚未研究

### 重要程度
中

### 建议研究方向
- 核验 OkHttp EventListener 各回调（callStart/dnsStart/connectStart/requestStart/responseStart/callEnd）与 APM 网络阶段拆分的精确时序映射

### 关联章节
19.23

### 外部 review 来源
- Gemini 外部 review (2026-04-24-15-19.23)

## [2026-04-24] 19.24 崩溃与 ANR 捕获机制 — 知识盲区

### 盲区描述
Android 11+ 对 /data/anr 目录读取权限封堵的具体官方描述与替代方案

### 重要程度
高

### 建议研究方向
- 核对 ApplicationExitInfo（API 30+）对传统 /data/anr traces 文件读取的替代关系，以及低版本兼容策略

### 关联章节
19.24, 9.2, 9.3

### 外部 review 来源
- Gemini 外部 review (2026-04-24-15-19.24)

## [2026-04-24] 19.25 耗电与发热监控 — 知识盲区

### 盲区描述
Thermal API 中各 THERMAL_STATUS_xxx 状态码的具体触发温度范围与系统反应

### 重要程度
中

### 建议研究方向
- 收集不同 SoC/设备上 PowerManager.THERMAL_STATUS_* 各级别的触发阈值与降级行为差异

### 关联章节
19.25

### 外部 review 来源
- Gemini 外部 review (2026-04-24-15-19.25)

## [2026-04-24] 19.26 混合栈与跨平台 APM — 知识盲区

### 盲区描述
Flutter 官方 FrameTiming API 的渲染管线映射与 Android Choreographer 的对应关系

### 重要程度
高

### 建议研究方向
- 核验 Flutter FrameTiming 中 build/draw/raster/presentation 各阶段与 Android 渲染管线的精确映射，确保跨平台 APM 指标口径一致

### 关联章节
19.26, 7.7

### 外部 review 来源
- Gemini 外部 review (2026-04-24-15-19.26)

## [2026-04-24] 19.27 千万级 DAU 的 APM 端侧架构 — 知识盲区

### 盲区描述
Linux mmap 的 Page Cache 落盘机制在 Android 系统遭遇 OOM/SigKill 时的真实表现

### 重要程度
高

### 建议研究方向
- 研究 mmap MAP_SHARED 在 Android 低内存场景下 Page Cache 回收策略，以及 APM 端侧 mmap 高可靠存储的丢失边界

### 关联章节
19.27

### 外部 review 来源
- Gemini 外部 review (2026-04-24-15-19.27)

## [2026-04-24] 19.20 SoloPi 与 Emmagee — 知识盲区

### 盲区描述
SoloPi 缺少现代 Android / AGP 兼容矩阵。当前可查官方基线仍是 AGP 4.0.2、compileSdk/targetSdk 29、release v0.12.0（2022），书稿却按 Android 8-17 统一适用处理，未覆盖 Android 12+ 无障碍、悬浮窗、无线 ADB 和 targetSdk 31+ 行为变化。

### 重要程度
高

### 建议研究方向
- 核对 SoloPi 在 Android 12/13/14/15 上的已知兼容 issue、厂商 ROM 限制与 workaround
- 验证 AGP 7/8、compileSdk 34/35 下的可编译性与 targetSdk 提升成本
- 补充无障碍、悬浮窗、无线调试在主流厂商 ROM 上的权限差异和失败表现

### 关联章节
19.19, 19.20


## [2026-04-24] 19.22 存储 Benchmark（AndroBench、A1 SD Bench） — 知识盲区

### 盲区描述
AndroBench / A1 SD Bench 在 Android 10-17 的现代存储模型下还能稳定覆盖哪些路径，当前缺少一手核验。尤其是 scoped storage、app-specific external、SAF/MediaStore、可移除 SD/USB 目录在不同 targetSdk 和 ROM 上的可测边界，正文还没有证据链。

### 重要程度
中

### 建议研究方向
- 核验 AndroBench 与 A1 SD Bench 在 Android 13/14/15/16/17 上的实际可运行性与权限前提
- 拆清 app 内部目录、app-specific external、共享媒体目录、SAF tree URI、可移除 SD/USB 的可测范围
- 记录主流 ROM 上 scoped storage、文件管理授权、USB/SD 挂载差异对 benchmark 结果的影响

### 关联章节
19.22, 6.2, 19.27

## [2026-04-25] 19.01  — 知识盲区

### 盲区描述
符号化与反混淆体系（Mapping/Build-ID 关联）

### 重要程度
高

### 建议研究方向
APM 客户端 SDK 如何在编译期生成并上报唯一构建标识，以便服务端关联符号表。

### 关联章节
- 19.01

### 外部 review 来源
- 外部 AI review

## [2026-04-25] 19.01  — 知识盲区

### 盲区描述
ApplicationExitInfo 性能开销

### 重要程度
中

### 建议研究方向
调研 `getHistoricalProcessExitReasons()` 在极端情况下的 Binder 耗时，及最佳调用时机（后台线程）。

### 关联章节
- 19.01

### 外部 review 来源
- 外部 AI review

## [2026-04-25] 19.02  — 知识盲区

### 盲区描述
Matrix AGP 8 插桩适配方案

### 重要程度
高

### 建议研究方向
查阅 `AsmClassVisitorFactory` 官方文档及社区 Matrix AGP8 适配方案（如 Github issue #888）。

### 关联章节
- 19.02

### 外部 review 来源
- 外部 AI review

## [2026-04-25] 19.02  — 知识盲区

### 盲区描述
methodMapping 编译期生成与反解机制

### 重要程度
高

### 建议研究方向
查阅 `matrix-gradle-plugin` 源码中关于 MethodTracer 和 id 分配的逻辑。

### 关联章节
- 19.02

### 外部 review 来源
- 外部 AI review

## [2026-04-25] 19.02  — 知识盲区

### 盲区描述
Battery Canary 系统级 Hook 原理及兼容性

### 重要程度
中

### 建议研究方向
分析 Battery Canary 监控 Wakelock 和 Alarm 时对系统 Service 的 Hook 点（如 `PowerManagerService`）。

### 关联章节
- 19.02

### 外部 review 来源
- 外部 AI review

## [2026-04-25] 19.03  — 知识盲区

### 盲区描述
Fork 后的多线程死锁风险及解决策略

### 重要程度
高

### 建议研究方向
深入研究 Linux `fork()` 系统调用在存在多线程的 ART 环境下造成的锁状态不一致问题，以及 KOOM 是如何通过特定的线程挂起或 `pthread_atfork` 机制来绕过这一难点的。

### 关联章节
- 19.03

### 外部 review 来源
- 外部 AI review

## [2026-04-25] 19.03  — 知识盲区

### 盲区描述
SELinux 策略对 Fork Dump 的进一步限制

### 重要程度
中

### 建议研究方向
调查 Android 14/15 中 SELinux 策略对 App fork 行为、高权限内存读取和指定目录文件写入带来的限制及适配方案。

### 关联章节
- 19.03

### 外部 review 来源
- 外部 AI review

## [2026-04-25] 19.04  — 知识盲区

### 盲区描述
Btrace 插桩对不同版本 ART 性能的实际影响

### 重要程度
中

### 建议研究方向
探究在 Android 12+ 上的 AOT 编译机制是否会放大插桩带来的方法退化开销，导致在低端机上采集的耗时比例失真严重。

### 关联章节
- 19.04

### 外部 review 来源
- 外部 AI review

## [2026-04-25] 19.05  — 知识盲区

### 盲区描述
官方 Instrumentation 测试集成方案

### 重要程度
高

### 建议研究方向
研究 `leakcanary-android-instrumentation` 的接入与自动断言机制

### 关联章节
- 19.05

### 外部 review 来源
- 外部 AI review

## [2026-04-25] 19.05  — 知识盲区

### 盲区描述
LeakCanary Service 自动监听原理

### 重要程度
中

### 建议研究方向
`ServiceWatcher` 如何通过反射拦截生命周期

### 关联章节
- 19.05

### 外部 review 来源
- 外部 AI review

## [2026-04-25] 19.06  — 知识盲区

### 盲区描述
`Looper.Printer` 的内存抖动开销

### 重要程度
高

### 建议研究方向
研究 `Looper.loop()` 源码中的字符串分配逻辑，以及它在 Vsync 高频场景下的 GC 影响，这是理解所有旧版 APM 缺陷的关键。

### 关联章节
- 19.06

### 外部 review 来源
- 外部 AI review

## [2026-04-25] 19.06  — 知识盲区

### 盲区描述
`Thread.getStackTrace()` 性能开销

### 重要程度
高

### 建议研究方向
结合 ART 源码了解抓取其他线程堆栈时的虚拟机行为和性能损耗。

### 关联章节
- 19.06

### 外部 review 来源
- 外部 AI review

## [2026-04-25] 19.06  — 知识盲区

### 盲区描述
`Looper.Observer` 隐藏 API

### 重要程度
中

### 建议研究方向
查看 Android 9+ 中 `Looper` 增加的 Observer 机制，及现代 APM 如何设法适配调用它。

### 关联章节
- 19.06

### 外部 review 来源
- 外部 AI review

## [2026-04-25] 19.07  — 知识盲区

### 盲区描述
AGP 8.0+ 下的编译期插桩（Transform）替代方案

### 重要程度
高

### 建议研究方向
DoKit 原本强依赖 AGP Transform API，但 AGP 8.0+ 已全面废弃 Transform。需要深入研究 DoKit 是如何适配（或是否兼容）AGP 8.x 的 AsmClassVisitorFactory 机制的。这决定了 DoKit 在当今最新 Android 项目中的生命力。

### 关联章节
- 19.07

### 外部 review 来源
- 外部 AI review

## [2026-04-25] 19.08  — 知识盲区

### 盲区描述
现代 AGP 的 Transform 替代方案

### 重要程度
高

### 建议研究方向
研究从老旧的 `Transform API`（ArgusAPM 时代）向现代 AGP 7.0/8.0+ 的 `AsmClassVisitorFactory` 迁移的过程中，APM 插件如何适配。

### 关联章节
- 19.08

### 外部 review 来源
- 外部 AI review

## [2026-04-25] 19.09  — 知识盲区

### 盲区描述
现代 APM 的跨版本 ANR 捕获机制演进

### 重要程度
中

### 建议研究方向
研究 AOSP 中 `ApplicationExitInfo` 的引入机制，对比旧版本的 Signal Catcher，了解类似 Measure 的框架是如何抹平这些版本差异的。

### 关联章节
- 19.09

### 外部 review 来源
- 外部 AI review

## [2026-04-25] 19.10  — 知识盲区

### 盲区描述
现代 APM 插桩适配方案

### 重要程度
高

### 建议研究方向
研究 `AsmClassVisitorFactory` 替代 `Transform` API 后的工程落地实践，这是后续所有自研或更新 APM 必踩的坑。

### 关联章节
- 19.10

### 外部 review 来源
- 外部 AI review

## [2026-04-25] 19.10  — 知识盲区

### 盲区描述
低版本 Android 重采样降级方案

### 重要程度
中

### 建议研究方向
在缺乏 `ProfilingManager` 的 Android 14 及以下设备中，APM 该如何更安全地唤起系统 trace 并回收文件。

### 关联章节
- 19.10

### 外部 review 来源
- 外部 AI review

## [2026-04-25] 19.12  — 知识盲区

### 盲区描述
SurfaceView 渲染监控

### 重要程度
中

### 建议研究方向
说明 `FrameMetrics` 无法监控 `SurfaceView` 内部渲染，需使用 `SurfaceControl.OnReparentListener` 或其他手段。

### 关联章节
- 19.12

### 外部 review 来源
- 外部 AI review

## [2026-04-25] 19.12  — 知识盲区

### 盲区描述
Chereographer 交互

### 重要程度
低

### 建议研究方向
API 31 后 `Choreographer.FrameData` 与 `FrameMetrics` 的关系。

### 关联章节
- 19.12

### 外部 review 来源
- 外部 AI review

## [2026-04-25] 19.13  — 知识盲区

### 盲区描述
协程追踪 (traceCoroutine)

### 重要程度
高

### 建议研究方向
`androidx.tracing:tracing:2.0.0` 针对协程挂起点的原生支持机制

### 关联章节
- 19.13

### 外部 review 来源
- 外部 AI review

## [2026-04-25] 19.13  — 知识盲区

### 盲区描述
Perfetto SDK (Track Event)

### 重要程度
中

### 建议研究方向
如何通过 Perfetto SDK 写入比 `androidx.tracing` 更丰富的 key-value 参数

### 关联章节
- 19.13

### 外部 review 来源
- 外部 AI review

## [2026-04-25] 19.13  — 知识盲区

### 盲区描述
ATrace 运行成本

### 重要程度
低

### 建议研究方向
`beginSection` / `endSection` 的具体指令开销，以及在高频循环（Hot Path）中的影响

### 关联章节
- 19.13

### 外部 review 来源
- 外部 AI review

## [2026-04-25] 19.14  — 知识盲区

### 盲区描述
Microbenchmark 的 DCE 问题

### 重要程度
高

### 建议研究方向
`Blackhole.consume()` 的底层实现原理及在 AOT 下的作用机制。

### 关联章节
- 19.14

### 外部 review 来源
- 外部 AI review

## [2026-04-25] 19.14  — 知识盲区

### 盲区描述
ProfileInstaller 的广播触发机制

### 重要程度
中

### 建议研究方向
深入探究 Macrobenchmark 是如何跨进程触发 `androidx.profileinstaller.action.INSTALL_PROFILE` 的。

### 关联章节
- 19.14

### 外部 review 来源
- 外部 AI review

## [2026-04-25] 19.16  — 知识盲区

### 盲区描述
Minor SDK 识别机制

### 重要程度
高

### 建议研究方向
Android 16+ `Build.VERSION.SDK_INT_FULL` 与 SDK Extensions 的关系。

### 关联章节
- 19.16

### 外部 review 来源
- 外部 AI review

## [2026-04-25] 19.16  — 知识盲区

### 盲区描述
脱敏（Redaction）机制

### 重要程度
中

### 建议研究方向
Perfetto Trace 在生成时如何过滤非本进程信息，确保隐私合规。

### 关联章节
- 19.16

### 外部 review 来源
- 外部 AI review

## [2026-04-25] 19.16  — 知识盲区

### 盲区描述
系统配额（Cost Quota）具体数值

### 重要程度
低

### 建议研究方向
不同采集类型（Heap Dump vs Trace）在系统内部消耗的“成本”权重。

### 关联章节
- 19.16

### 外部 review 来源
- 外部 AI review

## [2026-04-25] 19.17  — 知识盲区

### 盲区描述
Fragment 自动追踪开关

### 重要程度
高

### 建议研究方向
确认是否可以通过 Manifest 像 Activity 一样单独关闭。

### 关联章节
- 19.17

### 外部 review 来源
- 外部 AI review

## [2026-04-25] 19.17  — 知识盲区

### 盲区描述
URL Pattern 数量上限

### 重要程度
中

### 建议研究方向
每个 App ID 的 URL Pattern 聚合上限（通常为 400）。

### 关联章节
- 19.17

### 外部 review 来源
- 外部 AI review

## [2026-04-25] 19.17  — 知识盲区

### 盲区描述
离线数据保留时长

### 重要程度
中

### 建议研究方向
事件在设备本地存储的有效期（离线模式下）。

### 关联章节
- 19.17

### 外部 review 来源
- 外部 AI review

## [2026-04-25] 19.18  — 知识盲区

### 盲区描述
16KB Page Size 对 Native SDK 的性能损耗

### 重要程度
高

### 建议研究方向
研究对齐 16KB 后，原生库体积和加载性能的变化。

### 关联章节
- 19.18

### 外部 review 来源
- 外部 AI review

## [2026-04-25] 19.18  — 知识盲区

### 盲区描述
商业 APM 对 HarmonyOS NEXT 的原生支持

### 重要程度
中

### 建议研究方向
Bugly 和 APMPlus 均已开始适配鸿蒙原生，可补充作为跨端考量。

### 关联章节
- 19.18

### 外部 review 来源
- 外部 AI review

## [2026-04-25] 19.19  — 知识盲区

### 盲区描述
GPU 采集路径

### 重要程度
中

### 建议研究方向
补充 Adreno (`/sys/class/kgsl/kgsl-3d0/`) 和 Mali (`/sys/class/misc/mali0/device/`) 的 sysfs 路径差异。

### 关联章节
- 19.19

### 外部 review 来源
- 外部 AI review

## [2026-04-25] 19.19  — 知识盲区

### 盲区描述
Android 16 QPR 限制

### 重要程度
高

### 建议研究方向
研究 Android 16 对 GPU syscall filtering 的影响及 PerfDog 的应对方案。

### 关联章节
- 19.19

### 外部 review 来源
- 外部 AI review

## [2026-04-25] 19.20  — 知识盲区

### 盲区描述
Android 14 前台服务类型声明

### 重要程度
中

### 建议研究方向
调研 SoloPi 在 Android 14 下是否因未声明 `mediaProjection` 或 `specialUse` 类型而导致崩溃。

### 关联章节
- 19.20

### 外部 review 来源
- 外部 AI review

## [2026-04-25] 19.20  — 知识盲区

### 盲区描述
无线 ADB 提权稳定性

### 重要程度
低

### 建议研究方向
调研 SoloPi 本地 ADB Server 在部分厂商系统（如华为、小米）后台清理策略下的存活率。

### 关联章节
- 19.20

### 外部 review 来源
- 外部 AI review

## [2026-04-25] 19.21  — 知识盲区

### 盲区描述
Android Performance Class (PC15)

### 重要程度
高

### 建议研究方向
调研 Android 15 对内存（12GB）和渲染（Vulkan 1.3）的硬门槛

### 关联章节
- 19.21

### 外部 review 来源
- 外部 AI review

## [2026-04-25] 19.21  — 知识盲区

### 盲区描述
存储测试中的缓存干扰机制

### 重要程度
中

### 建议研究方向
解释 O_DIRECT 或清除缓存对 Benchmark 准确性的影响

### 关联章节
- 19.21

### 外部 review 来源
- 外部 AI review

## [2026-04-25] 19.21  — 知识盲区

### 盲区描述
现代 Web Benchmark 标准

### 重要程度
低

### 建议研究方向
了解 Speedometer 3.0 的测试项及其与实际 Webview 性能的关系

### 关联章节
- 19.21

### 外部 review 来源
- 外部 AI review

## [2026-04-25] 19.23  — 知识盲区

### 盲区描述
:---

### 重要程度
:---

### 建议研究方向
:---

### 关联章节
- 19.23

### 外部 review 来源
- 外部 AI review

## [2026-04-25] 19.23  — 知识盲区

### 盲区描述
**BoringSSL 符号前缀**

### 重要程度
中

### 建议研究方向
Android 10+ 的 BoringSSL 可能带有 `bsl_` 前缀，PLT Hook 需要处理符号别名。

### 关联章节
- 19.23

### 外部 review 来源
- 外部 AI review

## [2026-04-25] 19.23  — 知识盲区

### 盲区描述
**BoringSSL 静态链接**

### 重要程度
高

### 建议研究方向
Cronet 等库通常静态链接 BoringSSL，传统的 `libssl.so` Hook 无效，需研究基于特征码的 Inline Hook。

### 关联章节
- 19.23

### 外部 review 来源
- 外部 AI review

## [2026-04-25] 19.23  — 知识盲区

### 盲区描述
**H2/H3 指标换算**

### 重要程度
中

### 建议研究方向
HTTP/2 的多路复用如何与传统的单请求耗时模型对齐。

### 关联章节
- 19.23

### 外部 review 来源
- 外部 AI review

## [2026-04-25] 19.25  — 知识盲区

### 盲区描述
WorkSource 的归因原理

### 重要程度
高

### 建议研究方向
研究 `WakeLock.setWorkSource()` 如何将耗电转嫁给特定 UID

### 关联章节
- 19.25

### 外部 review 来源
- 外部 AI review

## [2026-04-25] 19.25  — 知识盲区

### 盲区描述
内核电流节点差异

### 重要程度
中

### 建议研究方向
调查不同芯片平台（Qualcomm, MTK）在 `/sys/class/power_supply/battery/` 下的私有节点名称

### 关联章节
- 19.25

### 外部 review 来源
- 外部 AI review

## [2026-04-25] 19.25  — 知识盲区

### 盲区描述
Doze 模式下的 Alarm 限制

### 重要程度
高

### 建议研究方向
明确 `setAndAllowWhileIdle` 在不同 Android 版本的配额限制 (Quota)

### 关联章节
- 19.25

### 外部 review 来源
- 外部 AI review

## [2026-04-25] 19.26  — 知识盲区

### 盲区描述
离线包/预热监控

### 重要程度
高

### 建议研究方向
`shouldInterceptRequest` 拦截耗时与缓存命中率

### 关联章节
- 19.26

### 外部 review 来源
- 外部 AI review

## [2026-04-25] 19.26  — 知识盲区

### 盲区描述
Flutter Impeller 引擎

### 重要程度
中

### 建议研究方向
Android 14+ 下着色器编译卡顿（Shader Jank）监控差异

### 关联章节
- 19.26

### 外部 review 来源
- 外部 AI review

## [2026-04-25] 19.27  — 知识盲区

### 盲区描述
伪共享（False Sharing）

### 重要程度
中

### 建议研究方向
在无锁队列 C++ 实现中，如何通过 `alignas(64)` 避免缓存行竞争。

### 关联章节
- 19.27

### 外部 review 来源
- 外部 AI review

## [2026-04-25] 19.27  — 知识盲区

### 盲区描述
Mmap 头部原子更新顺序

### 重要程度
高

### 建议研究方向
崩溃恢复时如何校验 Header 的有效性，防止索引指向半写的数据。

### 关联章节
- 19.27

### 外部 review 来源
- 外部 AI review

## [2026-04-25] 19.27  — 知识盲区

### 盲区描述
动态指令安全性

### 重要程度
中

### 建议研究方向
如下发全量 Hprof Dump 指令，如何防止被恶意利用泄露隐私数据。

### 关联章节
- 19.27

### 外部 review 来源
- 外部 AI review

## [2026-04-25] 19.README - 选择理由：总纲文件定义了全章的分类体系和工具链覆盖范围，如果分类逻辑或工具选型存在事实错误（如过时工具），将直接影响后续 22 个小节的编写价值。 — 知识盲区 (External Review)

### ------
- **重要程度**: ------
- **建议研究方向**: -------
- **来源**: 外部AI review (2026-04-25-00-ch19.README-external-review.md)

### Android 16/17 ProfilingManager 增强
- **重要程度**: 高
- **建议研究方向**: 研究 Android 17 中“系统触发式采样”的具体触发阈值和配置方法。
- **来源**: 外部AI review (2026-04-25-00-ch19.README-external-review.md)

### 16KB Page Size 对 APM 开销的影响
- **重要程度**: 中
- **建议研究方向**: 在 16KB 页面下，某些 Hook 框架（如 Inline Hook）可能需要重新适配。
- **来源**: 外部AI review (2026-04-25-00-ch19.README-external-review.md)

### 自研 APM 存储方案 mmap vs Protobuf
- **重要程度**: 中
- **建议研究方向**: Matrix 和 KOOM 都在用的存储层优化原理。
- **来源**: 外部AI review (2026-04-25-00-ch19.README-external-review.md)


## [2026-04-25] 15.8 Android 性能问题实证：真实世界的分类与代码模式 — 知识盲区

### 盲区描述
章节用论文 taxonomy 校准性能问题优先级，但没有单独覆盖主线程同步 Binder 调用。该问题会把 system_server 或远端进程的锁竞争、调度延迟直接传导到 App 主线程，是响应性问题和 ANR 排查中的高频根因。external-review 已命中该风险。

### 重要程度
高

### 建议研究方向
- 查 AOSP Binder 调用与 system_server 锁竞争在 Perfetto 中的观察点：binder transaction、binder reply、主线程 ioctl(BINDER_WRITE_READ)。
- 整理 PackageManager/ActivityManager/ContentResolver 等常见主线程同步 Binder 调用案例。
- 给出 Code Review 与 trace 双重确认方法，避免把所有 IPC 都泛化成同一类问题。

### 关联章节
- 15.8
- 9.1
- 13.8

## [2026-04-25] 19.24 崩溃与 ANR 捕获机制 — 知识盲区

### 盲区描述
章节写到 SIGQUIT / Signal Catcher Hook，但没有展开 ART SignalCatcher 使用 sigwait 消费 SIGQUIT 的机制，也没有说明普通 sigaction handler 为什么不能稳定截获 ANR。external-review 已命中该风险。

### 重要程度
高

### 建议研究方向
- 阅读 AOSP `art/runtime/signal_catcher.cc` 与 libsigchain 相关逻辑。
- 梳理 sigwait、sigaction、线程信号掩码三者的分发关系。
- 补一份量产 App、厂商 ROM、root/test 环境三类 ANR 捕获方案边界对照。

### 关联章节
- 19.24
- 9.1
- 9.3

## [2026-04-25] 19.01 APM 全景图与分类体系 — 知识盲区

### 盲区描述
APM 的构建链集成，如何在打包时自动生成 Mapping 映射并注入 APK 以保证线上线下的 Trace 关联。
### 重要程度
高
### 建议研究方向
研究 AGP Task，查阅 Matrix 或 Firebase Crashlytics 的 Gradle 插件工作原理。
### 关联章节
- 19.01
### 外部 review 来源
- Gemini 外部 review

### 盲区描述
------
### 重要程度
---------
### 建议研究方向
-------------

### 盲区描述
符号化与反混淆体系（Mapping/Build-ID 关联）
### 重要程度
高
### 建议研究方向
APM 客户端 SDK 如何在编译期生成并上报唯一构建标识，以便服务端关联符号表。

### 盲区描述
ApplicationExitInfo 性能开销
### 重要程度
中
### 建议研究方向
调研 `getHistoricalProcessExitReasons()` 在极端情况下的 Binder 耗时，及最佳调用时机（后台线程）。

## [2026-04-25] 19.02 Tencent Matrix — 知识盲区

### 盲区描述

### 重要程度
中
### 建议研究方向

### 关联章节
- 19.02
### 外部 review 来源
- Gemini 外部 review

### 盲区描述
------
### 重要程度
---------
### 建议研究方向
-------------

### 盲区描述
Matrix AGP 8 插桩适配方案
### 重要程度
高
### 建议研究方向
查阅 `AsmClassVisitorFactory` 官方文档及社区 Matrix AGP8 适配方案（如 Github issue #888）。

### 盲区描述
methodMapping 编译期生成与反解机制
### 重要程度
高
### 建议研究方向
查阅 `matrix-gradle-plugin` 源码中关于 MethodTracer 和 id 分配的逻辑。

### 盲区描述
Battery Canary 系统级 Hook 原理及兼容性
### 重要程度
中
### 建议研究方向
分析 Battery Canary 监控 Wakelock 和 Alarm 时对系统 Service 的 Hook 点（如 `PowerManagerService`）。

## [2026-04-25] 19.03 APM 数据采集与传输 — 知识盲区

### 盲区描述

### 重要程度
中
### 建议研究方向

### 关联章节
- 19.03
### 外部 review 来源
- Gemini 外部 review

### 盲区描述
Fork 后的多线程死锁风险及解决策略
### 重要程度
高
### 建议研究方向
深入研究 Linux `fork()` 系统调用在存在多线程的 ART 环境下造成的锁状态不一致问题，以及 KOOM 是如何通过特定的线程挂起或 `pthread_atfork` 机制来绕过这一难点的。

### 盲区描述
SELinux 策略对 Fork Dump 的进一步限制
### 重要程度
中
### 建议研究方向
调查 Android 14/15 中 SELinux 策略对 App fork 行为、高权限内存读取和指定目录文件写入带来的限制及适配方案。

## [2026-04-25] 19.04 APM 指标体系与看板 — 知识盲区

### 盲区描述

### 重要程度
中
### 建议研究方向

### 关联章节
- 19.04
### 外部 review 来源
- Gemini 外部 review

### 盲区描述
Btrace 插桩对不同版本 ART 性能的实际影响
### 重要程度
中
### 建议研究方向
探究在 Android 12+ 上的 AOT 编译机制是否会放大插桩带来的方法退化开销，导致在低端机上采集的耗时比例失真严重。

## [2026-04-25] 19.07 APM 线下性能工具 — 知识盲区

### 盲区描述

### 重要程度
中
### 建议研究方向

### 关联章节
- 19.07
### 外部 review 来源
- Gemini 外部 review

### 盲区描述
AGP 8.0+ 下的编译期插桩（Transform）替代方案
### 重要程度
高
### 建议研究方向
DoKit 原本强依赖 AGP Transform API，但 AGP 8.0+ 已全面废弃 Transform。需要深入研究 DoKit 是如何适配（或是否兼容）AGP 8.x 的 AsmClassVisitorFactory 机制的。这决定了 DoKit 在当今最新 Android 项目中的生命力。

## [2026-04-25] 19.08 APM 线上监控实战 — 知识盲区

### 盲区描述
现代 AGP（8.0+）强制移除 Transform API 对存量自研 APM 工具链的颠覆性影响。
### 重要程度
高
### 建议研究方向
如何将基于旧有 Transform API 的字节码插桩工程迁移到基于 `AsmClassVisitorFactory` 的新版插件范式。
### 关联章节
- 19.08
### 外部 review 来源
- Gemini 外部 review

### 盲区描述
------
### 重要程度
----------
### 建议研究方向
--------------

### 盲区描述
现代 AGP 的 Transform 替代方案
### 重要程度
高
### 建议研究方向
研究从老旧的 `Transform API`（ArgusAPM 时代）向现代 AGP 7.0/8.0+ 的 `AsmClassVisitorFactory` 迁移的过程中，APM 插件如何适配。

## [2026-04-25] 19.09 APM 卡顿监控 — 知识盲区

### 盲区描述

### 重要程度
中
### 建议研究方向

### 关联章节
- 19.09
### 外部 review 来源
- Gemini 外部 review

### 盲区描述
------
### 重要程度
---------
### 建议研究方向
-------------

### 盲区描述
现代 APM 的跨版本 ANR 捕获机制演进
### 重要程度
中
### 建议研究方向
研究 AOSP 中 `ApplicationExitInfo` 的引入机制，对比旧版本的 Signal Catcher，了解类似 Measure 的框架是如何抹平这些版本差异的。

## [2026-04-25] 19.10 APM ANR 监控 — 知识盲区

### 盲区描述

### 重要程度
中
### 建议研究方向

### 关联章节
- 19.10
### 外部 review 来源
- Gemini 外部 review

### 盲区描述
------
### 重要程度
----------
### 建议研究方向
--------------

### 盲区描述
现代 APM 插桩适配方案
### 重要程度
高
### 建议研究方向
研究 `AsmClassVisitorFactory` 替代 `Transform` API 后的工程落地实践，这是后续所有自研或更新 APM 必踩的坑。

### 盲区描述
低版本 Android 重采样降级方案
### 重要程度
中
### 建议研究方向
在缺乏 `ProfilingManager` 的 Android 14 及以下设备中，APM 该如何更安全地唤起系统 trace 并回收文件。

## [2026-04-25] 19.12 APM 启动监控 — 知识盲区

### 盲区描述

### 重要程度
中
### 建议研究方向

### 关联章节
- 19.12
### 外部 review 来源
- Gemini 外部 review

### 盲区描述
------
### 重要程度
------
### 建议研究方向
-------

### 盲区描述
SurfaceView 渲染监控
### 重要程度
中
### 建议研究方向
说明 `FrameMetrics` 无法监控 `SurfaceView` 内部渲染，需使用 `SurfaceControl.OnReparentListener` 或其他手段。

### 盲区描述
Chereographer 交互
### 重要程度
低
### 建议研究方向
API 31 后 `Choreographer.FrameData` 与 `FrameMetrics` 的关系。

## [2026-04-25] 19.13 APM 网络监控 — 知识盲区

### 盲区描述

### 重要程度
中
### 建议研究方向

### 关联章节
- 19.13
### 外部 review 来源
- Gemini 外部 review

### 盲区描述
------
### 重要程度
------
### 建议研究方向
-------

### 盲区描述
协程追踪 (traceCoroutine)
### 重要程度
高
### 建议研究方向
`androidx.tracing:tracing:2.0.0` 针对协程挂起点的原生支持机制

### 盲区描述
Perfetto SDK (Track Event)
### 重要程度
中
### 建议研究方向
如何通过 Perfetto SDK 写入比 `androidx.tracing` 更丰富的 key-value 参数

### 盲区描述
ATrace 运行成本
### 重要程度
低
### 建议研究方向
`beginSection` / `endSection` 的具体指令开销，以及在高频循环（Hot Path）中的影响

## [2026-04-25] 19.14 APM 电量监控 — 知识盲区

### 盲区描述

### 重要程度
中
### 建议研究方向

### 关联章节
- 19.14
### 外部 review 来源
- Gemini 外部 review

### 盲区描述
------
### 重要程度
--------
### 建议研究方向
------------

### 盲区描述
Microbenchmark 的 DCE 问题
### 重要程度
高
### 建议研究方向
`Blackhole.consume()` 的底层实现原理及在 AOT 下的作用机制。

### 盲区描述
ProfileInstaller 的广播触发机制
### 重要程度
中
### 建议研究方向
深入探究 Macrobenchmark 是如何跨进程触发 `androidx.profileinstaller.action.INSTALL_PROFILE` 的。

## [2026-04-25] 19.17 APM 端到端链路 — 知识盲区

### 盲区描述

### 重要程度
中
### 建议研究方向

### 关联章节
- 19.17
### 外部 review 来源
- Gemini 外部 review

### 盲区描述
------
### 重要程度
------
### 建议研究方向
-------

### 盲区描述
Fragment 自动追踪开关
### 重要程度
高
### 建议研究方向
确认是否可以通过 Manifest 像 Activity 一样单独关闭。

### 盲区描述
URL Pattern 数量上限
### 重要程度
中
### 建议研究方向
每个 App ID 的 URL Pattern 聚合上限（通常为 400）。

### 盲区描述
离线数据保留时长
### 重要程度
中
### 建议研究方向
事件在设备本地存储的有效期（离线模式下）。

## [2026-04-25] 19.18 APM 数据分析 — 知识盲区

### 盲区描述
原生 APM SDK 在 16KB 页面环境下的性能基准测试。
### 重要程度
中
### 建议研究方向
对比 4KB vs 16KB 对齐后的内存占用差。
### 关联章节
- 19.18
### 外部 review 来源
- Gemini 外部 review

### 盲区描述
------
### 重要程度
----------
### 建议研究方向
--------------

### 盲区描述
16KB Page Size 对 Native SDK 的性能损耗
### 重要程度
高
### 建议研究方向
研究对齐 16KB 后，原生库体积和加载性能的变化。

### 盲区描述
商业 APM 对 HarmonyOS NEXT 的原生支持
### 重要程度
中
### 建议研究方向
Bugly 和 APMPlus 均已开始适配鸿蒙原生，可补充作为跨端考量。

## [2026-04-25] 19.19 APM 治理体系 — 知识盲区

### 盲区描述
Android 16 QPR2 引入的 GPU syscall filtering 是否会彻底封杀非调试应用的 GPU 采集。
### 重要程度
高
### 建议研究方向
关注 AOSP 变更与 PerfDog 官方适配说明。
### 关联章节
- 19.19
### 外部 review 来源
- Gemini 外部 review

### 盲区描述
------
### 重要程度
------
### 建议研究方向
-------

### 盲区描述
GPU 采集路径
### 重要程度
中
### 建议研究方向
补充 Adreno (`/sys/class/kgsl/kgsl-3d0/`) 和 Mali (`/sys/class/misc/mali0/device/`) 的 sysfs 路径差异。

### 盲区描述
Android 16 QPR 限制
### 重要程度
高
### 建议研究方向
研究 Android 16 对 GPU syscall filtering 的影响及 PerfDog 的应对方案。

## [2026-04-25] 19.20 APM 平台架构 — 知识盲区

### 盲区描述

### 重要程度
中
### 建议研究方向

### 关联章节
- 19.20
### 外部 review 来源
- Gemini 外部 review

### 盲区描述
------
### 重要程度
------
### 建议研究方向
-------

### 盲区描述
Android 14 前台服务类型声明
### 重要程度
中
### 建议研究方向
调研 SoloPi 在 Android 14 下是否因未声明 `mediaProjection` 或 `specialUse` 类型而导致崩溃。

### 盲区描述
无线 ADB 提权稳定性
### 重要程度
低
### 建议研究方向
调研 SoloPi 本地 ADB Server 在部分厂商系统（如华为、小米）后台清理策略下的存活率。

## [2026-04-25] 19.21 APM 告警与根因分析 — 知识盲区

### 盲区描述

### 重要程度
中
### 建议研究方向

### 关联章节
- 19.21
### 外部 review 来源
- Gemini 外部 review

### 盲区描述
------
### 重要程度
------
### 建议研究方向
-------

### 盲区描述
Android Performance Class (PC15)
### 重要程度
高
### 建议研究方向
调研 Android 15 对内存（12GB）和渲染（Vulkan 1.3）的硬门槛

### 盲区描述
存储测试中的缓存干扰机制
### 重要程度
中
### 建议研究方向
解释 O_DIRECT 或清除缓存对 Benchmark 准确性的影响

### 盲区描述
现代 Web Benchmark 标准
### 重要程度
低
### 建议研究方向
了解 Speedometer 3.0 的测试项及其与实际 Webview 性能的关系

## [2026-04-25] 19.26 APM 总结与展望 — 知识盲区

### 盲区描述
------
### 重要程度
------
### 建议研究方向
-------

### 盲区描述
离线包/预热监控
### 重要程度
高
### 建议研究方向
`shouldInterceptRequest` 拦截耗时与缓存命中率

### 盲区描述
Flutter Impeller 引擎
### 重要程度
中
### 建议研究方向
Android 14+ 下着色器编译卡顿（Shader Jank）监控差异


## [2026-04-25] 19.25 耗电与发热监控 — 知识盲区

### 盲区描述
Exact Alarm 特殊权限、Doze idle quota 与 APM 端侧归因的版本矩阵仍不完整。已有外部 review 命中过 Doze quota，本轮补充确认还需要覆盖 Android 12+ `SCHEDULE_EXACT_ALARM` / `canScheduleExactAlarms()`、Android 13+ `USE_EXACT_ALARM` 适用边界，以及 Android 14+ 默认授权变化对线上 Alarm 样本的影响。

### 重要程度
高

### 建议研究方向
- 按 Android 12/13/14/15/16/17 拆出 exact alarm 权限、特殊应用访问、豁免类型和失败表现。
- 建立 APM 采样字段：permission/app-op 状态、`canScheduleExactAlarms()`、alarm type、allowWhileIdle/exact 标记、实际触发延迟。
- 与现有 Doze quota 盲区合并成“后台唤醒归因版本矩阵”。

### 关联章节
- 19.25


## [2026-04-25] 19.26 混合栈与跨平台 APM — 知识盲区

### 盲区描述
WebView Core Web Vitals API 能力矩阵缺失。正文按 Android API 26-37 讨论 FCP/LCP，但实际可用性取决于 Android System WebView / Chromium 版本、provider channel 与企业 ROM 是否冻结 WebView 更新。

### 重要程度
高

### 建议研究方向
- 建立 WebView/Chromium major version 与 `PerformanceObserver`、`paint`、`largest-contentful-paint`、`supportedEntryTypes` 的可用性表。
- 补充 feature detection 与降级策略：不支持 LCP 时回退到 FCP、业务 ready、DOM 信号或 PixelCopy 白屏采样。
- 记录样本中的 WebView provider package/version，避免只按 Android major version 聚合。

### 关联章节
- 19.26
- 7.11

## [2026-04-25] 19.15 19.15 Baseline Profiles — 知识盲区

### 盲区描述
Cloud Profiles 覆盖冲突

### 重要程度
中

### 建议研究方向
当 Google Play 的 Cloud Profile 与 App 自带的 Baseline Profile 冲突时，ART 的合并优先级逻辑（`profman` 合并策略）。

### 关联章节
- 19.15

### 外部 review 来源
- External AI Review (2026-04-25-15-ch19.15-external-review.md)

## [2026-04-25] 19.15 19.15 Baseline Profiles — 知识盲区

### 盲区描述
App Image (art 文件) 生成

### 重要程度
高

### 建议研究方向
Profile 不仅引导 AOT，还引导 `dex2oat` 生成 App Image，预加载类对象，进一步减少类加载耗时。

### 关联章节
- 19.15

### 外部 review 来源
- External AI Review (2026-04-25-15-ch19.15-external-review.md)

## [2026-04-25] External Review Integration

### [2026-04-25] 19.04 btrace / RheaTrace — 知识盲区

**盲区描述**: Btrace 3.0 插桩在 ART (Android 12+) 上的实际性能开销失真

**重要程度**: 中

**建议研究方向**: 分析百万量级插桩在 AOT/JIT 混合编译下的性能退化

**来源**: External AI Review

### [2026-04-25] 19.07 DoraemonKit / DoKit — 知识盲区

**盲区描述**: AGP 8.0+ 废弃 Transform API 后 DoKit 的兼容性与 AsmClassVisitorFactory 适配

**重要程度**: 高

**建议研究方向**: 调研 DoKit 在 Gradle 8+/AGP 8+ 下的兼容表现

**来源**: External AI Review

### [2026-04-25] 19.08 ArgusAPM — 知识盲区

**盲区描述**: 现代 AGP 8.0+ 强制移除 Transform API 对存量自研 APM 的影响

**重要程度**: 高

**建议研究方向**: 研究从 Transform API 迁移到 AsmClassVisitorFactory 的路径

**来源**: External AI Review

### [2026-04-25] 19.09 Measure — 知识盲区

**盲区描述**: APM 平台底层 ANR 跨版本捕获机制差异（Signal 拦截 vs ApplicationExitInfo）

**重要程度**: 中

**建议研究方向**: 结合 Measure 源码研究 Android 11+ 新系统 API 的利用

**来源**: External AI Review

### [2026-04-25] 19.10 其他开源 APM 库（AndroidGodEye、Collie、Rabbit） — 知识盲区

**盲区描述**: 现代 Android APM 构建期插桩技术迁移（Transform API 到 AsmClassVisitorFactory）

**重要程度**: 高

**建议研究方向**: 可作为单独的编译期插桩小结

**来源**: External AI Review

### [2026-04-25] 19.13 androidx.tracing（Tracing SDK） — 知识盲区

**盲区描述**: androidx.tracing 在协程挂起时的表现及 traceCoroutine 的实战效果

**重要程度**: 高

**建议研究方向**: 调研 alpha 版 traceCoroutine 是否能生成 Flow 连接片段

**来源**: External AI Review

### [2026-04-25] 19.14 Jetpack Benchmark（Microbenchmark + Macrobenchmark） — 知识盲区

**盲区描述**: ProfileInstaller 跨进程 Profile 写入和 dexopt 触发机制

**重要程度**: 中

**建议研究方向**: AOSP ProfileInstaller BroadcastReceiver 实现

**来源**: External AI Review

### [2026-04-25] 19.19 PerfDog — 知识盲区

**盲区描述**: Android 16 QPR2 引入的 GPU syscall filtering 是否封杀非调试应用 GPU 采集

**重要程度**: 高

**建议研究方向**: 关注 AOSP 变更与 PerfDog 官方适配

**来源**: External AI Review

### [2026-04-25] 19.21 Benchmark 应用（Geekbench、安兔兔、3DMark、PCMark、Vellamo） — 知识盲区

**盲区描述**: Android Performance Class PC15 对内存（12GB）和渲染（Vulkan 1.3）的硬门槛

**重要程度**: 高

**建议研究方向**: 调研 Android 15 PC15 完整规格要求

**来源**: External AI Review

### [2026-04-25] 19.22 存储 Benchmark（AndroBench、A1 SD Bench） — 知识盲区

**盲区描述**: 存储测试中 Page Cache 对 Benchmark 准确性的干扰机制及 O_DIRECT 规避

**重要程度**: 中

**建议研究方向**: 解释 O_DIRECT 或清除缓存对 Benchmark 的影响

**来源**: External AI Review

## [2026-04-25] 15.1 性能优化的术、道、器 — 知识盲区

### 盲区描述
ProfilingManager / Baseline Profiles 版本锚点不完整（external-review 已命中，Task 9 已复核）

### 重要程度
高

### 建议研究方向
- 核对 android.os.ProfilingManager(API 35)、ProfilingTrigger/API 36 触发器、AndroidX Core Profiling 封装的对应关系。
- 梳理 Baseline Profiles、ProfileInstaller(API 24+)、Cloud Profiles、Play 分发之间的边界。

### 关联章节
15.1

## [2026-04-25] 15.2 如何区分系统问题和 App 问题 — 知识盲区

### 盲区描述
Binder 服务端归因与内存元凶定位闭环缺失（external-review 已命中，Task 9 已复核）

### 重要程度
高

### 建议研究方向
- 整理 Perfetto 中 client binder wait 跳转到 server binder 线程的操作路径和 SQL。
- 验证 rss_stat/process memory/lmkd/ApplicationExitInfo.getRss() 如何联合定位内存压力制造者。

### 关联章节
15.2

## [2026-04-25] 15.3 性能指标体系 — 知识盲区

### 盲区描述
Frame Overrun、ApplicationExitInfo 与 RSS 指标缺口（external-review 已命中，Task 9 已复核）

### 重要程度
高

### 建议研究方向
- 补齐 Macrobenchmark FrameTimingMetric.frameOverrunMs(API 31+) 的定义和适用边界。
- 梳理 ApplicationExitInfo(API 30+) 在 Crash/ANR/LMK 归因中的字段、兼容性与采集时机。
- 对比 PSS 与 RSS 在 Android Vitals、Perfetto、lmkd、进程退出记录中的用途。

### 关联章节
15.3

## [2026-04-25] 13.1 Perfetto 简介与演进 — 知识盲区

### 盲区描述
1. **Mainline APEX 挂载**：apexd 如何在启动时将模块挂载到 /apex/com.android.perfetto
2. **ProtoZero 零拷贝原理**：Perfetto 开销极低（1%-3% CPU）的核心原因
3. **Java HPROF 采集权限**：user 版本上 profileable 如何影响 perfetto_hprof 加载

### 重要程度
高（APEX）/ 中（ProtoZero、HPROF 权限）

### 建议研究方向
- Android 12+ apexd 挂载流程
- perfetto.dev ProtoZero 设计文档
- profileable 与 perfetto_hprof 的权限交互

### 外部 review 来源
- Gemini 外部 review (2026-04-25)

## [2026-04-25] 13.2 Trace 抓取 — 知识盲区

### 盲区描述
1. **perfetto --dropbox 机制**：未 Root 设备上通过 DropboxManager 获取 Trace
2. **atrace_userspace_only 字段**：FtraceConfig 新字段，减少内核开销
3. **127 字符限制演进**：Android 13+ 是否依然严格生效

### 重要程度
中 / 低

### 建议研究方向
- perfetto dropbox 生产设备采集方案
- 对比不同版本 libcutils 源码中的 ATRACE_MESSAGE_LENGTH

### 外部 review 来源
- Gemini 外部 review (2026-04-25)

## [2026-04-25] 13.3 Perfetto View — 知识盲区

### 盲区描述
1. **Blocked 状态（红色）**：锁竞争识别与 waking_thread 追踪
2. **V 键对齐操作**：跨进程（App→SF→HWC）时间点对齐效率

### 重要程度
高（Blocked）/ 中（V 键）

### 建议研究方向
- Perfetto 锁竞争追踪完整链路
- 多轨道关联分析最佳实践

### 外部 review 来源
- Gemini 外部 review (2026-04-25)

## [2026-04-25] 13.4 大文件处理 — 知识盲区

### 盲区描述
1. **Perfetto Stdlib**：INCLUDE PERFETTO MODULE 及 android.* 模块复用
2. **Span Join 操作符**：处理重叠时间段的高级 SQL 语法

### 重要程度
中 / 低

### 建议研究方向
- perfetto.dev/docs/analysis/stdlib 最新预置模块
- CPU 状态与线程状态交集的 Span Join 用法

### 外部 review 来源
- Gemini 外部 review (2026-04-25)

## [2026-04-25] 13.5 专题分析 — 知识盲区

### 盲区描述
1. **Prediction Error 归因**：SurfaceFlinger 预测机制
2. **Buffer Stuffing 量化阈值**：结合 BlastBufferQueue 源码研究
3. **亚哨完成帧预警**：on_time_finish=1 但 dur 接近 deadline 的筛选 SQL

### 重要程度
低 / 中

### 建议研究方向
- SurfaceFlinger 预测与 jank_type 关系
- BlastBufferQueue buffer stuffing 阈值

### 外部 review 来源
- Gemini 外部 review (2026-04-25)

## [2026-04-25] 13.6 线程 CPU 状态 — 知识盲区

### 盲区描述
1. **TASK_KILLABLE 状态**：在 Trace 中是否显示为 D 或有特殊标记
2. **SCHED_IDLE 优先级影响**：R 状态下的表现差异

### 重要程度
中 / 低

### 建议研究方向
- Android 内核 TASK_KILLABLE 在 Perfetto 中的呈现
- SCHED_IDLE 调度策略的 Trace 特征

### 外部 review 来源
- Gemini 外部 review (2026-04-25)

## [2026-04-25] 13.7 高级用法 — 知识盲区

### 盲区描述
1. **Bigtrace 架构**：分布式 SQL 查询在 K8s 上的部署与分片逻辑
2. **Custom Data Source (SDK)**：自定义 Proto + protozero 高效写入
3. **Perfetto Standard Library**：官方已内置的 SQL 模块复用

### 重要程度
高

### 建议研究方向
- perfetto.dev Bigtrace Orchestrator/Worker 架构
- perfetto.dev Custom Data Source C++ 示例
- perfetto.dev Standard Library 章节完整模块清单

### 外部 review 来源
- Gemini 外部 review (2026-04-25)

## [2026-04-25] 13.8 Input Latency SQL — 知识盲区

### 盲区描述
1. **is_speculative_frame 列存在性**：Perfetto v40+ 实验性字段，需提醒版本检查

### 重要程度
中

### 建议研究方向
- 确认 is_speculative_frame 在各版本中的可用性

### 外部 review 来源
- Gemini 外部 review (2026-04-25)

## [2026-04-25] 13.1 — 知识盲区

### 盲区描述
Mainline APEX 挂载

### 重要程度
高

### 建议研究方向
研究 `apexd` 如何在启动时将模块挂载到 `/apex/com.android.perfetto`

### 外部 review 来源
- Gemini 外部 review (2026-04-25-13-ch13.01-external-review.md)


## [2026-04-25] 13.1 — 知识盲区

### 盲区描述
ProtoZero 零拷贝原理

### 重要程度
中

### 建议研究方向
查阅 `perfetto.dev` 关于 ProtoZero 库的设计文档

### 外部 review 来源
- Gemini 外部 review (2026-04-25-13-ch13.01-external-review.md)


## [2026-04-25] 13.1 — 知识盲区

### 盲区描述
Java HPROF 采集权限

### 重要程度
中

### 建议研究方向
调研在 `user` 版本上 `profileable` 如何具体影响 `perfetto_hprof` 的加载

### 外部 review 来源
- Gemini 外部 review (2026-04-25-13-ch13.01-external-review.md)


## [2026-04-25] 13.1 — 知识盲区

### 盲区描述
Perfetto 在 Android 14+ 引入的 `CLONE_SNAPSHOT` 触发机制如何实现“事后录制”。

### 重要程度
中

### 建议研究方向
调研 `traced` 对环形缓冲区快照的克隆逻辑。

### 外部 review 来源
- Gemini 外部 review (2026-04-25-13-ch13.01-external-review.md)


## [2026-04-25] 13.2 — 知识盲区

### 盲区描述
`perfetto --dropbox` 机制

### 重要程度
中

### 建议研究方向
了解在未 Root 的生产设备上如何通过 DropboxManager 获取 Trace。

### 外部 review 来源
- Gemini 外部 review (2026-04-25-13-ch13.02-external-review.md)


## [2026-04-25] 13.2 — 知识盲区

### 盲区描述
`atrace_userspace_only` 字段

### 重要程度
低

### 建议研究方向
在 `FtraceConfig` 中新引入的字段，用于减少内核开销。

### 外部 review 来源
- Gemini 外部 review (2026-04-25-13-ch13.02-external-review.md)


## [2026-04-25] 13.2 — 知识盲区

### 盲区描述
127 字符限制在 Android 13+ 是否依然严格生效（部分内核版本可能放宽）。

### 重要程度
低

### 建议研究方向
对比 Android 不同版本的 `libcutils` 源码。

### 外部 review 来源
- Gemini 外部 review (2026-04-25-13-ch13.02-external-review.md)


## [2026-04-25] 13.3 — 知识盲区

### 盲区描述
Blocked 状态（红色）

### 重要程度
高

### 建议研究方向
补充锁竞争的识别与 waking_thread 追踪。

### 外部 review 来源
- Gemini 外部 review (2026-04-25-13-ch13.03-external-review.md)


## [2026-04-25] 13.3 — 知识盲区

### 盲区描述
V 键对齐操作

### 重要程度
中

### 建议研究方向
提升多轨道关联分析速度。

### 外部 review 来源
- Gemini 外部 review (2026-04-25-13-ch13.03-external-review.md)


## [2026-04-25] 13.5 — 知识盲区

### 盲区描述
Prediction Error 归因

### 重要程度
低

### 建议研究方向
了解 SurfaceFlinger 预测机制。

### 外部 review 来源
- Gemini 外部 review (2026-04-25-13-ch13.05-external-review.md)


## [2026-04-25] 13.5 — 知识盲区

### 盲区描述
Buffer Stuffing 的量化阈值

### 重要程度
中

### 建议研究方向
结合 `BlastBufferQueue` 源码研究。

### 外部 review 来源
- Gemini 外部 review (2026-04-25-13-ch13.05-external-review.md)


## [2026-04-25] 13.5 — 知识盲区

### 盲区描述
`jank_type` 之外的“亚哨完成帧”预警机制。

### 重要程度
中

### 建议研究方向
研究 `on_time_finish = 1` 但 `dur` 接近 deadline 的量化筛选 SQL。

### 外部 review 来源
- Gemini 外部 review (2026-04-25-13-ch13.05-external-review.md)


## [2026-04-25] 13.8 — 知识盲区

### 盲区描述
`is_speculative_frame` 的列存在性

### 重要程度
中

### 建议研究方向
确认为 Perfetto v40+ 引入的实验性字段，需提醒用户检查版本。

### 外部 review 来源
- Gemini 外部 review (2026-04-25-13-ch13.08-external-review.md)


## [2026-04-25] 13.9 — 知识盲区

### 盲区描述
GKI 内核下 tracefs 挂载路径

### 重要程度
中

### 建议研究方向
确认在所有主流厂商 Android 13+ 设备中，`/sys/kernel/tracing` 是否已完全取代 `/sys/kernel/debug/tracing`。

### 外部 review 来源
- Gemini 外部 review (2026-04-25-13-ch13.09-external-review.md)


## [2026-04-25] 13.9 — 知识盲区

### 盲区描述
Perfetto SDK 的 Java 层封装

### 重要程度
中

### 建议研究方向
Android 16+ 的 `ProfilingManager` 是否允许 Java 层直接注册结构化数据源。

### 外部 review 来源
- Gemini 外部 review (2026-04-25-13-ch13.09-external-review.md)


## [2026-04-25] 13.9 — 知识盲区

### 盲区描述
Android 16+ 是否提供了 Java 层直接向 Perfetto 注册 Data Source 的能力。

### 重要程度
低

### 建议研究方向
关注 Android 16 `ProfilingManager` 的 API 演进。

### 外部 review 来源
- Gemini 外部 review (2026-04-25-13-ch13.09-external-review.md)


## [2026-04-25] 13.10 — 知识盲区

### 盲区描述
锁竞争的非 Java 层 (Native) 表现

### 重要程度
中

### 建议研究方向
Perfetto 对内核锁 (futex) 的 SQL 追踪方式。

### 外部 review 来源
- Gemini 外部 review (2026-04-25-13-ch13.10-external-review.md)


## [2026-04-25] 13.10 — 知识盲区

### 盲区描述
Perfetto 虚拟表性能优化

### 重要程度
高

### 建议研究方向
研究 `CREATE VIRTUAL TABLE USING ...` 在 Trace Processor 中的索引限制。

### 外部 review 来源
- Gemini 外部 review (2026-04-25-13-ch13.10-external-review.md)


## [2026-04-25] 14.1 — 知识盲区

### 盲区描述
Profileable 模式下的 Network Inspector

### 重要程度
中

### 建议研究方向
研究在不开启 `debuggable` 时，AS 如何通过拦截器查看 Release 包的网络数据（通常需要代码侵入）。

### 外部 review 来源
- Gemini 外部 review (2026-04-25-14-ch14.01-external-review.md)


## [2026-04-25] 14.1 — 知识盲区

### 盲区描述
ODPM 硬件要求

### 重要程度
中

### 建议研究方向
明确非 Pixel 设备上 Power Profiler 的降级表现。

### 外部 review 来源
- Gemini 外部 review (2026-04-25-14-ch14.01-external-review.md)


## [2026-04-25] 14.1 — 知识盲区

### 盲区描述
Profileable 模式下 Java Heap Dump 的缺失对排查生产环境内存问题的替代方案。

### 重要程度
中

### 建议研究方向
AOSP `perfetto` 工具集中的 `heapprofd` 如何在 `profileable` 模式下工作。

### 外部 review 来源
- Gemini 外部 review (2026-04-25-14-ch14.01-external-review.md)


## [2026-04-25] 14.2 — 知识盲区

### 盲区描述
`ProfilingManager` 与 Simpleperf 关系

### 重要程度
中

### 建议研究方向
研究 Android 15/16 引入的 `ProfilingManager` 如何触发 Simpleperf 采样并自动拉取。

### 外部 review 来源
- Gemini 外部 review (2026-04-25-14-ch14.02-external-review.md)


## [2026-04-25] 14.2 — 知识盲区

### 盲区描述
混合架构（big.LITTLE）下的采样差异

### 重要程度
低

### 建议研究方向
不同核心（大核/小核）的 PMU 事件计数器可能不一致，是否需要 `-c` 绑定核心分析。

### 外部 review 来源
- Gemini 外部 review (2026-04-25-14-ch14.02-external-review.md)


## [2026-04-25] 14.3 — 知识盲区

### 盲区描述
`libmemunreachable` 信号触发

### 重要程度
中

### 建议研究方向
研究 Android 14 信号 48 的具体日志输出格式及限制。

### 外部 review 来源
- Gemini 外部 review (2026-04-25-14-ch14.03-external-review.md)


## [2026-04-25] 14.3 — 知识盲区

### 盲区描述
MTE 异步模式实战

### 重要程度
高

### 建议研究方向
MTE 在 Android 15+ 上的默认策略及对 `malloc` 性能的影响。

### 外部 review 来源
- Gemini 外部 review (2026-04-25-14-ch14.03-external-review.md)


## [2026-04-25] 14.3 — 知识盲区

### 盲区描述
Graphics 内存跨进程分摊

### 重要程度
中

### 建议研究方向
如何在 `dumpsys meminfo` 中区分 SurfaceFlinger 侧和 App 侧的 buffer 占用。

### 外部 review 来源
- Gemini 外部 review (2026-04-25-14-ch14.03-external-review.md)


## [2026-04-25] 14.3 — 知识盲区

### 盲区描述
MTE (Memory Tagging Extension) 在 Android 15 生产设备上的实际可用性。

### 重要程度
高

### 建议研究方向
Pixel 8/9 系列的 MTE 开启状态及对应用层的影响。

### 外部 review 来源
- Gemini 外部 review (2026-04-25-14-ch14.03-external-review.md)


## [2026-04-25] 14.4 — 知识盲区

### 盲区描述
Android 15 Frontend 架构下的 LayerSnapshot 计算逻辑

### 重要程度
高

### 建议研究方向
研究 SF 如何将 RequestedState 转换为 Snapshot 并进行 z-order 合并

### 外部 review 来源
- Gemini 外部 review (2026-04-25-14-ch14.04-external-review.md)


## [2026-04-25] 14.4 — 知识盲区

### 盲区描述
ApplicationExitInfo (exit-info) 的详细字段定义

### 重要程度
中

### 建议研究方向
深入 ProcessList.java 研究 REASON_ANR 下的 subReason 分类

### 外部 review 来源
- Gemini 外部 review (2026-04-25-14-ch14.04-external-review.md)


## [2026-04-25] 14.4 — 知识盲区

### 盲区描述
VRR 模式下 FrameMetrics 的截止时间计算

### 重要程度
高

### 建议研究方向
研究 API 31+ FrameMetrics.DEADLINE 在 Android 15 上的精度提升逻辑

### 外部 review 来源
- Gemini 外部 review (2026-04-25-14-ch14.04-external-review.md)


## [2026-04-25] 14.4 — 知识盲区

### 盲区描述
16KB 页大小对内存统计 PSS 的间接影响（如元数据开销）。

### 重要程度
中

### 建议研究方向
对比 4KB 和 16KB 模式下 system_server 的 meminfo 差异。

### 外部 review 来源
- Gemini 外部 review (2026-04-25-14-ch14.04-external-review.md)


## [2026-04-25] 14.5 — 知识盲区

### 盲区描述
16KB Page Size 兼容性

### 重要程度
高

### 建议研究方向
Android 15 强制要求的 16KB 物理页对现有 PLT Hook 库（xHook, ByteHook）的破坏性影响。

### 外部 review 来源
- Gemini 外部 review (2026-04-25-14-ch14.05-external-review.md)


## [2026-04-25] 14.5 — 知识盲区

### 盲区描述
鸿蒙原生适配

### 重要程度
中

### 建议研究方向
三方性能库在鸿蒙系统（HarmonyOS Next）下的替代方案（如鸿蒙原生 AOP）。

### 外部 review 来源
- Gemini 外部 review (2026-04-25-14-ch14.05-external-review.md)


## [2026-04-25] 14.5 — 知识盲区

### 盲区描述
Android 15 (16KB Page Size) 对三方库 Native Hook 的冲击。

### 重要程度
高

### 建议研究方向
调研 ByteHook 对 16KB Page 的适配实现。

### 外部 review 来源
- Gemini 外部 review (2026-04-25-14-ch14.05-external-review.md)


## [2026-04-25] 14.6 — 知识盲区

### 盲区描述
**Monkey + LeakCanary 自动检测**

### 重要程度
高

### 建议研究方向
如何在自动化测试中结合 Monkey 触发泄漏并利用 LeakCanary 导出 Hprof

### 外部 review 来源
- Gemini 外部 review (2026-04-25-14-ch14.06-external-review.md)


## [2026-04-25] 14.6 — 知识盲区

### 盲区描述
**SoloPi 视觉拆帧原理**

### 重要程度
中

### 建议研究方向
了解其如何通过录屏每一帧的颜色变化判定“页面加载完成”

### 外部 review 来源
- Gemini 外部 review (2026-04-25-14-ch14.06-external-review.md)


## [2026-04-25] 14.6 — 知识盲区

### 盲区描述
Monkey 的性能集成方案。

### 重要程度
中

### 建议研究方向
研究如何通过 `am instrument` 封装 Monkey 操作。

### 外部 review 来源
- Gemini 外部 review (2026-04-25-14-ch14.06-external-review.md)


## [2026-04-25] 14.7 — 知识盲区

### 盲区描述
Mainline 模块更新机制

### 重要程度
中

### 建议研究方向
深入研究 `com.android.profiling` APEX 模块如何通过 Google Play 系统更新下发新的 Trigger 类型。

### 外部 review 来源
- Gemini 外部 review (2026-04-25-14-ch14.07-external-review.md)


## [2026-04-25] 14.7 — 知识盲区

### 盲区描述
系统触发器的冲突解决

### 重要程度
中

### 建议研究方向
当多个应用同时注册高频 Trigger（如 ANR）时，系统底层的仲裁逻辑。

### 外部 review 来源
- Gemini 外部 review (2026-04-25-14-ch14.07-external-review.md)


## [2026-04-25] 14.10 — 知识盲区

### 盲区描述
BPF CO-RE 在厂商自定义内核中的重定位失效场景

### 重要程度
中

### 建议研究方向
研究当厂商修改了内核核心结构体（如 `task_struct`）且未更新 BTF 时 CO-RE 的表现

### 外部 review 来源
- Gemini 外部 review (2026-04-25-14-ch14.10-external-review.md)


## [2026-04-25] 14.10 — 知识盲区

### 盲区描述
sched_ext 对 Android 功耗（Energy Aware Scheduling, EAS）的潜在冲突

### 重要程度
高

### 建议研究方向
研究自定义调度器如何与 EAS 的能效模型协作或共存

### 外部 review 来源
- Gemini 外部 review (2026-04-25-14-ch14.10-external-review.md)


## [2026-04-25] 14.11 — 知识盲区

### 盲区描述
`dumpsys battery` 隐藏字段

### 重要程度
中

### 建议研究方向
Android 14+ 新增的 `mSavedBatteryAsoc` (ASOC, 电池健康度)

### 外部 review 来源
- Gemini 外部 review (2026-04-25-14-ch14.11-external-review.md)


## [2026-04-25] 14.11 — 知识盲区

### 盲区描述
PowerStats HAL 2.0

### 重要程度
高

### 建议研究方向
Android 15 之后 HAL 层如何定义自定义 Power Rail

### 外部 review 来源
- Gemini 外部 review (2026-04-25-14-ch14.11-external-review.md)


## [2026-04-25] 14.11 — 知识盲区

### 盲区描述
Android 14+ 硬件级电池循环次数与健康度查询。

### 重要程度
中

### 建议研究方向
补充 `adb shell dumpsys battery` 在 A14+ 的新字段解析。

### 外部 review 来源
- Gemini 外部 review (2026-04-25-14-ch14.11-external-review.md)


## [2026-04-25] 14.12 — 知识盲区

### 盲区描述
**BTrace 3.0 采样原理**

### 重要程度
高

### 建议研究方向
研究同步采样如何与 Perfetto 时间戳对齐。

### 外部 review 来源
- Gemini 外部 review (2026-04-25-14-ch14.12-external-review.md)


## [2026-04-25] 14.12 — 知识盲区

### 盲区描述
**AppExitInfo 持久化**

### 重要程度
中

### 建议研究方向
调研 `/data/system/exit_info/` 的存储上限和清理机制。

### 外部 review 来源
- Gemini 外部 review (2026-04-25-14-ch14.12-external-review.md)


## [2026-04-25] 14.13 — 知识盲区

### 盲区描述
ArtMethod Hook 稳定性

### 重要程度
高

### 建议研究方向
研究 ART 虚拟机版本演进对结构体偏移的影响

### 外部 review 来源
- Gemini 外部 review (2026-04-25-14-ch14.13-external-review.md)


## [2026-04-25] 14.13 — 知识盲区

### 盲区描述
16KB Page Size 构建链适配

### 重要程度
中

### 建议研究方向
NDK r27 对 16KB 的默认支持情况

### 外部 review 来源
- Gemini 外部 review (2026-04-25-14-ch14.13-external-review.md)


## [2026-04-25] 14.13 — 知识盲区

### 盲区描述
Android 14 动态库只读限制

### 重要程度
高

### 建议研究方向
`File.setReadOnly()` 对 `System.load()` 的强制校验逻辑

### 外部 review 来源
- Gemini 外部 review (2026-04-25-14-ch14.13-external-review.md)


## [2026-04-25] 14.13 — 知识盲区

### 盲区描述
运行时 ART Hook 的具体实现。

### 重要程度
高

### 建议研究方向
调研 SandHook 对 Android 12-15 的适配方案。

### 外部 review 来源
- Gemini 外部 review (2026-04-25-14-ch14.13-external-review.md)



## [2026-04-25] 7.4 典型卡顿场景分析 — 知识盲区

### 盲区描述
跨进程动画中 SurfaceControl 的接管 (Handover) 细节未覆盖。SurfaceFlinger HWC Overlay 掉退对帧率影响、RenderThread 亲和力调度未深入研究。

### 重要程度
中-高

### 建议研究方向
- Android 12+ SplashScreen 的 RemoteAnimation 实现
- PowerHAL 动态调整 RenderThread 优先级的机制
- 通知栏展开时 HWC Overlay 掉退对帧率的影响

### 关联章节
- 7.1
- 7.2
- 7.4

### 外部 review 来源
- Gemini 外部 review

## [2026-04-25] 7.5 优化策略 — 知识盲区

### 盲区描述
Android 15 setFrameContentVelocity 对自研 UI 引擎的启示；Skia Graphite 引擎对 RenderEffect 的性能加持。

### 重要程度
高

### 建议研究方向
- Skia Graphite 在 Android 15 的推行路线图
- ContentProvider applyBatch 事务特性对数据一致性的帮助

### 关联章节
- 7.5
- 7.10

### 外部 review 来源
- Gemini 外部 review

## [2026-04-25] 7.7 Compose 性能 — 知识盲区

### 盲区描述
Strong Skipping 下不稳定参数使用 === 引用相等性比较的副作用；SnapshotStateObserver 的注册观察机制。

### 重要程度
高

### 建议研究方向
- Kotlin 2.0.20+ Strong Skipping 引用相等性陷阱
- SnapshotStateObserver registerApplyObserver 的"状态变化→Scope 失效"映射

### 关联章节
- 7.7

### 外部 review 来源
- Gemini 外部 review

## [2026-04-25] 7.8 RecyclerView 深度优化 — 知识盲区

### 盲区描述
多 RecyclerView 实例共存时 GapWorker 预取任务排序逻辑。

### 重要程度
中

### 建议研究方向
- GapWorker 在多列表场景下的预取预算平衡
- factorInCreateTime 衰减系数（通常 0.25）

### 关联章节
- 7.8

### 外部 review 来源
- Gemini 外部 review

## [2026-04-25] 7.9 感官流畅性 — 知识盲区

### 盲区描述
主流手机厂商是否已在 Framework 层修复 Choreographer 毫秒截断问题；Chrome Blink 层 VSync 抖动处理。

### 重要程度
中

### 建议研究方向
- 各厂商 ROM 中 lockAnimationClock 的魔改优化
- Chrome 时间源平滑算法

### 关联章节
- 7.9

### 外部 review 来源
- Gemini 外部 review

## [2026-04-25] 7.10 图片与 Bitmap 性能 — 知识盲区

### 盲区描述
Immutable Bitmap 在硬件加速渲染时的具体路径优化；Android 14 AVIF 硬件解码强制要求对业务层的实际收益。

### 重要程度
中-高

### 建议研究方向
- HARDWARE Bitmap 禁止 CPU 侧读写的渲染路径优化
- AV1 硬件解码覆盖率与 App 层收益量化

### 关联章节
- 7.10

### 外部 review 来源
- Gemini 外部 review

## [2026-04-25] 7.11 WebView 性能 — 知识盲区

### 盲区描述
不同 OEM GPU 驱动在 WebView 场景下的崩溃特征；宿主 App 通过 CDP 自动化获取 V8 Heap Snapshot。

### 重要程度
中-高

### 建议研究方向
- Adreno 驱动 WebView 崩溃特征统计
- Chrome DevTools Protocol 远程获取 Renderer V8 Heap Snapshot

### 关联章节
- 7.11

### 外部 review 来源
- Gemini 外部 review

## [2026-04-25] 7.12 View 布局优化 — 知识盲区

### 盲区描述
RenderNode 在重绘时的损坏区计算；LayoutLib/Compose 混合预览与真机差异。

### 重要程度
高

### 建议研究方向
- 硬件加速下 invalidate(Rect) 的实际作用边界
- LayoutLib 预览时布局解析逻辑

### 关联章节
- 7.12

### 外部 review 来源
- Gemini 外部 review

## [2026-04-25] 7.13 SystemUI 性能 — 知识盲区

### 盲区描述
Flexiglass 场景下的手势拦截机制；Compose 在 SystemUI 中的常驻内存开销。

### 重要程度
高

### 建议研究方向
- SceneTransitionLayout 手势检测器与 NotificationShadeWindowView 触摸逻辑并存
- Composed UI vs ViewTree 基准内存占用对比

### 关联章节
- 7.13

### 外部 review 来源
- Gemini 外部 review

## [2026-04-25] 7.14 GAPS 动态分析 — 知识盲区

### 盲区描述
GAPS 生成的 JSON 指令集的具体 Schema。

### 重要程度
中

### 建议研究方向
- GAPS Activity/ResourceID/Action 指令集 Schema
- 目标方法驱动性能压测新思路

### 关联章节
- 7.14

### 外部 review 来源
- Gemini 外部 review

## [2026-04-25] 7.15 作战手册 — 知识盲区

### 盲区描述
Android 15/16 的 16KB Page Size 对 mmap 及冷启动二进制加载的量化影响。

### 重要程度
高

### 建议研究方向
- 16KB Page 模式对冷启动 Native Lib 加载的量化影响
- ELF page alignment 检查方法

### 关联章节
- 7.15
- 8.3

### 外部 review 来源
- Gemini 外部 review

## [2026-04-25] 8.1 响应速度原理 — 知识盲区

### 盲区描述
Android 15 Adaptive Refresh Rate 对 Input 响应延迟的影响。

### 重要程度
中

### 建议研究方向
- 系统如何根据 Input 事件动态从 10Hz 跳到 120Hz
- InputDispatcher 共享内存事件分发的延迟测量

### 关联章节
- 8.1

### 外部 review 来源
- Gemini 外部 review

## [2026-04-25] 8.3 启动优化策略 — 知识盲区

### 盲区描述
Android 15+ 16KB Page 模式对文件预取(Read-ahead)和大型资源加载速度的影响。

### 重要程度
低

### 建议研究方向
- 16KB Page Size 改变 read-ahead 行为的量化数据

### 关联章节
- 8.3

### 外部 review 来源
- Gemini 外部 review

## [2026-04-25] 8.5-8.6 案例集与协程性能 — 知识盲区

### 盲区描述
16KB Page Size 导致 NDK 对齐膨胀；Kotlin 2.2 K2 编译器对协程状态机的内联优化；Android 16 perfetto 中协程层级切换可见性。

### 重要程度
高

### 建议研究方向
- -Wl,-z,max-page-size=16384 对多层级动态库加载的影响
- K1 vs K2 生成字节码深度差异
- CoroutineContext TrackedCoroutineInterceptor 实验性特性

### 关联章节
- 8.5
- 8.6

### 外部 review 来源
- Gemini 外部 review

## [2026-04-25] 8.10 ProfilingManager 系统触发式追踪 — 知识盲区

### 盲区描述
ANOMALY 触发器在 LMK 前生成 Heap Dump 的完整链路；MemoryLimiter 事件机制。

### 重要程度
高

### 建议研究方向
- TRIGGER_TYPE_ANOMALY 与 MemoryLimiter 的协作链路
- device_config 绕过 Rate Limiter 进行全流程压测

### 关联章节
- 8.10

### 外部 review 来源
- Gemini 外部 review
**external. 13.03**
- | Blocked 状态（红色） | 高 | 补充锁竞争的识别与 waking_thread 追踪。 |

**external. 13.03**
- | V 键对齐操作 | 中 | 提升多轨道关联分析速度。 |

**external. 13.05**
- | Prediction Error 归因 | 低 | 了解 SurfaceFlinger 预测机制。 |

**external. 13.05**
- | Buffer Stuffing 的量化阈值 | 中 | 结合 `BlastBufferQueue` 源码研究。 |

**external. 13.05**
- - **章节**：13.5.2

**external. 13.05**
- - **盲区描述**：`jank_type` 之外的“亚哨完成帧”预警机制。

**external. 13.05**
- - **建议研究方向**：研究 `on_time_finish = 1` 但 `dur` 接近 deadline 的量化筛选 SQL。

**external. 13.09**
- | GKI 内核下 tracefs 挂载路径 | 中 | 确认在所有主流厂商 Android 13+ 设备中，`/sys/kernel/tracing` 是否已完全取代 `/sys/kernel/debug/tracing`。 |

**external. 13.09**
- | Perfetto SDK 的 Java 层封装 | 中 | Android 16+ 的 `ProfilingManager` 是否允许 Java 层直接注册结构化数据源。 |

**external. 13.09**
- - **章节**：13.9

**external. 13.09**
- - **盲区描述**：Android 16+ 是否提供了 Java 层直接向 Perfetto 注册 Data Source 的能力。

**external. 13.09**
- - **重要程度**：低

**external. 13.09**
- - **建议研究方向**：关注 Android 16 `ProfilingManager` 的 API 演进。

**external. 14.01**
- | Profileable 模式下的 Network Inspector | 中 | 研究在不开启 `debuggable` 时，AS 如何通过拦截器查看 Release 包的网络数据（通常需要代码侵入）。 |

**external. 14.01**
- | ODPM 硬件要求 | 中 | 明确非 Pixel 设备上 Power Profiler 的降级表现。 |

**external. 14.01**
- - **章节**：14.1

**external. 14.01**
- - **盲区描述**：Profileable 模式下 Java Heap Dump 的缺失对排查生产环境内存问题的替代方案。

**external. 14.01**
- - **建议研究方向**：AOSP `perfetto` 工具集中的 `heapprofd` 如何在 `profileable` 模式下工作。

**external. 14.03**
- | `libmemunreachable` 信号触发 | 中 | 研究 Android 14 信号 48 的具体日志输出格式及限制。 |

**external. 14.03**
- | MTE 异步模式实战 | 高 | MTE 在 Android 15+ 上的默认策略及对 `malloc` 性能的影响。 |

**external. 14.03**
- | Graphics 内存跨进程分摊 | 中 | 如何在 `dumpsys meminfo` 中区分 SurfaceFlinger 侧和 App 侧的 buffer 占用。 |

**external. 14.03**
- - **章节**：14.3

**external. 14.03**
- - **盲区描述**：MTE (Memory Tagging Extension) 在 Android 15 生产设备上的实际可用性。

**external. 14.03**
- - **建议研究方向**：Pixel 8/9 系列的 MTE 开启状态及对应用层的影响。

**external. 14.05**
- | 16KB Page Size 兼容性 | 高 | Android 15 强制要求的 16KB 物理页对现有 PLT Hook 库（xHook, ByteHook）的破坏性影响。 |

**external. 14.05**
- | 鸿蒙原生适配 | 中 | 三方性能库在鸿蒙系统（HarmonyOS Next）下的替代方案（如鸿蒙原生 AOP）。 |

**external. 14.05**
- - **章节**：14.5

**external. 14.05**
- - **盲区描述**：Android 15 (16KB Page Size) 对三方库 Native Hook 的冲击。

**external. 14.05**
- - **建议研究方向**：调研 ByteHook 对 16KB Page 的适配实现。

**external. 14.06**
- | :--- | :--- | :--- |

**external. 14.06**
- | **Monkey + LeakCanary 自动检测** | 高 | 如何在自动化测试中结合 Monkey 触发泄漏并利用 LeakCanary 导出 Hprof |

**external. 14.06**
- | **SoloPi 视觉拆帧原理** | 中 | 了解其如何通过录屏每一帧的颜色变化判定“页面加载完成” |

**external. 14.06**
- - **章节**：14.6

**external. 14.06**
- - **盲区描述**：Monkey 的性能集成方案。

**external. 14.06**
- - **建议研究方向**：研究如何通过 `am instrument` 封装 Monkey 操作。

**external. 14.11**
- | `dumpsys battery` 隐藏字段 | 中 | Android 14+ 新增的 `mSavedBatteryAsoc` (ASOC, 电池健康度) |

**external. 14.11**
- | PowerStats HAL 2.0 | 高 | Android 15 之后 HAL 层如何定义自定义 Power Rail |

**external. 14.11**
- - **章节**：14.11

**external. 14.11**
- - **盲区描述**：Android 14+ 硬件级电池循环次数与健康度查询。

**external. 14.11**
- - **建议研究方向**：补充 `adb shell dumpsys battery` 在 A14+ 的新字段解析。

**external. 14.11**
- ## 十、下一候选章节

**external. 14.11**
- - `src/part2-performance/ch11-power/02-optimization-strategy.md`（与本章工具篇紧密衔接的实战篇）

**external. 14.11**
- ## 十一、落盘信息

**external. 14.11**
- - **已写入文件**：`logs/external-review/2026-04-25-14-ch14.11-external-review.md`

**external. 14.12**
- | **BTrace 3.0 采样原理** | 高 | 研究同步采样如何与 Perfetto 时间戳对齐。 |

**external. 14.12**
- | **AppExitInfo 持久化** | 中 | 调研 `/data/system/exit_info/` 的存储上限和清理机制。 |

**external. 14.13**
- | ArtMethod Hook 稳定性 | 高 | 研究 ART 虚拟机版本演进对结构体偏移的影响 |

**external. 14.13**
- | 16KB Page Size 构建链适配 | 中 | NDK r27 对 16KB 的默认支持情况 |

**external. 14.13**
- | Android 14 动态库只读限制 | 高 | `File.setReadOnly()` 对 `System.load()` 的强制校验逻辑 |

**external. 14.13**
- - **章节**：14.13

**external. 14.13**
- - **盲区描述**：运行时 ART Hook 的具体实现。

**external. 14.13**
- - **建议研究方向**：调研 SandHook 对 Android 12-15 的适配方案。

**external. 07.04**
- | SurfaceFlinger 的 HWC Overlay 掉退 (Fallback) | 中 | 当通知栏展开时，如果层级过多触发 GPU 合成，对帧率的影响。 |

**external. 07.04**
- | RenderThread 亲和力调度 (Affinity) | 高 | 除了小核运行案例，系统如何通过 PowerHAL 动态调整 RenderThread 优先级。 |

**external. 07.04**
- - **章节**：7.4

**external. 07.04**
- - **盲区描述**：跨进程动画中 `SurfaceControl` 的接管 (Handover) 细节。

**external. 07.04**
- - **建议研究方向**：Android 12+ `SplashScreen` 的 `RemoteAnimation` 实现。

**external. 07.05**
- | Skia Graphite 引擎 | 低 | Android 15 正在推行的下一代 GPU 渲染引擎对 RenderEffect 的性能加持。 |

**external. 07.05**
- | ContentProvider 批量操作原子性 | 中 | 除了减少 Binder 调用，`applyBatch` 的事务特性对数据一致性的帮助。 |

**external. 07.05**
- - **章节**：7.5

**external. 07.05**
- - **盲区描述**：Android 15 新增的 `setFrameContentVelocity` 对自研 UI 引擎的启示。

**external. 07.08**
- | RecyclerView 1.4.0 预取的优先级算法 | 中 | 研究 `GapWorker` 在多 RecyclerView 实例共存时的任务排序逻辑 |

**external. 07.08**
- - [7.8][预取任务调度] 探讨在多屏、多列表场景下 `GapWorker` 如何平衡不同 `RecyclerView` 的预取预算。

**external. 07.09**
- | Chrome 的时间源平滑算法 | 中 | 调研 Chrome 如何在 Blink 层处理来自 VSync 的微小抖动 |

**external. 07.09**
- - [7.9][厂商优化调研] 调研主流手机厂商是否已经在 Framework 层修复了 `Choreographer` 的毫秒截断问题。

**external. 07.10**
- - **源码路径**：`frameworks/base/graphics/java/android/graphics/Bitmap.java` -> `checkHardware()`

**external. 07.10**
- - **技术结论**：`HARDWARE` 格式 Bitmap 禁止一切 CPU 侧像素读写（getPixel/copyPixelsToBuffer），违规将抛出 `IllegalStateException`。

**external. 07.10**
- - **版本差异**：Android 8.0+ 像素内存由 `NativeAllocationRegistry` 注册到 ART，内存压力能正确触发 GC。

**external. 07.10**
- ## 八、落盘信息

**external. 07.10**
- - 已写入文件：`logs/external-review/2026-04-25-15-ch07.10-external-review.md`

**external. 07.11**
- - **技术结论**：**WebView 的 GPU Service 始终为 In-Process（宿主进程线程）**。

**external. 07.11**
- - **风险点**：GPU 驱动崩溃会直接导致宿主进程（Host App）死亡，且无法通过 `onRenderProcessGone` 挽救。

**external. 07.11**
- - **版本分界线**：Android 11 是多进程渲染全量覆盖的分水岭；在此之前 32 位低内存设备常回退到单进程。

**external. 07.12**
- | LayoutLib / Compose 混合预览性能 | 中 | 预览时的布局解析逻辑与真机差异 |

**external. 07.12**
- | RenderNode 在重绘时的损坏区计算 | 高 | 硬件加速下 `invalidate(Rect)` 的实际作用边界 |

**external. 07.13**
- | Scene Framework 的手势冲突处理 | 高 | 多个场景重叠时，手势分发优先级如何动态切换 |

**external. 07.13**
- | Compose 在 SystemUI 中的常驻内存开销 | 中 | 与传统 ViewTree 相比，Composed UI 的基准内存占用 |

**external. 07.13**
- - **章节**：7.13

**external. 07.13**
- - **盲区描述**：Flexiglass 场景下的手势拦截机制。

**external. 07.13**
- - **建议研究方向**：分析 `SceneTransitionLayout` 内部的手势检测器如何与 `NotificationShadeWindowView` 的原有触摸逻辑并存。

**external. 08**
- | 16KB Page Size 导致的 NDK 对齐膨胀 | 中 | 研究 `-Wl,-z,max-page-size=16384` 对多层级动态库加载的影响 |

**external. 08**
- | Kotlin 2.2 的 K2 编译器对协程状态机的内联优化 | 高 | 比较 K1 vs K2 生成的字节码深度差异 |

**external. 08**
- - **章节**：`06-coroutine-performance.md`

**external. 08**
- - **盲区描述**：Android 16 是否支持在 `perfetto` 中直接看到协程层级的切换。

**external. 08**
- - **建议研究方向**：研究 `CoroutineContext` 的 `TrackedCoroutineInterceptor` 实验性特性。

**external. 08**
- | Vulkan Render Stages 观测 | 高 | Perfetto GPU Render Stages 插件与驱动支持情况 |

**external. 08**
- | GPU Counter 特权访问 | 中 | `security.perfetto.gpu_counters.privileged` 属性 |

**external. 08**
- - **章节**：`09-game-performance.md`

**external. 08**
- - **盲区描述**：各 OEM 厂商对 `Mode.GAME_LOADING` 的具体 HAL 实现差异。

**external. 08**
- - **建议研究方向**：调研主流厂商（如华为、小米、OPPO）对该信号的实际提频策略。

**external. 09**
- | Android 16 ProgressStyle 性能 | 中 | 验证其渲染是否完全在 SystemUI 进程内完成，不回掉给 App。 |

**external. 09**
- - **章节 9.6**：需持续关注 Android 16/17 中 `Live Update` 的配额管理机制。

**external. 10**
- | CMC GC 的 userfaultfd 损耗 | 高 | 研究 Android 15 在非分代 CMC 下的内存分配 Stall 表现。 |

**external. 10**
- | SQLite CursorWindow 在 64 位进程下的限制 | 中 | 验证 64 位进程下 `config_cursorWindowSize` 是否有厂商层面的大幅上调。 |

**external. 10**
- - **[05-case-studies.md][高]**：补充 GPU 驱动层（如 PowerVR/Adreno）内存池回收机制的差异性分析（虽不可直接 Hook，但可给出各厂商的典型行为模式）。

**external. 11**
- - **关键源码路径**：

**external. 11**
- - `frameworks/base/core/java/com/android/internal/os/CpuPowerCalculator.java` (Android 16 功耗计算核心)

**external. 11**
- - `system/hardware/interfaces/suspend/aidl/.../SystemSuspend.cpp` (现代 WakeLock 中枢)

**external. 11**
- - **能量优先原则**：Android 16 默认优先使用硬件 `uJ` 数据，只有在 HAL 不支持时才回退到 `power_profile.xml` 的 `mA` 估算。

**external. 11**
- - **权限豁免**：`OnAlarmListener` 设置的精确闹钟在 Android 14+ 豁免 `SCHEDULE_EXACT_ALARM` 权限，但其生命周期仅限于进程存活期。

**external. 11**
- - `src/part2-performance/ch13-tools/`（第 13 章：性能工具链路）

**external. 18**
- - **18.11 ANGLE**: `GraphicsEnvironment.shouldUseAngleInternal()` 的决策链是排查“为什么我的 App 走/没走 ANGLE”的唯一官方真相。

**external. 18**
- - **18.13 WebView**: `OverlayProcessorWebView` 源码路径是分析 WebView 视频卡顿（是否命中硬件 Overlay）的终极证据。

**external. 18**
- - **18.14 Camera**: AIDL 接口 `ICameraDeviceSession.aidl` 是 Android 14+ 之后所有相机性能调试（特别是 Buffer 流转）的入口。

**external. 18**
- - `src/part2-performance/ch19-power-optimization/`（功耗优化与 HWC 章节高度关联）

**external. 18**
- - **[18.17]**：API 36 的 `ASurfaceTransaction_setBufferWithRelease` 在多缓冲池（Buffer Pooling）场景下的具体性能收益量化数据（待补充 Trace 案例）。

**external. 18**
- - **[18.21]**：Android 17 EyeDropper 在折叠屏/跨屏场景下的取色点坐标映射逻辑。

## [2026-04-25] 14.9 — 知识盲区
### 盲区描述
Qualcomm CHI Feature (夜景等自定义算法) 耗时追踪。
### 重要程度
中
### 建议研究方向

### 关联章节
- 14.9
### 外部 review 来源
- external-review

## [2026-04-25] 14.9 — 知识盲区
### 盲区描述
MTK 平台特定的 `MtkCam` Trace 标记。
### 重要程度
中
### 建议研究方向

### 关联章节
- 14.9
### 外部 review 来源
- external-review

## [2026-04-25] 11 — 知识盲区
### 盲区描述
FrameData 对象重用风险
### 重要程度
高
### 建议研究方向
源码中回调参数的生命周期
### 关联章节
- 11
### 外部 review 来源
- external-review

## [2026-04-25] 11 — 知识盲区
### 盲区描述
多 Window 监控冲突
### 重要程度
中
### 建议研究方向
一个 Activity 存在多个 Window（如 PopWindow/Dialog）时 JankStats 的覆盖范围
### 关联章节
- 11
### 外部 review 来源
- external-review

## [2026-04-25] 11 — 知识盲区
### 盲区描述
关键源码路径：`androidx/metrics/performance/JankStats.kt`
### 重要程度
中
### 建议研究方向

### 关联章节
- 11
### 外部 review 来源
- external-review

## [2026-04-25] 11 — 知识盲区
### 盲区描述
技术结论：JankStats 本质上是 `FrameMetrics` (API 24+) 的包装器，而在 API 16-23 上则降级为 `Choreographer` 模拟。
### 重要程度
中
### 建议研究方向

### 关联章节
- 11
### 外部 review 来源
- external-review

## [2026-04-25] 13.1 — 知识盲区
### 盲区描述
Mainline APEX 部署
### 重要程度
中
### 建议研究方向
研究 `com.android.os.perfetto` 的打包与更新逻辑
### 关联章节
- 13.1
### 外部 review 来源
- external-review

## [2026-04-25] 13.1 — 知识盲区
### 盲区描述
memfd_create 在 Perfetto 中的应用
### 重要程度
低
### 建议研究方向
对比 ashmem 与 memfd 在 trace 数据传递中的差异
### 关联章节
- 13.1
### 外部 review 来源
- external-review

## [2026-04-25] 13.10 — 知识盲区
### 盲区描述
`sqlite_master` 表在 Perfetto 里的可见性限制
### 重要程度
低
### 建议研究方向
为什么某些系统表无法通过普通 SELECT 访问
### 关联章节
- 13.10
### 外部 review 来源
- external-review

## [2026-04-25] 13.2 — 知识盲区
### 盲区描述
binderfs 时代的 ftrace 路径
### 重要程度
低
### 建议研究方向
研究 `/sys/kernel/debug/tracing` 与 `/sys/kernel/tracing` 的符号链接关系
### 关联章节
- 13.2
### 外部 review 来源
- external-review

## [2026-04-25] 13.2 — 知识盲区
### 盲区描述
DWARF unwinding 性能开销
### 重要程度
中
### 建议研究方向
对比 `linux.perf` 在不同采样频率下对 CPU 的压测数据
### 关联章节
- 13.2
### 外部 review 来源
- external-review

## [2026-04-25] 13.3 — 知识盲区
### 盲区描述
HWUI 渲染管线在 Trace 中的具体表现
### 重要程度
中
### 建议研究方向
对比 OpenGLES 与 Vulkan 后端在 RenderThread 上的 Slice 差异
### 关联章节
- 13.3
### 外部 review 来源
- external-review

## [2026-04-25] 13.4 — 知识盲区
### 盲区描述
Bigtrace 分布式架构
### 重要程度
中
### 建议研究方向
针对数千个 Trace 的分布式 SQL 引擎实现
### 关联章节
- 13.4
### 外部 review 来源
- external-review

## [2026-04-25] 13.4 — 知识盲区
### 盲区描述
PerfettoSQL 预编译宏
### 重要程度
低
### 建议研究方向
如何在 `trace_processor` 中预加载自定义 SQL 函数库
### 关联章节
- 13.4
### 外部 review 来源
- external-review

## [2026-04-25] 13.5 — 知识盲区
### 盲区描述
`SPAN_JOIN` 在 I/O 与调度交叉分析中的应用
### 重要程度
高
### 建议研究方向
如何用 SQL 同时展示 I/O 等待期间 CPU 到底在跑谁
### 关联章节
- 13.5
### 外部 review 来源
- external-review

## [2026-04-25] 13.5 — 知识盲区
### 盲区描述
Android 15 新增的 `android.frames.jank_type` 扩展枚举
### 重要程度
中
### 建议研究方向
关注新的 Jank 归因类型（如特定 HAL 延迟）
### 关联章节
- 13.5
### 外部 review 来源
- external-review

## [2026-04-25] 13.6 — 知识盲区
### 盲区描述
`TASK_KILLABLE` 在 Android 进程管理中的应用
### 重要程度
低
### 建议研究方向
对比 D 状态与 Killable 状态在 ANR 触发时的差异
### 关联章节
- 13.6
### 外部 review 来源
- external-review

## [2026-04-25] 13.6 — 知识盲区
### 盲区描述
调度器 cgroup 对 Runnable 耗时的非线性影响
### 重要程度
中
### 建议研究方向
研究权重（cpu.shares）与配额（cpu.cfs_quota_us）的交互
### 关联章节
- 13.6
### 外部 review 来源
- external-review

## [2026-04-25] 13.7 — 知识盲区
### 盲区描述
`Bigtrace` 的分布式部署架构
### 重要程度
中
### 建议研究方向
针对 PB 级 Trace 仓库的分布式查询引擎
### 关联章节
- 13.7
### 外部 review 来源
- external-review

## [2026-04-25] 13.7 — 知识盲区
### 盲区描述
`Perfetto UI` 的 `Extension Server` 协议
### 重要程度
低
### 建议研究方向
如何自建私有 UI 插件服务器
### 关联章节
- 13.7
### 外部 review 来源
- external-review

## [2026-04-25] 13.8 — 知识盲区
### 盲区描述
`InputDispatcher` 的 `Connection` 生命周期
### 重要程度
中
### 建议研究方向
SQL 表 `android_input_connections` 的状态变迁含义
### 关联章节
- 13.8
### 外部 review 来源
- external-review

## [2026-04-25] 13.8 — 知识盲区
### 盲区描述
虚拟输入设备在 Trace 中的表现
### 重要程度
低
### 建议研究方向
如何区分物理触摸和通过 adb 下发的虚拟点击
### 关联章节
- 13.8
### 外部 review 来源
- external-review

## [2026-04-25] 13.9 — 知识盲区
### 盲区描述
`static_key` 在 Tracepoint 中的汇编级实现
### 重要程度
低
### 建议研究方向
`nop` 指令如何被替换为 `jmp` 以实现零开销追踪
### 关联章节
- 13.9
### 外部 review 来源
- external-review

## [2026-04-25] 13.9 — 知识盲区
### 盲区描述
`perfetto` 进程内 TracePacket 缓存机制
### 重要程度
中
### 建议研究方向
避免 `trace_marker` 写入导致进程频繁唤醒的优化策略
### 关联章节
- 13.9
### 外部 review 来源
- external-review

## [2026-04-25] 15.1 — 知识盲区
### 盲区描述
Android 16 system-triggered profiling
### 重要程度
中
### 建议研究方向
持续关注 AOSP 变动
### 关联章节
- 15.1
### 外部 review 来源
- external-review

## [2026-04-25] 15.1 — 知识盲区
### 盲区描述
章节：15.1
### 重要程度
中
### 建议研究方向

### 关联章节
- 15.1
### 外部 review 来源
- external-review

## [2026-04-25] 15.1 — 知识盲区
### 盲区描述
盲区描述：Android 16 动态触发 profiling 的具体内核约束。
### 重要程度
中
### 建议研究方向

### 关联章节
- 15.1
### 外部 review 来源
- external-review

## [2026-04-25] 15.1 — 知识盲区
### 盲区描述
重要程度：中
### 重要程度
中
### 建议研究方向

### 关联章节
- 15.1
### 外部 review 来源
- external-review

## [2026-04-25] 15.10 — 知识盲区
### 盲区描述
Android 16 system-triggered profiling
### 重要程度
中
### 建议研究方向
持续关注 AOSP 变动
### 关联章节
- 15.10
### 外部 review 来源
- external-review

## [2026-04-25] 15.10 — 知识盲区
### 盲区描述
章节：15.10
### 重要程度
中
### 建议研究方向

### 关联章节
- 15.10
### 外部 review 来源
- external-review

## [2026-04-25] 15.10 — 知识盲区
### 盲区描述
盲区描述：Android 16 动态触发 profiling 的具体内核约束。
### 重要程度
中
### 建议研究方向

### 关联章节
- 15.10
### 外部 review 来源
- external-review

## [2026-04-25] 15.10 — 知识盲区
### 盲区描述
重要程度：中
### 重要程度
中
### 建议研究方向

### 关联章节
- 15.10
### 外部 review 来源
- external-review

## [2026-04-25] 15.2 — 知识盲区
### 盲区描述
Android 16 system-triggered profiling
### 重要程度
中
### 建议研究方向
持续关注 AOSP 变动
### 关联章节
- 15.2
### 外部 review 来源
- external-review

## [2026-04-25] 15.2 — 知识盲区
### 盲区描述
章节：15.2
### 重要程度
中
### 建议研究方向

### 关联章节
- 15.2
### 外部 review 来源
- external-review

## [2026-04-25] 15.2 — 知识盲区
### 盲区描述
盲区描述：Android 16 动态触发 profiling 的具体内核约束。
### 重要程度
中
### 建议研究方向

### 关联章节
- 15.2
### 外部 review 来源
- external-review

## [2026-04-25] 15.2 — 知识盲区
### 盲区描述
重要程度：中
### 重要程度
中
### 建议研究方向

### 关联章节
- 15.2
### 外部 review 来源
- external-review

## [2026-04-25] 15.3 — 知识盲区
### 盲区描述
Android 16 system-triggered profiling
### 重要程度
中
### 建议研究方向
持续关注 AOSP 变动
### 关联章节
- 15.3
### 外部 review 来源
- external-review

## [2026-04-25] 15.3 — 知识盲区
### 盲区描述
章节：15.3
### 重要程度
中
### 建议研究方向

### 关联章节
- 15.3
### 外部 review 来源
- external-review

## [2026-04-25] 15.3 — 知识盲区
### 盲区描述
盲区描述：Android 16 动态触发 profiling 的具体内核约束。
### 重要程度
中
### 建议研究方向

### 关联章节
- 15.3
### 外部 review 来源
- external-review

## [2026-04-25] 15.3 — 知识盲区
### 盲区描述
重要程度：中
### 重要程度
中
### 建议研究方向

### 关联章节
- 15.3
### 外部 review 来源
- external-review

## [2026-04-25] 15.4 — 知识盲区
### 盲区描述
Android 16 system-triggered profiling
### 重要程度
中
### 建议研究方向
持续关注 AOSP 变动
### 关联章节
- 15.4
### 外部 review 来源
- external-review

## [2026-04-25] 15.4 — 知识盲区
### 盲区描述
章节：15.4
### 重要程度
中
### 建议研究方向

### 关联章节
- 15.4
### 外部 review 来源
- external-review

## [2026-04-25] 15.4 — 知识盲区
### 盲区描述
盲区描述：Android 16 动态触发 profiling 的具体内核约束。
### 重要程度
中
### 建议研究方向

### 关联章节
- 15.4
### 外部 review 来源
- external-review

## [2026-04-25] 15.4 — 知识盲区
### 盲区描述
重要程度：中
### 重要程度
中
### 建议研究方向

### 关联章节
- 15.4
### 外部 review 来源
- external-review

## [2026-04-25] 15.5 — 知识盲区
### 盲区描述
Android 16 system-triggered profiling
### 重要程度
中
### 建议研究方向
持续关注 AOSP 变动
### 关联章节
- 15.5
### 外部 review 来源
- external-review

## [2026-04-25] 15.5 — 知识盲区
### 盲区描述
章节：15.5
### 重要程度
中
### 建议研究方向

### 关联章节
- 15.5
### 外部 review 来源
- external-review

## [2026-04-25] 15.5 — 知识盲区
### 盲区描述
盲区描述：Android 16 动态触发 profiling 的具体内核约束。
### 重要程度
中
### 建议研究方向

### 关联章节
- 15.5
### 外部 review 来源
- external-review

## [2026-04-25] 15.5 — 知识盲区
### 盲区描述
重要程度：中
### 重要程度
中
### 建议研究方向

### 关联章节
- 15.5
### 外部 review 来源
- external-review

## [2026-04-25] 15.6 — 知识盲区
### 盲区描述
Android 16 system-triggered profiling
### 重要程度
中
### 建议研究方向
持续关注 AOSP 变动
### 关联章节
- 15.6
### 外部 review 来源
- external-review

## [2026-04-25] 15.6 — 知识盲区
### 盲区描述
章节：15.6
### 重要程度
中
### 建议研究方向

### 关联章节
- 15.6
### 外部 review 来源
- external-review

## [2026-04-25] 15.6 — 知识盲区
### 盲区描述
盲区描述：Android 16 动态触发 profiling 的具体内核约束。
### 重要程度
中
### 建议研究方向

### 关联章节
- 15.6
### 外部 review 来源
- external-review

## [2026-04-25] 15.6 — 知识盲区
### 盲区描述
重要程度：中
### 重要程度
中
### 建议研究方向

### 关联章节
- 15.6
### 外部 review 来源
- external-review

## [2026-04-25] 15.7 — 知识盲区
### 盲区描述
Android 16 system-triggered profiling
### 重要程度
中
### 建议研究方向
持续关注 AOSP 变动
### 关联章节
- 15.7
### 外部 review 来源
- external-review

## [2026-04-25] 15.7 — 知识盲区
### 盲区描述
章节：15.7
### 重要程度
中
### 建议研究方向

### 关联章节
- 15.7
### 外部 review 来源
- external-review

## [2026-04-25] 15.7 — 知识盲区
### 盲区描述
盲区描述：Android 16 动态触发 profiling 的具体内核约束。
### 重要程度
中
### 建议研究方向

### 关联章节
- 15.7
### 外部 review 来源
- external-review

## [2026-04-25] 15.7 — 知识盲区
### 盲区描述
重要程度：中
### 重要程度
中
### 建议研究方向

### 关联章节
- 15.7
### 外部 review 来源
- external-review

## [2026-04-25] 15.8 — 知识盲区
### 盲区描述
Android 16 system-triggered profiling
### 重要程度
中
### 建议研究方向
持续关注 AOSP 变动
### 关联章节
- 15.8
### 外部 review 来源
- external-review

## [2026-04-25] 15.8 — 知识盲区
### 盲区描述
章节：15.8
### 重要程度
中
### 建议研究方向

### 关联章节
- 15.8
### 外部 review 来源
- external-review

## [2026-04-25] 15.8 — 知识盲区
### 盲区描述
盲区描述：Android 16 动态触发 profiling 的具体内核约束。
### 重要程度
中
### 建议研究方向

### 关联章节
- 15.8
### 外部 review 来源
- external-review

## [2026-04-25] 15.8 — 知识盲区
### 盲区描述
重要程度：中
### 重要程度
中
### 建议研究方向

### 关联章节
- 15.8
### 外部 review 来源
- external-review

## [2026-04-25] 15.9 — 知识盲区
### 盲区描述
Android 16 system-triggered profiling
### 重要程度
中
### 建议研究方向
持续关注 AOSP 变动
### 关联章节
- 15.9
### 外部 review 来源
- external-review

## [2026-04-25] 15.9 — 知识盲区
### 盲区描述
章节：15.9
### 重要程度
中
### 建议研究方向

### 关联章节
- 15.9
### 外部 review 来源
- external-review

## [2026-04-25] 15.9 — 知识盲区
### 盲区描述
盲区描述：Android 16 动态触发 profiling 的具体内核约束。
### 重要程度
中
### 建议研究方向

### 关联章节
- 15.9
### 外部 review 来源
- external-review

## [2026-04-25] 15.9 — 知识盲区
### 盲区描述
重要程度：中
### 重要程度
中
### 建议研究方向

### 关联章节
- 15.9
### 外部 review 来源
- external-review

## [2026-04-25] None — 知识盲区
### 盲区描述
Android 16 system-triggered profiling
### 重要程度
中
### 建议研究方向
持续关注 AOSP 变动
### 关联章节
- None
### 外部 review 来源
- external-review

## [2026-04-25] None — 知识盲区
### 盲区描述
章节：15.README
### 重要程度
中
### 建议研究方向

### 关联章节
- None
### 外部 review 来源
- external-review

## [2026-04-25] None — 知识盲区
### 盲区描述
盲区描述：Android 16 动态触发 profiling 的具体内核约束。
### 重要程度
中
### 建议研究方向

### 关联章节
- None
### 外部 review 来源
- external-review

## [2026-04-25] None — 知识盲区
### 盲区描述
重要程度：中
### 重要程度
中
### 建议研究方向

### 关联章节
- None
### 外部 review 来源
- external-review

## [2026-04-25] 17 — 知识盲区
### 盲区描述
Firebase 采集限流：10 分钟 300 事件，超出部分会被设备端直接丢弃。
### 重要程度
中
### 建议研究方向

### 关联章节
- 17
### 外部 review 来源
- external-review

## [2026-04-25] 19.17 19.17 — 知识盲区

- Firebase 采集限流：10 分钟 300 事件，超出部分会被设备端直接丢弃。

### 外部 review 来源
- Gemini 外部 review (2026-04-25-15-17-external-review.md)


## [2026-04-25] 19.16 ProfilingManager — 知识盲区

### 盲区描述
Heap Dump 敏感数据脱敏

### 重要程度
高

### 建议研究方向
ProfilingManager 简化了采集但未简化合规，需补充 OID 脱敏或加密流程的研究

### 关联章节
- 19.16

### 外部 review 来源
- Gemini 外部 review (2026-04-25)

## [2026-04-25] 19.17 Firebase Performance — 知识盲区

### 盲区描述
Firebase 采集限流与插桩冲突

### 重要程度
高

### 建议研究方向
10 分钟 300 事件限流、复杂 AOP 框架导致网络数据采集失败

### 关联章节
- 19.17

### 外部 review 来源
- Gemini 外部 review (2026-04-25)

## [2026-04-25] 19.18 APM SDK 选型 — 知识盲区

### 盲区描述
APM SDK 初始化对启动的影响

### 重要程度
中

### 建议研究方向
Sentry、Bugly Pro 等初始化时的反射/字节码插桩开销需量化

### 关联章节
- 19.18

### 外部 review 来源
- Gemini 外部 review (2026-04-25)

## [2026-04-25] 19.19 PerfDog — 知识盲区

### 盲区描述
GPU 指标跨 SoC 差异

### 重要程度
高

### 建议研究方向
PerfDog 对 GPU 读取深度取决于 SoC 驱动，跨芯片平台指标不可横比

### 关联章节
- 19.19

### 外部 review 来源
- Gemini 外部 review (2026-04-25)

## [2026-04-25] 19.20 其他性能测试工具 — 知识盲区

### 盲区描述
SoloPi 前台服务与后台启动 Activity 限制

### 重要程度
中

### 建议研究方向
SoloPi targetSdkVersion 29，Android 14+ 限制更严

### 关联章节
- 19.20

### 外部 review 来源
- Gemini 外部 review (2026-04-25)
