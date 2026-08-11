---
title: Trace 抓取
chapter: '13.2'
section: '13.2'
section_title: Trace 抓取
status: "finalized"
applicable_versions: Android 9 (API 28) - Android 17 (API 37)
last_verified: '2026-07-31'
last_verified_against: AOSP android-17.0.0_r1（external/perfetto ece66975738007dd0978b911d8a2077e49b8f31e、frameworks/native ae266dcb706d083868578cfedce381ef44488a07）+ android17-6.18-2026-06_r6 + Perfetto/Android 官方文档
confidence: high
sources:
- type: internal-reference
  path: /Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/DeepResearch/2026-06-05-trace-capture-linux-perf-frametimeline.md
  role: Trace 抓取、FrameTimeline 与 linux.perf 源码研究入口
- type: internal-reference
  path: /Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/DeepResearch/2026-07-12-android17-ftrace-atrace-perfetto-bridge.md
  role: Android 17 ftrace、atrace 与 Perfetto 数据通路研究入口
- type: internal-reference
  path: /Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/DeepResearch/2026-06-09-android17-tracekit-perfetto-apm-toolchain.md
  role: Android 14-17 data source 与 APM 工具链演进研究入口
- type: official
  path: https://perfetto.dev/docs/getting-started/system-tracing
  role: Perfetto UI、record_android_trace 与基础系统追踪流程
- type: official
  path: https://perfetto.dev/docs/learning-more/android
  role: Android 9-12 服务启用、PBTX 输入、配置目录与设备端 CLI 边界
- type: official
  path: https://perfetto.dev/docs/concepts/config
  role: TraceConfig、buffer、duration 与 data source
- type: official
  path: https://perfetto.dev/docs/reference/trace-config-proto
  role: Android 17 TraceConfig、HeapprofdConfig、JavaHprofConfig 与 PerfEventConfig 字段
- type: official
  path: https://perfetto.dev/docs/getting-started/atrace
  role: linux.ftrace 中的 atrace_categories 与 atrace_apps
- type: official
  path: https://perfetto.dev/docs/data-sources/native-heap-profiler
  role: heapprofd 版本、采样模型和 user build 权限
- type: official
  path: https://perfetto.dev/docs/data-sources/java-heap-profiler
  role: ART heap graph 版本、配置和权限
- type: official
  path: https://perfetto.dev/docs/quickstart/callstack-sampling
  role: linux.perf 调用栈采样与 scope 配置
- type: official
  path: https://perfetto.dev/docs/visualization/large-traces
  role: 大型 trace 的本机 Trace Processor 后端
- type: official
  path: https://perfetto.dev/docs/analysis/sql-stats
  role: stats 表的 data_loss、error 与各采集层统计项
- type: official
  path: https://developer.android.com/reference/android/os/Trace
  role: Java Trace API 版本、配对、名称长度与异步 cookie
- type: official
  path: https://developer.android.com/ndk/reference/group/tracing
  role: NDK ATrace API 与版本边界
- type: aosp
  path: https://android.googlesource.com/platform/external/perfetto/+/refs/tags/android-17.0.0_r1/tools/record_android_trace
  role: Android 17 锚点脚本的 CLI 参数和执行流程
- type: aosp
  path: https://android.googlesource.com/platform/external/perfetto/+/refs/tags/android-17.0.0_r1/protos/perfetto/config/trace_config.proto
  role: buffer fill policy、long trace、duration 与 flush 语义
- type: aosp
  path: https://android.googlesource.com/platform/external/perfetto/+/refs/tags/android-17.0.0_r1/protos/perfetto/config/data_source_config.proto
  role: Android 17 平台 data source 配置入口
- type: aosp
  path: https://android.googlesource.com/platform/external/perfetto/+/refs/tags/android-17.0.0_r1/protos/perfetto/config/profiling/perf_event_config.proto
  role: Android 17 linux.perf timebase、callstack_sampling 与 scope
- type: aosp
  path: https://android.googlesource.com/platform/external/perfetto/+/refs/tags/android-17.0.0_r1/protos/perfetto/config/profiling/heapprofd_config.proto
  role: heapprofd 目标、采样间隔与 continuous dump 字段
- type: aosp
  path: https://android.googlesource.com/platform/external/perfetto/+/refs/tags/android-17.0.0_r1/protos/perfetto/config/profiling/java_hprof_config.proto
  role: ART heap graph 目标与周期 dump 字段
- type: aosp
  path: https://android.googlesource.com/platform/external/perfetto/+/refs/tags/android-17.0.0_r1/src/profiling/perf/perf_producer.cc
  role: linux.perf 注册、目标过滤和进程分片
- type: aosp
  path: https://android.googlesource.com/platform/external/perfetto/+/refs/tags/android-17.0.0_r1/src/profiling/perf/traced_perf.cc
  role: traced_perf 的 init socket 接收与 proc 文件描述符转交
