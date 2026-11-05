---
title: Android 17 BiometricService 架构与性能优化
chapter: '1.24'
section: '1.24'
status: finalized
applicable_versions: Android 12 (API 31) - Android 17 (API 37)
last_verified: '2026-11-05'
last_verified_against: AOSP android-17.0.0_r1
last_source_verified_at: '2026-11-05'
last_idle_audit_at: '2026-11-05'
confidence: high
sources:
- type: aosp
  path: frameworks/base/core/java/android/app/Activity.java
- type: aosp
  path: frameworks/base/core/java/android/hardware/biometrics/BiometricPrompt.java
- type: aosp
  path: frameworks/base/core/java/android/hardware/biometrics/BiometricManager.java
- type: aosp
  path: frameworks/base/core/java/android/hardware/biometrics/IAuthService.aidl
- type: aosp
  path: frameworks/base/core/res/AndroidManifest.xml
- type: aosp
  path: frameworks/base/services/core/java/com/android/server/biometrics/AuthService.java
- type: aosp
  path: frameworks/base/services/core/java/com/android/server/biometrics/BiometricService.java
- type: aosp
  path: frameworks/base/services/core/java/com/android/server/biometrics/PreAuthInfo.java
- type: aosp
  path: frameworks/base/services/core/java/com/android/server/biometrics/AuthSession.java
- type: aosp
  path: frameworks/base/services/core/java/com/android/server/biometrics/BiometricSensor.java
- type: aosp
  path: frameworks/base/services/core/java/com/android/server/biometrics/BiometricHandlerProvider.java
- type: aosp
  path: frameworks/base/services/core/java/com/android/server/biometrics/sensors/BiometricScheduler.java
- type: aosp
  path: frameworks/base/services/core/java/com/android/server/biometrics/sensors/AuthSessionCoordinator.java
- type: aosp
  path: frameworks/base/services/core/java/com/android/server/biometrics/sensors/fingerprint/FingerprintService.java
- type: aosp
  path: frameworks/base/services/core/java/com/android/server/biometrics/sensors/fingerprint/aidl/FingerprintProvider.java
- type: aosp
  path: frameworks/base/services/core/java/com/android/server/biometrics/sensors/fingerprint/aidl/Sensor.java
- type: aosp
  path: frameworks/base/services/core/java/com/android/server/biometrics/sensors/fingerprint/aidl/FingerprintStartUserClient.java
- type: aosp
  path: frameworks/base/services/core/java/com/android/server/biometrics/sensors/fingerprint/aidl/FingerprintAuthenticationClient.java
- type: aosp
  path: frameworks/base/services/core/java/com/android/server/biometrics/sensors/face/FaceService.java
- type: aosp
  path: frameworks/base/services/core/java/com/android/server/biometrics/sensors/face/aidl/FaceProvider.java
- type: aosp
  path: frameworks/base/services/core/java/com/android/server/biometrics/sensors/face/aidl/Sensor.java
- type: aosp
  path: frameworks/base/services/core/java/com/android/server/biometrics/sensors/face/aidl/FaceStartUserClient.java
- type: aosp
  path: frameworks/base/services/core/java/com/android/server/biometrics/sensors/face/aidl/FaceAuthenticationClient.java
- type: aosp
  path: frameworks/base/packages/SystemUI/src/com/android/systemui/biometrics/AuthController.java
- type: aosp
  path: frameworks/base/packages/SystemUI/src/com/android/systemui/biometrics/UdfpsController.java
- type: aosp
  path: hardware/interfaces/biometrics/fingerprint/aidl/android/hardware/biometrics/fingerprint/IFingerprint.aidl
- type: aosp
  path: hardware/interfaces/biometrics/fingerprint/aidl/android/hardware/biometrics/fingerprint/ISession.aidl
- type: aosp
  path: hardware/interfaces/biometrics/face/aidl/android/hardware/biometrics/face/IFace.aidl
- type: aosp
  path: hardware/interfaces/biometrics/face/aidl/android/hardware/biometrics/face/ISession.aidl
- type: aosp
  path: hardware/interfaces/keymaster/aidl/android/hardware/keymaster/HardwareAuthToken.aidl
- type: official
  path: developer.android.com/reference/android/hardware/biometrics/BiometricManager
- type: official
  path: developer.android.com/reference/android/hardware/biometrics/BiometricPrompt
- type: aosp-doc
  path: source.android.com/docs/security/features/biometric
- type: aosp-doc
  path: source.android.com/docs/security/features/authentication
tags:
  - biometric
  - system-service
  - architecture
  - fingerprint
  - face
  - hal
  - tee
related_chapters:
- '1.10'
- '1.23'
- '21.4'
- '20.10'
---

# Android 17 BiometricService 架构与性能优化

排查“生物识别慢”这类问题时，我们先把一次认证拆开看：它要穿过应用、系统服务、SystemUI、HAL 和安全环境好几层，每层各有各的职责，也各有各的耗时方式。这篇文章讨论应用通过系统认证面板 `BiometricPrompt` 发起的认证；锁屏直接调用 `FingerprintManager`、录入流程和厂商私有解锁通道属于其他路径。

> 源码基线：Android 17 / API 37 / AOSP `android-17.0.0_r1`。

`BiometricService` 是一次 BiometricPrompt 会话的仲裁者，但它不是应用直接访问的第一个 Binder 服务，图像采集和模板匹配也发生在别处。应用入口、系统策略、会话状态、传感器队列、认证 UI 与安全执行环境分属不同组件。定位慢在哪里，就要先判断时间消耗落在哪一段。

## 真实调用链

### 进程与接口边界

先约定几组与源码一一对应的术语：

- provider：管理一种模态的一组传感器；
- `BiometricScheduler`：为单个传感器串行调度任务；
- client：一次认证、录入或枚举任务；
- operation：client 发给 HAL 的具体操作；
- session：framework 与 HAL 为当前用户复用的会话接口；
- HAL（硬件抽象层）：连接 Android framework 与厂商实现；
- AIDL 与 HIDL：前者用于当前稳定接口，后者是旧版接口技术，Android 17 仍保留兼容适配；
- HAT（`HardwareAuthToken`）：安全环境生成、可供 Keystore 验证的认证令牌。

整条链路可以放进一张进程图里，先看 SDK、`system_server`、SystemUI、HAL 与安全环境各自负责的部分：

