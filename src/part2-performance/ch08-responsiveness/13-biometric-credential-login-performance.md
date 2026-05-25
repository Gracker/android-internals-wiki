---
title: "BiometricPrompt 与 Credential Manager 登录链路性能"
chapter: "8.13"
status: ready-for-review
drafted_date: "2026-05-26"
applicable_versions: "Android 9 (API 28) - Android 17 (API 37); Credential Manager single tap Android 15+"
last_verified: "2026-05-26"
last_verified_against: "Android Developers identity docs, AOSP android-16.0.0_r1 frameworks/base"
confidence: medium
sources:
  - type: official
    path: "https://developer.android.com/identity/credential-manager"
  - type: official
    path: "https://developer.android.com/identity/sign-in/biometric-auth"
  - type: official
    path: "https://developer.android.com/identity/sign-in/single-tap-biometric"
  - type: official
    path: "https://developer.android.com/reference/android/hardware/biometrics/BiometricPrompt"
  - type: official
    path: "https://developer.android.com/reference/androidx/credentials/provider/BiometricPromptData"
  - type: aosp-doc
    path: "https://source.android.com/docs/security/features/authentication"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/biometrics/BiometricService.java"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/biometrics/sensors/BiometricScheduler.java"
  - type: aosp
    path: "frameworks/base/packages/SystemUI/src/com/android/systemui/biometrics/AuthController.java"
  - type: aosp
    path: "frameworks/base/services/credentials/java/com/android/server/credentials/CredentialManagerService.java"
tags: [responsiveness, biometric, credential-manager, passkeys, keystore]
related_chapters: ["8.12", "20.16", "26.12", "26.15"]
created_by: "task2a-knowledge-gap"
created_date: "2026-05-26"
gap_source: "AOSP结构/官方文档/素材驱动"
---

# 8.13 BiometricPrompt 与 Credential Manager 登录链路性能

<!-- outline-start -->
## 要点

### 🔹 登录流程的阶段拆分
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
设计登录流程埋点：prompt 展示耗时、认证结果类型、错误码、取消来源、credential provider、KeyMint 调用耗时、网络校验耗时、回退方式与最终转化。给出隐私和安全数据最小化原则。

## 扩展

### 🔸 OEM 生物识别实现差异
不同厂商的人脸、指纹、屏下指纹和多模态认证在传感器唤醒、采集失败、锁定策略上的表现差异较大，需要用设备矩阵和错误码分布验证。

### 🔸 与登录稳定性章节的分工
本节聚焦响应速度和可观测性；Keystore 配额、密钥不可用、登录失败治理详见 20.16 节。

### 🔸 Passkey 管理与用户体验
可扩展 Credential Manager passkey 管理、AAGUID 识别、账号恢复和跨设备迁移，但不把安全协议细节展开成身份认证专题。

<!-- outline-end -->

登录慢经常被归成“生物识别慢”或“passkey 慢”，但一次登录通常经过凭据发现、系统 UI、用户动作、传感器、Keystore/KeyMint、网络校验和页面跳转。每一段的责任方不同，能优化的动作也不同。本文把 `BiometricPrompt` 和 Credential Manager 放到同一条登录流程里，目标是把用户等待拆成可观测、可回退、可复盘的阶段。

Android Developers 已把初次登录推荐入口转向 Credential Manager；Biometric Prompt 更适合后续重新授权，或者需要自定义认证 UI 文案和加密对象的场景。[已验证: 官方文档, developer.android.com/identity/credential-manager][已验证: 官方文档, developer.android.com/identity/sign-in/biometric-auth]

## 登录流程按阶段归因

面向性能排查时，不要把一次点击后的所有时间合成 `login_cost_ms`。这个总耗时只能说明用户等了多久，不能说明慢在哪里。

| 阶段 | 典型入口 | 责任边界 | 观测口径 |
|---|---|---|---|
| 凭据发现 | `CredentialManager.getCredential()` / `prepareGetCredential()` | App 发起请求，系统服务选择 provider，provider 查询可用凭据 | App trace、provider 类型、候选数量、异常类型 |
| 系统认证 UI | `BiometricPrompt.authenticate()` 或 Credential Manager selector 内嵌认证 | SystemUI 展示 prompt，BiometricService 仲裁 sensor 与 device credential | prompt show、dismiss、error code、取消来源 |
| 用户动作与传感器 | 指纹、面部、PIN / pattern / password | 用户交互、传感器 HAL、锁定策略、环境光和屏幕状态 | `onAuthenticationSucceeded()` / `onAuthenticationError()` 时间、错误码分布 |
| 加密操作 | `CryptoObject`、`Cipher`、`Signature`、passkey assertion | Keystore / KeyMint、TEE / StrongBox、provider 实现 | init/sign/doFinal 耗时、安全级别、payload、失败码 |
| 服务端校验 | token / assertion / challenge verify | 网络、后端、风控、账号状态 | 请求耗时、HTTP 状态、风控拒绝原因 |
| 会话建立与跳转 | 写入本地会话、拉取用户态、进入首页 | App 业务代码、数据库、缓存、首屏渲染 | session write、首页首帧、业务错误 |

