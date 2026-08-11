---
title: "三方性能库与可观测性选型"
chapter: "14.10"
section: "14.10"
status: finalized
drafted_date: "2026-04-03"
drafted_by: "openclaw-task2a"
applicable_versions: "Android 5.0 (API 21) - Android 17 (API 37)"
last_verified: "2026-07-08"
last_verified_against: "AOSP android-17.0.0_r1 + AndroidX metrics / Android Vitals docs + GitHub upstream READMEs + bytedance/btrace 3.0 README/INTRODUCTION"
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
  - type: official
    path: https://developer.android.com/reference/androidx/metrics/performance/JankStats
  - type: official
    path: https://developer.android.com/topic/performance/vitals
  - type: official
    path: https://developer.android.com/reference/android/app/ApplicationExitInfo
  - type: aosp
    path: frameworks/base/core/java/android/view/FrameMetrics.java
  - type: official
    path: https://opentelemetry.io/docs/platforms/client-apps/android/
tags:
  - android
  - research
  - apm
  - observability
  - tracing
related_chapters:
  - "14.26"
  - "15.5"
  - "15.9"
pipeline_stage: ready-to-publish
task6_state: reviewed
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
last_task6_at: "2026-06-17T08:09:32+08:00"
last_task6_review_log: "logs/review/2026-06-17-08-review.md"
last_task6_audit: "2026-07-02"
task2b_result: fixed
last_task2b_at: "2026-05-28T18:50:00+08:00"
repaired_date: "2026-05-28"
repaired_by: "openclaw-task2b"
last_task9_audit: "2026-06-17"
last_task9_review_log: "logs/deep-review/2026-05-28-19-deep-review.md"
task9_review_notes: "2026-05-28 Task9 deep review: pass-tech-review; no P0/P1; P2 suggestions written to intake/suggestions.md; auto-promoted finalized. 2026-06-17 Task9 idle audit: AUTO-FIX btrace 3.0 Android capability boundary; current open-source path requires PC/adb and online support is roadmap; added Android 8+/64-bit/Android 15 allocation-monitor limits; return to Task6 revisiting."
last_task9_autofix_at: "2026-06-17"
last_task9_audit_log: "logs/deep-review/2026-06-17-05-audit.md"
last_task2b_verifier_at: "2026-06-17T07:29:33+08:00"
task2b_verifier_note: "status finalized→ready-for-review; task9 auto-fix 回流 Task6 复审"
task6_refinalize_note: "2026-06-17 Task6 复审通过（revisiting）；Task9 auto-fix 内容无文风/格式问题，L1/L2 全部通过；自动晋升 finalized。"
deepseek_cn_review_state: done
last_deepseek_cn_review_at: 2026-06-29
---


# 14.10 三方性能库与可观测性选型

## 三方性能库补足的场景

Perfetto、Simpleperf 和 Android Studio Profiler 适合在可控设备上还原现场。线上问题还有另外几项要求：按版本和设备采样、在异常发生前保留线索、控制采集开销、把同一次会话中的崩溃、卡顿、内存和网络事件关联起来。三方库主要补这些工程能力。

这不代表接入 SDK 后就可以放下官方工具。客户端监控负责发现异常和保存证据；Perfetto、系统 dump、基准测试与源码负责复现和归因。选型时应同时核对采集位置、适用系统、构建工具兼容性、运行开销、隐私边界和维护状态。

平台判断以 Android 17 / API 37 / [`android-17.0.0_r1`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/) 为上限；涉及 ART 内部结构时对照同标签的 [platform/art](https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/)。涉及 ftrace 或内核事件时，以 [`android17-6.18-2026-06_r6`](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/) 为内核口径。三方项目的“支持 Android 17”仍需结合目标 ROM、ABI、页面大小和构建链回归，不能由 README 的一行兼容表代替。

## 按采集位置理解工具

库名会变，采集位置决定了它能看到什么，也决定了风险位于哪里。

| 位置 | 代表方案 | 能解决的问题 | 不能替代的能力 |
|---|---|---|
| 系统与实验室工具 | Perfetto、Simpleperf、Profiler、系统 dump | 高保真时间线、采样、堆与系统状态 | 大规模线上采样与会话聚合 |
| App 进程内探针 | Matrix、KOOM、LeakCanary、btrace | 方法、Looper、堆、线程、I/O 或 trace 线索 | 系统全局因果关系 |
| 构建期改写 | Booster、Matrix Gradle 插件 | 字节码检查、替换和产物治理 | 运行时耗时与设备差异 |
| 研发侧工具箱 | DoKit、Rabbit、BlockCanary | 开发和测试设备上的快速反馈 | 生产采样、后端聚合和告警 |
| 可观测性平台 | Firebase Performance、Measure | 上传、聚合、筛选、会话关联 | 本地源码级定位 |

截至 2026 年 7 月，几个项目的版本口径如下。发布版本只能说明上游交付了什么，不能证明它适配当前项目的 AGP、R8、ROM 和安全策略。

| 项目 | 可核对的上游版本 | 接入前应关注的状态 |
|---|---|---|
| Matrix | `v2.1.0` | README 仍声明 Gradle 插件支持 AGP 3.5/4.0/4.1 |
| KOOM | `v2.2.2` | Java 模块支持 API 21+；Native/Thread 模块限 API 24+、arm64 |
| Booster | `v5.1.0` | 发布版 README 兼容表止于 AGP 8.2；主分支已有更高 AGP 适配代码 |
| btrace | `v3.1.0` | Android 8.0+、64 位；对象分配监控暂不支持 Android 15+ |
| LeakCanary | 文档稳定线 `2.14` | 官方接入示例使用 `debugImplementation`；3.0 仍是 alpha 线 |

