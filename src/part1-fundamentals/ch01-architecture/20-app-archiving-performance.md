---
title: App Archiving 机制与恢复性能
chapter: '1.20'
section: '1.20'
status: finalized
applicable_versions: Android 15 (API 35) - Android 17 (API 37)
last_verified: '2026-07-25'
last_verified_against: AOSP android-17.0.0_r1 + Android 17 API 37 official documentation
confidence: high
sources:
  - type: official
    path: "https://developer.android.com/about/versions/15/features#app-archiving"
  - type: official
    path: "https://developer.android.com/reference/android/content/pm/PackageInstaller"
  - type: official
    path: "https://developer.android.com/reference/android/content/pm/PackageManager"
  - type: official
    path: "https://developer.android.com/reference/android/content/pm/LauncherApps.ArchiveCompatibilityParams"
  - type: aosp
    path: "frameworks/base/core/java/android/content/pm/PackageInstaller.java @ android-17.0.0_r1"
  - type: aosp
    path: "frameworks/base/core/java/android/content/pm/PackageManager.java @ android-17.0.0_r1"
  - type: aosp
    path: "frameworks/base/core/java/android/content/pm/ArchivedPackageInfo.java @ android-17.0.0_r1"
  - type: aosp
    path: "frameworks/base/core/java/android/content/Intent.java @ android-17.0.0_r1"
  - type: aosp
    path: "frameworks/base/core/java/android/content/pm/LauncherApps.java @ android-17.0.0_r1"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/pm/PackageArchiver.java @ android-17.0.0_r1"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/pm/pkg/ArchiveState.java @ android-17.0.0_r1"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/pm/PackageInstallerService.java @ android-17.0.0_r1"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/pm/PackageInstallerSession.java @ android-17.0.0_r1"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/pm/DeletePackageHelper.java @ android-17.0.0_r1"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/pm/RemovePackageHelper.java @ android-17.0.0_r1"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/pm/InstallPackageHelper.java @ android-17.0.0_r1"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/pm/BroadcastHelper.java @ android-17.0.0_r1"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/pm/LauncherAppsService.java @ android-17.0.0_r1"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/pm/PackageManagerShellCommand.java @ android-17.0.0_r1"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/wm/ActivityStarter.java @ android-17.0.0_r1"
tags:
  - android
  - package-manager
  - app-archiving
  - storage
  - launcher
  - app-startup
related_chapters:
  - '1.9'
  - '4.2'
  - '6.1'
  - '8.2'
  - '12.1'
  - '16.2'
drafted_date: "2026-05-17"
created_by: "task2a-knowledge-gap"
created_date: "2026-05-17"
gap_source: "素材驱动/AOSP结构/官方文档"
material_paths:
  - "OpenClaw定时任务/AutoResearchClaw调研报告/2026-05-01-android-app-archiving-package-archiver-activitystarter-mechanism.md"
  - "developer.android.com/about/versions/15/features"
  - "cs.android.com frameworks/base/services/core/java/com/android/server/pm/PackageArchiver.java"
  - "cs.android.com frameworks/base/services/core/java/com/android/server/wm/ActivityStarter.java"
