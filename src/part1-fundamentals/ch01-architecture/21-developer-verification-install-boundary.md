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
task6_review_notes: "2026-06-17 Task6 revisiting复审：pass-light-edit。L1/L2 扫描通过（1.21 复审无禁用词、高频词、元叙述命中）；task9 auto-fix 已验证写作质量无回归；queue 无 pending；自动晋升 finalized。"
last_task6_review_log: "logs/review/2026-06-17-04-review.md"
task6_state: reviewed
task9_state: "reviewed"
drafted_date: "2026-05-20"
created_by: "task2a-knowledge-gap"
created_date: "2026-05-20"
gap_source: "官方文档/每日信息/AOSP结构"
task9_result: "auto-fixed"
task2b_state: "fixed"
last_task9_at: "2026-06-17T00:29:18+08:00"
task9_reviewed_date: "2026-06-17"
task9_reviewed_by: "openclaw-task9"
task9_review_notes: "2026-06-17 Task9 deep-review: AUTO-FIX P1 1; separated ADV enforcement scope (Android 7+ certified devices via Play services) from PackageInstaller 36.1 reason-code API surface; no queue item."
last_task9_review_log: "logs/deep-review/2026-06-17-00-deep-review.md"
last_task9_autofix_at: "2026-06-17"
task6_result: pass-light-edit
last_task2b_lite_at: "2026-06-30"
task2b_lite_note: "2026-06-30 Task2B Lite: 修复 last_task6_review_log 字段被 title 污染的机械错误。"
reviewed_by: openclaw-task6
reviewed_date: '2026-06-17'
last_task6_at: "2026-06-17T04:06:00+08:00"
deepseek_cn_review_state: done
last_deepseek_cn_review_at: 2026-06-17
last_task6_audit: "2026-06-27"
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
| Google 的开发者验证政策 | 哪些设备、区域、渠道和用户路径需要验证 | Android Developer Verifier、Google Play services、开发者管理中心 | 官方称覆盖 Android 7 及以上的认证 certified Android devices；分阶段启用 |
| Android 平台机制 | 安装会话如何请求 verifier、等待结果、触发用户动作并回传错误 | `PackageInstallerSession`、`DeveloperVerifierController`、`PackageInstaller` API | 锚定 `android-17.0.0_r1`；公开结果 API 自 36.1 提供 |
| APK 与安装信任链 | APK 是否可解析、签名是否有效、升级证书是否兼容、权限与设备策略是否允许 | APK Signature Scheme、PMS、PackageInstaller、DPM、package verifier | 由各自的平台版本和策略决定 |

Android 17 AOSP 提供 verifier 接入框架，却没有把 Google 的身份数据库和判定逻辑开源在 `frameworks/base` 中。实际 verifier 是系统指定的服务提供者；在 Google 认证设备上，官方把 Android Developer Verifier 描述为一项新的 Google 系统服务，并说明 Android 7 及以上设备通过 Google Play 服务接收相关更新。

AOSP 中存在这些类，也不表示任意 AOSP 构建都会自动执行 Google 的政策。Android 17 的 `PackageInstallerService` 默认策略是 `DEVELOPER_VERIFICATION_POLICY_NONE`；设备没有配置 verifier，或功能开关没有启用时，session 会跳过这一步。

`android.content.pm.verify.developer` 下的 `DeveloperVerifierService`、`DeveloperVerificationSession` 和 `DeveloperVerificationStatus` 都标有 `@SystemApi` 与 `@hide`。它们是平台与受信 verifier 的协议，普通应用无法通过公开 SDK 直接实现或调用。普通安装器应使用 `PackageInstaller` 公开 extras、reason code 和扩展接口。

## 2. 截至 2026-07-25，政策执行到哪里

### 2.1 2026 年 9 月只在首批渠道执行

从 2026-09-30 起，巴西、印度尼西亚、新加坡和泰国的认证 Android 设备开始执行首批验证，但当前公布的范围只覆盖下列参与商店发起的安装：

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
- 2027 年开始，计划把保护扩展到全球认证 Android 设备上的所有应用。

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

首批执行的 form factor 也有一层细节：Google Play 分发的应用需要登记所有 form factor；Play 以外的 2026 年首批强制范围当前落在所选四国的手机与 tablet。不要把手机上的实验结果直接外推到 TV、Auto 或 Wear。

### 2.2 特殊分发路径

