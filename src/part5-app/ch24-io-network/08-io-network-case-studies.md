---
title: "I/O 与网络优化案例集"
chapter: "24.8"
section: "24.8"
status: finalized
applicable_versions: "Android 10 (API 29) - Android 17 (API 37)"
last_verified: "2026-05-14"
last_verified_against: "AOSP android-35 SDK sources + Android Developers docs + OkHttp 5.x docs + Clippings 结构参考"
confidence: medium
drafted_date: "2026-05-14"
polish_count: 1
sources:
  - type: aosp
    path: "/Users/gracker/Android/sources/android-35/android/app/SharedPreferencesImpl.java"
  - type: aosp
    path: "/Users/gracker/Android/sources/android-35/android/app/QueuedWork.java"
  - type: aosp
    path: "/Users/gracker/Android/sources/android-35/android/os/StrictMode.java"
  - type: aosp
    path: "/Users/gracker/Android/sources/android-35/android/app/DownloadManager.java"
  - type: aosp
    path: "/Users/gracker/Android/sources/android-35/android/net/NetworkCapabilities.java"
  - type: official
    path: "https://developer.android.com/reference/android/content/SharedPreferences.Editor"
  - type: official
    path: "https://developer.android.com/topic/libraries/architecture/datastore"
  - type: official
    path: "https://developer.android.com/develop/connectivity/network-ops/network-access-optimization"
  - type: official
    path: "https://developer.android.com/develop/background-work/background-tasks/persistent/getting-started/define-work"
  - type: official
    path: "https://square.github.io/okhttp/features/calls/"
  - type: official
    path: "https://square.github.io/okhttp/features/events/"
  - type: official
    path: "https://square.github.io/okhttp/5.x/okhttp/okhttp3/-dispatcher/"
  - type: clippings
    path: "Clippings/Android 性能优化 - 原理：重新认识应用的速度优化.md"
  - type: clippings
    path: "Clippings/Android 性能优化 - CPU 优化（上）：合理使用线程池，提升 CPU 利用率.md"
  - type: clippings
    path: "Clippings/Android 性能优化 - 缓存优化：冷热端分离+重排序，提升缓存命中率.md"
tags: [case-study, io, network, optimization, sharedpreferences, upload-download]
related_chapters: ["24.1", "24.4", "24.6", "24.7", "25.4"]
pipeline_stage: ready-to-publish
task6_state: reviewed
task6_result: pass-light-edit
reviewed_by: openclaw-task6
reviewed_date: "2026-06-03"
last_task6_at: "2026-06-04T06:08:46+08:00"
task6_review_notes: "2026-06-03 Task6：revisiting 复审通过；L1/L2 扫描无新增正文问题；无新增 L3/L4 回炉项，转入 Task9 pending。"
task9_state: reviewed
task2b_state: fixed
last_task2a_at: "2026-05-14T13:14:00+08:00"
task9_result: auto-fixed
task9_reviewed_by: "openclaw-task9"
task9_reviewed_date: "2026-06-03"
last_task9_at: "2026-06-03T14:26:33+08:00"
last_task9_review_log: "logs/deep-review/2026-06-03-14-deep-review.md"
task2b_result: fixed
last_task2b_at: "2026-06-03T04:50:00+08:00"
last_task2b_notes: "frontmatter fallback：修复 PreferenceWriteBuffer flush 后无条件清空 pending 导致并发新增写入丢失的问题。"
task6_reviewed_date: "2026-06-03"
last_task6_review_log: "logs/review/2026-06-03-07-review.md"
last_task9_autofix_at: "2026-06-03"
task9_review_notes: "2026-06-03 Task9 14:20 auto-fixed：修正 OkHttp Dispatcher 排队时间观测口径，使用 OkHttp 5.x dispatcherQueueStart/dispatcherQueueEnd；旧版 OkHttp 需自定义队列埋点，不能用 callStart 代表出队。P0 0 / P1 0 / AUTO-FIX 1；回到 Task6 复审。"
deepseek_cn_review_state: done
last_deepseek_cn_review_at: 2026-06-13
---

# I/O 与网络优化案例集

## 为什么要了解 I/O 与网络优化案例集