task6_reviewed_date: "2026-06-15"
task6_l1_l2_fixes: 17
task6_l3_l4_issues: 0
pipeline_stage: ready-to-publish
task6_state: reviewed
task6_result: pass-light-edit
task9_state: reviewed
task9_result: auto-fixed
task9_reviewed_date: "2026-06-15"
task9_reviewed_by: openclaw-task9
last_task9_at: "2026-06-15T12:34:44+08:00"
last_task9_autofix_at: "2026-06-15"
last_task9_review_log: "logs/deep-review/2026-06-15-12-deep-review.md"
task2b_state: fixed
task2b_result: fixed-lite
last_task2b_lite_at: 2026-06-15
queue_entry: task9-2026-05-17-1-20-archive-conditions-callback
p0: 0
p1: 0
p2: 0
task9_review_notes: "2026-06-15 12:34 Task9 auto-fixed：清理上一轮回炉后残留的未限定源码锚点表述，并补正 SDM 校验边界：PackageArchiver 主路径无 SDM 特判，PackageInstallerSession android-16.0.0_r1 存在 verifySdmSignatures()，恢复安装是否携带 .sdm 仍待端到端验证。此前：2026-06-15 闲时抽检 P1:2 已由 Task2B Lite 修复；2026-05-27 Task9 pass-tech-review。"
reviewed_by: openclaw-task6
reviewed_date: "2026-06-15"
last_task6_at: "2026-06-15T13:15:35+08:00"
last_task6_review_log: "logs/review/2026-06-15-13-review.md"
task6_review_notes: "2026-05-27 Task6：回炉复审通过；Task2B 已补齐 requestArchive 失败路径、点击恢复 listener 口径和恢复链路时序图；本轮仅修验证标注前空格，无 L3/L4 回炉项。送 Task9 技术复审。 2026-06-15 Task6 revisiting→reviewed：pass-light-edit。L1/L2 无新问题（经多轮 review 已清洁）；L3/L4 无写作质量回炉项。Task9 闲时抽检 needs-rework（P1:2 技术口径），待 Task9 复审。 2026-06-15 Task6 revisiting→reviewed：pass-light-edit，自动晋升 finalized。Task9 auto-fixed（源码锚点已重定向 android-15/16.0.0_r1，版本边界已修正，调用者范围已拆分 Android 15 vs 16）；Task2B fixed-lite；queue.json 1.20 条目 completed。L1 全量扫描零命中（禁用词/汇报腔/AI套话/翻译腔/高频词/元叙述），L2 结构与节奏良好，L3/L4 无写作质量回炉项。✅ 自动晋升 finalized。"
deepseek_cn_review_state: done
last_deepseek_cn_review_at: 2026-06-25
last_task9_audit: "2026-06-15"
last_task9_audit_at: "2026-06-15T11:26:52+08:00"
last_task9_audit_log: "logs/deep-review/2026-06-15-11-audit.md"
last_task6_audit: "2026-06-25"
last_task6_audit_at: "2026-06-25T12:05:00+08:00"
last_task6_audit_log: "logs/review/2026-06-25-12-audit.md"
last_task6_audit_result: "pass-no-edit"
---

# 1.20 App Archiving 机制与恢复性能

Android 15 把应用归档做成了平台能力；Android 17 延续并完善了这条链路。应用归档不涉及压缩，也不等同于换了名称的普通卸载；它是一种可恢复的包状态转换：

```text
已安装
  ├─ 代码可用，组件可解析
  ├─ 用户数据存在
  └─ Launcher 展示真实 Activity
          │ requestArchive()
          ▼
已归档
  ├─ 当前用户的 installed = false
  ├─ ArchiveState 保存入口、标题和图标
  ├─ 用户数据保留，cache / code cache 被清理
  └─ Launcher 展示系统合成的归档入口
          │ requestUnarchive() / 点击归档图标
          ▼
恢复安装
  ├─ responsible installer 获取 APK
  ├─ PackageInstaller 会话完成正常安装校验
  ├─ installed = true，清除 ArchiveState
  └─ ACTION_PACKAGE_ADDED 表示安装完成
```

这套机制主要解决磁盘空间与恢复体验问题。它会经过包删除路径并通常终止目标进程，但不属于 LMKD 的内存回收策略。恢复过程还要先完成下载与安装，然后才能进入普通冷启动。

## 1. 四种容易混淆的状态

