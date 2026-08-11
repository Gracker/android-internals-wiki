---

title: HPROF Heap Dump 管线与 Perfetto java_hprof 数据源
chapter: 14.6
section: 14.6
status: finalized
pipeline_stage: ready-to-publish
task6_state: reviewed
task6_result: pass-light-edit
last_task6_at: "2026-07-17T12:14:00+08:00"
last_task6_audit: "2026-06-30"
last_task6_audit_at: "2026-06-30T06:05:00+08:00"
last_task6_audit_reason: "idle audit: L1零命中, frontmatter 修复 stray dash + CJK-Latin 空格, outline N/A"
task9_state: reviewed
task9_result: pass-tech-review
task2b_state: fixed
task2b_result: fixed
last_task2b_at: 2026-07-17T14:52:59+08:00
last_task2b_lite_at: "2026-07-17"
last_task9_at: "2026-07-17T15:20:00+08:00"
last_task9_result: "pass-tech-review"
reviewed_by: openclaw-task6
reviewed_date: 2026-07-17
drafted_date: 2026-06-07
drafted_by: openclaw-task2a
applicable_versions: Android 12 (API 31) - Android 17 (API 37)
last_verified: 2026-07-30
last_verified_against: AOSP android-17.0.0_r1 + KOOM 2.2.1 + Perfetto docs
confidence: high
sources:
  - type: aosp
    path: "art/runtime/hprof/hprof.cc"
  - type: aosp
    path: "art/perfetto_hprof/perfetto_hprof.cc"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/am/ActivityManagerService.java"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/am/ActivityManagerShellCommand.java"
  - type: aosp
    path: "frameworks/base/core/java/android/app/ActivityThread.java"
  - type: aosp
    path: "external/perfetto/src/profiling/memory/java_hprof_producer.cc"
  - type: aosp
    path: "external/perfetto/src/profiling/common/producer_support.cc"
  - type: aosp
    path: "external/perfetto/src/trace_processor/tables/profiler_tables.py"
  - type: blog
    path: "Obsidian/Cubox/从 Hprof 源码初探虚拟机内存管理-2022-03-07.md"
  - type: blog
    path: "Obsidian/DeepResearch/2026-05-03-app_exit_info_tracker_and_koom_fork_hprof.md"
  - type: obsidian
    path: "OpenClaw定时任务/AutoResearchClaw调研报告/2026-05-03-app_exit_info_tracker_and_koom_fork_hprof.md"
tags: [hprof, heap-dump, art, perfetto, java_hprof, memory-analysis]
related_chapters: ["10.1", "10.2", "14.5", "19.3"]
created_by: task2a-knowledge-gap
created_date: 2026-06-07
gap_source: 素材驱动/DeepResearch/AOSP

last_task9_audit: '2026-07-17T11:30:09+08:00'
last_task9_audit_log: 'logs/deep-review/2026-07-17-11-audit-hprof.md'
last_task9_autofix_at: "2026-07-17"
last_task2b_by: task2b-main
deepseek_cn_review_state: done
last_deepseek_cn_review_at: 2026-07-17
android17_review_notes: "区分完整 ART HPROF 与 Perfetto 引用图；校正 dumpheap 参数、AMS freezer、ART 双遍历、java_hprof fork 管线、权限与 SQL 表结构"
---

# 14.6 HPROF Heap Dump 管线与 Perfetto java_hprof 数据源

Android 上的“Java 堆转储”至少包含两类产物：

| 产物 | 采集入口 | 主要数据 | 适合回答的问题 |
| --- | --- | --- | --- |
| 完整 ART HPROF | `am dumpheap`、`Debug.dumpHprofData()`、Android Studio | 对象、类、GC Root、引用、实例字段、基本类型数组等 | 某个字段保存了什么、对象沿哪条引用链存活、离线工具能否读取完整对象数据 |
| Perfetto ART Heap Graph | `android.java_hprof` | 类、对象大小、GC Root、引用图、可达性、部分 native size | 哪类对象增长、谁支配了大块内存、堆变化与 GC、内存压力或卡顿是否同一时段出现 |

