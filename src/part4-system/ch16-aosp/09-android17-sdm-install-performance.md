---
title: "Android 17 SDM 安装编译链路性能"
chapter: "16.9"
status: draft
applicable_versions: "Android 16 (API 36) - Android 17 (API 37)"
tags: ['SDM', '安装', '编译', 'dexopt', '云编译', 'ART Service']
related_chapters: ['16.6', '1.9', '1.23', '21.11']
created_by: "task2a-knowledge-gap"
created_date: "2026-06-11"
gap_source: "DeepResearch 调研结果（score 18）+ AOSP 源码结构"
---

# 16.9 Android 17 SDM 安装编译链路性能

<!-- outline-start -->
## 要点

### 🔹 锚点 1：SDM（Secure Dex Metadata）产物管理架构
SDM 作为云编译产物的 ZIP 容器，包含 profile、vdex 等多种类型。ArtFileManager.java 中 getWritableArtifacts/getUsableArtifacts 识别 SDM 与 SDC 文件位置（Dalvik Cache 与 Next to DEX 两种路径）。

### 🔹 锚点 2：SDM 内容类型与 config.pb 配置解析
DexMetadataHelper.java 定义的六种 SDM 类型（TYPE_UNKNOWN/PROFILE/VDEX/PROFILE_AND_VDEX/NONE/ERROR），通过 ZIP 中 config.pb 配置文件和 profile/vdex 条目解析具体内容。

### 🔹 锚点 3：cloudCompilationPm() 标志与 SDM 创建条件
SDM 创建受 Flags.cloudCompilationPm() 控制。PrimaryDexopter.onDexoptStart 中根据此标志决定是否调用 maybeCreateSdc()。SDM 与传统本地 DEX 编译产物的共存策略。

### 🔹 键点 4：SDM 生命周期与安装链路性能影响
SDM 文件在安装、更新、卸载场景下的创建/删除时机。与现有 DM (DexMetadata) 文件的关系和迁移路径。安装链路中 SDM 引入的额外 I/O 开销与编译收益的权衡。

### 🔹 锚点 5：SDM 对启动性能的实际影响
SDM 携带的 profile 与 vdex 对 dexopt 编译质量的影响，以及由此产生的启动性能提升。与传统 Cloud Profile 的对比。

### 🔹 锚点 6：SDM 安全模型与权限边界
SDM/SDC 文件的 SELinux 上下文、权限控制与完整性验证。Secure Dex Metadata Companion 的安全设计考量。

## 扩展

### 🔸 扩展点 1
SDM 与 Baseline Profile 的协同与互斥关系

### 🔸 扩展点 2
SDM 在多 APK/App Bundle 场景下的分片管理策略

### 🔸 扩展点 3
OEM 定制 ROM 中 SDM 机制的适配与兼容性边界

<!-- outline-end -->

> 本节内容待加工。
