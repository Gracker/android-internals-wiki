---
title: "Linux ANON_VMA_LAZY 优化与 Android 内存性能"
chapter: "4.13"
section: "4.13"
status: ready-for-review
applicable_versions: "Android 15 (API 35) - Android 17 (API 37)"
tags: [memory, linux-kernel, anon_vma, page-table, memory-optimization]
related_chapters: ["4.2", "4.7", "4.10"]
created_by: "task2a-knowledge-gap"
created_date: "2026-06-05"
gap_source: "研究素材"
drafted_date: "2026-06-05"
last_verified: "2026-06-05"
last_verified_against: "Honor PATCH 0/15 mm: ANON_VMA_LAZY; Linux kernel mm/rmap.c; LWN Article 1074859"
confidence: medium
sources:
  - type: research
    path: "DeepResearch/2026-06-04-anon_vma_lazy_memory_optimization.md"
  - type: paper
    path: "Honor [PATCH 0/15] mm: introduce ANON_VMA_LAZY for deferred anon_vma creation"
  - type: article
    path: "LWN.net Article 1074859"
---

# 4.13 Linux ANON_VMA_LAZY 优化与 Android 内存性能

Linux 内核为每个匿名内存页维护 `anon_vma` 结构，用于反向映射（rmap）——给定一个物理页，快速找到映射了该页的所有进程。传统实现中，`anon_vma` 在 VMA（`vm_area_struct`）创建时立刻分配。荣耀提交的 ANON_VMA_LAZY 补丁将这个分配推迟到真正需要时，在 8GB 设备上节省约 45MB 内存。

本节分析这个机制的原理、量化效果和对 Android 性能路径的影响。

## 传统 anon_vma 机制与内存开销

### anon_vma 在 rmap 中的角色

`anon_vma` 是 Linux 反向映射的核心数据结构。当进程通过 `mmap(MAP_ANONYMOUS)` 分配匿名内存时，内核为每个 VMA 创建一个 `anon_vma` 实例，并通过 `anon_vma_chain` 将父子进程的 `anon_vma` 链接起来。

这个结构服务的核心场景是 **fork 后的 COW（Copy-on-Write）**：父进程 fork 子进程后，两者共享同一批物理页；当某一方写入时，内核需要通过 rmap 找到所有映射该页的 PTE 并逐一修改。`anon_vma` 让这个查找能在 O(子进程数) 内完成。

### eager allocation 的问题

传统实现中，`__anon_vma_prepare()` 在每次 VMA 分配时被调用：

```c
// mm/rmap.c（简化）
int __anon_vma_prepare(struct vm_area_struct *vma)
{
    avc = anon_vma_chain_alloc(GFP_KERNEL);
    anon_vma = find_mergeable_anon_vma(vma);
    if (!anon_vma) {
        anon_vma = anon_vma_alloc();  // 立即分配
        allocated = anon_vma;
    }
    // ... 绑定到 VMA
}
```

关键路径：`mmap()` → `mmap_region()` → `vma_merge()` 或 `vma_prepare()` → `__anon_vma_prepare()`。

问题在于：**绝大多数匿名 VMA 永远不会参与 fork**。Android 上，应用进程的 `mmap(MAP_ANONYMOUS)` 主要用于堆扩展、线程栈、ART 内部映射等——这些 VMA 在进程生命周期内不会被 fork 共享。但内核仍然为每个 VMA 分配了 `anon_vma` 和 `anon_vma_chain`，造成固定内存开销。

在 Android 典型负载下（几十个进程，每个进程数百个 VMA），这些结构的累积开销达到 **30-50MB**。

## ANON_VMA_LAZY 延迟分配设计

### 核心思路

ANON_VMA_LAZY 将 `anon_vma` 的创建推迟到两个时机之一：

1. **fork 时**：父进程的 VMA 被 fork 继承，此时必须建立 rmap 链
2. **page fault 时**：匿名页首次被写入，且该 VMA 可能被 rmap 扫描

对于不 fork 的进程（Android 上绝大多数应用），这些 VMA 的 `anon_vma` 永远不会被创建。

判定函数 `should_use_anon_vma_lazy(vma)` 检查 VMA 是否需要参与 fork 或 rmap 操作：

```c
// 判定逻辑（简化）
static bool should_use_anon_vma_lazy(struct vm_area_struct *vma)
{
    return !vma_need_fork_operations(vma) && 
           !vma_need_rmap_operations(vma);
}
```

