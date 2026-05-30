---
title: Package Manager Service 与应用安装性能
chapter: '1.9'
section: '1.9'
status: "finalized"
drafted_date: '2026-04-05'
polish_count: 1
polish_date: '2026-04-09'
polish_by: task2b-polish
drafted_by: openclaw-task2a
reviewed_date: "2026-05-28"
reviewed_by: "openclaw-task6"
reviewed_at: "2026-05-28T17:18:00+08:00"
task6_result: "pass-light-edit"
task6_state: "reviewed"
task9_state: "reviewed"
pipeline_stage: "ready-to-publish"
applicable_versions: Android 10 (API 29) - Android 17 (API 37)
last_verified: '2026-04-18'
last_verified_against: AOSP android-16.0.0_r1 (`PackageManagerShellCommand` / `PackageInstallerSession.verifySdmSignatures` / `ArtManagedInstallFileHelper` / `ArtManagerLocal` / `DexOptHelper` / `ArtShellCommand` / `BackgroundDexoptJob`) + AOSP android-9.0.0_r1 `Installer.java` + Android Developers Baseline Profiles overview
confidence: medium
sources:
- type: aosp
  path: frameworks/base/services/java/com/android/server/SystemServer.java
- type: aosp
  path: frameworks/base/services/core/java/com/android/server/pm/PackageManagerService.java
- type: aosp
  path: frameworks/base/services/core/java/com/android/server/pm/Installer.java
- type: aosp
  path: frameworks/base/services/core/java/com/android/server/pm/PackageManagerShellCommand.java
- type: aosp
  path: frameworks/base/services/core/java/com/android/server/pm/PackageInstallerSession.java
- type: aosp
  path: frameworks/base/services/core/java/com/android/server/pm/InstallingSession.java
- type: aosp
  path: frameworks/base/services/core/java/com/android/server/pm/InstallPackageHelper.java
- type: aosp
  path: frameworks/base/services/core/java/com/android/server/pm/DexOptHelper.java
- type: aosp
  path: frameworks/native/cmds/installd/InstalldNativeService.cpp
- type: aosp
  path: art/libartservice/service/java/com/android/server/art/ArtManagerLocal.java
- type: aosp
  path: art/libartservice/service/java/com/android/server/art/ArtManagedInstallFileHelper.java
- type: aosp
  path: art/libartservice/service/java/com/android/server/art/ArtShellCommand.java
- type: aosp
  path: art/libartservice/service/java/com/android/server/art/BackgroundDexoptJob.java
- type: official
  path: https://developer.android.com/topic/performance/baselineprofiles/overview
- type: official
  path: https://source.android.com/docs/core/perf/vm
- type: blog
  path: 'Android Authority: Android 16 Cloud Compilation'
tags:
- android
- pms
- package-manager
- dex2oat
- dexopt
- baseline-profiles
- cloud-compilation
- app-installation
- compilation
task9_result: "pass-tech-review"
last_task9_at: "2026-05-28T17:29:00+08:00"
task9_reviewed_by: "openclaw-task9"
task9_reviewed_date: "2026-05-28"
last_task9_review_at: "2026-05-30T12:20:00+08:00"
task9_reviewed_by_current: "openclaw-task9"
last_task9_audit_date: "2026-05-30"
task2b_result: "fixed-lite"
task2b_state: fixed
last_task2b_at: "2026-05-30T11:36:00+08:00"
last_task2b_by: "openclaw-task2b-lite"
last_task2b_summary: "Task2B Lite: Added DeepResearch reference materials to sources section"
last_task2b_lite_at: "2026-05-30"
task6_state: "revisiting"
task9_state: "reviewed"
pipeline_stage: "ready-to-publish"
review_notes: '2026-05-01 task9 deep-review: needs-rework。P0/P1 技术问题已写入 queue。；2026-05-06 04 task6 re-review: pass-light-edit。L1/L2 小修 8 处；无新增 B 类回炉问题，等待 Task 9 复审。 | 2026-05-06 05 task9 deep-review: needs-rework。P0 2 / P1 1 / P2 2。P0/P1 已写入 queue，等待 Task2B。 | 2026-05-12 21 task6 review: needs-rework。已清理 frontmatter 重复字段；Android 16 云端编译/SDM 深度段与前文资料边界冲突，已加存疑标注并写入 queue。'
task9_review_notes: "2026-05-28 Task9 deep-review: needs-rework。P0 2 / P1 1；SDM 全称/文件归属、installd 版本边界和 Cloud Compilation 设备侧链路仍冲突，已合并 queue。 | 2026-05-28 17 Task9 deep-review: pass-tech-review。复核 SDM/.sdm、installd Binder、ART Service 与安装编译链路，无 P0/P1；Task6 已通过且 queue 无 pending，自动晋升 finalized。"
last_task6_at: "2026-05-28T17:18:00+08:00"
task6_reviewed_date: "2026-05-28"
last_task9_review_log: "logs/deep-review/2026-05-28-17-deep-review.md"
last_task2b_verifier_at: '2026-05-28T15:47:00+08:00'
task6_reviewed_by: "openclaw-task6"
last_task6_review_log: "logs/review/2026-05-28-17-review.md"
task6_review_notes: "2026-05-28 17:18 Task6 review: pass-light-edit。清理编辑痕迹与参考资料表述 3 处；outline 5/5 覆盖；无新增 L3/L4 回炉项，送 Task9 复审。"
task9_reviewed_at: "2026-05-28T17:29:00+08:00"
updated_by: "openclaw-task9"
updated_date: "2026-05-28"
---

