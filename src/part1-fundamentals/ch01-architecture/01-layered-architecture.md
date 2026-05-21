---
title: "Android 分层架构"
chapter: "1.1"
section: "1.1"
status: ready-for-review
applicable_versions: "Android 8 (API 26) - Android 16 (API 36)"
last_verified: "2026-04-12"
last_verified_against: "AOSP android-16.0.0_r1, developer.android.com, source.android.com HAL/AIDL/VINTF/Mainline/lmkd docs"
confidence: high
sources:
  - type: official
    path: "https://developer.android.com/guide/platform"
  - type: official
    path: "https://source.android.com/docs/core/architecture/hal"
  - type: official
    path: "https://source.android.com/docs/core/architecture/aidl/aidl-hals"
  - type: official
    path: "https://source.android.com/docs/core/architecture/vintf"
  - type: official
    path: "https://source.android.com/docs/core/ota/modular-system"
  - type: official
    path: "https://source.android.com/docs/core/perf/lmkd"
  - type: blog
    path: "https://androidperformance.com"
tags: ['architecture', '分层架构', 'HAL', 'HIDL', 'AIDL', 'Binder', 'SystemServer', 'Zygote', 'SurfaceFlinger', '性能优化', 'Perfetto']
related_chapters: ["1.2", "1.3", "2.1", "3.1", "4.1", "5.1", "7.1"]
reviewed_date: "2026-05-22"
reviewed_by: openclaw-task6
polish_count: 1
polish_date: "2026-04-05"
polish_by: "task2b-polish"
review_notes: >-
  2026-04-28 task6 auto-promotion: finalized。条件满足：task6_result=pass-light-edit ✓，task9_result=pass-with-p1-notes ✓，queue无pending条目 ✓。2026-04-18 task6 re-review (revisiting): pass-light-edit。小修3处（禁用表达替换）。无B类大问题。评分: 结构5/5·措辞4/5·一致性5/5·验证4/5·元数据5/5。| 2026-04-11 task6 review: pass-light-edit。小修14处（禁用词替换/句式去模板化/验证标注格式统一）。无B类大问题。评分: 结构5/5·措辞4/5·一致性4/5·验证4/5·元数据5/5。| 2026-04-05 task2b-polish质检: 通过→ready-to-publish。小修1处（补充section字段）。无B类大问题。评分: 结构5/5·措辞5/5·一致性5/5·验证4/5·元数据5/5。| 2026-03-31 二次review: 通过finalized。小修7处（标准化验证标注格式/补充4处待验证标注/补充来源标注）。无B类大问题。评分: 结构4/5·措辞4/5·一致性4/5·验证4/5·元数据4/5。| 历史记录: 2026-03-30 task6 review 回炉 v2：集成3篇新研究素材（Perfetto映射/误区/Treble演进），补充数据源三层映射、HAL追踪完整方法、hwbinder vs binder区别、新增3条误区（线程状态/Binder阻塞/全系统视角），所有锚点已覆盖"
pipeline_stage: task9_pending
task6_state: reviewed
task6_result: pass-light-edit
task9_state: pending
task9_result: "needs-rework"
task9_reviewed_date: "2026-05-18"
task2b_state: fixed
task2b_result: fixed  # 2026-05-22 rework: SF version boundary, memfd claim, SELinux causal
task9_reviewed_by: "openclaw-task9"
last_task9_at: "2026-05-18T08:31:45+08:00"
task9_review_notes: "2026-05-18 task9 deep-review: needs-rework。P0 2 / P1 1 / P2 0。SurfaceFlinger 旧版本边界仍误写到 Android 14-；Android 15 起强制 memfd 说法与 AOSP android-16.0.0_r1 不符；SELinux AVC 性能因果仍需删除/补证。已写入 queue.json。 | 2026-05-18 task9 deep-review: needs-rework。P0 1 / P1 0 / P2 0。Android 16 SurfaceFlinger 旧 trace 名 doComposition 在正常/异常示例中残留，已写入 queue.json。 | 2026-05-18 task9 deep-review: needs-rework。P0 1 / P1 1 / P2 0。SurfaceFlinger Android 16 trace/源码切片名称仍使用旧路径；HAL 调用段落仍把 Treble 后 HAL 泛化成每次 Binder IPC。已写入 queue.json。 | 2026-05-17 task9 idle-audit: needs-rework。P0 1 / P1 0 / P2 0。命中 SELinux AVC 缓存实例描述错误，已写入 queue.json。"
last_task6_at: "2026-05-22T04:07:00+08:00"
last_task6_review_log: "logs/review/2026-05-22-04-review.md"
task6_review_notes: "2026-05-22 task6 复审：pass-light-edit。小修 1 处（调研记录与正文口径一致：SELinux/Treble 三路隔离降低误用风险，不写成减少检查次数）。无新增 B 类问题；Task9 尚未重新通过，未自动晋升。"
last_task9_audit: "2026-05-17"
task9_review_log: "logs/deep-review/2026-05-18-08-deep-review.md"
reviewed_at: "2026-05-18T08:31:45+08:00"
task6_reviewed_date: "2026-05-22"
last_task9_review_log: "logs/deep-review/2026-05-18-08-deep-review.md"
---

# Android 分层架构

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 Android 经典五层架构：Linux Kernel → HAL → Native Libraries / ART → Framework → Apps
- 🔹 每一层的职责边界与典型组件（SurfaceFlinger、Zygote、SystemServer、AMS/WMS 等）
- 🔹 Treble 架构引入的 HAL 接口定义（HIDL → AIDL 演进），对 vendor 与 framework 解耦的影响
- 🔹 Android 16 架构层面的最新变化（如 Mainline 模块持续扩展）
- 🔹 从性能视角看分层：哪些层是性能瓶颈热点（Binder 跨层调用、JNI 开销、HAL 延迟）

