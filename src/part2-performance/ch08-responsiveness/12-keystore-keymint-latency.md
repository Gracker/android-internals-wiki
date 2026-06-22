---
title: "Keystore/KeyMint 调用延迟与登录链路性能"
chapter: "8.12"
status: ready-for-review
drafted_date: "2026-05-22"
applicable_versions: "Android 6 (API 23) - Android 17 (API 37)"
last_verified: "2026-05-22"
last_verified_against: "AOSP android-16.0.0_r1, Android Developers Keystore/BiometricPrompt docs, AOSP KeyMint docs"
confidence: medium
sources:
  - type: official
    path: "https://developer.android.com/privacy-and-security/keystore"
  - type: official
    path: "https://developer.android.com/identity/sign-in/biometric-auth"
  - type: official
    path: "https://developer.android.com/reference/android/security/keystore/KeyGenParameterSpec.Builder"
  - type: aosp-doc
    path: "https://source.android.com/docs/security/features/keystore"
  - type: aosp-doc
    path: "https://source.android.com/docs/security/features/keystore/implementer-ref"
  - type: aosp-doc
    path: "https://source.android.com/docs/security/features/keystore/features"
  - type: aosp
    path: "frameworks/base/keystore/java/android/security/KeyStore2.java"
  - type: aosp
    path: "frameworks/base/keystore/java/android/security/keystore2/AndroidKeyStoreKeyGeneratorSpi.java"
  - type: aosp
    path: "frameworks/base/keystore/java/android/security/keystore2/AndroidKeyStoreCipherSpiBase.java"
  - type: aosp
    path: "system/security/keystore2/src/security_level.rs"
  - type: aosp
    path: "system/security/keystore2/src/operation.rs"
  - type: paper
    path: "https://arxiv.org/html/2507.07927v1"
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

登录页里一次看起来普通的解密、签名或硬件认证，可能会穿过 App 进程、`keystore2`、KeyMint HAL、TEE 或 StrongBox。它的性能问题通常不会表现成单一 CPU 热点，而是混在主线程等待、Binder 往返、用户认证、硬件排队和厂商实现差异里。本文把 Keystore/KeyMint 放回启动、登录和支付流程里看，目标是把“安全硬件很慢”拆成可观测、可调度、可降级的几个阶段。

## 调用路径：从 JCA Provider 到安全硬件

Android Keystore 对 App 暴露的是标准 Java Cryptography Architecture Provider。App 调 `KeyStore.getInstance("AndroidKeyStore")`、`KeyGenerator`、`Cipher`、`Signature` 或 `Mac` 时，前半段代码在 App 进程内执行，后半段通过 Binder 进入系统侧 `keystore2` 服务，再由 `keystore2` 调对应安全级别的 `IKeyMintDevice`。[已验证: 官方文档, developer.android.com/privacy-and-security/keystore][已验证: AOSP android-16.0.0_r1, frameworks/base/keystore/java/android/security/KeyStore2.java]

这条路径可以按边界拆成四段：

| 阶段 | 主要对象 | 性能成本 | 观测口径 |
| --- | --- | --- | --- |
| App 进程 | JCA Provider、`AndroidKeyStore*Spi` | 参数组装、对象初始化、`Cipher.init()` / `Signature.initSign()` 阻塞 | App Trace、StrictMode、主线程栈 |
| 系统服务 | `IKeystoreService`、`IKeystoreSecurityLevel` | Binder 往返、权限检查、key blob 读取、operation 管理 | Perfetto Binder、`keystore2` 线程 |
| KeyMint HAL | `IKeyMintDevice.begin()` / `generateKey()` / `finish()` | HAL 调用、operation slot 分配、错误码返回 | AOSP 源码锚点、厂商日志 |
| 安全环境 | TEE、StrongBox KeyMint | 随机数、密钥材料处理、认证 token 校验、证书链签发 | 只能通过端到端耗时和错误码间接观察 |

