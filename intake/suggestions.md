## [Task9 Deep Review] 14.16 Layout Inspector 与 ViewDebug 布局调试 — 2026-06-28
- **类型**：原理链完整性
- **位置**：invalidate 与 measure/layout 关系说明
- **问题**：未充分解释 invalidate 触发后的完整调用链，特别是与 measure/layout 阶段的因果关系
- **建议**：补充 invalidate → PFLAG_DIRTY → Choreographer callback → scheduleTraversals → performMeasure/performLayout 的完整流程说明

## [Task9 Deep Review] 14.22 HPROF Heap Dump 管线与 Perfetto java_hprof 数据源 — 2026-06-28
- **类型**：数据支撑
- **位置**：heap dump 性能影响数据
- **问题**：章节中提到的 heap dump 暂停时长和 I/O 压力数据缺少实际测量来源和实验条件说明
- **建议**：补充具体的测试环境、堆大小范围、实际测量数据来源，或注明数据来自第三方研究报告

## [Task9 Deep Review] 14.22 HPROF Heap Dump 管线与 Perfetto java_hprof 数据源 — 2026-06-28
- **类型**：交叉引用一致性
- **位置**：§19.3 章节引用
- **问题**：章节中引用 §19.3 讲述 KOOM fork-dump，但该章节编号可能不存在或内容不符
- **建议**：验证 §19.3 章节是否存在并包含相关内容，或修正为正确的章节编号## [Task9 Deep Review] 1.25 Android 17 Binder IPC 异步机制与批处理流水线 — 2026-06-28

- **类型**：源码准确性
- **位置**：IPCThreadState.cpp:1056-1104 和 IPCThreadState.cpp:1246-1362
- **问题**：文中所引用的行号与 Android 17 实际源码位置不符，transact 函数实际在 1100-1150 行左右，talkWithDriver 函数在 1300-1420 行左右
- **建议**：修正源码引用行号以确保开发者能准确定位到对应代码

## [Task9 Deep Review] 1.25 Android 17 Binder IPC 异步机制与批处理流水线 — 2026-06-28

- **类型**：原理完整性
- **位置**：2.3 节冻结回执机制
- **问题**：缺少 BR_TRANSACTION_PENDING_FROZEN 投递后解冻时机的详细说明
- **建议**：补充解冻时机、内核队列管理机制、解冻后的投递优先级等完整流程说明

## [Task9 Deep Review] 1.25 Android 17 Binder IPC 异步机制与批处理流水线 — 2026-06-28

- **类型**：版本差异
- **位置**：7.1 节 Android 版本对比
- **问题**：Android 16 到 Android 17 的差异描述过于简略，缺少具体的 API 或行为变化
- **建议**：补充具体的 API 变化、默认配置调整、新引入的优化措施等详细对比

## [Task9 Deep Review] 1.25 Android 17 Binder IPC 异步机制与批处理流水线 — 2026-06-28

- **类型**：数据支撑
- **位置**：5.1 节性能特征表格
- **问题**：多个关键性能数据标注 "[待补充]"，影响技术结论可信度
- **建议**：补充 oneway vs 同步调用的实际延迟对比数据、批处理模式下 syscall 减少量、frozen sync 立即返回错误 vs 普通同步等待卡住的 ANR 次数对比等量化数据

## [Task9 Deep Review] 1.25 Android 17 Binder IPC 异步机制与批处理流水线 — 2026-06-28

- **类型**：数据支撑
- **位置**：8.1 节 Perfetto Trace 表现
- **问题**：缺少实际的 Perfetto Trace 截图案例
- **建议**：补充实际的 Perfetto Trace 截图，展示 oneway vs 同步调用的 trace 表现差异

## [Task9 Deep Review] 1.25 Android 17 Binder IPC 异步机制与批处理流水线 — 2026-06-28

- **类型**：知识盲区
- **位置**：章节整体
- **问题**：缺少 Binder 事务优先级机制在 Android 17 中的实现细节
- **建议**：补充事务优先级机制说明，包括高优先级事务的调度策略和低延迟保障措施

## [Task9 Deep Review] 1.25 Android 17 Binder IPC 异步机制与批处理流水线 — 2026-06-28

- **类型**：知识盲区
- **位置**：章节整体
- **问题**：未讨论跨进程同步机制（如 Barrier/CountDownLatch）与 Binder oneway 的交互
- **建议**：补充跨进程同步机制与 Binder oneway 的交互说明，包括潜在的死锁风险和最佳实践## [Task9 Deep Review] 1.25 Android 17 Binder IPC 异步机制与批处理流水线 — 2026-06-28
- **类型**：原理链完整性
- **位置**：第2节 oneway 调用与异步语义
- **问题**：解释了 oneway 调用如何工作，但未说明为什么 Android 系统需要同时支持 oneway 和同步调用
- **建议**：补充架构设计决策推理，说明同步和异步调用的适用场景、性能权衡和设计哲学

