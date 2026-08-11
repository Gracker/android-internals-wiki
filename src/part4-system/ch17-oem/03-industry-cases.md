---
title: "OEM 与大型应用协作案例"
chapter: "17.3"
section: "17.3"
applicable_versions: "Android 12 (API 31) - Android 17 (API 37)"
last_verified: "2026-08-06"
last_verified_against: "Android Developers Game Mode/ADPF 文档, Samsung Support Game Booster, Samsung Developer SceneSDK, Android Developers Blog TikTok case study"
confidence: medium
sources:
  - type: official
    path: "https://developer.android.com/games/optimize/adpf/gamemode/about-API-and-interventions"
  - type: official
    path: "https://developer.android.com/games/optimize/adpf/gamemode/gamemode-interventions"
  - type: official
    path: "https://developer.android.com/games/optimize/adpf/gamemode/fps-throttling"
  - type: official
    path: "https://developer.android.com/topic/performance/adpf"
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
  - type: official
    path: "https://developer.android.com/jetpack/androidx/releases/window"
tags: ['case-study', 'game-mode', 'adpf', 'startup', 'foldable', 'oem', 'industry']
related_chapters: ["5.6", "7.4", "7.5", "8.2", "8.3", "11.1", "16.1", "17.1", "17.2"]
drafted_date: "2026-04-04"
drafted_by: "openclaw-task2a"
task6_state: reviewed
reviewed_by: hermes-aiw-review-finalize-apply
reviewed_date: "2026-08-06"
task6_result: "pass-light-edit"
last_task6_audit: "2026-07-15"
last_task6_audit_log: "logs/review/2026-07-15-18-audit.md"
last_task6_audit_notes: "idle audit: L1 禁用词全清；中英文间距干净；高频词(优化48/性能38/设备28)均主题固有；frontmatter 完整；4个🔹锚点全覆盖；无 L1/L2 问题，无需修改。"
status: finalized
pipeline_stage: finalized
task9_state: reviewed
task9_result: pass-tech-review
task2b_state: fixed
task2b_result: fixed
repaired_date: "2026-04-27"
repaired_by: "openclaw-task2b"
task9_reviewed_by: "openclaw-task9"
task9_reviewed_date: "2026-05-04"
last_task9_at: "2026-05-04T10:37:13+08:00"
last_task2b_at: "2026-04-27T14:50:00+08:00"
last_task9_audit: "2026-07-08"
last_task9_audit_log: "logs/deep-review/2026-07-08-14-audit.md"
last_task9_audit_notes: "idle audit: no P0/P1; android-17.0.0_r1 source paths rechecked; GameManager/PowerManager API version guards rechecked; existing P2 guards remain for FileProvider attachInfo, Thermal thresholds, Game State API."
review_notes: "2026-04-28 task9 deep-review: pass-tech-review；无 P0/P1；Task6 已通过且 queue 无 pending，自动晋升 finalized。P2 2 写入 suggestions。；2026-05-04 task9 deep-review: pass-tech-review。P0 0 / P1 0 / P2 3。核心 API 与案例链路可通过；仅有 Thermal thresholds API 版本守卫、FileProvider 插桩细节、折叠屏多窗口数据支撑三处 P2。；2026-08-06 hermes review/finalize: 复核 Jetpacker hybrid inference 新增段落与 Android 17/API 边界，未发现 P0/P1/P2 open issue，推进 finalized。"
deepseek_cn_review_state: done
last_deepseek_cn_review_at: 2026-06-21
last_body_apply_at: "2026-08-06T09:15:33+08:00"
last_body_apply_run_id: "20260806-091503-909828fa"
last_body_apply_source: "source-index:194; 04-jetpacker-intro.md"
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
| 机制解释 | 为什么这些动作可能影响指标 | AOSP、AndroidX、kernel、图形或媒体源码 |
| 设备实现 | OEM 如何响应提示、配置频率或温控 | vendor 文档、设备配置、厂商 Trace |
| 本地复现 | 在自己的 App 和设备上是否成立 | Perfetto、Macrobenchmark、counter、A/B 实验 |

