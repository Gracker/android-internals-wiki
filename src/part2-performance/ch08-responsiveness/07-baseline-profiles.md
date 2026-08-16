---

title: Baseline Profiles 与编译优化实践
chapter: '8.7'
section: '8.7'
status: "finalized"
applicable_versions: Android 7 (API 24) - Android 17 (API 37)
last_verified: "2026-06-20"
last_verified_against: "Android Developers Baseline/Startup/ProfileVerifier/Profileable docs (2026-06) + AOSP platform/art android-17.0.0_r1 ART Service"
confidence: medium
sources:
- type: official
  path: https://developer.android.com/topic/performance/baselineprofiles
- type: blog
  path: intake/research-feeds/2026-04-06-11-baseline-profiles-compilation-optimization.md
- type: blog
  path: intake/research-feeds/2026-04-04-07-ch08-startup-profiles-dex-layout-optimization.md
- type: official
  path: https://developer.android.com/topic/performance/baselineprofiles/create-baselineprofile
- type: official
  path: https://developer.android.com/topic/performance/baselineprofiles/debug-baseline-profiles
- type: official
  path: https://developer.android.com/guide/topics/manifest/profileable-element
tags:
- android
- research
- baseline-profiles
- art
- dexopt
- startup
- performance
pipeline_stage: ready-to-publish
task6_state: reviewed
task9_state: "reviewed"
task2b_state: "fixed"
last_idle_audit_at: "2026-08-02T18:35:07+08:00"
last_idle_audit_run_id: "20260802-183507-idle-audit-e1ac46d2"
---
# 8.7 Baseline Profiles 与编译优化实践

应用刚安装或升级时，设备还没有积累当前版本的本地运行 Profile。启动和高频交互路径中的 managed code（由 ART 管理的 Java / Kotlin 字节码）可能先由解释器执行，再经过 JIT（运行时即时编译），之后才由后台 profile-guided dexopt 按热点生成 AOT（提前编译）产物。Baseline Profile 允许开发者把已经验证过的类和方法规则随包提供，从首次运行开始缩短这段逐步达到稳定性能的时间。

这项能力跨越构建、分发和 ART 三个阶段：AGP / R8 将可读规则改写并打包，安装来源决定 Profile 何时进入设备，ART Service 再管理编译任务和产物。任意一个环节缺失时，即使包中存在 `baseline.prof`，当前进程也不一定已经使用对应的 AOT 代码。

本文以 Android 17 / API 37 的 `android-17.0.0_r1` 为平台源码基线，并将历史边界追溯到 Android 7。重点检查可以验证的生成、打包、安装、编译和测量路径。

## 为什么需要 Baseline Profiles

ART 需要同时平衡安装耗时、磁盘占用和运行速度。Android 5.0～6.0 倾向于在安装期间进行大范围 AOT；Android 7.0 改为由解释执行、JIT、本地 Profile 和后台 AOT 协作。这个变化缩短了安装时间，但新安装或刚升级的代码会经历一段尚未按照热点充分编译的阶段。

Baseline Profile 是开发者随构建产物提供的一组类和方法规则。ART 可以根据这些规则，对指定路径执行 profile-guided AOT（由性能画像指导的提前编译），减少解释执行和 JIT 预热。它适合启动、页面切换、列表滚动等可重复的高频路径，但不会修复主线程 I/O、锁竞争、布局过深或网络等待。官方概览给出的常见代码执行收益约为 30%，这个数字只用于说明大致量级；单个应用仍要使用同一包、同一设备和同一场景测量。

### Android 7 与 Android 9：两条时间线

Android 7.0（API 24）引入了混合编译路径：

1. 新代码可先由解释器执行。
2. JIT 根据设备上的运行行为编译热点，并记录本地 Profile。
3. 设备空闲并充电时，后台 dexopt 根据 Profile 进行 `speed-profile` 编译，也就是只对 Profile 覆盖的热点路径做速度优化。
4. 用户继续使用后，本地 Profile 仍会更新，编译结果也可能随之调整。

