---
title: "Android 应用分发与内容共享：PackageInstaller、AAB 和 Sharesheet 的系统边界"
chapter: "1.27"
section: "1.27"
status: finalized
applicable_versions: "Android 5.0 (API 21) - Android 17 (API 37)"
tags: [packageinstaller, shortcutservice, chooseractivity, app-bundle, distribution]
related_chapters: ["1.9", "8.11", "24.18"]
created_by: "task2a-knowledge-gap"
created_date: "2026-06-25"
gap_source: "素材驱动"
drafted_date: "2026-06-25"
last_verified: "2026-08-09"
last_verified_against: "AOSP android-17.0.0_r1 / API 37"
confidence: high
sources:
  - type: aosp
    path: "frameworks/base/core/java/android/content/pm/PackageInstaller.java"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/pm/PackageInstallerService.java"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/pm/PackageInstallerSession.java"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/pm/PackageSessionVerifier.java"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/pm/InstallingSession.java"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/pm/verify/developer/DeveloperVerifierController.java"
  - type: aosp
    path: "frameworks/base/core/java/com/android/internal/app/ChooserActivity.java"
  - type: aosp
    path: "frameworks/base/core/java/com/android/internal/app/ResolverListController.java"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/pm/ShortcutService.java"
  - type: official
    path: "https://developer.android.com/reference/android/content/pm/PackageInstaller"
  - type: official
    path: "https://developer.android.com/guide/app-bundle/app-bundle-format"
  - type: official
    path: "https://developer.android.com/training/sharing/send"
  - type: official
    path: "https://developer.android.com/training/sharing/direct-share-targets"
  - type: official
    path: "https://developer.android.com/sdk/api_diff/37/changes/android.content.pm.PackageInstaller"
  - type: official
    path: "https://source.android.com/docs/compatibility/17/android-17-cdd#4_application_packaging_compatibility"
---

# 1.27 Android 应用分发与内容共享：PackageInstaller、AAB 和 Sharesheet 的系统边界

应用安装和应用间分享都会用到 `PackageManager`、`Intent` 等平台能力，但两者没有共同的“分发流水线”。安装处理的是可执行软件包及其身份；分享处理的是一次跨应用的数据传递。先把这条边界划清，后面的性能与安全问题才不会相互混淆。

| 场景 | 平台接收的输入 | 主要系统组件 | 平台负责什么 |
| --- | --- | --- | --- |
| 应用安装或更新 | 一个单体 APK，或一组 base/split APK | `PackageInstallerService`、`PackageInstallerSession`、Package Manager | 暂存、解析、签名和策略校验、用户确认、安装提交 |
| App Bundle 发布 | `.aab` | 应用商店或 `bundletool`，不由设备端 Package Manager 直接处理 | 生成适合目标设备的 APK 集合 |
| 内容分享 | `ACTION_SEND` / `ACTION_SEND_MULTIPLE` Intent、文本或 `content://` URI | `ChooserActivity`、Intent Resolver、`ShortcutService` | 匹配、排序并启动接收目标，授予必要的临时 URI 权限 |

## 一、从商店到设备：责任在什么地方切换

一条常见的商店分发路径可以写成：

```text
开发者上传 AAB 或 APK
        ↓
商店生成并选择 APK 集合，负责下载、重试和网络策略
        ↓
安装器创建 PackageInstaller.Session，写入 base/split APK
        ↓
Android 封存 session，完成验证、确认和安装
        ↓
PackageInstaller 通过 IntentSender 返回最终状态
```

这里有三个经常被混为一谈的边界。

### 1. AAB 不能直接安装到 Android 设备

Android App Bundle 是发布格式。Google Play 可以根据 ABI、屏幕密度、语言和动态功能模块，从 AAB 生成目标设备需要的 APK。其他分发系统也可以通过 `bundletool` 生成 APK set。设备端最终安装的仍然是 APK：一个 base APK，加上零个或多个 split APK。

`PackageInstaller` 不解析 `.aab`，也不替应用商店决定应该下载哪些配置 split。若安装器漏掉必需的 split，或把不同版本、不同签名的 APK 混在同一个 session 中，平台会拒绝安装。

