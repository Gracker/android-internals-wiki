# 知识盲区记录

## 2026-05-12 新增盲区

### Android 16 云编译与 SDM 机制
- **盲区描述**: Android 16 的云端编译（Cloud Compilation）和 SDM 机制缺乏一手 AOSP 源码证据
- **涉及章节**: 1.9 Package Manager Service
- **验证状态**: 需要查阅 AOSP android-16.0.0_r1 中相关实现
- **建议行动**: 联系 AOSP 团队获取官方文档或源码分析

### 厂商定制的安装优化路径
- **盲区描述**: 主流手机厂商的安装优化路径（如 vivo 的 Turbo、小米的 HyperOS）缺乏实机测试数据
- **涉及章节**: 1.9 Package Manager Service
- **验证状态**: 需要在不同厂商设备上进行实际测试
- **建议行动**: 收集各厂商设备安装过程的 Perfetto 数据

### 厂商游戏模式输入优先级
- **盲区描述**: 厂商定制的游戏模式中输入优先级提升机制缺乏一手证据
- **涉及章节**: 1.10 ContentProvider 与 2.3 输入事件拦截
- **验证状态**: 当前描述基于推测，缺乏厂商源码验证
- **建议行动**: 获取厂商 Input 源码或进行实际性能测试

### 厂商防误触实现
- **盲区描述**: 各厂商防误触机制的具体实现位置和方案差异缺乏实机测试数据
- **涉及章节**: 2.3 输入事件拦截与安全机制
- **验证状态**: 需要在不同厂商设备上验证防误触实现
- **建议行动**: 测试各厂商设备在边缘触控和口袋防误触的表现

## [2026-05-12] 8.8 Android 多媒体管线性能 — Codec2 / tunneled playback / Media3 ABR

### 盲区描述
章节需要补齐 OMX → Codec2 的媒体框架演进、tunneled playback 在 OMX 与 Codec2 下的实现差异，以及 Media3 ABR “主动预测 / 亚 100ms 决策”是否有官方 release note、commit 或 benchmark 支撑。

### 重要程度
高

### 建议研究方向
- 核对 `frameworks/av/media/codec2/`、`frameworks/av/media/libstagefright/`、Codec2 component 配置与 tunneled playback 相关源码锚点。
- 核对 AndroidX Media3 release notes、`AdaptiveTrackSelection` / `BandwidthMeter` 变更与可复现实验数据。
- 整理 SurfaceView / TextureView / tunneled sideband 三路径在 Android 10-17 的版本边界。

### 关联章节
8.8、2.6、2.15、2.16、14.9

## [2026-05-13] 7.8 RecyclerView 列表滑动性能深度优化 — Android 17 DeliQueue 与 MessageQueue 版本口径

### 盲区描述
章节把 Android 17 DeliQueue、Treiber Stack、`targetSdk >= 37` 生效条件以及 missed frames / 首帧 P95 收益写成确定结论，但当前 sources 未给出 AOSP 源码路径、官方 behavior changes、commit 或 benchmark 条件。

### 重要程度
高

### 建议研究方向
- 核对 Android 17 `android.os.MessageQueue` / native looper / DeliQueue 相关源码路径与 targetSdk gating。
- 查找 Google 官方 Android 17 behavior changes、I/O presentation 或 benchmark，确认 4%、7.7%、9.1% 三组数字的设备、样本和统计口径。
- 复核 RecyclerView GapWorker 通过 `postFromTraversal()` → `recyclerView.post(this)` 投递到主线程队列后，DeliQueue 是否会实际改变预取 deadline 命中率。

### 关联章节
7.8、5.10、16.5


## [2026-05-13] 8.6 Kotlin Coroutine 性能实践 — 知识盲区

### 盲区描述
ADPF hint session 与 Kotlin 协程线程迁移的工程化边界缺少一手验证。

### 重要程度
高

### 建议研究方向
- 复核 PerformanceHintManager.Session 文档、setThreads 行为与 Android 15/16 flagged API 状态
- 用 DefaultDispatcher/limitedParallelism/固定 Executor 三种模型做 TID 迁移 trace
- 评估 reportActualWorkDuration 调用频率和 IPC 开销的实测数据

