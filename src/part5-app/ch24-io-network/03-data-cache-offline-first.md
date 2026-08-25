---
title: 数据缓存与离线优先架构
chapter: '24.3'
section: '24.3'
status: finalized
applicable_versions: Android 10 (API 29) - Android 17 (API 37)
last_verified: '2026-08-15'
last_verified_against: Android Developers app-specific storage, StorageManager and offline-first docs current through 2026-08-15; OkHttp 5.4.0 source, release and Maven Central metadata; RFC 9110/9111; AOSP android-17.0.0_r1
confidence: high
sources:
- type: official
  path: https://developer.android.com/training/data-storage/app-specific
- type: official
  path: https://developer.android.com/develop/connectivity/network-ops/network-access-optimization
- type: official
  path: https://developer.android.com/topic/architecture/data-layer/offline-first
- type: official
  path: https://developer.android.com/reference/android/os/storage/StorageManager
- type: legacy-reference-preserved
  path: https://square.github.io/okhttp/features/caching/
- type: legacy-reference-preserved
  path: https://square.github.io/okhttp/5.x/okhttp/okhttp3/-compression-interceptor/
- type: legacy-reference-preserved
  path: https://square.github.io/okhttp/5.x/okhttp-brotli/okhttp3.brotli/-brotli-interceptor/
- type: official
  path: https://lysine.dev/okhttp/features/caching/
- type: official
  path: https://lysine.dev/okhttp/5.x/okhttp/okhttp3/-compression-interceptor/
- type: official
  path: https://lysine.dev/okhttp/5.x/okhttp-brotli/okhttp3.brotli/-brotli-interceptor/
- type: official
  path: https://repo.maven.apache.org/maven2/com/squareup/okhttp3/okhttp/maven-metadata.xml
- type: official
  path: https://github.com/lysine-dev/okhttp/releases/tag/parent-5.4.0
- type: official
  path: https://github.com/lysine-dev/okhttp/blob/parent-5.4.0/okhttp/src/commonJvmAndroid/kotlin/okhttp3/internal/http/BridgeInterceptor.kt
- type: official
  path: https://github.com/lysine-dev/okhttp/blob/parent-5.4.0/okhttp/src/commonJvmAndroid/kotlin/okhttp3/CompressionInterceptor.kt
- type: official
  path: https://github.com/lysine-dev/okhttp/blob/parent-5.4.0/okhttp-brotli/src/main/kotlin/okhttp3/brotli/BrotliInterceptor.kt
- type: official
  path: https://github.com/lysine-dev/okhttp/blob/parent-5.4.0/okhttp/src/commonJvmAndroid/kotlin/okhttp3/Cache.kt
- type: official
  path: https://github.com/lysine-dev/okhttp/blob/parent-5.4.0/okhttp/src/commonJvmAndroid/kotlin/okhttp3/internal/cache/CacheStrategy.kt
- type: legacy-reference-preserved
  path: https://github.com/square/okhttp/blob/parent-5.3.0/okhttp/src/commonJvmAndroid/kotlin/okhttp3/internal/http/BridgeInterceptor.kt
- type: legacy-reference-preserved
  path: https://github.com/square/okhttp/blob/parent-5.3.0/okhttp/src/commonJvmAndroid/kotlin/okhttp3/CompressionInterceptor.kt
- type: legacy-reference-preserved
  path: https://github.com/square/okhttp/blob/parent-5.3.0/okhttp-brotli/src/main/kotlin/okhttp3/brotli/BrotliInterceptor.kt
- type: legacy-reference-preserved
  path: https://github.com/square/okhttp/blob/parent-5.3.0/okhttp/src/commonJvmAndroid/kotlin/okhttp3/Cache.kt
- type: legacy-reference-preserved
  path: https://github.com/square/okhttp/blob/parent-5.3.0/okhttp/src/commonJvmAndroid/kotlin/okhttp3/internal/cache/CacheStrategy.kt
- type: official
  path: https://www.rfc-editor.org/rfc/rfc9110.html
- type: official
  path: https://www.rfc-editor.org/rfc/rfc9111.html
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/content/Context.java
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/os/storage/StorageManager.java
- type: clippings
  path: Clippings/Android 性能优化 - 缓存优化：冷热端分离+重排序，提升缓存命中率.md
- type: clippings
  path: Clippings/Android 性能优化 - 物理内存优化实战：Java Heap 内存优化.md
- type: clippings
  path: Clippings/Android 性能优化 - CPU 优化（下）：减少 CPU 闲置时刻和等待，提升利用率.md
- type: official
  path: https://developer.android.com/topic/architecture/data-layer
- type: official
  path: https://developer.android.com/training/data-storage/room
- type: official
  path: https://developer.android.com/develop/background-work/background-tasks/persistent/getting-started/define-work
- type: official
  path: https://developer.android.com/topic/libraries/architecture/paging/v3-network-db
- type: official
  path: https://developer.android.com/training/data-storage/room/referencing-data
- type: official
  path: https://developer.android.com/develop/background-work/background-tasks/persistent/how-to/manage-work
- type: official
  path: https://developer.android.com/develop/background-work/background-tasks/persistent/how-to/states
- type: official
  path: https://developer.android.com/reference/androidx/hilt/work/HiltWorker
- type: official
  path: https://developer.android.com/reference/androidx/work/Data
- type: official
  path: https://developer.android.com/jetpack/androidx/releases/room
- type: official
  path: https://developer.android.com/jetpack/androidx/releases/work
- type: official
  path: https://developer.android.com/jetpack/androidx/releases/paging
- type: standard
  path: https://www.rfc-editor.org/rfc/rfc9110.html
- type: clippings
  path: Clippings/Android 性能优化 - 原理：重新认识应用的速度优化.md
- type: clippings
  path: Clippings/Android 性能优化 - 任务调度优化：线程+CPU，提升任务调度优先级.md
