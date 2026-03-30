---
title: "Input 事件分发全流程"
chapter: "3.1"
status: draft
applicable_versions: "TBD"
last_verified: ""
last_verified_against: ""
confidence: low
sources: []
tags: ['input', 'inputdispatcher']
related_chapters: []
---

# Input 事件分发全流程

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 输入事件完整链路：硬件 → Kernel InputDriver → EventHub → InputReader → InputDispatcher → App ViewRootImpl → View 树
- 🔹 InputDispatcher 的分发策略：焦点窗口、触摸窗口、ANR 超时
- 🔹 App 侧的事件分发：ViewRootImpl → DecorView → Activity.dispatchTouchEvent → ViewGroup → View
- 🔹 InputChannel 与 Socket pair 机制
- 🔹 关键超时参数：5s ANR for Key, 5s for Touch (Android 不同版本变化)

### 扩展（可选深入）

- 🔸 InputFlinger 的角色与演进
- 🔸 输入事件在 Systrace 中的完整追踪：deliverInputEvent → input event latency
- 🔸 Pointer Event 与 Motion Event 的区别

### OpenClaw 加工指引

> **锚点**是最低覆盖要求，加工时必须逐条落实并标注验证结果。
> **扩展**视素材丰富程度选择性深入。
> 如果从 Obsidian 素材或 AOSP 源码中发现大纲未列出但与本节强相关的知识点，
> 可**就地插入**最相关的锚点之后，并用 `[自动发现]` 标注，方便后续 review。
> 锚点内容需 L1/L2 验证，扩展内容至少 L2 验证，自动发现内容至少标注来源。
<!-- outline-end -->

> 本节内容待加工。
