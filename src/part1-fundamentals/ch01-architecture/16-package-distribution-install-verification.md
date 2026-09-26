---
title: 应用分发、安装验证与 PackageManager 性能
chapter: '1.16'
section: '1.16'
status: finalized
applicable_versions: Android 10 (API 29) - Android 17 (API 37)
last_verified: '2026-08-09'
last_verified_against: AOSP android-17.0.0_r1 + ACK android17-6.18-2026-06_r6 + Android Developers
confidence: high
sources:
- type: aosp
  path: frameworks/base/services/java/com/android/server/SystemServer.java @ android-17.0.0_r1
- type: aosp
  path: frameworks/base/services/core/java/com/android/server/pm/PackageManagerService.java @ android-17.0.0_r1
- type: aosp
  path: frameworks/base/services/core/java/com/android/server/pm/Computer.java @ android-17.0.0_r1
- type: aosp
  path: frameworks/base/services/core/java/com/android/server/pm/InitAppsHelper.java @ android-17.0.0_r1
- type: aosp
  path: frameworks/base/services/core/java/com/android/server/pm/ParallelPackageParser.java @ android-17.0.0_r1
- type: aosp
  path: frameworks/base/core/java/com/android/internal/pm/parsing/PackageParser2.java @ android-17.0.0_r1
- type: aosp
  path: frameworks/base/core/java/com/android/internal/pm/pkg/parsing/ParsingPackageUtils.java @ android-17.0.0_r1
- type: aosp
  path: frameworks/base/services/core/java/com/android/server/pm/PackageInstallerSession.java @ android-17.0.0_r1
- type: aosp
  path: frameworks/base/services/core/java/com/android/server/pm/InstallingSession.java @ android-17.0.0_r1
- type: aosp
  path: frameworks/base/services/core/java/com/android/server/pm/InstallPackageHelper.java @ android-17.0.0_r1
- type: aosp
  path: frameworks/base/services/core/java/com/android/server/pm/PackageSessionVerifier.java @ android-17.0.0_r1
- type: aosp
  path: frameworks/base/services/core/java/com/android/server/pm/StagingManager.java @ android-17.0.0_r1
- type: aosp
  path: frameworks/base/services/core/java/com/android/server/pm/Installer.java @ android-17.0.0_r1
- type: aosp
  path: frameworks/base/services/core/java/com/android/server/pm/DexOptHelper.java @ android-17.0.0_r1
- type: aosp
  path: frameworks/base/services/core/java/com/android/server/pm/PackageManagerShellCommand.java @ android-17.0.0_r1
- type: aosp
  path: frameworks/base/services/core/java/com/android/server/pm/PackageArchiver.java @ android-17.0.0_r1
- type: aosp
  path: frameworks/base/services/core/java/com/android/server/pm/pkg/ArchiveState.java @ android-17.0.0_r1
- type: aosp
  path: frameworks/base/services/core/java/com/android/server/wm/ActivityStarter.java @ android-17.0.0_r1
- type: aosp
  path: frameworks/base/services/incremental/IncrementalService.cpp @ android-17.0.0_r1
- type: aosp
  path: frameworks/base/core/java/android/util/apk/ApkSignatureVerifier.java @ android-17.0.0_r1
- type: aosp
  path: frameworks/native/cmds/installd/InstalldNativeService.cpp @ android-17.0.0_r1
- type: aosp
  path: art/libartservice/service/java/com/android/server/art/ArtManagerLocal.java @ android-17.0.0_r1
- type: aosp
  path: art/libartservice/service/java/com/android/server/art/ArtManagedInstallFileHelper.java @ android-17.0.0_r1
- type: aosp
  path: art/libartservice/service/java/com/android/server/art/PrimaryDexopter.java @ android-17.0.0_r1
- type: aosp
  path: art/libartservice/service/java/com/android/server/art/BackgroundDexoptJob.java @ android-17.0.0_r1
- type: aosp
  path: art/artd/artd.cc @ android-17.0.0_r1
- type: kernel
  path: kernel/common/fs/incfs/main.c @ android17-6.18-2026-06_r6
- type: kernel
  path: kernel/common/fs/incfs/vfs.c @ android17-6.18-2026-06_r6
- type: official
  path: https://source.android.com/docs/core/runtime/configure/art-service
- type: official
  path: https://source.android.com/docs/core/architecture/kernel/incfs
- type: official
  path: https://source.android.com/docs/security/features/apksigning
- type: official
  path: https://source.android.com/docs/security/features/apksigning/v4
- type: official
  path: https://developer.android.com/topic/performance/baselineprofiles/overview
- type: official
  path: https://developer.android.com/topic/performance/baselineprofiles/manually-create-measure
- type: official
  path: https://developer.android.com/topic/performance/startupprofiles/overview
- type: official
  path: https://developer.android.com/about/versions/15/behavior-changes-all#app-archiving
- type: official
  path: https://developer.android.com/developer-verification/guides
- type: official
  path: https://developer.android.com/developer-verification/guides/faq
- type: official
  path: https://developer.android.com/developer-verification/guides/limited-distribution
- type: official
  path: https://developer.android.com/reference/android/content/pm/PackageInstaller
- type: official
  path: https://developer.android.com/reference/android/os/Build.VERSION
- type: official
  path: https://developer.android.com/reference/android/os/Build.VERSION_CODES_FULL
- type: official
  path: https://developer.android.com/blog/posts/android-developer-verification-rolling-out-to-all-developers-on-play-console-and-android-developer-console
- type: aosp
  path: frameworks/base/core/java/android/content/pm/PackageInstaller.java @ android-17.0.0_r1
- type: aosp
  path: frameworks/base/core/java/android/content/pm/verify/developer/DeveloperVerifierService.java @ android-17.0.0_r1
- type: aosp
  path: frameworks/base/core/java/android/content/pm/verify/developer/DeveloperVerificationSession.java @ android-17.0.0_r1
- type: aosp
  path: frameworks/base/core/java/android/content/pm/verify/developer/DeveloperVerificationStatus.java @ android-17.0.0_r1
- type: aosp
  path: frameworks/base/services/core/java/com/android/server/pm/PackageInstallerService.java @ android-17.0.0_r1
- type: aosp
  path: frameworks/base/services/core/java/com/android/server/pm/verify/developer/DeveloperVerifierController.java @ android-17.0.0_r1
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
- type: aosp
  path: frameworks/base/services/core/java/com/android/server/pm/dex/InstallScenarioHelper.java @ android-17.0.0_r1
- type: aosp
  path: art/libartservice/service/README.md @ android-17.0.0_r1
- type: aosp
  path: frameworks/base/core/java/android/content/pm/PackageInstaller.java
- type: aosp
  path: frameworks/base/services/core/java/com/android/server/pm/PackageInstallerService.java
- type: aosp
  path: frameworks/base/services/core/java/com/android/server/pm/PackageInstallerSession.java
- type: aosp
  path: frameworks/base/services/core/java/com/android/server/pm/PackageSessionVerifier.java
- type: aosp
  path: frameworks/base/services/core/java/com/android/server/pm/InstallingSession.java
- type: aosp
  path: frameworks/base/services/core/java/com/android/server/pm/verify/developer/DeveloperVerifierController.java
- type: official
  path: https://developer.android.com/guide/app-bundle/app-bundle-format
- type: official
  path: https://developer.android.com/sdk/api_diff/37/changes/android.content.pm.PackageInstaller
- type: official
  path: https://source.android.com/docs/compatibility/17/android-17-cdd#4_application_packaging_compatibility
tags:
- pms
- package-manager
- package-installer
- art-service
- dexopt
- baseline-profiles
- incremental-install
- app-archiving
- android
- developer-verification
- app-signing
- security
- staged-install
- apk-install
- atomicity
- performance
- packageinstaller
- shortcutservice
- chooseractivity
- app-bundle
- distribution
related_chapters:
- '1.3'
- '1.5'
- '2.3'
- '3.1'
- '8.2'
- '1.9'
- '18.1'
- '26.5'
- '1.17'
- '18.5'
- '8.5'
- '24.1'
task6_state: reviewed
task9_state: reviewed
task2b_state: fixed
pipeline_stage: ready-to-publish
last_body_apply_at: '2026-08-06T11:15:29+08:00'
last_body_apply_run_id: 20260806-111529-1f9a01ff
last_review_finalize_at: '2026-08-06T12:07:15+08:00'
last_review_finalize_run_id: 20260806-120548-9b08ffcd
last_consolidated_at: '2026-08-24'
consolidated_from:
- src/part1-fundamentals/ch01-architecture/1.67-android17-packagemanager-architecture-performance.md
- src/part1-fundamentals/ch01-architecture/1.45-staged-install-state-machine.md
- src/part1-fundamentals/ch01-architecture/1.46-android17-staged-install-mechanism.md
- src/part1-fundamentals/ch01-architecture/1.49-Android-17-Staged-Install-状态机-提交-恢复链路.md
- src/part1-fundamentals/ch01-architecture/09-package-manager.md
- src/part1-fundamentals/ch01-architecture/21-developer-verification-install-boundary.md
- src/part1-fundamentals/ch01-architecture/23-staged-install-performance.md
- src/part1-fundamentals/ch01-architecture/27-android-app-distribution.md
---

# 应用分发、安装验证与 PackageManager 性能

安装一个应用需要经过一整套系统流程。系统要验证安装会话、解析包、校验签名、协调权限和共享库、准备应用数据、按策略执行 dexopt（DEX 优化流程，可能包括验证或预编译），最终才把新状态发布给系统其余部分。任何一个阶段变慢，都会延长用户看到“正在安装”的时间；如果编译产物或 Profile（记录重点类和方法的性能配置文件）没有按预期生效，影响还会延续到首次启动。

平台基线采用 AOSP `android-17.0.0_r1`；涉及增量文件系统（Incremental File System，IncFS）时，内核基线采用 Android 通用内核（ACK）`android17-6.18-2026-06_r6`。Android 10～16 只用于解释机制如何演进。

---

应用交付从制品生成开始，经过安装来源验证、PackageInstaller 会话、PMS 扫描与 dexopt，最后形成可启动的软件包状态。AAB、普通安装与 Staged Install 位于这条路径的不同边界，不能用同一个成功信号代替整条链路的完成。

按问题入口找对应部分：安装本身或 dexopt 变慢，看“PMS 扫描、解析与安装主路径”；安装被策略拦下，看“安装来源验证与权限边界”；更新要跨重启，看“Staged Install 的提交、重启与恢复”；问题出在商店侧的制品与下载，看“AAB 与 PackageInstaller 内容分发”。全文末尾汇总常见误区与结论。

## PMS 扫描、解析与安装主路径

### 先建立一张职责表

应用安装横跨多个进程。排查问题前，先确定观察的是负责决策、调度的控制面，还是实际完成文件操作与编译的执行面：

