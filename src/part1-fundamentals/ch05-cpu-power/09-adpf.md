---
status: "ready-for-review"
title: ADPF 自适应性能框架
chapter: '5.9'
section: '5.9'
applicable_versions: Android 11 (API 30, Thermal Headroom 基础能力) - Android 17 (API
  37)
drafted_date: '2026-04-06'
drafted_by: openclaw-task2a
tags:
- adpf
- thermal
- performance-hint
- game-performance
- cpu-boost
- frame-rate
related_chapters:
- '5.5'
- '5.6'
- '7.5'
- '14.7'
created_by: task2a-knowledge-gap
created_date: '2026-04-05'
gap_source: 官方文档+研究素材+AOSP结构
gap_score: 15/20
confidence: medium
sources:
- type: official
  path: https://developer.android.com/reference/android/os/PerformanceHintManager
- type: official
  path: https://developer.android.com/reference/android/os/PowerManager
- type: official
  path: https://developer.android.com/reference/android/os/health/SystemHealthManager
- type: official
  path: https://developer.android.com/reference/android/app/GameManager
- type: official
  path: https://developer.android.com/reference/android/app/GameState
- type: aosp
  path: frameworks/base/native/android/performance_hint.cpp
- type: aosp
  path: frameworks/base/core/java/android/os/PerformanceHintManager.java
- type: aosp
  path: frameworks/base/services/core/java/com/android/server/power/hint/HintManagerService.java
- type: blog
  path: https://android-developers.googleblog.com/
pipeline_stage: task9_pending
task6_state: reviewed
task9_state: pending
task2b_state: fixed
task2b_result: fixed
last_task2b_at: '2026-05-27T08:50:00+08:00'
reviewed_by: openclaw-task6
reviewed_date: "2026-05-27"
task6_result: pass-light-edit
task9_result: needs-rework
last_task9_at: "2026-05-21T04:36:55+08:00"
task9_reviewed_by: openclaw-task9
task9_reviewed_date: "2026-05-21"
last_task9_review_log: "logs/deep-review/2026-05-21-04-deep-review.md"
last_task6_at: "2026-05-27T09:16:48+08:00"
last_task6_review_log: "logs/review/2026-05-27-09-review.md"
task6_reviewed_date: "2026-05-27"
task6_review_notes: "2026-05-27 08:50：已删除原始调研块、素材摘要和过程性说明；API 版本边界、NDK workload hint、协程线程迁移内容已并入正文，等待复审。 | 2026-05-27 09:16 Task6：pass-light-edit。补齐 outline 标记；复核 Task2B 已清理编辑过程痕迹；L1/L2 通过；无新增 L3/L4 回炉项。Task9 result 仍为 needs-rework，送 Task9 复审。"
last_task2b_verifier_at: "2026-05-27T07:50:00+08:00"
task2b_verifier_result: ready-for-task6
task6_reviewed_by: openclaw-task6
review_type: task6-writing-quality-review
---

# 5.9 ADPF 自适应性能框架

<!-- outline-start -->
## 本节要点大纲

### 锚点(必须覆盖)

- 🔹 ADPF 的问题背景：负载波动、调频滞后与帧预算压力
- 🔹 Performance Hint API：HintSession、target duration、actual duration 与系统侧响应
- 🔹 Thermal API / Headroom API：热状态、热余量与低频异步采样边界
- 🔹 Game Mode / GameState：用户模式、游戏状态与 ADPF 的协同边界
- 🔹 Perfetto 观测路径：FrameTimeline、CPU frequency、thermal status 与 App 自定义 trace 标记
- 🔹 版本演进与公开 API 边界

### 扩展(可选深入)

- 🔸 Unity / Unreal Engine 的 ADPF 集成
- 🔸 OEM 对 ADPF 的定制差异
- 🔸 Kotlin 协程线程迁移与 HintSession TID 绑定边界
<!-- outline-end -->

## 为什么需要 ADPF

移动设备的性能困境可以用一个矛盾来概括：CPU 和 GPU 的性能上限是固定的（由 SoC 和散热能力决定），但 App 的负载是波动的——游戏进入团战时负载飙升，浏览界面时负载回落。传统的 CPU 调频策略基于历史负载采样来预测未来需求，存在一个无法回避的滞后：负载上升时，系统需要若干个采样周期才能确认趋势并提频，而这几个周期内 App 可能已经掉帧了。

