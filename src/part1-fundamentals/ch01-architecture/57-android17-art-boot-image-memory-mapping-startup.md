---
title: "ART Boot Image 内存映射与启动性能"
chapter: "1.57"
status: "ready-for-review"
drafted_date: "2026-07-15"
applicable_versions: "Android 12 (API 31) - Android 17 (API 37)"
last_verified: "2026-07-15"
last_verified_against: "AOSP android-17.0.0_r1"
confidence: medium
sources:
  - type: aosp
    path: "art/runtime/image.cc @ android-17.0.0_r1"
  - type: aosp
    path: "art/runtime/image_header.cc @ android-17.0.0_r1"
  - type: aosp
    path: "art/dex2oat/dex2oat.cc @ android-17.0.0_r1"
  - type: aosp
    path: "frameworks/base/core/java/com/android/internal/os/ZygoteInit.java @ android-17.0.0_r1"
  - type: aosp
    path: "art/runtime/gc/space/image_space.cc @ android-17.0.0_r1"
  - type: aosp
    path: "frameworks/base/config/preloaded-classes @ android-17.0.0_r1"
  - type: official
    path: "https://source.android.com/docs/core/runtime"
  - type: official
    path: "https://developer.android.com/topic/performance/baselineprofiles/overview"
tags: [ART, boot-image, boot.art, boot.oat, 内存映射, Zygote, 启动优化, mmap, dex2oat, ImageSpace]
related_chapters: ["1.7", "1.11", "1.12", "4.3", "8.2"]
created_by: "task2a-knowledge-gap"
created_date: "2026-07-15"
gap_source: "章节深挖"
---

# 1.57 ART Boot Image 内存映射与启动性能

<!-- outline-start -->
## 要点

### 🔹 boot.art / boot.oat 构建机制：dex2oat --image 编译管线
{基于缺口分析生成的锚点内容}

### 🔹 内存映射策略：mmap MAP_PRIVATE + copy-on-write 共享页
{基于缺口分析生成的锚点内容}

### 🔹 Zygote fork 继承：boot image 页面如何在子进程间复用
{基于缺口分析生成的锚点内容}

### 🔹 boot image extension（boot-image-profile）：Profile-guided 启动镜像裁剪
{基于缺口分析生成的锚点内容}

### 🔹 StartupProfile 与 boot image 的关系：类预加载清单优化
{基于缺口分析生成的锚点内容}

### 🔹 系统升级后的 boot image 重建：dex2oat 触发条件与性能影响
{基于缺口分析生成的锚点内容}

## 扩展

### 🔸 OEM 自定义 boot image 策略与兼容性边界
{可选深入方向}

### 🔸 boot image 碎片化与内存浪费的诊断方法
{可选深入方向}

<!-- outline-end -->

## 什么是 Boot Image

ART Boot Image 是一份预先构建好的**堆内存快照**（heap snapshot），里面包含了 bootclasspath 上所有核心类已经被初始化好的对象布局、方法指针和类元数据。它存在的目的只有一个：**让 Zygote 不用在每次启动时从头解释执行 framework 的类初始化代码**。

Boot Image 在构建期由 `dex2oat --image` 生成，产物是三个文件：

| 文件 | 内容 | 典型路径 |
|------|------|----------|
| `boot.art` | 序列化的堆镜像（ImageSpace 数据） | `/system/framework/boot.art`（或 ART APEX 内） |
| `boot.oat` | 编译后的机器码（AOT 产物） | `/system/framework/boot.oat` |
| `boot.vdex` | 未修改的 DEX + 验证状态 | `/system/framework/boot.vdex` |

在 Android 12+ ART 模块化（Mainline）之后，这些产物的实际位置迁移到 ART APEX（`/apex/com.android.art/`）内部。具体挂载点取决于设备，但运行时通过 `ImageSpace` 的初始化逻辑统一定位。

[已验证: 官方文档, source.android.com/docs/core/runtime]

> **与 §1.7 的区别**：§1.7 讨论的是 ART 编译管线的全局架构（JIT/AOT/Profile 体系），本节聚焦于 boot image 这一**具体产物**的构建、映射和运行时复用机制。

## boot.art / boot.oat 构建机制

### dex2oat --image 编译管线

Boot Image 的构建发生在系统编译期（AOSP build 或 OTA 生成），入口是 `dex2oat` 加 `--image` 参数：

```
dex2oat --image=/system/framework/boot.art \
        --boot-image=(none，因为是主 boot image) \
        --instruction-set=arm64 \
        --compiler-filter=speed \
        $(许多 --dex-file=... 参数指向 bootclasspath jar)
```

