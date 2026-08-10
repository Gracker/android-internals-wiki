---
title: 内存相关的版本演进
chapter: '4.6'
section: '4.6'
status: finalized
applicable_versions: Android 5.0 (API 21) - Android 17 (API 37)
last_verified: '2026-06-08'
last_verified_against: AOSP android-17.0.0_r1 + Android 17/API 37 官方文档
confidence: medium
sources:
- type: official
  path: https://source.android.com/docs/core/perf/art-management
- type: official
  path: https://developer.android.com/topic/performance/graphics/manage-memory
- type: official
  path: https://source.android.com/docs/security/test/memory-safety/arm-mte
- type: official
  path: https://developer.android.com/ndk/guides/arm-mte
- type: official
  path: https://developer.android.com/reference/android/graphics/Bitmap.Config#HARDWARE
- type: official
  path: https://developer.android.com/guide/practices/page-sizes
- type: blog
  path: Cubox/Scudo内存分配器介绍-2022-01-14.md
- type: blog
  path: Cubox/【Android 15】内存分配器Scudo在这些年的优化-2024-06-14.md
- type: blog
  path: Cubox/不同版本上 Bitmap 内存分配与回收原理对比-2023-01-24.md
- type: blog
  path: Cubox/四年之后，重新审视 MTE：从硬件架构到工程落地-2025-12-18.md
- type: research
  path: intake/research-feeds/2026-03-31-11-ch04-art-allocator-evolution.md
- type: research
  path: intake/research-feeds/2026-03-31-11-ch04-art-generational-gc.md
tags:
- memory-evolution
- art
- dalvik
- gc
- bitmap
- scudo
- mte
- large-heap
- memory-limit
- version-history
related_chapters:
- '4.1'
- '4.2'
- '4.3'
- '4.4'
- '4.5'
- '2.9'
reviewed_date: '2026-06-29'
reviewed_by: openclaw-task6
polish_count: '1'
polish_date: '2026-04-07'
polish_by: task2b-polish
rework_date: '2026-06-29'
rework_by: openclaw-task2b
drafted_date: '2026-03-31'
drafted_by: openclaw-subagent
review_count: '9'
task6_state: reviewed
task6_result: pass-light-edit-v2
last_task6_at: '2026-06-29T13:16:34+08:00'
last_task6_review_log: logs/review/2026-06-29-13-review.md
task6_review_notes: '2026-06-29 Task6 复审(revisiting→reviewed)：Task9 auto-fix 后写作质检通过。L1:
  无禁用词命中；1 处否定纠正式句型在限额内。L2: 结构清晰、版本叙事连贯。无 L3/L4 回炉项。queue 有 pending 条目(时效性巡检)，不可自动晋升，送
  Task2B 处理。'
task9_state: reviewed
task9_result: auto-fixed
last_task9_at: '2026-06-29T11:34:21+08:00'
last_task2b_lite_at: '2026-06-29'
task9_reviewed_by: openclaw-task9
task9_reviewed_date: '2026-06-29'
task9_review_notes: '2026-06-29 Task9 deep-review: auto-fixed。P0/P1 本轮无未闭环项；已修正 Bionic
  16KB compat 源码锚点/函数名与 MemoryLimiter 条件启用、anon+swap 延迟 kill 边界，回到 Task6 复审。'
last_task9_review_log: logs/deep-review/2026-06-29-11-deep-review.md
last_task9_autofix_at: '2026-06-29'
deepseek_cn_review_state: done
last_deepseek_cn_review_at: '2026-06-03'
p0: '0'
p1: '0'
p2: '0'
updated_by: openclaw-task9
updated_date: '2026-06-29'
pipeline_stage: ready-to-publish
task2b_state: fixed
task2b_result: fixed
last_task2b_at: '2026-06-29T14:53:01.246869+08:00'
promoted_at: '2026-06-29T14:53:01.246869+08:00'
promotion_note: 'Auto-promoted: Task6(pass-light-edit-v2) + Task9(auto-fixed) + queue
  cleared. Freshness check concerns resolved by Task9 deep-review.'
