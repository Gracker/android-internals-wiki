---
title: Android Developer Verification 与安装链路边界
chapter: '1.21'
section: '1.21'
status: finalized
applicable_versions: "Policy: certified Android 7+ devices; platform API: Android 16.1 (API 36.1) - Android 17 (API 37)"
last_verified: '2026-07-25'
last_verified_against: AOSP android-17.0.0_r1 + Android 17 API 37 + Android Developer Verification policy as of 2026-07-25
policy_snapshot: '2026-07-25'
confidence: high
sources:
  - type: official
    path: "https://developer.android.com/developer-verification/guides"
  - type: official
    path: "https://developer.android.com/developer-verification/guides/faq"
  - type: official
    path: "https://developer.android.com/developer-verification/guides/limited-distribution"
  - type: official
    path: "https://developer.android.com/reference/android/content/pm/PackageInstaller"
  - type: official
    path: "https://developer.android.com/reference/android/os/Build.VERSION"
  - type: official
    path: "https://developer.android.com/reference/android/os/Build.VERSION_CODES_FULL"
  - type: official
    path: "https://developer.android.com/blog/posts/android-developer-verification-rolling-out-to-all-developers-on-play-console-and-android-developer-console"
  - type: aosp
    path: "frameworks/base/core/java/android/content/pm/PackageInstaller.java @ android-17.0.0_r1"
  - type: aosp
    path: "frameworks/base/core/java/android/content/pm/verify/developer/DeveloperVerifierService.java @ android-17.0.0_r1"
  - type: aosp
    path: "frameworks/base/core/java/android/content/pm/verify/developer/DeveloperVerificationSession.java @ android-17.0.0_r1"
  - type: aosp
    path: "frameworks/base/core/java/android/content/pm/verify/developer/DeveloperVerificationStatus.java @ android-17.0.0_r1"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/pm/PackageInstallerService.java @ android-17.0.0_r1"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/pm/PackageInstallerSession.java @ android-17.0.0_r1"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/pm/verify/developer/DeveloperVerifierController.java @ android-17.0.0_r1"
tags:
  - android
  - package-manager
  - package-installer
  - developer-verification
  - app-signing
  - security
related_chapters:
  - '1.4'
  - '1.9'
  - '16.5'
  - '26.7'
pipeline_stage: ready-to-publish
task6_state: reviewed
task9_state: "reviewed"
task2b_state: "fixed"
---

# 1.21 Android Developer Verification 与安装链路边界

Android Developer Verification（Android 开发者验证，后文简称“开发者验证”）回答的是：

> 准备安装这个包的开发者身份、包名和签名密钥，是否满足当前设备上的开发者验证策略？

它不判断 APK 是否损坏、升级签名是否匹配、安装器是否有权限、用户是否同意，也不负责 dexopt。把这些问题混成一项“安装校验”，会直接导致错误归因。

以下分析采用三组基线：

- 平台源码：AOSP `android-17.0.0_r1`。
- 平台接口：Android 17 / API 37；相关公开接口最早标记为 Android 16.1 / API 36.1。
- 产品政策：Android Developer Verification 官方文档在 2026-07-25 的公开口径。

政策会继续变化，源码标签不会。工程实现应把两者分开管理。

## 1. 先分清三个坐标系

| 层次 | 解决的问题 | 载体 | 版本边界 |
|---|---|---|---|
| Google 的开发者验证政策 | 哪些设备、区域、渠道和用户路径需要验证 | Android Developer Verifier、Google Play services、开发者管理中心 | 官方称覆盖 Android 7 及以上、经 Google 认证的 Android 设备；分阶段启用 |
| Android 平台机制 | 安装会话如何请求验证、等待结果、触发用户动作并回传错误 | `PackageInstallerSession`、`DeveloperVerifierController`、`PackageInstaller` API | 以 `android-17.0.0_r1` 为源码基准；公开结果 API 自 36.1 提供 |
| APK 与安装信任链 | APK 是否可解析、签名是否有效、升级证书是否兼容、权限与设备策略是否允许 | APK Signature Scheme、PMS、PackageInstaller、DPM、旧版包验证服务 | 由各自的平台版本和策略决定 |