| 状态 | APK | 用户数据 | Launcher 入口 | 恢复责任方 |
|---|---|---|---|---|
| 已安装 | 有 | 有 | 真实 Activity | 不需要恢复 |
| 已归档 | 可能已删除，取决于多用户状态 | 保留 | `ArchiveState` 合成入口 | responsible installer |
| 卸载但保留数据 | 通常无 | 保留 | 没有平台归档入口 | 没有标准恢复契约 |
| `installPackageArchived()` 创建的归档包 | 无 APK，只有归档元数据 | API 不负责生成业务数据 | 归档入口 | 指定安装器 |

最末行是 Android 15 同期加入的另一条特权 API。`PackageInstaller.installPackageArchived()` 使用 `ArchivedPackageInfo` 在没有 APK 的情况下登记归档包，供需要先建立归档元数据的系统级流程使用。它不是用户点击归档图标后的下载接口，也不能替代 `requestUnarchive()`。

## 2. 平台中的参与者

### 2.1 发起归档的一方

调用入口是 `PackageInstaller.requestArchive(packageName, statusReceiver)`，API 35 加入。调用者需要：

- `DELETE_PACKAGES`，通常只授予系统或特权组件；或
- `REQUEST_DELETE_PACKAGES`，没有静默删除资格时仍会进入用户确认。

SDK 注解只是第一层。服务端还会校验 caller package 与 Binder UID、跨用户权限，以及后续卸载策略。持有 `REQUEST_DELETE_PACKAGES` 不等于可以静默归档任意应用。

归档前可先调用 `PackageManager.isAppArchivable(packageName)`。它适合用于界面能力判断，但不承诺操作一定成功：设备策略、App Lock、用户限制、包状态变化或确认流程仍可能导致归档失败。

### 2.2 `PackageArchiver`

`PackageArchiver` 位于 system_server 的 Package Manager 侧，负责：

- 检查目标包是否满足归档条件。
- 在删除 APK 前生成并持久化 `ArchiveState`。
- 把归档请求转换成带特殊标志的卸载。
- 识别 Launcher 点击是否指向归档入口。
- 建立恢复草稿会话，并通知负责恢复的安装器。
- 把安装器返回的接受状态或错误转给 Launcher / API 调用者。

它不负责下载 APK，也不负责应用首帧。

### 2.3 Launcher

`LauncherApps` 会把归档应用作为可展示条目返回。AOSP 的 `LauncherAppsService` 根据 `ArchiveState` 合成 `ActivityInfo`，保留原始 `ComponentName` 和标题，因此桌面仍能展示并点击这个入口。

默认兼容行为包括：

- 在图标上叠加云朵标记。
- 点击后显示恢复确认。

Launcher 可通过 `LauncherApps.setArchiveCompatibility()` 关闭其中一项，但前提是自己提供等价的状态提示和恢复进度体验。否则用户会把一次网络恢复误认为普通启动卡死。

### 2.4 负责恢复的安装器

恢复责任方按以下优先级选择：

```text
InstallSource.updateOwnerPackageName
        ↓ 为空
InstallSource.installerPackageName
```

正常应用路径在归档前会确认该安装器仍安装在目标用户中，并能接收显式的 `Intent.ACTION_UNARCHIVE_PACKAGE`。找不到能够恢复应用的安装器时，目标包不应被归档。

## 3. 为什么必须先保存 `ArchiveState`

APK 删除后，系统不能再从清单和资源表中读取 Launcher Activity、label 与图标。因此 `PackageArchiver.createAndStoreArchiveState()` 必须先完成以下工作：

1. 取得目标用户下的包状态。
2. 拒绝系统应用和已更新的系统应用。
3. 确认该用户当前安装了目标包。
4. 找到并验证负责恢复的安装器。
5. 检查归档 opt-out 状态。
6. 通过 `LauncherApps.getActivityList()` 取得至少一个 Launcher Activity。
7. 保存每个入口的标题、原始组件名和图标。

Android 17 的 `ArchiveState` 包含：

- `activityInfos`：一个或多个原始 Launcher Activity。
- `installerTitle`：负责恢复的安装器标题。
- `archiveTimeMillis`：归档时间。
- 每个 Activity 的标题、原始 `ComponentName`、普通图标路径和可选单色图标路径。

