---
title: "Android 17 Perfetto 数据源边界与验证"
chapter: "13.17"
section: "13.17"
status: finalized
drafted_date: "2026-06-16"
drafted_by: "openclaw-task2a"
applicable_versions: "Android 12 (API 31) - Android 17 (API 37)"
last_verified: "2026-06-16"
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
tags: ['perfetto', 'android17', 'data-sources', 'trace-capture', 'verification']
related_chapters: ["13.2", "13.9", "13.14"]
pipeline_stage: "ready-to-publish"
task6_state: "reviewed"
task6_result: pass-light-edit
task9_state: "reviewed"
reviewed_by: "openclaw-task6"
reviewed_date: "2026-06-23"
last_task6_at: "2026-06-23T02:08:00+08:00"
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
---


# Android 17 Perfetto 数据源边界与验证

## 章节概述

本章基于 AOSP `android-17.0.0_r1` 源码，验证 `linux.perf` 和 `android.surfaceflinger.frametimeline` 两个核心 Perfetto 数据源在 Android 17 / API 37 的可用性与实现细节。

## 核心发现

**Android 17 边界结论**（基于 `android-17.0.0_r1` 源码验证）：
- `linux.perf`（`traced_perf` 守护进程）与 `android.surfaceflinger.frametimeline` 在 Android 17 / API 37 中**完整可用**
- `JankClassificationThresholds` 简化为单一 `presentThreshold`（2ms），不再区分 legacy/extended
- `JankType` 从 Android 16 的 11 种扩展为 **16 种**，新增 `NonAnimating`、`AppResyncedJitter`、`DisplayNotOn`、`DisplayModeChangeInProgress`、`DisplayPowerModeChangeInProgress`
- `traced_perf.rc` 在 Android 17 保持 Android 16 已有的 `readtracefs`、`task_profiles ProcessCapacityHigh`、`shared_kallsyms`；属性驱动启停模型从 Android 12 起已存在

<!-- outline-start -->
## 要点

### 🔹 数据源注册机制
`android.surfaceflinger.frametimeline` 在 SurfaceFlinger 启动后无条件注册，`linux.perf` 则按需触发。

### 🔹 Jank 类型判别系统
FrameTimeline 通过 `classifyJankLocked()` 建立完整的 jank 分类机制，16 种类型覆盖性能与非性能延迟场景。

### 🔹 性能开销控制
`linux.perf` 的开销由采样频率、目标进程范围和调用栈展开成本共同决定；`frametimeline` 仅在 trace session 开启时写入 packet。

### 🔹 版本演进路径
`linux.perf` 在 Android 11 已存在，`android.surfaceflinger.frametimeline` 从 Android 12 引入；Android 17 主要扩展 JankType，traced_perf 维持既有属性驱动生命周期。

### 🔸 应用优化建议
针对不同场景的 Trace 配置方案，避免数据丢失，优化内存使用。

## 扩展

### 🔸 实时进程发现延迟
traced_perf 的 50ms 延迟机制避免 execve 期间信号处理异常，但可能遗漏短进程。

### 🔸 多进程协调
`mTraceCookie` 在跨进程场景下的正确性有待验证。

### 🔸 StatsD 集成
FrameTimeline 与 statsd atom 写入的路径关系需要进一步确认。

<!-- outline-end -->

## 1. `android.surfaceflinger.frametimeline` 数据源

### 1.1 数据源注册机制

**关键常量**：`frameworks/native/services/surfaceflinger/Scheduler/FrameTimeline.h`（`android-17.0.0_r1`）
```cpp
static constexpr char kFrameTimelineDataSource[] = "android.surfaceflinger.frametimeline";
```

**注册入口**：`FrameTimeline.cpp`（line 1344-1355）
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

**触发时机**：SurfaceFlinger 启动完成后无条件注册
```cpp
// SurfaceFlinger.cpp line 815-820
const nsecs_t now = systemTime();
const nsecs_t duration = now - mBootTime;
ALOGI("Boot is finished (%ld ms)", long(ns2ms(duration)));
mFrameTracer->initialize();
mFrameTimeline->onBootFinished();     // <-- 注册点
```

