---
title: "第 1 章：系统架构全景"
chapter: "1.0"
section: "1.0"
status: "finalized"
applicable_versions: "Android 8.0 (API 26) - Android 17 (API 37)"
last_verified: "2026-08-11"
last_verified_against: "AOSP android-17.0.0_r1; kernel android17-6.18-2026-06_r6; reviewed ch01 structure 1.1-1.29"
confidence: medium
sources:
  - type: repo
    path: "src/SUMMARY.md"
  - type: review
    path: "logs/external-review/archive/2026-04-22-21-1.0-external-review.md"
  - type: official
    path: "https://developer.android.com/about/versions/16/release-cycle"
tags: ['architecture', 'overview', 'chapter-intro']
related_chapters: ["1.1", "1.15", "1.9", "1.10", "1.21", "1.7"]
pipeline_stage: "ready-to-publish"
task2b_result: fixed
task2b_state: fixed
task6_state: reviewed
task9_state: "reviewed"
last_task2b_at: "2026-05-09T09:44:52"
reviewed_by: openclaw-task6
reviewed_date: "2026-05-08"
task6_result: "pass-light-edit"
task9_result: "pass-tech-review"
last_task9_at: "2026-05-14T18:30:00+08:00"
task9_reviewed_by: openclaw-task9
task9_reviewed_date: "2026-05-14"
last_task9_review_log: "logs/deep-review/2026-05-14-18-deep-review.md"
last_consolidated_at: '2026-08-24'
consolidation_note: 本轮逐篇审阅确认共 29 篇；合并稿按责任链保留，修正误并主题、标题契约与相邻文章边界，章内目标顺序与全书重编号已落地。
---

# 第 1 章：系统架构全景

这一章统一说明后续性能、稳定性和工具篇会涉及的系统层次。面对慢启动、ANR、安装失败或原生代码崩溃，工程师需要先确定代码运行在哪个进程、跨过哪些进程间通信（IPC）或应用二进制接口（ABI）边界、由谁调度，以及相关状态由用户态进程还是内核维护。

全章核对平台机制时使用 Android 17（API 37）的固定源码标签 `android-17.0.0_r1`。涉及 Binder、调度、cgroup 进程资源分组和 BPF 内核可编程机制的内容，统一按 `android17-6.18-2026-06_r6` 核对。Android 17 设备仍可能使用通用内核镜像（Generic Kernel Image，GKI）的较早受支持分支，因此书中的 6.18 结论用于核对公共内核源码，不代表每台升级设备都运行 6.18。

## 用五层视角定位问题

| 层次 | 常见载体 | 主要职责 | 排查时要问 |
|---|---|---|---|
| App 与 ART（Android 运行时） | UI 线程、业务线程、Binder 调用线程、垃圾回收（GC）/编译线程 | 组件生命周期、业务执行、字节码执行与编译 | 主线程在运行、等锁、等 IPC，还是未获调度 |
| 应用框架（Framework） | `system_server`（承载多数 Java 系统服务的进程）内的 ActivityManagerService（AMS）、WindowManagerService（WMS）、PackageManagerService（PMS）等 | 系统策略、组件调度、权限与全局状态 | 请求在哪个服务排队，服务端持有什么锁 |
| 原生服务 | SurfaceFlinger、AudioFlinger、installd、apexd 等 | 图形、音频、安装和底层系统能力 | 数据如何跨 Java 原生接口（JNI）、Binder 或共享内存，服务线程在做什么 |
| 硬件抽象层（HAL）与厂商实现 | AIDL/HIDL HAL、厂商守护进程、驱动的用户态接口 | 稳定硬件接口与厂商实现 | ABI 是否兼容，VINTF 清单是否匹配，动态链接器命名空间和 SELinux 策略是否允许这条路径 |
| Linux 内核 | Binder、调度器、内存、文件系统、驱动 | 线程调度、内存、IPC 传输、设备访问 | 线程为何睡眠或处于可运行状态（runnable，即已经就绪但还未获得 CPU），缓冲区、队列或设备是否成为限制 |

表中的 AIDL 和 HIDL 都用于定义 Android 组件之间的接口，HIDL 主要见于存量 HAL；VINTF 清单记录系统与厂商组件的兼容要求；SELinux 策略控制进程能够访问哪些服务和设备节点。

性能现象通常跨越两层以上。比如主线程卡在 `BinderProxy.transactNative()` 只给出调用方等待点；还要沿这次 Binder 事务（transaction）找到服务端线程，再检查它是在执行业务、等锁、等输入输出（I/O），还是尚未从目标进程队列取出。

## 内容索引