这张表决定埋点切法。`CredentialManager` 返回慢，不一定是 provider 慢；可能是用户在系统 UI 上停留。`BiometricPrompt` 成功回调慢，也不一定是传感器慢；如果 App 在回调里串行做 KeyMint 签名、网络校验和 JSON 解析，用户看到的是同一个等待窗口。

8.12 节已经展开 Keystore/KeyMint 的调用路径。这里沿用它的分段方式：登录章节只关心认证 UI、凭据入口和阶段归因，不重复解释 `keystore2`、KeyMint HAL 和 StrongBox 的细节。

## BiometricPrompt 的启动、取消与回调线程

平台 `BiometricPrompt.authenticate(CryptoObject, CancellationSignal, Executor, AuthenticationCallback)` 文档写明，这个调用会预热生物识别硬件、展示系统对话框并开始扫描。调用结束点包括认证成功、认证错误、用户关闭系统对话框或调用方取消；使用 `CryptoObject` 时，对话框关闭后该对象会失效。[已验证: 官方文档, developer.android.com/reference/android/hardware/biometrics/BiometricPrompt]

这条 API 对性能有三个直接影响。

| 行为 | 平台口径 | 工程影响 |
|---|---|---|
| 硬件预热和系统 UI 展示 | `authenticate()` 进入后由系统展示 prompt 并开始扫描 | 从点击到 prompt 可见要单独打点，不能算进传感器识别耗时 |
| 重复发起认证 | 新认证会停止前一次认证，前一次收到 canceled 类错误 | 配置变更、重复点击、页面重建会制造无效取消和额外等待 |
| 回调 executor | 认证回调通过调用方传入的 `Executor` 分发 | 回调里不能串行做网络、解密、数据库写入和页面构建 |

配置变更是最容易制造假慢的场景。屏幕旋转、深色模式切换、Activity 重建、导航返回再进入，都可能让旧 prompt 被取消再重新展示。平台文档也建议不要快速 cancel 再 start；跨配置变更应保留 prompt 所属的组件，避免用户感知到同一次认证被拆成两次。[已验证: 官方文档, developer.android.com/reference/android/hardware/biometrics/BiometricPrompt]

AOSP 的 `BiometricService` 会在 `handleAuthenticate()` 中做预认证检查，确认可用 modality、credential fallback 和 enrollment 状态；通过后创建 `AuthSession`，再和 SystemUI 的 `AuthController.showAuthenticationDialog()` 协作展示对话框。[已验证: AOSP android-16.0.0_r1, frameworks/base/services/core/java/com/android/server/biometrics/BiometricService.java][已验证: AOSP android-16.0.0_r1, frameworks/base/packages/SystemUI/src/com/android/systemui/biometrics/AuthController.java]

`BiometricScheduler` 负责每个 sensor 的 HAL operation 队列。源码注释说明它维护 `BaseClientMonitor` operation 队列，并要求每个 biometric sensor 拥有自己的 scheduler 实例。[已验证: AOSP android-16.0.0_r1, frameworks/base/services/core/java/com/android/server/biometrics/sensors/BiometricScheduler.java] 这解释了一个设备差异：同样是 `authenticate()`，屏下指纹、人脸和侧边指纹的排队、锁定和失败重试表现可能不同。App 侧只能按设备、sensor 类型和错误码间接归因，不应写死一个统一阈值。

## Credential Manager 与 passkey 单击登录

Credential Manager 是 Android 推荐的凭据交换入口，覆盖 passkey、密码、联合登录、数字凭证和跨设备恢复。[已验证: 官方文档, developer.android.com/identity/credential-manager] 从用户视角看，它把“选择账号”和“完成认证”放进统一系统体验；从性能视角看，它增加了 provider 选择、候选凭据查询和系统 UI 协调三类耗时。

