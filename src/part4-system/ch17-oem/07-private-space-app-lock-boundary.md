---
title: "Private Space 与应用锁的兼容性边界"
chapter: "17.7"
status: finalized
drafted_date: "2026-05-25"
applicable_versions: "Android 15 (API 35) - Android 17 (API 37) QPR2；手持设备通用逐应用锁无公开 SDK，AAOS App Lock 另行说明"
last_verified: "2026-08-04"
last_verified_against: "AOSP android-17.0.0_r1 framework sources; Android Developers Android 15/17 documentation; AOSP Android 16 QPR2 release notes; AAOS App Lock documentation"
confidence: medium-high
reviewed_date: "2026-08-04"
reviewed_by: "hermes-aiw-review-finalize-apply"
task6_state: reviewed
task9_state: reviewed
pipeline_stage: finalized
last_review_finalize_at: "2026-08-04T12:08:06+08:00"
last_review_finalize_run_id: "20260804-120806-549a8bbc"
sources:
  - type: official
    path: "https://source.android.com/docs/security/features/private-space"
  - type: official
    path: "https://source.android.com/docs/whatsnew/android-17-release"
  - type: official
    path: "https://developer.android.com/about/versions/17/summary"
  - type: official
    path: "https://source.android.com/docs/whatsnew/android-16-release"
  - type: official
    path: "https://developer.android.com/about/versions/15/features"
  - type: official
    path: "https://developer.android.com/about/versions/15/behavior-changes-all"
  - type: official
    path: "https://developer.android.com/reference/android/content/pm/LauncherApps"
  - type: official
    path: "https://developer.android.com/reference/android/content/pm/LauncherUserInfo"
  - type: official
    path: "https://developer.android.com/reference/android/os/UserManager"
  - type: official
    path: "https://developer.android.com/identity/sign-in/biometric-auth"
  - type: official
    path: "https://source.android.com/docs/automotive/unbundled_apps/app-lock"
  - type: blog
    path: "intake/daily-info/2026-05-25.md"
tags: [private-space, app-lock, user-profile, launcher, notification, media-access]
related_chapters: ["1.3", "1.9", "12.1", "17.1", "20.7", "24.13", "26.3"]
created_by: "task2a-knowledge-gap"
created_date: "2026-05-25"
gap_source: "官方文档/每日信息/素材驱动"
---

# 17.7 Private Space 与应用锁的兼容性边界

## 17.7.1 先分清四类“锁”

用户说“这个 App 被锁了”，背后的系统机制可能完全不同。排查前应先确认安全边界：

| 机制 | 保护对象 | 锁定后的系统行为 | 普通 App 能否识别 |
| --- | --- | --- | --- |
| AOSP Private Space | 一个独立 private profile 及其中的数据 | profile 停止，应用入口、最近任务和通知被隐藏 | 不能枚举主空间之外的 hidden profile |
| App 自有鉴权 | App 内的敏感页面或操作 | 由 App 决定页面遮挡、会话超时和重新认证 | 可以，因为策略由 App 自己实现 |
| OEM 手持设备应用锁 | 厂商选定的 App 或入口 | 可能在启动、最近任务、通知或设置页前插入认证 | 没有跨厂商公开 API |
| Android Automotive App Lock | 车载次用户中的敏感 App | 由平台签名的特权 App 管理锁定清单和认证入口 | 仅适用于 AAOS 集成，不是手持设备 SDK |

Android 17 / API 37 的手持设备 AOSP 没有通用的逐应用锁公开 API。`android-17.0.0_r1` 的 `PackageManager`、`LauncherApps`、通知和设备管理公开接口中也没有 `AppLockManager` 一类能力。Android 17 的 Advanced Protection Mode 面向整机安全策略，同样不负责给某个 App 增加启动口令。

Android Automotive 的 App Lock 容易造成名称误读。它是 Android 14 起可选的非捆绑、平台签名特权应用，服务于车载次用户；它和 private profile 的锁定状态相互独立。手持设备应用不能据此声明 Android 17 提供了通用 App Lock。

