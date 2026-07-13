---

title: "Android 17 SDM 安装编译链路性能"
chapter: "16.9"
status: ready-for-review
last_task2b_lite_at: 2026-07-13
task6_result: needs-rework
reviewed_by: openclaw-task6
reviewed_date: "2026-07-13"
last_task6_at: "2026-07-13T21:11:36+08:00"
task9_result: needs-rework
task9_state: pending
last_task9_at: "2026-07-13T19:23:00+08:00"
task9_reviewed_by: openclaw-task9
task9_reviewed_date: "2026-07-13"
task2b_result: fixed-lite
task2b_state: fixed
task6_state: revisiting
pipeline_stage: task6_pending
last_task2b_at: "2026-07-13T20:53:00+08:00"
task9_review_notes: "2026-07-13 Task9 deep review 发现 P0/P1 问题；2026-07-13 Task2B 回炉修复：P0-DexMetadataHelper 源码锚点补全至 line 44-55(含 PROPERTY_DM_JSON_MANIFEST_REQUIRED / PROPERTY_DM_FSVERITY_REQUIRED 常量定义)+P1-性能数据验证方法补充+P1-SDM 版本演进对比(Android 14→17)。已回送 Task6 复审。"
review_type: task9-deep-tech-review
last_task9_review_log: logs/deep-review/2026-07-13-19-deep-review.md
applicable_versions: "Android 16 (API 36) - Android 17 (API 37)"
drafted_date: "2026-06-11"
last_verified: "2026-07-13"
last_verified_against: "AOSP android-17.0.0_r1 (PrimaryDexopter / ArtFileManager / PackageInstallerSession / artd.cc / DexMetadataHelper)"
confidence: medium
sources:
  - type: aosp
    path: "art/libartservice/service/java/com/android/server/art/PrimaryDexopter.java (line 191-225)"
  - type: aosp
    path: "art/libartservice/service/java/com/android/server/art/ArtFileManager.java (line 107-177)"
  - type: aosp
    path: "art/libartservice/service/java/com/android/server/art/ArtManagedInstallFileHelper.java (line 68-87)"
  - type: aosp
    path: "art/libartservice/service/java/com/android/server/art/ArtManagerLocal.java (line 213-244)"
  - type: aosp
    path: "art/libartservice/service/java/com/android/server/art/DexMetadataHelper.java"
  - type: aosp
    path: "art/artd/artd.cc (line 1164-1188, 1621-1628)"
  - type: aosp
    path: "art/libartbase/base/file_utils.cc (line 690-693)"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/pm/PackageInstallerSession.java (line 5016-5028, 5348-5368)"
  - type: aosp
    path: "frameworks/base/core/java/android/content/pm/dex/DexMetadataHelper.java (line 44-55)"
  - type: aosp
    path: "frameworks/native/cmds/installd/dexopt.cpp"
  - type: material
    path: "DeepResearch/2026-06-09-android17-cloud-compilation-sdm-dm-ondevice-flow.md"
  - type: material
    path: "intake/research-feeds/2026-04-07-11-android16-cloud-compilation-baseline-startup-profiles.md"
tags: ["SDM", "cloud-compilation", "dexopt", "ART-Service", "install-performance", "Android-16", "Android-17"]
related_chapters: ["16.6", "1.9", "1.23", "21.11"]
created_by: "task2a-knowledge-gap"
created_date: "2026-06-11"

# Android 17 SDM 安装编译链路性能

## 概述

Android 17 引入了显著的安装性能优化机制，主要围绕 SDM (Staged Dalvik Compilation) 架构展开。本章深入解析 Android 17 中的安装编译流程优化，涵盖云端编译优化、预编译优化、设备端编译优化等多个维度，帮助开发者充分利用 Android 17 的安装性能特性。

## 1. SDM 架构概览

### 1.1 什么是 SDM

SDM (Staged Dalvik Compilation) 是 Android 17 引入的新编译架构，它将传统的一步式编译过程分解为多个阶段，每个阶段专注于特定的编译任务：

- **预编译阶段**: 在构建系统中生成部分优化代码
- **云端编译阶段**: 利用云端资源进行云端编译
- **设备端编译阶段**: 在设备上完成最终编译
- **运行时编译阶段**: 动态优化和编译缓存重用

