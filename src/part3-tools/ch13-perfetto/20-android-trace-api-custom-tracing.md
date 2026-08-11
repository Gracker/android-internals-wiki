---
title: "android.os.Trace API 深度解析与应用级自定义追踪"
chapter: "13.20"
status: ready-for-review
drafted_date: "2026-07-06"
applicable_versions: "Android 10 (API 29) - Android 17 (API 37)"
last_verified: "2026-07-06"
last_verified_against: "android-17.0.0_r1"
confidence: high
sources:
  - type: aosp
    path: "frameworks/base/core/java/android/os/Trace.java"
  - type: aosp
    path: "frameworks/base/core/jni/android_os_Trace.cpp"
  - type: aosp
    path: "system/core/libcutils/trace-dev.cpp"
  - type: official
    path: "developer.android.com/reference/android/os/Trace"
tags: [trace, systrace, perfetto, tracing, debugging, custom-trace]
related_chapters: ["13.1", "13.3", "13.9", "13.16", "14.27"]
created_by: "task2a-knowledge-gap"
created_date: "2026-07-05"
drafted_by: "task2a-content-processing"
task6_state: reviewed
task6_result: pass-light-edit
task9_result: pass-tech-review
task9_state: reviewed
last_task9_reviewed_at: 2026-07-13
reviewed_by: openclaw-task6
reviewed_date: 2026-07-13
pipeline_stage: ready-to-publish
deepseek_cn_review_state: done
last_deepseek_cn_review_at: 2026-07-13
---

# 13.20 android.os.Trace API 深度解析与应用级自定义追踪

`android.os.Trace` 给应用代码提供了一组很小的 ATrace 接口：同步切片、跨线程异步切片和数值 Counter。抓取系统 trace 时，这些业务语义会与调度、Binder、I/O、FrameTimeline 和渲染事件共享时间基准，工程师因而能回答“系统为何在这段业务代码里耗时”。

Trace 埋点不会自行启动采集，也不会保存历史记录。设备上必须存在一场选择了目标应用的 Perfetto/系统跟踪会话，事件才会进入 trace。平台锚点为 Android 17 / API 37 / `android-17.0.0_r1`；涉及 ftrace 的内核实现统一参考 `android17-6.18-2026-06_r6`。

## 1. 公开 API 边界

### 1.1 第三方应用能调用什么

Android 17 的 `android.os.Trace` 公开 SDK 面仍是下面 6 个方法：

| API | 引入版本 | 语义 |
|---|---:|---|
| `beginSection(String)` / `endSection()` | API 18 | 当前线程上的嵌套同步切片 |
| `beginAsyncSection(String, int)` / `endAsyncSection(String, int)` | API 29 | 可跨线程结束的进程内异步切片 |
| `setCounter(String, long)` | API 29 | 进程范围的有符号 64 位数值样本 |
| `isEnabled()` | API 29 | 当前应用 trace tag 是否处于采集状态 |

API 18 只有同步切片。异步切片、Counter 和 `isEnabled()` 都在 API 29 才进入公开 SDK，把它们写成 API 18 能力会让低版本应用在验证或运行阶段失败。

源码中的下列方法不属于普通应用 SDK：

- 带 `traceTag` 参数的 `traceBegin()`、`asyncTraceBegin()` 等重载；
- `asyncTraceForTrackBegin()` / `asyncTraceForTrackEnd()`；
- `instant()` / `instantForTrack()`；
- `registerWithPerfetto()`；
- `setAppTracingAllowed()`。

其中一部分带 `@SystemApi`，另一部分直接标记 `@hide`。平台模块、系统应用或 OEM 代码可在相应构建环境中使用，Play 应用不能靠反射或 hidden-API 绕过来建立功能依赖。`setAppTracingAllowed()` 从 Android 12 起还是 no-op，不能用作业务热路径的 trace 开关。

### 1.2 应用工程优先使用 AndroidX

截至 2026-07-30，AndroidX Tracing 稳定版是 1.3.0。它替应用处理低版本兼容，并提供能自动配对的 Kotlin 扩展。下面的依赖用于稳定的 ATrace 埋点：

```kotlin
dependencies {
    implementation("androidx.tracing:tracing-ktx:1.3.0")
}
```

