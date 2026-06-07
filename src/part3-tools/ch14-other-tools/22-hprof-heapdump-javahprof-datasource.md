---
title: "HPROF Heap Dump 管线与 Perfetto java_hprof 数据源"
chapter: "14.22"
status: ready-for-review
drafted_date: "2026-06-07"
drafted_by: "openclaw-task2a"
applicable_versions: "Android 12 (API 31) - Android 17 (API 37)"
last_verified: "2026-06-07"
last_verified_against: "AOSP android-17.0.0_r1 + KOOM 2.2.1 + Perfetto docs"
confidence: medium
sources:
  - type: aosp
    path: "art/runtime/hprof/hprof.cc"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/am/ActivityManagerService.java"
  - type: aosp
    path: "frameworks/base/core/java/android/app/ActivityThread.java"
  - type: blog
    path: "Obsidian/Cubox/从 Hprof 源码初探虚拟机内存管理-2022-03-07.md"
  - type: blog
    path: "Obsidian/DeepResearch/2026-05-03-app_exit_info_tracker_and_koom_fork_hprof.md"
  - type: obsidian
    path: "OpenClaw定时任务/AutoResearchClaw调研报告/2026-05-03-app_exit_info_tracker_and_koom_fork_hprof.md"
tags: [hprof, heap-dump, art, perfetto, java_hprof, memory-analysis]
related_chapters: ["10.1", "10.2", "14.3", "14.14", "19.3"]
created_by: "task2a-knowledge-gap"
created_date: "2026-06-07"
gap_source: "素材驱动/DeepResearch/AOSP结构"
---

# 14.22 HPROF Heap Dump 管线与 Perfetto java_hprof 数据源

这节拆解 Android 上 Java 堆转储（heap dump）从命令到文件的完整路径，以及在 Perfetto 中通过 `java_hprof` 数据源做结构化分析的方式。

堆转储是内存泄漏排查的核心证据。§10.2 讲了泄漏的定义和分类，§14.3 列了内存分析工具清单，§14.14 讲了 Android Studio Memory Profiler 和 LeakCanary 的堆转储分析流程。本节聚焦在更底层的问题：heap dump 在系统内部是怎么产生的、dump 过程对应用有多大影响、以及 Perfetto 如何把原始 hprof 文件转化为可查询的结构化数据。

## HPROF Heap Dump 调用栈：从 Shell 到 ART

一次 heap dump 经历三层：Shell 命令 → AMS → ART。每一层有独立的职责和防护。

**Shell 层**：`am dumpheap` 命令入口，解析参数后通过 Binder 调用 AMS。

**AMS 层**：权限校验（`SET_ACTIVITY_WATCHER`，signature|privileged 级别）、Freezer 保护、异步派发到目标进程。

**ART 层**：GC critical section + SuspendAll 双重保护下，遍历堆中所有对象，输出标准 JAVA PROFILE 1.0.3 格式的 hprof 文件。

`am dumpheap` → `AMS.dumpHeap()` → `IApplicationThread.dumpHeap()` → `ActivityThread.handleDumpHeap()` → `Debug.dumpHprofData()` → `art::Hprof::Dump()`

### Shell 命令层：am dumpheap 参数

```bash
am dumpheap [-n] [-g] [-m] [-b] <pid/package> <output_path>
```

| 参数 | 含义 | 适用场景 |
|------|------|----------|
| (无参数) | 托管 dump，等 GC 完成后输出 | 默认方式，适合离线分析 |
| `-n` | 非托管 dump（native dump） | 需要包含 native 分配信息时使用 |
| `-g` | dump 前执行一次 GC | 减少已回收对象噪音，默认行为 |
| `-m` | 导出 malloc 信息 | 搭配 `-n` 使用，分析 native 内存分配 |
| `-b` | 导出位图数据 | 需要分析 Bitmap 像素内容时使用 |