- type: aosp
  path: https://android.googlesource.com/platform/external/perfetto/+/refs/tags/android-17.0.0_r1/traced_perf.rc
  role: traced_perf 身份、init socket、group 与 capability
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/cmds/atrace/atrace.cpp
  role: Android 17 atrace category 与对应 tracefs 事件
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/services/surfaceflinger/Scheduler/FrameTimeline.cpp
  role: FrameTimeline data source 注册
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/services/surfaceflinger/Scheduler/FrameTimeline.h
  role: FrameTimeline data source 名称与 trace cookie
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/os/Trace.java
  role: Android 17 App Trace API 实现
- type: kernel
  path: https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/include/trace/events/sched.h
  role: sched_switch、sched_wakeup 等通用调度 tracepoint
- type: kernel
  path: https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/include/trace/events/power.h
  role: cpu_frequency、cpu_idle 等通用功耗 tracepoint
tags:
- tools
- perfetto
- trace
- capture
polish_by: task2b-polish
task6_state: "reviewed"
task6_result: pass-light-edit
task6_review_notes: "2026-07-09 Task6 re-review (post-Task9 auto-fix): L1 3 fixes (banned word 对齐→匹配, 2x version pinning 当前主干→Android 17). L2 minor. All 6 anchors + 2 extensions covered. No B-class issues. No banned words remaining. | 2026-07-11 08:06 Task6 revisiting-review (post-Task9 idle-audit auto-fix): Task9 将 record_android_trace 获取命令从 Perfetto GitHub main 改为 AOSP android-17.0.0_r1 Gitiles 锚点。L1/L2 复审 clean。锚点 6/6 + 扩展覆盖。无 B 类问题。task6_result=pass-light-edit，task9_result=auto-fixed（无P0/P1），queue 无 pending。✅ 自动晋升 finalized。"
pipeline_stage: "ready-to-publish"
reviewed_by: openclaw-task6
last_task6_audit: "2026-07-11"
last_task6_at: "2026-07-11"
task2b_result: fixed
task2b_fix_date: 2026-07-08
task2b_fix_notes: "2026-07-08 Task2B main rework: P0 token merge fix (20+ commands/APIs), version baseline update (android-17.0.0_r1 verified), FrameTimeline/linux.perf anchor correction, P1 data source selection flow, P2 unverifiable % removal. Based on deep-review 2026-07-08-21 and audit 2026-07-08-20."
task2b_state: fixed
task9_state: "reviewed"
task9_result: "auto-fixed"
last_task9_at: "2026-07-09T05:38:15+08:00"
task9_review_notes: "2026-07-09 Task9 deep-review auto-fix: P0=4 P1=0 P2=2. 修正 Android17 DataSourceConfig 新增数据源口径、FrameTimeline/linux.perf Android17 源码锚点与旧伪代码、linux.perf 版本验证矛盾、unsupported profiling overhead 百分比；回到 Task6 复审。 | 2026-07-09 05:38 Task9 deep-review: pass-tech-review。P0 0 / P1 0 / P2 0；按 android-17.0.0_r1 复核源码锚点、版本边界和交叉引用；Task6 已 pass-light-edit 且 queue 无 pending，自动晋升 finalized。 | 2026-07-11 06:25 Task9 idle audit auto-fix: 将 record_android_trace 获取命令从 Perfetto GitHub main 改为 AOSP android-17.0.0_r1 Gitiles 锚点；回到 Task6 复审。"
last_task9_autofix_at: 2026-07-11
deepseek_cn_review_state: done
last_deepseek_cn_review_at: 2026-07-12
last_task2b_verifier_at: "2026-07-09T03:31:26+08:00"
task2b_verifier_notes: "2026-07-09 Task2B Verifier: task9_state reviewed→pending; Task6 re-reviewed post-auto-fix (pass-light-edit), pipeline task9_pending correct, task9_state was stale reviewed."
task9_reviewed_date: "2026-07-09"
task9_reviewed_by: "openclaw-task9"
last_task9_review_log: "logs/deep-review/2026-07-11-06-audit.md"
updated_by: "openclaw-task9"
updated_date: "2026-07-11"
last_task9_audit: 2026-07-11
---

# 13.2 Trace 抓取

## 抓取配置决定分析上限

一份 trace 能回答哪些问题，由时间窗口、data source、目标进程和 buffer 完整性共同决定。卡顿发生在采集结束之后，或配置里缺少 FrameTimeline、Binder、调度事件时，UI 再熟练也补不回缺失的证据。

抓取前写下一句待验证的问题。例如：“主线程长帧来自 CPU 执行、Binder 等待，还是长期 Runnable 却得不到 CPU？”这句话会直接决定是否采集 App atrace、Binder tracepoint、`sched_switch`、`sched_wakeup`、线程状态和 FrameTimeline。

抓取完成后还要检查丢包。文件成功生成，只能证明会话结束并拿到了输出，不能证明每个 Producer 和 buffer 都没有丢数据。

## 复核基线

