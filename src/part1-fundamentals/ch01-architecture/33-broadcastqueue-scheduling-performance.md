---
title: "BroadcastQueue 调度与广播性能"
chapter: "1.33"
status: draft
applicable_versions: "Android 8 (API 26) - Android 17 (API 37)"
tags: [broadcast, broadcastqueue, scheduler, AMS, ANR]
related_chapters: ["1.8", "9.2", "5.8"]
created_by: "task2a-knowledge-gap"
created_date: "2026-06-27"
gap_source: "AOSP结构/章节深挖"
---

# 1.33 BroadcastQueue 调度与广播性能

<!-- outline-start -->
## 要点

### 🔹 BroadcastQueue 的两类队列与调度优先级
Normal BroadcastQueue 与 OffloadBroadcastQueue 的区别；优先级队列（PRIORITY_*_APP）如何决定投递顺序；system_server 中 BroadcastQueue 的线程模型。

### 🔹 广播投递全流程：从 sendBroadcast 到 onReceive
Intent 广播从 ActivityManagerService 到目标进程的投递链路；BroadcastRecord 状态机（PENDING → DELIVERED → DONE）；进程拉起延迟对广播投递的影响。

### 🔹 ANR 触发与超时机制
前台广播 10s / 后台广播 60s 超时阈值（Android 14+ 有调整）；BroadcastRecord ANR 的判定逻辑；ANR 弹窗与杀进程策略；如何通过 trace 识别广播 ANR 的根因。

### 🔹 Android 14/17 广播调度变更
Android 14 引入的广播优先级投递（foreground delivery）；Android 17 对 cached app 广播的延迟投递与合并；Deferred delivery 对后台优化的影响。

### 🔹 广播性能优化策略
有序广播 vs 无序广播的性能差异；LocalBroadcastManager 替代方案；registerReceiver 的 export 标志与性能开销；Android 14+ RECEIVER_NOT_EXPORTED 的强制要求与迁移成本。

### 🔹 系统广播的限流与合并
ACTION_SCREEN_ON/OFF 等高频系统广播的合并策略；BIND_* 广播的进程拉起代价；package replace 广播的风暴场景与系统防护。

### 🔹 Perfetto 中的广播性能分析
如何用 Perfetto SQL 定位广播投递延迟；broadcastProcessEvent 的 trace 轨道；BroadcastQueue 相关的 atrace 标签。

## 扩展

### 🔸 Sticky Broadcast 的废弃与替代
Android 5.0+ sticky broadcast 的废弃原因；SharedPreferences / LiveData / Flow 替代方案。

### 🔸 前台服务广播与 FGS 类型联动
Android 14+ FGS 类型声明对广播触发前台服务的限制。

<!-- outline-end -->

> 本节内容待加工。
