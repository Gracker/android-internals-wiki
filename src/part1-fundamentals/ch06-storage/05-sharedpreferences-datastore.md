---
title: "SharedPreferences/DataStore 性能与 ANR 优化"
chapter: "6.5"
status: draft
applicable_versions: "Android 1.0 (API 1) - Android 17 (API 37)"
tags: [sharedpreferences, datastore, anr, io, storage, performance]
related_chapters: ["6.1", "6.3", "9.1", "9.2", "8.2", "4.5"]
created_by: "task2a-knowledge-gap"
created_date: "2026-04-07"
gap_source: "AOSP结构+官方文档+读者需求+素材驱动"
gap_score: "18/20"
---

# 6.5 SharedPreferences/DataStore 性能与 ANR 优化

<!-- outline-start -->
## 要点

### 🔹 锚点 1：SharedPreferences 的设计缺陷与 ANR 根因
- SharedPreferences 的同步 I/O 模型为何会成为 Android 应用中最常见的 ANR 源头之一
- `apply()` 的异步假象：`apply()` 虽然不阻塞调用线程，但系统在 Activity/Service 生命周期切换时会强制 `fsync()` 等待未完成的写入
- `commit()` 的直接阻塞：在主线程调用 `commit()` 的完整调用链（XML 序列化 → 文件写入 → fsync）
- `await()` 和 `getSharedPreferences()` 的隐藏同步点
- SharedPreferences 在多进程场景下的数据丢失风险
- Perfetto 中如何定位 SharedPreferences 导致的 ANR（主线程 waiting for futex / Binder call → QueuedWork.waitToFinish）

### 🔹 锚点 2：SharedPreferences 源码级性能分析
- `SharedPreferencesImpl` 内部实现：内存缓存 + XML 文件 + NIO 写入
- `writeToFile()` 的完整流程（全量写入、无增量更新）
- `enqueueDiskWrite()` 与 `QueuedWork` 的关系
- Activity `onStop()` → `QueuedWork.waitToFinish()` → 主线程等待磁盘写入的链路
- 为什么在低端设备或高 I/O 负载时 SharedPreferences ANR 更频繁
- [待验证：Android 17 对 QueuedWork 的变更]

### 🔹 锚点 3：Jetpack DataStore 的架构与性能优势
- DataStore 基于 Kotlin Coroutines + Flow 的异步设计
- Preferences DataStore vs Proto DataStore 的选择策略
- DataStore 如何避免 SharedPreferences 的 ANR 链路（无 QueuedWork 依赖、无主线程 fsync）
- `updateData()` 的原子性保证（Single-process DataStore 的 file-level locking）
- DataStore 的迁移机制：`SharedPreferencesMigration` 的实现与性能影响
- Proto DataStore 的序列化开销分析（Protobuf vs XML）

### 🔹 锚点 4：SharedPreferences ANR 的实战分析案例
- 典型场景：`apply()` 后 `Activity.onPause()` 触发 `waitToFinish()` 导致 ANR
- 典型场景：`getSharedPreferences()` 首次加载大 XML 文件
- 典型场景：多进程 SharedPreferences 写入冲突
- 在 Perfetto 中的表现：主线程 SLEEPING/BLOCKED → `QueuedWork.waitToFinish`
- 在 `traces.txt` 中的特征：`android.app.QueuedWork.waitToFinish` 堆栈
- 量化数据：SharedPreferences ANR 在 Google Play 上报中的占比（[待补充]）

### 🔹 锚点 5：迁移策略与最佳实践
- 从 SharedPreferences 迁移到 DataStore 的路径规划
- 渐进式迁移策略（按模块逐步替换）
- 迁移期间的性能监控（对比迁移前后的 ANR 率）
- DataStore 的使用注意事项（单例模式、作用域管理、错误处理）
- 何时仍应使用 Room 而非 DataStore（结构化数据 vs 键值对数据）
- SharedPreferences 的 `commit()` 在后台线程的合理使用场景

### 🔹 锚点 6：在 Perfetto/工具中的表现
- SharedPreferences ANR 在 Perfetto 中的 Trace 特征
- DataStore 操作在 Perfetto 中的可追踪性
- 使用 Simpleperf/Perfetto 分析 SharedPreferences I/O 延迟
- 自定义 Trace Point 监控 DataStore 读写性能
- Android Studio Profiler 中的 SharedPreferences I/O 可见性

## 扩展

### 🔸 扩展点 1：Android 16/17 中 SharedPreferences 的变更
- Google 官方对 SharedPreferences 的废弃态度和时间线
- Android 17 行为变更中与存储 I/O 相关的变化
- [待验证]

### 🔸 扩展点 2：MMKV 与其他高性能 KV 存储方案
- 腾讯 MMKV 的 mmap 机制与性能优势
- MMKV vs DataStore vs SharedPreferences 的性能对比
- 在高并发场景下的选择策略

### 🔸 扩展点 3：多进程 KV 存储的安全方案
- ContentProvider 封装 SharedPreferences 的反模式
- 多进程场景下的正确存储方案（Room + ContentProvider / MMKV MultiProcess）
- 跨进程数据一致性保证

<!-- outline-end -->

> 本节内容待加工。