公开案例给出的百分比只能保留在原案例的分母里。没有设备分布、样本数、统计区间和版本信息时，不能把它改写成项目排期或行业基准。

平台锚点为 Android 17（API 37）和 AOSP `android-17.0.0_r1`。旧案例保留其历史背景，API 语义与建议按 Android 17 重新核对。

## Samsung：用户模式与合作接口是两条路径

Samsung 的公开材料提供了一个边界清楚的 OEM 案例。

Samsung 支持页把 Game Booster 描述为游戏运行时自动启动的用户功能，并说明它会在电量、性能和温度之间做平衡。该页面没有公开 CPU governor、uclamp、GPU 驱动参数或 thermal threshold，因此 Game Booster 的 UI 选项不能直接翻译成某个固定内核动作。

Samsung 2022 年的 SceneSDK 文章描述了另一条合作路径：游戏把 loading、lobby、gameplay 等场景信息交给设备侧服务，服务可按场景调整 CPU / GPU frequency；设备发生 frequency reduction 时，也可把通知发回游戏。文章还描述了按目标帧率调整显示刷新率的合作方式。

SceneSDK 不是 Android SDK 公共 API。文章里的 JSON 协议、支持范围和策略来自当时的 Samsung 合作环境，不能假设所有 Galaxy 设备或所有应用都能调用。它的工程价值在于展示双向协作：

- 应用提供比 CPU 利用率更早的场景和目标帧率信息；
- 设备提供温控、频率变化和资源约束信息；
- 应用收到约束后降低可伸缩负载，设备按场景分配预算；
- 双方用帧时间、功耗和热稳态验证结果。

在一台 Galaxy 设备上验证 Game Booster 或 SceneSDK 类策略，应同时记录场景标记、CPU / GPU frequency、FrameTimeline、thermal status、显示刷新率和电源模式。只有 UI 模式名称，没有运行数据，无法证明调度器或驱动做了什么。

这套分层也适用于其他 OEM 的游戏入口。厂商公开页能证明用户有哪些选项；绑核、频率投票和驱动策略仍需对应机型、系统版本和 Trace。

## Game Mode：用户选择、应用适配与 OEM intervention

Android Game Mode 有三个容易混淆的角色：

1. **用户选择**：Standard、Performance、Battery Saver，以及 Android 14 引入的 Custom。
2. **应用适配**：游戏读取 `GameManager.getGameMode()`，调整自己的分辨率、画质、帧率或后台工作。
3. **OEM intervention**：OEM 对没有自行适配或不再更新的游戏配置 backbuffer resize、ANGLE 或 FPS throttling。

Game Mode API 与 intervention 从部分 Android 12 设备开始提供，Android Developers 将 Android 13 及以上设备列入支持范围。`getGameMode()` 仍可能返回 `GAME_MODE_UNSUPPORTED`，应用必须准备默认策略。

Android 17 的 `GameManager.java` 还保留 Custom 的兼容处理：当模式为 `GAME_MODE_CUSTOM`，而应用 `targetSdkVersion` 不高于 Android 13 时，`getGameMode()` 返回 Standard。游戏应在每次 resume 时重新读取模式，未知值走安全分支。

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

声明 `supports*GameMode="true"` 后，游戏要实现对应策略，平台会清除此前对该模式应用的 OEM intervention。`allowGameDownscaling` 和 `allowGameFpsOverride` 是 intervention 的独立 opt-out 项，不能用 `supports*` 代替。

### intervention 的测量边界

WindowManager backbuffer resize 会改变游戏渲染缓冲区尺寸，再由系统缩放到显示尺寸；它可能降低 GPU 像素工作量，也会影响清晰度。FPS throttling 从 Android 13 起可用，目标是让帧率更稳定并减少功耗。ANGLE intervention 改变 GLES 实现路径，结果受 shader、driver 和设备支持影响。

对比 intervention 时应固定：

