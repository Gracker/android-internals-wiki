## [Task9 Idle Audit] ch15 Android 性能优化研究方法论 — 2026-06-27
- **类型**：源码引用准确性
- **位置**：3.2.2 Android 9 (API 28) - Perfetto 启动命令
- **问题**：文中提到 Android 9 需要手动启用 Perfetto traced，但命令 `adb shell traced &` 可能不准确。Android 9 的 Perfetto 可能需要使用不同参数或路径，建议验证官方文档中的正确命令格式。
- **建议**：核实 Android 9 中 Perfetto traced 的准确启用方法和命令参数，确保与 android-17.0.0_r1 实际实现一致。

## [Task9 Idle Audit] ch15 Android 性能优化研究方法论 — 2026-06-27
- **类型**：源码引用准确性
- **位置**：3.2.5 Android 17 (API 37) - traced 异步模式
- **问题**：文中提到 Android 17 支持异步模式 `adb shell traced --async`，该命令参数和功能需要在官方文档中验证，确保符合实际实现。
- **建议**：验证 Android 17 中 traced --async 命令的准确性和功能特性，补充具体的参数说明和使用场景。

## [Task9 Idle Audit] ch15 Android 性能优化研究方法论 — 2026-06-27
- **类型**：版本差异覆盖
- **位置**：3.3 工具选择的具体策略 - Android 14-17
- **问题**：文中提到"Android 14-17: Perfetto 完全替代 Systrace"，但这个时间点可能不准确。需要验证 Systrace 完全移除的准确时间点和 AOSP 变更。
- **建议**：核实 Systrace 完全移除的准确 Android 版本，补充 Systrace 到 Perfetto 迁移的具体时间线和兼容性说明。

## [Task9 Idle Audit] ch15 Android 性能优化研究方法论 — 2026-06-27
- **类型**：版本差异覆盖
- **位置**：3.2.3 Android 14 (API 34) - Perfetto 缓冲区大小
- **问题**：文中提到 Android 14 支持 `-b 16384` 缓冲区选项，需要确认该参数在 android-17.0.0_r1 中的可用性和具体实现细节。
- **建议**：验证 Android 14-17 各版本中 traced 命令的缓冲区参数支持情况，补充具体的参数限制和性能影响说明。

## [Task9 Idle Audit] ch15 Android 性能优化研究方法论 — 2026-06-27
- **类型**：版本差异覆盖
- **位置**：3.2.2 Android 11+ (API 30+) - Perfetto 默认启用
- **问题**：文中提到"Android 11+ (API 30+): Perfetto 默认启用"，但需要确认是否所有 Android 11 设备都默认启用，还是需要特定条件，避免以偏概全。
- **建议**：补充 Android 11+ 中 Perfetto 启用条件的详细说明，包括不同设备类型、系统版本的具体差异和配置要求。

## [Task9 Idle Audit] ch15 Android 性能优化研究方法论 — 2026-06-27
- **类型**：版本差异覆盖
- **位置**：3.2.1 Android 9+ 工具演进 - 缺少 Android 10 说明
- **问题**：文中缺少 Android 10 (API 29-30) 中间状态说明，Perfetto 从 Android 9 到 Android 11+ 的渐进过程描述不完整。
- **建议**：补充 Android 10 中 Perfetto 的可用性、限制和启用方法，说明其作为 Android 9 和 Android 11+ 之间过渡版本的特点。

## [Task9 Idle Audit] ch15 Android 性能优化研究方法论 — 2026-06-27
- **类型**：版本差异覆盖
- **位置**：3.2.5 Android 17 (API 37) - Perfetto 进一步优化描述
- **问题**：Android 17 的 Perfetto 进一步优化和异步采集描述过于简略，缺少具体的新增功能说明。
- **建议**：补充 Android 17 中 Perfetto 的具体新增特性，如异步采集的具体实现方式、电池感知策略的具体参数、性能分析增强功能等。

## [Task9 Idle Audit] ch15 Android 性能优化研究方法论 — 2026-06-27
- **类型**：源码引用准确性
- **位置**：工具选择的具体策略 - 各版本 ADB 命令
- **问题**：文中提到的 ADB 命令（如 traced、dumpsys meminfo、top、batterystats）在不同 Android 版本中的参数和行为可能有差异。
- **建议**：为每个 ADB 命令添加版本限定说明，特别是参数变化和功能差异的详细说明。

## [Task9 Idle Audit] ch15 Android 性能优化研究方法论 — 2026-06-27
- **类型**：版本差异覆盖
- **位置**：3.3 工具选择的具体策略 - 各版本工具组合
- **问题**：文中提到的工具组合在不同 Android 版本间的过渡和兼容性描述不够详细。
- **建议**：补充各版本间工具组合的平滑过渡建议，以及兼容性问题的解决方案。

