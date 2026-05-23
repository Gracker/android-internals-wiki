---
title: "R8 Configuration Analyzer 与 keep 规则体积归因"
chapter: "14.20"
status: draft
applicable_versions: "Android Gradle Plugin 8.0+ / Android Studio 2026+"
tags: [r8, app-size, build-tools, keep-rules, apk-optimization]
related_chapters: ["12.1", "25.7", "14.1"]
created_by: "task2a-knowledge-gap"
created_date: "2026-05-23"
gap_source: "官方文档"
---

# 14.20 R8 Configuration Analyzer 与 keep 规则体积归因

<!-- outline-start -->
## 要点

### 🔹 R8 Configuration Analyzer 解决的问题
说明它面向的是 keep 规则过宽、默认 AGP 规则、consumer rules 与 App 自定义规则叠加后造成的优化空间损失；区别于 APK Analyzer 的“结果体积查看”。

### 🔹 输入材料与报告产物
梳理生成分析数据所需的构建产物、规则来源、impactful rules、subsumed rules、历史对比文件，以及报告中哪些字段适合进入 CI。

### 🔹 keep 规则影响分级
按“阻止 shrinking / obfuscation / optimization / attribute pruning”的影响拆分规则代价，说明 `allowshrinking`、`allowobfuscation`、`allowoptimization` 的使用边界。

### 🔹 典型高风险规则模式
覆盖包级 `-keep class ** { *; }`、反射框架兜底规则、序列化字段保留、JNI 入口、ServiceLoader、注解与泛型签名等场景，给出排查顺序。

### 🔹 与 R8 full mode 迁移的配合
说明 AGP 8.0+ full mode 下 analyzer 如何帮助定位兼容问题，同时避免把 full mode 关闭当作长期方案。

### 🔹 CI 与回归治理
给出基线包、候选包、规则差异、dex size、mapping / seeds / usage 文件的归档方式，定义“规则变宽”的评审门槛。

### 🔹 与 APK Analyzer / apkanalyzer 的边界
APK Analyzer 看最终 APK 组成，R8 Configuration Analyzer 看规则为什么阻止优化；两者在体积排查中应按先结果、后原因的顺序配合。

## 扩展

### 🔸 反射与代码生成框架的 keep 规则模板
后续可整理 Gson、Moshi、Jackson、Room、Hilt、Retrofit、JNI 注册和插件化框架的最小规则模板。

### 🔸 R8 Analyzer 与 AI agent 辅助评审
官方 android/skills 中已有 r8-analyzer skill，可作为规则审查和报告摘要的工具链参考，但需要保留人工复核环节。

<!-- outline-end -->

> 本节内容待加工。
