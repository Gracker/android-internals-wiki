---
title: "Android 16 云端 Profile 与 dexopt 安装优化"
chapter: "16.6"
section: "16.6"
status: finalized
drafted_date: "2026-05-15"
applicable_versions: "Android 14 (API 34) - Android 17 (API 37)"
last_verified: "2026-07-01"
last_verified_against: "AOSP android-17.0.0_r1 ArtFileManager.java / ArtManagerLocal.java / DexMetadataHelper.java / ArtManagedInstallFileHelper.java; source.android.com ART Service configuration; Android Developers Baseline Profiles docs"
confidence: medium
tags: ["android-16", "art", "dexopt", "baseline-profile", "cloud-profile", "package-manager"]
related_chapters: ["1.7", "1.9", "8.7", "16.5", "21.4"]
created_by: "task2a-knowledge-gap"
created_date: "2026-05-15"
gap_source: "素材驱动/AOSP结构/官方文档"
sources:
  - type: official
    path: "https://source.android.com/docs/core/runtime/configure/art-service"
  - type: official
    path: "https://developer.android.com/topic/performance/baselineprofiles/overview"
  - type: official
    path: "https://developer.android.com/topic/performance/baselineprofiles/debug-baseline-profiles"
  - type: aosp
    path: "art/libartservice/service/java/com/android/server/art/ArtFileManager.java"
  - type: aosp
    path: "art/libartservice/service/java/com/android/server/art/DexMetadataHelper.java"
  - type: aosp
    path: "art/libartservice/service/java/com/android/server/art/ArtManagedInstallFileHelper.java"
  - type: aosp
    path: "frameworks/base/core/java/android/content/pm/DexMetadataHelper.java"
  - type: material
    path: "intake/research-feeds/2026-04-07-11-android16-cloud-compilation-baseline-startup-profiles.md"
  - type: blog
    path: "https://www.androidauthority.com/android-16-cloud-compilation-3541910/"
reviewed_by: "openclaw-task6"
reviewed_date: "2026-06-29"
review_type: task6-writing-quality-review
task6_result: "pass-light-edit"
last_task6_at: "2026-07-13T18:18:50+08:00"
last_task6_audit: "2026-06-07"
last_task6_review_log: "logs/review/2026-06-29-20-review.md"
review_notes: "2026-05-15 Task6：四层质检通过；L1/L2 轻量修复 6 处（frontmatter 元数据、结构性元叙述、标题与结尾措辞）；无 L3/L4 回炉项，送 Task9 技术复审。 | 2026-06-29 Task6 复审（Task9 auto-fix 后）：pass-light-edit。L1/L2 全部通过；禁用词零命中；SDM 证据边界写法清晰。Task9 auto-fix 涉及的源码锚点重锚（android-16→17.0.0_r1）写作质量合格。无 B 类回炉项，送 Task9 确认。 | 2026-07-13 Task6 re-review (revisiting after Task9 deep review + Task2B-lite fix): pass-light-edit。Task2B-lite 已修复 P0 DexMetadataHelper 路径 pm/dex/→pm/（正文+frontmatter 共 2 处）。L1 禁用词扫描零命中。L2 可读性通过。修复 frontmatter task9_p1_issues 计数不一致（0→1）。P1 ArtManagerLocal.deleteDexoptArtifacts() 方法引用由 Task2B-lite 审查后仅修复 P0，方法名准确性留待 Task9 复审确认。无 B 类回炉项。"
last_task9_audit: "2026-07-01"
last_task9_audit_log: "logs/deep-review/2026-07-01-15-audit.md"
last_task2b_lite_at: "2026-07-13"
task9_result: pass-tech-review
task9_state: reviewed
task2b_state: fixed
task2b_result: fixed-lite
task6_state: reviewed
pipeline_stage: ready-to-publish
last_task9_at: "2026-07-13T17:33:00+08:00"
last_task9_autofix_at: "2026-07-01"
last_task9_review_log: "logs/deep-review/2026-07-01-15-audit.md"
task9_reviewed_by: "openclaw-task9"
task9_reviewed_date: "2026-07-01"
task9_review_notes: "2026-07-13 Task9 deep review 发现 P0/P1 问题：1) DexMetadataHelper路径错误，已移除dex子目录；2) ArtManagerLocal.deleteDexoptArtifacts()方法已重构。P0 1 / P1 1 / P2 0；不可自动晋升，需 Task6 复审。P0/P1 问题已写入 queue.json，建议优先修复源码路径错误和方法引用过时问题。"
last_task6_at: 2026-07-13T17:17:00+08:00
task6_reviewed_date: "2026-07-13"
task9_p0_issues: 1
task9_p1_issues: 1
task9_p2_issues: 0
deepseek_cn_review_state: done
last_deepseek_cn_review_at: 2026-07-13
---

