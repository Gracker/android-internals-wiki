---
title: "ART Boot Image 内存映射与启动性能"
chapter: "1.57"
status: "draft"
applicable_versions: "Android 12 (API 31) - Android 17 (API 37)"
tags: [ART, boot-image, boot.art, 内存映射, Zygote, 启动优化, mmap]
related_chapters: [1.7, 1.11, 1.12, 8.2]
created_by: "task2a-knowledge-gap"
created_date: "2026-07-15"
gap_source: "章节深挖"
---
# 1.57 ART Boot Image 内存映射与启动性能

<!-- outline-start -->
## 要点

### 🔹 boot.art / boot.oat 构建机制：dex2oat --image 编译管线
{基于缺口分析生成的锚点内容}

### 🔹 内存映射策略：mmap MAP_PRIVATE + copy-on-write 共享页
{基于缺口分析生成的锚点内容}

### 🔹 Zygote fork 继承：boot image 页面如何在子进程间复用
{基于缺口分析生成的锚点内容}

### 🔹 boot image extension（boot-image-profile）：Profile-guided 启动镜像裁剪
{基于缺口分析生成的锚点内容}

### 🔹 StartupProfile 与 boot image 的关系：类预加载清单优化
{基于缺口分析生成的锚点内容}

### 🔹 系统升级后的 boot image 重建：dex2oat 触发条件与性能影响
{基于缺口分析生成的锚点内容}

## 扩展

### 🔸 OEM 自定义 boot image 策略与兼容性边界
{可选深入方向}

### 🔸 boot image 碎片化与内存浪费的诊断方法
{可选深入方向}

<!-- outline-end -->

> 本节内容待加工。
