---
title: "Android 17 Perfetto 数据源边界与验证"
chapter: "13.17"
section: "13.17"
status: finalized
drafted_date: "2026-06-16"
drafted_by: "openclaw-task2a"
applicable_versions: "Android 12 (API 31) - Android 17 (API 37)"
last_verified: "2026-08-07"
last_verified_against: "AOSP android-17.0.0_r1"
confidence: high
sources:
  - type: aosp_tag
    path: "android-17.0.0_r1"
  - type: DeepResearch
    path: "DeepResearch/2026-06-08-android-17-perfetto-data-sources-boundary-verification.md"
  - type: aosp
    path: "frameworks/native/services/surfaceflinger/Scheduler/FrameTimeline.h"
  - type: aosp
    path: "frameworks/native/services/surfaceflinger/Scheduler/FrameTimeline.cpp"
  - type: aosp
    path: "frameworks/native/services/surfaceflinger/SurfaceFlinger.cpp"
  - type: aosp
    path: "external/perfetto/src/profiling/perf/traced_perf.cc"
  - type: aosp
    path: "external/perfetto/src/profiling/perf/perf_producer.cc"
  - type: aosp
    path: "frameworks/native/libs/gui/include/gui/JankInfo.h"
  - type: aosp
    path: "frameworks/native/services/surfaceflinger/Jank/JankTracker.cpp"
  - type: aosp
    path: "frameworks/native/services/surfaceflinger/TimeStats/TimeStats.cpp"
  - type: aosp
    path: "frameworks/native/services/surfaceflinger/Layer.cpp"
  - type: aosp
    path: "frameworks/native/services/surfaceflinger/CompositionEngine/src/OutputLayer.cpp"
  - type: aosp
    path: "frameworks/native/services/surfaceflinger/CompositionEngine/include/compositionengine/impl/OutputLayerCompositionState.h"
  - type: aosp
    path: "frameworks/native/services/surfaceflinger/FrameTracer/FrameTracer.cpp"
  - type: aosp
    path: "external/perfetto/protos/perfetto/trace/android/graphics_frame_event.proto"
  - type: aosp
    path: "external/perfetto/src/trace_processor/importers/proto/graphics_frame_event_parser.cc"
  - type: aosp
    path: "external/perfetto/src/trace_processor/importers/proto/frame_timeline_event_parser.cc"
  - type: aosp
    path: "external/perfetto/traced_perf.rc"
  - type: aosp
    path: "external/perfetto/src/profiling/common/producer_support.cc"
  - type: aosp
    path: "external/perfetto/src/traced/service/builtin_producer.cc"
  - type: aosp
    path: "external/perfetto/protos/perfetto/config/profiling/perf_event_config.proto"
  - type: android_kernel
    path: "android17-6.18-2026-06_r6/kernel/events/core.c"
tags: ['perfetto', 'android17', 'data-sources', 'trace-capture', 'verification']
related_chapters: ["13.2", "13.9", "13.14"]
pipeline_stage: "finalized"
task6_state: "reviewed"
task6_result: pass-deep-review
task9_state: "reviewed"
reviewed_by: "hermes-aiw-review-finalize-apply"
reviewed_date: "2026-08-07"
last_task6_at: "2026-08-07T16:35:30+08:00"
last_task6_audit: "2026-06-25"
# task2b_state restored 2026-06-16 by Task9 — Android 17 重基完成 2026-06-22
task9_result: "auto-fixed"
task2b_result: "fixed"
task2b_state: "fixed"
task9_reviewed_by: "openclaw-task9"
task9_reviewed_date: "2026-06-23"
last_task9_at: "2026-06-23T01:30:06+08:00"
last_task9_review_log: "logs/deep-review/2026-06-23-01-deep-review.md"
last_task2b_lite_at: 2026-06-22
task9_review_notes: "2026-06-23 Task9 deep-review：auto-fix Android 17 重基后的源码行号、ShouldRejectDueToFilter 片段、linux.perf/traced_perf 版本归因与 readtracefs 权限用途；无剩余 P0/P1，回到 Task6 复审。"
last_task9_autofix_at: "2026-06-23"
auto_promoted_at: "2026-06-16T23:16:33+08:00"
last_task9_audit: "2026-06-22"
last_task2b_at: "2026-06-23T00:51:41+08:00"
deepseek_cn_review_state: done
last_deepseek_cn_review_at: 2026-06-27
last_rework_at: "2026-08-07T09:35:31+08:00"
last_rework_run_id: "20260807-093531-rework-28453939"
rework_notes: "Cleared open-verification outline wording and expanded source anchors to match the Android 17/Perfetto/kernel evidence cited by the body; returned from finalized to ready-for-review for Task6 re-review."
last_deep_review_at: "2026-08-07T16:35:30+08:00"
last_deep_review_run_id: "20260807-163530-deep-review-28453939"
deep_review_notes: "Task6 deep-review：复核 Android 17 Perfetto 图形数据源与 linux.perf 源码边界，收敛示例配置/回归检查措辞；无 P0/P1，进入 Task9 pending。"
last_review_finalize_at: "2026-08-07T22:07:21+08:00"
last_review_finalize_run_id: "20260807-220520-fa5b5c77"
review_finalize_notes: "Review-finalize 复核 android-17.0.0_r1 / android17-6.18 源码锚点、既有 findings 与章节边界；未发现开放 P0/P1/P2，正文无需再改，推进 finalized。"
---


# Android 17 Perfetto 数据源边界与验证

## 范围

平台基线是 AOSP `android-17.0.0_r1`，内核基线是 `android17-6.18-2026-06_r6`。核对范围包括 `android.surfaceflinger.frametimeline`、`android.surfaceflinger.frame` 和 `linux.perf` 的注册、启停、数据语义与验证方法。

## 核心发现

Android 17 的源码边界可以压缩成四点：

