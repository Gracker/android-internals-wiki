---
status: finalized
title: ADPF 自适应性能框架
chapter: '5.4'
section: '5.4'
applicable_versions: Android 11 (API 30, Thermal Headroom 基础能力) - Android 17 (API 37)
tags:
- adpf
- thermal
- performance-hint
- game-performance
- cpu-boost
- frame-rate
related_chapters:
- '5.2'
- '7.2'
- '14.10'
confidence: medium
last_verified: '2026-08-08'
consolidated_from:
- src/part1-fundamentals/ch05-cpu-power/5.19-ondevice-ai-adpf-intelligent-scheduling.md
- src/part1-fundamentals/ch05-cpu-power/5.29-android17-gpu-dvfs-headroom-power-advisor.md
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
  path: frameworks/base/core/jni/android_os_PerformanceHintManager.cpp
- type: aosp
  path: frameworks/base/services/core/java/com/android/server/power/hint/HintManagerService.java
pipeline_stage: ready-to-publish
task6_state: reviewed
task9_state: reviewed
task2b_state: fixed
last_idle_audit_at: '2026-08-08T18:35:19+08:00'
last_idle_audit_run_id: 20260808-183519-idle-audit-87d42442
---

# ADPF 自适应性能框架

ADPF 提供的是应用与系统之间的反馈接口，不是固定升频开关。应用需要用可解释的工作周期、容量余量和热状态驱动降级策略，并通过帧时间、能耗与温升复测系统是否做出了更合适的调度。

## 为什么需要 ADPF

移动设备的峰值性能由片上系统（System on Chip，SoC）、供电和散热条件共同限制，应用负载却会不断变化。游戏可能在多人对战、粒子效果集中出现或资源流式加载时突然变重；地图、相机和视频编辑也有类似的周期性负载。如果只由内核调度器和调频策略根据历史利用率判断，系统只能在负载出现后再作响应。

高刷新率会放大这段响应延迟。120 Hz 的显示周期约为 8.33 ms，但一次渲染不能独占整个周期：输入处理、应用逻辑、RenderThread（渲染线程）、GPU、SurfaceFlinger（系统合成服务）和最终显示提交都要分享这段时间。某个线程组若突然增加几毫秒工作，当前帧可能已经错过显示时限。

Android 动态性能框架（Android Dynamic Performance Framework，ADPF）在应用与系统之间增加了两类信号：

- 应用通过性能提示接口（Performance Hint API）报告周期性工作的目标时长、实际时长和线程集合，系统据此尝试调整这些线程的调度与性能。
- 应用通过热状态接口（Thermal API）和 CPU / GPU 余量接口（Headroom API）读取设备约束，提前降低分辨率、特效、帧率或后台负载。

应用持续报告结果，系统据此调整后续周期，再由新的结果继续修正策略，这就是本节所说的反馈回路。游戏模式（Game Mode）和游戏状态（Game State）进一步补充用户偏好与游戏阶段。这些信号让系统更了解应用需求，但不承诺使用某个运行频率、某颗 CPU 核，也不承诺在固定时间内提频。Android 17 的 Power AIDL 也明确允许平台按自身策略实现；AIDL 是 Android 用来定义跨进程接口的语言，Power HAL 则是 Android 系统框架（framework）访问设备电源策略实现的硬件抽象层。应用仍需处理设备不支持 ADPF、只支持部分能力，以及热约束优先于性能请求的情况。

## Performance Hint API：周期性工作的反馈回路

### HintSession、target duration 与 actual duration

Java 入口是 `PerformanceHintManager.Session`。这里的 session（会话）保存一组线程及其周期性性能目标。创建 session 时，需要传入一组 Linux 线程 ID（Thread ID，TID）和初始目标工作时长（target work duration）；返回 `null` 表示设备不支持 HintSession，或某个 TID 不属于本应用。session 应覆盖一组关系紧密、生命周期较长且周期性执行的线程。

target work duration 表示这组线程希望在每个周期内完成工作的时长，通常小于完整显示周期。以 60 Hz 渲染为例，显示周期约为 16.67 ms；如果纳入 session 的线程只负责其中 6 ms 的 CPU 工作，target 应接近 6 ms，不能直接填写 16.67 ms。Android 17 的 `IPower.createHintSession*()` 注释也采用“60 Hz 渲染、目标工作时长 6 ms”的例子。