| 层级 | 固定锚点 | 引用范围 |
| --- | --- | --- |
| Android 平台 | Android 17 / API 37 / `android-17.0.0_r1` | 设备端 `perfetto`、平台 data source、App Trace API |
| 平台内 Perfetto | `external/perfetto` 提交 `ece66975738007dd0978b911d8a2077e49b8f31e` | `TraceConfig`、`record_android_trace`、heapprofd、`linux.perf` |
| Framework Native | `frameworks/native` 提交 `ae266dcb706d083868578cfedce381ef44488a07` | atrace category、SurfaceFlinger FrameTimeline |
| Android 内核 | `android17-6.18-2026-06_r6` | `sched_switch`、`sched_wakeup`、`cpu_frequency`、`cpu_idle` 等通用 tracepoint |

设备平台和主机脚本要分别记录版本。源码字段固定到 Android 17 平台；浏览器 UI、主机 `trace_processor` 和上游脚本仍会继续变化。

Android 9 到 17 的设备端入口有三处分界：

| Android 版本 | tracing service | 文本配置 | 配置传入方式 |
| --- | --- | --- | --- |
| Android 9 | 服务已进系统镜像；非 Pixel 设备常要手动设置 `persist.traced.enable=1` | 不支持 `--txt` | simple mode，或经 stdin 传入预先序列化的 binary `TraceConfig` |
| Android 10 / 11 | Android 10 非 Pixel 设备仍可能要手动启用；Android 11 起多数设备默认启用 | 支持 PBTX + `--txt` | 非 root 设备宜经 stdin 传入 |
| Android 12-17 | 默认启用 | 支持 PBTX + `--txt` | shell 可从 `/data/misc/perfetto-configs/` 读取配置 |

## 三种抓取入口

| 入口 | 优点 | 适用场景 | 主要边界 |
| --- | --- | --- | --- |
| 设备端 `perfetto` | 直接控制 CLI 和完整 `TraceConfig` | 验证命令、调试设备侧权限、自动化底层流程 | 需要自行处理配置传输、停止和导出 |
| `record_android_trace` | 自动调用设备端 CLI、拉取结果并打开 UI | 日常 ADB 抓取、团队共享配置 | 脚本版本要记录；`-c` 模式由文件控制，短参数不会改写文件内容 |
| Perfetto UI Recording | 可视化选择 transport、buffer 和 probes | 初次组装配置、现场交互抓取 | 页面选项随 UI 版本变化，生成的配置仍要保存 |

三种入口最终都在控制 Perfetto tracing service。入口不同不会自动补齐未启用的数据源。

## 用设备端 `perfetto` 快速抓取

下面的 simple mode 命令用于抓 10 秒调度、频率、窗口、渲染、Binder 和输入事件，并把结果拉回主机。

```bash
adb shell perfetto \
  -o /data/misc/perfetto-traces/trace.perfetto-trace \
  -t 10s \
  sched freq idle am wm gfx view binder_driver input

adb pull /data/misc/perfetto-traces/trace.perfetto-trace .
```

simple mode 会根据短参数生成受限的 `TraceConfig`，仍依赖 `traced` 和 `traced_probes`。输出路径位于 `/data/misc/perfetto-traces/`；Android 9 若无法直接 `adb pull`，可用 `adb shell cat` 把文件重定向到主机。

`adb shell perfetto` 在非交互 ADB 会话里不一定能可靠接收 `Ctrl+C`。可复现问题宜设置 `-t`；后台会话则按 Perfetto background tracing 文档保存 PID，并显式停止该进程。

## 用完整 TraceConfig 抓取

normal mode 接收 protobuf 编码的 `TraceConfig`。PBTX（也常写作 pbtxt）是文本表示，Android 10 起由 `--txt` 解析；Android 9 设备端只接收 binary protobuf。

下面的 Android 12-17 配置用于采集 20 秒 App 渲染、调度、Binder、进程信息和 FrameTimeline。64 MiB 只是便于起步的示例值，抓取后要根据丢包统计和事件速率调整。

```textproto
buffers {
  size_kb: 65536
  fill_policy: RING_BUFFER
}

data_sources {
  config {
    name: "linux.ftrace"
    ftrace_config {
      ftrace_events: "sched/sched_switch"
      ftrace_events: "sched/sched_wakeup"
      ftrace_events: "sched/sched_waking"
      ftrace_events: "sched/sched_blocked_reason"
      ftrace_events: "power/cpu_frequency"
      ftrace_events: "power/cpu_idle"

      atrace_categories: "am"
      atrace_categories: "wm"
      atrace_categories: "gfx"
      atrace_categories: "view"
      atrace_categories: "input"
      atrace_categories: "binder_driver"
      atrace_categories: "dalvik"
      atrace_apps: "com.example.myapp"
    }
  }
}

data_sources {
  config {
    name: "linux.process_stats"
    process_stats_config {
      scan_all_processes_on_start: true
    }
  }
}

data_sources {
  config {
    name: "android.surfaceflinger.frametimeline"
  }
}

duration_ms: 20000
```