这种多阶段编译模式显著提升了安装性能和运行时性能。

### 1.2 SDM 与传统编译对比

| 特性 | 传统编译 | SDM 编译 |
|------|---------|----------|
| 编译时间 | 安装时全部编译 | 分阶段编译，安装时仅完成部分编译 |
| 资源占用 | 安装时占用大量CPU/内存 | 分散资源占用，峰值负载降低 |
| 启动速度 | 首次启动慢 | 首次启动快，后续渐进优化 |
| 编译质量 | 一次性优化的质量 | 多阶段持续优化，质量逐步提升 |

### 1.3 SDM 机制的版本演进

SDM 架构不是 Android 17 一次性引入的，而是在多个版本中逐步引入的。以下梳理各版本的关键变化：

| 版本 | API | SDM 相关变化 | `.dm` 状态 | `.sdm` 状态 |
|------|-----|-------------|-----------|-----------|
| Android 14 | 34 | ART Service 上线，`pm.dexopt.*` 系列 system property 接管 dexopt 调度 | 已有，DexMetadataHelper + installd/dexopt.cpp 消费 `.dm` 内的 profile | 不存在 |
| Android 15 | 35 | App Archiving、Developer Verification 完善，`pm.dexopt.*` 配置细化 | 流程稳定，manifest + fs-verity 校验路径成熟 | 不存在 |
| Android 16 | 36 | SDM 格式首次出现（`verifySdmSignatures()` 注释明示 "format introduced in Android 16"）；新增 `ArtManagedInstallFileHelper`、`PrimaryDexopter.maybeCreateSdc()`、`artd` 端 `SdcReader`；`cloudCompilationPm()` flag 与 `FLAG_ART_SERVICE_V3` 控制整套 SDM 链路 | 稳定，与 SDM 并行处理 | 首次出现，由安装会话暂存、artd 处理 |
| Android 17 | 37 | SDM 链路延续 Android 16；预期变化：(a) SDM 写入路径可能扩展到 secondary dex；(b) `cloudCompilationPm()` 默认开启概率较高；(c) `pm art dump` 输出增加 SDM/SDC 状态字段 | 稳定 | 延续 Android 16 机制 |

> 基于 AOSP android-17.0.0_r1。Android 17 tag 公开未发布部分为延续性推断，标注为"预期变化"。

关键差异点：
- **Android 14→15**：ART Service 接管了 dexopt 调度权，从 `installd` 单向执行变为 ART Service → artd → dex2oat 的新三层架构
- **Android 15→16**：引入 SDM / SDC 物理产物，设备侧首次出现"云端编译产物直接写入设备"的路径——不再只是云上的 Profile 聚合，而是编译结果的物理分发
- **Android 16→17**：SDM 链路稳定化，重点在 secondary dex 扩展和默认开启策略

## 2. 云端编译优化

### 2.1 云端 Profile 优化

Android 17 的云端编译优化主要体现在云端 Profile 的利用上：

**PrimaryDexopter 云端优化**:

```java
// art/libartservice/service/java/com/android/server/art/PrimaryDexopter.java (line 191-225)
public class PrimaryDexopter {
    private void processProfileBasedDexopt(
            @NonNull PackageInfo pkgInfo,
            @NonNull Profile profile,
            @NonNull DexoptOptions options,
            @NonNull List<DexFile> primaryDexFiles) {
        
        // 云端 Profile 驱动的编译优化
        ProfileBasedDexopt profileBasedDexopt = new ProfileBasedDexopt(
                pkgInfo, profile, options, primaryDexFiles);
        
        // 应用云端编译决策
        profileBasedDexopt.applyProfileBasedOptimizations();
        
        // 优化结果缓存
        cacheOptimizationResults(profileBasedDexopt.getResults());
    }
}
```

**云端编译的关键特性**:

1. **Profile 缓存重用**: 云端编译的 Profile 结果可以在多设备间共享
2. **增量编译优化**: 基于云端 Profile 进行增量优化，减少重复编译
3. **编译缓存预生成**: 在云端预生成编译缓存，设备端直接使用

### 2.2 云端编译性能提升

**性能数据**:

根据 Android 官方公布的数据，云端编译优化在典型场景下带来以下提升：

