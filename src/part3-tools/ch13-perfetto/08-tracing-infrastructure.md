---

title: "Android Tracing 基础设施:atrace、ftrace 与 Perfetto 数据采集原理"
chapter: 13.8
section: 13.8
status: finalized
pipeline_stage: ready-to-publish
task6_state: reviewed
applicable_versions: "Android 8.0 (API 26) - Android 17 (API 37)"
tags: [tracing, atrace, ftrace, tracepoint, perfetto, kernel, observability]
confidence: "medium"
sources:
- type: reference
  path: intake/research-feeds/2026-04-07-19-android17-ebpf-sched-ext-uprobestats-observability.md
- type: official
  path: https://perfetto.dev/docs/concepts/buffers
- type: kernel
  path: https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/Documentation/trace/ftrace.rst
- type: aosp
  path: https://android.googlesource.com/platform/external/perfetto/+/refs/tags/android-17.0.0_r1/src/traced/probes/ftrace/tracefs.cc
- type: kernel
  path: https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/drivers/android/binder_trace.h
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/cmds/atrace/atrace.cpp
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/jni/android_os_Trace.cpp
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/libs/tracing_perfetto/tracing_perfetto.cpp
- type: aosp
  path: https://android.googlesource.com/platform/system/core/+/refs/tags/android-17.0.0_r1/libcutils/trace-dev.cpp
- type: aosp
  path: https://android.googlesource.com/platform/external/perfetto/+/refs/tags/android-17.0.0_r1/perfetto.rc
- type: official
  path: https://perfetto.dev/docs/concepts/config
- type: official
  path: https://perfetto.dev/docs/reference/traced_probes
- type: official
  path: https://developer.android.com/reference/android/os/Trace
- type: kernel
  path: https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/samples/trace_events/trace-events-sample.h
- type: official
  path: https://perfetto.dev/docs/case-studies/android-boot-tracing
- type: aosp
  path: https://android.googlesource.com/platform/external/perfetto/+/refs/tags/android-17.0.0_r1/src/traced/probes/ftrace/ftrace_controller.cc
- type: aosp
  path: https://android.googlesource.com/platform/external/perfetto/+/refs/tags/android-17.0.0_r1/src/traced/probes/ftrace/ftrace_config_muxer.cc
last_verified: "2026-06-29"
last_verified_against: "AOSP android-17.0.0_r1, frameworks/base/core/jni/android_os_Trace.cpp, frameworks/native/libs/tracing_perfetto/tracing_perfetto.cpp, frameworks/native/cmds/atrace/atrace.cpp, system/core/libcutils/{trace-dev.cpp,include/cutils/trace.h}, external/perfetto/src/traced/probes/ftrace/{ftrace_controller.cc,cpu_reader.cc,tracefs.cc,tracefs.h}, external/perfetto/perfetto.rc, external/perfetto/src/profiling/perf/perf_producer.cc, frameworks/native/services/surfaceflinger/Scheduler/FrameTimeline.{h,cpp}"
related_chapters: [13.1, 13.2, 13.9, 14.23, 1.5]
task2b_state: "fixed"
task9_state: "reviewed"
---



# 13.8 Android Tracing 基础设施：atrace、ftrace 与 Perfetto 数据采集原理

Perfetto 界面里的调度切片、应用自定义区间和计数器来自多条采集路径。某条轨道没有数据时，只查 SQL 往往定位不到原因：事件可能没有在 tracefs 中启用，也可能已经写入内核缓冲区却来不及读取，还可能在 Perfetto 的共享内存或中央缓冲区中丢失。

平台锚点是 Android 17 / API 37 / `android-17.0.0_r1`，内核锚点是 `android17-6.18-2026-06_r6`。阅读目标是分清每一层的职责，并能沿着数据实际经过的路径排查问题。

## 三层缓冲区

系统追踪讨论中的“缓冲区”至少有三种，混用名称会把丢数原因引向错误位置。

| 所在层 | 数据结构 | 写入者与读取者 | 常见丢数表现 |
|---|---|---|---|
| Linux 内核 | ftrace 的每 CPU 环形缓冲区 | tracepoint 或 `trace_marker` 写入，`traced_probes` 读取 | `ftrace_cpu_overrun_delta` 非零 |
| Perfetto 数据生产者 | 数据生产者（`Producer`）与 `traced` 之间的共享内存 | `traced_probes`、应用 SDK 等数据生产者写入，`traced` 接收提交 | `traced_buf_trace_writer_packet_loss` 非零 |
| Perfetto 服务 | `TraceConfig.buffers` 定义的中央缓冲区 | `traced` 汇集各数据源，数据使用方（`Consumer`）读取或写文件 | `chunks_overwritten` 或 `chunks_discarded` 非零 |

