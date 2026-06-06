---
title: "Android Tracing 基础设施:atrace、ftrace 与 Perfetto 数据采集原理"
chapter: "13.9"
section: "13.9"
drafted_date: "2026-04-08"
drafted_by: "openclaw-task2a"
applicable_versions: "Android 8.0 (API 26) - Android 17 (API 37)"
last_verified: "2026-06-06"
last_verified_against: "AOSP android-16.0.0_r1, frameworks/base/core/jni/android_os_Trace.cpp, frameworks/native/libs/tracing_perfetto/tracing_perfetto.cpp, frameworks/native/cmds/atrace/atrace.cpp, external/perfetto/src/traced/probes/ftrace/, Linux include/trace/events/"
confidence: medium
sources:
  - type: aosp
    path: "frameworks/native/cmds/atrace/"
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
task2b_state: fixed
last_task2b_rerun_at: "2026-05-08T16:50:00+08:00"
task9_result: pass-tech-review
task2b_result: fixed
rework_date: "2026-04-25"
rework_by: openclaw-task2b
last_task9_at: "2026-06-07T04:33:40+08:00"
task9_reviewed_by: openclaw-task9
task9_reviewed_date: "2026-06-07"
task9_review_notes: "2026-05-05 13:34 task9 deep-review: needs-rework。P0 1:Perfetto SQL 原始 ftrace 表仍误写为 ftrace_events;正确表名是 ftrace_event。 | 2026-05-07 Task9 01:20:needs-rework。P0 0 / P1 1 / P2 0;ftrace_event 表名已修正,但 UprobeStats "任意用户态函数 <1%"与 Perfetto/StatsD 数据出口口径仍缺一手证据。 | 2026-05-08 Task9 17:38:needs-rework。P0 2 / P1 0 / P2 1;13.9 DRM tracepoint 与 Perfetto FtraceConfig 字段名存在事实错误,需回炉修正。 | 2026-05-08 Task9 18:39:needs-rework。P0 1 / P1 0 / P2 1;FtraceConfig.drain_period_ms 默认值误写 250ms,AOSP android-16.0.0_r1 实际 historical default 100ms、poll-backed 可到 1000ms,已写入 queue。 | 2026-05-08 Task9 20:30:pass-tech-review。P0 0 / P1 0 / P2 0;FtraceConfig 字段、drain_period_ms 默认值、trace_marker 路径和 atrace category 口径已按源码闭合;tracing 开销数字仍按待验证处理,仅作为 P3 日志项。 自动晋升 finalized。 | 2026-06-06 Task9 idle audit 21:20:needs-rework。P0 1 / P1 1 / P2 0;Android 15+ android.os.Trace 已接入 libtracing_perfetto 双路径,正文仍写成全部经 trace_marker/ftrace ring buffer;且 android-17-beta3 / AOSP main 锚点不可作为 Android 17 正文结论,已写入 queue。"
last_task2b_at: 2026-06-06T22:50:00+08:00
repaired_by: openclaw-task2b
repaired_date: "2026-04-26"
updated_by: openclaw-task2b
updated_date: "2026-06-06"
task2b_fix_notes: "2026-06-06 Task2B main: 修复 Task9 P0 Android 15+ trace_marker 单路径→双路径(libtracing_perfetto TrackEvent 分支),移除 AOSP main 锚点引用,更新数据流图;C/C++ ATRACE 仍走 trace_marker 路径单独说明。"
last_task9_review_log: logs/deep-review/2026-06-07-04-deep-review.md
status: finalized
task6_result: "pass-light-edit"
task6_state: reviewed
task9_state: reviewed
pipeline_stage: ready-to-publish
reviewed_by: "openclaw-task6"
reviewed_date: 2026-06-07
task6_reviewed_date: "2026-05-08"
last_task6_at: "2026-06-07T04:12:51+08:00"
last_task6_audit: "2026-05-26"
last_task6_review_log: logs/review/2026-06-07-04-review.md
review_notes: "2026-05-08 task6 revisit: pass-light-edit。完成 Task2B 修复后的复审;清理 frontmatter 重复字段,收紧 tracing 开销表述的验证边界;未发现新增 B 类回炉项;转入 Task9 复审。 | 2026-06-07 task6 revisit-2: pass-light-edit。Task2B 已修复 Task9 idle audit P0（Android 15+ 双路径、AOSP main 锚点移除）;四层质检全部通过，无 B 类回炉项;auto-promotion 未触发（task9_result=auto-fixed 非 pass-tech-review，queue.json 有 pending 13.9 条目）。 | 2026-06-07 Task9 04: deep-review pass-tech-review。P0/P1 0；Android 15+ Trace 双路径、FtraceConfig 字段与 trace_marker 边界均按 android-16.0.0_r1 闭合，自动晋升 finalized。"
deepseek_polish_state: done
last_deepseek_polish_at: 2026-05-27
last_task9_audit: "2026-06-06"
last_task9_autofix_at: "2026-06-07"
---


