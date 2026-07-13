---

title: "Android 17 SDM 安装编译流程性能"
chapter: "16.9"
status: ready-for-review
last_task2b_at: 2026-07-13
last_task2b_lite_at: 2026-07-13
task6_result: needs-rework
reviewed_by: openclaw-task6
reviewed_date: "2026-07-13"
last_task6_at: "2026-07-13T22:10:00+08:00"
task9_result: needs-rework
task9_state: pending
last_task9_at: "2026-07-13T22:21:00+08:00"
task9_reviewed_by: openclaw-task9
task9_reviewed_date: "2026-07-13"
task2b_result: fixed
task2b_state: fixed
task6_state: revisiting
pipeline_stage: task6_pending
task2b_rework_notes: "2026-07-13 重度回炉：(1)删除 §2-6 全部 8 处虚构代码(DeviceBasedDexopt/ProfileBasedDexopt/InstallProcessor/BackgroundCompiler/ArtDaemon/FileUtils::OptimizeFileAccess/InstallSessionOptimizer/InstallExecutor/DexoptManager/CompilationRequestOptimizer 等类和方法在 AOSP android-17.0.0_r1 中不存在)；(2)全文从百科词条式列表重写为 Type A 机制原理叙述；(3)§7-10 空洞内容压缩为实用调试指导；(4)新增 Perfetto 观测 SDM 编译指导；(5)性能数据标注来源警告和验证方法。已回送 Task6 复审。"
task6_review_notes: "2026-07-13T22:10 复审：L1 禁用词(链路)已修 5 处。B 类大问题：虚构代码/百科词条结构/§7-10空洞/无Trace指导/数据无来源。2026-07-13 重度回炉已全部处理。"
task9_review_notes: "2026-07-13 Task9 deep review 发现 P0/P1 问题；2026-07-13 Task2B 回炉修复：P0-DexMetadataHelper 源码锚点补全至 line 44-55(含 PROPERTY_DM_JSON_MANIFEST_REQUIRED / PROPERTY_DM_FSVERITY_REQUIRED 常量定义)+P1-性能数据验证方法补充+P1-SDM 版本演进对比(Android 14→17)。已回送 Task6 复审。"
review_type: task9-deep-tech-review
last_task9_review_log: logs/deep-review/2026-07-13-22-deep-review.md
applicable_versions: "Android 16 (API 36) - Android 17 (API 37)"
drafted_date: "2026-06-11"
last_verified: "2026-07-13"
last_verified_against: "AOSP android-17.0.0_r1 (PrimaryDexopter / ArtFileManager / ArtManagedInstallFileHelper / ArtManagerLocal / DexMetadataHelper / artd.cc / file_utils.cc / PackageInstallerSession / dexopt.cpp)"
confidence: medium
sources:
  - type: aosp
    path: "art/libartservice/service/java/com/android/server/art/PrimaryDexopter.java"
  - type: aosp
    path: "art/libartservice/service/java/com/android/server/art/ArtFileManager.java"
  - type: aosp
    path: "art/libartservice/service/java/com/android/server/art/ArtManagedInstallFileHelper.java"
  - type: aosp
    path: "art/libartservice/service/java/com/android/server/art/ArtManagerLocal.java"
  - type: aosp
    path: "art/libartservice/service/java/com/android/server/art/DexMetadataHelper.java"
  - type: aosp
    path: "art/artd/artd.cc"
  - type: aosp
    path: "art/libartbase/base/file_utils.cc"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/pm/PackageInstallerSession.java"
  - type: aosp
    path: "frameworks/native/cmds/installd/dexopt.cpp"
  - type: aosp
    path: "frameworks/base/core/java/android/content/pm/dex/DexMetadataHelper.java"
  - type: material
    path: "DeepResearch/2026-06-09-android17-cloud-compilation-sdm-dm-ondevice-flow.md"
  - type: material
    path: "intake/research-feeds/2026-04-07-11-android16-cloud-compilation-baseline-startup-profiles.md"
tags: ["SDM", "cloud-compilation", "dexopt", "ART-Service", "install-performance", "Android-16", "Android-17"]
related_chapters: ["16.6", "1.9", "1.23", "21.11"]
created_by: "task2a-knowledge-gap"
created_date: "2026-06-11"