下面的代码展示一个基本反馈周期：创建 HintSession，完成一帧渲染，再报告实际工作时长（actual duration）。`renderTid` 必须在对应线程中取得，或由应用自己的线程管理器提供；Java `Thread.getId()` 不是 Linux TID，不能代替它。

```java
// Java API；源码锚点：android-17.0.0_r1
PerformanceHintManager manager =
        getSystemService(PerformanceHintManager.class);

int renderTid = renderer.getRenderThreadTid(); // 应用自己的 Linux TID 获取逻辑
long targetWorkNanos = 6_000_000L;

PerformanceHintManager.Session session =
        manager.createHintSession(new int[] {renderTid}, targetWorkNanos);

if (session != null) {
    long start = System.nanoTime();
    renderer.renderOneFrame();
    long actual = System.nanoTime() - start;
    session.reportActualWorkDuration(actual);
}
```

这段代码只在 session 创建成功后上报一次完整周期的 actual duration。系统比较 actual 与 target，尝试调整线程运行在哪些 CPU 核上或调整运行频率，使后续周期接近目标。事后上报无法修复已经超时的工作；对于可预测的负载突增，应用应提前调整自身策略，使用原生开发套件（Native Development Kit，NDK）的客户端还可发送 Android 16 新增的工作负载提示（workload hint）。

目标改变时应调用 `updateTargetWorkDuration()`。例如，帧率、渲染比例或流水线分工发生变化后，需要重新测量这组线程可用的工作预算，不能只用 `1000 / fps` 生成固定数值；FPS 表示每秒显示帧数（frames per second）。

### Android 17 的调用链

以 `android-17.0.0_r1` 为准，下面的调用链展示 Java API 如何经过本地代码、系统服务和 Power HAL 到达设备实现：

```text
PerformanceHintManager.Session
  → android_os_PerformanceHintManager.cpp
  → libandroid.so / performance_hint.cpp
  → Binder 服务 IHintManager（performance_hint）
  → HintManagerService
  → IPower / IPowerHintSession AIDL
  → 设备 Power HAL 实现
```

其中，Java 原生接口（Java Native Interface，JNI）文件通过 `dlopen("libandroid.so")` 动态加载库，再用 `dlsym()` 查找 `APerformanceHint_*` 函数符号。NDK 实现随后连接名为 `performance_hint` 的 Binder 系统服务；Binder 是 Android 的进程间通信机制。创建 session 后，周期性更新可以使用快速消息队列（Fast Message Queue，FMQ）；FMQ 不可用时，则改用 `IHintSession` 的单向异步（`oneway`）Binder 调用。排查时可以分为三层：

1. 应用是否创建了有效 session，TID、target 和 actual 是否正确。
2. framework 是否接收、校验并保持 session，应用的用户标识符（User Identifier，UID）是否仍处于允许状态。
3. 设备的 Power HAL 是否支持 HintSession，以及它如何响应这些信号。

无论上报路径使用 FMQ 还是异步 Binder，应用侧代码仍会经过 JNI、锁、参数校验和客户端批处理。合适的调用频率是“每帧或每个任务周期一次”，不应为每个很小的子任务单独创建 session 或反复上报。

### `WorkDuration`：拆分 CPU 与 GPU 工作

Android 15（API 35）公开了 `reportActualWorkDuration(WorkDuration)`。`WorkDuration` 包含工作周期开始时间、总墙钟时长（wall time，即现实时间经过了多久）、CPU wall time 和 GPU wall time，使系统能够区分受 CPU 限制（CPU-bound）、受 GPU 限制（GPU-bound）或 CPU/GPU 阶段存在重叠的流水线。它属于公开的 API 35 能力；设备能否据此产生明显收益，仍取决于系统和 Power HAL 支持。

这组字段使用 `SystemClock.uptimeNanos()` 对应的时间基准。开始时间和总时长必须大于 0，CPU / GPU 时长不能为负，且两者不能同时为 0。下面的代码分别填写这四项数据并完成一次上报：

```java
// API 35+
WorkDuration duration = new WorkDuration();
duration.setWorkPeriodStartTimestampNanos(workStartNanos);
duration.setActualTotalDurationNanos(totalWallTimeNanos);
duration.setActualCpuDurationNanos(cpuWallTimeNanos);
duration.setActualGpuDurationNanos(gpuWallTimeNanos);
session.reportActualWorkDuration(duration);
```

