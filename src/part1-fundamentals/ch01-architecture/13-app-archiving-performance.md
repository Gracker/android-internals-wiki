---
title: 应用归档（App Archiving）机制与恢复性能
chapter: '1.13'
section: '1.13'
status: finalized
applicable_versions: Android 15 (API 35) - Android 17 (API 37)
last_verified: '2026-07-25'
last_verified_against: AOSP android-17.0.0_r1 + Android 17 API 37 official documentation
confidence: high
sources:
- type: official
  path: https://developer.android.com/about/versions/15/features#app-archiving
- type: official
  path: https://developer.android.com/reference/android/content/pm/PackageInstaller
- type: official
  path: https://developer.android.com/reference/android/content/pm/PackageManager
- type: official
  path: https://developer.android.com/reference/android/content/pm/LauncherApps.ArchiveCompatibilityParams
- type: aosp
  path: frameworks/base/core/java/android/content/pm/PackageInstaller.java @ android-17.0.0_r1
- type: aosp
  path: frameworks/base/core/java/android/content/pm/PackageManager.java @ android-17.0.0_r1
- type: aosp
  path: frameworks/base/core/java/android/content/pm/ArchivedPackageInfo.java @ android-17.0.0_r1
- type: aosp
  path: frameworks/base/core/java/android/content/Intent.java @ android-17.0.0_r1
- type: aosp
  path: frameworks/base/core/java/android/content/pm/LauncherApps.java @ android-17.0.0_r1
- type: aosp
  path: frameworks/base/services/core/java/com/android/server/pm/PackageArchiver.java @ android-17.0.0_r1
- type: aosp
  path: frameworks/base/services/core/java/com/android/server/pm/pkg/ArchiveState.java @ android-17.0.0_r1
- type: aosp
  path: frameworks/base/services/core/java/com/android/server/pm/PackageInstallerService.java @ android-17.0.0_r1
- type: aosp
  path: frameworks/base/services/core/java/com/android/server/pm/PackageInstallerSession.java @ android-17.0.0_r1
- type: aosp
  path: frameworks/base/services/core/java/com/android/server/pm/DeletePackageHelper.java @ android-17.0.0_r1
- type: aosp
  path: frameworks/base/services/core/java/com/android/server/pm/RemovePackageHelper.java @ android-17.0.0_r1
- type: aosp
  path: frameworks/base/services/core/java/com/android/server/pm/InstallPackageHelper.java @ android-17.0.0_r1
- type: aosp
  path: frameworks/base/services/core/java/com/android/server/pm/BroadcastHelper.java @ android-17.0.0_r1
- type: aosp
  path: frameworks/base/services/core/java/com/android/server/pm/LauncherAppsService.java @ android-17.0.0_r1
- type: aosp
  path: frameworks/base/services/core/java/com/android/server/pm/PackageManagerShellCommand.java @ android-17.0.0_r1
- type: aosp
  path: frameworks/base/services/core/java/com/android/server/wm/ActivityStarter.java @ android-17.0.0_r1
tags:
- android
- package-manager
- app-archiving
- storage
- launcher
- app-startup
related_chapters:
- '1.7'
- '4.1'
- '6.1'
- '8.2'
- '25.5'
- '16.1'
pipeline_stage: ready-to-publish
task6_state: reviewed
task9_state: reviewed
task2b_state: fixed
---

# 应用归档（App Archiving）机制与恢复性能

Android 15 把应用归档做成了平台能力；Android 17 延续并完善了这条链路。这里的“归档”不涉及压缩，也不等于换了名称的普通卸载，而是把应用包转换成一种可以恢复安装的状态：

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
  ├─ PackageInstaller session 完成正常安装校验
  ├─ installed = true，清除 ArchiveState
  └─ ACTION_PACKAGE_ADDED 表示安装完成
