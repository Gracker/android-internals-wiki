---
title: "第 19 章：APM 工具与性能监控生态"
chapter: "19.0"
section: "19.0"
drafted_date: "2026-04-24"
drafted_by: "openclaw"
applicable_versions: "Android 8 (API 26) - Android 17 (API 37)"
last_verified: "2026-08-14"
confidence: medium
tags: [apm, monitoring, benchmark, observability, matrix, koom, btrace]
related_chapters: ["14.7", "15.3", "15.1"]
sources:
  - type: official
    path: https://developer.android.com/topic/performance
  - type: official
    path: https://developer.android.com/jetpack/androidx/releases/metrics
  - type: official
    path: https://developer.android.com/topic/performance/tracing
  - type: official
    path: https://developer.android.com/jetpack/androidx/releases/tracing
  - type: official
    path: https://developer.android.com/jetpack/androidx/releases/benchmark
  - type: official
    path: https://developer.android.com/reference/android/os/ProfilingManager
  - type: official
    path: https://firebase.google.com/docs/perf-mon
  - type: github
    path: https://github.com/Tencent/matrix
  - type: github
    path: https://github.com/KwaiAppTeam/KOOM
  - type: github
    path: https://github.com/bytedance/btrace
  - type: github
    path: https://github.com/square/leakcanary
  - type: github
    path: https://github.com/didi/DoKit
  - type: github
    path: https://github.com/measure-sh/measure
  - type: official
    path: https://www.geekbench.com/download/android/
  - type: official
    path: https://benchmarks.ul.com/3dmark-android
  - type: official
    path: https://benchmarks.ul.com/pcmark-android
  - type: official
    path: https://browserbench.org/Speedometer3.1/
  - type: official
    path: https://www.antutu.com/web/download
  - type: github
    path: https://github.com/maxim-saplin/CrossPlatformDiskTest
task2b_result: "fixed"
task6_state: "reviewed"
last_task2b_at: "2026-05-06T05:49:37+08:00"
repaired_date: "2026-04-25"
repaired_by: openclaw-task2b
task6_result: pass-light-edit
reviewed_by: openclaw-task6
reviewed_date: "2026-05-08"
task6_reviewed_date: "2026-05-08"
last_task6_at: "2026-05-08T21:24:13+08:00"
last_task6_review_log: "logs/review/2026-05-08-21-review.md"
status: "finalized"
pipeline_stage: "ready-to-publish"
task9_state: "reviewed"
task9_result: "pass-tech-review"
task2b_state: "fixed"
task9_reviewed_date: "2026-05-08"
task9_reviewed_by: openclaw-task9
last_task9_at: "2026-05-08T21:35:11+08:00"
last_task9_review_log: "logs/deep-review/2026-05-08-21-deep-review.md"
review_notes: "2026-05-06 Task9 06:23：deep-review needs-rework；P1 Tracing SDK / tracing-perfetto 版本线仍写错；P2 Benchmark 目录与实际章节标题仍不一致。 | 2026-05-08 Task6 21:24：Task2B 修复后写作复审；轻修 2 处（19.22 目录标题与阅读建议），L1/L2 通过，无新增 L3/L4 回炉项，送 Task9 复审。"
task9_review_notes: "2026-05-08 Task9 21:32：pass-tech-review。无 P0/P1；P2 2 处记录在 deep-review/suggestions，不阻塞发布；自动晋升 finalized / ready-to-publish。"
last_consolidated_at: '2026-08-24'
consolidation_note: 第二轮逐篇审阅后收敛为 14 篇，合并同一责任链中的总览、机制、版本增量、观测与案例，并统一连续编号。
---

# 第 19 章：APM 工具与性能监控生态

第 13 章介绍线下 trace（按时间排列的性能事件记录）分析，第 14 章覆盖 Android Studio Profiler、CPU 采样工具 simpleperf、系统状态查询命令 dumpsys 等单项工具，第 15 章说明证据组织与判断方法。第 19 章转向生产环境中的采集与分析。

