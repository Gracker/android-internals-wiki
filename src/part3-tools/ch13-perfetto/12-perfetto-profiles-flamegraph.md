---
title: "\"Perfetto Profile 导入与 Flamegraph 分析\""
chapter: "\"13.12\""
section: "\"13.12\""
status: "finalized"
pipeline_stage: "ready-to-publish"
applicable_versions: "\"Android 10 (API 29) - Android 17 (API 37)（Simpleperf 导入）；Android 15 (API 35) - Android 17 (API 37)（Perfetto linux.perf 采集，需 profileable/debuggable/userdebug）\""
tags: ["perfetto", "simpleperf", "pprof", "flamegraph", "profiling", "trace"]
confidence: "high"
last_verified: "\"2026-05-15\""
last_verified_against: "\"Perfetto v53/v54 release notes, perfetto.dev profiling/import/symbolization docs, Android simpleperf public docs snippets\""
drafted_date: "\"2026-05-15\""
drafted_by: "\"openclaw-task2a\""
reviewed_date: "\"2026-05-15\""
reviewed_by: "openclaw-task6"
path: "\"intake/research-feeds/2026-04-14-07-perfetto-v54-data-explorer-jank-cuj-heap-graph-stats.md\""
related_chapters: "[\"13.2\", \"13.3\", \"13.10\", \"14.2\", \"14.8\"]"
created_by: "\"task2a-knowledge-gap\""
created_date: "\"2026-05-15\""
gap_source: "\"研究素材/官方发布说明\""
deepseek_polish_state: "done"
last_deepseek_polish_at: "\"2026-05-26\""
task6_state: "\"reviewed\""
last_task6_at: "'2026-05-15T14:12:00+08:00'"
task6_result: "pass-light-edit"
task9_state: "reviewed"
task9_result: "pass-tech-review"
task2b_state: "fixed"
task2b_result: fixed
task9_reviewed_date: "\"2026-05-18\""
task9_reviewed_by: "\"openclaw-task9\""
last_task9_at: "\"2026-05-18T15:25:00+08:00\""
last_task9_audit: 2026-06-28
---

# 13.12 Perfetto Profile 导入与 Flamegraph 分析

<!-- outline-start -->
## 要点

### 🔹 Profile 与 system trace 的数据边界
区分 system trace、pprof、Simpleperf protobuf、Firefox Profiler 和 Collapsed Stack 的证据口径，避免用聚合 profile 替代帧级诊断。

### 🔹 pprof / Simpleperf 导入流程
说明 Perfetto v53/v54 对 pprof、Simpleperf protobuf 和 `traceconv profile` 的支持，以及调用链、符号和 mapping 的输入条件。

### 🔹 选区 Flamegraph 与 TrackEvent callstack
解释动态 flamegraph、TrackEvent callstack 和 CPU sample profile 的差异，强调必须按时间窗、线程和场景收窄。

### 🔹 符号化、inline function 与 R8 retracing
梳理 native 符号、Build ID、inline frame、R8 mapping 的还原边界，避免在符号缺失时下结论。

### 🔹 DataGrid / SQL / 大 Trace 工作流
把 DataGrid、SQL 标准库、FrameTimeline、Binder、GC 与 profile 样本联动起来，形成可复现的诊断流程。

## 扩展

### 🔸 Firefox Profiler / Collapsed Stack 互通
标注历史 profile 资产迁移能保留的信息与会丢失的 Android trace 语义。

### 🔸 Profile 与 FrameTimeline / Binder / GC 交叉分析
给出按照异常帧、跨进程等待和 GC 窗口回看 sample 的使用模板。

<!-- outline-end -->

Perfetto 过去更像系统 trace 的工作台：调度、Binder、FrameTimeline、GC、counter 都在同一条时间轴上。v53 之后，pprof profile 和 Simpleperf protobuf 也能直接进入 Perfetto UI，CPU sample profile 不再只停留在独立的火焰图工具里。本节讨论三件事：不同 profile 格式各自回答什么问题，导入 Perfetto 后怎样读 flamegraph，以及怎样把 sample 热点放回 trace 时间窗里验证。