Android 17 AOSP 提供开发者验证服务的接入框架，却没有把 Google 的身份数据库和判定逻辑开源在 `frameworks/base` 中。下文用 verifier 指代设备指定的这项验证服务。在 Google 认证设备上，官方把 Android Developer Verifier 描述为一项新的 Google 系统服务，并说明 Android 7 及以上设备通过 Google Play services 接收相关更新。

AOSP 中存在这些类，并不表示任意 AOSP 构建都会自动执行 Google 的政策。Android 17 的 `PackageInstallerService` 默认策略是 `DEVELOPER_VERIFICATION_POLICY_NONE`；设备没有配置 verifier，或功能开关没有启用时，安装会话会跳过这一步。

`android.content.pm.verify.developer` 下的 `DeveloperVerifierService`、`DeveloperVerificationSession` 和 `DeveloperVerificationStatus` 都标有 `@SystemApi` 与 `@hide`。它们定义平台与受信任 verifier 之间的协议，普通应用无法通过公开 SDK 直接实现或调用。普通安装器只能使用 `PackageInstaller` 公开的结果附加字段、失败原因码和扩展接口。

## 2. 截至 2026-07-25，政策执行到哪里

### 2.1 2026 年 9 月只在首批渠道执行

从 2026-09-30 起，巴西、印度尼西亚、新加坡和泰国经 Google 认证的 Android 设备开始执行首批验证，但当前公布的范围只覆盖下列参与商店发起的安装：

- Google Play
- HONOR App Market
- OPPO App Market
- Samsung Galaxy Store
- Transsion Palm Store
- vivo V-Appstore
- Xiaomi GetApps

FAQ 在 2026-07-15 明确补充：

- 用户直接旁加载 APK，2026 年 9 月暂不受这轮要求影响。
- 未列入上表的其他商店，2026 年 9 月也暂不受这轮要求影响。
- 2027 年开始，计划把保护扩展到全球经 Google 认证的 Android 设备上的所有应用。

所以，“2026-09-30 起四国所有非 Play 安装都会被拦截”是错误结论。更准确的模型是：

```text
长期目标
  └─ certified Android devices Android 设备上的广泛安装来源

2026-09-30 首批执行
  ├─ 四个国家
  ├─ mobile / tablet 为主要执行形态
  └─ 七个明确列出的参与商店

暂不属于 2026-09 首批执行
  ├─ 直接旁加载
  └─ 未参与首批计划的其他商店
```

“暂不”描述的是当前上线批次，不代表可以忽略 2027 年的全球扩展。

首批执行还要区分设备类型（form factor）：通过 Google Play 分发的应用需要登记支持的所有设备类型；Play 以外的 2026 年首批强制范围，目前只包括所选四国的手机（mobile）与平板（tablet）。不要把手机上的实验结果直接外推到 TV、Auto 或 Wear。

### 2.2 特殊分发路径

| 路径 | 当前官方边界 | 工程理解 |
|---|---|---|
| ADB | 工作流保持不变，可安装未注册应用 | 只证明开发调试路径可用，不能替代真实商店验收 |
| 高级流程（Advanced flow） | 2026 年 8 月面向熟悉相关风险的高级用户推出；完成一次设置后可安装未注册应用 | 用户明确接受风险的旁加载路径，不是商店静默绕过接口 |
| 有限分发（Limited distribution） | 免费、无需政府签发身份证件，最多分享给 20 台经最终用户明确授权的设备 | 适合学习、课堂、家庭和非商业小范围分享 |
| 受管设备与组织内商店 | 由 IT 管理员审核的组织内应用不要求完成验证 | 同一 APK 离开组织内商店或进入非受管设备后，不能继续假设享有豁免 |

高级流程不是安装器可自行打开的开关。官方常见问题说明的流程包含启用开发者模式、反诱导确认、重启与重新认证、等待 24 小时，以及再次使用生物识别或 PIN 确认。ADB 不受这段等待时间影响。

这些步骤属于 2026 年的政策快照，不应硬编码成应用的永久业务规则。

## 3. 开发者验证和 APK 签名是什么关系

注册流程建立的是：

