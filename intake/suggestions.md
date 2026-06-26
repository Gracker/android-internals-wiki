## [Task9 Deep Review] 18.25 Jetpack Compose 渲染管线架构 — 2026-06-26

### [P2] 源码引用准确性
- **类型**：源码准确性
- **位置**：Choreographer.FrameCallback API 描述
- **问题**：章节提到 "FrameData.deadlineNanos" 但未明确标注 API 版本限制。AOSP android-17.0.0_r1 中 FrameCallback.doFrame() 只有 frameTimeNanos 参数，FrameData.deadlineNanos 在 API 34+ 才可用。
- **建议**：在章节中明确标注 API 版本要求："FrameTimeline.deadlineNanos 需要 Android 14 (API 34+) 支持，API 31-33 设备回退到固定估算"

### [P2] 原理链完整性
- **类型**：原理完整性
- **位置**：PausableComposition 与 RenderThread 协作部分
- **问题**：缺少详细说明当 PausableComposition 跨帧完成时，RenderThread 如何处理部分完成的 display list 构建。现有描述未覆盖跨帧场景下的线程同步问题。
- **建议**：补充 PausableComposition 跨帧完成时，RenderThread 的处理策略和同步机制，包括 partial display list 如何被缓存和后续帧的合并逻辑。

### [P2] 知识盲区
- **类型**：知识盲区
- **位置**：内存管理部分
- **问题**：缺少对 RenderNode 内存分配/回收策略的深入分析。章节未讨论内存压力下的缓存策略、LRU 算法、以及低端设备的内存优化方案。
- **建议**：补充 RenderNode 内存管理机制，包括创建池化策略、内存阈值控制、低端设备适配方案，以及监控内存使用的方法。

## [Task9 Deep Review] 16.1 Google 官方的性能优化思路 — 2026-06-26

### [P2] 数据缺失
- **类型**：数据缺失
- **位置**：Baseline Profiles 效果描述
- **问题**：章节提到 "很多应用测得的执行速度提升大约在 30% 左右"，但未提供具体的测试基准、测试设备配置、应用类型等关键信息。
- **建议**：补充具体的性能测试数据，包括测试基准（如启动时间、滚动性能）、设备配置、应用类型样本数量、测试方法说明。

### [P2] 数据缺失
- **类型**：数据缺失
- **位置**：lock-free MessageQueue 性能描述
- **问题**：章节正确指出了 Android 17 lock-free MessageQueue 的新特性，但缺少具体的性能对比数据来量化改进效果。
- **建议**：补充 lock-free vs legacy 队列的性能对比数据，包括吞吐量提升、延迟降低、线程扩展性等指标的测试结果。

### [P2] 数据缺失
- **类型**：数据缺失
- **位置**：AutoFDO 效果描述
- **问题**：章节提到 AutoFDO 优化内核和系统 native binary，但缺少具体的性能提升数据和适用场景说明。
- **建议**：补充 AutoFDO 的具体性能数据，包括编译优化后的启动时间改善、运行时性能提升百分比、适用的工作负载类型。

### [P2] 知识盲区
- **类型**：知识盲区
- **位置**：性能测试方法论
- **问题**：章节缺少系统性的性能测试方法论指导，如如何选择合适的测试指标、建立基线、回归测试策略等。
- **建议**：补充完整的性能测试方法论，包括关键指标选择、基线建立流程、性能回归检测策略、不同场景的测试重点。

### [P2] 知识盲区
- **类型**：知识盲区
- **位置**：优化策略取舍分析
- **问题**：章节缺少不同优化策略的适用性分析和取舍指导，开发者难以判断在什么场景下应该选择哪种优化方向。
- **建议**：增加优化策略决策树，根据应用类型、性能瓶颈、资源约束等因素提供具体的优化路径选择建议。
## [Task6 Review] 26.3 性能指标采集与上报 — 2026-06-26

### Issue 1: 锚点缺失 — 🔹 [网络聚合]
- **类型**：需补充素材
- **位置**：全文缺失
- **问题**：outline 要求覆盖"网络性能指标如何通过 StatsD 进行 URL pattern 归一化、状态码聚合和 payload size 统计"，但正文中完全没有涉及这些内容。
- **建议**：补充一节说明网络性能指标的采集与聚合机制，包括 URL pattern 归一化规则、HTTP 状态码分组统计、payload size 分类。
- **review 日志**：logs/review/2026-06-26-21-review.md

### Issue 2: 锚点缺失 — 🔹 [JankStats 关系]
- **类型**：需补充素材
- **位置**：全文缺失
- **问题**：outline 要求"区分系统级性能指标与端侧 JankStats 的数据分工，明确什么情况需要自采补充"，但 JankStats 在正文中零出现。
- **建议**：补充一段说明 StatsD 性能 Atom 与 JankStats 的分工——StatsD 做系统级聚合上报，JankStats 做端侧实时帧级诊断；什么场景下 App 需要在 JankStats 和 StatsD 之间做补充。
- **review 日志**：logs/review/2026-06-26-21-review.md

### Issue 3: 最佳实践章节内容过薄
- **类型**：需重写
- **位置**：性能监控最佳实践 > 隐私保护 / 数据生命周期管理
- **问题**：隐私保护仅 3 条泛化建议（脱敏处理/最小化采集/用户同意），数据生命周期管理仅 3 条泛化建议（实时7天/聚合90天/原始30天），没有 Android 17 特有机制或 StatsD 具体细节。
- **建议**：隐私保护应结合 Android 17 权限模型（READ_PRECISE_STATS、READ_APP_USAGE、READ_NETWORK_USAGE）和运行时权限流程展开；数据生命周期应与正文提到的 StatsD 环形缓冲（24h）、ZSTD 压缩归档、DeviceConfig 动态控制等机制关联，而非泛化数字。
- **review 日志**：logs/review/2026-06-26-21-review.md

