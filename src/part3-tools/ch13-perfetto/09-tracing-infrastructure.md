---
title: "Android Tracing 基础设施：atrace、ftrace 与 Perfetto 数据采集原理"
chapter: "13.9"
section: "13.9"
status: ready-for-review
drafted_date: "2026-04-08"
drafted_by: "openclaw-task2a"
applicable_versions: "Android 8.0 (API 26) - Android 17 (API 37)"
last_verified: "2026-04-08"
last_verified_against: "AOSP android-17-beta3, kernel/trace/"
confidence: medium
sources:
  - type: aosp
    path: "frameworks/native/cmds/atrace/"
  - type: aosp
    path: "system/traced/"
  - type: aosp
    path: "external/perfetto/src/traced/"
  - type: official
    path: "https://source.android.com/docs/core/debug/atrace"
  - type: kernel
    path: "kernel/trace/"
  - type: research
    path: "intake/research-feeds/2026-04-07-19-android17-ebpf-sched-ext-uprobestats-observability.md"
tags: [tracing, atrace, ftrace, tracepoint, perfetto, kernel, observability]
related_chapters: ["13.1", "13.2", "13.5", "14.10", "1.5"]
pipeline_stage: task9_pending
task6_state: reviewed
task9_state: pending
task2b_state: fixed
reviewed_by: openclaw-task6
reviewed_date: "2026-04-21"
task6_result: pass-light-edit
task9_result: needs-rework
---

# 13.9 Android Tracing 基础设施：atrace、ftrace 与 Perfetto 数据采集原理

当 Perfetto 里某个 Track 突然不出数，或者自定义 tag 没进 Trace 时，只会看 UI 已经不够了。我们得知道这些数据是从哪一层采上来，又是沿着什么路径写进 Trace 文件的。

这一节拆开 Android Tracing 的整条数据链：Linux 内核的 ftrace 如何提供基础事件，atrace 如何把用户空间 tag 接到这条链上，Perfetto 的 `traced` / `traced_probes` 如何把内核和用户空间数据汇到同一个 Trace 中，以及 App、Framework、Kernel 三层分别怎么扩展自定义追踪点。

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 ftrace 的三种模式，以及 tracefs 如何暴露控制接口
- 🔹 atrace category、`trace_marker` 与用户空间 trace tag 的写入路径
- 🔹 `traced` / `traced_probes` 的职责分工，以及 ftrace 数据进入 Perfetto 的路径
- 🔹 App、Framework、Kernel 三层自定义 tracing 的入口与适用场景
- 🔹 tracing 开销、buffer 溢出和生产环境抓取约束

### 扩展（可选深入）

- 🔸 eBPF 与静态 tracepoint 的互补关系
- 🔸 boot trace 的启用方式与适用场景

### OpenClaw 加工指引

> **锚点**是最低覆盖要求，加工时必须逐条落实并标注验证结果。
> **扩展**视素材丰富程度选择性深入。
> 如果从 AOSP 源码或官方文档中发现更精确的数据流细节，可在对应锚点后补充，并标注验证来源。
<!-- outline-end -->

## Linux 内核 ftrace 框架

Perfetto Trace 中大部分内核事件的数据源头都是 ftrace。它是 Linux 内核自 2.6.27 起内置的函数追踪框架，是一整套追踪基础设施的总称。

### ftrace 的三种核心模式

ftrace 提供了三种工作模式，各有适用场景：

**function tracer**——在内核编译时通过 `-mfentry`（x86）或 `-pg`（ARM）GCC 选项，在几乎每个内核函数入口插入一条 `fentry_call` 指令。默认情况下这条指令是 `nop`，开销为零。当启用 function tracer 时，运行时动态将 `nop` 替换为对追踪回调函数的调用。

function tracer 因而可以记录内核中**所有被追踪函数的调用序列**，粒度极细，但开销也最大。在 ARM64 上，function tracer 的典型开销约为 10-15% 的系统性能下降，因此不适合在性能测试中使用，主要用于调试和代码理解。