---

# Android 内存机制的版本演进

## 先分清“版本支持”和“设备行为”

平台上限为 Android 17 / API 37 / `android-17.0.0_r1`，内核以 `android17-6.18-2026-06_r6` 为锚点。旧版本用于解释历史设备上的轨迹、OOM 与内存统计。

阅读版本演进时，要区分三类信息：

1. **公开 API 或兼容性要求**：例如 API 26 起普通 Bitmap 像素位于 Native Heap。
2. **AOSP 默认值**：例如 Android 10+ 的 CC 默认使用分代模式，但 OEM 仍能改 Collector 配置。
3. **源码已具备的可选路径**：例如 CMC、MTE、16 KB linker compat 和 Android 17 MemoryLimiter，它们还受内核能力、feature flag、系统属性或 vendor 配置影响。

把“源码中存在”直接写成“所有设备均启用”，会误判线上数据。GC 名称、page size、MTE 和 MemoryLimiter 都应在目标设备上确认。

## Android 5.0：ART 成为默认 Runtime

Android 4.4 已提供实验性的 ART，Android 5.0 将 ART 设为默认 Runtime，取代 Dalvik。变化覆盖 DEX 执行、编译产物、堆组织、对象分配和 GC。

### Dalvik 到 ART 的 GC 变化

Dalvik 不能简单概括为“每次 GC 全程停止世界（stop-the-world）”。Android 2.3 已引入并发 GC；不同 Dalvik collector、堆大小和设备会产生不同停顿。早期设备上可能出现几十毫秒甚至更长停顿，但 `50～100 ms` 不能视作固定行为。

Android 5.0 的 ART 主要使用 Concurrent Mark Sweep（CMS）系列 collector。标记工作可与应用线程并发，仍有处理 roots 等暂停阶段。CMS 通常不移动对象，前台可减少压缩停顿；碎片严重、分配失败或应用转入后台时，ART 还可以执行压缩。

CMS 搭配 RosAlloc。RosAlloc 以不同 size class 的 run 管理空闲槽位，适合非移动堆中的小对象分配。它说明 GC 算法与对象分配器要分开分析，不能把 ART 概括成“沿用 Dalvik dlmalloc 全局锁”。

### 编译策略也在继续演进

Android 5.0 强调 AOT：安装阶段通过 `dex2oat` 生成本地代码。Android 7.0 起，ART 转为 AOT、JIT、解释执行和 profile-guided compilation 的混合模式。

这段变化影响内存口径：

- AOT 产物占用磁盘映射和代码页；
- JIT 引入 code cache，并在压力下回收；
- profile 决定哪些方法在后台编译；
- Java Heap、Code、`.art/.oat/.vdex` 映射应分别观察。

“ART 使用 AOT”在 Android 5.0 的历史语境成立，用它概括 Android 17 的完整执行模式会遗漏 JIT、解释器与 profile。

### 轨迹判断

旧设备上先从 GC 日志或 Perfetto 确认 collector 名称，再判断暂停是否异常。版本号只能缩小范围，无法替代设备证据。ART 的详细堆结构见 4.3。

## Android 8.0：Bitmap 像素回到 Native Heap

Bitmap 像素数据的位置有三段历史：

| 版本 | 像素数据位置 | 主要风险 |
| --- | --- | --- |
| API 10 及更早 | Native 内存 | Java Bitmap 与 Native 像素释放时机分离 |
| API 11～25 | Dalvik/ART 管理堆 | 大图直接挤占 Java Heap |
| API 26 及以后 | Native Heap | Java Heap 指标看不到像素主体，进程压力仍存在 |

