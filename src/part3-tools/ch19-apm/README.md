---
title: "第 19 章：APM 工具与性能监控生态"
chapter: "19.0"
section: "19.0"
drafted_date: "2026-04-24"
drafted_by: "openclaw"
applicable_versions: "Android 8 (API 26) - Android 17 (API 37)"
last_verified: "2026-04-24"
confidence: medium
tags: [apm, monitoring, benchmark, observability, matrix, koom, btrace]
related_chapters: ["14.10", "14.26", "15.5", "15.9"]
sources:
  - type: official
    path: https://developer.android.com/topic/performance
  - type: official
    path: https://developer.android.com/jetpack/androidx/releases/metrics
  - type: official
    path: https://developer.android.com/topic/performance/tracing
  - type: official
    path: https://firebase.google.com/docs/perf-mon
  - type: github
    path: https://github.com/Tencent/matrix
  - type: github
    path: https://github.com/KwaiAppTeam/KOOM
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
---

# 第 19 章：APM 工具与性能监控生态

第 13 章介绍线下 trace 分析，第 14 章覆盖 Profiler、simpleperf、dumpsys 等单项工具，第 15 章说明证据组织与判断方法。第 19 章转向生产环境中的采集与分析。

应用上线后仍会出现卡顿、启动慢、ANR、内存泄漏和 OOM，但通常无法通过 adb 直连设备采集 trace。APM（Application Performance Monitoring）以受控开销采集生产环境信号，用于发现、聚合和定位这些问题。

内容按具体工具和项目组织，说明能力范围、接入方式、架构与生产约束。工具之间相互独立，可以按问题查阅。

## 全景分类

工具按四个层级组织。表里的“状态”用于区分常用工具、维护中工具、原理参考和历史工具，避免把旧工具当成现代项目的默认选择。

### App 层：客户端 APM 框架

| 工具 | 来源 | 核心能力 | 线上/线下 | 状态 |
|------|------|----------|-----------|------|
| Matrix | 腾讯微信 | 卡顿、启动、IO、内存、APK 检查 | 线上 | 主流 |
| KOOM | 快手 | Java / Native / 线程泄漏、OOM | 线上 | 维护中 |
| btrace / RheaTrace | 字节跳动 | 方法级 trace、采样 tracing | 线上 | 维护中 |
| LeakCanary | Square | Activity / Fragment / ViewModel 泄漏检测 | 线下 | 主流线下工具 |
| BlockCanary | — | 主线程卡顿堆栈捕获 | 线上 | 仅参考原理 |
| DoKit | 滴滴 | FPS、启动、网络、调试工具箱 | 线下 | 维护中 |
| ArgusAPM | 360 | UI、网络、内存、卡顿、ANR | 线上 | 历史项目 / 仅参考原理 |
| Measure | 开源 | 崩溃、ANR、trace、会话时间线 | 线上 | 维护中 |
| AndroidGodEye | 开源 | CPU、内存、网络、电量、FPS | 线下 | 历史项目 / 仅参考原理 |
| Collie | 开源 | FPS、卡顿、流量、内存、启动 | 线上 | 历史项目 / 仅参考原理 |
| Rabbit | 开源 | 测速、慢函数、网络、卡顿、FPS | 线上+线下 | 历史项目 / 仅参考原理 |

### Framework 层：Google 官方 SDK

| 工具 | Jetpack / 平台模块 | 核心能力 | 状态 |
|------|-------------------|----------|------|
| JankStats | androidx.metrics | 帧级卡顿感知 | 主流 |
| FrameMetrics | android.view.FrameMetrics / Window.OnFrameMetricsAvailableListener (API 24+) | 帧耗时阶段细分（AndroidX 聚合器：FrameMetricsAggregator） | 主流 |
| Tracing SDK | androidx.tracing | 进程内 trace（`androidx.tracing:tracing` 1.3.0 稳定 / 2.0.0-alpha06；`androidx.tracing:tracing-perfetto`(+binary) 1.0.1 支持 Perfetto 格式输出） | 主流 |
| Microbenchmark | androidx.benchmark | 代码段 CPU 性能测量 | 主流 |
| Macrobenchmark | androidx.benchmark | 端到端启动、滑动、复杂 UI 测量 | 主流 |
| Baseline Profiles | Android Gradle Plugin / Jetpack | 编译优化 + 启动加速，和 Play Cloud Profiles / ART 编译策略一起影响首次启动 | 主流 |
| ProfilingManager | android.os | Android 15+ 系统性能取证（trace、heap dump、stack sampling） | 新平台能力 |

### 平台层：商业/服务端 APM

