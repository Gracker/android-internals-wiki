---

title: Android 版本演进中的架构变化
chapter: '1.6'
section: '1.6'
polish_count: 1
polish_date: '2026-04-06'
polish_by: task2b-polish
applicable_versions: Android 4.4 (API 19) - Android 17 (API 37)
last_verified: '2026-06-07'
last_verified_against: 'AOSP android-16.0.0_r4, Android 16/17 官方文档'
confidence: medium
sources:
- type: official
  path: https://source.android.com/docs/core/architecture
- type: official
  path: https://source.android.com/docs/core/runtime
- type: official
  path: https://developer.android.com/topic/performance/baselineprofiles
- type: blog
  path: https://android-developers.googleblog.com (ART Mainline Updates)
- type: blog
  path: obsidian/Cubox/谈Android架构创新性-2022-04-02.md
- type: blog
  path: obsidian/Personal-Knowlodge/source/2026-03-07_wechat_深度_Android_整体设计及背后意义.md
- type: blog
  path: obsidian/Personal-Knowlodge/source/2026-03-06_wechat_后AOSP时代还能贡献代码吗.md
- type: official
  path: https://developer.android.com/about/versions
task2b_fixed_at: '2026-05-08T23:46:33'
tags:
- treble
- mainline
- apex
- gki
- art
- dalvik
- privacy
- background-restrictions
- 16k-page
- compilation
- profile-guided
- background-execution
related_chapters:
- '1.1'
- '1.4'
- '1.7'
- '2.9'
- '4.4'
- '4.6'
- '5.6'
- '8.7'
task9_result: 'auto-fixed'
task9_reviewed_date: '2026-06-07'
task9_reviewed_by: 'openclaw-task9'
last_task9_at: '2026-06-07T02:20:00+08:00'
status: 'finalized'
reviewed_date: '2026-05-09'
reviewed_by: openclaw-task6
last_task6_at: '2026-05-09T02:08:33+08:00'
last_task6_audit: '2026-05-23'
last_task6_review_log: logs/review/2026-05-09-02-review.md
task6_state: revisiting
task6_result: pass-light-edit
task9_state: reviewed
task2b_state: 'fixed'
task2b_result: fixed-lite
pipeline_stage: 'task6_pending'
last_task2b_lite_at: '2026-06-07'
review_notes: 'task9 P90 rework: 寄存器描述修正(翻倍→精确), Dalvik/Zygote已验证正确；2026-04-14 task6
  轻量精修：文风、间距、图示占位; 2026-04-19 task6 re-review (revisiting): L1 fix x2 (not-X-Y pattern)；2026-05-01
  task9 deep-review: needs-rework。P0/P1 技术问题已写入 queue。 | 2026-05-09 Task6 02:08：revisiting
  写作复审；清理 frontmatter 重复键，修复 L1/L2 文风词与元叙述 8 处，无新增 L3/L4 回炉项，转 Task9 复审。 | 2026-05-09
  Task9 02:30：needs-rework。P1 1：Perfetto 表格提示把 ART Mainline 写成 Android 11+，需改为 Android
  12+ 或拆分 8-11/12+；P2 1：GSI 验证术语 CTS-V 应改为 VTS / CTS-on-GSI。'
last_task9_review_log: 'logs/deep-review/2026-06-07-02-deep-review.md'
deepseek_cn_review_state: done
last_deepseek_cn_review_at: 2026-05-31
last_task9_audit: '2026-06-07'
last_task9_autofix_at: '2026-06-07'
---


# Android 版本演进中的架构变化

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 关键版本的架构里程碑：4.4 ART / 5.0 Lollipop 64-bit / 8.0 Treble / 10 Mainline / 12 Material You
- 🔹 Android 16-17 (API 36-37) 最新架构变化与性能相关特性
- 🔹 Project Treble → VINTF → GSI → GKI 对系统碎片化的改善
- 🔹 从 Dalvik 到 ART 的演进：JIT → AOT → Profile-Guided Compilation
- 🔹 Privacy 变更对性能监控工具的影响（如 Android 11+ 包可见性限制）

### 扩展（可选深入）

- 🔸 各版本对后台限制的持续收紧（8.0 背景执行限制 → 12 精确闹钟限制 → 15 进一步限制）
- 🔸 16K Page Size 支持对性能和兼容性的影响

### OpenClaw 加工指引

> **锚点**是最低覆盖要求，加工时必须逐条落实并标注验证结果。
> **扩展**视素材丰富程度选择性深入。
> 如果从 Obsidian 素材或 AOSP 源码中发现大纲未列出但与本节强相关的知识点，
> 可**就地插入**最相关的锚点之后，并用 `[自动发现]` 标注，方便后续 review。
> 锚点内容需 L1/L2 验证，扩展内容至少 L2 验证，自动发现内容至少标注来源。
<!-- outline-end -->

## 为什么要了解 Android 版本演进

打开 Perfetto 抓一份 Trace，那些进程、线程、Binder 调用、渲染管线的形态并非一成不变。Android 从 2008 年的 1.0 到今天的 Android 17，每一次大版本的架构变更都在重塑这些行为。不了解这些变化，分析问题时容易犯经验主义的错误：用 Android 8 的经验去解释 Android 15 的 Trace，得出错误结论。

