---
title: "Android 17 ECH 与 domainEncryption 网络适配"
chapter: "24.18"
section: "24.18"
status: draft
applicable_versions: "Android 16 (API 36) - Android 17 (API 37)"
tags: [network, tls, ech, android17, network-security-config]
related_chapters: ["12.4", "24.4", "24.5", "24.16"]
created_by: "task2a-knowledge-gap"
created_date: "2026-05-25"
gap_source: "官方文档/每日信息"
last_verified: "2026-05-25"
last_verified_against: "Android Developers Android 17 behavior changes + API reference"
confidence: medium
sources:
  - type: official
    path: "https://developer.android.com/about/versions/17/behavior-changes-17"
  - type: official
    path: "https://developer.android.com/privacy-and-security/security-config"
  - type: official
    path: "https://developer.android.com/about/versions/17/features"
---

# 24.18 Android 17 ECH 与 domainEncryption 网络适配

<!-- outline-start -->
## 要点

### 🔹 ECH 的 Android 17 适配边界
说明 ECH 只在 Android 17 起可用，且依赖网络库、服务端 HTTPS DNS 记录和远端 ECH 支持，不把平台默认行为写成所有连接必然加密 SNI。

### 🔹 `domainEncryption` 配置方式
整理 `base-config` 与 `domain-config` 的配置位置、文档列出的 mode 取值差异，以及按域名灰度关闭的场景。

### 🔹 网络库支持矩阵
区分 HttpEngine、WebView、OkHttp/Conscrypt 路径，说明配置只有在网络库接入 ECH 后才生效。

### 🔹 失败与回退判定
覆盖 ECH 协商失败、ECH GREASE、标准 TLS 回退、证书透明度默认启用和代理/网关兼容性排查。

### 🔹 性能观测方法
设计 DNS HTTPS 记录查询、TLS 握手耗时、连接复用命中、失败率和地域/运营商维度监控，不给未验证的固定耗时收益。

### 🔹 灰度发布策略
给出白名单域名、关键接口降级、实验分组、抓包限制和隐私合规协同的工程检查项。

## 扩展

### 🔸 与 12.4 TLS 性能章节的边界
12.4 负责 TLS/证书/握手基础，本节只处理 Android 17 ECH 与应用侧配置。

### 🔸 与 24.16 本地网络权限适配的关系
两者都属于 Android 17 网络行为变化，但一个影响公网 TLS 握手，一个影响 LAN 访问权限。

<!-- outline-end -->

> 本节内容待加工。
