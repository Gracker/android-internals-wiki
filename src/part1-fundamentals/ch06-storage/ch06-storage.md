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

# 第 6 章：存储与 I/O（历史纲要）

> ⚠️ 本文件是 Hermes/OpenClaw 保留的历史纲要。frontmatter、选题和受保护 outline 的范围并不一致，部分表述也没有产品配置或源码证据。为保留流水线识别信息，下方 outline 原样保留；第 6 章的可引用入口请阅读 [README](./README.md)。

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
- **数据清理**：应用卸载时完整删除数据

### 🔸 跨设备存储
- **云存储集成**：Google Drive、Dropbox 等云服务集成
- **设备间传输**：Quick Share、Nearby Share 等传输技术
- **存储空间共享**：家庭组、设备间的存储空间共享
- **离线优先**：云文档离线访问能力

<!-- outline-end -->

## 审阅结论

这份 outline 同时包含存储架构、应用安装、Photo Picker、跨设备传输和云服务，无法在一个技术章节中建立清楚的源码边界。以下说法尤其不能脱离设备与版本直接引用：

- ext4、F2FS、EROFS 和 OverlayFS 的用途不同，不能把文件系统选择简化成“F2FS 一定更快”；
- FUSE、passthrough 与 FUSE BPF 是否参与共享存储访问，取决于平台版本、挂载方式、请求类型和产品配置；
- `dex2oat`、BackgroundDexOpt 和 staged install 属于安装、ART 与 PackageManager 方向，不是块 I/O 调度的同一条执行路径；
- Embedded Photo Picker、云媒体提供方和具体云服务的可用性受系统组件、地区、服务实现与用户选择影响；
- 厂商功能名称和性能收益需要对应版本、设备、测试方法与公开证据，不能用品牌示例代替 Android 平台机制。

本文件不再扩写技术正文。对应内容已经拆到以下章节：

- [6.1 Android 存储架构](./01-storage-architecture.md)：分区、挂载、加密、应用目录和共享存储边界；
- [6.2 Android 文件系统](./02-filesystem.md)：ext4、F2FS、EROFS 与产品配置；
- [6.3 I/O 调度与性能](./03-io-scheduling.md)：块层、调度器、writeback 和长尾分析；
- [6.4 Android 存储演进](./04-storage-evolution.md)：scoped storage、权限和平台版本变化；
- [6.6 vold、FUSE 与 scoped storage I/O](./06-vold-fuse-scoped-storage-io.md)：Android 17 共享存储执行路径；
- [6.7 FUSE passthrough 与 FUSE BPF](./07-fuse-bpf-scoped-storage-io-performance.md)：快路径条件和调试方法。

Photo Picker、应用安装和 ART 编译应在各自专题章节中以 AOSP `android-17.0.0_r1` 重新核对，不从本历史纲要推导结论。
