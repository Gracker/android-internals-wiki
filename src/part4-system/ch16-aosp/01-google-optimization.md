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
last_verified: "2026-07-01"
last_verified_against: "AOSP android-17.0.0_r1 (MessageQueue/Looper/Binder/BLAST/WMS) + Android 17 release notes/behavior changes + Mainline docs"
confidence: medium
tags:
  - android
  - performance
  - aosp
pipeline_stage: ready-to-publish
task6_state: reviewed
task9_state: reviewed
task9_result: pass-tech-review
task9_reviewed_date: "2026-07-02"
task9_reviewed_by: openclaw-task9
last_task9_at: "2026-07-02T05:27:44+08:00"
last_task9_audit: "2026-07-01"
last_task9_autofix_at: "2026-07-01"
last_task9_review_log: "logs/deep-review/2026-07-02-05-deep-review.md"
last_task9_review_notes: "2026-07-01 Task9 idle audit AUTO-FIX: AOSP android-17.0.0_r1 已公开，MessageQueue 稳定源码目录复核为 LegacyMessageQueue / CombinedMessageQueue / CombinedDeliMessageQueue；将 refs/heads/master 与 android-16.0.0_r1 源码锚点更新到 android-17.0.0_r1，并修正正文中“tag 尚未公开”的过期说明。回到 Task6 复审。 | 2026-06-26 Task9 review: Deep technical review completed. P0=0, P1=0, P2=5, No auto-fix required. Overall technical score: 4.2/5. Eligible for auto-promotion to finalized. | 2026-07-02 05:27 Task9 formal deep-review: pass-tech-review。复核 android-17.0.0_r1 源码锚点与版本边界；P0 0 / P1 0 / P2 0。Task6 已通过且 queue 无 pending，自动晋升 finalized。"
task2b_state: fixed
task2b_result: fixed-lite
task2b_fixed_at: "2026-06-26T11:40:00+08:00"
last_task2b_at: "2026-06-26T11:40:00+08:00"
task6_result: pass-light-edit
last_task6_audit: "2026-06-30"
last_task6_audit_log: "logs/review/2026-06-30-23-audit.md"
last_task6_at: 2026-07-02T05:06:00+08:00
task6_review_notes: "2026-07-02 05:06 Task6 re-review (revisiting after Task9 idle-audit auto-fix): pass-light-edit。Task9 idle-audit 将 MessageQueue 源码锚点从 master/android-16 刷新到 android-17.0.0_r1，正文落地正确；无新增 L1/L2 问题。无 B 类回炉项。Task9 result=auto-fixed，送 Task9 正式通过。"
last_task2b_lite_at: "2026-06-26T11:40:00+08:00"
sources:
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
    path: "https://android-developers.googleblog.com/2026/02/under-hood-android-17s-lock-free.html"
  - type: official
    path: "https://android-developers.googleblog.com/2026/03/BoostingAndroidPerformanceIntroducingAutoFDO.html"
  - type: aosp
    path: "https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/os/LegacyMessageQueue/MessageQueue.java"
  - type: aosp
    path: "https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/os/CombinedMessageQueue/MessageQueue.java"
  - type: aosp
    path: "https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/os/CombinedDeliMessageQueue/MessageQueue.java"
  - type: aosp
    path: "https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/libs/binder/ProcessState.cpp"
  - type: aosp
    path: "https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/libs/gui/BLASTBufferQueue.cpp"
deepseek_cn_review_state: done
last_deepseek_cn_review_at: 2026-06-26
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
我们这本书前面花了很多篇幅讲 Android 内部的具体机制,VSync、Binder、内存管理、调度器、BufferQueue。再往后退一步,这些机制改动背后有一条主线:Google 持续提高整个平台的性能上限,同时让优化尽快到达真实用户。

理解这条主线有三个直接价值。第一,我们能判断某个问题究竟应该优先在系统层找答案,还是应该回到 App 自己的初始化、线程模型和渲染路径上。第二,Google 官方提供的工具,Baseline Profiles、Macrobenchmark、Android Vitals、Perfetto,都是围绕这套思路设计的,不理解设计目标就容易把工具用成"测个数"的仪表盘。第三,Google 每个版本的性能特性都有清晰延续关系,从 Project Butter 到 Mainline,再到 Android 17 的 lock-free MessageQueue,这条线是连贯的。顺着这条线看版本演进,我们更容易预判下一轮优化会动到哪一层。

## 核心理念:两层性能观
Google 对性能的判断,基本可以拆成两层。