Android 的版本演进围绕一条清晰的主线：**模块化**。从 Project Treble 到 Project Mainline，从 GKI 到 APEX，Google 一直在把 Android 从一个"铁板一块"的操作系统拆解为可独立升级的模块。理解这条主线，不仅能帮你看懂系统架构的设计意图，还能帮你在实际工作中判断一个现象属于系统层还是厂商层。这会直接影响 OEM 和 App 开发者的日常判断。

性能分析最需要关注的是那些会改变底层行为的架构变化，而不是每个版本的新功能清单。

## 关键版本的架构里程碑

Android 的架构演进不是线性的——有些版本在底层做了大规模重构（如 5.0 引入 ART、8.0 引入 Treble），而有些版本则在应用层和 API 层做了大量工作。这里聚焦那些改变系统底层行为的版本。

### Android 4.4 KitKat（API 19）：ART 初登场

Android 4.4（2013 年）是一个特殊的过渡版本。它首次将 ART（Android Runtime）作为实验性选项引入，与 Dalvik 并存。此时 ART 还不是默认运行时，但它的出现意味着 Google 已经在为 Dalvik 的替代方案做准备了。

从性能角度看，ART 的 AOT（Ahead-Of-Time）编译策略与 Dalvik 的 JIT（Just-In-Time）形成了鲜明对比：ART 在安装时就把 DEX 字节码编译成本地机器码，运行时不再需要即时编译的开销。这在当时的低端设备（512MB 内存）上带来了可感知的流畅度提升。

### Android 5.0 Lollipop（API 21）：64 位与 ART 正式上位

Android 5.0（2014 年）是 Android 历史上架构变动最大的版本之一，两件事同时发生：

**ART 完全取代 Dalvik。** 从 Android 5.0 开始，Dalvik 被完全移除，ART 成为唯一的运行时。[已验证: Android 5.0 Release Notes, Wikipedia] 所有应用在安装时都会被 dex2oat 编译为本地代码。安装时间因此变长了，但运行时性能更稳定。垃圾回收器也做了重大改进，GC 暂停时间从 Dalvik 时代的上百毫秒降低到了几毫秒。

**64 位支持。** Android 5.0 正式支持 64 位 ARMv8 架构。这不只是为了寻址更大的内存空间。ARMv8 的指令集设计比 ARMv7 更高效，通用整数寄存器从 ARMv7 的 16 个（r0-r15）增加到 31 个（x0-x30），SIMD/NEON 寄存器也从 16 个 Q 寄存器增加到 32 个 V 寄存器，编译器因此能生成质量更高的本地代码。

Zygote 的双进程形态也从这里固定下来：64 位设备上，init 脚本里有两个 service——`zygote`（主）和 `zygote_secondary`（辅）。`init.zygote64.rc` 启动 `/system/bin/app_process64 --socket-name=zygote`，`init.zygote64_32.rc` 补一个 `/system/bin/app_process32 --socket-name=zygote_secondary`。引用 init/service 语义时，写 `zygote` / `zygote_secondary`；在 `ps`、Trace 或 cmdline 中看到的 `zygote64`，是 64 位主 zygote 的进程形态。[已验证: AOSP init.zygote64.rc, init.zygote64_32.rc, ARM Architecture Reference Manual]

### Android 8.0 Oreo（API 26）：Project Treble——模块化的起点

Android 8.0（2017 年）引入了 **Project Treble**，这是 Android 架构演进中最重要的一次重构。[已验证: 官方文档 source.android.com/docs/core/architecture]

在 Treble 之前，每次升级 Android 版本，芯片厂商（高通、MTK、三星 LSI）都需要先更新他们底层驱动代码以适配新的 Framework API，然后设备厂商再基于芯片厂商的适配做整机集成。整个升级链条动辄半年以上，Android 设备系统更新慢的根因就在这里。

Treble 的方案是在 Android Framework 和厂商实现（HAL）之间插入一层稳定的接口（HIDL（HAL Interface Definition Language）/AIDL（Android Interface Definition Language）），将系统分为 **System 分区**（Google 控制）和 **Vendor 分区**（芯片/设备厂商控制）。这样，Framework 可以独立于 Vendor 进行升级。

[图：Project Treble 前后的架构对比]

```
┌──────────────┐    ┌──────────────┐
│   Framework   │    │   Framework   │
│              │    │              │
│  (直接调用     │ →  │  HIDL/AIDL   │ ← 稳定接口层
│   HAL .so)   │    │  接口层       │
│              │    │              │
│  HAL (.so)   │    │  HAL (.so)   │
└──────────────┘    └──────────────┘
  Treble 之前          Treble 之后
```

从系统架构的角度看，Treble 的核心思想是**接口依赖倒置**——Google 定义接口，下层去实现，而不是下层定义接口，上层来适配。这让 Google 牢牢控制了 Android 的演进方向。

对性能分析的影响：Treble 之后，Binder IPC 中出现了两类通信，传统的 `binder`（Framework 层）和新增的 `hwbinder`（HAL 层）。Perfetto 中会出现这两种 Binder 调用，它们的行为特征有所不同。hwbinder 调用通常涉及硬件操作（如相机、传感器），延迟更高。

### Android 10（API 29）：Project Mainline 与 APEX

