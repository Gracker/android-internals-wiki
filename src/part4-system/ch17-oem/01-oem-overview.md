---
title: "OEM 性能优化的通用思路"
chapter: "17.1"
section: "17.1"
drafted_date: "2026-04-04"
drafted_by: "openclaw-task2a"
applicable_versions: "Android 8.0 (API 26) - Android 16 (API 36)"
last_verified: "2026-04-04"
last_verified_against: "AOSP android-16.0.0_r1"
confidence: medium
sources:
  - type: blog
    path: "obsidian/Personal-Knowlodge/source/2026-03-08_wechat_Android系统优化的那10年.md"
  - type: blog
    path: "obsidian/Personal-Knowlodge/source/the-performance-design-of-os.md"
  - type: official
    path: "source.android.com/docs/core/perf/cached-apps-freezer"
  - type: official
    path: "developer.android.com/topic/performance/background-optimization"
tags: ['oem', 'performance', 'freezer', 'preloading', 'background-management']
related_chapters: ["5.1", "5.5", "5.6", "4.4", "8.3", "17.2"]
task9_result: "pass-tech-review"
task9_reviewed_date: "2026-05-06"
task2b_state: fixed
status: "finalized"
pipeline_stage: "ready-to-publish"
task6_state: reviewed
task6_result: pass-light-edit
task9_state: "reviewed"
reviewed_by: openclaw-task6
reviewed_date: "2026-05-06"
task6_reviewed_date: "2026-05-06"
last_task6_at: "2026-05-06T01:05:00+08:00"
last_task6_audit: "2026-05-24"
review_notes: "2026-04-26 task6 re-review: pass-light-edit。小修1处（禁用句式 x1 替换）。无B类大问题。评分: 结构4/5·措辞4/5·一致性4/5·验证3/5·元数据4/5。 | 2026-05-06 Task6 01:05：Task2B 修复后写作复审，清理 L1/L2 表达与格式；无新增 L3/L4 回炉项，送 Task9 复审。 | 2026-05-06 Task9 01:28：复审通过。复核 CachedAppOptimizer freezer、USAP Pool 默认开关与 App Zygote 边界；无 P0/P1；P2 数据/Trace 观测补证写入 suggestions；Task6 已通过且 queue 无 pending，自动晋升 finalized。"
task9_reviewed_by: "openclaw-task9"
last_task9_at: "2026-05-06T01:28:30+08:00"
last_task9_audit: "2026-05-24"
last_task9_audit_log: "logs/deep-review/2026-05-24-21-audit.md"
deepseek_cn_review_state: done
last_deepseek_cn_review_at: 2026-05-28
---

# OEM 性能优化的通用思路

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 OEM 性能优化的通用方向：启动优化、流畅性、内存管理、功耗、温控
- 🔹 OEM 优化的技术手段分层：Kernel（调度/内存）→ Native（Binder/SF）→ Framework（AMS/WMS）→ App（预加载/冻结）
- 🔹 应用冻结技术：Frozen Process、SIGSTOP、cgroup freezer
- 🔹 预加载与预测启动：智能预测用户下一步操作
- 🔹 后台管理策略差异：保活 vs 杀后台的平衡

### 扩展（可选深入）

- 🔸 OEM 优化带来的兼容性问题（如后台杀进程过于激进）
- 🔸 各厂商性能优化品牌（HyperBoost / RAMDISK / LPDDR Training 等）

### OpenClaw 加工指引

> **锚点**是最低覆盖要求，加工时必须逐条落实并标注验证结果。
> **扩展**视素材丰富程度选择性深入。
> 如果从 Obsidian 素材或 AOSP 源码中发现大纲未列出但与本节强相关的知识点，
> 可**就地插入**最相关的锚点之后，并用 `[自动发现]` 标注，方便后续 review。
> 锚点内容需 L1/L2 验证，扩展内容至少 L2 验证，自动发现内容至少标注来源。
<!-- outline-end -->

