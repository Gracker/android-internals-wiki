---
title: "Google 官方的性能优化思路"
chapter: "16.1"
status: ready-for-review
drafted_date: "2026-04-04"
applicable_versions: "Android 4.1 (API 16) - Android 16 (API 36)"
last_verified: "2026-04-04"
last_verified_against: "官方文档 + Google Blog + Android Developers"
confidence: medium
sources:
  - type: official
    path: "developer.android.com/topic/performance"
  - type: official
    path: "developer.android.com/topic/performance/baselineprofiles"
  - type: blog
    path: "android-developers.googleblog.com (Android Performance Patterns 系列)"
  - type: official
    path: "source.android.com/docs/core/runtime"
  - type: blog
    path: "android-developers.googleblog.com (Project Mainline / ART Mainline Updates)"
tags: ['google', 'performance-philosophy', 'project-butter', 'art', 'baseline-profiles', 'mainline']
related_chapters: ["1.6", "2.9", "4.6", "5.7", "8.3", "15.1"]
---

# Google 官方的性能优化思路

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 Google 性能优化的核心理念：Systemic Performance、User-Perceived Performance
- 🔹 各版本的 Performance 旗舰特性：Project Butter(4.1) → Svelte(4.4) → ART(5.0) → Treble(8.0) → Mainline(10)
- 🔹 Android Runtime (ART) 的持续优化方向
- 🔹 Framework 层的性能优化实践（View 系统、Handler、Binder Pool）
- 🔹 Google 官方的 Performance 文档与最佳实践总结

### 扩展（可选深入）

- 🔸 Android Go Edition 的性能优化策略
- 🔸 Google 内部的性能测试基础设施（公开信息）

### OpenClaw 加工指引

> **锚点**是最低覆盖要求，加工时必须逐条落实并标注验证结果。
> **扩展**视素材丰富程度选择性深入。
> 如果从 Obsidian 素材或 AOSP 源码中发现大纲未列出但与本节强相关的知识点，
> 可**就地插入**最相关的锚点之后，并用 `[自动发现]` 标注，方便后续 review。
> 锚点内容需 L1/L2 验证，扩展内容至少 L2 验证，自动发现内容至少标注来源。
<!-- outline-end -->

## 为什么要了解 Google 的性能优化思路

我们这本书花了大量篇幅讲解 Android 内部的各种机制——VSync、Binder、内存管理、调度器。但如果你退后一步，站在 Google 的视角看整个 Android 生态的演进，会发现这些具体的机制改动背后有一条清晰的主线：Google 在用一种特定的方式思考性能问题，并且这种思考方式贯穿了从系统架构到开发工具的每一层。

理解这条主线有三个直接的好处。第一，当你面对一个性能问题时，能判断它是 Google 已经在系统层面解决的问题、还是需要 App 端自己处理的——这决定了你的优化方向。第二，Google 的官方文档和工具（Baseline Profiles、Jetpack Benchmark、Android Vitals）都是围绕这套理念设计的，理解理念才能用好工具。第三，Google 每个版本的性能改动不是随机的——从 Project Butter 到 Project Mainline，有一条可预测的演进逻辑。掌握了这条逻辑，你就能提前预判下一个版本会动什么。

## 核心理念：两层性能观

Google 对性能问题的认知可以归纳为两个层面。

### 系统层（Systemic Performance）

第一层是系统本身的性能基础。这不是某个 App 能左右的，而是整个平台的能力上限。Google 在这方面的核心策略是持续优化系统底层——内核、运行时、驱动、合成管线——让所有 App 自动受益。

举个具体的例子：Android 内核大约占设备 CPU 时间的 40%。Google 在 Android 16 中引入了 AutoFDO（Automatic Feedback-Directed Optimization），通过分析真实使用模式来重新排列和优化内核代码的指令布局。这个优化不需要任何 App 配合，所有运行在该内核上的代码都会变快——冷启动提升约 4.3%，Binder 调用提升 21.7%，某些微基准测试提升高达 37.7%。[已验证: Google Blog, android-developers.googleblog.com]