三个诊断模板分别处理 SharedPreferences 生命周期 ANR、页面请求变慢和大文件传输失败。它们不是带有真实业务数据的收益报告，因此不提供虚构的毫秒数、并发数或提升比例。项目应先采集自己的基线，再填写阈值和验收目标。

平台锚点是 Android 17（API 37）/ `android-17.0.0_r1`，网络客户端以 OkHttp 5.3.0 为实现样本。每个案例都按“现象、证据、机制、修复、验证”展开：

- 现象只帮助确定排查入口，不能代替根因证据；
- 证据要能区分主线程等待、磁盘 I/O、调度排队和网络交换；
- 修复要保留失败、取消、进程终止和账号切换语义；
- 验收要在同一业务路径、设备分层与网络条件下比较。

## SharedPreferences ANR 治理实战

### 现象

页面停止、应用进入后台或服务回调结束时发生 ANR，主线程堆栈停在 `QueuedWork.waitToFinish()`。同时，`queued-work-looper` 或其他线程可能正在执行 `SharedPreferencesImpl.writeToFile()`、XML 序列化或 `FileUtils.sync()`。

看到 `apply()` 不能排除 SharedPreferences。Android 官方 API 参考明确说明，待完成的 `Editor.apply()` 会在 Activity 或 Service 的生命周期转换期间阻塞主线程，以保证持久化完成。

### Android 17 源码路径

`android-17.0.0_r1` 中有四段行为需要一起看：

- `SharedPreferencesImpl.edit()` 会调用 `awaitLoadedLocked()`；首次加载尚未完成时，连创建编辑器都可能等待。
- `apply()` 先执行 `commitToMemory()`，再把等待磁盘完成的 finisher 交给 `QueuedWork`，随后安排磁盘写入。
- `ActivityThread` 在 Activity 停止、Service 命令结束和 Service 销毁等路径调用 `QueuedWork.waitToFinish()`。
- `commit()` 等待 `writtenToDiskLatch`；在没有其他磁盘写入时，源码允许当前调用线程直接执行写文件。

`apply()` 只是把调用点与磁盘写入分开。生命周期稍后仍可能等待此前的写入，异步接口也没有向调用方报告持久化失败。

### 观测路径

排查时同时保留以下证据：

| 证据 | 观测方式 | 判断点 |
| --- | --- | --- |
| ANR 主线程 | ANR trace、bugreport | 是否停在 `QueuedWork.waitToFinish()` 或 SharedPreferences 首次加载等待 |
| 磁盘线程 | 同一时间窗口的线程 trace、Perfetto | 是否正在写 XML、同步文件或等待块设备 |
| 写入来源 | 统一存储封装 | 偏好文件、业务类别、调用线程、调用阶段、写入类型和次数 |
| 文件状态 | 应用内部诊断 | XML 大小、偏好项数量、备份文件是否存在 |
| 生命周期 | Activity、Service 与广播时序 | 写入是否集中发生在停止、销毁或广播返回前 |

不要在日志中输出原始偏好键和值。可记录经过分类的业务来源或稳定散列，并设置采样和保留期限。

StrictMode 能发现主线程上的同步磁盘访问，但无法证明某次 `apply()` 稍后是否会在 `waitToFinish()` 中等待。Android 17 的 `QueuedWork.waitToFinish()` 还会临时允许当前线程磁盘写入，因此 StrictMode 结果只能作为补充证据。

### 根因

常见根因可以互相叠加：

- 一个 XML 保存了过多数据，首次加载、复制内存映射、序列化和文件同步都变慢；
- 高频状态变化每次都调用 `apply()`，待处理写入与内存复制增多；
- 在 `onStop()`、Service 回调结束或广播返回前集中写入，随后立刻进入框架等待点；
- 在主线程调用 `commit()`，调用线程直接参与文件写入并等待结果；
- 把 JSON、大集合、日志计数或草稿放进 SharedPreferences；
- 多进程同时使用 SharedPreferences；官方文档明确说明它不支持跨进程。

### 改法

数据类型决定迁移方向：

