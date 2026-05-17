---
title: "耗电/发热伴随卡顿排障入口"
chapter: "7.16"
status: draft
applicable_versions: "Android 10 (API 29) - Android 17 (API 37)"
tags: [jank, power, thermal, perfetto, battery-historian]
related_chapters: ["5.5", "5.10", "7.15", "11.1", "13.2", "14.11", "25.1", "25.2"]
created_by: "task2a-knowledge-gap"
created_date: "2026-05-17"
gap_source: "章节深挖/研究素材/官方文档"
source_refs:
  - "intake/research-gaps.md#2026-05-17-7.15"
  - "https://perfetto.dev/docs/data-sources/battery-counters"
  - "https://perfetto.dev/docs/data-sources/cpu-freq"
  - "https://source.android.com/docs/core/power/thermal-mitigation"
  - "https://developer.android.com/topic/performance/power/battery-historian"
---

# 7.16 耗电/发热伴随卡顿排障入口

<!-- outline-start -->
## 要点

### 🔹 投诉入口拆分：掉帧、发热、掉电分别代表什么
把线上反馈拆成三类信号：用户看到的帧时间异常、设备进入热限制后的频率收缩、后台任务或网络重试带来的持续耗电。加工时需要给出一张分流表，说明每类信号优先看哪些轨道和指标。

### 🔹 Perfetto 联合采集模板
覆盖 FrameTimeline、sched、CPU frequency、GPU/Display 相关 counter、thermal status、android.power、network packets、wakelock 事件。模板要说明哪些字段依赖设备暴露 power rails / ODPM，缺失时如何降级。

### 🔹 CPU/GPU 持续负载与热限制判读
区分短时峰值、持续满载、频率被动下降和调度迁移。加工时要把 thermal status、CPU/GPU 频率、top-app 线程运行时间和 FrameTimeline jank 对齐，避免只看单帧耗时。

### 🔹 Wakelock、JobScheduler/WorkManager 与网络重试
整理后台保活、周期任务、失败重试、前台服务和网络连接在 Battery Historian / batterystats / Perfetto 中的观察入口。与 5.10、25.2 交叉引用，不重复展开后台调度机制。

### 🔹 渲染负载、刷新率与显示功耗
说明高刷新率、复杂动画、视频/地图/WebView 页面如何同时影响帧时间和显示/SoC 能耗。加工时只写排障路径，渲染原理引用 2.x、18.x 章节。

### 🔹 设备能力差异与证据等级
列出 Pixel / AOSP 设备、厂商设备、低端机在 power rail、thermal HAL、GPU counter、网络 counter 可见性上的差异。没有设备级证据时标注待验证，不写泛化结论。

## 扩展

### 🔸 Power rail 命名与 EnergyConsumer 对照
整理 rail / channel、EnergyConsumer、BatteryUsageStats 三套口径之间的区别，作为 11.1 与 25.1 的补充索引。

### 🔸 热状态驱动的线上降级策略
补充根据 thermal status / thermal headroom 调整动画、刷新率、网络重试和后台任务节奏的策略，但需要标注 API 版本和设备限制。

### 🔸 游戏、地图、视频、WebView 四类场景案例
每类场景给出采集配置、第一判断点和常见误判，案例材料不足时保留为待补充。

<!-- outline-end -->

> 本节内容待加工。
