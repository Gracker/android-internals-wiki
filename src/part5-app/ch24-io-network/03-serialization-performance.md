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
last_task6_audit: "2026-05-24"
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

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 JSON（Gson / Moshi / kotlinx.serialization）性能对比
- 🔹 Protocol Buffers 与 FlatBuffers
- 🔹 Parcelable vs Serializable
- 🔹 序列化在启动和 IPC 中的性能影响

### 扩展（可选深入）

- 🔸 （待扩展）

### OpenClaw 加工指引

> **锚点**是最低覆盖要求，加工时必须逐条落实并标注验证结果。
> **扩展**视素材丰富程度选择性深入。
> 如果从 Obsidian 素材或 AOSP 源码中发现大纲未列出但与本节强相关的知识点，
> 可**就地插入**最相关的锚点之后，并用 `[自动发现]` 标注，方便后续 review。
> 锚点内容需 L1/L2 验证，扩展内容至少 L2 验证，自动发现内容至少标注来源。
<!-- outline-end -->

## 为什么要了解序列化性能对比与选型

序列化选型会同时影响 CPU、内存分配、包体积、混淆稳定性和协议演进。它不像数据库慢查询那样容易在 trace 里留下一个醒目的耗时片段，更多时候表现为冷启动阶段的短时 CPU 峰值、一次网络响应后的对象洪峰、Binder 调用前后多出来的复制成本，或者线上只在混淆包里复现的字段丢失。

应用侧选型要回答几个问题：JSON 库怎么选，什么时候换成 Protocol Buffers 或 FlatBuffers，进程间传对象该用 Parcelable 还是 Serializable，序列化工作怎么从启动路径和 Binder 路径里移出去。Binder 事务模型和线程池竞争详见 1.4 节；启动阶段的 TTID/TTFD 观测详见 21.1 节；连接池、弱网重试和协议层设计详见 24.4 节。


## JSON（Gson / Moshi / kotlinx.serialization）性能对比

JSON 的优势是可读、调试方便、后端兼容成本低。代价是文本格式本身需要 token 扫描和字符串处理；对象绑定还会产生字段匹配、构造对象、集合扩容和临时字符串。小请求里这部分成本通常被网络延迟盖住，大列表、配置下发、启动预拉取和离线缓存恢复时，序列化就会进入用户可感知路径。

Gson 的主要问题不只在速度。Gson README 已明确说明，它不推荐作为 Android JSON 方案：运行时开放反射与 shrink/optimization/obfuscation 不好配合，Android 场景更适合 Kotlin Serialization 或 Moshi Codegen 这类代码生成方案。已有 Gson 存量项目可以保留在非关键路径，但新模型不要继续把 Gson 放进启动、列表首屏或大批量缓存恢复路径。[已验证: 官方文档, github.com/google/gson/blob/main/README.md]

Moshi 适合 Kotlin/Java 混合项目。Moshi README 说明，Kotlin 场景可以用 reflection、codegen 或二者混用；Codegen 通过 KSP 为每个 Kotlin class 生成小而快的 adapter。Moshi 的价值不在于所有场景都最快；主要收益是把字段访问和构造逻辑提前到编译期，减少运行时反射、降低混淆风险。对 Android 业务代码，默认把 `@JsonClass(generateAdapter = true)` 作为数据模型约束更稳。[已验证: 官方文档, github.com/square/moshi/blob/master/README.md]

kotlinx.serialization 的定位是 Kotlin 多平台、多格式、无反射序列化。它通过 `@Serializable` 和编译器插件生成序列化器，JSON 只是其中一种格式。纯 Kotlin 模块、共享模型、需要同时支持 JSON/CBOR/ProtoBuf 的场景更适合这条路线。代价是模型要遵守插件约束，第三方 Java bean 或动态字段很多的接口迁移成本较高。[已验证: 官方文档, kotlinlang.org/docs/serialization.html]

应用内选型可以按这张表落到工程约束，而不是只看单次 benchmark 排名：

| 场景 | 优先选择 | 判断依据 |
|------|----------|----------|
| 新 Kotlin 模块、模型受控 | kotlinx.serialization 或 Moshi Codegen | 编译期生成序列化器，减少运行时反射；字段默认值、空值策略要在模型层写清楚 |
| Java/Kotlin 混合、需要平滑替换 Gson | Moshi Codegen | API 迁移成本较低，代码生成 adapter 更适合 Android 混淆包 |
| 存量 Gson、非关键路径 | 保留 Gson，补混淆与回归测试 | 避免一次性重写造成协议兼容风险；把热路径模型逐步迁出 |
| 大响应、只读取少数字段 | streaming reader 或拆接口 | 避免把完整 JSON 树和全部 DTO 一次性建出来 |
| 端到端协议可控 | Protocol Buffers | 二进制 schema 更适合高频网络与磁盘缓存 |

这段代码表达 JSON 选型后的性能基线写法。先固定同一份 payload、同一组模型、同一台设备和同一套混淆配置，再看 parse/encode 时间与分配量。

