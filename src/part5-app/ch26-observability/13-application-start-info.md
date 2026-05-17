---
title: "ApplicationStartInfo 与启动归因上报"
chapter: "26.13"
status: draft
applicable_versions: "Android 15 (API 35) - Android 17 (API 37)"
tags: [observability, startup, application-start-info, profilingmanager]
related_chapters: ["8.2", "8.10", "14.7", "26.9", "26.12"]
created_by: "task2a-knowledge-gap"
created_date: "2026-05-18"
gap_source: "研究素材/官方文档/章节深挖/Clippings结构参考"
source_refs:
  - "[结构参考: Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 10.md]"
  - "intake/research-gaps.md#2026-05-17-26-12"
  - "developer.android.com/reference/android/app/ApplicationStartInfo"
  - "developer.android.com/about/versions/17/features"
---

# 26.13 ApplicationStartInfo 与启动归因上报

<!-- outline-start -->
## 要点

### 🔹 启动归因在可观测性链路中的位置
把 `ApplicationStartInfo` 放到启动性能、Crash/ANR 补偿和线上诊断证据包之间，明确它解决的是「这次进程为什么被拉起、属于哪类启动、各阶段时间戳如何落盘」。

### 🔹 Android 15 `ApplicationStartInfo` 的字段边界
梳理 `ActivityManager.getHistoricalProcessStartReasons()`、`getStartType()`、`getReason()`、`getStartupTimestamps()`、`START_TIMESTAMP_*` 的可用范围，并标注 API 35 起可用。

### 🔹 冷启动、温启动、热启动的线上分流口径
建立线上指标侧的启动类型分流规则：只把 `START_TYPE_COLD` 纳入冷启动 SLA，把温启动/热启动、后台拉起、广播拉起、Provider 拉起从冷启动指标中拆开。

### 🔹 启动时间戳与业务埋点的合并协议
定义 SDK envelope：系统时间戳、业务首屏时间、`reportFullyDrawn()`、页面 ready、广告/引导扣除、trace id 和版本字段，避免只依赖单一耗时指标。

### 🔹 Android 17 `ProfilingTrigger` 的冷启动触发关系
对齐 `TRIGGER_TYPE_COLD_START` 与 `ApplicationStartInfo.getStartType() == START_TYPE_COLD` 的前提，说明触发式 profiling 与常规启动上报的分工。

### 🔹 数据保留、采样率与隐私边界
覆盖历史记录条数、回调时机、采样率、端侧缓存、脱敏字段、用户同意和结果文件上传策略，避免启动诊断能力演变成无限制日志采集。

### 🔹 与 ApplicationExitInfo 的联合归因
把启动前一次退出原因和本次启动原因合并：崩溃循环、包更新后首启、组件状态变化、低内存杀进程后重启分别进入不同排障路径。

## 扩展

### 🔸 Android 15/16/17 版本矩阵
补一张 API 35 `ApplicationStartInfo`、API 36 `ProfilingManager`、API 37 `ProfilingTrigger` 的能力边界表。

### 🔸 CI 与灰度监控接入
给出 Macrobenchmark、线上 P90/P99、trace 抽样和灰度回滚门禁之间的字段映射。

### 🔸 与 26.12 的拆分边界
26.12 继续讲版本化诊断能力总表；本节只写启动归因上报的 SDK 设计、字段协议和实战排障入口。

<!-- outline-end -->

> 本节内容待加工。
