---
title: "数据压缩与缓存策略"
chapter: "24.6"
section: "24.6"
status: finalized
applicable_versions: "Android 10 (API 29) - Android 17 (API 37)"
last_verified: "2026-08-15"
last_verified_against: "Android Developers app-specific storage, StorageManager and offline-first docs current through 2026-08-15; OkHttp 5.4.0 source, release and Maven Central metadata; RFC 9110/9111; AOSP android-17.0.0_r1"
confidence: high
sources:
  - type: official
    path: "https://developer.android.com/training/data-storage/app-specific"
  - type: official
    path: "https://developer.android.com/develop/connectivity/network-ops/network-access-optimization"
  - type: official
    path: "https://developer.android.com/topic/architecture/data-layer/offline-first"
  - type: official
    path: "https://developer.android.com/reference/android/os/storage/StorageManager"
  - type: legacy-reference-preserved
    path: "https://square.github.io/okhttp/features/caching/"
  - type: legacy-reference-preserved
    path: "https://square.github.io/okhttp/5.x/okhttp/okhttp3/-compression-interceptor/"
  - type: legacy-reference-preserved
    path: "https://square.github.io/okhttp/5.x/okhttp-brotli/okhttp3.brotli/-brotli-interceptor/"
  - type: official
    path: "https://lysine.dev/okhttp/features/caching/"
  - type: official
    path: "https://lysine.dev/okhttp/5.x/okhttp/okhttp3/-compression-interceptor/"
  - type: official
    path: "https://lysine.dev/okhttp/5.x/okhttp-brotli/okhttp3.brotli/-brotli-interceptor/"
  - type: official
    path: "https://repo.maven.apache.org/maven2/com/squareup/okhttp3/okhttp/maven-metadata.xml"
  - type: official
    path: "https://github.com/lysine-dev/okhttp/releases/tag/parent-5.4.0"
  - type: official
    path: "https://github.com/lysine-dev/okhttp/blob/parent-5.4.0/okhttp/src/commonJvmAndroid/kotlin/okhttp3/internal/http/BridgeInterceptor.kt"
  - type: official
    path: "https://github.com/lysine-dev/okhttp/blob/parent-5.4.0/okhttp/src/commonJvmAndroid/kotlin/okhttp3/CompressionInterceptor.kt"
  - type: official
    path: "https://github.com/lysine-dev/okhttp/blob/parent-5.4.0/okhttp-brotli/src/main/kotlin/okhttp3/brotli/BrotliInterceptor.kt"
  - type: official
    path: "https://github.com/lysine-dev/okhttp/blob/parent-5.4.0/okhttp/src/commonJvmAndroid/kotlin/okhttp3/Cache.kt"
  - type: official
    path: "https://github.com/lysine-dev/okhttp/blob/parent-5.4.0/okhttp/src/commonJvmAndroid/kotlin/okhttp3/internal/cache/CacheStrategy.kt"
  - type: legacy-reference-preserved
    path: "https://github.com/square/okhttp/blob/parent-5.3.0/okhttp/src/commonJvmAndroid/kotlin/okhttp3/internal/http/BridgeInterceptor.kt"
  - type: legacy-reference-preserved
    path: "https://github.com/square/okhttp/blob/parent-5.3.0/okhttp/src/commonJvmAndroid/kotlin/okhttp3/CompressionInterceptor.kt"
  - type: legacy-reference-preserved
    path: "https://github.com/square/okhttp/blob/parent-5.3.0/okhttp-brotli/src/main/kotlin/okhttp3/brotli/BrotliInterceptor.kt"
  - type: legacy-reference-preserved
    path: "https://github.com/square/okhttp/blob/parent-5.3.0/okhttp/src/commonJvmAndroid/kotlin/okhttp3/Cache.kt"
  - type: legacy-reference-preserved
    path: "https://github.com/square/okhttp/blob/parent-5.3.0/okhttp/src/commonJvmAndroid/kotlin/okhttp3/internal/cache/CacheStrategy.kt"
  - type: official
    path: "https://www.rfc-editor.org/rfc/rfc9110.html"
  - type: official
    path: "https://www.rfc-editor.org/rfc/rfc9111.html"
  - type: aosp
    path: "https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/content/Context.java"
  - type: aosp
    path: "https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/os/storage/StorageManager.java"
  - type: clippings
    path: "Clippings/Android 性能优化 - 缓存优化：冷热端分离+重排序，提升缓存命中率.md"
  - type: clippings
    path: "Clippings/Android 性能优化 - 物理内存优化实战：Java Heap 内存优化.md"
  - type: clippings
    path: "Clippings/Android 性能优化 - CPU 优化（下）：减少 CPU 闲置时刻和等待，提升利用率.md"
