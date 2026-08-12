---
title: Package Manager Service 与应用安装性能
chapter: '1.9'
section: '1.9'
status: finalized
applicable_versions: Android 10 (API 29) - Android 17 (API 37)
last_verified: '2026-08-06'
last_verified_against: AOSP android-17.0.0_r1 + ACK android17-6.18-2026-06_r6 + Android Developers
confidence: high
sources:
  - type: aosp
    path: "frameworks/base/services/java/com/android/server/SystemServer.java @ android-17.0.0_r1"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/pm/PackageManagerService.java @ android-17.0.0_r1"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/pm/Computer.java @ android-17.0.0_r1"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/pm/InitAppsHelper.java @ android-17.0.0_r1"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/pm/ParallelPackageParser.java @ android-17.0.0_r1"
  - type: aosp
    path: "frameworks/base/core/java/com/android/internal/pm/parsing/PackageParser2.java @ android-17.0.0_r1"
  - type: aosp
    path: "frameworks/base/core/java/com/android/internal/pm/pkg/parsing/ParsingPackageUtils.java @ android-17.0.0_r1"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/pm/PackageInstallerSession.java @ android-17.0.0_r1"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/pm/InstallingSession.java @ android-17.0.0_r1"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/pm/InstallPackageHelper.java @ android-17.0.0_r1"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/pm/PackageSessionVerifier.java @ android-17.0.0_r1"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/pm/StagingManager.java @ android-17.0.0_r1"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/pm/Installer.java @ android-17.0.0_r1"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/pm/DexOptHelper.java @ android-17.0.0_r1"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/pm/PackageManagerShellCommand.java @ android-17.0.0_r1"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/pm/PackageArchiver.java @ android-17.0.0_r1"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/pm/pkg/ArchiveState.java @ android-17.0.0_r1"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/wm/ActivityStarter.java @ android-17.0.0_r1"
  - type: aosp
    path: "frameworks/base/services/incremental/IncrementalService.cpp @ android-17.0.0_r1"
  - type: aosp
    path: "frameworks/base/core/java/android/util/apk/ApkSignatureVerifier.java @ android-17.0.0_r1"
  - type: aosp
    path: "frameworks/native/cmds/installd/InstalldNativeService.cpp @ android-17.0.0_r1"
  - type: aosp
    path: "art/libartservice/service/java/com/android/server/art/ArtManagerLocal.java @ android-17.0.0_r1"
  - type: aosp
    path: "art/libartservice/service/java/com/android/server/art/ArtManagedInstallFileHelper.java @ android-17.0.0_r1"
  - type: aosp
    path: "art/libartservice/service/java/com/android/server/art/PrimaryDexopter.java @ android-17.0.0_r1"
  - type: aosp
    path: "art/libartservice/service/java/com/android/server/art/BackgroundDexoptJob.java @ android-17.0.0_r1"
  - type: aosp
    path: "art/artd/artd.cc @ android-17.0.0_r1"
  - type: kernel
    path: "kernel/common/fs/incfs/main.c @ android17-6.18-2026-06_r6"
  - type: kernel
    path: "kernel/common/fs/incfs/vfs.c @ android17-6.18-2026-06_r6"
  - type: official
    path: "https://source.android.com/docs/core/runtime/configure/art-service"
  - type: official
    path: "https://source.android.com/docs/core/architecture/kernel/incfs"
  - type: official
    path: "https://source.android.com/docs/security/features/apksigning"
  - type: official
    path: "https://source.android.com/docs/security/features/apksigning/v4"
  - type: official
    path: "https://developer.android.com/topic/performance/baselineprofiles/overview"
  - type: official
    path: "https://developer.android.com/topic/performance/baselineprofiles/manually-create-measure"
  - type: official
    path: "https://developer.android.com/topic/performance/startupprofiles/overview"
  - type: official
    path: "https://developer.android.com/about/versions/15/behavior-changes-all#app-archiving"
tags:
  - pms
  - package-manager
  - package-installer
  - art-service
  - dexopt
  - baseline-profiles
  - incremental-install
  - app-archiving
related_chapters:
  - '1.2'
  - '1.7'
  - '2.3'
  - '3.4'
  - '8.2'