```

恢复责任安装器是原本安装或更新该应用、现在负责重新取得 APK 的安装器。安装会话（session）则是一笔可提交、可报告状态的安装任务。这套机制主要解决磁盘空间与恢复体验问题。它会经过包删除路径并通常终止目标进程，但不属于低内存终止守护进程 `lmkd` 的内存回收策略。恢复过程还要先完成下载与安装，然后才能进入普通冷启动。

## 1. 四种容易混淆的状态

| 状态 | APK | 用户数据 | 桌面入口 | 恢复责任方 |
|---|---|---|---|---|
| 已安装 | 有 | 有 | 真实 Activity | 不需要恢复 |
| 已归档 | 可能已删除，取决于多用户状态 | 保留 | `ArchiveState` 合成入口 | 恢复责任安装器 |
| 卸载但保留数据 | 通常无 | 保留 | 没有平台归档入口 | 没有标准恢复契约 |
| `installPackageArchived()` 创建的归档包 | 无 APK，只有归档元数据 | API 不负责生成业务数据 | 归档入口 | 指定安装器 |

最末行是 Android 15 同期加入的另一条特权 API。`PackageInstaller.installPackageArchived()` 使用 `ArchivedPackageInfo`，在没有 APK 的情况下登记包名、签名、入口等归档元数据，供系统级流程预先建立归档条目。它不是用户点击归档图标后的下载接口，也不能替代 `requestUnarchive()`。

## 2. 平台中的参与者

### 2.1 发起归档的一方

调用入口是 `PackageInstaller.requestArchive(packageName, statusReceiver)`，API 35 加入。调用者需要：

- `DELETE_PACKAGES`，通常只授予系统或特权组件；或
- `REQUEST_DELETE_PACKAGES`，没有静默删除资格时仍会进入用户确认。

SDK 注解只是第一层。服务端还会校验调用方软件包与 Binder UID 是否一致、是否具有跨用户权限，以及后续卸载策略。持有 `REQUEST_DELETE_PACKAGES` 不等于可以静默归档任意应用。

归档前可先调用 `PackageManager.isAppArchivable(packageName)`。它适合用于界面能力判断，但不承诺操作一定成功：设备策略、应用锁、用户限制、包状态变化或确认流程仍可能导致归档失败。

### 2.2 `PackageArchiver`

`PackageArchiver` 位于 `system_server` 的 Package Manager 侧，负责：

- 检查目标包是否满足归档条件。
- 在删除 APK 前生成并持久化 `ArchiveState`。
- 把归档请求转换成带特殊标志的卸载。
- 识别桌面启动器的点击是否指向归档入口。
- 建立恢复草稿会话，并通知恢复责任安装器。
- 把安装器返回的接受状态或错误转给桌面启动器或 API 调用者。

它不负责下载 APK，也不负责应用首帧。

### 2.3 桌面启动器

`LauncherApps` 会把归档应用作为可展示条目返回。AOSP 的 `LauncherAppsService` 根据 `ArchiveState` 合成 `ActivityInfo`，并保留原始 `ComponentName` 和标题，因此桌面仍能展示并点击这个入口。

默认兼容行为包括：

- 在图标上叠加云朵标记。
- 点击后显示恢复确认。

桌面启动器可通过 `LauncherApps.setArchiveCompatibility()` 关闭其中一项默认行为，但前提是自行提供等价的状态提示和恢复进度。否则，用户会把一次需要网络下载的恢复误认为普通启动卡死。

### 2.4 恢复责任安装器

恢复责任方按以下优先级选择：

```text
InstallSource.updateOwnerPackageName
        ↓ 为空
