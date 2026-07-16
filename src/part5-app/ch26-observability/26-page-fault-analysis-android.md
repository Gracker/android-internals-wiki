---
title: "Page Fault 类型分析与 Android 实践"
chapter: "26.26"
status: draft
applicable_versions: "Android 8 (API 26) - Android 17 (API 37)"
tags: [page-fault, minor-fault, major-fault, mmap, memory, observability]
related_chapters: ["26.25", "4.01", "9.13"]
created_by: "task2a-knowledge-gap"
created_date: "2026-07-16"
gap_source: "参考书驱动（Clippings/线上疑难问题 45.md）"
---

# 26.26 Page Fault 类型分析与 Android 实践

<!-- outline-start -->
## 要点

### 🔹 Page Fault 基本概念
{CPU 访问的虚拟地址没有映射到物理页时触发缺页异常，由内核 Page Fault Handler 处理}

### 🔹 Minor Page Fault（次缺页）
{页框已在内存中，只需更新页表映射；典型场景：共享库被多个进程使用时的 COW（Copy-On-Write）}

### 🔹 Major Page Fault（主缺页）
{需要从存储设备读取数据到内存；Android 无 Swap 分区时，主要来源是 mmap 文件的磁盘载入}

### 🔹 Invalid Page Fault（无效缺页）
{访问了未映射或受保护的地址，通常导致 SIGSEGV 段错误}

### 🔹 Android 平台的特殊性
{Android 默认无 Swap 分区（zram 压缩交换除外），major page fault 主要来自 mmap 文件的磁盘载入；与 Linux 桌面行为有显著差异}

### 🔹 Page Fault 计数与内存分配量估算
{/proc/[pid]/stat 中的 minor/major fault 计数；fault × 4KB 可粗略估算内存分配量}

### 🔹 I/O 瓶颈的 Page Fault 信号
{major page fault 激增 + iowait 上升 → 存储子系统瓶颈；典型场景：冷启动大量 dex/oat 文件 mmap 载入}

### 🔹 Page Fault 监控方案设计
{线上采集 page fault 计数变化趋势，结合场景标注（启动/滑动/后台）构建内存行为画像}

## 扩展

### 🔸 zram 对 Page Fault 行为的影响
{Android zram 压缩交换使被压缩的内存页可被"换入"，改变了传统 page fault 模式}

### 🔸 userfaultfd 与 Page Fault 控制流
{Linux 的 userfaultfd 机制允许用户态接管 page fault 处理，在 Android 17 中可用于内存监控和迁移}

<!-- outline-end -->

> 本节内容待加工。
