---
title: "Android 17 Keystore 配额与登录故障治理"
chapter: "20.14"
section: "20.14"
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
related_chapters: ["8.9", "20.2", "20.7", "26.5", "26.9"]
created_by: "task2a-knowledge-gap"
created_date: "2026-05-25"
gap_source: "官方文档/每日信息/AOSP结构"
---

# Android 17 Keystore 配额与登录故障治理

Android 17 开始按应用 UID 限制 Android Keystore 中的 key 数量。非系统应用以 API 37 为目标版本时，上限为 50,000；其他应用为 200,000，系统应用也使用 200,000。达到上限后，系统不会删除旧 key，也不会阻止应用继续使用仍然有效的旧 key；被拒绝的是新的生成或导入请求。

这类故障常在登录、设备绑定、支付签名或加密数据库初始化时暴露，但根因通常早已积累：alias 每次带新时间戳、账号退出不回收、轮换只加不删、测试任务长期留存。治理重点应前移到 alias 所有权和生命周期，不能等到 50,000 才临时枚举删除。

平台源码锚点为 `android-17.0.0_r1`。这里讨论 framework、keystore2 与 KeyMint 边界，不涉及 kernel 侧行为。

## 1. Android 17 配额的准确边界

官方文档给出的规则如下：

| 运行环境与应用身份 | key 上限 | 创建超限时的公开错误码 |
|---|---:|---|
| Android 17，非系统应用，`targetSdkVersion >= 37` | 50,000 | `ERROR_TOO_MANY_KEYS` |
| Android 17，非系统应用，`targetSdkVersion < 37` | 200,000 | `ERROR_INCORRECT_USAGE` |
| Android 17，系统应用 | 200,000 | 由 target SDK 决定返回哪个公开错误码 |
| Android 16 及更早版本 | 没有这项 Android 17 配额 | 不适用 |

这项变化属于 Android 17 的“所有应用行为变更”：旧 target 应用仍有 200,000 上限，只是兼容错误码保持为 `ERROR_INCORRECT_USAGE`。系统应用的数量上限固定为 200,000；若系统应用以 API 37 为目标，源码仍会用 SDK 37 对应的超限错误码。官方页面没有把“系统应用”描述成无限资源。

### 1.1 “每个应用”在源码中是“每个 UID”

`android-17.0.0_r1` 的 keystore2 在 `Domain::APP` 下把调用方 UID 写入 key descriptor 的 namespace，再按 `domain + namespace` 统计 client key entry。`count_key_entries()` 会把当前 keystore2 数据库和 legacy importer 中的 alias 数量相加。因此：

- 普通应用可按“本应用的 Android Keystore alias”理解这项配额。
- 同一包在不同 Android user/profile 下有不同 UID，计数彼此独立。
- 历史 shared UID 或特殊系统部署要按共享 UID 评估，不能只按包名统计。
- TEE、StrongBox 等安全级别没有各自独立的 50,000 额度；检查使用同一个 APP namespace 总数。
- 统计对象是 client key entry/alias。轮换产生的废弃 alias 会占额度，证书链或同一 alias 下的内部 blob 不能简单按文件数推算。

应用侧的 `KeyStore.aliases()` 或 `KeyStore.size()` 可用于盘点自己可见的条目，但它们不是系统配额查询 API。盘点结果要当作应用视角的估算，并记录枚举失败与耗时。

### 1.2 创建、导入和使用旧 key 要分开看

AOSP `KeystoreSecurityLevel.check_key_counts()` 在下面三条路径进入 KeyMint 前执行：

- `generate_key()`；
- `import_key()`；
- `import_wrapped_key()`。

计数达到上限时，检查直接返回错误。现有 key 的 `Cipher.init()`、`Signature.initSign()` 等使用路径没有经过这条“创建数量”检查，所以升级 target SDK 不会因配额本身让全部旧 key 同时失效。

还有一个容易遗漏的细节：配额检查发生在 rebind/覆盖旧 alias 之前。应用已经有 50,000 个 key 时，尝试以相同 alias 重新生成 key 也可能先被拒绝。恢复流程必须先确认并删除可回收 alias，释放额度后才能重建；“继续用同名 alias 重试”不是满额后的恢复办法。

