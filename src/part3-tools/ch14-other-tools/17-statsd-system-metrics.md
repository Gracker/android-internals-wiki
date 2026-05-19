---
title: "statsd 与系统级指标采集"
chapter: "14.17"
status: draft
applicable_versions: "Android 11 (API 30) - Android 17 (API 37)"
tags: [statsd, observability, perfetto, tools]
related_chapters: ["13.9", "13.10", "14.10", "15.3", "26.3"]
created_by: "task2a-knowledge-gap"
created_date: "2026-05-20"
gap_source: "AOSP结构/官方文档/已有章节深挖"
---

# 14.17 statsd 与系统级指标采集

<!-- outline-start -->
## 要点

### 🔹 statsd 在 Android 观测体系中的位置
说明 statsd、StatsCompanionService、StatsLog、atoms.proto 与 Mainline 模块的分工，明确它和 Perfetto、logcat、dumpsys 各自回答的问题。

### 🔹 Atom 模型：pushed、pulled 与 metric 配置
梳理 pushed atom、pulled atom、event metric、duration metric、gauge metric 的用途，以及配置、触发、聚合、拉取报告的基本路径。

### 🔹 性能排障常见数据入口
整理 ANR、JobScheduler、LMK、Game Mode、UprobeStats、功耗相关 atom 在排障中的使用方式，避免把 statsd 事件误当成完整 trace。

### 🔹 adb / cmd stats 调试流程
给出本地验证路径：推送配置、触发场景、拉取报告、清理配置，并说明 shell 权限、userdebug / eng 与量产机差异。

### 🔹 与 Perfetto、logcat、dumpsys 的交叉验证
建立排障顺序：statsd 定位事件是否发生，Perfetto 还原时序，logcat / dumpsys 补系统状态，避免单一信号误判。

### 🔹 权限、版本与 OEM 边界
说明 StatsD APEX、Android 版本差异、厂商 atom 扩展、隐私限制和线上采集边界，给出适合写进排障手册的安全用法。

## 扩展

### 🔸 Tradefed / CTS 中的 statsd collector
补充测试框架如何下发 statsd 配置、收集指标，以及适合做性能回归门禁的场景。

### 🔸 statsd report 与线上 APM 的边界
讨论 statsd 更适合系统级事件和聚合指标，线上 APM 更适合 App 内埋点、用户路径和业务维度。

### 🔸 自定义 Atom / 厂商扩展的兼容性风险
记录自定义 atom、vendor atom、版本升级和字段语义变化对长期指标看板的影响。

<!-- outline-end -->

> 本节内容待加工。