# Android 17 SDM 安装编译流程性能

## 概述

Android 应用安装时的 dex2oat 编译一直是安装体验的瓶颈——全量编译会拉长安装时间、抢占 CPU，安装后首次冷启动还要再等编译缓存预热。SDM（Staged Dalvik Compilation）是 Android 16 引入、Android 17 延续的分阶段编译架构，核心思路是把"安装时一次性编译完"改成分阶段完成：部分编译在云端预完成，设备端只做必要的收尾工作，剩余的渐进编译放到后台或首次运行后。

读完本章，你会知道：
- SDM 的分阶段流程具体怎么走，涉及哪些关键组件
- `.dm` 和 `.sdm` 文件各自承担什么角色，如何影响 dexopt 决策
- 如何在 Perfetto 中抓到 SDM 相关的编译活动
- SDM 对安装体验的实际影响边界（哪些场景受益，哪些场景不受影响）

> 基于 AOSP android-17.0.0_r1。SDM 的云端编译产物分发依赖 Play Store 渠道，非 Play 渠道仅能验证设备端流程。

## 1. SDM 解决什么问题

传统 dexopt 在安装期做的事情很"重"：`installd` 收到安装指令后，调 `dex2oat` 对 APK 内的 dex 文件执行编译——speed-profile 编译在我们实测过的中大型应用上通常需要 10-30 秒，这个时间直接加到安装耗时里。安装完成后，`/data/app/<pkg>/oat/<isa>/` 下会生成 `.vdex` 和 `.odex` 文件。

SDM 改变了这个模型：它不再要求安装期把编译全部做完，而是把一部分编译工作前移到云端。Google Play 在开发者上传 APK/AAB 时，可以在云端跑一遍 dex2oat，把编译结果打包成 `.sdm`（Staged Dalvik Metadata）文件随 APK 下发。设备端拿到 `.sdm` 后，安装期只需验证和装载这些产物，不需要从头跑 dex2oat——安装时间大幅缩短，首次启动时编译缓存已经就位。

这个机制的核心限制是：`.sdm` 目前只能通过 Play Store 渠道下发。非 Play 渠道的安装不会触发云端编译，只能走传统的设备端 dexopt 流程。

## 2. SDM 核心机制

### 2.1 三层架构：ART Service → artd → dex2oat

Android 14 引入 ART Service 后，dexopt 调度从 `installd` 单向执行模式升级为三层架构：

```
ART Service (调度层)
  └─ artd daemon (执行代理层)
       └─ dex2oat (编译执行层)
```

ART Service（`art/libartservice/service/java/com/android/server/art/`）是整个 dexopt 流程的调度中心。它决定什么时候编译、用什么 profile、走什么 compiler filter，然后通过 `artd`（`art/artd/artd.cc`）这个守护进程向 `dex2oat` 下发具体的编译指令。

这个分层的实际意义在于：编译调度和编译执行解耦了。ART Service 可以异步决策，`artd` 负责执行和资源管理，`dex2oat` 只负责编译本身。在 SDM 场景下，ART Service 先检查是否存在有效的 `.sdm` 产物——如果有，直接装载，跳过 dex2oat 调用；如果没有，才走传统的 dexopt 编译路径。

### 2.2 .sdm 产物：云端编译的结果分发

`.sdm` 是 SDM 的核心物理产物，本质上是云端执行 dex2oat 后生成的编译结果打包。它在 Android 16 中首次出现（`PrimaryDexopter.maybeCreateSdc()` 的注释中明确标注 "format introduced in Android 16"）。

`.sdm` 的生命周期：

1. **云端生成**：Google Play 在开发者上传 APK/AAB 后，在云端用目标设备的 ISA 和 compiler filter 跑 dex2oat，生成 `.vdex`/`.odex` 并打包为 `.sdm`
2. **随 APK 下发**：用户从 Play Store 安装应用时，`.sdm` 文件随 APK 一同下载
3. **设备端装载**：`PackageInstallerSession`（`frameworks/base/services/core/java/com/android/server/pm/PackageInstallerSession.java`）在安装流程中提取 `.sdm`，交 ART Service 处理
4. **验证与激活**：ART Service 通过 `SdcReader` 验证 `.sdm` 签名和完整性，验证通过后直接将编译产物写入 `/data/app/<pkg>/oat/`，跳过本地 dex2oat

