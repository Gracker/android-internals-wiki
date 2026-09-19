---
title: Perfetto SDK 与应用内 Trace 数据源
chapter: '14.12'
section: '14.12'
status: finalized
applicable_versions: Android 10 (API 29) - Android 17 (API 37)；system backend 依赖设备侧 traced 服务，低版本按设备能力降级
last_verified: '2026-08-13'
last_verified_against: AOSP external/perfetto android-17.0.0_r1 / Perfetto v57.2 / Android Developers ProfilingManager API 35 / ProfilingTrigger API 36
confidence: medium
sources:
- type: official
  path: https://perfetto.dev/docs/instrumentation/tracing-sdk
- type: official
  path: https://perfetto.dev/docs/getting-started/in-app-tracing
- type: official
  path: https://perfetto.dev/docs/design-docs/api-and-abi
- type: aosp
  path: https://android.googlesource.com/platform/external/perfetto/+show/android-17.0.0_r1/docs/instrumentation/tracing-sdk.md
- type: official
  path: https://developer.android.com/topic/performance/tracing/custom-events
- type: official
  path: https://developer.android.com/topic/performance/tracing
- type: official
  path: https://developer.android.com/topic/performance/tracing/profiling-manager/querying-profiles
- type: official
  path: https://developer.android.com/reference/android/os/ProfilingManager
- type: official
  path: https://developer.android.com/reference/android/os/ProfilingTrigger
- type: blog
  path: Cubox/性能工具-Perfetto(4)-通过SDK抓取信息-2026-05-02.md
tags:
- perfetto
- tracing-sdk
- in-app-tracing
- custom-data-source
- observability
related_chapters:
- '14.1'
- '14.6'
- '17.2'
- '26.1'
- '26.6'
pipeline_stage: ready-to-publish
task6_state: reviewed
task9_state: reviewed
task2b_state: fixed
---

# Perfetto SDK 与应用内 Trace 数据源

本文核对的平台源码版本是 AOSP `android-17.0.0_r1`。内核版本 `android17-6.18-2026-06_r6` 只决定 system trace 中可采集的 ftrace、调度和内核事件；Perfetto SDK 的 TrackEvent 编码、共享内存写入和 producer IPC 都在用户态完成。API level 表示 Android 平台接口版本，SDK revision 表示应用集成的 Perfetto 发布版本，两者要分开记录，不能由前者推断后者。

Perfetto SDK（Software Development Kit）负责把应用自定义事件写进 Perfetto trace，适合 C/C++ 模块、游戏引擎、Native 渲染管线和端侧推理运行时。应用可以独立采集一份只含自身事件的 `.pftrace`；也可以充当 producer（数据生产端），把事件交给系统 Perfetto service，再由有权限的 consumer（负责配置、启停和读取的一方）与调度、Binder、SurfaceFlinger 等数据一同采集。

## 1. Perfetto SDK 和 Android Trace API 的边界

“埋点”指在代码中主动记录时间点、执行区间或数值。Android 上常用的接口分为三层，选择时主要看数据表达能力和谁能控制采集，编程语言只是一项条件：

| 接口 | 写入内容 | 谁控制采集 | 常见用途 |
|---|---|---|---|
| `android.os.Trace`、`androidx.tracing`、NDK `ATrace_*` | atrace section（同步区间）、async section（可跨线程结束的区间）、counter（数值序列）等平台标记 | 系统 trace consumer | Java/Kotlin 页面、启动步骤、跨 Java/Native 的普通区间 |
| Perfetto SDK `track_event` | category（事件分类）、slice（有时长的区间）、custom track（自定义时间线）、flow（跨事件关联）、counter、debug annotation（附加键值参数） | in-process session 或外部 Perfetto consumer | C++ 引擎、渲染阶段、任务图和 Native 状态 |
| Perfetto SDK custom data source | 自定义 TracePacket 字段和生命周期回调；TracePacket 是 trace 文件的 protobuf 记录单元 | in-process session 或外部 Perfetto consumer | 高频且需要强类型 schema（字段类型固定的数据格式）的子系统状态 |

官方 SDK 文档建议 Android 专用埋点优先沿用 `android.os.Trace` / `ATrace_*`，前提是平台接口已经能表达所需信息。atrace 标记可以进入 Perfetto，不需要为了工具统一而迁移现有 Java/Kotlin 埋点。

