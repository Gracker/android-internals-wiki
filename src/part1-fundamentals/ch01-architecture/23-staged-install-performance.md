---
title: Android Staged Install 与安装原子性性能
chapter: '1.23'
section: '1.23'
status: finalized
applicable_versions: Android 10 (API 29) - Android 17 (API 37)
last_verified: '2026-07-25'
last_verified_against: AOSP android-17.0.0_r1 (PackageInstaller / PackageInstallerSession / PackageInstallerService / PackageSessionVerifier / StagingManager / InstallPackageHelper / DexOptHelper / ART Service)
confidence: high
sources:
- type: official
  path: https://developer.android.com/reference/android/content/pm/PackageInstaller.SessionParams
- type: official
  path: https://developer.android.com/reference/android/content/pm/PackageInstaller.Session
- type: official
  path: https://developer.android.com/reference/android/content/pm/PackageInstaller.SessionInfo
- type: official
  path: https://source.android.com/docs/core/ota/apex
- type: official
  path: https://source.android.com/docs/core/ota/modular-system
- type: official
  path: https://source.android.com/docs/core/runtime/configure/art-service
- type: aosp
  path: frameworks/base/core/java/android/content/pm/PackageInstaller.java @ android-17.0.0_r1
- type: aosp
  path: frameworks/base/services/core/java/com/android/server/pm/PackageInstallerSession.java @ android-17.0.0_r1
- type: aosp
  path: frameworks/base/services/core/java/com/android/server/pm/PackageInstallerService.java @ android-17.0.0_r1
- type: aosp
  path: frameworks/base/services/core/java/com/android/server/pm/PackageSessionVerifier.java @ android-17.0.0_r1
- type: aosp
  path: frameworks/base/services/core/java/com/android/server/pm/StagingManager.java @ android-17.0.0_r1
- type: aosp
  path: frameworks/base/services/core/java/com/android/server/pm/InstallPackageHelper.java @ android-17.0.0_r1
- type: aosp
  path: frameworks/base/services/core/java/com/android/server/pm/DexOptHelper.java @ android-17.0.0_r1
- type: aosp
  path: frameworks/base/services/core/java/com/android/server/pm/dex/InstallScenarioHelper.java @ android-17.0.0_r1
- type: aosp
  path: art/libartservice/service/README.md @ android-17.0.0_r1
tags:
- package-manager
- staged-install
- apk-install
- atomicity
- performance
- dexopt
related_chapters:
- '1.9'
- '1.7'
- '1.20'
- '1.21'
- '1.27'
- '16.6'
pipeline_stage: ready-to-publish
task6_state: reviewed
task9_state: reviewed
task2b_state: fixed
last_consolidated_at: "2026-08-11"
consolidated_from:
  - "src/part1-fundamentals/ch01-architecture/1.45-staged-install-state-machine.md"
  - "src/part1-fundamentals/ch01-architecture/1.46-android17-staged-install-mechanism.md"
  - "src/part1-fundamentals/ch01-architecture/1.49-Android-17-Staged-Install-状态机-提交-恢复链路.md"
---
# 1.23 Android Staged Install 与安装原子性性能

Staged Install（分阶段安装，后文简称“分阶段安装”）经常被概括成“原子性更强的 APK 安装”，这种概括混淆了两个问题。

Android 的普通安装本来就有事务边界。Android 17 的 `InstallPackageHelper.installPackagesTraced()` 把安装组织为准备（Prepare）、扫描（Scan）、协调（Reconcile）和提交（Commit）；前三个阶段完成检查，Commit 才修改 Package Manager 的系统状态。多包安装会话（multi-package session）还可以把多个子会话作为一组提交。

分阶段安装处理另一类场景：某批更新不能在当前运行中的系统里立即激活，需要先完整验证，再跨过一次重启，让 APEX 与 APK 在新一次启动中以一致状态生效。APEX 是 Android 用于交付和更新系统模块的包格式。分阶段安装提供的是**跨重启激活协议**，并非为普通 APK 安装补充基础事务能力。

