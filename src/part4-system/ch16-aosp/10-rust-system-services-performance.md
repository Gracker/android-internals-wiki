---
title: "Rust 化系统服务性能边界与 FFI 开销分析"
chapter: "16.10"
status: draft
applicable_versions: "Android 12 (API 31) - Android 17 (API 37)"
tags: [rust, ffi, jni, system-services, keystore, bluetooth, dns-resolver, bionic, scudo, monomorphization]
related_chapters: ["1.4", "1.32", "3.8", "14.21", "20.16"]
created_by: "task2a-knowledge-gap"
created_date: "2026-06-28"
gap_source: "AOSP结构"
---

# 16.10 Rust 化系统服务性能边界与 FFI 开销分析

<!-- outline-start -->
## 要点

### 🔹 Android Rust 化路线图与当前进展
{Google 自 Android 12 起积极推进系统服务的 Rust 重写。Android 17 中已有多个核心系统服务以 Rust 实现：Keystore 2.0、DNS Resolver（netd2）、UWB（Ultra-Wideband）、Virtualization Framework (virtmgr)、Bluetooth GDI/HAL 部分组件、bpfloader 等。Rust 化的核心目标是内存安全（消除 use-after-free、buffer overflow 等漏洞类别），但其性能边界和 FFI 开销需要系统级分析。}

### 🔹 已完成 Rust 重写的系统服务清单
{基于 android-17.0.0_r1 的 AOSP 源码统计：Keystore 2.0（system/security/keystore2）、DNS Resolver（packages/modules/DnsResolver）、UWB（system/uwb）、Virtualization Framework（packages/modules/Virtualization）、Bluetooth HAL 部分（system/bt）、bpfloader（frameworks/libs/net/netd/bpfloader）、Rust HTTP（packages/modules/Connectivity）等。每个服务的 Rust 代码量、FFI 边界数量和性能特征各不相同。}

### 🔹 Rust ↔ C/C++ FFI 性能开销分析
{Rust 与 C/C++ 的 FFI 调用本质上是零成本函数调用（extern "C"），但实际开销来自：(1) 跨语言边界的编译器优化屏障（LTO 可能部分消除）；(2) 数据布局转换（如 CString ↔ Rust String 的拷贝）；(3) panic/catch_unwind 跨边界的处理。典型 FFI 调用开销为 10-50ns，但复杂数据结构的 marshalling 可能显著增加延迟。}

### 🔹 Rust ↔ Java JNI 调用链路性能
{Android 系统服务通常需要暴露 Java API（通过 AIDL）。Rust 服务通过 JNI 桥接与 Java 层交互，调用链路为 Java → JNI → C wrapper → Rust extern "C"。相比 C++ 直接 JNI，多了一层 FFI 边界。Keystore 2.0 的 JNI 桥接性能分析显示，在高频调用场景（如批量密钥操作）下，FFI 开销可能成为瓶颈。}

### 🔹 Rust 内存安全对性能的影响
{Rust 的所有权系统和借用检查器在编译期消除内存安全漏洞类别，理论上不需要运行时检查（零成本抽象）。实际影响：(1) 某些场景需要 RefCell/Arc 运行时开销；(2) Rust 的 aliasing rules 允许编译器做更激进的优化；(3) 消除了 Scudo 的部分安全开销（但 Rust 服务仍链接 Scudo）。总体而言，Rust 性能通常与 C++ 持平或略好。}

### 🔹 Rust 分配器与 Scudo 交互
{Android 上 Rust 系统服务默认使用 Bionic 的 Scudo 分配器（通过 std::alloc 调用 malloc/free）。Rust 的 std::alloc 转发到 jemalloc/scudo，因此 Rust 服务的内存分配性能与 C/C++ 服务一致。使用 #[global_allocator] 替换为 Rust 原生分配器的做法在 Android 系统服务中不推荐，因为会绕过 Scudo 的安全保护。}

### 🔹 Rust panic/unwind 机制与 C++ 异常对比
{Rust 的 panic 机制与 C++ 异常在 ARM64 上使用相同的 DWARF unwinder（libunwind）。但 Rust panic 的开销特征不同：(1) panic 是非正常路径，编译器假设它极少发生；(2) catch_unwind 有运行时成本；(3) Rust 的 Result 类型鼓励显式错误处理，减少了对 panic 路径的依赖。Android 系统服务配置 panic = abort 以减小二进制体积，但会丢失跨 FFI 边界的 unwind 能力。}

### 🔹 Rust 二进制体积与 monomorphization 代码膨胀
{Rust 的泛型采用 monomorphization（单态化），为每个具体类型生成一份代码。这导致：(1) 二进制体积可能显著增加（比等效 C++ 大 20-50%）；(2) icache 压力增大；(3) 编译时间增加。Android 通过 dylib（动态链接 Rust stdlib）和 LTO 缓解体积问题。Android 17 的 Soong 构建系统支持 Rust dylib 和 thin-LTO 优化。}

## 扩展

### 🔸 Rust 系统服务调试与性能分析
{Rust 符号的 demangle（rust-demangler 而非 c++filt）、Perfetto heap profiler 对 Rust 分配的支持、Perfetto cpu profiler 对 Rust 函数符号的解析。}

### 🔸 Soong 构建系统与 Rust crate 管理
{Android Soong 构建系统的 rust_* 模块类型、external/upstream crates 管理策略、cargo-to-soong 转换工具链。}

<!-- outline-end -->

> 本节内容待加工。
