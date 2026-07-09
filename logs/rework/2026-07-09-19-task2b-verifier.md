# Task2B Verifier · 回流复查 · 2026-07-09 19:29

## 复查范围
本轮扫描 Task2B / Task2B Lite / Task9 auto-fix 后状态为 `task2b_state: fixed` 或 `task9_result: auto-fixed` 但尚未到达 `ready-to-publish` 的章节。

共发现 10 个状态不一致章节，本轮处理 6 个（按章节号排序取前 6）。

## 复查结果

| 章节 | 路径 | 问题描述 | 修复动作 |
|------|------|---------|---------|
| 2.7  | src/part1-fundamentals/ch02-rendering/07-hardware-layer.md | status=finalized, pipeline=task6_pending, task6_state=revisiting → Task6 无法拾取 | status: "finalized" → ready-for-review |
| 3.7  | src/part1-fundamentals/ch03-input/07-inputdispatcher-backpressure.md | 同上 | status: finalized → ready-for-review |
| 5.2  | src/part1-fundamentals/ch05-cpu-power/02-eas.md | 同上 | status: finalized → ready-for-review |
| 9.2  | src/part2-performance/ch09-anr/02-anr-types.md | 同上 | status: finalized → ready-for-review |
| 10.5 | src/part2-performance/ch10-memory-perf/05-case-studies.md | 同上 | status: "finalized" → ready-for-review |
| 15.6 | src/part3-tools/ch15-methodology/06-testing-best-practices.md | 同上 | status: finalized → ready-for-review |

## 根因分析
这些章节此前由 Task9 auto-fix 处理，Task9 正确设置了 `task6_state: revisiting` + `pipeline_stage: task6_pending`，但未将 `status` 从 `finalized` 改为 `ready-for-review`。导致 Task6 的 Step 2 选择逻辑（Priority 3: status=ready-for-review + task6_state=revisiting）无法匹配这些章节，形成状态死锁。

## 验证标准
- ✅ queue.json 无 pending 回炉条目（这些 section 均无 pending queue item）
- ✅ 正文非空壳（所有章节 body_lines ≥ 81）
- ✅ 无活跃锁
- ✅ frontmatter 已修正为回流就绪状态

## 未处理（留待下一轮）
- 17.1 (src/part4-system/ch17-oem/01-oem-overview.md) — 同类问题
- 18.1 (src/part2-performance/ch18-rendering-pipelines/01-pipeline-overview.md) — 同类问题
- 21.5 (src/part5-app/ch21-startup/05-splash-screen.md) — 同类问题
- 25.19 (src/part5-app/ch25-power-size/19-android-vitals-wakelock-governance.md) — 状态组合不同，需单独检查

## 状态修正统计
- 状态修正：6
- 阻塞：0
- 结果：ready-for-task6（6 个章节已回流）
