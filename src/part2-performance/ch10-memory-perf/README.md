# 第 10 章：内存性能

内存问题会以多种形式影响体验：OOM（内存不足）、频繁 GC、帧丢失、前后台恢复变慢、系统换页、cached process（缓存进程）重启，以及业务运行越久越迟缓。第 10 章从应用性能视角组织诊断方法，重点回答三个问题：

1. 增长发生在哪类内存中；
2. 谁持有对象或资源；
3. 这项变化怎样影响 GC、调度、I/O 和用户可感知延迟。

本章的平台实现以 Android 17 / API 37 / `android-17.0.0_r1` 为核对版本。涉及 PSI（资源压力导致任务停顿的时间）、cgroup v2（控制组机制）、回收与内核内存统计时，以 `android17-6.18-2026-06_r6` 为内核核对版本。旧版本差异会保留在对应专题中，结论范围不超过 Android 17。

## 内容索引

- [10.1 App 内存分析与案例](01-app-memory-analysis-cases.md)
- [10.2 低内存对系统性能的影响](02-low-memory-impact.md)
- [10.3 内存抖动与频繁 GC](03-memory-churn.md)
- [10.4 GPU 与图形内存统计、归因与诊断](04-gpu-graphics-memory-tracking.md)

## 按现象选择入口

| 现场现象 | 建议入口 |
| --- | --- |
| 不清楚 Java、Native、PSS、RSS、SwapPss、Graphics 的区别 | [10.1 App 内存分析与案例](01-app-memory-analysis-cases.md) |
| 页面退出后 Activity、View、callback 或资源仍被持有 | [23.1 内存泄漏检测与治理](../../part5-app/ch23-memory-practice/01-memory-leak-governance.md) |
| 多轮业务操作后内存持续增长 | [10.1 App 内存分析与案例](01-app-memory-analysis-cases.md) |
| PSI、换页、lmkd、后台重启或整机卡顿 | [10.2 低内存对系统性能的影响](02-low-memory-impact.md) |
| 需要查看从症状到证据的完整案例 | [10.1 App 内存分析与案例](01-app-memory-analysis-cases.md) |
| live set（仍存活的对象集合）稳定，但短命分配和 GC 很频繁 | [10.3 内存抖动与频繁 GC](03-memory-churn.md) |
| Graphics、DMA-BUF（跨设备共享的缓冲区）或 GPU private memory（GPU 私有内存）增长 | [10.4 GPU 与图形内存统计、归因与诊断](04-gpu-graphics-memory-tracking.md) |
| SQLite/Room 查询、CursorWindow 或分页造成峰值 | [24.2 数据库与序列化性能](../../part5-app/ch24-io-network/02-database-serialization-performance.md) |
| ART region、CMC（并发标记压缩）、LOS（大对象空间）或 compaction（内存压缩整理）引起疑问 | [4.2 ART Heap、GC 与后台维护调度](../../part1-fundamentals/ch04-memory/02-art-heap-gc-maintenance.md) |

## 分析顺序

### 1. 定义业务窗口

把问题写成可重复的操作序列，记录设备、build fingerprint（系统构建标识）、ART Mainline（可独立更新的 ART 系统模块）版本、应用版本、ABI（应用二进制接口）、构建类型、数据集、前后台状态和采样时钟。

### 2. 确定内存域

至少区分：

- ART managed heap（由 ART 管理的 Java/Kotlin 对象堆）；
- Native heap；
- 匿名映射（没有文件作为后备存储）与文件映射；
- Graphics、DMA-BUF 与 GPU private memory；
- Stack（线程栈）、Code（代码映射）、线程和文件描述符；
- Swap/ZRAM（交换区与压缩内存）和系统 PSI。

GC 只能处理 managed heap 中已经不可达的对象。Native owner（native 资源持有者）、Surface、codec（编解码器）、GPU 和内核页需要各自的证据链。

### 3. 区分 live set、churn 与峰值

- heap dump（堆转储）用于分析当前可达对象和引用链；
- ART allocation profile（分配剖析）用于分析分配调用栈与分配速率；
- Native heap profile 用于分析 `malloc`/`free`；
- Perfetto 用于对齐 GC、调度、frame（帧）、fault（缺页）、PSI 与业务阶段；
- `dumpsys meminfo` 和 smaps（进程内存映射明细）用于确定统计分类与映射归属；
- DMA-BUF、memtrack 和 GpuService 用于统计图形内存。

工具标签只能缩小调查范围。找到 owner（资源持有者）、生命周期或调用栈后，才能提出可验证的修复方案。

### 4. 做单变量对照实验

一次只调整一个变量，例如缓存容量、图片目标尺寸、任务并发数、解析批次或 buffer（缓冲区）规格。比较内存指标时，同时观察 CPU、I/O、GC、frame deadline miss（帧没有按期完成）、缓存命中率和业务尾延迟（少数最慢请求的耗时）。

内存降低但重建成本、I/O 或卡顿明显增加，说明方案还需要继续调整。

## 阅读建议

- App 侧排障从 10.1 开始，再按内存域进入对应小节。
- OOM、GC 抖动和前后台恢复问题，建议与第 4 章的 ART、lmkd、MemoryLimiter、内核回收章节对照。
- 图形与渲染问题要把 10.4 和渲染专题放在同一时间线分析，避免只看 Java heap。
- 平台或 OEM（设备厂商）调试还应保存 cgroup、PSI、lmkd（低内存终止守护进程）、MemoryLimiter 与 ART 配置，不能用 API level 代替设备实际状态。

## 证据边界

- 不使用无源码路径、无官方文档或无可复现实验的数据。
- 不把 PSS、RSS、Java heap、Native allocated 和 GPU memory 直接相加为统一口径。
- 不把 `System.gc()`、`WeakReference`、对象池、WebP、SparseArray 或异步线程写成通用解法。
- 不用一次快照证明泄漏，不用一次 GC 证明资源已经释放。
- 性能收益必须注明设备、构建、负载、指标和对照条件。