```text
现实中的个人或组织
        ↕ 身份验证
开发者账号
        ↕ 注册包名
应用包名
        ↕ 由私钥签名的 APK 证明
签名密钥
```

它利用签名 APK 证明包名与密钥归属，但不替代设备本地的 APK 签名校验。

攻击者即使知道已注册应用的包名，只要没有合法私钥，仍会受到以下限制：

1. Developer Verification 不能让伪造 APK 获得合法签名。
2. APK Signature Scheme 校验仍会发现签名无效。
3. 若设备上已有正版应用，升级安装还要通过签名继承链（signing lineage）和证书兼容性检查。

一个 APK 的 v2/v3/v4 签名有效，只说明 APK 由对应密钥签发且内容未被篡改；它不能自动证明开发者已完成身份验证，也不能证明包名已登记到对应账号。

发版资产至少要同时维护包名、当前与历史签名证书、验证账号与状态，以及各渠道最终交付 APK 的证书指纹。渠道重签会同时破坏升级兼容性和包名登记证明。

## 4. Android 17 对普通安装器公开了什么

### 4.1 API 36.1 与 API 37

`PackageInstaller` 文档把 Developer Verification 的结果字段标为“Added in version 36.1”。Android 17 / API 37 继续提供这些接口，并把安装器的目标 SDK 版本（target SDK）是否大于 36 作为新的回调行为边界。

36.1 是 SDK 次版本，不能只检查 `Build.VERSION.SDK_INT >= 36`。需要区分次版本时，可以使用下面的判断：

```kotlin
val supportsDeveloperVerificationResult =
    Build.VERSION.SDK_INT >= 36 &&
        Build.VERSION.SDK_INT_FULL >= Build.VERSION_CODES_FULL.BAKLAVA_1
```

Android 17 的 `Build.VERSION_CODES_FULL.CINNAMON_BUN` 为 37.0，自然满足这个条件。代码仍需用包含相应符号的 SDK 编译。

### 4.2 失败原因

| 常量 | 值 | 含义 |
|---|---:|---|
| `DEVELOPER_VERIFICATION_FAILED_REASON_UNKNOWN` | 0 | verifier 超时、连接失败，或报告未知原因而无法完成验证 |
| `DEVELOPER_VERIFICATION_FAILED_REASON_NETWORK_UNAVAILABLE` | 1 | verifier 明确报告网络不可用 |
| `DEVELOPER_VERIFICATION_FAILED_REASON_DEVELOPER_BLOCKED` | 2 | verifier 已完成判断，但开发者未通过当前策略 |

`UNKNOWN` 不等于“没有提供原因”。读取前必须检查失败原因附加字段是否存在，不能只使用默认值 0。

### 4.3 结果附加字段

| 附加字段 | 类型 | 用途 |
|---|---|---|
| `EXTRA_DEVELOPER_VERIFICATION_FAILURE_REASON` | `int` | 安装最终因 Developer Verification 中止时解释原因 |
| `EXTRA_DEVELOPER_VERIFICATION_LITE_PERFORMED` | `boolean` | 在失败结果中标记 verifier 是否只执行了轻量验证（lite verification） |
| `EXTRA_DEVELOPER_VERIFICATION_EXTENSION_RESPONSE` | `PersistableBundle` | verifier 对安装器扩展参数的响应 |
| `Intent.EXTRA_INTENT` | `Intent` | 需要用户动作，或提供可延后展示的系统解释页 |

`SessionParams.setExtensionParams()` 与 `getDeveloperVerificationServiceProvider()` 允许安装器和 verifier 使用双方约定的扩展参数。`Bundle` 的字段结构由 verifier 实现决定，不是跨设备通用协议。安装器只有确认服务提供方后才能解释其中内容；遥测也不应默认原样上传未知的 `Bundle`。

## 5. 一次提交可能产生多次回调

`Session.commit(IntentSender)` 只是把已封存的安装会话交给系统异步处理。这个方法成功返回，不代表安装已经完成。

Developer Verification 失败时，`EXTRA_STATUS` 取决于安装器的目标 SDK 版本、权限，以及该失败是否允许用户处理：

