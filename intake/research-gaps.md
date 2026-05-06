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

## [2026-04-25] 14.11 Battery Historian — 知识盲区

### 盲区描述
PowerMonitor API 累计值语义

### 重要程度
高

### 建议研究方向
getConsumedEnergy() 返回设备启动以来累计 μWs，需差值计算特定操作功耗；Perfetto Power Rails 可联合查询功耗与调度

### 关联章节
- 14.11

### 外部 review 来源
- Gemini 外部 review (2026-04-25)


## [2026-04-25] 15.2 系统 vs 应用归因 — 知识盲区

### 盲区描述
Android 14+ ANR 弹性放宽机制

### 重要程度
高

### 建议研究方向
CPU 饥饿时 BroadcastReceiver ANR 窗口可能放宽到 2x，需补充文档锚点

### 关联章节
- 15.2

### 外部 review 来源
- Gemini 外部 review (2026-04-25)


## [2026-04-25] 15.5 线上监控 — 知识盲区

### 盲区描述
现代 Android traces.txt 监听不可行

### 重要程度
高

### 建议研究方向
Android 10+ 沙盒权限收紧，普通 App 无法监听系统目录，应全面转向 ApplicationExitInfo

### 关联章节
- 15.5

### 外部 review 来源
- Gemini 外部 review (2026-04-25)

## [2026-04-25] 12.1 APK 体积优化 — 知识盲区

### 盲区描述
AGP 8.12/8.13 的 `android.r8.optimizedResourceShrinking` 与 AGP 9.0 默认启用路径下，动态资源引用（`Resources.getIdentifier()`、字符串拼接资源名、插件/WebView 资源路径）如何安全保留，正文缺少可执行验证方案。external-review 已命中 optimized resource shrinking 风险，本轮复核后确认需要补官方 `tools:keep` / `resources.txt` 口径。

### 重要程度
高

### 建议研究方向
- Android 官方 “Customize which resources to keep” 文档中 `getIdentifier()`、`tools:keep`、`resources.txt` 的现代用法
- AGP 8.12/8.13 opt-in 与 AGP 9.0 默认启用的行为差异
- 典型动态资源访问回归测试样例

### 关联章节
- 12.1

## [2026-04-25] 12.4 Android 网络安全与 TLS 性能优化 — 知识盲区

### 盲区描述
Android 17 网络安全行为需要按 ECH、CT、cleartext、客户端网络库能力拆开验证。ECH 依赖网络库集成；CT 默认启用有完整 SCT policy；cleartext hard block 目前缺少官方行为变更证据；OkHttp 的 TLS 1.3 与 0-RTT/HTTP3 能力也不能混写。

### 重要程度
高

### 建议研究方向
- Android 17 behavior changes 中 ECH、CT 的 targetSdk 条件
- Android Certificate Transparency Policy 的 embedded / OCSP / TLS SCT 数量规则
- OkHttp、Cronet、HttpEngine 对 ECH、HTTP/3、0-RTT 的公开能力边界
- `usesCleartextTraffic` 与 Network Security Configuration 在 API 28/37 的官方行为说明

### 关联章节
- 12.4
- 12.3

## [2026-04-25] 19.1 APM Landscape — 知识盲区

### 盲区描述
边缘性能恶化场景的 Trace 特征

### 重要程度
中

### 建议研究方向
结合真实性能瓶颈 trace 分析

### 关联章节
- 19.1

### 外部 review 来源
- Gemini 外部 review (2026-04-25)


## [2026-04-25] 19.11 JankStats — 知识盲区

### 盲区描述
JankStats 工具在极端场景下的自身性能开销。

### 重要程度
中

### 建议研究方向
结合实测分析，提供量化指标。

### 关联章节
- 19.11

### 外部 review 来源
- Gemini 外部 review (2026-04-25)


## [2026-04-25] 19.2 Tencent Matrix — 知识盲区

### 盲区描述
边缘性能恶化场景的 Trace 特征

### 重要程度
中

### 建议研究方向
结合真实性能瓶颈 trace 分析

### 关联章节
- 19.2

### 外部 review 来源
- Gemini 外部 review (2026-04-25)


## [2026-04-25] 19.3 KOOM — 知识盲区

### 盲区描述
边缘性能恶化场景的 Trace 特征

### 重要程度
中

### 建议研究方向
结合真实性能瓶颈 trace 分析

### 关联章节
- 19.3

### 外部 review 来源
- Gemini 外部 review (2026-04-25)


## [2026-04-25] 19.4 BTrace — 知识盲区

### 盲区描述
边缘性能恶化场景的 Trace 特征

### 重要程度
中

### 建议研究方向
结合真实性能瓶颈 trace 分析

### 关联章节
- 19.4

### 外部 review 来源
- Gemini 外部 review (2026-04-25)


## [2026-04-25] 19.5 LeakCanary — 知识盲区

### 盲区描述
边缘性能恶化场景的 Trace 特征

### 重要程度
中

### 建议研究方向
结合真实性能瓶颈 trace 分析

### 关联章节
- 19.5

### 外部 review 来源
- Gemini 外部 review (2026-04-25)


## [2026-04-25] 19.6 BlockCanary — 知识盲区

### 盲区描述
BlockCanary 工具在极端场景下的自身性能开销。

### 重要程度
中

### 建议研究方向
结合实测分析，提供量化指标。

### 关联章节
- 19.6

### 外部 review 来源
- Gemini 外部 review (2026-04-25)


## [2026-04-25] 19.7 DoKit — 知识盲区

### 盲区描述
DoKit 工具在极端场景下的自身性能开销。

### 重要程度
中

### 建议研究方向
结合实测分析，提供量化指标。

### 关联章节
- 19.7

### 外部 review 来源
- Gemini 外部 review (2026-04-25)


## [2026-04-25] 19.8 ArgusAPM — 知识盲区

### 盲区描述
ArgusAPM 工具在极端场景下的自身性能开销。

### 重要程度
中

### 建议研究方向
结合实测分析，提供量化指标。

### 关联章节
- 19.8

### 外部 review 来源
- Gemini 外部 review (2026-04-25)


## [2026-04-25] 19.9 Measure — 知识盲区

### 盲区描述
Measure 工具在极端场景下的自身性能开销。

### 重要程度
中

### 建议研究方向
结合实测分析，提供量化指标。

### 关联章节
- 19.9

### 外部 review 来源
- Gemini 外部 review (2026-04-25)

## [2026-04-25] 15.5 线上性能监控 — 知识盲区

### 盲区描述
ANR/退出监控仍缺 SIGQUIT SignalCatcher、自建 APM 信号栈、ApplicationExitInfo 多退出原因，以及 Android 15/16 ProfilingManager 异常触发取证的统一模型。external-review 已命中 SIGQUIT Hook 与 ProfilingManager 缺口，本轮源码复核后确认需要 Task 2B 补强。

### 重要程度
高

### 建议研究方向
- ART `art/runtime/signal_catcher.cc` 中 `SignalCatcher::HandleSigQuit()` 与系统 ANR trace 生成
- `ApplicationExitInfo` 的 `REASON_ANR`、`REASON_CRASH_NATIVE`、`getTraceInputStream()` 适用边界
- Android 15/16 `ProfilingManager` system-triggered profiling 的触发条件、产物类型与隐私约束

### 关联章节
- 15.5
- 9.3
- 19.16

## [2026-04-25] 15.6 性能测试最佳实践 — 知识盲区

### 盲区描述
现代性能测试环境控制缺少刷新率锁定、Android 14+ ART Service 背景 dexopt 干扰处理，以及峰值性能/热稳定态两套实验设计。external-review 已命中刷新率与测试场景分层缺口，本轮复核后确认会直接影响测试可重复性。

### 重要程度
高

### 建议研究方向
- `peak_refresh_rate` / `min_refresh_rate` 设置、`dumpsys display` 与 Perfetto FrameTimeline 验证方式
- Android 14+ `pm bg-dexopt-job --cancel/--disable`、`pm cancel-bg-dexopt-job` 兼容关系
- 短跑回归与长跑稳态测试的温度门槛、预热时长和报告字段

### 关联章节
- 15.6
- 14.6
- 5.5

## [2026-04-25] 15.7 AOSP 代码阅读 — 知识盲区

### 盲区描述
源码阅读方法缺少 Android 10+ `wm/` 包、跨 Binder/AIDL 边界追踪、异步 Trace cookie 配对，以及 Android 16 SurfaceFlinger/CompositionEngine 入口变更。external-review 已命中 wm 目录与 Binder 边界缺口，本轮源码复核又发现 Trace.h 与 SurfaceFlinger 锚点过期。

### 重要程度
高

### 建议研究方向
- `frameworks/base/services/core/java/com/android/server/wm/` 与 `am/` 的职责分界
- AIDL Stub/Proxy、`onTransact`、Perfetto binder transaction 的联合追踪
- `Trace.asyncTraceBegin/End`、`ATRACE_ASYNC_BEGIN/END` 的 name + cookie 配对
- Android 16 `SurfaceFlinger::composite()`、`CompositionEngine::present()`、`Output::present()` 调用链

### 关联章节
- 15.7
- 2.6
- 13.9

## [2026-04-25] 8.09 Game Performance — 知识盲区

### 盲区描述
GPU Counter 特权访问属性 security.perfetto.gpu_counters.privileged

### 重要程度
中-高

### 建议研究方向
- 外部 review 提出的后续研究项

### 关联章节
- 8.09

### 外部 review 来源
- Gemini 外部 review (2026-04-25-15-8.README-external-review.md)

## [2026-04-25] 9.05 ch09 案例集与专项 — 知识盲区

### 盲区描述
Android 16/17 Live Update 渲染是否完全在 SystemUI 进程内完成

### 重要程度
中-高

### 建议研究方向
- 外部 review 提出的后续研究项

### 关联章节
- 9.05

### 外部 review 来源
- Gemini 外部 review (2026-04-25-15-9.README-external-review.md)

## [2026-04-25] 12 APK 与网络性能 — 知识盲区

### 盲区描述
Brotli 共享字典 SDCH 在 Android 15 的支持情况

### 重要程度
中-高

### 建议研究方向
- 外部 review 提出的后续研究项

### 关联章节
- 12

### 外部 review 来源
- Gemini 外部 review (2026-04-25-15-12.README-external-review.md)

## [2026-04-25] 12 APK 与网络性能 — 知识盲区

### 盲区描述
QUIC Connection Migration 在 Perfetto 中的识别方法

### 重要程度
中-高

### 建议研究方向
- 外部 review 提出的后续研究项

### 关联章节
- 12

### 外部 review 来源
- Gemini 外部 review (2026-04-25-15-12.README-external-review.md)

## [2026-04-25] 15.README 方法论章节 README — 知识盲区

### 盲区描述
高负载或内存触顶情况下边缘 Trace 异常特征

### 重要程度
中-高

### 建议研究方向
- 外部 review 提出的后续研究项

### 关联章节
- 15.README

### 外部 review 来源
- Gemini 外部 review (2026-04-25-15-15.README-external-review.md)

## [2026-04-25] 18.16 渲染管线(Game Engine/VRR/PIP 等) — 知识盲区

### 盲区描述
API 36 ASurfaceTransaction_setBufferWithRelease 在多缓冲池场景下的性能收益量化

### 重要程度
中-高

### 建议研究方向
- 外部 review 提出的后续研究项

### 关联章节
- 18.16

### 外部 review 来源
- Gemini 外部 review (2026-04-25-15-18.README-external-review.md)

## [2026-04-25] 19.14 — 知识盲区

