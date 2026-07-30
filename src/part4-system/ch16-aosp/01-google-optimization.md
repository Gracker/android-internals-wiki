---
title: "Google 官方的性能优化思路"
section: "16.1"
chapter: "16.1"
status: finalized
drafted_date: "2026-04-10"
drafted_by: "openclaw-task2a"
reviewed_date: 2026-07-02
reviewed_by: openclaw-task6
applicable_versions: "Android 4.1 (API 16) - Android 17 (API 37)"
last_verified: "2026-07-30"
last_verified_against: "AOSP android-17.0.0_r1（ART/MessageQueue/Binder/BLAST/WMS）+ android17-6.18-2026-06_r6（Binder driver）+ Android 17 官方文档"
confidence: high
tags:
  - android
  - performance
  - aosp
pipeline_stage: ready-to-publish
task6_state: reviewed
task9_state: reviewed
task9_result: pass-tech-review
task9_reviewed_date: "2026-07-13"
task9_reviewed_by: openclaw-task9
last_task9_at: "2026-07-13T17:33:00+08:00"
last_task9_audit: "2026-07-13"
last_task9_autofix_at: "2026-07-01"
last_task9_review_log: "logs/deep-review/2026-07-13-17-deep-review.md"
last_task9_review_notes: "2026-07-13 Task9 deep review 发现 P0/P1 问题：1) CombinedMessageQueue路径不存在，实际为CombinedDeliMessageQueue；2) Binder线程池描述未说明总并发路径。P0 1 / P1 1 / P2 0；不可自动晋升，需 Task6 复审。P0/P1 问题已写入 queue.json，建议优先修复源码路径错误和并发描述不完整问题。"
last_task6_at: 2026-07-13T18:18:50+08:00
task2b_state: fixed
task2b_result: fixed-lite
task2b_fixed_at: "2026-06-26T11:40:00+08:00"
last_task2b_at: "2026-06-26T11:40:00+08:00"
task6_result: pass-light-edit
last_task6_audit: "2026-07-13"
last_task6_audit_log: "logs/review/2026-06-30-23-audit.md"
last_task6_at: 2026-07-13T18:18:50+08:00
task6_review_notes: "2026-07-13 Task6 re-review (revisiting after Task9 deep review + Task2B-lite fix): pass-light-edit。Task2B-lite 已修复 P0 CombinedMessageQueue→CombinedDeliMessageQueue（正文/frontmatter 全部正确）和 P1 Binder 16 并发路径描述。L1 禁用词扫描：零命中（对齐仅出现在 ELF segment 对齐技术语境）。L2 可读性通过。无 B 类回炉项。送 Task9 复审确认。"
last_task2b_lite_at: "2026-07-13"
sources:
  - type: official
    path: "https://developer.android.com/about/versions/jelly-bean"
  - type: official
    path: "https://developer.android.com/about/versions/kitkat"
  - type: official
    path: "https://developer.android.com/about/versions/17/release-notes"
  - type: official
    path: "https://developer.android.com/about/versions/17/behavior-changes-17"
  - type: official
    path: "https://developer.android.com/topic/performance/baselineprofiles/overview"
  - type: official
    path: "https://source.android.com/docs/core/ota/modular-system"
  - type: official
    path: "https://source.android.com/docs/core/architecture/hidl/binder-ipc"
  - type: official
    path: "https://source.android.com/docs/core/architecture/kernel/android-common"
  - type: official
    path: "https://source.android.com/docs/core/architecture/kernel/gki-android17-6_18-release-builds"
  - type: official
    path: "https://source.android.com/docs/core/architecture/16kb-page-size/16kb"
  - type: official
    path: "https://source.android.com/docs/core/runtime/configure"
  - type: official
    path: "https://source.android.com/docs/core/runtime"
  - type: official
    path: "https://source.android.com/docs/core/architecture/partitions"
  - type: official
    path: "https://android-developers.googleblog.com/2026/02/under-hood-android-17s-lock-free.html"
  - type: official
    path: "https://android-developers.googleblog.com/2026/03/BoostingAndroid%20PerformanceIntroducingAutoFDO.html"
  - type: aosp
    path: "https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/os/LegacyMessageQueue/MessageQueue.java"
  - type: aosp
    path: "https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/os/CombinedDeliMessageQueue/MessageQueue.java"
  - type: aosp
    path: "https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/app/ActivityThread.java"
  - type: aosp
    path: "https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/java/com/android/server/SystemServer.java"
  - type: aosp
    path: "https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/libs/binder/ProcessState.cpp"
  - type: aosp
    path: "https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/libs/gui/BLASTBufferQueue.cpp"
  - type: aosp
    path: "https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/runtime/gc/collector/mark_compact.cc"
  - type: kernel
    path: "https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/drivers/android/binder.c"
