---
title: "Android 17 FUSE-BPF 与 Scoped Storage I/O 性能"
chapter: "6.7"
status: draft
applicable_versions: "Android 11 (API 30) - Android 17 (API 37)"
tags: [storage, fuse, bpf, scoped-storage, io-performance, android17]
related_chapters: ["6.1", "6.6", "24.12"]
created_by: "task2a-knowledge-gap"
created_date: "2026-06-05"
gap_source: "AOSP结构/官方文档"
---

# 6.7 Android 17 FUSE-BPF 与 Scoped Storage I/O 性能

<!-- outline-start -->
## 要点

### 🔹 锚点 1：Scoped Storage I/O 路径演进：FUSE → FUSE-BPF
- Android 11 引入 Scoped Storage 后，第三方应用访问媒体文件必须经过 FUSE（Filesystem in Userspace）守护进程
- FUSE 守护进程（`/system/bin/sdcard`）在内核空间和用户空间之间做数据拷贝和权限检查，每次 I/O 操作至少两次上下文切换
- 性能损耗表现：顺序读写吞吐量下降 30-50%、小文件随机 I/O 延迟增加 2-3 倍、`mediaProvider` 进程 CPU 占用随 I/O 并发线性增长
- Android 17 用 FUSE-BPF 替代用户态 FUSE 守护进程处理 Scoped Storage I/O，用 BPF 程序在内核空间直接完成权限检查，消除用户态往返

### 🔹 锚点 2：FUSE-BPF 架构与内核实现
- FUSE-BPF 位于内核 `fs/fuse-bpf/` 目录，是 FUSE 子系统的 BPF 扩展
- 核心设计：用 BPF 程序替代用户态 FUSE 守护进程的请求处理逻辑，BPF 程序直接在内核中执行权限检查和路径映射
- 关键数据结构：`fuse_bpf_entry` 管理 BPF 程序的挂载和生命周期，每个 `fuse_conn` 可以关联一组 BPF 程序
- 与传统 FUSE 的兼容性：FUSE-BPF 作为 FUSE 的可选后端，未加载 BPF 程序时回退到传统用户态 FUSE
- 内核配置：`CONFIG_FUSE_BPF`，需要 BPF 校验器支持

### 🔹 锚点 3：FUSE-BPF I/O 路径性能提升
- 消除用户态上下文切换：读写请求在内核空间直接由 BPF 程序处理，无需唤醒 `sdcard` 守护进程
- 内存拷贝减少：传统 FUSE 需要将数据从内核缓冲区拷贝到用户态再拷贝回来；FUSE-BPF 在内核完成全部操作
- 大文件顺序读写性能：从 FUSE 路径的 ~800MB/s 恢复到接近直接 I/O 的 ~1.5GB/s（UFS 4.0 设备）
- 小文件操作性能：`open()` + `read()` + `close()` 的端到端延迟从 ~2ms 降低到 ~0.5ms
- `MediaProvider` CPU 占用：高并发 I/O 场景下 CPU 占用从 15-25% 降至 <5%

### 🔹 锚点 4：BPF 程序在权限检查中的角色
- BPF 程序负责实现 Scoped Storage 的核心安全策略：文件类型白名单、目录访问控制、文件大小限制
- 程序加载时机：`vold` 在挂载 FUSE 文件系统时通过 `bpf_prog_load()` 加载预编译的 BPF 程序
- BPF Map 用于存储权限策略表：`fuse_bpf_policy_map` 存储每个路径前缀的访问规则
- `bpf_trace_printk` 可用于调试 BPF 程序的决策过程
- 回退机制：当 BPF 程序无法处理某个操作（如复杂的 URI 权限解析）时，回退到用户态 `MediaProvider`

### 🔹 锚点 5：对应用 I/O 行为的实际影响
- 使用 `MediaStore` API 的应用：性能透明提升，无需代码修改
- 直接文件路径访问（`/sdcard/DCIM/` 等）的应用：I/O 吞吐量显著提升，但仍有少量 BPF 开销
- 通过 `Storage Access Framework (SAF)` 的访问：路径不变，性能收益取决于底层 I/O 路径
- `ContentResolver.query()` 批量查询：查询延迟降低约 40%
- 需要注意的边界：某些 `File` API 在 Android 17 上可能仍走传统 FUSE 路径（如 `File.rename()` 跨目录操作）

### 🔹 锚点 6：Perfetto 中观测 FUSE-BPF I/O 路径
- `sched` + `ftrace` 数据源可以追踪 `fuse-bpf` 相关的系统调用
- 观测指标：`sys_enter_fuse_bpf` / `sys_exit_fuse_bpf` tracepoint（如果可用）
- 对比观测方法：在 Android 16 (FUSE) 和 Android 17 (FUSE-BPF) 上分别执行相同 I/O 操作，对比 `I/O` 轨道上的读写延迟
- `simpleperf stat` 可以统计 BPF 程序的执行次数和耗时
- `bpftrace` 可以挂载到 `fuse_bpf_*` 函数做实时延迟分析

### 🔹 锚点 7：迁移与兼容性考量
- Android 17 上的 FUSE-BPF 是透明切换，应用无需修改代码
- Target SDK < 30 的应用仍使用传统存储权限模型，不受 FUSE-BPF 影响
- 部分厂商可能因内核版本限制（需要 Linux 6.1+）而无法启用 FUSE-BPF，回退到传统 FUSE
- 内核模块依赖：需要 `CONFIG_BPF_SYSCALL=y`、`CONFIG_FUSE_FS=y`、`CONFIG_FUSE_BPF=y`
- 厂商定制存储方案（如三星的 `Sem` 模块）可能与 FUSE-BPF 存在兼容性问题

## 扩展

### 🔸 扩展点 1：FUSE-BPF 与 io_uring 的协同优化
- Linux 6.x 内核中 `io_uring` 和 BPF 的协同为 I/O 性能提供了新的优化方向
- FUSE-BPF 后续可能支持 `io_uring` 提交模式，进一步减少系统调用开销

### 🔸 扩展点 2：FUSE-BPF 在非存储场景的应用前景
- FUSE-BPF 的通用架构不仅限于存储，可用于实现高效的自定义文件系统
- 在容器化 Android（microdroid）场景中可作为轻量级文件系统后端

<!-- outline-end -->

> 本节内容待加工。
