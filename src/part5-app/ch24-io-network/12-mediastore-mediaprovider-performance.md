---
title: "MediaStore 与 MediaProvider 性能治理"
chapter: "24.12"
status: draft
applicable_versions: "Android 10 (API 29) - Android 17 (API 37)"
tags: [MediaStore, MediaProvider, scoped-storage, media-transcoding, thumbnails, io-performance]
related_chapters: ["6.1", "6.4", "22.6", "24.1", "24.6"]
created_by: "task2a-knowledge-gap"
created_date: "2026-05-21"
gap_source: "AOSP结构+官方文档+素材索引去重"
gap_score: "17/20"
sources:
  - type: official
    path: "https://developer.android.com/training/data-storage/shared/media"
  - type: official
    path: "https://developer.android.com/social-and-messaging/guides/media-thumbnails"
  - type: official
    path: "https://developer.android.com/media/platform/transcoding"
  - type: aosp-doc
    path: "https://source.android.com/docs/core/media/media-provider"
  - type: aosp-doc
    path: "https://source.android.com/docs/core/media/media-transcoding"
  - type: aosp-doc
    path: "https://source.android.com/docs/core/storage/scoped"
  - type: aosp
    path: "packages/providers/MediaProvider/"
---

# 24.12 MediaStore 与 MediaProvider 性能治理

<!-- outline-start -->
## 要点

### 🔹 MediaStore 访问模型与性能边界
从 App 视角说明 `MediaStore`、`ContentResolver`、文件描述符、直接路径访问之间的差异，区分适合批量枚举、单文件读写、媒体预览和后台同步的访问方式。

### 🔹 MediaProvider 索引、扫描与元数据更新
梳理 `MediaProvider` 如何维护图片、视频、音频元数据索引，解释扫描、增量同步、`MediaStore` version 变化和 `ContentObserver` 对相册、备份、文件管理类 App 的影响。

### 🔹 Scoped Storage、FUSE 与批量操作
说明 Android 10 以后共享存储的访问路径、FUSE 额外开销、批量写入 / 更新 API 的适用场景，以及绕过低效逐文件操作的实践边界。

### 🔹 缩略图、预览图与解码成本
对比平台缩略图 API、`ThumbnailUtils`、`ImageDecoder`、`BitmapFactory`、`MediaMetadataRetriever` 的适用场景，说明列表预览、视频首帧、超大图和后台预生成的成本差异。

### 🔹 兼容媒体转码与 HDR → SDR 退化路径
基于兼容媒体转码和 Photo Picker HDR 转 SDR 能力，说明转码触发条件、延迟来源、缓存策略，以及 App 通过 `ApplicationMediaCapabilities` 声明能力后能减少哪些隐性成本。

### 🔹 线上排查与 Perfetto / dumpsys 观察点
整理媒体库访问慢、缩略图加载慢、转码等待、扫描风暴、数据库锁竞争等问题的观察入口，包括 `dumpsys media_provider`、Perfetto I/O / binder / database 轨道和应用侧埋点。

## 扩展

### 🔸 大图库首屏加载与分页同步策略
围绕相册、IM、文件管理器这类大图库场景，展开分页查询、预取窗口、缩略图缓存和取消机制。

### 🔸 MANAGE_EXTERNAL_STORAGE 类 App 的性能与合规边界
补充备份、杀毒、文件管理器等特殊 App 在全文件访问权限下的性能路径，以及普通 App 不应依赖该权限的原因。

<!-- outline-end -->

> 本节内容待加工。