Android 8.0 的变化没有让 Bitmap “脱离内存限制”。普通 Bitmap 像素虽然位于 Native Heap，仍消耗物理内存；Android 17 的 `Bitmap` 通过 `NativeAllocationRegistry` 登记原生分配，使 ART 能感知相应压力。分配失败仍可能抛出 `OutOfMemoryError`。

### 回收路径的边界

API 26+ 的 Java `Bitmap` 持有原生对象指针，平台为原生对象与像素注册回收动作。Java 对象不可达后，运行时可以执行原生清理；具体发生时间仍受 GC 和调度影响，没有“下一次 GC 必定立即释放”的承诺。

`Bitmap.recycle()` 会立即使像素不可用，只适用于调用方能证明 Bitmap 已无人使用的场景。现代图片库通常管理缓存、复用池和引用所有权，业务代码不应回收由库持有的资源。

### Hardware Bitmap

API 26 同时引入 `Bitmap.Config.HARDWARE`。像素由图形缓冲区管理，Bitmap 保持不可变，适合硬件加速 UI 的只读绘制。CPU 和 GPU 通常共享设备物理内存，所以“放进 GPU memory”不等于不占 RAM。

不同设备会把这部分内存记在 Graphics、GL、memtrack、dmabuf 或其他驱动口径。Java 堆稳定而 Graphics/dmabuf 持续增长时，应检查 Bitmap、Surface、视频缓冲区和图形资源所有权。

## Android 8.0～10：CC 与分代 CC

### Android 8.0：Concurrent Copying 成为默认方案

Android 8.0 默认启用 Concurrent Copying（CC）。它使用 read barrier 协调对象移动，以 RegionSpace 和 RegionTLAB 支持紧凑堆与线程本地 bump-pointer 分配。应用线程读取引用时，read barrier 保证拿到对象迁移后的正确位置。

AOSP 的 Android 8.0 ART 改进文档给出过一组平台基准：

| 指标 | AOSP 报告口径 |
| --- | --- |
| Heap | 相比 Android 7.0 平均减小 32% |
| 分配 | 相比 Android 7.0 快 70% |
| 暂停 | H2 benchmark 中缩短 85% |

这些数字解释设计收益，不能套用到任意应用和设备。对象存活率、堆大小、CPU、系统负载和 OEM 配置都会改变结果。

### Android 10：CC 默认进入分代模式

Android 10+ 的 CC 默认使用 generational mode。Young collection 优先处理最近分配区域，并借助 card table/remembered information 处理老对象指向年轻对象的引用。这样可以用较少工作回收大量短命对象，延后全堆回收。

“Young GC 暂停 1～3 ms”一类数字只能视为特定测量值。官方 GC 文档描述的是短暂停顿及其相对堆大小的特性，没有向应用承诺固定毫秒范围。同一个进程在不同设备、堆状态和线程数量下会得到不同结果。

以下推断也应避免：

- Young GC 出现频繁就等于泄漏；
- Full GC 出现一次就等于内存不足；
- 1～3 ms 一定不会掉帧；
- Android 10 设备必定使用 OEM 未修改的默认配置。

分配 Trace、GC cause、回收前后字节数、FrameTimeline 和业务场景要一起看。

## Android 14～17：CMC 与 UFFD 路径

`art/runtime/gc/collector/mark_compact.cc` 在 Android 14 源码中已经包含基于 `userfaultfd` 的 Mark-Compact 路径。源码存在只说明平台具备实现；具体设备是否选择 CMC，还取决于系统属性、内核 UFFD 能力和 ART 配置。

CMC 在短暂停顿内准备对象移动和引用更新，并用 UFFD 协调后续页级压缩。应用线程触碰尚未处理的页时，fault 可交给 ART 的处理路径。若设备不满足 UFFD 条件，ART 还保留其他 collector 或 stop-the-world fallback。

### Android 17 的分代 CMC

`android-17.0.0_r1` 中可以直接核验：