### Issue 4: 数据缺乏测试条件
- **类型**：需确认
- **位置**：Android 17 原生内存跟踪 > 内存分类精度变化（表格后段落）
- **问题**："整体看，Android 17 的内存跟踪开销比前代降低了约 40%，分类精度提升约 70%"——这两个数字缺乏测试条件（设备型号、测试方法、基线定义），违反 writing-guide 的数据规范。
- **建议**：补充测试条件（如设备型号、测试场景）或标注数据来源；如无法溯源，改为定性描述。
- **review 日志**：logs/review/2026-06-26-21-review.md

### Issue 5: API 名称准确性存疑
- **类型**：需确认
- **位置**：内存泄漏检测：LeakCanary（第二段）
- **问题**："Android 14+ 上 LeakCanary 利用了 ScheduleRef 和 PausedState 进行更精确的引用追踪"——ScheduleRef 不是已知的 LeakCanary 公开 API 类型，可能是对内部机制的误述。
- **建议**：核实 LeakCanary 2.x 源码（square/leakcanary）中是否存在 ScheduleRef 类型；如不存在，修正为准确的机制描述或删除该句。
- **review 日志**：logs/review/2026-06-26-21-review.md

## [2026-06-26 21] Task2A 知识缺口挖掘 — 已检查方向记录

本轮检查方向（避免下次重复扫描）：

### 素材驱动
- 41 个 unmapped DeepResearch 源全部逐一评估
- 高优先源：binder-ipc-latency、memtrack-jni-aggregation、profilingmanager-anomaly、fair-memory-trim、flutter-3.44-agentic、as-memory-profiler-jvmti、apm-tools-benchmark、perfdog-datasources
- 结论：大部分与现有章节重叠（1.4 Binder、4.6 onTrimMemory、8.10/8.16 ProfilingManager、14.1 AS Profiler、19.10 APM 工具、19.19 PerfDog 等）或素材不足（单一 DeepResearch 无交叉验证源）

### AOSP 结构对照
- frameworks/base 核心服务：AMS、PMS、WMS、InputManager、DisplayManager 全部已有章节
- system/ 核心组件：vold、netd、lmkd、installd、tombstoned 均已覆盖或隐含覆盖
- packages/modules/：Mainline Module 性能影响无足够素材

### 官方文档对照
- Android 17 behavior changes 全面对照：Edge-to-Edge (2.26)、16KB (4.7/20.13)、FGS types (5.17)、Predictive Back (3.12/22.13) 均已覆盖
- 无发现未覆盖的 Android 17 性能相关行为变更

### 章节深挖
- ch01-ch06（Part 1）：27+30+12+15+22+7 节，覆盖极为充分
- ch20-ch26（Part 5）：18+16+26+12+20+22+21 节，实战篇覆盖极为充分
- Clippings 三本参考书（90+ 篇）的知识点已全部映射到现有章节

### 结论
全书 488 节已覆盖 Android 17/API 37 范围内所有核心性能主题。本轮未发现评分 ≥ 14 的知识缺口。下一轮建议探索：Wear OS/TV/Auto 性能专题、Android 17 企业/MDM 性能约束、或等待新的 DeepResearch 素材积累。


## [Task9 Deep Review] 26.3 性能指标采集与上报 — 2026-06-26
- **类型**：源码准确性
- **位置**：summary.art-heap 关键字说明
- **问题**：声称 Android 17 的 Debug.MemoryInfo API 包含  关键字，但实际 AOSP 中不存在此关键字
- **建议**：移除不存在的关键字说明，使用正确的 AOSP API 如 、 等

## [Task9 Deep Review] 26.3 性能指标采集与上报 — 2026-06-26
- **类型**：源码准确性
- **位置**：android_os_Debug_getGpuPrivateMemoryKb 方法
- **问题**：引用了不存在的方法，声称用于查询 GPU 私有内存
- **建议**：使用正确的 AOSP GPU 内存查询 API，如 memtrack HAL 的正确方法或系统统计接口

## [Task9 Deep Review] 26.3 性能指标采集与上报 — 2026-06-26
- **类型**：源码准确性
- **位置**：MEMTRACK_FLAG_GPU_PRIVATE 标志位
- **问题**：声称 Android 17 引入了不存在的 GPU 私有内存标志位
- **建议**：使用正确的 memtrack HAL 标志位，如 、 等

## [Task9 Deep Review] 26.3 性能指标采集与上报 — 2026-06-26
- **类型**：版本差异覆盖
- **位置**：Android 16-17 内存分类精度提升
- **问题**：声称精度从 ±15% 提升到 ±5%，但无 AOSP 或 benchmark 数据支撑
- **建议**：补充实际测试数据或移除具体的精度百分比，改为定性描述

## [Task9 Deep Review] 26.3 性能指标采集与上报 — 2026-06-26
- **类型**：交叉引用一致性
- **位置**：与 26.1 观测性架构关系
- **问题**：未说明性能采集在整体观测性框架中的位置和关系
- **建议**：增加与 26.1 架构的明确关联说明，说明性能采集在整体观测性体系中的定位