tags:
- compression
- caching
- gzip
- brotli
- offline-sync
- offline-first
- sync
- conflict-resolution
- optimistic-update
- room
- workmanager
related_chapters:
- '24.5'
- '12.1'
- '24.2'
- '25.3'
pipeline_stage: finalized
task6_state: reviewed
task9_state: reviewed
task2b_state: fixed
last_review_finalize_at: '2026-08-15T10:34:29+08:00'
last_review_finalize_run_id: 20260815-103429-gracker-writing-review
last_draft_polish_at: '2026-08-15T10:34:29+08:00'
last_draft_polish_run_id: 20260815-103429-gracker-writing
last_consolidated_at: '2026-08-24'
consolidated_from:
- src/part5-app/ch24-io-network/06-data-caching.md
- src/part5-app/ch24-io-network/07-offline-first.md
---

# 数据缓存与离线优先架构

缓存减少重复计算和网络访问，离线优先进一步把本地数据源变成界面读取基线，并在后台同步远端状态。TTL、容量、版本和冲突策略共同决定数据是否可靠。

## 缓存层级、压缩、淘汰与一致性

### 压缩和缓存分别节省什么

网络耗时受 DNS 查询、建连和拥塞影响，也取决于应用传输了多少数据、是否重复下载，以及是否重复解析相同内容。压缩、HTTP 缓存、进程内缓存和离线数据源各有职责，任一机制都无法覆盖其余机制。

压缩以中央处理器（CPU）的运算时间和少量协议开销换取更少的传输字节；缓存以内存、存储空间和一致性成本换取更少的网络访问与解析工作；离线优先架构还要维护可恢复的写队列。评审方案时应同时回答以下问题：

- 数据是否会被重复读取，允许陈旧多久？
- 界面以哪一份持久数据为准，数据冲突时由谁裁决？
- 账号切换、退出登录和租户切换后，旧数据怎样隔离或删除？
- 缓存文件被系统清理、文件损坏或应用升级后，读取路径能否自行恢复？
- 压缩节省的传输时间，是否大于编码、解码和额外耗电？

平台锚点是 Android 17（API 37）/ `android-17.0.0_r1`，HTTP 客户端实现以 OkHttp 5.4.0 为例。OkHttp 的 Maven 坐标仍是 `com.squareup.okhttp3`，5.4.0 源码上游已迁至 `lysine-dev/okhttp`。服务端、内容分发网络（CDN）或客户端库版本不同时，应按部署版本重新核对行为。

### HTTP 请求与响应压缩

#### 先区分内容编码与数据格式

客户端通过 `Accept-Encoding` 声明能够接收的内容编码，服务端通过 `Content-Encoding` 标出响应体采用的编码。gzip 与 Brotli（标头值为 `br`）都属于 HTTP 内容编码；JSON、Protocol Buffers、JPEG 和 MP4 属于数据或媒体格式。内容编码作用于完整表示，数据格式定义表示内部怎样组织，两者处于不同层次。

Protocol Buffers 是按消息结构定义字段的二进制序列化格式，本身不会自动压缩。它通常比等价 JSON 紧凑，但字段值仍可能包含可压缩的重复内容。是否再做 gzip 或 Brotli，要根据样本数据测量，不能因为使用了 `.proto` 就判定“已经压缩”。

#### OkHttp 5.4.0 的透明解压边界

OkHttp 默认的 `BridgeInterceptor` 只在请求没有显式设置 `Accept-Encoding`、并且没有 `Range` 时添加 `Accept-Encoding: gzip`。满足以下条件时，它会流式解压响应：

- 该请求由 OkHttp 自动添加了 gzip 协商头；
- 响应包含 `Content-Encoding: gzip`；
- 响应语义允许携带响应体。

解压后返回给应用的响应会移除 `Content-Encoding` 和 `Content-Length`，解码后长度也被标为未知。业务代码读取的是解压后的内容，不能再用返回响应的 `Content-Length` 推算传输字节数。

OkHttp 5.4.0 还提供通用 `CompressionInterceptor`。它把注册算法组成 `Accept-Encoding`，并按完整的 `Content-Encoding` 值寻找一个已注册算法。它不会逐层解码 `gzip, br` 这类包含多层编码的值。`okhttp-brotli` 5.4.0 中的 `BrotliInterceptor` 注册 `Brotli` 与 `Gzip`，请求会声明 `Accept-Encoding: br, gzip`；这条拦截器路径接管响应解压，并替代 `BridgeInterceptor` 的默认透明 gzip 路径。

如果调用方手动设置了 `Accept-Encoding`，`CompressionInterceptor` 和默认 gzip 路径都不会替调用方透明解码。要关闭压缩，可显式发送 `Accept-Encoding: identity`。不要只添加 `br` 或 `gzip` 请求头，却仍假设响应体会自动解压。

服务端按 `Accept-Encoding` 返回不同表示时，应发送 `Vary: Accept-Encoding`。`Vary` 指定“哪些请求头共同决定缓存变体”，共享缓存据此分别保存 gzip、Brotli 和未编码响应，避免把某种编码发给不支持它的客户端。

#### 哪些数据值得压缩

用线上样本测量压缩收益，不设置适用于所有接口的固定字节阈值：

| 数据形态 | 建议 | 原因 |
| --- | --- | --- |
| JSON、HTML、XML，以及 GraphQL 接口返回的文本 | 评估 gzip 与 Brotli | 键名和结构重复较多，通常存在压缩空间 |
| Protocol Buffers | 用样本决定 | 二进制序列化不等于压缩，收益受字段内容影响 |
| JPEG、WebP、AVIF、音视频和 ZIP | 通常不再套通用压缩 | 这类格式已经使用专用编码，再压缩常见收益有限 |
| 加密或高熵内容 | 通常不再压缩 | “高熵”表示字节分布接近随机，重复模式很少，通用压缩难以缩小 |
| 很小的响应 | 以端到端测量决定 | 编码头、压缩器初始化和处理器时间可能高于传输收益 |

