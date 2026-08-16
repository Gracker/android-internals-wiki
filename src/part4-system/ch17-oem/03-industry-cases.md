---
title: "OEM 与大型应用协作案例"
chapter: "17.3"
section: "17.3"
applicable_versions: "Android 12 (API 31) - Android 17 (API 37)"
last_verified: "2026-08-14"
last_verified_against: "Android 17 AOSP, AndroidX androidx-main, Android Developers Game Mode/ADPF 文档, Samsung Game Booster/SceneSDK, Android Developers Blog TikTok case study"
confidence: medium
sources:
  - type: official
    path: "https://developer.android.com/games/optimize/adpf/gamemode/about-API-and-interventions"
  - type: official
    path: "https://developer.android.com/games/optimize/adpf/gamemode/gamemode-interventions"
  - type: official
    path: "https://developer.android.com/games/optimize/adpf/gamemode/fps-throttling"
  - type: official
    path: "https://developer.android.com/games/optimize/adpf/gamemode/gamemode-api"
  - type: official
    path: "https://developer.android.com/topic/performance/adpf"
  - type: official
    path: "https://developer.android.com/games/optimize/adpf"
  - type: official
    path: "https://developer.android.com/games/optimize/adpf/gamemode/gamestate-api"
  - type: official
    path: "https://developer.android.com/reference/android/os/PowerManager"
  - type: official
    path: "https://developer.android.com/reference/android/os/PerformanceHintManager"
  - type: official
    path: "https://developer.android.com/reference/android/os/PerformanceHintManager.Session"
  - type: official
    path: "https://developer.android.com/topic/libraries/app-startup"
  - type: official
    path: "https://developer.android.com/topic/performance/benchmarking/macrobenchmark-overview"
  - type: official
    path: "https://developer.android.com/develop/ui/compose/layouts/adaptive/foldables/learn-about-foldables"
  - type: official
    path: "https://www.samsung.com/levant/support/apps-services/know-more-about-the-game-booster-app/"
  - type: official
    path: "https://developer.samsung.com/galaxy-gamedev/blog/en/2022/04/26/accelerate-game-performance-based-on-scenesdk"
  - type: official
    path: "https://android-developers.googleblog.com/2022/08/precise-improvements-how-tiktok-enhanced-its-social-experience-on-android.html"
  - type: blog
    path: "Cubox/抖音 Android 性能优化系列：启动优化实践 - 掘金-2024-01-15.md"
  - type: blog
    path: "Cubox/抖音 Android 性能优化系列：新一代全能型性能分析工具 Rhea-2022-01-13.md"
  - type: repository
    path: "https://github.com/bytedance/btrace"
  - type: official
    path: "https://android-developers.googleblog.com/2026/07/build-intelligent-android-apps-cloud-and-hybrid-inference.html"
  - type: official
    path: "https://developer.android.com/jetpack/androidx/releases/window"
  - type: source
    path: "https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/app/GameManager.java"
  - type: source
    path: "https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/os/PerformanceHintManager.java"
  - type: source
    path: "https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/os/PowerManager.java"
  - type: source
    path: "https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/app/ActivityThread.java"
  - type: source
    path: "https://android.googlesource.com/platform/frameworks/support/+/refs/heads/androidx-main/core/core/src/main/java/androidx/core/content/FileProvider.java"
tags: ['case-study', 'game-mode', 'adpf', 'startup', 'foldable', 'oem', 'industry']
related_chapters: ["5.6", "7.4", "7.5", "8.2", "8.3", "11.1", "16.1", "17.1", "17.2"]
task6_state: reviewed
status: finalized
pipeline_stage: finalized
task9_state: reviewed
task2b_state: fixed
last_body_apply_at: "2026-08-06T09:15:33+08:00"
last_body_apply_run_id: "20260806-091503-909828fa"
last_review_finalize_at: "2026-08-06T10:06:06+08:00"
last_review_finalize_run_id: "20260806-100508-973d0b7e"
---

# OEM 与大型应用协作案例

## 案例能证明到哪一层

行业案例记录的是特定应用、设备、版本和实验条件下的结果。它适合解释团队如何缩小问题、如何选择指标，也容易被误读成跨设备规律。

阅读一份案例时，可以把内容拆成四列：

