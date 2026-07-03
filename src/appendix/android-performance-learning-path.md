---
title: "附录 G：Android 性能学习路线"
chapter: "appendix.G"
section: "appendix.G"
status: draft
applicable_versions: "Android 10 (API 29) - Android 17 (API 37)"
last_verified: "2026-07-02"
confidence: medium
tags: [learning-path, performance, framework, perfetto, apm]
related_chapters: ["13.0", "14.13", "15.7", "19.0", "21.4", "21.12"]
created_by: "openclaw-manual-intake"
created_date: "2026-07-02"
gap_source: "manual-request/android-performance-learning-path"
material_paths:
  - "intake/manual-requests/2026-07-02-android-performance-learning-gap.md"
pipeline_stage: "draft"
task6_state: "pending"
task9_state: "pending"
---

# 附录 G：Android 性能学习路线

这条路线面向已经有 Android 开发经验、想进入性能优化、Framework 或客户端稳定性方向的读者。它不要求从目录第一页开始读，而是按“能观察问题、能解释机制、能做工程验证”的顺序推进。

AIW 正文已经覆盖工具、系统机制、应用优化和线上监控。本附录负责把这些章节组织成训练路径。

## 起点：先建立性能问题的分类方式

性能优化的第一步不是背工具名，而是把问题分清。

| 问题类型 | 先读章节 | 验收方式 |
|---|---|---|
| 卡顿 / 掉帧 | 7.1-7.5、13.3、13.10 | 能把一段慢帧拆成主线程、RenderThread、SurfaceFlinger、GPU、调度等待五类候选 |
| 启动慢 | 8.2、8.3、21.1、21.4、21.12 | 能区分冷启动、温启动、TTID、TTFD、Baseline Profile 与 Startup Profile 的收益来源 |
| ANR | 9.1-9.4、20.4、26.4 | 能说明 input、broadcast、service、provider 四类 ANR 的触发路径和现场偏移风险 |
| 内存问题 | 4.1-4.5、10.1-10.6、23.1-23.7 | 能区分 Java 泄漏、native 泄漏、低内存回收、GC 抖动、线程/FD 资源泄漏 |
| 功耗 / 发热 | 5.1-5.6、11.1-11.5、25.1-25.6 | 能把耗电分到 CPU、wakelock、网络、定位、后台任务、thermal 降频等方向 |

这一阶段的输出不是笔记，而是五张排查卡片：每类问题写清现象、指标、trace 数据源、常见误判和下一步验证。

## 第一阶段：Perfetto 与系统 trace

Perfetto 是贯穿全书的观察入口。读者应先掌握三件事：

1. 会抓一份可用 trace：13.1、13.2、13.7。
2. 会读时间线：13.3、13.5、13.6。
3. 会用 SQL 固化判断：13.10、13.11、13.13、13.14。

练习场景建议从三个 trace 开始：

| 场景 | 采集重点 | 需要回答的问题 |
|---|---|---|
| 冷启动 | `am`、`wm`、`view`、`sched`、CPU frequency、进程状态 | 慢在进程创建、Provider、Application、Activity、首帧，还是调度等待 |
| 列表滑动 | FrameTimeline、`gfx`、`view`、RenderThread、SurfaceFlinger、CPU/GPU counter | 掉帧来自主线程、渲染线程、合成、GPU，还是系统负载 |
| ANR 复盘 | 主线程状态、Binder、I/O、锁竞争、系统负载 | 主线程当时在运行、阻塞、等待 Binder、等待 I/O，还是现场已经偏移 |

验收标准：给一份 trace，能写出“证据 -> 候选根因 -> 排除项 -> 补采项”的短报告。报告里不能只贴截图，要能列出关键 track、slice、线程状态和 SQL 结果。

## 第二阶段：Framework 主线

Framework 学习不要从“源码目录全景”开始铺开。更稳的方式是按性能问题倒推系统机制。

| Framework 主线 | 对应章节 | 读源码入口 |
|---|---|---|
| App 进程启动 | 1.2、1.3、1.11、8.2、21.1 | `ActivityThread`、`LoadedApk`、`ContentProvider`、`Zygote` |
| 主线程消息循环 | 1.5、2.4、7.3、9.3 | `Looper`、`MessageQueue`、`Handler`、`Choreographer` |
| 渲染管线 | 2.1-2.10、18.1-18.6 | `ViewRootImpl`、`ThreadedRenderer`、`RenderThread`、`SurfaceFlinger` |
| 输入与 ANR | 3.1-3.4、9.1-9.4 | `InputDispatcher`、`InputReader`、`ActivityManagerService`、`WindowManagerService` |
| Binder 与系统服务 | 1.4、1.17、1.30、1.38 | `frameworks/native/libs/binder`、`drivers/android/binder.c` |
| 内存与进程管理 | 4.1-4.6、4.15、16.8 | `ActivityManagerService`、`OomAdjuster`、`lmkd`、`art/runtime` |
| 调度、功耗和热管理 | 5.1-5.9、16.4、17.4 | cpuset、uclamp、EAS、Power HAL、Thermal HAL |

这条线的练习方式是“从 trace 找源码”。例如 trace 中看到 `Choreographer#doFrame` 超时，就顺着 `Choreographer`、`ViewRootImpl#doTraversal`、`ThreadedRenderer`、SurfaceFlinger 的提交链路读；看到 Binder 等待，就顺着客户端调用、服务端线程池、Binder transaction、调度状态读。

15.7 的 AOSP 阅读章节负责方法，前面的各章负责目标。

## 第三阶段：App 官方优化实践