| 模块 | 所在进程 | 主要职责 | 不应归给它的工作 |
|---|---|---|---|
| `PackageInstallerSession` | `system_server` | 管理安装会话（session）、密封、校验、提交和结果回调 | 不直接解析全部包状态 |
| PMS / `InstallPackageHelper` | `system_server` | 扫描、协调签名与权限、处理包状态、提交安装结果 | 不直接运行 `dex2oat` |
| `Installer` | `system_server` | 充当 `installd` 的 Binder 客户端 | 不制定安装策略 |
| `installd` | 原生守护进程 | 处理应用数据目录、权限、标签及底层文件操作 | Android 14 及以上版本不负责组织整套 dexopt 策略 |
| ART Service / `artd` | `system_server` / 原生守护进程 | 组织和执行设备端 dexopt，管理编译产物 | 不发布 PackageManager 状态 |
| `dex2oat` | 独立原生进程 | 按 ART Service 给出的参数生成 OAT、VDEX 等 ART 编译产物 | 不判断包能否安装 |

Android 14 起，设备端 AOT（Ahead-of-Time，运行前编译）任务改由 ART Service 统一调度。PMS 中仍能看到 `DexOptHelper`，但它在安装流程中主要负责转交请求：根据安装状态发起编译，最终由 `ArtManagerLocal`、`artd` 和 `dex2oat` 组织并完成。若把 Android 17 的安装编译简单画成“PMS 调用 `installd` 做 dexopt”，就会遗漏实际的调度和执行位置。

---

### PMS 为什么在开机早期启动

`PackageManagerService` 运行在 `system_server`。它维护已安装包、组件、签名、权限、共享库和用户安装状态，是 Activity、Service、Provider 解析以及权限检查的基础数据来源。

Android 17 的 `SystemServer.startBootstrapServices()` 用名为 `StartPackageManagerService` 的 Trace 区段标记 `PackageManagerService.main(...)`。它位于引导（bootstrap）阶段，早于 `startCoreServices()` 和 `startOtherServices()`。许多服务启动时已经需要查询包和权限信息，因此 PMS 必须较早就绪。

开机初始化会处理两类信息：

- 从持久化设置恢复包、用户和权限状态；
- 扫描 APEX 系统组件包、系统分区和 `/data/app` 中的实际包，解析 Manifest 清单，并让磁盘状态与设置状态保持一致。

`InitAppsHelper` 负责组织系统目录和 `/data` 目录的扫描。`ParallelPackageParser.makeExecutorService()` 在 Android 17 固定使用 4 个 `package-parsing-thread` 工作线程，并设置前台线程优先级。这里的“并行”主要是包解析并行，不等于 PMS 初始化的每一步都可以并行；共享状态提交仍要遵守 PMS 的锁和阶段顺序。

#### 包信息不是一个对象

阅读 PMS 源码时，常见的几类对象处于不同层次：

- `AndroidPackage`：包解析后的内部只读视图，包含组件、权限、代码路径等声明信息；
- `PackageSetting`：系统持久化的安装状态，例如 appId、安装路径、签名和各用户状态；
- `PackageStateInternal`：供系统内部查询的包状态视图；
- `PackageInfo`：根据调用方权限、用户和查询标志位（flags）生成的公共 API 返回对象。

`getPackageInfo()` 因此并非从全局映射表（Map）中原样取出一个 `PackageInfo`。它要根据调用方可见性、用户状态和查询标志位生成结果；包数量、标志位组合和对象构造成本都可能影响查询耗时。

---

### `Computer` 快照解决了什么

Android 17 的 PMS 仍有多个锁，不能用“PMS 已经无锁化”概括：

- `mLock` 保护内存中的包解析结果与关联状态，源码明确要求持有时间尽量短；
- `mInstallLock` 保护对 `installd` 的访问，源码要求不要在持有 `mLock` 时再获取它；
- `mSnapshotLock` 只用于构造或取得 `Computer` 快照。

`snapshotComputer()` 会比较当前数据版本和缓存快照版本。版本一致时可直接返回缓存；缓存版本落后时，才在 `mSnapshotLock` 与 `mLock` 的保护下重建快照。若当前线程已经持有 `mLock`，它会返回基于当前可变数据的实时查询视图（源码中的 live computer），避免在写操作中产生前后矛盾的快照。

可以据此得到两个结论：

1. 大量只读查询不必每次都重新获取 PMS 的主锁并复制全部状态；
2. 查询变慢仍可能来自快照重建、对象生成、包可见性过滤、Binder 排队或其他锁竞争。

所以，Perfetto 中一次缓慢的 `getPackageInfo` 调用，不能只凭 Android 版本就排除锁竞争，也不能看到 `Computer` 就断言读请求完全无锁。应结合 Java 监视器锁竞争（monitor contention）、Binder 调度和对应线程的轨迹区段（slice）判断。

---

### 普通 APK 安装怎样提交

无论入口是 `adb install` 还是应用商店调用的 `PackageInstaller` API，普通安装最终都会进入安装会话模型。一个会话把一批待提交文件及其状态作为一次事务，可以包含主包（base APK）、拆分包（split APK）、安装元数据以及一个或多个子会话（child session）。

#### 1. 写入和密封安装会话

安装器先创建会话，再把文件写入暂存（staging）目录。`PackageInstallerSession.commit()` 不会直接修改 PMS 的包表；它先密封会话，防止内容继续被改写。

Android 17 中，密封后的处理大致是：

```text
PackageInstallerSession.commit()
  └─ seal
      └─ handleSessionSealed()
          ├─ 持久化 sealed 状态
          └─ handleStreamValidateAndCommit()
              ├─ 校验 root / child sessions
              └─ 发送 MSG_INSTALL
```

密封状态需要持久化。这样即使进程死亡或系统重启，系统仍能判断会话处于可恢复、已失败还是待安装状态。

#### 2. 进入安装请求

`InstallingSession.installStage()` 把任务发到 PMS 的 Handler 消息队列。`start()` 创建 `InstallRequest`；普通 APK 请求随后进入 `InstallPackageHelper.installPackagesTraced()`。

这个方法的源码注释把核心事务分成四个阶段：

1. **Prepare（准备）**：检查安装参数、替换关系、应用二进制接口（ABI，用于匹配处理器架构）、签名和已有包状态；
2. **Scan（扫描）**：解析待安装包，生成扫描结果；
3. **Reconcile（协调）**：让多个扫描结果与系统现有包、共享用户和签名规则保持一致；
4. **Commit（提交）**：在锁保护下提交包状态。

Android 17 的实际执行还包含路径切换、应用数据准备、异步安装 dexopt 与提交后的广播：

```text
prepareInstallPackages
  → scanInstallPackages
  → reconcileInstallPackages
  → renameAndUpdatePaths
  → prepareAppDataPostCommitLIF
  → performDexoptIfNeededAsync
  → commitPackages
  → post-install / package broadcasts
```

路径切换发生在 dexopt 前，因为 OAT、VDEX 等 ART 产物会关联最终代码路径。应用数据也要在编译前准备好。

`DexOptHelper.performDexoptIfNeededAsync()` 使用单线程执行器（executor）处理安装 dexopt，也就是同一时刻只处理一个任务。源码还明确规定，dexopt 失败不应导致应用安装失败：应用可以先以解释执行或较低优化级别运行，之后再由后台 dexopt 补齐优化。

#### 3. 哪些阶段消耗什么资源

| 阶段 | 主要资源 | 常见变慢原因 |
|---|---|---|
| 安装会话写入 | 存储 I/O | APK 大、拆分包多、闪存忙、增量块尚未到达 |
| 签名与完整性校验 | CPU + I/O | 文件大、证书轮换、v4/IncFS 数据等待 |
| Manifest 解析与扫描 | CPU + 内核页缓存 | 包或组件多、压缩数据读取慢 |
| 协调 | CPU + 锁 | 共享库、更新关系、共享用户或签名规则复杂 |
| 应用数据准备 | Binder + I/O | `installd` 排队、目录创建、SELinux 标签与存储压力 |
| dexopt | CPU + I/O | DEX 大、Profile 缺失、设备热限制、后台负载 |
| 提交与发布 | 锁 + Binder | 多包事务、观察者和广播接收端繁忙 |

诊断时不能只看总安装时长。安装会话写入缓慢与 `dex2oat` 执行缓慢，要分开排查。

---

### 签名校验与增量安装

#### APK 签名方案的分工

Android 17 仍同时支持多代 APK Signature Scheme：

- v1 以 JAR 条目为单位，兼容旧系统；
- v2 从 Android 7 引入，保护 APK 的整体内容；
- v3 从 Android 9 引入签名密钥轮换历史（lineage）；
- v4 从 Android 11 引入面向流式安装的 `.idsig` 文件，并与 v2/v3 一起使用。

v4 不是 v2/v3 的替代品。`.idsig` 用于让系统在 APK 尚未完整落盘时验证已读取的数据块；APK 的最终身份和完整性仍要满足相应的 APK 签名规则。

#### IncFS 按块提供数据，与“按需解密”无关

IncFS 允许应用在 APK 的全部数据块下载完之前开始安装或运行。用户态数据加载器负责提供缺失块，IncFS 则通过 Merkle 树（一种逐层校验数据完整性的哈希树）和签名元数据校验读到的数据块。

平台侧入口可在 `frameworks/base/services/incremental/IncrementalService.cpp` 看到；内核侧实现在 ACK `android17-6.18-2026-06_r6` 的 `fs/incfs/main.c` 与 `fs/incfs/vfs.c`。内核负责增量文件系统和缺块读取语义，不负责 PackageManager 的签名策略。

增量安装因此可以准确描述为“边下载，边提供并校验数据块”，其中没有“APK 按需解密”这一步。遇到 IncFS 安装卡顿，要同时观察：

- 数据加载器是否及时提供系统请求的数据块；
- 存储读取是否阻塞；
- `.idsig` 与 APK 签名是否有效；
- 应用启动所需的 DEX、资源或原生库（native library）数据块是否已经到达。

---

### 安装 dexopt 与 ART Service

#### 编译过滤器取决于设备配置

`pm.dexopt.<reason>` 用于在 Android 构建中为不同编译原因指定编译过滤器（compiler filter），它决定 ART 采用的优化级别。ART Service 文档给出的标准配置中，`bg-dexopt` 通常使用 `speed-profile`，多个开机相关原因使用 `verify`；产品配置可以覆盖这些值。

即使请求了 `speed-profile`，没有可用 Profile 时也不能假定系统一定进行完整 AOT。ART 会综合 Profile、磁盘空间、温度、现有产物和其他约束，选择实际可用的编译方式。分析设备行为时，应读取设备配置并检查实际产物，不能把某个默认值当成所有 Android 17 设备的保证。

#### Baseline Profile、运行时 Profile 与 Startup Profile

三者解决的问题不同：

