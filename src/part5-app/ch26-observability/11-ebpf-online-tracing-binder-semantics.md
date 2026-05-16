---
title: "eBPF 在线追踪与 Binder 语义重建"
chapter: "26.11"
status: draft
applicable_versions: "Android 12 (API 31) - Android 17 (API 36)"
tags: [ebpf, binder, observability, tracing, online-diagnosis, security-audit]
related_chapters: ["1.4", "13.9", "14.10", "26.5"]
created_by: "task2a-knowledge-gap"
created_date: "2026-05-16"
gap_source: "研究素材/素材驱动"
gap_score: 17
material_count: 3
source_refs:
  - 论文/Android-2026-05-03-WOOTdroid/03-精读.md
  - https://arxiv.org/
  - src/part3-tools/ch14-other-tools/10-ebpf-performance-analysis.md
  - src/part1-fundamentals/ch01-architecture/04-binder.md
---

# 26.11 eBPF 在线追踪与 Binder 语义重建

<!-- outline-start -->
## 要点

### 🔹 线上追踪为什么不能只依赖 ftrace
从 ring buffer 覆盖、长期开启成本、事件丢失、生产环境权限边界解释在线追踪的约束。

### 🔹 Android eBPF syscall 追踪路径
梳理 raw_syscalls tracepoint、perf ring buffer、tail calls、MTE address masking 等 Android 特有适配点。

### 🔹 Binder 语义重建的关键问题
说明 ioctl(BINDER_WRITE_READ)、BC_TRANSACTION、Parcel buffer、接口签名表和参数反序列化的边界。

### 🔹 性能开销与完整性指标
整理 Geekbench、Top 100 应用 Monkey、独有事件率等实验指标如何转化为工程评估口径。

### 🔹 用于 ANR、隐私审计和冷启动回溯
连接线上问题排查场景，说明 syscall 序列和 Binder transaction 日志能回答哪些问题。

### 🔹 部署边界与合规风险
标清 root/OEM 预装、隐私数据采集、用户授权、敏感参数脱敏和厂商系统差异。

## 扩展

### 🔸 WOOTdroid 与 Android eBPF 工具链对比
对照 bpftrace、Perfetto eBPF 数据源、内核 tracepoint。

### 🔸 Binder 参数脱敏策略
整理短信、账户、位置等敏感接口的字段级脱敏规则。

<!-- outline-end -->

> 本节内容待加工。
