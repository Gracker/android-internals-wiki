---

title: "竞品分析方法"
chapter: "15.4"
section: "15.4"
status: finalized
drafted_date: "2026-04-04"
drafted_by: "openclaw-task2a"
applicable_versions: "Android 8.0 (API 26) - Android 17 (API 37)"
last_verified: "2026-07-30"
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
reviewed_by: openclaw-task6
reviewed_date: 2026-06-16
task6_result: pass-light-edit
last_task6_audit: "2026-07-02T14:05:00+08:00"
task9_result: auto-fixed
task9_reviewed_by: "openclaw-task9"
task9_reviewed_date: "2026-04-28"
last_task9_at: "2026-04-28T07:40:26+08:00"
task2b_result: fixed
last_task2b_at: "2026-04-27T21:44:26+08:00"
repaired_date: "2026-04-27"
repaired_by: "openclaw-task2b"
task9_review_notes: "2026-04-28 task9 deep-review: pass-tech-review。无 P0/P1；Task6 已通过且 queue 无 pending，自动晋升 finalized。P2 3 写入 suggestions。"
last_task9_audit: "2026-06-16"
last_task9_audit_log: "logs/deep-review/2026-06-16-18-audit.md"
task9_audit_notes: '2026-05-23 Task9 idle audit: 无 P0/P1。源码路径与 Android 16 FrameMetrics/ActivityTaskManager 链路复核通过；仅记录 P2：Benchmarking overview 官方 URL 已迁移。 | 2026-06-16 Task9 idle audit auto-fixed: P0 1（Battery Historian bugreport 导出命令修正为 adb bugreport bugreport.zip）/ P1 0 / P2 1（官方文档 URL 迁移修正）；回到 Task6 复审。'
deepseek_polish_state: done
last_deepseek_polish_at: "2026-05-25"
deepseek_cn_review_state: done
last_deepseek_cn_review_at: 2026-06-17
last_task9_autofix_at: "2026-06-16"
updated_by: "openclaw-task9"
updated_date: "2026-06-16"
last_task6_at: 2026-06-16T20:10:00+08:00
---

# 竞品分析方法

## 为什么要认真做竞品性能分析

竞品测试回答的是一个有边界的问题：

> 在指定设备、系统版本、应用版本、账号状态和操作路径下，两个应用的观测结果有多大差异？

它不能单独证明差异由哪段代码造成，也不能从一台设备推导全部用户的体验。测试报告若省略实验条件，一个启动耗时或卡顿率几乎无法复现，更无法用于版本决策。

平台源码锚点是 Android 17 / API 37 / `android-17.0.0_r1`。源码结论只用于解释 Android 平台计时和帧数据。竞品的业务实现不可见时，原因只能写成假设，并列出还缺少什么证据。当前结论不依赖 Linux 内核实现；若通过调度、频率或功耗事件解释差异，内核证据应固定到 `android17-6.18-2026-06_r6`。

## 竞品性能对比的方法论

一轮可复现的竞品测试至少包含四份记录：

1. **问题定义**：比较哪个用户场景、哪个指标、哪个时间窗口；
2. **实验清单**：设备、构建、应用版本、账号、数据集、网络、温度与编译状态；
3. **原始结果**：每次执行的顺序、成功或失败、指标值及对应 Trace；
4. **结论边界**：观察到了什么、尚未证明什么、下一步需要哪种证据。

### 控制变量的四项基本原则

**同设备**：A/B 应在同一台物理设备、同一用户和同一显示模式下成对执行。即使型号相同，芯片体质、存储老化和厂商配置也可能不同。需要覆盖多个档位时，每台设备独立形成一组结果，不把不同设备的样本混成一个分布。

**同场景**：使用用户可感知的起点、终点和成功条件。例如“从 Launcher 点击图标，到首个可操作 Feed 出现”仍需补充账号是否登录、缓存是否存在、广告是否展示、列表有多少项。两个产品的信息架构不同，不必强求页面名称相同，但工作量和用户目标要相近。

**同网络**：记录 Wi-Fi 或蜂窝网络、带宽、往返延迟、丢包、DNS、代理和服务端数据集。可控环境可以使用网络整形和固定响应；真实网络测试则应交替执行 A/B，并把网络时间单列。TLS 会话、CDN 命中和服务端负载无法靠“连接同一个 Wi-Fi”消除。

