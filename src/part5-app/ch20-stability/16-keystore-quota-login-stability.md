---
title: "Android 17 Keystore 配额与登录故障治理"
chapter: "20.16"
section: "20.16"
status: ready-for-review
drafted_date: "2026-05-25"
applicable_versions: "Android 11 (API 30) - Android 17 (API 37)"
last_verified: "2026-05-25"
last_verified_against: "Android Developers Android 17 behavior changes, API level 37 diff, AOSP Keystore docs"
confidence: medium
sources:
  - type: clippings-structure-ref
    path: "Clippings/Android 应用稳定性剖析与优化 - Java Crash 监控：实现自定义 Crash 处理器.md"
  - type: clippings-structure-ref
    path: "Clippings/Android 应用稳定性剖析与优化 - Java 堆栈：深入了解 Throwable.md"
  - type: clippings-structure-ref
    path: "Clippings/Android 应用稳定性剖析与优化 - 实现 FD 监控：文件描述符（FD）超限怎么办？.md"
  - type: clippings-structure-ref
    path: "Clippings/Android 应用稳定性剖析与优化 - 线程监控：如何解决“匿名”线程？.md"
  - type: official
    path: "https://developer.android.com/about/versions/17/behavior-changes-all"
  - type: official
    path: "https://developer.android.com/reference/android/security/KeyStoreException"
  - type: official
    path: "https://developer.android.com/sdk/api_diff/37/changes/android.security.KeyStoreException"
  - type: official
    path: "https://developer.android.com/privacy-and-security/keystore"
  - type: aosp-doc
    path: "https://source.android.com/docs/security/features/keystore"
  - type: aosp-doc
    path: "https://source.android.com/docs/security/features/keystore/implementer-ref"
tags: [stability, keystore, keymint, android17, login]
related_chapters: ["8.12", "20.2", "20.7", "26.5", "26.9"]
created_by: "task2a-knowledge-gap"
created_date: "2026-05-25"
gap_source: "官方文档/每日信息/AOSP结构"
---

# 20.16 Android 17 Keystore 配额与登录故障治理

<!-- outline-start -->
## 要点

### 🔹 Android 17 per-app Keystore 配额边界
说明非系统 App、targetSdk 37、系统 App 和旧 targetSdk 的配额差异，把 50,000 / 200,000 key 上限与 `ERROR_TOO_MANY_KEYS` 版本行为说清楚。

### 🔹 登录与支付场景为什么会撞上 key 数量上限
梳理设备绑定、账号切换、生物认证、Passkey、加密缓存、证书轮换和测试环境残留 key 的增长来源。

### 🔹 KeyStoreException 的分类与降级策略
区分配额、权限、认证状态、KeyMint 不支持和临时系统错误，避免把所有异常都重试或都提示用户重新登录。

### 🔹 key 生命周期治理
覆盖 alias 命名、账号退出清理、版本迁移、废弃 key 回收、批量删除风险和多进程同步。

### 🔹 线上证据包字段
设计异常码、targetSdk、key alias 前缀、账号态、设备加密状态、系统版本和调用场景字段，便于定位是配额耗尽还是业务状态异常。

### 🔹 灰度与压测方法
给出自动化构造大量 key、升级 targetSdk、回归登录/支付/生物认证流程的测试组合。

## 扩展

### 🔸 与 8.12 Keystore/KeyMint 延迟章节的边界
8.12 覆盖调用耗时和硬件路径；20.16 覆盖 key 数量、异常分类和故障恢复。

### 🔸 与 26.9 进程退出归因的关系
如果 key 配额导致启动流程崩溃，归因要同时保留 ApplicationExitInfo 和业务异常上报。

<!-- outline-end -->

