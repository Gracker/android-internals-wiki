---
title: "Perfetto SDK 与应用内 Trace 数据源"
chapter: "13.17"
section: "13.17"
status: ready-for-review
drafted_date: "2026-05-17"
applicable_versions: "Android 10 (API 29) - Android 17 (API 37)；system backend 依赖设备侧 traced 服务，低版本按设备能力降级"
last_verified: "2026-05-17"
last_verified_against: "Perfetto docs main / Android Developers tracing docs / external/perfetto main"
confidence: medium
sources:
  - type: official
    path: "https://perfetto.dev/docs/instrumentation/tracing-sdk"
  - type: official
    path: "https://perfetto.dev/docs/getting-started/in-app-tracing"
  - type: official
    path: "https://perfetto.dev/docs/design-docs/api-and-abi"
  - type: aosp
    path: "external/perfetto/docs/instrumentation/tracing-sdk.md"
  - type: official
    path: "https://developer.android.com/topic/performance/tracing/custom-events"
  - type: official
    path: "https://developer.android.com/topic/performance/tracing"
  - type: official
    path: "https://developer.android.com/topic/performance/tracing/profiling-manager/querying-profiles"
  - type: blog
    path: "/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/Cubox/性能工具-Perfetto(4)-通过SDK抓取信息-2026-05-02.md"
tags: [perfetto, tracing-sdk, in-app-tracing, custom-data-source, observability]
related_chapters: ["13.2", "13.9", "19.13", "26.3", "26.12"]
created_by: "task2a-knowledge-gap"
created_date: "2026-05-17"
gap_source: "素材驱动/官方文档"
gap_score: 16
material_count: 4
pipeline_stage: task9_pending
task6_state: reviewed
reviewed_by: openclaw-task6
reviewed_date: "2026-05-28"
task6_result: pass-light-edit
last_task6_at: "2026-05-28T08:10:00+08:00"
last_task6_review_log: "logs/review/2026-05-28-08-review.md"
task9_state: pending
task9_result: "needs-rework"
task2b_state: fixed
task2b_result: fixed-lite
last_task2b_lite_at: "2026-05-28"
task9_reviewed_date: "2026-05-17"
task9_reviewed_by: "openclaw-task9"
last_task9_at: "2026-05-17T10:20:00+08:00"
last_task9_review_log: "logs/deep-review/2026-05-17-10-deep-review.md"
task9_review_notes: "2026-05-17 10:20 Task9 deep-review: needs-rework。P0 0 / P1 3 / P2 0。Top: startup tracing 仅 kSystemBackend；Perfetto C API/ABI 稳定性未写清；ProfilingManager system trace 是请求进程脱敏结果，不能等同全设备/全进程 trace。"
task6_l1_l2_fixes: 0
task6_l3_l4_issues: 0
task6_reviewed_by: openclaw-task6
task6_reviewed_at: "2026-05-28T08:10:00+08:00"
task6_review_notes: "2026-05-28 08 Task6 revisiting-review: pass-light-edit；L1/L2 小修 0 处；outline 8/8 覆盖；无 L3/L4 回炉项。Task9 result 仍为 needs-rework，Task2B fixed-lite 后送 Task9 复核。"
---

# 13.17 Perfetto SDK 与应用内 Trace 数据源

<!-- outline-start -->
## 要点

### 🔹 Perfetto SDK 和 AndroidX Tracing 的边界
说明 `androidx.tracing`、平台 `android.os.Trace` 与 Perfetto SDK 的适用范围，帮助读者判断 Java / Kotlin 标记、Native `track_event` 和 custom data source 的边界。

### 🔹 in-process 后端的最小采集路径
覆盖 in-process backend 的初始化、`TrackEvent` 注册、采集配置、停止导出和事件写入，强调它只采集本应用事件。

### 🔹 system 后端与系统 Perfetto service 协作
解释应用作为 producer 与系统 Perfetto daemon 协作的方式，说明 system backend 能合并时间轴，但不能绕过系统级 trace 权限。

### 🔹 自定义 data source 的适用场景
区分 `track_event` 适合的时间轴问题与 custom data source 适合的结构化状态问题，给出 schema、消费工具和数据量三项检查。

### 🔹 启动早期 trace 与线上触发式采集
说明 startup tracing、短窗口触发和环形缓冲适合的场景，并把应用内事件与系统级事件的权限边界拆开。

