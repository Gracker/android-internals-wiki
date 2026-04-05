---
title: "AutoFDO 反馈导向编译优化"
chapter: "1.12"
status: draft
applicable_versions: "Android 16 (API 36) - Android 17 (API 37)"
tags: [autofdo, compilation, optimization, ART, profile-guided, dex2oat]
related_chapters: ["1.7", "8.3", "7.5"]
created_by: "task2a-knowledge-gap"
created_date: "2026-04-05"
gap_source: "研究素材/官方文档"
---

# 1.12 AutoFDO 反馈导向编译优化

<!-- outline-start -->
## 要点

### 🔹 锚点 1：AutoFDO 解决什么问题
- 传统 dex2oat 编译的局限：静态编译无法预知运行时热点
- Profile-Guided Optimization（PGO）的基本思路
- AutoFDO vs Manual FDO：自动化采集 vs 手动标注

### 🔹 锚点 2：AutoFDO 的工作机制
- 运行时 profile 采集：硬件性能计数器（PMU）采样
- profile 数据格式与传递路径
- 编译器如何利用 profile 信息（基本块排列、分支预测、内联决策）
- 与 dex2oat / ART 编译管线的集成点

### 🔹 锚点 3：与 Baseline Profiles 的关系与区别
- Baseline Profiles：开发者手动提供的热点方法列表
- AutoFDO：系统自动采集的全局 profile
- 两者是否互补、覆盖范围差异
- 在启动优化中的不同角色

### 🔹 锚点 4：Google 与 Honor 的合作案例
- Google 官方博客公布的实测数据
- Honor 设备上的具体性能提升
- 对冷启动、运行时性能的影响量化

### 🔹 锚点 5：Android 16 中的支持状态
- 系统级集成路径
- 开发者如何为 App 启用 AutoFDO
- AOSP 中相关源码路径

### 🔹 锚点 6：在 Perfetto / 工具中的观测
- 编译优化效果在 trace 中的体现
- 如何判断 App 是否受益于 AutoFDO

## 扩展

### 🔸 扩展点 1：其他平台的 FDO 实践（iOS、Windows）
### 🔸 扩展点 2：AutoFDO 对系统服务（system_server）的优化效果
### 🔸 扩展点 3：OEM 如何在系统镜像构建中利用 AutoFDO

<!-- outline-end -->

> 本节内容待加工。
