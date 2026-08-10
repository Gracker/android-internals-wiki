---
title: "ART Boot Image 内存映射与启动性能"
chapter: "1.57"
status: "ready-for-review"
drafted_date: "2026-07-15"
applicable_versions: "Android 12 (API 31) - Android 17 (API 37)"
last_verified: "2026-07-25"
last_verified_against: "AOSP android-17.0.0_r1"
confidence: high
sources:
  - type: aosp
    path: "art/runtime/oat/image.h, art/runtime/oat/image.cc @ android-17.0.0_r1"
  - type: aosp
    path: "art/runtime/gc/space/image_space.h, art/runtime/gc/space/image_space.cc @ android-17.0.0_r1"
  - type: aosp
    path: "art/libartbase/base/file_utils.cc @ android-17.0.0_r1"
  - type: aosp
    path: "art/dex2oat/dex2oat.cc, art/dex2oat/linker/image_writer.cc @ android-17.0.0_r1"
  - type: aosp
    path: "art/odrefresh/odrefresh.cc @ android-17.0.0_r1"
  - type: aosp
    path: "art/profman/boot_image_profile.cc @ android-17.0.0_r1"
  - type: aosp
    path: "frameworks/base/core/java/com/android/internal/os/ZygoteInit.java @ android-17.0.0_r1"
  - type: aosp
    path: "frameworks/base/config/preloaded-classes @ android-17.0.0_r1"
  - type: kernel
    path: "common/mm/memory.c @ android17-6.18-2026-06_r6"
  - type: official
    path: "https://source.android.com/docs/core/runtime/boot-image-profiles"
  - type: official
    path: "https://source.android.com/docs/security/features/verifiedboot/on-device-signing-architecture"
  - type: official
    path: "https://developer.android.com/topic/performance/startupprofiles/dex-layout-optimizations"
tags: [ART, boot-image, boot.art, boot.oat, 内存映射, Zygote, 启动优化, mmap, dex2oat, ImageSpace]
related_chapters: ["1.7", "1.11", "1.12", "4.3", "8.2"]
created_by: "task2a-knowledge-gap"
created_date: "2026-07-15"
gap_source: "章节深挖"
---

# 1.57 ART Boot Image 内存映射与启动性能

Boot Image 处在 ART 启动、系统镜像预编译和 Zygote 共享内存的交点。排查开机变慢、Zygote 私有脏页增长或 ART Mainline 更新后的编译行为时，需要分别观察镜像文件、编译 profile 和 Zygote 预加载。

平台行为以 Android 17 / API 37 / `android-17.0.0_r1` 为准；涉及 `MAP_PRIVATE` 与写时复制的内核行为以 `android17-6.18-2026-06_r6` 为准。

## Boot Image 保存了什么

ART Boot Image 是 `dex2oat` 生成的可加载运行时快照。它保存选入镜像的 Java 对象、类元数据和 ART 原生元数据，并与相应的 AOT 代码一起使用。运行时可以直接恢复这批对象和元数据，省去重复分配、链接及一部分初始化工作。

这项机制有两个边界：

- Boot Image 不等于整个 Boot Class Path。哪些类进入 `.art` 镜像、哪些方法获得 AOT 代码，受 Boot Image Profile、编译过滤器和构建配置共同影响。
- Boot Image 不等于 Zygote 完成 `preload()` 后的完整堆。Zygote 还会加载类、资源、共享库和图形驱动；这些操作产生的对象位于其他堆空间。

### `.art`、`.oat`、`.vdex` 的职责

一个 Boot Image 组件通常对应三类产物：

| 产物 | 主要内容 | 运行时用途 |
| --- | --- | --- |
| `.art` | `ImageHeader`、镜像对象、`ArtField`、`ArtMethod`、类表、字符串表、位图等 | 建立 `ImageSpace`，恢复预先构造的对象和 ART 元数据 |
| `.oat` | OAT 头、编译代码、运行时所需元数据 | 提供 AOT 代码和镜像依赖信息 |
| `.vdex` | DEX 与验证相关数据；是否携带 DEX section 取决于产物模式 | 配合 OAT 打开 DEX，复用验证结果 |

