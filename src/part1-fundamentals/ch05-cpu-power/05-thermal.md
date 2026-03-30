---
title: "Thermal 管控"
chapter: "5.5"
status: draft
applicable_versions: "TBD"
last_verified: ""
last_verified_against: ""
confidence: low
sources: []
tags: ['thermal']
related_chapters: []
---

# Thermal 管控

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 Thermal 管控链路：温度传感器 → Thermal HAL → thermal engine → 限频/限核
- 🔹 Android Thermal API（PowerManager.THERMAL_STATUS_*）
- 🔹 温度墙（Thermal Throttling）对性能的影响：持续高负载场景的帧率下降
- 🔹 Thermal Mitigation 策略：限频、限核、降亮度、关闭功能
- 🔹 如何在性能测试中排除温控干扰

### 扩展（可选深入）

- 🔸 各厂商 Thermal 策略差异（激进 vs 保守）
- 🔸 Sustained Performance Mode API
- 🔸 散热方案（石墨烯、VC 均热板）对性能稳定性的影响

### OpenClaw 加工指引

> **锚点**是最低覆盖要求，加工时必须逐条落实并标注验证结果。
> **扩展**视素材丰富程度选择性深入。
> 如果从 Obsidian 素材或 AOSP 源码中发现大纲未列出但与本节强相关的知识点，
> 可**就地插入**最相关的锚点之后，并用 `[自动发现]` 标注，方便后续 review。
> 锚点内容需 L1/L2 验证，扩展内容至少 L2 验证，自动发现内容至少标注来源。
<!-- outline-end -->

> 本节内容待加工。