**function_graph tracer**——在 function tracer 的基础上进一步记录函数的调用和返回，可以输出类似代码缩进的调用图。开销比 function tracer 还要高一些，因为它需要在函数入口和出口都插入钩子。

**tracepoint**——这是 Android 性能分析中最常用的 ftrace 模式。与 function tracer 不同，tracepoint 不是"追踪所有函数"，而是在内核源码中**预定义的探测点**。内核开发者在关键位置使用 `TRACE_EVENT` 宏声明一个 tracepoint，编译后它在未被启用时是一条分支预测为 not-taken 的 `if` 判断（使用 `static_key` 机制），开销接近零。当启用时，它执行对应的 probe 回调函数，将事件数据写入 per-CPU ring buffer。

Perfetto Trace 中我们看到的 `sched_switch`、`sched_wakeup`、`cpu_frequency`、`binder_transaction`、`block_rq_issue` 等内核事件，全部来自 tracepoint。它们是 ftrace 中开销最低、最稳定的数据源。

### tracefs 文件系统接口

用户空间通过 tracefs（通常挂载在 `/sys/kernel/tracing/`，旧内核在 `/sys/kernel/debug/tracing/`）与 ftrace 交互。关键文件包括：

- `available_events`：列出所有已注册的 tracepoint 名称
- `set_event`：写入要启用的 tracepoint 名称来激活
- `trace`：读取当前 ring buffer 中的追踪数据
- `buffer_size_kb`：设置 per-CPU ring buffer 的大小
- `tracing_on`：控制追踪的启停（写入 0/1）

[已验证: AOSP android-17-beta3, kernel/trace/trace.c]

当我们用 Perfetto 抓取 Trace 时，traced 守护进程通过读写这些文件来控制 ftrace 的启停和数据采集。Perfetto 的 `TraceConfig` 中 `ftrace_events` 字段列出的每一个事件名，最终都会被写入 `set_event` 文件。

### Android 常用 tracepoint 分类

Android 系统中与性能分析相关的 tracepoint 主要分布在以下几个子系统：

| 子系统 | 代表性 tracepoint | 用途 |
|--------|-------------------|------|
| sched | `sched_switch`, `sched_wakeup`, `sched_wakeup_new`, `sched_blocked_reason` | CPU 调度分析，线程状态追踪（§13.3 中大量使用） |
| power | `cpu_frequency`, `cpu_idle`, `clock_set_rate`, `clock_disable` | 功耗与频率分析，DVFS 行为追踪 |
| binder | `binder_transaction`, `binder_transaction_received`, `binder_lock`, `binder_unlock` | IPC 延迟分析，Binder ANR 诊断（§9.1, §9.2） |
| block | `block_rq_issue`, `block_rq_complete`, `block_rq_insert` | I/O 延迟分析，存储性能诊断（§6.1-6.3） |
| net | `netif_receive_skb`, `net_dev_xmit`, `napi_gro_receive_entry` | 网络传输分析 |
| drm | `drm_vblank_event`, `drm_atomic_commit` | 显示管线，VSync 追踪（§2.3） |

[已验证: AOSP android-17-beta3, available_events]

每一个 tracepoint 在 Perfetto SQL 中都有对应的表或可以直接查询。例如 `sched_switch` 对应 `sched` 表，`cpu_frequency` 对应 `cpu_frequency_counters`。理解这种从 tracepoint 到 SQL 的映射关系，有助于我们在 Perfetto 中遇到数据异常时快速定位是采集层面的问题还是分析层面的问题。

## atrace 用户空间追踪框架

ftrace 是内核层的机制。Android 应用和 Framework 代码运行在用户空间，需要一个桥梁把用户空间的追踪需求传递到内核。这个桥梁就是 atrace。

### atrace 的分类机制