“三个固定文件”只适合解释最小模型。Android 17 默认使用多组件能力：一个主镜像可以覆盖多个 Boot Class Path 组件，也可以接若干 Boot Image Extension。多镜像构建时会出现 `boot.art`、`boot-framework-*.art` 等文件，并各有对应的 `.oat`、`.vdex`。

`services.jar` 属于 System Server Class Path，不应当为了说明 Boot Image 而写进 Boot Class Path 清单。`odrefresh` 对 Boot Class Path 和 System Server Class Path 使用两套检查与编译流程。

## Android 17 的产物位置由运行时选择

源码中的镜像位置（image location）是一条组件描述，运行时还要把它展开成当前指令集的文件路径。以 `/system/framework/boot.art` 为例，`GetSystemImageFilename()` 会定位到类似 `/system/framework/arm64/boot.art` 的实际文件。

`GetDefaultBootImageLocationSafe()` 在 Android 17 上按以下次序选择默认镜像：

1. `odsign.verification.success` 为 `true`，且 `/data/misc/apexdata/com.android.art/dalvik-cache` 中存在完整主镜像时，优先使用这里的 `boot.art`。这类产物由 `odrefresh` 生成并由 `odsign` 校验。
2. 完整镜像生成失败但最小镜像可用时，可以使用 `boot_minimal.art`。最小镜像只覆盖 ART 模块内的 Boot Class Path JAR，后续组件按配置处理。
3. 没有可用的 `/data` 产物时，使用系统分区预编译镜像。Android 17 源码注释给出的主位置是 `/system/framework/boot.art`，实际文件仍带指令集子目录。
4. Mainline Boot Class Path JAR 可以拥有单独的 Boot Image Extension，运行时把它附加到主镜像描述中。

ART 已经模块化，并不表示 `boot.art` 一定位于 `/apex/com.android.art`。ART APEX 提供运行时、profile 和工具；当前进程使用的镜像可能来自 `/system`，也可能来自 ART APEX 的 `/data` 目录。

`GetBootImageLocationForDefaultBcpRespectingSysProps()` 会在 `odsign.verification.success` 不为 `true` 时设置 `deny_art_apex_data_files`。即使 `/data` 中残留同名文件，运行时也不会仅凭路径存在就采用它；设备取证应把 `odsign` 验证结果与进程 `maps` 一起检查。

## `dex2oat` 生成 Boot Image 的方式

### 主镜像与扩展镜像

`dex2oat` 根据参数区分三种 image：

- 传入 `--image` 且没有 `--boot-image`：生成主 Boot Image。
- 同时传入输出 image 和已有 `--boot-image`：生成 Boot Image Extension。
- 传入 `--app-image-file` 或 `--app-image-fd`：生成 App Image。

Android 17 的 AOT 编译统一使用位置无关代码，`Dex2Oat::ProcessOptions()` 直接设置 `compile_pic_ = true`。“Boot Image 依赖位置相关机器码，地址稍变就无法运行”不符合当前实现。

### profile 对类和方法的选择不同

Boot Image Profile 同时携带类和方法信息：

- 类条目参与决定哪些类进入 `.art` 镜像。
- 方法的热（hot）、启动（startup）等标记参与 `speed-profile` 编译决策。

进入镜像的类不代表其全部方法都被 AOT 编译；获得 AOT 代码的方法也不能简单等同于 `preloaded-classes`。Android 12 起，官方 ART 配置将 Boot Image 编译过滤器固定为 `speed-profile`。Android 17 的 `odrefresh` 也把主镜像和 Mainline 扩展的默认过滤器设为 `speed-profile`；扩展缺少 profile 时会回退到 `verify`。

### `preloaded-classes` 和 `dirty-image-objects`

`odrefresh` 生成主镜像时还会读取：

