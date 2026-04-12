---
title: "ADPF 自适应性能框架"
chapter: "5.9"
section: "5.9"
status: ready-for-review
applicable_versions: "Android 12 (API 31) - Android 17 (API 37)"
drafted_date: "2026-04-06"
drafted_by: "openclaw-task2a"
tags: [adpf, thermal, performance-hint, game-performance, cpu-boost, frame-rate]
related_chapters: ["5.5", "5.6", "7.5", "14.7"]
created_by: "task2a-knowledge-gap"
created_date: "2026-04-05"
gap_source: "官方文档+研究素材+AOSP结构"
gap_score: "15/20"
confidence: medium
sources:
  - type: official
    path: "https://developer.android.com/reference/android/os/PerformanceHintManager"
  - type: official
    path: "https://developer.android.com/reference/android/os/ThermalManager"
  - type: official
    path: "https://developer.android.com/reference/android/app/GameManager"
  - type: aosp
    path: "frameworks/base/native/android/performance_hint.cpp"
  - type: aosp
    path: "frameworks/base/core/java/android/os/PerformanceHintManager.java"
  - type: blog
    path: "https://android-developers.googleblog.com/"
pipeline_stage: task2b_pending
task6_state: reviewed
task9_state: reviewed
task2b_state: pending
reviewed_by: "openclaw-task6"
reviewed_date: "2026-04-12"
task6_result: needs-rework
task9_result: needs-rework
---

# 5.9 ADPF 自适应性能框架

## 为什么需要 ADPF

移动设备的性能困境可以用一个矛盾来概括：CPU 和 GPU 的性能上限是固定的（由 SoC 和散热能力决定），但 App 的负载是波动的——游戏进入团战时负载飙升，浏览界面时负载回落。传统的 CPU 调频策略基于历史负载采样来预测未来需求，存在一个无法回避的滞后：负载上升时，系统需要若干个采样周期才能确认趋势并提频，而这几个周期内 App 可能已经掉帧了。

这个滞后在高帧率场景中尤为致命。以 120 fps 为例，一帧的预算只有 8.33 ms。如果系统在 2-3 个采样周期（可能 10-30 ms）后才完成提频，App 已经连续掉了几帧。反过来，负载下降后系统缓慢降频又浪费了功耗。

ADPF（Android Dynamic Performance Framework）的核心思路是消除这个滞后——让 App 直接告诉系统"我接下来需要多少性能"，而不是等系统自己猜。系统拿到这个信息后，可以更精准、更快速地调整 CPU/GPU 频率和核心分配。这不是一个单一 API，而是 Performance Hint API、Thermal API、Game Mode API 三个互补组件构成的框架，覆盖了"预告需求→动态调频→热管理→模式适配"的完整性能调控流程。

[已验证: 官方文档, developer.android.com/reference/android/os/PerformanceHintManager]

## Performance Hint API：App 与系统的性能契约

### HintSession 的反馈循环

Performance Hint API 的核心抽象是 HintSession。App 创建一个 HintSession 时，需要指定两件事：参与工作的线程 ID 列表，以及目标帧时间（target work duration）。这相当于 App 和系统之间建立了一份"性能契约"：App 承诺会报告每帧的实际耗时，系统承诺根据偏差来调整资源。

反馈循环的工作方式如下：App 在每帧渲染完成后调用 `reportActualWorkDuration()`，报告这一帧实际花了多少时间。系统将这个实际值与 `updateTargetWorkDuration()` 设定的目标值做比较，然后根据偏差方向和幅度调整 CPU 频率——如果实际耗时持续超过目标，系统会提高频率；如果实际耗时持续低于目标，系统会降低频率以节省功耗。

```java
// frameworks/base/core/java/android/os/PerformanceHintManager.java
// @ AOSP android-16.0.0_r1
PerformanceHintManager phm = getSystemService(PerformanceHintManager.class);

// 创建 HintSession：指定工作线程和目标帧时间
long targetDurationNanos = 8_333_000L; // 120 fps = 8.33 ms
HintSession session = phm.createHintSession(
    Collections.singletonList(mainThreadId),
    targetDurationNanos
);

// 每帧完成后报告实际耗时
long actualDurationNanos = frameEndTime - frameStartTime;
session.reportActualWorkDuration(actualDurationNanos);

// 如果目标帧率变化（如从60 fps切到120 fps），更新目标
session.updateTargetWorkDuration(16_666_000L);
```

这段代码展示了 HintSession 的基本用法，有两个细节值得注意。