## 2. 哪些业务设计会让 alias 持续增长

| 来源 | 常见设计 | 风险 | 调整方向 |
|---|---|---|---|
| 设备绑定 | alias 包含时间戳或每次绑定的随机 ID | 重绑只创建，不回收旧代 | 一个设备槽位对应一个 active generation，换代成功后回收旧代 |
| 多账号登录 | 每次登录都新建账号 key | 账号切换与注销后仍留存 | 使用不含明文账号的稳定 account slot；退出只清理该账号私有 key |
| 生物认证 | enrollment 或锁屏变化后直接新建 | 已失效 key 仍占 alias | 捕获认证相关异常，完成授权恢复后删除旧 alias 再创建 |
| 支付/风控 | 每笔订单或每次挑战各建一个 key | 业务量与 key 数量线性增长 | 长期身份 key 与一次性挑战数据分离；一次性数据不进入 Keystore |
| 加密文件/数据库 | 每个文件、表或记录创建 Keystore key | 数据规模直接变成 alias 数量 | 用少量 Keystore key 包装 data-encryption keys |
| 证书/算法轮换 | 新版本创建新 alias，旧版本永久保留 | 多次升级后代际堆积 | 清单记录 active、last-known-good、retired，按确认点回收 |
| SDK 或多进程 | 各组件各自判断“不存在就创建” | 命名冲突、重复代际、归属不明 | key 管理由单一组件负责，创建与删除使用跨进程协议 |
| QA/自动化 | alias 含 case ID、run ID | 共享测试设备长期累积 | 测试专用前缀、每轮清理和数量上限 |

Passkey 需要单独澄清。普通 relying-party 应用通过 Credential Manager 请求 passkey 时，凭据私钥通常由 credential provider 管理，不能直接把每个 passkey 都算成本应用的 Android Keystore alias。只有应用自己生成 Keystore key，或实现凭据提供方并持有相关 key 时，才进入本应用的清单。排查时应以本应用 `AndroidKeyStore` 可见 alias 和创建调用栈为证据，不要从“用户有多少 passkey”反推配额。

## 3. 异常分类：公开错误码只是证据的一部分

`android.security.KeyStoreException` 从 API 33 提供 `getNumericErrorCode()`、`isTransientFailure()`、`getRetryPolicy()`、`isSystemError()` 和 `requiresUserAuthentication()`。API 37 新增 `ERROR_TOO_MANY_KEYS`，其数值在 Android 17 AOSP 中为 18。业务代码应引用 SDK 常量，不要把 18 写进协议或埋点逻辑。

配额失败在两类 target SDK 下应这样处理：

- `targetSdkVersion >= 37`：`ERROR_TOO_MANY_KEYS` 是明确配额证据。
- `targetSdkVersion < 37`：Android 17 返回 `ERROR_INCORRECT_USAGE`，官方只保证异常 message 包含 key limit 信息。消息文本适合辅助诊断，不适合成为唯一业务分支；同一个公开错误码也可能表示参数组合错误。

JCA 层还可能把底层 `KeyStoreException` 包在 `ProviderException`、`InvalidKeyException` 或其他算法异常的 cause 链里。与此同时，`UserNotAuthenticatedException`、`KeyPermanentlyInvalidatedException` 和 `StrongBoxUnavailableException` 是需要单独识别的公开异常类型，不能假定所有认证与硬件能力问题都会表现为某个 `KeyStoreException` 数值。

建议分类为以下几组：

