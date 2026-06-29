---


title: "Android 16 云端 Profile 与 dexopt 安装优化"
chapter: "16.6"
section: "16.6"
status: ready-for-review
drafted_date: "2026-05-15"
applicable_versions: "Android 14 (API 34) - Android 17 (API 37)"
last_verified: "2026-06-08"
last_verified_against: "AOSP android-17.0.0_r1 ArtFileManager.java / PrimaryDexopter.java / DexMetadataHelper.java; source.android.com ART Service configuration; Android Developers Baseline Profiles docs"
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
    path: "frameworks/base/core/java/android/content/pm/dex/DexMetadataHelper.java"
  - type: material
    path: "intake/research-feeds/2026-04-07-11-android16-cloud-compilation-baseline-startup-profiles.md"
  - type: blog
    path: "https://www.androidauthority.com/android-16-cloud-compilation-3541910/"
reviewed_by: "openclaw-task6"
reviewed_date: "2026-06-29"
review_type: task6-writing-quality-review
task6_result: "pass-light-edit"
last_task6_at: "2026-06-29T20:15:13+08:00"
last_task6_audit: "2026-06-07"
last_task6_review_log: "logs/review/2026-06-29-20-review.md"
review_notes: "2026-05-15 Task6：四层质检通过；L1/L2 轻量修复 6 处（frontmatter 元数据、结构性元叙述、标题与结尾措辞）；无 L3/L4 回炉项，送 Task9 技术复审。 | 2026-06-29 Task6 复审（Task9 auto-fix 后）：pass-light-edit。L1/L2 全部通过；禁用词零命中；SDM 证据边界写法清晰。Task9 auto-fix 涉及的源码锚点重锚（android-16→17.0.0_r1）写作质量合格。无 B 类回炉项，送 Task9 确认。"
last_task9_audit: "2026-06-08"
last_task9_audit_log: "logs/deep-review/2026-06-08-18-audit.md"
last_task2b_lite_at: "2026-06-29"
task9_result: "auto-fixed"
task9_state: "pending"
task2b_state: "fixed"
task6_state: "reviewed"
pipeline_stage: "task9_pending"
last_task9_at: "2026-06-29T16:41:24+08:00"
last_task9_autofix_at: "2026-06-29"
last_task9_review_log: "logs/deep-review/2026-06-29-16-deep-review.md"
task9_reviewed_by: "openclaw-task9"
task9_reviewed_date: "2026-06-29"
task9_review_notes: "2026-06-29 Task9 auto-fix: 将 SDM 产物管理源码锚点从 android-16.0.0_r1 重锚到 android-17.0.0_r1；无新增 P0/P1。"
task6_reviewed_date: "2026-06-29"
---

# 16.6 Android 16 云端 Profile 与 dexopt 安装优化

Android 14 之后，应用侧 AOT 编译的控制面转到 ART Service。到 Android 16，公开源码已经出现 SDM 相关的产物管理路径，外部报道也把它和 Play 分发侧的 Cloud Compilation 放在一起讨论。

Cloud Profile、Baseline Profile、Startup Profile、Dex Metadata 和 SDM 处在同一套 ART 编译体系里，但解决的问题不同。应用开发者能稳定控制的是 Baseline Profile、Startup Profile、`.dm` 验证和本地编译状态检查；云端编译是否命中，取决于安装渠道、Play 分发策略、设备端 ART 支持和产物校验结果。

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

Dex Metadata 文件使用 `.dm` 后缀，和目标 APK 按文件名配对。AOSP `frameworks/base/core/java/android/content/pm/dex/DexMetadataHelper.java` 里的规则很明确：`base.apk` 对应 `base.dm`；安装器不支持单独提交一个没有 APK 配对的 `.dm` 文件；开启 manifest 校验时，`.dm` 内的 `manifest.json` 还要匹配包名和 versionCode。

ART Service 侧还会继续解析 `.dm` 的内容。`art/libartservice/service/java/com/android/server/art/DexMetadataHelper.java` 会读取 `config.pb`，并根据 ZIP 里的 profile entry、VDEX entry 判断类型：只有 profile、只有 VDEX，或 profile + VDEX。这个设计解释了为什么 `.dm` 不能简单理解成“Baseline Profile 文件”：它是一个容器，profile 只是其中一种可携带内容。