这条依赖仍把事件写入系统 trace 体系。AndroidX Tracing 2.0.0-beta01 是另一套低开销进程内 Perfetto API，带 metadata、Coroutine context propagation 和可插拔 sink；它处于 beta，升级时要单独评估数据格式、初始化和采集方式。

## 2. 三类事件分别表达什么

### 2.1 同步切片：当前线程做了什么

同步切片表示一段严格嵌套、在同一线程开始和结束的执行区间。下面的代码把一次数据库查询标在执行它的线程上：

```kotlin
import androidx.tracing.trace

fun readCachedFeed(): List<FeedItem> =
    trace("FeedRepository.readCache") {
        feedDao.readAll()
    }
```

`trace {}` 用 `try/finally` 保证 `endSection()` 一定执行。切片的 wall duration 包含运行、被抢占、阻塞和睡眠时间；它不能直接等同于 CPU time。要拆分这些成分，还需在 Perfetto 中结合 `thread_state`、`sched` 和 I/O 数据。

同步切片遵守三条硬约束：

- begin/end 必须发生在同一线程；
- 调用必须按栈结构嵌套；
- `endSection()` 结束的是当前线程最近一次尚未结束的 section，它不接收名称。

不要让同步切片跨越可能切换线程的协程挂起点。挂起后若在线程 B 恢复，线程 A 留下未结束的栈，线程 B 又弹出了不属于它的切片，后续时间线会一起错位。

### 2.2 异步切片：一项工作经历了多条线程

异步切片记录逻辑任务的开始到完成，适合队列任务、网络请求、图片加载和协程。下面的示例使用 AndroidX 的 suspend 扩展包住一次请求：

```kotlin
import androidx.tracing.traceAsync
import java.util.concurrent.atomic.AtomicInteger

private val traceCookie = AtomicInteger()

suspend fun loadProfile(userKey: String): Profile {
    val cookie = traceCookie.incrementAndGet()
    return traceAsync("ProfileRepository.load", cookie) {
        profileRepository.load(userKey)
    }
}
```

异步 begin/end 可以位于不同线程，但名称和 cookie 必须一致。该切片反映端到端 elapsed time，里面可能包括排队、网络等待、锁等待和多次调度；它不代表某一条线程持续执行了这么久。

cookie 用来区分重叠实例。Perfetto 的 ATrace 文档把它描述为进程内共享整数命名空间，因此应用应由一个受控 tracing 组件分配仍在使用的 cookie，完成后才允许复用。`name.hashCode()`、固定常量和多个互不协调的计数器都可能在重叠任务中碰撞。

公共 `beginAsyncSection()` 会创建进程范围的异步轨道。轨道在 UI 中的堆叠只说明时间重叠，不提供父子因果关系。需要显式 flow、metadata 或可控 track 时，应评估 Perfetto SDK 或 AndroidX Tracing 2.0。

### 2.3 Counter：某个状态在这一刻是多少

Counter 适合队列深度、活动连接数、缓存条目数和解码中内存等状态量。下面的代码只在队列深度发生变化时打点：

```kotlin
import android.os.Trace

fun onDecodeQueueChanged(depth: Int) {
    Trace.setCounter("ImageDecode.queueDepth", depth.toLong())
}
```

每次调用写入一个绝对值样本。Perfetto 会用相邻样本绘制 Counter Track；它不会替应用累加增量，也不会自动求速率。高频循环应节流或只在值变化时写，避免采集开销和 buffer 压力反过来改变被测行为。

## 3. 名称设计决定后续分析成本

### 3.1 使用稳定、低基数名称

同一类工作保持同一名称，例如：

- `Startup.loadLocalConfig`
- `FeedRepository.readCache`
- `ImageDecode.decode`
- `Checkout.submit`

不要把用户 ID、完整 URL、搜索词、文件路径或时间戳拼进名称。动态名称会制造大量无法聚合的切片，也可能把个人数据写进可分享的 trace。需要区分少量固定分支时，可采用有限枚举后缀，如 `ImageDecode.jpeg` 与 `ImageDecode.webp`。

### 3.2 长度和字符约束

`beginSection()` 的公开约束是最多 127 个 Unicode code unit，也就是 Java `String.length()` 的计数口径，不是 127 字节。Android 17 的 JNI 会把 `|` 与换行替换为空格，避免破坏 ATrace 文本协议。

