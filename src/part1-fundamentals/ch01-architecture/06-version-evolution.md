---
title: "Android 版本演进中的架构变化"
chapter: "1.6"
section: "1.6"
status: finalized
pipeline_stage: ready-to-publish
applicable_versions: "Android 4.4 (API 19) - Android 17 (API 37)"
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
    path: "https://source.android.com/docs/core/architecture/treble"
  - type: official
    path: "https://source.android.com/docs/core/architecture/vintf"
  - type: official
    path: "https://source.android.com/docs/core/tests/vts/gsi"
  - type: official
    path: "https://source.android.com/docs/core/ota/modular-system"
  - type: official
    path: "https://source.android.com/docs/core/architecture/vndk"
  - type: official
    path: "https://source.android.com/docs/core/architecture/kernel/gki"
  - type: official
    path: "https://source.android.com/docs/core/architecture/kernel/android-common"
  - type: official
    path: "https://source.android.com/docs/core/architecture/bootloader/generic-bootloader"
  - type: official
    path: "https://source.android.com/docs/core/runtime"
  - type: official
    path: "https://source.android.com/docs/core/runtime/configure"
  - type: official
    path: "https://source.android.com/docs/core/runtime/jit-compiler"
  - type: official
    path: "https://developer.android.com/topic/performance/baselineprofiles"
  - type: official
    path: "https://developer.android.com/training/package-visibility"
  - type: official
    path: "https://developer.android.com/guide/practices/page-sizes"
  - type: official
    path: "https://source.android.com/docs/whatsnew/android-15-release"
  - type: official
    path: "https://source.android.com/docs/whatsnew/android-16-release"
  - type: official
    path: "https://developer.android.com/about/versions/16/summary"
  - type: official
    path: "https://developer.android.com/about/versions/17/features"
  - type: official
    path: "https://developer.android.com/about/versions/17/behavior-changes-17"
  - type: official
    path: "https://developer.android.com/about/versions/17/changes/messagequeue"
  - type: aosp
    path: "system/libvintf/VintfObject.cpp @ android-17.0.0_r1"
  - type: aosp
    path: "system/apex/apexd/apexd.cpp @ android-17.0.0_r1"
  - type: aosp
    path: "system/core/rootdir/init.zygote64_32.rc @ android-17.0.0_r1"
  - type: aosp
    path: "art/dex2oat/dex2oat.cc @ android-17.0.0_r1"
  - type: aosp
    path: "frameworks/base/core/java/android/os/CombinedMessageQueue/MessageQueue.java @ android-17.0.0_r1"
  - type: aosp
    path: "frameworks/base/apex/jobscheduler/framework/java/android/app/job/JobScheduler.java @ android-17.0.0_r1"
  - type: aosp
    path: "packages/modules/Profiling/framework/java/android/os/ProfilingManager.java @ android-17.0.0_r1"
  - type: aosp
    path: "packages/modules/Profiling/framework/java/android/os/ProfilingTrigger.java @ android-17.0.0_r1"
  - type: kernel
    path: "build.config.gki.aarch64 @ android17-6.18-2026-06_r6"
last_verified: "2026-07-25"
last_verified_against: "AOSP android-17.0.0_r1; ACK android17-6.18-2026-06_r6; Android Developers; source.android.com"
related_chapters:
  - "1.1"
  - "1.4"
  - "1.7"
  - "2.9"
  - "4.4"
  - "4.6"
  - "5.6"
  - "8.7"
