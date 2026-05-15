---
title: "Wi-Fi 评分、网络选择与连接切换性能"
chapter: "24.9"
status: draft
applicable_versions: "Android 10 (API 29) - Android 17 (API 37)"
tags: ["wifi", "connectivity", "network", "latency", "scoring", "performance"]
related_chapters: ["12.2", "12.3", "24.4", "24.5", "15.3"]
created_by: "task2a-knowledge-gap"
created_date: "2026-05-15"
gap_source: "AOSP结构/研究素材"
sources:
  - type: aosp
    path: "packages/modules/Wifi/service/java/com/android/server/wifi/WifiNetworkSelector.java"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/ConnectivityService.java"
  - type: blog
    path: "DeepResearch/2026-05-14-android-wifi-scoring-connectivity-service.md"
  - type: official
    path: "https://developer.android.com/reference/android/net/ConnectivityManager"
---

# 24.9 Wi-Fi 评分、网络选择与连接切换性能

<!-- outline-start -->
## 要点

### 🔹 ConnectivityService 与 Wi-Fi 模块分工
说明应用发起网络请求后，ConnectivityService、NetworkAgent、WifiNetworkSelector 各自负责的决策层。

### 🔹 Wi-Fi 评分输入
整理 RSSI、频段、历史连接、网络能力、验证状态、metered 状态和 OEM 配置对候选网络排序的影响。

### 🔹 连接切换的性能指标
定义连接建立耗时、漫游耗时、DNS 恢复耗时、首包耗时和用户感知中断时长的采集口径。

### 🔹 弱网与多网络并存场景
覆盖 Wi-Fi / 蜂窝切换、VPN、Captive Portal、Validated network 失败、网络回退对 App 请求的影响。

### 🔹 应用侧能做什么
整理 NetworkCallback、ConnectivityManager、OkHttp event listener、HTTPDNS 缓存和失败隔离的配合方式。

### 🔹 系统侧证据采集
给出 `dumpsys connectivity`、`dumpsys wifi`、bugreport、Perfetto network counters 和 logcat 标签的观察清单。

## 扩展

### 🔸 OEM Wi-Fi 评分差异
记录厂商在 scoring、漫游阈值、双 Wi-Fi、链路聚合中的常见差异和待验证项。

### 🔸 HTTP/3、QUIC 与网络切换
补连接迁移、0-RTT、连接池复用对移动网络切换体验的影响。

<!-- outline-end -->

> 本节内容待加工。
