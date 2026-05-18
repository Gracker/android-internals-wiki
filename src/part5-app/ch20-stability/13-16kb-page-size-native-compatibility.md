---
title: "16KB Page Size 兼容性与 Native 崩溃治理"
chapter: "20.13"
status: draft
applicable_versions: "Android 15 (API 35) - Android 17 (API 37)"
tags: [stability, native-crash, 16kb-page-size, ndk, elf]
related_chapters: ["4.7", "20.3", "20.11", "23.3", "25.6"]
created_by: "task2a-knowledge-gap"
created_date: "2026-05-18"
gap_source: "素材驱动/官方文档/AOSP结构/Clippings结构参考"
source_refs:
  - "[结构参考: Clippings/Android 应用稳定性剖析与优化 - ELF 文件与 readelf & objdump ：了解 ELF 格式与解析工具.md]"
  - "[结构参考: Clippings/Android 应用稳定性剖析与优化 - Native Crash 监控：为我们应用插上监控 Native Crash 的电子眼.md]"
  - "[结构参考: Clippings/Android 应用稳定性剖析与优化 - Native Hook 全解析：Native 闯关入门秘籍.md]"
  - "OpenClaw定时任务/AutoResearchClaw调研报告/2026-04-30-android-16kb-page-size-hook-library-compatibility.md"
  - "OpenClaw定时任务/AutoResearchClaw调研报告/2026-05-02-android-16kb-page-size-ndk-compatibility.md"
  - "DeepResearch/2026-05-08-16kb-page-size-third-party-library-impact.md"
  - "https://developer.android.com/guide/practices/page-sizes"
  - "https://source.android.com/docs/core/architecture/16kb-page-size/16kb"
  - "https://source.android.com/docs/core/architecture/16kb-page-size/16kb-backcompat-option"
---

# 20.13 16KB Page Size 兼容性与 Native 崩溃治理

<!-- outline-start -->
## 要点

### 🔹 16KB Page Size 在稳定性治理里的边界
把 16KB 页面问题限定在含 native 代码、预编译 `.so`、静态链接库和三方 SDK 的兼容性范围内；纯 Java/Kotlin 应用通常不需要处理 ELF 对齐，但仍要排查间接引入的 native 依赖。

### 🔹 ELF PT_LOAD 对齐与 Play 合规检查
说明 `p_align >= 16384`、`p_vaddr` / `p_offset` 同余关系、ZIP 对齐和 Play 预发布验证之间的关系，给出 `readelf`、APK Analyzer、CI 脚本各自适合检查的问题。

### 🔹 NDK、AGP 与链接器参数的升级路径
区分 AGP 8.5.1+、NDK r28+ 的默认兼容能力，以及旧工具链下 `-Wl,-z,max-page-size=16384`、`ANDROID_SUPPORT_FLEXIBLE_PAGE_SIZES=ON`、Prefab / React Native / 游戏引擎的参数传递风险。

### 🔹 NDK r27 WriteProtected 崩溃路径
梳理静态链接 `libc.a` 的 `WriteProtected` 旧实现如何在 16KB 设备上触发 `mprotect(..., 4096, ...)` 的 `EINVAL`，并把该类崩溃与普通 `SIGSEGV`、MTE 崩溃、业务 native 崩溃分开归因。

### 🔹 Hook、监控 SDK 与 legacy native 库分层排查
按风险把依赖分为三类：静态链接旧 NDK 的 legacy 库、参数无法传递的中间构建产物、已显式支持 16KB 的 Hook / 监控 SDK。排查重点放在构建产物和三方 SDK 版本，不把所有 native crash 都归到页大小。

### 🔹 线上崩溃识别与灰度兜底
设计崩溃聚合规则：设备页大小、ABI、NDK 版本、`UnsatisfiedLinkError`、`mprotect ... Invalid argument`、Play pre-launch 结果、三方 SDK 版本进入同一个证据包，用于灰度拦截和回滚判断。

### 🔹 兼容性验证流水线
建立从本地 16KB 模拟器/真机、CI ELF 扫描、Play pre-launch、灰度设备指标到线上告警的验证顺序，明确每一层能发现的问题和漏报边界。

## 扩展

### 🔸 bionic 16KB app compat mode 的安全代价
补充 `bionic.linker.16kb.app_compat.enabled` 的加载兜底、RELRO 保护退化和只作为过渡方案的使用条件。

### 🔸 React Native、Unity、Unreal 的 native 依赖清单化
记录跨平台框架中 `.so` 来源、Prefab 包、引擎插件和闭源 SDK 的清单化方法，避免只检查主工程 CMake 参数。

### 🔸 与 4.7 机制篇的交叉引用
本节只写应用治理动作；页大小、TLB、内核页表和系统侧性能收益详见 4.7 节。

<!-- outline-end -->

> 本节内容待加工。
