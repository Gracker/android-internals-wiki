## [Task9 Deep Review] 15.5 线上性能监控 — 2026-07-06
- **类型**：版本差异
- **位置**：ProfilingManager 和 ProfilingTrigger 版本边界描述
- **问题**：章节中提到的 API 版本引入时间与实际 AOSP android-17.0.0_r1 源码存在差异。ProfilingManager 在 Android 14 (API 34) 已引入，章节误标为 Android 15 (API 35)；ProfilingTrigger 在 android-16.0.0_r1 中已存在，章节误标为 Android 16 (API 36) 才加入。
- **建议**：修正 API 版本边界，补充准确的版本信息：ProfilingManager 实际从 Android 14 (API 34) 开始可用；ProfilingTrigger 在 Android 16 (API 35) 引入，并提供具体的源码路径验证。

---

## [Task9 Idle Audit] 15 Android 性能优化研究方法论 — 2026-07-06
- **类型**：源码准确性
- **位置**：第3.4节 VSync 组件描述
- **问题**：VSyncTracker 描述过于简化，实际涉及多组件协作
- **建议**：补充 VSyncTracker、VSyncModulator、VSyncDispatch 的协作关系说明，与实际 AOSP 实现保持一致

## [Task2B 回炉修复] 20.9 稳定性治理案例集 — 2026-07-06 12:50

来源：frontmatter backlog fallback（task9_result: needs-rework → 2026-07-06 deep-review）

修复内容（P1 3 项 / P2 4 项）：
- P1-1: 扩充 Android 17 信号处理机制（async-signal-safe 校验细则、线程亲和性信号分发、动态 altstack）
- P1-2: 扩充线程亲和性管理讨论（崩溃监控/信号处理确定性/性能关键路径隔离三大场景 + 注意事项）
- P1-3: 扩充 Android 17 线程监控 API（getThreadCpuTime / getThreadPriority / sched 表格 + 使用场景）
- P2-1: 增强 Android 5.0 vs 17 适用性说明（debuggerd handler 链的具体变化）
- P2-2: 增强 Android 15→17 信号处理演进时间线
- P2-3: OOM 案例补充虚拟内存碎片化分析（smaps/maps 碎片模式 + Perfetto 观察方法）
- P2-4: 补充 Android 12+ THREAD_PRIORITY_* 与 cgroup v2 调度讨论
- 修复 frontmatter 重复 key（task2b_state ×2、pipeline_stage 冲突、task2b_result 重复）

状态：pipeline_stage → task6_pending，task9_result → revisiting，等待 Task6 复审

## [Task9 Deep Review] 14.8 GPU 图形调试与分析工具 — 2026-07-06

[223 more lines in file]

---

## [Task9 Deep Review] 14.11 Battery Historian 与功耗分析工具 — 2026-07-07

### [Task9 Deep Review] 14.11 Battery Historian 与功耗分析工具 — 2026-07-07
- **类型**：源码准确性
- **位置**：API版本映射描述
- **问题**：章节提到"Android 15 (API 35)"将 PowerMonitor API 开放到应用层，但表述方式易混淆。Android 15对应API 35，Android 17对应API 37。这种版本数字描述方式违反了清晰的版本映射规则。
- **建议**：修正版本映射表述，明确 Android 15 ↔ API 35，Android 17 ↔ API 37 的对应关系，避免版本数字混淆。

### [Task9 Deep Review] 14.11 Battery Historian 与功耗分析工具 — 2026-07-07
- **类型**：源码准确性
- **位置**：PowerMonitorReadings.getConsumedEnergy() 方法描述
- **问题**：章节提到 PowerMonitorReadings.getConsumedEnergy() 方法返回累计能耗，但未在 android-17.0.0_r1 中验证该方法的确切签名和返回类型。API 35 的 PowerMonitor 系列接口在 Android 17 中的支持状态需要确认。
- **建议**：确认 PowerMonitor API 在 Android 17 中的支持状态和 API 签名，如存在则明确标注，如不存在需调整内容描述。

### [Task9 Deep Review] 14.11 Battery Historian 与功耗分析工具 — 2026-07-07
- **类型**：源码准确性
- **位置**：NDK performance_hint.h 路径描述
- **问题**：章节提到 NDK performance_hint.h 在 r28+ 重组，但未说明完整路径变更细节和 API 签名变化。开发者无法确定具体的文件位置和兼容性要求。
- **建议**：补充 NDK performance_hint.h 在 Android 17 中的完整路径变更说明和 API 签名兼容性信息。

### [Task9 Deep Review] 14.11 Battery Historian 与功耗分析工具 — 2026-07-07
- **类型**：原理链完整性
- **位置**：ADPF PowerMonitor 协作方案
- **问题**：章节提到"PowerMonitor 采样 → 分析能耗特征 → 判断是否启用 power efficiency mode"的协作方案，但缺少了关键的技术细节：如何从 PowerMonitor 的累计能耗数据推导出具体的能耗特征，以及判断逻辑的具体实现机制。
- **建议**：补充从 PowerMonitor 累计能耗数据推导具体能耗特征的技术细节，以及判断逻辑的具体实现机制，完善原理链。

