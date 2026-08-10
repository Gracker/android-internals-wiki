# 第 10 章：内存性能

内存问题会以多种形式影响体验：OOM、频繁 GC、帧丢失、前后台恢复变慢、系统换页、cached process 重启，以及业务运行越久越迟缓。第 10 章从应用性能视角组织诊断方法，重点回答三个问题：

1. 增长发生在哪个内存域；
2. 谁持有对象或资源；
3. 这项变化怎样影响 GC、调度、I/O 和用户可感知延迟。

当前平台锚点为 Android 17 / API 37 / `android-17.0.0_r1`。涉及 PSI、cgroup v2、回收与内核内存统计时，以 `android17-6.18-2026-06_r6` 为内核锚点。旧版本差异会保留在对应专题中，结论上限不超过 Android 17。

## 按现象选择入口

| 现场现象 | 建议入口 |
| --- | --- |
| 不清楚 Java、Native、PSS、RSS、SwapPss、Graphics 的区别 | [10.1 App 内存分析](01-app-memory-analysis.md) |
| 页面退出后 Activity、View、callback 或资源仍被持有 | [10.2 内存泄漏](02-memory-leak.md) |
| 多轮业务操作后内存持续增长 | [10.3 内存持续增长](03-memory-growth.md) |
| PSI、换页、lmkd、后台重启或整机卡顿 | [10.4 低内存对系统性能的影响](04-low-memory-impact.md) |
| 需要查看从症状到证据的完整案例 | [10.5 案例集](05-case-studies.md) |
| live set 稳定，但短命分配和 GC 很频繁 | [10.6 内存抖动](06-memory-churn.md) |
| SQLite/Room 查询、CursorWindow 或分页造成峰值 | [10.7 SQLite / Room 性能](07-sqlite-room-performance.md) |
| Graphics、DMA-BUF 或 GPU private memory 增长 | [10.8 GPU / 图形内存统计](08-gpu-memory-tracking.md) |
| ART region、CMC、LOS 或 compaction 引起疑问 | [10.10 ART GC 碎片化与 Compaction](10-art-gc-fragmentation-regions-optimization.md) |

[10.01 Android 内存性能优化](10.01-android-memory-performance-optimization.md) 提供全章决策框架，适合在问题类型还不明确时先读。

## 分析顺序

### 1. 定义业务窗口

把问题写成可重复的操作序列，记录设备、build fingerprint、ART Mainline 模块、应用版本、ABI、构建类型、数据集、前后台状态和采样时钟。

### 2. 确定内存域

至少区分：

- ART managed heap；
- Native heap；
- 匿名映射与文件映射；
- Graphics、DMA-BUF 与 GPU private memory；
- Stack、Code、线程和文件描述符；
- Swap/ZRAM 与系统 PSI。

GC 只能处理 managed heap 中不可达的对象。Native owner、Surface、codec、GPU 和内核页需要各自的证据链。

### 3. 区分 live set、churn 与峰值

- heap dump 用于分析当前可达对象和引用链；
- ART allocation profile 用于分析分配调用栈与分配速率；
- Native heap profile 用于分析 `malloc`/`free`；
- Perfetto 用于对齐 GC、调度、frame、fault、PSI 与业务阶段；
- `dumpsys meminfo` 和 smaps 用于确定统计分类与映射归属；
- DMA-BUF、memtrack 和 GpuService 用于图形内存。

工具标签只能缩小调查范围。找到 owner、生命周期或调用栈后，才能形成可验证的修复。

### 4. 做单变量对照实验

一次只调整一个变量，例如缓存容量、图片目标尺寸、任务并发数、解析批次或 buffer 规格。比较内存指标时，同时观察 CPU、I/O、GC、frame deadline miss、缓存命中和业务尾延迟。

内存降低但重建成本、I/O 或卡顿明显增加，说明方案还需要继续调整。

## 阅读建议

- App 侧排障可从 10.01 和 10.1 开始，再按内存域进入对应小节。
- OOM、GC 抖动和前后台恢复问题，建议与第 4 章的 ART、lmkd、MemoryLimiter、内核回收章节对照。
- 图形与渲染问题要把第 10.8 章和渲染专题放在同一时间线分析，避免只看 Java heap。
- 平台或 OEM 调试还应保存 cgroup、PSI、lmkd、MemoryLimiter 与 ART 配置，不能用 API level 代替设备实际状态。

## 证据边界

- 不使用无源码路径、无官方文档或无可复现实验的数据。
- 不把 PSS、RSS、Java heap、Native allocated 和 GPU memory 直接相加为统一口径。
- 不把 `System.gc()`、`WeakReference`、对象池、WebP、SparseArray 或异步线程写成通用解法。
- 不用一次快照证明泄漏，不用一次 GC 证明资源已经释放。
- 性能收益必须注明设备、构建、负载、指标和对照条件。