| 类型 | 生成或提供者 | 主要用途 | 生效位置 |
|---|---|---|---|
| Baseline Profile（基准配置文件） | 开发者随应用交付 | 提前标记高价值类和方法，指导 AOT | 安装或后台 dexopt，取决于分发与设备路径 |
| Runtime Profile（运行时配置文件） | ART 根据实际运行采样 | 反映该设备上的热点代码 | 后台 dexopt |
| Startup Profile（启动配置文件） | 开发者提供给 R8/D8 | 调整 DEX 中启动代码布局 | 构建期，不属于 PMS 的设备端步骤 |

Baseline Profile 通常位于 APK 的 `assets/dexopt/baseline.prof`。安装渠道可以把 Profile 写入 DEX 元数据文件（例如 `base.dm`）并随 APK 交付；使用 `ProfileInstaller` 的应用也可以在运行后把 Profile 写到 ART 能读取的位置，再等待后台 dexopt。

不能笼统声称“只要 APK 带有 Baseline Profile，安装按钮结束前就一定完成 AOT”。Google Play、ADB、IDE、本地侧载（sideload，即绕过应用商店直接安装）以及 OEM 构建可以采用不同调度时机。判断时应检查设备上的 ART 状态和编译原因。

Startup Profile 容易与设备端编译混淆。它影响 R8/D8 在构建时如何把启动相关类和方法排布到 DEX 中，目的是减少启动时的缺页异常（page fault）和随机读取；设备上并不存在一个名为“Startup Profile 编译”的 PMS 阶段。

#### Android 17 中可用的诊断命令

查看单个包的 ART 状态：

```bash
adb shell pm art dump com.example.app
```

`PackageManagerShellCommand` 也支持把 `art` 子命令转交给 ART Service：

```bash
adb shell cmd package art dump com.example.app
```

强制按 `speed-profile` 请求编译，适合在可控测试设备上做前后对比：

```bash
adb shell pm compile -m speed-profile -f -v com.example.app
```

清理 Profile 后重新验证：

```bash
adb shell pm art clear-app-profiles com.example.app
```

手动运行后台 dexopt：

```bash
adb shell pm bg-dexopt-job
```

这类命令会改变设备编译状态。性能实验应记录执行前后的包版本、Profile 状态、编译过滤器、温度和电量条件，不能把人工编译后的结果与普通用户首次安装直接比较。

---

### 后台 dexopt 与 OTA

Android 14 及以上版本的后台编译由 ART Service 的 `BackgroundDexoptJob` 管理。标准调度通常每天一次，要求设备处于空闲（idle）且充电（charging）状态；设备退出空闲状态后，运行中的任务会被取消。厂商可以调整这些约束和策略。

ART Service 不再保留旧 PMS 模型中的开机后 dexopt 任务（post-boot dexopt job），从而避免刚开机时的编译任务与用户操作直接争抢资源。尚未完成的编译工作交给后台任务，在设备空闲、充电等条件满足时继续。

OTA 或 Mainline 模块化系统更新后，已有编译产物能否复用，取决于启动镜像（boot image）、类路径（classpath）、APEX 版本、编译依赖和产物校验结果。不能把 OTA 后的行为笼统概括成“所有应用重新编译”：

- 可继续验证并复用的产物不必重做；
- 失效产物可能先用 `verify` 或解释执行保证可用性；
- 更积极的 `speed-profile` 编译可以在后台逐步完成。

用户不再长时间看到“正在优化第 N 个应用”，并不代表编译成本消失；系统只是把更多工作安排成可验证、可复用和可延后的任务。

---

### `.sdm` / `.sdc`：Android 17 源码中的“云编译产物”

Android 17 固定 tag 中存在 `.sdm` 和 `.sdc`，但应按源码能够证明的范围描述。

`PackageInstallerSession` 的注释把 `.sdm` 说明为承载 cloud compilation artifacts（云编译产物）的文件。这里的“云编译产物”只是源码对这类可选优化输入的命名，不表示应用安装时必然联网编译。`ArtManagedInstallFileHelper` 把 `.dm`、`.prof` 和 `.sdm` 列为 ART 管理的安装文件；`.sdm` 文件名还要包含有效的指令集架构（ISA），例如 `base.arm64.sdm`。源码注释说明该格式从 Android 16 引入。

验证要求比普通附属文件更严格：

- 必须能找到对应 APK；
- 文件名中的 ISA 必须有效；
- APK 与 `.sdm` 至少使用 v3 签名；
- APK 和 `.sdm` 的签名必须精确匹配。

ART Service 的 `PrimaryDexopter` 会尝试为各 ABI（如 arm64）创建 `.sdc`。`artd.maybeCreateSdc()` 的行为说明了几个适用边界：

1. 没有 `.sdm` 是常见情况，不是安装错误；
2. 可复用 `.sdc` 需要匹配 `.sdm` 时间戳和相关 APEX 版本；
3. 一旦实际 dexopt 已完成，临时 `.sdm` / `.sdc` 可以被提前删除；
4. 删除 dexopt 编译产物时，ART Service 会把 ODEX、VDEX、ART、SDM 和 SDC 一并纳入管理。

`.sdm` / `.sdc` 是受签名与版本约束的可选优化输入，不是 Android 17 所有应用都必须经历的安装阶段。源码类名使用 `SecureDexMetadata` 相关命名，但没有必要自行扩展一个未经源码或官方文档定义的全称。

---

### 跨重启的分阶段安装与 APEX

普通 APK 安装会话通常在当前开机周期完成。`StagingManager` 处理的是必须重启后才能完成的分阶段会话（staged session），常见于 APEX（Android 用于交付和更新系统模块的包格式），或要求多包全部成功、否则全部撤销的原子系统更新。

`PackageSessionVerifier` 会执行所有会话共用的校验；对于分阶段会话，还要处理重启前验证、与 `apexd` 交互、检查点与回滚（checkpoint/rollback），以及 `ready`（就绪）、`applied`（已应用）、`failed`（失败）等状态。这些步骤共同组成一个跨重启事务：

```text
session committed
  → pre-reboot verification
  → mark ready
  → reboot
  → apply and verify
  → mark applied
      或失败后进入回滚/失败处理
```

只有部分 `PackageInstallerSession` 属于分阶段会话。使用安装会话 API 时，应先检查参数和包类型，再判断是否需要跨重启分析。

---

### 应用归档

Android 15（API 35）引入系统级应用归档（App Archiving），Android 17 延续了这套能力。归档与普通卸载的行为不同：

- APK 和缓存可以被移除；
- 用户数据被保留；
- 桌面启动器（Launcher）仍可展示归档入口；
- 用户点击后，由负责的安装器恢复归档应用。

Android 17 的 `PackageArchiver` 使用带 `DELETE_ARCHIVE` 与 `DELETE_KEEP_DATA` 语义的删除路径，并保存 `ArchiveState`。归档状态可包含可启动 Activity 信息、安装器标题和归档时间。`ActivityStarter` 遇到归档目标时，可以转入请求恢复流程，而不是按“组件不存在”直接失败。

恢复完成后会出现相应包添加事件。对启动性能而言，归档后的第一次点击包含重新获取和恢复包的成本，不能与普通冷启动放在同一组数据里。

### 查询、权限与应用身份边界

安装只是 PMS 的一条主线。包查询和权限状态也会影响启动、跨包调用与系统服务性能，分析时需要把下面几层分开。

#### 查询快照、客户端缓存与包可见性

服务端通过 `Computer` 快照减少长时间持有 PMS 主锁；应用侧的 `ApplicationPackageManager` 还可能缓存部分查询结果。缓存命中只能说明省去了一部分 Binder 或对象构造成本，不能据此认为结果与版本、用户、调用 UID 和可见性规则无关。

Android 11 以后，普通应用的包查询受 `<queries>`、自动可见规则和调用身份限制。`AppsFilterImpl` 参与服务端过滤，因此“查询为空”未必表示包没有安装；诊断应同时记录调用方 UID、用户 ID（`userId`）、查询 API、查询标志位和 Manifest 可见性声明。系统组件或持有特权权限的工具得到的结果不能直接用于推断普通应用的查询结果。

#### 权限服务不是 PMS 内部的一张表

Android 17 的权限状态由 `AccessCheckingService` 及其权限与访问策略组件维护。PMS 仍提供包、UID、签名和安装状态等基础信息，并通过对外接口与权限服务协作。权限检查缓慢时，需要区分：

- 调用方 Binder 排队；
- PMS/权限服务的快照或锁；
- 跨用户、可见性和签名关系计算；
- 首次构造或失效后的缓存重建。

如果把所有权限工作都归到 `PackageManagerService.mLock`，会遗漏当前架构边界。

#### 拆分包（Split）、UID 与更新冲突

一个已安装包可以包含主包（base APK）、按设备配置选择的拆分包（config split）和动态功能拆分包（dynamic feature split）。`PackageInstallerSession` 用一次安装会话表示待提交的文件集合；缺少必要拆分包、版本不一致或签名不匹配，都会在验证或协调阶段失败。

Play Feature Delivery 负责从分发侧按需交付功能模块；到了设备端，仍以 PackageInstaller/PMS 实际收到的文件集合为准。

Linux UID、应用数据目录、SELinux 安全域（domain）和运行时权限共同构成应用沙箱。包名相同并不意味着可以直接覆盖安装：签名密钥轮换历史、`versionCode`、共享 UID 的历史约束、安装来源以及系统分区与数据分区的关系都会影响结果。

安装流程中的包冻结（package freeze）用于阻止更新期间发生并发启动或状态变化，与“应用休眠”或“冻结缓存进程”无关。

---

### 用 Perfetto 定位安装瓶颈

#### 采集配置

至少采集以下信息：

- `system_server`、`installd`、`artd`、`dex2oat` 和安装器进程；
- `sched` 线程调度事件；
- Binder 事务（transaction）；
- 文件系统与块 I/O；
- atrace 的 `pm`、`dalvik` 事件分类；
- 如果分析 IncFS，再加入相关内核与 I/O 事件。

Android 17 源码中可直接找到的 Trace 区段名称包括：

- `StartPackageManagerService`
- `scanDir [...]`
- `parallelScanDir`
- `parallel parsePackage [...]`
- `installStage`
- `queueInstall`
- `startInstall`
- `installPackages`
- `reconcilePackages`
- `dexopt`
- `commitPackages`

具体设备可能因功能开关（feature flag）、厂商修改或代码分支而缺少部分轨迹区段。应先搜索设备实际记录的区段，再围绕相应时间范围展开，不能依赖一套固定的 SQL 名单。

#### 诊断顺序

1. **确定时间边界**：从安装会话提交到结果回调，不要把 APK 下载时间混进来。
2. **看 `system_server` 的阶段**：prepare、scan、reconcile、dexopt、commit 中哪段最长。
3. **展开到执行进程**：dexopt 长就看 `artd` / `dex2oat`；数据目录长就看 `installd`；增量读取长就看数据加载器与 IncFS。
4. **区分运行、排队和 I/O 阻塞**：轨迹区段持续时间很长，不等于线程始终占用 CPU。
5. **核对设备状态**：温度、充电、空闲状态、存储压力和并发安装都会改变结果。

下面的 SQL 用于列出安装相关的轨迹区段，帮助找到后续分析的时间范围：