## profile 与 system trace 的数据边界

system trace 和 CPU profile 的采样方式不同，结论口径也不同。system trace 记录的是事件区间和系统状态，例如线程什么时候 Running、什么时候 blocked、哪一帧超过预算；CPU profile 记录的是采样命中的调用栈，回答“CPU 时间更集中在哪些函数上”。

| 数据类型 | Perfetto 里的典型形态 | 适合回答的问题 | 边界 |
|---|---|---|---|
| Perfetto system trace | `slice`、`sched`、`thread_state`、`counter`、FrameTimeline | 某段卡顿发生在哪个时间窗，线程在跑、等锁、等 Binder 还是等 I/O | 调用栈通常不完整，除非录制时开启 perf callstack sampling 或 TrackEvent callstack |
| pprof profile | profile 专用页面或导入后的 sample flamegraph | 一个进程或线程的 CPU 热点分布，哪些函数累计 sample 多 | 聚合视角强，缺少 Android 系统事件上下文；没有时间轴时不能单独解释某一帧为什么卡 |
| Simpleperf protobuf | 由 `simpleperf report-sample --protobuf` 生成，Perfetto v53 起可 ingest | Android 原生采样 profile，能携带进程、线程、映射和符号信息 | 采样频率、符号、权限和混淆文件决定可读性；Java/Kotlin/native 混合栈要额外处理 |
| Firefox Profiler / Collapsed Stack | v54 Trace Processor 支持导入 | 跨工具互通、已有 flamegraph 资料迁移 | 通常会丢失部分 Android trace 语义，适合迁移和对照，不适合作为唯一证据 |

[已验证: Perfetto v53/v54 Release Notes, perfetto.dev other-formats/cpu-profiling docs]

一个实战判断：如果问题表现为“某个交互场景卡顿”，先抓 system trace，再在目标时间窗看 callstack；如果问题表现为“CPU 长时间占用高”，先抓 profile，再回到 trace 验证线程是否抢占了帧预算。两类数据要互相约束，不能用一张全局 flamegraph 直接替代帧级诊断。

## pprof / Simpleperf 导入流程

Perfetto v53 release notes 明确写到两项变化：UI 支持直接导入并可视化 pprof profile；同时支持 ingest Simpleperf 的 protobuf 格式。v54 又补了 `traceconv profile` 自动检测 profile type，减少手动指定格式的成本。

[已验证: Perfetto v53.0/v54.0 Release Notes]

Simpleperf 侧可以先录制 `perf.data`，再输出 protobuf。下面这段命令只展示数据流，包名、采样时长和符号目录要按项目替换：

```bash
# 目标：把 Android simpleperf 采样结果转成 Perfetto 可导入的 protobuf profile
python extras/simpleperf/scripts/app_profiler.py \
  --app com.example.app \
  -r "-g --duration 10" \
  -o perf.data

simpleperf report-sample \
  --protobuf \
  --show-callchain \
  -i perf.data \
  -o simpleperf.pb
```

`-g` 负责采集调用链，`--show-callchain` 决定输出里是否保留栈。缺少这两步时，Perfetto 里可能只剩 leaf sample，flamegraph 会退化成一层函数列表。[已验证: Android simpleperf public docs snippets + Perfetto other-formats docs]

Perfetto 自带的 `linux.perf` data source 更适合需要时间轴上下文的采集。下面这段配置把采样限制在目标进程，频率控制在 100Hz；Perfetto 文档建议 Android 上非 native 调用栈采样频率低于 200Hz，避免 unwinder 压力反过来干扰被测场景：

```protobuf
# 目标：在 Perfetto trace 内采集目标 App 的 callstack sample，便于和 sched / frame 数据同窗分析
duration_ms: 10000
buffers: { size_kb: 40960 fill_policy: DISCARD }

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
        scope { target_cmdline: "com.example.app" }
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
    process_stats_config { scan_all_processes_on_start: true }
  }
}
```

这份 trace 打开后，sample 会显示在进程 track 组内。选中包含 sample 的时间区域，底部面板会按选区聚合出 dynamic flamegraph。选区聚合的价值在于把热点限定在某一帧、某次 Binder 往返或某段 GC 前后。[已验证: Perfetto cpu-profiling docs]

