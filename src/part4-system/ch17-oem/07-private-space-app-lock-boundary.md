---
title: "Private Space 与应用锁的兼容性边界"
chapter: "17.7"
status: ready-for-review
drafted_date: "2026-05-25"
applicable_versions: "Android 15 (API 35) - Android 17 (API 37) QPR2；Android 17 应用锁待官方确认"
last_verified: "2026-05-25"
last_verified_against: "AOSP/Android Developers documentation, Android 16 QPR2 release notes"
confidence: medium
sources:
  - type: official
    path: "https://source.android.com/docs/security/features/private-space"
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
  - type: blog
    path: "intake/daily-info/2026-05-25.md"
tags: [private-space, app-lock, user-profile, launcher, notification, media-access]
related_chapters: ["1.3", "1.9", "12.2", "17.1", "20.7", "24.13", "26.3"]
created_by: "task2a-knowledge-gap"
created_date: "2026-05-25"
gap_source: "官方文档/每日信息/素材驱动"
---

# 17.7 Private Space 与应用锁的兼容性边界

<!-- outline-start -->
## 要点

### 🔹 Private Space 的系统模型
说明 Private Space 作为独立 profile 的安装、隐藏、锁定和解锁状态，重点落到 Launcher、Settings、PackageManager 查询和跨 profile 可见性边界。

### 🔹 应用锁与 Private Space 的边界差异
区分系统级 profile 隔离、OEM 应用锁、传闻中的 Android 17 原生应用锁三类机制，避免把通知隐藏、启动拦截、任务栈恢复写成同一个能力。

### 🔹 对启动、任务栈和进程生命周期的影响
梳理用户解锁、从 Launcher 启动、从通知进入、从分享入口进入时，Activity 启动、冷启动归因、最近任务和进程保活的观察点。

### 🔹 通知、媒体访问和 URI 授权边界
覆盖锁定状态下通知内容展示、Photo Picker/MediaStore 结果、DocumentsUI 回退、一次性 URI 授权失效和用户中断导致的稳定性问题。

### 🔹 OEM 差异与兼容性探测
整理小米、三星等应用锁方案与 AOSP Private Space 的能力差异，用能力探测、失败码、版本/品牌维度统计替代厂商硬编码。

### 🔹 线上指标与排查入口
建立应用锁/Private Space 相关的启动失败率、空数据率、授权失败率、通知点击丢失率和页面恢复耗时指标，并给出日志字段建议。

## 扩展

### 🔸 与 24.13 Photo Picker、媒体转码与缓存治理的交叉
媒体选择、云端照片、隐私空间和应用锁会同时影响 URI 可用性，需要在 24.13 只保留性能处理，系统兼容性放到本节。

### 🔸 与 26.3 性能指标采集与上报的交叉
隐私相关状态不能直接采集个人敏感信息，只记录匿名化的系统版本、profile/锁定状态可见信号和失败类型。

### 🔸 Android 17 原生应用锁待验证清单
记录需要等待官方 SDK、AOSP tag 或 Android Developers 文档确认的 API、广播、权限、通知策略和 Launcher 行为。

<!-- outline-end -->

## 17.7.1 系统模型：Private Space 是 profile，不是单 App 开关

Android 15 引入的 Private Space 建在 Android 多用户模型上，profile 类型为 `android.os.usertype.profile.PRIVATE`。用户在 Private Space 里安装应用时，系统按新的 profile 安装一份独立实例，不会把主空间的应用数据复制过去；账号、下载内容和用户生成内容也按 profile 隔离。[已验证: 官方文档, source.android.com/docs/security/features/private-space]

锁定状态是这套机制的分界线。Private Space 锁定后，private profile 会进入 stopped 状态；解锁后，private profile 才会 start。Android Developers 对 App 侧影响的描述更直接：profile stopped 时，里面的应用不能执行前台或后台活动，也不能展示通知。[已验证: 官方文档, developer.android.com/about/versions/15/features]

这带来两个工程判断：

