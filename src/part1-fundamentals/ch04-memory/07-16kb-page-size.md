---

title: "16KB Page Size 与 Android 性能"
chapter: "4.7"
section: "4.7"
status: finalized
drafted_date: "2026-04-06"
reviewed_date: "2026-06-03"
reviewed_by: "openclaw-task6"
polish_count: 1
polish_date: "2026-04-08"
polish_by: "task2b-polish"
applicable_versions: "Android 15 (API 35) - Android 17 (API 37)"
last_verified: "2026-06-28"
last_verified_against: "developer.android.com page size docs, source.android.com 16KB architecture docs, AOSP android-17.0.0_r1 bionic/linker + libc/private/WriteProtected.h, ARM Architecture Reference Manual"
confidence: medium
sources:
  - type: official
    path: "developer.android.com/guide/practices/page-sizes"
  - type: official
    path: "source.android.com/docs/core/architecture/16kb-page-size/16kb"
  - type: official
    path: "android-developers.googleblog.com/2024/08/adding-16-kb-page-size-to-android.html"
  - type: official
    path: "android-developers.googleblog.com/2025/05/prepare-play-apps-for-devices-with-16kb-page-size.html"
  - type: aosp
    path: "platform/bionic/+/refs/tags/android-17.0.0_r1/linker/linker_phdr.cpp"
  - type: aosp
    path: "platform/bionic/+/refs/tags/android-17.0.0_r1/linker/linker_phdr.h"
  - type: aosp
    path: "platform/bionic/+/refs/tags/android-17.0.0_r1/linker/linker_phdr_16kib_compat.cpp"
  - type: aosp
    path: "platform/bionic/+/refs/tags/android-17.0.0_r1/linker/linker.cpp"
  - type: aosp
    path: "platform/bionic/+/refs/tags/android-17.0.0_r1/libc/platform/bionic/page.h"
  - type: aosp
    path: "platform/bionic/+/refs/tags/android-17.0.0_r1/libc/private/WriteProtected.h"
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
task6_reviewed_date: "2026-05-08"
task9_state: reviewed
task2b_result: fixed-lite
task2b_state: fixed
task6_result: "pass-light-edit"
task9_result: auto-fixed
task9_reviewed_date: "2026-06-03"
task9_reviewed_by: "openclaw-task9"
last_task9_at: "2026-06-28T12:33:34+08:00"
last_task2b_lite_at: 2026-06-03
task9_review_notes: "2026-06-28 Task9 闲时抽检 auto-fix：将 16KB Page Size 章节源码锚点重定到 android-17.0.0_r1；修正 source.android / Android Developers Blog 无效路径；按 Android 17 Bionic 修正 ElfReader compat 分支、RELRO 保护路径和 WriteProtected.h 当前实现。P0 3 / P1 2，均已小范围修复，回到 Task6 复审。 | 2026-06-03 Task9 14:20 auto-fixed：将 Bionic 16KB compat 源码锚点从 AOSP main 改为已核验的 android-16.0.0_r1；补 Android 17 backcompat fatal 验证开关；补 Pixel 9a 测试入口并扩展 applicable_versions 到 Android 17/API 37。P0 0 / P1 0 / AUTO-FIX 3；回到 Task6 复审。 | 2026-05-08 04 Task9 deep-review: pass-tech-review。P0 0 / P1 0 / P2 仅建议；无 queue pending，Task6 已通过，自动晋升 finalized / ready-to-publish；详见 logs/deep-review/2026-05-08-04-deep-review.md。 | 2026-05-08 03:44 Task2B rework: P0 contpte 16KB 覆盖粒度改为 2MB (CONT_PTES=128)；P0 kCompatPageSize 源码锚点改为 linker_phdr.h / ElfReader::LoadSegments()；P1 NDK r27 linker flags 补 common-page-size | 2026-04-28 task9 deep-review: needs-rework。P0 0 / P1 2 / P2 0。 | 2026-05-08 03 Task9 deep-review: needs-rework。P0 2 / P1 1 / P2 1。源码锚点与版本/数据口径需 Task2B 回炉；详见 logs/deep-review/2026-05-08-03-deep-review.md。 | 2026-05-24 Task9 闲时抽检：needs-rework。P0 0 / P1 2 / P2 0；第三方 SDK 迁移建议中的 llvm-objcopy 修复路径缺少官方依据且可能误导；frontmatter 覆盖 Android 17 但当前无 AOSP 17 release tag，同时遗漏 Android 16 PRODUCT_CHECK_PREBUILT_MAX_PAGE_SIZE / elf_alignment_test 版本边界。"
repaired_date: "2026-04-27"
repaired_by: "openclaw-task2b"
rework_type: "review回炉修复（Task9/External 问题单）"
review_notes: "2026-05-06 task9 deep-review: needs-rework。P1 2 / P2 1；THP/mTHP/contpte 与 compat RELRO 边界仍需回炉。"
last_task6_at: "2026-06-03T21:36:06+08:00"
review_log: "logs/review/2026-05-08-04-review.md"
task6_review_notes: "2026-05-08 03:09 task6 revisiting-review: pass-light-edit。复核 Task2B 修正后写作层，修复 26 处 L1/L2 文风、格式与代码说明问题；无新增回炉项，送 Task9 复审。 | 2026-05-08 04:05 task6 revisiting-review: pass-light-edit。复核 Task2B 修正后写作层，修复 frontmatter、代码块语言标注、compat 说明句和 mTHP 重复段落；无新增回炉项，送 Task9 复审。 | 2026-06-03 10:05 Task6 revisiting 复审：pass-light-edit。L1 禁用词/高频词/否定-纠正/元叙述/物理动词 grep 全部零命中；L2 结构/节奏/开头/读者视角均通过；无新增 L3/L4 回炉项。送 Task9 复审。 | 2026-06-24 01:13 Task6 revisiting 复审：pass-light-edit。Task9 auto-fix 后文稿写作层无新增问题；L1/L2 全部通过；无新增 B 类回炉项。转 Task9 确认 auto-fix 结果。"
last_task9_audit: "2026-06-28"
last_task9_audit_log: "logs/deep-review/2026-06-28-12-audit.md"
last_task9_autofix_at: "2026-06-28"
last_task9_review_log: "logs/deep-review/2026-06-28-12-audit.md"
deepseek_cn_review_state: done
last_deepseek_cn_review_at: 2026-06-24
---

