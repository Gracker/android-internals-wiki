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

## [2026-05-17] 26.12 Android 版本化线上诊断能力：ApplicationExitInfo、ProfilingManager 与 ProfilingTrigger — 知识盲区

### 盲区描述
26.12 当前覆盖 ApplicationExitInfo、ProfilingManager 与 ProfilingTrigger，但版本化诊断表漏掉两类会影响线上归因的边界：
1. ApplicationExitInfo reason 常量的 API 级别差异：`REASON_FREEZER` 为 API 33；`REASON_PACKAGE_STATE_CHANGE` / `REASON_PACKAGE_UPDATED` 为 API 34；API 34 之前包更新和组件状态变化可能仍落到 `REASON_USER_REQUESTED`。
2. Android 15 / API 35 的 `ApplicationStartInfo` 启动追溯能力：`ActivityManager#getHistoricalProcessStartReasons()`、`addApplicationStartInfoCompletionListener()`、`START_TYPE_COLD` 与 `START_TIMESTAMP_*` 应进入慢启动诊断决策表，并与 Android 17 `TRIGGER_TYPE_COLD_START` 的触发前提对齐。

### 重要程度
高

### 建议研究方向
- 复核 Android Developers `ApplicationExitInfo` API reference 中各 `REASON_*` 的 Added in API level，并补一张 API 30 / 33 / 34 的 reason 差异表。
- 复核 AOSP `frameworks/base/core/java/android/app/ApplicationStartInfo.java` 与 `ActivityManager#getHistoricalProcessStartReasons()`，整理 Android 15 可拿到的启动原因、启动类型和关键时间戳。
- 对齐 8.10：`TRIGGER_TYPE_COLD_START` 的前提是 `ApplicationStartInfo.getStartType() == START_TYPE_COLD`，说明它和 Android 15 启动历史记录的分工。

### 关联章节
26.12、26.9、8.10、8.2、14.7



## [2026-05-17] 5.10 JobScheduler/WorkManager 调度与后台任务性能 — Android 17 excessive CPU / Power Check 机制边界

### 盲区描述
章节把 Android 17 “Power Check”写成缓存态应用 CPU 占用分级熔断、强制终止并自动生成 ProfilingTrace，但公开 Android 17 release notes 目前只能支撑 ProfilingManager 新增 `TRIGGER_TYPE_KILL_EXCESSIVE_CPU_USAGE`。缺少 framework/service 源码、官方 behavior changes 或实机触发记录来确认触发条件、阈值、kill 路径、trace 产物和 JobScheduler quota 的关系。

### 重要程度
高

### 建议研究方向
- 核对 Android 17 `ProfilingManager`、ActivityManager/PowerStats/JobScheduler 相关 framework 源码与 API reference。
- 搜索官方 behavior changes / release notes 中 excessive CPU kill 的精确定义，区分采集触发器与系统强杀策略。
- 在 Android 17 设备上构造 cached/background CPU hog，记录 logcat、ApplicationExitInfo、ProfilingManager 产物和 dumpsys jobscheduler 状态。

### 关联章节
5.10、5.6、5.8、26.9


## [2026-05-17] 7.6 案例集 — HWC Overlay plane 能力与 SF 合成降级证据

### 盲区描述
案例六需要证明“某设备因 Overlay plane 不足退回 CLIENT 合成”时，不能只写中端/高端 SoC 的通用 plane 数。需要设备级 HWC 能力、Layer composition type 和 FrameTimeline/SF jank 证据闭环。

### 重要程度
高

### 建议研究方向
- 收集目标设备的 `dumpsys SurfaceFlinger`、Layer trace / Winscope、Perfetto `android.surfaceflinger.frametimeline` 与 SurfaceFlinger slices。
- 对照 AOSP `CompositionEngine::Output::composeSurfaces()`、`RenderEngine::drawLayers()` 与 HWC `presentOrValidate()/validate()` 路径。
- 如引用 plane 数，必须来自厂商文档、HWC 日志或实机验证，不使用“中端通常 4 个 / 高端 6-8 个”的泛化结论。

### 关联章节
7.6、7.15、17.1

## [2026-05-17] 7.15 场景化性能作战手册 — 功耗/发热伴随卡顿排障入口

