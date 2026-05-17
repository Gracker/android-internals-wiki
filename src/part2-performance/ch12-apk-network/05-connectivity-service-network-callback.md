---
title: "ConnectivityService 与网络状态监听性能"
chapter: "12.5"
status: draft
applicable_versions: "Android 7.0 (API 24) - Android 17 (API 37)"
tags: [connectivity, network-callback, network-performance, power, android-16]
related_chapters: ["12.2", "12.3", "12.4", "24.4", "25.2"]
created_by: "task2a-knowledge-gap"
created_date: "2026-05-17"
gap_source: "官方文档+AOSP结构+每日信息"
gap_score: 15
sources:
  - type: official
    path: "https://developer.android.com/develop/connectivity/network-ops/reading-network-state"
  - type: official
    path: "https://developer.android.com/topic/performance/power/network/action-app-traffic.html"
  - type: official
    path: "https://developer.android.com/topic/performance/background-optimization"
  - type: official
    path: "https://developer.android.com/develop/connectivity/5g/use-network-slicing"
  - type: aosp
    path: "packages/modules/Connectivity/service/src/com/android/server/ConnectivityService.java"
  - type: aosp
    path: "frameworks/base/core/java/android/net/ConnectivityManager.java"
---

# 12.5 ConnectivityService 与网络状态监听性能

<!-- outline-start -->
## 要点

### 🔹 平台网络状态模型
ConnectivityManager、Network、NetworkCapabilities 与 LinkProperties 分别回答“当前有哪些网络”“网络具备什么能力”“连接参数是什么”。本节需要说明这些对象怎样影响应用侧网络调度、弱网判断和请求重试策略。

### 🔹 NetworkCallback 的注册成本与回调边界
`registerDefaultNetworkCallback()`、`registerNetworkCallback()` 和一次性查询的成本不同。需要覆盖回调线程、生命周期解绑、重复注册、弱引用封装和进程后台场景。

### 🔹 CONNECTIVITY_ACTION 限制与后台进程唤醒
Android 7.0 以后，面向 API 24+ 的应用不再通过 manifest 接收 `CONNECTIVITY_ACTION`。本节需要解释这条限制对后台唤醒、功耗和网络状态监听架构的影响。

### 🔹 网络计量、漫游与请求降级策略
`NET_CAPABILITY_NOT_METERED`、蜂窝/无线局域网传输类型、漫游状态和链路带宽估计会影响同步频率、预取窗口、图片质量和日志上报策略。

### 🔹 ConnectivityService 的系统侧分发路径
从应用 API 到 ConnectivityService 的 Binder 调用，再到 NetworkAgent / NetworkMonitor 状态更新，本节只保留排查性能问题需要识别的关键节点。

### 🔹 5G Network Slicing 的适用边界
官方文档单独给出 network slicing 使用路径。需要说明它适合低延迟/高带宽业务的网络能力申请，但是否可用取决于运营商、设备、套餐和系统支持。

### 🔹 与 HTTPDNS、连接池和后台任务的关系
网络状态监听不直接替代 HTTPDNS、OkHttp Dns、连接池或 WorkManager 约束。章节需要把它们的分工说清，避免把所有弱网策略压到一个回调里。

## 扩展

### 🔸 多网络并存与 VPN 场景
同一时刻可能存在蜂窝、无线局域网、VPN、专用网络等多条路径。后续可补多网络选择、绑定 Network 发请求和企业 VPN 下的可观测性。

### 🔸 网络切换期间的请求失败归因
无线局域网切蜂窝、VPN 重连、Captive Portal 和 DNS 缓存失效会把故障混在一起。后续可补 OkHttp EventListener、Connectivity diagnostics 和服务端日志对账方法。

<!-- outline-end -->

> 本节内容待加工。