| 层次 | 要回答的问题 | 常见证据 |
| --- | --- | --- |
| 公开事实 | 团队公开做了什么、报告了什么结果 | 官方博客、演讲、源码、API 文档 |
| 机制解释 | 为什么这些动作可能影响指标 | AOSP、AndroidX、内核、图形或媒体源码 |
| 设备实现 | OEM（设备厂商）如何响应提示、配置频率或温控 | 设备厂商文档、设备配置、厂商 trace |
| 本地复现 | 在自己的应用和设备上是否成立 | Perfetto、Macrobenchmark、计数器、A/B 对照实验（两组只改一个变量） |

公开案例给出的百分比只能保留在原案例的分母里。没有设备分布、样本数、统计区间和版本信息时，不能把它改写成项目排期或行业基准。

本文核对 API 时以 Android 17（API 37）和 AOSP `android-17.0.0_r1` 为准。旧案例保留其历史背景，API 语义与建议按 Android 17 重新检查。

## Samsung：用户模式与合作接口是两条路径

Samsung 的公开材料提供了一个边界清楚的 OEM 案例。

Samsung 支持页把 Game Booster 描述为游戏运行时自动启动的用户功能，并说明它会在电量、性能和温度之间做平衡。该页面没有公开 CPU 调频器（governor）、利用率钳制（uclamp，给调度器利用率设上下界）、GPU 驱动参数或温控阈值，因此不能仅凭 Game Booster 的界面选项推断某个固定的内核动作。

Samsung 2022 年的 SceneSDK 文章描述了另一条合作路径：游戏把 loading（加载）、lobby（大厅）、gameplay（对局）等场景信息交给设备侧服务，服务可按场景调整 CPU / GPU 频率；设备降频时，也可把通知发回游戏。文章还描述了按目标帧率调整显示刷新率的合作方式。

SceneSDK 不属于 Android SDK 的公共 API。文章里的 JSON（机器可读的结构化文本）协议、支持范围和策略来自当时的 Samsung 合作环境，不能假设所有 Galaxy 设备或所有应用都能调用。它展示的是一种双向协作方式：

- 应用提供比 CPU 利用率更早的场景和目标帧率信息；
- 设备提供温控、频率变化和资源约束信息；
- 应用收到约束后降低可调整的负载，设备按场景分配资源；
- 双方用帧时间、功耗和热稳态验证结果。这里的热稳态指设备温度和运行频率不再持续漂移的阶段。

在一台 Galaxy 设备上验证 Game Booster 或 SceneSDK 类策略，应同时记录场景标记、CPU / GPU 频率、FrameTimeline（Android 帧生命周期轨道）、温控状态、显示刷新率和电源模式。只有界面上的模式名称而没有运行数据，无法证明调度器或驱动执行了什么动作。

这套分层也适用于其他 OEM 的游戏入口。厂商公开页能证明用户有哪些选项；绑核（把线程限制到指定 CPU 核）、频率投票（子系统向调频策略提交性能需求）和驱动策略仍需对应机型、系统版本和 Perfetto trace（性能跟踪记录）。

## Game Mode：用户选择、应用适配与厂商干预

Android Game Mode 有三个容易混淆的角色：

1. **用户选择**：Standard（标准）、Performance（性能）、Battery Saver（省电），以及 Android 14 引入的 Custom（自定义）。
2. **应用适配**：游戏读取 `GameManager.getGameMode()`，调整自己的分辨率、画质、帧率或后台工作。
3. **厂商干预**：OEM intervention 指系统或设备厂商不修改游戏代码便能应用的配置，包括 backbuffer resize（后缓冲区缩放）、ANGLE 和 FPS throttling（帧率限制）。ANGLE 是图形兼容层，可把 OpenGL ES 调用转到另一种图形后端。

Android Developers 文档称，Game Mode API 与厂商干预可用于部分 Android 12 设备以及 Android 13 及以上设备。`getGameMode()` 仍可能返回 `GAME_MODE_UNSUPPORTED`，应用必须准备默认策略。

Android 17 的 `GameManager.java` 还保留 Custom 的兼容处理：当模式为 `GAME_MODE_CUSTOM`，而应用 `targetSdkVersion` 不高于 Android 13 时，`getGameMode()` 返回 Standard。游戏应在 Activity 每次进入 `onResume()` 时重新读取模式，未知值走安全分支。