### 关联章节
5.9、8.6

## [2026-05-13] 14.3 内存分析工具 — 知识盲区

### 盲区描述
MTE ASYMM 在 Android App memtagMode=async 下是否自动启用缺少源码闭环。

### 重要程度
高

### 建议研究方向
- 定位 bionic/scudo/kernel 中 memtag async/asymm 选择路径
- 区分 Arm 硬件 mte3 能力、/sys mte_tcf_preferred、Zygote runtimeFlags 和 manifest memtagMode
- 补充 Pixel 8/9 或 Android 15/16 实机验证

### 关联章节
4.3、14.3


## [2026-05-13] 18.2 Android View 标准管线（BLAST 深入） — 知识盲区

### 盲区描述
Android 17 ART 分代 GC 与 Compose Composition 阶段分配/停顿之间的因果链缺少一手资料闭环；当前稿件直接给出“对象分配开销降低 20%+”，但缺 AOSP/ART 版本、Compose runtime 版本、设备、场景和 benchmark。

### 重要程度
高

### 建议研究方向
- 核对 Android 17 ART generational GC 的公开变更、启用条件和应用可观测指标。
- 核对 Compose runtime 中 Snapshot、SlotTable、LayoutNode 等对象的生命周期，区分持久结构和每帧临时分配。
- 设计同机对比：复杂 recomposition / derivedState / SubcomposeLayout 场景下的 alloc count、GC pause、FrameTimeline jank。

### 关联章节
18.2, 22.3, 4.3

## [2026-05-13] 20.7 异常处理架构设计 — 参考书素材

### 来源
[结构参考: Clippings/Android 应用稳定性剖析与优化 - 线程监控：如何解决匿名线程？.md]

### 知识点
1. 通过 ASM 字节码插桩将 Thread() 无参构造改写为 Thread(String name)，name 为调用类名，解决匿名线程（Thread-N）无法溯源问题
2. Thread.getAllStackTraces() 获取全线程快照及其局限（仅能拿到线程名，无法知道创建来源）
3. 字节码层面：INVOKESPECIAL + LdcInsnNode 改写 Thread.<init> 签名从 ()V 到 (Ljava/lang/String;)V 的完整流程
4. MethodInsnNode 过滤：owner=java/lang/Thread, desc=()V, name=<init> 的匹配模式

### 重要程度
中

### 建议加工方向
- 在 20.7 异常处理架构或 20.6 稳定度量中补充「线程监控」小节：线程数采集 + 匿名线程归因
- 可与已有 ASM 字节码插桩知识（书1第2讲）串联，形成完整的字节码监控方法论
- 补充现代方案对比：AGP Transform → ASM Visitor vs Gradle Transform API deprecated 后的替代路径


## [2026-05-14] 5.11 端侧 AI 推理性能 — Android ML 运行时公开/预览能力边界

### 盲区描述
章节涉及 Android 17 NPU feature、LiteRT CompiledModel / NPU / AOT、AICore 调度与内存归属，但当前正文混用了公开 API、Google AI Edge preview、厂商 SDK 能力和推测性 Android 17 平台能力。需要重新建立“公开可发布事实 vs preview / vendor / 待验证素材”的边界。

### 重要程度
高

### 建议研究方向
- 核对 Android 17 CDD、PackageManager feature 常量与 framework/service 源码，确认是否存在 `android.hardware.ai.npu`、NPU 访问声明、配额或异常模型。
- 核对 LiteRT CompiledModel Kotlin/C++ 文档、2025 LiteRT blog、release notes，拆分公开 GPU/CPU 能力、private preview NPU 能力和 vendor runtime 分发路径。
- 核对 AICore / Gemini Nano 官方文档、StatsD/LMKD/meminfo 相关源码，确认是否存在可影响 PSS/RSS 归属的 work attribution 机制。
- 为 AOT / 冷启动收益补机型、模型、delegate/runtime 版本、首次/稳态测试口径；无数据时删除 500ms→50ms 这类绝对数字。

### 关联章节
5.11、5.9、13.x、14.x、23.x

## [2026-05-14] 4.3 ART 虚拟机内存管理 — Generational CMC 源码锚点

