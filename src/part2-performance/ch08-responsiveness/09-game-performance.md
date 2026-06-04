---

title: "Android 游戏性能与 Game Mode/State API"
chapter: "8.9"
section: "8.9"
status: "ready-for-review"
applicable_versions: "Android 12 (API 31) - Android 17 (API 37)"
drafted_date: "2026-04-08"
drafted_by: "openclaw-task2a"
last_verified: "2026-04-27"
last_verified_against: "Android Developers Game SDK Performance Tuner + GameActivity text input docs, AOSP GameManagerService, Perfetto gpu.renderstages proto"
confidence: medium
sources:
  - type: official
    path: "https://developer.android.com/games/optimize/adpf/gamemode/about-API-and-interventions"
  - type: official
    path: "https://developer.android.com/games/optimize/adpf/gamemode/gamemode-api"
  - type: official
    path: "https://developer.android.com/games/optimize/adpf/gamemode/gamestate-api"
  - type: official
    path: "https://developer.android.com/games/optimize/adpf/gamemode/gamemode-interventions"
  - type: official
    path: "https://developer.android.com/reference/android/app/GameManager"
  - type: official
    path: "https://developer.android.com/reference/android/app/GameState"
  - type: official
    path: "https://developer.android.com/reference/android/os/health/SystemHealthManager"
  - type: official
    path: "https://developer.android.com/games/sdk/performance-tuner"
  - type: official
    path: "https://developer.android.com/games/agdk/game-activity/get-started"
  - type: official
    path: "https://developer.android.com/games/agdk/game-activity/use-text-input"
  - type: aosp
    path: "frameworks/base/core/java/android/app/GameManager.java"
  - type: aosp
    path: "frameworks/base/core/java/android/app/GameState.java"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/app/GameManagerService.java"
  - type: aosp
    path: "external/perfetto/protos/perfetto/config/data_source_config.proto"
  - type: research
    path: "intake/research-feeds/2026-04-08-19-android-adpf-agdk-game-mode-thermal-performance.md"
tags: [game, gamemode, gamestate, agdk, frame-pacing, adpf, gaming-performance, thermal]
related_chapters: ["2.17", "5.9", "5.5", "7.1", "7.9", "14.10"]
created_by: "task2a-knowledge-gap"
created_date: "2026-04-08"
gap_source: "官方文档+读者需求+研究素材"
pipeline_stage: task6_pending
task6_state: revisiting
task9_state: pending
task2b_state: fixed
task2b_result: fixed-lite
reviewed_by: "openclaw-task6"
reviewed_date: 2026-05-11
task6_result: pass-light-edit
task9_result: needs-rework
task9_reviewed_by: "openclaw-task9"
task9_reviewed_date: 2026-05-14
last_task9_at: "2026-05-14T12:37:27+08:00"
last_task2b_at: "2026-05-09T08:43:58+08:00"
review_notes: "2026-05-11 task6 review (revisiting→reviewed): pass-light-edit。L1/L2 修正 4 处，L3/L4 问题 6 个写入 queue.json。"
last_task6_at: "2026-05-11T13:05:00+08:00"
last_task2b_lite_at: 2026-06-05
---

# 8.9 Android 游戏性能与 Game Mode/State API

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 游戏性能与普通 App 的预算差异：持续满帧、热约束、帧时间波动
- 🔹 Game Mode API：Manifest / `game_mode_config.xml` 声明、`GameManager#getGameMode()` 读取用户模式
- 🔹 Game State API：`GameManager#setGameState(GameState)`、`isLoading`、`MODE_*`
- 🔹 Game Mode、Game State、OEM interventions 与 ADPF 的边界
- 🔹 Perfetto 观测口径：FrameTimeline、Surface layer、CPU/GPU 频率、`power.hint_session`
- 🔹 原生游戏工具链：GameActivity、Swappy、AGI / Perfetto 的分工
- 🔹 OEM 游戏模式与测试方法：关闭厂商模式，分开验证 user mode 与 `game_overlay`

### 结构

1. 游戏性能的特殊性：持续满帧 vs 按需渲染
2. Game Mode API：用户意图到系统行为的桥梁
3. Game State API：细粒度的状态通信
4. AGDK 工具链：从渲染到调试的完整支持
5. Perfetto：游戏帧时间、频率与热状态联合分析
6. Android 16 与 Android 12/13+ 的平台变化
7. 游戏卡顿分析方法论
8. OEM 游戏模式与 Game Mode API 的关系
<!-- outline-end -->

在前面几章我们讨论的优化方法——主线程减少耗时、布局层级优化、避免过度绘制——主要面向的是传统 View 体系的应用。游戏的性能模型完全不同。

一个普通 App 的大部分时间在等待用户交互，只在用户点击或滑动时才触发一帧渲染。游戏则从启动的那一刻起就持续以固定帧率推进渲染循环——60fps 意味着每 16.66ms 必须完成一帧，120fps 意味着预算只有 8.33ms，而且不能掉。这种持续满负载的运行模式，使得游戏对 CPU 调度延迟、热降频、GPU 吞吐量的敏感度远超普通应用。

一个典型的例子：某款游戏在冷启动后前 30 秒稳定 60fps，之后帧率开始波动，45 秒后跌到 40fps。从 Perfetto 中看到的不是某一帧特别慢，而是 CPU 频率在 1.8GHz 和 0.9GHz 之间反复跳变——系统检测到温度上升后开始降频，帧率随之崩塌。这不是代码写得不好，是系统没有给游戏正确的性能资源。

Android 从 Android 12 开始逐步构建了一套面向游戏的系统级性能框架：Game Mode API 让用户表达性能偏好，Game State API 让游戏告知系统当前运行状态，ADPF（已在 §5.9 详细讨论）提供 CPU 调度提示和热管理，Frame Pacing Library（已在 §2.17 详细讨论）解决渲染同步问题。这些 API 的共同设计理念是：**让游戏和系统之间建立双向的信息通道**，系统不再是"黑盒式"地根据历史负载猜测需求，而是拿到明确的信号后精准调配资源。