- `YoungMarkCompact` 以 sticky GC 类型暴露 young collection；
- 具体 young GC 工作复用主 `MarkCompact` 实例，避免复制大块 GC 数据结构；
- 分代状态维护 young、mid、old 三代；
- 对象需要经过 young 和 mid 阶段后再晋升 old，降低过早晋升；
- old-to-young 引用仍需要 card/remembered information，young GC 不能忽略老年代引用；
- `ShouldUseGenerationalGC()` 与 `use_generational_cmc` flag、`use_generational_gc` 属性共同决定分代选择；
- CMC 还受 `ShouldUseUserfaultfd()`、内核能力和设备属性约束。

“Android 17 使用 Generational CMC”表示 Android 17 AOSP 提供了主要新能力与默认候选路径，仍需在设备上确认。可以从进程启动日志中的 `Using generational ... GC`、Perfetto GC 切片和系统属性交叉判断。

## Android 11+：标准 Native allocator 转向 Scudo

Android 11 起，Scudo 服务于标准 Native heap 分配；低内存设备仍可使用 jemalloc。`malloc/free` 与通常的 `new/delete` 会进入该进程选定的 allocator，自定义 allocator、专用 arena、GraphicBuffer 和驱动分配不一定经过 Scudo。

### Scudo 提供什么

Scudo 是 hardened allocator，目标是在可接受成本下增强 heap corruption 防护。它通常包含：

- Primary allocator：按 size class 处理常见小块；
- Secondary allocator：以映射方式处理较大分配；
- thread-local 或共享缓存：减少常见分配路径的竞争；
- chunk header checksum 与状态检查；
- 可配置 quarantine：延迟复用已释放 chunk，增加发现 use-after-free 的机会。

Scudo 发现损坏或可疑释放后通常终止进程并输出诊断。它属于安全缓解与快速失败机制，覆盖能力弱于 ASan/HWASan 这类完整插桩工具。

### 配置决定检测边界

不要把所有检查写成无条件保证。以官方当前默认选项为例：

- quarantine 的大小随 32/64 位配置而异，并非固定禁用；
- `DeallocationTypeMismatch` 默认关闭，`malloc/delete` 不匹配未必由默认 Scudo 报出；
- custom allocator 不受 Scudo chunk header 保护；
- 一个未崩溃的版本仍可能存在未命中的 UAF、越界或泄漏。

Native 问题需要结合 tombstone、HWASan/ASan、GWP-ASan、MTE 和 heapprofd。4.5 给出了工具选择。

## Java 堆与 `largeHeap` 的版本边界

### heap class 是设备配置

`ActivityManager.getMemoryClass()` 返回当前设备近似的普通应用 memory class，`getLargeMemoryClass()` 返回大堆对应值。两者单位为 MiB，值可能相同，也可能差异很大。

Android 没有提供“2 GB RAM 对应 192 MiB、8 GB RAM 对应 512 MiB”这样的跨设备固定表。设备可通过 `dalvik.vm.heapstartsize`、`heapgrowthlimit`、`heapsize`、`heaptargetutilization` 等属性配置 ART；32/64 位、低内存设备和 OEM 选择都会影响结果。

以下命令用于检查具体设备：

```bash
adb shell getprop dalvik.vm.heapstartsize
adb shell getprop dalvik.vm.heapgrowthlimit
adb shell getprop dalvik.vm.heapsize
adb shell getprop dalvik.vm.heaptargetutilization
adb shell dumpsys meminfo com.example.app
```

前三项描述堆的起点、增长限制和最大配置，最末项提供当前进程 Java、Native、Graphics 等快照。属性值仍要结合进程位数和 Runtime 日志解释。

### `largeHeap` 只改变受管理堆等级

`android:largeHeap="true"` 请求更大的 Dalvik/ART Heap。官方文档明确指出：

- 多数应用不需要；
- 可用增量没有固定保证；
- 内存受限设备上可能与普通 memory class 相同；
- 同一进程内共享的应用要保持一致配置。