应用上线后仍会出现卡顿、启动慢、ANR（Application Not Responding，应用无响应）、内存泄漏和 OOM（Out of Memory，内存耗尽），但通常无法通过 `adb`（Android Debug Bridge）直连用户设备采集 trace。APM（Application Performance Monitoring，应用性能监控）通过采样率、触发条件、数据量和上传时机限制额外的 CPU、I/O（输入/输出）与网络开销，用于发现、聚合和定位这些问题。

内容按“全景与选型门槛、当前工具、历史方案、官方 API（Application Programming Interface，应用编程接口）、平台、实验室工具、采集机制与端侧（设备端）架构”组织。相邻工具共享的方法、兼容性评测和报告规范只保留一次，具体实现边界留在对应小节。

## 全景分类

工具按四个层级组织：App 层负责设备内采集，Framework（框架）层提供平台或 Jetpack（Android 官方支持库）API，平台层负责数据汇聚与分析，System 层用于实验室基准测试和自动化。“状态”描述截至 2026-08-14 的公开维护信号和本章建议用途，不代表市场占有率。仓库最近有提交只说明代码仍在变化，不能单独证明它兼容 Android 17、当前 AGP（Android Gradle Plugin）或所有 ABI（Application Binary Interface，应用二进制接口）；接入结论仍需按具体版本实测。

### App 层：客户端 APM 框架

表中的“线上”指生产环境中的用户设备，“线下”指开发、测试或实验室环境。

| 工具 | 来源 | 核心能力 | 线上/线下 | 状态 |
|------|------|----------|-----------|------|
| Matrix | 腾讯微信 | 卡顿、启动、I/O、内存、APK 检查 | 线上 | 成熟项目；最近公开提交较早，接入前验证 AGP 与平台 API |
| KOOM | 快手 | Java / Native（C/C++）/ 线程泄漏、OOM | 线上 | 有近期维护记录；接入前验证目标 API 与 ABI |
| btrace / RheaTrace | 字节跳动 | 方法级 trace、采样式 tracing | 线上 | 活跃维护 |
| LeakCanary | Square | Activity / Fragment / ViewModel 泄漏检测 | 线下 | 活跃维护；适合开发与测试阶段 |
| BlockCanary | — | 主线程卡顿堆栈捕获 | 线上 | 维护停滞；仅作原理参考 |
| DoKit | 滴滴 | FPS（每秒帧数）、启动、网络、调试工具箱 | 线下 | 维护频率较低；以线下调试为主 |
| ArgusAPM | 360 | UI（界面）、网络、内存、卡顿、ANR | 线上 | 历史项目；仅作原理参考 |
| Measure | 开源 | 崩溃、ANR、trace、会话时间线 | 线上 | 活跃维护 |
| AndroidGodEye | 开源 | CPU、内存、网络、电量、FPS | 线下 | 历史项目；仅作原理参考 |
| Collie | 开源 | FPS、卡顿、流量、内存、启动 | 线上 | 历史项目；仅作原理参考 |
| Rabbit | 开源 | 测速、慢函数、网络、卡顿、FPS | 线上+线下 | 历史项目；仅作原理参考 |

### Framework 层：Google 官方 SDK（软件开发工具包）