### 多进程 App 监控限制
remote` 或其他进程，`FrameTimingMetric` 可能采集不到对应的渲染帧。

建议研究方向：提醒开发者对于多进程应用，需确认被测逻辑是否在 targetPackage 的主进程中，或查阅最新的多进程支持 API。

### 外部 review 来源
- 2026-04-25-15-14-external-review.md


## [2026-04-25] 19.15 — 知识盲区

### R8 混淆对 Profile 匹配的影响
Baseline Profile 规则是在混淆前生成的。AGP 在打包时会自动将规则映射到混淆后的名称，但如果开发者手动移动 `.prof` 文件或使用了非标混淆流程，会导致 Profile 命中率为 0。

建议研究方向：提醒开发者检查 AAB 产物中解密后的 profile 记录是否与混淆后的 `mapping.txt` 一致。

### 外部 review 来源
- 2026-04-25-15-15-external-review.md


## [2026-04-25] 19.16 — 知识盲区

### 重样本数据的安全性与合规
未强调文件外传的安全性。

建议研究方向：必须增加“安全警示”，提醒开发者在上传结果前必须在本地进行 OID（对象标识符）脱敏或加密，且必须符合 App 隐私协议。

### 外部 review 来源
- 2026-04-25-15-16-external-review.md


## [2026-04-25] 19.17 — 知识盲区

### 网络插桩冲突
Firebase 通过字节码插桩拦截 OkHttp。如果业务中使用了某些复杂的 AOP 框架（如：自定义 Transformer 顺序不当）或者 OkHttp 的自定义 `EventListener` 占据了全局槽位，Firebase 的网络数据会采集失败。

建议研究方向：提醒开发者在 `build.log` 中检查 Firebase 插件的插桩日志。

### 9.2 知识盲区
- Firebase 采集限流：10 分钟 300 事件，超出部分会被设备端直接丢弃。

### 外部 review 来源
- 2026-04-25-15-17-external-review.md


## [2026-04-25] 19.19 — 知识盲区

### GPU 指标的 SoC 依赖
PerfDog 对 GPU 的读取深度取决于底层 SoC 驱动。在高通平台上数据较全，而在联发科或某些低端芯片上，GPU 利用率可能不可读或口径完全不同。

建议研究方向：补充“跨芯片平台指标不可横比”的警示。

### 外部 review 来源
- 2026-04-25-15-19-external-review.md



## [2026-04-25] 19.17 Firebase Performance Monitoring — 知识盲区

### 盲区描述
Firebase 采集存在设备端限流：10 分钟 300 事件，超出部分直接丢弃。这一限制可能导致事故分析时数据缺失。

### 重要程度
中

### 建议研究方向
- Firebase SDK 设备端限流策略与采样率的关系
- 限流场景下的数据完整性保障方案

### 关联章节
- 19.17

### 外部 review 来源
- Gemini 外部 review (2026-04-25-15-17-external-review.md)

## [2026-04-25] 19.16 ProfilingManager — 知识盲区

### 盲区描述
ProfilingManager 简化了 Heap Dump 采集，但未解决敏感数据合规问题。Heap Dump 包含所有 Java 对象明文。

### 重要程度
高

### 建议研究方向
- Heap Dump 脱敏方案（OID 替换、字段过滤）
- 合规框架下性能数据外传的最佳实践

### 关联章节
- 19.16

### 外部 review 来源
- Gemini 外部 review (2026-04-25-15-16-external-review.md)

## [2026-04-25] 8.7 Baseline Profiles 与编译优化实践 — 知识盲区

### 盲区描述
Android 16 Google Play cloud compilation 中 SDM（Secure Dex Metadata）与 Baseline Profile、Cloud Profile、设备侧 dex2oat/artd 的边界仍未闭环。章节目前只保留 `[待验证]`，缺少可执行的源码与官方资料核验方向。

### 重要程度
高

### 建议研究方向
- 核对 Android 16 SDM 的公开说明：分发渠道、与 APK 签名绑定、包含的云端编译产物类型。
- 核对 `packages/modules/Art/artd/` 与 ART Service 在 Android 14+ 后台 dexopt / `install-dm` / `bg-dexopt` 中的职责。
- 梳理 `baseline.prof`、`baseline.profm`、`.dm`、Cloud Profile、SDM 在 Play 安装、侧载、AGP 8.4 前后路径中的差异。

### 关联章节
- 8.7
- 1.7

### 外部 review 来源
- external-review 已命中：Android 16 SDM 文件和 artd 进程角色缺失

## [2026-04-25] 10.6 内存抖动 — 知识盲区 (External Review)

### 盲区描述
CMC GC 的 userfaultfd 损耗：Android 15 在非分代 CMC 下的内存分配 Stall 表现未覆盖。

### 重要程度
高

### 建议研究方向
- Android 15 CMC 下 userfaultfd 相关 Uninterruptible Sleep 状态的 Perfetto 观察方法
- 非分代 CMC vs 分代 CMC 的 STW 时间对比

### 关联章节
- 10.6

### 外部 review 来源
- Gemini 外部 review (2026-04-25-15-10.README-external-review.md)

## [2026-04-25] 10.7 SQLite — 知识盲区 (External Review)

### 盲区描述
SQLite CursorWindow 在 64 位进程下的限制：验证 64 位进程下 config_cursorWindowSize 是否有厂商层面的大幅上调。

### 重要程度
中

### 建议研究方向
- 各 OEM 64 位进程 CursorWindow 大小配置差异

### 关联章节
- 10.7

### 外部 review 来源
- Gemini 外部 review (2026-04-25-15-10.README-external-review.md)

## [2026-04-25] 12.2 QUIC 连接迁移 — 知识盲区 (External Review)

### 盲区描述
QUIC Connection Migration 在 Perfetto 中如何识别 Socket 切换。

### 重要程度
高

### 建议研究方向
- Perfetto 中 Connection Migration 触发的 Socket 切换观测方法

### 关联章节
- 12.2

### 外部 review 来源
- Gemini 外部 review (2026-04-25-15-12.README-external-review.md)

## [2026-04-25] 15.README 边缘 Trace 场景 — 知识盲区 (External Review)

### 盲区描述
高负载或内存触顶情况下的边界 Trace 异常特征。

### 重要程度
中

### 建议研究方向
- 边缘性能恶化场景的 Trace 特征提取

### 关联章节
- 15.README

### 外部 review 来源
- Gemini 外部 review (2026-04-25-15-15.README-external-review.md)

## [2026-04-25] 19.17 Firebase 采集限流 — 知识盲区 (External Review)

### 盲区描述
Firebase 采集限流：10 分钟 300 事件，超出部分被设备端直接丢弃。

### 重要程度
中

### 建议研究方向
- Firebase Performance SDK 各版本限流策略对比
- 与业务监控互补的最佳实践

### 关联章节
- 19.17

### 外部 review 来源
- Gemini 外部 review (2026-04-25-15-17-external-review.md)

## [2026-04-25] 18.17 Buffer Release 性能量化 — 知识盲区 (External Review)

### 盲区描述
API 36 ASurfaceTransaction_setBufferWithRelease 在多缓冲池场景下的具体性能收益量化数据。

### 重要程度
中

### 建议研究方向
- 补充多 Buffer Pooling 场景的 Trace 案例对比

### 关联章节
- 18.17

### 外部 review 来源
- Gemini 外部 review (2026-04-25-15-18.README-external-review.md)

## [2026-04-25] 18.21 EyeDropper 折叠屏取色 — 知识盲区 (External Review)

### 盲区描述
Android 17 EyeDropper 在折叠屏/跨屏场景下的取色点坐标映射逻辑。

### 重要程度
低

### 建议研究方向
- Android 17 EyeDropper 多 Display 取色坐标映射

### 关联章节
- 18.21

### 外部 review 来源
- Gemini 外部 review (2026-04-25-15-18.README-external-review.md)

## [2026-04-25] 8.09 Vulkan Render Stages — 知识盲区 (External Review)

### 盲区描述
Vulkan Render Stages 观测：各设备 Perfetto GPU Render Stages 插件与驱动支持情况。

### 重要程度
高

### 建议研究方向
- android.gpu.renderstages 数据源在各 SoC 平台的支持度
- security.perfetto.gpu_counters.privileged 属性配置

### 关联章节
- 8.09

### 外部 review 来源
- Gemini 外部 review (2026-04-25-15-8.README-external-review.md)

## [2026-04-25] 9.6 ProgressStyle 渲染进程 — 知识盲区 (External Review)

### 盲区描述
Android 16 ProgressStyle 性能：其渲染是否完全在 SystemUI 进程内完成。

### 重要程度
中

### 建议研究方向
- 验证 Android 16 ProgressStyle 渲染是否不回掉给 App

### 关联章节
- 9.6

### 外部 review 来源
- Gemini 外部 review (2026-04-25-15-9.README-external-review.md)
## [2026-04-26] 1.1 1.1 — 知识盲区

### 盲区描述
JNI Microbenchmarks

### 重要程度
高

### 建议研究方向
挖掘 `art/benchmark/jni_perf` 中的官方测试数据，以量化 JNI 开销

### 外部 review 来源
- 2026-04-25-15-1.1-external-review.md

## [2026-04-26] 1.1 1.1 — 知识盲区

### 盲区描述
Android 各大子系统从 ashmem 完全迁移到 memfd_create 的具体内核级表现和时间线。

### 重要程度
中

### 建议研究方向
AOSP `system/core/libcutils/ashmem-dev.cpp` 历史演进。

### 外部 review 来源
- 2026-04-25-15-1.1-external-review.md

## [2026-04-26] 1.10 1.10 ContentProvider 性能与优化 — 知识盲区

### 盲区描述
ContentProvider Client 缓存机制

### 重要程度
中

### 建议研究方向
研究 `ContentProviderClient` 在频繁调用时的缓存复用策略，以及如何正确 `release()` 避免泄漏。

### 外部 review 来源
- 2026-04-25-15-1.10-external-review.md

## [2026-04-26] 1.10 1.10 ContentProvider 性能与优化 — 知识盲区

### 盲区描述
多次调用场景下 `ContentProviderClient` 的连接保活机制。

### 重要程度
中

### 建议研究方向
AOSP `ContentResolver.acquireContentProviderClient()` 底层实现。

### 外部 review 来源
- 2026-04-25-15-1.10-external-review.md

## [2026-04-26] 1.11 1.11 Zygote 机制与启动性能优化 — 知识盲区

### 盲区描述
USAP Pool 在现代 Android 系统上的启用率

### 重要程度
低

### 建议研究方向
调查 Android 14+ 实际量产设备中，OEM 是否默认开启 USAP Pool，以及其对内存水位的实际影响。

### 外部 review 来源
- 2026-04-25-15-1.11-external-review.md

## [2026-04-26] 1.11 1.11 Zygote 机制与启动性能优化 — 知识盲区

### 盲区描述
USAP Pool 的实际启用现状。

### 重要程度
低

### 建议研究方向
验证各家 OEM 默认的 USAP 开启策略。

### 外部 review 来源
- 2026-04-25-15-1.11-external-review.md

## [2026-04-26] 1.12 1.12 AutoFDO 反馈导向编译优化 — 知识盲区

### 盲区描述
GKI 模块（GKI modules）的独立 AutoFDO profile 管理

### 重要程度
中

### 建议研究方向
除了 `vmlinux` 的全局 profile，单独加载的 KO（Kernel Object）如何管理自己的 `.afdo` 并在 DDK 中构建。

### 外部 review 来源
- 2026-04-25-15-1.12-external-review.md

## [2026-04-26] 1.12 1.12 AutoFDO 反馈导向编译优化 — 知识盲区

### 盲区描述
Kernel modules (KO) 的独立 AutoFDO 配置。

### 重要程度
中

### 建议研究方向
研究 DDK (Device Driver Kit) 文档，确认是否支持为每个 ko 文件独立注入 afdo profile。

### 外部 review 来源
- 2026-04-25-15-1.12-external-review.md

## [2026-04-26] 1.13 1.13 — 知识盲区

### 盲区描述
DeliQueue 在 Android 17 正式版的最终表现

### 重要程度
中

### 建议研究方向
持续追踪最终 AOSP 释放的 17 分支代码

### 外部 review 来源
- 2026-04-25-15-1.13-external-review.md

## [2026-04-26] 1.14 1.14 — 知识盲区

### 盲区描述
Android 17 新版 Bionic 对 mutex 的优化

### 重要程度
低

### 建议研究方向
检查 Bionic 源码

### 外部 review 来源
- 2026-04-25-15-1.14-external-review.md

## [2026-04-26] 1.15 1.15 — 知识盲区

### 盲区描述
Android 17 是否对 CriticalNative 增加了新的基础类型支持

### 重要程度
低

### 建议研究方向
检查 ART 源码

### 外部 review 来源
- 2026-04-25-15-1.15-external-review.md

## [2026-04-26] 1.16 1.16 — 知识盲区

### 盲区描述
AAudio offloaded playback 最终 API 形态

### 重要程度
高

### 建议研究方向
Android 17 最终 SDK 验证

### 外部 review 来源
- 2026-04-25-15-1.16-external-review.md

## [2026-04-26] 1.17 1.17 — 知识盲区

### 盲区描述
Android 17 中 Rust HAL 带来的 IPC 行为差异

### 重要程度
中

### 建议研究方向
研究 Rust AIDL binding

### 外部 review 来源
- 2026-04-25-15-1.17-external-review.md

## [2026-04-26] 1.2 1.2 — 知识盲区

### 盲区描述
Cloud Profiles 性能指标

### 重要程度
中

### 建议研究方向
收集官方针对 Cloud Profiles 对冷启动时间改善的量化实验报告

### 外部 review 来源
- 2026-04-25-15-1.2-external-review.md

## [2026-04-26] 1.2 1.2 — 知识盲区

### 盲区描述
dm-verity 验证在现代 Android 内核（GKI 5.15+）中带来的块读取验证开销确切毫秒级别数据。

### 重要程度
低

### 建议研究方向
Perfetto boot trace 中的 dm-verity 耗时分析。

### 外部 review 来源
- 2026-04-25-15-1.2-external-review.md

## [2026-04-26] 1.3 1.3 — 知识盲区

### 盲区描述
SDK Sandbox 进程开销

### 重要程度
中

### 建议研究方向
实际测量加载包含复杂广告 SDK 的 App 时，`_sdk_sandbox` 进程产生的 IPC 延迟和内存开销

### 外部 review 来源
- 2026-04-25-15-1.3-external-review.md

## [2026-04-26] 1.3 1.3 — 知识盲区

### 盲区描述
CachedAppOptimizer 的 `enableFreezer` 在陷入内核后，cgroup v2 contro

### 重要程度
低

### 建议研究方向
在 Perfetto 中深究 `android_freezer_events`。

### 外部 review 来源
- 2026-04-25-15-1.3-external-review.md

## [2026-04-26] 1.4 1.4 — 知识盲区

### 盲区描述
Android 14 Lazy Async 反压机制

### 重要程度
中

### 建议研究方向
阅读 Android 14/15 源码中关于 Binder 驱动队列管理和反压控制机制（`binder.c` 和 `IPCThreadState.cpp`）

### 外部 review 来源
- 2026-04-25-15-1.4-external-review.md

## [2026-04-26] 1.4 1.4 — 知识盲区

### 盲区描述
Android 14 中 Binder oneway 的 Lazy Async 导致客户端阻塞的底层条件。

### 重要程度
中

### 建议研究方向
梳理 `binder.c` 针对异步事务队列积压时的阻塞返回逻辑。

### 外部 review 来源
- 2026-04-25-15-1.4-external-review.md

## [2026-04-26] 1.5 1.5 — 知识盲区

### 盲区描述
无锁 MessageQueue 实现细节

### 重要程度
中

### 建议研究方向
详细分析 `android/os/ConcurrentMessageQueue` 在 AOSP 16 中的性能对比表现

### 外部 review 来源
- 2026-04-25-15-1.5-external-review.md

## [2026-04-26] 1.5 1.5 — 知识盲区

### 盲区描述
无锁消息队列对 UI 线程卡顿率的微观改善。

### 重要程度
中

### 建议研究方向
关联阅读 1.13 节并做 benchmark。

### 外部 review 来源
- 2026-04-25-15-1.5-external-review.md

## [2026-04-26] 1.6 1.6 — 知识盲区

### 盲区描述
Android 16 System-triggered Profiling

### 重要程度
高

### 建议研究方向
研究 `frameworks/base/core/java/android/os/ProfilingManager.java` 或对应系统服务的内部工作原理

### 外部 review 来源
- 2026-04-25-15-1.6-external-review.md

## [2026-04-26] 1.6 1.6 — 知识盲区

### 盲区描述
Android 16 性能监控 API（system-triggered profiling）的系统调用层实现路径。

### 重要程度
高

### 建议研究方向
剖析 framework 中的 Profiling 服务与 Perfetto 数据源的交互。

### 外部 review 来源
- 2026-04-25-15-1.6-external-review.md

## [2026-04-26] 1.7 1.7 ART 编译管线与 dex2oat 优化 — 知识盲区

### 盲区描述
Android 16 Cloud Compilation 的端侧落地实现

### 重要程度
中

### 建议研究方向
跟踪 `system/update_engine` 或 Play Store 相关的 OTA / staged install 机制如何消费云端 Profile。

### 外部 review 来源
- 2026-04-25-15-1.7-external-review.md

## [2026-04-26] 1.7 1.7 ART 编译管线与 dex2oat 优化 — 知识盲区

### 盲区描述
Cloud Compilation 在端侧的精确落地代码路径及兜底策略。

### 重要程度
中

### 建议研究方向
关注 `artd` 和 PackageInstaller 如何处理来自 Play Store 的额外编译产物。

### 外部 review 来源
- 2026-04-25-15-1.7-external-review.md

## [2026-04-26] 1.8 1.8 Activity Manager Service 与性能分析 — 知识盲区

### 盲区描述
Phantom Process Killer 细节

### 重要程度
低

### 建议研究方向
研究 Android 12+ 中 `ActivityManagerService` 如何具体监控并限制 `Runtime.exec()` 派生的子进程（32个上限的具体实现逻辑）。

### 外部 review 来源
- 2026-04-25-15-1.8-external-review.md

## [2026-04-26] 1.8 1.8 Activity Manager Service 与性能分析 — 知识盲区

### 盲区描述
Phantom Process Killer 的源码级执行机制。

### 重要程度
低

### 建议研究方向
结合 `PhantomProcessList.java` 分析其与 lmkd 的联动。

### 外部 review 来源
- 2026-04-25-15-1.8-external-review.md

## [2026-04-26] 1.9 1.9 Package Manager Service 与应用安装性能 — 知识盲区

### 盲区描述
VAB (Virtual A/B) 更新期间的后台 I/O 影响

### 重要程度
中

### 建议研究方向
研究系统在进行 Seamless Update 时，后台 block device 的合并操作对前台 I/O 性能的挤压。

### 外部 review 来源
- 2026-04-25-15-1.9-external-review.md

## [2026-04-26] 1.9 1.9 Package Manager Service 与应用安装性能 — 知识盲区

### 盲区描述
Virtual A/B 机制下 snapshot 合并对系统存储性能的隐性影响。

### 重要程度
中

### 建议研究方向
研究 `snapuserd` 进程的 I/O 行为及其对前台应用加载速度的干扰。

### 外部 review 来源
- 2026-04-25-15-1.9-external-review.md

## [2026-04-26] 2.1 2.1 — 知识盲区

### 盲区描述
Android 16 Host Image Copy 对纹理上传的具体影响。

### 重要程度
中

### 建议研究方向
结合 AOSP 最新源码和 OEM 文档深入研究

### 外部 review 来源
- 2026-04-25-15-2.1-external-review.md

## [2026-04-26] 2.10 2.10 — 知识盲区

### 盲区描述
Vulkan 多线程命令缓冲区构建在 Android UI 渲染中的实际应用案例。

### 重要程度
中

### 建议研究方向
结合 AOSP 最新源码和 OEM 文档深入研究

### 外部 review 来源
- 2026-04-25-15-2.10-external-review.md

## [2026-04-26] 2.11  — 知识盲区

### 盲区描述
Impeller 的 PSO 预编译文件存放路径

### 重要程度
中

### 建议研究方向
调查 Android 上的缓存路径（通常在 `/data/user/0/.../app_flutter/impeller_cache`）

### 外部 review 来源
- 2026-04-25-15-2.11-external-review.md

## [2026-04-26] 2.11  — 知识盲区

### 盲区描述
Android 14+ 对 PlatformView 的 HardwareRenderer 限制绕过

### 重要程度
高

### 建议研究方向
调查 Flutter 3.24 对 Android 14 渲染异常的 Workaround

### 外部 review 来源
- 2026-04-25-15-2.11-external-review.md

## [2026-04-26] 2.11  — 知识盲区

### 盲区描述
跨线程同步屏障（Synchronous SurfaceView）

### 重要程度
低

### 建议研究方向
调查 Flutter 如何保证 Raster 帧和 PlatformView 帧在 SurfaceFlinger 中的同步

### 外部 review 来源
- 2026-04-25-15-2.11-external-review.md

## [2026-04-26] 2.12 `2.12 Window Manager Service 与窗口管理` — 知识盲区

### 盲区描述
**Shared Memory Insets**

### 重要程度
中

### 建议研究方向
Android 15 后 Insets 是否存在通过共享内存减少跨进程通信的优化。

### 外部 review 来源
- 2026-04-25-15-2.12-external-review.md

## [2026-04-26] 2.12 `2.12 Window Manager Service 与窗口管理` — 知识盲区

### 盲区描述
**WMS 锁拆分现状**

### 重要程度
高

### 建议研究方向
`mGlobalLock` 在 Android 16+ 中是否有进一步拆分（如针对 Display 或 Task 级别）的计划。

### 外部 review 来源
- 2026-04-25-15-2.12-external-review.md

## [2026-04-26] 2.12 `2.12 Window Manager Service 与窗口管理` — 知识盲区

### 盲区描述
**BLASTBufferQueue 资源回收**

### 重要程度
中

### 建议研究方向
App 侧 `updateBlastSurfaceIfNeeded` 触发时，旧 Buffer 的释放时机对内存瞬时峰值的影响。

### 外部 review 来源
- 2026-04-25-15-2.12-external-review.md

## [2026-04-26] 2.13  — 知识盲区

### 盲区描述
Gralloc 分配时机

### 重要程度
中

### 建议研究方向
结合 `dequeueBuffer` 触发的 `GraphicBufferAllocator::allocate` 链路，解释为什么第一次渲染特别慢。

### 外部 review 来源
- 2026-04-25-15-2.13-external-review.md

## [2026-04-26] 2.13  — 知识盲区

### 盲区描述
BufferLayerConsumer 差异

### 重要程度
低

### 建议研究方向
BLAST 之后，SF 侧不再直接持有 BufferQueueConsumer，而是通过 Transaction 接收 Buffer，需理清 SF 侧对应的映射组件。

### 外部 review 来源
- 2026-04-25-15-2.13-external-review.md

## [2026-04-26] 2.14 2.14 图形 API 演进与选择策略（OpenGL ES / Vulkan / ANGLE） — 知识盲区

### 盲区描述
WebView 独立后端选路

### 重要程度
高

### 建议研究方向
研究 `aw_main_delegate.cc` 中对 `use-vulkan` 标志位的判断逻辑

### 外部 review 来源
- 2026-04-25-15-2.14-external-review.md

## [2026-04-26] 2.14 2.14 图形 API 演进与选择策略（OpenGL ES / Vulkan / ANGLE） — 知识盲区

### 盲区描述
Host Image Copy 兼容性

### 重要程度
中

### 建议研究方向
调研 Android 16 之前版本对 `VK_EXT_host_image_copy` 的模拟支持情况

### 外部 review 来源
- 2026-04-25-15-2.14-external-review.md

## [2026-04-26] 2.14 2.14 图形 API 演进与选择策略（OpenGL ES / Vulkan / ANGLE） — 知识盲区

### 盲区描述
RenderThread 亲和性动态调整

### 重要程度
低

### 建议研究方向
调研 `libprocessgroup` 对 top-app 核心绑定的具体 cpuset 值

### 外部 review 来源
- 2026-04-25-15-2.14-external-review.md

## [2026-04-26] 2.14 2.14 图形 API 演进与选择策略（OpenGL ES / Vulkan / ANGLE） — 知识盲区

### 盲区描述
WebView 在 SkiaVulkan 模式下不受系统 ANGLE 策略影响。

### 重要程度
高

### 建议研究方向
完善 §2.9 中关于 WebView 渲染管线的描述。

### 外部 review 来源
- 2026-04-25-15-2.14-external-review.md

## [2026-04-26] 2.15 2.15 DMA-BUF、Gralloc 与跨进程图形内存共享 — 知识盲区

### 盲区描述
DMA-BUF Sync File vs Fence

### 重要程度
高

### 建议研究方向
DMA-BUF 本身的 `dma_fence` 机制与 Android Sync Fence 的映射关系，将在 2.16 深挖。

### 外部 review 来源
- 2026-04-25-15-2.15-external-review.md

## [2026-04-26] 2.15 2.15 DMA-BUF、Gralloc 与跨进程图形内存共享 — 知识盲区

### 盲区描述
Multi-planar Buffer 分配逻辑

### 重要程度
中

### 建议研究方向
调研 `BufferUsage.VIDEO_DECODER` 下 YV12/NV12 格式在现代 Gralloc 里的 fd 数量选择。

### 外部 review 来源
- 2026-04-25-15-2.15-external-review.md

## [2026-04-26] 2.16  — 知识盲区

### 盲区描述
Fence FD 传递的成本

### 重要程度
中

### 建议研究方向
跨进程传递 FD 时的引用计数变化与内核句柄开销。

### 外部 review 来源
- 2026-04-25-15-2.16-external-review.md

## [2026-04-26] 2.16  — 知识盲区

### 盲区描述
Vulkan Explicit Sync

### 重要程度
高

### 建议研究方向
Android 15+ 在 Vulkan 后端下如何跳过传统的 Fence 封装，实现更底层的同步。

### 外部 review 来源
- 2026-04-25-15-2.16-external-review.md

## [2026-04-26] 2.16  — 知识盲区

### 盲区描述
Fence 挂死（Hang）的内核恢复机制

### 重要程度
中

### 建议研究方向
驱动侧的 Fence Timeout 机制以及如何触发 GPU Reset。

### 外部 review 来源
- 2026-04-25-15-2.16-external-review.md

## [2026-04-26] 2.17  — 知识盲区

### 盲区描述
Swappy 与 Vulkan `VK_GOOGLE_display_timing` 的底层交互

### 重要程度
中

### 建议研究方向
深入研究该扩展在不同厂商 GPU 驱动上的实现差异

### 外部 review 来源
- 2026-04-25-15-2.17-external-review.md

## [2026-04-26] 2.17  — 知识盲区

### 盲区描述
Android 17 DeliQueue 对 native 侧 AChoreographer 的间接影响

### 重要程度
高

### 建议研究方向
确认 DeliQueue 是否仅优化 Java 侧 MessageQueue，还是对 NDK 侧的 `ALooper` 同样有提速

### 外部 review 来源
- 2026-04-25-15-2.17-external-review.md

## [2026-04-26] 2.18 `2.18 Adaptive Refresh Rate 与动态帧率控制` — 知识盲区

### 盲区描述
HAL 层的 ARR 实现

### 重要程度
中

### 建议研究方向
关注 `IComposerClient` 的 `setLayerGenericMetadata` 及其对 ARR 的传参。

### 外部 review 来源
- 2026-04-25-15-2.18-external-review.md

## [2026-04-26] 2.18 `2.18 Adaptive Refresh Rate 与动态帧率控制` — 知识盲区

### 盲区描述
对变帧率视频的支持

### 重要程度
低

### 建议研究方向
`Surface.setFrameRate` 的 `FRAME_RATE_COMPATIBILITY_FIXED_SOURCE` 在 ARR 模式下的具体降频策略。

### 外部 review 来源
- 2026-04-25-15-2.18-external-review.md

## [2026-04-26] 2.19  — 知识盲区

### 盲区描述
**Multi-display 刷新率异步切换**

### 重要程度
中

### 建议研究方向
当内屏 120Hz、外屏 60Hz 同时活跃时，SurfaceFlinger 的单线程合成瓶颈。

### 外部 review 来源
- 2026-04-25-15-2.19-external-review.md

## [2026-04-26] 2.19  — 知识盲区

### 盲区描述
**VRR (Variable Refresh Rate) 与 ARR 的细微差异**

### 重要程度
高

### 建议研究方向
硬件层 VRR 协议（如 QSync/FreeSync 转移动端）在 Display HAL 层的映射。

### 外部 review 来源
- 2026-04-25-15-2.19-external-review.md

## [2026-04-26] 2.19  — 知识盲区

### 盲区描述
**RenderEngine 缓存对切换的影响**

### 重要程度
低

### 建议研究方向
切换瞬间 GL context 是否会重置或导致缓存失效。

### 外部 review 来源
- 2026-04-25-15-2.19-external-review.md

## [2026-04-26] 2.2 2.2 — 知识盲区

### 盲区描述
Game Mode API 在真实设备上的实际降频表现差异。

### 重要程度
中

### 建议研究方向
结合 AOSP 最新源码和 OEM 文档深入研究

### 外部 review 来源
- 2026-04-25-15-2.2-external-review.md

## [2026-04-26] 2.20  — 知识盲区

### 盲区描述
多窗口下的 Input 路由延迟

### 重要程度
中

### 建议研究方向
关注 `InputDispatcher` 在分屏边界处的 ANR 风险

### 外部 review 来源
- 2026-04-25-15-2.20-external-review.md

## [2026-04-26] 2.20  — 知识盲区

### 盲区描述
窗口模糊（Blur）的渲染开销

### 重要程度
高

### 建议研究方向
Android 12+ 窗口模糊在多窗口下会极大增加 GPU 负载

### 外部 review 来源
- 2026-04-25-15-2.20-external-review.md

## [2026-04-26] 2.20  — 知识盲区

### 盲区描述
任务栏（Taskbar）的独立合成层

### 重要程度
低

### 建议研究方向
了解 `TaskbarDelegate` 与 SF 的交互

### 外部 review 来源
- 2026-04-25-15-2.20-external-review.md

## [2026-04-26] 2.3 2.3 — 知识盲区

### 盲区描述
HW_VSYNC 短暂开启的具体阈值与时长。

### 重要程度
中

### 建议研究方向
结合 AOSP 最新源码和 OEM 文档深入研究

### 外部 review 来源
- 2026-04-25-15-2.3-external-review.md

## [2026-04-26] 2.4 2.4 — 知识盲区

### 盲区描述
厂商对 Choreographer 回调的定制（如华为 VSync 注入）在最新系统的现状。

### 重要程度
中

### 建议研究方向
结合 AOSP 最新源码和 OEM 文档深入研究

### 外部 review 来源
- 2026-04-25-15-2.4-external-review.md

## [2026-04-26] 2.5 2.5 — 知识盲区

### 盲区描述
Deferred GPU Commands 的 Pipeline Flush 具体合并策略。

### 重要程度
中

### 建议研究方向
结合 AOSP 最新源码和 OEM 文档深入研究

### 外部 review 来源
- 2026-04-25-15-2.5-external-review.md

## [2026-04-26] 2.6 2.6 — 知识盲区

### 盲区描述
HWC HAL v3 接口在不同设备上的兼容性问题。

### 重要程度
中

### 建议研究方向
结合 AOSP 最新源码和 OEM 文档深入研究

### 外部 review 来源
- 2026-04-25-15-2.6-external-review.md

## [2026-04-26] 2.7 2.7 — 知识盲区

### 盲区描述
Compose 的 graphicsLayer 在 CompositingStrategy.ModulateAlpha 下的具体光栅化时机。

### 重要程度
中

### 建议研究方向
结合 AOSP 最新源码和 OEM 文档深入研究

### 外部 review 来源
- 2026-04-25-15-2.7-external-review.md

## [2026-04-26] 2.8 2.8 — 知识盲区

### 盲区描述
Compose 中 drawBehind 与过度绘制的实际减少量验证。

### 重要程度
中

### 建议研究方向
结合 AOSP 最新源码和 OEM 文档深入研究

### 外部 review 来源
- 2026-04-25-15-2.8-external-review.md

## [2026-04-26] 2.9 2.9 — 知识盲区

### 盲区描述
Frame Timeline 在不同 OEM ROM 上的实现一致性。

### 重要程度
中

### 建议研究方向
结合 AOSP 最新源码和 OEM 文档深入研究

### 外部 review 来源
- 2026-04-25-15-2.9-external-review.md

## [2026-04-26] 2.0 `src/part1-fundamentals/ch02-rendering/README.md` — 知识盲区

### 盲区描述
Skia Graphite 异步指令录制性能

### 重要程度
高

### 建议研究方向
研究 Android 17 中 Graphite 如何通过多线程降低录制开销。

### 外部 review 来源
- 2026-04-25-15-2.README-external-review.md

## [2026-04-26] 2.0 `src/part1-fundamentals/ch02-rendering/README.md` — 知识盲区

### 盲区描述
ARR 对游戏 Swappy 库的底层交互

### 重要程度
中

### 建议研究方向
验证 Android 15 后 ARR 如何与 Frame Pacing Library 协同工作。

### 外部 review 来源
- 2026-04-25-15-2.README-external-review.md

## [2026-04-26] 2.0 `src/part1-fundamentals/ch02-rendering/README.md` — 知识盲区

### 盲区描述
Android 17 硬件加速光线追踪 (Ray Query)

### 重要程度
低

### 建议研究方向
针对 2026 年高性能 SoC 的移动端游戏渲染新特性。

### 外部 review 来源
- 2026-04-25-15-2.README-external-review.md

## [2026-04-26] 3.1 `src/part1-fundamentals/ch03-input/01-input-dispatch.md` — 知识盲区

### 盲区描述
最新 Android 16/17 版本相关机制变化

### 重要程度
高

### 建议研究方向
调研最新 AOSP release notes

### 外部 review 来源
- 2026-04-25-15-3.1-external-review.md

## [2026-04-26] 3.1 `src/part1-fundamentals/ch03-input/01-input-dispatch.md` — 知识盲区

### 盲区描述
新版本实现差异

### 重要程度
高

### 建议研究方向
AOSP main 分支

### 外部 review 来源
- 2026-04-25-15-3.1-external-review.md

## [2026-04-26] 4.5 `05-app-memory-optimization.md` — 知识盲区

### 盲区描述
ART GC 触发与 onTrimMemory 之间的时序耦合关系

### 重要程度
高

### 建议研究方向
结合最新 Linux Kernel / ART 源码进行行为分析

### 外部 review 来源
- 2026-04-25-15-4.5-external-review.md

## [2026-04-26] 4.6 `06-memory-evolution.md` — 知识盲区

### 盲区描述
PSI 指标在不同内核版本下的计算差异及其对 LMKD 杀进程策略的影响

### 重要程度
高

### 建议研究方向
结合最新 Linux Kernel / ART 源码进行行为分析

### 外部 review 来源
- 2026-04-25-15-4.6-external-review.md

## [2026-04-26] 4.7 `07-16kb-page-size.md` — 知识盲区

### 盲区描述
JEMalloc/Scudo 在 16KB 页大小下的对齐碎片与内存占用开销增长规律

### 重要程度
高

### 建议研究方向
结合最新 Linux Kernel / ART 源码进行行为分析

### 外部 review 来源
- 2026-04-25-15-4.7-external-review.md

## [2026-04-26] 4.8 `08-art-generational-gc.md` — 知识盲区

### 盲区描述
Read Barrier 在 Generational CC 期间对运行期性能的具体指令集开销

### 重要程度
高

### 建议研究方向
结合最新 Linux Kernel / ART 源码进行行为分析

### 外部 review 来源
- 2026-04-25-15-4.8-external-review.md

## [2026-04-26] 5.1 `01-linux-scheduling.md` — 知识盲区

### 盲区描述
PELT (Per-Entity Load Tracking) 算法在任务负载骤增时的衰减曲线与响应延迟

### 重要程度
高

### 建议研究方向
结合最新 Linux Kernel / ART 源码进行行为分析

### 外部 review 来源
- 2026-04-25-15-5.1-external-review.md

## [2026-04-26] 5.2 `02-eas.md` — 知识盲区

### 盲区描述
当设备处于高温降频状态时，EAS 如何动态调整选核策略

### 重要程度
高

### 建议研究方向
结合最新 Linux Kernel / ART 源码进行行为分析

### 外部 review 来源
- 2026-04-25-15-5.2-external-review.md

## [2026-04-26] 5.3 `03-big-little.md` — 知识盲区

### 盲区描述
DynamIQ 架构中 L3 Cache 共享机制对跨簇调度的延迟降低程度

### 重要程度
高

### 建议研究方向
结合最新 Linux Kernel / ART 源码进行行为分析

### 外部 review 来源
- 2026-04-25-15-5.3-external-review.md

## [2026-04-26] 5.4 `04-dvfs.md` — 知识盲区

### 盲区描述
硬件调频 (如 Arm AMU) 相比软件 cpufreq 带来的延迟降低优势

### 重要程度
高

### 建议研究方向
结合最新 Linux Kernel / ART 源码进行行为分析

### 外部 review 来源
- 2026-04-25-15-5.4-external-review.md

## [2026-04-26] 5.5 `05-thermal.md` — 知识盲区

### 盲区描述
不同厂商的 thermal-engine 配置文件 (thermal-engine.conf) 对 CPU 节流 (throttling) 的具体档位策略

### 重要程度
高

### 建议研究方向
结合最新 Linux Kernel / ART 源码进行行为分析

### 外部 review 来源
- 2026-04-25-15-5.5-external-review.md

## [2026-04-26] 5.6 `06-android-power.md` — 知识盲区

### 盲区描述
Doze 模式下网络限制与 Alarms 对齐机制在 Doze Maintenance Window 中的集中释放逻辑

### 重要程度
高

### 建议研究方向
结合最新 Linux Kernel / ART 源码进行行为分析

### 外部 review 来源
- 2026-04-25-15-5.6-external-review.md

## [2026-04-26] 5.7 `07-cpu-evolution.md` — 知识盲区

### 盲区描述
大核 X 系列架构的乱序执行深度增加对分支预测失败惩罚的影响

### 重要程度
高

### 建议研究方向
结合最新 Linux Kernel / ART 源码进行行为分析

### 外部 review 来源
- 2026-04-25-15-5.7-external-review.md

## [2026-04-26] 2.0 `src/part1-fundamentals/ch02-rendering/README.md` — 知识盲区

### 盲区描述
Android 17 光线追踪加速 (Ray Query)

### 重要程度
低

### 建议研究方向
仅针对高性能游戏场景，总纲可作为锦上添花提及。

### 外部 review 来源
- 2026-04-26-10-ch02-rendering-overview-external-review.md

## [2026-04-26] 9.1/9.2 ANR 广播动态超时 — 知识盲区

### 盲区描述
Android 14+ BroadcastQueueModernImpl 的 soft timeout / hard timeout 机制还没有在 9.1 与 9.2 中完整展开。external-review 已命中 9.1 的 Modern Broadcast Queue 动态超时问题，本轮复核确认 9.1 仍保留固定 10s/60s 表述。

### 重要程度
高

### 建议研究方向
- 对照 `BroadcastQueueModernImpl.dispatchReceivers()`、`deliveryTimeoutSoftLocked()`、`ProcessRecord.getCpuDelayTime()`，补齐 CPU starvation 如何把 10s/60s 拉到 20s/120s。
- 对照 Android Developers ANR vitals 文档，说明 app startup 时间与 `goAsync()` 是否共享同一广播窗口。
- 明确 Android 13 及以下 `BroadcastQueue` 与 Android 14+ modern queue 的版本边界。

### 关联章节
9.1, 9.2

### 外部 review 来源
- logs/external-review/2026-04-25-part2-batch-review-summary.md

## [2026-04-26] 9.3 ANR Perfetto 诊断轨道 — 知识盲区

### 盲区描述
9.3 写到 Android 14 新增 `android.anr` track，但目前只复核到 AOSP 的 `AnrLatencyTracker` trace slice/counter 与 statsd `ANR_LATENCY_REPORTED`，尚未确认是否存在稳定命名的 Perfetto track 或 SQL 表。

### 重要程度
中

### 建议研究方向
- 使用 Android 14/15/16 真实 ANR trace，检查 Perfetto UI track 名、`slice` / `track` / `args` 表中 ANR 相关记录。
- 对照 Perfetto trace processor schema，确认是否存在 `android_anr` 标准表或仅为 ActivityManager trace slices。
- 若不存在稳定 track 名，把正文改为 `AnrLatencyTracker` / `ANR_LATENCY_REPORTED` 诊断观测点。

### 关联章节
9.3, 13.2, 13.9


## [2026-04-26] ch03 Input 事件处理 — 知识盲区

### 盲区描述
最新 Android 16/17 版本 Input 相关机制变化未覆盖。

### 重要程度
高

### 建议研究方向
- 调研最新 AOSP release notes 中 Input 子系统变更
- Android 14/15/16 中 InputDispatcher timeout 判定逻辑变化

### 关联章节
- ch03-input

### 外部 review 来源
- Gemini 外部 review

## [2026-04-26] ch04 内存管理 — 知识盲区

### 盲区描述
不同 OEM 厂商对 Kswapd 水位线调整对整体内存架构的冲击

### 重要程度
高

### 建议研究方向
- 结合最新 Linux Kernel / ART 源码进行行为分析
- OEM 差异化 lmkd 配置对比

### 关联章节
- ch04 内存管理、性能优化相关章节

### 外部 review 来源
- Gemini 外部 review

## [2026-04-26] ch05 CPU 调度与能耗管理 — 知识盲区

### 盲区描述
内核态调度策略与 Android Framework 层（如 AMS 的 ProcessState/OomAdj）如何联动

### 重要程度
高

### 建议研究方向
- ProcessList.java 中 setOomAdj 对 CPU cpuset 的影响
- kernel/sched/ 及 drivers/cpufreq/ 中 EAS 核心架构

### 关联章节
- ch05-cpu-power、内存管理、进程管理

### 外部 review 来源
- Gemini 外部 review

## [2026-04-26] ch06 存储 I/O — 知识盲区

### 盲区描述
SQLite 同步写 (fsync) 如何通过文件系统传递到块设备层并导致主线程 D 状态；F2FS GC 对性能抖动影响

### 重要程度
高

### 建议研究方向
- 结合 SQLite WAL 模式与 VFS 层交互过程分析
- AOSP 中 F2FS 挂载参数及内核端 f2fs 模块

### 关联章节
- ch06-storage、SQLite 性能优化、启动优化

### 外部 review 来源
- Gemini 外部 review

## [2026-04-26] 16.1 Google 官方优化 — 知识盲区

### 盲区描述
BLASTBufferQueue 与 WMS 的跨进程 Transaction 同步引擎（BLASTSyncEngine）机制未覆盖。

### 重要程度
高

### 建议研究方向
- 分析 BLASTSyncEngine 和 WindowContainerTransaction 的源码实现
- 梳理 WMS 如何收集多个应用/系统的 Transaction 并统一 apply

### 关联章节
- 16.1

### 外部 review 来源
- Gemini 外部 review (2026-04-25)

## [2026-04-26] 16.2 版本变更 — 知识盲区

### 盲区描述
CachedAppOptimizer 具体冻结/解冻策略及 cgroup v2 freezer 机制。

### 重要程度
中

### 建议研究方向
- 深入 CachedAppOptimizer.java 了解 freezer 机制
- 研究 Android 如何使用 cgroup 控制进程冻结
- 了解 binder 调用触发短暂 unfreeze 的机制

### 关联章节
- 16.2

### 外部 review 来源
- Gemini 外部 review (2026-04-25)

## [2026-04-26] 16.3 AOSP 编译与环境搭建 — 知识盲区

### 盲区描述
Dynamic Partitions 对 adb remount 的限制，scratch 分区从 super 动态分配机制。

### 重要程度
高

### 建议研究方向
- 梳理 OverlayFS 时 scratch 分区如何从 super 动态分配
- fastboot delete-logical-partition 等处理 scratch 空间的方法

### 关联章节
- 16.3

### 外部 review 来源
- Gemini 外部 review (2026-04-25)

## [2026-04-26] 16.4 Kernel 6.12 性能 — 知识盲区

### 盲区描述
sched_ext 实际 BPF 加载机制与调度器实现示例。

### 重要程度
低

### 建议研究方向
- 分析 tools/testing/selftests/sched_ext/ 中的 scx_simple
- 如何通过 BPF 工具链在 Android 上加载 sched_ext 策略

### 关联章节
- 16.4

### 外部 review 来源
- Gemini 外部 review (2026-04-25)

## [2026-04-26] 16.5 Android 17 API 37 性能变更 — 知识盲区

### 盲区描述
DeliQueue 与同步屏障（Sync Barriers）的兼容实现。

### 重要程度
高

### 建议研究方向
- 查阅 ConcurrentMessageQueue 对于 postSyncBarrier 的支持机制
- 研究基于 min-heap 和无锁栈的新队列如何高效识别并阻塞异步消息之前的同步消息

### 关联章节
- 16.5, Handler 消息机制章节

### 外部 review 来源
- Gemini 外部 review (2026-04-25)

## [2026-04-26] 17.1 OEM 优化通用思路 — 知识盲区

### 盲区描述
不同厂商对后台 Freezer 介入的超时时间和白名单控制逻辑。

### 重要程度
中

### 建议研究方向
- 扒取不同厂商设备的 /sys/fs/cgroup/uid_*/cgroup.freeze 写入逻辑和时机
- 抓取不同厂商设备的 dumpsys activity 和 logcat 日志做对比

### 关联章节
- 17.1

### 外部 review 来源
- Gemini 外部 review (2026-04-25)

## [2026-04-26] 17.2 SoC 平台差异 — 知识盲区

### 盲区描述
联发科全大核架构的 EAS 参数细节，以及不同 SoC 的 NPU 调度对内存带宽的抢占。

### 重要程度
高

### 建议研究方向
- 寻找开源内核中 MTK 调度器特定参数（sched_energy_aware 行为调整）
- 使用 PMU 计数器对比开启和关闭 AI 功能时的内存带宽消耗

### 关联章节
- 17.2

### 外部 review 来源
- Gemini 外部 review (2026-04-25)

## [2026-04-26] 17.3 行业案例 — 知识盲区

### 盲区描述
不同 OEM 对 ADPF Hint 的实际响应调度逻辑差异。

### 重要程度
高

### 建议研究方向
- 测量调用 reportActualWorkDuration 到 CPU 频率实际拉高之间的时间延迟
- 在多台设备上对比 ADPF 生效时的 CPU 频率与调度器状态

### 关联章节
- 17.3

### 外部 review 来源
- Gemini 外部 review (2026-04-25)


## [2026-04-26] 2.6 SurfaceFlinger 与合成 — BLAST/HWC 现代合成路径

### 盲区描述
BLASTBufferQueue 的 transaction 合并机制、HWC2/HWC3 validate/present 协商路径、以及 Android 15 ARR 对 SurfaceFlinger Scheduler 的影响需要合并成一张版本化源码图。external-review 已命中 BLAST transaction 合并不足。

### 重要程度
高

### 建议研究方向
- `frameworks/native/libs/gui/BLASTBufferQueue.cpp`：`onFrameAvailable()`、`acquireNextBufferLocked()`、`Transaction::setBuffer()`
- `frameworks/native/services/surfaceflinger/`：`commit()`、`composite()`、CompositionEngine 与 HWC HAL 调用点
- AIDL `android.hardware.graphics.composer3` 与 HIDL composer@2.x 的 validate/present 差异

### 关联章节
2.6, 2.13, 2.16, 2.18, 2.19

## [2026-04-26] 3.1 Input 事件分发全流程 — InputClassifier/InputProcessor 与窗口信息版本边界

### 盲区描述
Android 12/13 的 InputClassifier、Android 14+ 的 InputProcessor，以及 Android 12 setInputWindows 与 Android 13+ WindowInfosListener 的切换需要补成版本矩阵。

### 重要程度
高

### 建议研究方向
- `frameworks/native/services/inputflinger/Android.bp` 对比 Android 12-16
- `InputDispatcher.cpp` 中 `setInputWindows()`、`DispatcherWindowListener`、`addWindowInfosListener()` 的版本差异
- 普通触摸、palm rejection、stylus 场景在 Trace 中的可观察点

### 关联章节
3.1, 9.1, 13.8

## [2026-04-26] 4.4 Low Memory Killer — lmkd/minfree/CachedAppOptimizer 版本矩阵

### 盲区描述
旧 LMK minfree/adj 写入链、userspace lmkd 引入时间、PSI 默认路径、CachedAppOptimizer/Freezer 默认策略变化需要按 Android 8.1-16 重建版本矩阵。

### 重要程度
高

### 建议研究方向
- `ProcessList.java`：`updateOomLevels()`、LMK_TARGET socket、oom_score_adj 常量
- `system/memory/lmkd/lmkd.cpp`：PSI、thrashing、reaper、low-RAM 分支
- `CachedAppOptimizer.java`：Android 11-16 `DEFAULT_FREEZER_DEBOUNCE_TIMEOUT` 与 `Process.setProcessFrozen()`

### 关联章节
1.3, 4.1, 4.2, 10.4


## [2026-04-27] 2.9 渲染机制的版本演进 — ANGLE/Vulkan 分阶段切换知识盲区

### 盲区描述
Android 16/17 中 OpenGL ES → ANGLE → Vulkan 的启用策略没有形成源码级决策链。当前章节容易被读成“Android 16 上所有 GLES App 自动走 ANGLE 并获得优化”，但实际还涉及设备默认、开发者选项、应用名单、OEM 覆盖、ANGLE package/driver 选择与后续 Android 17 扩展范围。external-review 已命中 ANGLE 状态机转换开销缺失。

### 重要程度
高

### 建议研究方向
- 复核 `frameworks/base/core/java/android/os/GraphicsEnvironment.java` 中 ANGLE 选择逻辑，以及 settings / package / rules 的优先级。
- 对照 source.android.com / developer.android.com 的 Android Vulkan / ANGLE roadmap，拆出 Android 15、16、17 的分阶段边界。
- 补 GLES → ANGLE → Vulkan 后在 Perfetto 中可观察的线程、GPU queue、fence/semaphore、driver slice 变化。

### 关联章节
2.9、2.14、18.11

## [2026-04-27] 4.7 16KB Page Size 与 Android 性能 — 知识盲区

### 盲区描述
16KB app compat mode 的真实副作用需要按 AOSP 分支复核。当前正文把 compat mode 写成“禁用 RELRO”，但 AOSP main 的 linker_phdr.cpp 仍存在 GNU RELRO mprotect 路径；需要区分兼容加载、segment padding/page-size migration、RELRO 保护、RELRO sharing 以及安全提示之间的边界。

### 重要程度
高

### 建议研究方向
- 对比 AOSP main、android-15、android-16 分支的 `bionic/linker/linker_phdr.cpp`：`should_use_16kib_app_compat_`、`CompatMapSegment()`、`phdr_table_protect_gnu_relro()`、`phdr_table_protect_gnu_relro_16kib_compat()`。
- 查官方 16KB compat/backcompat 文档，确认 `android:pageSizeCompat`、`bionic.linker.16kb.app_compat.enabled`、包管理器开关的 API level / SDK 暴露边界。
- 如需写安全代价，必须区分“RELRO 不生效”“RELRO sharing 不生效”“临时 RW 映射”“用户/开发者兼容模式警告”。

### 关联章节
- 4.7
- 14.13


## [2026-04-27] 19.0 第 19 章：APM 工具与性能监控生态 — 知识盲区

### 盲区描述
Ch19 README 和 SUMMARY 未覆盖实际存在的 19.23 网络 APM、19.24 Crash/ANR 捕获、19.25 功耗/热治理、19.26 Hybrid APM、19.27 APM 客户端架构。目录缺失会让这些 APM 关键领域从章节导航中消失，也会影响后续交叉引用。

### 重要程度
高

### 建议研究方向
- 核对 19.23-19.27 的章节状态、正文完整度和一手资料锚点。
- 为网络 APM、Crash/ANR 捕获、功耗热治理、Hybrid APM、客户端架构分别补齐官方/API/源码资料索引。
- 同步 README、SUMMARY 和 19.21/19.22 标题口径。

### 关联章节
19.0, 19.23, 19.24, 19.25, 19.26, 19.27


## [2026-04-27] 14.9 Android Camera 性能与 Perfetto 分析 — CamX/CHI Trace 映射盲区

### 盲区描述
external-review 已命中 Qualcomm CamX/CHI 观察点。本轮复核发现章节仍缺少 CamX/CHI pipeline node、CHI override、Preview/JPEG/ISP stage 与 Perfetto slice 的对应关系；现有内容只列出线程名和 requestStreamBuffers 口径，无法指导读者把 vendor slice 映射回 HAL3 request。

### 重要程度
高

### 建议研究方向
- 收集 Qualcomm CamX/CHI trace 中常见线程、node/stage、request id 命名。
- 建立 CamX/CHI node 到 HAL3 CaptureRequest / Stream / Buffer 的映射方法。
- 补充 YUV dump、vendor camera provider log、Perfetto slice 三者互证路径。

### 关联章节
- 14.9
- 18.14


## [2026-04-27] 16.4 Android 17 + Kernel 6.12 系统级性能优化 — 知识盲区

### 盲区描述
16.4 仍缺少 Android 17/API37 平台特性与 `android16-6.12` ACK/GKI 分支之间的明确边界。external-review 已命中 16.4 对 Android 17 + Kernel 6.12 的源码锚点不足；本轮复核进一步确认 EEVDF 版本表与 android15-6.6 源码不一致，DeliQueue 与 io_uring 的 Android 落地链也缺少一手源码证据。

### 重要程度
高

### 建议研究方向
- 核对 `android15-6.6`、`android16-6.12`、后续 Android 17/API37 tag 中 `kernel/sched/fair.c`、`kernel/sched/ext.c`、GKI config 的差异，重写 EEVDF/sched_ext 版本边界。
- 为 DeliQueue 定位准确源码路径、commit、启用条件和性能数据来源；无法定位时从定论改为待验证。
- 拆分 io_uring 内核能力、bionic/liburing 暴露、Cronet/SQLite/OkHttp 是否实际接入三层证据。

### 关联章节
16.4, 16.5, 5.1, 5.7, 1.13, 6.3


## [2026-04-27] 7.4 典型场景分析 — 知识盲区

### 盲区描述
Recents / 多任务缩略图链路的源码锚点不足。当前正文只写到 `TaskSnapshotController → TaskSnapshotPersister → ThumbnailData`，且把 `HardwareBuffer` 路径描述成“解码和上传纹理”。AOSP main 中 `TaskSnapshot` 持有 `HardwareBuffer`，`frameworks/base/packages/SystemUI/shared/src/com/android/systemui/shared/recents/model/ThumbnailData.kt` 通过 `Bitmap.wrapHardwareBuffer(buffer, colorSpace)` 包装。

### 重要程度
高

### 建议研究方向
- 核对 WMS `TaskSnapshotController`、`TaskSnapshotCache`、`TaskSnapshotPersister` 到 Recents/Launcher 的调用边界。
- 补齐 `android.window.TaskSnapshot` 字段、`ThumbnailData.fromSnapshot()` 与 `Bitmap.wrapHardwareBuffer()` 的源码锚点。
- 区分 HardwareBuffer 包装、GPU 采样/合成、普通图片 decode 三类成本，避免把 Recents 缩略图误写成图片解码问题。

### 关联章节
- 7.4
- 8.4
- 18.6

## [2026-04-27] 13 第13章 Perfetto — 知识盲区

### 盲区描述
现代架构对齐不足：Mainline APEX演进和Android 16+ UprobeStats/ProfilingManager的集成点覆盖较浅

### 重要程度
高

### 建议研究方向
- Android 12+ Mainline APEX演进与集成点；Android 16+ UprobeStats/ProfilingManager机制；perfetto::DataSource自定义实现；分布式处理方案Bigtrace；Perfetto内部源码路径同步

### 关联章节
13.1、13.2、13.3、13.4、13.5、13.6、13.7、13.8、13.9、13.10

### 外部review来源
Gemini外部review - 2026-04-25-13-13-batch-review-summary.md

---

## [2026-04-27] 10 第10章 内存性能优化 — 知识盲区

### 盲区描述
Android 15/16版本演进覆盖不足：指标基线重构、分析工具代差、显存计量闭环

### 重要程度
高

### 建议研究方向
- Android 15的16KB页面机制对PSS/RSS的影响；Android 16的ProfilingManager范式转移；Android 16显存计量闭环机制；AIDL IMemtrack系统级GPU内存监控；内存性能基线重构策略

### 关联章节
10.1、10.2、10.3、10.4

### 外部review来源
Gemini外部review - 2026-04-25-15-10-batch-review-summary.md

---


## [2026-04-28] 1.1 Android 分层架构 — 知识盲区

### 盲区描述
VNDK-less 后的库冗余处理机制未覆盖；Trunk Stable 开发模式（Android 16 Baklava）对 AOSP 稳定性的影响未梳理；16KB 兼容模式下如何运行 4KB 对齐旧版应用未说明。

### 重要程度
高

### 建议研究方向
- HAL APEX 如何打包依赖库以替代系统 VNDK
- Android 16 (Baklava) 的 Trunk Stable 开发模式变动
- 16KB 内核上运行 4KB 对齐旧版应用的兼容机制

### 关联章节
- 1.1

### 外部 review 来源
- Gemini 外部 review (2026-04-28)

## [2026-04-28] 1.2 系统启动全流程 — 知识盲区

### 盲区描述
GBL (Generic Bootloader) 标准化计时方案未研究；Asynchronous Probing 内核异步探测机制细节不足；Cloud Compilation 预编译产物下发完整流程待补。

### 重要程度
高

### 建议研究方向
- GBL 如何标准化开机计时
- 内核异步探测机制实现细节
- 预编译产物直接下发流程

### 关联章节
- 1.2

### 外部 review 来源
- Gemini 外部 review (2026-04-28)

## [2026-04-28] 1.3 进程模型与生命周期管理 — 知识盲区

### 盲区描述
ADJ 50 (PERCEPTIBLE_RECENT_FOREGROUND_APP_ADJ) 的宽限期时长定义机制未研究；AVF 虚拟机内部与宿主的 I/O 性能差异未评估。

### 重要程度
高

### 建议研究方向
- 系统如何定义 ADJ 50 的 RECENT 判定标准与宽限期时长
- AVF pVM 内部与宿主的 I/O 性能差异

### 关联章节
- 1.3

### 外部 review 来源
- Gemini 外部 review (2026-04-28)

## [2026-04-28] 1.1 Android 分层架构 — 知识盲区

- VNDK-less 后的库冗余处理 | 重要程度: 高 | 研究方向: HAL APEX 如何打包依赖库以替代系统 VNDK
- Trunk Stable 开发模式 | 重要程度: 中 | 研究方向: Android 16 (Baklava) 的开发模式变动对 AOSP 稳定性的影响
- 16KB 兼容模式 (Android 16) | 重要程度: 高 | 研究方向: 如何在 16KB 内核上运行 4KB 对齐的旧版应用

**来源**: Gemini 外部 review (2026-04-28-15-ch01-01-layered-architecture-external-review.md)

## [2026-04-28] 1.2 系统启动全流程 — 知识盲区

- GBL (Generic Bootloader) | 重要程度: 中 | 研究方向: 如何标准化开机计时
- Asynchronous Probing | 重要程度: 高 | 研究方向: 内核异步探测机制
- Cloud Compilation | 重要程度: 高 | 研究方向: 预编译产物直接下发流程

**来源**: Gemini 外部 review (2026-04-28-15-ch01-02-boot-process-external-review.md)

## [2026-04-28] 1.3 进程模型与生命周期管理 — 知识盲区

- ADJ 50 宽限期时长 | 重要程度: 高 | 研究方向: 系统如何定义“RECENT”
- AVF 性能开销 | 重要程度: 中 | 研究方向: 虚拟机内部与宿主的 I/O 差异

**来源**: Gemini 外部 review (2026-04-28-15-ch01-03-process-model-external-review.md)

## [2026-04-28] 1.4 Binder IPC 机制与性能影响 — 知识盲区

- FROZEN_CALLEE_POLICY_DROP | 重要程度: 高 | 研究方向: 系统服务如何利用该策略降低后台负载
- 16KB 页面的 mmap 对齐 | 重要程度: 中 | 研究方向: ProcessState.cpp 中的动态页大小适配

**来源**: Gemini 外部 review (2026-04-28-15-ch01-04-binder-external-review.md)

## [2026-04-28] 1.5 线程模型 — 知识盲区

- ADPF 核心迁移阈值 | 重要程度: 高 | 研究方向: 动态调度的触发逻辑
- DeliQueue 排序成本 | 重要程度: 中 | 研究方向: 消息积压时的 CPU 消耗

**来源**: Gemini 外部 review (2026-04-28-15-ch01-05-threading-model-external-review.md)

## [2026-04-28] 1.6 Android 版本演进中的架构变化 — 知识盲区

- Trace 脱敏机制 | 重要程度: 中 | 研究方向: ProfilingService 如何保护用户隐私
- HAL APEX 内存开销 | 重要程度: 高 | 研究方向: 重复库对 PSS 的累积影响

**来源**: Gemini 外部 review (2026-04-28-15-ch01-06-version-evolution-external-review.md)

## [2026-04-28] 1.7 ART 编译管线与 dex2oat 优化 — 知识盲区

- SDM 格式安全性 | 重要程度: 中 | 研究方向: 签名验证流程
- 强制不可变性收益 | 重要程度: 高 | 研究方向: 对 P90 启动耗时的真实贡献

**来源**: Gemini 外部 review (2026-04-28-15-ch01-07-art-compilation-external-review.md)

## [2026-04-28] 1.8 Activity Manager Service 与性能分析 — 知识盲区

- 广播异步处理超时 | 重要程度: 中 | 研究方向: 进程队列下的弹性时长计算
- ADJ 225 触发点 | 重要程度: 高 | 研究方向: 系统绑定的优先级分级

**来源**: Gemini 外部 review (2026-04-28-15-ch01-08-activity-manager-external-review.md)

## [2026-04-28] 1.9 Package Manager Service 与应用安装性能 — 知识盲区

- 快照重建开销 | 重要程度: 中 | 研究方向: 高频写入时的快照失效代价
- v4.1 签名 I/O 成本 | 重要程度: 低 | 研究方向: IncFS 块校验对闪存带宽的占用

**来源**: Gemini 外部 review (2026-04-28-15-ch01-09-package-manager-external-review.md)

## [2026-04-28] 1.10 ContentProvider 性能与优化 — 知识盲区

- MIME 类型异步查询埋点 | 重要程度: 中 | 研究方向: Android 16 内部新 Trace 标签
- 独立进程 CP 的页碎片 | 重要程度: 低 | 研究方向: 16KB 页大小对极小 Window 的内存浪费

**来源**: Gemini 外部 review (2026-04-28-15-ch01-10-content-provider-external-review.md)

## [2026-04-28] 1.11 Zygote 机制与启动性能优化 — 知识盲区

- 16KB 页下的 COW 颗粒度 | 重要程度: 中 | 研究方向: 单次复制 16KB 对 RAM 的微观影响
- Vulkan 预热与多核心联动 | 重要程度: 低 | 研究方向: 预热阶段是否占用非主核心 CPU

**来源**: Gemini 外部 review (2026-04-28-15-ch01-11-zygote-startup-external-review.md)

## [2026-04-28] 1.12 AutoFDO 反馈导向编译优化 — 知识盲区

- Propeller 布局优化 | 重要程度: 中 | 研究方向: AutoFDO 的下一代进阶技术
- 模块化 AFDO 签名 | 重要程度: 高 | 研究方向: GKI Module 与 Profile 的一致性校验

**来源**: Gemini 外部 review (2026-04-28-15-ch01-12-autofdo-optimization-external-review.md)

## [2026-04-28] 1.13 MessageQueue 机制与 DeliQueue 无锁优化 — 知识盲区

- TestLooperManager 生产可用性 | 重要程度: 高 | 研究方向: 它是如何通过 Instrumentation 挂载的
- MQ.Waiters 零值的含义 | 重要程度: 中 | 研究方向: 消费者线程饥饿或死锁的判断依据

**来源**: Gemini 外部 review (2026-04-28-15-ch01-13-messagequeue-deliqueue-external-review.md)

## [2026-04-28] 1.14 锁竞争与同步性能分析 — 知识盲区

- 标量替换 (Scalar Replacement) | 重要程度: 中 | 研究方向: 逃逸分析对锁消除之外的内存贡献
- Declarative Workload API | 重要程度: 高 | 研究方向: 调度器如何感知临界区优先级

**来源**: Gemini 外部 review (2026-04-28-15-ch01-14-lock-contention-external-review.md)

## [2026-04-28] 1.15 JNI/NDK 性能优化 — 知识盲区

- Critical JNI 注册限制 | 重要程度: 高 | 研究方向: 为什么静态注册在旧版本上更稳
- ARMv9 安全特性开销 | 重要程度: 低 | 研究方向: PAC/BTI 对 JNI 吞吐的微观影响

**来源**: Gemini 外部 review (2026-04-28-15-ch01-15-jni-ndk-performance-external-review.md)

## [2026-04-28] 1.16 Audio Pipeline 延迟与性能 — 知识盲区

- AIDL HAL 实时 Binder 调度 | 重要程度: 中 | 研究方向: 调度器如何保障 Binder 事务准时到达
- LC3plus 低延迟扩展 | 重要程度: 低 | 研究方向: 2026 高端硬件对 LC3plus 的采用率

**来源**: Gemini 外部 review (2026-04-28-15-ch01-16-audio-pipeline-performance-external-review.md)

## [2026-04-28] 1.17 IPC 全景：Android 进程间通信机制对比与性能选型 — 知识盲区

- VSOCK Datagram 性能 | 重要程度: 中 | 研究方向: 相比 Stream 模式在心跳包场景的收益
- memfd_file 安全审计 | 重要程度: 高 | 研究方向: Android 16 如何对匿名内存实施精细化控制

**来源**: Gemini 外部 review (2026-04-28-15-ch01-17-ipc-panorama-external-review.md)

## [2026-04-28] 2.1 Android 渲染架构全景 — 知识盲区

- 硬件切片调度 (Adreno 830) | 重要程度: 中 | 研究方向: GPU 分片如何优化 Android 16 的合成负载
- Headroom API 联动 | 重要程度: 高 | 研究方向: 渲染器如何根据热余量降级渲染质量

**来源**: Gemini 外部 review (2026-04-28-15-ch02-01-rendering-overview-external-review.md)


## [2026-04-28] 2.21 文字渲染性能
- **严重级别**：P1
- **位置**：引擎原理、优化实践及 API 演进小节
- **问题描述**：未反映 2026 年引擎提速、轴向缓存及排版 API 突破。
- **建议修正方向**：同步 HarfBuzz 10.x 收益并加入 Android 17 新特性说明。

### 9.4 可复用知识资产
- **性能锚点**：阿拉伯语塑形提速达 45% (Android 16+)。
- **核心 API**：`shiftDrawingOffsetForStartOverhang`。
- **技术结论**：2026 年的 Android 文本系统已实现从“基础显示”向“高品质动态排版”的完全跨越。

## 十一、落盘信息
- 已写入文件：`logs/external-review/2026-04-28-15-ch02-21-text-rendering-performance-external-review.md` — 知识盲区

### 动态字体回退延迟

**重要程度**：高

**建议研究方向**：Project Mainline 更新字体包时的系统级锁竞争

**关联章节**：2.21

**外部 review 来源**：2026-04-28-15-ch02-21-text-rendering-performance-external-review.md

### 垂直文本缓存失效率

**重要程度**：中

**建议研究方向**：启用 VERTICAL_TEXT_FLAG 后的 WordCache 命中率波动

**关联章节**：2.21

**外部 review 来源**：2026-04-28-15-ch02-21-text-rendering-performance-external-review.md


## [2026-04-28] 3.2 触控性能优化
- **严重级别**：P1
- **位置**：原理组成、预测机制及 16KB 适配小节
- **问题描述**：未反映 HCI 科学研究阈值及 Android 16 的 AI 预测模型。
- **建议修正方向**：同步 11ms 科学基准并引入 TFLite 预测模型实现。

### 9.4 可复用知识资产
- **性能锚点**：拖拽感知阈值 11ms。
- **核心机制**：TFLite MotionPredictor (NPU 推理)。
- **技术结论**：Android 16 标志着输入系统从“线性外推”跨入了“特征感知预测”的新阶段。

## 十一、落盘信息
- 已写入文件：`logs/external-review/2026-04-28-15-ch03-02-touch-performance-external-review.md` — 知识盲区

### 极坐标变换特征

**重要程度**：高

**建议研究方向**：预测模型如何通过角度/距离输入解耦屏幕方向

**关联章节**：3.2

**外部 review 来源**：2026-04-28-15-ch03-02-touch-performance-external-review.md

### 置信度动态过滤

**重要程度**：中

**建议研究方向**：预测点发生突跳时的系统自愈算法

**关联章节**：3.2

**外部 review 来源**：2026-04-28-15-ch03-02-touch-performance-external-review.md


## [2026-04-28] 3.3 手势导航与系统交互
- **严重级别**：P1
- **位置**：回调模型、演进趋势及 Monitor 原理小节
- **问题描述**：未反映 2026 年 AOT 强制拦截、观察者优先级及设备级隔离优化。
- **建议修正方向**：同步返回键 AOT 模型及优先级新常数，补全多窗口指针窃取隔离逻辑。

### 9.4 可复用知识资产
- **性能锚点**：预测性返回通过 Shell 托管动画减少了 App 主线程的每帧负担。
- **核心类名**：`OnBackInvokedDispatcher.PRIORITY_SYSTEM_NAVIGATION_OBSERVER`。
- **技术结论**：Android 16 实现了手势导航从“简单的输入捕获”向“精准的设备流管理”的飞跃。

## 十一、落盘信息
- 已写入文件：`logs/external-review/2026-04-28-15-ch03-03-gesture-navigation-external-review.md` — 知识盲区

### 三键导航长按阈值

**重要程度**：高

**建议研究方向**：400ms 等长按逻辑如何通过 InputDispatcher 触发预测预览

**关联章节**：3.3

**外部 review 来源**：2026-04-28-15-ch03-03-gesture-navigation-external-review.md

### Observer 注册竞争

**重要程度**：中

**建议研究方向**：为什么 API 36 暂时限制每个 Dispatcher 仅一个观察者回调

**关联章节**：3.3

**外部 review 来源**：2026-04-28-15-ch03-03-gesture-navigation-external-review.md


## [2026-04-28] 3.4 输入延迟与预测输入技术
- **严重级别**：P1
- **位置**：调度优化、量化工具及采样策略小节
- **问题描述**：未反映 2026 年 ADPF 闭环、HWC 4.0 标准及动态高频采样。
- **建议修正方向**：同步最新闭环调度逻辑并引入标准化光子时间线。

### 9.4 可复用知识资产
- **性能锚点**：HWC 4.0 实现了端到端延迟的软件级精准度量。
- **核心机制**：ADPF 动态线程提升。
- **技术结论**：2026 年的输入优化已从“单点提速”进化为“全链路反馈闭环”。

## 十一、落盘信息
- 已写入文件：`logs/external-review/2026-04-28-15-ch03-04-input-latency-prediction-external-review.md` — 知识盲区

### AI 预测的置信度管理

**重要程度**：高

**建议研究方向**：系统如何处理 TFLite 模型输出的概率分布

**关联章节**：3.4

**外部 review 来源**：2026-04-28-15-ch03-04-input-latency-prediction-external-review.md

### ADPF Margin 的节能权衡

**重要程度**：中

**建议研究方向**：预留 CPU 余量对待机功耗的微观影响

**关联章节**：3.4

**外部 review 来源**：2026-04-28-15-ch03-04-input-latency-prediction-external-review.md


## [2026-04-28] 3.5 输入事件拦截与安全机制
- **严重级别**：P1
- **位置**：安全边界、拦截机制及演进趋势小节
- **问题描述**：未反映 2026 年敏感隔离属性、物理分发切断及通话保护策略。
- **建议修正方向**：同步 API 36 敏感视图规范并引入 Android 17 的 InputMonitor 物理切断逻辑。

### 9.4 可复用知识资产
- **性能锚点**：密码输入触发 InputDispatcher 零延迟分发挂起。
- **核心属性**：`accessibilityDataSensitive`。
- **技术结论**：Android 16 标志着输入系统进入了“意图敏感型分发保护”阶段。

## 十一、落盘信息
- 已写入文件：`logs/external-review/2026-04-28-15-ch03-05-input-interception-security-external-review.md` — 知识盲区

### TapTrap 动画漏洞

**重要程度**：高

**建议研究方向**：系统如何防止在 Activity 切换瞬间利用透明度进行点击欺诈

**关联章节**：3.5

**外部 review 来源**：2026-04-28-15-ch03-05-input-interception-security-external-review.md

### Spy Window 的能量模型

**重要程度**：中

**建议研究方向**：后台高频监听输入流对系统唤醒锁的影响

**关联章节**：3.5

**外部 review 来源**：2026-04-28-15-ch03-05-input-interception-security-external-review.md


## [2026-04-28] 4.1 Android 内存模型全景
- **严重级别**：P1
- **位置：**内核管理、物理内存及指标分析小节
- **问题描述**：未反映 2026 年内存限额契约及 MTE/16KB 硬件开销。
- **建议修正方向**：引入配额制说明并更新 MTE/16KB 的内存基准损耗。

### 9.4 可复用知识资产
- **性能锚点**：MTE 系统开销 5%，16KB 膨胀系数 1.1x。
- **核心类名**：`ProfilingManager.TRIGGER_TYPE_ANOMALY`。
- **技术结论**：2026 年的内存管理已从“策略建议”演进为“硬性配额审计”。

## 十一、落盘信息
- 已写入文件：`logs/external-review/2026-04-28-15-ch04-01-memory-overview-external-review.md` — 知识盲区

### AnonSwap 的限额计算

**重要程度**：高

**建议研究方向**：MemoryLimiter 如何对 ZRAM 压缩后的匿名页进行计费

**关联章节**：4.1

**外部 review 来源**：2026-04-28-15-ch04-01-memory-overview-external-review.md

### MTE SYNC 模式的性能降级

**重要程度**：中

**建议研究方向**：精确检测模式对 CPU 缓存带宽的二次占用

**关联章节**：4.1

**外部 review 来源**：2026-04-28-15-ch04-01-memory-overview-external-review.md


## [2026-04-28] 4.2 Linux 内核内存管理
- **严重级别**：P1
- **位置**：页面回收、16KB 页适配及协同优化小节
- **问题描述**：未反映 2026 年 MGLRU 默认化、内核-GC 协同细节及 75% 缺页降幅。
- **建议修正方向**：同步最新内核策略并补全 Silk 论文落地后的架构逻辑。

### 9.4 可复用知识资产
- **性能锚点**：16KB 页模式下 page_fault 减少 75%。
- **核心指令**：`madvise(MADV_COLD)`。
- **技术结论**：Android 16 标志着内存治理进入了“由虚拟机驱动内核回收”的精细化阶段。

## 十一、落盘信息
- 已写入文件：`logs/external-review/2026-04-28-15-ch04-02-linux-memory-external-review.md` — 知识盲区

### 16KB 下的匿名页回收延迟

**重要程度**：中

**建议研究方向**：单次压缩/解压 16KB 块对主线程 D 状态的时长贡献

**关联章节**：4.2

**外部 review 来源**：2026-04-28-15-ch04-02-linux-memory-external-review.md

### mg_util 分代权重

**重要程度**：高

**建议研究方向**：系统如何根据 App 优先级（ADJ）动态干预 MGLRU 的代际转换

**关联章节**：4.2

**外部 review 来源**：2026-04-28-15-ch04-02-linux-memory-external-review.md


## [2026-04-28] 4.3 ART 虚拟机内存管理
- **严重级别**：P1
- **位置**：分代回收、分配器原理及性能分析小节
- **问题描述**：未反映 2026 年分代 CMC 收益、16KB 动态对齐及无锁队列红利。
- **建议修正方向**：更新性能基准数据，引入运行时对齐逻辑，并加入稳定性优化说明。

### 9.4 可复用知识资产
- **性能锚点**：分代 CMC 使 OpenCL 计算能效提升 32.6%。
- **核心逻辑**：运行时 GetPageSize() 取代硬编码对齐。
- **技术结论**：Android 16 实现了虚拟机层与硬件层（大页/多核）的深度自适应对齐。

## 十一、落盘信息
- 已写入文件：`logs/external-review/2026-04-28-15-ch04-03-art-memory-external-review.md` — 知识盲区

### 16KB 页对 TLAB 碎片的影响

**重要程度**：中

**建议研究方向**：最小 16KB TLAB 是否会导致极小线程应用的内存浪费

**关联章节**：4.3

**外部 review 来源**：2026-04-28-15-ch04-03-art-memory-external-review.md

### 晋升阈值动态调节

**重要程度**：高

**建议研究方向**：系统如何根据 ARR 刷新率动态压缩年轻代回收的 Budget

**关联章节**：4.3

**外部 review 来源**：2026-04-28-15-ch04-03-art-memory-external-review.md

### FrameRateCategory 权重

**重要程度**：高

**建议研究方向**：NORMAL 与 HIGH 在不同电池水位下的具体值差异

**关联章节**：02.02

**外部 review 来源**：2026-04-28-15-ch02-02-framerate-external-review.md


### 高频注入对功耗的冲击

**重要程度**：中

**建议研究方向**：虚拟 VSync 触发时的 CPU Cluster 唤醒策略

**关联章节**：02.02

**外部 review 来源**：2026-04-28-15-ch02-02-framerate-external-review.md


### resume 切片截止判定

**重要程度**：高

**建议研究方向**：组合器检查 deadlineNanos 的频率

**关联章节**：02.04

**外部 review 来源**：2026-04-28-15-ch02-04-choreographer-external-review.md


### vsyncId 唯一性范围

**重要程度**：低

**建议研究方向**：系统重启后 ID 是否复位

**关联章节**：02.04

**外部 review 来源**：2026-04-28-15-ch02-04-choreographer-external-review.md


### GPU Headroom 调控精度

**重要程度**：高

**建议研究方向**：系统如何避免性能反馈导致的频率震荡

**关联章节**：02.05

**外部 review 来源**：2026-04-28-15-ch02-05-main-render-thread-external-review.md


### 并发分箱 (Concurrent Binning)

**重要程度**：中

**建议研究方向**：Adreno 830 对 Tile 渲染顺序的硬件级重排

**关联章节**：02.05

**外部 review 来源**：2026-04-28-15-ch02-05-main-render-thread-external-review.md


### ModulateAlpha 规避路径

**重要程度**：中

**建议研究方向**：如何利用 Compose 1.10 策略彻底跳过离屏缓冲

**关联章节**：02.07

**外部 review 来源**：2026-04-28-15-ch02-07-hardware-layer-external-review.md


### VMA 内存管理

**重要程度**：高

**建议研究方向**：驱动层如何通过子分配缓解大页碎片

**关联章节**：02.07

**外部 review 来源**：2026-04-28-15-ch02-07-hardware-layer-external-review.md


### Z-Culling 的透明限制

**重要程度**：高

**建议研究方向**：半透明层如何阻断硬件深度测试的优化

**关联章节**：02.08

**外部 review 来源**：2026-04-28-15-ch02-08-overdraw-external-review.md


### Standardized Descriptor

**重要程度**：中

**建议研究方向**：不同 GPU 厂商如何映射到统一的 pixels_drawn 标签

**关联章节**：02.08

**外部 review 来源**：2026-04-28-15-ch02-08-overdraw-external-review.md


### Host Image Copy 内存收益

**重要程度**：中

**建议研究方向**：实际设备在 1080p 纹理上传时的 PSS 峰值对比

**关联章节**：02.09

**外部 review 来源**：2026-04-28-15-ch02-09-rendering-evolution-external-review.md


### Graphite 多线程开销

**重要程度**：高

**建议研究方向**：并行命令录制对主线程 doFrame 耗时的量化减负

**关联章节**：02.09

**外部 review 来源**：2026-04-28-15-ch02-09-rendering-evolution-external-review.md


### Headroom 刷新频率

**重要程度**：中

**建议研究方向**：调用该 API 本身带来的上下文切换开销

**关联章节**：02.10

**外部 review 来源**：2026-04-28-15-ch02-10-gpu-rendering-external-review.md


### 标准化计数器的厂商覆盖率

**重要程度**：高

**建议研究方向**：旧机型升级 Android 16 后是否都能支持 gpu_busy

**关联章节**：02.10

**外部 review 来源**：2026-04-28-15-ch02-10-gpu-rendering-external-review.md


### Timeline 模式下的 GPU Hang 诊断

**重要程度**：高

**建议研究方向**：当计数器停止前进时，系统如何执行超时自愈

**关联章节**：02.16

**外部 review 来源**：2026-04-28-15-ch02-16-sync-fence-external-review.md


### IOTLB 空间覆盖率

**重要程度**：中

**建议研究方向**：16KB 页对 SMMU 访问 Fence 状态时的缓存命中率提升

**关联章节**：02.16

**外部 review 来源**：2026-04-28-15-ch02-16-sync-fence-external-review.md


### present_id 跨屏映射

**重要程度**：中

**建议研究方向**：外接显示器场景下硬件 ID 与 Pacesetter 时钟的同步开销

**关联章节**：02.17

**外部 review 来源**：2026-04-28-15-ch02-17-frame-pacing-external-review.md


### 16KB 页对 IPC 计时的提速

**重要程度**：低

**建议研究方向**：更少的上下文切换是否优化了 Swappy 内部 fd 传递耗时

**关联章节**：02.17

**外部 review 来源**：2026-04-28-15-ch02-17-frame-pacing-external-review.md


### 预测失败的回滚机制

**重要程度**：中

**建议研究方向**：当预判的 expectedPresentTime 未命中时的系统补偿策略

**关联章节**：02.19

**外部 review 来源**：2026-04-28-15-ch02-19-refresh-rate-switching-external-review.md


### 16KB 页对评分缓存的影响

**重要程度**：低

**建议研究方向**：打分表在内存大页下的 TLB 命中率提升

**关联章节**：02.19

**外部 review 来源**：2026-04-28-15-ch02-19-refresh-rate-switching-external-review.md


### 内存预算的 A/B Test

**重要程度**：中

**建议研究方向**：不同内存分档下的降级策略对转化率的影响

**关联章节**：04.05

**外部 review 来源**：2026-04-28-15-ch04-05-app-memory-optimization-external-review.md


### MemoryLimiter 的判定粒度

**重要程度**：高

**建议研究方向**：匿名内存与 Swap 的累计计费权重

**关联章节**：04.05

**外部 review 来源**：2026-04-28-15-ch04-05-app-memory-optimization-external-review.md


### AnonSwap 的限额审计

**重要程度**：高

**建议研究方向**：系统如何防止应用通过共享进程（如 WebView）逃避内存计费

**关联章节**：04.06

**外部 review 来源**：2026-04-28-15-ch04-06-memory-evolution-external-review.md


### MTE 4.0 硬件收益

**重要程度**：中

**建议研究方向**：Android 17 是否针对 MTE4 的异步错误队列进行了优化

**关联章节**：04.06

**外部 review 来源**：2026-04-28-15-ch04-06-memory-evolution-external-review.md


### 32MB 页的回收背压

**重要程度**：高

**建议研究方向**：当系统内存紧张时，巨型页拆分的 CPU 停顿耗时

**关联章节**：04.07

**外部 review 来源**：2026-04-28-15-ch04-07-16kb-page-size-external-review.md


### 兼容模式的 RELRO 状态

**重要程度**：中

**建议研究方向**：匿名拷贝后，Bionic 如何通过 phdr 重新应用只读保护

**关联章节**：04.07

**外部 review 来源**：2026-04-28-15-ch04-07-16kb-page-size-external-review.md


### slice 长度对 Deadline 的偏置

**重要程度**：高

**建议研究方向**：应用如何通过控制处理时长请求获得更早的 CPU 响应

**关联章节**：05.01

**外部 review 来源**：2026-04-28-15-ch05-01-linux-scheduling-external-review.md


### EEVDF 在低功耗核心的滞后

**重要程度**：中

**建议研究方向**：调度器如何防止小核任务因 Lag 过高而强行抢占大核

**关联章节**：05.01

**外部 review 来源**：2026-04-28-15-ch05-01-linux-scheduling-external-review.md


### 16KB 页对 PELT 采样的干扰

**重要程度**：中

**建议研究方向**：大内存页访问模式是否导致利用率信号的相位偏移

**关联章节**：05.02

**外部 review 来源**：2026-04-28-15-ch05-02-eas-external-review.md


### mTHP 时代的 CPUIdle 偏置

**重要程度**：低

**建议研究方向**：内核大页整理任务如何通过 EAS 避开前台大核

**关联章节**：05.02

**外部 review 来源**：2026-04-28-15-ch05-02-eas-external-review.md


### 代理执行对中断亲和性的影响

**重要程度**：中

**建议研究方向**：硬件中断是否能随着线程的“优先级借用”而自动迁移核心

**关联章节**：05.03

**外部 review 来源**：2026-04-28-15-ch05-03-big-little-external-review.md


### 全大核时代的 Idle 深度

**重要程度**：高

**建议研究方向**：失去小核后，系统如何通过 DSU-120 降低待机泄露电流

**关联章节**：05.03

**外部 review 来源**：2026-04-28-15-ch05-03-big-little-external-review.md


### Direct Hint 的系统配额

**重要程度**：高

**建议研究方向**：多个高优 App 同时请求直连调频时的仲裁逻辑

**关联章节**：05.04

**外部 review 来源**：2026-04-28-15-ch05-04-dvfs-external-review.md


### SCMI 快速通道延迟

**重要程度**：中

**建议研究方向**：基于 Memory-mapped channel 的 SCMI 命令执行耗时

**关联章节**：05.04

**外部 review 来源**：2026-04-28-15-ch05-04-dvfs-external-review.md


### Headroom 的厂商标定一致性

**重要程度**：高

**建议研究方向**：不同 SoC 厂商对“1.0”余量的物理定义差异

**关联章节**：05.05

**外部 review 来源**：2026-04-28-15-ch05-05-thermal-external-review.md


### 16KB 页下的 zRAM 功耗补偿

**重要程度**：中

**建议研究方向**：压缩内存操作增加的 CPU 热量是否抵消了页表节能

**关联章节**：05.05

**外部 review 来源**：2026-04-28-15-ch05-05-thermal-external-review.md


### Energy Points 动态重算

**重要程度**：高

**建议研究方向**：系统如何处理外接电源对能量预算的瞬时扩容

**关联章节**：05.06

**外部 review 来源**：2026-04-28-15-ch05-06-android-power-external-review.md


### Wattson 模型的 SoC 覆盖率

**重要程度**：中

**建议研究方向**：骁龙 8 Elite 以外的芯片如何通过 OEM 补丁支持 Wattson

**关联章节**：05.06

**外部 review 来源**：2026-04-28-15-ch05-06-android-power-external-review.md


### Energy Limiter 的罚没逻辑

**重要程度**：高

**建议研究方向**：低电量模式下系统如何动态压缩单应用能量配额

**关联章节**：05.07

**外部 review 来源**：2026-04-28-15-ch05-07-cpu-evolution-external-review.md


### EEVDF 时代的 nice 值权重

**重要程度**：中

**建议研究方向**：旧有的 nice -20 到 +19 映射在 EEVDF 中是否保持完全兼容

**关联章节**：05.07

**外部 review 来源**：2026-04-28-15-ch05-07-cpu-evolution-external-review.md

## [2026-04-28] 4.7 16KB Page Size 与 Android 性能 — 知识盲区

### 盲区描述
Android 16/17 16KB page size 设备上的 THP 默认策略、mTHP/contpte 支持状态，以及 4KB ELF compat 模式对 PSS / Shared_Clean / Private_Dirty 的影响仍缺少一手源码或实机证据。external-review 已命中这些线索，本轮复核后判断需要进入研究闭环。

### 重要程度
高

### 建议研究方向
- 查 Android common kernel / Pixel kernel 中 16KB page size 配置、THP 默认策略和 contpte/mTHP 相关开关。
- 在 16KB 设备或模拟器上对 4KB 对齐 .so compat 与 16KB 对齐 .so 做 `/proc/<pid>/smaps` 对比。
- 对照 bionic `linker_phdr_16kib_compat.cpp`，确认匿名映射、RELRO 保护和共享页损失的精确边界。

### 关联章节
- 4.7

## [2026-04-28] 7.6 案例集 — 知识盲区

### 盲区描述
流畅度案例集缺少 SurfaceFlinger/HWC 合成和温控降频两个高频系统侧 Jank 场景，当前案例无法覆盖章节锚点中的 SF 合成、温控两类根因。

### 重要程度
高

### 建议研究方向
- 采集 SF/HWC 合成异常 trace：CLIENT/DEVICE composition、fence、FrameTimeline、present deadline。
- 采集 thermal throttling trace：thermal HAL、CPU/GPU frequency、sched runnable latency、FrameTimeline。
- 将两个场景写成完整案例，包含现象、trace 证据、归因和修复/缓解策略。

### 关联章节
- 7.6
- 2.6
- 5.5

## [2026-04-28] 5.8 后台执行限制与优化 — WIU 能力的窗口期

### 盲区描述
用户离开前台后多久 WIU 令牌会失效

### 重要程度
高

### 建议研究方向
- 用户离开前台后多久 WIU 令牌会失效

### 关联章节
- 5.8

### 外部 review 来源
- Gemini 外部 review

## [2026-04-28] 5.8 后台执行限制与优化 — pVM 功耗熔断机制

### 盲区描述
豁免状态下虚拟机对系统整体热指标的反馈阈值

### 重要程度
中

### 建议研究方向
- 豁免状态下虚拟机对系统整体热指标的反馈阈值

### 关联章节
- 5.8

### 外部 review 来源
- Gemini 外部 review

## [2026-04-28] 5.9 ADPF 自适应性能框架 — ADPF 响应与 EEVDF slice 联动

### 盲区描述
提频 Hint 是否会同时缩短任务的虚拟截止日期

### 重要程度
高

### 建议研究方向
- 提频 Hint 是否会同时缩短任务的虚拟截止日期

### 关联章节
- 5.9

### 外部 review 来源
- Gemini 外部 review

## [2026-04-28] 5.9 ADPF 自适应性能框架 — 16KB 页下的 Session 创建延迟

### 盲区描述
堆内存分页增大后，创建大量 HintSession 对 system_server 内存池的冲击

### 重要程度
低

### 建议研究方向
- 堆内存分页增大后，创建大量 HintSession 对 system_server 内存池的冲击

### 关联章节
- 5.9

### 外部 review 来源
- Gemini 外部 review

## [2026-04-28] 5.10 JobScheduler/WorkManager 调度与后台任务性能 — Energy Credits 重算频率

### 盲区描述
1 毫焦耳（µJ）如何精确折算为不同优先级的执行时长

### 重要程度
高

### 建议研究方向
- 1 毫焦耳（µJ）如何精确折算为不同优先级的执行时长

### 关联章节
- 5.10

### 外部 review 来源
- Gemini 外部 review

## [2026-04-28] 5.10 JobScheduler/WorkManager 调度与后台任务性能 — pVM 后台任务独立性

### 盲区描述
虚拟化环境任务是否能跨越宿主 App 的 Quota 限制

### 重要程度
中

### 建议研究方向
- 虚拟化环境任务是否能跨越宿主 App 的 Quota 限制

### 关联章节
- 5.10

### 外部 review 来源
- Gemini 外部 review

## [2026-04-28] 5.11 端侧 AI 推理性能 — pVM 推理的能效免死金牌

### 盲区描述
隔离环境下的 AI 任务是否豁免 Energy Limiter 强杀

### 重要程度
高

### 建议研究方向
- 隔离环境下的 AI 任务是否豁免 Energy Limiter 强杀

### 关联章节
- 5.11

### 外部 review 来源
- Gemini 外部 review

## [2026-04-28] 5.11 端侧 AI 推理性能 — 模型预留内存的 LMK 判定

### 盲区描述
系统预留的 3GB RAM 是否参与 global PSS 的回收基准计算

### 重要程度
中

### 建议研究方向
- 系统预留的 3GB RAM 是否参与 global PSS 的回收基准计算

### 关联章节
- 5.11

### 外部 review 来源
- Gemini 外部 review

## [2026-04-28] 6.1 Android 存储架构 — Storage APEX 的接口版本回退

### 盲区描述
当模块更新失败时，系统如何回退到内联的旧版存储服务

### 重要程度
中

### 建议研究方向
- 当模块更新失败时，系统如何回退到内联的旧版存储服务

### 关联章节
- 6.1

### 外部 review 来源
- Gemini 外部 review

## [2026-04-28] 6.1 Android 存储架构 — 16KB 下的 EROFS 压缩窗口

### 盲区描述
页面变大后，LZ4 算法的压缩窗口对齐策略

### 重要程度
高

### 建议研究方向
- 页面变大后，LZ4 算法的压缩窗口对齐策略

### 关联章节
- 6.1

### 外部 review 来源
- Gemini 外部 review

## [2026-04-28] 6.2 文件系统 — ZNS 模式下的 OTA 磨损

### 盲区描述
Virtual A/B 写入如何避开 ZNS 的顺序约束冲突

### 重要程度
高

### 建议研究方向
- Virtual A/B 写入如何避开 ZNS 的顺序约束冲突

### 关联章节
- 6.2

### 外部 review 来源
- Gemini 外部 review

## [2026-04-28] 6.2 文件系统 — 16KB 下的 NAT 缓存抖动

### 盲区描述
页面变大后 NAT 节点在 L1/L2 缓存中的冲突率变化

### 重要程度
中

### 建议研究方向
- 页面变大后 NAT 节点在 L1/L2 缓存中的冲突率变化

### 关联章节
- 6.2

### 外部 review 来源
- Gemini 外部 review

## [2026-04-28] 6.3 I/O 调度 — io_uring 的安全沙箱

### 盲区描述
系统如何限制非 Root 进程调用 io_uring 的子集指令

### 重要程度
高

### 建议研究方向
- 系统如何限制非 Root 进程调用 io_uring 的子集指令

### 关联章节
- 6.3

### 外部 review 来源
- Gemini 外部 review

## [2026-04-28] 6.3 I/O 调度 — 16KB 下的 I/O 合并概率

### 盲区描述
页面变大后，块层调度器合并 bio 请求的成功率变化

### 重要程度
中

### 建议研究方向
- 页面变大后，块层调度器合并 bio 请求的成功率变化

### 关联章节
- 6.3

### 外部 review 来源
- Gemini 外部 review

## [2026-04-28] 6.4 存储演进 — io_uring 的特权收割

### 盲区描述
Android 17 如何通过 SELinux 确保只有 vold 等关键路径能使用异步 I/O

### 重要程度
高

### 建议研究方向
- Android 17 如何通过 SELinux 确保只有 vold 等关键路径能使用异步 I/O

### 关联章节
- 6.4

### 外部 review 来源
- Gemini 外部 review

## [2026-04-28] 6.4 存储演进 — 16KB 页下的 Bionic 加载兼容

### 盲区描述
兼容模式在 Android 16 下的具体性能代价

### 重要程度
中

### 建议研究方向
- 兼容模式在 Android 16 下的具体性能代价

### 关联章节
- 6.4

### 外部 review 来源
- Gemini 外部 review

## [2026-04-28] 19.26 混合栈与跨平台 APM — WebView 可见状态与白屏采样锚点

### 盲区描述
章节讨论 WebView 白屏检测时漏掉 `onPageCommitVisible()` 与 `WebView.postVisualStateCallback()`。需要明确它们和 `onPageFinished()`、业务 ready、`PixelCopy` 的先后关系，避免线上采样旧页面或未提交 visual state。

### 重要程度
高

### 建议研究方向
- 复核 Android WebView API 23+ 官方文档中 `onPageCommitVisible()` 与 `postVisualStateCallback()` 的触发语义。
- 设计一条可发布的白屏检测时序：navigation start → commit visible → visual state callback → PixelCopy / DOM / business ready。
- 对比旧 WebView、跨进程 WebView renderer、Surface/TextureView 场景下 PixelCopy 的采样边界。

### 关联章节
19.26, 7.11, 18.13

## [2026-04-28] 2.2 帧率与刷新率 — 知识盲区

### 盲区描述
external-review 已命中 HyperOS 高频 VSync 注入方向；Task9 复核发现正文已经写入“HyperOS 2.0 通过 240Hz+ 虚拟 VSync 注入让 Choreographer 一个物理帧内多次处理输入”，但缺少 OEM 文档、源码、Perfetto trace 或可复现实验。

### 重要程度
高

### 建议研究方向
- 查找 HyperOS / MIUI 渲染与输入延迟优化的一手材料，区分触控采样率、输入预测、虚拟 VSync 与 Choreographer 回调注入。
- 用 Perfetto 对比物理刷新率、VSYNC-app、`Choreographer#doFrame`、InputDispatcher/InputReader 事件间隔，确认是否存在一个物理周期内多次 `CALLBACK_INPUT`。
- 若只能获得二手信息，正文应标 `[待验证]` 并移到 OEM 差异案例。