tags: [compression, caching, gzip, brotli, offline-sync]
related_chapters: ["24.4", "24.7", "12.1"]
pipeline_stage: finalized
task6_state: reviewed
task9_state: reviewed
task2b_state: fixed
last_review_finalize_at: "2026-08-15T10:34:29+08:00"
last_review_finalize_run_id: "20260815-103429-gracker-writing-review"
last_draft_polish_at: "2026-08-15T10:34:29+08:00"
last_draft_polish_run_id: "20260815-103429-gracker-writing"
---

# 数据压缩与缓存策略

## 压缩和缓存分别节省什么

网络耗时受 DNS 查询、建连和拥塞影响，也取决于应用传输了多少数据、是否重复下载，以及是否重复解析相同内容。压缩、HTTP 缓存、进程内缓存和离线数据源各有职责，任一机制都无法覆盖其余机制。

压缩以中央处理器（CPU）的运算时间和少量协议开销换取更少的传输字节；缓存以内存、存储空间和一致性成本换取更少的网络访问与解析工作；离线优先架构还要维护可恢复的写队列。评审方案时应同时回答以下问题：

- 数据是否会被重复读取，允许陈旧多久？
- 界面以哪一份持久数据为准，数据冲突时由谁裁决？
- 账号切换、退出登录和租户切换后，旧数据怎样隔离或删除？
- 缓存文件被系统清理、文件损坏或应用升级后，读取路径能否自行恢复？
- 压缩节省的传输时间，是否大于编码、解码和额外耗电？

平台锚点是 Android 17（API 37）/ `android-17.0.0_r1`，HTTP 客户端实现以 OkHttp 5.4.0 为例。OkHttp 的 Maven 坐标仍是 `com.squareup.okhttp3`，5.4.0 源码上游已迁至 `lysine-dev/okhttp`。服务端、内容分发网络（CDN）或客户端库版本不同时，应按部署版本重新核对行为。

## HTTP 请求与响应压缩

### 先区分内容编码与数据格式

客户端通过 `Accept-Encoding` 声明能够接收的内容编码，服务端通过 `Content-Encoding` 标出响应体采用的编码。gzip 与 Brotli（标头值为 `br`）都属于 HTTP 内容编码；JSON、Protocol Buffers、JPEG 和 MP4 属于数据或媒体格式。内容编码作用于完整表示，数据格式定义表示内部怎样组织，两者处于不同层次。

Protocol Buffers 是按消息结构定义字段的二进制序列化格式，本身不会自动压缩。它通常比等价 JSON 紧凑，但字段值仍可能包含可压缩的重复内容。是否再做 gzip 或 Brotli，要根据样本数据测量，不能因为使用了 `.proto` 就判定“已经压缩”。

### OkHttp 5.4.0 的透明解压边界

OkHttp 默认的 `BridgeInterceptor` 只在请求没有显式设置 `Accept-Encoding`、并且没有 `Range` 时添加 `Accept-Encoding: gzip`。满足以下条件时，它会流式解压响应：