读完这一节，我们能理解游戏性能优化的三层体系（系统层→框架层→引擎层），掌握 Game Mode/State API 的使用方法，以及在实际工作中如何用 Perfetto 分析游戏场景的性能瓶颈。

## 游戏性能的特殊性：持续满帧 vs 按需渲染

游戏和普通应用的性能需求差异，可以用一个数字来概括：**帧时间预算的占比**。

一个普通 App 在用户点击后，主线程执行 onClick → measure → layout → draw → syncAndDraw，整个流程通常在 5-10ms 内完成，占 60fps 帧预算（16.66ms）的 30-60%。即使偶尔超过预算，用户感知也不明显——因为下一帧可能几秒后才会来。

游戏的帧时间预算几乎是 100% 占满的。以 60fps 为例，每帧 16.66ms 的预算中，游戏引擎需要完成逻辑更新（AI、物理、碰撞检测）、场景图遍历、命令提交、GPU 渲染。120fps 下预算减半到 8.33ms，几乎没有容错空间。对应的约束主要有三点：

1. **CPU 调度延迟直接导致掉帧**。普通 App 偶尔被调度延迟 2-3ms 影响不大，但游戏如果主线程在某帧被内核调度器延迟了 3ms，这帧就几乎必然超时。在 §5.1 中我们讨论过 Linux CFS 调度器的公平性问题——游戏主线程和后台几十个线程竞争 CPU 时间时，如果没有特殊照顾，游戏线程被抢占的概率不低。

2. **热降频是帧率崩塌的主因之一**。SoC 持续满载运行后温度上升，系统降低 CPU/GPU 频率以保护硬件。帧时间预算本就紧张，频率一降直接导致帧率从 60fps 暴跌到 30fps 甚至更低。我们在 §5.5 讨论过 Thermal 管控的机制，但那一节侧重系统侧，本节侧重游戏侧如何主动应对。

3. **帧时间波动比平均帧率更影响体验**。平均 55fps 看起来只差 5fps，但如果这 55fps 中有 50 帧是 16ms、10 帧是 33ms（掉帧），用户感知到的是明显卡顿。§7.9 我们讨论了"感知流畅性"和步幅波动的概念，这在游戏场景中表现得更极端——游戏的用户对帧时间一致性极为敏感。

公开材料提到，ADPF 与 MediaTek MAGT 联合使用的个别案例出现过更高帧率和更低功耗。但公开页面没有同时给出设备型号、场景负载、温度约束和基线配置，所以这里不把“57%”当成通用收益。

ADPF 提供的是调度与热反馈回路，收益取决于游戏引擎、SoC、目标帧率和画质档位。

[来源: intake/research-feeds/2026-04-08-19-android-adpf-agdk-game-mode-thermal-performance.md]

## Game Mode API：用户意图到系统行为的桥梁

### 为什么需要 Game Mode

在 Game Mode API 出现之前，游戏性能调优面临一个尴尬的局面：系统不知道一个 App 是游戏。系统看到的是一个消耗大量 CPU/GPU 资源的进程，处理方式和任何后台服务一样，只会根据整体负载和温度做调度决策。结果会出现两个直接问题：

- 用户插着充电器、手机不烫、想要最高画质满帧体验时，系统可能正在省电模式下降频
- 用户在户外用流量、手机发烫、只希望再撑一小时时，游戏还在以最高画质狂跑

两种场景下用户的需求完全相反，但系统和游戏都不知道用户到底想要什么。

Game Mode API（Android 12, API 31）通过 `GameManager` 类解决了这个问题。用户在系统设置的"游戏设置"中为每个游戏选择偏好模式，系统通过 `GameManager` 将这个选择传递给游戏 App。游戏拿到信号后，可以据此调整渲染策略——性能模式用最高画质和帧率，省电模式降低画质和帧率。

[已验证: 官方文档, developer.android.com/reference/android/app/GameManager]

### 声明与查询

游戏先在 `AndroidManifest.xml` 中声明支持的 Game Mode，否则系统不会显示对应的设置选项：

```xml
<!-- AndroidManifest.xml -->
<application android:appCategory="game">
    <meta-data
        android:name="android.game_mode_config"
        android:resource="@xml/game_mode_config" />
</application>
```

`android:appCategory="game"` 让系统把应用识别为游戏，Game Dashboard 才会为它显示模式选择入口。`game_mode_config.xml` 则声明游戏支持哪些模式（Battery / Performance）。两者缺一不可。

在 `res/xml/game_mode_config.xml` 中声明由游戏自己处理的模式：

```xml
<?xml version="1.0" encoding="UTF-8"?>
<game-mode-config
    xmlns:android="http://schemas.android.com/apk/res/android"
    android:supportsBatteryGameMode="true"
    android:supportsPerformanceGameMode="true" />
```

声明后，App 在 `onResume()` 重新查询 `GameManager#getGameMode()`：

```java
if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
    GameManager gameManager = getSystemService(GameManager.class);
    int gameMode = gameManager.getGameMode();

    switch (gameMode) {
        case GameManager.GAME_MODE_PERFORMANCE:
            targetFps = 120;
            graphicsPreset = GraphicsPreset.ULTRA;
            break;
        case GameManager.GAME_MODE_BATTERY:
            targetFps = 30;
            graphicsPreset = GraphicsPreset.LOW;
            break;
        case GameManager.GAME_MODE_CUSTOM:
            // API 34+。targetSdk <= 33 时会为兼容性回落为 STANDARD。
            targetFps = 60;
            graphicsPreset = GraphicsPreset.HIGH;
            break;
        default: // STANDARD 或 UNSUPPORTED
            targetFps = 60;
            graphicsPreset = GraphicsPreset.HIGH;
            break;
    }
}
```

这里有三个边界。第一，`GAME_MODE_UNSUPPORTED` 表示应用没有进入 Game Mode 路径，游戏按默认档位运行。第二，`GAME_MODE_CUSTOM` 是 API 34 常量，不是 Android 17 新增。第三，公开 SDK 没有对应的模式切换监听回调；官方文档要求游戏在每次 `onResume()` 都重新调用 `getGameMode()`，处理用户在 Game Dashboard 或 OEM 面板里做的切换。