task6_state: reviewed
task9_state: reviewed
task2b_state: fixed
pipeline_stage: finalized
last_body_apply_at: "2026-08-06T11:15:29+08:00"
last_body_apply_run_id: "20260806-111529-1f9a01ff"
last_review_finalize_at: "2026-08-06T12:07:15+08:00"
last_review_finalize_run_id: "20260806-120548-9b08ffcd"
last_consolidated_at: "2026-08-11"
consolidated_from:
  - "src/part1-fundamentals/ch01-architecture/1.67-android17-packagemanager-architecture-performance.md"
---

# 1.9 Package Manager Service 与应用安装性能

安装一个应用需要经过一整套系统流程。系统要验证安装会话、解析包、校验签名、协调权限和共享库、准备应用数据、按策略执行 dexopt，最终才把新状态发布给系统其余部分。只要其中一个阶段变慢，用户看到的“正在安装”就会变长；如果编译产物或 Profile 没有按预期生效，影响还会延续到首次启动。

平台基线采用 AOSP `android-17.0.0_r1`；涉及 Incremental File System 时，内核基线采用 ACK `android17-6.18-2026-06_r6`。Android 10～16 只用于解释机制如何演进。

---

## 先建立一张职责表

应用安装横跨多个进程。排查问题前，先确定正在观察的是控制面还是执行面：

| 模块 | 所在进程 | 主要职责 | 不应归给它的工作 |
|---|---|---|---|
| `PackageInstallerSession` | `system_server` | 管理 session、密封、校验、提交和结果回调 | 不直接解析全部包状态 |
| PMS / `InstallPackageHelper` | `system_server` | 扫描、协调签名与权限、处理包状态、提交安装结果 | 不直接运行 `dex2oat` |
| `Installer` | `system_server` | `installd` Binder 客户端 | 不是安装策略中心 |
| `installd` | native daemon | 应用数据目录、权限、标签及底层文件操作 | Android 14+ 不负责组织整套 dexopt 策略 |
| ART Service / `artd` | `system_server` / native daemon | 组织和执行 on-device dexopt，管理编译产物 | 不负责发布 PackageManager 状态 |
| `dex2oat` | 独立 native 进程 | 按 ART Service 给出的参数生成 OAT、VDEX 等产物 | 不决定包是否允许安装 |

Android 14 起，设备端 AOT 编译的控制面已经迁移到 ART Service。PMS 中仍能看到 `DexOptHelper`，但它更接近安装侧的桥接层：根据安装状态发起请求，最终由 `ArtManagerLocal`、`artd` 和 `dex2oat` 完成编译。把 Android 17 的安装编译简单画成“PMS 调 installd 做 dexopt”，会遗漏实际的调度和执行位置。

---

## PMS 为什么在开机早期启动

`PackageManagerService` 运行在 `system_server`。它维护已安装包、组件、签名、权限、共享库和用户安装状态，是 Activity、Service、Provider 解析以及权限检查的基础数据来源。

Android 17 的 `SystemServer.startBootstrapServices()` 用 `StartPackageManagerService` trace 包住 `PackageManagerService.main(...)`。它位于 bootstrap 阶段，而不是更晚的 `startCoreServices()` 或 `startOtherServices()`。原因很直接：许多服务启动时已经需要查询包和权限信息。

开机初始化会处理两类信息：

- 从持久化设置恢复包、用户和权限状态；
- 扫描 APEX、系统分区和 `/data/app` 中的实际包，解析 Manifest 并让磁盘状态与设置状态保持一致。

`InitAppsHelper` 负责组织系统目录和 data 目录的扫描。`ParallelPackageParser.makeExecutorService()` 在 Android 17 固定使用 4 个 `package-parsing-thread` 工作线程，并设置前台线程优先级。这里的“并行”主要是包解析并行，不等于 PMS 初始化的每一步都可以并行；共享状态提交仍要遵守 PMS 的锁和阶段顺序。

### 包信息不是一个对象

阅读 PMS 源码时，常见的几类对象处于不同层次：