### 关联章节
- 2.2
- 2.4
- 17.3

## [2026-04-28] 2.7 Hardware Layer — 知识盲区

### 盲区描述
external-review 已命中 Android 16 自动建层与 16KB 页内存成本方向；Task9 复核未找到“drawPath/RenderEffect 权重 + 静态节点阈值自动升层”的明确 AOSP 锚点，也未找到 16KB 页对 GPU layer 小分配导致 9% 内存压力的图形内存专项数据。

### 重要程度
高

### 建议研究方向
- 在 `frameworks/base/libs/hwui` 与 `frameworks/base/graphics/java/android/graphics/RenderNode.java` 中定位自动 promotion 的真实条件、函数名、阈值和版本引入提交。
- 用不同尺寸 View layer 采集 gralloc/DMA-BUF stride、memtrack、dumpsys SurfaceFlinger/GPU memory，确认 16KB page 下的实际对齐与尾部浪费。
- 复核 Compose 1.10 `graphicsLayer` 离屏缓冲池化是否有 AndroidX release note 或源码提交，补 LazyLayout 快速滑动 trace 数据。

### 关联章节
- 2.7
- 4.7
- 7.5


## [2026-04-28] 2.8 过度绘制 — 知识盲区

### 盲区描述
Compose 1.10 是否存在公开的背景合并/遮挡跳过优化；external-review 已命中，但本轮未找到足够官方锚点。

