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
related_chapters: ["24.4", "24.7", "12.2"]
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

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 请求 / 响应数据压缩（gzip / brotli）
- 🔹 多级缓存设计：内存 / 磁盘 / 网络
- 🔹 缓存失效策略与一致性
- 🔹 离线数据同步

### 扩展（可选深入）

- 🔸 （待扩展）

<!-- outline-end -->

## 为什么要了解数据压缩与缓存策略

网络慢不一定要从连接层解决。24.4 已经讲过连接池、DNS 和弱网调度，12.2 也讲过一次 HTTP 请求的耗时拆分。App 侧还会遇到另一类更贴近业务的数据问题：同一份数据能不能少传、能不能少解析、能不能复用已有结果、离线时能不能继续读。

压缩和缓存的收益都来自一次少做一点工作。压缩减少传输字节，缓存减少网络、磁盘、序列化和 UI 等待。代价也很直接：压缩会吃 CPU，缓存会吃内存和存储，还会引入过期、一致性和隐私边界。工程上不要把“加缓存”当成默认答案，先确认这份数据是否会被重复访问、过期成本有多高、命中率能不能被量化。

## 请求 / 响应数据压缩（gzip / brotli）

HTTP 压缩由客户端和服务端共同决定。客户端通过 `Accept-Encoding` 声明可接收的编码，服务端用 `Content-Encoding` 标明响应体使用的编码。RFC 9110 把 `gzip` 定义为标准内容编码；Brotli 对文本类响应通常有更高压缩率，但需要客户端和服务端同时支持。

在 Android App 里，响应压缩通常交给网络库处理，不要在业务层手动包一层解压逻辑。OkHttp 5 的 `CompressionInterceptor` 文档说明，它会生成类似 `Accept-Encoding: br, gzip` 的请求头，并根据响应编码做透明解压；`okhttp-brotli` 的 `BrotliInterceptor` 会添加 `Accept-Encoding: br`，并处理 `Content-Encoding: br` 响应。

压缩选型按数据形态判断：

- 文本响应：JSON、HTML、XML、GraphQL 这类重复字段多的文本适合 gzip / brotli。服务端需要同时返回正确的 `Content-Encoding` 和 `Vary: Accept-Encoding`，否则 CDN 或中间缓存可能把某个编码版本误发给不支持的客户端。
- 已压缩资源：JPEG、WebP、AVIF、MP4、ZIP、protobuf 里已经压缩过的大字段，二次 gzip 收益很低，还会增加 CPU 和耗电。图片和视频应优先从编码格式、尺寸、码率、分片下载等方向处理，详见 24.5 和 12.2 节。
- 小响应：几十到几百字节的响应不适合强行压缩。压缩头、字典初始化和解压 CPU 可能抵消传输收益。
- 请求体：客户端上传压缩需要服务端明确支持请求 `Content-Encoding`。日志、埋点批量上报、大 JSON 上传可以评估压缩；普通表单、小 POST 请求不建议默认压缩。

压缩上线前要记录四个指标：原始字节数、线上传输字节数、解压耗时、端到端请求耗时。只看压缩率容易误判，低端机上的解压 CPU 占用、主线程上的解压或解析、重试放大的流量，都会把省下的网络时间还回去。

## 多级缓存设计：内存 / 磁盘 / 网络

缓存要分层设计，因为每一层解决的问题不同。内存缓存服务于当前进程内的重复访问；磁盘缓存服务于进程重启和离线读取；HTTP 缓存服务于标准协议下的网络复用；数据库或文件缓存服务于业务可控的数据状态。