# 13.9 Android Tracing 基础设施:atrace、ftrace 与 Perfetto 数据采集原理

当 Perfetto 里某个 Track 突然不出数,或者自定义 tag 没进 Trace 时,只会看 UI 已经不够了。需要知道这些数据是从哪一层采上来,又是沿着什么路径写进 Trace 文件的。

这一节拆开 Android Tracing 的整条数据链:Linux 内核的 ftrace 如何提供基础事件,atrace 如何把用户空间 tag 接到这条链上,Perfetto 的 `traced` / `traced_probes` 如何把内核和用户空间数据汇到同一个 Trace 中,以及 App、Framework、Kernel 三层分别怎么扩展自定义追踪点。

<!-- outline-start -->
## 本节要点大纲

### 锚点(必须覆盖)

- 🔹 ftrace 的三种模式,以及 tracefs 如何暴露控制接口
- 🔹 atrace category、`trace_marker` 与用户空间 trace tag 的写入路径
- 🔹 `traced` / `traced_probes` 的职责分工,以及 ftrace 数据进入 Perfetto 的路径
- 🔹 App、Framework、Kernel 三层自定义 tracing 的入口与适用场景
- 🔹 tracing 开销、buffer 溢出和生产环境抓取约束

### 扩展(可选深入)

- 🔸 eBPF 与静态 tracepoint 的互补关系
- 🔸 boot trace 的启用方式与适用场景

### OpenClaw 加工指引

> **锚点**是最低覆盖要求,加工时必须逐条落实并标注验证结果。
> **扩展**视素材丰富程度选择性深入。
> 如果从 AOSP 源码或官方文档中发现更精确的数据流细节,可在对应锚点后补充,并标注验证来源。
<!-- outline-end -->

## Linux 内核 ftrace 框架

Perfetto Trace 中大部分内核事件的数据源头都是 ftrace。它是 Linux 内核自 2.6.27 起内置的函数追踪框架,是一整套追踪基础设施的总称。

### ftrace 的三种核心模式

ftrace 提供了三种工作模式,各有适用场景:

**function tracer**——在内核编译时通过 `-mfentry`(x86)或 `-pg`(ARM)GCC 选项,在几乎每个内核函数入口插入一条 `fentry_call` 指令。默认情况下这条指令是 `nop`,开销为零。当启用 function tracer 时,运行时动态将 `nop` 替换为对追踪回调函数的调用。

function tracer 因而可以记录内核中**所有被追踪函数的调用序列**,粒度极细,但开销也最大。在 ARM64 上,function tracer 的典型开销约为 10-15% 的系统性能下降,因此不适合在性能测试中使用,主要用于调试和代码理解。

**function_graph tracer**——在 function tracer 的基础上进一步记录函数的调用和返回,可以输出类似代码缩进的调用图。开销比 function tracer 还要高一些,因为它需要在函数入口和出口都插入钩子。

**tracepoint**——这是 Android 性能分析中最常用的 ftrace 模式。与 function tracer 不同,tracepoint 不是"追踪所有函数",而是在内核源码中**预定义的探测点**。内核开发者在关键位置使用 `TRACE_EVENT` 宏声明一个 tracepoint,编译后它在未被启用时是一条分支预测为 not-taken 的 `if` 判断(使用 `static_key` 机制),开销接近零。当启用时,它执行对应的 probe 回调函数,将事件数据写入 per-CPU ring buffer。

Perfetto Trace 中的 `sched_switch`、`sched_wakeup`、`cpu_frequency`、`binder_transaction`、`block_rq_issue` 等内核事件,全部来自 tracepoint。它们是 ftrace 中开销最低、最稳定的数据源。

### tracefs 文件系统接口

用户空间通过 tracefs(通常挂载在 `/sys/kernel/tracing/`,旧内核在 `/sys/kernel/debug/tracing/`)与 ftrace 交互。关键文件包括:

- `available_events`:列出所有已注册的 tracepoint 名称
- `set_event`:写入要启用的 tracepoint 名称来激活
- `trace`:读取当前 ring buffer 中的追踪数据
- `buffer_size_kb`:设置 per-CPU ring buffer 的大小
- `tracing_on`:控制追踪的启停(写入 0/1)

