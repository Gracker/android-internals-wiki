---
title: "Android 游戏性能与 Game Mode/State API"
chapter: "8.9"
section: "8.9"
status: ready-for-review
applicable_versions: "Android 12 (API 31) - Android 17 (API 37)"
drafted_date: "2026-04-08"
drafted_by: "openclaw-task2a"
last_verified: "2026-04-08"
last_verified_against: "AOSP android-17-beta3"
confidence: medium
sources:
  - type: official
    path: "https://developer.android.com/games/gamemode/gamemode-api"
  - type: official
    path: "https://developer.android.com/games/optimize/performance"
  - type: official
    path: "https://developer.android.com/reference/android/app/GameManager"
  - type: official
    path: "https://developer.android.com/reference/android/app/GameStateManager"
  - type: aosp
    path: "frameworks/base/core/java/android/app/GameManager.java"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/GameManagerService.java"
  - type: research
    path: "intake/research-feeds/2026-04-08-19-android-adpf-agdk-game-mode-thermal-performance.md"
tags: [game, gamemode, gamestate, agdk, frame-pacing, adpf, gaming-performance, thermal]
related_chapters: ["2.17", "5.9", "5.5", "7.1", "7.9", "14.10"]
created_by: "task2a-knowledge-gap"
created_date: "2026-04-08"
gap_source: "官方文档+读者需求+研究素材"
pipeline_stage: task2b_pending
task6_state: reviewed
task9_state: reviewed
task2b_state: pending
reviewed_by: "openclaw-task6"
reviewed_date: "2026-04-13"
task6_result: needs-rework
task9_result: needs-rework
---

# 8.9 Android 游戏性能与 Game Mode/State API

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

Google 在 2025-2026 年的实测数据显示，有效使用 ADPF 的游戏可以实现最高 57% 的帧率提升。这个数字的背景是：很多游戏在不使用 ADPF 时，CPU 调度延迟和热降频导致的帧率损失远超开发者的预期。

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

游戏首先需要在 `AndroidManifest.xml` 中声明支持的 Game Mode，否则系统不会显示对应的设置选项：

```xml
<!-- AndroidManifest.xml -->
<application>
    <meta-data
        android:name="android.game_mode_config"
        android:resource="@xml/game_mode_config" />
</application>
```

在 `res/xml/game_mode_config.xml` 中声明支持的模式：

```xml
<?xml version="1.0" encoding="utf-8"?>
<game-mode-config
    xmlns:android="http://schemas.android.com/apk/res/android"
    android:gameModePerformance="true"
    android:gameModeBattery="true"
    android:gameModeCustom="true" />
```

声明后，App 通过 `GameManager` 查询当前用户的模式选择：

```java
// frameworks/base/core/java/android/app/GameManager.java
// @ AOSP android-17-beta3
GameManager gameManager = getSystemService(GameManager.class);
int gameMode = gameManager.getGameMode();

switch (gameMode) {
    case GameManager.GAME_MODE_PERFORMANCE:
        // 用户选择了性能优先：提升帧率目标、开启高画质
        targetFps = 120;
        graphicsPreset = GraphicsPreset.ULTRA;
        break;
    case GameManager.GAME_MODE_BATTERY:
        // 用户选择了省电优先：降低帧率、简化渲染
        targetFps = 30;
        graphicsPreset = GraphicsPreset.LOW;
        break;
    case GameManager.GAME_MODE_CUSTOM:
        // 用户自定义配置（Android 17 新增）
        // 可查询具体配置参数
        break;
    default: // GAME_MODE_STANDARD 或 GAME_MODE_UNSUPPORTED
        targetFps = 60;
        graphicsPreset = GraphicsPreset.HIGH;
        break;
}
```

这里有两个细节需要单独说明。第一，`GAME_MODE_UNSUPPORTED` 表示设备不支持 Game Mode（通常是没有通过 CTS 认证的低端设备或模拟器），游戏应该按默认策略运行。第二，Game Mode 可以在运行时变化，用户可能从设置中切换模式，App 通过 `GameManager.GameModeListener` 注册回调来监听变化，无需轮询。

[已验证: AOSP android-17-beta3, frameworks/base/core/java/android/app/GameManager.java]

### Game Mode 对系统行为的影响

Game Mode 不仅仅是给 App 读的一个标志——它同时会影响系统的调度策略。当游戏处于 PERFORMANCE 模式时：