Android 17 给 Keystore 增加了按 App 计数的 key 上限。登录、支付、设备绑定这类路径如果长期按账号、设备、证书版本或测试环境反复生成新 alias，升级 targetSdk 37 后可能从偶发登录失败变成稳定的 `KeyStoreException`。处理这类问题要落到三个动作：上线前盘点 key 数量，运行时分类异常，出问题后保留能定位到 alias 生命周期的证据包。

[结构参考: Clippings/Android 应用稳定性剖析与优化 - Java Crash 监控：实现自定义 Crash 处理器.md]

## Android 17 的 per-app Keystore 配额边界

Android Developers 的 Android 17 行为变更文档明确写到，系统从 Android 17 开始限制单个 App 可拥有的 Keystore key 数量：targetSdk 37 及以上的非系统 App 上限为 50,000 个，其他 App 上限为 200,000 个；系统 App 不按 targetSdk 降到 50,000，仍为 200,000 个。[已验证: 官方文档, developer.android.com/about/versions/17/behavior-changes-all]

超出上限后，创建 key 的调用会失败并抛出 `KeyStoreException`。错误码按 targetSdk 分流：targetSdk 37 及以上返回 `ERROR_TOO_MANY_KEYS`；其他 App 返回 `ERROR_INCORRECT_USAGE`。API 37 的 diff 也显示 `KeyStoreException` 新增了 `ERROR_TOO_MANY_KEYS` 字段，API 参考页说明这个字段只对 targetSdk 37 及以上 App 发出。[已验证: 官方文档, developer.android.com/sdk/api_diff/37/changes/android.security.KeyStoreException][已验证: 官方文档, developer.android.com/reference/android/security/KeyStoreException]

这个变更对业务的影响有两个层次：

| 维度 | Android 17 行为 | 工程处置 |
| --- | --- | --- |
| 非系统 App，targetSdk >= 37 | 50,000 个 key 上限，错误码为 `ERROR_TOO_MANY_KEYS` | targetSdk 升级前做别名盘点和清理演练 |
| 非系统 App，targetSdk < 37 | 200,000 个 key 上限，错误码仍可能落到 `ERROR_INCORRECT_USAGE` | 不能只按 `ERROR_TOO_MANY_KEYS` 判断配额问题 |
| 系统 App | 200,000 个 key 上限 | 仍要做生命周期治理，系统身份不等于无限资源 |
| 旧设备 | 无 Android 17 新上限 | 保持清理逻辑一致，避免升级系统后集中暴露 |

Android Keystore 通过 Java Cryptography Architecture provider 暴露给 App，App 侧以 alias 访问 key；AOSP 文档说明这些 App alias 会映射到内部 `APP` domain，并用调用方 UID 区分不同 App 的 key。[已验证: AOSP 文档, source.android.com/docs/security/features/keystore] 因此，配额治理要按 UID 和 alias 维度看，不能只按账号表或业务数据库里的记录数估算。

## 登录与支付场景的 key 增长来源

登录和支付路径容易积累 key，是因为它们经常把安全、账号、设备、风控和测试环境绑在一起。单次生成 key 看起来没问题，持续几年后 alias 可能变成资源泄漏。

常见增长来源可以按触发动作拆开：

| 来源 | 典型 alias 形态 | 风险点 | 治理动作 |
| --- | --- | --- | --- |
| 设备绑定 | `bind_${userId}_${deviceId}_${timestamp}` | 每次重绑都生成新 key，旧 key 没有删除 | 用稳定设备槽位，重绑时替换或标记旧 key 过期 |
| 账号切换 | `login_${userId}_${env}` | 多账号、游客态、测试账号长期残留 | 退出账号时只清理当前账号命名空间，保留共享 key |
| 生物认证 | `bio_${userId}_${authVersion}` | enrollment 变化、锁屏变更后旧 key 不可用但仍留在 Keystore | 捕获失效异常后进入重建流程，同时删除旧 alias |
| Passkey / 凭据 | `credential_${rpId}_${account}` | 本地凭据、服务端凭据和 Keystore key 生命周期不一致 | 用凭据 ID 反查 key，撤销凭据时同步回收 |
| 加密缓存 | `cache_${fileId}`、`db_${table}_${row}` | 为每个文件或记录建 key，数量随数据量线性增长 | Keystore 只保护 data key，数据批量加密走普通 crypto |
| 证书轮换 | `cert_${version}_${createdAt}` | 版本升级反复创建，回滚后旧 key 无引用 | 迁移脚本记录新旧 alias 映射，成功后清理过期版本 |
| 测试环境残留 | `debug_${caseId}_${runId}` | 自动化压测和 QA 设备累计生成大量 key | 测试包加清理入口，CI 设备每轮回收测试前缀 |