| 数据类型 | 原问题 | 改法 |
| --- | --- | --- |
| 小型设置 | SharedPreferences 写入集中、失败不可见 | Preferences DataStore 或 Proto DataStore |
| 结构化、可查询数据 | JSON 或集合放入 XML | Room |
| 高频瞬时状态 | 每次变化都持久化 | 进程内状态；只在业务要求的检查点保存 |
| 需要确认的用户操作 | `apply()` 无失败结果 | 持久业务状态与可观察错误 |
| 跨进程数据 | SharedPreferences 不支持多进程 | ContentProvider、Room 多实例失效通知或服务进程接口 |

不要用固定时间的 debounce 伪装持久化保证。持续写入可能让 debounce 长时间不输出，进程终止还会丢失尚未提交的值。只有“中间状态可丢、保留较新值即可”的数据才允许合并，并且要写清触发与恢复规则。

下面的示例假设项目已有 Proto DataStore `Settings`，用于展示可等待持久化结果的设置更新：

```kotlin
class SettingsRepository(
    private val settingsStore: DataStore<Settings>,
) {
    val settings: Flow<Settings> = settingsStore.data

    suspend fun setExperimentEnabled(enabled: Boolean) {
        settingsStore.updateData { current ->
            current.toBuilder()
                .setExperimentEnabled(enabled)
                .build()
        }
    }
}
```

`updateData()` 执行原子读改写，并在数据持久化后完成挂起调用。DataStore 适合小型数据；需要局部更新、关系查询或较大数据集时使用 Room。迁移期间要保证同一份数据只有一个写入归属，避免 SharedPreferences 与 DataStore 双写产生顺序冲突。

### 验收

验收不使用无法公开观测的“`apply()` 完成耗时”。`apply()` 没有完成回调，除非项目已经验证了内部插桩口径，否则该数字不可得。

可以比较：

- 同一偏好文件的大小、项目数量和写入调用次数；
- 生命周期结束前后的写入来源分布；
- Perfetto 中 `queued-work-looper` 的执行与主线程等待；
- `QueuedWork.waitToFinish()` 相关 ANR 在活跃用户或会话中的归一化比例；
- 迁移前后的读取错误、持久化失败和数据回退。

测试覆盖冷启动首次读取、连续修改、立即切后台、Service 停止、进程终止、存储压力、升级迁移和多进程误用。

## 网络请求性能优化案例

### 现象

页面端到端请求变慢，而服务端记录的处理时间没有同步增长。慢请求集中出现 DNS、建连、TLS、异步调度队列、响应下载或业务解析中的一个或多个阶段。图片预取、日志和大文件还可能与交互接口争用并发与带宽。

### 观测路径

OkHttp 5.3.0 `EventListener` 能记录事件，但事件序列不是固定直线。重定向、认证和重试会让 DNS、连接、请求与响应事件在同一个 `Call` 中出现多次；复用连接时不会出现 DNS 和建连事件；双工请求还会让请求体与响应事件交错。

| 时间段 | OkHttp 事件或业务埋点 | 常见根因 |
| --- | --- | --- |
| 异步排队 | `dispatcherQueueStart` → `dispatcherQueueEnd` | 异步并发额度、单主机额度、任务混用 |
| DNS | `dnsStart` → `dnsEnd` | 解析器、网络切换、错误缓存或备用解析 |
| TCP / TLS | `connectStart`、`secureConnectStart` 及对应结束事件 | 新连接、代理、握手或路由失败 |
| 连接取得 | `connectionAcquired`，结合是否出现 DNS / connect | 连接复用、重定向或新路由 |
| 首个响应头 | 请求头或请求体结束 → `responseHeadersStart` | 上传、网络往返、网关与服务端处理 |
| 响应体消费 | `responseBodyStart` → `responseBodyEnd` / `responseFailed` | 响应大小、读取速度、提前关闭或解析背压 |
| 解析与入库 | 应用自己的解析、事务和界面状态时间 | 大对象、数据库事务或主线程工作 |

`dispatcherQueueStart` / `dispatcherQueueEnd` 只描述被排队的异步 `enqueue()` 调用。同步 `execute()` 会登记为运行中的同步调用，但不受 `maxRequests` 与 `maxRequestsPerHost` 的异步队列限制。`callStart` 也不能当成出队时间。

TTFB 需要按每次网络交换分析。无请求体、`Expect: 100-continue`、双工请求和重试的事件顺序不同，不能用一条通用减法覆盖所有请求。保留事件所属 `Call`、交换次数、URL 模板和连接标识，避免把重试阶段相加后误报为一次服务端处理。

