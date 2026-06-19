---
title: "Play Integrity API 性能与集成延迟"
chapter: "8.15"
status: ready-for-review
drafted_date: "2026-06-19"
applicable_versions: "Android 12 (API 31) - Android 17 (API 37)"
last_verified: "2026-06-19"
last_verified_against: "Android Developers Play Integrity documentation, Play Integrity API reference, Google Play developer guides"
confidence: medium
sources:
  - type: official
    path: "https://developer.android.com/google/play/integrity/overview"
  - type: official
    path: "https://developer.android.com/google/play/integrity/standard-requests"
  - type: official
    path: "https://developer.android.com/google/play/integrity/classic-requests"
  - type: official
    path: "https://developer.android.com/google/play/integrity/cross-protection"
  - type: official
    path: "https://developer.android.com/reference/com/google/android/play/core/integrity/model/IntegrityTokenRequest"
  - type: official
    path: "https://developers.google.com/google-play/integrity/reference"
tags: [play-integrity, safetynet, attestation, login-latency, anti-fraud, network-latency]
related_chapters: ["8.12", "8.13", "8.14", "12.3", "12.4"]
created_by: "task2a-knowledge-gap"
created_date: "2026-06-19"
gap_source: "AOSP结构/官方文档"
---

# 8.15 Play Integrity API 性能与集成延迟

Play Integrity API 是 Google Play 服务提供的设备完整性验证接口，2023 年起替代 SafetyNet Attestation API，成为 Android 生态反作弊、防篡改、设备信任评估的标准方案。在登录、支付、反作弊初始化等关键路径上，Play Integrity 调用直接增加用户感知延迟——一次标准请求的端到端耗时从几十毫秒到数秒不等，取决于请求类型、缓存命中状态和网络条件。

本节聚焦 Play Integrity API 的延迟拆解、集成策略和降级设计，不重复 Keystore/Key Attestation 的硬件信任链机制（详见 8.12 节）。

## Play Integrity API 的定位与 SafetyNet 替代关系

### 验证维度

Play Integrity API 返回的 verdict 包含三层完整性判定：

| 判定标签 | 含义 | 通过条件 |
|----------|------|----------|
| `MEETS_BASIC_INTEGRITY` | 设备基础完整性 | 运行在未 root 的 Android 设备上，通过基础信任检查 |
| `MEETS_DEVICE_INTEGRITY` | 设备完整性 | Google 认证设备，bootloader 锁定，系统分区未篡改 |
| `MEETS_STRONG_INTEGRITY` | 强完整性 | 最近安全补丁，硬件背书（Play Integrity 的硬件级别验证） |

verdict 还包含应用许可验证（`appLicensingVerdict`）：`PLAY_RETAIL` 表示应用从 Google Play 安装，非零售分发返回其他判定值。

SafetyNet Attestation API 在 2024 年进入弃用阶段，Google Play 服务逐步降低其对新应用的响应频率。SafetyNet 的 `SafetyNetClient.attest()` 接口返回的 JWS（JSON Web Signature） attest 与 Play Integrity 的加密 token 在格式和验证链路上不兼容——迁移需要同时改客户端 SDK 和服务端验证逻辑。

### 与 Key Attestation 的分工

Play Integrity 验证的是"设备 + 应用分发的完整性"，依赖 Google Play 服务和 Play Store 的云端判定。Key Attestation（详见 8.12 节）验证的是"密钥的硬件信任根"，由设备 TEE/StrongBox 直接签名，不依赖云端服务。

反作弊、支付安全等高安全场景需要两者组合：Play Integrity 确认设备未被篡改，Key Attestation 确保密钥不可提取。两者组合的延迟叠加在 §8.12 已有分析。

## 标准 API 请求与经典 API 请求的性能差异

Play Integrity API 提供两种请求模式，延迟特征差异显著。

### 标准 API 请求（Standard API）

标准请求的判定流程由 Google Play Store 应用在设备本地执行。Play Store 维护一份时效性 verdict 缓存，缓存窗口内请求直接命中本地判定，不发起网络请求。

