---
title: "缓存优化实战：冷热端分离、重排序与 CPU 缓存命中率提升"
chapter: "21.15"
section: "21.15"
status: ready-for-review
applicable_versions: "Android 8 (API 26) - Android 17 (API 37)"
last_verified: "2026-07-16"
last_verified_against: "AOSP android-17.0.0_r1; ARM Cortex-A Technical Reference Manual; developer.android.com/topic/performance"
confidence: medium
tags: [cache, cpu, cache-locality, cache-line, lru, redex, dex-layout, performance]
related_chapters: ["21.1", "21.4", "21.6", "21.14", "5.1", "27.1"]
sources:
  - type: clippings-structure
    path: "[结构参考: Clippings/Android 性能优化 - 缓存优化：冷热端分离+重排序，提升缓存命中率]"
  - type: clippings-structure
    path: "[结构参考: Clippings/Android 性能优化 - 原理：重新认识应用的速度优化]"
  - type: official
    path: "https://developer.android.com/topic/performance/baselineprofiles/overview"
  - type: official
    path: "https://developer.android.com/topic/performance/startupprofiles/dex-layout-optimizations"
  - type: aosp
    path: "art/dex2oat/dex2oat.cc (DEX layout 编译入口)"
  - type: aosp
    path: "libcore/libart/src/main/java/dalvik/system/VMRuntime.java"
  - type: tool
    path: "https://github.com/facebook/redex"
---

# 缓存优化实战：冷热端分离、重排序与 CPU 缓存命中率提升

“缓存优化”在 Android 工程里至少指三种机制：

- `LruCache` 命中：业务对象或计算结果是否还在应用的内存缓存中；
- CPU cache 命中：处理器访问的指令或数据是否位于硬件 cache；
- DEX 局部性：启动时需要读取的类与方法是否集中在较少的文件页。

三者可能互相影响，却没有一一对应关系。把更多图片留在 `LruCache` 中，业务命中率可能提高，同时也会扩大 Java/native live set、增加 GC 和内存带宽压力。Startup Profile 改善的是 DEX 文件布局，不能直接宣称 L1 instruction cache miss 一定下降。

校验锚点为 Android 17 / API 37 / `android-17.0.0_r1` 和 common kernel `android17-6.18-2026-06_r6`，重点讨论应用可控的做法。更完整的硬件局部性与 false sharing 原理见[CPU Cache 友好代码与数据布局](../../part1-fundamentals/ch05-cpu-power/14-cpu-cache-friendly-code-data-layout.md)，DEX 构建流程见[Baseline Profile 与 Startup Profile 实战](./04-baseline-profile-practice.md)。

## 1. 先把硬件 cache 模型说准

移动 CPU 常见每核私有的 L1 instruction/data cache、每核或一组核心共享的 L2，以及 cluster 或 SoC 级共享 cache。容量、关联度、包含关系和访问延迟都由具体 CPU 与 SoC 决定，不能用一张固定的“L1 4 cycles、L2 20 cycles、DRAM 200 cycles”表代表所有 Android 设备。

CPU 从下一级层次填充 cache 时以 cache line 为单位。Android 17 common kernel 的 arm64 `cache.h` 定义 `L1_CACHE_SHIFT = 6`，对应 64 字节 L1 基线；同一文件又把 `ARCH_DMA_MINALIGN` 定义为 128 字节。64 字节可以作为当前 arm64 应用实验的起点，却不能扩展成所有 CPU、DMA 和一致性粒度都使用同一个数值。

common kernel 6.18 还通过 sysfs ABI 描述 cache 的 `level`、`type`、`size`、`coherency_line_size` 和 `shared_cpu_list`。下面的命令用于查看一台测试设备实际暴露的 CPU0 cache 拓扑。

```bash
adb shell 'for dir in /sys/devices/system/cpu/cpu0/cache/index*; do
  echo "$dir"
  for field in level type size coherency_line_size shared_cpu_list; do
    printf "%s=" "$field"
    cat "$dir/$field"
  done
done'
```

