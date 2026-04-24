---
title: "崩溃与 ANR 捕获机制"
chapter: "19"
section: "19.24"
status: ready-for-review
drafted_date: "2026-04-24"
drafted_by: "gemini"
applicable_versions: "Android 8 (API 26) - Android 17 (API 37)"
last_verified: "2026-04-24"
confidence: high
tags: [apm, crash, anr, stability, breakpad]
related_chapters: ["19.0", "19.16"]
pipeline_stage: task6_pending
---

# 崩溃与 ANR 捕获机制

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 [定位] 揭秘 APM 稳定性基建的最底层逻辑，解析 Java Crash、Native Crash 与 ANR 的捕获黑魔法。
- 🔹 [Java Crash 捕获] 展开 `Thread.setDefaultUncaughtExceptionHandler` 的原理，以及如何保证自身上报逻辑不被 Crash 截断。
- 🔹 [Native Crash 捕获] 解析 Google Breakpad / Crashpad 在 Android 端的应用，说明 Linux 信号（Signal）拦截机制与 Tombstone 文件的生成与解析。
- 🔹 [ANR 捕获演进史] 从早期读取 `/data/anr/traces.txt`，到监听 SIGQUIT 信号 (Signal Catcher Hook)，再到 Android 11+ 官方 `ApplicationExitInfo` 的终极方案。
- 🔹 [OOM 细分与防范] 拆解非 Java Heap OOM 的监控：文件描述符 (FD) 溢出、线程池暴增 (Thread Exhaustion)、虚拟内存地址空间 (VMA) 耗尽的监控与预警。
- 🔹 [现场快照留存] 说明崩溃瞬间如何收集寄存器状态、内存使用率、Logcat 尾部日志、以及用户 Session 操作轨迹。
- 🔹 [多 SDK 冲突] 解释当项目中同时存在多个 APM (如 Bugly + Firebase + 自研) 时，Crash Handler 被覆盖或死锁的风险及链接链处理方案。

### 扩展（可选深入）

- 🔸 绘制一张 Native Signal 从发生到 Crashpad 捕获上报的完整时序图。
- 🔸 提供针对 Android 11+ `ApplicationExitInfo` 捞取 ANR 与 LMK (Low Memory Killer) 历史记录的代码片段。
- 🔸 介绍对于 C/C++ 内存破坏 (如 Use-After-Free) 的 GWP-ASan 线上灰度检测方案。

### 流水线加工要求

- 要把不同 Android 版本对底层 `/data/anr` 或进程内存文件的权限封堵作为重要背景交代。
- OOM 监控部分不能只写 Java 堆内存，必须写清 FD 和线程数溢出的底层原因。
- 强调异常处理函数中绝对不能做复杂的内存分配与锁操作，以防二次 Crash。

### OpenClaw 加工指引

> **锚点**是最低覆盖要求，加工时必须逐条落实并标注验证结果。
> **扩展**视素材丰富程度选择性深入。
<!-- outline-end -->