[结构参考: Clippings/Android 应用稳定性剖析与优化 - 实现 FD 监控：文件描述符（FD）超限怎么办？.md]

FD、线程和 key 都有同一种稳定性模式：单个对象创建成本不高，但缺少归属和回收规则后会变成上限问题。FD 监控会记录打开路径和调用栈；Keystore 配额治理也要记录 alias 前缀、创建场景、账号态和版本迁移来源。只记录“创建失败”太晚，无法判断哪一类 key 在增长。

## KeyStoreException 分类与降级策略

`KeyStoreException` 不是一个动作。API 参考页把它描述为 Keystore / KeyMint 层生成或使用 key 失败时携带错误信息的异常，并提供 `getNumericErrorCode()`、`getRetryPolicy()`、`isTransientFailure()`、`isSystemError()` 等方法。[已验证: 官方文档, developer.android.com/reference/android/security/KeyStoreException]

登录路径里建议把异常分成五类：

| 分类 | 典型错误 | 处理方式 | 用户提示 |
| --- | --- | --- | --- |
| 配额耗尽 | `ERROR_TOO_MANY_KEYS`；targetSdk < 37 时可能表现为 `ERROR_INCORRECT_USAGE` 加消息文本 | 停止继续创建，进入清理和重建流程 | “本机安全凭据需要整理后重试”这类可恢复提示 |
| 认证状态 | `ERROR_USER_AUTHENTICATION_REQUIRED`、`ERROR_KEYSTORE_UNINITIALIZED` | 重新触发生物认证或设备凭据流程 | 引导用户完成认证，不提示重新安装 |
| key 失效 | `ERROR_KEY_DOES_NOT_EXIST`、`ERROR_KEY_CORRUPTED`、时间有效期错误 | 删除业务映射，重建 key 或走账号重新绑定 | 提示重新验证登录态 |
| 权限或能力不支持 | `ERROR_PERMISSION_DENIED`、`ERROR_UNIMPLEMENTED`、StrongBox 不可用异常 | 关闭当前安全级别策略或切换服务端流程 | 按业务风险给替代验证方式 |
| 系统或瞬时错误 | `ERROR_INTERNAL_SYSTEM_ERROR`、`ERROR_KEYSTORE_FAILURE`、`ERROR_KEYMINT_FAILURE`，并结合 retry policy | 有上限的退避重试；超过阈值后降级 | 告知稍后重试，保留问题编号 |

JCA 调用处经常把底层 `KeyStoreException` 包进 `ProviderException` 或算法相关异常里。异常处理代码要检查 cause 链，不能只 catch 一个外层类型。

这段示意代码用于登录 key 创建失败后的公开错误码提取，并把配额类问题和瞬时错误分开。关键分支有三处：targetSdk < 37 的兼容路径、只给瞬时错误的重试、配额错误进入清理流程。