- 该请求由 OkHttp 自动添加了 gzip 协商头；
- 响应包含 `Content-Encoding: gzip`；
- 响应语义允许携带响应体。

解压后返回给应用的响应会移除 `Content-Encoding` 和 `Content-Length`，解码后长度也被标为未知。业务代码读取的是解压后的内容，不能再用返回响应的 `Content-Length` 推算传输字节数。

OkHttp 5.4.0 还提供通用 `CompressionInterceptor`。它把注册算法组成 `Accept-Encoding`，并按完整的 `Content-Encoding` 值寻找一个已注册算法。它不会逐层解码 `gzip, br` 这类包含多层编码的值。`okhttp-brotli` 5.4.0 中的 `BrotliInterceptor` 注册 `Brotli` 与 `Gzip`，请求会声明 `Accept-Encoding: br, gzip`；这条拦截器路径接管响应解压，并替代 `BridgeInterceptor` 的默认透明 gzip 路径。

如果调用方手动设置了 `Accept-Encoding`，`CompressionInterceptor` 和默认 gzip 路径都不会替调用方透明解码。要关闭压缩，可显式发送 `Accept-Encoding: identity`。不要只添加 `br` 或 `gzip` 请求头，却仍假设响应体会自动解压。

服务端按 `Accept-Encoding` 返回不同表示时，应发送 `Vary: Accept-Encoding`。`Vary` 指定“哪些请求头共同决定缓存变体”，共享缓存据此分别保存 gzip、Brotli 和未编码响应，避免把某种编码发给不支持它的客户端。

### 哪些数据值得压缩

用线上样本测量压缩收益，不设置适用于所有接口的固定字节阈值：

| 数据形态 | 建议 | 原因 |
| --- | --- | --- |
| JSON、HTML、XML，以及 GraphQL 接口返回的文本 | 评估 gzip 与 Brotli | 键名和结构重复较多，通常存在压缩空间 |
| Protocol Buffers | 用样本决定 | 二进制序列化不等于压缩，收益受字段内容影响 |
| JPEG、WebP、AVIF、音视频和 ZIP | 通常不再套通用压缩 | 这类格式已经使用专用编码，再压缩常见收益有限 |
| 加密或高熵内容 | 通常不再压缩 | “高熵”表示字节分布接近随机，重复模式很少，通用压缩难以缩小 |
| 很小的响应 | 以端到端测量决定 | 编码头、压缩器初始化和处理器时间可能高于传输收益 |

图片和视频应优先调整尺寸、格式、码率和分片策略，相关网络边界见 24.5，端到端耗时分析见 12.1。

请求体压缩需要服务端明确接受对应的请求 `Content-Encoding`。批量日志或大型结构化上传可以评估请求压缩；表单和小型写请求不应默认启用。压缩包装可能改变请求体是否可重复发送，重试前要继续遵守 24.4 的幂等与一次性请求体边界。

### 测量与防护

至少分别记录：

- 编码前的应用数据大小；
- 网络上传输的字节数；
- 解码后的响应体大小；
- 编码、解码和解析耗时；
- 请求端到端耗时、失败类型与重试次数。

透明解压会让应用层看到的长度与线上传输长度不同。传输字节应从服务端、网络层观测或已验证口径的事件指标采集，解码后长度则在消费响应体时计数，两者不能混用。

客户端还要限制解码后的数据量、集合元素数量和解析深度。攻击者可以构造传输体积很小、解压后急剧膨胀的数据，这类输入常被称为“压缩炸弹”。仅依赖压缩前 `Content-Length` 无法防止异常放大。限制应在构建大型对象前生效，超限时终止读取并记录服务端、媒体类型和编码方式。

## 多级缓存设计：内存 / 磁盘 / 网络

### 每层只负责自己的语义

