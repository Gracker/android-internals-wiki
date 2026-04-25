# AIW 自动 Review 任务报告 (19.11)

## 一、目标发现结果
- 扫描范围：`src/part3-tools/ch19-apm/`
- 最终选择：19.11 JankStats
- 选择理由：JankStats 是 AndroidX 官方推荐的线上流畅性监控方案，技术链路涉及 Window、DecorView 以及底层的 FrameMetrics，具有较高的技术深度和实战价值。

## 二、总体结论
- 总体技术评分：4.2/5
- 是否建议回炉：否（P1 级建议可直接在下轮修正）
- 主要风险：对 `JankStats` 初始化时机（DecorView 依赖）的异常描述不够精确，且缺少对 `FrameData` 对象重用的性能提醒。
- 评分理由：内容覆盖了核心原理、版本差异和 Compose 场景，具备实战指导意义。但在源码细节（对象池优化）和极端边界（Window 状态切换）上仍有提升空间。
- 闭环建议：进入结构化修正队列，补充对象重用提醒和更精确的异常规避方案。

## 三、六维评分
| 维度 | 评分 | 问题数 |
|------|------|-------|
| 源码准确性 | 4.5/5 | 1 |
| 原理链完整性 | 4.0/5 | 1 |
| 版本差异覆盖 | 4.5/5 | 0 |
| 知识盲区 | 4.0/5 | 1 |
| 数据/案例支撑 | 4.0/5 | 0 |
| 交叉引用一致性 | 5.0/5 | 0 |

## 四、P0 问题（事实错误）
无

## 五、P1 问题（重要缺失）
- [P1][源码准确性][JankStats.createAndTrack 初始化时机]
- 原文问题：提到在 `setContentView()` 前初始化可能抛 `IllegalStateException`。
- 源码锚点：`androidx.metrics.performance.JankStats.createAndTrack` 调用 `window.getDecorView()`。
- 关键代码逻辑：`Activity` 的 `Window` 实现类（通常是 `PhoneWindow`）在 `getDecorView()` 时如果 `mDecor` 为 null，会触发 `installDecor()`。虽然通常不会抛异常，但在某些复杂的自定义 Window 场景或极早期的 `attachBaseContext` 阶段调用会返回 null 或导致非预期的 View 层级创建。
- 修正方向：建议明确说明“依赖 DecorView 的存在”，并推荐在 `onStart` 或 `setContentView` 之后初始化，而非仅笼统说明抛异常。

- [P1][知识盲区][FrameData 内部优化]
- 原文问题：未提及 `FrameData` 的对象重用机制。
- 源码锚点：`androidx.metrics.performance.JankStatsApi24Impl` 等实现类中对 `FrameData` 的构造。
- 缺失内容：JankStats 内部为了减少每帧回调带来的 GC 压力，对 `FrameData` 做了对象池优化（或通过复用字段减少分配）。开发者在回调中如果异步持有 `FrameData` 的引用，会导致读取到后续帧的数据。
- 建议补充方向：强制提醒开发者“不要异步持有 FrameData 引用”，必须拷贝出 DTO 数据，否则会导致数据污染。

## 六、P2 问题（建议改进）
- [P2][原理链完整性][JankStatsApi16Impl 降级方案]
- 原文问题：提到 API 16-23 使用“较粗的帧时间估算”。
- 建议：补充说明其底层是基于 `Choreographer.FrameCallback` 和 `ViewTreeObserver.OnPreDrawListener` 来模拟计算的，相比 `FrameMetrics` 缺少了渲染线程和 GPU 的真实反馈，因此在低版本上该数据不包含 GPU 耗时。

## 七、知识盲区清单
| 盲区 | 重要程度 | 建议研究方向 |
|---|---|---|
| FrameData 对象重用风险 | 高 | 源码中回调参数的生命周期 |
| 多 Window 监控冲突 | 中 | 一个 Activity 存在多个 Window（如 PopWindow/Dialog）时 JankStats 的覆盖范围 |

## 八、外部核验建议
- 搜索关键词：`androidx.metrics.performance source code`
- 建议查阅 `JankStatsApi24Impl.java` 中对 `OnFrameMetricsAvailableListener` 的具体封装逻辑。

## 九、可闭环输出

### 9.1 回炉问题单
- 章节：19.11
- 严重级别：P1
- 问题类型：源码错误/知识盲区
- 位置：初始化代码段及 FrameData 处理建议
- 问题描述：缺少 DecorView 依赖的精确描述和 FrameData 对象复用的风险提示。
- 建议修正方向：补充“禁止异步持有 FrameData 引用”的警告，并修正初始化时机的技术说明。

### 9.2 知识资产
- 关键源码路径：`androidx/metrics/performance/JankStats.kt`
- 技术结论：JankStats 本质上是 `FrameMetrics` (API 24+) 的包装器，而在 API 16-23 上则降级为 `Choreographer` 模拟。

## 十一、落盘信息
- 已写入文件：`logs/external-review/2026-04-25-15-11-external-review.md`