### 盲区描述
场景化手册覆盖启动、滑动、输入、SurfaceView、WebView、前后台、ANR 等入口，但缺“耗电/发热伴随卡顿”的独立路径。线上投诉常把掉帧、发热和掉电混在一起，需要先分辨 CPU/GPU 持续负载、热限频、wakelock、后台任务、网络重试和渲染负载。

### 重要程度
高

### 建议研究方向
- 补 Perfetto power rails、CPU/GPU frequency、thermal status、sched、FrameTimeline 的联合抓取模板。
- 补 Battery Historian / batterystats 与 wakelock、JobScheduler/WorkManager、网络重试的归因路径。
- 与 5.10、25.2 交叉引用，避免把后台任务功耗和前台渲染发热混成同一类。

### 关联章节
7.15、5.10、25.2


## [2026-05-17] 1.9 Package Manager Service 与应用安装性能 — Android 16 SDM / Cloud Compilation 源码链复核

### 盲区描述
章节需要把 Android 16 SDM / Cloud Compilation 的安装链路重新对齐到 AOSP：`.dm`、profile、`.sdm`、`.sdc` 的角色边界，以及 PackageInstallerSession、ArtManagedInstallFileHelper、ART Service、artd 之间的职责分工仍未形成可发布口径。

### 重要程度
高

### 建议研究方向
- 复核 AOSP android-16.0.0_r1 `PackageInstallerSession.verifySdmSignatures()`、`ArtManagedInstallFileHelper`、`ArtFileManager`、`Dexopter`、`PrimaryDexopter`。
- 区分 `cloudCompilationVerification()` / `cloudCompilationPm()` flag、`.dm` dex metadata、`.sdm` secure dex metadata、`.sdc` companion 文件。
- 用 Play 安装 Trace + `cmd package art dump` / `dumpsys package dexopt` 建立可观测边界，不写无来源收益数字。

### 关联章节
1.9、1.7、16.5

## [2026-05-17] 17.2 SoC 平台差异 — sched_ext OEM 调度器公开证据

### 盲区描述
章节列出的 Qualcomm SCX_Oplus、MediaTek SCX_Mtk、Google Pixel SCX_Litto 缺少公开可核对来源；sched_ext 在 Android common 6.12 中的存在不等于具体 OEM 设备默认启用，也不等于已有公开调度器实现可引用。

### 重要程度
高

### 建议研究方向
- 核对 Android common 6.12 `kernel/sched/ext.c`、`CONFIG_SCHED_CLASS_EXT` 与目标设备 kernel config。
- 查找 Qualcomm / MediaTek / Pixel vendor kernel tag 中可公开引用的 sched_ext BPF 程序名称和实现。
- 收集 Perfetto / ftrace / sysfs 证据，确认设备是否启用 sched_ext 以及对 top-app/game workload 的影响。

### 关联章节
17.2、5.1、5.4、17.1

## [2026-05-18] 5.8 后台执行限制与优化 — 16KB/GC/freezer 版本边界

### 盲区描述
5.8 当前把“系统压缩期间联动触发应用 GC”写成 Android 16/17 引入并绑定 16KB 页收益；已核到 source.android.com cached-apps-freezer 的基础口径是 Android 14+ cached/freeze 前 GC 与冻结后 compaction，但缺少 Android 16/17 或 16KB 专属增强的一手证据。

### 重要程度
高

### 建议研究方向
- 核对 `frameworks/base/services/core/java/com/android/server/am/CachedAppOptimizer.java`、`Freezer.java`、ART runtime GC 触发路径与 Android 14/15/16/17 tag 差异。
- 查找 source.android.com / AOSP release notes / commit 中是否存在 16KB page size 与 cached app compaction/GC 的直接关联。
- 若只存在 Android 14+ freezer 配套 GC，应回写为版本边界说明，不再作为 Android 16/17 或 16KB 专属变化。

### 关联章节
5.8、4.2、4.3、5.6


## [2026-05-18] 极客时间·线上疑难问题排查 — 参考书素材（文件 1-4）

### 来源
[结构参考: Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 1~4.md]

