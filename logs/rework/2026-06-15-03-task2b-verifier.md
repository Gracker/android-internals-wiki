# Task2B Verifier · 回流复查 · 2026-06-15 03:28

## 复查范围
本轮扫描所有 `task2b_state: fixed` / `task2b_result: fixed` / `fixed-lite` / `task9_result: auto-fixed` 章节，重点检查 `pipeline_stage: task6_pending` 的回流状态一致性。

## 发现问题

### 状态不一致（3 个章节）
3 个章节在 2026-06-15 被 Task9 idle audit auto-fix 后，`pipeline_stage` 正确设为 `task6_pending`、`task6_state: revisiting`，但 `status` 仍停留在 `finalized`，未更新为 `ready-for-review`，导致 Task6 无法拾取。

## 状态修正

### 19 APM 全景图与分类体系
- 文件：`src/part3-tools/ch19-apm/01-apm-landscape.md`
- 修正：`status: finalized → ready-for-review`
- 原因：Task9 auto-fix 后 status 未从 finalized 改为 ready-for-review
- queue.json：无 pending 条目（已确认）
- 其他字段：task2b_state=fixed ✓ | task6_state=revisiting ✓ | pipeline_stage=task6_pending ✓ | body≥30 ✓

### 2.2 帧率与刷新率
- 文件：`src/part1-fundamentals/ch02-rendering/02-framerate.md`
- 修正：`status: finalized → ready-for-review`
- 原因：Task9 auto-fix 后 status 未从 finalized 改为 ready-for-review
- queue.json：无 pending 条目（已确认）
- 其他字段：task2b_state=fixed ✓ | task6_state=revisiting ✓ | pipeline_stage=task6_pending ✓ | body≥30 ✓

### 5.12 Thermal 管控深度：从内核子系统到 ADPF 主动降频
- 文件：`src/part1-fundamentals/ch05-cpu-power/12-thermal-management-deep-dive.md`
- 修正：`status: finalized → ready-for-review`
- 原因：Task9 auto-fix 后 status 未从 finalized 改为 ready-for-review
- queue.json：无 pending 条目（已确认）
- 其他字段：task2b_state=fixed ✓ | task6_state=revisiting ✓ | pipeline_stage=task6_pending ✓ | body≥30 ✓

## 复查统计
- 本轮复查章节数：3
- 状态修正：3
- 阻塞：0
- 结果：ready-for-task6

## 说明
3 个章节均由 Task9 idle audit 于 2026-06-15 自动修复（auto-fix），frontmatter 中
`pipeline_stage` 和 `task6_state` 已正确设为回流状态，仅 `status` 字段未同步。
本轮修正后，这 3 个章节可被 Task6 正常拾取进入 revisiting review。