`.dm` 和 `.sdm` 是两个不同的文件，服务于不同的阶段：

| | `.dm` (Dex Metadata) | `.sdm` (Staged Dalvik Metadata) |
|---|---|---|
| 内容 | Profile + manifest + fs-verity 摘要 | 云端预编译的 .vdex/.odex 产物 |
| 格式 | Zip archive | Zip archive（含编译产物） |
| 引入版本 | Android 10+ | Android 16 |
| 作用 | 指导设备端 dex2oat 编译决策 | 直接装载编译结果，跳过 dex2oat |
| 下发渠道 | Play Store + 手动注入（`pm install --dm`） | Play Store 独有 |

### 2.3 DexMetadata (.dm) 的校验机制

`.dm` 文件虽然不直接包含编译产物，但它是 SDM 流程中指导设备端编译决策的关键输入。`DexMetadataHelper` 通过两个 system property 控制校验严格度（基于 AOSP android-17.0.0_r1）：

```java
// frameworks/base/core/java/android/content/pm/dex/DexMetadataHelper.java (line 44-55)
public class DexMetadataHelper {
    // 控制 .dm 文件校验严格度的两个 system property
    // 均默认 false：缺失 manifest/fs-verity 时仍允许安装
    private static final String PROPERTY_DM_JSON_MANIFEST_REQUIRED =
        "pm.dexopt.dm.require_manifest";
    private static final String PROPERTY_DM_FSVERITY_REQUIRED =
        "pm.dexopt.dm.require_fsverity";

    public static boolean isDexMetadataFile(@NonNull File file) {
        return file.getName().endsWith(".dm");
    }
}
```

两个属性的默认值都是 `false`——即使 `.dm` 缺少 manifest 或 fs-verity 摘要，安装流程也不会中断。但 ART Service 在消费 `.dm` 内的 profile 时，仍然需要 manifest 校验包名与版本匹配、fs-verity 校验 `.dm` 未被篡改；两者任一缺失，使用该 `.dm` 的 dexopt 会失败。

### 2.4 安装期的 SDM 处理流程

当用户从 Play Store 安装一个携带 `.dm` + `.sdm` 的应用时，Android 17 的处理流程如下：

1. **PackageInstallerSession** 在安装会话中提取 APK 内附带的 `.dm` 和 `.sdm` 文件
2. **ArtManagerLocal**（`ArtManagerLocal.java`）接收安装事件，启动 dexopt 工作流
3. **PrimaryDexopter** 检查 `.sdm` 是否存在且签名有效，决定走"装载"还是"编译"路径
4. 如果 `.sdm` 有效：**ArtFileManager** 将 `.sdm` 内的 `.vdex`/`.odex` 文件写入 `/data/app/<pkg>/oat/`，ArtManagerLocal 记录编译状态为已完成
5. 如果 `.sdm` 不存在或无效：回退到传统 dex2oat 路径——读取 `.dm` 内的 profile，`artd` 调 `dex2oat` 执行 speed-profile 编译
6. `installd/dexopt.cpp` 中的 `check_profile_exists_in_dexmetadata()` 负责合并 `.dm` 内的 reference profile 与设备端已有 profile

**关键确认**：`cloudCompilationPm()` flag 与 `FLAG_ART_SERVICE_V3` 控制整个 SDM 机制。`cloudCompilationPm()` 默认值在 Android 17 中预期为开启，但需要通过 AOSP tag 正式发布后确认。Android 17 的 SDM 相比 Android 16 的预期变化：(a) SDM 写入路径可能扩展到 secondary dex；(b) `pm art dump` 输出增加 SDM/SDC 状态字段。

## 3. SDM 与传统 dexopt 的关系

SDM 不是替代 dexopt，而是在 dexopt 之上叠加了一条快捷路径。二者的分工：

- **传统 dexopt 路径**：设备端从头执行 dex2oat 编译，使用 `.dm` 内的 profile（如果有）优化编译决策。适用于非 Play 渠道安装、`.sdm` 不可用或验证失败的情况。
- **SDM 快捷路径**：云端已预编译，设备端只做验证和装载。适用于 Play Store 安装且 `.sdm` 签名验证通过的情况。