下面的配置用于声明游戏自行处理 Performance 与 Battery 模式：

```xml
<!-- AndroidManifest.xml 的 <application> 内 -->
<meta-data
    android:name="android.game_mode_config"
    android:resource="@xml/game_mode_config" />

<!-- res/xml/game_mode_config.xml -->
<game-mode-config
    xmlns:android="http://schemas.android.com/apk/res/android"
    android:supportsBatteryGameMode="true"
    android:supportsPerformanceGameMode="true" />
```

声明 `supports*GameMode="true"` 后，游戏要实现对应策略，平台会清除此前对该模式应用的 OEM 干预。`allowGameDownscaling` 和 `allowGameFpsOverride` 是两项独立的退出开关（opt-out），分别控制画面降分辨率和帧率覆盖，不能用 `supports*` 属性代替。

### 厂商干预的测量边界

WindowManager 的 backbuffer resize 会改变游戏后缓冲区尺寸，再由系统缩放到显示尺寸；它可能降低 GPU 的像素处理量，也会影响清晰度。FPS throttling 从 Android 13 起可用，目标是让帧率更稳定并减少功耗。ANGLE 干预会改变 GLES 的实现路径，结果受着色器、图形驱动和设备支持情况影响。

对比有无厂商干预时，应固定：

- 同一 APK、关卡、画质、输入脚本和网络数据；
- 分辨率、显示刷新率、目标帧率和电源模式；
- 冷机起点、预热时长、环境温度和运行轮次；
- TTFF（Time to First Frame，首帧时间）、P50 / P95 帧时间（第 50 / 95 百分位）、未赶上显示截止点的帧数（deadline miss）、GPU 忙碌时间、功耗和温控状态。

Android 文档里的节能或 GPU 降幅属于文档给定设备与条件下的示例，不应写入本项目的验收门槛。

## ADPF：用反馈调节负载与温控余量

ADPF（Android Dynamic Performance Framework，Android 动态性能框架）让应用把工作目标和运行状态告诉系统，也让应用读取温控信号。它提供的是反馈信号，不是锁定 CPU 或 GPU 频率的接口。

### Thermal API（温控 API）

`PowerManager.getThermalHeadroom(int)` 从 API 30 提供，参数范围为 0～60 秒。它返回无单位的当前或预测温控压力值，下文简称 headroom；这个值不是摄氏温度，`1.0` 对应 `THERMAL_STATUS_SEVERE` 阈值，数值也可以大于 `1.0`。设备不支持时返回 `NaN`；调用明显快于每秒一次也可能得到 `NaN`。

`getThermalHeadroomThresholds()` 从 API 35 提供，返回设备为温控状态定义的 headroom 阈值映射表；设备没有定义的状态不一定出现在表中。调用可能抛出 `UnsupportedOperationException` 或 `IllegalStateException`。从 API 36 开始，这份映射表可能在运行时变化；Android 17 应用可以使用 `addThermalHeadroomListener()` 接收 headroom 与阈值更新。

下面的代码用于 Android 12～17 共用模块以较低频率采样，并为 API 35 以下设备保留 `SEVERE == 1.0f` 的定义：

```kotlin
data class ThermalSample(
    val headroom: Float,
    val severeThreshold: Float,
)

fun sampleThermalBudget(powerManager: PowerManager): ThermalSample? {
    val headroom = powerManager.getThermalHeadroom(10)
    if (headroom.isNaN()) return null

    val severeThreshold =
        if (Build.VERSION.SDK_INT >= 35) {
            runCatching {
                powerManager.thermalHeadroomThresholds[
                    PowerManager.THERMAL_STATUS_SEVERE
                ]
            }.getOrNull() ?: 1.0f
        } else {
            1.0f
        }

    return ThermalSample(headroom, severeThreshold)
}
```

这段代码只读取信号，不规定降级幅度。调用方应以秒级节奏运行，并给画质或帧率切换加入滞回控制（降低负载与恢复负载使用不同阈值）和最短保持时间，避免 headroom 在阈值附近波动时频繁切档。返回 `null` 时使用保守的默认策略，并记录设备信息。