- `AndroidPackage`：包解析后的内部只读视图，包含组件、权限、代码路径等声明信息；
- `PackageSetting`：系统持久化的安装状态，例如 appId、安装路径、签名和各用户状态；
- `PackageStateInternal`：供系统内部查询的包状态视图；
- `PackageInfo`：根据调用者权限、用户和 flags 生成的公共 API 返回对象。

因此，`getPackageInfo()` 不是从一个全局 Map 原样取出 `PackageInfo`。它要基于调用者可见性、用户状态和查询 flags 生成结果。包数量、查询 flags 和对象构造成本，都可能影响查询耗时。

---

## `Computer` 快照解决了什么

Android 17 的 PMS 仍有多个锁，不能用“PMS 已经无锁化”概括：

- `mLock` 保护内存中的包解析结果与关联状态，源码明确要求持有时间尽量短；
- `mInstallLock` 保护对 `installd` 的访问，源码要求不要在持有 `mLock` 时再获取它；
- `mSnapshotLock` 只用于构造或取得 `Computer` 快照。

`snapshotComputer()` 会比较当前数据版本和缓存快照版本。版本一致时可直接返回缓存；版本落后时，才在 `mSnapshotLock` 与 `mLock` 的保护下重建快照。若当前线程已经持有 `mLock`，它会返回当前数据的 live computer，避免在写操作中制造自相矛盾的快照。

可以据此得到两个结论：

1. 大量只读查询不必每次都重新获取 PMS 的主锁并复制全部状态；
2. 查询变慢仍可能来自快照重建、对象生成、包可见性过滤、Binder 排队或其他锁竞争。

所以，Perfetto 中一次慢 `getPackageInfo` 不能只凭 Android 版本就排除锁竞争，也不能看到 `Computer` 就断言读请求完全无锁。应该把 Java monitor contention、Binder 调度和对应线程 slice 放在一起看。

---

## 普通 APK 安装怎样提交

无论入口是 `adb install` 还是应用商店的 `PackageInstaller` API，普通安装最终都会进入 session 模型。一个 session 可以包含 base APK、split APK、安装元数据以及一个或多个 child session。

### 1. 写入和密封 session

安装器先创建 session，再把文件写入 staging 目录。`PackageInstallerSession.commit()` 不会直接修改 PMS 的包表；它先密封 session，防止继续改写内容。

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

密封和持久化很重要。进程死亡或系统重启后，系统需要知道 session 处于可恢复、已失败还是待安装状态。

### 2. 进入安装请求

`InstallingSession.installStage()` 把任务发到 PMS Handler。`start()` 创建 `InstallRequest`；普通 APK 请求随后进入 `InstallPackageHelper.installPackagesTraced()`。

这个方法的源码注释把核心事务分成四个阶段：

1. **Prepare**：检查安装参数、替换关系、ABI、签名和已有包状态；
2. **Scan**：解析待安装包，生成扫描结果；
3. **Reconcile**：把多个扫描结果与系统现有包、共享用户和签名规则统一起来；
4. **Commit**：在锁保护下提交包状态。

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

路径切换发生在 dexopt 前，因为 OAT/VDEX 等产物会关联最终代码路径。应用数据也要在编译前准备好。`DexOptHelper.performDexoptIfNeededAsync()` 使用单线程 executor 处理安装 dexopt；源码还明确规定，dexopt 失败不应让应用安装本身失败。结果可能是安装成功，但应用只能先以解释执行或较低优化级别运行，之后再由后台 dexopt 补齐。

### 3. 哪些阶段消耗什么资源

| 阶段 | 主要资源 | 常见变慢原因 |
|---|---|---|
| session 写入 | 存储 I/O | APK 大、split 多、闪存忙、增量块尚未到达 |
| 签名与完整性校验 | CPU + I/O | 文件大、证书轮换、v4/IncFS 数据等待 |
| Manifest 解析与扫描 | CPU + page cache | 包或组件多、压缩数据读取慢 |
| Reconcile | CPU + 锁 | 共享库、更新关系、共享用户或签名规则复杂 |
| 应用数据准备 | Binder + I/O | `installd` 排队、目录创建、SELinux 标签与存储压力 |
| dexopt | CPU + I/O | DEX 大、Profile 缺失、设备热限制、后台负载 |
| Commit 与发布 | 锁 + Binder | 多包事务、观察者和广播接收端繁忙 |

