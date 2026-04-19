# AIW 自动 Review 任务报告 (Gemini 外部审计)

## 一、目标发现结果
- **扫描范围**：`src/part2-performance/ch08-responsiveness/`
- **目标章节**：`01-responsiveness-principles.md` (响应速度原理)
- **选择理由**：该章节处于 `task9_pending` 状态，是响应速度模块的基石，涉及大量系统级底层原理，迫切需要源码级和版本差异（Android 15/16）的核验。

## 二、总体结论
- **总体技术评分**：3.5/5
- **是否建议回炉**：**是** (建议进行结构化补强)
- **主要风险**：内容虽涵盖了经典原理（RAIL, Input 路径），但对 **Android 15/16 的重大变革（ADPF GPU 报告、ARR 自适应刷新率、ApplicationStartInfo）** 覆盖极少，且遗漏了 **Input Predictor** 这一关键补偿机制。
- **闭环建议**：需补充 Android 15/16 现代性能架构内容，并将感知速度优化从“技巧层”提升到“系统预测层”。

## 三、六维评分
| 维度 | 评分 | 问题数 |
|------|------|-------|
| 源码准确性 | 5/5 | 0 |
| 原理链完整性 | 3.5/5 | 2 (P1) |
| 版本差异覆盖 | 2/5 | 2 (P1) |
| 知识盲区 | 3/5 | 1 (P1) |
| 数据/案例支撑 | 4/5 | 1 (P2) |
| 交叉引用一致性 | 5/5 | 0 |

## 四、P1 问题（重要缺失）

### 1. [P1][版本差异][启动响应] 遗漏 Android 15 `ApplicationStartInfo` API
- **原文位置**：Android Vitals 中的响应速度指标 -> 启动时间
- **原文问题**：仅提到了传统的 TTID/TTFD，未提及 Android 15 引入的 `ApplicationStartInfo`。
- **源码/一手资料锚点**：`android.app.ApplicationStartInfo`, `ActivityManagerService.reportStartInfo()`
- **运行原理说明**：Android 15 允许应用通过 `getHistoricalProcessStartInfo()` 获取详细的启动诊断数据（启动原因、温度、每个阶段的精确耗时）。这是目前诊断启动响应速度最权威的 AOSP API。
- **建议修正方向**：在 TTID/TTFD 小节后增加“现代启动诊断：ApplicationStartInfo”小段，说明其对定位“响应慢”根因的价值。

### 2. [P1][原理/版本] 遗漏 ARR (Adaptive Refresh Rate) 对响应抖动（Jitter）的解决
- **原文位置**：系统级响应路径 -> 路径中的瓶颈分布
- **原文问题**：提到 Jitter 问题，但未提及 Android 15/16 解决 Jitter 的核心技术——ARR。
- **源码/一手资料锚点**：`Display.hasArrSupport()`, `Display.getSuggestedFrameRate()`
- **运行原理说明**：传统的 VSync 是固定频率，高刷切换易导致 Jank。Android 15+ 引入 ARR，允许在不切换 Mode 的情况下动态调整 VSync 步长。
- **建议修正方向**：在“抖动问题”后补充 ARR 的作用，说明它是如何通过自适应 VSync 减少由于帧率不匹配导致的响应延迟波动。

### 3. [P1][知识盲区] 遗漏 Input Predictor (MotionPredictor) 补偿机制
- **原文位置**：系统级响应路径 -> 第一步：Input 事件的捕获与分发
- **原文问题**：描述了从硬件到 App 的被动分发，遗漏了系统的“预测”主动优化。
- **源码/一手资料锚点**：`android.view.MotionPredictor` (Android 14+ 强化)
- **运行原理说明**：系统利用 Kalman 滤波或其他算法预测手指/手写笔的下一个位置，提前 10-20ms 进行渲染准备，从而在物理上抵消一部分硬件延迟。
- **建议修正方向**：在 Input 分发小节增加“预测性响应：MotionPredictor”内容。

## 五、P2 问题（建议改进）

### 1. [P2][数据支撑] 细化“容量不足”与“抖动”在 Perfetto 中的量化指标
- **原文位置**：路径中的瓶颈分布
- **建议**：建议引入 ADPF (Android Dynamic Performance Framework) 的概念。Android 15 现在支持报告 GPU 任务时长（Hint Session），这直接解决了“容量预测”的问题。

## 六、知识盲区清单
| 盲区 | 重要程度 | 建议研究方向 |
| :--- | :--- | :--- |
| **ADPF Hint Session (GPU)** | 高 | 研究 Android 15 如何通过 `PerformanceHintManager` 报告 GPU 工作时长以优化响应速度。 |
| **ProfilingManager** | 中 | Android 15 引入的自动触发 Perfetto 机制，用于捕捉生产环境的响应速度异常。 |
| **16KB Page Size** | 低 | Android 15/16 内存页大小变化对底层 I/O 响应的影响（虽然主要影响启动，但涉及整机响应）。 |

## 七、外部核验建议
- **搜索关键词**：`Android 15 ApplicationStartInfo developer guide`
- **搜索关键词**：`Android 16 Adaptive Refresh Rate RecyclerView 1.4`
- **源码路径**：`frameworks/base/core/java/android/app/ApplicationStartInfo.java`
- **官方文档**：`developer.android.com/about/versions/15/features/profiling`

## 八、可闭环输出

### 9.1 回炉问题单
1. **章节**：8.1 响应速度原理
2. **严重级别**：P1
3. **问题类型**：版本差异/原理断裂
4. **描述**：缺少 Android 15/16 的 ADPF、ARR 和 ApplicationStartInfo 关键内容。
5. **修正方向**：在对应小节插入这些新特性的原理说明，重点放在它们如何解决文中提到的 Jitter 和容量问题。

### 9.2 可复用知识资产
- **知识点**：华为交互流畅性量化标准。
- **来源**：HarmonyOS 性能体验设计规范。
- **结论**：点击 ≤ 100ms, 抛滑 ≤ 80ms, 拖滑 ≤ 60ms。这些数据可直接用于文中“度量维度”小节。
- **源码锚点**：`frameworks/native/services/inputflinger/` (确认 AOSP 侧 input 处理路径未发生结构性重构)。

## 九、下一候选章节
- `src/part2-performance/ch08-responsiveness/02-anr-mechanism.md` (ANR 机制，作为原理的延伸)

## 十、落盘信息
- **已写入文件**：`logs/external-review/2026-04-19-10-01-responsiveness-principles-external-review.md`