## 为什么要了解 OEM 的优化思路

如果你做 Android 性能优化的时间够长，一定遇到过这种情况：你的 App 在 Pixel 上跑得好好的，到了某家厂商的机器上就莫名其妙卡顿、通知收不到、甚至后台直接被杀。打开 Perfetto 一看，CPU 调度策略变了、后台进程凭空消失、主线程的 Binder 调用比 AOSP 多出一倍。

这不是你的 App 有问题——是厂商在 AOSP 基础上做了一整套自己的性能优化，而这些优化的策略和力度，每家都不一样。

了解 OEM 的优化思路，目的是在分析 Trace 时能区分「这是我的代码问题」还是「这是厂商策略导致的现象」，而非逐个适配厂商的 ROM。这种判断能力在定位线上问题时尤其关键——当你看到 Perfetto 里某段调度行为异常，脑子里要有这根弦：可能是厂商在干预。

从更宏观的角度看，OEM 的优化方向代表了一类系统性思维：在资源受限的移动设备上，如何通过全栈手段让用户体验变好。这种思维对我们做 App 层优化同样有启发——很多在 App 层难以解决的问题，从系统角度往往有更优雅的解法。

## OEM 优化的五大方向

厂商做系统优化，核心围绕用户体验的五个维度展开。我们可以把这五个维度想象成一个金字塔：底部是稳定性和功耗，这是基本盘；中间是流畅性和启动速度，这是差异化竞争的核心；顶部是温控，它像一个天花板，限制了性能的极限。

**启动速度**是用户对手机的第一印象。冷启动从按下图标到第一帧渲染，中间涉及 Zygote fork、ClassLoader 加载、Application 初始化、Activity 创建到渲染——整段启动路径上的每个环节都是优化点。厂商会在系统层面做预加载（让 Zygote 提前初始化常用类）、dex2oat 编译策略调整，甚至直接在 init 阶段预创建进程。我们在 §8.3 中详细讲过 App 层的启动优化思路，厂商的做法是把同样的思路往系统层推。

**流畅性**是用户日常感知最强的指标。厂商会从渲染管线的每个环节入手：调整 VSync offset 让 App 和 SurfaceFlinger 的配合更紧凑、优化 GPU 调度策略减少渲染延迟、在 SurfaceFlinger 中做图层合成的特殊优化。我们前面在 §2.3～§2.6 中拆解了渲染管线的每个环节，厂商的优化就是在这些环节上做加减法。

**内存管理**在 Android 上永远是稀缺资源的争夺战。厂商的策略核心是「保证前台、压缩后台」：调整 LMK 的阈值参数（我们在 §4.4 中讲过 AOSP 的默认实现）、在内存紧张时更激进地回收后台进程、对系统进程做内存上限控制。国内厂商因为要应对更复杂的 App 生态（特别是各类保活方案），通常会比 AOSP 默认策略更激进。

**功耗**直接决定用户要不要充电。厂商的优化覆盖了从 CPU 调度到网络管理的完整路径：基于 EAS 的调度器调优（§5.2）、DVFS 策略的精细化（§5.4）、后台网络请求的批量合并、GPS 等传感器的使用限制，以及 Doze 模式的增强。功耗优化的目标是「不该花的 CPU 周期一个都不花」，而厂商在系统层有完整的控制力来实现这个目标。

**温控**是性能的天花板。当 SoC 温度达到阈值，Thermal 机制会强制降频（我们在 §5.5 中分析过），这时候前面所有的性能优化都会打折扣。厂商的温控策略差异很大：有的激进，温度稍高就降频换取更低功耗；有的保守，宁可温度高一点也要维持性能。这种策略差异直接反映在游戏场景的长帧率稳定性上。


## 技术手段的全栈分层