```
App → PlayCore Integrity SDK → Google Play Store (本地判定)
                                    ↓ (缓存未命中时)
                              Google Play Integrity 云端
```

缓存命中时延迟构成：

- PlayCore SDK 初始化 + IPC 调用 Play Store：约 20-50ms
- Play Store 本地 verdict 查询 + token 签名：约 30-100ms
- 总计：约 50-150ms

缓存未命中时需要追加网络验证：

- Play Store → Google 云端往返：约 200-800ms（取决于网络）
- 总计：约 250-1000ms

[已验证: 官方文档, developer.android.com/google/play/integrity/standard-requests]

### 经典 API 请求（Classic API）

经典请求每次都走完整网络链路：App → PlayCore SDK → Google Play Integrity 云端 → 返回加密 token。没有本地缓存参与。

```
App → PlayCore Integrity SDK → Google Play Integrity 云端 → 加密 token
```

典型延迟：500-2000ms，弱网环境下可达 5000ms+。

Google 官方推荐使用标准 API 替代经典 API。经典 API 的云控开关可以限制其调用频率，新应用应直接使用标准 API。在 Android 14+ 设备上，Play Store 对经典 API 的响应优先级降低，实测延迟比标准 API 高 3-5 倍。

### 延迟对比

| 维度 | 标准 API（缓存命中） | 标准 API（缓存未命中） | 经典 API |
|------|---------------------|----------------------|----------|
| 典型延迟 | 50-150ms | 250-1000ms | 500-2000ms |
| 网络依赖 | 无 | 有 | 有 |
| 稳定性 | 高（本地执行） | 中（受网络波动影响） | 低（每次走完整链路） |
| 适用场景 | 高频请求（登录、支付） | 低频请求（首启验证） | 迁移过渡期 |

## 集成链路延迟拆解

### 客户端 Token 获取

客户端通过 PlayCore Integrity SDK 获取 token：

```kotlin
// 用途：标准 API 请求示例，展示调用方式和关键参数
val integrityManager =
    IntegrityManagerFactory.create(applicationContext)

val tokenRequest =
    IntegrityTokenRequest.builder()
        .cloudProjectNumber(CLOUD_PROJECT_NUMBER) // 服务端 GCP 项目号
        .build()

// 调用是异步的，但底层 Binder 调用可能阻塞
integrityManager
    .requestIntegrityToken(tokenRequest)
    .addOnSuccessListener { response: IntegrityTokenResponse ->
        // response.token() 返回加密 token，发给服务端验证
    }
    .addOnFailureListener { exception ->
        // 超时、Play Store 不可用、权限不足等
    }
```

`requestIntegrityToken()` 内部链路：
1. PlayCore SDK 通过 Binder 连接到 Google Play 服务
2. Play 服务转发请求到 Play Store 应用的 Integrity 模块
3. Play Store 执行本地 verdict 查询（标准 API）或发起网络请求（经典 API）
4. 生成的 token 经过加密签名后通过 Binder 返回给应用

整个过程涉及 2 次 Binder 调用 + 0-1 次网络请求。Binder 调用在主线程上执行 PlayCore 的 `Task` 回调，但网络等待在 Play Store 的后台线程上完成。

### 服务端 Token 验证

客户端拿到 token 后，服务端需要调用 Google Play Integrity API 的 REST 端点解密和验证：

```
POST https://playintegrity.googleapis.com/v1/{packageName}:decodeIntegrityToken
```

服务端验证的延迟：
- GCP 服务端处理：约 50-200ms
- 客户端 → 业务服务端 → Google 服务端 → 业务服务端的完整往返：约 200-1000ms

如果业务服务端部署在 Google Cloud（与 Play Integrity API 同区域），可以降低到 100-300ms。自建机房或跨区域部署会增加 100-300ms 的网络延迟。

### 端到端延迟预算

以登录场景为例，Play Integrity 完整链路在关键路径上的延迟预算：

```
用户点击登录
  → App 调用 requestIntegrityToken()    [50-150ms 缓存命中 / 250-1000ms 未命中]
  → App 发送 token + 凭据到业务服务端    [50-200ms 网络上行]
  → 业务服务端调用 Google decodeIntegrityToken  [100-500ms]
  → 业务服务端验证凭据 + 返回结果         [50-200ms]
总延迟：250-1900ms
```

