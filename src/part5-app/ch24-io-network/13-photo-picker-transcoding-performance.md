---
title: "Photo Picker、媒体转码与缓存治理"
chapter: "24.13"
status: draft
applicable_versions: "Android 13 (API 33) - Android 17 (API 37)"
tags: [photo-picker, mediaprovider, transcoding, storage, io-performance]
related_chapters: ["7.10", "12.1", "20.10", "22.6", "24.12", "26.16"]
created_by: "task2a-knowledge-gap"
created_date: "2026-05-22"
gap_source: "官方文档/每日信息/素材驱动/AOSP结构"
---

# 24.13 Photo Picker、媒体转码与缓存治理

<!-- outline-start -->
## 要点

### 🔹 Photo Picker 的性能边界
说明 Photo Picker 与传统 SAF / `ACTION_PICK` / 应用自建相册页的差异，重点放在启动延迟、权限面、媒体 URI 生命周期和跨版本兼容策略。

### 🔹 嵌入式 Photo Picker 的接入成本
梳理嵌入式 Photo Picker 在页面切换、窗口嵌入、回退行为和冷启动路径上的成本，区分系统能力与应用 UI 编排成本。

### 🔹 视频转码的时间与存储成本
覆盖官方文档提到的 transcoding 处理时间、新文件占用、1 分钟视频长度限制、缓存文件回收策略，并给出线上指标设计。

### 🔹 MediaProvider 与缓存清理链路
从 MediaProvider、idle maintenance 和应用本地缓存三个层次分析媒体选择后的文件治理边界，避免把系统缓存和业务缓存混为一谈。

### 🔹 大图/多选场景的 I/O 与内存压力
补齐多选图片、HEIC/AVIF、缩略图预取、大图解码和上传前压缩对主线程、I/O 线程、Bitmap 内存的影响。

### 🔹 可观测性与回归防护
设计 Photo Picker 打开耗时、首张缩略图时间、选择完成到业务可用时间、转码耗时、失败率和缓存占用的指标。

## 扩展

### 🔸 Photo Picker 与 Android 版本适配矩阵
补充 Android 13 原生、Android 11/12 模块化 backport、Google Play services / OEM 差异的接入边界。

### 🔸 与隐私权限、应用锁和 OEM 相册能力的关系
只记录影响媒体选择性能和失败率的边界，不展开隐私功能本身。

### 🔸 与 24.12 MediaStore / MediaProvider 的交叉引用
加工时只引用 24.12 的 MediaProvider 原理，不重复写媒体库扫描机制。

<!-- outline-end -->

> 本节内容待加工。
