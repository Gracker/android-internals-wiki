---
title: "Package Manager Service 与应用安装性能"
chapter: "1.9"
section: "1.9"
status: ready-for-review
drafted_date: "2026-04-05"
polish_count: 1
polish_date: "2026-04-09"
polish_by: "task2b-polish"
drafted_by: "openclaw-task2a"
reviewed_date: "2026-04-11"
reviewed_by: "openclaw-task6"
applicable_versions: "Android 10 (API 29) - Android 17 (API 37)"
last_verified: "2026-04-12"
last_verified_against: "AOSP android-16.0.0_r1 + Android Developers Baseline Profiles overview"
confidence: medium
sources:
  - type: aosp
    path: "frameworks/base/services/java/com/android/server/SystemServer.java"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/pm/PackageManagerService.java"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/pm/Installer.java"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/pm/PackageManagerShellCommand.java"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/pm/PackageInstallerSession.java"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/pm/InstallingSession.java"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/pm/InstallPackageHelper.java"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/pm/DexOptHelper.java"
  - type: aosp
    path: "frameworks/native/cmds/installd/InstalldNativeService.cpp"
  - type: official
    path: "https://developer.android.com/topic/performance/baselineprofiles/overview"
  - type: official
    path: "https://source.android.com/docs/core/perf/vm"
  - type: official
    path: "https://source.android.com/docs/core/ota/apex"
  - type: blog
    path: "Android Authority: Android 16 Cloud Compilation"
  - type: blog
    path: "Google I/O 2025: What's new in Android performance"
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
pipeline_stage: task6_pending
task6_state: revisiting
task6_result: needs-rework
task9_state: pending
task9_result: needs-rework
task2b_result: fixed
task2b_state: fixed
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

在 android-16.0.0_r1 的 `SystemServer.java` 里，`StartPackageManagerService` 出现在 `startBootstrapServices()`，随后调用 `PackageManagerService.main(...)`。它不在 `startCoreServices()`。启动顺序放得这么早，是因为 UserManager、Overlay、Permission、ContentProvider 解析、应用启动前的包查询都依赖 PMS 先把包状态准备好。

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

PMS 初始化时要扫描 `/system/app/`、`/system/priv-app/`、`/product/app/`、`/vendor/app/`、`/data/app/` 等目录，解析 Manifest，校验签名，恢复 `packages.xml` 和每个包的持久化状态。首次开机、OTA 后首启、包量很多的设备，这一段在 `system_server` 里会非常显眼。

### PMS 管理的核心数据结构

PMS 在内存中维护了几个关键的数据结构：

- **PackageSetting**：每个已安装应用的持久化设置（安装时间、UID、权限授予状态、编译过滤器等），存储在 `/data/system/packages.xml`
- **PackageInfo**：从 APK 的 `AndroidManifest.xml` 解析出的完整包信息，包括声明的 Activity、Service、Provider、权限
- **AndroidPackage**：AOSP 中的内部接口，封装了对 APK 文件的只读访问，包括 DEX 文件列表、native 库、签名信息

这些数据结构是 PMS 服务整个系统的"数据库"。任何进程要启动一个应用、查询一个 ContentProvider、检查一个权限，最终都要通过 PMS 的这些数据结构来获取答案。

### PMS 与 installd 的协作关系

PMS 维护包状态和安装策略，真正落到文件系统和应用数据目录的操作由 `Installer` / `installd` 完成。android-16.0.0_r1 里的 `Installer.connect()` 已经不是连 `/dev/socket/installd`，而是通过 `ServiceManager.getService("installd")` 拿到 Binder 服务，再用 `IInstalld.Stub.asInterface(...)` 发起远程调用。

这一层分工大致是这样：

- PMS / `InstallPackageHelper`：包扫描、签名校验、权限与组件注册、安装状态提交
- `Installer`：Java 侧的系统服务代理，把 PMS 需要的底层操作转给 `IInstalld`
- `installd`：创建应用数据目录、设置 UID/GID 和 SELinux 上下文、处理编译产物相关的 native 操作
- ART Service / `DexOptHelper`：负责 dexopt 调度、编译原因和过滤器选择

如果我们在 Trace 里看到 `system_server` 很忙，却没有对应的 `installd` 或 `dex2oat` 开销，问题多半还停留在包扫描和状态提交；如果 `installd` / `dex2oat` 很重，瓶颈通常落在文件 I/O、数据目录准备或编译阶段。

[已验证: AOSP android-16.0.0_r1 `Installer.java` / `IInstalld` Binder 服务；`frameworks/native/cmds/installd/InstalldNativeService.cpp`]