Android 17 的 `PackageInstaller` API 文档和 `PackageInstallerSession.validateApkInstallLocked()` 都把同一组 APK 的一致性作为设备端安装前置条件：

- package name、version code 和签名证书一致；
- split name 唯一；
- 完整安装包含一个 base APK；
- 部分更新必须与设备上已有包保持一致。

`validateApkInstallLocked()` 会收集新增 APK，检查重复 split，通过 `assertApkConsistentLocked()` 核对包名、版本和签名，并将文件规范化为平台使用的名称。AAB 到 split APK 的选择可以发生在商店或 `bundletool`，但 base/split 集合一旦交给设备，设备端只接受满足 APK 一致性规则的结果。

### 2. 下载器和 PackageInstaller 是两个模块

CDN 选择、HTTP 并发、断点续传和网络切换恢复属于商店下载器。`PackageInstaller.Session.openWrite(name, offset, length)` 支持从指定文件偏移继续写入 session，但它不发起网络请求，也不知道 CDN 的存在。

`length` 已知时应传入真实长度，系统可以提前分配暂存空间。`offset` 适合恢复已经写入 session 的部分；安装器仍要自行保证远端对象没有变化，并校验下载结果。

因此，“弱网下载失败”要在下载层定位，“APK 已写完但 commit 失败”才进入 PackageInstaller 和 Package Manager 的诊断范围。

### 3. 普通安装器不因此获得静默安装能力

任何应用都可以使用 session API 创建安装请求，但最终能否无交互安装取决于调用者身份、权限、设备策略和用户授权。面向普通用户的外部来源安装通常需要：

- 声明 `REQUEST_INSTALL_PACKAGES`；
- 用户允许该来源请求安装应用；
- 在 `STATUS_PENDING_USER_ACTION` 返回后，由可见界面或通知引导用户完成系统确认。

设备所有者、关联的资料所有者以及持有系统级安装权限的组件有不同规则。应用不能把“能够创建 session”理解为“能够静默提交”。

## 二、PackageInstaller session 的执行过程

### 1. 安装器侧：创建、写入、关闭、提交

下面的示例只展示 session 的文件写入方式。调用方仍需满足安装权限和用户确认要求；`apkParts` 中应放入商店已经选好的 base/split APK。

```kotlin
data class ApkPart(
    val sessionName: String,
    val length: Long,
    val openInput: () -> InputStream,
)

fun stageApks(
    context: Context,
    packageName: String,
    apkParts: List<ApkPart>,
): Int {
    val installer = context.packageManager.packageInstaller
    val params = PackageInstaller.SessionParams(
        PackageInstaller.SessionParams.MODE_FULL_INSTALL,
    ).apply {
        setAppPackageName(packageName)
        if (Build.VERSION.SDK_INT >= 33) {
            setPackageSource(PackageInstaller.PACKAGE_SOURCE_STORE)
        }
    }

    val sessionId = installer.createSession(params)
    installer.openSession(sessionId).use { session ->
        apkParts.forEach { part ->
            part.openInput().use { input ->
                session.openWrite(part.sessionName, 0, part.length).use { output ->
                    input.copyTo(output)
                    session.fsync(output)
                }
            }
        }

        val callback = Intent(context, InstallResultReceiver::class.java)
            .setAction("com.example.store.INSTALL_RESULT")
        val statusReceiver = PendingIntent.getBroadcast(
            context,
            sessionId,
            callback,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_MUTABLE,
        )
        session.commit(statusReceiver.intentSender)
    }
    return sessionId
}
```

每个 `openWrite()` 返回的流必须在 `commit()` 前关闭。对 target API 35 及以上的安装器，传给 `commit()` 的 status receiver 必须来自可变 `PendingIntent`，因为系统要写入结果 extras。这个 `PendingIntent` 应使用显式组件或限定包名，并采用不会与其他安装混淆的 request code。

`commit()` 之后，session 被封存，调用者不能继续改写内容。回调可能先返回 `STATUS_PENDING_USER_ACTION`，也可能直接给出成功或失败。收到待确认状态时，应读取 `Intent.EXTRA_INTENT`；只有用户正在操作安装界面时才直接启动，否则应通过通知把用户带回交互流程。

