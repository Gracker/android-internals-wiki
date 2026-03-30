---
title: "Perfetto View 解读"
chapter: "13.3"
status: draft
applicable_versions: "TBD"
last_verified: ""
last_verified_against: ""
confidence: low
sources: []
tags: ['perfetto']
related_chapters: []
---

# Perfetto View 解读

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 Perfetto UI 的基本操作：缩放、搜索、Pin Track、时间选区
- 🔹 关键 Track 的含义：CPU 频率/调度、进程/线程 Slice、FrameTimeline、SurfaceFlinger
- 🔹 Slice 详情面板的解读：Wall Duration、CPU Duration、Self Time
- 🔹 Flow Events 的跟踪：Binder 调用的配对
- 🔹 颜色编码：线程状态色（Running/Runnable/Sleep/Uninterruptible）

### 扩展（可选深入）

- 🔸 Perfetto UI 的快捷键与效率技巧
- 🔸 与 Android Studio Profiler 中的 Trace 视图的对比

### OpenClaw 加工指引

> **锚点**是最低覆盖要求，加工时必须逐条落实并标注验证结果。
> **扩展**视素材丰富程度选择性深入。
> 如果从 Obsidian 素材或 AOSP 源码中发现大纲未列出但与本节强相关的知识点，
> 可**就地插入**最相关的锚点之后，并用 `[自动发现]` 标注，方便后续 review。
> 锚点内容需 L1/L2 验证，扩展内容至少 L2 验证，自动发现内容至少标注来源。
<!-- outline-end -->

> 本节内容待加工。
