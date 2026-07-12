## [Task9 Deep Review] 14.1 Android Studio Profiler — 2026-07-13

### [P2] Android Studio Meerkat 采样引擎改进描述
- **类型**：数据缺失
- **位置**："调用栈采样"章节末段
- **问题**："在 Android Studio Meerkat (2024.3) 及后续版本中，Google 持续改进采样引擎的准确性，降低 debug 分析时的误报率" 表述过于模糊
- **建议**：补充具体的改进内容，如 commit ID、changelog 内容或具体的优化指标，或引用官方文档中的具体改进说明

### [P2] Native 内存泄漏检测细节
- **类型**：知识盲区
- **位置**："Memory Profiler：从实时曲线到堆快照"章节 Native 内存泄漏相关段落
- **问题**：提到"Native 内存泄漏需要使用 Native 分配追踪或者 heapprofd 来排查"，但缺乏具体使用细节
- **建议**：补充 heapprofd 的具体使用方法、与 Perfetto heapprofd 的对比、以及不同 Android 版本下的兼容性说明

---

## Previous Suggestions (existing content)
## [Task9 Deep Review] 16.8 AppFlow：GB 级应用冷启动内存联合调度 — 2026-07-11
- **类型**：源码准确性
- **位置**：LMKD_PROCS_PRIO 协议描述章节
- **问题**：章节称 LMK_PROCS_PRIO 为"批量异步处理"，但 AOSP 17 主线实际为同步串行实现，单批上限3个进程
- **建议**：修正描述为"批量同步处理"，明确单次最多调整3个进程的限制，避免误导架构设计决策

## [Task9 Deep Review] 16.8 AppFlow：GB 级应用冷启动内存联合调度 — 2026-07-11
- **类型**：版本差异
- **位置**：Android 17 与论文实验平台对比章节
- **问题**：未充分说明 AppFlow 论文基于 Android 15 实验平台，而本节分析针对 Android 17，可能造成读者误认论文结果直接适用
- **建议**：增加版本差异说明段落，明确 PSI 阈值、MGLRU 状态机、kill_heaviest_task 等关键组件在 Android 17 的变化

## [Task14 参考书扫描] ch25.7 R8 与资源优化 — 2026-07-12
- **类型**：内容补充
- **来源**：[结构参考: Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 29.md]
- **建议补充**：ProGuard 完整处理流水线（shrink→optimize→obfuscate→preverify 四阶段），以及 ProGuard→d8→R8 的演进历史。现有 ch25.7 聚焦 R8 full mode，缺少 ProGuard 时代遗留项目的迁移路径和 d8 作为中间过渡的技术决策点
- **参考书覆盖深度**：中等

## [Task14 参考书扫描] ch21 启动优化 — 2026-07-12
- **类型**：内容补充
- **来源**：[结构参考: Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 29.md]
- **建议补充**：ReDex Interdex（类重排/文件重排优化冷启动 page fault）和 Oatmeal（100ms 内生成解释执行 Odex，解决 Assets ClassesN.dex 首次 Odex 耗时）的原理和实战效果。参考书提供了微信 Tinker 团队的实际使用经验
- **参考书覆盖深度**：深入

## [Task14 参考书扫描] ch20.8 崩溃聚合与归因分析 — 2026-07-12
- **类型**：内容补充
- **来源**：[结构参考: Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 3.md]
- **建议补充**：系统崩溃的系统性解决策略（查找原因→尝试规避→Hook 解决），包含 Toast BadTokenException 的 Hook 点定位实例（代理 mTN handler）。现有 ch20.8 侧重聚合算法，缺少系统崩溃 Hook 修复的实操路径
- **参考书覆盖深度**：中等

## [Task14 参考书扫描] ch20.9 稳定性治理案例集 — 2026-07-12
- **类型**：内容补充
- **来源**：[结构参考: Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 3.md]
- **建议补充**：TimeoutException（BinderProxy.finalize() timed out after 10 seconds）的完整解决路径：FinalizerWatchdogDaemon 机制分析→stop() 方法在 Android 6.0 的线程同步问题→替代 Hook 点发现。这是经典的系统崩溃黑科技案例
- **参考书覆盖深度**：深入

## [Task14 参考书扫描] ch26.21 编译期字节码插桩与监控自动化 — 2026-07-12
- **类型**：内容补充
- **来源**：[结构参考: Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 30.md]
- **建议补充**：AspectJ 的全面对比（成熟稳定/使用简单 vs 切入点固定/正则匹配/性能较低），以及 ASM 选择 Visitor 模式的技术决策依据。现有 ch26.21 聚焦 ASM 实战，补充 AspectJ 作为选型对比可增强完整性
- **参考书覆盖深度**：中等

## [Task14 参考书扫描] ch26.21 编译期字节码插桩与监控自动化 — 2026-07-12
- **类型**：内容补充
- **来源**：[结构参考: Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 30.md]
- **建议补充**：Dalvik 字节码直接操作工具生态（ASMDEX、Dexter、Dexmaker、Soot Jimple 三地址码转换），现有 ch26.21 专注 Java 字节码层面的 ASM 操作，补充 Dalvik 字节码层面工具可覆盖逆向/Dex 修改场景
- **参考书覆盖深度**：概述

## [Task14 参考书扫描] ch26.21 编译期字节码插桩与监控自动化 — 2026-07-12
- **类型**：内容补充
- **来源**：[结构参考: Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 30.md]
- **建议补充**：Java 字节码 vs Dalvik 字节码格式差异的系统对比（栈实现 vs 寄存器实现、Class 单独常量池 vs Dex 共享常量池、指令精简优化数据）。现有 ch26.21 可增加一段字节码格式背景知识补充
- **参考书覆盖深度**：中等