当前源码锚点为 Android 17 / API 37 / AOSP `android-17.0.0_r1`，同时保留 Android 10–16 的版本演进边界。

## 先分清三种“原子性”

| 层次 | 解决的问题 | Android 17 的主要实现 |
|---|---|---|
| 单次安装事务 | 包扫描、签名和依赖检查失败时，不提交一半 Package Manager 状态 | `InstallPackageHelper` 的 Prepare → Scan → Reconcile → Commit |
| 多包提交 | 多个子会话要么一起成功，要么一起失败 | `PackageInstaller.Session#addChildSessionId()` 与父会话 |
| 分阶段激活 | APEX、APK 或二者组成的更新需要在重启边界后统一生效 | `PackageSessionVerifier`、`StagingManager`、`apexd`、文件系统 checkpoint |

这三层可以叠加。一个分阶段父会话可以包含多个子会话，其中既有 APEX，也有 APK。此时既要满足多包同组提交规则，又要满足分阶段安装的跨重启状态机。

普通安装的原子性也有边界。`installPackagesTraced()` 要求可预见错误在 Commit 前被发现，并把系统状态修改集中到 Commit；但 `commitReconciledScanResultLocked()` 的源码注释同时警告，Commit 中抛出异常仍可能留下不一致状态。这是 Package Manager 的逻辑事务划分，不等同于数据库式或掉电安全的完整回滚。分阶段安装增加了持久化状态、`apexd` 协调和文件系统 checkpoint；checkpoint 是系统可在启动失败时放弃一组文件系统变更的恢复点。

## API 边界：谁能创建分阶段安装会话

`PackageInstaller.SessionParams#setStaged()` 从 Android 10 / API 29 开始提供。Android 17 中它仍是 `@SystemApi`，并要求 `android.permission.INSTALL_PACKAGES`。普通应用即使声明 `REQUEST_INSTALL_PACKAGES`，也不能因此获得分阶段安装能力。

调用 `setStaged()` 后，这个安装会话会被安排到下一次重启时安装。若它是多包安装的父会话，所有子会话都必须采用一致的分阶段安装属性；回滚（rollback）属性也有同样约束。任一子会话在激活时失败，整组都不能按部分成功处理。

另一个边界是免重启 APEX 更新。APEX 可以声明支持免重启更新（rebootless update），但这种 APEX 更新不属于分阶段安装会话。命令行使用 `--force-non-staged` 进入另一条路径。明确设置了 `staged` 属性的安装会话都要等待重启。

## Android 17 的完整状态机

### 提交后不会直接进入 StagingManager

实际路径比“`commit()` 调用 `StagingManager.commitSession()`”多出一整段验证：

```text
调用方
  └─ PackageInstaller.Session.commit()
       └─ PackageInstallerSession.commit()
            ├─ seal session，并持久化 sealed 状态
            ├─ 校验输入流，解析 APK / split
            ├─ Developer Verification（启用且适用时）
            ├─ 提取 native libraries
            └─ PackageSessionVerifier.verify(...)
                 ├─ 普通 APK 验证
                 └─ staged 专用的 pre-reboot verification
                      ├─ 检查活动 session / checkpoint 能力
                      ├─ 处理 rollback 冲突
                      ├─ 检查包名重叠
                      ├─ 向 apexd 提交并验证 APEX
                      └─ 标记 ready
                           └─ onVerificationComplete()
                                └─ StagingManager.commitSession(...)
```

`StagingManager.commitSession()` 接到的是已经完成当前验证流程的安装会话。它负责把会话纳入重启恢复管理；它不是 `commit()` 后的第一站，也不会替代前面的解析、Developer Verification 或 `PackageSessionVerifier`。

### `ready`、`applied`、`failed` 是三个持久化状态

`PackageInstallerSession` 使用三个布尔字段描述分阶段安装会话：