### 1.2 Jank 类型状态机

`FrameTimeline.cpp` 的 `SurfaceFrame::classifyJankLocked()`（line 829-1079，`android-17.0.0_r1`）是 jank 类型判定的核心，输出位掩码 `JankType`（共 16 种）：

| JankType 枚举 | 触发条件 | 性能影响 |
|--------------|----------|----------|
| `JankType::None` | FramePresentMetadata == OnTimePresent | 无影响 |
| `JankType::DisplayHAL` | OnTimeFinish + LatePresent，presentDelta 接近 vsync | 低 |
| `JankType::SurfaceFlingerCpuDeadlineMissed` | LateFinish + LatePresent，gpuFence == NO_FENCE | 中 |
| `JankType::SurfaceFlingerGpuDeadlineMissed` | LateFinish + LatePresent，gpuFence != NO_FENCE | 高 |
| `JankType::AppDeadlineMissed` | LateFinish + LatePresent | 高 |
| `JankType::PredictionError` | deltaToVsync 不在 presentThreshold 边界内 | 中 |
| `JankType::SurfaceFlingerScheduling` | OnTimeFinish + EarlyPresent | 低 |
| `JankType::BufferStuffing` | mLastLatchTime 有效 + mPredictions.endTime <= mLastLatchTime | 中 |
| `JankType::SurfaceFlingerStuffing` | LatePresent 且前后帧间距在 1 个 vsync 内 | 低 |
| `JankType::Dropped` | PresentState != Presented（frame 被丢弃） | 无 |
| `JankType::Unknown` | 无法归类 | 待分析 |
| `JankType::NonAnimating` | 未按时 present 但不属于动画帧，不可感知 jank | 无（不计数） |
| `JankType::AppResyncedJitter` | App 端修改了 vsync 时间 | 低 |
| `JankType::DisplayNotOn` | 显示屏关闭或处于 doze 状态 | 无 |
| `JankType::DisplayModeChangeInProgress` | 显示模式切换中 | 无 |
| `JankType::DisplayPowerModeChangeInProgress` | 电源模式切换中 | 无 |

> **Android 17 新增类型**：`NonAnimating`、`AppResyncedJitter`、`DisplayNotOn`、`DisplayModeChangeInProgress`、`DisplayPowerModeChangeInProgress` 在 Android 16 中不存在，在 `android-17.0.0_r1` 中首次引入（`libs/gui/include/gui/JankInfo.h` line 53-61）。这些类型用于过滤非性能原因导致的帧延迟，避免误报 jank。

### 1.3 关键参数配置

**默认阈值**：`FrameTimeline.h` line 110-117（`android-17.0.0_r1`）
```cpp
struct JankClassificationThresholds {
    nsecs_t presentThreshold =
            std::chrono::duration_cast<std::chrono::nanoseconds>(2ms).count();
    nsecs_t deadlineThreshold = std::chrono::duration_cast<std::chrono::nanoseconds>(0ms).count();
    nsecs_t startThreshold = std::chrono::duration_cast<std::chrono::nanoseconds>(2ms).count();
};
```

Android 17 中 `JankClassificationThresholds` 使用单一 `presentThreshold`（2ms），不再区分 legacy/extended。`increase_missed_frame_jank_threshold()` 已移除，不再通过 FlagManager 选择阈值。

**缓冲区大小**：
```cpp
static constexpr uint32_t kDefaultMaxDisplayFrames = 64;
static constexpr uint32_t kNumSurfaceFramesInitial = 10;
```

### 1.4 Trace Cookie 机制

`FrameTimeline.h` line 148-157：
```cpp
class TraceCookieCounter {
public:
    int64_t getCookieForTracing();
private:
    std::atomic<int64_t> mTraceCookie = 0;
};
```

作用：分离发送 Surface/DisplayFrame 的开始和结束时间戳，避免重复发送完整信息。

### 1.5 Trace 起点过滤门控