第一，`createHintSession()` 接受的是一个线程 ID 列表。App 可以同时把主线程和 RenderThread 都纳入同一个 session，系统会为这组线程统一调整 CPU 频率。对于游戏场景，还可以把游戏逻辑线程和渲染线程一起绑定，确保整个渲染管线获得一致的 CPU 资源。

第二，`updateTargetWorkDuration()` 不是一次性设定就完事的。当 App 的帧率目标发生变化时（比如从省电模式的 30 fps 切到性能模式的 120 fps），需要调用这个方法更新目标。系统会根据新目标重新计算 CPU 频率。

[已验证: AOSP android-16.0.0_r1, frameworks/base/core/java/android/os/PerformanceHintManager.java]

### 系统侧的响应机制

在系统侧，`PerformanceHintService`（运行在 system_server）接收来自各 App 的 HintSession 数据，并通过 HAL 层与 SoC 厂商的电源管理模块交互。具体的调频策略由 OEM 实现——不同厂商的 SoC 对 Hint 的响应方式不同。高通的 PerfLock 机制、联发科的 Perfservice 都会接收 ADPF 的 Hint 信号并据此调整 CPU 频率和核心分配。

这种设计意味着 ADPF 的实际效果存在设备差异。同一款游戏在 Pixel 上和在某款国产手机上，ADPF 带来的帧率稳定性提升可能不同。在 Perfetto 中观察 ADPF 效果时，需要意识到这种设备差异。

Native 层的实现位于 `frameworks/base/native/android/performance_hint.cpp`，为 C/C++ 游戏引擎提供了等效的 API（`APerformanceHint_*` 系列函数），避免引擎开发者必须通过 JNI 调用 Java API。

[已验证: AOSP android-16.0.0_r1, frameworks/base/native/android/performance_hint.cpp]

### Android 15 的增强：GPU 时长上报与能效模式

Android 15 为 Performance Hint API 引入了两个重要增强。

第一个是 GPU 工作时长上报。之前的 ADPF 只能上报 CPU 工作时长，系统据此只能调整 CPU 频率。Android 15 允许 App 在同一个 HintSession 中同时上报 CPU 和 GPU 的工作时长，系统可以据此同时调整 CPU 和 GPU 的频率。这对 GPU-bound 的游戏场景尤为重要——如果系统只根据 CPU 耗时来调频，而瓶颈在 GPU 上，ADPF 的调频就完全打偏了。

第二个是能效模式（power-efficiency mode）。HintSession 可以设置能效优先模式，让系统将关联线程调度到效率核（E-core）上，优先功耗而非性能。这个模式适合后台长时间运行的任务，比如游戏加载场景中的资源解压——不需要极致性能，但希望功耗尽可能低。

[已验证: 官方文档, developer.android.com/about/versions/15/behavior-changes-15]

### Android 16 的 Headroom API

Android 16 引入了 `SystemHealthManager`，提供了 `getCpuHeadroom()` 和 `getGpuHeadroom()` 两个新 API。这两个 API 返回的是当前 CPU/GPU 的性能余量——即"在触发降频之前，还有多少性能空间可以使用"。

Headroom 的计算基于设备的实时热状态和功耗状态。App 可以设定一个时间窗口（通过 `CpuHeadroomParams` / `GpuHeadroomParams`），查询在该窗口内的平均余量或最小余量。这对游戏引擎的自适应画质调节非常有价值：引擎可以在每帧开始时查询 Headroom，如果余量充足就保持高画质，如果余量紧张就开始降级渲染质量，避免等到热降频发生后再被动应对。

同时，Android 16 为 NDK 引入了 `AThermal_HeadroomCallback` 监听器 API，替代了之前基于轮询的 `AThermal_getThermalHeadroomThresholds()`。App 不再需要主动轮询热余量，而是注册回调，系统在热状态变化时主动通知。

[已验证: 官方文档, developer.android.com/about/versions/16/behavior-changes-16]

## Thermal API：从被动降频到主动管理

### 热状态的层级模型

ThermalManager API 不返回具体的温度值（"芯片 72 °C"），而是返回一个抽象的热状态等级。这个设计是有意为之的——不同 SoC 的温度阈值完全不同，直接暴露温度值对 App 开发者没有意义。App 关心的不是"多少度"，而是"在这个状态下我应该做什么"。

热状态从低到高分为七个等级：

| 状态 | 含义 | App 应对策略 |
|------|------|-------------|
| `THERMAL_STATUS_NONE` | 正常运行 | 无需任何调整 |
| `THERMAL_STATUS_LIGHT` | 轻微发热 | 开始降低非关键负载 |
| `THERMAL_STATUS_MODERATE` | 中度发热 | 降低帧率、简化渲染 |
| `THERMAL_STATUS_SEVERE` | 严重发热 | 大幅降级画质和帧率 |
| `THERMAL_STATUS_CRITICAL` | 临界状态 | 停止所有非必要工作 |
| `THERMAL_STATUS_EMERGENCY` | 紧急状态 | 保存数据、准备关闭 |
| `THERMAL_STATUS_SHUTDOWN` | 即将关机 | 立即保存、清理资源 |

