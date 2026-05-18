---
title: "性能实验统计与分位值回归判定"
chapter: "26.14"
status: draft
applicable_versions: "Android 8 (API 26) - Android 17 (API 37)"
tags: [observability, ab-test, performance-metrics, release-quality, macrobenchmark]
related_chapters: ["15.3", "15.6", "26.3", "26.6", "26.7"]
created_by: "task2a-knowledge-gap"
created_date: "2026-05-18"
gap_source: "章节深挖/素材驱动"
gap_score: 16
material_count: 5
source_refs:
  - "intake/research-gaps.md#2026-05-15-26.6"
  - "Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 32.md"
  - "Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 33.md"
  - "https://firebase.google.com/docs/ab-testing/abtest-config"
  - "https://developer.android.com/topic/performance/benchmarking/macrobenchmark-metrics"
---

# 26.14 性能实验统计与分位值回归判定

<!-- outline-start -->
## 要点

### 🔹 性能实验和灰度发布的边界
说明灰度发布回答“是否可以继续放量”，性能实验回答“某个方案是否造成可复核差异”。覆盖同质人群、同一时间窗、activation event 和 A/A 空转测试。

### 🔹 样本量不能只靠 baseline 与 MDE
整理 baseline、minimum detectable effect、alpha、power、历史方差、完整分布、allocation ratio 对样本量的影响，区分均值、比例和分位值三类检验对象。

### 🔹 P90/P99 的置信区间与尾部违约率
建立分位值实验的判定口径：bootstrap confidence interval、quantile confidence interval、tail violation rate、阈值超标率，避免把单个 P90 delta 当作稳定结论。

### 🔹 分群归因不能线性相加 P90
按设备档位、Android 版本、刷新率、启动类型、网络状态拆分分布；归因时看尾部样本来源、超阈值样本占比和分群权重，不用“样本量 × P90 delta”做结论。

### 🔹 SRM、采样和上报完整性
覆盖 Sample Ratio Mismatch、采样率切换、数据到达率、延迟上报、variant 崩溃导致的样本缺失，以及上报组件自监控字段。

### 🔹 CI 门禁与线上实验的证据对齐
把 Macrobenchmark 的 `FrameTimingMetric`、启动指标、固定设备基线和线上 P90/P99 / 慢帧率 / Crash / ANR 护栏指标放到同一张判定表里。

## 扩展

### 🔸 Sequential testing 与频繁看数风险
记录中途多次看数、提前停止、alpha spending、FDR 对发布决策的影响。

### 🔸 长尾分布的异常值处理
整理 winsorization、trimmed mean、分桶重算和异常样本回查的适用边界。

<!-- outline-end -->

> 本节内容待加工。
