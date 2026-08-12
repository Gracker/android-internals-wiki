---
status: "finalized"
title: ADPF 自适应性能框架
chapter: '5.9'
section: '5.9'
applicable_versions: Android 11 (API 30, Thermal Headroom 基础能力) - Android 17 (API
  37)
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
- '13.14'
confidence: medium
last_verified: '2026-08-08'
consolidated_from:
  - "src/part1-fundamentals/ch05-cpu-power/5.19-ondevice-ai-adpf-intelligent-scheduling.md"
  - "src/part1-fundamentals/ch05-cpu-power/5.29-android17-gpu-dvfs-headroom-power-advisor.md"
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
pipeline_stage: "ready-to-publish"
task6_state: reviewed
task9_state: "reviewed"
task2b_state: "fixed"
last_idle_audit_at: "2026-08-08T18:35:19+08:00"
last_idle_audit_run_id: "20260808-183519-idle-audit-87d42442"
---
# 5.9 ADPF 自适应性能框架

## 为什么需要 ADPF

移动设备的峰值性能由 SoC、供电和散热条件共同限制，应用负载却会不断变化。游戏可能在团战、粒子爆发或资源流式加载时突然变重；地图、相机和视频编辑也会出现相似的周期性负载。只依靠内核调度器和调频策略观察历史利用率，系统只能在负载出现后再响应。

高刷新率会放大这段时间差。120 Hz 的显示周期约为 8.33 ms，但一次渲染工作并不独占整个周期：输入、应用、RenderThread、GPU、SurfaceFlinger 和显示提交都要分享预算。某个线程组若突然多做了几毫秒工作，当前帧可能已经无法挽回。

ADPF（Android Dynamic Performance Framework）给应用增加了两类信号：

- 应用通过 Performance Hint API 报告周期性工作的目标时长、实际时长和线程集合，系统据此尝试调整这些线程的调度与性能。
- 应用通过 Thermal API、CPU/GPU Headroom API 读取设备约束，提前降低分辨率、特效、帧率或后台负载。

Game Mode 和 Game State 又补充了用户偏好与游戏阶段。它们共同改善系统与应用之间的信息差，但不承诺某个频点、某颗 CPU 或某次提频延迟。Android 17 的 Power AIDL 也明确允许平台按自身策略实现；应用仍需准备无 ADPF、能力不完整以及热约束优先的路径。

## Performance Hint API：周期性工作的反馈回路

### HintSession、target duration 与 actual duration

Java 入口是 `PerformanceHintManager.Session`。创建 session 时需要传入一组 Linux TID 和初始 target work duration；创建结果可为 `null`，表示设备不支持 HintSession，或某个 TID 不属于本应用。session 应覆盖一组关系紧密、生命周期较长、周期性执行的线程。

target work duration 表示这组线程每个周期希望完成工作的时长。它通常小于显示周期。以 60 Hz 渲染为例，显示周期约为 16.67 ms；如果纳入 session 的线程只负责其中 6 ms 的 CPU 工作，target 应接近 6 ms，而非直接填写 16.67 ms。Android 17 的 `IPower.createHintSession*()` 注释也使用了“60 Hz 渲染、目标工作时长 6 ms”的例子。

下面的代码展示基本反馈方式。`renderTid` 必须在对应线程中取得或由应用自己的线程管理器提供，不能拿 Java `Thread.getId()` 代替 Linux TID。

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

应用应在每个完整工作周期结束时上报 actual duration。系统比较 actual 与 target，尝试调整线程放置或运行频率，使后续周期接近目标。一次已经超时的工作不会因事后上报而恢复；可预测的负载跳变应提前调整业务策略，NDK 客户端还可使用 Android 16 增加的 workload hint。

目标改变时调用 `updateTargetWorkDuration()`。例如帧率、渲染比例或流水线分工发生变化后，要重新测量这组线程可用的工作预算，而不能只用 `1000 / fps` 生成一个固定数字。

### Android 17 的调用链

以 `android-17.0.0_r1` 为准，Java 调用经过以下层次：

```text
PerformanceHintManager.Session
  → android_os_PerformanceHintManager.cpp
  → libandroid.so / performance_hint.cpp
  → Binder 服务 IHintManager（performance_hint）
  → HintManagerService
  → IPower / IPowerHintSession AIDL
  → 设备 Power HAL 实现
```

JNI 文件通过 `dlopen("libandroid.so")` 和 `dlsym()` 绑定 `APerformanceHint_*` 符号。NDK 实现再连接名为 `performance_hint` 的 Binder 服务。创建 session 后，周期性更新可使用 FMQ；FMQ 不可用时退回 `IHintSession` 的 `oneway` 调用。排查时分为三层：