### 🔹 构建、体积和版本兼容边界
覆盖 Perfetto SDK 的接入形态、C++17、ABI、初始化时机、低版本降级，以及 C SDK / C++ SDK 的选择依据。

### 🔹 隐私和数据治理
说明 trace 数据的隐私风险，约束 category、event、调试注解、counter、导出流程和系统 trace 的数据边界。

### 🔹 Perfetto SDK、ProfilingManager、APM 自定义 trace 的组合方案
按开发期、性能专项、灰度线上、系统内测四种环境拆分采集方式、适用数据和产物。

## 扩展

### 🔸 待复核项
记录 Android 17 上 Perfetto SDK 与 `ProfilingManager` 的 session 关系、C SDK 包体积增量、自定义 data source 的 PerfettoSQL 样例三类后续验证点。
<!-- outline-end -->

Perfetto SDK 解决的是应用内部事件如何进入 Perfetto trace 的问题。它适合把 C / C++ 模块、游戏引擎、Native 渲染管线、端侧推理模块的区间和计数器放进同一份 `.pftrace`，让系统调度、Binder、渲染和应用自定义事件能在同一条时间轴上分析。读完这一节，应该能判断什么时候继续用 `android.os.Trace` / `androidx.tracing`，什么时候引入 Perfetto SDK，以及线上采集时不能越过哪些权限和隐私边界。

[已验证: 官方文档, perfetto.dev/docs/instrumentation/tracing-sdk]

## Perfetto SDK 和 AndroidX Tracing 的边界

`androidx.tracing` 和平台 `android.os.Trace` 的定位很窄：给 Java / Kotlin 代码区间打 trace section，并通过 Android 的 atrace 数据源进入系统 trace。Macrobenchmark、Perfetto 命令行抓取、Android Studio 采样都能读取这些标记。Java / Kotlin 页面、RecyclerView、启动初始化这类场景，用它就够了。详见 19.13 节。

Perfetto SDK 的入口在 Native 侧。官方文档把它定义为 C++17 userspace tracing library，用来让应用发出 trace events，并为 Perfetto trace 增加应用上下文。它给应用提供两类数据表达：

- `track_event`: 记录区间、异步区间、计数器、调试参数。多数应用内追踪先选它，配置成本低，Perfetto UI 和 Trace Processor 都能直接消费。
- custom data source: 用 protobuf schema 写入强类型数据，适合把子系统状态快照、引擎内部队列、水位或调度决策写成结构化 trace packet。

这两个层级不是互斥关系。`track_event` 负责时间轴上最常见的切片和计数器；custom data source 负责 Perfetto 原生数据源覆盖不到的结构化状态。

[已验证: AOSP external/perfetto/docs/instrumentation/tracing-sdk.md]

选择时按这张表判断：

| 场景 | 更合适的工具 | 判断依据 |
| --- | --- | --- |
| Java / Kotlin 方法耗时、页面生命周期、启动阶段普通标记 | `androidx.tracing` / `android.os.Trace` | 平台 API 足够，Macrobenchmark 可自动收集，接入成本最低 |
| Native 模块区间、游戏引擎帧阶段、C++ 推理管线 | Perfetto SDK `track_event` | 事件源在 Native 侧，想要 category、counter、debug annotation（调试注解）和 PerfettoSQL 分析 |
| 应用事件要和 ftrace、调度、Binder 放在同一条时间轴 | Perfetto SDK system backend 或平台 atrace | 采集由外部 Perfetto consumer 控制，应用只提供 producer 事件 |
| 需要写入自定义 protobuf，后续用 Trace Processor 或自研解析器分析 | Perfetto SDK custom data source | `track_event` 的区间和计数器表达不够，需要强类型数据 |
| 普通线上 SDK 想远程读取整机 ftrace、logcat、其他进程信息 | 不应承诺为应用内能力 | 这些属于系统级诊断边界，详见 26.12 节 |

## in-process 后端的最小采集路径

in-process backend 把 Perfetto service 和应用 data source 放在同一进程内，不连接系统 `traced` 守护进程。它只采集本应用写出的事件，不包含 ftrace、syscalls、调度等系统数据。这个模式适合开发期自测、Native 模块单元验证、SDK 内部可控采样，也适合把 `.pftrace` 文件作为复现材料附到 bug report。