温控策略要验证三个时间关系：headroom 何时接近阈值、应用何时降低负载、帧时间与频率何时稳定。只看温度值或平均 FPS，都不足以说明反馈是否有效。

### Performance Hint API

`PerformanceHintManager` 从 API 31 提供。应用用一组属于本进程的工作线程创建 `Session`（提示会话，下文简称 HintSession），给出周期性工作的目标时长（target duration），并在每个周期调用 `reportActualWorkDuration()` 上报实际时长。目标变化时调用 `updateTargetWorkDuration()`；API 34 起，线程集合变化时可以调用 `setThreads()`。

HintSession 传递的是工作目标，不承诺使用某个 CPU 核、固定频率或执行特定调频动作。Android 17 的 Android framework（系统框架）通过 native 接口（C/C++ 层接口）把会话交给设备实现，Power HAL（电源硬件抽象层）与厂商策略决定如何响应。`createHintSession()` 可能返回 `null`，会话结束时还要调用 `close()`。

以 60 Hz 游戏为例，目标值可以从一个周期的预算出发，但不能机械地写成整帧 `16.67 ms`。若会话只覆盖模拟线程（simulation）或渲染提交线程（render-submit），目标时长和实际时长都应描述这组线程负责的周期工作；GPU 完成时间、UI 线程和其他进程的耗时不能合并到同一项 CPU 工作时长里。

评估 HintSession 应做只改变会话开关的 A/B 对照，并同时观察：

- 会话的目标时长、实际时长与线程集合；
- 线程处于运行（running）、可运行但等待 CPU（runnable）或睡眠（sleeping）的时间；
- CPU 频率、空闲状态、uclamp 或可用的厂商计数器；
- FrameTimeline、GPU 完成时刻、thermal headroom 和功耗；
- 冷机短时突发负载与热稳态的差异。

API 调用成功只说明信号送到了系统框架。资源是否响应、用户体验是否改善，还要由设备数据确认。

### Game State API

Game State API 从 Android 13（API 33）提供，用于告诉系统当前处于 loading（加载）、gameplay（对局）等状态，以及内容是否正在加载。它和 Game Mode 的用户偏好、HintSession 的周期工作时长分别表达不同信息。

应用只应上报含义稳定、能够说明原因的状态转换。把所有场景都标为高负载会让状态失去区分度，也不能保证系统持续提高 CPU 或 GPU 频率。

## 大型应用的启动案例

### TikTok × Android：公开结果与动作

Android Developers 在 2022 年发布的 TikTok 案例报告了以下单次项目结果：

- 应用启动时间减少 45%；
- 以“帧率低于目标值的概率”衡量的流畅性指标改善 49%；
- 视频首帧出现速度提升 41%；
- 视频卡顿概率减少 27%；
- 30 天内每位用户的活跃天数和平均单次使用时长（session duration）各提升 1%。

这些数字来自 TikTok 当时的版本、设备分布和指标口径。公开文章没有给出可供其他团队复算的完整原始数据，因此它们只能作为该案例的结果。

文章公开的工程动作更容易复用：

- 启动：参考 Jetpack App Startup，按需加载组件并细化调度；用 simpleperf 与 Android Studio Profiler 检查 I/O、线程和锁竞争。
- 流畅性：用 Layout Inspector 简化 View 层级，把集中在一帧内的 `doFrame()` 任务分散到不同帧。
- 播放：按编解码格式（codec）复用媒体播放器实例，改善网络连接与网络套接字（socket）复用，动态调整缓冲区，并对下一条视频做预加载（preload）和首帧预渲染（prerender）。
- 防回归：持续使用 Perfetto、CPU Profiler 和线上指标观察版本变化。

文章还提到用后台线程加载 View。View 构造、资源访问和自定义 View 行为可能受主线程约束，不能把这项做法直接复制到任意界面。采用时要明确哪些步骤可以异步执行，并用线程检查、截图测试和多种设备组合验证。

### 抖音归档材料：300 多个启动任务

本库保存的字节技术文章记录了另一个历史样本：启动阶段超过 300 个任务，团队把它们分为配置、预加载和功能任务，再分别做按需配置、预加载收益评估、功能拆分与调度。

可复用的判断顺序是：