| 分类 | 可靠证据 | 处理 |
|---|---|---|
| 配额已确认 | Android 17、target 37、`ERROR_TOO_MANY_KEYS` | 停止创建，进入受控回收，不自动循环重试 |
| 配额疑似 | Android 17、旧 target、`ERROR_INCORRECT_USAGE`，且 message 明确提到 key limit | 上报疑似配额；本地盘点后再决定清理 |
| 需要用户认证 | `requiresUserAuthentication()` 或 `UserNotAuthenticatedException` | 走设备凭据/生物认证流程，不删除 key |
| key 永久失效 | `KeyPermanentlyInvalidatedException`、`ERROR_KEY_CORRUPTED` 等 | 按业务授权重建；旧 alias 可回收 |
| key 不存在 | `ERROR_KEY_DOES_NOT_EXIST` 或本地映射与 Keystore 不一致 | 修复 registry；需要时重新绑定 |
| 能力/策略不支持 | `StrongBoxUnavailableException`、`ERROR_UNIMPLEMENTED`、`ERROR_PERMISSION_DENIED` | 只有威胁模型允许时才换 TEE 或服务端验证 |
| 瞬时系统错误 | `isTransientFailure() == true` | 严格按 `getRetryPolicy()` 做有上限重试 |
| 永久参数错误 | `ERROR_INCORRECT_USAGE` 且没有配额证据 | 修正参数或版本组合，不靠重试恢复 |

下面的代码用于 Android 17 设备上的登录边界分类。它把明确配额、旧 target 的疑似配额、认证要求和瞬时错误分开，调用方仍需先处理 `UserNotAuthenticatedException` 等外层专用异常：

```kotlin
@RequiresApi(37)
fun classifyAndroid17KeystoreFailure(
    error: Throwable,
    targetSdk: Int,
): KeystoreFailure {
    val kse = generateSequence(error) { it.cause }
        .take(16)
        .filterIsInstance<KeyStoreException>()
        .firstOrNull()
        ?: return KeystoreFailure.Other(error.javaClass.name)

    val code = kse.numericErrorCode
    if (targetSdk >= 37 &&
        code == KeyStoreException.ERROR_TOO_MANY_KEYS
    ) {
        return KeystoreFailure.QuotaConfirmed
    }

    if (targetSdk < 37 &&
        code == KeyStoreException.ERROR_INCORRECT_USAGE &&
        kse.message.orEmpty().contains("key", ignoreCase = true) &&
        (kse.message.orEmpty().contains("limit", ignoreCase = true) ||
            kse.message.orEmpty().contains("too many", ignoreCase = true))
    ) {
        return KeystoreFailure.QuotaSuspected
    }

    if (kse.requiresUserAuthentication()) {
        return KeystoreFailure.UserAuthenticationRequired
    }

    if (kse.isTransientFailure) {
        return KeystoreFailure.Transient(kse.retryPolicy)
    }

    return KeystoreFailure.Permanent(
        code = code,
        systemError = kse.isSystemError,
    )
}
```

这段代码没有把 message 匹配当成“确认配额”，也只在 `isTransientFailure` 为真时读取 retry policy。`@RequiresApi(37)` 让 `ERROR_TOO_MANY_KEYS` 的 API 边界清晰；需要在旧系统共用分类器时，把 API 37 分支放进独立实现或版本隔离层。上报时保留外层异常类、cause 中的 `KeyStoreException`、公开错误码和清理状态，避免只记录一段 message。

## 4. 登录、支付路径的止损顺序

配额耗尽不应触发“清空 Keystore 后重试”。全量删除可能同时破坏登录、端到端加密、支付、数据库解锁与三方 SDK 状态。建议按下面顺序处置：

1. **停止新增**：对当前模块写入本地 quota gate，阻止同一启动周期继续生成 key。
2. **继续使用旧 key**：如果 active alias 仍存在且可用，优先完成读、验签或登录恢复。
3. **核对 registry**：确认 retired、orphan、测试前缀和已注销账号的候选集合。
4. **完成业务授权**：账号注销、设备解绑或凭据撤销需要服务端参与时，先完成服务端动作。
5. **小批量回收**：按归属和代际删除明确无引用 alias，每批记录成功与失败。
6. **重新计数**：确认释放出安全余量，再允许创建或轮换。
7. **新进程恢复**：启动关键路径只做轻量判断；大规模盘点放到 worker，避免把配额故障升级为 ANR。

可选功能遇到配额失败时可以关闭当前入口并展示可恢复提示。启动必需 key 若没有可用旧版本，应进入受控重新绑定或账号验证页面。不要退回明文 token、共享外部存储或无认证的软件 key；是否从 StrongBox 改用 TEE 也必须由既定安全策略决定。

## 5. alias 生命周期要有一份可执行契约

### 5.1 命名与 registry