InstallSource.installerPackageName
```

正常应用路径在归档前会确认该安装器仍安装在目标用户中，并能接收明确指定接收方的 `Intent.ACTION_UNARCHIVE_PACKAGE`。找不到能够恢复应用的安装器时，目标包不应被归档。

## 3. 为什么必须先保存 `ArchiveState`

APK 删除后，系统不能再从应用清单和资源表中读取桌面入口 Activity、标题与图标。因此，`PackageArchiver.createAndStoreArchiveState()` 必须先完成以下工作：

1. 取得目标用户下的包状态。
2. 拒绝系统应用和已更新的系统应用。
3. 确认该用户当前安装了目标包。
4. 找到并验证恢复责任安装器。
5. 检查应用是否明确声明不参与归档（opt-out）。
6. 通过 `LauncherApps.getActivityList()` 取得至少一个桌面入口 Activity。
7. 保存每个入口的标题、原始组件名和图标。

Android 17 的 `ArchiveState` 包含：

- `activityInfos`：一个或多个原始桌面入口 Activity。
- `installerTitle`：负责恢复的安装器标题。
- `archiveTimeMillis`：归档时间。
- 每个 Activity 的标题、原始 `ComponentName`、普通图标路径和可选单色图标路径。

图标存放在用户的凭据加密（Credential Encrypted，CE）系统目录：

```text
/data/system_ce/<userId>/package_archiver/<packageName>/
```

这是系统保存的展示材料，不是应用数据目录。重新安装成功时，`InstallPackageHelper` 会清除 `ArchiveState`，`PackageArchiver.clearArchiveState()` 同时删除这批图标。

## 4. 归档实际走的是特殊卸载

状态准备完成后，Android 17 组合以下删除标志：

```text
DELETE_ARCHIVE | DELETE_KEEP_DATA
```

需要为所有用户归档时再加 `DELETE_ALL_USERS`。公开的 `requestArchive()` 默认只针对当前 `PackageInstaller` 所在用户；命令行的 `pm archive` 默认选择所有用户，测试时不要混用这两种语义。

两个删除标志的职责不同：

- `DELETE_ARCHIVE`：告诉删除与广播链路这是归档，不是普通卸载。
- `DELETE_KEEP_DATA`：保留包设置和用户数据，使后续安装可以恢复原有身份与数据。

归档仍会进入 `PackageInstallerService.uninstall()` 和 `DeletePackageHelper`。因此，设备管理员、禁止卸载策略、受保护包、应用锁等限制仍然生效。删除路径会冻结并通常终止目标包的进程；这与 `lmkd` 根据内存压力信号（PSI）和进程优先级分值（adj）终止进程是两套机制。

删除成功时，包移除广播会携带 `EXTRA_ARCHIVAL=true`，同时把 `EXTRA_REPLACING` 设为 `true`、`EXTRA_DATA_REMOVED` 设为 `false`。接收方由此可以把归档与删除应用数据的普通卸载区分开。

### 4.1 删除 APK 的多用户前提

APK 和原生库位于包级代码目录，可被多个 Android 用户共用；`installed` 与 `ArchiveState` 则按用户分别保存。Android 17 的删除逻辑因此分成两种情况。

#### 只归档一个用户，其他用户仍安装

系统只把当前用户标记为未安装并清理相关状态。代码目录继续保留，因为其他用户仍要运行同一份 APK。

此时能够稳定回收的是归档路径清理的缓存与代码缓存；不能把整个 APK 大小都计入收益。

#### 归档唯一仍安装的用户

如果没有其他用户安装该包，而且 Package Manager Service（PMS）没有因内部缓存策略保留未安装包，删除流程才会移除包级代码和资源。`PackageSetting` 因 `DELETE_KEEP_DATA` 继续存在，并携带归档状态。

更准确的容量模型是：

```text
单 user 归档收益
  = cache + code cache
  + 条件成立时的共享代码目录

共享代码目录可回收
  ⇔ 没有其他 user 仍安装该包
     且 PMS 不要求缓存该未安装包
```

因此，单用户归档时若共享代码目录仍被占用，实际收益可能只有缓存和代码缓存。

### 4.2 保留与清理的边界

| 对象 | Android 17 归档结果 | 说明 |
|---|---|---|
| 凭据加密（CE）/ 设备加密（DE）用户数据 | 保留 | 数据库、`SharedPreferences`、账号状态等可在恢复后继续使用 |
| 缓存 | 清理 | `FLAG_CLEAR_CACHE_ONLY` |
| 代码缓存 | 清理 | `FLAG_CLEAR_CODE_CACHE_ONLY` |
| ART 应用性能配置文件 | 删除路径会销毁 | 归档没有设置保留配置文件的标志 |
| APK / split APK / 原生库 | 条件性删除 | 受其他用户与 PMS 缓存策略影响 |
| 任意共享存储文件 | 没有“全部删除”保证 | 不应把归档当成外部文件清理器 |
| `ArchiveState` 与归档图标 | 保留 | 用于桌面启动器展示与恢复 |

“用户数据保留”不代表所有运行时加速材料都会保留。ART 应用性能配置文件记录常用代码路径，可帮助后续编译优化；它被清理后，即使账号和数据库仍在，恢复后的编译状态与首次启动性能也可能发生变化。

## 5. 桌面启动器如何把失败启动变成恢复请求

归档入口仍保存原始 `ComponentName`。桌面启动器点击后会照常调用 `startActivity()`，但 APK 已不可用，`ActivityStarter` 找不到 `ActivityInfo`。Android 17 在 `START_CLASS_NOT_FOUND` 分支中增加归档判断：

```text
aInfo == null
  └─ PackageArchiver.isIntentResolvedToArchivedApp()
       ├─ package 必须处于 archived 状态
       ├─ Intent 必须包含显式 component
       └─ component 必须匹配 ArchiveState 中的原始入口