`AndroidKeyStoreKeyGeneratorSpi.engineGenerateKey()` 在 AOSP 中显式调用 `StrictMode.noteSlowCall("engineGenerateKey")`，随后选择 `TRUSTED_ENVIRONMENT` 或 `STRONGBOX` 安全级别并调用 `generateKey()`。`AndroidKeyStoreCipherSpiBase` 在 `Cipher.init()` 阶段就会调用 `createOperation()`，这一步可能已经拿到 KeyMint operation 和认证 challenge。[已验证: AOSP android-16.0.0_r1, frameworks/base/keystore/java/android/security/keystore2/AndroidKeyStoreKeyGeneratorSpi.java][已验证: AOSP android-16.0.0_r1, frameworks/base/keystore/java/android/security/keystore2/AndroidKeyStoreCipherSpiBase.java]

结论很直接：`Cipher.doFinal()` 慢只是结果，`Cipher.init()`、`Signature.initSign()`、`KeyGenerator.generateKey()` 也可能占用登录路径。线上埋点只包住 `doFinal()`，会漏掉最容易阻塞 UI 的初始化段。

## 延迟来源：生成、operation 与 attestation 分开看

Keystore 相关耗时至少分三类，不同类型的优化手段不同。

| 操作类型 | 常见场景 | 主要延迟来源 | 工程判断 |
| --- | --- | --- | --- |
| key generation | 首次安装、首次登录、开启支付保护 | 随机数、key blob 创建、硬件安全级别选择、证书链或 attestation 参数 | 尽量前移到非首帧、非支付确认路径 |
| begin/update/finish | 登录 token 解密、请求签名、支付确认 | operation slot、Binder、TEE/StrongBox 计算、数据长度 | 控制 payload 大小，保持 operation 生命周期短 |
| attestation | 设备绑定、数字凭证发行、风控建档 | 证书链生成、硬件签名、服务端校验等待 | 不放在冷启动和点击后立即反馈阶段 |

AOSP KeyMint implementer 文档把 `begin()` 描述为创建 cryptographic operation 的入口，并返回 `IKeyMintOperation` Binder 对象；认证绑定操作还会返回 challenge，供认证 token 使用。Android 16 的 `keystore2/src/security_level.rs` 在遇到 `TOO_MANY_OPERATIONS` 时会进入 operation pruning；`operation.rs` 也说明 operation 可能因为 `finish()`、`abort()`、客户端丢弃 Binder 或 pruning 结束。[已验证: 官方文档, source.android.com/docs/security/features/keystore/implementer-ref][已验证: AOSP android-16.0.0_r1, system/security/keystore2/src/security_level.rs][已验证: AOSP android-16.0.0_r1, system/security/keystore2/src/operation.rs]

这解释了一个线上现象：同样的算法、同样的数据长度，耗时分位值会在特定机型或特定时间窗突然拉长。原因不一定是“加密算法慢”，也可能是 operation slot 紧张、系统服务同时请求 KeyMint、StrongBox 资源更少，或者 App 自己把多个未完成的 `Cipher` / `Signature` 操作挂住了。

KeyDroid 论文对软件、TEE 和 Secure Element 形态的密钥性能做了实测，并指出硬件隔离越强，部分加解密场景的运行时成本越高。本文不直接引用其中的具体数值，因为论文设备、payload、provider 和测试环境与线上 App 不同；它适合作为风险提示：不要把 StrongBox 当成默认性能路径。[引用: arxiv.org/html/2507.07927v1]

## 认证绑定密钥与 BiometricPrompt 的边界

认证绑定密钥解决的是“用户认证后才允许使用这个 key”。它通过 `setUserAuthenticationRequired(true)` 和 `setUserAuthenticationParameters(timeout, type)` 配置，`timeout = 0` 表示每次使用 key 都要单独认证；非 0 表示认证成功后的一段时间内可复用授权。Android Developers 文档明确写到，每次使用都要认证的场景由 App 调 `BiometricPrompt.authenticate()` 发起，认证成功后再完成对应 cryptographic operation。[已验证: 官方文档, developer.android.com/privacy-and-security/keystore][已验证: 官方文档, developer.android.com/reference/android/security/keystore/KeyGenParameterSpec.Builder]

登录耗时里要把三段时间拆开：