`linux.ftrace` 同时承载 raw ftrace event 和 atrace 标记；`linux.process_stats` 补充进程信息；FrameTimeline 是独立 data source。Android 10/11 使用这份配置时，应删除 `android.surfaceflinger.frametimeline` 块。

### 在不同版本上传入配置

Android 12-17 可以把 PBTX 放进专用配置目录。下面的命令用于这条路径。

```bash
adb push config.pbtx /data/misc/perfetto-configs/config.pbtx
adb shell perfetto \
  --txt \
  -c /data/misc/perfetto-configs/config.pbtx \
  -o /data/misc/perfetto-traces/trace.perfetto-trace
```

`perfetto.rc` 会为 shell 创建并放行 `/data/misc/perfetto-configs/`。结果文件仍写到 trace 专用目录。

Android 10/11 的非 root 设备宜通过 stdin 传入同一份 PBTX。下面的管道避免了 SELinux 对普通临时目录读取的限制。

```bash
cat config.pbtx | adb shell perfetto \
  --txt \
  -c - \
  -o /data/misc/perfetto-traces/trace.perfetto-trace
```

`-c -` 表示从标准输入读取配置。Android 9 没有 `--txt`；只有在主机已经按匹配的 proto schema 生成 binary `TraceConfig` 时，才能用同样的 stdin 方式传入二进制。

### `buffers`：容量和保留方向

`size_kb` 定义 tracing service 的 central buffer，单位为 KiB。它不包含内核 per-CPU ftrace buffer，也不包含每个 Producer 的 shared memory；这三层都可能发生数据丢失。

`fill_policy` 决定 central buffer 满时保留哪一端：

- `RING_BUFFER` 是默认策略。新 packet 覆盖较旧的未读 packet，适合保留停止前的一段时间窗。
- `DISCARD` 在 writer 碰到未读 chunk 后停止接收新 packet，保留较早数据。会话仍可继续运行，不能把它解释为“buffer 满后立刻停止 tracing”。

固定写“10 秒用 64 MiB”缺少事件速率和设备条件。更稳妥的做法是先抓短 trace，检查 `stats`，再按峰值写入量和所需时间窗调整。

### `duration_ms`：活动时间和墙上时间

Android 17 的 `TraceConfig.duration_ms` 默认使用不计休眠时间的时钟。短 trace 几乎感受不到差别；跨待机的长 trace 可能在墙上时间里持续得更久。需要把设备休眠也计入期限时，设置 `prefer_suspend_clock_for_duration: true`。

未设置 `duration_ms` 时，会话由 Consumer 显式停止。自动化采集应提供时长、trigger 或清晰的停止路径，避免遗留后台会话。

### `data_sources`：名称、专属配置和目标 buffer

每个 `data_sources.config` 至少给出 data source 名称。需要额外参数时，再填写与该名称配套的字段，例如 `linux.ftrace` 对应 `ftrace_config`，`linux.perf` 对应 `perf_event_config`。

配置多个 central buffer 时，data source 通过 `target_buffer` 选择目标，索引从 0 开始。把高流量 profiling 数据放进独立 buffer，可以避免它覆盖调度和渲染事件；容量仍要用实际 trace 的写入量校准。

## ftrace event 与 atrace category

两类配置都写在 `linux.ftrace.ftrace_config` 中，但来源不同：

- `ftrace_events` 直接启用 tracefs event，例如 `sched/sched_switch`、`binder/binder_transaction`。
- `atrace_categories` 选择 Android 平台预定义的 category。一个 category 可能打开 ATRACE tag、若干 tracefs event，或两者。
- `atrace_apps` 指定哪些 App 的 `ATRACE_TAG_APP` 标记可见，值可以是包名，也可以按官方约定使用 `*`。

Android 17 的 `frameworks/native/cmds/atrace/atrace.cpp` 把 `sched` 映射到调度 tracepoint，把 `freq` 映射到 `power/cpu_frequency` 等事件，把 `binder_driver` 映射到 Binder 驱动 tracepoint。common kernel `android17-6.18-2026-06_r6` 的 `sched.h` 和 `power.h` 提供通用定义；设备是否启用某个事件还受内核配置和厂商实现影响。

下面的命令用于查看当前设备能够启用的 category。

```bash
adb shell atrace --list_categories
```

设备输出才是本次抓取的可用清单。AOSP category 存在，不保证厂商内核提供其依赖的每个 tracefs event。

### 按问题选择最小证据集

| 问题 | 建议起点 | 还需按设备确认的证据 |
| --- | --- | --- |
| App 长帧 | `sched freq gfx view input` + `atrace_apps` + FrameTimeline | GPU render stage、SurfaceFlinger/HWC、厂商频率事件 |
| 冷启动 | `sched freq am wm ss view binder_driver dalvik` + 目标 App | `android_startup` 所需事件、磁盘 I/O、类加载和包管理 |
| ANR / Binder 等待 | `sched am wm ss binder_driver input` | 对端进程 atrace、锁竞争、ANR 窗口前的日志 |
| 内存压力 | `sched memory dalvik` + `linux.process_stats` | PSI、mm event、heapprofd 或 ART heap graph |
| 功耗 | `sched freq idle power` | `android.power`、ODPM rail、热状态和厂商事件 |