厂商的优化不是在一个层面完成的，而是从 Kernel 到 App 层贯穿整个技术栈。理解这个分层结构，有助于我们在 Trace 中快速判断某个优化行为的来源。

**Kernel 层**是厂商最深的优化战场。这里的手段包括 CPU 调度器调优（修改 CFS/EEVDF 的参数、定制 EAS 的能效模型）、内存管理的参数调整（watermark、min_free_kbytes 等）、I/O 调度策略（为不同场景配置不同的 I/O 优先级和调度器）、以及 cgroup 的精细化配置。在高通平台上，厂商可以直接修改 Snapdragon 的 governor 参数；在联发科平台上，则有 MTK 定制的调度策略。这些改动在 Perfetto 中表现为 CPU 频率变化、调度迁移行为、以及内存回收事件。

**Native 层的优化集中在 SurfaceFlinger 和 Binder 这两个关键服务上。** SurfaceFlinger 是渲染合成的核心，厂商会针对自家的显示硬件做合成策略调优——比如调整 HWC 的使用策略、优化 Layer 的合成路径、甚至为特定 App（如游戏）做合成 bypass。Binder 层面，厂商可能会优化 Binder 线程池大小、调整 Binder 事务的优先级继承策略，以减少主线程在 Binder 调用上的等待时间。在 Perfetto 中，这些优化表现为 SurfaceFlinger 的合成耗时变化和 Binder 调用的延迟分布。

**Framework 层是厂商最容易做差异化创新的地方。** ActivityManagerService（AMS）控制着进程的生命周期和优先级——厂商会调整 OOM Adj 的计算逻辑，让前台 App 获得更高的优先级保护。WindowManagerService（WMS）控制着窗口和 Surface 的管理——厂商可能会对动画系统做加速或对多窗口场景做特殊优化。PackageManagerService（PMS）影响启动速度——厂商可以定制 dex2oat 的编译策略，让常用 App 提前完成 AOT 编译。

**App 层的优化更多是厂商与头部 App 的协同。** 厂商会提供专用 API 给合作的 App，让它们能根据运行场景动态调整 CPU 频率（CPU Boost）、使用更大的堆内存配额、或者在启动时获得更高的调度优先级。这就是为什么你在 Perfetto 中经常看到某些国民级 App（微信、支付宝）的调度行为跟普通 App 不一样——它们享受了厂商的白名单待遇。


## 应用冻结技术

后台进程的管理是 OEM 优化中最核心也最容易引发争议的领域。冻结技术是「不杀进程但让它不消耗资源」的折中方案，它的演进过程本身就是 Android 系统设计哲学变迁的一个缩影。

### 从杀进程到冻结

早期的 Android（4.x ~ 6.x 时代），手机内存普遍只有 2GB-3GB，厂商最常用的后台管理手段就是简单粗暴地杀进程。定时清理、内存阈值触发清理、甚至灭屏就清理。这带来了两个问题：一是 App 频繁被杀导致冷启动变多，用户体验下降；二是杀进程本身有开销，重新创建进程比唤醒一个冻结的进程慢得多。

iOS 的做法给了业界启发。在 iOS 中，App 进入后台约 3 分钟后会被挂起（类似 SIGSTOP），进程状态被完整保留在内存中，但不再获得 CPU 时间。当用户切回这个 App 时，恢复几乎是瞬时的。这种方式兼顾了后台资源控制（不耗 CPU）和前台切换速度（不需要冷启动）。

Android 厂商开始跟进类似的思路，但实现方式经历了几次迭代。

### SIGSTOP 方案及其局限

最直接的实现方式是给后台进程发送 SIGSTOP 信号。SIGSTOP 是 Unix 信号机制的一部分，被 SIGSTOP 的进程会被内核挂起，不再参与调度，直到收到 SIGCONT 信号恢复执行。

