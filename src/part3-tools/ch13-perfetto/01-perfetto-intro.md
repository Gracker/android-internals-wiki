---
title: "Perfetto 简介与演进"
chapter: "13.1"
section: "13.1"
status: ready-for-review
drafted_date: "2026-04-03"
applicable_versions: "Android 10 (API 29) - Android 16 (API 36)"
last_verified: "2026-04-03"
last_verified_against: "perfetto.dev docs"
confidence: medium
sources:
  - type: official
    path: "https://perfetto.dev/docs/"
  - type: official
    path: "https://source.android.com/docs/core/debug/perfetto"
  - type: blog
    path: "https://www.androidperformance.com/2019/12/01/Android-Systrace(Perfetto)-Basic/"
tags: ['perfetto', 'systrace', 'tracing', 'performance-analysis']
related_chapters: ["13.2", "13.3", "2.1", "7.1"]
---

# Perfetto 简介与演进

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 Perfetto 是什么：Google 的下一代系统级 tracing 工具，Systrace 的继任者
- 🔹 Perfetto 与 Systrace 的关系与区别
- 🔹 Perfetto 的架构：traced（守护进程）、traced_probes（数据源）、Perfetto UI
- 🔹 核心概念：TraceConfig、Data Source、Track、Slice、Counter
- 🔹 为什么性能分析离不开 Perfetto

### 扩展（可选深入）

- 🔸 Perfetto 在 Chrome / Linux 上的跨平台支持
- 🔸 Perfetto SDK 嵌入 App 的能力（Custom Data Sources）

### OpenClaw 加工指引

> **锚点**是最低覆盖要求，加工时必须逐条落实并标注验证结果。
> **扩展**视素材丰富程度选择性深入。
> 如果从 Obsidian 素材或 AOSP 源码中发现大纲未列出但与本节强相关的知识点，
> 可**就地插入**最相关的锚点之后，并用 `[自动发现]` 标注，方便后续 review。
> 锚点内容需 L1/L2 验证，扩展内容至少 L2 验证，自动发现内容至少标注来源。
<!-- outline-end -->

## 为什么要了解 Perfetto

如果你做过 Android 性能优化，你一定遇到过这样的场景：App 明明卡了，但拿到的日志毫无头绪；滑动掉帧了，却不知道时间花在哪里；ANR 堆栈指向的是 Binder 调用，但你不知道对端进程在做什么。这些问题有一个共同特征——它们跨越了多个进程、多个线程、甚至多个系统层级，单看任何一个进程的日志都无法拼出完整图景。

Perfetto 就是解决这类问题的工具。它给你的是整个系统的"上帝视角"：所有进程的 CPU 调度、所有线程的状态、内核的事件、图形管线的每一帧、内存的变化曲线——全部对齐在同一根时间线上。有了这根时间线，你可以像看监控录像一样，逐帧还原系统在任何一个时间窗口里发生了什么。

如果你之前用的是 Systrace，那么 Perfetto 是它的继任者，能力是 Systrace 的严格超集。如果你之前没有用过任何系统级 tracing 工具，那么 Perfetto 就是你应该从现在开始掌握的工具。

## Perfetto 是什么

Perfetto 是 Google 开源的、生产级的系统级 tracing 平台。它最初为 Android 设计，但现在已覆盖 Android、Linux 和 Chrome 三个平台。自 Android 10（API 29）起，Perfetto 正式取代 Systrace 成为 Android 的默认 tracing 系统。[已验证: 官方文档, source.android.com/docs/core/debug/perfetto]

Perfetto 不是单一工具，而是一整套 tracing 基础设施，包含三个核心模块：

- **采集层**：负责从系统各处收集 trace 数据，包括内核的 ftrace 事件、用户空间的 atrace 标注、/proc 和 /sys 文件的轮询数据、以及 App 自定义的 trace 事件。
- **分析层**：基于 SQL 的 trace 分析引擎（Trace Processor），可以用结构化查询语言对 trace 数据做任意维度的分析。
- **可视化层**：Web 端的 Perfetto UI（ui.perfetto.dev），支持打开数 GB 的大型 trace 文件，完全在浏览器本地运行，无需上传数据。

