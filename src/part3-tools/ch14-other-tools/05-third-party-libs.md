---
title: "三方性能库"
chapter: "14.5"
section: "14.5"
status: ready-for-review
drafted_date: "2026-04-03"
drafted_by: "openclaw-task2a"
applicable_versions: "Android 5.0 (API 21) - Android 16 (API 36)"
last_verified: "2026-04-03"
last_verified_against: "AOSP android-16.0.0_r1"
confidence: medium
sources:
  - type: blog
    path: "https://mp.weixin.qq.com/s/vkBeZ6hmVn_RaXS5Xv_L2g (抖音 Rhea)"
  - type: blog
    path: "https://github.com/Tencent/matrix (微信 Matrix)"
  - type: blog
    path: "https://github.com/KwaiAppTeam/KOOM (快手 KOOM)"
  - type: blog
    path: "https://github.com/didi/Booster (滴滴 Booster)"
  - type: blog
    path: "https://github.com/iqiyi/xHook (爱奇艺 xHook)"
tags:
  - android
  - research
pipeline_stage: task6_pending
task6_state: revisiting
task9_state: pending
task9_result: needs-rework
task2b_state: fixed
reviewed_by: "openclaw-task6"
reviewed_date: "2026-04-14"
task6_result: needs-rework
task2b_result: fixed
last_task2b_at: "2026-04-21T19:51:48+08:00"
---


# 三方性能库

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 Matrix（微信）：Trace Canary、Resource Canary、IO Canary 等
- 🔹 KOOM（快手）：Java/Native 内存泄漏检测
- 🔹 Booster（滴滴）：编译期优化插件
- 🔹 Anchors / AppInit 等启动优化框架
- 🔹 各工具的核心原理、优缺点对比

### 扩展（可选深入）

- 🔸 Rhea（字节跳动）Trace 工具
- 🔸 各工具的 Hook 机制对比（PLT Hook / Inline Hook / Transform）

### OpenClaw 加工指引

> **锚点**是最低覆盖要求，加工时必须逐条落实并标注验证结果。
> **扩展**视素材丰富程度选择性深入。
> 如果从 Obsidian 素材或 AOSP 源码中发现大纲未列出但与本节强相关的知识点，
> 可**就地插入**最相关的锚点之后，并用 `[自动发现]` 标注，方便后续 review。
> 锚点内容需 L1/L2 验证，扩展内容至少 L2 验证，自动发现内容至少标注来源。
<!-- outline-end -->

## 为什么要了解三方性能库

我们在前面几章介绍了 Perfetto、Simpleperf、Android Studio Profiler 等官方工具。这些工具能力强大，但有一个共同的局限：它们主要服务于线下分析场景。当我们需要在线上（生产环境）监控真实用户的性能数据、在灰度阶段快速定位特定用户的卡顿问题、或者在编译期自动扫描潜在性能陷阱时，就需要借助三方性能库了。

本章介绍的工具和 Perfetto 互补，覆盖的是线上监控、自动检测、编译期预防这些场景。理解每个工具的核心原理和适用场景，能帮助我们在合适的时机选对工具组合。

## Matrix：微信的全链路性能监控

Matrix 是腾讯微信团队开源的 Android 性能监控框架，也是目前国内覆盖面最广、集成度最高的性能监控方案之一。它是一套完整的 APM（Application Performance Monitoring）体系，包含多个子模块，每个模块针对一个特定的性能维度。

### 整体架构

Matrix 的设计思路是"无侵入接入、全链路覆盖"。它通过 Gradle 插件在编译期完成字节码插桩，运行时通过 Hook 收集各类性能数据，最终将数据上报到监控平台。整个框架分为五个核心模块：

- **Trace Canary**：卡顿、ANR、启动耗时、帧率监控
- **Resource Canary**：Activity/Fragment 内存泄漏、冗余 Bitmap 检测
- **IO Canary**：文件 I/O 性能问题检测、Closeable 泄漏监控
- **SQLiteLint**：SQLite 使用规范检测
- **Battery Canary**：耗电行为监控