异步名称和 Counter 名虽然没有同一条公开的 127 code unit 检查，底层 marker 消息仍有缓冲区上限。稳定短名称更便于 UI 搜索、SQL 聚合和跨版本对比。

### 3.3 延迟构造动态标签

trace 未启用时，API 会跳过事件写入；调用方在入参求值阶段创建的字符串却已经产生。下面的懒标签只会在 trace 活跃时构造：

```kotlin
import androidx.tracing.trace

fun decode(source: EncodedImage): Bitmap =
    trace(lazyLabel = { "ImageDecode/${source.format}" }) {
        decoder.decode(source)
    }
```

这里的 `format` 应来自小型固定枚举。若字段基数不可控，应改用稳定名称，并在 trace 外的受控诊断数据中保存关联信息。

## 4. Android 17 源码调用路径

### 4.1 Java 到 native

以 `Trace.beginSection("Feed.bind")` 为例，API 37 的路径如下：

```text
Trace.beginSection()
  -> isTagEnabled(TRACE_TAG_APP)
  -> nativeTraceBegin()
  -> tracing_perfetto::traceBegin()
  -> ATrace backend 或已注册的内部 Perfetto backend
```

`Trace.java` 在调用 JNI 前检查 `TRACE_TAG_APP`。JNI 的 `withString()` 把 Java 字符串转成 modified UTF-8、清理分隔字符，再进入 `frameworks/native/libs/tracing_perfetto`。

Android 17 的 `tracing_perfetto::traceBegin()` 会根据当前注册和启用状态选择路径。它不会无条件向 ATrace 与 Perfetto backend 各写一份。`registerWithPerfetto()` 也是隐藏的平台初始化入口，第三方应用不能据此假设 `android.os.Trace` 自动双写。

### 4.2 ATrace 路径如何启用

选择 ATrace 后，`libcutils` 会在首次使用时打开：

1. `/sys/kernel/tracing/trace_marker`；
2. 失败时回退到 `/sys/kernel/debug/tracing/trace_marker`。

`trace-dev.inc` 缓存 `debug.atrace.tags.enableflags` 对应的 property 信息，每次检查其序列号；序列号变化才刷新 tag。应用选择来自 `debug.atrace.app_number` 与 `debug.atrace.app_N`。源码里没有“Java TLS 缓存、每 64 次读属性”的实现。

启用后的典型 marker 编码包括：

| 事件 | libcutils 写入前缀 | Trace Processor 结果 |
|---|---|---|
| 同步 begin/end | `B` / `E` | 线程范围的 `slice` |
| 异步 begin/end | `S` / `F` | 进程范围的 `slice` |
| Counter | `C` | `counter` |
| 私有 track/instant API | `G` / `H` / `I` / `N` | 对应 process track 或 instant |

这些字符属于 Android 内部 ATrace 协议，应用代码应依赖公开 API 和 Trace Processor schema，不能直接写 marker 文本。Android 17 common kernel 的 trace marker/ring-buffer 侧以 [`android17-6.18-2026-06_r6`](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6) 为分析锚点；量产设备还可能带 OEM 内核改动。

### 4.3 开销不能写成固定纳秒数

Perfetto 官方文档给出的启用态 ATrace 单事件量级是 1–10 μs，成本来自字符串处理、Java 路径的 JNI 和写入 trace marker 的用户态/内核态往返。begin/end 是两个事件，高频短函数很容易让埋点成本接近业务成本。

trace 关闭时会走快速检查，成本低于写入态，但仍不能宣称“零开销”或固定 2–5 ns。动态标签分配、调用层级、设备 SoC、ART 编译状态和 backend 都会改变结果。热点埋点要用目标设备做 A/B 测量。

## 5. 让事件进入 Perfetto

### 5.1 TraceConfig

应用 ATrace 事件由 `linux.ftrace` data source 采集，目标包写在 `atrace_apps`。下面的 pbtxt 片段启用一个应用以及常用调度事件：

```protobuf
buffers {
  size_kb: 65536
  fill_policy: RING_BUFFER
}
data_sources {
  config {
    name: "linux.ftrace"
    ftrace_config {
      atrace_apps: "com.example.reader"
      ftrace_events: "sched/sched_switch"
      ftrace_events: "sched/sched_waking"
    }
  }
}
```

