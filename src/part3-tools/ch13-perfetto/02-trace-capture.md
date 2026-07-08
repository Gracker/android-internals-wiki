---
title: Trace 抓取
chapter: '13.2'
status: ready-for-review
applicable_versions: Android 10 (API 29) - Android 17 (API 37)
tags:
- tools
- perfetto
- trace
- capture
polish_by: task2b-polish
task6_state: reviewed
task6_result: pass-light-edit
task6_review_notes: "2026-07-09 Task6 re-review (post-Task9 auto-fix): L1 3 fixes (banned word 对齐→匹配, 2x version pinning 当前主干→Android 17). L2 minor. All 6 anchors + 2 extensions covered. No B-class issues. No banned words remaining."
pipeline_stage: task9_pending
reviewed_by: openclaw-task6
last_task6_audit: 2026-07-09
task2b_result: fixed
task2b_fix_date: 2026-07-08
task2b_fix_notes: "2026-07-08 Task2B main rework: P0 token merge fix (20+ commands/APIs), version baseline update (android-17.0.0_r1 verified), FrameTimeline/linux.perf anchor correction, P1 data source selection flow, P2 unverifiable % removal. Based on deep-review 2026-07-08-21 and audit 2026-07-08-20."
task2b_state: fixed
task9_state: reviewed
task9_result: auto-fixed
last_task9_at: 2026-07-09T00:37:21+08:00
task9_review_notes: "2026-07-09 Task9 deep-review auto-fix: P0=4 P1=0 P2=2. 修正 Android17 DataSourceConfig 新增数据源口径、FrameTimeline/linux.perf Android17 源码锚点与旧伪代码、linux.perf 版本验证矛盾、unsupported profiling overhead 百分比；回到 Task6 复审。"
last_task9_autofix_at: 2026-07-09
---

# Trace 抓取

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 命令行抓取：perfetto -c config.pbtxt -o trace.perfetto-trace
- 🔹 常用 TraceConfig 配置项：buffer_size、duration、data_sources
- 🔹 系统 atrace categories 配置：sched、gfx、view、wm、am、binder 等
- 🔹 用 record_android_trace 脚本快速抓取
- 🔹 通过 Perfetto UI 在线配置与抓取
- 🔹 在 App 中用 Trace.beginSection / Trace.endSection 添加自定义标记

### 扩展（可选深入）

- 🔸 长时间 Trace（Long Trace）的配置与分割策略
- 🔸 Heap Profiling 与 Callstack Sampling 的配置

### OpenClaw 加工指引


<!-- AIW-源码调研-2026-06-07 -->

### 🔸 源码深度补充

基于本次源码调研，补充 linux.perf 和 android.surfaceflinger.frametimeline 两个关键数据源在 Android 17 中的实现细节：

#### Linux.perf 数据源实现
- **守护进程**: `traced_perf` 通过 `ANDROID_SOCKET_traced_perf` 继承 socket 连接到 traced 服务
- **数据源注册**: `kDataSourceName = "linux.perf"` 在 `perf_producer.cc` 中定义
- **事件配置**: 支持内置计数器、追踪点和原始事件三种类型，通过 `EventConfig` 结构管理
- **目标过滤**: `TargetFilter` 支持命令行、PID 和进程分片多重过滤机制

#### FrameTimeline 数据源实现  
- **服务注册**: SurfaceFlinger 模块注册为 `android.surfaceflinger.frametimeline`
- **核心功能**: 检测帧卡顿类型（AppDeadlineMissed、BufferStuffing、SurfaceFlingerCpuDeadlineMissed 等）
- **数据结构**: 提供预期时间线（ExpectedTimeline）和实际时间线（ActualTimeline）两种切片
- **跨进程追踪**: 通过 surface_frame_token 和 display_frame_token 关联应用与 SurfaceFlinger 帧

#### Android 17 版本兼容性
两个数据源在 Android 17 (API 37) 中保持与 Android 12+ 相同的配置方式，源码实现稳定。以下源码锚点均基于 AOSP `android-17.0.0_r1`（Android 17 / API 37）验证。

**运行时要求**: userdebug/eng 构建支持大多数进程采样；user 构建需要目标应用声明 `android:profileable="true"`。


> **锚点**是最低覆盖要求，加工时必须逐条落实并标注验证结果。
> **扩展**视素材丰富程度选择性深入。
> 如果从 Obsidian 素材或 AOSP 源码中发现大纲未列出但与本节强相关的知识点，可**就地插入**最相关的锚点之后，并用 `[自动发现]` 标注，方便后续 review。
> 锚点内容需 L1/L2 验证，扩展内容至少 L2 验证，自动发现内容至少标注来源。
<!-- outline-end -->



<!-- AIW-源码调研-2026-06-08 补充 -->
### 🔸 2026-06-08 源码锚点强化与 Linux.Perf 完整调用链

#### FrameTimeline 架构细节（基于 android-17.0.0_r1）

1. **数据源注册**：`frameworks/native/services/surfaceflinger/Scheduler/FrameTimeline.cpp:1344-1354`（android-17.0.0_r1）
   ```cpp
   void FrameTimeline::onBootFinished() {
       perfetto::TracingInitArgs args;
       args.backends = perfetto::kSystemBackend;
       perfetto::Tracing::Initialize(args);
       registerDataSource();
   }
   void FrameTimeline::registerDataSource() {
       perfetto::DataSourceDescriptor dsd;
       dsd.set_name(kFrameTimelineDataSource);  // "android.surfaceflinger.frametimeline"
       FrameTimelineDataSource::Register(dsd);
   }
   ```

2. **SurfaceFrame Jank 分类逻辑**：`FrameTimeline.cpp:829-899`
   - `SurfaceFrame::classifyJankLocked(...)` 在 Android 17 中返回 `void`，不是旧资料里的 `uint32_t` 返回值函数。
   - 该函数先处理 invalid present time、prediction expired、missing token，再调用 `classifyJankLegacyLocked(...)` 并计算 deadline/present delta。
   - `AppDeadlineMissed`、`BufferStuffing`、`SurfaceFlingerCpuDeadlineMissed` 仍属于 SurfaceFrame jank 归因，但不能把旧版伪代码当作 Android 17 源码片段。

3. **TraceCookie 机制**：`FrameTimeline.h:148-156, 677`
   - `TraceCookieCounter::mTraceCookie = std::atomic<int64_t>` 负责生成 Perfetto packet cookie。
   - `FrameTimeline` 持有 `mTraceCookieCounter`，SurfaceFrame / DisplayFrame 通过该 counter 匹配 start/end packet。

4. **FeatureFlag 机制**：`frameworks/native/services/surfaceflinger/common/FlagManager.cpp:137,154-155`
   ```cpp
   DUMP_ACONFIG_FLAG(frametimeline_boottime_in_lambda);
   DUMP_ACONFIG_FLAG(use_content_priority_for_jank_classification);
   DUMP_ACONFIG_FLAG(use_experimental_jank_classification);
   ```
   Android 17 未复核到旧资料中的 `filter_frames_before_trace_starts`，FrameTimeline 相关判断应以上述 AOSP flags 为锚点。

#### Linux.Perf 守护进程架构（基于 android-17.0.0_r1）

1. **Socket 继承机制**：`external/perfetto/src/profiling/perf/traced_perf.cc:34-40`
   ```cpp
   static constexpr char kTracedPerfSocketEnvVar[] = "ANDROID_SOCKET_traced_perf";
   int GetRawInheritedListeningSocket() {
       const char* sock_fd = getenv(kTracedPerfSocketEnvVar);
       if (sock_fd == nullptr) PERFETTO_FATAL("Did not inherit socket from init.");
   }
   ```

2. **Producer 注册**：`external/perfetto/src/profiling/perf/perf_producer.cc:80-81`
   ```cpp
   constexpr char kProducerName[] = "perfetto.traced_perf";
   constexpr char kDataSourceName[] = "linux.perf";
   ```

3. **进程过滤实现**：`perf_producer.cc:326-381`
   - `PerfProducer::ShouldRejectDueToFilter(...)` 先匹配 `exclude_cmdlines` / `exclude_pids`，再匹配 `cmdlines` / `pids`，allow filter 为空时保留未显式排除的进程。
   - `TargetFilter` 还支持 `additional_cmdline_count` 与 `process_sharding`，用于摊薄系统级 unwinding 成本。