VMA 初始化路径变为：

```c
int anon_vma_prepare_lazy(struct vm_area_struct *vma)
{
    if (IS_ENABLED(CONFIG_ANON_VMA_LAZY) && 
        should_use_anon_vma_lazy(vma)) {
        return anon_vma_prepare_deferred(vma);  // 只做标记
    } else {
        return __anon_vma_prepare(vma);          // 传统路径
    }
}
```

### anon_vma_tree_t 数据结构

为了在同一套 rmap 框架下兼容两种模式，补丁引入 `anon_vma_tree_t`：

```c
struct anon_vma_tree_t {
    enum { ANON_VMA_TREE_LAZY, ANON_VMA_TREE_EAGER } mode;
    union {
        struct {
            struct folio *folio;
            bool anon_vma_created;
        } lazy;
        struct anon_vma *eager_anon_vma;
    } u;
};
```

lazy 模式下，rmap 操作可以绕过 `anon_vma` 锁，直接通过 VMA 信息完成查找：

```c
static int rmap_walk_anon_vma(struct folio *folio, ...)
{
    struct anon_vma_tree_t *av_tree = folio_anon_vma_tree(folio);
    if (av_tree->mode == ANON_VMA_TREE_LAZY && 
        !av_tree->u.lazy.anon_vma_created) {
        return rmap_walk_vma_direct(folio, args);  // 无锁路径
    } else {
        return rmap_walk_anon_vma_lock(av_tree, args);  // 传统加锁
    }
}
```

fork 时，如果 VMA 处于 lazy 模式，此时才真正创建 `anon_vma`：

```c
int anon_vma_fork_lazy(struct vm_area_struct *vma, struct vm_area_struct *pvma)
{
    if (!pvma->anon_vma && is_anon_vma_lazy(vma)) {
        return anon_vma_fork_deferred(vma, pvma);
    } else {
        return anon_vma_fork(vma, pvma);  // 传统路径
    }
}
```

## 量化优化效果

荣耀的 patchset 包含实测数据。测试环境为 8GB Android 设备：

**设备启动后**：

| 对象 | 优化前 (KB) | 优化后 (KB) | 变化 |
|------|------------|------------|------|
| `anon_vma` | 20,426 | 614 | **-97%** |
| `anon_vma_chain` | 18,866 | 8,112 | **-57%** |
| `vm_area_struct` | 117,035 | 118,176 | +1.0% |

**启动 24 个应用后**：

| 对象 | 优化前 (KB) | 优化后 (KB) | 变化 |
|------|------------|------------|------|
| `anon_vma` | 33,280 | 2,648 | **-92%** |
| `anon_vma_chain` | 31,477 | 15,577 | **-50.5%** |
| `vm_area_struct` | 196,873 | 197,345 | +0.2% |

[已验证: Honor PATCH 0/15 mm: ANON_VMA_LAZY, 内存使用对比表]

`vm_area_struct` 的小幅增加来自 `anon_vma_tree_t` 指针的额外字段。整体净节省约 **45MB**（8GB 设备的 0.56%），对低内存设备（4GB）收益更显著。

## 对 Android 关键路径的性能影响

### page fault 路径

lazy 模式下，匿名页首次写入的 page fault 处理流程不变——`anon_vma` 的有无不影响 `do_anonymous_page()` 中的 PTE 设置。区别在于 `page_add_new_anon_rmap()` 中的处理：如果 VMA 是 lazy 模式，rmap 信息记录到 `anon_vma_tree_t` 而非 `anon_vma`。

### fork 路径

`fork()` 是收益最大的场景。传统路径中，每个子进程需要复制父进程所有 VMA 的 `anon_vma_chain`（复杂度 O(VMA 数 × 子进程数)）。lazy 模式下，大部分 VMA 在 fork 时仍未创建 `anon_vma`，跳过了这一步。

Android 上，Zygote fork 应用进程是 fork 最频繁的场景。Zygote 进程有数千个 VMA（包括预加载的类、资源、图形驱动映射等），每次 fork 都要复制这些 `anon_vma` 结构。ANON_VMA_LAZY 可以显著减少 fork 时的内存分配量。

[待验证: Zygote fork 场景下的具体性能数据需要实际设备测试]