[已验证: 官方文档, github.com/Tencent/matrix]

### Trace Canary：卡顿与 ANR 的精准定位

Trace Canary 的核心能力是检测卡顿、慢函数、ANR、启动耗时和帧率异常。它的工作原理可以分两层来看。

第一层是**编译期插桩**。Trace Canary 会在编译阶段对应用字节码做方法级改写，在每个方法的入口和出口插入计时逻辑。这种插桩是选择性的，可以按包名、类名或白名单限制范围，控制运行时开销。插桩后的代码会在方法执行时记录起止时间戳和调用堆栈。早期版本主要依赖 Transform API，AGP 8.0+ 已经转到基于 Instrumentation API 的 `AsmClassVisitorFactory` 方案，插桩本质仍然是编译期字节码修改。

第二层是**运行时检测**。Trace Canary 监听主线程的 Looper 消息分发和 Choreographer 的 doFrame 回调。当一个 Message 的执行耗时超过阈值（比如默认 700ms），或者一帧的渲染超过 16.6ms 导致连续掉帧，它就会触发上报逻辑。对于 ANR 检测，Trace Canary 提供两种方式：LooperAnrTracer 在主线程 Message 开始执行时设置一个 5 秒超时（类似"埋炸弹"），如果超时触发则判定为 ANR；SignalAnrTracer 则通过捕捉系统发出的 SIGQUIT 信号来检测。

在实际分析中，我们可以通过 Trace Canary 的上报数据看到：触发卡顿的具体方法、完整的调用堆栈、该方法的执行耗时以及执行次数。这比在 Perfetto 中逐帧查看 Trace 要高效得多，特别是在线上环境中。

[已验证: 新版 Matrix Trace Canary 在 AGP 8.0+ 下使用基于 Instrumentation API 的 ASM visitor 方案，插桩本质仍然是编译期字节码改写]

### Resource Canary：内存泄漏与冗余 Bitmap

Resource Canary 采用弱引用（WeakReference）机制来检测 Activity 和 Fragment 的泄漏。它的做法是这样的：注册 ActivityLifecycleCallbacks，在每个 Activity 的 onDestroy 回调中，将该 Activity 实例包装成弱引用并存入观察队列。然后定期触发 GC 并轮询检查队列中的弱引用是否已被回收。如果在多次检查后仍然存活，就认为发生了泄漏。

检测到泄漏后，Resource Canary 会 Dump 出 Hprof 文件，但它不会把整个文件上传——那样太大了。它会在客户端对 Hprof 进行裁剪，只保留泄漏 Activity 到 GC Root 的强引用链和 Bitmap 数据缓冲区，大幅压缩文件大小后再上报。服务端收到后进行解析，还原出完整的引用链。

Resource Canary 还有一个独特的能力：**冗余 Bitmap 检测**。它通过分析 Hprof 中所有未被回收的 Bitmap 对象，对比其像素数据缓冲区的内容，找出图像数据完全相同但被多次创建的 Bitmap。这在实际项目中很有价值——我们经常看到不同模块各自 decode 了一份相同的图片资源。

[已验证: 官方文档, github.com/Tencent/matrix/wiki]

### IO Canary：文件 I/O 的问题扫描

IO Canary 通过 Native Hook 的方式拦截 POSIX 层的文件操作接口（open、read、write、close），实现对文件 I/O 行为的全量监控。它使用的 Hook 方案是 PLT Hook（类似爱奇艺开源的 xHook），通过修改 GOT 表中的函数指针来拦截调用，而非修改目标函数的机器码。

通过 Hook 收集到的 I/O 信息，IO Canary 检测三类常见问题：

一是**主线程 I/O**。如果检测到 open、read、write 操作发生在主线程，且耗时超过阈值，就会上报。在 Perfetto 中，这类问题表现为 Main Thread 处于 Uninterruptible Sleep（D 状态），但在 Trace 中我们无法直接看到是哪个文件导致的。IO Canary 恰好补上了这个信息缺口。

