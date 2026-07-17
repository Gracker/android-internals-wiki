---
title: "DEX 体积优化实战"
chapter: "25.29"
status: draft
applicable_versions: "Android 12 (API 31) - Android 17 (API 37)"
tags: [dex, r8, d8, apk-size, code-shrinking, baseline-profile, multidex]
related_chapters: ["25.6", "25.7", "21.12", "1.57"]
created_by: "task2a-knowledge-gap"
created_date: "2026-07-17"
gap_source: "Clippings参考书驱动"
confidence: medium
---

# 25.29 DEX 体积优化实战

<!-- outline-start -->
## 要点

### 🔹 DEX 文件结构与体积构成
- DEX 二进制格式：header、string_ids、type_ids、proto_ids、field_ids、method_ids、class_defs、data
- 体积来源：代码量（方法数/类数）、字符串池、调试信息（LineNumberTable、LocalVariableTable）
- DEX 方法数 64K 限制与 Multidex 的体积代价 [结构参考: Clippings/Android 性能优化 - dex 文件的体积优化实战.md]

### 🔹 R8 Full Mode 与代码缩减
- R8 Full Mode vs Compat Mode 的体积差异
- Keep 规则精简：避免过度 Keep 导致死代码无法剔除
- `@Keep` 注解滥用检测与治理
- 规则合并与去重：`-whyareyoukeeping` 诊断无用 Keep
- 详见 25.7 节的 R8 基础 [已验证: 官方文档, developer.android.com/build/shrink-code]

### 🔹 D8 与 DexBuilder 选项调优
- `--release` 模式对 DEX 体积的影响
- `--min-api` 与 DEX 格式版本（DEX 037 vs 038+）
- DEX 方法内联对体积的影响

### 🔹 Debug 信息剥离与映射管理
- `-strip-debug`：移除 LineNumberTable 对崩溃堆栈的影响
- R8 `mapping.txt` 的保留与上传（Crash symbolicaton 依赖）
- ReTrace 工具与 mapping 文件管理流程
- 如何在减小体积的同时保证线上可调试

### 🔹 Multidex 体积代价与优化
- Multidex DEX 文件数量与冷启动耗时的关联
- Main Dex List 最小化：只保留启动必需类
- Android 17 Art 加载多 DEX 的并行化优化 [待验证: AOSP android-17.0.0_r1]
- 通过模块化/动态特性模块减少主 APK DEX 数量

### 🔹 Startup Profile 与 DEX 布局优化
- Baseline Profile 如何影响 DEX 内类排列顺序
- `.art` / `.oat` 文件大小与 DEX 布局的关系
- Startup Profile 生成与 DEX 体积的 trade-off
- 详见 21.12 节

### 🔹 字符串池与资源引用优化
- R.string.* 常量内联对 DEX 字符串池的影响
- 常量折叠与 R8 内联优化边界
- `@stringRes` 注解与 R8 keep 的冲突

### 🔹 ProGuard / R8 诊断与体积回归监控
- `--print-usage`：被剔除的代码清单
- `--print-seeds`：存活代码清单审计
- DEX 体积 CI 门禁：每 PR 对比 `dexcount` 指标
- `com.android.tools.build:apkzlib` 程序化解析 DEX 方法数

## 扩展

### 🔸 Kotlin Metadata 对 DEX 体积的影响
- Kotlin 内联函数生成的 bytecode 膨胀
- `@Metadata` 注解开销与 R8 对 Kotlin Metadata 的处理
- K2 编译器对生成 DEX 大小的影响

### 🔸 动态特性模块（DFM）的 DEX 拆分策略
- 按功能模块拆分 DEX 的最佳实践
- 模块间依赖与 DEX 重复代码检测
- 详见 25.8 节

### 🔸 DexArchive 与增量编译
- D8 的 DexArchive 机制
- 增量 DEX 构建对 CI 效率的影响
- 布局稳定性与可缓存性

<!-- outline-end -->

> 本节内容待加工。