- SurfaceFlinger 在 boot finished 阶段注册两个图形数据源；注册成功只代表可被 trace session 选择，未开启 session 时不会写 Perfetto packet。
- `JankType` 从 Android 16 的 11 个枚举值扩展到 16 个。Android 17 同时保留 legacy 与 experimental 分类结果，活动结果由 aconfig flag 选择。
- `JankClassificationThresholds` 仍有 `presentThreshold`、`deadlineThreshold`、`startThreshold` 三个字段。Android 17 取消的是 Android 16 的 2ms/4ms 两档 present 阈值。
- `linux.perf` 由 tracing service 按需拉起 `traced_perf`。数据源被列出、daemon 已连接、采样结果可用是三个不同检查层级；产品内核、LSM/SELinux、build 类型、session 发起方和目标进程的 profileable 状态都可能限制采样。


## 1. `android.surfaceflinger.frametimeline` 数据源

### 1.1 数据源注册机制

下面的常量是 TraceConfig 必须使用的精确数据源名称：

```cpp
static constexpr char kFrameTimelineDataSource[] = "android.surfaceflinger.frametimeline";
```

名称匹配区分大小写。配置中的 `data_sources.config.name` 必须与它完全一致。

下面的注册入口来自 `FrameTimeline.cpp`。它初始化 Perfetto system backend，再向 tracing service 注册 descriptor：

```cpp
void FrameTimeline::onBootFinished() {
    perfetto::TracingInitArgs args;
    args.backends = perfetto::kSystemBackend;          // 系统后端 = traced
    perfetto::Tracing::Initialize(args);
    registerDataSource();
}

void FrameTimeline::registerDataSource() {
    perfetto::DataSourceDescriptor dsd;
    dsd.set_name(kFrameTimelineDataSource);
    FrameTimelineDataSource::Register(dsd);
}
```

`Register()` 让 tracing service 知道该 data source 可用；只有 trace session 选择它之后，SurfaceFlinger 才开始写 packet。

注册发生在 SurfaceFlinger 收到 boot finished 回调时。下面的调用顺序还表明 FrameTracer 会稍早完成初始化：

```cpp
// SurfaceFlinger.cpp line 815-820
const nsecs_t now = systemTime();
const nsecs_t duration = now - mBootTime;
ALOGI("Boot is finished (%ld ms)", long(ns2ms(duration)));
mFrameTracer->initialize();
mFrameTimeline->onBootFinished();     // <-- 注册点
```

boot finished 是注册边界，不是第一帧 packet 的时间戳。此前执行 `perfetto --query` 可能看不到这两个 SurfaceFlinger data source。

### 1.2 Jank 类型状态机

`FrameTimeline.cpp` 的 `SurfaceFrame::classifyJankLocked()` 与 `DisplayFrame::classifyJank()`共同完成分类。`JankType` 是位掩码；一帧可以同时带有主原因和上下文标记。它不能按“低、中、高”解释，严重度由独立的 `JankSeverityType` 表达。

Android 17 的 16 个枚举值可以按用途分组：

| 分组 | 枚举 | 解释边界 |
|---|---|---|
| 正常值 | `None` | 当前分类口径下没有 jank |
| 显示/SF | `DisplayHAL`、`SurfaceFlingerCpuDeadlineMissed`、`SurfaceFlingerGpuDeadlineMissed`、`SurfaceFlingerScheduling`、`SurfaceFlingerStuffing` | 需要结合 SF 的 start/end、GPU fence、present 时间和前一帧判断 |
| App/队列 | `AppDeadlineMissed`、`BufferStuffing`、`AppResyncedJitter` | App deadline、BufferQueue 堆积与 App 调整 vsync 时间是不同证据 |
| 数据不足或丢帧 | `PredictionError`、`Unknown`、`Dropped` | 分别表示预测偏差、无法归类和被新帧替换 |
| 非动画/显示状态 | `NonAnimating`、`DisplayNotOn`、`DisplayModeChangeInProgress`、`DisplayPowerModeChangeInProgress` | 用来标识非动画或显示状态变化，避免把所有 late present 都计作可感知性能问题 |

Android 16 的 `JankInfo.h` 到 `Dropped` 为止，共 11 个枚举值（含 `None`）；Android 17 增加后五项。Android 17 还在 `Experimental<T>` 中同时保存 legacy 与 experimental 值：`value()` 根据 `use_experimental_jank_classification` 选择当前值，`altValue()` 返回另一套结果。Trace packet 因而同时有 `jank_type` 与 `jank_type_experimental`。字段名带有历史包袱：当 experimental 算法被选为当前值时，`jank_type_experimental` 保存的是备用 legacy 结果。

### 1.3 关键参数配置

下面的结构体给出 Android 17 默认阈值；三个字段分别约束 present、deadline 和 start：

```cpp
struct JankClassificationThresholds {
    nsecs_t presentThreshold =
            std::chrono::duration_cast<std::chrono::nanoseconds>(2ms).count();
    nsecs_t deadlineThreshold = std::chrono::duration_cast<std::chrono::nanoseconds>(0ms).count();
    nsecs_t startThreshold = std::chrono::duration_cast<std::chrono::nanoseconds>(2ms).count();
};
```

`presentThreshold` 不是结构体里的唯一阈值。与 Android 16 相比，变化发生在 present 这一项：Android 16 有 `presentThresholdLegacy = 2ms` 和 `presentThresholdExtended = 4ms`，Android 17 合并为 `presentThreshold = 2ms`；`deadlineThreshold = 0ms` 与 `startThreshold = 2ms` 仍然存在。分类代码也没有随字段合并而变成单一路径，legacy 与 experimental 结果仍会并行计算。

下面两个常量控制 FrameTimeline 保存的显示帧窗口和 SurfaceFrame 容器的初始容量：

```cpp
static constexpr uint32_t kDefaultMaxDisplayFrames = 64;
static constexpr uint32_t kNumSurfaceFramesInitial = 10;
```

`kNumSurfaceFramesInitial` 只是 `vector` 的初始容量，不限制一个 DisplayFrame 最多关联多少个 SurfaceFrame。

### 1.4 Trace Cookie 机制

下面的计数器由 SurfaceFlinger 内的 `FrameTimeline` 持有：