[图：热状态等级变化示意图——时间线上展示状态从 NONE 到 SEVERE 再回到 NONE 的过程，标注每个阶段对应的系统行为和 App 建议行为]

App 通过 `ThermalManager.addThermalStatusListener()` 注册监听器，在状态变化时收到回调。App 不应该等到 SEVERE 才开始降级——到那时系统已经强制降频，帧率已经崩了。正确的做法是在 LIGHT 就开始做轻微调整（比如降低阴影分辨率），在 MODERATE 做更明显的调整（比如降低帧率目标），这样用户感知到的变化是平滑的，而不是突然从 60 fps 掉到 30 fps。

[已验证: 官方文档, developer.android.com/reference/android/os/ThermalManager]

### Thermal Headroom：预测式热管理

`getThermalHeadroom(int forecastSeconds)` 是 Thermal API 中最有趣的方法。它不报告当前状态，而是**预测**未来 N 秒后的热余量——即"如果当前负载持续不变，N 秒后还有多少热余量"。返回值是 0.0 到 1.0 的浮点数，越接近 1.0 表示离降频越近。

这个预测 API 的价值在于让 App 可以在热降频发生之前就开始调整。比如游戏引擎可以这样使用：每帧查询 `getThermalHeadroom(30)`，如果返回值超过 0.7，就开始降低渲染复杂度。这样 30 秒后即使系统触发了热降频，App 的负载已经降下来了，用户感知不到帧率突变。

```java
// 预测未来30秒的热余量
ThermalManager thermalManager = getSystemService(ThermalManager.class);
float headroom = thermalManager.getThermalHeadroom(30);

if (headroom > 0.8f) {
    // 即将触发严重降频，紧急降级
    renderer.setShadowQuality(ShadowQuality.LOW);
    targetFrameRate = 30;
} else if (headroom > 0.5f) {
    // 中等余量紧张，适度降级
    renderer.setShadowQuality(ShadowQuality.MEDIUM);
    targetFrameRate = 45;
}
```