| 路径 | 当前官方边界 | 工程理解 |
|---|---|---|
| ADB | 工作流保持不变，可安装未注册应用 | 只证明开发调试路径可用，不能替代真实商店验收 |
| 高级流程（Advanced flow） | 2026 年 8 月面向 power users 推出；一次设置后可安装未注册应用 | 用户明确接受风险的旁加载路径，不是商店静默绕过接口 |
| 有限分发（Limited distribution） | 免费、无需政府签发身份证件，最多分享给 20 台经最终用户明确授权的设备 | 适合学习、课堂、家庭和非商业小范围分享 |
| Managed device + organization store | 由 IT 管理员审核的组织内应用不要求完成验证 | 同一 APK 离开托管商店或进入非托管设备后，不能继续假设豁免 |

Advanced flow 不是安装器可自行打开的开关。官方常见问题说明的流程包含启用开发者模式、反诱导确认、重启与重新认证、24 小时等待，以及再次使用生物识别或 PIN 确认。ADB 不受这段等待时间影响。

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

攻击者拿到已注册应用的包名，却没有合法私钥时：

1. Developer Verification 不能让伪造 APK 获得合法签名。
2. APK Signature Scheme 校验仍会发现签名无效。
3. 若设备上已有正版应用，升级安装还要通过 signing lineage / certificate compatibility 检查。

一个 APK 的 v2/v3/v4 签名有效，只说明 APK 由对应密钥签发且内容未被篡改，不能自动证明开发者已完成身份验证，或包名已注册到对应账号。

发版资产至少要同时维护包名、当前与历史 signing certificate、验证账号与状态，以及各渠道最终交付 APK 的证书指纹。渠道重签会同时破坏升级兼容性和包名注册证明。

## 4. Android 17 对普通安装器公开了什么

### 4.1 API 36.1 与 API 37

`PackageInstaller` 文档把 Developer Verification 的结果字段标为“Added in version 36.1”。Android 17 / API 37 继续提供这些接口，并把安装器目标 SDK 大于 36 作为新的回调行为边界。

36.1 是次要 minor SDK，不应只检查 `Build.VERSION.SDK_INT >= 36`。需要区分 minor release 时，使用：

```kotlin
val supportsDeveloperVerificationResult =
    Build.VERSION.SDK_INT >= 36 &&
        Build.VERSION.SDK_INT_FULL >= Build.VERSION_CODES_FULL.BAKLAVA_1
```

Android 17 的 `Build.VERSION_CODES_FULL.CINNAMON_BUN` 为 37.0，自然满足这个条件。代码仍需用包含相应符号的 SDK 编译。

### 4.2 失败原因

| 常量 | 值 | 含义 |
|---|---:|---|
| `DEVELOPER_VERIFICATION_FAILED_REASON_UNKNOWN` | 0 | verifier 超时、连接失败，或报告未知原因导致无法完成 |
| `DEVELOPER_VERIFICATION_FAILED_REASON_NETWORK_UNAVAILABLE` | 1 | verifier 明确报告网络不可用 |
| `DEVELOPER_VERIFICATION_FAILED_REASON_DEVELOPER_BLOCKED` | 2 | verifier 已完成判断，但开发者未通过当前策略 |

`UNKNOWN` 不代表“未提供原因”。读取前必须检查 extra 是否存在，不能只使用默认值 0。

### 4.3 结果 extras

| Extra | 类型 | 用途 |
|---|---|---|
| `EXTRA_DEVELOPER_VERIFICATION_FAILURE_REASON` | `int` | 安装最终因 Developer Verification 中止时解释原因 |
| `EXTRA_DEVELOPER_VERIFICATION_LITE_PERFORMED` | `boolean` | 在失败结果中标记 verifier 是否只做了 lite verification |
| `EXTRA_DEVELOPER_VERIFICATION_EXTENSION_RESPONSE` | `PersistableBundle` | verifier 对 installer extension params 的响应 |
| `Intent.EXTRA_INTENT` | `Intent` | 需要用户动作，或提供可延后展示的系统解释页 |

`SessionParams.setExtensionParams()` 与 `getDeveloperVerificationServiceProvider()` 允许安装器和 verifier 扩展私有协议。`Bundle` 的结构由 verifier 实现决定，并非跨设备通用协议。安装器只有确认 provider 后才能解释它；遥测也不应默认原样上传未知 `Bundle`。

## 5. 一次提交可能产生多次回调

`Session.commit(IntentSender)` 只是把封存后的会话交给系统异步处理。方法成功返回不代表安装已经完成。

Developer Verification 失败时，`EXTRA_STATUS` 取决于安装器的目标 SDK、权限和失败是否允许用户处理：

