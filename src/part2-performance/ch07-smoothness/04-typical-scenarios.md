---
title: "典型场景分析"
chapter: "7.4"
status: draft
applicable_versions: "TBD"
last_verified: ""
last_verified_against: ""
confidence: low
sources: []
tags: ['scrolling', 'animation']
related_chapters: []
---

# 典型场景分析

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 列表滑动场景的 Jank 分析：RecyclerView 的 onBind、ViewHolder 创建、图片加载
- 🔹 页面切换动画的 Jank 分析：Activity Transition、Fragment 切换、SharedElement
- 🔹 窗口动画的 Jank：App 启动窗口、Dialog/PopupWindow 弹出
- 🔹 Notification 展开/折叠的 Jank
- 🔹 桌面滑动 / 多任务切换的 Jank

### 扩展（可选深入）

- 🔸 视频播放场景的帧率稳定性
- 🔸 地图/WebView 等重渲染场景的特殊处理

### OpenClaw 加工指引

> **锚点**是最低覆盖要求，加工时必须逐条落实并标注验证结果。
> **扩展**视素材丰富程度选择性深入。
> 如果从 Obsidian 素材或 AOSP 源码中发现大纲未列出但与本节强相关的知识点，
> 可**就地插入**最相关的锚点之后，并用 `[自动发现]` 标注，方便后续 review。
> 锚点内容需 L1/L2 验证，扩展内容至少 L2 验证，自动发现内容至少标注来源。
<!-- outline-end -->

> 本节内容待加工。