```

只有三项都满足，系统才调用 `requestUnarchiveOnActivityStart()`。普通的类名写错、组件被移除或包完全卸载，仍按 `START_CLASS_NOT_FOUND` 处理，不会被归档逻辑误判。

### 5.1 谁能从点击路径发起恢复

Android 17 的实现允许：

- Shell 命令调用。
- 当前用户或工作资料所对应父用户的默认桌面启动器。
- 能解析带 `HOME` 类别 Intent 的其他桌面启动器应用。

源码方法注释仍写着 `default/Home Launcher or Shell`，但实现已放宽到其他桌面启动器应用。非默认桌面启动器即使有资格触发，也会强制显示恢复确认。

初次启动请求最终返回 `START_ABORTED`。目标 Activity 此时不存在，Window Manager 必须停止本次启动和动画，不能把它报告成成功。

## 6. 恢复链路有两条异步状态线

### 6.1 Android 框架先创建草稿安装会话

`PackageArchiver.requestUnarchive()` 会先验证：

- 目标包在该用户下处于归档状态。
- 调用方软件包与 UID 一致。
- 调用者声明或持有 `REQUEST_INSTALL_PACKAGES` / `INSTALL_PACKAGES`。
- 跨用户权限满足。

若需要用户确认，系统先通过 `STATUS_PENDING_USER_ACTION` 返回确认 Intent。确认通过后，Android 框架为恢复责任安装器创建草稿安装会话：

```text
MODE_FULL_INSTALL
appPackageName = 目标包
installFlags = INSTALL_UNARCHIVE_DRAFT | INSTALL_UNARCHIVE
```

重复点击时，系统会复用同一目标包的有效草稿会话；若恢复已在进行，符合配置的桌面启动器会打开会话详情，不会并行发起第二次下载。

### 6.2 系统向安装器发送显式广播

`system_server` 随后发送：

```text
Intent.ACTION_UNARCHIVE_PACKAGE
  ├─ EXTRA_UNARCHIVE_ID
  ├─ EXTRA_UNARCHIVE_PACKAGE_NAME
  └─ EXTRA_UNARCHIVE_ALL_USERS
