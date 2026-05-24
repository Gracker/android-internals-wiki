---
title: "Android 17 流媒体网络预算与本地网络权限适配"
chapter: "24.16"
status: draft
applicable_versions: "Android 16 (API 36) - Android 17 (API 37)"
tags: [network, android17, streaming, local-network, connectivity]
related_chapters: ["12.2", "12.4", "16.5", "24.10", "24.11", "24.14", "26.17"]
created_by: "task2a-knowledge-gap"
created_date: "2026-05-24"
gap_source: "研究素材/官方文档/每日信息/Clippings结构参考"
gap_score: 16
material_count: 5
---

# 24.16 Android 17 流媒体网络预算与本地网络权限适配

<!-- outline-start -->
## 要点

### 🔹 场景边界：流媒体限速、本地设备发现与普通 API 请求
区分视频/音频流媒体码率决策、Cast/IoT/局域网设备发现、普通 HTTP API 请求三类网络路径，避免把 Android 17 的连接性变更写成所有网络请求的统一优化入口。

### 🔹 Data Plan Streaming API 的使用边界
梳理 `SubscriptionInfo.getStreamingAppMaxDownlinkKbps()` / `getStreamingAppMaxUplinkKbps()`、`SubscriptionPlan.BITRATE_UNKNOWN`、运营商数据计划和 ABR 码率选择之间的关系。

### 🔹 ACCESS_LOCAL_NETWORK 对局域网链路的影响
覆盖 Android 16 opt-in 到 Android 17 targetSdk 37 强制执行的迁移路径，说明 mDNS、SSDP、本地 HTTP server、投屏和 IoT 控制的权限与降级策略。

### 🔹 与卫星/低带宽网络适配的关系
复用 24.11 的低带宽预算思想，把运营商流媒体速率上限、本地网络权限拒绝和弱网/卫星网络能力合并到请求调度策略中。

### 🔹 TLS 与本地网络权限的取证差异
说明 TLS/ECH/证书失败属于 12.4 的安全连接问题，本地网络权限失败属于权限与目标 SDK 问题；两者在异常类型、日志和用户授权路径上分开记录。

### 🔹 灰度实验与线上指标
设计 targetSdk 36/37 对照、权限授权率、局域网发现成功率、流媒体首缓冲、码率切换、卡顿率和运营商网络分组指标，用于上线验证。

## 扩展

### 🔸 Media3 ABR 与平台流媒体速率上限的映射
记录 Media3/ExoPlayer 的码率估计如何接入运营商上限，避免把瞬时测速和 data plan cap 混成同一个信号。

### 🔸 Cast / IoT 场景的权限替代路径
整理 output switcher、系统选择器和显式 runtime permission 三种路径的产品取舍。

### 🔸 Android 17 网络行为变更回归清单
建立 targetSdk 37 前后的局域网、TLS、卫星/低带宽、DeliQueue 回调投递回归项。

<!-- outline-end -->

> 本节内容待加工。
