---
title: "Android 17 NetworkAgent 生命周期与 NetworkScorecard 动态评分机制"
chapter: "12.8"
status: draft
applicable_versions: "Android 12 (API 31) - Android 17 (API 37)"
tags: [NetworkAgent, NetworkScorecard, ConnectivityService, network-scoring, NetworkRanker, PSI, Android-17]
related_chapters: ["12.5", "12.6", "24.9", "24.16"]
created_by: "task2a-knowledge-gap"
created_date: "2026-06-23"
gap_source: "素材驱动"
confidence: medium-high
sources:
  - type: aosp
    path: "frameworks/opt/net/ConnectivityService/src/com/android/server/connectivity/ConnectivityService.java"
  - type: deepresearch
    path: "DeepResearch/2026-06-22-android17-networkagent-lifecycle-scoring-mechanism.md"
---

# 12.8 Android 17 NetworkAgent 生命周期与 NetworkScorecard 动态评分机制

<!-- outline-start -->
## 要点

### 🔹 NetworkAgent 注册与销毁流程
- `registerNetworkAgentInternal()` 的完整调用链
- NetworkAgentInfo 对象创建与 netId 分配
- NetworkMonitor 启动与验证流程
- `destroyNetwork()` 的资源清理顺序：netd 路由清理 → DNS 缓存销毁 → 速率限制规则清理

### 🔹 NetworkScorecard 评分模型
- Android 17 对 NetworkScorecard 机制的深度重构
- 从静态阈值到动态评分的演进
- 基于 PSI（Pressure Stall Information）的实时系统压力判断
- 评分因子：带宽、延迟、丢包率、信号强度、功耗成本

### 🔹 NetworkRanker 重匹配算法
- `rematchAllNetworksAndRequests()` 的触发时机
- 网络请求与网络提供方的匹配逻辑
- 评分更新后立即触发重匹配的实现
- 多网络共存时的优先级仲裁

### 🔹 NetworkAgent 生命周期状态机
- Android 17 新增的三个关键状态：CREATED → SCORING → SCORED
- 状态转换的触发条件
- 与 NetworkScorecard 的双向绑定关系
- 状态变化对上层 NetworkCallback 的影响

### 🔹 网络切换性能影响
- 网络评分变化触发的网络切换延迟
- 切换过程中的连接保持（handover）机制
- 对 TCP 长连接和 UDP 流的影响
- 应用层 NetworkCallback 的调度延迟

### 🔹 ConnectivityService 与 netd 的协作
- 网络创建/销毁时 netd 的原生网络配置
- DNS 解析器缓存的创建与销毁
- 入口速率限制（ingress rate limit）的管理
- BPF 过滤规则在网络切换时的更新

## 扩展

### 🔸 应用层对网络评分的感知
- NetworkCallback 收到 onAvailable/onLost 的时序与评分的关系
- 应用如何做网络质量感知和差异化策略
- WorkManager/JobScheduler 对网络约束的实际执行逻辑

### 🔸 Wi-Fi 与蜂窝网络共存的评分策略
- OEM 自定义评分权重对网络选择的影响
- Wi-Fi RSSI 阈值与切换触发
- 双连接（Dual Connectivity）场景下的评分

### 🔸 Android 17 PSI 与网络功耗
- PSI 压力信号如何影响后台网络任务的调度
- 低内存场景下网络连接的优先级降级
- 网络评分中的功耗因子权重

<!-- outline-end -->

> 本节内容待加工。
> [结构参考: DeepResearch/2026-06-22-android17-networkagent-lifecycle-scoring-mechanism.md]
> [已验证: AOSP android-17.0.0_r1, frameworks/opt/net/ConnectivityService/]