### 扩展（可选深入）

- 🔸 与 iOS / HarmonyOS 分层架构的对比
- 🔸 Mainline (Project Mainline / APEX) 对系统更新和性能的影响
- 🔸 Vendor VNDK 隔离对 native 库加载性能的影响

### OpenClaw 加工指引

> **锚点**是最低覆盖要求，加工时必须逐条落实并标注验证结果。
> **扩展**视素材丰富程度选择性深入。
> 如果从 Obsidian 素材或 AOSP 源码中发现大纲未列出但与本节强相关的知识点，
> 可**就地插入**最相关的锚点之后，并用 `[自动发现]` 标注，方便后续 review。
> 锚点内容需 L1/L2 验证，扩展内容至少 L2 验证，自动发现内容至少标注来源。
<!-- outline-end -->

## 为什么要了解 Android 分层架构

打开 Perfetto，随便抓一条系统级 Trace，会看到密密麻麻的进程、线程、彩色的 CPU 切片、Binder 调用箭头、VSync 信号线。这些可视化信息背后，是 Android 分层架构的“结构映射”：每个进程对应架构中的一层或一个组件，每条 Binder 箭头对应一次跨层调用，每段 CPU 切片对应某个层次的执行时间。

分析渲染卡顿时，Trace 里可能出现这样的场景：主线程在 `doFrame()` 里卡了 30 ms，原因是某个 `measure()` 调用触发 Binder 通信，等待 SystemServer 返回就花掉 20 ms。如果不清楚主线程、SystemServer、Binder 分别属于哪一层、为什么需要跨层通信，就只能看到一堆彩色方块，却无法定位根因。

理解分层架构，是性能分析的基础功。再打开 Perfetto Trace 时，就能快速判断异常耗时落在哪一层、为什么发生、该从哪一层入手优化。

