---

title: "竞品分析方法"
chapter: "15.4"
section: "15.4"
status: finalized
applicable_versions: "Android 8.0 (API 26) - Android 17 (API 37)"
last_verified: "2026-08-14"
last_verified_against: "AOSP android-17.0.0_r1 ActivityManagerShellCommand / WaitResult / ActivityTaskSupervisor / ActivityMetricsLogger / ActivityRecord / FrameMetrics / FrameTimeline; Android Developers current official documentation"
confidence: high
sources:
  - type: official
    path: "https://developer.android.com/topic/performance/vitals/launch-time"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/am/ActivityManagerShellCommand.java"
  - type: aosp
    path: "frameworks/base/core/java/android/app/WaitResult.java"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/wm/ActivityMetricsLogger.java"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/wm/ActivityRecord.java"
  - type: official
    path: "https://developer.android.com/studio/debug/apk-analyzer"
  - type: official
    path: "https://developer.android.com/topic/performance/benchmarking/benchmarking-overview"
  - type: official
    path: "https://developer.android.com/reference/android/view/FrameMetrics"
  - type: aosp
    path: "frameworks/base/core/java/android/view/FrameMetrics.java"
  - type: aosp
    path: "frameworks/native/services/surfaceflinger/Scheduler/FrameTimeline.cpp"
tags: ['competitive-analysis', 'benchmark', 'startup', 'fps', 'apk-size', 'methodology']
related_chapters: ["7.3", "8.3", "25.6", "13.2", "14.1", "15.3"]
pipeline_stage: ready-to-publish
task6_state: reviewed
task9_state: reviewed
task2b_state: fixed
---

# 竞品分析方法

## 为什么要认真做竞品性能分析

竞品测试回答的是一个有边界的问题：

> 在指定设备、系统版本、应用版本、账号状态和操作路径下，两个应用的观测结果有多大差异？

它不能单独证明差异由哪段代码造成，也不能从一台设备推导全部用户的体验。测试报告若省略实验条件，一个启动耗时或卡顿率几乎无法复现，更无法用于版本决策。

平台源码统一按 Android 17 / API 37 / `android-17.0.0_r1` 这个固定版本核对。源码结论只用于解释 Android 平台计时和帧数据。竞品的业务实现不可见时，原因只能写成假设，并列出还缺少什么证据。当前结论不依赖 Linux 内核实现；若通过调度、频率或功耗事件解释差异，内核证据应固定到 `android17-6.18-2026-06_r6`。

## 竞品性能对比的方法论

一轮可复现的竞品测试至少包含四份记录：

1. **问题定义**：比较哪个用户场景、哪个指标、哪个时间窗口；
2. **实验清单**：设备、构建、应用版本、账号、数据集、网络、温度与编译状态；
3. **原始结果**：每次执行的顺序、成功或失败、指标值及对应 Trace（系统时间线记录）；
4. **结论边界**：观察到了什么、尚未证明什么、下一步需要哪种证据。

### 控制变量的四项基本原则

**同设备**：A/B（在同一条件下交替测试应用 A 和 B）应在同一台物理设备、同一用户和同一显示模式下成对执行。即使型号相同，芯片个体差异、存储老化和厂商配置也可能不同。需要覆盖多个档位时，每台设备独立形成一组结果，不把不同设备的样本混成一个分布。

**同场景**：使用用户可感知的起点、终点和成功条件。例如“从 Launcher 点击图标，到首个可操作 Feed 出现”仍需补充账号是否登录、缓存是否存在、广告是否展示、列表有多少项。两个产品的信息架构不同，不必强求页面名称相同，但工作量和用户目标要相近。

**同网络**：记录 Wi-Fi 或蜂窝网络、带宽、往返延迟、丢包、DNS（域名解析）、代理和服务端数据集。可控环境可以使用网络整形和固定响应；真实网络测试则应交替执行 A/B，并把网络时间单列。TLS 会话（加密连接是否复用）、CDN 命中（内容是否来自边缘缓存）和服务端负载无法靠“连接同一个 Wi-Fi”消除。

**同热状态**：记录电池温度、Thermal Service（Android 热管理服务）状态和测试前的静置条件。不要连续测完 A 再测 B。可以使用 ABBA 交错顺序，例如 A1、B1、B2、A2，以减少时间漂移对单方结果的偏置；也可以预先随机顺序。一旦设备进入新的 thermal status（热状态等级），该轮作废并等待恢复。用户体验测试不应锁定 CPU 频率，因为固定频率会改变商用设备上的调度和温控行为。