polish_count: 1
polish_date: "2026-04-06"
polish_by: "task2b-polish"
task2b_fixed_at: "2026-05-08T23:46:33"
task9_result: pass-tech-review
task9_reviewed_date: "2026-06-07"
task9_reviewed_by: "openclaw-task9"
last_task9_at: "2026-06-07T04:33:40+08:00"
reviewed_date: "2026-06-29"
reviewed_by: "task2b-lite"
last_task6_at: "2026-06-29T13:35:00+08:00"
last_task6_audit: "2026-07-08"
last_task6_review_log: "logs/review/2026-06-07-04-review.md"
task6_state: reviewed
task6_result: pass-light-edit
task9_state: reviewed
task2b_state: fixed
task2b_result: fixed-lite
last_task2b_lite_at: "2026-06-07"
review_notes: "task9 P90 rework: 寄存器描述修正(翻倍→精确), Dalvik/Zygote已验证正确；2026-04-14 task6 | 2026-06-07 Task9 04: deep-review pass-tech-review。P0/P1 0；Android 17 官方版本差异补充已闭合，AOSP 源码锚点保持 android-16.0.0_r4/更低，自动晋升 finalized。轻量精修：文风、间距、图示占位; 2026-04-19 task6 re-review (revisiting): L1 fix x2 (not-X-Y pattern)；2026-05-01 task9 deep-review: needs-rework。P0/P1 技术问题已写入 queue。 | 2026-05-09 Task6 02:08：revisiting 写作复审；清理 frontmatter 重复键，修复 L1/L2 文风词与元叙述 8 处，无新增 L3/L4 回炉项，转 Task9 复审。 | 2026-05-09 Task9 02:30：needs-rework。P1 1：Perfetto 表格提示把 ART Mainline 写成 Android 11+，需改为 Android 12+ 或拆分 8-11/12+；P2 1：GSI 验证术语 CTS-V 应改为 VTS / CTS-on-GSI。"
last_task9_review_log: "logs/deep-review/2026-06-07-04-deep-review.md"
deepseek_cn_review_state: done
last_deepseek_cn_review_at: "2026-06-29"
last_task9_audit: "2026-07-13"
last_task9_autofix_at: "2026-06-07"
last_idle_audit_at: "2026-07-13"
---

# Android 版本演进中的架构变化

分析 Android 问题时，“这是 Android 17 设备”还不够。实际行为至少由五个版本维度共同决定：

1. 平台版本和具体 build；
2. 应用的 `targetSdkVersion` 以及已启用的 compat change；
3. ART、Media、Permission 等 Mainline 模块版本；
4. 厂商的 system、vendor 与 HAL 实现；
5. 内核分支、KMI 代际和设备调度配置。

同一平台版本的两台设备，可能运行不同的 Mainline 模块和不同代际的受支持内核。反过来，同一个应用安装在同一台设备上，只改变 targetSdk，也可能触发不同的 MessageQueue、权限或后台执行行为。

## 一张时间表先抓住主线

| 版本 | 主要架构变化 | 分析问题时的影响 |
|---|---|---|
| Android 4.4 / API 19 | ART 作为可选运行时预览 | ART 与 Dalvik 并存，不能把后来的 ART 行为套回所有 4.4 设备 |
| Android 5.0 / API 21 | ART 成为平台运行时；支持 64 位 ABI | 安装期编译、GC、Zygote 位数和原生 ABI 成为重要变量 |
| Android 7.0 / API 24 | ART 采用 JIT、AOT、解释执行的混合策略 | 首次运行、画像积累和后台 dexopt 会改变后续性能 |
| Android 8.0 / API 26 | Project Treble、VINTF、HIDL、VNDK | framework/vendor 边界被稳定接口、ABI 与测试套件约束 |
| Android 10 / API 29 | Project Mainline 与 APEX | 一部分系统组件可以脱离整机 OTA 更新 |
| Android 12 / API 31 | ART 进入 Mainline；GKI 2.0 成为关键内核架构 | 同一 Android 大版本的 ART 行为可能随模块更新变化 |
| Android 15 / API 35 | 平台支持 16 KB page size；VNDK 开始废弃 | native 二进制对齐和 vendor 依赖模型需要重新检查 |
| Android 16 / API 36 | GBL 支持、16 KB 兼容模式、系统触发 profiling、Job 配额调整 | 引导链、native 兼容和线上诊断出现新的可选能力 |
| Android 17 / API 37 | 无锁 MessageQueue、更多 profiling trigger、Job 等待原因统计 | targetSdk 与 API 37 新接口直接改变性能诊断路径 |

Material You 是 Android 12 的重要产品和 UI 变化，但它没有重构 system/vendor 或运行时边界。版本表聚焦会改变系统分层、二进制兼容或性能分析方法的节点。

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

