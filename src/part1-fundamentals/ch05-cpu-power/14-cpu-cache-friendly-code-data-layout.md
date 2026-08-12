---
title: "CPU Cache 友好代码与数据布局优化"
chapter: "5.14"
section: "5.14"
status: ready-for-review
applicable_versions: "Android 8 (API 26) - Android 17 (API 37)"
last_verified: "2026-06-05"
last_verified_against: "ARM Cortex-A spec, Linux kernel 6.12, AOSP android-17.0.0_r1, Simpleperf docs"
confidence: medium
sources:
  - type: aosp
    path: "frameworks/base/core/java/android/os/MessageQueue.java"
  - type: aosp
    path: "art/runtime/gc/accounting/card_table.h"
  - type: aosp
    path: "system/memory/libdmabufheap/"
  - type: aosp
    path: "frameworks/native/libs/binder/Parcel.cpp"
  - type: official
    path: "https://developer.android.com/ndk/guides/simpleperf"
  - type: blog
    path: "Facebook Redex interdex pass"
  - type: official
    path: "https://developer.arm.com/documentation"
tags: [cpu-cache, cache-line, false-sharing, data-layout, dex-reordering, redex, locality, startup-optimization]
related_chapters: ["5.1", "5.3", "8.7", "16.6", "21.4"]
---

# 5.14 CPU Cache 友好代码与数据布局优化
CPU cache 优化应先证明当前负载受内存层级限制，再让数据布局匹配访问模式，不能停留在“顺序数组比链表快”这类经验判断。移动 SoC 的核心、频率、cache 容量、共享层级和 PMU 事件均有差异；没有测量支撑的 padding、prefetch 或对象池，很容易增加内存占用，却没有改善延迟。

平台与内核基线分别为 Android 17 / API 37 / `android-17.0.0_r1` 和 `android17-6.18-2026-06_r6`。分析范围包括 Kotlin/Java、NDK C/C++、DEX 布局和系统源码中的局部性设计。调度与大小核见 5.1、5.2、5.3，Baseline Profile 见 8.7，启动测量见 21.4。

## 先建立准确的 cache 模型

现代移动 CPU 通常有每核私有的 L1 instruction/data cache、每核或小组共享的 L2，以及 cluster 或 SoC 级共享 cache。具体容量、关联度、包含关系和访问延迟由 CPU 与 SoC 实现决定。Cortex-A510、A710、A715 等核心就允许多种 L1/L2 配置，芯片厂商还可以加入 system-level cache。

因此，不应把一张“L1 2 周期、L2 10 周期、主存 200 周期”的表当作所有 Android 设备的参数。延迟还会受频率、未完成访存数、预取、TLB、DRAM 状态和争用影响。工程上需要关注的是数量级与相对关系：

- 靠近执行核心的层级通常容量小、延迟低；
- 访问逐渐落到共享 cache 和 DRAM 时，延迟和能耗会上升；
- 连续、可预测的访问更容易利用 cache line 和硬件预取；
- 频繁写共享 line 会产生一致性流量；
- 工作集大于有效 cache 容量时，命中率会下降。

### 64 字节的适用范围

Android common kernel `android17-6.18-2026-06_r6` 的 arm64 `arch/arm64/include/asm/cache.h` 定义：

```c
#define L1_CACHE_SHIFT  6
#define L1_CACHE_BYTES  (1 << L1_CACHE_SHIFT)
```

这个内核基线按 64 字节 L1 cache line 构建。相同文件还从 `CTR_EL0.CWG` 读取 cache writeback granule，并把 arm64 的 `ARCH_DMA_MINALIGN` 设为 128 字节，说明“CPU L1 line”“DMA 安全对齐”和“跨 CPU 避免干扰的间隔”不能只用一个常量概括。

应用代码可以把 64 字节作为当前常见设备的实验起点，但不能写成 Armv8/Armv9 规范保证。涉及共享库、DMA 或多代设备时，应结合目标 ABI、设备资料和测量决定布局。

### 线程迁移不会清空原核心的 cache