表里的组合只负责建立起点。某个问题已经定位到 Binder，就可以删掉无关图形事件；要解释显示末端，则要补 SurfaceFlinger、FrameTimeline、GPU/HWC 或显示侧数据。

## 用 `record_android_trace` 抓取

脚本固定到 Android 17 平台 tag，避免参数随上游更新而悄悄改变。下面的命令从 Gitiles 下载并解码该版本。

```bash
curl -L \
  'https://android.googlesource.com/platform/external/perfetto/+/refs/tags/android-17.0.0_r1/tools/record_android_trace?format=TEXT' \
  | python3 -c \
    'import base64,sys; sys.stdout.buffer.write(base64.b64decode(sys.stdin.buffer.read()))' \
  > record_android_trace
chmod +x record_android_trace
```

下载得到的脚本可用 `python3 record_android_trace --help` 查看参数。使用上游新版脚本也可以，但构建报告中应记录脚本版本。

Android 17 tag 的脚本在 API 29 以下设备上会 sideload `tracebox` 到 `/data/local/tmp/`，因此 Android 9 的脚本抓取路径和直接调用系统 `/system/bin/perfetto` 并不相同。

下面的短参数模式抓 10 秒系统 trace，同时启用目标 App 的 atrace 标记。

```bash
python3 ./record_android_trace \
  -o trace.perfetto-trace \
  -t 10s \
  -b 32mb \
  -a com.example.myapp \
  sched freq view ss input
```

Android 17 tag 的脚本要求提供至少一个 event 或 `-c/--config`。它会调用设备端 `perfetto`、把结果拉回主机，并在默认情况下打开 Perfetto UI；远程主机可加 `--no-open`。

已经准备好 PBTX 时，使用配置模式。下面的命令让时长、buffer、App 和 data source 全部由文件控制。

```bash
python3 ./record_android_trace \
  -c config.pbtx \
  -o trace.perfetto-trace
```

配置模式不要再叠加 `-t`、`-b` 或 `-a`；脚本在 `-c` 分支中直接读取文件，这些短参数不会改写 PBTX。团队复现问题时，提交 PBTX 和脚本版本，比只分享一条临时命令更容易追溯。

## 通过 Perfetto UI 抓取

在 `ui.perfetto.dev` 打开 “Record New Trace” 后，页面会提供当前可用的设备 transport，并逐项检查连接条件。不同 UI 版本可能提供 ADB WebSocket、WebUSB 或其他连接方式，应按页面提示授权，不能用 `adb devices` 的结果代替 UI 自身的连接状态。

Recording Settings 主要控制三件事：

- **Recording mode**：`Stop when full` 保留较早数据，`Ring buffer` 保留停止前的数据，`Long trace` 周期写入文件。
- **In-memory buffer size / Max duration**：定义 central buffer 和会话期限。
- **Probes**：选择调度、频率、atrace、FrameTimeline、内存、功耗或 profiling 数据。

UI 的 probes 名称和分组会随版本调整。配置完成后打开 “Recording command”，保存生成的 PBTX，再用同一份文件执行 `record_android_trace -c`，就能把交互抓取变成可重复的命令。

## 在 App 中添加 Trace 标记

### 同步区间：`beginSection()` / `endSection()`

`Trace.beginSection()` 从 API 18 起可用，区间必须在同一线程内正确嵌套。下面是调用点示例，业务方法的实现未展开。

```java
import android.os.Trace;

Trace.beginSection("loadHomePageData");
try {
    loadHomePageData();
} finally {
    Trace.endSection();
}
```

`finally` 保证异常路径也能关闭最近打开的 section。抓取配置还要把包名放进 `atrace_apps`，否则 App 的 `ATRACE_TAG_APP` 标记不会进入这次 system trace。

Android 17 的 `Trace.java` 将 section name 上限固定为 127 个 Unicode code unit；超长名称会抛出 `IllegalArgumentException`。`|`、换行和空字符由底层协议占用，API 会把它们替换为空格。名称宜包含稳定操作名，动态 ID 放进异步 cookie 或 Counter，避免制造大量难以聚合的 Slice 名称。

格式化 section name 可能创建临时字符串。API 29 及以上可以先用 `Trace.isEnabled()` 判断是否值得构造这类字符串；低版本代码需要按 SDK 版本分支处理。Trace API 内部已经检查开关，普通常量名称不需要重复判断。

### 异步区间和 Counter

`beginAsyncSection()`、`endAsyncSection()` 和 `setCounter()` 从 API 29 起可用。异步区间可以跨线程，也不要求嵌套，但开始和结束必须使用相同名称与 `int` cookie。

