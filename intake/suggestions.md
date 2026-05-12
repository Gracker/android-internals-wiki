## [Task9 Deep Review] 2.10 GPU 渲染深入 — 2026-05-11
- **类型**：源码准确性
- **位置**：Canvas.drawRect 示例源码路径
- **问题**：源码路径错误，未展示正确的AOSP实现路径
- **建议**：修正源码路径为 frameworks/base/graphics/java/android/graphics/BaseCanvas.java，补充完整的调用链说明

## [Task9 Deep Review] 2.10 GPU 渲染深入 — 2026-05-11
- **类型**：原理链完整性
- **位置**：GPU渲染管线章节
- **问题**：从Vertex Shader直接跳到Fragment Shader，缺少图元装配和光栅化阶段
- **建议**：补充图元装配（Primitive Assembly）和光栅化（Rasterization）阶段的详细说明，包括GPU内部的完整处理流程

## [Task9 Deep Review] 8.9 Android 游戏性能与 Game Mode/State API — 2026-05-11
- **类型**：源码准确性
- **位置**：Game Mode API使用示例
- **问题**：`GameManager.GAME_MODE_CUSTOM`常量在公开API中不存在
- **建议**：移除不存在的常量，使用兼容性处理逻辑，明确API边界和fallback机制

## [Task9 Deep Review] 2.9 渲染机制的版本演进 — 2026-05-11
- **类型**：版本差异
- **位置**：Android 16渲染章节
- **问题**：Android 16相比Android 15的具体渲染机制变化描述不足
- **建议**：明确列出Android 16在渲染方面的具体变化，包括Vulkan Profile要求、ARR增强、新API特性等

## [Task9 Deep Review] 2.10 GPU 渲染深入 — 2026-05-11
- **类型**：数据缺失
- **位置**：Vulkan vs OpenGL ES性能对比章节
- **问题**：性能改进数据缺乏基准测试数据支持
- **建议**：补充实际测试数据，包括不同分辨率、不同场景下的性能对比测试结果

## [Task9 Deep Review] 8.9 Android 游戏性能与 Game Mode/State API — 2026-05-11
- **类型**：数据缺失
- **位置**：ADPF热管理收益章节
- **问题**：声称的"57%收益"缺乏具体测试条件和数据支撑
- **建议**：提供具体的测试场景、设备型号、测试方法和量化数据，确保数据可验证性
## [Task9 Deep Review] 17.2 SoC 平台差异 — 2026-05-12
- **类型**：源码准确性
- **位置**：SQL 查询示例中的 sched 表查询
- **问题**：使用了不存在的 prev_cpu 字段，实际应为 cpu 字段 + LAG 窗口函数
- **建议**：修正 SQL 查询使用正确的字段和窗口函数，确保与 Perfetto sched 表实际结构匹配

## [Task9 Deep Review] 17.2 SoC 平台差异 — 2026-05-12
- **类型**：原理链完整性
- **位置**：全大核架构下的迁移成本解释
- **问题**：仅提到 DSU 存在但未解释实际迁移开销机制
- **建议**：补充跨核迁移的实际开销分析，包括缓存未命中、uclamp、集群策略等因素的具体影响

## [Task9 Deep Review] 17.2 SoC 平台差异 — 2026-05-12
- **类型**：数据与案例支撑
- **位置**：GPU 性能对比部分
- **问题**：缺乏具体 Perfetto trace 片段示例
- **建议**：补充不同 SoC 上 GPU 渲染的 Perfetto track 实际截图对比，展示架构差异导致的 pipeline 特性

## [Task9 Deep Review] 20.4 ANR 治理策略 — 2026-05-12
- **类型**：原理链完整性
- **位置**：Dispatchers.IO 降级逻辑
- **问题**：未解释线程池耗尽时的降级机制和调度策略
- **建议**：补充 kotlinx-coroutines 线程池耗尽时的降级逻辑，包括 limitedParallelism 视图的具体行为和调度策略

