---
title: "Memory Advice API 与游戏内存压力治理"
chapter: "23.10"
status: draft
applicable_versions: "AGDK / Jetpack 库版本相关 - Android 17 (API 37)"
tags: [memory-advice, agdk, game-memory, low-memory, native-memory]
related_chapters: ["8.9", "10.1", "10.4", "23.3", "23.7", "26.9"]
created_by: "task2a-knowledge-gap"
created_date: "2026-05-21"
gap_source: "官方文档/AOSP结构/每日信息"
sources:
  - type: official
    path: "https://developer.android.com/games/sdk/memory-advice/overview"
  - type: official
    path: "https://developer.android.com/games/sdk/memory-advice/start"
  - type: official
    path: "https://developer.android.com/games/optimize/memory-allocation"
  - type: official
    path: "https://developer.android.com/reference/games/memory-advice/namespacememory/advice"
---

# 23.10 Memory Advice API 与游戏内存压力治理

<!-- outline-start -->
## 要点

### 🔹 Memory Advice API 解决的问题
说明 Memory Advice API 面向游戏和图形重负载应用的定位：估算内存压力、给出状态通知、帮助应用在被系统杀进程前主动降级内存占用。

### 🔹 接入形态与版本边界
梳理 Jetpack 发行包、Android Game Development Kit、Unity 接入路径、原生 API 与 C/C++ 引擎的关系，明确它是库能力，不等同于新的 framework 系统服务。

### 🔹 MemoryState、可用内存与 watcher 回调
整理 `GetMemoryState()`、`GetAvailableMemory()`、`GetPercentageAvailableMemory()`、`RegisterWatcher()` 等接口的使用边界，以及回调线程、采样间隔和生命周期管理风险。

### 🔹 与 LMKD / ApplicationExitInfo / Android Vitals 的关系
解释 Memory Advice API 适合做运行时降级信号，LMKD 和 `ApplicationExitInfo` 负责事后归因，Android Vitals 负责线上质量聚合；三者不能互相替代。

### 🔹 游戏资产与图形内存降级策略
围绕纹理、mesh、音频缓存、关卡流式加载、对象池和 shader / pipeline cache（着色器与管线缓存），整理不同压力等级下可执行的释放和降级动作。

### 🔹 Perfetto 与 meminfo 验证方法
给出 `dumpsys meminfo`、Perfetto memory counter、heap profile、DMA-BUF / GPU memory 轨道和线上指标的复核路径，避免只看 API 状态就下结论。

## 扩展

### 🔸 Unity / Unreal 接入差异
记录 Unity 示例、Unreal 原生插件和自研引擎接入方式的差异，后续加工时补充官方示例和工程边界。

### 🔸 与 Android 17 App Memory Limits 的关系
对照 23.9 节的 Android 17 App Memory Limits，说明 Memory Advice API 在新系统内存限制下能提前暴露哪些信号。

### 🔸 线上灰度策略
补充把内存压力信号接入 A/B Test、功能开关和资源质量档位的策略，避免一次性对所有用户启用激进降级。

<!-- outline-end -->

> 本节内容待加工。
