---
title: "Package Manager Service 与应用安装性能"
chapter: "1.9"
section: "1.9"
status: draft
applicable_versions: "Android 10 (API 29) - Android 17 (API 37)"
tags: [PackageManager, dex2oat, installation, compilation, cloud-compilation, Baseline-Profiles, app-startup]
related_chapters: ["1.7", "1.8", "8.2", "8.3", "4.3"]
created_by: "task2a-knowledge-gap"
created_date: "2026-04-05"
gap_source: "AOSP结构+官方文档+研究素材"
---

# 1.9 Package Manager Service 与应用安装性能

<!-- outline-start -->
## 要点

### 🔹 锚点 1：PackageManagerService 在系统架构中的位置
- PMS 作为 system_server 中的核心服务之一
- 与 AMS、WMS 的协作关系：PMS 管理包信息，AMS 管理 Activity 生命周期
- 在系统启动流程中的启动时机（Boot Phase 100→480→1000）
- PMS 管理的数据结构：PackageSetting、PackageInfo、AndroidPackage

### 🔹 锚点 2：应用安装全流程与性能关键路径
- 安装触发路径：adb install / Google Play / PackageInstaller
- 安装阶段分解：copy → verify → dexopt → 签名验证 → 通知
- 每个阶段的耗时特征与瓶颈定位
- 安装过程中的 I/O、CPU、内存开销

### 🔹 锚点 3：dex2oat 编译对安装和启动性能的双重影响
- dex2oat 在安装流程中的触发时机与编译模式（verify/speed/profile/quicken）
- 编译模式的选择策略（系统预装 vs 用户安装 vs 更新）
- dex2oat 的资源消耗特征（CPU、内存、I/O）与并发控制
- 与 §1.7 ART 编译管线的交叉：安装时 dex2oat vs 后台 dexopt vs 运行时 JIT

### 🔹 锚点 4：Background Dexopt 策略与系统性能影响
- 后台 dexopt 的触发条件：充电 + 空闲 + 特定时间窗口
- JobScheduler 与 DexOptService 的协作
- dexopt 对前台应用的影响（I/O 竞争、CPU 争用）
- 在 Perfetto 中识别 dexopt 活动的方法
- 不同 Android 版本的 dexopt 策略演进

### 🔹 锚点 5：Baseline Profiles 与安装时优化
- Baseline Profiles 在安装流程中的角色：从安装即有 AOT 编译
- AGP 如何将 Baseline Profiles 打包进 APK
- 安装时 profile 引导的 dex2oat vs 运行时 JIT 收集的 profile
- Startup Profiles 子集对 DEX 布局的影响（AGP 8.3+）
- 量化数据：Baseline Profiles 对冷启动的提升幅度

### 🔹 锚点 6：Android 16 云端编译（Cloud Compilation）
- 云端编译的架构：APK + 预编译产物（Cloud DEX Metadata）一起分发
- 设备端 dex2oat 的减少或消除
- 对低端设备安装体验的改善
- 隐私与安全考量
- 与 Baseline Profiles 的关系：互补还是替代

### 🔹 锚点 7：应用更新与 OTA 更新的性能影响
- 应用更新时的增量编译 vs 全量编译
- 热更新 / 插件化方案对 PMS 的绕过与风险
- 系统 OTA 更新后 mass dexopt 的性能冲击
- Android 12+ 的 ART 模块化对 dexopt 策略的影响

### 🔹 锚点 8：在 Perfetto 中的表现与调试方法
- PMS 相关的 Track 和事件：dex2oat 进程、 installd 服务
- 安装耗时的分解分析方法
- 后台 dexopt 在 Trace 中的特征
- 常用的 adb 命令：pm compile、cmd package compile、dumpsys package

## 扩展

### 🔸 扩展点 1：多用户场景下的包管理性能
- 多用户共享 vs 用户独立包数据
- 用户切换时的 PMS 开销

### 🔸 扩展点 2：厂商定制对包管理的影响
- OEM 预装应用的优化策略（预编译、系统分区）
- 应用市场的自动更新策略对系统性能的影响

### 🔸 扩展点 3：installd 守护进程深入
- installd 的职责：dex2oat 调用、文件管理、权限控制
- installd 与 PMS 的 Binder 通信模型
- installd 的并发控制与资源限制

<!-- outline-end -->

> 本节内容待加工。
