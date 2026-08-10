---

title: "Android 17 SDM 安装编译流程性能"
chapter: "16.9"
status: finalized
last_task2b_at: 2026-07-13
last_task2b_lite_at: 2026-07-13
task6_result: passed
reviewed_by: hermes-aiw-review-finalize-apply
reviewed_date: "2026-07-29"
last_task6_at: "2026-07-29T18:06:00+08:00"
task9_result: passed
task9_state: reviewed
last_task9_at: "2026-07-29T18:06:00+08:00"
task9_reviewed_by: hermes-aiw-review-finalize-apply
task9_reviewed_date: "2026-07-29"
task2b_result: fixed
task2b_state: fixed
task6_state: reviewed
pipeline_stage: finalized
last_review_finalize_at: "2026-07-29T18:06:00+08:00"
last_review_finalize_run_id: "20260729-180555-eb91bcdc"
task2b_rework_notes: "2026-07-13 重度回炉：(1)删除 §2-6 全部 8 处虚构代码(DeviceBasedDexopt/ProfileBasedDexopt/InstallProcessor/BackgroundCompiler/ArtDaemon/FileUtils::OptimizeFileAccess/InstallSessionOptimizer/InstallExecutor/DexoptManager/CompilationRequestOptimizer 等类和方法在 AOSP android-17.0.0_r1 中不存在)；(2)全文从百科词条式列表重写为 Type A 机制原理叙述；(3)§7-10 空洞内容压缩为实用调试指导；(4)新增 Perfetto 观测 SDM 编译指导；(5)性能数据标注来源警告和验证方法。已回送 Task6 复审。"
task6_review_notes: "2026-07-13T22:10 复审：L1 禁用词(链路)已修 5 处。B 类大问题：虚构代码/百科词条结构/§7-10空洞/无Trace指导/数据无来源。2026-07-13 重度回炉已全部处理。"
task9_review_notes: "2026-07-13 Task9 deep review 发现 P0/P1 问题；2026-07-13 Task2B 回炉修复：P0-DexMetadataHelper 源码锚点核实(现稿正确否定 pm.dexopt.dm.require_manifest / require_fsverity 属性，这三项在 r1 中不存在)+P1-性能数据验证方法补充+P1-SDM 版本演进对比(Android 14→17)。2026-07-29 hermes-aiw-review-finalize-apply 复审通过。"
review_type: task9-deep-tech-review
last_task9_review_log: logs/deep-review/2026-07-13-22-deep-review.md
applicable_versions: "Android 16 (API 36) - Android 17 (API 37)"
drafted_date: "2026-06-11"
last_verified: "2026-07-30"
last_verified_against: "AOSP android-17.0.0_r1 (PackageInstallerSession / PackageManagerShellCommand / DexOptHelper / PrimaryDexopter / Dexopter / DexoptStatus / ReasonMapping / ArtFileManager / ArtManagedInstallFileHelper / DexMetadataHelper / artd / oat_file / sdc_file / path_utils); Configure ART"
confidence: high
sources:
  - type: aosp
    path: "https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/libartservice/service/java/com/android/server/art/PrimaryDexopter.java"
  - type: aosp
    path: "https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/libartservice/service/java/com/android/server/art/Dexopter.java"
  - type: aosp
    path: "https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/libartservice/service/java/com/android/server/art/model/DexoptStatus.java"
  - type: aosp
    path: "https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/libartservice/service/java/com/android/server/art/ReasonMapping.java"
  - type: aosp
    path: "https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/libartservice/service/java/com/android/server/art/ArtFileManager.java"
  - type: aosp
    path: "https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/libartservice/service/java/com/android/server/art/ArtManagedInstallFileHelper.java"
  - type: aosp
    path: "https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/libartservice/service/java/com/android/server/art/ArtManagerLocal.java"
  - type: aosp
    path: "https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/libartservice/service/java/com/android/server/art/DexMetadataHelper.java"
  - type: aosp
    path: "https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/artd/artd.cc"
  - type: aosp
    path: "https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/artd/path_utils.cc"
  - type: aosp
    path: "https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/runtime/oat/oat_file.cc"
  - type: aosp
    path: "https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/runtime/oat/sdc_file.cc"
  - type: aosp
    path: "https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/pm/PackageInstallerSession.java"
  - type: aosp
    path: "https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/pm/PackageManagerShellCommand.java"
  - type: aosp
    path: "https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/pm/DexOptHelper.java"
  - type: aosp
    path: "https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/content/pm/dex/DexMetadataHelper.java"
  - type: aosp
    path: "https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/cmds/installd/dexopt.cpp"
  - type: official
    path: "https://source.android.com/docs/core/runtime/configure"
  - type: material
    path: "DeepResearch/2026-06-09-android17-cloud-compilation-sdm-dm-ondevice-flow.md"
  - type: material
    path: "intake/research-feeds/2026-04-07-11-android16-cloud-compilation-baseline-startup-profiles.md"