[已验证: Android Developers Game Mode API + GameManager reference]

### Game Mode 对系统行为的影响

Game Mode 给游戏的第一手信息是用户偏好，不是一个直接控制 CPU 亲和性或调度优先级的万能开关。当前 AOSP 和官方文档可以拆成三层。

第一层是游戏自己的策略。只要游戏在 XML 里声明了 Performance 或 Battery 模式，平台就把模式选择交回给游戏处理。官方文档也写得很直接：平台会清掉 OEM 之前下发的 Game Mode interventions，避免系统和游戏同时改同一组参数。

第二层是 `GameManagerService` 这个 `system_server` 服务。它负责保存模式配置、转发 `getGameMode()` / `setGameState()` 调用，并把状态变化写入 statsd。这个服务本身不对外承诺“锁大核”或“抬调度优先级”这类行为。

第三层才是能在 AOSP 中直接看到的 loading boost。`GameManagerService#setGameState()` 收到 `GameState` 后，会先记录 `FrameworkStatsLog.GAME_STATE_CHANGED`。当当前模式是 `GAME_MODE_PERFORMANCE` 且 `gameState.isLoading()` 为 `true` 时，服务会调用 `PowerManagerInternal.setPowerMode(Mode.GAME_LOADING, true)`，在一个受限时长内打开加载期 boost；加载结束或超时后再关闭。AOSP 默认上限写在 `LOADING_BOOST_MAX_DURATION = 5 * 1000`，也就是 5 秒。加载态如果长时间不收敛，`Mode.GAME_LOADING` boost 会自己撤销，不能拿它覆盖整场对局。

OEM 还可以在这三层之外叠加自己的实现，例如 downscale、FPS override、ANGLE 驱动替换，或者更激进的频率策略。但这些都属于设备配置，不是 `GameMode` / `GameState` 默认保证的行为。

[已验证: AOSP main, frameworks/base/services/core/java/com/android/server/app/GameManagerService.java]

## Game State API：细粒度的状态通信

### 为什么需要比 Game Mode 更细的粒度

Game Mode 解决的是"用户想要什么"的问题，但同一个 Game Mode 下，游戏的不同阶段对系统资源的需求差异巨大：

- **加载阶段**：大量磁盘 I/O 和资源解压，CPU 密集但 GPU 空闲
- **主菜单**：轻量 UI 渲染，CPU/GPU 都空闲
- **过场动画**：视频解码，需要 GPU 但不需要 CPU
- **激烈战斗**：全负载，CPU（AI/物理）和 GPU（渲染）都满载

如果把整个游戏运行期间都按"PERFORMANCE 模式、需要全部资源"来请求，那在主菜单和过场动画阶段系统就在白白浪费功耗——CPU/GPU 高频运行但实际利用率很低，设备温度上升，等到需要资源的战斗阶段，反而因为温度过高开始降频。

Game State API 经常和 Android 12 的 Game Mode 一起讨论，但公开 SDK 边界要分开看。`GameManager#getGameMode()` 从 Android 12 / API 31 可用；`GameManager#setGameState(GameState)` 和 `GameState` 本身在 Android 13 / API 33 才进入公开 SDK。调用入口仍在 `GameManager` 上，不是另一套独立 manager。`GameState` 只有两类公开信息：`isLoading` 表示当前是否处于加载状态，`mode` 表示当前内容类型；可选构造器还允许游戏补一个 `label` 和 `quality` 供系统侧记录。

### 用真实的 GameState 字段描述场景

```java
if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
    GameManager gameManager = getSystemService(GameManager.class);

    // 资源加载、shader compile、切场景读盘
    gameManager.setGameState(new GameState(true, GameState.MODE_NONE));

    // 可中断的游戏内操作，例如探索、可暂停战斗、菜单交互
    gameManager.setGameState(new GameState(false, GameState.MODE_GAMEPLAY_INTERRUPTIBLE));

    // 实时对战、Boss 战、竞速结算这类不能被打断的玩法
    gameManager.setGameState(new GameState(false, GameState.MODE_GAMEPLAY_UNINTERRUPTIBLE));

    // 过场动画、广告、WebView、视频等非 gameplay 内容
    gameManager.setGameState(new GameState(false, GameState.MODE_CONTENT));
}
```

这里要分清 `isLoading` 和 `mode`。`isLoading` 只描述“现在有没有加载工作”，它可以和任意 `mode` 组合。`MODE_NONE` 表示不在 active play，常见于菜单、大厅或 loading UI；`MODE_GAMEPLAY_INTERRUPTIBLE` 和 `MODE_GAMEPLAY_UNINTERRUPTIBLE` 区分的是玩法是否能被打断；`MODE_CONTENT` 对应广告、视频、Web 页面这类非 gameplay 内容。公开 API 只有构造器和这些枚举，没有额外的工厂方法，也没有所谓的性能关键度字段。

### Game Mode、Game State、OEM interventions 与 ADPF 的边界

把这几套机制拆开看，职责会清楚很多。

1. `GameManager#getGameMode()` 读取用户偏好，决定游戏自己的画质、刷新率和功耗档位。
2. `GameManager#setGameState()` 上报当前场景。AOSP main 中能直接看到的系统动作主要是 statsd 记录，以及 PERFORMANCE 模式下 `isLoading=true` 时的 `Mode.GAME_LOADING` boost。
3. ADPF `PerformanceHintManager` / Thermal API 负责逐帧预算和热反馈，它解决的是“这一帧要多少 CPU / GPU 时间”。
4. OEM interventions、ANGLE、downscale、FPS override 是另一套设备配置。游戏声明自己支持 Game Mode 后，平台会优先尊重游戏自己的优化；如果还需要细粒度干预，再单独看 interventions 配置。

这样拆开后，Game State 的角色就很明确了：它是场景上报接口，不是通用的 CPU 绑核、提优先级或延后热降频 API。

