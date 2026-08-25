---
title: CPU Cache 友好代码与数据布局优化
chapter: '5.8'
section: '5.8'
status: finalized
pipeline_stage: ready-to-publish
applicable_versions: Android 8 (API 26) - Android 17 (API 37)
last_verified: '2026-06-05'
last_verified_against: ARM Cortex-A spec, Linux kernel 6.12, AOSP android-17.0.0_r1, Simpleperf docs
confidence: medium
sources:
- type: aosp
  path: frameworks/base/core/java/android/util/LruCache.java
- type: aosp
  path: frameworks/base/core/java/android/os/MessageQueue.java
- type: aosp
  path: art/runtime/gc/accounting/card_table.h
- type: aosp
  path: system/memory/libdmabufheap/
- type: aosp
  path: frameworks/native/libs/binder/Parcel.cpp
- type: official
  path: https://developer.android.com/ndk/guides/simpleperf
- type: blog
  path: Facebook Redex interdex pass
- type: official
  path: https://developer.arm.com/documentation
tags:
- lru-cache
- cache-pollution
- cpu-cache
- cache-line
- false-sharing
- data-layout
- dex-reordering
- redex
- locality
- startup-optimization
related_chapters:
- '5.1'
- '21.4'
- '18.5'
last_consolidated_at: '2026-08-25'
consolidated_from:
- src/part5-app/ch21-startup/10-cache-optimization-cpu-locality.md
---

# CPU Cache 友好代码与数据布局优化

CPU cache（高速缓存，下文保留 cache）优化应先证明当前负载受内存层级限制，再让数据布局匹配访问模式，不能停留在“顺序数组比链表快”这类经验判断。这里的内存层级包括各级 cache、地址转换缓存和 DRAM。不同移动 SoC（系统级芯片）的 CPU 核心、频率、cache 容量、共享层级和 PMU（Performance Monitoring Unit，性能监控单元）事件均有差异；没有测量支撑的 padding（填充）、prefetch（预取）或对象池，很容易增加内存占用，却没有改善延迟。

平台与内核基线分别为 Android 17 / API 37 / `android-17.0.0_r1` 和 `android17-6.18-2026-06_r6`。分析范围包括 Kotlin/Java、NDK C/C++、DEX 布局和系统源码中的局部性设计。调度、EAS 与大小核见 5.1，Baseline Profile 见 21.4，启动测量见 21.1。

## 先建立准确的 cache 模型

现代移动 CPU 通常有每核私有的 L1 指令 cache 和数据 cache、每核或小组共享的 L2，以及 cluster（核心簇）或 SoC 级共享 cache。具体容量、组相联路数、上下级是否互相包含，以及访问延迟，均由 CPU 与 SoC 实现决定。Cortex-A510、A710、A715 等核心允许采用多种 L1/L2 配置，芯片厂商还可以加入 system-level cache（系统级 cache）。

因此，不应把一张“L1 2 周期、L2 10 周期、主存 200 周期”的表当作所有 Android 设备的参数。延迟还会受频率、尚未完成的访存请求数、预取、TLB（Translation Lookaside Buffer，地址转换缓存）、DRAM 状态和资源争用影响。工程上更有参考价值的是数量级与相对关系：

- 靠近执行核心的层级通常容量小、延迟低；
- 访问逐渐落到共享 cache 和 DRAM 时，延迟和能耗会上升；
- 连续、可预测的访问更容易利用 cache line（缓存行，即硬件成块传输和维护的一段连续数据）和硬件预取；
- 频繁写入共享 cache line 会增加硬件一致性协议的通信量；
- 当工作集（某段时间内反复访问的数据集合）大于有效 cache 容量时，命中率会下降。

### 64 字节的适用范围

Android common kernel `android17-6.18-2026-06_r6` 的 arm64 `arch/arm64/include/asm/cache.h` 定义：