### 2. system_server 侧：封存先于安装

以 `android-17.0.0_r1` 为锚点，主要调用关系如下：

```text
PackageInstallerService.createSessionInternal()
    └─ 创建并持久化 PackageInstallerSession

PackageInstallerSession.commit()
    ├─ 检查写入流已经关闭
    ├─ markAsSealed()
    └─ dispatchSessionSealed()
         └─ streamValidateAndCommit()
              ├─ 准备 DataLoader（如果使用）
              ├─ validateApkInstallLocked()
              └─ 投递 MSG_INSTALL
                   └─ handleInstall()
                        ├─ 必要时请求用户确认
                        ├─ parseApk()
                        ├─ Android 17 开发者验证（启用时）
                        ├─ 原生库提取
                        ├─ PackageSessionVerifier.verify()
                        └─ InstallingSession.installStage()
```

`commit()` 的返回不能代表安装完成。它只发起异步处理，最终结果由 `IntentSender` 送回。把 `commit()` 放到主线程并不会让系统安装工作在应用主线程执行；安装器自己的下载、哈希计算或 APK 复制如果阻塞主线程，仍会造成该安装器 ANR。

### 3. 完整安装、继承安装和多包安装

`SessionParams.MODE_FULL_INSTALL` 提供一个完整 APK 集合。`MODE_INHERIT_EXISTING` 用于保留已有 APK，并增加、替换或移除部分 split；它要求目标包已经存在，新增内容也必须与现有安装一致。

Android 10（API 29）起，父 session 可以通过 `setMultiPackage()` 关联多个子 session。提交父 session 时，子 session 作为一个原子多包请求处理。它解决的是多个包需要共同成功或失败的问题，不等于并行下载，也不会取消每个子包各自的签名、策略和兼容性检查。

staged session 主要服务于需要跨重启验证和应用的系统级更新场景。普通应用商店不应为了“更可靠”而把所有安装都当成 staged install。

### 4. Streaming、Incremental 与普通 openWrite

`PackageInstallerSession` 确有 Streaming 和 Incremental DataLoader 分支，但它们有专门的 DataLoader 协议、权限和文件系统协作。普通安装器使用 `openWrite()` 顺序写入 APK，不会自动变成“边下边运行”的增量安装。

分析安装性能时应先确认 session 参数和 DataLoader 类型，再讨论数据是否完整暂存。把所有安装都归为流式解析，会误判磁盘占用和首次启动行为。

## 三、Android 17 的验证边界

### 1. APK 签名验证解决的是软件包身份连续性

APK 签名用于确认 APK 内容未在签名后被修改，并约束同一包名的更新关系。Android 17 CDD 要求设备支持 APK Signature Scheme v3.2、v3.1、v3、v2 和 JAR signing；这不表示每个 APK 都同时带有所有签名方案。

在 `PackageInstallerSession` 中，新增 APK 会经过 `ApkSignatureVerifier`，base/split 的 `SigningDetails` 必须一致。更新已有应用时，Package Manager 还会检查新旧签名或有效的签名轮换关系。签名不匹配属于安装冲突或无效包，不能通过关闭某个“性能校验”来绕过。

### 2. Android 17 开发者验证不是 APK 签名的替代品

开发者验证的结果字段在 `PackageInstaller` 文档中标为 Android 16.1（API 36.1）加入；Android 17 / API 37 继续提供，并把 installer target SDK 大于 API 36 作为一条新的回调行为边界。相关接口和结果信息包括：

- `getDeveloperVerificationServiceProvider()`；
- `EXTRA_DEVELOPER_VERIFICATION_FAILURE_REASON`；
- 开发者被阻止、网络不可用和未知错误等原因码；
- 验证扩展参数及响应。

APK 签名回答“这个更新是否延续了允许的签名身份”，开发者验证回答“当前安装策略下，开发者和包名是否满足验证要求”。Android 17 源码中的 `PackageInstallerSession.handleInstall()` 会在完成用户确认和 APK 解析后，在功能启用时启动 `DeveloperVerifierController`，随后才继续其余 package session 验证。