Android 10（2019 年）在 Treble 的基础上更进一步，引入了 **Project Mainline**（也叫 Mainline modules）。[已验证: 官方文档 source.android.com/docs/core/ota/modular-system]

Treble 让 Framework 可以独立于 Vendor 升级，Mainline 又把 Framework 内部的一部分系统组件拆成可独立发布的模块。Android 10 首发的 Mainline 模块包括 DNS Resolver（`com.android.resolv`）、Conscrypt（`com.android.conscrypt`）、Media 组件（`com.android.media` / `com.android.media.swcodec`）、PermissionController 等。这些模块可以通过 Google Play 更新，不必等待整机 OTA。

为了做到这一点，Google 设计了 **APEX**（Android Pony EXpress）——一种类似于 APK、但可以携带本地库和系统服务的打包格式。APEX 模块能在启动早期挂载，所以适合承载运行时和系统组件。Android 10 发布时已经有一批 Mainline 模块进入 APEX / APK 体系，不过 ART 还不在这批首发名单里。

注意一个容易混淆的时间点：Android 10/11 已经有 Mainline 架构，但官方 Mainline 模块表把 `com.android.art` 的引入版本标为 Android 12。也就是说，ART 作为可独立更新的运行时模块要到 Android 12 才成立。分清了这两段时间线，分析编译器、Profile-Guided Compilation 或 dex2oat 行为时就不会把 Android 10/11 的设备误判成"ART 已可通过 Play Store 单独更新"。

Google 在 2024 年 Android Summit 上分享过 ART Mainline 的实际数据：ART 14 通过编译器优化和运行时改进，为全球设备累计节省了约 95 PB 存储空间，平均每个应用瘦身约 9.3%。这个数字来自 Play Store 上 dex2oat 编译产物去重与 Profile-Guided 编译的叠加效果——更多设备命中 speed-profile 而非 speed（全量编译）时，OAT 文件体积显著缩小。[来源: Google Android Developer Blog, ART Mainline Updates 2024]

### Android 12（API 31）：GKI 与 Material You

Android 12（2021 年）在模块化道路上又迈了一步：**GKI（Generic Kernel Image）**。[已验证: 官方文档 source.android.com/docs/core/architecture/kernel/gki]

GKI 将模块化的边界推进到了 Linux 内核。在 GKI 之前，每个设备都有一个定制的内核（SoC 厂商 + 设备厂商的各种补丁），导致内核碎片化严重。GKI 的思路与 Treble 一脉相承：定义一个稳定的 **KMI（Kernel Module Interface）**，将 SoC 和设备特定的代码从核心内核中移出到可加载的厂商模块中。

搭载 Android 12 且使用 Linux 5.10+ 内核的设备被要求使用 GKI 内核。同一个 GKI 内核镜像因此可以运行在不同 SoC 的设备上，这在以前是不可想象的。

对性能分析的影响：GKI 意味着内核行为更加标准化。在做跨设备的性能对比时，内核层面的差异会越来越小，更多差异集中在 HAL 和 Vendor 层。

### Android 16-17 Baklava（API 36-37）：最新架构变化

Android 16（2025 年 6 月发布，代号 Baklava）延续了模块化和性能优化的趋势。[已验证: 官方文档 developer.android.com/about/versions/16]

几个对性能分析有直接影响的架构变化：

**Generic Bootloader (GBL)。** Android 16 引入了标准化的可更新 Bootloader，将模块化从内核进一步延伸到了引导程序。Bootloader 的标准化意味着启动链的前半段（Boot ROM → Bootloader → Kernel）也可以通过标准化接口进行独立更新。

**16KB 页面大小的兼容模式。** Android 15 开始支持 16KB 内存页面（详见本节扩展内容），Android 16 为此增加了兼容模式——允许为 4KB 页面构建的 App 在 16KB 设备上运行。同时，TLS 相关的缓冲区被隔离到独立的内存页面中，在 16KB 页面大小的设备上可以显著节省内存。

**Cloud Compilation（云端编译产物分发）。** Android 16 开始公开 CloudCompilation 路径——Play 分发侧可能通过 SDM（Secure Dex Metadata）和云端预编译减少本机 dex2oat 开销。官方公开资料中具体集成细节和设备覆盖范围仍有限（同书 §1.9 对该点也标注为待验证）。已确认的能力方向是：设备从 Play Store 获取预编译 `.odex` / `.vdex` 产物后可跳过本地编译，缓解 OTA 后首次开机"正在优化应用"的体验问题。设备侧启用条件、Play 与 ART 模块的协同路径，需以安装 Trace（`cmd package art dump` 编译状态）和 Play Console 数据验证，不应视为所有 Android 16 设备的确定行为。[来源: Android 16 behavior changes, ART dump; 具体 AOSP 集成文档待补]

**更严格的后台限制。** Android 16 将前台服务启动的后台 Job 也纳入了运行时配额管理，进一步收紧了后台执行的自由度。