4. **execve 保护延迟**：`perf_producer.cc:73`
   ```cpp
   constexpr uint32_t kProcDescriptorsAndroidDelayMs = 50;  // 防止 execve 期间 signal disposition 默认 terminate
   ```

#### Android 17 源码验证

以下源码锚点均基于 AOSP `android-17.0.0_r1`（Android 17 / API 37），已通过 Gitiles 复核确认可访问：

- `external/perfetto/src/profiling/perf/perf_producer.cc:81` — `kDataSourceName = "linux.perf"`
- `external/perfetto/src/profiling/perf/traced_perf.cc:34` — `ANDROID_SOCKET_traced_perf`
- `frameworks/native/services/surfaceflinger/Scheduler/FrameTimeline.h:656` — `kFrameTimelineDataSource`
- `frameworks/native/services/surfaceflinger/Scheduler/FrameTimeline.cpp:1351-1354` — `registerDataSource()`
- `frameworks/native/services/surfaceflinger/SurfaceFlinger.cpp:820` — `mFrameTimeline->onBootFinished()`



## 为什么要了解 Trace 抓取

性能分析的第一步永远是"拿到数据"。不管我们是排查卡顿、分析启动速度、还是调查 ANR，都需要先抓取一份 Trace 文件，然后在 Perfetto UI 中打开它。如果抓取的配置不对——比如漏掉了关键的 atrace category，或者 buffer 太小导致数据被覆盖——后续分析就无从谈起。

而且，Trace 抓取不是只有一种方式。不同场景需要不同的抓取策略：快速复现一个卡顿问题，用 `record_android_trace` 脚本几行命令就能搞定；分析启动性能，需要在 App 代码中插入自定义标记来精确度量各个阶段；排查内存泄漏，则需要额外开启 Heap Profiling。了解这些方式的差异和适用场景，能让我们在最短时间内拿到最有价值的 Trace 数据。

PerfettoTrace 有几种常见抓取方式，从命令行到 Perfetto UI、从系统级到 App 内自定义标记，各有适用场景。最后会给出一份覆盖常见分析场景的推荐配置。

## 命令行抓取：perfetto 命令

[已验证: 官方文档, perfetto.dev/docs/quickstart/android-tracing]

最基础的抓取方式是直接在设备上运行 `perfetto` 命令。Perfetto 从 Android 10（API 29）开始作为系统级追踪工具内置在设备中，我们只需要通过 `adb shell` 就可以调用它。

> **Android 17 源码状态** [已验证: Perfetto 官方文档 + AOSP `external/perfetto` android-17.0.0_r1]：以下数据源在 Android 10–17 范围内均保持可用，已通过 AOSP `android-17.0.0_r1` 源码验证关键文件可访问：
> - `linux.ftrace`、`linux.process_stats`、`linux.sys_stats`：Android 10+ 可用
> - `android.heapprofd`：Android 10+ 可用
> - `android.java_hprof`：Android 11+ 可用
> - `android.surfaceflinger.frametimeline`：Android 12+ 可用
> - `linux.perf`：Android 12+ 可用
> 本节抓取方法和配置示例基于 Android 10–17 源码与官方兼容性文档校验。Android 17 的 `DataSourceConfig` 追加了 `android.user_list`、`android.inputmethod`、`android.aflags` 等数据源；上述常用抓取数据源在 Android 17 中未废弃。

### 最简命令

```bash
adb shell perfetto -o /data/misc/perfetto-traces/trace.perfetto-trace -t10s \
  sched freq idle am wm gfx view binder_driver hal dalvik input res memory
```

这条命令启动一个 10 秒的追踪会话，收集指定的 atrace category 数据，输出到设备上的指定路径。抓取完成后，用 `adb pull` 把文件拉到本地：

```bash
adb pull /data/misc/perfetto-traces/trace.perfetto-trace
```

这几个参数决定输出位置、抓取时长和事件范围：

- `-o` 指定输出路径。Perfetto 要求输出路径必须在 `/data/misc/perfetto-traces/` 目录下（需要 root 或 shell 权限），这个目录是 Perfetto 服务进程有写入权限的标准位置。
- `-t10s` 指定追踪时长。也可以用 `-t20s`、`-t1m` 等格式。如果不指定 `-t`，追踪会持续到手动停止。
- 后面的 `sched freq idle am wm gfx ...` 是 atrace category 列表，决定抓取哪些系统事件。我们稍后详细讨论。

### 使用配置文件抓取

当追踪需求稍微复杂一些——比如需要调整 buffer 大小、开启多个数据源、或者配置 Long Trace——直接在命令行拼接参数就不太方便了。这时候可以用配置文件的方式。

Perfetto 使用 ProtocolBuffer 文本格式（`.pbtxt`）的配置文件，官方称为 `TraceConfig`。我们可以把完整的配置写到一个文件中，然后通过 `-c` 参数传给 `perfetto` 命令。

**Android 12+** 可以把配置文件 push 到设备上直接引用：

```bash
adb push config.pbtxt /data/misc/perfetto-configs/config.pbtxt
adb shell perfetto -c /data/misc/perfetto-configs/config.pbtxt \
  --txt \
  -o /data/misc/perfetto-traces/trace.perfetto-trace
```

**Android 10/11** 非 root 设备受 SELinux 规则限制，配置只能通过 stdin 传入：

```bash
cat config.pbtxt | adb shell perfetto -c - \
  --txt \
  -o /data/misc/perfetto-traces/trace.perfetto-trace
```

注意 `--txt` 参数告诉 Perfetto 配置文件是人类可读的文本格式（而非二进制 protobuf）。

`TraceConfig` 文件的基本结构是这样的：

```textproto
buffers {
  size_kb : 65536
  fill_policy : DISCARD
}

data_sources {
  config {
    name: "linux.ftrace"
    ftrace_config {
      ftrace_events : "sched/sched_switch"
      ftrace_events : "power/cpu_frequency"
      ftrace_events : "power/cpu_idle"
      atrace_categories : "am"
      atrace_categories : "wm"
      atrace_categories : "gfx"
      atrace_categories : "view"
      atrace_categories : "sched"
    }
  }
}

data_sources {
  config {
    name: "linux.process_stats"
    process_stats_config {
      scan_all_processes_on_start : true
    }
  }
}

duration_ms : 10000
```

[图：TraceConfig 文件结构示意——buffer 配置、data_sources 配置、duration 配置三段]

这份配置做的事情是：分配 64MB 的 tracebuffer，开启 ftrace 数据源（包括内核调度事件和 atrace category），同时收集进程信息，追踪 10 秒后自动停止。

## 常用 TraceConfig 配置项

[已验证: 官方文档, perfetto.dev/docs/concepts/config]

TraceConfig 决定 Perfetto 追踪会话的 buffer、时长和数据源。理解这几个配置项后，抓取窗口和数据量才好控制。

### buffer 配置

`buffers` 块定义了 Trace 数据的内存缓冲区。每个 Trace 会话至少需要一个 buffer。

```textproto
buffers {
  size_kb : 65536          # 64MB
  fill_policy : DISCARD     # 满了就丢弃新数据
}
```

- `size_kb`：buffer 大小，单位 KB。常见的值是 32768（32MB）到 131072（128MB）。buffer 太小会导致数据被覆盖或丢失，太大会占用过多内存。对于 10-30 秒的常规 Trace，64MB 通常是够用的。如果开启了调用栈采样或 Heap Profiling，需要更大的 buffer。
- `fill_policy`：满时的策略。`DISCARD` 表示 buffer 满后丢弃新事件（Stop when full），适合确定性抓取；`RING_BUFFER` 表示环形覆盖，旧数据被新数据覆盖，适合长时间监控。

### duration 配置

```textproto
duration_ms : 10000    # 10 秒
```

`duration_ms` 指定追踪时长，单位毫秒。如果不设置，Trace 会一直持续到手动停止（通过 `adb shell kill -S IGINT <pid>`）。对于可复现的性能问题，设置固定时长可以精确控制抓取窗口。

### data_sources 配置

`data_sources` 是 TraceConfig 中最核心的部分，它决定了我们抓取哪些数据。每个 data_source 都有一个 `name` 字段和对应的 config。

最常用的数据源是 `linux.ftrace`，它负责采集内核 ftrace 事件和 atrace 用户空间事件。其他的常用数据源包括：