[已验证: 官方文档, perfetto.dev/docs/instrumentation/tracing-sdk]

这段代码展示 in-process 模式的最小路径，读代码时看四个动作：初始化 backend、注册 `TrackEvent`、配置 `track_event` data source、停止后读取 trace。

```cpp
#include <fstream>
#include <memory>
#include <perfetto.h>

PERFETTO_DEFINE_CATEGORIES(
    perfetto::Category("rendering")
        .SetDescription("Events from the rendering subsystem"));
PERFETTO_TRACK_EVENT_STATIC_STORAGE();

void InitPerfetto() {
  perfetto::TracingInitArgs args;
  args.backends |= perfetto::kInProcessBackend;
  perfetto::Tracing::Initialize(args);
  perfetto::TrackEvent::Register();
}

std::unique_ptr<perfetto::TracingSession> StartAppTrace() {
  perfetto::TraceConfig cfg;
  cfg.add_buffers()->set_size_kb(1024);

  auto* ds_cfg = cfg.add_data_sources()->mutable_config();
  ds_cfg->set_name("track_event");

  auto session = perfetto::Tracing::NewTrace();
  session->Setup(cfg);
  session->StartBlocking();
  return session;
}

void StopAppTrace(std::unique_ptr<perfetto::TracingSession> session) {
  perfetto::TrackEvent::Flush();
  session->StopBlocking();
  std::vector<char> data = session->ReadTraceBlocking();
  std::ofstream("app-only.pftrace", std::ios::binary)
      .write(data.data(), data.size());
}

void DrawFrame() {
  TRACE_EVENT("rendering", "DrawFrame");
  TRACE_COUNTER("rendering", "FrameIndex", 42);
  // Rendering work omitted.
}
```

这份 trace 打开后只会出现应用写入的 `rendering` category。它不会自动带出 CPU 调度、Binder 调用或 SurfaceFlinger 事件；要看系统视角，需要切到 system backend，或使用 13.2 节的 Perfetto 命令行抓取。

## system 后端与系统 Perfetto service 协作

system backend 把应用写入的事件送到系统 Perfetto daemon。应用在这里扮演 producer：注册 data source，等待外部 trace session 选择是否启用。采集的开始、停止、buffer 大小、是否同时打开 ftrace，由外部 Perfetto CLI、Android Studio、系统工具或受控诊断通道决定。

[已验证: 官方文档, perfetto.dev/docs/instrumentation/tracing-sdk]

system backend 的价值在于合并时间轴。Native 模块写出的 `TRACE_EVENT("rendering", "DrawFrame")` 可以和 `sched_switch`、Binder transaction、SurfaceFlinger slice 一起分析，避免只看应用日志时丢掉线程迁移、CPU 抢占和系统服务等待。

这类配置文件展示了应用 `track_event` 与 ftrace 同采的思路。`linux.ftrace` 给出系统调度事件，`track_event` 接收应用 producer 事件。

```protobuf
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
      buffer_size_kb: 16384
    }
  }
}

data_sources {
  config {
    name: "track_event"
    track_event_config {
      enabled_categories: "rendering"
      disabled_categories: "*"
    }
  }
}

duration_ms: 10000
write_into_file: true
```

这份配置的前提是设备侧有权限启动系统级 trace session。普通第三方应用不应把 system backend 解读成“应用可以读取整机 trace”。它能提供事件，不能替代 adb、系统签名、`profileable` / `debuggable`、Android 15+ `ProfilingManager` 等权限模型。线上诊断方案要在协议里写清能力检查、失败回执和降级路径，详见 26.12 节。

## 自定义 data source 的适用场景

`track_event` 适合时间轴问题：某段代码什么时候开始、持续多久、当时 counter 是多少。custom data source 适合状态问题：队列里有多少任务、调度器把帧分到哪个阶段、推理运行时选择了哪个 delegate、缓存池水位如何变化。

[已验证: AOSP external/perfetto/docs/instrumentation/tracing-sdk.md]

引入 custom data source 前先过三条检查：

