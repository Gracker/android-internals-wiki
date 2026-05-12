# AIW 自动 Review 任务报告

## 一、目标发现结果
- 扫描范围：`src/part2-performance/ch07-smoothness/`
- 候选章节：
  1. `07-compose-performance.md` | 本次指定 review 目标，属于 Compose 性能优化核心章节。
- 最终选择：`src/part2-performance/ch07-smoothness/07-compose-performance.md`
- 选择理由：用户明确指定，且该章节目前处于 `ready-for-review` 状态，是 Task 9 深度技术复审的关键环节。
- 排除的高频原因：其他章节已完成或未标记为待技术复审。

## 二、总体结论
- 总体技术评分：3.0/5
- 是否建议回炉：是
- 主要风险：内容严重滞后于 2026 年的技术现状，遗漏了 Compose 1.7 - 1.10 版本中最重要的三项性能革新：Strong Skipping Mode、Pausable Composition 和 Baseline Profiles 的系统化应用。
- 评分理由：
  - **P0 级遗漏**：完全未提及 **Pausable Composition (1.10+)**。这是 Compose 2025 年最重要的性能飞跃，解决了长耗时重组导致的掉帧问题。
  - **P1 级滞后**：对 **Strong Skipping Mode (1.7+, Kotlin 2.0+)** 的描述仅停留在“自动发现”标注中，未将其作为核心优化思路重写，导致文中大量篇幅仍在强调手动处理稳定性（@Stable/@Immutable），这在 2026 年已非首选方案。
  - **P1 级缺失**：缺少 **Baseline Profiles** 的深度实战讲解。在 2026 年，不谈 Baseline Profiles 的 Compose 优化是不完整的。
  - **源码深度不足**：虽然提到了渲染三阶段，但未下钻到 `Recomposer`、`Snapshot` 和 `Composer` 的具体代码交互层级。
- 闭环建议：建议回炉，按 2026 年技术栈重构核心优化策略部分。
- 本轮 review 覆盖范围：全章内容，重点审查了重组机制、稳定性、动画和检测工具。
- 本轮未完成部分：无。

## 三、六维评分
| 维度 | 评分 | 问题数 |
|------|------|-------|
| 源码准确性 | 3.5/5 | 2 |
| 原理链完整性 | 2.5/5 | 3 |
| 版本差异覆盖 | 2.0/5 | 4 |
| 知识盲区 | 3.0/5 | 2 |
| 数据/案例支撑 | 3.5/5 | 1 |
| 交叉引用一致性 | 4.0/5 | 0 |