```kotlin
fun Throwable.findKeyStoreException(): KeyStoreException? {
    var current: Throwable? = this
    while (current != null) {
        if (current is KeyStoreException) return current
        current = current.cause
    }
    return null
}

fun classifyKeystoreFailure(error: Throwable): KeystoreFailure {
    val keyStoreError = error.findKeyStoreException()
        ?: return KeystoreFailure.Unknown(error.javaClass.name)

    return when (keyStoreError.numericErrorCode) {
        KeyStoreException.ERROR_TOO_MANY_KEYS -> KeystoreFailure.TooManyKeys
        KeyStoreException.ERROR_INCORRECT_USAGE -> {
            if (keyStoreError.message?.contains("key", ignoreCase = true) == true) {
                KeystoreFailure.PossibleTooManyKeysOnLegacyTarget
            } else {
                KeystoreFailure.IncorrectUsage
            }
        }
        KeyStoreException.ERROR_USER_AUTHENTICATION_REQUIRED -> KeystoreFailure.AuthRequired
        KeyStoreException.ERROR_KEY_DOES_NOT_EXIST,
        KeyStoreException.ERROR_KEY_CORRUPTED -> KeystoreFailure.KeyInvalid
        KeyStoreException.ERROR_PERMISSION_DENIED,
        KeyStoreException.ERROR_UNIMPLEMENTED -> KeystoreFailure.NotAllowedOrUnsupported
        else -> if (keyStoreError.isTransientFailure) {
            KeystoreFailure.Transient(keyStoreError.retryPolicy)
        } else {
            KeystoreFailure.Permanent(keyStoreError.numericErrorCode)
        }
    }
}
```

这段代码只表达分类方式。生产实现还要把外层异常类型、调用 API、alias 前缀、targetSdk、Android 版本和账号态一起上报，否则后端只能看到一组分散的错误码。

## key 生命周期治理

Keystore key 要像数据库表、缓存文件、FD 一样有生命周期。治理入口不在报错时，而在 alias 设计、创建前检查、迁移和退出账号流程里。

alias 建议包含稳定前缀、业务域、账号或设备槽位、版本号四类信息，避免把时间戳、随机数、runId 放进长期 key 名称。可复用的 key 用确定性 alias；必须轮换的 key 单独记录 `generation`，并给旧 generation 设置可回收状态。

| 阶段 | 动作 | 边界 |
| --- | --- | --- |
| 创建前 | 查询业务映射中是否已有可用 alias；必要时验证 `KeyStore.containsAlias(alias)` | 不能因为本地映射丢失就直接创建新 key，先尝试恢复 |
| 创建后 | 记录 alias、用途、安全级别、账号槽位、创建版本、最近使用时间 | 不记录原始 token、支付数据或可还原身份信息 |
| 账号退出 | 删除账号私有 key；保留设备级共享 key | 多账号场景不能全量清空 `AndroidKeyStore` |
| 版本迁移 | 新旧 alias 映射写入迁移表；确认新 key 可用后删除旧 key | 迁移失败要能回滚，不能一次删除全部旧 alias |
| 异常恢复 | 对 `ERROR_KEY_CORRUPTED`、认证失效、配额类错误走不同流程 | 配额错误不能通过无限重建解决 |
| 定期回收 | 后台任务清理已废弃、长期未使用、测试前缀 key | 批量删除要限速，并和登录/支付路径互斥 |

枚举 alias 的动作可能遍历大量项目，应放在后台线程，并做好耗时和失败记录。这段示意代码只用于盘点本 App 的 `AndroidKeyStore` alias，不能在主线程或崩溃 handler 里执行。

```kotlin
fun snapshotAndroidKeystoreAliases(): List<AliasSnapshot> {
    val keyStore = KeyStore.getInstance("AndroidKeyStore").apply { load(null) }
    val result = mutableListOf<AliasSnapshot>()
    val aliases = keyStore.aliases()

    while (aliases.hasMoreElements()) {
        val alias = aliases.nextElement()
        result += AliasSnapshot(
            alias = alias,
            prefix = alias.substringBefore('_', missingDelimiterValue = alias),
            hasCertificate = keyStore.getCertificate(alias) != null,
            entryType = when {
                keyStore.isKeyEntry(alias) -> "key"
                keyStore.isCertificateEntry(alias) -> "certificate"
                else -> "unknown"
            }
        )
    }
    return result
}
```

