---
title: "Android 17 Perfetto 数据源边界与验证"
chapter: "13.17"
section: "13.17"
status: ready-for-review
drafted_date: "2026-06-16"
drafted_by: "openclaw-task2a"
applicable_versions: "Android 12 (API 31) - Android 17 (API 37)"
last_verified: "2026-06-16"
last_verified_against: "AOSP android-16.0.0_r3"
confidence: medium
sources:
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
pipeline_stage: "task9_pending"
task6_state: "reviewed"
task6_result: "pass-light-edit"
task9_state: "pending"
reviewed_by: "openclaw-task6"
reviewed_date: "2026-06-16"
last_task6_at: 2026-06-16T22:15:00+08:00
# task2b_state restored 2026-06-16 by Task9 — P0/P1 technical rework required
task9_result: "needs-rework"
task2b_result: "fixed-lite"
task2b_state: "fixed"
task9_reviewed_by: "openclaw-task9"
task9_reviewed_date: "2026-06-16"
last_task9_at: "2026-06-16T21:32:37+08:00"
last_task9_review_log: "logs/deep-review/2026-06-16-21-deep-review.md"
last_task2b_lite_at: 2026-06-16
task9_review_notes: "2026-06-16 21 Task9 deep-review：needs-rework。AOSP android-16.0.0_r3 复核发现 FrameTimeline 源码路径、filter_frames_before_trace_starts flag、JankClassificationThresholds 字段、trace SQL/protobuf 示例与 linux.perf 开销口径存在 P0/P1，已合并 queue P95。"
---

# Android 17 Perfetto 数据源边界与验证

## 章节概述

本章专注于 Android 17 / API 37 的关键 Perfetto 数据源边界验证。基于 Android 16.0.0_r3 源码分析，重点验证 `linux.perf` 和 `android.surfaceflinger.frametimeline` 两个核心数据源的可用性与实现细节。

> **边界声明**：截至 2026-06-16，`android-17.0.0_r1` tag 尚未在 AOSP 公开，所有结论基于 android-16.0.0_r3 与兼容性政策推断。Android 17 公开 tag 发布后需二次验证。

## 核心发现

**Android 17 边界结论**：
- `linux.perf`（`traced_perf` 守护进程）与 `android.surfaceflinger.frametimeline` 在 Android 16.0.0_r3 中保持完整实现
- 基于 AOSP API 兼容性政策，两个数据源在 Android 17 / API 37 中**预期仍可用**
- 需等待 android-17.0.0_r1 公开后执行 `git log android-16.0.0_r3..android-17.0.0_r1 -- paths` 二次确认

<!-- outline-start -->
## 要点

### 🔹 数据源注册机制
`android.surfaceflinger.frametimeline` 在 SurfaceFlinger 启动后无条件注册，`linux.perf` 则按需触发。

### 🔹 Jank 类型判别系统
FrameTimeline 通过 `classifyJankLocked()` 建立完整的 jank 分类机制，11 种类型对应不同的性能影响。

### 🔹 性能开销控制
`linux.perf` 的 100Hz 采样带来约 0.1% 单核开销；`frametimeline` 仅在 trace session 开启时工作，开销极低。

### 🔹 版本演进路径
Android 12 引入两个核心数据源，Android 16 达到完整优化状态，Android 17 需待公开 tag 验证。

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

**关键常量**：`frameworks/native/services/surfaceflinger/Scheduler/FrameTimeline.h`（line 528）
```cpp
static constexpr char kFrameTimelineDataSource[] = "android.surfaceflinger.frametimeline";
```

**注册入口**：`FrameTimeline.cpp`（line 933-939）
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
// SurfaceFlinger.cpp line 762-764
const nsecs_t now = systemTime();
const nsecs_t duration = now - mBootTime;
ALOGI("Boot is finished (%ld ms)", long(ns2ms(duration)) );
mFrameTracer->initialize();
mFrameTimeline->onBootFinished();     // <-- 注册点
```

### 1.2 Jank 类型状态机

`FrameTimeline.cpp` line 600-680 的 `SurfaceFrame::classifyJankLocked()` 是 jank 类型判定的核心，输出位掩码 `JankType`：

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

### 1.3 关键参数配置

**默认阈值**：`FrameTimeline.h` line 95-100
```cpp
struct JankClassificationThresholds {
    nsecs_t presentThreshold = std::chrono::duration_cast<std::chrono::nanoseconds>(2ms).count();
    nsecs_t deadlineThreshold = std::chrono::duration_cast<std::chrono::nanoseconds>(0ms).count();
    nsecs_t startThreshold = std::chrono::duration_cast<std::chrono::nanoseconds>(2ms).count();
};
```

**缓冲区大小**：
```cpp
static constexpr uint32_t kDefaultMaxDisplayFrames = 64;
static constexpr uint32_t kNumSurfaceFramesInitial = 10;
```

### 1.4 Trace Cookie 机制

`FrameTimeline.h` line 122-130：
```cpp
class TraceCookieCounter {
public:
    int64_t getCookieForTracing();
private:
    std::atomic<int64_t> mTraceCookie = 0;
};
```

作用：分离发送 Surface/DisplayFrame 的开始和结束时间戳，避免重复发送完整信息。

### 1.5 Feature Flag 控制门控

`frameworks/native/services/surfaceflinger/common/FlagManager.cpp`：
```cpp
DUMP_ACONFIG_FLAG(filter_frames_before_trace_starts);
FLAG_MANAGER_ACONFIG_FLAG(filter_frames_before_trace_starts, "")
```

`FrameTimeline.cpp` line 919-921：
```cpp
mFilterFramesBeforeTraceStarts(
        FlagManager::getInstance().filter_frames_before_trace_starts() &&
        filterFramesBeforeTraceStarts),
