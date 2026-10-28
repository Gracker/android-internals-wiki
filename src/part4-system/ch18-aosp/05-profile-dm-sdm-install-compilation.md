---
title: Profile、DM 与 Secure Dex Metadata 安装编译
chapter: '18.5'
section: '18.5'
status: finalized
last_review_finalize_at: '2026-07-29T18:06:00+08:00'
applicable_versions: Android 14 (API 34) - Android 17 (API 37)
last_verified: '2026-08-14'
last_verified_against: AOSP android-17.0.0_r1 (PackageInstallerSession / PackageManagerShellCommand / DexOptHelper / PrimaryDexopter / Dexopter / DexoptStatus / ReasonMapping / ArtFileManager / ArtManagedInstallFileHelper / DexMetadataHelper / Dex2OatStatsReporter / artd / oat_file / sdc_file / path_utils); Configure ART / ART Service configuration / Baseline Profiles / Startup Profiles
confidence: high
sources:
- type: aosp
  path: https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/libartservice/service/java/com/android/server/art/PrimaryDexopter.java
- type: aosp
  path: https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/libartservice/service/java/com/android/server/art/Dexopter.java
- type: aosp
  path: https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/libartservice/service/java/com/android/server/art/model/DexoptStatus.java
- type: aosp
  path: https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/libartservice/service/java/com/android/server/art/ReasonMapping.java
- type: aosp
  path: https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/libartservice/service/java/com/android/server/art/ArtFileManager.java
- type: aosp
  path: https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/libartservice/service/java/com/android/server/art/ArtManagedInstallFileHelper.java
- type: aosp
  path: https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/libartservice/service/java/com/android/server/art/ArtManagerLocal.java
- type: aosp
  path: https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/libartservice/service/java/com/android/server/art/DexMetadataHelper.java
- type: aosp
  path: https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/libartservice/service/java/com/android/server/art/Dex2OatStatsReporter.java
- type: aosp
  path: https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/artd/artd.cc
- type: aosp
  path: https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/artd/path_utils.cc
- type: aosp
  path: https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/runtime/oat/oat_file.cc
- type: aosp
  path: https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/runtime/oat/sdc_file.cc
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/pm/PackageInstallerSession.java
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/pm/PackageManagerShellCommand.java
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/pm/DexOptHelper.java
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/content/pm/dex/DexMetadataHelper.java
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/cmds/installd/dexopt.cpp
- type: official
  path: https://source.android.com/docs/core/runtime/configure
- type: official
  path: https://source.android.com/docs/core/runtime/configure/art-service
- type: official
  path: https://developer.android.com/topic/performance/baselineprofiles/overview
- type: official
  path: https://developer.android.com/topic/performance/startupprofiles/dex-layout-optimizations
- type: official
  path: https://developer.android.com/topic/performance/baselineprofiles/confirm-startup-profiles
- type: official
  path: https://developer.android.com/topic/performance/baselineprofiles/debug-baseline-profiles
- type: material
  path: DeepResearch/2026-06-09-android17-cloud-compilation-sdm-dm-ondevice-flow.md
- type: material
  path: intake/research-feeds/2026-04-07-11-android16-cloud-compilation-baseline-startup-profiles.md
tags:
  - profile
  - dm
  - sdm
  - cloud-compilation
  - dexopt
  - art-service
  - install-performance
related_chapters:
- '1.5'
- '1.16'
- '21.4'
consolidated_from:
- 16.6 Android 16 云端 Profile 与 dexopt 安装优化
- 16.9 Android 17 SDM 安装编译流程性能
- src/part2-performance/ch08-responsiveness/05-baseline-profiles.md#oem-dexpreopt
---

# Profile、DM 与 Secure Dex Metadata 安装编译

Profile、Dex Metadata 与 Secure Dex Metadata 三样东西名称接近，交付与校验的阶段却各不相同。要判断安装编译的收益，我们要沿安装会话、ART Service 和运行时消费路径走一遍，弄清元数据在什么条件下被接受、验证并实际用上。

> 源码基线：AOSP `android-17.0.0_r1`。云端如何选择设备配置并生成 SDM 属于分发侧实现，不在 AOSP 设备端源码之内；本文讨论的是系统能够验证的接收、决策和加载行为。

## SDM 的定义与收益边界

SDM 的全名是 **Secure Dex Metadata**，Android 16 引入了这种文件，用它携带面向特定 ISA 的云端 AOT（ahead-of-time） 产物；ISA（instruction set architecture）指 `arm64` 这类 CPU 指令集。SDM 必须由与 APK 相同的 signer（签名证书身份）签名。还要说明一点：AOSP `android-17.0.0_r1` 中没有名为 “Staged Dalvik Compilation” 的架构，安装流程里也没有把 SDM 解包到应用 `oat` 目录这一步——运行时是直接从 ZIP 内部打开它的。

一组可供 ART 使用的云端产物由三个文件配合：

| 文件 | 典型内容 | 生成方 | 在流程中的职责 |
|---|---|---|---|
| `.dm` | `primary.prof`、`primary.vdex`，可带 `config.pb` | 分发侧 | 提供云端 Profile 或与 SDM 配套的 VDEX |
| `.sdm` | 至少包含供运行时打开的 `primary.odex` | 云端编译服务 | 提供指定 ISA 的 AOT 代码 |
| `.sdc` | SDM 时间戳与设备 ART APEX 版本 | 设备端 `artd` | 记录 SDM 文件代际与设备 ART 环境 |

SDM 只覆盖 base APK 与 split APK 内随应用打包的 **primary dex**；运行时动态生成或由自定义 ClassLoader 加载的 secondary dex，在这套 SDM 的范围之外。`ArtFileManager` 在 r1 源码中直接写明 “SDM files are only for primary dex files”。

收益的范围也很清楚。当 SDM、DM、SDC 与当前 APK、ISA、boot classpath 和编译目标兼容时，安装期可以直接复用云端产物，无需为同一目标在设备上再次运行 `dex2oat`；`dex2oat` 是 ART 把 DEX 编译为本地产物的工具，boot classpath 则是应用运行时依赖的框架核心类集合。