- 同一 APK、关卡、画质、输入脚本和网络数据；
- 分辨率、显示刷新率、目标帧率和电源模式；
- 冷机起点、预热时长、环境温度和运行轮次；
- TTFF、P50 / P95 帧时间、deadline miss、GPU busy、功耗和热状态。

Android 文档里的节能或 GPU 降幅属于文档给定设备与条件下的示例，不应写入本项目的验收门槛。

## ADPF：让负载与热预算形成反馈

### Thermal API

`PowerManager.getThermalHeadroom(int)` 从 API 30 提供，参数范围为 0～60 秒。返回值表示当前或预测使用了多少热包络：`1.0` 对应 `THERMAL_STATUS_SEVERE` 阈值，数值可以大于 `1.0`。设备不支持时返回 `NaN`；调用明显快于每秒一次也可能得到 `NaN`。

`getThermalHeadroomThresholds()` 从 API 35 提供，返回设备为各 thermal status 定义的 headroom threshold。调用可能抛出 `UnsupportedOperationException` 或 `IllegalStateException`。从 API 36 开始，threshold map 可以变化；Android 17 应用可以使用 `addThermalHeadroomListener()` 接收 headroom 与 threshold 更新。

下面的代码用于 Android 12～17 共用模块低频采样，并为 API 35 以下设备保留 `SEVERE == 1.0f` 的定义：

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

这段代码只读取信号，不规定降级幅度。调用方应以秒级节奏运行，并给画质或帧率切换加入滞回与最短保持时间，避免 headroom 在阈值附近波动时频繁切档。返回 `null` 时保持保守默认策略并记录设备信息。

温控策略要验证三个时间关系：headroom 何时接近阈值、应用何时降低负载、帧时间与频率何时稳定。只看温度值或只看平均 FPS 都不足以说明反馈是否有效。

### Performance Hint API

`PerformanceHintManager` 从 API 31 提供。应用用一组属于本进程的工作线程创建 `Session`，给出周期性工作的 target duration，并在每个周期调用 `reportActualWorkDuration()`。目标变化时调用 `updateTargetWorkDuration()`；API 34 起，线程集合变化时可以调用 `setThreads()`。

HintSession 传递的是工作目标，不承诺某个 CPU、频率或 governor 动作。Android 17 的 framework 经 native 接口把 session 交给设备实现，Power HAL 与 vendor 策略决定响应方式。`createHintSession()` 可能返回 `null`，会话结束还要 `close()`。

以 60 Hz 游戏为例，目标值可从一个周期的预算出发，但不能机械写成整帧 `16.67 ms`。若 session 只覆盖 simulation 或 render-submit 线程，target 和 actual 都应描述这组线程负责的周期工作；GPU 完成时间、UI 线程和其他进程的耗时不能塞进同一个 CPU duration。

评估 HintSession 应做开关 A/B，并同时观察：

- session 的 target / actual duration 与线程集合；
- 线程 running / runnable / sleeping 状态；
- CPU frequency、idle、uclamp 或可用 vendor counter；
- FrameTimeline、GPU completion、thermal headroom 和功耗；
- 冷机 burst 与热稳态的差异。

API 调用成功只说明信号送达 framework。资源响应和用户体验是否改善，需要设备数据确认。

### Game State API

Game State API 从 Android 13（API 33）提供，用于告诉系统当前处于 loading、gameplay 等状态，以及内容是否正在加载。它与 Game Mode 的用户偏好、HintSession 的周期 duration 不是同一个信号。

应用只应上报可持续解释的状态转换。把所有场景都标为高负载会让状态失去区分度，也不能保证系统持续给出高频资源。

## 大型 App 的启动案例

### TikTok × Android：公开结果与动作

Android Developers 在 2022 年发布的 TikTok 案例报告了以下单次项目结果：

- App 启动时间减少 45%；
- UI smoothness 指标改善 49%；
- 视频首帧出现速度提升 41%；
- 视频卡顿概率减少 27%；
- 30 天内每用户活跃天数和平均 session duration 各提升 1%。

