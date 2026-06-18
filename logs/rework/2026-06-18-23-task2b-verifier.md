# Task2B Verifier · 回流复查 · 2026-06-18 23:29

## 复查范围
本轮复查 6 个章节，聚焦 task2b/task9 auto-fix 后 frontmatter 状态未正确回流 Task6 的问题。

## 复查明细

### 1.17 IPC 全景：Android 进程间通信机制对比与性能选型
- **路径**: src/part1-fundamentals/ch01-architecture/17-ipc-panorama.md
- **诊断**: Task9 auto-fix 后 status 停留在 finalized，Task6 无法拾取（Task6 要求 status=ready-for-review）
- **修正**: status: finalized → ready-for-review
- **queue pending**: 0
- **body**: 378 行 ✓
- **结果**: ready-for-task6

### 5.2 EAS 能量感知调度
- **路径**: src/part1-fundamentals/ch05-cpu-power/02-eas.md
- **诊断**: Task9 auto-fix 后 status 停留在 finalized
- **修正**: status: finalized → ready-for-review
- **queue pending**: 0
- **body**: 243 行 ✓
- **结果**: ready-for-task6

### 3.7 InputDispatcher 反压与无响应窗口降级
- **路径**: src/part1-fundamentals/ch03-input/07-inputdispatcher-backpressure.md
- **诊断**: Task9 auto-fix 后 status 停留在 finalized
- **修正**: status: finalized → ready-for-review
- **queue pending**: 0
- **body**: 68 行 ✓
- **结果**: ready-for-task6

### 13.14 Perfetto DataGrid 与 Jank CUJ 标准库
- **路径**: src/part3-tools/ch13-perfetto/14-perfetto-data-explorer-jank-cuj.md
- **诊断**: Task9 auto-fix 后 status 停留在 finalized
- **修正**: status: finalized → ready-for-review
- **queue pending**: 0
- **body**: 183 行 ✓
- **结果**: ready-for-task6

### 18.1 渲染管线分类与选择对照表
- **路径**: src/part2-performance/ch18-rendering-pipelines/01-pipeline-overview.md
- **诊断**: pipeline_stage=finalized（非标准值），task6_state=reviewed 与 auto-fix 回流矛盾
- **修正**: pipeline_stage: finalized → task6_pending, task6_state: reviewed → revisiting
- **queue pending**: 0
- **body**: 78 行 ✓
- **结果**: ready-for-task6

### 15.2 如何区分系统问题和 App 问题
- **路径**: src/part3-tools/ch15-methodology/02-system-vs-app.md
- **诊断**: Task6 已于 6/17 re-review 通过 (pass-light-edit) 但未推进 pipeline；status=finalized 不符合 ready-for-review 要求
- **修正**: task6_state: revisiting → reviewed, pipeline_stage: task6_pending → task9_pending, status: finalized → ready-for-review
- **queue pending**: 0（queue 条目已 completed）
- **body**: 30 行 ✓ (borderline, 内容已从 Lite 截断恢复，16KB)
- **结果**: ready-for-task9

## 未处理的章节（超出本轮 6 章上限）
- 13.16 Agent 辅助 Perfetto 分析协议 — 同类问题 (status=finalized, pipeline=task6_pending)，下轮处理
- 13.17 Perfetto SDK 与应用内 Trace 数据源 — 同类问题 (status=finalized, pipeline=task6_pending)，下轮处理

## 统计
- 本轮复查：6 章
- 状态修正：6 章（共 9 处 frontmatter 修正）
- 阻塞：0
- 结果：ready-for-task6（5 章）/ ready-for-task9（1 章）

## 根因分析
4 个章节（1.17, 5.2, 3.7, 13.14）的共性问题是 Task9 auto-fix 流程只更新了 task9/task2b 字段但未将 status 从 finalized 改为 ready-for-review，导致 Task6 的选章条件 `status: ready-for-review AND task6_state: revisiting` 无法命中。18.1 的 pipeline_stage 被设为非标准值 "finalized"，疑似手动或脚本错误。15.2 是 Task6 re-review 通过后未推进 pipeline。