### 系统层（Systemic Performance）

第一层是系统本身的能力上限：内核、运行时、驱动、合成管线、线程调度、系统服务这些底层设施。Google 在这里的目标很简单——让平台默认更快，App 不改业务代码也能吃到收益。

AutoFDO 就是典型例子。它优化的是内核和系统 native binary 的机器码布局与分支预测,不要求 App 配合,但会影响冷启动、Binder 调用、系统服务执行这些底层热点路径。这个方向的细节可以继续看 §1.12《AutoFDO 反馈导向编译优化》和本章的 §16.4《Android 17 + Kernel 6.12 系统级性能优化》。Google 在系统层做的其他长期工作也属于这一类,比如 ART 编译与 GC 的持续演进、Binder 调度与线程池模型的调整、SurfaceFlinger 合成与 Buffer 管线重构。

### 用户感知层（User-Perceived Performance）

第二层是用户直接感知到的性能。Google 一直把启动拖不拖、滑动卡不卡、点击迟不迟、ANR 出没出放在指标的最前面。CPU 利用率和函数耗时只是参考，最终要回到用户动作本身。

这层思路决定了 Google 的工具形态。Android Vitals 追踪 ANR 率、崩溃率、卡顿率这类用户感知指标,而非只看某个线程的平均 CPU 占用。Macrobenchmark 的目标是复现冷启动、滚动、页面切换这些用户动作,然后确认优化前后用户能否感到差别。

两层必须一起看。系统层决定平台天花板，用户感知层决定 App 有没有把这层天花板用出来。系统把渲染、调度、编译流程做得再快，如果 App 还在主线程做同步 I/O、启动时塞满阻塞初始化、滚动里频繁分配对象，用户该觉着慢还是慢。

## 版本旗舰特性:一条清晰的演进线
Google 从 Android 4.1 开始,几乎每个关键版本都有一轮很鲜明的性能主线。把这些主线串起来看,比单独背技术名词更有用。

### Project Butter(Android 4.1,2012)
Project Butter 是 Android 性能口碑的一个分水岭。它解决的是整条 UI 渲染时序的一致性。

它做的三件事今天看仍然是主线。第一,把渲染正式绑到 VSync 节奏上,让 Choreographer 在 VSync 到来时统一调度 Input、Animation、Traversal。第二,引入三缓冲,把 CPU、GPU、SurfaceFlinger 的工作时序拉开,减少双缓冲里常见的"上一帧没放开,下一帧没法开始"这种等待。第三,围绕输入响应做延迟控制,尽量缩短从手指动作到屏幕变化之间的间隔。

这套思路的价值不止于"4.1 比以前顺"这层体验变化——它建立了按帧理解性能的思维模型。后面 RenderThread、FrameMetrics、Frame Timeline、Frame Pacing Library 这整串工具和机制，全是从这个模型里长出来的。相关机制可以回看 §2.3《VSync 机制》和 §2.4《Choreographer 与渲染流水线》。

### Project Svelte(Android 4.4,2013)
如果说 Project Butter 解决的是"顺不顺",Project Svelte 解决的是"资源很差时还能不能跑"。

Android 4.4 的目标是让系统在 512MB RAM 设备上也能工作。这个目标很简单,它把 Google 的另一条性能哲学固定下来。性能工程必须覆盖低端机上的稳定运行。为了做到这一点,Google 去压系统服务内存、减少预装软件的常驻开销、强化低内存回调和行为约束,还给开发者补上了 ProcStats 这类观测工具。

后来的 Android Go Edition 是这条思路的延伸,低资源设备是性能设计必须覆盖的基线场景。

### ART 替代 Dalvik(Android 5.0,2014)
Dalvik 到 ART 的切换,是 Android 运行时层面最重要的一次重写。Dalvik 时代更依赖解释执行和 JIT,热路径第一次执行一定更慢,GC 也更容易把前台线程直接停住。ART 把 AOT 编译引进来,让安装阶段就能把 DEX 转成机器码,运行时性能的基线一下子稳定了很多。

但纯 AOT 很快又暴露出安装慢、产物大、全量编译不划算这些问题,所以从 Android 7.0 开始,ART 逐步走向 JIT、AOT、Profile-Guided 混合编译。系统先解释和采样,再根据真实热路径做更有针对性的编译。这条线最终演变成了 Baseline Profiles、Cloud Profiles、Startup Profiles 这些今天仍然在用的工具链。