线程从一个 CPU 迁移到另一个 CPU 后，新核心的私有 cache 可能没有该线程最近使用的数据，需要从共享层级或其他 coherent cache 获取。原核心的全部 L1/L2 不会因此被软件统一失效；硬件一致性协议仍负责维护共享数据的可见性。

迁移成本取决于：

- 工作集是否仍在共享 cache；
- 数据是否能从同一 cluster 的其他 cache 获取；
- 两个核心是否跨 cluster；
- 迁移间隔与工作集大小；
- 迁移前后 CPU 的微架构和频率；
- 同期内存带宽与其他任务。

所以 `cpu-migrations` 上升只是一条线索。需要同时比较 CPU time、周期数、cache refill、运行核心和端到端延迟，才能判断迁移是否伤害局部性。

### Hardware cache、ART inline cache 与软件缓存属于不同机制

这里讨论的 L1/L2/L3 是硬件 cache。ART 的 inline cache 用接收者类型记录来优化虚调用，业务代码中的 LruCache 保存计算结果；二者也叫 cache，却不表示同一种存储层级。

ART inline cache 可能让编译器生成更直接的调用路径，从而间接影响指令前端和数据访问。它不能拿来证明某个对象“进入 L1”，也不能用 L1 miss 解释所有多态调用开销。

## 局部性的两个方向

### 空间局部性

空间局部性描述相邻地址在接近的时间被访问。CPU 以 cache line 为单位传输数据，顺序遍历连续数组通常能充分利用一次 refill，并让预取器提前请求后续 line。

以 C++ 为例，`std::vector<float>` 的元素连续；链表节点通常分散分配。批量求和时，数组通常更有利。不过“链表每个节点必 miss、数组每 line 只 miss 一次”只是最坏与理想模型，分配器复用、节点大小、预取器和 cache 容量都会改变结果。

在 Java/Kotlin 中也要分清容器内容：

- `IntArray` 连续保存 primitive 值；
- `Array<Int>` / `List<Int>` 保存引用，并涉及装箱对象；
- `Array<MyObject>` 连续保存对象引用，对象本体仍分散在堆中；
- `ByteArray` / `FloatArray` 适合紧凑的批量处理；
- Java 多维数组是“数组的数组”，每一行是独立对象。

把热循环从 boxed collection 改为 primitive array，收益可能同时来自减少装箱、减少分配和改善局部性。报告中要说明改动包含哪些因素，不能把全部收益都归给 cache。

### 时间局部性

时间局部性描述数据在短时间内重复使用。一个工作块在仍位于 cache 时完成多次计算，通常比每轮扫描整个大数据集更有效。

二维数值计算、图片卷积和张量预处理常用 tiling：把输入拆成能适配目标 cache 的小块，在块内完成多个操作后再进入下一块。tile 大小需要基准测试，因为代码、栈、其他数组和并发线程也会占用 cache。简单地把 tile 设为“L1 容量除以元素大小”会低估这些竞争。

## False sharing：不同字段，共享一条一致性 line

当多个 CPU 并发访问同一 cache line，且至少一个 CPU 写入时，一致性协议需要转移或失效副本。如果线程操作的是不同字段，却因为字段位于同一 line 而产生大量一致性流量，就构成有害的 false sharing。

典型模式包括：

- 多线程分别更新数组中的相邻计数器；
- 一个线程频繁写状态，其他线程频繁读同 line 中的配置；
- 锁与被其他 CPU 高频读取的数据挤在同一 line；
- 多生产者把各自的 head/tail 或统计字段放得过近。

运行变慢不能单凭“字段相邻”定性。锁竞争、atomic 重试、调度和内存带宽也会产生相似症状。

### 先修并发模型，再考虑 padding

false sharing 的常用缓解顺序是：

1. 减少共享写入，例如每线程 / 每 CPU 累积后批量归并；
2. 避免无条件写相同值；
3. 把一起读取、一起更新的字段分组；
4. 将高频写字段与高频只读字段分开；
5. 最终才为已证实的热点增加对齐或 padding。