```sql
SELECT
  p.name AS process_name,
  t.name AS thread_name,
  s.name,
  ROUND(s.dur / 1e6, 2) AS dur_ms
FROM slice s
JOIN thread_track tt ON s.track_id = tt.id
JOIN thread t ON tt.utid = t.utid
LEFT JOIN process p ON t.upid = p.upid
WHERE s.name GLOB '*install*'
   OR s.name GLOB '*Install*'
   OR s.name GLOB '*dexopt*'
   OR s.name GLOB '*scanDir*'
   OR s.name GLOB '*parsePackage*'
ORDER BY s.dur DESC
LIMIT 100;
```

这条查询只能找到已经记录的轨迹区段。某个阶段没有对应区段时，还要结合线程状态、Binder、I/O 和日志判断；没有搜到名称，不能证明该阶段没有执行。

---

### 版本与实现边界

| 版本 | 已确认的变化 | 对分析的影响 |
|---|---|---|
| Android 11 | IncFS 与 APK Signature Scheme v4 支持增量安装 | 安装与下载可以重叠，需要观察缺块读取和 `.idsig` |
| Android 14 | 设备端 dexopt 迁移到 ART Service | 编译问题要从 PMS 继续追到 `ArtManagerLocal`、`artd` 和 `dex2oat` |
| Android 15 | 系统级 App Archiving | 归档恢复不是普通冷启动 |
| Android 16 | Android 17 源码注释确认 `.sdm` 格式由此引入 | 可选云编译输入进入安装会话的签名校验与 ART 产物管理流程 |
| Android 17 | 当前固定基线；保留 ART 管理文件校验、SDM/SDC 复用判断和现代安装提交路径 | 以 `android-17.0.0_r1` 的实际功能开关和产品配置判断行为 |

版本变化必须能由固定 tag 或官方文档确认。没有类、提交或官方行为说明支撑的说法，不应写成平台事实。

---

## 安装来源验证与权限边界

安装会话进入 PMS 之前，平台可能先检查来源、安装器身份和用户授权。验证结果只回答当前来源是否允许继续，不替代签名、会话提交和包扫描。

Android Developer Verification（Android 开发者验证，后文简称“开发者验证”）回答的是：

> 准备安装这个包的开发者身份、包名和签名密钥，是否满足当前设备上的开发者验证策略？

它不判断 APK 是否损坏、升级签名是否匹配、安装器是否有权限、用户是否同意，也不负责 dexopt。把这些问题混成一项“安装校验”，会直接导致错误归因。

以下分析采用三组基线：

- 平台源码：AOSP `android-17.0.0_r1`。
- 平台接口：Android 17 / API 37；相关公开接口最早标记为 Android 16.1 / API 36.1。
- 产品政策：Android Developer Verification 官方文档在 2026-07-25 的公开口径。

政策会继续变化，源码标签不会。工程实现应把两者分开管理。

### 1. 先分清三个坐标系

| 层次 | 解决的问题 | 载体 | 版本边界 |
|---|---|---|---|
| Google 的开发者验证政策 | 哪些设备、区域、渠道和用户路径需要验证 | Android Developer Verifier、Google Play services、开发者管理中心 | 官方称覆盖 Android 7 及以上、经 Google 认证的 Android 设备；分阶段启用 |
| Android 平台机制 | 安装会话如何请求验证、等待结果、触发用户动作并回传错误 | `PackageInstallerSession`、`DeveloperVerifierController`、`PackageInstaller` API | 以 `android-17.0.0_r1` 为源码基准；公开结果 API 自 36.1 提供 |
| APK 与安装信任链 | APK 是否可解析、签名是否有效、升级证书是否兼容、权限与设备策略是否允许 | APK Signature Scheme、PMS、PackageInstaller、DPM、旧版包验证服务 | 由各自的平台版本和策略决定 |

Android 17 AOSP 提供开发者验证服务的接入框架，却没有在 `frameworks/base` 中开源 Google 的身份数据库和判定逻辑。下文用 verifier 指代设备指定的这项验证服务。在 Google 认证设备上，官方把 Android Developer Verifier 描述为一项新的 Google 系统服务，并说明 Android 7 及以上设备通过 Google Play services 接收相关更新。

AOSP 中存在这些类，并不表示任意 AOSP 构建都会自动执行 Google 的政策。Android 17 的 `PackageInstallerService` 默认策略是 `DEVELOPER_VERIFICATION_POLICY_NONE`；设备没有配置 verifier，或功能开关没有启用时，安装会话会跳过这一步。

`android.content.pm.verify.developer` 下的 `DeveloperVerifierService`、`DeveloperVerificationSession` 和 `DeveloperVerificationStatus` 都标有 `@SystemApi` 与 `@hide`。它们定义平台与受信任 verifier 之间的协议，普通应用无法通过公开 SDK 直接实现或调用。普通安装器只能使用 `PackageInstaller` 公开的结果附加字段、失败原因码和扩展接口。

### 2. 截至 2026-07-25，政策执行到哪里

#### 2.1 2026 年 9 月只在首批渠道执行

从 2026-09-30 起，巴西、印度尼西亚、新加坡和泰国经 Google 认证的 Android 设备开始执行首批验证，但当前公布的范围只覆盖下列参与商店发起的安装：

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
- 2027 年开始，计划把保护扩展到全球经 Google 认证的 Android 设备上的所有应用。

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

首批执行还要区分设备类型（form factor）：通过 Google Play 分发的应用需要登记支持的所有设备类型；Play 以外的 2026 年首批强制范围，目前只包括所选四国的手机（mobile）与平板（tablet）。不要把手机上的实验结果直接外推到 TV、Auto 或 Wear。

#### 2.2 特殊分发路径

| 路径 | 当前官方边界 | 工程理解 |
|---|---|---|
| ADB | 工作流保持不变，可安装未注册应用 | 只证明开发调试路径可用，不能替代真实商店验收 |
| 高级流程（Advanced flow） | 2026 年 8 月面向熟悉相关风险的高级用户推出；完成一次设置后可安装未注册应用 | 用户明确接受风险的旁加载路径，不是商店静默绕过接口 |
| 有限分发（Limited distribution） | 免费、无需政府签发身份证件，最多分享给 20 台经最终用户明确授权的设备 | 适合学习、课堂、家庭和非商业小范围分享 |
| 受管设备与组织内商店 | 由 IT 管理员审核的组织内应用不要求完成验证 | 同一 APK 离开组织内商店或进入非受管设备后，不能继续假设享有豁免 |

高级流程不是安装器可自行打开的开关。官方常见问题说明的流程包含启用开发者模式、反诱导确认、重启与重新认证、等待 24 小时，以及再次使用生物识别或 PIN 确认。ADB 不受这段等待时间影响。

这些步骤属于 2026 年的政策快照，不应硬编码成应用的永久业务规则。

### 3. 开发者验证和 APK 签名是什么关系

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

攻击者即使知道已注册应用的包名，只要没有合法私钥，仍会受到以下限制：

1. Developer Verification 不能让伪造 APK 获得合法签名。
2. APK Signature Scheme 校验仍会发现签名无效。
3. 若设备上已有正版应用，升级安装还要通过签名继承链（signing lineage）和证书兼容性检查。

一个 APK 的 v2/v3/v4 签名有效，只说明 APK 由对应密钥签发且内容未被篡改；它不能自动证明开发者已完成身份验证，也不能证明包名已登记到对应账号。

发版资产至少要同时维护包名、当前与历史签名证书、验证账号与状态，以及各渠道最终交付 APK 的证书指纹。渠道重签会同时破坏升级兼容性和包名登记证明。

### 4. Android 17 对普通安装器公开了什么

#### 4.1 API 36.1 与 API 37

`PackageInstaller` 文档把 Developer Verification 的结果字段标为“Added in version 36.1”。Android 17 / API 37 继续提供这些接口，并把安装器的目标 SDK 版本（target SDK）是否大于 36 作为新的回调行为边界。

36.1 是 SDK 次版本，不能只检查 `Build.VERSION.SDK_INT >= 36`。需要区分次版本时，可以使用下面的判断：

```kotlin
val supportsDeveloperVerificationResult =
    Build.VERSION.SDK_INT >= 36 &&
        Build.VERSION.SDK_INT_FULL >= Build.VERSION_CODES_FULL.BAKLAVA_1
```

Android 17 的 `Build.VERSION_CODES_FULL.CINNAMON_BUN` 为 37.0，自然满足这个条件。代码仍需用包含相应符号的 SDK 编译。

#### 4.2 失败原因

| 常量 | 值 | 含义 |
|---|---:|---|
| `DEVELOPER_VERIFICATION_FAILED_REASON_UNKNOWN` | 0 | verifier 超时、连接失败，或报告未知原因而无法完成验证 |
| `DEVELOPER_VERIFICATION_FAILED_REASON_NETWORK_UNAVAILABLE` | 1 | verifier 明确报告网络不可用 |
| `DEVELOPER_VERIFICATION_FAILED_REASON_DEVELOPER_BLOCKED` | 2 | verifier 已完成判断，但开发者未通过当前策略 |

`UNKNOWN` 不等于“没有提供原因”。读取前必须检查失败原因附加字段是否存在，不能只使用默认值 0。

#### 4.3 结果附加字段

| 附加字段 | 类型 | 用途 |
|---|---|---|
| `EXTRA_DEVELOPER_VERIFICATION_FAILURE_REASON` | `int` | 安装最终因 Developer Verification 中止时解释原因 |
| `EXTRA_DEVELOPER_VERIFICATION_LITE_PERFORMED` | `boolean` | 在失败结果中标记 verifier 是否只执行了轻量验证（lite verification） |
| `EXTRA_DEVELOPER_VERIFICATION_EXTENSION_RESPONSE` | `PersistableBundle` | verifier 对安装器扩展参数的响应 |
| `Intent.EXTRA_INTENT` | `Intent` | 需要用户动作，或提供可延后展示的系统解释页 |

`SessionParams.setExtensionParams()` 与 `getDeveloperVerificationServiceProvider()` 允许安装器和 verifier 使用双方约定的扩展参数。`Bundle` 的字段结构由 verifier 实现决定，不是跨设备通用协议。安装器只有确认服务提供方后才能解释其中内容；遥测也不应默认原样上传未知的 `Bundle`。

### 5. 一次提交可能产生多次回调

`Session.commit(IntentSender)` 只是把已封存的安装会话交给系统异步处理。这个方法成功返回，不代表安装已经完成。

Developer Verification 失败时，`EXTRA_STATUS` 取决于安装器的目标 SDK 版本、权限，以及该失败是否允许用户处理：

