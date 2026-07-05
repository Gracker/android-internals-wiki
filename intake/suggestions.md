[Task9 Deep Review] 2.11 Flutter 渲染管线与性能 — 2026-07-05
- **类型**: 源码准确性
- **位置**: ADPF 性能提示支持描述
- **问题**: 内容提到 Flutter Engine 主干未检索到 PerformanceHint 相关符号，Issue #155097 关闭为 not_planned。但根据 Flutter 3.44 最新源码，已有 AChoreographerPerformanceHint 相关实现证据，需要更新结论以反映 2026 年现状。
- **建议**: 补充说明 Flutter Engine 对 Android PerformanceHint Manager 的最新支持状态，明确当前是否已实现自动启用 ADPF HintSession，或仍需要手动配置。
## [Task9 Deep Review] 14.1 Android Studio Profiler — 2026-07-05
- **类型**: 源码准确性
- **位置**: JVMTI agent 实现路径
- **问题**: tools/base/profiler/native/perfa/perfa.cc 和 memory/memory_tracking_env.cc 的 JVMTI 事件回调注册路径需确认是否在 android-17.0.0_r1 中仍适用
- **建议**: 需要核实 AOSP android-17.0.0_r1 分支中相关源码路径的准确性，确认是否有重构或路径变更

## [Task9 Deep Review] 14.1 Android Studio Profiler — 2026-07-05
- **类型**: 源码准确性
- **位置**: SupportLevel.kt 配置限制
- **问题**: SupportLevel.kt 中 PROFILEABLE 配置的 except 列表（39-46行）需确认在 Android 17 中是否仍有此限制
- **建议**: 需要确认在 android-17.0.0_r1 中 SupportLevel.kt 的 PROFILEABLE 配置是否有变更，except 列表是否仍然适用

## [Task9 Deep Review] 14.1 Android Studio Profiler — 2026-07-05
- **类型**: 版本差异
- **位置**: Java Method Trace 限制说明
- **问题**: 章节标注的适用版本为 Android 8.0 (API 26) - Android 17 (API 37)，但未明确说明 Java Method Trace 在 Profileable App 中的限制是否在后续版本中有所变化
- **建议**: 需要补充说明 Java Method Trace 在 Profileable App 中的限制在不同 Android 版本中的变化情况

### [2026-07-05 12:05] Task2A Round 24 Gap Mining — No Candidates
已检查方向（本轮新增）：
- SDK Sandboxed UID/进程隔离内存管理（2026-07-05 DeepResearch 新增）→ 映射到 §20.3/ch04，非新章节
- queue.json 仅 1 条目（§2.15, priority=60），非新章节候选
- Clippings 无新增文件（7+ 天）
- 24 轮连续无合格候选，覆盖率饱和

### [2026-07-05 13:04] Task2A Round 25 Gap Mining — No Candidates
已检查方向（本轮新增）：
- Ch23 内存实战：23.14「内存压力分级响应」→ 已由 04.18（onTrimMemory 源码+实战策略）+ 23.7（内存监控与线上治理）+ 23.9（App Memory Limits）+ 23.10（Memory Advice API）多角度覆盖
- Ch21 启动：21.17「模块化启动框架与依赖图」→ 已由 21.2（启动框架设计与任务编排，820 行，含 DAG/App Startup/Alpha/多进程/微服务）+ 21.7（多进程启动优化）充分覆盖
- Ch21 启动：21.17「Startup Insights API」→ 已由 26.13（ApplicationStartInfo 与启动归因上报）覆盖
- Ch27 CPU：27.2「任务调度优先级与 CPU 核心绑定」→ 已由 27.1（附录含 Process.setThreadPriority/CPUSET/SCHED 双通道分析）+ 21.16（线程池与并发调度性能）覆盖
- Ch22 渲染：22.30「Compose 性能基准测试」→ Macrobenchmark 在 8.7/ch14 已有方法论文档，Compose 性能在 22.3/22.15/22.21/22.22/22.27/22.29 多节覆盖
- Ch24 I/O：24.21「DataStore 异步存储迁移实战」→ 已由 Part1 6.1（DataStore IPC 源码验证）+ 6.2/6.4（SharedPreferences ANR 与迁移）覆盖
- Ch20 稳定性：20.19「FD 泄漏与线程治理」→ 已由 20.14（线程与 FD 资源监控治理，finalized）覆盖
- Ch26 可观测性：26.24「ProfilingManager 生产级实践」→ 已由 26.12（版本化线上诊断能力）覆盖
- DeepResearch 新增文件（59 篇近 7 天）：SoC 电池/PMS cpuidle/Flutter Impeller/Binder 4MB/heapprofd 均已在 source-index.json 跟踪；AI Agent 内存沙箱评分 13 分（素材不足）；Perfetto v57 AI tracks 评分 15 但 13.21 已有 v54 大篇幅覆盖，增量不足
- Clippings 无新增文件（7+ 天）
- 25 轮连续无合格候选，覆盖率饱和

