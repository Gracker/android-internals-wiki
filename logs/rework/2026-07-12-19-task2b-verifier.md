# Task2B Verifier · 回流复查 · 2026-07-12 19:30

## 复查范围
本轮扫描全部 src/**/*.md 中 task2b_state=fixed / task2b_result=fixed|fixed-lite / task9_result=auto-fixed / pipeline_stage=task6_pending 的章节。
queue.json pending 条目：0

## 候选章节（非 ready-to-publish 且有修复证据）
共 3 个：

### 1. 16.5 Android 17 (API 37) 性能行为变更与适配方法
- 路径：src/part4-system/ch16-aosp/05-android17-api37-performance-changes.md
- 修复前状态：
  - status=ready-for-review ✅
  - task2b_state=fixed ✅
  - task2b_result=fixed-lite ✅
  - task9_result=auto-fixed ✅
  - task6_state=reviewed ⚠️（应为 revisiting）
  - pipeline_stage=task9_reviewed ⚠️（应为 task6_pending）
- 正文行数：594 ✅（≥30）
- queue pending：0 ✅
- 修正：task6_state → revisiting，pipeline_stage → task6_pending
- 结果：✅ 已修正，回流 Task6

### 2. 20.3 Native Crash 分析与治理
- 路径：src/part5-app/ch20-stability/03-native-crash-governance.md
- 状态：
  - status=ready-for-review ✅
  - task2b_state=fixed ✅
  - task2b_result=fixed ✅
  - task9_result=auto-fixed ✅
  - task6_state=revisiting ✅
  - pipeline_stage=task6_pending ✅
- 正文行数：529 ✅
- queue pending：0 ✅
- 结果：✅ 状态正确，无需修正

### 3. 22.10 RenderEffect 与 RuntimeShader 性能实践
- 路径：src/part5-app/ch22-rendering-practice/10-rendereffect-runtime-shader-performance.md
- 修复前状态：
  - status=finalized ⚠️（应为 ready-for-review）
  - task2b_state=fixed ✅
  - task2b_result=fixed ✅
  - task9_result=auto-fixed ✅
  - task6_state=revisiting ✅
  - pipeline_stage=task6_pending ✅
- 正文行数：137 ✅
- queue pending：0 ✅
- 修正：status → ready-for-review
- 结果：✅ 已修正，回流 Task6

## 统计
- 本轮复查：3 章
- 状态修正：2 处（16.5, 22.10）
- 阻塞：0
- 结果：ready-for-task6
