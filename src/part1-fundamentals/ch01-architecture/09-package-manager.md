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
applicable_versions: "Android 10 (API 29) - Android 17 (API 37)"
last_verified: "2026-04-05"
last_verified_against: "AOSP android-17-beta3"
confidence: medium
sources:
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/pm/"
  - type: aosp
    path: "system/installd/"
  - type: official
    path: "https://source.android.com/docs/core/perf/vm/multidex"
  - type: official
    path: "https://developer.android.com/topic/performance/baselineprofiles/overview"
  - type: blog
    path: "Android Authority: Android 16 Cloud Compilation"
  - type: official
    path: "https://source.android.com/docs/core/ota/apex"
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


---


# 1.9 Package Manager Service 与应用安装性能

## 为什么要了解 Package Manager Service

当我们在 Perfetto 中分析应用冷启动时，经常会看到一个很容易被忽略的阶段——`bindApplication`。这个阶段看起来只是"应用初始化"，但其中有一个耗时大户是跟 Package Manager Service（PMS）密切相关的：**系统需要为应用加载编译产物（OAT 文件）、验证 APK 签名、构建运行时包信息**。

另一个更直观的场景：用户从应用商店安装或更新一个 App，安装进度条转了十几秒甚至更久。很多人觉得这只是在下载，但实际上下载完成后，设备端还要经历 copy → verify → dexopt → 签名验证 → 通知的完整流水线。其中 dexopt（调用 dex2oat 编译 DEX 代码）可能是最耗时的环节——在低端设备上，一个大型应用的安装可能因为 dex2oat 花掉几分钟。

了解 PMS 和安装流程，我们就能回答这些问题：

- 安装耗时过长，瓶颈在哪里？是 I/O、dex2oat、还是签名验证？
- 应用冷启动慢，有没有可能是安装时的编译策略不够优化？
- 系统升级后所有应用都需要重新编译，这个过程对用户体验有什么影响？
- 在 Perfetto 中怎么定位安装和编译相关的性能问题？

这篇文章从 PMS 的架构位置出发，把应用安装的完整流程走一遍，重点放在每个阶段的性能特征和调试方法上。关于 dex2oat 本身的编译机制和优化策略，我们在 §1.7 已经详细分析过，这里不再重复——本节聚焦的是 PMS 如何**调度** dex2oat、安装流水线的性能瓶颈在哪里、以及 Android 16 云端编译如何改变这个格局。

[图：应用安装流水线全景——从用户点击"安装"到应用可启动的完整时序]

## PMS 在系统架构中的位置

PackageManagerService 是 `system_server` 中的核心系统服务之一，和 ActivityManagerService（AMS）、WindowManagerService（WMS）并称 Android 系统服务的"三巨头"。它们之间的分工很清晰：PMS 管理**包信息**（哪些应用安装了、权限是什么、组件声明了哪些），AMS 管理**组件生命周期**（Activity、Service、ContentProvider 的调度），WMS 管理**窗口和显示**。

在系统启动流程中，PMS 的初始化时机非常早。`SystemServer.java` 通过三个阶段启动系统服务：`startBootstrapServices()` → `startCoreServices()` → `startOtherServices()`。PMS 在 `startCoreServices()` 阶段就被初始化了，因为它是一切应用运行的基础——AMS 启动 Activity 之前，必须先从 PMS 获取应用的包信息（PackageInfo）、组件声明（ActivityInfo、ServiceInfo）、权限列表。

```
SystemServer 启动流程（简化）:
  startBootstrapServices()
    → ActivityManagerService (引导服务)
    → DisplayManagerService
  startCoreServices()
    → PackageManagerService  ← 在这里初始化
    → BatteryService
  startOtherServices()
    → WindowManagerService
    → InputManagerService
```

PMS 初始化时做的事情很重：扫描 `/data/app/`（用户应用）、`/system/app/` 和 `/system/priv-app/`（系统应用）、`/vendor/app/`（厂商应用）等目录下所有 APK，验证签名，构建内存中的包状态数据结构。这个过程在 Perfetto 中对应 `system_server` 进程启动阶段的 PMS 初始化 Slice，在低端设备上可能耗时数秒。

### PMS 管理的核心数据结构