类似的系统级优化还包括：ART 运行时的 GC 演进（从 Dalvik 的 STW 到 ART 的并发拷贝 GC），Binder 驱动的性能改进，以及 SurfaceFlinger 合成管线的持续重构。这些改动的一个共同特点：App 开发者什么都不用做，升级系统就自动受益。

### 用户感知层（User-Perceived Performance）

第二层是用户直接感受到的性能。这一层的优化对象是启动时间、滚动流畅度、触控响应速度、ANR 率。Google 的核心观点是：**性能的本质是用户感知，不是技术指标**。一个 App 的帧率从 55fps 提升到 58fps，如果用户在操作时仍然能感知到卡顿，那这个优化在工程上可能是对的，但在产品上是不够的。

这个理念体现在 Google 的很多工具设计上。Android Vitals 在 Google Play Console 中追踪的核心指标不是 CPU 利用率或内存分配量，而是用户直接感知到的指标：ANR 率、崩溃率、卡顿率（bad behavior rate）、前台服务滥用率。Jetpack Benchmark 库的设计目标也不是"测出某个方法的绝对耗时"，而是"测出用户实际会感受到的差异"。

这两层性能观的关系是这样的：系统层决定了平台的能力天花板，用户感知层决定了 App 能不能用好这个天花板。一个 App 如果在启动时做了太多的同步初始化、在主线程做了阻塞 I/O、在滚动时触发了大量的 GC，那即使系统再快，用户感知到的也是慢。

## 版本旗舰特性：一条清晰的演进线

Google 从 Android 4.1 开始，几乎每个大版本都有以性能为核心的"Project"。这些 Project 不是孤立的，它们之间有明确的递进关系。

### Project Butter（Android 4.1，2012）：让动画变得"丝滑"

Project Butter 是 Android 性能优化的分水岭。在 4.1 之前，Android 的"卡"是出了名的——滑动不流畅、动画掉帧、触控有延迟。Project Butter 用三个核心改动试图解决这个问题。

第一个是 **VSync 同步**。在此之前，App 渲染和屏幕刷新是不同步的，导致画面撕裂和帧率不稳定。Project Butter 引入了 VSync 信号驱动的渲染管线——Choreographer 在 VSync 到来时统一调度 Input、Animation、Traversal 三类回调，整个渲染过程被纳入一个严格的时间框架。（我们在 [2.3 VSync 机制](../part1-fundamentals/ch02-rendering/03-vsync.md) 和 [2.4 Choreographer](../part1-fundamentals/ch02-rendering/04-choreographer.md) 中详细分析了这套机制。）

第二个是 **三缓冲**。双缓冲在某些场景下会导致 CPU 空闲一个 VSync 周期——它必须等 GPU 释放 Buffer 才能开始画下一帧。三缓冲增加了一个缓冲区，让 CPU 可以提前开始下一帧的渲染，减少掉帧。

第三个是 **触控预测**。系统根据用户的触控轨迹预测下一个触控点，提前开始处理，降低从手指触碰到屏幕响应之间的延迟。

Project Butter 的核心贡献不只是这三个技术改动，更重要的是它建立了一个"以帧为单位"的性能思维模型——后续所有的渲染优化，从 RenderThread 到 Frame Pacing Library 到 FrameMetrics API，都是在这个模型上发展的。[已验证: 官方文档, source.android.com]

### Project Svelte（Android 4.4，2013）：让系统跑在 512MB 内存上

如果说 Project Butter 解决的是"快不快"的问题，Project Svelte 解决的就是"能不能跑"的问题。

Android 4.4 的核心目标是让最新版本的 Android 能在只有 512MB RAM 的设备上流畅运行。Google 工程团队的做法很硬核：他们把 Nexus 4 降级到 512MB 内存、双核 CPU、960x540 分辨率，在这个配置上跑系统，发现哪里 OOM 就修哪里。

