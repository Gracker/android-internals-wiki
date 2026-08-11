---
title: "数据压缩与缓存策略"
chapter: "24.6"
section: "24.6"
status: finalized
applicable_versions: "Android 10 (API 29) - Android 17 (API 37)"
last_verified: "2026-06-30"
last_verified_against: "Android Developers docs 2026-06-30 + OkHttp 5.x docs + RFC 9110/9111 + AOSP android-17.0.0_r1"
confidence: medium
drafted_date: "2026-05-14"
reviewed_by: openclaw-task6
reviewed_date: "2026-05-14"
last_task6_audit: "2026-07-08"
task6_result: pass-light-edit
polish_count: 1
sources:
  - type: official
    path: "https://developer.android.com/training/data-storage/app-specific"
  - type: official
    path: "https://developer.android.com/develop/connectivity/network-ops/network-access-optimization"
  - type: official
    path: "https://developer.android.com/topic/architecture/data-layer/offline-first"
  - type: official
    path: "https://square.github.io/okhttp/features/caching/"
  - type: official
    path: "https://square.github.io/okhttp/5.x/okhttp/okhttp3/-compression-interceptor/"
  - type: official
    path: "https://square.github.io/okhttp/5.x/okhttp-brotli/okhttp3.brotli/-brotli-interceptor/"
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
pipeline_stage: ready-to-publish
task6_state: reviewed
task9_state: reviewed
task2b_state: fixed
last_task2a_at: "2026-05-14T11:04:00+08:00"
task9_result: auto-fixed
task9_reviewed_by: openclaw-task9
task9_reviewed_date: "2026-06-30"
last_task9_at: "2026-06-30T22:26:27+08:00"
last_task9_audit: "2026-06-30"
last_task9_autofix_at: "2026-06-30"
deepseek_cn_review_state: done
last_deepseek_cn_review_at: 2026-07-06
---

# 数据压缩与缓存策略

## 为什么要了解数据压缩与缓存策略

网络耗时不只由 DNS、建连和拥塞决定。应用还可以减少传输字节、避免重复下载、复用已经解析的数据，并在断网时继续提供可读内容。压缩、HTTP 缓存、进程内缓存和离线数据源分别负责其中一部分，不能用一种机制代替其余机制。

压缩以 CPU 和少量协议开销换取更少的传输字节；缓存以内存、存储和一致性成本换取更少的网络访问与解析工作；离线优先架构还要维护可恢复的写队列。评审方案时应同时回答以下问题：

- 数据是否会被重复读取，允许陈旧多久？
- 哪一份数据是界面读取的权威副本？
- 账号切换、退出登录和租户切换后，旧数据怎样隔离或删除？
- 缓存文件被系统清理、文件损坏或应用升级后，读取路径能否自行恢复？
- 压缩节省的传输时间，是否大于编码、解码和额外耗电？

平台锚点是 Android 17（API 37）/ `android-17.0.0_r1`，HTTP 客户端实现以 OkHttp 5.3.0 为例。服务端、CDN 或客户端库版本不同时，应按线上版本重新核对行为。

## 请求 / 响应数据压缩（gzip / brotli）

### 先区分内容编码与数据格式

客户端通过 `Accept-Encoding` 声明能够接收的内容编码，服务端通过 `Content-Encoding` 标出响应体采用的编码。`gzip` 和 Brotli 都属于 HTTP 内容编码。JSON、Protocol Buffers、JPEG 和 MP4 则是数据或媒体格式，两者不是同一层概念。

Protocol Buffers 提供二进制序列化，不自动压缩。它通常比等价 JSON 紧凑，但字段值仍可能包含可压缩的重复内容。是否再做 gzip 或 Brotli，要根据样本数据测量，不能因为使用了 `.proto` 就判定“已经压缩”。

### OkHttp 5.3.0 的透明解压边界

OkHttp 默认的 `BridgeInterceptor` 只在请求没有显式设置 `Accept-Encoding`、并且没有 `Range` 时添加 `Accept-Encoding: gzip`。满足以下条件时，它会流式解压响应：

- 该请求由 OkHttp 自动添加了 gzip 协商头；
- 响应包含 `Content-Encoding: gzip`；
- 响应语义允许携带响应体。