1. 应用是否创建了有效 session，TID、target 和 actual 是否正确。
2. framework 是否接收、校验并保持 session，应用 UID 是否仍在允许状态。
3. 设备的 Power HAL 是否支持 HintSession，以及它怎样响应这些信号。

上报路径可能使用 FMQ，也可能经过异步 Binder，应用代码仍会经过 JNI、锁、参数校验和客户端批处理。合适的调用粒度是“每个帧或任务周期一次”，不应给每个细碎子任务单独建 session 或反复上报。

### `WorkDuration`：拆分 CPU 与 GPU 工作

Android 15（API 35）公开了 `reportActualWorkDuration(WorkDuration)`。`WorkDuration` 包含工作周期开始时间、总 wall time、CPU wall time 和 GPU wall time，使系统能区分 CPU-bound、GPU-bound 或重叠流水线。它是公开 API 35 能力；设备能否据此产生明显收益仍取决于系统和 Power HAL 支持。

这组字段使用 `SystemClock.uptimeNanos()` 对应的时间基准。开始时间和总时长必须大于 0，CPU/GPU 时长不能为负，而且两者不能同时为 0。

```java
// API 35+
WorkDuration duration = new WorkDuration();
duration.setWorkPeriodStartTimestampNanos(workStartNanos);
duration.setActualTotalDurationNanos(totalWallTimeNanos);
duration.setActualCpuDurationNanos(cpuWallTimeNanos);
duration.setActualGpuDurationNanos(gpuWallTimeNanos);
session.reportActualWorkDuration(duration);
```

如果应用无法可靠测得 GPU 工作边界，继续使用 `reportActualWorkDuration(long)` 比填入猜测值更稳妥。

### 能效模式与 Android 16 workload hint

`Session#setPreferPowerEfficiency(boolean)` 从 API 35 起公开。开启后表示这组线程可以优先采用节能调度，即便工作完成得更慢一些也可接受。它适合有明确周期、又允许延长完成时间的任务；是否适合视频处理、同步或推理，需要由产品延迟目标决定，不能按业务名称直接开启。

Java `sendHint()` 及 `CPU_LOAD_*`、`GPU_LOAD_*` 常量属于 `@TestApi`/隐藏接口，普通应用不能依赖。NDK `performance_hint.h` 在 API 36 增加三组公开函数：

- `APerformanceHint_notifyWorkloadIncrease()`：预计下一周期 CPU、GPU 或两者负载显著增加时提前发送。
- `APerformanceHint_notifyWorkloadReset()`：工作即将开始或负载特征完全改变，要求系统丢弃旧假设。
- `APerformanceHint_notifyWorkloadSpike()`：标记一次性的高开销周期，该周期不应代表长期负载。

这些 hint 有每应用限流，未支持的 hint 会被静默丢弃。它们用于少量、可解释的负载变化，持续高负载仍靠 target/actual 反馈。

### TID、协程与 `setThreads()`

HintSession 绑定 Linux TID。协程 ID、Java `Thread.getId()`、任务 ID 都不能替代 TID。Kotlin 协程在 `Dispatchers.Default` 或 `Dispatchers.IO` 上迁移后，原 session 的线程集合不会自动跟随。

可以采用以下策略：

- 为周期性性能任务使用受控的固定线程或自有线程池，并从执行线程取得 TID。
- Android 14（API 34）以后用 `Session#setThreads(int[])` 替换线程集合。
- API 31—33 若线程集合已经失真，可关闭旧 session，再用当前 TID 创建新 session。

`setThreads()` 不是 `oneway`。Android 17 的调用会同步经过 `IHintManager.setHintSessionThreads()`，并校验 TID 是否属于当前应用；session 不在前台时还可能抛出 `IllegalStateException`。因此应在线程池拓扑或场景切换时更新，不能跟随每次协程调度调用。

## Headroom API：CPU/GPU 容量余量

Android 16（API 36）的 `SystemHealthManager#getCpuHeadroom()` 与 `getGpuHeadroom()` 返回 0—100 的容量余量；0 表示系统无法再授予更多对应资源，暂时无法计算时返回 `Float.NaN`。它们回答“当前计算资源还有多少余量”，含义不同于 Thermal Headroom。

传 `null` 使用默认参数。每次有效调用至少包含一次同步 Binder 往返，官方文档提示它可能超过 1 ms；第一次调用或使用非默认参数时还可能更慢。正确的调用位置是 worker thread，并应遵守：

