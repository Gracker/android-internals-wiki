# Task2B Verifier 回流复查 · 2026-06-11 23:27

## 复查目标

| 章节 | 路径 | 状态问题 |
|------|------|---------|
| 16.2 各 Android 版本性能变更追踪 | src/part4-system/ch16-aosp/02-version-changes.md | status: finalized → task6_pending 无法被 Task6 拾取 |
| 2.13 图形缓冲区管理 (BufferQueue) | src/part1-fundamentals/ch02-rendering/13-buffer-queue.md | status: "finalized" → task6_pending 无法被 Task6 拾取 |
| 5.1 Linux 进程调度基础 | src/part1-fundamentals/ch05-cpu-power/01-linux-scheduling.md | status: "finalized" → task6_pending 无法被 Task6 拾取 |

## 诊断

3 个章节被 Task9 auto-fix 后设为 `pipeline_stage: task6_pending`、`task6_state: revisiting`，
但 `status` 仍为 `finalized`（而非 `ready-for-review`），导致 Task6 扫描时无法命中。

- queue.json 中无这 3 个 section 的 pending 条目 ✅
- 无活跃锁 ✅
- 正文行数均 ≥ 30（274/241/468）✅

## 修正动作

- 3 章 frontmatter `status` 统一改为 `ready-for-review`
- 其余字段（task2b_state/task6_state/task9_state/pipeline_stage）已正确，无需修改

## 结果

状态修正：3
阻塞：0
结果：ready-for-task6