padding 会增加对象大小、cache/TLB 占用和内存流量，可能把问题移动到相邻字段。Linux 6.18 的 false-sharing 文档也要求根据性能证据权衡空间成本。

### NDK 可以控制布局，Java/Kotlin 没有同等保证

C++ 可用 `alignas` 明确对齐，并用 `sizeof` / `offsetof` 验证构建结果。下面的结构用于实验性隔离两个高频计数器：

```cpp
struct alignas(64) CounterSlot {
    std::atomic<int64_t> value{0};
    std::byte padding[64 - sizeof(std::atomic<int64_t>)];
};

static_assert(sizeof(CounterSlot) == 64);
```

它只保证 C++ 对象布局满足这次构建的 64 字节设计。目标硬件若使用更大的 coherence granule，或数组起始、allocator、ABI 发生变化，仍要重新验证。原子操作也必须使用符合算法的 memory order；padding 不能修复 data race。

Java/Kotlin 对象布局属于 ART 实现细节，应用无法通过添加若干 `long` 字段可靠地保证字段独占 cache line。`@Contended` 不是 Android 公共 SDK 契约。应用层更稳的方案是减少共享可变对象、分片计数、批量提交，并以基准测试验证。

### 不要把 MessageQueue 当作已证实案例

Android 17 的 `MessageQueue` 有 Legacy、Combined 与 CombinedDeli 等实现变体，字段布局还要经过 ART 对象布局。`mPtr` 与 `mMessages` 在源码中相邻，不能证明它们位于同一 cache line，更不能证明它们引发了可测 false sharing。

`enqueueMessage()` 与队列消费还包含锁、native poll/wake 和主线程调度。没有 PMU、地址级采样和对照布局时，应把它作为共享队列案例分析，不能标记成 framework 的 false-sharing 事实。

## C/C++ 数据布局：AoS、SoA 与 hot/cold split

### AoS 与 SoA 由访问模式决定

Array of Structures（AoS）把一个元素的所有字段放在一起：

```cpp
struct Particle {
    float x, y, z;
    float vx, vy, vz;
    float r, g, b, a;
};
std::vector<Particle> particles;
```

这个结构每个元素为 40 字节（忽略额外对齐）。若循环只读 `x/y/z`，有用数据约占对象流量的 12/40，即 30%，并非固定的 18.75%。cache line 还可能跨越两个对象，边界与数组起始地址有关。

Structure of Arrays（SoA）把同类字段拆成连续数组：

```cpp
struct ParticleBatch {
    std::vector<float> x, y, z;
    std::vector<float> vx, vy, vz;
    std::vector<float> r, g, b, a;
};
```

只更新位置时，SoA 能避免拉入颜色与速度；处理一个粒子的全部字段时，AoS 可能更紧凑。还可以采用 Array of Structures of Arrays（AoSoA），按 SIMD 宽度或 tile 分组，在向量化与单元素访问之间折中。

选择时测量以下指标：

- 目标循环端到端耗时；
- bytes processed / item；
- L1D refill、LLC miss 与 TLB miss；
- 向量化报告和生成代码；
- 内存占用与构造成本。

### hot/cold split 要考虑对象生命周期

把每次迭代都读取的字段放进紧凑结构，把调试字符串、低频统计和错误信息放到 cold side，可以缩小热工作集。常见形式是：

```cpp
struct RenderItemHot {
    float transform[16];
    uint32_t flags;
    uint32_t resourceIndex;
};

struct RenderItemCold {
    std::string debugName;
    uint64_t createdAt;
};
```

热结构可以连续存入 vector，cold 数据通过稳定索引关联。这里的代价是多一层索引、两套生命周期和更复杂的更新逻辑。若 cold 字段在常见路径也频繁访问，拆分反而增加一次间接访问。

不要用想象中的 `RenderNode` 布局证明方案。应对自己的结构运行 `sizeof` / `offsetof`、编译器布局 dump 和 workload benchmark。

### 连续内存也有扩容与复制成本