[已验证: AOSP android-16.0.0_r1, kernel/trace/trace.c]

用 Perfetto 抓取 Trace 时,traced 守护进程通过读写这些文件来控制 ftrace 的启停和数据采集。Perfetto 的 `TraceConfig.ftrace_config.ftrace_events` 字段列出的每一个事件名,最终都会被写入 `set_event` 文件。

### Android 常用 tracepoint 分类

Android 系统中与性能分析相关的 tracepoint 主要分布在以下几个子系统:

| 子系统 | 代表性 tracepoint | 用途 |
|--------|-------------------|------|
| sched | `sched_switch`, `sched_wakeup`, `sched_wakeup_new`, `sched_blocked_reason` | CPU 调度分析,线程状态追踪(§13.3 中大量使用) |
| power | `cpu_frequency`, `cpu_idle`, `clock_set_rate`, `clock_disable` | 功耗与频率分析,DVFS 行为追踪 |
| binder | `binder_transaction`, `binder_transaction_received`, `binder_lock`, `binder_unlock` | IPC 延迟分析,Binder ANR 诊断(§9.1, §9.2) |
| block | `block_rq_issue`, `block_rq_complete`, `block_rq_insert` | I/O 延迟分析,存储性能诊断(§6.1-6.3) |
| net | `netif_receive_skb`, `net_dev_xmit`, `napi_gro_receive_entry` | 网络传输分析 |
| drm | `drm_vblank_event`, `drm_sched_job`, `drm_run_job` | 显示管线 VSync 追踪、GPU 任务调度(§2.3) |

[已验证: AOSP android-16.0.0_r1, available_events]

Perfetto 对 ftrace 事件做了两层处理:**原始 ftrace 事件**存放在 `ftrace_event` 表中(可按 `name` 列过滤事件类型),**派生表/视图**则对原始事件做结构化解析后生成更易查询的形式。例如 `sched_switch` 参与生成 `sched` 表的调度切片视图,`cpu_frequency` 进入 `cpu_frequency_counters` 表。

不是每个 tracepoint 都有独立的派生表——部分事件只在 `ftrace_event` 原始表中体现,查询时需要按 `name` 过滤。`ftrace_event` 表主要用于调试和验证采集是否生效;生产分析应优先使用 Perfetto 提供的派生表(`sched`、`cpu_frequency_counters` 等),字段更丰富且经过类型转换。理解这种"原始事件 → 派生视图"的分层关系,有助于在 Perfetto 中遇到数据异常时快速定位是采集层面的问题还是分析层面的问题。

## atrace 用户空间追踪框架

ftrace 是内核层的机制。Android 应用和 Framework 代码运行在用户空间,需要一个桥梁把用户空间的追踪需求传递到内核。这个桥梁就是 atrace。

### atrace 的分类机制

`atrace` 命令(源码位于 `frameworks/native/cmds/atrace/`)对 ftrace 的 tracepoint 做了分类封装。执行 `atrace --help` 时看到的那一堆 category(`sched`, `freq`, `binder_driver`, `gfx`, `view`, `dalvik` 等),每个 category 背后对应一组 ftrace events 和/或用户空间 tag 的启停。

例如:
- `atrace sched` → 启用 ftrace 的 `sched_switch`, `sched_wakeup`, `sched_wakeup_new` 等 tracepoint
- `atrace gfx` → 主线实现里至少启用 `ATRACE_TAG_GRAPHICS`,并可附带 `events/gpu_mem/gpu_mem_total/enable` 这类 graphics 相关 sysfs 开关;厂商还可以追加自己的 vendor categories,因此不能把 `gfx` 直接等同为某一个固定的 kernel event
- `atrace freq` → 启用 `events/power/cpu_frequency/enable`,并按设备支持启用 `clock/cpu_frequency_limits`、`clock/cpuhp/suspend_resume` 等与频率变化相关的事件或开关
- `atrace idle` → 启用 `events/power/cpu_idle/enable`

功耗分析里常把 `sched + freq + idle + power` 放在同一份采集配置中。这里的 `idle` 是独立 category,不能把 `cpu_idle` 归到 `freq`。

[已验证: AOSP android-16.0.0_r1, frameworks/native/cmds/atrace/atrace.cpp k_categories;Android 17 待 android-17.0.0_r1 公开后复核]

Perfetto 的 `TraceConfig.ftrace_config.ftrace_events` 直接绕过 atrace 的分类,直接操作 ftrace 的 event 名称。因此可以精确指定需要哪些 tracepoint,不受 atrace 预设分类限制。

