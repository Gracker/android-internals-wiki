---
title: "Perfetto Profile 导入与 Flamegraph 分析"
chapter: "13.11"
section: "13.11"
status: "finalized"
pipeline_stage: "ready-to-publish"
applicable_versions: "Android 10 (API 29) - Android 17 (API 37)（Simpleperf 导入）；Android 15 (API 35) - Android 17 (API 37)（Perfetto linux.perf 采集，需 profileable/debuggable/userdebug）"
tags: ["perfetto", "simpleperf", "pprof", "flamegraph", "profiling", "trace"]
confidence: "high"
sources:
- type: reference
  path: intake/research-feeds/2026-04-14-07-perfetto-v54-data-explorer-jank-cuj-heap-graph-stats.md
- type: aosp
  path: https://android.googlesource.com/platform/external/perfetto/+/android-17.0.0_r1/src/trace_processor/importers/pprof/pprof_trace_reader.cc
- type: aosp
  path: https://android.googlesource.com/platform/external/perfetto/+/android-17.0.0_r1/src/trace_processor/importers/simpleperf_proto/simpleperf_proto_parser.cc
- type: aosp
  path: https://android.googlesource.com/platform/external/perfetto/+/android-17.0.0_r1/CHANGELOG
- type: aosp
  path: https://android.googlesource.com/platform/system/extras/+/android-17.0.0_r1/simpleperf/cmd_report_sample.cpp
- type: aosp
  path: https://android.googlesource.com/platform/external/perfetto/+/android-17.0.0_r1/src/profiling/perf/event_config.cc
- type: kernel
  path: https://android.googlesource.com/kernel/common/+/android17-6.18-2026-06_r6/include/uapi/linux/perf_event.h
- type: aosp
  path: https://android.googlesource.com/platform/external/perfetto/+/android-17.0.0_r1/docs/getting-started/cpu-profiling.md
- type: aosp
  path: https://android.googlesource.com/platform/external/perfetto/+/android-17.0.0_r1/docs/data-sources/native-heap-profiler.md
- type: aosp
  path: https://android.googlesource.com/platform/external/perfetto/+/android-17.0.0_r1/src/traceconv/main.cc
- type: aosp
  path: https://android.googlesource.com/platform/external/perfetto/+/android-17.0.0_r1/src/traceconv/trace_to_bundle.cc
- type: aosp
  path: https://android.googlesource.com/platform/external/perfetto/+/android-17.0.0_r1/
- type: kernel
  path: https://android.googlesource.com/kernel/common/+/android17-6.18-2026-06_r6/
- type: reference
  path: https://github.com/google/perfetto/releases/tag/v53.0
- type: reference
  path: https://github.com/google/perfetto/releases/tag/v54.0
- type: reference
  path: https://raw.githubusercontent.com/google/perfetto/v54.0/docs/getting-started/other-formats.md
- type: reference
  path: https://raw.githubusercontent.com/google/perfetto/v54.0/docs/getting-started/cpu-profiling.md
- type: kernel
  path: https://android.googlesource.com/platform/external/perfetto/+/android-17.0.0_r1/src/trace_processor/perfetto_sql/stdlib/linux/perf/samples.sql
- type: aosp
  path: system/extras/simpleperf/scripts/app_profiler.py
