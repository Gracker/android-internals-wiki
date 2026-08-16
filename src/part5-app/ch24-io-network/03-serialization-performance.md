---
title: "序列化性能对比与选型"
chapter: "24.3"
section: "24.3"
status: finalized
applicable_versions: "Android 10 (API 29) - Android 17 (API 37)"
last_verified: "2026-08-15"
last_verified_against: "AOSP android-17.0.0_r1; Android common kernel android17-6.18-2026-06_r6; current Android Developers Benchmark, Parcelize, saved-state and launch docs; Gson, Moshi, kotlinx.serialization 1.11.0, Protocol Buffers and FlatBuffers upstream docs"
confidence: high
sources:
  - type: aosp
    path: "frameworks/base/core/java/android/os/Parcel.java @ android-17.0.0_r1"
  - type: aosp
    path: "frameworks/base/core/java/android/os/TransactionTooLargeException.java @ android-17.0.0_r1"
  - type: aosp
    path: "frameworks/native/libs/binder/ProcessState.cpp @ android-17.0.0_r1"
  - type: aosp-kernel
    path: "drivers/android/binder_alloc.c @ android17-6.18-2026-06_r6"
  - type: official
    path: "https://developer.android.com/reference/android/os/Parcelable"
  - type: official
    path: "https://developer.android.com/topic/performance/benchmarking/microbenchmark-overview"
  - type: official
    path: "https://github.com/google/gson/blob/main/README.md"
  - type: official
    path: "https://github.com/google/gson/blob/main/Troubleshooting.md"
  - type: official
    path: "https://github.com/square/moshi/blob/master/README.md"
  - type: official
    path: "https://square.github.io/moshi/1.x/moshi/moshi/com.squareup.moshi/-json-adapter/index.html"
  - type: official
    path: "https://github.com/Kotlin/kotlinx.serialization/blob/master/README.md"
  - type: official
    path: "https://kotlinlang.org/docs/serialization.html"
  - type: legacy-reference-preserved
    path: "https://square.github.io/moshi/"
  - type: legacy-reference-preserved
    path: "https://android.googlesource.com/platform/external/kotlinx.serialization/+/refs/heads/upstream-1.2.0-release/docs/json.md"
  - type: official
    path: "https://protobuf.dev/overview/"
  - type: official
    path: "https://protobuf.dev/programming-guides/proto3/"
  - type: official
    path: "https://protobuf.dev/programming-guides/field_presence/"
  - type: official
    path: "https://protobuf.dev/reference/java/java-generated/"
  - type: official
    path: "https://github.com/google/flatbuffers/blob/master/README.md"
  - type: official
    path: "https://developer.android.com/topic/performance/benchmarking/microbenchmark-write"
  - type: official
    path: "https://developer.android.com/guide/components/activities/parcelables-and-bundles"
  - type: official
    path: "https://developer.android.com/kotlin/parcelize"
  - type: official
    path: "https://developer.android.com/topic/performance/vitals/launch-time"
  - type: clippings
    path: "Clippings/Android 性能优化 - 原理：重新认识应用的速度优化.md"
  - type: clippings
    path: "Clippings/Android 性能优化 - 缓存优化：冷热端分离+重排序，提升缓存命中率.md"
  - type: clippings
    path: "Clippings/Android 性能优化 - 物理内存优化实战：Java Heap 内存优化.md"
tags: [serialization, json, protobuf, parcelable, flatbuffers]
related_chapters: ["24.4", "1.4", "21.1"]
pipeline_stage: finalized
last_review_finalize_at: "2026-08-15T09:53:21+08:00"
last_review_finalize_run_id: "20260815-095321-gracker-writing-review"
last_draft_polish_at: "2026-08-15T09:53:21+08:00"
last_draft_polish_run_id: "20260815-095321-gracker-writing"
task6_state: reviewed
task9_state: reviewed
task2b_state: fixed
---

# 序列化性能对比与选型

## 序列化成本出现在哪里

平台源码锚点是 Android 17 / API 37 / `android-17.0.0_r1`；涉及 Binder 驱动时，内核锚点是 `android17-6.18-2026-06_r6`。JSON、Protocol Buffers、FlatBuffers 等库独立于 Android 平台发布，行为要以项目锁定的依赖版本为准。