这个方案的风险在于，SIGSTOP 对应用是可观测的。虽然 App 无法捕获或忽略 SIGSTOP，但进程被挂起后，它持有的所有资源（锁、网络连接、Binder 引用）都会保持在挂起时的状态。这可能导致一些微妙的问题：比如一个 App 在持有 wake lock 的时候被 SIGSTOP，系统就无法进入休眠；或者在 Binder 调用中途被 SIGSTOP，调用方会一直阻塞。


### cgroup freezer：AOSP 的标准方案

Android 11 QPR3 引入了基于 cgroup v2 freezer 的 cached apps freezer 机制，这是 AOSP 官方认可的后台冻结方案。

cgroup freezer 的工作方式是将目标进程迁移到冻结的 cgroup 中。与 SIGSTOP 的关键区别在于，cgroup freezer 是从 cgroup 层面统一控制一组进程的状态——它不是逐个进程发送信号，而是通过向 cgroup 的 `cgroup.freeze` 文件写入 `1` 来冻结整个组。这样一来，一个 App 的所有进程（主进程、子进程、Content Provider 进程等）可以被原子性地冻结或恢复。

在 AOSP 中，这个机制由 ActivityManager 的 `setProcessFrozen` 和 `enableFreezer` 两个隐藏 API 控制。设备可以通过 `activity_manager_native_boot_use_freezer` 配置标志来启用，也可以在开发者选项中通过「Suspend execution for cached apps」开关控制。

我们可以在 Perfetto 中观察到冻结行为——当后台 App 被冻结后，它的所有线程会从 CPU 调度队列中消失，在 CPU Track 上表现为进程的线程完全没有任何 CPU 活动。验证冻结是否生效的方法是通过 adb：

```bash
# 查看当前被冻结的进程数量
adb shell dumpsys activity | grep "Apps frozen:"

# 检查 cgroup freeze 文件是否存在
adb shell ls /sys/fs/cgroup/uid_*/cgroup.freeze
```

[已验证: 官方文档, source.android.com/docs/core/perf/cached-apps-freezer]

### 厂商在冻结策略上的差异

各家厂商在 AOSP freezer 基础上的策略差异主要体现在两个维度：**冻结时机**和**冻结对象**。

冻结时机方面，AOSP 的默认策略是当 App 进入 cached 状态一段时间后触发冻结。而厂商的定制策略可能更激进——有的在 App 退到后台几秒内就冻结，有的根据内存压力动态调整冻结速度，有的甚至对白名单以外的 App 立即冻结。

冻结对象方面，AOSP 只冻结 cached 进程。但厂商可能会扩大范围——把某些 service 进程、甚至广播接收者进程也纳入冻结范围。这就是为什么同样的 App 在不同厂商设备上表现完全不同：在你的设备上后台音乐播放正常，在另一台设备上可能几秒就被冻结了。


## 预加载与预测启动

### 系统级预加载：从 Zygote 到定制化

Android 的应用进程都是从 Zygote fork 出来的。Zygote 在系统启动时预加载了大量 Java 类和资源（定义在 `frameworks/base/preloaded-classes` 中），这样每个新进程 fork 后不需要重新加载这些类，直接就能用。这个机制是 Android 启动速度的基石，我们在 §8.3 中也讨论过它对启动优化的影响。

厂商在此基础上做了进一步定制。常见做法包括：

第一，**扩展预加载列表**。把常用 App 依赖的核心类加入预加载列表，让更多类在 Zygote 阶段就加载完毕。代价是 Zygote 进程本身的内存占用更大，以及系统启动时间变长（因为要加载更多的类）。这是一道经典的工程权衡题：用系统启动时间换 App 启动时间。

第二，**预创建进程**。在系统启动阶段直接预创建若干应用进程（已经 fork 了 Zygote，但还没加载 App 代码），当用户点击图标启动 App 时，直接从预创建的进程中选一个，省掉 fork 的开销。这种方法在 Perfetto 中表现为启动 Trace 里没有 Zygote fork 阶段，`StartActivity` 直接进入 `bindApplication`。

