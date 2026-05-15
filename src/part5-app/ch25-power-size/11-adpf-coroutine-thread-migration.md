---
title: "ADPF Hint Session 与协程线程迁移"
chapter: "25.11"
status: draft
applicable_versions: "Android 12 (API 31) - Android 16 (API 36)"
tags: ["adpf", "performancehintmanager", "coroutine", "power", "threading"]
related_chapters: ["5.9", "8.6", "11.2", "25.1", "25.2"]
created_by: "task2a-knowledge-gap"
created_date: "2026-05-15"
gap_source: "素材驱动/官方文档"
sources:
  - type: official
    path: "developer.android.com/games/optimize/adpf"
  - type: official
    path: "developer.android.com/reference/android/os/PerformanceHintManager"
  - type: official
    path: "developer.android.com/ndk/reference/group/a-performance-hint"
  - type: material
    path: "DeepResearch/2026-05-13-adpf-performancehint-session-kotlin-coroutine-analysis.md"
  - type: structure
    path: "Clippings/Android 性能优化 - 任务调度优化：线程+CPU，提升任务调度优先级.md"
---

# 25.11 ADPF Hint Session 与协程线程迁移

<!-- outline-start -->
## 要点

### 🔹 PerformanceHintManager Session 的线程绑定模型
{待加工：围绕该锚点补充事实、验证路径与实战判断。}

### 🔹 协程调度导致 tid 变化时的失效场景
{待加工：围绕该锚点补充事实、验证路径与实战判断。}

### 🔹 setThreads、close、reportActualWorkDuration 的边界
{待加工：围绕该锚点补充事实、验证路径与实战判断。}

### 🔹 Android 15/16 flagged API 与 GPU hint 差异
{待加工：围绕该锚点补充事实、验证路径与实战判断。}

### 🔹 非游戏业务使用 ADPF 的判定条件
{待加工：围绕该锚点补充事实、验证路径与实战判断。}

### 🔹 功耗、温控与响应速度的联合验证方法
{待加工：围绕该锚点补充事实、验证路径与实战判断。}

## 扩展

### 🔸 主线程、RenderThread、业务线程的 session 组织方式
{待补充：素材充分时展开。}

### 🔸 与 Macrobenchmark / Perfetto 的验证脚本
{待补充：素材充分时展开。}

<!-- outline-end -->

> 本节内容待加工。
