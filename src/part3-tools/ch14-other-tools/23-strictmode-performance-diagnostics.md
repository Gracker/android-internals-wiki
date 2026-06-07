---
title: "StrictMode 性能检查与开发期诊断"
chapter: "14.23"
status: draft
applicable_versions: "Android 9 (API 28) - Android 17 (API 37)"
tags: [strictmode, disk-read, disk-write, network, custom-penalty, performance-diagnostics]
related_chapters: ["15.6", "14.4", "21.3"]
created_by: "task2a-knowledge-gap"
created_date: "2026-06-07"
gap_source: "AOSP结构/官方文档/章节深挖"
---

# 14.23 StrictMode 性能检查与开发期诊断

<!-- outline-start -->
## 要点

### 🔹 锚点 1：StrictMode 的定位与设计目标
- StrictMode 是 Android 开发者选项级别的性能守卫工具
- 在 Debug 构建中自动启用，生产构建中关闭的设计模式
- 与正式线上监控（APM SDK）的互补关系：StrictMode 负责开发期提前发现，APM 负责线上捕获
- 适用的性能问题类型：主线程磁盘 I/O、主线程网络操作、未关闭的 Closeable 对象、Activity 泄漏

### 🔹 锚点 2：ThreadPolicy 配置与常用策略
- `detectDiskReads()` / `detectDiskWrites()`：主线程磁盘操作检测
- `detectNetwork()`：主线程网络操作检测
- `detectCustomSlowCalls()`：自定义慢调用标记
- `detectResourceMismatches()`：资源类型不匹配检测
- Penalty 策略选择：`penaltyLog()` vs `penaltyDeath()` vs `penaltyDialog()` 的适用场景
- 推荐 Debug 构建配置模板

### 🔹 锚点 3：VmPolicy 配置与内存泄漏检测
- `detectActivityLeaks()`：Activity 泄漏检测
- `detectLeakedClosableObjects()`：未关闭的 Closeable 对象检测
- `detectLeakedSqlLiteObjects()`：SQLite 对象泄漏检测
- `detectNonSdkApiUsage()`：非 SDK API 使用检测（Android 9+）
- `detectExplicitGc()`：显式 GC 调用检测
- Android 17 中的 VmPolicy 新增与变更

### 🔹 锚点 4：StrictMode 违规输出的分析
- Logcat 中 StrictMode 违规日志的格式与读取方法
- 违规堆栈中 `android.os.StrictMode$AndroidBlockGuardPolicy.onThreadPolicyViolation` 的含义
- 如何从堆栈追溯到具体的磁盘/网络操作来源
- 与 `dropbox` 系统标签（`system_app_strictmode`）的关联

### 🔹 锚点 5：自定义 StrictMode 策略进阶
- `StrictMode.setThreadPolicy()` 的动态启用/禁用
- `StrictMode.allowThreadDiskReads()` / `allowThreadDiskWrites()` 白名单机制
- 如何为已知的安全磁盘操作添加豁免（如 SharedPreferences apply() vs commit()）
- 自定义 `penaltyListener()` 接入自建日志系统

### 🔹 锚点 6：StrictMode 在 CI/CD 中的集成
- 在自动化测试（Espresso / UI Automator）中启用 StrictMode
- 将 StrictMode 违规纳入 CI 失败条件
- `penaltyDeath()` 在 CI 环境中的使用
- 结合 Firebase Test Lab 的 StrictMode 报告

### 🔹 锚点 7：StrictMode 的局限性与替代方案
- StrictMode 不检测的场景：后台线程的磁盘 I/O 延迟、Binder 调用耗时、GPU 操作
- StrictMode 与 Systrace/Perfetto 的互补关系
- 何时应该从 StrictMode 迁移到 Perfetto 自定义 trace 点
- StrictMode 的性能开销与不建议在生产构建启用的原因

## 扩展

### 🔸 扩展点 1：StrictMode 与 Jetpack Compose 的兼容性
- Compose 渲染管线中的 StrictMode 误报处理
- Compose 动画帧中的磁盘操作检测

### 🔸 扩展点 2：StrictMode 违规的自动修复建议
- 常见违规模式的修复模板（SharedPreferences、文件操作、数据库查询）
- Lint 规则与 StrictMode 的互补

### 🔸 扩展点 3：StrictMode 在多进程环境中的行为
- ContentProvider 进程中的 StrictMode 配置
- Service 进程中的 StrictMode 策略选择

<!-- outline-end -->

> 本节内容待加工。