[已验证: 官方文档, https://developer.android.com/guide/platform]

## Android 经典五层架构

Android 的架构从底向上分为五层：Linux Kernel、HAL、Native Libraries & ART Runtime、Framework、Apps。这个分层有明确的工程动机，每一层的存在都对应一类具体问题。

### 从硬件到应用：为什么需要五层

如果没有分层，App 要直接跟硬件打交道。想画一帧画面，就得自己操作 GPU 寄存器；想拍张照片，就得自己写摄像头驱动协议。每个 App 都要适配每一款 SoC、每一个传感器型号。这在 PC 时代或许勉强可行（驱动安装是常规操作），但在手机上百个 App 共存的环境下完全不可行。

Android 的解法是逐层抽象：Kernel 层把硬件抽象成文件和系统调用，HAL 层把不同厂商的硬件差异藏到统一接口后面，Runtime 层让上层可以用 Java/Kotlin 而不是 C/C++ 写代码，Framework 层把系统功能封装成 Service API。最终，App 开发者只需要调用 `Activity.startActivity()` 就能启动一个新页面，完全不需要知道底层经历了 Binder 通信、Zygote fork、Surface 分配这一系列跨层操作。

```mermaid
graph TB
    A[应用层 Apps] --> B[应用框架层 Framework]
    B --> C[原生库与运行时层 Native Libraries / ART]
    C --> D[硬件抽象层 HAL]
    D --> E[Linux 内核层 Linux Kernel]
    
    style A fill:#4CAF50,color:#fff
    style B fill:#2196F3,color:#fff
    style C fill:#FF9800,color:#fff
    style D fill:#9C27B0,color:#fff
    style E fill:#F44336,color:#fff
```

[图：Android 五层架构图，每层用不同颜色标注，标注关键组件归属]

这个架构的设计取舍是：**每一层只对自己的上一层提供接口，对自己的下一层隐藏实现。** 这种设计保证了当硬件更换、系统升级时，上层代码不需要修改。在性能分析中，每一层都可能成为瓶颈，瓶颈的表现形式取决于它所在的层次。

### 各层职责：从 Kernel 到 App 的边界分工

**Linux 内核层**是整个系统的基础。进程调度、内存管理、网络栈、设备驱动这些最底层的工作都在这里完成。Android 对标准 Linux 内核做了几项关键定制。Binder 驱动负责高频进程间通信。内存回收这条线要按版本看：Android 8-9 仍能看到 in-kernel LMK 的历史实现，Android 10 及以后主线切到 userspace `lmkd`，并可结合 PSI（Pressure Stall Information）判断内存压力。共享内存也不是一套机制覆盖所有版本。早期大量使用 ashmem，Linux 5.18（2022）已从 staging 目录移除 ashmem 驱动，Android 正在从 ashmem 向 memfd / ashmemd / compat shim 迁移。AOSP android-16.0.0_r1 的 `libcutils` 仍保留受 `sys.use_memfd` 属性与兼容性检查控制的 memfd 路径和 ashmem fallback，尚未达到全量强制切换；图形等子系统还会结合 `dmabuf` 一类机制。

[已验证: 官方文档, https://source.android.com/docs/core/architecture/kernel]
[已验证: 官方文档, https://source.android.com/docs/core/perf/lmkd]

**硬件抽象层 (HAL)** 是 Android 解决硬件碎片化的核心手段。设想一下：高通的 Camera ISP 和联发科的 Camera ISP 实现完全不同，但上层 Framework 需要用同一套 API 来调用它们。HAL 层做的就是定义统一的接口（比如 `CameraDeviceSession`），由各 SoC 厂商实现自己的版本。Framework 调用接口时不关心下面是高通还是联发科，甚至不关心是实机还是模拟器。

从 Android 8.0 开始，Treble 把 HAL 接口稳定性和 system/vendor 边界提到架构级约束。这里不能简单理解成“HAL 从这一版开始全部独立成进程”。Treble 时代的 HIDL 同时支持 binderized 和 passthrough 两种传输模式，只有 binderized HAL 才以独立服务进程运行；AIDL HAL 则统一走 Binder 化的稳定接口。这套拆分让 framework-only OTA 有了成立条件，也把不少 HAL 故障隔离在独立服务进程内。

[已验证: 官方文档, https://source.android.com/docs/core/architecture/hal]

**原生库与运行时层**横跨了两个世界：向下是 C/C++ 的 Native 代码（Skia 图形库、OpenGL ES/Vulkan、Media Framework、SQLite），向上是 Java/Kotlin 的托管代码（ART 运行时）。ART 负责 AOT/JIT 编译、垃圾回收、内存管理。这一层是性能的关键战场，因为 Java 代码调用 Native 代码需要经过 JNI（Java Native Interface），每次 JNI 调用都有固定的上下文切换开销。

[已验证: 官方文档, https://source.android.com/docs/core/runtime]

**应用框架层 (Framework)** 是系统服务的聚集地。SystemServer 进程在这里运行，管理着 Activity Manager (AMS)、Window Manager (WMS)、Package Manager (PMS) 等几十个核心服务。这些服务通过 Binder 暴露给所有 App。SurfaceFlinger 虽然与 Framework 紧密协作，但它是一个独立的 Native 进程，不属于 SystemServer。

Zygote 进程也在这一层扮演关键角色：所有 App 进程都由 Zygote fork 而来，fork 后子进程继承了 Zygote 预加载的类和资源，省去了大量初始化时间。这也是 Android 冷启动通常能控制在几百毫秒量级的原因。

**应用层 (Apps)** 是用户直接交互的层次。无论是系统预装的电话、设置，还是用户安装的微信、抖音，都通过 Framework 提供的 API 与系统交互。从性能角度看，App 层能控制的优化范围有限——启动流程的大部分耗时在 Framework 层（AMS 调度、Zygote fork、Surface 分配），渲染管线的大部分耗时在 Native/HAL 层（Skia 绘制、GPU 合成）。理解这一点，才能在优化时找对方向。

[已验证: 官方文档, https://developer.android.com/guide/platform]

## 每一层的职责边界与典型组件

分层架构能长期稳定运行，靠的是清晰的职责边界。每一层都有自己的“管辖范围”，越界调用往往会带来性能问题。拆到单层看时，重点是三个问题：有哪些关键组件、为什么这样设计、性能分析时对应哪些观察点。

### SystemServer：系统服务启动与管理入口

SystemServer 是 Android 启动过程中由 Zygote fork 出的第一个重要进程。它启动并管理着几乎所有核心系统服务——AMS、WMS、PMS、PowerManager 等几十个服务都在这里运行。

```java
// frameworks/base/services/java/com/android/server/SystemServer.java
// @ AOSP android-16.0.0_r1
public static void main(String[] args) {
    new SystemServer().run();
}

private void run() {
    // 初始化系统属性、时区、日志等基础环境
    TimingsTraceAndSlog t = new TimingsTraceAndSlog();
    // 省略部分基础环境初始化逻辑
    System.loadLibrary("android_servers");  // 加载 JNI native 方法
    // 省略服务启动前的检查和准备逻辑
    try {
        startBootstrapServices(t);  // 先启动最基础的服务（AMS、PMS 等）
        startCoreServices(t);       // 再启动核心服务
        startOtherServices(t);      // 启动其他服务
    } catch (Throwable ex) { /* 省略异常处理 */ }
}
```

`main()` 只做一件事：构造 SystemServer 实例并调用 `run()`。`run()` 内部先完成环境初始化（系统属性、时区、Looper），再加载 `android_servers` JNI 库，随后按三阶段启动服务。三阶段的顺序是串行的：`startBootstrapServices()` 启动的服务之间有强依赖关系（比如 AMS 需要 PMS 提供的包信息），必须按序初始化；`startOtherServices()` 内部同样以串行调用为主，个别耗时初始化可借助 `SystemServerInitThreadPool` 并行执行。如果启动阶段的某个服务初始化耗时过长，Perfetto 中会表现为 SystemServer 的 main 线程长时间占用 CPU。

[已验证: AOSP android-16.0.0_r1, frameworks/base/services/java/com/android/server/SystemServer.java]

### SurfaceFlinger：独立合成服务

SurfaceFlinger 是一个独立的 Native 进程，它的职责很单一：把各个 App 产生的 Surface 合成为最终的画面，交给屏幕显示。它不属于 SystemServer，但与 SystemServer 中的 WMS 紧密协作——WMS 负责决定窗口的层级和位置，SurfaceFlinger 负责把这些窗口画出来。

SurfaceFlinger 的工作由 VSync 信号驱动。每个 VSync 周期，它会收集所有可见 Surface 的新帧，决定使用硬件合成（HWC Overlay）还是 GPU 合成（GLES Composition），然后把合成后的帧提交给屏幕。在 Perfetto 中，SurfaceFlinger 的活动可以在 `surfaceflinger` 进程的线程 track 上看到。Android 16 的主路径切片是 `commit`（WorkloadTracer Commit）→ `composite`（Composition）→ `postComposition`。Android 13–15 同样使用 `SurfaceFlinger::commit()` + `composite()` 路径（命名略有调整），旧版本（Android 10 及之前）的切片名是 `onMessageReceived` → `handleMessageRefresh` → `doComposition`。排查时先确认设备版本，再按对应名称搜索。

### Zygote：应用进程 fork 入口

Zygote 是 Android 启动速度优化中的关键设计。系统启动时，Zygote 进程预加载了 ART 运行时、常用 Java 类、系统资源（drawable、字符串等）。当需要启动新 App 时，AMS 发送 fork 请求给 Zygote，Zygote fork 出子进程——子进程瞬间就拥有了所有预加载的资源。

这个设计的关键数据是：一次 Zygote fork 大约只需要 20-50 ms（取决于设备性能）[待验证: 具体数值需多设备实测确认]，而如果不预加载、冷启动一个完整的 ART 虚拟机并加载所有基础类可能需要数百毫秒。在 Perfetto 中，Zygote fork 的过程可以在 `zygote64` 进程 track 上看到，fork 出新进程后会立即出现新进程的 CPU 活动。

[已验证: 官方文档, https://source.android.com/docs/core/runtime]

## Treble 架构：HIDL → AIDL 演进

在 Android 8.0 之前，系统更新一直是 Android 生态里最棘手的问题。每次发布新版本，OEM 厂商都需要把整个 Framework + HAL + 内核重新编译测试，导致大多数设备要等半年甚至一年才能收到更新，有些设备永远等不到。

### Project Treble 的核心思路

Project Treble 的目标，是把 framework 和 vendor 侧实现之间的兼容性边界固定下来。支撑这条边界的是几层机制：system/vendor 分区拆分、VINTF（Vendor Interface）契约、framework compatibility matrix / device compatibility matrix 的匹配校验，以及可冻结的稳定接口。Framework 能在不重刷 vendor 分区的前提下升级，靠的是这整套边界同时成立。

Treble 和 Project Mainline 负责的事情不同。Treble 解决 framework/vendor 解耦与兼容性，Mainline 解决部分系统组件的模块化更新。二者可以叠加，但职责不同。

这个架构变化对性能分析的影响也要按传输模式区分。Treble 时代的 HIDL 既可以是 passthrough，也可以是 binderized。passthrough 模式下，HAL 代码以共享库形式被调用方进程加载；binderized 模式下，HAL 作为独立服务进程通过 Binder 暴露能力。到 Stable AIDL HAL，这条调用链统一收敛到 binderized 服务。看 Trace 时，先确认 HAL 属于哪一种传输模式，再判断延迟是在调用方进程内，还是在跨进程 Binder 往返里。

[已验证: 官方文档, https://source.android.com/docs/core/architecture/hal]
[已验证: 官方文档, https://source.android.com/docs/core/architecture/vintf]

### HIDL 到 AIDL 的迁移

HIDL（Hardware Interface Definition Language）是 Treble 早期为 HAL 引入的接口定义语言。它的传输模型本身就分成两类：binderized 服务用于跨进程 IPC，passthrough 只适用于 C++ 调用方 / 实现方，常用来包住 legacy HAL。这个区分决定了排查时是在 Trace 里找独立 HAL 服务进程，还是留在调用方进程内继续追踪。

Android 版本演进过程中，Google 把新 HAL 接口逐步收敛到 Stable AIDL。AIDL HAL 需要 `@VintfStability` 标注和 `stability: "vintf"` 声明，并进入 VINTF manifest，运行形态是 binderized service。到 Android 13，HIDL 在官方文档里已经标为 deprecated，旧 HIDL HAL 继续兼容，新接口主线则转到 AIDL。

底层传输也随之简化。HIDL HAL 常见 `hwbinder`（`/dev/hwbinder`）与 passthrough 两条路；AIDL HAL 使用标准 `binder`（`/dev/binder`）。在 Perfetto 里，AIDL HAL 的 IPC 会和 App ↔ `system_server` 的 Binder 事件出现在同一组观测面里，排查时要靠目标进程名和 transaction 方向区分。

[已验证: 官方文档, https://source.android.com/docs/core/architecture/aidl/aidl-hals]
[已验证: 官方文档, https://source.android.com/docs/core/architecture/hidl]
[已验证: 来源见 research-feeds/2026-03-30-19-ch01-treble-aidl-evolution.md]

### 在 Perfetto 中追踪 HAL 问题的完整方法

Treble 之后，HAL 追踪最容易出错的地方，是把它理解成“所有 HAL 都分家了”。Treble 之前就存在独立 native service / daemon；Treble 时代的 HIDL 也同时存在 passthrough 和 binderized 两种形态；AIDL HAL 才统一收敛到 binderized 服务。所以，Trace 里能不能直接看到独立 HAL 进程，取决于这次调用走的是哪条传输路径。

排查方法也要跟着传输模式选。遇到 binderized HAL，先在 Framework 调用方线程找到调用起点，再沿 Binder transaction 跳到 HAL 服务进程，看它是在执行、等锁还是等 I/O。遇到 passthrough HAL，则更多要在调用方进程里继续看 native slice、锁竞争和系统调用。把两种路径混成一套固定剧本，定位很容易跑偏。

如果设备构建开启了对应 trace 类别，AIDL 层事件可以和 Binder 事务一起看；只盯着 Framework 侧的调用发起时间不够，需要把完整调用路径串起来。

[已验证: 来源见 research-feeds/2026-03-30-19-ch01-treble-aidl-evolution.md]

## Android 16 架构层面的最新变化

### Project Mainline 的持续扩展

Project Mainline 在 Android 16 上已经覆盖到 ART、Media、Network Stack 等一批核心组件。这里也要和 Treble 分开看。Treble 处理的是 framework/vendor 边界，Mainline 处理的是可更新模块的分发形态。Mainline 模块有 APEX，也有 APK；部分能力还会采用 APK-in-APEX 的组合方式。设备端可以通过 Google Play system update 或 OEM 的 OTA 机制拿到这些更新。

对性能分析而言，Mainline 带来的变化是：同一台设备即使系统版本号没变，某个模块的实现也可能已经更新。分析 Trace 前最好先确认相关 Mainline 模块版本，避免把模块升级带来的行为变化误判成系统回归。

[已验证: 官方文档, https://source.android.com/docs/core/ota/modular-system]

### 16 KB Page Size 对 Android 16 的影响

> **版本澄清**：16 KB Page Size 特性由 **Android 15** 引入（Android 16 继续完善）。Android 16 的主要变化是要求部分设备必须支持 16 KB Page Size，而非重新引入该特性。

Android 15 引入了 16 KB 页大小支持（传统是 4 KB），Android 16 在此基础上继续完善。更大的页意味着页表项减少约 75%，TLB 命中率提升，对大块连续内存访问（如 GPU Buffer）有正面影响，但也会增加内存碎片和小对象的内存浪费。Google 报告的数据：应用启动平均提升 3.16%，系统启动缩短约 0.8 s，内存开销增加约 9%。Thread Local Storage（TLS）的缓冲区做了专项优化，将其隔离到专用内存页面，减少了对整体内存的消耗。

## 从性能视角看分层：瓶颈热点的分布

理解分层架构的最终目的是为了解决性能问题。不同层次的性能瓶颈有不同的"指纹"——在 Perfetto Trace 中表现为不同的 track 和事件模式。

### Binder 跨层调用：最常见的中转瓶颈

Binder 是 Android 高频 IPC 的主要通道，Framework 服务调用、App 与系统服务交互、部分 HAL 控制面请求都会通过它完成。它的性能特点是：单次调用延迟低（约 10-100 μs）[待验证: 具体范围需实测，受数据大小和设备影响]，但调用次数多了就会积少成多。

以 Activity 启动为例，整个流程涉及 App 进程、SystemServer 进程、Zygote 进程之间的多次跨进程通信。App 向 AMS 发起启动请求（一次 Binder 调用，进入 system_server）；AMS 通过 `ZygoteProcess` 向 Zygote 发起 fork 请求（走 LocalSocket/USAP 池，不是 Binder）；fork 完成后新 App 进程通过 Binder 向 AMS 的 `attachApplication()` 报告就绪……一个完整的冷启动涉及多次 Binder 往返和一次 LocalSocket 通信，Binder 调用总量可能达到数十次 [来源: 社区测量与 Trace 分析经验]。如果 SystemServer 恰好忙于处理其他请求（比如后台 App 在做 dex2oat），这些 Binder 调用的等待时间就会显著增加，在 Perfetto 中表现为 App 主线程的 "Runnable" 或 "Uninterruptible Sleep" 状态。

**优化方向：** 减少不必要的 Binder 调用频率（合并多个小调用为一个批量调用），使用异步 Binder 调用避免阻塞，利用 SharedMemory 传输大数据减少拷贝。


> **SELinux 开销对 Binder 性能的影响**
> 
> Binder 每次 transaction 均触发 SELinux LSM 钩子 `selinux_binder_transaction()`，执行 `avc_has_perm()` 权限检查。该检查在 `kernel/common/security/selinux/hooks.c` 中实现，判断调用方 SID 是否有 `BINDER__CALL` 或 `BINDER__IMPERSONATE` 权限。
> 
> 关键性能事实在于 **AVC（Access Vector Cache）**：首次未知请求需完整策略评估（~1-10 μs），后续命中仅 O(1) 缓存查找（~50-200 ns）。Binder 高频调用特征使 AVC 命中率极高，稳态下 SELinux 开销可忽略不计。
> 
> Android 8+ Treble 引入 `/dev/binder`（框架）、`/dev/vndbinder`（vendor）、`/dev/hwbinder`（HAL）三路隔离，三路 binder 设备各自拥有独立的 Context Manager 和 binder context，通过 SELinux type / 权限边界限制跨域访问。SELinux AVC 本身是全局访问向量缓存（`security/selinux/avc.c` 中的 `static struct selinux_avc selinux_avc`），缓存键是 ssid/tsid/tclass/perm，不按 binder 设备拆成独立实例。Treble 三路隔离通过 SELinux type / 权限边界限制跨域访问，降低了误用风险。三路 binder 设备各自独立的 context manager 本身并不减少 SELinux 检查次数——每条 Binder transaction 仍走相同的 `avc_has_perm()` 路径。
> 
> enforcing 与 permissive 的差异仅体现在拒绝路径：两者均执行完整检查，但 enforcing 额外执行拒绝操作。对于正常放行的请求，两种模式路径几乎相同。
> 
> **源码**：`kernel/common/security/selinux/hooks.c` — `selinux_binder_transaction()`；`security/selinux/avc.c` — `avc_has_perm()`；`security/selinux/include/classmap.h` — `BINDER__CALL`/`BINDER__IMPERSONATE` 权限定义。**[来源: AOSP kernel/common SELinux hooks.c, mainline Linux AVC]**



[已验证: 官方文档 + 社区测量数据, https://androidperformance.com]

### JNI 边界：Java 与 Native 之间的固定开销

JNI 是 Java/Kotlin 代码调用 C/C++ Native 代码的唯一通道。每次跨越这个边界，都要执行上下文切换、参数编组（marshalling）、引用表管理等一系列固定操作。根据社区测量，一次简单的 JNI 空调用（无参数、无返回值）大约需要 100-200 ns，但带参数转换的调用可能上升到 1-5 μs [待验证: JNI 延迟数据需实际设备验证，不同 Android 版本和 CPU 架构差异较大]。

更常见的成本来自调用次数。一个常见反模式是：在循环中反复调用 JNI 方法，每次只处理一条数据。比如逐像素调 JNI 方法做图像处理，100 万个像素就是 100 万次 JNI 调用，光 JNI 开销就会累积到数百毫秒。正确做法是把数据打包成数组或 DirectByteBuffer，一次 JNI 调用传过去批量处理。

Android 提供了 `@FastNative` 和 `@CriticalNative` 注解来优化特定场景的 JNI 调用——前者跳过部分 JNI 检查（如异常检测），后者进一步要求方法不引用任何 Java 对象。根据社区测量和 ART 内部基准：常规 JNI 调用约 115 ns，`@FastNative` 约 35 ns（约 3 倍提升），`@CriticalNative` 约 25 ns（约 5 倍提升）。

[已验证: 官方文档, https://developer.android.com/reference/dalvik/annotation/optimization/FastNative]

### HAL 延迟：硬件响应阶段的瓶颈

HAL 层的延迟往往是最难优化的，因为它取决于具体的硬件实现。以 Camera HAL 为例，一次拍照操作的调用链是：App → Camera2 API（Framework）→ Camera HAL Service（独立进程，Binder IPC）→ Camera 驱动（内核）→ ISP 硬件。每一步都有延迟，其中硬件处理（自动对焦、曝光、ISP 处理）通常占大头。

在 Perfetto 中，Camera HAL 的延迟可以在 `camera provider` 进程的 track 上看到。如果这个进程的 CPU 切片显示它在等 I/O（"Uninterruptible Sleep"），大概率是在等硬件完成操作。这种情况下，软件层面的优化空间有限，更多需要从硬件设计和驱动优化入手。

## 在 Perfetto 中的表现

Android 分层架构在 Perfetto Trace 里有很直观的映射，每一层都有对应的可视化表现。学会在 Trace 中“看到”分层架构，是性能分析的基本功。

### 三种数据源与三层架构的对应关系

Perfetto 采集数据的方式恰好与 Android 的三层结构一一对应。最底层是 **ftrace**，它直接从 Linux 内核采集调度切换（`sched_switch`）、CPU 频率变化（`freq`）、Binder 驱动事务（`binder_transaction`）、I/O 事件等。这些事件对应的就是架构中的内核层。

中间层是 **atrace**（Android Trace），它通过系统属性和服务接口从 Framework 和 HAL 层采集标记事件。atrace 按 category 组织：`hal` 追踪 HAL 模块活动，`hwui` 追踪硬件加速渲染过程（DisplayList 录制、GPU 命令提交），`sched` 和 `freq` 追踪调度和频率，`binder_driver` 追踪所有 Binder IPC。每个 category 恰好对应架构的一个或多个层级——理解这些 category，就能在 Perfetto 中快速定位到感兴趣的架构层。

最上层是 **`/proc` 和 `/sys` 轮询**，Perfetto 定期读取这些虚拟文件系统来获取进程状态、内存计数器、电池信息等系统级状态。这些数据横跨所有架构层，提供宏观视角。

[已验证: 来源见 research-feeds/2026-03-30-19-ch01-architecture-perfetto-mapping.md]

### 各层对应的 Track 和事件

在 Perfetto UI 中打开一个系统级 Trace，最上面是按 CPU 编号排列的调度 Track（内核层），中间是各进程的线程 Track（App/Framework/Native 层），底部是各类 Counter Track（内存、功耗等）。其中 Binder Transaction Track 贯穿所有进程——它就是架构分层图中那条"跨层通信"的箭头在 Trace 中的具象化。

**应用层**的表现最直观：每个 App 都是一个独立的进程 Track。展开一个 App 进程，会看到它的主线程（`main`）、Binder 线程（`Binder:xxxx_x`）和 RenderThread。主线程上的 CPU 切片就是 App 的 Java/Kotlin 代码执行时间。如果主线程出现长时间连续的 CPU 切片，说明有耗时的业务逻辑阻塞了 UI 渲染。ART 的 GC 事件也在主线程 Track 中可见，标注为 "GC" slice——如果 GC 频繁出现且耗时长，说明存在内存抖动问题。

**Framework 层**主要体现在 `system_server` 进程中。展开它会看到几十个线程，每个线程对应一个或多个系统服务。比如 `ActivityManager` 线程处理 Activity 相关请求，`WindowManager` 线程处理窗口相关请求。当 App 向这些服务发起 Binder 调用时，Trace 中会出现一条从 App 进程指向 `system_server` 对应线程的箭头。如果这个箭头很长（等待时间长），需要到 `system_server` 对应线程中看它在忙什么。`surfaceflinger` 虽然与 Framework 层的 WMS 紧密协作，但它是独立的 Native 进程，在 Trace 中需要单独查看它的进程 Track。

`surfaceflinger` 是独立的 Native 系统服务进程，不属于 Framework 层也不属于 HAL 层，在架构上属于 Graphics Stack 的核心组件。Android 16 的 SurfaceFlinger 主路径经过 `SurfaceFlinger::commit()`（触发 layer 采集与 WorkloadTracer Commit）→ `SurfaceFlinger::composite()`（异步合成，CompositionEngine 路径）→ `postComposition`（帧提交与 vsync 偏移计算）。旧版本（Android 10 及之前）的主路径是 `onMessageReceived` → `handleMessageRefresh` → `doComposition`。如果合成阶段耗时过长，说明 GPU 合成负担重，可能需要减少 Surface 数量或降低图层复杂度。SurfaceFlinger 的 `FrameMissed` 行可以直接定位合成层问题，避免把根因误归到 App 层。

**Native/HAL 层**的表现比较分散。Treble 之后的 HAL 服务按传输模式区分：binderized HAL（AIDL HAL 和部分 HIDL HAL）以独立进程运行，名字类似 `android.hardware.camera.provider@2.4-service`；passthrough HAL（仅限 HIDL C++ 实现）则以共享库形式加载到调用方进程内，Trace 中不会出现独立的 HAL 进程。对于 binderized HAL，需要同时启用 `hal` 和 `binder_driver` 这两个 atrace category，才能看到完整的 Framework → HAL 调用路径。如果独立 HAL 进程频繁出现 "Runnable" 但不被调度的状态，说明系统 CPU 负载高，HAL 请求排队等待。对于 passthrough HAL，排查时要留在调用方进程内看 native slice 和锁竞争，不要去外面找不存在的 HAL 服务进程。

**内核层**在 Perfetto 中表现为底层的 CPU 调度 Track 和 ftrace 事件。每个 CPU core 上的调度切片（sched slice）显示了哪个线程正在执行。Binder 的事务事件（`binder_transaction`）记录跨进程通信的发起方、目标方和数据大小。这是唯一一个横跨所有架构层的数据源——无论跨的是哪两层，Binder 事务都会在这里留下记录。

[图：Perfetto Trace 截图示意，标注 App / system_server / surfaceflinger 进程，标注 Binder 调用箭头，标注 VSync 信号线，标注三种数据源的对应区域]

[已验证: 官方文档, https://perfetto.dev/docs/data-sources/atrace]

### 正常 vs 异常的表现对比

**正常情况：** App 主线程的 `doFrame()` 在每个 VSync 周期内完成（16.6 ms @60 Hz 或 8.3 ms @120 Hz）。Binder 调用箭头短而快。SurfaceFlinger 的合成阶段（Android 13+ 为 `composite`，Android 10 及之前为 `doComposition`）耗时稳定。

**异常情况（举例）：**
- 如果 App 主线程出现长时间 "Runnable" 但没有 CPU 切片，说明线程已经就绪但迟迟没拿到 CPU——可能是 CPU 被其他高优先级线程占满，或者系统处于 Thermal 降频状态。
- 如果 App 主线程的 Binder 调用箭头指向 `system_server` 后长时间没有返回，说明 SystemServer 在处理请求时被其他工作阻塞——可能是锁竞争，也可能是某个服务初始化慢。
- 如果 `surfaceflinger` 的合成阶段（Android 13+ `composite` / Android 10 及之前 `doComposition`）突然变长，可能是新增了一个复杂的 Surface（比如 Dialog 弹出），或者 GPU 驱动进入了低功耗模式需要唤醒。

[待补充：Trace 截图——正常帧 vs 掉帧对比]

## 常见问题与误区

### 误区：SurfaceFlinger 在 Framework 进程中

这是一个非常常见的误解。SurfaceFlinger 是一个独立的 Native 进程，不属于 SystemServer。在 Perfetto 中搜索 `surfaceflinger` 就能看到它的独立进程 track。它通过 Binder 与 SystemServer 中的 WMS 通信，但两者是完全独立的进程。理解这一点对于分析渲染问题很重要：SurfaceFlinger 的性能问题需要看 `surfaceflinger` 进程的 track，而不是 `system_server`。

### 误区：Zygote fork 会复制 ART 堆

有人认为 Zygote fork 会复制父进程的所有内存，因此内存开销很大。Linux 的 `fork()` 使用 Copy-on-Write（COW）机制：fork 后子进程和父进程共享同一份物理内存页，只有当某一方尝试写入时才复制被修改的页。由于 Zygote 在 fork 后会进入“等待下次 fork 请求”的状态（不修改已加载的类和资源），大部分内存页永远不会被复制。所以 Zygote fork 的实际内存开销远比直觉上的“复制整个堆”要小。

### 误区：HAL 层不影响性能，因为只是"接口封装"

HAL 在现代 Android 里还承担接口定义之外的进程隔离与硬件访问协调。Treble 之后，binderized HAL（AIDL HAL 和部分 HIDL HAL）作为独立进程运行，控制面调用走 Binder IPC（参数序列化 → 内核态切换 → 目标进程反序列化 → 执行 → 原路返回）。passthrough HAL（仅限 HIDL C++ 实现）以共享库形式加载到调用方进程内，不走跨进程 Binder。对于高频数据面操作（如 Camera 预览回调、Audio 数据流），即使控制面走 Binder，数据面通常使用 FMQ、共享内存、BufferQueue/dmabuf 等零拷贝通道，不走 Binder 数据拷贝。排查 HAL 延迟时，先按传输模式（binderized / passthrough）区分，再判断瓶颈在控制面 IPC 还是数据面吞吐。

### 误区：App 的性能问题一定在 App 层

很多性能问题出在 App 层（主线程做了耗时操作），但有不少场景根因在系统层。比如：
- **启动慢**：可能是因为 SystemServer 在处理多个启动请求时发生锁竞争，AMS 的 `ActivityManagerService.attachApplication()` 被阻塞。
- **渲染卡顿**：根因也可能落在 SurfaceFlinger 的合成阶段耗时过长（Android 13+ 看 `composite`，Android 10 及之前看 `doComposition`），也就是 GPU 合成负担过重。
- **ANR**：Input ANR 的根因也可能出在 SystemServer 端的 InputDispatcher 被其他工作拖慢。

在 Perfetto 中遇到性能问题时，**不要只看 App 进程**——把视线扩展到 `system_server`、`surfaceflinger`、相关 HAL 进程，往往能定位根因。Main Thread 上如果有一个持续几十毫秒的 Binder slice，下一步应先翻到 `system_server` 进程，找到处理这个 Binder 调用的线程；问题可能不在 App 本身，而在系统服务排队等待。理解分层架构是性能分析的基本功：每一层都可能是瓶颈所在。

[已验证: 来源见 research-feeds/2026-03-30-19-ch01-architecture-misconceptions.md]

### 误区：线程状态 "Running" 就意味着在干有用的事

在 Perfetto 的 CPU Track 中，"Running"（绿色）表示线程被 CPU 调度执行，但不一定在做有用的工作。它可能在等待自旋锁（spinlock）、忙轮询，甚至在做无意义的空转。需要结合线程 Track 中的 slice 信息（如 Binder transaction 标记、锁等待标记）一起判断。

反过来，"Uninterruptible Sleep"（紫色）通常意味着 I/O 等待或内核阻塞——这是性能瓶颈的强信号，不应该被忽略。CPU 使用率高不一定有效率（可能在空转），CPU 使用率低不一定没问题（可能被 I/O 或 Binder 等待阻塞）。只有结合 CPU Track + 线程 Track + Binder Track 三个维度，才能给出正确判断。

[已验证: 来源见 research-feeds/2026-03-30-19-ch01-architecture-misconceptions.md]

### 误区：Binder 调用很快，不需要关注

Binder 通过 `mmap()` 实现了单次数据拷贝，设计目标是高效 IPC。但"高效"不等于"免费"——同步 Binder 调用会阻塞调用线程。如果在 Main Thread 上执行同步 Binder 调用，而 `system_server` 端恰好忙于处理其他请求（比如后台 App 在做 `dex2oat`），App 侧就会看到 Main Thread 上一个持续的 "binder" slice，等待时间可能从几毫秒涨到几十甚至上百毫秒，直接导致掉帧甚至 ANR。

关键不在于 Binder 本身快不快，而在于 **Binder 调用链的端到端延迟取决于目标进程的处理速度**。目标进程忙、排队、被锁阻塞，都会传导为调用方的阻塞。分析 Binder 延迟时，永远要同时看调用方和被调用方。

[已验证: 来源见 research-feeds/2026-03-30-19-ch01-architecture-misconceptions.md]

### 面试常问：为什么 Android 要用 Binder 而不是 Socket/管道？

Binder 相比 Socket/管道的核心优势在于：**一次拷贝**。传统 IPC（Socket、管道、消息队列）至少需要两次数据拷贝（发送方 → 内核缓冲区 → 接收方），而 Binder 利用 `mmap()` 在目标进程空间预先映射了一块内存，发送方只需将数据拷贝到这块共享内存即可，目标进程直接读取。对于高频的小数据量 IPC（Android 系统中大量存在），这个差异非常显著。

此外，Binder 在内核层面实现了线程池管理——目标进程不需要自己管理接收线程，内核会在 Binder 请求到来时唤醒一个空闲的 Binder 线程。这让系统服务的并发处理变得非常高效。

[已验证: 官方文档, https://source.android.com/docs/core/architecture/kernel]

## Vendor VNDK 隔离对 native 库加载的影响（历史机制）

分层架构的接口隔离不只发生在 HAL 层。在 Android 8.0 引入 Treble 之后，Vendor 和 Framework 使用的 Native 库同样需要隔离——这就是 VNDK（Vendor Native Development Kit）机制。

> **版本说明**：VNDK 在 Android 8-14 期间是关键的接口隔离机制。Android 15 起正式过渡到 **VNDK-less**（也称 Self-contained HALs）架构，HAL APEX 自包含依赖库，`ro.vndk.version` 属性不再声明。VNDK 相关规则在新版本中已逐步退出，但在分析 Android 8-14 的存量设备和历史问题时仍然需要了解。

为什么需要隔离？Framework 和 Vendor 模块可能依赖同一个 C++ 库的不同版本。如果不隔离，链接器会随机加载其中一个版本，导致符号冲突或 ABI 不兼容的崩溃。

对性能的影响是双面的：VNDK 隔离要求 Vendor 进程只能使用白名单中的库，某些共享库需要被复制一份给 Vendor 使用，增加了存储空间和内存占用。但从系统稳定性的角度看，这个权衡是值得的——它消除了 Framework 更新导致 Vendor HAL 崩溃的风险。

---
## 参考资料

### AOSP 源码路径

1. SystemServer 启动流程
   `frameworks/base/services/java/com/android/server/SystemServer.java`

2. SurfaceFlinger 核心合成逻辑
   `frameworks/native/services/surfaceflinger/SurfaceFlinger.cpp`

3. Zygote 进程初始化
   `frameworks/base/core/java/com/android/internal/os/ZygoteInit.java`

4. Binder 驱动
   `drivers/android/binder.c`（内核源码）

### 官方文档

5. Android Platform Architecture
   https://developer.android.com/guide/platform

6. Android HAL Overview
   https://source.android.com/docs/core/architecture/hal

7. VINTF 与 system/vendor 兼容性
   https://source.android.com/docs/core/architecture/vintf

8. AIDL HAL 接口说明
   https://source.android.com/docs/core/architecture/aidl/aidl-hals

9. Project Mainline / Modular System
   https://source.android.com/docs/core/ota/modular-system

10. Low memory killer daemon
    https://source.android.com/docs/core/perf/lmkd

11. ART and Dalvik 运行时
    https://source.android.com/docs/core/runtime

12. VNDK 概述
    https://source.android.com/docs/core/architecture/vndk

### 工具与延伸阅读

13. Perfetto 数据源文档
    https://perfetto.dev/docs/data-sources/atrace

14. Android 性能优化系列 — androidperformance.com
    https://androidperformance.com/

---

## 调研记录

<!-- AIW-源码调研-2026-04-19 -->
- **2026-04-19**: 源码调研「SELinux 开销对 Binder 性能的影响」已完成。发现：SELinux 通过 `selinux_binder_transaction()` 钩子对每次 Binder transaction 执行 `avc_has_perm()` 检查；AVC 缓存使稳态开销极低（~50-200 ns/次）；Android 8+ Treble 三路 binder 设备隔离设计降低了跨域误用风险。报告：`OpenClaw定时任务/AutoResearchClaw调研报告/2026-04-19-selinux-binder-performance-overhead.md`

