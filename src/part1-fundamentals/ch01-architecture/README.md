---
title: "第 1 章：系统架构全景"
chapter: "1.0"
section: "1.0"
status: "finalized"
applicable_versions: "Android 8.0 (API 26) - Android 17 (API 37)"
last_verified: "2026-05-08"
last_verified_against: "src/SUMMARY.md, 子节 1.7/1.9/1.10/1.13/1.14/1.16/1.17 applicable_versions, AOSP android-17.0.0_r1"
confidence: medium
sources:
  - type: repo
    path: "src/SUMMARY.md"
  - type: review
    path: "logs/external-review/archive/2026-04-22-21-1.0-external-review.md"
  - type: official
    path: "https://developer.android.com/about/versions/16/release-cycle"
tags: ['architecture', 'overview', 'chapter-intro']
related_chapters: ["1.1", "1.2", "1.3", "1.4", "1.5", "1.6", "1.7", "1.8", "1.9", "1.10", "1.11", "1.12", "1.13", "1.14", "1.16"]
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
---

# 第 1 章：系统架构全景

这一章为后续性能、稳定性和工具篇建立同一套系统坐标。面对一次慢启动、ANR、安装失败或 native 崩溃，工程师需要先确定代码运行在哪个进程、跨过哪些 IPC/ABI 边界、由谁调度，以及状态保存在用户态还是内核。

当前平台源码锚点是 Android 17 / API 37 / `android-17.0.0_r1`。涉及 Binder、调度、cgroup 和 BPF 的内核正文统一锚定 `android17-6.18-2026-06_r6`。Android 17 设备仍可能使用官方支持的较早 GKI 分支，因此书中的 6.18 结论用于源码核读，不代表每台升级设备都运行 6.18。

## 用五层视角定位问题

| 层次 | 常见载体 | 主要职责 | 排查时要问 |
|---|---|---|---|
| App 与 ART | UI 线程、业务线程、Binder caller、GC/编译线程 | 组件生命周期、业务执行、字节码执行与编译 | 主线程在运行、等锁、等 IPC，还是未获调度 |
| Framework | `system_server` 内的 AMS、WMS、PMS 等 | 系统策略、组件调度、权限与全局状态 | 请求在哪个服务排队，服务端持有什么锁 |
| Native 服务 | SurfaceFlinger、AudioFlinger、installd、apexd 等 | 图形、音频、安装和底层系统能力 | 数据如何跨 JNI/Binder/共享内存，服务线程在做什么 |
| HAL 与 vendor | AIDL/HIDL HAL、vendor daemon、驱动用户态接口 | 稳定硬件接口与厂商实现 | ABI、VINTF、linker namespace 和 SELinux 是否允许这条路径 |
| Kernel | Binder、scheduler、memory、filesystem、driver | 线程调度、内存、IPC 传输、设备访问 | 线程为何睡眠或 runnable，buffer/队列/设备是否成为限制 |

性能现象通常跨越两层以上。比如主线程卡在 `BinderProxy.transactNative()` 只给出调用方等待点；还要沿 transaction 找到服务端线程，再检查它是在执行业务、等锁、等 I/O，还是尚未从目标进程队列取出。

## 基础主线

按下面顺序阅读，可以先建立稳定的系统模型：