- `linux.process_stats`：进程和线程信息
- `linux.sys_stats`：系统级统计（CPU、内存、I/O）
- `android.log`：logcat 日志
- `android.surfaceflinger.frametimeline`：帧时间线数据（仅 Android 12+，API 31+）。经验证，此数据源在 Android 17 (API 37) 中持续可用，配置方式不变。
- `android.gpu.memory`：GPU 内存使用

我们可以同时启用多个数据源，只需要在 TraceConfig 中添加多个 `data_sources` 块即可。

### 一个推荐的通用配置

通用配置可以拆成两份可直接执行的版本。`.pbtxt` 是 protobuftextformat，不能把版本判断写成运行时分支后直接塞进配置文件。跨版本抓取有两种做法：手工准备两份配置，或由 host 侧脚本按 APIlevel 生成对应文件。

#### Android 10 / 11 基线配置

```textproto
buffers {
  size_kb : 65536
  fill_policy : DISCARD
}

data_sources {
  config {
    name: "linux.ftrace"
    ftrace_config {
      ftrace_events : "sched/sched_switch"
      ftrace_events : "sched/sched_wakeup"
      ftrace_events : "sched/sched_waking"
      ftrace_events : "sched/sched_blocked_reason"
      ftrace_events : "power/cpu_frequency"
      ftrace_events : "power/cpu_idle"
      ftrace_events : "power/gpu_frequency"
      ftrace_events : "power/suspend_resume"

      atrace_categories : "am"
      atrace_categories : "wm"
      atrace_categories : "gfx"
      atrace_categories : "view"
      atrace_categories : "input"
      atrace_categories : "binder_driver"
      atrace_categories : "hal"
      atrace_categories : "dalvik"
      atrace_categories : "res"
      atrace_categories : "sched"
      atrace_categories : "freq"
      atrace_categories : "idle"

      atrace_apps : "com.example.myapp"
    }
  }
}

data_sources {
  config {
    name: "linux.process_stats"
    process_stats_config {
      scan_all_processes_on_start : true
    }
  }
}

data_sources {
  config {
    name: "linux.sys_stats"
    sys_stats_config {
      meminfo_period_ms : 1000
      stat_period_ms : 1000
      stat_counters : STAT_CPU_TIMES
      stat_counters : STAT_FORK_COUNT
    }
  }
}

duration_ms : 20000
```

#### Android 12+ 配置（追加 FrameTimeline）

```textproto
buffers {
  size_kb : 65536
  fill_policy : DISCARD
}

data_sources {
  config {
    name: "linux.ftrace"
    ftrace_config {
      ftrace_events : "sched/sched_switch"
      ftrace_events : "sched/sched_wakeup"
      ftrace_events : "sched/sched_waking"
      ftrace_events : "sched/sched_blocked_reason"
      ftrace_events : "power/cpu_frequency"
      ftrace_events : "power/cpu_idle"
      ftrace_events : "power/gpu_frequency"
      ftrace_events : "power/suspend_resume"

      atrace_categories : "am"
      atrace_categories : "wm"
      atrace_categories : "gfx"
      atrace_categories : "view"
      atrace_categories : "input"
      atrace_categories : "binder_driver"
      atrace_categories : "hal"
      atrace_categories : "dalvik"
      atrace_categories : "res"
      atrace_categories : "sched"
      atrace_categories : "freq"
      atrace_categories : "idle"

      atrace_apps : "com.example.myapp"
    }
  }
}

data_sources {
  config {
    name: "linux.process_stats"
    process_stats_config {
      scan_all_processes_on_start : true
    }
  }
}

data_sources {
  config {
    name: "linux.sys_stats"
    sys_stats_config {
      meminfo_period_ms : 1000
      stat_period_ms : 1000
      stat_counters : STAT_CPU_TIMES
      stat_counters : STAT_FORK_COUNT
    }
  }
}

data_sources {
  config {
    name: "android.surfaceflinger.frametimeline"
  }
}

duration_ms : 20000
```

两份配置的差别只有一处：Android 12+ 多了 `android.surfaceflinger.frametimeline` 数据源。低版本设备保留 `linux.ftrace`、`linux.process_stats` 和 `linux.sys_stats`，就能正常抓取调度、atrace 和系统统计数据。

[图：通用配置覆盖的数据维度——CPU 调度、渲染管线、系统统计、帧时间线]

注意 `atrace_apps` 字段。如果要追踪特定 App 的自定义 Trace 标记（通过 `Trace.beginSection` 添加的），必须在这里指定 App 的包名。否则即使 App 代码中有 `Trace.beginSection` 调用，也不会出现在 Trace 中。

## atraceCategories 详解

[已验证: 官方文档, source.android.com/devices/tech/debug/ftrace; AOSPatrace category 定义]

atrace categories 是 Android 系统预定义的事件分类，每一个 category 对应一组系统模块的追踪事件。选择正确的 category 组合，是拿到有价值 Trace 的关键。

在命令行中，我们可以用 `adb shell atrace --list_categories` 查看当前设备支持的所有 category。不同设备、不同 Android 版本支持的列表可能略有差异，但核心的几个 category 在所有设备上都可用。

日常性能分析中最常用的 categories 可以按用途分组：

### 渲染与 UI（分析卡顿、流畅度必备）

- **gfx**：Graphics 子系统的事件，包括 SurfaceFlinger 合成、BufferQueue 状态变化、Choreographer 的 VSync 回调等。分析帧渲染管线问题（如掉帧、GPU 耗时过长）时，`gfx` 是必选的。
- **view**：View 系统事件，包括 measure、layout、draw 的耗时。卡顿分析中，`view` category 能直接告诉我们某一帧的 measure/layout/draw 阶段花了多长时间。

### 系统服务（分析启动、ANR 必备）

- **am**：ActivityManager 事件，包括 Activity 的生命周期回调、Service 启停、Broadcast 分发等。分析 App 启动流程和 ANR 时，`am` 是核心 category。
- **wm**：WindowManager 事件，包括窗口的添加、移除、焦点变化等。配合 `am` 使用可以追踪完整的 UI 展示流程。
- **sm**：ServiceManager 事件，追踪系统服务的注册和获取。在 Binder 调用频繁的场景中有参考价值。

### CPU 调度（几乎所有场景都要选）

- **sched**：CPU 调度事件，包括线程的唤醒、切换、阻塞原因。这是 Perfetto 中最重要的 category——没有 `sched`，我们看不到每个线程在什么时候运行、什么时候被挂起、为什么被挂起。几乎所有性能分析场景都应该选上 `sched`。
- **freq**：CPU 频率变化事件。配合 `sched` 使用，可以看出线程在什么频率的 CPU 核心上运行，判断是否存在频率爬升慢导致的性能问题。
- **idle**：CPU idle 状态事件。可以观察 CPU 是否进入了深度睡眠，以及被唤醒的原因。

### Binder 与 IPC

- **binder_driver**：Binder 驱动事件，包括 Binder 事务的开始和完成。分析跨进程调用的耗时、Binder 调用阻塞主线程导致的 ANR 时，通常都要带上这个 category。

### 运行时与资源

- **dalvik**：ART 虚拟机事件，包括 GC、JIT 编译等。内存抖动或 GC 暂停导致的卡顿，需要 `dalvik` category 来定位。
- **res**：资源加载事件。追踪资源（图片、布局等）的加载耗时。
- **input**：Input 事件分发，包括触摸事件的入队和分发。分析点击响应延迟、滑动卡顿时，`input` category 提供了事件到达应用的时间线起点。
- **memory**：内存事件。追踪内存分配和释放相关的系统事件。

### 按分析场景选择 Categories

不同性能分析场景需要不同的 category 组合，可以先按这份表选：

| 分析场景 | 推荐 Categories |
|---------|----------------|
| 卡顿/流畅度 | `sched freq gfx view input` |
| App 启动 | `sched freq am wm view binder_driver` |
| ANR | `sched am wm binder_driver input` |
| Binder 性能 | `sched binder_driver` |
| 内存问题 | `sched dalvik memory gfx` |
| 功耗分析 | `sched freq idle power` |

这张表适合入门阶段使用。经验积累到一定程度后，可以按具体问题调整 category 组合——例如分析 HAL 层音频延迟时加上 `audio`，追踪 Camera 管线时加上 `camera`。`sched` + `freq` + `gfx` + `view` 仍然是多数场景下的基础组合。

## 用 record_android_trace 快速抓取

[已验证: 官方文档, perfetto.dev/docs/quickstart/android-tracing]

