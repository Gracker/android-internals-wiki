---
title: 竞品分析方法
chapter: '16.6'
section: '16.6'
status: finalized
applicable_versions: Android 8.0 (API 26) - Android 17 (API 37)
last_verified: '2026-08-14'
last_verified_against: AOSP android-17.0.0_r1 ActivityManagerShellCommand / WaitResult / ActivityTaskSupervisor / ActivityMetricsLogger / ActivityRecord / FrameMetrics / FrameTimeline; Android Developers current official documentation
confidence: high
sources:
- type: official
  path: https://developer.android.com/topic/performance/vitals/launch-time
- type: aosp
  path: frameworks/base/services/core/java/com/android/server/am/ActivityManagerShellCommand.java
- type: aosp
  path: frameworks/base/core/java/android/app/WaitResult.java
- type: aosp
  path: frameworks/base/services/core/java/com/android/server/wm/ActivityMetricsLogger.java
- type: aosp
  path: frameworks/base/services/core/java/com/android/server/wm/ActivityRecord.java
- type: official
  path: https://developer.android.com/studio/debug/apk-analyzer
- type: official
  path: https://developer.android.com/topic/performance/benchmarking/benchmarking-overview
- type: official
  path: https://developer.android.com/reference/android/view/FrameMetrics
- type: aosp
  path: frameworks/base/core/java/android/view/FrameMetrics.java
- type: aosp
  path: frameworks/native/services/surfaceflinger/Scheduler/FrameTimeline.cpp
tags:
- competitive-analysis
- benchmark
- startup
- fps
- apk-size
- methodology
related_chapters:
- '7.2'
- '8.3'
- '25.10'
- '14.1'
- '15.1'
- '16.3'
---

# 竞品分析方法

竞品对比只有在场景、设备状态、版本和指标口径一致时才有解释力。我们做它的目的，是用可重复的实验判断差异落在哪个用户阶段、竞品的哪些设计可以迁移到自己的产品上；一份笼统的排名反倒是次要产出。

> 源码基线：AOSP `android-17.0.0_r1`（Android 17 / API 37）；涉及调度、频率或功耗事件的解释时，内核证据固定到 `android17-6.18-2026-06_r6`。设备可能使用其他内核分支。

## 为什么要认真做竞品性能分析

竞品测试回答的是一个有边界的问题：

> 在指定设备、系统版本、应用版本、账号状态和操作路径下，两个应用的观测结果有多大差异？

先把边界记住：一轮竞品测试量出的是差异有多大、出现在哪个阶段。至于差异由哪段代码造成、放到全部用户身上是否成立，它回答不了，要回到源码、Trace 和更多设备上补证据。所以实验条件必须随结果一起写进报告；缺了条件，一个启动耗时或卡顿率几乎无法复现，更撑不起版本决策。

本文的源码结论只用于解释 Android 平台的计时和帧数据。竞品的业务实现我们看不见，写原因时只能写成假设，并列出还缺哪些证据。

## 竞品性能对比的方法论

一轮可复现的竞品测试至少包含四份记录：

1. **问题定义**：比较哪个用户场景、哪个指标、哪个时间窗口；
2. **实验清单**：设备、构建、应用版本、账号、数据集、网络、温度与编译状态；
3. **原始结果**：每次执行的顺序、成功或失败、指标值及对应 Trace；
4. **结论边界**：观察到了什么、尚未证明什么、下一步需要哪种证据。

### 控制变量的四项基本原则

**同设备**：A/B（成对交替测试两个应用）在同一台物理设备、同一用户和同一显示模式下执行。就算型号相同，芯片个体差异、存储老化和厂商配置也可能不同。要覆盖多个档位时，每台设备独立形成一组结果，不把不同设备的样本混成一个分布。

**同场景**：使用用户可感知的起点、终点和成功条件。例如“从 Launcher 点击图标，到首个可操作 Feed 出现”，还要补上账号是否登录、缓存是否存在、广告是否展示、列表有多少项。两个产品的信息架构不同，页面名称对不上没关系，工作量和用户目标要相近。

**同网络**：记录 Wi-Fi 或蜂窝网络、带宽、往返延迟、丢包、DNS、代理和服务端数据集。可控环境可以使用网络整形和固定响应；真实网络测试则交替执行 A/B，并把网络时间单列。TLS 会话是否复用、内容是否命中 CDN 边缘缓存、服务端负载如何，这三样靠“连同一个 Wi-Fi”消不掉，要单独记录。