`track_event` 是 SDK 的默认选择。它已经处理线程安全、增量状态、string interning（用整数 ID 复用重复字符串）和 flush（把暂存数据提交给 service）。Trace Processor（负责导入和查询 trace 的分析引擎）也能直接生成 `slice`、`counter`、flow 等标准数据。custom data source 适用于以下条件同时成立的场景：

- slice、counter 和调试参数无法自然表达数据；
- 高频记录对每个 TracePacket 的大小敏感，需要稳定的 protobuf schema；
- 团队愿意同步维护 Trace Processor importer（导入解析器）、内部存储表和查询；
- schema 具备字段编号、单位、枚举演进和兼容策略。

custom data source 写出的私有 protobuf 不会自动变成 PerfettoSQL 表。原始 trace 文件仍保留未知字段的编码字节，但没有对应 schema 和 importer 的官方 Trace Processor 会跳过这些字段，因此 PerfettoSQL 查询不到其中的业务数据。

## 2. in-process backend：应用自己控制 session

in-process backend（进程内后端）把 tracing service、consumer 和 producer 都放在当前进程，不连接 Android 的 `/dev/socket/traced_producer`。应用可以创建、停止并读取 session；这里的 session 指一次拥有独立配置和 buffer 的采集会话。产物只含注册到该进程内 backend 的数据源，不包含 ftrace、Binder、SurfaceFlinger 或其他进程事件。

下面的示例固定使用 `kInProcessBackend`，并让调用方传入经过实测的 buffer 容量与应用私有输出 fd（file descriptor，文件描述符）：

```cpp
#include <cstdint>
#include <memory>
#include <utility>

#include <perfetto.h>

PERFETTO_DEFINE_CATEGORIES(
    perfetto::Category("rendering")
        .SetDescription("Events from the rendering subsystem"));
PERFETTO_TRACK_EVENT_STATIC_STORAGE();

void InitPerfetto() {
  perfetto::TracingInitArgs args;
  args.backends = perfetto::kInProcessBackend;
  perfetto::Tracing::Initialize(args);
  perfetto::TrackEvent::Register();
}

std::unique_ptr<perfetto::TracingSession> StartAppTrace(
    uint32_t buffer_size_kb, int output_fd) {
  perfetto::TraceConfig config;
  config.add_buffers()->set_size_kb(buffer_size_kb);

  auto* ds_config = config.add_data_sources()->mutable_config();
  ds_config->set_name("track_event");

  perfetto::protos::gen::TrackEventConfig track_event_config;
  track_event_config.add_enabled_categories("rendering");
  track_event_config.add_disabled_categories("*");
  ds_config->set_track_event_config_raw(
      track_event_config.SerializeAsString());

  auto session =
      perfetto::Tracing::NewTrace(perfetto::kInProcessBackend);
  session->Setup(config, output_fd);
  session->StartBlocking();
  return session;
}

template <typename DrawFn>
void TraceDrawFrame(uint64_t frame_id, DrawFn&& draw) {
  TRACE_EVENT("rendering", "DrawFrame", "frame_id", frame_id);
  std::forward<DrawFn>(draw)();
  TRACE_COUNTER("rendering", "SubmittedFrameId", frame_id);
}

void StopAppTrace(
    std::unique_ptr<perfetto::TracingSession> session) {
  perfetto::TrackEvent::Flush();
  session->StopBlocking();
}
```

初始化、`TrackEvent::Register()` 和 category 静态存储都要在事件写入前完成。`StartBlocking()` 返回后，配置才处于活动状态；此前执行的 `TRACE_EVENT` 不属于这次普通 in-process session。`TraceDrawFrame()` 让真实渲染函数在 slice 作用域内执行，记录的是函数从进入到返回的持续时间。

`TrackEvent::Flush()` 把 writer（SDK 写入端）中尚未提交的数据推给 service，`StopBlocking()` 负责结束 session。示例使用 `Setup(config, output_fd)` 直接写入由应用以私有权限打开的文件；调用方要保持 fd 有效，并在停止完成后关闭。若 `Setup()` 不传 fd，再使用 `ReadTraceBlocking()` 读取 consumer buffer。同一个 session 只选择一种导出方式。