- `getCpuHeadroomMinIntervalMillis()`
- `getGpuHeadroomMinIntervalMillis()`

调用间隔过短时可能得到缓存值。若要指定计算窗口或 CPU TID，还要先查询设备支持的窗口范围，并处理参数、TID 归属和 affinity 校验异常。CPU/GPU Headroom 适合场景切换或低频质量调整，不适合进入渲染关键路径。

## Thermal API：先读懂状态，再决定降级

### Thermal Status 的语义

应用侧 Java 入口位于 `PowerManager`。`getCurrentThermalStatus()` 和 `addThermalStatusListener()` 给出系统已经进入的 throttling 等级。Android 17 源码对这些等级的定义如下：

| 状态 | 平台语义 | 应用侧常见处理 |
|---|---|---|
| `NONE` | 未处于 thermal throttling | 维持当前策略 |
| `LIGHT` | 轻度限制，用户体验尚未受影响 | 记录趋势，减少可延后工作 |
| `MODERATE` | 中度限制，体验尚未受到大幅影响 | 逐步降低高功耗选项 |
| `SEVERE` | 严重限制，体验会明显受影响 | 立即切入经过验证的保守配置 |
| `CRITICAL` | 平台已尽力降低功耗 | 保留关键交互与数据完整性 |
| `EMERGENCY` | 关键组件因热状态开始关闭，设备能力受限 | 尽快保存状态，停止非必要工作 |
| `SHUTDOWN` | 设备需要立即关机 | 不再假设后续工作能够完成 |

右侧策略只是工程起点。画质、帧率、相机能力或推理负载的具体降级幅度要经过设备实测，并加入滞回和冷却时间，避免状态在阈值附近波动时频繁切换。

### Thermal Headroom 的数值与采样边界

`PowerManager#getThermalHeadroom(int forecastSeconds)` 关注皮肤温度等慢变化传感器，参数范围是 0—60 秒。返回值 1.0 对应当前或预测将到达 `THERMAL_STATUS_SEVERE`；值可以大于 1.0，但 1.0 以上没有固定的状态映射。0.0 也不代表某个绝对温度。

API 文档给出的调用边界是：

- 高频于约 1 Hz 没有收益，明显更快时可能返回 `NaN`。
- 初次采样后的几秒内，样本不足时可能只返回当前 headroom，暂不提供有效预测。
- 预测越远，不确定性越高。
- `NaN` 还可能表示设备不支持该能力。

游戏开发指南建议以约 10 秒一次的节奏采样，适合大多数持续负载。以下代码只展示线程与异常边界；`applyThermalPolicy()` 内部仍要做滞回、冷却和设备标定。

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

API 35 的 `getThermalHeadroomThresholds()` 返回设备定义的状态阈值。Android 16 起，这张表可能在运行期间变化；Java `addThermalHeadroomListener()` 与 NDK `AThermal_registerThermalHeadroomListener()` 可接收 headroom 或阈值的显著变化。listener 不会因预测值单独变化而持续回调，所以主动预测仍需低频轮询。

### Thermal、CPU/GPU Headroom 与 Performance Hint 的分工

三类信号回答不同问题：

- Performance Hint：这组线程希望在多长时间内完成周期性工作。
- CPU/GPU Headroom：当前计算资源还有多少可授予容量。
- Thermal Status/Headroom：设备已经进入什么热限制，以及接近严重限制的趋势。

CPU 频率没有上升，并不能单独证明 HintSession 失效。当前资源可能已经足够，设备也可能受 GPU、内存带宽、功耗或热限制约束。排查时需要把工作时长、调度、频率和 thermal 数据放在同一时间范围内观察。

## Game Mode 与 Game State

### Game Mode 表达用户偏好

`GameManager#getGameMode()` 从 Android 12（API 31）起公开，首批只覆盖部分设备；Android 13 及以后设备提供更一致的可用范围。应用需要声明为 game，并在每次 `onResume()` 后重新查询模式。部分设备类型可能不发布 `GameManager`，获取系统服务后仍要检查空值。

模式值表达用户偏好或平台状态，不等于固定的画质表：

- `GAME_MODE_STANDARD`：使用游戏默认策略。
- `GAME_MODE_PERFORMANCE`：优先低延迟和稳定高帧率，通常要在帧率与单帧画质之间重新取舍。
- `GAME_MODE_BATTERY`：优先续航，可降低目标刷新率、帧率或部分画质。
- `GAME_MODE_UNSUPPORTED`：当前应用或设备不支持。
- `GAME_MODE_CUSTOM`：Android 14 起由平台处理用户自定义配置；旧 target SDK 还存在兼容返回规则。