AOSP `CredentialManagerService` 是系统侧入口。`executeGetCredential()` 会创建一次 `GetRequestSession`，读取启用的 provider，准备 provider sessions，然后调用各 provider session；`executePrepareGetCredential()` 则用于预取候选结果，减少后续 UI 阶段的等待。[已验证: AOSP android-16.0.0_r1, frameworks/base/services/credentials/java/com/android/server/credentials/CredentialManagerService.java]

Android 15 起，Credential Manager 支持把 passkey 创建和登录的认证信息直接嵌入 biometric prompt。官方 single tap 文档给出三条边界：登录流程只支持单账号场景；provider 要通过 `BiometricPromptData` 明确 `allowedAuthenticator`，未设置时默认值会落到弱设备级认证；如果设备策略要求 `DEVICE_CREDENTIALS`，系统会走标准 Credential Manager 流程，而不是 single tap。[已验证: 官方文档, developer.android.com/identity/sign-in/single-tap-biometric]

这会带来一张版本和形态决策表。

| 场景 | UI 形态 | 性能收益 | 回退边界 |
|---|---|---|---|
| Android 15+ 单账号 passkey | 候选凭据和认证合在同一个 biometric prompt | 少一次 selector 跳转，交互步数更短 | 多账号或 provider 未配置时回到标准选择流程 |
| 多账号 / 多 provider | Credential Manager selector 后再认证 | 用户可选账号和登录方式，归因字段更完整 | 交互更长，候选查询和 provider UI 要拆分计时 |
| 密码 / 联合登录回退 | Credential Manager 或业务登录页 | 提供可用性兜底 | 不与 passkey assertion 混成同一成功率 |
| 设备凭据强制策略 | PIN / pattern / password | 符合设备策略 | single tap provider 可能拿不到 biometric result |

`BiometricPromptData` 的 API 参考页补充了一个约束：它让 provider 把 metadata 和 biometric / device credential 认证放到单一对话框中；如果设置了 `cryptoObject`，`allowedAuthenticators` 必须是 `BIOMETRIC_STRONG`，否则会抛 `IllegalArgumentException`。[已验证: 官方文档, developer.android.com/reference/androidx/credentials/provider/BiometricPromptData]

[自动发现] single tap 的性能收益不能只看“少点一次”。provider 如果没有把账号数量、候选数量、是否命中 active credential、是否进入 standard flow 写入日志，线上只能看到成功率和总耗时变化，无法判断收益来自 UI 减少、provider 查询更快，还是用户群变了。

## Keystore、CryptoObject 与强生物认证边界

`CryptoObject` 把 `Cipher`、`Signature`、`Mac`、`KeyAgreement` 等加密操作交给 `BiometricPrompt`。平台文档把密钥分成两类：auth-per-use key 通过带 `CryptoObject` 的 `authenticate()` 解锁；time-based key 在指定时间窗口内可复用最近一次认证。[已验证: 官方文档, developer.android.com/reference/android/hardware/biometrics/BiometricPrompt.CryptoObject]

使用 `CryptoObject` 时，平台还有强度要求。`BiometricPrompt` 文档说明，只有满足 Android CDD Strong 要求的生物识别认证器才允许和 Keystore 加密操作集成；如果显式允许的生物识别强度不是 `BIOMETRIC_STRONG`，带 `CryptoObject` 的调用会报错。[已验证: 官方文档, developer.android.com/reference/android/hardware/biometrics/BiometricPrompt]

登录埋点要把这些状态拆开。

| 字段 | 示例 | 解释 |
|---|---|---|
| `authenticator_policy` | `BIOMETRIC_STRONG`、`BIOMETRIC_STRONG|DEVICE_CREDENTIAL`、`BIOMETRIC_WEAK` | 决定是否能绑定 Keystore 加密操作 |
| `crypto_mode` | `none`、`auth_per_use_crypto_object`、`time_based_key` | 区分只做身份确认还是解锁 key |
| `crypto_init_ms` | `Cipher.init` / `Signature.initSign` 耗时 | 这一步可能已经进入 Keystore / KeyMint |
| `prompt_wait_ms` | prompt 展示到认证成功或失败 | 主要覆盖用户动作、SystemUI、传感器和锁定策略 |
| `crypto_finish_ms` | `doFinal` / `sign` / `verify` 耗时 | 主要覆盖 KeyMint 操作和 provider 实现 |
| `server_verify_ms` | passkey assertion 或 token 校验 | 属于网络和后端，不应归到系统认证 |

