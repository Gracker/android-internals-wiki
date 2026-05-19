---
title: "SDK Runtime 与广告 SDK 启动隔离性能"
chapter: "21.10"
section: "21.10"
status: draft
applicable_versions: "Android 14 (API 34) - Android 17 (API 37)"
tags: [sdk-runtime, privacy-sandbox, startup, ads-sdk, ipc]
related_chapters: ["8.2", "21.1", "21.2", "21.6", "26.3"]
created_by: "task2a-knowledge-gap"
created_date: "2026-05-19"
gap_source: "官方文档/AOSP结构/每日信息"
gap_score: 16
material_count: 4
source_refs:
  - "https://developer.android.com/design-for-safety/privacy-sandbox/guides/sdk-runtime"
  - "https://developer.android.com/design-for-safety/privacy-sandbox/reference/sdksandbox/SdkSandboxManager"
  - "https://developer.android.com/jetpack/androidx/releases/privacysandbox-sdkruntime"
  - "intake/daily-info/2026-05-19.md"
---

# 21.10 SDK Runtime 与广告 SDK 启动隔离性能

<!-- outline-start -->
## 要点

### 🔹 SDK Runtime 解决的工程问题
从第三方广告 SDK 与宿主 App 同进程运行的启动、内存、隐私和治理问题切入，说明 Android 14 引入独立 SDK Runtime 的定位。

### 🔹 `SdkSandboxManager.loadSdk()` 的加载路径
梳理 App 通过 `SdkSandboxManager` 加载 runtime-enabled SDK、回调 `SandboxedSdk`、AIDL/IBinder 双向通信的基本流程。

### 🔹 启动耗时与首屏路径隔离
分析广告、归因、风控 SDK 初始化从 App 主进程迁移到 sandbox process 后，对 cold start、TTID/TTFD 和首屏任务编排的影响。

### 🔹 进程、Binder 与 SharedPreferences 同步成本
覆盖独立进程内存常驻、跨进程调用、参数序列化、SharedPreferences key 同步等性能成本，以及这些成本在 Trace 中的观测方式。

### 🔹 向低版本兼容的 Jetpack sdkruntime 路径
说明 AndroidX Privacy Sandbox SDK Runtime 对旧平台的兼容层职责，区分平台 SDK Runtime 与 Jetpack backport 的能力边界。

### 🔹 广告 SDK 接入的回退策略
整理运行时加载失败、sandbox 不可用、低版本设备、网络初始化失败时的 fallback 设计，避免把 SDK 加载放回关键首帧路径。

## 扩展

### 🔸 与启动框架任务编排的关系
把 SDK Runtime 加载纳入启动 DAG，区分首帧前必须完成、首帧后异步、用户触达前预热三类任务。

### 🔸 与隐私沙盒 Attribution Reporting / Topics 的边界
说明 SDK Runtime 是第三方 SDK 运行隔离能力，不等同于广告归因、Topics 或 Protected Audience API。

### 🔸 Trace 与线上指标设计
补充用 Perfetto、Macrobenchmark、FrameMetrics、APM 事件打点观察 SDK 加载耗时、sandbox 进程内存和 IPC 频率的指标口径。

<!-- outline-end -->

> 本节内容待加工。
