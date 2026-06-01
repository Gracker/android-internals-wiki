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

## [Task6 Review] 2.10 GPU 渲染深入 — 2026-06-01
- **类型**：需补充素材
- **位置**：实战案例 / 一手 AGI 与 Perfetto Trace 证据 / 效果验证
- **问题**：章节仍以占位图、示例命令和自称保存 Trace 来支撑具体性能数据，缺少可复核的 trace 文件、截图、测试条件或样本说明；同一社交应用案例在多个小节重复叙述。
- **建议**：补配真实 Perfetto/AGI 截图或 trace artifact，并写清设备、场景、采样方式；若没有一手证据，应改为示例场景并合并重复段落。
- **review 日志**：logs/review/2026-06-01-16-review.md

## [Task6 Review] 3.5 输入事件拦截与安全机制 — 2026-06-01
- **类型**：需确认
- **位置**：厂商定制的拦截增强方案 / 扩展：厂商游戏模式输入优先级机制（源码级验证）
- **问题**：正文先列出“事件优先队列”“提升触摸事件分发优先级”等厂商实现，后文源码验证又说明 AOSP 标准 GameMode 不包含独立输入优先级提升机制，AOSP 结论、厂商推测和已验证事实边界不够清楚。
- **建议**：Task2B 将厂商定制内容改成明确的非 AOSP 边界说明；无公开材料的实现项删除或标为待证；把源码验证附录整合回正文相应位置。
- **review 日志**：logs/review/2026-06-01-16-review.md

## [Task6 Review] 5.14 Android 17 ML Runtime 与 NPU 访问边界 — 2026-06-01
- **类型**：需重写
- **位置**：小结之后的“源码调研补充”块
- **问题**：发布稿在小结后保留多段原始调研补充，包含推测位置、需进一步确认、未一手验证等编辑态内容，破坏正文收束和可发布性。
- **建议**：将已验证事实整合回对应正文小节；未验证项移入参考/待验证清单或交 Task9 复核。
- **review 日志**：logs/review/2026-06-01-18-review.md

- **类型**：需确认
- **位置**：NNAPI HAL 版本演进口径
- **问题**：正文与补充材料同时出现 HIDL 1.3、Android 12+ AIDL、API 35/37 等口径，读者难以判断 Android 17 范围内的准确结论。
- **建议**：由 Task9 复核 Android 17 / API 37 内可发布口径，再由 Task2B 统一正文和表格。
- **review 日志**：logs/review/2026-06-01-18-review.md


## [Task6 Review] 18.13 WebView 渲染管线 — 2026-06-01
- **类型**：需补充素材
- **位置**：“实际性能数据对比”表格
- **问题**：表格声称 Pixel 8 Pro、Android 17、WebView provider milestone 123 的实测数据，但缺少 trace、样本、日志或验证记录路径。
- **建议**：补齐可复查数据来源；无法补齐时改为待验证案例或删除具体数值。
- **review 日志**：logs/review/2026-06-01-18-review.md

- **类型**：需确认
- **位置**：“Android 15-17 WebView provider 更新差异”
- **问题**：“Android 17 全量支持”“Overlay/Fence 优化”等属于版本差异判断，当前没有 Chromium milestone、AOSP/Chromium commit 或 external-review 证据。
- **建议**：交 Task9 复核版本边界；Task2B 按可验证证据改写为保守判断。
- **review 日志**：logs/review/2026-06-01-18-review.md
- **类型**：需确认
- **位置**：“实际排查要点”Kotlin 示例
- **问题**：示例使用 `Display.Hardware()`、`display.getHardware()`、`hardware.overlaySupport` 判断 overlay 能力，需确认这些是否为 Android 17 公开 API 或内部/伪代码。
- **建议**：Task9 核对 API 真实性；若不是公开 API，Task2B 改为 `dumpsys SurfaceFlinger`、Perfetto 或明确标注伪代码。
- **review 日志**：logs/review/2026-06-01-18-review.md


## [Task9 Deep Review] 2.1 Android 渲染架构全景 — 2026-06-02
- **类型**：数据缺失
- **位置**：三缓冲机制与 FrameTimeline 验证段
- **问题**：三缓冲的帧率平滑和端到端延迟代价已经有正确边界，但缺少一份真实 FrameTimeline / BufferQueue trace 样例来支撑判断。
- **建议**：补一个 60Hz/120Hz 场景的 Perfetto 示例，对比 expected_present_time、actual_present_time、dequeueBuffer 等待和 release fence 返回时机。

## [Task9 Deep Review] 2.5 MainThread 与 RenderThread 协作 — 2026-06-02
- **类型**：数据缺失
- **位置**：Bitmap 纹理上传量化描述
- **问题**：1080p RGBA upload 约 4-8ms、4K 可达 20ms+ 这组数字缺少设备、GPU、内存带宽、解码格式和测试方法限定。
- **建议**：补充同设备 microbenchmark 或 Perfetto trace，标注 bitmap 尺寸、Config、是否 hardware bitmap、是否调用 prepareToDraw() 以及 Upload Texture slice 的实际耗时。