`linux.perf` data source 的采集前提需要单独说明：Perfetto 官方文档标注 Android command line 路径要求 **Android 15+** 设备；在 user build 上还要求目标 App 声明 `profileable` 或 `debuggable`，或使用 userdebug/eng 系统镜像。Android 10-14 不支持 `linux.perf`，这个版本段的 CPU profiling 应走 Simpleperf protobuf 导入路径（`simpleperf report-sample --protobuf`），再在 Perfetto UI 中打开。章节适用范围因此要拆成两段：**Simpleperf 导入路径适用于 Android 10-17**；**Perfetto `linux.perf` callstack sampling 路径按官方文档标注 Android 15+、profileable/debuggable/userdebug 前提**。

导入失败通常要先检查输入文件是否缺关键字段：

- **只有一层函数**：录制时没有采集调用链，或 unwind 失败。先检查 simpleperf 是否用了 `-g`，Perfetto perf config 是否启用了 `callstack_sampling`。
- **函数名全是地址**：缺 unstripped ELF、Breakpad symbol 或 Build ID 不匹配。优先用 `traceconv bundle` 打包符号。
- **Java/Kotlin 名字被混淆**：缺 R8 / ProGuard `mapping.txt`，或 mapping 与设备上的 APK 版本不一致。
- **UI 能打开但时间轴无法对照**：输入是纯 pprof 或 collapsed stack，只有聚合 profile，没有系统 trace 的 FrameTimeline、sched 和 counter 上下文。

## TrackEvent callstack 与区域聚合

v53 的另一项变化，是转换 TrackEvent trace 时可以把 callstack 附到事件上。Perfetto UI 在选中一个区域后，会把区域内的 callstack 聚合成 flamegraph。它和 CPU sample profile 的区别在于：TrackEvent callstack 跟业务或工具转换出来的 slice 绑定，表达的是“这些事件发生时附带的调用栈”；CPU sample profile 绑定的是采样中断，表达的是“采样时 CPU 正在执行的栈”。

[已验证: Perfetto v53 Release Notes, perfetto.dev converting docs]

两者适合配合使用：

- **TrackEvent callstack**：适合 SDK、自定义 tracing、跨语言服务端 trace 转 Perfetto，能把函数栈挂到某类业务事件上。
- **perf / simpleperf sample**：适合定位 CPU 热点，能在没有手动插桩的 native/JIT 场景下采样。
- **system trace slice**：适合限定时间窗，例如只看某个 `Choreographer#doFrame`、某段 Binder transact 或某次 launch phase。

选区 flamegraph 的读法要保留时间边界。一个函数在全局 profile 里最高，不代表它导致了目标帧卡顿；要把选区缩到异常帧、异常线程和异常场景，再看 flamegraph 是否仍集中在同一条调用路径上。

## Flamegraph、inline function 与 R8 retracing

火焰图的横向宽度表示 sample 聚合数量，不是单次调用耗时。宽度越大，说明在选区内被采样命中的次数越多；它适合找 CPU 占用集中点，不适合直接证明某个函数“调用一次耗时 X ms”。单次耗时仍要回到 `slice.dur`、函数 trace slice 或方法级 instrumentation。

v53 支持在 pprof flamegraph 中区分 inline functions。这个能力对 Android native 性能分析很有用：编译器内联后，热函数可能不再以独立符号出现；如果 UI 能标出 inline frame，就能把“看不到函数”与“函数没有执行”分开。

[已验证: Perfetto v53 Release Notes]

v54 新增 R8 retracing during deobfuscation。配合 `traceconv bundle`，Perfetto 可以在打包 trace 时自动寻找 Gradle 标准路径下的 mapping 文件，也可以显式指定包名与 mapping：

```bash
# 目标：把 native 符号和 R8 mapping 打进 enriched trace，便于 UI 与 trace_processor_shell 读取
traceconv bundle \
  --symbol-paths /path/to/unstripped-symbols \
  --proguard-map com.example.app=/path/to/mapping.txt \
  raw-trace.perfetto-trace \
  enriched-trace
```