### Project Treble(Android 8.0,2017)
Project Treble 表面上讲的是架构解耦,真实情况是它解决了另一个性能大问题,Google 修好的系统优化到底能不能及时送到用户手里。

Treble 之前,Framework 和厂商 HAL 绑得很紧。Google 即使修好了框架层的性能 bug,也得等 SoC 厂商和 OEM 一层层适配,很多设备等不到更新。Treble 通过稳定接口把 Framework 和 HAL 拆开,把"平台层改进"和"厂商适配"之间的耦合降下来,这才给后面的 Mainline、Stable AIDL、模块化更新创造了前提。

### Project Mainline（Android 10，2019）：拆分系统能力与交付路径

Mainline 的核心动作是把"系统能力更新怎么送到设备"做成独立问题。官方 Mainline 文档写得很清楚：Android 10 引入 Mainline 后，终端可以通过 Google Play system update 或合作方 OTA 获取模块更新；模块本身可能是 APEX，也可能是 APK。ART 模块 `com.android.art` 从 Android 12 开始以 APEX 形式交付。

理解 Mainline 时，一个常见的混淆是把"性能特性本身"和"特性通过什么路径交付"当成一回事。至少有三条独立的路径：

- Mainline / APEX / APK 模块更新。这是 ART、DNS Resolver、Permission Controller 这类系统模块的交付方式。像 ART 运行时的能力演进,才可能走这条路。
- GKI kernel 分支与设备 OTA。AutoFDO 属于内核与系统 native binary 的构建优化,落在 `android15-6.6`、`android16-6.12` 这类内核分支和对应构建产物里,最终通过厂商 kernel OTA 或完整 OTA 到达设备,不属于 ART Mainline。
- Google Play 安装期编译。Baseline Profiles 由 App 自己随 APK/AAB 打包,Cloud Profiles 由 Google Play 聚合用户行为后参与安装或后台编译。这条流程作用在 App 的安装与编译阶段,归属 Play 编译路径。

沿着这三条路径回头看 Android 17 的运行时变化，很多表述会自然变得准确。比如 generational GC，它是 Android 17 release notes 里明确写出的运行时能力变化，但不等于"Mainline 推送的特性"——是否回推到旧设备，取决于对应 ART 模块版本、设备集成和 Google Play system update 的实际覆盖。Cloud Profiles 同理：它服务于 Play 安装期编译，不属于 ART Mainline 本身。

## ART 的持续优化方向
ART 这些年的优化可以沿着三条线来看：编译策略、GC、构建期工具链。

### 编译策略:从 AOT 走向 Profile-Guided
纯 AOT 的问题很明确。安装成本高、产物大,许多冷门方法提前编译收益很低。Android 7.0 之后,ART 把解释执行、JIT 和后台 AOT 编译揉到一起,先靠运行时收集热路径,再决定哪些方法值得编译。

这条路继续往前走,就有了 Google Play 参与的 Cloud Profiles 和开发者可控的 Baseline Profiles。官方 Baseline Profiles 文档给出的表述很清楚,Baseline Profiles 可以让关键代码路径从第一次启动开始就避免解释执行和 JIT,很多应用测得的执行速度提升大约在 30% 左右。官方同时强调,发布 Baseline Profile 之后,优化生效会明显快于"只依赖 Cloud Profiles"的情况。它对应前面三条交付方式里的第三条:Play 安装期编译流程,而非 Mainline。

### GC：减少前台停顿

Dalvik 时代 GC 的问题很集中：STW 时间长、碎片化重、前台线程容易被直接停住。ART 后续通过 Concurrent Copying、并发标记和对象搬移，一直在往"少打断前台"这个方向迭代。

Android 17 release notes 对 generational GC 的描述也保持了这个口径,ART 的 Concurrent Mark-Compact collector 现在支持 generational GC,会更频繁地做低成本的 young generation 回收。官方强调"frequent, low-cost",没有给出放之四海而皆准的暂停时间数字。所以这节只保留机制层判断,不再硬写某个固定毫秒数。更细的 GC 演进可以继续看 §4.8《ART 分代垃圾回收与 GC 暂停优化》。

### 工具链：R8、D8 与 Startup Profiles

除了运行时本身，Google 还在持续优化代码到达运行时之前的形态。R8 负责 shrink、optimize、inline、merge，目标是让 DEX 更小、更整齐。DEX 体积小了，冷启动时 fault 进来的页面就少，dex2oat 和加载阶段的负担也会跟着变轻。