这个滞后在高帧率场景中尤为致命。以 120 fps 为例，一帧的预算只有 8.33 ms。如果系统在 2-3 个采样周期（可能 10-30 ms）后才完成提频，App 已经连续掉了几帧。反过来，负载下降后系统缓慢降频又浪费了功耗。

ADPF（Android Dynamic Performance Framework）的核心思路是消除这个滞后：App 直接告诉系统"我接下来需要多少性能"，系统再据此调整 CPU / GPU 频率和核心分配。ADPF 由 Performance Hint API、Thermal API、Game Mode API 三个互补组件构成，覆盖"预告需求→动态调频→热管理→模式适配"的性能调控流程。

## Performance Hint API：App 与系统的性能契约

### HintSession 的反馈循环

Java 公开 API 里，对应对象是 `PerformanceHintManager.Session`。创建 session 时，App 需要给出线程 ID 数组和目标工作时长。这相当于 App 对系统声明一个明确的帧预算，比如 120 fps 对应 8_333_333 ns，60 fps 对应 16_666_667 ns。

反馈过程也很直接。App 在每帧结束后调用 `reportActualWorkDuration()` 上报实际耗时，系统把这个值和 `updateTargetWorkDuration()` 设定的目标做比较，再决定后续的 CPU / GPU 资源分配。

```java
// frameworks/base/core/java/android/os/PerformanceHintManager.java
// @ AOSP android-16.0.0_r1
PerformanceHintManager phm = getSystemService(PerformanceHintManager.class);

int[] tids = {mainThreadId};
long targetDurationNanos = 8_333_333L; // 120 fps = 8.33 ms

PerformanceHintManager.Session session =
        phm.createHintSession(tids, targetDurationNanos);

// 每帧完成后报告实际耗时
long actualDurationNanos = frameEndTime - frameStartTime;
session.reportActualWorkDuration(actualDurationNanos);

// 如果目标切回 60 fps，把预算更新为 16.67 ms
session.updateTargetWorkDuration(16_666_667L);
```

这里有两个容易写错的点。

第一，`createHintSession()` 接受的是 `int[] tids`，返回值是 `PerformanceHintManager.Session`。把它写成独立的 `HintSession` 类，或者把线程列表写成 `Collections.singletonList(...)`，示例代码就不能直接编译。

第二，target work duration 要和当前目标帧率对应。120 fps 是 8.33 ms，60 fps 是 16.67 ms。把这两个数字和注释写反，后面的调频判断也会跟着偏。

### 系统侧的响应机制

App 调 `reportActualWorkDuration()` 之后，信息不会直接到 SoC。公开 API 先进入 `PerformanceHintManager.Session`，再到 system_server 中的 `com.android.server.power.hint.HintManagerService`，再经 `IHintManager` 与厂商的 power hint HAL / AIDL 实现交互。排查 ADPF 失效时，也要按这三层拆开看：App 有没有正确上报，system_server 有没有收到 session 更新，OEM 实现有没有把 hint 变成提频或核心分配动作。

这种设计决定了 ADPF 的实际效果会有设备差异。同一款游戏在 Pixel 上和在某款定制 ROM 上，帧时间稳定性的改善幅度可能不同。分析时不能只看 App 代码，还要把 system_server 和 OEM 实现一起纳入判断。

Native 层的公开入口仍在 `frameworks/base/native/android/performance_hint.cpp`，对应 `APerformanceHint_*` 系列接口，方便 C / C++ 游戏引擎直接接入。Java JNI 层会通过 `dlopen("libandroid.so")` / `dlsym` 延迟绑定这些 NDK C API 符号；排查 native 接入问题时，公开 C API 与 Java framework wrapper 要分开看。

### CPU/GPU 工作时长、能效模式与 workload hint

Performance Hint API 的基础用法是周期性上报实际工作时长。Android 15 之后，ADPF 开始补齐 GPU-bound 场景的表达能力：同一个 work period 可以拆出 total、CPU、GPU 几类耗时，让系统知道瓶颈来自 CPU 线程还是 GPU 工作。AOSP 中的 `WorkDuration` overload 仍带有 feature flag，工程接入时要同时看 compile SDK、设备系统版本和 OEM 是否打开对应能力，不能只按单个 API level 下结论。