deepseek_cn_review_state: done
last_deepseek_cn_review_at: 2026-07-13
---

# Google 官方的性能优化思路

<!-- outline-start -->
## 本节要点大纲
### 锚点(必须覆盖)
- 🔹 Google 性能优化的核心理念:Systemic Performance、User-Perceived Performance
- 🔹 各版本的 Performance 旗舰特性:Project Butter(4.1) → Svelte(4.4) → ART(5.0) → Treble(8.0) → Mainline(10)
- 🔹 Android Runtime (ART) 的持续优化方向
- 🔹 Framework 层的性能优化实践(View 系统、Handler、Binder、窗口管理)
- 🔹 Google 官方的 Performance 文档与最佳实践总结
### 扩展(可选深入)
- 🔸 Android Go Edition 的性能优化策略
- 🔸 Google 内部的性能测试基础设施(公开信息)
<!-- outline-end -->

## 为什么要了解 Google 的性能优化思路
VSync、Binder、ART、内存回收和 BufferQueue 分属不同子系统，性能改动却经常遵循同一条工程路径：确定用户能感知的场景，找到跨层等待或资源浪费，修改平台机制，再用基准测试与线上数据检查副作用。

掌握这条路径有三项用途：

- 分清平台瓶颈与 App 自身问题，避免把主线程 I/O 归咎于系统调度，也避免用 App 侧规避方案掩盖 framework 回归。
- 理解工具的测量对象。Macrobenchmark 测关键用户旅程，Perfetto 解释跨进程时序，Android Vitals 观察线上结果，Baseline Profiles 改变代码编译状态。
- 正确阅读版本变化。Project Butter、ART、Treble、Mainline 和 Android 17 DeliQueue 作用在不同层，不能都概括成“系统更快”。

## 核心理念:两层性能观
“Systemic Performance”和“User-Perceived Performance”适合作为阅读框架，不是 AOSP 中两个固定模块。前者讨论平台提供的能力与成本，后者讨论启动、响应、帧、内存和功耗怎样影响用户。

### 系统层（Systemic Performance）

系统层包括内核、ART、Binder、图形合成、I/O、系统服务与构建工具链。一次平台优化可能让大量 App 受益，也可能只覆盖特定 SoC、构建配置或 targetSdk。

AutoFDO 能说明这个边界。官方 2026 年 3 月文章分别讨论了两类产物：

- Android userspace 的 native executable 和 library 已使用 AutoFDO；
- GKI 的 AutoFDO 当时部署到 `android15-6.6` 与 `android16-6.12`，并计划扩展到 `android17-6.18`。

这不支持“Android 17 所有系统 native binary 和所有内核模块都自动带 profile”的说法。内核文章明确把当前范围限定在主内核映像 `vmlinux`，GKI module 和 vendor module 仍列为后续方向。判断设备是否启用时，应检查对应构建配置、profile 产物和 boot image，不能只看 Android 版本号。

### 用户感知层（User-Perceived Performance）

用户感知层关心冷启动多久出现可用内容、输入多久得到反馈、动画是否按显示周期提交、前台进程是否发生 ANR 或低内存终止。CPU 利用率、锁等待和函数耗时用于解释这些现象，单独拿出来不能代表体验。