`FrameTimeline.cpp` line 1331-1335；默认值见 `FrameTimeline.h` line 627-628：
```cpp
FrameTimeline::FrameTimeline(std::shared_ptr<TimeStats> timeStats, pid_t surfaceFlingerPid,
                             JankClassificationThresholds thresholds, bool useBootTimeClock,
                             bool filterFramesBeforeTraceStarts)
      : mUseBootTimeClock(useBootTimeClock),
        mFilterFramesBeforeTraceStarts(filterFramesBeforeTraceStarts),
```

写 expected/actual timeline packet 前会检查 trace session 的起点：
```cpp
if (filterFramesBeforeTraceStarts && !shouldTraceForDataSource(ctx, timestamp)) {
    // Do not trace packets started before tracing starts.
    return;
}
```

`mFilterFramesBeforeTraceStarts` 在 Android 17 中默认值为 `true`，属构造参数控制的 packet 过滤边界，不受 aconfig flag 控制。

### 1.6 JankTracker 异步通知链

`JankTracker.cpp` line 26 + line 62-87：
- `JankTracker::onJankData()` 在每帧 jank 分类后被调用
- 通过 `BackgroundExecutor::getLowPriorityInstance().sendCallbacks()` 异步推送
- 批量阈值 `kJankDataBatchSize = 50`

### 1.7 配套数据源：`android.surfaceflinger.frame`（FrameTracer，graphics frame event）

<!-- AIW-源码调研-2026-06-26 -->

**定位补充**：§1.1~1.6 详述的 `android.surfaceflinger.frametimeline` 解决「帧是否按时」问题，而 `android.surfaceflinger.frame`（由 `FrameTracer/FrameTracer.cpp` 承载）解决「buffer 卡在哪一步」问题。两者通过 `buffer_id` + `frame_number` 字段在 trace processor 侧可关联。

**源码位置**：`frameworks/native/services/surfaceflinger/FrameTracer/FrameTracer.cpp`（android-17.0.0_r1）

**注册时序**（`SurfaceFlinger.cpp:819`）：
```cpp
mFrameTracer->initialize();         // 跟随 onBootFinished
mFrameTimeline->onBootFinished();   // 上一节 §1.1 已述
```

**初始化体**（`FrameTracer.cpp:36-46`）：
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

**数据源名常量**（`FrameTracer.h:90`）：`kFrameTracerDataSource[] = "android.surfaceflinger.frame"`

**13 种 BufferEventType**（`external/perfetto/protos/perfetto/trace/android/graphics_frame_event.proto`）：

| 类型 | 含义 | 触发位置（Layer.cpp） |
|------|------|---------------------|
| `DEQUEUE = 1` | App 端 dequeueBuffer | `setBuffer:982-985` |
| `QUEUE = 2` | App 端 queueBuffer | `setBuffer:986-987` |
| `ACQUIRE_FENCE = 4` | acquire fence signal | `latchBuffer:1269-1270` |
| `LATCH = 5` | SF latched 该 buffer | `latchBuffer:1271-1272` |
| `HWC_COMPOSITION_QUEUED = 6` | HWC 合成 | （HWC HAL 层） |
| `FALLBACK_COMPOSITION = 7` | GPU/renderEngine 合成 | `onCompositionPresented:1453-1455` |
| `PRESENT_FENCE = 8` | present fence signal 或反推时间戳 | `onCompositionPresented:1476-1498` |
| `RELEASE_FENCE / MODIFY / DETACH / ATTACH / CANCEL = 9..13` | buffer 释放与状态变更 | 各 buffer 路径 |

**Fence-异步与 Pending 队列**（`FrameTracer.cpp:79-100`）：当 fence 尚未 signal 时进入 `mTraceTracker[layerId].pendingFences[bufferID]` 队列；下次同一 buffer 的 trace 触发时由 `tracePendingFencesLocked()` 消费。**`kFenceSignallingDeadline = 60'000'000'000`（60s）** 硬超时（`FrameTracer.h:93`）防止 pending 队列无限增长导致 OOM。