能效模式用于表达"这组线程可以优先走低功耗路径"。公开入口是 `PerformanceHintManager.Session#setPreferPowerEfficiency(boolean)`，从 API 35 开始进入公开 API 面。它不依赖 `GameManager`，因此可以用于后台批处理、长时间同步、视频处理、AI 推理这类非游戏负载；前提是业务能接受更长的完成时间。

Java 层还有 `sendHint()` 及 `CPU_LOAD_*` / `GPU_LOAD_*` 这类即时 hint 常量，但它们标注为 `@TestApi` / `@hide`，不属于普通 App 的 public SDK 接入面。C / C++ 侧如果要表达负载突增、重置、尖峰，应优先看 NDK `performance_hint.h` 中的 `APerformanceHint_notifyWorkloadIncrease`、`APerformanceHint_notifyWorkloadReset`、`APerformanceHint_notifyWorkloadSpike` 等公开函数，并按头文件标注的 API 版本做条件编译。

### Android 16 的 Headroom API

Android 16 新增的是 `SystemHealthManager#getCpuHeadroom(@Nullable CpuHeadroomParams)` 和 `getGpuHeadroom(@Nullable GpuHeadroomParams)` 等 API。传 `null` 使用默认参数。它们返回 available CPU / GPU capacity headroom，用来回答一个更具体的问题：在当前负载下，离容量上限还剩多少余量。

这组 API 适合做较低频的策略判断，比如场景切换、画质挡位调整、后台调优线程的周期性采样。它不适合塞进 frame loop。官方文档明确写到，每次调用至少会触发一次同步 Binder，单次调用可能超过 1 ms，不建议在 critical thread 上等待结果。实际用法应该放在 worker thread，并遵守 `getCpuHeadroomMinIntervalMillis()` / `getGpuHeadroomMinIntervalMillis()` 暴露的最小轮询间隔。

在 120 fps 场景下，一帧预算只有 8.33 ms。1 ms 的同步 Binder 阻塞消耗了约 12% 的帧预算。如果放在渲染主线程调用 Headroom API，它本身就能成为掉帧来源。Android 16 的文档明确建议低频异步轮询模式，不要同步调用。

Android 16 的 NDK 侧还提供了 `AThermal_HeadroomCallback` 这类 thermal headroom listener。Java 层的 `PowerManager#getThermalHeadroom()` 适合做热趋势预测，`SystemHealthManager` 的 CPU / GPU headroom 更适合判断容量余量，这两类信号不要混成一件事。

### 公开 API 边界：`setPreferIdle`

有调研素材提到 API 37 可能在 `PerformanceHintManager.Session` 上引入 `setPreferIdle(boolean)`，语义比 `setPreferPowerEfficiency` 更偏向"任务可以暂停"。但当前 Android Developers API 37 参考文档和 NDK `performance_hint.h` 中均未找到该方法。如果该 API 存在，可能是 preview/vendor SDK 的一部分，不属于公开 SDK。

能效模式的公开入口仍然是 `setPreferPowerEfficiency(boolean)`（API 35 已确认可用），建议以它为优先选择。

## Thermal API：从被动降频到主动管理

### 热状态的层级模型

App 侧公开的 thermal 入口在 `PowerManager`，不是 `ThermalManager`。`getCurrentThermalStatus()`、`addThermalStatusListener()` 和 `getThermalHeadroom()` 都挂在 `PowerManager` 上。它返回热状态等级；对 App 来说，更有用的判断对象是“系统已经把设备放在哪个热状态上”，芯片绝对温度通常不是可直接决策的输入。

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

App 通过 `PowerManager.addThermalStatusListener()` 注册监听器，在状态变化时收到回调。不要等到 `THERMAL_STATUS_SEVERE` 再动作。到那时系统通常已经开始明显限频，帧时间也已经变差。更合理的做法是在 `LIGHT` 或 `MODERATE` 就提前降低部分负载，把体验变化摊平。

### Thermal Headroom：预测式热管理

`PowerManager#getThermalHeadroom(int forecastSeconds)` 不返回当前温度，它返回的是距离 `THERMAL_STATUS_SEVERE` 还有多少热余量。官方文档说明这个值下界是 0，`1.0` 表示已经到达或即将到达 severe throttling 阈值，值也可能大于 `1.0`。