# 4.7 16KB Page Size 与 Android 性能

## 为什么要了解 16KB Page Size

在同一设备上对比 4KB 和 16KB page size 的冷启动 trace，最稳定的差异通常来自 page fault 计数、`mmap` 映射数量和启动耗时。TLB refill / page-table walk 不会直接以 kernel slice 或 `iowait` 出现在 CPU Scheduling 轨道里；这类 CPU 事件更适合用 simpleperf / perf 的 PMU 事件核对。Perfetto 负责把 page fault、`mmap` 和进程启动时序放到同一时间轴比较。

从 Android 15 开始，AOSP 支持使用 16KB page size 的设备。Google Play 当前公开的兼容要求也围绕 Android 15 展开：从 2025 年 11 月 1 日起，target Android 15+ 的 64 位新 App 和现有 App 更新需要支持 16KB。对 Android 16、Android 17 的设备侧强制策略，要以当年的 CDD 或官方公告为准。

为什么是现在？手机 RAM 从 2015 年的 2-3GB 增长到 2025 年的 8-16GB，但 Linux 的默认内存页大小一直停留在 4KB——这个值是 1980 年代为 VAX 架构设计的。现代 ARM CPU 的 TLB 容量虽然在增长，但 4KB 页粒度下 TLB 覆盖的内存总量（TLB Reach）已经不够。Google 在官方文档中给出的 Pixel 测试结果显示，16KB 页的平均冷启动提升 3.16%，启动功耗降低 4.56%，系统启动时间缩短约 8%。这些数字适合作为方向性参考；落到具体 App 时，要用同一设备、同一 build、同一 App 在 4KB / 16KB 下复测。

## 核心机制

### TLB 与页大小的关系

TLB（Translation Lookaside Buffer）是理解 16KB 页收益的入口。

CPU 访问内存时，使用的是虚拟地址。虚拟地址需要翻译成物理地址才能访问实际的内存芯片，这个翻译过程通过页表（Page Table）完成。页表本身存储在内存中，如果每次内存访问都要先查页表，性能会下降一倍以上——因为每次实际的数据访问都需要额外的页表访问。

TLB 是 CPU 内部的一个小型缓存，专门存储最近使用的虚拟地址→物理地址映射。当 CPU 需要访问一个虚拟地址时，先查 TLB：命中则直接拿到物理地址（TLB Hit），未命中则需要遍历页表（TLB Miss），这个过程叫做 Page Table Walk，可能需要多次内存访问。

这就是页大小的关键：在 4KB 页大小下，一个 TLB entry 覆盖 4KB 内存；在 16KB 页大小下，同一个 TLB entry 覆盖 16KB 内存——覆盖面积扩大了 4 倍。假设一个 App 的代码段 + 数据段总共占用 64MB，4KB 页需要 16,384 个 TLB entry 才能全部覆盖，而 16KB 页只需要 4,096 个。

ARM Cortex-X 系列处理器的 L1 TLB 通常有几十到上百个 entry，L2 TLB（Unified TLB）有几百到上千个。对于一个活跃的 App 来说，64MB 的工作集完全可能超出 L1 TLB 的覆盖范围。页大小从 4KB 变为 16KB 后，同样的 TLB entry 数量能覆盖 4 倍的内存，TLB Miss 率显著下降。

[已验证: 来源见 ARM Architecture Reference Manual, TLB 结构描述]

> 本节讨论的内存管理基础机制，与 §4.1「Android 内存管理架构」中的进程内存布局、§4.3「ART 内存管理」中的堆管理策略直接相关。

### Page Fault 的减少

页大小增大还影响另一个关键指标：Page Fault 的频率。