**同热状态**：记录电池温度、Thermal Service（热管理服务）状态和测试前的静置条件。别连续测完 A 再测 B：用 ABBA 交错顺序，例如 A1、B1、B2、A2，减少时间漂移对单方结果的偏置，或者预先随机排序。设备一旦进入新的 thermal status（热状态等级），该轮作废，等它恢复再继续。用户体验测试不要锁定 CPU 频率——固定频率会改变商用设备上的调度和温控行为。

### 测试前的设备准备

准备项要写进机器可读的 run manifest，也就是每轮测试随结果保存的配置清单，避免依靠测试人员记忆：

- 设备序列号、型号、build fingerprint（系统构建标识）、API level、安全补丁和刷新率；
- App 的包名、versionName、versionCode、安装来源、签名摘要，以及 APK 和 split APK（按设备配置拆分的安装包）文件摘要；
- 账号、地区、语言、主题、权限、实验开关和本地数据状态；
- 电量、充电状态、节电/性能模式、亮度、音量、屏幕方向和网络参数；
- ART 编译策略，以及 Baseline Profile（随 App 发布的热点代码清单）是否保留；Cloud Profile 由 Google Play 按线上使用数据生成，是否保留同样要记录；
- 测试脚本版本、数据版本、执行时间和测试顺序。

`adb shell am kill-all` 只结束系统认为可以安全清理的后台进程，离“设备恢复到一致状态”还差得远；划掉最近任务同样未必让进程退出。所以每个测试维度要有自己的复位动作：启动测试控制目标进程与任务，滑动测试恢复列表位置，网络测试恢复响应数据，功耗测试恢复电量和热状态。

系统动画关不关，取决于问题定义。测 Activity 自身首帧时可以关；测用户看到的完整转场时必须保留，并固定动画缩放。两种结果分开报。

### 采样、顺序与停止条件

样本量该由数据决定：场景波动、想检测的差异大小和设备数量都会改变样本需求，把“20 次”“30 次”写死在流程里并没有统计上的保证。我们先做小规模预采样，再在测试计划中固定：

- 每台设备的最少有效轮数；
- 单轮超时和失败判定；
- 因来电、更新、温控或网络失控而排除样本的规则；
- 最大轮数，或置信区间达到目标宽度时停止；
- 查看结果前已经确定的主指标。

A/B 在同一设备、相近时间内成对执行。报告给出每轮原始值、配对差值、差值中位数、P90/P99 和置信区间；分位数的读法是 P90 表示 90% 的样本不高于该值。置信区间描述在既定统计方法下，真实差异的合理范围。

平均值、标准差可以照报，但别用“均值相差两倍标准差”来代替显著性检验：数据有长尾时，用配对 bootstrap（对配对差值重复重采样）估计区间，或用预先选定、不要求正态分布的非参数检验，并同时报告效应量，也就是差异本身有多大。

## 竞品启动速度对比

启动至少有两个用户口径：

- **TTID（Time to Initial Display，首次画面显示时间）**：应用首帧显示；
- **TTFD（Time to Full Display，完整画面显示时间）**：应用主动调用 `reportFullyDrawn()` 报告内容可用。

TTID 由系统判定，TTFD 靠应用自己埋点。竞品有没有调用、调用位置和我们的是否等价，从外部未必确认得了；确认不了时，TTFD 不能横向比较，只能各自纵向看趋势。

### adb am start -W 的原理与正确使用

`ActivityManagerShellCommand` 看到 `-W` 后调用 `startActivityAndWait()`。目标 Activity 的窗口绘制完成时，`ActivityRecord#onWindowsDrawn()` 经 `ActivityMetricsLogger#notifyWindowsDrawn()` 得到 `windowsDrawnDelayMs`，再由 `ActivityTaskSupervisor#reportActivityLaunched()` 写入 `WaitResult.totalTime` 并唤醒等待者。沿着这条调用链可以看到，`TotalTime` 的终点就是窗口绘制事件，我们读输出时要用对这一点。

下面的命令用于确认一个**进程冷启动**样本。Intent 描述待执行的操作和目标组件；`-S` 在启动前 force-stop（强制停止）Intent 匹配到的包，`-W` 等待启动结果：

