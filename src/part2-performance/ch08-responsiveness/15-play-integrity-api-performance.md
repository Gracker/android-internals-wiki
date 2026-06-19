---
title: "Play Integrity API 性能与集成延迟"
chapter: "8.15"
status: draft
applicable_versions: "Android 12 (API 31) - Android 17 (API 37)"
tags: [play-integrity, safetynet, attestation, login-latency, anti-fraud, network-latency]
related_chapters: ["8.12", "8.13", "8.14", "12.03", "12.04"]
created_by: "task2a-knowledge-gap"
created_date: "2026-06-19"
gap_source: "AOSP结构/官方文档"
---

# 8.15 Play Integrity API 性能与集成延迟

<!-- outline-start -->
## 要点

### 🔹 Play Integrity API 的定位与 SafetyNet 替代关系
- Play Integrity API 替代 SafetyNet Attestation API，是 Google Play 服务提供的设备完整性验证接口
- 验证三个维度：MEETS_DEVICE_INTEGRITY、MEETS_BASIC_INTEGRITY、MEETS_STRONG_INTEGRITY
- 从 Android 12 起作为推荐方案，SafetyNet Attestation 已弃用并逐步关停

### 🔹 标准 API 请求与经典 API 请求的性能差异
- 标准 API 请求：Play Store 本地缓存参与判定，减少网络往返，延迟较低
- 经典 API 请求：每次请求都走 Google 服务器校验，延迟高且不稳定
- Android 14+ 强制推荐标准请求，经典请求进入弃用倒计时

### 🔹 集成链路延迟拆解
- 客户端请求延迟：Play Store IPC + 缓存查询 + 网络验证（经典请求）
- Token 获取延迟：标准请求典型 200-500ms；经典请求 500-2000ms
- 服务端解密延迟：服务端调用 Google Play Integrity API 解密 token，额外网络往返

### 🔹 Token 缓存与预热策略
- 标准 API 的本地缓存窗口：Play Store 维护一个时效性窗口，窗口内命中缓存无需网络请求
- 预热方案：在用户进入登录/支付页面前提前请求 token
- 缓存复用边界：token 绑定 requestHash，不可跨请求复用

### 🔹 关键路径上的延迟影响
- 登录链路：Play Integrity 调用串行在登录请求前，直接增加首字节时间
- 支付确认链路：与 3DS、风控审核叠加，放大用户感知延迟
- 反作弊初始化：游戏启动时的完整性检查阻塞渲染

### 🔹 失败与降级处理
- 超时策略：Play Store 服务不可用、网络不可达时的超时设计
- 重试策略：指数退避，避免在弱网下密集请求
- 降级决策：完整性检查失败 vs 超时的不同业务处理路径

### 🔹 Perfetto 与自定义 Trace 埋点
- Play Integrity API 内部无 Perfetto trace 点，需要应用自行埋点
- 推荐指标：token_request_start、token_received、server_verification_start、server_verification_done

### 🔹 Android 17 环境下的变化
- Play Store 版本与 Play Integrity SDK 版本的协同关系
- Android 17 对 Play 服务框架的性能约束（后台限制、执行限制）间接影响 Play Integrity 响应速度

## 扩展

### 🔸 标准 API 缓存机制源码追踪
- com.google.android.play.core.integrity 与 Play Store 内部缓存的交互链路
- [待补充] Play Store app integrity 模块的 AIDL 接口分析

### 🔸 Play Integrity 与 Key Attestation 的互补关系
- Play Integrity 验证应用签名 + 设备完整性
- Key Attestation 验证密钥硬件根
- 两者组合使用的性能代价（详见 8.12 节 Keystore/KeyMint 延迟）

### 🔸 服务端批量验证性能
- 服务端调用 Play Integrity API 的 QPS 限制与配额管理
- 批量解密 token 的性能优化

<!-- outline-end -->

> 本节内容待加工。

[结构参考: 官方文档 developer.android.com/google/play/integrity]