| 工具 | Jetpack / 平台模块 | 核心能力 | 状态 |
|------|-------------------|----------|------|
| JankStats | `androidx.metrics:metrics-performance` 1.0.0 | 检测卡顿帧，并附带当时的 UI 状态 | 稳定版 |
| FrameMetrics | `android.view.FrameMetrics` / `Window.OnFrameMetricsAvailableListener`（API 24+） | 细分一帧各阶段的耗时；`FrameMetricsAggregator` 提供 AndroidX 聚合 | 平台稳定能力 |
| Tracing SDK | `androidx.tracing:tracing-*` 2.0.0；旧 `tracing-perfetto` / `-binary` / `-handshake` 1.0.1 | 系统 trace 区间，以及 2.0 新增的进程内缓冲区、flow（跨事件关联）、annotation（键值注释）和协程 trace | 稳定版；两组产物需区分 |
| Microbenchmark（微基准） | `androidx.benchmark` | 测量一小段代码的执行时间和内存分配 | 稳定能力 |
| Macrobenchmark（宏基准） | `androidx.benchmark` | 从应用外部测量启动、滑动和复杂 UI，从操作触发一直覆盖到结果展示 | 稳定能力 |
| Baseline Profiles（基线配置文件） | Android Gradle Plugin / Jetpack | 提供关键代码路径，让 ART（Android Runtime）提前生成 AOT（Ahead-of-Time，预先编译）代码；Play Cloud Profiles 是按真实设备数据生成的云端配置 | 稳定能力 |
| ProfilingManager | `android.os` | Android 15（API 35）起请求堆内存采样（heap profile）、Java 堆转储（heap dump）、调用栈采样（stack sampling）和系统 trace | 新平台能力 |

Tracing 2.0 的新接口把带字段的事件写入应用进程控制的缓冲区，Android Studio 的 System Trace 目前不会自动采集这部分数据；Benchmark 1.5 可以在测试结束后合并，核验时最新版本为 1.5.0-rc01（RC，候选发布版）。低频、希望始终进入系统 trace 缓冲区的事件，仍适合使用 `Trace.beginSection` 或 `androidx.tracing.trace {}`。这里的 slice 指带开始和结束时间的区间事件。

### 平台层：商业/服务端 APM

| 工具 | 来源 | 定位 | 状态 |
|------|------|------|------|
| Firebase Performance | Google | 自动采集启动、页面渲染和网络数据，并支持自定义 trace | 托管服务 |
| Sentry | 开源 | 崩溃、性能 tracing 与分布式 trace（关联客户端请求和服务端调用） | 开源 SDK + 托管/自建平台 |
| APMPlus | 字节/火山引擎 | 移动 APM 平台 | 商业平台 |
| Bugly | 腾讯 | 崩溃 + ANR 上报 | 商业平台 |
| CAT | 美团开源 | 分布式监控（偏服务端） | 服务端方案；移动端仅作关联参考 |
| PerfDog | 腾讯 WeTest | 免 Root（无需系统超级用户权限）测试 FPS / CPU / GPU / 内存 / 功耗 | 商业测试工具 |

托管服务的可用功能、计费、数据存储和处理地区、隐私条款会变化，选型时应以部署区域的官方说明和合同为准。

### System 层：Benchmark 与自动化

Benchmark（基准测试）用固定的一组操作（工作负载）比较设备或版本。分数只有在工具、测试项目、资源包、运行轮次，以及设备温度和降频状态一致时才可比较。

| 工具 | 定位 | 状态 | 使用边界 |
|------|------|------|----------|
| Geekbench 7 | CPU 单核/多核 + GPU Compute（通用 GPU 计算） | 当前版本 | Android 12+、至少 4 GB 内存；旧版本分数应保留为独立基线 |
| AnTuTu（安兔兔） | 综合性能（CPU / GPU / 内存 / UX，即用户体验） | Android 11.1.4（核验时） | 工具版本与 3D 资源包必须一致；结果还受温度和机型配置影响 |
| 3DMark | GPU + 游戏性能 | 当前维护 | 固定 Steel Nomad Light、Solar Bay、Wild Life 等具体测试及其版本；压力测试与单次跑分分开记录 |
| PCMark | 生产力、日常使用与存储测试 | Android 3.1.4113（核验时） | 固定 Work 3.0 或 Storage 2.0；不同工作负载版本的分数不能直接比较 |
| Speedometer 3.1 | 浏览器 / WebView 内 Web 应用的响应速度 | 当前 Web benchmark | 结果受浏览器内核、WebView 版本和设备热状态影响 |
| CPDT | 跨平台存储读写测试 | 公开版 2.4.0；发布节奏较慢 | 用于补充存储吞吐观察，仍要结合设备温度、缓存和文件系统状态复核 |
| SoloPi | 自动化测试与设备端性能采集 | 维护频率较低 | 适合专项测试，不能替代系统 trace |

