---
title: "Android 内存模型全景"
chapter: "4.1"
status: draft
applicable_versions: "TBD"
last_verified: ""
last_verified_against: ""
confidence: low
sources: []
tags: ['memory']
related_chapters: []
---

# Android 内存模型全景

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 Android 内存模型全景：物理内存 → 内核管理 → 用户空间（Native + Java Heap + Graphics）
- 🔹 关键内存指标：VSS、RSS、PSS、USS 的定义与适用场景
- 🔹 进程内存组成：Java Heap、Native Heap、Code（.dex/.so）、Stack、Graphics（GPU/EGL）
- 🔹 procfs 接口：/proc/meminfo、/proc/<pid>/status、/proc/<pid>/smaps
- 🔹 dumpsys meminfo 的解读方法

### 扩展（可选深入）

- 🔸 cgroup v1/v2 对 Android 内存控制的作用
- 🔸 ZRAM / Swap 在 Android 上的使用与配置

### OpenClaw 加工指引

> **锚点**是最低覆盖要求，加工时必须逐条落实并标注验证结果。
> **扩展**视素材丰富程度选择性深入。
> 如果从 Obsidian 素材或 AOSP 源码中发现大纲未列出但与本节强相关的知识点，
> 可**就地插入**最相关的锚点之后，并用 `[自动发现]` 标注，方便后续 review。
> 锚点内容需 L1/L2 验证，扩展内容至少 L2 验证，自动发现内容至少标注来源。
<!-- outline-end -->

> 本节内容待加工。