```cpp
class TraceCookieCounter {
public:
    int64_t getCookieForTracing();
private:
    std::atomic<int64_t> mTraceCookie = 0;
};
```

SurfaceFrame 与 DisplayFrame 的开始 packet 携带完整信息和新 cookie，结束 packet 只需携带同一个 cookie。cookie 用于在 Trace Processor 中闭合一对事件并减少重复载荷。所有 packet 都由 SurfaceFlinger 生产；“SurfaceFrame”描述 App 帧，不表示 App 进程负责发 cookie，因此这里不存在跨进程计数器协调。

### 1.5 Trace 起点过滤门控

下面的构造函数片段说明过滤策略被保存在 `FrameTimeline` 实例中；参数默认值定义在 `FrameTimeline.h`：

```cpp
FrameTimeline::FrameTimeline(std::shared_ptr<TimeStats> timeStats, pid_t surfaceFlingerPid,
                             JankClassificationThresholds thresholds, bool useBootTimeClock,
                             bool filterFramesBeforeTraceStarts)
      : mUseBootTimeClock(useBootTimeClock),
        mFilterFramesBeforeTraceStarts(filterFramesBeforeTraceStarts),
```

默认参数为 `true`，调用者仍可在构造时覆盖它。写 expected/actual timeline packet 前，下面的门控会检查对应 trace session 的起点：

```cpp
if (filterFramesBeforeTraceStarts && !shouldTraceForDataSource(ctx, timestamp)) {
    // Do not trace packets started before tracing starts.
    return;
}
```

`mFilterFramesBeforeTraceStarts` 的构造默认值是 `true`。`shouldTraceForDataSource()` 比较每个 data source 实例的 start time 与帧的起始时间，因此 trace 开始前已经启动、trace 开始后才结束的帧也可能被过滤。复现动作前应留出采集预热时间，不能在动作发生后才启动 session。

### 1.6 JankTracker 异步通知链

`JankTracker` 是向 `IJankListener` 分发 jank 数据的旁路，不负责写 Perfetto packet。`onJankData()` 在没有 listener 时由 `sListenerCount == 0` 快速返回；存在 listener 时，数据进入低优先级 `BackgroundExecutor`，每个 layer 累计到 `kJankDataBatchSize = 50` 后触发 flush。异步路径减少了 SurfaceFlinger 主线程上的 Binder 工作，但队列、锁和复制仍有成本，不能写成“没有开销”。

### 1.7 FrameTimeline 的覆盖范围

FrameTimeline 对标准 HWUI App Window 的 expected/actual 时间线覆盖最完整。SurfaceView 在官方 FrameTimeline 文档中仍标为未完整支持；相机、视频、游戏或厂商组件直接提交到独立 Surface 时，也可能没有完整的 App `actual_frame_timeline_slice`。这类路径不能因为查询没有返回 App 帧就判定“应用没有提交 buffer”，还要检查目标 layer、BufferQueue/BLAST、`BufferTX`、latch、HWC 与 present fence 证据。

SurfaceFlinger 的 actual slice 表达该帧从 SF 处理到显示完成锚点的端到端区间，可能覆盖调度、合成、Display HAL 和 fence 等待。它不是 SurfaceFlinger 主线程 CPU time，也不能把整段时长归因给 SF CPU。present fence 是系统显示管线的完成锚点，不表示面板像素已经完成光学响应。

### 1.8 FrameTimeline、TimeStats/statsd 与 `IJankListener`

`SurfaceFrame::onPresent()` 在存在预测数据时，把当前活动分类 `mJankType.value()` 交给 `TimeStats::incrementJankyFrames()`，随后构造同时带 legacy/experimental 结果的 `JankData`，交给 `JankTracker`。三条输出路径要分开理解：

- Perfetto FrameTimeline 保存按帧 packet，是否写入由 trace session 和 trace-start filter 控制；
- TimeStats 按刷新率、渲染率、UID、layer、GameMode 等维度聚合，statsd 通过 atom `10062`（global）和 `10063`（layer）拉取；
- `IJankListener` 接收按 layer 批量分发的 `JankData`，不参与 Perfetto packet 写入。

TimeStats 只聚合活动分类，不保存 FrameTimeline packet 中的备用分类。`kValidJankyReason` 仅把 `DisplayHAL`、SF CPU/GPU deadline miss、`AppDeadlineMissed`、`PredictionError` 和 `SurfaceFlingerScheduling` 计入 janky-frame 总数；`BufferStuffing` 另设计数。Android 17 新增的显示状态或非动画 context 位不会自动成为 statsd 的 janky-frame 原因。

TimeStats 未启用时，`incrementJankyFrames()` 立即返回。`onPullAtom()` 在完成一次 global 或 layer atom 拉取后才调用 `enable()`，所以某个 build 的首次完整拉取预期为空或数据很少。Perfetto session、statsd 拉取窗口与 listener 生命周期没有天然的一致关系，三者数值不能直接互相验算。

### 1.9 配套数据源：`android.surfaceflinger.frame`（FrameTracer，graphics frame event）

`android.surfaceflinger.frame` 由 `FrameTracer` 承载，记录 buffer 在 dequeue、queue、acquire、latch 和 present 一带的事件。它适合回答“buffer 流水线在哪一段停留较久”；`frametimeline` 适合回答“App/SF 帧是否符合预测时间线，以及当前分类器给出了什么 jank 标记”。

SurfaceFlinger 在同一个 boot finished 回调中依次初始化两个数据源。下面的调用顺序来自 `SurfaceFlinger.cpp`：

```cpp
mFrameTracer->initialize();
mFrameTimeline->onBootFinished();
```

`FrameTracer::initialize()` 使用 `std::call_once`，初始化 system backend 后注册 `android.surfaceflinger.frame`：

```cpp
void FrameTracer::initialize() {
    std::call_once(mInitializationFlag, [this]() {
        perfetto::TracingInitArgs args;
        args.backends = perfetto::kSystemBackend;
        perfetto::Tracing::Initialize(args);
        registerDataSource();
    });
}
```