图标存放在用户的 CE 系统目录：

```text
/data/system_ce/<userId>/package_archiver/<packageName>/
```

这是系统保存的展示材料，不是应用数据目录。重新安装成功时，`InstallPackageHelper` 会清除 `ArchiveState`，`PackageArchiver.clearArchiveState()` 同时删除这批图标。

## 4. 归档实际走的是特殊卸载

状态准备完成后，Android 17 组合以下删除标志：

```text
DELETE_ARCHIVE | DELETE_KEEP_DATA
```

需要为所有用户归档时再加 `DELETE_ALL_USERS`。公开的 `requestArchive()` 默认只针对当前 `PackageInstaller` 所在用户；shell 的 `pm archive` 默认选择 all users，测试时不要混用这两种语义。

两个核心标志的职责不同：

- `DELETE_ARCHIVE`：告诉删除与广播链路这是归档，不是普通卸载。
- `DELETE_KEEP_DATA`：保留包设置和用户数据，使后续安装可以恢复原有身份与数据。

归档仍会进入 `PackageInstallerService.uninstall()` 和 `DeletePackageHelper`。因此设备管理员、禁止卸载策略、受保护包、App Lock 等限制仍然生效。删除路径会冻结并通常终止目标包；这与 LMKD 根据 PSI 和 adj 终止进程是两套机制。

删除成功时，包移除广播会携带 `EXTRA_ARCHIVAL=true`，同时把 `EXTRA_REPLACING` 设为 true、`EXTRA_DATA_REMOVED` 设为 false。接收方由此可以把归档与删除应用数据的普通卸载区分开。

### 4.1 删除 APK 的多用户前提

APK 和 native library 位于包级代码目录，可被多个 Android 用户共用；`installed` 与 `ArchiveState` 则是 per-user 状态。Android 17 的删除逻辑因此分成两种情况。

#### 只归档一个用户，其他用户仍安装

系统只把当前用户标记为未安装并清理相关状态。代码目录继续保留，因为其他用户仍要运行同一份 APK。

此时能够稳定回收的是归档路径清理的缓存/ code cache；不能把整个 APK 大小都计入收益。

#### 归档唯一仍安装 user

如果没有其他用户安装该包，而且 PMS 没有因内部缓存策略保留未安装包，删除流程才会移除包级代码和资源。`PackageSetting` 因 `DELETE_KEEP_DATA` 继续存在，并携带归档状态。

更准确的容量模型是：

```text
单用户归档收益
  = 缓存 + 代码缓存
  + 条件成立时的共享代码目录

共享代码目录可回收
  ⇔ 没有其他用户仍安装该包
     且 PMS 不要求缓存该未安装包
```

### 4.2 保留与清理的边界

| 对象 | Android 17 归档结果 | 说明 |
|---|---|---|
| CE / DE 用户数据 | 保留 | 数据库、SharedPreferences、账号态等可在恢复后继续使用 |
| cache | 清理 | `FLAG_CLEAR_CACHE_ONLY` |
| code cache | 清理 | `FLAG_CLEAR_CODE_CACHE_ONLY` |
| ART app profile | 删除路径会销毁 | 归档没有设置 keep-profile flag |
| APK / split / native library | 条件性删除 | 受其他用户与 PMS 缓存策略影响 |
| 任意共享存储文件 | 没有“全部删除”保证 | 不应把归档当成外部文件清理器 |
| `ArchiveState` 与归档图标 | 保留 | 用于 Launcher 展示与恢复 |

“用户数据保留”不代表所有运行时加速材料都会保留。ART 配置文件被清理后，即使账号和数据库仍在，恢复后的编译状态与首次启动性能也可能发生变化。

## 5. Launcher 如何把失败启动变成恢复请求