诊断时不要只看总安装时长。session 写入慢和 `dex2oat` 慢的优化方向完全不同。

---

## 签名校验与增量安装

### APK 签名方案的分工

Android 17 仍同时支持多代 APK Signature Scheme：

- v1 以 JAR 条目为单位，兼容旧系统；
- v2 从 Android 7 引入，保护 APK 的整体内容；
- v3 从 Android 9 引入签名密钥轮换 lineage；
- v4 从 Android 11 引入面向流式安装的 `.idsig`，并与 v2/v3 一起使用。

v4 不是 v2/v3 的替代品。`.idsig` 用于让系统在 APK 尚未完整落盘时验证已读取的数据块；APK 的最终身份和完整性仍要满足相应的 APK 签名规则。

### IncFS 是按块供数，不是“按需解密”

Incremental File System 允许应用在 APK 的全部数据块下载完之前启动安装或运行。用户态数据加载器提供缺失块，IncFS 通过 Merkle tree 和签名相关元数据校验读取到的块。

平台侧入口可在 `frameworks/base/services/incremental/IncrementalService.cpp` 看到；内核侧实现在 ACK `android17-6.18-2026-06_r6` 的 `fs/incfs/main.c` 与 `fs/incfs/vfs.c`。内核负责增量文件系统和缺块读取语义，不负责 PackageManager 的签名策略。

因此，增量安装的准确描述是“边下载、边提供并校验数据块”。它不是“APK 按需解密”。遇到 IncFS 安装卡顿，要同时观察：

- 数据加载器是否及时提供 requested blocks；
- 存储读取是否阻塞；
- `.idsig` 与 APK 签名是否有效；
- 应用启动触达的 DEX、资源或 native library 块是否已经到达。

---

## 安装 dexopt 与 ART Service

### compiler filter 取决于设备配置

Android 构建可以通过 `pm.dexopt.<reason>` 配置不同原因对应的 compiler filter。ART Service 文档给出的标准配置中，`bg-dexopt` 通常使用 `speed-profile`，多个开机相关原因使用 `verify`；产品配置可以覆盖这些值。

即使请求了 `speed-profile`，没有可用 Profile 时也不能假定系统一定进行完整 AOT。ART 会结合 Profile、磁盘空间、温度、现有产物和其他约束选择可执行的结果。分析设备行为时，应读取设备配置和实际产物，而不是把某个默认值写成所有 Android 17 设备的保证。

### Baseline Profile、运行时 Profile 与 Startup Profile

三者解决的问题不同：

| 类型 | 生成或提供者 | 主要用途 | 生效位置 |
|---|---|---|---|
| Baseline Profile | 开发者随应用交付 | 提前标记高价值类和方法，指导 AOT | 安装或后台 dexopt，取决于分发与设备路径 |
| Runtime Profile | ART 根据实际运行采样 | 反映该设备上的热点代码 | 后台 dexopt |
| Startup Profile | 开发者提供给 R8/D8 | 调整 DEX 中启动代码布局 | 构建期，不是 PMS 的设备端步骤 |

Baseline Profile 通常位于 APK 的 `assets/dexopt/baseline.prof`。安装渠道可以把 Profile 编入 dex metadata（例如 `base.dm`）并随 APK 交付；使用 `ProfileInstaller` 的应用也可以在运行后把 Profile 写入系统可消费的位置，再等待后台 dexopt。

不能笼统声称“只要 APK 带 Baseline Profile，安装按钮结束前就一定完成 AOT”。Play、ADB、IDE、本地 sideload 以及 OEM 构建可以采用不同调度时机。判断时应检查设备上的 ART 状态和编译原因。

Startup Profile 则更容易被误解。它影响的是 R8/D8 如何把启动相关类和方法布置到 DEX，目的是减少启动时的 page fault 和随机读取；它不会在设备上触发一个名为“Startup Profile 编译”的 PMS 阶段。

### Android 17 中可用的诊断命令

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