### 测试前的设备准备

准备项要写进机器可读的 run manifest，也就是每轮测试随结果保存的配置清单，避免依靠测试人员记忆：

- 设备序列号、型号、build fingerprint（标识系统构建的完整字符串）、API level、安全补丁和刷新率；
- App 的包名、versionName、versionCode、安装来源、签名摘要，以及 APK 和 split APK（按设备配置拆分交付的安装包）文件摘要；
- 账号、地区、语言、主题、权限、实验开关和本地数据状态；
- 电量、充电状态、节电/性能模式、亮度、音量、屏幕方向和网络参数；
- ART（Android Runtime）编译策略，以及 Baseline Profile（随 App 发布的热点代码清单）和 Cloud Profile（Google Play 根据线上数据生成的热点代码清单）是否保留；
- 测试脚本版本、数据版本、执行时间和测试顺序。

`adb shell am kill-all` 只结束系统认为安全清理的后台进程，不能把设备恢复到一致状态。划掉最近任务也不保证进程退出。每个测试维度应有自己的复位动作：启动测试控制目标进程与任务，滑动测试恢复列表位置，网络测试恢复响应数据，功耗测试恢复电量和热状态。

系统动画是否关闭取决于问题定义。测 Activity 自身首帧时可以关闭；测用户看到的完整转场时必须保留，并固定动画缩放。两种结果不能混报。

### 采样、顺序与停止条件

固定“20 次”或“30 次”不是统计保证。场景波动、期望检测的差异和设备数量都会改变样本需求。建议先做小规模预采样，再在测试计划中固定以下内容：

- 每台设备的最少有效轮数；
- 单轮超时和失败判定；
- 因来电、更新、温控或网络失控而排除样本的规则；
- 最大轮数，或置信区间达到目标宽度时停止；
- 查看结果前已经确定的主指标。

A/B 在同一设备、相近时间内成对执行。报告给出每轮原始值、配对差值、差值中位数、P90/P99（90%/99% 的样本不高于该值）和置信区间。置信区间描述在既定统计方法下，真实差异的合理范围。平均值、标准差仍可保留，但不能用“均值相差两倍标准差”代替显著性检验。若数据存在长尾，可以使用配对 bootstrap（对 A/B 配对差值重复重采样）估计区间，或使用预先选定、不要求正态分布的非参数检验，并同时报告效应量，也就是差异本身有多大。

## 竞品启动速度对比

启动至少有两个用户口径：

- **TTID（Time to Initial Display，首次画面显示时间）**：应用首帧显示；
- **TTFD（Time to Full Display，完整画面显示时间）**：应用主动调用 `reportFullyDrawn()` 报告内容可用。

TTFD 依赖应用正确埋点。无法确认竞品是否调用、调用位置是否等价时，不能横向比较 TTFD。

### adb am start -W 的原理与正确使用

Android 17 中，`ActivityManagerShellCommand` 看到 `-W` 后调用 `startActivityAndWait()`。目标 Activity 的窗口绘制完成时，`ActivityRecord#onWindowsDrawn()` 经 `ActivityMetricsLogger#notifyWindowsDrawn()` 得到 `windowsDrawnDelayMs`，再由 `ActivityTaskSupervisor#reportActivityLaunched()` 写入 `WaitResult.totalTime` 并唤醒等待者。这条调用链说明 `TotalTime` 的终点来自窗口绘制事件。

下面的命令用于确认一个**进程冷启动**样本。Intent 是 Android 用来描述待执行操作及目标组件的消息；`-S` 会在启动前 force-stop（强制停止）Intent 匹配到的包，`-W` 会等待启动结果：

```bash
adb shell am start -S -W \
  -a android.intent.action.MAIN \
  -c android.intent.category.LAUNCHER \
  com.example.app/.MainActivity
```

这条命令不会清空文件页缓存、应用数据或服务端缓存。“冷”只描述进程在启动前不存在。若测试要求首次安装、首次登录或冷数据，必须另设场景，不能借 `-S` 推断。

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

输出读法以 Android 17 源码为准：