`atrace_apps` 控制哪些应用的 `TRACE_TAG_APP` 事件进入会话。系统服务类别则通过 `atrace_categories` 选择，例如 `am`、`wm`、`view` 或 `aidl`。两种配置负责不同职责。

### 5.2 命令行采集

Perfetto 官方 `record_android_trace` 脚本适合开发机复现。下面的命令采集目标应用、调度和常用系统类别：

```bash
python3 record_android_trace \
  -o reader.perfetto-trace \
  -t 10s \
  -a com.example.reader \
  sched freq idle am wm
```

采集开始后再复现目标旅程。若应用启动早期也在分析范围内，应确认脚本已经完成数据源启动，然后冷启动应用。Macrobenchmark 会自动保留测量迭代的 trace，适合把自定义 section 与启动、帧指标放在同一实验中。

系统“开发者选项 > 系统跟踪”也能采集 Perfetto trace，但配置、设备 build、应用版本和操作步骤仍要随报告保存。

### 5.3 `isEnabled()` 的含义

`Trace.isEnabled()` 表示当前进程的 app trace tag 被会话选择，适合避免只为 trace 服务的字符串构造。它不说明：

- trace buffer 还有多少空间；
- 当前事件一定完整保留到文件；
- 采集配置包含 sched、Binder 或 FrameTimeline；
- trace 可以记录敏感信息。

因此它只能当性能优化提示，不能参与鉴权、隐私或业务分支。

## 6. 协程和线程池怎么埋

一条协程经常经历“调用线程提交—等待队列—工作线程执行—回调线程恢复”。整项任务用异步切片，单个不挂起的 CPU/同步 I/O 段再用同步切片。下面的代码展示这两层语义：

```kotlin
import androidx.tracing.trace
import androidx.tracing.traceAsync
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

suspend fun loadFeed(cookie: Int): List<FeedItem> =
    traceAsync("Feed.load", cookie) {
        val rows = withContext(Dispatchers.IO) {
            trace("Feed.queryDb") {
                feedDao.readAll()
            }
        }
        withContext(Dispatchers.Default) {
            trace("Feed.mapModels") {
                rows.map(::toFeedItem)
            }
        }
    }
```

`Feed.load` 包含等待和线程切换；`Feed.queryDb` 与 `Feed.mapModels` 各自落在执行线程上。同步 lambda 内没有 suspend 调用，所以 begin/end 保持同线程。

线程池任务也遵循同一原则：

- 提交到完成：异步切片；
- 单次 worker 执行：同步切片；
- 队列长度：Counter；
- 排队时间：异步总时长减去已知执行切片，或直接在 Trace Processor 中做区间分析。

不要用 UI 中异步轨道的上下堆叠推断调用关系。公共 ATrace async event 没有 flow edge，视觉布局只为避免重叠。

## 7. Native 代码的公开 NDK 边界

NDK 在 `<android/trace.h>` 暴露等价能力，但引入版本与 Java SDK 不完全相同：

| NDK API | 可用版本 |
|---|---:|
| `ATrace_beginSection()` / `ATrace_endSection()` | API 23 |
| `ATrace_isEnabled()` | API 23 |
| `ATrace_beginAsyncSection()` / `ATrace_endAsyncSection()` | API 29 |
| `ATrace_setCounter()` | API 29 |

下面的 C++ 代码给一次同步解码加上线程切片：

```cpp
#include <android/trace.h>

class TraceScope {
public:
    explicit TraceScope(const char* name) {
        ATrace_beginSection(name);
    }

    ~TraceScope() {
        ATrace_endSection();
    }

    TraceScope(const TraceScope&) = delete;
    TraceScope& operator=(const TraceScope&) = delete;
};

DecodedFrame decodeFrame(const EncodedFrame& input) {
    TraceScope trace("VideoDecoder.decodeFrame");
    return decoder.decode(input);
}
```

`TraceScope` 让正常返回和异常展开都执行 `ATrace_endSection()`。名称不能包含换行或 `|`，高频调用前可用 `ATrace_isEnabled()` 避免昂贵标签构造。

平台源码中的 `<cutils/trace.h>` 还提供 `ATRACE_BEGIN`、`ATRACE_INT` 和系统 tag。它们属于平台内部接口。普通 NDK 应用使用 `<android/trace.h>`，事件隐式归入 app tag；`ATRACE_TAG_APP` 在 API 37 源码中的值是 `1 << 12`。