# 16.6 Android 16 云端 Profile 与 dexopt 安装优化

Android 14 之后，应用侧 AOT 编译的控制面转到了 ART Service。Android 16 引入 SDM（Secure Dex Metadata），所以本章保留 Android 16 的历史标题；当前源码结论统一核对到 Android 17 / `android-17.0.0_r1`。

Cloud Profile、Baseline Profile 和 Startup Profile 都会影响发布包的代码执行成本，但作用阶段不同。应用开发者能稳定控制的是 Baseline Profile、Startup Profile、`.dm` 验证和本地编译状态检查。云端编译产物是否下发，取决于安装渠道、分发策略、设备端 ART 支持和产物校验结果。AOSP 能证明设备端如何接收、验证和管理产物，不能证明 Google Play 对某个包采用了哪条分发策略。

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 **Cloud Profile、Baseline Profile、Startup Profile 的职责边界**：区分 Play 聚合热点、开发者随包 profile、DEX 布局 profile。
- 🔹 **Dex Metadata (.dm) 在安装与后台编译中的位置**：说明 `.dm` 的匹配规则、可携带 profile / VDEX，以及 ART Service 如何识别。
- 🔹 **BackgroundDexOptService 与 ART Service 的调度路径**：Android 14+ 以 ART Service 为 dexopt 控制面，后台任务按设备状态触发。
- 🔹 **System Dexopt Manager 与 Cloud Profile 的分工**：把公开可核对的 ART Service 能力和 Play 分发侧推测边界分开。
- 🔹 **开发者能控制的 profile 产物与验证命令**：给出包内检查、设备端编译、`dumpsys` / verbose result 验证路径。
- 🔹 **安装耗时、首次启动、后续启动之间的取舍**：说明安装期省时、首次启动收益和后续后台编译之间的关系。

### 扩展（可选深入）

- 🔸 Play 分发与非 Play 渠道的 profile 差异。
- 🔸 Android 16/17 ART Service 行为变更跟踪。
<!-- outline-end -->

## 三类 Profile 分别解决什么问题

安装优化和启动优化混在一起时，Baseline Profile 和 Cloud Profile 的关系容易被读错。Profile 本身只是“哪些类和方法更该被优化”的输入，能否变成更快的启动，要看安装渠道和 ART Service 是否把它用于 `speed-profile` 编译。

| 类型 | 生产者 | 分发位置 | 主要作用 | 开发者控制度 |
|------|--------|----------|----------|--------------|
| Baseline Profile | 应用或库开发者，通常由 Macrobenchmark / Gradle 生成 | APK / AAB 内的 `baseline.prof`、`baseline.profm`，或转换后的 `.dm` | 让新用户和每次更新后的关键路径更早被 AOT 编译 | 高：CI 可生成、检查、回归验证 |
| Startup Profile | 应用构建流程，AGP / R8 消费 | 构建期输入，不等同于运行期 profile 文件 | 指导 DEX layout，把启动路径相关代码放到更友好的布局里 | 中：依赖 AGP、R8 和规则覆盖 |
| Cloud Profile | Google Play 侧基于真实用户数据生成 | Play 分发路径，设备端由 ART Service 尝试消费 | 补齐单设备本地 profile 不可用或样本不足的场景 | 低：开发者只能间接影响覆盖路径 |

Baseline Profile 面向 Day-0：应用还没有在这台设备上跑过，也能把启动、登录、首页、列表滚动这类关键路径提前交给 ART。Startup Profile 面向布局：它影响 DEX 中代码排列，减少启动阶段跨 DEX、跨页面读取带来的 I/O 成本。Cloud Profile 面向分发规模：当 Play 已经有足够样本时，它能给新安装设备提供更接近真实热路径的 profile 输入。