### 根因

根因常见于以下组合：

- API、图片预取、遥测和大文件共用同一个异步 Dispatcher；
- 多个短生命周期 `OkHttpClient` 各自持有连接池，连接复用率下降；
- 只提高并发，没有同时观察服务端限流、HTTP/2 流限制与移动网络带宽；
- 手动创建多个客户端时丢失 Cookie、代理、证书固定、认证或事件监听配置；
- HTTPDNS 在 `Dns.lookup()` 中同步访问网络，甚至递归使用同一个客户端；
- 只记录总耗时，解析与数据库时间被算进网络时间。

HTTPDNS 的备用路径还要遵守系统 Private DNS、VPN、代理和网络切换边界，详见 24.4 与 24.10。缓存 IP 不能绕过 TLS 主机名校验，也不能把连接到某个 IP 解释为接口可用。

### 改法

可按任务类别设置独立异步 Dispatcher，同时从一个配置完整、长生命周期的基础客户端派生，保留共享连接池与安全配置。

下面的代码要求调用方传入已经用压测和线上观测确定的并发参数，不提供通用默认值：

```kotlin
data class AsyncRequestLimits(
    val total: Int,
    val perHost: Int,
)

fun OkHttpClient.withAsyncRequestLimits(
    limits: AsyncRequestLimits,
): OkHttpClient {
    require(limits.total > 0)
    require(limits.perHost > 0)

    val dispatcher = Dispatcher().apply {
        maxRequests = limits.total
        maxRequestsPerHost = limits.perHost
    }
    return newBuilder()
        .dispatcher(dispatcher)
        .build()
}
```

`newBuilder()` 派生的客户端继续共享基础客户端的连接池，并复制其他配置；新 Dispatcher 提供独立的异步排队额度。它不能保证带宽优先级，两个 Dispatcher 仍会争用设备网络、服务端容量和共享连接。交互 API 的资源预留要通过弱网测试验证。

`EventListener.Factory` 应在基础客户端上配置，事件记录要控制 URL、请求头和错误中的敏感信息。并发值按主机、协议、请求体大小、服务器限制、失败率和页面等待目标调整；OkHttp 默认值只能作为库行为，不能直接成为业务基线。

### 验收

验收同时看总耗时与阶段分布：

- 异步排队、DNS、建连、TLS、首个响应头与响应体消费的分位数；
- 每个 `Call` 的交换次数、重定向、重试和失败分类；
- 连接复用与新建连接数量；
- 交互 API 与批量任务各自的排队和失败；
- 响应传输字节、解码后字节和缓存命中；
- 移动网络、VPN、代理、网络切换和服务端限流场景；
- CPU、流量与电量是否因提高并发或重试而增加。

修改 Dispatcher 后还要验证同步 `execute()` 调用，因为它们不会进入这套异步配额。

## 大文件上传下载优化

### 现象

大文件任务占用连接时间长，失败后重传成本高。常见故障包括：

- 下载与交互 API 共用异步队列，页面请求长期等待；
- 上传前把整个文件读入内存；
- 网络切换或进程终止后从零开始；
- 已下载字节与远端表示不一致，却直接追加到临时文件；
- 用户选择的 `content://` URI 权限在后台任务运行前失效；
- 系统停止任务后，进度只在内存中，恢复时无法定位已确认分片。

### 选择正确的执行 API

Android 17 上应先按用户意图、持续时间和系统集成选择执行方式：

| 场景 | API 选择 | 边界 |
| --- | --- | --- |
| 页面可取消的小传输 | 页面协程与普通 HTTP 请求 | 页面离开后允许停止 |
| 系统管理的长时间 HTTP 下载 | `DownloadManager` | 系统处理 HTTP、失败重试、连接变化和重启；产品接受其通知与目标文件语义 |
| 用户发起、要求立即开始并持续显示进度的长传输 | API 34+ UIDT `JobScheduler` 任务 | 需要通知、调度时机满足可见性要求，并持久化恢复状态 |
| 后台发起、可延后且可中断的传输 | WorkManager | 约束满足后执行，不保证精确开始时间 |
| 低版本 UIDT 兼容或特殊短时任务 | 按官方选择指南评估前台服务或 WorkManager 前台模式 | 受前台服务类型、启动和执行限制 |