这类命令会改变设备编译状态。性能实验应记录执行前后的包版本、Profile 状态、compiler filter、温度和电量条件，不能把人工编译后的结果与普通用户首次安装直接比较。

---

## 后台 dexopt 与 OTA

Android 14+ 的后台编译由 ART Service 的 `BackgroundDexoptJob` 管理。标准调度通常每天一次，要求设备空闲且充电；设备退出 idle 后，运行中的任务会被取消。厂商可以调整约束和策略。

ART Service 不再保留旧 PMS 模型中的开机后 post-boot dexopt job。这样可以避免刚开机时的编译任务与用户操作直接争抢资源。需要补齐的编译工作交给后台任务，在满足 idle、charging 等条件时继续。

OTA 或 Mainline 更新后，已有编译产物是否还能复用取决于 boot image、classpath、APEX 版本、编译依赖和产物校验结果。不要把 OTA 后的行为概括成“所有应用重新编译”：

- 可继续验证并复用的产物不必重做；
- 失效产物可能先用 `verify` 或解释执行保证可用性；
- 更积极的 `speed-profile` 编译可以在后台逐步完成。

用户不再长时间看到“正在优化第 N 个应用”，不代表编译成本消失了，而是系统把更多工作改成了可验证、可复用和可延后的任务。

---

## `.sdm` / `.sdc`：Android 17 源码中的云编译产物

Android 17 固定 tag 中存在 `.sdm` 和 `.sdc`，但应按源码能够证明的范围描述。

`PackageInstallerSession` 的注释把 `.sdm` 说明为承载 cloud compilation artifacts 的文件。`ArtManagedInstallFileHelper` 把 `.dm`、`.prof` 和 `.sdm` 列为 ART 管理的安装文件；`.sdm` 文件名还要包含有效 ISA，例如 `base.arm64.sdm`。源码注释说明该格式从 Android 16 引入。

验证要求比普通附属文件更严格：

- 必须能找到对应 APK；
- 文件名中的 ISA 必须有效；
- APK 与 `.sdm` 至少使用 v3 签名；
- APK 和 `.sdm` 的签名必须精确匹配。

ART Service 的 `PrimaryDexopter` 会尝试为各 ABI 创建 `.sdc`。`artd.maybeCreateSdc()` 的行为说明了几个重要边界：

1. 没有 `.sdm` 是常见情况，不是安装错误；
2. 可复用 `.sdc` 需要匹配 `.sdm` 时间戳和相关 APEX 版本；
3. 一旦实际 dexopt 已完成，临时 `.sdm` / `.sdc` 可以被提前删除；
4. 删除 dexopt artifacts 时，ART Service 会把 ODEX、VDEX、ART、SDM 和 SDC 一并纳入管理。

这说明 `.sdm` / `.sdc` 是受签名与版本约束的可选优化输入，不是 Android 17 所有应用都必须经历的安装阶段。源码类名使用 `SecureDexMetadata` 相关命名，但没有必要自行扩展一个未经源码或官方文档定义的全称。

---

## 分阶段安装与 APEX

普通 APK session 通常在当前开机周期完成。`StagingManager` 处理的是必须重启后才能完成的 staged session，常见于 APEX 或需要原子应用的系统更新。

`PackageSessionVerifier` 会进行公共校验；对 staged session，还要处理重启前验证、`apexd` 交互、checkpoint/rollback，以及 ready、applied、failed 等状态。可以把它理解成一个跨重启事务：

```text
session committed
  → pre-reboot verification
  → mark ready
  → reboot
  → apply and verify
  → mark applied
      或失败后进入回滚/失败处理
```

只有部分 `PackageInstallerSession` 属于 staged session。使用 session API 时，先检查参数和包类型，再判断是否应跨重启分析。

---

## 应用归档

Android 15（API 35）引入系统级 App Archiving，Android 17 延续了这套能力。归档不是普通卸载：

- APK 和 cache 可以被移除；
- 用户数据被保留；
- Launcher 仍可展示归档入口；
- 用户点击后，由负责的安装器恢复归档应用。