输出要按设备保存。部分量产机可能隐藏某些属性，CPU0 的层次也不能代表所有异构核心；需要时继续读取其他 `cpu*/cache/index*` 目录，并用 `shared_cpu_list` 去重共享实例。

### 1.1 cache miss、page fault 与逻辑 miss

这几个词不能混用：

| 事件 | 所在层次 | 表示什么 |
| --- | --- | --- |
| CPU cache miss/refill | PMU / 微架构 | 当前 cache 层没有目标 line，需要从其他 cache 或内存层次取得 |
| TLB miss | 地址翻译 | TLB 中没有所需虚拟地址翻译，需要页表遍历 |
| minor/major page fault | 内核虚拟内存 | 页表或文件页尚未按当前访问建立；major fault 还可能等待存储 |
| `LruCache` miss | 应用数据结构 | key 不在应用缓存，需要加载或计算 |

一次 LLC miss 落到 DRAM 不等于 page fault；页面已经驻留时也会发生硬件 cache miss。反过来，DEX 文件布局可能减少需要触及的文件页，却不能仅凭 page-fault 下降推导 L1/L2 miss 同比例下降。

### 1.2 调度提示不等于绑大核

线程迁移到另一核心后，新核心的私有 cache 可能没有近期工作集，但一致性系统仍维护数据可见性，原核心 cache 也不会因为迁移被软件整体清空。迁移成本取决于共享 cache、cluster、工作集、频率和同期带宽竞争。

`PerformanceHintManager` 让应用向系统提交相关线程、目标工作时长和实际工作时长。系统可以据此调整策略，但 API 没有承诺把线程放到某个“大核”，也没有承诺降低 cache miss。生产代码通过 `sched_setaffinity()` 固定所谓大核，会绕过系统对负载、热状态、cpuset 和能耗的判断。调度细节见[线程池与并发性能](./14-thread-pool-concurrency-performance.md)。

## 2. 冷热端分离解决的是缓存污染

Android 17 的 `android.util.LruCache` 使用 `LinkedHashMap` 的 access-order 模式。命中会把条目移到队列头部，超出容量后逐出最久未访问条目。单个公开操作是线程安全的；由多次 `get`、`remove`、`put` 组成的复合操作仍要由调用方提供原子边界。

LRU 对稳定的时间局部性很有效，弱点是 scan pollution：一批只访问一次的新 key 可以占满队列，并逐出稍早访问、之后还会复用的条目。图片大列表、分页预取和一次性文档浏览都可能出现这种访问形状。

### 2.1 用 probation/protected 两段代替全表计数

一个低开销方案是 SLRU 风格的两段缓存：

- 新条目进入 probation 段；
- probation 条目再次命中后进入 protected 段；
- protected 超出预算时，将最久未访问条目降回 probation；
- probation 超出预算时，逐出最久未访问条目。

这样，一次扫描只会竞争 probation 预算。它不需要每次插入时遍历所有条目做“访问次数衰减”，也不会引入无上限的计数器。两段容量比例没有通用答案，应由 key 分布、value 大小、重复访问间隔和内存预算决定。

下面的 Kotlin 实现展示带权重、单锁保护的核心状态机。它省略了异步加载与资源释放回调，便于把晋升、降级和逐出规则看清楚。

