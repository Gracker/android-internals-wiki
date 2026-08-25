---
title: Android 版本演进中的架构变化
chapter: '1.4'
section: '1.4'
status: finalized
pipeline_stage: ready-to-publish
applicable_versions: Android 4.4 (API 19) - Android 17 (API 37)
confidence: high
tags:
- treble
- mainline
- apex
- gki
- vintf
- art
- profile-guided
- background-restrictions
- 16k-page
sources:
- type: official
  path: https://source.android.com/docs/core/architecture/treble
- type: official
  path: https://source.android.com/docs/core/architecture/vintf
- type: official
  path: https://source.android.com/docs/core/tests/vts/gsi
- type: official
  path: https://source.android.com/docs/core/ota/modular-system
- type: official
  path: https://source.android.com/docs/core/architecture/vndk
- type: official
  path: https://source.android.com/docs/core/architecture/kernel/gki
- type: official
  path: https://source.android.com/docs/core/architecture/kernel/android-common
- type: official
  path: https://source.android.com/docs/core/architecture/bootloader/generic-bootloader
- type: official
  path: https://source.android.com/docs/core/runtime
- type: official
  path: https://source.android.com/docs/core/runtime/configure
- type: official
  path: https://source.android.com/docs/core/runtime/jit-compiler
- type: official
  path: https://developer.android.com/topic/performance/baselineprofiles
- type: official
  path: https://developer.android.com/training/package-visibility
- type: official
  path: https://developer.android.com/guide/practices/page-sizes
- type: official
  path: https://source.android.com/docs/whatsnew/android-15-release
- type: official
  path: https://source.android.com/docs/whatsnew/android-16-release
- type: official
  path: https://developer.android.com/about/versions/16/summary
- type: official
  path: https://developer.android.com/about/versions/17/features
- type: official
  path: https://developer.android.com/about/versions/17/behavior-changes-17
- type: official
  path: https://developer.android.com/about/versions/17/changes/messagequeue
- type: aosp
  path: system/libvintf/VintfObject.cpp @ android-17.0.0_r1
- type: aosp
  path: system/apex/apexd/apexd.cpp @ android-17.0.0_r1
- type: aosp
  path: system/core/rootdir/init.zygote64_32.rc @ android-17.0.0_r1
- type: aosp
  path: art/dex2oat/dex2oat.cc @ android-17.0.0_r1
- type: aosp
  path: frameworks/base/core/java/android/os/CombinedMessageQueue/MessageQueue.java @ android-17.0.0_r1
- type: aosp
  path: frameworks/base/apex/jobscheduler/framework/java/android/app/job/JobScheduler.java @ android-17.0.0_r1
- type: aosp
  path: packages/modules/Profiling/framework/java/android/os/ProfilingManager.java @ android-17.0.0_r1
- type: aosp
  path: packages/modules/Profiling/framework/java/android/os/ProfilingTrigger.java @ android-17.0.0_r1
- type: kernel
  path: build.config.gki.aarch64 @ android17-6.18-2026-06_r6
last_verified: '2026-07-25'
last_verified_against: AOSP android-17.0.0_r1; ACK android17-6.18-2026-06_r6; Android Developers; source.android.com
related_chapters:
- '1.1'
- '1.3'
- '1.5'
- '2.1'
- '4.3'
- '4.5'
- '5.2'
- '21.4'
task6_state: reviewed
task9_state: reviewed
task2b_state: fixed
last_idle_audit_at: '2026-07-13'
last_consolidated_at: '2026-08-11'
consolidated_from:
- src/part1-fundamentals/ch01-architecture/1.41-android-17-机器学习驱动的任务调度器.md
---

# Android 版本演进中的架构变化

分析 Android 问题时，“这是 Android 17 设备”还不够。实际行为至少由五个版本维度共同决定：