`record_android_trace` 是 Perfetto 团队提供的一个 Python 脚本，它封装了底层 `perfetto` 命令的复杂性，让抓取 Trace 变得像运行一个命令一样简单。

### 获取脚本

```bash
curl -O https://raw.githubusercontent.com/google/perfetto/main/tools/record_android_trace
chmod +x record_android_trace
```

> ⚠️ 在中国大陆网络环境下，访问 GitHubraw 域名可能需要代理。也可以从 Perfetto 发布页（< https://github.com/google/perfetto/releases >）下载对应版本的脚本。

### 基本用法

最小命令不带任何参数：

```bash
python3 record_android_trace -o trace.perfetto-trace
```

如果不传 `-t`，脚本会持续抓取，直到我们手动停止。更多时候，我们会显式给出时长、buffer 大小和 atrace categories：

```bash
python3 record_android_trace -o trace.perfetto-trace -t20s -b 64mb \
  sched freq idle am wm gfx view binder_driver hal dalvik input res memory
```

这里 `-t20s` 表示 20 秒，`-b 64mb` 表示 64 MB buffer，后面的参数是 atrace category 列表。`-t`、`-b`、`-a` 这一组 short options 只适用于不带 `-c/--config` 的快速抓取。

### 为什么推荐这个脚本

相比直接在设备上运行 `perfetto` 命令，`record_android_trace` 把最繁琐的几个步骤自动化了。脚本会自动从设备 pull Trace 文件到本地当前目录，省去了手动 `adb pull`。抓取完成后还会自动在浏览器中打开 Perfetto UI 并加载 Trace，不需要手动拖文件。ADB 连接和权限问题也由脚本处理——对于需要频繁抓取 Trace 的日常分析，这些自动化能省下不少时间。

如果需要更精细的配置，可以通过 `-c` 参数传入 `.pbtxt` 配置文件。这时 `duration_ms`、buffer 大小、`atrace_apps` 等参数也写回 `config.pbtxt`，不再和 `-t`、`-b`、`-a` 混用：

```bash
python3 record_android_trace -c config.pbtxt -o trace.perfetto-trace
```

对于日常的快速分析场景，`record_android_trace` 脚本依然是最省事的抓取入口。

## 通过 Perfetto UI 在线抓取

