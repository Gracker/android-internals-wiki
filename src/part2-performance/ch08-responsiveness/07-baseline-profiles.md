---
title: "Baseline Profiles 与编译优化实践"
chapter: "8.7"
status: draft
applicable_versions: "Android 9 (API 28) - Android 17 (API 37)"
tags: [Baseline Profiles, Profile-Guided Optimization, dex2oat, 启动优化, AGP, app-speed-index]
related_chapters: ["1.7", "1.12", "8.2", "8.3"]
created_by: "task2a-knowledge-gap"
created_date: "2026-04-05"
gap_source: "官方文档"
---

# 8.7 Baseline Profiles 与编译优化实践

<!-- outline-start -->
## 要点

### 🔹 锚点 1：为什么需要 Baseline Profiles
- ART 的 AOT 编译策略演变：从全量编译到解释执行到 Profile-Guided
- 首次安装后的冷启动性能问题：dex2oat 的编译时机与范围
- Baseline Profiles 的本质：开发者在 APK 中预置的"热点方法清单"
- Google Play 在分发时利用 profiles 做云端编译优化
- 实测数据：Baseline Profiles 可提升约 30% 的首次启动速度

### 🔹 锚点 2：Baseline Profiles 的工作机制
- human-readable profile 格式 (HRPF) 与二进制格式
- APK 签名过程中 profile 的打包位置
- 安装时 dex2oat 如何消费 Baseline Profiles
- Cloud Profiles（Google Play 服务端聚合的 profile）与 Baseline Profiles 的合并
- Android 13+ 的 ART Service 如何管理 profile

### 🔹 锚点 3：生成与维护 Baseline Profiles
- 使用 Macrobenchmark 库生成 profiles
- Android Studio 的 Baseline Profile 模块向导
- Gradle 插件自动化：generateBaselineProfile task
- 稳定的 profile 需要覆盖的关键路径：冷启动、热启动、核心用户旅程
- Profile 的版本管理：随 APK 一起更新

### 🔹 锚点 4：与 AutoFDO 的关系与区别
- AutoFDO（1.12 节）：系统级，基于硬件性能计数器的反馈优化
- Baseline Profiles：应用级，基于代码路径覆盖的编译优化
- 两者互补：AutoFDO 优化 native 代码，Baseline Profiles 优化 dex 代码
- 在 OEM 构建流程中的配合使用

### 🔹 锚点 5：在 Perfetto 中验证 Baseline Profiles 的效果
- 对比安装/未安装 profiles 的启动 trace
- dex2oat 编译时间的变化
- 方法 JIT 编译 vs AOT 编译的 trace 特征
- 使用 app-speed-index 指标量化改善

### 🔹 锚点 6：常见问题与最佳实践
- Profile 过大导致 dex2oat 编译时间增加的反效果
- 多 dex 文件的 profile 管理策略
- Android App Bundle (AAB) 与 Baseline Profiles 的打包关系
- 非 Google Play 渠道（侧载、国内商店）的 profile 处理
- Library 的 Baseline Profiles 与 App 的合并

### 🔹 锚点 7：Jetpack Compose 与 Baseline Profiles
- Compose 运行时对 Baseline Profiles 的依赖
- Google 提供的 Compose library profiles
- 为什么 Compose 应用更需要 Baseline Profiles

## 扩展

### 🔸 扩展点 1：Profileable 应用与性能分析
- Android 13+ 的 profileable 标志对 profile 采集的影响

### 🔸 扩展点 2：OEM 系统镜像级别的编译优化
- system_server 和 framework 的预编译 profile
- System Baseline Profiles 在系统启动优化中的作用

<!-- outline-end -->

> 本节内容待加工。