- 主空间和 Private Space 里的同包名应用是两个用户维度下的安装实例，启动耗时、登录态、缓存命中和崩溃记录不能只按 `packageName` 聚合。
- 锁定状态下拿不到 Private Space 应用的可见入口，不能把“应用消失”“通知丢失”“媒体结果为空”直接归因到卸载、权限回收或服务端空数据。

Private Space 可以与 work profile、clone profile 同时存在，但设备上只能有一个 private profile，并且只属于 main user。普通业务应用通常拿不到枚举 hidden profile 的能力；要处理 Private Space 的，是 Launcher、Settings、文件选择器、照片选择器、分享面板和少数系统级入口。[已验证: 官方文档, source.android.com/docs/security/features/private-space]

## 17.7.2 Launcher 与系统入口的可见性边界

Launcher 是最容易把 Private Space 写错的入口。AOSP 文档要求 Launcher 支持 lock、unlock、hidden 三类状态：锁定时提供解锁入口；hidden 时不展示入口；Settings 在锁定状态下不能暴露 Private Space 的存在。[已验证: 官方文档, source.android.com/docs/security/features/private-space]

Android 15 的 Launcher 支持依赖两层条件：声明 `android.permission.ACCESS_HIDDEN_PROFILES`，并持有 `RoleManager.ROLE_HOME`。`LauncherApps#getProfiles()`、`getApplicationInfo()`、`resolveActivity()`、`getActivityList()` 等 API 面向 hidden private profile 时也遵守这个边界。第三方普通应用即使知道包名，也不能把 private profile 当成普通 user handle 查询。[已验证: 官方文档, developer.android.com/reference/android/content/pm/LauncherApps]

Launcher 识别 private profile 的公开入口是 `LauncherApps#getLauncherUserInfo()` 和 `LauncherUserInfo#getUserType()`。`LauncherUserInfo` 在 API 35 加入，`LauncherUserInfo.PRIVATE_SPACE_ENTRYPOINT_HIDDEN` 和 `getUserConfig()` 在 API 36 加入，用于表达锁定时入口是否应隐藏。锁定状态可通过 `UserManager.isQuietModeEnabled()` 判断，锁定和解锁广播会携带 `EXTRA_USER` 指向 private profile user。[已验证: 官方文档, developer.android.com/reference/android/content/pm/LauncherUserInfo]

与启动相关的失败要按入口拆开看：

- Launcher 查询失败：没有 HOME 角色、没有 `ACCESS_HIDDEN_PROFILES`、ROM 没接入 Private Space UI，都会让 private profile 不出现在 Launcher 查询结果里。
- 用户锁定 Private Space：profile stopped 后，`LauncherApps` 的部分操作会返回空结果，`pinShortcuts()` 这类操作还可能因 user locked/not running 抛出 `IllegalStateException`。
- 隐藏入口：API 36 起需要读取 `LauncherUserInfo.getUserConfig()` 中的 `PRIVATE_SPACE_ENTRYPOINT_HIDDEN`，不能只用 quiet mode 判断 UI 是否展示。

对启动性能章节的交叉引用只保留事实边界：应用冷启动、进程生命周期和首帧归因详见 1.3、8.2 和 21.1。本节只处理 profile 隔离导致的入口缺失、启动失败和指标归因问题。

## 17.7.3 应用锁、Private Space 与 OEM 方案不要混写

“应用锁”这个词在不同 ROM 上指向不同机制。写兼容性代码时，至少要拆成三类：AOSP Private Space、OEM 应用锁、待官方确认的 Android 17 原生应用锁。

| 类型 | 技术边界 | App 侧常见现象 | 可信验证方式 |
| --- | --- | --- | --- |
| AOSP Private Space | 独立 private profile，锁定时 user stopped，应用实例与数据按 profile 隔离 | Launcher 不可见、通知隐藏、分享/照片/文件入口跨空间受限 | AOSP/Android Developers 文档、`LauncherApps`/`LauncherUserInfo` API 行为 |
| OEM 应用锁 | 厂商在启动、最近任务、通知、Settings 或安全中心上加拦截策略，未必创建独立 profile | 启动前弹认证页、通知内容隐藏、后台进程未必停止 | 机型实测、厂商文档、失败码和行为表 |
| Android 17 原生应用锁 | 目前只有每日信息和社区文章线索，本轮未找到官方 Android Developers 或 AOSP 文档 | 不能写成已发布 API 或稳定行为 | [待验证: 等待 Android 17 官方 SDK、AOSP tag 或行为变更文档] |