`std::vector` 和 Binder `Parcel` 使用连续缓冲区，顺序读写具备空间局部性。但容量增长可能触发重新分配和复制。已知大小时合理 `reserve()` 可以减少扩容；过度预留会增加 RSS。

Android 17 `frameworks/native/libs/binder/Parcel.cpp` 中，`mData`、`mDataSize`、`mDataCapacity` 和 `mDataPos` 管理连续数据区，写入按 4 字节 padding，增长路径使用 `realloc` 或分配并复制。Parcel 另有对象偏移数组，读取也可以调整 data position，因此“Parcel 只能从头顺序读、不能随机访问”并不准确。

Parcel 的布局服务于 Binder wire format、安全检查和对象管理，cache 局部性是其连续数据区带来的性质之一。它不构成“Parcel 总比 JSON 快”的充分证据；序列化格式、数据规模、解析器和 IPC 拷贝都要纳入比较。

## Java/Kotlin 热路径：先减少工作，再谈对象池

### 避免装箱和指针追踪

在图像、音频、统计和几何运算中，优先评估 primitive array、紧凑 buffer 或专用 collection。`List<Float>` 的每个元素访问要经过引用与装箱对象，数据密度通常低于 `FloatArray`。

这不意味着业务层所有模型都要改成数组。对不在热点的代码，可读性与正确性更重要。常见做法是保留清晰的业务对象，在经过 profile 证实的计算边界转换为批量 buffer。

### 谨慎复用可变对象

ART 的线程局部分配路径很快，短命对象也可能在年轻代高效回收。对象池会带来：

- 状态重置不完整；
- 生命周期和线程安全更复杂；
- 池保留对象，抬高 live set；
- 旧对象未必仍在目标 CPU 的 cache；
- 池自身产生锁竞争或共享写入。

`Message.obtain()` 的回收池证明 framework 有特定复用策略，不证明所有临时对象都应池化。应用应先用 allocation profiler、GC pause、CPU 和内存数据确认分配成本，再比较“直接分配”“批量分配”“复用”三种方案。

### 分支与 cache 要分开归因

不可预测分支会造成 pipeline flush，间接跳转也会影响前端；这些问题与 data-cache miss 不同。三元表达式不保证生成无分支指令，`__builtin_expect` 也只是给编译器概率信息。

优化分支时查看 branch-misses、生成代码和端到端时间。把错误路径移出热函数可能改善指令布局，但函数内联、LTO 和 PGO 会再次改变代码，源码排列不能直接代表最终 instruction-cache 布局。

### 手动 prefetch 只能由实验决定

`__builtin_prefetch()` 是提示，编译器和硬件可以按各自规则处理。线性数组通常已有硬件预取；链表、树或多流访问有时能从软件 prefetch 获益。

prefetch 距离太近会来不及，太远会污染 cache，地址无效还可能造成额外页表工作。至少在两类核心、冷/热数据和有/无并发负载下比较，并检查能耗；只看一个 microbenchmark 的 p50 不足以进入通用库。

## DEX 局部性：使用 Startup Profile，不手写不存在的开关

DEX 标识符与 class definitions 受格式排序约束，不能描述为“按源码出现顺序排列”。ART 的 AOT/JIT 产物布局也不等于机械复制 DEX 顺序。

Android 当前的官方路径把两个 profile 分工：

- Baseline Profile 供 ART 对常用方法进行 AOT 编译；
- Startup Profile 在构建期指导 R8/D8 优化 DEX 中启动代码的布局。

Startup Profile 让启动关键类和方法更集中，并尽量放入首个 `classes.dex`，从而减少启动阶段需要触及的代码页。收益可能来自 DEX page locality、fault、解压 / 映射和编译代码布局等多项变化，不能全部写成 instruction-cache miss。

### 当前构建要求

官方文档给出的版本边界是：

- DEX layout optimization 从 AGP 8.1 可用；
- AGP 8.1–8.2 需要在 Baseline Profile 配置中启用；
- AGP 8.3 起默认启用；
- release 构建需要开启 R8、minification 和完整优化；
- startup journey 通过 `includeInStartupProfile = true` 进入 Startup Profile。

