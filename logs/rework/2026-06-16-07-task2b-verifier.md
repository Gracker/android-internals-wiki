# Task2B Verifier · 回流复查 · 2026-06-16 07:32

## 复查目标（5 章）

| 章节 | 路径 | 发现问题 |
|------|------|----------|
| 8.1 | src/part2-performance/ch08-responsiveness/01-responsiveness-principles.md | Task6 已 review(pass-light-edit) 但未推进 pipeline，task9_state 仍为 reviewed |
| 11.5 | src/part2-performance/ch11-power/05-wakelock.md | Task9 idle audit auto-fix 后 status 未从 finalized 改回 ready-for-review |
| 15.2 | src/part3-tools/ch15-methodology/02-system-vs-app.md | 同 11.5，status 未跟随 pipeline_stage 回退 |
| 16.4 | src/part4-system/ch16-aosp/04-android17-kernel612-performance.md | 同 11.5，status 未跟随 pipeline_stage 回退 |
| 20.7 | src/part5-app/ch20-stability/07-exception-architecture.md | Task6 已 review(pass-light-edit)，pipeline 已推进到 task9_pending，但 task9_state 仍为 reviewed |

## 复查标准

1. ✅ queue.json 中该 section 无 pending 回炉条目（5 章均无）
2. ✅ 正文有效行数 ≥ 30（5 章均远超）
3. ✅ 无活跃并发锁

## 状态修正（5 处）

### Ch 8.1 响应速度原理
- **问题**：Task6 于 2026-06-16 05:05 完成 revisiting review（pass-light-edit，无 B 类问题），但 pipeline_stage 停在 task6_pending，task9_state 保持 reviewed。
- **修正**：`task9_state: reviewed → pending`，`pipeline_stage: task6_pending → task9_pending`
- **效果**：章节正确进入 Task9 最终复审队列

### Ch 11.5 Wakelock 机制与功耗分析
- **问题**：Task9 idle audit auto-fix（2026-06-16）将 pipeline_stage 改为 task6_pending 并设 task6_state: revisiting，但 status 仍为 finalized，Task6 无法拾取。
- **修正**：`status: finalized → ready-for-review`
- **效果**：Task6 可正常拾取 revisiting 章节

### Ch 15.2 如何区分系统问题和 App 问题
- **问题**：同 11.5，Task9 idle audit auto-fix 后 status 未回退。
- **修正**：`status: finalized → ready-for-review`
- **效果**：Task6 可正常拾取 revisiting 章节

### Ch 16.4 Android 17 + Kernel 6.12 系统级性能优化
- **问题**：同 11.5，Task9 idle audit auto-fix 后 status 未回退。
- **修正**：`status: finalized → ready-for-review`
- **效果**：Task6 可正常拾取 revisiting 章节

### Ch 20.7 异常处理架构设计
- **问题**：Task6 于 2026-06-16 04:10 完成 review（pass-light-edit）并推进 pipeline 到 task9_pending，但 task9_state 保持 reviewed（来自前一轮 Task9 auto-fix），Task9 无法区分是否需要复审。
- **修正**：`task9_state: reviewed → pending`
- **效果**：Task9 可正常拾取做最终技术确认

## 阻塞（0）

无阻塞章节。

## 修改文件列表

- src/part2-performance/ch08-responsiveness/01-responsiveness-principles.md
- src/part2-performance/ch11-power/05-wakelock.md
- src/part3-tools/ch15-methodology/02-system-vs-app.md
- src/part4-system/ch16-aosp/04-android17-kernel612-performance.md
- src/part5-app/ch20-stability/07-exception-architecture.md
- logs/rework/2026-06-16-07-task2b-verifier.md（本文件）

## 结果

ready-for-task6（4 章回流 Task6，1 章回流 Task9）