解压后返回给应用的响应会移除 `Content-Encoding` 和 `Content-Length`，解码后长度也被标为未知。业务代码读取的是解压后的内容，不能再用返回响应的 `Content-Length` 推算传输字节数。

OkHttp 5.3.0 还提供通用 `CompressionInterceptor`。它把注册算法组成 `Accept-Encoding`，只解码自己认识的响应编码。该版本按完整的 `Content-Encoding` 值匹配单个算法，不会逐层解码由多个编码组成的值。`okhttp-brotli` 5.3.0 中的 `BrotliInterceptor` 继承该实现，并按源码注册 `Brotli` 与 `Gzip`。这会替代 `BridgeInterceptor` 的默认 gzip 路径。

如果调用方手动设置了 `Accept-Encoding`，`CompressionInterceptor` 和默认 gzip 路径都不会替调用方透明解码。要关闭压缩，可显式发送 `Accept-Encoding: identity`。不要只添加 `br` 或 `gzip` 请求头，却仍假设响应体会自动解压。

服务端按 `Accept-Encoding` 返回不同表示时，应发送 `Vary: Accept-Encoding`。共享缓存据此区分 gzip、Brotli 和未编码的响应，避免把一种表示发给不支持它的客户端。

### 哪些数据值得压缩

用线上样本测量压缩收益，不设置适用于所有接口的固定字节阈值：

| 数据形态 | 建议 | 原因 |
| --- | --- | --- |
| JSON、HTML、XML、GraphQL 文本 | 评估 gzip 与 Brotli | 键名和结构重复较多，通常存在压缩空间 |
| Protocol Buffers | 用样本决定 | 二进制序列化不等于压缩，收益受字段内容影响 |
| JPEG、WebP、AVIF、音视频和 ZIP | 通常不再套通用压缩 | 这类格式已经使用专用编码，再压缩常见收益有限 |
| 加密或高熵内容 | 通常不再压缩 | 输出接近随机分布，通用压缩难以缩小 |
| 很小的响应 | 以端到端测量决定 | 编码头、压缩器初始化和 CPU 成本可能高于传输收益 |

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

客户端还要限制解码后的数据量、集合元素数量和解析深度。压缩响应的线上传输体积很小，不代表解压后也小；仅依赖压缩前 `Content-Length` 无法防止异常放大。限制应放在开始构建大型对象之前，超限时终止读取并记录服务端、媒体类型和编码方式。

## 多级缓存设计：内存 / 磁盘 / 网络

### 每层只负责自己的语义

内存缓存服务于当前进程内的重复访问；磁盘文件缓存允许跨进程生命周期复用可再生成的数据；HTTP 缓存按协议复用响应；Room、DataStore 或持久文件保存应用需要恢复的状态。只有应用数据源可以被定义为界面读取的权威副本，HTTP 缓存和 `cacheDir` 都不具备这个保证。

| 层级 | 常见载体 | 适合缓存的数据 | 淘汰依据 | 主要风险 |
| --- | --- | --- | --- | --- |
| 内存 | `LruCache`、图片库内存层、进程内 Map | Bitmap、解析结果、短生命周期配置 | 容量、最近访问、业务热度 | 占用堆，可能增加 GC 或 OOM 风险 |
| 可删除磁盘文件 | `cacheDir`、`externalCacheDir`、图片库磁盘层 | 图片、接口快照、预取文件 | 配额、最近修改时间、业务分组 | 系统或用户可以删除，读取必须允许缺失 |
| HTTP | OkHttp `Cache`、CDN、代理缓存 | 符合 HTTP 缓存规则的响应 | 新鲜度、验证器和缓存指令 | 错误响应头、账号隔离和陈旧数据 |
| 应用数据源 | Room、DataStore、持久文件 | 用户可见数据、离线数据、同步状态 | 业务版本、账号、租户、服务端版本 | 迁移、冲突、隐私和恢复成本 |

内存缓存的容量应按实际对象大小计算。以 Bitmap 为例，条目大小应来自分配字节数等可验证数据，而不是条目个数。内存等级只能作为容量输入，不能解释为应用可以占满的额度；界面、数据库游标、原生内存和图形资源仍会共同占用进程预算。

