## [Task9 Deep Review] 2.1 Android 渲染架构全景 — 2026-06-01
- **类型**：源码准确性/原理完整性/版本差异
- **位置**：版本演进段落
- **问题**：将 Android 3.0 HWUI/DisplayList 与 Android 5.0 RenderNode/RenderThread 混合描述，需按两个独立架构演进拆开
- **建议**：按 AOSP android-4.4.4_r2 的 DisplayList/DisplayListRenderer 与 android-5.0.0_r1 的 RenderNode/renderthread 分工修正版本演进描述

## [Task9 Deep Review] 2.1 Android 渲染架构全景 — 2026-06-01
- **类型**：源码准确性
- **位置**：BufferQueue 伪代码
- **问题**：文中示意性伪代码 `BufferItem item = consumer.acquireBuffer();` 不对应实际 AOSP 方法签名
- **建议**：移除或替换为真实 AOSP BufferQueue.cpp 中的实际方法引用

## [Task9 Deep Review] 2.1 Android 渲染架构全景 — 2026-06-01
- **类型**：原理完整性
- **位置**：三缓冲机制原理
- **问题**：从双缓冲问题到三缓冲解决方案的因果链基本完整，但缺少对"为什么三缓冲会增加显示延迟"这一关键副作用的分析
- **建议**：补充三缓冲增加一帧显示延迟的副作用说明

## [Task9 Deep Review] 2.5 MainThread 与 RenderThread 协作 — 2026-06-01
- **类型**：源码准确性
- **位置**：ADPF 性能反馈机制
- **问题**：文中提到 Android 16 的 headroom API，但实际 ADPF hint session 上报机制在 Android 14 就已存在于 CanvasContext.cpp 中
- **建议**：Android 16 应单独说明 headroom API，与已存在的 hint session 机制区分

## [Task9 Deep Review] 2.5 MainThread 与 RenderThread 协作 — 2026-06-01
- **类型**：原理准确性
- **位置**：同步栅栏解释
- **问题**：syncFrameState 的阻塞点解释不够准确，UI 线程等的是 RenderThread 完成本帧同步阶段，不一定等上一帧 GPU 完成
- **建议**：修正为 UI 线程等待 RenderThread 完成本帧同步阶段，包括 prepareTree、layer update、makeCurrent、纹理准备等

## [Task9 Deep Review] 2.1 Android 渲染架构全景 — 2026-06-01
- **类型**：版本差异
- **位置**：GPU 分片并行提交
- **问题**：Adreno 830+ 硬件分片架构及多 CPU 核心同时录制机制未覆盖
- **建议**：补充 Adreno 830+ 多核并行录制技术及其对 GPU RenderThread 的性能影响

## [Task9 Deep Review] 2.1 Android 渲染架构全景 — 2026-06-01
- **类型**：数据支撑
- **位置**：性能对比数据
- **问题**：软件 vs 硬件渲染的性能对比缺乏具体 benchmark 数据支持
- **建议**：补充实际测试数据，包括设备型号、测试方法、性能对比数值

## [Task9 Deep Review] 2.5 MainThread 与 RenderThread 协作 — 2026-06-01
- **类型**：版本差异
- **位置**：DeliQueue 版本边界
- **问题**：Android 17 的 DeliQueue 作用在 MessageQueue 路径，不能写成 HWUI RenderThread WorkQueue 的替代实现
- **建议**：修正 DeliQueue 的作用范围说明，区分 RenderThread WorkQueue 与 MessageQueue 两个不同机制

## [Task9 Deep Review] 2.5 MainThread 与 RenderThread 协作 — 2026-06-01
- **类型**：知识盲区
- **位置**：多窗口场景下的线程争抢
- **问题**：同进程多窗口共用单例 RenderThread 的竞争机制未在原始大纲中包含
- **建议**：补充同进程多窗口场景下的 RenderThread 争抢和性能影响分析

## [Task9 Deep Review] 2.5 MainThread 与 RenderThread 协作 — 2026-06-01
- **类型**：数据支撑
- **位置**：Fence 机制等待时间
- **问题**：同步栅栏和 Fence 等待的具体耗时数据缺乏量化支撑
- **建议**：补充实际测试数据，包括 Fence 等待时间的量级和影响因素

## [Task9 Deep Review] 19.09 Measure — 2026-06-01
- **类型**：原理完整性
- **位置**：平台型 APM 数据模型
- **问题**：从事件类型到会话时间线的因果链完整，但缺少数据聚合和查询的底层原理说明
- **建议**：补充 Measure 后端数据聚合、索引和查询机制的技术原理解释

## [Task9 Deep Review] 19.09 Measure — 2026-06-01
- **类型**：知识盲区
- **位置**：与现有监控平台集成
- **问题**：Measure 与团队现有日志平台、埋点平台的分工协作模式未覆盖
- **建议**：补充 Measure 与 ELK、Prometheus、Grafana 等现有监控集成的模式和最佳实践

## [Task9 Deep Review] 19.09 Measure — 2026-06-01
- **类型**：知识盲区
- **位置**：自托管运维复杂性
- **问题**：存储、索引、备份等运维成本的深度分析不够充分
- **建议**：增加自托管环境下存储容量规划、索引优化、备份策略的实战经验分享