## [Task9 Deep Review] 20.4 ANR 治理策略 — 2026-05-12
- **类型**：数据与案例支撑
- **位置**：ANR 治理策略整体
- **问题**：缺乏实际 ANR 案例的完整分析流程和决策过程
- **建议**：添加 2-3 个完整的 ANR 案例分析，包含实际排查过程、决策依据和优化效果

## [Task9 Deep Review] 20.8 崩溃聚合与归因分析 — 2026-05-12
- **类型**：原理链完整性
- **位置**：崩溃聚合算法分析
- **问题**：缺少具体实现细节和时间复杂度分析
- **建议**：详细分析主流崩溃聚合算法（如堆栈相似度计算、指纹生成算法）的实现细节和性能特征

## [Task9 Deep Review] 20.8 崩溃聚合与归因分析 — 2026-05-12
- **类型**：数据与案例支撑
- **位置**：崩溃聚合效果部分
- **问题**：缺乏崩溃聚合效果的量化数据和基准测试
- **建议**：添加不同聚合算法在实际应用中的效果对比数据，包括聚合准确率、处理性能、存储效率等指标

## [Task9 Deep Review] 20.8 崩溃聚合与归因分析 — 2026-05-12
- **类型**：数据与案例支撑
- **位置**：实战指导部分
- **问题**：缺乏具体实战案例和作者经验分享
- **建议**：补充完整的崩溃治理实战案例，包括问题发现、分析过程、修复决策和效果验证

## [Task14 参考书扫描] 1.15 JNI/NDK 性能优化 — 2026-05-12
- **类型**：内容补充
- **来源**：[结构参考: Clippings/Android 应用稳定性剖析与优化 - Native Hook 全解析：Native 闯关入门秘籍.md]
- **建议补充**：Native Hook 三大方案（GOT/PLT Hook、Inline Hook、dlsym 家族）的原理对比与适用场景；GOT 表 hook 完整实现流程（基地址获取 via /proc/self/maps → 重定位偏移 via readelf -r → mprotect 改写权限 → 替换函数指针）；Android 各版本 dlsym 限制差异；bhook/bytehook 等成熟框架选型建议
- **参考书覆盖深度**：深入（含完整代码示例和 ELF 原理）
- **知识点属性**：有代码示例、有案例、适用 Android 全版本、无过时风险

## [Task14 参考书扫描] 4.3 ART 虚拟机内存管理 / 4.5 App 内存优化 — 2026-05-12
- **类型**：内容补充
- **来源**：[结构参考: Clippings/Android 应用稳定性剖析与优化 - Native 内存泄漏监控：寻找 Native 中不可达内存.md]
- **建议补充**：libmemunreachable 系统级 Native 内存泄漏检测原理（fork 子进程 + pipe 通信 + root 引用链遍历）；32→64 位架构迁移的虚拟内存差异；CollectAllocations 中 heap/anon/globals/stack 四类映射的 Root 标记策略；Android N+ 系统自带能力的使用方式
- **参考书覆盖深度**：深入（含 AOSP 源码分析）

## [Task14 参考书扫描] 4.3 ART 虚拟机内存管理 / 4.5 App 内存优化 — 2026-05-12
- **类型**：内容补充
- **来源**：[结构参考: Clippings/Android 应用稳定性剖析与优化 - OOM 发生路径：了解 OOM 是如何产生的.md]
- **建议补充**：OOM 两大分类框架（Java 堆限制 vs 虚拟内存不足）的 ART 源码级分析；Heap::AllocObjectWithAllocator → AllocateInternalWithGc → Heap::ThrowOutOfMemoryError 完整调用链；Thread::CreateNativeThread 中 pthread_create 失败导致的 OOM 路径；JNI 层 NewString 等分配的 OOM 触发条件；各 space（NonMoving/Main/BumpPointer/Region/LOS）的 OOM 日志差异
- **参考书覆盖深度**：深入（含 ART 源码级调用链分析）