`traceconv bundle` 会校验 Build ID；符号文件和线上包不匹配时，即使路径存在也不会用于还原。Java/Kotlin 的 mapping 也必须来自同一构建产物，否则 retracing 会把同名短符号还原到错误类。[已验证: Perfetto symbolization/deobfuscation docs + v54 Release Notes]

阅读混合栈时按这个顺序排查：native 地址是否已符号化，APK/JAR mapping 是否还原，inline frame 是否展开，再判断热点属于 Java/Kotlin、JNI 边界、native library 还是系统库。不要在符号缺失时急着下结论；缺符号的火焰图只能说明“某个映射里有热点”，还不能说明是哪段代码。

## DataGrid 与 SQL 标准库补充

v54 把 profile 相关的输入格式和 SQL 能力又向前推了一步：Trace Processor 支持 Collapsed Stack、Firefox Profiler preprocessed JSON；SQL 标准库新增 `heap_graph_stats`、Jank CUJ、counter-based weighted jank metrics；UI 侧则增强 DataGrid、pivot table、glob filter 和 snap-to-boundaries。

[已验证: Perfetto v54 Release Notes]

| v54 能力 | 和本节的关系 | 使用建议 |
|---|---|---|
| Collapsed Stack format | 可导入 Brendan Gregg FlameGraph 体系的 `main;foo;bar 100` 文本 | 适合迁移旧 profile 资料；缺时间轴时只做热点参考 |
| Firefox Profiler preprocessed JSON | 可承接 Linux perf、Android simpleperf 转出的 Firefox profile | 适合跨工具对照；如果已有 Simpleperf protobuf，优先走 v53 原生导入 |
| R8 retracing | 提升 Java/Kotlin 混淆栈还原质量 | 和 `mapping.txt`、构建版本绑定，不能跨版本复用 |
| `heap_graph_stats` + dmabuf | 内存 profile 与图形内存统计更易查询 | 和 10.x、14.3、14.9 章节联动，分析 Camera / Bitmap / GPU 内存 |
| Jank CUJ 与 weighted jank metrics | 把 profile 热点和 CUJ 级 jank 指标放到同一分析框架 | 和 7.x、13.8、13.10 联动，用标准库替代手写重复 SQL |
| DataGrid / pivot / filter | 降低 SQL 结果探索成本 | 适合先快速分组，再把稳定查询固化到 13.10 的 SQL 模板 |

这些能力不替代 SQL 工作流。DataGrid（SQL table viewer）和 pivot table 适合探索数据结构，最终要复用的诊断结论仍应落成 SQL：目标进程、时间窗、线程、sample 数、帧预算和证据截图要能重复生成。

## 大 Trace 分析工作流

Profile 导入后，最常见的误判是盯着最高的 flamegraph frame 直接改代码。大 trace 应该按场景收窄：先定位异常时间窗，再定位线程，再聚合该窗口内的 sample，再决定要改哪段代码。

一个可复用流程如下：

1. **抓取时保留时间轴证据**：system trace 至少包含 `sched/sched_switch`、`sched/sched_waking`、目标 App 的 process stats；卡顿场景还要包含 FrameTimeline / gfx / view 相关数据。详见 13.2 节。
2. **确认 profile 输入质量**：Simpleperf 检查调用链、符号和 mapping；Perfetto perf 采样检查目标进程、频率和 sample 数。
3. **用 UI 找异常窗口**：从 FrameTimeline、launch phase、ANR 前窗口或用户操作标记定位 100ms 到数秒的范围。
4. **在窗口内看 flamegraph**：只聚合目标范围，观察 leaf frame、cumulative frame 和线程分布是否集中。
5. **回到 SQL 量化**：用 13.10 / 13.11 的 SQL 模板统计目标线程 Running 时长、blocked 时长、CPU 频率区间和 sample 分布。
6. **写结论时给边界**：说明采样频率、设备、build 类型、是否 profileable、是否完成符号和 R8 retracing。

下面这段 SQL 用于检查 Perfetto perf 采样是否足够支撑 flamegraph 结论。它不分析热点，只回答“目标窗口里每个线程有多少 sample”：