AOSP 本身提供了标准化的预热缓存池机制：USAP（Unspecialized App Process）Pool。Zygote 在空闲时预先 fork 一批「空白进程」放入池中（`ZygoteServer.fillUsapPool()`），当 AMS 需要启动新进程时，优先从池中取用而非重新 fork。关键配置属性是 `usap_pool_enabled`（默认值因版本而异，AOSP 16 中默认关闭）和 `usap_pool_size_max`（池容量上限）。厂商可以基于这套机制做自己的预热策略——比如根据用户习惯提前填充池、增大池容量、或者在内存紧张时清空池释放资源。

在 Perfetto 中验证 USAP Pool 是否生效的方法：观察启动 Trace 中的 `Zygote` 线程 slice，如果出现 `usapReceive` 而非 `forkAndSpecialize`，说明进程来自预热池。需要额外注意的是，USAP Pool 目前不支持 App Zygote（Child Zygote）和 `android:useAppZygote` 场景，这类多进程架构的 App 仍走标准 fork 路径。


第三，**预编译优化**。调整 dex2oat 的编译策略，让常用 App 在系统空闲时提前完成 AOT 编译，或者使用基于用户使用习惯的 Profile-Guided Optimization（PGO）策略，只编译用户经常用到的代码路径。三星的 App Booster 就是这个思路——它手动对已安装的 App 执行 profile-guided 编译，让代码针对实际使用模式优化。


### AI 预测启动

更进阶的做法是基于用户行为预测来预加载 App。原理很简单：如果一个用户每天早上 8 点打开微信，那系统可以在 7:58 就开始预热微信的进程，等用户实际点击时，启动过程几乎瞬时完成。

ColorOS 的 Trinity Engine 就是这种思路的典型代表——它通过 AI 学习用户的使用习惯，预测用户下一步可能打开的 App，并提前做资源分配和进程预热。据 OPPO 公开的数据，Trinity Engine 可以将 App 启动速度提升 28%，加载时间缩短 21%。这种预测能力在 Perfetto 中很难直接观察到（因为预热过程发生在后台），但可以通过对比有无预测时 App 的冷启动 Trace 来间接验证。

当然，预测启动也有风险。如果预测不准，预加载的 App 白白消耗了内存和 CPU 资源。所以厂商通常采用保守策略——只对高频使用的 App 做预测，预测置信度低于阈值的不触发。数据显示，一个用户常用的 App 一般不超过 10 个，这为预测模型提供了天然的精简范围。


## 后台管理策略：保活与杀后台的博弈

### 中国 Android 生态的特殊性

理解厂商的后台管理策略，必须先理解中国 Android 生态的一个根本特殊性：**没有 Google Play Services**。

因为没有统一的推送服务（FCM），App 为了确保能及时收到消息通知，不得不自己维持后台进程的活跃状态。于是各种保活方案层出不穷：双进程守护、JobScheduler 定时唤醒、AccountSync 同步触发、1 像素 Activity 保活、甚至静默播放音频文件来防止进程被杀。多个 App 之间还会相互唤醒——你打开了 App A，它通过 ContentProvider 或广播把同公司的 App B 也拉起来。这就是臭名昭著的「全家桶」现象。

这种生态导致了一个恶性循环：App 越来越激进的保活 → 系统越来越卡、越来越耗电 → 厂商越来越激进的杀后台 → App 为了存活更加激进地保活。这个循环的结果是，国内 Android 手机的后台管理策略远比 AOSP 默认策略更激进。

### 厂商的策略光谱

面对这个生态，厂商的后台管理策略可以排列成一个光谱：

光谱的一端是**宽松策略**——尽量保留后台进程，通过冻结而非杀进程来控制资源消耗。这种策略的好处是 App 切换快、通知及时，代价是内存占用大、功耗高。AOSP 的默认策略偏向这一端。

