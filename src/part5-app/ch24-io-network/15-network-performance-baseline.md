---
title: "移动网络性能优化实战：DNS、连接、传输与容灾"
chapter: "24.15"
status: draft
applicable_versions: "Android 10 (API 29) - Android 17 (API 37)"
tags: [network, cronet, http3, dns, weak-network, performance]
related_chapters: ["12.2", "12.3", "12.4", "24.4", "24.5", "24.10", "24.14", "26.17"]
created_by: "task2a-knowledge-gap"
created_date: "2026-05-22"
gap_source: "参考书素材/官方文档/AOSP结构"
material_sources:
  - "intake/research-gaps.md#2026-05-22-网络性能优化"
  - "Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 18.md"
  - "Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 19.md"
  - "https://developer.android.com/develop/connectivity/network-ops/network-access-optimization"
  - "https://developer.android.com/develop/connectivity/cronet"
---

# 24.15 移动网络性能优化实战：DNS、连接、传输与容灾

<!-- outline-start -->
## 要点

### 🔹 请求阶段拆分
按 DNS、地址选择、TCP/QUIC 建连、TLS 握手、请求发送、首包返回、响应体下载拆分耗时，并给每个阶段绑定可观测字段。

### 🔹 DNS 与地址选择
覆盖系统 DNS、HTTPDNS、DoH/DoT、IPv4/IPv6 选择、TTL、缓存刷新和失败兜底，说明哪些问题应放在 24.10 继续展开。

### 🔹 连接复用与队头阻塞
整理 HTTP/1.1 keep-alive、HTTP/2 多路复用、连接池、域名合并和单连接限速场景，区分复用收益与 TCP 队头阻塞代价。

### 🔹 Cronet、OkHttp 与 Mars 选型
比较三类网络栈的协议支持、弱网能力、长连接支持、平台依赖、接入成本和监控字段，避免把某个库写成通用答案。

### 🔹 HTTP/3、QUIC 与网络切换
说明 HTTP/3/QUIC 在建连、迁移、队头阻塞上的优势，以及 UDP 可达率、回退策略、服务端支持和灰度条件。

### 🔹 弱网容灾策略
覆盖超时、重试、熔断、备用域名、备用 IP、请求分级、幂等保护和流量降级，回连 24.14 的请求分段优化。

### 🔹 数据体积与传输成本
对比 JSON、Protocol Buffers、gzip、Brotli、Zstandard 和业务字典，说明 CPU、流量、服务端成本之间的取舍。

### 🔹 验证与回归防护
给出客户端阶段耗时、接入层日志、Android Vitals、Cronet metrics、Perfetto/network trace 的联合验证方法。

## 扩展

### 🔸 移动网络标准演进
补充 Wi-Fi、蜂窝网络、5G、IPv6、网络切换对 App 请求体验的影响，避免停留在 2019 年网络环境。

### 🔸 安全与性能的取舍
整理 TLS 1.3、0-RTT、证书锁定、代理环境、证书轮换和重放风险的边界。

### 🔸 系统侧网络模块
从 ConnectivityService、DnsResolver、netd 角度补 AOSP 验证锚点，用于区分 App 网络库问题和系统网络问题。

<!-- outline-end -->

> 本节内容待加工。