| 安装器 | 首个回调 | 后续结果 |
|---|---|---|
| 目标 SDK ≤ 36，只有 `REQUEST_INSTALL_PACKAGES` | 先收到不带失败原因的 `STATUS_PENDING_USER_ACTION` | 用户允许绕过则继续；否则返回 `STATUS_FAILURE_ABORTED` 并携带原因 |
| 目标 SDK ≤ 36，持有特权 `INSTALL_PACKAGES` | 通常直接收到 `STATUS_FAILURE_ABORTED` 并携带原因 | 不依赖普通用户确认流程 |
| 目标 SDK ≥ 37，需要用户输入的非阻断问题 | 先收到不带失败原因的 `STATUS_PENDING_USER_ACTION` | 用户重试或允许后继续；否则最终返回 `STATUS_FAILURE_ABORTED` 并携带原因 |
| 目标 SDK ≥ 37，其余阻断结果 | `STATUS_FAILURE_ABORTED` 并携带原因 | 可能带 `Intent.EXTRA_INTENT`，供系统解释原因 |

系统默认的 Package Installer 是特例：AOSP 会优先让它展示相应的系统页面。

安装器应把 `STATUS_PENDING_USER_ACTION` 当成中间状态，按下面方式继续处理：

```kotlin
fun handleInstallResult(result: Intent) {
    when (result.getIntExtra(PackageInstaller.EXTRA_STATUS, Int.MIN_VALUE)) {
        PackageInstaller.STATUS_PENDING_USER_ACTION -> {
            val action = result.getParcelableExtra(
                Intent.EXTRA_INTENT,
                Intent::class.java,
            ) ?: return
            // 前台可立即拉起；后台应先发通知，让用户主动返回。
            startActivity(action.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK))
        }

        PackageInstaller.STATUS_SUCCESS -> {
            // 安装事务已经完成。
        }

        PackageInstaller.STATUS_FAILURE_ABORTED -> {
            val reason = if (result.hasExtra(
                    PackageInstaller.EXTRA_DEVELOPER_VERIFICATION_FAILURE_REASON,
                )
            ) {
                result.getIntExtra(
                    PackageInstaller.EXTRA_DEVELOPER_VERIFICATION_FAILURE_REASON,
                    PackageInstaller.DEVELOPER_VERIFICATION_FAILED_REASON_UNKNOWN,
                )
            } else {
                null
            }
            // reason == null 时，不能归因于 Developer Verification。
        }
    }
}
```

应用不在前台时直接启动待处理的系统 Intent，可能受到后台启动限制，也会显得突兀。公开 API 建议先发送通知，让用户回到安装器后再进入系统页面。

## 6. Android 17 的源码调用链

Android 17 把新机制直接接入 `PackageInstallerSession`，没有把 Google 的业务判定写进旧版包验证服务。

### 6.1 创建安装会话：保存初始策略并提前连接 verifier

`PackageInstallerService.createSessionInternal()` 从按用户保存的策略表读取默认值，分别作为安装会话的初始策略和当前策略。策略会写入安装会话 XML，因此进程重启不会改变已经创建的会话采用哪项初始策略。

满足以下条件时，构造 `PackageInstallerSession` 会提前绑定 verifier：

- 开发者验证功能已启用；
- 设备配置了 verifier 服务提供方；
- 当前会话不是多包安装的父会话；
- 当前会话不是系统重启后恢复出来的会话。

若 `SessionParams.appPackageName` 已提供包名，`DeveloperVerifierController` 还会调用 `onPackageNameAvailable()`，让 verifier 提前取得所需数据。此时验证尚未开始，这一步只是减少正式请求前的准备时间。

### 6.2 `commit()`：封存、流式校验，再进入安装消息

下面的调用序列用于定位 `commit()` 之后、Developer Verification 之前的安装会话状态转换：

```text
Session.commit(statusReceiver)
  → markAsSealed()
  → dispatchSessionSealed()
  → handleSessionSealed()
  → dispatchStreamValidateAndCommit()
  → handleStreamValidateAndCommit()
  → streamValidateAndCommit()
  → MSG_INSTALL
  → handleInstall()
```

`streamValidateAndCommit()` 会准备 `DataLoader`、验证 APK/APEX 安装会话的基本结构，并把会话标记为已提交。执行到这里仍未安装成功。