这保证一个 SurfaceFlinger 进程内只执行一次注册；它没有承诺数据源在 SurfaceFlinger 完成启动前可用。

`graphics_frame_event.proto` 定义了 13 个非零 `BufferEventType`。proto 中存在枚举值，不等于 AOSP 当前路径一定发射该值：

| Android 17 AOSP `Layer.cpp` 可见的发射 | 时间语义 |
|---|---|
| `DEQUEUE`、`QUEUE` | App 侧 dequeue 时间与向 SF post/queue 的时间 |
| `ACQUIRE_FENCE`、`LATCH` | acquire fence signal 与 SF latch 时间 |
| `FALLBACK_COMPOSITION` | layer 被排入 client composition 的时间戳 |
| `PRESENT_FENCE` | present fence signal；无有效 fence 时使用 HWC present timestamp 推导值 |

`HWC_COMPOSITION_QUEUED`、`RELEASE_FENCE` 等枚举仍在协议中，但上表没有把它们当作 Android 17 AOSP 的稳定发射点。分析 vendor trace 时可以观察额外事件；结论必须以当前 trace 和对应源码为准。

fence 尚未 signal 时，`traceFence()` 把记录放入 `pendingFences[bufferID]`。同一 buffer 后续再触发 FrameTracer 时，`tracePendingFencesLocked()` 才重新读取 fence。`kFenceSignallingDeadline = 60s` 只在消费 pending 项时丢弃过旧信号，不是独立运行的 60 秒定时清理器。

`traceSpanLocked()` 在 `startTime > 0 && startTime < endTime` 时生成区间，否则在 end time 写 instant。Trace Processor 的 graphics parser 再把事件重建成四类 phase：

- `APP_*`：Dequeue → Queue；
- `GPU_*`：Queue → AcquireFenceSignaled；
- `SF_*`：Latch → PresentFenceSignaled；
- `Display_*`：本次 Present → 同 layer 下一次 Present。

下面的 SQL 查询 Android 17 Trace Processor 重建出的 graphics phase；它使用 `slice`、`track` 和 parser 写入的参数，不把 data source 名误作 SQL 表名：

```sql
SELECT
  slice.ts,
  IIF(slice.dur = -1, trace_end() - slice.ts, slice.dur) / 1e6 AS dur_ms,
  track.name AS phase_track,
  slice.name AS frame_number,
  extract_arg(slice.arg_set_id, 'layer_name') AS layer_name
FROM slice
JOIN track ON track.id = slice.track_id
WHERE track.type = 'graphics_frame_event'
  AND (
    track.name GLOB 'APP_*' OR
    track.name GLOB 'GPU_*' OR
    track.name GLOB 'SF_*' OR
    track.name GLOB 'Display_*'
  )
ORDER BY slice.ts;
```

`GPU_*` 表示 Queue 到 acquire fence signal 的等待，不等同于 SurfaceFlinger RenderEngine 的 GPU 合成时间。识别 client composition 还要结合 FrameTimeline 的 `gpu_composition` 字段、GPU fence/render stage 轨道和 SurfaceFlinger slice。

### 1.10 Client composition 与 `FALLBACK_COMPOSITION`

`OutputLayer::requiresClientComposition()` 给出 layer 是否需要 client composition 的判定：

```cpp
bool OutputLayer::requiresClientComposition() const {
    const auto& state = getState();
    return !state.hwc || state.hwc->hwcCompositionType == Composition::CLIENT;
}
```

`state.hwc` 为空或 HWC 返回 `Composition::CLIENT` 时，layer 进入 client composition。`OutputLayerCompositionState` 对 `clientCompositionTimestamp` 的注释是“layer 被排入 client composition 的时间”。`Layer::onCompositionPresented()` 把这个时间写为 `FALLBACK_COMPOSITION`，所以它是路径标记和排队时间点，不能充当 GPU 完成 fence。原先用 `LATCH → FALLBACK_COMPOSITION` 计算 GPU 渲染耗时的做法没有源码依据。

两个图形数据源也没有稳定的一对一主键。FrameTimeline 使用 surface/display frame token（vsync id）表达 App 帧与 DisplayFrame 的 N:1 关系；FrameTracer 使用 `buffer_id`、`frame_number` 和 layer name 表达 BufferQueue 流程。跨数据源调查要以时间窗、进程、layer 和 flow 交叉核对，不能把 `frame_number` 与 FrameTimeline token 直接相等连接。

## 2. `linux.perf` 数据源

### 2.1 守护进程入口与生命周期

下面的 init service 定义来自 `external/perfetto/traced_perf.rc`：

```rc
service traced_perf /system/bin/traced_perf
    class late_start
    disabled
    socket traced_perf stream 0666 root root
    user nobody
    group nobody readproc readtracefs
    capabilities KILL DAC_READ_SEARCH
    task_profiles ProcessCapacityHigh
    shared_kallsyms
```

`disabled` 表示它不会随 class 自动启动。socket 用于接收目标进程 `/proc/<pid>/{maps,mem}` 的文件描述符；`readproc` 支持读取进程身份与 cmdline，`readtracefs` 支持解析 perf tracepoint，`KILL` 用于发送 Bionic profiler signal，`DAC_READ_SEARCH` 用于 unwinding 和设备端符号化。`ProcessCapacityHigh` 的具体 cgroup/调度映射由产品 task profile 定义，不应简写成固定“大核策略”。

Android 17 的属性规则如下；普通 trace session 由 Perfetto tracing service 的 builtin producer 管理 `traced.lazy.traced_perf`：

```rc
on property:persist.traced_perf.enable=1
    start traced_perf
on property:persist.traced_perf.enable="" && property:sys.init.perf_lsm_hooks=""
    stop traced_perf
on property:persist.traced_perf.enable="" && property:sys.init.perf_lsm_hooks=1 && property:traced.lazy.traced_perf=1
    start traced_perf
on property:persist.traced_perf.enable="" && property:sys.init.perf_lsm_hooks=1 && property:traced.lazy.traced_perf=""
    stop traced_perf
```

