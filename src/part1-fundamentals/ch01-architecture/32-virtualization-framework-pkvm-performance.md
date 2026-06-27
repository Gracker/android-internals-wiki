---
title: "Android Virtualization Framework 架构与 pKVM 隔离性能边界"
chapter: "1.32"
status: draft
applicable_versions: "Android 13 (API 33) - Android 17 (API 37)"
tags: [avf, virtualization, pkvm, crosvm, microdroid, vm-lifecycle, isolation-overhead]
related_chapters: ["1.3", "1.4", "4.1", "4.2"]
created_by: "task2a-knowledge-gap"
created_date: "2026-06-27"
gap_source: "AOSP结构/官方文档"
---

# 1.32 Android Virtualization Framework 架构与 pKVM 隔离性能边界

<!-- outline-start -->
## 要点

### 🔹 AVF 全景：从 Android 13 到 Android 17 的演进
- Android 13 引入 AVF，提供受保护的 VM 执行环境
- 核心组件：pKVM（protected KVM）、crosvm（VMM）、Microdroid（轻量 Android guest）
- Android 14-15 扩展：VirtualizationService API 稳定化、ADB inside VM 支持
- Android 16-17 扩展：虚拟设备支持（VirtualDeviceInfo）、多 VM 并发、性能调优
- 与 TrustZone / TEE 的定位区分：AVF 是第二级隔离（VM 级），TEE 是第一级（硬件级）

### 🔹 pKVM 内存隔离机制
- protected guest：VM 内存对 host 不可见（host 无法读写 guest 物理内存）
- 内存共享机制：shared_buf 和 grant tables 在 crosvm 和 guest 之间的数据交换
- 页表隔离：Stage-2 页表由 hypervisor 管理，host kernel 无法映射 guest 页面
- 性能代价：内存隔离导致的 copy 开销（非共享区域的数据需要通过 virtio 传输）
- 内存分配：guest memory 不参与 host 的 kswapd/lmkd 回收，对系统内存压力有独立影响

### 🔹 crosvm VMM 架构与 VirtIO 设备模型
- crosvm 用 Rust 编写，每个 VirtIO 设备运行在独立线程
- 关键 VirtIO 设备：virtio-blk（块设备）、virtio-net（网络）、virtio-console、virtio-vsock
- VirtIO 设备的上下文切换开销：每个 guest 退出到 host 再返回的开销分析
- 与 QEMU/KVM 的对比：crosvm 精简设备模型带来的启动速度优势
- Android 17 中 crosvm 的性能优化： balloon driver、free page reporting

### 🔹 VM 生命周期性能
- VM 启动时间分解：VM 配置解析 → 内存分配 → 内核加载 → guest init → 应用就绪
- 典型 Microdroid 启动时间：Android 13 约 3-5 秒，Android 17 优化至约 1-2 秒
- VM 内存开销：Microdroid 最小配置约 64MB（内核 + initramfs + runtime）
- VM 销毁延迟：从 VirtualMachine.stop() 到 VM 资源完全释放的时间
- 并发 VM 数量限制：Android 17 中 pKVM 的最大并发 VM 数量和内存约束

### 🔹 VM 与 host 的 IPC 通信性能
- vsock 通信模型：AF_VSOCK socket 的连接建立和数据传输
- binder over vsock：Android 14+ 支持跨 VM Binder 通信的延迟和吞吐
- 共享内存通信：gralloc/dmabuf 在 host 和 guest 之间的共享机制
- 与传统进程间 Binder IPC 的性能对比：延迟、吞吐、CPU 开销
- Android 17 新增的 RPC Binder over vsock 与传统 binder 的差异

### 🔹 AVF 对系统整体性能的影响
- pKVM 启用对 host 性能的影响：内存不可用于 host 页面合并（KSM）、不能被 lmkd 回收
- pKVM shadow page table 维护开销
- VM 运行时的 host CPU 开销：crosvm 线程、virtio 处理、exit handler 的 CPU 占比
- 对 thermal 和功耗的影响：VM 计算 task 导致的额外 CPU/GPU 功耗
- Android 17 中 AVF 的性能 profiling 工具：VM 内 Perfetto 支持

## 扩展

### 🔸 Microdroid 内部 Android 运行时
- Microdroid 中的 init、binder、service manager 简化实现
- Microdroid 中的应用安装和运行机制
- Microdroid 的 GC、内存管理、网络栈与标准 Android 的差异

### 🔸 AVF 安全性与性能的 trade-off
- protected VM vs non-protected VM 的性能差异
- 是否使用 pKVM 的决策树：安全需求 vs 性能代价
- Android 17 中 zero-copy 路径在 protected VM 中的限制

### 🔸 商业应用场景与性能预期
- Remote Attestation（远程证明）的性能开销
- 隔离工作档案（Isolated Work Profile）基于 AVF 的可行性
- 端侧 AI 模型在 VM 中推理的性能边界

<!-- outline-end -->

> 本节内容待加工。