`buffer_size_kb` 要根据目标设备上的事件率、最长采集时间和丢包统计确定。ring buffer（环形缓冲区）写满后覆盖旧 packet，`DISCARD` 策略写满后舍弃新 packet，两者丢失的时间段不同。

## 3. system backend：应用只作为 producer

system backend（系统后端）通过 producer socket `/dev/socket/traced_producer` 连接设备上的 `traced` 服务。应用注册 data source 并响应启停回调；系统 trace 的配置、buffer、输出文件和读取权限都由 consumer 管理。

Android 17 的 `system/sepolicy/private/app.te` 对 `appdomain` 使用 `perfetto_producer(appdomain)`，允许应用向 `traced` 写数据。consumer socket 的权限要求更严格；producer 能够连接，只说明应用可以提交数据，不能据此判断它有权启动或读取整机 trace。

应用只贡献 TrackEvent 时，初始化可以关闭 system consumer 实现。下面的配置来自 Android 17 SDK API 的推荐形态：

```cpp
void InitSystemProducer() {
  perfetto::TracingInitArgs args;
  args.backends = perfetto::kSystemBackend;
  args.enable_system_consumer = false;
  perfetto::Tracing::Initialize(args);
  perfetto::TrackEvent::Register();
}
```

`enable_system_consumer = false` 配合“代码中不显式调用 `NewTrace(kSystemBackend)`”时，linker（链接器）可以从最终二进制中移除未使用的 system consumer IPC（进程间通信）代码。这个字段只帮助构建工具删除未使用代码，不负责授权；应用代码仍不得创建 system consumer，也不调用 `ReadTraceBlocking()`。外部 consumer 决定何时选择 `track_event`。

adb 或受控实验环境的外部 TraceConfig 要显式请求 `track_event`，并在 `TrackEventConfig` 中启用目标 category。需要调度证据时，再加入 `linux.ftrace` 的 `sched_switch`、`sched_waking`；duration 与 buffer 按复现窗口和实测写入速率设置。配置由具备 consumer socket 权限的 shell 或系统组件提交，应用 producer 不负责创建输出文件。

应用进程必须在 session 期间运行并完成 data source 注册。若配置能抓到 ftrace 却没有 `rendering` slice，应依次检查 producer 是否连接、`track_event` descriptor（注册时上报的数据源说明）是否出现、category 是否匹配、进程是否在采集窗口内写事件。Manifest 中的 `profileable` / `debuggable` 属性会影响若干平台 profiler 和 shell profiling 能力，但不会让应用获得 system trace consumer 权限。

`linux.ftrace` 的可用事件由设备内核决定。本文核对的内核版本是 `android17-6.18-2026-06_r6`；量产设备使用的 vendor 内核与 GKI（Generic Kernel Image，通用内核镜像）组合、SELinux 策略，以及 tracefs（内核跟踪文件系统）配置仍要实机确认。

## 4. custom data source：schema 与 importer 要成对设计

custom data source 继承 `perfetto::DataSource<T>`。每个活动 trace session 会创建独立实例；多个并发 session 可能让 `Trace()` lambda（传给 `Trace()` 的匿名回调）执行多次。没有活动实例时 lambda 不执行，所以计算成本高的参数应放在 lambda 内。访问实例状态时要调用 `GetDataSourceLocked()` 取得带锁句柄，避免 session 停止与业务线程写入同时发生时访问已销毁的实例。

自定义数据源的四个边界如下：

| 入口 | 可做的工作 | 生命周期约束 |
|---|---|---|
| `OnSetup(const SetupArgs&)` | 解析本实例配置，准备有界状态 | `SetupArgs::config` 只在回调期间有效，不能保存指针 |
| `OnStart(const StartArgs&)` | 启动子系统采样 | 回调可能来自 Perfetto 内部线程 |
| `Trace(lambda)` | 按活动实例写 packet | 没有活动实例时 lambda 不执行；并发 session 可执行多次 |
| `OnStop(const StopArgs&)` | 停止采样并写收尾 packet | 不应长时间阻塞 Perfetto 回调线程 |