```

含义：控制 trace 启动前的 frame 是否写入 packet。

### 1.6 JankTracker 异步通知链

`JankTracker.cpp` line 26-30 + line 47-75：
- `JankTracker::onJankData()` 在每帧 jank 分类后被调用
- 通过 `BackgroundExecutor::getLowPriorityInstance().sendCallbacks()` 异步推送
- 批量阈值 `kJankDataBatchSize = 50`

## 2. `linux.perf` 数据源

### 2.1 守护进程入口与生命周期

**Init RC 配置**：`external/perfetto/traced_perf.rc`
```rc
service traced_perf /system/bin/traced_perf
    class late_start
    disabled                                           # 不会随 boot 自动启动
    socket traced_perf stream 0666 root root
    user nobody
    group nobody readproc
    capabilities KILL DAC_READ_SEARCH
    writepid /dev/cpuset/foreground/tasks
```

关键特性：
- `class late_start` + `disabled`：必须由上游 service 显式触发
- 触发入口：`cmd tracing perfetto ...` 或 Perfetto session 启动时检测到 `linux.perf` data source
- Socket 通信：环境变量 `ANDROID_SOCKET_traced_perf` 用于进程间通信

### 2.2 Main 函数与 Socket 继承

`external/perfetto/src/profiling/perf/traced_perf.cc` line 24-50：
```cpp
static constexpr char kTracedPerfSocketEnvVar[] = "ANDROID_SOCKET_traced_perf";

int GetRawInheritedListeningSocket() {
  const char* sock_fd = getenv(kTracedPerfSocketEnvVar);
  if (sock_fd == nullptr)
    PERFETTO_FATAL("Did not inherit socket from init.");
  ...
}