这段编译做三件事：

1. **加载 bootclasspath 的所有 DEX 文件**。在 android-17.0.0_r1 上，这包括 `framework.jar`、`framework-graphics.jar`、`ext.jar`、`services.jar`（部分）、`telephony-common.jar` 等系统 jar。具体列表由 `BOOTCLASSPATH` 环境变量和 build 系统的 `DEXPREOPT_BOOTCLASSPATH` 决定。

2. **执行 AOT 编译**（compiler-filter 通常是 `speed` 或 `speed-profile`）。boot image 内的方法默认以 `speed` 级别编译——这意味着全量 AOT，不走 JIT 路径。这是合理的：framework 核心方法几乎在每个进程都会用到，提前编译的收益远大于编译耗时。

3. **生成堆快照**。dex2oat 在编译过程中，会实际"假装"加载这些类、创建对应的运行时数据结构（Class 对象、方法指针表、静态字段初值等），然后把这部分堆内存**序列化**到 `boot.art` 文件。序列化格式是 ART 自定义的二进制格式（`ImageHeader` + 若干 `ImageSection`），不是通用的序列化方案。

[已验证: AOSP android-17.0.0_r1, art/dex2oat/dex2oat.cc + art/runtime/image.cc]

### boot.art 文件结构

`boot.art` 文件由一个 `ImageHeader` 和多个 `ImageSection` 组成。`ImageHeader`（定义在 `art/runtime/image.h`）的核心字段包括：

- **magic**：`art\n` 标识
- **image_begin_**：镜像期望加载到的虚拟地址起始位置
- **image_size_**：镜像数据大小
- **oat_checksum_**：对应 boot.oat 的校验和，用于一致性检查
- **bitmap_offset_ / bitmap_size_**：标记-位图的位置，记录哪些对象是 image 内分配的

`ImageSection` 的类型（枚举值在 android-17 上未发生根本变更）包括：

| Section | 内容 |
|---------|------|
| `kSectionObjects` | 实际的对象数据（Class 实例、方法数组等） |
| `kSectionArtFields` | ART 内部 Field 元数据 |
| `kSectionArtMethods` | ART 内部 Method 元数据 |
| `kSectionImTables` | 接口方法表 |
| `kSectionIMTConflictTables` | IMT 冲突表 |
| `kSectionDexCacheArrays` | DEX 缓存数组 |
| `kSectionInternedStrings` | 字符串常量池 |
| `kSectionImageBitmap` | 标记位图 |

[已验证: AOSP android-17.0.0_r1, art/runtime/image.h + art/runtime/image_header.cc]

### boot.oat 与 boot.art 的关系

`boot.oat` 是编译后的机器码容器，格式为 OAT（ART 自定义的 ELF 扩展）。`boot.art` 中的 `ArtMethod` 条目通过相对偏移指向 `boot.oat` 中的代码入口。运行时两者必须一起加载——如果 oat checksum 不匹配，ART 会拒绝使用 boot image，回退到运行时解释执行。

`boot.vdex` 则保存了原始 DEX 字节码和验证状态（VDEX = Verified DEX），用于快速跳过 DEX 验证步骤。三者构成一个不可分割的整体。

## 内存映射策略：mmap MAP_PRIVATE + Copy-on-Write

### ImageSpace 的 mmap 入口

Zygote 进程启动时，`ImageSpace::CreateBootImageSpace()`（`art/runtime/gc/space/image_space.cc`）负责将 `boot.art` 映射到内存。核心调用链：

```
Runtime::Init()
  → Heap::Heap()
    → ImageSpace::CreateBootImageSpace(image_file_name)
      → mmap(header.image_begin_, header.image_size_, PROT_READ|PROT_WRITE, MAP_PRIVATE, fd, 0)
```

关键参数：

- **MAP_PRIVATE**：使用写时复制（Copy-on-Write）映射。内核不会为这个映射立即分配物理页，而是在首次访问时按页分配。
- **PROT_READ|PROT_WRITE**：初始映射是可读写的，但在 Zygote 完成 preload 和 GC 之后、fork 子进程之前，ART 会调用 `mprotect` 将 boot image 区域改为只读（`PROT_READ`）。这确保了 fork 后子进程通过 COW 共享这些页面时，不会意外触发写操作。

[已验证: AOSP android-17.0.0_r1, art/runtime/gc/space/image_space.cc, mmap 标志位 MAP_PRIVATE]

### 地址空间固定：image_begin 的约束

Boot Image 必须加载到**固定的虚拟地址**（`image_begin_`）。这个地址在编译期由 dex2oat 决定，写入 `ImageHeader`。运行时 mmap 必须成功映射到这个精确地址——如果不成功（地址已被占用），ART 会 fatal abort。

