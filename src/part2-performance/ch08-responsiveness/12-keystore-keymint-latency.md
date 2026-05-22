---
title: "Keystore/KeyMint 调用延迟与登录链路性能"
chapter: "8.12"
status: draft
applicable_versions: "Android 6 (API 23) - Android 16 (API 36)"
tags: [keystore, keymint, strongbox, biometricprompt, startup, responsiveness]
related_chapters: ["6.1", "8.2", "8.3", "20.2", "26.3"]
created_by: "task2a-knowledge-gap"
created_date: "2026-05-22"
gap_source: "AOSP结构/官方文档/素材驱动"
---

# 8.12 Keystore/KeyMint 调用延迟与登录链路性能

<!-- outline-start -->
## 要点

### 🔹 调用路径：App → Android Keystore API → keystore2 → KeyMint HAL
加工时需要拆清 Java API、系统服务、HAL、TEE/StrongBox 的边界，说明哪些成本发生在 App 进程，哪些成本来自 Binder 和安全硬件调用。

### 🔹 密钥生成、签名与解密的延迟来源
覆盖 key generation、sign/verify、encrypt/decrypt、attestation 等操作的耗时来源，区分硬件安全、随机数、证书链生成、并发 operation 池和厂商实现差异。

### 🔹 认证绑定密钥与 BiometricPrompt 交互边界
说明 user authentication、validity duration、per-use authentication 与 BiometricPrompt 的关系，避免把用户等待、UI 交互和 KeyMint 计算耗时混在一起。

### 🔹 冷启动和登录流程的线程调度策略
聚焦启动、登录、支付、会话恢复等场景：哪些 Keystore 操作不能放主线程，哪些可以预创建，哪些必须等用户认证后执行。

### 🔹 设备差异：StrongBox、TEE、软件回退与并发限制
按设备能力说明 StrongBox 与 TEE 的延迟和可用性差异，并记录 KeyMint 并发 operation 下的失败码、排队和重试边界。

### 🔹 观测指标与线上归因
建立指标清单：操作类型、算法、provider、是否 StrongBox、耗时分位值、异常码、主线程占用、登录步骤耗时和设备型号。

### 🔹 治理策略：预创建、异步化、超时与降级
给出工程策略：启动前移、后台生成、派生结果缓存、超时保护、失败重试、能力探测和安全降级边界。

## 扩展

### 🔸 KeyMint 并发 operation 池与 vold 占用
AOSP 文档提到 KeyMint operation 并发数量要求；加工时可验证 vold、App 和系统服务并发请求时的资源竞争边界。

### 🔸 Passkey / Credential Manager 与 Keystore 的关系
可补充登录形态变化后，Credential Manager、passkey、硬件密钥和应用会话恢复之间的性能观测口径。

### 🔸 厂商 StrongBox 延迟差异样本
如果后续有实测素材，可补 Pixel、主流国产机、低端机的 key generation / sign / decrypt 分位值对比。

<!-- outline-end -->

> 本节内容待加工。