`ftrace_config.buffer_size_kb` 调整第一层，而且单位是“每个 CPU 的 KiB”。`TraceConfig.buffers.size_kb` 调整第三层。二者名字相近，控制的内存和失效方式完全不同。Perfetto 的[缓冲区说明](https://perfetto.dev/docs/concepts/buffers)给出了三类丢数统计及其语义。

## ftrace：事件源与函数 tracer

ftrace 同时包含事件追踪、函数追踪、环形缓冲区和 tracefs 控制接口。把它只理解成“函数追踪器”会漏掉 Android 性能分析最常用的 tracepoint 路径。

### “三种模式”的准确边界

许多教程把 `function`、`function_graph`、tracepoint 称作 ftrace 的三种模式。这个说法便于入门，但内核接口的分类更精确：

- `function` 是写入 `current_tracer` 的 tracer，记录经过筛选的函数入口。动态 ftrace 会在未启用时把可追踪调用点修补为快速路径；具体指令和编译选项取决于体系结构及内核构建配置。
- `function_graph` 也是 tracer。它在函数入口信息之外记录返回关系，因而能还原调用层级和耗时。过滤范围过宽时，事件量和扰动都会快速上升。
- tracepoint 属于事件源。启用 `sched/sched_switch` 等事件时，`current_tracer` 通常仍是 `nop`，事件通过 `events/<group>/<name>/enable` 独立控制。

因此，这里的“三种模式”指三种常见观测形态，不代表 tracepoint 是第三个 `current_tracer` 值。Android 日常系统性能采集应优先选静态 tracepoint；函数 tracer 适合缩小到明确函数集合后的内核调试。内核锚点的 [`ftrace.rst`](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/Documentation/trace/ftrace.rst)记录了 tracer、动态 ftrace 和过滤接口的定义。

tracepoint 通过 `TRACE_EVENT` 等宏在源码中声明字段。未启用时会经过静态分支快速路径，开销很小但不能写成绝对零；启用后还要分配事件、复制字段并写入当前 CPU 的环形缓冲区。事件频率、字段长度和消费者读取速度共同决定实际成本。

### tracefs 暴露了哪些控制点

Android 17 设备通常把 tracefs 挂载在 `/sys/kernel/tracing/`。`/sys/kernel/debug/tracing/` 是 libcutils 仍保留的兼容回退位置。排查采集问题时，以下文件最有用：

| tracefs 节点 | 含义 |
|---|---|
| `available_events` | 当前内核及已加载模块实际注册的事件 |
| `events/<group>/<name>/format` | 事件编号、字段布局和文本打印格式 |
| `events/<group>/<name>/enable` | 单事件启停开关 |
| `set_event` | 批量启停事件的兼容接口 |
| `available_tracers` / `current_tracer` | 可用 tracer 与当前 tracer |
| `set_ftrace_filter` / `set_graph_function` | 函数与函数图过滤范围 |
| `buffer_size_kb` | 每 CPU 内核环形缓冲区大小 |
| `per_cpu/cpu<N>/trace_pipe_raw` | 单 CPU 二进制事件流 |
| `per_cpu/cpu<N>/stats` | 单 CPU 缓冲区覆盖、丢弃和读取统计 |
| `tracing_on` | 当前 tracefs 实例是否记录事件 |

Android 17 的 Perfetto [`Tracefs::EnableEvent()`](https://android.googlesource.com/platform/external/perfetto/+/refs/tags/android-17.0.0_r1/src/traced/probes/ftrace/tracefs.cc)先向单事件 `enable` 文件写 `1`；写入失败后才把 `group:name` 追加到 `set_event`。停用过程对称，回退内容是 `!group:name`。所以“Perfetto 会把每个事件写入 `set_event`”不符合当前源码。

tracefs 还支持 `instances/<name>/` 下的命名实例。Perfetto 的 `FtraceController` 可以按 `FtraceConfig.instance_name` 创建并读取次级实例。次级实例适合隔离内核事件；Android 的 atrace category 仍受主实例和系统属性约束，不应假设它能随次级实例完整隔离。

### Android 17 常用事件

事件名必须以设备的 `available_events` 为准。GKI、厂商内核配置和驱动实现都会改变可用集合。

| 分析对象 | Android 17 锚点中的代表事件 | 说明 |
|---|---|---|
| CPU 调度 | `sched/sched_switch`、`sched/sched_waking`、`sched/sched_wakeup`、`sched/sched_wakeup_new` | 生成 `sched`、`thread_state` 等派生数据 |
| CPU 频率与空闲 | `power/cpu_frequency`、`power/cpu_idle`、可选的 `power/cpu_frequency_limits` | 频率限制事件是否存在仍需查设备 |
| Binder | `binder/binder_transaction`、`binder/binder_transaction_received`、`binder/binder_set_priority` | Android 17 的 Binder 追踪头文件没有旧资料常列的全局 `binder_lock` 事件 |
| 存储 | `block/*`、`f2fs/*`、`ext4/*` 中设备支持的事件 | 不同内核版本的 block 事件集合变化较多 |
| 中断 | `irq/*`、`ipi/*` | 高频事件应按问题范围选择 |
| 厂商驱动 | GPU、显示、UFS 等驱动自定义组 | 不能把某款设备的事件名写成 Android 通用接口 |

Binder 事件可以直接对照内核锚点的 [`drivers/android/binder_trace.h`](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/drivers/android/binder_trace.h)。atrace 的事件组合则应对照平台锚点的 [`cmds/atrace/atrace.cpp`](https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/cmds/atrace/atrace.cpp)。

Perfetto 会把可识别的高价值事件转换成领域表。例如，调度事件参与构造 `sched` 和 `thread_state`，频率事件进入计数器相关表。`ftrace_event` 保留原始事件索引及 `arg_set_id`，适合核对采集和查看尚无专用解析器的事件。正式分析应优先使用语义更稳定的派生表。

## atrace category 不是事件别名

`atrace` category 是 Android 定义的一组开关。一个 category 可以控制用户空间 tag 位、内核事件，也可以同时控制两者：

- `view`、`wm`、`am` 等 category 主要对应 `ATRACE_TAG_*`，使相应进程允许写用户空间追踪事件。
- `sched` 没有用户空间 tag 位，主要启用一组调度、任务和可选的内存相关 tracepoint。
- `gfx` 启用 `ATRACE_TAG_GRAPHICS`，还可附带 `gpu_mem/gpu_mem_total` 等内核事件。
- `freq` 和 `idle` 是两个独立 category，分别覆盖频率与 CPU idle 事件。
- 厂商可以从 `/vendor/etc/atrace/atrace_categories.txt` 增加设备专用 category 和 sysfs 开关。

Perfetto 的 `linux.ftrace` 数据源同时提供两种选择方式：

- `ftrace_events` 精确指定 `group/event`，适合已知问题和可复现实验。
- `atrace_categories` 复用 Android category，适合需要用户空间 tag 与配套内核事件的系统分析。

两者可以放在同一份配置中。category 展开后仍要检查 Trace 中的 `unknown_ftrace_events`、`failed_ftrace_events` 和 atrace 错误；category 名称存在，并不能保证其中每个可选事件都存在于当前设备。

## Android 17 用户空间事件有两条路径

“`android.os.Trace` 一定写 `trace_marker`”只适用于较早实现。Android 17 的 Java Framework 路径已经具备 Perfetto TrackEvent 与 atrace 兼容路径的选择逻辑。

### `android.os.Trace` 的当前路径

Android 17 的 [`android_os_Trace.cpp`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/jni/android_os_Trace.cpp)把 `nativeTraceBegin()`、`nativeTraceEnd()`、异步事件和计数器转交给 `tracing_perfetto::*`。随后 [`tracing_perfetto.cpp`](https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/libs/tracing_perfetto/tracing_perfetto.cpp)按 category 状态选择：

- atrace tag 未启用、对应 Perfetto category 已启用：写 Perfetto TrackEvent。
- atrace tag 已启用、Perfetto category 未启用：调用 `atrace_begin()` 等 libcutils 接口。
- 两边都启用：`debug.atrace.prefer_sdk` 的 category 位决定是否优先走 SDK。该属性由 `atrace --prefer_sdk` 配合 Perfetto 的 `atrace_categories_prefer_sdk` 管理，用于处理并发会话的兼容要求。
- 两边都未启用：调用直接返回，不产生事件。

Android 14 及更早分支中的 Java Trace 主要走 libcutils atrace。Android 15 开始接入 `tracing_perfetto`，后续版本补上并发 atrace 会话的优先级处理。分析跨版本 Trace 时，应把事件的采集路径与目标系统分支对应起来。

### libcutils `ATRACE_*` 仍写 `trace_marker`

使用 `system/core/libcutils/include/cutils/trace.h` 中经典 `ATRACE_BEGIN()`、`ATRACE_END()`、`ATRACE_INT()` 的 native 代码，仍由 [`trace-dev.cpp`](https://android.googlesource.com/platform/system/core/+/refs/tags/android-17.0.0_r1/libcutils/trace-dev.cpp)打开 `/sys/kernel/tracing/trace_marker`，失败时再尝试 debugfs 路径。

Android 17 的 libcutils 生成以下常用消息：

| API | 写入格式 |
|---|---|
| 同步区间开始 | `B\|<pid>\|<name>` |
| 同步区间结束 | `E\|<pid>` |
| 异步区间开始/结束 | `S\|<pid>\|<name>\|<cookie>` / `F\|<pid>\|<name>\|<cookie>` |
| 即时事件 | `I\|<pid>\|<name>` |
| 计数器 | `C\|<pid>\|<name>\|<value>` |

这些字符串进入 ftrace 的 `print` 事件，再由 Perfetto 解析成时间片、即时事件或计数器。事件名称包含的换行和竖线会被清理，libcutils 的单条消息缓冲区上限是 1024 字节；应用公开 API 还对区间名称施加更短的限制。

两条路径汇总后，Android 17 的数据流如下。图中的 Perfetto TrackEvent 不经过内核 ftrace 缓冲区。

```text
内核 tracepoint ──────────────────────→ 每 CPU ftrace 缓冲区 ─┐
                                                              │
libcutils ATRACE_* → trace_marker → ftrace/print ─────────────┤
                                                              ├→ traced_probes
Java android.os.Trace ─┬→ atrace 兼容路径 → trace_marker ─────┘       │
                       │                                             │
                       └→ Perfetto TrackEvent Producer ───────────────┤
                                                                     ↓
Consumer → TraceConfig → traced ← Producer 共享内存提交 → 中央缓冲区 → Trace 文件
```

图中 `traced` 接收数据使用方的配置并协调数据生产者；`traced_probes` 是拥有 `linux.ftrace` 等系统数据源的数据生产者。二者不处在同一个职责层级。

## `traced` 与 `traced_probes` 如何协作

Android 17 的 [`perfetto.rc`](https://android.googlesource.com/platform/external/perfetto/+/refs/tags/android-17.0.0_r1/perfetto.rc)定义了两个独立服务：

- `traced` 提供 Producer 套接字和 Consumer 套接字，管理会话、中央缓冲区、数据源启停和输出读取。
- `traced_probes` 以受限权限访问 tracefs、`/proc` 等系统接口，注册 `linux.ftrace`、`linux.process_stats` 等数据源。

Perfetto CLI、Android Studio 或 `TracingManager` 充当数据使用方。它们把 `TraceConfig` 交给 `traced`。`traced` 按数据源名称找到数据生产者，并把对应的 `DataSourceConfig` 发给它。官方的 [Trace 配置说明](https://perfetto.dev/docs/concepts/config)和 [`traced_probes` 参考](https://perfetto.dev/docs/reference/traced_probes)描述了这套协议边界。

### `linux.ftrace` 的采集过程

Android 17 源码中的实际步骤可以归纳为：

1. `FtraceConfigMuxer` 合并同一 tracefs 实例上的活跃会话配置，计算事件并集。
2. `Tracefs` 启用事件，配置时钟、缓冲区和受支持的选项。
3. `FtraceController` 为每个 CPU 打开 `per_cpu/cpu<N>/trace_pipe_raw`。
4. `CpuReader` 读取二进制页，按运行时读取到的事件格式解码，并写成 Perfetto protobuf 数据包。
5. `traced_probes` 通过 Producer 共享内存向 `traced` 提交数据包。
6. 会话退出时，muxer 只停用已不再被任何会话需要的事件；全部配置移除后才清理该实例的公共状态。

并发会话使若干参数无法按单个配置独占。`buffer_size_kb` 和 `drain_period_ms` 的 proto 注释都明确写着并发时不保证请求值。函数图还会修改 `current_tracer`，存在并发配置不兼容时，Perfetto 会拒绝启用或要求独占会话。

### 一份可审计的采集配置

下面的配置只演示字段归属和一组常见事件，不把时长、中央缓冲区大小当作通用推荐值。`ftrace_config.buffer_size_kb` 与 `drain_period_ms` 故意留空，让 Android 17 的 Perfetto 选择默认值。

```protobuf
duration_ms: 10000

buffers {
  size_kb: 32768
  fill_policy: RING_BUFFER
}

data_sources {
  config {
    name: "linux.ftrace"
    target_buffer: 0
    ftrace_config {
      ftrace_events: "sched/sched_switch"
      ftrace_events: "sched/sched_waking"
      ftrace_events: "power/cpu_frequency"
      ftrace_events: "power/cpu_idle"

      atrace_categories: "gfx"
      atrace_categories: "view"
      atrace_apps: "com.example.app"
    }
  }
}
```

这里的 32768 KiB 是 Perfetto 中央缓冲区，10 秒是示例采集窗口。真实值应由事件速率、复现窗口、设备内存和丢数统计共同决定。配置中列出的可选事件若不在 `available_events`，应从目标设备配置中删除。

Android 17 的 `FtraceConfigMuxer` 在调用方未指定内核缓冲区时，物理内存低于约 7 GiB 的设备选择每 CPU 2 MiB，达到或高于该阈值时选择每 CPU 8 MiB。这个分支是当前源码默认值，不能替代设备实测。`drain_period_ms` 未设置时，控制器使用 100 ms 历史周期；所有实例都使用缓冲区水位轮询时，保底周期放宽到 1000 ms。内核 6.18 支持 `drain_buffer_percent` 所依赖的 6.9+ 水位轮询能力，常规配置仍可保持未设置状态。

## App、Framework、内核三层自定义入口

入口要和要回答的问题相匹配。应用业务区间用 `android.os.Trace` 已经足够；平台原生 C/C++ 热路径可使用有 category 的 ATRACE；需要观察内核状态转换时才添加 tracepoint。

### App：同步区间、异步区间与计数器

下面是应用方法体内的代码，用于标记一次数据库读取。`finally` 保证异常路径也能闭合区间。

```java
Trace.beginSection("UserRepository.load");
try {
    loadUserDataFromDatabase();
} finally {
    Trace.endSection();
}
```

同步区间必须在同一线程正确嵌套。它会显示在调用线程的轨道上，不局限于主线程。API 29 及以上可以用 `beginAsyncSection(name, cookie)` 与 `endAsyncSection(name, cookie)` 表示跨线程工作；同名并发操作需要不同 `cookie`。持续数值适合 `setCounter()`，不要用大量零时长区间模拟计数器。

动态拼接区间名称会产生字符串分配，还可能把用户数据写进 Trace。只有名称构造确有成本时，才用 `Trace.isEnabled()` 避免未采集状态下的临时对象。公开 API 的同线程配对、异步 `cookie` 和名称限制可查 [`android.os.Trace`](https://developer.android.com/reference/android/os/Trace)。

### Framework 原生层：保留 category 语义

下面是平台函数中的示意节选，省略头文件和类声明。它标记原生函数范围，并在一个较小子区间上补充语义。

```cpp
void RenderEngine::drawLayers() {
    ATRACE_CALL();

    ATRACE_BEGIN("RenderEngine.prepareLayers");
    prepareLayers();
    ATRACE_END();

    submit();
}
```

`ATRACE_CALL()` 通过 RAII 在作用域退出时闭合。手工 `ATRACE_BEGIN()` / `ATRACE_END()` 没有这种保护，提前返回和错误分支都必须闭合。平台代码还要在包含 `trace.h` 前选择正确的 `ATRACE_TAG`；否则 category 配置和事件可见性会偏离设计意图。

对极高频路径，区间边界应围住能回答问题的工作单元。把每次循环迭代、每个像素或每个小对象操作都写入系统 Trace，会同时增加目标线程成本和事件带宽。

### 内核：在 6.18 锚点添加静态 tracepoint

下面的头文件展示 Android 17 内核锚点可用的最小声明形式。`define_trace.h` 必须位于 include guard 外，`__assign_str(name)` 使用 Linux 6.18 的单参数形式。

```c
/* include/trace/events/my_custom.h */
#undef TRACE_SYSTEM
#define TRACE_SYSTEM my_custom

#if !defined(_TRACE_MY_CUSTOM_H) || defined(TRACE_HEADER_MULTI_READ)
#define _TRACE_MY_CUSTOM_H

#include <linux/tracepoint.h>

TRACE_EVENT(my_event,
    TP_PROTO(int value, const char *name),
    TP_ARGS(value, name),
    TP_STRUCT__entry(
        __field(int, value)
        __string(name, name)
    ),
    TP_fast_assign(
        __entry->value = value;
        __assign_str(name);
    ),
    TP_printk("value=%d name=%s",
              __entry->value, __get_str(name))
);

#endif /* _TRACE_MY_CUSTOM_H */

#include <trace/define_trace.h>
```

`__string(name, name)` 保存源表达式，`__assign_str(name)` 在快速赋值阶段复制它。旧内核使用过双参数形式，移植代码时要按目标分支的 `trace_events.h` 和样例修改，不能把旧写法带进 6.18。锚点内核的 [`trace-events-sample.h`](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/samples/trace_events/trace-events-sample.h)提供了各字段宏的当前说明。

还需要在唯一一个编译单元中实例化定义。下面这段代码只负责生成 tracepoint 符号。

```c
#define CREATE_TRACE_POINTS
#include <trace/events/my_custom.h>
```

业务代码随后调用生成的 helper。下面的调用会产生 `my_custom:my_event`。

```c
#include <trace/events/my_custom.h>

static void update_state(int value, const char *name)
{
    trace_my_event(value, name);
}
```

模块或内核编译完成后，事件应出现在 `events/my_custom/my_event/` 和 `available_events` 中。Perfetto 配置使用斜杠形式 `my_custom/my_event`。只有事件成功注册、当前构建允许 `traced_probes` 访问且配置成功启用，Trace 中才会出现数据。

### 从 `ftrace_event` 核对自定义事件

新增事件还没有专用 Trace Processor 解析器时，可以先列出原始事件名称。下面的查询也能发现配置名与实际 `ftrace_event.name` 的差异。

```sql
SELECT
  name,
  COUNT(*) AS event_count
FROM ftrace_event
GROUP BY name
ORDER BY event_count DESC;
```

结果中的名称来自 Perfetto 实际写入的事件描述，不能用 `group_event` 之类的拼接规则猜测。确认名称后，再用 `arg_set_id` 展开字段。下面的查询保留 CPU、线程和全部参数。

```sql
SELECT
  f.ts,
  f.cpu,
  f.utid,
  f.name,
  a.key,
  a.display_value
FROM ftrace_event AS f
LEFT JOIN args AS a USING (arg_set_id)
WHERE f.name = 'my_event'
ORDER BY f.ts, a.key;
```

若该事件会长期参与统计，应在 Perfetto 中增加专用 protobuf 与解析器，或在项目 SQL 库中封装语义视图。原始表适合验证采集，像调度状态、CPU 频率这类已有领域模型的数据仍应使用派生表。

## 开销不能套固定百分比

系统追踪对工作负载的影响由事件命中频率、每条事件的字段量、字符串构造、内核缓冲区写入、Producer 解析和读取周期共同决定。给 `function tracer`、tracepoint 或 uprobe 写一个跨设备通用的纳秒数或百分比，会掩盖最有影响的变量。

| 机制 | 未启用时仍存在的工作 | 启用后的主要新增工作 | 使用建议 |
|---|---|---|---|
| 静态 tracepoint | 静态分支快速路径 | 字段计算、复制、每 CPU 缓冲区写入 | 系统性能采集的常用入口 |
| `function` / `function_graph` | 动态 ftrace 快速路径 | 大量函数事件、返回关系和过滤判断 | 只在可控构建上缩小函数集合 |
| libcutils ATRACE | tag 状态检查 | 名称处理、系统调用写 `trace_marker`、ftrace 记录 | 避开高频细粒度循环 |
| Perfetto TrackEvent | category 状态检查 | 数据包构造、共享内存提交 | 使用 category 与轨道模型控制范围 |
| eBPF kprobe/uprobe | 探针未挂载时无对应程序执行 | BPF 程序、map 更新、可选环形缓冲区输出 | 根据命中率和程序内容实测 |

开销评估应采用同一设备、同一构建、同一温控条件和同一输入脚本，交替运行无采集与有采集样本。比较目标指标之外，还要记录采集进程 CPU、Trace 文件速率和丢数统计。只跑一轮 A/B 无法区分追踪扰动与温度、频率、后台任务造成的波动。

## 丢数诊断与配置调整

完成采集后，先运行一条统一查询。新版 Trace Processor 会把当前会话内的 ftrace 计数增量放在 `*_delta`；其中 `ftrace_cpu_overrun_delta` 可能仍标为 `info`，只筛 `data_loss` 会漏掉它。

```sql
SELECT
  name,
  idx,
  severity,
  source,
  value
FROM stats
WHERE value != 0
  AND (
    severity IN ('data_loss', 'error')
    OR name IN (
      'ftrace_cpu_overrun_delta',
      'ftrace_cpu_commit_overrun_delta',
      'ftrace_cpu_dropped_events_delta'
    )
  )
ORDER BY name, idx;
```

查询有结果时，要按统计项所在层处理：

- `ftrace_cpu_overrun_delta` 非零：内核旧事件在 `traced_probes` 读取前被覆盖。减少高频事件通常比盲目扩容更有效；确认事件集已经精简后，再评估每 CPU `buffer_size_kb` 或读取策略。
- `ftrace_cpu_commit_overrun_delta` 非零：内核记录提交发生异常，需检查缓冲区大小、极端中断负载和内核实现。
- `ftrace_cpu_dropped_events_delta` 非零：关闭覆盖模式后，缓冲区已满导致新事件被拒绝。
- `traced_buf_trace_writer_packet_loss` 非零：Producer 共享内存提交发生丢包，应检查数据生产者是否被阻塞、数据包是否过大及系统调度压力。
- `traced_buf_chunks_overwritten` 非零：中央 `RING_BUFFER` 已回绕。它可能符合“只保留故障前最近窗口”的设计，也可能覆盖了分析所需的开头。
- `traced_buf_chunks_discarded` 非零：中央 `DISCARD` 缓冲区已满，后续数据被丢弃。

`buffer_size_kb`、`drain_period_ms`、`drain_buffer_percent` 都会改变内存、唤醒与丢数之间的权衡。修改一个参数后应重新运行同一复现并复查 `stats`，避免把“文件变大”当成“数据完整”。

## 生产环境抓取约束

生产采集要把诊断价值、性能扰动和数据敏感性一起纳入配置。

- 按问题选择事件。调度延迟需要 `sched_switch` 和唤醒事件，未必需要所有 Binder、I/O、IRQ 和驱动事件。
- 采集窗口围绕可识别触发点设置。固定宣称某个秒数适合所有问题没有依据；低频故障可以用长时环形缓冲区配合触发器保留故障前窗口。
- 自定义名称使用稳定、低基数的操作名。用户输入、URL、账号、消息内容等数据不应进入 Trace。
- 高频路径先计算事件速率，再决定采样、聚合或缩小区间。源码里一行 Trace 调用并不等于一次固定成本。
- 区分 `user`、`userdebug` 和 `eng` 构建权限。函数图、内核符号和部分系统数据源在 `user` 构建上受 SELinux、系统属性或 Perfetto 保护规则限制。
- 每份性能结论都保留 TraceConfig、设备构建号、内核版本、复现步骤和丢数查询结果。缺少这些信息时，后续很难判断差异来自代码还是采集条件。

## eBPF 与静态 tracepoint 的分工

静态 tracepoint 适合长期保留的内核语义事件。字段布局随内核演进，但事件位置由维护者在源码中选择，通常比函数符号更稳定。eBPF 可以附着到现有 tracepoint，在内核侧过滤或聚合；也可以用 kprobe、kretprobe、uprobe 和 uretprobe 观察尚无静态事件的函数。

kprobe 与 uprobe 依赖函数符号、内联、优化和二进制版本。平台升级后，探针位置与参数解释必须重新验证。BPF 程序若只在 map 中计数，与每次命中都向用户空间输出事件的成本差异很大。因此，静态 tracepoint、eBPF 聚合和 Perfetto 全量时间线应按问题组合，不能用一个固定开销表决定取舍。§14.23 会继续讨论 Android 动态探针的权限、版本边界和验证方法。

## Android 17 启动期 Trace

Android 17 的标准 Perfetto 启动期 Trace 由 `perfetto.rc` 中的 `perfetto_trace_on_boot` 服务执行。它等待持久属性可用、`persist.traced.enable=1` 且 `traced` 已监听 Consumer 套接字，然后读取：

- 配置：`/data/misc/perfetto-configs/boottrace.pbtxt`
- 输出：`/data/misc/perfetto-traces/boottrace.perfetto-trace`
- 一次性触发属性：`persist.debug.perfetto.boottrace=1`

在允许 `root` 的调试设备上，可以用下面的命令准备下一次启动采集。

```bash
adb root
adb push boottrace.pbtxt /data/misc/perfetto-configs/boottrace.pbtxt
adb shell setprop persist.debug.perfetto.boottrace 1
adb reboot

# 设备完成目标启动阶段后执行
adb pull /data/misc/perfetto-traces/boottrace.perfetto-trace
```

该属性会在服务启动时被清空，避免每次重启都重复抓取。服务需要等待 `/data`、持久属性和 `traced`，所以它不能覆盖这些条件满足前的全部内核和早期用户空间事件。需要更早窗口时，应使用内核启动参数预配置 ftrace，再通过 `preserve_ftrace_buffer` 接入 Perfetto，或使用设备启动链提供的早期追踪方案。官方的 [Android boot tracing 案例](https://perfetto.dev/docs/case-studies/android-boot-tracing)给出了配置与触发流程。

旧版本 Android 还存在 atrace boot trace 路径。它以 category 配置内核和用户空间 atrace 状态，输出流程与 Perfetto boot trace 不同。Android 17 新配置应以 `perfetto_trace_on_boot` 为准，阅读历史故障记录时仍需识别旧路径。

## 排查顺序

遇到“某条轨道没有数据”，按数据路径检查会更快：

1. 在目标设备的 `available_events` 中确认事件存在。
2. 确认配置使用正确的 `group/event`、atrace category 和目标应用名。
3. 检查 Trace 的 `unknown_ftrace_events`、`failed_ftrace_events` 与 atrace 错误。
4. 用 `ftrace_event` 验证原始事件是否进入 Trace，再查看派生表。
5. 查询 `stats` 的所有非零 `data_loss` 项，定位丢数层。
6. Android 15 及以上的 Java Trace 同时考虑 TrackEvent 与 atrace 兼容路径；经典原生 C/C++ `ATRACE_*` 仍检查 `trace_marker`。
7. 只改动一个采集变量，并用同一复现验证变化。

这套顺序把“事件不存在”“配置没有启用”“采集途中丢失”“解析层没有派生数据”分成四类问题。定位到具体层后，再调整事件、缓冲区或解析逻辑，结论才有源码和采集证据支撑。

## 源码与文档锚点

- Android 17 平台：[`atrace.cpp`](https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/cmds/atrace/atrace.cpp)、[`android_os_Trace.cpp`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/jni/android_os_Trace.cpp)、[`tracing_perfetto.cpp`](https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/libs/tracing_perfetto/tracing_perfetto.cpp)、[`trace-dev.cpp`](https://android.googlesource.com/platform/system/core/+/refs/tags/android-17.0.0_r1/libcutils/trace-dev.cpp)
- Android 17 Perfetto：[`tracefs.cc`](https://android.googlesource.com/platform/external/perfetto/+/refs/tags/android-17.0.0_r1/src/traced/probes/ftrace/tracefs.cc)、[`ftrace_controller.cc`](https://android.googlesource.com/platform/external/perfetto/+/refs/tags/android-17.0.0_r1/src/traced/probes/ftrace/ftrace_controller.cc)、[`ftrace_config_muxer.cc`](https://android.googlesource.com/platform/external/perfetto/+/refs/tags/android-17.0.0_r1/src/traced/probes/ftrace/ftrace_config_muxer.cc)、[`perfetto.rc`](https://android.googlesource.com/platform/external/perfetto/+/refs/tags/android-17.0.0_r1/perfetto.rc)
- Android 17 内核 6.18：[`ftrace.rst`](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/Documentation/trace/ftrace.rst)、[`trace-events-sample.h`](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/samples/trace_events/trace-events-sample.h)、[`binder_trace.h`](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/drivers/android/binder_trace.h)
- Perfetto 官方文档：[ftrace 采集与解析](https://perfetto.dev/docs/getting-started/ftrace)、[atrace instrumentation](https://perfetto.dev/docs/getting-started/atrace)、[TraceConfig](https://perfetto.dev/docs/reference/trace-config-proto)、[缓冲区与丢数](https://perfetto.dev/docs/concepts/buffers)