## [Task9 Idle Audit] ch15 Android 性能优化研究方法论 — 2026-06-27
- **类型**：版本差异覆盖
- **位置**：4.1 数据采集策略 - 采样策略设计
- **问题**：文中提到的采样策略可能需要根据不同 Android 版本的特点进行调整。
- **建议**：补充针对不同 Android 版本的采样策略优化建议，特别是 Android 14-17 新特性对数据采集的影响。

## [Task9 Idle Audit] ch15 Android 性能优化研究方法论 — 2026-06-27
- **类型**：版本差异覆盖
- **位置**：13.3 方法论实施建议 - 技术层面
- **问题**：文中提到"选择合适工具"但缺少针对不同 Android 版本的具体工具选择指导。
- **建议**：补充针对不同 Android 版本的工具选择决策树，帮助开发者根据目标版本选择合适的性能分析工具。
## [Task6 Review] 1.25 Android 17 Binder IPC 异步机制与批处理流水线 — 2026-06-27
- **类型**：需重写
- **位置**：全文结构
- **问题**：正文以源码验证注释为主，缺乏工程师视角的叙述串联。当前风格是"源码索引+行号注释"，不是连贯叙述。writing-guide §三.1 明确要求"叙述为主，列表为辅"。
- **建议**：在已验证源码结论基础上，增加叙述性段落。每个机制按"为什么存在→怎么工作→在 trace 中怎么观察"展开。参考 writing-guide 类型A结构模板。
- **review 日志**：logs/review/2026-06-27-22-review.md

## [Task6 Review] 1.25 — 2026-06-27
- **类型**：需补充素材
- **位置**：章节开头
- **问题**：缺少"为什么要了解 Binder 异步机制"的引入段落。从 outline 直接跳入"源码验证结论"，无动机交代。
- **建议**：补写 2-3 段开头，从实际性能问题场景引入（如 oneway spam 导致卡顿、冻结回执对 ANR 的影响）。

## [Task6 Review] 1.25 — 2026-06-27
- **类型**：需补充素材
- **位置**：🔸 扩展锚点（L49-52）
- **问题**：两个扩展锚点（Binder 异步性能基准测试 / 兼容性适配策略）完全无内容覆盖。
- **建议**：至少补充框架性内容或标注[待补充]，或调整 outline 去掉当前无法覆盖的锚点。

## [Task6 Review] 1.25 — 2026-06-27
- **类型**：需重写
- **位置**：outline 描述（L36-45）
- **问题**：大纲4个🔹锚点描述偏 AI 套话："重大变革""深度优化""显著提升""更高效的"等模糊形容词，与下方精确源码内容不匹配。
- **建议**：对照已验证源码结论重写大纲描述，用具体技术事实替代模糊形容词。

## [Task6 Review] 1.25 — 2026-06-27
- **类型**：需确认
- **位置**：L57,L60,L64-65
- **问题**：正文残留加工过程元数据（"本节由 AIW 每日源码调研自动反哺"、HTML 注释中的过程记录）。writing-guide §五要求发布稿不留编辑痕迹。
- **建议**：定稿前清除所有加工过程标记。

## [Task6 Review] 1.25 — 2026-06-27
- **类型**：需补充素材
- **位置**：全文
- **问题**：缺少"在 Perfetto/工具中的表现"章节。writing-guide 要求机制原理篇必须包含 Trace 中的表现描述。
- **建议**：补充 Binder 相关 track 在 Perfetto 中的表现，或标注[待补充：Trace 截图]。

## [Task9 Deep Review] 1.25 Android 17 Binder IPC 异步机制与批处理流水线 — 2026-06-27
- **类型**：原理断裂
- **位置**：冻结回执机制章节
- **问题**：缺少冻结状态转换的完整时序图，读者难以理解何时触发BR_FROZEN_REPLY与BR_TRANSACTION_PENDING_FROZEN的状态切换条件
- **建议**：补充状态转换流程图，说明frozen state的进入条件、触发时机和退出机制

## [Task9 Deep Review] 1.25 Android 17 Binder IPC 异步机制与批处理流水线 — 2026-06-27
- **类型**：版本差异
- **位置**：与Android 16的差异对比
- **问题**：未说明Android 16到17中Binder异步机制的具体演进点，缺少关键特性变更的版本对比
- **建议**：添加Android 16 vs 17的异步机制演进对比表格，重点标注新增功能和废弃特性