tracing service 预先注册一个 lazy `linux.perf` descriptor。收到含 `linux.perf` 的配置时，`BuiltinProducer::SetupDataSource()` 把 `traced.lazy.traced_perf` 设为 `1`；相关 session 数量降为零后，再延迟清空该属性。`traced_perf` 连接服务后会注册实际 producer descriptor。正常抓取无需手工改 `sys.init.perf_lsm_hooks` 或 `traced.lazy.traced_perf`，这两个属性属于平台控制路径。

`persist.traced_perf.enable=1` 是强制运行的诊断开关，适合有权限的 userdebug/eng 环境排查 daemon 启动问题。它不绕过 kernel、LSM、SELinux 或目标进程 profileable 限制。

### 2.2 Main 函数与 Socket 继承

下面的入口展示 init socket、descriptor getter 与 `PerfProducer` 的连接关系：

```cpp
static constexpr char kTracedPerfSocketEnvVar[] = "ANDROID_SOCKET_traced_perf";

int GetRawInheritedListeningSocket() {
  const char* sock_fd = getenv(kTracedPerfSocketEnvVar);
  if (sock_fd == nullptr)
    PERFETTO_FATAL("Did not inherit socket from init.");
  ...
}

int TracedPerfMain(int argc, char** argv) {
  // Option parsing and daemonize handling are omitted.
  base::MaybeLockFreeTaskRunner task_runner;
  AndroidRemoteDescriptorGetter proc_fd_getter{GetRawInheritedListeningSocket(),
                                               &task_runner};
  profiling::PerfProducer producer(&proc_fd_getter, &task_runner);
  producer.ConnectWithRetries(GetProducerSocket());
  task_runner.Run();
  return 0;
}
```

`ANDROID_SOCKET_traced_perf` 由 init 传入。缺少该 fd 时 daemon 直接报 fatal，说明这个 Android 入口依赖 init service 环境，不能把二进制当作普通 shell 程序直接启动。

### 2.3 Producer 与数据源标识

下面两个常量区分 producer 名称与 TraceConfig 使用的数据源名称：

```cpp
constexpr char kProducerName[] = "perfetto.traced_perf";
constexpr char kDataSourceName[] = "linux.perf";
```

`perfetto.traced_perf` 出现在 service state 的 producer 列表；配置文件必须写 `name: "linux.perf"`。

### 2.4 进程过滤机制

下面的片段展示 `PerfProducer` 如何匹配目标进程 cmdline：

```cpp
bool PerfProducer::ShouldRejectDueToFilter(
    pid_t pid, const TargetFilter& filter, bool skip_cmdline,
    base::FlatSet<std::string>* additional_cmdlines,
    std::function<bool(std::string*)> read_proc_pid_cmdline) {
  ...
  auto has_matching_pattern = [](const std::vector<std::string>& patterns,
                                 const char* cmd, const char* name) {
    for (const std::string& pattern : patterns) {
      if (glob_aware::MatchGlobPattern(pattern.c_str(), cmd, name)) return true;
    }
    return false;
  };
  ...
}
```

Android 17 中 `ShouldRejectDueToFilter` 使用 `glob_aware::MatchGlobPattern`。公开 proto 对 Android 13+ 的保证是“一个 pattern 最多使用一个 `*`”；以 `/` 开头的 pattern 匹配 argv0，其余 pattern 匹配 argv0 的二进制名部分。PID 与 cmdline 的 allow/deny 条件会一起参与筛选，不能把其中一项理解成覆盖其他条件。

过滤顺序会改变结果。`exclude_cmdline` 和 `exclude_pid` 先执行，命中任一项就拒绝；排除规则因而优先于所有允许规则。随后，`target_cmdline` 或 `target_pid` 命中任一项就接受，两组允许条件是 OR，不要求同时满足。允许列表都为空时，保留未被显式排除的进程；配置了允许列表却没有命中时，拒绝该进程。

TraceConfig 字段与 `TargetFilter` 内部集合名要区分。对外配置使用：

- `callstack_sampling.scope.target_cmdline`：白名单 cmdline（Android 13+ 支持单个通配符）
- `callstack_sampling.scope.exclude_cmdline`：黑名单 cmdline
- `callstack_sampling.scope.target_pid` / `exclude_pid`：直接 PID 过滤

### 2.5 实时进程发现延迟

下面的常量只作用于 Android 的远程进程 descriptor 查询：

```cpp
// Android 平台上的 signal-based descriptor lookup needs a short delay: when
// a process image is replaced by execve, the new libc needs time to reinstall
// the proper signal handlers. ...
constexpr uint32_t kProcDescriptorsAndroidDelayMs = 50;
```

`InitiateDescriptorLookup()` 延迟 50ms 再请求目标进程的 maps/mem descriptors，目的是避开 fork 后 execve 到新 libc 恢复 signal handler 之间的窗口。该等待是基于 wall time 的启发式策略。极短进程可能在 descriptor 请求前退出，已排队样本随后会因 descriptor 获取失败或超时而丢弃；它不是通用的“进程发现延迟”。

### 2.6 PerfEventConfig 字段映射

下面列出 Android 17 标签中仍在使用的核心字段：

```protobuf
message PerfEventConfig {
  optional PerfEvents.Timebase timebase = 15;
  optional CallstackSampling callstack_sampling = 16;
  repeated FollowerEvent followers = 19;
  optional uint32 ring_buffer_pages = 3;
  optional uint32 ring_buffer_read_period_ms = 8;
  optional uint64 max_enqueued_footprint_kb = 17;
  optional uint32 max_daemon_memory_kb = 13;
  repeated uint32 target_cpu = 20;
}
```

`timebase` 决定采样事件和频率；`callstack_sampling` 未设置时只记录计数，不采集调用栈。`ring_buffer_pages` 按每 CPU、4KiB page 计数且必须是 2 的幂。`max_enqueued_footprint_kb` 超限时丢弃 unwinder 队列中的新样本，`max_daemon_memory_kb` 检查 `traced_perf` 合计的 `RssAnon + Swap` 并停止数据源。`target_cpu` 从 Perfetto v50 开始可用；Android 17 平台快照包含该字段，但留空才表示所有 CPU。

