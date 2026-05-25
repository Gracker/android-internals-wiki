---
title: "Startup Profile 与 DEX Layout 启动优化"
chapter: "21.12"
status: draft
applicable_versions: "Android 7 (API 24) - Android 17 (API 37)"
tags: [startup-profile, baseline-profile, dex-layout, startup-optimization, macrobenchmark]
related_chapters: ["21.1", "21.4", "8.7", "19.15", "1.7"]
created_by: "task2a-knowledge-gap"
created_date: "2026-05-25"
gap_source: "章节深挖/官方文档"
material_paths:
  - "src/part5-app/ch21-startup/04-baseline-profile-practice.md#扩展-Startup-Profile-与-Dex-Layout-优化"
  - "https://developer.android.com/topic/performance/baselineprofiles/dex-layout-optimizations"
  - "https://developer.android.com/topic/performance/baselineprofiles/overview"
  - "https://developer.android.com/topic/performance/baselineprofiles/debug-baseline-profiles"
  - "https://developer.android.com/topic/performance/baselineprofiles/configure-baselineprofiles"
---

# 21.12 Startup Profile 与 DEX Layout 启动优化

<!-- outline-start -->
## 要点

### 🔹 Startup Profile 与 Baseline Profile 的边界
说明 Startup Profile 只面向启动路径的 DEX 布局优化，Baseline Profile 面向启动与高频交互的 ART 预编译；两者可能由同一套 Macrobenchmark 脚本产出，但编译阶段和收益来源不同。

### 🔹 DEX Layout 优化如何影响冷启动
梳理 R8 根据 `startup-prof.txt` 调整 classes.dex 方法和类布局的路径，解释它主要降低启动阶段的类加载、页面故障、磁盘读取局部性成本，而不是替代业务初始化治理。

### 🔹 `includeInStartupProfile` 的场景选择
给出哪些 CUJ 应进入 Startup Profile：入口 Activity、首屏骨架、首屏 Compose/View 树、首屏路由和必要 SDK 初始化；同时说明搜索、滚动、详情页等非首屏路径应留在 Baseline Profile。

### 🔹 构建条件与产物检查
覆盖 AGP、R8、Macrobenchmark、`dexLayoutOptimization` 等配置要求，说明如何检查 `startup-prof.txt`、`baseline-prof.txt`、APK/AAB 内二进制 profile 和 DEX 布局结果。

### 🔹 度量方式与回归判断
用 Macrobenchmark 对比 `CompilationMode.Partial`、无 profile、仅 Baseline Profile、Baseline + Startup Profile 的结果，区分 TTID、TTFD、首帧前 CPU 时间、主线程 I/O、类加载耗时和方差。

### 🔹 维护风险与发布策略
说明规则过宽会增加启动路径外代码的磁盘读取成本，规则过窄会漏掉首屏路径；补充 CI 生成、profile diff review、登录态/弹窗/远程配置固定、灰度验证和异常回滚策略。

### 🔹 Android 版本与安装渠道边界
建立 Android 7+、Android 9+ Cloud Profile、Play 分发、本地安装、第三方商店与 Android 16 云端编译材料之间的边界，避免把某一渠道能力写成通用系统行为。

## 扩展

### 🔸 与 21.4 Baseline Profile 实战的分工
本节从 21.4 的扩展点拆出，21.4 保留 Profile 生成和治理主线，本节聚焦启动路径 DEX layout、构建产物和验证矩阵。

### 🔸 AOSP `profman` / `dex2oat` 验证入口
后续加工可结合 `art/profman/`、`art/dex2oat/` 和 AGP/R8 文档验证 profile 消费路径，不照搬官方示例代码。

### 🔸 失败案例
记录 Startup Profile 误覆盖非首屏路径、启动弹窗导致 profile 不稳定、CI 设备状态污染、首屏网络请求掩盖 DEX layout 收益等案例。

<!-- outline-end -->

> 本节内容待加工。