具体的改动包括：精简系统进程的内存占用、优化 Google Apps 的内存使用（大量预装应用从系统镜像中解耦出来）、改进 low memory 状态下应用的行为（通过 onTrimMemory 回调），以及提供新工具 ProcStats 帮开发者监控应用的内存消耗。[已验证: Google I/O 2013 演讲 + developer.android.com]

Project Svelte 的遗产是 Android Go Edition，这个轻量版系统至今仍在面向入门级设备发布。

### ART 替代 Dalvik（Android 5.0，2014）：运行时的根本性重写

从 Dalvik 切换到 ART 不是一次简单的"升级"，而是整个运行时的推倒重来。Dalvik 使用 JIT（Just-In-Time）编译，每次运行代码时都需要解释执行或即时编译，这导致两个问题：运行时性能不稳定（热路径代码第一次执行一定慢），以及 GC 暂停时间不可控。

ART 引入了 AOT（Ahead-Of-Time）编译——在应用安装时就把 DEX 字节码编译成本地机器码。这让应用的运行速度有了可预测的基础，GC 也从 Dalvik 的 mark-and-sweep 演进为并发拷贝收集器（Concurrent Copying Collector），暂停时间大幅降低。

但这不是故事的终点。纯 AOT 有自己的问题：安装时间过长、存储空间占用过大。所以从 Android 7.0 开始，ART 走上了一条 JIT + AOT + Profile-Guided 的混合编译路径。系统先用 JIT 解释执行，同时收集"热方法"的 Profile；设备空闲时，根据 Profile 做针对性的 AOT 编译。这条路径最终演化出了 Baseline Profiles 和 Cloud Profiles。

[已验证: 官方文档, source.android.com/docs/core/runtime]

### Project Treble（Android 8.0，2017）：解耦 HAL，加速系统更新

Project Treble 解决的不是直接的性能问题，而是"性能优化能不能及时到达用户"的问题。

在 Treble 之前，Android 的框架代码和芯片厂商的 HAL 代码是耦合在一起的。Google 改了框架层的性能 bug，但这个更新需要芯片厂商和手机厂商适配 HAL，而适配周期可能长达一年甚至更久。结果是大量设备永远停留在旧版本，享受不到系统级的性能改进。

Treble 引入了 HIDL 接口层，把 Framework 和 HAL 彻底隔离开。Google 可以独立更新 Framework，不需要等厂商适配。这个架构改动是后续所有"快速推送性能优化"的基础——没有 Treble，就不会有 Project Mainline。[已验证: source.android.com/docs/core/architecture/treble]

### Project Mainline（Android 10，2019）：通过 Play 推送系统组件更新

Project Mainline 在 Treble 的基础上走得更远：它把 Android 系统拆分为十几个独立的 APEX 模块，这些模块可以通过 Google Play 系统更新来推送，不需要完整的 OTA 升级。

对性能优化影响最大的 Mainline 模块是 ART 模块。从 Android 12 开始，ART 的更新可以通过 Play 推送到设备上。这意味着 Google 不需要等设备厂商发布系统更新，就能把运行时的性能改进推送给用户。前面提到的 AutoFDO 优化、分代 GC、Cloud Profiles 这些技术，都是通过 Mainline 机制快速到达设备的。[已验证: source.android.com/docs/core/mainline]

这条演进线的逻辑越来越清晰：从 Project Butter 的"让系统更快"到 Project Mainline 的"让优化更快到达用户"。Google 在做的不只是优化系统本身，还在优化"优化系统的分发方式"。

## ART 的持续优化方向

ART 不是一成不变的运行时。在从 Android 5.0 的纯 AOT 到今天的混合编译路径之间，Google 做了大量增量优化。这里我们梳理几个最重要的方向。

