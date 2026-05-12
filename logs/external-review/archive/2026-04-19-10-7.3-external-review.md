# AIW 自动 Review 任务报告

## 一、目标发现结果
- 扫描范围：`src/part2-performance/ch07-smoothness/`
- 最终选择：`src/part2-performance/ch07-smoothness/03-jank-methodology.md`
- 选择理由：该章节作为“卡顿分析方法论”的核心，技术权重极高，且正处于 `pipeline_stage: task9_pending` 阶段。其内容直接决定了读者在实战中的分析路径，必须确保源码级准确性和版本时效性。

## 二、总体结论
- 总体技术评分：3.5/5
- 是否建议回炉：是
- 主要风险：存在 1 处 P0 级 SQL 语义错误；严重缺失 Android 15/16/17 版本演进内容；Choreographer 流水线描述不完整。
- 评分理由：文章框架清晰， Checklist 极具实战价值，但在底层源码细节（如线程状态语义）和最新 API 追踪上存在滞后，作为深度技术手册需进一步对齐 AOSP 最新行为。
- 闭环建议：建议回炉修正 P0/P1 问题，特别是补充 Android 16 的 `AppJankStats` 和调度延迟的正确 SQL 表达。

## 三、六维评分
| 维度 | 评分 | 问题数 | 说明 |
|------|------|-------|------|
| 源码准确性 | 3/5 | 1 (P0) | SQL 状态位描述有误，Choreographer 阶段缺失。 |
| 原理链完整性 | 4/5 | 1 (P1) | 基础流程闭环，但缺失现代 Android 的回调阶段。 |
| 版本差异覆盖 | 2/5 | 2 (P1) | 止步于 Android 12，完全缺失 15/16/17 核心特性。 |
| 知识盲区 | 3.5/5 | 1 (P2) | 对 ADPF 的进阶用法和线上自动 Trace 提及不足。 |
| 数据/案例支撑 | 4.5/5 | 0 | 引用了高爷的大量实战案例，支撑力强。 |
| 交叉引用一致性 | 5/5 | 0 | 与 7.1/7.2 及 2.x 章节引用关系紧密。 |

