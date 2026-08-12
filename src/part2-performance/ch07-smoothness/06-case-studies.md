---

title: 案例集
chapter: '7.6'
section: '7.6'
applicable_versions: Android 8.0 (API 26) - Android 17 (API 37)
last_verified: '2026-07-07'
last_verified_against: "AOSP android-17.0.0_r1 / AnimatedVectorDrawable fallbackOntoUI / Android 14 cached process freezing / ComponentCallbacks2 / Lottie vs AVD Perfetto 特征"
confidence: medium-high
sources:
- type: blog
  path: obsidian/Personal-Knowlodge/source/Android-Jank-Due-To-App.md
- type: blog
  path: obsidian/Personal-Knowlodge/source/Android-Jank-Due-To-System.md
- type: blog
  path: obsidian/Personal-Knowlodge/source/Android-Jank-Due-To-Low-Memory.md
- type: blog
  path: obsidian/Personal-Knowlodge/source/2026-03-07_wechat_Android深入卡顿分析与实践.md
- type: blog
  path: obsidian/Personal-Knowlodge/source/Android-Perfetto-07-MainThread-And-RenderThread.md
- type: official
  path: https://developer.android.com/topic/performance/recycler-view
- type: official
  path: https://developer.android.com/reference/android/content/ComponentCallbacks2
tags:
- case-study
- jank
- smoothness
- GC
- layout
- binder
- render-thread
- low-memory
- perfetto
- recycler-view
- bitmap-cache
- vendor-optimization
related_chapters:
- '7.1'
- '7.2'
- '7.3'
- '7.4'
- '2.5'
- '2.7'
- '4.4'
task2b_state: "fixed"
status: finalized
pipeline_stage: "ready-to-publish"
task6_state: "reviewed"
task9_state: "reviewed"
---
# 7.6 案例集

## 案例证据怎样使用

以下五个公开工程案例覆盖主线程、GC/内存、调度、SurfaceFlinger 合成和温控。案例来源分成三类：

- 腾讯音乐技术团队的 WeSing 复盘给出了设备、测试动作、版本差异和若干 trace 数据；
- AndroidPerformance 的系统案例给出了 Systrace 截图和对照数据，但仓库没有原始 trace 文件；
- 温控案例采用 Android Developers 发布的 Netmarble ADPF 案例，保留官方披露的效果数字。

截图可以证明作者当时观察到的形态，无法替代可查询的原始 trace。下面每个案例都把“公开材料中的事实”“Android 17 下的解释”和“仍缺少的证据”分开写。历史数据不冒充 `android-17.0.0_r1` 的实测结果；Android 17 源码只用于校正机制和工具入口。

### 统一复盘格式

| 字段 | 要回答的问题 |
|---|---|
| 现场 | 哪台设备、哪个 build、什么动作、持续多久 |
| 用户结果 | 哪一帧、哪个 CUJ 或哪段启动变差 |
| 关键证据 | 线程状态、slice、counter、heap、layer、fence、thermal |
| 排除项 | 哪些相似原因已经排除 |
| 根因 | 哪条因果关系有对照实验支持 |
| 修复 | 改了哪一段工作或资源配置 |
| 效果 | 同条件下哪些指标发生变化 |
| 证据缺口 | 缺少原始 trace、样本量、设备覆盖或统计定义中的哪一项 |

---

## 案例一：WeSing 歌房进房的一条主线程消息过重

### 现场与公开数据

腾讯音乐技术团队在 WeSing 歌房进房场景做过两轮优化。公开测试条件是 OnePlus 10 Pro、Android 12、进程冷启动，点击进房后等待 8 秒让 UI 稳定。原文报告 5.65 与 5.70 两轮优化后，PerfDog 卡顿率改善接近 50%。

其中一条主线程消息集中创建微服务并派发 Activity、Fragment 和音视频生命周期。trace 截图给出的服务实例创建时间为 312 ms；同一复盘还记录了 40 ms 的生命周期分发、115 ms 的音视频 SDK 初始化、103 ms 的 bitmap 模糊和 18 ms 的日志参数拼接。