内存缓存服务于当前进程内的重复访问；磁盘文件缓存允许应用重启后复用可再生成的数据；HTTP 缓存按协议复用响应；Room、DataStore 或普通持久文件保存应用必须恢复的状态。Room 是基于 SQLite 的持久化库，DataStore 适合保存少量键值或类型化对象。界面应从应用指定的权威数据源读取，HTTP 缓存和 `cacheDir` 都可能随时缺失，不能作为权威数据源。

| 层级 | 常见载体 | 适合缓存的数据 | 淘汰依据 | 主要风险 |
| --- | --- | --- | --- | --- |
| 内存 | `LruCache`、图片库内存层、进程内键值表 | Bitmap 像素对象、解析结果、短生命周期配置 | 容量、最近访问、业务热度 | 占用堆，可能增加垃圾回收（GC）频率，甚至引发内存不足（OOM） |
| 可删除磁盘文件 | `cacheDir`、`externalCacheDir`、图片库磁盘层 | 图片、接口快照、预取文件 | 配额、最近修改时间、业务分组 | 系统或用户可以删除，读取必须允许缺失 |
| HTTP | OkHttp `Cache`、CDN、代理缓存 | 符合 HTTP 缓存规则的响应 | 新鲜度、验证器和缓存指令 | 错误响应头、账号隔离和陈旧数据 |
| 应用数据源 | Room、DataStore、持久文件 | 用户可见数据、离线数据、同步状态 | 业务版本、账号、租户、服务端版本 | 迁移、冲突、隐私和恢复成本 |

`LruCache` 的 LRU 是“最近最少使用”策略：空间不足时优先淘汰最久未访问的条目。容量应按对象的实际成本计算。以 `Bitmap` 为例，条目大小应来自分配字节数等可验证数据，不能只数条目个数。系统给出的内存等级只能作为容量输入，界面对象、数据库游标、原生内存和图形资源仍会共同占用进程预算。

AOSP `Context.getCacheDir()` 在 `android-17.0.0_r1` 中说明：

- 系统需要回收存储空间时，会按 `lastModified()` 从较旧文件开始处理；
- 应用应尽量把缓存使用量控制在 `StorageManager.getCacheQuotaBytes()` 返回的动态配额以内；该值表示系统当前建议的缓存额度，会随设备状态变化；
- 设备采用可迁移存储后，绝对路径可能变化，只应持久化相对路径；
- 应用无需额外权限访问自己的内部缓存目录。

API 26 起，`StorageManager.setCacheBehaviorGroup()` 可以让一个目录在系统自动清理时整体保留或整体删除，并用组内最新的修改时间代表整组。`setCacheBehaviorTombstone()` 会把被系统自动清理的文件截断为零字节，而非移除目录项；这种零长度“墓碑”可帮助应用区分“曾经存在但已被清理”和“从未创建”。两种行为都只能设置在目录上并递归生效，也都只影响系统的自动清理。用户主动清除缓存时，墓碑设置会被忽略；分组设置也不提供持久性保证。

`externalCacheDir` 可能不可用，使用前要检查返回值和卷状态。需要在应用升级、进程重启或设备重启后仍可靠恢复的数据，应放在持久数据源中，不应依靠任一缓存目录。

### 配置 OkHttp 磁盘缓存

这个函数显式传入容量，并为 OkHttp 分配独占子目录：

```kotlin
fun buildHttpClient(
    context: Context,
    maxCacheBytes: Long,
): OkHttpClient {
    require(maxCacheBytes > 0) { "maxCacheBytes must be positive" }

    val httpCache = Cache(
        directory = File(context.cacheDir, "okhttp-http-cache"),
        maxSize = maxCacheBytes,
    )

    return OkHttpClient.Builder()
        .cache(httpCache)
        .build()
}
```

容量由设备存储、缓存配额、内容分布和命中收益共同决定，因此不在示例中写固定值。`Cache` 必须独占目录，同一目录不能交给多个 `Cache` 实例；一个实例可以由多个 OkHttpClient 共用。应用通常应共享长生命周期的 OkHttpClient，替换或结束使用缓存实例时再正确关闭它。

