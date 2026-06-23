---
title: "TaskSnapshot 系统架构与 Recents 渲染性能"
chapter: "2.29"
status: draft
applicable_versions: "Android 9 (API 28) - Android 17 (API 37)"
tags: [tasksnapshot, recents, overview, rendering, memory, surfaceflinger]
related_chapters: ["2.6", "2.13", "2.15", "4.1", "4.11", "8.2"]
created_by: "task2a-knowledge-gap"
created_date: "2026-06-24"
gap_source: "AOSP结构+章节深挖"
gap_score: 14
---

# 2.29 TaskSnapshot 系统架构与 Recents 渲染性能

<!-- outline-start -->
## 要点

### 🔹 锚点 1：TaskSnapshot 的触发时机与捕获机制
TaskSnapshotController 在哪些系统事件中触发快照捕获：Task 切到后台、App transition（home/recents）、进程 freeze。captureTaskSnapshot 的执行线程和时机约束：在 SurfaceFlinger 下一帧合成前完成 GraphicBuffer 读取。snapshot 捕获与 Activity onPause 的时序关系。Android 12+ 使用 HardwareBuffer 替代 Bitmap 的性能收益。[适用版本: Android 9+，Android 12+ HardwareBuffer]

### 🔹 锚点 2：Snapshot 内存模型与压力管理
单个 TaskSnapshot 的内存占用计算：分辨率 × 像素格式（RGBA_8888 = 4 bytes/pixel）。典型设备（1080p/1440p）的单张快照大小：8-16 MB。多任务场景下 snapshot 总内存占用：10 个后台 Task 可达 80-160 MB。系统的 snapshot 缓存策略：LRU 淘汰、内存压力下的主动释放。与 lmkd 的协调机制：snapshot 内存是否计入 cached memory 阈值判定。[适用版本: Android 9+]

### 🔹 锚点 3：Snapshot 持久化与重启后恢复
TaskSnapshotPersister 的磁盘写入策略：序列化路径（/data/system/app_snaps/）、写入时机（异步、低优先级）、文件格式。设备重启后 snapshot 加载的性能开销：反序列化延迟、按需加载策略。持久化 snapshot 在 low-RAM 设备上的禁用策略。Android 14+ 的 snapshot 持久化改进。[适用版本: Android 9+]

### 🔹 锚点 4：Recents/Overview 渲染管线中的 Snapshot 使用
RecentsAnimationController 如何协调 live tile 和 snapshot 的显示策略。动画启动阶段：从 snapshot 过渡到 live render 的切换时机。SurfaceFlinger 层面：snapshot 作为 SurfaceControl layer 的合成路径（texture layer vs buffer layer）。snapshot 缩放渲染的颜色空间转换开销。[适用版本: Android 9+，Android 12+ 改进]

### 🔹 锚点 5：低内存设备与极端场景的 Snapshot 降级
Low-RAM 设备（≤ 4GB）的 snapshot 策略：降低分辨率、跳过持久化、减少缓存数量。doze/standby 模式下的 snapshot 刷新策略。进程被 lmkd 杀掉后的 snapshot 保留策略（用户看到的是"尸体照片"）。Cached App Freezer 冻结进程的 snapshot 有效性判定。[适用版本: Android 9+]

### 🔹 锚点 6：折叠屏与多显示器的 Snapshot 复杂度
折叠态 → 展开态时 snapshot 分辨率不匹配问题：snapshot 是折叠态分辨率，recents 在展开态分辨率下渲染。inner/outer display 切换时的 snapshot 丢失。多显示器场景：每个 display 独立 snapshot vs 共享 snapshot。Android 14+ 对多显示器 snapshot 的改进支持。[适用版本: Android 12+ foldable]

### 🔹 锚点 7：TaskSnapshot 性能观测方法
dumpsys activity tasks 的 snapshot 信息字段含义。Perfetto 中 snapshot 相关的 trace slice（SurfaceFlinger::captureSurface、TaskSnapshotController::snapshot）。adb shell dumpsys SurfaceFlinger 中 snapshot layer 的识别。snapshot 捕获延迟的测量方法。[适用版本: Android 9+]

## 扩展

### 🔸 扩展点 1：TaskSnapshot 与 Activity Transition 动画的协同
从 Activity A 切到 Activity B 时，snapshot 如何被用于过渡动画。与 Material motion 的配合机制。

### 🔸 扩展点 2：Snapshot 压缩与质量权衡
Android 15+ 是否引入 snapshot 压缩（如 JPEG/WebP）来减少内存占用。压缩/解压缩延迟 vs 内存节省的权衡分析。

### 🔸 扩展点 3：OEM 自定义 Recents 实现与 TaskSnapshot 的关系
OEM 自研 recents/launcher（如 MIUI、One UI）如何使用或替代系统 TaskSnapshot 机制。兼容性边界。

<!-- outline-end -->

> 本节内容待加工。

[结构参考: AOSP 源码驱动 — TaskSnapshotController/TaskSnapshotPersister/SnapshotController]
