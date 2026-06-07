---
title: "eBPF 系统架构：bpfloader Rust 化与 BPF 程序组织"
chapter: "14.21"
status: draft
applicable_versions: "Android 14 (API 34) - Android 17 (API 37)"
tags: [ebpf, bpfloader, rust, bpf, system-architecture, timeInState]
related_chapters: ["14.10", "17.4", "26.11"]
created_by: "task2a-knowledge-gap"
created_date: "2026-06-07"
gap_source: "素材驱动/DeepResearch/AOSP结构"
---

# 14.21 eBPF 系统架构：bpfloader Rust 化与 BPF 程序组织

<!-- outline-start -->
## 要点

### 🔹 bpfloader 的角色与演进
bpfloader 是 Android BPF 体系的加载入口，负责在 init 阶段加载所有系统 BPF 程序。Android 17 完成了 bpfloader 的 Rust 化重写：C++ `NetBpfLoad.cpp` 已被完全移除，新入口为 `bpfloader.rs`，通过 bindgen 调用保留的 C++ `libbpf_android.so` 共享库。

### 🔹 bpfloader.rs 主流程
Rust 主流程：kmsg 文件初始化 → BpfKmsgLogger 注册 → 加载 libbpf 风格 .bpf 对象（timeInState.bpf）→ 调用 bindgen 包装的 C++ `legacyBpfLoader()` 走老路径 → `execNetBpfLoadDone()` execve 出 init 流程。理解这个启动链路对分析 BPF 程序加载失败至关重要。

### 🔹 BPF 程序的四个仓库与分工
Android 的 BPF 程序分散在四个仓：(1) `system/bpfprogs/` — timeInState.c、fuseMedia.c、bpfRingbufProg.c（通用程序）；(2) `system/bpf/progs/` — netd.c（网络守护进程相关）；(3) `frameworks/native/services/gpuservice/bpfprogs/` — gpuMem.c（GPU 内存跟踪）；(4) `packages/modules/Connectivity/bpf/progs/`（Connectivity 模块）。每个程序挂在不同的 tracepoint 上。

### 🔹 timeInState.c：核心 BPF 程序
timeInState.c 挂在 `tracepoint/sched/sched_switch` 上，追踪每个 UID 在每个 CPU 频率档位上的驻留时间、并发占用、活动 CPU 计数。是 Power Stats HAL 和 Battery Historian 的底层数据源。理解其数据结构对功耗分析至关重要。

### 🔹 gpuMem.c：GPU 内存跟踪
gpuMem.c 挂在 `tracepoint/gpu_mem/gpu_mem_total` 上，键为 `(gpu_id << 32 | pid)`，值为 size。被 GpuService 用于全局 GPU 内存统计，Perfetto 中可通过 `gpu_mem` counter 轨道观察。

### 🔹 libbpf_android 共享库
`Loader.cpp` 编译为 `libbpf_android.so`（`cc_library`），通过 `rust_bindgen` 生成 Rust FFI 绑定。即使 bpfloader 主入口已 Rust 化，核心 BPF 对象加载逻辑仍依赖 C++ libbpf。

### 🔹 调试方法
如何通过 `dumpsys bpf` 查看 BPF 程序加载状态，通过 `bpftool` 检查已加载程序和 map，以及通过 Perfetto 的 `ftrace/bpf/` 事件追踪加载过程。

## 扩展

### 🔸 自定义 BPF 程序的开发与加载
如何在 AOSP 环境中开发自定义 BPF 程序，使用 `libbpf_android` API 加载，以及 Android BPF 程序签名要求。

### 🔸 BPF 程序加载失败的排查
bpfloader 在 init 阶段运行，加载失败时 kmsg 中的错误信息格式和常见原因分析。

<!-- outline-end -->

> 本节内容待加工。