Android 9（API 28）增加了 Google Play Cloud Profiles 的分发能力。Play 聚合真实设备上的热点信息，再将可用的 Cloud Profile 提供给后续安装或更新。它有两个限制：只覆盖 Android 9 及以上版本的 Play 分发路径，并且新版本发布后需要一段时间积累样本。Android 7～8.1 没有 Cloud Profile；如果应用依赖 `androidx.profileinstaller`，Baseline Profile 会在应用首次运行时写入设备 Profile 目录，再等待后台 dexopt 编译。

这几类 Profile 的生产者、时机和用途不同：

| Profile | 生产者 | 可用时机 | 解决的问题 |
| --- | --- | --- | --- |
| Baseline Profile | 应用或库的开发者、CI | 构建时随包提供 | 提前描述已知的启动和高频 CUJ |
| Cloud Profile | Google Play 聚合 | Android 9+、Play 获得足够样本后 | 用线上行为补充开发者未覆盖的热点 |
| 本地运行 Profile | 单台设备上的 ART/JIT | 用户运行应用后 | 让该设备的编译结果随个人使用继续收敛 |

“包中有 Baseline Profile”和“设备已经完成 `speed-profile` 编译”是两个独立状态。Android 7～8.1、Play 安装、Android Studio / Gradle 安装和普通侧载的消费时机各不相同，不能因为安装已经完成就跳过编译状态检查。

### 版本边界

| 能力 | 平台或工具边界 | 说明 |
| --- | --- | --- |
| JIT、本地 Profile、后台 profile-guided dexopt | Android 7 / API 24 | ProfileInstaller 可以把 Baseline Profile 安装到这一代平台 |
| Cloud Profiles | Android 9 / API 28，Google Play | 非 Play 渠道没有这份聚合数据 |
| `ProfileVerifier` | Android 9 / API 28+ | 用于区分已编译、已入队和异常状态 |
| `<profileable>`、`android:shell` | Android 10 / API 29 | 允许 release-like 包被 shell 性能工具分析 |
| `<profileable android:enabled>` | Android 11 / API 30 | 控制应用能否被系统服务或 shell 分析 |
| ART Service | Android 14 起成为平台 dexopt 管理主路径 | 源码固定到 `android-17.0.0_r1` |

这张表描述的是平台能力，不等同于构建工具的推荐版本。当前官方工具链建议至少使用 AGP 8.0、Macrobenchmark 1.4.1 和 ProfileInstaller 1.4.1；新项目使用 AGP 8.2 及以上版本的 Baseline Profile Generator 模板，可以减少手工配置。

## 从文本规则到设备编译产物

排查 Profile 时要区分三层：仓库中的 HRF 文本、包内的二进制 Profile，以及设备上的 Profile 和 OAT / VDEX 编译产物。它们名称相似，却处于不同生命周期阶段。

### HRF：可审阅的生成结果

Baseline Profile Generator 输出 Human-Readable Format（HRF，人类可读格式）规则。使用当前插件时，常见路径如下：

- `src/<variant>/generated/baselineProfiles/baseline-prof.txt`
- `src/<variant>/generated/baselineProfiles/startup-prof.txt`

`baseline-prof.txt` 描述需要交给 ART 做 on-device（设备端）编译的类和方法。`startup-prof.txt` 是启动场景的子集，供 D8 / R8 在构建期间调整 DEX 布局。两份文本都可以进入版本库，也适合在代码评审中检查变动范围。

HRF 中的方法规则可能带有 `H`、`S`、`P` 标记，分别表示 hot、startup 和 post-startup，也就是热点、启动期和启动后使用的方法。团队通常不应手写大批规则；自动生成可以让方法签名、重载和 Kotlin 编译产物与当前 APK 保持一致。

### 包内：`baseline.prof` 与 `baseline.profm`

AGP 会把 HRF 编译成紧凑的 ART 二进制 Profile。检查构建产物时可以查看以下位置：