1. 平台版本和具体系统构建（build）；
2. 应用的 `targetSdkVersion`，以及以目标版本等条件切换行为的兼容性变更（compat change）；
3. ART、Media、Permission 等可独立更新的 Mainline 模块版本；
4. 厂商的系统分区（system）、厂商分区（vendor）与硬件抽象层（HAL）实现；
5. 内核分支、内核模块接口（KMI）代际和设备调度配置。

同一平台版本的两台设备，可能运行不同的 Mainline 模块和不同代际的受支持内核。反过来，同一个应用安装在同一台设备上，只改变目标 SDK 版本（`targetSdk`），也可能触发不同的 `MessageQueue`、权限或后台执行行为。

## 一张时间表先抓住主线

| 版本 | 主要架构变化 | 分析问题时的影响 |
|---|---|---|
| Android 4.4 / API 19 | ART 作为可选运行时预览 | ART 与 Dalvik 并存，不能把后来的 ART 行为套回所有 4.4 设备 |
| Android 5.0 / API 21 | ART 成为平台运行时；支持 64 位 ABI | 安装期编译、垃圾回收（GC）、Zygote 位数和原生 ABI 成为重要变量 |
| Android 7.0 / API 24 | ART 采用即时编译（JIT）、提前编译（AOT）和解释执行的混合策略 | 首次运行、代码使用画像积累和后台 DEX 优化（dexopt）会改变后续性能 |
| Android 8.0 / API 26 | Project Treble、VINTF、HIDL、VNDK | 系统框架与厂商实现的边界受到稳定接口、ABI 与测试套件约束 |
| Android 10 / API 29 | Project Mainline 与 APEX | 一部分系统组件可以脱离整机 OTA 更新 |
| Android 12 / API 31 | ART 进入 Mainline；GKI 2.0 成为关键内核架构 | 同一 Android 大版本的 ART 行为可能随模块更新变化 |
| Android 15 / API 35 | 平台支持 16 KB 内存页；VNDK 开始废弃 | 原生二进制对齐和厂商依赖模型需要重新检查 |
| Android 16 / API 36 | GBL 支持、16 KB 兼容模式、系统触发性能剖析（profiling）、`JobScheduler` 配额调整 | 引导链、原生代码兼容和线上诊断出现新的可选能力 |
| Android 17 / API 37 | 无锁 `MessageQueue`、更多性能剖析触发条件、`JobScheduler` 等待原因统计 | 目标 SDK 版本与 API 37 新接口直接改变性能诊断路径 |

Material You 是 Android 12 的重要产品和用户界面（UI）变化，但它没有重构系统与厂商分区或运行时边界。版本表只列出会改变系统分层、二进制兼容或性能分析方法的节点。

## 从 Treble 到 GKI：更新边界的分层变化

Android 的模块化沿着多个兼容边界逐步推进，各项边界是在不同版本中形成的。

```text
App / SDK API
    |
Framework 与可更新 Mainline 模块
    |  VINTF + stable HAL
Vendor / HAL 实现
    |  KMI
GKI 核心内核 + vendor modules
    |
Boot firmware / 可选 GBL
```

每条边界解决的问题不同。SDK API 约束应用与平台，厂商接口（Vendor Interface，VINTF）约束系统框架与厂商实现，KMI 约束通用内核映像（Generic Kernel Image，GKI）与厂商内核模块。它们都属于稳定接口，但不能互相替代。

### Treble、VINTF 与 HAL

Treble 在 Android 8.0 把系统框架（framework）和厂商（vendor）实现分到明确的分区与兼容边界。新版 system 与旧版 vendor 仍需满足双方声明的兼容契约；契约成立时，升级才可能减少同步修改。

VINTF 提供这份契约：

- 设备清单（device manifest）声明设备提供的 HAL 及版本；
- 系统框架兼容性要求表（Framework Compatibility Matrix，FCM）声明系统框架要求的 HAL 能力；
- OTA、启动和兼容性测试根据匹配规则判断组合是否合法。