AOSP `Context.getCacheDir()` 在 `android-17.0.0_r1` 中说明：

- 系统需要回收存储空间时，会按 `lastModified()` 从较旧文件开始处理；
- 应用应尽量把缓存使用量控制在 `StorageManager.getCacheQuotaBytes()` 返回的动态配额以内；
- 设备采用可迁移存储后，绝对路径可能变化，只应持久化相对路径；
- 应用无需额外权限访问自己的内部缓存目录。

API 26 起公开的 `StorageManager.setCacheBehaviorGroup()` 可以让一个目录在系统自动清理时按组保留或删除，并用组内最新的修改时间代表该组；`setCacheBehaviorTombstone()` 可以让自动清理后的文件留下零长度文件。两者都只接受目录并递归应用，也都只改变系统自动清理时的处理方式。用户主动清除缓存时，墓碑行为会被忽略；按组处理也不提供持久性保证。

`externalCacheDir` 可能不可用，使用前要检查返回值和卷状态。需要在应用升级、进程重启或设备重启后仍可靠恢复的数据，应放在持久数据源中，不应依靠任一缓存目录。

### 配置 OkHttp 磁盘缓存

下面的函数展示如何显式传入容量，并为 OkHttp 分配独占子目录：

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

OkHttp 的 `Cache.delete()` 会删除所配置目录中的全部内容，因此该目录不能混放应用的其他文件。缓存读写失败应退回网络或上层数据源，并记录错误；损坏的缓存不应阻塞正常读取。

## HTTP 缓存：由协议决定能否复用

### 新鲜度、存储和验证是三件事

RFC 9111 把“能否存储”“当前是否新鲜”“过期后能否验证”分开定义：

- `max-age` 表示响应经过多长时间后变为陈旧。`Date`、`Age` 和本地驻留时间都会参与当前年龄计算，不能只比较设备时钟与下载时间。
- `Expires` 是绝对过期时间；存在适用的 `max-age` 时，优先采用后者。
- `no-cache` 允许存储，但每次复用前必须向源站验证。它不是“不要缓存”。
- `no-store` 要求缓存不要存储请求或响应，也不要用它满足后续请求。它不能替代传输加密、访问控制或端侧数据保护。
- `private` 限制共享缓存存储响应，不会禁止专属于单个用户的私有缓存。OkHttp 的磁盘缓存属于私有缓存。
- `s-maxage` 面向共享缓存。OkHttp 5.3.0 的缓存策略源码明确忽略它。

陈旧响应不应被无条件返回。服务端或请求可以通过标准指令允许有限度使用陈旧响应；产品若采用“先展示旧数据、后台刷新”，还要在应用数据层表达刷新中、陈旧时间和刷新失败，不能把这一行为完全交给 HTTP 缓存。

### 验证器没有固定高低之分

`ETag` 配合 `If-None-Match`，`Last-Modified` 配合 `If-Modified-Since`。服务端返回 `304 Not Modified` 后，客户端保留本地响应体并更新可合并的响应元数据。

`ETag` 可以表达与时间无关的表示版本，也有强验证器和弱验证器之分。`Last-Modified` 适用于服务端能可靠维护修改时间的资源，但 HTTP 日期粒度、时钟和生成方式会影响判断。应根据服务端数据模型选择验证器，不应笼统地把一种描述成另一种的低级替代。

服务端返回随请求头变化的表示时，用 `Vary` 声明参与选择的请求头。OkHttp 会保存并比较这些请求头；`Vary: *` 的响应不会进入 OkHttp 缓存。缓存键只看 URL、却忽略语言、内容编码或账号范围，会导致错误复用。

### OkHttp 5.3.0 的实现边界

按 OkHttp 5.3.0 `Cache` 与 `CacheStrategy` 源码：

- 磁盘缓存只写入 `GET` 的完整响应，不缓存部分响应；
- 请求或响应含 `no-store` 时不会写入；
- 请求含 `no-cache` 时会访问网络或执行条件验证；
- `only-if-cached` 找不到可用条目时返回 `504`，它不等于“网络失败”；
- 条件命中同时计入 `networkCount` 和 `hitCount`；
- `requestCount`、`networkCount`、`hitCount` 可用于观察缓存使用情况。