二是**Buffer 过小**。如果 read/write 操作使用的缓冲区小于 4KB（即一个内存页），IO Canary 会认为缓冲区设置不合理，容易导致频繁的系统调用。

三是**重复读同一文件**。如果在短时间内多次 open 同一文件进行读取，说明可能存在缓存缺失或代码逻辑问题。

此外，IO Canary 还通过 Java 层 Hook CloseGuard 的 Reporter 来监控 Closeable 资源（如 InputStream、OutputStream）的泄漏。

[已验证: 官方文档, github.com/Tencent/matrix/wiki]

## KOOM：快手的内存泄漏监控

KOOM（Kwai OOM）是快手团队开源的内存监控方案，解决的核心问题是：如何在生产环境中高效检测 Java 堆、Native 堆以及线程的泄漏。相比 Matrix 的 Resource Canary（主要关注 Activity/Fragment 泄漏），KOOM 的监控范围更广。

### Java 堆泄漏检测

KOOM 的 Java 堆泄漏检测采用"阈值触发 + Hprof 裁剪"的方案。它通过 Runtime.totalMemory() 和 maxMemory() 计算当前 Java 堆使用率，当使用率超过阈值（如 80%）时触发 Dump。Dump 出的 Hprof 文件会在客户端进行裁剪——KOOM 实现了一套高效的 Hprof 文件解析和裁剪机制，能够只保留泄漏分析所需的关键数据（如 GC Root 引用链），将文件大小压缩到原来的 10%~20%。

一个关键优化是：KOOM 使用了 Fork 子进程来执行 Hprof Dump，避免在主进程中执行耗时的 Dump 操作导致卡顿或 ANR。这在 Perfetto 中的体现是：Dump 期间主线程不会出现长时间的阻塞，用户感知不到监控本身的存在。

[已验证: github.com/KwaiAppTeam/KOOM]

### Native 堆泄漏检测

KOOM 的 Native 泄漏检测模块（koom-native-leak）采用了与 Android 系统内置的 libmemunreachable 类似的方案，但做了工程化封装。它的核心原理分三步：

第一步是**Hook 内存分配器**。KOOM 通过 PLT Hook 拦截 malloc、free 等函数，记录每次 Native 内存分配的元数据：分配地址、大小和调用栈。

第二步是**Mark-and-Sweep 扫描**。KOOM 定期对整个进程的 Native 堆执行一次标记-清除（Mark-and-Sweep）分析。它会遍历进程内存中所有可达的指针，将它们指向的内存块标记为"可达"；未被标记的内存块就是"不可达"的——这些就是泄漏候选者。

第三步是**调用栈回溯**。利用检测到的不可达内存块的地址和大小，KOOM 从之前记录的分配元数据中回溯其分配时的调用栈，生成包含泄漏地址、大小和分配调用栈的报告。

这个模块支持 Android N（API 24）及以上版本，仅支持 arm64-v8a 架构。

[已验证: github.com/KwaiAppTeam/KOOM, L2 交叉验证]

### 线程泄漏检测

KOOM 还提供了线程泄漏检测能力。它通过 Hook pthread_create 和 pthread_exit，记录线程的创建和退出。如果一个线程在创建后长时间没有退出（超过可配置的阈值），且线程栈中看不到有意义的业务逻辑（比如卡在 Object.wait 或 nativePollOnce），KOOM 会将其标记为疑似泄漏线程。线程泄漏在生产环境中经常被忽视，但它占用的不仅是内存（每个线程默认 1MB 栈空间），还有文件描述符和调度资源。线上使用时通常还要配合线程白名单、业务线程命名规范或常驻线程标记，先过滤掉 Binder 线程池、线程池 worker、监控线程这类预期长期存活的线程，避免误报。

[待验证: KOOM 线程泄漏模块的线上稳定性表现]