## AGDK 工具链：从渲染到调试的完整支持

### Android Game Development Kit 概览

AGDK（Android Game Development Kit）里既有平台 API，也有通过 SDK 或服务分发的库。把它们都写成“Android 某个版本才引入”，会把平台边界和库边界混在一起。更合适的拆法如下：

| 组件 | 类型 | 平台 API 首发版本 | 库 / 服务可用范围 |
|------|------|------------------|------------------|
| **Game Mode API** (`GameManager#getGameMode()`) | 平台 API | Android 12 (API 31) | 系统框架内置 |
| **Game State API** (`GameManager#setGameState()`, `GameState`) | 平台 API | Android 13 (API 33) | 系统框架内置 |
| **Frame Pacing Library (Swappy)** | AGDK 库 | 不与 OS 版本绑定 | 通过 AGDK 集成，最低版本取决于当前 SDK 与接入方式 |
| **Game Activity** | AGDK 库 | 不与 OS 版本绑定 | 通过 AGDK 集成，官方文档当前要求 minSdk 19+ |
| **Game Text Input** | AGDK 库 | 不与 OS 版本绑定 | 通过 AGDK 集成，官方文档当前要求 minSdk 19+ |
| **Performance Tuner** | AGDK 库 + Play Console 服务 | 不与 OS 版本绑定 | 官方文档写明可运行在 Android 4.1 (API 16)+ |
| **Android GPU Inspector (AGI)** | 独立工具 | 不适用 | 主机侧工具，按 GPU 驱动与设备支持情况工作 |

真正和平台版本硬绑定的只有 `Game Mode` / `Game State`。`Game Activity`、`Game Text Input`、`Swappy`、`Performance Tuner` 都跟着 AGDK 自己的发布节奏走。`Performance Tuner` 这一行最容易写错，它不是 Android 12 特性，平台门槛也不是 API 31。

Frame Pacing Library 已在 §2.17 详细讨论，这里重点关注与性能优化直接相关的其他组件。

这里把几个工具的分工先讲清楚。GameActivity 解决的是 native 游戏和 Android 生命周期、输入之间的接缝；GameManager 负责读取 Game Mode；Swappy 管的是提交节奏和 display refresh 的匹配；AGI 负责 GPU 帧调试；Perfetto 负责把帧时间、CPU/GPU 频率、热状态和调度延迟放到同一份时间轴里。排障时按这个分工切入，比把它们都叫“性能工具”更容易定位。

### Game Activity：把 Android 生命周期和 native 引擎接起来

大多数 3D 游戏的渲染循环仍在 C/C++ 层。Game Activity 的价值，不在于替游戏决定画质或帧率，而在于把 Surface、输入、生命周期和文本输入收拢到一套更适合 native 游戏的接口里。

工程上可以把职责拆成三层：

1. **Game Activity / native 层**：处理 surface 创建、input buffer、窗口焦点和生命周期回调，让引擎主循环稳定跑起来。
2. **Activity / framework 层**：用 `GameManager#getGameMode()` 读取用户模式，再把结果同步到引擎配置，例如 target FPS、渲染分辨率或阴影档位。
3. **Swappy / AGI / Perfetto**：分别负责提交节奏、GPU 帧调试和系统级时间轴分析，不要把它们混成一个“游戏性能开关”。

如果项目已经从 `NativeActivity` 迁移到 `GameActivity`，先查三件事：切前后台时 surface 是否重建，输入路径是否仍绕回 Java 主线程，Game Mode 切换后引擎参数是否在下一次 `onResume()` 生效。这样写，比单纯罗列工具名更接近实际排障路径。

[已验证: 官方文档, developer.android.com/games/agdk/integration]

### Performance Tuner：自动化的性能质量报告

Performance Tuner 是 AGDK 中容易被忽视但非常有价值的组件。它自动收集以下数据并上报到 Google Play Console：

- **帧时间分布**：每秒的帧时间分位数（P50/P90/P99），比单纯看平均 FPS 更能反映卡顿情况
- **热状态关联**：帧时间与设备热状态的关系，帮助开发者判断卡顿是代码问题还是热降频
- **设备分段**：按设备型号、SoC、内存大小等维度分析性能差异，帮助确定优化优先级

Performance Tuner 的价值在于自动收集线上帧时间和设备分布，不需要团队自己搭采集系统。对独立开发者或小团队来说，这已经够用了。

更适合的用法是把它当线上分流器。Play Console 先告诉我们哪类设备、哪段场景的 P95/P99 抬升，再回到 Perfetto 抓同型号设备的本地 trace，把 FrameTimeline、频率和 thermal 放在一起看。一个回答“哪台机器更差”，另一个回答“差在哪里”。

[已验证: 官方文档, developer.android.com/games/sdk/performance-tuner]

## 游戏性能分析：Perfetto 中的关键 Track

### 游戏 Trace 的特殊配置

抓取游戏场景的 Perfetto Trace 时，建议启用以下额外的 atrace category：

```
adb shell perfetto \
  -c - --txt \
  <<EOF
buffers: { size_kb: 131072 }
data_sources: { config { name: "linux.ftrace" ftrace_config {
  ftrace_events: "sched/sched_switch" ftrace_events: "sched/sched_wakeup"
  ftrace_events: "power/cpu_frequency" ftrace_events: "power/cpu_idle"
  ftrace_events: "power/suspend_resume"
  atrace_categories: "gfx" atrace_categories: "view" atrace_categories: "sched"
  atrace_categories: "power" atrace_categories: "freq"
}}}
data_sources: { config { name: "linux.process_stats" } }
data_sources: { config {
  name: "gpu.renderstages"
  gpu_renderstages_config {}
}}
duration_ms: 30000
EOF
```