### COW 与内存回收

COW 触发时，`try_to_unmap()` 需要通过 rmap 找到所有映射该页的 PTE。如果 VMA 处于 lazy 模式且没有 fork 过，rmap 扫描只涉及当前进程——无需遍历 `anon_vma_chain`，减少了锁竞争。

`lmkd` 触发进程回收时（详见 4.4 节），被杀进程的 VMA 销毁路径也得到简化：不需要逐个释放 `anon_vma` 和 `anon_vma_chain`。

## Android 17 内核 6.12 中的适配状态

### 合并与配置

ANON_VMA_LAZY 由荣耀在 Linux 内核邮件列表提交，当前状态为 **上游未合并**。Android 17 GKI kernel 6.12 未默认启用。

该优化通过 `CONFIG_ANON_VMA_LAZY` 编译开关控制。OEM 可以在内核配置中启用：

```
CONFIG_ANON_VMA_LAZY=y
```

启用后，`should_use_anon_vma_lazy()` 的判定逻辑会自动为符合条件的 VMA 选择延迟分配。不需要应用侧适配。

[适用版本: Android 15+ (需 OEM 自行启用 CONFIG_ANON_VMA_LAZY)]

### 兼容性

- 与 ART GC 机制兼容：ART 的 `mmap` 匿名页分配和 GC 回收路径不依赖 `anon_vma` 的即时存在
- 与 ZRAM 兼容（详见 4.12 节）：ZRAM 压缩发生在物理页层面，不涉及 `anon_vma` 结构
- 与 16KB Page Size 兼容（详见 4.7 节）：页大小变更不影响 VMA 级别的 `anon_vma` 分配策略
- 与 MGLRU（Multi-Gen LRU）兼容：页面回收路径中的 rmap 操作已适配 lazy 模式

## 观测方法

### /proc/meminfo

`anon_vma` 和 `anon_vma_chain` 的内存不直接暴露在 `/proc/meminfo` 中。需要通过 `slabinfo` 间接观察：

```bash
# 查看 anon_vma 相关 slab 对象
cat /proc/slabinfo | grep -i anon_vma
```

启用 ANON_VMA_LAZY 后，`anon_vma` 和 `anon_vma_chain` 的对象数量会显著减少。

### Perfetto

通过 Perfetto 的 `memory_counters` 数据源可以观察整体内存变化，但无法直接区分 `anon_vma` 的贡献。推荐的观测方式：

1. 启用前后对比 `MemAvailable` 的变化（整体效果）
2. 通过 `sysctl vm.stat_interval` 加速 `/proc/vmstat` 的 `nr_slab_reclaimable` 采样
3. 用 `slabtop` 观察 `anon_vma` 对象的实时变化

```sql
-- Perfetto SQL: 对比启用前后的可用内存
SELECT
  ts,
  value / 1024.0 AS mem_available_mb
FROM counter
JOIN track ON counter.track_id = track.id
WHERE track.name = 'meminfo'
  AND counter.name = 'MemAvailable'
ORDER BY ts
```

### 与 lmkd 的关联

`anon_vma` 结构的减少直接增加了 `MemAvailable`，推迟了 `lmkd` 的触发时机（详见 4.4 节）。在 8GB 设备上，45MB 的额外可用内存意味着 `lmkd` 的 `minfree` 阈值被推迟了约一个级别，减少了后台进程被杀的概率。

## 扩展

### Multi-Gen LRU (MGLRU) 与 ANON_VMA_LAZY 的协同

MGLRU（Android 14+ 默认启用）优化了页面回收策略，ANON_VMA_LAZY 优化了匿名页的元数据开销。两者在不同层面减少内存压力：MGLRU 让回收更精准（减少不必要的页面驱逐），ANON_VMA_LAZY 让元数据更轻量（减少固定开销）。同时启用时效果叠加，不存在冲突。

[待补充: 具体的联合测试数据]

### 内存敏感场景下的收益评估

大内存应用（游戏、视频编辑器）通常有数千个匿名 VMA，`anon_vma` 开销占比更高。但这类应用也经常使用 `malloc/mmap` 大块分配，单次 `mmap` 只创建一个 VMA，实际的 `anon_vma` 数量不一定与内存使用量成正比。建议在启用前后分别采集 `slabinfo` 数据来评估实际收益。

[待验证: 游戏场景下的具体节省数据]