```bash
adb shell am start -S -W \
  -a android.intent.action.MAIN \
  -c android.intent.category.LAUNCHER \
  com.example.app/.MainActivity
```

这条命令碰不到文件页缓存、应用数据和服务端缓存，“冷”只描述进程在启动前不存在。要测首次安装、首次登录或冷数据，另设场景，别指望 `-S`。

`android-17.0.0_r1` 的典型输出如下：

```text
Starting: Intent { act=android.intent.action.MAIN cat=[android.intent.category.LAUNCHER]
                  cmp=com.example.app/.MainActivity }
Status: ok
LaunchState: COLD
Activity: com.example.app/.MainActivity
TotalTime: 1024
WaitTime: 1038
Complete
```

三个字段的读法，以源码为准：

- **LaunchState**：`WaitResult` 明确区分 `COLD`、`WARM`、`HOT`、`RELAUNCH`。报告必须保存这个字段；预期是 COLD 却得到其他状态时，该轮无效。
- **TotalTime**：Activity 启动跟踪开始到目标窗口完成首轮绘制的延迟，接近 TTID 的系统口径，量到窗口绘制为止；页面数据是否齐备、业务是否可操作，要再对照 TTFD 的埋点。
- **WaitTime**：`ActivityManagerShellCommand` 在调用前后用 uptime 计算阻塞时间。uptime 是设备开机后的运行时长，深度休眠时不增长；WaitTime 包含 shell 发起、系统等待和返回路径，适合诊断命令等待，别拿它替代 `TotalTime`。

旧版本曾输出 `ThisTime`，Android 17 的 [`WaitResult.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/app/WaitResult.java) 已无该字段，[`ActivityManagerShellCommand.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/am/ActivityManagerShellCommand.java) 也不再打印它。解析脚本要按目标系统版本识别字段，别假定三个时间值一直都在。

### 冷启动 vs 温启动 vs 热启动

下面四项解释 `am start -W` 返回的 `LaunchState`。它按进程是否运行、Activity 是否新建来分类，比用户层面的通用启动定义窄；报告里注明用的是哪套口径。

- **Cold**：目标应用进程需要创建。文件缓存和应用数据可以仍在。
- **Warm**：进程可复用，但 Activity 需要创建。
- **Hot**：进程和 Activity 可复用，任务被带回前台。
- **Relaunch**：Android 17 还会报告 `RELAUNCH`，例如配置变化使已有 Activity 销毁重建。

测试脚本应让平台返回的 `LaunchState` 参与校验，少用“按了返回键所以一定是 warm”这类间接判断。一个竞品可能通过透明 Activity、deep link（直达指定页面的链接）、多进程或不同 task（Activity 任务栈）策略进入首页，`TotalTime` 覆盖到哪个 Activity，取决于本次实际启动链。Perfetto 中的 Android App Startups 派生指标和 Activity transition 能补足这段时间线。

### 启动对比的注意事项

**SplashScreen**：Android 12 起的系统启动画面会早于应用首帧出现，但 `TotalTime` 的完成点仍来自目标 Activity 的窗口绘制，到不了“页面数据可用”。报告可以同时保留“启动画面出现”“应用首帧”“业务可操作”三个视觉时间点；后两者需要 Trace、视频或等价的 UI 状态检测。

**编译状态**：Play 安装的包可能带 Baseline Profile，用一段时间后还可能积累 JIT 产物或 Cloud Profile。竞品对比先选一种协议并写进报告：

- **商店现实状态**：保留各自经商店分发和正常使用形成的编译状态，回答用户现实体验问题；
- **统一实验状态**：对所有包执行同一安装、交互和编译流程，回答固定 ART 条件下的差异。

以下命令把整个包按 `speed` 模式预编译，适合统一实验状态：

```bash
adb shell cmd package compile -m speed -f com.example.app
```

它偏离了用户从 Play 安装后的自然状态，结果别叫“商店体验”。`speed-profile` 只按设备上已有的 profile 预编译热点代码；各 App 的 profile 是否存在、质量是否相近没有核验过，用它反而引入新的不一致。

**窗口与显示状态**：锁屏、分屏、画中画、外接显示器、刷新率切换和系统转场都会改变启动路径。每轮开始前校验，别只在整批开始前设置一次。