## [Task14 参考书扫描] 4.1 Android 内存模型全景 — 2026-05-12
- **类型**：内容补充
- **来源**：[结构参考: Clippings/Android 应用稳定性剖析与优化 - 初识内存：内存是什么？.md]
- **建议补充**：OOM pending exception 机制的底层实现（throwing_OutOfMemoryError TLS 标志位 → ThrowNewException → UncaughtExceptionHandler 捕获）；堆内存 OOM 与虚拟内存 OOM 的独立性说明及典型错误信息格式对比
- **参考书覆盖深度**：概述（基础概念，但 OOM 投递机制有参考价值）


---

[Task2B 回炉失败] 22.3 — 原因：需要高爷确认

**问题**：Task 9 深度技术 Review 指出 Pausable Composition 在 Compose 1.10 中是实验性版本，正式默认启用在 Compose 1.11。当前章节标题写的是"Pausable Composition（Compose 1.10 默认启用）"。

**需要确认**：
1. Pausable Composition 的默认启用版本是 Compose 1.10 还是 1.11？
2. 如果是 1.11，需要同步更新章节标题和相关描述

**Queue 条目 ID**：task9-22.3-pausable-comp-version-error
**状态**：blocked

记录时间：2026-05-12 07:16


## [Task9 Deep Review] 22.3 Jetpack Compose 性能优化 — 2026-05-12
- **类型**：版本差异/知识盲区
- **位置**：工具介绍部分
- **问题**：Android Studio Compose Profiler 遗漏，未介绍 Android Studio 2024.1+ 的 Compose Profiler 工具使用方法
- **建议**：补充工具使用方法和最佳实践

## [Task9 Deep Review] 22.3 Jetpack Compose 性能优化 — 2026-05-12
- **类型**：数据缺失
- **位置**：优化效果说明
- **问题**：性能对比数据不充分，缺乏具体的性能提升数据支撑
- **建议**：补充基准测试数据和性能提升百分比

## [Task9 Deep Review] 17.2 SoC 平台差异 — 2026-05-12
- **类型**：交叉引用错误
- **位置**：GPU 架构描述
- **问题**：与章节 2.10 的 GPU 渲染管线描述存在术语不一致
- **建议**：统一 GPU 相关术语使用

## [Task9 Deep Review] 17.2 SoC 平台差异 — 2026-05-12
- **类型**：数据缺失
- **位置**：Oryon 处理器参数
- **问题**：性能参数缺乏一手资料锚定，Oryon L1/L2 cache 一手资料边界仍未闭合
- **建议**：标注参数来源和验证边界

## [Task9 Deep Review] 16.5 Android 17 (API 37) 性能行为变更与适配方法 — 2026-05-12
- **类型**：知识盲区
- **位置**：DeliQueue 机制说明
- **问题**：DeliQueue 同步屏障机制描述不完整，需查阅 postSyncBarrier() 实现
- **建议**：补充同步屏障机制的详细实现说明

## [Task9 Deep Review] 16.5 Android 17 (API 37) 性能行为变更与适配方法 — 2026-05-12
- **类型**：数据缺失
- **位置**：性能提升说明
- **问题**：性能提升数据缺乏具体测试条件，缺乏具体的测试环境和测试条件说明
- **建议**：补充测试环境和基线数据

## [Task9 Deep Review] 1.5 线程模型 — 2026-05-12
- **类型**：数据缺失
- **位置**：L234 IdleHandler 1-2ms 阈值缺少测试条件
- **问题**：“控制在 1-2ms 以内”是经验阈值，但正文未给设备、刷新率、Trace 或业务场景。
- **建议**：补一条 Perfetto 示例或改成“不得超过当前帧预算中的空闲窗口”，避免固定阈值被当成平台规则。

## [Task9 Deep Review] 2.14 图形 API 演进与选择策略（OpenGL ES / Vulkan / ANGLE） — 2026-05-12
- **类型**：数据缺失
- **位置**：L334 WebGPU 90%-95% Vulkan 吞吐量缺少一手数据
- **问题**：AndroidX WebGPU release notes 只说明 alpha 版本与 Dawn commit 更新，未给 Android 17 compute pipeline 对 Vulkan 90%-95% 的公开基准。
- **建议**：补 benchmark 来源、设备、driver、workload、样本数；否则删除百分比，只保留 WebGPU 是更高层 Kotlin binding / Dawn 路线。