## 应用安装全流程与性能关键路径

了解了 PMS 的架构位置后，我们来看看一个应用从"用户点击安装"到"可以启动"经历了什么。安装流程根据触发方式有所不同（adb install / Google Play / PackageInstaller），但核心流水线是一样的。

### 安装触发路径

安装入口看起来不同，收敛点都是 session 提交和包状态更新。

**adb install**：宿主机先把 APK 推到 `/data/local/tmp/` 一类的临时位置，设备侧 shell 再通过 `PackageManagerShellCommand` 执行 `install-create`、`install-write`、`install-commit`。adb 会一直等到 session commit 完成再返回。

**Google Play / 应用商店**：安装器 App 通过 `PackageInstaller` API 管理 session。对 split APK、staged install、多包安装，这条路径更常见。

**系统预装 / 开机扫描**：PMS 在系统启动或 OTA 后扫描预装目录，把镜像里的包注册进内存状态和持久化配置。它不走 `adb install` 的 shell 命令，但后续仍然要处理包解析、状态恢复、必要的 dexopt。

### 现代安装控制路径

以 `adb install` 为例，现代 AOSP 的入口在 `PackageManagerShellCommand`。它先创建 session，再写入 APK 或 split，提交时进入 `PackageInstallerSession.commit()`。session 封存后，`InstallingSession.installStage()` 把真正的安装工作投递给 PMS 侧逻辑；包扫描和状态提交主要在 `InstallPackageHelper`，dexopt 调度走 `DexOptHelper` / ART Service，底层目录和文件操作再经 `Installer` 转给 `IInstalld`。

这套 session 模型解决了两个实际问题。一个是 split APK、多包安装、staged install 都能共用同一套提交协议；另一个是“写入文件”和“真正生效”被拆成两个阶段，失败回滚、重试、后台安装都更容易做。

### 安装阶段分解

从性能分析角度，安装过程可以拆成六段。

**1. 传输与写入 session**

APK 从 USB、网络或本地来源写入 session。大包、split 多、闪存慢时，这一段会先被拉长。

**2. commit 与文件落位**

session commit 之后，安装器把 APK 放到 `/data/app/` 下的目标目录。这里主要看文件 copy / rename、fsync、校验和存储写入延迟。

**3. 包扫描与签名校验**

PMS 解析 `AndroidManifest.xml`、校验签名、检查 sharedUserId / 权限 / ABI / split 关系，再决定能否把这个包正式纳入系统状态。升级安装还要检查新旧签名和 `versionCode` 规则。

**4. 应用数据目录与 native 准备**

`IInstalld` 负责应用数据目录、权限、SELinux 上下文、编译产物目录等底层操作。多用户设备在这里还会处理 user 维度的数据准备。

**5. dexopt 调度**

现代 Android 把编译决策更多放到 `DexOptHelper` / ART Service。有没有 Baseline Profiles、Cloud Profiles、设备是否空闲、当前安装原因是什么，都会影响这里选用的编译过滤器。对 Android 12+ 的常见安装路径，没拿到可用 profile 时通常只做 `verify`；更早版本还存在 quicken 等历史行为，细节见 §1.7。

**6. 状态发布与广播**

包状态写回 `packages.xml` 等持久化信息，PMS 更新内存结构，随后发出 `ACTION_PACKAGE_ADDED` 等广播，Launcher 和其他系统组件才能看到这个应用。

### 安装耗时分析方法

在 Perfetto 中分析安装耗时，可以关注以下 Track 和 Slice：

- **system_server 进程**：搜索 `PackageInstallerSession`、`installStage`、`commitPackagesLocked` 一类 Slice
- **installd 进程**：应用目录准备、文件操作耗时
- **`dex2oat` / `artd` 相关进程**：编译耗时，通常是安装期最重的一段 CPU 开销
- **I/O Track**：`ext4` / `f2fs` 的写入延迟、fsync 抖动

一个实用的 adb 命令来查看应用的编译状态：

```bash
# 查看单个应用的编译状态
adb shell cmd package compile --dump {package_name}

# 查看所有应用的编译状态
adb shell dumpsys package dexopt
```

输出中的 `compilation_filter` 字段显示当前的编译级别，`compilation_reason` 显示是什么触发的编译（`install` / `bg-dexopt` / `ota` 等）。

[待补充：安装过程在 Perfetto 中的 Trace 截图，标注各阶段]

[已验证: AOSP android-16.0.0_r1 `PackageManagerShellCommand.java` / `PackageInstallerSession.java` / `InstallingSession.java`]