序列化把内存中的对象编码成可传输或保存的数据，反序列化则把这些数据还原成运行时对象。两步都会消耗 CPU、产生临时对象，还会影响安装包体积、代码优化规则和协议升级方式。问题通常表现为冷启动解析配置时在 Perfetto（Android 系统追踪工具）中出现较长区段、网络响应后频繁分配对象并触发 GC（Garbage Collection，垃圾回收）、Binder 调用两侧花时间编解码，或者字段只在经过 R8 缩减、优化与混淆的发布包中丢失。

选型要先确定数据边界：

- 进程内函数调用直接传对象，不需要序列化。
- 网络与持久化需要可演进、跨版本的格式，例如 JSON 或 Protocol Buffers。
- Android 组件参数、瞬时状态和跨进程调用使用 `Parcelable`、`Bundle` 或 AIDL（Android Interface Definition Language，Android 接口定义语言）支持的类型。
- 大型二进制内容应通过文件描述符、Content URI（由 ContentProvider 授权访问的数据地址）或分页接口传递，不应内嵌进一个 Binder 事务。

Binder 机制见 [1.4 Binder IPC](../../part1-fundamentals/ch01-architecture/04-binder.md)，启动观测见 [21.1 启动分析](../ch21-startup/01-startup-analysis.md)，网络协议设计见 [24.4 网络架构](04-network-architecture.md)。

## JSON（Gson / Moshi / kotlinx.serialization）性能对比

JSON 便于抓包、日志检查和跨语言协作。解析端仍要扫描括号、字段名、数字等词法单元，解码字符串、匹配字段并构造对象；若先建立 `JsonElement` 等表示完整 JSON 层级的树，再转换成业务对象，还会多分配一批节点对象。小响应的解析时间可能低于网络等待，大列表、配置恢复和启动预读则需要单独测量。

### 三个库的当前边界

截至本轮复核，Gson 仍处于维护模式：项目会继续修复已有问题，但通常不再增加大型功能。其项目说明明确指出：Gson 以 Java 为主要目标，不支持 Kotlin 非空类型和默认参数等语言语义；它还会在运行时反射任意模型字段，这种开放式反射难以与 Android 发布包的缩减、优化和混淆配合，因此官方不再推荐用 Gson 处理 Android JSON。存量项目不必仅因这段说明立即重写，但应限制允许反射的模型、用 `@SerializedName` 为字段声明稳定名称，并用经过 R8 处理的发布 APK 或 AAB 验证字段名、构造方式和泛型适配器。新 Kotlin 数据模型宜优先评估代码生成方案。