这个 API 也有两个边界条件。第一，如果调用频率明显快于约 1 Hz，或者系统还没积累够预测样本，返回值可能是 `NaN`。第二，它更适合放在后台线程做 1 秒级采样，不适合每帧查询。

```java
PowerManager powerManager = getSystemService(PowerManager.class);

// 1 秒级后台采样，不要放在渲染关键线程
float headroom = powerManager.getThermalHeadroom(30);
int thermalStatus = powerManager.getCurrentThermalStatus();

if (!Float.isNaN(headroom) && headroom >= 1.0f) {
    renderer.setShadowQuality(ShadowQuality.LOW);
    targetFrameRate = 30;
} else if (thermalStatus >= PowerManager.THERMAL_STATUS_MODERATE) {
    renderer.setShadowQuality(ShadowQuality.MEDIUM);
}
```

这里的判断只是示意。分档阈值要结合设备的 `getThermalHeadroomThresholds()`、机型散热能力和业务自己的帧率目标来定，不能把单一阈值当成通用规则。

### 与 PowerManagerService 的关系

把控制面拆开，事情就清楚了。性能 hint 这一路是 `PerformanceHintManager.Session` → `HintManagerService` → vendor power hint HAL / AIDL。热状态这一路是 `PowerManager` → `IThermalService` → Thermal HAL。前一路告诉系统“App 现在要多少资源”，后一路告诉系统“设备现在还能给多少资源”。

定位问题时，这两个方向要分开判断。如果 `reportActualWorkDuration()` 已经在报，但 CPU 频率没有跟着抬起来，先查 hint 这一侧。如果频率上不去，同时 thermal status 持续升高，那瓶颈更可能在 thermal 这一侧。

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

### Game State：细粒度的性能标注

Android 13 没有新增 `GameStateManager` 这个公开类。游戏仍然通过 `GameManager#setGameState(GameState)` 向系统上报当前阶段，只是 `GameState` 这个对象把 `isLoading`、`mode`、`label`、`quality` 等状态收进去。

```java
GameManager gameManager = getSystemService(GameManager.class);

// 例如：当前处在不可中断的实时对战阶段
gameManager.setGameState(
        new GameState(
                false,
                GameState.MODE_GAMEPLAY_UNINTERRUPTIBLE));
```

`isLoading` 用来告诉系统当前是否处在加载阶段，`mode` 用来区分 menu、可中断 gameplay、不可中断 gameplay 等状态。它不是一个“性能关键开关”，公开 API 里也没有 `isPerformanceCritical` 这样的字段。

`GameState.MODE_CONTENT` 表达的是游戏内非 gameplay 内容，比如广告、网页、文字或视频，不是所有非游戏 App 的通用状态标记。视频播放、视频通话、地图导航这类性能敏感但非游戏的场景，应直接使用 `PerformanceHintManager.Session`、`setPreferPowerEfficiency()` 和 headroom 采样，不要绕到 Game State 模型里。

## 非游戏场景与协程线程迁移边界

ADPF 不只服务游戏。只要应用能把一组长期运行的线程、目标工作时长和实际耗时稳定地报给系统，就可以使用 Performance Hint API。非游戏场景的难点通常不在 API 调用本身，而在"线程集合是否稳定"。

HintSession 绑定的是 Linux TID，不是协程 ID、任务 ID 或业务请求 ID。Kotlin 协程在 `Dispatchers.Default` / `Dispatchers.IO` 上发生线程迁移时，如果新 TID 没有纳入 session，后续 work duration 上报就很难和真实执行线程对应。API 31-33 的保守做法是控制协程执行上下文，必要时重建 session；API 34 之后可以用 `Session#setThreads(int[])` 动态更新线程集合，但仍要控制更新频率，避免把每次协程调度都变成 Binder 往返。

`reportActualWorkDuration()` 本身也会进入系统服务。高帧率渲染、音视频处理、AI 推理这类场景要把 ADPF 上报放在帧或任务边界，不要在细碎的子任务里频繁调用。120 fps 下一帧只有 8.33 ms，任何同步 IPC 都会占掉可观预算。

## ADPF 的完整工作流

把三个 API 放在一起，一个更可靠的 ADPF 集成流程是这样：