OkHttp 的 `Cache.delete()` 会删除所配置目录中的全部内容，因此该目录不能混放应用的其他文件。缓存读写失败应退回网络或应用数据源，并记录错误；损坏的缓存不应阻塞正常读取。

## HTTP 缓存：由协议决定能否复用

### 新鲜度、存储和验证是三件事

RFC 9111 把“能否存储”“当前是否新鲜”“过期后能否验证”分开定义。新鲜状态表示缓存仍可直接复用，陈旧状态表示新鲜期已经结束：

- `max-age` 表示响应从何时起变为陈旧。`Date`、`Age` 和本地驻留时间都会参与当前年龄计算，不能只比较设备时钟与下载时间。
- `Expires` 是绝对过期时间；存在适用的 `max-age` 时，优先采用后者。
- `no-cache` 允许存储，但每次复用前必须向源站验证；源站指生成该资源的原始服务器。因此它表达的是“先验证”，并非“不要存储”。
- `no-store` 要求缓存不要存储请求或响应，也不要用它满足后续请求。它不能替代传输加密、访问控制或端侧数据保护。
- `private` 限制 CDN、代理等共享缓存存储响应，不会禁止私有缓存存储。OkHttp 的磁盘缓存属于私有缓存。
- `s-maxage` 只为共享缓存指定新鲜期。OkHttp 5.4.0 的私有缓存会解析该值，但不会按它决定复用时间。

陈旧响应不能无条件返回。协议指令可以授权缓存在限定条件下复用陈旧响应；产品若采用“先展示旧数据、后台刷新”，还要在应用数据层表达刷新中、陈旧时长和刷新失败，HTTP 缓存无法单独提供这些界面状态。

### 验证器没有固定高低之分

`ETag`（实体标签）是服务端为某个资源表示分配的版本标识，客户端复查时通过 `If-None-Match` 发送它。`Last-Modified` 记录修改时间，复查时配合 `If-Modified-Since`。服务端返回 `304 Not Modified`，表示内容没有变化；客户端无需再次下载响应体，只需保留缓存内容并更新可合并的响应元数据。

`ETag` 可以表达与时间无关的表示版本，也有强验证器和弱验证器之分。`Last-Modified` 适用于服务端能可靠维护修改时间的资源，但 HTTP 日期粒度、时钟和生成方式会影响判断。两者的适用条件不同，应根据服务端数据模型选择，不能按等级排序。

服务端返回随请求头变化的表示时，用 `Vary` 声明参与选择的请求头。OkHttp 会把这些请求头的名称和值写入缓存元数据，并在复用前逐项比较；`Vary: *` 表示任何请求都不能直接匹配，因此响应不会进入 OkHttp 缓存。若自建缓存键只包含 URL，遗漏语言、内容编码或账号范围，就可能复用错误的响应变体。

### OkHttp 5.4.0 的实现边界

按 OkHttp 5.4.0 `Cache` 与 `CacheStrategy` 源码：

- 磁盘缓存只写入 `GET` 响应；当前实现不支持缓存 `206 Partial Content` 这类部分响应；
- 请求或响应含 `no-store` 时不会写入；
- 请求含 `no-cache` 时会访问网络或执行条件验证；
- `only-if-cached` 禁止访问网络，找不到可用条目时由 OkHttp 生成 `504 Unsatisfiable Request`；该状态不能解释为源站返回的网络错误；
- 条件命中会访问网络完成验证，同时复用本地响应体，因此同时计入 `networkCount` 和 `hitCount`；
- `requestCount`、`networkCount`、`hitCount` 分别记录总请求数、使用网络的请求数和缓存命中数。

这些计数只能解释 OkHttp 这一层。图片库内存命中、Room 查询和应用文件缓存要分别统计，不能合并成一个缺少层级信息的“总命中率”。评估时还应观察写入失败、淘汰、条件请求、响应年龄、账号范围和因缓存节省的网络字节。