图片和视频应优先调整尺寸、格式、码率和分片策略，相关网络边界见 24.6，端到端耗时分析见 12.1。

请求体压缩需要服务端明确接受对应的请求 `Content-Encoding`。批量日志或大型结构化上传可以评估请求压缩；表单和小型写请求不应默认启用。压缩包装可能改变请求体是否可重复发送，重试前要继续遵守 24.6 的幂等与一次性请求体边界。

#### 测量与防护

至少分别记录：

- 编码前的应用数据大小；
- 网络上传输的字节数；
- 解码后的响应体大小；
- 编码、解码和解析耗时；
- 请求端到端耗时、失败类型与重试次数。

透明解压会让应用层看到的长度与线上传输长度不同。传输字节应从服务端、网络层观测或已验证口径的事件指标采集，解码后长度则在消费响应体时计数，两者不能混用。

客户端还要限制解码后的数据量、集合元素数量和解析深度。攻击者可以构造传输体积很小、解压后急剧膨胀的数据，这类输入常被称为“压缩炸弹”。仅依赖压缩前 `Content-Length` 无法防止异常放大。限制应在构建大型对象前生效，超限时终止读取并记录服务端、媒体类型和编码方式。

### 多级缓存设计：内存 / 磁盘 / 网络

#### 每层只负责自己的语义

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

#### 配置 OkHttp 磁盘缓存

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

### HTTP 缓存：由协议决定能否复用

#### 新鲜度、存储和验证是三件事

RFC 9111 把“能否存储”“当前是否新鲜”“过期后能否验证”分开定义。新鲜状态表示缓存仍可直接复用，陈旧状态表示新鲜期已经结束：

- `max-age` 表示响应从何时起变为陈旧。`Date`、`Age` 和本地驻留时间都会参与当前年龄计算，不能只比较设备时钟与下载时间。
- `Expires` 是绝对过期时间；存在适用的 `max-age` 时，优先采用后者。
- `no-cache` 允许存储，但每次复用前必须向源站验证；源站指生成该资源的原始服务器。因此它表达的是“先验证”，并非“不要存储”。
- `no-store` 要求缓存不要存储请求或响应，也不要用它满足后续请求。它不能替代传输加密、访问控制或端侧数据保护。
- `private` 限制 CDN、代理等共享缓存存储响应，不会禁止私有缓存存储。OkHttp 的磁盘缓存属于私有缓存。
- `s-maxage` 只为共享缓存指定新鲜期。OkHttp 5.4.0 的私有缓存会解析该值，但不会按它决定复用时间。

陈旧响应不能无条件返回。协议指令可以授权缓存在限定条件下复用陈旧响应；产品若采用“先展示旧数据、后台刷新”，还要在应用数据层表达刷新中、陈旧时长和刷新失败，HTTP 缓存无法单独提供这些界面状态。

#### 验证器没有固定高低之分

`ETag`（实体标签）是服务端为某个资源表示分配的版本标识，客户端复查时通过 `If-None-Match` 发送它。`Last-Modified` 记录修改时间，复查时配合 `If-Modified-Since`。服务端返回 `304 Not Modified`，表示内容没有变化；客户端无需再次下载响应体，只需保留缓存内容并更新可合并的响应元数据。

`ETag` 可以表达与时间无关的表示版本，也有强验证器和弱验证器之分。`Last-Modified` 适用于服务端能可靠维护修改时间的资源，但 HTTP 日期粒度、时钟和生成方式会影响判断。两者的适用条件不同，应根据服务端数据模型选择，不能按等级排序。

服务端返回随请求头变化的表示时，用 `Vary` 声明参与选择的请求头。OkHttp 会把这些请求头的名称和值写入缓存元数据，并在复用前逐项比较；`Vary: *` 表示任何请求都不能直接匹配，因此响应不会进入 OkHttp 缓存。若自建缓存键只包含 URL，遗漏语言、内容编码或账号范围，就可能复用错误的响应变体。

#### OkHttp 5.4.0 的实现边界

按 OkHttp 5.4.0 `Cache` 与 `CacheStrategy` 源码：

- 磁盘缓存只写入 `GET` 响应；当前实现不支持缓存 `206 Partial Content` 这类部分响应；
- 请求或响应含 `no-store` 时不会写入；
- 请求含 `no-cache` 时会访问网络或执行条件验证；
- `only-if-cached` 禁止访问网络，找不到可用条目时由 OkHttp 生成 `504 Unsatisfiable Request`；该状态不能解释为源站返回的网络错误；
- 条件命中会访问网络完成验证，同时复用本地响应体，因此同时计入 `networkCount` 和 `hitCount`；
- `requestCount`、`networkCount`、`hitCount` 分别记录总请求数、使用网络的请求数和缓存命中数。

这些计数只能解释 OkHttp 这一层。图片库内存命中、Room 查询和应用文件缓存要分别统计，不能合并成一个缺少层级信息的“总命中率”。评估时还应观察写入失败、淘汰、条件请求、响应年龄、账号范围和因缓存节省的网络字节。

#### 账号与敏感数据隔离

OkHttp 的缓存以 URL 为主键，并依据 `Vary` 记录的请求头匹配响应变体。私有缓存只表示它不与其他客户端共享，并不自动区分同一应用中的多个登录账号。带凭据接口需要明确选择：

- 敏感或一次性数据由服务端返回 `no-store`；
- 允许端侧缓存的账号数据使用账号级独立缓存目录和客户端，退出登录时关闭并删除该账号目录；
- 应用自建缓存键包含账号、租户、环境、查询参数、分页位置和数据版本，但不写入原始令牌；
- 日志、埋点和错误上报不记录 `Authorization`、Cookie 或完整敏感缓存键。