官方数据传输选择指南把标准 WorkManager 传输定位在短于常规执行窗口的任务。长时间 Worker 会进入前台服务与 JobScheduler 限制范围，不能因为使用 WorkManager 就忽略平台配额和停止条件。

UIDT 从 Android 14（API 34）开始提供。系统仍可能因约束失效、热状态、系统健康或低内存停止任务；用户从任务管理器停止应用时，进程可能被直接终止且不调用 `onStopJob()`。下载状态必须在传输过程中持续写入持久存储。

`NetworkType.UNMETERED` 表示非计费网络，不等于 Wi-Fi。Wi-Fi 可能计费，蜂窝网络也可能暂时或长期非计费。用户明确触发的传输和后台预取应使用不同的产品策略。

### 下载断点必须验证同一远端表示

断点记录至少包含资源标识、目标临时文件、已验证字节数、总长度、强 ETag 或其他稳定版本、校验信息和任务状态。

恢复 HTTP 下载时：

- 请求 `Range: bytes=<offset>-`，并用 `If-Range` 携带强验证器；
- 收到 `206 Partial Content` 后，验证 `Content-Range` 的起点、终点和总长度，再追加；
- 收到 `200 OK` 表示服务端发送完整表示，丢弃或重建旧临时文件，不能直接追加；
- 收到 `416 Range Not Satisfiable` 时，根据 `Content-Range` 与本地长度重新核对，不能直接宣告完成；
- 多段内容只有共享同一强验证器时才能安全组合；
- 透明内容编码会改变字节偏移，断点协议要使用稳定的编码表示，或明确发送 `Accept-Encoding: identity`。

下载完成后校验长度、摘要或签名，再以原子方式把临时文件发布为正式文件。存储空间预检查只能减少失败，写入过程仍要处理空间耗尽、介质移除和权限变化。

### 上传治理

上传前把用户选择的内容复制到应用拥有的不可变暂存文件，或通过 `ACTION_OPEN_DOCUMENT` 获取并持久化 URI 权限。即使调用 `takePersistableUriPermission()`，原文档被移动或删除后仍会失去访问；恢复代码必须处理这一情况。

OkHttp 5.3.0 已提供 `File.asRequestBody()`，会从文件源流式写入。下面的函数只构造请求，不把文件读入字节数组：

```kotlin
fun buildUploadRequest(
    endpoint: HttpUrl,
    stagedFile: File,
    mediaType: MediaType,
): Request {
    require(stagedFile.isFile)
    return Request.Builder()
        .url(endpoint)
        .post(stagedFile.asRequestBody(mediaType))
        .build()
}
```

该请求体默认可以再次读取，因此暂存文件在上传完成前必须保持路径、长度和内容不变。OkHttp 5.3.0 的 `FileDescriptor.toRequestBody()` 则明确标为 one-shot，不能假设认证、连接失败或服务端响应后还能自动重发。

需要断点上传时，客户端与服务端共同定义协议：

- 创建上传会话，得到稳定的 `uploadId`；
- 每个分片携带序号或字节范围、长度和校验值；
- 服务端原子确认已接收分片，重复分片按同一结果返回；
- 客户端持久化已确认范围，不把“已发送”当成“已确认”；
- 完成操作使用幂等语义，并由服务端校验完整长度与摘要；
- 分片并发、大小和重试按网络、服务端限制与设备 I/O 测量，不采用通用固定值。

进度回调要按时间或进度变化节流，不能每写少量字节就切换到主线程。取消应停止网络读取，并保存已经由服务端确认的状态。

### 验收

大文件验证以恢复正确性为主，再比较吞吐和资源：

| 场景 | 验收点 |
| --- | --- |
| 完整传输 | 长度、摘要、正式文件发布和服务端完成状态一致 |
| 网络切换 | 旧连接失败后按已确认断点恢复，不重复发布资源 |
| 远端文件变化 | `If-Range` 失配后重建临时文件，不拼接不同版本 |
| 进程终止 | 重启后从持久状态恢复，未确认分片可安全重发 |
| 任务停止 | WorkManager、UIDT 或用户取消后资源及时释放 |
| 存储不足 | 临时文件清理可控，错误能引导用户处理 |
| URI 失效 | 权限丢失、文档移动或删除后进入可恢复错误 |
| 多任务并发 | 交互 API 的排队、失败和耗时没有异常恶化 |
| 计费网络 | 遵守用户选择、后台策略和系统网络能力 |

