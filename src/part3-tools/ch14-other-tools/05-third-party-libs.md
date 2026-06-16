---
title: "三方性能库"
chapter: "14.5"
section: "14.5"
status: finalized
drafted_date: "2026-04-03"
drafted_by: "openclaw-task2a"
applicable_versions: "Android 5.0 (API 21) - Android 16 (API 36)"
last_verified: "2026-06-17"
last_verified_against: "external review + GitHub upstream READMEs + AndroidX/AGP docs + bytedance/btrace 3.0 README/INTRODUCTION"
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
  - type: blog
    path: "https://github.com/square/leakcanary (Square LeakCanary)"
  - type: blog
    path: "https://github.com/bytedance/btrace (字节 btrace / RheaTrace)"
  - type: official
    path: "https://firebase.google.com/docs/perf-mon (Firebase Performance Monitoring)"
  - type: blog
    path: "https://github.com/measure-sh/measure (Measure)"
  - type: blog
    path: "https://github.com/didi/DoKit (滴滴 DoKit)"
  - type: blog
    path: "https://github.com/markzhai/AndroidPerformanceMonitor (BlockCanary)"
  - type: blog
    path: "https://github.com/SusionSuc/rabbit-client (Rabbit)"
tags:
  - android
  - research
  - apm
  - observability
  - tracing
related_chapters:
  - "14.12"
  - "14.13"
  - "15.5"
  - "15.9"
pipeline_stage: task6_pending
task6_state: revisiting
review_round: 4
task9_state: reviewed
task9_result: auto-fixed
task9_reviewed_date: "2026-05-28"
task9_reviewed_by: openclaw-task9
last_task9_at: "2026-06-17T05:27:45+08:00"
task2b_state: fixed
reviewed_by: openclaw-task6
reviewed_date: "2026-05-28"
task6_result: pass-light-edit
last_task6_at: "2026-05-28T19:05:00+08:00"
last_task6_review_log: "logs/review/2026-05-28-19-review.md"
last_task6_audit: "2026-05-22"
task2b_result: fixed
last_task2b_at: "2026-05-28T18:50:00+08:00"
repaired_date: "2026-05-28"
repaired_by: "openclaw-task2b"
last_task9_audit: "2026-06-17"
last_task9_review_log: "logs/deep-review/2026-05-28-19-deep-review.md"
task9_review_notes: "2026-05-28 Task9 deep review: pass-tech-review; no P0/P1; P2 suggestions written to intake/suggestions.md; auto-promoted finalized. 2026-06-17 Task9 idle audit: AUTO-FIX btrace 3.0 Android capability boundary; current open-source path requires PC/adb and online support is roadmap; added Android 8+/64-bit/Android 15 allocation-monitor limits; return to Task6 revisiting."
last_task9_autofix_at: "2026-06-17"
last_task9_audit_log: "logs/deep-review/2026-06-17-05-audit.md"
---


# 三方性能库

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 Matrix（微信）：Trace Canary、Resource Canary、IO Canary 等
- 🔹 KOOM（快手）：Java/Native 内存泄漏检测
- 🔹 Booster（滴滴）：编译期优化插件
- 🔹 Anchors / AppInit 等启动优化框架
- 🔹 LeakCanary、btrace、Firebase Performance、Measure、DoKit 的定位差异
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

## 为什么这一章值得单独写

官方工具已经很强了。Perfetto、Simpleperf、Profiler 这些能力，足够把很多问题看得很深。那为什么还要讲三方性能库？

因为真实工作里，很多问题发生在线上版本、灰度用户、复杂设备分布里。官方工具擅长把问题看透，三方库更擅长把问题先感知到、保留住、或者提前拦下来。两者在不同位置上各有分工。

这一章要回答的是：**什么场景下需要借助三方能力，它们各自补的是哪一块空白。**

## 先按层看，不要先按库名看

一上来就列库名，读者很容易只记住“Matrix、KOOM、LeakCanary、btrace”。这样很难记住工具和问题之间的对应关系。更稳的方式，是先把它们放回各自所在的层。

| 层次 | 代表方案 | 更接近什么 |
|---|---|---|
| **官方基础能力** | JankStats、FrameMetrics、ApplicationExitInfo | 指标与系统回调，不是完整 APM |
| **客户端 SDK / 组件** | Matrix、KOOM、LeakCanary、btrace、DoKit、BlockCanary、Rabbit | 在 App 里负责采集或研发诊断 |
| **平台 / 可观测性方案** | Firebase Performance、Measure | 聚合、展示、分析、告警 |