Android Vitals 以用户感知 ANR 等线上指标观察结果，Macrobenchmark 在可控环境复现启动、滚动和页面切换，Perfetto 再解释每个阶段的等待。系统优化提高公共路径的效率，App 仍需控制主线程 I/O、同步 Binder、初始化顺序和每帧分配。

## 版本旗舰特性:一条清晰的演进线
下面的时间线包含运行时优化、低内存适配和系统模块化。Treble 与 Mainline 主要改变接口和交付方式，本身不等同于一次运行时提速。

### Project Butter(Android 4.1,2012)
Project Butter 把 UI 工作组织到显示节奏上：VSync 驱动 `Choreographer` 安排 input、animation 和 traversal，图形管线通过多缓冲降低 CPU、GPU 与合成阶段互相等待的概率。它确立了按帧预算分析流畅度的方式。后续的 RenderThread、FrameMetrics、Frame Timeline 与 Frame Pacing 都沿用这种观察尺度。

### Project Svelte(Android 4.4,2013)
Project Svelte 面向 512 MB RAM 设备，重点是系统与预装应用的内存占用、后台进程成本和低内存可观测性。Android Go Edition 延续了低资源设备基线，但 App 仍需按自己的进程、资源和后台任务验证，不能把 Go 设备视为统一硬件型号。

### ART 替代 Dalvik(Android 5.0,2014)
Android 5.0 默认使用 ART，并在安装阶段执行 AOT 编译。全量 AOT 会增加安装时间和磁盘占用，Android 7.0 起改为 interpretation、JIT 与 profile-guided AOT 的混合模式。Cloud Profiles、Baseline Profiles 和 Startup Profiles 分别介入 profile 分发、关键方法预编译和 DEX 布局，三者不能互换。

### Project Treble(Android 8.0,2017)
Treble 通过稳定的 framework/vendor 接口降低系统框架升级对 vendor implementation 的耦合。它改善的是升级边界，不能据此推导某个 API 调用或渲染阶段会变快。性能改动能否到达某台设备，仍取决于模块归属、厂商集成和 OTA。

### Project Mainline（Android 10，2019）：拆分系统能力与交付路径

Android 10 引入 Mainline 后，部分系统组件可以通过 Google Play system update 或合作方 OTA 以 APEX/APK 模块更新。ART 从 Android 12 起属于可更新模块。分析某项优化的覆盖范围时，要分开三条交付路径：

- Mainline 模块更新覆盖 ART、DNS Resolver 等被模块化的系统组件；
- GKI 与 vendor kernel 通过内核或整机 OTA 交付；
- Baseline Profile 随 APK/AAB 发布，Cloud Profile 由 Google Play 在安装或后台编译阶段提供。

Android 17 的 generational CMC 属于 ART 版本能力。它能否回到旧平台，需要查设备上的 ART module release 和兼容策略；“ART 可更新”不能直接推出“所有旧设备会获得 Android 17 GC”。

### Android 16 → Android 17：关键性能跃迁

| 层 | 可验证的版本变化 | 阅读边界 |
|---|---|---|
| ART | Android 17 release notes 公布 generational CMC；`mark_compact.cc` 提供 `YoungMarkCompact`，`ShouldUseGenerationalGC()` 的系统属性默认值为 `true` | ART flag、DeviceConfig 和设备模块版本仍会影响启用状态 |
| MessageQueue | Android 17 上，targetSdk 37+ App 按兼容性变更使用 DeliQueue；官方行为变更页面提示反射私有字段的兼容风险 | 系统进程和实验 flag 还有独立选择路径 |
| GKI | Android 16 的新 GKI 基线是 `android16-6.12`；Android 17 的新基线是 `android17-6.18` | Android 平台向后兼容多条受支持 GKI，不能把平台版本与唯一内核版本画等号 |
| 16 KB page size | AOSP 从 Android 15 起支持 16 KB page size 与 16 KB ELF alignment；Android 16 增加 prebuilt alignment 检查选项 | Android 17 不是该能力的首次正式版本 |