### 2.7 Android 17 内核与权限边界

`linux.perf` 最终调用内核 `perf_event_open()`。内核锚点 `android17-6.18-2026-06_r6` 的 `kernel/events/core.c` 在创建 event 前调用 `security_perf_event_open(PERF_SECURITY_OPEN)`；采集 kernel frames 时还会经过 `perf_allow_kernel()`，受 `perf_event_paranoid`、capability 与 LSM hook 约束。

AOSP 用户态源码能证明 `linux.perf` producer 和配置路径存在，不能证明每台 Android 17 量产设备都允许同样的采样。`PerfProducer::OnProcDescriptors()` 在接收目标进程的 maps/mem fd 后调用 `CanProfile()`，这道检查直接决定设备端用户栈能否展开：

- 非 `user` build 直接通过这道用户态检查；
- `user` build 上，普通 shell session 要求目标包的 `profileable_from_shell` 或 `debuggable` 为真；
- trusted-system session 接受 `profileable` 或 `debuggable`；平台 UID 也只有 trusted-system session 才通过；
- `target_installed_by` 非空时，安装来源还必须落在允许列表中；SDK sandbox 会映射回所属 App UID，isolated UID 使用更保守的检查。

上述规则只描述 Perfetto 用户态 guardrail。设备仍有下列限制：

- kernel frames 还依赖产品内核、符号访问与安全策略，user build 可能只返回用户栈或拒绝 session；
- vendor kernel 可以改变 PMU、tracepoint 和 LSM 策略，GKI common tag 不是具体设备内核配置的替代品；
- 一次成功 session 仍可能出现 ring-buffer overrun、unwinder overload、descriptor timeout 或符号缺失。

## 3. 数据源对比与协作关系

| 维度 | `linux.perf` | `android.surfaceflinger.frametimeline` | `android.surfaceflinger.frame` |
|---|---|---|---|
| producer | `traced_perf` | SurfaceFlinger `FrameTimeline` | SurfaceFlinger `FrameTracer` |
| 注册/启动 | tracing service 先注册 lazy descriptor，session 按需启动 daemon | SF boot finished 后注册 | SF boot finished 后注册 |
| 数据语义 | perf counter、CPU/tracepoint 样本、可选调用栈 | expected/actual timeline、active/alternate jank 分类、severity | BufferQueue 周期事件和重建 phase |
| 主要 join 维度 | `utid/upid`、sample timestamp、callsite | surface/display frame token、`upid`、layer、timestamp | buffer/layer 轨道、frame number、timestamp |
| 外部限制 | kernel、LSM、SELinux、session 发起方、profileable、符号 | SF 启动时序、trace-start filter、渲染路径覆盖、厂商实现 | 发射点覆盖、pending fence、厂商扩展 |
| Android 17 源码状态 | 用户态路径已确认；设备可用性需实测 | 注册与 packet 路径已确认 | 注册与 AOSP Layer 发射点已确认 |

## 4. 版本演进与兼容性

| Android 版本 | 关键差异 | 源码证据 |
|-------------|---------|----------|
| **Android 11 (API 30)** | `linux.perf` / `traced_perf` 已存在；FrameTimeline 尚未引入 | android-11.0.0_r1 external/perfetto |
| **Android 12/12L (API 31/32)** | FrameTimeline 对外可用；`linux.perf` 继续存在 | Perfetto FrameTimeline 文档要求 Android 12+ |
| **Android 13-15 (API 33-35)** | `target_cmdline` 在 Android 13+ 获得单通配符语义；FrameTimeline 持续演进 | `PerfEventConfig.Scope` 注释与各版本标签 |
| **Android 16 (API 36)** | present 分类保留 2ms legacy 与 4ms extended 两档；`JankType` 到 `Dropped` 共 11 个枚举值 | `android-16.0.0_r3` FrameTimeline/JankInfo |
| **Android 17 (API 37)** | present 阈值合并为 2ms，legacy/experimental 算法仍并存；新增 5 个 jank/context 位；`traced_perf.rc` 延续 lazy 生命周期 | `android-17.0.0_r1` FrameTimeline/JankInfo/traced_perf |

`android-17.0.0_r1` 中的 `external/perfetto` 是固定的平台源码快照，不能简化成某个上游版本号；平台 tag、设备端 producer 与主机 Trace Processor 是三条独立版本轴。开发机使用更新的 Trace Processor 打开 trace 时，stdlib 与公开视图可能增加字段；查询前仍要用 `PRAGMA table_info(...)` 或官方 schema 确认列名。主机工具版本变化不会改变设备端数据源是否发出了 packet。

## 5. 性能影响分析

### 5.1 `linux.perf` 性能开销

- **采样频率**：`timebase.frequency` 越高，perf event 采样和 unwinder 队列压力越大，不能用固定百分比描述所有设备。
- **目标范围**：未设置 scope 会保留所有进程的样本，系统级 DWARF unwinding 很容易过载；应按 cmdline/PID 缩小范围。
- **调用栈模式**：DWARF unwinding、frame-pointer unwinding、仅计数的成本不同；kernel frames 还会增加符号处理。
- **ring buffer**：`ring_buffer_pages` 按 CPU 分配，CPU 数量和 page 数共同决定内核缓冲内存。
- **内存与丢样边界**：`max_enqueued_footprint_kb` 会在 unwinder 队列占用超过阈值时丢样；`max_daemon_memory_kb` 会在 `traced_perf` 内存超过阈值时停止数据源。
- **连接恢复**：producer 连接重试从 100ms backoff 开始，最大到 30s；它是断连恢复参数，不是每次采样固定增加的延迟。

### 5.2 两个 SurfaceFlinger 数据源的开销

