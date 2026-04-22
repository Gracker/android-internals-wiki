---
title: "16KB Page Size 与 Android 性能"
chapter: "4.7"
section: "4.7"
status: ready-for-review
drafted_date: "2026-04-06"
reviewed_date: "2026-04-21"
reviewed_by: openclaw-task6
polish_count: 1
polish_date: "2026-04-08"
polish_by: "task2b-polish"
applicable_versions: "Android 15 (API 35) - Android 17 (API 37)"
last_verified: "2026-04-06"
last_verified_against: "developer.android.com, source.android.com, ARM Architecture Reference Manual"
confidence: medium
sources:
  - type: official
    path: "developer.android.com/guide/practices/page-sizes"
  - type: official
    path: "source.android.com/docs/architecture/16kb-page-size"
  - type: official
    path: "android-developers.googleblog.com/16kb-page-size"
  - type: research
    path: "ARM Architecture Reference Manual — TLB 结构与页大小"
tags:
  - android
  - memory
  - page-size
  - tlb
  - compatibility
  - research
pipeline_stage: task6_pending
task6_state: revisiting
task9_state: pending
task2b_result: fixed
task2b_state: fixed
task6_result: pass-light-edit
task9_result: 'needs-rework'
task9_reviewed_date: '2026-04-22'
task9_reviewed_by: 'openclaw-task9'
last_task9_at: '2026-04-22T11:30:00+08:00'
last_task2b_at: "2026-04-22T12:08:42+08:00"
---
# 4.7 16KB Page Size 与 Android 性能

## 为什么要了解 16KB Page Size

当我们在 Perfetto 中对比同一台设备上 4KB 和 16KB page size 的启动 trace 时，会发现一个明显的差异：冷启动阶段主线程的 page fault 次数大幅减少，CPU 在内核态的时间占比明显下降。这不是魔法——是内存管理粒度变化带来的直接效果。

从 Android 15 开始，AOSP 支持使用 16KB page size 的设备。Google Play 当前公开的兼容要求也围绕 Android 15 展开：从 2025 年 11 月 1 日起，target Android 15+ 的 64 位新 App 和现有 App 更新需要支持 16KB。对 Android 16、Android 17 的设备侧强制策略，要以当年的 CDD 或官方公告为准。

为什么是现在？手机 RAM 从 2015 年的 2-3GB 增长到 2025 年的 8-16GB，但 Linux 的默认内存页大小一直停留在 4KB——这个值是 1980 年代为 VAX 架构设计的。现代 ARM CPU 的 TLB 容量虽然在增长，但 4KB 页粒度下 TLB 覆盖的内存总量（TLB Reach）已经远远不够用了。Google 的测试数据表明，切换到 16KB 后平均冷启动速度提升 3.16%，部分 App 甚至提升 30%——这不是微优化，是值得系统级投入的性能收益。

## 核心机制

### TLB 与页大小的关系

要理解 16KB 页为什么能提升性能，我们需要先理解 TLB（Translation Lookaside Buffer）在内存访问中的角色。

CPU 访问内存时，使用的是虚拟地址。虚拟地址需要翻译成物理地址才能访问实际的内存芯片，这个翻译过程通过页表（Page Table）完成。页表本身存储在内存中，如果每次内存访问都要先查页表，性能会下降一倍以上——因为每次实际的数据访问都需要额外的页表访问。

TLB 是 CPU 内部的一个小型缓存，专门存储最近使用的虚拟地址→物理地址映射。当 CPU 需要访问一个虚拟地址时，先查 TLB：命中则直接拿到物理地址（TLB Hit），未命中则需要遍历页表（TLB Miss），这个过程叫做 Page Table Walk，可能需要多次内存访问。

这就是页大小的关键：在 4KB 页大小下，一个 TLB entry 覆盖 4KB 内存；在 16KB 页大小下，同一个 TLB entry 覆盖 16KB 内存——覆盖面积扩大了 4 倍。假设一个 App 的代码段 + 数据段总共占用 64MB，4KB 页需要 16,384 个 TLB entry 才能全部覆盖，而 16KB 页只需要 4,096 个。