归档入口仍保存原始 `ComponentName`。Launcher 点击后走正常的 `startActivity()`，但 APK 已不可用，`ActivityStarter` 找不到 `ActivityInfo`。Android 17 在 `START_CLASS_NOT_FOUND` 分支追加归档判断：

```text
aInfo == null
  └─ PackageArchiver.isIntentResolvedToArchivedApp()
       ├─ package 必须处于归档状态
       ├─ Intent 必须包含显式组件
       └─ component 必须匹配 ArchiveState 中的原始入口
```

只有三项都满足，系统才调用 `requestUnarchiveOnActivityStart()`。普通的类名写错、组件被移除或包完全卸载，仍按 `START_CLASS_NOT_FOUND` 处理，不会被归档逻辑吞掉。

### 5.1 谁能从点击路径发起恢复

Android 17 的实现允许：

- Shell。
- 当前用户或 profile parent 的默认 Launcher。
- 能解析 HOME Intent 的 Launcher 应用。

源码方法注释仍写着“default/Home Launcher or Shell”，但实现已放宽到其他 Launcher 应用。非默认 Launcher 即使有资格触发，也会强制显示恢复确认。

初次启动请求最终返回 `START_ABORTED`。目标 Activity 此时不存在，Window Manager 必须停止本次启动和动画，不能把它伪装成成功。

## 6. 恢复链路有两条异步状态线

### 6.1 框架层先创建草稿会话

`PackageArchiver.requestUnarchive()` 会先验证：

- 目标包在该用户下处于归档状态。
- caller package 与 UID 一致。
- 调用者声明或持有 `REQUEST_INSTALL_PACKAGES` / `INSTALL_PACKAGES`。
- 跨用户权限满足。

若需要用户确认，系统先通过 `STATUS_PENDING_USER_ACTION` 返回确认 Intent。确认通过后，Framework 为 responsible installer 创建草稿会话：

```text
MODE_FULL_INSTALL
appPackageName = 目标包
installFlags = INSTALL_UNARCHIVE_DRAFT | INSTALL_UNARCHIVE
```

重复点击时，系统会复用同一目标包的有效 draft session；若恢复已在进行，符合配置的 Launcher 会打开会话详情，不会并行发起第二次下载。

### 6.2 系统向安装器发送显式广播

system_server 随后发送：

```text
Intent.ACTION_UNARCHIVE_PACKAGE
  ├─ EXTRA_UNARCHIVE_ID
  ├─ EXTRA_UNARCHIVE_PACKAGE_NAME
  └─ EXTRA_UNARCHIVE_ALL_USERS
```

广播使用 `setPackage(installerPackage)`，`Intent` 定义也标记为 explicit-only。系统给安装器一个临时后台执行窗口；Android 17 AOSP 常量为 120 秒。这是实现细节，并未规定下载必须在 120 秒内完成；安装器仍应尽快转入合规的前台或 session 工作流。

### 6.3 安装器的恢复契约

收到广播后，安装器需要：

1. 读取包名与 `unarchiveId`。
2. 判断账号、网络、可用包和空间。
3. 通过 `reportUnarchivalState()` 返回“可开始”或具体错误。
4. 创建 full-install session，在 `SessionParams` 中设置目标包与 `unarchiveId`。
5. 写入基础 base APK 并提交。
6. 让标准 PackageInstaller / PMS 安装链路完成签名、版本、策略和包扫描。

`unarchiveId` 把广播与安装会话绑定起来。即使安装器没有设置它，Android 17 也会尝试按包名、installer UID 和用户复用 draft session，但显式设置可以消除并发歧义。

`INSTALL_UNARCHIVE` 不是安装器可随意伪造的“跳过确认”开关。`PackageInstallerService` 会清掉外部传入值，仅在目标已归档、请求安装器与 responsible installer 匹配时重新设置。它允许在恢复确认完成后跳过第二次安装确认，但不会跳过 APK 签名和正常安装校验。