| 产物 | APK | AAB |
| --- | --- | --- |
| 二进制 Profile | `assets/dexopt/baseline.prof` | `BUNDLE-METADATA/com.android.tools.build.profiles/baseline.prof` |
| Profile 元数据 | `assets/dexopt/baseline.profm` | `BUNDLE-METADATA/com.android.tools.build.profiles/baseline.profm` |

`baseline.prof` 是规则主体。配套的 `baseline.profm` 保存 DEX 与 Profile 格式转换所需的元数据，使 ProfileInstaller 能为不同 Android 版本转换格式。进行手工 `.dm` 实验时，两者会分别改名为 `primary.prof` 和 `primary.profm`，再放入同名的 Dex Metadata 归档；`.dm` 是安装器可以与 APK 一起接收的 DEX 元数据文件。

二进制 `baseline.prof` 必须小于 1.5 MB。这个限制针对包内二进制文件，不能用 HRF 文本行数代替。范围过宽的规则可能增加代码体积、磁盘读取和编译成本；是否删减应根据二进制大小和基准结果决定，没有适用于所有应用的“几千行”阈值。

### 设备端：Profile 数据与编译产物

Android 17 的 ART Service 文档明确区分了 Profile 数据和编译产物路径：

- 当前与参考 Profile：`/data/misc/profiles/{cur/<user-id>,ref}/<package-name>/{primary,*.split}.prof`
- 主 APK 与 split 的编译产物：`/data/app/.../oat/<isa>/{base,split_*}.{art,odex,vdex}`

其中 OAT / ODEX 保存已编译代码，VDEX 保存经过验证的 DEX 相关数据，ART 文件可包含运行时使用的映像。设备、ABI、安装卷、split 和厂商配置都会改变完整路径。`/data/app/.../oat/arm64/base.odex` 只是常见示例，不能写成所有设备都固定存在的地址；读取这些目录通常还需要 root 或 userdebug 环境。日常验证应优先使用 `ProfileVerifier` 和 `dumpsys package dexopt`。

### 安装来源决定消费时机

当前官方调试文档把安装路径分为三组：

| 安装来源 | 常见行为 | 工程上的判断方式 |
| --- | --- | --- |
| Google Play | Play 管理 Baseline / Cloud Profile 的交付；设备可能走安装期 Dex Metadata 编译，也可能在后台设备更新中完成编译 | 不保证某次首启前一定完成，需要读取设备编译状态 |
| Android Studio 或 Gradle 安装 non-debuggable build | AGP 8.4 及以上版本自动触发设备端编译；AGP 8.4 以下没有这项自动行为 | 检查 AGP、variant 和 dexopt 状态 |
| 其他 installer、普通侧载 | ProfileInstaller 把包内 Profile 写入当前 Profile 并等待后续后台 dexopt | `ENQUEUED` 属于中间态，完成编译后再测收益 |

Google Play 的产品实现和设备后台任务会持续演进，OEM 也可以调整 dexopt 策略。因此，Play 路径中可能看到 `install-dm`，也可能看到后台更新完成编译。工程验收应同时满足三项证据：包内规则存在、设备编译状态符合预期、Macrobenchmark 能复现收益。

在 Android 9～11 的实验室环境中，可以将 APK 和包含 `primary.prof`、`primary.profm` 的同名 `.dm` 一起传给 `adb install-multiple`，通过 `install-dm` 路径完成安装期编译。官方手工流程将这种做法限定在 API 28～30；它适合用来理解 `reason=install-dm`，不应视为 Android 17 的通用侧载方案。

## Android 17 的 ART Service 锚点

Android 17 平台源码固定在 `android-17.0.0_r1`。相关目录包括：

- [`artd/`](https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/artd/)：执行 dexopt、产物校验和文件操作的守护进程实现。
- [`libartservice/`](https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/libartservice/)：system_server 中 ART Service 的 API、调度和状态管理。
- [ART Service README](https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/libartservice/service/README.md)：编译场景、reason、compiler filter 与存储位置的源码同仓说明。
- [`profman/`](https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/profman/)：ART Profile 的读取、合并和转储工具实现。

