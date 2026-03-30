---
title: "App 耗电优化"
chapter: "11.2"
status: draft
applicable_versions: "TBD"
last_verified: ""
last_verified_against: ""
confidence: low
sources: []
tags: ['wakelock', 'jobscheduler']
related_chapters: []
---

# App 耗电优化

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 WakeLock 最佳实践：类型选择、超时设置、及时释放
- 🔹 后台任务省电策略：JobScheduler / WorkManager 的正确使用
- 🔹 位置服务功耗优化：精度选择、更新频率、Geofencing
- 🔹 网络请求功耗优化：批量请求、减少轮询、Push 替代 Pull
- 🔹 Alarm 使用规范：避免精确重复闹钟、使用 setAndAllowWhileIdle 的限制

### 扩展（可选深入）

- 🔸 前台服务的功耗考量与 Android 14+ 对 FGS 的限制
- 🔸 Camera/Audio 等硬件资源的功耗优化

### OpenClaw 加工指引

> **锚点**是最低覆盖要求，加工时必须逐条落实并标注验证结果。
> **扩展**视素材丰富程度选择性深入。
> 如果从 Obsidian 素材或 AOSP 源码中发现大纲未列出但与本节强相关的知识点，
> 可**就地插入**最相关的锚点之后，并用 `[自动发现]` 标注，方便后续 review。
> 锚点内容需 L1/L2 验证，扩展内容至少 L2 验证，自动发现内容至少标注来源。
<!-- outline-end -->

> 本节内容待加工。