### 知识点
1. **Native 崩溃捕获四大难点**：fd 泄漏（需预留 fd）、栈溢出（需 signalstack）、堆内存耗尽（需绕过 libc/STL 用 Linux Syscall）、二次崩溃（Breakpad fork 子进程收集） → ch20.03 Native Crash分析与治理
2. **ANR 检测两种方案对比**：FileObserver 监听 /data/anr/traces.txt（高版本 ROM 权限受限）；监控消息队列运行时间（无法准确判定 ANR，更偏卡顿范畴） → ch26.04 ANR 监控体系
3. **崩溃现场信息采集五层框架**：崩溃信息（进程/线程/堆栈/类型）→ 系统信息（Logcat/机型/厂商/CPU）→ 内存信息（系统剩余/Java/RSS/PSS/虚拟内存）→ 资源信息（fd/线程数/JNI引用）→ 应用信息（场景/操作路径/自定义） → ch26.05 线上问题排查方法论
4. **崩溃分析三步法**：确定重点（严重程度+类型+Logcat+资源）→ 查找共性（机型/系统/ROM/ABI/应用维度聚合）→ 尝试复现 → ch20.08 崩溃聚合与归因分析
5. **系统崩溃 Hook 解法**：以 Android 7.0 Toast BadTokenException 为例，通过代理 Toast.mTN handler 捕获异常，参考 Android 8.0 源码做法 → ch20.09 稳定性治理案例集
6. **TimeoutException 根因与 Hook**：由 FinalizerWatchdogDaemon 抛出，通过源码分析→尝试 Stop()→寻找其他 Hook 点三步解决 → ch20.09
7. **Bitmap 内存分配版本演进**：Android 3.0 前（Java堆对象+Native像素）→ 3.0-7.0（统一Java堆）→ 8.0+（NativeAllocationRegistry+Hardware Bitmap）→ ch23.02 Bitmap与图片内存优化
8. **自定义 Allocation Tracker**：绕过 AS 限制实现自动化内存分析，Dalvik/ART 差异大（dvmEnableAllocTracker vs setAllocTrackingEnabled），兼容到 Android 8.1 → ch23.07 内存监控与线上治理

### 重要程度
中

### 建议加工方向
- ch20.03 可补充 Breakpad 四大难点的技术细节作为"实现原理"素材
- ch26.05 可补充"崩溃现场五层信息采集"作为排查方法论的结构化检查清单
- ch20.09 可收录 Toast BadTokenException 和 TimeoutException 两个经典系统崩溃案例
- ch23.02 可用 Bitmap 版本演进时间线作为"历史背景"段落
- ch26.04 可补充 FileObserver vs 消息队列两种 ANR 检测方案的对比分析



## [2026-05-19] 2.15 DMA-BUF、Gralloc 与跨进程图形内存共享 — Android 16/17 图形内存优化公开边界

### 盲区描述
libdmabufheap pooling、Binder FDA 批量 fd 安装、allocator AIDL `additionalOptions` / 16KB 页大小对图形 buffer 成本的关系需要重新拆分：哪些是 AOSP 通用能力，哪些是 Binder/Parcel 层实现细节，哪些只是 vendor allocator 或设备策略。

### 重要程度
高

### 建议研究方向
- 复核 `system/memory/libdmabufheap` 是否存在通用释放后缓存/按尺寸复用路径；若只有 vendor allocator 行为，必须限定实现来源。
- 追 Binder / Parcel native handle 传递路径，确认 FDA 是否参与 `GraphicBuffer::flatten/unflatten` 的 fd 安装，并补可定位源码路径。
- 用 android-15/16 tag 对比 `IAllocator.allocate2()`、`BufferDescriptorInfo.additionalOptions` 与 16KB page size 文档，拆清接口存在时间和实际用途。

### 关联章节
2.15、2.13、2.16、4.2


## [2026-05-20] 21.1/21.9 启动优化 — 参考书素材（极客时间 #9 #10）

### 来源
[结构参考: Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 9.md]
[结构参考: Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 10.md]

### 知识点
1. 启动4阶段模型（T1预览窗口→T2闪屏→T3主页→T4可操作），以及对应3个核心体验问题
2. systrace + ASM 函数插桩方案：降低性能损耗到1倍以内，覆盖主线程+子线程调用流程
3. 闪屏优化：预览窗口做闪屏（今日头条方案），合并闪屏与主Activity减少100ms
4. 启动框架 DAG 编排：Pipeline 机制（mmkernel/Alpha），防止主线程空转等待依赖任务
5. GC 监控：Debug.getRuntimeStat("art.gc.blocking-gc-time") 统计阻塞式同步 GC
6. 数据重排优化：ReDex Interdex 类重排 + 资源文件重排（修改7zip源码），减少磁盘I/O缺页中断，100-200ms提升
7. 类加载 verify 跳过：Dalvik 平台 gDvm.classVerifyMode 设为 VERIFY_MODE_NONE，2MB Dex 从350ms降到150ms
8. 启动线上监控指标：快开慢开比（2s快开/5s慢开）、P90启动耗时、区分冷/温/首次安装启动
9. 实验室监控：视频录制+80%绘制检测/图像识别，覆盖高中低端机
10. 保活/插件化/热修复对启动的负面影响量化分析（Tinker 加载补丁后启动慢5%-10%）