仅返回 `private` 不能解决同一应用内的多账号隔离。响应使用 `Vary: Authorization` 后，OkHttp 会按授权标头区分响应，也会把对应请求头值写入缓存元数据；采用该方案前必须评估设备端保存凭据的风险。

### 业务缓存失效与一致性

#### 先指定权威数据源

TTL（存活时间）规定缓存条目可直接使用多久。固定 TTL 只能表达时间，无法表达用户刚完成写操作、服务端版本改变或依赖资源已经更新。应用应为每类数据指定权威数据源，并给缓存条目记录可验证的来源与版本。

一个应用自建缓存条目通常需要以下维度：

- 资源标识、账号、租户和环境；
- 经过规范化的查询参数与分页位置；
- 数据结构版本、服务端版本或验证器；
- 写入时间、允许陈旧时间和来源；
- 完整性信息，例如长度、校验值或原子提交标记。

写操作成功后，应按资源关系让受影响条目失效，不能只删除当前接口 URL。例如，头像更新会影响用户详情、会话列表和个人页摘要。依赖关系可以用标签记录，也可以建立从资源标识指向缓存键的“反向索引”，由资源查出所有相关条目。无法可靠枚举依赖时，可提升账号或资源版本，让旧版本缓存整体失效，这比在多处手工删除更容易验证。

#### 处理并发、损坏和陈旧数据

同一缓存键过期时，多个并发读取可能同时发起刷新。`single-flight` 指把这些同键请求合并为一次实际刷新，其余调用等待并共享结果。互斥范围应限制在同一键，某次超时或取消不能让其他键停止刷新。多进程应用还要使用进程间可见的原子写入或数据库事务，进程内锁无法保护另一个进程。

磁盘内容应先写入同一文件系统中的临时文件，校验成功后再用原子重命名替换目标；在文件系统提供该保证时，读取者只会看到旧文件或完整的新文件。读取时把文件不存在、零长度、结构版本不支持、校验失败和解析失败都视为可恢复的缓存未命中；删除损坏条目，再从权威数据源获取。持久业务数据损坏则应进入迁移或恢复流程。

展示陈旧数据时，界面状态至少能区分“已有旧数据、正在刷新”“已有旧数据、刷新失败”和“没有数据”。字段 `lastSyncedAt` 应记录最近一次成功同步的时间，失败的尝试不能改写它。预取任务要设置业务范围和淘汰优先级，避免一次性内容挤占高复用资源。

### 缓存与离线真源的边界

HTTP、内存和可删除文件缓存都用于减少重复工作，条目缺失时应能回到权威数据源重新取得。它们不能表示本地写入是否已经被服务端确认，也不能独立保存冲突版本、幂等键或用户可见失败状态。

需要离线读写时，应把本地持久数据源提升为界面唯一读取入口，并用持久队列记录待同步操作。具体的 Room 事务、Outbox、WorkManager、冲突处理和乐观更新由本文下一部分统一展开，缓存层只负责命中、失效、淘汰与可恢复缺失。

### 缓存执行检查清单

- 压缩协商：调用方手动覆盖 `Accept-Encoding` 时自行负责解压；服务端按编码返回不同表示时发送正确的 `Vary`。
- 压缩选型：`Protocol Buffers` 不被当成压缩格式；文本、媒体、加密内容和小响应分别测量。
- 解码防护：限制解码后大小、集合数量和解析深度；主线程不执行大型解码或解析。
- 内存缓存：容量按字节等真实成本计算；缓存项可被淘汰，业务对象不能只存在于内存缓存。
- 磁盘缓存：`cacheDir` 数据允许随时缺失；使用相对路径；OkHttp 使用独占子目录。
- HTTP 指令：区分 `no-cache`、`no-store`、`private` 与 `s-maxage`；正确处理 `Vary` 和验证器。
- 账号隔离：敏感响应不存储；多账号缓存分区；退出登录时清除所属数据；缓存键和日志不包含原始凭据。
- 一致性：写后按资源关系失效；同键刷新合并；文件原子替换；损坏条目可删除并重新获取。

### 缓存部分的参考与验证

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


## 本地真源、同步队列与冲突处理

单次缓存命中解决访问成本，离线优先还要管理本地写入、待同步操作、服务端确认和冲突。用户可见状态必须反映同步结果。

### 离线优先先保证什么

离线优先把网络中断、变慢和暂时不可用视为数据层的常见条件。Android 官方给出的最低要求是：应用的主要内容在没有网络时仍可读取。离线优先不要求每一种写操作都支持离线提交，转账、权限授予或需要实时库存确认的操作仍可采用仅在线写入。

平台锚点是 Android 17（API 37）/ `android-17.0.0_r1`。Room 是基于 SQLite 的持久化库，WorkManager 用于持久后台调度，Paging 用于分页加载；它们都属于 AndroidX，能力随库版本变化。示例只使用这些库的稳定公开接口，不把 AndroidX 行为归因于平台版本。

本节前文区分了可删除缓存与持久数据。离线优先还要保存用户操作、同步进度、服务端版本和失败状态。本地权威数据源是界面与业务逻辑唯一读取的数据副本；它可能暂时落后于服务端，但应用不会因网络状态不同而读取两套相互冲突的数据。Outbox 是数据库中的待发送操作表，服务端幂等协议则用固定标识识别同一次操作的重复请求。两者共同保证写入可恢复。

设计离线能力前，要逐项回答：

- 哪些页面在首次安装且无网络时仍应可用？
- 哪些写操作只能在线确认，哪些可以排队，哪些允许先改本地？
- 本地与服务端都修改了同一资源时，由谁检测和处理冲突？
- 进程在服务端成功之后、本地确认之前终止，重发会不会产生重复结果？
- 账号退出、租户切换和令牌失效时，旧队列怎样停止与清理？

### 离线优先的设计原则

#### 本地数据源是读取入口