```text
App process
  BiometricPrompt / BiometricManager
          │ IAuthService
          ▼
system_server
  AuthService
    ├─ 权限、AppOps、前台状态与 PromptInfo 检查
    └─ 调用内部 IBiometricService
          ▼
  BiometricService
    ├─ PreAuthInfo：计算当前可用认证器
    ├─ AuthSession：管理一次 Prompt 会话
    └─ BiometricSensor：包装已注册认证器
          │ IBiometricAuthenticator
          ├──────────────────────────────┐
          ▼                              ▼
  FingerprintService                FaceService
    → Provider                        → Provider
    → per-sensor Scheduler            → per-sensor Scheduler
    → AuthenticationClient            → AuthenticationClient
          │ AIDL ISession，或旧 HAL 兼容适配
          ▼
vendor biometric HAL process
          │ vendor-defined secure channel
          ▼
secure isolated environment
  采集保护、模板保护、匹配、Strong 认证的 HAT 生成

system_server ── IStatusBarService ──► SystemUI process
  AuthSession                          AuthController / AuthContainerView
       ◄──────── IBiometricSysuiReceiver ────────┘
```

其中四个地方最容易混淆：

1. `BiometricPrompt.Builder.build()` 从 `Context.AUTH_SERVICE` 取得 `IAuthService`。普通应用不直接持有 `IBiometricService`。
2. `AuthService` 与 `BiometricService` 都在 `system_server`，前者是 SDK 入口与访问控制层，后者是内部仲裁层。
3. `AuthController` 运行在独立的 SystemUI 进程，不属于 `system_server`。
4. HAL 运行在 vendor 侧进程；采集、模板与匹配的安全要求由安全隔离环境及厂商实现满足。TEE 是 Trusted Execution Environment（可信执行环境），说的是安全隔离环境这一侧；HAL 进程本身在 vendor 侧，两层要分开称呼。

<!-- gracker-diagram: ch01-24-biometric-boundaries -->
![BiometricPrompt 的访问控制、仲裁和硬件边界](../../assets/diagrams/ch01/ch01-24-biometric-boundaries.png)

图：应用先访问 AuthService，再由 BiometricService 仲裁 Prompt 会话；对应模态的 provider 和单传感器 scheduler 执行操作。SystemUI 负责面板交互，HAL 与安全隔离环境承担各自的硬件和安全职责。

对应源码入口：

- `BiometricPrompt.Builder.build()`：`core/java/android/hardware/biometrics/BiometricPrompt.java`
- `AuthService.onStart()`：发布 `Context.AUTH_SERVICE`
- `BiometricService.onStart()`：发布内部 `Context.BIOMETRIC_SERVICE`
- `AuthController`：实现 `CommandQueue.Callbacks`，接收状态栏 Binder 命令。

### `authenticate()` 如何进入系统

我们从应用这一端开始。`BiometricPrompt.authenticate()` 在应用进程完成参数检查，保存调用方提供的 `Executor`（决定回调在哪个线程执行）和 `AuthenticationCallback`，然后调用：

```java
final long authId = mService.authenticate(
        mToken,
        operationId,
        userId,
        mBiometricServiceReceiver,
        mContext.getPackageName(),
        promptInfo);
```

从这段调用能确认两个事实：

- `CryptoObject` 存在时，`operationId` 来自关联的加密操作；没有 `CryptoObject` 时为 `0`。
- 内部返回值是请求 ID，用于后续取消和回调关联。公开的 `authenticate()` 仍以异步回调向应用报告结果。

`AuthService.authenticate()` 随后检查：

- 同用户调用所需的生物识别权限；跨用户调用所需的内部权限；
- AppOps 是否允许；
- token、receiver、包名和 `PromptInfo` 是否为空；
- 调用 UID/PID 是否位于前台；
- 非公开、测试或高级 prompt 选项所需的额外权限。

通过检查后，`AuthService` 清除来访 Binder identity，避免后续系统内部调用继续沿用应用身份，再把请求交给内部 `BiometricService`。

`BiometricServiceWrapper.authenticate()` 只做内部权限、参数和认证器配置检查，然后把后续工作投递到专用 Handler 所在线程，应用的 Binder 调用栈到这里就返回了。所以公开的 `authenticate()` 快速返回时，它可能只是应用侧或服务入口的拒绝；要确认认证器已经开始采集，还要看后面的会话与 sensor 回调。

### 新请求如何处理旧会话

入口都通过之后，下一个问题就是新请求撞上旧会话。`BiometricService` 只有一个 `mAuthSession`：新请求通过预认证、进入系统侧 `authenticateInternal()` 创建会话时，如果旧会话还在，系统会先调用它的 `onCancelAuthSession(true)`，再用新会话替换 `mAuthSession`。对仍在认证的旧会话，这会请求取消传感器、关闭旧 UI，并向旧客户端返回取消；已经认证并确认的会话则在取消函数入口直接返回。每个传感器的 `BiometricScheduler` 各有操作队列，Prompt 仲裁层不把这些新会话逐一排队。

同一个 `BiometricPrompt` 对象还有应用侧的限制。`authenticateInternal()` 先保存本次传入的 Executor 和 callback；若 `mIsPromptShowing` 已为 `true`，就向该 callback 投递 `BIOMETRIC_ERROR_CANCELED`，内部返回 `-1`，不会调用 `IAuthService.authenticate()`。这个分支只挡住了本次调用，系统里的原会话照常运行，后续原会话事件仍会经该对象当前保存的 callback 交付。

公开 API 文档把重复调用概括为停止旧客户端、启动新认证。落到这个版本的实际行为上，我们要区分两种情形：同实例的本地拒绝，以及另一实例发出的请求到达系统后的会话替换。收到一次取消错误时，原 HAL operation 是否已经停止，还要看 sensor 侧的终止回调。

所以应用侧要在发起请求前挡住重复提交，配置变化、重复点击或状态重组时，也别快速走一遍“取消—重建—认证”。反复重建会增加 UI、HAL 取消确认和 scheduler 队列清理开销；同实例重复调用还可能覆盖 callback，让本地错误和原会话结果交给同一个回调对象。

## 预认证：`PreAuthInfo` 决定谁有资格参与

请求进入系统侧，我们先看资格判断。`BiometricService.handleAuthenticate()` 先创建 `PreAuthInfo`，读取请求、传感器属性、用户状态和系统策略，生成：

- `eligibleSensors`：本次可以参与的传感器；
- `ineligibleSensors`：传感器及其不可用原因；
- `credentialRequested` / `credentialAvailable`；
- 是否需要确认；
- 生物识别强度和 Identity Check（在受保护场景要求强生物识别的系统能力）相关状态。

### 资格判断项