1. 任务是否影响 TTID（Time to Initial Display，初始画面显示时间）或 TTFD（Time to Full Display，完整画面显示时间）之前的必要功能；
2. 延后后能否保持线程安全、跨进程一致性和功能可用；
3. 预加载在目标人群中的命中率与节省时间是多少；
4. 后台并发是否抢占 CPU、I/O、锁或内存，反而拖慢主线程；
5. 每次改动能否由 Macrobenchmark 与 Perfetto 重复验证。

任务数只是规模描述。减少一个 10 μs 任务与减少一次主线程磁盘读取的收益不同，排期要看关键路径的墙钟耗时（wall time，即包含等待在内的实际经过时间）和资源竞争。

## 从 Android 17 启动源码看 ContentProvider

`ActivityThread.handleBindApplication()` 决定了 ContentProvider（内容提供者组件，下文简称 provider）初始化与 `Application.onCreate()` 的先后关系。下面的 Android 17 源码摘录用于确认顺序：

```java
if (!data.restrictedBackupMode) {
    if (!ArrayUtils.isEmpty(data.providers)) {
        installContentProviders(app, data.providers);
    }
}

timestampApplicationOnCreateNs = SystemClock.uptimeNanos();
mInstrumentation.callApplicationOnCreate(app);
```

同进程 provider 会在 `Application.onCreate()` 前安装，因此 provider 的 `attachInfo()` / `onCreate()` 会进入冷启动关键路径。优化对象应由 Perfetto trace 决定：移除无用 provider、按库文档关闭自动初始化、用 AndroidX Startup 合并初始化入口，或把非必要工作延到首次使用。

### FileProvider 历史技巧：先核对依赖版本

抖音归档文章描述过一项历史字节码方案：临时修改 `ProviderInfo.grantUriPermissions`，利用当时 FileProvider 的安全检查顺序中断 `attachInfo()`，再把路径策略（path strategy，即内容 URI 与本地文件路径之间的映射规则）推迟到首次文件访问。

这项技巧不能直接作为 Android 17 项目的建议：

- `exported=false` 和 `grantUriPermissions=true` 是 FileProvider 要求的安全配置，绕过检查会增加升级与安全风险；
- 当前 AndroidX `androidx-main` 的 `attachInfo()` 只校验安全属性、保存 authority（内容 URI 中标识 provider 的字段）并清理缓存，路径配置 XML 由 `getLocalPathStrategy()` 在首次需要时解析；
- AndroidX 版本由应用依赖决定，系统是 Android 17 也不能证明项目已经使用这份实现；
- 延后路径解析只会转移这部分耗时，首次分享文件或打开内容 URI 的延迟也要测量。

项目应检查锁定版本的 AndroidX Core 源码，同时测量冷启动和首次文件访问。若当前版本仍有可测量开销，可以优先升级、减少重复的 FileProvider、缩小路径配置并按官方 API 使用。不要靠修改 `ProviderInfo` 或捕获后忽略 `SecurityException` 来延迟初始化。

### Rhea / btrace 的可复用部分

归档文章里的 Rhea 后续可以与字节开源的 btrace / RheaTrace3 对照。它用于补充应用的方法级调用信息，并把结果与 Perfetto 的调度、Binder（Android 进程间通信）、I/O 和渲染轨道放到同一时间轴。

方法级插桩（向方法中插入测量代码）会改变包体和编译过程，插桩与采样都会增加采集或运行开销。专门用于诊断的构建包应记录插件版本、采样或插桩范围、过滤规则与额外开销；结论仍要回到系统 trace，区分方法墙钟耗时、Runnable 状态下等待 CPU 的时间和锁阻塞。

## 大型应用与 OEM 的协作方式

Samsung SceneSDK 与 TikTok 案例展示了两种合作关系：前者把应用场景交给设备资源管理，后者由大型应用团队与 Android 团队围绕标准工具和 Jetpack 能力改造。

工程协作可以分为三层：

| 层次 | 接口与交付物 | 可移植性 |
| --- | --- | --- |
| Android 公共能力 | Game Mode、Game State、ADPF、Frame Pacing（帧节奏控制）、Perfetto | 较高，仍需检查设备支持 |
| OEM 设备配置 | 厂商干预、单应用配置（per-app profile）、驱动或电源配置 | 绑定机型和系统版本 |
| 联合诊断 | 稳定复现场景、双方 trace、计数器、实验报告 | 结论只覆盖已验证设备与版本 |