离线优先的 `Repository` 是协调本地与网络数据源的数据访问组件。`Flow` 表示可持续发出新值的异步数据流，`StateFlow` 还会保留当前值，Paging 数据流则按页提供列表。界面与业务逻辑只观察本地数据；网络读取完成后先写入本地，再由本地数据变化通知界面。它们不应绕过 `Repository` 直接读取网络数据源。

界面仍需要同步语义。只暴露业务实体而没有刷新状态，会让“旧数据可读”和“数据已经同步”混为一谈。建议把以下信息作为界面状态的一部分：

- 本地是否有可展示数据；
- 最近一次成功同步时间；
- 当前是否刷新；
- 最近一次刷新是否失败；
- 用户操作处于待同步、待登录、冲突还是永久失败。

#### 为每类写入选择策略

Android 官方离线优先指南给出三类写入。策略应按业务风险选择，本地队列的实现能力不能决定业务结果：

| 写入策略 | 适用情况 | 本地行为 | 用户看到的结果 |
| --- | --- | --- | --- |
| 仅在线写入 | 转账、实时库存、权限变更 | 服务端确认后再更新权威本地数据 | 成功或失败均明确返回 |
| 排队写入 | 日志、遥测、非时效上报 | 操作进入持久队列，稍后发送 | 通常不阻塞当前操作 |
| 延迟写入 | 草稿、待办、可离线编辑内容 | 先更新本地，再把变更加入 Outbox | 立即可见，同时显示同步状态 |

“延迟写入”也常称为乐观更新：服务端确认前先改变本地状态，并把失败或冲突保留下来供后续处理。支付或订单可以在本地显示“已提交”，但不能在服务端确认前显示“已支付”或“已下单成功”。提前反馈的对象是提交动作，不能把尚未成立的业务结果标为成功。

#### 分开保存四类状态

结构化离线数据通常需要四组表或等价持久结构：

- 业务实体：界面查询的用户数据；
- Outbox：尚未得到服务端确认的本地操作；
- 远端分页键或增量水位：分页键记录某组查询从哪个游标继续取下一页，增量水位记录本地已经同步到哪个版本、时间点或令牌；
- 同步状态：账号、数据域、成功时间、错误分类和下一次可尝试时间。

HTTP 缓存不能替代这些表。WorkManager 自己的数据库也不是业务队列：它保存工作调度状态，不保存业务冲突、账号版本和用户可见失败。

### Room + WorkManager 的离线架构

#### Room 表按读取和同步方式建模

Room 适合保存结构化本地数据。表结构应来自界面查询、同步顺序、冲突字段和账号隔离，不能逐字段照搬接口响应。数据库索引会额外保存可快速查找的列值，适合“某账号下可立即发送的 Outbox 项”这类高频查询；索引也会增加写入与存储成本。数据库迁移还要覆盖升级前遗留的待同步操作。

这个实体骨架展示 Outbox 需要表达的协议状态。字段名仅用于说明边界，业务应按服务端协议调整：

```kotlin
enum class OutboxStatus {
    PENDING,
    WAITING_FOR_AUTH,
    CONFLICT,
    PERMANENT_FAILURE,
}

@Entity(
    tableName = "sync_outbox",
    indices = [
        Index(
            value = ["localOperationId"],
            unique = true,
        ),
        Index(
            value = [
                "accountId",
                "status",
                "nextAttemptAtMillis",
                "localSequence",
            ],
        ),
    ],
)
data class SyncOutboxEntity(
    @PrimaryKey(autoGenerate = true)
    val localSequence: Long = 0,
    val localOperationId: String,
    val accountId: String,
    val resourceType: String,
    val resourceId: String,
    val operation: String,
    val payloadJson: String,
    val idempotencyKey: String,
    val expectedServerVersion: String?,
    val status: OutboxStatus,
    val attemptCount: Int,
    val nextAttemptAtMillis: Long?,
    val lastErrorCategory: String?,
    val createdAtMillis: Long,
    val updatedAtMillis: Long,
)
```

重试同一操作时必须复用同一个 `idempotencyKey`；用户发起新的业务操作时生成新键。服务端需要记录这个键及处理结果，再次收到同一键时返回已有结果或避免重复产生副作用。`expectedServerVersion` 表示本次修改依据的服务端版本，用于发现“读取之后又被别人修改”的并发冲突。幂等键识别重复操作，版本字段识别数据变化，两者不能互相替代。

`localSequence` 由数据库生成，用于稳定选择本地操作顺序；`createdAtMillis` 用于展示和观测，不能独自决定先后。服务端确认后，可以删除 Outbox 行；若业务要求保留审计记录，应转入字段更受控、保留规则独立的历史表。

Room 2.3 及以上在没有自定义转换器时，会把枚举名称转换为字符串保存；自定义 `@TypeConverter` 的优先级更高。当前稳定版 Room 2.8.4 仍保留该行为。枚举常量改名后，旧字符串可能无法解析；需要长期演进的数据库格式应使用稳定编码，并为已有数据提供迁移。

`payloadJson` 可能包含用户输入或凭据派生信息。存储前要限定字段、保留时间和日志输出；需要加密时，还要设计密钥失效后的清理路径。不要把访问令牌保存进 Outbox。

#### 本地变更与 Outbox 同事务写入

这个函数用一次 Room 事务同时更新收藏状态和插入待发送操作：