光谱的另一端是**激进策略**——快速杀掉非白名单的后台进程，甚至对白名单的 App 也严格限制后台活动。这种策略的好处是省电、省内存，代价是用户体验差：通知延迟、App 切换需要冷启动、某些功能（如后台导航、后台音乐）可能中断。

国内厂商的策略普遍偏向激进端，但程度不一：

小米（MIUI/HyperOS）的后台管理相对激进，有完整的自启动控制和相互唤醒拦截机制。微信等头部 App 通常在白名单中，享受更宽松的后台策略——这就是为什么普通开发者会发现「微信能自启动但我的 App 不行」。

华为（EMUI/HarmonyOS）同样激进，但提供了更细粒度的后台管控设置。用户可以手动为特定 App 设置「不受限制」的后台策略，但这通常需要深入设置菜单好几层才能找到。

OPPO/vivo（ColorOS/OriginOS）的策略相对平衡，近年来通过 AI 学习用户习惯来动态调整后台策略，对用户常用的 App 放宽限制。

荣耀（MagicOS）的后台优化以省电为导向，有用户反馈其「激进电池优化器」会影响第三方 App 的通知接收和后台功能。


### 对开发者的影响

这种厂商策略的差异对开发者最直接的影响体现在两个方面：**通知可靠性**和**后台任务执行**。

通知可靠性方面，在国内环境下，开发者通常需要接入厂商自己的推送通道（小米推送、华为推送、OPPO 推送等）来保证通知送达率。开发者这么做，是因为不接入厂商推送通道，通知就会被后台管理策略吞掉。

后台任务方面，WorkManager 和 JobScheduler 的行为在不同厂商设备上可能不一致。一个在 Pixel 上正常执行的后台同步任务，在某厂商设备上可能被延迟数小时甚至完全跳过。开发者能做的最可靠的方案是使用 Foreground Service，但这会显示一个常驻通知栏——又是一个用户体验的权衡。


## 与其他机制的关系

OEM 的优化实践不是孤立存在的，它和我们前面讨论过的多个系统机制紧密关联：

OEM 的性能优化不是一个独立模块，它嵌入在全书讨论过的各个系统机制中。理解这些关联，能帮我们在 Trace 中更快判断一个现象的来源。

**与 CPU 调度的关系（§5.1～§5.4）**：厂商在 Kernel 层的调度器调优直接影响 EAS 的行为。如果你在 Perfetto 中看到 CPU 迁移策略跟 AOSP 默认行为不同，很可能是厂商修改了 sched_energy_cost 或者 CPU capacity 的配置。DVFS 的 governor 选择和参数调优（§5.4）同样因厂商而异。

**与内存管理的关系（§4.1～§4.4）**：厂商调整 LMK 的阈值参数是最常见的内存优化手段。当你在 Perfetto 中观察到后台进程被杀的时机跟 §4.4 描述的 AOSP 默认行为不一致时，应该想到这是厂商策略干预的结果。

**与渲染管线的关系（§2.1～§2.6）**：SurfaceFlinger 的合成策略、VSync offset 的配置、GPU 调度策略都可能被厂商定制。这些定制会影响帧渲染的时序，导致你在 Trace 中看到的帧渲染模式跟 Pixel 设备不同。

**与启动优化（§8.3）的关系**：厂商的预加载和预测启动策略直接改变了启动 Trace 的形态。如果启动 Trace 中缺少 Zygote fork 阶段，或者某些类的加载耗时异常短，这通常是厂商预加载的结果。

## 版本演进

OEM 优化策略随 Android 版本的演进经历了几个关键转折点：

**Android 5.0（2014）**：ART 替代 Dalvik，AOT 编译为厂商提供了预编译优化的基础。JobScheduler API 引入，为后台任务管理提供了标准接口。