### 重要程度
高

### 建议加工方向
- ch21.01 可补充启动4阶段模型作为分析框架
- ch21.08 可补充快开慢开比、P90指标等线上度量方案
- ch21.09 可收录 DAG 编排空转案例、数据重排案例
- [需确认: verify 跳过在 Android 16/17 下已不可用，需标注版本限制]

## [2026-05-20] 24.1 文件I/O优化 — 参考书素材（极客时间 #11 #12 #13）

### 来源
[结构参考: Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 11.md]
[结构参考: Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 12.md]
[结构参考: Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 13.md]

### 知识点
1. Linux I/O 全链路：VFS → 具体文件系统(ext4/F2FS) → Page Cache → 通用块层 → I/O调度 → 驱动
2. Android 闪存演进：eMMC → UFS 2.0/2.1 → NVMe（iPhone），F2FS vs ext4 对比
3. 文件损坏三视角分析：应用程序（非原子操作/跨进程）、文件系统（断电丢失）、磁盘（闪存寿命/ECC）
4. 写入放大原理：闪存擦除以block为单位，低端机/老设备更严重；fstrim/TRIM 缓解
5. 三种I/O方式对比：标准I/O（Page Cache缓冲）、直接I/O（O_DIRECT绕Page Cache）、mmap（减少系统调用+数据拷贝）
6. mmap 适用场景与限制：小文件频繁读写、跨进程同步（Binder内部用mmap）；虚拟内存增大、磁盘延迟无法解决
7. 多线程阻塞I/O实验：30线程读40MB文件，收益递减（3.6s→1.1s），过多线程反而更慢
8. 小文件系统设计：目录查找性能瓶颈（FAT32线性 vs ext4 Hash索引），微信SFS方案
9. I/O线上监控：Native Hook（PLT/GOT Hook libc.so open/read/write/close）优于 Java Hook
10. 四类I/O问题检测规则：主线程I/O（>100ms）、Buffer过小（<4KB且>5次）、重复读（>3次且未更新）、资源泄漏（CloseGuard Hook）
11. Matrix I/O Canary 开源方案细节

### 重要程度
高

### 建议加工方向
- ch24.01 可补充三种I/O方式对比表、mmap适用场景、Buffer大小推荐实验数据
- ch26.03 可补充 I/O 线上监控四规则作为可观测性实战案例
- [需确认: F2FS 可靠性问题在 2026 年是否已解决，需更新]
- [需确认: eMMC 在当前市场占比已极低，相关内容可能需降级为历史背景]

## [2026-05-20] 19.09 Measure — Crash/ANR 与 native crash 能力边界

### 盲区描述
Measure 章节需要补齐错误监控能力边界：Android JVM crash、Android native crash、ANR、iOS crash、Flutter crash 的捕获方式与符号化材料不同。当前正文只写 Crash / ANR 自动捕获和 mapping / native symbol，未说明官方文档中 Android native C/C++ crash reporting 尚未支持，ANR 文档也提示 API 31 起 App Exit Info 可含 tombstone 但 native crash reports 尚未实现。

### 重要程度
高

### 建议研究方向
- 核对 `docs/features/feature-crash-reporting.md`：Android JVM crash 通过 `UncaughtExceptionHandler`，native C/C++ crash reporting not yet supported，R8/ProGuard mapping 上传路径。
- 核对 `docs/features/feature-anr-reporting.md`：ANR 通过 SIGQUIT / watchdog 采集，API 30 App Exit Info，API 31 native tombstone 说明与当前不支持边界。
- 核对 `docs/api/sdk/README.md` 的 `PUT /builds`：`mapping_type` 为 `proguard`、`dsym`、`elf_debug`、`jsbundle`，按 Android/iOS/Flutter/React Native 区分符号化材料。
- 产出“错误监控能力边界”表，避免把 Android native crash、iOS dSYM、React Native/Flutter 符号上传混成同一能力。