### 编译策略的演进：从 AOT 到 Profile-Guided

纯 AOT 编译的问题前面提到了——安装太慢、占用太多空间。Android 7.0 引入了 JIT 解释执行 + Profile 收集的混合模式。具体来说：应用首次运行时，ART 用 JIT 解释执行字节码，同时在后台记录哪些方法被频繁调用（"热方法"）。设备充电且空闲时，`dex2oat` 编译器根据 Profile 对热方法做 AOT 编译。这样下次启动应用时，关键路径已经是机器码了，而不是需要 JIT 解释的字节码。

Android 9.0 进一步引入了 Cloud Profiles：当足够多的用户在设备上产生了 Profile，Google 会把这些 Profile 聚合后上传到云端，然后在其他用户首次安装应用时预置这些 Cloud Profiles。这解决了"新安装的应用第一次运行一定慢"的问题——因为 ART 有了云端提供的 Profile，安装时就能对关键路径做 AOT 编译。

Baseline Profiles 是 Cloud Profiles 的开发者可控版本。开发者可以在应用中打包一个自己定义的 Profile（指定哪些类和方法需要在安装时编译），ART 在安装时优先使用 Baseline Profiles 做编译。根据 Google 的数据，Baseline Profiles 可以将关键代码路径的执行速度提升约 30%。[已验证: developer.android.com/topic/performance/baselineprofiles]

### GC 的演进：从暂停到几乎无感

Dalvik 的 mark-and-sweep GC 有两个致命问题：GC 时所有线程暂停（Stop-The-World），以及堆碎片化导致的频繁 Full GC。ART 的 Concurrent Copying Collector 通过并发标记和对象搬移同时解决了这两个问题。

从 Android 8.0 开始，ART 进一步引入了分代收集：年轻代（Young Generation）使用 Copying Collector，回收频率高但暂停时间极短（1-3ms）；老年代（Old Generation）使用标记-压缩收集器，回收频率低但更彻底。Android 16/17 中的分代 GC 进一步细化了年轻代的处理，暂停时间进一步缩短。[待验证: Android 17 分代 GC 暂停时间的精确数据]

### 工具链优化：R8、D8 和 Startup Profiles

R8 是 Android 的代码压缩和优化工具，替代了旧的 ProGuard。R8 不只是做代码混淆和移除未使用的类——它还能做类合并、方法内联、常量折叠等优化，生成更小的 DEX 文件。更小的 DEX 意味着更短的 dex2oat 编译时间和更少的页面错误（page fault）。

Startup Profiles（AGP 8.3 默认启用）是 Baseline Profiles 的编译时补充。它们指导 D8 编译器在生成 DEX 文件时，将启动关键路径上的类放在 DEX 文件的前部，减少冷启动时的 page fault。配合 Baseline Profiles 使用，冷启动可以提升 15-30%。[已验证: developer.android.com/topic/performance/baselineprofiles]

## Framework 层的性能优化实践

Google 在 Framework 层的优化往往不像 Project Butter 那样有一个响亮的名字，但它们的累积效果同样显著。

### View 系统的持续瘦身

Android 的 View 系统从 1.0 开始就存在，历史包袱沉重。Google 在每个版本中都在做小幅度的优化：减少 View.measure 和 View.layout 的重复调用、优化 invalidate 的传播范围、减少不必要的 requestLayout 触发。

一个值得注意的长期趋势是：Google 正在把越来越多的渲染工作从主线程转移到 RenderThread。从 Android 5.0 引入 RenderThread 开始，到今天，主线程主要负责 measure/layout/draw 的记录（生成 DisplayList），而实际的 OpenGL/Vulkan 渲染指令执行都在 RenderThread 中异步进行。这意味着主线程的耗时不再直接等于渲染耗时——即使主线程稍微慢一点，只要 RenderThread 能在 VSync 周期内完成渲染，用户仍然不会感知到卡顿。[已验证: AOSP, frameworks/base/libs/hwui/]