省掉的只有安装期编译这一段：安装会话写盘、APK 与 SDM 签名校验、包扫描、原生库处理、`fsync`、SELinux 检查以及首次启动的其余工作照常发生，`fsync` 负责把文件数据及相关元数据同步到稳定存储。AOSP 也没有承诺过固定的安装或启动提升百分比。

<!-- gracker-diagram: ch18-05-01-four-roles -->
![Profile、DM、SDM 与 SDC 在不同阶段各司其职](../../assets/diagrams/ch18/ch18-05-01-four-roles.png)

图：Profile 提供编译输入，DM/SDM 交付元数据与云端产物，SDC 保存设备首次接收的环境上下文。 primary dex 按已安装 APK 容器界定，包含 classes2.dex 等；不是只优化首个 DEX，也不按 ClassLoader 名字分类。

## 1. 先分清 Profile、DM、SDM 与 SDC

这一节先把四个名字的职责拆开：Profile 是编译输入，DM 与 SDM 是两类交付文件，SDC 是设备端生成的记录文件。后面的安装与运行时行为，我们都以这组区分为前提。

### 1.1 三类 Profile 解决不同问题

先看输入侧。Profile 是 ART 或构建工具用来选择热点代码的输入，profile-guided AOT 就是只预编译 Profile 命中的方法和类；compiler filter 是 ART 的编译策略名，例如 `verify` 只验证 DEX，`speed-profile` 会按 Profile 选择代码做 AOT。SDM 走的是另一条路：它直接携带指定 ISA 的 AOT 代码，到手已经是编译产物，而 Profile 只是编译输入。我们把两者都叫“云端编译”，就会混淆生成方、交付方式和验证方法。