App 侧最佳实践适合集中补齐。这里不追求把每个 API 背完，而是要能做出可复现 demo。

| 主题 | 章节 | demo 目标 |
|---|---|---|
| Baseline Profile | 8.7、19.15、21.4 | 用 Macrobenchmark 生成 profile，对比无 profile 与 profile 下的启动耗时 |
| Startup Profile / DEX layout | 21.12 | 生成 `startup-prof.txt`，确认 R8/D8 消费路径，并在启动 trace 中区分类加载收益 |
| Macrobenchmark / Microbenchmark | 19.14、15.6 | 固定设备、版本、迭代次数，输出 P50/P90/P95 和方差 |
| App Startup 与 Provider 治理 | 21.3、21.6 | 把隐式 Provider 初始化改成显式依赖图，测首帧前主线程时间 |
| 16KB page size | 4.7、20.13 | 用 NDK/AGP 新版本验证 native 库对齐和加载行为 |
| ADPF | 5.9、25.11、25.16 | 用 PerformanceHintSession / Thermal API 解释帧预算、热状态和调度协作 |
| ProfilingManager | 19.16、26.5 | 从轻量指标触发 system trace 或 heap dump，并把产物关联回 session |

验收标准：每个 demo 都要有测试条件、基线数据、优化后数据、trace 证据和失败边界。只写“官方说能提速”不算完成。

## 第四阶段：线上监控与 APM 原理

线上监控学习要从“低开销、可聚合、可回放”三件事出发。

| 能力 | 章节 | 要掌握的机制 |
|---|---|---|
| 卡顿监控 | 19.2、19.11、19.12、26.3 | Looper Printer、Choreographer、FrameMetrics、JankStats |
| ANR 监控 | 9.3、19.24、20.4、26.4 | SIGQUIT、traces.txt、MessageQueue、系统现场偏移 |
| Java 内存泄漏 | 19.3、23.1、23.7 | HPROF、shark、fork + COW dump、线上采样策略 |
| native 内存与 crash | 20.3、20.11、20.18、23.3 | malloc/mmap hook、unwind、symbolication、MTE |
| 方法级 trace | 19.4、14.13、26.21 | 字节码插桩、ART 方法入口、PLT/inline hook、Perfetto 输出 |
| 可观测性治理 | 15.5、15.9、15.10、26.1-26.8 | 指标发现、重样本取证、版本归因、发布门禁 |

这一阶段要避免一个误区：线上监控不是把线下工具搬进生产环境。线上采集必须说明开销、采样率、失败率、隐私边界、设备分布和结果聚合方式。

## 第五阶段：系统级优化与 OEM 视角

想进入 Framework、系统性能或厂商优化方向，需要把 App 现象和系统资源管理接起来。

| 方向 | 章节 | 工程判断 |
|---|---|---|
| 调度与 CPU | 5.1-5.4、16.4、17.4 | Runnable 等待是系统负载、优先级、cpuset/uclamp，还是应用并发过量 |
| 低内存与回收 | 4.2-4.6、4.15、16.8 | 卡顿是否来自 direct reclaim、zram、LMKD、cached app freezer |
| I/O 与存储 | 6.1-6.4、24.1-24.3 | 主线程 I/O、SQLite fsync、F2FS、文件系统队列如何体现在 trace 中 |
| 图形内存与合成 | 2.6、2.13-2.16、18.1-18.6 | GPU、HWC、dmabuf、sync fence、BufferQueue 的等待点怎么归因 |
| 厂商策略 | 17.1-17.8 | ROM 策略、设备能力、热管理和调度配置如何改变 App 表现 |

这一阶段的输出应该是一组跨层案例。每个案例从 App 现象开始，落到 Framework / native / kernel 的证据，再回到 App 侧可以做什么、系统侧可以做什么、哪些无法在应用内解决。

## 三个月训练安排

| 时间 | 任务 | 产出 |
|---|---|---|
| 第 1-2 周 | Perfetto 基础、trace 抓取、线程状态、FrameTimeline | 3 份 trace 短报告 |
| 第 3-4 周 | 启动、卡顿、ANR 三类问题拆解 | 3 张排查卡片 + 1 个冷启动 demo |
| 第 5-6 周 | Framework 主线：ActivityThread、Looper、Choreographer、Binder | 4 条源码调用链图 |
| 第 7-8 周 | Baseline Profile、Startup Profile、Macrobenchmark、App Startup | 1 个可重复 benchmark 项目 |
| 第 9-10 周 | Matrix、KOOM、btrace、Hook 基础设施 | 2 个最小监控 demo：卡顿 / 内存或 trace |
| 第 11-12 周 | 调度、内存回收、I/O、ADPF、线上取证 | 1 份跨层性能案例报告 |

每周只保留一个主目标。读章节、跑 demo、抓 trace、写报告四件事必须放在同一个问题里完成。

## 最小作品集

读完这条路线，至少应该留下这些可复查产物：

- 3 份 Perfetto trace 分析报告：启动、滑动、ANR。
- 1 个 Macrobenchmark + Baseline Profile / Startup Profile demo。
- 1 个 App Startup / Provider 初始化治理 demo。
- 1 个最小 APM demo：卡顿监控、ANR 现场或内存泄漏任选其一。
- 1 份 Framework 调用链笔记：从 trace slice 回到 AOSP 源码。
- 1 份跨层案例：说明问题如何从 App 现象追到调度、I/O、Binder 或内存回收。

这些产物比“读完多少章节”更重要。性能优化能力的验证方式，是能不能在一个真实问题里拿出证据、排除错误方向，并给出可验证的修改。