它不会扩大 Native Heap、Graphics、dmabuf 或 FD 的独立额度，也不会提升进程的 `oom_score_adj`。更大的存活对象图还可能增加 GC 工作量，但暂停变化不能按堆容量线性推算。

### Java OOM 与进程被杀是两条路径

受管理堆到达增长上限且无法满足分配时，应用可能收到 Java `OutOfMemoryError`。系统整体内存紧张时，lmkd 会按进程优先级与内存压力选 victim；进程可能没有先发生 Java OOM。

API 26+ 的 Bitmap、Native heap 和 Graphics 让“Java 堆还空着、进程仍被终止”更常见。Android 17 的 MemoryLimiter per-process cgroup 路径，见后文。

## MTE：Android 13 起在部分设备可用

Arm Memory Tagging Extension（MTE）为指针和内存 granule 分配 tag。每个 16 字节 granule 对应 4 bit allocation tag，指针高位携带 logical tag；访问时硬件比较两者。tag 不匹配可以暴露部分越界与 use-after-free。

4 bit tag 只有有限取值，碰撞仍可能发生。MTE 是概率型检测和安全缓解，无法证明 Native 代码没有错误。tag storage 的名义位数约为受标记内存的 1/32，运行成本还包括分配器维护、检查模式和诊断记录。

### 平台时间线

| 版本 | 面向应用的关键变化 |
| --- | --- |
| Android 13 | 部分设备开始支持 MTE，可用 `memtagMode` 请求 heap tagging |
| Android 14 QPR3 | NDK 文档给出 stack tagging 插桩支持 |
| Android 17 | 支持设备与工具继续扩展，具体启用仍取决于硬件和系统配置 |

可先检查设备 CPU 特性：

```bash
adb shell grep mte /proc/cpuinfo
```

输出包含 `mte` 只能说明设备当前暴露该 CPU 特性。App 进程是否启用，还要检查 Manifest、compat change 或运行时配置。

### App 公共模式是 `sync` 与 `async`

- `sync`：在发生不匹配的 load/store 处以 `SIGSEGV`、`SEGV_MTESERR` 终止，定位精度高，适合测试。
- `async`：允许执行继续到后续内核入口，再以 `SEGV_MTEAERR` 终止，报告精度较低，开销更适合充分测试后的发布场景。

以下调试用 Manifest 为应用进程请求同步模式：

```xml
<application
    android:memtagMode="sync"
    ... />
```

Manifest 请求只作用于支持 MTE 的设备。自定义 allocator 还要自行使用 `PROT_MTE`、对齐和 tag 指令；heap MTE 也覆盖不了未做 stack instrumentation 的栈对象。

### Stack Tagging

Android 14 QPR3 起，可用 NDK 的 `-fsanitize=memtag`、`-march=armv8-a+memtag` 等选项构建调试用 stack tagging。该产物只在兼容设备运行，官方明确把插桩构建定位在调试用途。

Arm 架构和内核内部还有更多 fault mode 组合。Android 应用的稳定公开配置仍以 `off/default/sync/async` 为准，应用不要依赖厂商 sysfs 把某个模式“透明升级”为另一种语义。

## Graphics 计量：位置变化不等于免费

`dumpsys meminfo` 中 Graphics、GL 和其他图形口径受 memtrack HAL、驱动、buffer 共享关系及 OEM 实现影响。跨设备直接比较单个 Graphics 数字容易误判。

Hardware Bitmap、Surface、视频 buffer 或 GPU 资源可能同时涉及：

- 进程虚拟映射和 RSS/PSS；
- dma-buf 共享页；
- memtrack 归属；
- GPU/driver 私有统计；
- Java/Native wrapper 对底层 handle 的引用。

分析时使用同一设备、同一版本、同一场景做前后对照。`dumpsys meminfo`、Perfetto 的进程内存/图形数据源、dmabuf 信息和图形子系统工具要互相印证。

## Android 15+：16 KB Page Size