### 重要程度
高

### 建议研究方向
- 检索 Compose 1.10 release notes、AOSP/AndroidX commit、issue tracker 中与 Modifier.background、Surface、draw skipping 相关的条目
- 确认该优化是否影响像素级 overdraw，还是只影响 composition/draw phase CPU 开销

### 关联章节
- 2.8
- 2.5

## [2026-04-28] 2.9 渲染机制的版本演进 — 知识盲区

### 盲区描述
Android 16 上 Skia Graphite/HWUI 的默认启用范围、ANGLE 系统级启用条件与 VPA16 的准确边界。

### 重要程度
高

### 建议研究方向
- 核对 AOSP android16-qpr2-release 中 HWUI 后端选择、Skia Graphite 开关、ANGLE 系统属性/feature flag
- 核对 Android Vulkan Profile 2025 官方文档，区分 Vulkan Profile 要求与 OpenGL ES 运行时翻译

### 关联章节
- 2.9
- 2.10
- 2.14

## [2026-04-28] 16.3 AOSP 源码编译与调试环境 — 知识盲区

### 盲区描述
Cuttlefish 的 crosvm/KVM/virtio 架构与官方安装路径；external-review 已命中 crosvm/virtio 盲区。

### 重要程度
中

### 建议研究方向
- 阅读 source.android.com Cuttlefish get-started 与 device/google/cuttlefish 文档
- 补充 CI artifact 路径、host package、cuttlefish-base/cuttlefish-user 与 launch_cvd 的可复现步骤

