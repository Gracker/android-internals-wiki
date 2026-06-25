---
title: "Native 堆栈回溯与符号化机制"
chapter: "20.18"
status: draft
applicable_versions: "Android 10 (API 29) - Android 17 (API 37)"
tags: [native, crash, stack-unwinding, symbolication, ndk]
related_chapters: ["20.3", "9.3", "14.2", "14.13"]
created_by: "task2a-knowledge-gap"
created_date: "2026-06-26"
gap_source: "素材驱动/参考书"
---

# 20.18 Native 堆栈回溯与符号化机制

<!-- outline-start -->
## 要点

### 🔹 为什么 Native 堆栈回溯是稳定性基建

Native Crash 分析的核心瓶颈不在「崩溃是否上报」，而在「崩溃堆栈能不能还原到源码行」。一段 `#00 pc 0x8a3c` 的原始地址，如果没有可靠的回溯和符号化管线，等于丢失了全部调试信息。这一节拆解从 CPU 寄存器到可读源码行号的完整链路。

### 🔹 FP 回溯（Frame Pointer Unwinding）

ARM64 下 FP（X29 寄存器）串联函数调用链的原理；`-fomit-frame-pointer` 在不同编译配置下的行为；Android NDK 从 r23 起默认启用 FP 的背景；FP 回溯的性能开销（每帧约 2 条指令）与可靠性边界（栈被破坏后 FP 链断裂）。

### 🔹 CFI 回溯（Compact Frame Information）

`.eh_frame` / `.eh_frame_hdr` 段的作用；CFI 记录如何描述寄存器保存与恢复规则；`libunwind` 与 `_Unwind_Backtrace` 的调用路径；Android 10+ 系统 crash dump 中 CFI 回溯的默认地位；CFI 回溯对包体积的影响（.eh_frame 约增加 5-10% so 体积）。

### 🔹 堆栈回溯的性能开销对比

FP 回溯 vs CFI 回溯 vs libunwind-astack 的延迟差异（单次回溯纳秒级 vs 微秒级）；高频采样场景（Simpleperf、Perfetto）下的回溯选型；`-g` 符号信息对回溯性能的影响。

### 🔹 符号化管线：从地址到源码行

`addr2line` 的使用方式与边界（内联函数还原、优化后行号偏移）；`llvm-symbolizer` 相对 GNU addr2line 的优势；`-Wl,--export-dynamic` 对导出符号的影响；strip 后如何用 `.sym` 文件或 debug 信息包还原。

### 🔹 ELF 文件结构与符号表

`.symtab`（完整符号表）vs `.dynsym`（动态符号表）的区别；`readelf -s` 和 `objdump -t` 的实际用法；`strip --strip-unneeded` 保留哪些段、删哪些段；有符号表 vs 无符号表对堆栈还原成功率的影响。

### 🔹 Tombstone 格式与解析

Tombstone 文件的生成路径（`debuggerd` → `/data/tombstones/`）；`backtrace` 段、`memory near` 段、`ABI` 段的含义；Tombstone 中的 `Build fingerprint` 和 `Revision` 对版本定位的作用；如何从 Tombstone 提取有用信息做自动化归因。

### 🔹 线上 Native 堆栈采集方案

`sigaction` 注册信号处理器捕获 SIGSEGV/SIGABRT；在信号处理器中安全回溯（避免 malloc/IO）；`libunwind` 的 `_US_UNWIND_FRAME_RESUME` 模式；Google Breakpad / Crashpad 的 minidump 生成机制；Android 系统 `debuggerd_client` 的 fallback 路径。

### 🔹 Android 15+ CFI 强制启用与兼容性

Android 15 起对 system 模块强制启用 CFI（Control Flow Integrity），第三方 NDK 库的兼容性边界；CFI 检查失败导致的 SIGILL vs 常规 SIGSEGV 区分；`-fsanitize=cfi` 编译选项对包体积和运行时性能的影响。

## 扩展

### 🔸 Compose Native 交互层堆栈

Compose Runtime 在 JNI 层的堆栈回溯特殊处理；Compose Compiler 生成的 lambda 对 FP 链的影响。

### 🔸 混淆与 Native 混合堆栈

R8 混淆后的 Java 堆栈与 Native 堆栈的拼接策略；`mapping.txt` 与 Native 符号的联合还原。

### 🔸 ARM64 PAC 与 BTI 对堆栈的影响

Pointer Authentication Code 对回溯准确性的影响；Branch Target Identification 与 CFI 的协同。

<!-- outline-end -->

> 本节内容待加工。

[结构参考: Clippings/Android 应用稳定性剖析与优化 - Native Backtrace：Native 堆栈信息获取.md]
[结构参考: Clippings/Android 应用稳定性剖析与优化 - Android.bp 文件与符号表：如何才能找到函数符号？.md]
[结构参考: Clippings/Android 应用稳定性剖析与优化 - ELF 文件与 readelf & objdump ：了解 ELF 格式与解析工具.md]