本书的 Android 17 内核新基线固定到 `android17-6.18-2026-06_r6`。该 tag 在 2026 年 6 月 release build 系列中可追溯；同一 Android 17 平台仍可能搭配官方兼容表中的旧 GKI 分支。涉及 framework 行为时看 `android-17.0.0_r1`，涉及 Binder driver、调度或内存回收时再看指定 kernel tag。

对 App 性能分析而言，`SDK_INT`、targetSdk、ART module、kernel release 和设备配置都是独立变量。Android 17 设备上的 targetSdk 36 App 按公开行为合同保留 legacy MessageQueue，targetSdk 37+ App 才进入新兼容路径。

## ART 的持续优化方向
ART 的性能改动可以沿编译状态、垃圾回收和 DEX 组织三条线阅读。

### 编译策略:从 AOT 走向 Profile-Guided
官方 ART 配置文档给出的 Pixel 流程是：安装时若带 Cloud Profile，ART 对 profile 中的方法做 AOT；其余方法先解释执行，热点方法再 JIT；设备空闲充电时，后台编译服务根据本地 profile 与 cloud profile 重新编译。

Baseline Profile 让开发者把关键代码路径随应用发布，减少首轮使用等待动态 profile 成熟的时间。官方文档中的“约 30%”是一些应用常见的代码执行速度改善，不是冷启动总时长的固定收益。I/O、Binder、资源加载或网络占主导时，profile 无法消除这些等待。

### GC：从 Concurrent Copying 到 Generational CMC

Android 17 release notes 将 generational garbage collection 列为性能变化：Concurrent Mark-Compact 优先执行频繁、成本较低的 young collection。`android-17.0.0_r1` 的 `mark_compact.cc` 可以核对三处实现边界：

- `YoungMarkCompact::RunPhases()` 让主 collector 进入 young-generation 路径；
- `ShouldUseGenerationalGC()` 读取 ART flag 与 `persist.device_config.runtime_native_boot.use_generational_gc`；
- 该属性的代码默认值是 `true`，虚拟设备和配置开关仍可改变行为。

因此，“Android 17 默认具备 generational CMC”可以作为平台锚点；某次 trace 使用了哪类 GC，还要检查 ART event、进程配置和设备 module build。暂停时长、回收频率与内存收益必须在目标 workload 上测量，官方 release notes 没有给出适用于所有设备的固定数字。

### 工具链：R8、D8 与 Startup Profiles

R8 执行 shrink、optimization 和 class/member rewriting，D8/R8 生成 DEX。体积减小不保证冷启动等比例变快，因为收益还受类加载顺序、压缩、存储、page cache 和编译状态影响。

Baseline Profile 指定应提前编译的关键路径；Startup Profile 的重点是 DEX layout，让启动期类和方法在文件中靠近，减少启动阶段的 major page fault。构建后应检查 APK/AAB 中的 profile、安装后的编译状态，再用 Macrobenchmark 与 Perfetto 确认效果。

## Framework 层的性能优化实践
Framework 改动经常改变 App、system_server 和 native service 之间的等待关系。阅读时要同时看公开行为合同、同一 tag 的实现和 trace 证据。

### View 系统:持续减主线程负担
View 绘制不能只看 UI thread。主线程处理 input、animation、measure、layout 和 display-list recording；RenderThread 消费渲染节点并驱动 GPU 工作；SurfaceFlinger 负责系统合成。RenderThread 减少了一部分主线程绘制工作，却没有移走 View 树遍历、业务代码和同步点。

诊断掉帧时应按 Frame Timeline 区分 App deadline 与 SurfaceFlinger deadline，再查看 UI thread、RenderThread、GPU fence 和合成阶段。只优化 `onDraw()` 或只看主线程 CPU 都可能漏掉瓶颈。

