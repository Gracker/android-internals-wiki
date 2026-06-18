# Task2B Verifier · 回流复查 · 2026-06-19 07:31

## 复查目标（4 章）

| 章节 | 路径 | 问题 | 修正 |
|------|------|------|------|
| 13.16 | src/part3-tools/ch13-perfetto/16-agent-perfetto-analysis-protocol.md | Task9 auto-fix 后 Task6 已 re-review pass，但 task9_state 仍为 reviewed，未重置为 pending | task9_state: reviewed → pending |
| 13.17 | src/part3-tools/ch13-perfetto/17-perfetto-sdk-in-app-tracing.md | 同上 | task9_state: reviewed → pending |
| 15.2 | src/part3-tools/ch15-methodology/02-system-vs-app.md | 同上 | task9_state: reviewed → pending |
| 25.22 | src/part5-app/ch25-power-size/22-location-services-performance.md | pipeline_stage=task6_pending 但 task6_state / task9_state 缺失 | 补 task6_state=revisiting, task9_state=pending, task9_result=pending |

## 复查标准

1. queue.json 无 pending 条目 ✅（4 章均无）
2. 正文有效性 ✅（4 章有效正文行均 ≥ 100）
3. 无冲突锁 ✅
4. frontmatter 状态闭环 — 本轮修正 4 处

## 修正后状态

- 13.16: ready-for-review / t2b=fixed / t6=reviewed / t9=pending / pipe=task9_pending → 等 Task9 最终确认
- 13.17: 同上
- 15.2: 同上
- 25.22: ready-for-review / t2b=fixed / t6=revisiting / t9=pending / pipe=task6_pending → 等 Task6 复审

## 统计

- 状态修正：4
- 阻塞：0
- 结果：ready-for-task6（25.22 直接回流 Task6；13.16/13.17/15.2 回流 Task9 最终确认）