alias 应由稳定业务域、非敏感 account slot、用途和 generation 构成，例如：

`auth.<account-slot>.device-sign.v3`

不要把账号 ID、手机号、订单号、token 或可猜测的简单哈希放进 alias。`account-slot` 可以是首次绑定时生成并持久化的随机标识。业务 registry 至少记录：

- alias、业务 owner、账号槽位、用途和 generation；
- 状态：`CREATING`、`ACTIVE`、`RETIRED`、`DELETING`、`DELETED`、`BROKEN`；
- 创建应用版本、创建时间、最近成功使用时间；
- 是否绑定生物认证、是否请求 StrongBox、当前安全级别；
- 替代 alias 与回滚截止点。

registry 不保存 key material，也不把“数据库里有记录”当成 key 存在证明。每次关键使用都要处理“registry 有、Keystore 无”和“Keystore 有、registry 无”两种不一致。

### 5.2 创建事务

创建不能只写成 `containsAlias()` 后立即 `generateKey()`。两个进程可能同时得到 false。更稳妥的状态流是：

`ABSENT -> CREATING -> ACTIVE -> RETIRED -> DELETING -> DELETED`

- 单一 key-manager 进程或跨进程文件锁负责状态转换。
- `CREATING` 记录应在生成前持久化，进程被杀后可恢复。
- 生成成功后读取 key characteristics，确认算法、安全级别和认证参数符合策略，再切到 `ACTIVE`。
- 同一用途只能有一个 active generation；轮换期可额外保留一个 last-known-good。
- 删除先切 `DELETING`，调用 `KeyStore.deleteEntry(alias)` 后复查，再写 `DELETED`。

文件锁只协调本应用进程，Keystore 的 UID 隔离仍由系统负责。若第三方 SDK 自己创建 key，宿主应要求它声明 alias 前缀、创建频率和删除 API；无法归属的 alias 很难安全回收。

### 5.3 生物认证与锁屏变化

生物认证 key 的失效取决于 `KeyGenParameterSpec`：认证有效期、允许的认证器组合、是否在新增生物特征后失效等参数都会改变行为。遇到 `UserNotAuthenticatedException` 时应先认证；遇到 `KeyPermanentlyInvalidatedException` 才进入重建。两者混在一起会造成不必要的删 key 和重新登录。

设备没有设置 LSKF 时，生成认证绑定 key 还可能映射为 `ERROR_KEYSTORE_UNINITIALIZED`。这个错误也可表示 `KeyStore.load()` 未调用，必须结合调用位置区分，不能直接提示“Keystore 损坏”。

## 6. 盘点与回收实现

全量枚举接近 50,000 个 alias 会产生 Binder、数据库和字符串分配成本。它不应运行在主线程、崩溃 handler、`Application.onCreate()` 首帧前，也不应在每次登录都执行。常态监控可以由低频 worker 采集总数和前缀桶，只有达到预警区间或命中创建失败时才进入更细盘点。

下面的代码用于后台生成脱敏盘点结果。它只保留总数和受控前缀分布，不把完整 alias 放进遥测：

```kotlin
fun collectAliasInventory(
    knownPrefixes: Set<String>,
): AliasInventory {
    val keyStore = KeyStore.getInstance("AndroidKeyStore").apply {
        load(null)
    }
    val byPrefix = knownPrefixes.associateWith { 0 }.toMutableMap()
    var total = 0

    val aliases = keyStore.aliases()
    while (aliases.hasMoreElements()) {
        val alias = aliases.nextElement()
        total += 1

        val prefix = knownPrefixes.firstOrNull { known ->
            alias.startsWith("$known.")
        }
        if (prefix != null) {
            byPrefix[prefix] = byPrefix.getValue(prefix) + 1
        }
    }

    return AliasInventory(
        total = total,
        knownPrefixCounts = byPrefix,
        unknownCount = total - byPrefix.values.sum(),
    )
}
```

该函数的 `total` 是应用 provider 可见条目数，用来做趋势和接近阈值的预警；它不是 keystore2 内部计数接口。`unknownCount` 只能提示仍有未登记 owner，不能据此批量删除。盘点任务还应记录耗时、枚举异常和触发原因，并设置运行频率与最长执行时间。