### 用户空间 Trace tag 的底层实现

App 和 Framework 中常用的 `Trace.beginSection("myTag")` / `Trace.endSection()`(Android API)和 C/C++ 中的 `ATRACE_CALL()` / `ATRACE_BEGIN()` 宏,它们的数据最终通过 ftrace 或 Perfetto 自身的管道传递。具体路径与 Android 版本有关,不能一概写成"全部经 trace_marker → ftrace ring buffer"。

#### Java 侧 android.os.Trace

`android.os.Trace.beginSection("myTag")` 在 Android 14 及更早版本中的路径:

1. `Trace.beginSection()` → `nativeTraceBegin()` JNI 入口 `frameworks/base/core/jni/android_os_Trace.cpp`
2. 老路径通过 `libcutils/trace-dev.cpp` 中的 `atrace_begin()` 写入 `/sys/kernel/tracing/trace_marker`

Android 15+ 的实际路径变了:`android_os_Trace.cpp` 转而调用 `tracing_perfetto::traceBegin()`(位于 `frameworks/native/libs/tracing_perfetto/tracing_perfetto.cpp`)。Android 15.0.0_r1 先用 `toPerfettoCategory()` 判断是否有可用 Perfetto category;Android 16.0.0_r1 起再通过 `shouldPreferAtrace()` 处理 atrace 与 Perfetto 同时启用时的优先级:
- Perfetto category 已启用,且当前配置不要求兼容同一 category 的 atrace 会话时,走 **Perfetto TrackEvent** 路径,数据由 Perfetto producer 直接汇入 Trace 文件,不经过 ftrace ring buffer
- Perfetto category 未启用、tag 仍由 atrace 会话采集,或 Android 16+ 并发 atrace 兼容规则要求保留 atrace 输出时,走 `atrace_begin()` → `trace_marker` 路径

Android 15+ 中用户空间的 trace section 不再只有 ftrace ring buffer 一条通道:Perfetto TrackEvent 路径让数据可以绕开 ftrace ring buffer 直接进入 traced。分析 Android 15+ 设备的 Trace 时,Java 侧用户空间 slices 可能同时来自 trace_marker 解析出的 slice / `ftrace_event` 原始事件和 Perfetto SDK track;是否走 TrackEvent 取决于 Perfetto category 是否启用以及并发 atrace 兼容规则。

#### C/C++ ATRACE 宏

`ATRACE_CALL()` / `ATRACE_BEGIN()` / `ATRACE_END()` 宏定义在 `system/core/libcutils/include/cutils/trace.h`,底层仍调用 `atrace_begin()` 等接口。与 Java 侧不同,这些宏在 Android 15+ 中仍然走 `atrace_begin()` → `trace_marker` 路径,没有切换到 TrackEvent 分支。

`trace_marker` 常见写入格式包括 `B|<pid>|<name>`(begin)、`E|<pid>`(end)和 `C|<pid>|<name>|<value>`(counter)。Counter 用于记录随时间变化的数值,例如队列长度、缓存大小或业务侧自定义计数。Perfetto 解析 Trace 时,会把这些用户空间 tag 转成对应进程的 slice 或 counter Track。

[已验证: AOSP android-16.0.0_r1, frameworks/base/core/jni/android_os_Trace.cpp, frameworks/native/libs/tracing_perfetto/tracing_perfetto.cpp, system/core/libcutils/trace-dev.cpp, kernel/trace/trace.c trace_marker_write()]

Android 14 及更早版本中,用户空间追踪事件和内核 `sched_switch` 等事件共用 ftrace ring buffer,因此天然在同一根时间线上。Android 15+ 的 TrackEvent 路径让部分用户空间事件不再经过 ftrace ring buffer,但 traced 会把各路数据源汇流到同一个 Trace 文件中,时间线仍然统一。

### atrace / Perfetto 在启动过程中的角色

启动期 trace 需要按版本区分两条路径。

- **较早的 atrace boot trace**:`init` 监听 `persist.debug.atrace.boottrace=1`,随后启动 `boottrace` 服务。该服务实际执行的是 `atrace --async_start -f /data/misc/boottrace/categories`,从 `/data/misc/boottrace/categories` 读取 category 列表,把事件写进内核 trace buffer。它没有固定的 trace 文件输出目录,通常要在系统起来后再执行 `atrace --async_stop -z -o <path>` 导出结果。
- **Android 13+ 的 Perfetto boot trace**:`perfetto.rc` 监听 `persist.debug.perfetto.boottrace=1`,启动 `perfetto_trace_on_boot`。配置文件固定放在 `/data/misc/perfetto-configs/boottrace.pbtxt`,输出文件固定写到 `/data/misc/perfetto-traces/boottrace.perfetto-trace`。