## [Task2A Round 80] 已检查方向 — 2026-07-12 09:13
- SensorPrivacyService → 隐私主题（8/20）
- ReDex/Oatmeal → §21.12 已覆盖（12/20）
- ProGuard→R8 → §25.07 补充（9/20）
- 系统崩溃 Hook → §20.09 补充（10/20）
- AOSP 核心服务/模块 → 已覆盖

## [Task9 Deep Review] 16.5 Android 17 (API 37) 性能行为变更与适配方法 — 2026-07-12
- **类型**：版本差异
- **位置**：16KB 页面大小对原生库的影响章节
- **问题**：仅说明受影响库类型，未明确这是逐步推进的特性，不同设备可能处于不同适配阶段
- **建议**：补充说明 16KB 页面大小的设备推出时间线和当前市场覆盖率

## [Task9 Deep Review] 16.5 Android 17 (API 37) 性能行为变更与适配方法 — 2026-07-12
- **类型**：数据缺失
- **位置**：DeliQueue 性能收益章节
- **问题**：声称 5,000x synthetic benchmark 提升但未提供测试方法、工作负载和对比基准，数据可信度存疑
- **建议**：补充 Google 官方博客中 benchmark 方法的具体描述，或标注"此数据来自 Google 内部 benchmark，未经独立复核"

## [Task9 Deep Review] 16.5 Android 17 (API 37) 性能行为变更与适配方法 — 2026-07-12
- **类型**：数据缺失
- **位置**：16KB 页面大小对原生库的影响章节
- **问题**：声称特定库受影响但未提供实际测试案例或复现步骤，缺少数据支撑
- **建议**：补充至少一个实际受影响库的复现案例，或提供官方确认的受影响库列表

## [Task2A Round 69] 已检查方向 — 2026-07-12 18:10
- Contexthub/SensorHub → 7/20 ❌
- Kotlin Metadata → 8/20 ❌
- BPF overhead → 10/20, §14.25 已覆盖
- AOSP 核心服务/模块 → 已覆盖
- 全部输入源已消费，无新缺口


## [Task2A Round 89] 已检查方向 — 2026-07-12 22:11
- MediaMetrics → 6/20 ❌（过于小众，非性能核心）
- NFC performance → 7/20 ❌（边缘话题）
- JobScheduler internals → 10/20 ❌（已有 1414 mentions 覆盖充分）
- Room database → ch26-database 已有章节
- Notification cooldown → UX 特性非性能主题
- Clippings ep40-58 → 概述性内容已有更深入覆盖
- 全部输入源已消费，无新缺口


## [Task2A Round 90] 已检查方向 — 2026-07-12 23:14
- source-index.json: 空（0 items），无新增可映射条目
- research-feeds: 最后 2026-04-14，3 个月无更新
- Clippings: 最后 2026-06-23，19 天无更新
- daily-info 2026-07-12: AppFlow 论文已在 §4.11 覆盖
- MUSCHED Clippings: 已在 §17.08 覆盖
- 线上疑难问题 ep40-58: 教学/概述性内容，已有更深入覆盖
- 全部输入源已消费，无新缺口（连续第 4 轮无合格候选）

### 2026-07-13 Round 93 Gap Mining — 已检查方向
- ✅ DeepResearch `camera-perfetto-latency-decomposition` (2026-07-13): Camera Open Latency / First Frame Latency AOSP 源码级分析 → 映射到已有 §14.9（finalized, 626 行），评分 12/20，**补充建议而非新章节**
  - 建议：§14.9 下次 Task2B 复审时，将 `CameraService::connectHelper` openLatencyMs 度量路径和 `SessionStatsBuilder::incCounter` 直方图（10 bin）补充到 `camera-launch` 锚点
- ✅ Daily-info 2026-07-13: Android 17 scheduler → §1.43 已覆盖；Linux 6.10 BPF → §6.19/§14.31 已覆盖；Copilot X/Flutter 3.20/Rust 1.80 → 超出范围
- ✅ source-index: 0 unmapped high-quality
- ✅ Clippings: 20 天未更新（stale）
- ✅ research-feeds: 3+ 月未更新（stale）

## [Task2A Round 88] ch14.9 Camera 性能分析 — 2026-07-13
- **类型**：内容补充
- **来源**：DeepResearch 2026-07-13-camera-perfetto-latency-decomposition.md (309 行 AOSP 源码级调研)
- **建议补充**：
  1. CameraService::connectHelper() 中 openLatencyMs 的计算与 statsd 上报路径
  2. SessionStatsBuilder::incCounter() 中 mStartLatencyMs（首帧延迟）的写入逻辑
  3. CameraLatencyHistogram 10-bin 分箱（100/200/300/400/500/700/900/1300/2100ms）
  4. CameraServiceProxyWrapper → ICameraServiceProxy → statsd 的完整上报链路
  5. Perfetto async slice 名称（"frame capture"/"first full buffer"/"still capture"）与 ATRACE 宏的映射
- **参考书覆盖深度**：无（Clippings 参考书未覆盖 Camera 子系统）
- **结构参考**：[来源: DeepResearch/2026-07-13-camera-perfetto-latency-decomposition.md]

### 2026-07-13 Round 95 Gap Mining — 已检查方向
- ✅ DeepResearch 4 篇（2026-07-12）：binder-priority（§1.48/§1.53/§1.44 已覆盖，12/20）、ftrace-bridge（§14.31 已覆盖）、power-advisor（§5.29 已覆盖）、sensor-privacy（隐私主题非性能，9/20）
- ✅ Daily-info 2026-07-13: 全部已覆盖或超范围
- ✅ source-index: 空
- ✅ Clippings: 20 天 stale
- ✅ research-feeds: 3+ 月 stale