- **空闲开销**：trace session 不开时没有 Perfetto packet 写入；FrameTimeline 自身的帧状态维护仍属于 SurfaceFlinger 正常路径。
- **FrameTimeline packet**：有效 prediction 和 actual timeline 都用 start/end packet 表示；SurfaceFrame、DisplayFrame、skipped frame 数量会共同放大数据量。
- **FrameTracer packet**：事件量随活跃 layer、buffer 周转和 fence 数量增长；未 signal fence 还会占用 pending 容器。
- **Jank listener**：它与 Perfetto data source 是两条路径。没有 listener 时快速返回，存在 listener 时仍会产生异步排队与批量 Binder 回调成本。

开销结论必须来自目标设备的 A/B trace：固定复现场景，比较关闭/开启数据源时的 CPU time、丢帧、Perfetto buffer loss、`traced_perf` RSS/Swap 和 skipped-sample stats。源码只能说明成本随哪些变量增长。

## 6. 实际应用建议

### 6.1 Trace 数据查询

下面的查询同时显示当前 jank 结果和 packet 中的备用分类结果：

```sql
SELECT
  process.name AS process_name,
  frame.ts,
  IIF(frame.dur = -1, trace_end() - frame.ts, frame.dur) / 1e6 AS dur_ms,
  frame.surface_frame_token,
  frame.display_frame_token,
  frame.layer_name,
  frame.jank_type AS active_jank_type,
  extract_arg(
    frame.arg_set_id,
    'Jank type (experimental)'
  ) AS alternate_jank_type,
  frame.present_type,
  frame.on_time_finish
FROM actual_frame_timeline_slice AS frame
LEFT JOIN process ON process.upid = frame.upid
WHERE frame.jank_type != 'None'
   OR COALESCE(
        extract_arg(frame.arg_set_id, 'Jank type (experimental)'),
        'None'
      ) NOT IN ('None', 'Unspecified')
ORDER BY frame.ts;
```

`active_jank_type` 对应 SurfaceFlinger 由 flag 选中的 `value()`；parser 中名为 `Jank type (experimental)` 的 arg 来自 `altValue()`，所以查询把它命名为 `alternate_jank_type`。`jank_type` 可以包含逗号分隔的多个 bit，报告不能把它当成互斥枚举。

### 6.2 避免数据丢失

抓取前先查看 service state。下面的命令适合人工诊断；`--query` 输出明确标注为非稳定机器接口，自动化应解析 `--query-raw` 的 `TracingServiceState`：

```bash
adb shell perfetto --query \
  | grep -E 'perfetto\.traced_perf|linux\.perf|android\.surfaceflinger\.(frame|frametimeline)'
```

`linux.perf` 的 lazy descriptor 可能在 daemon 尚未运行时就已列出，因此还要执行短 session，并检查 trace 中是否有样本、错误 stats 和 `perfetto.traced_perf` producer。正常采集由配置触发 lazy daemon：

```bash
adb shell perfetto --txt \
  -c /data/local/tmp/perfetto.pbtxt \
  -o /data/misc/perfetto-traces/trace.perfetto-trace
```

这条命令不会手工设置 init 的内部 lazy 属性。若 session 无样本，再核对 logcat、service state、目标 App 的 profileable 状态和产品内核策略。

### 6.3 FrameTimeline 与 FrameTracer 配置

在已验证可工作的基础 TraceConfig 中，同时加入 `android.surfaceflinger.frametimeline` 和 `android.surfaceflinger.frame`，即可采集帧预测/实际时间线与 BufferQueue phase；两个数据源都不要求额外 config message。duration 与 buffer 不能从文章复制固定值，应由目标设备上的复现窗口、活跃 layer 数、帧率和实际写入速率决定。

验收时先启动 session，再执行复现动作。采集结束后同时检查 FrameTimeline 帧数、graphics frame event 轨道、Perfetto buffer-loss stats 和复现时间窗；独立 Surface 或 SurfaceView 场景还要确认目标 layer 是否进入了这两个数据源的覆盖范围。

### 6.4 `linux.perf` 最小调用栈配置

`linux.perf` 调用栈配置至少要明确四件事：`timebase` 的事件与采样频率、`callstack_sampling.scope` 的目标进程、用户栈展开模式、ring buffer 与 daemon guardrail。采样频率、page 数和内存上限都属于设备测量结果，不能脱离复现场景给出通用常数。

需要把调用栈与调度状态关联时，再加入 `linux.ftrace` 的 `sched_switch`/`sched_waking` 和 `linux.process_stats` 的启动时进程扫描。留空 `target_cpu` 会覆盖所有在线 CPU。开启 `kernel_frames` 前，应在目标 build 上验证内核栈权限与符号可用性；扩大 CPU/进程范围、提高采样频率或改用高频 tracepoint 时，要同时检查 ring-buffer overrun、unwinder overload、descriptor failure 和数据源停止原因。

## 7. 源码锚点复核方法

下面的命令可在 AOSP 多仓库 checkout 的 `frameworks/native`、`external/perfetto` 和 `kernel/common` 中固定 tag 读取源码，避免把 repo 根目录误当作单个 Git 仓库。它们是复核源码锚点的最小集合，不能替代目标设备上的实际 trace 验收：

```bash
git -C frameworks/native show \
  android-17.0.0_r1:services/surfaceflinger/Scheduler/FrameTimeline.h \
  | rg 'kFrameTimelineDataSource|JankClassificationThresholds'

git -C external/perfetto show \
  android-17.0.0_r1:src/profiling/perf/perf_producer.cc \
  | rg 'kDataSourceName|kProcDescriptorsAndroidDelayMs'

git -C external/perfetto show \
  android-17.0.0_r1:protos/perfetto/config/profiling/perf_event_config.proto \
  | rg 'target_cpu|max_enqueued_footprint_kb|max_daemon_memory_kb'

git -C kernel/common show \
  android17-6.18-2026-06_r6:kernel/events/core.c \
  | rg 'security_perf_event_open|perf_allow_kernel'
```

这些命令只证明固定 tag 中的实现。设备验收还需要 `perfetto --query`、一次短采集、Trace Processor schema 检查和结果数据检查。

## 8. 已知边界与潜在风险

### 8.1 已知边界