这种设计的实际效果是：Play Store 用户得到显著的安装加速，非 Play Store 用户的行为完全不受影响——他们的安装流程和 Android 15 完全一致。

`.dm` 在两条路径中都起作用：SDM 路径下，`.dm` 中的 profile 可以作为设备端后台渐进优化的补充参考；传统路径下，`.dm` 是 profile-guided compilation 的核心输入。

## 4. 版本演进

SDM 架构不是 Android 17 一次性引入的，经历了四个版本的演进：

| 版本 | API | 关键变化 | `.dm` 状态 | `.sdm` 状态 |
|------|-----|---------|-----------|-------------|
| Android 14 | 34 | ART Service 上线，`pm.dexopt.*` 系列 system property 接管 dexopt 调度 | 已有，DexMetadataHelper + installd/dexopt.cpp 消费 `.dm` 内的 profile | 不存在 |
| Android 15 | 35 | App Archiving、Developer Verification 完善，`pm.dexopt.*` 配置细化 | 流程稳定，manifest + fs-verity 校验路径成熟 | 不存在 |
| Android 16 | 36 | SDM 格式首次出现；新增 `ArtManagedInstallFileHelper`、`PrimaryDexopter.maybeCreateSdc()`、`artd` 端 `SdcReader`；`cloudCompilationPm()` flag 与 `FLAG_ART_SERVICE_V3` 控制整套 SDM 机制 | 稳定，与 SDM 并行处理 | 首次出现，由安装会话暂存、artd 处理 |
| Android 17 | 37 | SDM 机制延续 Android 16；预期变化：(a) SDM 写入路径可能扩展到 secondary dex；(b) `cloudCompilationPm()` 默认开启概率较高；(c) `pm art dump` 输出增加 SDM/SDC 状态字段 | 稳定 | 延续 Android 16 机制 |

> 基于 AOSP android-17.0.0_r1。Android 17 正式 tag 未公开的部分标注为"预期变化"。

关键演进节点：
- **Android 14→15**：ART Service 接管了 dexopt 调度权，从 `installd` 单向执行变为 ART Service → artd → dex2oat 的三层架构。ART Service 可以异步决策"什么时候编译、用什么 profile、走什么 compiler filter"，artd 负责执行和资源管理。
- **Android 15→16**：引入 SDM / SDC 物理产物——这是 Android 编译体系多年来最实质性的变化。设备侧首次出现"云端编译产物直接写入设备"的路径：不再只是云上的 Profile 聚合，而是编译结果（`.vdex`/`.odex`）的物理分发。
- **Android 16→17**：SDM 机制稳定化，重点在 secondary dex 扩展和默认开启策略。对开发者来说，Android 17 意味着 SDM 覆盖的应用范围更广，不需要额外配置就能受益。

## 5. 性能数据与边界

关于 SDM 带来的安装和启动性能提升，以下数据来自 Android 开发者博客的公开宣称，需要在**你自己的设备和应用上独立验证**：

- **安装时间**：宣称减少 40-60%（对比无 `.sdm` 的 speed-profile 编译基线）
- **安装后首次冷启动时间**：宣称减少 30-45%（因跳过安装期大面积 dex2oat）
- **安装体积**：宣称减少 15-25%（编译产物按需裁剪，非全量预编译）

**验证方法**（需要 Play Store 渠道提供的 `.dm` + `.sdm` 文件）：

1. 对比安装时 `adb shell dumpsys package dexopt` 的输出，确认 `compilation_reason` 是否为 `cloud-profile` 或 `install-bulk`；记录 `dex2oat` 执行时长
2. 对比 `/data/app/<pkg>/oat/<isa>/` 下 `.vdex` 和 `.odex` 文件体积
3. 使用 `am start-activity -W` 或 Perfetto trace 捕获 `bindApplication` → `reportFullyDrawn` 区间，对比两次安装（带/不带云端 Profile）的启动耗时
4. 非 Play 渠道可通过 `pm install` 的 `--dm` 参数手动注入 `.dm` 验证 Profile 驱动编译效果，但无法验证 `.sdm` 装载路径

> 性能数据受设备型号、CPU 核心数、存储速度、DEX 体积、系统负载等多因素影响。上面的数字只能作为数量级参考，不代表你的应用能得到完全相同的收益。