tags: ["SDM", "cloud-compilation", "dexopt", "ART-Service", "install-performance", "Android-16", "Android-17"]
related_chapters: ["16.6", "1.9", "1.23", "21.11"]
created_by: "task2a-knowledge-gap"
created_date: "2026-06-11"
---

# Android 17 Secure Dex Metadata：安装、验证与运行时加载

## 结论

Android 17 的 SDM 全名是 **Secure Dex Metadata**。它是 Android 16 引入的、按指令集区分并由 APK 签名者签名的云端编译产物容器。AOSP `android-17.0.0_r1` 没有名为 “Staged Dalvik Compilation” 的架构，也没有把 SDM 解包到应用 `oat` 目录的安装步骤。

一组可供 ART 使用的云端产物由三个文件配合：

| 文件 | 典型内容 | 生成方 | 在流程中的职责 |
|---|---|---|---|
| `.dm` | `primary.prof`、`primary.vdex`，可带 `config.pb` | 分发侧 | 提供云端 Profile 或与 SDM 配套的 VDEX |
| `.sdm` | 至少包含供运行时打开的 `primary.odex` | 云端编译服务 | 提供指定 ISA 的 AOT 代码 |
| `.sdc` | SDM 时间戳与设备 ART APEX 版本 | 设备端 `artd` | 把收到的 SDM 与当前设备环境绑定，识别替换和 samegrade 情况 |

SDM 只覆盖 base APK 与 split APK 内的 **primary dex**。动态生成或由自定义 ClassLoader 加载的 secondary dex 不在这套 SDM 支持范围内。`ArtFileManager` 在 r1 源码中直接写明 “SDM files are only for primary dex files”。

性能收益也有明确边界：当 SDM、DM、SDC 与当前 APK、ISA、boot classpath 和编译目标兼容时，安装期可以避开一次本机 `dex2oat`。安装会话写盘、APK 与 SDM 签名校验、包扫描、原生库处理、`fsync`、SELinux 操作以及首次启动的其余工作仍会发生。AOSP 没有承诺固定的安装或启动提升百分比。

AOSP `android-17.0.0_r1` 是以下结论的平台源码锚点。云端如何选择设备配置并生成 SDM 不属于 AOSP 开源设备端实现，讨论范围只包括系统能够验证的接收、决策和加载行为。

## 1. 先分清 DM、SDM 与 SDC

### 1.1 `.dm`：Dex Metadata

`.dm` 是 ZIP 文件，文件名与对应 APK 同基名：

| APK | 对应 DM |
|---|---|
| `base.apk` | `base.dm` |
| `split_feature.apk` | `split_feature.dm` |

ART Service 的 `DexMetadataHelper.getType()` 检查 ZIP 中的 `primary.prof` 与 `primary.vdex`，并把结果分成 `PROFILE`、`VDEX`、`PROFILE_AND_VDEX`、`NONE` 或 `ERROR`。`config.pb` 可以附带配置；缺少它时，ART Service 使用默认配置。

这两个有效负载用途不同：

- `primary.prof` 列出适合 `speed-profile` 的方法和类，可作为本机 dexopt 输入。
- `primary.vdex` 保存验证相关数据。SDM 路径打开 AOT 代码时，运行时会从配套 DM 读取它。