**性能监控 API 增强。** `ProfilingManager`（Android 15 / API 35 引入，Android 16 增强）支持应用主动请求和系统自动触发两种性能分析模式。应用侧通过 `ProfilingManager.requestProfiling(int profilingType, Bundle parameters, String tag, CancellationSignal cancellationSignal, Executor executor, Consumer<ProfilingResult> listener)` 请求系统转储 Trace（参数包括分析类型、可选配置 Bundle、取消信号和结果回调）；系统侧可通过 `addProfilingTriggers(List<ProfilingTrigger>)` 注册自动触发条件，`registerForAllProfilingResults(Executor, Consumer)` 接收系统级 Profiling 结果。Android 16 进一步强化了其在 App Startup 阶段的自动化能力，系统可以在 ANR 等关键事件发生时自动捕获背景环形缓冲区中的 Trace 数据。`ApplicationStartInfo` 新增的组件启动信息（可通过 `getStartComponent()` 精确区分冷启动由 Activity / Service / Receiver / Provider 中哪种组件触发）也为启动性能归因提供了更精细的维度。[来源: AOSP android.os.ProfilingManager API 35/36, android-16.0.0_r1]

**修订的 SDK 发布节奏。** Android 16 引入了新的 SDK 发布结构——2025 年内发布两个 API 版本。第一个包含新 API 和行为变更，第二个只增加 API 不改变行为。这对 App 开发者意味着更平滑的适配周期。

**Android 17 / API 37 延续的变化。** Android 17 在 API 36 基础上补充了多项与性能分析直接相关的能力。[来源: Android 17 官方 Features 与 behavior-changes 页面]

**MessageQueue lock-free 实现。** 对 targetSdkVersion 37+ 的 App，Android 17 会启用新的 lock-free `android.os.MessageQueue`；低 target App 仍受 compat change 控制，可用 `USE_NEW_MESSAGEQUEUE` 开关测试。新实现让主线程 Looper 的消息分发路径不再依赖传统互斥锁。观察 `Looper.loop()` wall duration 时，Android 17 且已启用该变更的进程中，锁竞争导致的尾部延迟应有所减少。[来源: Android 17 behavior changes for target 37]

**ProfilingManager 自动触发条件扩展。** API 37 新增 `ProfilingTrigger` 类型：`TRIGGER_TYPE_OOM`（内存不足）、`TRIGGER_TYPE_ANOMALY`（系统异常）、`TRIGGER_TYPE_KILL_EXCESSIVE_CPU_USAGE`（CPU 过量使用被杀）、`TRIGGER_TYPE_COLD_START`（冷启动）和 `TRIGGER_TYPE_APP_COMPAT`（兼容性问题）。这些 trigger 让系统在关键性能事件发生时自动捕获 Trace，无需 App 侧主动请求。[来源: android.os.ProfilingTrigger API 37 参考]

**JobDebugInfo 与后台任务诊断。** Android 17 新增 `JobDebugInfo` API，提供后台 Job 未运行原因、累计 pending 时长和运行时长等聚合信息。排查后台任务性能问题时，可以把 `getPendingJobReasonStats()` / `getPendingJobReasonsHistory()` 与 `JobParameters.getStopReason()`、standby bucket 一起看，区分“尚未满足约束”和“运行后被系统停止”。[来源: Android 17 Features]

**16KB 页面：强制关闭兼容模式。** Android 17 允许通过系统属性关闭 16KB backcompat，让不支持 16KB 页面对齐的 binary 直接 abort 而非降级运行，进一步推动开发者在 16KB 设备上正确对齐。[来源: Android 16KB page sizes 文档]

## Project Treble → VINTF → GSI → GKI：模块化的完整链条

这些里程碑落到系统边界上，形成的是一条模块化链条：Treble、VINTF、GSI、GKI 分别处理不同边界。

这条链条的目标只有一个：**让 Android 的每一层都可以独立更新。**

[图：Android 模块化演进全景]

```
┌─────────────────────────────────────┐
│           App Layer                  │  ← 一直可以独立更新（Play Store）
├─────────────────────────────────────┤
│       Framework Layer                │  ← Treble (8.0) 后可独立更新
├─────────────────────────────────────┤
│     Framework 内部组件               │  ← Mainline/APEX (10) 后可独立更新
├─────────────────────────────────────┤
│       HAL / Vendor Layer            │  ← Treble (8.0) 定义了稳定接口
├─────────────────────────────────────┤
│       Linux Kernel                   │  ← GKI (12) 后可独立更新核心内核
├─────────────────────────────────────┤
│       Bootloader                     │  ← GBL (16) 标准化引导程序
├─────────────────────────────────────┤
│       Boot ROM                       │  ← 芯片固化，不可更新
└─────────────────────────────────────┘
```

### VINTF：Treble 的"契约"

VINTF（Vendor Interface）是 Treble 架构中定义 HAL 接口版本和兼容性的框架。设备厂商需要在 VINTF manifest 中声明自己实现了哪些 HAL 接口（版本号、类型），而 Framework 则在 compatibility matrix 中声明它需要哪些 HAL 接口。OTA 更新时，系统会校验这两份"契约"是否匹配——如果 Framework 的要求超出了 Vendor 的实现范围，更新会被拒绝。

这种设计保证了一个老设备的 Vendor 分区可以和新版本的 Framework 正常配合工作。

### VNDK 与 linker namespace：把 ABI 边界固定下来