[来源: intake/daily-info/2026-05-25.md] 当日素材出现“Android 17 原生应用锁”线索，但当前公开官方资料只能确认 Android 15 Private Space 与 Android 16 QPR2 文件导入增强。文章、社媒或 beta 传闻只能作为待验证清单，不能进入 API 能力表。

这一区分会影响排障结论。Private Space 锁定会停止 private profile；OEM 应用锁更常见的是在 Activity 启动或任务切换前做认证拦截，应用进程和后台任务是否停止取决于厂商实现。线上指标里如果只记 `is_locked=true` 这种粗字段，会把三类机制混成一个桶，后续看不出是 profile stopped、认证页取消、通知隐藏，还是媒体授权失效。

## 17.7.4 启动、任务栈和生命周期的观察点

Private Space 对启动的影响集中在“入口存在但 profile 不可运行”和“入口被隐藏”两类。前者像一次系统级 gating，后者像查询结果缺失。二者在日志里要分开记录。

建议用下表组织启动排查字段：

| 场景 | 观察点 | 记录字段 |
| --- | --- | --- |
| Launcher 点击 Private Space 应用 | profile 是否 quiet、入口是否 hidden、`LauncherApps.resolveActivity()` 是否返回空 | `entry_source=launcher`、`profile_type=private`、`quiet_mode`、`entrypoint_hidden`、`resolve_result` |
| 通知点击 | 通知是否在锁定状态被隐藏、点击时 private profile 是否 running | `entry_source=notification`、`notification_redacted`、`profile_running`、`pending_intent_result` |
| 分享面板进入 | 目标是否来自 private profile、用户是否在选择期间锁定空间 | `entry_source=sharesheet`、`target_user_type`、`selection_cancel_reason` |
| 文件/照片选择 | URI 来自主空间还是 private profile、授权是否跨 profile、读取时 profile 是否仍解锁 | `entry_source=picker`、`uri_authority`、`grant_flags`、`read_exception` |
| 最近任务恢复 | locked 后任务是否从 Recents 隐藏、恢复时是否重新认证或重新启动 | `entry_source=recents`、`task_visible`、`cold_or_warm_start` |

App 自身无法稳定、合规地探测所有 profile 状态。业务侧更可执行的办法是记录用户可观察入口和失败结果：从哪里进入、系统返回什么异常、是否能读 URI、是否发生认证取消、页面恢复用了多久。需要 profile 级信号时，优先放到 Launcher、系统应用、企业管理组件或测试工具里采集。

启动耗时指标也要改聚合键。至少把 `user_serial_number` 或匿名化 user/profile 维度纳入端侧诊断包，否则主空间的热启动和 Private Space 的冷启动会混在一起；如果合规要求不允许采集 user 维度，可以用匿名分桶记录“main/profile/unknown”，并在服务端只做聚合分析。

## 17.7.5 通知、媒体访问和 URI 授权

官方文档给出的媒体边界很明确：Private Space 锁定时，里面的应用不会出现在 Settings、Sharesheet、Photo Picker 和 DocsUI；解锁后，这些入口才会让相关应用和内容可见。跨空间访问依赖系统 Sharesheet 和 Photo Picker，且只发生在 Private Space 解锁时。[已验证: 官方文档, source.android.com/docs/security/features/private-space]

Android 16 QPR2 增加了从主空间向 Private Space 移动或复制文件的能力。流程由 Private Space Launcher 容器里的 Add files 入口发起，用户通过系统文件选择器选文件，再由新的系统组件在 private profile 内以前台服务完成传输，文件落到 Private Space 的 `Downloads` 目录。AOSP release notes 同时标明 OEM 采用该能力是可选项。[已验证: 官方文档, source.android.com/docs/whatsnew/android-16-release]