```c
#define L1_CACHE_SHIFT  6
#define L1_CACHE_BYTES  (1 << L1_CACHE_SHIFT)
```

这个内核基线按 64 字节 L1 cache line 构建。相同文件还从 `CTR_EL0.CWG` 读取 cache writeback granule（cache 写回粒度），并把 arm64 的 `ARCH_DMA_MINALIGN` 设为 128 字节。这说明“CPU L1 cache line”“DMA 安全对齐”和“跨 CPU 避免互相干扰的间隔”不能用同一个常量概括。

应用代码可以把 64 字节作为当前常见设备的实验起点，但不能写成 Armv8/Armv9 规范保证。涉及共享库、DMA 或多代设备时，应结合目标 ABI、设备资料和测量决定布局。

### 线程迁移不会清空原核心的 cache

线程从一个 CPU 迁移到另一个 CPU 后，新核心的私有 cache 可能没有该线程最近使用的数据，需要从共享层级或同一硬件一致性域内的其他 cache 获取。原核心的全部 L1/L2 不会因此被软件统一失效；硬件一致性协议仍负责维护共享数据的可见性。

迁移成本取决于：

- 工作集是否仍在共享 cache；
- 数据是否能从同一 cluster 的其他 cache 获取；
- 两个核心是否跨 cluster；
- 迁移间隔与工作集大小；
- 迁移前后 CPU 的微架构和频率；
- 同期内存带宽与其他任务。

所以 `cpu-migrations` 上升只是一条线索。还要同时比较 CPU time、周期数、cache refill（从较低层级重新填入 cache line 的次数）、实际运行的核心和端到端延迟，才能判断迁移是否破坏局部性。

### Hardware cache、ART inline cache 与软件缓存属于不同机制

这里讨论的 L1/L2/L3 是硬件 cache。ART 的 inline cache（内联缓存）会记录某个调用点出现过的接收者类型，用来优化虚调用；业务代码中的 `LruCache` 则保存可复用的计算结果。它们虽然都叫 cache，却不属于同一种机制或存储层级。

ART inline cache 可能让编译器生成更直接的调用路径，从而间接影响取指、译码等指令前端工作和数据访问。它不能证明某个对象“进入 L1”，L1 miss 也不能解释所有多态调用开销。

## 局部性的两个方向

### 空间局部性

空间局部性描述相邻地址在接近的时间被访问。CPU 以 cache line 为单位传输数据，顺序遍历连续数组通常能充分利用一次 refill，并让预取器提前请求后续 cache line。

以 C++ 为例，`std::vector<float>` 的元素连续；链表节点通常分散分配。批量求和时，数组通常更有利。不过“链表每个节点必 miss、数组每 line 只 miss 一次”只是最坏与理想模型，分配器复用、节点大小、预取器和 cache 容量都会改变结果。

在 Java/Kotlin 中还要分清容器实际保存的内容：

- `IntArray` 连续保存 primitive（基本类型）值；
- `Array<Int>` / `List<Int>` 保存引用，并涉及装箱对象；
- `Array<MyObject>` 连续保存对象引用，对象本体仍分散在堆中；
- `ByteArray` / `FloatArray` 适合紧凑的批量处理；
- Java 多维数组是“数组的数组”，每一行是独立对象。

把热循环从 boxed collection（装箱元素集合）改为 primitive array（基本类型数组），收益可能同时来自减少装箱、减少分配和改善局部性。报告中要说明改动包含哪些因素，不能把全部收益都归给 cache。

### 时间局部性

时间局部性描述数据在短时间内重复使用。一个工作块在仍位于 cache 时完成多次计算，通常比每轮扫描整个大数据集更有效。

二维数值计算、图片卷积和张量预处理常用 tiling（分块）：把输入拆成能放入目标 cache 的小块，在块内完成多个操作后再进入下一块。tile 大小需要通过基准测试确定，因为代码、栈、其他数组和并发线程也会占用 cache。简单地把 tile 设为“L1 容量除以元素大小”，会低估这些资源竞争。