### Handler/MessageQueue 的优化

主线程的 MessageQueue 是 Android 事件驱动的核心。Google 在近期的版本中对它做了两个重要的性能优化。

第一个是锁优化。MessageQueue 的 `next()` 方法需要与 `enqueueMessage()` 争抢锁（`mLock`）。在高频消息场景下（比如快速滑动时的 Input 事件和 Traversal 消息交替入队），锁竞争会导致主线程不必要的等待。Android 14/15 对锁的粒度做了优化，减少了临界区的范围。

第二个是 Android 17 中引入的 DeliQueue（实验性）。这是一种无锁的消息队列设计，针对主线程的高频消息场景做了特殊优化。根据公开数据，DeliQueue 可以将主线程锁等待减少约 15%，掉帧减少约 4%，冷启动首帧的 P95 延迟改善约 9.1%。[待验证: DeliQueue 是否在 Android 17 正式版中默认启用]

### Binder 的性能改进

Binder 是 Android 进程间通信的基础设施，几乎所有的跨进程调用都经过它。Google 在 Binder 上的优化主要是减少数据拷贝和改进调度。

Android 8.0 引入了 Binder 线程池的动态扩展（之前是固定的 16 个线程），允许系统根据负载调整线程池大小。Android 10+ 引入了 Binder 事务的优先级继承，防止低优先级进程的 Binder 调用阻塞高优先级进程。

在 Perfetto 中，我们可以通过 Binder Track 观察这些优化的效果——`client_dur`（客户端耗时）、`server_dur`（服务端耗时）、`dispatch_dur`（分发延迟）三个维度的指标可以帮助我们定位 Binder 调用中的性能瓶颈。[已验证: perfetto.dev/docs/data-sources/android-binder]

### 窗口管理的优化：从 WindowManager 到 BlastBufferQueue

Android 12 引入的 BlastBufferQueue 是窗口管理管线的一次重要重构。在此之前，Buffer 的跨进程传递需要经过 BufferQueue 的多个中间状态（FREE → DEQUEUED → QUEUED → ACQUIRED），每次状态转换都可能涉及 Binder 调用和锁竞争。BlastBufferQueue 简化了 Buffer 的传递路径，让 App 进程可以直接将渲染完成的 Buffer "blast" 给 SurfaceFlinger，减少了中间环节的延迟。[已验证: AOSP, frameworks/native/libs/gui/]

## Google 官方的 Performance 工具与文档体系

Google 围绕性能优化建立了一套完整的工具和文档体系。这里我们做一次系统性的梳理，帮助读者知道"有什么工具"以及"在什么场景下用什么工具"。

### 文档入口

Google 官方的性能文档有几个主要入口：

- **developer.android.com/topic/performance**：总入口，涵盖启动性能、渲染性能、内存管理、网络优化、电池优化等所有主题。
- **Android Performance Patterns**：2015 年发布的一系列视频教程，由 Google 工程师 Colt McAnlis 主讲。虽然部分内容已经过时（比如当时还在讲 Dalvik），但其中关于渲染管线、VSync、过度绘制的基础概念讲解至今仍然值得一看。
- **developer.android.com/studio/profile**：Android Studio Profiler 的官方文档，包括 CPU Profiler、Memory Profiler、Network Profiler 的使用方法。

### 开发者工具链

Google 提供的性能工具可以分为三类：**度量工具**、**分析工具**和**优化工具**。

度量工具回答"有没有问题"：

- **Jetpack Benchmark**（`androidx.benchmark`）：在 CI 环境中稳定测量代码执行时间。它自动处理 CPU 频率锁定、预热循环、结果统计等细节，确保测量结果的可重复性。
- **Macrobenchmark**：Jetpack Benchmark 的"宏观"版本，用于测量整个用户操作的耗时，比如冷启动时间、帧率。配合 Baseline Profiles 使用，可以直接测量 Profile 带来的性能提升。
- **Android Vitals**：通过 Google Play Console 查看真实用户的性能数据。核心指标包括 ANR 率、崩溃率、卡顿率（用户感知到卡顿的会话比例）。这是唯一能告诉你"真实用户到底体验如何"的工具。

