---
title: "Crash 上报体系搭建"
chapter: "26.2"
section: "26.2"
status: draft
applicable_versions: "Android 10 (API 29) - Android 16 (API 36)"
last_verified: "2026-05-10"
last_verified_against: "待验证"
confidence: low
drafted_date: "2026-05-10"
polish_count: 0
sources: []
tags: [crash-reporting, symbolication, deobfuscation, alerting]
related_chapters: ["26.1", "20.2", "20.3", "19.24"]
pipeline_stage: draft
task6_state: pending
task9_state: pending
task2b_state: pending
---

# Crash 上报体系搭建

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 Crash SDK 核心流程：捕获 / 序列化 / 持久化 / 上报
- 🔹 多进程 Crash 上报的可靠性保证
- 🔹 符号化与反混淆服务
- 🔹 Crash 实时告警与分级响应

### 扩展（可选深入）

- 🔸 （待扩展）

### OpenClaw 加工指引

> **锚点**是最低覆盖要求，加工时必须逐条落实并标注验证结果。
> **扩展**视素材丰富程度选择性深入。
> 如果从 Obsidian 素材或 AOSP 源码中发现大纲未列出但与本节强相关的知识点，
> 可**就地插入**最相关的锚点之后，并用 `[自动发现]` 标注，方便后续 review。
> 锚点内容需 L1/L2 验证，扩展内容至少 L2 验证，自动发现内容至少标注来源。


## Crash 聚合与归因分析中的 ML 应用

<!-- AIW-源码调研-2026-05-12 -->

### Analysis Engine 机制（Firebase Crashlytics）

Firebase Crashlytics 的 analysis engine 是目前最具体的商业实现案例，基于以下特征向量进行事件聚类：

**特征向量**：
1. Stack trace frames（栈帧序列）
2. Exception message（异常消息文本）
3. Error code（错误码）
4. Platform characteristics（平台特征）
5. Error type characteristics（错误类型特征）

**核心聚类语义**：
- **Issue**：共享同一个 failure point 的崩溃事件集合。同一 Issue 内所有事件有共同的崩溃点。
- **Variation**：同一 Issue 内到达 failure point 的路径可能不同，不同路径可能意味着不同根因，Variation 用于区分这些子路径。

**Crash Insights**：主动识别常见稳定性模式并提供修复建议，是 ML 在 crash 治理中的高级应用形式。

> 来源：[Firebase Crashlytics 官方文档](https://firebase.google.com/docs/crashlytics) — 官方产品描述

### Sentry ML-driven Analysis

Sentry 的 Android SDK 公开文档描述其使用了 ml-driven 算法进行 issue ranking，具体层次：

- **异常检测**：区分新 issue vs 已知 issue 的回归
- **趋势预测**：预测某 issue 是否会持续恶化
- **智能聚类**：基于语义相似性而非仅栈帧匹配进行分组
- **根因推断**：结合多维度数据（设备分布、OS 版本、用户行为序列）推断崩溃根因

> 来源：[getsentry/sentry-java (GitHub)](https://github.com/getsentry/sentry-java) — 开源 SDK 仓库

### Android NDK Native Crash 处理基础设施

**关键源码路径**（待验证）：
- `bionic/libunwind/`：Native 栈帧解析，支持 ARM64/AArch64 和 ARM32
- `system/core/debuggerd/` → `trusted京城/aee/`（Android 14+）：crash signal 处理路径变更
- `frameworks/base/core/java/android/app/ActivityThread.java`：ANR 和 crash 处理入口

**处理链路**：
1. Signal Handler 注册（`bionic/libc/bionic/.__fortified_charm` 或自定义 handler）
2. `libunwind` 解析 Native 栈帧
3. ADR (Android Debug Record) 记录寄存器上下文和栈数据
4. `tombstone` 写入 `/data/tombstones/tombstone_XX`
5. `addr2line` / `ndk-stack` / `llvm-symbolizer` 符号化

### 性能影响

1. **Analysis Engine 计算开销**：在线聚合需要实时计算，大数据量下可能成为上报链路瓶颈
2. **Symbolization 延迟**：ProGuard/R8 混淆后符号化耗时，线上实时符号化依赖预计算的 mapping 文件
3. **Variation 生成**：过多样 Variation 稀释开发者注意力，需 ML 排序抑制低价值 Variation

### 版本差异

| Android 版本 | 变化 |
|-------------|------|
| Android 5.0 (API 21) | ART 引入，Java crash 处理从 Dalvik 迁移 |
| Android 7.0 (API 24) | `debuggerd` 改写，引入 `DEBUGGERD_SIGNAL` |
| Android 10 (API 29) | Scoped storage 影响 crash 报告文件写入路径 |
| Android 14 (API 34) | `debuggerd` 重构为 aee 子系统，NDK crash 处理路径变更 |
| Android 15+ (API 35+) | 64-bit only 进程模型影响 crash 信号处理链 |

### 待深入方向

- Firebase Crashlytics analysis engine 源码实现（Google 内部系统，无 AOSP 对应）
- Sentry ML 算法具体实现（未完全开源）
- AOSP libunwind 实现版本差异验证
- LLM 在 crash 分析中的具体生产应用案例

<!-- outline-end -->

## 为什么要了解Crash 上报体系搭建

（待加工）