VINTF 管的是 HAL 接口的版本匹配，但光有接口还不够——vendor 进程在运行时还会加载 native 共享库。如果 vendor 模块不小心依赖了 Framework 内部某个 `.so`，Framework 一升级就可能打破 ABI 兼容。为了解决这个层面的隔离，Treble 引入了 VNDK（Vendor Native Development Kit）和 linker namespace。VNDK 提供一组允许 vendor 进程在运行时依赖的稳定库，Framework 内部库则继续留在 system 一侧。这样，vendor 模块不会因为 framework 私有库的符号变化被一起打断。

动态链接器会为 Framework 进程、vendor 进程、Same-Process HAL 准备不同的 namespace。比如 SP-HAL 只能看到 LL-NDK 和 VNDK-SP 指定的库，看不到 Framework 内部实现细节。Treble 建立了两层隔离：一层是 HAL 接口版本由 VINTF 约束，另一层是 native ABI 可见范围由 VNDK + namespace 约束。

为支持不同 vendor image 的组合，Android 还引入过 VNDK snapshot / VNDK APEX，把某个版本的稳定库集合固定下来，供 vendor 构建和 GSI 运行时复用。Android 15 开始官方逐步淡出 VNDK 机制，但在 Treble 建立期，它承担的是"冻结 vendor 可见 ABI"这件事。

Treble 时代引入的 VNDK 解决的是"vendor 能看见哪些库"的问题。到了 Android 15+，这个思路被进一步推进——与其维护一份"允许看的库清单"，不如让每个 vendor 模块把自己需要的库打包带走。**VNDK-less 与 Vendor APEX 自包含**就是这个方向：Android 15+ 进一步弃用 VNDK 机制，转向 Vendor APEX 自包含模式。每个 Vendor APEX 模块将自身依赖的共享库打包在一起，不再依赖系统分区的 VNDK 库集合。这是模块化链条的又一步推进——vendor 模块不仅在接口层面独立于 Framework（Treble 的贡献），在 native 依赖层面也实现了自包含。对性能分析的影响：当 Perfetto 中看到 vendor 进程加载的 `.so` 路径从 `/system/lib64/vndk-*` 迁移到 `/vendor/apex/*/lib64/` 时，说明设备已进入 VNDK-less 阶段，ABI 隔离从"冻结共享库"变成了"各自打包"。

### GSI：Treble 的"试金石"

GSI（Generic System Image）是 Treble 架构的一个副产品——如果 Treble 的接口定义足够完善，那么一个纯 AOSP 编译出来的 System Image 理论上应该能在任何 Treble 兼容的设备上运行。GSI 就是这个"通用系统镜像"，主要用于：

1. **VTS（Vendor Test Suite）/ CTS-on-GSI 验证**：设备必须通过 GSI 测试才能获得 Google 认证
2. **开发调试**：开发者可以在自己的设备上刷入 GSI 来测试纯 AOSP 的行为
3. **Project Treble 合规性检查**：确保厂商的 Vendor 实现遵循了 Treble 接口

GSI 能成为 Treble 合规性的试金石，有两个前提：HAL 版本匹配，以及 vendor 分区对 system 镜像的 native 依赖已经被压缩到 VNDK / LL-NDK / namespace 允许的范围内。设备能启动纯 AOSP GSI，再通过 CTS-on-GSI / VTS，说明这台设备同时满足了接口兼容和 ABI 隔离两项约束。

从系统工程师的视角看，Android 架构设计离不开四个对象：接口定义（IDL）、接口约束（VINTF / CTS）、ABI 可见范围（VNDK / linker namespace），以及配套的测试套件。Treble 和 GKI 都沿着这条思路演进。

## 从 Dalvik 到 ART：编译策略的演进

Android 的运行时经历了从 Dalvik 到 ART 的迁移，但这个故事比"换个虚拟机"复杂得多——编译策略本身也在不断演进，每一次调整都直接影响着 App 的启动速度和运行时性能。

### Dalvik 时代：JIT 编译（Android 2.2 - 4.4）

早期的 Android 设备内存非常有限（200MB RAM 很常见）。Dalvik 运行时采用 **JIT（Just-In-Time）编译**策略：应用运行时，Dalvik 会跟踪频繁执行的代码路径（"trace"），并将这些热点代码动态编译为本地机器码。未编译的代码则以解释方式执行。

JIT 的优势是内存占用小——只编译运行中用到的热点代码。劣势也明显：每次运行都需要重新编译（编译结果不持久化），运行时开销大，耗电。

Android 2.2 引入的 trace-based JIT 让 Dalvik 的性能有了质的飞跃，但随着 App 越来越大、功能越来越多，JIT 的局限性也日益明显。

### ART 初期：全量 AOT 编译（Android 5.0 - 6.0）

ART 在 Android 5.0 取代 Dalvik 后，采取了截然不同的策略——**AOT（Ahead-Of-Time）全量编译**。安装 App 时，dex2oat 工具会将整个 DEX 文件编译为 OAT（Optimized Android applicaTion）格式的本地代码。[已验证: 官方文档 source.android.com/docs/core/runtime]

全量 AOT 的好处是运行时零编译开销——所有代码都是本地机器码，直接执行。GC 暂停时间也从 Dalvik 时代的"World Pause"（上百毫秒）大幅缩短。App 运行更流畅，这是 5.0 被誉为"最流畅的 Android 版本"的技术基础。

但全量 AOT 有三个严重的问题：