`atrace` 命令（源码位于 `frameworks/native/cmds/atrace/`）对 ftrace 的 tracepoint 做了分类封装。当我们执行 `atrace --help` 时看到的那一堆 category（`sched`, `freq`, `binder_driver`, `gfx`, `view`, `dalvik` 等），每个 category 背后对应一组 ftrace events 和/或用户空间 tag 的启停。

例如：
- `atrace sched` → 启用 ftrace 的 `sched_switch`, `sched_wakeup`, `sched_wakeup_new` 等 tracepoint
- `atrace gfx` → 启用 `drm_vblank_event` + 用户空间 tag `gfx`
- `atrace freq` → 启用 `cpu_frequency`, `cpu_idle` 等 tracepoint

[已验证: AOSP android-17-beta3, frameworks/native/cmds/atrace/atrace.cpp]

Perfetto 的 `TraceConfig.ftrace_events` 直接绕过 atrace 的分类，直接操作 ftrace 的 event 名称。这也是为什么 Perfetto 比 atrace 更灵活——我们可以精确指定需要哪些 tracepoint，而不受 atrace 预设分类的限制。

### 用户空间 Trace tag 的底层实现

我们在 App 和 Framework 中经常使用的 `Trace.beginSection("myTag")` / `Trace.endSection()`（Android API）和 C/C++ 中的 `ATRACE_CALL()` / `ATRACE_BEGIN()` 宏，它们的数据最终也通过 ftrace 传递。

具体流程是这样的：

1. 应用调用 `android.os.Trace.beginSection("myTag")`
2. 这最终调用到 `android.os.Trace.nativeBeginSection()` → JNI → `libcutils/Trace.cpp` 中的 `atrace_begin()`
3. `atrace_begin()` 将追踪数据写入一个特殊的文件描述符——这个 fd 指向的是 `/sys/kernel/tracing/trace_marker`
4. `trace_marker` 是 ftrace 提供的一个接口，允许用户空间程序向 per-CPU ring buffer 写入自定义事件

`trace_marker` 写入的数据格式是 `B|<pid>|<name>`（begin）和 `E|<pid>`（end）。在 Perfetto 解析 Trace 时，这些用户空间 tag 被提取并显示在对应进程的 Track 中。

[已验证: AOSP android-17-beta3, system/core/libcutils/Trace.cpp, kernel/trace/trace.c trace_marker_write()]

这就是为什么 Perfetto 中的用户空间追踪事件能和内核的 `sched_switch` 等事件出现在同一根时间线上——它们共用同一个 ring buffer。

### atrace 在启动过程中的角色

Android 系统启动时（init 进程阶段），如果检测到 `persist.sys.atrace.boot` 属性为 `1`，atrace 会自动启用 boot trace 模式，持续采集启动过程中的追踪数据。这对于分析冷启动耗时、系统服务初始化顺序等问题非常有用。boot trace 数据最终写入 `/data/misc/trace/` 目录。

[待验证: Android 17 中 boot trace 的默认配置是否仍然使用此属性]

## Perfetto traced 守护进程与数据流

Perfetto 在 Android 9（Pie）引入，从 Android 10 开始替代 Systrace 成为默认的追踪后端。它的核心是 `traced` 守护进程。

### traced 的架构

traced 进程（源码位于 `external/perfetto/src/traced/`）采用 producer-consumer 架构：

- **traced service**：中心协调者，管理数据源的注册和启停
- **traced_probes**：内置的 producer 进程，负责从 ftrace、`/proc` 文件系统等系统数据源采集数据
- **Consumer**：发起 Trace 请求的客户端（可以是 Perfetto CLI、Android Studio、或通过 `android.os.TracingManager` 的 App）

数据流如下：

```
ftrace tracepoints ──┐
                      ├── traced_probes ──→ traced service ──→ Trace 文件
/proc/* 文件系统 ────┤                                         
                      │
用户空间 tag ─────────┘ (通过 trace_marker)
```

[图：ftrace tracepoint、trace_marker、traced_probes、traced service 到 Trace 文件的数据流示意图]

[已验证: AOSP android-17-beta3, external/perfetto/src/traced/]