## dex2oat 编译对安装和启动的双重影响

安装时的 dex2oat 编译是一个"付出 vs 收获"的权衡：编译越多，安装越慢但运行越快；编译越少，安装越快但运行时依赖 JIT 热身。这组权衡是 Android 编译策略演进的核心驱动力。

### 安装时编译 vs 后台编译 vs 运行时 JIT

关于这三种编译方式的机制和演进历史，我们在 §1.7 中已有深入分析。这里从 PMS 调度的角度做一个快速梳理：

**安装时编译（install-time dexopt）**：安装提交阶段会根据可用 profile 和系统版本选择过滤器。Android 12+ 的常见路径里，没有可用 Baseline / Cloud / local profile 时通常只做 `verify`；较早版本还有 quicken 等历史差异，`speed-profile` 这个字符串本身不能单独说明编译覆盖。

**后台编译（bg-dexopt）**：设备空闲充电时，ART Service 通过 JobScheduler 触发的后台优化。使用设备上积累的 JIT Profile，以 `speed-profile` 级别编译热点方法。这是安装后的补充优化环节。

**运行时 JIT**：应用运行时即时编译热点方法，同时在后台收集 Profile 供后续的 AOT 编译使用。

从性能分析的角度，我们最关心的是：**应用当前处于哪种编译状态，冷启动路径上的方法有多少是 AOT 编译过的？** 这可以通过以下命令判断：

```bash
# 查看编译状态
adb shell cmd package compile --dump com.example.app
# 输出示例：
# [com.example.app]
#   path: /data/app/~~xxx/com.example-xxx/base.apk
#   arm64: [status=verify] [compilation_filter=speed-profile] ...

# 手动触发全量编译（调试用）
adb shell cmd package compile -m speed -f com.example.app

# 手动触发 profile 编译
adb shell cmd package compile -m speed-profile -f com.example.app
```

### 编译模式的选择策略

系统对不同场景的编译模式选择是有策略的：

| 安装场景 | 默认编译级别 | 原因 |
|---------|------------|------|
| 首次安装（无可用 profile，Android 12+ 常见） | verify | 安装更快，首次启动更多依赖解释执行和 JIT |
| 首次安装（有 Baseline Profiles） | speed-profile | 安装即有 AOT 覆盖 |
| 首次安装（有 Cloud Profiles） | speed-profile | 聚合 Profile 覆盖更广 |
| 系统预装 | speed 或 speed-profile | OEM 配置决定 |
| OTA 后首次启动 | verify | 优先快速开机 |
| 后台空闲充电 | speed-profile | 使用本地 JIT Profile |
| 存储空间不足 | verify 或降级 | 节省存储 |

[已验证: AOSP frameworks/base/services/core/java/com/android/server/pm/, 编译策略; art/dex2oat/dex2oat_options.cc, 编译过滤器]

## Background Dexopt 策略与系统性能影响

后台 dexopt 是 Android 编译优化的"第二道防线"——安装时可能因为时间紧迫（用户在等安装完成）只能做 verify，但设备空闲充电时有充足的时间做更深度的编译。

### 触发条件

后台 dexopt（在 Android 14+ 中由 ART Service 管理）的触发条件非常保守：

- **设备正在充电**（AC 或 USB 充电，不是无线充电）
- **设备处于空闲状态**（屏幕关闭、没有前台应用）
- **电量充足**（通常要求 > 30%）
- **特定时间窗口**（通常是凌晨 2-5 点，但各 OEM 可能不同）

ART Service 通过 JobScheduler 注册一个专门的 `bg-dexopt-job`，当上述条件全部满足时，JobScheduler 会调度这个 Job 执行。如果条件不再满足（比如用户突然点亮屏幕），JobScheduler 会中断正在执行的 dexopt。

### dexopt 对前台应用的影响

后台 dexopt 设计得尽量不影响前台体验，但实际上仍然存在资源竞争：

**CPU 争用**：dex2oat 是 CPU 密集型操作，即使系统会限制后台 dexopt 的 CPU 优先级（通过 `sched_setscheduler` 设置为 `SCHED_BATCH`），在核心数量有限的设备上仍然可能抢占前台应用的 CPU 时间。

**I/O 竞争**：dex2oat 需要读取 DEX 文件、写入 OAT 文件，这些都是密集的文件 I/O。如果前台应用同时在读写存储（如加载图片、写入数据库），I/O 带宽竞争可能导致前台应用卡顿。

**内存压力**：dex2oat 编译过程中会占用相当数量的内存（用于编译中间表示），在内存紧张的设备上可能触发 LMK 杀后台进程。

