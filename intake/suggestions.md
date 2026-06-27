## [Task9 Deep Review] 1.25 Android 17 Binder IPC 异步机制与批处理流水线 — 2026-06-27
- **类型**：源码准确性
- **位置**：IPCThreadState::transact() 行号引用
- **问题**：文中引用 IPCThreadState.cpp:948-996，但实际 android-17.0.0_r1 中该函数行号为 1056-1104
- **建议**：修正行号引用为 1056-1104，确保源码引用准确

## [Task9 Deep Review] 1.25 Android 17 Binder IPC 异步机制与批处理流水线 — 2026-06-27
- **类型**：源码准确性
- **位置**：BR_FROZEN_REPLY 处理逻辑
- **问题**：文中提到 BR_FROZEN_REPLY 但未给出 IPCThreadState.cpp:1183-1188 的具体处理代码片段
- **建议**：补充完整的 BR_FROZEN_REPLY 处理代码，包括错误类型判断和返回值处理逻辑

## [Task9 Deep Review] 1.25 Android 17 Binder IPC 异步机制与批处理流水线 — 2026-06-27
- **类型**：源码准确性
- **位置**：enableFrozenObjectErrorCode() 函数实现
- **问题**：文中引用 enableFrozenObjectErrorCode() 函数但未说明其在 IPCThreadState.cpp:104-107 的具体实现
- **建议**：补充该函数的完整实现代码，包括 aconfig flag 查询逻辑

## [Task9 Deep Review] 1.25 Android 17 Binder IPC 异步机制与批处理流水线 — 2026-06-27
- **类型**：版本差异
- **位置**：Android 12-17 的渐进式优化
- **问题**：文中提到 Android 12 引入冻结回执，但未说明 Android 13/14/15/16/17 在这个机制上的具体增量改进
- **建议**：补充 Android 12-17 各版本中冻结回执机制的具体演进变化

## [Task9 Deep Review] 1.25 Android 17 Binder IPC 异步机制与批处理流水线 — 2026-06-27
- **类型**：数据缺失
- **位置**：关键性能断言部分
- **问题**："oneway 调用延迟对比"、"批处理吞吐提升"、"冻结回执对 ANR 的影响"等关键断言缺少量化数据支撑
- **建议**：补充实测数据，包括端到端延迟对比、syscall 减少量统计、ANR window 优化效果等

## [Task9 Deep Review] 1.25 Android 17 Binder IPC 异步机制与批处理流水线 — 2026-06-27
- **类型**：交叉引用
- **位置**：相关章节引用
- **问题**：文中提到 1.27 和 1.30 章节，但 src/ 目录下不存在这两个章节
- **建议**：修正引用为已存在的章节号，或标注为"未来章节"，避免误导读者

## [Task6 Review] 1.25 Android 17 Binder IPC 异步机制与批处理流水线 — 2026-06-27
- **类型**：需重写
- **位置**：全文结构
- **问题**：正文以源码验证注释为主，缺乏工程师视角的叙述串联。当前风格是"源码索引+行号注释"，不是连贯叙述。writing-guide §三.1 明确要求"叙述为主，列表为辅"。
- **建议**：在已验证源码结论基础上，增加叙述性段落。每个机制按"为什么存在→怎么工作→在 trace 中怎么观察"展开。参考 writing-guide 类型A结构模板。

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

## [Task9 Deep Review] 1.25 Android 17 Binder IPC 异步机制与批处理流水线 — 2026-06-28
- **类型**：源码准确性
- **位置**：BINDER_VM_SIZE 定义
- **问题**：文中提到共享缓冲区大小定义，但未给出 ProcessState.cpp:48 的具体行号和定义内容
- **建议**：补充 BINDER_VM_SIZE 的完整定义和注释说明，包括内存映射大小的计算逻辑

## [Task9 Deep Review] 1.25 Android 17 Binder IPC 异步机制与批处理流水线 — 2026-06-28
- **类型**：原理完整性
- **位置**：冻结回执与进程生命周期关系
- **问题**：缺少 BR_FROZEN_REPLY 和 BR_TRANSACTION_PENDING_FROZEN 与进程 freezer、oom_adj、app lifecycle 的完整交互链
- **建议**：补充冻结回执机制与进程生命周期的完整关系图，包括冻结状态转换的条件和时机

## [Task9 Deep Review] 1.25 Android 17 Binder IPC 异步机制与批处理流水线 — 2026-06-28
- **类型**：原理完整性
- **位置**：oneway spam 检测机制
- **问题**：未解释内核计数器如何工作、阈值多少、与用户态的协作机制
- **建议**：补充 oneway spam 检测的完整工作机制，包括计数器算法、触发阈值和用户态日志记录的触发条件