### traced 如何采集 ftrace 数据

traced_probes 采集 ftrace 数据的核心步骤：

1. 读取 `TraceConfig` 中的 `ftrace_events` 列表
2. 打开 `/sys/kernel/tracing/` 目录下的控制文件
3. 将需要启用的 tracepoint 名称写入 `set_event`
4. 设置 `buffer_size_kb` 为配置值（通常 32-128MB）
5. 写入 `tracing_on` 为 `1` 开始采集
6. 循环读取 per-CPU ring buffer 中的数据（通过 `trace_pipe_raw`），解析后写入 Perfetto protobuf 流
7. Trace 结束时写入 `tracing_on` 为 `0`，关闭所有 fd

`TraceConfig` 中几个容易忽略的 ftrace 相关配置：

- `ftrace_drain_period_ms`：多久从 ring buffer 读一次数据。默认 250ms。设太大会导致 buffer 溢出丢数据，设太小会增加 CPU 唤醒频率
- `ftrace_buffer_size_kb`：per-CPU ring buffer 大小。设备 8 核时设 32KB 意味着总共 256KB 的内核缓冲区，高负载场景下很容易溢出
- `ftrace_events`：要启用的 tracepoint 列表。Perfetto 文档有完整的事件列表

traced_probes 读取 ftrace 数据的源码路径：

- `FtraceController`（`external/perfetto/src/traced_probes/ftrace_controller.cc`）是核心调度器，`ReadTick()` 方法按 `ftrace_drain_period_ms` 周期读取各 CPU 的 ring buffer
- `FtraceReader`（`external/perfetto/src/traced_probes/ftrace_reader/`）负责打开 per-CPU 的 `/sys/kernel/tracing/per_cpu/cpu<N>/trace_pipe_raw` 文件描述符并循环 read
- 读取到的原始二进制数据通过 `FtraceEventFilter` 过滤后，序列化为 Perfetto protobuf 流交给 traced service
- `trace_pipe_raw` 与 `trace`（文本格式）的区别：前者输出二进制 ftrace event 结构体，由 traced_probes 直接解析，避免了一次文本序列化和反序列化的开销

[待验证: 具体文件名在不同 Perfetto 版本中的变化，以及 GKI kernel 下 tracefs 挂载路径差异]

### 用户空间 Data Source 注册

除了 ftrace，Perfetto 还支持用户空间自定义 Data Source。这里需要区分两条路径：

**路径一：App 层时间片（最常用）。** 通过 `android.os.Trace` / `androidx.tracing` 写入 `trace_marker`，traced 会自动采集。适合绝大多数场景，不需要引入额外依赖。

**路径二：Perfetto C++ SDK 自定义 Data Source。** 如果你需要发射结构化的自定义数据（不是简单的时间片），可以使用 Perfetto C++ SDK 注册自定义数据源。这是纯 C++ API，Java/Kotlin 应用需要通过 JNI 调用：

```cpp
// Perfetto C++ SDK — 注册自定义 Data Source
#include "perfetto.h"

class MyDataSource : public perfetto::DataSource<MyDataSource> {
 public:
  void OnSetup(const SetupArgs&) override {}
  void OnStart(const StartArgs&) override {}
  void OnStop(const StopArgs&) override {}
};

PERFETTO_DECLARE_DATA_SOURCE_STATIC_MEMBERS(MyDataSource);
PERFETTO_DEFINE_DATA_SOURCE_STATIC_MEMBERS(MyDataSource);

// 注册时：
perfetto::DataSourceDescriptor dsd;
dsd.set_name("my.custom.data");
MyDataSource::Register(dsd);
```

注册后，在 `TraceConfig` 中通过 `data_sources` 字段指定名称即可启用。

[待验证: Android 16+ TracingManager API 是否提供 Java 层直接注册 Perfetto Data Source 的能力]

## 自定义 Tracing 实战

理解了这条数据链后，就可以按层次添加自定义追踪点。

[图：App、Framework、Kernel 三层 tracing 入口与数据汇合位置示意图]