这两条管线都从 ART 的托管堆取快照，产物和暂停边界却不相同。`android.java_hprof` 这个名字容易造成误会：Perfetto 在目标进程中 fork 后直接写 `HeapGraph` protobuf packet，不会先落一份 HPROF 再解析。

§10.2 讨论泄漏模型，§14.5 讨论 Android Studio Memory Profiler 与 LeakCanary。这里聚焦采集管线、数据边界和 Android 17 上可核对的源码行为。

## 完整 HPROF：从 Shell 到 ART

### `am dumpheap` 参数以 Android 17 解析器为准

`ActivityManagerShellCommand.runDumpHeap()` 在 `android-17.0.0_r1` 中识别这些参数：

| 参数 | Android 17 行为 |
| --- | --- |
| `--user <ID|current>` | 指定查找进程的用户 |
| `-g` | 转储前在目标进程执行两次 `System.gc()`，中间运行 finalization |
| `-b <png|jpg|webp>` | 托管堆转储时包含 Bitmap 像素数据，并指定编码格式；格式参数不可省略 |
| `-n` | 调用 `Debug.dumpNativeHeap()`，输出 native heap dump，不是 HPROF |
| `-m` | 调用 `Debug.dumpNativeMallocInfo()`，输出 malloc 信息，不是 HPROF；Android 17 的帮助文本没有列出这个解析器仍接受的选项 |

没有 `-g` 时，系统不会主动在转储前运行 GC。输出文件参数在解析器中可省略；省略后使用 `/data/local/tmp/heapdump-<时间>.prof`。自动化脚本宜显式给出设备侧路径，避免后续猜测文件名。

下面的命令用于抓取一次已回收明显垃圾、且包含 PNG 编码 Bitmap 内容的完整 HPROF：

```bash
adb shell am dumpheap -g -b png \
  com.example.app /data/local/tmp/com.example.app.hprof
adb pull /data/local/tmp/com.example.app.hprof
```

`-b` 会把潜在的用户图像带进文件。文件应按敏感数据处理，分析结束后从设备和共享目录清理。

### 调用链中每一层做什么

Android 17 的托管堆路径可以按下面的顺序阅读：

| 层 | 入口 | 职责 |
| --- | --- | --- |
| Shell | `ActivityManagerShellCommand.runDumpHeap()` | 解析参数、创建输出文件描述符、等待异步回调 |
| system_server | `ActivityManagerService.dumpHeap()` | 检查权限与目标进程、临时关闭 Cached App Freezer、派发 Binder 调用 |
| 应用进程 | `ApplicationThread.dumpHeap()` | 复制文件描述符，把 `H.DUMP_HEAP` 消息送给 `ActivityThread` |
| 应用进程 | `ActivityThread.handleDumpHeap()` | 按选项运行 GC，并选择 managed、native heap 或 malloc-info 路径 |
| ART | `Debug.dumpHprofData()` → `art::hprof::DumpHeap()` | 停止托管线程，遍历堆并写 HPROF |

这个拆分能解释两个常见现象：Shell 命令会等待目标进程异步完成；遍历堆和写文件的工作发生在目标应用进程，不在 `system_server`。

### 权限检查和 Freezer 的含义

`ActivityManagerService.dumpHeap()` 要求调用方持有 `android.permission.SET_ACTIVITY_WATCHER`。Android 17 中该权限的保护级别是 `signature`。AMS 还会调用 `enforceDebuggable()` 检查目标进程，因此不能把 `am dumpheap` 当成面向任意发布应用的通用接口。

应用在自己的进程内调用公开的 `Debug.dumpHprofData()` 时，不经过 AMS 这组跨进程检查。它仍会承受 ART 转储的停顿、I/O 和敏感数据风险。

