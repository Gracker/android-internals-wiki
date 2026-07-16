---
title: "Broadcast 性能与跨进程通信开销治理"
chapter: "8.21"
status: draft
applicable_versions: "Android 14 (API 34) - Android 17 (API 37)"
tags: ['broadcast', 'broadcast-receiver', 'ipc', 'ordered-broadcast', 'performance']
related_chapters: ['9.02', '9.09', '9.11']
created_by: "task2a-knowledge-gap"
created_date: "2026-07-16"
gap_source: "素材驱动"
---

# 8.21 Broadcast 性能与跨进程通信开销治理

<!-- outline-start -->
## 要点

### 🔹 Broadcast 分发管线：ActivityManagerService → Binder → Receiver
### 🔹 有序广播 (Ordered Broadcast) 串行化延迟分析
### 🔹 粘性广播 (Sticky Broadcast) 查找与内存开销
### 🔹 正常广播 vs 有序广播 vs 本地广播性能对比
### 🔹 BroadcastReceiver onReceive 执行时间预算与 ANR 边界
### 🔹 Android 17 后台广播限制与性能影响
### 🔹 跨进程广播替代方案：Messenger / AIDL / ContentProvider
### 🔹 广播性能监控：goAsync 与 PendingResult 最佳实践

## 扩展

### 🔸 系统广播性能影响（BOOT_COMPLETED, PACKAGE_*）
### 🔸 广播队列拥塞诊断方法

<!-- outline-end -->

> 本节内容待加工。

<!--
缺口分析摘要：Broadcast 性能仅 6 次提及，ordered broadcast 仅 1 次。BroadcastReceiver ANR（91 次提及）在 ch09 已覆盖，但非 ANR 的性能问题（广播分发延迟、有序广播串行化、粘性广播开销）无专门章节。需覆盖：Broadcast 分发管线性能、有序广播串行化开销、粘性广播内存与查找开销、LocalBroadcastManager 替代方案效率、Android 17 后台广播限制的性能影响。
评分：14/20 ({'素材丰富度': 3, '相关性': 4, '读者需求度': 4, '时效性': 3})
-->
