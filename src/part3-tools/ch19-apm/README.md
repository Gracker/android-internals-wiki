---
title: "第 19 章：APM 工具与性能监控生态"
chapter: "19.0"
section: "19.0"
status: draft
drafted_date: "2026-04-24"
drafted_by: "openclaw"
applicable_versions: "Android 8 (API 26) - Android 17 (API 37)"
last_verified: "2026-04-24"
confidence: medium
tags: [apm, monitoring, benchmark, observability, matrix, koom, btrace]
related_chapters: ["14.5", "14.12", "14.13", "15.5", "15.9", "15.10"]
---

# 第 19 章：APM 工具与性能监控生态

前面的章节里，Perfetto（第 13 章）解决了线下 trace 分析，其他工具（第 14 章）补上了 Profiler、simpleperf、dumpsys 等单项能力，方法论（第 15 章）回答了"怎么用这些工具做判断"。但有一类问题这三章都没有正面回答：**线上怎么办？**

应用上线之后，卡顿、启动慢、ANR、内存泄漏、OOM 这些问题还会持续出现，但开发者不再能 adb 直连设备抓 trace。APM（Application Performance Monitoring）就是补这个缺口的：把线下能观察到的信号，用可控的开销搬到线上去。

这一章不重复第 14 章"APM 选型"的分析框架，而是把视角降到每一个具体的工具和项目上——它解决了什么问题、怎么接入、架构是什么样的、线上跑起来有哪些工程约束。每个工具独立成篇，读者可以按需翻阅。

## 全景分类

本章覆盖的工具按四个层级组织：

### App 层：客户端 APM 框架

| 工具 | 来源 | 核心能力 | 线上/线下 |
|------|------|----------|-----------|
| Matrix | 腾讯微信 | 卡顿、启动、IO、内存、APK 检查 | 线上 |
| KOOM | 快手 | Java/Native/线程泄漏、OOM | 线上 |
| btrace / RheaTrace | 字节跳动 | 方法级 trace、采样 tracing | 线上 |
| LeakCanary | Square | Activity/Fragment 内存泄漏 | 线下 |
| BlockCanary | — | 主线程卡顿堆栈捕获 | 线上 |
| DoKit | 滴滴 | FPS、启动、网络、调试工具箱 | 线下 |
| ArgusAPM | 360 | UI、网络、内存、卡顿、ANR | 线上 |
| Measure | 开源 | 崩溃、ANR、trace、会话时间线 | 线上 |
| AndroidGodEye | 开源 | CPU、内存、网络、电量、FPS | 线下 |
| Collie | 开源 | FPS、卡顿、流量、内存、启动 | 线上 |
| Rabbit | 开源 | 测速、慢函数、网络、卡顿、FPS | 线上+线下 |

### Framework 层：Google 官方 SDK

| 工具 | Jetpack 模块 | 核心能力 |
|------|-------------|----------|
| JankStats | androidx.metrics | 帧级卡顿感知 |
| FrameMetrics | androidx.metrics | 帧耗时阶段细分 |
| Tracing SDK | androidx.tracing | 进程内 trace（2.0 支持 Perfetto 格式） |
| Microbenchmark | androidx.benchmark | 代码段 CPU 性能测量 |
| Macrobenchmark | androidx.benchmark | 端到端启动/滑动/复杂 UI 测量 |
| Baseline Profiles | — | 编译优化 + 启动加速 |
| ProfilingManager | android.os | 系统触发式性能追踪 |

### 平台层：商业/服务端 APM

| 工具 | 来源 | 定位 |
|------|------|------|
| Firebase Performance | Google | 最易上手的移动性能平台 |
| Sentry | 开源 | 崩溃 + APM + 分布式 trace |
| APMPlus | 字节/火山引擎 | 移动 APM 平台 |
| Bugly | 腾讯 | 崩溃 + ANR 上报 |
| CAT | 美团开源 | 分布式监控（偏服务端） |
| PerfDog | 腾讯 WeTest | 免 Root 性能测试（FPS/CPU/GPU/内存/功耗） |

### System 层：Benchmark 与自动化

| 工具 | 定位 |
|------|------|
| Geekbench | CPU 单核/多核 + GPU Compute |
| AnTuTu（安兔兔） | 综合性能（CPU/GPU/内存/UX） |
| 3DMark | GPU + 游戏性能 |
| PCMark | 生产力与日常使用性能 |
| Vellamo | Qualcomm 浏览器/多核/单核 |
| AndroBench | 存储顺序/随机 + SQLite |
| A1 SD Bench | SD 卡/RAM 读写速度 |
| SoloPi | 阿里无线化自动化测试 |
| Emmagee | 网易性能监控浮窗 |

## 与其他章节的关系

- **第 13 章（Perfetto）**：Perfetto 是线下 trace 分析的核心工具，本章的 btrace/RheaTrace、JankStats、Tracing SDK 都会产出 Perfetto 兼容的数据格式。
- **第 14 章**：14.5 三方性能库做了概要介绍，14.12 APM 选型给了分层框架，14.13 Hook 基础设施讲底层原理。本章是这两个小节的展开版——每个工具独立深入。
- **第 15 章（方法论）**：15.5 线上监控、15.9 线上问题流转、15.10 治理工程化讲的是"怎么把这些工具用成体系"，本章讲的是"这些工具本身是什么"。

## 本章内容

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
- 19.20 SoloPi 与 Emmagee
- 19.21 Benchmark 应用（Geekbench、安兔兔、3DMark、PCMark、Vellamo）
- 19.22 存储 Benchmark（AndroBench、A1 SD Bench）

## 阅读建议

- 第一次搭线上 APM 体系：先读 19.1 建立全景图，再按团队当前最需要解决的问题选 2-3 个工具深入。
- 已经在用某个工具想深入理解：直接翻对应小节。
- 需要选型：结合 14.12 的框架和本章各工具的深度分析一起看。
- 关注 Benchmark 方向：19.21 和 19.22 覆盖主流 Benchmark 应用。