| 状态 | 含义 | 是否终态 |
|---|---|---|
| `isReady` | 重启前验证完成，可以进入下一次启动的激活流程 | 否 |
| `isApplied` | 更新已成功应用 | 是 |
| `isFailed` | 安装会话已失败，并保存错误码与错误信息 | 是 |

三者会以 `isReady`、`isApplied`、`isFailed` 属性写入 `/data/system/install_sessions.xml`。较大的会话数据存放在 `/data/system/install_sessions/`。`PackageInstallerService` 重启后从 XML 恢复状态，不依赖调用方重新提交。

对分阶段安装会话或 APEX 会话，`buildSessionDir()` 会把会话目录放在数据分区的暂存目录中，内部存储通常表现为：

```text
/data/app-staging/session_<sessionId>/
```

普通内部 APK 安装会话通常使用 `/data/app/vmdl<sessionId>.tmp`。这两个目录不能混写成同一种安装路径。

### 为什么先持久化就绪状态，再通知 apexd

`PackageSessionVerifier.endVerification()` 对包含 APEX 的分阶段安装会话规定了以下顺序：

1. `session.setSessionReady()`，让 Package Installer 先持久化 `ready` 状态。
2. `mApexManager.markStagedSessionReady(sessionId)`，再告诉 apexd 可以激活。

如果设备在第 1 步后、第 2 步前重启，`apexd` 没收到 `ready` 通知，不会激活这批 APEX；重启恢复阶段可以把安装会话判为失败。如果先通知 `apexd`、后写 Package Installer 状态，窗口期内重启就可能出现 APEX 已激活、APK 侧却不知道该继续哪个安装会话的不一致状态。

这段顺序直接展示了分阶段安装的原子性来源：持久化状态与 `apexd` 状态之间采用明确的提交次序，不能简化成一句“重启后提升状态”。

## 重启前到底检查什么

`PackageSessionVerifier.verifyStaged()` 的 Android 17 主线可以整理为五组检查：

1. **活动会话与 checkpoint 能力**：设备不支持文件系统 checkpoint 时，不能让多批分阶段安装会话同时处于活动状态。
2. **回滚冲突**：回滚会话与普通分阶段更新冲突时，回滚具有更高优先级。
3. **包重叠**：两批活动会话更新同一软件包时，系统根据提交顺序拒绝冲突的一方。
4. **APEX 提交与验证**：包含 APEX 时，向 `apexd` 提交会话，并继续检查 APEX 容器签名与包信息。
5. **建立 checkpoint 并转为 ready**：支持 checkpoint 的设备调用 `StorageManager.startCheckpoint(2)`，随后按前述顺序更新 Package Installer 与 `apexd` 的状态。

“重启前验证”（pre-reboot verification）不能简化成检查磁盘空间和签名。它还负责检查并发的分阶段安装会话、回滚、包重叠和 APEX 状态是否一致。

Developer Verification 位于安装会话的通用验证路径中，发生在分阶段安装专用验证之前。Android 17 设备若启用了相应服务，并且当前安装适用该策略，分阶段安装会话同样必须通过它。

## 重启后：APEX 先于 `system_server` 激活

设备启动时，`apexd` 会在 `system_server` 恢复 Package Installer 安装会话前验证并挂载 APEX。随后，`PackageInstallerService.restoreAndApplyStagedSessionIfNeeded()` 从持久化数据中找出满足以下条件的会话：

- 设置了 `staged` 属性；
- 已提交（committed）；
- 尚未应用，也没有失败；
- 没有父会话，或者本身是可恢复的顶层父会话。

如果子会话的父会话已经丢失，系统会直接把这个孤立的子会话标记为失败。筛选完成后，`StagingManager.restoreSessions()` 接手：