| 检查项 | Android 17 的判断依据 | 常见结果 |
| --- | --- | --- |
| 请求强度 | `BIOMETRIC_STRONG`、`BIOMETRIC_WEAK` 等位掩码（bit field） | 传感器强度不足 |
| 运行时强度 | OEM 声明强度与 `BiometricStrengthController` 更新值 | 安全更新前需降级 |
| 硬件状态 | `isHardwareDetected()` | 硬件不可用 |
| 录入状态 | `hasEnrolledTemplates()` | 尚未录入 |
| 锁定状态 | `getLockoutModeForUser()`；预认证分支显式挡下限时锁定 | 限时锁定；永久锁定还可能通过后续 sensor error/lockout 回调进入会话处理 |
| 用户设置 | 是否允许应用使用该模态 | 对 App 禁用 |
| 设备策略 | DPM（Device Policy Manager，设备策略管理器）是否禁用指纹、人脸或虹膜 | 被管理策略禁用 |
| 人脸相机 | 相机可用性和相机隐私开关 | 相机不可用或隐私限制 |
| 设备凭据 | `TrustManager.isDeviceSecure()` | PIN/图案/密码不可用 |
| 显示环境 | 外接或受控虚拟显示相关策略 | 当前显示不允许认证 |

`canAuthenticate(authenticators)` 复用这类信息计算公开结果。它是调用时刻的状态快照，既没有预留传感器，也不对稍后的 `authenticate()` 结果做出保证——前后台状态、相机隐私、锁定、用户切换、另一个认证会话和 HAL 健康状态都可能在两次调用之间变化。

对应到应用侧，正确的策略是：

- 用 `canAuthenticate()` 决定是否展示入口或引导录入；
- 仍以 `AuthenticationCallback` 作为本次认证的最终结果；
- 不因为预检查成功而忽略错误回调。

### 强度由安全等级决定

指纹、人脸是认证模态，Class 3、Class 2、Class 1 是安全等级，两组概念要分开看。设备装了二维相机，安全等级未必到 Class 2；装了深度相机，也未必到 Class 3；等级要靠设备实现按 CDD（Compatibility Definition Document，兼容性定义文档）的架构安全与抗欺骗要求声明并通过测试来确立。

Android API 的能力边界是：

| 类型 | BiometricPrompt | Keystore 定时授权 | Keystore 单次操作授权 |
| --- | --- | --- | --- |
| `BIOMETRIC_STRONG` / Class 3 | 支持 | 支持 | 支持 |
| `BIOMETRIC_WEAK` / Class 2 | 支持 | 不支持 | 不支持 |
| Class 1 / Convenience | 不进入公开 BiometricPrompt API | 不支持 | 不支持 |
| `DEVICE_CREDENTIAL` | 支持 | 支持 | 支持 |

`BiometricSensor.getCurrentStrength()` 将 OEM 声明值与运行时更新值按位掩码合并，结果不会比 OEM 初始声明更强。安全更新导致的降级会直接影响 `PreAuthInfo` 的资格判断。

API 37 增加了受角色和权限限制的 `BiometricManager.getBiometricSensorStrengths()`。调用方必须位于前台，同时持有 `USE_BIOMETRIC` 和角色授予的 `ACCESS_BIOMETRIC_SENSOR_STRENGTHS`；框架权限注释列出的授予范围是钱包、设备策略管理，以及便于测试的 system shell。返回结果把每种模态映射到 `BIOMETRIC_STRONG` 或 `LESS_THAN_STRONG`，Class 3 以下的细分等级对外不可见。普通应用仍应使用 `canAuthenticate()`。

## 传感器发现、注册与会话复用

参与认证的传感器，要先把注册信息登记到 `BiometricService`。我们顺着启动流程看注册顺序，再看每个 `BiometricSensor` 保存什么状态、AIDL session 何时复用。

### 注册从 `AuthService.onStart()` 发起

源码在 `AuthService` 中给出了注册顺序：

```text
AuthService.onStart()
  → registerAuthenticators()
    → FingerprintService.registerAuthenticators()
      → providers → sensors
        → BiometricService.registerAuthenticator()
    → FaceService.registerAuthenticators()
      → providers → sensors
        → BiometricService.registerAuthenticator()
    → IrisService.registerAuthenticators()
```

`BiometricService` 用 `CopyOnWriteArrayList<BiometricSensor> mSensors` 保存注册结果。源码中没有 `SensorListState`。

Android 17 优先支持稳定 AIDL HAL，同时仍有 HIDL 配置和 `HidlToAidlSessionAdapter` 等兼容路径。分析具体设备时，我们查看 provider 类型和 HAL instance（已注册的 HAL 服务实例）来确认走哪条路，单凭系统版本下不了结论。

### `BiometricSensor` 保存什么

每个 `BiometricSensor` 只包装仲裁所需的少量状态：

- `id`、`modality`；
- OEM 声明强度和运行时强度；
- `IBiometricAuthenticator impl`；
- 当前 sensor state；
- 用于关联准备请求与回调的 cookie，以及最近错误。

它手里没有模板内容，也没有 `lockoutState` 字段；锁定状态通过对应 sensor service/provider 查询，并由 sensor 侧 tracker（状态跟踪器）与 `AuthSessionCoordinator` 协调。

### AIDL session 何时复用、何时重建

Fingerprint 和 Face AIDL 的每个 sensor 都维护 `mCurrentSession`，provider 通过这些 sensor 与 scheduler 驱动当前用户的 HAL 会话。用户匹配且 session 健康时，认证 client 复用它；切换用户、HAL 死亡或 session 关闭时才创建或替换。

创建路径的接口形态是：

```aidl
interface IFingerprint {
    SensorProps[] getSensorProps();
    ISession createSession(int sensorId, int userId, ISessionCallback cb);
}

interface IFace {
    SensorProps[] getSensorProps();
    ISession createSession(int sensorId, int userId, ISessionCallback cb);
}
```

所以 `createSession()` 是冷路径开销，摊不进每次 BiometricPrompt 的延迟；trace 中出现用户切换、HAL 重连或 start-user client（为新用户建立 HAL 会话的任务）时，我们把它单独标记为冷路径。

## 两层状态机：Prompt 会话与单个传感器

一次 Prompt 会话里有两层状态在同时推进：`AuthSession` 记录整次会话走到哪一步，每个 `BiometricSensor` 记录自己的准备与认证状态。我们把两层分开看，排查时才不会张冠李戴。

### `AuthSession` 管理整次 Prompt

主要 session state 为：

