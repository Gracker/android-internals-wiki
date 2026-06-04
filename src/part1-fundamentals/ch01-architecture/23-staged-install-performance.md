---
title: "Android Staged Install 与安装原子性性能"
chapter: "1.23"
status: draft
applicable_versions: "Android 10 (API 29) - Android 17 (API 37)"
tags: [package-manager, staged-install, apk-install, atomicity, performance]
related_chapters: ["1.9", "1.20", "16.6"]
created_by: "task2a-knowledge-gap"
created_date: "2026-06-04"
gap_source: "素材驱动"
confidence: medium
---

# 1.23 Android Staged Install 与安装原子性性能

<!-- outline-start -->
## 要点

### 🔹 锚点 1：Staged Install 机制概览
- Staged Install 的设计动机：解决 A/B 分区更新和应用大版本更新的原子性问题
- 核心流程：Prepare → Commit → Reboot（如需）→ Finalize
- 与传统 installFlow 的区别： stagedInstallSession 不需要用户确认即可在后台完成
- AOSP 源码路径：PackageInstallerSession 中的 staged 安装路径

### 🔹 锚点 2：安装性能瓶颈定位
- APK 验证阶段：签名校验（v1/v2/v3/v3.1）的 CPU 开销
- DEX 优化阶段：dex2oat 编译耗时与编译滤镜选择
- 磁盘 I/O 阶段：解压、复制、 SELinux relabel 的开销分布
- 大型 APK（>200MB）的安装耗时分解

### 🔹 锚点 3：Staged Install 与系统重启的交互
- 哪些 staged session 需要 reboot：涉及 native 库更新或 split APK 变更
- reboot 期间的安装恢复： deviceSpecific config → finalize session
- 重启后首次启动的优化：dexopt 延迟、Profile 引导

### 🔹 锚点 4：Android 16/17 安装性能优化
- Android 16 云端 Profile：安装时直接应用云端 Profile 进行 dexopt
- Android 17 增量安装优化：streaming install for large APKs
- installd 的并发控制与调度优化
- 厂商定制安装优化路径：vivo Turbo、小米 HyperOS 的安装加速

### 🔹 锚点 5：安装性能的 Perfetto 分析方法
- installd 进程的 CPU 和 I/O 轨道
- dex2oat 编译轨道：编译滤镜、线程数、耗时
- PackageInstallerSession 的状态机跟踪
- 安装全链路的端到端耗时度量

## 扩展

### 🔸 扩展点 1：Staged Install 回滚机制
- 安装失败时的回滚策略
- Staged Rollback 与 GS1 (Guaranteed Rollback) 的关系

### 🔸 扩展点 2：多 APK / App Bundle 安装性能
- Split APK 安装路径与单 APK 的性能差异
- Asset Delivery 的安装延迟与用户感知

<!-- outline-end -->

> 本节内容待加工。