```text
开机早期
  ├─ apexd 验证并激活本次启动所需 APEX
  └─ PackageInstallerService 恢复 session XML
       └─ StagingManager.restoreSessions(...)
            ├─ 拒绝 boot_completed 之后的错误调用
            ├─ 检查 build fingerprint 是否变化
            ├─ 读取 supportsCheckpoint / needsCheckpoint
            ├─ 清理已销毁和悬空的 APEX session
            ├─ 对照 apexd session 状态
            └─ resumeSession(...)
                 ├─ 检查 APK-in-APEX 与重复包
                 ├─ 处理 rollback 用户数据快照
                 └─ installApksInSession(...)
                      └─ PackageInstallerSession.installSession()
                           └─ 普通 APK 安装事务
```

`restoreSessions()` 发现系统构建指纹（build fingerprint）与提交时记录不一致后，会让待恢复的安装会话失败。系统镜像已经改变，重启前完成的验证不能继续作为当前系统上的有效结论。

尚未就绪的安装会话不会被强行安装。Android 17 会把它移出本轮立即恢复集合，并在 `BOOT_COMPLETED` 之后重新触发验证。因此，本次开机通常不会应用该会话，系统也不会绕过检查继续安装。

## 文件系统 checkpoint 不等同于 Virtual A/B

`StagingManager` 通过 `StorageManager` 使用以下能力：

- `supportsCheckpoint()`：设备是否支持文件系统 checkpoint。
- `needsCheckpoint()`：当前启动是否仍处于需要提交或回退 checkpoint 的状态。
- `startCheckpoint(2)`：为分阶段激活建立 checkpoint。
- `abortChanges("abort-staged-install", false)`：失败时放弃变更并回到安全状态。

这些是文件系统 checkpoint 接口。Virtual A/B 设备可能同时使用快照和 checkpoint，但源码中的 `supportsCheckpoint()` 不能直接改写成“是否支持 Virtual A/B”。分析日志时应保留 API 的准确含义。

没有文件系统 checkpoint 时，系统不允许并行恢复多批分阶段安装会话，因为缺少覆盖多批系统变更的统一回退边界。

## 不同安装会话的恢复差异

| 类型 | 重启前 | 重启后 | 失败影响 |
|---|---|---|---|
| 仅 APK 的分阶段安装 | 完成通用验证与分阶段安装冲突检查 | `installApksInSession()` 进入普通 APK 安装事务 | 通常将当前会话标记为失败 |
| 仅 APEX 的分阶段安装 | 额外提交给 `apexd` 并验证 APEX | APEX 已在开机早期激活；随后完成状态检查 | 可能回退已激活的 APEX、放弃 checkpoint 并重启 |
| APEX 与 APK 混合安装 | APEX 与所有子会话作为一批验证 | 先确认 APEX 激活状态，再安装 APK 子会话 | APEX 失败会传播到同批及其他受影响的分阶段安装会话 |
| 多包 APK 安装 | 父会话管理多个子会话的一致提交 | 子会话按同一父会话的语义安装 | 任一子会话失败，不能把父会话视为部分成功 |

包含 APEX 且设备支持 checkpoint 时，`resumeSession()` 不会过早把 `apexd` 会话宣告为永久成功。会话 ID 会保留到 `PHASE_BOOT_COMPLETED`，届时 `markStagedSessionsAsSuccessful()` 才通知 `apexd`。本次启动能否进入开机完成阶段，也属于健康检查的一部分。

## 失败处理与回退边界

三个名字相近的操作负责不同层次的失败处理：

| 操作 | 作用 |
|---|---|
| `abortSession()` | 从 `StagingManager` 的内存集合移除记录，不等于系统级回滚 |
| `abortCommittedSession()` | 放弃已经提交但尚未重启的安装会话，并确保相关 APEX 会话被中止 |
| `abortCheckpoint()` | 记录分阶段安装失败原因、回退已激活的 APEX，并调用 StorageManager 放弃文件系统变更 |