1. **认证 UI 等待**：从展示 `BiometricPrompt` 到 `onAuthenticationSucceeded()`，主要受用户动作、传感器、系统 UI 和锁屏凭据影响。
2. **operation 初始化**：`Cipher.init()` / `Signature.initSign()` 创建 KeyMint operation，可能已经触发 Binder 和硬件调用。
3. **数据处理**：`doFinal()` / `sign()` / `verify()` 完成实际加解密或签名，受 payload、算法、安全级别和厂商实现影响。

如果把这三段合成一个 `login_biometric_cost`，定位会变得很粗：用户手慢、BiometricPrompt 动画、TEE 签名、StrongBox 排队都会落在同一个桶里。正确做法是按阶段打点，再用同一个 `login_trace_id` 关联。详见 §26.3 的性能指标采集与上报；本文只补 Keystore 维度。

使用 `CryptoObject` 时，App 会把 `Cipher`、`Signature`、`Mac` 或 `KeyAgreement` 交给 `BiometricPrompt`。Android 官方示例也建议把 Keystore 纳入 biometric workflow，用认证结果解锁 cryptographic operation。[已验证: 官方文档, developer.android.com/identity/sign-in/biometric-auth] 对性能排查来说，这意味着 `authenticate()` 之前的 `Cipher.init()` 不能默认算进“用户认证时间”，它已经属于 Keystore operation 准备阶段。

## 冷启动和登录流程的线程调度

Android Developers 文档给出明确约束：cryptographic operations 可能耗时，App 应避免在主线程使用 `AndroidKeyStore`，以免影响 UI 响应，StrictMode 可以帮助发现这类位置。[已验证: 官方文档, developer.android.com/privacy-and-security/keystore]

落到启动和登录流程，可以按下面的顺序安排：

| 时机 | 适合做 | 不适合做 | 备注 |
| --- | --- | --- | --- |
| 冷启动首帧前 | 读取轻量配置、判断是否有登录态 | 生成 StrongBox key、attestation、批量解密历史数据 | 首帧路径参考 §8.2；首帧前只保留展示必需项 |
| 首帧后空闲期 | 预生成非 per-use key、刷新能力探测缓存、预热风控配置 | 长时间占用单个 operation | 与 §8.3 的延迟初始化策略一致 |
| 用户点击登录后 | 初始化本次必需的 `CryptoObject`，展示认证 UI | 在主线程串行 key generation + 网络请求 + JSON 解析 | 后台初始化完成后再回主线程触发 prompt |
| 认证成功后 | 解密小 payload、签名 challenge、换取会话 | 用 StrongBox 直接处理大 payload | 大数据应走普通加密，Keystore 只保护小密钥或小 token |

一个实用边界是：Keystore 适合保护密钥、refresh token、短 challenge 和小块凭据，不适合把大文件、大 JSON、图片或数据库页直接送进安全硬件处理。若业务要加密较大 payload，通常做法是用 Keystore 保护用于数据加密的密钥，数据本身走常规 AES-GCM 流程；是否允许这样做取决于安全策略，不能为了性能偷偷降级。

## StrongBox、TEE、软件回退与并发限制

StrongBox 是 Android 9 之后可选的 KeyMint 形态，设备可通过 `FEATURE_STRONGBOX_KEYSTORE` 暴露能力；App 可用 `setIsStrongBoxBacked(true)` 请求 StrongBox。官方文档也写明，StrongBox 适合物理篡改或侧信道风险更高的场景，但它更慢、资源更受限、并发操作更少，大多数 App 不必默认使用 StrongBox。[已验证: 官方文档, developer.android.com/privacy-and-security/keystore]

设备能力判断要记录“请求值”和“实际值”：

