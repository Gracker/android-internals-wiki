---
title: "Zygote 图形驱动预加载与启动性能"
chapter: "1.19"
status: draft
applicable_versions: "Android 12 (API 31) - Android 17 (API 37)"
tags: [zygote, app-startup, gpu-driver, graphics, preload]
related_chapters: ["1.11", "2.10", "8.2", "16.2"]
created_by: "task2a-knowledge-gap"
created_date: "2026-05-16"
gap_source: "素材驱动/AOSP结构"
material_paths:
  - "OpenClaw定时任务/AutoResearchClaw调研报告/2026-05-07-zygote-preloadappprocesshals-preloadgraphicsdriver.md"
  - "cs.android.com frameworks/base/core/java/com/android/internal/os/ZygoteInit.java"
  - "cs.android.com frameworks/base/core/jni/com_android_internal_os_ZygoteInit.cpp"
  - "cs.android.com frameworks/base/core/java/android/os/GraphicsEnvironment.java"
---

# 1.19 Zygote 图形驱动预加载与启动性能

<!-- outline-start -->
## 要点

### 🔹 为什么图形驱动预加载属于启动性能问题
从 App 冷启动、首帧提交、GPU driver 首次加载成本三个角度说明问题边界，区分 Zygote 通用 preload 与应用自己的初始化。

### 🔹 ZygoteInit.preload() 中的图形相关节点
梳理 `PreloadAppProcessHALs`、`PreloadGraphicsDriver`、`preloadSharedLibraries`、`WebViewFactory.prepareWebViewInZygote()` 的相对顺序，以及 Perfetto / log 中能看到的观察点。

### 🔹 nativePreloadAppProcessHALs() 的 HAL 选择原则
解释为什么当前优先覆盖大多数 App 进程都会触达、且适合在 fork 前预热的图形 HAL；说明不应把厂商私有 HAL 预加载推成通用结论。

### 🔹 maybePreloadGraphicsDriver() 与禁用开关
说明 `ro.zygote.disable_gl_preload` 的作用、适用场景和风险：预加载可以降低子进程首次图形调用成本，但驱动兼容问题可能影响 zygote 启动。

### 🔹 Updatable GPU Driver 与 GraphicsEnvironment
整理 system driver、updatable driver、ANGLE / game driver 选择路径，说明它们与 Zygote preload 的关系：preload 解决首次加载成本，driver selection 决定加载哪套库。

### 🔹 对 App 启动分析的影响
给出 trace 分析口径：如何区分 zygote 预热收益、App 首帧 GPU 初始化、SurfaceFlinger 合成等待和应用主线程初始化成本。

### 🔹 版本与设备边界
按 Android 12-17、AOSP main、OEM driver 包、SELinux / vendor 配置差异整理验证边界，避免把单一设备表现写成平台规律。

## 扩展

### 🔸 与 1.11 Zygote 机制的交叉引用
本节只展开图形驱动与 HAL 预加载，Zygote fork、preloaded-classes、资源预加载详见 1.11 节。

### 🔸 与 8.2 App 启动全流程的交叉引用
首帧阶段的实际观测、ApplicationStartInfo 与启动阶段归因放到 8.2 节引用，不在本节重复写启动全流程。

### 🔸 驱动预加载异常的排查入口
可补充 SELinux denial、driver package、vendor EGL / Vulkan 库加载失败时的日志与降级策略。

<!-- outline-end -->

> 本节内容待加工。