Android 17 中，安装、后台 dexopt、OTA 后处理和命令行请求都会进入 ART Service 管理的 dexopt 场景。安装时如果有可用的 Dex Metadata Profile，默认 compiler filter（编译过滤器）可以是 `speed-profile`；没有 Profile 时通常从 `verify` 开始，只做验证而不按热点生成优化代码。设备空闲并充电时，后台任务再根据 Profile 编译。源码文档也允许厂商通过属性和 API 调整默认策略，因此某台设备上的 reason（编译原因）和执行时机可能不同于 AOSP 默认值。

Cloud Profile 的服务端聚合和 Play 交付不在 AOSP `platform/art` 仓库中。公开资料足以确认它面向 Android 9 及以上版本的 Play 分发，却不足以推导私有服务端文件格式或调度实现。因此，不能采用“Android 16 云端预编译包”“SDM 固定格式”等无法由公开一手资料复核的说法。

## 生成与维护 Baseline Profile

### 用 Baseline Profile Generator 描述 CUJ

AGP 8.2 及以上版本的项目应优先使用 Android Studio 的 Baseline Profile Generator 模板。生成模块执行 `BaselineProfileRule`，通过 UIAutomator 运行启动和 Critical User Journey（CUJ，关键用户旅程），再把设备采集结果转换为 HRF。

下面的生成器只演示 launcher 冷启动；登录状态、深链、通知入口和滚动路径应按照产品行为分别建立独立场景：

```kotlin
@RunWith(AndroidJUnit4::class)
@LargeTest
class BaselineProfileGenerator {
    @get:Rule
    val rule = BaselineProfileRule()

    @Test
    fun launcherStartup() = rule.collect(
        packageName = "com.example.app",
        includeInStartupProfile = true,
    ) {
        pressHome()
        startActivityAndWait()
    }
}
```

`includeInStartupProfile = true` 会同时生成用于 DEX 启动布局的规则，只适合从入口到初始可交互界面的路径。列表滚动、搜索、下单等启动后的 CUJ 仍可以进入 Baseline Profile，但应关闭这个参数，避免把大量运行期代码放入首个 DEX。

当前插件提供按应用或 variant 生成的任务。CI 可以运行：

```bash
./gradlew :app:generateBaselineProfile
./gradlew :app:generateFreeReleaseBaselineProfile
```

第一条命令为 release build type 生成 Profile，第二条展示 `generate<Variant>BaselineProfile` 的任务命名形式。任务结束后，应检查目标 variant 的 `generated/baselineProfiles`，并将生成文件和对应 APK / AAB 保存在同一份 CI 证据中。

### 生成 variant 与最终 release 要分开

Profile 生成和最终发布对 R8 的要求不同：

| 阶段 | 混淆与优化 | 原因 |
| --- | --- | --- |
| Profile 生成 variant | 关闭 R8 重命名与优化 | 采集结果保留稳定、可映射的方法签名 |
| 最终 release | 开启 `isMinifyEnabled = true` 与完整 R8 优化 | 缩减代码、优化 DEX，并把 HRF 规则改写到发布后的符号 |
| Macrobenchmark 目标包 | 与待发布 release 行为一致 | 让测量反映用户拿到的代码与资源 |

Baseline Profile Gradle Plugin 会准备 `nonMinifiedRelease` 一类生成 variant。AGP / R8 在构建最终 release 时，将 Profile 规则重写为优化后的符号；AGP 8.2 的工具链改进提高了这一步的覆盖率。升级 AGP / R8、调整 keep 规则、修改 flavor 或重构启动调用链后，都应重新生成并测量，不能继续沿用旧 HRF，只检查文件是否仍然存在。

### 覆盖范围由用户路径决定

一份可维护的 Baseline Profile 通常包含：

- launcher、通知、深链等主要启动入口；
- 到 TTID 和 TTFD 之间执行的初始化与首屏代码；
- 高频页面切换、列表滚动、搜索等对延迟敏感的 CUJ；
- 应用自己的 Compose 或 View 调用路径。