**同热状态**：记录电池温度、Thermal Service 状态和测试前的静置条件。不要连续测完 A 再测 B。可以使用 ABBA 或随机顺序，例如 A1、B1、B2、A2；一旦设备进入新的 thermal status，该轮作废并等待恢复。用户体验测试不应锁定 CPU 频率，因为固定频率会改变商用设备上的调度和温控行为。

### 测试前的设备准备

准备项要写进机器可读的 run manifest，避免依靠测试人员记忆：

- 设备序列号、型号、build fingerprint、API level、安全补丁和刷新率；
- App 的包名、versionName、versionCode、安装来源、签名摘要和 APK/split 摘要；
- 账号、地区、语言、主题、权限、实验开关和本地数据状态；
- 电量、充电状态、节电/性能模式、亮度、音量、屏幕方向和网络参数；
- ART 编译策略、Baseline/Cloud Profile 是否保留；
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

A/B 在同一设备、相近时间内成对执行。报告给出每轮原始值、配对差值、差值中位数、P90/P99 和置信区间。平均值、标准差仍可保留，但不能用“均值相差两倍标准差”代替显著性检验。若数据存在长尾，使用配对 bootstrap 区间或预先选定的非参数检验，并同时报告效应量。

## 竞品启动速度对比

启动至少有两个用户口径：

- **TTID（Time to Initial Display）**：应用首帧显示；
- **TTFD（Time to Full Display）**：应用主动调用 `reportFullyDrawn()` 报告内容可用。

TTFD 依赖应用正确埋点。无法确认竞品是否调用、调用位置是否等价时，不能横向比较 TTFD。

### adb am start -W 的原理与正确使用

Android 17 中，`ActivityManagerShellCommand` 看到 `-W` 后调用 `startActivityAndWait()`。目标 Activity 的窗口绘制完成时，`ActivityRecord#onWindowsDrawn()` 经 `ActivityMetricsLogger#notifyWindowsDrawn()` 得到 `windowsDrawnDelayMs`，再由 `ActivityTaskSupervisor#reportActivityLaunched()` 写入 `WaitResult.totalTime` 并唤醒等待者。

下面的命令用于确认一个**进程冷启动**样本。`-S` 会在启动前 force-stop 与 Intent 匹配的包，`-W` 会等待启动结果：

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
- **WaitTime**：`ActivityManagerShellCommand` 在调用前后用 uptime 计算的阻塞时间，包含 shell 发起、系统等待和返回路径。它适合诊断命令等待，不应替代 `TotalTime`。

旧版本曾输出 `ThisTime`，Android 17 的 [`WaitResult.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/app/WaitResult.java) 已无该字段，[`ActivityManagerShellCommand.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/am/ActivityManagerShellCommand.java) 也不再打印它。解析脚本应按目标系统版本识别字段，不能假定三时间值长期存在。

### 冷启动 vs 温启动 vs 热启动

- **Cold**：目标应用进程需要创建。文件缓存和应用数据可以仍在。
- **Warm**：进程可复用，但 Activity 需要创建。
- **Hot**：进程和 Activity 可复用，任务被带回前台。
- **Relaunch**：Android 17 还会报告 `RELAUNCH`，例如配置变化使已有 Activity 销毁重建。

测试脚本应让平台返回的 `LaunchState` 参与校验，少用“按了返回键所以一定是 warm”这类间接判断。一个竞品可能通过透明 Activity、深链路、多个进程或不同 task 策略进入首页，`TotalTime` 覆盖到哪个 Activity 取决于本次实际启动链。Perfetto 中的 Android App Startups 派生指标和 Activity transition 能补足这段时间线。

### 启动对比的注意事项

**SplashScreen**：Android 12 起的系统启动画面会早于应用首帧出现，但 `TotalTime` 的完成点仍来自目标 Activity 的窗口绘制。它不能表示页面数据可用。报告可以同时保留“启动画面出现”“应用首帧”“业务可操作”三个视觉时间点；后两者需要 Trace、视频或等价的 UI 状态检测。

**编译状态**：Play 安装可能带有 Baseline Profile，使用一段时间后还可能获得 JIT/Cloud Profile。竞品对比应选择并声明一种协议：