## `.dm` 是 Profile 进入安装路径的外壳

Dex Metadata 文件使用 `.dm` 后缀，和目标 APK 按文件名配对。AOSP `frameworks/base/core/java/android/content/pm/dex/DexMetadataHelper.java` 的规则是 `base.apk` 对应 `base.dm`；安装器不接受没有 APK 配对的独立 `.dm` 文件。

Android 17 的校验边界分两层：

- `ArtManagedInstallFileHelper.validateDmFile()` 检查同目录下能否找到对应 APK。
- framework 侧 `validateDexMetadataFile()` 用 `StrictJarFile` 打开归档。源码注释提到 `manifest.json`、package name 和 version code，但 r1 方法体没有解析或比对这些字段。

ART Service 侧还会继续解析 `.dm` 的内容。`art/libartservice/service/java/com/android/server/art/DexMetadataHelper.java` 会读取 `config.pb`，并根据 ZIP 里的 profile entry、VDEX entry 判断类型：只有 profile、只有 VDEX，或 profile + VDEX。这个设计解释了为什么 `.dm` 不能简单理解成“Baseline Profile 文件”：它是一个容器，profile 只是其中一种可携带内容。

`.sdm` 是另一种文件。r1 的命名包含 ISA，例如 `base.arm64.sdm`；`validateSdmFile()` 会检查 ISA、APK v3 签名、SDM v3 签名，并要求两边 signer 完全一致。不能把 `.dm` 的轻量校验套到 `.sdm`，也不能把普通 Dex Metadata 和 cloud dexopt artifact 写成同一个容器。

验证 `.dm` 的低成本路径是把它和 APK 一起侧载，再强制跑一次 `speed-profile` 编译。下面这组命令只验证当前包能否按外部 profile 编译，不代表分发侧已下发 Cloud Profile 或 SDM：

```bash
adb install-multiple -r base.apk base.dm
adb shell pm art clear-app-profiles com.example.app
adb shell pm compile -m speed-profile -f -v com.example.app
adb shell pm art dump com.example.app
```

`pm art clear-app-profiles` 清理 current/reference 等本地 profile，保留 cloud profile、embedded profile 等外部 profile。`pm compile -m speed-profile -f -v` 会在 verbose result 中输出 `actualCompilerFilter`。值为 `speed-profile` 说明 ART 找到了可用 profile；值为 `verify` 时，应检查文件名、格式和 DEX checksum。`pm art dump` 是 Android 17 ART Service 的直接状态入口，`dumpsys package dexopt` 可作为兼容旧工具的补充。

## ART Service 接管了 Android 14 之后的 dexopt 控制面

Android 13 及更早版本里，很多 dexopt 逻辑仍在 Package Manager 一侧。Android 14 开始，source.android.com 明确写到：应用的设备端 AOT 编译由 ART Service 处理，ART Service 属于 ART Mainline 模块，可通过系统属性和 Java API 调整。

默认编译原因里，`bg-dexopt` 对应 `speed-profile`。后台 dexopt 通常优先使用 profile 指导编译，减少相对全量 `speed` 的编译工作与产物体积。官方默认值包含：

```text
pm.dexopt.first-boot=verify
pm.dexopt.boot-after-ota=verify
pm.dexopt.boot-after-mainline-update=verify
pm.dexopt.bg-dexopt=speed-profile
pm.dexopt.inactive=verify
pm.dexopt.cmdline=verify
pm.dexopt.shared=speed
```

这组默认值反映了 Android 编译策略的取舍：开机和 OTA 后优先保证系统可用，后台空闲阶段再补 profile-guided 编译。`pm.dexopt.shared` 是一个特殊兜底项，面向被其他应用通过 `<uses-library>` 或 `Context#createPackageContext(..., CONTEXT_INCLUDE_CODE)` 使用的包。官方文档说明，这类包出于隐私原因不能使用本地 profile；如果请求 profile-guided 编译，ART Service 会先尝试使用 Cloud Profile，找不到 Cloud Profile 时再退回 `pm.dexopt.shared` 指定的 filter。