- `/system/etc/preloaded-classes`：传给 `dex2oat --preloaded-classes-fds`，同时由 Zygote 在 Java 层逐项加载并初始化。
- `/system/etc/dirty-image-objects` 与 ART APEX 内同名文件：给 `ImageWriter` 提供容易被写脏的对象信息，改善对象排布，减少共享页被少量可变对象牵连的概率。

Android 17 AOSP 手机配置中的 `preloaded-classes` 有 18,784 个有效条目。这个数字只描述该 tag 的默认 phone 配置；产品可以替换该文件，后续版本也会变化，不能当作平台契约。

## `.art` 文件结构

Android 17 的定义位于 `art/runtime/oat/image.h`，文件格式实现位于 `art/runtime/oat/image.cc`。旧资料常写成 `runtime/image.h` 或不存在的 `runtime/image_header.cc`，检索源码时要用当前路径。

`ImageHeader` 记录的内容包括：

- 格式 magic 与 version；`android-17.0.0_r1` 中分别为 `art\n` 和 `119`。
- 镜像预留大小、组件数、期望地址、镜像大小与镜像校验和。
- 对应 OAT 的校验和及地址范围。
- 依赖 Boot Image 的起始地址、大小、组件数与组合校验和。
- image roots、指针大小、各 section 的偏移和大小。
- 压缩块信息；镜像可以使用未压缩、LZ4 或 LZ4HC 存储。

Android 17 的 `ImageSections` 顺序如下：

| Section | 内容 |
| --- | --- |
| `kSectionObjects` | Java 镜像对象 |
| `kSectionArtFields` | `ArtField` 数据 |
| `kSectionArtMethods` | `ArtMethod` 数据 |
| `kSectionImTables` | 接口方法表 |
| `kSectionIMTConflictTables` | IMT 冲突表 |
| `kSectionRuntimeMethods` | ART 运行时方法 |
| `kSectionJniStubMethods` | JNI stub 方法 |
| `kSectionInternedStrings` | intern 字符串集合 |
| `kSectionClassTable` | 类表 |
| `kSectionStringReferenceOffsets` | 字符串引用偏移 |
| `kSectionDexCacheArrays` | `DexCache` 数组 |
| `kSectionMetadata` | 镜像附加元数据 |
| `kSectionImageBitmap` | ImageSpace 存活位图 |

`ImageHeader::IsValid()` 检查格式和地址范围。加载器还会检查文件长度、位图位置、组件数、预留大小、OAT 校验和及 Boot Class Path 依赖，不只比较魔数。

## 运行时如何映射和重定位

调用起点在 `Heap` 构造阶段。下面的调用骨架只保留与 Boot Image 加载有关的函数：

```text
Runtime::Init()
  └─ Heap::Heap()
      └─ ImageSpace::LoadBootImage()
          └─ ImageSpace::BootImageLoader::LoadFromSystem()
              ├─ ReserveBootImageMemory()
              ├─ LoadComponents()
              │   ├─ ImageSpace::Loader::Init()
              │   └─ OpenOatFile()
              ├─ MaybeRelocateSpaces()
              └─ DeduplicateInternedStrings()
```

这条调用路径发生在 `ZygoteInit.preload()` 之前。Java 层开始预加载时，Boot Image 对应的 `ImageSpace` 和 OAT 已经加入 ART 堆。

### 预留连续地址并装入组件

`BootImageLoader::LoadImage()` 计算所有组件和 OAT 所需的总预留大小，然后调用 `ReserveBootImageMemory()`。启用 relocation 时，基址由 `ART_BASE_ADDRESS + ChooseRelocationOffsetDelta()` 得出；未启用时使用镜像头中的基址。

地址改变不会直接导致 fatal abort。`MaybeRelocateSpaces()` 计算实际地址与 `ImageHeader::GetImageBegin()` 的差值，再由 `Relocator::RelocateBootImage()` 修正镜像内的对象引用和原生指针。加载器还会为 OAT 初始化运行时 relocation。

预留连续地址仍有价值：多个 image 与 OAT 可以按构建时布局装入同一段低 4 GB 地址空间，引用编码和相邻空间预留也更容易满足。它不等于“所有内部指针都是不可调整的绝对地址”。

