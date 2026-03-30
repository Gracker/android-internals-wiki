---
title: "Android 功耗模型"
chapter: "11.1"
status: draft
applicable_versions: "TBD"
last_verified: ""
last_verified_against: ""
confidence: low
sources: []
tags: ['power']
related_chapters: []
---

# Android 功耗模型

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 Android 功耗模型：power_profile.xml 定义各硬件模块的功耗参数
- 🔹 功耗组成拆解：CPU、Display、GPU、Cellular、WiFi、GPS、Audio、Camera
- 🔹 BatteryStats 的工作原理与数据采集
- 🔹 Coulomb Counter / Fuel Gauge 与功耗估算的区别
- 🔹 App 耗电量的归属算法

### 扩展（可选深入）

- 🔸 ODPM（On-Device Power Monitor）与 Pixel 设备的硬件功耗监测
- 🔸 功耗模型的准确性问题与校准方法

### OpenClaw 加工指引

> **锚点**是最低覆盖要求，加工时必须逐条落实并标注验证结果。
> **扩展**视素材丰富程度选择性深入。
> 如果从 Obsidian 素材或 AOSP 源码中发现大纲未列出但与本节强相关的知识点，
> 可**就地插入**最相关的锚点之后，并用 `[自动发现]` 标注，方便后续 review。
> 锚点内容需 L1/L2 验证，扩展内容至少 L2 验证，自动发现内容至少标注来源。
<!-- outline-end -->

> 本节内容待加工。
