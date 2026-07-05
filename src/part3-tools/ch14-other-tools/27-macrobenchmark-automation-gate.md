---
title: "Macrobenchmark 框架与自动化性能门禁"
chapter: "14.27"
status: draft
applicable_versions: "Android 12 (API 31) - Android 17 (API 37)"
tags: [macrobenchmark, benchmark, ci, performance-gate, baseline-profile, androidx]
related_chapters: ["14.1", "21.4", "21.12", "8.7"]
created_by: "task2a-knowledge-gap"
created_date: "2026-07-05"
gap_source: "官方文档/AOSP结构"
---

# 14.27 Macrobenchmark 框架与自动化性能门禁

<!-- outline-start -->
## 要点

### 🔹 Macrobenchmark 框架定位与核心架构
- AndroidX Benchmark Macrobenchmark 库的定位：Google 官方推荐的端侧性能测量框架
- 与 Microbenchmark 的区别：Macrobenchmark 测量整体用户场景（启动、滑动、帧率），Microbenchmark 测量细粒度函数
- 核心架构：Instrumentation 测试 + MeasureRule + StatVerifier，运行在真机/模拟器上

### 🔹 基准测试类型与适用场景
- `StartupMode.COLD`：冷启动耗时测量（从 fork 到 first draw）
- `StartupMode.WARM`：温启动（进程已存在，Activity 需重建）
- `StartupMode.HOT`：热启动（Activity 在后台，仅需 onResume）
- `FrameTimingMetric`：帧渲染耗时与丢帧统计
- `TraceMetric`：从 Perfetto trace 中提取自定义指标
- `PowerMetric`：功耗指标采集（Android 17+ 增强支持）

### 🔹 Baseline Profile 自动化生成与验证
- 通过 Macrobenchmark 自动生成 Baseline Profile 的 `BaselineProfileRule`
- Generated vs Reference Profile 的差异分析与策略
- 与 Cloud Profile 自动分发机制的协同

### 🔹 CI/CD 性能门禁集成
- GitHub Actions / GitLab CI 中集成 Macrobenchmark 的架构
- 性能回归检测：`StatVerifier` 设定阈值（如 P90 启动时间 ≤ 800ms）
- 历史趋势可视化：将测量结果推送到 GitHub Pages / Firebase
- 多设备矩阵策略：高端/中端/入门级设备的阈值分级

### 🔹 Perfetto Trace 与 Macrobenchmark 协同
- `TraceMetric` 自定义 Perfetto SQL 查询提取指标
- 从 trace 中提取 Systrace 区域内的 ANR/Jank 关联数据
- 与 `PerfettoSdk` 的 in-app trace 标记联动

### 🔹 Android 17 Macrobenchmark 新特性
- PowerMetric 能力增强：细分 CPU/GPU/modem 功耗域
- ART Profile Installation 支持 Startup Profile 验证
- Compose Recomposition 计数自动统计

## 扩展

### 🔸 Macrobenchamrk 与内部 APM 平台对接
- 将 Macrobenchmark JSON 结果导入自建 APM 系统的数据管道
- 与线上性能数据对比验证（线下/线上一致性校验）

### 🔸 多模块/多变体基准测试策略
- Flavor + BuildType 组合下的基准测试矩阵
- Library 模块的独立基准测试（androidx-benchmark-junit4）
<!-- outline-end -->

> 本节内容待加工。
