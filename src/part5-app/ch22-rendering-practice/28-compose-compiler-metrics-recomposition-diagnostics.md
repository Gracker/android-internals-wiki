---
title: "Compose Compiler Metrics 与 Recomposition 诊断体系"
chapter: "22.28"
status: draft
applicable_versions: "Android 12 (API 31) - Android 17 (API 37)"
tags: [compose, compiler, recomposition, diagnostics, stability]
related_chapters: ["22.3", "22.20", "22.25", "22.26"]
created_by: "task2a-knowledge-gap"
created_date: "2026-06-27"
gap_source: "章节深挖+官方文档"
gap_score: 17
---

# 22.28 Compose Compiler Metrics 与 Recomposition 诊断体系

<!-- outline-start -->
## 要点

### 🔹 Compose Compiler Metrics 输出结构
- 编译器报告的生成方式：compose-compiler-gradle-plugin reports 参数
- 报告文件组织：模块级 .txt + 类级 detail
- stability-inference.csv 与 recomposition-reasons.txt 的字段含义

### 🔹 Stability 推断机制
- Composable 函数参数的 stable/unstable 判定规则
- @Stable 与 @Immutable 注解的边界
- 集合类型（List、Map、Set）的 unstable 默认行为与绕过方式
- 强类型（data class）的自动 stable 推断条件

### 🔹 Recomposition 原因解读
- recomposition-reasons 输出格式解析
- 参数级变更追踪：哪个参数变了、为什么变了
- 高频 recomposition 热点识别方法
- @SkippableComposable 缺失的原因分析

### 🔹 Strong Skipping 模式下的诊断差异
- Strong Skipping（Compose 1.6+）开启前后 metrics 输出的区别
- 不稳定参数但不触发 recomposition 的场景
- Stability Inference 与 Skippable 的关系

### 🔹 Compose Runtime Metrics 与运行时观测
- Compose Tracking（setTracingFlag）的运行时开销
- Composition 的 Snapshot 级别观测：registerObservedReads
- recompose 与 applyChanges 的时间线关联
- Perfetto 中 Compose 相关 slice 的含义

### 🔹 诊断工作流：从 Metrics 到修复
- Step 1：生成全项目 compiler metrics
- Step 2：grep unstable 定位问题函数
- Step 3：结合 recomposition-reasons 分析根因
- Step 4：修复后用 Layout Inspector / Compose Preview 验证
- Step 5：回归 Baseline Profile 确认收益

### 🔹 与 Perfetto trace 的交叉验证
- Composable 函数在 trace 中的 slice 模式
- composition / measure / draw / layout 阶段的时间分布
- 高频 recomposition 在 trace 中的识别特征

## 扩展

### 🔸 CI 集成：自动化 Stability 回归检测
- 将 compiler metrics 解析集成到 CI pipeline
- unstable 函数增量告警机制
- Stability 破坏检测：PR 级别 diff 比对

### 🔸 Compose 1.7+ Compiler 重构对 Metrics 的影响
- 新编译器（K2 编译器插件）输出格式变化
- 旧 metrics 字段的兼容性

<!-- outline-end -->

> 本节内容待加工。

[结构参考: Compose 官方文档 — Compose Compiler Metrics & Stability]
[适用版本: Android 12 - Android 17 / Compose 1.4+]