```kotlin
@RunWith(AndroidJUnit4::class)
class FeedJsonBenchmark {
    @get:Rule
    val benchmarkRule = BenchmarkRule()

    private val payload = InstrumentationRegistry.getInstrumentation()
        .context.assets.open("feed_payload.json")
        .bufferedReader()
        .use { it.readText() }

    private val json = Json { ignoreUnknownKeys = true }
    private val moshi = Moshi.Builder().build()
    private val moshiAdapter = moshi.adapter(FeedResponse::class.java)

    @Test
    fun decodeWithKotlinxSerialization() = benchmarkRule.measureRepeated {
        json.decodeFromString<FeedResponse>(payload)
    }

    @Test
    fun decodeWithMoshiCodegen() = benchmarkRule.measureRepeated {
        moshiAdapter.fromJson(payload)
    }
}
```

Jetpack Microbenchmark 文档提供了 Android 端小段代码性能测量工具。序列化 benchmark 要跟随 release 构建、R8、目标 API、样本 payload 和机型一起记录；只拿 debug 包结果做选型，会把反射、内联、类加载和 JIT 状态都混在一起。[已验证: 官方文档, developer.android.com/topic/performance/benchmarking/microbenchmark-overview]

JSON 适合可读性优先、协议快速迭代的场景。当协议稳定、需要更小的传输体积和更快的解析速度时，二进制格式就该纳入考虑。

## Protocol Buffers 与 FlatBuffers

Protocol Buffers 适合端到端协议可控的结构化数据。官方概览把它定义为 language-neutral、platform-neutral、extensible 的结构化数据序列化机制，并说明它类似 JSON，但更小、更快，并会生成对应语言的 binding。对 Android 来说，它常见于网络协议、磁盘缓存、跨端共享模型和 gRPC 通信。[已验证: 官方文档, protobuf.dev/overview]

Protobuf 的工程收益来自 schema。字段编号稳定后，客户端和服务端可以独立演进；新增字段能被旧端跳过，删除字段可以保留编号避免复用事故。它也会把“字段名字符串匹配”换成“字段编号解析”，payload 通常比 JSON 小。代价是可读性下降，抓包调试要配 `.proto`，动态字段和临时实验字段不如 JSON 灵活。

FlatBuffers 的目标不同。FlatBuffers README 说明，它面向内存效率设计，允许直接访问序列化数据，不需要先解析或 unpack。这个特性适合读多写少、只访问局部字段、数据块较大且结构稳定的场景，比如离线索引、模型元数据、地图/游戏资源、端侧配置快照。它不适合频繁修改的业务对象；写入侧 builder、schema 维护和调试成本更高。[已验证: 官方文档, github.com/google/flatbuffers/blob/master/README.md]

二者在 Android 里的判断口径可以压成三条：

- 协议长期稳定、跨端共享、服务端能配合生成代码：优先看 Protocol Buffers。
- 数据需要 mmap 或从二进制块里按需读字段：评估 FlatBuffers。
- 后端字段仍在频繁试验、排查依赖可读文本、接口体积不大：保留 JSON，等协议稳定后再迁移。

迁移时不要把 JSON DTO 原样翻成 `.proto`。更安全的做法是为网络层定义独立 schema，再在仓储层转换成 UI/domain model。这样能把协议演进、默认值、未知字段处理和 UI 状态分开，也避免一个字段名调整牵动页面模型。

网络和存储的序列化选型讨论到这里。Android 还有一类特殊的序列化场景：进程间通信。

## Parcelable vs Serializable

Android IPC 和组件参数传递优先使用 Parcelable。AOSP `Parcel.java` 文档写得很直接：Parcel 不是通用序列化机制，它和 Parcelable API 是为高性能 IPC transport 设计的，不适合持久化存储；Parcel 底层实现变化可能让旧数据不可读。[已验证: AOSP android-17.0.0_r1, frameworks/base/core/java/android/os/Parcel.java]

同一份 AOSP 文档还说明，`writeTypedObject`、`writeTypedArray`、`writeTypedList`、`readTypedObject`、`createTypedArrayList` 这组方法比普通 `writeParcelable` / `readParcelable` 更高效，因为它们不把原对象的 class 信息写入 Parcel，读取方通过 `Parcelable.Creator` 明确知道类型。AIDL、Bundle、Intent extra 和跨进程回调里，能用 typed Parcelable 就不要退回泛型容器。[已验证: AOSP android-17.0.0_r1, frameworks/base/core/java/android/os/Parcel.java]

Serializable 只适合低频、兼容旧接口、数据量很小的场景。AOSP `writeValue()` 注释把 Serializable 放在支持类型列表末尾，并明确提示前面的类型都有相对高效的 Parcel 写入实现；依赖 generic serialization 的方式低效，应尽量避免。原因不需要神化：Java 序列化会走通用对象图、类描述、字段访问和流格式，Android IPC 没必要付这笔成本。[已验证: AOSP android-17.0.0_r1, frameworks/base/core/java/android/os/Parcel.java]