| 安装器 | 首个回调 | 后续结果 |
|---|---|---|
| 目标 SDK ≤ 36，只有 `REQUEST_INSTALL_PACKAGES` | 先收到不带失败原因的 `STATUS_PENDING_USER_ACTION` | 用户允许绕过则继续；否则返回 `STATUS_FAILURE_ABORTED` 并携带原因 |
| 目标 SDK ≤ 36，持有特权 `INSTALL_PACKAGES` | 通常直接收到 `STATUS_FAILURE_ABORTED` 并携带原因 | 不依赖普通用户确认流程 |
| 目标 SDK ≥ 37，需要用户输入的非阻断问题 | 先收到不带失败原因的 `STATUS_PENDING_USER_ACTION` | 用户重试或允许后继续；否则最终返回 `STATUS_FAILURE_ABORTED` 并携带原因 |
| 目标 SDK ≥ 37，其余阻断结果 | `STATUS_FAILURE_ABORTED` 并携带原因 | 可能带 `Intent.EXTRA_INTENT`，供系统解释原因 |

系统默认的 Package Installer 是特例：AOSP 会优先让它展示相应的系统页面。

安装器应把 `STATUS_PENDING_USER_ACTION` 当成中间状态，按下面方式继续处理：

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

应用不在前台时直接启动待处理的系统 Intent，可能受到后台启动限制，也会显得突兀。公开 API 建议先发送通知，让用户回到安装器后再进入系统页面。

### 6. Android 17 的源码调用链

Android 17 把新机制直接接入 `PackageInstallerSession`，没有把 Google 的业务判定写进旧版包验证服务。

#### 6.1 创建安装会话：保存初始策略并提前连接 verifier

`PackageInstallerService.createSessionInternal()` 从按用户保存的策略表读取默认值，分别作为安装会话的初始策略和当前策略。策略会写入安装会话 XML，因此进程重启不会改变已经创建的会话采用哪项初始策略。

满足以下条件时，构造 `PackageInstallerSession` 会提前绑定 verifier：

- 开发者验证功能已启用；
- 设备配置了 verifier 服务提供方；
- 当前会话不是多包安装的父会话；
- 当前会话不是系统重启后恢复出来的会话。

若 `SessionParams.appPackageName` 已提供包名，`DeveloperVerifierController` 还会调用 `onPackageNameAvailable()`，让 verifier 提前取得所需数据。此时验证尚未开始，这一步只是减少正式请求前的准备时间。

#### 6.2 `commit()`：封存、流式校验，再进入安装消息

下面的调用序列用于定位 `commit()` 之后、Developer Verification 之前的安装会话状态转换：

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

`streamValidateAndCommit()` 会准备 `DataLoader`、验证 APK/APEX 安装会话的基本结构，并把会话标记为已提交。执行到这里仍未安装成功。

#### 6.3 `handleInstall()`：解析 APK 后先做 Developer Verification

下面的序列标出 `performDeveloperVerification()` 在 `handleInstall()` 中相对 APK 解析的位置：

```text
handleInstall()
  ├─ sendPendingUserActionIntentIfNeeded()
  ├─ prepareInheritedFiles()
  ├─ parseApk()
  └─ performDeveloperVerification()
       └─ startDeveloperVerificationSession()
```

单包安装会话使用一个 `CompletableFuture`。多包安装不会验证父会话，而会分别验证每个子会话；任一子会话失败，整个多包安装都会失败。

#### 6.4 `DeveloperVerifierController` 与 verifier 的交互

`startDeveloperVerificationSession()` 交给 `DeveloperVerifierController` 的信息包括：

- 包名；
- 暂存包的 URI；
- `SigningInfo`；
- 应用清单声明的共享库；
- 当前验证策略；
- 安装器扩展参数；
- ADB 或强制验证相关的内部标志。

控制器使用 `PackageManager.ACTION_VERIFY_DEVELOPER` 绑定设备指定的 `DeveloperVerifierService`，然后调用 `onVerificationRequired(session)`；用户请求重试时调用 `onVerificationRetry(session)`；超时后调用 `onVerificationTimeout(id)`。

verifier 通过 `DeveloperVerificationSession` 的以下方法回报结果：

```text
reportVerificationComplete(status)
reportVerificationIncomplete(reason)
reportVerificationBypassed(reason)
```

完整结果包含 `isVerified`、轻量验证状态、App Metadata（应用元数据）状态和可选的失败说明。未完成结果目前只区分原因未知与网络不可用。

#### 6.5 结果怎样回到原安装链

下面的分支图说明 verifier 的结果如何完成 `CompletableFuture`，并决定继续原安装链还是结束安装会话：

```text
verifier callback
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

Developer Verification 位于 APK 解析完成之后、原有安装会话验证继续运行之前。通过这一关后，包仍可能因为签名、设备策略、存储、共享库、APK 格式或后续安装事务而失败。

### 7. 验证策略决定失败后的处理方式

Android 17 AOSP 定义了四种 System API 验证策略：

| 策略 | 开发者未通过 | 原因未知 / 连接失败 / 超时 | 网络不可用 |
|---|---|---|---|
| `NONE` | 不阻断 | 不阻断 | 不阻断 |
| `BLOCK_FAIL_OPEN` | 阻断 | 允许用户继续 | 允许重试或继续 |
| `BLOCK_FAIL_WARN` | 阻断 | 允许用户继续 | 允许重试或继续 |
| `BLOCK_FAIL_CLOSED` | 阻断 | 阻断 | 允许用户重试 |

`BLOCK_FAIL_OPEN` 与 `BLOCK_FAIL_WARN` 在 Android 17 源码注释中的安装结果描述相同；不要只凭名字推导额外语义。

每个用户的默认策略由 verifier 或系统指定的策略代理设置。verifier 还可通过安装会话的 `setPolicy()` 覆盖当前请求。业务代码不能只凭国家码模拟最终判定，必须以系统回调为准。

### 8. ADB 的绕过边界

官方面向开发者的承诺是 ADB 工作流不变。Android 17 源码分别描述了机制与结果：旧的非强制路径可以直接跳过验证；启用 `verificationServiceAdb` 后，ADB 安装请求也可送到 verifier，并通过 `FLAG_VERIFICATION_IS_ADB` 表明来源。verifier 可用 `DEVELOPER_VERIFICATION_BYPASSED_REASON_ADB` 明确报告这次验证因 ADB 来源而绕过。

若内部安装会话还设置了 `forceVerification`，平台会追加 `FLAG_VERIFICATION_FORCED_ON_ADB`；即便如此，源码注释仍要求只有阻断策略才能阻止安装。这些都属于命令行、测试或系统管理边界，不是普通第三方安装器 API，也不改变常规 ADB 用于开发测试的产品承诺。

- `adb install` 成功：证明 APK 和调试安装路径基本可用。
- 商店安装成功：证明该商店、设备、账号、区域和策略组合可用。
- 两者不能互相替代。

### 9. 安装耗时应如何分段统计

从取得安装包到收到最终回调，至少包含下面这些阶段，不能把总耗时全部记到 Developer Verification：

```text
包体获取
  + session 写入
  + seal / stream validation
  + 普通用户授权等待
  + Developer Verification
  + 原有 package verification
  + native library / 安装事务 / dexopt
  + 最终回调
```

这里的 `dexopt` 指 dex 字节码的编译与优化。`DeveloperVerifierController` 会在安装会话创建时尝试提前连接 verifier，正式验证请求则在 `handleInstall()` 解析 APK 后发送。因此，只看“创建安装会话到安装成功”的总时长，无法得出开发者验证本身的耗时。

Android 17 r1 控制器的默认参数是：

- 等待 verifier 连接：10 秒；
- 等待 verifier 响应请求：10 秒；
- verifier 可申请延长的总上限：10 分钟。

它们来自 `DeviceConfig.NAMESPACE_PACKAGE_MANAGER_SERVICE`，只是默认值，不构成兼容性保证或产品服务等级协议（SLA）。设备厂商、系统更新和实验配置都可能改变这些时间。

| 时间点 | 普通安装器是否可见 | 含义 |
|---|---|---|
| 安装会话创建、文件写入 | 可见 | 安装器自身 I/O |
| `commit()` | 可见 | 系统异步处理起点 |
| 首次 `STATUS_PENDING_USER_ACTION` | 可见 | 需要用户介入，不一定来自 Developer Verification |
| Developer Verification 失败原因 | 仅在失败且系统提供时可见 | 可确认验证层失败 |
| 最终成功或失败 | 可见 | 安装会话结束 |
| verifier 的绑定、请求和响应时刻 | 普通应用不可直接取得 | 需要系统级指标、系统轨迹或受控设备日志 |

普通安装器可以上报“`commit()` 到首个回调”和“`commit()` 到最终回调”，但不能把前者直接命名为“Developer Verification 耗时”。

### 10. 推荐的错误归因顺序

下面的决策顺序以公开状态和失败原因附加字段为依据，避免仅凭错误文本归因：

```text
收到安装回调
  ├─ STATUS_PENDING_USER_ACTION
  │    └─ 中间状态：保存 session 上下文并处理 Intent.EXTRA_INTENT
  ├─ STATUS_FAILURE_ABORTED
  │    ├─ 有 Developer Verification reason → 归入 developer verification
  │    └─ 无 reason → 检查用户取消、session abandon 等原因
  ├─ STATUS_FAILURE_BLOCKED
  │    └─ 检查 DPM、用户限制、旧 package verifier、关键包保护
  ├─ STATUS_FAILURE_INVALID / CONFLICT
  │    └─ 检查 APK、split、签名、版本与现有包
  └─ STATUS_SUCCESS
       └─ 安装完成；不等于应用首帧已经出现