Startup Profiles 负责编译期的进一步收束。和 Baseline Profiles 配合时，一个管安装期编译关键代码路径，一个管 DEX 布局阶段把启动热点排到更容易被顺序读取的位置。两者放一起，才是今天 Android 启动优化工具链的完整图景。

## Framework 层的性能优化实践
Google 在 Framework 层的很多工作没有单独冠上 Project 名字,但卡顿、启动、切换速度这些体验,往往会受这些改动影响。

### View 系统:持续减主线程负担
View 系统历史太久,Google 这些年一直在做两件事,减少不必要的 measure/layout/invalidate 传播,以及把更重的绘制工作继续往 RenderThread 挪。

从 Android 5.0 引入 RenderThread 之后，主线程更多在做 DisplayList 记录，OpenGL 或 Vulkan 指令提交不再堵在 UI 线程上。这个变化对性能分析的意义很大：主线程慢只说明一部分问题，RenderThread 和合成侧能不能赶上 VSync，才真正决定用户会不会看见掉帧。

### Handler / MessageQueue：legacy 队列和 Android 17 新队列的区别
MessageQueue 的性能问题,在于"很多生产者在并发入队"和"Looper 必须按消息到期时间有序取出"这两件事被塞进了同一套队列结构里。

在 legacy locked queue 里,这个问题通常表现为单锁竞争。Looper 在 `next()` 里遍历并取出到期消息,生产者在 `enqueueMessage()` 里按 `when` 插入单链表,两边都会碰到同一份队列状态。分析旧实现时,可以说它围绕一把锁序列化访问;源码引用应指向 `MessageQueue` 自身,不能只引用 `Handler.java`。`Handler` 只是暴露 `sendMessage()`、`post()` 这些 API 的封装层,队列实现应该看 `Looper.java` 和 `MessageQueue` 的具体实现文件。

到了 Android 17，这个前提就不能再直接套用了。Android 17 release notes 和 behavior changes 都明确写到，targetSdk 37 及以上应用会收到新的 lock-free `android.os.MessageQueue`，官方 DeliQueue 博客也确认了 lock-free 设计方向与性能收益。源码侧，android-17.0.0_r1 的 `core/java/android/os/` 目录里可以稳定锚定 `LegacyMessageQueue/`、`CombinedMessageQueue/`、`CombinedDeliMessageQueue/` 这几条实现路径，其中 `CombinedMessageQueue` 和 `CombinedDeliMessageQueue` 上的 `@EnabledAfter(targetSdkVersion = android.os.Build.VERSION_CODES.BAKLAVA)` 对应 targetSdk 37+ 的兼容门槛。旧稿里从 master 观察到的 `LockedMessageQueue/`、`ConcurrentMessageQueue/`、`SemiConcurrentMessageQueue/` 不能作为 Android 17 稳定源码锚点；对比 android-16.0.0_r1，Android 17 新增了 `CombinedDeliMessageQueue`，讨论 DeliQueue 时应以 android-17.0.0_r1 为主线。

Google 在 DeliQueue 技术博客里给出的主线也和这个拆分一致,生产者尽量走无锁入队,Looper 再在自己的视角里整理待执行消息。对我们做性能分析来说,这个变化的意义是,不能再看到 `Handler.post()` 就默认脑补成"老式单锁链表"。必须先分清设备系统版本和 App 的 targetSdk,再决定该看 legacy locked queue 还是新的 concurrent queue。更细的实现与兼容边界,可以继续看 §1.13《MessageQueue 机制与 DeliQueue 无锁优化》。

### Binder：线程池与优先级继承的时间线
Binder 线程池和优先级继承的版本演进，社区里一直有简化说法，比如"Android 8 动态扩展线程池，Android 10 才有优先级继承"。实际情况要更细致一些。

先看线程池。AOSP `frameworks/native/libs/binder/ProcessState.cpp`（android-17.0.0_r1 稳定锚点）很早就把默认 worker 上限定义成 `DEFAULT_MAX_BINDER_THREADS = 15`，并通过 `BINDER_SET_MAX_THREADS` 把这个上限交给 driver。也就是说,Binder 线程池从早期就是"driver 按需唤醒或拉起 worker,userspace 负责设置上限"的模型。工程里常说的"16 线程"，大多是把发起调用的线程也口语化算进去了；driver 默认 worker 上限仍是 15。