## 业务缓存的冷热分段

业务缓存利用时间局部性，但它的 hit/miss 是数据结构层指标，不能与 CPU cache miss 混算。Android 17 的 `android.util.LruCache` 用 access-order `LinkedHashMap` 保存条目：命中会把条目移到最近使用端，超出权重预算时从最久未使用端逐出。单个公开操作受内部锁保护；由多次 `get`、`remove`、`put` 组成的复合操作仍需调用方提供共同的原子边界。

纯 LRU 的常见弱点是 scan pollution（扫描污染）：分页浏览或大列表预取会连续加入一批只访问一次的新 key，把稍早访问、之后仍会复用的热条目逐出。只有 trace 和缓存指标确认存在这种访问形状时，才需要比 LRU 更复杂的策略。

### 用 probation/protected 隔离一次性扫描

SLRU（Segmented LRU，分段最近最少使用）把预算拆成两个 access-order 段：

1. 新条目进入 `probation` 观察段。
2. `probation` 条目再次命中后晋升到 `protected` 保护段。
3. `protected` 超出预算时，把最久未访问条目降回 `probation`。
4. `probation` 超出预算时，逐出最久未访问条目。

一次扫描因此主要竞争观察段预算，稳定复用的条目得到单独保护。两段比例没有通用答案，应由 key 分布、value 权重、重复访问间隔和内存预算共同决定。图片可以用实际字节数作为权重；普通对象只能采用团队能持续校准的近似值。

### 并发加载和释放仍要单独设计

`LruCache.create()` 在内部锁外计算 value。多个线程同时 miss 同一个 key 时，可能并行创建多个结果，缓存只保留其中一个。加载昂贵时，应在缓存外合并同 key 的在途请求，并定义失败是否缓存、多久后允许重试。不要把磁盘、网络或解码工作放进全局缓存锁，否则其他 key 的命中也会等待这次 I/O。

若 value 持有 `Bitmap`、文件句柄或其他需释放资源，应先在锁内收集逐出项，再在锁外执行释放回调，避免回调重入缓存或长时间占锁。上线 A/B 至少同时观察：

- 逻辑 hit、miss、逐出、晋升和降级；
- miss 后的解码、数据库、磁盘或网络成本；
- 缓存总权重、Java/native heap、PSS 和 GC；
- 锁等待、主线程耗时与端到端延迟。

命中率提高而 PSS、GC 或锁等待恶化时，缓存并没有带来净收益。分段 LRU 只解决明确的扫描污染，不应替代容量治理、内存压力响应和加载去重。

## False sharing（伪共享）：不同字段，共用一条一致性 cache line

当多个 CPU 并发访问同一 cache line，且至少一个 CPU 写入时，一致性协议需要转移数据或让其他核心上的副本失效。如果线程操作的是不同字段，却因为这些字段位于同一 cache line 而产生大量一致性通信，就形成了 false sharing。这里“共享”的是硬件维护一致性的 cache line，业务数据本身并没有被多个线程共同修改。

典型模式包括：

- 多线程分别更新数组中的相邻计数器；
- 一个线程频繁写状态，其他线程频繁读取同一 cache line 中的配置；
- 锁与被其他 CPU 高频读取的数据挤在同一 cache line；
- 多生产者把各自的 head/tail（读写位置）或统计字段放得过近。

运行变慢不能单凭“字段相邻”定性。锁竞争、atomic（原子操作）重试、调度和内存带宽不足也会产生相似症状。

### 先调整并发模型，再考虑 padding

缓解 false sharing 时，通常按以下顺序排查：

1. 减少共享写入，例如每线程 / 每 CPU 累积后批量归并；
2. 避免无条件写相同值；
3. 把一起读取、一起更新的字段分组；
4. 将高频写字段与高频只读字段分开；
5. 最后才为已经证实的热点增加对齐或 padding，让高频字段落入不同的 cache line。