因此，业务代码不能把 `Private Space locked`、`OEM authentication canceled` 和 `App session expired` 归为同一种状态。三者的生命周期、权限与恢复路径都不同。

## 17.7.2 Private Space 的系统模型

Private Space 从 Android 15 / API 35 引入，建立在 Android 多用户框架上，profile 类型是 `android.os.usertype.profile.PRIVATE`。同一个包安装到主用户和 private profile 后，会形成两份用户域实例：

- Linux UID 不同；Android UID 包含 userId 与 appId 两部分。
- `/data/user/<userId>/<package>` 等应用数据目录不同。
- 账号、数据库、偏好、缓存和下载内容不自动复制。
- 每个用户分别记录安装状态，因此可以只在一边安装；同包名的代码版本由设备级 PackageManager 管理，更新后各已安装用户实例通常共用新版本。

所以，“主空间已经登录”不代表 Private Space 中也有登录态；服务端按账号与包名统计时，也可能把两个运行环境合在同一个指标桶里。

Private Space 的主要状态如下：

| 状态 | profile 生命周期 | Launcher | 通知与最近任务 | 跨空间选择 |
| --- | --- | --- | --- | --- |
| 已解锁 | user started | 展示容器和应用 | 可以显示 | 系统 Sharesheet、Photo Picker 可按策略提供内容 |
| 已锁定、入口可见 | user stopped | 只展示 Private Space 解锁入口 | 私密应用及通知隐藏 | 私密应用和内容不可用 |
| 已锁定、入口隐藏 | user stopped | 连 Private Space 入口也隐藏 | 私密应用及通知隐藏 | 私密应用和内容不可用 |

锁定操作会停止 private profile。运行在该 profile 中的 Activity、Service、Job 和进程随用户停止而退出运行状态；这比在 Activity 前盖一个认证页的影响范围大得多。解锁会启动 profile，但 App 仍要按一次正常的进程创建和状态恢复来处理，不能依赖锁定前的内存对象。

设备只能创建一个 Private Space，它属于主用户。它可以和工作资料、clone profile 共存。Settings 在锁定时也要遵守隐藏要求，不能通过应用列表侧漏私密空间中安装了什么。

## 17.7.3 普通 App 所处的边界

普通业务 App 只应处理“自己当前运行在哪个 Android 用户中”。它无法通过公开、可移植的方式枚举主用户的 Private Space，也不应把品牌、userId 范围或进程 UID 当作 Private Space 探针。

一个包在 Private Space 内运行时，它看到的是自己的 Context、文件目录、权限和账号状态。开发者需要保证这些常规路径成立：

- 进程冷启动后可以从持久状态恢复页面。
- deep link、通知、分享和文件选择都经过同一套路由校验。
- 账号缺失、数据库为空或文件不可读时给出可恢复的 UI。
- 用户锁定空间造成任务中断时，重启后可以重试或明确终止。

`UserManager.isQuietModeEnabled(UserHandle)` 是公开方法，但调用者先要拥有目标 `UserHandle`。普通 App 拿不到 hidden private profile 的句柄，因此这个方法不是通用 Private Space 检测接口。`requestQuietModeEnabled()` 的调用者还必须是前台默认 Launcher，或持有 `MANAGE_USERS` / `MODIFY_QUIET_MODE`；业务 App 不应调用它控制 Private Space。

这种限制也是隐私设计的一部分。若任意 App 都能判断设备是否创建了 Private Space、其中是否正在运行或安装了哪些包，Private Space 的隐藏语义就会被削弱。

## 17.7.4 Launcher 与系统组件如何接入

默认 Launcher 的职责不同。Android 17 源码给 hidden profile 访问设置了两条权限路径：

1. 声明 normal 级别的 `android.permission.ACCESS_HIDDEN_PROFILES`，同时持有 `RoleManager.ROLE_HOME`。
2. 平台系统应用持有 signature/privileged 级别的 `ACCESS_HIDDEN_PROFILES_FULL`，无需 HOME 角色。

只声明 normal 权限并不能让普通 App 枚举 Private Space。`LauncherApps#getProfiles()` 的 Android 17 源码注释明确写出了 HOME 角色条件；当调用进程本身位于 managed/private profile 时，该方法也只返回当前 profile。

