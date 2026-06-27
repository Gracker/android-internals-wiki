# Task2B Verifier · 回流复查 · 2026-06-28 07:27

## 复查范围
本轮扫描全部 src/ 下 fixed / fixed-lite / auto-fixed / task6_pending 状态章节。

## 候选章节
| # | 章节 | 路径 | 状态 |
|---|------|------|------|
| 1 | 1.25 | src/part1-fundamentals/ch01-architecture/01.25-binder-ipc-async-pipeline.md | task2b_state: fixed → MISALIGNED |

其余 318 个 fixed/fixed-lite 章节均已 finalized/ready-to-publish，无需复查。

## 复查详情

### 1.25 Android 17 Binder IPC 异步机制与批处理流水线

**复查前状态**：
- frontmatter: status=ready-for-review, task2b_state=fixed, task2b_result=fixed, task9_result=needs-rework, task6_state=reviewed, task9_state=reviewed, pipeline_stage=task6_pending
- queue.json: pending P95 from task9-deep-tech-review (added 2026-06-28T07:22:06)
- progress.json: pipeline_stage=task9_pending
- 正文有效行数: 220 (≥ 30 ✓)
- 锁: 无冲突

**问题**：Task9 于 07:22 新增 P0 源码错误（mCallRestriction 枚举值描述），写入 queue P95 并设置 task9_result=needs-rework。但未同步将 task2b_state 从 fixed 回退为 pending，pipeline_stage 未从 task6_pending 改为 task2b_pending。导致章节停留在"已修复待 Task6 复审"状态，实际应回到 Task2B 主修复队列。

**状态修正**：
- frontmatter: task2b_state: fixed → pending
- frontmatter: pipeline_stage: task6_pending → task2b_pending
- progress.json: pipeline_stage: task9_pending → task2b_pending

**结论**：章节需经 Task2B 主修复处理 queue P95 问题单后再回流 Task6。已修正状态路由。

## 统计
- 本轮复查：1 章
- 状态修正：1 章（1.25 frontmatter + progress.json）
- 阻塞：0
- 结果：no-change（1.25 需 Task2B 主修复先处理，非 ready-for-task6）
