# Task2B Verifier · 回流复查 · 2026-06-05 03:28

## 复查章节

| 章节 | 标题 | 状态修正 | 说明 |
|------|------|----------|------|
| 7.18 | HWC Overlay Plane 与合成降级排查 | ✅ 已修正 | 补充 task6_state: pending, task9_state: pending |
| 2.22 | SurfaceFlinger FrontEnd 与 RequestedLayerState | ✅ 已修正 | 补充 task6_state: pending, task9_state: pending |
| 4.11 | Cached App Freezer 与 GC 触发边界 | ✅ 已修正 | 补充 task6_state: pending, task9_state: pending |
| 25.19 | Android Vitals 过度 WakeLock 指标与治理 | ✅ 已修正 | 补充 task6_state: pending, task9_state: pending |
| 25.14 | JobScheduler 调试：Pending Reasons 与 JobDebugInfo | ✅ 已修正 | 补充 task6_state: pending, task9_state: pending |
| 21.12 | Startup Profile 与 DEX Layout 启动优化 | ✅ 已修正 | 补充 task6_state: pending, task9_state: pending |

## 问题类型

6 个章节均为 task2a 直接产出后标记为 ready-for-review + task6_pending，但缺少 task6_state / task9_state 字段。
Task6 扫描要求 task6_state: pending 才能命中，导致这些章节长期停留在 task6_pending 但无法被 Task6 拾取。

## 修正内容

为每个章节的 frontmatter 补充：
- `task6_state: pending`
- `task9_state: pending`

## 跳过章节

- 7.13 SystemUI 性能分析：queue 中仍有 pending（task6-review, pri=50），等待主修复处理
- 2.6 SurfaceFlinger 与合成：queue 中仍有 pending（task-deepresearch-injector, pri=80），等待素材注入
- 19 商业 APM 平台：queue 中仍有 pending（task-deepresearch-injector, pri=80），等待素材注入

## 统计

- 本轮复查：6 章
- 状态修正：6
- 阻塞：0（3 章因 queue pending 跳过，不算阻塞）