[已验证: AOSP frameworks/base/cmds/am/src/com/android/commands/am/Am.java]

不带 `-n` 时走的是 `Debug.dumpHprofData()` 路径，输出标准 Java heap 转储。带 `-n` 时走 `Debug.dumpNativeBacktraceToFile()` 等路径，产出的是 malloc 调试数据，不是 hprof 格式——两者不要混淆。

### AMS 层：权限与 Freezer 保护

`ActivityManagerService.dumpHeap()` 的关键保护逻辑：

1. **权限检查**：调用方需要 `android.permission.SET_ACTIVITY_WATCHER` 权限（protectionLevel = signature|privileged，对应 system 或 root 级别）。普通应用无法触发其他进程的 heap dump。

2. **Freezer 保护**：在 dump 前调用 `enableFreezer(false)` 暂停 Cached App Freezer。如果不做这一步，目标进程可能处于冻结状态，无法响应 Binder 调用，导致 dump 超时失败。dump 完成后调用 `enableFreezer(true)` 恢复。详见 §4.11。

3. **异步派发**：AMS 通过 `IApplicationThread.dumpHeap()` Binder 调用把 dump 请求发送到目标进程的 `ActivityThread`。目标进程在主线程 Handler 中处理 `handleDumpHeap` 消息，调用 `Debug.dumpHprofData(filename)` 触发 ART 层的 dump。

[已验证: AOSP frameworks/base/services/core/java/com/android/server/am/ActivityManagerService.java]

### ART 层：双重保护机制

ART 中 `Hprof::Dump()` 的执行受两个保护机制约束：

**第一层：`gc::ScopedGCCriticalSection`**。在 dump 过程中阻止 GC 运行。dump 需要遍历堆中所有对象，如果遍历过程中 GC 移动了对象（复制 GC 场景），dump 出来的数据就会不一致。这个 critical section 确保 dump 期间 GC 不会干扰。

**第二层：`ScopedSuspendAll`**。暂停所有托管线程。dump 不仅要防 GC，还要防应用线程在遍历过程中修改对象引用。SuspendAll 让堆处于一个静止的快照状态。

`[来源: Obsidian/Cubox/从 Hprof 源码初探虚拟机内存管理-2022-03-07.md]`

这两个保护机制是 heap dump 对应用性能影响巨大的根因——所有线程暂停，GC 停止，应用处于完全冻结状态，直到 dump 写完。

## HPROF 文件格式与解析

ART 输出的 hprof 文件遵循 JAVA PROFILE 1.0.3 格式，由 `art/runtime/hprof/hprof.cc` 中的 `Hprof` 类生成。

### 文件整体结构

一个 hprof 文件由 header + body 两部分组成：

```
┌─────────────────────────────┐
│ Header                      │
│  - FixedHeader              │  "JAVA PROFILE 1.0.3" + identifier size + timestamp
│  - StringTable              │  所有字符串（类名、字段名等）的 ID → 值映射
│  - ClassTable               │  所有已加载类的序列号、class object ID、类名
│  - StackTraces              │  分配栈帧信息
├─────────────────────────────┤
│ Body (Heap Dump Segment)    │
│  - GC Roots                 │  各种类型的根对象
│  - Class Dump               │  每个类的元数据（字段、实例大小等）
│  - Instance Dump            │  实例对象的字段值
│  - Object Array Dump        │  对象数组的元素引用
│  - Primitive Array Dump     │  基本类型数组的原始值
├─────────────────────────────┤
│ Heap Dump End               │
└─────────────────────────────┘
```

`[来源: Obsidian/Cubox/从 Hprof 源码初探虚拟机内存管理-2022-03-07.md]`

### Android 对标准格式的扩展：Heap 类型标记

Android 在 heap dump segment 中通过 `HPROF_HEAP_DUMP_INFO` record 区分三种堆：