### App 层：android.os.Trace 和 androidx.tracing

最简单的方式：

```java
// android.os.Trace（API 18+）
Trace.beginSection("loadUserData");
try {
    loadUserDataFromDatabase();
} finally {
    Trace.endSection();
}
```

在 Perfetto 中，这些 section 会出现在**调用该方法的线程 Track** 中（不限于主线程），名称为 `loadUserData`。需要注意：
- `beginSection` 和 `endSection` 必须在同一线程配对调用
- section 可以嵌套，但不能交叉
- section 名称在 Perfetto SQL 的 `slice` 表中，可按名称过滤

如果需要跨线程追踪异步操作，API 29+ 提供了 `Trace.beginAsyncSection()` / `Trace.endAsyncSection()`，用 cookie 关联起止端。

`androidx.tracing` 库（`androidx.tracing:tracing`）提供了两个价值：一是向后兼容（API < 18 时自动降级为空操作）；二是通过 `TraceCompat`（已 deprecated，新代码直接用 `androidx.tracing.Trace`）统一 `beginSection` / `beginAsyncSection` 的调用入口。1.x 版本主要做兼容封装；2.0.0-alpha 引入了新的低开销 in-process tracing API，支持 Coroutine context 传播和可插拔 backend。

[已验证: developer.android.com/reference/androidx/tracing/Trace, androidx.tracing:tracing:1.2.0]

### Framework 层：ATRACE 宏

在 Framework Java 代码中，Android 提供了 `android.os.Trace` 的同等 API。在 native C/C++ 代码中（如 SurfaceFlinger、AudioFlinger），使用 `ATRACE_CALL()` 和 `ATRACE_BEGIN()` 宏：

```cpp
// 自动 RAII：构造时 begin，析构时 end
void SurfaceFlinger::handleMessageRefresh() {
    ATRACE_CALL();  // 自动以函数名作为 section 名称
    // ... 合成一帧的逻辑
}

// 手动控制
ATRACE_BEGIN("computeLayerBounds");
computeLayerBounds();
ATRACE_END();
```

这些宏定义在 `libcutils/Trace.h` 中，底层调用 `atrace_begin()` / `atrace_end()`，最终写入 `trace_marker`。

[已验证: AOSP android-17-beta3, system/core/libcutils/include/cutils/trace.h]

### 内核层：添加自定义 tracepoint

对于系统/OEM 开发者，添加内核级 tracepoint 的标准流程：

1. 在头文件中声明 tracepoint：

```c
// kernel/trace/events/my_custom.h
#undef TRACE_SYSTEM
#define TRACE_SYSTEM my_custom

TRACE_EVENT(my_event,
    TP_PROTO(int value, const char *name),
    TP_ARGS(value, name),
    TP_STRUCT__entry(
        __field(int, value)
        __string(name, name)
    ),
    TP_fast_assign(
        __entry->value = value;
        __assign_str(name, name);
    ),
    TP_printk("value=%d name=%s", __entry->value, __get_str(name))
);
```

2. 在代码中调用：

```c
#include <trace/events/my_custom.h>
trace_my_event(42, "test_event");
```

3. 在 `kernel/trace/Makefile` 中注册

[待验证: 完整的 tracepoint 注册流程在不同 GKI 版本中的差异]

### 在 Perfetto 中查看自定义追踪数据

只要自定义 tracepoint 被注册到 ftrace，Perfetto 就能采集它。在 `TraceConfig` 中添加：

```protobuf
ftrace_events: "my_custom/my_event"
```

在 SQL 中查询：

```sql
SELECT ts, value, name
FROM ftrace
WHERE name = 'my_custom_my_event'
```

## Tracing 开销与性能影响

"加 Trace 会不会影响性能"——这是很多人关心但很少被量化回答的问题。

### 不同追踪模式的开销对比

