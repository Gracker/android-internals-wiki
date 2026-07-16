---
title: "Compose Runtime Tracing — androidx.tracing 与 Perfetto 组合阶段追踪"
chapter: "22.37"
status: draft
applicable_versions: "Android 13 (API 33) - Android 17 (API 37)"
tags: [Compose, Tracing, Perfetto, Observability, Recomposition]
related_chapters: ["22.28", "22.3", "13.21", "26.1"]
created_by: "task2a-knowledge-gap"
created_date: "2026-07-16"
gap_source: "AOSP结构/官方文档"
---

# 22.37 Compose Runtime Tracing — androidx.tracing 与 Perfetto 组合阶段追踪

<!-- outline-start -->
## 要点

### 🔹 锚点 1：androidx.tracing.compose 架构与启用方式
- androidx.tracing:tracing 和 androidx.tracing:tracing-perfetto 模块架构
- CompositionTracer 接口：组合阶段追踪的钩子设计
- 启用方式：Debug 模式自动启用 vs Production 通过 API 显式开启
- tracing-perfetto 的 AAR 集成与 Systrace 回退机制

### 🔹 锚点 2：Compose 组合阶段的 Trace 事件
- recompose:start / recompose:end — 重组事件追踪
- compose:start / compose:end — 组合事件追踪
- subcompose:start / subcompose:end — 子组合事件追踪
- 每个事件的参数：受影响的 Composable 信息、重组原因
- Trace 事件与 FrameTimeline 的时序对齐

### 🔹 锚点 3：Perfetto 中分析 Compose 组合开销
- 在 Perfetto UI 中识别 Compose 重组 Track
- 重组频率热点定位：某 Composable 单帧重组次数
- 子组合嵌套深度的 Perfetto 可视化
- 重组与布局/绘制阶段的耗时占比分析
- 使用 Perfetto SQL 查询重组统计（与 13.22 Perfetto SQL Cookbook 联动）

### 🔹 锚点 4：生产环境 Compose Tracing 部署
- tracing-perfetto 在 Release 构建中的开销评估
- 采样策略：基于用户的灰度采样 vs 基于会话的触发式采样
- Trace 数据的线上收集与聚合
- 与现有 APM 框架（Firebase Performance / 自研 APM）的集成路径

### 🔹 锚点 5：重组归因与性能反模式识别
- 从 Trace 事件中提取重组原因（State 变化、强制重组、键值变化）
- 高频重组 Composable 的自动识别规则
- 无效重组（unnecessary recomposition）的 Trace 特征
- 与 Compose Compiler Metrics（22.28）交叉验证重组问题

### 🔹 锚点 6：与 Layout Inspector / Recompose Highlighter 的工具链协同
- Layout Inspector 的实时重组高亮 vs Perfetto 的离线深度分析
- 开发期调试工具与线上监控工具的能力边界
- 从开发期发现到线上验证的完整 Compose 性能工作流

## 扩展

### 🔸 扩展点 1：自定义 Trace Section 与 Composable 关联
- 使用 Trace.beginSection() 在自定义 Composable 中添加细粒度追踪
- Modifier.Node 架构下的自定义追踪粒度控制
- 追踪命名规范与 Perfetto Slice 聚合

### 🔸 扩展点 2：Compose Tracing 与 Macrobenchmark 集成
- 在 Macrobenchmark 测试中自动收集 Compose Trace
- 基线对比：重组次数回归检测
- CI/CD 中的 Compose 性能门禁自动化

<!-- outline-end -->

> 本节内容待加工。

[结构参考: 官方文档 developer.android.com/jetpack/androidx/releases/tracing]
[适用版本: Android 13 (API 33) - Android 17 (API 37)，tracing-perfetto 需 Compose 1.6+]