Android 17 exact tag 由 `BackgroundDexoptJob` 构造任务并执行工作，`BackgroundDexoptJobService` 作为 JobService 入口；旧资料里的 `BackgroundDexOptService` 类名不适用于这个 tag。常规后台任务的 job ID 为 `27873780`，周期为一天，要求 device idle、charging、battery-not-low。用户安装后马上启动时，后台 dexopt 可能尚未运行。线下验证启动收益时，除了检查包内 `baseline.prof`，还要读取当前设备的 dexopt 状态。

## Android 16 的 SDM 与云端编译

Android 16 引入 SDM 格式，Android 17 r1 保留完整的设备端管理路径。Play 侧如何决定生成、下发和灰度，公开开发者资料没有给出可逐包验证的规则。

AOSP android-17.0.0_r1 的 `ArtFileManager` 仍然把 SDM 纳入可写与可用产物列表。源码里 `getWritableArtifacts()` 会为 primary dex 构造 `SecureDexMetadataWithCompanionPaths`；`getUsableArtifacts()` 也会识别 `ArtifactsLocation.SDM_DALVIK_CACHE` 和 `ArtifactsLocation.SDM_NEXT_TO_DEX`。这说明 ART Service 的产物管理已经知道“SDM 位置上的编译产物”这一类对象。

`ArtManagerLocal.deleteDexoptArtifacts(snapshot, packageName)` 在注释里把 cloud dexopt artifacts 单列出来，删除范围包括 VDEX、ODEX、ART、SDM、SDC。`PrimaryDexopter` 还会创建 SDC，并在本地 dexopt 成功后删除不再需要的 SDM/SDC。设备端能够管理这些文件，并不说明某次 Play 安装一定携带了它们。

外部报道把 Android 16 Cloud Compilation 描述为：分发侧运行编译，再把预生成产物放进 SDM 随 APK 下发。AOSP r1 只覆盖设备端半程：识别 SDM artifact location、校验 ISA 与签名、把 SDM 交给 ART 工具、清理相关文件。它没有公开 Google Play 的样本门槛、ABI 选择、生成服务或灰度策略。

可验证的结论是：Android 16 起设备端具备接收和管理 SDM/cloud dexopt artifacts 的能力，Android 17 r1 延续了这条路径，并执行前文所述的 ISA 与签名校验。某次安装是否使用这些产物，要结合安装来源、安装文件、`pm art dump` 和实际编译结果判断。支持 SDM 不等于每次安装都会省去设备端 dexopt。

## System Dexopt Manager 的分发侧边界

目前公开 AOSP 中可稳定引用的设备端入口是 ART Service、`artd`、`pm compile`、`BackgroundDexoptJob` 和 `ArtManagerLocal`。如果材料里出现 System Dexopt Manager 或 SDM 管理器这类叫法，写正文时不要把它们包装成一个可在 AOSP 中搜索到的系统服务类。

公开资料能支撑的边界可以拆成四部分：

- Play / 安装来源：决定是否提供 Cloud Profile 或 SDM 产物，也决定用户额外下载多少编译元数据。
- Package Manager / Installer：完成 APK、split、`.dm`、`.prof`、`.sdm` 的路径配对和相应校验。
- ART Service：根据安装原因、profile 可用性、系统属性和设备状态决定 compiler filter，并管理 OAT、VDEX、ART、SDM、SDC 等产物。
- `artd` / `dex2oat`：执行本地编译，或在已有可用产物时跳过不必要的本地工作。

这个分工能避免两个误判：把 Play 侧能力说成 AOSP 设备端类名；把 Cloud Profile 和 Cloud Compilation 合并成同一件事。Cloud Profile 是 profile 输入，Cloud Compilation / SDM 更接近预生成编译产物的分发和管理路径。

## 开发者能控制什么

应用侧能稳定控制三件事：生成 profile、确保产物进包、用同一台设备复核编译状态。

CI 中应把 Baseline Profile 当成 release 产物的一部分检查。官方当前给出的稳定检查点是 APK 内的 `/assets/dexopt/baseline.prof`，以及 AAB 内的 `/BUNDLE-METADATA/com.android.tools.build.profiles/baseline.prof`。Startup Profile 是构建期 DEX layout 输入，包内没有独立 `startup.prof` 可供安装时检查；AGP 8.8 及以上可结合 AAB 中的 `r8.json` 查看 startup DEX 标记。

```bash
unzip -l app-release.apk | grep 'assets/dexopt/baseline.prof'
unzip -l app-release.aab | grep 'BUNDLE-METADATA/com.android.tools.build.profiles/baseline.prof'
```