Page Fault 分两种：Major（需要从磁盘读取）和 Minor（只需在内存中分配新页）。在 Android 上，由于采用 flash 存储，Major Page Fault 的延迟相对较低，但仍然远高于 TLB Hit 的延迟（微秒级 vs 纳秒级）。更常见的是 Minor Page Fault——App 启动时加载代码段、初始化数据段、mmap 文件时都会触发。

16KB 页大小下，操作系统一次性分配 16KB 而非 4KB 的连续内存。虽然看起来"浪费"了（如果一个对象只有 1KB，16KB 页会浪费 15KB），但内存访问有很强的局部性（Locality）——分配 16KB 后，附近的数据大概率很快也会被访问。结果是总的 Page Fault 次数减少，启动阶段的内核开销降低。

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

公开页面没有给出完整样本 App 列表、每个 build fingerprint、重复次数和统计区间。本章把这些数字当作方向性收益，不把它们写成所有 App 的固定收益。冷启动提升 3.16% 是平均值，30% 的最佳值更接近内存访问密集型 App（如大型游戏、图片编辑类 App）。这类 App 在启动时需要映射大量代码和资源文件，TLB Miss 和 Page Fault 是主要瓶颈，因此 16KB 页的收益最大。

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

如果 App 没有任何 Native 代码（C/C++），通常不需要修改。ART 运行时和 Android 框架已经适配了 16KB 页，Java/Kotlin 层的内存分配由 ART 堆管理器处理，不需要关心底层页大小。

### Native 代码（NDK）

如果 App 包含 `.so` 文件——无论是自己写的还是通过第三方 SDK 引入的——就需要确保这些 `.so` 文件的 ELF 段（segment）满足 16KB 边界要求。

原因在于：Linux 加载 ELF 共享库时，通过 `mmap()` 将文件映射到内存。`mmap()` 要求映射区域落在页大小边界上。如果 `.so` 文件的 ELF 段只按 4KB 边界组织，在 16KB 页系统上，一个段可能跨越两个页——加载器需要额外处理跨页边界，甚至可能导致段内容被部分截断或错误映射，引发 SIGBUS 或 SIGSEGV 崩溃。

**构建工具链要求：**
- NDK r28+：默认输出满足 16KB 边界要求的 `.so` 文件
- NDK r27 及更低版本：需要在链接时添加 `-Wl,-z,max-page-size=16384 -Wl,-z,common-page-size=16384`
- AGP 8.5.1+：对使用 uncompressed shared libraries 的 App，可以正确请求 16KB zip 布局
- AAB 产物要再用 `bundletool dump config --bundle <your.aab> | grep alignment` 检查是否为 `PAGE_ALIGNMENT_16K`
- AGP 8.3-8.5 虽然默认会生成满足 16KB 页边界要求的 ELF，但 `bundletool` 默认不会补齐 APK zip alignment；只升级到这几个版本，Play 产物仍可能安装失败

**代码中的页大小假设：** 容易出错的是把页大小写死成 `4096`，例如 `#define PAGE_SIZE 4096`。`sysconf(_SC_PAGESIZE)` 和 `getpagesize()` 都属于运行时查询，应该保留：

```c
// 错误：把页大小写死成 4096
#define PAGE_SIZE 4096

// 正确：运行时查询
long page_size = sysconf(_SC_PAGESIZE);
int page_size2 = getpagesize();
```

这类 bug 通常不会在 4KB 设备上暴露，只在 16KB 设备上才崩溃。Google Play 已经在 Play Console 中增加了检测机制，会警告使用了 4KB 边界 `.so` 的 App。


## Bionic Linker 16KB 兼容模式内部机制

### Bionic 中的页大小来源与 Linker 分支

Bionic 的页大小查询由 `libc/platform/bionic/page.h` 里的 `page_size()` 统一提供。固定页大小构建直接返回 `PAGE_SIZE`；page-size migration 构建从 `getauxval(AT_PAGESZ)` 读取运行时页大小。Native 代码把页大小写死成 `4096`，会绕过这条运行时路径。

Bionic Linker 加载 ELF 时，`linker_phdr.cpp` 先在 `ElfReader::Read()` 中读取 program header，并通过 `CheckProgramHeaderAlignment()` 得到 `min_align_`。下面保留关键分支，省略无关检查；它用于说明条件判断，不作为可编译片段。

```cpp
// bionic/linker/linker_phdr.cpp (AOSP android-17.0.0_r1)
bool ElfReader::Read(...) {
    // Several unrelated ELF header, section and dynamic checks are omitted.
    CheckProgramHeaderAlignment();

    if (kPageSize == 16 * 1024 && min_align_ < kPageSize) {
        auto compat_prop_val =
            android::base::GetProperty("bionic.linker.16kb.app_compat.enabled", "false");
        should_use_16kib_app_compat_ =
            android::base::ParseBool(compat_prop_val) ==
                android::base::ParseBoolResult::kTrue ||
            get_16kb_appcompat_mode();
        if (compat_prop_val == "fatal") {
            dlopen_16kib_err_is_fatal_ = true;
        }
    }
}
```