这段代码要求调用方已经测得同一工作周期的开始时间和各项时长。如果应用无法可靠测量 GPU 工作边界，继续使用 `reportActualWorkDuration(long)` 比填写猜测值更可靠。

### 能效模式与 Android 16 workload hint

`Session#setPreferPowerEfficiency(boolean)` 从 API 35 起公开。开启后表示这组线程可以优先采用节能调度，即使工作完成得稍慢也能接受。它适合周期明确、允许延长完成时间的任务；视频处理、同步或推理是否适用，需要根据产品的延迟目标判断，不能只按业务名称直接开启。

Java `sendHint()` 及 `CPU_LOAD_*`、`GPU_LOAD_*` 常量属于测试 API（`@TestApi`）或隐藏接口，普通应用不能依赖。NDK `performance_hint.h` 在 API 36 增加三组公开函数：

- `APerformanceHint_notifyWorkloadIncrease()`：预计下一周期 CPU、GPU 或两者负载显著增加时提前发送。
- `APerformanceHint_notifyWorkloadReset()`：工作即将开始或负载特征完全改变时，通知系统不再沿用此前的负载判断。
- `APerformanceHint_notifyWorkloadSpike()`：标记一次性的高开销周期，该周期不应代表长期负载。

系统会限制每个应用发送这些 hint 的频率；设备不支持的 hint 可能被忽略且不返回错误。它们适合报告次数较少、原因明确的负载变化，持续高负载仍应通过 target / actual 反馈表达。

### TID、协程与 `setThreads()`

HintSession 绑定 Linux TID。协程 ID、Java `Thread.getId()` 和任务 ID 都不能替代 TID。Kotlin 协程可能在 `Dispatchers.Default` 或 `Dispatchers.IO` 的不同工作线程之间迁移，但原 session 保存的线程集合不会自动随之更新。

可以采用以下策略：

- 为周期性性能任务使用受控的固定线程或自有线程池，并从真正执行工作的线程取得 TID。
- Android 14（API 34）以后用 `Session#setThreads(int[])` 替换线程集合。
- API 31—33 若线程集合已经失真，可关闭旧 session，再用当前 TID 创建新 session。

`setThreads()` 不是 `oneway` 调用。Android 17 会同步执行 `IHintManager.setHintSessionThreads()`，并校验 TID 是否属于当前应用；session 不在前台时还可能抛出 `IllegalStateException`。因此，应在线程池的线程组成发生变化或场景切换时更新，不能在每次协程调度时都调用。

## Headroom API：CPU/GPU 容量余量

Android 16（API 36）的 `SystemHealthManager#getCpuHeadroom()` 与 `getGpuHeadroom()` 返回 0—100 的容量余量（headroom）；0 表示系统当前无法再提供更多对应资源，暂时无法计算时返回 `Float.NaN`。`NaN` 是“非数值”（Not a Number）的浮点数标记。两项接口回答“当前计算资源还有多少余量”，含义不同于 Thermal Headroom。

传入 `null` 表示使用默认参数。每次有效调用至少包含一次同步 Binder 往返，即应用要等待系统服务返回结果；官方文档提示这可能超过 1 ms，第一次调用或使用非默认参数时还可能更慢。调用应放在工作线程（worker thread），并遵守以下最小间隔：

- `getCpuHeadroomMinIntervalMillis()`
- `getGpuHeadroomMinIntervalMillis()`

调用间隔过短时可能得到缓存值。若要指定计算窗口或 CPU TID，还要先查询设备支持的窗口范围，并处理参数、TID 归属和 CPU 亲和性（affinity，即线程允许运行在哪些 CPU 上）校验异常。CPU / GPU Headroom 适合在场景切换时或以较低频率调整质量，不适合放入渲染关键路径。

## Thermal API：先读懂状态，再决定降级

### Thermal Status 的语义

应用侧 Java 入口位于 `PowerManager`。`getCurrentThermalStatus()` 和 `addThermalStatusListener()` 返回系统当前的热节流（thermal throttling）等级，即系统为了控制温度而限制性能的程度。Android 17 源码对这些等级的定义如下：