| 类型 | 生产者与位置 | 主要作用 | 开发者控制度 |
| --- | --- | --- | --- |
| [Baseline Profile](https://developer.android.com/topic/performance/baselineprofiles/overview) | 应用或库团队生成，随 APK/AAB 发布 | 让关键路径在新安装或更新后更早进入 profile-guided AOT | 高，可在 CI 生成和检查 |
| [Startup Profile](https://developer.android.com/topic/performance/startupprofiles/dex-layout-optimizations) | 由构建流程交给 R8/AGP 使用 | 调整 DEX layout，即类和方法在 DEX 文件内的排列，减少启动期跨页和跨 DEX 读取 | 中，结果体现在 DEX 布局而非运行时独立 Profile |
| Cloud Profile | 分发侧依据用户样本生成，经 DM 等安装输入交付 | 为新设备提供更接近真实热路径的 profile | 低，取决于渠道、样本与设备 ART 策略 |

Baseline Profile 面向 Day-0，也就是新安装或更新后、设备还没有积累本地运行样本的阶段；Startup Profile 只负责构建期布局；Cloud Profile 提供 Profile 输入，设备仍可能需要运行 `dex2oat`。Cloud Compilation/SDM 分发的才是预生成编译产物。这几种机制可以同时存在，但职责各管一段，谁也顶替不了谁。

<!-- gracker-diagram: ch18-05-02-profile-types -->
![Baseline、Startup、Cloud 与云端 AOT 的边界](../../assets/diagrams/ch18/ch18-05-02-profile-types.png)

图：Baseline 和 Cloud 可作 ART 编译输入，Startup Profile 在构建期影响 DEX 布局。 SDM 直接交付云端 AOT 产物；DM 携带 Cloud Profile 仍可能需要本机 dex2oat。

按照 [Baseline Profile 调试文档](https://developer.android.com/topic/performance/baselineprofiles/debug-baseline-profiles)，APK 中的稳定检查点是 `assets/dexopt/baseline.prof`，AAB 中则是 `BUNDLE-METADATA/com.android.tools.build.profiles/baseline.prof`。Startup Profile 的源规则通常是 `startup-prof.txt`；[现行验证文档](https://developer.android.com/topic/performance/baselineprofiles/confirm-startup-profiles)建议检查最终 DEX 布局，或在 AGP 8.8 及以上检查 AAB 中的 `BUNDLE-METADATA/com.android.tools/r8.json`。另外，安装后的文件系统里没有一个叫 `startup.prof` 的文件可供查找。

### 1.2 `.dm`：Dex Metadata

`.dm` 是 ZIP 文件，文件名与对应 APK 同基名：

| APK | 对应 DM |
|---|---|
| `base.apk` | `base.dm` |
| `split_feature.apk` | `split_feature.dm` |

ART Service 的 `DexMetadataHelper.getType()` 检查 ZIP 中的 `primary.prof` 与 `primary.vdex`，把结果分成 `PROFILE`、`VDEX`、`PROFILE_AND_VDEX`、`NONE` 或 `ERROR`。VDEX 保存 DEX 验证信息及相关数据；`config.pb` 可以附带配置，缺少它时 ART Service 使用默认配置。

这两部分内容分工不同：

- `primary.prof` 列出适合 `speed-profile` 的方法和类，可作为本机 dexopt 输入；
- `primary.vdex` 保存验证相关数据。SDM 路径打开 AOT 代码时，运行时会从配套 DM 读取它。

平台层的 `android.content.pm.dex.DexMetadataHelper.validateDexMetadataFile()` 在 r1 中通过 `StrictJarFile` 打开归档，确认文件结构可读。这个方法的 JavaDoc 仍提到 manifest，但 r1 的方法体没有读取 `manifest.json`，其中也没有 `pm.dexopt.dm.require_manifest` 与 `pm.dexopt.dm.require_fsverity` 属性，`pm install` 同样没有受支持的 `--dm` 参数。判断 DM 状态时，这三项都要排除在依据之外。

AOSP 的 [Configure ART](https://source.android.com/docs/core/runtime/configure) 文档描述了常见的 Pixel 策略：Play 分发的 DM 可携带 cloud profile，ART 对其中列出的方法做 AOT 编译；没有 DM 时，该策略可能在安装期不做 AOT。这描述的是一种产品配置，OEM 仍可以通过 ART Service 配置选择不同的安装 compiler filter。

<!-- gracker-diagram: ch18-05-03-dm-classification -->
![DM 分类只说明 ZIP 条目存在](../../assets/diagrams/ch18/ch18-05-03-dm-classification.png)

图：DM 读取与 config 解析先处理错误，getType 再按两个 ZIP 条目的存在性分类。 PROFILE/VDEX 类型不证明条目内容可用；缺 config 用默认值，缺文件与读取失败也不能混成一种状态。

### 1.3 `.sdm`：Secure Dex Metadata

SDM 的文件名多一段指令集名称，`artd/path_utils.cc` 的构造规则可概括为：

| APK | ISA | 对应 SDM |
|---|---|---|
| `base.apk` | `arm64` | `base.arm64.sdm` |
| `split_feature.apk` | `arm64` | `split_feature.arm64.sdm` |

同一个 APK 若要覆盖两种 ISA，需要两个不同的 SDM；`arm64` 产物也供不了 `arm` 进程使用。

<!-- gracker-diagram: ch18-05-04-filenames -->
![APK、DM、SDM 和安装重命名必须对应](../../assets/diagrams/ch18/ch18-05-04-filenames.png)

图：DM 与 APK 同基名，SDM 还带目标 ISA，安装器要在重命名时同步维护映射。 伴随文件需在对应目录；正常协调的重命名可接受，错误映射和不支持的 native ISA 会失败。

SDM 通过 APK Signature Scheme v3（APK v3 签名协议） 校验身份，`ArtManagedInstallFileHelper.validateSdmFile()` 逐项核验，下面任何一条命中都会判 SDM 无效：

- 文件名没有受支持的 ISA 后缀；
- 找不到同基名 APK；
- APK 的 v3 签名校验失败；
- SDM 的 v3 签名校验失败；
- APK 与 SDM 的 signer 集合不完全相同。

<!-- gracker-diagram: ch18-05-05-sdm-validation -->
![新 API 验证 SDM 的名称与 signer](../../assets/diagrams/ch18/ch18-05-05-sdm-validation.png)

图：新 helper 依次核对支持的 ISA、对应 APK、双方 v3 签名和当前 signer 集合。 这是新 API 分支的检查；历史签名轮换链不能替代 signer 精确匹配，身份有效也不等于运行时兼容。

在 feature flag（功能开关） `artManagedInstallFilesValidationApi()` 对应的新验证分支中，这些结果被标为 `RESULT_SHOULD_DELETE_AND_CONTINUE`：`PackageInstallerSession` 删除无效伴随文件、记录 warning，并继续处理安装。r1 仍保留旧分支，旧分支遇到无效 SDM 时可能直接拒绝安装。分析日志时，我们先确认设备走的是哪条分支，再解读无效 SDM 的处理结果。

SDM 的签名约束让安装会话能验证它的来源，调用方也不限于 Play：`adb install-multiple` 就可以把 `.apk`、`.dm` 与 `.sdm` 作为独立文件写入同一会话，随后由安装会话和 ART helper 按名称与后缀分类。这只是通用的多文件提交方式，难点在产物本身——名称要正确、signer 要与 APK 完全一致、ISA 要适配目标设备，普通开发构建通常拿不到这样的 SDM。

<!-- gracker-diagram: ch18-05-06-installer-branches -->
![新旧验证分支与删除失败分别处理](../../assets/diagrams/ch18/ch18-05-06-installer-branches.png)

图：PackageInstaller 的 flag 决定验证分支，新分支无效文件删除成功才继续安装。 删除失败仍会拒绝安装；旧分支对 SDM 验 v3 并与会话 APK 身份比较，不重复新 helper 的全部检查。

### 1.4 `.sdc`：Secure Dex Metadata Companion

SDC 由设备自己生成，应用商店不下发它。`PrimaryDexopter.onDexoptStart()` 会在 Android 16 及以上、非 pre-reboot 流程中，按 primary dex 的每个 ABI 请求 `artd.maybeCreateSdc()`。ABI（application binary interface）定义二进制调用约定等接口，ART 再把 ABI 映射到对应 ISA；pre-reboot 指系统更新生效前、为下次重启预先准备编译产物的流程。

下面这一行展示 ART Service 到 `artd` 的调用位置：

```java
mInjector.getArtd().maybeCreateSdc(outputSdc);
```

调用发生在 dexopt 决策之前。设备上没有 SDM 时，`artd` 照样返回成功，源码注释把这种情况称为常态——缺 SDM 本身不算安装错误。

SDC 是两行文本，内容形式如下：

```text
sdm-timestamp-ns=<SDM 的 mtime，纳秒>
apex-versions=<当前设备 ART 看到的 APEX 版本串>
```

运行时拿 SDC 保存的时间戳，与当前 SDM 的 `st_mtim`（即纳秒精度的最后修改时间）比对；两者不同，说明 SDM 在 SDC 建立后被替换，这份产物不会被采用。APEX 是承载 ART 等模块化系统组件的包。所谓 samegrade placebo，是在版本号不变的情况下换入另一版 ART APEX 做测试；SDC 保存 `apex-versions` 上下文，就是为了避免把这种环境变化误判为完全兼容。

SDC 的位置由目标 OAT 位置决定：常见情况是应用旁 `oat/<isa>/` 下的 `.sdc`，需要 dalvik-cache 时则使用共享的 ART 编译产物缓存目录。它解决的是设备环境与文件代际的匹配；签名验证在安装阶段就已完成。

<!-- gracker-diagram: ch18-05-08-apex-context -->
![SDC 的时间戳与 APEX 环境如何参与验证](../../assets/diagrams/ch18/ch18-05-08-apex-context.png)

图：SDC 绑定 SDM 修改时间与首次接收时的 BCP APEX 环境，运行时再与当前环境检查。 APEX 标识优先用更新时间而非仅 versionCode；允许子集 BCP 的前缀兼容，不是永远整串相等。

<!-- gracker-diagram: ch18-05-07-sdc-lifecycle -->
![SDC 的缺失、复用与重建条件](../../assets/diagrams/ch18/ch18-05-07-sdc-lifecycle.png)

图：PrimaryDexopter 提前触发 SDC 准备，artd 按 SDM 与已有 SDC 的状态决定返回、复用或重建。 SDM 缺失是常态；已有相同 mtime 的 SDC 保留首次上下文，不能通过再次调用把它刷新成任意当前环境。

## 2. 从安装会话到 ART Service

### 2.1 安装器接收伴随文件

`PackageInstallerSession` 把 `.dm`、`.sdm` 等识别为 ART-managed install files，并在提交前校验文件名映射与 SDM 签名。它处理的是会话中的独立文件，不会从 APK 内“提取 SDM”。

文件名必须能反推出会话中的对应 APK。以 `base.arm64.sdm` 为例，验证器移除 `.arm64.sdm` 后补回 `.apk`，得到 `base.apk`；如果 APK 被临时改名而伴随文件没有同步命名，验证就会失败。

在具备合法测试产物时，可用下面的命令验证安装器是否接受三类文件：

```bash
adb install-multiple base.apk base.dm base.arm64.sdm
```

这条命令只演示文件提交方式。`base.arm64.sdm` 必须使用与 `base.apk` 完全相同的 signer 集合，并且设备要运行对应 ISA；随手创建同名 ZIP 进不了可用路径。

### 2.2 dexopt 由谁执行

Android 14 起，应用 dexopt 的调度入口已经迁到 ART Service。r1 中的职责分配是：

| 组件 | 职责 |
|---|---|
| Package Manager | 完成安装事务，在需要时发起安装 dexopt |
| ART Service Java 层 | 选择 primary dex、ABI、compiler filter、Profile 与优先级 |
| `artd` | 作为 ART Service 的特权辅助进程，校验路径、检查现有产物、准备文件并启动编译器 |
| `dex2oat` | 需要本机编译时生成 VDEX、ODEX 与可选 ART image |
| ART runtime | 应用启动或加载 dex 时选择并映射兼容产物 |

入口迁走之后，`installd` 仍处理安装系统中的其他受特权文件操作；应用 dexopt 的主线要看 ART Service——DM Profile 处理和 SDM 调度的入口都在那里，具体受保护操作交给 `artd`，`frameworks/native/cmds/installd/dexopt.cpp` 只适合当作旧流程的对照。

<!-- gracker-diagram: ch18-05-09-install-to-art -->
![安装会话和 ART Service 的职责交接](../../assets/diagrams/ch18/ch18-05-09-install-to-art.png)

图：Package Manager 完成安装事务并按需发起 dexopt，ART Service 与 artd 决定和执行后续工作。 Android14+ 主线由 ART Service 管理应用 dexopt；installd 的其他安装文件职责仍需另看。

### 2.3 ART 如何决定跳过本机编译

安装触发 `DexOptHelper.performDexoptIfNeededAsync()` 后，ART Service 为每个 primary dex 与 ABI 构造目标，`Dexopter` 大体经历以下阶段：

1. `PrimaryDexopter.onDexoptStart()` 尝试建立或刷新 SDC。
2. ART Service 根据安装 reason、DM 类型、Profile 与产品配置确定目标 compiler filter。
3. `artd.getDexoptNeeded()` 结合 APK、boot classpath、现有本地产物以及 SDM 组合判断目标是否已经满足。
4. 现有产物满足目标时，结果为无需本机 dexopt。
5. 产物缺失、过期或 compiler filter 不满足要求时，`artd.dexopt()` 启动 `dex2oat`。

OatFileAssistant 是 ART 用来查找并判断编译产物是否可用的运行时组件，SDM 因而也是它可选择的产物位置之一；AIDL 接口用 `SDM_DALVIK_CACHE` 与 `SDM_NEXT_TO_DEX` 表示 SDM 产物位于共享缓存或应用旁目录。SDM 并没有单独取代 dexopt 调度器，调度器仍要判断这份云端产物能否满足当前目标。

若本机编译已执行，`PrimaryDexopter` 会尽早删除对应 SDM 与 SDC，释放空间。相关源码条件可缩写为：

```java
if (status == DexoptResult.DEXOPT_PERFORMED && !mInjector.isPreReboot()) {
    mInjector.getArtd().deleteSdmSdcFiles(...);
}
```

删除动作也说明 SDM 是可被本机编译结果替代的 dexopt artifact（编译产物）。即使没有立即删除，ART 的文件垃圾回收也会清理失效产物。

<!-- gracker-diagram: ch18-05-10-dexopt-decision -->
![兼容候选、目标 filter 与 force 共同决定重编](../../assets/diagrams/ch18/ch18-05-10-dexopt-decision.png)

图：ART Service 先准备 SDC 与目标输入，再结合 trigger 判断是否需要本机编译。 存在 SDM 不保证跳过；force、Profile 缺失降级、取消和存储条件都要按目标分别解释。

<!-- gracker-diagram: ch18-05-11-local-cleanup -->
![本机编译后按目标与 ISA 清理云端产物](../../assets/diagrams/ch18/ch18-05-11-local-cleanup.png)

图：本机 dexopt 已执行且不是 pre-reboot 时，PrimaryDexopter 尽早删除该目标的 SDM/SDC。 清理范围按 primary dex 与 ISA 对应；单个 ABI 成功不能外推整个包，其他失效文件由 GC 再判断。

### 2.4 安装编译与后台 dexopt 是两个时点

Android 14 之后，ART Service 负责应用设备端 AOT 编译的调度与策略。首次开机或 OTA 后第一次启动会优先保证系统可用，后续后台任务再按 Profile 编译；产品可以覆盖这些 compiler filter，Pixel 的默认策略只是其中一种，其他 OEM 未必相同。

[ART Service 配置文档](https://source.android.com/docs/core/runtime/configure/art-service)写明，默认后台 dexopt 每日运行一次，条件是设备空闲且充电；设备退出空闲状态时，任务会立即取消。新安装后立即启动时，后台 dexopt 可能还未发生；多次启动后的编译状态也可能已经被本地 JIT（just-in-time） Profile 和后台编译改变。所以比较 Profile 或 SDM 收益时，应固定安装来源和编译状态，把“安装结束”“首次启动”“后台 dexopt 后启动”分成三组。

<!-- gracker-diagram: ch18-05-12-install-background -->
![安装、首次启动和后台 dexopt 的时点分开](../../assets/diagrams/ch18/ch18-05-12-install-background.png)

图：安装策略、首次运行的 JIT/Profile 积累和后续后台编译会改变同一 APK 的执行状态。 默认后台任务在空闲充电时每日调度，退出空闲即取消；OEM 可定制，因此各时点要独立记录。

`speed-profile` 表示编译器使用了可用 profile，区分不出 Baseline、Cloud 还是设备本地 profile；`install-dm` 也只说明调用中携带过 DM。实际输入、compiler filter、reason 和产物位置，我们要结合 `pm art dump`、安装日志和 trace 判断。

## 3. 运行时怎样使用 SDM

### 3.1 直接从 ZIP 打开 `primary.odex`

r1 在这里的选择很直接：`OatFileBase::OpenOatFileFromSdm()` 把 ZIP 内部条目名拼成 `<sdm>!/primary.odex`，随后直接加载；安装阶段自始至终没有把 SDM 解包并复制到 `/data/app/<pkg>/oat/<isa>/`。

下面两行给出 ODEX 与 VDEX 的真实来源：

```cpp
std::string elf_filename = sdm_filename + kZipSeparator + "primary.odex";
ret->vdex_ = VdexFile::OpenFromDm(dm_filename, error_msg);
```

ODEX 来自 SDM，VDEX 来自同 APK 的 DM。缺少可用 DM/VDEX 时，仅有 SDM 也组不成这条运行时加载路径；运行时还需要 APK 自身校验 dex checksum 与依赖关系。

`OatFile::OpenFromSdm()` 带有名为 `Open sdm file <path>` 的 `ScopedTrace`。抓取应用启动 trace 时，看这个 slice（trace 中带起止时间的区间事件） 是否出现，比检查“`oat` 目录里有没有 `.odex`”更能说明 SDM 被运行时打开。

<!-- gracker-diagram: ch18-05-13-zip-load -->
![运行时组合 SDM、DM、SDC 和 APK](../../assets/diagrams/ch18/ch18-05-13-zip-load.png)

图：运行时从 SDM ZIP 打开 ODEX，从 DM 取 VDEX，并用 SDC 与 APK/依赖完成检查。 入口 trace 早于 DM 存在检查；缺任何必要输入都可能失败，图中输入关系不表示并行调用或保证成功映射。

### 3.2 运行时的兼容性检查

云端产物照样要过 ART 的兼容性检查，OatFileAssistant 仍会核对：

- APK dex checksum；
- boot classpath 与 class loader context（类加载器依赖关系）；
- compiler filter 是否满足请求；
- OAT/VDEX 状态；
- SDM 与 SDC 的时间戳关系；
- SDC 保存的 ART APEX 版本上下文。

其中任一条件不满足，系统可以选择较低编译级别的已有产物、解释执行、JIT，或安排本机 dexopt，具体取决于当前 reason、filter 与设备策略。所以看到 SDM 文件存在，只能证明安装器曾接收过文件；运行时是否正在执行其中的机器码，要靠下面的证据链确认。

<!-- gracker-diagram: ch18-05-14-compatibility-policy -->
![候选有效性与是否重编是两类判断](../../assets/diagrams/ch18/ch18-05-14-compatibility-policy.png)

图：格式与依赖检查决定候选是否可用，filter/trigger 再影响是否安排目标编译。 filter 不足不等于所有场景立即禁止现有代码执行；回退、JIT 与重编取决于当前策略和状态。

### 3.3 确认内容被采用的三类证据

`ReasonMapping` 中存在 `cloud` reason，也存在带 `-dm` 后缀的安装 reason。`Dexopter` 源码注释明确提示：`-dm` 只表示本次调用传入过 DM，空 DM 或内容未被使用时也可能出现该后缀。

我们判断云端产物是否生效，要组合三类证据：

1. `pm art dump <package>` 的 compiler filter、reason 与 location；location 是供人阅读的调试字符串，格式不保证稳定，脚本不宜依赖它；
2. trace 中是否出现本机 `dex2oat`，以及是否出现 `Open sdm file`；
3. 安装日志中的 SDM validation warning、`artd` 错误和 dexopt 结果。

所以只看 `install-dm`、只看文件存在，或只看安装总耗时，都确认不了 SDM 路径。

<!-- gracker-diagram: ch18-05-15-evidence-levels -->
![接收、候选、入口尝试与实际采用分开取证](../../assets/diagrams/ch18/ch18-05-15-evidence-levels.png)

图：安装验证、ART 状态、入口 trace 与目标进程执行证据分别对应不同层次。 dump location 是不稳定调试字符串，Open sdm file 仅表示尝试，单一信号不能证明应用已执行云端机器码。

## 4. 性能收益来自哪里

### 4.1 能省掉的工作

可用的 SDM 组合已经带有指定 ISA 的 AOT 代码，并由 DM 提供匹配 VDEX。若它满足安装目标，设备就无需在安装阶段为同一目标运行 `dex2oat`，可以省掉：

- 编译器进程的 wall time，即从开始到结束经过的实际时长；
- dex2oat 的 CPU 时间与临时内存峰值；
- 本机生成 ODEX/VDEX 的写放大，即存储层实际写入量超过最终文件大小的额外写入；
- 安装期编译造成的热量与功耗。

收益随应用 dex 规模、目标 filter、CPU、存储、温控和产品安装策略变化。安装策略原本使用 `verify` 或不做 AOT 的设备，能够省掉的本机编译本来就少。

### 4.2 仍需支付的工作

下面这些开销，SDM 一项也省不掉：

- APK、DM、SDM 的下载与安装会话写入；
- APK 与 SDM 的 v3 签名解析和 signer 比较；
- APK 解析、权限与包状态更新；
- 原生库提取或映射；
- 文件搬移、`fsync`、配额和 SELinux 操作；
- SDC 创建及 ART 产物兼容性检查；
- 未被 AOT 覆盖的方法解释执行与 JIT；
- 应用自身初始化、I/O、Binder 调用和首帧绘制。

所以“携带 SDM 后安装近似零成本”的说法不成立。安装总耗时若主要花在下载、写盘或包扫描，dex2oat 的减少对总值影响有限。

### 4.3 固定百分比的来源与测量

AOSP r1 源码没有给出 “安装时间减少 40%～60%”“冷启动减少 30%～45%” 或 “体积减少 15%～25%” 的保证，也没有定义可推出这些数字的基准。一个百分比要进入工程结论，得先交代测试设备、APK、compiler filter、采样次数与置信区间。

冷启动还可能出现方向不同的变化：省掉安装期编译通常有利于安装体验，SDM 的映射、ZIP 访问和页缺失特征却可能与本地产物不同。我们把安装 wall time、首次启动与后续启动分开测量。

<!-- gracker-diagram: ch18-05-16-partial-cost -->
![云端 AOT 只可能省掉安装编译的一部分](../../assets/diagrams/ch18/ch18-05-16-partial-cost.png)

图：可用云端产物可替代部分本机 dex2oat，安装事务和应用启动的其他成本仍需测量。 原策略仅 verify 时编译可省空间很小；新增文件 I/O 与映射也影响总成本，没有固定整机收益百分比。

## 5. 建立可复现的 A/B/C 实验

### 5.1 三组输入

同一 APK 版本，我们建议准备三组安装输入：

| 组别 | 输入 | 回答的问题 |
|---|---|---|
| A | APK | 设备默认安装策略的基线 |
| B | APK + DM | cloud profile 或 VDEX 对本机 dexopt 的影响 |
| C | APK + DM + 对应 ISA 的 SDM | 云端 AOT 产物能否避开本机 dex2oat |

三组实验要固定设备构建、ART APEX 版本、电量、温度区间、存储余量、网络条件和 APK 字节。每组至少多次冷安装，并报告中位数、P90（90% 样本不超过的值）与失败/回退次数。更新安装和全新安装应分开统计。

<!-- gracker-diagram: ch18-05-17-abc -->
![三组安装输入与前置编译状态共同控制](../../assets/diagrams/ch18/ch18-05-17-abc.png)

图：同一 APK 比较单包、加 DM、再加指定 ISA SDM 三组，分别验证输入与候选是否采用。 A 组可已有 Baseline；还需控制本地 Profile、旧产物、JIT 与后台任务，更新安装和全新安装分开。

### 5.2 采集指标

安装阶段记录：

- `adb install-multiple` 的端到端 wall time；
- Package Manager 的 `dexopt` slice；
- `dex2oat` 进程是否出现、wall time、CPU time 与峰值 RSS（驻留在物理内存中的大小）；
- SDM 校验 warning；
- ART stats 中 `ART_DEX2OAT_REPORTED` 的 compiler filter、compilation reason、DM type、ISA、状态、输出大小与耗时；
- 安装前后 `/data` 占用变化。

启动阶段记录：

- TTID（首帧可见时间） 与 TTFD（应用报告内容完整可用的时间）；
- `Open sdm file` slice；
- 主线程 runnable（可运行但等待 CPU）、I/O wait 与 major fault（需要从存储调入内存页的缺页）；
- JIT 活动和后台 dexopt；
- 连续多次启动后的变化。

`am start -W` 适合做快速筛查，替代不了 Macrobenchmark 或带统计设计的 Perfetto 实验。Macrobenchmark 是 Jetpack 提供的跨进程性能测试框架，能重复控制启动和编译状态。测试 C 组时，还要把“SDM 被接收”和“SDM 被运行时采用”分成两个检查点。

<!-- gracker-diagram: ch18-05-18-metrics -->
![安装阶段与启动阶段分别测量](../../assets/diagrams/ch18/ch18-05-18-metrics.png)

图：安装观测分解编译与事务成本，启动观测分解加载、缺页和应用关键路径。 adb 总耗时、ART 编译 wall time、CPU time 与 RSS 是不同口径；快速 am start 结果不能替代受控多轮实验。

## 6. 用命令与 Perfetto 定位问题

### 6.1 读取 ART Service 状态

下面的命令查看单个包的 dexopt 状态，并保留安装与 ART 相关日志：

```bash
adb shell pm art dump com.example.app
adb shell getprop pm.dexopt.install
adb shell logcat -s artd PackageManager DexMetadataHelper
```

`pm art dump` 会列出 dex container、ABI、compiler filter、compilation reason 与 location。location 若指向 SDM 内的 `primary.odex`，证据比 reason 字符串更强。`DexoptStatus` 同时说明 location 只是供人阅读的调试信息，没有稳定格式；`getprop` 反映产品当前安装 filter，某次安装已完成的具体决策，还要结合日志和 trace 确认。

生产版设备通常不允许 shell 枚举 `/data/app` 内部目录。文件级核对只适用于 root、userdebug/eng 或测试基础设施已经授予访问权的环境；普通设备上，我们依赖 `pm art dump`、日志和 trace。

<!-- gracker-diagram: ch18-05-19-diagnostic -->
![属性、ART dump 与现场执行各答一问](../../assets/diagrams/ch18/ch18-05-19-diagnostic.png)

图：getprop 显示当前属性，ART dump 报告候选状态，trace/日志继续核对实际决策与加载。 空属性可能使用默认值，回调可改 filter；dump 候选和属性都不是应用已执行 SDM 的证明。

### 6.2 Perfetto 的四个时间点

一次覆盖安装到首次启动的 trace，我们按以下顺序阅读：

1. Package Manager 的 `dexopt` slice：安装流程在 ART 上停留多久。
2. `artd` 与 `dex2oat`：是否启动本机编译，线程在哪些 CPU 上运行。
3. 应用进程的 `Open sdm file <path>`：运行时是否尝试打开 SDM。
4. 应用启动主线程：SDM 之外的初始化、I/O 与首帧瓶颈。

trace 里找不到 `dex2oat`，还不足以单独证明 SDM 生效——产品策略使用 `verify` 或沿用兼容本地产物时，也会出现这种 trace；我们还要看 ART dump 的 location 与 `Open sdm file`。

下面的 SQL 用于在 trace 中同时搜索本机编译和 SDM 打开事件：

```sql
SELECT ts, dur, name
FROM slice
WHERE name GLOB '*dex2oat*'
   OR name GLOB 'Open sdm file *'
ORDER BY ts;
```

查询结果要与安装时间窗和目标包对应。系统上可能同时为其他包做后台 dexopt，单凭进程名容易把无关编译计入样本。

<!-- gracker-diagram: ch18-05-20-trace-sql -->
![编译进程查询与 SDM slice 查询分开](../../assets/diagrams/ch18/ch18-05-20-trace-sql.png)

图：先在 process 表找编译进程，再沿 slice、thread_track、thread、process 还原 SDM 尝试归属。 编译器可没有同名 slice；进程生命周期与轨道归属可能缺失，后台其他包的事件不能自动计入当前样本。

### 6.3 常见现象

| 现象 | 可能解释 | 下一项证据 |
|---|---|---|
| 安装成功，日志提示删除 SDM | ISA 后缀、APK 映射或 v3 signer 校验失败 | `PackageInstallerSession` warning |
| SDM 存在，仍启动 dex2oat | 目标 filter 更高、依赖变化、DM/VDEX 缺失或产物过期 | `pm art dump` 与 artd 日志 |
| 没有 dex2oat，也没有 SDM location | 安装策略不要求 AOT，或复用了其他兼容产物 | `pm.dexopt.install` 与 location |
| `Open sdm file` 后回退 | SDC 时间戳、APEX 版本、checksum 或依赖检查未通过 | ART runtime 日志 |
| 带 `install-dm` reason，性能无变化 | DM 被传入但 Profile/VDEX 未被选用 | DM type、filter 与 location |
| 更新后 SDM/SDC 消失 | 本机 dexopt 已执行并触发及时清理 | dexopt result 与 `dex2oat` slice |

## 7. 分发与应用开发的职责

### 7.1 分发系统需要保证什么

能生成 SDM 的分发系统需要同时解决：

- 针对目标 ISA 和兼容运行时环境生成云端 AOT 产物；
- 为每个 base/split APK 建立正确文件名；
- 用 APK signer 对 SDM 做 v3 签名；
- 配送含匹配 `primary.vdex` 的 DM；
- 在应用更新、签名轮换、split 变化和 ART 环境变化时避免投递陈旧产物；
- 监控设备端 validation warning 与本机 dexopt 回退率。

这些服务端步骤没有开源在 AOSP 中。设备端源码能证明的是接收协议和兼容性条件；某个应用商店在何时生成、覆盖哪些机型、使用哪个 compiler filter，这类问题要问分发侧，设备端源码答不了。

### 7.2 应用工程师需要做什么

应用代码通常无需感知 SDM。工程侧更有价值的工作包括：

- 提供高质量 Baseline Profile，覆盖非云端分发和云端数据尚未成熟的用户；
- 用 Macrobenchmark 验证 Profile 覆盖与 TTID/TTFD；
- 控制反射、动态 dex 与冷启动主线程工作量；
- 将安装性能与启动性能分别设定指标；
- 在主要分发渠道建立 A/B/C 样本，持续观察 SDM 接收、采用和回退率。

Baseline Profile 与 cloud profile 的覆盖来源不同：前者随应用构建发布，后者由分发侧运行数据生成。两者都可能成为 ART 编译输入，SDM 替代不了 Baseline Profile。

<!-- gracker-diagram: ch18-05-21-responsibilities -->
![分发、设备和应用团队各自提供哪些证据](../../assets/diagrams/ch18/ch18-05-21-responsibilities.png)

图：分发侧准备相容且签名匹配的产物，设备端验证与选择，应用团队持续建设 Profile 与启动回归。 设备端支持不能推出渠道实际覆盖；SDM 不替代应用 Baseline Profile，也不免除应用自身初始化工作。

### 7.3 OEM dexpreopt 与应用 Profile

OEM dexpreopt 在系统镜像构建期处理 boot classpath、`system_server`、系统组件和预装 APK。`WITH_DEXPREOPT`、`WITH_DEXPREOPT_BOOT_IMG_AND_SYSTEM_SERVER_ONLY` 等构建开关决定镜像预编译范围，产物进入 system 分区或 boot image 相关目录；应用 Baseline Profile 则随 APK/AAB 交付，由安装端 ART、渠道或 ProfileInstaller 消费。

预装应用可能同时获得镜像 dexpreopt 与后续 profile-guided dexopt，但两者发生的阶段、权限、输入和产物归属不同。`WITH_DEXPREOPT_*` 管不到第三方应用的 Profile；某家 OEM 的私有预装策略，也写不进 AOSP 的应用分发规则。做实验时，我们分别记录镜像构建配置、安装输入、ART Service 的 compiler filter/reason 和应用侧 Macrobenchmark 结果。

<!-- gracker-diagram: ch18-05-22-dexpreopt -->
![镜像 dexpreopt 与应用交付 Profile 的阶段不同](../../assets/diagrams/ch18/ch18-05-22-dexpreopt.png)

图：OEM dexpreopt 在镜像构建期生成产物，应用 Profile 在交付与设备端消费环节参与优化。 预装应用可以经历两种路径；WITH_DEXPREOPT 系列开关不是第三方应用的 Profile 开关。

### 7.4 应用团队可复核的产物与状态

CI 先检查 Baseline Profile 是否进入 release 包，再在同一设备上验证 compiler filter：

```bash
unzip -l app-release.apk | grep 'assets/dexopt/baseline.prof'
unzip -l app-release.aab | grep 'BUNDLE-METADATA/com.android.tools.build.profiles/baseline.prof'
adb install -r app-release.apk
adb shell pm compile -m speed-profile -f -v com.example.app
adb shell pm art dump com.example.app
```

这些命令能证明的是构建产物和当前设备状态；渠道是否下发了 Cloud Profile 或 SDM，要靠另外的实验回答。验证 Profile 的启动收益，应使用同一 APK、设备和脚本，对比未编译与要求 Baseline Profile 的 Macrobenchmark 组；验证 SDM，则使用第 5 节的 APK / APK+DM / APK+DM+SDM 三组输入。我们把这两类实验分开做，不合并成一个“云端优化开关”。

<!-- gracker-diagram: ch18-05-23-ci-evidence -->
![ZIP 条目、Profile 有效性与编译采用逐步检查](../../assets/diagrams/ch18/ch18-05-23-ci-evidence.png)

图：CI 先精确检查条目名，再确认 Profile 内容与 DEX 匹配，最后验证设备实际编译和启动结果。 install -r 保留运行历史；compile -f 请求会改变编译状态，不能据条目存在或 filter 请求识别输入来源。

## 8. 版本边界

| 平台版本 | SDM 相关状态 |
|---|---|
| Android 14 / API 34 | ART Service 接管应用 dexopt 调度；常见云端优化仍以 DM cloud profile 驱动本机 AOT 为主 |
| Android 15 / API 35 | 延续 ART Service 与 DM 流程；这里核对的 SDM 格式尚未作为该版本基线 |
| Android 16 / API 36 | `ArtManagedInstallFileHelper` 源码注释标记 SDM 格式从此版本引入 |
| Android 17 / API 37 | `android-17.0.0_r1` 延续 SDM/SDC，并明确 primary dex、v3 signer、运行时 ZIP 加载与本机 dexopt 后清理行为 |

判断 r1 行为要以 r1 源码为准，`main` 分支上的实验 flag 是另一回事：核对的 r1 Package Manager 与 ART 源码中找不到 `cloudCompilationPm()` 和 `FLAG_ART_SERVICE_V3` 这些名称，所以这里没有采用它们。secondary dex 支持、默认开启比例和商店覆盖率，在 r1 里同样找不到依据，还算不上 Android 17 的已有能力。

## 源码索引

- [ArtManagedInstallFileHelper.java：DM/SDM 文件名与 signer 验证](https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/libartservice/service/java/com/android/server/art/ArtManagedInstallFileHelper.java)
- [PrimaryDexopter.java：建立 SDC 与本机 dexopt 后清理](https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/libartservice/service/java/com/android/server/art/PrimaryDexopter.java)
- [ArtFileManager.java：SDM 只覆盖 primary dex](https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/libartservice/service/java/com/android/server/art/ArtFileManager.java)
- [Dexopter.java：DM reason 与 dexopt 决策](https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/libartservice/service/java/com/android/server/art/Dexopter.java)
- [DexoptStatus.java：compiler filter、reason 与 location](https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/libartservice/service/java/com/android/server/art/model/DexoptStatus.java)
- [ReasonMapping.java：cloud、install 与 `-dm` reason 映射](https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/libartservice/service/java/com/android/server/art/ReasonMapping.java)
- [ArtManagerLocal.java：ART Service 的 dexopt 调度入口](https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/libartservice/service/java/com/android/server/art/ArtManagerLocal.java)
- [DexMetadataHelper.java：DM 内容分类](https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/libartservice/service/java/com/android/server/art/DexMetadataHelper.java)
- [Dex2OatStatsReporter.java：`ART_DEX2OAT_REPORTED` 字段](https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/libartservice/service/java/com/android/server/art/Dex2OatStatsReporter.java)
- [artd.cc：SDC 创建、路径校验与 dexopt 执行](https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/artd/artd.cc)
- [path_utils.cc：SDM/SDC 路径构造](https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/artd/path_utils.cc)
- [oat_file.cc：从 SDM 打开 ODEX、从 DM 打开 VDEX](https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/runtime/oat/oat_file.cc)
- [sdc_file.cc：SDC 的两个字段](https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/runtime/oat/sdc_file.cc)
- [PackageInstallerSession.java：安装会话验证结果处理](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/pm/PackageInstallerSession.java)
- [PackageManagerShellCommand.java：安装命令如何提交伴随文件](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/pm/PackageManagerShellCommand.java)
- [DexOptHelper.java：Package Manager 发起安装 dexopt](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/pm/DexOptHelper.java)
- [DexMetadataHelper.java：平台侧 DM 归档验证](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/content/pm/dex/DexMetadataHelper.java)
- [installd/dexopt.cpp：旧 dexopt 边界的对照源码](https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/cmds/installd/dexopt.cpp)
- [Configure ART：cloud profile、编译产物与 compiler filter](https://source.android.com/docs/core/runtime/configure)
- [ART Service configuration：后台 dexopt 的调度条件](https://source.android.com/docs/core/runtime/configure/art-service)
- [Baseline Profiles overview：Baseline、Cloud 与 Startup Profile 边界](https://developer.android.com/topic/performance/baselineprofiles/overview)
- [Create Startup Profiles：构建期 DEX layout 优化](https://developer.android.com/topic/performance/startupprofiles/dex-layout-optimizations)
- [Confirm Startup Profiles optimization：DEX 与 R8 元数据检查](https://developer.android.com/topic/performance/baselineprofiles/confirm-startup-profiles)
- [Debug Baseline Profiles：APK/AAB 内的 Baseline Profile 路径](https://developer.android.com/topic/performance/baselineprofiles/debug-baseline-profiles)

## 相关章节

- [1.5 ART 编译、优化与去优化机制](../../part1-fundamentals/ch01-architecture/05-art-compilation-verification-deoptimization.md)：解释 ODEX、VDEX、AOT、JIT 与 compiler filter。
- [1.16 应用分发、安装验证与 PackageManager 性能](../../part1-fundamentals/ch01-architecture/16-package-distribution-install-verification.md)：区分安装会话的 staged 语义与 Secure Dex Metadata。
- [21.4 Baseline、Startup 与 Cloud Profile 编译优化](../../part5-app/ch21-startup/04-baseline-startup-cloud-profile.md)：从应用侧生成、打包和回归 Baseline Profile。
- [18.4 AutoFDO 反馈导向编译优化](04-autofdo-feedback-directed-optimization.md)：native 采样反馈与 LLVM/Clang 构建期优化，不属于 ART Profile。
