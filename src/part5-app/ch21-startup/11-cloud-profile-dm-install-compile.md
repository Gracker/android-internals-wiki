---
title: "云端 Profile、DM 文件与安装后编译优化"
chapter: "21.11"
status: draft
applicable_versions: "Android 7 (API 24) - Android 16 (API 36)"
tags: [startup, art, baseline-profile, dexopt, cloud-profile]
related_chapters: ["1.7", "8.2", "21.4", "21.8"]
created_by: "task2a-knowledge-gap"
created_date: "2026-05-20"
gap_source: "素材驱动/AOSP结构/官方文档"
---

# 21.11 云端 Profile、DM 文件与安装后编译优化

<!-- outline-start -->
## 要点

### 🔹 云端 Profile 在启动优化里的位置
说明 Play 分发的 cloud profile、应用随包提供的 baseline profile、设备本地 JIT profile 分别影响哪一段启动成本，避免把编译收益和业务初始化收益混在一起评估。

### 🔹 DM 文件与 ART 编译模式
梳理 `.dm` 文件进入安装过程后的使用方式，覆盖 verify、speed-profile、speed 等常见编译模式，并标出不同模式对安装耗时和首次启动耗时的影响。

### 🔹 dex2oat、bg-dexopt-job 与空闲编译
解释安装时编译、后台空闲编译、系统维护窗口之间的关系，给出排查启动慢时需要同时观察的系统事件和命令入口。

### 🔹 Profile 命中率与冷启动收益评估
建立验证口径：同一版本、同一设备、清除本地 profile、区分首次启动与稳定启动，用 P50/P90/P99 分位值判断编译优化是否改变启动曲线。

### 🔹 灰度发布中的 Profile 风险
覆盖错误 profile、过窄场景、动态特性模块、热修复和 R8 混淆变更带来的失效场景，说明线上回归需要看启动耗时、安装耗时和崩溃率三类指标。

### 🔹 与 Baseline Profile 实战的分工
本节聚焦系统如何消费 profile 与如何验证效果；生成规则、Macrobenchmark 录制和 Gradle 集成详见 21.4 节。

## 扩展

### 🔸 厂商 ROM 编译策略差异
对比不同设备的 `pm compile` 默认策略、维护窗口频率和省电模式影响，形成启动回归排查清单。

### 🔸 动态特性模块与 Play 分发
补充 App Bundle、按需模块和 cloud profile 覆盖范围之间的关系，说明多模块应用的 profile 验证边界。

<!-- outline-end -->

> 本节内容待加工。