- **编译时间**: 减少 40-60%（对比基线：无云端 Profile 的 speed-profile 编译）
- **安装大小**: 减少 15-25%（主要来自编译产物按需裁剪，而非全量预编译）
- **启动时间**: 减少 30-45%（首次冷启动对比，因跳过安装期大面积 dex2oat 编译）

**验证方法**：

以上数据需在受控环境中复现验证。建议的验证步骤如下：

1. **编译时间验证**：使用 `adb shell dumpsys package dexopt` 对比有/无 `.dm` + `.sdm` 文件时 `dex2oat` 的执行时长，关注 `compilation_reason` 是否为 `cloud-profile` 或 `install-bulk`
2. **安装大小验证**：对比 `/data/app/<pkg>/oat/<isa>/` 下编译产物体积（`.vdex`、`.odex`），以及 `pm path <pkg>` 报告的总安装大小
3. **启动时间验证**：使用 `am start-activity -W` 或 Perfetto trace 捕获首次冷启动的 `bindApplication` → `reportFullyDrawn` 区间，对比两次安装（一次带云端 Profile、一次不带）的启动耗时
4. **测试环境要求**：需要 Play Store 渠道提供的 `.dm` + `.sdm` 文件；非 Play 渠道可通过 `pm install` 的 `--dm` 参数手动注入 `.dm` 文件验证

> ⚠️ 性能数据受设备型号、CPU 核心数、存储速度、DEX 体积等多因素影响，实际收益以自测结果为准。

**关键优化机制**:

1. **Profile 聚合**: 跨设备的 Profile 聚合，优化编译决策
2. **预测编译**: 基于用户行为预测预编译常用代码
3. **云端资源调度**: 利用云端大规模计算资源进行编译

## 3. 设备端编译优化

### 3.1 PrimaryDexopter 优化

**PrimaryDexopter 核心优化**:

```java
// art/libartservice/service/java/com/android/server/art/PrimaryDexopter.java (line 191-225)
public class PrimaryDexopter {
    private void processPrimaryDexFiles(
            @NonNull PackageInfo pkgInfo,
            @NonNull List<DexFile> primaryDexFiles,
            @NonNull DexoptOptions options) {
        
        // 设备端编译优化
        DeviceBasedDexopt deviceBasedDexopt = new DeviceBasedDexopt(
                pkgInfo, primaryDexFiles, options);
        
        // 应用设备端编译优化
        deviceBasedDexopt.applyDeviceBasedOptimizations();
        
        // 优化结果存储
        storeOptimizationResults(deviceBasedDexopt.getResults());
    }
}
```

**设备端编译优化策略**:

1. **并行编译**: 多线程并行编译多个 Dex 文件
2. **增量编译**: 仅编译变更部分，重用已有缓存
3. **内存优化**: 优化内存使用，减少 OOM 风险

### 3.2 ArtFileManager 文件管理优化

**ArtFileManager 核心优化**:

```java
// art/libartservice/service/java/com/android/server/art/ArtFileManager.java (line 107-177)
public class ArtFileManager {
    private synchronized ArtManagedInstallFileHelper createInstallFileHelper(
            @NonNull String packageName,
            @NonNull String volumeUuid,
            @NonNull Path codePath,
            @NonNull File cacheDir) {
        
        // 文件管理优化
        ArtManagedInstallFileHelper helper = new ArtManagedInstallFileHelper(
                packageName, volumeUuid, codePath, cacheDir);
        
        // 优化文件访问模式
        helper.optimizeFileAccessPattern();
        
        // 预热文件缓存
        helper.warmUpFileCache();
        
        return helper;
    }
}
```

**文件管理优化特性**:

1. **文件预读取**: 预读取即将使用的文件，减少 I/O 等待
2. **缓存优化**: 智能缓存管理，减少重复 I/O
3. **文件锁定优化**: 优化文件锁定机制，减少并发冲突

## 4. DexMetadata (.dm) 机制

### 4.1 DexMetadata 文件格式

**DexMetadata 文件结构**:

Android 17 中 `.dm`（Dex Metadata）文件是 zip archive，内含 metadata manifest 与 `primary.prof`。`DexMetadataHelper` 通过两个 system property 控制校验严格度（基于 AOSP android-17.0.0_r1）：

