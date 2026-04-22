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