验证 `.dm` 的最低成本路径是把它和 APK 一起侧载，再强制跑一次 `speed-profile` 编译。下面这组命令只验证当前包能不能被 ART Service 按 profile 消费，不代表 Play 云端编译已经命中：

```bash
adb shell pm art clear-app-profiles com.example.app
adb shell pm compile -m speed-profile -f -v com.example.app
adb shell dumpsys package dexopt | grep -A 6 com.example.app
```

`pm art clear-app-profiles` 先清理设备运行时产生的本地 profile，避免把本地历史数据误判成随包 profile 的收益。`pm compile -m speed-profile -f -v` 会在 verbose result 中暴露 `actualCompilerFilter`。看到 `actualCompilerFilter=speed-profile`，才说明这次编译吃到了可用的 profile；看到 `actualCompilerFilter=verify`，常见原因是 `.dm` 文件名不匹配、格式不对，或 profile 中记录的 DEX checksum 和 APK 不一致。

## ART Service 接管了 Android 14 之后的 dexopt 控制面

Android 13 及更早版本里，很多 dexopt 逻辑仍在 Package Manager 一侧。Android 14 开始，source.android.com 明确写到：应用的设备端 AOT 编译由 ART Service 处理，ART Service 属于 ART Mainline 模块，可通过系统属性和 Java API 调整。

默认编译原因里，`bg-dexopt` 对应 `speed-profile`。后台 dexopt 的常规目标不是全量 `speed`，而是尽量利用 profile 指导编译，减少编译时间和产物体积。官方默认值包含：

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

后台任务仍然受设备状态约束。AOSP `BackgroundDexoptJob` 使用 JobScheduler，周期任务要求设备 idle、charging、battery-not-low；这解释了为什么用户安装后马上启动，未必已经拿到后台 dexopt 的收益。线下验证启动收益时，不能只看包里有没有 `baseline.prof`，还要看当前设备的 dexopt 状态。

## Android 16 的 SDM 证据边界

Android 16 云端编译目前要分两层写：AOSP 里能看到设备端对 SDM 产物的支持；Play 侧如何生成、签名、下发和灰度，公开资料还不完整。

AOSP android-17.0.0_r1 的 `ArtFileManager` 仍然把 SDM 纳入可写与可用产物列表。源码里 `getWritableArtifacts()` 会为 primary dex 构造 `SecureDexMetadataWithCompanionPaths`；`getUsableArtifacts()` 也会识别 `ArtifactsLocation.SDM_DALVIK_CACHE` 和 `ArtifactsLocation.SDM_NEXT_TO_DEX`。这说明 ART Service 的产物管理已经知道“SDM 位置上的编译产物”这一类对象。

`ArtManagerLocal.deleteDexoptArtifacts()` 的注释还把 cloud dexopt artifacts 单列出来，删除范围包括 VDEX、ODEX、ART、SDM、SDC 文件。这能证明设备端已有云端 dexopt 产物的清理路径，但不能推出 Play 商店已经对所有 Android 16 设备启用云端编译。

外部报道把 Android 16 Cloud Compilation 描述为：Play 侧运行 `dex2oat`，再把预编译产物放进 SDM（Secure Dex Metadata）随 APK 下发，设备端避免重复执行本地 `dex2oat`。这条说法和 AOSP 中 SDM 产物管理路径相互印证，但签名绑定、产物适配 ABI、Play 灰度策略、是否对所有包开放，仍缺少官方开发者文档或 AOSP 端到端说明。

[待验证: Android Authority, android-16-cloud-compilation-3541910]

因此，写性能结论时只能给出这个边界：Android 16 具备接收和管理 SDM / cloud dexopt artifacts 的设备端基础；Play 分发是否命中云端编译，需要用实际安装包、设备版本和 `dumpsys package dexopt` 结果确认。不能把“支持 SDM”写成“所有安装都会跳过设备端 dex2oat”。

## System Dexopt Manager 的分发侧边界

目前公开 AOSP 中可稳定引用的设备端入口是 ART Service、`artd`、`pm compile`、`BackgroundDexoptJob` 和 `ArtManagerLocal`。如果材料里出现 System Dexopt Manager 或 SDM 管理器这类叫法，写正文时不要把它们包装成一个可在 AOSP 中搜索到的系统服务类。

