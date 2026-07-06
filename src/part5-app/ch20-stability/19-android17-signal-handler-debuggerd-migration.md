---
title: "Android 17 信号处理架构迁移与 debuggerd bionic/linker 重构"
chapter: "20.19"
status: draft
applicable_versions: "Android 14 (API 34) - Android 17 (API 37)"
tags: ["signal-handler", "debuggerd", "bionic", "crash-monitoring", "native"]
related_chapters: ["20.3", "20.9", "20.18"]
created_by: "task2a-knowledge-gap"
created_date: "2026-07-07"
gap_source: "素材驱动+研究盲区"
---

# 20.19 Android 17 信号处理架构迁移与 debuggerd bionic/linker 重构

<!-- outline-start -->
## 要点

### 🔹 debuggerd 架构迁移路径
- Android 14 及之前：debuggerd 位于 `system/core/debuggerd/`，独立守护进程模型
- Android 15-16：过渡期，部分功能向 bionic/linker 迁移
- Android 17：debuggerd 核心功能正式迁入 `bionic/linker/`，与动态链接器深度集成
- 迁移动机：减少 crash dump 过程中的二次崩溃风险、缩短信号处理路径

### 🔹 信号线程亲和性分发机制
- Android 17 信号处理器绑定到特定线程的设计
- SIGSEGV/SIGABRT/SIGBUS 的线程定向投递
- 与传统 `signal()` / `sigaction()` 全局处理的差异
- 对 crash dump 准确性的影响：线程上下文保真度提升

### 🔹 动态 altstack 尺寸策略
- `SIGSTKSZ` 在 Android 17 中的变化：从固定值到动态计算
- 信号处理器嵌套场景下的 altstack 容量保障
- 不同设备配置（RAM 大小、页尺寸）下的 altstack 自适应
- 16KB Page Size 对 altstack 的影响（与 20.13 交叉引用）

### 🔹 信号处理器链兼容性
- Android 17 下第三方 crash 监控 SDK 信号处理器链的行为
- `SA_RESTART` / `SA_ONSTACK` / `SA_SIGINFO` 标志的兼容性
- 多级信号处理器注册顺序：系统 → SDK → 应用
- 信号处理器链断裂的检测与恢复

### 🔹 对 Native Crash 监控 SDK 的影响
- Bugly / Firebase Crashlytics / xCrash 等主流 SDK 的适配策略
- `prctl(PR_SET_DUMPABLE)` 与信号投递权限的变化
- tombstone 文件格式在 Android 17 中的变化
- Crash dump 采集的可靠性保障：fork-based vs in-process

### 🔹 与 ART 异常处理的协作
- ART 内部信号处理器（`art::SignalChain`）与系统信号处理的边界
- Java NPE / OOM 等运行时异常的信号转换路径
- `art::FaultManager` 在 Android 17 中的调整
- Native crash 与 Java crash 的信号分流

### 🔹 crash dump 输出与符号化衔接
- Android 17 tombstone 格式变化：新增字段与格式调整
- 与 20.18（Native 堆栈回溯与符号化机制）的衔接
- unwind 表（`.eh_frame` / `.ARM.exidx`）在 Android 17 中的一致性
- `symbols.zip` 与 `llvm-symbolizer` 的版本对齐

## 扩展

### 🔸 实战：SDK 适配检查清单
- 信号处理器注册前的 `sigaltstack` 验证
- `SA_NODEFER` 在嵌套信号场景下的正确使用
- SDK 初始化时序：Application.onCreate vs ContentProvider vs App Startup

### 🔸 Android 17 信号处理性能基准
- 信号处理到 crash dump 开始的延迟基准（P50/P99）
- 不同 SDK 方案的 crash dump 完成时间对比
- crash dump 过程中的内存占用峰值

<!-- outline-end -->

> 本节内容待加工。

[结构参考: 研究盲区 intake/research-gaps.md — Android 17信号处理机制与debuggerd架构迁移]
[素材来源: source-index score=16 — Android 17信号处理机制与debuggerd架构迁移]