## Matrix：最像“客户端 APM 框架”的方案

Matrix 是腾讯微信团队开源的插件式性能监控框架。Android 端把多个采集器放在统一的插件生命周期和 `PluginListener` 回调下；数据存储、脱敏、上传、聚合和告警仍由接入方补齐。把 Matrix 称为“完整 APM 平台”会高估开源仓库提供的范围。

### 整体架构

各模块使用的观测手段并不相同。Trace Canary 依赖编译期字节码改写和运行时主线程观测；Resource Canary 使用弱引用、GC 检查和 Hprof；IO Canary 进入 native I/O 路径并改写 `CloseGuard` reporter。不能用“全部通过 Hook”概括 Matrix。上游 README 列出的主要 Android 能力包括：

- **APK Checker**：检查包体、资源、Native 库和构建产物
- **Trace Canary**：卡顿、ANR、启动耗时、帧率监控
- **Resource Canary**：Activity 泄漏与重复 Bitmap 检测
- **IO Canary**：文件 I/O 性能问题检测、Closeable 泄漏监控
- **SQLiteLint**：SQLite 使用规范检测
- **Battery Canary**：耗电行为监控
- **Memory Hook / Pthread Hook / MemGuard**：Native 分配、线程资源和堆内存安全问题

模块清单和公开能力可在 [Matrix README](https://github.com/Tencent/matrix/blob/master/README.md) 核对。不同模块的系统边界、ABI 和构建链要求各自独立，接入一个模块不等于获得整套能力。

### Trace Canary：卡顿与 ANR 的观测边界

Trace Canary 关注卡顿、慢方法、启动、帧率和 ANR 线索。理解它时要分开看“方法记录”“主线程消息观测”和“ANR 检测”，三者的触发条件与证据强度不同。

**方法记录**由 Gradle 插件改写 class，在方法入口和出口调用 `AppMethodBeat`，再用 method id、时间和线程内执行顺序还原调用片段。`Constants.DEFAULT_EVIL_METHOD_THRESHOLD_MS` 在当前主分支为 700 ms，但这是上游默认配置，不是 Android 卡顿或 ANR 的系统判定线。包过滤、黑名单、插桩规模和 buffer 策略都会改变开销与可见范围。

**主线程观测**通过 Looper 分发边界与 `UIThreadMonitor` / `FrameTracer` 组织采样。不能把“单帧超过 16.6 ms”写成固定规则：Android 17 设备可能运行在 60、90、120 Hz 或动态刷新率下，帧预算取决于该帧所在的 VSync 时间线。应用采集到的慢消息或掉帧仍需和 Perfetto 中的 `Choreographer#doFrame`、RenderThread、SurfaceFlinger 与调度事件对齐。

**ANR 线索**有两条路径。`LooperAnrTracer` 在一次主线程 dispatch 开始后安排 5 秒延迟任务，dispatch 正常结束便取消；超时日志表达的是“主线程消息已持续 5 秒”，还不能单独证明系统已经确认 ANR。`SignalAnrTracer` 处理 SIGQUIT / trace dump 相关回调，并继续检查主线程阻塞和进程错误状态。Android 17 上这条路径涉及 ART、signal 与系统 ANR 实现细节，必须在目标 ROM 上验证权限、符号、回调时序和误报率。

构建兼容性是 Matrix 当前最醒目的门槛。官方 README 仍写明 Gradle 插件支持 AGP 3.5/4.0/4.1，源码也保留 `MatrixTraceLegacyTransform` 对 `com.android.build.api.transform` 的依赖；而 [AGP API 更新记录](https://developer.android.com/build/releases/gradle-plugin-api-updates) 明确说明旧 Transform API 从 AGP 8.0 起移除。使用 AGP 8/9 的项目应选择已迁移且经过内部验证的 fork，或把 class 级改写迁到 Instrumentation API，把全量 class 产物操作迁到 Scoped Artifacts API。验证范围至少包含 Debug/Release、R8、增量构建、配置缓存、多模块、动态特性和混淆 mapping。

上述判断可由 Matrix 的 [`Constants`](https://github.com/Tencent/matrix/blob/master/matrix/matrix-android/matrix-trace-canary/src/main/java/com/tencent/matrix/trace/constants/Constants.java)、[`LooperAnrTracer`](https://github.com/Tencent/matrix/blob/master/matrix/matrix-android/matrix-trace-canary/src/main/java/com/tencent/matrix/trace/tracer/LooperAnrTracer.java)、[`SignalAnrTracer`](https://github.com/Tencent/matrix/blob/master/matrix/matrix-android/matrix-trace-canary/src/main/java/com/tencent/matrix/trace/tracer/SignalAnrTracer.java) 和 [`MatrixTraceLegacyTransform`](https://github.com/Tencent/matrix/blob/master/matrix/matrix-android/matrix-gradle-plugin/src/main/kotlin/com/tencent/matrix/plugin/transform/MatrixTraceLegacyTransform.kt) 交叉核对。

### Resource Canary：内存泄漏与冗余 Bitmap

Resource Canary 的公开主路径从 `Application.ActivityLifecycleCallbacks.onActivityDestroyed()` 接收已销毁 Activity，为对象建立 `WeakReference`，放入待检查队列，并在后台线程按配置重试 GC 与存活检查。对象跨过多轮检查仍可达时，模块再按 `DumpMode` 进入“不 dump”“自动 dump”“手动 dump”“fork dump / analyze”等处理器。弱引用仍存活只说明对象尚未回收；低内存压力、调试器、GC 未执行和生命周期时序都会影响判断，因此需要重试与去重。

Hprof 的处理方式取决于配置。上游同时包含 `HprofBufferShrinker`、客户端分析、fork dump / analyze 和仅报告对象信息等路径，不能把它固定描述成“客户端裁剪、服务端解析”。接入方应明确选择哪个处理器、原始或裁剪 Hprof 保存多久、是否允许上传、如何加密，以及分析进程允许使用多少 CPU、磁盘和 PSS。

上游 README 还列出重复 Bitmap 检测：分析 heap 中存活 Bitmap 的像素缓冲区，找出内容重复的对象。它能提示重复 decode 或缓存分裂，但相同像素不等于对象可以直接合并；密度、色彩空间、可变性、硬件 Bitmap 和生命周期仍要逐项确认。

对应实现可查看 [`ActivityRefWatcher`](https://github.com/Tencent/matrix/blob/master/matrix/matrix-android/matrix-resource-canary/matrix-resource-canary-android/src/main/java/com/tencent/matrix/resource/watcher/ActivityRefWatcher.java) 与 [`processor` 目录](https://github.com/Tencent/matrix/tree/master/matrix/matrix-android/matrix-resource-canary/matrix-resource-canary-android/src/main/java/com/tencent/matrix/resource/processor)。当前上游默认观察入口面向 Activity；项目若声明 Fragment 检测，应给出所用 fork 的 `FragmentLifecycleCallbacks` 和 watcher 代码。

### IO Canary：文件 I/O 的问题扫描

IO Canary 在 native 层拦截 `open`、`read`、`write`、`close` 等调用，把文件路径、Java 调用上下文、线程、次数、字节数和耗时汇总到 detector。上游 Matrix 公共组件内置了 xHook 风格的 PLT Hook 实现。PLT Hook 只能覆盖经过目标 ELF 重定位槽的调用；静态链接、同一 ELF 内部直接调用、内联、不同符号变体和未列入 Hook 集合的系统调用都可能绕过采集，所以“全量监控”不成立。

三个公开 detector 的条件值得按源码理解：

- **主线程 I/O**：检查文件操作是否来自主线程，并结合连续读写耗时等条件分类。文件 I/O 可能表现为 Running、Runnable、Sleeping 或 Uninterruptible Sleep，不能预设 Perfetto 中一定是 D 状态。
- **小缓冲区**：默认阈值为 4096 B，但源码还要求操作次数大于 20、平均每次读写小于阈值，并且连续读写耗时达到 13 ms。它检测的是“频繁小 I/O 已形成可观测成本”，不是看到一次 2 KB `read()` 就报警。
- **短时重复读取**：同一路径、相同调用信息在短窗口内达到默认重复次数 5 后报告；写操作会清掉对应观察记录。报告是缓存缺失的候选线索，也可能来自格式探测或刻意的分段读取。

Java 侧 `CloseGuardHooker` 通过反射替换 `dalvik.system.CloseGuard.Reporter`，用于发现未关闭资源。它依赖非 SDK 实现细节，Android 17 / API 37 设备上要覆盖 user、userdebug、混淆、隐藏 API 策略和 OEM ROM 测试。反射失败时应降级并记录能力缺失，不能让监控组件影响业务启动。

默认条件可在 [`io_canary_env.h`](https://github.com/Tencent/matrix/blob/master/matrix/matrix-android/matrix-io-canary/src/main/cpp/core/io_canary_env.h)、[`small_buffer_detector.cc`](https://github.com/Tencent/matrix/blob/master/matrix/matrix-android/matrix-io-canary/src/main/cpp/detector/small_buffer_detector.cc) 和 [`CloseGuardHooker`](https://github.com/Tencent/matrix/blob/master/matrix/matrix-android/matrix-io-canary/src/main/java/com/tencent/matrix/iocanary/detect/CloseGuardHooker.java) 中核对。

## KOOM：把内存问题单独拉出来处理

KOOM（Kwai OOM）是快手团队开源的内存监控方案。它最适合解决已经明确落在内存侧的问题。相比 Matrix 的 Resource Canary，KOOM 更像一个专项治理工具。

### Java 堆泄漏检测

KOOM 的 Java 模块会周期性观察 Java heap、线程数、文件描述符数和 VSS。一个或多个指标连续越过配置阈值后，`OOMMonitor` 才进入 dump 与分析流程。示例中的 `setHeapThreshold(0.9f)`、`setThreadThreshold(50)` 等值明确标注为测试配置；生产阈值应来自目标设备分层和线上分布，不能抄示例。

为缩短主进程冻结时间，上游路径会暂停 ART VM、`fork()` 子进程、恢复父进程，再由子进程 dump heap。KOOM README 把传统 dump 的长冻结缩短到“20 ms 内”作为项目测量结果；Copy-on-write 页、堆规模、内存压力、ROM 修改和调度抖动都会影响结果，接入文档不应把 20 ms 写成设备保证。

子进程可生成 strip Hprof，并由基于 Shark 的分析器在设备侧计算泄漏对象和引用链；需要交给 Android Studio 或 MAT 时，上游还提供 refill 工具。Dump、裁剪和分析仍可能运行数分钟并占用一条 CPU 及较多内存，README 因此建议远程开关和采样。系统正处于低内存压力时启动分析，可能放大 OOM 风险；触发器要同时检查前后台、剩余磁盘、充电状态、温度和进程重要性。

Java 模块的触发、兼容范围和资源提示见 [`koom-java-leak/README.md`](https://github.com/KwaiAppTeam/KOOM/blob/master/koom-java-leak/README.md)。该模块声明支持 Android 5.0 / API 21 及以上和四种常见 ABI；这项声明不自动覆盖 Android 17 上的所有 OEM ART 修改，仍需真机验证 fork、dump、解析与恢复路径。

### Native 堆泄漏检测

`koom-native-leak` 采用“分配元数据 + 保守可达性扫描”的方案。工作过程可拆成三步：

1. 通过 PLT Hook 记录 `malloc` / `free` 等分配路径的地址、大小和分配栈。

2. 周期性扫描寄存器、线程栈、全局区和 heap 中形似指针的值，把能到达的分配块标记为可达。

3. 将未标记块与分配元数据关联，输出地址、大小和分配栈。

这是保守扫描：一个恰好长得像地址的整数或 allocator 残留值可能把泄漏块继续标成可达，造成漏报；扫描时的线程与 allocator 状态也会影响结果。上游 README 给出的范围是 Android 7.0 / API 24 及以上、仅 `arm64-v8a`，并建议只在性能较好的设备上采样启用。Android 17 上还要覆盖 16 KB page size、目标 libc/allocator、PAC/BTI、unwind 和符号化配置。

实现说明见 [`koom-native-leak/README.md`](https://github.com/KwaiAppTeam/KOOM/blob/master/koom-native-leak/README.md)。

### 线程泄漏检测

KOOM 的 ThreadLeakMonitor 通过 Hook `pthread_create`、`pthread_exit` 等生命周期函数，跟踪创建栈、线程名和回收状态。公开 README 聚焦一种明确的 POSIX 资源泄漏：joinable 线程已经退出，却没有执行 `pthread_join()` 或 `pthread_detach()`；线程的退出状态及相关资源会一直保留到被回收。业务线程长期运行属于另一类治理问题，不能仅凭存活时间归为 pthread 泄漏。

该模块也只声明 Android 7.0 / API 24 及以上和 `arm64-v8a`。报告应保留创建栈、退出时刻、join/detach 状态和线程名，避免把 Binder 线程池、线程池 worker 或监控线程的长期存活混入同一种告警。

适用范围和判定条件见 [`koom-thread-leak/README.md`](https://github.com/KwaiAppTeam/KOOM/blob/master/koom-thread-leak/README.md)。

## Booster：把问题尽量拦在编译期

Booster 在构建期检查或改写 class 和产物。它可以统一处理应用及依赖中的特定调用点，也可以产出检查报告。构建期结果描述的是静态代码和最终产物，无法回答某段代码在线上执行了多少次、耗时多少或在哪类设备上触发。

### 不要混淆两种 Transform

早期 Booster 建立在 AGP 的 `com.android.build.api.transform.Transform` 接口上。该接口从 AGP 8.0 起已经删除。Booster 文档中的 “Transform based modules” 又是它自己对字节码转换模块的分类，这个名称延续到了 5.x，不能据此推断 5.x 仍调用旧 AGP Transform API。

当前主分支的 `BoosterPlugin.registerTransform()` 在 `androidComponents.onVariants` 中注册任务，再通过 `variant.artifacts.forScope(ScopedArtifacts.Scope.ALL).toTransform(ScopedArtifact.CLASSES, ...)` 接入 class 产物。这属于 Android Components / Scoped Artifacts 路径。若只需逐 class ASM visitor，也可以使用 `variant.instrumentation.transformClassesWith()`；两类 API 的输入范围、增量粒度和 classpath 能力不同。

编译期改写本身没有采集线程或定时器，但改写后的代码可能增加运行成本，线程重定向也会改变调度、公平性与故障表现。“构建期完成”不等于“运行时零开销”。

### Booster 的主要优化能力

Booster 以独立模块提供检查、替换和产物处理能力。生产项目应逐个启用模块并保存模块报告，避免把整套插件当成一个开关。

- **API 与字节码检查**：识别可能阻塞 UI 线程的 API、产物异常或不符合团队约束的调用。静态检查给出候选位置，是否在主线程执行仍需运行时证据。
- **线程改写**：`booster-transform-thread` 将 `Thread`、`Executors`、`ThreadPoolExecutor` 等创建路径替换为 Booster 的 instrument 类，以统一命名和线程池策略。它会改变第三方库的执行语义，必须覆盖队列饱和、拒绝策略、优先级、线程本地变量、关闭与取消行为。
- **资源索引内联**：`booster-transform-r-inline` 从 symbol list 解析资源 id，把字节码中的 `GETSTATIC R$*.field` 换成常量，并清理部分 R class 字段。AGP 的 non-final / non-transitive R、动态特性、资源 shrink、资源稳定 ID 和 library R 都会影响正确性；应比较改写报告、APK/AAB、安装后资源访问和 R8 结果。
- **系统缺陷兼容模块**：Toast 模块把 `Toast.show()` 调用改写为 `ShadowToast.show(toast)`。在 API 25 上，wrapper 尝试替换 Toast 内部 Handler callback / runnable 来捕获 `BadTokenException`；它不是简单地给每个调用点包一层 `try-catch`，也不应在其他 API 上假定相同内部字段。

这些模块与 Trace Canary 形成静态和动态两类证据：Booster 报告“代码中存在某种调用或改写”，运行时 trace 回答“调用是否发生、位于哪条路径、成本多大”。两类结果不要合并成同一个结论。

源码依据包括 [`BoosterPlugin.kt`](https://github.com/didi/booster/blob/master/booster-gradle-plugin/src/main/kotlin/com/didiglobal/booster/gradle/BoosterPlugin.kt)、[`RInlineTransformer.kt`](https://github.com/didi/booster/blob/master/booster-transform-r-inline/src/main/kotlin/com/didiglobal/booster/transform/r/inline/RInlineTransformer.kt) 和 [`ToastTransformer.kt`](https://github.com/didi/booster/blob/master/booster-transform-toast/src/main/kotlin/com/didiglobal/booster/transform/toast/ToastTransformer.kt)。

### 版本兼容性怎么读

Booster `v5.1.0` README 的发布版兼容表列出：

| AGP | Booster 发布线 | 判断 |
|---|---|---|
| 7.x 及更早 | 4.x | 按表选择最低 Booster 版本 |
| 8.0 / 8.1 / 8.2 | 5.0.0+ | 5.x 支持字节码转换模块；多数旧 Task 模块已移除 |
| 8.3—8.5 | 表中为 N/A | `v5.1.0` 不能按发布表宣称支持 |
| 8.6 及以上 | 发布表没有对应行 | 不能从主分支 adapter 推断 5.1.0 artifact 已支持 |

2026 年的主分支已经出现 AGP 8.3—8.12 adapter 和集成测试，说明上游正在扩展范围；这些代码晚于 `v5.1.0`，不能倒推 Maven Central 的 5.1.0 已包含它们。接入策略应以“已发布 artifact + 对应 commit + CI 实测”三项为准。AGP 9 项目还要核对上游主分支移除 AGP 9 substitute module 的提交，不能根据模块名猜测兼容性。

升级验证至少覆盖 clean/incremental build、configuration cache、并行构建、R8、baseline profile、test/benchmark variant、动态特性、AAB 和 mapping/资源产物。官方兼容表与迁移说明见 [Booster README](https://github.com/didi/booster/blob/master/README.md)，AGP 旧 Transform API 的删除与替代接口见 [Android Gradle plugin API updates](https://developer.android.com/build/releases/gradle-plugin-api-updates)。

## 启动优化框架：组织启动阶段的任务依赖

启动框架负责表达任务、依赖和等待点。它不会减少 SDK 自身的初始化工作，也无法突破 Android 启动的生命周期约束。任何异步化都要回答三个问题：首帧前是否必须完成、哪个线程允许调用、失败后谁负责降级或重试。

### 核心思路：有向无环图（DAG）调度

大型 App 的 `Application.onCreate()` 和首个 Activity 生命周期中常有 SDK 初始化、数据预加载、组件注册和路由表构建。这些工作可以表示为 DAG：任务是节点，依赖是有向边；入度为零的后台任务可以调度执行，依赖完成后再释放后继节点。

并行数量越多，CPU 竞争、锁冲突、I/O 队列和 class loading 抖动也越大。调度器需要限制并发，显式区分主线程任务与后台任务，并把首帧必需节点的最长依赖链当作关键路径。任务总耗时下降但关键路径变长时，启动指标仍会退化。

还要区分“组件发现”和“并行调度”。[Jetpack App Startup](https://developer.android.com/topic/libraries/app-startup) 通过一个共享 `InitializationProvider` 发现 `Initializer`，由 `dependencies()` 声明顺序，也支持手动延迟初始化；它的 `create()` 调用不提供通用后台并行调度器。需要并行 DAG、线程选择或锚点等待时，要由业务调度层负责。

### 典型框架对比

**Alpha** 是阿里开源的早期 DAG 调度样本，支持任务依赖、优先级和线程池。仓库已归档，代码提交停在 2018 年，适合阅读设计，不适合直接作为新项目依赖。

**Anchors** 在图调度上增加“锚点”：`AnchorsManager.start()` 可以阻塞等待指定节点完成，异步节点由线程池驱动，同步节点投递到主线程。它也支持显式 block/unlock。锚点放在 `Application.onCreate()` 时会直接占用主线程启动窗口，应只等待首个可交互页面不可缺少的节点。上游最新版本记录为 2022 年的 `v1.1.8`，接入现代 Kotlin、AGP 和 Android 17 项目前要自行回归。

**AppInit（hacket/AppInit）** 使用 `@AppInitTask` 标注任务 id、进程、优先级、依赖和是否后台执行，通过 KAPT/KSP 收集任务，也提供 AndroidX Startup 入口。仓库与 Maven `1.0.1` 线停在 2022 年。项目里的 `@AppInit` 若来自另一个同名库，必须先确认 group id 与仓库，避免把不同实现的能力写到一起。

选型时可用四项验收：

1. 循环依赖在构建期或启动早期失败，并给出完整环路。
2. 每个任务有线程约束、进程范围、超时、失败策略和幂等说明。
3. trace 中能看到任务排队、执行、等待和关键路径，线上指标能关联调度版本。
4. 用 Macrobenchmark 比较冷启动分位数，同时检查首帧、完全绘制、CPU time、主线程 I/O 和后台抢占。

上游状态可从 [alibaba/alpha](https://github.com/alibaba/alpha)、[DSAppTeam/Anchors](https://github.com/DSAppTeam/Anchors) 与 [hacket/AppInit](https://github.com/hacket/AppInit) 核对。

## 再补几类经常被漏掉的工具

### LeakCanary：本地泄漏排查工具

LeakCanary 在 debug / 测试构建中观察应被回收的对象，dump heap 后用 Shark 分析引用图，并给出到 GC root 的保留路径。官方 `2.14` 接入示例明确使用 `debugImplementation`，这与 KOOM 面向采样式线上取证的部署目标不同。

- LeakCanary 适合研发复现、自动化测试和本地引用链解释。
- KOOM 提供阈值触发、fork dump、Native heap 与 pthread 资源监控，更偏受控线上采样。

两者都会遇到 heap dump 成本、对象暂时存活和框架已知引用等问题。报告中的 reference path 是“为什么对象仍可达”的证据，不自动等同于“应该在哪一行置 null”。修复前还要确认 owner 生命周期、泄漏对象的 retained size 与重复频率。

当前稳定接入说明见 [LeakCanary Getting Started](https://square.github.io/leakcanary/getting_started/)。`3.0-alpha` 可用于跟踪演进，不宜在没有回归计划时替换稳定线。

### Firebase Performance：接入成本较低的平台型方案

Firebase Performance Monitoring 的 Android SDK 会自动采集 app start、前后台时长和 screen rendering；加入 Gradle 插件后还会插桩 HTTP/S 请求与 `@AddTrace`。自定义 trace 可以增加 duration、metric 和 attribute。它适合快速获得按设备、版本、国家等维度聚合的趋势。

边界同样明确：官方文档写明多进程 Android App 只支持主进程；HTTP payload size 依赖 `content-length`，可能不准确；默认 trace 的起止定义也未必等于产品自己的“可交互”口径。接入还要审查数据收集开关、URL 聚合、属性基数、地区合规和 BigQuery 成本。

能力和限制见 [Firebase Android 接入文档](https://firebase.google.com/docs/perf-mon/get-started-android) 与 [Performance Monitoring 概览](https://firebase.google.com/docs/perf-mon/)。

### Measure：更完整的平台视角

Measure 同时提供客户端 SDK、后端与 Web UI，可使用托管服务或自托管。它以 session timeline 组织点击、导航、HTTP、log、crash、ANR、trace 和 bug report，并提供 app health 与 adaptive capture。

平台化的代价是运维和数据模型复杂度。评估时应验证采样决策是否能远程下发、会话数据如何脱敏、离线缓存上限、符号表和 mapping 保留期、服务端升级，以及一次事故需要关联的字段能否稳定落在同一个 session。

项目范围与自托管入口见 [measure-sh/measure](https://github.com/measure-sh/measure)。

### DoKit：更像研发工具箱

DoKit 把 App 信息、沙盒浏览、网络、UI 检查、启动耗时、FPS 等能力放进设备端入口，适合开发和测试现场。它还包含 AOP/字节码与平台服务相关功能，接入前要区分仅 debug 生效的 kit、会修改构建产物的插件和依赖远端服务的功能。

GitHub release 页面、README badge 与 AGP 8.6 相关 feature 分支显示的 Android 版本线并不一致。新项目应从所需 kit 反推最小依赖，按选定 artifact 验证 AGP/Kotlin/R8 与 Android 17，避免因为一个调试入口引入整套运行时代码。DoKit 不负责大规模生产采样、后端聚合和告警。

项目能力与数据收集说明见 [didi/DoKit](https://github.com/didi/DoKit)。

### BlockCanary：理解 Looper 监控的历史样本

BlockCanary 的仓库没有正式 release，代码更新已长期停滞，不适合作为 Android 17 新项目的生产依赖。它仍是理解 Looper `Printer` 卡顿监控的历史样本：观察 Message 分发前后时间，并在超时期间采集主线程栈。该方法看不到 RenderThread、GPU、SurfaceFlinger 和系统调度全貌，也会和其他 `setMessageLogging()` 使用者争用入口。

源码见 [markzhai/AndroidPerformanceMonitor](https://github.com/markzhai/AndroidPerformanceMonitor)。

### Rabbit：设备端调试入口

Rabbit（`SusionSuc/rabbit-client`）把页面信息、性能观察和调试入口放在设备 UI 中，定位接近 DoKit 一类研发工具箱。其 `v1.0-beta` 发布于 2020 年，仓库代码更新停在 2023 年。Android 17 项目若保留它，应限制到 internal/debug variant，并检查 exported component、网络代理、文件访问和隐私权限。

源码与发布记录见 [SusionSuc/rabbit-client](https://github.com/SusionSuc/rabbit-client)。

## 扩展：Rhea / btrace —— 字节跳动的 Trace 工具

Rhea 后续以 `btrace` 开源。旧文章常把 Rhea 1.0、2.0 和“Rhea 3.0”连成一套方法插桩方案，但当前 `btrace 3.x` 已经换了技术路线。阅读历史资料时要按版本拆开，避免把旧架构写成 3.1.0 的现状。

### 2.0 与 3.x 的边界

`btrace 2.0` 依赖编译期方法插桩。它能给被插桩方法较精确的进入/退出时序，却增加构建和维护成本，只能覆盖打进 APK 的方法，系统 framework 方法也不在该范围内。早期 Rhea 对 `trace_marker` 竞争、用户态缓存和异步转储的探索仍有历史价值；原团队公布的开销数字来自特定版本与测试环境，不能套用到当前设备。

`btrace 3.x` 的 Android 路径改为“同步回溯 + 动态插桩”：

- 在目标线程经过高频叶子节点或阻塞点时，同步遍历 ART stack，先保存 method pointer，再批量符号化。
- 使用 ShadowHook 动态代理 allocation、`MonitorEnter`、`Object.wait`、`Unsafe.park`、GC 等点，在进入或退出边界触发回溯并记录 wall time / thread CPU time。
- Android 8.1 及以上默认使用 Perfetto 模式，合并 App trace 与设备可提供的 atrace/ftrace；旧系统可退回 simple 模式，只保留 App trace。

同步回溯避开了周期性 suspend/resume 的部分成本，并可观察系统方法；它仍依赖触发点。线程长时间停在没有插桩点的计算或阻塞路径中，采样会出现空洞。生成的函数时长是相邻 stack sample 重建结果，不等于逐方法入口/出口的精确计时。

### 当前开源使用边界

`v3.1.0` README 列出的 Android 条件是：

- Android 8.0 及以上；
- 设备与 App 都是 64 位；
- Java 对象分配监控尚未适配 Android 15 及以上；
- PC 端需要 adb、Java、Python 3，设备要安装集成 btrace 的 APK；
- online support 仍列在 roadmap。

所以 btrace 适合连接设备的深度 trace 和内部构建诊断。若要用于线上用户，团队还需实现受控触发、权限、缓冲区上限、加密上传、超时、符号管理与远程熔断。Android 17 上它会接触 ART 内部符号和 ShadowHook，必须在 `android-17.0.0_r1` 对应的 Pixel/AOSP 镜像及目标 OEM ROM 上回归；Perfetto 中出现的内核事件再按 [`android17-6.18-2026-06_r6`](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/) 核对，不要用旧内核字段解释新 trace。

当前原理与限制见 [btrace README](https://github.com/bytedance/btrace/blob/master/README.MD) 和 [btrace 3.0 Introduction](https://github.com/bytedance/btrace/blob/master/INTRODUCTION.MD)；早期方法插桩路线可对照[抖音 Rhea 文章](https://mp.weixin.qq.com/s/vkBeZ6hmVn_RaXS5Xv_L2g)阅读。

## Hook 能力只在这里做选型

Matrix、KOOM、btrace 等工具会使用 PLT Hook、Inline Hook、ART/JVMTI 或构建期字节码改写，但“使用了 Hook”不足以证明兼容性。选型时至少记录目标符号、拦截位置、ABI、装载时机、链式调用规则、失败降级、4 KB/16 KB page size、BTI/PAC、CFI/unwind 和目标 ROM。具体实现、回调安全与验证矩阵统一放在 [Hook 基础设施与性能工具实现原理](26-hook-infrastructure.md)，本节不再重复维护两套原理说明。

## 工具选型指南

选型从“要保留什么证据”开始，再看采集方式和维护成本。

### 按场景选择

| 目标 | 候选能力 | 选型前的硬条件 |
|---|---|---|
| debug Java 泄漏 | LeakCanary | debug/test variant；可接受 heap dump 与本地分析 |
| 受控线上 OOM 取证 | KOOM Java | 远程开关、采样、磁盘/内存保护、Hprof 合规 |
| Native 分配或 pthread 资源 | KOOM Native/Thread、Matrix hook | API/ABI 符合；目标 ROM、unwind、page size 已回归 |
| 卡顿、启动、I/O 线索 | Matrix 对应模块 | Gradle 插件已迁移；自建数据上传与聚合 |
| 构建期扫描与替换 | Booster 或自研 AGP 插件 | AGP/Booster artifact 精确匹配；改写报告可审计 |
| 会话聚合与告警 | Firebase Performance、Measure | 数据地区、脱敏、成本、主进程/多进程范围满足要求 |
| 连接设备的函数级 trace | btrace + Perfetto | Android 8+、64 位、PC/adb；Android 17 真机验证 |
| 启动依赖管理 | AndroidX Startup、自研 DAG、Anchors/AppInit | 先定义关键路径、线程约束、超时与失败策略 |

### 组合使用的注意事项

**开销会叠加。** 方法探针、Looper 监听、native Hook、stack unwind、heap dump、裁剪与上传都会消耗资源。不要引用上游的固定百分比充当本项目数据；用目标低端机、Android 版本、采样率与典型业务跑 Macrobenchmark 和长稳测试，并用 Perfetto 检查监控线程本身。

**Hook 链会冲突。** 两个库同时改写 `open`、`malloc` 或 ART 符号时，链顺序、原函数指针、unhook 和递归保护可能互相破坏。ByteHook 支持同一函数的多 Hook，不代表 xHook fork、另一套 inline hook 与它可以安全混用。接入清单应画出每个符号的 owner 与链顺序，并通过故障注入验证任一模块初始化失败或关闭时其余模块仍工作。

**数据需要共同主键。** 卡顿、OOM、网络和启动数据若各自使用不同 session、时间源、版本号与用户匿名标识，事后无法关联。统一 monotonic/wall clock 换算、process start id、session id、build id、mapping id、ABI、page size 和采样配置，比统一 UI 更优先。

**监控必须可关闭。** 远程开关应支持按模块、版本、设备层级和采样组关闭，并设本地最大磁盘、内存、CPU 时间、上传次数与超时。监控代码发生崩溃、ANR 或 OOM 时，要能确认它是否参与了事故。

## 从信号到平台：统一可观测性口径

三方 SDK 之外，还应先复用平台与 Jetpack 已有信号：

| 信号 | 适合回答的问题 | 主要边界 |
|---|---|---|
| `JankStats` | Window 每帧的 jank 判断和 UI 状态 | 不负责上传、聚合、告警或生成 trace |
| `FrameMetrics` | API 24+ 的 measure/layout、draw、sync、swap、deadline 等原始阶段耗时 | 低版本回退、jank 判断和状态管理要自行实现 |
| `ApplicationExitInfo` | API 30+ 的进程退出 reason、importance、PSS/RSS 与可选 trace | 历史条数有限，trace 可能为空，隐藏 subreason 不是公开契约 |
| `ProfilingManager` | API 35+ 由系统代采 system trace、heap dump/profile 和 stack trace | 配额、采集时机和交付由系统控制，详见 ProfilingManager 专章 |
| Android Vitals | 分发侧的稳定线上基线 | 聚合口径不替代单次故障的本地证据 |

平台内的数据也要分层：metric 是低成本数值，event 是离散事实，span 表示有起止的操作，profile 是较大的深度诊断产物，snapshot 则是 HPROF、tombstone、ANR trace 或截图。不要把它们都叫作“trace”，也不要用一种采样策略处理所有类型。

自建 schema 至少保留 event time、monotonic time、session/process start、app/build/mapping ID、设备与系统版本、metric 单位、sampling rule/probability，以及大型 artifact 的 hash、大小、类型、加密和过期时间。数据模型必须能区分“没有发生”“没有采集”“被采样丢弃”“上传失败”和“解析失败”；把这些情况都存成 `null` 会让发生率与覆盖率失真。

Session ID 表示一段使用期，trace ID 表示一次操作或请求树，两者不要由账号、手机号或设备标识直接生成。跨端传播优先使用 W3C `traceparent`，并只向允许的自有域名传播；URL、SQL、页面标题和堆对象等高基数字段应先归一化或哈希，HPROF、截图与 trace 使用独立权限和保留期。

采样预算按数据类型分开：crash/ANR 事件可保持高覆盖，frame 与网络 span 采用稳定规则采样，大型 profile/snapshot 只在异常、系统触发或远程诊断窗口内获取。接入前后都要在低端设备上比较启动、帧、内存、功耗、磁盘和网络开销；远程开关必须能按模块熔断。

## 常见问题与误区

**“Matrix 接入后可以替代 Perfetto。”** Matrix 记录 App 侧选定探针，Perfetto 负责跨进程时间线与系统数据源。一个慢方法栈解释不了 CPU 是否被抢占、Binder 对端、RenderThread、GPU fence 或 SurfaceFlinger 合成；线上报告应能引导到可复现的 Perfetto 场景。

**“KOOM Native 可以替代 ASan/HWASan。”** KOOM 寻找保守扫描下不可达、仍未释放的分配块，偏向泄漏候选；ASan/HWASan 主要检测越界、use-after-free、double-free 等内存安全错误。保守扫描中的 pointer-like 值常造成漏报，sanitizer 又需要专门构建与更高开销，两者解决的问题和部署环境都不同。泄漏专项还应区分 LeakSanitizer、`libmemunreachable` 与分配采样。

**“AGP Transform API 删除，所以 Booster 的字节码模块都失效。”** 旧 AGP Transform 接口已删除；Booster 5.x 把 class 产物接到 Android Components / Scoped Artifacts。应检查具体 Booster 与 AGP 组合，不能从旧接口的名称推导整个项目状态。

**“启动框架会自动缩短启动。”** 调度器只能调整依赖、线程和时机。错误并行会增加争用，错误锚点会直接阻塞主线程。优化结果要用首帧与完全绘制分位数、关键路径和任务总 CPU time 验收，不能用“异步任务数量”验收。

**“README 写支持 API 37，所有能力就都支持 Android 17。”** Hook 框架的系统范围、被 Hook 符号的稳定性、上层工具的逻辑和目标 OEM ROM 是四个层次。ByteHook/ShadowHook 支持 API 37，只能证明框架维护者覆盖了其公开测试范围；btrace 的对象分配监控仍明确排除 Android 15+，这两条信息并不矛盾。

## 参考资料

- [Matrix](https://github.com/Tencent/matrix)
- [KOOM](https://github.com/KwaiAppTeam/KOOM)
- [Booster](https://github.com/didi/booster)
- [Android Gradle plugin API updates](https://developer.android.com/build/releases/gradle-plugin-api-updates)
- [LeakCanary](https://square.github.io/leakcanary/)
- [Firebase Performance Monitoring](https://firebase.google.com/docs/perf-mon/)
- [Measure](https://github.com/measure-sh/measure)
- [DoKit](https://github.com/didi/DoKit)
- [btrace](https://github.com/bytedance/btrace)
- [ByteHook](https://github.com/bytedance/bhook)
- [ShadowHook](https://github.com/bytedance/android-inline-hook)
- [xHook 与 Android PLT Hook 概述](https://github.com/iqiyi/xHook/blob/master/docs/overview/android_plt_hook_overview.zh-CN.md)
- [AndroidX App Startup](https://developer.android.com/topic/libraries/app-startup)
- [Alpha](https://github.com/alibaba/alpha)
- [Anchors](https://github.com/DSAppTeam/Anchors)
- [AppInit](https://github.com/hacket/AppInit)
- [JankStats API](https://developer.android.com/reference/androidx/metrics/performance/JankStats)
- [Android Vitals](https://developer.android.com/topic/performance/vitals)
- [ApplicationExitInfo API](https://developer.android.com/reference/android/app/ApplicationExitInfo)
- [Android 17 FrameMetrics](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/view/FrameMetrics.java)
- [OpenTelemetry Android](https://opentelemetry.io/docs/platforms/client-apps/android/)
