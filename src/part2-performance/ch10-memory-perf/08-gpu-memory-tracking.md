---
title: "GPU / 图形内存统计与实战监控"
chapter: "10.8"
status: draft
applicable_versions: "Android 12 (API 31) - Android 17 (API 37)"
tags: [gpu-memory, dmabuf, gralloc, perfetto, memory-tracking, graphics]
related_chapters: ["2.15", "4.2", "10.1", "14.8"]
created_by: "task2a-knowledge-gap"
created_date: "2026-06-07"
gap_source: "AOSP结构/章节深挖/官方文档"
---

# 10.8 GPU / 图形内存统计与实战监控

<!-- outline-start -->
## 要点

### 🔹 锚点 1：GPU 内存分配路径与 Android 图形内存架构
- GPU 驱动、DMA-BUF Heaps、Gralloc 分配器之间的关系
- Android 12+ DMA-BUF Heaps 统一分配路径
- GPU private memory vs. shared (DMA-BUF) memory 的区别
- 与 ch2.15（DMA-BUF/Gralloc）的交叉引用：本节聚焦监控与归因，机制详见 2.15

### 🔹 锚点 2：dumpsys meminfo 中的 GPU / Graphics 内存解读
- `dumpsys meminfo <pkg>` 输出中 Graphics / GL / Other Dev 的含义
- 如何从 meminfo 读取 GPU 内存占用趋势
- Private vs. Shared GPU 内存的区别
- `dumpsys gfxinfo <pkg>` 中帧相关的 GPU 内存信息

### 🔹 锚点 3：Perfetto GPU Memory 计数器与 SQL 查询
- `gpu.counters.*` 数据源的采集配置
- `gpu.track` / `gpu.memory` 轨道的 Perfetto View 解读
- SQL 查询：按进程聚合 GPU 内存占用
- Android 14+ `gpu.memory` perfetto 数据源的使用

### 🔹 锚点 4：procfs / sysfs 中的 GPU 内存指标
- `/sys/kernel/debug/dma_buf/` 与 `/sys/kernel/debug/dma_heap/`
- `/d/mali/gpu_memory`（Mali GPU）或等效路径
- 如何通过 `adb shell cat /proc/<pid>/smaps | grep -i gpu` 定位 GPU 内存
- 不同 GPU 厂商（Qualcomm Adreno / ARM Mali / Imagination）的 GPU 内存暴露差异

### 🔹 锚点 5：GPU 内存泄漏的诊断方法
- 常见 GPU 内存泄漏模式：未回收的 Hardware Bitmap、Surface 泄漏、EGL Context 未释放
- 从 `dumpsys meminfo` 趋势判断 GPU 内存增长
- Perfetto 中 `gpu.memory` 的持续增长与对应的 Java/native 层分配关联
- 用 Android Studio Memory Profiler 的 Native Heap Dump 追踪 GPU 分配（heapprofd 兼容性）

### 🔹 锚点 6：Android 17 图形内存管理变更
- Android 17 中 16KB Page Size 对 GPU 内存分配的影响
- DMA-BUF Heaps 在 Android 17 的成熟度
- Gralloc 4.0+ 对 GPU 内存追踪的改善
- GPU 内存预算与系统 LMK 的交互

### 🔹 锚点 7：GPU 内存优化实战建议
- Hardware Bitmap 的正确使用与回收时机
- SurfaceView vs. TextureView 的 GPU 内存开销对比
- 帧缓冲区双缓冲/三缓冲的 GPU 内存代价
- 大分辨率图片加载的 GPU 内存控制策略

## 扩展

### 🔸 扩展点 1：不同 SoC 平台的 GPU 内存统计差异
- Snapdragon (Adreno) / Dimensity (Mali) / Exynos (Xclipse/Mali) 的 GPU 内存暴露接口差异
- OEM 自定义的 GPU 内存 debug 接口

### 🔸 扩展点 2：GPU 内存与整体系统内存预算
- GPU 内存占用对应用可用内存的影响
- 在低内存设备上 GPU 内存的竞争与 LMK 触发

### 🔸 扩展点 3：Game / AR / Camera 场景的 GPU 内存管理
- 游戏场景中纹理内存、渲染目标的 GPU 内存管理
- ARCore / Camera X 的 GPU 内存使用模式

<!-- outline-end -->

> 本节内容待加工。