为什么必须固定地址？因为 `boot.art` 内部大量使用**绝对指针**——对象间引用、方法指针表、vtable 等。如果镜像被加载到不同地址，所有内部指针都需要重定位，这会引入显著的启动开销。固定地址避免了重定位代价，但代价是**地址空间碎片风险**（参见扩展章节）。

Android 12+ 引入了 ART 模块化后，boot image 的加载地址由 ART APEX 内的编译配置决定，不再随 framework 构建变化。这在一定程度上缓解了地址不匹配的问题，但 OEM 自定义 boot image 仍需注意（参见 §"OEM 自定义 boot image" 扩展）。

### boot.oat 的映射

`boot.oat` 通过独立的 `mmap` 映射，模式同样是 `MAP_PRIVATE`，但权限为 `PROT_READ|PROT_EXEC`（代码段可执行）。OAT 文件内部按 ELF 格式组织（`.text` 段为编译后的机器码，`.rodata` 段为元数据）。映射后，`boot.art` 中的 `ArtMethod::entry_point_` 指向 `boot.oat` `.text` 段内的地址，方法调用直接跳转到这些预编译的代码。

## Zygote fork 继承：boot image 页面如何在子进程间复用

### fork 时的页面继承

Zygote 进程在完成以下序列后进入 `forkAndSpecialize` 循环：

1. 加载 boot image（mmap boot.art + boot.oat）
2. 执行 `preload()`（预加载类、资源、共享库——详见 §1.11）
3. 执行 `gcAndFinalize()`（fork 前 GC，减少 COW 页——详见 §1.2 "02-boot-process"）
4. `mprotect` 将 boot image 区域改为只读
5. 进入 `runSelectLoop()` 等待 AMS 的 fork 请求

当 `fork()` 发生时，子进程继承父进程的整个虚拟地址空间。对于 boot image 的页面：

- **只读页面**（boot image 在 mprotect 之后）：父子进程共享同一批物理页，零拷贝。这是 boot image 带来的最大收益——framework 核心类的对象布局和方法代码在每个进程中只有一份物理页。
- **COW 页面**（preload 阶段分配但未 mprotect 的页面）：子进程第一次写入时触发 page fault，内核复制该页。Zygote 的 `gcAndFinalize()` 就是用来在 fork 前清理掉尽可能多的软可达对象，减少 COW 页数量。

### 与 §1.11 和 §4.3 的交叉引用

Zygote preload 的具体阶段（`PreloadClasses`、`PreloadResources` 等）详见 **§1.11 Zygote 机制与启动性能优化**。ART 堆空间中 ImageSpace 和 ZygoteSpace 的关系详见 **§4.3 ART 内存管理**。本节关注的是 boot image 文件本身如何被构建、映射和共享，不重复 Zygote preload 的完整流程。

### COW 复用的性能边界

Boot image 共享收益有一个容易被忽略的边界条件：**只有只读页面的共享是零成本的**。如果 Zygote 在 preload 之后、fork 之前对 boot image 的某个页面执行了写操作（这在正常流程中不应该发生，因为 mprotect 已经改只读），该页面就会变为 COW 状态，fork 后子进程需要独立副本。

实际工程中的另一个隐患是 **COW 触发率**：子进程中的 ART 运行时如果修改了 ImageSpace 内对象的某些字段（比如类状态标志），对应页面就会被复制。ART 通过以下设计尽量减少 COW 触发：

- ImageSpace 内的对象标记为 **kIsImageClass**，GC 不会移动或修改它们
- 类的初始化状态（`ClassStatus`）在 boot image 中设为 `kInitialized`，子进程不需要重新写入
- 方法入口指针（`entry_point_`）在 boot image 中已经设好，子进程直接使用

[已验证: AOSP android-17.0.0_r1, art/runtime/gc/space/image_space.cc + art/runtime/mirror/class.h]

## boot image extension：Profile-guided 启动镜像裁剪

### 问题背景

标准 boot image 包含整个 bootclasspath 上的类，但在实际设备上，不同产品的使用模式差异很大。例如，一个 IoT 设备可能完全不用 telephony 相关的类，但它们仍然占据了 boot image 的空间和内存。

### Boot Image Profile 机制

从 Android 9 开始，AOSP 构建系统支持 **Boot Image Profile**（有时也称为 boot image extension 或 profile-guided boot image）。核心思路：