两条路径都依赖 init 属性触发,但落盘方式不同。atrace 负责先把 trace 挂到 ring buffer 上,Perfetto 则在启动期直接按配置生成可分析的 `.perfetto-trace` 文件。

[已验证: AOSP android-16.0.0_r1, frameworks/native/cmds/atrace/atrace.rc, external/perfetto/perfetto.rc]

## Perfetto traced 守护进程与数据流

Perfetto 在 Android 9(Pie)引入,从 Android 10 开始替代 Systrace 成为默认的追踪后端。它的核心是 `traced` 守护进程。

### traced 的架构

traced 进程(源码位于 `external/perfetto/src/traced/`)采用 producer-consumer 架构:

- **traced service**:中心协调者,管理数据源的注册和启停
- **traced_probes**:内置的 producer 进程,负责从 ftrace、`/proc` 文件系统等系统数据源采集数据
- **Consumer**:发起 Trace 请求的客户端(可以是 Perfetto CLI、Android Studio、或通过 `android.os.TracingManager` 的 App)

数据流如下(Android 15+ 双路径):

```text
ftrace tracepoints ──┐
                      ├── traced_probes ──→ traced service ──→ Trace 文件
/proc/* 文件系统 ────┤
                      │
用户空间 tag ─────────┤
  ├── C/C++ ATRACE: trace_marker ──→ ftrace ring buffer ──→ traced_probes
  └── Java Trace (Android 15+)
      ├── atrace fallback ──→ trace_marker ──→ ftrace ring buffer ──→ traced_probes
      └── Perfetto TrackEvent ──→ traced service (直连)
```

[图:ftrace tracepoint、trace_marker、traced_probes、traced service 到 Trace 文件的数据流示意图,标注 Android 15+ TrackEvent 分流]

[已验证: AOSP android-16.0.0_r1, external/perfetto/src/traced/]

### traced 如何采集 ftrace 数据

traced_probes 采集 ftrace 数据的核心步骤:

1. 读取 `TraceConfig` 中的 `ftrace_config.ftrace_events` 列表
2. 打开 `/sys/kernel/tracing/` 目录下的控制文件
3. 将需要启用的 tracepoint 名称写入 `set_event`
4. 设置 `buffer_size_kb` 为配置值(通常 32-128MB)
5. 写入 `tracing_on` 为 `1` 开始采集
6. 循环读取 per-CPU ring buffer 中的数据(通过 `trace_pipe_raw`),解析后写入 Perfetto protobuf 流
7. Trace 结束时写入 `tracing_on` 为 `0`,关闭所有 fd

`TraceConfig` 中几个容易忽略的 ftrace 相关配置:

- `ftrace_config.drain_period_ms`:多久从 ring buffer 读一次数据。AOSP `ftrace_controller.cc` 中 `kDefaultTickPeriodMs = 100`,即未显式配置时 historical default 为 100ms;若所有实例使用 buffer watermark polling,`GetTickPeriodMs()` 返回 `kPollBackingTickPeriodMs = 1000`。proto 注释建议除本地精调外保持 unset。设太大会导致 buffer 溢出丢数据,设太小会增加 CPU 唤醒频率。注意这是 `FtraceConfig` 消息内的字段名,不是顶层的 `TraceConfig` 字段
- `ftrace_config.buffer_size_kb`:per-CPU ring buffer 大小。设备 8 核时设 32KB 意味着总共 256KB 的内核缓冲区,高负载场景下很容易溢出。32KB 是一个容易溢出的反例值,不是默认值;Perfetto v43+ 多数配置不显式设置该字段,默认值 / `buffer_size_lower_bound` 通常远大于 32KB
- `ftrace_config.ftrace_events`:要启用的 tracepoint 列表。这是 `FtraceConfig` 消息内的字段,通过 `TraceConfig.ftrace_config` 设置

traced_probes 读取 ftrace 数据的源码路径:

- `FtraceController`(`external/perfetto/src/traced/probes/ftrace/ftrace_controller.cc`)负责读取 `TraceConfig`、启停 ftrace,并按 `FtraceConfig.drain_period_ms` 触发采集循环
- `CpuReader`(`external/perfetto/src/traced/probes/ftrace/cpu_reader.cc`)负责解析单个 CPU 的原始 ftrace page
- `FtraceProcfs`(`external/perfetto/src/traced/probes/ftrace/ftrace_procfs.cc`)封装 tracefs 访问;`OpenPipeForCpu()` 打开 `/sys/kernel/tracing/per_cpu/cpu<N>/trace_pipe_raw`
- 原始二进制事件通过 ftrace parser / event filter 处理后,写入 Perfetto protobuf 流并交给 traced service
- `trace_pipe_raw` 与 `trace`(文本格式)的区别:前者输出二进制 ftrace event 结构体,由 traced_probes 直接解析,避免一次文本序列化和反序列化

[已验证: AOSP android-16.0.0_r1, external/perfetto/src/traced/probes/ftrace/{ftrace_controller.cc,cpu_reader.cc,ftrace_procfs.cc}]

### 用户空间 Data Source 注册

除了 ftrace,Perfetto 还支持用户空间自定义 Data Source。这里需要区分两条路径:

**路径一:App 层时间片(最常用)。** 通过 `android.os.Trace` / `androidx.tracing` 写 section:Android 14 及更早版本经 `trace_marker` 进入 ftrace;Android 15+ 按前文的 TrackEvent / atrace fallback 双路径进入 Perfetto。适合绝大多数场景,不需要引入额外依赖。

**路径二:Perfetto C++ SDK 自定义 Data Source。** 如果需要发射结构化的自定义数据(不是简单的时间片),可以使用 Perfetto C++ SDK 注册自定义数据源。这是纯 C++ API,Java/Kotlin 应用需要通过 JNI 调用:

```cpp
// Perfetto C++ SDK - 注册自定义 Data Source
#include "perfetto.h"

class MyDataSource : public perfetto::DataSource<MyDataSource> {
 public:
  void OnSetup(const SetupArgs&) override {}
  void OnStart(const StartArgs&) override {}
  void OnStop(const StopArgs&) override {}
};

PERFETTO_DECLARE_DATA_SOURCE_STATIC_MEMBERS(MyDataSource);
PERFETTO_DEFINE_DATA_SOURCE_STATIC_MEMBERS(MyDataSource);

// 注册时:
perfetto::DataSourceDescriptor dsd;
dsd.set_name("my.custom.data");
MyDataSource::Register(dsd);
```

注册后,在 `TraceConfig` 中通过 `data_sources` 字段指定名称即可启用。

[待验证: Android 16+ TracingManager API 是否提供 Java 层直接注册 Perfetto Data Source 的能力]

## 自定义 Tracing 实战

理解了这条数据链后,就可以按层次添加自定义追踪点。

[图:App、Framework、Kernel 三层 tracing 入口与数据汇合位置示意图]

### App 层:android.os.Trace 和 androidx.tracing

最简单的方式:

```java
// android.os.Trace(API 18+)
Trace.beginSection("loadUserData");
try {
    loadUserDataFromDatabase();
} finally {
    Trace.endSection();
}
```

在 Perfetto 中,这些 section 会出现在**调用该方法的线程 Track** 中(不限于主线程),名称为 `loadUserData`。约束有三点:
- `beginSection` 和 `endSection` 必须在同一线程配对调用
- section 可以嵌套,但不能交叉
- section 名称在 Perfetto SQL 的 `slice` 表中,可按名称过滤

如果需要跨线程追踪异步操作,API 29+ 提供了 `Trace.beginAsyncSection()` / `Trace.endAsyncSection()`,用 cookie 关联起止端。

`androidx.tracing` 库(`androidx.tracing:tracing`)提供两个价值:一是向后兼容(API < 18 时自动降级为空操作),二是通过 `TraceCompat`(已 deprecated,新代码直接用 `androidx.tracing.Trace`)统一 `beginSection` / `beginAsyncSection` 的调用入口。

1.x 版本主要做兼容封装;2.0.0-alpha 引入了新的低开销 in-process tracing API,支持协程上下文传播和可插拔后端。

[已验证: developer.android.com/reference/androidx/tracing/Trace, androidx.tracing:tracing:1.2.0]

### Framework 层:ATRACE 宏

在 Framework Java 代码中,Android 提供了 `android.os.Trace` 的同等 API。在 native C/C++ 代码中(如 SurfaceFlinger、AudioFlinger),使用 `ATRACE_CALL()` 和 `ATRACE_BEGIN()` 宏:

```cpp
// 自动 RAII:构造时 begin,析构时 end
void SurfaceFlinger::handleMessageRefresh() {
    ATRACE_CALL();  // 自动以函数名作为 section 名称
    // ... 合成一帧的逻辑
}

// 手动控制
ATRACE_BEGIN("computeLayerBounds");
computeLayerBounds();
ATRACE_END();
```