### [Task9 Deep Review] 14.11 Battery Historian 与功耗分析工具 — 2026-07-07
- **类型**：版本差异覆盖
- **位置**：Android 17功耗隐私保护机制
- **问题**：章节仅在源码调研部分提到Android 17的功耗隐私保护机制，但未在正文中充分说明这些机制对普通应用的限制影响。普通应用最大20秒数据延迟，250ms粒度需要系统权限，这对功耗分析的准确性有重要影响。
- **建议**：在正文中补充Android 17功耗隐私保护机制对普通应用的限制说明，包括数据粒度差异和权限要求。

### [Task2B 回炉修复完成] 14.11 Battery Historian — 2026-07-07 02:53
- **状态**：已修复
- **处理内容**：P0 路径矛盾 1 处 + P1 重要缺失 5 处 + P2 建议改进 5 处
- **详情**：见 `OpenClaw定时任务/知识加工/2026-07-07-02-知识加工(回炉).md`
- **下一步**：已退回 pipeline_stage: task6_pending，等待 Task6 → Task9 复审


### [Task2A Round 33] 知识缺口挖掘 — 无合格候选 — 2026-07-07 02:04
- **已检查方向**：
  1. DeepResearch 文件：无新文件（最新 2026-04-14，均已映射）
  2. Clippings 参考书：无新增（7+ 天无变化）
  3. Daily-info 2026-07-06：已消费，所有主题（Android 17 调度器→§1.44/§4.35、Linux 6.10 内存碎片→§4.36/§6.19、Compose 性能→已有覆盖、架构模式→超出范围）均已映射
  4. Source-index：0 个未映射高质量素材
  5. Research-gaps：全部指向现有章节（§14.11/§14.8）的补充
  6. Suggestions：全部为 Task9 深度审核对现有章节的修改建议
- **结论**：覆盖饱和（第 33 次连续），未发现 ≥14 分新缺口

### [Task2A Round 34] 知识缺口挖掘 — 无合格候选 — 2026-07-07 04:12
- **已检查方向**：
  1. Source-index：0 个未映射高质量素材
  2. Research-feeds（2026-04-08~14）：5 个文件已全部映射
  3. Daily-info 2026-07-04~07：已消费，主题均已有对应章节
  4. AOSP 源码结构：frameworks/base 核心服务、system/ 核心组件均已覆盖
  5. Android 17 新特性：22 项检查中 17 项已覆盖，5 项未覆盖均 < 14 分（非性能核心）
  6. Clippings 三本参考书：25+16+59 篇知识点全部有对应章节
  7. 深度主题覆盖：30+ 细分主题（缓存/DEX/Native Hook/CPU亲和/线程优先级/MMKV/Doze/等）全部有覆盖
- **候选总数**：~80 个，均 < 14 分
- **结论**：覆盖饱和（第 34 次连续），未发现 ≥14 分新缺口
- **建议**：转向推动 26 个 draft 章节提升质量 + 211 个 ready-for-review 转化



## [Task9 Deep Review] 2026-07-07 14.11 Battery Historian 与功耗分析工具 — 建议改进

**类型**: 知识盲区
**位置**: 多种优化场景
**问题**: 缺少功耗分析的硬件测量方案、Perfetto 与 Battery Historian 数据关联、多设备功耗数据对比方法、功耗分析在 CI/CD 中的集成
**建议**: 
1. 补充硬件功耗测量方案：Monsoon Power Monitor、华为功耗仪等高精度测量设备的适用场景和限制
2. 说明如何将 Perfetto 的 power_rails 数据与 Battery Historian 的 batterystats 进行交叉验证
3. 提供不同设备（Pixel、Samsung、小米等）功耗数据的对比方法和注意事项
4. 添加功耗分析在 CI/CD 流水线中的集成方案和自动化检测示例

## [Task9 Deep Review] 2026-07-07 18.18 PIP 与自由窗口渲染 — 建议改进

**类型**: 知识盲区
**位置**: 多窗口内存管理
**问题**: 缺少多窗口内存管理策略的详细说明
**建议**: 
1. 补充多窗口场景下的内存管理策略：buffer 重用、内存共享、裁剪优化等
2. 说明 SurfaceFlinger 如何管理多窗口的内存占用和释放策略
3. 提供内存优化的具体实践方法和监控指标

## [Task9 Deep Review] 2026-07-07 14.11 Battery Historian 与功耗分析工具 — 建议改进

**类型**: 数据缺失
**位置**: 功耗分析在 CI/CD 中的集成
**问题**: 缺少功耗分析在 CI/CD 中的集成方案和具体实现
**建议**: 
1. 提供使用 Macrobenchmark PowerMetric 进行自动化功耗测试的完整配置示例
2. 说明如何将功耗数据集成到持续集成流水线中
3. 给出功耗回归检测的阈值设定方法和失败处理机制

## [Task9 Deep Review] 2026-07-07 18.18 PIP 与自由窗口渲染 — 建议改进

**类型**: 数据缺失
**位置**: Freeform resize 异常 Trace
**问题**: 缺少 Freeform resize 异常情况的实际 Trace 对照截图
**建议**: 
1. 添加包含正常和异常情况的 Perfetto Trace 对照截图
2. 标注关键时间点和性能指标差异
3. 提供异常情况的识别和排查方法