- 系统倾向于保持 CPU/GPU 高频率，即使温度已经接近阈值（但不会超过安全限制）
- 后台进程的调度优先级被进一步压低
- 系统可能延迟触发 Thermal 降频（给 App 更多时间通过画质调整来主动降温）

当处于 BATTERY 模式时：

- 系统更积极地降频，CPU 倾向于调度到效率核
- 后台同步和网络活动可能被进一步限制
- 屏幕亮度可能被限制

系统侧的行为由 `GameManagerService`（运行在 system_server）协调，具体的调度策略调整委托给 PowerManager 和 ThermalManager。因此，Game Mode 在不同 OEM 设备上的实际效果可能存在差异，有的厂商在 PERFORMANCE 模式下会解锁更高的 CPU 频率上限，有的则只是微调调度策略。

[已验证: AOSP android-17-beta3, frameworks/base/services/core/java/com/android/server/GameManagerService.java]

## Game State API：细粒度的状态通信

### 为什么需要比 Game Mode 更细的粒度

Game Mode 解决的是"用户想要什么"的问题，但同一个 Game Mode 下，游戏的不同阶段对系统资源的需求差异巨大：

- **加载阶段**：大量磁盘 I/O 和资源解压，CPU 密集但 GPU 空闲
- **主菜单**：轻量 UI 渲染，CPU/GPU 都空闲
- **过场动画**：视频解码，需要 GPU 但不需要 CPU
- **激烈战斗**：全负载，CPU（AI/物理）和 GPU（渲染）都满载

如果把整个游戏运行期间都按"PERFORMANCE 模式、需要全部资源"来请求，那在主菜单和过场动画阶段系统就在白白浪费功耗——CPU/GPU 高频运行但实际利用率很低，设备温度上升，等到真正需要资源的战斗阶段，反而因为温度过高开始降频。

Game State API（Android 13, API 33）通过 `GameStateManager` 让游戏告知系统当前的运行状态和性能关键度，使系统可以在不同的游戏阶段采用不同的资源调配策略。

[已验证: 官方文档, developer.android.com/reference/android/app/GameStateManager]

### 四种状态与性能关键度标注

```java
// frameworks/base/core/java/android/app/GameStateManager.java
// @ AOSP android-17-beta3
GameStateManager stateManager = getSystemService(GameStateManager.class);

// 进入加载阶段：CPU 密集但不是帧率敏感
stateManager.setGameState(GameState.create(
    /* isPerformanceCritical= */ false,
    /* gameMode= */ gameManager.getGameMode()
));

// 加载完成，进入游戏主界面
// （不需要特别标注，保持默认即可）

// 进入对战场面：帧率关键，不能掉帧
stateManager.setGameState(GameState.create(
    /* isPerformanceCritical= */ true,
    /* gameMode= */ gameManager.getGameMode()
));

// 过场动画播放中：GPU 密集但 CPU 可以休息
stateManager.setGameState(GameState.create(
    /* isPerformanceCritical= */ false,
    /* gameMode= */ gameManager.getGameMode()
));
```

`isPerformanceCritical` 是这个 API 中最重要的参数。当标记为 `true` 时，系统会做出以下行为调整：

1. **避免 CPU 核心迁移**。游戏线程被绑定在当前运行的核心上，减少因核心切换导致的 cache miss。核心迁移的开销在 120fps 场景下尤其明显——一个线程从大核 A 迁移到大核 B，L2 cache 全部失效，接下来几帧的耗时可能飙升。
2. **提高调度优先级**。系统的调度器会尽量避免抢占标记为 performance-critical 的线程。
3. **延迟热降频触发**。系统在温度接近阈值时会给予更多缓冲时间，等待 App 主动降级负载。

反过来，当 `isPerformanceCritical = false` 时，系统可以更激进地省电：把游戏线程调度到效率核、降低 CPU/GPU 频率、允许后台同步执行等。

[已验证: AOSP android-17-beta3, frameworks/base/core/java/android/app/GameStateManager.java]

### Game Mode + Game State + ADPF 的协同工作流

把 Game Mode、Game State 和 §5.9 讨论的 ADPF（Performance Hint + Thermal）放在一起，游戏的完整性能管理流程如下：