AMS 在请求前调用 `mCachedAppOptimizer.enableFreezer(false)`，完成回调中再调用 `enableFreezer(true)`。这段代码临时关闭的是系统范围的 Cached App Freezer，目的在于避免目标进程被冻结后无法处理 Binder 请求。它没有“暂停目标进程”；目标进程的托管线程暂停发生在更下层的 ART。

### `-g` 在哪里生效

`ActivityThread.handleDumpHeap()` 只在 `runGc` 为 `true` 时执行以下序列：

```java
System.gc();
System.runFinalization();
System.gc();
```

该序列发生在调用 `Debug.dumpHprofData()` 之前。它能减少等待回收对象对快照的干扰，也会增加采集前的停顿；它不能证明业务层已经不存在泄漏。

随后，`handleDumpHeap()` 根据模式选择一个入口：

- managed：`Debug.dumpHprofData(path, fd, bitmapFormat)`；
- native heap：`Debug.dumpNativeHeap(fd)`；
- malloc info：`Debug.dumpNativeMallocInfo(fd)`。

因此，`-n` 和 `-m` 的结果不能交给 HPROF 分析器。

## ART 如何生成 HPROF

### 停顿覆盖完整的两遍遍历

`art/runtime/hprof/hprof.cc` 的 `DumpHeap()` 先进入 `gc::ScopedGCCriticalSection`，再创建 `ScopedSuspendAll(..., true /* long suspend */)`。前者防止 GC 与对象访问冲突，后者停止托管线程，使对象和引用在遍历期间保持一致。

`Hprof::Dump()` 在这个暂停范围内执行两遍：

1. 用计数输出器运行 `ProcessHeap(false)`，计算整体大小和最大 record 大小；
2. 清空访问状态，再由 `DumpToFile()` 或 DDMS 路径写正式数据。

暂停覆盖计数遍历、正式遍历和文件输出，代价不止一次“扫对象”。耗时受对象数、字段与数组数据量、存储速度、Bitmap 内容和设备状态影响。没有一组固定的“每 100 MB 几秒”数字能跨设备成立，采集方案应在目标机型和目标堆规模上测量。

### Android 17 HPROF 的结构

ART 写出的头部 magic 是 `JAVA PROFILE 1.0.3`，对象 ID 宽度为 4 字节。文件包含字符串与类定义、GC Root、类转储、实例转储、对象数组和基本类型数组等 record。

可以用下面的结构理解文件，但解析器必须按 record 的长度和 tag 读取，不能依赖示意图推算偏移：

```text
Header
├── magic / identifier size / timestamp
├── STRING 与 LOAD_CLASS records
├── HEAP_DUMP_SEGMENT
│   ├── GC Root records
│   ├── CLASS_DUMP
│   ├── INSTANCE_DUMP
│   ├── OBJECT_ARRAY_DUMP
│   └── PRIMITIVE_ARRAY_DUMP
└── HEAP_DUMP_END
```

ART 的实现会在生成堆数据时收集字符串和类信息，再按分析工具需要的顺序组织输出。自行编写裁剪器时，还要处理 Android 扩展 tag、分段边界、对象 ID 和交叉引用。

### app、zygote 与 image 只是空间归类

Android 的 `HPROF_HEAP_DUMP_INFO` record 标识对象所在的堆空间：

| 标识 | Android 17 归类规则 |
| --- | --- |
| `HPROF_HEAP_APP` | 常规应用对象，以及 app image 中的对象 |
| `HPROF_HEAP_ZYGOTE` | Zygote space 与 Zygote large-object space 中的对象 |
| `HPROF_HEAP_IMAGE` | boot image space 中的对象 |

zygote 或 boot image 对象通常不是应用泄漏的分配主体，但它们可能出现在 GC Root 路径中，相关类和字符串 record 也可能被其他对象引用。不能把“很少是泄漏主体”改写成“整段可安全删除”。KOOM 一类工具会配套裁剪和补全器维护文件引用关系；直接删二进制区段很容易得到无法解析或引用断裂的文件。

### GC Root 和对象遍历