### 关联章节
- 16.3

## [2026-04-28] 2.10 GPU 渲染深入 — Android 16 GPU 观测与 Gralloc 16KB 行为

### 盲区描述
章节和 external-review 引入了 `gpu_busy` 标准化、`gpu_render_stages` 阶段可见性、Gralloc AIDL V2 sub-allocation 等 Android 16 说法，但缺少 source.android.com、perfetto.dev、AOSP 接口/VTS 或实机 trace 证据。

### 重要程度
高

### 建议研究方向
- 核对 API 36 / Android 16 官方图形、Perfetto、VPA16 文档。
- 核对 `hardware/interfaces/graphics/allocator/aidl`、mapper/allocator vendor 实现和 VTS 是否要求 sub-allocation。
- 找一台 Android 16 设备导出 Perfetto GPU counter descriptor，确认是否存在统一 `gpu_busy` 标签。

### 关联章节
- 2.10

## [2026-04-28] 2.16 Sync Fence 框架与帧同步机制 — Timeline Semaphore 与 native fence fd 边界

### 盲区描述
章节把 Vulkan Timeline Semaphores 写成会替代 acquire/release/present fence fd，并写入 Android 17 去 fd 化路线图；当前缺少 Android 17 CDD/AOSP/source.android.com 证据，也缺少 Vulkan external sync 与 Android native fence 交界的源码链说明。