每条边界解决的问题不同。SDK API 约束应用与平台，VINTF 约束 framework 与 vendor，KMI 约束 GKI 与厂商内核模块。把它们都称为“稳定接口”没有错，但不能互相替代。

### Treble、VINTF 与 HAL

Treble 在 Android 8.0 把 framework 和 vendor 实现分到明确的分区与兼容边界。新版 system 与旧 vendor 仍需满足双方声明的兼容契约；契约成立时，升级才有机会减少同步修改。

VINTF 提供这份契约：

- device manifest 声明设备提供的 HAL 及版本；
- framework compatibility matrix 声明 framework 要求的 HAL 能力；
- OTA、启动和兼容性测试根据匹配规则判断组合是否合法。

Android 8.0 初期主要使用 HIDL 描述跨分区 HAL。新的 HAL 现在使用具有 VINTF 稳定性的 AIDL。旧设备和旧 HAL 仍可能保留 HIDL，因此阅读 trace 时必须先确认接口类型。

`/dev/hwbinder` 主要对应 binderized HIDL HAL 的通信域。不能把所有硬件访问都归为 hwbinder：AIDL HAL、同进程 HAL、socket、共享内存和厂商自定义路径都有不同的调用形态；硬件操作也不天然比 framework Binder 慢，延迟取决于具体服务、设备和工作内容。

### GSI 是验证载体，不是“所有设备共用的 system”

GSI 是接近纯 AOSP 的通用 system image。Android 9 及以上的相关设备可以用 GSI 运行 VTS 和 CTS-on-GSI，验证 vendor 接口是否满足当前 framework 的要求。

GSI 能启动，只说明分区与接口组合越过了启动门槛。完整合规还需要 VTS、CTS-on-GSI 及设备类型要求的其他测试。性能也不能只凭 GSI 推断量产系统，因为量产 build 还包含厂商服务、HAL、调度参数和功耗策略。

### VNDK 与 linker namespace 的历史位置

Treble 还需要解决原生 ABI 可见性。VNDK 曾提供 vendor 可以依赖的一组 framework 原生库，linker namespace 则限制不同进程和模块能看到哪些库。

Android 15 开始废弃 VNDK。对以 Android 15 构建的 vendor/product 分区，原 VNDK 库像其他 vendor/product 可用库一样安装；VNDK APEX、相关版本属性和 vendor snapshot 等机制被移除或收缩。用于兼容旧 vendor image 的早期 VNDK APEX 仍可能存在，LL-NDK 也不属于上述废弃范围。

原生隔离仍由分区边界、稳定 AIDL/HIDL、linker namespace、LL-NDK 和构建依赖检查共同约束。排查库加载问题时，应以设备实际的 `ld.config.txt`、APEX 列表和已加载 `.so` 路径为准，不要预设所有 Android 15+ 设备都把依赖放进 Vendor APEX。

### Mainline 与 APEX

Android 10 的 Project Mainline 把一部分系统组件拆成可独立更新的模块。模块可以采用 APK 或 APEX：

- APK 适合普通 framework 组件和权限控制器一类模块；
- APEX 可以携带 native 库，并在启动早期由 `apexd` 验证、激活和挂载。

Mainline 让安全修复和组件更新不必总等整机 OTA，但“设备运行 Android 10”不代表所有后来出现的模块已经可更新。ART 从 Android 12 才成为 Mainline 模块。

这会改变复现方法。遇到 ART、Conscrypt、Media 或 Permission 行为差异时，除了 build fingerprint，还要记录活动 APEX/APK 模块版本。只对比 `Build.VERSION.SDK_INT` 可能漏掉变量。

### GKI 与 KMI

GKI 把通用内核主体和设备相关模块分开。KMI 规定 GKI 对 vendor kernel modules 暴露的接口，并在对应 KMI 代际内维持兼容。

稳定 KMI 并不表示任意 GKI 都能替换：

- 不同 GKI 内核或 KMI 代际之间不承诺模块兼容；
- vendor modules、设备树、boot 配置和厂商功能仍需匹配；
- 相同 Android 平台可以支持多个历史 ACK 分支。