`OnStop()` 中存在异步清理时，要调用 `StopArgs::HandleStopAsynchronously()` 取得 acknowledgement closure，也就是用于确认“停止操作已经完成”的回调。清理线程写完末尾 packet 后，还要在最后一次 `Trace()` lambda 中显式调用 `TraceContext::Flush()`，再执行该回调。这个过程必须在 consumer 配置的 stop timeout（停止等待上限）内完成；超时后服务会强制停止，之后写出的末尾数据不会进入 trace。数据源名称宜使用团队控制域名的反向域名形式，减少与其他 producer 的命名冲突。

强类型 packet 需要扩展 TracePacket schema。原版 amalgamated SDK 不会为项目私有消息生成 setter，完整实现至少包含四处同步修改：

1. 为 packet 定义稳定的 protobuf 字段和编号；
2. 生成 SDK 侧 pbzero 写入接口；pbzero 是 Perfetto 的轻量级 protobuf 写入代码；
3. 在 Trace Processor importer 中解析字段并写入内部 storage（表存储）；
4. 为 schema 兼容、损坏 packet、未知枚举和 SQL 结果补测试。

只在应用仓库里增加 `.proto`，公开版 Perfetto UI 无法自动识别它。团队无法长期维护 Trace Processor fork（定制分支）时，优先使用 TrackEvent 的 category、slice、counter、flow 和长度受限的 debug annotation。

## 5. startup tracing、触发器与环形缓冲

普通 session 只能记录它启动后发生的事件。Perfetto SDK 的 startup tracing（启动早期采集）会先让 data source 写入临时目标缓冲区，再等待后续 system session 用匹配的配置接管这些数据。Android 17 的 `Tracing::SetupStartupTracingOpts` 默认超时是 10 秒；超时、配置不匹配，或 service 不接受 producer-provided shared memory（由 producer 提供的共享内存）时，startup session 会终止。

下面的代码固定使用 system backend，并把 session handle（管理该 startup session 的对象）交给调用方；不再等待 system session 时，可以通过该 handle 主动 abort（中止等待）：

```cpp
std::unique_ptr<perfetto::StartupTracingSession>
StartStartupTracing(const perfetto::TraceConfig& config) {
  perfetto::Tracing::SetupStartupTracingOpts options;
  options.backend = perfetto::kSystemBackend;
  return perfetto::Tracing::SetupStartupTracingBlocking(
      config, options);
}
```

未覆盖 `timeout_ms` 时，Android 17 SDK 使用源码默认值 10 秒。`SetupStartupTracingOpts` 还提供 `on_setup`、`on_adopted` 和 `on_aborted` 回调，生产实现应记录临时数据是否被 system session 接管，或等待是否中止。startup tracing 不支持 in-process backend。in-process 场景应在目标初始化工作前创建普通 session，并等待 `StartBlocking()` 完成。system 场景还要求外部 consumer 在超时内提交可匹配配置；只调用 `SetupStartupTracingBlocking()` 不会生成可读取的系统 trace 文件。

Perfetto trigger 是向已配置 session 发送“条件已满足”信号的机制，本身不负责创建 session。下面是 Android 17 头文件公开的触发接口：

```cpp
static void ActivateTriggers(
    const std::vector<std::string>& triggers,
    uint32_t ttl_ms);
```

`ttl_ms` 是触发信号的有效期，由调用方根据 producer 连接策略确定。调用只向当前已连接或在 TTL 内完成连接的 backend 发送信号；trace 的 ring buffer、停止策略和输出文件仍由 consumer 配置。应用内 APM（Application Performance Monitoring，应用性能监控系统）可以决定何时发信号，但不能借此读取 consumer buffer。

要持续保留故障发生前的一段数据，session 必须提前运行并使用 ring buffer。故障出现后才启动 trace，只能看到故障后的活动。进程被 LMK（low-memory killer，低内存终止机制）或 native crash 直接终止时，尚未提交的 producer chunk（共享内存中的一块待提交数据）和应用私有文件都可能丢失；线上方案要单独验证异常退出路径。

## 6. 构建、体积和版本兼容

官方 C++ SDK release 由 `perfetto.h` 与 `perfetto.cc` 两个 amalgamated（合并发布）文件组成，要求 C++17。推荐把 `perfetto.cc` 编成内部静态库，并链接到使用它的同一个 native linker unit，也就是最终生成同一个 ELF 文件的链接单元。不要把 Perfetto C++ 类型导出为跨动态库 ABI（Application Binary Interface，应用二进制接口）。

