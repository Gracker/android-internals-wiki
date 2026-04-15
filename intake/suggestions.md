## [Task9 Deep Review] 3.1 Input 事件分发全流程 — 2026-04-15
- **类型**：版本差异
- **位置**：Android 12 InputFlinger 重构描述
- **问题**：Android 12 的 InputFlinger 重构描述过于简化，实际是代码抽取到独立服务但仍运行在同一进程内，而非真正的独立服务
- **建议**：修正描述，明确说明代码组织变化和运行时环境

## [Task9 Deep Review] 3.1 Input 事件分发全流程 — 2026-04-15
- **类型**：版本差异
- **位置**：版本演进表
- **问题**：缺少 Android 15 Predictive Back 手势对 Input 分发路径的重大影响
- **建议**：补充 Android 15 版本变更，说明预测性返回手势的实现机制

## [Task9 Deep Review] 3.1 Input 事件分发全流程 — 2026-04-15
- **类型**：数据缺失
- **位置**：ANR 超时机制部分
- **问题**：缺少实际 ANR Trace 分析案例，无法展示 wq 堆积到 ANR 触发的完整过程
- **建议**：添加一个具体的 Input ANR Trace 分析案例，包括 wq 堆积、ANR 触发、系统响应的完整时序

## [Task9 Deep Review] 3.1 Input 事件分发全流程 — 2026-04-15
- **类型**：数据缺失
- **位置**：性能分析部分
- **问题**：缺少不同场景下的 Input 处理耗时基准数据
- **建议**：补充正常点击 vs 复杂手势处理的耗时对比数据，提供量化参考
## [Task6 Review] 16.5 Android 17 (API 37) 性能行为变更与适配方法 — 2026-04-15
- **类型**：回炉重修（技术细节验证）
- **位置**：全文多处关键技术点
- **问题**：
  1. ProfilingManager 触发器常量名需验证
  2. DeliQueue 性能改善需补充 Trace 截图
  3. 16KB 页面断言需提供具体案例
- **建议**：
  1. 检查 AOSP 源码中 ProfilingManager 触发器常量
  2. 补充真实的 Perfetto Trace 片段
  3. 提供具体的原生库名称和 AOSP 链接
- **review 日志**：logs/review/2026-04-15-17-review.md



## [Task9 Deep Review] 2.2 帧率与刷新率 — 2026-04-15
- **类型**：数据缺失
- **位置**："120Hz 的屏幕功耗通常比 60Hz 高 20-40%"（扩展：120Hz 场景功耗权衡）
- **问题**：功耗差异数值缺少可追溯的来源，且未说明适用于哪种面板技术
- **建议**：标注为近似参考值，注明"具体功耗差异因面板技术和设备而异"

## [Task9 Deep Review] 2.2 帧率与刷新率 — 2026-04-15
- **类型**：数据缺失
- **位置**："触摸停止后一段时间（通常 2-3 秒）"（Touch Boost 描述）
- **问题**：Touch Boost 超时是 OEM 可配置的，AOSP 默认值可能与"2-3 秒"不符
- **建议**：改为"OEM 可配置的触摸提升超时"或标注为近似值

## [Task9 Deep Review] 2.2 帧率与刷新率 — 2026-04-15
- **类型**：数据缺失
- **位置**："Janky frames 比例超过 5% 时用户能明显感知到卡顿"
- **问题**：缺少来源
- **建议**：标注来源或改为更保守的表述

## [Task9 Deep Review] 2.2 帧率与刷新率 — 2026-04-15
- **类型**：源码准确性
- **位置**：Perfetto SQL 查询刷新率变化事件
- **问题**：track_event 表名和 refreshRate 事件名可能与当前 Perfetto 版本不匹配
- **建议**：验证并更新 SQL 查询，或使用 Perfetto 的 display_refresh_rate track


## [Task9 Deep Review] 14.4 dumpsys 系列命令 — 2026-04-15
- **类型**：数据缺失
- **位置**：全章节
- **问题**：作为工具使用章节，没有一处真实的 dumpsys 输出样例。读者无法对照自己的输出判断是否正常，也无法理解关键字段在实际输出中的位置和格式
- **建议**：每个核心子命令（activity、meminfo、gfxinfo、window、batterystats、SurfaceFlinger）至少添加一个精简的真实输出片段（10-20 行），标注关键字段

## [Task9 Deep Review] 14.4 dumpsys 系列命令 — 2026-04-15
- **类型**：源码准确性
- **位置**：framestats 逐帧时间线说明
- **问题**：列名列表不完整，缺少 Flags、OldestInputEvent、NewestInputEvent、DequeueBufferDuration、QueueBufferDuration、GpuCompleted 等列。这些列在实战分析中都有用途（Flags 区分正常帧和异常帧，DequeueBufferDuration 反映 BufferQueue 等待时间）
- **建议**：补全列名列表，或至少标注"此处列出最关键的列，完整列表参见 AOSP Choreographer.java"

## [Task9 Deep Review] 14.4 dumpsys 系列命令 — 2026-04-15
- **类型**：版本差异
- **位置**：batterystats --enable full-wake-history
- **问题**：该参数在 Android 13+ 可能已不工作或行为变更，章节未提及版本限制
- **建议**：标注该参数适用的 Android 版本范围，Android 13+ 推荐替代方案

## [Task9 Deep Review] 14.4 dumpsys 系列命令 — 2026-04-15
- **类型**：版本差异
- **位置**：batterystats 功耗分析工作流
- **问题**：导出 bugreport 命令只提到 adb bugreport > bugreport.zip，未提及 Android 12+ 推荐使用 adb bugreportz（生成标准 zip 文件，速度更快）
- **建议**：补充 bugreportz 的用法说明和版本差异

## [Task9 Deep Review] 14.4 dumpsys 系列命令 — 2026-04-15
- **类型**：知识盲区
- **位置**：进阶用法
- **问题**：未提及 dumpsys --proto 输出格式（protobuf），该格式在自动化性能测试 CI/CD 中广泛使用
- **建议**：在进阶用法或实战部分补充 --proto 的用法和典型场景（如自动解析 meminfo 数据入库）

## [Task9 Deep Review] 14.4 dumpsys 系列命令 — 2026-04-15
- **类型**：交叉引用
- **位置**：gfxinfo 部分 JankStats 库提及
- **问题**：提到 JankStats 库（AndroidX）但未交叉引用 7.1 节（卡顿定义）或 7.5 节（优化策略），读者找不到后续阅读入口
- **建议**：添加"详见 §7.1 卡顿的定义与分类"和"§7.5 优化策略中 JankStats 的集成方法"
