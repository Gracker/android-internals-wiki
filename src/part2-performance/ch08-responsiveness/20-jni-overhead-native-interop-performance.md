---
title: "JNI 调用开销与 Native 互操作性能边界"
chapter: "8.20"
status: draft
applicable_versions: "Android 14 (API 34) - Android 17 (API 37)"
tags: ['jni', 'native-interop', 'jni-overhead', 'critical-region', 'android-17']
related_chapters: ['8.11', '8.19', '1.55']
created_by: "task2a-knowledge-gap"
created_date: "2026-07-16"
gap_source: "素材驱动"
---

# 8.20 JNI 调用开销与 Native 互操作性能边界

<!-- outline-start -->
## 要点

### 🔹 JNI 调用开销拆解：函数指针查找、参数 marshal、寄存器保存
### 🔹 Get<Type>ArrayElements vs Get<Type>ArrayRegion 性能对比
### 🔹 JNI Critical Region 与 ART GC 阻塞：PNR (Pause Not Responding) 风险
### 🔹 Local Reference / Global Reference 管理与泄漏
### 🔹 RegisterNatives vs动态查找（dlsym）性能差异
### 🔹 JNI 线程 attach/detach 开销与 ThreadLocal 管理
### 🔹 Android 17 ART JNI 内联优化与 16KB page size 影响
### 🔹 JNI 性能分析：Perfetto JNI trace 与 systrace 插桩

## 扩展

### 🔸 JNI 批量化调用模式设计
### 🔸 Native 线程创建开销（pthread_create 成本拆解）
### 🔸 AOSP JNI 性能 benchmark 参考

<!-- outline-end -->

> 本节内容待加工。

<!--
缺口分析摘要：JNI 调用开销在含 native 代码的应用（游戏、音视频、SDK）中是关键性能因素。全书 JNI overhead 仅 25 次提及且无专门章节，Native thread overhead 0 次提及。需覆盖：JNI 调用开销来源（寄存器保存/恢复、GC critical region）、GetByteArrayElements vs GetByteArrayRegion 性能差异、JNI 引用管理（Local/Global Reference）、JNI 与 ART GC 的交互（critical region 阻塞 GC）、Android 17 的 JNI 变更。
评分：16/20 ({'素材丰富度': 3, '相关性': 5, '读者需求度': 4, '时效性': 4})
-->