现稿中的 `dexOptions.reorderClassesWithProfiling` 不是对应的公开 AGP 配置，不应出现在示例中。

### 生成、验证、A/B 测量

Startup Profile 应覆盖 launcher、常见 deep link、通知入口等真实启动路径，又要避免把大量非启动 journey 塞满首个 DEX。

验证时：

1. 用 APK Analyzer 查看 startup 类和方法是否进入预期 DEX；
2. AGP 8.8 及以上可检查 AAB 内 `BUNDLE-METADATA/com.android.tools/r8.json` 的 `"startup": true`；
3. 用 Macrobenchmark 分别测冷启动、温启动和多个入口；
4. 固定 APK、编译状态、设备温度和系统版本。

不要引用与当前应用、构建链无关的 Redex 百分比作为预期收益。官方给出的经验范围也只能用于决定是否实验，发布结论应来自自己的 A/B 数据。

## Simpleperf：从症状到证据

### 先查看设备支持哪些 PMU 事件

事件名和可用性取决于 CPU PMU、内核及权限。采集前先运行：

```bash
simpleperf list
simpleperf list raw
simpleperf stat --print-hw-counter
```

第一条列出内核封装事件，第二条列出当前 Arm PMU 的 raw event，第三条显示可用硬件 counter 数量。不能假设每台设备都支持 `raw-l2-dcache-refill`，也不能把某个 Cortex 文档中的 event number 直接用于另一款 SoC。

### 先做成组计数

如果设备支持通用事件，可以先比较周期、指令和 cache 事件：

```bash
simpleperf stat \
  --group cpu-cycles,instructions \
  --group cache-references,cache-misses \
  -p <pid> --duration 10
```

同组事件尽量同时调度，适合计算 IPC 或 miss ratio。硬件 counter 不足时会发生 multiplexing，输出中的 enabled/running 时间和警告必须保留。不同 cluster 可能使用不同 PMU，线程迁移也会影响解释。

没有一个通用的“cache miss 超过 10% 就该优化”阈值。miss 的种类、每次代价、memory-level parallelism 和业务 deadline 都不同。应该比较相同工作量下的前后变化，并确认 latency / throughput 同向改善。

### 再做热点采样

确认 cache 事件与慢样本相关后，再定位符号：

```bash
simpleperf record \
  -e cache-misses:u \
  -p <pid> --duration 10 --call-graph dwarf
simpleperf report --sort dso,symbol
```

是否支持该事件采样、用户态过滤和 DWARF call graph 要由 `simpleperf list` 与设备能力确认。采样结果只能定位哪些指令附近出现事件，不一定包含被访问的数据地址，也不能单独证实 false sharing。

debuggable / profileable 应用可使用 Simpleperf 的应用分析流程。不要把 `setenforce 0` 写成普通开发步骤；量产设备的 PMU 与 tracing 权限由系统安全策略决定。

### 低 IPC 不能单独证明 memory-bound

IPC 低还可能来自：

- branch miss 或 instruction-cache / TLB 压力；
- 长依赖链；
- 锁等待附近的短运行片段；
- 前后端 stall；
- 不同核心宽度与频率；
- PMU multiplexing 或统计窗口错误。

判断 memory-bound 至少需要观察 cache/TLB refill、backend stall、内存带宽或 latency 采样中的一部分，并通过改变数据布局或工作集做可控实验。

Perfetto 的 sched、CPU frequency、thread state 和应用 slice 用于提供时间上下文。默认 trace 不会自动产生每线程 instructions/cycles，也不存在可以直接复制的通用 SQL，把任意 counter 按线程求 IPC。可以用相同 workload 的时间窗口关联 Simpleperf 与 Perfetto，但需注明两次采集还是同次采集。

### False sharing 需要地址级证据

普通 cache-miss 采样只能提示热点。定位 false sharing 通常需要：

