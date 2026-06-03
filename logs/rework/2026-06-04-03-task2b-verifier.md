# Task2B Verifier · 回流复查 · 2026-06-04 03:30

## 复查范围
本轮复查 6 个章节，修正 frontmatter 状态不一致问题。

## 复查结果

### 1. 13.15 BufferQueue 阻塞的 Perfetto 识别
- **问题**：Task6 pass-light-edit + Task9 pass-tech-review，但 status 仍为 ready-for-review
- **修复**：status → finalized, pipeline_stage → ready-to-publish, t6_state → reviewed, t9_state → reviewed
- **依据**：双审通过，无 queue 阻塞项

### 2. 4.8 ART 分代垃圾回收与 GC 暂停优化
- **问题**：Task6 pass-light-edit + Task9 pass-tech-review，但 status 仍为 ready-for-review，frontmatter 存在重复键
- **修复**：status → finalized, pipeline_stage → ready-to-publish, 去重 frontmatter
- **依据**：双审通过，无 queue 阻塞项

### 3. 13.8 Perfetto 输入延迟 SQL 深度分析
- **问题**：status=finalized 但 t9_result=pending, pipeline=task6_pending — Task9 未完成就提前 finalized
- **修复**：pipeline_stage → task9_pending, t9_state → pending, t6_state → reviewed
- **依据**：Task9 尚未完成，退回 Task9 队列

### 4. 19/09 Measure
- **问题**：t9_result=auto-fixed 但 pipeline_stage 停留在 task9_pending，未回流 Task6
- **修复**：pipeline_stage → task6_pending, t6_state → revisiting, t9_state → reviewed
- **依据**：auto-fix 完成后应回流 Task6 复审

### 5. 14.6 自动化测试工具
- **问题**：t9_result=auto-fixed 但 pipeline_stage 停留在 task9_pending，未回流 Task6
- **修复**：pipeline_stage → task6_pending, t6_state → revisiting, t9_state → reviewed
- **依据**：auto-fix 完成后应回流 Task6 复审

### 6. 21.1 启动完整路径分析（App 视角）
- **问题**：t9_result=auto-fixed 但 t9_state=pending, pipeline 停留在 task9_pending
- **修复**：pipeline_stage → task6_pending, t6_state → revisiting, t9_state → reviewed
- **依据**：auto-fix 完成后应回流 Task6 复审

## 系统性问题
- **Frontmatter 重复键**：全书 342 个章节存在 YAML 重复键（多次 Task 流程写入同名字段导致）。建议后续统一去重。
- **stale revisiting 标记**：34 个已 finalized+ready-to-publish 章节的 t6_state 仍为 revisiting（本轮未修复，为外观性问题，不影响流水线）。

## 统计
- 状态修正：6
- 阻塞：0（13.8 退回 Task9 不算阻塞，属于正常回流）
- 结果：ready-for-task6（3 个章节已回流 Task6）+ 2 finalized + 1 退回 Task9