**Android 6.0（2015）**：Doze 模式和 App Standby 引入，这是 Google 第一次系统性地从 AOSP 层面限制后台行为。厂商在此基础上做了大量增强。

**Android 8.0（2017）**：后台执行限制大幅收紧——隐式广播被大量禁用、后台服务受限。这迫使 App 改用更规范的后台方案，也为厂商的优化提供了更干净的基础。

**Android 9.0（2018）**：Adaptive Battery 引入，基于机器学习预测用户使用习惯来分配后台资源。厂商纷纷在此基础上训练自己的模型。

**Android 11（2020）**：cached apps freezer 正式引入（QPR3），基于 cgroup v2 的进程冻结成为 AOSP 标准方案。厂商从自己的 SIGSTOP/cgroup 方案逐步迁移到 AOSP 标准。

**Android 12（2021）**：前台服务启动限制更加严格，Exact Alarm 需要特殊权限。进一步收紧了 App 的后台行为空间。

**Android 14（2023）**：前台服务类型强制声明，每种类型有明确的使用场景限制。与 Samsung 合作改进了后台 App 管理 API，提升了跨设备一致性。


## 常见问题与误区

**误区一：「手机卡一定是 App 写得烂。」**

不完全对。如果你在一家厂商的设备上卡顿但其他设备正常，第一反应应该是检查厂商的后台管理策略和调度策略。某些厂商在灭屏后会限制所有非前台进程的 CPU 使用，这会导致 App 正在执行的后台同步变慢，进而影响下次打开的速度。在 Perfetto 中对比不同设备上同一 App 的 Trace，往往能发现差异来源不是 App 代码，而是系统策略。

**误区二：「厂商的优化一定比 AOSP 好。」**

不一定。厂商的优化往往是针对特定使用场景和硬件配置做的，在某些场景下可能比 AOSP 好很多（比如游戏场景、常用 App 启动场景），但在另一些场景下可能更差（比如多任务切换、长时间运行后台任务）。特别是杀后台过于激进的厂商，用户的多任务体验往往更差。

**误区三：「白名单是解决一切问题的办法。」**

让 App 进入厂商的白名单能解决大部分后台限制问题，但这是一个短视的方案。白名单是厂商和头部 App 之间的博弈结果，普通 App 很难进入。正确的做法是使用 Android 标准的后台 API（Foreground Service、WorkManager），并在必要时接入厂商的推送通道。

**误区四：「冻结等于杀进程。」**

不等。冻结（cgroup freezer）是将进程挂起但保留其在内存中的状态，恢复时不需要冷启动。杀进程是完全销毁进程，下次启动需要从 Zygote fork 开始。在 Perfetto 中，被冻结的进程的线程会从 CPU Track 上消失但进程条仍然存在；被杀的进程则完全消失，下次出现时伴随完整的启动 Trace。

**误区五：「厂商之间的差异只在 UI 层。」**

远远不止。从 Kernel 的调度器参数到 Framework 的 AMS/WMS 逻辑，厂商几乎在每个层面都做了定制。如果你只分析过 Pixel 设备的 Trace，迁移到厂商设备分析时需要重新建立对「正常行为」的认知基线。

## 参考资料

### AOSP 源码路径
- `frameworks/base/services/core/java/com/android/server/am/CachedAppOptimizer.java` — cgroup freezer 管理
- `frameworks/base/core/java/com/android/internal/os/ZygoteInit.java` — Zygote 预加载逻辑
- `frameworks/base/services/core/java/com/android/server/am/ActivityManagerService.java` — 进程优先级和 OOM Adj 管理
- `system/core/init/init.cpp` — 系统启动流程
- `kernel/sched/` — CPU 调度器实现