### 未压缩镜像与压缩镜像的映射不同

未压缩且允许直接映射时，`LoadImageFile()` 使用：

```cpp
MemMap::MapFileAtAddress(
    address,
    image_size,
    PROT_READ | PROT_WRITE,
    MAP_PRIVATE,
    fd,
    start,
    /* low_4gb= */ true,
    image_filename,
    /* reuse= */ false,
    image_reservation,
    error_msg);
```

这段源码说明 image object 区以私有文件映射装入，初始权限是读写。Android 17 的 `ImageSpace` 加载代码没有在 Zygote `fork` 前统一把整段镜像 `mprotect(PROT_READ)`；把“fork 前统一转为只读”写成固定步骤会误导排查。

压缩镜像需要建立匿名读写映射，再从只读文件映射解压进去。运行时即时编译到 `memfd` 的扩展也可能复制进匿名映射。此时物理页共享特征与直接文件映射不同，诊断时要以 `/proc/<pid>/maps`、`smaps` 中的实际映射为准。

Image bitmap 单独以 `PROT_READ | MAP_PRIVATE` 映射。OAT 则由 `OatFile::Open()` 按文件段及是否允许执行建立映射，不能用一句“整个 `boot.oat` 都是 `PROT_READ|PROT_EXEC`”概括。

## Zygote 共享与写时复制

Boot Image 的内存收益有两层来源：

1. 直接文件映射让多个进程可以引用同一份文件页缓存。
2. Zygote `fork()` 让子进程继承相同页表；匿名页和私有文件页在发生写入前都可以共享。

`MAP_PRIVATE` 表示写入不会回写原文件。Linux 在私有映射的写 fault 上进入写时复制处理；`android17-6.18-2026-06_r6` 的相关实现位于 `mm/memory.c`。页面一旦被某个进程修改，该进程获得私有页，PSS、`Private_Dirty` 和物理内存占用随之变化。

读写权限并不等于页面已经私有化。只有写入落到该页时才会产生私有副本。文件映射也不保证永远保持 `Shared_Clean`：类初始化、锁字、运行时修正或同页其他可变对象都可能写脏页面。`dirty-image-objects` 的排布优化用于减少这种页级放大。

### Zygote 的 `preload()` 是另一层共享

`ZygoteInit.preload()` 的 Android 17 顺序包括：

- `preloadClasses()`：读取 `/system/etc/preloaded-classes`，对每个条目执行 `Class.forName(line, true, null)`，明确要求初始化。
- 缓存非 Boot Class Path 的类加载器。
- 预加载资源、共享库、文本资源、兼容性配置和部分图形相关组件。
- `ZygoteHooks.onEndPreload()` 完成 ART 侧收尾。
- 返回主流程后调用 `gcAndFinalize()`，清理预加载期间产生的临时对象，再开始 fork System Server 和应用进程。

Boot Image 提供构建期生成的对象与元数据；Zygote preload 提供本次开机中的类初始化和额外对象。两者都能减少子进程重复工作，但对象来源、生成时机和调优入口不同。

## 五类 profile 与清单的作用阶段

| 名称 | 作用对象 | 使用阶段 | 是否直接改变 Boot Image |
| --- | --- | --- | --- |
| Boot Image Profile | Boot Class Path 的类和方法 | 系统构建或 `odrefresh` 编译 Boot Image | 是，影响 image class 与 `speed-profile` 方法编译 |
| `preloaded-classes` | Zygote 要加载并初始化的类 | Zygote 启动；也传给 Boot Image 编译器 | 会参与编译约束，但主要职责是 Zygote 预加载 |
| System Server profile | System Server Class Path JAR | 系统构建或 `odrefresh` 编译 System Server 产物 | 不修改主 Boot Image |
| 应用 Baseline Profile | 应用或库的方法与类 | 安装、更新及 ART dexopt | 不修改平台 Boot Image |
| 应用 Startup Profile | 应用启动路径中的类和方法 | R8/D8 构建应用时优化 DEX 布局 | 不修改平台 Boot Image |