```java
import android.os.Trace;

int requestCookie = 1001;
Trace.beginAsyncSection("loadProfile", requestCookie);

startProfileRequest()
        .whenComplete((result, error) -> {
            Trace.setCounter("profileQueueDepth", pendingRequestCount());
            Trace.endAsyncSection("loadProfile", requestCookie);
        });
```

cookie 用来区分同名并发操作。结束调用要覆盖成功、失败和取消等终止路径。业务请求 ID 若为 `long` 或字符串，应建立稳定的 `int` 映射，不能依赖可能冲突的随意截断。

### NDK ATrace

普通 App 的 Native 代码使用公开头文件 `<android/trace.h>`。同步 API 从 API 23 起可用；异步区间和 Counter 从 API 29 起可用。下面的调用点省略了初始化函数的实现。

```c
#include <android/trace.h>

ATrace_beginSection("nativeInit");
initialize_native_components();
ATrace_endSection();
```

这段标记仍走 App tracing tag，抓取时同样要设置 `atrace_apps`。AOSP 平台内部代码常见 `<cutils/trace.h>` 与 `ATRACE_BEGIN`，它们不属于普通 NDK App 的公开集成方式。

Perfetto C++ SDK 的 Track Event 可以提供 category、flow、显式轨道和结构化 annotation。它是另一套埋点路径，具体集成见 §13.20 和 §13.16；只需要 Java/Kotlin 方法区间时，`android.os.Trace` 更直接。

## Long trace：周期写文件

默认会话把 packet 留在 central buffer，Consumer 在结束时读取。Long trace 设置 `write_into_file: true`，让 tracing service 周期性把已提交数据写入 Consumer 提供的文件描述符。

下面的 Android 17 配置演示 1 小时墙上时间、5 秒写文件周期和 2 GiB 文件上限。32 MiB buffer 仍是示例起点，必须用目标设备的事件速率复核。

```textproto
buffers {
  size_kb: 32768
  fill_policy: RING_BUFFER
}

write_into_file: true
file_write_period_ms: 5000
max_file_size_bytes: 2147483648

duration_ms: 3600000
prefer_suspend_clock_for_duration: true

data_sources {
  config {
    name: "linux.ftrace"
    ftrace_config {
      ftrace_events: "sched/sched_switch"
      ftrace_events: "sched/sched_wakeup"
      ftrace_events: "power/cpu_frequency"
      atrace_categories: "am"
      atrace_categories: "wm"
      atrace_categories: "gfx"
      atrace_categories: "view"
    }
  }
}
```

`file_write_period_ms` 的有效最小值是 100 ms。写文件周期越短，磁盘唤醒和 I/O 越频繁；周期越长，central buffer 越要覆盖这一段时间内的峰值写入量。`max_file_size_bytes` 达到上限时会停止 tracing，即使 `duration_ms` 尚未结束。

`flush_period_ms` 要求 Producer 定期提交尚未填满的 shared-memory page，和 `file_write_period_ms` 的 central buffer 写文件动作不同。Android 17 的 service 会为 long trace 自动处理周期 flush，大多数配置无需手动设置；过于频繁的 flush 会增加开销。

这些字段生成一个持续增长的文件，不提供自动轮转。需要多个独立文件时，可运行有界的连续会话，或采用 trigger、clone/periodic snapshot 方案；分段之间是否允许空窗和重叠，要在采集设计里明确。

长 trace 结束后仍要检查丢包和文件尾部完整性。浏览器受内存上限影响时，使用本机 `trace_processor server http trace.perfetto-trace` 作为 UI 后端，详见 §13.4。

## Heap profiling 与 Callstack sampling

profiling 数据量和运行开销通常高于普通调度 trace。应先固定目标进程和问题类型，再设置采样间隔、频率、buffer 与会话时长。

| 目标 | Data source | 平台边界 | user build 的 App 门槛 |
| --- | --- | --- | --- |
| Native 分配与释放调用栈 | `android.heapprofd` | Android 10+ | `profileable` 或 `debuggable` |
| ART 对象分配调用栈 | `android.heapprofd` + `heaps: "com.android.art"` | Android 12+ | `profileable` 或 `debuggable` |
| Java 对象保留图 | `android.java_hprof` | Android 11+ | `profileable` 或 `debuggable` |
| CPU / PMU 调用栈采样 | `linux.perf` | Android 12+ 平台已有；Android 17 源码按上述配置 | `profileable` 或 `debuggable` |

debug Android build 可以扩大到多数 App 和系统服务，具体范围仍受 SELinux、kernel perf 权限、目标进程和厂商配置影响。FrameTimeline 属于 SurfaceFlinger 系统数据，不使用这张表里的 App profiling gate。

### Native 与 ART allocation sampling

heapprofd 是进程外守护进程。目标进程内的 client 在分配路径采样并把记录写入 shared memory，守护进程负责异步展开调用栈、记账和写 trace；不能把整套 profiler 描述成“运行在目标进程中”。

下面的配置针对一个 App 采集 Native 分配，并每 10 秒导出一次累计统计。