padding 会增加对象大小、cache/TLB 占用和内存流量，也可能把竞争转移到相邻字段。Linux 6.18 的 false-sharing 文档同样要求根据性能证据权衡空间成本。

### NDK 可以控制布局，Java/Kotlin 没有同等保证

C++ 可用 `alignas` 明确对齐，并用 `sizeof` / `offsetof` 验证构建结果。下面的结构用于实验性隔离两个高频计数器：

```cpp
struct alignas(64) CounterSlot {
    std::atomic<int64_t> value{0};
    std::byte padding[64 - sizeof(std::atomic<int64_t>)];
};

static_assert(sizeof(CounterSlot) == 64);
```

它只保证 C++ 对象布局满足本次构建的 64 字节设计。目标硬件若采用更大的 coherence granule（一致性维护粒度），或数组起始地址、allocator（内存分配器）、ABI 发生变化，仍要重新验证。原子操作也必须采用符合算法要求的 memory order（内存序）；padding 无法修复 data race（数据竞争）。

Java/Kotlin 对象布局属于 ART 实现细节，应用无法通过添加若干 `long` 字段可靠地保证字段独占 cache line。`@Contended` 不是 Android 公共 SDK 契约。应用层更稳的方案是减少共享可变对象、分片计数、批量提交，并以基准测试验证。

### 不要把 MessageQueue 当作已证实案例

Android 17 的 `MessageQueue` 有 Legacy、Combined 与 CombinedDeli 等实现变体，字段布局还要经过 ART 对象布局。`mPtr` 与 `mMessages` 在源码中相邻，不能证明它们位于同一 cache line，更不能证明它们引发了可测 false sharing。

`enqueueMessage()` 与队列消费还包含锁、native 层的等待/唤醒（poll/wake）和主线程调度。没有 PMU、地址级采样和对照布局时，可以把它作为共享队列案例分析，但不能标记成 framework 已经存在 false sharing 的事实。

## C/C++ 数据布局：AoS、SoA 与 hot/cold split（冷热字段拆分）

### AoS 与 SoA 的选择由访问模式决定

Array of Structures（AoS，结构体数组）把一个元素的所有字段放在一起：

```cpp
struct Particle {
    float x, y, z;
    float vx, vy, vz;
    float r, g, b, a;
};
std::vector<Particle> particles;
```

这个结构每个元素为 40 字节（忽略额外对齐）。若循环只读 `x/y/z`，有用数据约占对象流量的 12/40，即 30%，并非固定的 18.75%（12/64）。cache line 还可能跨越两个对象，边界与数组起始地址有关。

Structure of Arrays（SoA，分字段数组）把同类字段拆成连续数组：

```cpp
struct ParticleBatch {
    std::vector<float> x, y, z;
    std::vector<float> vx, vy, vz;
    std::vector<float> r, g, b, a;
};
```

只更新位置时，SoA 能避免把颜色与速度数据一并载入 cache；处理一个粒子的全部字段时，AoS 可能更紧凑。还可以采用 Array of Structures of Arrays（AoSoA，分块结构体数组），按 SIMD（单指令多数据）宽度或 tile 分组，在向量化与单元素访问之间折中。

选择时测量以下指标：

- 目标循环端到端耗时；
- bytes processed / item（处理每个元素读取或写入的字节数）；
- L1D refill、LLC（last-level cache，末级 cache）miss 与 TLB miss；
- 向量化报告和生成代码；
- 内存占用与构造成本。

### hot/cold split 还要考虑对象生命周期

hot/cold split 会把每次迭代都读取的字段放入紧凑的热结构，把调试字符串、低频统计和错误信息放到 cold side（冷数据区），从而缩小热工作集。常见形式是：

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