Android 8.0 初期主要使用硬件接口定义语言（HIDL）描述跨分区 HAL。新的 HAL 现在使用具有 VINTF 稳定性的 Android 接口定义语言（AIDL）。旧设备和旧 HAL 仍可能保留 HIDL，因此阅读系统跟踪数据时必须先确认接口类型。

`/dev/hwbinder` 主要用于独立进程形式（binderized）的 HIDL HAL 通信。不能把所有硬件访问都归为 `hwbinder`：AIDL HAL、同进程 HAL、套接字（socket）、共享内存和厂商自定义路径都有不同的调用形态。硬件操作也不一定比系统框架 Binder 慢，延迟取决于具体服务、设备和工作内容。

### GSI 是验证载体，不是“所有设备共用的 system”

通用系统映像（Generic System Image，GSI）是接近纯 Android 开源项目（AOSP）的 system 映像。Android 9 及以上的相关设备可以用 GSI 运行厂商测试套件（VTS）和基于 GSI 的兼容性测试套件（CTS-on-GSI），验证厂商接口是否满足当前系统框架的要求。

GSI 能启动，只说明分区与接口组合已经满足启动所需的最低条件。完整合规还需要 VTS、CTS-on-GSI 及设备类型要求的其他测试。性能也不能只凭 GSI 推断量产系统，因为量产版本还包含厂商服务、HAL、调度参数和功耗策略。

### VNDK 与链接器命名空间的历史位置

Treble 还需要解决原生 ABI 的可见性。厂商原生开发套件（Vendor Native Development Kit，VNDK）曾提供一组可供 vendor 依赖的 framework 原生库；链接器命名空间（linker namespace）则限制不同进程和模块能看到哪些库。

Android 15 开始废弃 VNDK。对以 Android 15 构建的 `vendor`/`product` 分区，原 VNDK 库像其他可供 `vendor`/`product` 使用的库一样安装；VNDK APEX、相关版本属性和厂商快照（vendor snapshot）等机制被移除或缩减。用于兼容旧版 vendor 映像的早期 VNDK APEX 仍可能存在，向 vendor 提供稳定底层原生接口的 LL-NDK 也不属于上述废弃范围。

原生代码隔离仍由分区边界、稳定 AIDL/HIDL、链接器命名空间、LL-NDK 和构建依赖检查共同约束。排查库加载问题时，应以设备实际的 `ld.config.txt`、APEX 列表和已加载 `.so` 路径为准，不要预设所有 Android 15 及以上设备都把依赖放进 Vendor APEX。

### Mainline 与 APEX

Android 10 的 Project Mainline 把一部分系统组件划为可独立更新的模块。模块可以采用 APK 或 APEX：

- APK 适合普通系统框架组件和权限控制器一类模块；
- APEX 是面向底层系统组件的封装格式，可以携带原生库，并在启动早期由 `apexd` 验证、激活和挂载。

Mainline 让安全修复和组件更新不必总等整机空中升级（OTA），但“设备运行 Android 10”不代表所有后来出现的模块已经可更新。ART 从 Android 12 才成为 Mainline 模块。

这会改变复现方法。遇到 ART、加密与安全提供程序 Conscrypt、Media 或 Permission 行为差异时，除了用于标识系统版本的构建指纹（build fingerprint），还要记录当前启用的 APEX/APK 模块版本。只对比 `Build.VERSION.SDK_INT` 可能漏掉变量。

### GKI 与 KMI

GKI 把通用内核主体和设备相关模块分开。KMI 规定 GKI 向厂商内核模块（vendor kernel modules）开放哪些接口，并在对应 KMI 代际内维持兼容。

稳定 KMI 并不表示任意 GKI 都能替换：

- 不同 GKI 内核或 KMI 代际（generation）之间不承诺模块兼容；
- 厂商模块、设备树、启动配置和厂商功能仍需匹配；
- 相同 Android 平台可以支持多个历史 Android 通用内核（Android Common Kernel，ACK）分支。