### 关联章节
19.09 Measure；19.0 APM 工具总览



## [2026-05-21] 26.5 线上问题排查方法论 — 参考书素材

### 来源
[结构参考: Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 14.md]

### 知识点
1. I/O 线上监控方案：Native Hook（PLT/GOT Hook on libc open/read/write/close）可低损耗采集全量 I/O 信息，性能可忽略不计；Java Hook（BlockGuardOs 动态代理）性能差且无法监控 Native I/O
2. 线上 I/O 不良规则抽象：主线程连续读写 >100ms、Buffer < block size 且读写 >5次、重复读同文件 >3 次、资源泄漏（CloseGuard Hook）
3. Matrix I/O Canary 实践：基于 GOT Hook 监控 libjavacore.so 等，覆盖 Java 层 I/O 调用

### 重要程度
高

### 建议加工方向
- 整理为「线上 I/O 监控方案选择」对比表：Java Hook vs Native Hook vs 插桩
- 提炼 I/O 不良规则为可配置的检测阈值模板

## [2026-05-21] 26.3 性能指标采集与上报 — 参考书素材

### 来源
[结构参考: Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 16.md]

### 知识点
1. 存储模块线上监控三要素：正确性（损坏率监控 + CRC 校验）、时间开销（初始化耗时 + 读写耗时）、空间开销（内存峰值 + ROM 占用）
2. ROM 整体监控：文件总大小异常率 + 文件数异常率 + 存储树剪枝上报 + 远程清理规则下发

### 重要程度
中

### 建议加工方向
- 整理为「存储监控指标体系」模板，含 SP 损坏率基准值（万分之一）
- ROM 存储树剪枝算法与上报策略

## [2026-05-21] 26.3 性能指标采集与上报 — 参考书素材

### 来源
[结构参考: Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 17.md]

### 知识点
1. SQLite 线上耗时监控：WCDB SQLiteTrace 三接口（busy/damage/耗时），EXPLAIN QUERY PLAN 本地测试
2. Matrix SQLiteLint 智能分析：基于 SQL 语法树自动检测索引使用不当、select* 等六大问题

### 重要程度
高

### 建议加工方向
- 整理 SQLite 线上监控方案对比：自研 Trace vs Matrix SQLiteLint
- 提供可落地的监控接入步骤

## [2026-05-21] 4.2 Linux 内核内存管理 — Android 17 ART MADV_COLD 协同

### 盲区描述
章节需要确认 Android 17 是否已有 ART GC → `madvise(MADV_COLD)` → MGLRU 的正式实现链。目前本轮核验未在 AOSP `platform/art` main 的 `runtime/gc` 源码中找到 `MADV_COLD` 调用，不能只凭 archived external-review 写成确定实现。

### 重要程度
高

### 建议研究方向
- 查找 Android 17 / API 37 release note、AOSP commit、ART `runtime/gc` 调用点，确认是否存在 GC 标记阶段对冷对象页调用 `MADV_COLD`。
- 核对 Linux `mm/madvise.c` 中 `madvise_cold_or_pageout_pte_range()`、`folio_deactivate()` 与 MGLRU 的实际交互，避免把 cold advice 简化成“直接降到更老 generation”。
- 若存在性能数据，补齐设备、内核分支、ART 配置、trace 指标与 jank/换入统计口径。

### 关联章节
4.2、4.3、4.4

## [2026-05-21] 22.3 Jetpack Compose 性能优化 — Compose 重组与 ART GC 数据闭环

### 盲区描述
章节把 Compose 重组分配压力与 ART Concurrent Copying / Young Generation GC pause 写成已源码验证的 Android 17 结论，但缺少固定 AOSP tag、正确 API level 口径、Perfetto/GC log 样本和 benchmark 条件。需要把“减少不必要重组可降低分配压力”与“具体 GC pause 数值”分开验证。

### 重要程度
高

### 建议研究方向
- 固定 Android 16 / Android 17 preview 的 ART 源码 tag，核对 `Heap::RequestConcurrentGCCollector`、generational CC、safepoint 相关路径和行号。
- 在 Compose 长列表滚动或重组 benchmark 中采集 Perfetto、logcat GC、分配数据，记录设备、刷新率、Compose Foundation、Compose Compiler/Kotlin 版本。
- 复核 Android 17 API level 与项目 `applicable_versions` 口径，避免把 preview 结论写进 Android 10-16 稳定范围。

