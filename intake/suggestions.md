# General Suggestions and Improvements
**external. 二、总体结论**
- 章节：14.8
**external. 二、总体结论**
- 问题类型：数据支撑
**external. 二、总体结论**
- 位置：实战案例 1-3
**external. 二、总体结论**
- 问题描述：缺乏真实实测数据支撑，目前多为经验数值估计。
**external. 二、总体结论**
- 建议：收集设备上真实的 trace 记录，并替换为真实业务数据。
**external. 二、总体结论**
- **章节**：14.5 / 15.5
**external. 二、总体结论**
- **类型**：建议补充
**external. 二、总体结论**
- **位置**：Booster 章节
**external. 二、总体结论**
- **描述**：AGP 8.0 Transform 替代方案可以提供更清晰的 API 指引。
**external. 二、总体结论**
- **建议**：明确提及 `AsmClassVisitorFactory`。
**external. 二、总体结论**
- 章节：14.10
**external. 二、总体结论**
- 问题类型：原理链完整性
**external. 二、总体结论**
- 位置：UprobeStats 与动态埋点
**external. 二、总体结论**
- 问题描述：缺少 Mainline 升级特性的明确说明。
**external. 二、总体结论**
- 建议：补充说明 UprobeStats APEX 模块具备 Mainline 独立升级特性。
**external. 二、总体结论**
- 章节：15.13 Hook 基础设施与性能工具实现原理
**external. 二、总体结论**
- 问题类型：内容缺失
**external. 二、总体结论**
- 位置：第一条路线：系统回调 / 官方接口
**external. 二、总体结论**
- 问题描述：未提及 JVMTI。
**external. 二、总体结论**
- 建议：补充 JVMTI (Android 8.0+) 作为线下最强大的官方监控基础设施。
**external. 二、总体结论**
- **章节**：14.6 / 15.6
**external. 二、总体结论**
- **类型**：建议改进
**external. 二、总体结论**
- **位置**：指标测量章节
**external. 二、总体结论**
- **描述**：强化 TTFD 和 `reportFullyDrawn()` 的绑定关系。
**external. 二、总体结论**
- **建议**：明确 `reportFullyDrawn()` 作为 TTFD 的官方触发点。
**external. 二、总体结论**
- **章节**：7.3
**external. 二、总体结论**
- **类型**：建议补充
**external. 二、总体结论**
- **位置**：JankStats 构造器
**external. 二、总体结论**
- **描述**：构造器接受 `WindowMetrics` 参数，但建议提供便捷工厂方法。
**external. 二、总体结论**
- **建议**：增加 `JankStats.createForWindow(context)` 静态方法封装。
**external. 二、总体结论**
- **章节**：14.8
**external. 二、总体结论**
- **类型**：建议改进
**external. 二、总体结论**
- **位置**：关键指标测量章节
**external. 二、总体结论**
- **描述**：建议增加 CPU 使用率与 UI 线程阻塞的关联分析。
**external. 二、总体结论**
- **建议**：补充 `proc` 文件系统读取 CPU 频率与进程状态的示例代码。

---

## [Task6 Review] 16.5 Android 17 (API 37) 性能行为变更与适配方法 — 2026-04-23
- **类型**：需补充数据/需验证
- **位置**：性能提升数据描述
- **问题**：4%掉帧减少缺乏具体测试环境和基线说明；MessageQueue字段变更在AOSP android-17-beta3中描述不够精确
- **建议**：需补充具体的设备配置、测试条件和性能对比基线；需要在实际代码中验证字段变更的具体影响
- **review 日志**：logs/review/2026-04-23-16-review.md

## [Task6 Review] 2.0 渲染系统总纲 — 2026-04-23
- **类型**：需补充内容
- **位置**：章节依赖关系
- **问题**：各章节之间的具体依赖关系不够明确，缺乏典型性能问题排查路径
- **建议**：添加章节依赖关系图和典型性能问题排查路径流程图
- **review 日志**：logs/review/2026-04-23-16-review.md

## [Task6 Review] 2.21 文字渲染性能 — 2026-04-23
- **类型**：需补充数据/需补充优化指导
- **位置**：性能对比数据、优化步骤、版本演进
- **问题**：StaticLayout vs BoringLayout缺乏具体耗时对比数据；缺少PrecomputedText的具体使用示例和适用条件；缺少Android各版本文字渲染的性能变化趋势
- **建议**：补充具体的性能测试数据和使用示例；补充Android 12-17文字渲染性能的演进对比和最佳实践
- **review 日志**：logs/review/2026-04-23-16-review.md