Android 17 的新内核基线是 `android17-6.18`，本书当前使用的固定内核源码版本为 `android17-6.18-2026-06_r6`。官方兼容表同时列出 Android 17 可支持的若干较早 GKI 分支，所以看到 Android 17 用户空间时，不能直接断言设备内核一定是 6.18。

### Android 16 的 GBL

通用引导加载程序（Generic Bootloader，GBL）提供标准化、可更新的 UEFI 应用，包含通用 Android 引导逻辑、Fastboot 和厂商扩展接口。Android 16 引入平台支持，并建议符合条件的新 ARM64 设备集成。

GBL 仍依赖设备启动固件（boot firmware）提供统一可扩展固件接口（UEFI）、Android 验证启动（AVB）和必要协议，也允许厂商扩展。它是一套可部署的标准化方案，不是所有 Android 16 设备都具备的统一 Bootloader。分析启动时间时，仍要记录实际启动链，不能只按系统版本判断。

## 从 Dalvik 到 ART：编译策略如何改变

### Android 4.4：ART 预览

Android 4.4 中，Android 运行时（Android Runtime，ART）是可选运行时，Dalvik 仍是常见默认路径。ART 尝试把更多 Dalvik 可执行格式（DEX）代码提前编译为机器码，用安装时间和存储空间换取运行期收益。

这段历史反映的是编译时机变化。成本可以落在安装期、首次运行、后台空闲期或运行时，不同策略会在这些阶段之间重新分配 CPU、存储和延迟，不能只用“ART 一定更快”概括。

### Android 5.0 到 6.0：以安装期 AOT 为主

Android 5.0 用 ART 取代 Dalvik 作为平台运行时，并正式支持 64 位应用二进制接口（ABI）。ART 在这个阶段主要通过 `dex2oat` 做安装期提前编译（Ahead-of-Time，AOT）。

不能把它写成“所有方法都必然编译，运行时零编译开销”。用于决定编译范围和优化级别的编译过滤器、系统应用预编译、描述类加载时可见代码及依赖的类加载上下文，以及设备配置都会影响产物。可靠的判断来自具体包的编译状态，不能只凭版本印象。

64 位支持也不等于应用自动变快。ARM64 提供更多通用寄存器和新的 ABI，但指针、对象或原生数据结构可能变大。性能结果取决于代码、编译器和内存访问模式。

64 位设备上的 Zygote 形态由产品配置决定。`zygote64`、`zygote64_32`、`zygote32_64` 等配置决定主、辅 Zygote 的位数；init 服务名仍常见 `zygote` 与 `zygote_secondary`。不要仅凭 Android 版本假设一定存在两个 Zygote。

### Android 7.0 以后：JIT、AOT 与解释执行混合

Android 7.0 引入带代码使用画像的即时编译（Just-in-Time，JIT），并与 AOT、解释执行组合：

1. 未编译代码可以先解释执行；
2. JIT 编译运行期频繁执行的热点代码；
3. ART 在画像（Profile）中记录常用方法与类；
4. 后台 DEX 优化按画像做 `speed-profile` 编译；
5. 已编译代码和画像会随更新、空间压力或校验条件变化。

画像引导编译（Profile-Guided Compilation）并不保证“第一次必慢、以后必快”。安装来源可能提供根据用户使用数据生成的云端画像（Cloud Profile），应用和库也可以携带开发时准备的基准画像（Baseline Profile），帮助 ART 在用户首次运行前编译关键路径。这里分发的是代码使用画像，不应写成 Play 商店直接给每台设备下发可复用的 `.odex`/`.vdex` 机器码。

Android 16 的无缝应用更新优化也不是“云端编译”。它把 `dexopt`/`dex2oat` 移到安装流程更早的阶段，缩短应用包在代码和资源切换期间无法运行的时间。