### 6.3 `handleInstall()`：解析 APK 后先做 Developer Verification

下面的序列标出 `performDeveloperVerification()` 在 `handleInstall()` 中相对 APK 解析的位置：

```text
handleInstall()
  ├─ sendPendingUserActionIntentIfNeeded()
  ├─ prepareInheritedFiles()
  ├─ parseApk()
  └─ performDeveloperVerification()
       └─ startDeveloperVerificationSession()
```

单包安装会话使用一个 `CompletableFuture`。多包安装不会验证父会话，而会分别验证每个子会话；任一子会话失败，整个多包安装都会失败。

### 6.4 `DeveloperVerifierController` 与 verifier 的交互

`startDeveloperVerificationSession()` 交给 `DeveloperVerifierController` 的信息包括：

- 包名；
- 暂存包的 URI；
- `SigningInfo`；
- 应用清单声明的共享库；
- 当前验证策略；
- 安装器扩展参数；
- ADB 或强制验证相关的内部标志。

控制器使用 `PackageManager.ACTION_VERIFY_DEVELOPER` 绑定设备指定的 `DeveloperVerifierService`，然后调用 `onVerificationRequired(session)`；用户请求重试时调用 `onVerificationRetry(session)`；超时后调用 `onVerificationTimeout(id)`。

verifier 通过 `DeveloperVerificationSession` 的以下方法回报结果：

```text
reportVerificationComplete(status)
reportVerificationIncomplete(reason)
reportVerificationBypassed(reason)
```

完整结果包含 `isVerified`、轻量验证状态、App Metadata（应用元数据）状态和可选的失败说明。未完成结果目前只区分原因未知与网络不可用。

### 6.5 结果怎样回到原安装链

下面的分支图说明 verifier 的结果如何完成 `CompletableFuture`，并决定继续原安装链还是结束安装会话：

```text
verifier callback
  ├─ verified / policy NONE / allowed bypass
  │    └─ future success
  │         └─ resumeVerify()
  │              ├─ extract native libraries
  │              ├─ PackageSessionVerifier
  │              └─ install
  │
  └─ rejected / incomplete / timeout / connection failure
       ├─ policy 是否要求阻断
       ├─ 是否允许用户重试或 install anyway
       └─ failure
            ├─ INSTALL_FAILED_VERIFICATION_FAILURE
            ├─ EXTRA_DEVELOPER_VERIFICATION_FAILURE_REASON
            └─ dispatchSessionFinished()
```

Developer Verification 位于 APK 解析完成之后、原有安装会话验证继续运行之前。通过这一关后，包仍可能因为签名、设备策略、存储、共享库、APK 格式或后续安装事务而失败。

## 7. 验证策略决定失败后的处理方式

Android 17 AOSP 定义了四种 System API 验证策略：

| 策略 | 开发者未通过 | 原因未知 / 连接失败 / 超时 | 网络不可用 |
|---|---|---|---|
| `NONE` | 不阻断 | 不阻断 | 不阻断 |
| `BLOCK_FAIL_OPEN` | 阻断 | 允许用户继续 | 允许重试或继续 |
| `BLOCK_FAIL_WARN` | 阻断 | 允许用户继续 | 允许重试或继续 |
| `BLOCK_FAIL_CLOSED` | 阻断 | 阻断 | 允许用户重试 |

`BLOCK_FAIL_OPEN` 与 `BLOCK_FAIL_WARN` 在 Android 17 源码注释中的安装结果描述相同；不要只凭名字推导额外语义。

每个用户的默认策略由 verifier 或系统指定的策略代理设置。verifier 还可通过安装会话的 `setPolicy()` 覆盖当前请求。业务代码不能只凭国家码模拟最终判定，必须以系统回调为准。

## 8. ADB 的绕过边界

官方面向开发者的承诺是 ADB 工作流不变。Android 17 源码分别描述了机制与结果：旧的非强制路径可以直接跳过验证；启用 `verificationServiceAdb` 后，ADB 安装请求也可送到 verifier，并通过 `FLAG_VERIFICATION_IS_ADB` 表明来源。verifier 可用 `DEVELOPER_VERIFICATION_BYPASSED_REASON_ADB` 明确报告这次验证因 ADB 来源而绕过。

