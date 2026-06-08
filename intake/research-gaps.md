## [Task 2A Gap Mining] 2026-06-08 13:07 (Round 32)

- Direction: 同 Round 31 — 无空 draft、TASK2B_BACKLOG=0、418 sections（296+6 finalized + 76 ready-for-review + 0 draft + 40 misc）。source-index 10 条素材中 0 条高质量未映射。research-feeds 自 2026-04 无更新。daily-info 06-08 已在 Round 31 完整分析（6 篇 DeepResearch 全部映射已有章节）。Clippings 三本参考书已全部覆盖。AOSP 26 chapters 覆盖饱和。research-gaps.md 最新条目为 Statsd 验证需求（ch14.17 已有章节，非新章节缺口）。
- No gap scored >= 14
- Book: 418 sections (302 finalized + 76 ready-for-review + 0 draft + 40 misc)
- 32 consecutive empty runs
- Recommendation: 暂停 gap mining cron 或仅在 new material injection 时触发
- Bottleneck: Task 6 review of 76 ready-for-review sections

# Research Gaps

> ℹ️ **2026-06-05 同步**：以下 3 条已在 `researched-gaps.json` 完成（19.18 商业 APM 完成于 2026-06-06、19.06 BlockCanary 完成于 2026-06-05、13.2 Trace 抓取完成于 2026-06-05），仅 `research-gaps.md` 未同步。本轮已加入新选题。

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
> ℹ️ **2026-06-05 完成**：6.7 FUSE-BPF 验证完成（经源码验证不存在，已更新草稿章节）
[2026-06-05] 6.7 FUSE-BPF 与 Scoped Storage I/O 性能 — AOSP 内核/用户态链路源码验证 (已完成)
- **章节**：`src/part1-fundamentals/ch06-storage/07-fuse-bpf-scoped-storage-io-performance.md`（draft 状态，78 行）
- **问题**：草稿断言"FUSE-BPF 位于内核 `fs/fuse-bpf/` 目录"，需用 AOSP Common Kernel 与 `system/core/fs_mgr`/`external/selinux` 验证实际路径、守护进程名、是否回退到传统 FUSE、Scoped Storage 路径在用户态 `sdcard` 与内核 FUSE-BPF 之间的权限检查分工
- **缺口**：
  - 验证 `fs/fuse-bpf/` 目录是否真实存在（android17-gki / android16-6.12 / main）
  - 验证 `system/bin/sdcard` 是否仍是 Android 17 媒体 FUSE 后端，或已被 FUSE-BPF 取代
  - 验证 `mediaProvider` 与 FUSE-BPF 的衔接（Ioctl / sysfs / proc 接口）
  - 验证 SELinux 策略（`fuse_bpf` domain）与 FUSE 域（`fuse` domain）的边界
  - 验证 Android 17 / API 37 中是否启用（feature flag / build flag）
- **优先级**：中-高
- **路径**：
  - https://android.googlesource.com/kernel/common/+/refs/heads/android-6.12
  - https://android.googlesource.com/platform/system/core/+/refs/heads/main
  - https://android.googlesource.com/platform/external/selinux/+/refs/heads/main
  - https://cs.android.com/android/_/android/platform/system/core/+/main:fs_mgr

[2026-06-07] 26.x Observability — Android 17 Statsd (StatsService) 与 StatsdConfig/StatsdAtom 链路边界源码验证
- **章节**：`src/part5-app/ch26-observability/05-online-troubleshooting.md`、`src/part5-app/ch26-observability/12-versioned-diagnostics.md`、`src/part3-tools/ch13-perfetto/09-tracing-infrastructure.md`
- **问题**：
  1. 各章节（5.06、5.07、5.10、10.4、11.01、13.x、26.x）频繁引用 `android.surfaceflinger.frametimeline` / `android_job_scheduler_states` / battery/thermal statsd 数据源，但章节都未深挖 Statsd 自身的服务、配置、调度链路
  2. 章节中 `StatsdConfig` 的 pull atom / push atom 注册、`StatsdAtom.write()` 调用路径与 Perfetto `StatsdTracingConfig` 转换逻辑缺乏源码验证
  3. Android 17 中 `StatsdService` 的启动顺序、config 持久化（`/data/misc/statsd/`）、权限边界、API level 门控缺乏统一证据
- **缺口**：
  - 验证 `frameworks/base/services/core/java/com/android/server/statsd/StatsdService.java` 在 Android 17 中是否仍由 `SystemService` 启动、是否依赖 `statsd.binary`（packages/modules/StatsD）
  - 验证 `StatsdConfig`（packages/modules/StatsD/service/java/com/android/server/statsd/StatsdConfig.java）核心字段、push/pull atom 注册逻辑
  - 验证 `StatsdAtom.write()` (frameworks/base/core/java/android/util/StatsdAtom.java) 的 JNI 路径与权限
  - 验证 `statsd` cmd（packages/modules/StatsD/cmd/statsd/src/main.rs 或 .java）的 `dumpsys statsd` 输出格式
  - 验证 Perfetto `StatsdTracingConfig` 在 ui.perfetto.dev 中 `android_*_states` 表的来源（`trace_processor/src/tables/statsd_tables.py`）
  - 验证 Android 17 / API 37 中是否新增 statsd atom（feature flag / build flag）
- **优先级**：中
- **路径**：
  - https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1 services/core/java/com/android/server/statsd/
  - https://android.googlesource.com/platform/packages/modules/StatsD/+/android-17.0.0_r1
  - https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1 core/java/android/util/StatsdAtom.java
  - https://cs.android.com/android/_/android/platform/packages/modules/StatsD/+/main