Android 17 的新内核基线是 `android17-6.18`，本书当前 kernel 源码锚点为 `android17-6.18-2026-06_r6`。官方兼容表同时列出 Android 17 可支持的若干较早 GKI 分支，所以看到 Android 17 用户空间时，不能直接断言设备内核一定是 6.18。

### Android 16 的 GBL

Generic Bootloader 提供标准化、可更新的 UEFI 应用，包含通用 Android 引导逻辑、Fastboot 和厂商扩展接口。Android 16 引入平台支持，并建议符合条件的新 ARM64 设备集成。

GBL 仍依赖设备 boot firmware 提供 UEFI、AVB 和必要协议，也允许厂商扩展。它是可部署的标准化方案，不是 Android 16 设备无条件具备的统一 Bootloader。分析启动时间时，仍要记录实际 boot chain，不能只按系统版本判断。

## 从 Dalvik 到 ART：编译策略如何改变

### Android 4.4：ART 预览

Android 4.4 中，ART 是可选运行时，Dalvik 仍是常见默认路径。ART 尝试把更多 DEX 代码提前编译为机器码，用安装和存储成本换取运行期收益。

这段历史反映的是编译时机变化。成本可以落在安装期、首次运行、后台空闲期或运行时，不同策略会在这些阶段之间重新分配 CPU、存储和延迟，不能只用“ART 一定更快”概括。

### Android 5.0 到 6.0：以安装期 AOT 为主

Android 5.0 用 ART 取代 Dalvik 作为平台运行时，并正式支持 64 位 ABI。ART 在这个阶段主要通过 dex2oat 做安装期 AOT 编译。

不能把它写成“所有方法都必然编译，运行时零编译开销”。编译过滤器、系统应用预编译、类加载上下文和设备配置都会影响产物。可靠的判断来自具体包的编译状态，而不是版本印象。

64 位支持也不等于应用自动变快。ARM64 提供更多通用寄存器和新的 ABI，但指针、对象或 native 数据结构可能变大。性能结果取决于代码、编译器和内存访问模式。

64 位设备上的 Zygote 形态由产品配置决定。`zygote64`、`zygote64_32`、`zygote32_64` 等配置决定主、辅 Zygote 的位数；init service 名仍常见 `zygote` 与 `zygote_secondary`。不要仅凭 Android 版本假设一定存在两个 Zygote。

### Android 7.0 以后：JIT、AOT 与解释执行混合

Android 7.0 引入带代码画像的 JIT，并与 AOT、解释执行组合：

1. 未编译代码可以先解释执行；
2. JIT 编译运行期热点；
3. ART 记录方法与类的使用画像；
4. 后台 dexopt 按 Profile 做 `speed-profile` 编译；
5. 已编译代码和画像会随更新、空间压力或校验条件变化。

Profile-Guided Compilation 并不保证“第一次必慢、以后必快”。安装来源可能提供 Cloud Profile，应用和库也可以携带 Baseline Profile，帮助 ART 在用户首次运行前编译关键路径。这里分发的是 Profile，不应写成 Play 商店直接给每台设备下发可复用的 `.odex`/`.vdex` 机器码。

Android 16 的无缝应用更新优化也不是“云端编译”。它把 `dexopt`/`dex2oat` 移到安装流程更早的阶段，缩短包在代码和资源切换期间不可运行的时间。

### Android 12 以后：ART 版本不再只跟随系统大版本

ART 从 Android 12 起成为 Mainline 模块。Android 12 及以上设备可以通过 Google Play 系统更新获得运行时和编译器修复。因此，分析 JIT、GC、dexopt 或验证器行为时，需要同时记录：

- 平台 build；
- ART APEX 版本；
- 包的 compiler filter、Profile 和 dexopt reason；
- 是否刚经历安装、OTA 或 Mainline 更新。

`adb shell cmd package art dump <package>` 可以查看 ART Service 维护的包编译状态。命令输出属于诊断接口，字段可能随版本变化，自动化脚本应针对目标 build 验证。

## Android 15 到 17：当前需要适配的变化

### 16 KB page size