```kotlin
import java.util.LinkedHashMap

class SegmentedLruCache<K : Any, V : Any>(
    private val probationMaxWeight: Int,
    private val protectedMaxWeight: Int,
    private val weightOf: (K, V) -> Int = { _, _ -> 1 },
) {
    private data class WeightedValue<V>(
        val value: V,
        val weight: Int,
    )

    private val probation =
        LinkedHashMap<K, WeightedValue<V>>(0, 0.75f, true)
    private val protectedSegment =
        LinkedHashMap<K, WeightedValue<V>>(0, 0.75f, true)

    private var probationWeight = 0
    private var protectedWeight = 0

    init {
        require(probationMaxWeight > 0)
        require(protectedMaxWeight > 0)
    }

    @Synchronized
    fun get(key: K): V? {
        protectedSegment[key]?.let { return it.value }

        val entry = probation.remove(key) ?: return null
        probationWeight -= entry.weight
        protectedSegment[key] = entry
        protectedWeight += entry.weight
        trimProtected()
        return entry.value
    }

    @Synchronized
    fun put(key: K, value: V): V? {
        val weight = weightOf(key, value)
        require(weight in 1..probationMaxWeight) {
            "entry weight must fit the probation segment"
        }
        val replacement = WeightedValue(value, weight)

        protectedSegment.remove(key)?.let { previous ->
            protectedWeight -= previous.weight
            protectedSegment[key] = replacement
            protectedWeight += replacement.weight
            trimProtected()
            return previous.value
        }

        val previous = probation.remove(key)
        if (previous != null) {
            probationWeight -= previous.weight
        }
        probation[key] = replacement
        probationWeight += replacement.weight
        trimProbation()
        return previous?.value
    }

    @Synchronized
    fun clear() {
        probation.clear()
        protectedSegment.clear()
        probationWeight = 0
        protectedWeight = 0
    }

    private fun trimProtected() {
        while (
            protectedWeight > protectedMaxWeight &&
            protectedSegment.isNotEmpty()
        ) {
            val (key, entry) = takeEldest(protectedSegment)
            protectedWeight -= entry.weight
            probation[key] = entry
            probationWeight += entry.weight
        }
        trimProbation()
    }

    private fun trimProbation() {
        while (
            probationWeight > probationMaxWeight &&
            probation.isNotEmpty()
        ) {
            val (_, entry) = takeEldest(probation)
            probationWeight -= entry.weight
        }
    }

    private fun takeEldest(
        map: LinkedHashMap<K, WeightedValue<V>>,
    ): Pair<K, WeightedValue<V>> {
        val iterator = map.entries.iterator()
        val eldest = iterator.next()
        val result = eldest.key to eldest.value
        iterator.remove()
        return result
    }
}
```

`LinkedHashMap` 的 access-order 读取会修改内部顺序，所以两个 segment 的所有访问都放在同一把锁内。`weightOf` 返回值在条目存活期间必须稳定；图片可用实际 byte count，普通对象只能选择团队能够维护的近似权重。若 value 持有 Bitmap、文件句柄或其他待释放资源，还要收集逐出项，并在锁外执行释放回调，避免重入和长时间占锁。

### 2.2 上线前要同时观察收益与代价

分段 LRU 适合有明显“一次扫描 + 稳定热集”的 workload。均匀随机访问、工作集远大于预算或 key 很少复用时，两段结构可能只增加查找和迁移成本。

A/B 至少记录：

- 逻辑 hit、miss、逐出、晋升和降级次数；
- miss 后的解码、磁盘、数据库或网络成本；
- 缓存总权重、Java/native heap、PSS 和 GC；
- 主线程与后台线程耗时；
- 按入口、页面和设备档位拆分的端到端延迟。

命中率上升但 PSS、GC 或锁等待恶化时，缓存并没有给用户带来净收益。Android 内存压力回调到来后，应按产品恢复成本缩容或清理；不要为了维持命中率长期保留所有热条目。

### 2.3 避免热点 key 并发失效和错误复合操作

`LruCache.create()` 在内部锁之外计算 value。多个线程同时 miss 同一个 key 时，可能并行创建多个 value，缓存会保留其中一个并通过 `entryRemoved()` 交还其他结果。这是源码定义的行为。

如果加载成本很高，应在缓存外为相同 key 合并 in-flight 请求，并明确失败是否缓存、失败条目多久重试。不要简单把磁盘、网络或图片解码放进全局 cache 锁；那会把缓存查找变成串行 I/O。