### 6.4 安装完成不会自动重放第一次点击

- `UNARCHIVAL_OK` 只表示安装器能够开始恢复。
- 初次 `startActivity()` 已以 `START_ABORTED` 结束。
- Android 17 的 `PackageArchiver` 没有保存并自动重放原始启动 Intent。
- 安装完成通过 `ACTION_PACKAGE_ADDED` 或会话完成状态观察。

Launcher 或产品层可以展示下载进度，并在安装完成后让用户再次点击；某些 OEM 或安装器也可能额外提供“恢复后打开”，但那不是 AOSP `PackageArchiver` 的默认保证。

## 7. 正确理解三个回调

| 信号 | 表示什么 | 不表示什么 |
|---|---|---|
| `requestArchive()` 的 `EXTRA_STATUS` | 待用户操作、成功或失败；success 才表示归档删除完成 | 不代表一定回收了完整 APK 大小 |
| `requestUnarchive()` 的 `EXTRA_UNARCHIVE_STATUS` | 安装器是否接受请求，或为什么不能开始 | 不代表 APK 已安装 |
| 恢复 session success /对应的 `ACTION_PACKAGE_ADDED` | APK 已重新安装，归档状态已清除 | 不代表应用首帧已经完成 |

恢复链路可能给出以下状态：

- `UNARCHIVAL_OK`
- 需要用户操作
- 存储不足，并给出还缺多少字节
- 无网络
- 安装器被禁用或已卸载
- 通用错误

把 `UNARCHIVAL_OK` 当作安装完成，会让监控数据提前结束，也会让 Launcher 在 APK 仍不存在时再次启动。

## 8. 恢复性能要拆成四段

```text
T_user_ready
  = T_framework_request
  + T_installer_prepare
  + T_download_and_install
  + T_next_launch
```

### 8.1 `T_framework_request`

包括 `ActivityStarter` 发现类不存在、匹配 `ArchiveState`、校验 Launcher 与确认策略、创建 draft session 和发送恢复广播。这些工作主要在 `system_server` 内完成，通常远短于网络和安装。如果这里很慢，应优先检查 `system_server` 锁竞争、Package Manager 处理线程排队和会话 I/O。

### 8.2 `T_installer_prepare`

包括安装器进程拉起、账号与授权检查、包版本选择、空间估算和状态上报。需要登录、付费校验或用户确认时，耗时没有固定上限。

### 8.3 `T_download_and_install`

包括网络下载与分包选择、session 写入和提交、签名与版本校验、包扫描、权限状态恢复、dexopt/ART 工作和 `ACTION_PACKAGE_ADDED`。这通常是恢复的主要耗时，不能用 `PackageArchiver` 的短耗时掩盖安装器与 PackageInstaller 的长尾。

### 8.4 `T_next_launch`

恢复后的启动仍是普通应用冷启动：Zygote fork、`bindApplication`、Provider、`Application`、Activity 与首帧都不会被归档机制跳过。

归档路径还清理了缓存、code cache 和 app profile，所以首次启动可能比应用持续安装时的冷启动更慢。内置 Baseline Profile、合理的启动依赖和较小的安装包仍有作用，但不能据此承诺恢复后一定完成 AOT 编译。

## 9. 指标与观测

不要只报一个“恢复耗时”。至少拆成：

| 指标 | 起点 | 终点 | 主要责任域 |
|---|---|---|---|
| `T_archive_done` | 发起归档 | `requestArchive` success | PMS / installd / 存储 |
| `T_unarchive_accepted` | 点击或调用恢复 | `UNARCHIVAL_OK` | `system_server` / installer |
| `T_package_restored` | 点击或调用恢复 | session success / `ACTION_PACKAGE_ADDED` | 网络 / installer / PMS |
| `T_first_frame_after_restore` | 恢复完成后的启动 | 首帧完成 | App 启动链 |