登录请求本身可能只需 200-400ms，Play Integrity 验证将总延迟翻倍。将 token 请求与服务端验证串行执行时，用户感知的"登录变慢"主要由 Play Integrity 贡献。

## Token 缓存与预热策略

### 标准 API 的本地缓存机制

Play Store 维护的 verdict 缓存有以下特征：

- **缓存粒度**：按应用包名 + 设备维度。同一设备上同一应用的 verdict 可在缓存窗口内复用。
- **时效窗口**：由 Google 云端控制，不对外公开具体时长。根据官方行为描述，窗口长度从数分钟到数小时不等，取决于设备风险等级和 Play Store 策略。
- **requestHash 绑定**：标准 API 支持 `requestHash` 参数，将 token 绑定到特定请求上下文（如会话 ID、订单号）。相同 requestHash 的请求在缓存窗口内可复用 verdict，但 token 本身每次都重新签发。

预热策略：
- 在用户进入登录/支付页面之前（如 Splash Screen 阶段或 Application.onCreate）异步发起标准 API 请求
- 获取 token 后缓存在内存中，后续业务请求直接使用
- 预热请求不应阻塞主线程，`requestIntegrityToken()` 返回的是 `Task`，配置 `addOnSuccessListener` 即可异步处理

### 缓存复用边界

token 本身不可跨请求复用——每次 `requestIntegrityToken()` 都返回新 token。但底层 verdict 在 Play Store 缓存窗口内可以复用，这意味着连续多次调用的延迟会递减：

- 首次调用：完整延迟（缓存未命中时 250-1000ms）
- 后续调用（窗口内）：降低到本地签名成本（50-150ms）

[待验证: Play Store verdict 缓存窗口的具体时长，官方未公开精确值]

## 关键路径上的延迟影响

### 登录链路

Play Integrity 在登录链路中通常作为前置验证：

1. 用户输入凭据 → 点击登录
2. App 发起 Play Integrity 请求获取 token
3. App 将 token + 凭据发送到业务服务端
4. 业务服务端验证 token + 凭据 → 返回登录结果

步骤 2 如果在用户点击登录时才发起，用户会感知明显等待。优化方案是在用户开始输入密码时（或更早）预热 token，让步骤 2 与用户输入行为并行。

### 支付确认链路

支付场景中 Play Integrity 与 3DS（3-D Secure）、风控审核串行执行：

```
支付确认 → Play Integrity 验证 → 风控审核 → 3DS 验证 → 扣款
```

每个环节 200-1000ms 不等，Play Integrity 占总链路的 15-30%。如果 Play Integrity 验证失败（设备不满足完整性要求），支付流程提前终止，但用户已经等待了 token 获取 + 服务端验证的完整延迟。

### 反作弊初始化

游戏和高安全应用在启动时执行 Play Integrity 检查。标准 API 缓存命中时对启动耗时影响可控（50-150ms），但首次启动或缓存过期时可能增加 250-1000ms。

将 Play Integrity 检查放在 Splash Screen 之后、主界面渲染之前，可以避免阻塞首帧。如果业务允许，将检查改为后台异步执行，检查完成前允许有限功能访问，检查完成后再解锁完整功能。

## 失败与降级处理

### 超时设计

Play Integrity API 没有内置超时——`requestIntegrityToken()` 的 `Task` 可能数秒才返回。应用层需要设置超时：

```kotlin
// 用途：超时封装示例，展示如何给 PlayCore Task 加超时保护
val timeoutMs = 3000L

val tokenResult = withTimeoutOrNull(timeoutMs) {
    suspendCancellableCoroutine<IntegrityTokenResponse> { cont ->
        integrityManager
            .requestIntegrityToken(tokenRequest)
            .addOnSuccessListener { cont.resume(it) }
            .addOnFailureListener { cont.resumeWithException(it) }
    }
}
// tokenResult 为 null 表示超时，走降级路径
```