覆盖率没有通用目标值。遗漏一个高频入口，会使该路径缺少提前编译；把低频管理页和整套回归测试都纳入，又可能增加编译和存储成本。每次新增 CUJ 后都要检查二进制大小，并使用 `FrameTimingMetric`、TTID 或 TTFD 验证该场景是否受益。

TTFD 依赖应用准确报告 fully drawn。View / Activity 应在异步首屏内容已经可交互后调用 `reportFullyDrawn()`；Compose 可以使用 `ReportDrawn`、`ReportDrawnWhen` 或 `ReportDrawnAfter`。过早上报会让生成器和基准遗漏首屏后半段代码，过晚上报则会把与首屏无关的工作错误纳入启动范围。

### Library 与 Compose

库可以在 AAR 中提供 Baseline Profile，AGP 构建应用时会合并依赖库规则和应用规则。库规则可以覆盖库内部的通用热点，却无法描述应用自己的导航、数据组装和自定义 Composable 调用链。因此，应用仍需为自身 CUJ 生成 Profile。

Startup Profile 规则由应用启动测试生成，库不能提供独立的 Startup Profile。Compose 项目也遵循同一边界：依赖库提供的 Baseline 规则覆盖运行时和 UI 库内部方法，应用规则再补充自己的组合树、入口和业务路径。收益取决于实际执行路径和未编译代码的成本，不能预设 Compose 一定比 View 获得更高比例的改善。

## Startup Profile：构建期的 DEX 布局输入

Startup Profile 和 Baseline Profile 可以共用采集场景，但由不同阶段消费：

| 项目 | Baseline Profile | Startup Profile |
| --- | --- | --- |
| 生成文本 | `baseline-prof.txt` | `startup-prof.txt` |
| 消费者 | 设备上的 ART | 构建期 D8/R8 |
| 作用 | 指导指定方法的 profile-guided AOT | 把启动代码优先放入主 DEX 并调整 DEX 内布局 |
| 包内可检查文件 | `baseline.prof` | 没有独立的 `startup.prof` |
| 验证方式 | ProfileVerifier、dexopt 状态、基准 | DEX 内容、AAB 中的 R8 元数据、基准 |

DEX layout 优化从 AGP 8.1 开始可用，AGP 8.3 起默认开启；当前官方推荐使用 AGP 8.2 及以上版本和 Baseline Profile Generator。最终 release 需要开启 R8。官方 Startup Profile 文档给出的常见结果，是在已有 Baseline Profile 的基础上再缩短约 15%～30% 启动时间；这仍然是经验范围，不能写成单个应用的验收阈值。

`includeInStartupProfile = true` 只应用于初始显示必经的场景。启动代码最好能够容纳在 `classes.dex` 中；容量不足后会进入后续 DEX，连续读取和类加载的局部性收益可能下降。现有证据能够确认的是 DEX 排布变化，不能仅根据规则文件推导 L1 I-Cache、TLB 或 16 KB page-size 的固定收益。Native ELF / ZIP 的 16 KB 对齐也属于另一项构建兼容工作。

AGP 8.8 及以上版本会把 R8 元数据写入 AAB。下面的命令提取这份元数据，并检查是否有 DEX 被标记为 startup：

```bash
unzip -j -o app-release.aab BUNDLE-METADATA/com.android.tools/r8.json
jq '.dexFiles' r8.json
```

输出对象中的 `"startup": true` 表示该 DEX 应用了 Startup Profile 布局。AGP 8.8 以下版本可以使用 APK Analyzer 检查启动类是否进入 `classes.dex`。两种检查都要配合启动基准，因为规则被应用不代表业务指标一定改善。

## 验证链路：包、设备状态、性能

### 第一步：确认包内 Profile

下面两组命令分别检查 APK 和 AAB 中是否包含 Baseline Profile 主体及元数据：

