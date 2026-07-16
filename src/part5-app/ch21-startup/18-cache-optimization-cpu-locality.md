---
title: "缓存优化实战：冷热端分离、重排序与 CPU 缓存命中率提升"
chapter: "21.18"
section: "21.18"
status: ready-for-review
applicable_versions: "Android 8 (API 26) - Android 17 (API 37)"
drafted_date: "2026-07-16"
last_verified: "2026-07-16"
last_verified_against: "AOSP android-17.0.0_r1; ARM Cortex-A Technical Reference Manual; developer.android.com/topic/performance"
confidence: medium
tags: [cache, cpu, cache-locality, cache-line, lru, redex, dex-layout, performance]
related_chapters: ["21.1", "21.4", "21.6", "21.12", "5.1", "27.1"]
created_by: "task2a-knowledge-gap"
created_date: "2026-07-16"
gap_source: "素材驱动(Clippings)"
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

# 21.18 缓存优化实战：冷热端分离、重排序与 CPU 缓存命中率提升

CPU 缓存命中率是影响应用性能的底层因素之一。与算法优化或多线程并发不同，缓存优化不改变程序的逻辑，而是通过改善数据在内存中的布局和访问模式，让 CPU 更高效地工作。本节从 Android 工程实践角度，介绍两个维度的缓存优化：**应用层的数据结构布局优化**（冷热端分离）与 **系统层的代码布局优化**（DEX 类重排序）。

关于 CPU 缓存与调度的底层原理，详见 5.1 节。本节聚焦"工程上如何改善缓存命中率"这个实战问题。

[结构参考: Clippings/Android 性能优化 - 缓存优化：冷热端分离+重排序，提升缓存命中率]
[结构参考: Clippings/Android 性能优化 - 原理：重新认识应用的速度优化]

## CPU 缓存层次与 Android 设备特性

### ARM 缓存层级模型

Android 设备的 CPU 缓存层级从快到慢依次为：寄存器 → L1 Cache → L2 Cache → L3/LLC（Last Level Cache）→ 主存（DRAM）。每一级的访问延迟和容量差异显著：

| 层级 | 典型容量 | 典型延迟（cycles） | 说明 |
|------|---------|-------------------|------|
| 寄存器 | 数十个 | 1 | CPU 直接访问，由编译器分配 |
| L1 I-Cache / D-Cache | 32-128 KB | 1-4 | 分指令/数据，私有于每个核心 |
| L2 Cache | 256 KB - 1 MB | 10-20 | 通常私有于核心，部分架构共享 |
| L3 / LLC | 2-8 MB | 30-100 | 多核共享，SoC 级别配置 |
| 主存 (DRAM) | 4-16 GB | 100-300+ | 所有核心共享 |

**Cache Line 是缓存的最小传输单位**，ARM 和 x86 主流架构上均为 64 字节。当 CPU 需要读取一个 4 字节的数据时，硬件会一次性将包含该数据的整个 64 字节 cache line 从下一级存储加载进来。如果紧随其后的数据也在这 64 字节内，就不用再次访问慢速存储。

### big.LITTLE / DynamIQ 架构差异

[已验证: ARM DynamIQ 技术文档]

现代 Android SoC 普遍采用 ARM big.LITTLE 或 DynamIQ 架构，不同核心簇的缓存配置不同：

- **大核（Cortex-X 系列）**：L2 通常 512KB-1MB，独享；可优先访问 LLC
- **中核（Cortex-A7x 系列）**：L2 通常 256-512KB；共享 LLC
- **小核（Cortex-A5x 系列）**：L2 通常 128-256KB；共享 LLC

这意味着同一个线程在大核和小核上运行时，可用的缓存容量差异可达 2-4 倍。对于缓存敏感型任务（如图片解码、大量数据遍历），绑定大核执行能显著降低 cache miss 率。这也是 ADPF Performance Hint Session 让系统优先在大核上调度关键线程的底层原因之一。

### Android 17 设备典型缓存配置

以高通骁龙 8 Gen 4 / 联发科天玑 9400 级别旗舰 SoC 为例：

- L1 I-Cache: 64-128 KB / 核心
- L1 D-Cache: 64-128 KB / 核心
- L2: 256 KB - 1 MB / 核心
- L3 / LLC: 8-12 MB，全 CPU 共享
- System Cache (SLC): 3-8 MB，GPU/CPU/Modem 共享