因此，Performance 模式不应直接写死为 120 fps 和最高画质。较高帧率往往需要降低每帧渲染成本。应用应切换到预先测过的 profile，并同步更新 frame pacing、渲染配置和 HintSession target。

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

如果游戏声明自己支持 Performance/Battery Game Mode，就要实现对应调整；平台会让应用自己的优化优先于既有 OEM intervention。没有声明或选择退出时，OEM 仍可能使用 FPS throttling、backbuffer resize 等 intervention。二者要在目标设备上分别验证。

### Game State 表达当前阶段

Android 13（API 33）增加 `GameManager#setGameState(GameState)`。`GameState` 包含：

- `isLoading`：是否处于加载阶段。
- `mode`：菜单/非活动、可中断 gameplay、不可中断 gameplay 或内容展示。
- `label`、`quality`：可选的开发者自定义整数标识。

上报不可中断实时对战可写成：

```java
GameState state = new GameState(
        false,
        GameState.MODE_GAMEPLAY_UNINTERRUPTIBLE);
gameManager.setGameState(state);
```

`MODE_CONTENT` 用于游戏内广告、网页、文字或视频等非 gameplay 内容，不是普通视频、地图或相机应用的通用性能标签。非游戏应用应直接使用 Performance Hint 与 Headroom API。

## 一套可验证的接入流程

1. **建立基线**：在固定设备、环境温度、电量区间和运行时长下记录无 ADPF 的帧时间、功耗和热状态。
2. **选择工作单元**：找出周期稳定、线程生命周期较长的渲染、音视频或计算任务，并确认 Linux TID。
3. **定义 target**：从整个流水线预算中分配该线程组的工作时长，以 P50/P90/P95 actual duration 检查目标是否可达。
4. **持续反馈**：每个工作周期上报 actual duration；场景或帧率改变后更新 target。
5. **读取约束**：在 worker thread 低频读取 Thermal、CPU/GPU Headroom，处理 `NaN`、不支持和异常。
6. **平滑降级**：用滞回、最短驻留时间和逐级 profile 避免频繁切换。
7. **处理生命周期**：前后台切换后校验 session 和 TID；不再使用时显式 `close()`。
8. **做同机 A/B**：比较达到同一体验目标时的掉帧、功耗和持续稳定时间，避免只看瞬时最高频率。

## 在 Perfetto 中验证

### 采集什么

ADPF 没有向所有设备承诺固定名为 `power.hint_session` 或 `power.thermal` 的 UI track。厂商实现、trace 配置和 Perfetto 版本都会影响可见数据。建议至少采集：

- FrameTimeline 或应用自己的帧边界，确认 deadline 与实际完成时间。
- `sched_switch`、`sched_wakeup` 等调度事件，观察 session 线程运行在哪些 CPU 上。
- CPU frequency 与可用的 GPU frequency/counter，观察资源状态。
- thermal 相关 counter 或应用记录的 thermal status/headroom。
- 应用自定义 trace slice，标出 target 更新、actual 上报和质量 profile 切换。

自定义 slice 的价值是对齐时间，不代表它能证明 Power HAL 在同一时刻采取了某个动作。

### 怎样判断结果

先确定 session 覆盖的 TID 和工作周期，再从掉帧区间向外看：

1. actual duration 是否持续超过 target，还是只有一次性 spike。
2. 关键线程是否获得更及时的运行机会，CPU/GPU 是否已经处于足够状态。
3. thermal status/headroom 是否在同一阶段恶化。
4. 质量或帧率策略是否及时调整，调整后是否出现新的 pipeline 瓶颈。

成功不一定表现为更高频率。若帧时间稳定且平均频率或功耗下降，系统同样可能做出了更合适的决策。因果判断需要同机多轮 A/B、相近初始温度和一致场景，单次 trace 只能提供线索。

## 版本演进与 Android 17 边界

| 版本 | 公开能力 |
|---|---|
| Android 10（API 29） | Java Thermal Status 查询与 listener |
| Android 11（API 30） | Java `PowerManager#getThermalHeadroom()` 与 NDK thermal manager 基础接口 |
| Android 12（API 31） | Java `PerformanceHintManager`、`GameManager`；NDK `AThermal_getThermalHeadroom()` |
| Android 13（API 33） | `GameManager#setGameState(GameState)`；NDK `APerformanceHintManager`/Session |
| Android 14（API 34） | Java/NDK `setThreads()`；`GAME_MODE_CUSTOM` |
| Android 15（API 35） | `WorkDuration` 上报、`setPreferPowerEfficiency()`、Thermal Headroom thresholds |
| Android 16（API 36） | CPU/GPU Headroom；Java/NDK Thermal Headroom listener；NDK workload hint、session config 与图形流水线关联能力 |
| Android 17（API 37） | `android-17.0.0_r1` 公开 Java Session 面仍是 `reportActualWorkDuration`、`setPreferPowerEfficiency`、`setThreads`、`updateTargetWorkDuration` 和生命周期接口；公开 Java/NDK API 中没有 `setPreferIdle(boolean)` |