## [Task9 Deep Review] 1.25 Android 17 Binder IPC 异步机制与批处理流水线 — 2026-06-28
- **类型**：机制解释深度
- **位置**：第4节内核批处理流水线
- **问题**：批处理性能提升的解释过于表面，缺少对 syscall 开销的具体分析
- **建议**：深入分析 syscall 开销的构成，包括上下文切换、内核态/用户态切换成本，以及批处理如何减少这些开销

## [Task9 Deep Review] 1.25 Android 17 Binder IPC 异步机制与批处理流水线 — 2026-06-28
- **类型**：交叉引用一致性
- **位置**：第9节关联章节
- **问题**：文中提到章节 1.4 "Binder 基础架构"，但可能需要指向更具体的 BC/BR 协议章节
- **建议**：验证交叉引用的准确性，确保指向最相关的章节内容

## [Task9 Deep Review] 1.25 Android 17 Binder IPC 异步机制与批处理流水线 — 2026-06-28
- **类型**：术语一致性
- **位置**：全文
- **问题**：不同章节中对 "binder 线程" 和 "IPC 线程" 的术语使用可能存在差异
- **建议**：统一术语使用，明确 binder 线程和 IPC 线程的定义和关系
## [Task2A Gap Mining] 已检查方向记录 — 2026-06-28 09:11

**结论：本轮未发现评分 ≥ 14 的知识缺口，跳过新章节创建。**

### 已检查方向（避免重复挖掘）

#### AOSP 子系统覆盖检查
- ✅ frameworks/base/ 核心服务（AMS, PMS, WMS, InputFlinger, etc.）— 全部已覆盖
- ✅ system/ 核心组件（lmkd, vold, netd, installd）— 全部已覆盖
- ✅ packages/modules/（DNSResolver, Bluetooth, Media）— 主要模块已覆盖
- ✅ frameworks/native/（Binder, SurfaceFlinger, etc.）— 已覆盖

#### Android 17 新特性覆盖检查
- ✅ Binder 异步批处理（1.25/1.27）、DeliQueue（1.26/1.28）
- ✅ MemoryLimiter（4.17）、App Hibernation（5.24）
- ✅ 16KB Page Size（4.7/20.13）、Edge-to-Edge（2.26）
- ✅ Predictive Back（3.12/22.13）、Desktop Mode（2.20/22.14）
- ✅ Private Space（17.7）、App Archiving（1.20）
- ✅ AVF/pKVM（1.32）、MTE（20.11）
- ✅ JobScheduler 五维节流（5.23）、Low Power Standby（5.25）
- ✅ HWUI Vulkan 多队列（18.26）、WebGPU（18.27）

#### 官方文档覆盖检查
- ✅ ADPF（5.9/8.19/25.11/25.16）、Baseline Profiles（8.7/21.4/19.15）
- ✅ ProfilingManager（8.10/8.16/14.7/19.16）
- ✅ ApplicationExitInfo（26.9）、ApplicationStartInfo（26.13）
- ✅ Photo Picker（24.13）、MediaStore（24.12）
- ✅ Compose 性能（7.7/22.3/22.15-22.28/18.25）

#### 新兴方向评估（均 < 14 分）
- ❌ Wear OS 性能（8/20）— 素材不足，受众窄
- ❌ Android TV 性能（7/20）— 素材不足
- ❌ KMP 性能（12/20）— 素材丰富度不够
- ❌ io_uring on Android（10/20）— 缺 Android 特定素材
- ❌ VPN 性能（8/20）— 太窄
- ❌ OTA/Update Engine 性能（7/20）— 超出本书范围
- ❌ File-Based Encryption 性能（9/20）— 已有稳定文档，缺新素材
- ❌ Shader 编译/纹理流式传输性能（9/20）— 主要面向游戏开发者
- ❌ Kotlin Multiplatform 性能（12/20）— 最接近但素材不够

#### 参考书交叉验证
- ✅ 《Android 应用稳定性剖析与优化》15 篇 — 全部主题已映射到 ch20（18 节）
- ✅ 《Android 性能优化》16 篇 — 全部主题已映射到 ch21-ch25
- ✅ 《线上疑难问题》59 篇 — 全部主题已映射到 ch26 及各章节案例

### 当前全书规模
- 总小节：545（finalized: 334, ready-for-review: 144, draft: 40, 其他: 27）
- Part 5 覆盖：ch20(18) + ch21(17) + ch22(30) + ch23(17) + ch24(20) + ch25(23) + ch26(23) = 148 节
- 空 draft（<15行）：0 个
- 小 draft（<60行有 outline）：20 个 → 这些是 Phase 2 的加工目标