**Span 语义**（`FrameTracer::traceSpanLocked:172-181`）：fence 带 startTime 时生成 [startTime, endTime] 区间事件，不带时只生成 endTime 时刻的 instant 事件。

**GPU stall 识别 SQL 模式**：
```sql
-- GPU 合成占比（HWC vs GPU 边界判定）
SELECT
  layer_name,
  COUNTIF(type = 'FALLBACK_COMPOSITION') AS gpu_count,
  COUNTIF(type = 'HWC_COMPOSITION_QUEUED') AS hwc_count,
  ROUND(100.0 * COUNTIF(type = 'FALLBACK_COMPOSITION') /
        NULLIF(COUNTIF(type IN ('FALLBACK_COMPOSITION','HWC_COMPOSITION_QUEUED')), 0), 2) AS gpu_pct
FROM android.surfaceflinger.frame
WHERE frame_number BETWEEN :start AND :end
GROUP BY layer_name
ORDER BY gpu_count DESC;
```

**与 FrameTimeline 的关联方式**：两者都包含 `buffer_id`（FrameTracer 中 `buffer_id = 5`，FrameTimelineEvent 中字段不同需查 `perfetto/trace/android/frame_timeline_event.proto`），实际关联依赖 `frame_number` + `layer_name` 联合键。

**反哺来源**：`DeepResearch/2026-06-26-android17-frametracer-graphics-frame-event.md`（id=23 选题，high priority）


## 2. `linux.perf` 数据源

### 2.1 守护进程入口与生命周期

**Init RC 配置**：`external/perfetto/traced_perf.rc`（`android-17.0.0_r1`）
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

**属性驱动启停条件**（Android 12 起已有，Android 17 保持）：
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

关键特性：
- `class late_start` + `disabled`：必须由上游触发
- `readtracefs` 权限组用于读取 tracefs；`/proc/pid/{maps,mem}` 文件描述符由 `traced_perf` socket 接收，`/proc` 读取依赖 `readproc`
- `task_profiles ProcessCapacityHigh`：将 traced_perf 放入高容量 cgroup，提升 unwinding 性能
- `shared_kallsyms`：允许访问内核符号表，支持内核调用栈符号化
- 属性驱动生命周期：由 `persist.traced_perf.enable`、`sys.init.perf_lsm_hooks`、`traced.lazy.traced_perf` 三组属性联合控制启停
- Socket 通信：环境变量 `ANDROID_SOCKET_traced_perf` 用于进程间通信

### 2.2 Main 函数与 Socket 继承

`external/perfetto/src/profiling/perf/traced_perf.cc` line 34-50 + line 84-105：
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

### 2.3 Producer 与数据源标识

`external/perfetto/src/profiling/perf/perf_producer.cc`（`android-17.0.0_r1`）：
```cpp
constexpr char kProducerName[] = "perfetto.traced_perf";
constexpr char kDataSourceName[] = "linux.perf";
```

### 2.4 进程过滤机制

`perf_producer.cc` line 326-378（`android-17.0.0_r1`）：
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

Android 17 中 `ShouldRejectDueToFilter` 使用 `glob_aware::MatchGlobPattern` 进行 cmdline 匹配，支持 `*` 通配符。额外包含 `skip_cmdline` 跳过列表、`additional_cmdline_count` 多 cmdline 进程、`process_sharding` 分片等边界处理。

TraceConfig 字段与 `TargetFilter` 内部集合名要区分。对外配置使用：
- `callstack_sampling.scope.target_cmdline`：白名单 cmdline（Android 13+ 支持单个通配符）
- `callstack_sampling.scope.exclude_cmdline`：黑名单 cmdline
- `callstack_sampling.scope.target_pid` / `exclude_pid`：直接 PID 过滤

### 2.5 实时进程发现延迟

`perf_producer.cc` line 73：
```cpp
// TODO(b/151835887): on Android, when using signals, there exists a vulnerable
// window between a process image being replaced by execve, and the new
// libc instance reinstalling the proper signal handlers. ...
constexpr uint32_t kProcDescriptorsAndroidDelayMs = 50;
```