分析工具回答"问题在哪里"：

- **Android Studio Profiler**：集成的 CPU、内存、网络、能耗分析器。适合开发阶段的问题定位。
- **Perfetto**：系统级 Trace 分析工具。适合分析跨进程的性能问题，比如 App → Binder → SystemServer → SurfaceFlinger 的完整链路。（我们在 [第 13 章 Perfetto](../part3-tools/ch13-perfetto/01-perfetto-intro.md) 有详细介绍。）
- **Simpleperf**：基于 Linux `perf` 的 Native 代码性能分析工具。适合分析 C/C++ 代码的热点函数和调用栈。

优化工具回答"怎么修"：

- **Baseline Profiles + Startup Profiles**：在安装时预编译关键代码路径，减少运行时的 JIT 开销。
- **R8**：代码压缩和优化工具，减小 APK 体积和运行时内存占用。
- **App Startup Library**：Jetpack 提供的启动库，帮助组织 Application 的初始化逻辑，支持懒加载和依赖管理。

### Google 的最佳实践总结

Google 在多个场合（I/O 演讲、官方文档、Codelab）中反复强调的性能最佳实践可以归纳为几条核心原则：

**原则一：不要在主线程做阻塞操作。** 这条规则说起来简单，但实际违反它的场景无处不在：同步的 SharedPreferences 写入、主线程的 Binder 调用、数据库的同步查询、甚至一个大 JSON 的反序列化。Google 的建议是：如果它可能超过 1ms，就放到后台线程。

**原则二：延迟初始化。** 不是所有代码都需要在 Application.onCreate() 里执行。Google 推荐的做法是：只初始化用户在启动后前几秒内就需要使用的组件，其他的延迟到实际需要时再初始化。App Startup Library 可以帮助管理这种依赖关系。

**原则三：优化关键路径，而非全局优化。** 用 Macrobenchmark 识别用户感知最明显的操作（通常是冷启动和列表滚动），然后集中优化这些路径。Baseline Profiles 的核心思路就是这个——只预编译用户真正会用到的代码路径，而不是试图优化所有代码。

**原则四：在低端设备上测试。** Google 的 Android Vitals 数据显示，低端设备上的性能问题发生率远高于高端设备。Google 的内部测试矩阵包括各种 RAM 大小、CPU 核心数和屏幕分辨率的设备配置。如果一个优化方案只在旗舰设备上有效，那它很可能不是一个好的优化。

**原则五：度量先行。** 在优化之前先测量基准值，优化之后确认提升幅度。Jetpack Benchmark 和 Macrobenchmark 是为此设计的。没有数据的优化和盲猜没有区别。

## Android Go Edition：面向入门设备的性能策略

[已验证: developer.android.com/android-go]

Android Go Edition（也叫 Android Go）是 Google 面向 1-2GB RAM 入门设备的轻量版系统。它的核心策略和 Project Svelte 一脉相承，但在技术实现上走得更远。

系统层面的改动包括：预装应用的内存占用被严格限制（每个 Google Go 应用比标准版应用节省约 50% 内存），系统服务被精简（一些不必要的服务直接裁剪），以及针对低内存场景的 LMK 策略调整。

应用层面的策略是：鼓励开发者使用 Feature Flags 或 APK Split 来减少单个安装包的功能和代码量。Go Edition 的用户设备上通常只有 8-16GB 的存储空间，一个 100MB 的应用可能就占用了 1% 的存储。

Go Edition 的存在也验证了 Google 性能理念中的一个重要观点：**好的性能优化应该是向下兼容的**。为低端设备做的优化（减少内存分配、减少后台工作、延迟初始化）同样会让高端设备受益。