```textproto
data_sources {
  config {
    name: "android.heapprofd"
    heapprofd_config {
      process_cmdline: "com.example.myapp"
      sampling_interval_bytes: 4096
      continuous_dump_config {
        dump_phase_ms: 0
        dump_interval_ms: 10000
      }
    }
  }
}
```

`sampling_interval_bytes` 在手写 `TraceConfig` 时必须显式设为非零值。4096 表示平均每 4 KiB 分配量抽取一个样本，采样是随机化过程，并非机械地记录每第 4096 个字节。间隔越小，细粒度分配越容易被观察到，client、shared memory、unwinding 和 trace 体积的成本也越高。

没有 `process_cmdline` 或 `pid` 时，普通目标配置不会自行选择进程。`all: true` 可以请求所有符合资格的进程，但低采样间隔下很容易让 heapprofd 过载。

Android 12+ 若要采集 ART 对象分配，把 `heaps: "com.android.art"` 加入同一 `heapprofd_config`。它回答“采样窗口内哪些调用栈发生分配”，不提供某一时刻的完整对象持有关系。

### Java heap graph

`android.java_hprof` 让目标 ART 进程生成对象引用图。下面的最小配置按进程名请求一次 heap graph。

```textproto
data_sources {
  config {
    name: "android.java_hprof"
    java_hprof_config {
      process_cmdline: "com.example.myapp"
    }
  }
}

duration_ms: 10000
```

结果用于 retained graph 和泄漏保留关系分析，不是包含全部对象字段值的传统 `.hprof` 文件。生成对象图会暂停目标进程并消耗额外内存，抓取窗口应避开需要测量原始延迟的区间。

### `linux.perf` 调用栈采样

Android 17 的 `PerfEventConfig` 已把新配置分成 `timebase` 和 `callstack_sampling`。下面的配置用每 CPU 100 Hz 的 `SW_CPU_CLOCK` 作为采样源，只保留目标 App 的用户空间调用栈。

```textproto
data_sources {
  config {
    name: "linux.perf"
    perf_event_config {
      timebase {
        counter: SW_CPU_CLOCK
        frequency: 100
        timestamp_clock: PERF_CLOCK_MONOTONIC
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

100 Hz 是配置示例，不是跨设备建议值。`frequency` 是向内核请求的每 CPU 采样频率，内核可能因负载而节流；采样结束后应检查丢样统计。省略 `scope` 会保留所有进程的样本，用户空间 unwinder 更容易过载。

Android 13+ 的 `target_cmdline` 支持一个 `*` 通配符，Android 12 按归一化后的命令行做精确匹配。需要内核栈时可设置 `kernel_frames: true`，但 user build 仍受 `kptr_restrict` 和平台权限限制。

`linux.perf` 和 simpleperf 都调用 `perf_event_open`。前者把样本写进 Perfetto trace，便于与调度、Binder 和帧事件放在同一时间轴；后者输出 `perf.data`，更适合独立 CPU profile 和成熟的命令行分析流程。

## Android 17 源码核对点

| 结论 | Android 17 源码位置 | 代码能证明什么 |
| --- | --- | --- |
| atrace category 映射 | `frameworks/native/cmds/atrace/atrace.cpp` | `sched`、`freq`、`idle`、`binder_driver`、`memory` 等 category 对应哪些 ATRACE tag / tracefs event |
| FrameTimeline 注册 | `FrameTimeline.h:656`、`FrameTimeline.cpp:1344-1354` | data source 名为 `android.surfaceflinger.frametimeline`，在 SurfaceFlinger boot finished 路径注册 |
| `linux.perf` 注册 | `perf_producer.cc:80-81, 1327-1331` | Producer 名为 `perfetto.traced_perf`，data source 名为 `linux.perf` |
| `traced_perf` socket | `traced_perf.cc:34-40`、`traced_perf.rc` | init socket 用于接收 `/proc` 文件描述符；守护进程以 `nobody` 运行并依赖 group、capability 和 SELinux |
| profiling 配置 | `perf_event_config.proto`、`heapprofd_config.proto`、`java_hprof_config.proto` | Android 17 的字段、deprecated 边界、scope 和目标过滤语义 |
| 新增平台入口 | `data_source_config.proto` | Android 17 增加 `android.user_list`、`android.inputmethod`、`android.aflags` 配置字段，已有常用 data source 仍保留 |

源码存在某个配置字段，只能证明平台代码具备入口。设备能否产出数据，还要看 Producer 是否注册、feature flag、权限、内核/HAL 和目标进程资格。

## 抓取后的质量检查

分析前先确认这五项：

1. trace 的起止时间覆盖了复现动作，设备时间轴上能找到触发点。
2. 目标进程、线程和 App 自定义标记存在，包名没有写错。
3. 问题所需 data source 有可查询的轨道或表；空轨道要回查配置与权限。
4. `stats` 没有与结论相关的数据丢失；存在丢包时只对完整区间下判断。
5. 记录设备 build、内核、PBTX、脚本和分析端版本，保证别人能复现。

下面的 PerfettoSQL 用于列出非零的数据丢失和错误统计。

```sql
SELECT
  name,
  severity,
  source,
  value