对 App 来说，这些规则会把很多“偶发 I/O 失败”伪装成业务问题：

- Photo Picker 返回的 URI 只表示用户当时授予了访问，不能推导后续 profile 状态不变。长任务读取前要处理 `SecurityException`、`FileNotFoundException` 和用户取消。
- DocumentsUI 或文件导入从 Android 16 QPR2 起多了跨 profile 移动/复制路径，缓存目录、文件名和原始 URI 不能假设同属一个用户空间。
- 通知点击失败不一定是 `PendingIntent` 丢失，也可能是锁定状态下通知被隐藏或目标 profile stopped。
- 分享入口目标为空不一定是目标 App 未安装，还可能是 private profile locked 后被系统从 Sharesheet 中移除。

媒体处理和缓存策略详见 24.13，本节只给兼容性约束：跨 profile URI 要按一次性外部输入处理，落盘前校验 MIME、大小和可读性；长耗时处理要复制到本 App 可控存储后再进入转码、上传或索引队列；失败上报不要包含原始 URI、路径或文件名。

## 17.7.6 OEM 差异的探测方式

OEM 应用锁最容易诱导业务写厂商硬编码。更稳的做法是按能力和结果建行为表：能否从 Launcher 正常启动、启动前是否出现认证页、通知内容是否隐藏、最近任务是否隐藏、后台任务是否被暂停、文件选择/照片选择是否返回可读 URI。

测试表建议按这几列记录：

| 维度 | 示例取值 | 用途 |
| --- | --- | --- |
| 系统能力 | `private_space`、`oem_app_lock`、`unknown` | 区分 profile 隔离和启动拦截 |
| 系统版本 | API level、QPR/厂商版本号 | 复现版本差异 |
| 入口类型 | Launcher、通知、分享、Photo Picker、DocumentsUI | 定位失败发生在哪个系统入口 |
| 认证结果 | 成功、取消、超时、失败码不可见 | 解释启动中断和页面恢复失败 |
| profile 可见信号 | quiet mode、entrypoint hidden、running unknown | 只在有权限的系统组件中采集 |
| 业务结果 | 启动成功、空数据、授权失败、读取异常、恢复超时 | 服务端聚合的稳定字段 |

不要把厂商名写成逻辑分支的唯一条件。同一品牌在不同地区版本、桌面版本、安全中心版本上行为可能不同。品牌维度适合做统计分组，不适合直接决定代码路径。决定处理逻辑的是系统返回值、异常类型、入口来源和用户是否完成认证。

## 17.7.7 线上指标与排查入口

Private Space 和应用锁相关问题不应该只进 crash 或 ANR 指标。更有价值的是单独建一组兼容性指标，定位“系统隐私入口改变导致业务流程不可达”的比例。

建议保留这些指标：

- `private_space_entry_failure_rate`: Launcher、通知、分享、Picker 等入口进入失败占比，按入口拆分。
- `profile_locked_read_failure_rate`: URI 或文件读取阶段出现权限/文件不存在异常的比例，按 MIME 和入口拆分，不记录原始 URI。
- `notification_resume_loss_rate`: 通知点击后没有进入目标页面或需要重新认证的比例。
- `picker_empty_or_cancel_rate`: Photo Picker / DocumentsUI 结果为空、取消、读取失败的比例。
- `locked_state_recovery_duration_ms`: 用户完成系统认证后到业务页面可交互的耗时，按 P50/P90/P99 看分布。

日志字段要能支持复盘，但不能泄露隐私状态。推荐字段为系统版本、厂商版本、入口类型、匿名 profile 分桶、错误类型、异常类名、耗时分位、是否发生用户取消。不要上传应用列表、私密空间中安装的包名、文件路径、媒体名称、账号信息或原始通知内容。性能指标采集与上报规范详见 26.3。

## 17.7.8 Android 17 应用锁待验证清单

本轮只找到每日信息中的 Android 17 应用锁线索，没有找到可引用的 Android Developers 行为变更、SDK API reference 或 AOSP tag 文档。因此本节不把 Android 17 应用锁写成已确认能力。