```

其中，DPM 是设备策略管理器（Device Policy Manager）。`STATUS_FAILURE_BLOCKED` 的公开定义覆盖设备策略、旧版包验证服务和系统关键包保护等来源。只有 `STATUS_FAILURE_ABORTED` 同时携带 Developer Verification 失败原因时，才有充分证据把问题归入本机制。

`EXTRA_STATUS_MESSAGE` 是调试文本，可能随系统版本、语言和 OEM 改变。它适合保留样本，不适合作为监控聚合键。

### 11. Android 17 r1 的轻量验证附加字段类型不一致

公开契约规定 `EXTRA_DEVELOPER_VERIFICATION_LITE_PERFORMED` 是 `boolean`。但在 `android-17.0.0_r1` 中：

1. `setSessionFailedDueToDeveloperVerification()` 用 `Bundle.putBoolean()` 写入。
2. `sendOnPackageInstalled()` 复制到最终 Intent 时却调用 `extras.getInt()`。

这是 r1 源码中的类型不一致，不能把 `int` 当成新的公开协议。`Bundle.getInt()` 遇到原来的 `Boolean` 时还可能返回默认值 0，因此 `true` 信息可能在复制过程中已经丢失。下面的兼容性读取只能把类型差异限制在一处，不能恢复已丢失的真值：

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

兼容代码应限制在负责平台差异的适配层，并记录实际收到的类型，以便系统修复后删除这段分支；业务层仍统一使用 `Boolean?`。

### 12. 遥测字段与隐私边界

建议记录：

- 包名、`versionCode`、安装器包名与安装来源；
- 安装器的目标 SDK 版本、是否持有特权安装权限；
- `SDK_INT`、`SDK_INT_FULL`、安装会话是否为多包安装，以及是否为 staged（重启后应用）安装；
- `EXTRA_STATUS`、失败原因附加字段是否存在及其枚举值；
- 是否出现待用户操作、停留多久、最终继续还是取消；
- 设备是否受组织管理、是否通过 ADB 安装；
- 安装会话写入、`commit()` 到首个回调、`commit()` 到最终状态的耗时；
- 由服务端按版本维护的政策区域和渠道批次。

不建议默认记录未知的 verifier 扩展 `Bundle`、系统解释页文本、身份文件、账号凭据或签名私钥，也不要把自由格式的状态文本作为主聚合维度，因为它的可能取值很多且会随版本变化。

下面是一份只记录状态与时长、不收集身份材料的示例：

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

### 13. 发版与渠道验收清单

#### 开发者账号与签名

- 正式版、测试版（beta）、企业版和历史包名都已盘点。
- 包名已登记到正确账号。
- 注册证明 APK 与最终渠道 APK 的签名证书一致。
- Play App Signing、旧密钥、密钥轮换和非 Play 渠道的证书关系有记录。
- 渠道下载后的 APK 再次验签，防止重签或产物替换。

#### 安装器

- 用 `SDK_INT_FULL` 处理 36.1 API 边界。
- 把 `STATUS_PENDING_USER_ACTION` 当成中间状态。
- 目标 SDK 37 已覆盖待用户操作、重试、仍然安装和直接中止四条路径。
- 只有失败原因附加字段存在时，才把失败归因到 Developer Verification。
- 只有确认 verifier 服务提供方和字段结构后，才使用扩展参数。
- 后台收到待用户操作状态时通过通知让用户返回，不直接拉起 Activity。

#### 测试维度

| 维度 | 样本 |
|---|---|
| 平台 | Android 16.1、Android 17 |
| 设备 | 经 Google 认证的 Android 设备、无对应 verifier 的 AOSP 或企业设备 |
| 安装器目标 SDK | ≤ 36、37 |
| 权限 | `REQUEST_INSTALL_PACKAGES`、特权 `INSTALL_PACKAGES` |
| 结果 | 验证通过、开发者未通过、网络不可用、超时 |
| 用户路径 | 出现待用户操作后继续、重试或取消 |
| 分发 | 参与商店、非参与商店、直接旁加载、ADB、组织管理的商店 |
| 安装会话 | 单包、多包 |

区域和商店策略要在真实分发入口验证。VPN、修改系统语言或地区设置，以及实验室中的 ADB 安装成功，都不足以证明真实渠道路径可用。

### 14. 与其他安装机制的边界

| 机制 | 失败说明 | 是否由 Developer Verification 替代 |
|---|---|---|
| APK 解析与签名 | 文件损坏、签名无效、split APK 不一致、升级证书冲突 | 否 |
| 安装器权限与未知来源授权 | 调用方无权创建/提交安装，或用户未授权该来源 | 否 |
| 设备策略 / 用户限制 | 管理员禁止安装、卸载或未知来源 | 否 |
| 旧版包验证服务 / Play Protect | 对应用内容、恶意行为或包风险做判断 | 否 |
| Developer Verification | 开发者身份、包名与密钥登记不满足当前策略 | 当前机制 |
| SDM / dex 元数据 | 安装时附带的 dex 编译优化元数据是否可信 | 否 |
| `dexopt` / ART 应用性能配置文件 | 安装后代码编译状态和启动性能 | 否 |

可以按下面的职责模型理解：

> Developer Verification 是安装继续条件中的一项，无法取代 Android 现有的安装安全模型。

它通过 Android 17 的 `PackageInstallerSession` 接入统一安装事务；Google 的实际验证规则由设备上的 verifier 和当前政策控制；普通安装器只应根据公开回调处理用户动作与最终状态，不应猜测系统内部结论。

### 源码锚点

- [PackageInstaller：公开 extras、reason、policy 与 installer API](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/content/pm/PackageInstaller.java#449)
- [DeveloperVerifierService：系统 verifier 的回调入口](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/content/pm/verify/developer/DeveloperVerifierService.java#48)
- [DeveloperVerificationSession：请求信息、结果与 bypass API](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/content/pm/verify/developer/DeveloperVerificationSession.java#37)
- [PackageInstallerService：per-user policy 与 session 创建](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/services/core/java/com/android/server/pm/PackageInstallerService.java#298)
- [PackageInstallerSession：handleInstall 接入点](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/services/core/java/com/android/server/pm/PackageInstallerSession.java#3066)
- [PackageInstallerSession：Developer Verification 异步链路](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/services/core/java/com/android/server/pm/PackageInstallerSession.java#3244)
- [PackageInstallerSession：结果、用户动作与失败 extra](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/services/core/java/com/android/server/pm/PackageInstallerSession.java#3491)
- [DeveloperVerifierController：绑定、请求与超时管理](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/services/core/java/com/android/server/pm/verify/developer/DeveloperVerifierController.java#514)

### 官方资料

- [Android developer verification](https://developer.android.com/developer-verification/guides)
- [Frequently asked questions](https://developer.android.com/developer-verification/guides/faq)
- [Limited distribution](https://developer.android.com/developer-verification/guides/limited-distribution)
- [PackageInstaller API reference](https://developer.android.com/reference/android/content/pm/PackageInstaller)
- [Build.VERSION：SDK_INT_FULL](https://developer.android.com/reference/android/os/Build.VERSION#SDK_INT_FULL)
- [Build.VERSION_CODES_FULL](https://developer.android.com/reference/android/os/Build.VERSION_CODES_FULL)
- [Android Developer Verifier rollout](https://developer.android.com/blog/posts/android-developer-verification-rolling-out-to-all-developers-on-play-console-and-android-developer-console)

## Staged Install 的提交、重启与恢复

普通 APK 安装完成于当前系统会话，Staged Install 还要跨越重启验证和回滚状态机。它用更长的提交周期换取系统组件更新的原子性。

Staged Install（分阶段安装）经常被概括成“原子性更强的 APK 安装”，这种概括混淆了两个问题。

Android 的普通安装本来就有事务边界。Android 17 的 `InstallPackageHelper.installPackagesTraced()` 把安装组织为准备（Prepare）、扫描（Scan）、协调（Reconcile）和提交（Commit）；前三个阶段完成检查，Commit 才修改 Package Manager 的系统状态。多包安装会话（multi-package session）还可以把多个子会话作为一组提交。

分阶段安装处理另一类场景：某批更新不能在当前运行中的系统里立即激活，需要先完整验证，再跨过一次重启，让 APEX 与 APK 在新一次启动中以一致状态生效。APEX 是 Android 用于交付和更新系统模块的包格式。分阶段安装提供的是**跨重启激活协议**，并非为普通 APK 安装补充基础事务能力。

当前源码锚点为 Android 17 / API 37 / AOSP `android-17.0.0_r1`，同时保留 Android 10–16 的版本演进边界。

### 先分清三种“原子性”

| 层次 | 解决的问题 | Android 17 的主要实现 |
|---|---|---|
| 单次安装事务 | 包扫描、签名和依赖检查失败时，不提交一半 Package Manager 状态 | `InstallPackageHelper` 的 Prepare → Scan → Reconcile → Commit |
| 多包提交 | 多个子会话要么一起成功，要么一起失败 | `PackageInstaller.Session#addChildSessionId()` 与父会话 |
| 分阶段激活 | APEX、APK 或二者组成的更新需要在重启边界后统一生效 | `PackageSessionVerifier`、`StagingManager`、`apexd`、文件系统 checkpoint |

这三层可以叠加。一个分阶段父会话可以包含多个子会话，其中既有 APEX，也有 APK。此时既要满足多包同组提交规则，又要满足分阶段安装的跨重启状态机。

普通安装的原子性也有边界。`installPackagesTraced()` 要求可预见错误在 Commit 前被发现，并把系统状态修改集中到 Commit；但 `commitReconciledScanResultLocked()` 的源码注释同时警告，Commit 中抛出异常仍可能留下不一致状态。这是 Package Manager 的逻辑事务划分，不等同于数据库式或掉电安全的完整回滚。

分阶段安装增加了持久化状态、`apexd` 协调和文件系统 checkpoint；checkpoint 是系统可在启动失败时放弃一组文件系统变更的恢复点。

### API 边界：谁能创建分阶段安装会话

`PackageInstaller.SessionParams#setStaged()` 从 Android 10 / API 29 开始提供。Android 17 中它仍是 `@SystemApi`，并要求 `android.permission.INSTALL_PACKAGES`。普通应用即使声明 `REQUEST_INSTALL_PACKAGES`，也不能因此获得分阶段安装能力。

调用 `setStaged()` 后，这个安装会话会被安排到下一次重启时安装。若它是多包安装的父会话，所有子会话都必须采用一致的分阶段安装属性；回滚（rollback）属性也有同样约束。任一子会话在激活时失败，整组都不能按部分成功处理。

另一个边界是免重启 APEX 更新。APEX 可以声明支持免重启更新（rebootless update），但这种 APEX 更新不属于分阶段安装会话。

命令行使用 `--force-non-staged` 进入另一条路径。明确设置了 `staged` 属性的安装会话都要等待重启。

### Android 17 的完整状态机

#### 提交后不会直接进入 StagingManager

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

#### `ready`、`applied`、`failed` 是三个持久化状态

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

#### 为什么先持久化就绪状态，再通知 apexd

`PackageSessionVerifier.endVerification()` 对包含 APEX 的分阶段安装会话规定了以下顺序：

1. `session.setSessionReady()`，让 Package Installer 先持久化 `ready` 状态。
2. `mApexManager.markStagedSessionReady(sessionId)`，再告诉 apexd 可以激活。

如果设备在第 1 步后、第 2 步前重启，`apexd` 没收到 `ready` 通知，不会激活这批 APEX；重启恢复阶段可以把安装会话判为失败。如果先通知 `apexd`、后写 Package Installer 状态，窗口期内重启就可能出现 APEX 已激活、APK 侧却不知道该继续哪个安装会话的不一致状态。

这段顺序直接展示了分阶段安装的原子性来源：持久化状态与 `apexd` 状态之间采用明确的提交次序，不能简化成一句“重启后提升状态”。

### 重启前到底检查什么

`PackageSessionVerifier.verifyStaged()` 的 Android 17 主线可以整理为五组检查：

1. **活动会话与 checkpoint 能力**：设备不支持文件系统 checkpoint 时，不能让多批分阶段安装会话同时处于活动状态。
2. **回滚冲突**：回滚会话与普通分阶段更新冲突时，回滚具有更高优先级。
3. **包重叠**：两批活动会话更新同一软件包时，系统根据提交顺序拒绝冲突的一方。
4. **APEX 提交与验证**：包含 APEX 时，向 `apexd` 提交会话，并继续检查 APEX 容器签名与包信息。
5. **建立 checkpoint 并转为 ready**：支持 checkpoint 的设备调用 `StorageManager.startCheckpoint(2)`，随后按前述顺序更新 Package Installer 与 `apexd` 的状态：先持久化 `ready`，再通知 `apexd`。