### 账号与敏感数据隔离

OkHttp 的缓存以 URL 为主键，并依据 `Vary` 记录的请求头匹配响应变体。私有缓存只表示它不与其他客户端共享，并不自动区分同一应用中的多个登录账号。带凭据接口需要明确选择：

- 敏感或一次性数据由服务端返回 `no-store`；
- 允许端侧缓存的账号数据使用账号级独立缓存目录和客户端，退出登录时关闭并删除该账号目录；
- 应用自建缓存键包含账号、租户、环境、查询参数、分页位置和数据版本，但不写入原始令牌；
- 日志、埋点和错误上报不记录 `Authorization`、Cookie 或完整敏感缓存键。

仅返回 `private` 不能解决同一应用内的多账号隔离。响应使用 `Vary: Authorization` 后，OkHttp 会按授权标头区分响应，也会把对应请求头值写入缓存元数据；采用该方案前必须评估设备端保存凭据的风险。

## 业务缓存失效与一致性

### 先指定权威数据源

TTL（存活时间）规定缓存条目可直接使用多久。固定 TTL 只能表达时间，无法表达用户刚完成写操作、服务端版本改变或依赖资源已经更新。应用应为每类数据指定权威数据源，并给缓存条目记录可验证的来源与版本。

一个应用自建缓存条目通常需要以下维度：

- 资源标识、账号、租户和环境；
- 经过规范化的查询参数与分页位置；
- 数据结构版本、服务端版本或验证器；
- 写入时间、允许陈旧时间和来源；
- 完整性信息，例如长度、校验值或原子提交标记。

写操作成功后，应按资源关系让受影响条目失效，不能只删除当前接口 URL。例如，头像更新会影响用户详情、会话列表和个人页摘要。依赖关系可以用标签记录，也可以建立从资源标识指向缓存键的“反向索引”，由资源查出所有相关条目。无法可靠枚举依赖时，可提升账号或资源版本，让旧版本缓存整体失效，这比在多处手工删除更容易验证。

### 处理并发、损坏和陈旧数据

同一缓存键过期时，多个并发读取可能同时发起刷新。`single-flight` 指把这些同键请求合并为一次实际刷新，其余调用等待并共享结果。互斥范围应限制在同一键，某次超时或取消不能让其他键停止刷新。多进程应用还要使用进程间可见的原子写入或数据库事务，进程内锁无法保护另一个进程。

磁盘内容应先写入同一文件系统中的临时文件，校验成功后再用原子重命名替换目标；在文件系统提供该保证时，读取者只会看到旧文件或完整的新文件。读取时把文件不存在、零长度、结构版本不支持、校验失败和解析失败都视为可恢复的缓存未命中；删除损坏条目，再从权威数据源获取。持久业务数据损坏则应进入迁移或恢复流程。

展示陈旧数据时，界面状态至少能区分“已有旧数据、正在刷新”“已有旧数据、刷新失败”和“没有数据”。字段 `lastSyncedAt` 应记录最近一次成功同步的时间，失败的尝试不能改写它。预取任务要设置业务范围和淘汰优先级，避免一次性内容挤占高复用资源。

## 离线数据同步

### 缓存与离线数据源不是同一概念

Android Developers 的离线优先架构让 `Repository`（数据访问仓库）协调本地与网络数据源，并建议界面和业务逻辑只从本地权威数据源读取。HTTP 缓存可以减少下载，却无法表示一次本地写入是否等待上传，也不能保存冲突版本、请求去重标识和错误状态。这些状态应由 `Outbox` 记录：它是持久化在本地数据库中的待发送操作表，可与业务数据变更写入同一个事务。

图中的 `UI` 是用户界面，`Repository` 负责组织数据读写，`WorkManager` 负责可跨进程终止继续调度的持久任务，`Network API` 是服务端接口。读路径与持久写队列的关系如下：