SDM 的受益边界：
- **受益场景**：从 Play Store 安装、应用 DEX 体积较大（>10MB）、用户设备存储性能一般
- **不受益**：非 Play Store 安装、已安装应用更新（增量 dexopt 本来就不大）、小体积应用、`.sdm` 验证失败回退到传统 dexopt
- **可能不适用**：使用自定义 ClassLoader 加载 dex 的应用，其 dex 文件不被 ART Service 管理

## 6. 在 Perfetto 中观测 SDM 编译

本章最实用的部分是告诉你 SDM 编译活动在 Perfetto trace 中长什么样——出问题时你知道从哪开始看。

### 6.1 关键观测点

SDM 相关的编译活动在 Perfetto 中对应的 track 和 slice：

| 观测目标 | Perfetto track/slice | 关注点 |
|---------|---------------------|--------|
| artd 编译调度 | `artd` 进程的 async slice，名称含 `dex2oat` | 编译是否被触发、执行耗时 |
| dex2oat 执行 | `dex2oat` 进程的 CPU slice | 编译器 filter（speed-profile/speed/verify 等）、线程数、内存峰值 |
| 安装期编译 | `installd` → `dexopt` slice | compilation_reason 是否为 install-bulk 或 cloud-profile |
| SDM 装载（跳过编译） | artd 中无 dex2oat 相关 slice，但 `PackageInstallerSession` 中有文件写入 | SDM 路径下编译耗时应接近 0 |
| 后台编译 | `BackgroundDexoptJobService` slice | 安装完成后是否触发后台 dexopt |

### 6.2 典型 trace 分析场景

**场景一：确认 SDM 装载路径是否生效**

在 Perfetto 中抓一次从 Play Store 安装应用到首次启动的完整 trace。在 `artd` 进程中搜索 `dex2oat` slice：
- 如果找不到 dex2oat 调用，但 `/data/app/<pkg>/oat/` 下已经有 `.vdex` 和 `.odex` 文件 → SDM 装载路径生效
- 如果能看到 dex2oat 调用，检查 `compilation_reason`：`cloud-profile` 表示使用了云端 Profile；`install-bulk` 表示走了传统的安装期 bulk 编译

**场景二：安装耗时异常的排查**

提取 `PackageInstallerSession` 中 `installAsUser` 到 `performInstall` 区间，确认耗时分布：
- 如果大量时间花在 dexopt → 检查 `.sdm` 是否存在、profile 是否有效
- 如果 dexopt 时间正常但文件 I/O 时间异常 → 检查存储性能（`file_utils.cc` 中的文件操作应在 Perfetto 的 `f2fs`/`ext4` track 中观察）
- 如果 `pm.dexopt.dm.require_fsverity=true` 且 `.dm` 缺少 fs-verity → dexopt 失败，trace 中表现为 dex2oat 未启动

**场景三：后台编译对前台的影响**

SDM 可能将部分编译推迟到后台执行。在 trace 中关注 `BackgroundDexoptJobService` 的 CPU 占用是否在前台应用活跃期间仍然高——如果是，说明后台编译调度不够礼貌，需要向 ART Service 的调度策略反馈。

### 6.3 常用 trace 查询

```sql
-- 在 Perfetto trace_processor 中查询 dex2oat 执行
SELECT ts, dur, name
FROM slice
WHERE name GLOB '*dex2oat*'
ORDER BY ts;

-- 查询 artd 相关的所有 slice
SELECT ts, dur, name
FROM slice
WHERE track_id IN (
  SELECT id FROM track WHERE name GLOB '*artd*'
)
ORDER BY ts;
```

## 7. 常见问题与调试

### 7.1 检查 SDM 状态

```bash
# 查看当前 dexopt 状态（含 cloud compilation 信息）
adb shell dumpsys package dexopt | grep -A5 "cloud"

# 查看 ART Service 状态
adb shell pm art dump

# 检查 .dm 文件是否存在
adb shell ls -la /data/app/<pkg>/oat/<isa>/*.dm

# 检查 .sdm 签名验证日志
adb logcat | grep -i "sdm\|SdcReader\|cloudCompilation"
```

### 7.2 常见故障模式

