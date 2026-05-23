---
title: "vold、FUSE 与 Scoped Storage I/O 性能边界"
chapter: "6.6"
status: draft
applicable_versions: "Android 10 (API 29) - Android 17 (API 37)"
tags: [storage, fuse, scoped-storage, vold, io]
related_chapters: ["6.1", "6.2", "6.3", "24.12"]
created_by: "task2a-knowledge-gap"
created_date: "2026-05-24"
gap_source: "AOSP结构/官方文档/章节深挖"
gap_score: 16
---

# 6.6 vold、FUSE 与 Scoped Storage I/O 性能边界

<!-- outline-start -->
## 要点

### 🔹 Android 外部存储路径：vold、MediaProvider 与 FUSE
从 `/storage/emulated/0` 访问路径拆出 vold 挂载、FUSE 守护进程、MediaProvider 索引和 App 权限检查的边界。

### 🔹 SDCardFS 退场后 FUSE 的性能代价
梳理 Android 10 前后的 SDCardFS / FUSE 迁移，以及随机读写、目录遍历、权限检查带来的额外开销。

### 🔹 FUSE passthrough 与非 FUSE 访问模式
说明 passthrough 适用条件、MediaProvider 非 FUSE 通道，以及为什么媒体类批量访问不应直接压在 emulated storage 路径上。

### 🔹 Scoped Storage 下随机 I/O、批量扫描与媒体访问
把相册、下载目录、日志导出、缓存迁移这几类 App 场景拆成不同 I/O 模式，分别给出性能风险点。

### 🔹 Perfetto / dumpsys / strace 观察点
列出 `fuse`、`vold`、`media_provider`、block I/O、主线程 D 状态和 Binder 调用的排查入口。

### 🔹 App 侧优化策略：MediaStore、SAF、缓存与分片写
从可落地动作解释何时走 MediaStore、何时复制到 App 私有目录、何时做批量事务和后台迁移。

### 🔹 Android 10-17 的版本边界
对齐 scoped storage、SDCardFS deprecation、FUSE passthrough 和 MediaProvider 行为在不同 Android 版本中的差异。

## 扩展

### 🔸 FBE 与 16KB Page Size 对外部存储 I/O 的影响
补充加密层、页大小和块设备读写粒度对 FUSE 路径的放大效应。

### 🔸 厂商文件管理器 / 相册批量导入案例
收集图库首扫、文件管理器复制、聊天 App 媒体迁移中的 trace 证据。

<!-- outline-end -->

> 本节内容待加工。