不要用想象中的 `RenderNode` 布局证明方案。应对自己的结构运行 `sizeof` / `offsetof`，查看编译器输出的布局 dump，并执行能代表真实负载的 workload benchmark。

### 连续内存也有扩容与复制成本

`std::vector` 和 Binder `Parcel` 使用连续缓冲区，顺序读写具备空间局部性。但容量增长可能触发重新分配和复制。已知大小时合理调用 `reserve()` 可以减少扩容；过度预留则会增加 RSS（常驻内存）。

Android 17 `frameworks/native/libs/binder/Parcel.cpp` 中，`mData`、`mDataSize`、`mDataCapacity` 和 `mDataPos` 管理连续数据区，写入按 4 字节 padding，增长路径使用 `realloc` 或分配并复制。Parcel 另有对象偏移数组，读取也可以调整 data position，因此“Parcel 只能从头顺序读、不能随机访问”并不准确。

Parcel 的布局主要服务于 Binder 传输格式（wire format）、安全检查和对象管理，cache 局部性只是连续数据区带来的性质之一。它不足以证明“Parcel 总比 JSON 快”；序列化格式、数据规模、解析器和 IPC 拷贝都要纳入比较。

## Java/Kotlin 热路径：先减少工作，再谈对象池

### 避免装箱和指针追踪

在图像、音频、统计和几何运算中，可以优先评估 primitive array、紧凑 buffer 或专用 collection。`List<Float>` 的每个元素访问都要经过对象引用和装箱对象，这种逐级追踪引用的访问方式称为 pointer chasing；其数据密度通常低于 `FloatArray`。

这不意味着业务层的所有模型都要改成数组。对不在热点的代码，可读性与正确性更重要。常见做法是保留清晰的业务对象，只在性能分析已经证实的计算边界把数据转换为批量 buffer。

### 谨慎复用可变对象

ART 的线程局部分配路径很快，存活时间短的对象也可能在 GC 年轻代中高效回收。对象池则会引入以下成本：

- 状态重置不完整；
- 生命周期和线程安全更复杂；
- 池保留对象，扩大 live set（当前仍存活、无法被 GC 回收的对象集合）；
- 旧对象未必仍在目标 CPU 的 cache；
- 池自身产生锁竞争或共享写入。

`Message.obtain()` 的回收池只能说明 framework 在这个场景采用了特定复用策略，不能证明所有临时对象都适合池化。应用应先用 allocation profiler（分配分析器）、GC pause（垃圾回收停顿）、CPU 和内存数据确认分配成本，再比较“直接分配”“批量分配”“复用”三种方案。

### 分支与 cache 要分开归因

不可预测分支会造成 pipeline flush（清空流水线中推测执行的指令），间接跳转也会影响取指和译码；这些问题与 data-cache miss 属于不同机制。三元表达式不保证生成无分支指令，`__builtin_expect` 也只向编译器提供分支概率提示。

优化分支时要同时查看 `branch-misses`、生成后的机器码和端到端时间。把错误路径移出热函数可能改善指令布局，但函数内联、LTO（链接时优化）和 PGO（基于运行数据的优化）会再次改变代码，因此源码排列不能直接代表最终的 instruction-cache 布局。

### 是否手动 prefetch，要由实验决定

`__builtin_prefetch()` 是提示，编译器和硬件可以按各自规则处理。线性数组通常已有硬件预取；链表、树或多流访问有时能从软件 prefetch 获益。

prefetch 距离太近，数据可能来不及到达；距离太远，又可能提前挤出仍在使用的 cache line。目标地址不在页表中时，还可能增加地址转换工作。至少要在两类核心、冷/热数据和有/无并发负载下比较，并检查能耗；只看一次 microbenchmark（微基准）的 p50（中位数）结果，不足以支持把改动放入通用库。

## DEX 局部性：使用 Startup Profile，不手写不存在的开关