- 数据必须有稳定 schema：字段名、枚举值、单位和版本兼容规则要能长期维护，不能把它当成任意日志字符串。
- 数据要能被 Trace Processor 或内部工具消费：如果后续仍靠人工肉眼读文本，`track_event` 的 `debug annotation` 往往更省成本。
- 数据量要可控：高频状态快照会挤占 trace buffer，必须按 category、采样率或触发窗口限制。

适合 custom data source 的例子是 Native 渲染引擎的帧调度状态：每帧包含 frame id、stage、queue depth、target timestamp、deadline miss reason。`track_event` 能画出阶段耗时，但很难把这些字段作为强类型列稳定查询。custom data source 能把字段写进 protobuf，再用 PerfettoSQL 做聚合。

不适合的例子是业务日志。用户 id、订单号、请求 URL、异常堆栈原文不应直接进入 trace。trace 会被上传、转发、归档，字段名和参数值都要按隐私数据处理。

## 启动早期 trace 与线上触发式采集

启动早期事件的难点是 trace session 还没建立，Native 初始化、引擎加载、SoLoader、JNI 注册可能已经跑完。Perfetto SDK 提供 startup tracing 方案，但官方 `example_startup_trace.cc` 走的是 `kSystemBackend`：进程初始化后设置 startup tracing，早期 data source 事件先写入，外部 system trace session 建立后再统一导出。in-process backend 只在应用进程内控制 session 生命周期，不应承诺缓存 session 建立前事件。

[已验证: 官方文档, perfetto.dev/docs/instrumentation/tracing-sdk]

这组方案要拆开看：

- 冷启动首屏：Native 运行时、引擎初始化、资源预热在 Java 层 trace 建立前已经发生，需要把它们补进启动时间轴。
- 短窗口触发：只在卡顿、超时、异常前后开启数秒 trace，减少常开成本；这不等同 startup tracing。
- 环形缓冲：低频记录关键状态，高危事件发生后停止并导出窗口内数据；它依赖预先存在的采集会话或应用内缓冲。

线上触发式采集要拆成两层。应用内事件可以由 SDK 自己写，trace 是否导出要受采样率、用户授权、文件大小、网络状态和隐私策略控制。系统级事件不能由普通应用私自读取；如果需要系统调度、ftrace、全进程信息，应走内测 adb、系统签名工具、Android 15+ 公开 profiling API，或者由用户显式触发 bug report。

## 构建、体积和版本兼容边界

Perfetto SDK 发布包通常以两个 amalgamated 文件接入：`perfetto.h` 和 `perfetto.cc`。C++ SDK 需要 C++17 标准库，CMake 中一般把 `perfetto.cc` 编成静态库，再链接到应用或 Native 模块。Cubox 素材里的 v54 示例也采用这种路径：下载 release zip，把 SDK 链到示例目录，编出 `example`、`example_system_wide`、`example_custom_data_source`、`example_startup_trace` 等二进制。[来源: obsidian/Cubox/性能工具-Perfetto(4)-通过SDK抓取信息-2026-05-02.md]

[已验证: 官方文档, perfetto.dev/docs/getting-started/in-app-tracing]

工程接入时重点看四个成本：

- 编译成本：`perfetto.cc` 是单文件聚合实现，增量编译会受影响。大型工程可以单独做成静态库，避免业务模块反复编译它。
- ABI 成本：Android 端要按目标 ABI 打包 Native 库。接入前要确认 `arm64-v8a`、`armeabi-v7a`、`x86_64` 等产物策略和包体积预算。
- 初始化时机：`Tracing::Initialize()` 和 `TrackEvent::Register()` 要早于事件写入。启动期采集要把初始化放到 Native 模块入口或进程早期初始化位置。
- 低版本降级：Android 10 以后系统 trace 文件使用 Perfetto 格式；系统 backend 还依赖设备上的 `traced` 能力和抓取权限。低版本或权限不足时，保留 `android.os.Trace` / `ATrace_*` 标记，保证线下工具仍能看到基础区间。

C SDK 和 C++ SDK 的差异可以按团队语言栈判断。纯 C / Rust FFI / 需要最小 ABI 面的模块才考虑 `include/perfetto/public` C API/ABI；Perfetto 官方 API/ABI 文档仍把这层标为 not stable yet，生产接入要锁定 SDK revision 并把升级验证写进构建流程。已有 C++17 工程、需要 `TrackEvent` category、counter、`debug annotation`、custom data source 的模块优先走 C++ SDK。不要为了“统一工具”把 Java/Kotlin 业务层全部迁到 Perfetto SDK，平台 trace API 已经能覆盖大部分应用层区间。

