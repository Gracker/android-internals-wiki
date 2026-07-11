# Task2B Verifier · 回流复查 · 2026-07-12 03:30

## 复查目标

本轮扫描全部 src/ 中 task2b_state=fixed / task2b_result=fixed|fixed-lite / task9_result=auto-fixed / pipeline_stage=task6_pending 的章节，共命中 2 个状态不一致的章节：

| 章节 | 文件 | 问题 |
|------|------|------|
| 20.5 | src/part5-app/ch20-stability/05-oom-governance.md | Task9 idle-audit auto-fix 后 status 仍为 finalized，task9_state 仍为 reviewed |
| 25.9 | src/part5-app/ch25-power-size/09-power-size-case-studies.md | 同上 |

## 根因

2026-07-12 Task9 idle-audit 对两章执行了 auto-fix（源码锚点更新 / 版本差异补充），正确设置了 pipeline_stage: task6_pending 和 task6_state: revisiting，但未将 status 从 finalized 改为 ready-for-review，也未将 task9_state 从 reviewed 改为 pending。导致 Task6 无法通过优先级筛选拾取这两章。

## 验证结果

### Section 20.5 — OOM 治理
- queue.json pending：无
- 正文行数：256（≥ 30）✓
- 并发锁：无 ✓
- 修复前状态：status=finalized, task9_state=reviewed
- 修复后状态：status=ready-for-review, task9_state=pending
- task2b_state=fixed ✓, task6_state=revisiting ✓, pipeline_stage=task6_pending ✓

### Section 25.9 — 功耗与包体积案例集
- queue.json pending：无
- 正文行数：125（≥ 30）✓
- 并发锁：无 ✓
- 修复前状态：status=finalized, task9_state=reviewed
- 修复后状态：status=ready-for-review, task9_state=pending
- task2b_state=fixed ✓, task6_state=revisiting ✓, pipeline_stage=task6_pending ✓

## 状态修正

| 章节 | 修正项 | 旧值 | 新值 |
|------|--------|------|------|
| 20.5 | status | finalized | ready-for-review |
| 20.5 | task9_state | reviewed | pending |
| 25.9 | status | finalized | ready-for-review |
| 25.9 | task9_state | reviewed | pending |

## 阻塞

无。两章均已满足 Task6 回流标准，等待 Task6 下一轮拾取。

## 结论

ready-for-task6
