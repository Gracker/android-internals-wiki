---
title: "ART Verifier Quickening 与 dexopt 过滤器性能边界"
chapter: "1.22"
section: "1.22"
status: draft
applicable_versions: "Android 8 (API 26) - Android 16 (API 36)"
tags: [art, dex2oat, dexopt, verifier, startup]
related_chapters: ["1.7", "1.9", "16.6", "21.11"]
created_by: "task2a-knowledge-gap"
created_date: "2026-05-24"
gap_source: "研究素材/官方文档/AOSP结构"
sources:
  - type: official
    path: "https://source.android.com/docs/core/runtime/configure"
  - type: official
    path: "https://source.android.com/docs/core/runtime/configure/art-service"
  - type: official
    path: "https://developer.android.com/guide/practices/verifying-apps-art"
  - type: aosp
    path: "https://android.googlesource.com/platform/art/+/main/dex2oat/"
  - type: research
    path: "intake/daily-info/2026-05-24.md#增量扫描-源码调研art-verifier-quickening-与-dex2oat-过滤器体系"
---

# 1.22 ART Verifier Quickening 与 dexopt 过滤器性能边界

<!-- outline-start -->
## 要点

### 🔹 Verifier 在安装、首次启动和后台编译中的位置
梳理 ART bytecode verifier、`dex2oat`、VDEX/OAT 产物和 PackageManager 安装流程的关系，明确哪些耗时属于安装期，哪些会转移到首次运行或后台 dexopt。

### 🔹 compiler filter 的执行成本和收益边界
按 `verify`、`quicken`、`speed-profile`、`speed` 拆分工作内容、产物形态、启动收益、存储成本和适用版本，避免把过滤器当成单纯的优化等级。

### 🔹 quickening 的版本边界
说明 `quicken` 在 Android 11 及以下的解释器优化语义，以及 Android 12 之后官方过滤器口径变化对旧文档、旧设备和厂商定制 ROM 的影响。

### 🔹 ART Service 接管 dexopt 后的场景拆分
覆盖 Android 14+ ART Service 在 first boot、OTA、mainline update、install、bg-dexopt、cmdline 下的默认策略，以及 `pm.dexopt.*` 系统属性的排障价值。

### 🔹 VDEX、verifier deps 与 class loader context
解释 VDEX 中验证结果和 quickening 信息的复用条件，关联 class loader context mismatch、`<uses-library>` 检查和 dexpreopt 产物失效后的降级路径。

### 🔹 性能排障中的证据采集
整理 `pm compile`、`pm bg-dexopt-job`、`dumpsys package dexopt`、logcat ART/dex2oat 日志和安装耗时拆分方法，用于区分 verifier、AOT 编译、profile 缺失和 CLC mismatch。

### 🔹 与启动优化和云端 Profile 的关系
把本节与 1.7 ART 编译管线、16.6 Android 16 云端 Profile、21.11 DM 文件安装后编译优化建立交叉引用，只补执行策略和排障动作，不重复讲 ART 总体架构。

## 扩展

### 🔸 旧设备 quicken 产物与现代 ART Service 的兼容排查
围绕 Android 8-11 旧设备和 Android 14+ 主线化 ART 做版本矩阵，记录验证、quickening、AOT 产物复用的差异。

### 🔸 dexopt 策略对大体积应用安装耗时的影响
结合 very-large dex 降级、profile 缺失和后台 dexopt 取消条件，形成大包安装后首启慢的排障清单。

<!-- outline-end -->

> 本节内容待加工。