先把层次分清楚，后面的选型才不会变成“哪个名字更响就接哪个”。

## Matrix：最像“客户端 APM 框架”的方案

Matrix 是腾讯微信团队开源的 Android 性能监控框架。它的价值在于把客户端常见的性能监控问题组织成了一套相对统一的框架。

### 整体架构

Matrix 的设计目标是低侵入接入，覆盖从采集到上报的完整监控流程。它通过 Gradle 插件在编译期完成字节码插桩，运行时通过 Hook 收集各类性能数据，最终将数据上报到监控平台。整个框架分为五个核心模块：

- **Trace Canary**：卡顿、ANR、启动耗时、帧率监控
- **Resource Canary**：Activity 泄漏检测、冗余 Bitmap 检测（Fragment 泄漏支持取决于具体分支和版本，上游主干公开能力以 Activity leak + duplicated bitmap 为核心；若项目需要 Fragment 级泄漏监控，需确认使用的分支是否包含 `FragmentLifecycleCallbacks` 注册逻辑和对应的 watcher 实现）
- **IO Canary**：文件 I/O 性能问题检测、Closeable 泄漏监控
- **SQLiteLint**：SQLite 使用规范检测
- **Battery Canary**：耗电行为监控

[已验证: 官方文档, github.com/Tencent/matrix]

### Trace Canary：卡顿与 ANR 的精准定位

Trace Canary 的核心能力是检测卡顿、慢函数、ANR、启动耗时和帧率异常。它的工作原理可以分两层来看。

第一层是**编译期插桩**。Trace Canary 会在编译阶段对应用字节码做方法级改写，在每个方法的入口和出口插入计时逻辑。这种插桩是选择性的，可以按包名、类名或白名单限制范围，控制运行时开销。插桩后的代码会在方法执行时记录起止时间戳和调用堆栈。公开上游长期保留的是 Transform 路径；截至 2025 Q1，Tencent/matrix 官方插件还没有发布面向 AGP 8.0+ 的正式可用版本。AGP 8.0 起 `android.registerTransform` 已移除，使用 AGP 8.0+ 的项目不要把 Matrix 官方插件视为可直接接入的选项。可执行路线只有两类：使用已经迁移到 Android Components instrumentation 管线且经过团队验证的 fork；或自行把 `MatrixTraceTransform` 迁到 `variant.instrumentation.transformClassesWith(...)` / `AsmClassVisitorFactory`，再按需配合 Artifacts API 处理产物。迁移验证至少覆盖 Debug/Release、R8、增量编译和多模块场景。

第二层是**运行时检测**。Trace Canary 监听主线程的 Looper 消息分发和 Choreographer 的 doFrame 回调。当一个 Message 的执行耗时超过阈值（比如默认 700ms），或者一帧的渲染超过 16.6ms 导致连续掉帧，它就会触发上报逻辑。对于 ANR 检测，Trace Canary 提供两种方式：LooperAnrTracer 在主线程 Message 开始执行时设置一个 5 秒超时（类似"埋炸弹"），如果超时触发则判定为 ANR；SignalAnrTracer 则通过捕捉系统发出的 SIGQUIT 信号来检测。

在实际分析中，我们可以通过 Trace Canary 的上报数据看到：触发卡顿的具体方法、完整的调用堆栈、该方法的执行耗时以及执行次数。这比在 Perfetto 中逐帧查看 Trace 要高效得多，特别是在线上环境中。

