# 第 15 章（Methodology）批量 Review 总结

- **章节范围**：15.1 - 15.8
- **Review 日期**：2026-04-18 ~ 2026-04-19
- **Reviewer**：Claude Opus 4.6 (Thinking) / External AI
- **来源规范**：aiw-gemini-review-pack.md

---

## 一、总体概览

| 章节 | 标题 | 评分 | P0 | P1 | P2 | 处置建议 |
|------|------|------|----|----|----|---------| 
| 15.1 | 性能优化的术、道、器 | 2.5/5 | 2 | 3 | 2 | **回炉** |
| 15.2 | 如何区分系统问题和 App 问题 | 3/5 | 0 | 2 | 3 | 结构化修正 |
| 15.3 | 性能指标体系 | 3.5/5 | 1 | 2 | 4 | 结构化修正 |
| 15.4 | 竞品分析方法 | 4/5 | 0 | 1 | 3 | 轻量修正 |
| 15.5 | 线上性能监控 | 3/5 | 1 | 1 | 3 | **局部回炉** |
| 15.6 | 性能测试最佳实践 | 4/5 | 0 | 1 | 2 | 轻量修正 |
| 15.7 | AOSP 代码阅读 | 4.5/5 | 0 | 0 | 2 | 无需修正 |
| 15.8 | Android 性能问题实证 | 3.5/5 | 0 | 2 | 2 | 结构化修正 |
| **合计** | — | **均值 3.5/5** | **4** | **12** | **21** | — |

---

## 二、高频问题模式

### 1. API 版本标注错误（4 处）
- ProfilingManager 标注为 Android 8，实际 Android 15 API 35（15.1）
- FrameMetrics 标注为 Android 11-13，实际 Android 7.0 API 24（15.1）
- FrameMetricsAggregator 标注为 API 28，实际是 Jetpack 库依赖 API 24（15.3）
- CompilationMode.SpeedProfile() 不存在，应为 Partial()（15.6）

### 2. 系统机制描述错误（3 处）
- LMK 杀进程依据：PSS（错）→ oom_score_adj（正）（15.3）
- Choreographer.FrameCallback 线程行为：API 24 独立线程（错）→ 始终主线程（正）（15.5）
- SurfaceFlinger 入口：doComposition（过时）→ onMessageRefresh（正）（15.2）

### 3. 数据引用不一致（2 处）
- 慢帧不良行为阈值描述与 Google Play 官方定义不匹配（15.3）
- 论文数据 76.39% 引用为 63.41%（15.8）

---

## 三、优先修正队列

### 立即修正（P0，4 条）
1. **15.1 第 80 行**：ProfilingManager API 版本 → Android 15 (API 35)
2. **15.1 第 102 行**：FrameMetrics API 版本 → Android 7.0 (API 24)
3. **15.3 第 222 行**：LMK 杀进程依据 → oom_score_adj（不是 PSS）
4. **15.5 第 107 行**：FrameCallback 线程行为 → 始终主线程（删除 API 24 独立线程的说法）

### 尽快修正（P1，12 条）
1. 15.1：BlastBufferQueue 版本标注 → Android 12+ 不是 10+
2. 15.1：Baseline Profiles 版本标注 → API 33+ 不是 21+
3. 15.1：Google 搜索延迟数据过时 → 更新或删除
4. 15.2：SurfaceFlinger 方法名 → onMessageRefresh
5. 15.2：ANR 超时阈值 → 区分不同类型
6. 15.3：FrameMetricsAggregator → Jetpack 库，非 API 28
7. 15.3：慢帧不良行为阈值 → 区分 Core Vitals 和 Other Vitals
8. 15.4：TotalTime 端点 → 首帧绘制完成，不是 onResume()
9. 15.5：JankStats 掉帧判定 → API 31+ 使用 DEADLINE
10. 15.6：CompilationMode → Partial() 不是 SpeedProfile()
11. 15.8：论文数据引用 → 核实 63.41% vs 76.39% 口径
12. 15.8：代码示例 Java/Kotlin 混杂 → 统一风格

---

## 四、质量分布

```
5.0 ┃
    ┃          ★                 ★★
4.0 ┃     ★         ★    ★
    ┃ ★        ★              ★
3.0 ┃
    ┃ ★
2.5 ┃
    ┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    15.1  15.2  15.3  15.4  15.5  15.6  15.7  15.8
    回炉         修正  轻量  回炉  轻量  通过  修正
```

- **最佳**：15.7（AOSP 代码阅读）4.5/5 — 零 P0/P1，可直接发布
- **最差**：15.1（性能优化哲学）2.5/5 — 2×P0 版本标注错误，建议回炉
- **中位数**：3.5/5

---

## 五、交叉引用一致性问题

1. **LMK 依据**：15.2 说 oom_adj_score（拼写错误），15.3 说 PSS。两处都不完全正确。正确字段名是 `oom_score_adj`。
2. **ANR 超时**：15.2 和 15.3 都提到 ANR 5s 阈值，但未区分输入分发 ANR（5s）和其他类型 ANR 的超时差异。15.8 在第 97 行正确指出了这个区分。
3. **JankStats**：15.3 未提及，15.5 有介绍但版本未更新（未标注 1.0.0 stable）。

---

## 六、知识盲区汇总

| 盲区 | 重要程度 | 出现在 | 建议 |
|------|---------|--------|------|
| JankStats 1.0 Stable | 高 | 15.3, 15.5 | 补充版本状态和用法 |
| ProfilingManager API 35 | 高 | 15.1, 15.5 | 修正版本标注并补充用法 |
| Jetpack Compose 性能反模式 | 中 | 15.8 | 补充 Compose recomposition 问题 |
| ARR（Adaptive Refresh Rate）| 低 | 15.3 | 补充对帧预算的影响 |

---

## 七、可直接发布的章节

- **15.7（AOSP 代码阅读）**：0×P0, 0×P1。内容经核验全部准确。可直接进入发布队列。

---

## 八、推荐修正优先级

1. **第一批**（建议 1 天内完成）：修正 4 条 P0（15.1 版本标注 ×2、15.3 LMK 依据、15.5 线程行为）
2. **第二批**（建议 3 天内完成）：修正 12 条 P1（上述列表）
3. **第三批**（可排入迭代）：处理 21 条 P2 建议

---

## 九、Review 报告索引

| 章节 | 报告文件 |
|------|---------|
| 15.1 | logs/external-review/2026-04-18-22-15.1-external-review.md |
| 15.2 | logs/external-review/2026-04-18-22-15.2-external-review.md |
| 15.3 | logs/external-review/2026-04-18-22-15.3-external-review.md |
| 15.4 | logs/external-review/2026-04-18-22-15.4-external-review.md |
| 15.5 | logs/external-review/2026-04-18-22-15.5-external-review.md |
| 15.6 | logs/external-review/2026-04-18-22-15.6-external-review.md |
| 15.7 | logs/external-review/2026-04-18-22-15.7-external-review.md |
| 15.8 | logs/external-review/2026-04-18-22-15.8-external-review.md |