Android 15 开始支持以 16 KB 页大小构建平台。更大的页面能扩大 TLB 覆盖范围、减少部分页表遍历，但也可能增加内部碎片和小映射成本。官方基准给出的收益是特定设备与工作负载结果，不应转换成“所有应用都会提升固定百分比”。

应用兼容性主要取决于 native 代码：

- 纯 Java/Kotlin 代码通常不直接依赖页大小，但 SDK 或依赖库可能携带 `.so`；
- ELF `LOAD` segment 和 APK 内未压缩 native 库都需要正确对齐；
- `mmap()`、共享内存、页掩码和常量 `4096` 都要检查；
- 应使用当前 NDK/AGP 重新构建，并在 16 KB 设备或模拟器上验证。

Android 16 加入 16 KB backcompat mode，让一部分只按 4 KB 对齐的应用能够过渡运行；它不保证所有不兼容 native 二进制都能工作。Android 17 又提供测试属性，可把 backcompat 设为 `fatal`，让不兼容二进制立即终止：

```bash
adb shell setprop bionic.linker.16kb.app_compat.enabled fatal
adb shell setprop pm.16kb.app_compat.disabled true
```

这是设备级测试开关，不应由普通应用在生产环境设置。Google Play 从 2025 年 11 月 1 日起，要求面向 Android 15 及以上设备的新应用和更新支持 16 KB page size。

Android 16 还把 `basename()`/`dirname()` 使用的 TLS 缓冲区改为首次使用时单独分配。官方发布说明给出的结果是在 16 KB 系统上释放初始线程页中的约 8 KB 空间。这是 bionic 实现优化，不表示每个线程的总内存固定减少 8 KB。

### Android 16：系统触发 profiling 与 Job 配额

Android 15 / API 35 引入 `ProfilingManager` 的应用主动请求接口。Android 16 / API 36 增加系统触发 profiling：应用注册关注的触发类型，系统在 `reportFullyDrawn()` 或 ANR 等事件附近采集并把结果交给应用。

Android 16 还调整 JobScheduler 的普通和加急 Job 运行时配额。配额会考虑 standby bucket、任务启动时应用是否处于 top 状态，以及任务是否在前台服务运行期间执行。前台服务不再等同于“Job 一定不计配额”。排查任务未运行时，应读取 `pending reason`、`stop reason` 和约束，不能只看是否启动过前台服务。

### Android 17：MessageQueue、ProfilingTrigger 与 Job 诊断

以 API 37 为目标版本的应用在 Android 17 上默认使用新的无锁 `MessageQueue`。目标版本较低 target 应用可以通过 compat change 测试：

```bash
adb shell am compat enable USE_NEW_MESSAGEQUEUE <package>
adb shell am compat disable USE_NEW_MESSAGEQUEUE <package>
```

它改变的是 `MessageQueue` 内部实现，不是让主线程上的业务、布局和 Binder 等待自动消失。依赖 `mMessages` 等私有字段的反射代码需要迁移；具体实现见 §1.13。

API 37 扩展 `ProfilingTrigger`，新增或公开用于 cold start、OOM、过量 CPU 被杀、异常和 app compatibility 等场景的触发类型。不同 trigger 产生的 artifact 和停止条件不同，不能笼统写成“所有异常都自动保存完整 system trace”。应用仍需注册触发器、接收结果，并遵守系统限额。

`JobScheduler.getPendingJobReasonStats(jobId)` 返回 pending reason 到累计等待时长的映射。多个原因可以同时成立，所以各项时长之和可能超过任务实际等待时间。它适合回答“哪类约束长期阻止任务运行”，但不能替代 `getPendingJobReasonsHistory()`、`JobParameters.getStopReason()` 和业务侧幂等日志。

`android-17.0.0_r1` 源码仍用 aconfig/`@FlaggedApi` 管理部分新增接口和 trigger。应用应以最终 API 37 SDK、设备构建和 API 可用性为准，不把预览版或单一产品的 flag 状态推广到所有 Android 17 设备。

## 隐私与后台限制也会改变性能工具

系统架构不仅由分区和内核组成。权限与后台策略同样会改变采集工具能看到什么、任务能运行多久。