## 四、P0 问题（事实错误）
- [P0][源码准确性][SQL 查询部分]
- **原文问题**：在 SQL 查询段落中，注释称 `sched.end_state = 'R'` 表示线程被抢占（Preempted）。
- **源码 / 一手资料锚点**：[Perfetto Documentation - Sched Table](https://perfetto.dev/docs/analysis/sql-tables#sched)
- **关键代码逻辑**：在 Linux 内核调度中，`R` 状态表示线程处于就绪队列但被换出。Perfetto 将被高优先级任务强制踢下 CPU 的状态专门标记为 `'R+'`。
- **运行原理说明**：`R` 可能只是时间片耗尽或自愿让出，而 `R+` 才是明确的 CPU 资源争抢信号。
- **核验结论**：原文解释混淆了“就绪”与“抢占”，会导致开发者在分析时过度诊断 CPU 竞争。
- **建议修正方向**：将 SQL 条件修正为 `end_state = 'R+'` 以准确识别抢占，或在文中明确区分 `R` 和 `R+` 的语义差异。

## 五、P1 问题（重要缺失）
- [P1][版本差异覆盖][全文演进]
- **原文问题**：缺失 Android 15/16/17 的核心流畅性特性。
- **缺失内容**：
    1. **Android 15**: ADPF 的 GPU/CPU 实际工作时长报告，以及 `ProfilingManager` API（生产环境自动触发堆栈/Trace）。
    2. **Android 16**: **Adaptive Refresh Rate (ARR)** 及其对 RecyclerView 1.4 的原生支持；新增 **`AppJankStats`** API（比 FrameMetrics 更细粒度）；`FrameMetrics.FRAME_TIMELINE_VSYNC_ID`（打通跨进程帧追踪的钥匙）。
    3. **Android 17**: **MessageQueue 无锁优化（DeliQueue）** 对主线程抖动的影响；`MemoryLimiter` 触发的自动分析。
- **为什么这是重要缺失**：这些特性改变了现代 Android 性能优化的游戏规则（从手动抓 Trace 到系统自动反馈和 ADPF 智能调度）。

- [P1][原理链完整性][Choreographer 阶段]
- **原文问题**：流水线描述仅包含 Input/Animation/Traversal。
- **缺失内容**：`CALLBACK_INSETS_ANIMATION` (API 30+) 和 `CALLBACK_COMMIT` (API 23+)。
- **源码锚点**：`android.view.Choreographer.java` 中的 `CALLBACK_*` 常量定义及 `doFrame` 循环逻辑。
- **建议补充方向**：补齐这两个阶段，特别是 `COMMIT` 阶段在性能监控（修正时间戳）中的角色。

## 六、P2 问题（建议改进）
- [P2][知识盲区][FrameMetrics 判定细节]
- **原文问题**：建议补充 FrameMetrics 在 API 31 之前手动计算 deadline 的一个关键缺陷：它无法识别系统正在利用“三级缓冲”来消化瞬时波动的意图。
- **建议**：在对比 `DEADLINE` API 时，强调原生 `DEADLINE` 包含了 SurfaceFlinger 对 VSync Offset 的动态调整，这是手动计算 `1000/refreshRate` 永远无法覆盖的。

## 七、知识盲区清单
| 盲区 | 重要程度 | 建议研究方向 |
|------|------|-------|
| ADPF Hint Session 实战 | 高 | 研究 App 如何通过 ADPF 告知系统工作负载以避免随机掉帧。 |
| Android 16 System-triggered Profiling | 中 | 研究系统如何在检测到卡顿时自动触发并保存 Trace 到 `/data/misc/perfetto-traces`。 |
| Android 17 DeliQueue 机制 | 中 | 深入 AOSP 源码分析 MessageQueue 无锁化对 Handler 消息延迟的改善程度。 |

## 八、外部核验建议
- **搜索关键词**：`AppJankStats Android 16`, `FRAME_TIMELINE_VSYNC_ID usage`, `ADPF setThreadsPowerEfficiencyMode`, `sched.end_state R+ vs R`.
- **建议来源**：
    - `cs.android.com`：查看 `AppJankStats.java` 和 `FrameTimeline.cpp`。
    - `perfetto.dev`：查看 SQL 分析中的 `sched` 表语义。
    - `developer.android.com`：关注 ADPF 和 Android 16 Beta 版本的新 API 说明。

## 九、可闭环输出

### 9.1 回炉问题单（必须修）
- **章节**：7.3 卡顿分析方法论
- **严重级别**：P0
- **问题类型**：源码错误 / 语义误导
- **位置**：SQL 查询部分，关于 `end_state = 'R'` 的解释。
- **问题描述**：错误将 `R` 解释为抢占（Preempted），混淆了正常的就绪排队与异常的优先级争抢。
- **建议修正方向**：修正为 `R+` 或补充两者的语义对照。

### 9.2 知识资产补充（供后续研究）
- **章节**：7.3
- **盲区描述**：Android 16 引入的 `AppJankStats` 如何取代部分 `FrameMetrics` 职责。
- **建议补充方向**：在 FrameMetrics 章节后增加“未来演进：AppJankStats”小节。

### 9.3 可复用知识资产
- **一手资料**：[Android 16 API Preview - AppJankStats](https://developer.android.com/reference/android/app/jank/AppJankStats)
- **关键源码路径**：`frameworks/base/core/java/android/view/Choreographer.java` (CALLBACK 顺序)
- **版本差异摘要**：
    - Android 12: `FrameMetrics.DEADLINE`, `FrameTimeline` Trace Track.
    - Android 15: ADPF GPU/CPU duration reporting.
    - Android 16: `FRAME_TIMELINE_VSYNC_ID`, `AppJankStats`, ARR (Adaptive Refresh Rate).
    - Android 17: Lock-free MessageQueue.

## 十、下一候选章节
- `src/part2-performance/ch07-smoothness/04-typical-scenarios.md` (将本章节的方法论应用到具体案例中，需核验案例的 Trace 表现是否符合新版本特征)。

## 十一、落盘信息
- 已写入文件：`logs/external-review/2026-04-19-10-03-jank-methodology-external-review.md`