ARM Cortex-X 系列处理器的 L1 TLB 通常有几十到上百个 entry，L2 TLB（Unified TLB）有几百到上千个。对于一个活跃的 App 来说，64MB 的工作集完全可能超出 L1 TLB 的覆盖范围。页大小从 4KB 变为 16KB 后，同样的 TLB entry 数量能覆盖 4 倍的内存，TLB Miss 率显著下降。

[已验证: 来源见 ARM Architecture Reference Manual, TLB 结构描述]

> 本节讨论的内存管理基础机制，与 §4.1「Android 内存管理架构」中的进程内存布局、§4.3「ART 内存管理」中的堆管理策略直接相关。

### Page Fault 的减少

页大小增大还影响另一个关键指标：Page Fault 的频率。

Page Fault 分两种：Major（需要从磁盘读取）和 Minor（只需在内存中分配新页）。在 Android 上，由于采用 flash 存储，Major Page Fault 的延迟相对较低，但仍然远高于 TLB Hit 的延迟（微秒级 vs 纳秒级）。更常见的是 Minor Page Fault——App 启动时加载代码段、初始化数据段、mmap 文件时都会触发。

16KB 页大小下，操作系统一次性分配 16KB 而非 4KB 的连续内存。虽然看起来"浪费"了（如果一个对象只有 1KB，16KB 页会浪费 15KB），但实际上内存访问有很强的局部性（Locality）——分配 16KB 后，附近的数据大概率很快也会被访问。结果是总的 Page Fault 次数减少，启动阶段的内核开销降低。

### 量化性能数据

Google 在 Pixel 设备上的测试给出了以下具体数据：

| 指标 | 改善幅度 |
|------|---------|
| 冷启动（平均值） | +3.16% |
| 冷启动（最佳 App） | +30% |
| 功耗（启动场景） | -4.56% |
| 相机热启动 | +4.48% |
| 相机冷启动 | +6.60% |
| 系统启动时间 | +8%（约 -950ms） |

[已验证: 来源见 Google 官方 16KB Page Size 文档及 Android Developers Blog]

冷启动提升 3.16% 是所有 App 的平均值，30% 的最佳值出现在内存访问密集型 App 上（如大型游戏、图片编辑类 App）。这类 App 在启动时需要映射大量代码和资源文件，TLB Miss 和 Page Fault 是主要瓶颈，因此 16KB 页的收益最大。

功耗降低 4.56% 来自 CPU 减少了 TLB refill 和 Page Table Walk 的次数。这些操作需要访问内存中的页表，相比直接命中 TLB，功耗要高出数倍。减少这类"管理开销"，CPU 可以把更多时间用在有意义的计算上。

系统启动时间缩短 8%（约 950ms）的影响尤为明显——这个阶段的 page fault 特别密集，因为 system_server 和核心服务需要加载大量框架代码。更多启动优化的系统性方法见 §8.1「响应速度优化原则」和 §8.3「启动优化实战」。16KB 页让每次 page fault 覆盖更多代码，总的 fault 次数减少。

## 对内存使用的影响

性能提升不是免费的。16KB 页大小的主要代价是**内部碎片**增加。

考虑一个场景：App 分配了一个 5KB 的对象。在 4KB 页下，需要 2 页（8KB），浪费 3KB。在 16KB 页下，需要 1 页（16KB），浪费 11KB。这就是内部碎片——分配粒度变大导致的空间浪费。

Google 的测试表明，16KB 页大小下系统平均内存使用量增加约 5-10%。但这个数字需要辩证地看：

**页表本身变小了。** 同样的 8GB 内存，4KB 页需要约 200 万个页表项，16KB 页只需要 50 万个。页表本身也占用内存，而且页表越小，L1/L2 缓存命中率越高。