| 状态 | 平台语义 | 应用侧常见处理 |
|---|---|---|
| `NONE` | 未处于 thermal throttling | 维持当前策略 |
| `LIGHT` | 轻度限制，用户体验尚未受影响 | 记录趋势，减少可延后工作 |
| `MODERATE` | 中度限制，体验尚未受到大幅影响 | 逐步降低高功耗选项 |
| `SEVERE` | 严重限制，体验会明显受影响 | 立即切入经过验证的保守配置 |
| `CRITICAL` | 平台已尽力降低功耗 | 保留关键交互与数据完整性 |
| `EMERGENCY` | 关键组件因热状态开始关闭，设备能力受限 | 尽快保存状态，停止非必要工作 |
| `SHUTDOWN` | 设备需要立即关机 | 不再假设后续工作能够完成 |

右侧策略只是工程起点。画质、帧率、相机能力或推理负载的具体降级幅度需要经过设备实测，还应加入滞回（hysteresis，即升档和降档使用不同阈值）与最短冷却时间，避免状态在阈值附近波动时频繁切换。

### Thermal Headroom 的数值与采样边界

`PowerManager#getThermalHeadroom(int forecastSeconds)` 主要使用设备外壳表面温度等变化较慢的传感器，参数范围是 0—60 秒。返回值 1.0 表示当前或预测将达到 `THERMAL_STATUS_SEVERE`；值可以大于 1.0，但 1.0 以上没有固定的状态映射。0.0 也不对应某个绝对温度。

API 文档给出的调用边界是：

- 采样频率高于约 1 Hz（每秒一次）没有收益，明显更快时可能返回 `NaN`。
- 初次采样后的几秒内，如果样本不足，接口可能只返回当前 headroom，暂不提供有效预测。
- 预测越远，不确定性越高。
- `NaN` 还可能表示设备不支持该能力。

游戏开发指南建议约每 10 秒采样一次，适合大多数持续负载。下面的代码在独立线程中定期读取 10 秒预测值和当前 Thermal Status，并跳过 `NaN`：

```java
ScheduledExecutorService thermalWorker =
        Executors.newSingleThreadScheduledExecutor();

thermalWorker.scheduleAtFixedRate(() -> {
    float forecast = powerManager.getThermalHeadroom(10);
    int status = powerManager.getCurrentThermalStatus();
    if (!Float.isNaN(forecast)) {
        applyThermalPolicy(status, forecast);
    }
}, 0, 10, TimeUnit.SECONDS);
```

这段示例只展示线程和无效值处理；`applyThermalPolicy()` 内部仍需实现滞回、冷却时间和设备标定。API 35 的 `getThermalHeadroomThresholds()` 返回设备定义的状态阈值。Android 16 起，这张表可能在运行期间变化；Java `addThermalHeadroomListener()` 与 NDK `AThermal_registerThermalHeadroomListener()` 可以接收 headroom 或阈值的显著变化。监听器（listener）不会仅因预测值变化而持续回调，因此主动预测仍需低频轮询。

### Thermal、CPU/GPU Headroom 与 Performance Hint 的分工

三类信号回答不同问题：

- Performance Hint：这组线程希望在多长时间内完成周期性工作。
- CPU/GPU Headroom：当前计算资源还有多少可授予容量。
- Thermal Status/Headroom：设备已经进入什么热限制，以及接近严重限制的趋势。

CPU 频率没有上升，不能单独证明 HintSession 失效。当前资源可能已经足够，设备也可能受 GPU、内存带宽、功耗或热限制约束。排查时需要在同一时间范围内对照工作时长、调度、频率和 thermal 数据。

## Game Mode 与 Game State

### Game Mode 表达用户偏好

`GameManager#getGameMode()` 从 Android 12（API 31）起公开，首批只覆盖部分设备；Android 13 及以后设备提供更一致的可用范围。应用需要声明为游戏（game），并在每次 `onResume()` 后重新查询模式。部分设备类型可能不提供 `GameManager` 服务，因此获取系统服务后仍要检查返回值是否为空。

模式值表达用户偏好或平台状态，不对应一套固定的画质参数：

- `GAME_MODE_STANDARD`：使用游戏默认策略。
- `GAME_MODE_PERFORMANCE`：优先低延迟和稳定高帧率，通常要在帧率与单帧画质之间重新取舍。
- `GAME_MODE_BATTERY`：优先续航，可降低目标刷新率、帧率或部分画质。
- `GAME_MODE_UNSUPPORTED`：当前应用或设备不支持。
- `GAME_MODE_CUSTOM`：Android 14 起由平台处理用户自定义配置；目标 SDK 较旧时还存在兼容返回规则。