```kotlin
suspend fun setBookmarked(
    accountId: String,
    articleId: String,
    bookmarked: Boolean,
) {
    val operationId = idGenerator.newId()
    val nowMillis = clock.nowMillis()

    database.withTransaction {
        val operation = SyncOutboxEntity(
            localOperationId = operationId,
            accountId = accountId,
            resourceType = "article",
            resourceId = articleId,
            operation = "set_bookmarked",
            payloadJson = payloadEncoder.encodeBookmark(bookmarked),
            idempotencyKey = operationId,
            expectedServerVersion = articleDao.serverVersion(
                accountId = accountId,
                articleId = articleId,
            ),
            status = OutboxStatus.PENDING,
            attemptCount = 0,
            nextAttemptAtMillis = null,
            lastErrorCategory = null,
            createdAtMillis = nowMillis,
            updatedAtMillis = nowMillis,
        )

        articleDao.setBookmarkLocally(
            accountId = accountId,
            articleId = articleId,
            bookmarked = bookmarked,
            pendingOperationId = operationId,
        )
        outboxDao.insert(operation)
    }

    syncScheduler.ensureScheduled(accountId)
}
```

`pendingOperationId` 让远端确认能够对应到具体本地操作。用户快速切换两次收藏状态时，较早请求的确认不能清除较新操作的待同步标记。服务端版本读取、业务实体更新与 Outbox 插入都在同一事务中：三项写入一起提交或一起回滚，账号也参与每次查询。

调度调用位于事务之后。如果进程恰好在事务提交后、调用 `ensureScheduled()` 前终止，Outbox 记录仍在；应用启动、登录恢复或其他同步入口必须再次安排“唯一工作”。唯一工作以固定名称避免重复调度同一逻辑任务。Outbox 保存待发送这一业务事实，`WorkRequest` 只记录何时、在什么约束下运行 `Worker`。

网络请求不能包在 Room 事务里。发送前用短事务选择可发送记录，响应回来后再用短事务更新实体、服务端版本和 Outbox 状态，避免网络等待期间占用数据库事务。

#### WorkManager 负责持久调度

WorkManager 会持久保存调度记录，适合离开界面、进程退出或设备重启后仍需执行的同步。`NetworkType.CONNECTED` 约束只能说明系统判断当前有可用网络，不能保证鉴权有效、DNS 成功或源站可访问，`Worker` 仍要分类处理请求结果。

这个 `Worker` 骨架只从输入数据读取账号标识，业务请求数据仍保存在 Room：

```kotlin
@HiltWorker
class OutboxSyncWorker @AssistedInject constructor(
    @Assisted appContext: Context,
    @Assisted params: WorkerParameters,
    private val repository: OfflineRepository,
) : CoroutineWorker(appContext, params) {

    override suspend fun doWork(): Result {
        val accountId = inputData.getString(INPUT_ACCOUNT_ID)
            ?: return Result.failure()

        return when (repository.drainReadyOutbox(accountId)) {
            DrainResult.DRAINED -> Result.success()
            DrainResult.WAITING_FOR_USER -> Result.success()
            DrainResult.RETRYABLE_FAILURE -> Result.retry()
            DrainResult.INVALID_CONFIGURATION -> Result.failure()
        }
    }
}
```

带业务依赖的 `Worker` 需要 `HiltWorkerFactory` 或自定义 `WorkerFactory`。Hilt 是依赖注入库；使用 `@HiltWorker` 时，“辅助注入”表示 `Context` 与 `WorkerParameters` 由 WorkManager 在运行时提供，Hilt 注入其余应用依赖。这些应用依赖必须能由 `SingletonComponent` 提供，也就是处于应用生命周期范围。没有使用 Hilt 的项目，可以让 `Worker` 从应用级依赖容器获取 `Repository`。

WorkManager 的输入与输出 `Data` 存在序列化大小上限，由 `Data.MAX_DATA_BYTES` 定义。它适合传账号或队列标识，不适合复制整批请求数据。队列内容保存在 Room 后，重新安排工作、进程恢复和账号清理都能使用同一份状态。

同步工作应按账号或租户设置唯一名称，并明确选择 `ExistingWorkPolicy`。`KEEP` 保留已有工作并忽略新请求，适合“同一账号已有一个队列处理器”的场景；`REPLACE` 会取消旧 `Worker`；`APPEND` 把新工作接到旧工作之后，也会继承前置工作的失败或取消状态。若新工作不应受前置失败影响，可评估 `APPEND_OR_REPLACE`。策略要结合队列顺序与取消语义测试，不能只为避免重复启动而随意替换。

唯一工作只限制同名 WorkManager 工作，不能限制页面协程、其他调度入口或另一个进程同时读取 Outbox。所有发送入口还要经过同一同步协调器，或在数据库事务中“原子认领”记录：用带状态条件的更新把待发送行标为已认领，只有更新成功的调用方可以发送。若实现持久的“发送中”状态，还要定义 `Worker` 被取消或进程终止后的重新认领规则；服务端幂等仍然不可省略。

Worker 运行期间约束失效时，WorkManager 会停止它；Worker 收到停止信号后返回的 `Result` 会被忽略。协程代码应保留取消传播，网络、文件和数据库操作也要能停止。不要捕获 `CancellationException` 后转换成普通成功或失败。

WorkManager 不保证精确开始时间。需要用户立即等待结果的前台操作应走页面生命周期内的请求；同时需要进程退出后继续完成时，再把持久 Outbox 交给 WorkManager。

#### 失败分类决定队列状态

统一把所有失败返回 `Result.retry()` 会制造无效请求，也会让用户看不到需要操作的错误。指数退避是每次临时失败后逐步延长等待时间，它只适用于预期稍后可能恢复的错误。队列状态可以按以下边界处理：

| 结果 | 队列处理 | 调度处理 |
| --- | --- | --- |
| 连接中断、超时、可重试的服务端错误 | 保留待发送状态，增加尝试记录 | 按退避策略重试 |
| `429` | 读取合法的 `Retry-After`；该响应头给出服务端允许重试的时间或等待秒数 | 记录下次可尝试时间，到时再安排 |
| `401` 或登录失效 | 改为等待登录或令牌恢复 | 不进行无限退避重试 |
| 请求数据校验失败 | 标记永久失败并保存可展示原因 | 结束本次 Worker |
| `412 Precondition Failed` | 标记版本冲突并拉取远端版本 | 进入冲突策略 |
| `409 Conflict` | 按服务端定义的业务冲突处理 | 不默认当作临时网络错误 |
| 删除返回资源不存在 | 按删除协议判断是否可视为幂等成功 | 完成或转为业务失败 |

