---
title: "ART 去优化（Deoptimization）触发机制与性能影响"
chapter: "1.35"
status: draft
applicable_versions: "Android 12 (API 31) - Android 17 (API 37)"
tags: [art, deoptimization, deopt, jit, aot, performance, safepoint]
related_chapters: ["1.7", "1.13", "1.22", "8.7", "21.4"]
created_by: "task2a-knowledge-gap"
created_date: "2026-06-28"
gap_source: "AOSP结构/章节深挖"
---

# 1.35 ART 去优化（Deoptimization）触发机制与性能影响

<!-- outline-start -->
## 要点

### 🔹 去优化的本质：从编译代码回退到解释执行
{deopt 的定义、为什么需要 deopt、编译假设失效的场景}

### 🔹 Deopt 触发条件分类
{full_deopt / slot_deopt / implicit_deopt 三类触发条件的分类与差异}

### 🔹 类加载导致的去优化（CHA 失效）
{运行时新类加载使 AOT/JIT 编译阶段的内联和去虚化决策失效，触发 deopt}

### 🔹 Debuggable 应用的全面去优化
{debuggable=true 时 ART 的行为差异：解释执行、JIT 禁用、方法钩子}

### 🔹 Deopt 执行链路：DeoptCheckpoint 与栈遍历
{art/runtime/deopt_checkpoint.cc 的工作机制，线程到达 safepoint 后的栈帧重建流程}

### 🔹 Perfetto 中的 Deoptimization 事件识别与量化
{如何在 Perfetto trace 中识别 deopt slice，关联到触发原因，量化性能影响}

### 🔹 去优化与 JIT 重编译的循环：抖动场景
{反复 deopt → 重新 JIT → 再次 deopt 的场景，性能抖动的诊断方法}

## 扩展

### 🔸 Quickening 失效与 deopt 的关系
{1.22 中提到的 Quickening 机制，其失效如何触发 deopt}

### 🔸 Android 17 中 deopt 行为的变化
{Android 17 在 deopt 机制上的改进，包括 JIT code cache 策略调整}

### 🔸 Baseline Profile 如何减少 deopt 概率
{良好的 profile 覆盖如何让编译器做出更保守的去虚化决策}

### 🔸 Gradle 采样与 deopt：为什么 release build 不要 debuggable
{debuggable app 在 CI 测试与真实性能之间的差异}

<!-- outline-end -->

> 本节内容待加工。
