# Research Gaps

[2026-06-04] 19.18 商业 APM 平台 — Android 17 SDK/API 门槛需要源码验证
- **章节**：`src/part3-tools/ch19-apm/18-commercial-apm.md`
- **问题**：Sentry profiling/UI Profiling/transaction-based profiling、Bugly Pro 页面回放/启动 Span/16KB Page Size 等能力存在 SDK/API 版本门槛
- **缺口**：需要使用 android-17.0.0_r1 源码验证具体门槛，明确哪些能力在 Android 17 中可用
- **优先级**：高
- **路径**：https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1

[2026-06-04] 19.06 BlockCanary — Android 17 Looper.Observer 接口稳定性需要验证
- **章节**：`src/part3-tools/ch19-apm/06-blockcanary.md`
- **问题**：章节提到 Android 10（API 29）起，`Looper` 内部存在 `@hide` 的 `Looper.Observer`，但未验证 Android 17 中的状态
- **缺口**：需要使用 android-17.0.0_r1 源码验证 Looper.Observer 接口在 Android 17 中的可用性和稳定性
- **优先级**：中
- **路径**：https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1

[2026-06-04] 13.2 Trace 抓取 — Android 17 linux.perf 和 FrameTimeline 需源码验证
- **章节**：`src/part3-tools/ch13-perfetto/02-trace-capture.md`
- **问题**：
  1. linux.perf 数据源（即 `traced_perf` 守护进程）状态需要 Android 17 验证
  2. `android.surfaceflinger.frametimeline` 需验证在 Android 17 中的适用性
- **缺口**：需要使用 android-17.0.0_r1 源码验证这些数据源在 Android 17 中的状态和可用性
- **优先级**：高
- **路径**：https://android.googlesource.com/platform/frameworks/native/+/android-17.0.0_r1