1. **初始化阶段**：查询 `GameManager.getGameMode()`；创建 `PerformanceHintManager.Session`；注册 `PowerManager` thermal status listener。
2. **运行阶段**：每帧上报 `reportActualWorkDuration()`；在 worker thread 里按较低频率采样 `PowerManager#getThermalHeadroom()` 或 `SystemHealthManager` 的 CPU / GPU headroom。
3. **状态切换**：场景变化时调用 `GameManager.setGameState(...)`；目标帧率变化时更新 `updateTargetWorkDuration()`。
4. **异常处理**：thermal status 升到 `SEVERE` 或 headroom 接近阈值时，先降画质、降帧率，再让系统的限频兜底。

这个流程里，Performance Hint API 负责表达工作预算，Thermal API 负责表达热约束，Game Mode / GameState 负责表达用户模式和业务阶段。三种信号放在一起，系统才能知道 App 想跑多快、设备还能撑多久、当前场景值不值得继续提频。

## 在 Perfetto 中的表现

### 建议优先看的观测点

公开文档没有把 `power.hint_session`、`power.thermal` 这类名字定义成稳定的 trace contract。不同 Android 版本、厂商配置和 Perfetto schema 下，可见的 track 名、counter 名和数据源都可能不同。把这些字符串写死，读者很容易在自己的 trace 里什么都搜不到。

实际分析时先抓三个相对稳定的观察点：

- **FrameTimeline / 帧时间**：看实际帧时间是否长期贴着目标 budget，还是经常在 budget 上方抖动。
- **CPU frequency / 调度行为**：看上报 work duration 之后，big core 频率和线程调度有没有跟着变化。
- **thermal status / 温度相关 counter**：看掉帧区间前后，thermal status 是否上升，或者 thermal / power counter 是否同步显示热约束增强。

如果项目自己接了 ADPF，最好再补两类自定义 trace 标记，一类包住 `reportActualWorkDuration()`，一类包住画质或帧率策略切换。这样回放 trace 时，可以把“App 何时上报 hint”“系统何时提频”“热状态何时升高”放到同一条时间线上。

### 分析 ADPF 是否生效

判断 ADPF 是否起作用，可以按这个顺序看：

1. 先在 FrameTimeline 里找出掉帧区间，确认 frame budget 是 16.67 ms、8.33 ms 还是其他目标。
2. 再看同一时间段的 CPU frequency 和关键线程调度，判断系统是否尝试给更多资源。
3. 接着对照 thermal status / thermal counter，确认是不是热约束把提频压住了。
4. 再回到 App 自己的 trace section，看 `reportActualWorkDuration()` 与画质切换是否发生在正确时机。

如果 frame time 已经超 budget，但 CPU 频率和调度没有明显响应，问题更像是 HintSession 接入或 OEM 实现。如果 CPU 频率已经抬高，但 thermal status 同时上升并很快限频，问题更像是热约束。没有 App 自定义 trace 标记时，只能判断相关性，很难证明某次上报和某次提频之间的因果关系。

## 版本演进

| 版本 | 引入/变更 |
|------|----------|
| Android 11 (API 30) | `PowerManager#getThermalHeadroom()` 与 NDK thermal manager 可用，这一层是后续 ADPF 热预测能力的基础 |
| Android 12 (API 31) | `PerformanceHintManager` 与 `GameManager` 引入，ADPF 主框架成形 |
| Android 13 (API 33) | 继续通过 `GameManager#setGameState(GameState)` 上报游戏状态，不新增 `GameStateManager` 公开类 |
| Android 14 (API 34) | `PerformanceHintManager.Session#setThreads(int[])` 公开，适合动态修正 HintSession 绑定的线程集合 |
| Android 15 (API 35) | GPU 工作时长上报能力进入 ADPF 演进主线；HintSession 能效模式；`PowerManager#getThermalHeadroomThresholds()` |
| Android 16 (API 36) | `SystemHealthManager#getCpuHeadroom(CpuHeadroomParams)` / `getGpuHeadroom(GpuHeadroomParams)`（传 null 用默认值）；NDK thermal headroom listener；NDK workload hint 系列函数 |
| Android 17 (API 37) | 当前不把 `setPreferIdle(boolean)` 写成公开 SDK 能力；RecyclerView 1.4 自适应刷新率支持属于 ARR，不是 ADPF HintSession |


## 常见问题与误区

### 误区一：ADPF 能提升 SoC 的绝对性能