表中的临时传输错误、身份失效、数据错误与版本冲突会进入不同队列状态。退避时间、服务端限流时间和业务重试上限也属于不同约束。服务端明确给出等待时间时，业务队列要保存它；WorkManager 的退避只负责工作级重新调度。

为了处理“服务端已成功、本地尚未确认时进程终止”，发送端必须复用原操作的幂等键。服务端返回已有结果后，本地按普通成功确认。仅靠 WorkManager 的唯一工作不能防止这种重复请求。

### 冲突解决策略

#### 幂等与并发控制解决不同问题

幂等键识别“同一个操作被重发”，服务端版本识别“操作基于旧数据”。前者防止重复执行副作用，后者防止旧副本覆盖新数据。两者都需要：

- 同一 Outbox 项每次重试使用相同幂等键；
- 用户再次发起操作时使用新幂等键；
- 本地保存最近确认的服务端版本；
- 写请求携带它所依据的版本；
- 服务端原子地检查版本并执行写入。

使用 HTTP `ETag`（实体标签）作为版本时，修改请求可以发送 `If-Match`。弱 ETag 以 `W/` 开头，只表示两个响应在语义上等价；强 ETag 才能标识完全匹配的表示。RFC 9110 要求 `If-Match` 做强比较，因此弱 ETag 无法满足这项写入前置条件。版本不匹配通常返回 `412 Precondition Failed`；`409 Conflict` 表示资源当前状态与业务操作冲突，具体含义由接口协议定义。客户端要分别处理，测试不能只覆盖 `409`。

#### 冲突策略按业务风险选择

| 策略 | 适用情况 | 服务端与本地需要保存 | 失败方式 |
| --- | --- | --- | --- |
| 服务端版本覆盖 | 公告、推荐、只读配置 | 服务端版本、同步水位 | 本地旧副本被替换 |
| 服务端判定的后写覆盖 | 低风险且允许覆盖的字段 | 服务端接收序列或可信时间 | 较早编辑可能丢失 |
| 字段级合并 | 字段互相独立的资料或设置 | 字段版本、修改来源 | 同字段仍可能冲突 |
| 操作级合并 | 可交换或可累积的业务操作 | 操作标识与合并规则 | 错误规则会重复或漏算 |
| 用户处理 | 文档编辑、审批和高风险业务 | 本地副本、远端副本、差异与恢复入口 | 用户需要明确选择 |

“后写覆盖”表示服务端保留它判定为较晚的修改。若直接比较设备时间，结果会受到用户改时钟、时区、离线时长和设备漂移影响。可以由服务端分配版本或接收序列；若产品必须保留用户编辑发生时间，它只作为展示与策略输入之一，不能充当唯一并发条件。

删除操作需要“墓碑”或等价的服务端删除版本。墓碑保留资源标识、删除版本和时间，不再保留正常业务内容，用于告诉其他副本“该资源已经删除”。只从本地表移除记录，会让下一次增量同步把服务端旧对象重新写回；墓碑也需要保留期限和服务端确认规则。

同一资源存在多个待发送操作时，应定义顺序与合并条件。操作合并是把多个尚未发送、业务含义可替代的变更压成一个目标状态。例如，“设置收藏状态”可以只保留较新的目标值；已经发送的请求必须等待确认、依靠版本条件，或由服务端按操作序列处理。订单、转账和审计事件不能按资源标识合并。

同步批量不使用通用固定条数。选择量要结合请求数据大小、单次数据库事务时间、服务端限流、Worker 可用时间和失败隔离能力。网络调用在事务外执行，服务端响应对应的数据与分页键在短事务中一起提交。

### 渐进式加载与乐观更新

#### Paging 3 仍以数据库驱动界面

`RemoteMediator` 是 Paging 在本地数据不足或需要刷新时调用的网络加载器，它把远端结果写入 Room，不直接把网络响应交给界面。`PagingSource` 是本地分页读取接口，只从 Room 取数据并提供给界面。网络成功但数据库事务失败时，界面不应显示那一页；数据库写入成功后，Room 使旧 `PagingSource` 失效，再由新实例从本地读出更新后的分页数据。

远端分页键记录某组查询下一次应使用的服务端游标。它与对应数据要在同一个事务中更新，否则进程可能只保存了下一页键，却没有保存这一页数据，恢复后会跳过内容；也可能只保存数据而重复请求同一页。

`RemoteMediator.initialize()` 返回值决定首次创建分页流时是否访问网络。`REFRESH` 表示重建或刷新列表，`APPEND` 和 `PREPEND` 分别表示向列表末尾和开头加载：

- `LAUNCH_INITIAL_REFRESH` 发起远端刷新，并让远端 `APPEND` 与 `PREPEND` 等待该刷新成功；
- `SKIP_INITIAL_REFRESH` 跳过这次远端刷新，直接使用已有本地数据。

缓存是否需要刷新由数据域的过期规则决定，不应复制文档示例中的固定时长。刷新失败时保留本地列表，通过 `LoadState` 或业务状态给出重试入口。`LoadState` 用 `Loading`、`Error` 和 `NotLoading` 表示一次分页加载正在进行、已经失败或当前没有加载。

分页键必须包含查询条件、账号和排序方式。只用一个全局 `nextKey`，会让不同搜索词或账号共享分页位置。服务端改变排序或游标格式时，还要清理相应分页键并启动完整刷新。

#### 乐观更新需要持久状态机

状态机为每项操作规定允许的状态及转换，例如“待同步 → 已确认”或“待同步 → 冲突”。把当前状态持久化后，应用进程重建仍能恢复同一语义。乐观更新适合收藏、已读、草稿和其他可回滚或可解释失败的动作。界面状态应区分：

