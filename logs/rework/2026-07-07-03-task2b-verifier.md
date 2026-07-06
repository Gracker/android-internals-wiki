# Task2B Verifier · 回流复查 · 2026-07-07 03:34

## 复查范围

本轮扫描全部 src/**/*.md 的 task2b/fixed 状态章节，筛选非 ready-to-publish 且存在状态不一致的章节。

命中 2 个需要修正的章节 + 1 个 queue.json 结构问题。

## 1. §14.11 Battery Historian 与功耗分析工具
**文件**: `src/part3-tools/ch14-other-tools/11-battery-historian.md`

**问题**: CRITICAL — commit `80759fd88`（cleanup: 14.11 frontmatter dedup last_task2b_at）完全破坏了 YAML frontmatter。文件开头变为 `---\n\n# 14.11...`，所有元数据（status、pipeline_stage、task2b/task6/task9 状态字段等）全部丢失。

**根因分析**:
1. commit `2bba4875f` 将 `---\ntitle:` 误改为 `---title:`（换行被删除，frontmatter 起始分隔符与 title 合并）
2. commit `80759fd88` 尝试清理，但 diff `@@ -1,3 +1,869 @@` 表明将 frontmatter 的前 3 行替换为了 869 行正文，等于完全吞掉了 frontmatter

**修复**:
- 从 git 历史（commit `2bba4875f`）恢复完整 frontmatter
- 修复 `---title:` 为正确的 `---\ntitle:`
- 清理 `last_task2b_rerun_at`、`last_task2b_at` 等字段中的 trailing `''` 空值
- 追加 verifier 审计标记到 `review_notes`
- 恢复后状态: `status: ready-for-review`, `pipeline_stage: task6_pending`, `task2b_state: fixed`, `task9_result: needs-rework`

**验证**: frontmatter 52 行，首行 `title: Battery Historian 与功耗分析工具`，末行 `task9_reviewed_by: openclaw-task9`

## 2. §18.18 PIP 与自由窗口渲染
**文件**: `src/part2-performance/ch18-rendering-pipelines/18-pip-freeform.md`

**问题**: frontmatter 中 `task9_result` 出现两次（duplicate key）:
- 第一次: `task9_result: needs-rework`（正确，Task9 闲时抽检发现 P85 版本差异问题）
- 第二次: `task9_result: pass-tech-review`（旧值残留）
- YAML 规范中后出现的同键覆盖前面的，导致实际值为 `pass-tech-review`，与 queue 中 pending P85 entry 矛盾

此外 `status: finalized` 不正确 — Task9 刚发现问题，章节应处于 `ready-for-review` 等待 Task2B 回炉。

**修复**:
- 移除重复的 `task9_result: pass-tech-review`，保留 `task9_result: needs-rework`
- `status: finalized` → `status: ready-for-review`
- `task2b_state: pending` ✓（已正确）
- `pipeline_stage: task2b_pending` ✓（已正确）

## 3. queue.json 结构修复

**问题 A**: 5 处 JSON string value 中包含未转义的 ASCII 双引号（`"`），导致 JSON 解析失败
- 影响: 所有读取 queue.json 的任务均无法正常解析
- 修复: 将正文引用中的 ASCII `"` 替换为 Unicode 弯引号 `""`

**问题 B**: 顶层存在孤儿 key `"14.11"`（P95 pending），不在 `items[]` 数组内
- 影响: Task2B 主修复扫描 `items[]` 时无法发现该条目
- 修复: 将孤儿 entry 移入 `items[]` 数组

**修复后 queue 状态**: 14 items, 4 pending
- 18.18 P85 (task9) — waiting for Task2B main
- 2.15 P60 (task6-audit) — 不属于 Task2B lane
- 1.1 P60 (task6-audit) — 不属于 Task2B lane
- 14.11 P95 (task9) — waiting for Task2B main

## 状态闭环确认

| 章节 | 修复前 | 修复后 | queue pending? |
|------|--------|--------|----------------|
| 14.11 | frontmatter 完全丢失 | ready-for-review, task6_pending | P95 pending (Task2B 待修) |
| 18.18 | task9_result 冲突, status finalized | ready-for-review, task2b_pending | P85 pending (Task2B 待修) |

## 阻塞项
- §14.11 P95 API版本映射错误 — 需 Task2B 主修复处理
- §18.18 P85 TaskOrganizer 版本差异 — 需 Task2B 主修复处理