如果产品点击一次后自动等待并打开应用，可额外定义端到端指标，但必须注明“自动打开”由哪一层实现。

### 9.1 Android 17 命令行验证

先在测试包和测试用户上执行，避免误归档主账号应用：

```bash
adb shell pm archive --user current <package>
adb shell dumpsys package <package>
adb shell pm request-unarchive --user current <package>
adb logcat -s PackageArchiverService PackageManager PackageInstaller ActivityTaskManager
```

还可用：

```bash
adb shell pm get-archived-package-metadata --user current <package>
```

该命令输出用于 `install-archived` 的序列化十六进制元数据，不是面向人的状态摘要。`pm list packages -u` 只能说明 PMS 仍知道这个未安装包，也不能单独证明它拥有有效 `ArchiveState`。

### 9.2 Trace 对齐

Perfetto 中至少同时观察：

- system_server 的 ActivityTaskManager / Package Manager 工作。
- 负责恢复的安装器进程启动、网络和会话写入。
- installd、dex2oat / ART 相关工作。
- 恢复完成后的目标应用进程与首帧。

测量磁盘收益时要记录其他用户是否仍安装该包，并分别统计基础 APK、split、native library、cache、code cache 与用户数据。忽略多用户条件，既可能把“只清了缓存”误报成归档失效，也可能把其他清理任务释放的空间算给归档。

## 10. 安全与策略边界

归档保留用户数据，因此恢复必须保持包身份连续性。Android 17 的关键约束是：

- 归档调用方的包名/UID 必须匹配。
- 归档与恢复分别受删除、安装和跨用户权限约束。
- responsible installer 由既有 `InstallSource` 决定。
- 恢复广播只显式发送给该安装器。
- draft session 绑定安装器 UID、目标包和用户。
- `INSTALL_UNARCHIVE` 由系统重新判定，不能由普通安装器强行保留。
- 恢复 APK 继续经过标准安装、签名和版本校验。
- 设备所有者、工作资料策略、应用锁和用户限制仍可阻止操作。

当前 `PackageArchiver` 没有“归档专用 SDM 签名校验”分支。`.sdm` 或云编译材料如果参与安装，属于 `PackageInstallerSession` 的通用安装能力；没有端到端证据时，不应把它写成归档恢复的强制步骤。

归档也不会为目标应用创建新的 SELinux domain。归档态没有可执行 APK 和可启动进程；恢复后仍根据包身份、seinfo 与平台策略进入正常应用域。

## 11. 版本边界

| 版本 | 平台能力 |
|---|---|
| Android 14 及以前 | 没有公开的 OS-level `requestArchive()` / `requestUnarchive()`；应用商店可实现自己的归档方案 |
| Android 15 / API 35 | 引入平台归档 API、`ArchiveState`、`ACTION_UNARCHIVE_PACKAGE`、Launcher 归档入口和 metadata-only archived install |
| Android 16 / API 36 | 延续平台能力并迭代 Launcher / session 处理 |
| Android 17 / API 37 | 当前源码锚点；以 `android-17.0.0_r1` 的多用户删除、draft session、确认与 Launcher 行为为准 |

Android 15 的“移除 APK 与缓存、保留用户数据”是 API 契约层的概括；Android 17 源码补充了一个实现边界：其他用户仍安装时，共享 APK 必须保留。

## 12. 常见误区

### 误区一：归档一定释放“安装大小”

不一定。多用户设备上，其他用户仍安装就不能删除共享代码目录。应分别测量代码、缓存和用户数据。

### 误区二：归档就是 LMKD 杀进程

不是。它走包删除路径并会终止目标进程；触发原因和状态转换都属于 Package Manager，不是内存压力回收。

### 误区三：`UNARCHIVAL_OK` 表示应用已经恢复

不是。它只表示恢复可开始，安装完成要看 session 或 `ACTION_PACKAGE_ADDED`。

