# AIW 自动 Review 任务报告

## 一、目标发现结果
- 扫描范围：`src/part3-tools/ch14-other-tools/08-gpu-debug-tools.md`
- 候选章节：`14.8 GPU 图形调试与分析工具`
- 最终选择：`14.8 GPU 图形调试与分析工具`
- 选择理由：属于待技术复审的章节，涵盖 AGI, RenderDoc, Sokatoa 等高优性能分析工具。

## 二、总体结论
- 总体技术评分：4.0/5
- 是否建议回炉：是（建议局部回炉修正事实）
- 主要风险：AGI 基于 GFXReconstruct 重构的路线图存在较高事实风险，且 Android 17 ANGLE 的系统行为描述需要与 AOSP 强对齐。
- 评分理由：文章整体结构清晰，工具选型对比具有极高的实战价值，但在 AGI 2026 路线图和 ANGLE 行为的绝对断言上缺乏源码/官方确凿证据（存在 1 个 P0 风险，2 个 P1）。
- 闭环建议：进入结构化修正队列，重点核实 AGI 路线图。
- 本轮 review 覆盖范围：全章工具定性与选型，Perfetto/AGI 使用，实战案例。

## 三、六维评分
| 维度 | 评分 | 问题数 |
|------|------|-------|
| 源码准确性 | 3.5/5 | 1 |
| 原理链完整性 | 4.5/5 | 0 |
| 版本差异覆盖 | 4.0/5 | 1 |
| 知识盲区 | 4.0/5 | 1 |
| 数据/案例支撑 | 4.0/5 | 1 |
| 交叉引用一致性 | 4.5/5 | 0 |

## 四、P0 问题（事实错误）
- [P0][源码准确性][AGI 2025-2026 路线图]
- **原文问题**：断言 AGI "2026 H2：高级 Frame Profiler Alpha。基于 GFXReconstruct 重建"。
- **核验结论**：AGI 传统上基于 GAPID 的追踪框架。虽然 Samsung Sokatoa 基于 GFXReconstruct，但官方层面 Google 是否将 AGI 的 Frame Profiler 底层完全切换为 GFXReconstruct 存在极大的事实风险。如果这是 2026 年的预判，需补充确凿的官方 issue 或源码提交记录。
- **建议修正方向**：如果查不到 Google 官方关于 AGI 切换 GFXReconstruct 的声明，请移除该断言，或明确标注为 "社区推测/Sokatoa 路线" 而非 AGI 路线。

## 五、P1 问题（重要缺失）
- [P1][版本差异覆盖][AGI 对 GLES 应用的分析路径]
- **原文问题**：描述 "Android 17 将 ANGLE 从 allowlist 转向 denylist"。
- **缺失内容**：Android 15 已经开始将 ANGLE 作为默认的 GLES 驱动（Developer Options 中有相关切换），到 Android 16/17 是强制行为。描述应当更准确地反映这个渐进过程，而不是仅提 Android 17。
- **建议补充方向**：明确 Android 15/16 期间 ANGLE 作为默认选项的过程。

- [P1][知识盲区][GPU Profiling 的性能开销]
- **原文问题**：提到了 AGI 帧捕获会有显著影响，但未提及 AGI System Profiler 采集 GPU Counter 时的驱动层开销。
- **缺失内容**：某些 Mali GPU 在高频轮询 GPU Counter 时，会引发微小的 CPU 侧中断开销。
- **建议补充方向**：补充说明 System Profiler 在极高采样率下可能引起的 CPU 扰动。

## 六、P2 问题（建议改进）
- [P2][数据/案例支撑][案例 1：UI 渲染中的 GPU 带宽瓶颈]
- **原文问题**："待验证：具体优化数据来自类似场景的经验，非本案例实测"。
- **问题描述**：使用编造的数据降低了可信度。
- **建议**：建议使用一个真实的开源项目（如 Plaid 或 Now in Android）的真实 trace 截图和带宽降低比例。

## 七、知识盲区清单
| 盲区 | 重要程度 | 建议研究方向 |
|------|----------|--------------|
| AGI 底层架构演进 | 高 | 确认 AGI 是否正在或者已经合入 GFXReconstruct 相关代码 (cs.android.com 搜索 AGI 源码) |
| Android 16/17 ANGLE 强制策略细节 | 中 | AOSP 中关于 `ro.gfx.angle.supported` 和默认驱动选择的属性变化逻辑 |

## 八、外部核验建议
- 搜索关键词：`"Android GPU Inspector" "GFXReconstruct"`
- 搜索关键词：`AOSP angle default driver android 15 16 17`

## 九、可闭环输出

### 9.1 回炉问题单（必须修）
- **章节**：14.8
- **严重级别**：P0
- **问题类型**：源码/事实错误
- **位置**：AGI 2025-2026 路线图
- **问题描述**：断言 AGI 将基于 GFXReconstruct 重建，疑似幻觉，需官方证据或删除。
- **建议修正方向**：核实并修改。

### 9.2 可复用知识资产（高价值新增知识）
- **章节**：14.8
- **可复用的技术结论**：Frame Profiler 与 System Profiler 的选型边界极其清晰（宏观定位看 System/Perfetto，微观 Draw Call 看 Frame Profiler/RenderDoc），这段论述可以被提取为标准的 GPU 分析 SOP。