Android 17 的 `NetworkCapabilities` 源码说明，`NET_CAPABILITY_NOT_METERED` 比 Wi-Fi 传输类型更适合判断计费属性；同步查询得到的能力快照可能立即过期。前台界面用 `NetworkCallback` 接收变化，后台任务使用 WorkManager 或 JobScheduler 约束，并在传输过程中继续处理网络失效。

## 案例复盘清单

### SharedPreferences

- ANR 主线程与磁盘线程证据位于同一时间窗口；
- 首次加载、`apply()` finisher、`commit()` 和生命周期等待分开判断；
- 新数据优先使用 DataStore 或 Room；
- 合并写只用于允许丢中间态的数据，没有固定 debounce 伪装持久化；
- 验收采用归一化 ANR 和可观测写入数据。

### 网络请求

- 每次 `Call` 能区分多个网络交换；
- 异步排队与同步 `execute()` 采用不同口径；
- 连接复用通过事件缺失与 `connectionAcquired` 共同判断；
- Dispatcher 参数来自项目自己的基线，独立队列不被描述成带宽优先级；
- HTTPDNS 保留系统网络策略、TLS 主机名与失败处理。

### 大文件

- 执行 API 与用户意图、传输时长和平台版本匹配；
- 下载断点使用强验证器，正确处理 `206`、`200` 与 `416`；
- 上传输入可在后台继续访问，内容在重试期间保持不变；
- 已发送与已确认状态分开持久化；
- 进程终止、任务停止、网络切换和账号退出均可恢复或清理。

## 参考与验证

- [AOSP android-17.0.0_r1 · SharedPreferencesImpl.java](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/app/SharedPreferencesImpl.java)
- [AOSP android-17.0.0_r1 · QueuedWork.java](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/app/QueuedWork.java)
- [AOSP android-17.0.0_r1 · ActivityThread.java](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/app/ActivityThread.java)
- [AOSP android-17.0.0_r1 · DownloadManager.java](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/app/DownloadManager.java)
- [AOSP android-17.0.0_r1 · NetworkCapabilities.java](https://android.googlesource.com/platform/packages/modules/Connectivity/+/refs/tags/android-17.0.0_r1/framework/src/android/net/NetworkCapabilities.java)
- [Android Developers · SharedPreferences](https://developer.android.com/reference/android/content/SharedPreferences)
- [Android Developers · DataStore](https://developer.android.com/topic/libraries/architecture/datastore)
- [Android Developers · Data transfer background task options](https://developer.android.com/develop/background-work/background-tasks/data-transfer-options)
- [Android Developers · User-initiated data transfer](https://developer.android.com/develop/background-work/background-tasks/uidt)
- [Android Developers · DownloadManager](https://developer.android.com/reference/android/app/DownloadManager)
- [Android Developers · Define work requests](https://developer.android.com/develop/background-work/background-tasks/persistent/getting-started/define-work)
- [Android Developers · Read network state](https://developer.android.com/develop/connectivity/network-ops/reading-network-state)
- [Android Developers · Access documents and other files](https://developer.android.com/training/data-storage/shared/documents-files)
- [OkHttp 5.3.0 · EventListener.kt](https://github.com/lysine-dev/okhttp/blob/parent-5.3.0/okhttp/src/commonJvmAndroid/kotlin/okhttp3/EventListener.kt)
- [OkHttp 5.3.0 · Dispatcher.kt](https://github.com/lysine-dev/okhttp/blob/parent-5.3.0/okhttp/src/commonJvmAndroid/kotlin/okhttp3/Dispatcher.kt)
- [OkHttp 5.3.0 · RequestBody.kt](https://github.com/lysine-dev/okhttp/blob/parent-5.3.0/okhttp/src/commonJvmAndroid/kotlin/okhttp3/RequestBody.kt)
- [RFC 9110 · HTTP Semantics](https://www.rfc-editor.org/rfc/rfc9110.html)