- 支持 Arm SPE 的设备；
- 内核 perf data-source 信息；
- `perf c2c` 或等价厂商工具；
- 带符号的 binary；
- 结构体布局信息，例如 `pahole` / `offsetof`。

这些条件在量产 Android 手机上经常不齐。可行的替代实验是：固定线程和工作量，只改变计数器分片或字段间距；同时比较吞吐、atomic retry、cache event 与功耗。若无法得到地址级证据，结论应写成“与共享 line 竞争一致”，不写成已经定位到某个字段。

## Android 17 源码中的局部性设计

### ART CardTable：一字节表示 1 KiB 堆区间

Android 17 ART 的 `CardTable` 定义 `kCardShift = 10`，所以每个 card-table byte 对应 1 KiB heap。对象引用写屏障把相应 byte 标为 `kCardDirty`，GC 再扫描 dirty card。

`CardTable::Create()` 为表额外分配 256 字节，并调整 `biased_begin`，使其地址低字节等于 `kCardDirty`。源码注释说明，这样 JIT 写屏障不必另行构造或加载 dirty 常量。这是减少生成代码指令的一项具体设计。

可确认的边界是：

- card granularity 是 1 KiB heap / 1 byte table；
- biased base 服务于高效计算 card 地址与 dirty store；
- dirty、aged、aged2 是 GC 状态。

不能从这些常量推出“每次写屏障节省一条 cache line”或固定性能百分比。实际指令序列依赖 ISA、编译器后端和运行模式；多个 mutator 写相邻 card byte 也不自动等于已经观测到的 false sharing。

### Binder Parcel：连续数据与独立对象表

Android 17 `Parcel` 的普通数据存储在 `mData` 连续缓冲区，通过 `mDataPos` 顺序写入，并按 4 字节边界 padding。容量不足时 `growData()` 扩大缓冲区，`continueWrite()` 负责所有权与复制。Binder 对象位置另存于 `mObjects` 或 RPC object-position 容器。

这套布局方便顺序序列化和内核 Binder 处理，也能减少普通字段的指针追踪。与此同时，扩容、对象验证、FD 复制和大 blob 仍可能主导成本。源码结构能解释数据在哪里，性能结论仍要由具体 transaction 测量。

### Linux cache 对齐宏表达了取舍

内核 6.18 的 `include/linux/cache.h` 提供：

- `__read_mostly`，把热路径中很少修改的数据集中；
- `__cacheline_aligned` / `____cacheline_aligned_in_smp`；
- cacheline group begin/end；
- `cache_line_size()`。

文件注释明确要求谨慎使用 `__read_mostly`，并用 profile 决定；紧凑读取减少 line 数，对齐隔离则增加空间。应用层可借鉴这套决策顺序，不能直接复制内核宏或认为所有结构都应独占一条 line。

### 删除与 cache 无关的伪案例

PSS 的 Dalvik/native/other 分类用于内存归因，不能说明“cache 流分离”。`anon_huge_pages`、`file_pmd_mapped` 等 smaps 字段反映大页映射状态，也不能用于避免 false sharing。它们属于内存统计和 TLB/页表主题，不应作为 Android 17 cache 优化案例。

同样，SLUB 不会把所有对象大小统一向上取整到 cache-line 整数倍；具体 alignment 取决于架构、cache flags、对象大小和创建参数。16 KiB page 对 slab order、碎片和 TLB 的影响也需要单独测量。

## 一套可执行的优化流程

### 1. 固定业务指标

先选用户可见或系统目标：帧耗时、启动时间、音频 deadline、每秒处理量、单次能量。cache counter 是解释指标，不能取代业务指标。

### 2. 找到 CPU 热点

用 Perfetto 确认线程何时在运行、是否被抢占或迁移；用 Simpleperf 的 cycles / instructions 找 CPU 热点。若线程多数时间阻塞，先查锁、I/O 或 Binder。

### 3. 验证 memory hierarchy 假设

在设备支持范围内加入 cache/TLB/stall 事件。改变工作集大小、遍历顺序或字段布局，看事件和业务耗时是否产生可重复的同向变化。

### 4. 一次只改一个主要变量