## Booster：滴滴的编译期优化框架

前面两个工具都是运行时监控方案，Booster 走的是编译期路线。Booster 是滴滴团队开源的 Gradle 插件框架，经典实现建立在 Transform API 这一代 AGP 扩展点上，在 .class 转 .dex 之前对字节码做扫描和改写。理解这条历史路径，有助于判断它在新旧 AGP 版本里的兼容性边界。

### Transform API 的工作位置

要理解 Booster，我们先要知道它在构建流程中的位置。Android 应用的构建流程大致是：源码 → Java/Kotlin 编译 → .class 文件 → **Transform 阶段** → .dex 文件 → APK 打包。Booster 就工作在 Transform 阶段，拿到所有 .class 文件后、生成 .dex 之前。

因此，Booster 能做的事情非常广泛：它可以看到整个应用的字节码，可以做静态分析、代码注入和代码优化。而且这些操作都在编译期完成，对运行时性能没有额外开销。

[已验证: github.com/didi/Booster]

### Booster 的主要优化能力

Booster 的功能以模块化形式提供，我们可以按需引入。

**性能检测模块**通过静态分析所有 .class 文件构建全局调用图（Call Graph），找出在主线程调用了 I/O 操作、SharedPreferences 读写、网络请求等可能阻塞的 API。它生成可视化报告帮助我们快速定位问题代码。这和 Trace Canary 的运行时检测形成互补——Trace Canary 发现的是实际发生了的卡顿，Booster 发现的是潜在可能卡顿的代码。

**资源索引内联与常量清除**模块针对的是 Android 构建系统中一个经典的冗余问题。编译后，R 类（如 R.id.xxx、R.layout.xxx）其实就是一组 static final int 常量。运行时访问这些字段需要一次字段查找（虽然 JIT 会优化，但首次访问仍有开销）。Booster 直接将这些字段访问替换为字面值常量，并从类中删除不再需要的常量字段，既减少了包体积，也略微提升了运行时性能。

**系统 Bug 修复**模块展现了编译期优化的另一个优势。比如 Android API 25 中 Toast 的 BadTokenException 问题（在 Toast.show() 时如果 NotificationManagerService 还未来得及处理，会抛出异常导致崩溃）。Booster 通过字节码注入，在所有 Toast.show() 调用前后包裹 try-catch，一次性解决全局问题，而不需要每个调用点手动处理。

**多线程优化**模块针对第三方 SDK 滥建线程的问题。很多 SDK 在初始化时会 new Thread() 或使用 Executors 创建线程池，如果集成多个 SDK，线程数可能快速膨胀。Booster 可以将这些线程创建重定向到统一的线程池管理器。

[已验证: github.com/didi/Booster, L2 交叉验证]

### Booster 的局限性

Booster 基于 Transform API 的经典方案也有局限。Transform API 在 AGP 7.x 已经进入废弃阶段，到了 AGP 8.0 被彻底移除。旧版 Booster 或自研 Transform 插件在 AGP 8.0+ 环境下会直接失去接入点，继续做同类字节码改写需要迁移到 Instrumentation API 的 `AsmClassVisitorFactory`，以及处理产物编排的 Artifacts API。另一个限制是编译期分析无法覆盖运行时行为，Booster 能发现“这段代码在主线程调用了 I/O”，但无法判断“这个 I/O 在实际运行中到底耗时多久”。

[已验证: AGP 8.0 Release Notes，Booster 的兼容性边界仍要看具体版本或 fork]

## 启动优化框架：Anchors、AppInit 与任务调度

启动优化领域的三方库走的是另一条路线：它们不检测问题，而是提供一套框架来帮助我们组织和管理启动任务，减少冷启动耗时。

### 核心思路：有向无环图（DAG）调度