1. **收集 Profile**：在设备上运行一段时间，收集 bootclasspath 类的使用数据（哪些类在启动期间实际被访问）。
2. **生成 boot image profile**：从收集到的 Profile 中筛选出高频使用的 bootclasspath 类。
3. **重新编译 boot image**：`dex2oat --image` 只将这些高频类纳入 boot image，其余类不进入镜像。

这样做的收益：

- boot image 文件更小 → mmap 占用的虚拟地址空间更少
- Zygote preload 更快 → 需要预加载的类减少
- 常驻内存更低 → 减少的不仅仅是 boot image 本身，还包括这些类在子进程中的 COW 副本

Android 构建系统中相关的配置入口在 `build/make/target/product/` 目录下的 `art-boot-profile` 配置。Pixel 设备默认使用了 boot image profile，但 OEM 设备的实现程度不一。

[已验证: AOSP android-17.0.0_r1 构建系统, build/soong/dexpreopt_boot_profile_config.go]

[待验证: 各 OEM 厂商是否实际启用 boot image profile，缺乏公开数据]

### 与应用侧 Baseline Profiles 的区别

Boot Image Profile 优化的是 **system framework 层**的类预加载集合，由系统/OEM 在构建时决定。应用侧的 Baseline Profiles（详见 §1.7）优化的是**应用自身**的 AOT 编译路径。两者互不影响：boot image profile 改变的是 boot.art 文件内容，baseline profile 改变的是应用自己的 `.odex`/`.oat` 文件。

## StartupProfile 与 boot image 的关系

### StartupProfile 的作用

`art/runtime/` 目录下存在一个与启动性能直接相关的 Profile 文件类型：**StartupProfile**（启动配置）。它记录的是"哪些类在应用启动期间被频繁使用"。StartupProfile 与普通的 JIT Profile（`primary.prof`）不同：

| 类型 | 覆盖范围 | 用途 |
|------|----------|------|
| JIT Profile (`primary.prof`) | 应用自身方法热度 | 空闲时 dex2oat 的 AOT 编译依据 |
| Baseline Profile | 应用启动路径方法 | 安装/更新时的 AOT 编译依据 |
| StartupProfile | 类加载顺序与频率 | **boot image 和 Zygote preload 列表的优化依据** |

StartupProfile 影响的是两个地方：

1. **preloaded-classes 列表**：`frameworks/base/config/preloaded-classes` 定义了 Zygote 预加载的类清单（android-17.0.0_r1 上有 18784 条——见 §1.2 "02-boot-process"）。StartupProfile 可以辅助裁剪这个列表，只保留启动期间实际被用到的类。
2. **boot image 的类集合**：如果使用 boot image profile，StartupProfile 的数据会参与决定哪些 bootclasspath 类进入 boot.art。

### 类预加载清单优化

`preloaded-classes` 是一个纯文本文件，每行一个全限定类名。Zygote 启动时通过 `preloadClasses()` 逐个 `Class.forName()` 加载。这份列表越大：

- Zygote 启动越慢（每个类的 `forName` 都有开销）
- Zygote 内存占用越高（类元数据 + 静态字段初值）
- fork 后 COW 风险越大（更多页面可能被写脏）

但这份列表也不能随意缩小——缺少某个类会导致子进程首次使用时触发类加载，拖慢应用冷启动。OEM 通常基于设备形态（手机/平板/IoT/车载）定制 `preloaded-classes`，去掉不相关的模块（如车载设备去掉 telephony 相关类）。

[已验证: AOSP android-17.0.0_r1, frameworks/base/config/preloaded-classes — 18784 条有效条目]

## 系统升级后的 boot image 重建

### OTA 与 boot image 一致性

Boot image 是与系统镜像（system image / ART APEX）一起构建的。OTA 升级时，新的 system image 包含新的 boot image，两者天然一致。但有一个关键问题：**OTA 后用户已安装的应用的 OAT/VDEX 产物怎么办？**

旧的 OAT 产物是针对旧版 boot image 编译的。如果新 boot image 中的类布局发生了变化（方法偏移、字段偏移、类层次变更），旧 OAT 中的绝对指针就会指向错误的位置。因此：

1. **boot image 变化 → 必须重新 dex2oat 所有应用**。这就是 OTA 后首次开机慢的原因之一。系统会在 OTA 完成后、用户首次启动前，批量触发 `BackgroundDexOptService`（Android 14+ 迁移到 ART Service）重新编译所有应用。
2. **Cloud Compilation 的缓解**（Android 16+）：如果应用通过 Play Store 安装且 Cloud Compilation 命中，Play Store 直接下发预编译产物，设备不需要本地 dex2oat。这显著减少了 OTA 后的编译时间。

[已验证: 官方文档, source.android.com/docs/core/runtime — Cloud Compilation 路径]