```text
UI
 │ 只观察本地数据
 ▼
Repository
 ├── 读：Room / DataStore / 持久文件 ← 网络刷新
 └── 写：本地事务 = 业务数据变更 + Outbox 记录
                                  │
                                  ▼
                       WorkManager 处理队列
                                  │
                                  ▼
                              Network API
```

界面始终观察本地权威数据源；网络刷新写回本地后，界面由数据流更新。需要离线提交的用户动作，应在同一数据库事务中更新业务数据并插入 `Outbox` 记录。这样两项写入会一起成功或一起回滚，应用在两次独立写入之间终止时也不会丢失待上传操作。

### 读、写与调度分别设计

- 读路径：先读取本地数据；需要刷新时由仓库访问网络，再以事务更新本地数据。旧数据继续可读时，状态中附带同步时间、刷新进度和错误。
- 写路径：按业务要求选择仅在线写、排队写或先本地后网络。要求离线不丢的写操作放入持久 `Outbox`。每项操作携带幂等键，即服务端用来识别重复提交并保证多次执行效果相同的标识。
- 调度路径：用 `WorkManager` 的网络约束等待可用网络，并把同步任务注册为“唯一工作”，防止同一逻辑任务并发运行多个实例。`Worker` 是执行这项后台工作的任务单元；它顺序读取持久队列，并按结果返回成功、失败或重试。可重试错误应采用逐步增加等待时间的指数退避，永久错误则记录原因并停止自动重试。
- 合并路径：只有业务语义允许时才合并操作。草稿连续编辑可以保留最终版本；订单提交、转账和审计事件不能按“同资源”任意覆盖。

`NetworkCallback` 是 Android 的网络状态回调，它只能说明系统观察到网络变化，不能保证源站可访问，也不适合直接执行整批同步。需要在应用进程终止后继续调度的任务交给 `WorkManager`；前台页面可以单独发起即时刷新，但结果仍要写回同一个本地数据源。

`Outbox` 记录应按协议需求保存资源标识、操作类型、幂等键、期望服务端版本、请求数据、状态、尝试次数、下次允许尝试时间、创建与更新时间、最近错误分类。请求数据是否允许持久化、是否需要加密、保留多久，都要纳入隐私设计。“乐观更新”指服务端确认前先更新本地界面，提交失败后必须回滚或显示冲突；冲突检测与服务端合并策略详见 24.7。

## 执行检查清单

- 压缩协商：调用方手动覆盖 `Accept-Encoding` 时自行负责解压；服务端按编码返回不同表示时发送正确的 `Vary`。
- 压缩选型：`Protocol Buffers` 不被当成压缩格式；文本、媒体、加密内容和小响应分别测量。
- 解码防护：限制解码后大小、集合数量和解析深度；主线程不执行大型解码或解析。
- 内存缓存：容量按字节等真实成本计算；缓存项可被淘汰，业务对象不能只存在于内存缓存。
- 磁盘缓存：`cacheDir` 数据允许随时缺失；使用相对路径；OkHttp 使用独占子目录。
- HTTP 指令：区分 `no-cache`、`no-store`、`private` 与 `s-maxage`；正确处理 `Vary` 和验证器。
- 账号隔离：敏感响应不存储；多账号缓存分区；退出登录时清除所属数据；缓存键和日志不包含原始凭据。
- 一致性：写后按资源关系失效；同键刷新合并；文件原子替换；损坏条目可删除并重新获取。
- 离线同步：界面与业务逻辑从本地数据源读取；业务写入与 `Outbox` 在同一事务；`Worker` 使用持久队列、网络约束、幂等与可分类重试。

## 参考与验证