Launcher 可以用下列 API 形成状态模型：

- `LauncherApps.getProfiles()`：取得调用者有权访问的 profile。
- `LauncherApps.getLauncherUserInfo(user)`：取得 `LauncherUserInfo`。
- `LauncherUserInfo.getUserType()`：与 `UserManager.USER_TYPE_PROFILE_PRIVATE` 比较。
- `UserManager.isQuietModeEnabled(user)`：判断 profile 是否处于 quiet mode。
- `LauncherUserInfo.getUserConfig()`：读取额外 Launcher 配置。
- `LauncherUserInfo.PRIVATE_SPACE_ENTRYPOINT_HIDDEN`：API 36 起表示锁定时是否隐藏入口。

下面的示例只适用于默认 Launcher 或具备相应特权的系统组件，目的在于把 profile 生命周期与入口展示拆成两个布尔量：

```kotlin
data class PrivateProfileUiState(
    val user: UserHandle,
    val locked: Boolean,
    val hideEntrypointWhenLocked: Boolean,
)

fun readPrivateProfileStates(
    launcherApps: LauncherApps,
    userManager: UserManager,
): List<PrivateProfileUiState> {
    return launcherApps.profiles.mapNotNull { user ->
        val info = launcherApps.getLauncherUserInfo(user) ?: return@mapNotNull null
        if (info.userType != UserManager.USER_TYPE_PROFILE_PRIVATE) {
            return@mapNotNull null
        }

        val hidden = if (Build.VERSION.SDK_INT >= 36) {
            info.userConfig.getBoolean(
                LauncherUserInfo.PRIVATE_SPACE_ENTRYPOINT_HIDDEN,
                false,
            )
        } else {
            false
        }

        PrivateProfileUiState(
            user = user,
            locked = userManager.isQuietModeEnabled(user),
            hideEntrypointWhenLocked = hidden,
        )
    }
}
```

`locked` 决定 private profile 当前能否运行，`hideEntrypointWhenLocked` 决定锁定时 Launcher 是否仍展示解锁入口。将两者压成一个 `isHidden` 会丢失“已锁定但入口可见”的状态。

Launcher 还应监听 `Intent.ACTION_PROFILE_AVAILABLE` 与 `Intent.ACTION_PROFILE_UNAVAILABLE`，并从 `Intent.EXTRA_USER` 读取发生变化的 profile。广播表示 quiet mode 变化，收到广播后仍应重新查询当前状态，避免依赖过期缓存。`ACTION_MANAGED_PROFILE_AVAILABLE` 一类名称限定 managed profile，不适合作为 Private Space 的唯一监听入口。

## 17.7.5 启动、最近任务与通知

Private Space 锁定后，系统隐藏其中应用的 Launcher 图标、最近任务和通知。这里有三项容易写错：

- 通知不可见不等于 `PendingIntent` 被系统删除。官方约束描述的是锁定状态下的可见性与 profile 停止；不能在没有源码或复现证据时把点击失败归因成 PendingIntent 失效。
- 最近任务消失不等于业务 Activity 主动 `finish()`。Recents 是系统面向用户展示的任务视图，private profile 停止后由系统隐藏相关任务。
- 解锁不保证恢复原进程。应用应按进程死亡后的任务恢复规则重建依赖，并校验目标页面仍可访问。

入口路由宜集中处理。Launcher 启动、通知、App Link、分享目标和恢复的 task 都可能直接落到敏感页面；只在首页做一次认证检查会留下绕过路径。

如果产品要求“每次进入支付页都认证”，这属于 App 自有鉴权。AndroidX `BiometricPrompt` 可以组合强生物识别与设备凭据，认证成功后再发放短时会话；它不会改变 user/profile 状态，也不会替代 Private Space 或 OEM 应用锁。

下面的代码用于构建 App 自有认证提示，调用点应放在统一的敏感路由守卫中：