```

广播使用 `setPackage(installerPackage)`，`Intent` 定义也要求明确指定接收方。系统给安装器一个临时后台执行窗口；Android 17 AOSP 常量为 120 秒。这是实现细节，并未规定下载必须在 120 秒内完成；安装器仍应尽快转入符合平台规则的前台执行或安装会话流程。

### 6.3 安装器的恢复契约

收到广播后，安装器需要：

1. 读取软件包名与 `unarchiveId`。
2. 判断账号、网络、可用包和空间。
3. 通过 `reportUnarchivalState()` 返回“可开始”或具体错误。
4. 创建完整安装会话，在 `SessionParams` 中设置目标包与 `unarchiveId`。
5. 写入基础 APK 并提交会话。
6. 让标准 PackageInstaller / PMS 安装链路完成签名、版本、策略和包扫描。

`unarchiveId` 把广播与安装会话关联起来。即使安装器没有设置它，Android 17 也会尝试按包名、安装器 UID 和用户复用草稿会话，但显式设置可以避免并发请求互相混淆。

`INSTALL_UNARCHIVE` 不是安装器可随意伪造的“跳过确认”开关。`PackageInstallerService` 会清除外部传入值，仅在目标已经归档、请求安装器与恢复责任安装器匹配时重新设置。它允许在恢复确认完成后跳过第二次安装确认，但不会跳过 APK 签名和正常安装校验。

### 6.4 安装完成不会自动重放第一次点击

- `UNARCHIVAL_OK` 只表示安装器能够开始恢复。
- 初次 `startActivity()` 已以 `START_ABORTED` 结束。
- Android 17 的 `PackageArchiver` 没有保存并自动重放原始启动 Intent。
- 安装完成通过 `ACTION_PACKAGE_ADDED` 或安装会话的完成状态观察。

桌面启动器或产品层可以展示下载进度，并在安装完成后让用户再次点击；某些设备厂商或安装器也可能额外提供“恢复后打开”，但那不是 AOSP `PackageArchiver` 的默认保证。

## 7. 正确理解三个回调

| 信号 | 表示什么 | 不表示什么 |
|---|---|---|
| `requestArchive()` 的 `EXTRA_STATUS` | 待用户操作、成功或失败；只有成功状态才表示归档删除完成 | 不代表一定回收了完整 APK 大小 |
| `requestUnarchive()` 的 `EXTRA_UNARCHIVE_STATUS` | 安装器是否接受请求，或为什么不能开始 | 不代表 APK 已安装 |
| 恢复安装会话成功，或收到对应的 `ACTION_PACKAGE_ADDED` | APK 已重新安装，归档状态已清除 | 不代表应用首帧已经完成 |

恢复链路可能给出以下状态：

- `UNARCHIVAL_OK`
- 需要用户操作
- 存储不足，并给出还缺多少字节
- 无网络
- 安装器被禁用或已卸载
- 通用错误

把 `UNARCHIVAL_OK` 当作安装完成，会让监控数据提前结束，也会让桌面启动器在 APK 仍不存在时再次尝试启动。

## 8. 恢复性能要拆成四段

从用户请求恢复到应用再次可用，总耗时可按下面四段计算：

```text
T_user_ready
  = T_framework_request
  + T_installer_prepare
  + T_download_and_install
  + T_next_launch