### Android 12 以后：ART 版本不再只跟随系统大版本

ART 从 Android 12 起成为 Mainline 模块。Android 12 及以上设备可以通过 Google Play 系统更新获得运行时和编译器修复。因此，分析 JIT、垃圾回收、DEX 优化或验证器行为时，需要同时记录：

- 平台构建版本；
- ART APEX 版本；
- 应用包的编译过滤器（compiler filter）、代码使用画像和 DEX 优化原因（dexopt reason）；
- 是否刚经历安装、OTA 或 Mainline 更新。

`adb shell cmd package art dump <package>` 可以查看 ART Service 维护的应用包编译状态。命令输出属于诊断接口，字段可能随版本变化，自动化脚本应针对目标构建验证。

## Android 15 到 17：当前需要适配的变化

### 16 KB 内存页

Android 15 开始支持以 16 KB 内存页大小（page size）构建平台。更大的页面能扩大地址转换缓存（Translation Lookaside Buffer，TLB）覆盖范围、减少部分页表遍历，但也可能增加页面内部未被利用的空间和小块映射成本。官方基准给出的收益来自特定设备与工作负载，不应转换成“所有应用都会提升固定百分比”。

应用兼容性主要取决于原生代码：

- 纯 Java/Kotlin 代码通常不直接依赖页大小，但 SDK 或依赖库可能携带 `.so`；
- 可执行与可链接格式（ELF）文件的 `LOAD` 加载段和 APK 内未压缩的原生库都需要正确对齐；
- 内存映射函数 `mmap()`、共享内存、页掩码和写死的常量 `4096` 都要检查；
- 应使用当前原生开发工具包（NDK）和 Android Gradle 插件（AGP）重新构建，并在 16 KB 设备或模拟器上验证。

Android 16 加入 16 KB 向后兼容模式（backcompat mode），让一部分只按 4 KB 对齐的应用能够过渡运行；它不保证所有不兼容的原生二进制都能工作。Android 17 又提供测试属性，可把兼容模式设为 `fatal`，让不兼容二进制立即终止：

```bash
adb shell setprop bionic.linker.16kb.app_compat.enabled fatal
adb shell setprop pm.16kb.app_compat.disabled true
```

这是设备级测试开关，不应由普通应用在生产环境设置。Google Play 当前要求目标版本为 Android 15 / API 35 或更高的应用支持 64 位设备上的 16 KB 页；从 2027 年 2 月 1 日起，不支持的应用更新将无法发布。

Android 16 还把 `basename()`/`dirname()` 使用的线程局部存储（Thread-Local Storage，TLS）缓冲区改为首次使用时单独分配。官方发布说明给出的结果是在 16 KB 系统上释放初始线程页中的约 8 KB 空间。这是 Android C 库 bionic 的实现优化，不表示每个线程的总内存固定减少 8 KB。

### Android 16：系统触发性能剖析与 Job 配额

Android 15 / API 35 引入 `ProfilingManager` 的应用主动请求接口。Android 16 / API 36 增加系统触发的性能剖析（profiling）：应用注册关注的触发类型，系统在 `reportFullyDrawn()` 或应用无响应（ANR）等事件附近采集数据，再把结果交给应用。

Android 16 还调整 `JobScheduler` 的普通任务和加急任务（expedited job）运行时配额。配额会考虑应用待机分组（standby bucket）、任务启动时应用是否处于顶层（top）状态，以及任务是否在前台服务运行期间执行。前台服务不再等同于“Job 一定不计配额”。排查任务未运行时，应读取待执行原因（pending reason）、停止原因（stop reason）和约束，不能只看是否启动过前台服务。

### Android 17：MessageQueue、ProfilingTrigger 与 Job 诊断

以 API 37 为目标版本的应用在 Android 17 上默认使用新的无锁 `MessageQueue`。目标版本较低的应用可以通过兼容性变更开关测试：