仅 APK 的会话在重启后安装失败时，通常会调用 `setSessionFailed()` 并清理自己的暂存目录。包含 APEX 的失败影响更大：系统可能调用 `revertActiveSessions()`，再通过 checkpoint 回退；如果回退本身失败，还可能触发重启，以免系统继续运行在无法确认一致性的状态中。

恢复阶段若发现某个 APEX 会话已处于激活失败（activation failed）、状态未知（unknown）、已回退（reverted）、正在回退或回退失败等状态，会阻止相关会话继续应用。出现“一个 APEX 会话失败，其他分阶段安装会话也被标记失败”时，不应按普通 APK 的独立失败模型排查。

失败原因还会写入：

```text
/metadata/staged-install/failure_reason.txt
```

这份文件需要相应权限才能读取，在量产用户版本（user build）上不能假设 `adb shell` 一定可见。

## Android 17 的 dexopt 边界

旧实现常被描述为：Package Manager Service（PMS）调用 `installd`，`installd` 从 `run_dex2oat.cpp` 读取 `restore-dex2oat-threads`，再直接创建 `dex2oat` 进程。把这套描述用于 Android 17 的分阶段 APK 安装，会得到错误的性能模型。

Android 17 的应用安装 `dexopt` 已由 ART Service 负责。分阶段 APK 在重启后进入普通 APK 安装事务，`InstallPackageHelper` 准备 `dexopt` 请求，`DexOptHelper.performDexoptIfNeededAsync()` 再调用 `ArtManagerLocal.dexoptPackage()`。ART Service 通过 `artd` 管理编译请求和产物；底层仍可能运行 `dex2oat`，但调度入口已不再沿用 PMS → `installd` 的旧主线。

安装场景会映射为不同的编译原因（compilation reason），例如：

- `install`
- `install-fast`
- `install-bulk`
- `install-bulk-secondary`

`InstallScenarioHelper` 还会根据电池和温控状态调整批量安装策略。最终编译过滤器（compiler filter）受设备配置、安装参数、性能配置文件（profile）和 ART Service 策略共同影响，不能只看一个 `dalvik.vm.*dex2oat-filter` 属性下结论。

APEX 本身不会作为普通应用交给这条 `dexopt` 路径。在 APEX 与 APK 混合会话中，需要执行应用 `dexopt` 的是 APK 子会话。

安装时的 `dexopt` 采用尽力而为策略，也就是编译失败通常不会单独导致安装失败。Android 17 的 `DexOptHelper` 明确避免仅因 `dexopt` 步骤失败就让应用安装失败。因此：

- “安装会话失败”不能自动归因于 `dex2oat`；应先检查 Package Installer 保存的错误码和错误信息。
- `dexopt` 失败可能表现为安装后首次运行需要解释执行或等待后续编译，不一定触发分阶段安装回退。
- `INSTALL_FAILED_DEXOPT`、进程被杀或空间不足等日志必须和当前代码路径核对，不能拿旧版行为直接套用。

## 性能测量：分为三个时间窗口

分阶段安装会跨过一次重启，`commit()` 到 `isApplied()` 无法只靠一段连续的进程内计时或一份短 Perfetto 系统轨迹测准。因此，应分成三个窗口测量，并用持久化的会话 ID 与状态时间把结果关联起来。

### 窗口一：重启前提交与验证

关注以下工作：

- 安装会话数据写入和封存；
- APK 与 split APK 解析；
- Developer Verification；
- 原生库提取；
- 通用 APK 验证；
- 分阶段安装冲突与回滚检查；
- APEX 提交和验证；
- 建立 checkpoint 并持久化就绪状态。

这部分的结束条件是 `SessionInfo.isStagedSessionReady()`，不能以 `commit()` 返回为准。验证中包含异步步骤，调用方必须通过回调或查询安装会话状态，等待它进入 `ready` 或 `failed`。

### 窗口二：重启与开机早期

关注：