### Handler / MessageQueue：legacy 队列和 Android 17 新队列的区别
Legacy MessageQueue 用一把 monitor 保护按 `when` 排序的单链表。生产者插入的最坏复杂度是 O(N)，Looper 取队首是 O(1)；生产者和消费者访问同一状态时可能发生锁竞争。

Android 17 的 DeliQueue 将并发入队与单线程排序分开：

- 生产者用 CAS 向 Treiber stack 入队，调用线程的入队复杂度为 O(1)；
- Looper 将新消息整理进自己独占的 min-heap，处理成本按官方说明摊销为 O(log N)；
- 跨线程移除先写 tombstone，再由 Looper 清理结构；
- idle handler 与 file-descriptor listener 等辅助状态仍使用各自的锁，因此“lock-free MessageQueue”不代表类中没有任何 `synchronized`。

在 `android-17.0.0_r1` 中，源码由构建变体提供两条路径：

- `LegacyMessageQueue/MessageQueue.java` 是兼容实现；
- `CombinedDeliMessageQueue/MessageQueue.java` 同时含 legacy 与 DeliQueue 代码，`USE_NEW_MESSAGEQUEUE` 标注 `@EnabledAfter(targetSdkVersion = BAKLAVA)`，`computeUseDeliQueue()` 还会读取 compat change 与实验 flag。

公开行为合同是 Android 17 上 targetSdk 37+ App 使用新实现。system_server 会在创建 main Looper 前调用 `MessageQueue.setUseDeliQueue(true)`，App 进程则由启动参数决定传入值；测试或 flag 还可能改变选择。`getImplName()` 是 `@hide` 诊断接口，普通 SDK App 不应依赖它。分析 `Handler.post()` 时，至少记录系统 build 与 targetSdk，并用 MessageQueue dump 或 Perfetto contention 证据确认实现。

### Binder：线程池与优先级继承的时间线
`ProcessState.cpp` 将 `DEFAULT_MAX_BINDER_THREADS` 设为 15，并用 `BINDER_SET_MAX_THREADS` 配置 driver。调用 `startThreadPool()` 还会主动创建一条 main pooled thread；`getThreadPoolMaxTotalThreadCount()` 的基础计算正是 `1 + mMaxThreads`。工程里常说的“默认 16 条”由此而来。

这 16 条属于目标进程的 Binder thread pool 容量，不包含某个客户端发起事务的线程，也不表示一次事务会并行使用 16 条线程。进程还可能直接调用 `IPCThreadState::joinThreadPool()`；源码说明这种额外 join 无法由 `mKernelStartedThreads` 完整统计。排查线程池饥饿时，应从目标进程实际 thread state、Binder transaction 排队和 runnable 延迟取证。

在 `android17-6.18-2026-06_r6` 的 `drivers/android/binder.c` 中，优先级处理有几项限制：

- 只有同步事务且调用线程使用 driver 支持的调度策略时，事务才记录调用线程的 policy 与 priority；oneway 事务使用目标进程默认优先级；
- `binder_transaction_priority()` 还会合并 Binder node 的 minimum priority；
- RT policy 只有 node 设置 `inherit_rt` 时才保留，否则回退到 `SCHED_NORMAL`；
- driver 在处理事务时保存目标线程原优先级，并在 reply、错误或回到等待路径时恢复。

Perfetto 中的高 nice/RT server slice 要结合 transaction 类型和 Binder node 配置解释。长事务、线程池满载、CPU 调度延迟与优先级继承是四类不同问题。

### 窗口管理:BLASTBufferQueue 优化 buffer 与 transaction 的同帧提交
BLASTBufferQueue 没有删除 BufferQueue。`BLASTBufferQueue.cpp` 仍创建 `BufferQueueCore`、producer 与 consumer；它增加的是 buffer acquire 与 `SurfaceControl::Transaction` 按 frame number 协调的机制。

