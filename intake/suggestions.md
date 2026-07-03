## [Task2B Main Fixed] 13.21 全部 Task9 Deep Review 问题 — 2026-07-03 18:53
- 已通过主 body 重写修复以下问题：
  1. ✅ 数据源数量 77 → 18（基于 android-17.0.0_r1 源码验证的 ProbesProducer 数据源清单）
  2. ✅ heapprofd 参数修正为 kDefaultShmemSize=8MB, kUnwinderThreads=5，新增双 producer 模型说明
  3. ✅ 删除 ExclusiveTracer/DistributedTracer 等未经源码验证的代码示例及"追踪开销降低 60%"等无依据性能指标
  4. ✅ 修复数据源数量定义标准缺失（明确 18 个 ProbesProducer 数据源与其他类型数据源的区别）
  5. ✅ 补充 heapprofd 双 producer 架构说明（HeapprofdProducer + JavaHprofProducer，信号机制）
- 章节已重新送入 Task6 → Task9 流水线（frontmatter: task2b_state=fixed, pipeline_stage=task6_pending）

## [Task9 Deep Review] 13.21 Perfetto 版本演进与 Android 9-17 新特性验证 — 2026-07-03
- **类型**：源码准确性/原理链断裂
- **位置**：主 body 数据源演进表格
- **问题**：章节声称 Android 17 有 77 个 protobuf 数据源，但底部源码调研验证为 18 个 ProbesProducer 数据源，数据源数量表未经 AOSP 源码逐版本验证
- **建议**：以底部源码调研增补的 18 个 ProbesProducer 数据源为准重写数据源演进表格，删除未经源码验证的 77 个数据源的虚假数据

## [Task9 Deep Review] 13.21 Perfetto 版本演进与 Android 9-17 新特性验证 — 2026-07-03
- **类型**：源码准确性/数据缺失
- **位置**：heapprofd 深度分析段
- **问题**：章节声称 heapprofd 内存占用为"应用内存的 5-10%"，但源码调研增补显示实际参数为 8MB 共享内存、5 个 unwinder 线程，且缺乏测试条件标注
- **建议**：修正为源码中的实际参数：kDefaultShmemSize=8MB, kUnwinderThreads=5，并添加参数使用说明

## [Task9 Deep Review] 13.21 Perfetto 版本演进与 Android 9-17 新特性验证 — 2026-07-03
- **类型**：源码错误/知识盲区
- **位置**：Exclusive Tracing 相关内容
- **问题**：章节中的 ExclusiveTracer、DistributedTracer 类和相关"追踪开销降低 60%"等性能指标缺乏 AOSP 源码佐证，疑似捏造代码示例
- **建议**：删除未经源码验证的 ExclusiveTracer、DistributedTracer 类示例，仅保留已验证的功能描述

## [Task9 Deep Review] 13.21 Perfetto 版本演进与 Android 9-17 新特性验证 — 2026-07-03
- **类型**：原理链断裂
- **位置**：数据源演进历程
- **问题**：章节声称"从 Android 9 的单一 ftrace 发展到 Android 17 的 77 个 protobuf 数据源"，但与底部源码调研的 18 个数据源矛盾，未解释数据源定义标准差异
- **建议**：明确定义数据源类型标准，区分 ProbesProducer 数据源和其他类型数据源，解释两者关系

## [Task9 Deep Review] 13.21 Perfetto 版本演进与 Android 9-17 新特性验证 — 2026-07-03
- **类型**：原理链断裂
- **位置**：heapprofd 双 producer 模型
- **问题**：章节未解释 heapprofd 内部集成 HeapprofdProducer 和 JavaHprofProducer 两个独立 producer 的架构设计原理
- **建议**：补充 heapprofd 双 producer 模型的架构说明，解释两个 producer 的分工和协作机制