```bash
unzip -l app-release.apk \
  | grep -E 'assets/dexopt/baseline\.prof(m)?$'

unzip -l app-release.aab \
  | grep -E 'BUNDLE-METADATA/com\.android\.tools\.build\.profiles/baseline\.prof(m)?$'
```

包内至少要有 `baseline.prof`。如果缺失，应返回生成任务、source set、variant 和打包日志检查；此时查看设备上的 `verify` 状态没有诊断价值，因为 Profile 尚未进入构建产物。

### 第二步：确认设备已经编译

下面的 ADB 命令先以 `bg-dexopt` 原因触发一次编译，再读取目标包的 dexopt 状态：

```bash
PACKAGE_NAME=com.example.app

adb shell cmd package compile -r bg-dexopt "$PACKAGE_NAME"
adb shell dumpsys package dexopt \
  | grep -A 3 "$PACKAGE_NAME"
```

`status=speed-profile` 表示设备上存在按照 Profile 编译的产物。`status=verify` 只说明当前查询没有找到 profile-guided 编译产物，原因可能是尚未编译、安装路径没有触发编译、Profile 不可用或厂商策略不同；它不能证明 APK / AAB 中没有嵌入 Profile。`reason=install-dm`、`bg-dexopt`、`cmdline` 分别表示编译由安装期 Dex Metadata、后台任务和命令行请求触发。

手工执行 compile 会改变待测包的编译状态。进行性能对比时，应让 Macrobenchmark 管理 reset、编译和迭代，避免先运行 ADB 命令，再把结果误当成未编译样本。

### 第三步：用 ProfileVerifier 区分状态

`ProfileVerifier` 从 Android 9 / API 28 开始提供有效查询，可以区分 Profile 已打包、已写入等待编译，以及已经生成编译产物等状态。常见结果如下：

| 结果码 | 含义 | 处理 |
| --- | --- | --- |
| `RESULT_CODE_COMPILED_WITH_PROFILE` | 已安装匹配 Profile，且已有按 Profile 编译的产物 | 可以进入基准测试 |
| `RESULT_CODE_PROFILE_ENQUEUED_FOR_COMPILATION` | ProfileInstaller 已写入 Profile，等待后台 dexopt | 等待或在测试环境触发编译 |
| `RESULT_CODE_ERROR_NO_PROFILE_EMBEDDED` | 当前 APK 没有嵌入 Baseline Profile | 检查 variant 与打包 |
| `RESULT_CODE_NO_PROFILE` | ProfileInstaller 没有安装 Profile；APK 仍可能带有嵌入 Profile | 检查 initializer、安装来源和包内容 |
| `RESULT_CODE_COMPILED_WITH_PROFILE_NON_MATCHING` | 设备按一份与当前 APK 不完全匹配的参考 Profile 编译 | 重新安装同版本并检查 Play/PackageManager 路径 |
| `RESULT_CODE_ERROR_UNSUPPORTED_API_VERSION` | 平台低于 API 28 | 在 Android 7/8 改用 ADB 状态与基准 |

`ProfileVerifier` 适合给实验记录标注编译状态，不适合作为线上启动路径的阻塞条件。它会执行 I/O，也不应在主线程上同步等待结果。

### 第四步：Macrobenchmark 对比编译模式

同一个 APK 至少应比较未 AOT 和使用 Baseline Profile 两种状态。再加入“使用一段时间后的 JIT / 本地 Profile”和 `Full()`，可以帮助理解性能上限与稳定状态，但它们不能代替首装 Baseline Profile 样本。

下面四种模式与当前官方示例一致，分别构造无 AOT、Baseline Profile、使用后局部编译和完整 AOT 状态：

```kotlin
@Test
fun noAot() = startup(CompilationMode.None())

@Test
fun baselineProfile() = startup(
    CompilationMode.Partial(
        baselineProfileMode = BaselineProfileMode.Require,
    ),
)

@Test
fun postUsageProfile() = startup(
    CompilationMode.Partial(
        baselineProfileMode = BaselineProfileMode.Disable,
        warmupIteration = 3,
    ),
)

@Test
fun fullAotReference() = startup(CompilationMode.Full())
```