ADPF 不能突破硬件的物理上限。如果 SoC 在最高频率下仍然无法在目标帧时间内完成渲染，ADPF 也无能为力。ADPF 解决的是"系统资源没有及时跟上 App 需求"的问题，而不是"硬件性能不够"的问题。它能让系统更快地把频率拉到最高，但不能让最高频率变得更高。

### 误区二：HintSession 创建后就能自动优化

创建 HintSession 只是第一步。如果 App 从来不调用 `reportActualWorkDuration()`，系统拿不到反馈数据，就等于这个 session 是空的。同样，如果 target duration 设置得过于宽松（比如 60 fps 的 App 设了 100ms 的 target），系统会认为当前性能绰绰有余而降频，反而导致性能下降。target duration 应该等于帧预算时间（1000 ms / 目标帧率）。

### 误区三：热降频只需要系统处理

很多开发者认为热管理是系统的事情，App 不需要关心。但实际情况是：系统级的强制降频是粗暴的——直接把 CPU 频率砍到很低，所有 App 都受影响。如果 App 通过 Thermal API 提前降低自己的负载（比如游戏降低画质），设备的发热量就减少了，系统就不需要触发强制降频，用户的整体体验反而更好。

### 误区四：ADPF 只对游戏有用

虽然 ADPF 的主要场景是游戏，但任何帧率敏感的应用都可以从中受益。Camera 应用在录制高帧率视频时、视频编辑 App 在实时预览时、AR 应用在渲染时，都可以通过 Performance Hint API 向系统预告性能需求。Android 16 的 Headroom API 降低了非游戏场景的使用门槛：不需要建立完整的 HintSession 反馈循环，也可以低频查询当前性能余量。

**RecyclerView 1.4 的自适应刷新率支持**：AndroidX RecyclerView 1.4.0 引入了 `setFrameContentVelocity()` API，用于在快速滚动时向系统上报滑动速度，配合 Adaptive Refresh Rate（自适应刷新率）机制动态调整屏幕刷新率。这不是 ADPF HintSession 集成——RecyclerView 1.4 不会自动创建 `PerformanceHintManager.Session`，也不会自动上报 work duration。如果需要 ADPF 能力，应用仍需自行创建和管理 HintSession。

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

### OEM 对 ADPF 的定制

不同 SoC 厂商对 ADPF 的实现策略存在差异，这是分析 ADPF 效果时需要考虑的变量。

高通平台通过 PowerHint HAL 将 ADPF 的 Hint 信号映射到 PerfLock 请求，触发 CPU/GPU 频率调整和核心分配。联发科平台通过 Perfservice 接收 ADPF Hint，结合自己的调度策略做频率决策。Google Tensor 平台有自己的 DVFS 调度策略，与 ADPF 的集成方式也可能不同。

同一款游戏在不同设备上的 ADPF 响应速度和效果可能不同。在做竞品分析（§15.4）或跨设备性能对比时，需要把 OEM 的 ADPF 定制策略纳入考量。

**OEM ADPF 响应差异**：不同 SoC 厂商对 ADPF Hint 的响应延迟存在显著差异，直接影响“掉帧后补频能否挽回当前帧”。120 fps 下一帧只有 8.33 ms，响应延迟超过 4 ms 就意味着近半帧预算耗在等待上。

跨设备调优策略不能一刀切。响应延迟较快的设备上，ADPF 可以做帧级补救；响应延迟接近半帧预算的设备上，ADPF 更适合做趋势性调频（提前告诉系统“接下来几帧都需要高性能”），而不是等掉帧后再补救。

## 参考资料

- Android Developers：`PerformanceHintManager` API reference，覆盖 session 创建、target duration、actual duration、thread set 更新等公开接口。
- Android Developers：Android 15 ADPF 说明，覆盖 GPU 工作时长上报和能效模式的版本背景。
- Android Developers：`PowerManager` thermal API reference，覆盖 thermal status、thermal headroom 与预测采样边界。
- Android Developers：`SystemHealthManager` API reference，覆盖 CPU / GPU headroom 的调用入口和低频采样要求。
- AOSP：`frameworks/base/core/java/android/os/PerformanceHintManager.java`，用于核对 Java API surface、flagged API 与 session 状态机。
- AOSP：`frameworks/base/native/android/performance_hint.cpp` 与 NDK `performance_hint.h`，用于核对 native workload hint 接入边界。
