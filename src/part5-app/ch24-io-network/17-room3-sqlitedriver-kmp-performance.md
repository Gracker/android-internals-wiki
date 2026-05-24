---
title: "Room 3.0 与 SQLiteDriver 迁移性能边界"
chapter: "24.17"
status: draft
applicable_versions: "Android 8 (API 26) - Android 17 (API 37); Room 3.0 alpha"
tags: [room3, sqlite, sqlitedriver, kmp, ksp, database-performance]
related_chapters: ["10.7", "14.1", "19.14", "24.2"]
created_by: "task2a-knowledge-gap"
created_date: "2026-05-25"
gap_source: "官方文档/每日信息"
sources:
  - type: official
    path: "https://developer.android.com/jetpack/androidx/releases/room3"
  - type: official
    path: "https://android-developers.googleblog.com/2026/03/room-30-modernizing-room.html"
  - type: daily-info
    path: "intake/daily-info/2026-05-22.md"
---

# 24.17 Room 3.0 与 SQLiteDriver 迁移性能边界

<!-- outline-start -->
## 要点

### 🔹 Room 3.0 的变化边界
梳理 `androidx.room3` 新坐标、KMP 定位、SQLiteDriver 后端、KSP-only 编译链路和 Kotlin-only 生成代码，把它和 Room 2.x 的 SupportSQLite / KAPT / Java AP 路径区分清楚。

### 🔹 SQLiteDriver 对数据库 I/O 路径的影响
说明 Room 3.0 背后的 `androidx.sqlite` driver API 如何改变打开连接、事务执行、statement 复用和跨平台封装边界，避免把 API 迁移误写成单纯依赖升级。

### 🔹 KSP 与 schema 输出对构建性能的影响
覆盖 Room Gradle Plugin、schemaDirectory、可缓存构建、flavor 维度 schema 输出和 CI 校验，把编译耗时、增量构建和自动迁移验证放在同一个迁移清单里。

### 🔹 SupportSQLite 兼容层的使用策略
说明 `room3-sqlite-wrapper` 只适合迁移期兜底，哪些旧代码可以短期通过 wrapper 适配，哪些数据库访问应该直接迁到 driver API。

### 🔹 迁移前后的性能验证方法
给出查询耗时、事务耗时、主线程 I/O、数据库锁等待、冷启动打开数据库和 schema migration 的验证指标，连接到 Macrobenchmark、Perfetto、StrictMode 和 Android Studio Profiler。

### 🔹 KMP 场景的边界
说明 Android App 团队引入 Room 3.0 时应优先验证 Android 端数据路径；iOS、Desktop、Web/WASM 支持属于架构边界，不应反向污染 Android 端性能结论。

### 🔹 常见风险与回滚策略
整理 alpha 版本引入、KSP 配置缺失、旧 SupportSQLite 扩展点失效、自动迁移 schema 漏提交、DAO Java 源码处理和多模块迁移拆分等风险。

## 扩展

### 🔸 Room 2.x 到 Room 3.0 迁移 checklist
可整理依赖坐标、KSP、Gradle Plugin、schema、driver、wrapper 和测试用例的分步清单。

### 🔸 Room 3.0 与 DataStore / 原生 SQLite 选型
可补充不同数据量、查询复杂度、跨平台需求和启动路径敏感度下的选型边界。

### 🔸 Web/WASM SQLiteDriver 的跨端同步问题
可作为 KMP 扩展材料，讨论 WebWorkerSQLiteDriver 与离线同步策略，不作为 Android 端主线。

<!-- outline-end -->

> 本节内容待加工。