## 隐私和数据治理

trace 数据比日志更容易暴露上下文，因为它把时间、线程、进程、函数名、参数、counter 和系统状态放在同一份文件里。Perfetto SDK 事件进入 `.pftrace` 后，分析者可以按线程、category、参数过滤，也可以用 PerfettoSQL 批量查询。写入前就要把字段当作可上传诊断材料设计。

[已验证: 官方文档, developer.android.com/topic/performance/tracing/custom-events]

应用内 trace 至少遵守这几条规则：

- category 名称只描述技术模块，例如 `rendering`、`network_scheduler`、`ml_runtime`，不包含用户、租户、实验组或业务单号。
- event 名称保持稳定，避免拼接动态参数。`DrawFrame` 比 `DrawFrame_user_123` 安全，也更适合 PerfettoSQL 聚合。
- `debug annotation` 只写低敏技术值，例如 frame id、queue depth、buffer size、stage enum。URL、手机号、token、地理位置、原始请求体不能写入 trace。
- counter 要有单位和范围。没有单位的 `cost=123` 在后续分析里价值很低，也容易被误读。
- 线上导出 trace 前做大小限制、脱敏、加密传输、保留期控制和用户授权记录。

系统 trace 的权限边界更严。合并 ftrace 和其他进程数据的 `.pftrace` 可能包含全设备行为，普通应用不能把它当作自身数据读取、上传或长期保存。

## Perfetto SDK、ProfilingManager、APM 自定义 trace 的组合方案

Perfetto SDK 不是 APM 的替代品。它负责把应用事件写成 Perfetto 原生数据；APM 负责采样、触发、上传、去重、归档和告警；`ProfilingManager` / `ProfilingTrigger` 负责 Android 15+ 的平台公开 profiling 入口。`ProfilingManager` 返回的是请求应用相关的 redacted 结果，不能当作 adb 或系统签名工具可拿到的全设备 trace。三者组合时按环境拆分：

| 环境 | 采集方式 | 适用数据 | 产物 |
| --- | --- | --- | --- |
| 开发期 | in-process Perfetto SDK + 手动导出 `.pftrace` | Native 模块区间、counter、custom data source | 本地 Perfetto UI / Trace Processor 分析 |
| 性能专项测试 | system backend + 外部 Perfetto CLI / Android Studio | 应用事件 + ftrace + Binder + 渲染数据 | 同机复现 trace，配合 13.2、13.9 节分析 |
| 灰度/线上 | APM 触发策略 + 应用内 `track_event` 摘要 + 受控 profiling API | 低频、低敏、短窗口证据 | 事件摘要、分位值、必要时受控 trace 文件 |
| 系统/内测版本 | 系统签名或 adb 通道启动系统级 trace | 调度、系统服务、跨进程数据 | 完整 `.pftrace`，仅限授权环境 |

26.3 节负责性能指标上报，26.12 节负责版本化诊断能力。13.17 的位置更靠近工具层：它讲清应用如何成为 Perfetto producer，以及 producer 能写什么、不能读什么。

## 待复核项

- [待验证] Android 17 设备上 Perfetto SDK system backend 与 `ProfilingManager` 同时使用时，trace session 冲突、buffer 归属和文件导出策略是否有公开限制。
- [待补充] Perfetto C SDK 在 Android NDK 多 ABI 工程中的包体积增量，需要用真实 release 构建测量。
- [待补充] 自定义 data source 的 PerfettoSQL 解析样例，可以在后续章节用一个 Native 渲染队列或端侧推理队列做完整演示。

## 参考资料

- [已验证: 官方文档, perfetto.dev/docs/instrumentation/tracing-sdk]
- [已验证: 官方文档, perfetto.dev/docs/getting-started/in-app-tracing]
- [已验证: AOSP external/perfetto/docs/instrumentation/tracing-sdk.md]
- [已验证: 官方文档, developer.android.com/topic/performance/tracing/custom-events]
- [已验证: 官方文档, developer.android.com/topic/performance/tracing]
- [来源: obsidian/Cubox/性能工具-Perfetto(4)-通过SDK抓取信息-2026-05-02.md]