分别比较：

- primitive array 与 boxed collection；
- AoS、SoA、AoSoA；
- 每线程分片与共享 atomic；
- 有无 reserve；
- 有无 Startup Profile；
- 有无 prefetch / 不同 tile。

避免一次同时改算法、线程数、数据结构和编译选项，否则无法解释收益来源。

### 5. 覆盖大小核与热状态

至少在目标机型的常见调度状态下重复。不要为了 cache 实验把生产代码永久绑核；可在受控 benchmark 中记录运行 CPU，并分别观察两类核心。长时负载还要记录 thermal 和频率，防止把降频差异误认为 cache 收益。

### 6. 检查代价

布局优化可能增加：

- RSS 与 allocator 碎片；
- TLB miss；
- 初始化和转换成本；
- 代码复杂度；
- 低端设备上的工作集；
- 多份数据的一致性维护。

只有业务指标在代表性设备和输入上稳定改善，改动才值得保留。

## 结论

Cache 友好代码的核心是让“经常一起使用的数据”在时间和地址上靠近，让“被不同 CPU 频繁写的数据”减少共享。实现方式会随语言层变化：

- Kotlin/Java 优先减少装箱、指针追踪和共享可变状态；
- NDK 使用连续容器、hot/cold split、SoA/AoSoA 和经过验证的对齐；
- 启动代码通过 Startup Profile 交给 R8/D8 做 DEX layout；
- 系统级问题通过 PMU、地址级采样和源码布局核对。

所有规则都有反例。数组可能因转换成本输给对象模型，padding 可能因内存膨胀变慢，prefetch 可能污染 L1，Startup Profile 也可能因为覆盖错误入口而收益很小。先测量，再做最小改动，最终回到端到端指标验收。

## 源码核对索引

- `art/runtime/gc/accounting/card_table.h`
  - `kCardShift`、card 状态和 biased base 字段。
- `art/runtime/gc/accounting/card_table.cc`
  - 额外 256 字节映射与 `biased_begin` 计算。
- `frameworks/native/libs/binder/Parcel.cpp`
  - 连续 `mData`、4 字节 padding、增长与对象位置管理。
- `kernel/arch/arm64/include/asm/cache.h`
  - 64 字节 L1 基线、`CTR_EL0.CWG` 与 DMA alignment。
- `kernel/include/linux/cache.h`
  - read-mostly、cacheline alignment 与 group 宏。
- `kernel/Documentation/kernel-hacking/false-sharing.rst`
  - 检测条件、`perf c2c` 与缓解原则。

## References

- [Android Simpleperf documentation](https://developer.android.com/ndk/guides/simpleperf)
- [AOSP Simpleperf command reference](https://android.googlesource.com/platform/system/extras/+/android-17.0.0_r1/simpleperf/doc/executable_commands_reference.md)
- [Baseline Profiles overview](https://developer.android.com/topic/performance/baselineprofiles/overview)
- [Startup Profiles overview](https://developer.android.com/topic/performance/startupprofiles/overview)
- [Create Startup Profiles and optimize DEX layout](https://developer.android.com/topic/performance/startupprofiles/dex-layout-optimizations)
- [Confirm Startup Profile optimization](https://developer.android.com/topic/performance/baselineprofiles/confirm-startup-profiles)
- [AOSP Android 17 ART CardTable](https://android.googlesource.com/platform/art/+/android-17.0.0_r1/runtime/gc/accounting/card_table.h)
- [AOSP Android 17 Binder Parcel](https://android.googlesource.com/platform/frameworks/native/+/android-17.0.0_r1/libs/binder/Parcel.cpp)
- [Android common kernel 6.18 arm64 cache definitions](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/arch/arm64/include/asm/cache.h)
- [Android common kernel 6.18 cache helpers](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/include/linux/cache.h)
- [Android common kernel 6.18 false-sharing guide](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/Documentation/kernel-hacking/false-sharing.rst)
- [Arm Cortex-A processor comparison](https://developer.arm.com/documentation/109140/latest/)
