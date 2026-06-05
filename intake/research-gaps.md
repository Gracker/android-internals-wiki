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