- [Android Developers · App-specific storage](https://developer.android.com/training/data-storage/app-specific)
- [Android Developers · StorageManager API reference](https://developer.android.com/reference/android/os/storage/StorageManager)
- [Android Developers · Network access optimization](https://developer.android.com/develop/connectivity/network-ops/network-access-optimization)
- [Android Developers · Offline-first architecture](https://developer.android.com/topic/architecture/data-layer/offline-first)
- [OkHttp · Caching](https://lysine.dev/okhttp/features/caching/)
- [OkHttp 5.x API · CompressionInterceptor](https://lysine.dev/okhttp/5.x/okhttp/okhttp3/-compression-interceptor/)
- [OkHttp 5.x API · BrotliInterceptor](https://lysine.dev/okhttp/5.x/okhttp-brotli/okhttp3.brotli/-brotli-interceptor/)
- [Maven Central · OkHttp metadata](https://repo.maven.apache.org/maven2/com/squareup/okhttp3/okhttp/maven-metadata.xml)
- [OkHttp 5.4.0 · Release](https://github.com/lysine-dev/okhttp/releases/tag/parent-5.4.0)
- [OkHttp 5.4.0 · BridgeInterceptor.kt](https://github.com/lysine-dev/okhttp/blob/parent-5.4.0/okhttp/src/commonJvmAndroid/kotlin/okhttp3/internal/http/BridgeInterceptor.kt)
- [OkHttp 5.4.0 · CompressionInterceptor.kt](https://github.com/lysine-dev/okhttp/blob/parent-5.4.0/okhttp/src/commonJvmAndroid/kotlin/okhttp3/CompressionInterceptor.kt)
- [OkHttp 5.4.0 · BrotliInterceptor.kt](https://github.com/lysine-dev/okhttp/blob/parent-5.4.0/okhttp-brotli/src/main/kotlin/okhttp3/brotli/BrotliInterceptor.kt)
- [OkHttp 5.4.0 · Cache.kt](https://github.com/lysine-dev/okhttp/blob/parent-5.4.0/okhttp/src/commonJvmAndroid/kotlin/okhttp3/Cache.kt)
- [OkHttp 5.4.0 · CacheStrategy.kt](https://github.com/lysine-dev/okhttp/blob/parent-5.4.0/okhttp/src/commonJvmAndroid/kotlin/okhttp3/internal/cache/CacheStrategy.kt)

以下 5.3.0 链接保留为上一轮审校使用的源码锚点：

- [OkHttp 5.3.0 · BridgeInterceptor.kt](https://github.com/square/okhttp/blob/parent-5.3.0/okhttp/src/commonJvmAndroid/kotlin/okhttp3/internal/http/BridgeInterceptor.kt)
- [OkHttp 5.3.0 · CompressionInterceptor.kt](https://github.com/square/okhttp/blob/parent-5.3.0/okhttp/src/commonJvmAndroid/kotlin/okhttp3/CompressionInterceptor.kt)
- [OkHttp 5.3.0 · BrotliInterceptor.kt](https://github.com/square/okhttp/blob/parent-5.3.0/okhttp-brotli/src/main/kotlin/okhttp3/brotli/BrotliInterceptor.kt)
- [OkHttp 5.3.0 · Cache.kt](https://github.com/square/okhttp/blob/parent-5.3.0/okhttp/src/commonJvmAndroid/kotlin/okhttp3/Cache.kt)
- [OkHttp 5.3.0 · CacheStrategy.kt](https://github.com/square/okhttp/blob/parent-5.3.0/okhttp/src/commonJvmAndroid/kotlin/okhttp3/internal/cache/CacheStrategy.kt)
- [RFC 9110 · HTTP Semantics](https://www.rfc-editor.org/rfc/rfc9110.html)
- [RFC 9111 · HTTP Caching](https://www.rfc-editor.org/rfc/rfc9111.html)
- [AOSP android-17.0.0_r1 · Context.java](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/content/Context.java)
- [AOSP android-17.0.0_r1 · StorageManager.java](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/os/storage/StorageManager.java)