last_verified: "2026-07-11"
last_verified_against: "Perfetto v53/v54 release notes; Perfetto v54.0 cpu-profiling/other-formats docs; Perfetto v54.0 traceconv/main.cc and trace_enrichment.cc; Android simpleperf public docs snippets"
drafted_date: "2026-05-15"
drafted_by: "openclaw-task2a"
reviewed_date: "2026-05-15"
reviewed_by: "openclaw-task6"
related_chapters: "[\"13.2\", \"13.3\", \"13.9\", \"14.2\", \"14.8\"]"
created_by: "task2a-knowledge-gap"
created_date: "2026-05-15"
gap_source: "研究素材/官方发布说明"
deepseek_polish_state: "done"
last_deepseek_polish_at: "2026-05-26"
task6_state: "reviewed"
last_task6_at: "2026-07-11T08:06:00+08:00"
last_task6_audit: "2026-07-15"
task6_result: "pass-light-edit"
task6_review_notes: "2026-07-11 08:06 Task6 revisiting-review (post-Task9 idle-audit auto-fix): Task9 修正 traceconv bundle --proguard-map 参数为 PERFETTO_PROGUARD_MAP + --symbol-paths。L1: 修复 frontmatter 多处双重引号格式问题（title/chapter/section 等 10+ 字段）。L2: clean。锚点 5/5 + 扩展 2/2 覆盖。无 B 类问题。task6_result=pass-light-edit，task9_result=auto-fixed（无P0/P1），queue 无 pending。✅ 自动晋升 finalized。"
task9_state: "reviewed"
task9_result: "auto-fixed"
task2b_state: "fixed"
task2b_result: fixed
task9_reviewed_date: "2026-07-11"
task9_reviewed_by: "\"openclaw-task9\""
last_task9_at: "2026-07-11T04:28:06+08:00"
last_task9_audit: "2026-07-11"
last_task9_autofix_at: "2026-07-11"
task9_reviewed_at: "2026-07-11T04:28:06+08:00"
last_task9_review_log: "logs/deep-review/2026-07-11-04-audit.md"
p0: 1
p1: 0
p2: 0
updated_by: "openclaw-task9"
updated_date: "2026-07-11"
task9_review_notes: "2026-07-11 Task9 idle-audit AUTO-FIX: P0 1 / P1 0 / P2 0；修正 Perfetto v54.0 `traceconv bundle` 示例中不存在的 `--proguard-map` CLI 参数，改为 v54 源码支持的 `PERFETTO_PROGUARD_MAP` + `--symbol-paths` 路径，并将外部格式/CPU profiling/traceconv 参考锚定到 v54.0。回到 Task6 复审。详见 logs/deep-review/2026-07-11-04-audit.md。"
deepseek_cn_review_state: done
last_deepseek_cn_review_at: 2026-07-17
---

# 13.11 Perfetto Profile 导入与 Flamegraph 分析

平台源码锚点为 Android 17 / API 37 / `android-17.0.0_r1`。Perfetto v53、v54 带来的格式支持属于分析端能力，不能直接换算成设备 API 等级；设备侧 `linux.perf` 采集则有 Android 版本、系统构建类型和应用可分析性要求。读这类资料时，要把“文件能否被新版 Perfetto 打开”和“设备能否录到调用栈”分成两项检查。

## Profile 与 system trace 的数据边界

系统跟踪记录调度、线程状态、Binder、FrameTimeline、GC 和计数器等带时间位置的事件。CPU 采样分析在采样中断发生时记录调用栈，回答某段 CPU 执行更集中在哪些路径。两者可以出现在同一个 Perfetto 文件里，也可以是彼此独立的文件；只有同一次 `linux.perf` 与其他数据源联合录制时，调用栈采样才能直接与帧、调度和 Binder 共用时间轴。

| 输入 | Android 17 Trace Processor 中的主要数据形态 | 保留的信息 | 不能单独证明的内容 |
|---|---|---|---|
| 原生 Perfetto system trace | `slice`、`sched`、`thread_state`、FrameTimeline、计数器 | 事件时间、持续时间、线程状态和跨进程关系 | 未启用调用栈采样时，无法给出完整函数热点 |
| pprof | `__intrinsic_aggregate_profile`、`__intrinsic_aggregate_sample`，UI 有专用页面 | 调用树、指标类型、单位和每条栈的聚合值 | 不生成逐次采样时间轴，不能定位某一帧 |
| Simpleperf protobuf | `cpu_profile_stack_sample` | 样本时间、线程、调用栈、映射和已解析的符号 | 导入器忽略上下文切换记录，不会生成 `sched` 或 `thread_state` |
| Perfetto `linux.perf` | `perf_sample`，并可与 ftrace、FrameTimeline 联合录制 | 同一 trace 时钟下的样本、线程、CPU、调用栈和展开错误 | 采样命中数不能直接换算成单次函数耗时 |
| 带调用栈的 TrackEvent | 事件自身及其调用栈 | 业务事件与栈的明确关联，区域选择可聚合火焰图 | 它记录事件附带的栈，不等同于周期性 CPU 采样 |
| Firefox Profiler 预处理 JSON | 部分 CPU 样本、线程和进程 | 历史资料中的采样调用栈 | Android marker、调度、帧等语义支持不完整 |
| Collapsed Stack | 聚合调用树，指标为 `samples/count` | 根到叶的栈字符串和正整数计数 | 没有进程时间轴、线程状态和 Android 系统事件 |