- **LaunchState**：`WaitResult` 明确区分 `COLD`、`WARM`、`HOT`、`RELAUNCH`。报告必须保存这个字段；预期为 COLD 却得到其他状态时，该轮无效。
- **TotalTime**：Activity 启动跟踪开始到目标窗口完成首轮绘制的延迟。它接近 TTID 的系统口径，不表示网络数据齐备或页面可以完成业务操作。
- **WaitTime**：`ActivityManagerShellCommand` 在调用前后用 uptime（设备开机后的运行时间，深度休眠时不增长）计算阻塞时间，包含 shell 发起、系统等待和返回路径。它适合诊断命令等待，不应替代 `TotalTime`。

旧版本曾输出 `ThisTime`，Android 17 的 [`WaitResult.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/app/WaitResult.java) 已无该字段，[`ActivityManagerShellCommand.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/am/ActivityManagerShellCommand.java) 也不再打印它。解析脚本应按目标系统版本识别字段，不能假定三时间值长期存在。

### 冷启动 vs 温启动 vs 热启动

下面四项解释的是 Android 17 `am start -W` 返回的 `LaunchState`。它按进程是否运行、Activity 是否新建来分类，范围比用户层面的通用启动定义更窄；报告应注明采用哪套口径。

- **Cold**：目标应用进程需要创建。文件缓存和应用数据可以仍在。
- **Warm**：进程可复用，但 Activity 需要创建。
- **Hot**：进程和 Activity 可复用，任务被带回前台。
- **Relaunch**：Android 17 还会报告 `RELAUNCH`，例如配置变化使已有 Activity 销毁重建。

测试脚本应让平台返回的 `LaunchState` 参与校验，少用“按了返回键所以一定是 warm”这类间接判断。一个竞品可能通过透明 Activity、deep link（直接进入指定页面的链接）、多个进程或不同 task（Activity 任务栈）策略进入首页，`TotalTime` 覆盖到哪个 Activity 取决于本次实际启动链。Perfetto 中的 Android App Startups 派生指标（由原始 Trace 计算出的启动区间）和 Activity transition（页面切换过程）能补足这段时间线。

### 启动对比的注意事项

**SplashScreen**：Android 12 起的系统启动画面会早于应用首帧出现，但 `TotalTime` 的完成点仍来自目标 Activity 的窗口绘制。它不能表示页面数据可用。报告可以同时保留“启动画面出现”“应用首帧”“业务可操作”三个视觉时间点；后两者需要 Trace、视频或等价的 UI 状态检测。

**编译状态**：Play 安装可能带有 Baseline Profile，使用一段时间后还可能获得 JIT（Just-In-Time，运行时即时编译）或 Cloud Profile。竞品对比应选择并声明一种协议：

- **商店现实状态**：保留各自经商店分发和正常使用形成的编译状态，回答用户现实体验问题；
- **统一实验状态**：对所有包执行同一安装、交互和编译流程，回答固定 ART 条件下的差异。

以下命令会把整个包按 `speed` 模式做预编译，适合统一实验状态：

```bash
adb shell cmd package compile -m speed -f com.example.app
```

它会改变用户从 Play 安装后的自然状态，因此不能把结果称为商店体验。`speed-profile` 只按设备已有的 profile 预编译热点代码；没有核验各 App 的 profile 是否存在且质量相近时，使用该模式会引入新的不一致。

**窗口与显示状态**：锁屏、分屏、画中画、外接显示器、刷新率切换和系统转场都会改变启动路径。每轮开始前校验，而非只在整个批次开始前设置一次。

## 竞品流畅性对比

平均 FPS（Frames Per Second，每秒帧数）会隐藏停顿的位置与长度。竞品流畅性报告至少需要帧 deadline（平台为每帧分配的完成时限）命中情况、长尾帧、连续卡顿段、场景阶段和帧归属。加载中的临时界面、页面转场和稳定滑动应分段统计。

### 抓 Trace 对比帧耗时分布

