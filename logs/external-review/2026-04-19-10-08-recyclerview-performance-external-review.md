# AIW 自动 Review 任务报告

## 一、目标发现结果
- **扫描范围**：`src/part2-performance/ch07-smoothness/`
- **候选章节**：
  1. `08-recyclerview-performance.md` | 状态：ready-for-review，且涉及大量 AndroidX 与 AOSP 交叉机制，是典型的性能深水区。
- **最终选择**：`08-recyclerview-performance.md`
- **选择理由**：RecyclerView 是 Android 流畅性的核心组件，且当前稿件涉及了最新的 Android 15/16 适配（ARR）以及深层 Trace 分析，技术核验价值极高。

## 二、总体结论
- **总体技术评分**：3.8/5
- **是否建议回炉**：是
- **主要风险**：虽然覆盖了大多数核心知识点，但在 GapWorker 预取的量化逻辑、Step 1 的 Pre-layout 机制深度、以及 ARR 的版本分界线上描述不够精确。
- **评分理由**：存在 3 处 P1 级重要缺失和 1 处 P0 级事实描述偏差。
- **本轮 review 覆盖范围**：布局三阶段、四级缓存、GapWorker 预取、DiffUtil 增量更新、ARR 适配、Perfetto 分析 SQL。
- **本轮未完成部分**：自定义 LayoutManager 的滑动距离计算与回收逻辑（`fill()` 方法深度审计）留待下一轮。

## 三、六维评分
| 维度 | 评分 | 问题数 |
|------|------|-------|
| 源码准确性 | 3.5/5 | 1 (P0) |
| 原理链完整性 | 3.5/5 | 2 (P1) |
| 版本差异覆盖 | 4.0/5 | 1 (P1) |
| 知识盲区 | 4.5/5 | 0 |
| 数据/案例支撑 | 4.0/5 | 0 |
| 交叉引用一致性 | 5.0/5 | 0 |

## 四、P0 问题（事实错误）
- **[P0][源码准确性][RecycledViewPool 共享]**
- **原文问题**：文中提到 `setRecycleChildrenOnDetach(true)` 属于 `LinearLayoutManager`，`GridLayoutManager` 也能直接复用。
- **核验结论**：虽然 `GridLayoutManager` 继承自 `LLM`，但该 API 在嵌套场景下的核心作用是配合 `RecycledViewPool` 的解绑。更关键的事实是：如果子 RecyclerView 被销毁（Detach）但没有设置 `sharedPool`，这些 View 将被直接丢弃。
- **建议修正方向**：强调 `setRecycleChildrenOnDetach` 必须与共享 Pool 强绑定，否则开启后反而可能导致由于 Detach 过于激进导致的重新 Inflate 开销。

## 五、P1 问题（重要缺失）
- **[P1][原理链完整性][GapWorker 预取准入]**
- **原文问题**：提到 `willBindInTime` 读取运行平均耗时，但未说明算法细节。
- **源码锚点**：`androidx.recyclerview.widget.GapWorker` / `RecyclerView.RecycledViewPool.ScrapData`
- **关键代码逻辑**：`mBindRunningAverageNs = (mBindRunningAverageNs / 4 * 3) + (newValue / 4)`。
- **缺失内容**：RecyclerView 使用的是 **3/4 权重的滑动平均（Running Average）**，而不是简单的平均值。
- **为什么这是重要缺失**：这决定了预取机制对“突发性重布局”的反应灵敏度。如果新的一帧 Bind 突然变久，预取会迅速感知并关停，防止卡顿扩散。建议补充这一算法细节。

- **[P1][版本差异覆盖][ARR 适配逻辑]**
- **原文问题**：提到 RecyclerView 1.4.0 支持 ARR，但对 API 级别描述模糊。
- **一手资料锚点**：AndroidX RecyclerView 1.4.0 Release Notes (2025-01-15)；`android.view.View#setFrameContentVelocity`。
- **缺失内容**：明确 ARR 功能生效的前提是 **`compileSdk 35` (Android 15)**。
- **建议补充方向**：说明 RecyclerView 内部通过 `Api35Impl` 类进行版本隔离，只有在 Android 15 及以上设备且滚动速度发生变化时，才会触发速度上报。

- **[P1][原理链完整性][Stride Jitter 补偿]**
- **原文问题**：提到 VSync 时间精度导致的步幅波动。
- **缺失内容**：缺少工程层面的闭环改进建议。
- **建议补充方向**：在“无掉帧卡顿”一节，应补充 **“亚像素位移补偿（Sub-pixel Remainder Compensation）”** 方案。即：在 `scrollBy` 时，手动维护一个 `float` 残差，确保长期的像素步进与物理时间戳完美对齐。

## 六、P2 问题（建议改进）
- **[P2][源码准确性][Trace 断面名称]**
- **原文问题**：文中提到 `RV onCreateViewHolder type=0x%X`。
- **证据依据**：AOSP `RecyclerView.java` 源码。
- **描述**：该标签仅在 `VERBOSE_TRACING` 开启时出现。在标准发布版中，对应的 Trace 通常为 `RV CreateView` 和 `RV BindView`。
- **建议**：补充说明 Trace 名称可能随 AndroidX 版本或调试配置变化。

## 七、知识盲区清单
| 盲区 | 重要程度 | 建议研究方向 |
|------|------|-------|
| Prefetch 与自定义 LayoutManager 的对接 | 中 | 研究 `LayoutManager.collectAdjacentPrefetchPositions` 的实现要求 |
| 144Hz/165Hz 高刷新率下的 GapWorker 表现 | 低 | 测试极短 Gap 时间（<2ms）下的预取放弃率 |

## 八、外部核验建议
- **搜索关键词**：`RecyclerView GapWorker willBindInTime implementation`
- **建议来源**：`cs.android.com` 搜索 `ScrapData` 内部类。
- **搜索关键词**：`RecyclerView 1.4.0 Adaptive Refresh Rate release notes`
- **建议来源**：`developer.android.com` 查看正式版变更日志。

## 九、可闭环输出

### 9.1 回炉问题单
- **章节**：7.8 RecyclerView 滑动优化
- **级别**：P1
- **类型**：原理断裂
- **位置**：GapWorker 预取机制
- **问题描述**：遗漏了滑动平均（3/4 权重）的量化逻辑。
- **建议修正方向**：加入该公式，并解释其在“性能感知与自我调节”中的设计意图。

### 9.2 知识资产
- **源码锚点**：`androidx.recyclerview.widget.GapWorker`
- **关键路径**：`GapWorker.java` -> `prefetchPositionWithDeadline()`
- **技术结论**：预取不仅依赖时间戳，更依赖 `willCreateInTime` 和 `willBindInTime` 对历史成本的实时评估。
- **资产价值**：解释了为什么有时候 Trace 里有预取动作但没有后续 Bind，这是系统在“舍车保帅”防止卡顿。

## 十、下一候选章节
- `src/part2-performance/ch07-smoothness/09-custom-view-optimization.md`（如果存在）

## 十一、落盘信息
- **已写入文件**：`logs/external-review/2026-04-19-10-08-recyclerview-performance-external-review.md`