公开资料能支撑的边界可以拆成四部分：

- Play / 安装来源：决定是否提供 Cloud Profile 或 SDM 产物，也决定用户额外下载多少编译元数据。
- Package Manager / Installer：完成 APK、split、`.dm` 的安装配对和基础校验。
- ART Service：根据安装原因、profile 可用性、系统属性和设备状态决定 compiler filter，并管理 OAT / VDEX / ART / SDM / SDC 等产物。
- `artd` / `dex2oat`：执行本地编译，或在已有可用产物时跳过不必要的本地工作。

这个分工能避免两个误判：把 Play 侧能力说成 AOSP 设备端类名；把 Cloud Profile 和 Cloud Compilation 合并成同一件事。Cloud Profile 是 profile 输入，Cloud Compilation / SDM 更接近预生成编译产物的分发和管理路径。

## 开发者能控制什么

应用侧能稳定控制三件事：生成 profile、确保产物进包、用同一台设备复核编译状态。

CI 中应把 Baseline Profile 当成 release 产物的一部分检查。APK 要检查 `/assets/dexopt/baseline.prof` 和 `/assets/dexopt/baseline.profm`，AAB 要检查 `/BUNDLE-METADATA/com.android.tools.build.profiles/baseline.prof` 和对应 `.profm`。如果要侧载 `.dm`，还要确认 `base.apk` 与 `base.dm` 同名配对。

```bash
unzip -l app-release.apk | grep -E 'assets/dexopt/(baseline.prof|baseline.profm)'
unzip -l app-release.aab | grep -E 'BUNDLE-METADATA/.*/baseline.prof'
```

这一步只能证明构建产物里有 profile。下一步必须在设备端看编译状态：

```bash
adb install -r app-release.apk
adb shell pm compile -m speed-profile -f -v com.example.app
adb shell dumpsys package dexopt | grep -A 6 com.example.app
```

如果输出仍停在 `verify`，先查文件名、DEX checksum、安装来源和 AGP / ProfileInstaller 行为。不要先归因到 Android 16 云端编译未启用。对启动收益的判断还要回到 Macrobenchmark，用同一包、同一设备、同一脚本对比 `CompilationMode.None()` 与 `CompilationMode.Partial()`，指标至少包含 TTID、TTFD 和启动阶段 jank。

## 安装耗时和启动收益不是同一个指标

Profile 体系经常同时影响安装、首次启动和后续启动，但三个指标不能互相替代。

- 安装耗时：看 session 提交、APK 复制、签名校验、包扫描、`.dm` 校验、dexopt 或 SDM 产物接收。Cloud Compilation 如果命中，主要减少设备端 `dex2oat` 的 CPU 和 I/O 开销。
- 首次启动：看启动路径是否已经有可用 OAT / VDEX / ART 产物，是否减少解释执行、JIT 热身和 page fault。Baseline Profile 的收益主要体现在这里。
- 后续启动：看本地 JIT profile、后台 `bg-dexopt`、Cloud Profile 是否继续补齐热点路径。这个阶段的收益会随用户行为收敛。

低端设备更容易从安装期省时中受益，因为 `dex2oat` 同时吃 CPU、内存和闪存 I/O。高端设备安装阶段的绝对耗时可能不明显，但 Baseline Profile 对首次启动仍有价值。评价方案时不要只用“安装快了多少”概括整套 Profile 体系，至少把安装耗时、TTID、TTFD、编译状态分开记录。

## 与应用实战章节的交叉引用

- Baseline Profile 生成、调试、Macrobenchmark 对比流程详见 8.7 节。
- ART 编译策略、compiler filter、JIT / AOT 演进详见 1.7 节。
- PMS 安装路径、`PackageInstallerSession`、`InstallPackageHelper` 和 `DexOptHelper` 的位置详见 1.9 节。
- 启动优化实战中如何把 profile 结果转成 TTID / TTFD 收益，详见 21.4 节。

可确认的边界是：设备端 ART Service 和 SDM 管理路径已有可核对源码；Play 云端编译的分发策略仍要以官方文档、实机安装和 `dumpsys package dexopt` 结果为准。