| 状态 | 含义 |
| --- | --- |
| `STATE_AUTH_IDLE` | 尚未准备认证 |
| `STATE_AUTH_CALLED` | 已让候选传感器准备，等待 cookie |
| `STATE_AUTH_STARTED` | 非指纹传感器已可启动，Prompt 已请求显示 |
| `STATE_AUTH_STARTED_UI_SHOWING` | UI 动画完成，允许启动指纹 |
| `STATE_AUTH_PAUSED` | 可重试模态暂停 |
| `STATE_AUTH_PAUSED_RESUMING` | 正在为重试重新准备传感器 |
| `STATE_AUTH_PENDING_CONFIRM` | 匹配成功，等待用户显式确认 |
| `STATE_AUTHENTICATED_PENDING_SYSUI` | 已认证，等待 SystemUI 完成收尾 |
| `STATE_ERROR_PENDING_SYSUI` | 错误已暂存，等待 UI 完成展示 |
| `STATE_SHOWING_DEVICE_CREDENTIAL` | 转入 PIN、图案或密码 |

客户端 Binder 死亡时还会进入 `STATE_CLIENT_DIED_CANCELLING` 清理路径。源码的 `@IntDef` 没有把这个值列入主状态集合，但处理分支存在。

`AuthSession` 只有一个 `mState`。源码中没有 `AUTH_STARTED_FACE` 和 `AUTH_STARTED_FINGERPRINT` 这类并行 session state。多传感器进度由每个 `BiometricSensor` 的状态分别记录。

### `BiometricSensor` 管理单个传感器

单传感器状态为：

```text
UNKNOWN
  → WAITING_FOR_COOKIE
  → COOKIE_RETURNED
  → AUTHENTICATING
  → CANCELING
  → STOPPED
```

cookie 是一次准备请求的关联值，用来把下面这些动作对应起来：

1. `AuthSession` 为每个 eligible sensor 生成非零 cookie。
2. `BiometricSensor.goToStateWaitingForCookie()` 调用 `prepareForAuthentication()`。
3. 对应 provider 创建 authentication client，并把它放入该传感器的 scheduler。
4. client 到达队首且可以开始时，scheduler 通过 `onReadyForAuthentication(requestId, cookie)` 通知 `BiometricService`。
5. 所有 cookie 返回后，`AuthSession` 再调用 `startPreparedClient(cookie)`。

这套“准备—就绪—启动”握手避免 Prompt 仲裁层在 sensor operation 尚未到达队首时提前启动 HAL。

### 启动顺序经过 UI 协调

启动顺序要经过 UI 协调，并不是“指纹和人脸同时开始”那么直接：

```text
goToInitialState()
  → 所有 eligible sensors 执行 prepare
  → 等待所有 cookie 返回
  → 先启动非指纹传感器
  → 请求 SystemUI 显示 Prompt
  → SystemUI 入场动画完成
       ├─ onDialogAnimatedIn(startFingerprintNow = true)
       │    → 启动已准备的指纹
       └─ startFingerprintNow = false
            → 继续延后
            → SystemUI 稍后调用 onStartFingerprintNow()
```

源码注释说明了延后指纹的原因：避免指纹交互提示（affordance）在 BiometricPrompt UI 完成入场前出现。人脸可以先运行；指纹是否随入场动画结束启动，由 SystemUI 根据当前 UI 和模态策略决定。

重试时 UI 已存在，`AuthSession` 重新准备可重试传感器，cookie 就绪后直接恢复相应传感器，不再创建第二个对话框。

<!-- gracker-diagram: ch01-24-prepare-ui-start -->
![cookie 就绪与 UI 反馈共同决定传感器启动](../../assets/diagrams/ch01/ch01-24-prepare-ui-start.png)

图：初次会话先为所有可用传感器 prepare，等各自 scheduler 回报 cookie 就绪。非指纹可先启动，指纹则等待 SystemUI 的入场和启动许可；重试已有 UI 时使用恢复分支。

## 线程模型与 Binder 回调

状态机之外还有一层容易忽略的事实：这些状态转换和回调分别跑在不同线程上。回调最终落在哪个线程，决定了我们排查时该看哪条轨道、应用又该把工作放在哪里。

### framework 线程

| 位置 | Android 17 线程 | 主要工作 |
| --- | --- | --- |
| `AuthService` Binder 入口 | system_server Binder 线程 | 权限、AppOps、前台和参数检查 |
| `BiometricService` 会话逻辑 | `BiometricsCallbackHandler` | 串行处理 session、sensor 与 SystemUI 回调 |
| 指纹 provider/scheduler | `FingerprintHandler` | 创建 client、调度单传感器操作 |
| 人脸 provider/scheduler | `FaceHandler` | 创建 client、调度单传感器操作 |
| SystemUI `AuthController` | SystemUI 主线程为主 | 创建、更新和关闭认证 UI |
| App callback | 调用方传入的 `Executor` | `onAuthentication*()` |

`BiometricHandlerProvider` 为 `BiometricsCallbackHandler` 创建独立 `HandlerThread`，优先级为 `THREAD_PRIORITY_DISPLAY`；Face 和 Fingerprint handler 也是独立线程，优先级为 `THREAD_PRIORITY_DEFAULT`。

Sensor HAL 回调与 SystemUI 回调到达 Binder stub（接收端接口实现）后，`BiometricService` 都会再次 `post()` 到 callback handler。这样，`mAuthSession` 的状态转换集中在一个串行执行上下文中，避免多个 Binder 线程直接并发修改。

### 应用回调线程

`BiometricPrompt` 的 receiver 会执行：

```java
mExecutor.execute(() -> {
    mAuthenticationCallback.onAuthenticationSucceeded(result);
});
```

`onAuthenticationFailed()`、`onAuthenticationError()` 和帮助信息也遵守同一 Executor。使用 `Context.getMainExecutor()` 时，回调中的数据库、网络、复杂解密或页面初始化都会占用应用主线程；改用后台 Executor 时，涉及 View 的操作必须切回主线程。

## `BiometricScheduler`：每个传感器串行调度操作

### scheduler 怎样排队

每个 AIDL sensor 持有一个 `BiometricScheduler`，包含：

- 一个保存待执行任务的 `Deque<BiometricSchedulerOperation> mPendingOperations`；
- 一个 `mCurrentOperation`；
- 当前用户查询器 `mCurrentUserRetriever` 和用户切换接口 `mUserSwitchProvider`；
- 最近的 operation 记录和统计信息。

HAL session 由各模态的 AIDL `Sensor.mCurrentSession` 持有。scheduler 通过查询器取得当前 session 对应的用户；队首任务属于其他用户时，再调度 stop-user/start-user client 完成切换。

队首 operation 分两类：

- cookie 为 `0`：scheduler 可以直接 `start()`；
- cookie 非 `0`：先回报 BiometricService，等待 `startPreparedClient(cookie)`。

新 client 声明 `interruptsPrecedingClients()` 时，scheduler 会：

1. 把可取消的 pending operation（待执行任务）标为 canceling；
2. 当前 operation 已开始且可中断时，请求取消；
3. 等当前 operation 的完成 callback 执行后，再启动队列中的下一项。