同一文件中的 `syncNextTransaction()`、`mergeWithNextTransaction()` 和 `applyPendingTransactions()` 分别展示等待下一 buffer transaction、按 frame number 保存待合并 transaction、取得并应用 pending transaction。它们共同说明机制，不能写成每次提交都严格按这三个函数直接顺序调用。

跨窗口同步还要看 WMS 的 `BLASTSyncEngine`。它收集参与 sync group 的窗口 transaction，在 ready 后合并并提交。由此减少内容 buffer 与窗口几何/层级状态跨帧错位的概率；能否同帧呈现仍受生产者出帧、fence、GPU 和 SurfaceFlinger deadline 影响。

## Google 官方的 Performance 工具与文档体系
工具应按问题阶段选择，不能用同一份 profiler 数据同时代替基准、归因和线上监控。

### 文档入口
`developer.android.com/topic/performance` 是 App 性能总入口。版本 release notes 说明平台能力，behavior changes 说明运行版本与 targetSdk 门槛，`source.android.com` 说明系统架构与设备集成，AOSP tag 则用于验证实现。DeliQueue 就需要把四层资料放在一起读。

### 度量、分析、优化三类工具

- **度量**：Microbenchmark 测进程内代码路径，Macrobenchmark 测启动、滚动和切换等应用场景，Android Vitals 观察生产环境分布。
- **分析**：Perfetto 观察跨线程、跨进程时序，simpleperf 分析 native CPU sample，Android Studio Profiler 用于交互式检查单个进程。
- **优化与交付**：Baseline/Startup Profiles 改善编译与 DEX layout，R8 缩减和优化代码，App Startup 管理初始化依赖。

### 一轮可审计的优化

1. 用用户动作定义 Critical User Journey，并写清起点、终点与成功条件。
2. 建立 release/profileable 构建基线，记录设备、温度、刷新率、编译状态和样本分布。
3. 用 trace 或 sample 将长尾归因到线程、进程、锁、I/O、GC、GPU 或系统服务。
4. 每次修改一个主要变量，并同时检查目标指标、资源成本和稳定性指标。
5. 把同一指标放进 CI 与生产监控，发现回归时保留版本、设备和 trace 证据。

## 不同设备类型的优化策略差异

“旗舰、中端、低端”缺少稳定的技术定义，RAM 数量也不能代表 CPU、存储和散热能力。更可靠的测试样本按瓶颈维度选设备：

| 维度 | 需要记录 | 容易暴露的问题 |
|---|---|---|
| CPU | 核心拓扑、频率、调度与 thermal state | 主线程 runnable delay、JIT/编译、锁竞争 |
| 内存 | 物理内存、swap/zram、memory pressure | GC、LMK、后台重启、大对象峰值 |
| 存储 | 文件系统、顺序/随机读取、page cache 状态 | 冷启动 fault、数据库与资源加载 |
| 图形 | GPU、驱动、分辨率、刷新率 | RenderThread、GPU fence、合成 deadline |
| 系统 | build、ART module、kernel、targetSdk | 行为门槛和平台差异 |

Android Go 设备应纳入低资源样本，但不能代替整个长尾。高刷新率高分辨率设备也可能比低价设备更容易暴露 GPU 与帧预算问题。每个优化结论至少要说明在哪些维度上验证过。

## Google 内部的性能测试基础设施
公开资料能确认的范围有限：

- DeliQueue 团队用 BigTrace 在大量 Perfetto trace 上查询 MessageQueue contention，并在模拟器和真实硬件上运行 stress test；
- 内核 AutoFDO 团队在受控实验室用 simpleperf、ARM ETE/TRBE 和代表性 App workload 采集 profile，再比较 profile、binary、benchmark 与稳定性；
- AOSP 仓库提供 unit test、integration test、benchmark 与兼容性测试基础设施。

这些信息支持“数据发现—受控修改—持续验证”的流程，不足以描述 Google 内部全部设备池、门禁阈值或发布系统。没有公开来源的内部平台名称和规模不应写入正文。