### 关联章节
22.3、22.15、7.7、4.9

## [2026-05-22] 网络性能优化 — 参考书素材（极客时间 #18-#19）

### 来源
[结构参考: Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 18.md]
[结构参考: Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 19.md]

### 知识点
1. 无线网络基础知识：WiFi/蜂窝/蓝牙/NFC 各标准特性与适用场景，5G 基带芯片格局
2. Link Turbo 双通道聚合加速技术：WiFi + 蜂窝同时传输，MPTCP/MPUDP 原理
3. UNIX 网络 I/O 五种模型对比：阻塞/非阻塞/多路复用/信号驱动/异步，客户端场景下多路复用不一定优于阻塞 I/O
4. epoll vs select/poll 误区澄清：连接数少时 select 可能更快；epool 未使用 mmap
5. 网卡收发包流程：硬中断 + 软中断机制，/proc/softirqs、/proc/interrupts 监控接口
6. 网络性能评估指标体系：吞吐量/延迟/连接数/丢包，Linux 网络分析工具矩阵（ping/hping3/iperf3/netstat/ss/dropwatch/strace等）
7. 网络优化三大目标：速度（利用带宽）/弱网络（连通性）/安全（防劫持篡改）
8. 网络库横向对比：OkHttp（Android 单平台）/Chromium Cronet（跨平台标准）/Mars（跨平台弱网络优化），核心模块差异
9. HTTPDNS 解决 LocalDNS 三大问题：劫持/调度不准/TTL 修改，配合统一接入层做流量调度与容灾
10. 连接复用优化：HTTP/2 多路复用 + 统一接入层域名合并，但存在 TCP 队首阻塞
11. 数据压缩方案：gzip/Brotli/Z-standard + 业务字典训练，Protocol Buffers vs JSON 序列化对比
12. HTTPS 安全优化：TLS 1.3 0-RTT、ecc 证书替代 RSA、Session Ticket 复用、证书锁定
13. QUIC（HTTP/3）优势与坑：解决队首阻塞 + 0-RTT + 灵活拥塞控制，但 UDP 穿透性/运营商支持不足
14. IPv6 对网络性能的正向作用：减少 NAT，P2P/QUIC 连接不再受阻，印度测试连接耗时降低 10%-20%

### 重要程度
高

### 建议加工方向
- AIW 目前缺少独立的网络性能优化章节，建议在 Part 5 新增"网络性能"章节，覆盖上述知识点
- 以网络请求全链路（DNS→建连→收发→关闭）为主线组织内容，每步拆解优化手段
- QUIC/HTTP 3 现状需更新至 2025-2026 年实际落地情况（Chrome/Android Cronet 默认支持状态）
- HTTPDNS 部分可结合 DoH/DoT 等新标准补充
- 5G 内容需更新（SA/NSA、毫米波、载波聚合等当前部署现状）

### 关联章节
[章节待创建] Part 5 网络性能优化

---

## [2026-05-22] 网络可观测性与监控 — 参考书素材（极客时间 #20）

### 来源
[结构参考: Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 20.md]

### 知识点
1. 网络监控三种方法：插桩（Aspect 切面）/Native Hook（PLT Hook connect/send/recv）/统一网络库
2. PLT Hook 监控 Socket 的实现细节：排除 libc.so、过滤 Local Socket
3. TrafficStats 流量监控：基于 /proc/net/xt_qtaguid/stats，Android 7.0+ 权限收紧
4. 客户端网络质量监控维度：时延（DNS/建连/首包/总时间）/维度（网络类型/运营商/地域/版本）/错误（DNS失败/连接失败/超时）
5. 接入层监控互补：实时性强（秒级）/可靠性高（不受客户端上报通道影响）
6. 实时 vs 离线监控分层：实时（PV+错误率）/离线（全维度+UV）
7. 报警算法：规则驱动 vs 时间序列/神经网络智能报警，混合方案更优
8. WiFi 稳定性检测：网卡驱动层射频参数 + 协议栈 ACK 信息判断 WiFi 问题 vs 服务器问题

### 重要程度
高