若内部安装会话还设置了 `forceVerification`，平台会追加 `FLAG_VERIFICATION_FORCED_ON_ADB`；即便如此，源码注释仍要求只有阻断策略才能阻止安装。这些都属于命令行、测试或系统管理边界，不是普通第三方安装器 API，也不改变常规 ADB 用于开发测试的产品承诺。

- `adb install` 成功：证明 APK 和调试安装路径基本可用。
- 商店安装成功：证明该商店、设备、账号、区域和策略组合可用。
- 两者不能互相替代。

## 9. 安装耗时应如何分段统计

从取得安装包到收到最终回调，至少包含下面这些阶段，不能把总耗时全部记到 Developer Verification：

```text
包体获取
  + session 写入
  + seal / stream validation
  + 普通用户授权等待
  + Developer Verification
  + 原有 package verification
  + native library / 安装事务 / dexopt
  + 最终回调
```

这里的 `dexopt` 指 dex 字节码的编译与优化。`DeveloperVerifierController` 会在安装会话创建时尝试提前连接 verifier，正式验证请求则在 `handleInstall()` 解析 APK 后发送。因此，只看“创建安装会话到安装成功”的总时长，无法得出开发者验证本身的耗时。

Android 17 r1 控制器的默认参数是：

- 等待 verifier 连接：10 秒；
- 等待 verifier 响应请求：10 秒；
- verifier 可申请延长的总上限：10 分钟。

它们来自 `DeviceConfig.NAMESPACE_PACKAGE_MANAGER_SERVICE`，只是默认值，不构成兼容性保证或产品服务等级协议（SLA）。设备厂商、系统更新和实验配置都可能改变这些时间。

| 时间点 | 普通安装器是否可见 | 含义 |
|---|---|---|
| 安装会话创建、文件写入 | 可见 | 安装器自身 I/O |
| `commit()` | 可见 | 系统异步处理起点 |
| 首次 `STATUS_PENDING_USER_ACTION` | 可见 | 需要用户介入，不一定来自 Developer Verification |
| Developer Verification 失败原因 | 仅在失败且系统提供时可见 | 可确认验证层失败 |
| 最终成功或失败 | 可见 | 安装会话结束 |
| verifier 的绑定、请求和响应时刻 | 普通应用不可直接取得 | 需要系统级指标、系统轨迹或受控设备日志 |

普通安装器可以上报“`commit()` 到首个回调”和“`commit()` 到最终回调”，但不能把前者直接命名为“Developer Verification 耗时”。

## 10. 推荐的错误归因顺序

下面的决策顺序以公开状态和失败原因附加字段为依据，避免仅凭错误文本归因：

```text
收到安装回调
  ├─ STATUS_PENDING_USER_ACTION
  │    └─ 中间状态：保存 session 上下文并处理 Intent.EXTRA_INTENT
  ├─ STATUS_FAILURE_ABORTED
  │    ├─ 有 Developer Verification reason → 归入 developer verification
  │    └─ 无 reason → 检查用户取消、session abandon 等原因
  ├─ STATUS_FAILURE_BLOCKED
  │    └─ 检查 DPM、用户限制、旧 package verifier、关键包保护
  ├─ STATUS_FAILURE_INVALID / CONFLICT
  │    └─ 检查 APK、split、签名、版本与现有包
  └─ STATUS_SUCCESS
       └─ 安装完成；不等于应用首帧已经出现
```

其中，DPM 是设备策略管理器（Device Policy Manager）。`STATUS_FAILURE_BLOCKED` 的公开定义覆盖设备策略、旧版包验证服务和系统关键包保护等来源。只有 `STATUS_FAILURE_ABORTED` 同时携带 Developer Verification 失败原因时，才有充分证据把问题归入本机制。

`EXTRA_STATUS_MESSAGE` 是调试文本，可能随系统版本、语言和 OEM 改变。它适合保留样本，不适合作为监控聚合键。

## 11. Android 17 r1 的轻量验证附加字段类型不一致