**实际浪费取决于分配模式。** 连续分配大块内存（如 Bitmap、buffer）时，浪费可以忽略。小对象分配（如 Java 对象）由 ART 的堆管理器处理，堆管理器向内核申请 16KB 页后，内部做精细分配，浪费有限。

**LMK 交互。** 内存使用量增加意味着 lmkd 可能更早触发回收（§4.5「低内存影响与 lmkd」详细分析了 LMK 的触发策略）。16KB 页下 Page Fault 减少带来的性能收益是否足以抵消 LMK 的额外开销，取决于具体的内存压力水平。6GB 以下的设备需要特别关注这个权衡；8GB+ 的设备上，5-10% 的内存增长（约 400-800MB）在可用 RAM 的占比中不太敏感。

## 对 App 开发者的影响

这是所有 App 开发者必须面对的现实问题。

### 纯 Java/Kotlin App

如果 App 没有任何 Native 代码（C/C++），好消息是：通常不需要修改。ART 运行时和 Android 框架已经适配了 16KB 页，Java/Kotlin 层的内存分配由 ART 堆管理器处理，不需要关心底层页大小。

### Native 代码（NDK）

如果 App 包含 `.so` 文件——无论是自己写的还是通过第三方 SDK 引入的——就需要确保这些 `.so` 文件的 ELF 段（segment）按 16KB 边界对齐。

为什么？Linux 加载 ELF 共享库时，通过 `mmap()` 将文件映射到内存。`mmap()` 按页大小对齐映射区域。如果 `.so` 文件的 ELF 段只按 4KB 对齐，在 16KB 页系统上，一个段可能跨越两个页——加载器需要额外处理跨页对齐，甚至可能导致段内容被部分截断或错误映射，引发 SIGBUS 或 SIGSEGV 崩溃。

**构建工具链要求：**
- NDK r28+：默认输出 16KB 对齐的 `.so` 文件
- NDK r27：需要在链接时添加 `-Wl,-z,max-page-size=16384`
- AGP 8.5.1+：对使用 uncompressed shared libraries 的 App，可以正确请求 16KB zip 布局
- AAB 产物要再用 `bundletool dump config --bundle <your.aab> | grep alignment` 检查是否为 `PAGE_ALIGNMENT_16K`
- AGP 8.3-8.5 虽然默认会生成 16KB 页边界 ELF，但 `bundletool` 默认不会替你补齐 APK zip alignment；只升级到这几个版本，Play 产物仍可能安装失败

**代码中的页大小假设：** 真正会出错的是把页大小写死成 `4096`，例如 `#define PAGE_SIZE 4096`。`sysconf(_SC_PAGESIZE)` 和 `getpagesize()` 都属于运行时查询，应该保留：

```c
// 错误：把页大小写死成 4096
#define PAGE_SIZE 4096

// 正确：运行时查询
long page_size = sysconf(_SC_PAGESIZE);
int page_size2 = getpagesize();
```

这类 bug 通常不会在 4KB 设备上暴露，只在 16KB 设备上才崩溃。Google Play 已经在 Play Console 中增加了检测机制，会警告使用了 4KB 对齐 `.so` 的 App。

### Google Play 兼容要求

公开文档当前明确的一条时间线是：

- **2025 年 11 月 1 日**：提交到 Google Play、且 target Android 15+ 的新 App 与现有 App 更新，需要在 64 位设备上支持 16KB page size

公开文档里没有给出“2026 年 5 月 1 日所有更新一刀切”的统一口径，本章不把它写成既定政策。

[已验证: 来源见 Google Play 16 KB 要求页面及 developer.android.com]

## 迁移与测试方法

### 模拟器测试

Android Studio 从 2024 年起提供了 16KB 页大小的模拟器镜像。在 AVD Manager 中创建虚拟设备时，选择 Android 15+ 的系统镜像，在高级设置中将 "Page Size" 设为 16KB 即可。

启动后在设备上验证：

```bash
adb shell getconf PAGE_SIZE
# 预期输出: 16384
```

### 物理设备测试