- 关机和重启本身；
- `apexd` 的 APEX 验证、激活与挂载；
- 文件系统 checkpoint 状态；
- `system_server` 启动到 Package Installer 开始恢复安装会话的时间。

这一段通常需要开机系统轨迹（boot trace），并同时保留 `apexd` 日志。只采集 `system_server` 启动后的 `atrace`，会漏掉 APEX 在开机早期已经完成的工作。

### 窗口三：`system_server` 恢复与 APK 安装

Android 17 源码中可直接依赖的系统轨迹名称包括：

- `restoreSessions`
- `installApksInSession`
- `installPackages`
- `dexopt`

前两个位于 `StagingManagerTiming`，后两个用于观察普通 APK 安装事务与 ART 编译。这里的 slice 是系统轨迹中的一段带起止时间的工作区间。先用精确名称查找，再展开它们的父子区间：

```sql
SELECT
  name,
  ts / 1e9 AS ts_s,
  dur / 1e6 AS dur_ms
FROM slice
WHERE name IN (
  'restoreSessions',
  'installApksInSession',
  'installPackages',
  'dexopt'
)
ORDER BY ts;
```

不要预设 `verifyPackage`、`collectCertificates`、`commitPackageSettings`、`relabel` 一定是稳定存在的 slice 名称。不同版本和厂商分支可能没有这些名称，应先在目标系统轨迹中确认，再编写 SQL。

查看 `artd`、`dex2oat`、`apexd`、`installd` 和 `system_server` 的 CPU 调度时间，可以使用下面的进程维度查询：

```sql
SELECT
  process.name AS process_name,
  SUM(sched.dur) / 1e6 AS cpu_ms
FROM sched
JOIN thread USING (utid)
JOIN process USING (upid)
WHERE process.name IN (
  'system_server', 'apexd', 'artd', 'dex2oat', 'installd'
)
GROUP BY process.name
ORDER BY cpu_ms DESC;
```

CPU 时间不能替代从开始到结束的墙钟时间。若 `dex2oat` 的 CPU 时间不高但对应区间很长，还要检查可运行态等待（runnable 延迟）、I/O 等待、温控降频和内存压力。

### 一次可复现的测量应记录什么

至少保存以下上下文：

1. 系统构建指纹、Android 版本与 AOSP 或厂商基线。
2. 父会话 ID 和所有子会话 ID。
3. 会话类型：仅 APK、仅 APEX、APEX 与 APK 混合，或多包安装。
4. APK/APEX 文件版本、大小、split APK 列表和签名方案。
5. 是否启用回滚、设备是否支持 checkpoint。
6. ART 编译原因、最终 compiler filter，以及 profile 是否存在。
7. 提交前系统轨迹、开机系统轨迹、恢复阶段系统轨迹和完整的 `logcat -b all`。
8. `isReady`、`isApplied`、`isFailed` 的状态变化时间。

跨设备比较时，应使用同一批安装文件、同一安装参数，以及相近的温控和电量条件。仅报告“安装总耗时降低 30%”而不说明时间窗口，通常没有可比性。

## 实战排障

### 安装会话一直不能变为 `ready`

先确认问题发生在重启前，而非设备已经重启、但会话尚未变为 `applied`：

```bash
adb shell pm list staged-sessions --only-parent
adb shell dumpsys package
adb logcat -b all -d | grep -E \
  'PackageInstallerSession|PackageSessionVerifier|StagingManager|apexd'
```

排查顺序：

1. `isFailed` 是否已经为 `true`；若是，直接读取保存的错误信息。
2. Developer Verification 是否仍在等待或已拒绝。
3. 是否与现有分阶段安装会话或回滚会话重叠。
4. 多包安装父会话下的子会话是否全部封存、提交，并且属性一致。
5. 含 APEX 时，`apexd` 提交、容器签名和包名检查是否通过。
6. `/data` 剩余空间是否足以写入暂存目录和后续安装产物。