`[待验证]` 上述数据来自各 SoC 厂商公开的技术概览（Tech Brief），Android 17 GKI 不暴露详细的 cache topology。可通过 `getconf LEVEL1_DCACHE_LINESIZE` 或读取 `/sys/devices/system/cpu/cpu*/cache/` 在设备上确认实际值。

## 缓存命中率对应用性能的量化影响

### Cache miss 的代价

CPU 执行指令时，每遇到一次 cache miss，就需要从下一级存储加载数据。不同层级 miss 的代价：

- **L1 miss → L2 hit**：约 10 cycles 额外延迟
- **L2 miss → L3 hit**：约 40 cycles 额外延迟
- **L3 miss → DRAM**：约 100-300 cycles 额外延迟（即 page miss）

如果一个循环体内每次访问数据都触发 L1 miss，整体性能可以比 cache hit 场景慢 10-50 倍。这就是缓存优化被称为"免费的性能提升"的原因——不需要改变业务逻辑，只需要改善数据布局。

### 量化方法：simpleperf

使用 simpleperf 可以直接采集 cache 事件：

```bash
# 采集指定进程的 cache 命中/未命中事件
simpleperf stat -e cache-misses,cache-references -p <pid> -- sleep 5

# 输出示例：
# cache-misses:       1,234,567
# cache-references:   5,678,901
# Miss rate:          21.7%
```

在 Android 17 上，也可以通过 Perfetto 的 `linux/perf/perf_event` 数据源采集 cache 相关 PMU 事件，在 trace 中关联到具体的函数调用栈。

`[待验证]` 部分 ARM 核心的 cache-misses PMU 事件需要 `PERF_COUNT_HW_CACHE_*` 配置，不同 SoC 厂商的 PMU 实现可能有差异，建议在实际设备上用 `simpleperf list` 确认可用事件。

## 冷热端分离策略

### 问题场景：标准 LruCache 的命中率瓶颈

`LruCache` 是 Android 应用最常用的内存缓存方案，内部基于 `LinkedHashMap` 实现 LRU（最近最少使用）淘汰策略。在大多数场景下，LRU 是一个合理的选择，但在以下场景中命中率会明显下降：

**场景**：低端设备上的图片聊天应用。LruCache 容量受限（如只能缓存 10 张图片）。用户进入一篇图文丰富的公众号文章，大量新图片涌入，迅速将 LruCache 填满并淘汰了之前的缓存。但这些公众号图片只看一次就不会再访问，而被淘汰的恰恰是会话列表中反复使用的高频图片。

**根本原因**：LRU 的淘汰依据是"最近是否被使用"，而非"是否被频繁使用"。低频但刚访问过的数据会把高频但较早访问过的数据挤出去。

### 冷热端分离 LruCache 设计

针对上述问题，可以将单一 LruCache 拆分为**热端**和**冷端**两个缓存池：

- **热端**：存放高频访问数据（访问次数 ≥ 2），采用按访问频率排序的策略
- **冷端**：存放低频访问数据（访问次数 = 1），仍然采用 LRU 策略

核心逻辑：

1. 首次访问的数据 → 放入冷端头部；同时将缓存中所有已有数据的访问计数减 1（衰减）
2. 再次访问某数据时，访问计数 +1；若计数 ≥ 2 → 提升到热端
3. 冷端满了 → 淘汰冷端尾部数据（最久未访问的低频数据）
4. 热端满了 → 将热端尾部数据降级到冷端头部

这样设计的优势是：即使一次性大量涌入临时数据（如浏览公众号），也不会淘汰掉会话列表等高频场景的数据，从而提升整体缓存命中率。

工程实现建议：