这些数字来自 TikTok 当时的版本、设备分布和指标口径。公开文章没有给出可供其他团队复算的完整原始数据，因此它们只能作为该案例的结果。

文章公开的工程动作更容易复用：

- 启动：参考 Jetpack App Startup，按需加载组件并细化调度；用 simpleperf 与 Android Studio Profiler 检查 I/O、线程和锁。
- 流畅性：用 Layout Inspector 简化 View 层级，把每帧任务分配到不同帧。
- 播放：复用按 codec 组织的 player，改善连接与 socket 复用，动态调整缓冲区，并做下一条视频 preload 与首帧 prerender。
- 防回归：持续使用 Perfetto、CPU Profiler 和线上指标观察版本变化。

文章还提到后台线程加载 View。View 构造、资源访问和自定义 View 行为存在主线程约束，不能把这条动作直接复制到任意 UI。采用时要限定可异步部分，并用线程检查、截图测试和设备组合验证。

### 抖音归档材料：300 多个启动任务

本库保存的字节技术文章记录了另一个历史样本：启动阶段超过 300 个任务，团队把它们分为配置、预加载和功能任务，再分别做按需配置、预加载收益评估、功能拆分与调度。

可复用的判断顺序是：

1. 任务是否影响 TTID 或 TTFD 前的必要功能；
2. 延后后能否保持线程安全、进程安全和功能可用；
3. 预加载在目标人群中的命中率与节省时间是多少；
4. 后台并发是否抢占 CPU、I/O、锁或内存，反向拖慢主线程；
5. 每次改动能否由 Macrobenchmark 与 Perfetto 重复验证。

任务数只是规模描述。减少一个 10 μs 任务与减少一次主线程磁盘读取的收益不同，排期要看关键路径 wall time 和资源竞争。

## 从 Android 17 启动源码看 ContentProvider

`ActivityThread.handleBindApplication()` 决定了 provider 初始化与 `Application.onCreate()` 的先后关系。下面的 Android 17 源码摘录用于确认顺序：

```java
if (!data.restrictedBackupMode) {
    if (!ArrayUtils.isEmpty(data.providers)) {
        installContentProviders(app, data.providers);
    }
}

timestampApplicationOnCreateNs = SystemClock.uptimeNanos();
mInstrumentation.callApplicationOnCreate(app);
```

同进程 provider 会在 `Application.onCreate()` 前安装，因此 provider 的 `attachInfo()` / `onCreate()` 会进入冷启动关键路径。优化对象应由 Trace 决定：移除无用 provider、按库文档关闭自动初始化、用 AndroidX Startup 合并初始化入口，或把非必要工作延到首次使用。

### FileProvider 历史技巧已经失去适用前提

抖音归档文章描述过一项历史字节码方案：临时修改 `ProviderInfo.grantUriPermissions`，利用旧版 FileProvider 的安全检查中断 `attachInfo()`，再把 path strategy 推迟到首次文件访问。

这项技巧不适合作为 Android 17 建议：

- `exported=false` 和 `grantUriPermissions=true` 是 FileProvider 的安全契约，绕过检查会增加升级与安全风险；
- 当前 AndroidX `androidx-main` 的 `attachInfo()` 只校验安全属性、保存 authority 并清理 cache，path XML 由 `getLocalPathStrategy()` 首次需要时解析；
- AndroidX 版本由 App 依赖决定，平台是 Android 17 也不能证明项目已经使用这份实现。

项目应检查锁定的 AndroidX Core 源码和启动 Trace。若当前版本仍有可测量开销，优先升级、减少重复 FileProvider、缩小 path 配置并按官方 API 使用。不要靠修改 `ProviderInfo` 或吞掉 `SecurityException` 延迟初始化。

### Rhea / btrace 的可复用部分

归档文章里的 Rhea 后续可以与字节开源的 btrace / RheaTrace3 对照。它的用途是补充应用方法现场，并把结果与 Perfetto 的调度、Binder、I/O 和渲染轨道放到同一时间轴。