1. **安装时间暴增**：一个大型 App 的 dex2oat 编译可能需要几分钟
2. **存储空间占用大**：OAT 文件体积是原始 DEX 的数倍
3. **系统更新后全部重编译**：OTA 更新后，所有 App 都需要重新 dex2oat，导致更新后首次启动极慢

这说明性能优化中没有银弹——AOT 解决了运行时性能问题，却引入了安装时间和空间的问题。

### Profile-Guided 混合编译（Android 7.0 至今）

Android 7.0 引入了**混合编译策略**，这是 ART 编译策略的最终形态，至今仍是 Android 的核心编译方案。[已验证: 官方文档 source.android.com/docs/core/runtime]

核心思路是结合 JIT 和 AOT 的优势：

1. **首次启动**：App 以解释模式或 JIT 模式运行，不做全量 AOT。安装速度飞快。
2. **运行时画像（Profile）**：ART 在运行过程中记录哪些方法被频繁调用（"hot methods"），生成本地 Profile 文件。
3. **后台 AOT 编译**：当设备空闲且充电时，编译守护进程根据 Profile 数据，只对"hot methods"进行 AOT 编译。冷代码不需要浪费编译资源。
4. **后续启动**：已经 AOT 编译的 hot methods 直接执行本地代码，未编译的部分仍然走 JIT 或解释。

这样就兼顾了安装速度（不全量编译）、运行性能（hot methods 有本地代码）和存储空间（只编译必要的代码）。

后续的改进包括：

- **Cloud Profiles（Android 9+）**：Google Play 收集大量用户的 Profile 数据，在 App 安装时就提供聚合后的 Profile，让首次启动就有 AOT 编译的热点代码
- **Baseline Profiles（Android 7+，库开发者可提供）**：开发者可以在 APK 中内置 Profile 文件，定义自己 App 的关键代码路径。Jetpack 库（如 Compose）已经内置了 Baseline Profiles。这直接影响 Compose 的首次启动性能——没有 Baseline Profile 的 Compose App 在首次启动时会有明显的卡顿。

从 Perfetto 的角度看，编译策略直接影响你在 Trace 中看到的模式：如果一个 App 首次安装后启动很慢但后续变快，那就是 Profile-Guided 编译在起作用。我们可以在 Trace 中观察到首次启动时更多的 JIT 编译活动（对应 CPU 使用率高峰），以及后续启动时这些活动消失。

## Privacy 变更对性能监控工具的影响

模块化解决了系统更新的碎片化问题，但 Android 的另一条演进主线——隐私保护——对性能分析工具的影响同样直接。自 Android 10 起，隐私限制逐版本收紧，负责维护性能监控 SDK 或内部工具的工程师如果不了解这些限制，工具可能在新版本上直接失效。

### 包可见性限制（Android 11+）

Android 11（API 30）引入了**包可见性（Package Visibility）限制**。[已验证: 官方文档 developer.android.com/training/package-visibility]

在此之前，任何 App 都可以通过 `PackageManager.getInstalledApplications()` 获取设备上所有已安装 App 的列表。在 Android 11+ 上，这个方法默认只返回本 App 和少数系统 App。要查询其他 App，必须在 Manifest 中通过 `<queries>` 元素显式声明，或者申请 `QUERY_ALL_PACKAGES` 权限（Google Play 对此权限有严格审查）。

对性能监控的影响：

- **竞品对比工具**无法再自动发现竞品 App
- **系统级性能分析工具**（如检测后台 App 占用的工具）受限
- **SDK** 如果需要检测宿主 App 的依赖库版本，需要在 AAR 的 Manifest 中声明 queries

### 其他关键隐私限制

除了包可见性，Android 还在多个版本中逐步收紧了其他隐私相关限制：

- **Android 10**：后台位置权限需要单独授权（`ACCESS_BACKGROUND_LOCATION`）
- **Android 11**：一次性权限授权、权限自动撤销（长期未使用的 App 的权限被自动回收）
- **Android 12**：精确闹钟需要 `SCHEDULE_EXACT_ALARM` 权限（进一步限制后台定时任务）
- **Android 13**：通知权限（`POST_NOTIFICATIONS`）需要运行时授权；闹钟、日历等核心场景可以通过 `USE_EXACT_ALARM` 获得精确闹钟能力
- **Android 14**：前台服务必须声明类型并申请对应权限（如 `FOREGROUND_SERVICE_CAMERA`）；多数新安装且 target Android 13+ 的 App 不再默认获得 `SCHEDULE_EXACT_ALARM`
- **Android 15**：`dataSync` 和 `mediaProcessing` 类型的前台服务有 6 小时/24 小时的配额限制；处于停止态或特定后台生命周期的 App 网络请求受到约束（WorkManager / 前台服务场景不受影响）

[适用版本: Android 10 (API 29) 起，隐私限制逐版本收紧]

对性能分析工具开发者的启示：设计工具时就要考虑最小权限原则。能用 `<queries>` 精确声明的就不要申请 `QUERY_ALL_PACKAGES`；能用 WorkManager 的就不要用前台服务；能用 ProfilingManager API 的就不要自己做 proc 文件读取。

## 扩展：后台限制的持续收紧

Android 对后台执行的管制经历了从"放任"到"严管"的渐进过程。这个趋势会直接改变 App 开发者和性能优化工程师的策略，因为很多"以前能用的招"现在不能用了。