所以“录入一定比认证优先”“认证一定能抢占录入”这类说法都靠不住。是否中断，取决于具体 client 的属性、当前 operation 是否已经开始以及它是否可取消。

<!-- gracker-diagram: ch01-24-sensor-scheduler -->
![单传感器队列先完成当前任务，再推进下一项](../../assets/diagrams/ch01/ch01-24-sensor-scheduler.png)

图：每个 sensor 的 scheduler 保持一个当前任务和待执行队列。可执行的队首任务若 cookie 为零可直接启动，非零则回报就绪并等待仲裁层许可；中断请求也必须按条件取消并等当前任务终止。

### Fingerprint 与 Face HAL 的终止条件不同

Fingerprint AIDL 把方法分为 non-interrupting operation（同一 session 中排他执行的主要操作）和 interrupting operation（可在主要操作期间调用的交互方法）。一个 session 同时只能执行一个 non-interrupting operation；`authenticate()`、`enroll()`、`detectInteraction()` 属于可取消的 non-interrupting operation。取消后，HAL 必须用 `Error::CANCELED` 结束该 operation。这里的 interrupting 是 HAL 接口分类，不表示 scheduler 会抢占前一个 client。

Face AIDL 没有这组 interrupting operation 分类，接口约束是一个 session 同时只能执行一个 operation。Face 的 `onAuthenticationFailed()` 是终止回调；Fingerprint 的同名拒绝匹配回调不是终止回调，指纹 operation 可以继续等待下一次触摸。framework 的 scheduler 会等当前 operation 的终止回调完成，再启动下一个排队操作。

指纹 AIDL 的主要方法是：

```aidl
ICancellationSignal authenticate(long operationId);
ICancellationSignal enroll(HardwareAuthToken hat);
ICancellationSignal detectInteraction();
void enumerateEnrollments();
void removeEnrollments(int[] enrollmentIds);
void generateChallenge();
void revokeChallenge(long challenge);
void resetLockout(HardwareAuthToken hat);
void close();
```

UDFPS（Under-Display Fingerprint Sensor，屏下指纹传感器）的 `onPointerDown*()`、`onPointerUp*()`、`onUiReady()` 等属于可在采集 operation 运行时调用的交互方法，跟第二个 authenticate operation 是两回事。

Face AIDL 也使用 `authenticate()` 和 `detectInteraction()`，没有 `detectInteractive()`。Android 17 还提供带 `OperationContext` 的变体，HAL 可以利用显示、AOD（Always-On Display，息屏显示）等上下文优化执行，也可以忽略额外上下文并按基础方法处理。

### 超时来自哪里

`AuthSession` 里没有“所有认证 30～60 秒强制结束”的统一常量。真实的超时各有来源：

- HAL 对当前采集返回 `BIOMETRIC_ERROR_TIMEOUT`；
- sensor client 的具体实现；
- SystemUI 的交互状态；
- scheduler watchdog 的显式调用；
- OEM HAL 或安全环境。

`BiometricScheduler.startWatchdog()` 中有 10 秒清理定时器，Fingerprint/Face service 也暴露了受 `USE_BIOMETRIC_INTERNAL` 保护的 `scheduleWatchdog()` 内部入口，provider 会把它转为对应 scheduler 的 `startWatchdog()`。但它是显式调用的清理机制，BiometricPrompt 每次 `authenticate()` 并未自动启用它；说成所有认证 10 秒或 30～60 秒强制结束，就与源码对不上了。

排查超时时，我们记录实际 error、modality（指纹、人脸等认证模态）、`vendorCode` 和当前 operation，以实际值为准，套固定秒数只会误导。

## 指纹、UDFPS 与人脸的性能边界

### 指纹路径

我们先把指纹的调用链摆出来，用它区分 provider 排队、client 启动和 HAL operation：

```text
FingerprintService.prepareForAuthentication()
  → FingerprintProvider.scheduleAuthenticate()
  → FingerprintAuthenticationClient
  → per-sensor BiometricScheduler
  → AIDLSession.authenticate[WithContext](operationId)
  → ISessionCallback
```

provider 在自己的 handler 上构造 client。client 启动 HAL operation 后保存 `ICancellationSignal`；取消时调用它的 `cancel()`，并等待 HAL 的最终回调完成生命周期。

下面这些时间各有归属，合成一个“指纹算法耗时”会掩盖问题：

- operation 在 scheduler 队列中的等待；
- 当前用户 AIDL session 的启动或重建；
- Prompt 入场完成前的指纹延后；
- UDFPS overlay（屏幕上的指纹交互层）、触摸命中、显示模式与刷新率协调；
- HAL 采集和 secure matcher（安全环境中的匹配器）；
- 成功动画、对话框关闭与 App Executor 调度。

### UDFPS 是 UI、显示和 HAL 的协作

SystemUI 的 `AuthController` 根据 sensor properties（传感器属性）创建 `UdfpsController`，维护 sensor bounds（传感器在屏幕上的区域）和 display scale（显示缩放比例），并向 framework 注册 UDFPS overlay controller。指纹 authentication client 收到 `PointerContext` 后调用 HAL 的 `onPointerDownWithContext()` 或兼容方法。

一次 UDFPS 卡顿可能发生在：

1. Prompt 尚未完成入场；
2. overlay 尚未就绪；
3. 触摸未命中 sensor bounds；
4. 显示模式或高刷新率请求尚未完成；
5. HAL 尚未回报 acquired（样本采集状态）；
6. 采集质量不足，多次 acquired 后才匹配；
7. 匹配完成，但成功 UI 仍在收尾。

UDFPS 延迟高度依赖面板、传感器、贴膜、亮度策略与 vendor HAL。手里没有硬件和 trace，跨设备通用的毫秒区间就站不住脚，引用它只会误导排查。

### 人脸路径

人脸采用相同的 provider/scheduler 分层，但 HAL 回调和失败终止语义与指纹不同：

```text
FaceService.prepareForAuthentication()
  → FaceProvider.scheduleAuthenticate()
  → FaceAuthenticationClient
  → per-sensor BiometricScheduler
  → AIDLSession.authenticate[WithContext](operationId)
  → authentication frame / acquired / success / failure / error
```

人脸 client 可以接收 `FaceAuthenticationFrame`，把 acquired 信息和帮助文案交给 UI。一次拒绝匹配（reject）会结束当前 face authentication client；在 BiometricPrompt 中，`AuthSession` 可进入暂停状态，由用户点击重试后重新 prepare。

是否需要显式确认由三项共同决定：

- 该 sensor 是否支持确认；
- 用户设置是否要求该模态总是确认；
- `PromptInfo` 是否请求确认。