### 盲区描述
Android 16 QPR2 / Android 17 Generational CMC 的公开说明与 AOSP 具体开关、年轻代参数、设备能力判断之间缺少可复核对应关系。当前章节出现 `use_generational_cmc`、`generational_cmc_supported`、年轻代占比 25%-40% 等细节，但缺 tag/commit 证据。

### 重要程度
高

### 建议研究方向
- 对齐 Android 16 QPR2 / Android 17 ART tag 或 commit，确认 Generational CMC 开关名称与设备能力判断路径。
- 复核 `gUseUserfaultfd`、`xgc_option.generational_gc`、`ShouldUseGenerationalGC()` 与 DeviceConfig 属性之间的关系。
- 查找年轻代大小/晋升策略的源码参数或官方说明，补不到则删除具体比例。

### 关联章节
4.3, 4.5


## [2026-05-14] 22.3 Jetpack Compose 性能优化 — Pausable Composition / Compose 工具链资料闭环

### 盲区描述
章节包含 Pausable Composition 默认启用/回退、LazyLayoutCacheWindow 版本 API、“View 系统性能对等 / 0.2% 卡顿率”、后台文本布局预热、Android Studio Compose Profiler 等判断；其中多处仍缺官方 release notes、AndroidX 源码 flag、工具文档或 benchmark 条件。

### 重要程度
高

### 建议研究方向
- 核对 Compose Foundation 1.9/1.10 release notes、Android Developers Blog 与 AndroidX `ComposeFoundationFlags.isPausableCompositionInPrefetchEnabled` 默认值。
- 补 `LazyLayoutCacheWindow` Dp/fraction API 的版本边界与可编译示例。
- 查找 Android Studio Compose Profiler / Composition tracing 的官方入口、适用版本和 trace 采集步骤。
- 对“0.2% 卡顿率”和“后台文本布局预热”补设备、样本、指标定义和启用条件；补不齐则从正文判断中移除。

### 关联章节
22.3、7.7、22.2、18.2

## [2026-05-14] 24.4 网络架构与连接管理 — HTTPDNS / OkHttp Dns 执行边界

### 盲区描述
章节已经覆盖 HTTPDNS、TTL、失败隔离和系统 DNS 兜底，但缺少 OkHttp `Dns.lookup()` 的执行边界：该回调同步参与 route planning，必须并发安全；如果在 `lookup()` 内实时发 HTTPDNS 网络请求，可能阻塞建连、递归依赖同一个 `OkHttpClient`、在弱网下放大延迟，甚至让 HTTPDNS 服务自身解析失败。

### 重要程度
高

### 建议研究方向
- 核对 OkHttp 5 `Dns` 文档与 `RoutePlanner` / `RealRoutePlanner` 源码，确认 `lookup()` 的同步调用位置、并发安全要求和失败传播方式。
- 补一套 HTTPDNS 接入模式：异步预取、内存/磁盘缓存读取、TTL 刷新、失败 IP quarantine、bootstrap client / system DNS 启动路径。
- 补弱网验证口径：HTTPDNS 服务不可达、返回空列表、单 IP 失败、多 IP + fast fallback、网络切换后的缓存刷新。

### 关联章节
24.4、24.5、12.3

## [2026-05-15] 26.2 Crash 上报体系搭建 — Native Crash / ApplicationExitInfo 补偿链路

### 盲区描述
26.2 目前把 Java Crash、Native Crash 的崩溃当下落盘写成同一套最小 envelope 流程，缺少 Native signal handler 的 async-signal-safe / out-of-process handler 边界；下次启动扫描只覆盖 SDK 本地 crash store，未纳入 Android 11+ `ApplicationExitInfo` 对 ANR trace 与 native tombstone protobuf 的系统补偿入口。

### 重要程度
高

### 建议研究方向
- 复核 Crashpad / Breakpad Android client 的 signal handler、minidump 写入和 handler 进程模型。
- 复核 Android `ApplicationExitInfo#getTraceInputStream()` 在 API 30/31+ 对 `REASON_ANR`、`REASON_CRASH_NATIVE` 的返回条件、环形缓冲覆盖和 `null` 边界。
- 设计 SDK envelope 与系统 exit reason 的去重键：pid、timestamp、process_name、reason、tombstone/build id、top frame。

