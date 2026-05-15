---
title: "ART FinalizerDaemon 与 ReferenceQueue 性能边界"
chapter: "4.9"
status: draft
applicable_versions: "Android 8 (API 26) - Android 17 (API 37)"
tags: ["art", "gc", "memory", "finalizer", "referencequeue", "performance"]
related_chapters: ["4.3", "4.5", "10.2", "23.1"]
created_by: "task2a-knowledge-gap"
created_date: "2026-05-15"
gap_source: "素材驱动/章节深挖"
sources:
  - type: blog
    path: "Obsidian/DeepResearch/2026-05-09-art-finalizerdaemon-referencequeue-concurrency.md"
  - type: aosp
    path: "art/runtime/daemon.cc; art/runtime/reference_queue.cc（待源码版本复核）"
---

# 4.9 ART FinalizerDaemon 与 ReferenceQueue 性能边界

<!-- outline-start -->
## 要点

### 🔹 ReferenceQueue 与 FinalizerDaemon 的职责边界
区分 Java 引用队列、对象终结、ART daemon 线程和应用资源释放责任，避免把内存泄漏、终结延迟和 GC 暂停混成一个问题。

### 🔹 从 GC 标记到 finalizer 执行的路径
梳理对象进入待终结队列、FinalizerDaemon 取出并执行 finalize()、异常处理和超时监控的观察点。

### 🔹 ReferenceQueue 并发优化的版本口径
记录 Android 16/17 ART 对 ReferenceQueue / ConcurrentMessageQueue 相关优化的公开证据、源码路径和未验证边界。

### 🔹 队列堆积对内存与卡顿的影响
分析 finalizer 堆积、CloseGuard 警告、FD 泄漏、native handle 泄漏在 heap、threads、Perfetto 中的表现。

### 🔹 诊断流程与证据采集
给出 heap dump、`adb shell dumpsys meminfo`、ART log、Perfetto 线程轨道和 simpleperf 的组合观察方式。

### 🔹 工程治理边界
给出 `AutoCloseable`、显式 close、Cleaner、资源池和测试门禁的适用条件，说明 finalize() 不适合作为主释放路径。

## 扩展

### 🔸 Cleaner / CloseGuard / StrictMode 的组合使用
补充不同 API level 下可用性、误报来源和 CI 接入方式。

### 🔸 Native 资源释放与 Java wrapper 生命周期
补 JNI global ref、fd、GraphicBuffer、Bitmap native allocation 的排查模板。

<!-- outline-end -->

> 本节内容待加工。