不要把“提交命令已返回”当成 `ready`。命令行测试可使用 `--staged-ready-timeout` 等待 `ready` 或 `failed`；超时只说明等待窗口结束，不能自动证明系统死锁。

### 已经 `ready`，但重启后没有变为 `applied`

这类问题已经越过重启前验证，重点看恢复阶段：

```bash
adb shell pm list staged-sessions --only-parent
adb shell dumpsys apexservice
adb logcat -b all -d | grep -E \
  'StagingManager|PackageInstaller|ApexManager|apexd|checkpoint'
```

逐项确认：

- 本次启动的系统构建指纹是否与提交时一致。
- 是否出现 `restoreSessions` 与 `installApksInSession` 区间。
- StorageManager 是否报告正在返回安全状态（safe state）。
- `apexd` 会话是已激活或成功，还是激活失败或已回退。
- 安装会话是否已变为 `failed`，而调用方仍缓存旧的 `SessionInfo`。
- 尚未 `ready` 的会话是否被安排在 `BOOT_COMPLETED` 后重新验证，因而本次启动没有应用。

若 `restoreSessions` 完全没有出现，先确认采集是否覆盖 Package Installer 的恢复时段，再检查调用是否发生在 `sys.boot_completed` 已经为 `true` 之后。

### APK 安装阶段慢，怀疑 dexopt

先用 `installApksInSession`、`installPackages` 和 `dexopt` 的父子关系判断时间花在哪里，再看进程调度：

```bash
adb logcat -b all -d | grep -E \
  'DexOptHelper|ArtManagerLocal|artd|dex2oat|PackageManager'
adb shell df -h /data
adb shell pm art dump <package-name>
```

典型判断：

- `installPackages` 长、`dexopt` 短：优先看包扫描、签名、文件搬移和 Package Manager 锁等待。
- `dexopt` 的墙钟时间与 CPU 时间都长：检查 compiler filter、DEX 规模、profile 和 CPU 核心占用。
- `dexopt` 墙钟时间长但 CPU 时间少：检查调度等待、I/O、温控或内存压力。
- 日志显示 `dexopt` 失败但会话已经 `applied`：符合前述尽力而为边界，继续检查应用首次启动和后续后台 `dexopt`。

运行中的 `dex2oat` 进程可能很快退出，直接读取 `/proc/$(pidof dex2oat)/cmdline` 经常来不及取得内容。需要参数时，应优先保留 ART 日志和 Perfetto 的进程、线程元数据。

### 暂存空间不足

下面的命令分别查看数据分区空间、暂存目录大小和相关错误日志：

```bash
adb shell df -h /data
adb shell ls -lah /data/app-staging
adb logcat -b all -d | grep -E \
  'INSTALL_FAILED_INSUFFICIENT_STORAGE|PackageInstaller|StagingManager|apexd'
```

目录读取受系统构建类型和 SELinux 权限限制。看不到 `/data/app-staging` 不等于目录不存在，也不能因此排除空间问题。APEX 与 APK 混合会话还要结合 `apexd` 日志和 `dumpsys apexservice`；`/data/apex/active` 也不是 Package Installer 写入 APK 的暂存目录。

## 常用命令

以下命令适合工程机和测试环境；权限、可用参数会受系统构建类型影响：

```bash
# 创建 staged session
adb shell pm install-create --staged

# 创建 staged multi-package parent
adb shell pm install-create --staged --multi-package

# 提交，并等待 ready/failed；0 表示不等待
adb shell pm install-commit --staged-ready-timeout 60000 <session-id>

# 查看 staged session
adb shell pm list staged-sessions
adb shell pm list staged-sessions --only-ready
adb shell pm list staged-sessions --only-parent

# 在重启前放弃 session
adb shell pm install-abandon <session-id>
```

`pm install-create` 之后还要用 `pm install-write` 写入 APK，并在多包安装场景中把子会话加入父会话。具体脚本应检查每条命令的返回值和会话 ID，不要仅凭 `grep Success` 推测父子会话已经正确关联。