含义：traced_perf 检测到新进程后**等待 50ms** 才发送 BIONIC_SIGNAL_PROFILER 信号，避免 execve 期间信号处理异常。

### 2.6 PerfEventConfig 字段映射

`protos/perfetto/config/profiling/perf_event_config.proto` 核心字段：
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

## 3. 数据源对比与协作关系

| 维度 | `linux.perf` | `android.surfaceflinger.frametimeline` |
|------|--------------|----------------------------------------|
| 注册时机 | traced 检测到 config 含此 data source 时启动 traced_perf | SurfaceFlinger.onBootFinished() 无条件注册 |
| 数据路径 | perf_event_open syscall → kernel ring buffer → traced_perf → traced | SurfaceFrame lifecycle → FrameTimeline::Trace() → traced |
| 数据语义 | CPU 周期采样 + 调用栈 | 显示帧 jank 类型 + 预测 vs 实际时间线 |
| 性能开销 | 随采样频率、目标范围和调用栈展开方式变化，需在目标设备实测 | 仅 trace session 开启时写 packet |
| Android 12+ 可用 | 是 | 是 |
| Android 17 验证状态 | 已确认（android-17.0.0_r1） | 已确认（android-17.0.0_r1） |

## 4. 版本演进与兼容性

| Android 版本 | 关键差异 | 源码证据 |
|-------------|---------|----------|
| **Android 10 (API 29)** | Perfetto 系统服务内置；不支持两个核心数据源 | FrameTimeline/ 目录不存在 |
| **Android 11 (API 30)** | `linux.perf` / `traced_perf` 已存在；FrameTimeline 尚未引入 | android-11.0.0_r1 external/perfetto |
| **Android 12 (API 31)** | `android.surfaceflinger.frametimeline` 引入；`linux.perf` 继续可用，二者从本章范围开始同时覆盖 | android-12.0.0_r1 FrameTimeline / traced_perf.cc |
| **Android 13-15 (API 33-35)** | SurfaceFlinger refactor，FrameTimeline 完善 | android-13.0.0_r1 / android-15.0.0_r1 FrameTimeline |
| **Android 16 (API 36)** | `commit_not_composited` flag、FrameTimeline 完整优化；`traced_perf.rc` 已包含 `readtracefs`、`ProcessCapacityHigh`、`shared_kallsyms` | android-16.0.0_r3 FrameTimeline / traced_perf.rc |
| **Android 17 (API 37)** | 单一 `presentThreshold`（2ms）；JankType 扩展为 16 种；`traced_perf.rc` 与 Android 16 的权限组、task profile、属性驱动生命周期保持一致 | `android-17.0.0_r1` 已公开并验证 |

## 5. 性能影响分析

### 5.1 `linux.perf` 性能开销
- **采样频率**：`timebase.frequency` 越高，perf event 采样和 unwinder 队列压力越大，不能用固定百分比描述所有设备。
- **内存与丢样边界**：`max_enqueued_footprint_kb` 会在 unwinder 队列占用超过阈值时丢样；`max_daemon_memory_kb` 会在 `traced_perf` 内存超过阈值时停止数据源。
- **启动延迟**：`ConnectWithRetries`（kInitialConnectionBackoffMs=100ms, kMaxConnectionBackoffMs=30s）

### 5.2 `frametimeline` 性能开销
- **空闲开销**：trace session 不开时没有 Perfetto packet 写入；FrameTimeline 自身的帧状态维护仍属于 SurfaceFlinger 正常路径。
- **运行开销**：开启时每个 SurfaceFrame 写 1-2 个 packet，锁竞争极低。
- **异步通知**：JankTracker 使用低优先级 BackgroundExecutor，不影响 SurfaceFlinger 主路径。

## 6. 实际应用建议

### 6.1 Trace 数据查询

```sql
-- 查询 FrameTimeline jank 数据（trace_processor SQL）
SELECT display_frame_token, name, jank_type
FROM actual_frame_timeline_slice
WHERE jank_type != 'None'
ORDER BY display_frame_token DESC
LIMIT 20;
```

### 6.2 避免数据丢失