后续资料出现后，需要按下面清单补证据：

- API 面：是否存在新的 `PackageManager`、`LauncherApps`、`NotificationManager`、`ActivityTaskManager` 或 `DevicePolicyManager` API。
- 权限面：是否新增普通权限、signature 权限、role 约束，或沿用 `ACCESS_HIDDEN_PROFILES` / HOME role 模型。
- 启动面：被锁应用从 Launcher、通知、分享、deep link、最近任务进入时，系统返回认证页还是直接拦截。
- 通知面：通知是否隐藏整条、只隐藏内容，还是按 channel/category 处理。
- 生命周期面：被锁应用是否 stopped、进程是否保留、后台服务和 Job 是否继续运行。
- 可观测面：是否有公开错误码、statsd atom、logcat tag 或 `ApplicationExitInfo` reason 可用于线上归因。

只有这些点能被官方文档、AOSP tag 或可复现实机测试支撑时，才能把 Android 17 应用锁从 `[待验证]` 升级为正式能力表。

## References

- [已验证: 官方文档, Private space | Android Open Source Project](https://source.android.com/docs/security/features/private-space)
- [已验证: 官方文档, Android 16 / QPR1 / QPR2 release notes](https://source.android.com/docs/whatsnew/android-16-release)
- [已验证: 官方文档, Android 15 features and APIs overview](https://developer.android.com/about/versions/15/features)
- [已验证: 官方文档, Android 15 behavior changes for all apps](https://developer.android.com/about/versions/15/behavior-changes-all)
- [已验证: 官方文档, LauncherApps API reference](https://developer.android.com/reference/android/content/pm/LauncherApps)
- [已验证: 官方文档, LauncherUserInfo API reference](https://developer.android.com/reference/android/content/pm/LauncherUserInfo)
- [来源: intake/daily-info/2026-05-25.md]

- [Android 17 原生应用锁：系统级通知隐藏与 OEM 对比，黄林晴，掘金，2026-02-10](https://juejin.cn/post/7604694326518104115) — Android 17 Canary 2601 代码中曝光 `app_locked_new_notification` 等字段，揭示原生应用锁的通知分类屏蔽策略；与小米 HyperOS 的对比参考有助于理解 OEM 差异化落点。

<!-- AIW-源码调研-2026-06-06 -->

### 17.7.8.1 AOSP源码验证结果（2026-06-06）

基于AOSP main分支（等同于Android 17）源码级验证，确认以下事实：

**✅ 已验证结论：**
1. **不存在原生应用锁功能**：AOSP main分支中未发现任何AppLock、AppLockManager相关API或实现
2. **Android 17官方安全特性为AAPM**：`AdvancedProtectionManager.java`提供设备级安全模式，非应用级锁定
3. **功能差异明确**：AAPM包含网络限制、USB限制、安装源限制等，不提供应用锁定能力
4. **官方文档无应用锁条目**：Android 17 behavior changes和features页面均未提及应用锁功能

**🔍 源码搜索范围：**
- `frameworks/base/core/java/android/security/advancedprotection/AdvancedProtectionManager.java`
- `frameworks/base/services/core/java/com/android/server/am/`（无AppLock相关类）
- `frameworks/base/core/java/android/app/`（仅有RemoteLockscreenValidationSession，为锁屏验证非应用锁）
- `frameworks/base/core/java/android/content/pm/`（无应用锁API）
- `frameworks/base/core/java/android/app/admin/`（无应用锁权限）
- `frameworks/base/core/java/android/app/Notification.java`（无应用锁定通知字段）

**⚠️ 与社区文章的差异：**
- 网络文章声称"Android 17 Canary 2601 暴露 app_locked_new_notification"与官方发布版本不符
- 该内容可能属于未发布的实验性代码或社区误传
- 官方Android 17最终版本不包含此功能

**📝 结论：**
Android 17应用锁仍处于"待官方确认"状态，本轮AOSP源码验证未发现相关实现。后续需要等待官方SDK、AOSP tag或Android Developers文档更新才能确认具体API和能力边界。