这段 Parcelable 代码只展示写入顺序和 typed API 的配合。读写字段顺序必须稳定，新增字段要考虑版本兼容；跨进程大对象不要直接塞进 Bundle。

```kotlin
@Parcelize
data class UserCard(
    val id: Long,
    val name: String,
    val avatarUrl: String?
) : Parcelable

class UserServiceProxy(private val remote: IUserService) {
    fun send(card: UserCard) {
        remote.updateUserCard(card)
    }
}
```

`@Parcelize` 可以减少手写样板代码，但它不会自动处理大对象、跨版本兼容和 Binder 事务大小——这些仍需开发者自己关注。性能问题仍要回到字段数量、字符串长度、集合规模、是否包含 Bitmap/byte array、调用频率和线程位置。

## 序列化在启动和 IPC 中的性能影响

启动阶段的序列化问题通常来自四类路径：`Application` 同步读取配置、ContentProvider 初始化时解析缓存、首屏接口返回后一次性构建大 DTO、AB 实验/灰度配置在主线程展开。这些路径都会把 CPU 解析、对象分配和类加载放进 TTID/TTFD 前后。启动分析方法详见 21.1 节；24.3 的处理动作是把大 payload 延后、拆小、缓存已解析结果，或者换成生成代码/二进制 schema。

不要在启动路径里创建大量一次性 parser、adapter 或 `Json` 实例。kotlinx.serialization 文档建议复用自定义 format 实例，因为 format 实现可能缓存和 class 相关的额外信息；Moshi 的 adapter 也应按类型复用。复用不会自动解决所有性能问题，但能减少冷启动里重复建立元数据和 adapter 查找。[已验证: 官方文档, android.googlesource.com/platform/external/kotlinx.serialization/+/refs/heads/upstream-1.2.0-release/docs/json.md][已验证: 官方文档, square.github.io/moshi]

IPC 路径要控制 Parcel 大小和调用频率。`TransactionTooLargeException.java` 说明，Binder 事务 buffer 当前固定大小为 1 MB，并由进程内进行中的事务共享；异常只能作为大事务失败的启发式信号，无法判断请求没发出去还是响应没回去。规避方式是让事务保持小，避免传巨大字符串数组或大 Bitmap，把大结果拆页返回，或者先返回必要字段再让客户端按需请求。[已验证: AOSP android-17.0.0_r1, frameworks/base/core/java/android/os/TransactionTooLargeException.java]

序列化问题在 Perfetto 中可以从三个方向定位：

- 主线程或启动关键线程出现连续 CPU slice，但没有明显 I/O 等待：结合方法 trace 或 simpleperf 查 JSON/Proto/Parcel 相关栈。
- `binder transaction` 前后耗时变长：查参数对象大小、列表长度、是否重复传完整 DTO。
- GC 在接口返回或缓存恢复后变密：查一次解析生成的对象数量，优先处理大集合和嵌套对象。

一旦确认是序列化成本，不要一上来就换库。更稳的改法是先缩小 payload、减少字段、延迟解析、拆页、复用 adapter、把大对象放到文件/数据库后传 key；库替换放在后面，用这些优化后的场景再去比较 JSON/Proto/FlatBuffers 的实际差异。

## 建立序列化选型基线

序列化库的公开 benchmark 只能作为方向参考。应用自己的模型、R8 规则、payload 分布、字段默认值、字符串长度和设备 CPU 都会改写结果。选型前至少补三组基线：

| 基线 | 观测指标 | 用途 |
|------|----------|------|
| decode/encode microbenchmark | 单次耗时、分配量、P50/P90 | 判断库和模型生成策略 |
| 启动路径 trace | TTID/TTFD 附近 CPU slice、GC、类加载 | 判断是否要延后解析或预生成缓存 |
| IPC 压测 | Parcel 大小、调用频率、TransactionTooLargeException | 判断是否要分页或传 key |

如果三组基线指向不同结论，以用户路径优先。启动慢就先处理启动路径里的解析；Binder 失败就先拆事务；后台同步耗电再看批量 encode/decode 的 CPU 和分配量。库替换是工程动作，选型依据必须来自目标路径。

## 参考资料

- [已验证: AOSP android-17.0.0_r1, frameworks/base/core/java/android/os/Parcel.java]
- [已验证: AOSP android-17.0.0_r1, frameworks/base/core/java/android/os/TransactionTooLargeException.java]
- [引用: developer.android.com/reference/android/os/Parcelable]
- [引用: developer.android.com/topic/performance/benchmarking/microbenchmark-overview]
- [引用: github.com/google/gson/blob/main/README.md]
- [引用: github.com/square/moshi/blob/master/README.md]
- [引用: kotlinlang.org/docs/serialization.html]
- [引用: protobuf.dev/overview]
- [引用: github.com/google/flatbuffers/blob/master/README.md]