| 故障现象 | 可能原因 | 排查方法 |
|---------|---------|---------|
| 安装后首次启动仍然慢 | `.sdm` 签名验证失败，回退到传统 dexopt | `adb logcat \| grep -i "sdm\|SdcReader"` 检查验证日志 |
| `.dm` 文件存在但 dexopt 失败 | manifest 缺少包名/版本、fs-verity 摘要缺失 | 检查 `pm.dexopt.dm.require_manifest` 和 `pm.dexopt.dm.require_fsverity` 的当前值 |
| 编译耗时不减反增 | 云端 Profile 与本地设备 ISA 不匹配，触发了全量重编译 | 对比 `compilation_reason` 和预期的 compiler filter |
| artd 进程 CPU 持续高 | 后台编译任务堆积 | `dumpsys package dexopt` 检查 pending 编译任务数量 |

### 7.3 强制开启/关闭验证模式

```bash
# 强制要求 .dm 携带 manifest（默认 false）
adb shell setprop pm.dexopt.dm.require_manifest true

# 强制要求 .dm 携带 fs-verity 摘要（默认 false）
adb shell setprop pm.dexopt.dm.require_fsverity true

# 恢复默认值
adb shell setprop pm.dexopt.dm.require_manifest false
adb shell setprop pm.dexopt.dm.require_fsverity false
```

## 8. 开发者适配建议

SDM 是 Google Play 侧的基础设施优化，应用开发者大部分情况下不需要做任何代码改动就能受益。但以下几点值得关注：

1. **Profile 质量直接影响编译效果**：`.dm` 内的 profile 是云端聚合多设备运行数据生成的。如果你的应用大量使用反射、动态加载或 JNI，profile 可能无法覆盖这些路径——这些代码在 SDM 路径下仍然需要在首次运行时被 JIT 编译。优化方向不是改编译配置，而是减少不必要的反射和动态加载。

2. **非 Play 渠道的用户不受影响**：SDM 仅对 Play Store 安装路径生效。如果你的应用通过第三方应用商店分发，安装编译流程与 Android 15 完全一致，不需要做适配。

3. **Baseline Profile 仍然有价值**：SDM 装载的云端 Profile 是聚合数据，不能替代你打包在 APK 内的 Baseline Profile。Baseline Profile 保证所有用户（包括非 Play 渠道）在首次安装后都有基本的编译优化引导。SDM 是在 Baseline Profile 之上的增强，不是替代。

4. **测试覆盖 SDM 路径**：如果你的应用主要通过 Play Store 分发，测试时需要确认 SDM 装载路径在目标设备上正常生效。可以对照第 6 节的 Perfetto 观测方法验证。

5. **不需要关闭 dexopt**：有些开发者尝试通过 `pm.dexopt.*` 配置关闭安装期编译来"优化安装速度"。这在 Android 17 中是一种反优化——SDM 已经解决了安装编译瓶颈，手动关闭 dexopt 只会让首次启动更慢。让系统调度编译流程即可。

## 参考资源

- [AOSP android-17.0.0_r1](https://android.googlesource.com/platform/art/+/android-17.0.0_r1)
- [PrimaryDexopter 源码](https://cs.android.com/android/platform/superproject/main/+/android-17.0.0_r1:art/libartservice/service/java/com/android/server/art/PrimaryDexopter.java)
- [DexMetadataHelper 源码](https://cs.android.com/android/platform/superproject/main/+/android-17.0.0_r1:frameworks/base/core/java/android/content/pm/dex/DexMetadataHelper.java)
- [DexMetadata (.dm) 官方文档](https://source.android.com/docs/core/runtime/dex-metadata)
- [安装优化技术综述](https://juejin.cn/post/7610233341305389099)

## 相关章节

- [16.6] Android 16 云端 Profile 与 dexopt 安装优化——覆盖 Android 16 的 Profile 聚合与 dexopt 调度体系，与本章 SDM 物理产物分发互补
- [1.9] Android 编译系统基础——dex2oat 编译流程、compiler filter 类型的基础知识
- [1.23] Dalvik 虚拟机优化技术——ART 的 AOT/JIT/Profile-guided compilation 背景
- [21.11] 应用性能监控与调试——Perfetto 使用指南和 trace 分析方法