版本关系分为三层：

| 层级 | Android 17 边界 |
|---|---|
| 设备 tracing service | 固定到 `android-17.0.0_r1` 的 `external/perfetto` 与设备厂商补丁 |
| 应用 Perfetto SDK | 独立选择并锁定 release revision；不能由 API 37 推导 |
| trace 分析工具 | 可使用更新的 Trace Processor，但查询要按工具版本校验 schema |

Perfetto tracing protocol 的 socket、共享内存和 protobuf 协议维持双向兼容，新 client（SDK 端）可以连接旧 service，旧端会忽略不认识的字段。协议兼容不代表旧 service 支持所有新特性；依赖新 IPC 方法、capability（服务声明的能力）或 data source 字段时，仍要在运行时检查该能力是否存在。

公开 C++ `TrackEvent` 与 custom data source 属于官方 API，发布形态是静态库。公开 API 不保证跨动态库的 C++ ABI 稳定；应用不能从一个 linker unit 导出 Perfetto C++ 类型，再交给另一个 linker unit 使用。`include/perfetto/ext/` 是内部接口，不应在应用中依赖。Android 17 源码文档和当前官方稳定性文档都把 `include/perfetto/public` 下的 C API/ABI 标为未稳定。纯 C 或 Rust FFI（Foreign Function Interface，跨语言调用接口）项目采用它时要锁定 revision，并在每次升级时回归验证编译、运行和 trace 解析。

APK 体积不能用一个固定数字描述。`stripped release` 指已移除调试符号的发布产物，LTO 是链接时优化，RTTI 是 C++ 运行时类型信息。至少要分别测量：

- 只启用 system producer，并设置 `enable_system_consumer = false`；
- 同时链接 in-process service/consumer；
- 各 ABI 的 stripped release 产物；
- LTO、异常、RTTI，以及 zlib/zstd 压缩和 re2 正则匹配能力开启前后的差异。

`Tracing::Initialize()` 对已初始化 backend 的重复调用不会重建它，后续参数也大多被忽略。一个进程应集中管理 backend 初始化和 category 注册，避免多个 SDK 各自携带一份 amalgamated 实现。

平台版本差异如下：

- Android 9 已随系统提供 `traced`；
- 本知识库从 Android 10 开始讨论应用接入，旧设备仍需检查 daemon（后台服务进程）是否运行和 socket 是否可达；
- Android 15 / API 35 增加 `ProfilingManager.requestProfiling()`；
- Android 16 / API 36 增加 `ProfilingTrigger` 与触发式 profiling；
- Android 17 / API 37 的行为以 `android-17.0.0_r1` 为准。

低版本或 system backend 不可用时，保留 `android.os.Trace` / `ATrace_*` 标记。它们对 Android 专用代码的覆盖面更广，也能被 Macrobenchmark、Android Studio 和系统 trace 工具采集。

## 7. 隐私与数据治理

这里的“数据治理”指明确哪些内容可以记录、谁可以读取、是否允许上传，以及文件保留多久。trace 同时包含时间、线程、进程、事件名、参数和系统状态。固定事件名也可能暴露业务流程，动态参数还可能直接携带账号、URL、token 或位置数据。埋点设计要按“这份文件可能被上传用于诊断”的标准评审：

- category 只描述技术模块，如 `rendering`、`network_scheduler`、`ml_runtime`；
- event 名固定，动态值写入有类型、有上限的参数；
- frame id、queue depth、buffer size、stage enum 可以进入调试参数；
- 用户标识、订单号、完整 URL、请求体、token、地理位置和原始堆栈不得写入；
- counter 标明单位、范围、无效值和重置语义；
- 从文件生成到上传的整条路径都要限制文件大小、采样率和保留期，明确谁可以读取，并使用加密传输。

in-process trace 只含本进程数据，但文件仍可能带有敏感业务上下文。system trace 还可能包含其他进程和系统行为，普通应用只有 producer 权限时不得尝试复制、上传或长期保存整机产物。

`ProfilingManager` 返回给应用的是经过 redaction（按规则删除或模糊敏感字段）的结果。自定义 packet 或新字段是否保留取决于 redactor 规则，不能把未脱敏 trace 中可见的字段当成公开 API 保证。

