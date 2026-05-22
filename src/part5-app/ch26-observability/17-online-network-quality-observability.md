---
title: "线上网络质量监控与接入层协同"
chapter: "26.17"
status: draft
applicable_versions: "Android 8 (API 26) - Android 17 (API 37)"
tags: [observability, network, trafficstats, apm, alerting]
related_chapters: ["19.23", "24.4", "24.10", "26.3", "26.5"]
created_by: "task2a-knowledge-gap"
created_date: "2026-05-22"
gap_source: "参考书素材/知识盲区/官方文档/AOSP结构"
---

# 26.17 线上网络质量监控与接入层协同

<!-- outline-start -->
## 要点

### 🔹 网络监控的分层目标
说明客户端样本、接入层日志和系统网络状态各自回答的问题，避免只用接口总耗时判断网络故障。

### 🔹 客户端阶段耗时采集
覆盖 DNS、建连、TLS、首包、响应体、重试、队列等待等阶段，并说明 OkHttp、Cronet、自研网络库的采集入口差异。

### 🔹 流量与网络状态维度
梳理 TrafficStats、NetworkCapabilities、默认网络切换、VPN/代理/计费网络等维度在归因中的作用。

### 🔹 Native Hook 与统一网络库的边界
对比插桩、PLT Hook、统一网络库、官方指标接口的覆盖面、成本和发布风险。

### 🔹 客户端与接入层对账
说明客户端未到达接入层、接入层秒级告警、客户端维度更丰富三类差异，以及 request id / trace id 的对账方式。

### 🔹 实时告警与离线分析
区分分钟级 PV/错误率告警、小时级维度圈选、P90/P99 尾延迟分析和运营商/地域/CDN 归因。

### 🔹 网络故障证据包
定义一次线上网络故障应保留的字段：网络类型、运营商、域名、IP、协议、错误码、阶段耗时、重试次数和上报通道状态。

## 扩展

### 🔸 QUIC / HTTP/3 指标口径
说明 QUIC 下 TCP/TLS 字段不再直接适用，需要协议类型、连接迁移和 0-RTT 单独建模。

### 🔸 AIOps 报警算法边界
对规则告警、时间序列异常检测和混合策略做工程取舍，标注误报、漏报和历史基线要求。

### 🔸 Wi-Fi 稳定性与系统网络验证
关联 NetworkCapabilities VALIDATED、Captive Portal、厂商 Wi-Fi 质量判断与应用侧可观测边界。

<!-- outline-end -->

> 本节内容待加工。