## 8. Android 17 私有能力该怎样理解

### 8.1 track、instant 与 tag

API 37 的 `Trace.java` 包含 `asyncTraceForTrack*` 和 `instant*`。前者允许平台代码指定 process track 并表达严格嵌套，后者写入无持续时间的瞬时事件。它们没有进入普通应用 SDK，不能放进面向第三方开发者的可编译示例。

同样，`TRACE_TAG_AIDL`、`TRACE_TAG_WINDOW_MANAGER` 等 tag 面向平台代码。应用公开 API 始终使用 `TRACE_TAG_APP`，采集端以包名选择应用事件。

### 8.2 Binder 自动切片覆盖什么

Android 17 的 `BBinder::transact()` 会在 `ATRACE_TAG_AIDL` 启用时调用 `startTrace()`，服务端事务处理由 AIDL slice 包围。抓取配置加入 `aidl` 后，可以观察服务端执行落在哪条 Binder 线程以及持续多久。

这段自动切片不携带应用 async section 的 cookie，也没有为业务请求生成跨进程 trace context。应用进程与服务进程各自拥有 process-scoped async 轨道；两个进程写相同 name/cookie 不会合成一条 slice。

分析一次跨进程调用时应组合：

- 客户端业务切片；
- Binder transaction 数据；
- 服务端 AIDL/业务切片；
- 调度、锁和线程状态。

需要显式跨进程因果关系时，协议层要传播受控、无敏感信息的 request ID，并在分析工具或 Perfetto SDK flow 中建立关系。`android.os.Trace` 的公开接口本身没有 flow 或 typed argument。

### 8.3 内部 Perfetto backend

`android-17.0.0_r1` 的 `frameworks/native/libs/tracing_perfetto` 为部分平台组件提供 Perfetto Track Event 路径。选择逻辑是 ATrace 优先条件与已启用 Perfetto category 的分支选择。把它描述成“每个 `Trace.beginSection()` 都双写”会导致错误的开销估计和重复事件预期。

第三方应用若需要 categories、typed metadata、flow 或自定义 track，可评估：

| 方案 | 稳定性与适用范围 |
|---|---|
| AndroidX Tracing 1.3.0 | 稳定；简单 ATrace section/async/counter |
| AndroidX Tracing 2.0.0-beta01 | beta；进程内 Perfetto、metadata、协程上下文和 sink |
| Perfetto C++ SDK | 高级原生埋点；categories、track、flow、typed arguments |

选型时还要确认采集端、冷启动初始化、文件合并和线上开销，不能只比较一次函数调用耗时。

## 9. 用 PerfettoSQL 读取自定义事件

### 9.1 Slice 已经是配对结果

Trace Processor 会把 begin/end 配对为一行 `slice`，其中 `ts` 是开始时间，`dur` 是持续时间。异步 section 也已经是完整 slice，无需把 `slice` 表自连接来猜 begin 与 end。

下面的查询同时覆盖线程切片和进程异步切片，并补齐进程/线程上下文：

```sql
INCLUDE PERFETTO MODULE slices.with_context;

SELECT
  id AS slice_id,
  ts,
  dur,
  name,
  process_name,
  thread_name,
  track_name
FROM thread_or_process_slice
WHERE process_name = 'com.example.reader'
  AND name GLOB 'Feed.*'
  AND dur >= 0
ORDER BY dur DESC;
```

同步切片通常有 `thread_name`，进程范围异步切片的该列可能为空。`dur = -1` 表示未完成或采集结束时仍开放，统计延迟前应排除并单独报警。

### 9.2 分位数语法

PerfettoSQL 的 `PERCENTILE` 参数使用 0–100 的百分位值。下面的查询计算 P50、P90 和 P99：

```sql
SELECT
  name,
  COUNT(*) AS samples,
  PERCENTILE(dur, 50) / 1e6 AS p50_ms,
  PERCENTILE(dur, 90) / 1e6 AS p90_ms,
  PERCENTILE(dur, 99) / 1e6 AS p99_ms
FROM slice
WHERE name IN ('Feed.queryDb', 'Feed.mapModels')
  AND dur >= 0
GROUP BY name;
```