这个快照只能回答“当前有哪些 alias”。业务还要把快照和自己的 key_registry 对齐：Keystore 里有但业务 registry 没引用的，是孤儿 key；registry 里有但 Keystore 找不到的，是业务映射损坏；同一账号出现多个 active generation，说明迁移或轮换没有收尾。

[自动发现] 多进程 App 要给 key 创建和删除加进程级互斥。登录进程、主进程、支付 SDK 进程如果同时发现 alias 不存在并各自创建，短时间内就会制造重复 key。可选方案是把 key 管理收束到主进程的 bound service，或用文件锁保护创建段；文件锁只保护 App 私有目录内的协调，不改变 Keystore 的访问控制语义。

## 线上证据包字段

配额问题的排查重点不是“有一个异常”，而是“哪个命名空间在增长、什么时候开始增长、升级 targetSdk 后错误码怎样变化”。证据包字段要围绕 alias 生命周期设计。

| 字段 | 示例 | 用途 |
| --- | --- | --- |
| `scene` | `login_restore`、`payment_confirm`、`device_bind` | 识别用户路径 |
| `api` | `KeyGenerator.generateKey`、`KeyStore.deleteEntry`、`Cipher.init` | 定位失败动作 |
| `key_alias_prefix` | `login`、`bio`、`credential`、`cache` | 聚合增长来源 |
| `alias_generation` | `v3`、`202605` | 判断轮换和迁移状态 |
| `target_sdk` | `37` | 区分 `ERROR_TOO_MANY_KEYS` 与兼容错误码 |
| `android_api` | `37` | 判断是否处在 Android 17 行为范围 |
| `numeric_error_code` | `18`、`13` | 使用公开 API 归因 |
| `retry_policy` | `RETRY_NEVER`、`RETRY_WITH_EXPONENTIAL_BACKOFF` | 控制重试策略 |
| `is_transient_failure` | `true` / `false` | 避免无限重试永久错误 |
| `account_state` | `anonymous`、`logged_in`、`switching` | 区分账号流程 |
| `keystore_alias_count_bucket` | `0-1k`、`1k-10k`、`10k-50k`、`50k+` | 不上传全量 alias 也能看趋势 |
| `cleanup_result` | `skipped`、`deleted_12`、`failed_permission` | 观察自愈效果 |
| `process_name` | `main`、`payment`、`push` | 处理多进程竞争 |
| `exit_reason` | `REASON_CRASH`、`REASON_ANR`、`none` | 和 26.9 拼接进程退出归因 |

[结构参考: Clippings/Android 应用稳定性剖析与优化 - Java 堆栈：深入了解 Throwable.md]

证据包不要上传完整 alias、账号 ID、token、密钥材料或支付凭据。alias 前缀、generation、hash 后的账号槽位和数量桶已经足够排查增长来源。需要抽样分析完整 alias 时，应走受控诊断任务，并在本地脱敏后上传。

如果配额失败触发启动崩溃，下一次启动要同时读取 `ApplicationExitInfo`。26.9 节已经说明 Android 11+ 可通过系统记录补退出原因；业务证据包补充失败前最近一次 key 动作、alias 前缀、targetSdk、错误码、是否进入 SafeMode。这样能区分“key 配额导致登录初始化崩溃”和“进程被系统回收后登录态恢复失败”。[详见 26.9 节]

## 灰度与压测方法

targetSdk 37 的灰度不能只看崩溃率。Keystore 配额属于状态型风险，低比例灰度可能刚好避开历史 key 多的用户。灰度前要先做本地盘点和线上采样，灰度中按 alias count bucket 观察失败率。

建议按三组测试推进：