### 关联章节
26.2, 20.2, 20.3, 19.24, 15.3

## [2026-05-15] 26.5 线上问题排查方法论 — Android 版本化线上诊断能力

### 盲区描述
26.5 的线上 Trace 与证据包模板没有按 Android 版本拆分官方诊断入口：Android 11(API 30)+ `ApplicationExitInfo` 可作为下次启动补偿证据；Android 15(API 35)+ `ProfilingManager` 支持 App-driven system trace / heap / stack profiling；Android 16(API 36)+ `ProfilingTrigger` 支持事件触发采集。需要把这些能力与 Android 10-14 的 Perfetto/bug report/人工协助路径放到同一张版本边界表里。

### 重要程度
高

### 建议研究方向
- 复核 `ActivityManager.getHistoricalProcessExitReasons()` / `ApplicationExitInfo` 的 reason、traceInputStream、历史记录保留与去重边界。
- 复核 `ProfilingManager.requestProfiling()` 的 system trace 参数、rate limiter、结果文件目录、取消/超时行为。
- 复核 `ProfilingTrigger` 在 Android 16/API 36 及后续 API 36.1/37 中的 trigger 类型差异，把 ANR、fully drawn、app-request running trace 分开说明。
- 给 26.5 增加 Android 10-14 / 15 / 16+ 三档线上诊断能力表，并回连 13.2、15.5、20.3、26.2。

### 关联章节
26.5、13.2、15.5、20.3、26.2

## [2026-05-15] 26.6 A/B Test 与性能回归防护 — 知识盲区

### 盲区描述
性能 A/B Test 章节需要补齐统计模型边界：连续耗时/功耗/帧耗时这类长尾指标的样本量不能只由 baseline、MDE、alpha、power 决定，还需要历史方差或完整分布、检验对象（均值/比例/分位值）、分群后的 allocation ratio；P90/P99 的分群归因也不能用“样本量 × 分位值变化”线性相加。

### 重要程度
高

### 建议研究方向
- 梳理性能指标的三类实验检验：均值/比例、阈值违约率、P90/P99 分位值，并给出各自所需字段。
- 为分位值实验补 quantile confidence interval、bootstrap 或 tail violation rate 的工程实现路径。
- 补充多分群、多护栏指标和频繁中途看数时的假阳性控制：预注册检查窗口、sequential testing / alpha spending、FDR。
- 对齐 Macrobenchmark `FrameTimingMetric` 在 API 29/30 与 API 31+ 的指标可用性，明确 CI 门禁如何降级。

### 关联章节
26.3, 15.6, 26.7

## [2026-05-15] 20.7 异常处理架构设计 — SafeMode 崩溃循环判定与退出补偿链路

### 盲区描述
章节缺少 SafeMode 在真实启动链路中的一手验证：handler 未注册前退出、native crash、ANR、初始化失败、低内存杀进程、WebView renderer 退出与用户强杀/升级之间的判定边界尚未形成闭环。

### 重要程度
高

### 建议研究方向
- 核对 Android 11-16 `ApplicationExitInfo` 的 reason/status/processStateSummary 与 `getTraceInputStream()` 行为，区分 API 30 exit reason、API 31+ native tombstone trace、ANR trace 与 null fallback。
- 设计并验证 launch marker 状态机：`launch_started`、首帧/首页 ready、版本升级清理、bootCount/elapsedRealtime、连续成功启动退出规则。
- 补充 crash 文件存储协议的一手实现：tmp 写入、`fsync(fd)`、同卷 `rename`、`fsync(parent dir)`、completed 扫描与 partial 清理。
- 单独整理 WebView renderer crash 恢复路径：`WebViewClient.onRenderProcessGone()`、受影响 WebView 清理、页面兜底和上报字段。

### 关联章节
20.7、20.2、20.3、26.2、20.6

## [2026-05-15] 4.9 ART FinalizerDaemon 与 ReferenceQueue 性能边界 — Cleaner / CloseGuard 版本边界与 daemon 路径