平台层的 `android.content.pm.dex.DexMetadataHelper.validateDexMetadataFile()` 在 r1 中通过 `StrictJarFile` 打开归档，确认文件结构可读。该 tag 的实现中没有 `pm.dexopt.dm.require_manifest` 与 `pm.dexopt.dm.require_fsverity` 属性，也不存在受支持的 `pm install --dm` 参数。不能用这三项判断 Android 17 的 DM 状态。

AOSP 的 [Configure ART](https://source.android.com/docs/core/runtime/configure) 文档描述了常见的 Pixel 策略：Play 分发的 DM 可携带 cloud profile，ART 对其中列出的方法做 AOT 编译；没有 DM 时，该策略可能在安装期不做 AOT。它描述的是一种产品配置，OEM 仍可通过 ART Service 配置选择不同的安装 compiler filter。

### 1.2 `.sdm`：Secure Dex Metadata

SDM 的文件名多一段指令集名称。`artd/path_utils.cc` 的构造规则可概括为：

| APK | ISA | 对应 SDM |
|---|---|---|
| `base.apk` | `arm64` | `base.arm64.sdm` |
| `split_feature.apk` | `arm64` | `split_feature.arm64.sdm` |

同一个 APK 若要覆盖两种 ISA，需要两个不同的 SDM。安装器不能拿 `arm64` 产物供 `arm` 进程使用。

SDM 使用 APK Signature Scheme v3 校验。`ArtManagedInstallFileHelper.validateSdmFile()` 会处理以下条件：

- 文件名没有受支持的 ISA 后缀；
- 找不到同基名 APK；
- APK 的 v3 签名无法验证；
- SDM 的 v3 签名无法验证；
- APK 与 SDM 的 signer 集合不完全相同。

在 `artManagedInstallFilesValidationApi()` 对应的新验证分支中，这些结果被标为 `RESULT_SHOULD_DELETE_AND_CONTINUE`：`PackageInstallerSession` 删除无效伴随文件、记录 warning，并继续处理安装。r1 仍保留旧分支；旧分支遇到无效 SDM 时可能直接拒绝安装。分析日志时应先确认设备采用哪条 flag 分支，不能把“无效 SDM 一定回退”写成无条件结论。

SDM 的签名约束说明它可以通过安装会话安全接收。AOSP 没有限定调用方必须是 Play；`adb install-multiple` 也识别 `.apk`、`.dm` 与 `.sdm` 后缀。难点在于获得名称正确、与 APK signer 完全一致且适配目标 ISA 的有效产物，普通开发构建通常没有这样的 SDM。

### 1.3 `.sdc`：Secure Dex Metadata Companion

SDC 由设备生成，不随应用商店下载。`PrimaryDexopter.onDexoptStart()` 会在 Android 16 及以上、非 pre-reboot 流程中，按 primary dex 的每个 ABI 请求 `artd.maybeCreateSdc()`。

下面这一行展示 ART Service 到 `artd` 的调用位置：

```java
mInjector.getArtd().maybeCreateSdc(outputSdc);
```

调用发生在 dexopt 决策之前。SDM 不存在时，`artd` 返回成功；源码注释把这种情况称为常态，因此缺少 SDM 本身不构成安装错误。

SDC 是两行文本，内容形式如下：

```text
sdm-timestamp-ns=<SDM 的 mtime，纳秒>
apex-versions=<当前设备 ART 看到的 APEX 版本串>
```

运行时会比较 SDC 保存的时间戳与当前 SDM 的 `st_mtim`。两者不同，说明 SDM 在 SDC 建立后被替换，产物不会被采用。`apex-versions` 会覆盖 OAT header 中对应值，用于识别同版本 ART APEX 替换测试（samegrade placebo）场景。

SDC 的位置由目标 OAT 位置决定：常见情况是应用旁 `oat/<isa>/` 下的 `.sdc`，需要 dalvik-cache 时则使用 dalvik-cache 对应位置。不要把它描述成 SDM 的签名文件；签名验证在安装阶段完成，SDC 解决的是设备环境与文件代际匹配。

## 2. 从安装会话到 ART Service

### 2.1 安装器接收伴随文件

`PackageInstallerSession` 把 `.dm`、`.sdm` 等识别为 ART-managed install files，并在提交前校验文件名映射与 SDM 签名。它处理的是会话中的独立文件，不会从 APK 内“提取 SDM”。

文件名必须能反推出会话中的对应 APK。以 `base.arm64.sdm` 为例，验证器移除 `.arm64.sdm` 后补回 `.apk`，得到 `base.apk`。如果 APK 被临时改名而伴随文件没有同步命名，验证就会失败。

在具备合法测试产物时，可用下面的命令验证安装器是否接受三类文件：

```bash
adb install-multiple base.apk base.dm base.arm64.sdm
```

这条命令只演示文件提交方式。`base.arm64.sdm` 必须使用与 `base.apk` 完全相同的 signer 集合，并且设备要运行对应 ISA；随手创建同名 ZIP 无法进入可用路径。

### 2.2 dexopt 的执行所有者

Android 14 起，应用 dexopt 的调度入口已经迁到 ART Service。Android 17 r1 中的职责分配是：

| 组件 | 职责 |
|---|---|
| Package Manager | 完成安装事务，在需要时发起安装 dexopt |
| ART Service Java 层 | 选择 primary dex、ABI、compiler filter、Profile 与优先级 |
| `artd` | 校验受保护路径、检查现有产物、准备文件并启动编译器 |
| `dex2oat` | 需要本机编译时生成 VDEX、ODEX 与可选 ART image |
| ART runtime | 应用启动或加载 dex 时选择并映射兼容产物 |

`installd` 仍处理安装系统中的其他受特权文件操作，但 `frameworks/native/cmds/installd/dexopt.cpp` 已不适合作为 Android 17 应用 dexopt 的中心流程图。把 DM Profile 合并和 SDM 调度都归给 `installd` 会掩盖 ART Service 与 `artd` 的现有边界。

### 2.3 ART 如何决定跳过本机编译

安装触发 `DexOptHelper.performDexoptIfNeededAsync()` 后，ART Service 为每个 primary dex 与 ABI 构造目标。`Dexopter` 大体经历以下阶段：

1. `PrimaryDexopter.onDexoptStart()` 尝试建立或刷新 SDC。
2. ART Service 根据安装 reason、DM 类型、Profile 与产品配置确定目标 compiler filter。
3. `artd.getDexoptNeeded()` 结合 APK、boot classpath、现有本地产物以及 SDM 组合判断目标是否已经满足。
4. 现有产物满足目标时，结果为无需本机 dexopt。
5. 产物缺失、过期或 compiler filter 不满足要求时，`artd.dexopt()` 启动 `dex2oat`。

SDM 因而属于 OatFileAssistant 可选择的产物位置，AIDL 对外暴露 `SDM_DALVIK_CACHE` 与 `SDM_NEXT_TO_DEX` 两个位置值。它没有单独取代 dexopt 调度器；调度器仍要判断这份云端产物能否满足当前目标。

若本机编译已执行，`PrimaryDexopter` 会尽早删除对应 SDM 与 SDC，释放空间。相关源码条件可缩写为：

```java
if (status == DexoptResult.DEXOPT_PERFORMED && !mInjector.isPreReboot()) {
    mInjector.getArtd().deleteSdmSdcFiles(...);
}
```

删除动作也说明 SDM 是可被本机编译结果替代的 dexopt artifact。即使没有立即删除，ART 文件 GC 也会回收失效产物。

## 3. 运行时怎样使用 SDM

### 3.1 直接从 ZIP 打开 `primary.odex`

r1 不会在安装阶段把 SDM 解包并复制到 `/data/app/<pkg>/oat/<isa>/`。r1 `OatFileBase::OpenOatFileFromSdm()` 把 ZIP 内部条目名拼成 `<sdm>!/primary.odex`，随后直接加载。

下面两行给出 ODEX 与 VDEX 的真实来源：

```cpp
std::string elf_filename = sdm_filename + kZipSeparator + "primary.odex";
ret->vdex_ = VdexFile::OpenFromDm(dm_filename, error_msg);
```

ODEX 来自 SDM，VDEX 来自同 APK 的 DM。缺少可用 DM/VDEX 时，仅有 SDM 也无法组成这条运行时加载路径。运行时还需要 APK 自身校验 dex checksum 与依赖关系。

`OatFile::OpenFromSdm()` 带有名为 `Open sdm file <path>` 的 `ScopedTrace`。抓取应用启动 trace 时，这个 slice 比“`oat` 目录里有没有 `.odex`”更能说明 SDM 被运行时打开。

### 3.2 兼容性判断仍然完整

云端产物没有绕过 ART 的兼容性检查。OatFileAssistant 仍会核对：

- APK dex checksum；
- boot classpath 与 class loader context；
- compiler filter 是否满足请求；
- OAT/VDEX 状态；
- SDM 与 SDC 的时间戳关系；
- SDC 保存的 ART APEX 版本上下文。

其中任一条件不满足，系统可以选择较弱的已有产物、解释/JIT 执行，或安排本机 dexopt，具体取决于当前 reason、filter 与设备策略。看到 SDM 文件存在，只能证明安装器曾接收过文件，不能证明运行时正在执行其中的机器码。

### 3.3 DM reason 不能单独证明内容被采用

`ReasonMapping` 中存在 `cloud` reason，也存在带 `-dm` 后缀的安装 reason。`Dexopter` 源码注释明确提示：`-dm` 只表示本次调用传入过 DM，空 DM 或内容未被使用时也可能出现该后缀。

判断云端产物是否生效应组合三类证据：

1. `pm art dump <package>` 的 compiler filter、reason 与 location；
2. trace 中是否出现本机 `dex2oat`，以及是否出现 `Open sdm file`；
3. 安装日志中的 SDM validation warning、`artd` 错误和 dexopt 结果。

只看 `install-dm`、只看文件存在，或只看安装总耗时，都不足以确认 SDM 路径。

## 4. 性能收益来自哪里

### 4.1 能省掉的工作

可用的 SDM 组合已经带有指定 ISA 的 AOT 代码，并由 DM 提供匹配 VDEX。若它满足安装目标，设备无需在安装阶段为同一目标运行 `dex2oat`，可减少：

- 编译器进程的 wall time；
- dex2oat 的 CPU 时间与临时内存峰值；
- 本机生成 ODEX/VDEX 的写放大；
- 安装期编译造成的热量与功耗。

收益随应用 dex 规模、目标 filter、CPU、存储、温控和产品安装策略变化。安装策略原本使用 `verify` 或不做 AOT 的设备，能够省掉的本机编译本来就少。

### 4.2 仍需支付的工作

SDM 不会消除以下开销：

- APK、DM、SDM 的下载与安装会话写入；
- APK 与 SDM 的 v3 签名解析和 signer 比较；
- APK 解析、权限与包状态更新；
- 原生库提取或映射；
- 文件搬移、`fsync`、配额和 SELinux 操作；
- SDC 创建及 ART 产物兼容性检查；
- 未被 AOT 覆盖的方法解释执行与 JIT；
- 应用自身初始化、I/O、Binder 调用和首帧绘制。

因此“携带 SDM 后安装近似零成本”不成立。安装总耗时若主要花在下载、写盘或包扫描，dex2oat 的减少对总值影响有限。

### 4.3 不应照搬固定百分比

AOSP r1 源码没有给出 “安装时间减少 40%～60%”“冷启动减少 30%～45%” 或 “体积减少 15%～25%” 的保证，也没有定义可推出这些数字的基准。缺少测试设备、APK、compiler filter、采样次数与置信区间的百分比不应进入工程结论。

冷启动也可能出现方向不同的变化：省掉安装期编译通常有利于安装体验，SDM 的映射、ZIP 访问和页缺失特征却可能与本地产物不同。应把安装 wall time、首次启动与后续启动分开测量。

## 5. 建立可复现的 A/B/C 实验

### 5.1 三组输入

同一 APK 版本建议准备三组安装输入：

| 组别 | 输入 | 回答的问题 |
|---|---|---|
| A | APK | 设备默认安装策略的基线 |
| B | APK + DM | cloud profile 或 VDEX 对本机 dexopt 的影响 |
| C | APK + DM + 对应 ISA 的 SDM | 云端 AOT 产物能否避开本机 dex2oat |

三组实验要固定设备构建、ART APEX 版本、电量、温度区间、存储余量、网络条件和 APK 字节。每组至少多次冷安装，并报告中位数、P90 与失败/回退次数。更新安装和全新安装应分开统计。

### 5.2 采集指标

安装阶段记录：

- `adb install-multiple` 的端到端 wall time；
- Package Manager 的 `dexopt` slice；
- `dex2oat` 进程是否出现、wall time、CPU time 与峰值 RSS；
- SDM 校验 warning；
- ART stats 中 `ART_DEX2OAT_REPORTED` 的 compiler filter、compilation reason、DM type、ISA、状态、输出大小与耗时；
- 安装前后 `/data` 占用变化。

启动阶段记录：

- TTID 与 TTFD；
- `Open sdm file` slice；
- 主线程 runnable、I/O wait 与 major fault；
- JIT 活动和后台 dexopt；
- 连续多次启动后的变化。

`am start -W` 适合做快速筛查，无法替代 Macrobenchmark 或带统计设计的 Perfetto 实验。测试 C 组时，还要把“SDM 被接收”和“SDM 被运行时采用”分成两个检查点。

## 6. 用命令与 Perfetto 定位问题

### 6.1 读取 ART Service 状态

下面的命令查看单个包的 dexopt 状态，并保留安装与 ART 相关日志：

```bash
adb shell pm art dump com.example.app
adb shell getprop pm.dexopt.install
adb shell logcat -s artd PackageManager DexMetadataHelper
```

`pm art dump` 会列出 dex container、ABI、compiler filter、compilation reason 与 location。location 若指向 SDM 内的 `primary.odex`，证据强于 reason 字符串。`getprop` 反映产品当前安装 filter，不能用来推断某次安装已完成的具体决策。

生产版设备通常不允许 shell 枚举 `/data/app` 内部目录。文件级核对只适用于 root、userdebug/eng 或测试基础设施已经授予访问权的环境；普通设备应依赖 `pm art dump`、日志和 trace。

### 6.2 Perfetto 的四个时间点

一次覆盖安装到首次启动的 trace，可按以下顺序阅读：

1. Package Manager 的 `dexopt` slice：安装流程在 ART 上停留多久。
2. `artd` 与 `dex2oat`：是否启动本机编译，线程在哪些 CPU 上运行。
3. 应用进程的 `Open sdm file <path>`：运行时是否尝试打开 SDM。
4. 应用启动主线程：SDM 之外的初始化、I/O 与首帧瓶颈。

找不到 `dex2oat` 不能单独证明 SDM 生效，产品策略使用 `verify` 或沿用兼容本地产物时也会出现这种 trace。应再查看 ART dump 的 location 与 `Open sdm file`。

下面的 SQL 用于在 trace 中同时搜索本机编译和 SDM 打开事件：

```sql
SELECT ts, dur, name
FROM slice
WHERE name GLOB '*dex2oat*'
   OR name GLOB 'Open sdm file *'
ORDER BY ts;
```

查询结果要与安装时间窗和目标包对应。系统上可能同时为其他包做后台 dexopt，单凭进程名容易把无关编译计入样本。

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

这些服务端步骤没有开源在 AOSP 中。设备端源码能证明接收协议和兼容性条件，无法证明某个应用商店在何时生成、覆盖哪些机型或使用哪个 compiler filter。

### 7.2 应用工程师需要做什么

应用代码通常无需感知 SDM。工程侧更有价值的工作包括：

- 提供高质量 Baseline Profile，覆盖非云端分发和云端数据尚未成熟的用户；
- 用 Macrobenchmark 验证 Profile 覆盖与 TTID/TTFD；
- 控制反射、动态 dex 与冷启动主线程工作量；
- 将安装性能与启动性能分别设定指标；
- 在主要分发渠道建立 A/B/C 样本，持续观察 SDM 接收、采用和回退率。

Baseline Profile 与 cloud profile 的覆盖来源不同。前者随应用构建发布，后者由分发侧运行数据生成；两者都可能成为 ART 编译输入，不能把 SDM 当作 Baseline Profile 的替代品。

## 8. 版本边界

| 平台版本 | SDM 相关状态 |
|---|---|
| Android 14 / API 34 | ART Service 接管应用 dexopt 调度；常见云端优化仍以 DM cloud profile 驱动本机 AOT 为主 |
| Android 15 / API 35 | 延续 ART Service 与 DM 流程；这里核对的 SDM 格式尚未作为该版本基线 |
| Android 16 / API 36 | `ArtManagedInstallFileHelper` 源码注释标记 SDM 格式从此版本引入 |
| Android 17 / API 37 | `android-17.0.0_r1` 延续 SDM/SDC，并明确 primary dex、v3 signer、运行时 ZIP 加载与本机 dexopt 后清理行为 |

不要根据 `main` 分支上的实验 flag 推断 r1 行为。`cloudCompilationPm()` 和 `FLAG_ART_SERVICE_V3` 没有作为依据，因为核对的 r1 Package Manager 与 ART 源码中找不到这些名称。secondary dex 支持、默认开启比例和商店覆盖率也不能算作 Android 17 已有能力。

## 源码索引

- [ArtManagedInstallFileHelper.java：DM/SDM 文件名与 signer 验证](https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/libartservice/service/java/com/android/server/art/ArtManagedInstallFileHelper.java)
- [PrimaryDexopter.java：建立 SDC 与本机 dexopt 后清理](https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/libartservice/service/java/com/android/server/art/PrimaryDexopter.java)
- [ArtFileManager.java：SDM 只覆盖 primary dex](https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/libartservice/service/java/com/android/server/art/ArtFileManager.java)
- [Dexopter.java：DM reason 与 dexopt 决策](https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/libartservice/service/java/com/android/server/art/Dexopter.java)
- [DexoptStatus.java：compiler filter、reason 与 location](https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/libartservice/service/java/com/android/server/art/model/DexoptStatus.java)
- [DexMetadataHelper.java：DM 内容分类](https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/libartservice/service/java/com/android/server/art/DexMetadataHelper.java)
- [artd.cc：SDC 创建、路径校验与 dexopt 执行](https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/artd/artd.cc)
- [path_utils.cc：SDM/SDC 路径构造](https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/artd/path_utils.cc)
- [oat_file.cc：从 SDM 打开 ODEX、从 DM 打开 VDEX](https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/runtime/oat/oat_file.cc)
- [sdc_file.cc：SDC 的两个字段](https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/runtime/oat/sdc_file.cc)
- [PackageInstallerSession.java：安装会话验证结果处理](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/pm/PackageInstallerSession.java)
- [PackageManagerShellCommand.java：安装命令如何提交伴随文件](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/pm/PackageManagerShellCommand.java)
- [DexMetadataHelper.java：平台侧 DM 归档验证](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/content/pm/dex/DexMetadataHelper.java)
- [Configure ART：cloud profile、编译产物与 compiler filter](https://source.android.com/docs/core/runtime/configure)

## 相关章节

- [16.6 Android 16 云端 Profile 与 dexopt 安装优化](./06-android16-cloud-profile-dexopt.md)：补充 DM cloud profile 与本机 dexopt 决策。
- [1.7 ART 编译管线与 dex2oat 优化](../../part1-fundamentals/ch01-architecture/07-art-compilation.md)：解释 ODEX、VDEX、AOT、JIT 与 compiler filter。
- [1.23 Android Staged Install 与安装原子性性能](../../part1-fundamentals/ch01-architecture/23-staged-install-performance.md)：区分安装会话的 staged 语义与 Secure Dex Metadata。
- [21.11 云端 Profile、DM 文件与安装后编译优化](../../part5-app/ch21-startup/11-cloud-profile-dm-install-compile.md)：从应用启动角度补充 DM 与 Profile。