这些命令只证明构建产物包含 Baseline Profile。非 Play 本地安装还要确认 AGP/ProfileInstaller 的安装路径，或显式使用配对的 `.dm`。设备端状态可用以下命令检查：

```bash
adb install -r app-release.apk
adb shell pm compile -m speed-profile -f -v com.example.app
adb shell pm art dump com.example.app
```

如果输出仍停在 `verify`，应查文件名、DEX checksum、安装来源和 AGP/ProfileInstaller 行为。不要直接归因到云端编译。`actualCompilerFilter=speed-profile` 也只证明存在可用 profile，不能区分 Baseline、Cloud 或本地采集来源。启动收益还要用 Macrobenchmark 在同一包、同一设备、同一脚本下对比 `CompilationMode.None()` 与 `CompilationMode.Partial()`，指标至少包含 TTID、TTFD 和启动阶段 jank。

## 安装耗时和启动收益不是同一个指标

Profile 体系经常同时影响安装、首次启动和后续启动，但三个指标不能互相替代。

- 安装耗时：看 session 提交、APK 复制、签名校验、包扫描、metadata 校验、dexopt 或 SDM 产物接收。可用 cloud dexopt artifact 可能减少设备端重复编译工作，但还会增加产物下载、校验和写盘。
- 首次启动：看启动路径是否已经有可用 OAT / VDEX / ART 产物，是否减少解释执行、JIT 热身和 page fault。Baseline Profile 的收益主要体现在这里。
- 后续启动：看本地 JIT profile、后台 `bg-dexopt`、Cloud Profile 是否继续补齐热点路径。这个阶段的收益会随用户行为收敛。

设备性能、存储速度、包体、DEX 数量和网络都会改变收益分布。评价方案时要把安装 wall time、设备端 dex2oat CPU time、下载字节、TTID、TTFD、编译状态分开记录。

## 与应用实战章节的交叉引用

- Baseline Profile 生成、调试、Macrobenchmark 对比流程详见 [[04-baseline-profile-practice|21.4 Baseline Profile 实战]]。
- ART 编译策略、compiler filter、JIT/AOT 演进详见 [[07-art-compilation|1.7 ART 编译管线与 dex2oat 优化]]。
- PMS 安装路径、`PackageInstallerSession`、`InstallPackageHelper` 和 `DexOptHelper` 详见 [[09-package-manager|1.9 Package Manager]]。

设备端 ART Service 和 SDM 管理路径已有可核对源码，开发者可以通过 `pm compile -v` 与 `pm art dump` 验证设备状态。分发侧策略仍要以渠道文档和安装结果为准，不能由 AOSP 设备端源码反推。

## 参考资料

- [ART Service configuration](https://source.android.com/docs/core/runtime/configure/art-service)
- [Baseline Profiles overview](https://developer.android.com/topic/performance/baselineprofiles/overview)
- [Debug Baseline Profiles](https://developer.android.com/topic/performance/baselineprofiles/debug-baseline-profiles)
- [Create Startup Profiles](https://developer.android.com/topic/performance/startupprofiles/dex-layout-optimizations)
- [AOSP r1：ArtManagerLocal.java](https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/libartservice/service/java/com/android/server/art/ArtManagerLocal.java)
- [AOSP r1：ArtFileManager.java](https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/libartservice/service/java/com/android/server/art/ArtFileManager.java)
- [AOSP r1：ArtManagedInstallFileHelper.java](https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/libartservice/service/java/com/android/server/art/ArtManagedInstallFileHelper.java)
- [AOSP r1：ART DexMetadataHelper.java](https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/libartservice/service/java/com/android/server/art/DexMetadataHelper.java)
- [AOSP r1：BackgroundDexoptJob.java](https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/libartservice/service/java/com/android/server/art/BackgroundDexoptJob.java)
- [AOSP r1：PrimaryDexopter.java](https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/libartservice/service/java/com/android/server/art/PrimaryDexopter.java)
- [AOSP r1：ArtShellCommand.java](https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/libartservice/service/java/com/android/server/art/ArtShellCommand.java)
- [AOSP r1：framework DexMetadataHelper.java](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/content/pm/dex/DexMetadataHelper.java)