| 层级 | 常见载体 | 适合缓存的数据 | 淘汰依据 | 主要风险 |
|------|----------|----------------|----------|----------|
| 内存缓存 | `LruCache`、图片库内存层、进程内 Map | Bitmap、解析后的列表项、短生命周期配置 | 容量、最近访问、业务热度 | 占用 Java 堆，低端机容易诱发 GC 或 OOM |
| 磁盘缓存 | `Context.getCacheDir()`、`getExternalCacheDir()`、图片库磁盘层 | 图片、接口响应快照、预取文件 | 存储配额、最近访问时间、业务分组 | 系统可随时清理，不能当持久数据源 |
| HTTP 缓存 | OkHttp `Cache`、CDN、代理缓存 | 带 `Cache-Control` / `ETag` / `Last-Modified` 的 GET 响应 | RFC 9111 freshness 与 revalidation | 服务端头配置错误会导致过期数据 |
| 业务缓存 | Room、DataStore、文件索引 | 用户可见数据、离线数据、同步状态 | 业务版本、用户、租户、分页游标、服务端版本 | 一致性和冲突处理成本高 |

AOSP `Context.getCacheDir()` 文档明确写到，系统会在设备空间不足时自动删除该目录文件，并且建议 App 控制在 `StorageManager.getCacheQuotaBytes()` 返回的配额以下；`StorageManager` 还提供 `setCacheBehaviorGroup()` 和 `setCacheBehaviorTombstone()`，用于把一组互相依赖的缓存文件按组处理，或在系统清理时保留零长度墓碑文件。

这段代码展示 OkHttp 磁盘 HTTP 缓存的最小接入方式。这里需要确认两点：缓存目录放在 `cacheDir`，容量有明确上限。

```kotlin
val httpCache = Cache(
    directory = File(application.cacheDir, "http_cache"),
    maxSize = 50L * 1024L * 1024L,
)

val client = OkHttpClient.Builder()
    .cache(httpCache)
    .build()
```

OkHttp 文档把缓存命中分为直接命中、未命中和条件命中。条件命中会向服务端发起验证请求，如果服务端返回 `304 Not Modified`，客户端继续使用本地响应体，只更新响应元数据。缓存命中率要接入埋点；只有缓存层代码，不代表线上有有效命中。可以按“命中次数 / 读取次数”记录图片、接口响应、Room 查询、预取列表四类指标。命中率低时，从访问模式查起：一次性大图、临时活动页、短期热榜，可能会挤掉首页头像、会话列表、配置项这类更高复用价值的数据。

## 缓存失效策略与一致性

缓存失效不要只靠固定时间。固定 TTL 容易在两端同时出问题：时间太短，命中率上不去；时间太长，用户读到过期数据。更稳的做法是把协议、业务版本和用户动作拆开处理。

HTTP 层使用服务端头做主判断：

- `Cache-Control: max-age=...` 决定响应在多长时间内仍然新鲜。
- `ETag` 配合 `If-None-Match` 做实体标签验证，适合内容版本可以被服务端稳定标识的接口。
- `Last-Modified` 配合 `If-Modified-Since` 做时间验证，精度和可靠性弱于 `ETag`，但兼容性好。
- `no-store` 用于禁止存储，适合令牌、隐私数据、一次性凭证这类不该落盘的数据。

RFC 9111 规定，缓存可以用新鲜度和验证机制判断存储响应是否可复用；验证请求中应带上已有的实体标签，`ETag` 优先级高于只依赖修改时间。

业务层要把缓存键设计清楚。一个安全的缓存键通常至少包含接口名、用户 ID、租户或环境、参数摘要、分页游标、数据版本。对多账号 App，缺少用户维度会串数据；对灰度接口，缺少实验分组会串策略；对分页接口，缺少游标会把不同页覆盖到同一份缓存里。

写操作发生后，缓存失效要跟着业务语义走：

- 用户改资料：用户详情缓存、个人页摘要、会话头像都要被标记过期，不能只清当前接口。
- 用户点赞或收藏：本地列表可以先更新计数和状态，再把远端确认结果写回；失败时要能回滚或标记待同步。
- 服务端配置变更：配置类数据应有版本号，客户端启动时先读本地版本，再按版本决定是否拉取。
- 批量预取：预取数据要有来源和过期时间，避免把用户主动访问产生的高价值缓存淘汰掉。

缓存一致性的边界要写进代码注释或数据模型。`cacheDir` 下的数据可能被系统删除，业务代码读取时必须能处理文件不存在；Room 里的业务缓存不能因为“离线可读”就跳过 schema 迁移；HTTP 缓存不能缓存带隐私的 `Authorization` 响应，除非服务端明确给出可缓存策略并做了用户隔离。