Android 15 起 AOSP 支持 16 KB page size。自 2025 年 11 月 1 日起，Google Play 要求面向 Android 15 / API 35+ 设备的新应用和更新在 64 位设备上支持 16 KiB。

### 应用兼容性

纯 Java/Kotlin 应用在所有依赖均不含原生代码时通常兼容，仍要测试。含 `.so` 的应用需要：

- AGP 8.5.1+ 处理正确的打包对齐；
- NDK r28+ 默认产生兼容的 ELF 对齐；
- 检查所有预编译 SDK 与 AAR 中的原生库；
- 用 `sysconf(_SC_PAGESIZE)` 或 `getpagesize()` 代替硬编码 `4096`；
- 在 16 KB 系统跑启动、`dlopen`、`mmap` 和业务回归。

验证设备与 APK 时可使用：

```bash
adb shell getconf PAGE_SIZE
zipalign -c -P 16 -v 4 app-release.apk
```

第一个结果应为 `16384`，第二个检查 APK 中未压缩共享库的 16 KiB 对齐。ELF LOAD 段还要通过官方脚本或 `llvm-objdump` 检查。

### PSS 与内部碎片要按页理解

Linux 为 `/proc/<pid>/smaps` 生成 `Pss`，按每个驻留页的共享情况分摊。Android 的 `Debug.getPss()`/`dumpsys meminfo` 读取并归并这些数据。`smaps` 中 `Shared_Clean / N` 的简单公式无法精确替代内核按页计算。

16 KB 改变了页粒度，较小的独立映射、ELF 尾页和保护页可能产生更多页内空闲。普通 `malloc(5 KiB)` 通常由 allocator 与其他 chunk 共用页面，不能直接推导为“单独占一张 16 KB 页”。内存增减要从完整映射、allocator 行为、页表和工作集测量。

### Android 17 linker compat

`android-17.0.0_r1` 的 bionic 链接器已包含 16 KB App Compat：

- `ElfReader::Read()` 在 16 KB 系统发现 ELF 对齐不足时判断 compat；
- `ElfReader::LoadSegments()` 调用 `Setup16KiBAppCompat()`；
- `linker_phdr_16kib_compat.cpp` 检查 RX/RW 布局，并准备兼容映射；
- 4 KiB ELF 内容可能读入匿名映射，带来共享性和 PSS 成本。

兼容模式是迁移辅助，不应代替重新构建和验证原生依赖。具体细节见 4.7。

## Android 17：App MemoryLimiter

Android 17 在 `system_server` 中加入 MemoryLimiter。它不是公开应用 API，也不是所有 Android 17 设备都会启用。`android-17.0.0_r1` 的启用条件包括：

- `Flags.memoryLimiterEnable()`；
- 运行在 system UID；
- `/vendor/etc/memory-limiter-config.xml` 存在；
- 配置中有适合设备 `MemTotal` 的 limit set。

### cgroup 控制与监测

Java 控制器按进程可见性选择 `memHigh` 和 `swapHigh`，Native peer 通过 processgroup API 找到进程 cgroup。Android 17 实现使用：

- `memory.high`：限制/节流内存工作集；
- `memory.swap.max`：限制 swap 使用；
- `memory.events`：观察 high 等事件；
- `memory.stat` 中的 `anon + shmem`；
- `memory.swap.current`：计算 anon+shmem+swap 当前值。

Java 中部分字段和日志沿用 `swapHigh`/`memory.swap.high` 命名，但原生文件路径是 `memory.swap.max`。运行行为应以最终写入的 cgroup 文件为准。

### 越界后的行为

`memory.high` 本身不会直接发送 `SIGKILL`。MemoryLimiter 在内存与 swap 事件后可能进入轮询；当 `anon + shmem + swap.current` 超过组合阈值时：

