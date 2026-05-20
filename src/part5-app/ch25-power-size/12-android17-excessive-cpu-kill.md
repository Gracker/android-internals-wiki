---
title: "Android 17 Excessive CPU Kill 与后台任务功耗治理"
chapter: "25.12"
section: "25.12"
status: draft
applicable_versions: "Android 15 (API 35) - Android 17 (API 37)"
tags: [android-17, profiling-trigger, jobscheduler, workmanager, power, background-task]
related_chapters: ["5.10", "25.2", "25.4", "26.12", "11.2"]
created_by: "task2a-knowledge-gap"
created_date: "2026-05-20"
gap_source: "研究素材/官方文档/章节深挖"
gap_score: 18
sources:
  - type: clippings-structure-ref
    path: "Clippings/Android 性能优化 - CPU 优化（上）：合理使用线程池，提升 CPU 利用率.md"
  - type: clippings-structure-ref
    path: "Clippings/Android 性能优化 - CPU 优化（下）：减少 CPU 闲置时刻和等待，提升利用率.md"
  - type: clippings-structure-ref
    path: "Clippings/Android 性能优化 - 任务调度优化：线程+CPU，提升任务调度优先级.md"
  - type: research
    path: "/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/DeepResearch/2026-05-19-android-jobscheduler-profilingtrigger-version-boundary.md"
  - type: official
    path: "https://developer.android.com/about/versions/17/features"
  - type: official
    path: "https://developer.android.com/about/versions/17/release-notes"
  - type: official
    path: "https://developer.android.com/reference/android/os/ProfilingTrigger"
---

# 25.12 Android 17 Excessive CPU Kill 与后台任务功耗治理

<!-- outline-start -->
## 要点

### 🔹 Android 17 excessive CPU trigger 的能力边界
说明 `TRIGGER_TYPE_KILL_EXCESSIVE_CPU_USAGE` 解决的问题、返回物形态、与 `ProfilingManager` / `ProfilingTrigger` 的关系，并明确它不能替代 App 自己的后台任务治理。

### 🔹 与 JobScheduler quota 的关系
区分 JobScheduler / WorkManager 的配额、约束和调度延迟，与系统对异常 CPU 占用的终止与采样机制。重点说明两者可能观察同一类后台任务，但控制路径不同。

### 🔹 App 侧高 CPU 后台任务的常见成因
覆盖周期任务过密、链式 Work 堆积、重试风暴、日志压缩上传、数据库 vacuum / migration、图片转码、加密压缩、热循环轮询等场景。

### 🔹 线上证据采集与归因字段
设计后台任务 CPU 异常的证据包字段：work id、job id、uid、processName、threadName、triggerType、trace file、start reason、exit reason、battery state、network state、standby bucket。

### 🔹 治理策略：约束、合并、退避和熔断
按任务可延后程度设置约束，给出唯一任务、指数退避、失败隔离、分片执行、前台可见任务切换、远程开关和采样上限的实战策略。

### 🔹 Android 15-17 的版本化降级路径
Android 15 以前主要依赖 App 自建监控和 `ApplicationExitInfo`；Android 15+ 可结合 `ProfilingManager` 主动采集；Android 17 使用 trigger 结果做事后归因。需要列出低版本 fallback。

## 扩展

### 🔸 与 26.12 线上诊断能力的关系
26.12 负责讲版本化诊断 API；本节只讲后台任务功耗治理场景，避免重复解释 `ProfilingManager` 基础 API。

### 🔸 与 5.10 系统调度机制的关系
5.10 讲 JobScheduler / WorkManager 调度机制；本节讲 App 因后台 CPU 异常被系统采样或终止时如何定位和治理。

### 🔸 待验证阈值与厂商差异
记录 excessive CPU 触发阈值、kill signal、厂商自定义策略、实机触发条件等需要补充 trace 或源码证据的边界。

<!-- outline-end -->

> 本节内容待加工。
> 结构参考已读取：`Clippings/Android 性能优化 - CPU 优化（上）：合理使用线程池，提升 CPU 利用率.md`、`Clippings/Android 性能优化 - CPU 优化（下）：减少 CPU 闲置时刻和等待，提升利用率.md`、`Clippings/Android 性能优化 - 任务调度优化：线程+CPU，提升任务调度优先级.md`。后续加工只能借用知识点覆盖顺序和案例组织方式，禁止搬运原文段落。