## 离线数据同步

离线能力不等于把所有接口结果落盘。Android Developers 的离线优先文档把本地数据源放在 UI 和网络之间：UI 读取本地数据，仓库负责和网络数据源同步；网络不可用时，本地数据源可能落后于服务端，网络恢复后再同步。

离线同步在这里作为缓存边界处理，冲突解决和乐观更新详见 24.7 节。

```text
UI
 ↓ 读取 Flow / suspend 查询
Repository
 ↓ 先读本地数据源，再触发刷新
Room / DataStore / 文件缓存
 ↓ 后台任务同步
Network API
```

读路径和写路径要分开设计：

- 读路径：界面优先读本地数据源；缓存为空或过期时触发刷新；弱网下展示旧数据时要给 UI 一个状态，例如 `stale=true` 或 `lastSyncedAt`。
- 写路径：用户动作先写本地待同步队列，再由后台任务发送；服务端确认后写入最终状态；失败时保留错误码、重试次数和下一次重试时间。
- 调度路径：周期同步、约束网络类型、充电状态、指数退避重试，交给 WorkManager 这类持久后台任务；网络连通性变化只负责唤醒，不要在回调里直接跑大量同步逻辑。
- 合并路径：同一资源的多次本地写入要能合并，例如连续修改草稿、批量点赞、重复上报日志，避免网络恢复后一口气打爆服务端。

Android 的网络优化文档建议把可预取的数据集中传输，减少无线电被频繁唤醒的次数；也建议在发起请求前检查连接状态，网络不可用时把请求延后。

离线同步的失败处理要能回到用户动作。缓存层只能回答“本地有什么”，不能回答“这次写入有没有被服务端接受”。待同步表至少记录资源 ID、操作类型、幂等键、payload 摘要、创建时间、重试次数、上次错误。没有这些字段，线上排查只能看到“数据不一致”，很难还原是哪一次写入卡住。

## 执行检查清单

- 压缩：记录压缩前后字节数、解压耗时、端到端耗时；小响应和已压缩资源不默认压缩。
- 内存缓存：给 `LruCache` 设置按字节计算的容量，低端机按 `ActivityManager.getMemoryClass()` 或图片库推荐值收敛上限。
- 磁盘缓存：放在 `cacheDir` 的数据必须允许丢失；业务持久数据放 Room、DataStore 或 app-specific files，不要混进临时缓存目录。
- HTTP 缓存：只缓存 GET 和明确可缓存响应；让服务端提供 `Cache-Control`、`ETag` 或 `Last-Modified`。
- 业务缓存：缓存键包含用户、租户、参数、版本；写操作后按资源维度失效。
- 离线同步：本地读、后台写、可重试、可合并、可观测；冲突策略交给 24.7 的离线优先架构处理。

## 参考与验证

- [Android Developers · App-specific storage](https://developer.android.com/training/data-storage/app-specific)
- [Android Developers · Network access optimization](https://developer.android.com/develop/connectivity/network-ops/network-access-optimization)
- [Android Developers · Offline-first architecture](https://developer.android.com/topic/architecture/data-layer/offline-first)
- [OkHttp · Caching](https://square.github.io/okhttp/features/caching/)
- [OkHttp 5.x · CompressionInterceptor](https://square.github.io/okhttp/5.x/okhttp/okhttp3/-compression-interceptor/)
- [OkHttp Brotli · BrotliInterceptor](https://square.github.io/okhttp/5.x/okhttp-brotli/okhttp3.brotli/-brotli-interceptor/)
- [RFC 9110 · HTTP Semantics](https://www.rfc-editor.org/rfc/rfc9110.html)
- [RFC 9111 · HTTP Caching](https://www.rfc-editor.org/rfc/rfc9111.html)
- [AOSP android-17.0.0_r1 · Context.java](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/content/Context.java)
- [AOSP android-17.0.0_r1 · StorageManager.java](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/os/storage/StorageManager.java)