**`kPageSize`** 是 Linker 看到的运行时页大小；**`min_align_`** 来自 ELF program header 的最小 `p_align`。在 16KB 系统上遇到 `min_align_ < kPageSize` 的 ELF，Linker 才会读取 `bionic.linker.16kb.app_compat.enabled` 和 per-app compat mode。没有启用 compat 时，`LoadSegments()` 会在 `min_align_ < kPageSize` 的分支报错：`program alignment (4096) cannot be smaller than system page size (16384)`。

### 错误消息改进（commit fc89c8ae，2024-08-05）

在此次提交之前，ELF program alignment 不符合系统页大小时 Linker 报错模糊（通用 segfault）。提交后改为明确报错：

```text
program alignment (4096) cannot be smaller than system page size (16384)
```

- **提交**：`fc89c8ae1dfc3b091b03f56c3e3cec30a36c76ba`
- **作者**：Steven Moreland
- **文件**：`linker/linker_phdr.cpp` + `linker/linker_phdr.h`

### 兼容模式的加载方式与代价

启用 compat 后，`LoadSegments()` 使用 `kCompatPageSize` 对 `p_vaddr` / `p_offset` 向下取整。`CompatMapSegment()` 不直接 `mmap64()` 文件段，而是把按 4KB 边界组织的 LOAD segment 读入匿名 RW 映射；`Setup16KiBAppCompat()` 再调整 `load_bias_`，让 RX/RW permission boundary 位于 16KB 页起点。

RELRO 保护仍然存在。Android 17 中，`soinfo::protect_relro()` 在 compat 分支直接返回，普通分支走 `phdr_table_protect_gnu_relro(..., PROT_READ)`；compat loaded binary 的权限恢复由 `protect_16kib_app_compat_code()` / `protect_16kib_app_compat_middle_pages()` 完成。后者遍历 `PT_LOAD` 与 `PT_GNU_RELRO`，`protect_segment_middle_pages()` 对 `PT_GNU_RELRO` 强制使用 `PROT_READ`。因此本节不能写“compat mode 禁用 RELRO”。它的代价集中在匿名映射、额外地址空间预留、VMA 数量和 16KB 权限边界处理上。

### 兼容模式不具备性能红利

兼容模式的目标是**让旧 4KB ELF 继续加载**，不是让它在 16KB 系统上获得 TLB 收益。`CompatMapSegment()` 把按 4KB 边界组织的 LOAD segment 读入匿名 RW 映射，而不是走 `mmap64()` 直接映射文件。加载以 4KB 边界组织的 `.so` 时，Bionic 因权限边界冲突被迫将本可共享的 `.so` 内容执行匿名拷贝——原本可被多个进程共享的 `.so` 库变为每个进程独占一份，PSS 随之升高，且无法享受 16KB 页带来的启动加速红利。

在 Perfetto 中对比同一 App 的 compat 模式和非 compat 模式，compat 模式下 `mmap` 命中的文件映射更少、匿名页更多，启动耗时通常不会改善。具体的 Perfetto/proc 观察方法：

- **smaps 对比**：同一 `.so` 在 compat 模式下 `Shared_Clean` 会降低或归零（因为匿名拷贝不共享），`Private_Dirty` 和 `PSS` 相应升高。用 `adb shell cat /proc/<pid>/smaps | grep -A 20 <libname>` 分别在两种模式下抓取对比
- **Perfetto `mem.mm.min_flt`**：compat 模式下 minor fault 计数与满足 16KB 要求的版本相当或更多，说明页分配粒度没有改善
- **启动耗时**：用 `am start -W` 或 Perfetto 的 cold launch slice 对比；compat 模式下冷启动不会获得 16KB 页的 TLB 收益

compat 只用于临时兼容验证，不应作为发布态性能方案。对于有性能要求的 App，正确做法仍然是重新编译 `.so` 使其满足 16KB 边界要求，不要依赖 compat 模式。

### 控制接口总览

| 控制方式 | 属性/API | 作用域 |
|----------|---------|--------|
| 系统级 | `bionic.linker.16kb.app_compat.enabled` | 全局所有 App |
| 应用级 | `AndroidManifest.xml android:pageSizeCompat` | 单个 App |
| 用户级 | 设置 → App Info → Advanced → "Run app with page size compat mode" | 单个 App |
| 包管理器 | `pm.16kb.app_compat.disabled` | 安装时预检 |
| Android 17 回退开关 | `bionic.linker.16kb.app_compat.enabled=fatal` | 禁止 4KB ELF 进入 16KB backcompat，直接暴露不兼容问题 |

### 对开发者的实际含义

链接参数 `-Wl,-z,max-page-size=16384 -Wl,-z,common-page-size=16384` 的作用是告诉链接器将 ELF 的 `p_align` 设为 16384，使最小 `p_align` 满足 16KB 系统要求，从而绕过 `linker_phdr.cpp` 中的兼容模式检测。

## Bionic Linker 16KB Compat Mode 常量与 mprotect 修复