应用 Startup Profile 是 Baseline Profile 的启动子集，用来影响 APK/AAB 内 DEX 的排列，让启动代码更集中。它不会生成 `/system/etc/preloaded-classes`，也不会选择平台 `boot.art` 中的类。

Boot Image Profile 与 `preloaded-classes` 可以来自同一批关键用户旅程采样。`profman --generate-boot-image-profile` 也能同时输出 Boot Image Profile 和预加载类清单，但两个输出文件的用途不同。

## ART Mainline 更新与 `odrefresh`

Android 12 起，ART 是可更新的 Mainline 模块。早期启动阶段的 `odsign` 会调用 `odrefresh` 检查运行时产物；Android 17 源码检查的输入包括：

- ART APEX 与其他相关 APEX 的版本信息。
- 影响编译结果的系统属性。
- Boot Class Path JAR 的数量、大小和校验和。
- System Server Class Path JAR 的数量、大小和校验和。
- 已生成产物及 `cache-info.xml` 的一致性。

检查失败时，`odrefresh` 可以重新生成主 Boot Image、Mainline Extension 和需要更新的 System Server 产物，默认输出目录是 `/data/misc/apexdata/com.android.art/dalvik-cache`。完整主镜像编译失败时，源码还会尝试生成只覆盖 ART 模块 JAR 的最小镜像，并在后续启动重试完整编译。

profile 输入和运行时产物的边界如下：

- 官方文档所说“Boot Image Profile 只能随 OTA 更新”，对应系统镜像内的 framework profile。Mainline APEX 还可以携带模块自己的 `etc/boot-image.prof`，Android 17 会把已安装模块提供的 profile 加入扩展镜像编译。
- `odrefresh` 可以在 ART/APEX 或 Boot Class Path 变化后，用当前系统和 APEX 提供的 profile 输入重新生成 `/data` 下的 `.art/.oat/.vdex`。

“ART Mainline 更新不会重建 Boot Image”不符合上述流程。

### Boot Image 变化不代表所有应用立即重编

应用 OAT 产物记录 Boot Class Path、image checksum 或 class loader context 等依赖信息。ART 按产物和当前上下文判断能否继续使用；失效的产物再由 ART Service 安排 dexopt。一次 Boot Image 变化可能让大量应用产物失效，但源码没有“无条件重新编译所有应用”的规则。

Boot Image、System Server 产物与普通应用产物的维护者也不同：

- `odrefresh`/`odsign` 负责早期启动需要的 Boot Class Path 与 System Server 运行时产物。
- Android 14 及以后由 ART Service 管理普通应用 dexopt。
- 产物不可用时，ART 还可能以 JIT、解释执行或 imageless 模式继续启动；具体退化方式取决于缺失的是主镜像、扩展还是应用编译产物。

## 确认设备正在使用的镜像

### 1. 查看配置与进程映射

以下命令用于确认是否覆盖默认 image location，并查出 Zygote 映射的实际文件。读取其他进程的 `/proc` 信息通常需要 root 或 `userdebug`/`eng` 构建。

```bash
adb shell getprop dalvik.vm.boot-image
adb shell 'pid=$(pidof zygote64); cat /proc/$pid/maps | grep -E "boot.*\\.(art|oat|vdex)"'
```

属性为空表示运行时采用默认选择逻辑，不代表没有 Boot Image。`maps` 中的路径是当前进程使用位置的直接证据；还要同时检查 32 位 Zygote 或其他运行时进程。

### 2. 用 `smaps` 判断共享质量

以下命令用于观察每段 Boot Image 映射的 `Shared_Clean`、`Private_Clean` 和 `Private_Dirty`：

```bash
adb shell 'pid=$(pidof zygote64); cat /proc/$pid/smaps' > zygote64-smaps.txt
```

从输出中按 `.art`、`.oat` 路径分组，再比较 Zygote 与多个应用进程。单看 RSS 会重复计算共享页；PSS 适合估算分摊成本，`Private_Dirty` 更适合定位写时复制增长。