“重启前验证”（pre-reboot verification）不能简化成检查磁盘空间和签名。它还负责检查并发的分阶段安装会话、回滚、包重叠和 APEX 状态是否一致。

Developer Verification 位于安装会话的通用验证路径中，发生在分阶段安装专用验证之前。Android 17 设备若启用了相应服务，并且当前安装适用该策略，分阶段安装会话同样必须通过它。

### 重启后：APEX 先于 `system_server` 激活

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

### 文件系统 checkpoint 不等同于 Virtual A/B

`StagingManager` 通过 `StorageManager` 使用以下能力：

- `supportsCheckpoint()`：设备是否支持文件系统 checkpoint。
- `needsCheckpoint()`：当前启动是否仍处于需要提交或回退 checkpoint 的状态。
- `startCheckpoint(2)`：为分阶段激活建立 checkpoint。
- `abortChanges("abort-staged-install", false)`：失败时放弃变更并回到安全状态。

这些是文件系统 checkpoint 接口。Virtual A/B 设备可能同时使用快照和 checkpoint，但源码中的 `supportsCheckpoint()` 不能直接改写成“是否支持 Virtual A/B”。分析日志时应保留 API 的准确含义。

没有文件系统 checkpoint 时，系统不允许并行恢复多批分阶段安装会话，因为缺少覆盖多批系统变更的统一回退边界。

### 不同安装会话的恢复差异

| 类型 | 重启前 | 重启后 | 失败影响 |
|---|---|---|---|
| 仅 APK 的分阶段安装 | 完成通用验证与分阶段安装冲突检查 | `installApksInSession()` 进入普通 APK 安装事务 | 通常将当前会话标记为失败 |
| 仅 APEX 的分阶段安装 | 额外提交给 `apexd` 并验证 APEX | APEX 已在开机早期激活；随后完成状态检查 | 可能回退已激活的 APEX、放弃 checkpoint 并重启 |
| APEX 与 APK 混合安装 | APEX 与所有子会话作为一批验证 | 先确认 APEX 激活状态，再安装 APK 子会话 | APEX 失败会传播到同批及其他受影响的分阶段安装会话 |
| 多包 APK 安装 | 父会话管理多个子会话的一致提交 | 子会话按同一父会话的语义安装 | 任一子会话失败，不能把父会话视为部分成功 |

包含 APEX 且设备支持 checkpoint 时，`resumeSession()` 不会过早把 `apexd` 会话宣告为永久成功。会话 ID 会保留到 `PHASE_BOOT_COMPLETED`，届时 `markStagedSessionsAsSuccessful()` 才通知 `apexd`。本次启动能否进入开机完成阶段，也属于健康检查的一部分。

### 失败处理与回退边界

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

### Android 17 的 dexopt 边界

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

### 性能测量：分为三个时间窗口

分阶段安装会跨过一次重启，`commit()` 到 `isApplied()` 无法只靠一段连续的进程内计时或一份短 Perfetto 系统轨迹测准。因此，应分成三个窗口测量，并用持久化的会话 ID 与状态时间把结果关联起来。

#### 窗口一：重启前提交与验证

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

#### 窗口二：重启与开机早期

关注：

- 关机和重启本身；
- `apexd` 的 APEX 验证、激活与挂载；
- 文件系统 checkpoint 状态；
- `system_server` 启动到 Package Installer 开始恢复安装会话的时间。

这一段通常需要开机系统轨迹（boot trace），并同时保留 `apexd` 日志。只采集 `system_server` 启动后的 `atrace`，会漏掉 APEX 在开机早期已经完成的工作。

#### 窗口三：`system_server` 恢复与 APK 安装

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

#### 一次可复现的测量应记录什么

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

### 实战排障

#### 安装会话一直不能变为 `ready`

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

#### 已经 `ready`，但重启后没有变为 `applied`

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

#### APK 安装阶段慢，怀疑 dexopt

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

#### 暂存空间不足

下面的命令分别查看数据分区空间、暂存目录大小和相关错误日志：

```bash
adb shell df -h /data
adb shell ls -lah /data/app-staging
adb logcat -b all -d | grep -E \
  'INSTALL_FAILED_INSUFFICIENT_STORAGE|PackageInstaller|StagingManager|apexd'
```

目录读取受系统构建类型和 SELinux 权限限制。看不到 `/data/app-staging` 不等于目录不存在，也不能因此排除空间问题。APEX 与 APK 混合会话还要结合 `apexd` 日志和 `dumpsys apexservice`；`/data/apex/active` 也不是 Package Installer 写入 APK 的暂存目录。

### 常用命令

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

### 源码阅读入口

- `PackageInstaller.java`：`setStaged()`、多包安装约束、`SessionInfo` 的 `ready` / `applied` / `failed` API。
- `PackageInstallerSession.java`：会话封存、解析、Developer Verification、原生库提取、安装与状态持久化。
- `PackageInstallerService.java`：安装会话 XML、暂存目录和重启恢复入口。
- `PackageSessionVerifier.java`：通用验证、分阶段安装专用验证、checkpoint 与 APEX `ready` 顺序。
- `StagingManager.java`：重启恢复、`apexd` 状态核对、APK 安装、checkpoint 回退与开机完成后的成功确认。
- `InstallPackageHelper.java`：普通 APK 的 Prepare / Scan / Reconcile / Commit 事务。
- `DexOptHelper.java`、`InstallScenarioHelper.java`：Android 17 安装 `dexopt` 的 ART Service 入口和编译原因。
- ART Service README：`artd`、`dexopt` 与产物管理的系统边界。

### 版本与实现边界

| 版本 | 需要记住的边界 |
|---|---|
| Android 10 / API 29 | `setStaged()`、分阶段 APEX/APK 安装与相关 `SessionInfo` 状态成为平台能力 |
| Android 11–13 | 分阶段安装、APEX、回滚与 checkpoint 继续演进；具体并发和回退策略要按对应源码标签核对 |
| Android 14–16 | ART Service 成为应用 `dexopt` 的主要管理层，不能继续沿用旧 PMS / `installd` 主线描述 |
| Android 17 / API 37 | 当前源码基准：Developer Verification 参与适用的安装会话验证；`StagingManager` 与 ART Service 行为按 `android-17.0.0_r1` 核对 |

回看任何旧版本问题时，都要同时锁定 Android 框架、ART 和 `apexd` 的版本。只把框架文件换成 Android 17，却继续引用旧 `installd` 的 `dexopt` 流程或旧 `apexd` 状态机，会得到跨版本混用的结论。

## AAB 与 PackageInstaller 内容分发

AAB 决定商店侧如何生成和选择 APK 集合，PackageInstaller 承担设备侧安装。两者属于同一软件交付链的不同责任边界：商店负责制品选择、下载和重试，平台从安装会话开始负责校验、确认与提交。

| 场景 | 平台接收的输入 | 主要系统组件 | 平台负责什么 |
| --- | --- | --- | --- |
| 应用安装或更新 | 一个单体 APK，或一组基础 APK / split APK | `PackageInstallerService`、`PackageInstallerSession`、Package Manager | 暂存、解析、签名和策略校验、用户确认、安装提交 |
| App Bundle 发布 | `.aab` | 应用商店或 `bundletool`，不由设备端 Package Manager 直接处理 | 生成适合目标设备的 APK 集合 |

### 一、从商店到设备：责任在什么地方切换

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

#### 1. AAB 不能直接安装到 Android 设备

Android App Bundle（AAB）是发布格式。Google Play 可以根据应用二进制接口（ABI）、屏幕密度、语言和动态功能模块，从 AAB 生成目标设备需要的 APK。其他分发系统也可以通过 `bundletool` 生成一组 APK。设备端最终安装的仍是 APK：一个基础 APK，加上零个或多个 split APK；split APK 按设备配置或功能模块拆分代码和资源。

`PackageInstaller` 不解析 `.aab`，也不替应用商店决定应该下载哪些配置 split APK。若安装器漏掉必需的 split APK，或把不同版本、不同签名的 APK 混在同一个安装会话中，平台会拒绝安装。

Android 17 的 `PackageInstaller` API 文档和 `PackageInstallerSession.validateApkInstallLocked()` 都把同一组 APK 的一致性作为设备端安装前置条件：

- 包名、版本号和签名证书一致；
- split APK 名称唯一；
- 完整安装包含一个基础 APK；
- 部分更新必须与设备上已有包保持一致。

`validateApkInstallLocked()` 会收集新增 APK，检查重复的 split APK，通过 `assertApkConsistentLocked()` 核对包名、版本和签名，并将文件改为平台使用的规范名称。挑选 split APK 的工作可以发生在商店或 `bundletool` 侧，但基础 APK 与 split APK 的集合一旦交给设备，设备端只接受满足一致性规则的结果。

#### 2. 下载器和 PackageInstaller 是两个模块

内容分发网络（CDN）选择、HTTP 并发、断点续传和网络切换恢复属于商店下载器。`PackageInstaller.Session.openWrite(name, offset, length)` 支持从指定文件偏移继续写入安装会话，但它不发起网络请求，也不知道 CDN 的存在。

已知 `length` 时应传入真实长度，系统可以提前分配暂存空间。`offset` 是开始写入的文件偏移量，适合从安装会话中已经写入的位置继续；安装器仍要自行保证远端文件没有变化，并校验下载结果。

因此，“弱网下载失败”要在下载层定位；“APK 已写完但 `commit()` 失败”才进入 PackageInstaller 和 Package Manager 的诊断范围。

#### 3. 普通安装器不因此获得静默安装能力

任何应用都可以使用安装会话 API 创建安装请求，但最终能否无交互安装，取决于调用方身份、权限、设备策略和用户授权。面向普通用户的外部来源安装通常需要：

- 声明 `REQUEST_INSTALL_PACKAGES`；
- 用户允许该来源请求安装应用；
- 在 `STATUS_PENDING_USER_ACTION` 返回后，由可见界面或通知引导用户完成系统确认。

设备所有者、关联的资料所有者以及持有系统级安装权限的组件有不同规则。应用不能把“能够创建安装会话”理解为“能够静默安装”。

### 二、PackageInstaller 安装会话的执行过程

#### 1. 安装器侧：创建、写入、关闭、提交

下面的示例只展示安装会话的文件写入方式。调用方仍需满足安装权限和用户确认要求；`apkParts` 中应放入商店已经选好的基础 APK 与 split APK。

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

每个 `openWrite()` 返回的流必须在 `commit()` 前关闭。对目标 API 35 及以上的安装器，传给 `commit()` 的状态接收器必须来自可变的 `PendingIntent`，因为系统要写入结果附加字段。这个 `PendingIntent` 应使用明确的组件或限定包名，并采用不会与其他安装混淆的请求码。