如果用户选择 device credential fallback，是否还能使用 `CryptoObject` 取决于密钥配置和 API 形态。官方 biometric guide 对“biometric 或 lock screen credential”这种 time-based key 给出限制：允许 device credential fallback 时，不能把 `CryptoObject` 传给 `authenticate()`。[已验证: 官方文档, developer.android.com/identity/sign-in/biometric-auth] 因此，登录方案要把“本次只确认用户在场”和“本次要解锁 auth-per-use key”分成两个产品路径。

## 系统服务与源码验证点

排查登录认证慢时，源码入口要按职责查，不要只搜一个类名。

| 模块 | 源码路径 | 用途 |
|---|---|---|
| Framework API | `core/java/android/hardware/biometrics/BiometricPrompt.java` | API 语义、异常、取消和 executor 边界 |
| 生物认证仲裁 | `services/core/java/com/android/server/biometrics/BiometricService.java` | `BiometricPrompt` 请求预认证、创建 `AuthSession`、处理成功/失败/取消 |
| Sensor 调度 | `services/core/java/com/android/server/biometrics/sensors/BiometricScheduler.java` | sensor operation 队列、当前 operation、近期 operation 记录 |
| SystemUI Prompt | `packages/SystemUI/src/com/android/systemui/biometrics/AuthController.java` | 展示认证对话框、处理 owner 前后台、回传 dismiss 和 error |
| Credential Manager | `services/credentials/java/com/android/server/credentials/CredentialManagerService.java` | provider session、get/create/prepare 请求、取消 token |
| Keystore / KeyMint | 详见 8.12 节 | `CryptoObject` 后续的 key operation、StrongBox、TEE 和 operation slot |

AOSP authentication 文档说明，Android 使用 user authenticator 解锁设备并 gate cryptographic keys；Gatekeeper、Fingerprint / biometric 组件通过认证状态和 keystore 服务协作，HAL service 在系统进程接收 Binder 请求，可信应用在安全环境执行安全操作。[已验证: AOSP 文档, source.android.com/docs/security/features/authentication]

这也给 Perfetto 排查一个方向：App 线程只能看到请求发起和回调，系统侧要看 Binder、SystemUI、`system_server` 中 biometric / credential 相关 slice，以及设备厂商是否有可用 sensor HAL 日志。普通线上 SDK 不具备整机 trace 权限，版本化诊断入口详见 26.12 节。

## 线上观测与回退治理

登录观测要服务于两个动作：定位慢在哪一段，决定走哪个回退路径。字段过少会失去定位能力，字段过多又容易碰到隐私和安全边界。

建议的最小事件模型如下。

| 事件 | 触发点 | 关键字段 |
|---|---|---|
| `login_credential_request_start` | 调用 Credential Manager 或业务登录入口 | `flow_id`、`scene`、`api_level`、`credential_types`、`single_tap_expected` |
| `login_credential_candidates` | provider 候选返回或失败 | `candidate_count_bucket`、`provider_kind`、`has_passkey`、`has_password`、`error_type` |
| `login_prompt_shown` | SystemUI prompt 可见或 App 收到等价信号 | `authenticators`、`crypto_mode`、`is_single_tap`、`device_model` |
| `login_auth_result` | 认证成功、失败、取消、锁定 | `result`、`error_code`、`dismiss_reason`、`cancel_source`、`prompt_wait_ms` |
| `login_crypto_result` | 加密操作完成 | `operation`、`security_level`、`duration_ms`、`error_family` |
| `login_server_verify` | 服务端校验完成 | `duration_ms`、`network_type`、`http_family`、`risk_decision` |
| `login_finish` | 进入登录态或回退 | `final_method`、`fallback_reason`、`total_ms`、`conversion_result` |

隐私边界要提前写进 SDK 协议。不要上传指纹、人脸、PIN、明文账号、passkey 原始 assertion、credential ID 全量值、AAGUID 原值或服务端 challenge。需要做 join 时，用服务端生成的 `flow_id`、账号分桶、credential 类型、provider 类型和错误家族就够。AAGUID、credential ID、rpId 这类字段如果业务必须使用，应在端侧做不可逆摘要，并经过安全评审。

回退策略也要分级。

| 失败类型 | 典型信号 | 回退动作 |
|---|---|---|
| 用户取消 | dismiss、negative button、返回键、页面离开 | 保留当前页面，不弹连续 prompt；给账号密码或稍后再试入口 |
| 传感器失败 | timeout、lockout、unable to process | 降低重试频率，提示换手指 / 光线 / 姿态；达到阈值后转 device credential |
| Credential Manager 无凭据 | no credential、provider 空结果 | 展示注册、密码登录或联合登录，不把它记成认证失败 |
| KeyMint / Keystore 失败 | key invalid、auth required、too many keys、StrongBox unavailable | 进入 20.16 的 key 生命周期治理和异常分类，不无限重试 |
| 服务端拒绝 | assertion 校验失败、风控拒绝、账号冻结 | 回到账号安全流程，不归因到系统认证慢 |