一次合作调优至少应交付：

- 可自动执行的场景脚本和用户指标；
- 应用、系统、内核、驱动、设备模式与温度信息；
- 原始 trace、采集配置、统计 SQL 和实验轮次；
- 标准 API 路径与私有配置路径的独立开关；
- 回退条件、版本范围和升级后的复验计划。

如果一个收益只能依赖私有配置获得，应用仍需保留公共路径和安全默认值。设备完成 OTA（系统在线更新）、更换 SoC（系统级芯片）或游戏版本升级后，应重新验证。

## 折叠屏与多窗口：负载随窗口状态变化

折叠与展开可能改变窗口尺寸、宽高比、像素密度、逻辑显示屏（Display）、刷新模式和折叠姿态。Activity 可能经历配置变更或重建，Surface（应用提交图形缓冲区的接口）与缓冲区尺寸也可能变化。性能问题应按时间线分成：

1. 折叠状态或窗口尺寸变化；
2. Activity / Compose 状态恢复与重新布局；
3. Surface 创建、尺寸更新和缓冲区分配；
4. 首个正确内容帧与后续稳定帧；
5. 媒体、相机或游戏状态是否连续。

Jetpack WindowManager 提供 `FoldingFeature`（折叠区域及其姿态信息）；Compose 自适应布局 API 可以使用窗口尺寸和姿态信息选择布局。这些 API 不会自动减少 Compose 重组、图片解码或 GPU 像素处理量。大型资源应按当前窗口需求加载，状态恢复也要避免在主线程重复 I/O。

多窗口不会让 GPU 工作量按固定倍数增长。每个窗口的可见面积、刷新节奏、内容复杂度、遮挡关系和硬件合成能力都会改变 SurfaceFlinger（系统合成服务）与 GPU 负载。验证时应记录各窗口的边界尺寸（bounds）、合成层（Layer）、FrameTimeline、GPU 频率、内存和温控状态，再比较单窗口与多窗口。

折叠后不要用手写的 `16.6 ms` 定时器代替 `Choreographer`。Activity 或 ViewRoot 是否重建取决于配置与设备行为，帧回调应随其生命周期注册和清理；目标帧率、Surface 的目标帧率请求（frame-rate vote）、动画参数与媒体策略则要按新的 Display 和窗口状态重算。

## 汽车、TV 与 IoT：保留机制，替换指标

手机案例不能直接按百分比迁移到其他 Android 形态，但验证方法仍可复用：

- **Android Automotive**：关注系统启动到可交互的时间、驾驶相关界面的响应时限、相机或音频链路和长期热稳态。
- **Android TV**：关注启动、遥控输入到画面呈现的延迟、视频首帧、掉帧、解码器与内存压力。
- **IoT**：关注受限内存、冷启动、持续功耗、闪存 I/O 与看门狗（检测卡死的监控机制）触发后的恢复。

每种形态都应从用户可感知指标开始，再用 Perfetto、内核跟踪记录、媒体或图形计数器定位。手机游戏的 60 / 120 fps、触摸延迟和短时升频（boost）不能自动成为车机、TV 或常驻设备的目标。

## 常见误判

### 把厂商模式名称当成内核机制

“性能”“加速”“智能温控”是产品层名称。没有设备厂商文档或 trace 时，只能描述模式切换前后的可观测差异。

### 把 HintSession 当成锁频接口

Performance Hint 传递目标时长与实际时长。它不承诺绑核、固定频率或避免温控降频。

### 用平均 FPS 掩盖持续运行后的降频

前半段高帧率和后半段降频可能得到看似正常的平均值。报告应同时给出时间序列、P95 帧时间、未赶上显示截止点的帧数与稳态窗口。

### 照搬旧版 FileProvider 字节码改写

旧文章依赖当时的 AndroidX 实现。当前 `androidx-main` 已经把本地路径策略延迟到首次访问，但项目锁定的版本可能不同，这部分耗时也可能转移到首次文件操作。应同时核对依赖源码、冷启动 trace 和首次文件访问 trace，安全校验不应被修改。