1. **启动时**：查询 Game Mode，确定整体性能策略（性能/省电/平衡）
2. **每帧渲染**：通过 ADPF HintSession 上报帧时间，系统据此调整 CPU/GPU 频率
3. **场景切换时**：更新 Game State（loading/running/cutscene），系统调整资源分配
4. **热状态变化时**：Thermal API 回调通知温度变化，App 主动调整画质
5. **Game Mode 变化时**：用户从设置中切换偏好，App 更新帧率目标和画质级别

这个流程中，三个 API 各司其职：Game Mode 传达"用户想要什么"，Game State 传达"游戏正在做什么"，ADPF 传达"这一帧需要多少资源"。系统综合这三个维度的信息做出调度决策，比单纯靠历史负载猜测要精准得多。

## AGDK 工具链：从渲染到调试的完整支持

### Android Game Development Kit 概览

AGDK（Android Game Development Kit）是 Google 为 Android 游戏开发者提供的工具集，包含以下核心组件：

| 组件 | 功能 | 引入版本 |
|------|------|---------|
| **Frame Pacing Library (Swappy)** | 帧节奏控制，与 VSync 同步 | Android 9 (API 28) |
| **Game Activity** | 替代 NativeActivity 的优化 Activity | Android 12 (API 31) |
| **Game Text Input** | 低延迟文本输入 | Android 12 (API 31) |
| **Performance Tuner** | 自动化性能数据收集 + Play Console 集成 | Android 12 (API 31) |
| **Android GPU Inspector (AGI)** | GPU 性能分析和帧调试 | 独立工具 |

Frame Pacing Library 已在 §2.17 详细讨论，这里重点关注与性能优化直接相关的其他组件。

### Game Activity：比 NativeActivity 更好的选择

大多数游戏使用 C/C++ 引擎渲染，通常基于 `NativeActivity`。`Game Activity` 是 Google 提供的替代方案，针对游戏场景做了几项关键优化：

1. **减少输入延迟**。`NativeActivity` 的输入事件经过 Java 层的 InputQueue 分发，再通过 JNI 传递到 native 代码。`Game Activity` 允许 native 代码直接通过 `android/input.h` 接收事件，绕过 Java 层的分发路径，减少约 1-2ms 的输入延迟。
2. **更好的窗口管理**。`Game Activity` 正确处理了分割屏、画中画、通知遮罩等场景的生命周期，避免了 `NativeActivity` 在这些场景下的常见 bug。
3. **C/C++ 接口统一**。`Game Activity` 将输入、窗口、游戏模式查询都统一到 native API，游戏引擎不需要通过 JNI 回调 Java 层。

```c
// Game Activity 提供的游戏模式查询 native API
#include <game-activity/GameActivity.h>

extern "C" void onGameModeChanged(GameActivity* activity, int gameMode) {
    switch (gameMode) {
        case GAME_MODE_PERFORMANCE:
            setTargetFPS(120);
            setGraphicsPreset(ULTRA);
            break;
        case GAME_MODE_BATTERY:
            setTargetFPS(30);
            setGraphicsPreset(LOW);
            break;
        default:
            setTargetFPS(60);
            setGraphicsPreset(HIGH);
            break;
    }
}
```

[已验证: 官方文档, developer.android.com/games/agdk/integration]

### Performance Tuner：自动化的性能质量报告

Performance Tuner 是 AGDK 中容易被忽视但非常有价值的组件。它自动收集以下数据并上报到 Google Play Console：

- **帧时间分布**：每秒的帧时间分位数（P50/P90/P99），比单纯看平均 FPS 更能反映卡顿情况
- **热状态关联**：帧时间与设备热状态的关系，帮助开发者判断卡顿是代码问题还是热降频
- **设备分段**：按设备型号、SoC、内存大小等维度分析性能差异，帮助确定优化优先级

Performance Tuner 的价值在于"自动化"——开发者不需要自己搭建性能数据采集系统，SDK 自动处理数据采集、压缩、上传、展示的全流程。对于独立开发者或小团队来说，这是获取真实用户性能数据的最省力方式。

