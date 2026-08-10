---
title: "第 6 章存储与 I/O 主题分流"
chapter: "06"
status: "outdated"
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

# 第 6 章：存储与 I/O 主题分流


## 内容边界

存储架构、应用安装、Photo Picker、跨设备传输和云服务无法在一个技术章节中建立清楚的源码边界。以下说法尤其不能脱离设备与版本直接引用：

- ext4、F2FS、EROFS 和 OverlayFS 的用途不同，不能把文件系统选择简化成“F2FS 一定更快”；
- FUSE、passthrough 与 FUSE BPF 是否参与共享存储访问，取决于平台版本、挂载方式、请求类型和产品配置；
- `dex2oat`、BackgroundDexOpt 和 staged install 属于安装、ART 与 PackageManager 方向，不是块 I/O 调度的同一条执行路径；
- Embedded Photo Picker、云媒体提供方和具体云服务的可用性受系统组件、地区、服务实现与用户选择影响；
- 厂商功能名称和性能收益需要对应版本、设备、测试方法与公开证据，不能用品牌示例代替 Android 平台机制。

对应主题入口如下：

- [6.1 Android 存储架构](./01-storage-architecture.md)：分区、挂载、加密、应用目录和共享存储边界；
- [6.2 Android 文件系统](./02-filesystem.md)：ext4、F2FS、EROFS 与产品配置；
- [6.3 I/O 调度与性能](./03-io-scheduling.md)：块层、调度器、writeback 和长尾分析；
- [6.4 Android 存储演进](./04-storage-evolution.md)：scoped storage、权限和平台版本变化；
- [6.6 vold、FUSE 与 scoped storage I/O](./06-vold-fuse-scoped-storage-io.md)：Android 17 共享存储执行路径；
- [6.7 FUSE passthrough 与 FUSE BPF](./07-fuse-bpf-scoped-storage-io-performance.md)：快路径条件和调试方法。

Photo Picker、应用安装和 ART 编译应在各自专题章节中以 AOSP `android-17.0.0_r1` 核对，不能依据这份主题索引推导技术结论。