## 版本演进与当前结论

| 版本 | 需要记住的边界 |
|---|---|
| Android 10 / API 29 | `setStaged()`、分阶段 APEX/APK 安装与相关 `SessionInfo` 状态成为平台能力 |
| Android 11–13 | 分阶段安装、APEX、回滚与 checkpoint 继续演进；具体并发和回退策略要按对应源码标签核对 |
| Android 14–16 | ART Service 成为应用 `dexopt` 的主要管理层，不能继续沿用旧 PMS / `installd` 主线描述 |
| Android 17 / API 37 | 当前源码基准：Developer Verification 参与适用的安装会话验证；`StagingManager` 与 ART Service 行为按 `android-17.0.0_r1` 核对 |

回看任何旧版本问题时，都要同时锁定 Android 框架、ART 和 `apexd` 的版本。只把框架文件换成 Android 17，却继续引用旧 `installd` 的 `dexopt` 流程或旧 `apexd` 状态机，会得到跨版本混用的结论。

## 源码阅读入口

- `PackageInstaller.java`：`setStaged()`、多包安装约束、`SessionInfo` 的 `ready` / `applied` / `failed` API。
- `PackageInstallerSession.java`：会话封存、解析、Developer Verification、原生库提取、安装与状态持久化。
- `PackageInstallerService.java`：安装会话 XML、暂存目录和重启恢复入口。
- `PackageSessionVerifier.java`：通用验证、分阶段安装专用验证、checkpoint 与 APEX `ready` 顺序。
- `StagingManager.java`：重启恢复、`apexd` 状态核对、APK 安装、checkpoint 回退与开机完成后的成功确认。
- `InstallPackageHelper.java`：普通 APK 的 Prepare / Scan / Reconcile / Commit 事务。
- `DexOptHelper.java`、`InstallScenarioHelper.java`：Android 17 安装 `dexopt` 的 ART Service 入口和编译原因。
- ART Service README：`artd`、`dexopt` 与产物管理的系统边界。

## 参考资料

- [PackageInstaller.SessionParams](https://developer.android.com/reference/android/content/pm/PackageInstaller.SessionParams)
- [PackageInstaller.Session](https://developer.android.com/reference/android/content/pm/PackageInstaller.Session)
- [PackageInstaller.SessionInfo](https://developer.android.com/reference/android/content/pm/PackageInstaller.SessionInfo)
- [AOSP：APEX 文件格式与更新流程](https://source.android.com/docs/core/ota/apex)
- [AOSP：模块化系统组件](https://source.android.com/docs/core/ota/modular-system)
- [AOSP：配置 ART Service](https://source.android.com/docs/core/runtime/configure/art-service)
- [PackageInstaller.java @ android-17.0.0_r1](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/content/pm/PackageInstaller.java)
- [PackageInstallerSession.java @ android-17.0.0_r1](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/services/core/java/com/android/server/pm/PackageInstallerSession.java)
- [PackageInstallerService.java @ android-17.0.0_r1](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/services/core/java/com/android/server/pm/PackageInstallerService.java)
- [PackageSessionVerifier.java @ android-17.0.0_r1](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/services/core/java/com/android/server/pm/PackageSessionVerifier.java)
- [StagingManager.java @ android-17.0.0_r1](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/services/core/java/com/android/server/pm/StagingManager.java)
- [InstallPackageHelper.java @ android-17.0.0_r1](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/services/core/java/com/android/server/pm/InstallPackageHelper.java)
- [DexOptHelper.java @ android-17.0.0_r1](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/services/core/java/com/android/server/pm/DexOptHelper.java)
- [InstallScenarioHelper.java @ android-17.0.0_r1](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/services/core/java/com/android/server/pm/dex/InstallScenarioHelper.java)
- [ART Service README @ android-17.0.0_r1](https://android.googlesource.com/platform/art/+/android-17.0.0_r1/libartservice/service/README.md)