### 限制演进时间线

**Android 8.0（2017）——后台执行限制元年。** 这是 Android 第一次系统性地限制后台行为。App 进入缓存状态后，后台服务会在几分钟内被系统杀死。为了给必要的后台任务留一条路，Android 8.0 引入了 `startForegroundService()`——但服务必须在 5 秒内调用 `startForeground()` 显示通知，否则触发 ANR。隐式广播也受到了限制。

**Android 12（2021）——前台服务启动限制。** App 在后台时，一般情况下不能再启动前台服务，否则抛出 `ForegroundServiceStartNotAllowedException`。同时引入了 "Phantom Process Killer"——限制 App 的子进程总数（全局 32 个）和后台 CPU 使用。精确闹钟需要声明 `SCHEDULE_EXACT_ALARM` 权限。

**Android 13（2022）——精确闹钟权限分流。** Android 13 增加 `USE_EXACT_ALARM` 常规权限，给闹钟、日历等符合政策的核心场景使用；普通 App 继续走 Android 12 引入的 `SCHEDULE_EXACT_ALARM` 特殊权限口径。

**Android 14（2023）——前台服务类型强制声明，精确闹钟默认收紧。** 所有前台服务必须在 Manifest 中声明具体类型（mediaPlayback、location、connectedDevice 等），并申请对应权限。`BOOT_COMPLETED` 广播对某些前台服务类型的启动也做了限制。同时，`SCHEDULE_EXACT_ALARM` 不再预授予多数新安装且 target Android 13+ 的 App，默认处于拒绝状态。

**Android 15（2024）——配额制。** `dataSync` 和 `mediaProcessing` 前台服务类型引入了 6 小时/24 小时的配额。后台 App 的网络请求约束有具体触发条件：App 处于停止态（force-stopped）、不在前台服务或 WorkManager 调度上下文中时，网络访问可能失败（`UnknownHostException`）。使用前台服务、WorkManager 或用户可见交互触发的网络请求不在约束范围内。[来源: Android 15 behavior changes, developer.android.com]

**Android 16（2025）——配额扩展。** 从前台服务启动的后台 Job 也必须遵守运行时配额。JobScheduler 的配额根据 App 的 standby bucket 和启动时的状态动态调整。

[已验证: 官方文档 developer.android.com/about/versions]

对性能优化的影响：

- **App 不能再依赖后台长时间运行**——必须用 WorkManager 等调度框架
- **定时任务的精度受限**——精确闹钟不再是默认能力
- **后台网络请求在特定条件下可能失败**——App 停止态且非前台服务/WorkManager 上下文时，需要处理 `UnknownHostException`
- **前台服务的通知要求越来越严格**——用户更容易感知并关闭

## 扩展：16K Page Size 对性能和兼容性的影响

模块化的边界已经从 Framework 推进到了内核和 Bootloader，而内存管理层面也在经历类似的基础设施升级，对性能和 App 兼容性都有直接影响。

### 为什么需要更大的页面

传统上，Linux（包括 Android）使用 4KB 的内存页面大小。这是早期硬件条件下的合理选择。但现代 ARM CPU 普遍支持更大的页面大小（16KB、64KB），而 Android 设备的物理内存也已经从早期的 512MB 增长到 8GB、12GB 甚至 16GB。

更大的页面带来的好处是 **TLB（Translation Lookaside Buffer）命中率更高**。TLB 是 CPU 中缓存虚拟地址到物理地址映射的高速缓存，更大的页面意味着同样的 TLB 容量可以覆盖更多的内存，减少 TLB miss 导致的页面遍历开销。

### 实测性能提升

Google 官方的测试数据显示，在 16KB 页面大小的设备上：[已验证: 官方博客 android-developers.googleblog.com]

- **App 启动时间**平均缩短 3.16%，部分 App 提升达 30%
- **功耗**在 App 启动场景降低 4.56%
- **相机冷启动**加快 6.60%
- **系统开机时间**缩短约 0.8 秒（8%）

整体性能提升约 5-10%，代价是内存使用略有增加（因为内存对齐导致的内部碎片）。

### 对 App 兼容性的影响

**纯 Kotlin/Java 应用**几乎不需要改动——ART 虚拟机屏蔽了页面大小的差异。

**使用 Native 代码（C/C++）的应用**需要重新编译，确保 ELF 文件使用 16KB 对齐。具体来说：
- NDK 构建需要配置 `max-page-size=16384`
- 直接操作内存的 Native 代码需要检查是否有假设 4KB 页面大小的硬编码
- 某些使用 `mmap` 的代码需要检查对齐参数

从 2025 年 11 月起，Google Play 要求所有新提交的 App（targeting Android 15+）必须在 64 位设备上支持 16KB 页面大小。不支持的应用可能会被拒绝上架。

Android 16 增加了兼容模式，让部分为 4KB 页面构建的 App 能在 16KB 设备上运行，但这只是过渡方案——开发者最终需要正确支持 16KB。

## 在 Perfetto 中的版本差异观察

了解版本演进后，我们可以在 Perfetto 中观察到一些具体的版本差异：

