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

---

## [Task9 Deep Review] 15.1 Android 性能优化研究方法论 — 2026-07-03
- **类型**：源码准确性/版本差异
- **位置**：自适应刷新率场景的帧数据分析段
- **问题**：FrameRateOverrides API 说明中缺少 Android 17 中 VSync 偏移动态调整的具体实现机制，只提到 VSync offset 会随帧率变化而调整，未说明具体的调整算法和边界条件
- **建议**：补充 SurfaceFlinger 中 VSync offset 调整的具体实现逻辑，包括 `Scheduler/MessageQueue.cpp` 中的分派机制

---

## [Task9 Deep Review] 13.21 Perfetto 版本演进与 Android 9-17 新特性验证 — 2026-07-03
- **类型**：源码准确性/CLI 参数错误
- **位置**：性能优化与最佳实践 — 大型追踪文件处理
- **问题**：章节提到 perfetto CLI 支持 --buffer-size、--duration-seconds 等参数，但这些不是标准 CLI 参数。实际 buffer size 通过 config protobuf 字段配置，duration 通过 duration_ms 配置
- **建议**：修正 CLI 参数描述，移除非标准参数，改为正确的 config 文件配置方式

---

## [Task9 Deep Review] 21.2 启动框架设计与任务编排 — 2026-07-03
- **类型**：原理链断裂
- **位置**：线程池优先级策略段
- **问题**：章节提到设置 IO 线程优先级为 THREAD_PRIORITY_BACKGROUND，但未解释该优先级与系统整体调度的交互关系，包括其如何影响 CPU 分配和与前台任务的竞争
- **建议**：补充 THREAD_PRIORITY_BACKGROUND 的作用机制说明，包括 Linux 调度器对其的处理方式和与其他线程优先级的交互关系

---

## [Task9 Deep Review] 15.1 Android 性能优化研究方法论 — 2026-07-03
- **类型**：知识盲区/AI 时代缺失
- **位置**：性能优化方法体系段
- **问题**：章节未覆盖 AI 时代性能优化的新方法，如大模型推理优化、LLM 推理的性能特点和优化策略
- **建议**：增加 AI 相关性能优化内容的简要说明，包括大模型推理的延迟优化和资源调度策略

---

## [Task9 Deep Review] 13.21 Perfetto 版本演进与 Android 9-17 新特性验证 — 2026-07-03
- **类型**：知识盲区/隐私控制
- **位置**：企业级部署考量段
- **问题**：章节未覆盖 Android 17 中 Perfetto 的隐私控制新特性，如数据脱敏、权限控制等企业级安全需求
- **建议**：补充 Android 17 中 Perfetto 的隐私控制功能，包括数据源级隐私配置和敏感信息过滤机制

---

## [Task9 Deep Review] 21.2 启动框架设计与任务编排 — 2026-07-03
- **类型**：数据缺失/性能对比
- **位置**：三种线程池的分工段
- **问题**：章节中的线程池配置参数缺少实际性能对比数据，无法验证配置参数的合理性
- **建议**：添加线程池配置的性能对比数据，包括不同配置下的任务吞吐量和延迟测试结果

---

## [Task9 Deep Review] 13.21 Perfetto 版本演进与 Android 9-17 新特性验证 — 2026-07-03
- **类型**：锦上添花/案例补充
- **位置**：企业级部署考量段
- **问题**：章节的企业级部署部分内容偏泛化，缺少具体的实际部署案例
- **建议**：增加 1-2 个企业级 Perfetto 部署的具体案例，包括配置文件示例和实际效果数据

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


---

## [Task2A Gap Mining] 已检查方向 — 2026-07-03 23:19

**本轮结果：未发现评分 ≥ 14 的知识缺口**

已检查方向（避免下轮重复）：
1. source-index.json 高质量未映射素材 → 索引为空（0 条目）
2. research-feeds 最近 10 个文件 → Perfetto v54、Compose Pausable、ADPF、AudioFlinger、Camera HAL3 等均已映射到现有章节
3. daily-info 最近 3 天 → Android 17 DeliQueue、桌面模式、Android Bench 等均已覆盖
4. AOSP 系统服务覆盖 → NotificationManager、ConnectivityManager、TelephonyManager、PowerManager、WindowManager、ActivityManager 均有专门章节（ch08-*）
5. 官方文档方向 → 无法 fetch（DNS 限制），但已通过 daily-info 间接覆盖
6. Compose LazyGrid → 已在 §22.22 中有专门小节（7 处提及，含 span/itemPool/crossAxis 测量分析）
7. heapprofd 生产部署 → 已在 §13.21 中有增补小节（26 文件提及，含双 producer 模型、生产配置）
8. Clippings 三本参考书 → 稳定性 15 篇对应 ch20、性能优化 16 篇对应 ch21-25、线上疑难 59 篇对应 ch26（仅含目录元数据）
9. 形式因子 → Wear OS/Auto/TV/XR/Foldable/Desktop 均有覆盖
10. CPU 缓存友好性 → §5.18 专章覆盖（cache line/false sharing/data layout）
11. 50+ 关键词全文搜索 → 所有核心主题均有 ≥3 处提及
12. 知识盲区 intake/research-gaps.md → 仅 2 条（heapprofd 部署、多进程启动框架），前者已部分覆盖，后者偏理论

**全书规模**：589 个小节（finalized 340 / ready-for-review 195 / draft 33 / deprecated 6）
**成熟度评估**：核心性能领域（启动/渲染/内存/功耗/工具/稳定性/可观测性）覆盖密度已接近饱和。

下次建议探索方向：
- Clippings「线上疑难问题」59 篇的实际内容（需重新 clip 获取正文，非仅目录）
- Android 17 Final SDK 行为变更文档（如 CT 默认启用、BAL IntentSender 扩展的实际性能影响）
- GenAI/Agent 应用层性能模式（GUI 代理 benchmark、模型加载/inference 性能基线）
