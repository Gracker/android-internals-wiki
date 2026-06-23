---
title: "ch06-storage"
chapter: "06"
status: "ready-for-review"
applicable_versions: "Android 8 (API 26) - Android 17 (API 37)"
tags: [storage, io, filesystem]
drafted_date: "2026-06-23"
last_verified: "2026-06-23"
last_verified_against: "AOSP general knowledge"
confidence: medium
sources:
  - type: aosp
    path: "frameworks/base/core/java/android/content/pm/"
  - type: aosp
    path: "frameworks/native/cmds/installd/"
  - type: research
    path: "DeepResearch/android-install-optimization"
related_chapters: ["05", "07"]
---

# ch06-storage

<!-- outline-start -->
## 要点

### 🔹 Android 存储架构
- **存储层级**：内部存储、外部存储、应用专用存储、共享存储
- **权限模型**：运行时权限、存储访问框架 SAF、分区存储
- **文件系统**：FUSE、ext4、F2FS、针对移动设备的优化
- **存储空间管理**：空间分配、回收策略、压缩技术

### 🔹 安装优化机制
- **Staged Install**：分阶段安装流程，减少应用启动阻塞
- **dex2oat 优化**：编译时机优化，减少冷启动延迟
- **BackgroundDexOpt**：后台编译策略，提升应用响应速度
- **厂商定制边界**：vivo Turbo、小米 HyperOS 等厂商的优化实现

### 🔹 照片选择器演进
- **标准 Photo Picker**：传统弹窗式选择器
- **Embedded Photo Picker**：Android 14+ 新特性
- **零权限设计**：无需存储权限，只访问用户选择的照片
- **云端集成**：支持 Google Photos 等云端照片选择

## 扩展

### 🔸 存储性能优化
- **I/O 优化**：异步读写、批量操作、缓存策略
- **内存映射**：mmap 优化，减少数据拷贝开销
- **压缩算法**：LZ4、zstd 等现代压缩技术的应用
- **SSD 优化**：针对闪存特性的写入放大控制

### 🔸 安全与隐私
- **分区存储**：应用数据隔离，防止越界访问
- **权限最小化**：细粒度权限控制，减少权限滥用
- **加密存储**：文件级加密、数据库加密
- **数据清理**：应用卸载时的数据彻底清除

### 🔸 跨设备存储
- **云存储集成**：Google Drive、Dropbox 等云服务集成
- **设备间传输**：Quick Share、Nearby Share 等传输技术
- **存储空间共享**：家庭组、设备间的存储空间共享
- **离线优先**：云文档离线访问能力

<!-- outline-end -->