PMS 在内存中维护了几个关键的数据结构：

- **PackageSetting**：每个已安装应用的持久化设置（安装时间、UID、权限授予状态、编译过滤器等），存储在 `/data/system/packages.xml`
- **PackageInfo**：从 APK 的 `AndroidManifest.xml` 解析出的完整包信息，包括声明的 Activity、Service、Provider、权限
- **AndroidPackage**：AOSP 中的内部接口，封装了对 APK 文件的只读访问，包括 DEX 文件列表、native 库、签名信息

这些数据结构是 PMS 服务整个系统的"数据库"。任何进程要启动一个应用、查询一个 ContentProvider、检查一个权限，最终都要通过 PMS 的这些数据结构来获取答案。

### PMS 与 installd 的协作关系

PMS 负责高层逻辑（解析包、管理权限、维护状态），但涉及文件系统操作的底层工作交给了 `installd` 守护进程。这个分工的原因是权限隔离：PMS 运行在 `system_server` 中，虽然有系统权限，但不应该直接操作应用的私有数据目录。installd 是一个原生（C/C++）守护进程，以 elevated privileges 运行，专门负责：

- 创建和删除应用数据目录（`/data/data/{pkg}/`）
- 设置目录的 UID/GID 和 SELinux 上下文
- 调用 dex2oat 进行 DEX 编译
- 管理 OAT/VDEX 编译产物文件

PMS 与 installd 之间通过 `/dev/socket/installd` 这个 Unix 域套接字通信，只有系统 UID 的进程才能访问这个 socket。在 Android 14+ 中，installd 还通过 Binder 与 `artd`（ART 守护进程）通信来执行编译任务。理解了 PMS 和 installd 的分工后，下面我们来看安装的完整流水线——每个阶段分别由谁负责、耗时在哪里。

[已验证: AOSP frameworks/base/services/core/java/com/android/server/pm/PackageManagerService.java, 系统服务初始化; system/installd/ 目录结构]

## 应用安装全流程与性能关键路径

了解了 PMS 的架构位置后，我们来看看一个应用从"用户点击安装"到"可以启动"经历了什么。安装流程根据触发方式有所不同（adb install / Google Play / PackageInstaller），但核心流水线是一样的。

### 安装触发路径

三种常见的安装触发方式：

**adb install**：开发者最熟悉的方式。adb 客户端将 APK 推送到设备的临时目录（`/data/local/tmp/`），然后通过 Binder 调用 PMS 的 `installPackage()` 方法。整个安装过程是同步的——adb 会等到安装完成才返回。

**Google Play / 应用商店**：通过系统级的 `PackageInstaller` 会话管理器。PackageInstaller 支持会话式安装（`PackageInstaller.Session`），允许分步提交 APK 数据（对 split APK 和大型应用很重要）。安装过程在后台进行，用户看到的是通知栏的进度条。

**系统预装**：系统镜像中的应用在首次开机时由 PMS 扫描并注册，不需要显式的安装流程。首次开机时 PMS 会扫描所有预装目录（`/system/app/`、`/system/priv-app/`、`/product/app/` 等），这是一个批量操作，在系统启动 Trace 中可以看到明显的 PMS 扫描耗时。

### 安装阶段分解

无论哪种触发方式，安装的核心阶段如下：

**1. 传输（Transfer）**

APK 从来源（USB/网络/本地）复制到设备。adb install 走的是 USB 传输，Google Play 走的是网络下载。传输完成后，APK 存放在临时目录。

**2. 拷贝（Copy）**

installd 将 APK 从临时目录复制到最终位置 `/data/app/{random-session-id}/base.apk`。这里的 `{random-session-id}` 是一个随机生成的目录名，用于隔离不同版本的应用。拷贝过程受存储 I/O 速度影响，在大 APK（>100MB）上可能比较明显。

**3. 签名验证（Verification）**

PMS 验证 APK 的数字签名，确保应用未被篡改。如果设备上已有同包名的应用，还需要验证新旧签名的兼容性（签名轮换的场景）。签名验证本身是 CPU 密集型的（RSA/ECDSA 验证），但通常不会成为主要瓶颈。

**4. DEX 编译（dexopt）**