`Hprof::VisitRoot()` 把 ART 的 root 类型映射为标准或 Android 扩展 HPROF tag，例如 JNI global/local、Java frame、native stack、sticky class、thread object、interned string、debugger、VM internal 和 JNI monitor。

`ProcessBody()` 访问运行时 root、image root，再通过 `Heap::VisitObjectsPaused()` 访问对象。对象按类型写成 class、instance、object array 或 primitive array record。泄漏分析器在这份图上计算从 GC Root 到对象的路径、可达性和 dominator tree；“被某个字段引用一次”与“该对象支配一片子图”不是同一个概念。

## Perfetto `android.java_hprof`：直接采集引用图

### 这条链路从 Android 11 已经存在

`android.java_hprof` 支持 Android 11 及以上版本。Android 17 的管线由 heapprofd 进程中的 `JavaHprofProducer` 和目标进程中的 ART Perfetto 插件协作完成：

1. traced 把 `JavaHprofConfig` 交给 `JavaHprofProducer`；
2. producer 根据 `pid` 或 `process_cmdline` 找到目标，读取有效 UID 并调用 `CanProfile()`；
3. producer 用 `sigqueue()` 发送 `__SIGRTMIN + 6`，signal value 携带 tracing session ID；
4. ART 插件的信号处理器只向 pipe 写通知，附着到 ART 的 listener thread 再调用 `DumpPerfetto()`；
5. ART 在受保护的暂停区间锁定运行时结构并 fork，父进程尽快恢复托管线程；
6. 子进程继续 daemonize，遍历 fork 时刻的堆副本，直接向 Perfetto trace writer 写 `HeapGraph` packet；
7. Trace Processor 导入 protobuf packet，生成 `heap_graph_*` SQL 表。

Java producer 只负责找进程、做授权和发信号。它不会接收 HPROF 文件描述符，也没有 `ArtHprofParser` 把临时 HPROF 转成 protobuf 的步骤。

fork 把父进程的暂停范围缩到准备快照和创建子进程的阶段，图遍历由子进程继续完成。它仍有 fork、页表、Copy-on-Write、子进程内存与序列化开销，不应描述成零成本采集。

### TraceConfig 示例

下面的 textproto 配置用于进程启动后立即抓一份图，并在延迟 30 秒后开始每 60 秒追加一份：

```protobuf
buffers {
  size_kb: 65536
  fill_policy: RING_BUFFER
}

data_sources {
  config {
    name: "android.java_hprof"
    java_hprof_config {
      process_cmdline: "com.example.app"
      min_anonymous_memory_kb: 10240
      dump_smaps: true
      continuous_dump_config {
        dump_phase_ms: 30000
        dump_interval_ms: 60000
        scan_pids_only_on_start: false
      }
    }
  }
}

duration_ms: 180000
```

`StartDataSource()` 总会立即调用一次 `SendSignal()`。`dump_interval_ms` 非零时，`dump_phase_ms` 是第一次追加采集前的延迟；它不延迟开头那份快照。后续每隔 `dump_interval_ms` 再采一份。

### 配置字段的边界

| 字段 | Android 17 语义 |
| --- | --- |
| `process_cmdline` | repeated；按 `/proc/<pid>/cmdline` 匹配。Android 13 起允许一个 `*` 通配符 |
| `pid` | repeated；直接指定 PID，适合局部调试或外部触发场景 |
| `target_installed_by` | repeated；可限制为一个或多个 installer，特殊值有 `@system`、`@product`、`@null` |
| `continuous_dump_config` | 设置追加采集的 phase、interval 与是否每轮重扫 PID |
| `min_anonymous_memory_kb` | 跳过 anon RSS 与 swap 之和低于阈值的进程 |
| `dump_smaps` | 附带经过路径过滤的 `/proc/self/smaps` 信息 |
| `ignored_types` | repeated；从图中排除指定类型，可能改变引用图与 retained 结果 |