| 特征 | Android 8 之前 | Android 8-10 | Android 11+ |
|------|----------------|-------------|-------------|
| Binder 类型 | 只有 binder | binder + hwbinder | binder + hwbinder |
| Zygote（init service） | zygote（32-bit-only 设备）或 zygote + zygote_secondary（64-bit 设备） | zygote + zygote_secondary | zygote + zygote_secondary |
| 编译产物 | 完整 OAT（全量 AOT） | VDEX + ODEX（Profile-AOT） | VDEX + ODEX（Profile-AOT） |
| 后台进程 | 可长期存活 | 受限但仍可后台服务 | 配额制 + 网络限制 |

> **表格阅读提示**：Android 8-10 和 11+ 的编译产物格式看起来相同（VDEX + ODEX），但 Android 12+ 由于 ART 已成为 Mainline 模块，编译器行为和优化策略可能已经通过 Play Store 更新发生变化。因此分析 12+ 设备的 Trace 时，不能直接把 8-11 的 ART 行为当成默认前提。Android 11 虽然已有 Mainline 架构，但 `com.android.art` 的 Release introduced 为 Android 12，11 的 ART 行为仍与 10 相近。表格里的 Zygote 一行按 init service 名称统一写成 `zygote` / `zygote_secondary`；在 `ps` 或 Trace 里常看到的 `zygote64`，说的是 64 位主 zygote 的进程形态。

[图：Android 8、Android 11+、Android 16 在 Perfetto 中的典型 Trace 对比，重点标出 binder/hwbinder、zygote 形态与编译产物差异]

## 常见问题与误区

### 误区："升级 Android 版本会让 App 变慢"

实际情况取决于具体场景。ART 的编译策略优化、GC 改进通常会让 App 更快。但后台限制的收紧可能影响依赖后台运行的 App。如果 App 做了适当的适配（使用 WorkManager、合理声明前台服务类型），新版本上通常会更快。

### 误区："Treble 只影响系统开发者，App 开发者不需要了解"

Treble 改变了 HAL 层的通信方式，间接影响了硬件相关操作（相机、传感器、音频）的延迟特征。分析涉及硬件的延迟问题（如相机启动慢）时，了解 Treble 架构有助于判断问题出在 Framework 层还是 HAL 层。

### 误区："Profile-Guided 编译意味着 App 安装后第一次都很慢"

Cloud Profiles 和 Baseline Profiles 大幅缓解了这个问题。大多数通过 Google Play 分发的 App 在安装时就能获得 Profile 数据，首次启动时热点代码已经有 AOT 编译。完全"裸启动"（无任何 Profile）的场景越来越少见。

## 参考资料

- 官方文档：
  - [Android Architecture](https://source.android.com/docs/core/architecture)
  - [Project Treble](https://source.android.com/docs/core/architecture/treble)
  - [Project Mainline](https://source.android.com/docs/core/ota/modular-system)
  - [GKI](https://source.android.com/docs/core/architecture/kernel/gki)
  - [ART and Dalvik](https://source.android.com/docs/core/runtime)
  - [Package Visibility](https://developer.android.com/training/package-visibility)
  - [Background Execution Limits](https://developer.android.com/about/versions/oreo/background)
  - [16KB Page Size](https://developer.android.com/guide/practices/page-sizes)
  - [Android 16 Features](https://developer.android.com/about/versions/16)
  - [Android 17 Features](https://developer.android.com/about/versions/17/features)
  - [Android 17 MessageQueue](https://developer.android.com/about/versions/17/changes/messagequeue)
  - [Android 14 Exact Alarm Changes](https://developer.android.com/about/versions/14/changes/schedule-exact-alarms)
- AOSP 源码路径：
  - `art/dex2oat/dex2oat.cc` — dex2oat 编译器入口
  - `system/apex/` — APEX 模块定义
  - `hardware/interfaces/` — HIDL 接口定义
- Obsidian 素材：
  - [谈Android架构创新性](obsidian://open?vault=Obsidian&file=Cubox%2F%E8%B0%88Android%E6%9E%B6%E6%9E%84%E5%88%9B%E6%96%B0%E6%80%A7-2022-04-02.md)
  - [深度 | Android 整体设计及背后意义](obsidian://open?vault=Obsidian&file=Personal-Knowlodge%2Fsource%2F2026-03-07_wechat_%E6%B7%B1%E5%BA%A6_Android_%E6%95%B4%E4%BD%93%E8%AE%BE%E8%AE%A1%E5%8F%8A%E8%83%8C%E5%90%8E%E6%84%8F%E4%B9%89.md)
  - [Android 运行时更新 | 为数十亿设备提高内存](obsidian://open?vault=Obsidian&file=Personal-Knowlodge%2Fsource%2F2026-03-07_wechat_Android_%E8%BF%90%E8%A1%8C%E6%97%B6%E6%9B%B4%E6%96%B0_%E4%B8%BA%E6%95%B0%E5%8D%81%E4%BA%BF%E8%AE%BE%E5%A4%87%E6%8F%90%E9%AB%98%E5%86%85%E5%AD%98.md)
  - [后AOSP时代还能贡献代码吗](obsidian://open?vault=Obsidian&file=Personal-Knowlodge%2Fsource%2F2026-03-06_wechat_%E5%90%8EAOSP%E6%97%B6%E4%BB%A3%E8%BF%98%E8%83%BD%E8%B4%A1%E7%8C%AE%E4%BB%A3%E7%A0%81%E5%90%97.md)