使用 `0.5`、`0.9`、`0.99` 会把查询写成第 0.5、0.9、0.99 百分位，不能得到 P50/P90/P99。多份 trace 的回归统计还应交给 Batch Trace Processor 或外部统计任务，单次 trace 内的切片不代表独立设备样本。

### 9.3 Counter 查询

应用 Counter 通常挂在 process counter track。下面的查询返回队列深度随时间的变化：

```sql
SELECT
  c.ts,
  c.value,
  pct.name AS counter_name,
  p.name AS process_name
FROM counter c
JOIN process_counter_track pct ON c.track_id = pct.id
JOIN process p ON pct.upid = p.upid
WHERE p.name = 'com.example.reader'
  AND pct.name = 'ImageDecode.queueDepth'
ORDER BY c.ts;
```

Counter 的算术平均值会受到采样频率影响。要计算时间加权平均队列深度，应先把相邻样本扩展成 `[ts, next_ts)` 区间，再按 duration 加权。

### 9.4 不要依赖 `category = 'atrace'`

`slice.category` 对 Track Event category 有明确含义，ATrace slice 的该列通常为空。按 `category = 'atrace'` 过滤可能把目标事件全部丢掉。应用事件宜用进程名、稳定的自定义名称和 track context 定位。

## 10. 高频埋点和 buffer 失真

### 10.1 埋点粒度

以下位置通常有分析价值：

- 启动阶段的配置、数据库、依赖初始化；
- 页面跳转中的数据准备与首帧前工作；
- 一次列表批处理、图片解码或序列化；
- 用户可感知的异步请求；
- 队列、连接和内存状态的低频 Counter。

逐元素循环、每像素处理、每次 Compose 小函数调用等位置容易让 trace 开销支配原始工作。要么把范围提升到 batch，要么采样少量实例，并用 A/B trace 核对埋点对帧时间的影响。

Compose Runtime tracing 有自己的版本、依赖和切片语义，详见 [22.37 Compose Runtime Tracing](../../part5-app/ch22-rendering-practice/37-compose-runtime-tracing-perfetto-integration.md)。不要在每个 `@Composable` 内手工 begin/end，也不要让同步 section 跨过可挂起操作。

### 10.2 Ring buffer 会覆盖旧事件

`RING_BUFFER` 满后覆盖较早数据。出现“十秒采集只剩靠后的几秒”时，应检查：

- buffer 大小；
- ftrace event 与 atrace category 数量；
- 应用自定义事件频率；
- 采集时长；
- 是否同时抓了高吞吐数据源。

增加 buffer 只能缓解容量，不会消除探针效应。更可靠的处理顺序是缩小问题窗口、减少无关数据源、降低埋点频率，再调整 buffer。

### 10.3 生产安全

trace 文件可能包含进程名、线程名、切片名和系统状态。应用自定义名称必须排除：

- 账号、手机号、设备标识；
- URL query、搜索词、消息正文；
- 文件系统中的用户路径；
- token、cookie、密钥；
- 可反推出个人行为的高基数 ID。

trace 采集、上传、保留和分享要遵守产品隐私政策。`Trace.isEnabled()` 不能替代数据分类和脱敏。

## 11. 与 Macrobenchmark 配合

Macrobenchmark 会为每次测量保留 Perfetto trace，应用 section 因此能直接服务于性能门禁：

1. 用稳定 section 包住业务阶段；
2. 用 `TraceSectionMetric` 对公开支持的聚合方式生成 metric；
3. metric 退化时打开对应迭代 trace；
4. 用版本化 PerfettoSQL 继续拆分调度、I/O、Binder 和子切片；
5. 在同设备、同 APK、同 compilation mode 下复测。

`TraceSectionMetric` 适合稳定、低基数 section。任意 SQL 后处理应锁定 Trace Processor/Perfetto 版本，并保留原始 trace。自动化门禁的设备和统计策略见 [14.27 Macrobenchmark 框架与自动化性能门禁](../ch14-other-tools/27-macrobenchmark-automation-gate.md)，Perfetto schema 的版本边界见 [13.1 Perfetto 简介与演进](01-perfetto-intro.md)。

## 12. 排错清单

### 切片完全不出现

- 采集配置是否包含目标 `atrace_apps`；
- 包名是否对应正在运行的进程；
- 事件是否发生在采集窗口内；
- `Trace.isEnabled()` 在复现期间是否返回 true；
- Macrobenchmark 是否运行了预期 variant 和目标包；
- trace 是否因 buffer 覆盖丢掉早期内容。