`commit()` 之后，安装会话被封存，调用方不能继续改写内容。回调可能先返回 `STATUS_PENDING_USER_ACTION`，也可能直接给出成功或失败。收到待确认状态时，应读取 `Intent.EXTRA_INTENT`；只有用户正在操作安装界面时才直接启动，否则应通过通知把用户带回交互流程。

#### 2. `system_server` 侧：封存先于安装

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

`commit()` 返回不代表安装完成。它只发起异步处理，最终结果由 `IntentSender` 送回。把 `commit()` 放到主线程并不会让系统安装工作在应用主线程执行；但如果安装器自己的下载、哈希计算或 APK 复制阻塞主线程，仍会造成应用无响应（ANR）。

#### 3. 完整安装、继承安装和多包安装

`SessionParams.MODE_FULL_INSTALL` 提供一个完整 APK 集合。`MODE_INHERIT_EXISTING` 用于保留已有 APK，并增加、替换或移除部分 split APK；它要求目标包已经存在，新增内容也必须与现有安装一致。

Android 10（API 29）起，父安装会话可以通过 `setMultiPackage()` 关联多个子会话。提交父会话时，所有子会话作为一个原子多包请求处理：共同成功，或共同失败。它不代表并行下载，也不会取消每个子包各自的签名、策略和兼容性检查。

分阶段安装会话（staged session）主要服务于需要跨重启验证和应用的系统级更新。普通应用商店不应为了“更可靠”而把所有安装都改成分阶段安装。

#### 4. Streaming、Incremental 与普通 `openWrite()`

`PackageInstallerSession` 确有流式（Streaming）和增量式（Incremental）`DataLoader` 分支，但它们需要专门的数据加载协议、权限和文件系统配合。普通安装器使用 `openWrite()` 顺序写入 APK，不会自动变成“边下载边运行”的增量安装。

分析安装性能时应先确认安装会话参数和 `DataLoader` 类型，再讨论数据是否完整暂存。把所有安装都归为流式解析，会误判磁盘占用和首次启动行为。

### 三、Android 17 的验证边界

#### 1. APK 签名验证解决的是软件包身份连续性

APK 签名用于确认 APK 内容未在签名后被修改，并约束同一包名的更新关系。Android 17 兼容性定义文档（CDD）要求设备支持 APK Signature Scheme v3.2、v3.1、v3、v2 和 JAR 签名；这不表示每个 APK 都同时带有所有签名方案。

在 `PackageInstallerSession` 中，新增 APK 会经过 `ApkSignatureVerifier`，基础 APK 与 split APK 的 `SigningDetails` 必须一致。更新已有应用时，Package Manager 还会检查新旧签名或有效的签名轮换关系。签名不匹配属于安装冲突或无效包，不能通过关闭某个“性能校验”来绕过。

#### 2. Android 17 开发者验证不是 APK 签名的替代品

开发者验证的结果字段在 `PackageInstaller` 文档中标为 Android 16.1（API 36.1）加入；Android 17 / API 37 继续提供，并把安装器的目标 SDK 是否大于 API 36 作为一条新的回调行为边界。相关接口和结果信息包括：

- `getDeveloperVerificationServiceProvider()`；
- `EXTRA_DEVELOPER_VERIFICATION_FAILURE_REASON`；
- 开发者被阻止、网络不可用和未知错误等原因码；
- 验证扩展参数及响应。

APK 签名回答“这个更新是否延续了允许的签名身份”，开发者验证回答“当前安装策略下，开发者和包名是否满足验证要求”。Android 17 源码中的 `PackageInstallerSession.handleInstall()` 会在完成用户确认和 APK 解析后，在功能启用时启动 `DeveloperVerifierController`，随后才继续安装会话的其余验证。

安装器必须以 `EXTRA_STATUS` 为主状态，并在失败时读取开发者验证原因。网络不可用不应统一显示成“APK 损坏”；设备策略是否允许用户继续，由系统确认界面和验证策略决定。

#### 3. 安装失败不能只归因于签名

常见返回状态应按类别处理：

| 状态 | 常见含义 | 安装器应提供的下一步 |
| --- | --- | --- |
| `STATUS_PENDING_USER_ACTION` | 需要用户确认、授权或查看系统说明 | 在合适的前台时机启动系统提供的 Intent |
| `STATUS_FAILURE_INVALID` | APK 损坏、格式错误、split APK 不一致或签名无效 | 重新核对 APK 集合和下载校验值 |
| `STATUS_FAILURE_CONFLICT` | 与已有包、签名、权限或共享库关系冲突 | 显示冲突对象，不要盲目重试 |
| `STATUS_FAILURE_INCOMPATIBLE` | SDK、ABI 或硬件能力不兼容 | 回到商店侧重新选择适配 APK |
| `STATUS_FAILURE_STORAGE` | 暂存或安装空间不足、存储不可用 | 引导释放空间，再重建或重试安装会话 |
| `STATUS_FAILURE_BLOCKED` / `STATUS_FAILURE_ABORTED` | 策略、验证器或用户拒绝阻止安装 | 结合附加字段和系统说明展示原因 |

只记录一条“安装失败”会丢掉最有价值的诊断信息。至少要记录安装会话 ID、包版本、APK 集合摘要、`EXTRA_STATUS`、`EXTRA_STATUS_MESSAGE`、失败阶段以及是否经过用户确认；日志中不要保存签名私钥、授权令牌或用户文件内容。

### 四、安装性能应该怎样测

没有脱离设备、包结构和安装模式的固定优化百分比。建议把时间轴分成以下阶段：

1. **商店选择与下载**：服务端选择 APK 集合、首字节、下载完成、重试次数；
2. **安装会话写入**：`createSession()` 到最后一个输出流关闭，分别统计下载等待和本地写入；
3. **平台处理**：调用 `commit()` 到首次结果、用户确认耗时、确认后到最终结果；
4. **首次可用**：安装成功到首次启动，另行观察 dex、资源和应用初始化成本。

以下现象可以按证据快速分流：

| 现象 | 先检查什么 | 不应直接推断什么 |
| --- | --- | --- |
| 写入安装会话很慢 | 输入流吞吐、存储 I/O、是否在重复计算摘要 | `PackageInstallerService` 发生了大量垃圾回收 |
| `commit()` 后长时间等待 | 是否待用户确认、开发者验证、原生库提取、包验证服务 | 存在“后台安装低优先级队列” |
| 大包空间不足 | 下载文件、安装会话暂存与最终安装是否同时占空间，`length` 是否准确 | 平台的空间预估一定错误 |
| split APK 安装失败 | 基础 APK 与 split APK 的版本、签名、名称、设备配置和依赖 | 增量更新机制失败 |
| 安装器界面 ANR | 下载、复制、哈希和回调处理是否占用主线程 | 系统安装逻辑运行在应用界面线程 |

如果需要比较单体 APK 与 split APK，应固定设备、包版本、数据状态和安装方式，分别报告下载字节数、安装会话写入字节数、提交耗时和最终占用。AAB 能减少多少下载量取决于资源、ABI、语言和模块拆分，不能给出适用于所有应用的区间。

内容分享虽然也会使用 PackageManager 做目标解析，但它属于 `ACTION_SEND`、Sharesheet 与 URI 授权主题，不属于软件包安装流水线，本文不再展开。

### 五、源码核对入口

基于 `android-17.0.0_r1` 排查时，可以从以下位置开始：

| 问题 | 文件与关键入口 |
| --- | --- |
| 安装会话创建、持久化和配额 | `PackageInstallerService.createSessionInternal()` |
| 写入、封存和提交 | `PackageInstaller.Session.openWrite()`、`PackageInstallerSession.commit()` |
| 基础 APK / split APK 一致性与签名 | `PackageInstallerSession.validateApkInstallLocked()` |
| 用户确认和 Android 17 开发者验证 | `PackageInstallerSession.handleInstall()`、`DeveloperVerifierController` |
| 包验证服务与安装提交 | `PackageSessionVerifier.verify()`、`InstallingSession.installStage()` |

调试时先标明问题属于下载、安装会话写入、平台验证还是安装提交。按这些类别记录，才能得到可复现的结论。

## 常见误区

### “PMS 执行所有安装工作”

PMS 负责事务和包状态，文件操作、数据目录、编译调度和机器码生成分布在 `installd`、ART Service、`artd`、`dex2oat` 等组件中。

### “`Computer` 让所有查询完全无锁”

缓存快照减少了主锁争用，但快照重建和其他系统锁仍然存在。查询本身也可能耗在过滤、对象生成、Binder 排队或 CPU 调度上。

### “安装成功就说明 dexopt 成功”

Android 17 的安装路径明确允许 dexopt 失败而不让整个安装失败。应用可以先运行，再由后台任务补齐优化。

### “有 Baseline Profile 就必然安装时完成 AOT”

Profile 是否可用、由谁交付、何时编译都取决于安装渠道和设备策略。应以 `pm art dump` 和实际性能轨迹为准。

### “Startup Profile 是设备端编译步骤”

Startup Profile 主要在构建期影响 DEX 布局。它与指导 ART AOT 的 Baseline Profile 有关联，但职责不同。

### “IncFS 会按需解密 APK”

IncFS 按需提供并验证数据块。加密不是这套机制的定义。

### “`.sdm` 是每个 Android 17 安装都必须有的文件”

Android 17 源码把它作为可选 ART 管理文件。没有 `.sdm` 是正常路径。

---

## 结论

Android 17 的安装流程可以简要概括为：`PackageInstallerSession` 管事务，PMS 管包状态，`installd` 管应用数据和底层文件，ART Service 与 `artd` 管 dexopt，`dex2oat` 执行计算量最大的编译工作。

有用的性能结论必须回答三个问题：

1. 慢的是安装事务中的哪个阶段；
2. 该阶段实际运行在哪个进程、哪条线程上；
3. 观察到的是 CPU 执行、锁等待、Binder 排队，还是文件与增量数据 I/O。

围绕这三个问题收集证据，就能把模糊的“安装慢”定位到可验证、可复现的具体系统问题。

## 参考资料

建议按一次普通 APK 安装的控制流阅读：

1. `PackageInstallerSession.commit()`：安装会话如何密封、校验和进入安装；
2. `InstallingSession.installStage()` / `start()`：怎样形成 `InstallRequest`；
3. `InstallPackageHelper.installPackagesTraced()`：Prepare、Scan、Reconcile、Commit 四阶段；
4. `DexOptHelper.performDexoptIfNeededAsync()`：PMS 怎样把安装 dexopt 交给 ART Service；
5. `ArtManagerLocal.dexoptPackage()`、`PrimaryDexopter`、`artd.cc`：编译任务如何组织和执行；
6. `Installer.java` 与 `InstalldNativeService.cpp`：应用数据和底层文件操作；
7. `PackageManagerService.snapshotComputer()`：查询快照怎样缓存和重建。

分析跨重启的分阶段安装时，再加入 `PackageSessionVerifier` 与 `StagingManager`；分析增量安装时，再加入平台 `IncrementalService.cpp` 和 ACK 的 `fs/incfs`。

---

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
