---
title: "Android 版本化线上诊断能力：ApplicationExitInfo、ProfilingManager 与 ProfilingTrigger"
chapter: "26.12"
section: "26.12"
status: draft
applicable_versions: "Android 10 (API 29) - Android 17 (API 37)"
tags: [observability, online-diagnostics, application-exit-info, profiling-manager]
related_chapters: ["26.2", "26.5", "14.7", "8.10", "13.2", "15.5", "20.3", "19.24"]
created_by: "task2a-knowledge-gap"
created_date: "2026-05-17"
gap_source: "研究素材/官方文档/章节深挖"
gap_score: 18
sources:
  - type: research
    path: "/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/DeepResearch/2026-05-15-android-versioned-diagnostic-capabilities.md"
  - type: research
    path: "/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/DeepResearch/2026-05-15-android线上诊断能力版本边界-profiling-trigger.md"
  - type: official
    path: "https://developer.android.com/reference/android/app/ApplicationExitInfo"
  - type: official
    path: "https://developer.android.com/reference/android/os/ProfilingManager"
  - type: official
    path: "https://developer.android.com/topic/performance/tracing/profiling-manager/trigger-based-capture"
  - type: aosp
    path: "frameworks/base/core/java/android/app/ApplicationExitInfo.java"
  - type: aosp
    path: "packages/modules/Profiling/framework/java/android/os/ProfilingManager.java"
  - type: aosp
    path: "packages/modules/Profiling/framework/java/android/os/ProfilingTrigger.java"
---

# 26.12 Android 版本化线上诊断能力：ApplicationExitInfo、ProfilingManager 与 ProfilingTrigger

<!-- outline-start -->
## 要点

### 🔹 诊断能力分层
区分三类官方入口：进程退出追溯、运行时采集、系统事件触发采集。章节要说明它们分别回答什么问题，避免把 Crash/ANR 事后证据、Perfetto system trace 和 heap dump 放进同一套处理口径。

### 🔹 Android 10-14 的降级路径
说明 Android 10 主要依赖 Perfetto、bug report、日志和人工协助；Android 11-14 可用 `ApplicationExitInfo` 做退出原因补偿，但采集范围和 trace 类型有版本边界。

### 🔹 ApplicationExitInfo 的退出证据边界
覆盖 `ActivityManager#getHistoricalProcessExitReasons()`、`ApplicationExitInfo#getReason()`、`getTraceInputStream()`、`REASON_ANR`、`REASON_CRASH_NATIVE`、`REASON_APPLICATION_SPECIFIC_ERROR` 的 API 版本差异和空返回条件。

### 🔹 ProfilingManager 的应用驱动采集
覆盖 Android 15+ `ProfilingManager` / AndroidX Profiling 的 system trace、heap dump、heap profile、stack sampling 四类采集，说明结果回调、文件归档、限流和采集成本。

### 🔹 ProfilingTrigger 与 Extension 版本
覆盖 Android 16/API 36、extension 36.1、Android 17/API 37 的 trigger 差异，区分 `APP_FULLY_DRAWN`、`ANR`、`COLD_START`、`OOM`、`ANOMALY` 等触发器的返回物和使用场景。

### 🔹 证据归档与去重字段
设计一套线上证据归档字段：pid、timestamp、processName、reason、triggerType、profilingType、resultFilePath、caseId、sessionId、appVersion、device、API level。说明 Java crash、native crash、ANR、OOM 和用户手动杀进程如何去重。

### 🔹 隐私、限流与采集成本
说明 trace、heap dump、stack sampling 可能包含业务方法名、对象内容、线程名和用户上下文；采集要有用户授权、字段脱敏、文件加密、保留期限、远程开关和采样上限。

## 扩展

### 🔸 Native crash tombstone 与 Crashpad/Breakpad 补偿
补充 Android 12+ native tombstone protobuf 与 SDK minidump 的关系，区分系统补偿证据和 SDK 自有 crash store。

### 🔸 版本能力表与排障决策表
把 Android 10-14、15、16、17 分成四档，给出“遇到慢启动/ANR/native crash/OOM/进程被杀时先拿什么证据”的决策表。

### 🔸 与 26.5 证据包模板的关系
本节只讲版本化诊断入口和采集边界；26.5 继续保留排障流程、反馈复现、远程日志和灰度处置。

<!-- outline-end -->

> 本节内容待加工。