因此，Performance 模式不应直接固定为 120 FPS 和最高画质。较高帧率往往需要降低每帧渲染成本。应用应切换到预先测试过的配置档（profile），并同步更新帧呈现节奏（frame pacing）、渲染配置和 HintSession target。下面的示例在 Activity 恢复时查询模式，并选择对应配置档：

```java
@Override
protected void onResume() {
    super.onResume();
    GameManager gameManager = getSystemService(GameManager.class);
    if (gameManager == null) {
        applyGameProfile(GameProfile.DEFAULT);
        return;
    }
    switch (gameManager.getGameMode()) {
        case GameManager.GAME_MODE_PERFORMANCE:
            applyGameProfile(GameProfile.HIGH_FRAME_RATE);
            break;
        case GameManager.GAME_MODE_BATTERY:
            applyGameProfile(GameProfile.LONG_PLAY);
            break;
        default:
            applyGameProfile(GameProfile.DEFAULT);
    }
}
```

这段代码还处理了设备不提供 `GameManager` 的情况。如果游戏声明支持 Performance / Battery Game Mode，就要实现相应调整；平台会让应用自身的优化优先于现有的设备厂商（Original Equipment Manufacturer，OEM）干预。应用没有声明支持或选择退出时，OEM 仍可能使用帧率限制（FPS throttling）、后备缓冲区缩放（backbuffer resize）等干预措施。两条路径需要在目标设备上分别验证。

### Game State 表达当前阶段

Android 13（API 33）增加 `GameManager#setGameState(GameState)`。`GameState` 包含：

- `isLoading`：是否处于加载阶段。
- `mode`：菜单 / 非活动、可中断游戏过程（gameplay）、不可中断 gameplay 或内容展示。
- `label`、`quality`：可选的开发者自定义整数标识。

下面的代码将当前阶段上报为不可中断的实时对战：

```java
GameState state = new GameState(
        false,
        GameState.MODE_GAMEPLAY_UNINTERRUPTIBLE);
gameManager.setGameState(state);
```

这次上报会把 `isLoading` 设为 `false`，并将模式设为 `MODE_GAMEPLAY_UNINTERRUPTIBLE`。`MODE_CONTENT` 用于游戏内广告、网页、文字或视频等非 gameplay 内容，不是普通视频、地图或相机应用的通用性能标签。非游戏应用应直接使用 Performance Hint 与 Headroom API。

## 一套可验证的接入流程

1. **建立基线**：在固定设备、环境温度、电量区间和运行时长下，记录未启用 ADPF 时的帧时间、功耗和热状态。
2. **选择工作单元**：找出周期稳定、线程生命周期较长的渲染、音视频或计算任务，并确认 Linux TID。
3. **定义 target**：从整个流水线预算中分配该线程组的工作时长，用 actual duration 的第 50、90、95 百分位数（P50 / P90 / P95）检查目标能否稳定达到。
4. **持续反馈**：每个工作周期上报 actual duration；场景或帧率改变后更新 target。
5. **读取约束**：在 worker thread 中低频读取 Thermal、CPU / GPU Headroom，并处理 `NaN`、能力不支持和调用异常。
6. **平滑降级**：用滞回、每档最短保持时间和逐级配置档（profile）避免频繁切换。
7. **处理生命周期**：前后台切换后校验 session 和 TID；不再使用时显式 `close()`。
8. **进行同机 A/B 对照**：在同一设备上分别启用和关闭方案，比较达到同一体验目标时的掉帧、功耗和持续稳定时间，避免只看瞬时最高频率。

## 在 Perfetto 中验证

### 采集什么

ADPF 没有向所有设备承诺提供固定名为 `power.hint_session` 或 `power.thermal` 的界面轨道（UI track）。厂商实现、trace（性能跟踪）配置和 Perfetto 版本都会影响可见数据。建议至少采集：

- FrameTimeline（系统记录的预期帧与实际帧时间线）或应用自己的帧边界，用于对照截止时间（deadline）与实际完成时间。
- `sched_switch`、`sched_wakeup` 等调度事件，观察 session 线程运行在哪些 CPU 上。
- CPU frequency 与可用的 GPU frequency / counter（随时间变化的数值轨道），用于观察资源状态。
- thermal 相关 counter，或应用自行记录的 thermal status / headroom。
- 应用自定义 trace slice（带开始和结束时间的事件区间），用于标出 target 更新、actual 上报和质量 profile 切换。

自定义 slice 用于对齐事件时间，不能据此证明 Power HAL 在同一时刻采取了某个具体动作。

### 怎样判断结果