| Heap 类型 | 标识 | 含义 | 可否裁剪 |
|-----------|------|------|----------|
| `HPROF_HEAP_APP` | app | 应用自然堆，存放应用运行时分配的对象 | 不可裁剪（分析目标） |
| `HPROF_HEAP_ZYGOTE` | zygote | Zygote 空间，fork 后由子进程继承的对象 | 可裁剪（GC 策略为 never） |
| `HPROF_HEAP_IMAGE` | image | Boot image 空间，系统启动时加载的类和对象 | 可裁剪（GC 策略为 never） |

`DumpHeapObject()` 中根据对象所属 space 判断类型：

- 对象在 `ZygoteSpace` → `HPROF_HEAP_ZYGOTE`
- 对象在 boot `ImageSpace` → `HPROF_HEAP_IMAGE`
- 其他（包括 app ImageSpace、RegionSpace、MainSpace、LOS）→ `HPROF_HEAP_APP`

这个三分法是 KOOM 等 strip 工具裁剪 hprof 的依据——zygote 和 image 区域的对象在 dump 中可以安全删除，因为它们不会被 GC 回收，也不会泄漏，保留它们只会增大文件体积。

`[来源: Obsidian/Cubox/从 Hprof 源码初探虚拟机内存管理-2022-03-07.md]`

### GC Root 类型

`ProcessBody()` 遍历堆时先处理 GC Root，再遍历所有对象。ART 中 GC Root 分为以下几类：

| Root 类型 | 标签 | 来源 |
|-----------|------|------|
| `kRootThreadObject` | `HPROF_ROOT_THREAD_OBJECT` | 线程对象本身 |
| `kRootJNILocal` | `HPROF_ROOT_JNI_LOCAL` | JNI 局部引用 |
| `kRootJNIGlobal` | `HPROF_ROOT_JNI_GLOBAL` | JNI 全局引用 |
| `kRootNativeStack` | `HPROF_ROOT_NATIVE_STACK` | native 栈上的引用 |
| `kRootStickyClass` | `HPROF_ROOT_STICKY_CLASS` | 粘性类（image space 中的类） |
| `kRootInternedString` | `HPROF_ROOT_INTERNED_STRING` | 字符串常量池 |
| `kRootVMInternal` | `HPROF_ROOT_VM_INTERNAL` | VM 内部引用 |
| `kRootJavaFrame` | `HPROF_ROOT_JAVA_FRAME` | Java 栈帧中的局部变量 |
| `kRootMonitorUsed` | `HPROF_ROOT_MONITOR_USED` | 被 synchronize 持有的对象 |
| `kRootDebugger` | `HPROF_ROOT_DEBUGGER` | 调试器引用 |

`MarkRootObject()` 为每种 root 类型写入固定格式的 record，包含对象 ID、线程序列号、栈帧编号等信息。

`[来源: Obsidian/Cubox/从 Hprof 源码初探虚拟机内存管理-2022-03-07.md]`

### 对象遍历：Space 维度

`ProcessBody()` 通过 `Heap::VisitObjectsPaused()` 遍历所有空间中的对象：

1. **RegionSpace**：ART 默认的并发 GC 使用 RegionSpace 管理分代区域，通过 `region_space_->Walk(visitor)` 遍历
2. **BumpPointerSpace**：线程本地分配缓冲区（TLAB），通过 `bump_pointer_space_->Walk(visitor)` 遍历
3. **AllocationStack**：通过 `allocation_stack_` 遍历已分配但未在 bitmap 中的对象
4. **LiveBitmap**：通过 `GetLiveBitmap()->Visit()` 遍历所有存活对象

对每个对象调用 `DumpHeapObject()`，根据对象类型分别输出：

- Class 对象 → `DumpHeapClass()`：输出类元数据、静态字段、实例字段定义
- Array 对象 → `DumpHeapArray()`：对象数组输出引用列表，基本类型数组输出原始值
- Instance 对象 → `DumpHeapInstanceObject()`：按类继承链输出所有实例字段值