公开契约规定 `EXTRA_DEVELOPER_VERIFICATION_LITE_PERFORMED` 是 `boolean`。但在 `android-17.0.0_r1` 中：

1. `setSessionFailedDueToDeveloperVerification()` 用 `Bundle.putBoolean()` 写入。
2. `sendOnPackageInstalled()` 复制到最终 Intent 时却调用 `extras.getInt()`。

这是 r1 源码中的类型不一致，不能把 `int` 当成新的公开协议。`Bundle.getInt()` 遇到原来的 `Boolean` 时还可能返回默认值 0，因此 `true` 信息可能在复制过程中已经丢失。下面的兼容性读取只能把类型差异限制在一处，不能恢复已丢失的真值：

```kotlin
fun readLitePerformedCompat(intent: Intent): Boolean? {
    if (!intent.hasExtra(
            PackageInstaller.EXTRA_DEVELOPER_VERIFICATION_LITE_PERFORMED,
        )
    ) {
        return null
    }

    return when (
        val value = intent.extras?.get(
            PackageInstaller.EXTRA_DEVELOPER_VERIFICATION_LITE_PERFORMED,
        )
    ) {
        is Boolean -> value          // 公开契约
        is Int -> value != 0         // 兼容错误类型；r1 的 true 可能已丢失
        else -> null
    }
}
```

兼容代码应限制在负责平台差异的适配层，并记录实际收到的类型，以便系统修复后删除这段分支；业务层仍统一使用 `Boolean?`。

## 12. 遥测字段与隐私边界

建议记录：

- 包名、`versionCode`、安装器包名与安装来源；
- 安装器的目标 SDK 版本、是否持有特权安装权限；
- `SDK_INT`、`SDK_INT_FULL`、安装会话是否为多包安装，以及是否为 staged（重启后应用）安装；
- `EXTRA_STATUS`、失败原因附加字段是否存在及其枚举值；
- 是否出现待用户操作、停留多久、最终继续还是取消；
- 设备是否受组织管理、是否通过 ADB 安装；
- 安装会话写入、`commit()` 到首个回调、`commit()` 到最终状态的耗时；
- 由服务端按版本维护的政策区域和渠道批次。

不建议默认记录未知的 verifier 扩展 `Bundle`、系统解释页文本、身份文件、账号凭据或签名私钥，也不要把自由格式的状态文本作为主聚合维度，因为它的可能取值很多且会随版本变化。

下面是一份只记录状态与时长、不收集身份材料的示例：

```json
{
  "package_name": "com.example.app",
  "version_code": 12345,
  "installer_package": "com.example.store",
  "installer_target_sdk": 37,
  "sdk_int": 37,
  "sdk_int_full": 3700000,
  "status": "STATUS_FAILURE_ABORTED",
  "developer_verification_reason_present": true,
  "developer_verification_reason": "NETWORK_UNAVAILABLE",
  "pending_user_action_seen": true,
  "managed_device": false,
  "adb_install": false,
  "distribution_cohort": "2026-09-participating-store",
  "duration_ms": {
    "session_write": 420,
    "commit_to_first_callback": 1800,
    "pending_user_action": 12000,
    "commit_to_terminal": 14800
  }
}
```

`distribution_cohort` 是业务侧标签，不是 Android API 字段。使用服务端标签比把地区规则写死在客户端更容易随政策更新。

## 13. 发版与渠道验收清单

### 开发者账号与签名

- 正式版、测试版（beta）、企业版和历史包名都已盘点。
- 包名已登记到正确账号。
- 注册证明 APK 与最终渠道 APK 的签名证书一致。
- Play App Signing、旧密钥、密钥轮换和非 Play 渠道的证书关系有记录。
- 渠道下载后的 APK 再次验签，防止重签或产物替换。

### 安装器

- 用 `SDK_INT_FULL` 处理 36.1 API 边界。
- 把 `STATUS_PENDING_USER_ACTION` 当成中间状态。
- 目标 SDK 37 已覆盖待用户操作、重试、仍然安装和直接中止四条路径。
- 只有失败原因附加字段存在时，才把失败归因到 Developer Verification。
- 只有确认 verifier 服务提供方和字段结构后，才使用扩展参数。
- 后台收到待用户操作状态时通过通知让用户返回，不直接拉起 Activity。