```

这四个名称是本文建议的观测指标，不是 Android 平台定义的公开常量。分段记录后，才能判断延迟来自系统请求、安装器准备、下载与安装，还是安装后的首次启动。

### 8.1 `T_framework_request`

包括 `ActivityStarter` 发现目标类不存在、匹配 `ArchiveState`、校验桌面启动器与确认策略、创建草稿安装会话，以及发送恢复广播。这些工作主要在 `system_server` 进程内完成，通常远短于网络和安装。如果这一段很慢，应优先检查 `system_server` 的锁竞争、Package Manager `Handler` 消息队列是否积压，以及安装会话的磁盘 I/O。

### 8.2 `T_installer_prepare`

包括安装器进程拉起、账号与授权检查、包版本选择、空间估算和状态上报。需要登录、付费校验或用户确认时，耗时没有固定上限。

### 8.3 `T_download_and_install`

包括网络下载与 split APK 选择、安装会话写入和提交、签名与版本校验、包扫描、权限状态恢复、`dexopt`/ART 编译优化，以及发送 `ACTION_PACKAGE_ADDED`。这通常是恢复的主要耗时。即使 `PackageArchiver` 很快返回，安装器和 PackageInstaller 仍可能出现少量耗时很长的尾部样本，两者要分别统计。

### 8.4 `T_next_launch`

恢复后的启动仍是普通应用冷启动：Zygote 创建应用进程、`bindApplication`、Provider、`Application`、Activity 与首帧都不会被归档机制跳过。

归档路径还会清理缓存、代码缓存和 ART 应用配置文件，因此首次启动可能比应用一直保留安装时的冷启动更慢。应用内置 Baseline Profile（预先列出的启动热点代码）并控制启动依赖和安装包体积，仍能帮助 ART 更早优化常用路径；但这不等于恢复后一定完成 AOT（安装前编译）优化。

## 9. 指标与观测

不要只报一个“恢复耗时”。至少拆成：

| 指标 | 起点 | 终点 | 主要责任域 |
|---|---|---|---|
| `T_archive_done` | 发起归档 | `requestArchive()` 返回成功 | PMS / `installd` / 存储 |
| `T_unarchive_accepted` | 点击或调用恢复 | `UNARCHIVAL_OK` | `system_server` / 恢复责任安装器 |
| `T_package_restored` | 点击或调用恢复 | 安装会话成功 / `ACTION_PACKAGE_ADDED` | 网络 / 恢复责任安装器 / PMS |
| `T_first_frame_after_restore` | 恢复完成后的启动 | 首帧完成 | 应用启动链 |

如果产品在一次点击后自动等待并打开应用，可以再定义“从点击到首帧”的整体指标，但要注明“自动打开”由哪一层实现。

### 9.1 Android 17 shell 验证

先对测试包和测试用户执行，避免误归档主账号中的应用：

```bash
adb shell pm archive --user current <package>
adb shell dumpsys package <package>
adb shell pm request-unarchive --user current <package>
adb logcat -s PackageArchiverService PackageManager PackageInstaller ActivityTaskManager
```

前三条命令依次发起归档、查看包状态并请求恢复；最后一条同时收集归档、安装和 Activity 启动日志，便于对齐各阶段时间。

如果要单独检查归档元数据，可以运行：

```bash
adb shell pm get-archived-package-metadata --user current <package>
```

该命令输出供 `install-archived` 使用的序列化十六进制元数据，不是便于直接阅读的状态摘要。`pm list packages -u` 只能说明 PMS 仍记录着这个未安装包，不能单独证明它拥有有效的 `ArchiveState`。

### 9.2 对齐系统轨迹

Perfetto 中至少同时观察：

- `system_server` 中 ActivityTaskManager / Package Manager 的工作。
- 恢复责任安装器的进程启动、网络请求和安装会话写入。
- `installd`、`dex2oat` / ART 的编译优化工作。
- 恢复完成后的目标应用进程与首帧。

测量磁盘收益时，要记录其他用户是否仍安装该包，并分别统计基础 APK、split APK、原生库、缓存、代码缓存与用户数据。忽略多用户条件，既可能把“只清了缓存”误报成归档失效，也可能把其他清理任务释放的空间计入归档收益。

## 10. 安全与策略边界

归档保留用户数据，因此恢复必须保持包身份连续性。Android 17 的关键约束是：

- 归档调用方的软件包名必须与 UID 匹配。
- 归档与恢复分别受删除、安装和跨用户权限约束。
- 恢复责任安装器由既有的 `InstallSource` 决定。
- 恢复广播只显式发送给该安装器。
- 草稿安装会话绑定安装器 UID、目标包和用户。
- `INSTALL_UNARCHIVE` 由系统重新判定，不能由普通安装器强行保留。
- 恢复 APK 继续经过标准安装、签名和版本校验。
- 设备所有者策略、工作资料策略、应用锁和用户限制仍可阻止操作。

当前 `PackageArchiver` 没有“归档专用 SDM 签名校验”分支。`.sdm` 是安装时可随 APK 一并处理的编译元数据文件；它或云端生成的编译材料如果参与安装，走的是 `PackageInstallerSession` 的通用能力。没有覆盖完整恢复流程的证据时，不应把这类材料写成归档恢复的强制步骤。

归档也不会为目标应用创建新的 SELinux 安全域。归档状态下没有可执行 APK 和可启动进程；恢复后，系统仍根据包身份、`seinfo` 安全标签和平台策略，把进程放入正常的应用安全域。

## 11. 版本边界

| 版本 | 平台能力 |
|---|---|
| Android 14 及以前 | 没有公开的平台级 `requestArchive()` / `requestUnarchive()`；应用商店可实现自己的归档方案 |
| Android 15 / API 35 | 引入平台归档 API、`ArchiveState`、`ACTION_UNARCHIVE_PACKAGE`、桌面启动器归档入口，以及只用元数据创建归档包记录的能力 |
| Android 16 / API 36 | 延续平台能力，并调整桌面启动器和安装会话的处理 |
| Android 17 / API 37 | 当前源码基准；以 `android-17.0.0_r1` 的多用户删除、草稿安装会话、用户确认和桌面启动器行为为准 |

Android 15 的“移除 APK 与缓存、保留用户数据”是 API 契约层的概括；Android 17 源码还表明，其他用户仍安装该包时，共享 APK 必须保留。

## 12. 常见误区

### 误区一：归档一定释放“安装大小”

不一定。多用户设备上，只要其他用户仍安装该包，就不能删除共享代码目录。应分别测量代码、缓存和用户数据。

### 误区二：归档就是 LMKD 杀进程

不是。它走包删除路径并会终止目标进程；触发原因和状态转换都属于 Package Manager，不是内存压力回收。

### 误区三：`UNARCHIVAL_OK` 表示应用已经恢复

不是。它只表示恢复可以开始；是否安装完成，要看安装会话状态或 `ACTION_PACKAGE_ADDED`。

### 误区四：系统会自动重放第一次点击

AOSP Android 17 没有这个保证。首次启动已返回 `START_ABORTED`。

### 误区五：`INSTALL_UNARCHIVE` 绕过安装安全

它只避免用户已经确认恢复后再次看到安装确认。系统会重新计算该标志，APK 仍要经过正常校验。

### 误区六：数据保留意味着性能状态完全保留

不成立。缓存、代码缓存和 ART 应用配置文件都可能被清理，恢复后的首次启动要单独测量。

## 13. 源码阅读索引

- [`PackageInstaller.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/content/pm/PackageInstaller.java)：公开的归档、恢复、状态上报和归档安装 API。
- [`PackageManager.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/content/pm/PackageManager.java)：`isAppArchivable()` 与 `getArchivedPackage()`。
- [`ArchivedPackageInfo.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/content/pm/ArchivedPackageInfo.java)：无 APK 归档安装所需的包、签名和入口元数据。
- [`Intent.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/content/Intent.java)：`ACTION_UNARCHIVE_PACKAGE` 与 `EXTRA_ARCHIVAL`。
- [`LauncherApps.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/content/pm/LauncherApps.java)：桌面启动器的兼容选项。
- [`PackageArchiver.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/services/core/java/com/android/server/pm/PackageArchiver.java)：归档状态、恢复请求、图标和安装器协议主线。
- [`ArchiveState.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/services/core/java/com/android/server/pm/pkg/ArchiveState.java)：归档状态数据模型。
- [`PackageInstallerService.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/services/core/java/com/android/server/pm/PackageInstallerService.java)：卸载确认、草稿安装会话、恢复安装标志与归档安装。
- [`PackageInstallerSession.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/services/core/java/com/android/server/pm/PackageInstallerSession.java)：恢复安装的用户确认与状态上报。
- [`DeletePackageHelper.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/services/core/java/com/android/server/pm/DeletePackageHelper.java)：单用户、全用户删除和代码目录回收条件。
- [`RemovePackageHelper.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/services/core/java/com/android/server/pm/RemovePackageHelper.java)：缓存、代码缓存、ART 配置文件与用户数据边界。
- [`InstallPackageHelper.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/services/core/java/com/android/server/pm/InstallPackageHelper.java)：恢复安装后清除归档状态。
- [`BroadcastHelper.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/services/core/java/com/android/server/pm/BroadcastHelper.java)：归档与安装广播携带的附加字段。
- [`LauncherAppsService.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/services/core/java/com/android/server/pm/LauncherAppsService.java)：为归档应用合成桌面启动器 Activity。
- [`PackageManagerShellCommand.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/services/core/java/com/android/server/pm/PackageManagerShellCommand.java)：`pm archive`、`request-unarchive` 和归档元数据命令。
- [`ActivityStarter.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/services/core/java/com/android/server/wm/ActivityStarter.java)：`START_CLASS_NOT_FOUND` 到恢复请求的切换。
- [Android 15 App archiving 官方说明](https://developer.android.com/about/versions/15/features#app-archiving)
- [PackageInstaller API](https://developer.android.com/reference/android/content/pm/PackageInstaller)
- [Launcher archive compatibility API](https://developer.android.com/reference/android/content/pm/LauncherApps.ArchiveCompatibilityParams)

## 小结

Android 17 的 App Archiving 可以概括为：

下图串起了归档、恢复请求和重新安装三个阶段：

```text
先保存可恢复入口
  → 用 DELETE_ARCHIVE | DELETE_KEEP_DATA 转换包状态
  → Launcher 展示归档入口
  → 点击后把恢复请求交给 responsible installer
  → 安装器通过普通 PackageInstaller session 恢复 APK
  → 安装成功后清除 ArchiveState
```

这条链路有三个容易混淆的边界：

1. 归档状态按用户保存，APK 却可能由多个用户共享。
2. `UNARCHIVAL_OK` 是“开始恢复”，不是“恢复完成”。
3. 归档保留业务数据，但会清理缓存和 ART 应用配置文件；恢复后的启动性能必须重新测量。