| 状态 | 界面含义 | 后续动作 |
| --- | --- | --- |
| 待同步 | 本地已更新，服务端尚未确认 | 允许继续浏览，显示轻量状态 |
| 已确认 | 服务端接受了对应操作 | 清除对应待同步标识 |
| 待登录 | 操作仍保留，需要恢复身份 | 引导登录后重新安排同步 |
| 冲突 | 服务端版本已变化 | 自动合并或让用户处理 |
| 永久失败 | 服务端拒绝且不会自动重试 | 回滚或保留失败副本 |

确认响应必须匹配 `pendingOperationId`。较早操作的迟到响应不能覆盖较新本地状态。永久失败时采用回滚还是保留本地副本，由业务可逆性决定；无论哪种，都要持久化结果，不能只显示一次短暂提示。

仅在线高风险操作也可以提供渐进反馈，但文案必须保持“处理中”或“等待服务端确认”。网络断开、页面退出和进程终止后，界面从本地状态恢复同一语义。

### 同步可观测性与恢复验证

这里的“可观测性”指能通过指标和日志回答队列积压多久、同步卡在哪一类状态，以及用户当前看到的数据有多旧。接口成功率无法单独说明离线体验，应分层记录：

- 首次本地可读耗时、本地为空与本地陈旧的比例；
- 最近成功同步时间与数据年龄；
- Outbox 条目数量、年龄分布和账号归属；
- 成功、临时失败、待登录、冲突与永久失败的数量；
- `412`、`409`、限流和服务端幂等命中的结果；
- WorkManager 工作状态、停止原因和重试次数；
- Room 事务耗时、分页键异常与数据库迁移失败。

日志中只记录内部操作标识和错误分类，不记录令牌、完整请求数据或用户正文。账号退出时要取消该账号的唯一工作，删除或隔离它的业务数据、分页键和 Outbox，并验证已经运行的请求返回后不会写回已退出账号。

恢复测试应覆盖：

- 首次安装后在飞行模式进入页面；
- 有旧数据时刷新失败；
- 本地事务提交后、安排 WorkRequest 前终止进程；
- 服务端成功后、本地确认前终止进程；
- Worker 运行期间失去网络约束或收到取消；
- 设备重启、进程重建和数据库迁移；
- 令牌失效、账号切换与退出登录；
- `429`、`412`、`409`、永久校验错误和重复幂等键；
- 设备时间错误、多端乱序写入与删除后同步；
- 用户连续修改同一资源，远端响应按不同顺序返回。

### 设计审查清单

- 读取：界面与业务逻辑只从本地权威数据源观察数据，刷新状态与数据状态分开表达。
- 写入：每类操作明确选择仅在线、排队或延迟写入，不把高风险结果提前标成成功。
- 事务：用户可见本地变更与 Outbox 同事务；网络调用不占用 Room 事务。
- 幂等：同一操作重试复用键，新操作使用新键，服务端提供对应去重保证。
- 冲突：版本条件、`412` 和 `409` 语义写入接口协议；设备时间不是唯一顺序依据。
- 调度：WorkManager 只处理持久调度，业务请求数据与状态保存在 Room。
- 多账号：队列、唯一工作、分页键和数据均按账号隔离，退出登录有清理与迟到响应防护。
- Paging：远端分页键与数据同事务，查询条件与排序参与分页键范围。
- 乐观更新：待同步、待登录、冲突和永久失败均能在进程重建后恢复。
- 隐私：Outbox 不保存访问令牌，日志不输出完整请求数据，敏感内容有保留和清理规则。

## 全文小结

缓存与离线优先解决的是两个层级的问题：缓存通过压缩、复用和淘汰降低重复成本，离线优先通过本地真源、持久操作队列和冲突协议保证网络不稳定时的数据语义。可删除缓存永远不能承担用户资产、同步状态或待确认写入。

实现时先指定每类数据的权威来源、新鲜度、账号范围和恢复方式，再让 Room 事务保存业务变更与 Outbox，让 WorkManager 只负责调度。验收不仅看命中率和接口成功率，还要检查数据年龄、积压、幂等命中、冲突、进程终止恢复和账号清理。

## 参考资料

- [Android Developers · Build an offline-first app](https://developer.android.com/topic/architecture/data-layer/offline-first)
- [Android Developers · Data layer](https://developer.android.com/topic/architecture/data-layer)
- [Android Developers · Save data in a local database using Room](https://developer.android.com/training/data-storage/room)
- [Android Developers · Referencing complex data using Room](https://developer.android.com/training/data-storage/room/referencing-data)
- [Android Developers · Task scheduling with WorkManager](https://developer.android.com/develop/background-work/background-tasks/persistent)
- [Android Developers · Define work requests](https://developer.android.com/develop/background-work/background-tasks/persistent/getting-started/define-work)
- [Android Developers · Manage work](https://developer.android.com/develop/background-work/background-tasks/persistent/how-to/manage-work)
- [Android Developers · Work states](https://developer.android.com/develop/background-work/background-tasks/persistent/how-to/states)
- [Android Developers · HiltWorker](https://developer.android.com/reference/androidx/hilt/work/HiltWorker)
- [Android Developers · WorkManager Data](https://developer.android.com/reference/androidx/work/Data)
- [Android Developers · Page from network and database](https://developer.android.com/topic/libraries/architecture/paging/v3-network-db)
- [AndroidX · Room release notes](https://developer.android.com/jetpack/androidx/releases/room)
- [AndroidX · WorkManager release notes](https://developer.android.com/jetpack/androidx/releases/work)
- [AndroidX · Paging release notes](https://developer.android.com/jetpack/androidx/releases/paging)
- [RFC 9110 · HTTP Semantics](https://www.rfc-editor.org/rfc/rfc9110.html)