## 3. Java/Kotlin 数据布局的可控边界

### 3.1 对象数组只连续保存引用

`Array<MyObject>` 和 `ArrayList<MyObject>` 的 backing array 连续保存对象引用，对象本体仍由 ART 放在 managed heap 中。它们不能当作 C/C++ 的 `Particle particles[]`，也不能由“一个 64 字节 line 能放四个对象”推导遍历 miss 数量。

`LinkedList` 每个节点独立分配并需要指针追踪；`ArrayList` 通常减少节点对象并改善引用遍历。收益还会受到元素对象访问、扩容、索引操作和算法复杂度影响。没有目标设备基准时，不应写固定的 8 倍或 9 倍数字。

对于图像、音频、统计、几何和模型预处理等批量数值路径，primitive array 能提供更紧凑的数据。下面的 SoA 形式只读取坐标时不会把颜色字段一起拉入热循环。

```kotlin
class ParticleColumns(capacity: Int) {
    val x = FloatArray(capacity)
    val y = FloatArray(capacity)
    val z = FloatArray(capacity)
    val color = IntArray(capacity)

    fun squaredDistanceSum(): Float {
        var sum = 0f
        for (index in x.indices) {
            val px = x[index]
            val py = y[index]
            val pz = z[index]
            sum += px * px + py * py + pz * pz
        }
        return sum
    }
}
```

这项改动的收益可能同时来自减少装箱、减少对象数量、顺序访问和编译器优化。结论应写成“该数据表示在当前 workload 更快”，不能把全部差值都归给 CPU cache。若常见操作每次都要读取一个粒子的全部字段，AoS 或分块的 AoSoA 也可能更合适。

普通 RecyclerView 数据源常由图片请求、绑定、布局和绘制主导。只有 profile 显示大批量模型遍历占据 CPU 热点时，才值得把业务对象转换为列式数据；转换时间和双份内存也要进入结果。

### 3.2 Java 字段声明顺序不能控制 cache line

Android 17 ART 的 `ClassLinker::LinkFieldsHelper::LinkFields()` 会先放引用字段，再按 long、double、int、float、char、short、boolean、byte 的顺序处理基本类型，并尝试填充对齐空隙。同一类型还按 DEX field index 排序。

因此，把源码中的“热字段”声明在类前面，不能保证它们位于对象的前 64 字节，也不能保证两个字段落在同一 line。R8 重写、继承关系、引用压缩和 ART 实现都会影响最终布局。Java/Kotlin 应优先通过拆分数据结构、减少对象和改用 primitive buffer 改善局部性。

### 3.3 Android 上的 `@Contended` 是 no-op

`jdk.internal.vm.annotation.Contended` 不是 Android 公共 SDK。Android 17 libcore 源码还明确写明它在 Android 上是 no-op，并把 retention 改为 `SOURCE`。普通 App 不能靠 VM 参数把它变成可靠的 padding 契约。

怀疑 false sharing 时，先减少共享写入：

- 每线程或每任务局部累计，批量归并；
- 按 shard 分散计数器；
- 避免循环中反复写入相同状态；
- 把高频写状态从大块只读配置中拆出；
- 在 NDK 中需要精确布局时，用 `alignas`、`sizeof` 和 `offsetof` 校验目标 ABI。

手写若干无用 `long` 字段也没有稳定的 cache-line 隔离保证。普通 PMU cache-miss 计数只能提示访存压力，不能单独证明某两个字段发生 false sharing；可靠结论还需要地址级采样或只改变共享布局的对照实验。

### 3.4 对象池不保证保留 CPU 热度

ART 的短命对象分配路径很快，对象池会延长对象生命周期，并引入重置、所有权、同步和泄漏风险。一个回收到池里的对象下次取出时，未必仍位于当前核心的 cache。