安装器必须以 `EXTRA_STATUS` 为主状态，并在失败时读取开发者验证原因。网络不可用不应统一显示成“APK 损坏”；设备策略是否允许用户继续，由系统确认界面和验证策略决定。

### 3. 安装失败不能只归因于签名

常见返回状态应按类别处理：

| 状态 | 常见含义 | 安装器应提供的下一步 |
| --- | --- | --- |
| `STATUS_PENDING_USER_ACTION` | 需要用户确认、授权或查看系统说明 | 在合适的前台时机启动系统提供的 Intent |
| `STATUS_FAILURE_INVALID` | APK 损坏、格式错误、split 不一致或签名无效 | 重新核对 APK 集合和下载校验值 |
| `STATUS_FAILURE_CONFLICT` | 与已有包、签名、权限或共享库关系冲突 | 显示冲突对象，不要盲目重试 |
| `STATUS_FAILURE_INCOMPATIBLE` | SDK、ABI 或硬件能力不兼容 | 回到商店侧重新选择适配 APK |
| `STATUS_FAILURE_STORAGE` | 暂存或安装空间不足、存储不可用 | 引导释放空间，再重建或重试 session |
| `STATUS_FAILURE_BLOCKED` / `STATUS_FAILURE_ABORTED` | 策略、验证器或用户拒绝阻止安装 | 结合 extras 和系统说明展示原因 |

只记录一条“安装失败”会丢掉最有价值的诊断信息。至少要记录 session ID、包版本、APK 集合摘要、`EXTRA_STATUS`、`EXTRA_STATUS_MESSAGE`、失败阶段以及是否经过用户确认；日志中不要保存签名私钥、授权令牌或用户文件内容。

## 四、安装性能应该怎样测

没有脱离设备、包结构和安装模式的固定优化百分比。建议把时间轴分成以下阶段：

1. **商店选择与下载**：服务端选择 APK 集合、首字节、下载完成、重试次数；
2. **session 写入**：`createSession()` 到末尾一个输出流关闭，分别统计下载等待和本地写入；
3. **平台处理**：调用 `commit()` 到首次结果、用户确认耗时、确认后到最终结果；
4. **首次可用**：安装成功到首次启动，另行观察 dex、资源和应用初始化成本。

以下现象可以按证据快速分流：

| 现象 | 先检查什么 | 不应直接推断什么 |
| --- | --- | --- |
| 写入 session 很慢 | 输入流吞吐、存储 I/O、是否在重复计算摘要 | `PackageInstallerService` 发生了 GC 风暴 |
| `commit()` 后长时间等待 | 是否待用户确认、开发者验证、原生库提取、package verifier | 存在“后台安装低优先级队列” |
| 大包空间不足 | 下载文件、session 暂存与最终安装是否同时占空间，`length` 是否准确 | 平台的空间预估一定错误 |
| split 安装失败 | base/split 的版本、签名、名称、设备配置和依赖 | 增量更新机制失败 |
| 安装器界面 ANR | 下载、复制、哈希和回调处理是否占用主线程 | 系统安装逻辑运行在应用 UI 线程 |

如果需要比较单体 APK 与 split APK，应固定设备、包版本、数据状态和安装方式，分别报告下载字节数、session 写入字节数、提交耗时和最终占用。AAB 减少多少下载量取决于资源、ABI、语言和模块拆分，不能给出适用于所有应用的区间。

## 五、内容分享走的是另一条路径

### 1. ACTION_SEND 如何到达 ChooserActivity

发送方构造 `ACTION_SEND` 或 `ACTION_SEND_MULTIPLE` Intent，并通过 `Intent.createChooser()` 请求 Android Sharesheet。普通应用目标由 Resolver 通过 Package Manager 的 `queryIntentActivitiesAsUser()` 查询，再按权限、用户资料、IntentFilter 和系统策略过滤。

这里的匹配遵循 Android IntentFilter 规则，不会通过正则表达式扫描。已安装应用数量会影响候选规模，但候选查询、排序和界面填充不能简单归结为“在 UI 线程线性遍历全部应用”。Android 17 的实现分布在 `ResolverListController`、`ResolverActivity` 和 `ChooserActivity` 中。