手动触发后台 dexopt 的命令：

```bash
# 手动触发后台 dexopt（不检查充电/空闲条件）
adb shell cmd package bg-dexopt-job
```

[已验证: AOSP frameworks/base/services/core/java/com/android/server/art/, ART Service 后台 dexopt 实现; 官方文档 source.android.com]

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

## Android 16 云端编译（Cloud Compilation）

Android 16 引入了一个可能从根本上改变安装体验的特性：**云端编译（Cloud Compilation）**。

### 架构与工作原理

在传统模式中，dex2oat 运行在设备端——每次安装或更新应用时，设备需要消耗 CPU、内存和 I/O 来编译 DEX 代码。云端编译的核心思路是：**把这些编译工作搬到云端，设备只负责下载和使用编译产物**。

工作流程如下：

1. **云端预编译**：Google Play 的服务器在应用上架或更新时，在云端运行 dex2oat，生成编译产物
2. **产物签名**：编译产物使用与应用 APK 相同的密钥签名，确保完整性
3. **分发**：用户从 Play Store 下载应用时，编译产物以 **Secure DEX Metadata (SDM)** 文件格式一起下载
4. **设备端加载**：设备直接使用 SDM 文件中的编译产物，跳过本机 dex2oat

```
传统模式：APK → 设备端 dex2oat → OAT → 运行
云端编译：APK + SDM (预编译产物) → 直接加载 OAT → 运行
```

### 对低端设备的改善

云端编译最大的受益者是低端设备。在 2GB 内存的入门级手机上，dex2oat 编译一个大型应用可能需要几分钟，期间 CPU 占用高、内存紧张、用户体验很差。云端编译把这段等待时间完全消除了——只要网络带宽足够（SDM 文件通常比 APK 本身小），安装时间主要由下载 SDM 和文件落盘决定，而不再被设备端 dex2oat 主导。

### 与 Baseline Profiles 的关系

云端编译和 Baseline Profiles 不是替代关系，而是互补：

- **Baseline Profiles** 解决的是"哪些代码需要编译"的问题——标记启动路径和关键交互路径
- **Cloud Compilation** 解决的是"在哪里编译"的问题——从设备端搬到云端
- **Cloud Profiles**（Google Play 聚合的用户 Profile）提供了更全面的编译覆盖

三者的结合意味着：应用从 Play Store 安装后，启动路径上的代码已经有了云端预编译的 AOT 产物，冷启动性能接近或超过经过多天后台 dexopt 的状态。

### 隐私与安全考量

SDM 文件使用与应用相同的签名密钥，确保只有应用开发者授权的编译产物才能被加载。从隐私角度，Cloud Profiles 使用的是聚合和匿名化的数据，不包含用户个体信息。

需要注意的是，云端编译目前仅适用于通过 Google Play 分发的应用。侧载（sideload）的应用仍然走传统的设备端 dex2oat 流程。

[已验证: Android Authority, Android 16 Cloud Compilation; Google Blog, SDM 文件格式]

## 应用更新与 OTA 更新的性能影响

### 应用更新时的编译策略

应用更新时，PMS 需要处理版本升级和编译产物的更新。编译策略取决于更新前后的变化：

**增量更新（Delta Update）**：Google Play 支持增量更新，只下载 APK 中变化的部分。但编译方面仍然是全量重新编译——因为 DEX 文件可能整体变化（R8 混淆导致类名和方法索引变化）。增量编译在 ART 中有探索（如 dex2oat 的 incremental compilation），但尚未成为标准流程。

**全量更新**：删除旧版本的编译产物，重新运行 dex2oat。编译级别遵循与首次安装相同的策略（有 Profile 用 speed-profile，没有用 verify）。

更新耗时通常比首次安装短，因为系统已经有了该应用的 Profile（本地 JIT Profile 或 Cloud Profile），speed-profile 会实际编译有意义的方法。

### 系统 OTA 更新后的 mass dexopt

系统 OTA 更新是一个特殊的性能场景。OTA 更新可能改变了系统框架（framework.jar）、运行时（ART 模块）、或系统库，导致所有应用的编译产物失效——因为 OAT 文件中包含了编译时系统 API 的内联和优化，系统代码变了，这些优化可能不再正确。

**传统流程（Android 13 及以前）**：OTA 后首次启动时，系统对所有应用执行 mass dexopt，编译级别为 `verify`。用户在开机后会看到"正在优化应用 X/Y"的进度界面，这在大量应用的低端设备上可能需要很长时间。