DEX 标识符与 class definitions（类定义）受格式排序约束，不能描述为“按源码出现顺序排列”。ART 的 AOT（Ahead-of-Time，预先编译）和 JIT（Just-in-Time，即时编译）产物也不会机械复制 DEX 顺序。

Android 当前的官方工具链让两类 profile（用于指导构建或运行时优化的配置文件）承担不同任务：

- Baseline Profile 供 ART 对常用方法进行 AOT 编译；
- Startup Profile 在构建期指导 R8/D8 优化 DEX 中启动代码的布局。

Startup Profile 让启动关键类和方法更集中，并尽量放入首个 `classes.dex`，从而减少启动阶段需要触及的代码页。收益可能同时来自 DEX page locality（代码页局部性）、page fault（缺页）减少、解压或映射过程变化，以及编译产物布局变化，不能全部归因于 instruction-cache miss。

### 当前构建要求

官方文档给出的版本边界是：

- DEX layout optimization 从 AGP 8.1 可用；
- AGP 8.1–8.2 需要在 Baseline Profile 配置中启用；
- AGP 8.3 起默认启用；
- release 构建需要开启 R8、minification 和完整优化；
- startup journey（启动场景的基准测试流程）通过 `includeInStartupProfile = true` 进入 Startup Profile。

`dexOptions.reorderClassesWithProfiling` 不是对应的公开 AGP 配置，不应出现在示例中。

### 生成、验证、A/B 测量

Startup Profile 应覆盖 launcher、常见 deep link（直接打开应用内指定页面的链接）、通知入口等真实启动路径，也要避免让大量与启动无关的 journey 占满首个 DEX。

验证时：

1. 用 APK Analyzer 查看 startup 类和方法是否进入预期 DEX；
2. AGP 8.8 及以上可检查 AAB 内 `BUNDLE-METADATA/com.android.tools/r8.json` 的 `"startup": true`；
3. 用 Macrobenchmark 分别测冷启动、温启动和多个入口；
4. 固定 APK、编译状态、设备温度和系统版本。

不要引用与当前应用、构建链无关的 Redex 百分比作为预期收益。官方给出的经验范围也只能用于决定是否实验，发布结论应来自自己的 A/B 数据。

## Simpleperf：从症状到证据

### 先查看设备支持哪些 PMU 事件

事件名和可用性取决于 CPU PMU、内核及权限。PMU 事件是硬件提供的计数项，用来统计周期、指令、cache miss 等微架构行为。采集前先运行：

```bash
simpleperf list
simpleperf list raw
simpleperf stat --print-hw-counter
```

第一条列出内核封装的事件，第二条列出当前 Arm PMU 直接暴露的 raw event（原始硬件事件），第三条显示可用硬件 counter（计数器）数量。不能假设每台设备都支持 `raw-l2-dcache-refill`，也不能把某个 Cortex 文档中的 event number 直接用于另一款 SoC。

### 先做成组计数

如果设备支持通用事件，可以先比较周期、指令和 cache 事件：

```bash
simpleperf stat \
  --group cpu-cycles,instructions \
  --group cache-references,cache-misses \
  -p <pid> --duration 10
```

同组事件会尽量同时调度，适合计算 IPC（instructions per cycle，每周期执行的指令数）或 miss ratio（未命中比例）。硬件 counter 不足时会发生 multiplexing（分时复用），输出中的 enabled/running 时间和警告必须保留。不同 cluster 可能使用不同 PMU，线程迁移也会影响结果解释。

不存在通用的“cache miss 超过 10% 就该优化”阈值。miss 的种类、每次 miss 的代价、memory-level parallelism（内存访问并行度）和业务 deadline（截止时间）都会影响结果。应该比较相同工作量下的前后变化，并确认 latency（延迟）或 throughput（吞吐量）也随之改善。

### 再做热点采样

确认 cache 事件与慢样本相关后，再定位符号：

