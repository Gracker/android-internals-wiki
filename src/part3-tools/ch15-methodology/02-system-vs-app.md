---
last_task2b_state: fixed-lite
last_task2b_result: fixed-lite
last_task6_state: revisiting
last_task9_state: revisiting
last_pipeline_stage: task6_pending
task2b_result: fixed-lite
task2b_state: fixed
task6_state: revisiting
task9_state: pending
pipeline_stage: task6_pending
task2b_result: fixed-lite
last_task2b_lite_at: 2026-06-18
last_audit_log: "logs/review/2026-06-18-08-audit.md"
last_task9_audit_log: "logs/deep-review/2026-06-16-04-audit.md"
last_task9_autofix_at: "2026-06-16"
deepseek_cn_review_state: done
last_deepseek_cn_review_at: 2026-06-16
---

# 如何区分系统问题和 App 问题
<!-- outline-start -->
## 本节要点大纲
### 锚点（必须覆盖）
- 🔹 区分系统问题 vs App 问题的重要性
- 🔹 从 Trace 判断：CPU 调度延迟 → 系统、主线程耗时 → App
- 🔹 系统负载高的特征：CPU 全核满载、kswapd 活跃、SurfaceFlinger 延迟
- 🔹 App 自身问题的特征：主线程 Slice 耗时明显、特定操作触发
- 🔹 灰色地带：系统资源不足导致 App 表现差（谁该负责？）

### 扩展（可选深入）
- 🔸 多 App 共存时的性能归因
- 🔸 系统级性能回归的排查方法

### OpenClaw 加工指引
> **锚点**是最低覆盖要求，加工时必须逐条落实并标注验证结果。
> **扩展**视素材丰富程度选择性深入。
> 如果从 Obsidian 素材或 AOSP 源码中发现大纲未列出但与本节强相关的知识点，
> 可**就地插入**最相关的锚点之后，并用 `[自动发现]` 标注，方便后续 review。
> 锚点内容需 L1/L2 验证，扩展内容至少 L2 验证，自动发现内容至少标注来源。
<!-- outline-end -->

## 为什么一定要区分系统问题和 App问题

很多性能排查卡在后半段——trace 够了，工具也会用，问题出在一开始就把责任链看错了。

用户反馈你的 App 滑动卡顿，你打开 Perfetto 一看，主线程每一帧都在 20ms 左右——超标了，但 MainThread 的 Slice 里没有特别长的耗时段。放大去看，主线程大部分时间处于 Runnable 状态，也就是