Android 12 起，SurfaceFlinger（负责图层合成与呈现的系统服务）的 FrameTimeline 能把 App 产生的帧和显示端呈现的帧关联起来。Android 17 的固定源码版本可查 [`FrameTimeline.cpp`](https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/services/surfaceflinger/Scheduler/FrameTimeline.cpp) 与 [`frame_timeline_event.proto`](https://android.googlesource.com/platform/external/perfetto/+/refs/tags/android-17.0.0_r1/protos/perfetto/trace/android/frame_timeline_event.proto)。

一次 Trace 需要包含：

- `android.surfaceflinger.frametimeline` 数据源；
- `linux.ftrace`（内核事件 Trace 数据源）中与 View、input、window manager、graphics 相关的 atrace 分类；
- 目标包的 atrace events，也就是 App 通过 Android Trace 标记写入的事件；
- 场景开始、结束和阶段切换标记。

Trace 时长应覆盖完整操作路径，没有通用的“至少 10 秒”。短动画可能只需数秒，长列表或视频场景可能需要一分钟。持续时间由场景定义决定，帧数与有效区间一并报告。

滑动可以由 UI Automator（可跨 App 操作界面的自动化测试框架）或坐标事件驱动。坐标相同只保证输入相同，不能保证两个应用滚动距离或内容工作量相同；应再用可见 item、页面标识或录屏确认终点。`sendevent` 是向 Linux 输入设备节点写事件的低层命令，依赖设备节点和权限，不适合作为可移植方案。

### 帧耗时分析的关键指标

**deadline miss 率**：表示未按时完成的帧占比，应使用每帧自己的 deadline 判断，不硬编码 60 Hz 的 16.6 ms 或 120 Hz 的 8.3 ms。可变刷新率、App 对期望帧率的投票和 SurfaceFlinger 调度会让相邻帧的预算不同。

**P50/P90/P99**：分位数描述主体与长尾，但必须说明统计的是应用帧实际时长、预期时长、超出 deadline 的时长，还是帧间隔。不同字段的 P99 不能直接比较。

**连续卡顿段**：记录同一交互中连续 miss 的帧数和持续时间。单个长帧与连续多个超时帧，即使落在相似的百分位，也会形成不同的视觉现象。

**归属**：FrameTimeline 的 App Jank、SurfaceFlinger Jank 和 jank type（平台标记的卡顿来源类型）是定位线索。它们不能单独证明业务代码、GPU 驱动或系统服务的责任，需要回到 UI thread（处理界面事件与布局绘制的主线程）、RenderThread（承担部分渲染工作的线程）、GPU 和 SurfaceFlinger 时间线寻找直接阻塞关系。

**有效帧集合**：标出首帧、窗口转场、无内容变化帧和测试脚本空等帧。排除规则必须在看数据之前设定，并对 A/B 使用同一规则。

### FrameMetrics 能做什么

`FrameMetrics` 从 API 24 提供 `Window` 帧的分阶段耗时，适合接入**自己控制的应用**。它无法注入未授权的竞品进程，所以不能作为任意竞品的线上采集方案。即使双方都接入了同类 APM（Application Performance Monitoring，应用性能监控）系统，也要确认采样率、过滤规则、窗口范围和用户分群一致。

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

回调处理放到专用 `HandlerThread`（带消息循环的后台线程），避免主线程上的采集逻辑干扰被测对象。`dropCountSinceLastInvocation` 表示监听器来不及接收的帧数，应连同数据上报，否则低估繁忙时段。API 26–30 的 `deadline == -1` 样本不能套用 deadline miss 判定。

Android 17 的 [`FrameMetrics.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/view/FrameMetrics.java) 定义 `TOTAL_DURATION = INTENDED_VSYNC → FRAME_COMPLETED`，`DEADLINE = INTENDED_VSYNC → FRAME_DEADLINE`。源码注释使用 `TOTAL_DURATION < DEADLINE` 表示按时完成。两者相等时不要判为命中。`FIRST_DRAW_FRAME` 通常应从动画卡顿统计中单列。

`dumpsys gfxinfo <package> framestats` 可以作为无侵入备选，但它主要反映 HWUI（Android 硬件加速界面渲染管线）窗口帧，输出字段随平台演进，覆盖面也不等同 FrameTimeline。解析器必须按 API 版本测试，并保留原始 dump（命令原始输出）。

## 竞品包体积对比

“包有多大”至少对应四种对象：AAB（Android App Bundle，上传到应用商店的发布包）、单个 APK、某设备收到的 base + split APK（基础包与按设备配置拆分的安装包）集合，以及压缩下载估算。比较前要选择同一种对象。只拿竞品的 `base.apk` 与自家 universal APK（包含多种设备资源的通用安装包）比较，结果没有意义。

### APK Analyzer 的使用

Android Studio 的 APK Analyzer 可以查看 APK 或 App Bundle 的压缩大小、下载大小估算、DEX（Android 字节码文件）、资源、assets（原样打包的资源文件）和 native libraries（C/C++ 等原生库）。使用竞品安装包前还要确认获取与分析符合渠道条款，并保存下载来源、版本、签名和文件哈希。

图形界面的基本流程如下：

1. 在 Android Studio 中选择 `Build → Analyze APK`，或者直接将 APK 文件拖入编辑器窗口。
2. 对每个文件记录 raw file size（文件本身大小）与 download size（传输压缩后的估算大小），避免混用两种数字。
3. 展开 DEX、`resources.arsc`、`res/`、`assets/` 和 `lib/<abi>/`。
4. 使用 Compare with previous APK 比较同一个产品的相邻版本。

横向对比时，先为目标设备收集完整 split 集合，再按相同 ABI（CPU 指令集）、density（屏幕密度）、language（语言资源）和动态功能模块计算。无法取得完整集合时，报告要写明缺少的 split。

### 命令行工具 apkanalyzer

Android SDK Command-Line Tools 自带 `apkanalyzer`。下面的命令分别读取文件大小、下载大小估算、包内文件和两个 APK 的逐项差异：

```bash
apkanalyzer -h apk file-size app.apk
apkanalyzer -h apk download-size app.apk
apkanalyzer -h files list app.apk
apkanalyzer -h apk compare --different-only app-a.apk app-b.apk
```

`files list` 的当前官方语法没有 `--size` 选项；需要明细大小时使用 `apk compare` 或 APK Analyzer 界面。`unzip -l ... | tail -1` 也不适合分类统计：glob、目录层级和压缩方式都会使汇总失真。

### 包体积对比的关键维度

**DEX**：大小受功能量、依赖、编译器、R8（Android 代码压缩与优化工具）配置、字符串、调试信息和压缩率共同影响。仅凭 DEX 较大，不能断言代码质量较差，也不能从 Kotlin/Java 语言选择直接归因。

**Native libraries**：按 ABI 和压缩状态拆分。AAB 交付通常只向设备发送匹配的 ABI；universal APK 则可能包含多套 `.so`。还要查看调试符号是否剥离、库是否按内存页边界对齐，以及相同库是否在多个动态模块重复出现。

**Resources 与 `resources.arsc`**：分别检查图片、字体、音视频、密度/语言变体和资源表。位图改为矢量图可能减小文件，也可能增加运行时栅格化（把矢量图转换成像素）成本，需结合场景判断。

**Assets**：离线数据、Web bundle（Web 页面所需文件的打包集合）、模型和预置媒体常放在这里。Play Asset Delivery（Google Play 的大资源交付机制）或运行时下载内容不在当前 APK 时，要在“首装下载”和“首次使用追加下载”中另行记录。

**交付大小**：用户关心某设备实际需要下载的压缩字节。`apkanalyzer apk download-size` 是估算值，不等于 Play Console 的交付统计；报告应标明来源。

## 注意事项：避免误导性结论

### 误区一：只看单次数据就下结论

单次结果只能作为观察记录。重复采样后仍需看差值分布和区间；样本多也不能补救测试顺序、网络或热状态失控。报告使用“在本实验条件下，A 的配对中位数比 B 低 X ms，区间为……”这类可核查表述。

### 误区二：不同量级的场景放在一起比

Cold 与 Warm、首屏骨架与首屏数据、信息流滑动与静态设置页不能放在同一组。若产品形态没有等价场景，应保留两个各自有意义的用户任务，避免为了得到排名而制造虚假的一一对应。

### 误区三：忽略版本差异和编译状态

“最新版”仍可能因地区、灰度渠道和签名不同而对应多个构建。记录 versionCode 和安装包哈希，并确认测试期间没有自动更新。刚安装与长期使用的包，其 ART profile、磁盘数据、登录态和服务端分群都可能不同，不能只归因于 JIT。

### 误区四：把设备差异当性能差异

同型号不等于同设备。每台设备分别做 A/B，再汇总“多少台设备上方向一致”。系统 OTA（整机系统在线更新）、Google Play system update（通过 Google Play 分发的系统组件更新）和系统关键服务更新后，设备进入新的实验批次，旧结果只保留为历史参考。

### 误区五：忽略 SoC 平台差异的影响

SoC（System on Chip，系统级芯片）、GPU 驱动、内存、存储、厂商调度配置和散热结构共同影响结果。跨设备数据适合回答覆盖面问题，不能用“设备甲上的 A”对“设备乙上的 B”。性能模式、游戏模式和自适应刷新率也要作为设备配置保存。

### 误区六：把相关性写成实现原因

没有竞品源码时，Trace 能证明某线程、Binder（Android 跨进程调用机制）调用、GPU 或系统阶段占用了时间，却不能直接证明其产品设计动机。包体积分类也只能显示字节分布，不能从 DEX 大小推断混淆质量。结论应分成“观测”“候选原因”“验证办法”三列。

## 扩展：自动化竞品对比测试流水线

### 基本架构

1. **合规获取与归档**：保存来源、渠道、版本、签名、哈希和完整 split 清单；不绕过访问控制。
2. **设备调度**：校验 fingerprint、显示模式、电量、thermal status、网络和磁盘空间，异常设备退出本轮。
3. **状态准备**：按场景创建账号与数据，执行可验证的复位动作。
4. **随机执行**：按设备生成 A/B 顺序，设置超时、重试上限和失败分类。
5. **证据采集**：保存 `am start -W` 原始输出、Perfetto Trace、录屏、安装包分析和设备快照。
6. **统一计算**：从原始文件生成帧集合、分位数、配对差值和区间，分析代码与原始数据一起版本化。
7. **报告门禁**：缺版本、样本不足、状态不一致或 Trace 丢失时标记无效，不生成胜负结论。

Macrobenchmark 很适合自有应用的启动、滚动和动画基准，并自动输出 JSON 与 Perfetto Trace。官方要求目标包为 profileable，也就是在 manifest 中允许 shell 读取详细 Trace；无法修改的竞品往往不满足这一条件。此时使用外部 UI Automator/adb 驱动和 shell Perfetto 采集，同时接受可观测性较低的限制。`FrameMetrics` 也只能部署到可修改的应用。

`dumpsys gfxinfo` 若作为兼容路径，流水线应按 Android API 版本选择解析器，并用固定样本验证字段。遇到未知格式时直接失败，不能静默填 0。

## 扩展：竞品功耗对比方法

功耗是系统级结果。屏幕、蜂窝信号、Wi-Fi、音频、传感器、温控和后台服务都可能超过两个应用之间的差值。场景必须固定持续时间、亮度、音量、网络响应、屏幕内容和用户输入，并交替执行 A/B。

### 软件测量方案

Battery Historian 已不再积极维护。它仍可把 batterystats（Android 系统累计的电池使用统计）中的 wake lock（保持 CPU 或屏幕运行的唤醒锁）、job（系统调度任务）、alarm（定时唤醒事件）、网络和进程状态放到时间线上，用于解释行为；时间线展示组件何时活跃，不等于直接测得该组件消耗了多少能量。

下面的命令用于重置统计，并在执行场景后导出 bugreport（包含系统诊断信息的压缩包）：

```bash
adb shell dumpsys batterystats --reset
adb bugreport bugreport.zip
```

重置会影响全设备统计，需在专用测试机执行。bugreport 可能包含账号、网络与系统日志，归档前按团队安全规范处理。

AndroidX Macrobenchmark 的实验性 `PowerMetric` 可以读取 CPU、DISPLAY、GPU、MEMORY、NETWORK 等类别，但它测量**全系统**功耗/能量。官方截至 2026-08-14 仍把高精度采集限制在 Pixel 6、Pixel 6 Pro 及后续实体设备。它适合在支持设备上做受控场景比较，不能解释为竞品进程独占的能量。Android 17 平台的 Power Stats 入口可从 [`PowerStatsService.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/powerstats/PowerStatsService.java) 继续追到设备 HAL（Hardware Abstraction Layer，硬件抽象层）；具体可用 channel（能量测量通道）和 consumer（逻辑耗能单元）由硬件实现决定。

### 硬件测量方案

外部电源分析仪需要设备支持的供电夹具或厂商测试接口，不应在没有硬件规范的情况下直接断开电池。测量流程包括：

1. 校准采样率、电压与时间同步，确认设备不会同时从 USB 和仪器取电；
2. 在同一电压、屏幕和无线条件下记录空闲基线；
3. 用场景标记对齐每轮操作，保存原始电压与电流序列；
4. 对功率积分得到能量，使用 J、mJ、Wh 或 mWh 报告；
5. 按随机顺序重复 A/B，给出配对差值与区间。

`mAh`（毫安时）只表示电荷量；电压变化时不能直接等同能量。空闲基线相减也可能掩盖后台活动，原始总能量与基线修正值应同时保留。

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
- [Perfetto](https://perfetto.dev/) — 系统级 Trace 分析平台（§13.2-§13.5 详细介绍）
- [Android Studio Profiler](https://developer.android.com/studio/profile) — 集成性能分析工具（§14.1 详细介绍）
