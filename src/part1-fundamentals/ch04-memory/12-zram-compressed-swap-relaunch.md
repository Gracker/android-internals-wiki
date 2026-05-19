---
title: "ZRAM 压缩交换与应用重启延迟"
chapter: "4.12"
status: draft
applicable_versions: "Android 8 (API 26) - Android 17 (API 37)"
tags: [memory, zram, swap, lmkd, relaunch, performance]
related_chapters: ["4.2", "4.4", "8.2", "10.1", "15.2"]
created_by: "task2a-knowledge-gap"
created_date: "2026-05-20"
gap_source: "研究素材/官方文档/AOSP结构"
---

# 4.12 ZRAM 压缩交换与应用重启延迟

<!-- outline-start -->
## 要点

### 🔹 ZRAM 在 Android 内存压力中的位置
说明 ZRAM 处理的是匿名页压缩交换，和 page cache 回收、LMKD 杀进程不是同一层动作。

### 🔹 kswapd、direct reclaim、LMKD 的分工边界
区分后台回收、同步回收、进程淘汰三类路径，避免把低内存卡顿全部归因到 App 主线程。

### 🔹 应用重启延迟为什么受 swap-in 影响
从后台保活、匿名页换入、页面触碰顺序解释 relaunch 比冷启动和热启动都更难定位的原因。

### 🔹 热数据、冷数据与压缩块大小取舍
整理热感知压缩交换的研究结论，说明解压速度、压缩率、CPU 占用之间的取舍。

### 🔹 Perfetto 与 /proc 指标观测路径
列出 `kswapd`、PSI、major fault、RSS/swap、LMKD event、ApplicationExitInfo 的交叉验证入口。

### 🔹 Android 版本演进：MGLRU、ZRAM recompression、16KB page
跟踪内核和 Android 版本中与内存回收、压缩交换、页大小相关的行为变化。

### 🔹 App 端可做与不可做的边界
说明 App 能通过内存预算、缓存释放、进程拆分降低压力，但不能直接控制系统 swap 策略。

## 扩展

### 🔸 Ariadne 论文与热感知压缩交换
基于 HPCA 2025 / arXiv 2502.12826 梳理 hotness-aware、size-adaptive、proactive decompression 三个方向。

### 🔸 低内存设备与 Android Go 策略
补充低内存设备上的内存预算、后台保活和启动体验差异。

### 🔸 与 ApplicationExitInfo / LMK 归因的交叉验证
把 relaunch 延迟、LMK 退出原因、RSS 口径和线上上报串起来。

<!-- outline-end -->

> 本节内容待加工。