## 8. Perfetto SDK、ProfilingManager 与 APM 的组合

APM 在这里指 Application Performance Monitoring，即负责线上触发、收集和聚合性能数据的系统。三者分别控制不同环节：

- Perfetto SDK 负责事件编码和 producer 生命周期；
- `ProfilingManager` 负责受平台约束的 profiling 请求、rate limiting（限制单位时间内的请求次数）、文件交付和 redaction；
- APM 负责触发条件、采样、上传、聚合和告警。

Android 17 的 `packages/modules/Profiling/service/.../Configs.java` 给出了一个容易被忽略的边界：`ProfilingManager` 的 system trace 配置包含 `linux.process_stats`、`android.packages_list`、目标 App 的 atrace、`linux.ftrace` 和 `android.surfaceflinger.frametimeline`，没有请求 `track_event`，也没有请求应用自定义 data source。

因此，应用初始化 Perfetto SDK system backend 后，SDK TrackEvent 不会自动出现在 Android 17 的 `ProfilingManager` 结果中。需要同时使用 SDK 与平台 profiling 时，可以按以下方式分工：

| 环境 | 应用埋点 | session 控制 | 可期待的产物 |
|---|---|---|---|
| 开发期 Native 单测 | SDK in-process `track_event` | 应用 | 只含本进程 SDK 事件的 `.pftrace` |
| adb / 实验室专项 | SDK system backend + ATrace | shell 或受控工具 | 显式配置的 TrackEvent、ftrace、Binder、渲染数据 |
| Android 15-17 公开线上 profiling | ATrace + `ProfilingManager` | 平台 service | rate limiting、redaction 后与请求 App 相关的结果 |
| 系统/内测版本 | SDK system backend + 平台数据源 | 具备 `traced_consumer` 策略权限的系统组件或 shell | 授权配置范围内的 system trace |

`ProfilingManager.requestProfiling()` 从 API 35 可用，系统触发注册从 API 36 可用。请求受系统限流且不保证执行；回调成功后也要使用 `ProfilingResult.getResultFilePath()` 取得交付文件。API 37 没有开放任意 TraceConfig 注入，所以应用不能要求它顺带启用私有 custom data source。

APM 若需要 SDK 专属事件，可以管理短时间运行的 in-process session，并上传应用自己的文件；若需要系统调度证据，应调用公开 profiling API 或依赖受控 consumer。两类文件的访问权限、脱敏状态和查询 schema 要分别记录。

## 9. Trace Processor 查询与验收

TrackEvent 使用标准 importer，无需自定义插件。下面的 SQL 检查 `rendering` category 是否生成线程上的 slice 记录：

```sql
SELECT
  process.name AS process_name,
  thread.name AS thread_name,
  slice.ts / 1e6 AS ts_ms,
  IIF(slice.dur = -1, trace_end() - slice.ts, slice.dur) / 1e6 AS dur_ms,
  slice.name,
  slice.category
FROM slice
JOIN thread_track ON thread_track.id = slice.track_id
JOIN thread USING (utid)
LEFT JOIN process USING (upid)
WHERE slice.category = 'rendering'
ORDER BY slice.ts;
```

结果为空时，不要只看事件宏是否执行。检查 trace 配置是否选择 `track_event`、category 过滤是否匹配、producer 是否在 session 内连接，以及事件是否发生在 `StartBlocking()` 之后。

下面的查询检查示例 counter；counter 名来自 `TRACE_COUNTER` 的 track name：

```sql
SELECT
  counter.ts / 1e6 AS ts_ms,
  counter.value,
  counter_track.name
FROM counter
JOIN counter_track ON counter_track.id = counter.track_id
WHERE counter_track.name = 'SubmittedFrameId'
ORDER BY counter.ts;
```

custom data source 的验收标准更高：原始 trace 中有 packet、Trace Processor 没有 importer error（导入错误）、目标 storage 表有行、未知枚举按兼容规则处理、SQL 输出与写入样本一致，五项都要通过。

一次完整接入至少保存这些证据：