- [1.1 Android 分层架构](01-layered-architecture.md)：App、Framework、Native、HAL 与 Kernel 的职责边界。
- [1.2 系统启动全流程](02-boot-process.md)：Boot ROM、bootloader、kernel、init、Zygote 与 SystemServer 的启动分段。
- [1.3 进程模型与生命周期管理](03-process-model.md)：进程状态、缓存进程、OOM 调整与冻结边界。
- [1.4 Binder IPC 机制与性能影响](04-binder.md)：事务、线程、buffer、同步等待与错误传播。
- [1.5 线程模型](05-threading-model.md)：Looper、MessageQueue、线程池和调度状态。
- [1.6 Android 版本演进中的架构变化](06-version-evolution.md)：Treble、Mainline、GKI、VNDK 弃用、16 KiB page size 与 Android 17 行为。
- [1.7 ART 编译管线与 dex2oat 优化](07-art-compilation.md)：解释器、JIT、AOT、profile 和 dexopt filter。
- [1.8 Activity Manager Service 与性能分析](08-activity-manager.md)：组件调度、进程管理和前后台切换。
- [1.9 Package Manager Service 与应用安装性能](09-package-manager.md)：扫描、安装、session、归档和编译产物。
- [1.10 ContentProvider 性能与优化](10-content-provider.md)：跨进程数据访问、初始化与权限检查。
- [1.11 Zygote 机制与启动性能优化](11-zygote-startup.md)：预加载、fork 继承与启动共享成本。
- [1.12 AutoFDO 反馈导向编译优化](12-autofdo-optimization.md)：采样如何影响系统二进制布局。
- [1.13 MessageQueue 与 DeliQueue](13-messagequeue-deliqueue.md)：Android 17 无锁消息发布、Looper 私有堆与兼容开关。
- [1.14 锁竞争与同步性能分析](14-lock-contention.md)：monitor、futex、锁顺序和优先级反转。
- [1.15 JNI/NDK 性能优化](15-jni-ndk-performance.md)：Java/native 边界、引用、拷贝和线程附着。
- [1.16 Audio Pipeline 延迟与性能](16-audio-pipeline-performance.md)：FAST Mixer、AAudio、线程调度和设备约束。
- [1.17 IPC 全景](17-ipc-panorama.md)：Binder、socket、共享内存、FMQ 与 DMA-BUF 的选型边界。

## 系统行为专题

基础主线之后，可以按问题跳转：

- [1.18 Binder Freezer 与缓存进程冻结](18-binder-freezer-cached-process.md)
- [1.19 Zygote 图形栈预加载与首帧冷路径](19-zygote-graphics-driver-preload.md)
- [1.20 App Archiving 机制与恢复性能](20-app-archiving-performance.md)
- [1.21 Developer Verification 与安装链路](21-developer-verification-install-boundary.md)
- [1.22 ART Verifier、Quickening 与 dexopt filter](22-art-verifier-quickening-dexopt-filters.md)
- [1.23 Staged Install 与安装原子性](23-staged-install-performance.md)
- [1.24 ResourcesManager 与 Configuration](24-resourcesmanager-configuration-performance.md)
- [1.25 AMS 双锁与 system_server 竞争](25-ams-dual-lock-system-server-contention.md)

## Android 17 深入阅读

### MessageQueue 与 Binder

- [1.25 Binder async/oneway 流水线](01.25-binder-ipc-async-pipeline.md)
- [1.26 DeliQueue 源码解析](01.26-messagqueue-deliqueue-optimization.md)
- [1.30 Binder transaction buffer](30-binder-transaction-buffer-performance.md)
- [1.31 Binder 调试、冻结状态与事务录制](31-binder-performance-recording-trace.md)
- [1.32 Binder Perfetto 与内核快照](01.32-android17-binder-ipc-performance-monitoring.md)
- [1.38 Binder 线程池饥饿](38-binder-thread-pool-starvation-performance.md)
- [1.44 Binder 优先级继承与命令缓冲](1.44-binder-ipc-priority-inheritance.md)
- [1.54 Binder 线程池实现](1.54-binder-thread-pool-implementation/1.54-binder-thread-pool-implementation.md)

### Framework 与运行时

