---
title: "序列化性能对比与选型"
chapter: "24.3"
section: "24.3"
status: finalized
applicable_versions: "Android 10 (API 29) - Android 17 (API 37)"
last_verified: "2026-06-30"
last_verified_against: "AOSP android-17.0.0_r1 + Android Developers docs + upstream library docs"
confidence: medium
drafted_date: "2026-05-14"
reviewed_by: openclaw-task6
reviewed_date: "2026-05-14"
task6_result: pass-light-edit
polish_count: 1
sources:
  - type: aosp
    path: "frameworks/base/core/java/android/os/Parcel.java"
  - type: aosp
    path: "frameworks/base/core/java/android/os/TransactionTooLargeException.java"
  - type: official
    path: "https://developer.android.com/reference/android/os/Parcelable"
  - type: official
    path: "https://developer.android.com/topic/performance/benchmarking/microbenchmark-overview"
  - type: official
    path: "https://github.com/google/gson/blob/main/README.md"
  - type: official
    path: "https://github.com/square/moshi/blob/master/README.md"
  - type: official
    path: "https://github.com/Kotlin/kotlinx.serialization/blob/master/README.md"
  - type: official
    path: "https://kotlinlang.org/docs/serialization.html"
  - type: official
    path: "https://square.github.io/moshi/"
  - type: official
    path: "https://android.googlesource.com/platform/external/kotlinx.serialization/+/refs/heads/upstream-1.2.0-release/docs/json.md"
  - type: official
    path: "https://protobuf.dev/overview/"
  - type: official
    path: "https://github.com/google/flatbuffers/blob/master/README.md"
  - type: clippings
    path: "Clippings/Android 性能优化 - 原理：重新认识应用的速度优化.md"
  - type: clippings
    path: "Clippings/Android 性能优化 - 缓存优化：冷热端分离+重排序，提升缓存命中率.md"
  - type: clippings
    path: "Clippings/Android 性能优化 - 物理内存优化实战：Java Heap 内存优化.md"
tags: [serialization, json, protobuf, parcelable, flatbuffers]
related_chapters: ["24.4", "1.4", "21.1"]
pipeline_stage: ready-to-publish
task6_state: reviewed
last_task6_audit: "2026-07-06"
task9_state: reviewed
last_task2a_at: "2026-05-14T08:20:00+08:00"
task9_result: auto-fixed
task2b_state: fixed
task9_reviewed_by: "openclaw-task9"
task9_reviewed_date: "2026-06-30"
last_task9_at: "2026-06-30T21:20:00+08:00"
last_task9_audit: "2026-06-30"
last_task9_audit_log: "logs/deep-review/2026-06-30-21-audit.md"
last_task9_review_log: "logs/deep-review/2026-06-30-21-audit.md"
last_task9_autofix_at: "2026-06-30"
task9_review_notes: "2026-06-30 Task9 idle audit auto-fix: 将 Parcel.java / TransactionTooLargeException.java 的 AOSP 验证口径从 master snapshot 固定到 android-17.0.0_r1；源码行为与 Android 17 tag 一致。无待入 queue P0/P1。"
deepseek_cn_review_state: done
last_deepseek_cn_review_at: 2026-07-01
---

# 序列化性能对比与选型

## 为什么要了解序列化性能对比与选型

平台源码锚点是 Android 17 / API 37 / `android-17.0.0_r1`；涉及 Binder 驱动时，内核锚点是 `android17-6.18-2026-06_r6`。JSON、Protocol Buffers、FlatBuffers 等库独立于 Android 平台发布，行为要以项目锁定的依赖版本为准。

序列化会消耗 CPU，产生临时对象，也会改变包体积、混淆规则和协议演进方式。问题通常表现为冷启动解析配置时的 CPU 区段、网络响应后的分配与 GC、Binder 调用两侧的编解码，或者只在 R8 发布包中出现的字段丢失。

选型要先确定数据边界：

- 进程内函数调用直接传对象，不需要序列化。
- 网络与持久化需要可演进、跨版本的格式，例如 JSON 或 Protocol Buffers。
- Android 组件参数、瞬时状态和跨进程调用使用 `Parcelable`、`Bundle` 或 AIDL 支持的类型。
- 大型二进制内容应通过文件描述符、内容 URI 或分页接口传递，不应内嵌进一个 Binder 事务。