回收名单应来自业务事实，而非“很久没使用”一个条件。安全删除通常需要同时满足：registry 状态为 retired、替代 key 已成功使用、服务端不再接受旧公钥、回滚期结束、所有相关进程已经刷新选择。测试前缀可以按测试环境的明确契约清理；未知前缀应先归属。

## 7. 多进程、升级与回滚

target SDK 从 36 升到 37 时，已有 key 不会被系统自动清理。若某个 UID 已积累 50,000 个或更多条目，升级后下一次生成或导入会立即失败。发布前应针对历史设备做数量分桶，不能只在新安装设备上测试。

多进程应用可把 key 管理集中到 bound service，也可以用私有目录中的锁和持久状态协调。无论选哪种方式，都要满足：

- 只有 owner 组件可以创建、轮换和删除该前缀。
- 业务进程只请求“取得或创建某用途 key”，不自行拼接随机 alias。
- 删除与使用有租约或代际保护，避免远程进程仍持有旧 alias 时被清理。
- 配额失败写入共享 gate，其他进程读到后停止创建风暴。
- 回滚应用版本时，新旧版本都能理解 registry schema，或明确保留兼容迁移器。

卸载应用通常会清理对应 UID 的 Keystore 数据，但“让用户重装/清数据”不应成为线上恢复设计。它会同时清除业务数据与认证状态，也无法修复 alias 持续泄漏的代码。

## 8. 线上证据包

建议记录这些字段：

| 字段 | 说明 |
|---|---|
| `scene`、`api` | 登录恢复、设备绑定、支付签名；失败发生在 generate/import/use/delete 哪一步 |
| `app_version`、`target_sdk`、`android_api` | 确认 Android 17 与 API 37 错误码边界 |
| `outer_exception`、`keystore_error_code` | 同时保留 JCA 外层异常和底层公开码 |
| `is_transient`、`retry_policy`、`is_system_error` | 约束重试与系统故障归因 |
| `requires_user_auth` | 避免把设备未解锁误判为配额 |
| `alias_owner`、`alias_prefix`、`generation` | 定位增长来源，不上传完整 alias |
| `alias_count_bucket`、`unknown_prefix_count` | 观察 UID 下的数量趋势与未登记 owner |
| `registry_state`、`cleanup_batch_result` | 确认恢复卡在哪个状态 |
| `security_level`、`auth_policy` | 区分 TEE、StrongBox 与用户认证策略 |
| `process_name`、`lock_owner` | 发现多进程创建竞争 |
| `last_exit_reason` | 启动崩溃后与 `ApplicationExitInfo` 对照 |

错误消息可能包含 alias 或内部信息，上报前要清洗。账号槽位应使用不可逆且不可跨用户关联的标识；简单 SHA-256 账号 ID 仍可能被字典反查。密钥、token、证书私密内容、完整 alias 都不进入日志。

如果配额错误导致启动崩溃，下次启动可读取 Android 11+ 的 `ApplicationExitInfo`，再与本地保存的最近一次 key 操作关联。退出记录只能说明进程因 crash、ANR 等原因结束，不能单独证明 Keystore 是根因；业务异常时间、进程名和本次启动 session 才能完成归因。详细用法见 26.9。

## 9. 灰度与压测

### 9.1 测试组合

| 用例 | 构造方式 | 预期 |
|---|---|---|
| 目标版本升级 | target 36 包积累测试 alias，再覆盖安装 target 37 包 | 旧 key 仍可用；新增 key 按 API 37 规则分类 |
| 恰好达到阈值 | 在测试设备建立 50,000 个 APP key | 下一次生成/导入失败；同名覆盖也按源码门禁验证 |
| 旧 target 超限 | Android 17 上使用 target 36 测试包达到对应阈值 | 数值码为 `ERROR_INCORRECT_USAGE`，message 只作疑似证据 |
| 删除后恢复 | 删除一批已知测试 alias，再创建新 key | 释放额度后恢复，业务 key 未被误删 |
| 多进程竞争 | 主进程、支付进程、push 进程同时请求相同用途 key | 只有一个 active generation，没有创建风暴 |
| 进程中断 | 在 `CREATING`、`DELETING` 状态杀进程 | 重启能按 registry 恢复，不生成随机新 alias |
| 生物认证变化 | 锁屏、生物 enrollment、认证超时分别测试 | 认证要求与永久失效分类不同 |
| StrongBox 不可用 | 在不支持或资源不足设备请求 StrongBox | 按安全策略处理，不误报为配额 |
| 大规模枚举 | 建立大量测试 alias 后运行 inventory worker | 不阻塞主线程，耗时与失败被记录 |
| 启动路径失败 | 注入 quota 异常并模拟进程 crash | 下次启动不继续创建，并能关联退出记录 |