```bash
adb shell am compat enable USE_NEW_MESSAGEQUEUE <package>
adb shell am compat disable USE_NEW_MESSAGEQUEUE <package>
```

它改变的是 `MessageQueue` 内部实现，不是让主线程上的业务、布局和 Binder 等待自动消失。依赖 `mMessages` 等私有字段的反射代码需要迁移；具体实现见 §1.9。

API 37 扩展 `ProfilingTrigger`，新增或公开用于冷启动（cold start）、内存不足（OOM）、因 CPU 使用过量被终止、异常和应用兼容性等场景的触发类型。不同触发器产生的采集结果（artifact）和停止条件不同，不能笼统写成“所有异常都自动保存完整系统跟踪数据”。应用仍需注册触发器、接收结果，并遵守系统限额。

`JobScheduler.getPendingJobReasonStats(jobId)` 返回各项待执行原因及其累计等待时长。多个原因可以同时成立，所以各项时长之和可能超过任务实际等待时间。它适合回答“哪类约束长期阻止任务运行”，但不能替代 `getPendingJobReasonsHistory()`、`JobParameters.getStopReason()` 和用于识别重复执行的业务日志。

`android-17.0.0_r1` 源码仍用功能开关配置系统 `aconfig` 和 `@FlaggedApi` 注解管理部分新增接口和触发器。应用应以最终 API 37 SDK、设备构建和接口可用性为准，不把预览版或单一产品的开关状态推广到所有 Android 17 设备。

### Android 17 没有统一的“机器学习任务调度器”

固定源码标签（tag）中不存在面向所有应用、名为 `MLScheduler` 或等价名称的统一任务调度器。容易被混写成“机器学习调度”的能力分属不同层次：

- `JobScheduler` 根据约束、配额、应用待机分组和截止时间（deadline）决定后台任务何时可运行；
- `AppStandbyController` 可以把仅供系统使用的预测结果作为输入，但这不等于 `JobScheduler` 自己运行一个公开的机器学习模型；
- `OomAdjuster` 与 `ProcessStateController` 计算进程重要性，再把内存回收优先级 `oom_score_adj` 交给低内存终止守护进程 `lmkd`；
- Android 动态性能框架（ADPF）的 `PerformanceHintManager` 让应用报告工作时长目标，由系统和设备实现选择资源策略；
- ACK 6.18 的 EEVDF 公平任务选择算法、CPU 利用率上下限（uclamp）、CPU 集合（cpuset）与任务配置（task profile）仍是内核和系统策略机制，不是 Android 17 新增的通用机器学习调度 API。

如果设备厂商（OEM）的产品确有预测式调度扩展，结论至少要包含组件或包名、模型输入、控制输出、进入任务配置、uclamp 或其他执行机制的调用链，以及固定构建指纹下的对照跟踪数据。只有营销名称、版本号或一组没有原始数据的百分比，不能证明平台存在统一调度器。

## 隐私与后台限制也会改变性能工具

系统架构不仅由分区和内核组成。权限与后台策略同样会改变采集工具能看到什么、任务能运行多久。

### 包可见性

Android 11 对以 API 30 及以上为目标的应用限制包可见性。`PackageManager` 查询通常只返回自动可见和通过 `<queries>` 声明的包。`QUERY_ALL_PACKAGES` 只适用于少数核心场景，并受 Google Play 政策限制。

性能 SDK 不应通过枚举所有安装包推断竞争负载，也不该为了“兼容”直接申请全量查询权限。系统级工具、普通应用和可调试（debuggable）构建拥有不同权限边界，测试结论要注明由哪种身份采集。

### 后台执行时间线