```sql
-- 目标：确认选区内 sample 数是否集中在目标线程，避免用样本不足的 flamegraph 下结论
INCLUDE PERFETTO MODULE linux.perf.samples;

WITH target_window AS (
  SELECT 10000000000 AS ts_start, 12000000000 AS ts_end
), target_process AS (
  SELECT upid
  FROM process
  WHERE name = 'com.example.app'
)
SELECT
  thread.name AS thread_name,
  COUNT(*) AS sample_count
FROM perf_sample
JOIN thread USING (utid)
JOIN target_process USING (upid)
JOIN target_window
WHERE perf_sample.ts >= target_window.ts_start
  AND perf_sample.ts < target_window.ts_end
GROUP BY thread.name
ORDER BY sample_count DESC;
```

如果目标窗口里只有十几个 sample，火焰图只能提供线索；如果 sample 主要落在非目标线程，也要重新确认场景是否选错。稳定结论至少要同时满足三点：异常窗口能复现，sample 聚合指向同一类调用路径，system trace 能解释它如何影响帧、启动或响应时间。

## 扩展：Firefox Profiler / Collapsed Stack 互通

v54 的 Firefox Profiler 和 Collapsed Stack 支持，解决的是历史 profile 资产迁移问题。Firefox Profiler JSON 能保留 CPU samples、thread/process 信息和部分 marker；Collapsed Stack 更轻，只保留“栈字符串 + 次数”。

[已验证: Perfetto v54 Release Notes, perfetto.dev other-formats docs]

信息丢失点要提前说明：Collapsed Stack 通常没有 Android 线程状态、Binder、FrameTimeline、CPU 频率和原始时间戳；Firefox Profiler JSON 的 marker 语义也不等同于 Android 系统 trace slice。它们适合回答“旧资料里的热点能不能在 Perfetto 里复读”，不适合直接回答“某一帧为什么掉”。

## 扩展：Profile 与 FrameTimeline / Binder / GC 交叉分析

Profile 与 system trace 的结合点在时间窗。FrameTimeline 给出异常帧，Binder slice 给出跨进程等待，GC slice 给出停顿区间，profile sample 再说明目标线程在窗口内把 CPU 花在哪里。

[自动发现] 一套简化模板是：

- **FrameTimeline → profile**：先选异常帧的 `ts + dur`，只看这段内主线程和 RenderThread 的 sample，确认 CPU 热点是否落在 layout/draw、Compose recomposition、bitmap decode 或业务计算。
- **Binder → profile**：先定位长 Binder transact，再看客户端线程是否在 CPU 上执行序列化/反序列化，服务端线程是否在同窗内有 CPU 热点。
- **GC → profile**：先定位 GC pause 或 allocation-heavy 窗口，再看 sample 是否集中在对象创建、集合扩容、JSON 解析或图片解码。

结论写法要把证据拆开：`slice.dur` 说明时间窗，`thread_state` 说明等待或运行状态，flamegraph 说明 sample 分布。三者一致时，才把它写成根因候选；三者不一致时，只能写成排查线索。

## 参考资料

- [已验证: 官方文档, Perfetto v53.0 Release Notes](https://github.com/google/perfetto/releases/tag/v53.0)
- [已验证: 官方文档, Perfetto v54.0 Release Notes](https://github.com/google/perfetto/releases/tag/v54.0)
- [已验证: 官方文档, Perfetto external trace formats](https://raw.githubusercontent.com/google/perfetto/main/docs/getting-started/other-formats.md)
- [已验证: 官方文档, Perfetto CPU profiling](https://raw.githubusercontent.com/google/perfetto/main/docs/getting-started/cpu-profiling.md)
- [已验证: 官方文档, Perfetto symbolization and deobfuscation](https://raw.githubusercontent.com/google/perfetto/main/docs/learning-more/symbolization.md)
- [来源: intake/research-feeds/2026-04-14-07-perfetto-v53-rust-sdk-pprof-simpleperf-custom-sorting.md]
- [来源: intake/research-feeds/2026-04-14-07-perfetto-v54-data-explorer-jank-cuj-heap-graph-stats.md]