Android Vitals 不会给出“登录生物识别慢”这个专门指标，但登录卡死、ANR、崩溃、慢启动、LMK 或电池问题可能在 26.15 的质量指标里反映出来。登录页埋点应能回连 `versionCode`、设备型号、API level、页面、账号态和回退方式，方便把 Play Console 里的外部质量变化接回内部证据。

## OEM 生物识别实现差异

生物识别性能天然带厂商差异。屏下指纹需要屏幕亮度、触控、动画和 sensor 协作；人脸认证受光线、摄像头、活体检测和是否需要确认影响；侧边指纹和后置指纹又有不同的唤醒路径。平台 API 给的是统一回调，不保证每类传感器的 P90/P99 一样。

设备矩阵建议至少按下面几个维度切样本：

- 传感器形态：UDFPS、侧边指纹、后置指纹、2D face、3D face、多模态。
- 系统版本：API level、厂商 ROM 版本、是否升级包、是否 beta。
- 认证策略：`BIOMETRIC_STRONG`、`BIOMETRIC_WEAK`、`DEVICE_CREDENTIAL`、组合策略。
- 场景状态：冷启动后首次认证、页面内二次授权、锁屏刚解锁、前后台切换后、横竖屏切换后。
- 失败类型：timeout、lockout、cancel、sensor privacy、no space、unable to process、user canceled。

没有设备矩阵时，不建议把“认证超过 800ms 就异常”这类阈值写进线上规则。更稳的做法是每个设备族建立 P50 / P90 / P99 基线，再看版本变化和回退转化率。

## 与 20.16 和 26.x 的分工

20.16 负责 Keystore 配额、key 生命周期、异常分类和登录故障恢复；8.13 只使用其中的异常家族做阶段归因。遇到 `ERROR_TOO_MANY_KEYS`、key 失效、StrongBox 不可用或账号退出后 key 残留，应转到 20.16 的治理动作。

26.12 负责版本化线上诊断能力。登录认证问题如果需要系统 trace、`ApplicationExitInfo`、`ProfilingManager` 或系统触发 profiling，不在本文展开 API 细节，只在证据包里保留能关联到 26.12 的 `flow_id`、进程、时间戳和版本信息。

26.15 负责 Play Console 和 Android Vitals 的外部质量口径。登录页引入 passkey single tap 或 biometric fallback 后，内部成功率提高不代表平台质量没有风险；ANR、Crash、LMK、慢启动和功耗指标仍要跟版本放量一起看。

## Passkey 管理与用户体验

passkey 的体验问题不只发生在认证弹窗。账号恢复、跨设备迁移、provider 切换、同一个账号多凭据、密码和联合登录共存，都会影响 Credential Manager 的候选数量和选择路径。性能指标要记录交互形态，不要只记录认证结果。

建议把 passkey 管理拆成三组指标：

| 指标组 | 字段 | 用途 |
|---|---|---|
| 候选凭据 | `candidate_count_bucket`、`has_password`、`has_passkey`、`provider_kind` | 判断用户是否被多账号、多凭据拖慢 |
| single tap 命中 | `single_tap_expected`、`single_tap_used`、`standard_flow_reason` | 判断 Android 15+ 新流程是否按预期生效 |
| 账号恢复 | `restore_source`、`new_device`、`credential_recreated` | 判断换机和重装后的登录路径是否变长 |

AAGUID、attestation、WebAuthn 协议细节属于身份认证专题。本文只把它们当成性能维度：是否改变 provider 返回、服务端校验和回退路径。涉及账号安全策略的结论必须由安全团队确认，不能为了减少一步 UI 交互而降低认证强度。

## 小结

BiometricPrompt 和 Credential Manager 的性能排查入口，是把登录流程拆成凭据发现、系统认证 UI、用户动作、传感器、加密操作、服务端校验和会话建立。App 能优化的是请求时机、重复发起、回调线程、加密操作位置、回退策略和证据字段；传感器 HAL、SystemUI、Credential Provider 和 KeyMint 的差异要通过分阶段指标和设备矩阵回收证据。登录认证既是性能问题，也是安全问题，任何降级都要留下策略来源和服务端判断。