```kotlin
val authenticators =
    BiometricManager.Authenticators.BIOMETRIC_STRONG or
        BiometricManager.Authenticators.DEVICE_CREDENTIAL

val promptInfo = BiometricPrompt.PromptInfo.Builder()
    .setTitle("验证身份")
    .setSubtitle("继续访问敏感内容")
    .setAllowedAuthenticators(authenticators)
    .build()
```

认证回调只代表这一次系统认证完成。App 仍需定义会话过期时间、进程死亡后的默认状态、后台停留阈值，以及认证取消时返回哪个安全页面。使用 `DEVICE_CREDENTIAL` 时不要再设置 negative button，二者在 `PromptInfo` 中互斥。

`FLAG_SECURE` 也不是应用锁。它可限制窗口截图和在非安全显示器上的呈现，适合保护已打开的敏感内容；它不会认证用户，也不会阻止其他入口启动 Activity。

## 17.7.6 Sharesheet、Photo Picker 与 URI 授权

Private Space 解锁时，系统可以通过 Sharesheet 和 Photo Picker 提供受控的跨空间交互。锁定后，private profile 停止，其中的应用和内容会从这些系统入口中消失。

分析 URI 问题时，应把两个条件分开：

1. 调用方是否持有该 URI 的临时或持久授权。
2. 提供 URI 的用户与 `ContentProvider` 当前是否可用。

用户锁定 Private Space 后，来源 provider 所在用户可能停止运行。此时读取可抛出 `FileNotFoundException`、`SecurityException` 或 provider 相关异常，但这不能证明 URI grant 已被撤销。空间再次解锁后，如果授权仍在、来源对象仍存在，读取可能恢复。

对于上传、转码、OCR 或索引等长任务，稳妥的边界是：

- 在用户选择完成后立即检查 MIME、声明长度与可读性。
- 任务需要脱离来源长期执行时，将内容复制到当前 App 用户域内的受控存储。
- 记录复制是否完成，不把 `content://` 字符串当作文件系统路径。
- 重新打开 URI 时处理来源被删除、provider 不可用和授权变化。
- 日志不写原始 URI、文件名、媒体标题或私密空间包列表。

Android 16 QPR2 增加了从主空间向 Private Space 移动或复制文件的可选能力。用户从 Private Space 的 Launcher 容器选择 Add files，通过系统文件选择器选取内容，再由 private profile 内的系统组件把文件写入 `Downloads`。AOSP 发布说明标注该功能由 OEM 选择是否集成，因此 App 不能假定所有 API 36 QPR2 或后续设备都有同一入口。

媒体解码、转码与缓存的性能处理见 24.13；这里仅界定 user/profile、provider 可用性与 URI grant 的关系。

## 17.7.7 OEM App Lock 的兼容策略

OEM 手持设备应用锁可能位于 Activity 启动、任务切换、通知展示或厂商安全中心中，也可能覆盖其中几项。它未必创建独立 profile，锁定时是否终止进程、暂停后台任务或隐藏通知都由固件实现决定。

Android 17 没有供普通 App 查询“OEM 是否锁了我”的统一 API，也没有统一认证结果码。厂商名只能帮助测试分组，不能单独决定运行时分支。同一品牌不同地区固件、桌面版本或安全组件版本可能采用不同策略。

兼容代码应围绕可观察结果设计：

| 用户路径 | App 可观察信号 | 应对方式 |
| --- | --- | --- |
| 冷启动后没有到达目标页 | 生命周期、路由参数、进程创建时间 | 保存可重放的非敏感路由，避免把中断记成崩溃 |
| 从后台回到前台 | `ProcessLifecycleOwner`、页面可见性、会话时间 | 重新校验 App 自有敏感会话 |
| 通知进入失败 | 通知发出时间、目标路由是否消费 | 统计路由结果，不猜测 OEM 锁状态 |
| Picker 返回后读取失败 | URI 授权标志、异常类型、复制阶段 | 给出重选入口，区分选择取消与读取失败 |
| task 恢复到过期页面 | `savedInstanceState`、业务对象版本 | 回到安全的上一级页面并允许重试 |