Android 17 的 pprof 导入器按 pprof 中的指标类型和单位建立聚合表；Simpleperf 导入器把样本写入 `cpu_profile_stack_sample`；`linux.perf` 样本则进入 `perf_sample`。这三个入口不能混用同一套 SQL 表名。[Android 17 pprof 导入器](https://android.googlesource.com/platform/external/perfetto/+/android-17.0.0_r1/src/trace_processor/importers/pprof/pprof_trace_reader.cc)、[Android 17 Simpleperf protobuf 导入器](https://android.googlesource.com/platform/external/perfetto/+/android-17.0.0_r1/src/trace_processor/importers/simpleperf_proto/simpleperf_proto_parser.cc)

诊断交互卡顿时，FrameTimeline、`slice` 和 `thread_state` 负责界定异常区间，区间内的 `perf_sample` 用于判断正在消耗 CPU 的调用路径。分析持续高 CPU 时，聚合 profile 可以快速找到热点，但仍需调度数据确认目标线程得到多少 CPU、是否被其他线程抢占。全局火焰图不能代替帧级因果链。

## pprof：只有聚合值，没有逐样本时间轴

Perfetto v53 加入 pprof 导入和专用 UI 页面。Android 17 的解析代码支持原始 protobuf 和 gzip 压缩输入，并把每种 `sample_type` 的类型与单位保留下来。CPU 时间、分配字节数、对象数可能同时出现在一个 pprof 文件中，火焰图宽度取决于当前选择的指标，不能默认解释为 CPU 时间。

pprof 的 `location_id` 顺序以叶节点开头，导入器会把它转换为 Perfetto 使用的根到叶调用树。导入后的样本是聚合项，未被展开成带原始时间戳的 `perf_sample`。即使 pprof 元数据包含采集周期，也无法仅凭该文件把一条调用栈准确放回某个 `Choreographer#doFrame`。

导入检查可按以下顺序进行：

- 在 pprof 专用页面确认当前指标及单位，例如 `cpu/nanoseconds` 或 `alloc_space/bytes`。
- 对比 self 值与 cumulative 值。self 值表示栈叶处的聚合量，cumulative 值包含所有后代路径。
- 检查映射名、函数名和源码位置。地址或宽泛的共享库名说明符号证据仍不完整。
- 需要解释卡顿时，另行抓取包含 FrameTimeline 和调度数据的原生 trace；两次独立录制只能做场景级对照，不能宣称时间点一一对应。

Perfetto v54 的 `traceconv profile` 增加输出类型自动检测，它处理的是从 Perfetto trace 导出 profile 的流程；打开 pprof 文件不需要先执行该命令。[Perfetto v53/v54 变更记录](https://android.googlesource.com/platform/external/perfetto/+/android-17.0.0_r1/CHANGELOG)

## Simpleperf protobuf：保留样本时间，不导入调度记录

Simpleperf 路径适合 Android 10—17 上的应用 CPU 分析。主机脚本先录制 `perf.data`，再由 `report-sample` 输出 Perfetto 可识别的 protobuf。Android 17 源码中的格式头为 `SIMPLEPERF`，版本号为 1。

下面的命令用系统设置应用展示完整数据流。`100 Hz` 是为了控制分析开销而给出的录制选择，不是所有设备都应固定采用的阈值。

```bash
python system/extras/simpleperf/scripts/app_profiler.py \
  --app com.android.settings \
  -r "-e task-clock:u -f 100 -g --duration 10" \
  -o perf.data

simpleperf report-sample \
  --protobuf \
  --show-callchain \
  --symdir "$ANDROID_PRODUCT_OUT/symbols" \
  -i perf.data \
  -o simpleperf.trace
```

`-g` 要求录制调用链；`--show-callchain` 要求导出完整链。Android 17 的 `report-sample` 在未指定 `--show-callchain` 时会把地址数组裁成一个元素，导入后的火焰图因而只剩叶节点。`--symdir` 会递归查找带符号文件，应用经过 R8 混淆时还可向 `report-sample` 传入与该 APK 同构建的 `--proguard-mapping-file`。[Android 17 `report-sample` 参数与实现](https://android.googlesource.com/platform/system/extras/+/android-17.0.0_r1/simpleperf/cmd_report_sample.cpp)

Simpleperf protobuf 中的样本带时间戳和线程标识。Android 17 导入器会把 Simpleperf 的叶到根调用链反转成 Perfetto 的根到叶顺序，再写入 `cpu_profile_stack_sample`。同一格式中的上下文切换记录当前被忽略，所以打开 `simpleperf.trace` 后看到样本时间位置，不代表文件同时具备线程 Running、Runnable 或休眠证据。

下面的查询用于检查 Simpleperf 导入后的进程、线程和采样覆盖范围。

```sql
SELECT
  process.name AS process_name,
  thread.tid,
  thread.name AS thread_name,
  COUNT(*) AS sample_count,
  MIN(sample.ts) AS first_sample_ts,
  MAX(sample.ts) AS last_sample_ts
FROM cpu_profile_stack_sample AS sample
JOIN thread USING (utid)
LEFT JOIN process ON process.upid = thread.upid
WHERE process.name = 'com.android.settings'
GROUP BY process.name, thread.tid, thread.name
ORDER BY sample_count DESC;
```

查询结果能暴露包名选择错误、目标线程未被采到或录制区间过短等问题。它不能提供调度时长，也不能把样本数解释成函数执行毫秒数。

## `linux.perf`：把 CPU 样本录进同一条时间轴

Perfetto 官方命令行采集文档把 Android 设备下限标为 Android 15。user 构建要求目标应用在清单中声明 `profileable` 或 `debuggable`；userdebug、eng 构建的权限条件不同。这里的版本约束属于设备侧采集能力，与主机 Trace Processor 能导入哪些文件格式是两条独立版本线。

`linux.perf` 使用 Linux `perf_event_open` ABI。Android 17 的 Perfetto 采集端为样本请求 TID、时间和计数值；启用用户态展开后，再请求用户寄存器与栈内存；启用内核帧后，请求内核调用链。对应的内核 ABI 标志定义在 `PERF_SAMPLE_TID`、`PERF_SAMPLE_TIME`、`PERF_SAMPLE_CALLCHAIN`、`PERF_SAMPLE_REGS_USER` 和 `PERF_SAMPLE_STACK_USER` 中。[Android 17 Perfetto perf 事件配置](https://android.googlesource.com/platform/external/perfetto/+/android-17.0.0_r1/src/profiling/perf/event_config.cc)、[android17-6.18-2026-06_r6 perf 事件 ABI](https://android.googlesource.com/kernel/common/+/android17-6.18-2026-06_r6/include/uapi/linux/perf_event.h)

下面的配置以 `100 Hz` 周期采样系统设置应用，并同时录制调度、进程快照和 FrameTimeline。Perfetto 文档建议非原生调用栈低于每 CPU 200 Hz；合适频率仍要结合设备核数、展开错误和被测负载评估。

```protobuf
duration_ms: 10000
buffers: {
  size_kb: 40960
  fill_policy: DISCARD
}

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
          target_cmdline: "com.android.settings"
        }
        kernel_frames: true
      }
    }
  }
}

data_sources {
  config {
    name: "linux.ftrace"
    ftrace_config {
      ftrace_events: "sched/sched_switch"
      ftrace_events: "sched/sched_waking"
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
```

这份配置生成的 `perf_sample`、`sched`、进程信息和 FrameTimeline 共用一条 trace 时间轴。录制开销也是证据的一部分：高频采样、多核设备、Java/JIT 展开和内核帧都会增加采集端工作量，复现时应记录频率、构建类型、设备型号和是否启用内核帧。[Android 17 CPU profiling 文档](https://android.googlesource.com/platform/external/perfetto/+/android-17.0.0_r1/docs/getting-started/cpu-profiling.md)

下面的查询分别检查每个线程的覆盖范围和 perf 导入告警。

```sql
SELECT
  process.name AS process_name,
  thread.tid,
  thread.name AS thread_name,
  COUNT(*) AS sample_count,
  MIN(sample.ts) AS first_sample_ts,
  MAX(sample.ts) AS last_sample_ts,
  SUM(sample.unwind_error IS NOT NULL) AS unwind_error_count
FROM perf_sample AS sample
JOIN thread USING (utid)
LEFT JOIN process ON process.upid = thread.upid
WHERE process.name = 'com.android.settings'
GROUP BY process.name, thread.tid, thread.name
ORDER BY sample_count DESC;

SELECT
  name,
  idx,
  value,
  severity,
  source
FROM stats
WHERE name GLOB 'perf_*'
  AND value != 0
ORDER BY name, idx;
```

第一组结果描述样本落在哪些线程及是否出现展开错误；第二组结果暴露 perf 数据源或导入阶段记录的非零统计项。样本少可能来自线程运行时间短、过滤条件不匹配、丢样本或展开失败，不能用一个固定数量作为通用合格线。

## 选区 Flamegraph 与 TrackEvent 调用栈

CPU 火焰图的横向宽度表示当前指标的聚合值。对周期性 `linux.perf` 样本，常见指标是样本数；对 pprof，它可能是 CPU 纳秒、分配字节或对象数；对 Collapsed Stack，它是行尾给出的计数。宽度不表示某次调用的墙钟耗时，单次持续时间需要 `slice.dur`、方法跟踪或其他区间证据。

阅读火焰图要区分两个值：

- **self**：该函数位于采样调用栈叶节点的数量或指标值。
- **cumulative**：该函数出现在调用路径任意层级时累计的数量或指标值。

一个调度函数可能 cumulative 很宽而 self 很窄，说明大量热点经过它进入不同子路径；一个叶函数 self 很宽，才表示采样经常中断在该函数内部。采样受频率、随机相位、线程运行份额和展开质量影响，函数排名是统计证据，不是精确计时。

Perfetto v53 还支持把调用栈附到 TrackEvent slice 或 instant event。点选单个事件时，详情面板展示该事件的栈；区域选择会把区间内事件附带的栈聚合成火焰图。TrackEvent 调用栈表达“事件记录时附带的调用关系”，`perf_sample` 表达“采样中断时 CPU 上的调用关系”。两者可以交叉验证，不能视为同一种采样来源。

选区分析要同时限定：

- 时间：异常帧、启动阶段、Binder 往返或明确的用户操作标记。
- 线程：主线程、RenderThread、Binder 工作线程或已确认的后台工作线程。
- 场景：冷启动与热启动、首帧与滚动、缓存命中与未命中不能混在同一聚合结果中。
- 指标：样本数、CPU 时间、分配字节等指标需要在结论里写明。

## 符号、内联函数与 R8 还原

可读的函数名依赖采集产物与构建产物匹配。native 栈需要正确的 ELF、Build ID 和展开信息；Java/Kotlin 混淆栈需要同一 APK 构建生成的 `mapping.txt`。路径中存在一个同名 `.so` 还不够，Build ID 不匹配时不能用于证明线上地址对应某个函数。

编译器内联会让一个机器码地址对应多层源码调用关系。Perfetto v53 的 UI 能标出 inline frame，分析时应保留这些层级：外层调用者解释业务入口，内联函数解释执行的源码位置。缺少 DWARF inline 信息时，“火焰图没有某个函数名”不能推出该函数未执行。

对已经录好的原生 Perfetto trace，可分别生成符号包和 R8 去混淆包，再利用 protobuf trace 的可拼接性得到 UI 可直接打开的文件。执行前由构建流水线把该 APK 对应的 `mapping.txt` 绝对路径写入 `R8_MAPPING_FILE`。下面的命令沿用 Android 构建输出目录，并将系统设置包与它的 R8 映射绑定。

```bash
PERFETTO_BINARY_PATH="$ANDROID_PRODUCT_OUT/symbols" \
traceconv symbolize raw-trace.perfetto-trace > symbols.pb

PERFETTO_PROGUARD_MAP="com.android.settings=$R8_MAPPING_FILE" \
traceconv deobfuscate raw-trace.perfetto-trace > deobfuscation.pb

cat raw-trace.perfetto-trace symbols.pb deobfuscation.pb \
  > enriched-trace.perfetto-trace
```

构建流水线必须保证 `R8_MAPPING_FILE` 来自被测 APK 的同一次构建；环境变量的格式固定为 `包名=映射文件`，多个包用冒号分隔。生成的 `symbols.pb` 和 `deobfuscation.pb` 是额外 TracePacket 流，拼接后才能得到可直接打开的 enriched trace。[Android 17 符号化与去混淆文档](https://android.googlesource.com/platform/external/perfetto/+/android-17.0.0_r1/docs/data-sources/native-heap-profiler.md)

`traceconv bundle` 是另一种交付方式。Android 17 的命令行只提供 `--symbol-paths`、`--no-auto-symbol-paths` 和 `--verbose` 等 bundle 选项，没有 `--proguard-map`。下面的命令生成供归档或传递的 TAR 包。

```bash
PERFETTO_PROGUARD_MAP="com.android.settings=$R8_MAPPING_FILE" \
traceconv bundle \
  --symbol-paths "$ANDROID_PRODUCT_OUT/symbols" \
  raw-trace.perfetto-trace \
  settings-profile.tar
```

输出文件是 TAR，其中包含 `trace.perfetto`，并在收集成功时包含 `symbols.pb`、`deobfuscation.pb`；它不是可直接当作原生 trace 打开的 enriched trace。需要单文件查看时，采用上一段的生成与拼接流程。[Android 17 `traceconv bundle` CLI](https://android.googlesource.com/platform/external/perfetto/+/android-17.0.0_r1/src/traceconv/main.cc)、[Android 17 bundle 内容生成](https://android.googlesource.com/platform/external/perfetto/+/android-17.0.0_r1/src/traceconv/trace_to_bundle.cc)

## SQL 与 DataGrid：从探索走向可复现查询

Perfetto v54 的 DataGrid 增加了 pivot、glob、contains、not-contains 和 distinct value picker。它适合快速发现线程、映射或函数分布；需要复查、批量运行和代码评审的结论应固化成 SQL，并记录 Trace Processor 版本。

`linux.perf.samples` 标准库把 `perf_sample` 的调用栈整理成树。下面的查询按累计样本数查看全 trace 热点。

```sql
INCLUDE PERFETTO MODULE linux.perf.samples;

SELECT
  name,
  mapping_name,
  source_file,
  line_number,
  self_count,
  cumulative_count
FROM linux_perf_samples_summary_tree
ORDER BY cumulative_count DESC
LIMIT 50;
```

`self_count` 是以该帧为叶节点的样本数，`cumulative_count` 是该帧出现在调用树中的样本数。该表汇总全部 `perf_sample`；需要进程或时间过滤时，应先筛选原始样本并使用 UI 选区，不能把全 trace 排名直接归因于某个短帧。

同一份 trace 含有 FrameTimeline 与 `linux.perf` 时，可以按异常帧的 UI 线程和时间区间统计样本。下面的查询给出每帧命中的调用栈样本数量。

```sql
INCLUDE PERFETTO MODULE android.frames.timeline;

WITH target_frames AS (
  SELECT
    frame_id,
    ts,
    dur,
    ui_thread_utid
  FROM android_frames
  WHERE process_name = 'com.android.settings'
    AND dur > 0
)
SELECT
  frame.frame_id,
  frame.ts,
  frame.dur,
  COUNT(sample.id) AS ui_thread_sample_count
FROM target_frames AS frame
LEFT JOIN perf_sample AS sample
  ON sample.utid = frame.ui_thread_utid
 AND sample.ts >= frame.ts
 AND sample.ts < frame.ts + frame.dur
GROUP BY frame.frame_id, frame.ts, frame.dur
ORDER BY frame.ts;
```

这里统计的是帧区间内 UI 线程被采中的次数。CPU 线程只在运行时可能被周期采中，零样本既可能表示线程未运行，也可能与频率、短区间、过滤或丢样本有关；还要结合 `thread_state`、FrameTimeline jank 标记和展开统计判断。

## FrameTimeline、Binder 与 GC 的证据拼接

Profile 与系统跟踪联合分析时，每类数据负责不同的证明责任：

- **FrameTimeline** 给出帧的实际区间、预期区间和 jank 分类。`perf_sample` 只能说明该区间内某线程被采中时的调用路径。
- **Binder** 的 slice 与 flow 用于连接客户端等待和服务端执行。客户端线程 blocked 时不会产生用户态 CPU 样本；服务端线程的热点要在服务端 `utid` 上查找。
- **GC** slice 说明一次回收活动的范围，但整个 GC 区间不等于应用线程全程 Stop-The-World。暂停影响需要结合具体 GC pause slice、线程状态和帧重叠关系；采样落在分配路径只能支持“分配活动较重”的判断。

一个可审计的卡顿结论可以写成：某个 FrameTimeline 异常帧与主线程 Running 区间重叠，区间内主线程样本集中在某条已完成符号化的调用路径，复现实验中该分布稳定出现。若主线程大部分时间 blocked，应继续查 Binder、锁或 I/O 等等待链，不能因为全局火焰图中某函数排名靠前就把它定为该帧根因。

## Firefox Profiler 与 Collapsed Stack 迁移

Perfetto v54 支持 Firefox Profiler 预处理 JSON 和 Collapsed Stack。它们主要用于接入历史分析资产。

Collapsed Stack 每行采用根到叶的分号分隔栈，末尾是正整数计数。下面是一份最小格式示例，用于说明解析方向和计数含义。

```text
main;render;layout 37
main;render;draw 63
```

导入后 `render` 的 cumulative count 为两行计数之和，`layout` 与 `draw` 的 self count 分别来自各自行尾。该格式没有线程身份、样本时间、Binder、FrameTimeline 或 CPU 频率，适合比较聚合热点，不适合帧级诊断。

Firefox Profiler 预处理 JSON 可保留 CPU 样本以及部分线程、进程信息。Android 17 所带变更记录将该支持描述为面向 CPU profiling 的部分解析，marker、颜色等丰富元数据不能假定完整导入。原始资料已有 Simpleperf protobuf 时，直接导入该格式能保留更明确的 Android 样本与线程语义。

## 大 trace 的分析顺序

大文件分析可以按证据依赖关系推进：

1. 确认输入类型、设备版本、Perfetto/Trace Processor 版本和采集方式。
2. 检查目标进程、线程、时间覆盖、非零 `stats` 和调用栈展开错误。
3. 从 FrameTimeline、启动阶段、Binder flow、ANR 前窗口或用户标记选定异常区间。
4. 在区间内限定线程，阅读 self 与 cumulative 分布，并确认指标单位。
5. 用 `thread_state`、`sched`、slice 和 flow 解释 CPU 执行、等待与跨进程关系。
6. 把稳定查询保存为 SQL，记录采样频率、构建类型、符号目录、Build ID 和 R8 映射版本。

复查清单应覆盖以下问题：

- 当前文件是聚合 profile，还是包含统一时间轴的原生 trace？
- SQL 使用的是 `cpu_profile_stack_sample` 还是 `perf_sample`？
- 火焰图宽度对应样本数、CPU 时间、分配字节，还是其他指标？
- native Build ID、展开信息和 R8 mapping 是否与被测构建一致？
- 展开错误、丢样本或目标过滤是否影响调用树？
- 帧、Binder、GC 与采样结论是否来自同一次录制？
- 结论是否区分 CPU 热点、墙钟耗时、等待时间和系统调度？

## 参考资料

- [Android 17 / API 37 Perfetto 源码锚点](https://android.googlesource.com/platform/external/perfetto/+/android-17.0.0_r1/)
- [android17-6.18-2026-06_r6 内核源码锚点](https://android.googlesource.com/kernel/common/+/android17-6.18-2026-06_r6/)
- [Perfetto v53.0 Release Notes](https://github.com/google/perfetto/releases/tag/v53.0)
- [Perfetto v54.0 Release Notes](https://github.com/google/perfetto/releases/tag/v54.0)
- [Perfetto v54 external trace formats](https://raw.githubusercontent.com/google/perfetto/v54.0/docs/getting-started/other-formats.md)
- [Perfetto v54 CPU profiling](https://raw.githubusercontent.com/google/perfetto/v54.0/docs/getting-started/cpu-profiling.md)
- [Android 17 pprof 导入源码](https://android.googlesource.com/platform/external/perfetto/+/android-17.0.0_r1/src/trace_processor/importers/pprof/pprof_trace_reader.cc)
- [Android 17 Simpleperf protobuf 导入源码](https://android.googlesource.com/platform/external/perfetto/+/android-17.0.0_r1/src/trace_processor/importers/simpleperf_proto/simpleperf_proto_parser.cc)
- [Android 17 `linux.perf.samples` 标准库](https://android.googlesource.com/platform/external/perfetto/+/android-17.0.0_r1/src/trace_processor/perfetto_sql/stdlib/linux/perf/samples.sql)
- [Android 17 Simpleperf `report-sample` 源码](https://android.googlesource.com/platform/system/extras/+/android-17.0.0_r1/simpleperf/cmd_report_sample.cpp)