确认策略与“二维/三维”或“Class 2/Class 3”没有固定一一映射。

### 多模态会话的协调

人脸和指纹都符合本次请求条件（eligible）时，`AuthSession` 可以准备多个 sensor。通用 framework 代码在这里的工作是协调各 sensor 的启动、UI、成功、失败和取消，厂商级特征融合不在其中：

- 非指纹 sensor 在所有 cookie 返回后先启动；
- 指纹等待 UI 信号；
- 任一 sensor 成功后，session 记录 `mAuthenticatedSensorId`；
- 无需确认时取消其他 sensor；
- 需要确认时，源码会为特定侧边指纹场景保留传感器，其余 sensor 取消；
- 后到的成功或错误回调会按当前 session/requestId 状态过滤。

因此，把双模态设备的总延迟写成 `max(face, fingerprint)` 会过于简化：两个模态的启动时刻不同，失败后的 UI 策略也不同。

## 安全边界：模板、HAT 与 Keystore

### 原始模板与 framework 的隔离

Android 对 Class 2 和 Class 3 生物识别要求采集、录入和识别位于安全隔离环境中。原始生物数据和模板不得暴露给 Android framework，持久化数据需要设备专属密钥保护。

framework 能看到的只有：

- sensor metadata；
- acquired、success、failure、error 等事件；
- enrollment ID 等受限标识；
- Strong 认证成功时返回的 HardwareAuthToken；
- 用于会话协调的 requestId、cookie ID。

具体使用 TEE、Secure Element（安全元件）、StrongBox 或其他受支持安全硬件，由设备实现决定。StrongBox 主要是隔离的 KeyMint 实现和安全存储能力，它可能保存某些用户相关数据；拿它统称所有 biometric matcher 的所在位置，就与它的实际职责不符了。

### `HardwareAuthToken` 的字段

`android.hardware.keymaster.HardwareAuthToken` 包含：

```text
challenge
userId             // secure user ID，不是 Android userId/UID
authenticatorId    // 当前录入集合对应的 secure authenticator ID
authenticatorType
timestamp
mac                // HMAC-SHA256
```

HAT 有两类用途：

- 录入或解除锁定（enrollment/reset lockout）：HAL 验证由设备凭据等安全认证产生的 HAT；
- Strong 生物识别成功：HAL 用传入的 `operationId` 填入 challenge，生成 HAT，授权对应的 auth-per-use key operation（每次使用都要求认证的密钥操作）。

只有 Strong sensor 可以在成功回调中返回可供 Keystore 使用的 HAT。非 Strong sensor 即使回传 token，`AuthSession.onAuthenticationSucceeded()` 也会把它丢弃。

### 成功回调为何晚于 HAL success

Strong sensor 成功后，`AuthSession` 暂存 token，并通知 SystemUI 播放成功或确认 UI。SystemUI dismiss 后：

1. `AuthSession.onDialogDismissed()` 把生物识别 HAT 或设备凭据 attestation（凭据验证证明）交给 `KeyStoreAuthorization.addAuthToken()`；
2. 再调用应用侧 `onAuthenticationSucceeded()`；
3. 清理其他 sensor 和当前 session。

App 观察到的 success 时间包含 UI 收尾和 token 注入阶段。HAL 匹配成功时，App callback 未必已经执行。

Gatekeeper 负责 PIN、图案和密码等设备凭据验证；设备的安全生物识别组件负责匹配；Keystore2/KeyMint 消费合适的 AuthToken。StrongBox 是隔离的 KeyMint 实现，从它身上推不出 biometric matcher 的运行位置，我们要按设备实现单独确认。各组件共享安全认证协议，但职责不同。

<!-- gracker-diagram: ch01-24-success-token-callback -->
![HAL 匹配成功到应用成功回调还有收尾阶段](../../assets/diagrams/ch01/ch01-24-success-token-callback.png)

图：Strong 生物识别成功后，AuthSession 暂存 HAT 并通知 UI；必要确认或成功动画结束后收到 dismiss，再向 Keystore 提交令牌并发送应用回调。应用 Executor 的等待只是最后一部分，success 也不能代替后续密钥操作本身的错误检查。

## 失败、取消与锁定

### failure、error 与 cancel 的语义

| 结果 | 含义 | 会话行为 |
| --- | --- | --- |
| `onAuthenticationFailed()` | 采集有效但未匹配 | App 收到 failed；Face operation 结束并进入可重试暂停，Fingerprint operation 通常继续等待 |
| `BIOMETRIC_ERROR_TIMEOUT` | 当前 sensor operation 超时 | SystemUI 以软错误处理，session 可停在可重试状态 |
| hard error（不可恢复错误） | HAL 不可用、不可恢复错误等 | 暂存错误，等待 UI 展示后结束 |
| App cancel | 调用方取消当前 requestId | sensor 进入 `CANCELING`，等待取消完成或强制收尾 |
| client death（客户端死亡） | App Binder 死亡 | 取消运行中 sensor，关闭 UI |
| lockout（认证锁定） | HAL/sensor tracker 报告限流状态 | 允许回退到设备凭据时转到 credential UI，否则结束 |

`CancellationSignal.cancel()` 发出取消请求，不保证所有层在同一时刻停止。旧 HAL 回调仍可能到达，因此每次回调都先用 requestId、cookie 和当前 session 过滤。

### 锁定由 sensor 侧报告并协调

`PreAuthInfo` 调用每个认证器的 `getLockoutModeForUser()`。AIDL HAL 可通过：

- `onLockoutTimed(durationMillis)`；
- `onLockoutPermanent()`；
- `onLockoutCleared()`

报告状态。framework 的 `AuthSessionCoordinator` 和 `MultiBiometricLockoutState` 在不同认证强度、sensor 与用户之间协调结果。

“失败 5 次锁 30 秒”只适合当作个别设备的例子，写成所有设备的 framework 实现就错了。精确要求来自当前 Android CDD，执行细节还受 sensor strength、HAL 与设备策略影响。诊断时我们以实际 error、duration、sensorId 和设备 CDD 版本为准。

## SystemUI 与 App 的可见完成时间

### `AuthController` 的职责

`BiometricService` 通过 `IStatusBarService.showAuthenticationDialog()` 把 `PromptInfo`、sensor IDs、credential 许可、确认策略、operationId 和 requestId 传给 SystemUI。

`AuthController` 在 SystemUI 中：

- 创建并持有 `AuthContainerView`；
- 根据 sensor properties 管理指纹、人脸、UDFPS 和凭据 UI；
- 检查发起认证的 App 是否退到后台；
- 把入场完成、立即启动指纹、重试、切换凭据和 dismiss（关闭对话框）事件回传给 `AuthSession`；
- 把 acquired、success 和 error 映射为用户可见状态。