## 常见问题与误区
### "系统已经越来越快了,App 端不用太管"
系统优化可以缩短公共路径，无法替应用移除主线程 I/O、同步 Binder 和过早初始化。平台升级后仍要重新测量原来的 Critical User Journey，因为编译状态、targetSdk 行为和设备配置也可能变化。

### "Baseline Profiles 能包治启动慢"
Baseline Profiles 让关键路径更早获得合适的编译状态。主线程 I/O、数据库锁、同步 Binder、资源解码和网络等待仍需分别处理。检查 profile 是否安装成功后，还要用 trace 比较编译 CPU time 与启动总时长。

### "升级 Android 版本，性能自然会整体变好"
新系统可能改进 ART、MessageQueue 或图形管线，也可能增加安全检查、行为限制和迁移成本。结论必须绑定 App targetSdk、设备 build、ART module、kernel、编译状态与测试场景。

## 参考资料
- AOSP / 官方源码路径
  - [Choreographer（VSync 驱动的帧调度入口）](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/view/Choreographer.java)
  - [Legacy MessageQueue](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/os/LegacyMessageQueue/MessageQueue.java)
  - [Combined DeliQueue MessageQueue](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/os/CombinedDeliMessageQueue/MessageQueue.java)
  - [ActivityThread 的 DeliQueue 启动参数](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/app/ActivityThread.java)
  - [SystemServer 启用 DeliQueue](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/java/com/android/server/SystemServer.java)
  - [ART MarkCompact / YoungMarkCompact](https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/runtime/gc/collector/mark_compact.cc)
  - [ProcessState Binder thread pool](https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/libs/binder/ProcessState.cpp)
  - [BLASTBufferQueue](https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/libs/gui/BLASTBufferQueue.cpp)
  - [WMS BLASTSyncEngine](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/wm/BLASTSyncEngine.java)
  - [Binder driver（android17-6.18-2026-06_r6）](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/drivers/android/binder.c)
- 官方文档
  - [Jelly Bean：VSync、triple buffering 与 touch latency](https://developer.android.com/about/versions/jelly-bean)
  - [KitKat：512 MB 设备与低内存优化](https://developer.android.com/about/versions/kitkat)
  - [App performance guide](https://developer.android.com/topic/performance/overview)
  - [Baseline Profiles overview](https://developer.android.com/topic/performance/baselineprofiles/overview)
  - [Android 17 release notes](https://developer.android.com/about/versions/17/release-notes)
  - [Android 17 behavior changes](https://developer.android.com/about/versions/17/behavior-changes-17)
  - [Android runtime and Dalvik](https://source.android.com/docs/core/runtime)
  - [Configure ART](https://source.android.com/docs/core/runtime/configure)
  - [Partitions 与 Treble 的 system/vendor 边界](https://source.android.com/docs/core/architecture/partitions)
  - [Mainline modules](https://source.android.com/docs/core/ota/modular-system)
  - [Android common kernels](https://source.android.com/docs/core/architecture/kernel/android-common)
  - [Android 17 GKI 6.18 release builds](https://source.android.com/docs/core/architecture/kernel/gki-android17-6_18-release-builds)
  - [16 KB page size](https://source.android.com/docs/core/architecture/16kb-page-size/16kb)
  - [Binder IPC](https://source.android.com/docs/core/architecture/hidl/binder-ipc)
- 官方博客
  - [Android 17 lock-free MessageQueue](https://android-developers.googleblog.com/2026/02/under-hood-android-17s-lock-free.html)
  - [AutoFDO for the Android kernel](https://android-developers.googleblog.com/2026/03/BoostingAndroid%20PerformanceIntroducingAutoFDO.html)
- 交叉阅读
  - §1.12《AutoFDO 反馈导向编译优化》
  - §1.13《MessageQueue 机制与 DeliQueue 无锁优化》
  - §2.12《Window Manager Service 与窗口管理》
  - §16.4《Android 17 + Kernel 6.18 系统级性能优化》