| 安装器 | 首个回调 | 后续结果 |
|---|---|---|
| target SDK ≤ 36，只有 `REQUEST_INSTALL_PACKAGES` | 先收到不带原因的 `STATUS_PENDING_USER_ACTION` | 用户允许绕过则继续；否则返回 `STATUS_FAILURE_ABORTED` + reason |
| target SDK ≤ 36，持有特权 `INSTALL_PACKAGES` | 通常直接收到 `STATUS_FAILURE_ABORTED` + reason | 不依赖普通用户确认流程 |
| target SDK ≥ 37，需要用户输入的非阻断问题 | 先收到不带原因的 `STATUS_PENDING_USER_ACTION` | 用户重试/允许后继续，或最终 aborted + reason |
| target SDK ≥ 37，其余阻断结果 | `STATUS_FAILURE_ABORTED` + reason | 可能带 `Intent.EXTRA_INTENT`，供系统解释原因 |

系统默认 Package Installer 是特例：AOSP 会优先让它展示相应系统 UI。

安装器应把 pending 看成中间状态：

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

应用不在前台时直接启动待处理 Intent，可能被后台启动限制拦住，也会造成突兀体验。公开 API 建议发送通知，让用户回到安装器后再进入系统页面。

## 6. Android 17 的真实源码调用链

Android 17 把新机制直接接入 `PackageInstallerSession`，没有把 Google 的业务判定写进旧的 package verifier。

### 6.1 创建会话：冻结默认策略并预热 verifier

`PackageInstallerService.createSessionInternal()` 从 per-user 策略表读取默认值，作为会话的 initial policy 和 current policy。策略会写入会话 XML，因此进程重启不会改变已创建会话的初始边界。

满足以下条件时，构造 `PackageInstallerSession` 会提前绑定 verifier：

- 验证功能已启用；
- 设备配置了验证器服务提供者；
- 当前不是多包父会话；
- session 不是从重启状态恢复。

若 `SessionParams.appPackageName` 已提供包名，controller 还会调用 `onPackageNameAvailable()` 让 verifier 预取数据。此时尚未开始验证，只是 pre-warm。

### 6.2 commit：封存、流式校验，再进入安装消息

下面的调用序列用于定位 `commit()` 之后、Developer Verification 之前的会话状态转换：

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

`streamValidateAndCommit()` 会准备 DataLoader、验证 APK/APEX 会话的基本结构并标记 committed。执行到这里仍未安装成功。

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

单包会话使用一个 `CompletableFuture`。multi-package session 不验证 parent，而是分别验证每个 child；任一 child 失败，parent 整体失败。

### 6.4 controller 与 verifier 的交互

`startDeveloperVerificationSession()` 交给 `DeveloperVerifierController` 的信息包括：

- package name；
- staged package URI；
- `SigningInfo`；
- 清单声明的共享库；
- 当前验证策略；
- 安装器扩展参数；
- ADB/强制验证的内部标志。

controller 使用 `PackageManager.ACTION_VERIFY_DEVELOPER` 绑定设备指定的 `DeveloperVerifierService`，然后调用 `onVerificationRequired(session)`；用户请求重试时调用 `onVerificationRetry(session)`；超时后调用 `onVerificationTimeout(id)`。

verifier 通过 `DeveloperVerificationSession` 回报：

```text
reportVerificationComplete(status)
reportVerificationIncomplete(reason)
reportVerificationBypassed(reason)
```

完整结果包含 `isVerified`、lite verification 状态、App Metadata 状态和可选失败说明。incomplete 当前只区分 unknown 与 network unavailable。

### 6.5 结果怎样回到原安装链

下面的分支图说明 verifier 结果怎样完成 future，并决定恢复原安装链还是结束会话：

