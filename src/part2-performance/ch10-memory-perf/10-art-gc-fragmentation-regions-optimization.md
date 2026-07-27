---
title: ART GC 碎片化与 Compaction 策略审计笔记
chapter: 10.10
status: needs-review
applicable_versions: Android 8 (API 26) - Android 17 (API 37)
tags: [Android, 内存性能, ART GC, 碎片化优化]
last_verified: "2026-07-27"
last_verified_against: "AOSP android-17.0.0_r1 baseline boundary; no source material supplied in deep-review run"
confidence: low
pipeline_stage: source-rework-required
task6_state: needs-source-material
task9_state: blocked-source-boundary
last_deep_review_at: "2026-07-27T16:35:02+08:00"
last_deep_review_run_id: "20260727-163502-deep-review-501b4554"
sources:
  - type: audit
    ref: "deep-review run 20260727-163502-deep-review-501b4554"
    note: "本轮未提供可路由源码/材料；正文仅保留可作为复查框架的通用 GC 议题，禁止作为 Android 17 新特性结论引用。"
---

# 10.10 ART GC 碎片化与 Compaction 策略审计笔记

## 审计结论

本章在 deep-review 中被判定为 **source-rework-required**：原稿把“Android 17 引入 Region 管理、按 Region 计算碎片化分数、Perfetto 暴露 `perfetto_heap_region_metrics`、应用可选择/调整 Region”等内容写成确定事实，但本轮 `materials` 为空，正文也没有给出 AOSP 文件、提交、官方文档或 Perfetto schema 作为支撑。为避免把未经证实的 Android 17/API 37 主线结论写入 AIW，本文已降级为审计笔记，不再宣称这些机制已经在 Android 17 对应用开发者开放或可直接观测。

后续要恢复为正式章节，需要 body-apply/source-material lane 提供至少以下证据之一：

1. `art/runtime/gc/` 下与 compaction、heap space、collector type、region/region space 相关的 android-17.0.0_r1 源码定位；
2. Android Runtime / ART GC 官方说明或 release note；
3. Perfetto heap profiling 或 ART GC trace 相关的真实表、track、counter/schema 文档；
4. 能复现实验的 trace、logcat、statsd 或 benchmark 数据。

## 版本边界

- 本章只允许讨论 **Android 8 (API 26) 到 Android 17 (API 37)** 范围内已经验证的 ART/Perfetto 行为。
- 不得把 Android 18/API 38+、未合入 AOSP baseline、厂商私有 runtime 或研究原型的结论回填为 Android 17 主线事实。
- “Region”“fragmentation score”“selective compaction”等术语在后续正文中必须绑定到具体源码类、trace 字段或官方文档；没有来源时只能作为待验证问题，而不能作为工程建议。

## 可保留的技术问题框架

### 1. 碎片化为什么影响 ART 堆

长时间运行的 Android 进程会经历不同生命周期对象的交错分配与释放。即使总空闲内存仍然存在，空闲块分布、对象移动成本、GC 暂停预算和 native/Java heap 压力都可能影响分配延迟、GC 频率与 OOM 风险。这一问题可以作为章节主题保留，但需要用源码或 trace 解释 ART 在对应版本中的真实 collector 与 heap-space 行为。

### 2. Compaction 需要回答的源码问题

后续重写时，应按源码而不是伪代码回答：

- Android 17 baseline 中有哪些 ART GC collector/heap space 与 compaction 相关？
- 何时触发 moving/compacting collector，触发条件来自 runtime flag、heap utilization、zygote/fork 后状态还是 foreground/background 进程策略？
- 对象移动如何更新引用，暂停阶段和并发阶段如何划分？
- 应用开发者能观察到哪些信号：logcat、Perfetto track、heap dump、`dumpsys meminfo`、statsd，还是只能间接通过 GC pause 与 allocation profile 判断？

### 3. 应用侧可以安全讨论的方向

在没有 ART 内部源码证据之前，应用侧建议只能保留为通用内存性能方向：

- 减少短生命周期大对象和临时数组的峰值分配；
- 对图片、buffer、序列化临时对象做复用或生命周期收敛；
- 用 Perfetto、Android Studio Memory Profiler、heap dump、logcat GC 记录定位分配峰值与暂停，而不是假设存在应用可控制的 ART Region；
- 避免用 `System.gc()` 或“预热后释放大块内存”作为默认优化手段，除非有可复现数据证明收益且不会伤害交互路径。

## 已移除/回流的高风险说法

以下原稿内容已从正式叙述中移除或降级为待验证项：

- “Android 17 引入革命性的 GC Region 管理机制”；
- “ART 源码中的碎片化计算公式”及 Java 伪代码；
- 应用可按 Region 监控、选择 Region、调整 Region 大小或隔离资源 Region；
- `perfetto_heap_region_metrics` SQL 表；
- 未给出处的“GC 暂停减少 60%”“内存效率提升 25%”“启动 3.2s 降至 1.8s”等案例数字；
- “Android 17 的 ART GC Region 架构代表重大进步”等无来源结论。

## 后续重写检查清单

1. 在 frontmatter `sources` 中列出 AOSP 路径、文档 URL 或实验报告路径。
2. 每个 Android 17 主线结论都要能追溯到 `android-17.0.0_r1` 或 android17-6.18 相关证据。
3. Perfetto SQL 示例必须来自真实 schema；如果只是分析思路，应标注为伪代码/示意。
4. 性能收益必须来自可复现实验或公开数据；否则只写“可能改善/需要验证”。
5. 完成 source-bound rewrite 后再把 `confidence` 从 `low` 提升到 `medium` 或更高。