![WeSing 进房服务创建 trace](https://image.cubox.pro/cardImg/2023121920204054940/61512.jpg?imageMogr2/quality/90/ignore-error/1)

这些数字属于该团队的设备、版本和 PerfDog 口径，不能换算成 Android vitals 或其他应用的收益。

### 从现象到根因

分析没有停在“主线程有一个 312 ms 长任务”。团队继续拆开这条消息里的工作：

1. 微服务框架允许 lazy 初始化，但业务不断把服务标成进房预加载；
2. 多个单项成本集中在同一条 Looper message，首批 UI 更新只能排在它们之后；
3. 部分工作有严格的 UI 或生命周期顺序，不能全部丢到线程池；
4. bitmap 处理、配置 JSON 和部分 SDK 初始化可以脱离主线程；
5. 日志方法即使最终不输出，调用前的字符串拼接和序列化已经发生。

根因由“单个方法很慢”扩展为“进房依赖没有分层，必须完成、可延后、可预热和可异步的工作混在同一条消息中”。

### 修复

公开复盘采用了五组动作：

- 删除无必要的预加载，把服务默认改为 lazy；
- 将无 UI 依赖的解析、bitmap 处理等移到工作线程；
- 对进房后立即使用且类加载昂贵的组件做有条件预热；
- 把必须在主线程执行的生命周期工作拆成小段，并保持业务顺序；
- 避免关闭日志后仍构造昂贵参数。

原案例为了消息顺序使用过 `postAtFrontOfQueue()`。这个 API 会插队，可能延迟输入、traversal 和其他消息。迁移到新项目时，应把依赖写成显式状态机或阶段队列，并给每段工作设置预算和取消条件；不能复制“插到队头”这一实现细节。

### 效果与证据边界

原文披露两项结果：整体 PerfDog 卡顿率接近减半；有条件预热让线上进房平均耗时减少 250 ms。它没有公开完整样本量、分位数和全部前后 trace，因此这两项数据只描述 WeSing 当时的发布结果。

在 Android 17 上复验同类修改，应对齐：

- 目标 CUJ 的 FrameTimeline 与进房 marker；
- 每条主线程 message 的 wall time、Running 与 Runnable 时间；
- 冷启动类加载/JIT、后台预热 CPU 和内存；
- 第一帧、内容稳定时刻与用户可交互时刻；
- 拆分后是否出现时序错误或首次点击延迟。

来源：[Android 深入卡顿分析与实践（QQ 音乐技术团队）](https://cloud.tencent.com/developer/article/2372774)。

---

## 案例二：反复进退房后的内存增长与 GC

### 现场与公开数据

同一 WeSing 复盘记录了“开始流畅，反复进退歌房后越来越卡”的问题。Profiler 显示房间退出后仍有对象存活，其中一个根因是弹窗关闭后动画没有停止，引用链继续保留页面对象。原文还记录了内存紧张时进房更容易触发频繁 GC。

![反复进退房后的内存增长](https://image.cubox.pro/cardImg/2023121920204870875/18152.jpg?imageMogr2/quality/90/ignore-error/1)

公开材料没有给出该泄漏修复前后的 GC pause 分位值或 JankStats 对照。因而这里只保留“引用链与生命周期修复”结论，不采用缺少来源的堆大小、GC 次数和卡顿率。

### 从现象到根因

“使用一段时间后变慢，重启恢复”可以由多种因素造成：Java/native 泄漏、图片/GPU 缓存、线程增长、热限制、系统内存压力或存储 I/O。确认 GC 因果关系需要三组证据同时出现：

1. 相同操作循环下，Java/native/graphics 内存或存活对象持续增长；
2. ART GC 的 pause 或 allocation stall 更频繁，并与异常帧相交；
3. Heap dump、heapprofd 或引用分析指向无法释放的对象；
4. 修掉引用或限制缓存后，内存曲线、GC 事件和帧长尾同步改善。

ART 的并发 GC 仍包含暂停阶段，但不能把整个 Concurrent GC slice 都算作主线程 Stop-The-World 时间。应查看 trace 中明确的 pause、线程状态和分配等待。不同 Android/ART 版本的事件名称会变化，固定搜索 `GC For Alloc` 不够稳。

原案例中“弹窗关闭后动画仍持有页面”的引用链能解释对象为何存活。修复动作是结束动画、移除回调/监听并释放与页面生命周期绑定的对象。缓存问题还要分别按 Java heap、native allocation、GraphicBuffer/dma-buf 和 GPU 资源计量。

### 低内存对照：不要把系统压力误判成应用泄漏

AndroidPerformance 还公开过一组整机低内存冷启动对照：

| 条件 | bindApplication 到第一帧 | Block I/O 与 Uninterruptible Sleep/WakeKill | Running |
|---|---:|---:|---:|
| 低内存 | 约 2.0 s | 约 750 ms | 约 600–682 ms |
| 正常内存 | 约 1.22 s | 约 130 ms | 约 624 ms |

![低内存冷启动 trace](https://www.androidperformance.com/images/15688227815756.jpg)

![正常内存冷启动 trace](https://www.androidperformance.com/images/15688228638217.jpg)

这组数据表明，两次启动的 Running 时间接近，差异主要落在 I/O/不可中断等待及系统内存活动。它不能证明所有低内存卡顿都由 I/O 导致，但足以排除“应用 CPU 计算增加”作为该次对照的主解释。

Android 17 / `android17-6.18-2026-06_r6` 下应查看 PSI memory、direct reclaim、kswapd、swap/zram I/O、major fault、lmkd 事件和前台线程状态。现代 lmkd 主要依据 PSI 与进程优先级工作，旧内核里的 lowmemorykiller 日志和固定 minfree 配方不应直接搬过来。

### 修复与效果

应用泄漏路径的修复目标是让房间退出后对象可回收，并限制可重建缓存。整机低内存路径则需要减少前后台常驻、避免前台直接回收/I/O，并由系统团队在目标设备上调校 lmkd、zram、回收和存储策略。

Android 14 起，应用不再收到部分旧的 `TRIM_MEMORY_RUNNING_*` 回调；对应常量在 API 35 被弃用。应用仍可用 `TRIM_MEMORY_UI_HIDDEN`、后台状态和自身预算释放可重建资源，不能等待旧式“运行中低内存”通知再处理。

验收至少包含重复进退房 heap 曲线、GC pause、FrameTimeline、native/graphics 内存、PSI 和热状态。只看到 Java heap 下降，还不足以证明 GPU buffer 或整机压力改善。

来源：[WeSing 复盘](https://cloud.tencent.com/developer/article/2372774)、[Android 低内存案例](https://www.androidperformance.com/2019/09/18/Android-Jank-Due-To-Low-Memory/)、[ComponentCallbacks2](https://developer.android.com/reference/android/content/ComponentCallbacks2)。

---

## 案例三：SDK 升级增加线程后，主线程获得 CPU 变慢

### 现场与关键数据

WeSing 5.68 的版本对比发现：

- 相比上个版本，进程增加近 30 个线程；
- file descriptor 增加约 250 个；
- 团队使用的卡顿率从 15% 上升到 20%；
- 增量线程在退出歌房后仍未减少；
- APK/版本二分把变化定位到 TRTC SDK 升级；
- Perfetto SQL 统计显示升级后的 DefaultDispatch 线程 CPU 时间超过 UI Thread 和 RenderThread。

![SDK 升级前后线程 CPU 对比](https://image.cubox.pro/cardImg/2023121920205064063/74508.jpg?imageMogr2/quality/90/ignore-error/1)

### 从相关性到根因

线程数增加本身不能证明调度卡顿。这个案例有价值，是因为团队做了版本二分、线程来源定位和 CPU 时间聚合，并由 SDK 方移除与业务无关的功能后恢复指标。

在 Android 17 上，还应补两项证据：

- 异常帧里 UI Thread/RenderThread 是否长时间处于 Runnable，wakeup 到 Running 的等待是否上升；
- 新线程在同一时间是否 Running，占用了哪些 CPU，是否带来频率、迁核、thermal、内存或 GC 变化。

如果新增线程多数处于 Sleeping，调度影响可能很小；如果一个新增 CPU worker 长时间 Running，即使线程总数不高，也能挤压交互线程。file descriptor 增长是资源回归信号，不能直接解释 CPU 调度。

### 修复

团队把问题提交给 SDK 方，去掉升级时引入但当前业务不需要的功能。通用处理包括：

- 为 SDK 和业务线程提供稳定、可聚合的名字；
- 对线程池设置有界并发、队列和取消；
- 页面退出时停止会话与 worker；
- 用版本开关或依赖回退完成 A/B；
- 分开统计线程数、CPU time、Runnable latency、RSS/PSS 和 FD。

手动把 UI Thread 或 RenderThread 固定到某个“大核”会把 SoC 拓扑、热状态和厂商调度差异写死，不能替代移除无效工作。

### 效果与证据边界

原文只写“修复后各项指标正常”，没有披露修复后的卡顿率、线程数和 FD 数。因此可复核结论到这里为止：SDK 升级稳定复现资源与卡顿回归，二分和 CPU 统计指向新增 worker，SDK 修复消除了回归。不能自行补成“20% 回到某个百分比”。

来源：[Android 深入卡顿分析与实践](https://cloud.tencent.com/developer/article/2372774)。

---

## 案例四：SurfaceFlinger GPU 合成帧迟到

### 公开 trace 观察

AndroidPerformance 的系统案例展示过 App 侧未出现对应长任务，而 SurfaceFlinger 的 GPU 合成区间拉长并伴随掉帧。原始 Systrace 图片仍可访问：

![SurfaceFlinger GPU 合成案例一](https://www.androidperformance.com/images/15683644397329.jpg)

![SurfaceFlinger GPU 合成案例二](https://www.androidperformance.com/images/15683644447973.jpg)

这是一份旧版 Systrace 现场，早于现代 FrameTimeline。图片支持“该现场的 SF GPU 合成很慢”，不包含 Android 17 的 jank type、完整 layer 属性或 HWC validate 结果。

### Android 17 下怎样重建证据

现代设备上应从目标 DisplayFrame 反查：

1. App SurfaceFrame 是否按时提交；
2. SurfaceFlinger 的 `SurfaceFlingerCpuDeadlineMissed` 或 `SurfaceFlingerGpuDeadlineMissed` 是否与用户看到的帧对应；
3. HWC validate 后哪些 layers 是 DEVICE，哪些进入 CLIENT composition；
4. CLIENT 帧中 `CompositionEngine` / `RenderEngine::drawLayers()` 和 GPU fence 是否拉长；
5. 同一时刻的可见 layer 集、格式、alpha、transform、crop、dataspace、保护属性、刷新率和 display mode；
6. present fence 何时 signal。

CLIENT composition 只表示 SurfaceFlinger 需要把相关 layers 渲染进 client target。它本身是受支持的正常路径。只有 CLIENT 变化、RenderEngine/GPU 时长和 missed DisplayFrame 在时间上对应，才能把这次卡顿归到合成降级或 GPU 合成压力。

不能按“屏幕上有五层、硬件只有四个 plane”推断根因。AOSP 没有为普通应用提供固定 overlay plane 数量查询；HWC 决策还受格式、缩放、旋转、混合、带宽和厂商策略影响。

### 修复

公开旧案例没有披露对应产品的代码改动和前后数据，这里不补造修复结果。针对同类现场，可验证的候选动作包括：

- 减少不必要的独立 Surface/Window；
- 避免让可合成 layer 带上无收益的 alpha、复杂 transform 或大面积 blur；
- 对视频/相机检查 SurfaceView、TextureView 和 overlay 选择；
- 系统侧检查 HWC capability、validate/present、client target 和驱动 fence；
- 固定亮度、分辨率、刷新率与 layer 集后做前后 trace。

成功标准是目标设备上 CLIENT/DEVICE 分配或 GPU 工作发生预期变化，SF jank type 和 present 长尾同时改善。App 主线程变短与这一结论无直接等价关系。

Android 17 源码锚点是 `SurfaceFlinger.cpp`、CompositionEngine 的 `Output.cpp`、`RenderEngine` 和 `HWComposer.cpp`。详细步骤见 [HWC Overlay Plane 与合成降级排查](./12-hwc-overlay-composition-downgrade.md)。

来源：[Android 系统平台性能案例](https://www.androidperformance.com/2019/09/05/Android-Jank-Due-To-System/)、[Hardware Composer HAL](https://source.android.com/docs/core/graphics/implement-hwc)。

---

## 案例五：Netmarble 用热反馈换取持续帧率

### 现场与公开结果

Android Developers 的 Netmarble 案例介绍了《Game of Thrones: Kingsroad》在长时间高负载后出现热限制和帧率波动。团队对画质项逐项测量，发现动态分辨率比阴影、纹理等选项更适合负责主要降载；随后根据 ADPF Thermal API 同时调整分辨率和目标帧率。

官方案例披露的结果为：

- 平均 thermal headroom 从 1.04 降到 0.92，降幅 11%；
- 未接入该策略时，热限制区间的帧率会在约 40–56 FPS 波动；
- 接入后，持续帧率通常保持在约 50–60 FPS；
- 动态目标帧率最低可降到 30 FPS，以避免不可持续的高负载。

这些数值来自官方开发者故事，但页面没有完整列出设备覆盖、环境温度和样本分布，不能作为其他游戏的 SLA。

### 从现象到根因

温度升高和频率下降同时出现，仍不足以单独确认 thermal 是首因。可信证据应包含：

- 相同内容和输入下，frame time 随会话时间变差；
- thermal status/headroom 或 cooling state 同期变化；
- CPU/GPU 可用容量减少或频率上限降低；
- 内存泄漏、后台负载、亮度和充电条件已记录；
- 冷却或降低工作量后，持续 frame time 恢复。

Netmarble 案例先测不同画质项对热负载的影响，再选择动态分辨率，这一步把“收到热信号”连接到了“哪项工作可以减少”。

### 修复

Thermal API 提供 thermal status 与 headroom。应用需要自行决定降载动作，例如 render scale、阴影、后处理、粒子、视距、模拟频率或 target FPS。调整策略应加入滞回和最短保持时间，防止阈值附近反复重建资源。

ADPF Performance Hint Session 可报告周期工作的一组线程、target duration 和 actual duration。它是给系统的提示，不保证锁频、升频或绑定某个 CPU。热保护可以覆盖性能请求。

官方最佳实践建议长时间运行测试；当前页面提出至少覆盖 15 分钟，以观察热稳定点。测试还要固定亮度、充电状态、环境温度、网络和游戏内容。

### 效果与 Android 17 边界

这个案例的收益来自“提前降低不可持续负载”，画质和目标帧率本身也发生了变化。比较时要同时报告画质档位、实际 render scale、目标/显示/提交帧率、功耗和 thermal headroom，不能只比较平均 FPS。

Android 17 / API 37 继续提供 Thermal API、ADPF 与 CPU/GPU headroom 相关能力。设备支持和厂商映射仍有差异；`getThermalHeadroom()` 返回 NaN 时，要考虑调用间隔或设备不支持。热状态的同一个等级也不能换算成统一的 CPU/GPU 频率。

来源：[Netmarble ADPF 案例](https://developer.android.com/stories/games/netmarble-got-adpf)、[ADPF Thermal API](https://developer.android.com/games/optimize/adpf/thermal)、[ADPF 最佳实践](https://developer.android.com/games/optimize/adpf/best-practices-adpf)。

---

## 五个案例放在一张责任表里

| 案例 | 用户侧结果 | 最早异常证据 | 责任边界 | 修复类型 |
|---|---|---|---|---|
| WeSing 进房 | 进入阶段多次长停顿 | 一条 UI message 聚集 312 ms 创建及其他任务 | 应用主线程与初始化架构 | lazy、异步、预热、拆分依赖 |
| 进退房内存 | 使用时间越长越卡 | 对象无法释放、GC/分配压力 | 应用生命周期；另查整机内存 | 断引用、停动画、限制缓存 |
| SDK 线程回归 | 新版本卡顿率上升 | +30 线程、+250 FD、worker CPU 上升 | SDK 并发与调度竞争 | 移除无关功能、有界线程池 |
| SF GPU 合成 | App 侧短，显示仍迟到 | SF/RenderEngine GPU 合成区间 | SurfaceFlinger/HWC/GPU | 简化 layer 条件或修 HWC/驱动 |
| Netmarble 热限制 | 长会话帧率波动 | thermal headroom 与持续性能 | 应用负载、Power/Thermal HAL、SoC | 动态分辨率与目标帧率 |

这张表的“责任边界”不是团队归属。应用 layer 属性可能触发显示侧成本，系统内存压力也会放大应用 I/O。它表示下一步需要哪类证据和修改权限。

---

## Android 17 复现实验清单

### App 主线程、GC 与调度

- FrameTimeline、目标 CUJ 和应用 marker；
- UI Thread、RenderThread、Binder、sched wakeup/switch；
- ART GC pause、allocation、HeapTaskDaemon；
- Java/native/graphics memory、heapprofd、PSI；
- 线程 CPU time、Runnable latency、FD 与任务队列。

### SurfaceFlinger 与 HWC

- SurfaceFlinger FrameTimeline、layers、transactions；
- target layer 的 buffer/frame number 与 acquire fence；
- DEVICE/CLIENT composition、client target；
- RenderEngine/GPU 与 present fence；
- display id、刷新率、亮度和分辨率。

### Thermal

- thermal status/headroom、CPU/GPU headroom；
- CPU/GPU frequency、idle、调度与 ADPF session；
- 实际画质、render scale、target FPS 与提交节奏；
- 环境温度、充电、亮度和至少覆盖热稳定点的测试时长。

平台源码以 `android-17.0.0_r1` 为上界，内核以 `android17-6.18-2026-06_r6` 为锚点。ART、AndroidX、WebView、游戏引擎、GPU/HWC 与 OEM 策略还要记录各自版本。旧 Systrace 案例可用于认识形态，当前结论必须由目标 build 的 Perfetto/Winscope/厂商数据重建。

---

## 相关章节

- [卡顿原因](./02-jank-causes.md)
- [分析方法](./03-jank-methodology.md)
- [典型场景](./04-typical-scenarios.md)
- [优化策略](./05-optimization.md)
- [热节流适配与性能降级治理](../../part5-app/ch25-power-size/16-thermal-throttling-performance.md)
- [系统内存压力与 lmkd](../../part1-fundamentals/ch04-memory/04-lmk.md)
- [Android Thermal](../../part1-fundamentals/ch05-cpu-power/05-thermal.md)
- [ADPF](../../part1-fundamentals/ch05-cpu-power/09-adpf.md)
- [视频 Overlay 与 HWC](../ch18-rendering-pipelines/15-video-overlay-hwc.md)

## 参考资料

- [Android 深入卡顿分析与实践](https://cloud.tencent.com/developer/article/2372774)
- [Android App 自身导致的卡顿案例](https://www.androidperformance.com/2019/09/05/Android-Jank-Due-To-App/)
- [Android 系统平台导致的卡顿案例](https://www.androidperformance.com/2019/09/05/Android-Jank-Due-To-System/)
- [Android 低内存案例](https://www.androidperformance.com/2019/09/18/Android-Jank-Due-To-Low-Memory/)
- [Perfetto FrameTimeline](https://perfetto.dev/docs/data-sources/frametimeline)
- [Hardware Composer HAL](https://source.android.com/docs/core/graphics/implement-hwc)
- [ComponentCallbacks2](https://developer.android.com/reference/android/content/ComponentCallbacks2)
- [Netmarble ADPF 案例](https://developer.android.com/stories/games/netmarble-got-adpf)
- [ADPF Thermal API](https://developer.android.com/games/optimize/adpf/thermal)
- [ADPF 最佳实践](https://developer.android.com/games/optimize/adpf/best-practices-adpf)
- [AOSP Android 17 SurfaceFlinger](https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/services/surfaceflinger/SurfaceFlinger.cpp)
- [AOSP Android 17 CompositionEngine Output](https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/services/surfaceflinger/CompositionEngine/src/Output.cpp)
- [AOSP Android 17 HWComposer](https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/services/surfaceflinger/DisplayHardware/HWComposer.cpp)
- [AOSP Android 17 PowerManager](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/os/PowerManager.java)
- [Android common kernel PSI](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/kernel/sched/psi.c)
- [Android common kernel reclaim](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/mm/vmscan.c)