对象池只适合分配与回收已被证实是瓶颈、对象重置可验证、池上限清晰的场景。启动路径应同时比较直接分配、批量分配和复用方案，并观察 allocated bytes、GC、live set、CPU time 与 TTID/TTFD。相关 GC 边界见[ART GC 与启动性能](./11-art-gc-suppression-startup-performance.md)。

## 4. DEX 重排序优化的是文件页局部性

启动期间，ART 可能查找、验证、解析或执行多个 DEX 中的类与方法。启动代码分散时，进程需要触及更多 DEX 区域。构建期把常见入口所需代码集中到 primary DEX 的局部区域，可以减少文件页访问、fault 和相关加载工作。

这条路径不应描述成“预读一个 cache line 就得到下一个类”。DEX 项、文件页、ART metadata、AOT/JIT code cache 和 CPU instruction cache 是不同层次。

### 4.1 Baseline Profile 与 Startup Profile

| Profile | 消费时机 | 主要作用 |
| --- | --- | --- |
| Baseline Profile | 安装或设备编译阶段由 ART 使用 | 让选中的常用方法更早得到合适的编译 |
| Startup Profile | 构建阶段由 R8 使用 | 调整启动类和方法在 DEX 文件中的布局 |

官方建议同时使用两者。Startup Profile 是 Baseline Profile 规则的启动子集，但 Library 不能独立贡献 Startup Profile；App 必须覆盖自己的 launcher、常用 deep link、通知等主要启动入口。

当前构建边界包括：

- DEX layout optimization 从 AGP 8.1 可用；
- AGP 8.1–8.2 需要显式启用，AGP 8.3 起默认启用；
- release 构建需要启用 R8、minification 和完整优化；
- `BaselineProfileRule.collect(..., includeInStartupProfile = true)` 生成启动规则；
- 生成文件位于 `src/<variant>/generated/baselineProfiles/startup-prof.txt`，由 AGP 消费。

规则过宽会让启动代码溢出首个 DEX，并增加文件与构建成本。生成后要用 APK Analyzer 检查关键类所在 DEX；AGP 8.8+ 还可查看 AAB 中 `r8.json` 的 DEX `"startup": true` 标记。操作步骤与 A/B 设计见[Baseline Profile 与 Startup Profile 实战](./04-baseline-profile-practice.md)。

### 4.2 不从 Baseline Profile 推导 native code 排列

Baseline Profile 可以改变安装期编译覆盖和运行时 JIT 工作量。没有 `dex2oat` 产物、符号和 profile 布局证据时，不能继续声称它会按调用频率把所有高频 native code 相邻排列，也不能把启动收益全部归为 instruction-cache 改善。

测量时应把两个变量拆开：

- 保持 DEX 布局一致，对比 Baseline Profile 的编译收益；
- 保持 Baseline Profile 和安装编译状态一致，对比 Startup Profile 的 DEX 布局收益。

### 4.3 ReDex 只适合已有工具链的团队