这些宏定义在 `system/core/libcutils/include/cutils/trace.h` 中,底层调用 `atrace_begin()` / `atrace_end()`,最终写入 `trace_marker`。

[已验证: AOSP android-16.0.0_r1, system/core/libcutils/include/cutils/trace.h]

### 内核层:添加自定义 tracepoint

系统/OEM 开发者添加内核级 tracepoint 时,最小可编译路径分三步。

1. 在 `include/trace/events/<subsystem>.h` 声明 tracepoint。`<trace/define_trace.h>` 要放在 include guard 外面:

```c
// include/trace/events/my_custom.h
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
        __assign_str(name, name); // Linux < 6.10 使用双参数形式
        // Linux 6.10+ 使用 __assign_str(name),第二个参数被移除
    ),
    TP_printk("value=%d name=%s", __entry->value, __get_str(name))
);

#endif /* _TRACE_MY_CUSTOM_H */

/* This part must be outside protection. */
#include <trace/define_trace.h>
```

2. 在唯一一个 C 文件中生成 tracepoint 定义:

```c
// drivers/.../my_custom_trace.c
#define CREATE_TRACE_POINTS
#include <trace/events/my_custom.h>
```

3. 在业务代码中调用生成的 helper:

```c
#include <trace/events/my_custom.h>

void my_path(void)
{
    trace_my_event(42, "test_event");
}
```

Makefile 只负责把包含 `CREATE_TRACE_POINTS` 的源文件编进对应模块或内核目录,不在 `kernel/trace/Makefile` 里"注册" tracepoint。编译完成后,事件会出现在 tracefs 的 `available_events` 中,名称是 `my_custom:my_event`,Perfetto 配置里写成 `my_custom/my_event`。

