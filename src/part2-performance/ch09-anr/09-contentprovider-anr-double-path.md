---
title: "ContentProvider ANR 双路径：Publish 超时与 Call Hang 检测"
chapter: "9.9"
status: draft
applicable_versions: "Android 12 (API 31) - Android 17 (API 37)"
tags: [anr, content-provider, publish-timeout, call-hang, ams]
related_chapters: ["1.10", "9.2", "9.4", "9.7"]
created_by: "task2a-knowledge-gap"
created_date: "2026-06-07"
gap_source: "素材驱动/DeepResearch"
---

# 9.9 ContentProvider ANR 双路径：Publish 超时与 Call Hang 检测

<!-- outline-start -->
## 要点

### 🔹 ContentProvider ANR 的两条正交路径
ContentProvider 在 AOSP 中存在两条独立的 ANR/超时路径：(1) Provider 进程 publish 注册超时（进程初始化失败）；(2) 已发布 Provider 的 call hang 检测（调用方主动开启）。两条路径的触发机制、超时常量、处理流程完全不同，在 Perfetto trace 中表现也不同。

### 🔹 路径 1：Provider Publish 超时（10s × HW_TIMEOUT_MULTIPLIER）
当 AMS 拉起 Provider 进程后，Provider 必须在 `CONTENT_PROVIDER_PUBLISH_TIMEOUT_MILLIS`（默认 10s × HW multiplier）内调用 `publishContentProviders` 注册到 `mProviderMap`。超时后 AMS 调用 `removeProcessLocked` 以 `REASON_INITIALIZATION_FAILURE` 杀进程。这不会弹 ANR 对话框，Perfetto 中无 `am_anr` 事件，但可见 `am_proc_died` + `SUBREASON_UNKNOWN`。

### 🔹 路径 1：超时常量定义与语义
四个超时常量全部定义在 `ContentResolver`（不是 `ContentProviderHelper`）：`CONTENT_PROVIDER_PUBLISH_TIMEOUT_MILLIS`（10s × HW）、`CONTENT_PROVIDER_READY_TIMEOUT_MILLIS`（20s × HW）、`CONTENT_PROVIDER_TIMEOUT_MILLIS`（3s × HW）、`REMOTE_CONTENT_PROVIDER_TIMEOUT_MILLIS`。每个常量对应 AMS 中不同的 `what` 消息码和 `wait()` 条件。

### 🔹 路径 2：Provider Call Hang 检测
已发布的 Provider，调用方通过 `ContentProviderClient.setDetectNotResponding(timeoutMillis)` 主动开启 call hang 检测。超时机制通过 `Handler(Looper.getMainLooper(), null, true /* async */)` 投递 `NotRespondingRunnable`，超时后调用 `mContentResolver.appNotRespondingViaProvider(...)` 进入标准 ANR 流程。

### 🔹 路径 2：ANR 流程与 Perfetto 表现
路径 2 走标准 ANR 流程：`ContentProviderHelper.appNotRespondingViaProvider` → `mAnrHelper.appNotResponding` → `ProcessErrorStateRecord.appNotResponding` → `AppNotRespondingDialog` 弹框。Perfetto 中标记为 `am_anr` 事件，与路径 1 完全不同。

### 🔹 HW_TIMEOUT_MULTIPLIER 对低端机的影响
所有超时基准都乘以 `Build.HW_TIMEOUT_MULTIPLIER`。Performance Class 低端机 multiplier 通常 ≥ 1.5x，意味着 `CONTENT_PROVIDER_PUBLISH_TIMEOUT_MILLIS` 实际可能 ≥ 15s。分析 ANR trace 时必须考虑设备性能等级对超时阈值的影响。

### 🔹 调试方法与 Perfetto SQL
如何在 Perfetto trace 中区分两条路径：路径 1 查找 `am_proc_died` + `SUBREASON_UNKNOWN`（无 `am_anr`），路径 2 查找 `am_anr` + `content_provider` 子类型。提供 SQL 查询模板。

## 扩展

### 🔸 ContentProvider ANR 与应用启动的关系
ContentProvider publish 超时经常发生在应用冷启动阶段，特别是 multi-process 场景下 ContentProvider 进程初始化耗时过长。

### 🔸 HW_TIMEOUT_MULTIPLIER 查询与调试
如何通过 `adb shell getprop ro.hw_timeout_multiplier` 或 `Build.HW_TIMEOUT_MULTIPLIER` 获取实际值，以及在 Perfetto 中关联分析。

### 🔸 ContentProvider ANR 的治理策略
从应用侧和系统侧两个角度总结治理策略：异步初始化、延迟加载、进程拆分等。

<!-- outline-end -->

> 本节内容待加工。