### [2026-07-05 14:08] Task2A Round 26 Gap Mining — No Candidates
已检查方向（本轮新增）：
- 无新增 DeepResearch 文件 since Round 24（所有 2026-07-05 DeepResearch 已在 Round 22-24 评估完毕）
- 无新增 Clippings 文件（7+ 天无变化）
- 无新增 research-feeds（最新 mtime: 2026-03-29）
- Source index: 0 unmapped high-quality items
- 14 draft sections all have >15 lines content（无空 draft）
- 5 个 2026-07-05 DeepResearch 文件均映射到已有章节（binder-sz4m→§1.25/1.30/1.53, battery→ch05/ch25, perfetto-v57→§13.23, audio-hardening→ch25.17, ai-agent-memory→§20.3/ch04）
- Task2B backlog: 0（≤20，允许挖掘）
- 26 轮连续无合格候选，覆盖率饱和

### [2026-07-05 15:12] Task2A Round 26 Gap Mining — No Candidates
已检查方向（本轮新增）：
- App Links / Deep Links resolution 性能 → 评分 11/20（素材 2, 相关性 3, 读者需求 3, 时效性 3），低于阈值
- Activity Embedding / 大屏多窗口性能 → 22.14 已覆盖桌面窗口化渲染，ActivityEmbedding 更偏 UI/UX
- Notification Trampoline 限制迁移 → 非性能优化主题，是兼容性行为变更
- BroadcastReceiver 动态注册性能 → 仅 1 篇素材，评分 9/20
- ClipboardService / 剪贴板访问延迟 → 非核心性能瓶颈，评分 8/20
- Backup/Restore 性能影响 → 系统级调度，App 层不可控，评分 8/20
- Runtime Permission 检查 IPC 开销 → 单次调用 <1ms，评分 8/20
- Data Binding vs View Binding vs Compose 迁移性能 → 评分 11/20（衰落技术，时效性低）
- TransitionManager / Transition API 性能 → SharedElement 已有 1 篇覆盖
- Lint 自定义性能规则 → 工具类话题，评分 8/20
- Storage Access Framework (SAF) 性能 → 已有 3 篇文件涉及
- Room Auto Migration 性能 → 已有 1 篇覆盖
- ExoPlayer / Media3 性能 → 已有 1 篇覆盖
- MediaCodec 硬件编解码性能 → 已有 3 篇覆盖
- ViewPager2 性能 → 已有 3 篇覆盖
- ProGuard / R8 full mode → 已有 5 篇覆盖
- ConfigStore / WallpaperColors / Compose Multipreview → 非性能主题或过于边缘
- Companion Device Manager presence → 极小众场景，评分 7/20
- Screen Recorder / MediaProjection 性能 → 细分场景，评分 9/20
- 线上疑难问题参考书 59 篇全量映射 → 所有主题均已有对应章节
- Android 性能优化参考书 16 篇全量映射 → 所有主题均已有对应章节
- 26 轮连续挖掘（24+25+26 轮无合格候选），覆盖率确认饱和

## [Task9 Idle Audit] 1.5 线程模型 — 2026-07-05
- **类型**：版本差异
- **位置**：章节适用版本声明与源码引用不一致
- **问题**：章节声明适用 Android 5.0 - Android 17 (API 21-37)，但所有源码引用和分析均基于 android-16.0.0_r1（Android 16，API 35）。存在版本覆盖声明与实际分析基准版本不匹配的问题。
- **建议**：① 修正章节适用版本范围至 Android 5.0 - Android 16（API 21-35），或② 将源码引用更新为 android-17.0.0_r1 并补充 Android 17 行为差异分析。建议优先选择方案①，因为当前源码分析深度与 Android 16 更匹配。

### [2026-07-05 16:05] Task2A Round 27 Gap Mining — No Candidates
已检查方向（本轮新增）：
- 无新增 DeepResearch 文件（自 Round 24 起无变化）
- 无新增 Clippings 文件（自 2026-06-23 起无变化，12 天）
- 无新增 research-feeds（最新 mtime: 2026-04-14，近 3 个月无更新）
- Source index: 0 unmapped high-quality items
- 14 draft sections all have >15 lines content（无空 draft，本轮无法进入 Phase 2）
- Task2B backlog: 0（≤20，允许挖掘）
- queue.json 6 条 pending 均为素材注入（非新章节创建）
- 27 轮连续无合格候选，覆盖率确认饱和
- 全书 577 小节：finalized 342 + ready-for-review 197 + draft 19 + 其他 19
- 本轮无新增可挖掘方向，所有信息源自 Round 24-26 已穷尽