## 四、P0 问题（事实错误/严重过时）
- [P0][版本差异覆盖][全文]
- **原文问题**：文章将性能优化的核心几乎全部押注在“手动维护稳定性”上（@Stable, @Immutable）。
- **源码 / 一手资料锚点**：`androidx.compose.compiler.plugins.kotlin.lower.StrongSkippingMode`；[Android Developers Blog: Compose Compiler updates](https://android-developers.googleblog.com/2024/04/jetpack-compose-compiler-moving-to-kotlin-repo.html)
- **关键代码逻辑**：在 Strong Skipping 模式下，所有可重启的 Composable 均可跳过。不稳定参数使用 `===` (实例相等性) 比较，稳定参数使用 `equals()`。
- **运行原理说明**：这是 2025-2026 年 Compose 优化的分水岭。原文建议读者手动为 List 包装不可变集合或标注注解，这增加了大量开发成本。在 2026 年，应优先通过 Strong Skipping 解决。
- **建议修正方向**：将 Strong Skipping 模式提升为“稳定性优化”的首选章节，并将手动注解标记为“进阶微调手段”。

- [P0][原理链完整性][渲染模型章节]
- **原文问题**：对 Composition 阶段的描述仍然是“原子执行、不可中断”。
- **源码 / 一手资料锚点**：`androidx.compose.runtime.Recomposer` 中的 `setPausableContent` 和 `resume` 逻辑；[Compose 1.10 Release Notes]
- **运行原理说明**：Compose 1.10 引入了时间片轮转（Time-slicing）。如果重组即将耗尽帧预算（deadlineNanos），它会在 slot 边界处暂停，释放主线程。
- **为什么错**：文中说“如果重组耗时 30ms 就会掉帧”，在 1.10 默认开启 Pausable 后，这 30ms 会被自动拆分到 2-3 帧中执行，显著降低掉帧率。
- **建议修正方向**：增加“可暂停重组（Pausable Composition）”专节，解释其如何通过 `deadlineNanos` 实现增量执行。

## 五、P1 问题（重要缺失）
- [P1][知识盲区][性能检测工具章节]
- **原文问题**：完全未提及 Baseline Profiles。
- **缺失内容**：Baseline Profiles 是解决 Compose 首次启动卡顿（First-run Jank）和库执行效率的关键。
- **运行原理说明**：通过 Macrobenchmark 记录关键路径，生成二进制 Profile 并在安装时进行 AOT 编译。
- **建议补充方向**：在“性能检测”或“通用建议”中增加 Baseline Profiles 章节，明确其在生产环境的强制性。

- [P1][原理链完整性][Compose 动画性能]
- **原文问题**：未提及 Compose 1.9+ 的后台文本预取（Background Text Prefetch）和 `CacheWindow` API。
- **建议补充方向**：在 LazyColumn 优化部分补充 `CacheWindow` 如何配合 Pausable Composition 提升滚动预取成功率。

## 六、P2 问题（建议改进）
- [P2][源码准确性][重组本质]
- **原文位置**：`Greeting` 编译后代码示例。
- **建议**：建议补充 `$changed` 位运算的简要说明，说明 Compose 如何通过一个 `Int` 存储多个参数的变化状态，这是实现“智能重组”的高效底层设计。

## 七、知识盲区清单
| 盲区 | 重要程度 | 建议研究方向 |
|------|----------|--------------|
| Pausable Composition 状态恢复机制 | 高 | 研究 SlotTable 在暂停点如何保存上下文，以及是否会造成过期的状态读取。 |
| Strong Skipping 与 Lambda Memoization | 中 | 深入研究编译器如何自动为捕获不稳定变量的 Lambda 包裹 remember。 |
| LookaheadScope 性能边界 | 中 | 研究其在复杂共享元素动画中对 Layout 阶段耗时的具体影响。 |

## 八、外部核验建议
- **搜索关键词**：`Jetpack Compose 1.10 Pausable Composition source code`
- **建议查阅**：
  1. `cs.android.com` 搜索 `androidx/compose/runtime/Recomposer.kt` 寻找 `shouldPause` 逻辑。
  2. 查阅 `shreyaspatil.dev` 对 PausableComposition 的深度解析博文。
  3. 查看 Kotlin 官方关于 `composeCompiler` 配置项的最新文档。

## 九、可闭环输出

### 9.1 回炉问题单（必须修）
- **章节**：7.7 Jetpack Compose 性能优化
- **严重级别**：P0
- **问题类型**：原理描述严重滞后
- **位置**：渲染模型、稳定性优化章节
- **问题描述**：遗漏了 1.10 的 Pausable Composition 和 1.7+ 的 Strong Skipping Mode 核心机制，导致优化建议过时。
- **建议修正方向**：重写“稳定性”章节，将 Strong Skipping 作为默认推荐；新增“Pausable Composition”原理专节。

- **章节**：7.7 Jetpack Compose 性能优化
- **严重级别**：P1
- **问题类型**：关键技术点缺失
- **位置**：性能检测与通用建议
- **问题描述**：缺失 Baseline Profiles 的实战讲解。
- **建议修正方向**：增加专节说明 Baseline Profiles 的生成、注入与 AOT 编译原理。

### 9.2 知识盲区清单（供后续研究）
- **盲区描述**：Compose 1.9 引入的 `CacheWindow` API 对 Lazy 预取的影响。
- **重要程度**：高
- **建议研究方向**：结合 Pausable Composition，研究其如何量化预取窗口以平衡内存与流畅度。

### 9.3 一般建议清单（非阻断）
- **问题类型**：案例支撑不足
- **位置**：Perfetto 分析部分
- **建议**：补充 1.10 版本下，Pausable Composition 暂停/恢复在 Perfetto Slice 中的具体特征图（通常表现为 `compose` 切片被拆分为多个非连续片段）。

### 9.4 可复用知识资产
- **一手资料**：`androidx.compose.runtime.Recomposer`
- **关键源码路径**：`androidx/compose/runtime/Recomposer.kt`
- **关键类 / 方法**：`setPausableContent`, `PausedComposition.resume`
- **技术结论**：2026 年的 Compose 性能核心已从“规避重组”转向“平滑重组（Pausable）”和“自动化稳定性推断（Strong Skipping）”。
- **价值**：这是 Compose 走向完全成熟、替代传统 View 系统的底层信心来源。

## 十、下一候选章节
- `src/part2-performance/ch07-smoothness/08-flutter-performance.md` (如有) 或继续深挖 `07.3-perfetto-analysis.md` 中关于 Compose 1.10 的 Trace 特征。

## 十一、落盘信息
- 已写入文件：`logs/external-review/2026-04-19-10-07-compose-performance-external-review.md`