`None()` 表示没有 AOT 的冷态，`Partial(Require)` 强制要求 Baseline Profile，`Partial(Disable, warmupIteration = 3)` 模拟使用几次后的局部编译。`Full()` 可以减少 JIT 造成的波动，却很少代表用户设备上的真实分发状态。基准应在物理设备上运行，并固定 APK、系统版本、温控条件、启动入口和迭代策略。

官方 Now in Android 示例在 Pixel 7 上测得 TTID 229.0 ms（Baseline Profile）和 324.8 ms（无编译），相差约 29.5%。这是特定样例和设备的结果，可以用来校验测量方式，不能直接变成业务应用的承诺。启动场景应同时记录 TTID 和 TTFD；交互 CUJ 还应增加 `FrameTimingMetric` 或自定义 trace 区间。

Perfetto 用于解释两组结果为何不同，例如观察 JIT 活动、类加载、主线程长任务和首屏绘制。单个 slice 不能证明 Baseline Profile 已经安装，编译状态仍应通过 ProfileVerifier 或 dexopt 状态确认。

## 常见失败与排查顺序

| 现象 | 优先检查 | 常见原因 |
| --- | --- | --- |
| 包里没有 `baseline.prof` | 生成任务、目标 variant、source set、AGP 日志 | 只生成了别的 flavor，或 release 没消费生成文件 |
| ProfileVerifier 返回 `NO_PROFILE` | APK 内容、ProfileInstaller initializer、安装来源 | initializer 被禁用，或只检查了安装状态 |
| 长时间保持 `ENQUEUED` / `verify` | 后台 dexopt 条件、OEM 策略、存储空间 | Profile 已写入但尚未产生编译产物 |
| `NON_MATCHING` | 包版本、versionCode、Play/PackageManager 安装记录 | 参考 Profile 与当前 APK 的 DEX 不完全对应 |
| `Partial(Require)` 与 `None()` 差异很小 | CUJ 覆盖、R8 改写、测试包、TTFD 上报 | 路径没被采集，或瓶颈位于 I/O、锁、网络、渲染 |
| 启用 Startup Profile 后没有改善 | `startup-prof.txt`、`r8.json`、`classes.dex` 容量 | 启动规则没应用，或启动代码溢出主 DEX |
| Profile 二进制接近 1.5 MB | CUJ 数量、宽泛规则、库合并结果 | 低频路径过多或规则范围过宽 |

排查应按证据层级推进：先查包内文件，再查设备编译状态，然后比较基准，最后用 Perfetto 解释原因。这样可以分别处理没有打包、尚未编译、已编译但没有覆盖目标路径，以及瓶颈不在 managed code 编译中的情况。

## `<profileable>` 与 OEM dexpreopt

### Release-like 性能分析

`<profileable>` 允许性能工具分析 non-debuggable 包。元素本身和 `android:shell` 从 API 29 开始可用，`android:enabled` 在 API 30 加入。设置 `android:shell="true"` 后，shell 可以发起 simpleperf、Perfetto 和 `am profile` 等分析，但应用不会因此变成 debuggable。

下面的 manifest 配置放在 `<application>` 内，用于本地 release-like 基准测试和 trace：

```xml
<profileable
    android:shell="true"
    tools:targetApi="29" />
```

`tools:targetApi` 只帮助 lint 理解版本边界。是否在生产 manifest 中保留 `android:shell="true"`，应按照团队安全策略决定；性能测量包至少应保持 `debuggable=false`，避免调试运行时开销影响数据。

### OEM 系统镜像预编译

OEM dexpreopt（构建系统镜像时进行的 DEX 预编译）会处理 boot classpath、`system_server`、系统组件和预装 APK。`WITH_DEXPREOPT`、`WITH_DEXPREOPT_BOOT_IMG_AND_SYSTEM_SERVER_ONLY` 等构建开关控制镜像构建范围，产物位于 system 分区或 boot image 相关目录。应用 Baseline Profile 则随 APK / AAB 分发，由安装端 ART 或 ProfileInstaller 消费。