先确定 session 覆盖的 TID 和工作周期，再从掉帧区间向外看：

1. actual duration 是否持续超过 target，还是只有一次性尖峰（spike）。
2. 关键线程是否获得更及时的运行机会，CPU/GPU 是否已经处于足够状态。
3. thermal status/headroom 是否在同一阶段恶化。
4. 质量或帧率策略是否及时调整，调整后是否出现新的流水线（pipeline）瓶颈。

成功不一定表现为更高频率。如果帧时间稳定，同时平均频率或功耗下降，系统也可能作出了更合适的决策。判断因果关系需要在同一设备上进行多轮 A/B 对照，并保持初始温度和测试场景接近；单次 trace 只能提供线索。

## 版本演进与 Android 17 边界

| 版本 | 公开能力 |
|---|---|
| Android 10（API 29） | Java Thermal Status 查询与 listener |
| Android 11（API 30） | Java `PowerManager#getThermalHeadroom()` 与 NDK thermal manager 基础接口 |
| Android 12（API 31） | Java `PerformanceHintManager`、`GameManager`；NDK `AThermal_getThermalHeadroom()` |
| Android 13（API 33） | `GameManager#setGameState(GameState)`；NDK `APerformanceHintManager`/Session |
| Android 14（API 34） | Java/NDK `setThreads()`；`GAME_MODE_CUSTOM` |
| Android 15（API 35） | `WorkDuration` 上报、`setPreferPowerEfficiency()`、Thermal Headroom thresholds |
| Android 16（API 36） | CPU / GPU Headroom；Java / NDK Thermal Headroom listener；NDK workload hint、会话配置（session config）与图形流水线关联能力 |
| Android 17（API 37） | `android-17.0.0_r1` 公开的 Java Session API 仍包括 `reportActualWorkDuration`、`setPreferPowerEfficiency`、`setThreads`、`updateTargetWorkDuration` 和生命周期接口；公开 Java / NDK API 中没有 `setPreferIdle(boolean)` |

API 37 的 `core/api/current.txt` 以及 NDK `performance_hint.h` 都没有 `setPreferIdle(boolean)`。不能把预览版 SDK（preview SDK）、厂商 SDK 或内部接口当作 Android 17 的公共能力。Java `sendHint()` 也仍属于测试或隐藏接口。

## 常见误区

### HintSession 会把 CPU 拉到最高频率

公开契约只说明系统会“尝试”调整线程所运行的 CPU 核和 / 或运行频率，使 actual 接近 target。系统可能维持当前频率、改变线程的 CPU 分配、采用厂商内部策略，也可能因热或功耗约束无法提供更多资源。

### target duration 等于整帧周期

target 只对应 session 覆盖的工作，显示周期还要容纳流水线的其他阶段。把 16.67 ms 直接交给只负责 6 ms 渲染工作的线程组，会使系统高估这组线程的时间余量。

### 掉帧后上报能够修复当前帧

actual duration 是事后反馈，主要影响后续周期。对于可以预测的大幅负载变化，可以通过 NDK 发送 workload hint，并同步减少应用自身的峰值工作；一次性且不可预测的 spike 仍可能导致掉帧。

### Thermal Headroom 和 CPU/GPU Headroom 可以互换

Thermal Headroom 表示接近严重热限制的程度；CPU/GPU Headroom 表示当前可授予的计算容量。设备可能热余量尚可但 GPU 已满，也可能 CPU 有余量却因皮肤温度接近阈值而需要降级。

### ADPF 只适用于游戏

Performance Hint API 可服务相机预览、视频编辑、增强现实（Augmented Reality，AR）、地图和周期性推理等前台工作。Game Mode / Game State 只面向游戏；非游戏应用无需借用游戏语义。

## 游戏引擎接入

Unity 官方 Android provider（平台适配组件）支持 Unity 2021.3 及以上、Adaptive Performance 5.0 及以上；Unity 2021 / 2022 的包管理器可能默认安装 4.0，需要手动升级。官方还建议使用较新的 Android provider 1.2；1.0 只在 Pixel 设备上启用。provider 会逐帧上报 target 和 CPU / GPU actual duration；项目仍要根据自身内容调校分辨率、细节层级（Level of Detail，LOD）、阴影和帧率调节器（scaler）。