[已验证: Matrix 上游仍可见 `MatrixTraceLegacyTransform` 等 Transform 路径；公开 issue #888 记录 AGP 8.x 下 `android.registerTransform` 已移除；AGP 8.0+ 字节码改写需迁移到 Android Components instrumentation API / `AsmClassVisitorFactory`]

### Resource Canary：内存泄漏与冗余 Bitmap

Resource Canary 采用弱引用（WeakReference）机制来检测 Activity 的泄漏（上游公开的监听入口主要是 `ActivityLifecycleCallbacks`，对应 `DestroyActivityLifecycleListener` 在 `onActivityDestroyed` 回调中执行入队）。它的做法是：将已销毁的 Activity 实例包装成弱引用并存入观察队列，然后定期触发 GC 并轮询检查队列中的弱引用是否已被回收。如果在多次检查后仍然存活，就认为发生了泄漏。Fragment 泄漏检测不在上游主干的默认路径中，Matrix 上游公开能力主要是 Activity leak 与 duplicated bitmap；如果团队需要 Fragment 级别监控，需要确认使用的 fork 是否自行注册了 `FragmentManager.FragmentLifecycleCallbacks` 并实现了对应的弱引用追踪。

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

## KOOM：把内存问题单独拉出来处理

KOOM（Kwai OOM）是快手团队开源的内存监控方案。它最适合解决已经明确落在内存侧的问题。相比 Matrix 的 Resource Canary，KOOM 更像一个专项治理工具。

### Java 堆泄漏检测

KOOM 的 Java 堆泄漏检测采用"阈值触发 + Hprof 裁剪"的方案。它通过 Runtime.totalMemory() 和 maxMemory() 计算当前 Java 堆使用率，当使用率超过阈值（如 80%）时触发 Dump。Dump 出的 Hprof 文件会在客户端进行裁剪——KOOM 实现了一套 Hprof 文件解析和裁剪机制，只保留泄漏分析所需的关键数据（如 GC Root 引用链、必要对象记录和 bitmap buffer 相关信息）。公开 README 与源码能支撑“裁剪后再上报”这个机制，但具体压缩比例要看堆内容、bitmap 占比和裁剪策略，线上文档里不应写成固定 10%~20%。

一个关键优化是：KOOM 使用了 Fork 子进程来执行 Hprof Dump，避免在主进程中执行耗时的 Dump 操作导致卡顿或 ANR。
<!-- AIW-源码调研-2026-05-08 -->
> **深度研究补充**：KOOM FastDump 的 Suspend-Fork-Resume 机制有更完整的源码级分析，见 [[DeepResearch/2026-05-08-koom-fastdump-suspend-fork-resume-mechanism|2026-05-08: KOOM FastDump Suspend-Fork-Resume 机制]]。核心发现：主进程冻结 <20ms 依赖 Suspend VM → fork → Resume 三步；koom-fast-dump.so（闭源）是核心实现，hprof_dump.cpp 等 6 个 native 源文件构建该 so；OOMMonitor 组合 5 个 OOMTracker（HeapOOMTracker/ThreadOOMTracker/FdOOMTracker/PhysicalMemoryOOMTracker/FastHugeMemoryOOMTracker）；hprof_strip.cpp 直接解析 Hprof 二进制格式裁剪 system heap，体积减少 50-70%。
这在 Perfetto 中的体现是：Dump 期间主线程不会出现长时间的阻塞，用户感知不到监控本身的存在。

[已验证: github.com/KwaiAppTeam/KOOM]

### Native 堆泄漏检测

KOOM 的 Native 泄漏检测模块（koom-native-leak）采用了与 Android 系统内置的 libmemunreachable 类似的方案，但做了工程化封装。它的核心原理分三步：

第一步是**Hook 内存分配器**。KOOM 通过 PLT Hook 拦截 malloc、free 等函数，记录每次 Native 内存分配的元数据：分配地址、大小和调用栈。

第二步是**Mark-and-Sweep 扫描**。KOOM 定期对整个进程的 Native 堆执行一次标记-清除（Mark-and-Sweep）分析。它会遍历进程内存中所有可达的指针，将它们指向的内存块标记为"可达"；未被标记的内存块就是"不可达"的——这些就是泄漏候选者。

第三步是**调用栈回溯**。利用检测到的不可达内存块的地址和大小，KOOM 从之前记录的分配元数据中回溯其分配时的调用栈，生成包含泄漏地址、大小和分配调用栈的报告。

这个模块支持 Android N（API 24）及以上版本，仅支持 arm64-v8a 架构。

[已验证: github.com/KwaiAppTeam/KOOM, L2 交叉验证]

### 线程泄漏检测

KOOM 还提供了线程泄漏检测能力。这里的“泄漏”分两类：线程长时间存活；POSIX 默认 joinable 线程已经退出、但没有被 `pthread_join()` 或 `pthread_detach()` 回收。joinable 线程结束后仍会保留线程描述符、栈等 native 资源，数量累积后会推高 native 内存和线程相关资源占用。KOOM ThreadLeakMonitor 通过 Hook `pthread_create`、`pthread_exit` 并跟踪 join/detach 状态，识别长时间存活的线程和退出后未回收的 joinable 线程。

官方 README 给这个模块的适用范围很窄：只支持 Android N（API 24）及以上，只支持 `arm64-v8a`。它不适合直接覆盖 Android 5/6 或 32 位设备。线上使用时通常还要配合线程白名单、业务线程命名规范或常驻线程标记，先过滤掉 Binder 线程池、线程池 worker、监控线程这类预期长期存活的线程，避免误报。

[已验证: KwaiAppTeam/KOOM koom-thread-leak README, Scope: Android N+ / arm64-v8a]

## Booster：把问题尽量拦在编译期

前面几个工具更多在运行时工作，Booster 走的是另一条路：尽量在编译期就把问题扫出来，或者把优化提前做掉。它是一种编译期治理方案，和前面几个运行时工具的定位完全不同。

### Transform API 的工作位置

要理解 Booster，我们先要知道它在构建流程中的位置。Android 应用的构建流程大致是：源码 → Java/Kotlin 编译 → .class 文件 → **Transform 阶段** → .dex 文件 → APK 打包。Booster 就工作在 Transform 阶段，拿到所有 .class 文件后、生成 .dex 之前。

Booster 能做的事情非常广泛：拿到整个应用的字节码后，可以做静态分析、代码注入和代码优化。这些操作都在编译期完成，对运行时性能没有额外开销。

[已验证: github.com/didi/Booster]

### Booster 的主要优化能力

Booster 的功能以模块化形式提供，我们可以按需引入。

**性能检测模块**通过静态分析所有 .class 文件构建全局调用图（Call Graph），找出在主线程调用了 I/O 操作、SharedPreferences 读写、网络请求等可能阻塞的 API。它生成可视化报告帮助我们快速定位问题代码。这和 Trace Canary 的运行时检测形成互补——Trace Canary 发现的是实际发生了的卡顿，Booster 发现的是潜在可能卡顿的代码。

**资源索引内联与常量清除**模块针对的是 Android 构建系统中一个经典的冗余问题。在 AGP 7.x 及更早版本中，编译后 R 类（如 R.id.xxx、R.layout.xxx）是一组 `static final int` 常量。运行时访问这些字段需要一次字段查找（虽然 JIT 会优化，但首次访问仍有开销）。Booster 直接将这些字段访问替换为字面值常量，并从类中删除不再需要的常量字段，既减少了包体积，也略微提升了运行时性能。

**AGP 8.0+ 的 R 字段变更**：AGP 8.0 起 `android.nonFinalResIds` 和 `nonTransitiveRClass` 默认开启，应用模块的 R 字段不再是 `static final`——编译器会为每个资源 ID 生成 `static int`（非 final）的内联赋值。因此，Booster 原有的"把 R 字段访问替换为字面值"的前提（字段是 final 常量）在 AGP 8.0+ 默认配置下不再成立。使用 Booster 这类优化时需要确认项目仍在使用旧版 AGP 或已手动关闭 `nonFinalResIds`；对于 AGP 8.0+ 项目，该优化的收益和适用条件需要重新评估，Booster 官方或 fork 是否已适配 non-final R 字段也需要验证。

**系统 Bug 修复**模块展现了编译期优化的另一个优势。比如 Android API 25 中 Toast 的 BadTokenException 问题（在 Toast.show() 时如果 NotificationManagerService 还未来得及处理，会抛出异常导致崩溃）。Booster 通过字节码注入，在所有 Toast.show() 调用前后包裹 try-catch，一次性解决全局问题，而不需要每个调用点手动处理。

**多线程优化**模块针对第三方 SDK 滥建线程的问题。很多 SDK 在初始化时会 new Thread() 或使用 Executors 创建线程池，如果集成多个 SDK，线程数可能快速膨胀。Booster 可以将这些线程创建重定向到统一的线程池管理器。

[已验证: github.com/didi/Booster, L2 交叉验证]

### Booster 的局限性

Booster 基于 Transform API 的经典方案也有局限，但不能简单等同为“AGP 8 后都不可用”。当前 didi/Booster README 的兼容表写得更细：

| 构建环境 | Booster 选择 | 迁移判断 |
|---|---|---|
| AGP 7.x 及以下 | Booster 4.x | 继续使用 4.x 线，不升级到 Booster 5.x |
| AGP 8.0 / 8.1 / 8.2 | Booster 5.0.0+ | 5.x 线面向 AGP 8；README 说明大多数 Task based modules 不再支持，但 Transform based modules 在 5.x 中仍 supported without breaking changes |
| AGP 8.3 / 8.4 / 8.5 | N/A | README 兼容表未给可用 Booster 版本，接入前需要验证 fork 或替代方案 |

因此，正确的迁移判断是按 AGP 与 Booster 双版本一起看：AGP 8.0 移除了 Android Gradle Plugin 原有 `registerTransform` 接口，但 Booster 5.x 已把一部分 Transform based modules 留在 8.0-8.2 的兼容范围内；AGP 8.3+ 则不能按旧经验假设可用。自研字节码改写继续往后迁移时，应优先评估 Android Components instrumentation API 的 `AsmClassVisitorFactory`，以及 Artifacts API 对产物编排的影响。另一个限制是编译期分析无法覆盖运行时行为，Booster 能发现“这段代码在主线程调用了 I/O”，但无法判断“这个 I/O 在实际运行中到底耗时多久”。

[已验证: didi/Booster README compatibility table + 5.x migration notes]

## 启动优化框架：组织启动阶段的任务依赖

启动优化框架和前面的监控库定位不同。它们负责把启动阶段的任务组织得更清楚，减少串行依赖和不必要的阻塞。

### 核心思路：有向无环图（DAG）调度

大型 App 的 Application.onCreate() 和首个 Activity 的生命周期中往往要执行几十个初始化任务：SDK 初始化、数据预加载、组件注册、路由表构建等等。如果全部串行执行，启动时间会非常长。这些任务之间存在依赖关系（比如路由表初始化必须在页面跳转之前完成），但也有大量任务之间没有依赖，完全可以并行。

启动优化框架的核心思路是：将启动任务声明为节点，将依赖关系声明为边，构建一张有向无环图（DAG）。框架在运行时对 DAG 进行拓扑排序，找出哪些任务可以并行执行，按照依赖关系和优先级调度到线程池中。

[已验证: L2 交叉验证多个开源框架（Alpha、Anchors、AppInit）]

### 典型框架对比

**Alpha**（阿里巴巴开源）是最早广为人知的启动调度框架。它支持任务依赖声明、优先级设置、线程池配置。使用方式是继承 Task 类实现具体任务，通过 Task.Builder 构建依赖关系图。Alpha 的不足在于：它已经停止维护，API 设计比较早期，不支持 Kotlin DSL。

**Anchors** 是一个更轻量的方案，专注于"锚点"概念——即在特定时机必须完成的任务。比如"在 Activity.onCreate 之前必须完成路由表初始化"。它通过声明锚点来划分启动阶段，每个阶段内的任务并行执行，阶段之间按序串行。

**AppInit** 采用注解驱动的方式，通过 @AppInit 注解标记初始化方法，编译期自动收集所有初始化方法并生成调度代码。它的优势是接入成本低——只需要加注解，不需要手动构建依赖图。但灵活性相应较低，复杂依赖关系不如编程式 API 好控制。

在实际项目中，选择哪个框架不如理解背后的设计原则重要：**任务拆细、依赖显式化、并行最大化、监控可量化**。即使不引入三方框架，团队也应该按这个思路组织自己的启动任务。

[待验证: 各框架的最新维护状态]

## 再补几类经常被漏掉的工具

### LeakCanary：本地泄漏排查工具

`LeakCanary` 是开发和测试阶段最实用的内存泄漏分析工具之一。它最大的价值是能在本地把对象引用链解释得非常清楚。

放到这本书里，最好把它和 `KOOM` 分开写：

- `LeakCanary`：更偏本地调试和研发自查
- `KOOM`：更偏线上内存治理和生产环境取证

这两者是互补，不是互斥。

[已验证: github.com/square/leakcanary]

### Firebase Performance：接入成本较低的平台型方案

`Firebase Performance Monitoring` 的优点是接入成本低、启动 / 渲染 / HTTP 监控开箱即用，适合快速建立“线上能看到一些性能指标”的基础能力。它的边界也很明显：对复杂归因、私有化部署、自定义 trace 流程的控制不如自建方案灵活。

在本章里，它更适合被当成“平台型 APM”的典型代表，而不是和 `Matrix`、`KOOM` 按同一种维度比较。

[已验证: firebase.google.com/docs/perf-mon]

### Measure：更完整的平台视角

`Measure` 的价值在于它不只是一个客户端 SDK，而是一整套以 session timeline 为中心的移动可观测性平台：把点击、导航、HTTP、log、crash、ANR 和 trace 放进同一个会话视角里。

对已经跨过“只想看单项指标”的团队来说，这类平台更接近完整的线上性能治理方案。

[已验证: github.com/measure-sh/measure]

### DoKit：更像研发工具箱

`DoKit` 的覆盖面很广，FPS、启动耗时、网络、沙盒浏览、各种研发辅助能力都在里面。它对开发和测试现场有价值，定位更接近“本地研发工具箱”；生产环境的大规模线上 APM 采样、聚合、告警不应依赖它。2024-2025 年间，DoKit 云端服务和官网维护状态不稳定，依赖 `www.dokit.cn` 的 Mock、数据看板等能力不应作为团队长期方案；离线可用的设备侧工具更值得保留。

把它和 `Firebase Performance`、`Measure` 完全写成同一类工具，会让读者误判其使用场景。

[已验证: github.com/didi/DoKit + external-review 2026-04-25]

### BlockCanary：理解 Looper 监控的历史样本

`BlockCanary` 已多年停更，不适合作为新项目的生产监控方案。它的价值在于展示早期卡顿监控的基本做法：通过 `Looper.getMainLooper().setMessageLogging(...)` 观察 Message 分发前后时间，再配合主线程堆栈采样定位长耗时片段。读旧项目时，如果看到类似 Printer / Looper 日志的卡顿监控，可以把它归到这一类。

[已验证: github.com/markzhai/AndroidPerformanceMonitor]

### Rabbit：轻量级研发侧后门

`Rabbit`（`SusionSuc/rabbit-client`）更像轻量级研发侧工具，把性能观察、页面信息和调试入口放在手机端 UI 中。它适合中小团队在调研期快速建立“设备上能看到”的反馈面，但不承担完整线上 APM 的采样、聚合和告警能力。选型时应把它放在 DoKit 这类研发工具箱旁边，避免拿它和 Matrix、Measure 做同层比较。

[已验证: github.com/SusionSuc/rabbit-client]

## 扩展：Rhea / btrace —— 字节跳动的 Trace 工具

Rhea 是字节跳动在 Trace 工具上的一条演进线，后续以 `btrace` 项目的形式完全开源。它基于 Perfetto 生态，适合用来理解函数级 Trace 工具在真实业务里的工程化演进；当前开源 btrace 3.0 已覆盖 Android、iOS 和 HarmonyOS，但 Android 侧 README 标注的边界是 Android 8.0+、64 位设备 / 应用，Java 对象创建监控暂未适配 Android 15 及以上设备。

### 从 Systrace 到 Rhea 的三阶段演进

抖音团队在性能优化过程中经历了三个 Trace 工具阶段，这个演进过程很值得我们了解。

**第一阶段是 Systrace + 自动插桩**。Rhea 1.0 通过字节码插桩自动在每个方法的入口和出口插入 Trace.beginSection / Trace.endSection 调用，并限制方法层级来控制性能开销。但实测发现性能损耗约 11.5%——原因有两个：一是 Systrace 的所有线程向同一个 trace_marker 文件写入时竞争内核态 pos 锁，导致大量 Uninterruptible Sleep；二是限制层级导致超过层级的方法调用信息缺失。

**第二阶段是自研 Method Trace**。Rhea 2.0 摒弃了 Systrace，改为在 Java 层记录方法的首末时间戳，异步写入文件，然后转换为 Systrace 可视化格式。性能损耗从 11.5% 降到了约 3%。但它只能覆盖 Java 方法级信息，无法看到锁等待、I/O 耗时、Binder 调用等系统级行为。

**第三阶段是动态一体化 Trace**。Rhea 3.0 放弃了前面的方案，重新设计了一套完整架构：不限层级插桩获取函数耗时 + Hook atrace_marker_fd 拦截用户态 Trace + Hook libc 的 open/read/write/fsync 收集 I/O 信息 + Hook libbinder.so 的 IPCThreadState.transact 收集 Binder 耗时 + 运行时动态打开 ART 虚拟机的轻锁日志。最终将用户态 atrace 和内核态 ftrace 合并为一个完整的 Trace 文件，兼容 Systrace/Perfetto 可视化格式。

Rhea 的一个关键优化是将直接写入内核态 trace_marker 文件的 Trace 在用户态拦截、缓存，再异步转储。这避免了大量线程同时向同一文件写入导致的 pos 锁竞争问题。这个问题在实际优化中很容易误导方向，因为工具本身的性能开销会表现为 I/O Wait。开源后的 btrace 3.0 又补了同步采样模式，用更低的持续开销换取函数级时序观测能力，更适合长时间抓取。

[来源: Cubox/抖音 Android 性能优化系列：新一代全能型性能分析工具 Rhea]

[已验证: Rhea 后续以 btrace 形式完全开源，3.0 版本补充了同步采样等新能力]

## 扩展：Hook 机制对比

上面提到的工具大量使用了 Hook 技术，但 Hook 方案之间有结构性差异。理解这些区别有助于我们在评估工具时判断其适用范围和稳定性风险。

### PLT Hook（以 xHook 为代表）

PLT Hook 的工作对象是 ELF 文件中的 .got（Global Offset Table）。当我们的代码调用外部函数时（比如调用 libc.so 的 open），实际是通过 .plt → .got 的间接跳转。.got 中存储了目标函数的实际地址。PLT Hook 就是修改 .got 中的函数指针，将其指向我们的 Hook 函数。

这种方案的优势是：不修改目标函数的机器码，只修改一个指针，兼容性和稳定性较好。xHook 的 upstream README 明确标注支持 Android 4.0 - 10（API 14 - 29），ABI 覆盖 armeabi、armeabi-v7a、arm64-v8a、x86 和 x86_64。Android 11+ 能否直接使用，要按目标系统和符号回归验证。劣势是：只能 Hook 通过 .got 进行的间接调用，无法 Hook 同一 ELF 内部函数之间的直接调用。

Matrix 的 IO Canary、KOOM 的内存分配 Hook 都使用了 PLT Hook 方案。

[来源: Cubox/xHook PLT Hook 概述]

### Inline Hook

Inline Hook 直接修改目标函数的机器码（通常是将函数入口处的几条指令替换为跳转指令），将执行流导向 Hook 函数。这种方式理论上可以 Hook 任何函数调用，包括 ELF 内部的直接调用。

优势是覆盖范围广，理论上无 Hook 盲区。劣势是：需要处理不同 CPU 架构的指令差异（ARM、ARM64、x86 等），兼容性风险高；如果目标函数很短（短于一条跳转指令的长度），可能无法 Hook；在多线程环境下修改代码段存在竞态条件。字节跳动在开源生态里把这两条路线拆得很清楚：`ByteHook` 是 PLT Hook 库，`ShadowHook` 才是 Inline Hook 库。分析字节系方案时，先区分自己看到的是 ELF 导入表拦截，还是函数入口改写。两者的稳定性边界和适用场景不同。

Inline Hook 写入 trampoline 后，还要把被改写地址区间的 instruction cache 刷新掉。NDK 侧通常通过 `__builtin___clear_cache(begin, end)` 或 Hook 框架内部封装完成这一步；漏掉 I-cache 刷新时，CPU 可能继续执行旧指令，表现为偶发 `SIGILL`、跳转到旧入口或只在特定 SoC 上复现的崩溃。Android 15 的 16KB page size 设备还要求 Hook 库不要假设页大小固定为 4KB，涉及 `mprotect` 的页边界计算、trampoline 分配和 ELF segment alignment 的代码都要回归验证。

[已验证: bytedance/bhook 为 PLT Hook，bytedance/android-inline-hook 为 ShadowHook Inline Hook；Inline Hook 需处理 I-cache 刷新和 16KB page size 兼容边界]

### Transform（编译期字节码修改）

Booster 使用的 Transform 属于编译期方案。它在 .class 文件阶段对字节码进行修改，修改后的代码直接编译进 APK 中。

优势是零运行时开销——修改在编译期完成，运行时不存在任何 Hook 成本。劣势是只能在编译期看到静态信息，无法根据运行时状态做动态决策。

## 工具选型指南

理解了每个工具的原理之后，实际项目里可以按下面几个场景选择和组合使用。

### 按场景选择

**线上性能监控**需要 Matrix 或 KOOM 这类运行时方案。如果我们的核心关注点是卡顿和 ANR，Matrix 的 Trace Canary 是最成熟的选择。如果内存问题（特别是 Native 泄漏和线程泄漏）是主要矛盾，KOOM 的覆盖范围更广。很多团队的做法是同时接入两者——Matrix 负责卡顿/ANR/IO 监控，KOOM 负责内存监控。

**编译期预防**需要 Booster。它在每次构建时自动扫描潜在问题，不依赖线上数据就能发现问题。特别是对第三方 SDK 的行为约束（线程数控制、主线程 I/O 检测），Booster 在编译期就能拦截。

**启动任务管理**可以用 Anchors / AppInit 等调度框架。重点还是把 DAG 调度的思路落到任务拆分和依赖编排上，而不是绑定某个具体框架。如果项目规模不大，完全可以自建一个轻量的任务调度器。

**线下深度 Trace**中 Perfetto 仍然是首选，btrace / Rhea 的价值在于把应用方法栈与系统 trace 放到同一个 Perfetto 视角里。按 bytedance/btrace 3.0 README，当前开源 Android 路径仍需要 PC 侧脚本、adb 可识别设备和集成 SDK 的 APK；online support 还在 roadmap。要做灰度用户远程取证，不能直接把 btrace 3.0 当成无需 PC / adb 的线上方案，需要先确认团队使用的是内部分支还是自建上传 / 触发通道。

### 组合使用的注意事项

同时接入多个性能库时，通常会遇到三类额外成本。

一是**性能开销叠加**。每个运行时监控工具都会引入额外成本，例如字节码插桩、Looper 监听、native Hook、Hprof 裁剪和上报队列；多个工具叠加后，低端机更容易出现用户可感知的卡顿。不要在选型文档里直接套用固定百分比，应在目标设备、目标版本和目标采样率下用 Macrobenchmark、Perfetto 或线上灰度指标测出基线。通常的做法是对监控工具本身做采样，只对部分用户开启完整监控。

二是**Hook 冲突**。如果 Matrix 和 KOOM 都 Hook 了 libc 的 open/write，可能出现 Hook 链冲突。xHook 本身支持 Hook 链（多个 Hook 函数按序执行），但不同工具使用不同的 Hook 库时可能冲突。建议统一使用同一个底层 Hook 库。

三是**上报数据整合**。多个工具各自上报数据到各自的平台，分析问题时需要跨平台关联。理想情况是建设统一的 APM 平台，将卡顿、内存、I/O 等数据关联到同一个用户会话上。

## 常见问题与误区

**"Matrix 是万能的，接了就不用 Perfetto 了"**。Matrix 解决的是线上监控问题，Perfetto 解决的是线下深度分析问题。两者定位不同，互相不可替代。Matrix 能告诉你"用户 A 在某次操作中发生了卡顿，调用栈是 XXX"，但要理解为什么会走到这条代码路径、整个渲染管线当时的状态如何，还是需要 Perfetto Trace。

**"KOOM 的 Native 泄漏检测可以替代 ASan"**。KOOM 的 Mark-and-Sweep 方案是"不精确"的——它只能检测到"不可达"的内存块，但"不可达"不等于"泄漏"（某些长期存活的内存块可能在扫描瞬间没有被任何栈变量引用）。AddressSanitizer (ASan) 是更精确的工具，但它需要特殊编译且开销大，不适合生产环境。KOOM 适合生产环境的持续监控，ASan 适合开发阶段的问题定位。

**"Booster 的 Transform API 已经过时了"**。Transform API 在 AGP 8.0 已经被移除，旧版基于 Transform 的 Booster 方案不能直接带到新的构建流程里。编译期优化本身还有效，只是接入点换成了 Instrumentation API 和 Artifacts API。

**"启动框架能自动优化启动速度"**。启动调度框架只是帮你更好地组织任务——把可以并行的任务并行化、把非关键路径的任务延迟化。它本身不会让任何单个任务执行得更快。如果每个初始化任务本身就很慢，用了框架也不会有质的变化。优化启动还是要减少启动路径上的工作量。

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