这三层是解耦的——你可以只用采集层把数据抓到文件里，用 Trace Processor 写 SQL 查询；也可以只用 UI 打开别人给你的 trace 文件做可视化分析。

## 从 Systrace 到 Perfetto：为什么要换

Systrace 是 Android 4.1（2012 年）引入的 tracing 工具，它基于 Linux 内核的 ftrace 机制和用户空间的 atrace 注解来收集系统事件，最终生成一个可以在 Chrome 中查看的 HTML 报告。在很长一段时间里，Systrace 是 Android 性能分析的标配工具。

但 Systrace 有几个根本性的限制，这些限制在实际工作中会让你非常难受：

**第一，只能抓很短的时间。** Systrace 把所有数据先写进内存缓冲区，结束时一次性输出到文件。这意味着 trace 时长受限于内存大小——通常只能抓 10-30 秒。如果你想复现一个需要操作好几分钟才会出现的问题，Systrace 根本帮不了你。

**第二，数据源有限。** Systrace 主要依赖 ftrace 和 atrace，覆盖的是 CPU 调度、Binder 调用、图形管线等基础事件。如果你想看内存分配细节、Java 堆的使用情况、或者每个硬件子系统的功耗——对不起，Systrace 不支持。

**第三，分析能力薄弱。** Systrace 的 HTML 报告是一个"所见即所得"的视图，你能做的操作就是缩放、点选、看信息面板。没有办法对数据做聚合、过滤、统计。面对一个包含几百个进程的 trace 文件，你只能靠肉眼在时间线上来回滚动，效率极低。

Perfetto 从架构层面解决了这三个问题。它用一个后台守护进程（`traced`）把数据边采集边写盘，所以 trace 时长几乎没有上限；它支持十几种数据源，从内核事件到 Java 堆 Profiling 再到硬件功耗计数器都覆盖；它内置了 SQL 分析引擎，你可以用 `SELECT` 语句对 trace 数据做任意查询，就像操作数据库一样。

下表总结了二者的关键差异：

| 维度 | Systrace | Perfetto |
|------|---------|---------|
| 引入版本 | Android 4.1 (2012) | Android 10 (2019) |
| 采集时长 | 通常 10-30 秒 | 任意时长（受磁盘空间限制） |
| 数据格式 | 压缩文本（JSON） | Protocol Buffers 二进制流 |
| 后台服务 | 无（进程退出即结束） | traced 守护进程 |
| 数据源 | ftrace + atrace | ftrace + atrace + heapprofd + Java 堆 + /proc + /sys + 功耗 + 自定义 |
| 分析方式 | HTML 报告（只读浏览） | SQL 查询 + Web UI + 脚本 |
| UI 承载能力 | 大 trace 文件会卡顿/崩溃 | 可流畅打开数 GB 文件 |
| 跨平台 | 仅 Android | Android + Linux + Chrome |
| 状态 | 已停止维护 | 活跃开发中 |