方法级插桩或采样会改变包体、编译和运行开销。专项包应记录插件版本、采样或插桩范围、过滤规则与额外开销；结论仍要回到系统 Trace，区分方法 wall time、Runnable 等待和锁阻塞。

## 大型 App 与 OEM 的协作方式

Samsung SceneSDK 与 TikTok 案例展示了两种合作关系：前者把应用场景交给设备资源管理，后者由大型 App 团队与 Android 团队围绕标准工具和 Jetpack 能力改造。

工程协作可以分为三层：

| 层次 | 接口与交付物 | 可移植性 |
| --- | --- | --- |
| Android 公共能力 | Game Mode、Game State、ADPF、Frame Pacing、Perfetto | 较高，仍需检查设备支持 |
| OEM 设备配置 | intervention、per-app profile、驱动或 power 配置 | 绑定机型和系统版本 |
| 联合诊断 | 稳定复现场景、双方 Trace、counter、实验报告 | 结论只覆盖已验证设备与版本 |

一次合作调优至少应交付：

- 可自动执行的场景脚本和用户指标；
- App、系统、kernel、driver、设备模式与温度信息；
- 原始 Trace、采集配置、统计 SQL 和实验轮次；
- 标准 API 路径与私有配置路径的独立开关；
- 回退条件、版本范围和升级后的复验计划。

如果一个收益只能依赖私有配置获得，应用仍需保留公共路径和安全默认值。设备 OTA、SoC 变更或游戏版本升级后，应重新验证。

## 折叠屏与多窗口：负载随窗口状态变化

折叠与展开可能改变窗口尺寸、宽高比、density、display、刷新模式和折叠姿态。Activity 可能经历配置变更或重建，Surface 与 buffer 尺寸也可能变化。性能问题应按时间线拆成：

1. 折叠状态或窗口尺寸变化；
2. Activity / Compose 状态恢复与重新布局；
3. Surface 创建、尺寸更新和 buffer 分配；
4. 首个正确内容帧与后续稳定帧；
5. 媒体、相机或游戏状态是否连续。

Jetpack WindowManager 或 Compose adaptive APIs 提供 `FoldingFeature`、窗口尺寸与姿态信息。它们用于选择布局，不会自动减少重组、图片解码或 GPU 像素工作量。大型资源应按当前窗口需求加载，状态恢复也要避免在主线程重复 I/O。

多窗口不等于 GPU 工作量固定翻倍。每个窗口的可见面积、刷新节奏、内容复杂度、遮挡关系和硬件合成能力都会改变 SurfaceFlinger 与 GPU 负载。验证时应记录各窗口 bounds、Layer、FrameTimeline、GPU frequency、内存和 thermal，再比较单窗口与多窗口。

折叠后不要用手写的 `16.6 ms` 定时器代替 `Choreographer`。Activity 或 ViewRoot 是否重建取决于配置与设备行为，帧回调应随其生命周期注册和清理；目标帧率、Surface frame-rate vote、动画参数与媒体策略则要按新的 display 和窗口状态重算。

## 汽车、TV 与 IoT：保留机制，替换指标

手机案例不能直接按百分比迁移到其他 Android 形态，但证据方法仍可复用：

- **Android Automotive**：关注系统启动到可交互、驾驶相关 UI deadline、相机或音频链路和长期热稳态。
- **Android TV**：关注启动、遥控输入到呈现、视频首帧、掉帧、decoder 与内存压力。
- **IoT**：关注受限内存、冷启动、持续功耗、flash I/O 与看门狗恢复。

每种形态都应从用户可感知指标开始，再用 Perfetto、kernel trace、媒体或图形 counter 定位。手机游戏的 60 / 120 fps、触摸延迟和短时 boost 不能自动成为车机、TV 或常驻设备的目标。

## 常见误判

### 把厂商模式名称当成内核机制

“性能”“加速”“智能温控”是产品层名称。没有 vendor 文档或 Trace 时，只能描述模式切换前后的可观测差异。