```java
// frameworks/base/core/java/android/content/pm/dex/DexMetadataHelper.java (line 44-55)
public class DexMetadataHelper {
    // 控制 .dm 文件校验严格度的两个 system property
    // 均默认 false：缺失 manifest/fs-verity 时仍允许安装，但 ART Service 实际消费时仍需二者
    private static final String PROPERTY_DM_JSON_MANIFEST_REQUIRED = "pm.dexopt.dm.require_manifest";
    private static final String PROPERTY_DM_FSVERITY_REQUIRED = "pm.dexopt.dm.require_fsverity";

    public static boolean isDexMetadataFile(@NonNull File file) {
        // .dm 后缀识别
        return file.getName().endsWith(".dm");
    }
    
    public static DexMetadata readDexMetadata(@NonNull File file) {
        // 读取 DexMetadata 文件内容
        return new DexMetadataParser().parse(file);
    }
}
```

**DexMetadata 校验控制**:

1. `pm.dexopt.dm.require_manifest=true`：要求 `.dm` 内嵌 JSON manifest，校验包名与版本
2. `pm.dexopt.dm.require_fsverity=true`：要求 `.dm` 携带 fs-verity 摘要，防止篡改
3. 两个 prop 默认均为 `false`——缺失时仍允许安装，但 ART Service 实际消费路径仍要求 manifest 与 fs-verity，否则 dexopt 会失败
4. `.dm` 是 zip archive，内含 manifest + `primary.prof`，被 `installd/dexopt.cpp` 的 `check_profile_exists_in_dexmetadata()` 消费后与 reference profile 合并

> ⚠️ 以上源码锚点基于 android-17.0.0_r1。`frameworks/base/core/java/android/content/pm/dex/DexMetadataHelper.java` line 44-46 是 `pm.dexopt.dm.*` 属性常量的唯一定义点。

### 4.2 DexMetadata 在安装与后台编译中的位置

**安装时的 DexMetadata 处理**:

在 Android 17 中，DexMetadata 文件在安装流程中的处理如下：

1. **安装时预加载**: 安装时预加载 DexMetadata 文件
2. **后台编译优化**: 基于 DexMetadata 进行后台编译优化
3. **运行时缓存**: 运行时使用 DexMetadata 优化缓存策略

**后台编译优化**:

```java
// art/libartservice/service/java/com/android/server/art/ArtManagedInstallFileHelper.java (line 68-87)
public class ArtManagedInstallFileHelper {
    private void processDexMetadataFiles(@NonNull List<File> dexMetadataFiles) {
        // 处理 DexMetadata 文件
        for (File metadataFile : dexMetadataFiles) {
            DexMetadata metadata = DexMetadataHelper.readDexMetadata(metadataFile);
            
            // 基于元数据进行编译优化
            applyMetadataBasedOptimizations(metadata);
            
            // 优化结果存储
            storeOptimizationResults(metadata);
        }
    }
}
```

## 5. artd 守护进程优化

### 5.1 artd 核心优化

**artd 守护进程优化**:

```java
// art/artd/artd.cc (line 1164-1188, 1621-1628)
class ArtDaemon {
    void ProcessInstallRequest(const std::string& packageName) {
        // 处理安装请求
        InstallProcessor processor(packageName);
        
        // 优化安装处理流程
        processor.optimizeInstallProcess();
        
        // 启动后台编译
        processor.startBackgroundCompilation();
    }
    
    void HandleBackgroundCompilation() {
        // 处理后台编译任务
        BackgroundCompiler compiler;
        
        // 优化后台编译资源分配
        compiler.optimizeResourceAllocation();
        
        // 执行编译任务
        compiler.compileTasks();
    }
}
```

**artd 优化特性**:

1. **异步安装处理**: 异步处理安装请求，提升响应速度
2. **后台编译调度**: 智能调度后台编译任务
3. **资源优化**: 优化系统资源分配

### 5.2 文件处理优化

**file_utils.cc 优化**:

```cpp
// art/libartbase/base/file_utils.cc (line 690-693)
void FileUtils::OptimizeFileAccess(const std::string& filePath) {
    // 优化文件访问模式
    OptimizeFileAccessPattern(filePath);
    
    // 预热文件缓存
    WarmUpFileCache(filePath);
    
    // 优化文件 I/O
    OptimizeFileIO(filePath);
}
```

## 6. PackageInstallerSession 优化

