## [Task9 Deep Review] 1.9 Package Manager Service 与应用安装性能 — 2026-05-30

### [Task9 Deep Review] 1.9 Package Manager Service 与应用安装性能 — 2026-05-30
- **类型**：知识盲区
- **位置**：应用安装全流程章节
- **问题**：未提及多用户设备上应用安装的用户维度隔离实现细节（Android 多用户机制下的应用数据目录管理和权限隔离）
- **建议**：补充说明 Android 多用户环境下，应用数据目录如何按用户隔离、`IInstalld` 如何处理用户维度数据准备、以及多用户对安装性能的影响

- **类型**：知识盲区
- **位置**：ProfilingManager工具协作边界
- **问题**：缺少ProfilingManager与Systrace、perfetto等底层工具的深度集成边界讨论
- **建议**：补充ProfilingManager与系统级trace工具的协作边界、触发时机优先级、资源分配策略以及复用机制的深入讨论

## [Task9 Deep Review] 14.7 ProfilingManager — 2026-05-30
- **类型**：数据缺失
- **位置**：生产环境基准数据章节
- **问题**：缺少实际线上场景的Profiling性能数据、故障案例和参数优化基准
- **建议**：补充实际生产环境中的Profiling性能开销数据、buffer size和采样频率的优化基准、以及典型故障场景的分析案例

## [Task9 Deep Review] 14.7 ProfilingManager — 2026-05-30
- **类型**：版本差异
- **位置**：OEM兼容性讨论
- **问题**：未涵盖不同厂商Android实现的Profiling行为差异和适配策略
- **建议**：补充主流OEM（小米、华为、OPPO等）对Profiling模块的实现差异、配置参数差异以及兼容性适配策略
- **问题**：缺少不同编译级别在不同设备配置下的基准数据（如 verify/speed-profile/speed 在不同核心数/内存配置下的编译时间对比）
- **建议**：补充 concrete benchmark 数据，帮助读者理解编译选择的实际性能权衡

## [Task9 Deep Review] 14.7 ProfilingManager — 2026-05-30
- **类型**：源码准确性
- **位置**：BufferFillPolicy 枚举表说明
- **问题**：章节明确说明 FLUSH_FULL 不在公开 API 中，但文中仍提及 FLUSH_FULL 2 次，与章节自身说明矛盾
- **建议**：删除所有对 FLUSH_FULL 的提及，确保与实际 AndroidX API 一致

- **类型**：原理完整性
- **位置**：结果分发机制
- **问题**：文中提到"显式请求与 global listener 可以同时命中"，但缺少对去重机制和优先级的详细说明
- **建议**：补充结果去重机制的具体实现，包括 resultFilePath 作为去重主键、失败情况下的兜底策略等

- **类型**：知识盲区
- **位置**：整体章节
- **问题**：未讨论 ProfilingManager 与 Battery Historian 的集成方法
- **建议**：补充说明如何将 ProfilingManager 数据与 Battery Historian 数据结合分析，提供故障排查的完整流程

- **类型**：数据支撑
- **位置**：性能提升描述
- **问题**：文中提到"Baseline Profile 可以将冷启动时间改善约 30%"，但缺少具体测试设备和场景数据
- **建议**：补充测试设备型号、Android 版本、测试方法和具体的性能提升数据范围

## [Task9 Deep Review] 14.6 自动化测试工具 — 2026-05-30
- **类型**：源码准确性
- **位置**：FrameTimingMetric API 版本边界
- **问题**：文中提到 `frameOverrunMs` 等 deadline / overrun 指标仅 API 31+，但需要明确这是 Macrobenchmark 支持的版本，不是 Android 系统版本
- **建议**：明确区分 Android 系统版本与 Macrobenchmark 库支持的版本边界，避免读者混淆

- **类型**：源码准确性
- **位置**：PowerMetric 设备要求
- **问题**：文中提到 API 29+ 是入口条件，但缺少对设备必须支持 power rails / ODPM 的重要补充说明
- **建议**：明确指出即使 API 29+，设备也必须支持 power rails / ODPM 才能获得功耗数据，并推荐支持该功能的设备型号

- **类型**：原理完整性
- **位置**：Microbenchmark 预热机制
- **问题**：文中提到"会自动处理预热（warmup）"，但缺少对预热次数、判断标准和如何避免 JIT 编译干扰的详细说明
- **建议**：补充 Microbenchmark 的预热机制细节，包括默认预热次数、如何判断预热完成、JIT 编译对测量的影响等

- **类型**：知识盲区
- **位置**：基准测试环境配置
- **问题**：未讨论 CI 环境中如何正确配置 CPU/Governor、内存限制、后台进程清理等环境变量
- **建议**：补充基准测试环境的最佳配置实践，包括 CPU 模式设置、内存限制、后台进程清理等

- **类型**：数据支撑
- **位置**：性能回归阈值
- **问题**：文中提到"如果关键指标（如冷启动时间）超出阈值，就标记构建为失败"，但没有给出具体的阈值设置依据
- **建议**：提供具体的阈值设置指导，包括基于历史基线的百分比设置、绝对时间设置的最佳实践等

- **类型**：数据支撑
- **位置**：基准测试稳定性
- **问题**：文中没有提供多次运行基准测试的波动范围数据，读者无法评估测试结果的可靠性
- **建议**：补充 Macrobenchmark 测试的正常波动范围数据，帮助读者判断测试结果的可靠性