### 重要程度
高

### 建议研究方向
- 核对 Android 16/17 CDD、VPA16、AOSP Surface/ANativeWindow/BufferQueue/HWC3 的同步接口。
- 查 Vulkan timeline semaphore、external semaphore/fence fd import/export 在 Android HWUI/ANGLE 中的使用边界。
- 若保留 16KB 页减少 fence wait 抖动的说法，补 kernel/perf/ftrace 实测。

### 关联章节
- 2.16

## [2026-04-28] 2.0 渲染系统总纲 — 知识盲区

### 盲区描述
Android 17 图形栈入口与外部 Review 候选结论未完成回源。active external-review 已命中 Present ID、Vulkan/ANGLE、Graphite、Impeller、Jank Isolation 等候选点，但 README 仍停留在 Android 12-16 的总括表达。

### 重要程度
高

### 建议研究方向
- 核对 AOSP / Android Developers 对 Vulkan/ANGLE/Graphite 的正式边界
- 核对 Flutter Impeller Android 默认后端的版本与 API 条件
- 核对 Frame Pacing / Present ID 的官方数据与适用设备条件

### 关联章节
- 2.10
- 2.11
- 2.14
- 2.17
- 2.20
- 2.21

## [2026-04-28] 3.0 第 3 章：输入系统 — 知识盲区

### 盲区描述
Android 16/17 输入栈变化缺少总纲级验证矩阵。active external-review 已命中 AOT Predictive Back、ML predictor、Impulse、DeliQueue、InputMonitor 隔离等候选点，需要先回源再决定写入哪些子节。

### 重要程度
高

### 建议研究方向
- 核对 Predictive Back 版本/targetSdk/系统拦截边界
- 核对 MotionPredictor、VelocityTracker 默认策略变化和可观测 trace 点
- 核对 DeliQueue 对输入回调排队延迟的量化收益是否可公开引用

### 关联章节
- 3.1
- 3.2
- 3.3
- 3.4
- 3.5
- 3.6

## [2026-04-28] 1.13 MessageQueue 机制与 DeliQueue 无锁优化 — 待验证外部技术线索

### 盲区描述
external-review 提到 Perfetto `MQ.Delivered` / `MQ.Backlog` / `MQ.Waiters` 计数器，以及 Android 17 最终实现改为 Treiber Stack + Min-heap。本轮复核未在官方行为变更页、公开 AOSP android-16.0.0_r1 源码或可访问文档中确认。

### 重要程度
中

### 建议研究方向
- 查 Android 17 对应 tag 的 `frameworks/base/core/java/android/os/*MessageQueue*` 实现
- 查 Perfetto proto / track event 中是否有 MQ.* counter 的正式 producer
- 区分官方 public API、内部 trace label 与第三方文章二次概括

### 关联章节
1.13、3.1、13.1

## [2026-04-28] 6.2 文件系统 — 待验证外部技术线索

### 盲区描述
external-review 提到 Android 16 F2FS ZNS、EROFS 16KB sub-page compression、Android 17 IncFS `.prefetch_hints`。本轮只能确认 F2FS 对 zoned block device 有上游能力、EROFS 官方文档有 in-place decompression / 镜像压缩数据；未确认这些说法已经成为 Android 16/17 平台行为。

### 重要程度
高

### 建议研究方向
- 对照 android16-6.12 GKI config、F2FS zoned device patch 与 Pixel/vendor kernel 开关
- 查 EROFS 16KB page 场景下压缩簇、folio、sub-page 相关提交
- 查 IncFS 文档、Play streaming install 实现和 `.prefetch_hints` 是否存在公开 AOSP 入口

### 关联章节
6.1、6.2、6.3、6.4



## [2026-04-29] 3.5 输入事件拦截与安全机制 — 知识盲区

### 盲区描述
InputMonitor / monitorGestureInput / pilferPointers 与 Android 14 accessibilityDataSensitive 没有进入章节主线。external-review 已命中 InputMonitor 隔离相关线索，但其“Android 17 密码场景物理切断”说法未完成回源；本轮能确认的是 AOSP android-14.0.0_r1 已存在 InputMonitor 监控输入流、MONITOR_INPUT 权限、pilferPointers，以及 View.accessibilityDataSensitive / isAccessibilityTool 边界。

### 重要程度
高

### 建议研究方向
- 核对 `frameworks/base/core/java/android/view/InputMonitor.java`、`InputManagerService.monitorGestureInput()`、`InputDispatcher` spy window / pilferPointers 行为。
- 核对 `View.accessibilityDataSensitive`、`ACCESSIBILITY_DATA_SENSITIVE_YES`、`AccessibilityServiceInfo.isAccessibilityTool` 对无障碍交互的限制。
- 查 Android 15/16/17 是否有密码输入场景对非系统 InputMonitor 的新增限制；没有一手证据前不要写入正文。

### 关联章节
- 3.5
- 9.1
- 9.2

## [2026-04-29] 4.2 Linux 内核内存管理 — 知识盲区

### 盲区描述
MGLRU 在 Android common kernel / GKI / Pixel 分支中的启用状态缺少版本矩阵。external-review 已命中“Android 16 GKI 6.12 默认开启 MGLRU”的线索，但本轮只能确认 MGLRU 已在 Linux 6.1 主线，不能把主线合入直接等同于 Android 10-16 设备默认行为。

### 重要程度
高

### 建议研究方向
- 检查 android14-6.1、android15-6.6、android16-6.12 的 `CONFIG_LRU_GEN`、`CONFIG_LRU_GEN_ENABLED`、Pixel vendor defconfig 与运行态 `/sys/kernel/mm/lru_gen/enabled`。
- 区分传统 LRU、MGLRU 可用、MGLRU 默认启用、OEM 二次调参四种状态。
- 核对 Silk / GC-内核协同论文结论与 Android 平台实现边界，避免把研究原型写成系统默认能力。

### 关联章节
- 4.2
- 4.3
- 4.4

## [2026-04-29] 5.2 EAS 能量感知调度 — 知识盲区

### 盲区描述
external-review 已命中 “GKI 6.12 改为 sum aggregation” 线索，但本轮复核 android16-6.12 common kernel 仍是 max aggregation。需要确认该说法是否来自 RFC、Pixel/vendor hook 或特定 OEM 分支。

### 重要程度
高

### 建议研究方向
- 核对 android16-6.12 tags、Pixel vendor kernel、`CONFIG_USE_VENDOR_GROUP_UTIL` / vendor hook 相关实现
- 检索 uclamp sum aggregation RFC/patchset 与是否合入 mainline/GKI
- 用目标设备 `/proc/sched_debug`、trace 和源码确认 rq 级 clamp 聚合口径

### 关联章节
- 5.2


## [2026-04-29] 5.3 大小核架构 — 知识盲区

### 盲区描述
external-review 已命中 Proxy Execution、RTG、DSU-120 16KB 线索。本轮能确认 android16-6.12 有 `CONFIG_SCHED_PROXY_EXEC` 与 `sched_proxy_exec` 开关，但未确认 RTG 符号在 GKI common 存在，也未确认 DSU-120 存在 16KB page mode snoop-filter hash register。

### 重要程度
高

### 建议研究方向
- 核对 Qualcomm/MediaTek/Pixel vendor kernel 中 RTG、`preferred_cluster`、`SCHED_BOOST_ON_BIG` 的具体分支
- 核对 Proxy Execution 在 Android 16/17 设备上的 config、boot arg、sysfs enable 状态
- 查 ARM DSU-120 TRM/whitepaper 是否公开 16KB page 与 snoop filter hash 相关寄存器

### 关联章节
- 5.3

## [2026-04-29] 5.5 Thermal 管控 — 知识盲区

### 盲区描述
Android 16 `SystemHealthManager.getCpuHeadroom()` / `getGpuHeadroom()` 与 `PowerManager.getThermalHeadroom()` 的组合策略还没有在章节中展开。external-review 已命中该方向，本轮 Task 9 已复核 AOSP android16-qpr2 中 API 存在，但仍需要补齐厂商支持范围、返回值稳定性和调优策略。

### 重要程度
高

### 建议研究方向
- 复核 Android 16 API 文档与 AOSP `SystemHealthManager`、`CpuHeadroomParams`、`GpuHeadroomParams` 的边界条件。
- 采样不同 SoC 上 [0,100] headroom 的含义、NaN/UnsupportedOperationException 出现场景、最小轮询间隔。
- 建立 thermal headroom（热余量）与 CPU/GPU headroom（算力余量）的联合降载策略。

### 关联章节
5.4, 5.5, 5.9, 8.9

### 外部 review 来源
2026-04-28-15-ch05-05-thermal-external-review.md

---

## [2026-04-29] 8.2 App 启动全流程 — 知识盲区

### 盲区描述
Unfrozen Cached Process 竞合

### 重要程度
中

### 建议研究方向
研究 Android 14+ 缓存进程解冻对新进程 fork 时的 CPU 调度优先级干扰

### 关联章节
- 8.2

### 外部 review 来源
2026-04-29-10-8.2-external-review.md


## [2026-04-29] 8.3 启动优化策略 — 知识盲区

### 盲区描述
Startup Profile 与重打包冲突

### 重要程度
高

### 建议研究方向
验证加固或重打包工具是否会破坏 Startup Profile 生成的物理 DEX 布局

### 关联章节
- 8.3

### 外部 review 来源
2026-04-29-10-8.3-external-review.md


## [2026-04-29] 8.4 其他响应速度场景 — 知识盲区

### 盲区描述
AutoFDO 对自定义 HIDL 的增益

### 重要程度
中

### 建议研究方向
验证内核级优化是否同样覆盖了三方 OEM 定义的硬件接口 Binder

### 关联章节
- 8.4

### 外部 review 来源
2026-04-29-10-8.4-external-review.md


## [2026-04-29] 8.4 其他响应速度场景 — 知识盲区

### 盲区描述
触摸预测在 240Hz 采样下的精度

### 重要程度
高

### 建议研究方向
研究高刷触控屏对 ML 预测算法准确率的影响