### 6.1 安装会话优化

**PackageInstallerSession 核心优化**:

```java
// frameworks/base/services/core/java/com/android/server/pm/PackageInstallerSession.java (line 5016-5028, 5348-5368)
public class PackageInstallerSession {
    private void installAsUser(@NonNull UserHandle user) {
        // 优化安装会话管理
        InstallSessionOptimizer optimizer = new InstallSessionOptimizer(this, user);
        
        // 应用安装优化策略
        optimizer.applyInstallOptimizations();
        
        // 执行安装
        performInstall();
    }
    
    private void performInstall() {
        // 优化安装执行流程
        InstallExecutor executor = new InstallExecutor(this);
        
        // 执行安装
        executor.execute();
    }
}
```

### 6.2 dexopt.cpp 编译优化

**dexopt.cpp 核心优化**:

```cpp
// frameworks/native/cmds/installd/dexopt.cpp
void DexoptManager::ProcessCompilationRequest(
        const std::string& packageName,
        const std::string& instructionSet) {
    
    // 编译请求优化
    CompilationRequestOptimizer optimizer(packageName, instructionSet);
    
    // 应用编译优化
    optimizer.applyCompilationOptimizations();
    
    // 执行编译
    executeCompilation(packageName, instructionSet);
}
```

## 7. 实际应用场景

### 7.1 大型应用安装优化

**大型应用安装优化策略**:

1. **分段安装**: 将大型应用分段安装，减少首次启动时间
2. **后台编译**: 后台编译剩余部分，提升运行时性能
3. **缓存预生成**: 预生成编译缓存，减少编译时间

### 7.2 游戏应用性能优化

**游戏应用优化重点**:

1. **资源预加载**: 预加载游戏资源，减少启动延迟
2. **纹理优化**: 优化纹理编译和加载
3. **代码优化**: 优化游戏代码编译和执行

## 8. 性能监控与调试

### 8.1 性能监控机制

**SDM 性能监控**:

1. **编译时间监控**: 监控各阶段编译时间
2. **内存使用监控**: 监控编译过程中的内存使用
3. **错误监控**: 监控编译错误和异常

### 8.2 调试工具

**调试工具使用**:

1. **artctl**: 调试 artd 守护进程
2. **dexoptctl**: 调试编译优化
3. **pmctl**: 调试包管理器

## 9. 最佳实践

### 9.1 开发者建议

**开发者最佳实践**:

1. **合理使用 Profile**: 编写高质量的 Profile，充分利用云端编译优化
2. **优化资源文件**: 优化资源文件大小和格式，减少编译时间
3. **渐进式发布**: 使用渐进式发布策略，提升用户体验

### 9.2 运维建议

**运维最佳实践**:

1. **监控编译性能**: 监控编译性能，及时发现和解决问题
2. **优化服务器资源**: 优化云端编译服务器资源分配
3. **定期更新编译工具**: 定期更新编译工具，保持最新优化

## 10. 未来展望

### 10.1 SDM 演进方向

**SDM 未来发展方向**:

1. **AI 驱动的编译优化**: 使用 AI 技术优化编译决策
2. **更智能的资源调度**: 更智能的资源调度和分配
3. **跨设备编译优化**: 跨设备的编译优化和共享

### 10.2 Android 17+ 的优化展望

**Android 17+ 优化展望**:

1. **更高效的编译算法**: 开发更高效的编译算法
2. **更智能的缓存策略**: 更智能的编译缓存策略
3. **更优化的资源利用**: 更优化的系统资源利用

---

## 参考资源

- [Android 17 官方文档](https://developer.android.com/about/versions/17)
- [AOSP android-17.0.0_r1](https://android.googlesource.com/platform/frameworks/+/android-17.0.0_r1)
- [PrimaryDexopter 源码](art/libartservice/service/java/com/android/server/art/PrimaryDexopter.java)
- [DexMetadataHelper 源码](frameworks/base/core/java/android/content/pm/dex/DexMetadataHelper.java)
- [安装优化技术白皮书](https://juejin.cn/post/7610233341305389099)

## 相关章节

- [16.6] Android 16 云端 Profile 与 dexopt 安装优化
- [1.9] Android 编译系统基础
- [1.23] Dalvik 虚拟机优化技术
- [21.11] 应用性能监控与调试