**现代流程（Android 14+ ART Service）**：ART Service 的策略更加智能：

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

[已验证: AOSP frameworks/base/services/core/java/com/android/server/art/, OTA 后编译策略; Google Blog, Android OTA 优化]

## 在 Perfetto 中的表现与调试方法

前面讲了安装流程、编译策略、OTA 更新，这些理论知识在实际分析中需要对应到 Trace 中的具体位置。接下来，我们来看看这些过程在 Perfetto Trace 中长什么样、怎么定位问题。

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
# 查看单个应用的编译状态和编译产物路径
adb shell cmd package compile --dump {package_name}

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
| Android 7.0 | 混合编译模式（JIT + Profile-Guided AOT） | 安装速度大幅提升（不再全量 AOT） |
| Android 8.0 | 后台 dexopt 改由 JobScheduler 调度 | 更智能的后台编译时机 |
| Android 9.0 | 引入 Cloud Profiles（dex metadata） | 安装时有更全面的 Profile 覆盖 |
| Android 10 | APEX / Mainline 基础设施引入，OTA 与 ART 更新开始解耦 | 后续 OTA 优化和 Virtual A/B 路径有了继续演进的基础 |
| Android 12 | ART 模块化（Mainline） | 编译优化可通过 Play 系统更新推送 |
| Android 14 | ART Service 取代直接 dex2oat 调用 | 编译管理更统一，后台 dexopt 更智能 |
| Android 16 | Cloud Compilation / SDM 格式 | 设备端 dex2oat 大幅减少，安装速度提升 |
| Android 17 | static final 不可变 → 更激进的常量折叠 | 编译优化深度提升（与 §1.7 交叉） |

## 常见问题与误区

**误区一："安装越快越好，后台慢慢编译就行"**

后台 dexopt 需要设备空闲+充电。用户安装完立刻使用的场景下，在后台编译完成之前，应用完全依赖解释执行和 JIT。对于不经常充电或充电时不空闲的用户（比如睡前充电但手机闹钟在用），后台 dexopt 可能很久都不会执行。这就是 Baseline Profiles 存在的意义——确保安装时就有编译覆盖。

**误区二："dex2oat 没用，JIT 够了"**

JIT 在运行时动态编译，理论上可以覆盖更多热点方法。但 JIT 有两个限制：第一，首次执行的方法都是解释执行，冷启动路径上全是"首次执行"；第二，JIT 编译有运行时开销（占用应用主线程或 JIT 线程的 CPU 时间）。AOT 编译的优势在于零运行时开销——代码已经编译好了，直接执行机器码。

**误区三："安装慢是 PMS 的问题"**

安装慢最常见的原因是 dex2oat 编译，不是 PMS 本身的逻辑。PMS 解析 Manifest、管理权限这些操作通常在几百毫秒内完成。真正的瓶颈在 dex2oat 编译和文件 I/O。在分析安装性能时，应该先看 dex2oat 进程的 CPU 时间和 I/O 延迟。

**误区四："OTA 后所有应用都要重新全量编译"**

从 Android 14 开始，ART Service 在 OTA 后只做 `verify` 级别的编译，而且如果已有可用的 VDEX 文件且 verify filter 可以容忍依赖不匹配，则完全跳过编译。OTA 后首次启动比以前快了很多。

**误区五："dumpsys package dexopt 显示 speed-profile，说明应用编译得很好"**

`speed-profile` 只是编译级别，不代表实际编译了多少方法。对 Android 12+ 的常见安装路径，没有可用 profile 时它往往会退到 `verify`；更早版本还要看 quicken 等历史行为。要确认真实覆盖率，仍然要结合 `oatdump` 或 `profman`。

## 参考资料

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
- `frameworks/base/services/core/java/com/android/server/art/`：ART Service（Android 14+）

### 官方文档
- [Baseline Profiles 概述](https://developer.android.com/topic/performance/baselineprofiles/overview)
- [ART 与 Dalvik](https://source.android.com/docs/core/runtime)
- [ART 性能与虚拟机](https://source.android.com/docs/core/perf/vm)
- [dex2oat 编译选项](https://source.android.com/docs/core/runtime/dex2oat)
- [Profile-Guided 代码优化](https://source.android.com/docs/core/runtime/pgodexopt)
- [Package Manager API](https://developer.android.com/reference/android/content/pm/PackageManager)

### 深入阅读
- Android Authority: Android 16 Cloud Compilation
- Google Blog: Android Performance Updates 2025（dex2oat 编译优化）
- Google I/O 2025: What's new in Android performance（Cloud Compilation 详解）