系统认证页属于 App 进程外的 UI。测试脚本若只等待某个 Activity 出现，很容易把用户尚未认证判断成启动超时。自动化用例应把“出现厂商认证页”“用户取消”“认证成功后继续启动”分成不同结果。

## 17.7.8 观测与隐私

Private Space 的存在本身带有隐私含义。普通 App 的线上日志不应尝试推导或上传 `user_serial_number`、userId、私密空间应用列表。对 userId 做哈希仍可能产生稳定跨会话标识，不能自动解决隐私风险。

业务侧可以记录的字段包括：

- `entry_source`：`launcher`、`notification`、`app_link`、`share`、`picker`、`task_restore`。
- `process_start_kind`：冷启动、已有进程、未知。
- `route_result`：到达、认证取消、参数无效、来源不可读、状态已过期。
- `content_read_result`：成功、授权错误、来源不存在、provider 不可用、用户取消。
- `recovery_duration_bucket`：分桶后的恢复耗时。

这些字段描述 App 自己看到的结果，不声称识别了 Private Space 或 OEM 应用锁。默认 Launcher、Settings、系统测试工具等受控组件可以在权限允许时记录 profile type、quiet mode 和入口隐藏配置，但也应优先保留在端侧诊断中，并经过隐私审查后再做聚合。

测试范围至少覆盖：

- 主空间与 Private Space 分别全新安装，验证数据不会互相继承。
- Private Space 解锁、锁定且入口可见、锁定且入口隐藏。
- App 位于前台、后台、最近任务和进程已死亡四种起点。
- Launcher、通知、App Link、分享、Photo Picker、DocumentsUI 六类入口。
- 选择 URI 后立刻锁定空间，再执行同步读取与延迟读取。
- OEM 应用锁开启与关闭，并分别执行认证成功、取消和超时。

测试报告要写明设备、Build fingerprint、API level、QPR 或厂商版本、Launcher 版本和复现入口。只写“Android 17 应用锁异常”无法判断问题来自 AOSP Private Space、AAOS App Lock、OEM 策略，还是 App 自有鉴权。

## 17.7.9 Android 17 结论

以 Android 17 / API 37 / `android-17.0.0_r1` 为锚点，可确认以下边界：

- 手持设备 AOSP 没有通用逐应用锁的公开 SDK 或平台服务。
- Private Space 仍是独立 private profile；锁定时 profile 停止。
- hidden profile 的 Launcher 访问需要 HOME 角色与 `ACCESS_HIDDEN_PROFILES`，或系统特权权限 `ACCESS_HIDDEN_PROFILES_FULL`。
- 普通 App 不能可靠识别 Private Space，应按当前用户中的常规生命周期和失败结果编程。
- Android Automotive App Lock 是车载特权组件，不应外推到手持设备。
- 需要保护 App 内敏感页面时，应实现统一路由鉴权与安全会话，并把它和系统 profile 锁分开测试。

## References

- [Private space | Android Open Source Project](https://source.android.com/docs/security/features/private-space)
- [Android 17 feature summary](https://developer.android.com/about/versions/17/summary)
- [Android 17 release notes | AOSP](https://source.android.com/docs/whatsnew/android-17-release)
- [Android 16 / QPR1 / QPR2 release notes](https://source.android.com/docs/whatsnew/android-16-release)
- [`LauncherApps.java` | `android-17.0.0_r1`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/content/pm/LauncherApps.java)
- [`LauncherUserInfo.java` | `android-17.0.0_r1`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/content/pm/LauncherUserInfo.java)
- [`UserManager.java` | `android-17.0.0_r1`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/os/UserManager.java)
- [`ACCESS_HIDDEN_PROFILES` permission declarations | `android-17.0.0_r1`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/res/AndroidManifest.xml)
- [LauncherApps API reference](https://developer.android.com/reference/android/content/pm/LauncherApps)
- [LauncherUserInfo API reference](https://developer.android.com/reference/android/content/pm/LauncherUserInfo)
- [Show a biometric authentication dialog](https://developer.android.com/identity/sign-in/biometric-auth)
- [App Lock | Android Automotive OS](https://source.android.com/docs/automotive/unbundled_apps/app-lock)
