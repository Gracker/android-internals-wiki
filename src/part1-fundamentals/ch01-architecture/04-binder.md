---
title: "Binder IPC 机制与性能影响"
chapter: "1.4"
status: draft
applicable_versions: "TBD"
last_verified: ""
last_verified_against: ""
confidence: low
sources: []
tags: ['binder', 'ipc']
related_chapters: []
---

# Binder IPC 机制与性能影响

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 Binder 架构：Client → Proxy → Binder Driver → Stub → Server，一次拷贝的实现原理（mmap）
- 🔹 AIDL 接口定义与代码生成：Proxy/Stub 模式
- 🔹 Binder 线程池模型：默认最大 15 个 binder 线程（可配置）、线程池动态管理、线程耗尽对 ANR 的影响
- 🔹 同步 Binder 调用的性能开销：上下文切换、调度延迟、数据序列化
- 🔹 oneway 异步调用 vs 同步调用的性能差异与适用场景
- 🔹 Binder 调用在 Perfetto/Systrace 中的表现：binder transaction、binder reply

### 扩展（可选深入）

- 🔸 Binder 与传统 IPC（Socket、管道、共享内存）的性能对比
- 🔸 Binder 调用频率与系统负载：如何在 Trace 中识别 binder 风暴
- 🔸 AIDL 与 HIDL 的区别及演进（HAL 层 Binder 化）

### OpenClaw 加工指引

> **锚点**是最低覆盖要求，加工时必须逐条落实并标注验证结果。
> **扩展**视素材丰富程度选择性深入。
> 如果从 Obsidian 素材或 AOSP 源码中发现大纲未列出但与本节强相关的知识点，
> 可**就地插入**最相关的锚点之后，并用 `[自动发现]` 标注，方便后续 review。
> 锚点内容需 L1/L2 验证，扩展内容至少 L2 验证，自动发现内容至少标注来源。
<!-- outline-end -->

> 本节内容待加工。