发送文本的最小写法如下：

```kotlin
fun shareText(context: Context, text: String) {
    val send = Intent(Intent.ACTION_SEND).apply {
        type = "text/plain"
        putExtra(Intent.EXTRA_TEXT, text)
    }
    context.startActivity(Intent.createChooser(send, null))
}
```

明确的 `text/plain` 能让系统排除不支持文本的目标。不要使用 `*/*` 扩大候选范围，除非无法给出更准确的 MIME 类型。

### 2. 文件分享依赖 content URI 和临时授权

跨应用分享文件时应提供 `content://` URI，例如由 `FileProvider` 生成，并同时携带临时读取权限。接收方可能从 `EXTRA_STREAM` 或 `ClipData` 读取 URI，因此发送方应保证两处信息一致。

```kotlin
fun shareDocument(context: Context, uri: Uri, mimeType: String) {
    val send = Intent(Intent.ACTION_SEND).apply {
        type = mimeType
        putExtra(Intent.EXTRA_STREAM, uri)
        clipData = ClipData.newUri(context.contentResolver, "shared document", uri)
        addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
    }
    context.startActivity(Intent.createChooser(send, null))
}
```

权限只覆盖这次 Intent 授予的 URI。不要传递应用私有文件路径或 `file://` URI，也不要为了分享一个文件而开放整个目录。接收方读取大文件时，`ContentProvider.openFile()` 应避免在主线程执行昂贵的生成工作。

### 3. Direct Share 来自 Sharing Shortcuts

Direct Share 行展示的是联系人、会话等具体目标。应用需要在 shortcuts XML 中声明 `<share-target>`，再发布与类别匹配的动态快捷方式。Android 17 的 `ChooserActivity.queryDirectShareTargets()` 优先使用可用的 `AppPredictor`，否则调用 `ShortcutManager.getShareTargets()`；`ShortcutService` 根据 IntentFilter 匹配已发布的分享快捷方式。

这条路径不存在 `queryShortcuts()` 的“增量查询开关”，也没有 `ShortcutInfo` 按使用频率自动预加载的公开契约。应用负责维护有效快捷方式、报告使用情况并删除过期对象，系统负责匹配和排序。通信应用尤其要避免发布长期不活跃或已失效的会话。

### 4. Sharesheet 性能由发送方能控制什么

应用能直接改进以下几处：

- 使用准确的 MIME 类型和必要的 extras；
- 缩略图保持小而可快速读取，不把原图当预览；
- `ContentProvider` 快速返回文件描述符，耗时准备提前完成；
- Direct Share 快捷方式保持少而新鲜，ID 不复用于不同对象；
- 使用系统 Sharesheet，不先查询所有接收应用再自建一套列表；
- 分享完成统计与安装下载指标分开记录。

如果 Sharesheet 首屏慢，应同时采集发送 Intent 的内容、候选应用数量、URI provider 响应、Direct Share 查询和系统 trace。没有这些证据时，缓存所有候选应用容易产生权限、资料隔离和应用变更后的陈旧数据问题。

## 六、源码核对入口

基于 `android-17.0.0_r1` 排查时，可以从以下位置开始：

| 问题 | 文件与关键入口 |
| --- | --- |
| session 创建、持久化和配额 | `PackageInstallerService.createSessionInternal()` |
| 写入、封存和提交 | `PackageInstaller.Session.openWrite()`、`PackageInstallerSession.commit()` |
| base/split 一致性与签名 | `PackageInstallerSession.validateApkInstallLocked()` |
| 用户确认和 Android 17 开发者验证 | `PackageInstallerSession.handleInstall()`、`DeveloperVerifierController` |
| package verifier 与安装提交 | `PackageSessionVerifier.verify()`、`InstallingSession.installStage()` |
| 普通分享目标查询 | `ResolverListController.getResolversForIntentAsUser()` |
| Direct Share 查询 | `ChooserActivity.queryDirectShareTargets()`、`ShortcutService.getShareTargets()` |

调试时先标明问题属于下载、session 写入、平台验证、安装提交、Intent 解析还是 URI 读取。按这些类别记录，才能得到可复现的结论。