### 测试维度

| 维度 | 样本 |
|---|---|
| 平台 | Android 16.1、Android 17 |
| 设备 | 经 Google 认证的 Android 设备、无对应 verifier 的 AOSP 或企业设备 |
| 安装器目标 SDK | ≤ 36、37 |
| 权限 | `REQUEST_INSTALL_PACKAGES`、特权 `INSTALL_PACKAGES` |
| 结果 | 验证通过、开发者未通过、网络不可用、超时 |
| 用户路径 | 出现待用户操作后继续、重试或取消 |
| 分发 | 参与商店、非参与商店、直接旁加载、ADB、组织管理的商店 |
| 安装会话 | 单包、多包 |

区域和商店策略要在真实分发入口验证。VPN、修改系统语言或地区设置，以及实验室中的 ADB 安装成功，都不足以证明真实渠道路径可用。

## 14. 与其他安装机制的边界

| 机制 | 失败说明 | 是否由 Developer Verification 替代 |
|---|---|---|
| APK 解析与签名 | 文件损坏、签名无效、split APK 不一致、升级证书冲突 | 否 |
| 安装器权限与未知来源授权 | 调用者无权创建/提交安装，或用户未授权该来源 | 否 |
| 设备策略 / 用户限制 | 管理员禁止安装、卸载或未知来源 | 否 |
| 旧版包验证服务 / Play Protect | 对应用内容、恶意行为或包风险做判断 | 否 |
| Developer Verification | 开发者身份、包名与密钥登记不满足当前策略 | 当前机制 |
| SDM / dex 元数据 | 安装时附带的 dex 编译优化元数据是否可信 | 否 |
| `dexopt` / ART 应用性能配置文件 | 安装后代码编译状态和启动性能 | 否 |

可以按下面的职责模型理解：

> Developer Verification 是安装继续条件中的一项，无法取代 Android 现有的安装安全模型。

它通过 Android 17 的 `PackageInstallerSession` 接入统一安装事务；Google 的实际验证规则由设备上的 verifier 和当前政策控制；普通安装器只应根据公开回调处理用户动作与最终状态，不应猜测系统内部结论。

## 源码锚点

- [PackageInstaller：公开 extras、reason、policy 与 installer API](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/content/pm/PackageInstaller.java#449)
- [DeveloperVerifierService：系统 verifier 的回调入口](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/content/pm/verify/developer/DeveloperVerifierService.java#48)
- [DeveloperVerificationSession：请求信息、结果与 bypass API](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/content/pm/verify/developer/DeveloperVerificationSession.java#37)
- [PackageInstallerService：per-user policy 与 session 创建](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/services/core/java/com/android/server/pm/PackageInstallerService.java#298)
- [PackageInstallerSession：handleInstall 接入点](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/services/core/java/com/android/server/pm/PackageInstallerSession.java#3066)
- [PackageInstallerSession：Developer Verification 异步链路](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/services/core/java/com/android/server/pm/PackageInstallerSession.java#3244)
- [PackageInstallerSession：结果、用户动作与失败 extra](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/services/core/java/com/android/server/pm/PackageInstallerSession.java#3491)
- [DeveloperVerifierController：绑定、请求与超时管理](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/services/core/java/com/android/server/pm/verify/developer/DeveloperVerifierController.java#514)

## 官方资料

- [Android developer verification](https://developer.android.com/developer-verification/guides)
- [Frequently asked questions](https://developer.android.com/developer-verification/guides/faq)
- [Limited distribution](https://developer.android.com/developer-verification/guides/limited-distribution)
- [PackageInstaller API reference](https://developer.android.com/reference/android/content/pm/PackageInstaller)
- [Build.VERSION：SDK_INT_FULL](https://developer.android.com/reference/android/os/Build.VERSION#SDK_INT_FULL)
- [Build.VERSION_CODES_FULL](https://developer.android.com/reference/android/os/Build.VERSION_CODES_FULL)
- [Android Developer Verifier rollout](https://developer.android.com/blog/posts/android-developer-verification-rolling-out-to-all-developers-on-play-console-and-android-developer-console)
