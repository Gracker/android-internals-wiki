---
title: "Frame Timeline API 33 Perfetto 深度分析：Expected vs Actual Timeline"
chapter: "13.20"
status: draft
applicable_versions: "Android 13 (API 33) - Android 17 (API 37)"
tags: [Perfetto, FrameTimeline, Jank, Choreographer, 渲染性能分析]
related_chapters: ["2.4", "13.5", "13.8", "22.8"]
created_by: "task2a-knowledge-gap"
created_date: "2026-07-16"
gap_source: "研究素材+章节深挖"
confidence: medium
---

# 13.20 Frame Timeline API 33 Perfetto 深度分析：Expected vs Actual Timeline

<!-- outline-start -->
## 要点

### 🔹 Expected Timeline 与 Actual Timeline 的物理含义
- Expected Timeline：系统为应用分配的帧时间窗口（非简单 VSync-app 时刻）
- Actual Timeline：应用实际完成帧渲染（含 GPU 工作）并发送给 SurfaceFlinger 的真实耗时
- 两者偏差即为 jank

### 🔹 Perfetto 中的三条关键 Track
- Expected Timeline Track：基于 Choreographer.getPreferredFrameTimeline() 的帧调度计划
- Actual Timeline Track：实际帧呈现耗时记录
- Choreographer#doFrame：应用主线程 Track 中的 slice，与 Actual Timeline 对齐

### 🔹 颜色编码规则与 Jank 归因
- 绿色：帧在预期时间内完成，无 jank
- 红色：应用导致 jank（Actual 超出 Expected 边界）
- 黄色：SurfaceFlinger 合成延迟导致的 jank（非应用责任）

### 🔹 FrameData API 核心方法
- getFrameTimeNanos()：当前帧的 VSync 时间戳
- getLastFrameTimeNanos()：上一帧的 VSync 时间戳
- getIntervalNanos()：帧间隔（由刷新率决定）
- getDeadlineNanos()：帧截止时间（用于 shouldPause 判定等）

### 🔹 FrameTimeline 获取方式
- Choreographer 实例的 getPreferredFrameTimeline()：获取系统推荐的帧调度计划
- getFrameTimelines()：获取所有可用帧时间线列表

### 🔹 Expected Timeline 与 VSYNC-app 的时间差分析
- Expected Timeline 综合考虑了 VSync offset、SurfaceFlinger 合成时间、Display 显示延迟
- 这解释了为什么 Expected Timeline 和 VSYNC-app 之间存在可观测的时间差
- [结构参考: Clippings/线上疑难问题 该如何排查和跟踪]

### 🔹 Perfetto 抓取命令与配置
- atrace 配置：sched freq idle am wm gfx view binder_driver hal
- perfetto 命令行录制与 UI 导入流程

## 扩展

### 🔸 自定义 Frame Timeline 可视化分析
- 结合 Perfetto SQL 查询提取帧延迟分布
- 构建 P50/P90/P99 帧延迟看板

### 🔸 与 Compose PausableComposition 的联动分析
- 通过 Frame Timeline 观察 PausableComposition 效果
- shouldPause 回调对帧节奏的影响

<!-- outline-end -->

> 本节内容待加工。