两套机制可能同时作用于预装应用，但发生的构建阶段、所需权限和产物归属都不同。不能把 `WITH_DEXPREOPT_*` 写成应用 Profile 开关，也不能把 OEM 私有的预装策略当作 AOSP 应用分发规则。Android 17 的存储位置和 dexopt 场景以 [ART Service README](https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/libartservice/service/README.md) 为源码依据。

## 与 AutoFDO 的分工

Baseline Profile 面向 ART 管理的 DEX 代码，回答哪些类和方法应按照 Profile 编译。[AutoFDO](../../part1-fundamentals/ch01-architecture/12-autofdo-optimization.md) 面向 native 可执行文件和共享库，使用采样或硬件分支轨迹反馈指导 LLVM / Clang 优化。OEM 可以在同一版本中使用两者，但二者的数据、工具链和产物不能互相替代：

| 维度 | Baseline Profile | AutoFDO |
| --- | --- | --- |
| 代码 | Java/Kotlin 编译出的 DEX | C/C++ 等 native 机器码 |
| 输入 | Macrobenchmark CUJ 生成的 ART 规则 | 由采样或分支轨迹生成的编译反馈 |
| 消费者 | ART / dex2oat | LLVM / Clang 链接与优化阶段 |
| 主要验证 | ProfileVerifier、dexopt、Macrobenchmark | 构建日志、符号化采样、native 基准 |

分析 AutoFDO、CoreSight 或调度实现等内核侧内容时，统一以 `android17-6.18-2026-06_r6` 为当前基线；Baseline Profile 的结论不依赖某个特定内核实现。

## 工程验收清单

一次发布的 Baseline Profile 验收至少应保留以下证据：

- 生成任务对应待发布 flavor，`baseline-prof.txt` 和 `startup-prof.txt` 的变更已经过评审；
- 生成 variant 关闭 R8，最终 release 开启 R8 并完成规则改写；
- APK/AAB 含 `baseline.prof`，二进制小于 1.5 MB；
- Startup Profile 场景只覆盖初始显示入口，AGP 8.8+ 的 `r8.json` 有预期的 `"startup": true`；
- 目标安装路径上的 ProfileVerifier 或 dexopt 状态已经记录；
- 在物理设备上使用 `None()` 和 `Partial(Require)` 比较 TTID、TTFD 或目标 CUJ；
- trace 能解释为何有收益或没有收益，结论范围不超过实际测量的设备、APK 和平台版本。

## 参考资料

### Android Developers

- [Baseline Profiles overview](https://developer.android.com/topic/performance/baselineprofiles/overview)
- [Create Baseline Profiles](https://developer.android.com/topic/performance/baselineprofiles/create-baselineprofile)
- [Configure Baseline Profile generation](https://developer.android.com/topic/performance/baselineprofiles/configure-baselineprofiles)
- [Debug Baseline Profiles](https://developer.android.com/topic/performance/baselineprofiles/debug-baseline-profiles)
- [Benchmark Baseline Profiles](https://developer.android.com/topic/performance/baselineprofiles/measure-baselineprofile)
- [Create Startup Profiles](https://developer.android.com/topic/performance/startupprofiles/dex-layout-optimizations)
- [Confirm Startup Profiles optimization](https://developer.android.com/topic/performance/baselineprofiles/confirm-startup-profiles)
- [`<profileable>` manifest element](https://developer.android.com/guide/topics/manifest/profileable-element)
- [ProfileVerifier API](https://developer.android.com/reference/androidx/profileinstaller/ProfileVerifier)

### AOSP 与交叉章节

- [ART `android-17.0.0_r1`](https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/)
- [ART 编译与 dexopt](../../part1-fundamentals/ch01-architecture/07-art-compilation.md)
- [AutoFDO 优化](../../part1-fundamentals/ch01-architecture/12-autofdo-optimization.md)