| 版本 | 主要约束 | 设计影响 |
|---|---|---|
| Android 8.0 | 后台 Service 和隐式广播受限 | 持久延迟工作迁移到 `JobScheduler`/`WorkManager` |
| Android 12 | 后台启动前台服务受限；精确闹钟进入特殊权限模型 | 区分用户可见即时任务、持久任务和闹钟 |
| Android 14 | 面向新版本的前台服务必须声明类型和相应权限；多数新安装应用默认不再预授权精确闹钟能力 | Manifest 类型、运行时权限和 Play 政策一起检查 |
| Android 15 | `dataSync`、`mediaProcessing` 前台服务引入时间配额 | 长任务需要保存进度并处理超时（timeout）回调 |
| Android 16 | `JobScheduler` 任务的运行时配额限制继续趋严 | 不把前台服务当作任务配额豁免手段 |

`WorkManager` 适合需要持久调度且允许系统选择执行时机的任务，但不是所有后台工作的替代品。音频播放、导航、用户发起的数据传输、精确闹钟和短暂进程内任务，各自有不同 API 与政策边界。

## 诊断时怎样识别实际的版本变量

面对“旧版本正常，新版本变慢”，可以按下面的顺序收集信息：

1. 记录构建指纹、API 级别、应用版本、编译 SDK 版本（`compileSdk`）和目标 SDK 版本（`targetSdk`）；
2. 查询相关兼容性变更，确认行为是否由目标 SDK 版本门槛触发；
3. 对 ART、Media、Conscrypt 等问题记录当前启用的 Mainline 模块版本；
4. 用 `uname -r` 确认真实内核，不从 Android 大版本反推内核分支；
5. 涉及 HAL 时确认 HIDL/AIDL、服务进程和 Binder 域；
6. 涉及原生代码崩溃或内存问题时，记录 `getconf PAGE_SIZE`、ABI 和 ELF 对齐；
7. 涉及 Job 或前台服务时，记录待执行原因、停止原因、应用待机分组和约束变化；
8. 在两台设备上使用相同工作负载（workload）与采集配置，再比较系统性能跟踪工具 Perfetto 的数据。

Perfetto 里的进程名或时间片段（slice）名称只提供线索。例如出现 `hwbinder` 线程，说明某条独立进程形式的 HIDL HAL 路径仍在使用，不代表整个设备没有迁移 AIDL；看到 `dex2oat`，也要区分安装、OTA、Mainline 更新还是后台 DEX 优化。

## 常见误区

### “Android 17 设备一定运行 6.18 内核”

Android 17 支持多个历史 GKI 分支。`android17-6.18` 是当前新基线和本书使用的固定源码版本，不是所有升级设备的强制内核版本。

### “Treble 以后 framework 和 vendor 可以任意组合”

组合必须满足 VINTF、系统框架兼容性要求表（FCM）、KMI、强制访问控制机制 SELinux 和测试要求。稳定接口减少同步修改，不取消兼容约束。

### “Mainline 让所有系统组件都能通过 Play 更新”

只有纳入 Mainline 的模块具备对应更新路径，而且模块集合随版本演进。ART 的 Mainline 边界是 Android 12，不是 Android 10。

### “Profile-Guided Compilation 会让第一次启动必然很慢”

云端画像和基准画像可以让关键路径提前完成 AOT 编译。是否生效仍取决于分发渠道、代码使用画像、安装状态和 ART 配置。

### “16 KB 内存页只影响 NDK 应用”

应用自身没有 C/C++ 代码，也可能通过 SDK、数据库或图形库打包原生 `.so` 文件。应检查最终 APK/AAB，不能只检查业务源码。

### “Android 17 用机器学习统一调度 Job、进程与 CPU”

这些职责分别由 `JobScheduler`/App Standby、ActivityManagerService（AMS）/`OomAdjuster`、ADPF 和内核调度器承担。除非目标设备能给出明确的 OEM 组件和控制链路，否则应把这类说法记录为待验证的产品假设。

分析版本演进时，要把“平台发布了什么”“设备启用了什么”“应用因目标 SDK 版本得到了什么行为”分开。三层证据一致后，才能用版本差异解释性能现象。