- **请求值**：是否调用 `setIsStrongBoxBacked(true)`，算法、key size、block mode、padding、digest 是否在目标安全级别支持范围内。
- **实际值**：Android 12 及以上可通过 `KeyInfo.getSecurityLevel()` 区分 `TRUSTED_ENVIRONMENT`、`STRONGBOX`、`SOFTWARE` 等安全级别；更老设备只能用较粗的硬件背书判断。[已验证: 官方文档, developer.android.com/privacy-and-security/keystore]
- **失败值**：StrongBox 不可用或参数组合不支持时，AOSP `AndroidKeyStoreKeyGeneratorSpi` 会把 `KM_ERROR_HARDWARE_TYPE_UNAVAILABLE` 转成 `StrongBoxUnavailableException`。[已验证: AOSP android-16.0.0_r1, frameworks/base/keystore/java/android/security/keystore2/AndroidKeyStoreKeyGeneratorSpi.java]

软件回退不能只按性能处理。支付、数字凭证、设备绑定这类场景可能要求硬件安全级别；如果回退到 software-backed key，安全语义已经变化，应让服务端、风控策略或产品流程知道。普通会话恢复场景可以有更宽的降级策略，但也要把 `security_level` 写入日志和服务端样本，避免把安全级别不同的耗时混在同一组分位值里。

并发限制同样要纳入模型。AOSP KeyMint 文档要求实现至少支持 16 个 concurrent operations；Keystore 最多使用 15 个，留下 1 个给 `vold` 做密码加密。文档还说明，当 Keystore 已有 15 个 operation 未 `finish` 或 `abort`，再收到第 16 个请求时，会 abort 最近最少使用的 operation 后再开始新的 operation。[已验证: 官方文档, source.android.com/docs/security/features/keystore/implementer-ref]

这个规则对 App 的直接影响是：不要长时间持有未完成的 `Cipher` / `Signature` / `Mac` 对象，也不要在批量任务里同时拉起大量硬件 backed operation。多线程并发加密不一定提升吞吐，反而可能把 operation slot 打满，导致其他登录、FBE 或系统服务请求被迫等待或失败。

## 线上指标：按阶段、设备和安全级别归因

Keystore 性能埋点必须带维度。只记录一个 `keystore_cost_ms` 没有排查价值。

| 字段 | 示例 | 用途 |
| --- | --- | --- |
| `scene` | `cold_start_restore_session`、`login_biometric`、`payment_confirm` | 区分启动、登录、支付的用户感知 |
| `phase` | `load_key`、`init_operation`、`prompt_wait`、`do_final`、`attestation` | 拆开认证 UI、Binder 和硬件计算 |
| `api` | `Cipher.init`、`Cipher.doFinal`、`Signature.sign`、`KeyGenerator.generateKey` | 定位耗时发生点 |
| `algorithm` | `AES/GCM/NoPadding`、`HmacSHA256`、`EC/P-256`、`RSA/PSS` | 区分算法成本 |
| `security_level` | `TEE`、`StrongBox`、`Software`、`Unknown` | 区分实际安全级别 |
| `strongbox_requested` | `true` / `false` | 区分请求策略与实际落点 |
| `auth_mode` | `none`、`duration_300s`、`per_use_biometric`、`device_credential` | 拆开认证绑定策略 |
| `payload_bytes` | `32`、`256`、`4096` | 判断是否误把大 payload 送进硬件 |
| `duration_ms` | P50 / P90 / P99 | 建立版本、机型和场景基线 |
| `thread` | `main`、`default_executor`、`io_executor` | 识别主线程阻塞 |
| `result` | `ok`、`UserNotAuthenticatedException`、`StrongBoxUnavailableException`、KeyStore error code | 归因失败与降级 |

分位值必须按机型、Android 版本、厂商 ROM、App 版本、安全级别和算法拆分。StrongBox 样本与 TEE 样本合并后，P90/P99 会失真；冷态首次生成 key 与热态签名合并后，也会把一次性建档成本误判成每次登录成本。

Perfetto 侧可以同时看主线程栈、Binder 往返和 `keystore2` 线程活动。App 自定义 Trace 建议包住 `loadKey`、`initCryptoObject`、`biometricPrompt`、`cryptoFinish` 四个阶段，并把网络登录请求独立出来。网络慢和 KeyMint 慢如果共用一个 login span，只能得到“登录慢”这一层结论，看不到可修复点。

## 治理策略：安全边界先定，再谈性能