### 关联章节
- 8.4

### 外部 review 来源
2026-04-29-10-8.4-external-review.md


## [2026-04-29] 8.5 案例集 — 知识盲区

### 盲区描述
R8 Full Mode 与 Kotlin 协程内联冲突

### 重要程度
中

### 建议研究方向
验证在激进模式下，协程 `Continuation` 状态机被 R8 合并后是否会影响 Method Trace 的可读性

### 关联章节
- 8.5

### 外部 review 来源
2026-04-29-10-8.5-external-review.md


## [2026-04-29] 8.7 Baseline Profiles 与编译优化实践 — 知识盲区

### 盲区描述
SDM 文件签名绑定逻辑

### 重要程度
高

### 建议研究方向
研究云端生成的 `.odex` 如何与本地生成的 `base.apk` 保持签名一致性验证

### 关联章节
- 8.7

### 外部 review 来源
2026-04-29-10-8.7-external-review.md


## [2026-04-29] 8.7 Baseline Profiles 与编译优化实践 — 知识盲区

### 盲区描述
16KB 下的 DEX 预读算法

### 重要程度
中

### 建议研究方向
验证 Android 15 内核读取 16KB 对齐的 DEX 时是否存在类似 fadvise 的提前加载策略

### 关联章节
- 8.7

### 外部 review 来源
2026-04-29-10-8.7-external-review.md


## [2026-04-29] 8.8 Android 多媒体管线性能 — 知识盲区

### 盲区描述
BLE Audio 调度优先级

### 重要程度
高

### 建议研究方向
研究 `audioserver` 如何在 BLE 链路下为空间音频分配实时调度配额

### 关联章节
- 8.8

### 外部 review 来源
2026-04-29-10-8.8-external-review.md


## [2026-04-29] 8.8 Android 多媒体管线性能 — 知识盲区

### 盲区描述
Codec2 与 16KB 对齐的副作用

### 重要程度
中

### 建议研究方向
验证在 16KB 页面下，小分辨率（如 360p）预览流的内存碎片浪费情况

### 关联章节
- 8.8

### 外部 review 来源
2026-04-29-10-8.8-external-review.md


## [2026-04-29] 8.10 ProfilingManager 系统触发式性能追踪 — 知识盲区

### 盲区描述
ANOMALY 阈值的动态下发

### 重要程度
高

### 建议研究方向
研究 `device_config` (Mainline Profiling namespace) 是否允许云端动态调整触发异常的 CPU/内存阈值

### 关联章节
- 8.10

### 外部 review 来源
2026-04-29-11-8.10-external-review.md


## [2026-04-29] 8.10 ProfilingManager 系统触发式性能追踪 — 知识盲区

### 盲区描述
Redacted Heap Dump 的内容

### 重要程度
中

### 建议研究方向
验证系统触发的 Heap Dump 是否会剔除 String 值等敏感业务数据

### 关联章节
- 8.10

### 外部 review 来源
2026-04-29-11-8.10-external-review.md


## [2026-04-29] 8.9 Android 游戏性能与 Game Mode/State API — 知识盲区

### 盲区描述
ARR 下的 Swappy 步进稳定性

### 重要程度
高

### 建议研究方向
验证在 60Hz 到 120Hz 的 ARR 跳变瞬间，Swappy 内部时间戳插值器的漂移率

### 关联章节
- 8.9

### 外部 review 来源
2026-04-29-11-8.9-external-review.md


## [2026-04-29] 8.9 Android 游戏性能与 Game Mode/State API — 知识盲区

### 盲区描述
WebView 与 Game Mode 资源互斥

### 重要程度
中

### 建议研究方向
研究 Android 15 下 `DEFAULT_TO_WEB` 意图是否会抢占 Game Mode 预留的 CPU 大核核心

### 关联章节
- 8.9

### 外部 review 来源
2026-04-29-11-8.9-external-review.md


## [2026-04-29] 9.2 ANR 类型与触发条件 — 知识盲区

### 盲区描述
AnrTimer 与 BPF 结合的预研

### 重要程度
中

### 建议研究方向
验证 Android 17 是否会利用 eBPF 在内核直接挂起超时的 SocketPair 发送

### 关联章节
- 9.2

### 外部 review 来源
2026-04-29-11-9.2-external-review.md


## [2026-04-29] 9.3 ANR 分析方法 — 知识盲区

### 盲区描述
Redacted Trace 剥离逻辑

### 重要程度
高

### 建议研究方向
研究系统在生成 redacted 版本的 traces.txt 时，如何保护 method 名混淆后的原始映射

### 关联章节
- 9.3

### 外部 review 来源
2026-04-29-11-9.3-external-review.md


## [2026-04-29] 9.4 特殊场景的 ANR — 知识盲区

### 盲区描述
ShortService 的 CPU 份额限制

### 重要程度
中

### 建议研究方向
研究 Android 15 下 `shortService` 触发 `onTimeout` 后，系统是否会立即对该进程执行 CPU Throttling

### 关联章节
- 9.4

### 外部 review 来源
2026-04-29-11-9.4-external-review.md


## [2026-04-29] 9.5 案例集 — 知识盲区

### 盲区描述
freezer 对 ProfilingManager 的干扰

### 重要程度
高

### 建议研究方向
研究当应用被冻结时，ProfilingManager 是否能成功回传结果文件

### 关联章节
- 9.5

### 外部 review 来源
2026-04-29-11-9.5-external-review.md


## [2026-04-29] 9.6 Notification 性能与 ANR — 知识盲区

### 盲区描述
NLS 进程的冻结豁免

### 重要程度
高

### 建议研究方向
验证活跃的 `NotificationListenerService` 是否会被 Android 14+ 的 Freezer 机制豁免冻结

### 关联章节
- 9.6

### 外部 review 来源
2026-04-29-11-9.6-external-review.md


## [2026-04-29] 9.7 ANR 非技术故障诊断 — 知识盲区

### 盲区描述
BPF 针对 InputChannel 的监控

### 重要程度
中

### 建议研究方向
研究 Android 17 是否开放了基于 BPF 的 Input 事件全链路延迟监控给三方 App

### 关联章节
- 9.7

### 外部 review 来源
2026-04-29-11-9.7-external-review.md

## [2026-04-29] 10.2 内存泄漏 — 知识盲区

### 盲区描述
DeliQueue 对引用处理的收益；16KB Page 对 Heap Dump 体积影响（验证 .hprof 是否膨胀 10%+）

### 重要程度
高

### 建议研究方向
- 深入研究上述盲区，补充版本差异与源码证据

### 关联章节
10.2, 10.6

### 外部 review 来源
- Gemini 外部 review (2026-04-29)


## [2026-04-29] 10.3 内存持续增长 — 知识盲区

### 盲区描述
ProfilingManager 是否可根据 RSS 斜率动态触发 heap profile；16KB 下 ZRAM 压缩比变化

### 重要程度
高

### 建议研究方向
- 深入研究上述盲区，补充版本差异与源码证据

### 关联章节
10.3, 10.4

### 外部 review 来源
- Gemini 外部 review (2026-04-29)


## [2026-04-29] 10.4 低内存对系统性能的影响 — 知识盲区

### 盲区描述
ZRAM 重压缩对热页锁定机制（Android 15 Multi-Comp 豁免逻辑）；MGLRU 在 16KB 下精度误差

### 重要程度
高

### 建议研究方向
- 深入研究上述盲区，补充版本差异与源码证据

### 关联章节
10.4, 10.5

### 外部 review 来源
- Gemini 外部 review (2026-04-29)


## [2026-04-29] 10.5 案例集 — 知识盲区

### 盲区描述
dmabuf_dump 的权限收紧（Android 16 SELinux 审计隔离）；ZRAM 16KB 解压抖动对 AudioFlinger 调度影响

### 重要程度
高

### 建议研究方向
- 深入研究上述盲区，补充版本差异与源码证据

### 关联章节
10.3, 10.5

### 外部 review 来源
- Gemini 外部 review (2026-04-29)


## [2026-04-29] 10.6 内存抖动与频繁 GC — 知识盲区

### 盲区描述
16KB Page 对 TLAB 填充率影响（ART 是否自动调大 TLAB 默认尺寸）；DeliQueue 与 GC 回调优先级

### 重要程度
高

### 建议研究方向
- 深入研究上述盲区，补充版本差异与源码证据

### 关联章节
10.2, 10.6

### 外部 review 来源
- Gemini 外部 review (2026-04-29)


## [2026-04-29] 10.7 SQLite/Room 数据库性能优化 — 知识盲区

### 盲区描述
Room 2.8+ Kotlin KSP 生成效率（启动阶段类加载耗时缩减率）；F2FS 原子写与 WAL 冲突

### 重要程度
高

### 建议研究方向
- 深入研究上述盲区，补充版本差异与源码证据

### 关联章节
10.7

### 外部 review 来源
- Gemini 外部 review (2026-04-29)


## [2026-04-29] 11.1 Android 功耗模型 — 知识盲区

### 盲区描述
uclamp 对 PAS 的干预（EAS 2.0 下 uclamp_min 是否被功耗红线覆盖）；VIRTUAL-SKIN 映射精度

### 重要程度
高

### 建议研究方向
- 深入研究上述盲区，补充版本差异与源码证据

### 关联章节
11.1

### 外部 review 来源
- Gemini 外部 review (2026-04-29)


## [2026-04-29] 11.2 App 耗电优化 — 知识盲区

### 盲区描述
setPowerEfficiencyHint 的 CPU 亲和度（是否迁移到 E-Core Island）；dataSync 配额重置粘性

### 重要程度
高

### 建议研究方向
- 深入研究上述盲区，补充版本差异与源码证据

### 关联章节
11.2

### 外部 review 来源
- Gemini 外部 review (2026-04-29)


## [2026-04-29] 11.3 系统级功耗优化 — 知识盲区

### 盲区描述
归档应用的 FGS 唤醒豁免（External Binder 强制唤醒）；AppStandbyController ML 输入（内存回收频率作为桶降级特征）

### 重要程度
高

### 建议研究方向
- 深入研究上述盲区，补充版本差异与源码证据

### 关联章节
11.3

### 外部 review 来源
- Gemini 外部 review (2026-04-29)


## [2026-04-29] 11.4 案例集（功耗） — 知识盲区

### 盲区描述
dataSync 预算在多用户模式下的隔离；16KB Page 对 BatteryStats 持久化压力

### 重要程度
中

### 建议研究方向
- 深入研究上述盲区，补充版本差异与源码证据

### 关联章节
11.2, 11.4

### 外部 review 来源
- Gemini 外部 review (2026-04-29)

## [2026-04-29] 7.10 图片加载与 Bitmap 性能优化 — 知识盲区

### 盲区描述
Ultra HDR / Gainmap 图片的内存与显存模型仍未闭环。AOSP Bitmap.java 已提供 hasGainmap()/getGainmap()/setGainmap()，BitmapFactory.cpp 会解码 gainmap；正文仍按 SDR `宽×高×4` 估算，缺少 gainmap bitmap、metadata、PSS/GPU 显存与回收时机的边界。

### 重要程度
高

### 建议研究方向
- 复核 Android 14-16 BitmapFactory.cpp 中 getGainmapAndroidCodec()/decodeGainmap() 对 sampleSize、density scale、hardware allocator 的处理。
- 设计 Perfetto/heapprofd/Graphics Memory 实测，比较同一 JPEG 在有/无 Gainmap、Hardware/Software Bitmap 下的 Native heap、PSS、GPU memory 与 fd 变化。
- 明确 `Bitmap.setGainmap(null)` 的适用条件：只在业务接受 SDR 降级时作为低端机兜底。

### 关联章节
- 7.10

### 外部 review 来源
- external-review 已命中：logs/external-review/archive/2026-04-29-09-7.10-external-review.md



## [2026-04-29] 18.1 渲染链路分类与选择矩阵 — 知识盲区

### 盲区描述
HardwareBufferRenderer 离屏渲染器产生的显存碎片归属与内存隔离机制未覆盖。AVP (Advanced Video Pipeline) 对渲染链路的选择影响未验证。

### 重要程度
高

### 建议研究方向
- 研究离屏渲染器产生的显存碎片是否归入宿主进程的 smaps 统计
- 验证 Android 16 AVP 是否会强制视频层脱离 BLAST 并行路径

### 关联章节
- 18.1
- 18.2
- 18.3

### 外部 review 来源
- Gemini 外部 review (2026-04-29)

## [2026-04-29] 18.2 Android View 标准链路 — 知识盲区

### 盲区描述
Non-blocking Sync 的触发阈值机制未研究：HardwareRenderer 如何根据 ADPF Hint Session 动态决定是否开启非阻塞模式。AVP 事务优先级的内核保障未验证。

### 重要程度
高

### 建议研究方向
- 研究 HardwareRenderer 与 ADPF Hint Session 的交互决定非阻塞模式开启的阈值
- 验证 Android 16 是否通过 cgroup 提升了视频解耦 Transaction 的 Binder 调度优先级

### 关联章节
- 18.1
- 18.2

### 外部 review 来源
- Gemini 外部 review (2026-04-29)

## [2026-04-29] 18.3 Android View 软件渲染链路 — 知识盲区

### 盲区描述
Android 16 SkTaskGroup 软件渲染辅助线程与 cgroup 的绑定策略未研究。16KB Page 环境下 copyBlt 带宽峰值的功耗影响未验证。

### 重要程度
高

### 建议研究方向
- 研究 Android 16 软件渲染辅助线程是否被限制在特定能效核心（LITTLE Cores）运行
- 验证大页面环境下 Dirty Rect 拷贝是否会触发更宽总线周期导致瞬时功耗尖峰

### 关联章节
- 18.2
- 18.3

### 外部 review 来源
- Gemini 外部 review (2026-04-29)

## [2026-04-29] 5.1 Linux 进程调度基础 — 知识盲区

### 盲区描述
EEVDF 的 vlag/lag 在 Android common 6.6/6.12 默认 ftrace 中没有直接暴露。章节当前把 `sched_eevdf_entity` 写成可直接采集的 Perfetto 事件，需要重新研究 stock 内核与厂商内核下可用的观测路径。

### 重要程度
高

### 建议研究方向
- 复核 Android common `include/trace/events/sched.h` 与 vendor kernel 是否有私有 EEVDF tracepoint。
- 如果没有 tracepoint，评估 BPF/kprobe/tracefs 自定义采集 vlag 的可行性与权限边界。
- 建立退化方案：用 `sched_switch`、`sched_wakeup`、Runnable duration、priority、cpu frequency 近似判断调度不公。

### 关联章节
5.1, 5.2, 7.3

## [2026-04-29] 9.5 案例集 — 知识盲区

### 盲区描述
ANR 案例集缺少 Android 15/16 Cached Apps Freezer 对 Gesture Monitor 的版本复核，也缺少 Android 11+ `ApplicationExitInfo#getTraceInputStream()` 在 APM 端侧采集中的位置。

### 重要程度
高

### 建议研究方向
- 复核 Android 15/16 freezer、InputDispatcher、Gesture Monitor 相关源码或设备日志，确认该类冻结 ANR 是否仍可能出现。
- 梳理 `ActivityManager#getHistoricalProcessExitReasons()`、`ApplicationExitInfo.REASON_ANR`、`getTraceInputStream()` 的版本、权限、返回内容和体积限制。
- 对比官方退出信息、Looper 消息历史、event log、Perfetto trace 四类证据在聚合归因中的分工。

### 关联章节
9.3, 9.5, 19.x APM 端侧采集


## [2026-04-29] 18.10 18.10 SurfaceControl API 深入 — 知识盲区

### 盲区描述
ASurfaceControl_readFromParcel 的生命周期锁定

### 重要程度
高

### 建议研究方向
研究在反序列化后，若原进程释放了句柄，目标进程的引用是否能物理上锁住 SurfaceFlinger 侧的 Layer 内存

### 关联章节
- 18.10

### 外部 review 来源
- 2026-04-29-11-18.10-external-review.md


## [2026-04-29] 18.10 18.10 SurfaceControl API 深入 — 知识盲区

### 盲区描述
InputTransferToken 在 NDK 的自动感知

### 重要程度
中

### 建议研究方向
验证 Android 16 针对跨进程 Layer 的触摸焦点转移是否实现了“事件自适应重路由”

### 关联章节
- 18.10

### 外部 review 来源
- 2026-04-29-11-18.10-external-review.md


## [2026-04-29] 18.5 18.5 Android View 多窗口链路 — 知识盲区

### 盲区描述
TaskFragment 的 Transaction 频率限制

### 重要程度
中

### 建议研究方向
研究 Android 15 对 Activity Embedding 的窗口变换频率是否执行了系统级限流

### 关联章节
- 18.5

### 外部 review 来源
- 2026-04-29-11-18.5-external-review.md


## [2026-04-29] 18.5 18.5 Android View 多窗口链路 — 知识盲区

### 盲区描述
跨进程多窗口的 Vsync 相位对齐

### 重要程度
高

### 建议研究方向
验证在 Desktop Mode 下，不同进程的 `Choreographer` 唤醒相位是否存在动态偏移以平抑 SF 负载

### 关联章节
- 18.5

### 外部 review 来源
- 2026-04-29-11-18.5-external-review.md


## [2026-04-29] 18.6 18.6 SurfaceView 直出链路 — 知识盲区

### 盲区描述
Low Latency Input 与 ADPF 联动

### 重要程度
高

### 建议研究方向
研究开启直连输入后，系统是否会自动提升 Producer 线程的 cgroup 调度优先级

### 关联章节
- 18.6

### 外部 review 来源
- 2026-04-29-11-18.6-external-review.md


## [2026-04-29] 18.6 18.6 SurfaceView 直出链路 — 知识盲区

### 盲区描述
16KB 下的像素重采样开销

### 重要程度
中

### 建议研究方向
验证当 SurfaceView 尺寸非 16 像素对齐时，HWC Scaler 是否会产生额外的线性过滤开销

### 关联章节
- 18.6

### 外部 review 来源
- 2026-04-29-11-18.6-external-review.md


## [2026-04-29] 18.7 18.7 TextureView 合成链路 — 知识盲区

### 盲区描述
AVP 对 TextureView 采样的旁路优化

### 重要程度
高

### 建议研究方向
研究 Android 16 Advanced Video Pipeline 是否支持将 TextureView 的内容直接在合成侧进行 YUV-to-RGB 直出

### 关联章节
- 18.7

### 外部 review 来源
- 2026-04-29-11-18.7-external-review.md


## [2026-04-29] 18.7 18.7 TextureView 合成链路 — 知识盲区

### 盲区描述
16KB 下的 EGLImage 映射抖动

### 重要程度
中

### 建议研究方向
验证在大页面环境下，跨进程共享 Buffer 的 `fd` 导入是否会引起更频繁的内核页表锁竞争

### 关联章节
- 18.7

### 外部 review 来源
- 2026-04-29-11-18.7-external-review.md


## [2026-04-29] 18.8 18.8 OpenGL ES 渲染链路 — 知识盲区

### 盲区描述
HardwareBufferRenderer 与 GLES 共享上下文的锁竞争

### 重要程度
高

### 建议研究方向
研究当 UI 渲染与 GLES 渲染并发竞争同一个 GPU Context 时的内部互斥粒度

### 关联章节
- 18.8

### 外部 review 来源
- 2026-04-29-11-18.8-external-review.md


## [2026-04-29] 18.8 18.8 OpenGL ES 渲染链路 — 知识盲区

### 盲区描述
ARR 下的 EGLSync 漂移

### 重要程度
中

### 建议研究方向
验证在 90Hz 到 120Hz 切换瞬间，`eglClientWaitSyncKHR` 的超时计算是否需要根据 `VsyncPeriod` 进行动态补偿

### 关联章节
- 18.8

### 外部 review 来源
- 2026-04-29-11-18.8-external-review.md


## [2026-04-29] 18.9 18.9 Vulkan 原生渲染管线 — 知识盲区

### 盲区描述
Dynamic Rendering 与 ANGLE 的协作效率

### 重要程度
中

### 建议研究方向
研究 Android 15 下 ANGLE 翻译层利用动态渲染绕过旧版 GLES FBO 限制的性能增益

### 关联章节
- 18.9

### 外部 review 来源
- 2026-04-29-11-18.9-external-review.md


## [2026-04-29] 18.9 18.9 Vulkan 原生渲染管线 — 知识盲区

### 盲区描述
AVP 对硬件光追 (Ray Tracing) 的准入要求

### 重要程度
高

### 建议研究方向
验证 Android 16 AVP 是否已将基本的光追 Extension 纳入 `minimums` 范畴

### 关联章节
- 18.9