# 1.9 Package Manager Service 与应用安装性能

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）
- [PMS 在系统架构中的位置](#pms-在系统架构中的位置)：`SystemServer.startBootstrapServices()` 中的启动位置，以及它为什么要早于大多数系统服务。
- [PMS 与 installd 的协作关系](#pms-与-installd-的协作关系)：`Installer`、`IInstalld`、`installd`、ART Service 在现代安装路径里的职责分工。
- [应用安装全流程与性能关键路径](#应用安装全流程与性能关键路径)：从 session 写入到状态发布，哪些阶段吃 CPU，哪些阶段吃 I/O。
- [Baseline Profiles 与安装时优化](#baseline-profiles-与安装时优化)：安装期编译覆盖、DEX 布局、首次启动收益如何落到实际行为上。
- [版本演进](#版本演进)：Android 10 到 Android 17 里，包管理、编译调度、OTA 优化各自怎么变。

### 导读
本节把 PMS 放回 `system_server` 的启动现场，再顺着 `PackageInstallerSession`、`InstallPackageHelper`、`Installer`、`IInstalld` 这几层往下看。我们关心的是安装阶段的真实执行位置、首次启动前已经做完了哪些准备、Trace 里每一段耗时该怎么归因。
<!-- outline-end -->


## 为什么要了解 Package Manager Service

当我们在 Perfetto 里分析冷启动时，经常会看到 `bindApplication`、类加载、page fault、`dlopen` 这些运行期事件。它们的耗时表现，往往受安装期已经做过的工作影响，比如 APK 扫描、签名校验、DEX 布局、dexopt 编译产物是否可用。`bindApplication` 负责进程绑定和应用运行时初始化；APK 签名校验、包扫描、安装期 dexopt 发生在更早的安装或开机扫描阶段。

另一个更直接的场景是安装和更新。用户看到下载完成，不等于应用已经可以流畅启动。设备端还要继续做 session 提交、包扫描、签名校验、数据目录准备、dexopt、状态发布等步骤。大型 APK、split 安装、低端闪存、首次 dexopt，都可能把这段时间拉长。

了解 PMS 和安装流程，我们就能回答这些问题：

- 安装耗时长，瓶颈在文件写入、签名校验，还是 dexopt？
- 首次冷启动慢，是否和安装期的编译策略、Baseline Profiles、DEX 布局有关？
- 系统 OTA 后，哪些应用需要重新校验或重新编译，用户为什么有时会看到“优化应用”变少？
- 在 Perfetto 里，应该去 `system_server`、`installd`、`PackageInstallerSession`、`dex2oat` 的哪一段找证据？

这篇文章从 PMS 的启动位置讲起，再把现代 Android 的安装提交路径拆开。重点放在三个地方：PMS 与 `installd` / ART Service 的职责边界、安装阶段的主要耗时点、安装期编译策略如何影响首次启动。

[图：应用安装流水线全景——从用户点击“安装”到应用可启动的完整时序]

## PMS 在系统架构中的位置

`PackageManagerService` 是 `system_server` 里的基础服务。AMS 负责进程和组件调度，WMS 负责窗口与显示，PMS 负责包、权限、组件声明、共享库、安装状态这些元数据。很多系统服务在启动时都要查询这些信息，所以 PMS 要比大多数服务更早就绪。

在「Android 16」的 `SystemServer.java` 里，`StartPackageManagerService` 出现在 `startBootstrapServices()`，随后调用 `PackageManagerService.main(...)`。它不在 `startCoreServices()`。启动顺序放得这么早，是因为 UserManager、Overlay、Permission、ContentProvider 解析、应用启动前的包查询都依赖 PMS 先把包状态准备好。

```text
SystemServer 启动阶段（简化）:
  startBootstrapServices()
    → ActivityManagerService
    → DisplayManagerService
    → Installer / DomainVerificationService
    → PackageManagerService
  startCoreServices()
    → BatteryService
    → UsageStatsService
  startOtherServices()
    → WindowManagerService
    → InputManagerService
```

PMS 初始化时要扫描 `/system/app/`、`/system/priv-app/`、`/product/app/`、`/vendor/app/`、`/data/app/` 等目录，解析 Manifest，校验签名，恢复 `packages.xml` 和每个包的持久化状态。首次开机、OTA 后首启、包量很多的设备，这一段在 `system_server` 里会非常显眼。android-16 源码中 PMS 开机扫描的并行路径：`InitAppsHelper.java` 的 `getApexScanPartitions()` / `scanSystemDirs()` 通过线程池（`ParallelPackageParser`）在多线程中处理。`ParallelPackageParser` 和 `mExecutorService` 并行扫描路径在「Android 13」到「Android 16」的源码中均已存在，不是「Android 16」首次引入。包数量多的设备上，并行扫描缩短了 PMS 初始化耗时。

[已验证: AOSP android-16.0.0_r1 `InitAppsHelper.java` parallel APEX scanning / `ParallelPackageParser`]

### PMS 管理的核心数据结构

PMS 在内存中维护了几个关键的数据结构：

- **PackageSetting**：每个已安装应用的持久化设置（安装时间、UID、权限授予状态、编译过滤器等），存储在 `/data/system/packages.xml`
- **PackageInfo**：从 APK 的 `AndroidManifest.xml` 解析出的完整包信息，包括声明的 Activity、Service、Provider、权限
- **AndroidPackage**：AOSP 中的内部接口，封装了对 APK 文件的只读访问，包括 DEX 文件列表、native 库、签名信息

这些数据结构是 PMS 服务整个系统的"数据库"。任何进程要启动一个应用、查询一个 ContentProvider、检查一个权限，最终都要通过 PMS 的这些数据结构来获取答案。

### PMS 与 installd 的协作关系

PMS 维护包状态和安装策略，具体落到文件系统和应用数据目录的操作由 `Installer` / `installd` 完成。从 `android-9.0.0_r1` 到 `android-16.0.0_r1`，`Installer.connect()` 都通过 `ServiceManager.getService("installd")` 获取 Binder 服务，再用 `IInstalld.Stub.asInterface(...)` 发起远程调用。本节不把 `installd` Binder 化写成 Android 16 的版本断点。

现代安装路径里，dexopt 的控制面和执行面还要再拆一层：

- PMS / `InstallPackageHelper`：包扫描、签名校验、权限与组件注册、安装状态提交
- `DexOptHelper`：基于安装原因、Profile 可用性和包状态，决定是否发起 dexopt
- ART Service（`ArtManagerLocal` / `ArtShellCommand` 所在服务）：接收 dexopt 请求，组织编译参数和任务调度
- `artd`：ART 的守护进程，负责把编译任务落到本机执行
- `dex2oat`：主要消耗 CPU 和 I/O 的工作进程，负责生成 OAT / VDEX 等编译产物
- `Installer` / `IInstalld` / `installd`：继续处理应用目录、权限、SELinux 上下文和部分编译产物相关的底层文件操作

因此，安装路径更适合按 `PackageInstallerSession -> InstallPackageHelper -> DexOptHelper -> ART Service -> artd -> dex2oat` 来看。`system_server` 里的 Slice 主要反映控制面决策，`dex2oat` 进程承接执行面里最重的编译开销。

[已验证: AOSP android-9.0.0_r1 到 android-16.0.0_r1 `Installer.java`; AOSP android-16.0.0_r1 `DexOptHelper.java` / `art/libartservice/service/java/com/android/server/art/ArtManagerLocal.java` / `ArtShellCommand.java`]

### Computer 模式与无锁读

Android 13 起引入 `Computer` 接口实现读写分离，到 Android 14 已成为 PMS 的核心架构模式。此前 PMS 的所有操作（包扫描、查询、安装、更新）都共享同一把全局锁（`mPackages`），查询操作会被写操作阻塞。

`Computer` 接口的工作方式是快照隔离：

- **写操作**（安装、更新、卸载）持锁修改活跃的 `Computer` 实例，修改完成后生成新的快照
- **读操作**（查询包信息、组件解析、权限检查）拿到的是快照引用，不与写操作竞争锁
- 每个读请求持有的快照在该请求完成前保持一致视图，不会被中间的写操作影响

这对性能分析有实际意义。在 Perfetto 中观察 PMS 活动时，如果看到 `PackageManagerService` 的查询 Slice（如 `getPackageInfo`）耗时较长，在 Android 14+ 的设备上，耗时较长通常是因为快照中需要遍历的数据量本身较大，或系统处于高负载状态。Android 13 及以下则仍然可能出现读写锁竞争导致的查询延迟。

[已验证: AOSP android-14.0.0_r1 `frameworks/base/services/core/java/com/android/server/pm/Computer.java` / `PackageManagerService.java` 的 `mComputer` 字段]

## 应用安装全流程与性能关键路径

了解 PMS 的架构位置后，可以继续看一个应用从"用户点击安装"到"可以启动"经历的完整阶段。安装流程根据触发方式有所不同（adb install / Google Play / PackageInstaller），但核心流水线是一样的。

### 安装触发路径

安装入口看起来不同，收敛点都是 session 提交和包状态更新。

**adb install**：宿主机先把 APK 推到 `/data/local/tmp/` 一类的临时位置，设备侧 shell 再通过 `PackageManagerShellCommand` 执行 `install-create`、`install-write`、`install-commit`。adb 会一直等到 session commit 完成再返回。

**Google Play / 应用商店**：安装器 App 通过 `PackageInstaller` API 管理 session。对 split APK、staged install、多包安装，这条路径更常见。

**系统预装 / 开机扫描**：PMS 在系统启动或 OTA 后扫描预装目录，把镜像里的包注册进内存状态和持久化配置。它不走 `adb install` 的 shell 命令，但后续仍然要处理包解析、状态恢复、必要的 dexopt。

### 现代安装控制路径

以 `adb install` 为例，现代 AOSP 的入口在 `PackageManagerShellCommand`。它先创建 session，再写入 APK 或 split，提交时进入 `PackageInstallerSession.commit()`。session 封存后，`InstallingSession.installStage()` 把安装任务交给 PMS 侧逻辑；包扫描和状态提交主要在 `InstallPackageHelper`，dexopt 决策在 `DexOptHelper`，编译请求再交给 ART Service，由 `artd` 拉起 `dex2oat` 执行。Perfetto 里看到的 `system_server`、`artd`、`dex2oat`，分别对应这条链上的控制面和执行面。

这套 session 模型解决了两个实际问题。一个是 split APK、多包安装、staged install 都能共用同一套提交协议；另一个是“写入文件”和“正式生效”被拆成两个阶段，失败回滚、重试、后台安装都更容易做。

### 安装阶段分解

从性能分析角度，安装过程可以拆成六段。

**1. 传输与写入 session**

APK 从 USB、网络或本地来源写入 session。大包、split 多、闪存慢时，这一段会先被拉长。

**2. commit 与文件落位**

session commit 之后，安装器把 APK 放到 `/data/app/` 下的目标目录。这里主要看文件 copy / rename、fsync、校验和存储写入延迟。

**3. 包扫描与签名校验**

PMS 解析 `AndroidManifest.xml`、校验签名、检查 sharedUserId / 权限 / ABI / split 关系，再决定能否把这个包正式纳入系统状态。升级安装还要检查新旧签名和 `versionCode` 规则。

**4. APK 签名与流式校验**

APK v3 签名支持密钥轮转（key rotation，proof-of-rotation 机制），允许应用在签名密钥变更时保持更新链。Android 11 引入 APK Signature Scheme v4（merkle tree 签名，服务于增量/流式安装的 .idsig 文件），v4 需要与 v2/v3 配套使用。流式校验允许安装过程中增量验证 APK 块，而非一次性读入全部内容做校验。

在 Android 12+ 设备上，`IncrementalService`（`system/incremental_delivery/` / `frameworks/base/services/incremental/IncrementalService.cpp`）配合 v4 签名实现了按需解密和校验：应用安装后不必等所有文件完整写入，先完成校验的部分就可以被访问。在 Perfetto 中，可以通过 `android.incremental` 相关的 Trace 事件观察这一过程。当设备使用 Incremental FS（`/data/incremental/` 挂载点）时，文件访问会经过 `IncrementalService` 的 ioctl 路径，触发按块的签名校验。

这对大型游戏和应用商店的分发体验有直接影响：用户可以在"安装尚未完成"时就启动应用，已校验的部分可正常使用，未校验的部分按需下载和验证。

[已验证: AOSP `system/incremental_delivery/` / `frameworks/base/services/incremental/IncrementalService.cpp`]

**5. 应用数据目录与 native 准备**

`IInstalld` 负责应用数据目录、权限、SELinux 上下文、编译产物目录等底层操作。多用户设备在这里还会处理 user 维度的数据准备。

**6. dexopt 调度**

现代 Android 把编译决策更多放到 `DexOptHelper` / ART Service。有没有 Baseline Profiles、Cloud Profiles、设备是否空闲、当前安装原因是什么，都会影响这里选用的编译过滤器。对 Android 12+ 的常见安装路径，没拿到可用 profile 时通常只做 `verify`；更早版本还存在 quicken 等历史行为，细节见 §1.7。

**7. 状态发布与广播**

包状态写回 `packages.xml` 等持久化信息，PMS 更新内存结构，随后发出 `ACTION_PACKAGE_ADDED` 等广播，Launcher 和其他系统组件才能看到这个应用。

### 安装耗时分析方法

在 Perfetto 中分析安装耗时，可以关注以下 Track 和 Slice：

- **system_server 进程**：搜索 `PackageInstallerSession`、`installStage`、`commitPackagesLocked` 一类 Slice。这里看到的是安装控制面的提交、扫描和状态发布。
- **`artd` 进程**：ART Service 下发编译任务后的守护进程活动，适合用来判断 dexopt 是否真的启动。
- **`dex2oat` 相关进程**：编译耗时通常集中在这里，是安装期最重的 CPU 开销。
- **installd 进程**：应用目录准备、文件操作耗时。
- **I/O Track**：`ext4` / `f2fs` 的写入延迟、fsync 抖动。

查看编译状态时，不要再用不存在的 `cmd package compile --dump`。Android 14+ 更稳妥的做法是直接看 ART Service 或 PMS 的输出：

```bash
# 查看 ART 侧记录的编译状态
adb shell cmd package art dump com.example.app

# 查看包管理侧的 dexopt 摘要
adb shell dumpsys package dexopt
```

如果要排查 profile 文件，再看 `cmd package dump-profiles` 或 `cmd package snapshot-profile` 这一组子命令。`art dump` 和 `dumpsys package dexopt` 里的 `compilation_filter`、`reason`、ABI 维度输出，足够先判断这次安装落在哪条编译路径上。

[待补充：安装过程在 Perfetto 中的 Trace 截图，标注各阶段]

[已验证: AOSP android-16.0.0_r1 `PackageManagerShellCommand.java` / `PackageInstallerSession.java` / `InstallingSession.java`]

## dex2oat 编译对安装和启动的双重影响

安装时的 dex2oat 编译是一个"付出 vs 收获"的权衡：编译越多，安装越慢但运行越快；编译越少，安装越快但运行时依赖 JIT 热身。这组权衡是 Android 编译策略演进的核心驱动力。

### 安装时编译 vs 后台编译 vs 运行时 JIT

关于这三种编译方式的机制和演进历史，我们在 §1.7 中已有深入分析。这里从 PMS 调度的角度做一个快速梳理：

**安装时编译（install-time dexopt）**：安装提交阶段会根据可用 profile 和系统版本选择过滤器。Android 12+ 的常见路径里，没有可用 Baseline / Cloud / local profile 时通常只做 `verify`；较早版本还有 quicken 等历史差异，`speed-profile` 这个字符串本身不能单独说明编译覆盖。

**后台编译（bg-dexopt）**：设备空闲充电时，ART Service 通过 JobScheduler 触发的后台优化。使用设备上积累的 JIT Profile，以 `speed-profile` 级别编译热点方法。这是安装后的补充优化环节。

**运行时 JIT**：应用运行时即时编译热点方法，同时在后台收集 Profile 供后续的 AOT 编译使用。

从性能分析的角度，更关心的是应用当前处于哪种编译状态，冷启动路径上的方法有多少已经有 AOT 产物。查询时直接看 ART Service 或 PMS 的状态输出：

```bash
# 查看 ART 侧记录的编译状态
adb shell cmd package art dump com.example.app

# 查看系统里的 dexopt 摘要
adb shell dumpsys package dexopt

# 手动触发全量编译（调试用）
adb shell cmd package compile -m speed -f com.example.app

# 手动触发 profile 编译
adb shell cmd package compile -m speed-profile -f com.example.app
```

需要导出 profile 文件时，再看 `cmd package dump-profiles` 或 `cmd package snapshot-profile`。

### 编译模式的选择策略

系统对不同场景的编译模式选择是有策略的：

| 安装场景 | 默认编译级别 | 原因 |
|---------|------------|------|
| 首次安装（无可用 profile，Android 12+ 常见） | `verify` | 安装更快，首次启动更多依赖解释执行和 JIT |
| 首次安装（有 Baseline Profiles） | `speed-profile` | 安装即有 AOT 覆盖 |
| 首次安装（有 Cloud Profiles） | `speed-profile` | 聚合 Profile 覆盖更广 |
| 系统预装 | `speed` 或 `speed-profile` | OEM 配置决定 |
| OTA 后首次启动 | `verify` | 优先快速开机 |
| 后台空闲充电 | `speed-profile` | 使用本地 JIT Profile |
| 存储空间不足 | `verify` 或降级 | 节省存储 |

[已验证: AOSP frameworks/base/services/core/java/com/android/server/pm/, 编译策略; art/dex2oat/dex2oat_options.cc, 编译过滤器]

## Background Dexopt 策略与系统性能影响

后台 dexopt 是安装后补足编译覆盖的机制。安装时可能因为用户在等待完成而只做 verify；设备空闲充电时，系统才有足够时间做更深的编译。

### 触发条件

后台 dexopt（Android 14+ 由 ART Service 统一调度）在 AOSP 里的约束来自 `BackgroundDexoptJob.schedule()` 对 JobScheduler 的设置：

- **`setRequiresDeviceIdle(true)`**：设备处于 idle
- **`setRequiresCharging(true)`**：设备在充电。AOSP 这一层不区分有线和无线。
- **`setRequiresBatteryNotLow(true)`**：电量不处于 low battery 状态，不等于固定的 30% 阈值。
- **周期性任务**：Job 会按周期重新调度，不绑定固定的“凌晨 2-5 点”窗口。

夜间执行常见于用户长时间空闲充电的场景，这属于调度结果，不是 ART Service 固定写死的时间策略。OEM 可以在系统层叠加自己的限制条件，但那已经超出 AOSP 的默认语义。

### dexopt 对前台应用的影响

后台 dexopt 设计得尽量不影响前台体验，但仍然存在资源竞争：

**CPU 争用**：dex2oat 是 CPU 密集型操作，`dexopt.cpp` 通过 `setpriority(PRIO_PROCESS, 0, ANDROID_PRIORITY_BACKGROUND)` 将后台编译进程的 nice 值设为背景优先级，降低其 CPU 调度权重。在核心数量有限的设备上仍然可能抢占前台应用的 CPU 时间。

**I/O 竞争**：dex2oat 需要读取 DEX 文件、写入 OAT 文件，这些都是密集的文件 I/O。如果前台应用同时在读写存储（如加载图片、写入数据库），I/O 带宽竞争可能导致前台应用卡顿。

**内存压力**：dex2oat 编译过程中会占用相当数量的内存（用于编译中间表示），在内存紧张的设备上可能触发 LMK 杀后台进程。

手动触发后台 dexopt 的命令：

```bash
# 手动触发后台 dexopt（不检查充电/空闲条件）
adb shell cmd package bg-dexopt-job
```

[已验证: AOSP android-16.0.0_r1 `art/libartservice/service/java/com/android/server/art/BackgroundDexoptJob.java` / `ArtManagerLocal.java`]

## Baseline Profiles 与安装时优化

Baseline Profiles 让应用在安装时就能获得一部分 AOT 编译覆盖，不必等用户先运行几天再积累本地 profile。对首次启动敏感的应用，这会直接影响“安装完立刻打开”的体验。

### 安装流程中 Baseline Profiles 的工作方式

Baseline Profiles 从构建阶段就进入安装路径。开发者用 Macrobenchmark 录制关键路径，AGP 把 profile 元数据打进 APK 或 AAB；包安装提交后，Package Manager / ART 会把这些 profile 用到安装期 dexopt，让首发启动就拿到一部分 AOT 覆盖。

Android Developers 的《Baseline Profiles overview》给出的原始表述是：Baseline Profiles 可让应用从第一次启动开始，把代码执行速度提升约 30%。这对应的是安装期提前编译带来的收益，观察点落在编译产物是否已经准备好。

放到启动分析里，读法也要分清阶段。`bindApplication` 会消费这些编译产物，表现为类加载、page fault、OAT/VDEX 映射更顺；签名校验、包扫描、profile 驱动的 dexopt 发生在安装提交阶段。

### Startup Profiles 与 DEX 布局

Startup Profiles 作用在 DEX 布局。它们告诉构建工具哪些启动关键类应该更早放进主 DEX 的前部，减少启动期类加载时的随机 I/O 和 page fault。AGP 8.3 之后，这条路径已经是更成熟的主流配置。

同一篇官方概述页给出的表述是：Startup Profiles 会在 Baseline Profiles 的基础上，再带来约 15% 的启动性能提升，大应用的收益可能更高。在本章语境里，Baseline Profiles 影响安装期编译覆盖，Startup Profiles 影响启动期 DEX 布局。

[已验证: https://developer.android.com/topic/performance/baselineprofiles/overview]

## Android 16 云端编译与 SDM

公开资料把 Android 16 的一条安装优化路径称为 Cloud Compilation。AOSP 设备侧能确认的是 `.sdm` 文件进入安装会话后的校验、暂存和 ART 生命周期管理；Play 服务端如何生成产物、哪些设备和包会命中、命中后是否一定免除本机 `dex2oat`，公开源码还不能串起完整链条。

设备侧链路可以拆成三段：

- `PackageInstallerSession.maybeStageArtManagedInstallFilesLocked()` 会把与 APK 匹配的 ART-managed install files 暂存到目标路径。
- `PackageInstallerSession.verifySdmSignatures()` 对 `.sdm` 文件做签名校验。源码注释把 SDM 定义为包含 cloud compilation artifacts 的文件，并要求 `.sdm` 与 APK 使用同一签名密钥。
- `ArtManagedInstallFileHelper` 把 `.dm`、`.prof`、`.sdm` 都纳入 ART-managed install files，并按 APK 路径匹配对应文件；`ArtManagerLocal` 在删除 dexopt artifacts 时同时处理 VDEX、ODEX、ART、SDM、SDC 等产物。

后续分析统一把 SDM 写作 Secure Dex Metadata / `.sdm` cloud compilation artifact；无法在 AOSP android-16.0.0_r1 中对应到源码的全称和目录，不作为正文口径使用。

性能分析时要把源码证据和分发侧推断分开。能写成确定事实的是：安装会话可以接收并校验 `.sdm`，ART 侧能管理 SDM/SDC 等 cloud dexopt artifacts。不能写成定稿结论的是：Play Store 一定为目标包预生成 SDM、安装时一定免除本机编译、冻结窗口一定达到某个固定毫秒数量级。

抓 Play 安装 Trace 时，如果 `system_server` 仍有安装提交 Slice，但几乎没有明显的 `dex2oat` CPU 段，可以把它作为“可能命中云端产物”的线索，再对照安装来源、ART dump、`dumpsys package dexopt` 和包状态输出。没有 `.sdm` 或没有公开命中字段时，仍按常规本机 dexopt 路径排查。

[已验证: AOSP android-16.0.0_r1 `PackageInstallerSession.verifySdmSignatures()` / `maybeStageArtManagedInstallFilesLocked()`; `art/libartservice/service/java/com/android/server/art/ArtManagedInstallFileHelper.java`; `ArtManagerLocal.deleteDexoptArtifacts()`]

## App Archiving 机制（Android 15+）

Android 15 引入 OS 级 App Archiving，通过 `PackageArchiver`（`services/core/java/com/android/server/pm/PackageArchiver.java`）实现。归档后的应用移除 APK 和缓存文件，但保留用户数据，Launcher 显示灰显图标。

**ActivityStarter 拦截入口**（`ActivityStarter.java` 行 1155-1167）：当 `startActivity` 无法解析 Activity 类时（`err == START_CLASS_NOT_FOUND && aInfo == null`），若 `Flags.archiving()` 为 true，则调用 `PackageArchiver.isIntentResolvedToArchivedApp()` 检查 Intent 是否指向归档应用：

```java
if (isArchivingEnabled()) {
    PackageArchiver packageArchiver = mService
            .getPackageManagerInternalLocked()
            .getPackageArchiver();
    if (packageArchiver.isIntentResolvedToArchivedApp(intent, mRequest.userId)) {
        err = packageArchiver
                .requestUnarchiveOnActivityStart(
                        intent, callingPackage, mRequest.userId, realCallingUid);
    }
}
```

**isIntentResolvedToArchivedApp 逻辑**（PackageArchiver.java 行 377-400）：检查 Intent 的 component 是否在 `ArchiveState.getActivityInfos()` 中出现过。若是，`requestUnarchiveOnActivityStart()` 向应用的 installer（Google Play 等）发送 `ACTION_UNARCHIVE_PACKAGE` Intent，完成下载恢复。

**ArchiveState 数据结构**（`services/core/java/com/android/server/pm/pkg/ArchiveState.java`）：保存 `List<ArchiveActivityInfo>`（activity title、originalComponentName、iconBitmap）、`installerTitle`、`archiveTimeMillis`。

**与 LMK 的关系**：App Archiving 与 LowMemoryKiller 无直接关联。归档操作通过 `DELETE_ARCHIVE | DELETE_KEEP_DATA` 标志位移除 APK，data 目录保留，归档 App 不直接触发 LMK。

[已验证: AOSP mainline `PackageArchiver.java` / `ActivityStarter.java` / `ArchiveState.java`]

## 应用更新与 OTA 更新的性能影响

### 应用更新时的编译策略

应用更新时，PMS 需要处理版本升级和编译产物的更新。编译策略取决于更新前后的变化：

**增量更新（Delta Update）**：Google Play 支持增量更新，只下载 APK 中变化的部分。但编译方面仍然是全量重新编译——因为 DEX 文件可能整体变化（R8 混淆导致类名和方法索引变化）。增量编译在 ART 中有探索（如 dex2oat 的 incremental compilation），但尚未成为标准流程。

**全量更新**：删除旧版本的编译产物，重新运行 dex2oat。编译级别遵循与首次安装相同的策略（有 Profile 用 speed-profile，没有用 verify）。

更新耗时通常比首次安装短，因为系统已经有了该应用的 Profile（本地 JIT Profile 或 Cloud Profile），speed-profile 会实际编译有意义的方法。

### 系统 OTA 更新后的 mass dexopt

系统 OTA 更新是一个特殊的性能场景。OTA 更新可能改变了系统框架（framework.jar）、运行时（ART 模块）、或系统库，导致所有应用的编译产物失效——因为 OAT 文件中包含了编译时系统 API 的内联和优化，系统代码变了，这些优化可能不再正确。

**传统流程（Android 13 及以前）**：OTA 后首次启动时，系统对所有应用执行 mass dexopt，编译级别为 `verify`。用户在开机后会看到"正在优化应用 X/Y"的进度界面，这在大量应用的低端设备上可能需要很长时间。

**现代流程（Android 14+ ART Service）**：ART Service 的策略更加细分：

1. OTA 后首次启动，只对 primary DEX 文件做 `verify`，跳过 secondary DEX
2. 如果已有可用的 VDEX 文件且 verify filter 可以容忍依赖不匹配，则跳过编译
3. 不再在开机后立即运行后台 dexopt 补偿，避免与前台应用竞争

**A/B / Virtual A/B 更新**：这套方案逐步改善了 OTA 体验。更新可以在后台写入另一套分区，用户可见的停机时间更短；是否还会出现“优化应用”界面或后台补偿编译，仍取决于 Android 版本、ART 策略和设备实现，不能概括成某一个版本之后全部消失。

```bash
# 查看 OTA 后的编译状态
adb shell getprop pm.dexopt.boot-after-ota
# 通常返回 "verify"

# 手动触发全量 dexopt（调试用，慎用——可能耗时很长）
adb shell cmd package compile -m speed -f -a
```

[已验证: AOSP android-16.0.0_r1 `art/libartservice/service/java/com/android/server/art/ArtManagerLocal.java` / `BackgroundDexoptJob.java`]

## 在 Perfetto 中的表现与调试方法

前面讲了安装流程、编译策略、OTA 更新，这些理论知识在实际分析中需要对应到 Trace 中的具体位置。这些过程在 Perfetto Trace 中有明确的表现特征，可以据此定位问题。

### 安装过程的 Trace 特征

抓取安装过程的 Trace 需要一些技巧，因为安装涉及多个进程（adb → system_server → installd → dex2oat）。推荐的抓取方式：

```bash
# 在安装之前开始抓取
adb shell perfetto \
  -c - --txt \
  -o /data/misc/perfetto-traces/install-trace.pb \
<<EOF
buffers: {
    size_kb: 63488
}
data_sources: {
    config {
        name: "linux.ftrace"
        ftrace_config {
            ftrace_events: "sched/sched_switch"
            ftrace_events: "power/cpu_frequency"
            atrace_categories: "am"
            atrace_categories: "pm"
            atrace_categories: "dalvik"
            atrace_apps: "system_server"
            atrace_apps: "installd"
        }
    }
}
duration_ms: 60000
EOF
```

然后在另一个终端执行安装操作。Trace 中应该能看到：

- **system_server 进程**：`PackageInstallerSession`、`installPackage` 等 Slice
- **installd 进程**：文件操作相关的事件
- **dex2oat 进程**：作为子进程出现，CPU 使用率通常很高
- **I/O Track**：密集的文件写入

### dex2oat 活动的识别

dex2oat 在 Trace 中以独立进程的形式出现，进程名通常为 `dex2oat` 或 `dex2oat64`。关键特征：

- **CPU 占用高**：多线程并行编译，在 8 核设备上可能占满 4-6 个核心
- **内存占用**：编译过程中会分配数百 MB 的内存用于中间表示
- **I/O 密集**：读取 DEX 文件（数百 MB），写入 OAT 文件（可能跟原 DEX 一样大）
- **运行时间**：取决于编译级别和 DEX 大小，从几秒（verify）到几分钟（speed）

如果我们在 Trace 中看到 dex2oat 进程运行时间异常长，可以检查：

1. 编译级别是否过高（应该是 verify 或 speed-profile 而不是 speed）
2. 设备是否处于低内存状态（导致 dex2oat 被迫使用更少线程）
3. 存储性能是否正常（eMMC 设备上 I/O 可能是瓶颈）

### 后台 dexopt 在 Trace 中的特征

后台 dexopt 通常在凌晨用户不用手机时运行。在 Trace 中的特征：

- **JobScheduler** 触发的 `bg-dexopt-job`
- **dex2oat 进程**以较低的 CPU 优先级运行
- **批量执行**：对所有需要优化的应用逐个编译
- **可中断**：用户点亮屏幕后，dexopt 会被中止

### 常用的调试命令

```bash
# 查看单个应用在 ART 侧的编译状态
adb shell cmd package art dump com.example.app

# 查看所有应用的编译状态摘要
adb shell dumpsys package dexopt

# 手动为应用设置编译级别
adb shell cmd package compile -m speed-profile -f {package_name}

# 手动触发后台 dexopt
adb shell cmd package bg-dexopt-job

# 查看 installd 的日志
adb logcat -s installd

# 查看 dex2oat 的详细日志
adb shell setprop persist.sys.dex2oatlog 1

# 分析 OAT 文件内容（查看哪些方法被编译了）
adb shell oatdump --oat-file=/data/app/~~xxx/{pkg}-xxx/oat/arm64/base.odex | head -100

# 分析 Profile 文件内容
adb shell profman --dump-profile-file=/data/misc/profiles/cur/0/{pkg}/primary.prof
```

[待补充：安装过程和后台 dexopt 在 Perfetto 中的 Trace 截图]

## 与其他机制的关系

Package Manager Service 与全书多个章节有交叉：

- **§1.7 ART 编译管线与 dex2oat 优化**：dex2oat 的编译机制、编译级别、Profile 体系的详细说明。本节聚焦 PMS 如何调度 dex2oat，§1.7 聚焦 dex2oat 本身的工作原理
- **§1.8 Activity Manager Service**：AMS 启动 Activity 时需要从 PMS 获取 PackageInfo 和组件信息，PMS 的响应速度直接影响启动延迟
- **§8.2 App 启动全流程**：冷启动时 `bindApplication` 会消费安装期已经准备好的 OAT/VDEX/DEX 布局结果；签名校验和包扫描不在这一步发生
- **§8.3 启动优化策略**：Baseline Profiles 和 Startup Profiles 是启动优化的关键手段，配置方法详见该节
- **§4.3 ART 虚拟机内存管理**：dex2oat 编译过程的内存占用和 JIT 代码缓存在 ART 的内存预算中

## 版本演进

| 版本 | 包管理与编译变化 | 性能影响 |
|------|----------------|---------|
| Android 7.0 | 混合编译模式（JIT + Profile-Guided AOT） | 安装速度显著加快，不再需要安装时全量 AOT 编译 |
| 「Android 8.0」 | 后台 dexopt 改由 JobScheduler 调度 | 更智能的后台编译时机 |
| Android 9.0 | 引入 Cloud Profiles（dex metadata） | 安装时有更全面的 Profile 覆盖 |
| Android 10 | APEX / Mainline 基础设施引入，OTA 与 ART 更新开始解耦 | 后续 OTA 优化和 Virtual A/B 路径有了继续演进的基础 |
| Android 12 | ART 模块化（Mainline） | 编译优化可通过 Play 系统更新推送 |
| Android 13 | `Computer` 接口引入 PMS 读写分离 | 并发查询不再被写操作阻塞 |
| Android 14 | ART Service 取代直接 dex2oat 调用 | 编译管理更统一，后台 dexopt 更智能 |
| Android 16 | android-16 源码中可见 APEX 模块并发解析路径（并行扫描框架在更早版本已存在）；安装会话可处理 `.sdm` ART-managed install files，并校验其签名与 APK 一致 | 命中云端产物时可能减少本机 dexopt；Play 生成和命中条件需用安装来源、Trace 与 ART 状态交叉验证 |
| Android 17 | static final 不可变 → 更激进的常量折叠 | 编译优化深度提升（与 §1.7 交叉） |

## 常见问题与误区

**误区一："安装越快越好，后台慢慢编译就行"**

后台 dexopt 需要设备空闲+充电。用户安装完立刻使用的场景下，在后台编译完成之前，应用完全依赖解释执行和 JIT。对于不经常充电或充电时不空闲的用户（比如睡前充电但手机闹钟在用），后台 dexopt 可能很久都不会执行。这就是 Baseline Profiles 存在的意义——确保安装时就有编译覆盖。

**误区二："dex2oat 没用，JIT 够了"**

JIT 在运行时动态编译，理论上可以覆盖更多热点方法。但 JIT 有两个限制：第一，首次执行的方法都是解释执行，冷启动路径上全是"首次执行"；第二，JIT 编译有运行时开销（占用应用主线程或 JIT 线程的 CPU 时间）。AOT 编译的优势在于零运行时开销——代码已经编译好了，直接执行机器码。

**误区三："安装慢是 PMS 的问题"**

安装慢最常见的瓶颈是 dex2oat 编译和文件 I/O。PMS 解析 Manifest、管理权限这些操作通常在几百毫秒内完成；分析安装性能时，应该先看 dex2oat 进程的 CPU 时间和 I/O 延迟，再回到 PMS Slice 判断控制面是否异常。

**误区四："OTA 后所有应用都要重新全量编译"**

从 Android 14 开始，ART Service 在 OTA 后只做 `verify` 级别的编译，而且如果已有可用的 VDEX 文件且 verify filter 可以容忍依赖不匹配，则完全跳过编译。OTA 后首次启动阶段减少了全量编译等待。

**误区五："dumpsys package dexopt 显示 speed-profile，说明应用编译得很好"**

`speed-profile` 只是编译级别，不代表实际编译了多少方法。对 Android 12+ 的常见安装路径，没有可用 profile 时它往往会退到 `verify`；更早版本还要看 quicken 等历史行为。要确认真实覆盖率，仍然要结合 `oatdump` 或 `profman`。

## 参考资料
### 延伸调研
- OEM 厂商定制安装优化路径分析（vivo Turbo / 小米 HyperOS）：`/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/DeepResearch/2026-05-24-oem-install-optimization-vivo-xiaomi.md`。对比 AOSP 标准安装链路与 vivo Turbo / 小米 HyperOS 厂商定制安装优化路径，包含编译过滤器决策表、`installd` 改造机制、云编译 `.dm` 集成方式及厂商差异化策略分析。
- Android 16 installd Binder 化与 dexopt 链路：`/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/DeepResearch/2026-05-28-android-16-dexopt-chain-installd-service-binder.md`。详细分析 installd 从 Unix Domain Socket 切换到 Binder 服务的源码实现，包含 ServiceManager 注册机制、DexoptCommand 处理链和 dex2oat 子进程执行细节。
- Android 16 云编译与 SDM 机制：`/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/DeepResearch/2026-05-28-android-16-cloud-compilation-sdm-mechanism.md`。深入分析 Play 侧云编译与设备端 SDM (Secure Dex Metadata) 产物管理的源码实现，包含 ART Service 产物管理体系和云端编译产物签名验证机制。
- 厂商安装优化路径实机验证（vivo vs 小米）：`/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/DeepResearch/2026-05-28-oem-install-optimization-vivo-xiaomi-verification.md`。对比 vivo Turbo 和小米 HyperOS 在编译过滤器选择、installd 扩展命令和云编译集成方面的差异化实现，包含实机验证数据和源码对比。


### AOSP 源码路径
- `frameworks/base/services/java/com/android/server/SystemServer.java`：`StartPackageManagerService` 所在启动阶段
- `frameworks/base/services/core/java/com/android/server/pm/PackageManagerService.java`：PMS 主实现
- `frameworks/base/services/core/java/com/android/server/pm/Installer.java`：`IInstalld` Binder 客户端
- `frameworks/base/services/core/java/com/android/server/pm/PackageManagerShellCommand.java`：`adb install` 的 shell 入口
- `frameworks/base/services/core/java/com/android/server/pm/PackageInstallerSession.java`：session commit 与封存
- `frameworks/base/services/core/java/com/android/server/pm/InstallingSession.java`：`installStage()` 调度
- `frameworks/base/services/core/java/com/android/server/pm/InstallPackageHelper.java`：包扫描、校验、状态提交
- `frameworks/base/services/core/java/com/android/server/pm/DexOptHelper.java`：dexopt 调度
- `frameworks/native/cmds/installd/InstalldNativeService.cpp`：installd native 服务实现
- `art/dex2oat/`：dex2oat 编译器
- `art/libartservice/service/java/com/android/server/art/ArtManagerLocal.java`：ART Service 的本地调度入口
- `art/libartservice/service/java/com/android/server/art/ArtManagedInstallFileHelper.java`：`.dm` / `.prof` / `.sdm` ART-managed install files 匹配
- `art/libartservice/service/java/com/android/server/art/ArtShellCommand.java`：`cmd package art ...` 子命令实现
- `art/libartservice/service/java/com/android/server/art/BackgroundDexoptJob.java`：后台 dexopt 的 JobScheduler 调度

### 官方文档
- [Baseline Profiles 概述](https://developer.android.com/topic/performance/baselineprofiles/overview)
- [ART 与 Dalvik](https://source.android.com/docs/core/runtime)
- [ART 性能与虚拟机](https://source.android.com/docs/core/perf/vm)
- [dex2oat 编译选项](https://source.android.com/docs/core/runtime/dex2oat)
- [Profile-Guided 代码优化](https://source.android.com/docs/core/runtime/pgodexopt)
- [Package Manager API](https://developer.android.com/reference/android/content/pm/PackageManager)

### 深入阅读
- Android Authority: Android 16 Cloud Compilation（外部报道，适合补背景，不适合单独当作平台契约）