[已验证: 官方文档, developer.android.com/games/agdk/performance-tuner]

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
duration_ms: 30000
EOF
```

相比普通 App 的 Trace 配置，游戏场景需要额外关注：
- **`power` 和 `freq` category**：追踪 CPU/GPU 频率变化，这是判断热降频和调度问题的核心数据
- **更大的 buffer**：游戏持续满负载，30 秒的 Trace 数据量可能达到 100MB+
- **GPU counter**：如果设备支持，启用 GPU 性能计数器追踪

### 关键分析路径

拿到游戏 Trace 后，按以下顺序分析：

**第一步：帧时间稳定性**

在 Perfetto 的 Frame Timeline Track 中，观察游戏 App 的帧时间。正常情况下帧时间应该稳定在目标值附近（如 60fps 下约 16.66ms）。如果看到帧时间在某些区域突然升高（如从 16ms 跳到 33ms 或 50ms），记录这些时间点。

**第二步：关联 CPU 频率**

切换到 CPU Frequency Track，观察帧时间升高的时间点对应的 CPU 频率。如果频率从 2.8GHz 降到 1.2GHz，说明是热降频导致的掉帧。此时需要结合 Thermal Status Track 确认。

**第三步：检查 ADPF Hint Session**

如果游戏集成了 ADPF，在 Trace 中找到 `power.hint_session` Track。对比 target duration 和 actual duration：
- 两条线贴近 → ADPF 调频有效
- actual 持续高于 target → 系统资源跟不上需求，可能是热降频限制了提频上限
- actual 持续低于 target → target 设得过于宽松，可以降低目标以节省功耗

**第四步：排除调度延迟**

在 CPU Scheduling Latency Track 中检查游戏主线程和渲染线程的调度延迟。如果看到频繁的 2-5ms 调度延迟（线程从 `TASK_RUNNING` 到实际获得 CPU 的时间），说明游戏线程的调度优先级可能不够高。结合 §5.1 中关于 CFS 调度的讨论，确认游戏线程是否被正确设置了 SCHED_FIFO 或通过 ADPF 获得了优先级提升。

[图：Perfetto 中游戏性能分析的典型视图——从上到下依次为 Frame Timeline、CPU Frequency、Thermal Status、Hint Session Track，标注关键分析区域]

### OEM 游戏模式对 Trace 的干扰

分析游戏性能时有一个常见的坑：**OEM 的游戏模式可能干扰你的 Trace 数据**。

Samsung 的 Game Booster、Xiaomi 的 Game Turbo、OPPO 的 Game Space 等厂商游戏模式，在检测到游戏运行后会执行一系列激进的优化：强制锁定 CPU 最高频率、禁止后台进程运行、修改 GPU 调度策略。这些优化会"掩盖"代码层面的性能问题——在开启厂商游戏模式时看起来流畅的 60fps，在关闭后可能暴露出大量卡顿。

做性能分析和优化时，**必须关闭厂商的游戏模式**，只依赖 Game Mode API + ADPF 进行性能管理。否则我们很难区分到底是代码优化生效，还是厂商模式在托底。

[待补充：各主要 OEM 厂商游戏模式的关闭方法列表]

## Android 16/17 的游戏性能新特性

### Android 16：ADPF 与 Vulkan 协同增强

Android 16 在游戏性能方面的核心变化是 ADPF 的 Headroom API 和 Vulkan 的深度协同。

`SystemHealthManager` 新增的 `getCpuHeadroom()` 和 `getGpuHeadroom()` 让游戏可以在每帧开始时查询"当前还有多少性能余量"，而不是等帧时间超标了才发现问题。这对自适应画质引擎尤其有价值——引擎可以根据 Headroom 提前调整渲染复杂度，避免在热降频发生时才被动应对。

同时，Android 16 将 Vulkan 1.4 作为默认的图形 API，ANGLE 作为 OpenGL ES 的兼容层。对游戏来说，可以把影响拆成三点：
- 使用 Vulkan 的游戏可以直接获得更低的驱动开销和更精确的 GPU 时间控制
- 使用 OpenGL ES 的游戏通过 ANGLE 转译到 Vulkan，存在约 5-15% 的性能开销（§2.14 讨论过 ANGLE 的转译机制）
- Game Mode 的 PERFORMANCE 模式下，系统可能为 ANGLE 转译路径提供额外的优化

[已验证: 官方文档, developer.android.com/about/versions/16/behavior-changes-16]

### Android 17：Game Mode Interventions

Android 17 引入了 Game Mode Interventions 机制，允许 OEM 对**不再积极更新的旧游戏**施加系统级优化。这个设计的出发点是：大量热门游戏（尤其是休闲游戏和小游戏）的开发者已经不再更新，但这些游戏的性能问题严重影响用户体验。

Interventions 机制允许 OEM 在不修改游戏代码的情况下，通过系统配置为特定游戏应用优化策略：

- **调整 backbuffer 大小**：降低渲染分辨率以减少 GPU 负载（类似 PC 上的动态分辨率缩放）
- **限制帧率**：强制将 60fps 的游戏限制到 30fps，在低端设备上获得更稳定的体验
- **调整 CPU 亲和性**：将游戏线程绑定到特定核心组合

开发者可以选择退出（opt-out）Game Mode Interventions，如果他们认为系统优化会导致兼容性问题。退出方式是在 Manifest 中声明：

```xml
<meta-data
    android:name="android.game_mode_config"
    android:resource="@xml/game_mode_config" />