FROM stats
WHERE severity IN ('data_loss', 'error')
  AND value != 0
ORDER BY severity, name;
```

每个命中项要回到对应层处理：ftrace 丢包检查内核 buffer 和读取速率，Producer/central buffer 丢包检查 shared memory、buffer 容量与写文件周期，profiling 丢样还要检查 unwinder 和守护进程资源限制。

## 常见误区

**category 越多越好。** 多余事件会提高写入速率、扩大解析成本，还可能覆盖需要的时间窗。先用问题驱动的最小集合，证据不足时再补。

**文件生成就代表数据完整。** 会话可以在部分 data source 空结果或 buffer 丢包的情况下正常产出文件。`stats`、轨道、目标进程和采集窗口都要检查。

**App 写了 `Trace.beginSection()` 就一定可见。** system trace 还要在 `atrace_apps` 里选中包名，并覆盖这段代码的执行时间。

**Long trace 会自动切成多个文件。** `file_write_period_ms` 控制周期写入，`max_file_size_bytes` 达到上限后停止会话；这两个字段都不负责文件轮转。

**profiling 配置可直接复用到整机。** 省略 `scope`、使用过小的 heap sampling interval 或过高的 perf frequency，都会放大采集扰动。目标进程、频率和采样间隔必须在目标设备上试跑。

## 后续阅读

§13.3 讲 Perfetto UI，§13.4 讲大型 trace，§13.5 讲线程 CPU 状态。拿到 trace 后，先完成上述五项质量检查，再进入具体主题分析。

## 参考资料

- [Recording system traces with Perfetto](https://perfetto.dev/docs/getting-started/system-tracing) 与 [Advanced System Tracing on Android](https://perfetto.dev/docs/learning-more/android)：设备端 CLI、`record_android_trace`、Android 9-12 输入和服务边界。
- [Trace configuration](https://perfetto.dev/docs/concepts/config) 与 [TraceConfig reference](https://perfetto.dev/docs/reference/trace-config-proto)：buffer、duration、long trace、heapprofd、JavaHprofConfig 和 PerfEventConfig。
- [Instrumenting Android apps/platform with atrace](https://perfetto.dev/docs/getting-started/atrace)、[Android `Trace` API](https://developer.android.com/reference/android/os/Trace) 与 [NDK tracing API](https://developer.android.com/ndk/reference/group/tracing)：App 标记、包名、配对、名称长度和 API level。
- [Native/ART allocation profiling](https://perfetto.dev/docs/data-sources/native-heap-profiler)、[ART heap graph](https://perfetto.dev/docs/data-sources/java-heap-profiler) 与 [`linux.perf` callstack sampling](https://perfetto.dev/docs/quickstart/callstack-sampling)：profiling 数据形态、配置和权限。
- [Visualising large traces](https://perfetto.dev/docs/visualization/large-traces) 与 [Trace Processor Stats](https://perfetto.dev/docs/analysis/sql-stats)：本机 Trace Processor HTTP 后端，以及 data loss/error 统计项。
- Android 17 `external/perfetto` 的 [`record_android_trace`](https://android.googlesource.com/platform/external/perfetto/+/refs/tags/android-17.0.0_r1/tools/record_android_trace)、[`trace_config.proto`](https://android.googlesource.com/platform/external/perfetto/+/refs/tags/android-17.0.0_r1/protos/perfetto/config/trace_config.proto)、[`data_source_config.proto`](https://android.googlesource.com/platform/external/perfetto/+/refs/tags/android-17.0.0_r1/protos/perfetto/config/data_source_config.proto)、[`heapprofd_config.proto`](https://android.googlesource.com/platform/external/perfetto/+/refs/tags/android-17.0.0_r1/protos/perfetto/config/profiling/heapprofd_config.proto)、[`java_hprof_config.proto`](https://android.googlesource.com/platform/external/perfetto/+/refs/tags/android-17.0.0_r1/protos/perfetto/config/profiling/java_hprof_config.proto) 与 [`perf_event_config.proto`](https://android.googlesource.com/platform/external/perfetto/+/refs/tags/android-17.0.0_r1/protos/perfetto/config/profiling/perf_event_config.proto)：脚本参数和平台配置协议。
- Android 17 [`atrace.cpp`](https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/cmds/atrace/atrace.cpp)、[`FrameTimeline.cpp`](https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/services/surfaceflinger/Scheduler/FrameTimeline.cpp) 与 [`Trace.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/os/Trace.java)：category、FrameTimeline 和 App Trace 实现。
- common kernel `android17-6.18-2026-06_r6` 的 [`sched.h`](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/include/trace/events/sched.h) 与 [`power.h`](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/include/trace/events/power.h)：调度、频率和 idle tracepoint。