1. 应用使用的 Perfetto SDK revision 和构建选项；
2. 设备 Android build、`android-17.0.0_r1` 对应关系与实际 vendor 版本；
3. backend、producer 名、data source 名和 category；
4. TraceConfig、采集命令、输出文件 hash（内容摘要）；
5. buffer loss（缓冲区数据丢失）、producer disconnect（连接断开）、startup adopted/aborted（被接管或中止）状态；
6. Trace Processor 版本和可复现 SQL。

## 10. 已确认的限制与待实测项

- Android 17 `ProfilingManager` 默认 system-trace 配置不采集 SDK `track_event` 或 custom data source；它会采集目标包的 atrace。
- startup tracing 只支持 system backend，默认等待匹配 session 10 秒；它不提供应用读取 system trace 的权限。
- SDK C++ client 与 system service 依赖长期兼容的 tracing protocol；具体新能力仍需检查 service 是否声明对应 capability。
- C API/ABI 仍处于不稳定状态；C++ SDK 采用静态链接，不把 C++ 接口导出为共享库 ABI。
- C SDK/C++ SDK 针对不同 ABI（如 arm64-v8a、x86_64）生成的包体积、启动耗时和常驻内存，需要用目标 release APK 测量，不能从官方示例推算。
- 私有 custom data source 的 SQL 表由项目 importer 决定；上面的标准 SQL 只适用于 TrackEvent。

## 参考资料

### Android 17 一手源码

- [AOSP `android-17.0.0_r1` Tracing SDK 文档](https://android.googlesource.com/platform/external/perfetto/+/refs/tags/android-17.0.0_r1/docs/instrumentation/tracing-sdk.md)
- [AOSP `example.cc`](https://android.googlesource.com/platform/external/perfetto/+/refs/tags/android-17.0.0_r1/examples/sdk/example.cc)
- [AOSP `example_system_wide.cc`](https://android.googlesource.com/platform/external/perfetto/+/refs/tags/android-17.0.0_r1/examples/sdk/example_system_wide.cc)
- [AOSP `example_startup_trace.cc`](https://android.googlesource.com/platform/external/perfetto/+/refs/tags/android-17.0.0_r1/examples/sdk/example_startup_trace.cc)
- [AOSP `TracingInitArgs` / `SetupStartupTracingOpts`](https://android.googlesource.com/platform/external/perfetto/+/refs/tags/android-17.0.0_r1/include/perfetto/tracing/tracing.h)
- [AOSP `DataSource` 生命周期接口](https://android.googlesource.com/platform/external/perfetto/+/refs/tags/android-17.0.0_r1/include/perfetto/tracing/data_source.h)
- [AOSP `TrackEvent` 宏接口](https://android.googlesource.com/platform/external/perfetto/+/refs/tags/android-17.0.0_r1/include/perfetto/tracing/track_event.h)
- [Android 17 appdomain Perfetto producer policy](https://android.googlesource.com/platform/system/sepolicy/+/refs/tags/android-17.0.0_r1/private/app.te)
- [Android 17 `ProfilingManager` TraceConfig 生成逻辑](https://android.googlesource.com/platform/packages/modules/Profiling/+/refs/tags/android-17.0.0_r1/service/java/com/android/os/profiling/Configs.java)
- [`android17-6.18-2026-06_r6` kernel tag](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6)

### 官方接口与使用文档

- [Perfetto Tracing SDK](https://perfetto.dev/docs/instrumentation/tracing-sdk)
- [Perfetto TrackEvent](https://perfetto.dev/docs/instrumentation/track-events)
- [Perfetto tracing API/ABI 稳定性](https://perfetto.dev/docs/design-docs/api-and-abi)
- [Android `<profileable>`](https://developer.android.com/guide/topics/manifest/profileable-element)
- [Android `ProfilingManager`](https://developer.android.com/reference/android/os/ProfilingManager)
- [ProfilingManager 结果读取与 redaction](https://developer.android.com/topic/performance/tracing/profiling-manager/retrieve-and-analyze)
- [Android Native 自定义 trace event](https://developer.android.com/topic/performance/tracing/custom-events-native)

### 相关章节

- 14.1 Trace 抓取：系统 TraceConfig 与命令行
- 14.6 Android Tracing 基础设施：producer、service、consumer
- 17.2 Matrix、btrace 与 AndroidX Tracing SDK
- 26.1 性能指标上报：线上指标与文件治理
- 26.6 诊断能力演进：权限、采样和版本化协议