Pixel 8/8 Pro/8a 和 Pixel 9 系列在 Android 15 QPR1+ 上支持开发者选项中的 "Boot with 16KB page size"。启用后重启设备即可。

### 验证 APK 对齐

Google 提供了 `check_elf_alignment.sh` 脚本，可以检查 APK 中所有 `.so` 文件是否满足 16KB 对齐：

```bash
# 方法 1：使用 zipalign 工具验证
zipalign -c -P 16 -v 4 your_app.apk

# 方法 2：使用 check_elf_alignment.sh
# 来源：Android 官方文档
./check_elf_alignment.sh your_app.apk
```

Play Console 的 App Bundle Explorer 也提供了自动化的对齐检查。上传 AAB 后，在 "发布" → "设置" 中可以看到对齐状态。

### 常见迁移问题

**第三方 SDK 的 `.so` 文件**：这是最常见的阻塞点。如果 App 依赖的第三方 SDK 还没有适配 16KB，你需要联系 SDK 提供方获取更新版本。在此期间，可以用 NDK r28+ 的 `llvm-objcopy` 工具手动重新对齐（但这不能修复代码中的硬编码 PAGE_SIZE 问题）。

**构建缓存问题**：升级 AGP/NDK 后，记得 clean build。Gradle 的增量编译缓存可能保留旧的 4KB 对齐产物。

## 在 Perfetto 中的表现

16KB 页大小不会在 Perfetto 中显示为一个独立的 Track 或标记——它的影响体现在多个 Track 的数据差异中。

### Page Fault 频率变化

Perfetto 的 `mem.mm.min_flt` 计数器（部分 Pixel 设备支持）可以追踪 Minor Page Fault 的频率。对比 4KB 和 16KB 设备上同一 App 的冷启动 trace，16KB 设备上的 page fault 计数应该明显更低。

使用 Trace Processor SQL 查询：

```sql
-- 查询指定进程的 page fault 总量
-- 替换 '目标进程名' 为实际进程名即可运行
SELECT
  process.name,
  SUM(counter.value) AS total_page_faults
FROM counter
JOIN counter_track ON counter.track_id = counter_track.id
JOIN process_counter_track ON counter_track.id = process_counter_track.id
JOIN process USING (upid)
WHERE counter_track.name LIKE '%min_flt%'
  AND process.name = '目标进程名'
GROUP BY process.name
ORDER BY total_page_faults DESC;
```

[待补充: 实际 16KB vs 4KB 的 Perfetto trace 截图对比]

### CPU 内核态时间占比

TLB Miss 减少后，CPU 在内核态处理 Page Table Walk 的时间也相应减少。在 Perfetto 的 CPU Scheduling Track 中，对比两种页大小下启动阶段的 `iowait` 和内核态时间，可以看到 16KB 设备的内核态占比更低。

## 与 Linux THP（Transparent Huge Pages）的关系

16KB 页大小和 THP 是两种不同的优化路径，但它们解决的是同一个问题——减少 TLB Miss。

**THP** 在 4KB 基础页大小上工作，将连续的 4KB 页合并为 2MB 的大页（ARM64 PMD_SIZE）。优点是不需要修改 App，内核自动管理；缺点是需要物理连续的大块内存（4KB base 时为 2MB），长时间运行后碎片化严重，khugepaged 的后台整理本身也有 CPU 开销。

**16KB 基础页** 是更底层的改变。它不需要物理连续内存（每个 16KB 页独立分配），没有 khugepaged 的开销，收益更确定。缺点是需要重新编译 Native 代码。

两者**可以叠加使用**：16KB 基础页 + THP 合并为 32MB 大页。ARM64 的 PMD_SIZE（PMD 级别的 block size）随基础页大小变化：4KB base → 2MB THP，16KB base → 32MB THP。这意味着 TLB entry 可以覆盖 16KB（普通页）或 32MB（大页），TLB Reach 进一步扩大。不过在实际的 Android 设备上，THP 默认配置通常是 `madvise` 模式（只对显式请求的内存区域启用），对大多数 App 的实际影响有限。