### 3. 用 `oatdump` 检查镜像内容

`oatdump` 的 `--image` 参数接受单个或冒号分隔的 Boot Image location。下面的命令用于检查系统分区上的一个主镜像：

```bash
adb shell oatdump --image=/system/framework/boot.art
```

设备若使用 `/data` 产物或扩展组件，需要把 `maps` 中确认的 location 按组件顺序传入。输出可核对 image header、section、对象、OAT 依赖和编译代码；工具可用性与读取权限取决于构建类型。

### 4. 区分 `odrefresh` 与应用 dexopt

ART 产物更新问题应同时收集：

- early boot 日志中的 `odrefresh`、`odsign`、`dex2oat`。
- `/data/misc/apexdata/com.android.art/dalvik-cache` 中产物的时间戳和完整性。
- `odrefresh` 的编译阶段、触发原因与失败原因。
- ART Service 对应用执行的 dexopt 记录。

这些证据可以区分 Boot Image 重建、System Server 编译和应用 dexopt，避免把三类耗时合成一个“OTA 后重编”结论。

## OEM 调整的验证边界

OEM 可以调整 Boot Class Path、Boot Image Profile、`preloaded-classes` 和 `dirty-image-objects`，但每项改动都需要整机数据验证：

- Boot Image Profile 过小，会增加常用类恢复、方法解释/JIT 和随机 I/O；过大则增加文件尺寸、映射范围及驻留页。
- `preloaded-classes` 过小，会把类加载和初始化移到应用冷启动；过大会拉长 Zygote preload，并增加共享堆与脏页压力。
- 容易写入的对象散布在大量页面中，会抬高每个子进程的 `Private_Dirty`。只比较 `boot.art` 文件大小看不到这项成本。
- Mainline Boot Class Path JAR、System Server JAR 和自定义 Boot Class Path JAR 要放在正确的 classpath 配置中。把 `services.jar` 当作 Boot Class Path 组件会让编译依赖模型失真。

调优至少要同时观察 Zygote preload 时间、应用冷启动、Boot Image/OAT 文件尺寸、各进程 PSS、`Private_Dirty`、page fault 和 dexopt/JIT 行为。单个指标变好不能证明整机收益。

## 源码阅读入口

- `art/runtime/oat/image.h`、`image.cc`：格式版本、`ImageHeader`、section 和压缩块。
- `art/runtime/gc/space/image_space.h`、`image_space.cc`：image location 解析、预留、映射、校验、扩展加载和重定位。
- `art/libartbase/base/file_utils.cc`：Android 17 默认 Boot Image location 与 `/system`、`/data` 选择。
- `art/dex2oat/dex2oat.cc`、`dex2oat/linker/image_writer.cc`：主镜像/扩展识别、profile、对象选择与布局。
- `art/odrefresh/odrefresh.cc`：更新检查、`speed-profile` 参数、完整/最小镜像与 System Server 编译。
- `art/profman/boot_image_profile.cc`：从采样 profile 生成 Boot Image Profile 和预加载类清单。
- `frameworks/base/core/java/com/android/internal/os/ZygoteInit.java`：`preload()`、`preloadClasses()`、`gcAndFinalize()` 与 `fork` 前流程。
- `common/mm/memory.c`：`MAP_PRIVATE` 写 fault 与写时复制。

## Android 17 的映射与共享边界

Android 17 的 Boot Image 是一组可校验、可重定位、可扩展的 ART 运行时产物。`.art` 保存选入镜像的对象和元数据，`.oat` 提供编译代码，`.vdex` 保存 DEX 与验证相关数据；运行时可能从系统分区加载，也可能使用 `odrefresh` 在 ART APEX 数据目录生成的版本。

Boot Image Profile、Boot Image Extension、Zygote `preloaded-classes`、应用 Baseline Profile 和应用 Startup Profile 分属不同环节。性能分析只有在文件来源、映射类型、私有脏页、Zygote 预加载和 ART 产物更新原因分别确认后，才有足够证据修改配置。