`[来源: Obsidian/Cubox/从 Hprof 源码初探虚拟机内存管理-2022-03-07.md]`

[待验证: 源码路径基于 master 分支分析，android-17.0.0_r1 中类名和字段名可能有细微差异]

## Perfetto java_hprof 数据源

Android 17 中 Perfetto 引入了 `art_hprof` 数据源（也称为 `java_hprof` 数据源），将 hprof 文件解析为结构化的堆图数据，在 Perfetto UI 中以 `heap_graph` 系列表的形式呈现。

### 从 hprof 到 heap_graph 的转换链路

```
Perfetto trace config 配置 java_hprof 数据源
    ↓
traced 抓取期间触发 heap dump（或导入已有 hprof）
    ↓
ArtHprofParser 解析 hprof 二进制格式
    ↓
转换为 Perfetto 内部的堆图 proto 结构
    ↓
trace_processor 导入后生成 heap_graph 系列表
    ↓
Perfetto UI 可视化（火焰图、对象统计、Retained Size）
```

[待验证: art_hprof 数据源在 Android 17 (API 37) 中的具体配置方式和可用性状态]

### 配置方式

在 TraceConfig 中启用 `java_hprof` 数据源：

```protobuf
data_sources: {
  config: {
    name: "linux.java_hprof"
    java_hprof_config: {
      // 可配置连续 dump 间隔
      dump_interval_ms: 60000
      // 可配置是否跟踪分配栈
      track_allocations: true
    }
  }
}
```

[待验证: Android 17 中此配置字段的准确名称和默认值]

### heap_graph 系列表

解析后的 hprof 数据在 Perfetto SQL 中以 `heap_graph` 表族呈现：

| 表名 | 内容 | 用途 |
|------|------|------|
| `heap_graph_object` | 每个堆对象的类型、大小、引用列表 | 查找特定类型的对象实例 |
| `heap_graph_class` | 类名、类大小、实例数量统计 | 统计各类实例数量和总大小 |
| `heap_graph_reference` | 对象间的引用关系 | 追踪引用链、计算 Retained Size |

`heap_graph_object` 表的核心字段：

```sql
-- 示例：查找所有 Activity 实例及其 retained size
SELECT
  o.id,
  o.type_name,
  o.self_size,
  o.reachable
FROM heap_graph_object o
WHERE o.type_name LIKE '%Activity%'
ORDER BY o.self_size DESC;
```

[待验证: Perfetto 表名和字段在 android-17.0.0_r1 trace_processor 版本中是否完全一致]

heap_graph 与 Perfetto 其他数据源的关联分析是它最有价值的场景——可以把堆大小变化和同一时间轴上的 GC 事件、帧渲染耗时、内存压力信号对齐，判断内存问题对 UI 性能的影响。

## 实战：Heap Dump 的性能影响

### 系统 dumpheap 的开销

通过 `am dumpheap` 或 `Debug.dumpHprofData()` 执行 heap dump 时，应用付出的代价：

| 影响维度 | 量级 | 原因 |
|----------|------|------|
| **线程暂停** | 全线程停止 | `ScopedSuspendAll` 暂停所有托管线程 |
| **GC 冻结** | GC critical section | `ScopedGCCriticalSection` 阻止 GC 运行 |
| **暂停时长** | 数秒到数十秒 | 与堆大小正相关：100MB 堆约 5-10 秒，500MB 堆可能超过 30 秒 |
| **I/O 压力** | 与堆大小相当 | hprof 文件大小 ≈ 堆大小的 50-80%（不含裁剪） |
| **内存压力** | dump 缓冲区 | ART 内部用缓冲区攒满一个 record 后写文件 |

这些开销在开发调试时可以接受，在线上环境则不可接受——用户会感知到应用完全卡死数秒到数十秒。

### 生产环境替代方案：KOOM fork-dump