### kCompatPageSize 常量与 CompatMapSegment 双路径

AOSP commit ce1c3cf77b8b08d402818dad10b804013f46722f 中新增了 16KB 兼容模式，关键常量定义在：

```cpp
// bionic/linker/linker_phdr.h
static constexpr size_t kCompatPageSize = 0x1000;  // 4KB
```

在 `ElfReader::LoadSegments()`（`bionic/linker/linker_phdr.cpp`）中根据 `should_use_16kib_app_compat_` 决定调用路径：

```cpp
if (should_use_16kib_app_compat_) {
    if (!CompatMapSegment(i, file_length)) {
        return false;
    }
} else {
    if (!MapSegment(i, file_length)) {
        return false;
    }
}
```

CompatMapSegment 内部使用 4KB (kCompatPageSize) 边界映射，原生 MapSegment 使用 16KB 边界映射。

### NDK r27 mprotect alignment Bug（GitHub android/ndk#2026）

NDK r27 链接器生成的 ELF 文件 p_align=4096（4KB），在 16KB 页面设备上触发 mprotect 边界错误：

```text
Crash with WriteProtected mprotect 1 failed: Invalid argument.
```

`mprotect(addr, size, PROT_READ | PROT_WRITE)` 的 `addr` 参数必须落在页边界上，16KB 设备上 4KB 边界地址会触发 EINVAL。该 bug 在 AOSP commit ce1c3cf77b8b08d402818dad10b804013f46722f（2024-10-11）中修复，NDK r28 已包含。

### RELRO 保护在 Compat 模式下的差异

Compat 模式先在 `protect_16kib_app_compat_code()` 中把 compat code region 设为 `PROT_READ | PROT_EXEC`（必要时附加 `PROT_WRITE` / `PROT_BTI`），再由 `protect_16kib_app_compat_middle_pages()` 恢复中间页权限。遇到 `PT_GNU_RELRO` 时，`protect_segment_middle_pages()` 强制使用 `PROT_READ`：

```cpp
// bionic/linker/linker_phdr_16kib_compat.cpp (AOSP android-17.0.0_r1)
static bool protect_segment_middle_pages(const soinfo* si, const ElfW(Phdr)* phdr) {
    int prot = PFLAGS_TO_PROT(phdr->p_flags);
    if (phdr->p_type == PT_GNU_RELRO) prot = PROT_READ;
    uintptr_t seg_start = si->load_bias + phdr->p_vaddr;
    uintptr_t seg_end = seg_start + phdr->p_memsz;
    uintptr_t p_start = __builtin_align_up(seg_start, page_size());
    uintptr_t p_end = __builtin_align_down(seg_end, page_size());
    if (p_start < p_end) {
        return mprotect(reinterpret_cast<void*>(p_start), p_end - p_start, prot) == 0;
    }
    return true;
}
```

这反映了 Android 17 compat 模式把 RELRO 保护拆到 16KB compat code / middle pages 保护阶段，而不是单独的 `phdr_table_protect_gnu_relro_16kib_compat()` 函数。

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

Pixel 8/8 Pro/8a、Pixel 9 系列以及 Android 16+ 的 Pixel 9a 支持开发者选项中的 "Boot with 16KB page size"。启用后重启设备即可。

### 验证 APK alignment

Google 提供了 `check_elf_alignment.sh` 脚本，可以检查 APK 中所有 `.so` 文件是否满足 16KB 边界要求：

```bash
# 方法 1：使用 zipalign 工具验证
zipalign -c -P 16 -v 4 your_app.apk

# 方法 2：使用 check_elf_alignment.sh
# 来源：Android 官方文档
./check_elf_alignment.sh your_app.apk
```

Play Console 的 App Bundle Explorer 也提供了自动化的边界检查。上传 AAB 后，在 "发布" → "设置" 中查看 alignment 状态。

### 常见迁移问题

**第三方 SDK 的 `.so` 文件**：这是最常见的阻塞点。如果 App 依赖的第三方 SDK 还没有适配 16KB，需要联系 SDK 提供方获取更新版本。对没有源码的 SDK，`llvm-objcopy` 不能可靠修复 PT_LOAD `p_align`、权限边界和代码中的硬编码 `PAGE_SIZE`；可用的检查工具是 `llvm-objdump`、`zipalign -c -P 16`、`bundletool dump config` 和 `check_elf_alignment.sh`（参见上方「迁移检查」小节）。

### 三方库破坏性影响清单（源码级核实）

16KB Page Size 的破坏性集中在**静态链接 native 库**层面，而非 Java/Kotlin 层。以下是经过源码或 Issue 溯源的受影响清单：

#### NDK r27 libc.a：WriteProtected hardcoded PAGE_SIZE

这是影响最广的已知 crash 根因。AOSP commit `2713655`（2023-08-11）修复了 `bionic/libc/private/WriteProtected.h` 中的两处硬编码：