### 把多窗口压力写成固定倍数

窗口数量不会直接换算成 GPU 或内存倍数。窗口边界、内容、刷新率、合成路径和遮挡都要进入实验条件。

### 用案例百分比承诺自己的收益

TikTok 的 45% 启动改善属于该项目。自己的基线、设备分布和瓶颈不同，收益需要本地实验给出。

## 与相关章节的边界

- §5.4、§5.6 和 §11.1 解释 DVFS（动态电压与频率调节）、Power HAL 与温控机制；这里关注应用如何提供信号并验证 OEM 响应。
- §2.2 与 §2.10 解释帧率、刷新率和 GPU；这里关注厂商干预、折叠和多窗口实验。
- §8.2、§8.3 解释启动路径；这里补充 TikTok、抖音与 ContentProvider 的公开案例。
- §13 解释 Perfetto；案例应附采集配置、原始 trace 和统计脚本。
- §17.1、§17.2 解释 OEM 与 SoC 差异；这里把差异限制在具体设备证据中。

## 参考资料

### OEM 与行业案例

- [Samsung Game Booster 支持页](https://www.samsung.com/levant/support/apps-services/know-more-about-the-game-booster-app/)
- [Samsung SceneSDK 案例](https://developer.samsung.com/galaxy-gamedev/blog/en/2022/04/26/accelerate-game-performance-based-on-scenesdk)
- [TikTok Android 性能案例](https://android-developers.googleblog.com/2022/08/precise-improvements-how-tiktok-enhanced-its-social-experience-on-android.html)
- 本库归档：`Cubox/抖音 Android 性能优化系列：启动优化实践-2022-03-25.md`
- 本库归档：`Cubox/抖音 Android 性能优化系列：新一代全能型性能分析工具 Rhea-2022-01-14.md`
- [ByteDance btrace](https://github.com/bytedance/btrace)
- [Android Developers Blog: Build intelligent Android apps: Cloud and hybrid inference](https://android-developers.googleblog.com/2026/07/build-intelligent-android-apps-cloud-and-hybrid-inference.html)（不作为本篇案例证据；截至 2026-08-14 返回 404）

### Android API 与指南

- [Game Mode API 与厂商干预概览](https://developer.android.com/games/optimize/adpf/gamemode/about-API-and-interventions)
- [Game Mode API](https://developer.android.com/games/optimize/adpf/gamemode/gamemode-api)
- [Game Mode interventions](https://developer.android.com/games/optimize/adpf/gamemode/gamemode-interventions)
- [FPS throttling](https://developer.android.com/games/optimize/adpf/gamemode/fps-throttling)
- [Game State API](https://developer.android.com/games/optimize/adpf/gamemode/gamestate-api)
- [ADPF 总览](https://developer.android.com/games/optimize/adpf)
- [ADPF 平台说明的旧路径](https://developer.android.com/topic/performance/adpf)（截至 2026-08-14 返回 404；请使用上一条 ADPF 总览）
- [PowerManager thermal API](https://developer.android.com/reference/android/os/PowerManager)
- [PerformanceHintManager API](https://developer.android.com/reference/android/os/PerformanceHintManager)
- [PerformanceHintManager.Session API](https://developer.android.com/reference/android/os/PerformanceHintManager.Session)
- [AndroidX App Startup](https://developer.android.com/topic/libraries/app-startup)
- [Macrobenchmark 启动测量](https://developer.android.com/topic/performance/benchmarking/macrobenchmark-overview)
- [折叠屏适配](https://developer.android.com/develop/ui/compose/layouts/adaptive/foldables/learn-about-foldables)
- [AndroidX Window 版本说明](https://developer.android.com/jetpack/androidx/releases/window)

### Android 17 与 AndroidX 源码

- [`GameManager.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/app/GameManager.java)
- [`PerformanceHintManager.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/os/PerformanceHintManager.java)
- [`PowerManager.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/os/PowerManager.java)
- [`ActivityThread.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/app/ActivityThread.java)
- [AndroidX FileProvider 当前源码](https://android.googlesource.com/platform/frameworks/support/+/refs/heads/androidx-main/core/core/src/main/java/androidx/core/content/FileProvider.java)