- **商店现实状态**：保留各自经商店分发和正常使用形成的编译状态，回答用户现实体验问题；
- **统一实验状态**：对所有包执行同一安装、交互和编译流程，回答固定 ART 条件下的差异。

以下命令会把整个包按 `speed` 模式编译，适合统一实验状态：

```bash
adb shell cmd package compile -m speed -f com.example.app
```

它会改变用户从 Play 安装后的自然状态，因此不能把结果称为商店体验。`speed-profile` 依赖设备上已有且质量相近的 profile；没有核验 profile 时，使用该模式反而会引入新的不一致。

**窗口与显示状态**：锁屏、分屏、画中画、外接显示器、刷新率切换和系统转场都会改变启动路径。每轮开始前校验，而非只在整个批次开始前设置一次。

## 竞品流畅性对比

平均 FPS 会隐藏停顿的位置与长度。竞品流畅性报告至少需要帧 deadline 命中情况、长尾帧、连续卡顿段、场景阶段和帧归属。加载占位、页面转场和稳定滑动应分段统计。

### 抓 Trace 对比帧耗时分布

Android 12 起，SurfaceFlinger FrameTimeline 能把应用产生帧和显示端帧关联起来。Android 17 的源码锚点是 [`FrameTimeline.cpp`](https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/services/surfaceflinger/Scheduler/FrameTimeline.cpp) 与 [`frame_timeline_event.proto`](https://android.googlesource.com/platform/external/perfetto/+/refs/tags/android-17.0.0_r1/protos/perfetto/trace/android/frame_timeline_event.proto)。

一次 Trace 需要包含：

- `android.surfaceflinger.frametimeline` 数据源；
- `linux.ftrace` 中与 View、input、window manager、graphics 相关的 atrace 分类；
- 目标包的 atrace events；
- 场景开始、结束和阶段切换标记。

Trace 时长应覆盖完整操作路径，没有通用的“至少 10 秒”。短动画可能只需数秒，长列表或视频场景可能需要一分钟。持续时间由场景定义决定，帧数与有效区间一并报告。

滑动可以由 UI Automator 或坐标事件驱动。坐标相同只保证输入相同，不能保证两个应用滚动距离或内容工作量相同；应再用可见 item、页面标识或录屏确认终点。`sendevent` 依赖设备节点和权限，不适合作为可移植方案。

### 帧耗时分析的关键指标

**deadline miss 率**：用每帧自己的 deadline 判断，不硬编码 60 Hz 的 16.6 ms 或 120 Hz 的 8.3 ms。可变刷新率、应用帧率投票和 SurfaceFlinger 调度会让相邻帧的预算不同。

**P50/P90/P99**：分位数描述主体与长尾，但必须说明统计的是应用帧实际时长、预期时长、超出 deadline 的时长，还是帧间隔。不同字段的 P99 不能直接比较。

**连续卡顿段**：记录同一交互中连续 miss 的帧数和持续时间。单个长帧与连续多个超时帧，即使落在相似的百分位，也会形成不同的视觉现象。

**归属**：FrameTimeline 的 App Jank、SurfaceFlinger Jank 和 jank type 是定位线索。它们不能单独证明业务代码、GPU 驱动或系统服务的责任，需要回到 UI thread、RenderThread、GPU 和 SurfaceFlinger 时间线寻找直接阻塞关系。

**有效帧集合**：标出首帧、窗口转场、无内容变化帧和测试脚本空等帧。排除规则必须在看数据之前设定，并对 A/B 使用同一规则。

### FrameMetrics 能做什么

`FrameMetrics` 从 API 24 提供 Window 帧分段数据，适合接入**自己控制的应用**。它无法注入未授权的竞品进程，所以不能作为任意竞品的线上采集方案。即使双方都接入了同类 APM，也要确认采样率、过滤规则、窗口范围和用户分群一致。

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

回调处理放到专用 HandlerThread，避免主线程上的采集逻辑干扰被测对象。`dropCountSinceLastInvocation` 表示监听器来不及接收的帧数，应连同数据上报，否则低估繁忙时段。API 26–30 的 `deadline == -1` 样本不能套用 deadline miss 判定。

Android 17 的 [`FrameMetrics.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/view/FrameMetrics.java) 定义 `TOTAL_DURATION = INTENDED_VSYNC → FRAME_COMPLETED`，`DEADLINE = INTENDED_VSYNC → FRAME_DEADLINE`。源码注释使用 `TOTAL_DURATION < DEADLINE` 表示按时完成。两者相等时不要判为命中。`FIRST_DRAW_FRAME` 通常应从动画卡顿统计中单列。

`dumpsys gfxinfo <package> framestats` 可以作为无侵入备选，但它主要反映 HWUI 窗口帧，输出字段随平台演进，覆盖面也不等同 FrameTimeline。解析器必须按 API 版本测试，并保留原始 dump。

## 竞品包体积对比

“包有多大”至少对应四种对象：AAB 上传文件、单个 APK、某设备收到的 base + split APK 集合，以及压缩下载估算。比较前要选择同一种对象。只拿竞品的 `base.apk` 与自家 universal APK 比较，结果没有意义。

### APK Analyzer 的使用

Android Studio 的 APK Analyzer 可以查看 APK 或 App Bundle 的压缩大小、下载大小估算、DEX、资源、assets 和 native libraries。使用竞品安装包前还要确认获取与分析符合渠道条款，并保存下载来源、版本、签名和文件哈希。

图形界面的基本流程如下：

1. 在 Android Studio 中选择 `Build → Analyze APK`，或者直接将 APK 文件拖入编辑器窗口。
2. 对每个文件记录 raw file size 与 download size，避免混用压缩前后数字。
3. 展开 DEX、`resources.arsc`、`res/`、`assets/` 和 `lib/<abi>/`。
4. 使用 Compare with previous APK 比较同一个产品的相邻版本。

横向对比时，先为目标设备收集完整 split 集合，再按相同 ABI、density、language 和动态功能模块计算。无法取得完整集合时，报告要写明缺少的 split。

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

**DEX**：大小受功能量、依赖、编译器、R8 配置、字符串、调试信息和压缩率共同影响。仅凭 DEX 较大，不能断言代码质量较差，也不能从 Kotlin/Java 语言选择直接归因。

**Native libraries**：按 ABI 和压缩状态拆分。AAB 交付通常只向设备发送匹配的 ABI；universal APK 则可能包含多套 `.so`。还要查看符号是否剥离、库是否按页对齐，以及相同库是否在多个动态模块重复出现。

**Resources 与 `resources.arsc`**：分别检查图片、字体、音视频、密度/语言变体和资源表。位图改为矢量图可能减小文件，也可能增加运行时栅格化成本，需结合场景判断。

**Assets**：离线数据、Web bundle、模型和预置媒体常放在这里。Play Asset Delivery 或运行时下载内容不在当前 APK 时，要在“首装下载”和“首次使用追加下载”中另行记录。

**交付大小**：用户关心某设备实际需要下载的压缩字节。`apkanalyzer apk download-size` 是估算值，不等于 Play Console 的交付统计；报告应标明来源。

## 注意事项：避免误导性结论

### 误区一：只看单次数据就下结论

单次结果只能作为观察记录。重复采样后仍需看差值分布和区间；样本多也不能补救测试顺序、网络或热状态失控。报告使用“在本实验条件下，A 的配对中位数比 B 低 X ms，区间为……”这类可核查表述。

### 误区二：不同量级的场景放在一起比

Cold 与 Warm、首屏骨架与首屏数据、信息流滑动与静态设置页不能放在同一组。若产品形态没有等价场景，应保留两个各自有意义的用户任务，避免为了得到排名而制造虚假的一一对应。

### 误区三：忽略版本差异和编译状态

“最新版”仍可能因地区、灰度渠道和签名不同而对应多个构建。记录 versionCode 和安装包哈希，并确认测试期间没有自动更新。刚安装与长期使用的包，其 ART profile、磁盘数据、登录态和服务端分群都可能不同，不能只归因于 JIT。

### 误区四：把设备差异当性能差异

同型号不等于同设备。每台设备分别做 A/B，再汇总“多少台设备上方向一致”。系统 OTA、Google Play system update 和核心服务更新后，设备进入新的实验批次，旧结果只保留为历史参考。

### 误区五：忽略 SoC 平台差异的影响

SoC、GPU 驱动、内存、存储、厂商调度配置和散热结构共同影响结果。跨设备数据适合回答覆盖面问题，不能用“设备甲上的 A”对“设备乙上的 B”。性能模式、游戏模式和自适应刷新率也要作为设备配置保存。

### 误区六：把相关性写成实现原因

没有竞品源码时，Trace 能证明某线程、Binder 调用、GPU 或系统阶段占用了时间，却不能直接证明其产品设计动机。包体积分类也只能显示字节分布，不能从 DEX 大小推断混淆质量。结论应分成“观测”“候选原因”“验证办法”三列。

## 扩展：自动化竞品对比测试流水线

### 基本架构

1. **合规获取与归档**：保存来源、渠道、版本、签名、哈希和完整 split 清单；不绕过访问控制。
2. **设备调度**：校验 fingerprint、显示模式、电量、thermal status、网络和磁盘空间，异常设备退出本轮。
3. **状态准备**：按场景创建账号与数据，执行可验证的复位动作。
4. **随机执行**：按设备生成 A/B 顺序，设置超时、重试上限和失败分类。
5. **证据采集**：保存 `am start -W` 原始输出、Perfetto Trace、录屏、安装包分析和设备快照。
6. **统一计算**：从原始文件生成帧集合、分位数、配对差值和区间，分析代码与原始数据一起版本化。
7. **报告门禁**：缺版本、样本不足、状态不一致或 Trace 丢失时标记无效，不生成胜负结论。

Macrobenchmark 很适合自有应用的启动、滚动和动画基准，并自动输出 JSON 与 Perfetto Trace。官方要求目标包可被 profile；无法修改的竞品往往不满足这一条件。此时使用外部 UI Automator/adb 驱动和 shell Perfetto 采集，同时接受可观测性较低的限制。`FrameMetrics` 也只能部署到可修改的应用。

`dumpsys gfxinfo` 若作为兼容路径，流水线应按 Android API 版本选择解析器，并用固定样本验证字段。遇到未知格式时直接失败，不能静默填 0。

## 扩展：竞品功耗对比方法

功耗是系统级结果。屏幕、蜂窝信号、Wi-Fi、音频、传感器、温控和后台服务都可能超过两个应用之间的差值。场景必须固定持续时间、亮度、音量、网络响应、屏幕内容和用户输入，并交替执行 A/B。

### 软件测量方案

Battery Historian 已不再积极维护。它仍可把 batterystats 中的 wake lock、job、alarm、网络和进程状态放到时间线上，用于解释行为；时间线展示组件何时活跃，不等于直接测得该组件消耗了多少能量。

下面的命令用于重置统计、执行场景后导出 bugreport：

```bash
adb shell dumpsys batterystats --reset
adb bugreport bugreport.zip
```

重置会影响全设备统计，需在专用测试机执行。bugreport 可能包含账号、网络与系统日志，归档前按团队安全规范处理。

AndroidX Macrobenchmark 的实验性 `PowerMetric` 可以读取 CPU、DISPLAY、GPU、MEMORY、NETWORK 等类别，但它测量**全系统**功耗/能量，官方当前限制为 Pixel 6、Pixel 6 Pro 及后续设备。它适合在支持设备上做受控场景比较，不能解释为竞品进程独占的能量。Android 17 平台的 Power Stats 入口可从 [`PowerStatsService.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/powerstats/PowerStatsService.java) 继续追到设备 HAL；具体可用 channel 和 consumer 由硬件实现决定。

### 硬件测量方案

外部电源分析仪需要设备支持的供电夹具或厂商测试接口，不应在没有硬件规范的情况下直接断开电池。测量流程包括：

1. 校准采样率、电压与时间同步，确认设备不会同时从 USB 和仪器取电；
2. 在同一电压、屏幕和无线条件下记录空闲基线；
3. 用场景标记对齐每轮操作，保存原始电压与电流序列；
4. 对功率积分得到能量，使用 J、mJ、Wh 或 mWh 报告；
5. 按随机顺序重复 A/B，给出配对差值与区间。

`mAh` 只表示电荷量；电压变化时不能直接等同能量。空闲基线相减也可能掩盖后台活动，原始总能量与基线修正值应同时保留。

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
