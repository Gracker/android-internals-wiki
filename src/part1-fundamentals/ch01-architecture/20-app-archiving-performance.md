---
title: "App Archiving 机制与恢复性能"
chapter: "1.20"
status: draft
applicable_versions: "Android 15 (API 35) - Android 17 (API 37)"
tags: [package-manager, app-archiving, storage, app-startup, android-15]
related_chapters: ["1.9", "6.1", "8.2", "12.1", "16.2"]
created_by: "task2a-knowledge-gap"
created_date: "2026-05-17"
gap_source: "素材驱动/AOSP结构/官方文档"
material_paths:
  - "OpenClaw定时任务/AutoResearchClaw调研报告/2026-05-01-android-app-archiving-package-archiver-activitystarter-mechanism.md"
  - "developer.android.com/about/versions/15/features"
  - "cs.android.com frameworks/base/services/core/java/com/android/server/pm/PackageArchiver.java"
  - "cs.android.com frameworks/base/services/core/java/com/android/server/wm/ActivityStarter.java"
sources:
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/pm/PackageArchiver.java @ AOSP main"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/wm/ActivityStarter.java @ AOSP main"
  - type: official
    path: "https://developer.android.com/about/versions/15/features"
  - type: obsidian
    path: "OpenClaw定时任务/AutoResearchClaw调研报告/2026-05-01-android-app-archiving-package-archiver-activitystarter-mechanism.md"
---

# 1.20 App Archiving 机制与恢复性能

<!-- outline-start -->
## 要点

### 🔹 App Archiving 解决的问题边界
说明 Android 15 平台归档能力和 Google Play 早期归档方案的差异：平台归档会移除 APK 与缓存文件、保留用户数据，并让系统继续保留可恢复入口。重点区分存储回收、安装状态、进程生命周期和 LMK 之间的边界。

### 🔹 PackageInstaller.requestArchive() 的入口条件
梳理 `PackageInstaller.requestArchive()`、`REQUEST_DELETE_PACKAGES` 权限、installer of record、`DELETE_ARCHIVE | DELETE_KEEP_DATA` 标志位，以及为什么普通 App 不能任意归档其他应用。

### 🔹 PackageArchiver 与 ArchiveState 数据模型
解析 `PackageArchiver` 的职责：创建和保存 `ArchiveState`、记录归档 Activity 信息、生成 Launcher 可展示的图标与标题、判断目标 Intent 是否指向归档应用。

### 🔹 ActivityStarter 点击恢复的拦截路径
从 Launcher 点击归档图标进入 `ActivityStarter`，说明 `START_CLASS_NOT_FOUND` 分支如何调用 `isIntentResolvedToArchivedApp()`，再通过 `requestUnarchiveOnActivityStart()` 转给 installer 恢复应用。

### 🔹 恢复链路的性能口径
拆分点击恢复的耗时：系统分支判断、installer 弹窗或静默确认、网络下载、PackageInstaller session、dexopt / profile、首次启动。给出 trace、logcat 与 PackageInstaller 回调的观察点。

### 🔹 与 PMS、存储和启动优化的交叉关系
回连 1.9 PMS、6.1 存储架构、8.2 App 启动全流程和 12.1 APK 体积优化：归档节省的是安装包和缓存文件，不等于减少已运行进程的 RSS，也不直接改变 LMK 选择。

### 🔹 版本与生态边界
整理 Android 15-17 的公开 API、AOSP main 实现、第三方应用商店需要处理 `ACTION_UNARCHIVE_PACKAGE` 的条件，以及 Android 16 以后 SDM / 签名校验线索的待验证边界。

## 扩展

### 🔸 SDM 签名校验与归档恢复安全性
补充 `.sdm` 签名文件、installer 身份、恢复包完整性校验的源码线索；无法验证的细节标注 `[待验证]`。

### 🔸 归档状态对 SELinux 与包可见性的影响
检查归档应用在 package visibility、LauncherApps、Settings、权限状态和 SELinux context 上的表现差异。

### 🔸 与自动清理 / 空间治理策略的关系
分析系统自动归档、用户手动归档、应用商店空间治理策略和企业设备策略之间的优先级关系。

<!-- outline-end -->

> 本节内容待加工。
