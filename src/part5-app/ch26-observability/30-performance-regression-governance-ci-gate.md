---
title: "性能防劣化体系与 CI 门禁实战"
chapter: "26.30"
status: draft
applicable_versions: "Android 10 (API 29) - Android 17 (API 37)"
tags: [性能防劣化, CI门禁, Macrobenchmark, 自动化测试, 性能基线]
related_chapters: ["15.10", "14.27", "26.07", "26.18"]
created_by: "task2a-knowledge-gap"
created_date: "2026-07-17"
gap_source: "方法论缺口+Macrobenchmark生态+行业实践"
confidence: high
---

# 26.30 性能防劣化体系与 CI 门禁实战

<!-- outline-start -->
## 要点

### 🔹 性能防劣化体系全景
- 性能劣化的成因分类：代码劣化、依赖升级、SDK 变更、系统行为变更
- 防劣化的三层防线：PR 级（即时）→ 合并级（每日）→ 发布级（发版前）
- 性能预算（Performance Budget）的概念与制定原则

### 🔹 性能基线建设
- 基线指标选型：启动耗时（P50/P90/P99）、帧率（Jank 率/大卡顿率）、内存（PSS/Java Heap/Native）
- 基线数据的采集方法：Macrobenchmark + 真机矩阵 + 厂商云真机
- 基线漂移检测：统计学方法（控制图/置信区间）vs 固定阈值
- 基线版本管理：历史基线快照、对比基线选择策略

### 🔹 Macrobenchmark CI 集成
- Macrobenchmark 在 CI 中的运行策略（定期 vs 每次提交 vs 手动触发）
- Benchmark 结果的 JSON 输出格式与解析
- CI 环境一致性挑战：设备状态、热节流、后台干扰
- 多设备基准矩阵：高端机/中端机/低端机的分层基线

### 🔹 Baseline Profile 自动化门禁
- Baseline Profile 生成与验证的 CI 流水线
- Profile 变更对启动耗时的回归检测
- Profile 与 AGP / R8 / AOT 编译的版本对齐

### 🔹 发布门禁实战
- 发版前性能 Checklist 的自动化
- 灰度阶段的性能指标监控与回滚判定
- 性能劣化的自动告警机制（Slack/飞书/钉钉通知）

### 🔹 性能治理组织实践
- 性能 Owner 制度的建立与运作
- 性能周报/月报的自动化生成
- 性能 OKR 与团队绩效的关联方式

## 扩展

### 🔸 开源工具链对比
- Macrobenchmark vs Firebase Performance vs 商业 APM 的定位差异
- gradle-plugin / GitHub Actions / GitLab CI 的集成方案
- Perfy / Crusoe 等社区工具的适用场景

### 🔸 性能回归的统计分析方法
- A/B 测试中的性能指标显著性检验
- P值 vs 效应量 vs 置信区间的正确解读
- 样本量计算与实验设计

### 🔸 云真机 vs 本地真机 vs 模拟器
- 各方案的性能保真度对比
- Firebase Test Lab / 华为云真机 / WeTest 的适用场景
- 混合策略：本地高频 + 云端低频

<!-- outline-end -->

> 本节内容待加工。
[结构参考: Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间.md]