### [2026-07-05 18:04] Task2A Round 28 Gap Mining — No Candidates
已检查方向（本轮新增）：
- 新增 DeepResearch 文件（自 Round 27 后）：
  - `2026-07-05-android17-startup-insights-application-start-info.md`（18KB）→ ApplicationStartInfo 已由 §26.13（finalized）+ §21.2（finalized）覆盖，评分 10/20
  - `2026-07-05-android17-art-heaptask-system-7-subclasses-source-closed-loop.md`（22KB）→ 映射到 §4.21（draft，23 行），非新章节
- btrace 3.0 专项评估：§19.04 已 finalized，`last_verified_against: "bytedance/btrace v3.0.0/v3.1.0"`，60KB+35KB DeepResearch 素材是对已有章节的补充验证，非新缺口
- 字节跳动全栈调研（34KB）：行业概览文档，工具层（btrace/bhook/ShadowHook/ByteX）+ 平台层（Slardar/APMPlus）均有对应章节覆盖
- 从 NNAPI 到 LiteRT（37KB）：§5.11（端侧 AI 推理）+ §5.14（Android 17 ML Runtime）已覆盖
- 荣耀 MUSCHED 调研（25KB）：§17.8（MUSCHED 调度实践）已 ready-for-review
- 无新增 Clippings 文件（12+ 天无变化）
- Source index: 0 unmapped high-quality items
- 14 draft sections all have >15 lines content（无空 draft）
- Task2B backlog: 0（≤20，允许挖掘）
- 28 轮连续无合格候选，覆盖率确认饱和
- 全书进度：578 小节，finalized 342 + ready-for-review 197 + draft 20 + 其他 19


## [Task9 Deep Review] 14.8 GPU 图形调试与分析工具 — 2026-07-05
- **类型**：知识盲区 / 数据支撑
- **位置**：Perfetto GPU 分析能力 §
- **问题**：未提及 Perfetto 的 `vulkan.memory_tracker` 数据源。该数据源可追踪 GPU 内存分配/释放/映射，对诊断 GPU 内存泄漏和显存压力有价值。
- **建议**：在"Perfetto 中的 GPU 分析能力"章节补充 `vulkan.memory_tracker` 简介，与 gpu.counters / gpu.renderstages 并列。

## [Task9 Deep Review] 14.8 GPU 图形调试与分析工具 — 2026-07-05
- **类型**：知识盲区
- **位置**：Sokatoa § / 厂商专用工具 §
- **问题**：Samsung Xclipse GPU（AMD RDNA 架构）仅作为 Sokatoa 支持平台提及，缺少 Samsung 自身的 Xclipse profiling 工具/方法的说明。
- **建议**：补充 Xclipse profiling 工具的可用性和限制，或在"厂商专用工具"中注明 Samsung 当前依赖 Sokatoa 而无独立工具。

## [Task9 Deep Review] 14.8 GPU 图形调试与分析工具 — 2026-07-05
- **类型**：数据支撑
- **位置**：GPU 性能分析的核心指标 → Draw Call 数量 §
- **问题**：Draw Call 阈值（UI < 100、2D < 500、3D > 2000）未标注来源且高度依赖 GPU 架构。Mali TBDR 和 Adreno IMR 的 Draw Call 开销差异显著。
- **建议**：标注为参考范围，注明"因 GPU 架构而异，Mali TBDR 对 Draw Call 数量更敏感"或类似限定。

## [Task9 Deep Review] 14.8 GPU 图形调试与分析工具 — 2026-07-05
- **类型**：版本差异
- **位置**：AGI 2025-2026 演进 §
- **问题**：2026-04-05 研究素材将 GFXReconstruct Frame Profiler Alpha 归入 AGI H2 2026 路线图，但 APA（2026-05-19 发布）后章节将其归入 APA 后续路线图。两者的过渡关系未明确说明，措辞与 AGI 自身路线图存在张力。
- **建议**：补充一句说明 GFXReconstruct frame profiling 的归属变动，或标注"原 AGI 路线图中的 GFXReconstruct Frame Profiler Alpha 计划在 APA 发布后可能已整合至 APA 产品线"。

## [Task9 Deep Review] 14.8 GPU 图形调试与分析工具 — 2026-07-05
- **类型**：原理链
- **位置**：关键 GPU 指标 → GPU Utilization §
- **问题**：首次引入"GPU Utilization"时说"100% 意味着 GPU 在满负荷运行"，但后文"不同设备的 GPU 计数器差异"节指出同一计数器在 Adreno 和 Mali 上含义不同。首次引入时缺少限定。
- **建议**：在首次定义 Utilization 时加一句"不同厂商 GPU 的 Utilization 计算方式不完全相同，后文有详细说明"的前向引用。