Android 12 及更早版本默认只在数据源启动时扫描 PID；Android 13 及以上默认每轮重扫。配置文件显式写出 `scan_pids_only_on_start`，能避免同一配置在跨版本设备上表现不同。

### `CanProfile()` 如何决定能否采集

Android 17 的 `producer_support.cc` 按 build type、UID、trace session initiator 和 `packages.list` 联合判断：

- 非 `user` 构建直接允许；
- `user` 构建上的普通应用会映射到 `packages.list`；
- 普通 Shell 发起的 session 要求目标为 `profileable_from_shell` 或 `debuggable`；
- trusted-system session 要求目标为 `profileable` 或 `debuggable`；
- 平台 UID 只允许 trusted-system initiator；
- isolated UID 采用更保守的规则；
- 配置了 `target_installed_by` 时，installer 还要命中允许列表。

这组检查与 `am dumpheap` 的 `SET_ACTIVITY_WATCHER`、`enforceDebuggable()` 不是同一套权限模型。排查“抓不到图”时，应同时确认 trace 发起者、应用 manifest 的 profileable/debuggable 属性、目标进程 UID 和 installer 条件。

## Perfetto 引用图和完整 HPROF 差在哪

Perfetto 文档把 `android.java_hprof` 的结果称为 ART Heap Dump。它是轻量引用图，记录类型、对象、大小、root 和对象间引用，不保存实例中的基本类型字段值。完整 HPROF 可以携带这些值，还可能包含字符串、基本类型数组和 Bitmap 内容，所以文件更敏感。

Android 17 的 Trace Processor 也能导入完整 ART HPROF。导入 HPROF 后会填充 HPROF 专用的数据表；这项能力不代表实时 `android.java_hprof` 采集会生成 HPROF。

| 能力 | 实时 `android.java_hprof` | 导入完整 ART HPROF |
| --- | --- | --- |
| 类、对象、root、引用关系 | 有 | 有 |
| `self_size`、`native_size`、可达性 | 有 | 有 |
| 实例基本类型字段 | 无 | 有 |
| 解码后的 `String`、基本类型数组数据 | 无 | 有 |
| 与 trace 时间轴直接对齐 | 有 | 取决于导入方式 |
| 父进程完整序列化期间保持暂停 | 否，fork 后由子进程遍历 | 是，传统 HPROF 在父进程内完成两遍 |

## Trace Processor 表与正确的 SQL 用法

### 表结构

Android 17 的 `profiler_tables.py` 定义了这些公开视图的底层表：

| 表 | 关键列 | 说明 |
| --- | --- | --- |
| `heap_graph_class` | `id`、`name`、`deobfuscated_name`、`location`、`superclass_id`、`classloader_id`、`kind` | 类定义 |
| `heap_graph_object` | `id`、`upid`、`graph_sample_ts`、`self_size`、`native_size`、`reference_set_id`、`reachable`、`heap_type`、`type_id`、`root_type` | 对象 |
| `heap_graph_reference` | `reference_set_id`、`owner_id`、`owned_id`、字段名与字段类型 | 对象引用 |
| `heap_graph_object_data` | `field_set_id`、字符串值、基本类型数组元数据 | 仅完整 HPROF 会填充 |
| `heap_graph_primitive` | `field_set_id`、字段名、类型和值列 | HPROF 实例的基本类型字段 |

生成表都带隐式 `id` 主键，所以 `heap_graph_object.id` 可以与 `owner_id`、`owned_id` 关联。`profiler_tables.py` 的 `columns` 列表没有手写 `id`，不等于 SQL 表没有 `id`。

Android 17 没有一张名为 `heap_graph` 的采样元信息表。同一 `(upid, graph_sample_ts)` 的全部 `heap_graph_object` 行构成一次 dump。包含多次采集的 trace，查询时要选定这两个维度。

### 统计最新快照中各类的 shallow size

下面的查询为每个进程选取时间戳最新的一份图，再按类统计对象数与 `self_size`：