### 外部 review 来源
- 2026-04-29-11-18.9-external-review.md

## [2026-04-29] 18.11 ANGLE（GLES-over-Vulkan 翻译层） — 知识盲区

### 盲区描述
ANGLE 针对 Vulkan 1.3 扩展的利用上限

### 重要程度
中

### 建议研究方向
- 研究 Android 15 下 ANGLE 是否已开始利用 maintenance4 进一步精简资源绑定开销

### 关联章节
- 18.11

### 外部 review 来源
- 2026-04-29-11-18.11-external-review.md


## [2026-04-29] 18.11 ANGLE（GLES-over-Vulkan 翻译层） — 知识盲区

### 盲区描述
AVP 16 对 ANGLE 版本的物理锁定

### 重要程度
高

### 建议研究方向
- 验证 Android 16 是否强制要求 com.android.angle 库必须具备特定的 NDK 兼容性标识

### 关联章节
- 18.11

### 外部 review 来源
- 2026-04-29-11-18.11-external-review.md


## [2026-04-29] 18.12 Flutter 渲染管线 — 知识盲区

### 盲区描述
Impeller 针对 AVP 视频层的绕过

### 重要程度
高

### 建议研究方向
- 研究当 Flutter 页面包含视频内容时，Impeller 是否会主动退避以让出 HWC Overlay 名额给 AVP

### 关联章节
- 18.12

### 外部 review 来源
- 2026-04-29-11-18.12-external-review.md


## [2026-04-29] 18.12 Flutter 渲染管线 — 知识盲区

### 盲区描述
16KB 下的 Skia 软渲染退化

### 重要程度
中

### 建议研究方向
- 验证在 16KB 环境下，低配设备回退到 Skia 软件后端后的物理页内存压力是否导致更频繁的 GC

### 关联章节
- 18.12

### 外部 review 来源
- 2026-04-29-11-18.12-external-review.md

<!-- 8.1-2026-04-30-uil-motionpredictor -->
## [2026-04-30] 8.1 响应速度原理 — 知识盲区

### 盲区描述
Android 端“UIL / User Interaction Latency”的官方状态、Android Vitals 归属、Play 排名影响，以及 MotionPredictor API 与系统级触摸预测的边界仍需一手资料确认。

### 重要程度
高

### 建议研究方向
- 查 developer.android.com / source.android.com 是否存在 UIL 正式指标定义、P99 200ms 口径和 Play Console 展示入口
- 对比 API 34-37 `android.view.MotionPredictor` 文档、AOSP native MotionPredictor 实现、设备输入源支持范围
- 用 Perfetto 验证真实事件与预测事件在 App/RenderThread/SurfaceFlinger 侧的可观测信号

### 关联章节
8.1, 3.4, 13.8, 18.19

### 来源
Task9 deep review: logs/deep-review/2026-04-30-05-deep-review.md

<!-- 8.3-2026-04-30-16kb-cow-startup -->
## [2026-04-30] 8.3 启动优化策略 — 知识盲区

### 盲区描述
16KB page size 对启动期 SDK 配置写入、Zygote 继承页 COW、minor/major page fault 和 PSS/RSS 的实际影响缺少可复核数据。

### 重要程度
高

### 建议研究方向
- 设计 4KB/16KB 页设备或模拟环境的冷启动对比，记录 minor faults、major faults、RSS/PSS、CPU time
- 区分普通堆写入、Zygote 继承页首次写入、mmap 文件页写入、SharedPreferences/DataStore 写入
- 结合 §4.7 16KB Page Size 与 §1.11 Zygote 机制补源码和实验条件

### 关联章节
8.3, 4.7, 1.11, 6.5

### 来源
Task9 deep review: logs/deep-review/2026-04-30-05-deep-review.md

## [2026-04-30] 12.1 APK 体积优化 — 知识盲区

### 盲区描述
resources.arsc 16KB 映射对齐：在大页面环境下，资源表文件是否需要物理 16KB 对齐以实现零拷贝映射

### 重要程度
中

### 建议研究方向
- 研究 16KB page 环境下 resources.arsc 的 mmap 行为
- 对比 4KB/16KB 设备上的资源加载性能差异

### 关联章节
- 12.1

### 外部 review 来源
- 2026-04-29-11-12.1-external-review.md

## [2026-04-30] 12.1 APK 体积优化 — 知识盲区

### 盲区描述
Startup Profile 与重打包冲突：加固工具是否会破坏 AGP 8.5+ 生成的针对 16KB 优化的物理 DEX 布局

### 重要程度
高

### 建议研究方向
- 验证主流加固方案（360、梆梆、乐固）对 Baseline/Startup Profile DEX 布局的兼容性
- 测试加固后冷启动性能是否有回退

### 关联章节
- 12.1

### 外部 review 来源
- 2026-04-29-11-12.1-external-review.md

## [2026-04-30] 12.2 网络性能优化 — 知识盲区

### 盲区描述
QUIC 连接迁移在 16KB 页表下的稳定性：IP 地址跳变触发内核页表重新映射时，Cronet 内部 Buffer 挂载是否存在微秒级阻塞

### 重要程度
中

### 建议研究方向
- 研究 16KB page 环境下 QUIC 连接迁移的时延特征
- Perfetto 中观察 Cronet 内部 Buffer 状态

### 关联章节
- 12.2

### 外部 review 来源
- 2026-04-29-11-12.2-external-review.md

## [2026-04-30] 12.2 网络性能优化 — 知识盲区

### 盲区描述
BPF 带宽估计在虚拟化网络（VPN）下的精度：VpnService 环境下物理带宽估计值是否会因封包开销产生虚高

### 重要程度
高

### 建议研究方向
- 验证 VpnService 环境下 getLinkDownstreamBandwidthKbps 返回值与实际带宽的关系
- 设计 ABR 调度在 VPN 场景下的降级策略

### 关联章节
- 12.2

### 外部 review 来源
- 2026-04-29-11-12.2-external-review.md

## [2026-04-30] 2.8 过度绘制 — 移动端 TBR/On-Chip Memory 成本模型

### 盲区描述
当前章节把过度绘制成本主要写成像素数和外部内存带宽线性增加，缺少移动端 tile-based renderer 下 on-chip tile memory、fragment shading、texture fetch、blend、depth/stencil 与最终 resolve 的分层成本模型。

### 重要程度
高

### 建议研究方向
- 核对 ARM Mali / Qualcomm Adreno / Imagination PowerVR 的公开 overdraw、tile memory、Early-Z、alpha blending 文档。
- 用 AGI / Perfetto GPU counter 在一台 Adreno 与一台 Mali 设备上对比不透明层、半透明层、复杂 shader 的 overdraw 成本。
- 明确哪些成本会落到外部内存带宽，哪些只体现在 tile memory / fragment work / GPU busy。

### 关联章节
- 2.8
- 2.10
- 18.9

## [2026-04-30] 12.3 网络性能深入：连接池、TLS 与传输优化 — 知识盲区

### 盲区描述
1. **ECH 在国内运营商网关的截断率**：2026 年 Encrypted Client Hello 在移动 5G 网络下的握手成功率及降级耗时尚未梳理。
2. **预测性解析对蜂窝网络数据量的副作用**：Android 16 系统级预测性 DNS 解析是否会因过度预取导致用户月度流量异常消耗未验证。

### 重要程度
中 / 低

### 建议研究方向
- 研究 2026 年 ECH 在国内主流运营商 5G 网关的截断率及降级表现
- 验证 Predictive DNS Prefetching 在蜂窝网络下的流量开销增量

### 关联章节
- 12.3
- 12.4

### 外部 review 来源
- Gemini 外部 review (2026-04-29-11-12.3-external-review.md)

## [2026-04-30] 12.4 Android 网络安全与 TLS 性能优化 — 知识盲区

### 盲区描述
1. **ECH 与部分企业防火墙的碰撞**：2026 年主流硬件防火墙对 ECH 加密 ClientHello 的策略性拦截率及降级表现不明。
2. **HPKE SPI 对国产加密算法（SM2/4）的支持**：Android 17 的 HpkeSpi 是否已通过子模块支持我国商用密码标准（SM2/SM4）未确认。

### 重要程度
中 / 高

### 建议研究方向
- 研究 2026 年主流企业级防火墙对 ECH ClientHello 的拦截策略及 TLS 降级行为
- 核验 Android 17 HpkeSpi 对国密算法（SM2/SM4）的支持状态

### 关联章节
- 12.4
- 12.3

### 外部 review 来源
- Gemini 外部 review (2026-04-29-11-12.4-external-review.md)

## [2026-04-30] 7.11 WebView 渲染性能与优化 — WebView 渲染提交路径与 16KB RELRO 边界

### 盲区描述
当前章节把 GLFunctor、独立 Layer、Viz、GPU service、SurfaceControl / ASurfaceControl、BufferQueue 与 SurfaceFlinger 的关系混在一起，缺少按 Android 版本、WebView provider 版本和设备 trace 区分的渲染提交路径。16KB page size 下 WebView RELRO 对齐 / PSS 共享失效也只有 [待验证] 结论，缺 AOSP 修复点和实测证据。

### 重要程度
高

### 建议研究方向
- 复核 Chromium `android_webview` 渲染相关源码与 release CL，区分 GLFunctor/HWUI 同窗口合成、SurfaceControl/BufferQueue 参与、renderer multiprocess 与 GPU service in-process 的边界。
- 在 Android 10 / 11 / 14 / 16 设备上抓 WebView 滚动 trace，对比 App RenderThread、`CrRendererMain`、`VizCompositorThread`、`CrGpuMain`、SurfaceFlinger layer 列表和 FrameTimeline。
- 对 4KB / 16KB page-size 设备分别测 WebView 首开 native load、major/minor fault、RELRO shared/private mapping、PSS 增量，确认是否存在可复现的 RELRO 对齐失效。

### 关联章节
- 7.11
- 2.9
- 2.10
- 18.13
- 13.7

## [2026-05-01] 1.3 进程模型与生命周期管理 — 知识盲区

### 盲区描述
AVF Terminal / pVM 与 Phantom Process Killer 的边界尚未回源。章节把 Android 16 AVF Terminal 写成大量子进程场景的“官方规避路径”，但需要确认它是否只是 Terminal/pVM 产品形态不受宿主 phantom process quota 约束，还是可被普通第三方 App 作为通用子进程保活方案使用。

### 重要程度
高

### 建议研究方向
- 核对 Android 16 AVF Terminal / Linux Terminal 的官方文档、feature flag 与公开 API 边界。
- 核对 `PhantomProcessList` 对宿主 App fork 子进程的统计路径，确认 pVM 内部进程是否完全不可见，以及这是否能作为开发建议。
- 给出“可用于开发者测试环境”和“可作为业务 App 方案”的边界判断。

### 关联章节
1.3、5.8、16.x


## [2026-05-01] 2.9 渲染机制的版本演进 — 知识盲区

### 盲区描述
Graphite / Early-Z 在 Android 16 HWUI 中的真实启用路径、设备范围、系统属性或 feature flag、Perfetto/Skia backend 观测方法尚未建立。当前正文把 Graphite 部署与不透明过度绘制自动消除连成强结论，缺少 AOSP 与设备侧证据。

### 重要程度
高

### 建议研究方向
- 核对 android-16.0.0_r1 与 main 中 HWUI / Skia Graphite 后端的源码入口、编译开关、运行时属性。
- 在支持 Android 16 的参考设备上记录 Skia backend、RenderThread slice、GPU overdraw / Early-Z 可观测指标。
- 明确 Graphite 与 SkiaVulkan / Ganesh 的关系，拆分“能力存在”“系统启用”“默认启用”三个层级。

### 关联章节
2.9, 2.10, 2.15, 18.9

## [2026-05-01] 2.16 Sync Fence 框架与帧同步机制 — 知识盲区

### 盲区描述
Vulkan Timeline Semaphore 与 Android native fence / sync_file fd 的 interop 边界尚未写清。当前正文把 Vulkan 内部 timeline 计数器模型直接推导为 acquire / release / present fd 的替代方案，并进一步写到 Android 17 去 fd 化路线，证据链不足。

### 重要程度
高

### 建议研究方向
- 核对 Vulkan timeline semaphore、external semaphore fd、native fence fd、sync_file fd 在 Android 图形栈中的转换关系。
- 追踪 SkiaVulkanPipeline / VulkanManager createReleaseFence、ANativeWindow queueBuffer、SurfaceFlinger latchBuffer、HWC present/release fence 的端到端源码链。
- 查 Android 17 CDD / source.android.com / AOSP tag 是否存在“去 fd 化”正式路线；没有公开依据时改成待验证展望。

### 关联章节
2.13, 2.16, 2.17, 18.9


## [2026-05-02] 13.2 Trace 抓取 — Profiling 数据源权限与版本边界

### 盲区描述
Perfetto 抓取章节已经覆盖 heapprofd、java_hprof 与 linux.perf 配置，但缺少量产 user build、userdebug/eng、profileable/debuggable manifest 标记之间的权限差异说明。尤其是 CPU callstack sampling 官方 quickstart 要求 Android T+，且目标 App 需 profileable/debuggable 或设备为 userdebug/eng；heapprofd 在 user build 上也只能分析 debuggable/profileable App。

### 重要程度
高

### 建议研究方向
- 复核 Perfetto heapprofd、java_hprof、linux.perf/cpu_profile 的 Android 版本下限与权限前提。
- 补充量产 user 设备上抓取失败的典型错误表现、fallback 工具与推荐排查步骤。
- 建立 TraceConfig 数据源支持矩阵，覆盖 Android 10-16。

### 关联章节
13.2, 13.3, 13.5, 14.1


## [2026-05-03] 10.2 内存泄漏 — 知识盲区

### 盲区描述
Android 17 / ART generational CMC 对 WeakReference、ReferenceQueue 入队时机与 LeakCanary 检测延迟的真实影响尚未建立一手证据；Android 15+ 是否存在 LeakCanary ContentProvider 自动初始化静默失败，也缺少官方文档、issue 或复现条件。

### 重要程度
高

### 建议研究方向
- 阅读 ART reference processing / concurrent copying / generational CMC 相关提交，确认 Android 17 相比 Android 10+ generational CC 的真实变化。
- 用同一测试 App 在 Android 15/16/17 设备或模拟器上对比 WeakReference 入队延迟、GC 类型日志、LeakCanary watchDuration 命中率。
- 查证 LeakCanary AppWatcherInstaller 在 Android 15+、多进程、direct boot、instant app、严格沙箱场景下的已知 issue 与 manualInstall API 边界。

### 关联章节
10.2, 4.3, 10.1

## [2026-05-04] 11.2 App 耗电优化 — GNSS 硬件围栏卸载与功耗量化

### 盲区描述
正文涉及 Geofencing 的 GNSS hardware offload、Android 版本线和功耗收益，但当前缺少可复核的一手资料与实测条件。需要确认 API/能力暴露、HAL 实现、Play services FLP 路径和 vendor 芯片卸载之间的边界。

### 重要程度
高

### 建议研究方向
- 核对 `android.location.GnssCapabilities.hasGeofencing()`、GNSS AIDL/HIDL geofence 接口与 Android 版本线。
- 搜集 Pixel / Qualcomm / MediaTek / Broadcom 等公开资料中 hardware geofence 的功耗测试条件。
- 梳理 `dumpsys location` 中 hardware/software geofence 的可观测字段，给出 user build 可复核路径。

### 关联章节
11.2, 5.6, 11.1

## [2026-05-04] 1.16 Audio Pipeline 延迟与性能 — AAudio Power Saving Offloaded 边界

### 盲区描述
章节已写入 `AAUDIO_PERFORMANCE_MODE_POWER_SAVING_OFFLOADED`，但 API level、支持格式、设备覆盖、是否等价于 DSP 解码，以及 75% 功耗收益缺少可复核来源。

### 重要程度
高

### 建议研究方向
- 核对 Android 16/17 `aaudio/AAudio.h`、developer.android.com NDK Audio reference 与 API diff，确认 enum 引入版本和公开文档语义。
- 对照 `dumpsys audio` / output profile / `AAudioStream_getPerformanceMode()`，确认 offloaded path 的实际选路与回退条件。
- 如保留功耗数字，补设备型号、音频格式、播放时长、AP sleep 时间、功耗采样方法和对照组。

### 关联章节
1.16、5.6、16.5

## [2026-05-04] 5.5 Thermal 管控 — 知识盲区

### 盲区描述
16KB page size 是否能在真实设备上延迟 thermal throttling，当前缺少一手 A/B trace 和功耗数据。

### 重要程度
高

### 建议研究方向
- 同 SoC / 同 ROM 条件下采集 4KB 与 16KB 模式的 thermal_zone、CPU/GPU freq、Frame Timeline、power rail 数据
- 记录环境温度、散热条件、负载脚本、time-to-throttle 与稳定帧率，确认 4.5% MMU 功耗估算是否能转化为整机热收益
- 区分应用启动、大内存分配、游戏持续负载三类场景，避免把单点功耗数据泛化到整机温控

### 关联章节
4.7, 5.4, 5.12, 8.9

## [2026-05-04] 9.5 案例集 — 知识盲区

### 盲区描述
缺少可公开复核的 Binder 线程池耗尽 / 同步 Binder 回调导致 ANR 的完整案例素材。

### 重要程度
高

### 建议研究方向
- 收集包含 am_anr、主线程栈、Binder 线程池栈、对端进程栈、binder transaction 线索的真实案例
- 复核 DEFAULT_MAX_BINDER_THREADS、joinThreadPool、同步回调链路在 Android 14-16 的版本边界
- 沉淀修复方案：异步化、拆分锁、超时降级、避免跨进程同步回调

### 关联章节
1.4, 9.2, 9.3, 9.4

## [2026-05-06] 17.2 SoC 平台差异 — Oryon 微架构资料边界

### 盲区描述
Snapdragon 8 Elite Oryon 的 L1/L2 cache 拓扑、共享层级与访问延迟缺少可复核的一手资料。当前正文存在把 Nuvia/前 Apple CPU 团队背景写成“与苹果 M 系列同源”，并可能把 Snapdragon X Elite 缓存拓扑误用于手机 8 Elite 的风险。

### 重要程度
高

### 建议研究方向
- 查 Qualcomm 官方白皮书、Hot Chips/ISSCC、芯片拆解或可信微架构 benchmark，区分 Snapdragon X Elite 与 Snapdragon 8 Elite。
- 如只能使用二手博客，删除具体 cache/latency 数字，保留为 [待验证] 背景。
- 用实机 PMU / perf / Perfetto 对缓存 miss、迁移前后 IPC 和频率策略做对照。

### 关联章节
17.2, 5.1, 5.2, 5.3

## [2026-05-06] 11.1 Android 功耗模型 — 知识盲区

### 盲区描述
PAS/Power-aware scheduling、ADPF/CPU-GPU headroom 与 ODPM/PowerStats 是否存在公开的一手耦合链路仍未确认。当前 AOSP 可确认的公开路径是 PowerStats/PowerMonitor 能量 snapshot、Power HAL headroom、PerformanceHintManager hint session；尚未找到 ODPM → ADPF/HintManagerService → kernel sched EM/PAS 的公开调用链。

### 重要程度
高

### 建议研究方向
- 复核 CDD / source.android.com 是否定义 PAS、CPU/GPU headroom、PowerStats/ODPM 之间的兼容性要求。
- 对照 AOSP android-15/16 的 PowerStatsService、SystemHealthManager、HintManagerService、PerformanceHintManager、Power HAL AIDL 与 kernel sched/EAS/PAS 相关分支，确认是否存在公开桥接。
- 如只存在 vendor 私有实现，正文应按“可能的 OEM 扩展/待验证”处理，不写成 Android 15/16 平台通用能力。

### 关联章节
5.2, 5.9, 11.1

## [2026-05-07] 13.9 Android Tracing 基础设施 — UprobeStats 开销与数据出口

### 盲区描述
UprobeStats 在 Android 16/17 的真实数据出口与开销边界缺少一手证据。正文写“任意用户态函数耗时统计、性能开销 <1%”，但 uprobe/uretprobe 开销受命中频率、map 更新、ring buffer 写出、参数提取和栈回溯影响，不能脱离场景给固定比例。

### 重要程度
高

### 建议研究方向
- 核对 `packages/modules/UprobeStats/` 中 statsd 触发、BPF 程序加载、RingBuf/Map 输出与 Guardrail 限制。
- 确认 Perfetto 是否有标准数据源/SQL 表接收 UprobeStats，还是主要经 StatsD/自定义消费链路。
- 补低频诊断点与热点函数两类基准，给出调用频率、是否采栈、map/ringbuf 写出配置。

### 关联章节
13.9, 14.10

