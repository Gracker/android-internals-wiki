# AIW 自动 Review 任务报告

## 一、目标发现结果
- **扫描范围**：`src/part2-performance/ch08-responsiveness/`
- **候选章节**：
  1. `09-game-performance.md` | 状态：ready-for-review，涉及多个 API 版本演进，技术密度高。
- **最终选择**：`src/part2-performance/ch08-responsiveness/09-game-performance.md`
- **选择理由**：游戏性能是 Android 12+ 的重点建设领域，涉及最新的 ADPF 和 Android 16/17 平台特性，需要源码级核验确保不误导读者。

## 二、总体结论
- **总体技术评分**：4.2/5
- **是否建议回炉**：否（建议结构化修正即可）
- **主要风险**：对 Android 17 的最新游戏特性覆盖略显单薄，部分 AOSP 硬编码细节（如超时时间）未点透。
- **评分理由**：章节结构完整，原理链清晰，正确区分了 Game Mode、Game State、ADPF 和 Interventions 的边界。源码路径和 API 版本标注基本准确。
- **本轮 review 覆盖范围**：Game Mode/State API 源码逻辑、Android 16 Headroom API、Android 17 性能观测、AGDK 工具链。
- **本轮未完成部分**：VRR（可变刷新率）与 Game Mode 的深度联动策略（需结合 SurfaceFlinger 源码深挖）。

## 三、六维评分
| 维度 | 评分 | 问题数 |
|------|------|-------|
| 源码准确性 | 4.5/5 | 1 |
| 原理链完整性 | 4.0/5 | 1 |
| 版本差异覆盖 | 4.5/5 | 1 |
| 知识盲区 | 4.0/5 | 2 |
| 数据/案例支撑 | 4.0/5 | 1 |
| 交叉引用一致性 | 5.0/5 | 0 |

## 四、P0 问题（事实错误）
*暂无 P0 级别事实错误。*

## 五、P1 问题（重要缺失）
- **[P1][源码准确性][2.3 Game Mode 对系统行为的影响]**
  - **原文问题**：提到“在一个受限时长内打开加载期 boost”，未说明具体时长。
  - **源码锚点**：`frameworks/base/services/core/java/com/android/server/app/GameManagerService.java` 中的 `LOADING_BOOST_MAX_DURATION` 常量。
  - **关键代码逻辑**：AOSP 硬编码为 `5000` 毫秒。当 `setGameState(isLoading=true)` 触发时，系统开启 `Mode.GAME_LOADING` 并启动延迟消息，5秒后强制回退。
  - **建议修正方向**：明确指出 AOSP 默认的 5s 超时限制，提醒开发者加载过程若超过 5s 需考虑分段上报或注意 boost 消失。

- **[P1][版本差异覆盖][6. Android 16 与 Android 12/13+ 的平台变化]**
  - **原文问题**：Android 17 仅提到了 Generational GC。
  - **缺失内容**：Android 17 (API 37) 引入的 `preferredFrameRateCategory` 在 `WindowManager` 中的重要性。
  - **运行原理说明**：游戏现在可以通过 `Window` 级别声明 `FRAME_RATE_CATEGORY_HIGH`，让系统更智能地处理 LTPO 屏幕的动态刷新率切换，而非硬编码刷新率。
  - **建议补充方向**：在 Android 17 章节补充 `preferredFrameRateCategory` 对游戏 VRR 适配的简化意义。

## 六、P2 问题（建议改进）
- **[P2][知识盲区][5. Perfetto 中的关键 Track]**
  - **问题描述**：虽然提到了 `power.hint_session`，但未点明这是 Android 17 针对 ADPF 可视化增强的核心轨道。
  - **建议**：补充在 Perfetto 中 `power.hint_session` 轨道直接对比 `Target Duration` vs `Actual Duration` 的调试方法，这是 ADPF 调优的“第一现场”。

- **[P2][数据/案例支撑][5.2 关键分析路径]**
  - **问题描述**：对 `SurfaceView` vs `TextureView` 在游戏场景下的具体性能差异缺乏“为什么”的底层解释。
  - **建议**：补充 `SurfaceView` 拥有独立 Hardware Layer、绕过 `ViewRootImpl` 绘制流程、支持零拷贝呈现的结论，解释其为何是游戏首选。

## 七、知识盲区清单
| 盲区 | 重要程度 | 建议研究方向 |
|------|----------|--------------|
| VRR (Variable Refresh Rate) 调度 | 高 | 研究 Android 15/16 对 `setFrameRate` 与 `preferredFrameRateCategory` 的冲突处理逻辑 |
| `sched_ext` 游戏自定义调度 | 中 | 调研 Android 17 实验性支持的 BPF 调度器在重负载游戏中的表现 |
| Game Text Input 延迟优化 | 低 | 确认 `GameActivity` 如何通过独立线程处理软键盘输入以减少对渲染的影响 |

## 八、外部核验建议
- **搜索关键词**：`site:cs.android.com GameManagerService LOADING_BOOST_MAX_DURATION`
- **建议查阅**：`frameworks/base/core/java/android/view/WindowManager.java` 中关于 `FRAME_RATE_CATEGORY_*` 的定义（Android 15+）。
- **建议查阅**：Perfetto 官方文档中关于 `android_power_rails` 和 `adpf_hint_session` 的 SQL 查询示例。

## 九、可闭环输出

### 9.1 回炉问题单（必须修）
- **章节**：8.9
- **严重级别**：P1
- **问题类型**：源码缺失 / 版本差异
- **位置**：2.3 节与 6 节
- **问题描述**：缺失 `GAME_LOADING` boost 的 5s 硬编码时长；缺失 Android 17 `preferredFrameRateCategory` 对 VRR 的支持。
- **建议修正方向**：明确 5s 超时逻辑；新增 Android 17 帧率类别 API 说明。

### 9.2 知识盲区清单（供后续研究）
- **章节**：8.9
- **盲区描述**：VRR 与 `preferredFrameRateCategory` 的协同机制。
- **重要程度**：中
- **建议研究方向**：SurfaceFlinger 内部对 Category 映射到具体刷新率的权重算法。

### 9.3 一般建议清单（非阻断）
- **章节**：8.9
- **位置**：5.2 节分析路径
- **问题描述**：`SurfaceView` 的性能优势解释不够“Under the hood”。
- **建议**：增加关于独立 Hardware Layer 和独立 BufferQueue 的底层优势说明。

### 9.4 可复用知识资产
- **章节**：8.9
- **一手资料**：`cs.android.com` / `frameworks/base/services/core/java/com/android/server/app/GameManagerService.java`
- **关键源码路径**：见上
- **关键调用链**：`GameManager#setGameState` -> `GameManagerService#SET_GAME_STATE` -> `PowerManagerInternal#setPowerMode(GAME_LOADING)`
- **版本差异摘要**：Android 16 (API 36) 引入 Headroom API；Android 17 (API 37) 引入 `preferredFrameRateCategory`。
- **Trace 观察点**：`power.hint_session` 轨道是 Android 17+ 调试 ADPF 的核心。

## 十、下一候选章节
- `src/part2-performance/ch05-scheduling/09-adpf.md`（与本章高度关联，建议联动 Review）。

## 十一、落盘信息
- **已写入文件**：`logs/external-review/2026-04-19-11-09-game-performance-external-review.md`