1. 先把该进程的两个限制恢复为 `max`；
2. 条件满足时通知 Profiling 模块的 `TRIGGER_TYPE_ANOMALY`；
3. 延迟 30 秒向 AMS 请求终止进程，为性能分析留出时间；
4. DeviceConfig 的 disable-kill 开关可以跳过最终的 kill。

MemoryLimiter 与 lmkd 并行作用于不同条件。前者关注厂商配置的单进程阈值，后者在系统内存压力下选择 victim；任何一方都可能先产生可见结果。

平台调试可查看：

```bash
adb shell am memory-limiter status
```

`ignore` 和 `manual` 子命令面向测试，通常需要平台调试权限，不属于普通应用的诊断接口。

## Android 17 kernel 6.18：MGLRU 延续

MGLRU（Multi-Gen LRU）早于 Android 17 已进入 Android GKI。内核锚点 `android17-6.18-2026-06_r6` 的 `arch/arm64/configs/gki_defconfig` 包含：

```text
CONFIG_LRU_GEN=y
CONFIG_LRU_GEN_ENABLED=y
```

这说明该 GKI 基线编译并默认启用 MGLRU。具体产品仍可能使用厂商配置、不同 kernel build 或运行时开关，不能仅凭 Android 版本推断。

MGLRU 按访问代际组织匿名页/文件页 folio，回收时优先处理较老代，提高 working-set 判断的质量。它改变内核回收，不能替代应用对泄漏、Bitmap 或原生分配的治理。

设备上可检查：

```bash
adb shell cat /sys/kernel/mm/lru_gen/enabled
```

节点存在且值包含启用位，才说明运行内核开放了相应能力。Perfetto 的 vmscan tracepoint能观察回收活动；传统 LRU 也会产生的事件不能单独证明 MGLRU 正在工作。

## 版本演进速查表

| 版本 | 平台变化 | 诊断时要记住 |
| --- | --- | --- |
| Android 5.0 | ART 成为默认 Runtime，CMS/RosAlloc 与 AOT | Dalvik/ART 停顿没有跨设备固定值 |
| Android 7.0 | AOT + JIT + 解释执行的混合模式 | Code cache 和 profile 进入分析范围 |
| Android 8.0 | CC 默认；RegionTLAB/read barrier | AOSP 基准数字不能当 App 保证 |
| Android 8.0 | Bitmap 像素进入原生堆；硬件 Bitmap | Java 堆不再覆盖全部图片压力 |
| Android 10 | CC 默认使用 generational mode | Young GC 仍需测量 cause、停顿和回收量 |
| Android 11 | Scudo 覆盖标准 Native heap，低内存设备例外 | 默认选项决定具体检测能力 |
| Android 13 | 部分设备支持应用 MTE | 先确认硬件与进程模式 |
| Android 14 | UFFD Mark-Compact 源码路径可核验 | 源码存在不代表每台设备已选择 |
| Android 14 QPR3 | MTE 栈标签工具支持 | 插桩构建仅用于兼容设备调试 |
| Android 15 | AOSP 支持 16 KB page size | Native ELF 与 APK 打包都要检查 |
| Android 17 | 分代 CMC/YoungMarkCompact | flag、属性、UFFD 和 kernel 共同决定 |
| Android 17 | MemoryLimiter 条件启用 | cgroup 单进程阈值与 lmkd 系统压力并存 |
| Android 17 kernel 6.18 | GKI 配置延续 MGLRU | 产品 kernel 和运行节点需要现场确认 |

## 排查旧版本与新版本差异

面对“升级系统后内存变大/变小”，按以下顺序取证：

1. 固定同一 APK、同一业务数据、同一操作脚本和稳定等待时间；
2. 记录 API、build fingerprint、ABI、page size、kernel 与低内存设备标志；
3. 确认 ART collector、是否 generational、GC cause 和回收前后数据；
4. 分开统计 Java、Native、Graphics/dmabuf、Code、Stack、swap 和 FD；
5. 检查 Bitmap 解码配置、图片库版本、Native allocator 与 MTE；
6. 查看 `ApplicationExitInfo`、lmkd/MemoryLimiter 线索和系统压力；
7. 用多轮 P50/P95/P99 与退出后的回落值比较。