大型 App 的 Application.onCreate() 和首个 Activity 的生命周期中往往要执行几十个初始化任务：SDK 初始化、数据预加载、组件注册、路由表构建等等。如果全部串行执行，启动时间会非常长。这些任务之间存在依赖关系（比如路由表初始化必须在页面跳转之前完成），但也有大量任务之间没有依赖，完全可以并行。

启动优化框架的核心思路是：将启动任务声明为节点，将依赖关系声明为边，构建一张有向无环图（DAG）。框架在运行时对 DAG 进行拓扑排序，找出哪些任务可以并行执行，按照依赖关系和优先级调度到线程池中。

[已验证: L2 交叉验证多个开源框架（Alpha、Anchors、AppInit）]

### 典型框架对比

**Alpha**（阿里巴巴开源）是最早广为人知的启动调度框架。它支持任务依赖声明、优先级设置、线程池配置。使用方式是继承 Task 类实现具体任务，通过 Task.Builder 构建依赖关系图。Alpha 的不足在于：它已经停止维护，API 设计比较早期，不支持 Kotlin DSL。

**Anchors** 是一个更轻量的方案，专注于"锚点"概念——即在特定时机必须完成的任务。比如"在 Activity.onCreate 之前必须完成路由表初始化"。它通过声明锚点来划分启动阶段，每个阶段内的任务并行执行，阶段之间按序串行。

**AppInit** 采用注解驱动的方式，通过 @AppInit 注解标记初始化方法，编译期自动收集所有初始化方法并生成调度代码。它的优势是接入成本低——只需要加注解，不需要手动构建依赖图。但灵活性相应较低，复杂依赖关系不如编程式 API 好控制。

在实际项目中，选择哪个框架不如理解背后的设计原则重要：**任务颗粒化、依赖显式化、并行最大化、监控可量化**。即使不引入三方框架，团队也应该按这个思路组织自己的启动任务。

[待验证: 各框架的最新维护状态]

## 扩展：Rhea / btrace —— 字节跳动的 Trace 工具

Rhea 是字节跳动在 Trace 工具上的一条演进线，后续以 `btrace` 项目的形式完全开源。它基于 Perfetto 生态，支持 Android 和 iOS，适合用来理解函数级 Trace 工具在真实业务里的工程化演进。

### 从 Systrace 到 Rhea 的三阶段演进

抖音团队在性能优化过程中经历了三个 Trace 工具阶段，这个演进过程很值得我们了解。

**第一阶段是 Systrace + 自动插桩**。Rhea 1.0 通过字节码插桩自动在每个方法的入口和出口插入 Trace.beginSection / Trace.endSection 调用，并限制方法层级来控制性能开销。但实测发现性能损耗约 11.5%——原因有两个：一是 Systrace 的所有线程向同一个 trace_marker 文件写入时竞争内核态 pos 锁，导致大量 Uninterruptible Sleep；二是限制层级导致超过层级的方法调用信息缺失。

**第二阶段是自研 Method Trace**。Rhea 2.0 摒弃了 Systrace，改为在 Java 层记录方法的首末时间戳，异步写入文件，然后转换为 Systrace 可视化格式。性能损耗从 11.5% 降到了约 3%。但它只能覆盖 Java 方法级信息，无法看到锁等待、I/O 耗时、Binder 调用等系统级行为。

**第三阶段是动态一体化 Trace**。Rhea 3.0 放弃了前面的方案，重新设计了一套完整架构：不限层级插桩获取函数耗时 + Hook atrace_marker_fd 拦截用户态 Trace + Hook libc 的 open/read/write/fsync 收集 I/O 信息 + Hook libbinder.so 的 IPCThreadState.transact 收集 Binder 耗时 + 运行时动态打开 ART 虚拟机的轻锁日志。最终将用户态 atrace 和内核态 ftrace 合并为一个完整的 Trace 文件，兼容 Systrace/Perfetto 可视化格式。