### 包可见性

Android 11 对以 API 30 及以上为目标的应用限制包可见性。`PackageManager` 查询通常只返回自动可见和通过 `<queries>` 声明的包。`QUERY_ALL_PACKAGES` 只适用于少数核心场景，并受 Google Play 政策限制。

性能 SDK 不应通过枚举所有安装包推断竞争负载，也不该为了“兼容”直接申请全量查询权限。系统级工具、普通应用和 debuggable 构建拥有不同权限边界，测试结论要注明采集身份。

### 后台执行时间线

| 版本 | 主要约束 | 设计影响 |
|---|---|---|
| Android 8.0 | 后台 Service 和隐式广播受限 | 持久延迟工作迁移到 JobScheduler/WorkManager |
| Android 12 | 后台启动前台服务受限；精确闹钟进入特殊权限模型 | 区分用户可见即时任务、持久任务和闹钟 |
| Android 14 | 面向新版本的前台服务必须声明类型和相应权限；多数新安装应用默认不再预授权精确闹钟能力 | Manifest 类型、运行时权限和 Play 政策一起检查 |
| Android 15 | `dataSync`、`mediaProcessing` 前台服务引入时间配额 | 长任务需要保存进度并处理 timeout 回调 |
| Android 16 | Job 运行时配额限制继续趋严 | 不把前台服务当作 Job 配额豁免手段 |

WorkManager 适合需要持久调度且允许系统选择执行时机的任务，但不是所有后台工作的替代品。音频播放、导航、用户发起的数据传输、精确闹钟和短暂进程内任务，各自有不同 API 与政策边界。

## 诊断时怎样识别实际的版本变量

面对“旧版本正常，新版本变慢”，可以按下面的顺序收集信息：

1. 记录构建指纹、API build fingerprint、API level、应用版本、compileSdk 和 targetSdk；
2. 查询相关 compat change，确认行为是否由 targetSdk 门槛触发；
3. 对 ART、Media、Conscrypt 等问题记录活动 Mainline 模块版本；
4. 用 `uname -r` 确认真实内核，不从 Android 大版本反推内核分支；
5. 涉及 HAL 时确认 HIDL/AIDL、服务进程和 Binder 域；
6. 涉及 native 崩溃或内存时记录 `getconf PAGE_SIZE`、ABI 和 ELF 对齐；
7. 涉及 Job/前台服务时记录 `pending reason`、`stop reason`、standby bucket 和约束变化；
8. 在两台设备上使用相同 workload 与采集配置，再比较 Perfetto。

Perfetto 里的进程名或 slice 名只提供线索。例如出现 `hwbinder` 线程，说明某条 HIDL binderized HAL 路径仍在使用，不代表整个设备没有迁移 AIDL；看到 `dex2oat`，也要区分安装、OTA、Mainline 更新还是后台 dexopt。

## 常见误区

### “Android 17 设备一定运行 6.18 内核”

Android 17 支持多个历史 GKI 分支。`android17-6.18` 是当前新基线和本书源码锚点，不是所有升级设备的强制内核版本。

### “Treble 以后 framework 和 vendor 可以任意组合”

组合必须满足 VINTF、FCM、KMI、SELinux 和测试要求。稳定接口减少同步修改，不取消兼容约束。

### “Mainline 让所有系统组件都能通过 Play 更新”

只有纳入 Mainline 的模块具备对应更新路径，而且模块集合随版本演进。ART 的 Mainline 边界是 Android 12，不是 Android 10。

### “Profile-Guided Compilation 会让第一次启动必然很慢”

Cloud Profile 和 Baseline Profile 可以让关键路径提前 AOT 编译。是否命中仍取决于分发渠道、Profile、安装状态和 ART 配置。

### “16 KB 页大小只影响 NDK 应用”

应用自身没有 C/C++ 代码，也可能通过 SDK、数据库或图形库打包 native `.so`。应检查最终 APK/AAB，而不是只检查业务源码。

分析版本演进时，要把“平台发布了什么”“设备启用了什么”“应用因 targetSdk 得到了什么行为”分开。三层证据一致后，才能用版本差异解释性能现象。