```sql
WITH latest_dump AS (
  SELECT
    upid,
    MAX(graph_sample_ts) AS graph_sample_ts
  FROM heap_graph_object
  GROUP BY upid
)
SELECT
  o.upid,
  COALESCE(c.deobfuscated_name, c.name) AS class_name,
  COUNT(*) AS object_count,
  SUM(o.self_size) AS shallow_size_bytes
FROM heap_graph_object AS o
JOIN latest_dump AS d
  USING (upid, graph_sample_ts)
JOIN heap_graph_class AS c
  ON o.type_id = c.id
WHERE o.reachable = 1
GROUP BY o.upid, class_name
ORDER BY shallow_size_bytes DESC;
```

这个结果回答“类实例自身占了多少 Java 堆”。它没有计算对象独占支配的子图，不是 retained size。

### 用标准库计算 class-level dominated size

retained size 要基于 dominator tree。Perfetto 已提供实现，下面的查询直接使用 Android heap graph 聚合模块：

```sql
INCLUDE PERFETTO MODULE android.memory.heap_graph.heap_graph_class_aggregation;

SELECT
  upid,
  graph_sample_ts,
  type_name,
  obj_count,
  size_bytes,
  dominated_obj_count,
  dominated_size_bytes
FROM android_heap_graph_class_aggregation
WHERE reachable_obj_count > 0
ORDER BY dominated_size_bytes DESC
LIMIT 50;
```

`dominated_size_bytes` 来自 dominator tree，并按类聚合。把“只有一个入边”当 retained size 会在共享引用、root、环和不可达对象上给出错误结果。

### 查看按 root 路径聚合的类树

定位某类对象经哪类 root 路径存活时，可以使用 class summary tree 模块：

```sql
INCLUDE PERFETTO MODULE android.memory.heap_graph.class_summary_tree;

SELECT
  upid,
  graph_sample_ts,
  id,
  parent_id,
  name,
  root_type,
  self_count,
  self_size,
  cumulative_count,
  cumulative_size
FROM android_heap_graph_class_summary_tree
ORDER BY cumulative_size DESC
LIMIT 100;
```

表中的 `parent_id` 组成按最短 root 路径聚合后的树，`cumulative_size` 是节点及其后代的总和。它适合生成 flamegraph 风格视图，不应与单对象 dominator tree 混称。

## 工具选择与采集流程

### 需要完整对象值

在可控的调试环境中使用 Android Studio Memory Profiler、`am dumpheap` 或进程内 `Debug.dumpHprofData()`。采集前确认：

- 目标进程是否为预期 user/profile；
- 是否需要 `-g`，以及能否接受额外 GC；
- 是否需要 Bitmap 数据；
- 设备剩余空间和文件保存位置；
- HPROF 中是否可能出现 token、账号、文本、图片或其他用户数据；
- 分析器是否支持 Android 扩展 HPROF。

采集完成后先保留原文件的只读副本，再让转换、裁剪或脱敏工具处理副本。这样能区分“采集不完整”和“后处理破坏格式”。

### 需要时间关联或较短的父进程停顿

使用 `android.java_hprof`，并把采集点与这些事件放在同一条 Perfetto trace 中：

- `art`/GC 事件；
- `process_stats`、内存计数器与 LMK 相关事件；
- 主线程调度、Binder 和帧时间；
- native heap 问题需要另行启用的 `android.heapprofd`。

Java heap graph 和 native allocation profile 是两个数据源。Java 对象的 `native_size` 只反映 `NativeAllocationRegistry` 上报的近似关联值，不能替代 native heap 分配采样。

### KOOM fork-dump 的使用边界

KOOM 2.2.1 的 `ForkJvmHeapDumper` 源码执行 `suspendAndFork()`：子进程调用 `Debug.dumpHprofData(path)`，父进程走 `resumeAndWait(pid)`。`ForkStripHeapDumper` 在这条路径上安装 HPROF 裁剪逻辑，仓库同时提供 `koom-fill-crop.jar`。