[已验证: 官方文档, perfetto.dev/docs/#systrace-vs-perfetto]

还有一个重要的兼容性细节：Perfetto UI 可以直接打开 Systrace 格式的 trace 文件。这意味着你之前积累的 Systrace 文件不需要丢弃，全部可以在 Perfetto UI 中继续分析。反过来，Perfetto 也提供了 `traceconv` 工具，可以把 Perfetto 格式的 trace 转换为 Systrace 文本格式。

## Perfetto 的架构

理解 Perfetto 的架构，有助于你在遇到问题时知道是哪个环节出了差错。Perfetto 的整体架构可以用一句话概括：**多个 Producer 往共享内存里写数据，一个 Service 管理调度和缓冲，一个或多个 Consumer 发起采集请求并读取结果。**

[图：Perfetto 架构示意图——Producer → Shared Memory → traced (Service) → Trace Buffer → Consumer → 输出文件]

### traced：核心守护进程

`traced` 是 Perfetto 的核心服务进程，在系统启动时由 init 进程拉起。它做两件事：

- **管理采集会话**：接收 Consumer 的配置（TraceConfig），按配置激活各个 Data Source，管理数据缓冲区的生命周期。
- **路由数据**：各个 Producer 写入共享内存的 trace 数据，由 `traced` 汇聚到主缓冲区（Trace Buffer），最终根据配置写出到文件。

如果 `traced` 进程没有运行（比如被手动 kill 了），Perfetto 的"正常模式"（normal mode）就无法工作。这时候系统会回退到"轻量模式"（light mode），只使用 atrace + ftrace 的子集功能，等价于一个简化版的 Systrace。[已验证: 官方文档, source.android.com/docs/core/debug/perfetto]

从 Android 11 开始，`traced` 默认启用，无需手动配置。在 Android 9 和 10 上，需要手动启动或通过开发者选项启用。

### traced_probes：系统数据源代理

`traced_probes` 是另一个系统服务，它负责采集那些需要特权访问的系统级数据源——具体来说，是 ftrace（内核事件）和 /proc、/sys 文件系统的轮询数据。

为什么不直接让 `traced` 来采集？因为 `traced` 以普通用户权限运行，而读取 ftrace 和某些 /proc、/sys 节点需要 root 或 system 权限。`traced_probes` 以更高的权限运行，专门负责这些特权数据源的采集，采集到的数据通过共享内存传递给 `traced`。

`traced_probes` 支持的主要数据源包括：

- **ftrace**：内核级事件，如 CPU 调度（sched_switch、sched_wakeup）、系统调用、中断等。这是 trace 中 CPU 行为数据的来源。
- **atrace**：用户空间标注事件，Android Framework 和 App 通过 `android.os.Trace` API 写入的事件。
- **/proc 和 /sys 轮询器**：定期采样进程级别的 CPU 使用率、内存使用量、系统级计数器等。
- **功耗计数器**：从 Android 10 开始，集成了电池和能耗相关的硬件计数器，包括总电流和 ODPM（On-Device Power Rails Monitor，各硬件子系统的独立功耗）。

[已验证: 官方文档, perfetto.dev/docs/data-sources]

这些数据源默认是空闲状态——只有在显式启动一次 trace 采集时才会激活。这和一直开着日志系统不同，Perfetto 不会在你不需要的时候产生任何开销。

### Perfetto UI：可视化界面

Perfetto UI 是一个纯前端的 Web 应用，托管在 ui.perfetto.dev，但所有数据都在浏览器本地处理，不会上传到任何服务器。它基于 WebAssembly 和 Web Workers 实现，可以在浏览器中流畅地打开和渲染数 GB 大小的 trace 文件。

在 UI 中，你会看到：

- **时间线视图**：每个进程、每个线程、每个 CPU 核心对应一条水平轨道（Track），轨道上的色块代表事件（Slice）。
- **计数器图表**：CPU 频率、内存使用量等随时间变化的数值，以折线图的形式叠加显示。
- **SQL 查询面板**：直接在 UI 中写 SQL 语句查询 trace 数据，结果以表格形式返回。

我们将在 13.3 节详细介绍 Perfetto UI 的使用方法。

### Trace Processor：SQL 分析引擎

Trace Processor 是 Perfetto 的分析核心。它把二进制的 trace 文件解析后加载为一个 SQLite 数据库，你可以用标准 SQL 对其中的数据进行查询。这比在 UI 上手动点选要强大得多——你可以写脚本自动化分析流程，也可以批量处理大量 trace 文件。

例如，你想统计某个 trace 中所有帧的耗时分布，一条 SQL 就能搞定：

```sql
SELECT
  name,
  COUNT(*) as frame_count,
  AVG(dur) / 1e6 as avg_ms,
  MAX(dur) / 1e6 as max_ms
FROM slice
WHERE name LIKE 'doFrame%'
GROUP BY name;
```

Trace Processor 可以通过命令行工具（`trace_processor_shell`）使用，也可以嵌入到你自己的分析脚本中。我们将在后续章节中详细讲解其用法。

## 核心概念

在使用 Perfetto 之前，我们需要搞清楚几个核心概念。这些概念贯穿了 Perfetto 的采集、分析和可视化三个阶段。

### TraceConfig：采集的"剧本"

每一次 trace 采集都由一个 TraceConfig 来定义。TraceConfig 是一个 Protocol Buffer 消息，它告诉 Perfetto：

- **开启哪些数据源**：比如 ftrace 中要记录哪些事件（sched、power、freq...），atrace 中要启用哪些 tag（gfx、view、input...），是否开启堆 Profiling 等。
- **缓冲区配置**：缓冲区大小、数量，以及每个数据源写入哪个缓冲区。
- **采集时长**：持续多长时间，或者在什么条件下停止。
- **输出方式**：数据写到哪里——文件、Dropbox（Android 的 dropbox 机制），还是通过 IPC 流式传递给 Consumer。

通常你不需要手写 TraceConfig 的 protobuf 文本。在 Android 设备上，通过开发者选项的"系统追踪"抓取时，系统会自动生成配置；使用 `perfetto` 命令行工具时，可以通过 JSON 配置文件或命令行参数来指定；Perfetto 官网也提供了一个交互式的配置生成器。

### Data Source：数据的来源

Data Source 是 Perfetto 中数据采集的抽象单位。每个 Data Source 代表一类可采集的数据。我们已经提到了 ftrace、atrace、/proc 轮询器等系统级数据源。除此之外，Perfetto 还支持：

- **heapprofd**：Native 内存 Profiling，追踪 malloc/free 调用。从 Android 10 开始支持。
- **java_hprof**：Java 堆 Profiling，从 Android 11 开始支持。
- **android.log**：将 logcat 日志写入 trace，方便在时间线上对照系统事件和日志。
- **perf（Linux perf events）**：CPU Profiling，通过采样调用栈来定位热点函数。

每个 Data Source 在运行时由一个 Producer 负责实际采集。系统级数据源的 Producer 通常是 `traced_probes`，而 App 自定义的 Data Source 则由 App 进程自己充当 Producer。

### Track：时间线上的一条轨道

打开 Perfetto UI，你会看到很多水平排列的轨道——每个进程一条、每个线程一条、每个 CPU 核心一条。这些轨道就是 Track。

Track 是事件的容器。属于同一类上下文的事件被组织到同一个 Track 上。例如：

- 一个线程的所有 trace 事件（measure、layout、draw 等）在同一个线程 Track 上。
- 每个 CPU 核心的调度事件（哪个进程在运行、运行了多久）在对应的 CPU Track 上。
- 系统级的计数器数据（CPU 频率、内存用量）有各自独立的 Counter Track。

Track 的组织方式是分层的：进程 Track 是父 Track，线程 Track 是子 Track。在 UI 中，你可以展开/折叠进程来查看/隐藏其下的线程 Track。

### Slice：时间段内的事件

Slice 是 Perfetto 中最常见的事件类型。它代表一个有开始、有结束的时间段操作。在 UI 中，Slice 显示为轨道上的色块——色块的长度代表持续时间，颜色和标注代表事件类型。

一个典型的例子是 `Choreographer#doFrame`。当主线程执行一帧的渲染工作时，这个 Slice 从 VSync 回调开始，到渲染完成结束。它的内部可能包含多个子 Slice：`measure`、`layout`、`draw`、`syncAndDrawFrame` 等，形成嵌套结构。

```
Choreographer#doFrame (16.2ms)
  ├── measure (2.1ms)
  ├── layout (1.8ms)
  └── draw (10.3ms)
       ├── syncAndDrawFrame (1.2ms)
       └── RenderThread (8.5ms)
```

通过分析 Slice 的嵌套关系和持续时间，你就能定位一帧的耗时花在了哪个环节。这是 Perfetto 性能分析中最常用的基本操作。

### Counter：随时间变化的数值

Counter 记录的是一个数值随时间的变化。和 Slice 不同，Counter 没有明确的开始和结束——它是对某个指标的连续采样。

在 Perfetto UI 中，Counter 以折线图的形式显示。常见的 Counter 包括：

- CPU 频率（每个核心独立追踪）
- 进程的内存使用量（RSS、PSS）
- 线程的 CPU 使用率
- 硬件功耗计数器

Counter 和 Slice 通常配合使用。比如你发现某帧的 `doFrame` Slice 特别长（卡顿），同时看到对应的 CPU 频率 Counter 在那个时间段很低——那很可能是因为 CPU 降频导致了渲染超时。

## 为什么性能分析离不开 Perfetto

如果你还在用 log + 断点的方式做性能分析，你可能觉得 Perfetto 的学习曲线有点陡。但一旦你掌握了它，你会发现几乎所有性能问题都能在 trace 中找到答案。原因很简单：**性能问题的本质是"时间花在了不该花的地方"，而 Perfetto 给你的是系统中所有维度的精确时间记录。**

具体来说，Perfetto 在以下场景中不可替代：

**流畅性分析。** 掉帧、卡顿的本质是某帧的渲染超时。Perfetto 可以让你看到每一帧从 VSync 到上屏的完整流程——Choreographer 的 doFrame 用了多久、RenderThread 耗时多少、SurfaceFlinger 合成是否及时。这些信息分散在 App 进程、system_server 进程和 SurfaceFlinger 进程中，只有系统级的 trace 才能把它们串联起来。

**启动速度分析。** 冷启动涉及 Zygote fork → Application 创建 → ContentProvider 初始化 → Activity 创建 → 首帧渲染等十几个步骤，跨越多个进程。Perfetto 可以按时间线展示每个步骤的耗时和依赖关系，让你一眼看出瓶颈在哪。

**ANR 分析。** ANR 是主线程阻塞的结果，但阻塞的原因可能在其他进程（比如 Binder 对端正在做耗时操作）。Perfetto 的 Binder 事件追踪可以让你看到完整的 Binder 调用链：谁发起的、发给了谁、对端处理了多久。

**功耗分析。** 从 Android 10 开始，Perfetto 可以采集 ODPM（On-Device Power Rails Monitor）数据，追踪每个硬件子系统（CPU、GPU、显示屏、Modem 等）的独立功耗。这在优化电池续航时非常有用。

**内存分析。** 通过 heapprofd 和 java_hprof 数据源，Perfetto 可以在 trace 中同时记录内存分配行为和系统状态变化，帮助你理解"什么时候分配了内存、分配了多少、触发了什么后续事件"。

这些场景都有一个共同特征：问题跨越了单个进程、单个线程的边界。对于这种系统级问题，Perfetto 不是众多可选工具之一——它是唯一的工具。

## Perfetto 的跨平台能力

Perfetto 不止服务于 Android。作为一个开源项目，它的设计目标是成为一个通用的 tracing 基础设施。

在 Chrome 中，Perfetto 是 `chrome://tracing` 背后的引擎。Chrome 的各个组件（渲染、网络、GPU 等）通过 Perfetto 的数据源接口上报 trace 事件，开发者可以在 Perfetto UI 中查看完整的浏览器行为时间线。

在 Linux 桌面/服务器上，Perfetto 提供了完整的系统级 tracing 能力，包括 ftrace 数据源、/proc 和 /sys 轮询、以及 Native 应用的 CPU 和堆 Profiling。一个叫 `tracebox` 的单文件可执行程序把所有必要工具打包在一起，方便在不同 Linux 机器上部署。

对于 Android 开发者来说，这个跨平台能力的实际意义在于：你掌握的 Perfetto 使用技巧（UI 操作、SQL 查询、配置方法）在所有平台上通用。如果你将来需要在 Linux 或 Chrome 上做性能分析，不需要重新学习一套工具。[已验证: 官方文档, perfetto.dev/docs]

## Perfetto SDK：在 App 中嵌入自定义 Trace

Perfetto 提供了一个 C++17 的 Tracing SDK，允许 App 开发者在自己的代码中添加自定义的 trace 点。这比使用 `android.os.Trace`（本质上是 atrace）更强大，因为：

- **自定义事件类型**：不只是简单的 begin/end，可以定义带结构化数据的复杂事件。
- **自定义 Counter**：可以追踪 App 特有的指标（队列长度、缓存命中率等），和系统级数据在同一时间线上展示。
- **两种运行模式**：
  - *In-process 模式*：Perfetto 服务运行在 App 进程内部，只采集 App 自己的事件，不需要特殊权限。支持 Android、Linux、macOS、Windows。
  - *System 模式*：App 通过 UNIX socket 连接到系统的 `traced` 守护进程，这样 App 的自定义事件就和系统级事件（CPU 调度、内存变化等）对齐在同一时间线上。这是做全栈性能分析时最强大的组合。

SDK 的使用方式是继承 `perfetto::DataSource` 类，定义自己的事件 schema。采集到的事件数据可以直接在 Perfetto UI 中查看，也可以通过 Trace Processor 用 SQL 查询。

不过需要注意，如果定义了完全自定义的数据格式，可能需要在 Trace Processor 和 UI 中做对应的适配工作，才能正确解析和展示自定义事件。对于大多数 Android 性能分析场景，`android.os.Trace` API（atrace）已经足够，SDK 主要面向有深度定制需求的应用和引擎开发者。[已验证: 官方文档, perfetto.dev/docs/instrumentation/tracing-sdk]

## 版本演进时间线 [自动发现]

Perfetto 的引入和演进与 Android 版本紧密相关：

- **Android 4.1 (2012)**：Systrace 引入，成为 Android tracing 的起点。
- **Android 9 (API 28, 2018)**：Perfetto 基础设施开始集成到 AOSP，但默认未启用。"系统追踪"（Traceur）应用出现在开发者选项中，支持在设备上直接抓取 trace。
- **Android 10 (API 29, 2019)**：Perfetto 正式成为默认的 tracing 系统。设备上抓取的 trace 文件默认保存为 Perfetto 格式（.perfetto-trace）。heapprofd（Native 内存 Profiling）和功耗计数器数据源引入。
- **Android 11 (API 30, 2020)**：`traced` 守护进程默认启用，不再需要手动启动。Java 堆 Profiling（`java_hprof`）数据源引入。
- **Android 12 (API 31, 2021)**：Perfetto 的配置和采集能力进一步增强，与 Android Studio Profiler 的集成更加紧密。
- **Android 13-16**：持续优化数据源和性能，Perfetto 保持活跃开发。Systrace 命令行工具已从最新的 platform-tools 中移除。

如果你在使用低于 Android 10 的设备，仍然可以使用 Systrace；但强烈建议在 Android 10 及以上设备上使用 Perfetto，以获得完整的数据源覆盖和分析能力。

[已验证: 官方文档, source.android.com/docs/core/debug/perfetto; 适用版本: Android 4.1 - Android 16]

## 参考资料

- Perfetto 官方文档：https://perfetto.dev/docs/
- Android 官方 Perfetto 指南：https://source.android.com/docs/core/debug/perfetto
- Perfetto GitHub 仓库：https://github.com/google/perfetto
- Perfetto UI：https://ui.perfetto.dev
- AOSP traced 服务源码路径：`system/tracing/traced/`
- AOSP traced_probes 服务源码路径：`system/tracing/traced_probes/`
- 高爷 Systrace/Perfetto 系列教程：https://www.androidperformance.com/2019/12/01/Android-Systrace(Perfetto)-Basic/
