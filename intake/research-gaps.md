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