这些代码依赖 ART 内部实现和版本适配，入口还会调用 `sdkVersionMatch()` 拒绝不支持的系统。源码中的 fork 设计不能直接推出 Android 17 已适配，也不能推出某个固定毫秒级停顿。接入 Android 17 时要核对 KOOM 版本、ART 符号与实现、目标厂商 ROM、子进程资源占用、文件可解析性和失败回退。

Android 17 的 Perfetto ART Heap Graph 自身也使用 fork。只需要引用图和时间轴时，可先评估系统数据源；需要完整 HPROF、第三方告警策略或定制裁剪时，再评估 KOOM 一类方案。

## 版本边界

| Android 版本 | 相关变化 |
| --- | --- |
| Android 11 | `android.java_hprof` 可用于 ART heap graph 采集 |
| Android 12 | `target_installed_by` 可用；`scan_pids_only_on_start` 默认 `true` |
| Android 13 | `process_cmdline` 支持一个通配符；连续采集默认每轮重扫进程 |
| Android 14—17 | 保持 fork 后写 HeapGraph 的主线；配置与权限仍应按目标 tag 核对 |
| Android 17 / API 37 | 平台源码锚点为 `android-17.0.0_r1` |

版本表用于说明行为演进。命令参数、私有 ART 入口、Perfetto proto 字段和 SQL 模块名都可能随 tag 变化，跨版本脚本应带版本检查。

## Android 17 源码核对清单

阅读或排障时，可以从这些断点逐层核对：

1. `ActivityManagerShellCommand.runDumpHeap()`：参数、默认文件名和等待回调；
2. `ActivityManagerService.dumpHeap()`：`SET_ACTIVITY_WATCHER`、`enforceDebuggable()` 与 Freezer；
3. `ActivityThread.handleDumpHeap()`：`-g` 的 GC 序列和三种 dump 分支；
4. `art::hprof::DumpHeap()`、`Hprof::Dump()`：GC critical section、long suspend 与两遍遍历；
5. `JavaHprofProducer::DataSource::SendSignal()`：PID、UID、`CanProfile()` 与 `SIGRTMIN + 6`；
6. `art/perfetto_hprof/perfetto_hprof.cc`：pipe listener、fork、父进程恢复和子进程写 packet；
7. `profiler_tables.py` 与 `android.memory.heap_graph.*` SQL 模块：表列、采样键和 dominator 聚合。

这条清单把“命令是否发出”“目标为何拒绝”“进程在哪里停”“产物含哪些数据”“SQL 为何算错”分到对应源码层，排查时不必把所有失败都归到 HPROF 解析器。

## 参考源码与文档

- [ActivityManagerShellCommand.java（android-17.0.0_r1）](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/am/ActivityManagerShellCommand.java)
- [ActivityManagerService.java（android-17.0.0_r1）](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/am/ActivityManagerService.java)
- [ActivityThread.java（android-17.0.0_r1）](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/app/ActivityThread.java)
- [ART hprof.cc（android-17.0.0_r1）](https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/runtime/hprof/hprof.cc)
- [ART perfetto_hprof.cc（android-17.0.0_r1）](https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/perfetto_hprof/perfetto_hprof.cc)
- [Perfetto java_hprof_producer.cc（android-17.0.0_r1）](https://android.googlesource.com/platform/external/perfetto/+/refs/tags/android-17.0.0_r1/src/profiling/memory/java_hprof_producer.cc)
- [Perfetto JavaHprofConfig proto（android-17.0.0_r1）](https://android.googlesource.com/platform/external/perfetto/+/refs/tags/android-17.0.0_r1/protos/perfetto/config/profiling/java_hprof_config.proto)
- [Perfetto Java heap profiler 文档](https://perfetto.dev/docs/data-sources/java-heap-profiler)
- [Perfetto Heap Dump Explorer 文档](https://perfetto.dev/docs/visualization/heap-dump-explorer)
- [KOOM 2.2.1](https://github.com/KwaiAppTeam/KOOM/tree/v2.2.1)