biometric HAL 不在它的调用范围里。`UdfpsController` 管理 overlay 和触摸交互，我们要跟踪的 authenticate operation 仍由 fingerprint provider/client 驱动。

### 三种“完成”时间点

| 时间点 | 说明 |
| --- | --- |
| HAL success | secure matcher 已接受样本 |
| SystemUI success | Prompt 已进入成功或确认状态 |
| App callback | token 已处理，SystemUI 已按原因 dismiss，回调已进入应用 Executor |

用户可能在成功动画开始时就认为认证完成，业务代码则要等 App callback。性能指标必须写明采用哪个结束点。

## 性能定位：先分段，再解释

### 建议记录的时间点

人脸可在 Prompt 入场前启动，指纹通常等待 SystemUI 信号，两种模态各有各的时间轴。我们把 App、会话、UI 和每个 sensor 分开记录：

| 标记 | 事件 | 可观测位置 |
| --- | --- | --- |
| `A_request` | App 调用 `authenticate()` 前 | App 埋点 |
| `B_enter` | `AuthService.authenticate()` 接收 | `system_server` 日志或定制 trace |
| `B_session` | `PreAuthInfo` 完成并创建 `AuthSession` | `BiometricService` |
| `U_show` | SystemUI 开始显示 Prompt | `AuthController.showAuthenticationDialog()` |
| `U_animated` | Prompt 入场动画完成 | `onDialogAnimatedIn()` |
| `S_prepare[id]` | 向指定 sensor 提交 prepare | `prepareForAuthentication()` |
| `S_ready[id]` | 指定 sensor 的 cookie 就绪 | `onReadyForAuthentication()` |
| `S_start[id]` | 对指定 sensor 调用 HAL authenticate | sensor client |
| `S_acquired[id]` | 指定 sensor 的首个 acquired/frame | sensor client callback |
| `S_reject[id]` | 指定 sensor 报告未匹配；Fingerprint 可出现多次 | sensor client callback |
| `S_end[id]` | operation 终止：success/error，Face 还包括 failure | sensor client callback |
| `U_dismiss` | SystemUI dismiss 完成回调 | `onDialogDismissed()` |
| `A_callback` | App callback 开始执行 | 调用方 Executor |

跨进程计算必须使用同一单调时钟，例如 Perfetto 的 trace clock（跟踪时钟）；各进程自己记录的 wall clock（日期时间）时间戳直接相减，得不出有效的耗时。

公开 `authenticate()` 也不会把内部 requestId 返回给 App，因此 App 与 `system_server` 的事件关联要靠受控的单请求测试或自有系统埋点；并发场景下拿“时间上最近的一条 biometric 日志”顶替关联 ID，并不可靠。

这些标记允许在同一份 trace 中分别计算：

```text
应用到 Binder 入口耗时   = B_enter - A_request
预认证与会话创建耗时     = B_session - B_enter
sensor 排队与准备耗时   = S_ready[id] - S_prepare[id]
sensor 启动协调耗时     = S_start[id] - S_ready[id]
首个样本等待            = S_acquired[id] - S_start[id]
当前 operation 耗时            = S_end[id] - S_start[id]
Prompt 入场耗时          = U_animated - U_show
HAL 成功后的 UI 收尾      = U_dismiss - 成功 sensor 的 S_end[id]
token 提交与回调交付阶段  = A_callback - U_dismiss
```

`S_start[id]` 需要从 framework client 或 vendor trace 取得。对 Face，`S_start[id]` 可以早于 `U_show`；对 Fingerprint，`S_start[id]` 往往不早于 `U_animated`。手里只有 App 的 `A_request/A_callback` 时，我们得到的是端到端耗时；要把责任落到安全环境还是传感器，还差 sensor 侧的分段。`U_dismiss` 若记录在 `AuthSession.onDialogDismissed()` 入口，其后仍包含 `addAuthToken()`、回调 Binder 交付和 App Executor 等待，只把 `A_callback - U_dismiss` 读成应用线程调度延迟会丢掉这几段；要拆分，就增加 token 提交后与应用 Binder stub 收到回调时的标记。

### 系统自带诊断入口

以下命令用于查看当前 session、已注册 sensor、provider 和 scheduler 状态：

```bash
adb shell dumpsys biometric
adb shell dumpsys fingerprint
adb shell dumpsys face
```

`dumpsys biometric` 的文本输出包含 sensor 列表和 `CurrentSession`。Fingerprint/Face dump 可看到 provider、当前 client、pending queue（待执行队列）和最近 operation。量产设备可能限制部分 dump 内容，userdebug/eng 构建更适合深入分析。

以下命令用于抓取 framework 与 SystemUI 事件：

```bash
adb logcat -v threadtime \
  -s BiometricService AuthService AuthController \
     FingerprintService FaceService BiometricScheduler
```

tag 和详细日志受构建类型、日志级别及 OEM 修改影响。采集前应在目标构建上确认实际 tag。

Perfetto 建议至少覆盖：

- `sched`、线程唤醒与 CPU frequency；
- Binder driver；
- `system_server` 与 SystemUI；
- gfx/view/window 相关轨道；
- 相机与 vendor biometric/TEE 自定义 data source（跟踪数据源）。

`BiometricService`、`AuthSession` 和 `AuthController` 的主路径上，没有稳定的专用 `Trace.traceBegin()` slice 可以当作跨设备的统一依据。厂商 trace 名称并不是 AOSP 给出的保证；需要统一标记时，我们在自有系统构建中给 App、UI 和 sensor 的分界加成对 trace。

### 症状到证据的映射

| 症状 | 先看什么 | 常见原因 |
| --- | --- | --- |
| 点击后迟迟不弹窗 | `A_request`～`U_show`、前台状态/AppOps、PreAuthInfo | 主线程阻塞、策略检查失败、旧会话取消、SystemUI 忙 |
| 弹窗出现后指纹才慢慢亮 | `S_ready`～`S_start`、`U_show`～`U_animated`、UDFPS overlay/显示模式 | UI 协调或显示准备，不一定是 matcher |
| 有提示但迟迟不成功 | acquired/reject 序列、`S_start`～`S_end` | 样本质量、环境、HAL 或 secure matcher |
| 已显示成功，业务页面仍未继续 | 成功 sensor 的 `S_end`～`A_callback` | 成功动画、HAT 注入、App Executor 排队 |
| 第二次认证特别慢 | 旧 requestId、cancel 完成、scheduler 当前任务 | 快速重启导致清理与新请求竞争 |
| 偶发立即转 PIN | lockout error、credentialAllowed | 限时/永久锁定或传感器策略 |
| 人脸不可用但指纹正常 | 相机隐私开关、eligibleSensors | 相机隐私、相机占用、模态单独禁用 |