Android Developers 提供 Unreal ADPF 插件（plugin）；当前引擎支持表列出 Unreal Engine 4.25 及以上。插件分别为游戏线程（game thread）与渲染 / 渲染硬件接口线程（Render Hardware Interface，RHI）建立 hint session，并结合 thermal 信号调整 Unreal 的可扩展画质系统（Scalability）。默认设置只适合作为起点，项目应保留同机基线和自定义质量档位。

引擎自动接入不免除 TID、target、热策略和 trace 验证。引擎升级、渲染线程模型变化后，应重新核对 session 覆盖范围。

## OEM 差异应怎样验证

Android 17 的稳定公共约定止于 framework 的 `IHintManager` 与 `android.hardware.power` AIDL。`IPowerHintSession` 提供 target、actual、线程集合（thread set）、会话模式（session mode）等接口，但这些信号如何映射到调度器、CPU / GPU 策略或厂商控制器，不在公共 API 的保证范围内。

因此，不应仅凭 SoC 品牌推断设备使用 PerfLock（部分厂商的私有性能锁机制）、某个私有服务或固定响应时间。跨设备测试至少记录：

- `createHintSession()` 是否返回有效 session。
- 同一 target/actual 序列下的帧时间和关键线程调度。
- 初始温度、电量、充电状态和持续运行时间。
- CPU / GPU / thermal 变化，以及未启用 ADPF 时的对照结果。
- 前后台切换、刷新率变化、线程重建后的行为。

具备系统权限或使用工程机时，可以结合系统服务诊断命令 `dumpsys performance_hint`、Power HAL 日志和厂商 trace 进一步定位；普通应用应以公开 API 返回值和可观测性能为准。

## 与其他章节的关系

- [5.2 DVFS、Thermal 与 Android 功耗管理](02-dvfs-thermal-android-power.md)：解释 EAS/DVFS、应用侧 Thermal API、Thermal HAL 与系统功耗约束怎样共同影响性能请求。
- [7.2 卡顿分析方法、典型场景与案例](../../part2-performance/ch07-smoothness/02-jank-methodology-scenarios-cases.md)：动态画质、帧率和负载分级的验证方法。
- [14.7 Perfetto SQL、SPAN_JOIN 与 Jank CUJ](../../part3-tools/ch14-perfetto/07-perfetto-sql-span-join-jank-cuj.md)：用关键用户操作流程（Critical User Journey，CUJ）查询帧、调度与 counter 数据。

## 参考资料

- [Android Dynamic Performance Framework](https://developer.android.com/games/optimize/adpf)
- [PerformanceHintManager.Session API reference](https://developer.android.com/reference/android/os/PerformanceHintManager.Session)
- [PowerManager Thermal API reference](https://developer.android.com/reference/android/os/PowerManager)
- [SystemHealthManager API reference](https://developer.android.com/reference/android/os/health/SystemHealthManager)
- [Game Mode API](https://developer.android.com/games/optimize/adpf/gamemode/gamemode-api)
- [Game State API](https://developer.android.com/games/optimize/adpf/gamemode/gamestate-api)
- [Game Mode interventions](https://developer.android.com/games/optimize/adpf/gamemode/gamemode-interventions)
- [Unity Adaptive Performance and Android provider](https://developer.android.com/games/engines/unity/unity-adpf)
- [ADPF Unreal Engine plugin](https://developer.android.com/games/engines/unreal/unreal-adpf)
- [AOSP `PerformanceHintManager.java`（android-17.0.0_r1）](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/os/PerformanceHintManager.java)
- [AOSP `android_os_PerformanceHintManager.cpp`（android-17.0.0_r1）](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/jni/android_os_PerformanceHintManager.cpp)
- [AOSP `performance_hint.cpp`（android-17.0.0_r1）](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/native/android/performance_hint.cpp)
- [AOSP `HintManagerService.java`（android-17.0.0_r1）](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/power/hint/HintManagerService.java)
- [AOSP NDK `performance_hint.h`（android-17.0.0_r1）](https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/include/android/performance_hint.h)
- [AOSP Power AIDL `IPower.aidl`（android-17.0.0_r1）](https://android.googlesource.com/platform/hardware/interfaces/+/refs/tags/android-17.0.0_r1/power/aidl/android/hardware/power/IPower.aidl)
- [AOSP Power AIDL `IPowerHintSession.aidl`（android-17.0.0_r1）](https://android.googlesource.com/platform/hardware/interfaces/+/refs/tags/android-17.0.0_r1/power/aidl/android/hardware/power/IPowerHintSession.aidl)