版本变化可以解释现象，不能代替引用链、调用栈和目标设备测量。

## 常见误区

### Android 8.0 后 Bitmap 不需要管理

像素迁入 Native Heap 只改变记账位置。普通 Bitmap、硬件 Bitmap 和图形缓冲区都消耗进程或系统物理内存，仍需控制解码尺寸、缓存与所有权。

### `largeHeap` 提供稳定的两倍空间

设备可能返回相同或不同的 large memory class，平台不保证倍率。该选项也不覆盖 Native、Graphics、swap 或 FD。

### Scudo 可以阻止所有原生内存错误

Scudo 能发现部分 chunk corruption 和非法释放，并通过终止进程降低继续利用的机会。插桩范围、配置、custom allocator 和概率检测都会留下边界，测试仍需 Sanitizer、MTE 与专项工具。

### Android 17 设备都启用 CMC、MemoryLimiter 和 MGLRU

这三项分别受 ART 配置与 UFFD、feature flag/vendor XML、产品内核配置与运行时开关影响。AOSP 锚点证明实现存在，设备结论要现场核对。

---

## 参考资料

### AOSP / kernel 源码锚点

- `art/runtime/gc/collector/concurrent_mark_sweep.cc`：CMS
- `art/runtime/gc/collector/concurrent_copying.cc`：CC
- `art/runtime/gc/collector/mark_compact.h/.cc`：CMC、`YoungMarkCompact`、三代与 UFFD
- `art/runtime/gc/heap.cc`：Collector 创建、分代选择与运行日志
- `frameworks/base/graphics/java/android/graphics/Bitmap.java`：Native 分配与 Hardware Bitmap
- `external/scudo/`：Android Scudo 集成
- `bionic/linker/linker_phdr.cpp`、`linker_phdr_16kib_compat.cpp`：16 KB compat
- `frameworks/base/services/core/java/com/android/server/am/MemoryLimiter.java`：gate、状态与延迟 kill
- `frameworks/base/services/core/jni/com_android_server_am_MemoryLimiter.cpp`：cgroup 文件与监测
- `packages/modules/Profiling/framework/java/android/os/ProfilingTrigger.java`：API 37 anomaly trigger
- `kernel/common/arch/arm64/configs/gki_defconfig`：`LRU_GEN` 配置

平台源码以 `android-17.0.0_r1` 为当前锚点，内核以 `android17-6.18-2026-06_r6` 为当前锚点。

### 官方文档

- [Android runtime and Dalvik](https://source.android.com/docs/core/runtime)
- [Configure ART](https://source.android.com/docs/core/runtime/configure)
- [Debug ART garbage collection](https://source.android.com/docs/core/runtime/gc-debug)
- [Android 8.0 ART improvements](https://source.android.com/docs/core/runtime/improvements)
- [Managing Bitmap Memory](https://developer.android.com/topic/performance/graphics/manage-memory)
- [Scudo](https://source.android.com/docs/security/test/scudo)
- [Arm MTE on Android](https://source.android.com/docs/security/test/memory-safety/arm-mte)
- [MTE Guide for NDK](https://developer.android.com/ndk/guides/arm-mte)
- [`<application android:largeHeap>`](https://developer.android.com/guide/topics/manifest/application-element)
- [Support 16 KB page sizes](https://developer.android.com/guide/practices/page-sizes)

### 交叉阅读

- 4.1：Android 进程内存口径
- 4.2：Linux reclaim、cgroup 与 MGLRU
- 4.3：ART Collector 和分配路径
- 4.4：lmkd、冻结与 MemoryLimiter
- 4.5：App Bitmap、泄漏、Native 工具与预算
- 4.7：16 KB 构建和兼容性
- 2.9：渲染架构与 Graphics 内存演进