## App 侧写法

节选中的认证请求绑定到当前 Activity 实例：销毁实例时先清除本地请求标记，再取消认证；三个回调都检查自己是否仍属于当前请求，避免取消后迟到的事件继续操作旧页面。示例使用 framework `android.hardware.biometrics.BiometricPrompt`，宿主应用需声明 `USE_BIOMETRIC` 权限；登录和错误展示函数由应用实现。

```kotlin
class LoginActivity : ComponentActivity() {
    private var cancellationSignal: CancellationSignal? = null

    fun requestBiometricLogin() {
        if (isDestroyed || cancellationSignal != null) return

        val signal = CancellationSignal()
        cancellationSignal = signal

        val prompt = BiometricPrompt.Builder(this)
            .setTitle("确认身份")
            .setAllowedAuthenticators(
                BiometricManager.Authenticators.BIOMETRIC_STRONG or
                    BiometricManager.Authenticators.DEVICE_CREDENTIAL
            )
            .build()

        prompt.authenticate(
            signal,
            mainExecutor,
            object : BiometricPrompt.AuthenticationCallback() {
                override fun onAuthenticationSucceeded(
                    result: BiometricPrompt.AuthenticationResult
                ) {
                    if (cancellationSignal !== signal) return
                    cancellationSignal = null
                    continueLogin()
                }

                override fun onAuthenticationError(
                    errorCode: Int,
                    errString: CharSequence
                ) {
                    if (cancellationSignal !== signal) return
                    cancellationSignal = null
                    renderAuthenticationError(errorCode, errString)
                }

                override fun onAuthenticationFailed() {
                    if (cancellationSignal !== signal) return
                    showTryAgainHint()
                }
            }
        )
    }

    override fun onDestroy() {
        val signal = cancellationSignal
        cancellationSignal = null
        signal?.cancel()
        super.onDestroy()
    }
}
```

示例用 `mainExecutor`，请求标记也只在主线程读写，所以三个回调都应保持短小。若成功后要读数据库、访问网络或执行较重的密码学业务，应把任务交给后台执行器，再把 UI 结果送回主线程。

这段代码在配置重建时也会取消认证，没有实现跨实例保留。需要旋转屏幕后继续认证时，应让独立于 Activity 实例的会话持有者保存请求状态，并把结果交给当前页面。仅在 `onDestroy()` 中跳过取消，会留下旧实例中的 signal 和 callback，新实例不会自动接管它们。API 文档关于避免快速取消重启的提醒仍然适用。

还要注意：

- `onAuthenticationFailed()` 通常不是终止回调，不要在这里立即创建新的 Prompt；
- 正常终止时由 success 或 error 清理本地进行中状态，销毁时则先使本地请求失效再取消；
- 若改用后台 Executor，需同步保护请求状态，涉及 View 的操作仍需切回主线程；
- `CryptoObject` 使用的认证器要和密钥生成时的授权配置一致。

## 版本边界

| 版本 | 相关变化 |
| --- | --- |
| Android 9 / API 28 | 引入 framework `BiometricPrompt` |
| Android 11 / API 30 | 公开 `BiometricManager.Authenticators`，可组合 biometric 与 device credential |
| Android 12 / API 31 | AOSP 文档明确纳入 UDFPS 支持；适用范围从该版本开始 |
| Android 13 起 | 新设备实现逐步迁移到稳定 AIDL biometric HAL |
| Android 17 / API 37 | 当前源码锚点；包含 Identity Check 资格处理、受限 sensor strength 查询和现代 AIDL session context（会话上下文）能力 |

Android 17 仍保留旧设备 HAL 兼容适配。版本号说明的是 framework 能力上限；落到一台具体设备，还是要核查它的 provider、HAL interface version、sensor properties 和 vendor 实现。

## 源码核查索引

| 问题 | Android 17 源码 |
| --- | --- |
| App 为何先进入 AuthService | `BiometricPrompt.java`、`IAuthService.aidl`、`AuthService.java` |
| 谁计算 eligible sensor | `PreAuthInfo.java` |
| 谁保存当前 Prompt 会话 | `BiometricService.java` 的 `mAuthSession` |
| session 与 sensor 状态是什么 | `AuthSession.java`、`BiometricSensor.java` |
| callback 在哪个线程运行 | `BiometricHandlerProvider.java`、`BiometricPrompt.java` |
| operation 为何串行 | `BiometricScheduler.java`、AIDL `ISession.aidl` |
| AIDL session 是否复用 | Fingerprint/Face `aidl/Sensor.java` 与 `*StartUserClient.java` |
| UDFPS 如何传 pointer | `FingerprintAuthenticationClient.java`、`UdfpsController.java` |
| HAT 何时交给 Keystore | `AuthSession.onDialogDismissed()` |
| SystemUI 如何参与 | `AuthController.java`、`AuthContainerView.java` |

官方资料：

- [AOSP Biometrics](https://source.android.com/docs/security/features/biometric)
- [AOSP Authentication](https://source.android.com/docs/security/features/authentication)
- [BiometricPrompt API](https://developer.android.com/reference/android/hardware/biometrics/BiometricPrompt)
- [BiometricManager API](https://developer.android.com/reference/android/hardware/biometrics/BiometricManager)

## 与关联章节的分工

| 章节 | 分工 |
| --- | --- |
| §1.10 Binder 线程池与优先级继承 | Binder 调度和优先级传播 |
| §8.5 Keystore/KeyMint | 密钥授权、CryptoObject、KeyMint 与 StrongBox |
| §8.5 BiometricPrompt 登录性能 | 登录业务的端到端指标和线上观测 |
| §20.10 Keystore 治理 | 密钥生命周期、失效与异常治理 |

## 小结

整条 BiometricPrompt 路径可以归纳为四个控制点：

1. `AuthService` 处理公开入口的访问控制；
2. `BiometricService` 用 `PreAuthInfo` 和单个 `AuthSession` 仲裁请求；
3. 每个 sensor 的 provider 与 `BiometricScheduler` 串行驱动 HAL operation；
4. SystemUI 控制用户可见流程，安全环境完成受保护的采集、匹配与 HAT 生成。

一次慢认证可能卡在旧会话取消、预认证、scheduler、AIDL session 冷启动、Prompt 动画、UDFPS 显示协作、首个样本、secure matcher、HAT 注入或 App Executor 中的任何一段。我们把 App、UI 和各 sensor 的分段标记采齐，再对照当前 requestId、sensorId、operation 和 error，问题就能归到负责的组件。