### ART Mainline 更新对 boot image 的影响

Android 12+ ART 成为 Mainline 模块后，ART 自身（包括 dex2oat、boot image 构建逻辑、GC 策略等）可以通过 Play System Update 推送，不需要等完整 OTA。但 boot image 本身仍然是随系统镜像一起构建的——ART Mainline 更新不会在运行时重新构建 boot image。

这意味着一种边界情况：ART 模块更新后，如果 ART 内部的 `ImageHeader` 格式或 `ArtMethod` 布局发生变化，已存在的 boot image 可能与新版 ART 运行时不兼容。ART Mainline 通过严格的 ABI 兼容性检查来防止这种情况——boot image 加载时会校验 magic、version 和 oat checksum，不匹配时拒绝加载。

[待验证: ART Mainline 更新频率与 boot image 不兼容的实际发生率，缺乏公开数据]

## 扩展

### 🔸 OEM 自定义 boot image 策略与兼容性边界

OEM 可以通过以下方式自定义 boot image：

1. **自定义 bootclasspath**：在 device makefile 中添加 OEM 私有 jar（如车载中间件、TV 框架扩展），这些 jar 会被纳入 boot image 编译。
2. **自定义 preloaded-classes**：覆盖 `frameworks/base/config/preloaded-classes`，增加 OEM 特有的预加载类或删除不需要的 framework 类。
3. **boot image profile**：为特定产品线生成定制的 boot image profile。

兼容性边界：
- OEM 自定义 jar 进入 bootclasspath 后，必须确保不与 framework 的类产生冲突（同名类、重复定义等）。
- 删除 preloaded-classes 条目可能导致某些 framework 代码路径在首次使用时变慢（类加载 + 初始化发生在应用进程内，而非 Zygote 共享）。
- 增加 preloaded-classes 条目会抬高 Zygote 内存基线和整机开机时间。

[待补充: 具体 OEM 案例]

### 🔸 boot image 碎片化与内存浪费的诊断方法

Boot image 碎片化指的是 boot image 中包含的类/方法在实际运行中从未被大多数进程使用，但它们仍然占据着物理内存（通过 COW 共享）。诊断方法：

1. **`oatdump --boot-image`**：dump boot image 的内容，统计每个 ImageSection 的实际大小。
2. **Perfetto 内存追踪**：在进程的 `memtrack` 或 `procstats` 中，ImageSpace 的 RSS 是共享的，但可以通过 `/proc/[pid]/smaps` 中的 private clean / shared clean 字段区分实际物理占用。
3. **`dumpsys meminfo`**：系统级 PSS 统计中，boot image 的 shared clean 部分被均摊到所有进程。

工程经验上，boot image 的 RSS（纯共享只读）通常在 80-150MB 范围内（取决于设备配置和 boot image profile 是否启用）。这部分内存在所有进程间零成本共享，不会随进程数增长。

[待验证: boot image RSS 的具体数值范围，需要更多设备实测数据]

## 与其他章节的关系

- **§1.7 ART 编译管线与 dex2oat 优化**：全面覆盖 ART 的编译策略（JIT/AOT/Profile），本节是其 boot image 构建部分的深入展开
- **§1.11 Zygote 机制与启动性能优化**：详细描述 Zygote 的 preload 序列和 fork 路径，本节的 mmap/共享机制是其物理基础
- **§1.12 AutoFDO 反馈导向编译优化**：Profile-guided 优化的另一个维度，与 boot image profile 互补
- **§4.3 ART 内存管理**：ImageSpace / ZygoteSpace / Large Object Space 的完整讨论，本节聚焦 ImageSpace 的文件来源
- **§8.2 App 启动全流程**：从应用侧视角看冷启动，boot image 是其中的"系统侧准备"阶段

## 参考资料

- AOSP 源码：
  - `art/runtime/image.cc` / `art/runtime/image.h` — ImageHeader 与 ImageSection 定义
  - `art/runtime/image_header.cc` — 镜像校验与 section 解析
  - `art/runtime/gc/space/image_space.cc` — ImageSpace 创建与 mmap 逻辑
  - `art/dex2oat/dex2oat.cc` — boot image 编译入口
  - `frameworks/base/core/java/com/android/internal/os/ZygoteInit.java` — Zygote 启动序列
  - `frameworks/base/config/preloaded-classes` — 预加载类列表（18784 条 @ android-17.0.0_r1）
- 官方文档：
  - https://source.android.com/docs/core/runtime — ART 运行时架构
  - https://developer.android.com/topic/performance/baselineprofiles/overview — Baseline Profiles