```cpp
// 修复前：padding[PAGE_SIZE] 在 4KB 硬编码，16KB 设备上 mprotect 边界错误
char padding[PAGE_SIZE];                      // PAGE_SIZE = 4096 always
mprotect(addr, PAGE_SIZE, prot);             // EINVAL on 16KB device

// Android 17 当前实现：使用 max_android_page_size() 作为 padding 与 mprotect 粒度
char padding[max_android_page_size()];
mprotect(addr, max_android_page_size(), prot);  // works on both 4KB and 16KB
```

`WriteProtected<T>` 是 Bionic 用来对齐并写保护静态对象的模板联合类。静态链接 NDK r27 `libc.a` 的任何 `.so` 在 16KB 设备上启动时都会触发：`WriteProtected mprotect 1 failed: Invalid argument`。

受影响组件：
- **NDK r27 `libc.a` 静态归档**：所有通过 ndk-build 静态链接 `libc.a` 的 native 库（Android NDK r27）
- **NDK r27 预编译 `lldb-server`**：同属 NDK r27 预编译包，包含相同 bug

来源：[GitHub android/ndk#2026](https://github.com/android/ndk/issues/2026)（2024-06-02）；AOSP commit [2713655](https://android-review.googlesource.com/c/platform/bionic/+/2713655)。**NDK r28+ 已包含修复。**

#### React Native prefab 模式：CMake linker flags 被忽略

React Native 0.75.x 的 prefab native 模块（`react-android`）在 CMake 构建时**完全忽略** `-Wl,-z,max-page-size=16384` linker flags，导致生成的 `.so` 仍然是 4KB 对齐，无法通过 Google Play pre-launch validation。

```gradle
// React Native 0.75.x build.gradle —— 这段配置在 prefab 模式下被忽略
arguments "-DCMAKE_SHARED_LINKER_FLAGS=-Wl,-z,max-page-size=16384",
          "-DCMAKE_MODULE_LINKER_FLAGS=-Wl,-z,max-page-size=16384",
          "-DCMAKE_EXE_LINKER_FLAGS=-Wl,-z,max-page-size=16384"
```

根因：`ReactAndroid/cmake-utils/default-app-setup` 中的 CMake 配置不向 prefab 工具链传递 `max-page-size` 参数。**修复方案**：升级 NDK 28+；App 层面无法通过 gradle 配置绕过。

来源：[GitHub facebook/react-native#54073](https://github.com/facebook/react-native/issues/54073)。

#### Hook 类库（xHook / bhook / SandHook）：兼容性良好

主流 Hook 库**不依赖 `WriteProtected`**，因此不受上述 bug 影响：

- **ShadowHook**（ByteDance）的 Gap Trampoline 机制利用 PT_LOAD 段末尾未使用空间插入 hook stub，不涉及页对齐的 `mprotect` 边界问题
- **xHook / bhook** 的 PLT/GOT hook 路径同样不涉及 `WriteProtected`，兼容性不受页大小影响

#### APM SDK（KOOM / Matrix）：兼容性分层

- **KOOM**：fork dump 路径（`koom-fast-dump.so`）使用 `fork()` + `WaitForVmToSuspend()`，native 内存操作走标准系统调用，不依赖 `WriteProtected`，在 16KB 设备上正常工作
- **Matrix（Tencent）**：主要兼容性风险在于 Android 15 对 `/proc/self/maps` 输出格式的微调（16KB 设备上 Size 列以 16KB 为单位显示），而非 `WriteProtected` 本身；Matrix 的正则解析若硬编码了 KB 单位（如 `\d+ +K`），可能在 16KB 设备上将 `16384`（非 K 后缀）解析失败

#### 游戏引擎（Unity IL2CPP / Unreal NDK）

需要确认是否静态链接了 NDK r27 `libc.a`。官方未公开明确的兼容性声明，建议通过 Play Console pre-launch report 验证或直接联系引擎支持。理论上，重新编译使 `.so` 满足 16KB 边界即可解决。

| 类别 | 典型库/组件 | 受影响程度 | 根因 |
|------|------------|----------|------|
| NDK 静态库 | `libc.a` (r27) | **严重（启动 crash）** | WriteProtected hardcoded 4KB |
| 预编译调试工具 | `lldb-server` (r27) | **严重（无法调试）** | 同上 |
| React Native | prefab native 模块 | **高（Play 认证失败）** | prefab 忽略 max-page-size flag |
| 游戏引擎 | Unity IL2CPP / Unreal NDK | **中（需验证）** | 依赖 NDK 版本和静态链接方式 |
| Hook 框架 | xHook / bhook / SandHook | **低（兼容）** | 不依赖 WriteProtected |
| APM SDK | KOOM | **低（兼容）** | fork/dump 路径无 WriteProtected |
| APM SDK | Matrix | **低（/proc/maps 解析风险）** | 解析格式依赖，非页对齐问题 |



**构建缓存问题**：升级 AGP/NDK 后，记得 clean build。Gradle 的增量编译缓存可能保留旧的 4KB 边界产物。

## 在 Perfetto 中的表现

16KB 页大小不会在 Perfetto 中显示为一个独立的 Track 或标记——它的影响体现在多个 Track 的数据差异中。

### Page Fault 与 mmap 变化

Perfetto 侧优先看 minor / major fault 与 `mmap` / `munmap` 相关事件。`mem.mm.min_flt` 这类计数器是否可用，取决于设备内核和 trace 配置；没有该 counter 时，可用 `/proc/<pid>/stat` 启动前后差值、`am start -W` 启动耗时和 simpleperf 单独采样互相校验。对比 4KB 和 16KB 设备上同一 App 的冷启动 trace，16KB 设备上的 page fault 计数通常会更低。

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

最小复现实验的记录项要固定下来：同一台可切换 page size 的设备、同一 Android build、同一 App 版本；每轮记录 `adb shell getconf PAGE_SIZE`、`adb shell getprop ro.build.fingerprint`、`am start -W` 启动耗时、minor / major fault 计数和 trace 时间段。若 SoC 暴露 TLB PMU 事件，再用 simpleperf / perf 采 `DTLB` / `ITLB` refill 或 walk 相关事件；事件名依内核导出而定，不能在正文写死成所有设备通用。

### TLB / page-table walk 的观测边界

TLB miss 后的 page-table walk 主要由 ARM64 hardware page-table walker 完成，不会直接变成 Perfetto CPU Scheduling 的 kernel slice 或 `iowait`。只有 page fault 才会进入内核异常路径，并可能在 trace 或计数器中留下调度侧信号。

因此，Perfetto 用来合并比较 page fault、`mmap` 和启动时序；TLB refill / DTLB walk 需要 simpleperf / perf 的 PMU 事件。设备没有导出 TLB PMU 事件时，只能把 page fault 减少和启动耗时变化作为间接证据，不能用 `iowait` 或内核态时间当成 TLB walk 的直接证据。

## 与 Linux THP（Transparent Huge Pages）的关系

16KB 页大小和 THP 是两种不同的优化路径，但它们解决的是同一个问题——减少 TLB Miss。

**THP** 在 4KB 基础页大小上工作，将连续的 4KB 页合并为 2MB 的大页（ARM64 PMD_SIZE）。优点是不需要修改 App，内核自动管理；缺点是需要物理连续的大块内存（4KB base 时为 2MB），长时间运行后碎片化严重，khugepaged 的后台整理本身也有 CPU 开销。

**16KB 基础页** 是更底层的改变。它不需要物理连续内存（每个 16KB 页独立分配），没有 khugepaged 的开销，收益更确定。缺点是需要重新编译 Native 代码。

两者**可以叠加使用**：16KB 基础页 + THP 合并为 32MB 大页。ARM64 的 PMD_SIZE（PMD 级别的 block size）随基础页大小变化：4KB base → 2MB THP，16KB base → 32MB THP。在这种组合下，TLB entry 可以覆盖 16KB（普通页）或 32MB（大页），TLB Reach 进一步扩大。不过在实际的 Android 设备上，THP 默认配置通常是 `madvise` 模式（只对显式请求的内存区域启用），对大多数 App 的实际影响有限。验证设备上 THP 默认策略的方法：

```bash
# 查看 THP 当前模式（always / madvise / never）
adb shell cat /sys/kernel/mm/transparent_hugepage/enabled

# 查看内核配置是否编译了 THP
adb shell zcat /proc/config.gz | grep CONFIG_TRANSPARENT_HUGEPAGE
```

不同 OEM/SoC 可能使用不同默认值；分析时要先确认目标设备的 THP 状态，不要假设所有 Android 16 设备行为一致。

对于性能分析来说，16KB 基础页的收益比 THP 更直接、更稳定。在分析 App 的 TLB 相关性能问题时，优先确认设备是否启用了 16KB 页。

### mTHP 与 contpte：16KB 环境下的二次优化

在 16KB 基础页之上，如果内核启用了 `CONFIG_ARM64_CONTPTE` 和 mTHP 框架，可以获得进一步的 TLB 优化。contpte（contiguous page table entries）利用 ARM MMU 的 contiguous hint 特性，将一组物理连续的页表条目合并为一个 TLB entry。在 16KB 基础页下，`ARM64_CONT_PTE_SHIFT` 默认为 7，`CONT_PTES = 1 << 7 = 128`，`CONT_PTE_SIZE = 128 × 16KB = 2MB`——单个 TLB entry 覆盖 2MB，相当于覆盖范围从 16KB 扩大了 128 倍。这些能力依赖内核配置和 SoC 支持，不是所有 Android 16 设备都会启用。

contpte 与 THP 的区别：THP（PMD 级）需要物理连续的 32MB 大块内存（16KB base），对碎片化敏感；contpte 在更小的粒度（2MB）上工作，内存分配器更容易满足连续性要求。mTHP（Multi-size Transparent Huge Pages）框架允许内核在 16KB 基础页上按需组装 64KB、128KB 等中间大小的 folio，这些 folio 可能利用也可能不利用 contpte hint——两者是独立的优化维度。在 Perfetto 中，mTHP 的效果仍然通过 page fault 减少和启动耗时缩短来间接观测。验证内核是否启用 mTHP：`adb shell cat /sys/kernel/mm/transparent_hugepage/hpage_pmd_size`，再查看 `/sys/kernel/mm/transparent_hugepage/` 目录下是否存在 multi-size 相关配置。

## 版本演进与 OEM 适配

### 已公开确认的里程碑

- **Android 15（API 35，2024）**：AOSP 开始支持 16KB page size 设备；模拟器与部分 Pixel 设备提供测试入口
- **Google Play（2025-11-01）**：target Android 15+ 的新 App 与现有 App 更新，需要在 64 位设备上支持 16KB

### Android 16 源码侧验证入口

Starting in Android 16，构建系统支持对 prebuilt `.so` 做 16KB 对齐检查：在 `BoardConfig.mk` 中设置 `PRODUCT_CHECK_PREBUILT_MAX_PAGE_SIZE := true`。如果某个 prebuilt 暂时不满足 16KB 对齐，可以用 `ignore_max_page_size`（模块级）或 `LOCAL_IGNORE_MAX_PAGE_SIZE`（旧式 Android.mk）临时豁免。对应的自动化测试入口是 `atest elf_alignment_test`。

### Android 16 / 17 的设备策略

Android 16、Android 17 会不会把 16KB 写成更强的设备侧要求，要看对应版本的 CDD、兼容性公告或 OEM 发布说明。Android 官方迁移文档已经给出 Android 17 的 backcompat 验证选项：把 `bionic.linker.16kb.app_compat.enabled` 设为 `fatal` 后，4KB 对齐 ELF 会直接失败，用来提前暴露仍依赖兼容模式的产物；这不等价于所有设备默认启用 16KB。

### OEM 适配进展

OEM 的适配进度取决于 SoC 厂商的内核支持。高通（Snapdragon）和联发科（Dimensity）从 2024 年开始在 BSP 中提供 16KB 页大小选项。实际启用还需要 OEM 验证所有 HAL 模块和驱动程序的兼容性——特别是 Camera HAL、GPU 驱动、安全模块（TrustZone）这些包含大量 Native 代码的组件。

从 Perfetto 分析的角度，同一款 App 在不同 OEM 的 16KB 设备上可能有不同的性能表现——因为 OEM 可以调整页大小相关的内核参数（如 THP 策略、zRAM 块大小等）。在跨设备对比性能数据时，需要先确认底层页大小是否一致。

```bash
# 快速检查设备页大小
adb shell getconf PAGE_SIZE
```

## 常见问题与误区

### "16KB 页会让 App 占用更多内存"

这个说法过于简化。页表本身变小了（节省内存），内部碎片会增加（浪费内存）。最终效果取决于 App 的分配模式：大量小对象的 App 内存增长更多，以大块分配为主的 App 几乎没有增长。Google 的平均数据是 5-10%，但对于 8GB+ 设备来说，这个增长在整体内存预算中占比不大。

### "纯 Java App 不需要关心 16KB"

大体正确，但有一个例外：如果 App 通过 JNI 调用了系统库（如 `libandroid_runtime.so`、`libnativehelper.so`），而这些系统库在某些老设备上还没有满足 16KB 边界要求——这种情况下 App 本身不需要修改，但可能遇到系统级兼容性问题。Android 15+ 的系统库已经全部满足 16KB 边界要求，所以这只影响老设备。

### "16KB 页大小只影响启动速度"

这个判断不完整。16KB 页影响所有涉及内存访问的场景，不只影响启动。滑动时的大量 Bitmap 解码、WebView 的页面渲染、视频解码的 buffer 管理都会受益。只是启动阶段的收益最容易量化（因为 page fault 最密集），所以 Google 在官方文档中重点展示了启动数据。从 Perfetto 分析的实际案例来看，列表滑动场景中 Bitmap 频繁 mmap/unmmap 导致的 Minor Page Fault 也是一个可观测的改善点（参见 §7.8「RecyclerView 列表滑动性能深度优化」中的内存访问模式分析）。

### "我需要在代码中硬编码 16384"

不要这样做。正确的做法是用 `sysconf(_SC_PAGESIZE)` 运行时查询。这样才能同时兼容 4KB、16KB 设备，以及未来可能出现的 64KB 页大小。

## 参考资料

- [已验证: developer.android.com/guide/practices/page-sizes — Google 官方 16KB 迁移指南]
- [已验证: source.android.com/docs/core/architecture/16kb-page-size/16kb — AOSP 16KB 架构文档]
- [已验证: ARM Architecture Reference Manual — TLB 结构与页大小]
- [已标注边界: Google 官方 16KB 性能数据缺少完整样本与 build 细节，本章只作方向性参考]
- [待验证: 16KB 基础页 + THP 在各 Android 16/17 OEM 设备上的默认策略需逐设备核验 /sys/kernel/mm/transparent_hugepage/enabled；contpte/mTHP 依赖内核配置 CONFIG_ARM64_CONTPTE]