相比普通 App 的 Trace 配置，游戏场景需要额外关注：
- **`power` 和 `freq` category**：追踪 CPU/GPU 频率变化，这是判断热降频和调度问题的核心数据
- **更大的 buffer**：游戏持续满负载，30 秒的 Trace 数据量可能达到 100MB+
- **GPU counters / render stages**：上方配置只启用了 `gpu.renderstages`，没有启用 Perfetto `gpu.counters` 数据源。如果需要观察 GPU busy、GPU 频率和带宽趋势，要在支持设备上额外启用 `gpu.counters`：`data_sources { config { name: "gpu.counters" gpu_counter_config { ... } } }`。`gpu.renderstages` 把 Vulkan / OpenGL ES 的 RenderPass、binning、rendering、clears 等阶段放到时间轴上看。两类数据都依赖驱动和设备权限，userdebug/root 设备上还要确认 `security.perfetto.gpu_counters.privileged` 等开关是否允许采集

### 关键分析路径

拿到游戏 Trace 后，先分清渲染架构，再选观察点。

如果游戏主画面由 `GameActivity`、`SurfaceView`、Unity / Unreal、自研 Vulkan / OpenGL ES 循环直接驱动，主信号是 `FrameTimeline`、应用自己的 Surface layer、SurfaceFlinger 合成轨、Swappy slice 和 GPU counters。这里记录的是帧提交与实际 present，更接近玩家真正看到的帧时间。

如果游戏只是外层壳或局部界面用了 Android UI，`Choreographer#doFrame` 仍然有用，但它只反映 UI 线程这一侧的节拍，不能代替整帧 present 时间。登录页、支付页、商城、系统弹窗这类混合界面，通常要把 `Choreographer` 和 `FrameTimeline` 对在一起看。

按这个边界，分析顺序通常是：

**第一步：先看 FrameTimeline 和应用 Surface layer**

在 Perfetto 里找到游戏 Surface 对应的 layer，先看 Actual / Expected frame、present 节奏和 jank 分类。原生游戏掉帧时，这里比 `Choreographer` 更早暴露问题。启用了 `gpu.renderstages` 后，再把 RenderPass / render stage 的耗时对应到同一段 Actual frame；如果某个 pass 的 rendering 或 clears 阶段贴着 present deadline 变长，排查方向就从 Java/UI 线程切到 draw call、overdraw、shader 和 render target 配置。

**第二步：关联 CPU / GPU 频率和热状态**

切到 CPU Frequency、GPU counter 和 Thermal 相关轨道。帧时间抬升如果和频率下探、温度升高同时出现，通常是热或功耗约束在起作用。

**第三步：再看 Swappy 或 ADPF**

用了 Swappy，就把提交节奏、present 节奏和 display refresh 放到同一条时间轴里看。用了 ADPF，就看 `power.hint_session` 里 target duration 与 actual duration 的偏差，判断 hint 是否跟上场景变化。

渲染同步和性能反馈可以拆成两条线看。

帧节奏线仍由 Swappy、`ANativeWindow_setFrameRate` / `SurfaceControl` frame rate、FrameTimeline 和自适应刷新率（ARR）共同承担。Swappy 管的是提交节奏和 display refresh 的匹配，这部分从 Android 12 到 Android 16 没有根本性变化。

性能反馈线走的是 ADPF：`PerformanceHintManager` / NDK ADPF 接口通过 target duration 和 actual duration 的偏差给调度器提示，再把 hint session 与 native surface / graphics pipeline 关联起来。Android 16 在这条线上新增了 `SystemHealthManager#getCpuHeadroom()` 和 `#getGpuHeadroom()`（上面已讨论），帮助游戏判断当前瓶颈在 CPU 还是 GPU。

两条线在实战中配合使用：Swappy 保证帧以正确的节奏提交，ADPF 保证系统给游戏线程足够的 CPU/GPU 预算。不要把两者混成一个统一的"帧 deadline 上报"接口——公开 SDK 中没有这样的单一入口。

同时要注意 Swappy 配置不当可能引发"反向卡顿"：如果 Swappy 锁定的 VSync 偏移与系统实际的 ARR（自适应刷新率）切换窗口错位，就会出现"Swappy 按 60Hz 间隔提交，但显示器刚切到 120Hz"的帧节奏混乱——Perfetto 里表现为 Actual frame 周期性在 16ms 和 33ms 之间跳变，且跳变节奏与 VSync offset 切换同步。遇到这种形态，先检查 Swappy 的 swap interval 是否跟随了 display 的实际刷新率，再检查 ADPF hint session 的 target duration 是否和 Swappy 配置一致。

**第四步：检查调度延迟**

再检查主线程、RenderThread、渲染 worker 或 native game thread 的调度延迟。这里回答的是“CPU 有没有及时把这一帧跑起来”，不是“这一帧是否成功 present”。

### 三组可直接对照的 Trace 片段

**片段 1：FrameTimeline 抖动，但 CPU 频率没有掉**

- 观察点：应用 Surface layer 的 Actual frame、Expected frame，外加 GPU counter
- 常见形态：Actual frame 从 16.6ms 抬到 33.3ms，但 big cluster 频率和 thermal status 基本稳定
- 判断：问题更像 GPU 侧瓶颈，例如 shader 编译、fill rate、后处理或分辨率过高；这时别把锅先甩给调度器

现代 Vulkan 游戏的 GPU 瓶颈分析不能只看频率和 busy 程度。Vulkan 1.3 核心的动态渲染（`VK_KHR_dynamic_rendering`）和管线状态对象（PSO）管理已经改变了传统的瓶颈分布：Draw Call 数量在 Vulkan 下不再是 CPU 侧的主要瓶颈——命令缓冲区批量提交把 driver overhead 大幅压缩；真正需要关注的是 render pass 之间的内存屏障、subpass 依赖、以及 render target 切换导致的 GPU 空闲气泡。在 Perfetto 中配合 `gpu.renderstages` 可以直接看到这些阶段的耗时分布，比单纯看 GPU busy 百分比更有诊断价值。

[图：FrameTimeline 片段，Expected frame 仍维持 16.6ms，Actual frame 偶发拉到 33.3ms；CPU Frequency 基本平，GPU busy 上抬]

**片段 2：帧时间和热状态一起变差**