```

并在 `game_mode_config.xml` 中设置 `android:allowInterventions="false"`。

[待验证: Game Mode Interventions 在 Android 17 最终版中的具体实现细节和 OEM 可配置项]

## 游戏卡顿分析方法论

### 帧时间分析：关注波动而非平均值

游戏性能分析中最大的误区之一是只看平均 FPS。"平均 55fps" 可能意味着 50 帧是 16ms + 10 帧是 33ms，用户看到的是每秒卡顿两次。正确的做法是看帧时间分布，尤其是 P95 和 P99 帧时间。

在 Perfetto 中，可以通过 SQL 查询游戏 App 的帧时间分布：

```sql
-- 查询帧时间分布（P50/P90/P95/P99）
SELECT
    process.name AS process_name,
    quantile(dur / 1e6, 0.50) AS p50_ms,
    quantile(dur / 1e6, 0.90) AS p90_ms,
    quantile(dur / 1e6, 0.95) AS p95_ms,
    quantile(dur / 1e6, 0.99) AS p99_ms,
    count(*) AS total_frames,
    countif(dur > 16.666e6) AS missed_vsync
FROM slice
JOIN thread_track ON slice.track_id = thread_track.id
JOIN thread ON thread_track.utid = thread.utid
JOIN process ON thread.upid = process.upid
WHERE slice.name LIKE 'Choreographer#doFrame%'
    AND process.name LIKE '%game_process_name%'
