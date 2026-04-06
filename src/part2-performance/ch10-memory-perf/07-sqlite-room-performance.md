---
title: "SQLite/Room 数据库性能优化"
chapter: "10.7"
status: draft
applicable_versions: "Android 8 (API 26) - Android 17 (API 37)"
tags: [SQLite, Room, database, ANR, CursorWindow, WAL, performance]
related_chapters: ["1.10", "4.1", "9.1", "10.1", "10.6"]
created_by: "task2a-knowledge-gap"
created_date: "2026-04-06"
gap_source: "AOSP结构+官方文档+读者需求"
---

# 10.7 SQLite/Room 数据库性能优化

<!-- outline-start -->
## 要点

### 🔹 锚点 1：为什么数据库操作是性能瓶颈
- 主线程数据库操作 → ANR 的经典路径
- CursorWindow Binder 1MB 限制与 TransactionTooLargeException
- 在 Perfetto 中识别 DB 相关耗时（SQLite trace 点、SQLiteDatabase lock 等待）
- 真实案例：一次慢查询拖垮整个应用的响应链

### 🔹 锚点 2：SQLite 内部机制与性能影响
- WAL（Write-Ahead Logging）vs 回滚日志模式：并发读写性能差异
- SQLite 的锁模型（SHARED / RESERVED / PENDING / EXCLUSIVE）
- Android SQLiteDatabase 的线程安全实现（SQLiteOpenHelper 的 getWritableDatabase 同步）
- page cache 与查询性能的关系

### 🔹 锚点 3：CursorWindow 与 Binder 传输瓶颈
- CursorWindow 内部结构：共享内存 + Binder 跨进程传输
- 2MB CursorWindow 限制的来源（Binder 事务大小限制）
- SQLiteCursor 的翻页重查机制（fillWindow）
- 大数据集的分页策略：Limit/Offset vs Keyset Pagination
- 与 §1.10 ContentProvider 性能的交叉关联

### 🔹 锚点 4：Room 的性能特性与优化
- Room 编译时 SQL 验证对性能的间接影响（减少运行时错误）
- Room 的 Transaction @Query 与 suspend 函数的线程模型
- Paging 3 的懒加载与预取策略对内存和滑动的影响
- Room 的 Migration 性能：大表 ALTER / CREATE 时的主线程阻塞风险

### 🔹 锚点 5：数据库优化的实战策略
- 事务批处理：BEGIN/COMMIT 包裹批量写入的性能提升（10x-100x）
- 索引策略：复合索引的列顺序对查询计划的影响
- EXPLAIN QUERY PLAN 的解读方法
- WITHOUT ROWID 表的使用场景
- PRAGMA 调优（journal_mode, synchronous, cache_size）

### 🔹 锚点 6：数据库与 ANR 的关联分析
- 主线程 DB 写入 → SQLiteLock → 其他读操作排队 → ANR traces 中的 SQLiteDatabase 锁
- ContentProvider + SQLiteDatabase 的组合死锁模式
- StrictMode 检测主线程 DB 操作
- 异步 DB 操作的线程池设计（单线程串行 vs 并发写入）

## 扩展

### 🔸 扩展点 1：SQLCipher 加密数据库的性能开销
- SQLCipher 的加密层对读写性能的量化影响
- 与原生 SQLite 的性能对比

### 🔸 扩展点 2：多进程数据库访问
- Multi-process SQLiteOpenHelper 的注意事项
- WAL 模式下多进程读写的并发行为
- 与 §1.10 多进程 ContentProvider 死锁的关联

<!-- outline-end -->

> 本节内容待加工。