- [1.33 BroadcastQueue 调度](33-broadcastqueue-scheduling-performance.md)
- [1.34 OomAdjuster 与进程优先级](34-oomadjuster-process-priority-performance.md)
- [1.35 ART 去优化](35-art-deoptimization-performance.md)
- [1.36 Java 类加载](36-java-class-loading-performance.md)
- [1.37 logd 日志开销](37-logd-logging-system-performance.md)
- [1.45 Staged Install 状态机](1.45-staged-install-state-machine.md)
- [1.46 ResourcesManager 与 Configuration 派发](1.46-resourcesmanager-configuration-performance.md)
- [1.48 Activity relaunch 判定](1.48-Android-17-ResourcesManager-Configuration-Activity-Relaunch-判定模型.md)
- [1.49 Staged Install 提交与恢复](1.49-Android-17-Staged-Install-状态机-提交-恢复链路.md)

### Native、内核与系统服务

- [1.32 AVF 与 pKVM](32-virtualization-framework-pkvm-performance.md)
- [1.40 Bionic libc 性能边界](40-bionic-libc-performance.md)
- [1.55 VNDK 弃用与 linker namespace](1.55-android17-vndk-isolation-native-library-performance.md)
- [1.56 cgroup v1/v2 混合层级](56-android17-cgroup-v2-unified-hierarchy.md)
- [1.57 ART Boot Image 映射](57-android17-art-boot-image-memory-mapping-startup.md)
- [1.58 Dynamic Linker 与 native 库加载](58-android-dynamic-linker-linker64-native-library.md)
- [1.60 ACK 6.18 BPF 可观测性](1.60-linux-610-bpf-android17-boundary.md)
- 系统服务专题：[1.61 Telephony](1.61-android17-telephonymanager-architecture-performance.md)、[1.62 Connectivity](1.62-android17-connectivitymanager-architecture-performance.md)、[1.63 Notification](1.63-android17-notificationmanager-architecture-performance.md)、[1.64 Biometric](1.64-android17-bometricservice-architecture-performance.md)、[1.65 Location](1.65-android17-locationmanager-architecture-performance.md)、[1.66 Window](1.66-android17-windowmanager-architecture-performance.md)、[1.67 Package](1.67-android17-packagemanager-architecture-performance.md) 与 [1.68 Activity Manager](1.68-android17-activitymanager-architecture-performance.md)。

目录中还保留了部分 deprecated、重复编号和历史事实核查页。阅读主线以本页和 `SUMMARY.md` 给出的入口为准，不应按文件名判断内容的新旧。

## 按问题选择阅读路径

- 启动慢：`1.2 → 1.11 → 1.7 → 1.19 → 1.36 → 1.57`。
- 主线程卡顿或 ANR：`1.4 → 1.14 → 1.38 → 1.31`，并到服务端章节核对调用链。
- 安装、OTA 或 staged session：`1.9 → 1.21 → 1.23 → 1.45 → 1.49`。
- 配置变化导致重建：`1.24 → 1.46 → 1.48`。
- native 库加载失败或启动开销：`1.15 → 1.40 → 1.55 → 1.58`。
- system_server 调度与进程优先级：`1.8 → 1.25 → 1.33 → 1.34 → 1.68`。

## 读源码时保留三条边界

同一 Android 版本不保证同一运行行为。target SDK、compat change、aconfig flag、Mainline 模块版本、厂商分支与设备内核都可能改变结果。正文中出现“Android 17 默认启用”时，应继续检查启用条件。

源码常量不等于性能承诺。Binder buffer、线程数、超时或队列阈值只能解释实现边界，收益与风险仍要在目标设备、相同 workload 和相同构建上测量。

历史版本有助于解释设计迁移，但 Android 17 结论必须回到 `android-17.0.0_r1` 与相应内核锚点。预览文档、旧 tag 和 OEM 私有实现都不能替代当前源码。

## 源码锚点

- [AOSP android-17.0.0_r1](https://android.googlesource.com/platform/manifest/+/android-17.0.0_r1)
- [Android common kernel android17-6.18-2026-06_r6](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6)
- [Android 17 API 概览](https://developer.android.com/about/versions/17)