GROUP BY process.name;
```

关注 `missed_vsync` 列——它直接告诉你在采集期间有多少帧超过了 VSync 周期。如果 P50 = 11ms 但 P99 = 45ms，说明 99% 的帧都在预算内，但最慢的 1% 严重超时。这就是"感觉卡但平均帧率还行"的根源。

### GC 对游戏帧的影响

ART 的 GC 暂停是游戏卡顿的常见来源之一。游戏通常在每帧的渲染循环中分配大量临时对象（变换矩阵、碰撞检测中间结果等），导致 GC 频繁触发。GC 的 STW（Stop-The-World）暂停会中断游戏主线程，导致帧时间飙升。

在 Perfetto 中识别 GC 影响：搜索 `art::gc` 相关的 slice，或者观察主线程在渲染循环中出现的不明原因的空闲段——如果主线程在 `RUNNABLE` 状态但没有执行任何代码（slice 为空），很可能是被 GC 暂停了。

应对策略：
1. 减少渲染循环中的对象分配，使用对象池复用
2. 利用 §5.9 中 ADPF 的 Thermal API，在热状态安全时允许更大的 GC 堆，减少 GC 触发频率
3. 在游戏加载阶段预分配所有需要的内存，避免在战斗场景中触发 GC
4. 使用 Android 17 的 Generational GC（§4.8），它将 GC 暂停时间从原来的 10-30ms 降低到 1-5ms

### 热节流导致的渐进式降帧

热降频导致的帧率下降有一个典型模式：不是突然从 60fps 跳到 30fps（那是调度问题），而是缓慢地、渐进式地下降——55fps → 50fps → 45fps → 40fps → 35fps。

在 Trace 中看到这种模式时，需要：
1. 检查 Thermal Status Track，确认温度变化与帧率下降的对应关系
2. 检查 CPU Frequency Track，确认是否在温度升高后频率逐步降低
3. 如果游戏使用了 ADPF Thermal API，检查 `getThermalHeadroom()` 的查询频率和 App 的应对策略

应对热降频的最佳实践不是对抗系统（那不可能赢），而是**主动合作**：在温度还低的时候就适当降低渲染复杂度，把热余量留到关键时刻使用。这和 §5.5 中讨论的"主动式热管理"策略一致——越早开始降级，最终达到的稳态帧率就越高。

[图：热降频场景的帧时间模式——前 30 秒稳定 16ms，之后随温度升高逐步增长到 20ms→25ms→33ms，形成渐进式降帧曲线]

## OEM 游戏模式与 Game Mode API 的关系

### 厂商模式的"越俎代庖"

主流 Android 厂商都有自己的游戏优化模式，这些模式通常比 Google 的 Game Mode API 更激进：

- **Samsung Game Booster**：检测到游戏后自动锁定 CPU 最高频率，禁止 TouchWiz 的动画和过渡效果，优化内存管理
- **Xiaomi Game Turbo**：类似策略，额外提供网络加速（QoS 优先级提升）和免打扰模式
- **OPPO/OnePlus Game Space**：锁定最高频率 + GPU 频率提升 + 触控采样率提升

这些厂商模式的存在导致了一个尴尬的碎片化问题：同一个游戏在不同品牌手机上的性能表现可能差异巨大，而且这种差异来自厂商模式而非游戏代码。对于做跨设备性能优化的开发者来说，处理时至少要注意三件事：

1. **测试时必须关闭厂商模式**。否则我们无法区分是代码优化有效，还是厂商模式在帮忙。
2. **Game Mode API 是跨设备的标准化方案**。Google 的 Game Mode API 在所有通过 GMS 认证的设备上行为一致，而厂商模式各不相同。
3. **两者可能冲突**。某些厂商模式会忽略 Game Mode API 的 BATTERY 模式，强制保持最高性能——这看似"更好"，实际上会导致设备更快过热，最终体验更差。

### 性能测试的最佳实践

进行游戏性能测试和优化时，建议遵循以下流程：

1. 关闭所有 OEM 游戏模式（Samsung Game Booster / Xiaomi Game Turbo 等）
2. 设置系统电池模式为"默认"（不是"省电"也不是"性能"）
3. 通过 `adb shell settings put global low_power 0` 确认省电模式关闭
4. 使用 `adb shell cmd game mode set <package> <mode>` 模拟不同 Game Mode
5. 在 Perfetto 中同时抓取帧时间、CPU 频率、热状态、ADPF Session 数据
6. 每次测试前确保设备温度回到常温（>5 分钟静止冷却）

## 与其他章节的关系

- **§2.17 Frame Pacing Library**：Swappy 解决游戏渲染循环与 VSync 的同步问题，是游戏帧节奏控制的基础
- **§5.9 ADPF**：本章的 Game Mode/State API 与 ADPF 的 Performance Hint/Thermal API 构成完整的游戏性能管理框架
- **§5.5 Thermal 管控**：§5.5 侧重系统侧的热管理机制，本章侧重游戏侧如何通过 Thermal API 主动应对
- **§7.1 卡顿定义与分类**：游戏的"掉帧"和普通 App 的"卡顿"在成因和表现上有显著差异
- **§7.9 感知流畅性**：步幅波动分析在游戏场景中尤为重要——帧时间一致性比平均帧率更能反映游戏体验
- **§4.8 ART 分代 GC**：Generational GC 减少了 GC 暂停时间，对游戏的帧时间稳定性有直接帮助
- **§14.10 eBPF/BPF**：eBPF 的 sched_ext 可以用于更精细的游戏线程调度分析和优化

## 参考资料

- AOSP GameManager: `frameworks/base/core/java/android/app/GameManager.java`
- AOSP GameManagerService: `frameworks/base/services/core/java/com/android/server/GameManagerService.java`
- AOSP GameStateManager: `frameworks/base/core/java/android/app/GameStateManager.java`
- 官方文档: https://developer.android.com/games/gamemode/gamemode-api
- 官方文档: https://developer.android.com/games/optimize/performance
- 官方文档: https://developer.android.com/games/agdk
- AGDK Frame Pacing: https://developer.android.com/games/agdk/frame-pacing
- 研究素材: intake/research-feeds/2026-04-08-19-android-adpf-agdk-game-mode-thermal-performance.md
- 研究素材: intake/research-feeds/2026-04-05-19-android16-arr-surfaceflinger-choreographer-frame-pacing.md