[已验证: 官方文档, ui.perfetto.dev/#!/record]

Perfetto UI（<https://ui.perfetto.dev>）不仅是一个 Trace 分析工具，它还内置了 Trace 抓取功能。打开网站后，左侧导航栏选择 "Record new trace"，就可以通过图形界面配置和执行抓取。

### 连接设备

使用 USB 线连接设备和电脑后，Perfetto UI 会自动检测到连接的 Android 设备。在 "Target platform" 下拉框中选择对应设备。

如果设备没有被检测到，需要确认 ADB 连接正常（`adb devices` 能列出设备），并且浏览器支持 WebUSB。

### 配置抓取参数

Perfetto UI 把配置分成了几个直观的 Tab：

**Buffer 模式选择**（在 "Recording mode" 区域）：
- **Stop when full**：buffer 满了就停止（默认，最常用）。适合确定性时长抓取。
- **Ring buffer**：环形覆盖，新数据覆盖旧数据。适合不确定何时复现的问题。
- **Long trace**：持续写入文件。适合长时间追踪（几分钟到几小时）。

**数据源选择**（在各个 Tab 页中）：
- **CPU**：包括 CPU 调度、频率、idle 状态、调用栈采样。性能分析基本都要选。
- **GPU**：GPU 渲染阶段、GPU 内存。
- **Memory**：内存信息、Heap Profiling。
- **AndroidApps**：atrace categories 和指定 App 的 Trace 事件。
- **Advanced**：logcat、系统统计、网络包等。

[图：Perfetto UI 抓取界面截图——左侧 Recordingmode 选择，中间数据源配置 Tab，右侧 StartRecording 按钮]

### 导出配置为命令行

Perfetto UI 可以把可视化配置导出为命令行：在 UI 上配好参数后，切到 "Recording command" Tab，就会显示对应的命令行和 `.pbtxt` 配置文件。

这样我们就能把 UI 上的可视化配置直接转成可重复执行的脚本命令。在团队协作中，可以把这份配置文件提交到代码仓库，确保所有人使用相同的 Trace 配置。

操作方式是：在 "Recording command" Tab 中，复制两个 EOF 标记之间的内容，保存为 `config.pbtxt` 文件。之后团队成员就可以直接用这个配置文件来抓取 Trace，抓取时长和 buffer 参数也统一由 `config.pbtxt` 控制：

```bash
python3 record_android_trace -c config.pbtxt -o trace.perfetto-trace
```

## 在 App 中添加自定义 Trace 标记

[已验证: 官方文档, developer.android.com/reference/android/os/Trace; AOSP `frameworks/base/core/java/android/os/Trace.java`]

系统默认的 atrace category 覆盖了大部分系统级行为，但很多时候我们需要在 App 代码中标记自定义的业务逻辑耗时——比如 "加载首页数据"、"初始化播放器"、"解析 JSON 响应" 这些 App 特有的阶段。Android 提供了 `android.os.Trace` API 来实现这个需求。

### 基本用法

```java
import android.os.Trace;

// 标记一段代码的开始
Trace.beginSection("loadHomePageData");

try {
    // ... 实际的业务代码 ...
    fetchDataFromNetwork();
    parseJsonResponse();
    updateUI();
} finally {
    // 标记结束（必须与 beginSection 配对）
    Trace.endSection();
}
```

抓取 Trace 时，只要在 atrace categories 中包含了 App 的包名（通过 `atrace_apps` 或命令行参数 `-a com.example.myapp`），这些自定义标记就会出现在 Perfetto UI 中**调用线程对应的 track** 上，显示为带有标签名的彩色切片。如果示例在主线程调用 `Trace.beginSection`，slice 显示在主线程 track；如果在工作线程或 RenderThread 调用，slice 会出现在对应线程 track，不会统一落到主线程。跨线程操作应改用 `Trace.beginAsyncSection` / `Trace.endAsyncSection`。

`Trace.beginSection` 和 `Trace.endSection` 使用的底层标签是 `ATRACE_TAG_APP`。因此，所有通过 `android.os.Trace` API 添加的标记都会归类到同一个 tag 下。

### 使用约束

使用这套 API 时有几个关键约束。

最基本的要求是 `beginSection` 和 `endSection` 必须**严格配对、嵌套调用**——不能交叉嵌套，也不能在一个线程中 `beginSection` 然后在另一个线程中 `endSection`。`Trace.endSection()` 不需要传入标签名，它自动关闭最近一次 `beginSection` 对应的区域，和栈的 push/pop 机制一样。正因为这个栈式设计，如果 `endSection` 调用次数和 `beginSection` 不匹配，后续所有标记都会错位。

`Trace.beginSection` 的 section name 上限是 127 个 Unicode code unit。Java public API 对过长名字会抛出 `IllegalArgumentException`；native 侧也受 ATrace 消息长度和 ftrace `trace_marker` 写入格式约束。这个限制来自一条 trace_marker 消息要同时容纳事件类型、线程信息和 section name，名字过长会增加 trace buffer 压力，也会让 Perfetto UI 难以阅读。建议使用简洁但足够描述性的标签名，比如 `"HomeFragment.loadData"`，不要把请求 URL、JSON 片段或用户标识塞进 section name。

另外，`beginSection`/`endSection` 只能在同一线程中使用。跨线程操作要改用异步 API。

### 异步标记（API 29+）

从 Android 10（API 29）开始，`android.os.Trace` 增加了异步追踪 API，可以跨线程标记一个操作的开始和结束：

```java
import android.os.Trace;

// 在一个线程中开始
int cookie = 1001;  // 同一次异步操作在 begin / end 两端保持同一个 int 值
Trace.beginAsyncSection("networkRequest", cookie);

// ... 网络请求 ...

// 在回调线程中结束
Trace.endAsyncSection("networkRequest", cookie);
```

`beginAsyncSection` 和 `endAsyncSection` 通过同一个 `int cookie` 关联一次异步操作。这解决了异步操作（如网络请求、Handler 回调）中无法使用同步 `beginSection`/`endSection` 的问题。如果业务里原本用的是 `long` 请求 ID，需要先做显式转换或映射，再传给这组 API。

### Native 代码中的自定义标记

对于普通 App 的 C/C++ 代码（JNI 层、NDK so），用 public NDK 头文件 `android/trace.h`：

```c
#include <android/trace.h>

ATrace_beginSection("nativeInit");
// ... 初始化代码 ...
ATrace_endSection();
```

这组 API 和 `android.os.Trace` 一样，底层都走 app tracing tag，抓取时仍然需要把目标包名放进 `atrace_apps` 或 `record_android_trace -a`。

如果代码运行在平台内部模块里，AOSP 代码里还会看到 `<cutils/trace.h>` 和 `ATRACE_BEGIN` / `ATRACE_END`。这套头文件不面向普通 App / NDK 工程，这里只把它当作 framework / system code 的实现路径，不把它当成通用示例。

如果要讲 PerfettoSDK，则是另一条集成路径。PerfettoSDK 通过头文件注入的方式集成，需要在项目的 `CMakeLists.txt` 或 `Android.bp` 中添加 SDK 源码依赖，然后使用 `TRACE_EVENT` 宏来标记自定义事件。集成方式详见 Perfetto 官方文档的 [Instrumentation SDK](https://perfetto.dev/docs/instrumentation/tracing-sdk) 章节。[待补充: 完整的 CMake 集成示例]

### 在 Perfetto 中的表现

在 Perfetto UI 中，自定义 Trace 标记出现在 App 进程对应线程的 track 上。每个 `beginSection`/`endSection` 对显示为一个带有标签文字的切片（slice），长度表示耗时。

[图：Perfetto UI 中自定义 Trace 标记的展示——App 主线程 track 上的 "loadHomePageData" 等自定义切片]

通过自定义标记和系统事件的叠加，我们可以在同一个时间轴上看到业务逻辑耗时和系统级行为（如 VSync、GC、Binder 调用）的完整上下文。这种"业务 + 系统"的双视角，是 Perfetto 分析区别于传统 profiling 工具的核心优势之一。

此外，Android 设备的开发者选项中内置了**系统追踪**应用，可以直接在设备上配置和启动 Trace 抓取，无需连接电脑。适合在现场复现问题时使用。抓取完成后，Trace 文件保存在设备上，后续可以通过 `adb pull` 导出。入口为"设置 → 开发者选项 → 系统追踪"。

## Long Trace：长时间追踪

[已验证: 官方文档, perfetto.dev/docs/concepts/config#long-traces]

默认情况下，Perfetto 把 Trace 数据全部缓存在内存 buffer 中，在会话结束时一次性写入文件。这种方式的优点是开销最小，缺点是 Trace 大小受设备物理内存限制——通常能记录几十秒到几分钟的数据。

但有些问题需要长时间追踪才能复现：比如偶发的 ANR（可能几小时才出现一次）、长时间运行后的内存泄漏、或者跑分场景下完整的 Benchmark 过程。Perfetto 的 Long Trace 模式就是为了这类场景设计的。

### 启用 Long Trace

启用 Long Trace 时，需要在 TraceConfig 中设置 `write_into_file: true`：

```textproto
buffers {
  size_kb : 32768    # 32MB in-memory buffer
}

write_into_file: true
file_write_period_ms : 5000     # 每 5 秒刷盘一次
max_file_size_bytes : 2147483648   # 最大 2GB

duration_ms : 3600000   # 1 小时

data_sources {
  config {
    name: "linux.ftrace"
    ftrace_config {
      ftrace_events : "sched/sched_switch"
      ftrace_events : "sched/sched_wakeup"
      ftrace_events : "power/cpu_frequency"
      atrace_categories : "am"
      atrace_categories : "wm"
      atrace_categories : "gfx"
      atrace_categories : "view"
      atrace_categories : "sched"
    }
  }
}
```

这几个参数决定刷盘节奏和文件上限：

- `write_into_file: true`：启用 Long Trace 模式，Trace 数据会定期从内存 buffer 刷写到磁盘文件。
- `file_write_period_ms`：刷盘间隔。默认是 5000ms（5 秒）。更短的间隔意味着每次刷盘的数据量更少、buffer 可以更小，但磁盘 I/O 更频繁。
- `max_file_size_bytes`：Trace 文件的最大大小。达到上限后 Trace 自动停止。不设置则无限制（直到磁盘满）。
- `duration_ms`：总追踪时长。Long Trace 通常设置较长的时长。

### Long Trace 的注意事项

Long Trace 在降低内存要求的同时引入了新的 trade-off。

**磁盘 I/O 开销**是一个需要关注的因素。每次刷盘都会产生磁盘写入，在 I/O 敏感的场景（如 Benchmark）中可能影响测量结果的准确性。如果对 I/O 干扰敏感，可以适当增大 `file_write_period_ms` 来降低刷盘频率，代价是内存 buffer 需要更大来缓存中间数据。

数据源也需要精简。长时间追踪时，如果开启了太多 atrace category，生成的数据量可能非常大。建议只保留分析目标相关的核心 category，通常 `sched` + `freq` + `gfx` + `view` 就够了。

最实际的挑战是**大文件分析**。长时间追踪可能产生几百 MB 甚至几 GB 的 Trace 文件，这种大文件在浏览器中通过 ui.perfetto.dev 打开会非常慢甚至崩溃。解决方案是使用 `trace_processor_shell` 命令行工具在本地解析，然后在 Perfetto UI 中通过本地 HTTP 服务查看。具体操作参见 §13.4（大 Trace 文件处理）。

## Heap Profiling 与 Callstack Sampling

[已验证: 官方文档, perfetto.dev/docs/data-sources/native-heap-profiler ; perfetto.dev/docs/reference/trace-config-proto#perfeventconfig]

Perfetto 不只能做时间线追踪。它还集成了内存剖析（Heap Profiling）和 CPU 调用栈采样（Callstack Sampling），可以在同一个 Trace 会话中同时收集这些数据。

### 数据源选择指南

开启 Heap Profiling 或 Callstack Sampling 之前，先确认问题类型和可用权限，再选择对应的数据源：

| 分析目标 | 推荐数据源 | 最低 Android 版本 | 权限要求 | 数据形态 |
|----------|-----------|------------------|---------|---------|
| Native 内存泄漏（趋势观察） | `android.heapprofd` | Android 10 | userdebug/eng，或 user 构建 + `android:profileable` | 按调用栈聚合的分配统计 + 火焰图 |
| Java 对象持有关系（快照） | `android.java_hprof` | Android 11 | userdebug/eng，或 user 构建 + `android:profileable` | 单次 heap dump，进程会短暂停顿 |
| Java 分配热点（持续） | `android.heapprofd` + `heaps:"com.android.art"` | Android 12 | 同 heapprofd | 持续采样 Java 堆分配 |
| CPU 密集型瓶颈 | `linux.perf` | Android 12 | userdebug/eng（user 构建须目标 App 为 profileable/debuggable） | 调用栈采样频率图 |
| 调用栈采样（system_server） | `linux.perf` | Android 12+ | system_server 在 user 构建下也支持采样 | 系统服务调用栈火焰图 |

选择流程：**问题类型 → 对应数据源 → 确认权限可用性 → 评估 buffer 和性能开销 → 确定结果分析方式**。

开启 profiling 类数据源会显著增加 Trace 体积和运行时开销。建议：
- **buffer**：Heap Profiling 和 Callstack Sampling 建议 buffer ≥ 128 MB，Long Trace 场景 ≥ 256 MB
- **采样间隔**：heapprofd 官方默认 `sampling_interval_bytes: 4096`。采样间隔越小，精度越高、运行时开销越大；设到 1024 这类更激进的值前，应先用短 Trace 验证目标场景是否可接受
- **先排查再 profiling**：先用 `linux.ftrace` + `gfx`/`sched` 快速定位问题线程，再针对性地开启 profiling

### Native Heap Profiling（heapprofd）

`heapprofd`（Heap Profiling Daemon）是 Android 10+ 内置的采样式堆内存分析器，运行在目标进程中。它通过 hook `malloc`/`free`（以及 C++ 的 `operator new`/`delete`）来追踪 Native 堆分配，生成按调用栈聚合的分配统计。

在 TraceConfig 中启用 heapprofd 时，`data_sources.config.name` 从 Android 10 起就是 `android.heapprofd`：

```textproto
data_sources {
  config {
    name: "android.heapprofd"
    heapprofd_config {
      sampling_interval_bytes : 4096
      process_cmdline: "com.example.myapp"
      continuous_dump_config {
        dump_phase_ms : 0
        dump_interval_ms : 10000
      }
    }
  }
}
```

这些字段决定采样范围和导出节奏：
- `sampling_interval_bytes`：采样间隔，默认 4096 字节。意味着每分配 4096 字节采样一次。更大的值意味着更低的开销但更粗的粒度。
- `process_cmdline`：目标进程的包名。不设置时 heapprofd **不会**采样任何进程；如确实要 profile 所有符合条件的进程，必须显式设置 `all : true`（`HeapprofdConfig` proto 的独立字段）。全进程采样在 userdebug 设备上开销很高，可能导致 heapprofd 过载。
- `continuous_dump_config`：周期性导出快照的间隔。用于观察内存增长趋势。

在 Perfetto UI 中，Heap Profiling 数据显示为火焰图（Flamegraph）和分配详情表，可以直接看到哪些调用路径分配了最多的内存。

**权限边界**：heapprofd 在 `userdebug`/`eng` 构建上可采样大多数 App 和系统服务；在 `user` 构建上只能采样 manifest 中声明了 `android:profileable="true"` 或 `android:debuggable="true"` 的 App。未满足条件的目标进程会得到空 profile 或采样失败。官方文档见 [ perfetto.dev — HeapProfiler](https://perfetto.dev/docs/data-sources/native-heap-profiler)。

### Java Heap Sampling（Android 12+）

从 Android 12 开始，heapprofd 也支持 Java 堆的采样分析。这里要分清两层边界：`android.heapprofd` 这个数据源 Android 10+ 就有了，但 `heaps : "com.android.art"` 这类 Java heap selector 是 Android 12 才引入的字段。配置示例：

```textproto
data_sources {
  config {
    name: "android.heapprofd"
    heapprofd_config {
      sampling_interval_bytes : 4096
      heaps : "com.android.art"
      process_cmdline: "com.example.myapp"
    }
  }
}
```

Java Heap Sampling 和传统的 Java Heap Dump（如通过 `android.os.Debug.dumpHprofData(String)` 导出、`adb shell am dumpheap <pid>` 捕获、Android Studio Profiler 的 DumpJavaHeap，或本节后文的 `android.java_hprof` 数据源触发）是两种不同的分析手段。Sampling 记录的是每次分配发生时的调用栈，能看到"谁在频繁分配内存"；HeapDump 是某一时刻的对象存留快照，能看到"谁持有大量对象不释放"。两者互补，前者适合定位分配热点，后者适合定位泄漏源头。

### JavaHeapSnapshot（Android 11+）

如果目标是查看某一刻的 Java 对象保留关系，使用 `android.java_hprof` 数据源。它走 `JavaHprofConfig`，输出一次 Java heap 快照；数据形态不同于 `android.heapprofd` + `heaps : "com.android.art"` 的持续采样。

最小配置如下：

```textproto
data_sources {
  config {
    name: "android.java_hprof"
    java_hprof_config {
      process_cmdline: "com.example.myapp"
    }
  }
}

duration_ms : 10000
```

选择方式可以按问题类型确定：

- `android.heapprofd` + `heaps : "com.android.art"`：Android 12+，看 Java 分配热点和调用栈，适合回答“谁在频繁分配”。
- `android.java_hprof` + `java_hprof_config`：Android 11+，看快照里的对象持有关系，适合回答“谁还持有没有释放”。
- 快照会让目标进程产生停顿，适合复现窗口明确、可接受短暂停顿的泄漏分析；长时间趋势仍然用 heapprofd continuous dump。

源码锚点基于 AOSP `android-17.0.0_r1`：`external/perfetto/protos/perfetto/config/data_source_config.proto:208` 中 `perf_event_config = 111`，以及 `external/perfetto/protos/perfetto/config/profiling/java_hprof_config.proto`。

### CPU Callstack Sampling

Perfetto 还可以在 Trace 中集成 CPU 调用栈采样。这对分析 CPU 密集型瓶颈（如某段计算代码占用大量 CPU）非常有用。

**版本与设备要求**：`linux.perf` 数据源（即 `traced_perf` 守护进程）从 Android 12 (API 31) 起可用。源码证据：`external/perfetto/src/profiling/perf/perf_producer.cc:81` 定义 `kDataSourceName = "linux.perf"`，`traced_perf.cc` 完整实现；`external/perfetto/protos/perfetto/config/data_source_config.proto` 在 android-12.0.0_r1 与 android-17.0.0_r1 中都有 `perf_event_config` 配置入口。Android 17 已基于 `android-17.0.0_r1` 复核。运行条件取决于构建类型：`userdebug`/`eng` 构建可采样大多数进程；`user` 构建上目标 App 必须声明 `android:profileable="true"` 或 `android:debuggable="true"`，二者满足其一即可。非符合条件的目标进程会被跳过，trace 中无采样数据。官方 quickstart 见 [perfetto.dev — CPU Profiling](https://perfetto.dev/docs/quickstart/callstack-profiling)。

```textproto
data_sources {
  config {
    name: "linux.perf"
    perf_event_config {
      timebase {
        frequency : 100
        timestamp_clock : PERF_CLOCK_MONOTONIC
      }
      callstack_sampling {
        scope {
          target_cmdline: "com.example.myapp"
        }
      }
    }
  }
}
```

`frequency : 100` 表示每秒采样 100 次（10ms 间隔）。采样频率越高，结果越精确，但开销也越大。对于大多数分析场景，100-1000Hz 是合理的范围。

`scope.target_cmdline` 限定只对目标进程采样。如果不设 `scope`，`traced_perf` 会保留所有进程的样本，unwinder 队列容易过载，导致采样丢失和 `traced_perf` 内存暴涨。Android 12+ 的 `target_cmdline` 支持通配符（如 `com.example.*`）。

在 Perfetto UI 中，调用栈采样数据显示为火焰图，可以直观地看到 CPU 时间花在了哪些函数调用上。

### perf_event vs atrace：两条正交的追踪路径

理解 `linux.perf` 数据源，需要先认识它与 `linux.ftrace`（即 atrace）之间的本质差异。两者在数据源、overhead 和适用场景上完全不同：

| 维度 | `linux.ftrace`（atrace） | `linux.perf`（perf_event） |
|------|--------------------------|---------------------------|
| **底层机制** | ftrace ring buffer + `trace_marker` | `perf_event_open` syscall |
| **数据类型** | 注解事件（ATrace API 写入）、内核 ftrace 事件 | 硬件计数器采样（CPU cycles、cache-miss）、调用栈 |
| **调用栈采集** | 不支持 | 支持（DWARF unwind） |
| **硬件计数器** | 不支持 | 支持（PMU events） |
| **overhead** | 低（仅注解点） | 中（采样频率可调，需按目标设备实测） |

`linux.perf` 数据源通过 `traced_perf` 守护进程实现，它调用 Linux 内核的 `perf_event_open` syscall，为每个 CPU 创建一个 perf event group leader（由 `timebase` 定义），然后周期性采样。

**PerfEventConfig 字段说明**：

源码锚点在 `protos/perfetto/config/profiling/perf_event_config.proto`。Android 17 的 `PerfEventConfig` 已经把调用栈相关约束收进 `Callstack Sampling` 子消息，字段编号也和早期文章里常见的旧 schema 不同：

```protobuf
// 节选自 protos/perfetto/config/profiling/perf_event_config.proto
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

message CallstackSampling {
  optional Scope scope = 1;
  optional bool kernel_frames = 2;
  optional UnwindMode user_frames = 3;
}
```

- `timebase`：定义主采样事件和采样频率，常见写法是 `frequency : 100`。
- `callstack_sampling`：打开调用栈采样，并通过 `scope`、`kernel_frames`、`user_frames` 控制保留哪些进程、是否带内核栈、使用哪种 userspace unwinder。
- `followers`：在同一个采样点附带记录其他硬件计数器，适合同时看 cycles、instructions、cache-misses。
- `ring_buffer_pages` / `ring_buffer_read_period_ms`：控制 kernel 到 `traced_perf` 的 ringbuffer 容量和读取节奏。
- `max_enqueued_footprint_kb` / `max_daemon_memory_kb`：限制 unwinder 队列和 `traced_perf` 自身的内存占用，超限后会丢样或停止数据源。

旧资料里常见的顶层 `target_cmdline`、`target_pid`、`kernel_frames` 字段在 Android 17 的 proto 中已标为 deprecated。新配置优先写在 `callstack_sampling.scope` 里。

**PerfettoSQL 中的 `perf_sample` 表**：linux.perf 采样数据存入 `perf_sample` 表，可通过 Perfetto Trace Processor 查询：

| 列名 | 含义 |
|------|------|
| `id` | 采样唯一 ID |
| `ts` | 采样时间戳（ns） |
| `utid` | 被采样线程的 UTID |
| `cpu` | 采样时所在的 CPU |
| `cpu_mode` | "user" 或 "kernel" |
| `callsite_id` | 指向 `stack_profile_callsite` 表的外键（用于重建调用栈） |

通过 JOIN `stack_profile_callsite` 表和 `stack_profile_frame` 表可以重建完整的火焰图调用栈。

**simpleperf 与 Perfetto linux.perf 的关系**：simpleperf（`platform/system/extras/simpleperf/`）是 AOSP 自带的命令行 CPU profiling 工具，输出 `perf.data` 文件；Perfetto linux.perf 将采样数据直接写入 Perfetto trace 文件。两者都基于 `perf_event_open` syscall，核心差异在于输出格式和与 Perfetto UI 的集成程度。


### 同时收集多种数据的配置示例

一份 TraceConfig 可以同时开启多个数据源。这个示例同时收集 ftrace 事件、Heap Profiling 和 CPU 调用栈采样：

```textproto
buffers {
  size_kb : 131072   # 128MB，Heap Profiling 需要更大 buffer
  fill_policy : DISCARD
}

data_sources {
  config {
    name: "linux.ftrace"
    ftrace_config {
      ftrace_events : "sched/sched_switch"
      ftrace_events : "sched/sched_wakeup"
      ftrace_events : "power/cpu_frequency"
      atrace_categories : "am"
      atrace_categories : "wm"
      atrace_categories : "gfx"
      atrace_categories : "view"
      atrace_categories : "sched"
      atrace_apps : "com.example.myapp"
    }
  }
}

data_sources {
  config {
    name: "android.heapprofd"
    heapprofd_config {
      sampling_interval_bytes : 4096
      heaps : "com.android.art"
      process_cmdline: "com.example.myapp"
    }
  }
}

data_sources {
  config {
    name: "linux.perf"
    perf_event_config {
      timebase {
        frequency : 100
        timestamp_clock : PERF_CLOCK_MONOTONIC
      }
      callstack_sampling {
        scope {
          target_cmdline: "com.example.myapp"
        }
      }
    }
  }
}

duration_ms : 20000
```

注意这里的 heapprofd 配置默认按 Android 12+ 写法展示了 `heaps : "com.android.art"`。如果目标设备是 Android 10/11，需要删掉 `heaps` 字段，只保留 Native Heap Profiling。当同时开启 Heap Profiling 时，buffer 建议设为 128MB 或更大，因为调用栈数据的体积比单纯的 ftrace 事件大得多。

## 常见问题与误区

**"atrace categories 选得越多越好"**——不对。每个 category 都会持续产生额外事件，数据量会很快膨胀，buffer 也更容易被写满。关键数据被覆盖后，后面的分析就失去了定位依据。更稳妥的做法是根据分析目标选一组最小 category 组合，再按需要逐步加项，参考前面「按分析场景选择 Categories」的推荐表。

**"Trace 文件越大，信息越丰富"**——也不对。信息丰富度取决于数据源的选择和配置是否精准，而不是文件大小。一份 20MB 的精准 Trace 通常比一份 200MB 的冗余 Trace 更容易定位问题。

**"抓 Trace 影响性能，测出来的数据不准"**——要看配置。只开 `sched`、`gfx`、`view` 这类核心 category 时，Perfetto 通常适合日常定位问题；但 Heap Profiling、Long Trace 持续刷盘、高频 CPU 采样都会明显抬高开销。做严格 Benchmark 时，最好把“测性能”和“抓 Trace”拆成两轮，或者只保留最小数据源。

**"beginSection 忘了 endSection 没关系"**——这会导致 Trace 数据混乱。未配对的 section 会被 Perfetto 解析器丢弃，浪费了 instrumentation 的努力。强烈建议用 try/finally 包裹，确保 `endSection` 总是被调用。

## 与其他章节的关系

Trace 抓取是工具篇的入口。掌握抓取方式后，后续章节会基于这些 Trace 数据展开分析：

- §13.3（PerfettoView）会介绍如何在 Perfetto UI 中阅读和导航 Trace
- §13.5（主题分析）会深入各性能主题的 Trace 分析方法
- §13.6（线程 CPU 状态）专门讲解如何通过 `sched` category 分析线程的运行状态
- §14.1（Android Studio Profiler）提供了另一种可视化 Trace 的方式

如果已经抓到了一份 Trace 但不知道怎么看，直接跳到 §13.3 即可。

## 参考资料


- **FrameMetrics 与 Perfetto 集成**：FrameMetricsAPI 底层通过 FrameInfo 结构体收集数据，Perfetto 基于相同数据源。C++ 层 FrameMetricsObserver 有两种模式：不等待 presenttime（公共 API）和等待 presenttime（Perfetto 系统级分析）。FrameMetrics 是 Perfetto 数据的上层包装。详见相关 DeepResearch 调研。
1. Perfetto 官方文档 - Quickstart : AndroidTracing : https://perfetto.dev/docs/quickstart/android-tracing
2. Perfetto 官方文档 - TraceConfig 配置: https://perfetto.dev/docs/concepts/config
3. Perfetto 官方文档 - Native Heap Profiler : https://perfetto.dev/docs/data-sources/native-heap-profiler
4. Perfetto 官方文档 - TraceConfigProtoReference（PerfEventConfig）: https://perfetto.dev/docs/reference/trace-config-proto#perfeventconfig
5. Perfetto AOSP Proto - JavaHprofConfig : external/perfetto/protos/perfetto/config/profiling/java_hprof_config.proto
6. Android Developers - Trace API : https://developer.android.com/reference/android/os/Trace
7. AOSP Trace.java 源码: frameworks/base/core/java/android/os/Trace.java
8. 高爷博客 - Android Perfetto 系列 2：PerfettoTrace 抓取: https://www.androidperformance.com/2024/05/21/Android-Perfetto-02-how-to-get-perfetto/
9. 高爷博客 - Android Perfetto 系列 4：使用命令行在本地打开超大 Trace: https://www.androidperformance.com/2025/02/08/Android-Perfetto-04-Open-Big-Trace-With-Command-Line/
10. **PerfettoAPM 工具链演进（Android 14→16）**：Android 14 至 16 累计新增 15 个 datasource（Nextid 123→138），APM 端侧三件套（cpu_per_uid_config / app_wakelock_config / kernel_wakelocks_config），traced_probes readtracefs 权限升级，traced.rcperfetto_trace_on_boot 新增。详见 DeepResearch：[2026-06-09-android17-tracekit-perfetto-apm-toolchain.md](file:///Users/gracker/Library/Mobile%20Documents/iCloud~md~obsidian/Documents/Obsidian/DeepResearch/2026-06-09-android17-tracekit-perfetto-apm-toolchain.md)

以下为两个核心数据源的关键源码锚点，基于 AOSP `android-17.0.0_r1`（Android 17 / API 37）源码验证：

**linux.perf**（Android 12+）：
- 数据源名定义：`external/perfetto/src/profiling/perf/perf_producer.cc :81` — `kDataSourceName = "linux.perf"`
- 守护进程：`external/perfetto/src/profiling/perf/traced_perf.cc`
- SELinux 策略：`external/perfetto/traced_perf.rc` — 通过 `persist.traced_perf.enable` 和 `sys.init.perf_lsm_hooks` 控制启动
- 配置协议：`external/perfetto/protos/perfetto/config/profiling/perf_event_config.proto`

**android.surfaceflinger.frametimeline**（Android 12+）：
- 数据源名定义：`frameworks/native/services/surfaceflinger/Scheduler/FrameTimeline.h:656` — `kFrameTimelineDataSource = "android.surfaceflinger.frametimeline"`
- 注册入口：`frameworks/native/services/surfaceflinger/Scheduler/FrameTimeline.cpp:1351-1354` — `FrameTimeline::registerDataSource()`
- SF 集成点：`frameworks/native/services/surfaceflinger/SurfaceFlinger.cpp:820` — 调用 `mFrameTimeline->onBootFinished()`

两个数据源均已通过 AOSP `android-17.0.0_r1`（Android 17 / API 37）源码复核，上述行号和 API 口径与已公开源码一致。

<!-- AIW-源码调研-2026-06-06 -->

## 源码验证更新（2026-06-06）

基于深度源码调研，更新以下核心结论：

### 数据源标识符验证结果

**linux.perf** 源码位置修正：
- Android 12.0.0_r1: `external/perfetto/src/profiling/perf/perf_producer.cc :77`
- Android 16.0.0_r1: `external/perfetto/src/profiling/perf/perf_producer.cc:80`
- Android 15.0.0_r1: `external/perfetto/src/profiling/perf/perf_producer.cc:81`
- Android 17.0.0_r1: `external/perfetto/src/profiling/perf/perf_producer.cc:81`
- **修正原章节 "line81" 引用**：Android 17 主线使用 `android-17.0.0_r1` 的 line 81；Android 16 line 80 仅作历史对照。

**android.surfaceflinger.frametimeline** 源码位置（android-17.0.0_r1）：
- 数据源名定义：`frameworks/native/services/surfaceflinger/Scheduler/FrameTimeline.h:656`
- 注册入口：`frameworks/native/services/surfaceflinger/Scheduler/FrameTimeline.cpp:1351-1354`
- SF 集成点：`frameworks/native/services/surfaceflinger/SurfaceFlinger.cpp:820`

### Android 17 源码验证确认

本节源码锚点已基于 AOSP `android-17.0.0_r1`（Android 17 / API 37）通过 Gitiles 复核：
- `external/perfetto`：关键文件（`perf_producer.cc`、`traced_perf.cc`、`traced_perf.rc`、proto 定义）已核对
- `frameworks/native`：`FrameTimeline.{h,cpp}`、`SurfaceFlinger.cpp` 已核对
- `frameworks/base`：`android/os/Trace.java` 已核对
- 本章节所有 Android 17 正文结论均基于上述源码锚点

### FrameTimelineEvent 协议增强（Android 16）

在 `external/perfetto/protos/perfetto/trace/android/frame_timeline_event.proto` 中新增：
```
message ActualSurfaceFrameStart {
  optional JankSeverityType jank_severity_type = 12;  // field11 → 12
}

message ActualDisplayFrameStart {
  optional JankSeverityType jank_severity_type = 9;   // field8 → 9  
}
```

**性能影响**：Android 16 支持更精细的卡顿类型分级统计，`jank_severity_type` 字段为帧级分析提供统一的卡顿严重度标签。

### traced_perf.rc 权限简化

Android 17.0.0_r1 配置：
```rc
group nobody readproc readtracefs          # 新增 readtracefs
task_profiles ProcessCapacityHigh          # 新增任务配置
shared_kallsyms                           # 新增共享符号访问
```

**安全优化**：移除 `writepid` 依赖，改用 `readtracefs`，提升 LinuxPerf 权限模型安全性

### PerfEventConfig 协议扩展

协议从 Android 12 的 "Nextid : 19" 扩展到 Android 16 的 "Nextid : 21"：
```protobuf
FollowerEvent followers = 19;             // 新增：群组内事件跟随
repeated uint32 target_cpu = 20;          // 新增：精确 CPU 索引计数
```

**性能提升**：`target_cpu` 字段支持按 CPU 索引精确过滤 perf 事件，减少不相关事件的处理开销。

### Simpleperf 解耦验证

AOSP simpleperf (`system/extras/simpleperf/`) 与 Perfetto linux.perf 为不同实现：
- 使用相同底层 API：perf_event_open
- 输出格式不同：simpleperf → Android 自定义格式，linux.perf → Perfetto 格式
- 权限管理分离： traced_perf.rc vs simpleperf.rc



<!-- AIW-源码调研-2026-06-09 -->

## 源码验证更新（2026-06-09）

基于 Android 16.0.0_r4 一手源码保留 Android 14 → Android 16 Perfetto APM 工具链演进对照。Android 17 主线结论必须以上文 `android-17.0.0_r1` 复核结果为准；本小节只作为历史演进材料，不把 Android 16 锚点外推为 Android 17 事实。

### DataSourceConfig 协议版本演进

源码：`external/perfetto/protos/perfetto/config/data_source_config.proto`

| Android 版本 | tag | Nextid | 备注 |
|---|---|---|---|
| Android 14 | android-14.0.0_r1 | 123 | 基线（含 android.network_packets124、Android14QPR1+ android.sdk_sysprop_guard125）|
| Android 15 | android-15.0.0_r1 | 130 | 新增 android.protolog(127)、android.input.inputevent(128)、android.pixel.modem(130) |
| Android 16 | android-16.0.0_r4 | 138 | 新增 android.windowmanager(131)、org.chromium.system_metrics(132)、android.kernel_wakelocks(133)、gpu.renderstages(134)、org.chromium.histogram_samples(135)、android.app_wakelocks(136)、android.cpu_per_uid(137) |
| Android 17 | android-17.0.0_r1 | 141 | 新增 android.user_list(138)、android.inputmethod(139)、android.aflags(140) |

### Android 16 APM 三件套源码定位

- **`android.cpu_per_uid`**：`external/perfetto/protos/perfetto/config/android/cpu_per_uid_config.proto`（Copyright 2025）
  ```protobuf
  message CpuPerUidConfig {
    optional uint32 poll_ms = 1;
  }
  ```
- **`android.app_wakelocks`**：`external/perfetto/protos/perfetto/config/android/app_wakelock_config.proto`（Copyright 2025）
  ```protobuf
  message AppWakelocksConfig {
    optional int32 write_delay_ms = 1;     // 建议 5000ms
    optional int32 filter_duration_below_ms = 2;
    optional bool drop_owner_pid = 3;
  }
  ```
- **`android.kernel_wakelocks`**：`external/perfetto/protos/perfetto/config/android/kernel_wakelocks_config.proto`

### traced_probes 权限模型升级

源码：`external/perfetto/traced_perf.rc`（android-16.0.0_r4）

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

`traced_probes.rc`（同版本）：

```rc
service traced_probes /system/bin/traced_probes
    class late_start
    disabled
    user nobody
    group nobody readproc log readtracefs
    task_profiles ProcessCapacityHigh
    onrestart exec_background -nobody shell -- /system/bin/traced_probes --cleanup-after-crash
    file /dev/kmsg w
    capabilities DAC_READ_SEARCH SYS_NICE
    shared_kallsyms
```

`readtracefs` group + `DAC_READ_SEARCH` capability 替代旧版 `writepid`，LinuxPerf / ftrace 路径只读。

### android.input.inputevent 数据源

源码：`external/perfetto/protos/perfetto/config/android/android_input_event_config.proto`（Copyright 2024）

- TraceMode: TRACE_MODE_TRACE_ALL（仅 userdebug/eng）/ TRACE_MODE_USE_RULES
- TraceLevel : NONE / REDACTED（抹去坐标+keycode）/ COMPLETE
- TraceRule 支持 match_all_packages / match_any_packages / match_secure / match_ime_connection_active
- `trace_dispatcher_input_events` + `trace_dispatcher_window_dispatch` 双开关可独立启用

### FtraceConfig atrace 集成新增

源码：`external/perfetto/protos/perfetto/config/ftrace/ftrace_config.proto`（android-16.0.0_r4，Nextid : 36）

```protobuf
repeated string atrace_categories_prefer_sdk = 28;
optional bool atrace_userspace_only = 34;   // Perfetto v52+
```

`atrace_userspace_only = true` 关闭 vendor-specific ftrace 事件注入；`atrace_categories_prefer_sdk` 让混合路径切到纯 Perfetto SDK track_event。

### ProducerIPC 零拷贝路径

源码：`external/perfetto/src/tracing/ipc/producer/producer_ipc_client_impl.h`（android-16.0.0_r4）

```cpp
SharedMemoryArbiter* MaybeSharedMemoryArbiter() override;
bool IsShmemProvidedByProducer() const override;
void OnConnectionInitialized(bool connection_succeeded,
                             bool using_shmem_provided_by_producer,
                             bool direct_smb_patching_supported,
                             bool use_shmem_emulation);
```

`direct_smb_patching_supported` 决定 producer→traced 是否走 SMB 直接 patch，APM SDK 在 Android 16+ 可借此减少一次数据拷贝。

### Android 17 验证结论

本节源码锚点已基于 AOSP `android-17.0.0_r1`（Android 17 / API 37）通过 Gitiles 复核，关键文件和行号与正文一致。`external/perfetto`、`frameworks/native`、`frameworks/base` 下的核心源码路径均可公开访问。