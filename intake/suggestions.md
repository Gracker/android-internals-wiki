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
## [Task2A Gap Mining] 知识缺口挖掘方向记录 — 2026-07-03 20:11
- **轮次结果**：未发现评分 ≥ 14 的知识缺口
- **已检查方向**：
  1. AOSP `frameworks/base/services/` 核心服务覆盖（AMS/WMS/PMS/PowerManagerService/NotificationManagerService/AlarmManagerService/InputManagerService/DisplayManagerService/SensorService/AudioService/ConnectivityService/TelephonyManager/LocationManagerService/StorageManagerService/MediaSession）— 全部已有对应章节
  2. AOSP `system/` 核心组件（lmkd/vold/netd/installd/statsd）— 全部已覆盖
  3. AOSP `packages/modules/` 模块（Wifi/Bluetooth/Media/Connectivity）— 全部已覆盖
  4. Clippings 三本参考书章节交叉比对（稳定性 25 篇 / 性能优化 16 篇 / 线上疑难 58+ 篇）— 核心知识点全部映射
  5. Android 17 新特性（Certificate Transparency / Bubbles / Handoff / UWB / OTP SMS / ACCESS_LOCAL_NETWORK / Safer DCL / ICU 78 / NPU / Desktop Experience / Compose 1.10 Pausable）— 除 ICU 78（非性能话题）外全部有覆盖
  6. 研究素材（8 篇 research-feeds：Perfetto v53/v54 / Compose Pausable / ADPF / View hierarchy / AudioTrack / Frame Timeline）— 全部已映射
  7. 每日信息（最近 3 天 daily-info）— 热点话题（DeliQueue / 桌面模式 / MessageQueue 重写 / 协程性能 / AI 编程基准）均有对应章节
  8. 现有章节 🔸 扩展锚点深挖 — 未发现素材丰富到足以独立成节的扩展点
  9. Compose Snapshot 状态系统 — 已在 22.20/22.28/22.29 中覆盖
  10. AlarmManager / NotificationManagerService 性能 — 已在 5.23/8.14 等章节中覆盖
- **全书状态**：577 总节 / 340 finalized / 194 ready-for-review / 36 draft
- **建议**：后续精力宜聚焦于加工 36 个 draft 章节（多个已有实质内容）和 review 194 个 ready-for-review 章节，而非继续新增章节


## [Task6 Review round5] 13.21 Perfetto 版本演进 — 2026-07-03

### 问题 1：FrameTimeline 通用内容填充
- **类型**：需重写
- **位置**：🔹 FrameTimeline 集成 — UI 线程性能瓶颈典型场景 + 分析方法列表
- **问题**：FrameTimeline 集成小节末尾的「UI 线程性能瓶颈典型场景」（过度绘制、过度布局、阻塞操作、动画卡顿）和「分析方法」（时间线分析、资源使用分析、依赖关系分析、热路径识别）是通用 Android 性能知识，与 FrameTimeline 在 Perfetto 中的集成机制无关
- **建议**：删除通用列表，替换为 FrameTimeline 在 trace_processor 中的 SQL 查询示例、帧匹配逻辑说明或实际追踪场景

### 问题 2：perfetto CLI 参数疑似非标准
- **类型**：需确认（技术准确性）
- **位置**：🔸 性能优化与最佳实践 — CLI 命令示例
- **问题**：`--buffer-size=256M`、`--compression=zstd`、`--duration-seconds=300` 疑似不是标准 perfetto CLI 参数。这些参数通常在 config protobuf 中设置
- **建议**：验证 perfetto CLI 支持的 flag；如不支持，改为使用 config 文件的正确示例

### 问题 3：Systrace 迁移示例 buffer 映射差异
- **类型**：需确认（技术准确性）
- **位置**：🔸 与 Systrace 的对比 — 迁移示例
- **问题**：`systrace -b 128`（128KB）映射到 `size_kb: 131072`（128MB），存在约 1000 倍差异
- **建议**：确认 systrace -b 单位，修正等效配置值

### 非阻塞性备注（不进入 queue）
- 🔸 企业级部署考量小节仍然偏泛（MDM/RBAC/边缘-集中-混合模式），缺少 Perfetto 特有部署细节。此前 round4 已标注为 non-blocking，维持判断
- review 日志：logs/review/2026-07-03-20-review.md