## 竞品流畅性对比

平均 FPS 会把停顿的位置和长度抹平，所以我们看流畅性时不只盯这一个数：帧 deadline（每帧的完成时限）命中情况、长尾帧、连续卡顿段、场景阶段和帧归属至少要有。加载中的临时界面、页面转场和稳定滑动分开统计。

### 抓 Trace 对比帧耗时分布

Android 12 起，SurfaceFlinger 的 FrameTimeline 能把 App 产生的帧和显示端呈现的帧关联起来；固定源码版本可查 [`FrameTimeline.cpp`](https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/services/surfaceflinger/Scheduler/FrameTimeline.cpp) 与 [`frame_timeline_event.proto`](https://android.googlesource.com/platform/external/perfetto/+/refs/tags/android-17.0.0_r1/protos/perfetto/trace/android/frame_timeline_event.proto)。

一次 Trace 需要包含：

- `android.surfaceflinger.frametimeline` 数据源；
- `linux.ftrace` 中与 View、input、window manager、graphics 相关的 atrace 分类；
- 目标包的 atrace events，也就是 App 通过 Android Trace 标记写入的事件；
- 场景开始、结束和阶段切换标记。

Trace 时长要覆盖完整的操作路径，没有通用值：“至少 10 秒”这类说法不必遵守——短动画可能几秒就够，长列表或视频场景可能要一分钟。持续时间跟着场景定义走，帧数和有效区间一起报告。

滑动可以由 UI Automator（可跨 App 操作界面的自动化测试框架）或坐标事件驱动。坐标相同只说明输入相同；两个应用各自滚了多远、内容工作量多大，还要用可见 item、页面标识或录屏确认终点。`sendevent` 是向 Linux 输入设备节点写事件的低层命令，依赖设备节点和权限，不适合作为可移植方案。

### 帧耗时分析的关键指标

**deadline miss 率**：未按时完成的帧占比。判断要用每帧自己的 deadline，不硬编码 60 Hz 的 16.6 ms 或 120 Hz 的 8.3 ms——可变刷新率、App 对期望帧率的投票和 SurfaceFlinger 调度都会让相邻帧的预算不同。

**P50/P90/P99**：分位数描述主体与长尾。统计对象必须写明：应用帧实际时长、预期时长、超出 deadline 的时长，还是帧间隔；不同字段的 P99 不能直接比较。

**连续卡顿段**：记录同一交互中连续 miss 的帧数和持续时间。单个长帧与连续多个超时帧，即使落在相似的百分位，也会形成不同的视觉现象。

**归属**：FrameTimeline 的 App Jank、SurfaceFlinger Jank 和 jank type（平台标记的卡顿来源类型）是定位线索。要把责任落到业务代码、GPU 驱动或系统服务，还得回到 UI thread、RenderThread、GPU 和 SurfaceFlinger 时间线里找直接阻塞关系。

**有效帧集合**：标出首帧、窗口转场、无内容变化帧和测试脚本空等帧。排除规则在看数据之前设定，并对 A/B 使用同一规则。

### FrameMetrics 能做什么

`FrameMetrics` 从 API 24 提供 `Window` 帧的分阶段耗时，适合接在**我们自己控制的应用**里；未授权的竞品进程注入不了，所以它当不了任意竞品的线上采集方案。

即使双方都接入了同类 APM（Application Performance Monitoring，应用性能监控）系统，也要确认采样率、过滤规则、窗口范围和用户分群一致。

下面的监听器用于自有应用记录总时长、deadline 和首绘标记。`DEADLINE` 从 API 31 才可用，因此示例显式保留旧系统的缺失值：

```java
activity.getWindow().addOnFrameMetricsAvailableListener(
    (window, frameMetrics, dropCountSinceLastInvocation) -> {
        long totalDuration = frameMetrics.getMetric(FrameMetrics.TOTAL_DURATION);
        long deadline = Build.VERSION.SDK_INT >= Build.VERSION_CODES.S
                ? frameMetrics.getMetric(FrameMetrics.DEADLINE)
                : -1L;
        boolean firstDraw =
                frameMetrics.getMetric(FrameMetrics.FIRST_DRAW_FRAME) == 1L;
        recordFrame(totalDuration, deadline, firstDraw, dropCountSinceLastInvocation);
    },
    metricsHandler
);
```

回调处理放到专用 `HandlerThread`（带消息循环的后台线程），避免主线程上的采集逻辑干扰被测对象。`dropCountSinceLastInvocation` 是监听器来不及接收的帧数，要连同数据一起上报，否则繁忙时段会被低估。API 26–30 的 `deadline == -1` 样本拿不到 deadline，miss 判定对它们不适用。

Android 17 的 [`FrameMetrics.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/view/FrameMetrics.java) 定义 `TOTAL_DURATION = INTENDED_VSYNC → FRAME_COMPLETED` 和 `DEADLINE = INTENDED_VSYNC → FRAME_DEADLINE`，源码注释用 `TOTAL_DURATION < DEADLINE` 表示按时完成；两者相等时别判为命中。`FIRST_DRAW_FRAME` 通常应从动画卡顿统计中单列。

`dumpsys gfxinfo <package> framestats` 可以作为无侵入备选，但它主要反映 HWUI 窗口帧，输出字段随平台演进，覆盖面也不等同 FrameTimeline。解析器必须按 API 版本测试，并保留原始 dump 输出。

## 竞品包体积对比

“包有多大”至少对应四种对象：AAB（Android App Bundle，上传到应用商店的发布包）、单个 APK、某设备收到的 base + split APK 集合，以及压缩下载估算。先选定同一种对象再比：只拿竞品的 `base.apk` 对自家 universal APK（含多种设备资源的通用包），这种比较得不出有意义的结果。

### APK Analyzer 的使用

Android Studio 的 APK Analyzer 可以查看 APK 或 App Bundle 的压缩大小、下载大小估算、DEX、资源、assets（原样打包的资源文件）和 native libraries（C/C++ 等原生库）。使用竞品安装包前，先确认获取与分析符合渠道条款，并保存下载来源、版本、签名和文件哈希。

图形界面的基本流程如下：

1. 在 Android Studio 中选择 `Build → Analyze APK`，或者直接将 APK 文件拖入编辑器窗口。
2. 对每个文件同时记录 raw file size（文件本身大小）与 download size（传输压缩后的估算大小），两种数字别混用。
3. 展开 DEX、`resources.arsc`、`res/`、`assets/` 和 `lib/<abi>/`。
4. 使用 Compare with previous APK 比较同一个产品的相邻版本。

横向对比时，先为目标设备收集完整 split 集合，再按相同 ABI（CPU 指令集）、density、language 和动态功能模块计算；取不到完整集合时，报告写明缺哪些 split。

### 命令行工具 apkanalyzer

Android SDK Command-Line Tools 自带 `apkanalyzer`。下面的命令分别读取文件大小、下载大小估算、包内文件和两个 APK 的逐项差异：

```bash
apkanalyzer -h apk file-size app.apk
apkanalyzer -h apk download-size app.apk
apkanalyzer -h files list app.apk
apkanalyzer -h apk compare --different-only app-a.apk app-b.apk
```

`files list` 的当前官方语法没有 `--size` 选项，需要明细大小时用 `apk compare` 或 APK Analyzer 界面。`unzip -l ... | tail -1` 也不适合分类统计：glob、目录层级和压缩方式都会使汇总失真。

### 包体积对比的关键维度

**DEX**：大小受功能量、依赖、编译器、R8（Android 代码压缩与优化工具）配置、字符串、调试信息和压缩率共同影响。看到 DEX 大就断言代码质量差、或归因到 Kotlin/Java 的语言选择，都跳步了；它只说明上面某几项大。

**Native libraries**：按 ABI 和压缩状态拆分。AAB 交付通常只向设备发送匹配的 ABI；universal APK 则可能包含多套 `.so`。还要看调试符号是否剥离、库是否按内存页边界对齐，以及相同库是否在多个动态模块重复出现。

**Resources 与 `resources.arsc`**：分别检查图片、字体、音视频、密度/语言变体和资源表。位图改成矢量图可能减小文件，也可能增加运行时栅格化（把矢量图转换成像素）成本，要结合场景判断。

**Assets**：离线数据、Web bundle（Web 页面文件的打包集合）、模型和预置媒体常放在这里。Play Asset Delivery（Google Play 的大资源交付机制）或运行时下载的内容不在当前 APK 时，要在“首装下载”和“首次使用追加下载”中另行记录。

**交付大小**：用户关心某台设备实际要下载的压缩字节。`apkanalyzer apk download-size` 给的是估算值，和 Play Console 的交付统计对不上；报告里标明数据来源。

## 注意事项：避免误导性结论

### 误区一：只看单次数据就下结论

单次结果只是观察记录。重复采样后看差值分布和区间；样本再多，也救不回测试顺序、网络或热状态失控的轮次。报告用“在本实验条件下，A 的配对中位数比 B 低 X ms，区间为……”这类可核查的表述。

### 误区二：不同量级的场景放在一起比

Cold 与 Warm、首屏骨架与首屏数据、信息流滑动与静态设置页，别放进同一组。产品形态没有等价场景时，保留两个各自有意义的用户任务；为了凑排名制造虚假的一一对应，得不偿失。

### 误区三：忽略版本差异和编译状态

“最新版”仍可能因地区、灰度渠道和签名不同而对应多个构建。记录 versionCode 和安装包哈希，并确认测试期间没有自动更新。刚安装与长期使用的包，ART profile、磁盘数据、登录态和服务端分群都可能不同，归因别停在 JIT 上。

### 误区四：把设备差异当性能差异

同型号的两台设备，仍然是两台设备。每台设备分别做 A/B，再汇总“多少台设备上方向一致”。系统 OTA（整机系统在线更新）、Google Play system update（经 Google Play 分发的系统组件更新）和系统关键服务更新后，设备进入新的实验批次，旧结果只作历史参考。

### 误区五：忽略 SoC 平台差异的影响

SoC（System on Chip，系统级芯片）、GPU 驱动、内存、存储、厂商调度配置和散热结构共同影响结果。跨设备数据适合回答覆盖面问题；“设备甲上的 A”对“设备乙上的 B”这种比较做不得。性能模式、游戏模式和自适应刷新率也要作为设备配置保存。

### 误区六：把相关性写成实现原因

没有竞品源码时，Trace 能证明某线程、Binder 调用、GPU 或系统阶段占用了时间；再往产品设计动机上推，就超出证据范围了。包体积分类显示的是字节分布，DEX 大小同样推不出混淆质量。结论分成“观测”“候选原因”“验证办法”三列来写。

## 扩展：自动化竞品对比测试流水线

### 基本架构

1. **合规获取与归档**：保存来源、渠道、版本、签名、哈希和完整 split 清单；不绕过访问控制。
2. **设备调度**：校验 fingerprint、显示模式、电量、thermal status、网络和磁盘空间，异常设备退出本轮。
3. **状态准备**：按场景创建账号与数据，执行可验证的复位动作。
4. **随机执行**：按设备生成 A/B 顺序，设置超时、重试上限和失败分类。
5. **证据采集**：保存 `am start -W` 原始输出、Perfetto Trace、录屏、安装包分析和设备快照。
6. **统一计算**：从原始文件生成帧集合、分位数、配对差值和区间，分析代码与原始数据一起版本化。
7. **报告门禁**：缺版本、样本不足、状态不一致或 Trace 丢失时标记无效，不生成胜负结论。

Macrobenchmark 很适合自有应用的启动、滚动和动画基准，并自动输出 JSON 与 Perfetto Trace。官方要求目标包为 profileable，也就是 manifest 中允许 shell 读取详细 Trace；竞品的 manifest 我们改不了，多半过不了这条。这时用外部 UI Automator/adb 驱动加 shell Perfetto 采集，并接受可观测性较低的限制。同样地，`FrameMetrics` 也只能部署到我们改得到的应用里。

`dumpsys gfxinfo` 若作为兼容路径，流水线应按 Android API 版本选择解析器，并用固定样本验证字段。遇到未知格式直接失败，别静默填 0。

## 扩展：竞品功耗对比方法

功耗是系统级结果：屏幕、蜂窝信号、Wi-Fi、音频、传感器、温控和后台服务，任何一项的波动都可能盖过两个应用之间的差值。所以场景要固定持续时间、亮度、音量、网络响应、屏幕内容和用户输入，并交替执行 A/B。

### 软件测量方案

Battery Historian 已不再积极维护，但仍可把 batterystats 里的 wake lock（唤醒锁）、job、alarm、网络和进程状态放到时间线上，帮我们解释行为。注意它展示的是组件何时活跃；组件消耗了多少能量，还要另行测量。

下面的命令用于重置统计，并在执行场景后导出 bugreport（包含系统诊断信息的压缩包）：

```bash
adb shell dumpsys batterystats --reset
adb bugreport bugreport.zip
```

重置会影响全设备统计，需在专用测试机执行。bugreport 可能包含账号、网络与系统日志，归档前按团队安全规范处理。

AndroidX Macrobenchmark 的实验性 `PowerMetric` 可以读取 CPU、DISPLAY、GPU、MEMORY、NETWORK 等类别，但它测量**全系统**功耗/能量。官方截至 2026-08-14 仍把高精度采集限制在 Pixel 6、Pixel 6 Pro 及后续实体设备。它适合在支持设备上做受控场景比较；结果对应整个系统，分不出竞品进程独占的能量。

Android 17 平台的 Power Stats 入口可从 [`PowerStatsService.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/powerstats/PowerStatsService.java) 继续追到设备 HAL；具体可用的 channel（能量测量通道）和 consumer（逻辑耗能单元）由硬件实现决定。

### 硬件测量方案

外部电源分析仪需要设备支持的供电夹具或厂商测试接口，别在没有硬件规范的情况下直接断开电池。测量流程包括：

1. 校准采样率、电压与时间同步，确认设备不会同时从 USB 和仪器取电；
2. 在同一电压、屏幕和无线条件下记录空闲基线；
3. 用场景标记对齐每轮操作，保存原始电压与电流序列；
4. 对功率积分得到能量，使用 J、mJ、Wh 或 mWh 报告；
5. 按随机顺序重复 A/B，给出配对差值与区间。

`mAh`（毫安时）只表示电荷量，电压一变，同样的电荷对应的能量就不同。空闲基线相减也可能掩盖后台活动，原始总能量与基线修正值要同时保留。

## 参考资料

### 官方文档
- [App startup time](https://developer.android.com/topic/performance/vitals/launch-time) — 官方启动时间测量指南
- [Overview of measuring app performance](https://developer.android.com/topic/performance/measuring-performance) — 设备校准、编译状态与测量边界
- [APK Analyzer](https://developer.android.com/studio/debug/apk-analyzer) — APK 分析工具文档
- [apkanalyzer](https://developer.android.com/tools/apkanalyzer) — 命令行语法与大小口径
- [Benchmarking overview](https://developer.android.com/topic/performance/benchmarking/benchmarking-overview) — 性能基准测试框架
- [Macrobenchmark metrics](https://developer.android.com/topic/performance/benchmarking/macrobenchmark-metrics) — Startup、Frame 与 Power 指标
- [FrameMetrics API](https://developer.android.com/reference/android/view/FrameMetrics) — 帧性能测量 API
- [Reduce APK size](https://developer.android.com/topic/performance/reduce-apk-size) — APK 体积优化指南
- [Battery Historian](https://developer.android.com/topic/performance/power/battery-historian) — 电量分析工具

### AOSP 源码
- [`ActivityManagerShellCommand.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/am/ActivityManagerShellCommand.java) — Android 17 `am start -W` 调用与输出
- [`WaitResult.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/app/WaitResult.java) — Android 17 启动等待结果字段
- [`ActivityTaskSupervisor.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/wm/ActivityTaskSupervisor.java) — 等待与 `totalTime` 回填
- `frameworks/base/services/core/java/com/android/server/wm/ActivityMetricsLogger.java` — 启动 transition、`windowsDrawn` 与 `Displayed` 计时记录
- `frameworks/base/services/core/java/com/android/server/wm/ActivityRecord.java` — Activity 窗口绘制完成状态与启动等待结果
- `frameworks/base/core/java/android/view/FrameMetrics.java` — FrameMetrics API 定义
- [`FrameTimeline.cpp`](https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/services/surfaceflinger/Scheduler/FrameTimeline.cpp) — Android 17 SurfaceFlinger FrameTimeline

### 工具与平台
- [Perfetto](https://perfetto.dev/) — 系统级 Trace 分析平台（§14.1-§14.3 详细介绍）
- [Android Studio Profiler](https://developer.android.com/studio/profile) — 集成性能分析工具（§15.1 详细介绍）