### 把 HintSession 当成锁频接口

Performance Hint 传递 target 与 actual duration。它不承诺绑核、固定频率或避免 thermal throttling。

### 用平均 FPS 掩盖热衰减

前半段高帧率和后半段降频可能得到看似正常的平均值。报告应同时给出时间序列、P95 帧时间、deadline miss 与稳态窗口。

### 复制旧版 FileProvider 插桩

旧文章依赖当时的 AndroidX 实现。当前版本已改成延迟创建本地 path strategy，安全校验也不应被修改。先核对依赖源码和 Trace。

### 把多窗口压力写成固定倍数

窗口数量不会直接换算成 GPU 或内存倍数。bounds、内容、刷新率、合成路径和遮挡都要进入实验条件。

### 用案例百分比承诺自己的收益

TikTok 的 45% 启动改善属于该项目。自己的基线、设备分布和瓶颈不同，收益需要本地实验给出。

## 与相关章节的边界

- §5.4、§5.6 和 §11.1 解释 DVFS、Power HAL 与 thermal；这里关注应用如何提供信号并验证 OEM 响应。
- §2.2 与 §2.10 解释帧率、刷新率和 GPU；这里关注 intervention、折叠和多窗口实验。
- §8.2、§8.3 解释启动路径；这里补充 TikTok、抖音与 provider 的公开案例。
- §13 解释 Perfetto；案例应附采集配置、原始 Trace 和统计脚本。
- §17.1、§17.2 解释 OEM 与 SoC 差异；这里把差异限制在具体设备证据中。

## 参考资料

### OEM 与行业案例

- [Samsung Game Booster 支持页](https://www.samsung.com/levant/support/apps-services/know-more-about-the-game-booster-app/)
- [Samsung SceneSDK 案例](https://developer.samsung.com/galaxy-gamedev/blog/en/2022/04/26/accelerate-game-performance-based-on-scenesdk)
- [TikTok Android 性能案例](https://android-developers.googleblog.com/2022/08/precise-improvements-how-tiktok-enhanced-its-social-experience-on-android.html)
- 本库归档：`Cubox/抖音 Android 性能优化系列：启动优化实践-2022-03-25.md`
- 本库归档：`Cubox/抖音 Android 性能优化系列：新一代全能型性能分析工具 Rhea-2022-01-14.md`
- [ByteDance btrace](https://github.com/bytedance/btrace)
- [Android Developers Blog: Build intelligent Android apps: Cloud and hybrid inference](https://android-developers.googleblog.com/2026/07/build-intelligent-android-apps-cloud-and-hybrid-inference.html)

### Android API 与指南

- [Game Mode API](https://developer.android.com/games/optimize/adpf/gamemode/gamemode-api)
- [Game Mode interventions](https://developer.android.com/games/optimize/adpf/gamemode/gamemode-interventions)
- [Game State API](https://developer.android.com/games/optimize/adpf/gamemode/gamestate-api)
- [ADPF 总览](https://developer.android.com/games/optimize/adpf)
- [PowerManager thermal API](https://developer.android.com/reference/android/os/PowerManager)
- [PerformanceHintManager API](https://developer.android.com/reference/android/os/PerformanceHintManager)
- [AndroidX App Startup](https://developer.android.com/topic/libraries/app-startup)
- [Macrobenchmark 启动测量](https://developer.android.com/topic/performance/benchmarking/macrobenchmark-overview)
- [折叠屏适配](https://developer.android.com/develop/ui/compose/layouts/adaptive/foldables/learn-about-foldables)

### Android 17 与 AndroidX 源码

- [`GameManager.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/app/GameManager.java)
- [`PerformanceHintManager.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/os/PerformanceHintManager.java)
- [`PowerManager.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/os/PowerManager.java)
- [`ActivityThread.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/app/ActivityThread.java)
- [AndroidX FileProvider 当前源码](https://android.googlesource.com/platform/frameworks/support/+/refs/heads/androidx-main/core/core/src/main/java/androidx/core/content/FileProvider.java)