```java
public class HotColdLruCache<K, V> {
    // 热端：存放高频数据，容量占比 40-50%
    private final LruCache<K, CacheEntry<V>> hotCache;
    // 冷端：存放低频数据，容量占比 50-60%
    private final LruCache<K, CacheEntry<V>> coldCache;
    // 总容量
    private final int maxSize;

    private static class CacheEntry<V> {
        V value;
        int accessCount;
    }

    public V get(K key) {
        CacheEntry<V> hot = hotCache.get(key);
        if (hot != null) {
            hot.accessCount++;
            return hot.value;
        }
        CacheEntry<V> cold = coldCache.get(key);
        if (cold != null) {
            cold.accessCount++;
            if (cold.accessCount >= 2) {
                // 提升到热端
                coldCache.remove(key);
                hotCache.put(key, cold);
            }
            return cold.value;
        }
        return null; // cache miss
    }

    public void put(K key, V value) {
        CacheEntry<V> entry = new CacheEntry<>();
        entry.value = value;
        entry.accessCount = 1;
        coldCache.put(key, entry); // 新数据先入冷端
    }
}
```

> ⚠️ 以上代码为示意实现，生产环境需要处理热端淘汰时降级到冷端、并发安全（`synchronized` 或 `ConcurrentHashMap`）、内存大小计算（`sizeOf()`）等细节。

### 适用性判断

冷热端分离并非在所有场景下都比标准 LruCache 更优：

- **适合**：缓存容量受限（低端设备）、访问模式有明显的冷热分化（部分数据高频、大部分数据低频）
- **不适合**：缓存容量充裕、访问模式均匀（大部分数据访问频率相近）、对实现复杂度敏感的轻量场景

[结构参考: Clippings/Android 性能优化 - 缓存优化：冷热端分离+重排序，提升缓存命中率 — 冷热端分离 LruCache 方案]

## 数据重排序与内存布局优化

### Cache Line 对齐与空间局部性

CPU 从主存加载数据到缓存时，以 cache line（64 字节）为单位。如果一组高频访问的字段分散在不同的 cache line 中，每次访问都需要独立的缓存加载；反之，如果它们被紧凑地排列在同一个 cache line 中，一次加载就能覆盖多个字段。

**Array of Structs (AoS) vs Struct of Arrays (SoA)** 是经典的内存布局选择：

```
// AoS: 每个对象包含所有字段 —— 常见的 OOP 写法
class Particle { float x, y, z; int color; }
Particle[] particles = new Particle[1000];

// SoA: 每个字段独立数组 —— 数据导向设计
float[] posX = new float[1000];
float[] posY = new float[1000];
float[] posZ = new float[1000];
int[] colors = new int[1000];
```

当只需要遍历位置数据（如碰撞检测）时，SoA 布局只需要顺序读取 `posX/posY/posZ` 数组，每个 cache line 可以容纳 16 个 float（64/4），cache 命中率极高。而 AoS 布局下，每个 Particle 对象占 16 字节（3 float + 1 int），一次 cache line 加载虽然能覆盖 4 个对象，但也包含了不需要的 `color` 字段。

在 Android 应用中，SoA 布局特别适合：

- 列表/RecyclerView 的大量 item 数据遍历
- 图像处理（像素数据的批量操作）
- 游戏中的实体组件系统（ECS）

### 字段排序优化

即使采用传统的 AoS 布局，也可以通过调整字段声明顺序来改善缓存效率：

- **将高频访问字段集中在前 64 字节**：确保它们落在同一个 cache line 中
- **将低频字段放到后面**：它们被访问时才触发额外的 cache line 加载
- **避免在热路径对象中嵌入大数组引用**：引用本身只占 4/8 字节，但实际数据分散在堆的其他位置

`@Contended` 注解可以解决伪共享（false sharing）问题——当多个线程各自修改同一 cache line 中的不同变量时，缓存一致性协议（如 MESI）会频繁失效该 cache line。`@Contended` 会自动在变量周围填充 padding，使其独占一个 cache line。但注意 Android 上 `@Contended` 需要 `android-27+` 且 ART 默认不启用该注解的 padding，需要通过 `-XX:-RestrictContended` 参数开启。

[已验证: AOSP android-17.0.0_r1, libcore/dalvik/src/main/java/dalvik/system/VMRuntime.java — VMRuntime 不直接暴露 @Contended 配置，需通过 system property 控制]

## 代码缓存优化：DEX 类文件重排序

### 原理：指令缓存命中率与类加载顺序

应用程序的 DEX 文件中，类的排列顺序并非按运行时访问顺序排列。在冷启动时，ART 需要按需加载类（class loading），如果类分散在 DEX 文件的不同位置，每加载一个新类就可能触发一次 I/O 和 cache miss。

如果能将启动路径上需要的类集中排列在 DEX 文件的前面区域，就可以：

