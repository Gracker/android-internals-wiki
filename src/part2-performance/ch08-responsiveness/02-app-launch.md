---
title: "App 启动全流程"
chapter: "8.2"
status: draft
applicable_versions: "TBD"
last_verified: ""
last_verified_against: ""
confidence: low
sources: []
tags: ['cold-start', 'launch']
related_chapters: []
---

# App 启动全流程

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 冷启动 / 温启动 / 热启动的定义与区别
- 🔹 冷启动完整流程：Process.start → ActivityThread → Application.onCreate → Activity.onCreate → 首帧绘制
- 🔹 TTID（Time To Initial Display）与 TTFD（Time To Full Display / reportFullyDrawn）的定义
- 🔹 启动耗时的度量方法：adb am start -W、Logcat ActivityTaskManager、Perfetto
- 🔹 Application.onCreate 中常见的耗时操作：SDK 初始化、数据库初始化、多 Dex 加载
- 🔹 首帧绘制的关键路径：inflate → measure → layout → draw

### 扩展（可选深入）

- 🔸 Baseline Profile 与 Cloud Profile 对启动速度的提升
- 🔸 App Startup Library（AndroidX）的使用与原理
- 🔸 Zygote preload 对启动速度的贡献量化

### OpenClaw 加工指引

> **锚点**是最低覆盖要求，加工时必须逐条落实并标注验证结果。
> **扩展**视素材丰富程度选择性深入。
> 如果从 Obsidian 素材或 AOSP 源码中发现大纲未列出但与本节强相关的知识点，
> 可**就地插入**最相关的锚点之后，并用 `[自动发现]` 标注，方便后续 review。
> 锚点内容需 L1/L2 验证，扩展内容至少 L2 验证，自动发现内容至少标注来源。
<!-- outline-end -->

> 本节内容待加工。