这是安装流水线中**最可能成为性能瓶颈**的阶段。PMS 通过 installd（进而通过 artd）调用 dex2oat，将 APK 中的 DEX 字节码编译为设备架构的机器码。编译的级别由编译过滤器（compiler filter）决定：

- 首次安装（无 Profile）：`speed-profile`，但没有 Profile 等效于 `verify`，几乎不编译
- 有 Baseline Profiles 的应用：`speed-profile`，编译 Profile 中标记的方法
- 系统预装应用：根据 OEM 配置，可能是 `speed`（全量编译）或 `speed-profile`

关于编译级别的详细说明和各级别的性能差异，我们在 §1.7 中有完整分析。这里的关键点是：**dex2oat 的编译级别直接决定了应用首次启动的代码执行效率**。

**5. 权限与组件注册**

PMS 解析 `AndroidManifest.xml`，提取应用声明的权限、Activity、Service、Provider 等组件信息，更新内存中的 PackageSetting 和 packages.xml。这个阶段很快，通常不超过几十毫秒。

**6. 通知**

安装完成后，PMS 发送 `ACTION_PACKAGE_ADDED` 广播，通知系统中其他组件（Launcher 需要显示图标、ContentService 需要更新等）。

### 安装耗时分析方法

在 Perfetto 中分析安装耗时，可以关注以下 Track 和 Slice：

- **system_server 进程**：搜索 `installPackage`、`PackageInstallerSession` 相关 Slice
- **installd 进程**：文件操作耗时
- **dex2oat 进程**：编译耗时（通常是大头）
- **I/O Track**：`ext4` / `f2fs` 的写入延迟

一个实用的 adb 命令来查看应用的编译状态：

```bash
# 查看单个应用的编译状态
adb shell cmd package compile --dump {package_name}

# 查看所有应用的编译状态
adb shell dumpsys package dexopt
```

输出中的 `compilation_filter` 字段显示当前的编译级别，`compilation_reason` 显示是什么触发的编译（`install` / `bg-dexopt` / `ota` 等）。

[待补充：安装过程在 Perfetto 中的 Trace 截图，标注各阶段]

[已验证: AOSP frameworks/base/services/core/java/com/android/server/pm/PackageInstallerSession.java, 安装会话管理]

## dex2oat 编译对安装和启动的双重影响

安装时的 dex2oat 编译是一个"付出 vs 收获"的权衡：编译越多，安装越慢但运行越快；编译越少，安装越快但运行时依赖 JIT 热身。这个 trade-off 是 Android 编译策略演进的核心驱动力。

### 安装时编译 vs 后台编译 vs 运行时 JIT

关于这三种编译方式的机制和演进历史，我们在 §1.7 中已有深入分析。这里从 PMS 调度的角度做一个快速梳理：

**安装时编译（install-time dexopt）**：PMS 在安装流程中触发，编译级别取决于是否有可用的 Profile（Baseline Profiles 或 Cloud Profiles）。没有 Profile 时，默认只做 `verify`，安装很快但冷启动全靠解释执行和 JIT。

**后台编译（bg-dexopt）**：设备空闲充电时，ART Service 通过 JobScheduler 触发的后台优化。使用设备上积累的 JIT Profile，以 `speed-profile` 级别编译热点方法。这是安装后的"补课"环节。

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
| 首次安装（无 Profile） | verify | 快速安装，牺牲初始性能 |
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

Baseline Profiles 让应用在安装时就能获得 AOT 编译覆盖，不需要等用户先用几天积累 Profile。这是解决"安装后首次启动慢"这个问题的关键机制。

### 安装流程中 Baseline Profiles 的工作方式

Baseline Profiles 的工作流从开发阶段就开始了：

1. **开发时**：开发者通过 Jetpack Macrobenchmark 录制关键路径（如冷启动、首页滑动），生成 `baseline-prof.txt`
2. **构建时**：AGP 将 `baseline-prof.txt` 转换为二进制格式 `baseline.prof` + `baseline.profm`，打包进 APK/AAB
3. **分发时**：Google Play 还会聚合大量用户的 Cloud Profiles，与 Baseline Profiles 合并
4. **安装时**：PMS 从 APK 中读取 Baseline Profiles，交给 ART Service，以 `speed-profile` 级别编译其中标记的方法