```bash
simpleperf record \
  -e cache-misses:u \
  -p <pid> --duration 10 --call-graph dwarf
simpleperf report --sort dso,symbol
```

设备是否支持该事件采样、用户态过滤和 DWARF call graph（基于调试信息还原的调用栈），要通过 `simpleperf list` 与设备能力确认。采样结果只能定位事件出现在哪些指令附近，不一定包含被访问的数据地址，也不能单独证实 false sharing。

标记为 debuggable 或 profileable 的应用可以使用 Simpleperf 的应用分析流程。不要把关闭 SELinux 强制模式的 `setenforce 0` 写成普通开发步骤；量产设备的 PMU 与 tracing 权限由系统安全策略决定。

### 低 IPC 不能单独证明 memory-bound（主要受内存访问限制）

IPC 低还可能来自：

- branch miss 或 instruction-cache / TLB 压力；
- 长依赖链；
- 锁等待附近的短运行片段；
- 指令前端或执行后端的 stall（停顿）；
- 不同核心宽度与频率；
- PMU multiplexing 或统计窗口错误。

判断负载是否 memory-bound，至少需要观察 cache/TLB refill、backend stall（执行后端停顿）、内存带宽或访问延迟采样中的一部分，并通过改变数据布局或工作集进行可控实验。

Perfetto 的 sched、CPU frequency、thread state 和应用 slice（带起止时间的自定义事件区间）可以提供时间上下文。默认 trace 不会自动产生每线程 instructions/cycles，也不存在一段可直接套用的通用 SQL，能把任意 counter 按线程换算成 IPC。可以用相同 workload 的时间窗口关联 Simpleperf 与 Perfetto，但需注明数据来自两次采集还是同一次采集。

### False sharing 需要地址级证据

普通 cache-miss 采样只能提示热点。定位 false sharing 通常需要：

- 支持 Arm SPE（Statistical Profiling Extension，统计分析扩展）的设备；
- 内核提供的 perf data-source（访存来源）信息；
- `perf c2c`（cache-to-cache 分析）或等价的厂商工具；
- 带符号信息的 binary（二进制文件）；
- 结构体布局信息，例如 `pahole` / `offsetof`。

这些条件在量产 Android 手机上经常无法全部满足。可行的替代实验是固定线程和工作量，只改变计数器分片或字段间距，同时比较吞吐量、atomic retry、cache event 与功耗。若无法得到地址级证据，结论应写成“现象与共享 cache line 竞争一致”，不要声称已经定位到某个字段。

## Android 17 源码中的局部性设计

### ART CardTable：一字节表示 1 KiB 堆区间

Android 17 ART 的 `CardTable`（卡表）定义 `kCardShift = 10`，因此卡表中的每个 byte 对应 1 KiB heap（堆内存）区间。对象引用的 write barrier（写屏障）会把对应 byte 标为 `kCardDirty`，GC 随后只需扫描这些 dirty card（脏卡）覆盖的堆区间。

`CardTable::Create()` 为表额外分配 256 字节，并调整 `biased_begin`，使其地址低字节等于 `kCardDirty`。源码注释说明，这样 JIT 生成的写屏障不必另行构造或加载 dirty 常量，可以减少生成代码中的指令。

可确认的边界是：

- card granularity 是 1 KiB heap / 1 byte table；
- biased base（带偏置的基地址）用于高效计算 card 地址并写入 dirty 状态；
- dirty、aged、aged2 是 GC 状态。

不能从这些常量推出“每次写屏障节省一条 cache line”或固定的性能百分比。实际指令序列依赖 ISA（指令集架构）、编译器后端和运行模式；多个 mutator（并发修改堆的应用线程）写入相邻的 card byte，也不等于已经观测到 false sharing。

### Binder Parcel：连续数据与独立对象表