| 测试组 | 构造方式 | 通过条件 |
| --- | --- | --- |
| targetSdk 升级回归 | 同一设备安装 targetSdk 36 包生成历史 alias，再升级 targetSdk 37 包 | 旧 alias 可读；新建 key 失败时分类正确；不会把配额错误当普通登录失败 |
| 大量 key 压测 | 自动生成接近 50,000 的测试前缀 key，再执行登录、支付、生物认证和退出账号 | 达到阈值前有告警；超限后进入清理流程；清理后可恢复 |
| 生命周期回收 | 多账号切换、账号注销、服务端解绑、证书轮换、版本回滚 | 账号私有 key 被清理；共享 key 不被误删；迁移失败可回滚 |

压测脚本要使用测试专用前缀，例如 `qa_quota_${runId}_${index}`，并提供可靠清理入口。不要在个人主力设备上跑无上限生成脚本；如果脚本中断，下一轮测试先枚举并删除测试前缀。

灰度策略按风险从小到大排列：

- **预检灰度**：targetSdk 37 包先对内部用户和 QA 设备开放，收集 alias count bucket、key 创建失败率、清理耗时。
- **低比例放量**：按设备型号、Android 版本、账号年龄、登录方式分桶观察，避免只看总失败率。
- **诊断开关**：对命中配额或接近阈值的用户打开短期 alias 盘点，不长期上传明细。
- **回退按钮**：发现配额问题集中后，远程关闭新 key 创建路径，切回复用现有 key 或账号重新验证流程。
- **清理任务**：先清理明确无业务引用的测试前缀和废弃 generation，再处理账号私有 key；不能全量清空 Keystore。

## 扩展：与 8.12 Keystore/KeyMint 延迟章节的边界

8.12 关注 `AndroidKeyStore` 调用穿过 App 进程、`keystore2`、KeyMint HAL、TEE / StrongBox 后产生的耗时和调度问题；20.16 处理 key 数量、异常分类和恢复路径。[详见 8.12 节]

两节的证据包可以共用 `scene`、`api`、`security_level`、`duration_ms` 和错误码字段，但判断口径不同。8.12 看到 P99 高，要看 Binder、operation slot、StrongBox 和主线程；20.16 看到创建失败，要看 alias 数量、命名空间、targetSdk 和生命周期。

AOSP KeyMint implementer 文档还说明，`begin()` 会创建 `IKeyMintOperation`，实现至少支持 16 个并发 operation，Keystore 使用最多 15 个并给 `vold` 留 1 个。[已验证: AOSP 文档, source.android.com/docs/security/features/keystore/implementer-ref] 这属于调用并发和延迟问题，不等同于 Android 17 的 key 数量配额。压测报告要把“key 数量上限”和“operation 并发上限”分开写。

## 扩展：与 26.9 进程退出归因的关系

配额问题本身通常是可恢复业务错误，但如果创建 key 放在启动主路径、异常分类又把它当成未预期异常抛出，就会变成启动崩溃。此时 26.9 的 `ApplicationExitInfo` 能补进程退出原因，20.16 的业务证据包负责解释为什么进入这条崩溃路径。

处理顺序建议如下：下次启动先读取退出归因和本地未上报业务异常；如果上一轮退出前存在 `TooManyKeys` 或 `PossibleTooManyKeysOnLegacyTarget`，先进入轻量登录恢复页，再执行后台清理和重新绑定。不要在启动首帧前做全量 alias 扫描，也不要在崩溃循环中继续创建新 key。

## 小结

Android 17 的 Keystore 配额把长期存在的 alias 生命周期问题显性化。稳定的处理方式是上线前盘点、运行时分类、出问题后保留证据包：targetSdk 37 及以上用 `ERROR_TOO_MANY_KEYS` 定位配额错误；旧 targetSdk 还要结合 `ERROR_INCORRECT_USAGE`、message 和调用场景判断；登录、支付、设备绑定路径要把 key 创建、复用、迁移和回收写进同一份契约。配额耗尽时，继续重试只会制造更多失败，应该先停新建、做受控清理，再恢复登录或支付流程。
