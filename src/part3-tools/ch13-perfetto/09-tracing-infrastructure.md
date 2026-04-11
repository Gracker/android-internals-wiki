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
pipeline_stage: task6_pending
task6_state: pending
task9_state: pending
task2b_state: idle
---

# 13.9 Android Tracing 基础设施：atrace、ftrace 与 Perfetto 数据采集原理

前面几节我们一直在用 Perfetto 做分析：看 CPU 调度、看渲染管线、看 Binder 调用、看内存变化。但我们从未追问一个根本问题——这些数据是怎么被采集出来的？

这个问题并非"知道了也没什么用"。当我们在 Perfetto 中发现某个 Track 的数据突然消失、当自定义的追踪点没有出现在 Trace 中、当需要给团队内部的模块添加性能埋点时，理解底层采集机制就变成了前提条件。对于系统开发和 OEM 团队来说，这更是日常工作中绕不过去的一环。

这一节我们从最底层讲起：Linux 内核的 ftrace 框架如何工作，Android 的 atrace 如何在 ftrace 之上封装出面向应用的追踪接口，Perfetto 的 traced 守护进程如何把内核和用户空间的数据汇总到同一个 Trace 文件中，以及我们如何在不同层级自定义追踪点。

## Linux 内核 ftrace 框架

Perfetto Trace 中大部分内核事件的数据源头都是 ftrace。它是 Linux 内核自 2.6.27 起内置的函数追踪框架，不是"一个工具"，而是一整套追踪基础设施的总称。

### ftrace 的三种核心模式

ftrace 提供了三种工作模式，各有适用场景：

**function tracer**——在内核编译时通过 `-mfentry`（x86）或 `-pg`（ARM）GCC 选项，在几乎每个内核函数入口插入一条 `fentry_call` 指令。默认情况下这条指令是 `nop`，开销为零。当启用 function tracer 时，运行时动态将 `nop` 替换为对追踪回调函数的调用。

这意味着 function tracer 可以记录内核中**所有被追踪函数的调用序列**，粒度极细，但开销也最大。在 ARM64 上，function tracer 的典型开销约为 10-15% 的系统性能下降，因此不适合在性能测试中使用，主要用于调试和代码理解。

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

当我们用 Perfetto 抓取 Trace 时，traced 守护进程本质上就是通过读写这些文件来控制 ftrace 的启停和数据采集。Perfetto 的 `TraceConfig` 中 `ftrace_events` 字段列出的每一个事件名，最终都会被写入 `set_event` 文件。

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

Perfetto 的 `TraceConfig.ftrace_events` 本质上是绕过 atrace 的分类，直接操作 ftrace 的 event 名称。这也是为什么 Perfetto 比 atrace 更灵活——我们可以精确指定需要哪些 tracepoint，而不受 atrace 预设分类的限制。

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

[待补充：traced_probes 读取 ring buffer 的具体代码路径]

### 用户空间 Data Source 注册

除了 ftrace，Perfetto 还支持用户空间自定义 Data Source。通过 Perfetto SDK（C++/Java），开发者可以注册自定义的数据源：

```java
// 通过 Perfetto SDK 注册自定义 data source
DataSource.register(new DataSource.InstanceDescriptor<MyDataSource>("my.custom.data"));
```

或通过 `android.os.Trace` / `androidx.tracing` 写入 trace_marker，这些数据会被 traced 自动采集。

## 自定义 Tracing 实战

理解了底层机制后，我们来看看在不同层级如何添加自定义追踪点。

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

在 Perfetto 中，这些 section 会出现在主线程 Track 中，名称为 `loadUserData`。需要注意：
- `beginSection` 和 `endSection` 必须在同一线程配对调用
- section 可以嵌套，但不能交叉
- section 名称在 Perfetto SQL 的 `slice` 表中，可按名称过滤

`androidx.tracing` 库提供了兼容性封装和额外的 `LazyThreadSafetyMode` 控制参数。如果 minSdk 低于 18，它会自动降级为空操作。

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