Binder 机制见 [1.4 Binder IPC](../../part1-fundamentals/ch01-architecture/04-binder.md)，启动观测见 [21.1 启动分析](../ch21-startup/01-startup-analysis.md)，网络协议设计见 [24.4 网络架构](04-network-architecture.md)。

## JSON（Gson / Moshi / kotlinx.serialization）性能对比

JSON 便于抓包、日志检查和跨语言协作。解析端仍要扫描词法单元、解码字符串、匹配字段并构造对象；若先建 `JsonElement` 或类似树结构，再转换成业务对象，还会增加一轮对象分配。小响应中的成本可能低于网络等待，大列表、配置恢复和启动预读则需要单独测量。

### 三个库的当前边界

Gson 当前处于维护模式。其项目说明明确指出：Gson 以 Java 为主要目标，不支持 Kotlin 非空类型和默认参数等语言语义；开放式反射也不适合 Android 发布包的压缩、优化与混淆流程，因此不再推荐用 Gson 处理 Android JSON。存量项目不必仅因这段说明立即重写，但需要固定 R8 规则，并用混淆后的发布制品验证字段名、构造方式和泛型适配器。新 Kotlin 数据模型宜优先评估代码生成方案。

[Gson 项目说明](https://github.com/google/gson)

Moshi 同时支持 Java 和 Kotlin。Kotlin 类可以使用反射适配器，也可以用 KSP 在编译期生成适配器；`@JsonClass(generateAdapter = true)` 会让 Moshi 选择生成代码。代码生成减少运行时反射依赖，并让 R8 规则更容易审计，但不保证在每种数据形状上都比其他库快。迁移 Gson 时还要逐项验证空值、默认值、枚举、时间格式和自定义适配器，不能按 API 外形相似直接替换。

[Moshi 项目说明](https://github.com/square/moshi)

`kotlinx.serialization` 通过 Kotlin 编译器插件为 `@Serializable` 类型生成序列化器，适合受控的 Kotlin 与 Kotlin Multiplatform 数据模型。它的 JSON 格式 API 已稳定；截至 2026 年 6 月，官方仍把 CBOR、Protocol Buffers、HOCON 和 Properties 格式列为实验 API。`kotlinx-serialization-protobuf` 也不能与 `protoc` 生成的 Java/Kotlin API 混为一谈，跨端协议采用它之前要单独验证线格式和演进规则。

[Kotlin 序列化格式状态](https://kotlinlang.org/docs/serialization.html)

### 先验证语义，再比较速度

同一份 JSON 在不同库中未必得到相同对象。基准测试前要固定以下规则：

| 规则 | 需要验证的内容 |
| --- | --- |
| 未知字段 | 忽略、报警还是拒绝 |
| 缺失与 `null` | 是否使用默认值，非空字段如何失败 |
| 数字 | 整数范围、浮点特殊值、字符串数字是否接受 |
| 枚举 | 未知枚举值的处理 |
| 多态 | 类型判别字段、未知子类型与安全范围 |
| 字段名 | `@SerializedName`、`@Json`、`@SerialName` 是否完全对应 |
| 发布包 | R8 后生成代码、反射规则和自定义适配器是否仍可用 |

应用场景可以按下面的顺序筛选：

| 场景 | 候选方案 | 工程判断 |
| --- | --- | --- |
| 新 Kotlin 模块，模型可加注解 | kotlinx.serialization JSON 或 Moshi KSP | 对比协议语义、构建插件、包体积与目标路径数据 |
| Java/Kotlin 混合 | Moshi 代码生成或经过约束的 Gson | Java 模型覆盖率与迁移回归成本更重要 |
| 存量 Gson | 保留并补发布包测试，按路径迁移 | 不把一次性全量替换当作性能优化 |
| 大响应，只读取少量字段 | 流式读取或拆分接口 | 避免构造完整 JSON 树和全部传输对象 |
| 客户端与服务端共同维护协议 | Protocol Buffers | 评估字段演进、运行库、压缩后大小和调试工具 |

### 用可复现的基准测试比较

下面的代码只比较“同一字符串解码成同一对象”的稳态成本。两个数据类同时启用 kotlinx.serialization 和 Moshi 代码生成；夹具校验放在计时循环之外，`BlackHole.consume()` 防止编译器或 R8 删除未使用结果。

```kotlin
@Serializable
@JsonClass(generateAdapter = true)
data class BenchmarkFeed(
    val items: List<BenchmarkItem> = emptyList()
)

@Serializable
@JsonClass(generateAdapter = true)
data class BenchmarkItem(
    val id: Long,
    val title: String,
    val tags: List<String> = emptyList()
)

@RunWith(AndroidJUnit4::class)
class FeedJsonBenchmark {
    @get:Rule
    val benchmarkRule = BenchmarkRule()

    private val fixture = InstrumentationRegistry.getInstrumentation()
        .context.assets.open("feed_payload.json")
        .bufferedReader()
        .use { it.readText() }

    private val kotlinxJson = Json {
        ignoreUnknownKeys = true
    }

    private val moshi = Moshi.Builder().build()
    private val moshiAdapter = moshi.adapter(BenchmarkFeed::class.java)

    @Before
    fun verifyFixture() {
        val kotlinxResult = kotlinxJson.decodeFromString<BenchmarkFeed>(fixture)
        val moshiResult = checkNotNull(moshiAdapter.fromJson(fixture))
        assertEquals(kotlinxResult, moshiResult)
    }

    @Test
    fun decodeWithKotlinxSerialization() = benchmarkRule.measureRepeated {
        val result = kotlinxJson.decodeFromString<BenchmarkFeed>(fixture)
        BlackHole.consume(result)
    }

    @Test
    fun decodeWithMoshiCodegen() = benchmarkRule.measureRepeated {
        val result = checkNotNull(moshiAdapter.fromJson(fixture))
        BlackHole.consume(result)
    }
}
```

这段测试没有测首次类加载、读取文件、网络等待或对象到领域模型的转换，也没有比较编码。它适合隔离解码函数，不代表启动或接口的端到端结果。项目还应分别建立编码用例、小型与大型夹具、正常与缺字段夹具；库配置必须与发布代码一致。

Jetpack Microbenchmark 会预热代码，记录执行时间和分配次数，并把明细写入 JSON 报告。较新的插件在满足官方版本要求时默认完整编译基准测试 APK；若需要验证 R8 后的差异，应按文档配置最小化，不要拿可调试包或模拟器结果决定线上选型。首次使用成本和用户路径仍要由 Macrobenchmark 与 Perfetto 验证。

[Microbenchmark 概览](https://developer.android.com/topic/performance/benchmarking/microbenchmark-overview) · [编写 Microbenchmark](https://developer.android.com/topic/performance/benchmarking/microbenchmark-write) · [`BlackHole`](https://developer.android.com/reference/kotlin/androidx/benchmark/BlackHole)

## Protocol Buffers 与 FlatBuffers

Protocol Buffers 通过字段编号编码结构化数据，并为各语言生成访问代码。它适合客户端、服务端和缓存格式由同一套协议管理的场景。是否比 JSON 更小、更快仍取决于字段类型、字符串比例、压缩、运行库和访问方式；应比较压缩后的线上字节数与端到端 CPU，而不是引用公开排名。

模式演进比格式名称更重要。字段编号发布后不能改作其他含义；删除字段时应同时保留编号和名称，阻止后续复用。二进制 Proto3 会保留未知字段并在再次编码时写回，但转换成 JSON 或逐字段复制到新消息可能丢失未知字段。标量字段还要决定是否需要显式记录字段存在性（presence），否则“未提供”和“默认值”可能无法区分。

下面的模式片段演示字段删除和存在性处理。`legacy_title` 与编号 4 都被保留；`subtitle` 使用 `optional`，使生成代码能够区分缺失和空字符串。

```proto
syntax = "proto3";

package feed.v1;

message FeedItem {
  reserved 4;
  reserved "legacy_title";

  int64 id = 1;
  string title = 2;
  optional string subtitle = 3;
  repeated string tags = 5;
}
```

这个片段只是线格式的一部分。发布检查还要让新旧客户端互相读写夹具，验证未知字段、枚举、默认值和重编码路径。Android 端可以评估 Protocol Buffers lite 运行库；官方生成代码文档说明，lite 运行库更适合资源受限设备，但会舍弃描述符、反射等能力。运行库和 `protoc` 版本也应纳入依赖锁定。

[Protocol Buffers 概览](https://protobuf.dev/overview/) · [Proto3 演进规则](https://protobuf.dev/programming-guides/proto3/#updating) · [Java lite 运行库](https://protobuf.dev/reference/java/java-generated/#runtime-library)

FlatBuffers 的目标是直接从序列化数据读取字段，省去先解析或解包成完整对象的步骤。它适合结构稳定、读多写少、常只访问局部字段的大型数据，例如离线索引或资源清单。它并不会自动使用 `mmap`；应用需要自己把文件映射成可访问的字节缓冲区，而且映射也不会消除页错误与存储 I/O。生成访问器、构建器、模式演进、输入校验和调试工具都要一起评估。

[FlatBuffers 项目说明](https://github.com/google/flatbuffers)

选型时可用下面的比较维度：

| 维度 | JSON | Protocol Buffers | FlatBuffers |
| --- | --- | --- | --- |
| 人工检查 | 直接可读 | 需要 `.proto` 与解码工具 | 需要 `.fbs` 与工具 |
| 访问方式 | 解析为对象或流式读取 | 解析为生成消息 | 可从字节缓冲区按字段访问 |
| 演进约束 | 由字段名与应用规则管理 | 字段编号、字段存在性、未知字段 | 模式兼容规则与生成代码 |
| Android 代价 | 解析、字符串和对象分配 | 运行库、生成代码和消息分配 | 原生/Java 制品、构建器与缓冲区生命周期 |
| 适用判断 | 协议变化快、可读性重要 | 跨端稳定协议、高频编解码 | 大型稳定数据、局部读取 |

不要把现有 JSON 传输对象逐字段翻译成 `.proto` 或 `.fbs` 后直接复用为界面对象。网络模式、持久化模式和界面状态有不同的演进周期；在仓储层做显式转换，能让默认值和兼容逻辑有清晰归属。

## Parcelable vs Serializable

`Parcel` 是 Android 的高效 IPC 传输容器，不是通用序列化格式。Android 17 的 `Parcel.java` 明确禁止把 Parcel 数据写入持久化存储，因为底层实现变化可能让旧数据无法读取。磁盘缓存和网络协议不应在 Parcelable 与 Serializable 之间二选一，而应使用有版本规则的持久化格式。

在组件参数或跨进程接口中，优先使用 SDK/AIDL 原生类型或明确的 Parcelable。`writeParcelable()` 会同时写类名和数据；`writeTypedObject()`、`writeTypedList()` 等类型明确的 API 由读取方提供 `Parcelable.Creator`，不写对象类信息，因此更紧凑。AIDL 已知参数类型时会生成相应编解码代码，业务层不应再把对象包进 `Serializable` 或无类型的嵌套容器。

Android 17 的 `writeValue()` 把 `Serializable` 放在兜底分支，并注明通用 Java 序列化开销很大。它需要处理类描述和对象图，还会受类结构、`serialVersionUID` 与混淆影响。已有低频接口可以在测量后保留，新接口不应只因 `implements Serializable` 写起来短就选择它。

下面的代码展示 `@Parcelize` 数据对象和一个调试期大小估算函数。`writeTypedObject()` 与读取端已知类型的场景一致；`Parcel.dataSize()` 给出本地编码后的字节数。

```kotlin
@Parcelize
data class UserCard(
    val id: Long,
    val name: String,
    val avatarUrl: String?
) : Parcelable

fun parcelSizeBytes(card: UserCard): Int {
    val parcel = Parcel.obtain()
    return try {
        parcel.writeTypedObject(card, 0)
        parcel.dataSize()
    } finally {
        parcel.recycle()
    }
}
```

这个数值只用于发现对象随数据增长的趋势，不包括 Binder 命令、对象偏移表、同进程其他在途事务或返回值，不能当作安全阈值。`@Parcelize` 也只生成读写代码，不提供持久化版本协议。使用 `@RawValue` 时，插件会退回 `Parcel.writeValue()`；高频 IPC 中应审计该属性最终采用的类型分支。

[Android 17 `Parcel.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/os/Parcel.java) · [Parcelize 文档](https://developer.android.com/kotlin/parcelize)

## 序列化在启动和 IPC 中的性能影响

### 启动路径：区分稳态速度和首次使用成本

`Application.onCreate()`、初始化 `ContentProvider`、首屏配置恢复和接口返回后的批量对象构造都可能位于 TTID/TTFD 路径。官方启动文档也把反序列化列为应在启动瓶颈中检查的工作。处理顺序是：

- 只解析首帧或可交互状态需要的数据，其余数据延后或分页。
- 若只读取少量字段，使用流式读取或调整接口，不先构建完整 JSON 树。
- 复用应用级格式配置和 Moshi 适配器；Moshi 返回的适配器可跨线程复用。
- 在真实冷启动中测首次类加载、生成序列化器初始化、磁盘读取、解析和领域转换。
- 若解析后的内容需要跨启动复用，把它写成有版本的数据库或文件格式，不能持久化 Parcel。

Microbenchmark 的预热与完整编译适合比较稳态函数；Macrobenchmark 和 Perfetto 才能回答“这次解析是否延迟首帧或可交互状态”。可在解析边界加窄范围的应用追踪区段，并结合采样调用栈、分配与 GC 判断时间花在词法扫描、对象构造还是业务转换。

[应用启动性能](https://developer.android.com/topic/performance/vitals/launch-time)

### Android 17 Binder 缓冲区边界

“Binder 每笔事务有 1 MB”是不准确的。Android 17 的 `ProcessState.cpp` 把普通 `/dev/binder` 映射大小定义为 `1 MiB - 2 × 运行时页大小`。`android17-6.18-2026-06_r6` 的 `binder_alloc.c` 允许的映射上限是 4 MiB，但实际缓冲区取用户空间请求值与该上限的较小者。平台 native 层请求约 1 MiB，所以 `TransactionTooLargeException` 文档将当前容量概括为 1 MB；在 16 KiB 页设备上，表达式还会扣除两个 16 KiB 页。

这块空间属于进程，并由该进程正在处理的 Binder 事务共享，不是某次调用的独占配额。单个参数看起来小，也可能在并发调用、返回值和其他系统交互同时发生时失败。`TransactionTooLargeException` 只是启发式异常，客户端不能确定请求未发送，还是服务端处理后无法返回结果；重试有副作用的调用前必须使用幂等协议或查询提交状态。

状态保存数据也会经由系统进程参与 Binder 传输。Android 官方建议将这类数据保持在 50 KB 以下；这个建议只针对状态保存，不是所有 Binder 接口的通用上限。状态中应保存恢复界面所需的标识和少量输入，不保存列表、位图或完整接口响应。

[Android 17 `ProcessState.cpp`](https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/libs/binder/ProcessState.cpp) · [6.18 内核 `binder_alloc.c`](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/drivers/android/binder_alloc.c) · [Android 17 `TransactionTooLargeException.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/os/TransactionTooLargeException.java) · [Parcelable 与 Bundle 建议](https://developer.android.com/guide/components/activities/parcelables-and-bundles)

大型结果应改变接口形状：

- 列表按稳定游标分页，避免重复传整页已有数据。
- 大型二进制数据通过受权限保护的内容 URI 或 `ParcelFileDescriptor` 读取。
- 进程间只传记录标识，让接收方通过明确的数据接口查询。
- 高频小调用可以在保持事务时长可控的前提下批量化，并验证尾延迟和失败语义。

## 建立序列化选型基线

公开基准测试只能用于发现候选项。应用自己的字段分布、字符串长度、R8 配置、依赖版本、设备 CPU 和协议压缩都会改变结果。至少建立四组可复现数据：

| 基线 | 记录内容 | 回答的问题 |
| --- | --- | --- |
| 编解码 Microbenchmark | 时间、分配次数、制品配置、设备与夹具哈希 | 单个函数的稳态差异 |
| 冷启动 Macrobenchmark | TTID、TTFD、解析追踪区段、GC 与类加载 | 首次解析是否影响用户路径 |
| 网络或磁盘端到端测试 | 压缩前后字节数、读写时间、领域转换 | 格式变化是否改善完整链路 |
| IPC 压测 | 本地 Parcel 估算、并发数、往返延迟、失败与重试 | 接口是否需要分页或外部数据通道 |

发布前还要运行协议回归：

- 当前解码器读取所有仍受支持的历史夹具。
- 新旧编码器与解码器交叉验证，检查缺失字段、未知字段和默认值。
- R8 发布制品执行相同测试，覆盖反射、生成代码和自定义适配器。
- 目标设备覆盖 Android 10 / API 29 与 Android 17 / API 37；包含 16 KiB 页设备时，额外观察 Binder 缓冲区与原生序列化库。
- 畸形、过大和过深输入能够受控失败，不把原始用户数据写入性能日志。

## 小结

JSON 库先比较协议语义和发布包稳定性，再比较速度；Gson 存量代码可以渐进迁移，新 Kotlin 模型宜优先评估生成代码。Protocol Buffers 依赖严格的字段编号与兼容测试，FlatBuffers 的直接访问优势只在目标数据形状中成立。Parcelable 服务于 Android 瞬时传输，不能用于持久化；Android 17 的 Binder 容量还是进程共享资源。优化顺序应从减少数据、延迟非必要解析、分页和调整接口开始，换库必须由同一业务路径上的测量结果支持。