这些计数只能解释 OkHttp 这一层。图片库内存命中、Room 查询和应用文件缓存要分别统计，不能合并成一个缺少层级信息的“总命中率”。评估时还应观察写入失败、淘汰、条件请求、响应年龄、账号范围和因缓存节省的网络字节。

### 账号与敏感数据隔离

OkHttp 的缓存以 URL 为主键，并依据 `Vary` 记录的请求头匹配表示。应用内多账号不等于 RFC 所说的“单个用户”环境。带凭据接口需要明确选择：

- 敏感或一次性数据由服务端返回 `no-store`；
- 允许端侧缓存的账号数据使用账号级独立缓存目录和客户端，退出登录时关闭并删除该账号目录；
- 应用自建缓存键包含账号、租户、环境、查询参数、分页位置和数据版本，但不写入原始令牌；
- 日志、埋点和错误上报不记录 `Authorization`、Cookie 或完整敏感缓存键。

仅返回 `private` 不能解决同一应用内的多账号隔离。让响应 `Vary: Authorization` 虽然能影响匹配，还会把相应请求头写入缓存元数据；采用该方案前必须评估端侧凭据存储风险。

## 业务缓存失效与一致性

### 先指定权威数据源

固定 TTL 只能表达时间，无法表达用户刚完成写操作、服务端版本改变或依赖资源已经更新。应用应为每类数据指定权威数据源，并给缓存条目记录可验证的来源与版本。

一个应用自建缓存条目通常需要以下维度：

- 资源标识、账号、租户和环境；
- 经过规范化的查询参数与分页位置；
- 数据结构版本、服务端版本或验证器；
- 写入时间、允许陈旧时间和来源；
- 完整性信息，例如长度、校验值或原子提交标记。

写操作成功后，按资源关系标记受影响条目，而不是只删除当前接口 URL。例如，头像更新会影响用户详情、会话列表和个人页摘要。依赖关系可以用标签或反向索引记录；无法可靠枚举时，提升账号或资源版本比散落多处的手工删除更容易验证。

### 处理并发、损坏和陈旧数据

同一缓存键并发失效时，可用 single-flight 或等价的请求合并机制，让并发读取共享一次刷新结果。互斥范围应限制在同一键，超时与取消不能让其他键停止刷新。多进程应用还要使用进程间可见的原子写入或数据库事务，进程内锁无法保护另一个进程。

磁盘文件建议写入临时文件、校验成功后原子替换。读取时把文件不存在、零长度、结构版本不支持、校验失败和解析失败都视为可恢复的缓存未命中；删除损坏条目，再从权威数据源获取。只有持久业务数据损坏才进入迁移或恢复流程。

展示陈旧数据时，界面状态至少能区分“已有旧数据、正在刷新”“已有旧数据、刷新失败”和“没有数据”。`lastSyncedAt` 应表示最近一次成功同步，而不是最近一次尝试。预取任务要设置业务范围和淘汰优先级，避免一次性内容挤占高复用资源。

## 离线数据同步

### 缓存与离线数据源不是同一概念

Android Developers 的离线优先架构要求带网络访问的仓库同时具有本地与网络数据源，并建议上层只从本地权威数据源读取。HTTP 缓存可以减少下载，却不能表示一次本地写入是否等待上传，也不能保存冲突版本、幂等键和错误状态。这些状态应由持久待发送队列（Outbox）记录。

下面的结构图用于区分读路径和持久写队列：

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

界面始终观察本地权威数据源；网络刷新写回本地后，界面由数据流更新。需要离线提交的用户动作，应在同一事务中更新本地业务数据并写入 Outbox，避免应用在两次写入之间终止后丢失待上传操作。

### 读、写与调度分别设计

- 读路径：先读取本地数据；需要刷新时由仓库访问网络，再以事务更新本地数据。旧数据继续可读时，状态中附带同步时间、刷新进度和错误。
- 写路径：按业务要求选择仅在线写、排队写或先本地后网络。要求离线不丢的写操作放入持久 Outbox。
- 调度路径：用 WorkManager 的网络约束等待可用网络，并用唯一工作限制同时运行的同步任务。Worker 读取持久队列，按结果返回成功、失败或重试。
- 合并路径：只有业务语义允许时才合并操作。草稿连续编辑可以保留最终版本；订单提交、转账和审计事件不能按“同资源”任意覆盖。