[已验证: Linux kernel tracepoint pattern, include/trace/events/*.h, include/trace/define_trace.h, CREATE_TRACE_POINTS]

> **内核版本差异**:`__assign_str()` 宏在 Linux 6.10 发生了参数变更。旧内核(包括当前 GKI 6.6 分支)使用双参数写法 `__assign_str(dst, src)`;Linux 6.10+ 移除了第二个参数,改为 `__assign_str(dst)`,编译器自动从 `TP_STRUCT__entry` 中的 `__string()` 声明推导源字段。如果目标设备运行 Android 17 / Kernel 6.12,需确认内核版本后使用对应的写法。

### 在 Perfetto 中查看自定义追踪数据

只要自定义 tracepoint 被注册到 ftrace,Perfetto 就能采集它。在 `TraceConfig` 中添加:

```protobuf
ftrace_config {
  ftrace_events: "my_custom/my_event"
}
```

在 SQL 中查询:

```sql
-- 调试用:从原始 ftrace_event 表查询自定义事件
SELECT ts, name
FROM ftrace_event
WHERE name = 'my_custom_my_event'
```

> **注意**:`ftrace_event` 表是 Perfetto 对原始 ftrace ring buffer 数据的直接映射,字段较少。生产分析应优先使用 `sched`、`thread_state`、`counter`、`slice` 等派生表;结构化参数通过 `arg_set_id` / `EXTRACT_ARG()` 获取,查询前可先 `SELECT DISTINCT name FROM ftrace_event` 确认目标事件是否存在。如果自定义事件需要在分析中反复使用,推荐通过 Perfetto 的 `trace_processor_shell --metrics-v2` 或自定义 SQL view 做二次封装。

## Tracing 开销与性能影响

"加 Trace 会不会影响性能"--这是很多人关心但很少被量化回答的问题。

### 不同追踪模式的开销对比

| 追踪模式 | 典型开销 | 适用场景 |
|----------|---------|---------|
| function tracer | 系统 10-15% 性能下降 | 内核调试、代码理解,**禁止**在生产或性能测试中启用 |
| tracepoint(已启用) | 单个 tracepoint 约 100-500ns | 性能分析首选;Android 默认追踪集开销 < 3% 需按设备和事件集复测 |
| tracepoint(未启用) | 接近零(static_key branch) | 平时零开销,按需启用 |
| trace_marker(用户空间 tag) | 约 200-500ns/次 | App/Framework 追踪,高频调用时需注意 |
| eBPF kprobe | 约 500-2000ns/次 | 动态追踪,比 tracepoint 开销略高 |

[待验证: tracepoint 和 trace_marker 的精确纳秒级开销数据需要在不同平台实测]

### ftrace buffer 与数据丢失

ftrace 使用 per-CPU ring buffer 存储事件。当事件产生速度超过消费者(traced_probes)的读取速度时,旧事件会被覆盖。Perfetto 中某个时间段的数据突然消失,通常就是 ring buffer 溢出造成的。

缓解方法:
- 增大 buffer(`buffer_size_kb`),但会占用更多内核内存
- 减少启用的 tracepoint 数量,只采集需要的
- 调整 `TraceConfig.ftrace_config.drain_period_ms`,让 traced_probes 更频繁地读取

### 生产环境中的 Tracing 最佳实践

1. **最小化启用的事件集**:不要"全选"。只启用分析目标相关的事件
2. **控制 Trace 时长**:30-60 秒足够大多数分析场景,超过 5 分钟的 Trace 文件会很大且难以分析
3. **避免高频自定义 tag**:如果在一个循环里调用 `Trace.beginSection()`,频率超过每秒 1000 次时,tag 本身就会成为性能负担
4. **控制 buffer 大小**:在低内存设备上,大 buffer 可能导致内存压力

## 与 eBPF 的关系

eBPF 是 tracepoint 的重要补充。传统的 tracepoint 是静态的--必须在编译时在源码中声明。而 eBPF 提供了动态追踪能力:

- **kprobe**:动态附加到任意内核函数入口,无需修改内核源码
- **uprobe**:动态附加到用户空间函数入口,无需修改应用代码
- **tracepoint**:eBPF 程序也可以附加到现有的静态 tracepoint 上,获取结构化的参数数据

Android 16 引入的 UprobeStats 是基于 eBPF uprobe 机制的动态埋点工具,可以在不修改应用代码的情况下对用户态函数做耗时统计。实际开销与命中频率、BPF map 更新次数、ring buffer 写入和栈回溯深度强相关(详见 §14.10);简单的 uprobe/uretprobe 单次开销常在微秒级,高频热点函数上需要评估对目标线程的尾部延迟影响。UprobeStats 适合低频采样或冷路径观测,不建议对帧循环内的高频函数做全量统计。

[来源: intake/research-feeds/2026-04-07-19-android17-ebpf-sched-ext-uprobestats-observability.md;"任意函数 <1%" 缺一手基准数据,已收窄为条件化描述]

§14.10 会继续讨论 eBPF 在 Android 性能分析中的具体应用。

## 小结

这一节梳理了 Android Tracing 的完整数据流:

```text
内核 tracepoint ──→ ftrace ring buffer ──→ traced_probes ──→ traced ──→ Trace 文件 ──→ Perfetto UI/SQL
C/C++ ATRACE ──→ trace_marker ──→ ftrace ring buffer ──↗
Java android.os.Trace (Android 14 及更早) ──→ trace_marker ──→ ftrace ring buffer ──↗
Java android.os.Trace (Android 15+) ──┬── Perfetto TrackEvent ──→ traced ──↗
                                      └── atrace fallback ──→ trace_marker ──→ ftrace ring buffer ──↗
```

理解这个链条后:
- 遇到 Trace 数据缺失,先检查 ftrace buffer 配置
- 需要自定义追踪点,按 App、Framework、Kernel 三层选择入口
- 评估 Tracing 对测试结果的影响时,对照不同模式的开销范围
- OEM/系统开发者可以沿着内核 tracepoint 到 Perfetto 的路径扩展观测能力

## 延伸阅读

### XTrace:字节跳动生产级 Android 动态追踪系统深度解析
- 来源:/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/DeepResearch/XTrace:字节跳动生产级 Android 动态追踪系统深度解析.md
- 类型:DeepResearch 调研结果
- 摘要:XTrace 利用 ART Instrumentation 机制做非侵入式动态追踪,并通过改造 entry point 路径绕开全局方法注入与强制解释执行两大性能坑,还给出了线上 A/B 测试与故障诊断收益。
- 注入时间:2026-04-18
- 价值:能把 13.9 从基础设施层延伸到生产级动态追踪方案对比。

### btrace (bytedance/btrace) 深度调研报告
- 来源:/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/DeepResearch/btrace (bytedance:btrace) 深度调研报告.md
- 类型:DeepResearch 调研结果
- 摘要:围绕 btrace 1.0→3.0 演进,说明从编译期插桩转向运行时 Hook + 同步抓栈的设计原因,覆盖 ShadowHook、StackVisitor hack、ART method pointer 批量符号化,以及与 Perfetto、异步采样方案的取舍边界。
- 注入时间:2026-04-21
- 价值:把第三方 tracing 工具的架构取舍讲透,适合补强 Android tracing 生态的横向对比。