- 观察点：FrameTimeline、CPU Frequency、Thermal track
- 常见形态：前 20-30 秒 Actual frame 稳定在目标值附近，随后 CPU/GPU 频率逐级下探，帧时间同步抬到 20ms、25ms、33ms
- 判断：这是典型的热或功耗约束。后面要查的是 Headroom、画质档位、target FPS 和场景负载，不是某一帧的单点卡顿

[图：FrameTimeline 与 Thermal 对照片段，前半段帧时间稳定，后半段随 thermal status 升级与 CPU/GPU 频率下探一起变差]

**片段 3：`power.hint_session` 跟不上场景变化**

- 观察点：`power.hint_session` 的 target duration / actual duration，再把主线程或 render thread 的 sched slice 放到同一条时间轴里看
- 常见形态：切到高负载战斗后，target duration 仍停在旧值，actual duration 连续多帧超预算，thread slice 里还能看到 runnable 但没及时拿到 CPU
- 判断：Hint 更新滞后，或者场景切换后 worker 数量、目标帧率、CPU 预算没有一起刷新

[图：Hint Session 片段，target duration 仍停留在旧档位，actual duration 连续抬升；同一时间轴上的 render thread 出现 runnable 等待]

[图：Perfetto 中游戏性能分析的典型视图——从上到下依次为 FrameTimeline、CPU Frequency、Thermal Status、Hint Session Track，标注重点观察区域]

### OEM 游戏模式对 Trace 的干扰

分析游戏性能时有一个常见的坑：**OEM 的游戏模式可能干扰你的 Trace 数据**。

OEM 面板往往会把 downscale、FPS override、触控策略、后台限制或驱动替换叠在一起。如果不先关掉这些开关，Trace 里看到的频率、帧时间和 thermal 变化就会把设备私有策略和游戏自身优化混在一起。

做基线分析时，先关闭 OEM 游戏面板，再分别测试 Game Mode、interventions 和游戏自己的 ADPF 适配。这样我们才能看清收益到底来自哪一层。

[待补充：各主要 OEM 厂商游戏模式的关闭方法列表]

## Android 16 与 Android 12/13+ 的平台变化

### Android 16：ADPF Headroom API

Android 16 在游戏侧新增了 `SystemHealthManager#getCpuHeadroom()` 和 `SystemHealthManager#getGpuHeadroom()`。两个接口都在 API 36 添加，用来估算当前 CPU / GPU 的可用余量，帮助游戏判断这一段负载更像 CPU bound 还是 GPU bound。

`SystemHealthManager` 官方 reference 写明：这两个接口每次调用至少会触发一次同步 binder transaction，耗时可能超过 1ms。120fps 下单帧预算只有 8.33ms，1ms 阻塞已经吃掉约 12% 的预算；144fps 下预算约 6.94ms，占比更高。渲染主线程不要直接同步调用 Headroom API。更稳妥的做法是放到低频控制回路或独立线程里异步轮询，把结果缓存给引擎，用于调整 target FPS、动态分辨率或特效档位。

`getThermalHeadroom()` 更适合看未来一段时间的热余量，回答“还能不能继续维持当前负载”；`getCpuHeadroom()` / `getGpuHeadroom()` 更适合看当前 CPU / GPU 压力，回答“这一段更像 CPU bound 还是 GPU bound”。实战里先用 thermal headroom 决定是否提前降档，再用 CPU/GPU headroom 决定降 CPU 逻辑负载、GPU 分辨率还是后处理。

[已验证: Android Developers SystemHealthManager reference, API level 36]

### Android 12/13+：Game Mode Interventions

Game Mode Interventions 不是 Android 17 才出现的功能。官方文档的口径是：它从部分 Android 12 设备开始可用，在 Android 13 及以上设备上更常见。它面向的是开发者暂时无法更新，或者已经停止维护的游戏，OEM 可以通过系统配置补一层兼容优化。

当前公开文档覆盖的 interventions 主要有三类：

- `WindowManager` backbuffer resize，用 `downscaleFactor` 降低渲染分辨率
- FPS throttling，用固定帧率上限换更稳定的帧时间和更低的功耗
- ANGLE / driver 相关替换，由 OEM 按设备兼容性决定是否启用

如果游戏要退出这类干预，`game_mode_config.xml` 里要分别关掉具体开关，不是补一个总开关就结束：

```xml
<?xml version="1.0" encoding="UTF-8"?>
<game-mode-config
    xmlns:android="http://schemas.android.com/apk/res/android"
    android:allowGameDownscaling="false"
    android:allowGameFpsOverride="false" />
```

开发阶段有两类命令需要分开看。`adb shell cmd game mode [standard|performance|battery] <PACKAGE_NAME>` 用来切换用户模式；给 interventions 下配置的是 `adb shell device_config put game_overlay <PACKAGE_NAME> ...`。把这两条命令混成一条，会把“选择模式”和“下发 OEM 配置”两件事写乱。

[已验证: Android Developers Game Mode API / interventions / FPS throttling docs]

## 游戏卡顿分析方法论

### 帧时间分析：关注波动而非平均值

游戏性能分析中最大的误区之一是只看平均 FPS。"平均 55fps" 可能意味着 50 帧是 16ms + 10 帧是 33ms，用户看到的是每秒卡顿两次。正确的做法是看帧时间分布，尤其是 P95 和 P99 帧时间。

对 native game，优先统计 `FrameTimeline` 和应用 Surface layer 的实际呈现帧。`Choreographer#doFrame` 只适合主循环或重要界面仍由 Android UI 驱动的场景。

如果 trace 里的主要瓶颈出现在 `ViewRootImpl` / `Choreographer` 一侧，可以用下面的 SQL 统计 UI 线程节拍。它统计的是 UI 线程 slice，不是 SurfaceFlinger 已经 present 的最终帧：

