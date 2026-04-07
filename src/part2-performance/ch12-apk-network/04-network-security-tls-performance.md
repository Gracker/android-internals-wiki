---
title: "Android 网络安全与 TLS 性能优化"
chapter: "12.4"
status: draft
applicable_versions: "Android 7.0 (API 24) - Android 17 (API 37)"
tags: [network-security, tls, ech, hpke, certificate-transparency, cleartext, performance]
related_chapters: ["12.2", "12.3", "1.6"]
created_by: "task2a-knowledge-gap"
created_date: "2026-04-08"
gap_source: "官方文档+AOSP结构"
gap_score: 14
---

# 12.4 Android 网络安全与 TLS 性能优化

<!-- outline-start -->
## 要点

### 🔹 锚点 1：TLS 握手与连接延迟
- TLS 1.2 vs TLS 1.3 握手次数与延迟对比
- Session Resumption / 0-RTT 对连接延迟的影响
- 在 Perfetto 中观察 TLS 握手耗时的方法
- Android 各版本的 TLS 默认行为差异

### 🔹 锚点 2：Encrypted Client Hello (ECH) 的性能影响
- Android 17 引入 ECH 平台支持
- SNI 加密对 TLS 握手的额外开销
- 对 OkHttp / Cronet 的透明性
- 启用 ECH 后的连接延迟实测数据

### 🔹 锚点 3：Certificate Transparency 的开销
- Android 17 默认启用 Certificate Transparency
- CT 日志验证对 TLS 握手耗时的影响
- 开发者需要了解的性能影响

### 🔹 锚点 4：Cleartext Traffic 弃用的迁移与性能
- Android 17 弃用 usesCleartextTraffic
- HTTP → HTTPS 迁移中的延迟变化
- Network Security Configuration 的性能配置

### 🔹 锚点 5：HPKE 混合加密 SPI
- Android 17 新增 HPKE 支持
- 对安全通信性能的提升
- 适用场景：端到端加密、安全消息

### 🔹 锚点 6：网络性能优化最佳实践
- 连接池配置对 TLS 连接复用的影响
- DNS-over-HTTPS / DNS-over-TLS 的性能权衡
- 网络安全配置的最佳性能实践

## 扩展

### 🔸 扩展点 1：Android 17 ACCESS_LOCAL_NETWORK 权限对本地调试的影响
{localhost 通信需要新权限，ADB/开发工具的影响}

### 🔸 扩展点 2：跨 App localhost 通信的性能替代方案
{USE_LOOPBACK_INTERFACE 权限的影响与替代 IPC 方案}

<!-- outline-end -->

> 本节内容待加工。