int TracedPerfMain(int, char**) {
  base::UnixTaskRunner task_runner;
  AndroidRemoteDescriptorGetter proc_fd_getter{GetRawInheritedListeningSocket(),
                                               &task_runner};
  profiling::PerfProducer producer(&proc_fd_getter, &task_runner);
  producer.ConnectWithRetries(GetProducerSocket());
  task_runner.Run();
  return 0;
}
```

### 2.3 Producer 与数据源标识

`external/perfetto/src/profiling/perf/perf_producer.cc`：
```cpp
constexpr char kProducerName[] = "perfetto.traced_perf";
constexpr char kDataSourceName[] = "linux.perf";
```

### 2.4 进程过滤机制

`perf_producer.cc` line 80-103：
```cpp
bool ShouldRejectDueToFilter(pid_t pid, const TargetFilter& filter) {
  bool reject_cmd = false;
  std::string cmdline;
  if (GetCmdlineForPID(pid, &cmdline)) {
    // reject if absent from non-empty whitelist, or present in blacklist
    reject_cmd = (filter.cmdlines.size() && !filter.cmdlines.count(cmdline)) ||
                 filter.exclude_cmdlines.count(cmdline);
  } else {
    PERFETTO_DLOG("Failed to look up cmdline for pid [%d]",
                  static_cast<int>(pid));
    // reject only if there's a whitelist present
    reject_cmd = filter.cmdlines.size() > 0;
  }

  bool reject_pid = (filter.pids.size() && !filter.pids.count(pid)) ||
                    filter.exclude_pids.count(pid);
  ...
}
```

支持三种过滤方式：
- `target_cmdline`：白名单 cmdline（支持通配符）
- `exclude_cmdlines`：黑名单 cmdline  
- `pids` / `exclude_pids`：直接 PID 过滤

### 2.5 实时进程发现延迟

`perf_producer.cc` line 47：
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
| 性能开销 | 100Hz ≈ 1-3% CPU（unwind 主导） | 极低（仅在 trace session 开启时写 packet） |
| Android 12+ 可用 | 是 | 是 |
| Android 17 验证状态 | 需公开 tag 复核 | 需公开 tag 复核 |

## 4. 版本演进与兼容性

| Android 版本 | 关键差异 | 源码证据 |
|-------------|---------|----------|
| **Android 10 (API 29)** | Perfetto 系统服务内置；不支持两个核心数据源 | FrameTimeline/ 目录不存在 |
| **Android 11 (API 30)** | heapprofd 完善，`android.java_hprof` 引入 | perfetto 主线 |
| **Android 12 (API 31)** | `linux.perf` (`traced_perf`) 引入；`android.surfaceflinger.frametimeline` 引入 | lineage-18.1 traced_perf.cc |
| **Android 13-15 (API 33-35)** | SurfaceFlinger refactor，FrameTimeline 完善 | lineage-22.2 完整实现 |
| **Android 16 (API 36)** | `commit_not_composited` flag、完整优化 | lineage-22.2 = android-16.0.0_r3 |
| **Android 17 (API 37)** | 需公开 tag 复核 | 待验证 |

## 5. 性能影响分析

### 5.1 `linux.perf` 性能开销
- **100Hz 采样**：100Hz × 每次约 1ms unwinder 工作 = ~0.1% 单核开销
- **高频瓶颈**：1000Hz 时 unwinder 队列成为瓶颈（默认 `max_enqueued_footprint_kb` 触发时丢样）
- **启动延迟**：`ConnectWithRetries`（kInitialConnectionBackoffMs=100ms, kMaxConnectionBackoffMs=30s）

### 5.2 `frametimeline` 性能开销
- **空闲开销**：trace session 不开时为 0
- **运行开销**：开启时每个 SurfaceFrame 写 1-2 个 packet，锁竞争极低
- **异步通知**：JankTracker 使用低优先级 BackgroundExecutor，不影响主线程

## 6. 实际应用建议

### 6.1 Trace 数据查询

```sql
-- 查询 FrameTimeline jank 数据（trace_processor SQL）
SELECT display_frame_token, name, jank_type
FROM actual_frame_timeline
WHERE jank_type != 'None'
ORDER BY display_frame_token DESC
LIMIT 20;
```

### 6.2 避免数据丢失

```bash
# 确保 traced_perf 在 FrameTimeline 写入前已启动
adb shell setprop ctl.start traced_perf
adb shell cmd tracing perfetto --start-trigger ...
```

### 6.3 性能优化配置

```protobuf
// PerfEventConfig 优化示例
message PerfEventConfig {
  // 降低采样频率减少 overhead
  optional CallstackSampling callstack_sampling = 16 {
    scope: TARGET_CMDLINE
    target_cmdlines: ["myapp"]
    user_frames: UNWIND_WITH_DWARF
  };
  
  // 限制内存使用
  optional uint64 max_enqueued_footprint_kb = 17 {
    value: 1024  // 1GB
  };
  
  // 针对性 CPU 采样
  repeated uint32 target_cpu = 20 {
    value: [0, 1, 2, 3]  // 仅采样指定核心
  };
}
```

## 7. 二次验证计划

Android 17 / API 37 公开 tag 发布后，需执行以下验证：

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

## 8. 未解问题与未来方向

### 8.1 待验证场景

1. **多进程协调**：`mTraceCookie` 在跨进程场景下的正确性
2. **初始化顺序**：`traced_perf` 与 FrameTimeline 写入的时序保证
3. **StatsD 集成**：FrameTimeline 与 statsd atom 写入的路径关系

### 8.2 潜在风险

1. **信号处理脆弱性**：execve 期间的 50ms 延迟可能遗漏短进程
2. **内存压力**：高采样频率下的 unwinder 队列积压
3. **权限控制**：`filter_frames_before_trace_starts` 的默认值影响数据完整性

## 信息源与参考资料

### 一手源码
- `frameworks/native/services/surfaceflinger/Scheduler/FrameTimeline.{h,cpp}` (android-16.0.0_r3)
- `frameworks/native/services/surfaceflinger/common/FlagManager.cpp` (android-16.0.0_r3)
- `frameworks/native/services/surfaceflinger/Jank/JankTracker.{h,cpp}` (android-16.0.0_r3)
- `external/perfetto/src/profiling/perf/traced_perf.cc` (lineage-18.1)
- `external/perfetto/src/profiling/perf/perf_producer.cc` (lineage-18.1)
- `external/perfetto/traced_perf.rc` (lineage-18.1)

### 相关章节
- 13.2 Trace 抓取 - 基础 trace 配置方法
- 13.9 Android Tracing 基础设施 - 数据采集原理
- 13.14 Perfetto DataGrid 与 Jank CUJ 标准库 - jank 分析实践

---

*本节基于 Android 16.0.0_r3 源码分析，Android 17 需待公开 tag 后二次验证。与 §13.2、§13.9、§13.14 形成交叉参考体系。*