1. 减少启动阶段的磁盘 I/O 次数（因为预读的 cache line 中包含了接下来需要的类）
2. 提高指令缓存命中率（因为热点类的代码段更紧凑）
3. 减少 page fault（因为减少了虚拟内存到物理内存的映射跳转）

### 工程方案一：Startup Profile + DEX Layout 优化

[已验证: 官方文档, developer.android.com/topic/performance/startupprofiles/dex-layout-optimizations]

Android 7+ 的 ART 编译器支持根据 profile 指导的 DEX 布局优化。R8 编译器在构建时根据 `startup-prof.txt` 重新排列 DEX 文件中类的顺序，将启动路径相关的类移到 `classes.dex` 的前面。

**与 Baseline Profile 的区别**：Baseline Profile 指导的是 ART 的 AOT 预编译（哪些方法需要提前编译），而 Startup Profile 指导的是 DEX 文件中类的物理排列顺序。两者互补但作用域不同。

详见 21.4 节（Baseline Profile 实战）和 21.12 节（Startup Profile 与 DEX Layout 启动优化）。

### 工程方案二：Redex 工具链

[结构参考: Clippings/Android 性能优化 - 缓存优化：冷热端分离+重排序，提升缓存命中率 — Redex 方案]

Facebook 开源的 [Redex](https://github.com/facebook/redex) 是一个 DEX 优化框架，其中 `InterDexPass` 模块实现了跨 DEX 文件的类重排优化。基本流程：

1. 在开发机上构建 APK
2. 通过 `adb shell am dumpheap` 获取应用启动后的堆内存快照
3. 使用 Redex 提供的 `dump_classes_from_hprof.py` 脚本从 hprof 中提取类加载顺序
4. 将顺序列表写入 Redex 配置文件的 `coldstart_classes` 字段
5. 执行 `redex input.apk -o output.apk` 重新排列 DEX
6. 重新签名后安装

**Redex vs R8 Startup Profile**：

| 维度 | R8 Startup Profile | Redex InterDexPass |
|------|-------------------|-------------------|
| 集成方式 | Gradle 插件，构建时自动执行 | 独立工具链，需手动或 CI 集成 |
| 优化范围 | DEX 内类排序 + 方法内联 | 跨 DEX 类排序 + 字节码优化 |
| 数据来源 | Macrobenchmark 自动采集 | 手动 dumpheap 采集 |
| 维护成本 | 低（官方维护） | 中（需维护配置和 CI 流水线） |
| Android 17 兼容 | 原生支持 | 需验证 DEX 解析兼容性 |

对于大多数应用，推荐优先使用官方的 R8 Startup Profile（详见 21.12 节）。只有在 DEX 布局优化有进一步需求（如多 DEX 应用、需要 Redex 的其他字节码优化能力）时，才考虑引入 Redex。

`[待验证]` Redex 对 Android 17 ART 的兼容性：Redex 最近一次 release 的 release notes 未明确声明 Android 17 支持，实际使用前需在目标设备上验证。

### 方案三：ART AOT 编译后的代码布局

ART 的 AOT 编译器（`dex2oat`）在编译时会将 DEX 中的方法编译为 native 代码并写入 OAT 文件。OAT 文件中代码段的布局也会影响指令缓存命中率。

[已验证: AOSP android-17.0.0_r1, art/dex2oat/dex2oat.cc]

Android 12+ 引入的 Profile-Guided Compilation 不仅选择性地编译热点方法，还会根据 profile 中的调用频率信息调整编译后的代码布局，将高频方法的 native code 集中在相邻的内存区域。这是 Baseline Profile 对启动性能的间接收益之一——不仅减少了 JIT 编译开销，还改善了代码段的空间局部性。

详见 21.4 节（Baseline Profile 实战）。

## 缓存命中率测量方法

### simpleperf PMU 采集

```bash
# 采集完整 cache 事件统计
simpleperf stat -e \
  L1-dcache-load-misses,L1-dcache-loads,\
  L1-icache-load-misses,L1-icache-loads,\
  cache-misses,cache-references \
  -p <pid> -- sleep 10
```

### Perfetto trace 分析

在 Perfetto 中可以通过 `linux/perf/perf_event` 数据源采集 PMU 事件，并在 trace 中关联到具体的函数调用栈和线程：

1. 在 trace config 中添加 `linux/perf` 数据源
2. 配置 `perf_event_config` 中的事件类型为 cache 相关 PMU 事件
3. 在 trace viewer 中，将 cache miss 事件与 CPU 调度切片对齐分析
4. 查看热点函数执行期间的 cache miss 密集程度

### ARM PMU 事件可用性

`[待验证]` 不同的 ARM SoC 对 PMU 事件的支持程度不同。ARM 架构定义了 PMUv3 通用事件集（如 `MEM_ACCESS`、`L1D_CACHE_REFILL`），但具体的实现 ID 和计数器数量由 SoC 厂商决定。建议使用 `simpleperf list` 查看当前设备支持的事件列表。

## 实战案例：列表滚动场景的数据结构优化

### 从 LinkedList 到 ArrayBacked

一个常见的缓存反模式是在性能敏感路径上使用 `LinkedList`：

- `LinkedList` 的每个 Node 都是独立堆分配，Node 之间通过指针连接
- 遍历时，每个 Node 可能位于完全不同的 cache line 甚至不同的内存页
- 对于 1000 个元素的遍历，`LinkedList` 可能触发近 1000 次 cache miss

改为 `ArrayList` 或裸数组后：

- 元素在内存中是连续排列的
- 一次 cache line 加载（64 字节）可以覆盖 8-16 个对象引用（取决于 32/64 位）
- 遍历 1000 个元素可能只需要 60-130 次 cache line 加载

在 Android 滚动列表场景中，数据源从 `LinkedList` 改为 `ArrayList` 的收益：

| 数据量 | LinkedList 遍历 | ArrayList 遍历 | 提升 |
|--------|----------------|----------------|------|
| 1,000 | ~3.2 ms | ~0.4 ms | 8x |
| 10,000 | ~35 ms | ~3.8 ms | 9x |

（上述数据为示意性量化，实际效果取决于设备、对象大小和访问模式。）

### 对象池的缓存友好设计

启动路径中创建大量临时对象会带来两个问题：GC 压力和 cache 争用。对象池（Object Pool）可以复用已有对象，减少分配开销。但对象池本身的缓存友好性也需要设计：

- **数组-backed 对象池**（`Object[] pool`）比链表-backed 对象池有更好的 cache locality
- **池大小应与 cache 容量匹配**：如果活跃对象总大小超过 L2 cache，池本身的收益会被 cache miss 抵消
- **避免池中对象持有大字段引用**：这些引用指向的数据可能分散在堆各处，拖累 cache 局部性

## 扩展

### Compose 数据结构的缓存友好性

Compose 的 `SlotTable` 是一个基于数组的树形数据结构，设计上已经考虑了缓存局部性——子节点在数组中倾向于相邻存储。从 Compose 1.0 到 1.10 的演进中，Google 持续优化了 SlotTable 的内存分配器（如 `PausableComposition` 减少重组范围），间接改善了 cache 命中率。

`[待补充]` Compose 1.10 在 Android 17 上的缓存性能基准数据。

### SoC 厂商差异化缓存配置

不同 SoC 厂商（高通、联发科、三星 Exynos、Google Tensor）的缓存层级参数差异显著，尤其在中端和入门级芯片上。例如：

- 高端芯片可能有 12 MB LLC + 6 MB SLC
- 中端芯片可能只有 4-6 MB LLC，无独立 SLC
- 入门级芯片可能 L2 只有 128 KB/核心

这意味着同一个应用在中端设备上的 cache miss 率可能比高端设备高 2-3 倍。对于跨设备性能优化，建议在目标最低配设备上测试 cache 指标。

`[待补充]` 主流 SoC（骁龙 8 Gen 4 / 天玑 9400 / Tensor G5）的详细缓存拓扑对比。

---

> 本节参考资料：
> - [结构参考: Clippings/Android 性能优化 - 缓存优化：冷热端分离+重排序，提升缓存命中率]
> - [结构参考: Clippings/Android 性能优化 - 原理：重新认识应用的速度优化]
> - [已验证: 官方文档, developer.android.com/topic/performance/startupprofiles/dex-layout-optimizations]
> - [已验证: AOSP android-17.0.0_r1, art/dex2oat/dex2oat.cc]
> - [引用: https://github.com/facebook/redex]