Android 17 的 `PackageArchiver` 使用带 `DELETE_ARCHIVE` 与 `DELETE_KEEP_DATA` 语义的删除路径，并保存 `ArchiveState`。归档状态可包含可启动 Activity 信息、安装器标题和归档时间。`ActivityStarter` 遇到归档目标时，可以转入请求恢复流程，而不是按“组件不存在”直接失败。

恢复完成后会出现相应包添加事件。对启动性能而言，归档后的第一次点击包含重新获取和恢复包的成本，不能与普通冷启动放在同一组数据里。

## 查询、权限与应用身份边界

安装只是 PMS 的一条主线。包查询和权限状态也会影响启动、跨包调用与系统服务性能，分析时需要把下面几层分开。

### 查询快照、客户端缓存与包可见性

服务端通过 `Computer` 快照减少长时间持有 PMS 主锁；应用侧的 `ApplicationPackageManager` 还可能缓存部分查询结果。缓存命中只能说明省去了一部分 Binder 或对象构造成本，不能证明结果不受版本、用户、调用 UID 和可见性规则影响。

Android 11 以后，普通应用的包查询受 `<queries>`、自动可见规则和调用身份限制。`AppsFilterImpl` 参与服务端过滤，因此“查询为空”未必表示包没有安装；诊断应同时记录 caller UID、userId、查询 API、flags 和 manifest 可见性声明。系统组件或持有特权权限的工具得到的结果不能直接外推到普通应用。

### 权限服务不是 PMS 内部的一张表

Android 17 的权限状态由 `AccessCheckingService` 及其 permission/access policy 组件维护，PMS 仍提供包、UID、签名和安装状态等事实，并在对外接口中完成协作。权限检查慢时，需要区分：

- 调用方 Binder 排队；
- PMS/权限服务的快照或锁；
- 跨用户、可见性和签名关系计算；
- 首次构造或失效后的缓存重建。

把所有权限工作都归到 `PackageManagerService.mLock` 会遗漏当前架构边界。

### Split、UID 与更新冲突

一个已安装包可以包含 base APK、config split 和动态特性 split。`PackageInstallerSession` 以一次 session 表达待提交文件集合；缺失必须的 split、版本不一致或签名不匹配会在验证/协调阶段失败。Play Feature Delivery 属于分发层，设备最终仍以 PackageInstaller/PMS 接收到的文件集合为准。

Linux UID、应用数据目录、SELinux domain 和 runtime permission 共同构成沙箱。包名相同并不自动允许覆盖安装：签名 lineage、versionCode、shared UID 历史约束、安装来源和系统/数据分区关系都会影响结果。安装流程中的 package freeze 用于阻止更新窗口里的并发启动或状态变化，也不是“应用休眠”或“冻结缓存进程”。

---

## 用 Perfetto 定位安装瓶颈

### 采集配置

至少采集以下信息：

- `system_server`、`installd`、`artd`、`dex2oat` 和安装器进程；
- `sched` 线程调度；
- Binder transaction；
- 文件系统与块 I/O；
- atrace 的 `pm`、`dalvik` 分类；
- 如果分析 IncFS，再加入相关内核与 I/O 事件。

Android 17 源码中可直接找到的 trace 名称包括：

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

具体设备可能因 feature flag、厂商修改或代码分支而缺少部分 slice。先搜索现有 slice，再围绕时间段展开，不要依赖一套固定 SQL 名单。

### 诊断顺序

1. **确定时间边界**：从 session commit 到安装结果回调，不要把 APK 下载时间混进来。
2. **看 `system_server` 的阶段**：prepare、scan、reconcile、dexopt、commit 中哪段最长。
3. **展开到执行进程**：dexopt 长就看 `artd` / `dex2oat`；数据目录长就看 `installd`；增量读取长就看数据加载器与 IncFS。
4. **区分运行、排队和 I/O 阻塞**：长 slice 不等于线程一直在 CPU 上执行。
5. **核对设备状态**：温度、充电、idle、存储压力和并发安装都会改变结果。

下面的 SQL 可先列出安装相关 slice，作为继续分析的入口：

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

这条查询只能发现已有 slice。某个阶段没有 slice 时，还要结合线程状态、Binder、I/O 和日志判断，不能把“没搜到名字”当作“阶段没有执行”。