Rhea 的一个关键优化是将直接写入内核态 trace_marker 文件的 Trace 在用户态拦截、缓存，再异步转储。这避免了大量线程同时向同一文件写入导致的 pos 锁竞争问题。这个问题在实际优化中很容易误导方向，因为工具本身的性能开销会表现为 I/O Wait。开源后的 btrace 3.0 又补了同步采样模式，用更低的持续开销换取函数级时序观测能力，更适合长时间抓取。

[来源: Cubox/抖音 Android 性能优化系列：新一代全能型性能分析工具 Rhea]

[已验证: Rhea 后续以 btrace 形式完全开源，3.0 版本补充了同步采样等新能力]

## 扩展：Hook 机制对比

上面提到的工具大量使用了 Hook 技术，但 Hook 方案之间有本质区别。理解这些区别有助于我们在评估工具时判断其适用范围和稳定性风险。

### PLT Hook（以 xHook 为代表）

PLT Hook 的工作对象是 ELF 文件中的 .got（Global Offset Table）。当我们的代码调用外部函数时（比如调用 libc.so 的 open），实际是通过 .plt → .got 的间接跳转。.got 中存储了目标函数的实际地址。PLT Hook 就是修改 .got 中的函数指针，将其指向我们的 Hook 函数。

这种方案的优势是：不修改目标函数的机器码，只修改一个指针，兼容性和稳定性较好。xHook 经过爱奇艺在多个产品中的验证，支持 armeabi、armeabi-v7a 和 arm64-v8a，支持 Android 4.0+。劣势是：只能 Hook 通过 .got 进行的间接调用，无法 Hook 同一 ELF 内部函数之间的直接调用。

Matrix 的 IO Canary、KOOM 的内存分配 Hook 都使用了 PLT Hook 方案。

[来源: Cubox/xHook PLT Hook 概述]

### Inline Hook

Inline Hook 直接修改目标函数的机器码（通常是将函数入口处的几条指令替换为跳转指令），将执行流导向 Hook 函数。这种方式理论上可以 Hook 任何函数调用，包括 ELF 内部的直接调用。

优势是覆盖范围广，理论上无 Hook 盲区。劣势是：需要处理不同 CPU 架构的指令差异（ARM、ARM64、x86 等），兼容性风险高；如果目标函数很短（短于一条跳转指令的长度），可能无法 Hook；在多线程环境下修改代码段存在竞态条件。字节跳动在开源生态里把这两条路线拆得很清楚：`ByteHook` 是 PLT Hook 库，`ShadowHook` 才是 Inline Hook 库。分析字节系方案时，先区分自己看到的是 ELF 导入表拦截，还是函数入口改写。两者的稳定性边界和适用场景不同。

[已验证: bytedance/bhook 为 PLT Hook，bytedance/android-inline-hook 为 ShadowHook Inline Hook]

### Transform（编译期字节码修改）

Booster 使用的 Transform 属于编译期方案。它在 .class 文件阶段对字节码进行修改，修改后的代码直接编译进 APK 中。

优势是零运行时开销——修改在编译期完成，运行时不存在任何 Hook 成本。劣势是只能在编译期看到静态信息，无法根据运行时状态做动态决策。

## 工具选型指南

理解了每个工具的原理之后，实际项目里可以按下面几个场景选择和组合使用。

### 按场景选择

**线上性能监控**需要 Matrix 或 KOOM 这类运行时方案。如果我们的核心关注点是卡顿和 ANR，Matrix 的 Trace Canary 是最成熟的选择。如果内存问题（特别是 Native 泄漏和线程泄漏）是主要矛盾，KOOM 的覆盖范围更广。很多团队的做法是同时接入两者——Matrix 负责卡顿/ANR/IO 监控，KOOM 负责内存监控。

**编译期预防**需要 Booster。它在每次构建时自动扫描潜在问题，不依赖线上数据就能发现问题。特别是对第三方 SDK 的行为约束（线程数控制、主线程 I/O 检测），Booster 在编译期就能拦截。

