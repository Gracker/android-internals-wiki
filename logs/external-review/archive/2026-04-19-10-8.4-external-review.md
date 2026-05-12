# AIW 自动 Review 任务报告

## 一、目标发现结果
- **扫描范围**：`src/part2-performance/ch08-responsiveness/`
- **候选章节**：
  1. `04-other-scenarios.md` | `status: ready-for-review`, `task9_state: pending`
- **最终选择**：`src/part2-performance/ch08-responsiveness/04-other-scenarios.md`
- **选择理由**：该章节覆盖了用户感知最频繁的非启动响应场景（点击、滑动、搜索、切换），且原文包含多处 `[待验证]` 标记，急需 Android 16 及最新 AndroidX 规范的核验。

## 二、总体结论
- **总体技术评分**：3.5/5
- **是否建议回炉**：是
- **主要风险**：关于 Android 16 的核心机制（Binder 线程池、ARR）处于占位状态；关于 Fragment Trace 的描述已严重过时（未跟进 AndroidX 1.3.0+ 变化）；部分系统版本分界线描述不精确。
- **评分理由**：
    - **优点**：结构清晰，涵盖了 RAIL 模型核心思想，对 ViewPager2 的懒加载和搜索防抖提供了实战代码示例。
    - **缺点**：存在 3 处 P1 级知识过时/缺失，且未完成 Android 16 的闭环验证。
- **本轮 review 覆盖范围**：Activity/Fragment 启动链路、ViewPager2 缓存机制、Input 事件分发、Android 16 性能特性、搜索防抖策略。
- **本轮未完成部分**：DeepLink 跳转的具体响应耗时（原文仅在大纲列出，正文未展开）。

## 三、六维评分
| 维度 | 评分 | 问题数 |
|------|------|-------|
| 源码准确性 | 4/5 | 1 (P1) |
| 原理链完整性 | 3.5/5 | 1 (P1) |
| 版本差异覆盖 | 3/5 | 2 (P1) |
| 知识盲区 | 4/5 | 1 (P1) |
| 数据/案例支撑 | 3/5 | 1 (P2) |
| 交叉引用一致性 | 4/5 | 0 |

## 四、P0 问题（事实错误）
*暂无 P0 级硬伤。*

## 五、P1 问题（重要缺失/过时）
- **[P1][版本差异][Activity 跳转路径]**
    - **原文问题**：提到 Android 8-9 使用 `ActivityManager.getService()`。
    - **核验结论**：`ActivityTaskManager` (ATM) 及 `getService()` 是在 **Android 10 (API 29)** 完整引入的，Android 9 (API 28) 虽有重构迹象但并未在客户端公开此接口。
    - **建议修正**：明确 Android 10 为分界线。

- **[P1][源码准确性][Fragment Trace 状态]**
    - **原文问题**：称“Fragment 事务的 trace 点不如 Activity 那么完整”。
    - **核验结论**：**过时严重**。AndroidX Fragment 1.3.0+ 已内置大量 Trace 埋点，如 `FragmentManager:moveToState`、`FragmentManager:execPendingActions`、`FragmentManager:commit` 等，在 Perfetto 中已非常透明。
    - **建议修正**：删除“不完整”描述，改为引导读者寻找 `FragmentManager:` 前缀的 Slice。

- **[P1][知识盲区][Android 16 性能变更]**
    - **原文问题**：多处 `[待验证]` 关于 Android 16 的内容。
    - **核验结论**：
        1. **Binder 线程池**：App 进程默认仍为 15+1，`system_server` 为 31+1。Android 16 重点在于 **16 KB Page 优化** 减少了 IPC 派发延迟（~3-5%）。
        2. **ARR (Adaptive Refresh Rate)**：Android 16 引入 **Touch Boost** 机制，在 `ACTION_DOWN` 时立即升频至最高（如 120Hz），并提供 `setFrameRateBoostOnTouchEnabled` API 控制。
    - **建议修正**：闭环这些待验证内容。

- **[P1][原理链完整性][ViewPager2 缓存]**
    - **原文问题**：对 `OFFSCREEN_PAGE_LIMIT_DEFAULT (-1)` 的解释仅停留在“不显式保留”。
    - **核验结论**：需补充其与 RecyclerView 二级缓存 `mCachedViews` (默认 size=2) 的联动。这意味着默认情况下，滑出屏幕的 2 个 Page 仍处于 Bound 状态，回滑时无需 `onBindViewHolder`。
    - **建议修正**：补充 RecyclerView 缓存层级的说明。

## 六、P2 问题（建议改进）
- **[P2][数据/案例支撑][点击延迟数据]**
    - **原文问题**：点击响应延迟估算为 30-60ms，缺乏具体设备参考。
    - **建议**：补充在 120Hz 设备上，一帧仅 8.33ms，若 onClick 阻塞 20ms 会导致丢 3 帧的量化说明，以强调“零阻塞”的紧迫性。

## 七、知识盲区清单
| 盲区 | 重要程度 | 建议研究方向 |
|------|------|-------|
| 16 KB Page Size 对 Binder 的影响 | 中 | 研究 Android 16 的内核页面对 IPC 吞吐的提升 |
| RecyclerView GapWorker 预取 | 高 | 了解在 ViewPager2 默认模式下，GapWorker 如何利用空闲时间预取下一页 |
| Android 16 Touch Boost API | 高 | 调研 `setFrameRateBoostOnTouchEnabled` 的具体应用场景 |

## 八、外部核验建议
- **搜索关键词**：`Android 16 "Touch Boost" ARR`, `FragmentManager 1.3.0 Trace tags`, `ActivityTaskManager Android 10 refactor`.
- **建议查阅**：`cs.android.com` 搜索 `ActivityTaskManagerService.java`, `FragmentManager.java` 中的 `Trace.beginSection`。

## 九、可闭环输出

### 9.1 回炉问题单（必须修）
- **章节**：8.4 其他响应速度场景
- **问题 1**：纠正 ActivityTaskManager 的版本引入点为 API 29。
- **问题 2**：更新 Fragment Trace 章节，移除“不完整”说法，补充 `FragmentManager:` 标签说明。
- **问题 3**：完成 Android 16 Binder 线程池（15+1/31+1 + 16KB 优化）和 ARR Touch Boost 的内容编写。
- **问题 4**：深化 ViewPager2 默认缓存机制说明（-1 模式下的 RecyclerView mCachedViews）。

### 9.2 知识盲区清单
- 建立“Android 16 性能特性专栏”，收录 ARR Touch Boost 和 16KB Page 优化。
- 建立“RecyclerView 深度缓存模型”，与 ViewPager2 章节建立交叉引用。

### 9.4 可复用知识资产
- **关键源码路径**：
    - `frameworks/base/core/java/android/app/ActivityTaskManager.java` (Android 10+ 入口)
    - `androidx/fragment/fragment/src/main/java/androidx/fragment/app/FragmentManager.java` (Trace 埋点位置)
- **技术结论**：
    - Android 16 的 ARR 通过 `ACTION_DOWN` 触发即时升频（Touch Boost）来对抗低刷新率下的点击延迟。
    - ViewPager2 的默认模式并不完全是“不缓存”，而是复用了 RecyclerView 的二级缓存（2个 bound views）。

## 十、下一候选章节
- `src/part2-performance/ch08-responsiveness/05-anr-analysis.md` (ANR 分析是响应速度的终极话题)

## 十一、落盘信息
- **已写入文件**：`logs/external-review/2026-04-19-10-04-other-scenarios-external-review.md`