| 工具 | 来源 | 定位 | 状态 |
|------|------|------|------|
| Firebase Performance | Google | 最易上手的移动性能平台 | 主流 |
| Sentry | 开源 | 崩溃 + APM + 分布式 trace | 主流 |
| APMPlus | 字节/火山引擎 | 移动 APM 平台 | 商业平台 |
| Bugly | 腾讯 | 崩溃 + ANR 上报 | 商业平台 |
| CAT | 美团开源 | 分布式监控（偏服务端） | 服务端主流 / 移动端仅参考 |
| PerfDog | 腾讯 WeTest | 免 Root 性能测试（FPS / CPU / GPU / 内存 / 功耗） | 商业测试工具 |

### System 层：Benchmark 与自动化

| 工具 | 定位 | 状态 | 使用边界 |
|------|------|------|----------|
| Geekbench 6 | CPU 单核/多核 + GPU Compute | 主流 | Android 10+；旧设备需另建 Geekbench 5 或历史基线 |
| AnTuTu（安兔兔） | 综合性能（CPU / GPU / 内存 / UX） | 活跃 | 适合横向参考，结果受版本、温度和机型库影响 |
| 3DMark | GPU + 游戏性能 | 主流 | 适合图形压力与稳定性测试 |
| PCMark | 生产力、日常使用与存储测试 | 主流 | 适合续航和真实工作负载对比 |
| Speedometer 3.0 | 浏览器 / WebView JavaScript 与 DOM 性能 | 主流 Web benchmark | 结果受浏览器内核、WebView 版本和热状态影响 |
| CPDT | 跨平台存储读写测试 | 维护中 | 适合补充存储吞吐观察，仍要结合设备温度和文件系统状态复核 |
| SoloPi | 自动化测试与端上性能采集 | 维护中 | 适合专项测试，不替代系统 trace |

Vellamo、AndroBench、A1 SD Bench、Emmagee 不再作为现代 Android 推荐入口。它们保留在具体小节里，只用于读旧报告或理解历史方案：Vellamo 已下架；AndroBench / A1 SD Bench 与 Android 10+ 存储权限和现代 UFS 特性存在口径偏差；Emmagee 对 Android 10+ 权限、后台限制和进程模型覆盖不足。

## 与其他章节的关系

- **第 13 章（Perfetto）**：Perfetto 是线下 trace 分析工具。btrace/RheaTrace 可以把方法调用写成可导入 Perfetto 的 trace 数据；Tracing SDK 用 `Trace.beginSection` / `androidx.tracing.trace {}` 给 Perfetto 添加进程内 slice；JankStats 不直接生成 Perfetto trace 文件，它通过 `OnFrameListener` / `FrameData` 输出帧级 jank 数据和 UI state，适合与 Perfetto、FrameTimeline、Tracing SDK 一起归因。
- **第 14 章**：14.10 统一说明三方性能库和 APM 可观测性选型，14.26 说明 Hook 基础设施；第 19 章分别展开具体工具。
- **第 15 章（方法论）**：15.5 和 15.9 说明线上监控、问题流转与治理，第 19 章说明各工具的能力与边界。

## 内容索引

- 19.1 APM 全景图与分类体系
- 19.2 Tencent Matrix
- 19.3 KOOM
- 19.4 btrace / RheaTrace
- 19.5 LeakCanary
- 19.6 BlockCanary
- 19.7 DoraemonKit / DoKit
- 19.8 ArgusAPM
- 19.9 Measure
- 19.10 其他开源 APM 库（AndroidGodEye、Collie、Rabbit）
- 19.11 JankStats
- 19.12 FrameMetrics
- 19.13 androidx.tracing（Tracing SDK）
- 19.14 Jetpack Benchmark（Microbenchmark + Macrobenchmark）
- 19.15 Baseline Profiles 与编译优化
- 19.16 ProfilingManager
- 19.17 Firebase Performance
- 19.18 商业 APM 平台（Sentry、APMPlus、Bugly）
- 19.19 PerfDog
- 19.20 SoloPi 与历史 Emmagee
- 19.21 Benchmark 应用（Geekbench 6、安兔兔、3DMark、PCMark、Speedometer）
- 19.22 存储 Benchmark（AndroBench、A1 SD Bench）
- 19.23 网络 APM 底层捕获原理
- 19.24 崩溃与 ANR 捕获机制
- 19.25 耗电与发热监控 (Battery & Thermal)
- 19.26 混合栈与跨平台 APM (WebView / Flutter)
- 19.27 千万级 DAU 的 APM 端侧架构
- 19.10 补充：APM 工具基准测试与兼容性验证

## 阅读建议

- 初次搭建线上 APM：先读 19.1，再按当前问题选择 2—3 个工具。
- 已在使用某个工具：直接进入对应条目核对实现与边界。
- 需要选型：结合 14.10 的框架和各工具的详细分析。
- 关注 Benchmark 方向：19.21 覆盖通用 Benchmark 应用，19.22 覆盖存储基线工具。