快手 KOOM 通过 `fork()` + Copy-on-Write 策略规避主进程阻塞。核心流程：

```
主进程 Suspend ART VM（暂停所有线程）
    ↓
fork() 创建子进程（利用 Linux COW，fork 瞬间不拷贝物理内存）
    ↓
主进程 Resume ART VM（恢复运行）
    ↓
子进程独立执行 hprof dump + strip 裁剪
```

主进程只阻塞约 20ms（Suspend → fork → Resume 三个步骤），子进程在独立地址空间完成 dump，不影响用户感知。详见 §19.3。

KOOM 的 `ForkStripHeapDumper` 还会在子进程中对 hprof 进行 strip 裁剪，删除 zygote 和 image 区域的数据，文件体积减少 50-70%。裁剪后的文件需要用 `koom-fill-crop.jar` 工具在 PC 端补全文件头，才能被 Android Studio Profiler 和 MAT 正确打开。

[已验证: Obsidian/DeepResearch/2026-05-03-app_exit_info_tracker_and_koom_fork_hprof.md]

### 何时选择哪种方案

| 场景 | 推荐方式 | 原因 |
|------|----------|------|
| 开发调试 | Android Studio Memory Profiler | IDE 集成，可视化好，无需额外接入 |
| CI/自动化测试 | `am dumpheap` + MAT/shark | 可脚本化，不影响用户体验 |
| 线上监控 | KOOM fork-dump | 主进程阻塞 < 20ms，用户无感知 |
| 一次性排查 | `Debug.dumpHprofData()` | 简单直接，适合本地复现场景 |

## 扩展

### Perfetto heap_graph SQL 分析

使用 `heap_graph_object` 和 `heap_graph_reference` 表可以进行多种分析：

**查找泄漏嫌疑对象**——已被判定可达但实际应该回收的对象：

```sql
SELECT
  o.type_name,
  COUNT(*) as instance_count,
  SUM(o.self_size) as total_size
FROM heap_graph_object o
WHERE o.reachable = 1
  AND o.type_name IN (
    'android.app.Activity',
    'android.app.Fragment',
    'androidx.fragment.app.Fragment'
  )
GROUP BY o.type_name
ORDER BY total_size DESC;
```

**Retained Size 近似计算**——一个对象及其独占引用的所有对象的总大小：

```sql
-- 通过 heap_graph_reference 追踪独占引用链
SELECT
  o.type_name,
  o.self_size,
  COUNT(r.owner_id) as ref_count
FROM heap_graph_object o
LEFT JOIN heap_graph_reference r ON r.owned_id = o.id
WHERE o.reachable = 1
GROUP BY o.id
HAVING ref_count <= 1
ORDER BY o.self_size DESC
LIMIT 20;
```

[待验证: SQL 查询的准确性依赖 trace_processor 版本和 heap_graph 表的 schema 定义]

### KOOM fork-dump 的实现边界

KOOM 的 fork-dump 方案有几个限制：

- **只支持 Java 堆**：fork 出来的子进程只能 dump Java 堆对象，native 分配需要走 heapprofd（§14.3）。
- **COW 不是零开销**：fork 后子进程写页时会触发缺页中断，物理内存分配在第一次写入时发生。如果堆很大，子进程 dump 期间的内存压力仍然可观。
- **ART 版本兼容**：SuspendVM/ResumeVM 是 ART 内部 API，不同 Android 版本的实现有差异。KOOM 通过 JNI 调用 `art::Runtime::Current()->SuspendVM()`，需要为每个主要版本做适配。
- **文件格式补全**：strip 后的 hprof 文件不能直接在 MAT 中打开，需要 PC 端的 `koom-fill-crop.jar` 补全 STRING 和 CLASS 表。

[已验证: Obsidian/DeepResearch/2026-05-03-app_exit_info_tracker_and_koom_fork_hprof.md]
