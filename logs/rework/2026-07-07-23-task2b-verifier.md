# Task2B Verifier · 回流复查 · 2026-07-07 23:28

## 复查目标（5 章节）

### Group 1: Task9 auto-fixed + Task6 已复审，task9_state 未重置（3 章）

| 章节 | 路径 | 问题 | 修复 |
|------|------|------|------|
| 19.16 | src/part3-tools/ch19-apm/16-profiling-manager.md | Task9 idle audit auto-fix 后 task9_state 留在 reviewed，Task6 已于 2026-07-07T20:11 完成 revisiting review (pass-light-edit)，章节卡在 task9_pending 但 Task9 不会拾取 | task9_state: reviewed→pending |
| 2.20 | src/part1-fundamentals/ch02-rendering/20-multiwindow-desktop-rendering.md | 同上；Task6 已于 2026-07-07 完成 revisiting review | task9_state: reviewed→pending |
| 16.3 | src/part4-system/ch16-aosp/03-aosp-build.md | 同上；Task6 已于 2026-07-07T20:11 完成 revisiting review | task9_state: reviewed→pending |

### Group 2: Task9 auto-fixed，status 留在 finalized 未回落（2 章）

| 章节 | 路径 | 问题 | 修复 |
|------|------|------|------|
| 12.4 | src/part2-performance/ch12-apk-network/04-network-security-tls-performance.md | Task9 idle audit auto-fix (2026-07-07T22:29) 正确设置 pipeline_stage=task6_pending、task6_state=revisiting，但 status 未从 finalized 回退到 ready-for-review；Task6 无法拾取 | status: finalized→ready-for-review |
| 7.6 | src/part2-performance/ch07-smoothness/06-case-studies.md | 同上；Task9 idle audit auto-fix (2026-07-07T21:20) | status: finalized→ready-for-review |

### 跳过

| 章节 | 路径 | 原因 |
|------|------|------|
| 13.12 | src/part3-tools/ch13-perfetto/12-perfetto-profiles-flamegraph.md | 已完成全流程（finalized + ready-to-publish + pass-tech-review），frontmatter 引号转义为历史遗留，不影响流水线状态 |

## 验证

- queue.json 无 Task2B pending 条目 ✓
- 所有 5 章正文 ≥ 30 行 ✓
- 无活跃锁冲突（本轮自建锁） ✓
- 未修改正文 ✓

## 统计
- 复查：5 章
- 状态修正：5
- 阻塞：0
- 结果：ready-for-task6 / ready-for-task9（Group 2 回 Task6，Group 1 回 Task9）

## 修复详情

### Group 1 根因分析
Task9 idle audit 执行 auto-fix 时按规范设置 task6_state=revisiting、pipeline_stage=task6_pending。
Task6 随后拾取并完成 revisiting review（pass-light-edit），正确设置 task6_state=reviewed、pipeline_stage=task9_pending。
但 Task6 未将 task9_state 从 reviewed 重置为 pending，导致 Task9 不会再次拾取。
**修复**：手动重置 task9_state=pending，使 Task9 能在下一轮做 confirmation pass。

### Group 2 根因分析
Task9 idle audit 执行 auto-fix 时正确设置 task6_state=revisiting、pipeline_stage=task6_pending，
但未将 status 从 finalized 改回 ready-for-review。Task6 只扫描 status=ready-for-review 的章节，
因此这些章节永远不会被 Task6 拾取。
**修复**：手动重置 status=ready-for-review。
**建议**：Task9 auto-fix 流程应包含 `status: finalized → ready-for-review` 步骤。