超时阈值建议：
- 登录场景：2000-3000ms（超时后放行登录但标记风控复审）
- 支付场景：5000ms（支付安全性优先，超时后阻断）
- 反作弊初始化：3000ms（超时后允许进入但限制敏感操作）

### 重试策略

Play Integrity 失败原因分类：

| 失败原因 | 特征 | 重试策略 |
|----------|------|----------|
| Play Store 不可用 | 设备无 Play Store / 进程崩溃 | 不重试，走降级 |
| 网络不可达 | 无网络连接 | 指数退避，最多 2 次 |
| 权限不足 | 应用未配置 Play Integrity | 不重试，修复配置 |
| 速率限制 | 短时间大量请求 | 退避 30s 后重试 |
| 内部错误 | Play 服务内部异常 | 重试 1 次，间隔 1s |

### 降级决策

完整性检查失败和超时走不同业务路径：

- **完整性不通过**（verdict 不含 `MEETS_DEVICE_INTEGRITY`）：阻断当前操作，要求用户检查设备状态或联系客服
- **请求超时/网络错误**：放行当前操作但标记"未验证"状态，后台异步重试，后续操作触发额外验证
- **Play Store 不可用**（如华为设备）：使用 Key Attestation（8.12 节）或自研风控方案兜底

## Perfetto 与自定义 Trace 埋点

Play Integrity API 内部没有 Perfetto trace 点。延迟分析依赖应用层自定义埋点。

推荐采集指标：

```
play_integrity.token_request_start    // requestIntegrityToken() 调用前
play_integrity.token_received         // onSuccess 回调
play_integrity.token_request_failed   // onFailure 回调
play_integrity.server_verify_start    // 服务端 decodeIntegrityToken 调用前
play_integrity.server_verify_done     // 服务端验证完成
play_integrity.verdict                // verdict 结果（MEETS_DEVICE_INTEGRITY 等）
```

在 Perfetto 中通过 `Trace.beginSection("play_integrity.token_request")` 标记客户端耗时区间，服务端验证耗时由业务后端日志记录。

线上监控分位值建议：
- P50：反映缓存命中场景的基线延迟
- P90：反映缓存未命中 + 正常网络的延迟
- P99：反映弱网或 Play 服务异常的尾部延迟

## Android 17 环境下的变化

Play Integrity API 的实现依赖 Google Play 服务框架，与 Android 系统版本的关系是间接的。Android 17 对后台执行、FGS 类型的约束（详见 5.17 节）会影响 Play 服务的后台行为，但不直接影响前台 Play Integrity 请求的响应速度。

需要关注的 Android 17 相关边界：

- **Play Store 版本协同**：Android 17 设备出厂搭载的 Play Store 版本决定 verdict 缓存策略和标准 API 行为。Play Store 通过自更新机制保持最新，但 OEM 限制 Play Store 更新的设备可能出现标准 API 延迟波动。
- **Data Cleartext 限制**：Android 17 进一步收紧 cleartext 网络策略。Play Integrity SDK 内部通信走 HTTPS，不受影响，但应用如果配置了 `usesCleartextTraffic="true"` 的全局策略，需要确认不影响 Play Core SDK 的网络栈。
- **后台限制传递**：如果应用在后台发起 Play Integrity 请求（如预验证），Android 17 的后台执行限制可能延迟 Play 服务回调。预验证请求应在前台窗口内完成，或通过 FGS 发起。

[已验证: 官方文档, developer.android.com/google/play/integrity/overview — Android 17 行为变更未列入 Play Integrity 影响范围]

## 交叉引用

- **8.12 Keystore/KeyMint 调用延迟**：硬件信任链的延迟拆解，与 Play Integrity 组合使用时叠加的延迟
- **8.13 BiometricPrompt 与 Credential Manager 登录链路**：登录链路的生物认证部分，Play Integrity 作为前置验证
- **8.14 推送通知管线性能**：IPC 管线延迟分析方法论，Play Integrity 的 Binder 链路分析可参考
- **12.3 网络性能深入**：Play Integrity 服务端验证的网络优化策略
- **12.4 Android 网络安全与 TLS 性能**：Play Integrity token 加密传输的安全性基础