- [1.1 Android 分层架构、进程模型与线程协作](01-android-architecture-process-threading.md)
- [1.2 Android 版本演进中的架构变化](02-version-evolution.md)
- [1.3 系统启动、Zygote 与图形栈预加载](03-boot-zygote-graphics-preload.md)
- [1.4 Java 类加载与 ART Boot Image](04-class-loading-art-boot-image.md)
- [1.5 ART 编译、验证与去优化机制](05-art-compilation-verification-deoptimization.md)
- [1.6 JNI、NDK 与 Bionic 原生运行时性能](06-jni-ndk-bionic-performance.md)
- [1.7 Dynamic Linker、VNDK 与 Native 库隔离](07-dynamic-linker-vndk-isolation.md)
- [1.8 MessageQueue 与锁竞争：从 DeliQueue 到系统等待链](08-messagequeue-lock-contention.md)
- [1.9 Android IPC 全景与 Binder 性能](09-ipc-binder-performance.md)
- [1.10 Binder 线程池、异步事务与 Freezer](10-binder-scheduling-freezer-threadpool.md)
- [1.11 Binder 事务缓冲区与可观测性](11-binder-buffer-observability.md)
- [1.12 ActivityManager 组件调度、进程优先级与锁模型](12-activitymanager-process-lock-priority.md)
- [1.13 Android 17 cgroup v1/v2 混合层级与进程资源隔离机制](13-cgroup-v1-v2-process-isolation.md)
- [1.14 Android 17 BroadcastQueue 进程级调度与广播性能边界](14-broadcastqueue-scheduling-performance.md)
- [1.15 ContentProvider 性能与优化](15-content-provider.md)
- [1.16 应用分发、安装验证与 PackageManager 性能](16-package-distribution-install-verification.md)
- [1.17 应用归档（App Archiving）机制与恢复性能](17-app-archiving-performance.md)
- [1.18 ResourcesManager 与 Configuration 变更性能](18-resourcesmanager-configuration-performance.md)
- [1.19 Android 显示架构与 WindowManager](19-display-windowmanager-architecture.md)
- [1.20 音频链路（Audio Pipeline）延迟与性能](20-audio-pipeline-performance.md)
- [1.21 Telephony 服务架构、状态传播与回调](21-telephony-service.md)
- [1.22 Connectivity 服务、网络选择与回调](22-connectivity-service.md)
- [1.23 Android 17 NotificationManager 架构与性能优化](23-notificationmanager-architecture-performance.md)
- [1.24 Android 17 BiometricService 架构与性能优化](24-biometricservice-architecture-performance.md)
- [1.25 Android 17 LocationManager 架构与性能优化](25-locationmanager-architecture-performance.md)
- [1.26 Android 17 AVF 架构与 pKVM 隔离性能边界](26-virtualization-framework-pkvm-performance.md)
- [1.27 Android logd 日志系统性能与开销](27-logd-logging-system-performance.md)
- [1.28 Android 17 / ACK 6.18 BPF 可观测性与可编程边界](28-bpf-observability-boundary.md)
- [1.29 Android AI 手机技术栈：平台接口、端侧推理与协作边界](29-android-ai-phone-ecosystem.md)

## 按问题选择阅读路径

- 启动慢：`1.3 → 1.5 → 1.4 → 1.7`。
- 主线程卡顿或 ANR：`1.9 → 1.8 → 1.10 → 1.11`，并到服务端章节核对调用链。
- 安装、系统升级（OTA）或分阶段安装会话（staged session）：`1.16 → 1.17`。
- 配置变化导致重建：`1.18 → 1.19`。
- 原生库加载失败或启动开销：`1.6 → 1.7`。
- system_server 调度与进程优先级：`1.12 → 1.10 → 1.14 → 1.13`。

## 读源码时保留三条边界

同一 Android 版本不保证同一运行行为。应用面向的 SDK 版本（target SDK）、兼容性开关（compat change）、`aconfig` 功能开关、可独立更新的 Mainline 模块版本、厂商分支与设备内核都可能改变结果。正文中出现“Android 17 默认启用”时，应继续检查启用条件。

源码常量不等于性能承诺。Binder 缓冲区、线程数、超时或队列阈值只能解释实现范围，收益与风险仍要在目标设备、相同测试负载和相同构建上测量。

历史版本有助于解释设计变化，但 Android 17 结论必须回到 `android-17.0.0_r1` 与相应的固定内核版本。预览文档、旧源码标签和设备厂商（OEM）的私有实现都不能替代当前源码。

## 固定源码版本

- [AOSP android-17.0.0_r1](https://android.googlesource.com/platform/manifest/+/android-17.0.0_r1)
- [Android common kernel android17-6.18-2026-06_r6](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6)
- [Android 17 API 概览](https://developer.android.com/about/versions/17)