### 官方文档
- [Cached Apps Freezer](https://source.android.com/docs/core/perf/cached-apps-freezer) — AOSP 官方冻结机制说明
- [Background Optimization](https://developer.android.com/topic/performance/background-optimization) — 后台优化指南
- [Foreground Services](https://developer.android.com/guide/components/foreground-services) — 前台服务使用指南
- [Power Management](https://source.android.com/docs/core/power) — 电源管理

### 深入阅读
- [OS 设计之性能设计系列](https://www.androidperformance.com/2023/08/21/the-performance-design-of-os/) — Yingyun 大佬关于 OS 性能设计的深度思考
- [Android 系统优化的那 10 年](https://mp.weixin.qq.com/s/606a7fadda223d94dff5194079ae78b7) — 系统优化历史回顾

---

> **验证状态**：L2 验证通过 8 处（AOSP 源码路径、官方文档、Linux man page），待验证 4 处（厂商具体策略参数）。信心等级：medium。
>
> **素材来源**：obsidian/Personal-Knowlodge/source/2026-03-08_wechat_Android系统优化的那10年.md、obsidian/Personal-Knowlodge/source/the-performance-design-of-os.md、source.android.com、developer.android.com

### Android 16 Market Share Reaches 20.4%
- 来源：https://www.appbrain.com/stats/top-android-sdk-versions
- 类型：技术资讯
- 摘要：Android平台在2026年保持强劲发展势头，新功能不断推出，用户体验持续改善，生态系统更加完善。
- 入库时间：2026-05-31
- 评分：12/20

### Android 16 Market Share Reaches 20.4%
- 来源：https://www.appbrain.com/stats/top-android-sdk-versions
- 类型：技术资讯
- 摘要：Android 16以20.4%的市场份额成为最受欢迎的版本，反映出用户对新功能、安全性和性能优化的积极认可。
- 入库时间：2026-05-31
- 评分：16/20

### Android 16 Market Share Reaches 20.4%
- 来源：https://www.appbrain.com/stats/top-android-sdk-versions
- 类型：技术资讯
- 摘要：Android平台在2026年保持强劲发展势头，新功能不断推出，用户体验持续改善，生态系统更加完善。
- 入库时间：2026-05-31
- 评分：12/20

### Android 16 Market Share Reaches 20.4%
- 来源：https://www.appbrain.com/stats/top-android-sdk-versions
- 类型：技术资讯
- 摘要：Android 16以20.4%的市场份额成为最受欢迎的版本，反映出用户对新功能、安全性和性能优化的积极认可。
- 入库时间：2026-05-31
- 评分：16/20

### Android 16 Market Share Reaches 20.4%
- 来源：https://www.appbrain.com/stats/top-android-sdk-versions
- 类型：技术资讯
- 摘要：Android平台在2026年保持强劲发展势头，新功能不断推出，用户体验持续改善，生态系统更加完善。
- 入库时间：2026-05-31
- 评分：12/20

### Android 16 Market Share Reaches 20.4%
- 来源：https://www.appbrain.com/stats/top-android-sdk-versions
- 类型：技术资讯
- 摘要：Android 16以20.4%的市场份额成为最受欢迎的版本，反映出用户对新功能、安全性和性能优化的积极认可。
- 入库时间：2026-05-31
- 评分：16/20

### 聊聊2026年Android开发会是什么样_android_陆业聪-开源鸿蒙跨平台开发者社区
- 来源：https://openharmonycrossplatform.csdn.net/695626f1bf6b0e4b285fea36.html
- 类型：技术资讯
- 摘要：2026年Android开发呈现AI本地化、跨平台成熟和鸿蒙挑战三大趋势，开发者需要适应AI能力设备端部署和跨平台技术的新要求。
- 入库时间：2026-05-31
- 评分：12/20

### Android 16 Market Share Reaches 20.4%
- 来源：https://www.appbrain.com/stats/top-android-sdk-versions
- 类型：技术资讯
- 摘要：Android 16以20.4%的市场份额成为最受欢迎的版本，反映出用户对新功能、安全性和性能优化的积极认可。
- 入库时间：2026-05-31
- 评分：16/20