`NetworkCallback` 提供的是网络状态信号，不保证源站可访问，也不适合在回调中执行整批同步。需要进程终止后继续存在的任务由 WorkManager 约束调度；前台页面的即时刷新可以独立发起，但仍要写回同一个本地数据源。

Outbox 记录应按协议需求保存资源标识、操作类型、幂等键、期望服务端版本、请求数据、状态、尝试次数、下次允许尝试时间、创建与更新时间、最近错误分类。请求数据是否允许持久化、是否需要加密、保留多久，都要纳入隐私设计。冲突检测、乐观更新和服务端合并策略详见 24.7。

## 执行检查清单

- 压缩协商：没有手动覆盖 `Accept-Encoding` 后又依赖透明解压；服务端按编码返回不同表示时发送正确的 `Vary`。
- 压缩选型：Protocol Buffers 不被当成压缩格式；文本、媒体、加密内容和小响应分别测量。
- 解码防护：限制解码后大小、集合数量和解析深度；主线程不执行大型解码或解析。
- 内存缓存：容量按字节等真实成本计算；缓存项可被淘汰，业务对象没有只存在于内存缓存。
- 磁盘缓存：`cacheDir` 数据允许随时缺失；使用相对路径；OkHttp 使用独占子目录。
- HTTP 指令：区分 `no-cache`、`no-store`、`private` 与 `s-maxage`；正确处理 `Vary` 和验证器。
- 账号隔离：敏感响应不存储；多账号缓存分区；退出登录时清除所属数据；缓存键和日志不包含原始凭据。
- 一致性：写后按资源关系失效；同键刷新合并；文件原子替换；损坏条目可删除并重新获取。
- 离线同步：本地数据源是上层读取入口；业务写入与 Outbox 在同一事务；Worker 使用持久队列、网络约束、幂等与可分类重试。

## 参考与验证

- [Android Developers · App-specific storage](https://developer.android.com/training/data-storage/app-specific)
- [Android Developers · StorageManager API reference](https://developer.android.com/reference/android/os/storage/StorageManager)
- [Android Developers · Network access optimization](https://developer.android.com/develop/connectivity/network-ops/network-access-optimization)
- [Android Developers · Offline-first architecture](https://developer.android.com/topic/architecture/data-layer/offline-first)
- [OkHttp 5.3.0 · BridgeInterceptor.kt](https://github.com/square/okhttp/blob/parent-5.3.0/okhttp/src/commonJvmAndroid/kotlin/okhttp3/internal/http/BridgeInterceptor.kt)
- [OkHttp 5.3.0 · CompressionInterceptor.kt](https://github.com/square/okhttp/blob/parent-5.3.0/okhttp/src/commonJvmAndroid/kotlin/okhttp3/CompressionInterceptor.kt)
- [OkHttp 5.3.0 · BrotliInterceptor.kt](https://github.com/square/okhttp/blob/parent-5.3.0/okhttp-brotli/src/main/kotlin/okhttp3/brotli/BrotliInterceptor.kt)
- [OkHttp 5.3.0 · Cache.kt](https://github.com/square/okhttp/blob/parent-5.3.0/okhttp/src/commonJvmAndroid/kotlin/okhttp3/Cache.kt)
- [OkHttp 5.3.0 · CacheStrategy.kt](https://github.com/square/okhttp/blob/parent-5.3.0/okhttp/src/commonJvmAndroid/kotlin/okhttp3/internal/cache/CacheStrategy.kt)
- [RFC 9110 · HTTP Semantics](https://www.rfc-editor.org/rfc/rfc9110.html)
- [RFC 9111 · HTTP Caching](https://www.rfc-editor.org/rfc/rfc9111.html)
- [AOSP android-17.0.0_r1 · Context.java](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/content/Context.java)
- [AOSP android-17.0.0_r1 · StorageManager.java](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/os/storage/StorageManager.java)
