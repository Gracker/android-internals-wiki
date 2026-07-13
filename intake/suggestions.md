## [Task9 Deep Review] 16.5 Android 17 (API 37) 性能行为变更与适配方法 — 2026-07-13
- **类型**：源码准确性
- **位置**：从 Concurrent Copying 到 Generational CMC 章节
- **问题**：章节中分代 GC 的性能数据不够具体，只提到"young GC 速度远快于 full GC"但缺少具体的暂停时间对比数据
- **建议**：补充典型场景下 young GC 和 full GC 的暂停时间、内存回收量、CPU 占用对比数据

## [Task9 Deep Review] 16.5 Android 17 (API 37) 性能行为变更与适配方法 — 2026-07-13
- **类型**：版本差异
- **位置**：ProfilingManager 新的系统触发器章节
- **问题**：章节提到新增触发器，但未明确说明这些触发器在 Android 17 中的具体行为和产物格式差异
- **建议**：补充 ProfilingManager 在 Android 17 中各个触发器的具体行为描述、产物格式和使用建议

## [Task9 Deep Review] 16.5 Android 17 (API 37) 性能行为变更与适配方法 — 2026-07-13
- **类型**：知识盲区
- **位置**：16KB 页面对游戏引擎的影响章节
- **问题**：虽然提到游戏引擎受影响，但缺少具体案例和解决方案
- **建议**：补充 16KB 页面对常见游戏引擎（如 Unity、Unreal）的具体影响案例和适配方案

## [Task9 Deep Review] 16.5 Android 17 (API 37) 性能行为变更与适配方法 — 2026-07-13
- **类型**：数据支撑
- **位置**：ProfilingManager 触发器开销章节
- **问题**：缺少系统触发器相对于手动触发的额外开销数据
- **建议**：补充 ProfilingManager 系统触发器相对于手动触发器的额外 CPU、内存、I/O 开销数据

## [Task9 Deep Review] 16.5 Android 17 (API 37) 性能行为变更与适配方法 — 2026-07-13
- **类型**：交叉引用
- **位置**：相关章节引用
- **问题**：正文引用"1.7 ART 编译机制"、"1.12 AutoFDO 优化"等章节，但需要确认这些章节是否确实存在且内容一致
- **建议**：验证并确认相关章节的准确存在性，确保交叉引用的一致性

## [Task9 Deep Review] 16.9 Android 17 SDM 安装编译链路性能 — 2026-07-13
- **类型**：数据支撑
- **位置**：云端编译性能提升章节
- **问题**：章节中提到的编译时间减少40-60%、安装大小减少15-25%、启动时间减少30-45%等性能数据缺乏具体的测试环境和配置信息
- **建议**：补充性能数据的测试环境、验证方法和可复现步骤，增加数据的可信度

## [Task9 Deep Review] 16.9 Android 17 SDM 安装编译链路性能 — 2026-07-13
- **类型**：版本差异
- **位置**：SDM架构概览章节
- **问题**：部分Android 17特有的优化机制未与之前的版本做充分对比，容易造成理解偏差
- **建议**：增加与Android 16及更早版本的详细对比说明，突出Android 17的关键改进点

## [Task9 Deep Review] 16.9 Android 17 SDM 安装编译链路性能 — 2026-07-13
- **类型**：知识盲区
- **位置**：并行编译优化章节
- **问题**：提到多线程并行编译，但缺少具体的线程数优化配置和效果数据
- **建议**：补充编译线程数的优化配置建议、不同设备配置下的性能效果对比数据

## [Task9 Deep Review] 16.9 Android 17 SDM 安装编译链路性能 — 2026-07-13
- **类型**：数据支撑
- **位置**：性能提升数据章节
- **问题**：提到的40-60%编译时间提升、30-45%启动时间提升等性能数据缺乏具体的验证方法和测试环境信息
- **建议**：补充性能数据的测试环境说明、验证方法和可复现的具体步骤

## [Task9 Deep Review] 16.9 Android 17 SDM 安装编译链路性能 — 2026-07-13
- **类型**：交叉引用
- **位置**：相关章节引用
- **问题**：章节中涉及的其他章节引用需要确保准确性和一致性
- **建议**：验证并更新所有相关章节的交叉引用，确保内容的一致性和准确性

## [Task6 Review] 16.9 Android 17 SDM 安装编译流程性能 — 2026-07-13

### B1 [需重写] §2-§6 大量疑似虚构代码（P0）
- **位置**：§2.1/§3.1/§3.2/§4.2/§5.1/§5.2/§6.1/§6.2 所有代码块
- **问题**：DeviceBasedDexopt、InstallProcessor、BackgroundCompiler、ArtDaemon、FileUtils::OptimizeFileAccess、InstallSessionOptimizer、InstallExecutor、DexoptManager、CompilationRequestOptimizer 等类/方法在 AOSP android-17.0.0_r1 中不存在
- **建议**：全部代码对照 AOSP 真实源码重写，无法验证的删除或标注 [待验证]

### B2 [需重写] 全篇百科词条式结构（P1）
- **位置**：全文
- **问题**：违反 writing-guide "叙述为主，列表为辅"原则，属于"百科词条式"反面教材
- **建议**：按 Type A（机制原理篇）重写，每节补连贯叙述段落

### B3 [需补充] §7-§10 内容空洞（P1）
- **位置**：§7/§8/§9/§10
- **问题**：仅名词罗列，无实质内容（如 §8.2 仅列工具名无用法）
- **建议**：补充具体场景、命令示例、操作指导；§10 精简或删除

### B4 [需补充] 缺少 Perfetto/Trace 观测指导（P2）
- **位置**：全文
- **问题**：性能章节无 Trace 观测内容
- **建议**：补充"在 Perfetto 中观测 SDM 编译"小节

### B5 [需确认] §2.2 性能数据来源（P2）
- **位置**：§2.2
- **问题**：标注"Android 官方公布"但无链接
- **建议**：补充来源链接或改标"社区测试数据"

- **review 日志**：logs/review/2026-07-13-22-review.md

## [Task2B 回炉完成] 16.9 Android 17 SDM 安装编译流程性能 — 2026-07-13 22:54

来源：Task6 Review (priority 90) + Task9 Deep Tech Review (priority 95)
修复内容：
- P0 ×8: 删除全部虚构代码（DeviceBasedDexopt/ProfileBasedDexopt/InstallProcessor/BackgroundCompiler/ArtDaemon/FileUtils::OptimizeFileAccess/InstallSessionOptimizer/InstallExecutor/DexoptManager/CompilationRequestOptimizer 等类和方法在 AOSP android-17.0.0_r1 中不存在）
- P0: 全篇从百科词条式列表（90%列表占比）重写为 Type A 机制原理叙述（~18%列表占比）
- P0: 性能数据标注"官方宣称+需独立验证"警告，补充具体验证步骤
- P1: §7-10 空洞内容（60行名词罗列无实质）压缩为实用调试指导（检查SDM状态/故障模式表/强制验证模式）
- P1: 新增 §6 在 Perfetto 中观测 SDM 编译（track对照表+3个典型场景+SQL查询模板）
- P1: 补充 SDK 版本与传统 dexopt 关系说明
- P1: 补充开发者适配建议（5条实操指南）
- L1: "链路"5处→全部替换
状态：已回送 Task6 → Task9 复审 (pipeline_stage: task6_pending)