[已验证: 官方文档, developer.android.com/reference/android/os/ThermalManager#getThermalHeadroom]

### 与 PowerManagerService 的关系

ThermalManager 的数据来源于底层的 Thermal HAL（`hardware/interfaces/thermal/`），由 SoC 厂商实现。HAL 层直接读取芯片上的温度传感器数据，结合厂商的热模型计算热状态。PowerManagerService 负责在热状态达到 SEVERE 以上时执行系统级的强制降频（直接限制 CPU 频率上限），这是 App 无法绕过的。

ADPF 的 Thermal API 和 PowerManagerService 的热管理是分层的：前者是"建议性"的，App 可以选择响应或忽略（虽然不响应会导致后续系统强制降频体验更差）；后者是"强制性"的，系统直接操作 CPU 频率。ADPF 的设计理念是让 App 在系统强制降频之前主动调整，这样系统的强制降频就成为一个兜底机制，而不是唯一的调控手段。

[待验证: Thermal HAL 2.0 在 Android 16/17 中的具体变化]

## Game Mode API：用户意图的传达

### 游戏模式的三个维度

Game Mode API 通过 `GameManager` 类提供了用户选择的性能偏好。Android 12 引入后，用户可以在系统设置中为每个游戏选择模式：

- **PERFORMANCE**：优先性能，系统会倾向于提频，App 应该以最高画质和帧率运行
- **BATTERY**：优先续航，系统会倾向于降频，App 应该降低画质和帧率
- **STANDARD**：平衡模式，系统按默认策略调度

App 通过 `GameManager.getGameMode()` 查询当前模式，然后据此调整渲染策略。Game Mode 和 Performance Hint API 可以协同工作：PERFORMANCE 模式下 App 把帧率目标设高一些，同时通过 HintSession 告知系统需要更多资源；BATTERY 模式下 App 把帧率目标设低一些，HintSession 的目标时长也相应放宽。

```java
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
    default: // STANDARD
        targetFps = 60;
        graphicsPreset = GraphicsPreset.HIGH;
        break;
}
```

[已验证: 官方文档, developer.android.com/reference/android/app/GameManager]

### Game State：细粒度的性能标注

Android 13 引入了 `GameStateManager`，允许 App 告知系统更细粒度的游戏状态——不仅仅是"我在运行"，而是"我在加载"、"我在对战"、"我在过场动画"。不同状态下的性能需求差异很大：加载阶段需要大量 I/O 和解压，对战阶段需要稳定的渲染帧率，过场动画只需要视频解码性能。

```java
GameStateManager stateManager = getSystemService(GameStateManager.class);
// 标注当前处于对战阶段，性能关键
stateManager.setGameState(GameState.create(
    /* isPerformanceCritical= */ true,  // 对战阶段不能掉帧
    /* gameMode= */ GameManager.GAME_MODE_PERFORMANCE
));
```

`isPerformanceCritical` 参数是给系统的关键信号：当标记为 true 时，系统会尽可能避免降频和核心迁移；当标记为 false 时（比如过场动画），系统可以更激进地节省功耗。

[已验证: 官方文档, developer.android.com/reference/android/app/GameStateManager]

## ADPF 的完整工作流

把三个 API 放在一起，一个完整的 ADPF 集成流程如下：

1. **初始化阶段**：查询 Game Mode，确定性能策略；创建 HintSession；注册 Thermal 状态监听
2. **运行阶段**：每帧渲染后上报实际耗时；定期查询 Thermal Headroom；根据热状态预判调整画质
3. **状态切换**：Game Mode 变化时更新策略；游戏场景切换时更新 Game State；帧率目标变化时更新 HintSession 的 target duration
4. **异常处理**：热状态达到 CRITICAL 时保存数据；HintSession 被系统关闭时重新创建

这个流程中，Performance Hint API 负责"告诉系统需要什么"，Thermal API 负责"预测系统还能给什么"，Game Mode API 负责"用户想要什么"。三者缺一——只有 Hint 没有 Thermal 预判，App 会在热降频时措手不及；只有 Thermal 没有 Hint，系统的调频精度受限于采样滞后；没有 Game Mode，App 无法区分用户对"流畅"和"省电"的偏好。

## 在 Perfetto 中的表现

### ADPF 相关 Track

在 Perfetto Trace 中，ADPF 相关信息分散在几个 Track 中：

**Hint Session Track**（`power.hint_session`）：每个 HintSession 有一个独立的 Track，显示 target duration 和 actual duration 的对比。正常情况下两条线贴近，说明 ADPF 调频精准；如果 actual 持续高于 target，说明系统资源跟不上 App 需求（可能是 SoC 性能不足或热降频限制了提频）。

**Thermal Status Track**（`power.thermal`）：展示热状态等级的时间线。关注热状态从 NONE 上升到 LIGHT/MODERATE 的时刻——如果这个时刻与帧率下降的时刻吻合，说明掉帧是热降频导致的。

**CPU Frequency Track**：Perfetto 中每个 CPU 核心都有自己的频率 Track。结合 Hint Session Track 一起看：当 App 上报 actual > target 时，CPU 频率是否在后续几个周期内上升？如果没有，可能是 ADPF HAL 层没有正确响应，或者已经被热管理限制了频率上限。

### 分析 ADPF 有效性

判断 ADPF 是否对某个 App 有效，可以按以下步骤：

1. 在 Perfetto 中找到目标 App 的 Hint Session Track
2. 观察 actual duration 与 target duration 的关系——如果 actual 在 target 附近波动，说明调频有效
3. 对比没有使用 ADPF 时（同场景、同设备）的帧时间稳定性
4. 检查 CPU frequency track 中频率变化是否与 Hint Session 的上报节奏对应

[图：Perfetto 中 ADPF 效果对比——上图为未使用 ADPF 时的帧时间（波动大），下图为使用 ADPF 后（帧时间稳定在 target 附近）]

如果 ADPF 的 Hint Session 数据存在但 CPU 频率没有变化，可能的原因包括：OEM 未正确实现 ADPF HAL、设备正在热降频中（频率被锁定在上限以下）、或者 HintSession 的 target duration 设置不合理（过长导致系统认为不需要提频）。

[待补充：Trace 截图——ADPF Hint Session + CPU frequency 关联分析的完整示例]

## 版本演进

| 版本 | 引入/变更 |
|------|----------|
| Android 12 | Performance Hint API 首次引入（`PerformanceHintManager`）；Game Mode API 引入（`GameManager`） |
| Android 13 | `GameStateManager` 引入，支持细粒度游戏状态标注；Thermal API NDK 接口（`AThermalManager`，API 31） |
| Android 14 | 更多 OEM 支持 ADPF HAL；`getThermalHeadroom()` 可用性扩大 |
| Android 15 | GPU 工作时长上报（CPU+GPU 联合调频）；HintSession 能效模式；`getThermalHeadroomThresholds()` 热余量阈值查询 |
| Android 16 | `SystemHealthManager.getCpuHeadroom()` / `getGpuHeadroom()`；`AThermal_HeadroomCallback` 监听器；Vulkan 默认化与 ADPF 深度协同 |
| Android 17 | [待验证：ADPF 对非游戏场景的扩展细节；Camera/视频播放场景的 ADPF 支持] |

## 常见问题与误区

### 误区一：ADPF 能提升 SoC 的绝对性能

ADPF 不能突破硬件的物理上限。如果 SoC 在最高频率下仍然无法在目标帧时间内完成渲染，ADPF 也无能为力。ADPF 解决的是"系统资源没有及时跟上 App 需求"的问题，而不是"硬件性能不够"的问题。简单来说，ADPF 让系统更快地把频率拉到最高，但不能让最高频率变得更高。

### 误区二：HintSession 创建后就能自动优化

创建 HintSession 只是第一步。如果 App 从来不调用 `reportActualWorkDuration()`，系统拿不到反馈数据，就等于这个 session 是空的。同样，如果 target duration 设置得过于宽松（比如 60 fps 的 App 设了 100ms 的 target），系统会认为当前性能绰绰有余而降频，反而导致性能下降。target duration 应该等于帧预算时间（1000 ms / 目标帧率）。

### 误区三：热降频只需要系统处理

很多开发者认为热管理是系统的事情，App 不需要关心。但实际情况是：系统级的强制降频是粗暴的——直接把 CPU 频率砍到很低，所有 App 都受影响。如果 App 通过 Thermal API 提前降低自己的负载（比如游戏降低画质），设备的发热量就减少了，系统就不需要触发强制降频，用户的整体体验反而更好。

### 误区四：ADPF 只对游戏有用

虽然 ADPF 的主要场景是游戏，但任何帧率敏感的应用都可以从中受益。Camera 应用在录制高帧率视频时、视频编辑 App 在实时预览时、AR 应用在渲染时，都可以通过 Performance Hint API 向系统预告性能需求。Android 16 的 Headroom API 更是降低了非游戏场景的使用门槛——不需要建立完整的 HintSession 反馈循环，直接查询当前性能余量即可。

## 与其他章节的关系

- **§5.5 Thermal 管控**：本章侧重 App 侧的 Thermal API 使用，§5.5 侧重系统侧的热管理机制（HAL、内核温控策略）
- **§5.6 Android 功耗管理**：从调频机制看，ADPF 属于功耗管理的一部分，与 §5.6 的 DVFS、EAS 机制有底层关联
- **§7.5 优化策略**：ADPF 是帧率优化的手段之一，§7.5 中的"动态画质调节"策略通常需要结合 ADPF 使用
- **§14.7 Perfetto 高级分析**：本章涉及的 Perfetto Track 分析是 §13/14 工具使用的基础应用

## 扩展

### Unity/Unreal Engine 的 ADPF 集成

主流游戏引擎已经开始内置 ADPF 支持。Unity 从 2021.2 版本开始提供 ADPF 集成插件，Unreal Engine 通过 Android Platform Extensions 支持相关 API。

**自动 ADPF vs 手动 ADPF** 的取舍是一个实际决策点。自动模式由引擎统一管理 HintSession 的创建、target duration 的设定、actual duration 的上报——开发者只需要启用开关。手动模式允许开发者精细控制：哪些线程纳入 session、target duration 根据场景动态调整、上报时机精确到每帧。

对于大多数游戏，自动模式足够。但如果游戏有非常特殊的帧率需求（比如 VR 场景要求精确的 72 fps、或者有可变刷新率的渲染管线），手动模式能提供更精确的控制。

[待补充：Unity ADPF 插件的具体配置步骤]

### OEM 对 ADPF 的定制

不同 SoC 厂商对 ADPF 的实现策略存在差异，这是分析 ADPF 效果时需要考虑的变量。

高通平台通过 PowerHint HAL 将 ADPF 的 Hint 信号映射到 PerfLock 请求，触发 CPU/GPU 频率调整和核心分配。联发科平台通过 Perfservice 接收 ADPF Hint，结合自己的调度策略做频率决策。Google Tensor 平台有自己的 DVFS 调度策略，与 ADPF 的集成方式也可能不同。

同一款游戏在不同设备上的 ADPF 响应速度和效果可能不同。在做竞品分析（§15.4）或跨设备性能对比时，需要把 OEM 的 ADPF 定制策略纳入考量。

[待验证：不同 OEM 的 ADPF HAL 实现差异的具体数据]