---

## 常见误区

### “PMS 执行所有安装工作”

PMS 负责事务和包状态，文件操作、数据目录、编译调度和机器码生成分布在 `installd`、ART Service、`artd`、`dex2oat` 等组件中。

### “`Computer` 让所有查询完全无锁”

缓存快照减少了主锁争用，但快照重建和其他系统锁仍然存在。查询本身也可能耗在过滤、对象生成、Binder 排队或 CPU 调度上。

### “安装成功就说明 dexopt 成功”

Android 17 的安装路径明确允许 dexopt 失败而不让整个安装失败。应用可以先运行，再由后台任务补齐优化。

### “有 Baseline Profile 就必然安装时完成 AOT”

Profile 是否可用、由谁交付、何时编译都取决于安装渠道和设备策略。应以 `pm art dump` 和实际 trace 为准。

### “Startup Profile 是设备端编译步骤”

Startup Profile 主要在构建期影响 DEX 布局。它与指导 ART AOT 的 Baseline Profile 有关联，但职责不同。

### “IncFS 会按需解密 APK”

IncFS 按需提供并验证数据块。加密不是这套机制的定义。

### “`.sdm` 是每个 Android 17 安装都必须有的文件”

Android 17 源码把它作为可选 ART 管理文件。没有 `.sdm` 是正常路径。

---

## 版本演进

| 版本 | 已确认的变化 | 对分析的影响 |
|---|---|---|
| Android 11 | IncFS 与 APK Signature Scheme v4 支持增量安装 | 安装与下载可以重叠，需要观察缺块读取和 `.idsig` |
| Android 14 | on-device dexopt 迁移到 ART Service | 编译问题要从 PMS 继续追到 `ArtManagerLocal`、`artd` 和 `dex2oat` |
| Android 15 | 系统级 App Archiving | 归档恢复不是普通冷启动 |
| Android 16 | Android 17 源码注释确认 `.sdm` 格式由此引入 | 可选云编译输入进入 session 签名与 ART 产物管理 |
| Android 17 | 当前固定基线；保留 ART 管理文件校验、SDM/SDC 复用判断和现代安装提交路径 | 以 `android-17.0.0_r1` 的实际 feature flag 和产品配置判断行为 |

版本变化必须能由固定 tag 或官方文档确认。没有类、提交或官方行为说明支撑的说法，不应写成平台事实。

---

## 源码阅读顺序

建议按一次普通 APK 安装的控制流阅读：

1. `PackageInstallerSession.commit()`：session 如何密封、校验和进入安装；
2. `InstallingSession.installStage()` / `start()`：怎样形成 `InstallRequest`；
3. `InstallPackageHelper.installPackagesTraced()`：Prepare、Scan、Reconcile、Commit 四阶段；
4. `DexOptHelper.performDexoptIfNeededAsync()`：PMS 怎样把安装 dexopt 交给 ART Service；
5. `ArtManagerLocal.dexoptPackage()`、`PrimaryDexopter`、`artd.cc`：编译任务如何组织和执行；
6. `Installer.java` 与 `InstalldNativeService.cpp`：应用数据和底层文件操作；
7. `PackageManagerService.snapshotComputer()`：查询快照怎样缓存和重建。

分析 staged install 时，再加入 `PackageSessionVerifier` 与 `StagingManager`；分析增量安装时，再加入平台 `IncrementalService.cpp` 和 ACK 的 `fs/incfs`。

---

## 小结

Android 17 的安装流程可以压缩成一句话：`PackageInstallerSession` 管事务，PMS 管包状态，`installd` 管应用数据和底层文件，ART Service 与 `artd` 管 dexopt，`dex2oat` 执行最重的编译工作。

有用的性能结论必须回答三个问题：

1. 慢的是安装事务中的哪个阶段；
2. 该阶段实际运行在哪个进程、哪条线程上；
3. 观察到的是 CPU 执行、锁等待、Binder 排队，还是文件与增量数据 I/O。

只要沿着这三个问题收集证据，就能把“安装慢”从一个模糊现象拆成可验证、可复现的系统问题。