关键点在于第 4 步：如果没有 Baseline Profiles，`speed-profile` 在没有 Profile 数据时等效于 `verify`——什么都不编译。有了 Baseline Profiles，安装时就能编译出有意义的 AOT 产物。Google 的数据是，正确配置 Baseline Profiles 可以提升约 30% 的代码执行速度。

### Startup Profiles 与 DEX 布局

Startup Profiles 是 Baseline Profiles 的启动子集，但它影响的不是编译策略，而是 DEX 文件的物理布局。AGP 8.3 起默认启用 DEX 布局优化（`dexLayoutOptimization = true`），R8/D8 编译器会将启动关键类集中到 classes.dex 的前部，减少类加载时的 I/O 操作。

综合使用 Baseline Profiles + Startup Profiles 的效果：**冷启动速度比单独使用 Baseline Profiles 快 15-30%**。

关于 Baseline Profiles 和 Startup Profiles 的详细配置方法和量化数据，参见 §1.7 和 §8.3。

[已验证: 官方文档 developer.android.com, Baseline Profiles 概述; AGP 8.3 发行说明]

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

云端编译最大的受益者是低端设备。在 2GB 内存的入门级手机上，dex2oat 编译一个大型应用可能需要几分钟，期间 CPU 占用高、内存紧张、用户体验很差。云端编译把这段等待时间完全消除了——只要网络带宽足够（SDM 文件通常比 APK 本身小），安装速度可以大幅提升。

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

**A/B（无缝）更新**：Android 10+ 的 A/B 分区设计进一步改善了 OTA 体验。更新在后台写入未使用的分区，dex2oat 也可以在后台提前完成，用户只经历一次重启，不再有"优化应用"的等待。

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
- **§8.2 App 启动全流程**：冷启动时 `bindApplication` 阶段的编译产物加载（OAT 文件映射）与 PMS 的编译策略直接相关
- **§8.3 启动优化策略**：Baseline Profiles 和 Startup Profiles 是启动优化的关键手段，配置方法详见该节
- **§4.3 ART 虚拟机内存管理**：dex2oat 编译过程的内存占用和 JIT 代码缓存在 ART 的内存预算中

## 版本演进

| 版本 | 包管理与编译变化 | 性能影响 |
|------|----------------|---------|
| Android 7.0 | 混合编译模式（JIT + Profile-Guided AOT） | 安装速度大幅提升（不再全量 AOT） |
| Android 8.0 | 后台 dexopt 改由 JobScheduler 调度 | 更智能的后台编译时机 |
| Android 9.0 | 引入 Cloud Profiles（dex metadata） | 安装时有更全面的 Profile 覆盖 |
| Android 10 | A/B 分区更新成为强制 | OTA 后不再有"优化应用"等待 |
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

`speed-profile` 只是编译级别，不代表实际编译了多少方法。如果 Profile 为空（首次安装且没有 Baseline Profiles），`speed-profile` 等效于 `verify`——什么都没编译。需要结合 `oatdump` 或 `profman` 来确认实际的编译覆盖率和 Profile 内容。

## 参考资料

### AOSP 源码路径
- `frameworks/base/services/core/java/com/android/server/pm/`：PackageManagerService 实现
- `frameworks/base/services/core/java/com/android/server/pm/PackageInstallerSession.java`：安装会话管理
- `system/installd/`：installd 守护进程实现
- `art/dex2oat/`：dex2oat 编译器
- `frameworks/base/services/core/java/com/android/server/art/`：ART Service（Android 14+）

### 官方文档
- [Baseline Profiles 概述](https://developer.android.com/topic/performance/baselineprofiles/overview)
- [ART 与 Dalvik](https://source.android.com/docs/core/runtime)
- [dex2oat 编译选项](https://source.android.com/docs/core/runtime/dex2oat)
- [Profile-Guided 代码优化](https://source.android.com/docs/core/runtime/pgodexopt)
- [Package Manager API](https://developer.android.com/reference/android/content/pm/PackageManager)

### 深入阅读
- Android Authority: Android 16 Cloud Compilation
- Google Blog: Android Performance Updates 2025（dex2oat 编译优化）
- Google I/O 2025: What's new in Android performance（Cloud Compilation 详解）