[ReDex](https://github.com/facebook/redex) 是独立的 DEX 优化框架，`InterDexPass` 可消费 `coldstart_classes` 列表安排 cold-start 类。其官方文档仍给出了从 HPROF 提取类列表并运行 InterDex 的流程。

新项目优先采用 AGP、R8 和 Startup Profile。Android 官方 R8 文档提醒，其他工具在 R8 之后改写 DEX 可能破坏 R8 优化或 Baseline Profile。已经使用 ReDex 的项目需要同时验证：

- pass 顺序、mapping、资源与反射规则；
- Baseline/Startup Profile 是否仍与最终 DEX 对应；
- APK/AAB 签名与安装流程；
- Android 8–17 目标设备上的 verifier、启动和功能回归；
- 最终包体、DEX mmap、TTID/TTFD 与故障率。

不能仅凭 ReDex 能读写 DEX 就宣布 Android 17 兼容，也不能把某个旧版本的冷启动收益当作当前应用预期。

## 5. 用 Simpleperf 和 Perfetto 验证假设

PMU 事件取决于 CPU、内核与权限。Android 17 的 Simpleperf 文档要求先用 `list` 查看设备可用事件；异构核心还可能支持不同 raw event。量产非 root 设备通常只能分析 debuggable 或 `<profileable android:shell="true" />` 的应用。

下面的命令先查看事件和硬件 counter 数量，再在应用已运行时成组统计 cycles/instructions 与通用 cache 事件。

```bash
adb shell simpleperf list
adb shell simpleperf stat --print-hw-counter

adb shell simpleperf stat \
  --app com.example.app \
  --group cpu-cycles,instructions \
  --group cache-references,cache-misses \
  --duration 10
```

只有 `simpleperf list` 确认事件可用时才运行对应组。`--group` 尽量让组内事件同时计数，便于计算 IPC 或 miss ratio；PMU counter 不足时仍可能失败或发生 multiplexing，报告中的 enabled/running 比例和警告必须保留。线程在不同 cluster 之间迁移时，事件定义和计数覆盖也要纳入解释。

`simpleperf stat` 给出窗口汇总。确认 cache 事件随性能退化同向变化后，可以用 `simpleperf record` 对受支持事件采样并生成调用栈；采样命中的指令地址不一定包含被访问数据地址，因此仍不能仅靠普通调用栈定位 false sharing。

Perfetto 的正确数据源名称是 `linux.perf`。它可以采集 perf counter 或 callstack sample，并与 `linux.ftrace` 的调度、CPU frequency、进程和应用 trace 对齐。Android 设备权限、PMU 与 Perfetto producer 能力各不相同；缺失轨道表示本次配置或设备没有提供数据，不能按 0 miss 处理。

### 5.1 端到端指标必须与 PMU 同时改善

硬件计数器是解释信号，验收仍以 workload 为准：

| 改动 | 主指标 | 辅助证据 | 必查代价 |
| --- | --- | --- | --- |
| LRU → 分段 LRU | miss 后总延迟、滚动或启动指标 | 逻辑 hit/miss、逐出 | PSS、GC、锁等待、错误率 |
| boxed collection → primitive arrays | ns/item、吞吐或帧耗时 | cycles、instructions、cache/TLB event | 转换成本、双份数据、可维护性 |
| 共享计数 → 分片归并 | 吞吐、尾延迟 | atomic retry、cache event、CPU migration | 汇总延迟、内存 |
| 加入 Startup Profile | TTID/TTFD | DEX 分布、page fault、DEX mmap | 包体、构建、入口覆盖 |

miss rate 下降但执行指令数大幅增加，应用可能更慢；miss rate 上升但算法少做了很多工作，端到端时间也可能变好。没有通用的“cache miss 超过 10%”告警线。

### 5.2 可重复实验的最低要求

- 使用 release-like、profileable 构建，不用 Debug 结果替代发布判断；
- 固定输入、页面、线程数、安装与编译状态；
- 记录设备、SoC、API、kernel、温度、刷新率和电量条件；
- 微循环用 AndroidX Microbenchmark，启动或滚动用 Macrobenchmark；
- 同一设备交错运行 baseline 与 candidate，报告分布和样本量；
- 一次只改变一个主要变量；
- 同时保存 Perfetto、Simpleperf 输出和构建产物信息。

CPU-bound 数值循环适合看 PMU。线程大部分时间等待 Binder、I/O、锁或网络时，应先处理等待链；cache line 重排无法缩短外部依赖。

## 6. 检查清单

- [ ] 业务 `LruCache` miss、CPU cache miss 和 page fault 使用不同指标名。
- [ ] cache 容量、line size 和共享拓扑来自目标设备或可信硬件资料。
- [ ] 没有使用固定 cycles、SoC cache 容量或倍率冒充通用事实。
- [ ] 没有把 ADPF 描述成大核绑定，也没有在生产代码硬绑核心。
- [ ] 分段 LRU 的两段操作具有共同原子边界，并按 weight 管理容量。
- [ ] 缓存 A/B 同时观察命中率、miss 成本、PSS、GC 和锁等待。
- [ ] `Array<MyObject>` 没有被当作连续对象数组。
- [ ] Java 字段声明顺序没有被用作 cache-line 布局契约。
- [ ] Android App 没有依赖 `@Contended` 或 VM 参数实现 padding。
- [ ] 对象池有 allocation/GC 数据和上限，未依赖“对象仍在 CPU cache”的假设。
- [ ] Startup Profile 与 Baseline Profile 的消费者和作用分开说明。
- [ ] DEX layout 收益以文件页与启动指标解释，没有直接等同于 L1 I-cache。
- [ ] Simpleperf 事件先用 `list` 确认，并保留 multiplexing 信息。
- [ ] PMU 变化与端到端 latency、throughput 或帧指标一起验收。

## 小结

冷热端分离、数据重排和 Startup Profile 分别作用于应用淘汰策略、进程内数据表示和 APK 的 DEX 文件布局。将它们都叫“提高缓存命中率”容易掩盖测量口径：分段 LRU 看逻辑 hit/miss，primitive array 看数值路径的端到端耗时与 PMU，Startup Profile 看 DEX 分布、文件页和 TTID/TTFD。

Android 17 上，Java 对象字段由 ART 排列，`@Contended` 对 App 没有效果，ADPF 也不承诺指定 CPU。可维护的做法是减少无效工作和指针追踪、限制共享写入、使用带预算的缓存策略，并在目标设备上让业务指标与底层证据相互印证。

## 参考资料

- [Android 17 `LruCache.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/util/LruCache.java)：access-order、容量、线程安全和 `create()` 并发语义。
- [Android 17 ART `ClassLinker::LinkFields`](https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/runtime/class_linker.cc)：对象字段类型排序与空隙填充。
- [Android 17 libcore `Contended.java`](https://android.googlesource.com/platform/libcore/+/refs/tags/android-17.0.0_r1/ojluni/src/main/java/jdk/internal/vm/annotation/Contended.java)：Android no-op 与 `SOURCE` retention。
- [Android common kernel 6.18 arm64 `cache.h`](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/arch/arm64/include/asm/cache.h)：L1 cache line 基线和 DMA alignment。
- [Android common kernel 6.18 CPU cache sysfs ABI](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/Documentation/ABI/testing/sysfs-devices-system-cpu)：cache 层级、类型、大小、line size 和共享 CPU 属性。
- [Android 17 Simpleperf command reference](https://android.googlesource.com/platform/system/extras/+/refs/tags/android-17.0.0_r1/simpleperf/doc/executable_commands_reference.md)：事件枚举、group、multiplexing 和应用分析权限。
- [Perfetto performance counters and CPU profiling](https://perfetto.dev/docs/quickstart/callstack-sampling)：`linux.perf`、perf counter 与调用栈采样。
- [PerformanceHintManager API](https://developer.android.com/reference/android/os/PerformanceHintManager)：hint session 的线程与工作时长契约。
- [Create Startup Profiles](https://developer.android.com/topic/performance/startupprofiles/dex-layout-optimizations)：AGP/R8 要求、生成和 DEX layout。
- [Debug Baseline and Startup Profiles](https://developer.android.com/topic/performance/baselineprofiles/debug-baseline-profiles)：APK Analyzer 与 `r8.json` 验证。
- [Enable app optimization with R8](https://developer.android.com/topic/performance/app-optimization/enable-app-optimization)：完整 R8 优化及后处理工具风险。
- [ReDex InterDex](https://fbredex.com/docs/technical_details/interdex/)：`coldstart_classes`、InterDex 配置与验证方式。