Android 17 `Parcel` 的普通数据存储在 `mData` 连续缓冲区，通过 `mDataPos` 顺序写入，并按 4 字节边界 padding。容量不足时 `growData()` 扩大缓冲区，`continueWrite()` 负责所有权与复制。Binder 对象位置另存于 `mObjects` 或 RPC object-position 容器。

这套布局方便顺序序列化和内核 Binder 处理，也能减少普通字段的指针追踪。与此同时，扩容、对象验证、FD 复制和大 blob（二进制数据块）仍可能成为主要成本。源码结构只能解释数据放在哪里，性能结论仍要通过具体 transaction 测量。

### Linux cache 对齐宏表达了取舍

内核 6.18 的 `include/linux/cache.h` 提供：

- `__read_mostly`，把热路径会读取、但很少修改的数据集中到特定区域；
- `__cacheline_aligned` / `____cacheline_aligned_in_smp`；
- cacheline group begin/end；
- `cache_line_size()`。

文件注释明确要求谨慎使用 `__read_mostly`，并根据性能分析结果决定是否采用。紧凑排列可以减少读取的 cache line 数，对齐隔离则会增加空间占用。应用层可以借鉴这套决策顺序，但不能直接复制内核宏，也不应让所有结构都独占一条 cache line。

### 删除与 cache 无关的伪案例

PSS（按共享比例折算后的进程内存）中的 Dalvik/native/other 分类用于内存归因，不能说明所谓的“cache 流分离”。`anon_huge_pages`、`file_pmd_mapped` 等 smaps 字段反映大页映射状态，也不能用来避免 false sharing。它们属于内存统计和 TLB/页表主题，不应作为 Android 17 cache 优化案例。

同样，Linux 的 SLUB slab allocator（小对象分配器）不会把所有对象统一向上取整到 cache-line 大小的整数倍；具体 alignment（对齐方式）取决于架构、cache flags、对象大小和创建参数。16 KiB page 对 slab order（一个 slab 占用的连续页阶数）、内存碎片和 TLB 的影响，也需要单独测量。

## 一套可执行的优化流程

### 1. 固定业务指标

先选择用户可感知或系统必须满足的指标：帧耗时、启动时间、音频 deadline、每秒处理量、单次能量。cache counter 只是用来解释现象的硬件计数，不能取代业务指标。

### 2. 找到 CPU 热点

用 Perfetto 确认线程何时在运行、是否被抢占或迁移；用 Simpleperf 的 cycles / instructions 找 CPU 热点。若线程多数时间阻塞，先查锁、I/O 或 Binder。

### 3. 验证 memory hierarchy 假设

在设备支持范围内加入 cache、TLB 和 stall 事件。改变工作集大小、遍历顺序或字段布局，观察硬件事件与业务耗时是否出现可重复、方向一致的变化。

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

至少要在目标机型的常见调度状态下重复实验。不要为了 cache 实验把生产代码永久绑核；可以在受控 benchmark 中记录实际运行的 CPU，并分别观察性能核和能效核。长时间负载还要记录 thermal（温度与热限制状态）和频率，避免把降频差异误认为 cache 收益。

### 6. 检查代价

布局优化可能增加：

- RSS 与 allocator 产生的内存碎片；
- TLB miss；
- 初始化和转换成本；
- 代码复杂度；
- 低端设备上的工作集；
- 多份数据的一致性维护。

只有业务指标在代表性设备和输入上稳定改善，改动才值得保留。

## 结论

Cache 友好代码要让“经常一起使用的数据”在时间和地址上靠近，并减少“被不同 CPU 频繁写的数据”之间的 cache line 共享。实现方式会随语言层变化：

- Kotlin/Java 优先减少装箱、指针追踪和共享可变状态；
- 业务缓存用受控权重、加载去重和必要时的冷热分段保护真实热集；
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

## 参考资料

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
- [AOSP Android 17 `LruCache`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/util/LruCache.java)
- [Arm Cortex-A processor comparison](https://developer.arm.com/documentation/109140/latest/)
