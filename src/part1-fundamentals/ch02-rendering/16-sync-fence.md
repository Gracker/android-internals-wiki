---
title: "Sync Fence 框架与帧同步机制"
chapter: "2.16"
status: draft
applicable_versions: "Android 8 (API 26) - Android 17 (API 37)"
tags: [sync-fence, fence, hwui, rendering, synchronization, timeline]
related_chapters: ["2.4", "2.5", "2.6", "2.13", "2.15"]
created_by: "task2a-knowledge-gap"
created_date: "2026-04-05"
gap_source: "章节深挖+读者需求+AOSP结构"
gap_score: "15/20"
---

# 2.16 Sync Fence 框架与帧同步机制

<!-- outline-start -->
## 要点

### 🔹 锚点 1：为什么需要 Fence
- GPU 渲染是异步的：App 提交 draw call 后，GPU 还在画，但主线程已经继续了
- 如果 SurfaceFlinger 在 GPU 还没画完时就开始合成，会读到不完整的帧（撕裂）
- Fence 就是「这件事做完了」的信号：GPU 画完 → fence signal → SurfaceFlinger 可以合成
- 类比：餐厅出餐铃——你点了菜，不用一直盯着厨房，铃响了去取就行

### 🔹 锚点 2：Fence 的内核机制
- Android sync framework（sw_sync / sync_timeline / sync_pt）
- 基于 Linux fence（dma-buf fence），Android 在此之上做了封装
- Fence timeline：时间轴模型，每个时间点对应一个 fence
- HWC（Hardware Composer）生成的硬件 fence vs 软件模拟 fence
- fence fd 的生命周期：create → signal → close

### 🔹 锚点 3：渲染管线中的 Fence 使用
- App 渲染完成 → acquire fence（GPU 完成写入的信号）
- SurfaceFlinger 合成 → release fence（HWC/GPU 完成合成并释放 buffer 的信号）
- Display 显示完成 → retire fence（屏幕完成显示上一帧的信号）
- [图：一帧经过的 3 个 fence——acquire/release/retire，标注在渲染管线时序图上]

### 🔹 锚点 4：在 Perfetto 中的 Fence 表现
- BufferQueue track 中的 fence 等待时间
- SurfaceFlinger 的 Composition timeline 中 fence 的作用
- GPU completion fence vs HWC release fence 的区分
- fence 超时或未 signal 时的异常表现

### 🔹 锚点 5：Fence 与掉帧的关系
- acquire fence 延迟 → App 渲染慢 → 下一帧的 buffer 还没释放 → dequeueBuffer 阻塞
- release fence 延迟 → SurfaceFlinger 合成慢 → 前一帧 buffer 被 hold → 三缓冲耗尽
- fence merge：多个 Layer 的 acquire fence 合并为一个，如何影响合成时机
- 实战：在 Perfetto 中追踪 fence 延迟导致的掉帧

### 🔹 锚点 6：常见问题与排查
- Fence 泄漏：fd 未 close 导致 buffer 泄漏
- HWC fence 回退：硬件 fence 不可用时的 fallback 路径和性能影响
- Fence 超时：GPU hang 导致 fence 永远不 signal，系统如何处理
- [待验证：Android 17 对 fence 机制是否有优化]

## 扩展

### 🔸 扩展点 1：Fence 在 Camera/Video 管线中的应用
- Camera 的 completion fence
- Video decoder 的 output fence

### 🔸 扩展点 2：Timeline 和 Fence 的调试工具
- sync_dump / dumpsys SurfaceFlinger 中的 fence 信息
- /sys/kernel/debug/sync/ 调试接口

<!-- outline-end -->

> 本节内容待加工。