## Google 内部的性能测试基础设施

Google 内部的性能测试体系在公开信息中能了解到的主要有以下几个方面。

**AOSP 中的测试框架。** AOSP 中包含了大量的性能基准测试（在 `platform/testing` 目录下），涵盖启动时间、渲染性能、Binder 调用延迟等。这些测试是 Google 内部 CI 系统的一部分，每次提交代码都会运行，用于回归检测。

**Postsubmit 性能监控。** Google 在内部的 CI 系统中持续监控每个 AOSP 提交对性能指标的影响。如果某个提交导致启动时间增加了 50ms 或帧率下降了 2fps，会自动触发告警并通知提交者。这种"性能回归检测"机制确保了性能是持续改善的，而不是随着功能增加而逐渐退化。

**设备农场（Device Farm）。** Google 在全球多个数据中心维护了大量的真实设备集群，用于运行自动化性能测试。这些设备覆盖了不同的 SoC 平台（高通、联发科、三星、谷歌 Tensor）、不同的 Android 版本和不同的内存配置。

[待补充: Google 内部 Perfetto Dashboard 和 Android Vitals 后台的具体使用细节，这些信息目前只有公开演讲中的零散提及]

## 常见问题与误区

### "Google 的系统级优化就够了，App 不需要自己优化"

系统级优化提高了平台的能力上限，但 App 的实际表现取决于它怎么使用这个平台。一个在主线程做同步 Binder 调用的 App，在再快的系统上也会卡。Google 的优化是乘数（让好的更好），不是魔法（不能让差的不差）。

### "Baseline Profiles 能解决所有启动性能问题"

Baseline Profiles 只解决"代码需要 JIT 编译"这一层的问题。如果你的启动慢是因为在主线程做了大量 I/O、或者初始化了太多不需要的库，Baseline Profiles 帮不了你。它是在代码已经是机器码的基础上还能省多少的问题，不是能替代架构优化的银弹。

### "升级到最新的 Android 版本，性能自动就会变好"

这句话大部分时候是对的——ART 的优化、Binder 的改进、渲染管线的重构确实在每个版本都有进步。但有两个例外：一是新的隐私限制可能导致某些操作变慢（比如 Android 11+ 的包可见性查询需要额外的 IPC）；二是新的功能可能引入新的开销（比如 Android 12 的 SplashScreen API 如果配置不当，反而会增加启动时间）。升级通常带来净正收益，但具体到某个 App 某个场景，仍然需要实测。

### "Google 的性能优化思路只适用于大厂 App"

Google 的最佳实践——延迟初始化、避免主线程阻塞、减少内存分配——适用于所有大小的 App。事实上，小 App 反而更容易做到这些，因为它们的依赖更少、架构更简单。Baseline Profiles 和 Macrobenchmark 也被设计为可以在任何项目中集成的 Gradle 插件，不需要复杂的构建系统。

## 参考资料

- AOSP 源码路径：
  - `frameworks/base/core/java/android/view/Choreographer.java`（VSync 驱动的渲染调度）
  - `frameworks/base/core/java/android/os/Handler.java`（消息队列核心）
  - `frameworks/native/libs/binder/`（Binder IPC 实现）
  - `art/runtime/`（ART 运行时核心）
  - `system/memory/`（内存管理相关）
- [已验证: 官方文档, developer.android.com/topic/performance]
- [已验证: 官方文档, developer.android.com/topic/performance/baselineprofiles]
- [已验证: 官方文档, source.android.com/docs/core/runtime]
- [已验证: 官方文档, source.android.com/docs/core/mainline]
- [已验证: 官方文档, source.android.com/docs/core/architecture/treble]
- [已验证: Google Blog, android-developers.googleblog.com]
- [已验证: Perfetto 文档, perfetto.dev/docs/data-sources/android-binder]
- [引用: https://www.androidperformance.com/（高爷博客）]
