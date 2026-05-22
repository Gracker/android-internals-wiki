---
title: "AppFlow：GB 级应用冷启动内存联合调度"
chapter: "16.8"
status: draft
applicable_versions: "Android 15 - Android 17（研究原型，非 AOSP 主线）"
tags: [aosp-performance, cold-start, memory-scheduling, lmkd, file-preload]
related_chapters: ["4.4", "6.3", "8.2", "16.7", "21.1"]
created_by: "task2a-knowledge-gap"
created_date: "2026-05-23"
gap_source: "研究素材 + 论文精读 + 官方/外部搜索"
sources:
  - type: paper
    path: "https://arxiv.org/abs/2603.17259"
  - type: note
    path: "/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/论文/Android-2026-05-23-AppFlow-ColdLaunch/03-精读.md"
  - type: research-feed
    path: "intake/research-feeds/2026-04-02-15-ch05-appflow-cold-launch-scheduler.md"
---

# 16.8 AppFlow：GB 级应用冷启动内存联合调度

<!-- outline-start -->
## 要点

### 🔹 大型应用冷启动的系统侧瓶颈
说明 GB 级应用在多任务场景下为什么会从 warm launch 退化为 cold launch：文件 I/O、页回收、后台进程杀灭三个机制互相影响，不能只按 App 初始化任务拆解。

### 🔹 AppFlow 的三段式调度模型
拆解 Selective File Preloader、Adaptive Memory Reclaimer、Context-Aware Process Killer 三个组件的职责边界，以及它们分别接入 Android Framework 与 Linux Kernel 的位置。

### 🔹 文件访问预测与预加载预算
解释启动文件热度、文件大小、预加载预算之间的关系：小文件用于降低 stall，大文件用于提升顺序吞吐。需要标注论文中 128KB 阈值与 100MB 预算属于实验设计，不是 Android 平台默认值。

### 🔹 预加载感知的页回收策略
说明 AppFlow 如何避免 kswapd/直接回收提前驱逐预加载页，以及这与 Android 现有 LMKD、zRAM、文件页/匿名页回收策略的差异。

### 🔹 Context-Aware Kill 与 LMKD 策略边界
围绕应用内存膨胀-重置周期，分析“杀掉谁”从单纯优先级排序变成收益/代价评估的问题，并对照现有 LMKD adj、PSI 触发和后台保活策略。

### 🔹 Perfetto 与线上指标如何验证
列出验证 AppFlow 类策略需要观察的证据：launch timeline、major/minor fault、block I/O、kswapd/direct reclaim、LMK kill、ApplicationExitInfo、启动 P90/P95/P99。

### 🔹 工程化接入风险
讨论该方案修改 Android Framework 与 Linux Kernel 的部署成本、CTS/VTS 风险、厂商内核维护成本，以及对文件系统、功耗、后台保活公平性的潜在影响。

## 扩展

### 🔸 与 Baseline Profile / 云端 Profile 的关系
比较代码路径预热、编译优化与文件页预加载的分工，避免把 dexopt 收益和 I/O 预加载收益混在一起。

### 🔸 与车载系统和端侧 LLM 应用的关系
补充车载多屏、端侧大模型、3D 游戏这类 GB 级负载为什么更容易触发该问题。

### 🔸 AOSP 可验证锚点
后续加工时核对 ActivityManagerService、UsageStatsManager、LMKD、mm/vmscan、readahead、zRAM 相关源码路径，区分论文原型与 AOSP 主线事实。

<!-- outline-end -->

> 本节内容待加工。