50,000 与 200,000 是系统拒绝线，不是业务告警线。业务应根据日增长速度、清理能力和最坏轮换量，在明显更低的位置设置预警。测试脚本必须使用独立设备或可重置的测试 user、固定测试前缀和硬性生成上限；任务结束与中断恢复都要清理测试 key。

### 9.2 发布门禁

target 37 放量前至少确认：

- 所有 `KeyGenerator.generateKey()`、`KeyPairGenerator.generateKeyPair()`、导入与 wrapped import 入口都有 owner。
- alias 不含无界时间戳、请求 ID、订单 ID 或 run ID。
- 每个 owner 都有删除协议、最大 active generation 和测试清理入口。
- quota confirmed、quota suspected、auth required、permanent invalidation、transient system error 能分开统计。
- 配额 gate 不会退回明文存储或无限重试。
- 历史设备按 alias count bucket 观察，接近业务预警线的用户有受控清理方案。
- 启动首帧前不会执行全量 alias 枚举或批量删除。

## 10. 与相邻章节的边界

8.9 关注应用进程、keystore2、KeyMint HAL、TEE/StrongBox 之间的延迟、operation slot 和线程调度；这里关注持久 key entry 数量与 alias 生命周期。operation 并发上限和每 UID key 数量是两套资源约束，报告中应分别统计。

20.7 统一讨论异常恢复、crash loop 与 SafeMode，26.9 讨论 `ApplicationExitInfo`。这里提供 Keystore 故障分类和恢复状态；进程退出记录只能作为时间与结果证据。

## 小结

Android 17 的 50,000/200,000 配额把 alias 泄漏从长期隐患变成明确的创建门禁。稳定治理要抓住四个事实：配额按 APP UID 统计；target 37 非系统应用使用 50,000 上限；已有 key 的正常使用不因配额直接失效；达到上限后，同名重建也可能在 rebind 前被拒绝。

因此，恢复动作应是停止新增、保留可用旧 key、按 owner 和代际清理、确认释放额度，再恢复创建。`ERROR_TOO_MANY_KEYS` 是 target 37 的明确证据；旧 target 的 `ERROR_INCORRECT_USAGE` 只能结合 Android 17 环境和 message 标成疑似。把这个边界写进 key-manager、遥测和发布测试，登录与支付链路才不会在 target SDK 升级后集中失败。

## 参考资料

- [Android 17 behavior changes - Per-app keystore limits](https://developer.android.com/about/versions/17/behavior-changes-all#per-app-keystore-limits)
- [`KeyStoreException`](https://developer.android.com/reference/android/security/KeyStoreException)
- [API 36 -> 37 `KeyStoreException` diff](https://developer.android.com/sdk/api_diff/37/changes/android.security.KeyStoreException)
- [Android Keystore system](https://developer.android.com/privacy-and-security/keystore)
- [AOSP `android-17.0.0_r1`：keystore2 quota check](https://android.googlesource.com/platform/system/security/+/android-17.0.0_r1/keystore2/src/security_level.rs)
- [AOSP `android-17.0.0_r1`：keystore2 alias count](https://android.googlesource.com/platform/system/security/+/android-17.0.0_r1/keystore2/src/utils.rs)
- [AOSP `android-17.0.0_r1`：public error mapping](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/keystore/java/android/security/KeyStoreException.java)
- [AOSP：Keystore architecture](https://source.android.com/docs/security/features/keystore)
- [AOSP：Keystore/KeyMint implementer reference](https://source.android.com/docs/security/features/keystore/implementer-ref)