**启动任务管理**可以用 Anchors / AppInit 等调度框架。重点还是把 DAG 调度的思路落到任务拆分和依赖编排上，而不是绑定某个具体框架。如果项目规模不大，完全可以自建一个轻量的任务调度器。

**线下深度 Trace**中 Perfetto 仍然是首选，Rhea 的价值在于：当我们需要在真实用户环境中远程抓取 Trace（比如灰度用户反馈的特定场景卡顿），Rhea 可以不依赖 PC、不依赖 adb 就在 App 侧完成 Trace 抓取。

[自动发现]

### 组合使用的注意事项

同时接入多个性能库时，通常会遇到三类额外成本。

一是**性能开销叠加**。每个运行时监控工具都有一定的性能开销（Matrix 约 2~5%，KOOM 的 Native Hook 也有少量开销），多个工具叠加后，低端机更容易出现用户可感知的卡顿。通常的做法是对监控工具本身做采样，只对部分用户开启完整监控。

二是**Hook 冲突**。如果 Matrix 和 KOOM 都 Hook 了 libc 的 open/write，可能出现 Hook 链冲突。实际上 xHook 本身支持 Hook 链（多个 Hook 函数按序执行），但不同工具使用不同的 Hook 库时可能冲突。建议统一使用同一个底层 Hook 库。

三是**上报数据整合**。多个工具各自上报数据到各自的平台，分析问题时需要跨平台关联。理想情况是建设统一的 APM 平台，将卡顿、内存、I/O 等数据关联到同一个用户会话上。

## 常见问题与误区

**"Matrix 是万能的，接了就不用 Perfetto 了"**。Matrix 解决的是线上监控问题，Perfetto 解决的是线下深度分析问题。两者定位不同，互相不可替代。Matrix 能告诉你"用户 A 在某次操作中发生了卡顿，调用栈是 XXX"，但要理解为什么会走到这条代码路径、整个渲染管线当时的状态如何，还是需要 Perfetto Trace。

**"KOOM 的 Native 泄漏检测可以替代 ASan"**。KOOM 的 Mark-and-Sweep 方案是"不精确"的——它只能检测到"不可达"的内存块，但"不可达"不等于"泄漏"（某些长期存活的内存块可能在扫描瞬间没有被任何栈变量引用）。AddressSanitizer (ASan) 是更精确的工具，但它需要特殊编译且开销大，不适合生产环境。KOOM 适合生产环境的持续监控，ASan 适合开发阶段的问题定位。

**"Booster 的 Transform API 已经过时了"**。Transform API 在 AGP 8.0 已经被移除，旧版基于 Transform 的 Booster 方案不能直接带到新的构建流程里。编译期优化本身还有效，只是接入点换成了 Instrumentation API 和 Artifacts API。

**"启动框架能自动优化启动速度"**。启动调度框架只是帮你更好地组织任务——把可以并行的任务并行化、把非关键路径的任务延迟化。它本身不会让任何单个任务执行得更快。如果每个初始化任务本身就很慢，用了框架也不会有质的变化。优化启动的根本还是减少启动路径上的工作量。

## 参考资料

- Matrix GitHub: https://github.com/Tencent/matrix
- KOOM GitHub: https://github.com/KwaiAppTeam/KOOM
- Booster GitHub: https://github.com/didi/Booster
- xHook GitHub: https://github.com/iqiyi/xHook
- ByteHook GitHub: https://github.com/bytedance/bhook (字节跳动 PLT Hook)
- ShadowHook GitHub: https://github.com/bytedance/android-inline-hook (字节跳动 Inline Hook)
- btrace GitHub: https://github.com/bytedance/btrace
- 抖音 Android 性能优化系列：Rhea Trace 工具: https://mp.weixin.qq.com/s/vkBeZ6hmVn_RaXS5Xv_L2g
- Android PLT Hook 概述（xHook 文档）: https://github.com/iqiyi/xHook/blob/master/docs/overview/android_plt_hook_overview.zh-CN.md
- Alpha 启动调度框架: https://github.com/alibaba/alpha