1. **注册不等于有数据**：`perfetto --query` 能列出 descriptor，session 仍可能因为权限、配置、启动时序或 producer 错误而得到空结果。
2. **活动/备用分类**：`jank_type` 是 flag 选择的活动值，名为 `Jank type (experimental)` 的 arg 是备用值；报告要记录设备 build 和 flag 状态。
3. **FrameTimeline 起点过滤**：默认过滤 trace session 开始前已经启动的 frame。
4. **FrameTracer 事件覆盖**：proto 的 13 个事件值是协议上限，AOSP 与 vendor 的发射点可能不同。
5. **跨数据源关联**：FrameTimeline token 与 BufferQueue frame number 属于不同编号空间，只能借助时间窗、layer、process 和 flow 建立证据链。
6. **渲染路径覆盖**：标准 HWUI App Window 的 FrameTimeline 证据最完整；SurfaceView 和独立 Surface 需要补查 layer、BufferQueue、事务、fence 与 HWC。
7. **statsd 统计口径**：TimeStats 聚合活动分类的子集，首次拉取才启用统计；它不是 Perfetto 按帧数据的镜像。

### 8.2 潜在风险

1. **短进程用户栈缺失**：50ms descriptor 延迟给 execve 留出安全窗口，也提高了进程退出前拿不到 maps/mem fd 的概率。
2. **采样过载**：频率、CPU 数、目标进程数、DWARF 栈深与 tracepoint 事件率会一起推高 ring buffer 和 unwinder 压力。
3. **量产设备权限差异**：userdebug 上成功的 kernel frame 或平台进程采样，到了 user build 可能被 profileable、LSM、SELinux 或符号策略限制。
4. **分类不等于根因**：`AppDeadlineMissed`、`SF GPU Deadline Missed` 等 bit 是 FrameTimeline 对时序的分类。CPU、Binder、I/O、fence 和 GPU 轨道仍需交叉验证。

## 信息源与参考资料

### 一手源码

- [Android 17 `FrameTimeline.h`](https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/services/surfaceflinger/Scheduler/FrameTimeline.h)
- [Android 17 `FrameTimeline.cpp`](https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/services/surfaceflinger/Scheduler/FrameTimeline.cpp)
- [Android 17 `JankInfo.h`](https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/libs/gui/include/gui/JankInfo.h)
- [Android 17 `JankTracker.cpp`](https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/services/surfaceflinger/Jank/JankTracker.cpp)
- [Android 17 `TimeStats.cpp`](https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/services/surfaceflinger/TimeStats/TimeStats.cpp)
- [Android 17 `SurfaceFlinger.cpp`](https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/services/surfaceflinger/SurfaceFlinger.cpp)
- [Android 17 `Layer.cpp`](https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/services/surfaceflinger/Layer.cpp)
- [Android 17 `OutputLayer.cpp`](https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/services/surfaceflinger/CompositionEngine/src/OutputLayer.cpp)
- [Android 17 `OutputLayerCompositionState.h`](https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/services/surfaceflinger/CompositionEngine/include/compositionengine/impl/OutputLayerCompositionState.h)
- [Android 17 `FrameTracer.cpp`](https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/services/surfaceflinger/FrameTracer/FrameTracer.cpp)
- [Android 17 `graphics_frame_event.proto`](https://android.googlesource.com/platform/external/perfetto/+/refs/tags/android-17.0.0_r1/protos/perfetto/trace/android/graphics_frame_event.proto)
- [Android 17 `graphics_frame_event_parser.cc`](https://android.googlesource.com/platform/external/perfetto/+/refs/tags/android-17.0.0_r1/src/trace_processor/importers/proto/graphics_frame_event_parser.cc)
- [Android 17 `frame_timeline_event_parser.cc`](https://android.googlesource.com/platform/external/perfetto/+/refs/tags/android-17.0.0_r1/src/trace_processor/importers/proto/frame_timeline_event_parser.cc)
- [Android 17 `traced_perf.rc`](https://android.googlesource.com/platform/external/perfetto/+/refs/tags/android-17.0.0_r1/traced_perf.rc)
- [Android 17 `traced_perf.cc`](https://android.googlesource.com/platform/external/perfetto/+/refs/tags/android-17.0.0_r1/src/profiling/perf/traced_perf.cc)
- [Android 17 `perf_producer.cc`](https://android.googlesource.com/platform/external/perfetto/+/refs/tags/android-17.0.0_r1/src/profiling/perf/perf_producer.cc)
- [Android 17 profiler `producer_support.cc`](https://android.googlesource.com/platform/external/perfetto/+/refs/tags/android-17.0.0_r1/src/profiling/common/producer_support.cc)
- [Android 17 `builtin_producer.cc`](https://android.googlesource.com/platform/external/perfetto/+/refs/tags/android-17.0.0_r1/src/traced/service/builtin_producer.cc)
- [Android 17 `PerfEventConfig`](https://android.googlesource.com/platform/external/perfetto/+/refs/tags/android-17.0.0_r1/protos/perfetto/config/profiling/perf_event_config.proto)
- [`android17-6.18-2026-06_r6` `perf_event_open()`](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/kernel/events/core.c)

### 官方使用文档

- [Android FrameTimeline data source](https://perfetto.dev/docs/data-sources/frametimeline)
- [Callstack sampling with `linux.perf`](https://perfetto.dev/docs/quickstart/callstack-sampling)
- [Perfetto CLI `--query` / `--query-raw`](https://perfetto.dev/docs/reference/perfetto-cli)
- [TraceConfig proto reference](https://perfetto.dev/docs/reference/trace-config-proto)

### 相关章节

- 13.2 Trace 抓取 - 基础 trace 配置方法
- 13.9 Android Tracing 基础设施 - 数据采集原理
- 13.14 Perfetto DataGrid 与 Jank CUJ 标准库 - jank 分析实践

验收顺序是：固定 platform/kernel tag，查询 descriptor，执行短 session，检查 producer 与错误 stats，确认 SQL schema，再讨论 jank 或调用栈结论。任何一步缺失，都要在报告中降低可信度并写出补采条件。