Keystore 优化不能只追求更快。先定每类 key 的安全级别，再决定能前移、异步化或降级到哪里。

| 策略 | 适用场景 | 风险边界 |
| --- | --- | --- |
| 预创建 key | 首次安装后、首帧后、用户进入安全设置页 | per-use auth key 仍要等认证授权，不能绕过用户动作 |
| 后台初始化 `CryptoObject` | 用户点击登录后到 prompt 展示前 | 初始化超时要回到账号密码或短信流程，不能卡住主线程 |
| 小 payload 原则 | refresh token、challenge、session key wrapping | 大 payload 走普通数据加密，Keystore 只保护密钥 |
| 超时与取消 | 厂商 StrongBox P99 高、operation slot 紧张 | 取消后不要遗留长期未完成 operation；失败码要上报 |
| 能力探测缓存 | StrongBox 特性、算法支持、安全级别 | 缓存按 App 版本、系统版本、biometric enrollment 变化失效 |
| 分级降级 | 普通会话恢复、低风险登录 | 支付、数字凭证、设备绑定要由服务端策略确认是否允许降级 |

工程上更稳的做法是把 key 分级：

- **会话恢复 key**：优先 TEE，允许在低风险场景走可控降级；重点是响应速度和可用性。
- **支付确认 key**：优先硬件 backed，按业务安全要求决定是否必须 StrongBox；重点是安全语义和错误透明。
- **设备绑定 / 数字凭证 key**：关注 attestation 和安全级别；生成和证明过程不放在首帧或高频点击路径。
- **批量数据加密 key**：Keystore 保护 data key，数据加解密由普通 crypto 流程处理；重点是 payload 边界。

## 扩展：operation 池、Passkey 和厂商样本

### KeyMint operation 池与 vold 占用

KeyMint 至少 16 个 concurrent operations、Keystore 使用 15 个并给 `vold` 留 1 个，这不是只面向系统实现者的细节。App 如果在登录、数据库解锁、文件解密、支付 SDK 初始化时同时创建多个 operation，就可能和系统侧请求共享同一组硬件资源。后续做专项测试时，建议压测三类场景：单 operation P99、同 UID 多 operation、跨进程并发 operation，并记录是否出现 `TOO_MANY_OPERATIONS`、`KEY_USER_NOT_AUTHENTICATED`、`StrongBoxUnavailableException` 或 operation 被提前结束。

### Passkey / Credential Manager 与 Keystore 的关系

Credential Manager 是 Android 推荐的统一凭据入口，覆盖 passkey、密码、联合登录和数字凭证。对普通 App 来说，调用 Credential Manager 后看到的是凭据请求耗时、系统 UI 耗时和 provider 返回耗时，不应把它直接等同为本 App 的 `AndroidKeyStore` 耗时。[已验证: 官方文档, developer.android.com/training/sign-in/passkeys]

数字凭证发行侧会接触 Android Keystore attestation。官方 `android_keystore_attestation` proof type 用硬件签名报告证明 key 位于 TEE 或 StrongBox 且不可导出、不可克隆。[已验证: 官方文档, developer.android.com/identity/digital-credentials/credential-issuer/keystore-attestation] 这类流程要单独建 `credential_attestation` 指标，不和本地登录 token 解密放在同一组基线里。

### 厂商 StrongBox 延迟差异样本

当前章节不写固定设备数值。后续如果补实测，应至少给出：设备型号、SoC、Android 版本、是否出厂系统、算法、key size、payload、StrongBox/TEE/software 实际安全级别、冷/热状态、样本量、P50/P90/P99、失败码和是否主线程。没有这些条件，数字只能说明“某次测试慢”，不能支撑线上治理策略。

## 小结

Keystore/KeyMint 性能排查的入口不是“加密慢”，而是把 key generation、operation 初始化、认证 UI、硬件计算、并发 slot 和设备安全级别拆开。启动和登录流程里，主线程只保留展示与调度；安全硬件操作放到后台、短生命周期、小 payload，并用分阶段指标回收证据。安全等级不能被性能优化悄悄改掉，允许降级的场景要在服务端和风控规则里留痕。