## [Task9 Deep Review] 1.25 Android 17 Binder IPC 异步机制与批处理流水线 — 2026-06-27
- **类型**：数据缺失
- **位置**：性能断言部分
- **问题**："oneway 节省""批处理 IPC 吞吐""BR_FROZEN_REPLY 立即感知失败"等关键性能断言缺少具体基准测试数据支撑
- **建议**：补充Binder异步机制的性能测试数据，包括延迟对比、吞吐量提升百分比、ANR window优化效果等量化指标

## [Task2B Fixed] 1.25 — 2026-06-27 22:50
以上所有 1.25 相关的 Task6/Task9 问题单已在 Task2B 主修复中处理完毕：
- [Task9 P0] FLAG_ONEWAY 行号：已核实，实际在 78-79，Task9 标注错误，保持原值
- [Task9 P1] waitForResponse 签名：已核实，匹配 android-17.0.0_r1 实际签名
- [Task9 P2] 冻结状态转换时序图：已添加 mermaid 时序图
- [Task9 P2] 版本差异对比：已添加 Android 16 vs 17 对比表
- [Task9 P1] 性能数据：已添加对比表，量化数据标注 [待补充]
- [Task9 知识盲区] Binder 线程池调度：已补充调度机制分析
- [Task6] 全文结构：已从源码索引转为叙述为主
- [Task6] 缺少开头：已添加动机引入
- [Task6] 扩展锚点空白：已填充兼容性迁移要点
- [Task6] Outline AI 套话：已重写
- [Task6] 加工过程元数据：已清除
- [Task6] Perfetto 表现：已添加 Trace 观察表，截图标注 [待补充]

## [Task6 Review] 1.25 Android 17 Binder IPC 异步机制与批处理流水线 — 2026-06-27

### 问题 1：Binder 线程池数量计算逻辑存疑
- **类型**：需确认（技术准确性）
- **位置**：§6 Binder 线程池与 oneway 调用的调度，"应用进程：8 个 binder 线程（`BINDER_VM_SIZE` / 128KB，实际由 `DEFAULT_MAX_BINDER_THREADS` 控制）"
- **问题**：`BINDER_VM_SIZE / 128KB = 8` 的除法逻辑有误导性——binder 线程池上限不由缓冲区大小除法决定，而是由 `DEFAULT_MAX_BINDER_THREADS` 常量控制。括号内的除法算式容易让读者误解因果关系。
- **建议**：Task 9 验证 `DEFAULT_MAX_BINDER_THREADS` 在 android-17.0.0_r1 中的实际值和定义位置；修正或删除除法表述。

### 问题 2：enableFrozenObjectErrorCode() aconfig flag 默认值不确定
- **类型**：需确认（版本差异）
- **位置**：§7 与 Android 16 的关键区别，对比表最后一行
- **问题**：表格中写 "aconfig flag 默认关闭（部分构建）" → "aconfig flag，默认可能不同"，"可能不同"是不确定表述
- **建议**：Task 9 查证 Android 17 中 `enable_frozen_object_error` aconfig flag 的实际默认值，明确写入或删除该行。

### 问题 3：BR_FROZEN_REPLY 响应时间数据无来源
- **类型**：需确认（数据来源）
- **位置**：§5 关键性能特征，对比表 "冻结进程响应" 行
- **问题**：`BR_FROZEN_REPLY 立即感知（< 1ms）` 中的 < 1ms 没有标注数据来源或测试条件
- **建议**：补充实测数据来源，或改为定性描述（"立即返回，不走超时等待"）。

### 问题 4：RPC Binder 缓冲区版本归属待验证
- **类型**：需确认（版本归属）
- **位置**：§5 末尾 "与 RPC Binder 的缓冲区边界" 段落
- **问题**：提到 `kDefaultRpcBinderSize` 从 ~100KB 扩到 ~600KB，但未明确这个变更发生在哪个 Android 版本
- **建议**：Task 9 验证该扩容变更的具体版本（是否属于 Android 17），明确标注。

### 问题 5：性能数据和 Perfetto trace 描述大量待补充
- **类型**：需补充素材
- **位置**：§5 "量化数据 [待补充]"、§8 整节 [待补充：Trace 截图]
- **问题**：章节核心性能数据（oneway vs 同步延迟对比、批处理 syscall 减少量、ANR 次数对比）和 Perfetto trace 观察描述均为空
- **建议**：不阻塞当前 review 流程，但需后续补充实测 trace 数据。建议在 Task 9 完成技术验证后，由 Task 2B 补充。

---
*review 日志：logs/review/2026-06-27-23-review.md*
