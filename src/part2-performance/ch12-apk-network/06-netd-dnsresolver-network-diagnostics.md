---
title: "netd 与 DnsResolver：DNS 解析性能和故障诊断"
chapter: "12.6"
section: "12.6"
status: draft
applicable_versions: "Android 10 (API 29) - Android 17 (API 37)"
tags: [netd, dnsresolver, network-performance, connectivity, diagnostics]
related_chapters: ["12.2", "12.3", "12.5", "24.4", "24.10"]
created_by: "task2a-knowledge-gap"
created_date: "2026-05-17"
gap_source: "AOSP结构+官方文档+每日信息"
gap_score: 16
sources:
  - type: official
    path: "https://source.android.com/docs/core/ota/modular-system/dns-resolver"
  - type: official
    path: "https://source.android.com/docs/core/architecture/hidl/network-stack"
  - type: official
    path: "https://developer.android.com/develop/connectivity/troubleshoot-network-issues"
  - type: official
    path: "https://developer.android.com/develop/connectivity/network-ops/connecting"
  - type: aosp
    path: "packages/modules/Connectivity/netd/"
  - type: aosp
    path: "packages/modules/Connectivity/service/src/com/android/server/ConnectivityService.java"
---

# 12.6 netd 与 DnsResolver：DNS 解析性能和故障诊断

<!-- outline-start -->
## 要点

### 🔹 DNS 解析在 Android 网络请求里的位置
明确应用 `DnsResolver` / OkHttp `Dns.lookup()`、系统 DNS Resolver 模块、`netd`、网络接口和缓存之间的边界，避免把 DNS、TCP 建连和服务端耗时混在一起判断。

### 🔹 DNS Resolver 模块化后的能力边界
梳理 Android 10 之后 DNS Resolver 主线模块的更新方式、私有 DNS、解析缓存和安全防护范围，标出应用能观测到和不能直接控制的部分。

### 🔹 netd 与 ConnectivityService 的调用关系
从 `ConnectivityService`、`NetworkManagementService`、`NetdService` 到 `packages/modules/Connectivity/netd/` 建立最小调用图，说明网络切换、DNS 配置和链路属性变更如何传到应用侧。

### 🔹 DNS 延迟、失败和网络切换的诊断路径
围绕 `LinkProperties`、DNS server 列表、`NetworkCapabilities`、HTTPDNS fallback、抓包和日志建立排查顺序，区分解析失败、缓存污染、运营商劫持和网络切换后的连接复用问题。

### 🔹 应用层 DNS 优化的边界
把系统 DNS、HTTPDNS、OkHttp `Dns`、异步预取、TTL 缓存、失败隔离和 bootstrap client 放到同一张选型表里，说明哪些优化能降低尾延迟，哪些会引入一致性和可用性风险。

### 🔹 可观测指标与线上告警设计
定义 DNS P50/P90/P99、解析失败率、fallback 命中率、网络切换后的首包失败率、按运营商/地区分桶等指标，避免只用总体网络错误率定位 DNS 问题。

## 扩展

### 🔸 私有 DNS、DoT/DoH 与企业网络兼容性
补充私有 DNS、VPN、企业代理和 Captive Portal 场景下的排查边界。

### 🔸 Tethering offload 与 netd 侧数据面
如素材充分，补充 tethering hardware offload 与普通 App 网络请求诊断的边界。

<!-- outline-end -->

> 本节内容待加工。