Vellamo、AndroBench、A1 SD Bench、Emmagee 不再作为现代 Android 的推荐入口。它们保留在具体小节里，用于阅读旧报告或理解历史方案：Vellamo 已下架；旧版 AndroBench / A1 SD Bench 以早期存储权限、文件路径和测试模型为前提，结果不能直接代表现代 UFS（Universal Flash Storage，通用闪存存储）或真实应用负载；Emmagee 对 Android 10+ 的权限、后台限制和进程模型覆盖不足。

## 与其他章节的关系

- **第 13 章（Perfetto）**：Perfetto 是线下 trace 分析工具。btrace/RheaTrace 可以把方法调用写成可导入 Perfetto 的 trace 数据；`Trace.beginSection` / `androidx.tracing.trace {}` 把 slice 写入系统 trace 缓冲区，Tracing 2.0 还提供应用进程控制的记录方式。JankStats 不生成 Perfetto trace 文件，它通过 `OnFrameListener` / `FrameData` 输出帧级 jank（异常卡顿帧）和 UI state（当时的界面状态），适合与 Perfetto、FrameTimeline（系统记录的帧时间线）和 Tracing SDK 一起定位原因。
- **第 14 章**：14.7 统一说明第三方性能库、APM 可观测性（通过指标、日志和 trace 了解运行状态）选型与 Hook（拦截或替换调用）基础设施；第 19 章分别展开具体工具。
- **第 15 章（方法论）**：15.3 和 15.1 说明线上监控，以及问题交接、负责人、修复和回归检查流程；第 19 章说明各工具的能力与边界。

## 内容索引

- [19.1 APM 全景、Firebase 与商业平台选型](01-apm-landscape-firebase-commercial.md)
- [19.2 Matrix、btrace 与 Tracing SDK](02-matrix-btrace-tracing-sdk.md)
- [19.3 KOOM 与 LeakCanary 内存诊断](03-koom-leakcanary-memory-diagnostics.md)
- [19.4 DoKit 与 Measure 开发期性能工具](04-dokit-measure-dev-tools.md)
- [19.5 历史开源 APM：BlockCanary、ArgusAPM、AndroidGodEye、Collie 与 Rabbit](05-open-source-apm-history.md)
- [19.6 Jetpack Benchmark：Microbenchmark、Macrobenchmark 与测量协议](06-jetpack-benchmark-baseline-profiles.md)
- [19.7 实验室测试工具与设备 Benchmark](07-lab-tools-device-benchmarks.md)
- [19.8 网络 APM 底层捕获原理](08-network-apm-internals.md)
- [19.9 崩溃与 ANR 捕获机制](09-crash-anr-internals.md)
- [19.10 耗电与发热监控 (Battery & Thermal)](10-battery-thermal-apm.md)
- [19.11 混合栈与跨平台 APM (WebView / Flutter)](11-hybrid-apm.md)
- [19.12 千万级 DAU 的 APM 端侧架构](12-apm-client-architecture.md)

## 阅读建议

- 初次搭建线上 APM：先读 19.1，再按当前问题选择 2—3 个工具。
- 已在使用某个工具：直接进入对应条目核对实现与边界。
- 需要选型：结合 14.10 的框架和各工具的详细分析。
- 关注回归与实验室测试：19.6 负责 Jetpack Benchmark 测量协议，19.7 负责操作复现、设备 Benchmark 与性能档位分组。