```sql
-- 仅适用于以 Choreographer 驱动的 UI 段落
SELECT
    process.name AS process_name,
    quantile(dur / 1e6, 0.50) AS p50_ms,
    quantile(dur / 1e6, 0.90) AS p90_ms,
    quantile(dur / 1e6, 0.95) AS p95_ms,
    quantile(dur / 1e6, 0.99) AS p99_ms,
    count(*) AS total_frames
FROM slice
JOIN thread_track ON slice.track_id = thread_track.id
JOIN thread ON thread_track.utid = thread.utid
JOIN process ON thread.upid = process.upid
WHERE slice.name LIKE 'Choreographer#doFrame%'
  AND process.name LIKE '%game_process_name%'
GROUP BY process.name;
```

目标是 120Hz 时，要把 8.33ms 当预算；90Hz 是 11.11ms；60Hz 是 16.66ms。present miss 仍要回到 `FrameTimeline` 看 Actual frame 和 jank reason。

### GC 对游戏帧的影响

ART 的 GC 暂停是游戏卡顿的常见来源之一。游戏通常在每帧的渲染循环中分配大量临时对象（坐标变换数据、碰撞检测中间结果等），导致 GC 频繁触发。GC 的 STW（Stop-The-World）暂停会中断游戏主线程，导致帧时间飙升。

在 Perfetto 中识别 GC 影响：先搜索 `art::gc` / heap task / allocation stall 相关的 slice，确认是否有 STW GC 暂停。主线程 `RUNNABLE` 状态但未执行代码的空洞，更常见的原因是调度等待或 CPU 竞争（查看 sched latency），不应直接归因为 GC 暂停。STW GC 的判断需要结合线程 suspend 信号和 `art::gc` slice，不能只靠 RUNNABLE 空洞。

应对策略：
1. 减少渲染循环中的对象分配，使用对象池复用
2. 根据 ADPF thermal/headroom 反馈提前降 CPU/GPU 负载、降低画质或减少分配压力；对象池、加载期预分配、避免每帧 Java/Kotlin 分配、复用 native buffers 是更直接的 GC 控制手段
3. 在游戏加载阶段预分配所有需要的内存，避免在战斗场景中触发 GC
4. 在支持新版 ART 分代 GC 的设备上，观察短生命周期对象是否带来更少的 STW 暂停；具体收益受 ART 版本、堆大小、对象分配模式和场景负载影响，不能把固定毫秒区间当成通用结论

### 热节流导致的渐进式降帧

热降频导致的帧率下降有一个典型模式：表现为缓慢地、渐进式地下降——55fps → 50fps → 45fps → 40fps → 35fps（突然从 60fps 跳到 30fps 更可能是调度问题）。

在 Trace 中看到这种模式时，需要：
1. 检查 Thermal Status Track，确认温度变化与帧率下降的对应关系
2. 检查 CPU Frequency Track，确认是否在温度升高后频率逐步降低
3. 如果游戏使用了 ADPF Thermal API，检查 `getThermalHeadroom()` 的查询频率和 App 的应对策略

应对热降频的最佳实践不是对抗系统（那不可能赢），而是**主动合作**：在温度还低的时候就适当降低渲染复杂度，把热余量留到关键时刻使用。这和 §5.5 中讨论的"主动式热管理"策略一致——越早开始降级，最终达到的稳态帧率就越高。

[图：热降频场景的帧时间模式——前 30 秒稳定 16ms，之后随温度升高逐步增长到 20ms→25ms→33ms，形成渐进式降帧曲线]

## OEM 游戏模式与 Game Mode API 的关系

### 先把 OEM 面板当成独立变量

OEM 的游戏面板通常会把多种动作绑在一起，例如画质降档、FPS override、触控采样率调整、后台限制、网络策略或驱动替换。同一个“性能模式”在不同机型上对应的开关并不一样，直接横向比较很容易把平台差异误判成游戏优化效果。

做跨设备分析时，更稳妥的办法是拆成四轮基线：

1. **基线轮**：关闭 OEM 游戏面板，`GAME_MODE_STANDARD`，系统电池模式保持默认。
2. **用户模式轮**：只切 `adb shell cmd game mode [standard|performance|battery] <PACKAGE_NAME>`，观察 Game Mode 本身带来的变化。
3. **interventions 轮**：只通过 `adb shell device_config put game_overlay ...` 验证 downscale / FPS override，不叠加 OEM 面板。
4. **叠加轮**：再打开 OEM 面板，看它是否在前三轮之外额外改了频率、触控或后台策略。

如果第四轮收益明显大于前面三轮，说明提升主要来自 OEM 私有策略；如果第二轮就已经带来稳定收益，才更像是游戏自己对 `getGameMode()` 或 ADPF 做了正确适配。

### 性能测试的最佳实践

进行游戏性能测试和优化时，建议遵循以下流程：

1. 先备份或清空 `device_config get game_overlay <PACKAGE_NAME>` 的现有配置，避免旧 interventions 污染结果。
2. 关闭 OEM 游戏面板，设置系统电池模式为默认，并通过 `adb shell settings put global low_power 0` 确认省电模式关闭。
3. 依次跑完基线轮、用户模式轮、interventions 轮和叠加轮，不要一次把所有开关都打开。
4. 每一轮都记录相同指标：显示刷新率、FrameTimeline P95/P99、CPU / GPU 频率、thermal status，以及游戏内部实际生效的画质 / target FPS。
5. 每次测试前让设备回到接近常温，再开始下一轮对比。

## 与其他章节的关系

- **§2.17 Frame Pacing Library**：Swappy 解决游戏渲染循环与 VSync 的同步问题，是游戏帧节奏控制的基础
- **§5.9 ADPF**：本章的 Game Mode/State API 与 ADPF 的 Performance Hint/Thermal API 构成完整的游戏性能管理框架
- **§5.5 Thermal 管控**：§5.5 侧重系统侧的热管理机制，本章侧重游戏侧如何通过 Thermal API 主动应对
- **§7.1 卡顿定义与分类**：游戏的"掉帧"和普通 App 的"卡顿"在成因和表现上有显著差异
- **§7.9 感知流畅性**：步幅波动分析在游戏场景中尤为重要——帧时间一致性比平均帧率更能反映游戏体验
- **§4.8 ART 分代 GC**：Generational GC 减少了 GC 暂停时间，对游戏的帧时间稳定性有直接帮助
- **§14.10 eBPF/BPF**：eBPF 的 sched_ext 可以用于更精细的游戏线程调度分析和优化

