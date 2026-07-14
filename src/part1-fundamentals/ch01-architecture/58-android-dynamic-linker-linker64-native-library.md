---
title: "Android Dynamic Linker (linker64) 架构与 Native 库加载性能边界"
chapter: "1.58"
status: "draft"
applicable_versions: "Android 10 (API 29) - Android 17 (API 37)"
tags: [linker64, dynamic-linker, ELF, dlopen, namespace, RELRO, native-library, bionic]
related_chapters: [1.15, 1.55, 8.11]
created_by: "task2a-knowledge-gap"
created_date: "2026-07-15"
gap_source: "AOSP结构"
---
# 1.58 Android Dynamic Linker (linker64) 架构与 Native 库加载性能边界

<!-- outline-start -->
## 要点

### 🔹 linker64 内部架构：ELF 解析 → 依赖图 → 重定位 → 初始化
{基于缺口分析生成的锚点内容}

### 🔹 Linker Namespace 隔离机制：system / vendor / product 命名空间
{基于缺口分析生成的锚点内容}

### 🔹 Lazy Binding vs RELRO：即时绑定与只读重定位的性能-安全权衡
{基于缺口分析生成的锚点内容}

### 🔹 dlopen 异常处理与构造函数/析构函数链
{基于缺口分析生成的锚点内容}

### 🔹 Android 17 linker 变更：MTE 感知、16KB Page Size 适配
{基于缺口分析生成的锚点内容}

### 🔹 Native 库加载延迟模型：so 文件数量、依赖深度与冷启动
{基于缺口分析生成的锚点内容}

## 扩展

### 🔸 JNI_OnLoad 与 Native 注册的性能选择：动态注册 vs 静态注册
{可选深入方向}

### 🔸 so 文件优化：符号裁剪、strip、合并策略对加载性能的影响
{可选深入方向}

<!-- outline-end -->

> 本节内容待加工。