### 误区四：系统会自动重放第一次点击

AOSP Android 17 没有这个保证。首次启动已返回 `START_ABORTED`。

### 误区五：`INSTALL_UNARCHIVE` 绕过安装安全

它只避免已确认恢复后再次弹出安装确认。系统会重新计算该标志，APK 仍走正常校验。

### 误区六：数据保留意味着性能状态完全保留

不成立。cache、code cache 和 app profile 都可能被清理，恢复后的首次启动要单独测量。

## 13. 源码阅读索引

- [`PackageInstaller.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/content/pm/PackageInstaller.java)：公开归档、恢复、状态上报和 archived install API。
- [`PackageManager.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/content/pm/PackageManager.java)：`isAppArchivable()` 与 `getArchivedPackage()`。
- [`ArchivedPackageInfo.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/content/pm/ArchivedPackageInfo.java)：无 APK 归档安装所需的包、签名和入口元数据。
- [`Intent.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/content/Intent.java)：`ACTION_UNARCHIVE_PACKAGE` 与 `EXTRA_ARCHIVAL`。
- [`LauncherApps.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/content/pm/LauncherApps.java)：Launcher 兼容选项。
- [`PackageArchiver.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/services/core/java/com/android/server/pm/PackageArchiver.java)：归档状态、恢复请求、图标和 installer 协议主线。
- [`ArchiveState.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/services/core/java/com/android/server/pm/pkg/ArchiveState.java)：归档状态数据模型。
- [`PackageInstallerService.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/services/core/java/com/android/server/pm/PackageInstallerService.java)：卸载确认、draft session、unarchive flag 与 archived install。
- [`PackageInstallerSession.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/services/core/java/com/android/server/pm/PackageInstallerSession.java)：恢复安装的用户确认与状态上报。
- [`DeletePackageHelper.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/services/core/java/com/android/server/pm/DeletePackageHelper.java)：单用户/全用户删除和代码目录回收条件。
- [`RemovePackageHelper.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/services/core/java/com/android/server/pm/RemovePackageHelper.java)：cache、code cache、profile 与用户数据边界。
- [`InstallPackageHelper.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/services/core/java/com/android/server/pm/InstallPackageHelper.java)：恢复安装后清除归档状态。
- [`BroadcastHelper.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/services/core/java/com/android/server/pm/BroadcastHelper.java)：归档与安装广播的 extras。
- [`LauncherAppsService.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/services/core/java/com/android/server/pm/LauncherAppsService.java)：合成归档 Launcher Activity。
- [`PackageManagerShellCommand.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/services/core/java/com/android/server/pm/PackageManagerShellCommand.java)：`pm archive`、`request-unarchive` 和 metadata 命令。
- [`ActivityStarter.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/services/core/java/com/android/server/wm/ActivityStarter.java)：`START_CLASS_NOT_FOUND` 到恢复请求的切换。
- [Android 15 App archiving 官方说明](https://developer.android.com/about/versions/15/features#app-archiving)
- [PackageInstaller API](https://developer.android.com/reference/android/content/pm/PackageInstaller)
- [Launcher archive compatibility API](https://developer.android.com/reference/android/content/pm/LauncherApps.ArchiveCompatibilityParams)

## 小结

Android 17 的 App Archiving 可以概括为：

```text
先保存可恢复入口
  → 用 DELETE_ARCHIVE | DELETE_KEEP_DATA 转换包状态
  → Launcher 展示归档入口
  → 点击后把恢复请求交给 responsible installer
  → 安装器通过普通 PackageInstaller 会话恢复 APK
  → 安装成功后清除 ArchiveState
```

需要记住的是三个边界：

1. 归档状态按用户保存，APK 却可能由多个用户共享。
2. `UNARCHIVAL_OK` 是“开始恢复”，不是“恢复完成”。
3. 归档保留业务数据，但会清理缓存和 profile；恢复后的启动性能必须重新测量。