[Gson 项目说明](https://github.com/google/gson)

Moshi 同时支持 Java 和 Kotlin。Kotlin 类可以使用反射适配器，也可以通过 KSP（Kotlin Symbol Processing，Kotlin 符号处理）在编译期生成适配器；`@JsonClass(generateAdapter = true)` 会让 Moshi 选择生成代码。代码生成减少运行时反射依赖，并让 R8 规则更容易审计，但不保证在每种数据形状上都比其他库快。迁移 Gson 时还要逐项验证空值、默认值、枚举、时间格式和自定义适配器，不能因为方法名和用法看起来相近就直接替换。

[Moshi 项目说明](https://github.com/square/moshi)

`kotlinx.serialization` 通过 Kotlin 编译器插件为 `@Serializable` 类型生成序列化器，适合受控的 Kotlin 与 Kotlin Multiplatform 数据模型。截至 2026-08-15，官方格式列表中仍只有 JSON API 稳定；CBOR（二进制对象表示）、Protocol Buffers、HOCON（面向人工编辑的配置格式）和 Properties（键值配置）都是实验 API，调用接口可能继续变化。`kotlinx-serialization-protobuf` 也不同于由 `protoc`（Protocol Buffers 编译器）生成的 Java/Kotlin API，跨端协议采用它之前要单独验证二进制格式和升级规则。

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

只有这些行为一致，速度结果才是在比较实现成本；若一个库忽略未知字段、另一个库直接失败，耗时差异也包含了语义差异。

应用场景可以按下面的顺序筛选：

| 场景 | 候选方案 | 工程判断 |
| --- | --- | --- |
| 新 Kotlin 模块，模型可加注解 | kotlinx.serialization JSON 或 Moshi KSP | 对比协议语义、构建插件、包体积与目标路径数据 |
| Java/Kotlin 混合 | Moshi 代码生成或经过约束的 Gson | Java 模型覆盖率与迁移回归成本更重要 |
| 存量 Gson | 保留并补发布包测试，按路径迁移 | 不把一次性全量替换当作性能优化 |
| 大响应，只读取少量字段 | 流式读取或拆分接口 | 避免构造完整 JSON 树和全部传输对象 |
| 客户端与服务端共同维护协议 | Protocol Buffers | 评估字段演进、运行库、压缩后大小和调试工具 |

这张表只用于缩小候选范围。项目仍要用相同数据、相同发布配置和相同设备验证结果。

### 用可复现的基准测试比较

下面的设备端 Microbenchmark 只比较“同一字符串解码成同一对象”的稳态成本；稳态指代码完成预热后重复执行时的表现。两个数据类同时启用 kotlinx.serialization 和 Moshi 代码生成。固定输入样本（`test fixture`，下称测试样本）的结果校验放在计时循环之外，`BlackHole.consume()` 则让编译器和 R8 不能因为结果无人使用而删除被测代码。

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

这段测试没有测首次类加载、读取文件、网络等待或对象到业务模型的转换，也没有比较编码。它适合隔离解码函数，不代表启动或接口从输入到结果的完整耗时。项目还应分别建立编码用例、小型与大型测试样本、正常与缺字段样本；库配置必须与发布代码一致。

Jetpack Microbenchmark 会预热代码，记录执行时间和对象分配次数，并把明细写入 JSON 报告。使用 Benchmark 1.3.0-beta01 以上和 Android Gradle Plugin 8.4.0 以上版本时，`androidx.benchmark` 插件默认对基准测试 APK 做 AOT（Ahead-of-Time，运行前）完整编译；这不等于 R8 缩减与混淆。若要验证 R8 处理后的差异，库模块需使用 AGP 8.3 以上并单独启用测试最小化。不要用可调试包或模拟器结果决定生产环境选型；首次使用成本和完整用户路径仍要由 Macrobenchmark（从应用外部测量启动、滚动等场景）与 Perfetto 系统追踪验证。

[Microbenchmark 概览](https://developer.android.com/topic/performance/benchmarking/microbenchmark-overview) · [编写 Microbenchmark](https://developer.android.com/topic/performance/benchmarking/microbenchmark-write) · [`BlackHole`](https://developer.android.com/reference/kotlin/androidx/benchmark/BlackHole)

## Protocol Buffers 与 FlatBuffers

Protocol Buffers 为每个字段分配唯一编号，并把编号写入二进制数据，再为各语言生成读写代码。它适合客户端、服务端和缓存格式由同一套协议定义管理的场景。是否比 JSON 更小、更快，仍取决于字段类型、字符串比例、压缩方式、运行库和访问方式；应比较生产网络实际压缩后的字节数与编解码全程的 CPU 时间，不能直接引用公开排名。

协议结构怎样升级比格式名称更重要。字段编号发布后不能改作其他含义；删除字段时应同时保留编号和名称，阻止后续复用。Proto3 解析二进制消息时会保存当前代码不认识的字段，并在重新编码同一消息时写回；转换成 JSON，或逐字段复制到新消息，都可能丢失这些未知字段。数字、布尔值、字符串等基本类型还要决定是否显式记录字段存在性（`presence`，即区分“没有提供”与“提供了默认值”）。

下面的 `.proto` 定义演示字段删除和存在性处理。`legacy_title` 与编号 4 都被保留；`subtitle` 使用 `optional`，使生成代码能够区分缺失和空字符串。

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

这个片段只是二进制协议的一部分。发布检查还要让新旧客户端互相读写固定测试样本，验证未知字段、枚举、默认值和重新编码路径。Android 端可以评估 Protocol Buffers `lite` 精简运行库；官方生成代码文档说明，它更适合资源受限设备，但不提供描述符（运行时描述消息与字段的元数据）、嵌套 Builder 和反射能力。运行库与 `protoc` 编译器版本也要一起固定。

[Protocol Buffers 概览](https://protobuf.dev/overview/) · [Proto3 演进规则](https://protobuf.dev/programming-guides/proto3/#updating) · [Java lite 运行库](https://protobuf.dev/reference/java/java-generated/#runtime-library)

FlatBuffers 的目标是直接从序列化字节中读取字段，省去先解析或解包成完整对象的步骤。它适合结构稳定、读多写少、经常只访问局部字段的大型数据，例如离线索引或资源清单。它不会自动调用 `mmap`（把文件映射到进程虚拟地址空间）；应用要自行提供可访问的字节缓冲区，而内存映射仍可能因页面尚未载入而触发页错误和存储 I/O。生成访问器、构建器、协议结构升级、输入校验和调试工具都要一起评估。

[FlatBuffers 项目说明](https://github.com/google/flatbuffers)

选型时可用下面的比较维度：

| 维度 | JSON | Protocol Buffers | FlatBuffers |
| --- | --- | --- | --- |
| 人工检查 | 直接可读 | 需要 `.proto` 与解码工具 | 需要 `.fbs` 与工具 |
| 访问方式 | 解析为对象或流式读取 | 解析为生成消息 | 可从字节缓冲区按字段访问 |
| 演进约束 | 由字段名与应用规则管理 | 字段编号、字段存在性、未知字段 | 数据结构兼容规则与生成代码 |
| Android 代价 | 解析、字符串和对象分配 | 运行库、生成代码和消息分配 | 原生/Java 依赖包、构建器与缓冲区生命周期 |
| 适用判断 | 协议变化快、可读性重要 | 跨端稳定协议、高频编解码 | 大型稳定数据、局部读取 |

不要把现有 JSON 传输对象逐字段改写成 `.proto` 或 `.fbs` 后直接复用为界面对象。网络协议、持久化结构和界面状态的升级周期不同；在仓储层（连接数据来源与业务模型的边界）显式转换，才能明确由哪一层处理默认值和兼容逻辑。

## Parcelable 与 Serializable

`Parcel` 是 Android 为 IPC（Inter-Process Communication，进程间通信）设计的高效传输容器，不是通用序列化格式。Android 17 的 `Parcel.java` 明确禁止把 Parcel 数据写入持久化存储，因为底层实现变化可能让旧数据无法读取。磁盘缓存和网络协议不应在 Parcelable 与 Serializable 之间二选一，而应使用有版本规则的持久化格式。

在组件参数或跨进程接口中，优先使用 Android SDK 和 AIDL 直接支持的基础类型，或明确的 Parcelable。`writeParcelable()` 会同时写类名和数据；`writeTypedObject()`、`writeTypedList()` 等类型明确的 API 由读取方提供 `Parcelable.Creator`，不写对象类信息，因此更紧凑。AIDL 已知参数类型时会生成相应编解码代码，业务层不应再把对象包进 `Serializable` 或无类型的嵌套容器。

Android 17 的 `writeValue()` 在其他已支持类型都不匹配时才处理 `Serializable`，并注明通用 Java 序列化开销很大。它需要处理类描述和对象图（对象及其互相引用形成的结构），还会受类结构、`serialVersionUID`（Java 序列化版本标识）与混淆影响。已有低频接口可以在测量后保留，新接口不应只因 `implements Serializable` 写起来短就选择它。

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

这个数值只用于观察对象随数据增长的趋势。它不包括 Binder 命令元数据、标记 Binder 对象和文件描述符位置的偏移表、同一进程正在处理的其他事务或返回值，因此不能当作安全阈值。`@Parcelize` 也只生成读写代码，不提供持久化版本协议。使用 `@RawValue` 时，插件会改用 `Parcel.writeValue()`；高频 IPC 中要确认该属性在运行时进入哪一种类型分支。

[Android 17 `Parcel.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/os/Parcel.java) · [Parcelize 文档](https://developer.android.com/kotlin/parcelize)

## 序列化在启动和 IPC 中的性能影响

### 启动路径：区分稳态速度和首次使用成本

`Application.onCreate()`、初始化 `ContentProvider`、首屏配置恢复和接口返回后的批量对象构造，都可能影响 `TTID`（Time to Initial Display，从启动到初始画面显示）或 `TTFD`（Time to Full Display，从启动到应用报告内容已完整显示）。官方启动文档也把反序列化列为启动变慢时应检查的工作。处理顺序是：

- 只解析首帧或可交互状态需要的数据，其余数据延后或分页。
- 若只读取少量字段，使用流式读取或调整接口，不先构建完整 JSON 树。
- 复用应用级格式配置和 Moshi 适配器；Moshi 提供的适配器可以安全地供多个线程共用，自定义适配器也必须满足线程安全要求。
- 在真实冷启动中测首次类加载、生成序列化器初始化、磁盘读取、解析和业务模型转换。
- 若解析后的内容需要跨启动复用，把它写成有版本的数据库或文件格式，不能持久化 Parcel。

Microbenchmark 的预热与完整编译适合比较预热后的函数；Macrobenchmark 和 Perfetto 才能回答“这次解析是否延迟初始画面或可交互状态”。可以添加只包围解析调用的自定义追踪区段，再结合采样调用栈、对象分配与 GC，判断时间花在 JSON 扫描、对象构造还是业务转换。

[应用启动性能](https://developer.android.com/topic/performance/vitals/launch-time)

### Android 17 Binder 缓冲区边界

“Binder 每笔事务有 1 MB”是不准确的。Android 17 的 `ProcessState.cpp` 把普通 `/dev/binder` 映射大小定义为 `1 MiB - 2 × 运行时页大小`；MiB 是二进制兆字节，1 MiB 等于 1,048,576 字节。`android17-6.18-2026-06_r6` 的 `binder_alloc.c` 允许的映射上限是 4 MiB，但实际缓冲区取用户空间请求值与该上限的较小者。Android 平台原生层请求约 1 MiB，所以 `TransactionTooLargeException` 文档将当前容量概括为 1 MB；在 16 KiB 内存页设备上，表达式还会扣除两个 16 KiB 页。

这块空间属于进程，并由该进程正在处理的 Binder 事务共享，不是某次调用的独占配额。单个参数看起来很小，也可能在并发调用、返回值和其他系统交互同时发生时失败。`TransactionTooLargeException` 不能指出失败发生在发送请求还是返回结果；重试会修改数据的调用前，必须采用幂等协议（同一请求重复执行不会产生重复副作用）或先查询提交状态。

`rememberSaveable` / `onSaveInstanceState()` 保存的状态也会经由系统进程参与 Binder 传输。Android 官方建议把这类状态控制在 50 KB 以下；这个数值只针对状态保存，不是所有 Binder 接口的通用上限。状态中应保存恢复界面所需的标识和少量输入，不保存列表、位图或完整接口响应。

[Android 17 `ProcessState.cpp`](https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/libs/binder/ProcessState.cpp) · [6.18 内核 `binder_alloc.c`](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/drivers/android/binder_alloc.c) · [Android 17 `TransactionTooLargeException.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/os/TransactionTooLargeException.java) · [Parcelable 与 Bundle 建议](https://developer.android.com/guide/components/activities/parcelables-and-bundles)

大型结果应改变接口形状：

- 列表使用稳定的续页标记分页，让下一次请求从已返回位置继续，避免重复传输已有数据。
- 大型二进制数据通过受权限保护的 Content URI，或 `ParcelFileDescriptor`（Android 对文件描述符的封装）读取。
- 进程间只传记录标识，让接收方通过明确的数据接口查询。
- 高频小调用可以在事务时长仍可控时合并成批，并验证 P95/P99 延迟（第 95/99 百分位耗时）与失败后能否安全重试。

## 建立序列化选型基线

公开基准测试只能用于发现候选项。应用自己的字段分布、字符串长度、R8 配置、依赖版本、设备 CPU 和协议压缩都会改变结果。至少建立四组可复现数据：

| 基线 | 记录内容 | 回答的问题 |
| --- | --- | --- |
| 编解码 Microbenchmark | 时间、分配次数、发布配置、设备与测试样本哈希（内容指纹） | 单个函数预热后的差异 |
| 冷启动 Macrobenchmark | `TTID`、`TTFD`、解析追踪区段、GC 与类加载 | 首次解析是否影响用户路径 |
| 网络或磁盘端到端测试 | 压缩前后字节数、读写时间、业务模型转换 | 格式变化是否降低从读取到业务对象的总耗时 |
| IPC 压力测试 | 本地 Parcel 估算、并发数、往返延迟、失败与重试 | 接口是否需要分页或外部数据通道 |

发布前还要运行协议兼容性回归测试：

- 当前解码器读取所有仍受支持的历史测试样本。
- 新旧编码器与解码器交叉验证，检查缺失字段、未知字段和默认值。
- 经过 R8 处理的发布 APK 或 AAB 执行相同测试，覆盖反射、生成代码和自定义适配器。
- 目标设备覆盖 Android 10 / API 29 与 Android 17 / API 37；包含 16 KiB 页设备时，额外观察 Binder 缓冲区与原生序列化库。
- 格式错误、体积过大或嵌套层级过深的输入能够受控失败，不把原始用户数据写入性能日志。

## 小结

JSON 库先比较协议语义和发布包稳定性，再比较速度；Gson 存量代码可以渐进迁移，新 Kotlin 模型宜优先评估生成代码。Protocol Buffers 依赖严格的字段编号与兼容测试，FlatBuffers 的直接访问优势只在目标数据形状中成立。Parcelable 服务于 Android 瞬时传输，不能用于持久化；Android 17 的 Binder 容量还是进程共享资源。优化顺序应从减少数据、延迟非必要解析、分页和调整接口开始，换库必须由同一业务路径上的测量结果支持。
