---
title: "Android 17 CPU 缓存局部性与 PSS 内存核算源码机制"
chapter: "ch04/ch05.05.06"
status: quarantined
applicable_versions: "Android 16 (API 35) - Android 17 (API 37)"
tags: ["Android-17", "ch04/ch05", "源码分析", "性能优化"]
related_chapters: ["ch04/ch05"]
created_by: "task2a-knowledge-gap"
created_date: "2026-07-08"
gap_source: "AOSP结构"
gap_score: "19/20"
---
<!-- 
[QUARANTINE NOTICE — 2026-07-08]
原因：outline 模板错误：标题为 CPU 缓存局部性/PSS 核算，但大纲内容全部是 LMKD/PSI（copy-paste 错误）。
处理：本章由 task2a-knowledge-gap 自动创建，但 outline 模板存在 copy-paste 错误。
如需恢复，请手动修正 outline 后将 status 改回 draft。
-->


# 05.06 Android 17 CPU 缓存局部性与 PSS 内存核算源码机制

> [!CAUTION] 隔离内容说明
> 下方受保护大纲来自错误的 LMKD/PSI 模板，与本页标题无关。为了保留 Hermes 的隔离记录，本轮不改动大纲；它不属于可引用的技术正文。

<!-- outline-start -->
## 本节要点大纲

### 🔹 锚点（必须覆盖）

- 🔸 LMKD 从 kernel module 到 userspace 守护进程的演进路径
- 🔸 PSI（Pressure Stall Information）监听机制与 BPF ring buffer 实现
- 🔸 三维决策模型：zone watermarks、thrashing、swap utilization
- 🔸 pidfd 等待机制替代传统信号量的实现方案
- 🔸 epoll 事件驱动的高效响应架构（10ms/100ms 双间隔）
- 🔸 Android 17 LMKD 与传统 LowMemoryKiller 的关键差异
- 🔸 PSI 监听对内存压力识别精度的提升效果

### 🔹 扩展（可选深入）

- 🔸 各厂商对 PSI 监听参数的定制化配置
- 🔸 通过 Perfetto 观察 PSI 监听行为的方法
- 🔸 LMKD 在极端内存压力下的行为边界
- 🔸 PSI 与 vmpressure 的兼容性和迁移策略

## 本节内容待加工

> 本节基于 DeepResearch 素材驱动，通过源码级分析Android 17 LMKD的PSI协同机制，从内核态到用户态的完整迁移路径。
>
> **注**：所有锚点内容待加工，需要基于 AOSP android-17.0.0_r1 源码进行验证和深化。

<!-- outline-end -->

## 本页去向

这个文件同时混入“CPU cache/PSS”和“LMKD/PSI”两个主题，无法在不改写受保护大纲与 quarantine 元数据的前提下形成自洽章节。当前可引用内容已经分别进入：

- [4.35 Android 17 CPU 缓存局部性与 PSS 内存核算](../ch04-memory/4.35-android17-cpu-cache-locality-pss-accounting.md)
- [5.18 CPU 缓存局部性与 PSS 核算](5.18-android17-cpu-cache-locality-pss-accounting.md)
- [5.25 Android 17 CPU 缓存局部性](5.25-android17-cpu-cache-locality.md)
- [4.37 Android 17 LMKD userspace 迁移](../ch04-memory/4.37-android17-lmkd-userspace-migration.md)
- [4.50 LMKD v2 与 PSI 分级压力治理](../ch04-memory/4.50-lmkd-v2-psi-tiered-pressure-governance.md)

CPU cache/PSS 相关修订应采用 AOSP `android-17.0.0_r1`；LMKD/PSI 同时采用 AOSP `android-17.0.0_r1` 与 kernel `android17-6.18-2026-06_r6`。本页只负责隔离与迁移提示，不复制上述章节的技术论述。