再看优先级继承。官方 binder IPC 文档写得很明确,binder driver 一直支持 nice priority inheritance。Android 8 借 Treble 引入 `/dev/hwbinder` 域,同时把 real-time priority inheritance 加进 binder driver;到了 Android 10,Stable AIDL 又让满足稳定性要求的 HAL 可以回到 `/dev/binder`。准确的演进线是:早期已有 nice priority inheritance,Android 8 加入 RT inheritance 与 hwbinder 域,Android 10 通过 Stable AIDL 重新整理 binder domain 边界。

把这条时间线理清楚之后，再看 Perfetto 里的 Binder track，就不会把线程池耗尽、调度延迟和优先级反转搅在一起了。Binder 的具体机制还可以回看 §1.4《Binder IPC 机制与性能影响》。

### 窗口管理:BLASTBufferQueue 优化 buffer 与 transaction 的同帧提交
BLASTBufferQueue 常被简化成"App 直接把 buffer 发给 SurfaceFlinger"。源码里的路径更具体（android-17.0.0_r1 可稳定验证）：`BLASTBufferQueue` 仍然会创建内部的 `BufferQueueCore`、producer 和 consumer，BufferQueue 基础设施还在。它把 buffer acquire 与 `SurfaceControl.Transaction` 的提交时机绑到同一个 frame number 上。`BLASTBufferQueue.cpp` 里能直接看到这条主线：`syncNextTransaction()` → `mergeWithNextTransaction()` → `applyPendingTransactions()` 的完整调用链。`SurfaceControl.java` 里也有 `onMergeWithNextTransaction()` 这条 Java 侧钩子。

跨进程同步场景还要把 WMS 放进来。窗口尺寸、裁剪、层级变化通常由 SystemServer 侧的 WMS 管理,App 侧 buffer 与窗口状态相关的 transaction 需要经由 `SurfaceControl.Transaction` / `WindowContainerTransaction` 参与 WMS 的统一调度。WMS 侧的 `BLASTSyncEngine` 会收集参与同一次 sync 的窗口 transaction,合并后再提交给 SurfaceFlinger。这样,内容 buffer、窗口几何变化和层级 transaction 更容易落在同一帧,减少 buffer latch 与 transaction apply 之间的错位和额外等待。窗口事务这条线如果要继续往下追,可以接着看 §2.12《Window Manager Service 与窗口管理》。

## Google 官方的 Performance 工具与文档体系
Google 的性能思路最终都会落到工具和文档上。我们真要把这套思路用在工程里,入口基本就这几类。

### 文档入口
官方文档入口里最常用的还是三个。

第一是 `developer.android.com/topic/performance`,这是总入口,启动、渲染、内存、网络、电池这些主题都从这里发散。第二是 Baseline Profiles 与 Macrobenchmark 相关文档,它们对应的是 Google 当前最主推的 App 侧性能工作流。第三是 Android 各版本的 release notes 与 behavior changes,这两类页面负责回答"这一版系统新增了什么"和"targetSdk 提上去之后什么行为会变"。Android 17 的 lock-free MessageQueue 就是典型例子,release notes 讲能力变化,behavior changes 讲适用边界。

### 度量、分析、优化三类工具
Google 的性能工具大致可以分成三类。

度量工具回答"有没有问题"。Jetpack Benchmark 负责稳定地测代码段，Macrobenchmark 负责复现冷启动、滚动、页面切换这些用户动作，Android Vitals 负责反馈真实用户到底有没有在现场感知到问题。

分析工具回答"问题在哪"。Android Studio Profiler 适合开发阶段的单进程定位，Perfetto 适合看跨线程、跨进程、跨系统服务的完整时序，simpleperf 更适合 native 代码热点和调用栈分析。Perfetto 的方法论在第 13 章有完整展开。

优化工具回答"怎么修"。Baseline Profiles 和 Startup Profiles 负责把关键代码路径尽早变成机器码，R8 负责把 DEX 组织得更小更紧凑，App Startup Library 负责把初始化依赖理清楚，避免所有工作都挤进 `Application.onCreate()`。

### 反复回到五件事

Google 在 I/O、Codelab 和官方文档里反复强调的原则并不花哨，常见的就五件。

第一，不要在主线程做阻塞操作。第二，初始化按用户实际的使用顺序来排，不要在启动时全量摊开。第三，优先优化关键路径，别把精力平均铺到每一行代码上。第四，一定要在资源更紧的设备上测——旗舰机上的"没感觉"往往说明不了什么。第五，优化前后都要量化，没有基线就谈不上收益。

这些原则看起来像常识，但它们恰好解释了为什么 Google 会同时推动系统层优化和开发者工具链优化：系统层提高平台默认能力，开发者工具要求 App 把这些能力用到位。