### 同步切片栈错位

- 每个 begin 是否在同线程有且只有一个 end；
- 异常、early return 和取消路径是否由 `finally` 保护；
- 同步 section 是否跨协程挂起点；
- 第三方 callback 是否换了线程。

### 异步切片异常拉长或互相交叉

- begin/end 的名称是否逐字符一致；
- cookie 是否在重叠期间保持唯一；
- 取消与超时路径是否结束 section；
- 进程被杀时未结束的 slice 是否被错误纳入统计；
- UI 的视觉堆叠是否被误读成父子关系。

### SQL 查不到事件

- 先运行 `SELECT * FROM slice WHERE name GLOB '*关键字*' LIMIT 20`；
- 不要强制 `category = 'atrace'`；
- 同步切片查 `thread_slice`，异步切片查 `process_slice`，或统一查 `thread_or_process_slice`；
- `PERCENTILE` 使用 0–100；
- incomplete slice 的 `dur` 可能为负值。

## 13. 源码核对表

| 结论 | Android 17 证据 |
|---|---|
| 公开 API 只有 6 个方法 | `frameworks/base/core/java/android/os/Trace.java` |
| `beginSection` 上限为 127 个 Java code unit | `Trace.java:507-516` |
| JNI 清理换行与 `|` | `frameworks/base/core/jni/android_os_Trace.cpp:32-60` |
| Android 17 存在 ATrace/Perfetto backend 选择 | `frameworks/native/libs/tracing_perfetto/tracing_perfetto.cpp` |
| tag 通过 property serial 变化刷新 | `system/core/libcutils/trace-dev.inc:79-95` |
| trace marker 打开路径 | `system/core/libcutils/trace-dev.cpp:31-43` |
| `B/E/S/F/C` marker 编码 | `system/core/libcutils/trace-dev.cpp:72-116` |
| `ATRACE_TAG_APP` 为 `1 << 12` | `system/core/libcutils/include/cutils/trace.h:50-78` |
| AIDL server 事务由 tag 控制的 slice 包围 | `frameworks/native/libs/binder/Binder.cpp:479-500` |

行号对应 `android-17.0.0_r1`，后续分支可能移动。评审结论应同时记录 tag 和文件路径，避免用浮动 `main` 的行号解释量产系统。

## 参考资料

- [Android 17 `Trace.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/os/Trace.java)
- [Android 17 `android_os_Trace.cpp`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/jni/android_os_Trace.cpp)
- [Android 17 `tracing_perfetto.cpp`](https://android.googlesource.com/platform/frameworks/native/+/android-17.0.0_r1/libs/tracing_perfetto/tracing_perfetto.cpp)
- [Android 17 `trace-dev.cpp`](https://android.googlesource.com/platform/system/core/+/android-17.0.0_r1/libcutils/trace-dev.cpp)
- [Android 17 `trace-dev.inc`](https://android.googlesource.com/platform/system/core/+/android-17.0.0_r1/libcutils/trace-dev.inc)
- [Android 17 `cutils/trace.h`](https://android.googlesource.com/platform/system/core/+/android-17.0.0_r1/libcutils/include/cutils/trace.h)
- [Android 17 `Binder.cpp`](https://android.googlesource.com/platform/frameworks/native/+/android-17.0.0_r1/libs/binder/Binder.cpp)
- [`android.os.Trace` API reference](https://developer.android.com/reference/android/os/Trace)
- [AndroidX Tracing releases](https://developer.android.com/jetpack/androidx/releases/tracing)
- [AndroidX Tracing API](https://developer.android.com/reference/kotlin/androidx/tracing/package-summary)
- [Android NDK tracing API](https://developer.android.com/ndk/reference/group/tracing)
- [Perfetto ATrace instrumentation](https://perfetto.dev/docs/getting-started/atrace)
- [Perfetto ATrace data source](https://perfetto.dev/docs/data-sources/atrace)
- [PerfettoSQL common queries](https://perfetto.dev/docs/analysis/common-queries)
- [PerfettoSQL `slices.with_context`](https://perfetto.dev/docs/analysis/stdlib-docs#slices-with_context)
- [Android 17 common kernel tag](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6)