### 盲区描述
4.9 同时讨论 finalizer、ReferenceQueue、Cleaner、CloseGuard，但还缺少面向 Android 8-16 的版本矩阵和源码路径区分：`sun.misc.Cleaner` 在 `ReferenceQueue.enqueuePending()` 分支由 `ReferenceQueueDaemon` 直接执行；`java.lang.ref.Cleaner.Cleanable` 在 `FinalizerDaemon.processReference()` 中走 `doClean()`；`android.util.CloseGuard` 官方 API Added in API 30，`java.lang.ref.Cleaner` Added in API 33。

### 重要程度
高

### 建议研究方向
- 复核 AOSP `android-16.0.0_r1`：`ReferenceQueue.java` L236-L278、`Daemons.java` L363-L405、`FinalizerReference.java` L33-L69。
- 补 API level 表：API 26-29、30-32、33+ 分别可用的 CloseGuard / Cleaner / StrictMode 方案。
- 核实 core library desugaring 对 `java.lang.ref.Cleaner` 的支持边界，避免把 API 33 平台类建议直接写给 Android 8-12。

### 关联章节
4.9, 10.2, 23.1


## [2026-05-16] 23.3/23.6 虚拟内存黑科技优化 — WebView reservation 释放与 ART 备份栈释放

### 来源
[结构参考: Clippings/Android 性能优化 - 虚拟内存优化（下）：一些“黑科技”优化手段.md]

### 知识点
1. 释放 WebView 预留虚拟内存：Android 系统为每个进程预留 1G（64位）/130M（32位）虚拟内存给 WebView，即使应用不使用 WebView 也会占用。通过解析 /proc/self/maps 找到 [anon:libwebview reservation] 并调用 munmap 释放（Android 10+）；Android 9 以下需通过 PLT Hook android_dlopen_ext 获取 gReservedAddress。
2. 释放 ART 虚拟机备份栈空间：Android 5-7 系统中 ART 创建 main space + main space 1（共 1G），备份空间用于 HomogeneousSpaceCompact GC。通过 GetPrimitiveArrayCritical 禁用拷贝回收 GC，再 munmap 释放未使用的 512M 空间（抖音线上验证 OOM 率未升高）。

### 重要程度
中（WebView reservation 释放仅影响 32 位设备；ART 备份栈仅 Android 5-7，已过时）

### 建议加工方向
- 23.6 大内存与多进程策略中补充 WebView reservation 释放方案作为虚拟内存优化补充
- 23.3 Native 内存管理中补充 munmap 释放预留空间的思路
- 注意标注版本限制：WebView reservation 释放适用于 32 位设备；ART 备份栈仅适用于 Android 5-7
- 补充字节 mSponge 方案索引（Hook num_bytes_allocated_ 扩展 Java 堆至 1G）

### 关联章节
23.3、23.4、23.6、20.5

## [2026-05-16] 13.14 Perfetto DataGrid 与 Jank CUJ 标准库 — 知识盲区

### 盲区描述
Perfetto v54 的 `android.cujs.base` 默认只把 `J<...>` CUJ slice 中的 `com.android.*` / `com.google.android*` 进程纳入 `android_jank_cuj`。章节目前缺少第三方 App、自定义 CUJ marker、AndroidX JankStats 与系统 FrameTracker CUJ 之间的适用范围边界，读者可能把系统 CUJ SQL 直接套到普通业务 App 滑动 trace 上。

### 重要程度
高

### 建议研究方向
- 复核 Perfetto v54 `android.cujs.base` / `threads` / `android_jank_cuj.sql` 对进程名、CUJ slice 名、FrameTracker counter 的过滤条件。
- 找一个系统 UI / Launcher trace 与一个第三方 App trace 对比，确认 `android_jank_cuj`、`android_jank_cuj_frame`、`android_jank_cuj_counter_metrics` 在两类 trace 中的表是否为空或字段差异。
- 梳理第三方 App 可执行方案：AndroidX JankStats、自定义 atrace/track event marker、自写 SQL 扩展 `_is_jank_slice` 过滤口径，以及与 FrameTimeline 的 join 边界。

### 关联章节
7.3, 7.4, 13.8, 13.10, 13.14

