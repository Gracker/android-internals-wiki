---
title: "26.29 JVMTI Agent — ART 运行时动态监控接口与线上方法追踪"
chapter: "26.29"
status: draft
applicable_versions: "Android 8.0 (API 26) - Android 17 (API 37)"
tags: [JVMTI, ART, runtime-monitoring, dynamic-instrumentation, profilo, method-tracing]
related_chapters: ["26.21", "26.23", "26.27", "1.35", "14.1"]
created_by: "task2a-knowledge-gap"
created_date: "2026-07-17"
gap_source: "Clippings参考书+AOSP源码+章节深挖"
---

# 26.29 JVMTI Agent — ART 运行时动态监控接口与线上方法追踪

<!-- outline-start -->
## 要点

### 🔹 JVMTI 是什么：JVM Tool Interface 的 Android 之旅
{JVMTI 定义、标准 JVM 工具接口规范、ART 如何实现 JVMTI 子集、与 Desktop JVM 的差异}

### 🔹 ART JVMTI 实现架构与能力边界
{art/runtime/jvmti 目录结构、agent 加载机制、支持的 capability 子集、与 OpenJDK JVMTI 的差异}

### 🔹 Agent 加载与卸载：JVMTI Agent_OnLoad / Agent_OnUnload 生命周期
{android.os.Debug.attachAgent、JVMTI 启动模式、attach 时机、卸载清理}

### 🔹 方法级性能监控：MethodEntry / MethodExit 事件
{如何注册方法进/出事件、采样 vs 全量、性能开销实测、与 Trace.beginSection 的对比}

### 🔹 字段访问监控：FieldAccess / FieldModification 事件
{监控对象字段读写、内存泄漏检测场景、 WatchpointDescription 用法}

### 🔹线上动态挂载与卸载策略
{生产环境安全 attach/detach、白名单控制、权限校验、与 ProGuard/R8 混淆的配合}

### 🔹 JVMTI vs 字节码插桩 vs XTrace：三大动态监控方案选型
{26.21 字节码插桩（编译期）vs 26.23 XTrace（ART hook）vs JVMTI（运行时 agent）的成本/精度/覆盖面对比}

## 扩展

### 🔸 Facebook Profilo 的 JVMTI 集成路径
{Profilo 如何在 Android 上使用 JVMTI、与 ATrace 收集的配合}

### 🔸 JVMTI 在内存泄漏检测中的高级用法
{TagObject / GetObjectsWithTags、堆快照增量标记}

### 🔸 JVMTI 性能开销量化与采样策略优化
{不同 capability 组合的 CPU 开销、内存开销、对帧率的影响}

<!-- outline-end -->

> 本节内容待加工。

[结构参考: Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 53.md]
