---
title: "BiometricPrompt 与 Credential Manager 登录链路性能"
chapter: "8.13"
status: draft
applicable_versions: "Android 9 (API 28) - Android 17 (API 37)"
tags: [responsiveness, biometric, credential-manager, passkeys, keystore]
related_chapters: ["8.12", "20.16", "26.12", "26.15"]
created_by: "task2a-knowledge-gap"
created_date: "2026-05-26"
gap_source: "AOSP结构/官方文档/素材驱动"
---

# 8.13 BiometricPrompt 与 Credential Manager 登录链路性能

<!-- outline-start -->
## 要点

### 🔹 登录链路的关键路径拆分
区分 Credential Manager 账号发现、BiometricPrompt 展示、用户认证、Keystore/KeyMint 签名、服务端校验与页面跳转几段耗时。明确哪一段可由 App 优化，哪一段受系统服务、传感器 HAL、Credential Provider 或网络影响。

### 🔹 BiometricPrompt 的启动与取消成本
梳理 `BiometricPrompt.authenticate()` 会唤醒硬件、展示系统对话框并开始采集的行为，解释快速取消/重启、配置变更、前后台切换对登录体验和错误回调的影响。

### 🔹 Credential Manager 与 Passkey 单击登录
覆盖 Android 15 起 Credential Manager 单击 passkey 创建/登录与 biometric prompt 集成的版本边界，说明单账号、多账号、密码/联合登录回退路径对交互步数和耗时归因的影响。

### 🔹 Keystore/KeyMint 与强生物认证边界
关联 8.12 节，说明只有满足强度要求的 biometric authenticator 才能参与 Keystore 加密操作。把传感器认证成功和密钥签名耗时分开观测，避免把 KeyMint 延迟误归因到 UI。

### 🔹 系统服务与 AOSP 验证入口
列出 BiometricService、BiometricScheduler、CredentialManagerService、SystemUI biometric prompt 与 Keystore/KeyMint 的源码验证点，后续加工时用 AOSP 分支确认线程、Binder 调用和错误码边界。

### 🔹 线上观测与回退治理
设计登录链路埋点：prompt 展示耗时、认证结果类型、错误码、取消来源、credential provider、KeyMint 调用耗时、网络校验耗时、回退方式与最终转化。给出隐私和安全数据最小化原则。

## 扩展

### 🔸 OEM 生物识别实现差异
不同厂商的人脸、指纹、屏下指纹和多模态认证在传感器唤醒、采集失败、锁定策略上的表现差异较大，需要用设备矩阵和错误码分布验证。

### 🔸 与登录稳定性章节的分工
本节聚焦响应速度和可观测性；Keystore 配额、密钥不可用、登录失败治理详见 20.16 节。

### 🔸 Passkey 管理与用户体验
可扩展 Credential Manager passkey 管理、AAGUID 识别、账号恢复和跨设备迁移，但不把安全协议细节展开成身份认证专题。

<!-- outline-end -->

> 本节内容待加工。