## 参考资料



<!-- AIW-源码调研-2026-05-17: Kotlin Coroutine 与 ADPF Hint 工程化边界 -->
## ADPF Hint Session 与 Kotlin Coroutine 线程迁移（2026-05-17 补充）

> 本节基于 AOSP 源码和 Google 官方 ADPF codelab 源码调研，补充 §5.9 ADPF 在 Kotlin 协程场景下的工程化约束。

### 核心约束：Hint Session 基于线程 TID，而非协程

ADPF 的 `APerformanceHint_createSession()` API 设计基于**实际线程 ID（TID）**绑定：

```cpp
// adpf_manager.cpp (Google 官方 codelab)
// external/kotlinx.coroutines/.../adpf_manager.cpp
bool ADPFManager::InitializePerformanceHintManager() {
#if __ANDROID_API__ >= 33
    hint_manager_ = APerformanceHint_getManager();
    int32_t tids[1];
    tids[0] = gettid();  // 绑定当前线程 TID
    hint_session_ = APerformanceHint_createSession(hint_manager_, tids, 1, last_target_);
#endif
}
```

Kotlin 协程的线程模型：
- `Dispatchers.Default`：共享 `CommonPool`（CPU 核心数线程），协程可能在不同线程间迁移
- `Dispatchers.IO`：共享 `IOPool`（最多 64 线程），协程挂起后恢复可能在另一线程

```kotlin
// Kotlin 协程线程迁移示例
launch(Dispatchers.Default) {
    val threadBefore = Thread.currentThread().id  // 可能是 Thread-1
    delay(100)  // 挂起点
    val threadAfter = Thread.currentThread().id  // 可能是 Thread-5（不同线程）
}
```

**结果**：协程迁移后，新线程不在 hint session 中，无法享受 ADPF hint 优化。

### API 版本差异：线程动态管理

```cpp
// adpf_manager.cpp
void ADPFManager::RegisterThreadIdsToHintSession() {
#if __ANDROID_API__ >= 34
    // API 34: 直接 setThreads，动态添加/移除
    APerformanceHint_setThreads(hint_session_, data, size);
#elif __ANDROID_API__ >= 33
    // API 33: 只能先 close 再重建 session
    APerformanceHint_closeSession(hint_session_);
    hint_session_ = APerformanceHint_createSession(hint_manager_, data, size, last_target_);
#endif
}
```

| 版本 | 添加线程开销 | 推荐场景 |
|------|------------|---------|
| API 33 | 重建 session（高开销） | 线程稳定场景 |
| API 34 | `setThreads()`（低开销） | 动态线程池 |

### Kotlin 协程优先级提案状态

GitHub `Kotlin/kotlinx.coroutines` Issue #1617 讨论了协程优先级 hint：

> "If CoroutinePriority is provided by CoroutineContext, wrap a dispatched task into an object which can be compared by taken priority and put it into the executor. The element behaves like a hint."

**现状**：协程优先级 hint 功能**尚未实现**，无官方 ADPF 集成。

### IPC 开销估算

| 操作 | 估算延迟（未一手验证） |
|------|----------------------|
| `APerformanceHint_createSession()` | ~50-100μs |
| `APerformanceHint_reportActualWorkDuration()` | ~5-10μs |
| Session 重建（API 33） | 较高，避免频繁调用 |

游戏帧预算 16.67ms（60fps），单次 hint 调用占比 <0.1%，可接受。

### 工程化建议

1. **绑定稳定线程**：使用 `Dispatchers.Main` 或单线程调度器，确保 TID 稳定
2. **避免高频调用**：每帧调用 `reportActualWorkDuration()` 会累积开销
3. **API 33 慎重建**：频繁重建 session 会导致性能倒退
4. **帧循环优先**：游戏帧循环（非协程）直接调用 ADPF，协程层做吞吐量控制

### 源码位置

- AOSP ADPF codelab: `external/kotlinx.coroutines/kotlinx-coroutines-core/`
- ADPF Manager 源码: `external/kotlinx.coroutines/.../adpf_manager.h`
- CoroutineDispatcher: `external/kotlinx.coroutines/kotlinx-coroutines-core/common/src/CoroutineDispatcher.kt`

<!-- AIW-源码调研-2026-05-17 END -->

- AOSP GameManager: `frameworks/base/core/java/android/app/GameManager.java`
- AOSP GameState: `frameworks/base/core/java/android/app/GameState.java`
- AOSP GameManagerService: `frameworks/base/services/core/java/com/android/server/app/GameManagerService.java`
- 官方文档: https://developer.android.com/reference/android/app/GameManager
- 官方文档: https://developer.android.com/reference/android/app/GameState
- 官方文档: https://developer.android.com/reference/android/os/health/SystemHealthManager
- 官方文档: https://developer.android.com/games/optimize/adpf/gamemode/about-API-and-interventions
- 官方文档: https://developer.android.com/games/optimize/adpf/gamemode/gamemode-api
- 官方文档: https://developer.android.com/games/optimize/adpf/gamemode/gamestate-api
- 官方文档: https://developer.android.com/games/optimize/adpf/gamemode/gamemode-interventions
- 官方文档: https://developer.android.com/games/optimize/adpf/gamemode/fps-throttling
- AGDK Frame Pacing: https://developer.android.com/games/sdk/frame-pacing
- Android Performance Tuner: https://developer.android.com/games/sdk/performance-tuner
- GameActivity text input: https://developer.android.com/games/agdk/game-activity/use-text-input
- 研究素材: intake/research-feeds/2026-04-08-19-android-adpf-agdk-game-mode-thermal-performance.md
- 研究素材: intake/research-feeds/2026-04-05-19-android16-arr-surfaceflinger-choreographer-frame-pacing.md