```text
验证器回调
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

Developer Verification 位于 APK 已解析、原有 session verification 继续运行之前。通过后，包仍可能因为签名、设备策略、存储、shared library、APK 格式或后续安装事务失败。

## 7. policy 决定失败后的处理方式

Android 17 AOSP 定义了四种系统 system API policy：

| Policy | developer blocked | unknown / 连接失败 / 超时 | network unavailable |
|---|---|---|---|
| `NONE` | 不阻断 | 不阻断 | 不阻断 |
| `BLOCK_FAIL_OPEN` | 阻断 | 允许用户继续 | 允许重试或继续 |
| `BLOCK_FAIL_WARN` | 阻断 | 允许用户继续 | 允许重试或继续 |
| `BLOCK_FAIL_CLOSED` | 阻断 | 阻断 | 允许用户重试 |

`BLOCK_FAIL_OPEN` 与 `BLOCK_FAIL_WARN` 在 Android 17 头文件注释中的安装结果描述相同；不要只凭名字推导额外语义。

per-user 默认策略由 verifier 或系统指定的 policy delegate 设置。verifier 还可通过会话的 `setPolicy()` 覆盖当前请求。业务代码不能只凭国家码模拟最终判定，必须以系统回调为准。

## 8. ADB 的绕过边界

官方面向开发者的承诺是 ADB 工作流不变。Android 17 源码把这个产品承诺拆成机制与结果两层：旧的非强制路径可以直接跳过；启用 `verificationServiceAdb` 后，ADB 请求也可送到 verifier，并通过 `FLAG_VERIFICATION_IS_ADB` 表明来源。verifier 可用 `DEVELOPER_VERIFICATION_BYPASSED_REASON_ADB` 明确回报 bypass。

若内部会话还设置了 `forceVerification`，平台会追加 `FLAG_VERIFICATION_FORCED_ON_ADB`；即便如此，源码注释仍要求只有 blocking policy 才能阻断。这些都属于命令行、测试或系统管理边界，不是普通第三方安装器 API，也不改变常规 ADB 用于开发测试的产品承诺。

- `adb install` 成功：证明 APK 和调试安装路径基本可用。
- 商店安装成功：证明该商店、设备、账号、区域和策略组合可用。
- 两者不能互相替代。

## 9. 安装耗时应该怎样拆

安装端到端耗时至少包含下面这些阶段，不能全部记到 Developer Verification：

```text
包体获取
  + session 写入
  + seal / stream validation
  + 普通用户授权等待
  + Developer Verification
  + 原有软件包验证
  + native library / 安装事务 / dexopt
  + 最终回调
```

controller 会在会话创建时尝试 pre-warm verifier，正式请求则在 `handleInstall()` 解析 APK 后发送。只看“创建会话到成功”无法得到纯验证耗时。

Android 17 r1 控制器的默认参数是：

- verifier 连接等待：10 秒；
- verifier 请求等待：10 秒；
- verifier 可申请延长的总上限：10 分钟。

它们来自 `DeviceConfig.NAMESPACE_PACKAGE_MANAGER_SERVICE`，是默认值，不是兼容性保证或产品 SLA。OEM、系统更新和实验配置都可能改变它们。

| 时间点 | 普通安装器是否可见 | 含义 |
|---|---|---|
| session 创建、文件写入 | 可见 | 安装器自身 I/O |
| `commit()` | 可见 | 系统异步处理起点 |
| 首次 `STATUS_PENDING_USER_ACTION` | 可见 | 需要用户介入，不一定来自 Developer Verification |
| Developer Verification failure reason | 仅失败且系统提供时可见 | 可确认验证层失败 |
| 最终成功/ failure | 可见 | 安装会话结束 |
| verifier bind、request、response 精确时间 | 普通应用不可直接取得 | 需要 system metrics、trace 或受控设备日志 |

普通安装器可上报“提交 → 首次回调”和“提交 `commit → terminal callback`，但不能把前者直接命名为“开发者验证耗时”。

## 10. 推荐的错误归因顺序

下面的决策顺序以公开状态和附加原因为依据，避免仅凭错误文本归因：

```text
收到安装回调
  ├─ STATUS_PENDING_USER_ACTION
  │    └─ 中间状态：保存会话上下文并处理 Intent.EXTRA_INTENT
  ├─ STATUS_FAILURE_ABORTED
  │    ├─ 有开发者验证原因 → 归入开发者验证
  │    └─ 无原因 → 检查用户取消、session abandon 等原因
  ├─ STATUS_FAILURE_BLOCKED
  │    └─ 检查 DPM、用户限制、旧 package verifier、关键包保护
  ├─ STATUS_FAILURE_INVALID / CONFLICT
  │    └─ 检查 APK、split、签名、版本与现有包
  └─ STATUS_SUCCESS
       └─ 安装完成；不等于应用首帧已经出现