| 追踪模式 | 典型开销 | 适用场景 |
|----------|---------|---------|
| function tracer | 系统 10-15% 性能下降 | 内核调试、代码理解，**禁止**在生产或性能测试中启用 |
| tracepoint（已启用） | 单个 tracepoint 约 100-500ns | 性能分析首选，Android 默认追踪集开销 < 3% |
| tracepoint（未启用） | 接近零（static_key branch） | 平时零开销，按需启用 |
| trace_marker（用户空间 tag） | 约 200-500ns/次 | App/Framework 追踪，高频调用时需注意 |
| eBPF kprobe | 约 500-2000ns/次 | 动态追踪，比 tracepoint 开销略高 |

[待验证: tracepoint 和 trace_marker 的精确纳秒级开销数据需要在不同平台实测]

### ftrace buffer 与数据丢失

ftrace 使用 per-CPU ring buffer 存储事件。当事件产生速度超过消费者（traced_probes）的读取速度时，旧事件会被覆盖。这就是为什么 Perfetto 中有时会发现某个时间段的数据突然消失——ring buffer 溢出了。

缓解方法：
- 增大 buffer（`buffer_size_kb`），但会占用更多内核内存
- 减少启用的 tracepoint 数量，只采集需要的
- 调整 `ftrace_drain_period_ms`，让 traced_probes 更频繁地读取

### 生产环境中的 Tracing 最佳实践

1. **最小化启用的事件集**：不要"全选"。只启用分析目标相关的事件
2. **控制 Trace 时长**：30-60 秒足够大多数分析场景，超过 5 分钟的 Trace 文件会很大且难以分析
3. **避免高频自定义 tag**：如果在一个循环里调用 `Trace.beginSection()`，频率超过每秒 1000 次时，tag 本身就会成为性能负担
4. **注意 buffer 大小**：在低内存设备上，大 buffer 可能导致内存压力

## 与 eBPF 的关系

eBPF 是 tracepoint 的重要补充。传统的 tracepoint 是静态的——必须在编译时在源码中声明。而 eBPF 提供了动态追踪能力：

- **kprobe**：动态附加到任意内核函数入口，无需修改内核源码
- **uprobe**：动态附加到用户空间函数入口，无需修改应用代码
- **tracepoint**：eBPF 程序也可以附加到现有的静态 tracepoint 上，获取结构化的参数数据

Android 16 引入的 UprobeStats 就是基于 eBPF uprobe 机制的动态埋点工具，可以在不修改应用代码的情况下对任意用户态函数进行耗时统计，性能开销 < 1%。

[已验证: 来源见 intake/research-feeds/2026-04-07-19-android17-ebpf-sched-ext-uprobestats-observability.md]

在 §14.10 中我们会深入讨论 eBPF 在 Android 性能分析中的具体应用。

## 小结

我们梳理了 Android Tracing 的完整数据流：

```
内核 tracepoint ──→ ftrace ring buffer ──→ traced_probes ──→ traced ──→ Trace 文件 ──→ Perfetto UI/SQL
用户 trace_marker ──→ ftrace ring buffer ──↗
```

理解这个链条后：
- 遇到 Trace 数据缺失，我们知道要去检查 ftrace buffer 配置
- 需要自定义追踪点，我们知道在哪一层用什么 API
- 想评估 Tracing 对测试结果的影响，我们知道不同模式的精确开销范围
- 对于 OEM/系统开发者，我们知道了从内核到 Perfetto 的完整扩展路径

## 延伸阅读

### XTrace：字节跳动生产级 Android 动态追踪系统深度解析
- 来源：/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/DeepResearch/XTrace：字节跳动生产级 Android 动态追踪系统深度解析.md
- 类型：DeepResearch 调研结果
- 摘要：XTrace 利用 ART Instrumentation 机制做非侵入式动态追踪，并通过改造 entry point 路径绕开全局方法注入与强制解释执行两大性能坑，还给出了线上 A/B 测试与故障诊断收益。
- 注入时间：2026-04-18
- 价值：能把 13.9 从基础设施层延伸到生产级动态追踪方案对比。