API 37 的 `core/api/current.txt` 以及 NDK `performance_hint.h` 都没有 `setPreferIdle(boolean)`。不要把 preview SDK、厂商 SDK 或内部接口当成 Android 17 公共能力。Java `sendHint()` 也仍是测试/隐藏面。

## 常见误区

### HintSession 会把 CPU 拉到最高频率

公开契约只说系统“尝试”调整线程放置和/或运行频率，使 actual 接近 target。系统可能维持频率、改变 CPU 放置、使用厂商内部策略，也可能因热或功耗约束无法追加资源。

### target duration 等于整帧周期

target 属于 session 所覆盖的工作。显示周期还要容纳流水线其他阶段。把 16.67 ms 原样交给只负责 6 ms 渲染工作的线程组，会让系统误判余量。

### 掉帧后上报能够修复当前帧

actual duration 是反馈，主要影响后续周期。可预测的大幅负载变化可在 NDK 使用 workload hint，并同步降低应用自身的峰值工作；一次性不可预测 spike 仍可能掉帧。

### Thermal Headroom 和 CPU/GPU Headroom 可以互换

Thermal Headroom 表示接近严重热限制的程度；CPU/GPU Headroom 表示当前可授予的计算容量。设备可能热余量尚可但 GPU 已满，也可能 CPU 有余量却因皮肤温度接近阈值而需要降级。

### ADPF 只适用于游戏

Performance Hint API 可服务相机预览、视频编辑、AR、地图和周期性推理等前台工作。Game Mode/Game State 只面向游戏；非游戏应用无需借用游戏语义。

## 游戏引擎接入

Unity 官方 Android provider 支持 Unity 2021.3 及以上、Adaptive Performance 5.0 及以上；Unity 2021/2022 的包管理器可能默认得到 4.0，需要手动升级。官方还建议使用较新的 Android provider 1.2，而非仅在 Pixel 启用的 1.0。provider 会按帧上报 target 和 CPU/GPU actual duration，项目仍要按自己的内容调校分辨率、LOD、阴影和帧率 scaler。

Android Developers 提供 Unreal ADPF plugin；当前引擎支持表列出 Unreal Engine 4.25 及以上。插件分别为 game thread 与 render/RHI 线程建立 hint session，并结合 thermal 信号调整 Unreal Scalability。默认设置只适合作为起点，项目应保留同机基线和自定义质量阶梯。

引擎自动接入不免除 TID、target、热策略和 trace 验证。引擎升级、渲染线程模型变化后，应重新核对 session 覆盖范围。

## OEM 差异应怎样验证

Android 17 的稳定契约止于 framework `IHintManager` 与 `android.hardware.power` AIDL。`IPowerHintSession` 提供 target、actual、thread set、session mode 等接口，具体如何映射到调度器、CPU/GPU 策略或厂商控制器不在公共 API 保证范围内。

因此，不应仅凭 SoC 品牌推断 PerfLock、某个私有服务或固定响应时间。跨设备测试至少记录：

- `createHintSession()` 是否返回有效 session。
- 同一 target/actual 序列下的帧时间和关键线程调度。
- 初始温度、电量、充电状态和持续运行时间。
- CPU/GPU/thermal 变化，以及无 ADPF 的对照结果。
- 前后台切换、刷新率变化、线程重建后的行为。

有系统权限或工程机时，可结合 `dumpsys performance_hint`、Power HAL 日志和厂商 trace 扩展定位；普通应用以公开 API 返回值和可观测性能为准。

## 与其他章节的关系

- **§5.5 Thermal 管控**：这里关注应用侧 Thermal API，§5.5 解释 Thermal HAL、系统服务和内核温控。
- **§5.6 Android 功耗管理**：EAS、DVFS 与功耗约束决定设备怎样响应性能请求。
- **§7.5 优化策略**：动态画质、帧率和负载分级是消费 ADPF 信号的应用策略。
- **§13.14 Perfetto DataGrid 与 Jank CUJ 标准库**：可用于查询帧、调度与 counter 数据。

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