```

`STATUS_FAILURE_BLOCKED` 的公开定义覆盖 device policy、package verifier 和系统关键包保护等来源。只有 `STATUS_FAILURE_ABORTED` 同时带 Developer Verification reason 时，才有充分证据归入本机制。

`EXTRA_STATUS_MESSAGE` 是调试文本，可能随系统版本、语言和 OEM 改变。它适合保留样本，不适合作为监控聚合键。

## 11. Android 17 r1 的 lite extra 类型不一致

公开契约规定 `EXTRA_DEVELOPER_VERIFICATION_LITE_PERFORMED` 是 `boolean`。但在 `android-17.0.0_r1` 中：

1. `setSessionFailedDueToDeveloperVerification()` 用 `Bundle.putBoolean()` 写入。
2. `sendOnPackageInstalled()` 复制到最终 Intent 时却调用 `extras.getInt()`。

这是 r1 源码中的类型不一致，不能把 `int` 当成新的公开协议。`Bundle.getInt()` 遇到原来的 `Boolean` 时还可能回落为默认值 0，因此 `true` 信息可能在复制过程中已经丢失。下面的防御性读取只能避免类型假设扩散，不能恢复已丢失的真值：

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

兼容代码应限制在适配层，并记录真实类型以便后续删除；业务层仍使用 `Boolean?`。

## 12. 遥测字段与隐私边界

建议记录：

- package name、versionCode、installer package 与 package source；
- installer target SDK、是否持有特权安装权限；
- `SDK_INT`、`SDK_INT_FULL`、session 是否 multi-package / staged；
- `EXTRA_STATUS`、reason extra 是否存在及枚举值；
- 是否出现待用户操作、停留多久、最终继续还是取消；
- managed / unmanaged、ADB/非 ADB；
- session write、commit 到首回调、commit 到终态的耗时；
- 服务端版本化的政策区域和渠道批次。

不建议默认记录未知验证器扩展 `Bundle`、系统解释页文本、身份文件、账号凭据或签名私钥，也不要用自由文本 status message 作为高基数主维度。

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

- 正式版、beta、企业版和历史包名都已盘点。
- package name 已登记到正确账号。
- 注册证明 APK 与最终渠道 APK 的 signing certificate 一致。
- Play App Signing、旧密钥、密钥轮换和非 Play 渠道的证书关系有记录。
- 渠道下载后的 APK 再次验签，防止重签或产物替换。

### 安装器

- 用 `SDK_INT_FULL` 处理 36.1 API 边界。
- 把 `STATUS_PENDING_USER_ACTION` 当成中间状态。
- target SDK 37 覆盖 pending、retry、install anyway 与 direct abort。
- 只有原因字段存在时才归因到开发者验证。
- 只在确认验证器服务提供者与数据结构后使用扩展参数。
- 后台收到 pending 时通过通知恢复，不盲目拉起 Activity。

### 测试维度

| 维度 | 样本 |
|---|---|
| 平台 | Android 16.1、Android 17 |
| 设备 | certified Google Android、无对应 verifier 的 AOSP/企业设备 |
| 安装器目标 SDK | ≤ 36、37 |
| 权限 | `REQUEST_INSTALL_PACKAGES`、特权 `INSTALL_PACKAGES` |
| 结果 | verified、developer blocked、network unavailable、timeout |
| 用户路径 | pending 后继续、重试、取消 |
| 分发 | 参与商店、非参与商店、直接旁加载、ADB、managed store |
| session | 单包、multi-package |

区域和商店策略要在真实分发入口验证。VPN、修改 locale 或实验室 ADB 成功，都不足以证明真实渠道路径。

## 14. 与其他安装机制的边界

| 机制 | 失败说明 | 是否由 Developer Verification 替代 |
|---|---|---|
| APK 解析与签名 | 文件损坏、签名无效、split 不一致、升级证书冲突 | 否 |
| 安装器权限与未知来源授权 | 调用者无权创建/提交安装，或用户未授权该来源 | 否 |
| Device Policy / 用户限制 | 管理员禁止安装、卸载或未知来源 | 否 |
| 旧 package verifier / Play Protect | 对应用内容、恶意行为或包风险做判断 | 否 |
| Developer Verification | 开发者身份、包名与密钥注册不满足当前策略 | 当前机制 |
| SDM / dex metadata | 安装附带的执行优化元数据是否可信 | 否 |
| dexopt / ART profile | 安装后代码编译状态和启动性能 | 否 |

可以按下面的职责模型理解：

> Developer Verification 是安装继续条件中的一项，无法取代 Android 现有的安装安全模型。

它通过 Android 17 的 `PackageInstallerSession` 接入统一安装事务；Google 的实际验证规则由设备上的 verifier 和当前政策控制；普通安装器只应根据公开回调处理用户动作与终态，不应猜测系统内部结论。

## 源码锚点

- [PackageInstaller：公开附加字段、原因、策略与安装器 API](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/content/pm/PackageInstaller.java#449)
- [DeveloperVerifierService：系统 verifier 的回调入口](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/content/pm/verify/developer/DeveloperVerifierService.java#48)
- [DeveloperVerificationSession：请求信息、结果与绕过 API](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/content/pm/verify/developer/DeveloperVerificationSession.java#37)
- [PackageInstallerService：per-user policy 与会话创建](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/services/core/java/com/android/server/pm/PackageInstallerService.java#298)
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