对于性能分析来说，16KB 基础页的收益比 THP 更直接、更稳定。在分析 App 的 TLB 相关性能问题时，优先确认设备是否启用了 16KB 页。

## 版本演进与 OEM 适配

### 已公开确认的里程碑

- **Android 15（API 35，2024）**：AOSP 开始支持 16KB page size 设备；模拟器与部分 Pixel 设备提供测试入口
- **Google Play（2025-11-01）**：target Android 15+ 的新 App 与现有 App 更新，需要在 64 位设备上支持 16KB

### Android 16 / 17 的设备策略

Android 16、Android 17 会不会把 16KB 写成更强的设备侧要求，要看对应版本的 CDD、兼容性公告或 OEM 发布说明。当前没有查到可直接引用的公开条文时，更适合把它当成待确认信息，而不是既定政策。

### OEM 适配进展

OEM 的适配进度取决于 SoC 厂商的内核支持。高通（Snapdragon）和联发科（Dimensity）从 2024 年开始在 BSP 中提供 16KB 页大小选项。实际启用还需要 OEM 验证所有 HAL 模块和驱动程序的兼容性——特别是 Camera HAL、GPU 驱动、安全模块（TrustZone）这些包含大量 Native 代码的组件。

从 Perfetto 分析的角度，这意味着同一款 App 在不同 OEM 的 16KB 设备上可能有不同的性能表现——因为 OEM 可以调整页大小相关的内核参数（如 THP 策略、zRAM 块大小等）。在跨设备对比性能数据时，需要先确认底层页大小是否一致。

```bash
# 快速检查设备页大小
adb shell getconf PAGE_SIZE
```

## 常见问题与误区

### "16KB 页会让 App 占用更多内存"

这个说法过于简化。页表本身变小了（节省内存），内部碎片确实增加了（浪费内存）。最终效果取决于 App 的分配模式：大量小对象的 App 内存增长更多，以大块分配为主的 App 几乎没有增长。Google 的平均数据是 5-10%，但对于 8GB+ 设备来说，这个增长在整体内存预算中占比不大。

### "纯 Java App 不需要关心 16KB"

大体正确，但有一个例外：如果你的 App 通过 JNI 调用了系统库（如 `libandroid_runtime.so`、`libnativehelper.so`），而这些系统库在某些老设备上还没有 16KB 对齐——这种情况下 App 本身不需要修改，但可能遇到系统级兼容性问题。Android 15+ 的系统库已经全部 16KB 对齐，所以这只影响老设备。

### "16KB 页大小只影响启动速度"

不对。16KB 页影响所有涉及内存访问的场景——不只是启动。滑动时的大量 Bitmap 解码、WebView 的页面渲染、视频解码的 buffer 管理都会受益。只是启动阶段的收益最容易量化（因为 page fault 最密集），所以 Google 在官方文档中重点展示了启动数据。从 Perfetto 分析的实际案例来看，列表滑动场景中 Bitmap 频繁 mmap/unmmap 导致的 Minor Page Fault 也是一个可观测的改善点（参见 §7.8「RecyclerView 列表滑动性能深度优化」中的内存访问模式分析）。

### "我需要在代码中硬编码 16384"

绝对不要。正确的做法是用 `sysconf(_SC_PAGESIZE)` 运行时查询。这不仅是为了兼容 4KB 和 16KB 设备，也是为了应对未来可能出现的 64KB 页大小。

## 参考资料

- [已验证: developer.android.com/guide/practices/page-sizes — Google 官方 16KB 迁移指南]
- [已验证: source.android.com/docs/architecture/16kb-page-size — AOSP 架构文档]
- [已验证: ARM Architecture Reference Manual — TLB 结构与页大小]
- [待验证: Google 官方 16KB 测试数据的精确测试条件（设备型号 / Android 版本 / App 样本）]
- [待验证: 16KB 基础页 + THP 在 Android 16 设备上的默认启用状态]