### 建议加工方向
- AIW Part 5 可观测性章节需要包含网络监控体系
- PLT Hook 网络监控可归入"Native Hook 实践"段落
- 客户端+接入层双层监控架构是可观测性章节的核心内容
- 报警算法演进需要补充 2024-2026 年 AIOps 实际落地案例

### 关联章节
[章节待创建] Part 5 可观测性


## [2026-05-23] 25.2/25.3 功耗监控实战 — 参考书素材

### 来源
[结构参考: Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 22.md]

### 知识点
1. 耗电监控的 Java Hook 方案：通过 ProxyHook 代理 PowerManagerService/AlarmManagerService 实现对 WakeLock/Alarm 的 acquire/release/set/remove 的拦截
2. 耗电监控的插桩方案：封装 WakelockMetrics 基类替换直接调用，兼容 Android P+（Hook 失效场景）
3. Facebook Battery-Metrics 开源库：监控 Alarm/WakeLock/Camera/CPU/Network 并采集充电状态和电量水平
4. 华为安卓绿色联盟后台资源使用"红线"规则表（后台 WakeLock 时长/Alarm 频次/网络使用等具体阈值）

### 重要程度
中

### 建议加工方向
- 补充 Hook 方案在 Android P+ 的替代策略对比
- 华为红线规则可作为 ch25.2 后台功耗治理的厂商实例参考

## [2026-05-23] 22.2 UI 优化实战 — 参考书素材

### 来源
[结构参考: Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 24.md]

### 知识点
1. 异步创建 View 的 Looper MessageQueue 替换技巧：将工作线程 Looper 的 MessageQueue 临时替换为 UI 线程的 Queue，创建完成后恢复
2. View 跨 Activity/Fragment 缓存复用机制（参考微信实践经验，需注意状态清理防止错乱）
3. Litho 的三大优化：异步布局（measure/layout 移到后台线程）、界面扁平化（Yoga 引擎自动消除多余层级）、RecyclerView 按组件类型独立回收
4. PrecomputedText 异步 measure/layout（Jetpack 集成）
5. RenderScript 用于图片密集计算（高斯模糊、扫一扫场景的缩放/裁剪/二值化/降噪）

### 重要程度
中

### 建议加工方向
- Litho 的异步布局思路可作为 ch22 渲染优化实战的"突破系统限制"方案参考
- 异步创建 View 的 Looper 替换方案可作为 ch22 的进阶技巧

## [2026-05-23] 25.6/25.7 APK 深度优化 — 参考书素材

### 来源
[结构参考: Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 25.md]

### 知识点
1. ReDex StripDebugInfoPass：保留行号但去除局部变量/debug info，减少约 5% Dex 体积
2. ReDex InterDexPass（CrossDexDefMinimizer）：贪心算法优化 Dex 分包，减少跨 Dex 方法引用冗余，4+ Dex 场景可减少 10%+ 体积
3. Facebook 的 XZ 压缩 Dex 方案：secondary.dex.jar.xzs，XZ 比 Zip 压缩率高 30%
4. ReDex oatmeal：直接在本进程按 ODEX 格式生成 ODEX 文件，10MB Dex 从 10s+ 降到 ~100ms
5. 四大组件和 View 混淆方案：XML 替换 + ASM 代码替换（参考饿了么 Mess 开源组件）
6. Native Library 合并（Buck）：Android 4.3 之前进程加载 Library 数量限制的应对
7. Native Library 裁剪（Buck relinker）：分析 JNI 调用链，删除无用导出 symbol，实现 Library 级别的 ProGuard Shrinking

### 重要程度
高

### 建议加工方向
- ReDex 三大 Pass（StripDebugInfo/InterDex/oatmeal）可作为 ch25.7 R8 与资源优化的进阶补充
- Library 合并/裁剪方案可作为 ch25.6 APK 分析的 Native 优化方向
- XZ 压缩方案可作为极致优化案例补充到 ch25.6



## [2026-05-25] 26.8 可观测性案例集 — 参考书素材

### 来源
[结构参考: Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 31.md]

### 知识点
1. 基于大数据的"实时质量"体系：分钟级质量数据采集+业务数据校验+风险感知
2. 舆情监控系统架构：爬取用户反馈/应用市场/微博/新闻，实时分析产品舆情

### 重要程度
中

### 建议加工方向
- "实时质量"体系可作为 ch26.8 可观测性案例集的大数据驱动测试案例
- 舆情监控可作为 ch26.8 的外部信号采集补充