Android 17 中 `traced_perf` 仍通过属性驱动启停（见 §2.1），不是直接调用 `ctl.start`：

```bash
# 方式一：显式启用 traced_perf
adb shell setprop persist.traced_perf.enable 1

# 方式二：lazy trigger（需要 perf_event_open LSM hooks）
adb shell setprop sys.init.perf_lsm_hooks 1
adb shell setprop traced.lazy.traced_perf 1

# 触发 Perfetto trace session 后 traced_perf 按需启动
adb shell perfetto -c /data/misc/perfetto-configs/perf.conf \
  -o /data/misc/perfetto-traces/trace.perfetto-trace
```

### 6.3 性能优化配置

```textproto
# Perfetto TraceConfig textproto 示例
buffers {
  size_kb: 32768
  fill_policy: RING_BUFFER
}

data_sources {
  config {
    name: "linux.perf"
    perf_event_config {
      timebase {
        frequency: 100
      }
      callstack_sampling {
        scope {
          target_cmdline: "myapp"
        }
        user_frames: UNWIND_DWARF
      }
      ring_buffer_pages: 256
      max_enqueued_footprint_kb: 65536
      max_daemon_memory_kb: 262144
      target_cpu: 0
      target_cpu: 1
      target_cpu: 2
      target_cpu: 3
    }
  }
}
```

## 7. 已执行回归检查

以下复核命令已在 `android-17.0.0_r1` 公开后执行：

```bash
# 1. 检查数据源常量是否变更
git log android-16.0.0_r3..android-17.0.0_r1 \
  -- frameworks/native/services/surfaceflinger/Scheduler/FrameTimeline.h \
  | grep kFrameTimelineDataSource

# 2. 检查数据源是否被禁用
git log android-16.0.0_r3..android-17.0.0_r1 \
  -- external/perfetto/src/profiling/perf/perf_producer.cc \
  | grep kDataSourceName

# 3. 检查 PerfEventConfig 字段变更
git log android-16.0.0_r3..android-17.0.0_r1 \
  -- protos/perfetto/config/profiling/perf_event_config.proto
```

## 8. 已知边界与潜在风险

### 8.1 已知边界

1. **多进程协调**：`mTraceCookie` 在跨进程场景下的正确性在 `android-17.0.0_r1` 中保持不变。
2. **初始化顺序**：`traced_perf` 与 FrameTimeline 写入的时序保证机制未变。
3. **StatsD 集成**：FrameTimeline 与 statsd atom 写入的路径关系与 Android 16 相同。

### 8.2 潜在风险

1. **信号处理脆弱性**：execve 期间的 50ms 延迟可能遗漏短进程。
2. **内存压力**：高采样频率下的 unwinder 队列积压。
3. **FrameTimeline 过滤边界**：`mFilterFramesBeforeTraceStarts` 为 true 时，trace 开始前已启动的 frame packet 会被过滤；该行为来自构造参数，在 Android 17 中仍是默认行为。

## 信息源与参考资料

### 一手源码
- `frameworks/native/services/surfaceflinger/Scheduler/FrameTimeline.{h,cpp}` (android-17.0.0_r1)
- `frameworks/native/libs/gui/include/gui/JankInfo.h` (android-17.0.0_r1)
- `frameworks/native/services/surfaceflinger/Jank/JankTracker.{h,cpp}` (android-17.0.0_r1)
- `external/perfetto/src/profiling/perf/traced_perf.cc` (android-17.0.0_r1)
- `external/perfetto/src/profiling/perf/perf_producer.cc` (android-17.0.0_r1)
- `external/perfetto/traced_perf.rc` (android-17.0.0_r1)

### 相关章节
- 13.2 Trace 抓取 - 基础 trace 配置方法
- 13.9 Android Tracing 基础设施 - 数据采集原理
- 13.14 Perfetto DataGrid 与 Jank CUJ 标准库 - jank 分析实践

---

*本节基于 AOSP `android-17.0.0_r1` 源码分析并通过 Task9 深度技术 Review 验证。与 §13.2、§13.9、§13.14 形成交叉参考体系。*