## Android Go Edition:面向低资源设备的性能策略
Android Go Edition 是 Project Svelte 思路的延续版。它把低内存、低存储、低算力设备当成真实目标平台,再反过来重做系统和应用默认配置。

这条线的意义在于,它不断提醒我们,好的性能优化应该天然向下兼容。减少常驻内存、延迟初始化、降低后台工作、缩短关键路径,这些策略不会只对低端机有效。相反,低端机场景往往最容易把问题放大,也最容易逼我们看清楚主要性能瓶颈。

## Google 内部的性能测试基础设施
公开信息里能看到的 Google 内部性能基础设施主要分三类。

第一类是 AOSP 与平台测试仓库里的基准测试,用来守住启动时间、渲染耗时、系统服务行为这些基础指标。第二类是持续回归监控,每次平台代码变更之后都要确认关键性能指标没有被悄悄拉坏。第三类是覆盖不同 SoC、不同内存规模、不同分辨率配置的设备池,避免性能结论只在单一测试机上成立。

这部分公开细节不算多,这里只保留工程上能确定的结论,不去硬写内部平台名称和实现细节。

## 常见问题与误区
### "系统已经越来越快了,App 端不用太管"
系统层优化会抬高默认上限,但它不会替我们删掉主线程阻塞 I/O,也不会自动把启动阶段那些不该同步做的初始化搬走。Google 的系统优化更像乘数,前提还是 App 自己的结构别太差。

### "Baseline Profiles 能包治启动慢"
Baseline Profiles 解决的是"关键代码路径尽早编译成机器码",但启动优化不等于只做编译。如果启动慢的根因是主线程 I/O、同步 Binder、数据库初始化、第三方 SDK 常驻初始化,那它只能缓解一部分,不可能替代架构和线程模型层面的整理。

### "升级 Android 版本,性能自然会整体变好"
大方向通常是对的,但具体场景仍然要实测。新系统会带来更好的运行时、更好的调度和更好的系统工具,也可能同时带来新的行为限制、更多安全检查或 targetSdk 适配成本。Google 每一版都在优化平台,也每一版都在改平台规则,这两件事是一起发生的。

## 参考资料
- AOSP / 官方源码路径
  - `https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/view/Choreographer.java`(VSync 驱动的帧调度入口)
  - `https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/os/Looper.java`(Looper 驱动 MessageQueue)
  - `https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/os/LegacyMessageQueue/MessageQueue.java`(legacy MessageQueue 实现)
  - `https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/os/CombinedMessageQueue/MessageQueue.java`(Android 17 MessageQueue 兼容门槛与组合实现)
  - `https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/os/CombinedDeliMessageQueue/MessageQueue.java`(Android 17 DeliQueue 实现)
  - `https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/libs/binder/ProcessState.cpp`(`DEFAULT_MAX_BINDER_THREADS` / `BINDER_SET_MAX_THREADS`)
  - `https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/libs/gui/BLASTBufferQueue.cpp`(完整调用链：`syncNextTransaction()` → `mergeWithNextTransaction()` → `applyPendingTransactions()`)
  - `https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/libs/gui/include/gui/BLASTBufferQueue.h`(BLAST 的同步接口定义)
  - `https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/view/SurfaceControl.java`(`mergeWithNextTransaction` Java 侧钩子)
  - `https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/wm/BLASTSyncEngine.java`(WMS 侧 BLAST sync 收集与提交)
  - `https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/window/WindowContainerTransaction.java`(窗口事务跨进程传递对象)
- 官方文档
  - `https://developer.android.com/topic/performance`
  - `https://developer.android.com/topic/performance/baselineprofiles/overview`
  - `https://developer.android.com/about/versions/17/release-notes`
  - `https://developer.android.com/about/versions/17/behavior-changes-17`
  - `https://source.android.com/docs/core/ota/modular-system`
  - `https://source.android.com/docs/core/architecture/treble`
  - `https://source.android.com/docs/core/architecture/hidl/binder-ipc`
- 官方博客
  - `https://android-developers.googleblog.com/2026/02/under-hood-android-17s-lock-free.html`
  - `https://android-developers.googleblog.com/2026/03/BoostingAndroidPerformanceIntroducingAutoFDO.html`
- 交叉阅读
  - §1.12《AutoFDO 反馈导向编译优化》
  - §1.13《MessageQueue 机制与 DeliQueue 无锁优化》
  - §2.12《Window Manager Service 与窗口管理》
  - §16.4《Android 17 + Kernel 6.12 系统级性能优化》
