---
title: "启动优化"
chapter: "8"
status: finalized
---

# 第 8 章：启动优化

“启动”可能指设备开机、system_server 建立服务、应用进程创建，也可能只指一次 Activity 展示。它们的起止点、执行进程和证据来源都不同。本章按这些边界组织阅读，避免用一个时间数字解释所有问题。

本轮正文核查使用以下当前锚点：

- Android 平台：Android 17 / API 37 / `android-17.0.0_r1`
- Android common kernel：`android17-6.18-2026-06_r6`
- AndroidX 等独立库：各专题在正文中单独标明版本

历史版本可以用于解释 API 和实现演进，当前结论不得越过 Android 17。

## 先确定调查对象

| 对象 | 常用起止点 | 主要证据 | 不应混入的指标 |
|---|---|---|---|
| 设备开机 | bootloader/kernel 起点到 boot complete、home ready 等产品里程碑 | bootanalyze、bootstat、init 日志、Perfetto/ftrace | App 的 TTID/TTFD |
| system_server | 进程启动、服务 `onStart()`、boot phase、boot completed | `SystemServerTiming`、`StartService`、`OnBootPhase`、线程状态 | AndroidX `Initializer` 耗时 |
| App 进程与首帧 | process start、`bindApplication`、Provider、`Application.onCreate()`、first frame | `ApplicationStartInfo`、Macrobenchmark、Perfetto | 设备开机总时长 |
| App 可用状态 | launch start 到应用调用 `reportFullyDrawn()`，首帧是中间里程碑 | TTFD、业务 marker、用户路径实验 | 尚未上报的“自动完成时间” |
| 后台工作 | Job 入队到约束满足并开始执行 | JobScheduler pending reason、WorkManager/JobScheduler 状态 | Activity 冷启动类型 |

同一条 Perfetto trace 可以包含多类证据，指标定义仍需分开。开始优化前要写清楚进程、启动类型、起点、终点和重复实验条件。

## 章节导航

### 系统启动与平台服务

- [8.1 Android 17 系统启动优化与 bootanalyze 工具链](./8.1-bootanalyze-optimization-toolchain.md)：bootanalyze、bootstat、init、Zygote、SystemServer 与 Perfetto 的职责边界。
- [8.34 Android 17 SystemServer 启动边界与多进程架构核查](./8.34-android17-modular-startup-framework.md)：系统服务顺序、boot phase 并行、APEX 和应用多进程的区别。

### App 启动数据与诊断

- [21.1 App 启动分析](../../part5-app/ch21-startup/01-startup-analysis.md)：冷/温/热启动、主线程关键路径与常规诊断入口。
- [21.17 Startup Insights API 与启动性能可观测性](../../part5-app/ch21-startup/17-startup-insights-api-observability.md)：Macrobenchmark、AndroidX Startup Insights 与线上观测。
- [26.13 ApplicationStartInfo 与启动归因上报](../../part5-app/ch26-observability/13-application-start-info.md)：启动原因、类型、timestamp map、完成回调与历史记录边界。

### 初始化依赖与调度

- [8.33 Android 17 应用启动边界与 AndroidX App Startup 依赖图](./8.33-android17-modular-startup-framework-dependency-graph.md)：Provider 时序、`Initializer` 依赖、循环检测、手动初始化和多进程配置。
- [8.38 Android 17 任务调度器核查](./8.38-android17-task-scheduler-optimization.md)：区分 DeliQueue、JobScheduler、ADPF、Linux scheduler 和应用初始化框架。
- [8.37 PerformanceHintManager 实战](./8.37-android17-performance-hint-manager.md)：周期性负载的 target/actual duration、Java/NDK 接入与 Android 17 源码路径。

### 启动阶段的内存证据

- [8.39 Android 17 heapprofd 生产环境部署](./8.39-android17-heapprofd-production-deployment.md)：startup native allocation sampling、user build 权限、buffer/guardrail 和符号化。
- [第 4 章：内存管理](../ch04-memory/README.md)：RSS/PSS、ART heap、LMKD、MTE 和进程内存诊断。

## 学习路径

1. 设备开机问题从 8.1 开始，先用事件缩小时间范围，再用 trace 解释阶段内部。
2. App 问题先阅读 21.1，建立冷/温/热启动与 TTID/TTFD 的准确口径。
3. 需要线上归因时阅读 21.17 和 26.13，区分测试工具、平台记录和真实用户采集。
4. 看到“模块化启动”时，按 SystemServer/APEX 与 AndroidX App Startup 两层分别核查。
5. 只有分配、调度或周期性负载证据指向专项问题时，再进入 8.37—8.39。

## 一次可复核的优化流程

1. 固定设备、构建、温度区间、账号状态和启动类型。
2. 记录足够多的未插桩样本，报告中位数、尾部分位值和样本数。
3. 用里程碑把回退缩小到一个阶段，再查看该阶段线程的 running、runnable、sleep、I/O、Binder 和锁等待。
4. 回到 `android-17.0.0_r1` 或对应库版本的源码，确认调用关系、线程和版本边界。
5. 每轮只改变一个可解释变量；修改后同时检查目标指标和内存、功耗、稳定性副作用。
6. profiler 会改变被测进程，heapprofd、method trace 等运行结果不能直接充当无插桩性能基线。

## 历史核查页

目录中保留了一批 `status: deprecated` 的重复稿、错题提纲和失效来源。它们用于记录“为什么某个说法不能继续引用”，默认不进入学习主线；本页明确列出的 8.34、8.38 只负责边界核查。文件顶部的 `task6_*`、`task9_*`、`status`、review 时间和 OpenClaw/Hermes 字段是流水线状态，正文审阅不得删除或擅自重置。

判断一篇历史稿是否可引用，应看提纲之后的审阅结论和它指向的主篇；受保护的 `outline-start`/`outline-end` 区域只保留原始任务上下文，不代表技术结论已经验证。