## [2026-05-25] 26.6 A/B Test 与性能回归防护 — 参考书素材

### 来源
[结构参考: Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 32.md]

### 知识点
1. A/B 测试"同质同时"原则：同质人群、同一时间、除方案变量外其他变量一致
2. 最小样本量计算器：基准线指标值 + 最小相对变化 + 统计功效(1−β) + 显著性水平(α)
3. A/A/B 测试模式：先做空转测试验证分流科学性，再做正式 A/B 测试
4. A/B 测试天数计算：所需天数 ≥ 计算用户数 / (日均流量 × 流量百分比)

### 重要程度
高

### 建议加工方向
- "同质同时"原则和最小样本量计算器是 ch26.6 A/B Test 的核心统计基础，建议补充
- A/A/B 测试模式是提升 A/B 可信度的最佳实践

## [2026-05-25] 26.3 性能指标采集与上报 — 参考书素材

### 来源
[结构参考: Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 33.md]

### 知识点
1. 多进程写 + mmap 存储架构：完全无锁、无 IPC、数据基本不丢失（微信实践）
2. UV 采样 + 用户标识哈希 + 每日轮换算法：Hash(id) % N == (timestamp/86400) % N
3. 班车制上报 + FileObserver + rename 原子性：多进程文件同步无需跨进程锁
4. 埋点验证平台：实时扫码验证 + 灰度非实时验证，自动规则校验（漏字段/多字段/违规值）

### 重要程度
高

### 建议加工方向
- 微信 mmap 上报组件架构可作为 ch26.3 采集与上报的核心案例
- UV 采样轮换算法和班车制上报是生产级上报组件的关键设计模式
- 埋点验证平台可作为 ch26.3 的数据质量保障补充

## [2026-05-25] 26.5 线上问题排查方法论 — 参考书素材

### 来源
[结构参考: Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 35.md]

### 知识点
1. Xlog（Mars）高性能日志方案：全量用户全天候日志，mmap 落盘，已开源
2. Logan（美团）统一日志平台：整合代码日志/崩溃日志/埋点日志/行为日志
3. 远程调试实现：JDWP over 网络通道，绕过 adb，需要处理 ProGuard 和 Debugable
4. Lua 脚本远程控制：200KB VM，动态执行代码/获取对象快照/查询 DB/上报信息
5. 全链路追踪：traceId 串联客户端/服务端/CDN 日志，参考 Dapper/EagleEye/点击流

### 重要程度
高

### 建议加工方向
- Xlog + Logan 可作为 ch26.5 线上排查的核心日志工具方案
- 远程调试和 Lua 脚本控制可作为 ch26.5 的进阶排查手段
- 全链路追踪可作为 ch26.5/ch26.17 的跨层排查方法论

## [2026-05-27] 18.10 SurfaceControl API 深入 — 知识盲区

### 盲区描述
缺少跨进程SurfaceControl共享的完整实现路径。当前章节提到了Java层的Parcelable能力，但未详细说明native层面如何实现跨进程的ASurfaceControl句柄传递和同步机制。

### 重要程度
高

### 建议研究方向
- 深入研究AOSP android-16.0.0_r1中surface_control.h的跨进程机制
- 分析SurfaceControl在WindowManager/Shell中的跨进程管理模式
- 补充完整的应用场景：WebView OOP、画中画、跨进程UI组件的具体实现示例

### 关联章节
- 18.2 SurfaceFlinger基础
- 13.14 WebView渲染管线
- 2.6 SurfaceFlinger架构基础

## [2026-05-27] 2.23 SurfaceFlinger VSync Scheduler 与 DisplayFrameRate 策略 — 知识盲区

### 盲区描述
VSyncPredictor在不同SoC厂商的实现差异和硬件适配特性。当前章节主要基于AOSP标准实现，但实际在不同厂商设备上可能存在定制化实现，影响预测准确性和调度效率。

### 重要程度
高

### 建议研究方向
- 研究主流SoC厂商（Qualcomm、MediaTek、Samsung等）对VSyncPredictor的定制实现
- 分析不同硬件VSync源（HW_VSYNC_0、TE信号等）对预测算法的影响
- 收集实际设备上的调度问题案例和厂商优化方案

### 关联章节
- 2.3 VSync基础原理
- 2.18 Android图形栈架构
- 8.8 多媒体管线性能
