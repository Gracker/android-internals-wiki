---
title: "Firebase Performance"
chapter: "19"
section: "19.14"
status: finalized
applicable_versions: "Android 8 (API 26) - Android 17 (API 37)"
last_verified: "2026-08-14"
last_verified_against: "Firebase Performance official docs updated through 2026-08-13, Google Maven metadata, Firebase Android BoM 34.17.0, firebase-perf 22.0.6 AAR and sources"
confidence: high
tags: [apm]
related_chapters: ["19.0", "19.9"]
sources:
  - type: official
    path: "https://firebase.google.com/docs/perf-mon"
  - type: official
    path: "https://firebase.google.com/docs/perf-mon/get-started-android"
  - type: official
    path: "https://firebase.google.com/docs/perf-mon/troubleshooting"
  - type: official
    path: "https://firebase.google.com/docs/perf-mon/network-traces"
  - type: official
    path: "https://firebase.google.com/docs/perf-mon/screen-traces"
  - type: official
    path: "https://firebase.google.com/docs/perf-mon/custom-code-traces?platform=android"
  - type: official
    path: "https://firebase.google.com/docs/perf-mon/custom-url-patterns"
  - type: official
    path: "https://firebase.google.com/docs/perf-mon/alerts"
  - type: official
    path: "https://firebase.google.com/docs/perf-mon/bigquery-export"
  - type: official
    path: "https://dl.google.com/dl/android/maven2/com/google/firebase/firebase-bom/maven-metadata.xml"
  - type: official
    path: "https://dl.google.com/dl/android/maven2/com/google/firebase/firebase-perf/maven-metadata.xml"
  - type: official
    path: "https://dl.google.com/dl/android/maven2/com/google/firebase/perf-plugin/maven-metadata.xml"
  - type: official
    path: "https://dl.google.com/dl/android/maven2/com/google/gms/google-services/maven-metadata.xml"
pipeline_stage: "ready-to-publish"
task6_state: reviewed
task9_state: "reviewed"
task2b_state: fixed
---
# Firebase Performance

## Firebase Performance 的定位

Firebase Performance Monitoring 是 Firebase 提供的托管型性能监控服务：数据接收、存储和控制台由 Firebase 运营，团队只需在应用中接入 SDK，无需自行部署采集服务器。它会采集启动、前后台、屏幕渲染和部分 HTTP/S 请求，也允许应用补充业务 trace。控制台按版本、设备、国家或地区等维度聚合数据。

它适合中小团队快速建立基础性能看板（汇总关键指标的 dashboard），也可以补充成熟监控体系，用来观察各版本的长期变化。它不提供自托管采集服务，端侧还会采样和限流，控制台展示也达不到秒级。因此，Firebase Performance 无法单独承担实时故障发现、还原单次请求的完整过程、解释每一帧为何变慢，或诊断 native（C/C++ 等本地代码）问题。

截至 2026 年 8 月 14 日，当前 Firebase 构建版本如下：

| 组件 | 版本 | 说明 |
| --- | --- | --- |
| Firebase Android BoM | `34.17.0` | 统一 Firebase Android 库版本 |
| `firebase-perf` | `22.0.6` | BoM 对应的 Performance SDK |
| Performance Gradle plugin | `2.0.2` | 网络请求和 `@AddTrace` 字节码插桩 |
| Google services plugin | `4.5.0` | 处理 `google-services.json` |

BoM（Bill of Materials）用于让一组 Firebase 库采用彼此兼容的版本。`firebase-perf:22.0.6` 的 AAR（Android Archive 库包）声明最低支持 API 23；本文内容按 Android 8（API 26）到 Android 17（API 37）复核。Firebase Android BoM 从 `34.0.0` 起不再包含独立 KTX module（Kotlin 扩展构件），这些扩展 API 已并入主 module，依赖仍写 `firebase-perf`。

## 数据模型：trace、metric、attribute

Firebase Performance 用 trace 表示一段被计时的执行区间，用 metric 表示数值指标，用 attribute 表示便于筛选的键值标签。自动 trace 和 custom trace 都带有 duration 等内建 metric；custom trace 还能记录自定义 metric 与 attribute。Network request trace 还会保存 URL pattern（把相似 URL 归为一组的匹配规则）、HTTP method、status code、payload size 和 Content-Type 等网络字段。

| 对象 | 含义 | 例子 | 使用建议 |
| --- | --- | --- | --- |
| trace | 一段被计时的执行区间 | `_app_start`、`home_first_feed` | 名称固定，不拼动态值 |
| metric | trace 中的整数计数或内建耗时 | duration、`item_count`、`retry_count` | 用数值表达次数或数量 |
| attribute | 用于过滤和分组的键值标签 | `entry=cold_start`、`result=success` | 只放可选值少且固定的枚举，不放 user id |
| network request trace | 一次被捕获的 HTTP/S 请求 | `GET api.example.com/v1/items/**` | 用 URL pattern 聚合动态路径 |

metric 适合记录条目数、重试次数等整数；trace duration 由 `start()` 到 `stop()` 自动计算。attribute 用于筛选和分组。用户 id、订单号、完整搜索词等字段可能产生大量不同取值，这类高基数字段会把样本切成许多小组；它们还可能属于 PII（Personally Identifiable Information，可识别个人的信息），不应交给 Performance Monitoring。

这套模型擅长回答“哪个版本变慢”“哪类设备更慢”“哪条业务路径分布异常”，但不能还原一次故障的完整调用栈。

## 构建接入：插件与运行库分工

Performance Gradle plugin 与运行时 SDK 负责不同工作。这里的字节码插桩，是指插件在构建时修改编译产物，自动插入计时和采集调用：

- `com.google.firebase.firebase-perf` 在构建期对受支持的网络库和 `@AddTrace` 做字节码插桩。
- `firebase-perf` 在进程中记录、采样、暂存并上传性能事件。
- `com.google.gms.google-services` 读取 `google-services.json`，把 Firebase 项目配置转换成 Android resource（应用资源）。

下面的 Kotlin DSL 示例保留了 2026 年 7 月可用的 BoM `34.16.0`。新接入或本次升级时，应把示例中的这一项改成当前版本 `34.17.0`；两版 BoM 都会选择 `firebase-perf:22.0.6`，另外两个 Gradle plugin 版本不变：

```kotlin
plugins {
    id("com.android.application") version "<项目使用的 AGP 版本>" apply false
    id("com.google.gms.google-services") version "4.5.0" apply false
    id("com.google.firebase.firebase-perf") version "2.0.2" apply false
}

// app/build.gradle.kts
plugins {
    id("com.android.application")
    id("com.google.gms.google-services")
    id("com.google.firebase.firebase-perf")
}

dependencies {
    implementation(platform("com.google.firebase:firebase-bom:34.16.0"))
    implementation("com.google.firebase:firebase-perf")
}
```

代码中的 AGP 指 Android Gradle Plugin，其版本沿用项目现有配置。BoM 只管理 Firebase 库版本，不管理 Gradle plugin 版本，因此两个 plugin 的版本仍要单独声明。使用 version catalog（版本目录）或根构建脚本时，可以采用等价写法。

### 构建插桩和数据采集不是同一个开关

团队经常只关闭运行时采集，却仍让 debug 构建执行字节码插桩。构建期和运行期是两套开关，需要分开配置：

| 控制项 | 作用时机 | 结果 |
| --- | --- | --- |
| `FirebasePerfExtension.setInstrumentationEnabled(false)` | 指定 variant 的构建期 | 不对该 variant（如 debug、release）执行自动网络和 `@AddTrace` 插桩 |
| Gradle property `firebasePerformanceInstrumentationEnabled=false` | 整次构建 | 全局关闭 Performance 插桩；适合 CI（持续集成）参数或临时诊断 |
| `firebase_performance_collection_enabled=false` | 应用运行期 | 默认不采集；之后可由 `setPerformanceCollectionEnabled(true)` 改变 |
| `firebase_performance_collection_deactivated=true` | 应用运行期 | 强制停用并覆盖 enabled；只有删除该 Manifest 项并重新发版才能恢复 |

下例通过 Android Manifest 元数据把运行时采集默认关闭，待用户同意隐私政策，或分阶段启用策略选中该设备后再开启：

```xml
<application>
    <meta-data
        android:name="firebase_performance_collection_enabled"
        android:value="false" />
</application>
```

这段 Manifest 配置不会自动关闭构建插桩。若 debug variant 不需要插桩，还要在构建配置中调用 `FirebasePerfExtension.setInstrumentationEnabled(false)`；若只想停止采集和上传，则无需关闭插桩。

Firebase 没有“debug 构建默认关闭”的通用规则。可采用这样的发布策略：debug variant 明确关闭插桩与采集，内部测试包只对少量受控设备启用，release 再按产品政策开放。接入清单还应覆盖 Firebase IAM（Identity and Access Management，身份与权限管理）、BigQuery 数据仓库权限、服务可用地区、数据保留说明、用户同意机制和隐私政策。Google Analytics 权限不属于 Performance Monitoring 的基本接入条件。

> 多进程应用要特别留意：官方只支持主进程中的 Performance Monitoring。独立 `:remote`、`:push` 等远程进程不会自动获得与主进程相同的采集能力；需要观察这些进程时，仍要保留应用自己的多进程监控。

## 自动采集能力与版本边界

自动采集覆盖的是 SDK 明确识别的生命周期和网络调用，不等于应用发生的每一个性能事件。

| 能力 | 采集方式 | 稳妥边界 | 局限 |
| --- | --- | --- | --- |
| App start | 自动 | 记录 Firebase SDK 定义的启动区间 | 不是进程 fork 到首帧，也不是完整首屏 |
| Foreground / background | 自动 | 依据进程生命周期记录会话区间 | 不等同于业务页面停留 |
| Screen rendering | 自动 | Activity；SDK `20.1.0+` 增加 Fragment | 固定 60 Hz 阈值，缺少逐帧业务状态 |
| HTTP/S request | 自动 + 手工 | 自动覆盖受支持的 Java/Kotlin 网络库调用 | Cronet、native 或自研栈需要手工记录 |
| Custom trace | 手工或 `@AddTrace` | 业务阶段、解码、查询等代码区间 | 需要设计稳定字段，`@AddTrace` 不能附加自定义数据 |

Android 17 / API 37 没有一套单独的 Firebase Performance 统计规则。这里以 SDK `22.0.6` 的官方文档和源码为准；跨版本比较时，也要记录 SDK 版本和采样策略是否改变，避免把采集方式的变化误判为应用性能变化。

## App start：不要把 `_app_start` 当成完整启动

在 `firebase-perf:22.0.6` 中，SDK 内部把这条 trace 记为 `_as`，控制台显示为 `_app_start`。计时使用单调时钟 `elapsedRealtime`：它按设备启动后的经过时间递增，不受用户修改时间或网络校时影响。它的区间是：

1. 起点：Firebase 首个类的早期 class-load（类加载）近似时间。
2. 终点：第一个 Activity 的 `onResume()` 回调时间。
3. 子区间：到首次 `onCreate()`、`onStart()` 和 `onResume()` 的几个阶段耗时。

这个区间没有覆盖 Firebase 初始化之前的全部进程时间，也没有等待第一帧或首屏内容可用。API 24 以后，源码会读取 `Process.getStartElapsedRealtime()`，但该时间用于实验性 TTID trace 及 `process start → class load` 子区间，不能把它写成稳定 `_app_start` 的起点。这里的 process start 接近系统从 Zygote fork（派生）应用进程的时刻；`Process.getStartUptimeMillis()` 也不是稳定 `_app_start` 使用的时钟。

SDK 会过滤后台触发的进程启动。`22.0.6` 修复了 Android 14（API 34）及以上版本的判断：在 Firebase 的早期初始化阶段调用 `ActivityManager.getMyMemoryState()`，只有 `IMPORTANCE_FOREGROUND` 才允许生成 `_app_start`。这个变化同样覆盖 Android 17。

`_app_start` 可用于比较版本趋势，不能替代应用定义的 TTID（Time to Initial Display，首次画面出现时间）和 TTFD（Time to Full Display，完整内容可用时间）。若“启动完成”要求首页骨架绘制、首批数据展示或页面可交互，需要另建 custom trace，并用 Macrobenchmark（Jetpack 的端侧性能基准工具）或 Perfetto 系统 trace 校验各阶段。

## Screen rendering：指标是“屏幕实例比例”

Firebase 自动 screen trace 的时间窗口取决于页面类型：

- Activity：`onActivityStarted()` 到 `onActivityStopped()`。
- Fragment：`onFragmentResumed()` 到 `onFragmentPaused()`，需要 SDK `20.1.0+`。

Fragment 不会独立读取一条 FrameMetrics 流。FrameMetrics 是 Android 提供的 `Window` 帧耗时数据；SDK 从宿主 Activity 的 `Window` 收集它，再计算 Fragment 生命周期区间内的计数差值。多个 Fragment 重叠、生命周期管理不规范，或使用单 Activity 的 Compose Navigation，都会让页面级结果更难解释。

SDK `22.0.6` 对单帧的分类仍是：

- slow frame：耗时 `> 16 ms`；
- frozen frame：耗时 `> 700 ms`。

官方文档明确指出，自动 screen rendering trace 按固定 60 Hz 阈值计算。在 60 Hz 屏幕上，每个刷新周期约为 16.67 ms；在 90/120 Hz 设备上，刷新周期缩短为约 11.11/8.33 ms。一帧即使错过设备的真实刷新周期，也可能没有超过 16 ms，因此 Firebase 可能低估高刷新率设备上的卡顿。

控制台中的汇总百分比也不是“慢帧数除以总帧数”：

- slow rendering：slow frame 超过该 screen instance 总帧数 50% 的 screen instance 占比；
- frozen frames：frozen frame 超过该 screen instance 总帧数 0.1% 的 screen instance 占比。

这里的 screen instance 指一次 Activity 或 Fragment 展示区间，不是一帧。自动 screen trace 不能附加 custom metric 或 custom attribute。单 Activity + Compose 应用若要区分具体 route（导航目的地）、滚动阶段或业务动作，应使用 JankStats（Jetpack 的逐帧卡顿统计库）记录状态，并按需增加 custom trace。

## 自定义 trace：字段规则与服务端边界

custom trace 的命名要保持长期稳定，也要符合控制台和后端的公开约束：

| 项目 | 公开约束 | 工程建议 |
| --- | --- | --- |
| trace name | 最长 100 个字符；无首尾空格；不能以 `_` 开头 | 使用固定 snake_case（小写单词以下划线连接） |
| metric name | 最长 100 个字符；无首尾空格；不能以 `_` 开头 | 表达可累加的整数计数 |
| trace metrics | 每条 custom trace 最多 32 个，duration 也计入 | 只保留诊断需要的少量指标 |
| attribute | 每条 custom trace 最多 5 个 | 采用取值少且固定的枚举 |
| attribute key | 文档口径最长 32 个字符，只使用英文字母与 `_` | 遵循文档口径，不依赖 SDK 的宽松校验 |
| attribute value | 最长 100 个字符 | 不写 PII、认证 token 或自由文本 |

这里有一处容易误读的源码差异：SDK `22.0.6` 的端侧校验允许 attribute key 最长 40 个字符，也允许首字母后的数字，并拒绝 `firebase_`、`google_`、`ga_` 前缀；当前 Android 官方文档给出的服务端规则更严格，只接受最长 32 个字符以及字母、下划线。生产代码应采用两套规则共同接受的范围。通过端侧校验，只能说明本地 SDK 接受了该字段，不能保证服务端和控制台会长期保留它。

| 场景 | trace 名 | metric 名 | attribute | 不要写 |
| --- | --- | --- | --- | --- |
| 首屏首批内容 | `home_first_feed` | `item_count`、`payload_kb` | `entry=cold_start` | 完整接口 URL、user id |
| 登录流程 | `login_request` | `retry_count` | `result=success` 或 `result=fail` | 手机号、邮箱 |
| 图片解码 | `image_decode_list` | `image_count`、`decode_ms` | `source=disk` 或 `source=network` | 图片 hash（哈希值）、CDN（内容分发网络）签名 |
| 数据库查询 | `db_query_user` | `row_count`、`query_ms` | `source=room` | SQL 原文、主键 id |

下面的示例用主 module 中的 Kotlin `trace` 扩展保证异常路径也会调用 `stop()`：

```kotlin
import com.google.firebase.Firebase
import com.google.firebase.perf.performance
import com.google.firebase.perf.trace

suspend fun loadFirstFeed(): List<FeedItem> {
    return Firebase.performance.newTrace("home_first_feed").trace {
        putAttribute("entry", "cold_start")

        val items = repository.loadFirstPage()
        putMetric("item_count", items.size.toLong())
        items
    }
}
```

`trace {}` 内部使用 `try/finally` 停止 trace，因此抛出异常或协程被取消时也能执行 `stop()`。若项目不用该扩展，应显式写 `start()`、`try/finally` 和 `stop()`，避免 trace 一直没有结束时间。`@AddTrace` 适合简单方法计时，但它不能附加 custom metric 和 attribute；需要业务字段时，应使用显式 API。

## 网络请求聚合和 URL pattern

自动 network request trace 记录请求 URL、HTTP method、response code、request/response payload size、Content-Type 和 duration。官方默认把 response code `100..399` 计为成功；duration 从发出请求算到完整接收响应。这个总耗时不能继续拆成 DNS（域名解析）、TCP 建连、TLS 加密握手、服务器处理和重试等阶段。

Performance Gradle plugin `2.0.2` 的插桩类覆盖以下调用：

- OkHttp 3.x 的 `Call.execute()` / `enqueue()`；
- `HttpURLConnection` / `HttpsURLConnection`；
- Apache HttpClient。

官方文档明确列的是 OkHttp **3.x.x**。较新 OkHttp 即使保持二进制兼容，也只表示已经编译的调用通常还能找到相同方法，不代表 Performance plugin 一定识别这些调用。升级网络库或插件后，应发送测试请求，并用 SDK debug log 核对是否采集成功。Cronet（基于 Chromium 的网络引擎）、native 网络栈、自研协议栈以及插件未识别的封装，需要手工创建 `HttpMetric`。

### 手工记录不受支持的网络栈

下面的示例为 Cronet 或自研网络 client 的一次请求创建独立 `HttpMetric`：

```kotlin
import com.google.firebase.Firebase
import com.google.firebase.perf.FirebasePerformance
import com.google.firebase.perf.performance

suspend fun executeWithMetric(request: ApiRequest): ApiResponse {
    val metric = Firebase.performance.newHttpMetric(
        "https://api.example.com/v1/items",
        FirebasePerformance.HttpMethod.GET,
    )
    metric.start()

    return try {
        val response = cronetClient.execute(request)
        metric.setHttpResponseCode(response.code)
        metric.setResponsePayloadSize(response.bodySizeBytes)
        response.contentType?.let(metric::setResponseContentType)
        response
    } finally {
        metric.stop()
    }
}
```

`HttpMetric` 不保证线程安全，一次请求应创建一个实例，不要放进 singleton（全局共享的单例对象）反复使用。异常分支也要执行 `stop()`。若网络 client 能区分 DNS、TLS、timeout 等错误，可在应用自己的少量固定分类字段或错误监控中记录；`HttpMetric` 没有通用的 network-stage 字段。

### URL pattern 要在控制台中统一分组

SDK 在写入 URL 时会移除 user-info（如 `user:password@host` 中的账号信息）和 query 参数（`?key=value`），并把长度截到 2000 个字符。这只是上报前的保护措施，凭证仍不应放在 URL 中；自定义 attribute 也不能写 PII、token、签名或自由文本。

控制台会生成 automatic URL pattern，也允许创建 custom URL pattern。这里的 segment 指 URL path 中由 `/` 分隔的一段；pattern 语法不接受 `{id}` 这种参数写法：

- 字面量 segment：`api.example.com/v1/items/list`
- `*`：匹配一个 path segment
- `**`：匹配 path 的剩余部分，只能放在 pattern 末尾

例如，`/api/item/10001/detail` 与 `/api/item/10002/detail` 应定义为：

```text
api.example.com/api/item/*/detail
```

这个 pattern 只归并一个动态 segment。若其后还可能出现任意数量的 path segment，才使用末尾 `**`。

同一请求只映射到一个 URL pattern：Firebase 先尝试 custom pattern，再使用 automatic pattern；多个 custom pattern 同时命中时，从 path 左侧开始，按字面量、`*`、`**` 的顺序选择更具体的一条。新增 pattern 不会追溯改写历史数据，而且新规则最多可能等待 12 小时才出现聚合结果。当前限制是每个 app 最多 400 个 custom pattern、每个 domain 最多 100 个。设计时应按同一类 API 资源归并，不要为每个具体 URL 单独创建 pattern。

payload size 通常依赖 `Content-Length` 等 HTTP header（请求或响应头）信息；该 header 缺失或填写不准时，控制台数值也可能不准，不能把它当作线路实际传输字节数。缺少 Content-Type 可以被接受，格式非法的 Content-Type 则可能让请求不显示。长时间未完成、没有执行 `stop()` 或未被插桩命中的请求，也不会形成可用样本。

排查采集时，可在测试构建的 Manifest 临时设置 `firebase_performance_logcat_enabled=true`，再到 Logcat（Android 设备日志）检查 `FirebasePerformance` debug log 中是否出现已完成的 trace/request 和对应 URL。验证完成后移除该开关，避免增加生产日志。

## 采样、时效和排查边界

SDK 记录到事件，不代表控制台会保存设备上发生的每个事件。采样会按一定比例选择设备或事件，限流则限制一个时间窗口内可发送或接收的数量；两者都可能减少最终样本。设备侧还会批量发送，服务端也要继续处理。

| SDK 情况 | 控制台时效 | 适合做什么 |
| --- | --- | --- |
| Android SDK `19.0.10+` 或 BoM `26.1.0+` | SDK 大约每 30 秒批量发送；控制台通常几分钟内出现 | 分阶段发布观察、当日回归、版本趋势 |
| 旧 SDK | 大约 36 小时延迟 | 次日复盘、长期趋势 |

`firebase-perf:22.0.6` 已进入 near real-time（近实时）处理路径，这里的含义是数据通常在采集后几分钟内显示。“几分钟”不能当作严格的实时 SLA（Service Level Agreement，服务时效约定）；设备离线、省电策略、初始化失败、上传失败或服务端处理都可能继续推迟数据。

官方 troubleshooting 文档给出的设备限流口径是：code trace 和 network request trace 合计每台设备每 10 分钟最多发送 300 个事件。此外，SDK 会通过 Firebase Remote Config（远程配置服务）取得针对该 app 的动态采样率，随机选择哪些设备发送 trace；服务端仍可能丢弃一部分已收到的事件。启用 BigQuery 集成的项目会获得较高的 network request trace 数量上限，但仍不等于全量采集。因此：

- 高频轮询和图片请求不会保证逐条保留；
- 小流量分阶段发布可能因为样本不足而看不出变化；
- 控制台分布只能代表被捕获并被接受的事件。

Performance alerts 也有样本门槛。App start、custom trace、network 和 screen rendering 告警需要过去一小时至少 100 个样本；这里的样本是 Firebase 已记录并用于相应指标的事件。低流量版本不能把“没有告警”等同于“没有问题”。

### BigQuery 导出能补分析能力，不能取消采样

Firebase Performance 支持把 captured events（已被采集并接受的事件）导出到 BigQuery，每一行对应一个 performance event。BigQuery 是 Google Cloud 的托管分析型数据仓库，适合使用 SQL 做长期留存和跨版本分析。导出数据已经经过端侧采样与限流，不是设备上全部事件的原始副本。

首次启用导出后，初始数据传播最多可能需要 48 小时；之后的常规同步任务通常会在安排执行后的 24 小时内完成。BigQuery 提供分析和持有数据副本的能力，不提供自托管采集入口；字段 schema（表结构和字段定义）也由 Firebase 制定。

## 和 JankStats、FrameMetrics、Android Vitals 的分工

这些工具都会出现渲染或稳定性指标，但观察对象不同：

| 工具 | 主要样本 | 长处 | 不足 |
| --- | --- | --- | --- |
| Firebase Performance | Activity/Fragment screen instance、network、custom trace | 接入快，可看版本、设备和地区分布 | 固定 60 Hz 阈值；缺少逐帧状态 |
| JankStats | 逐帧 jank（卡顿帧）判定 + `StateInfo` 状态标签 | 能关联 route、滚动和业务状态 | 需要自行聚合、存储和上报 |
| FrameMetrics | `Window` 级帧阶段耗时 | 能观察 layout、draw、同步和 GPU 等阶段 | API 24+；数据较底层，需要自行解释 |
| Android Vitals | Google Play 分发人群的慢帧、ANR 等质量数据 | 适合设定发布质量门槛和评估用户影响 | 只覆盖 Play 样本，业务上下文少 |

Firebase 的 16/700 ms、screen instance 占比与 Android Vitals 的用户或会话统计口径不能直接比较。看到百分比变化时，应先确认分母（计算该百分比所基于的样本集合）、刷新率、版本分布和采样窗口，再决定是否用 JankStats、FrameMetrics、Macrobenchmark 或 Perfetto 继续定位。

## 使用建议

### 适合采用

- 希望用较低接入成本观察启动、页面和网络的版本趋势；
- 产品运行地区可以稳定访问 Firebase 服务；
- 能接受托管服务、采样、分钟级控制台延迟和 Firebase 定义的字段 schema；
- 愿意为首页可用、登录、图片解码、数据库查询等关键路径设计少量 custom trace。

### 需要配合其他工具

- 秒级错误告警：使用业务错误码、日志或实时 APM（Application Performance Monitoring，应用性能监控）系统；
- 逐帧页面状态：使用 JankStats；
- 启动与渲染阶段：使用 Macrobenchmark、FrameMetrics 和 Perfetto；
- ANR（Application Not Responding，应用无响应）和 native 故障信息：使用 Android Vitals、系统 trace、tombstone（native 崩溃转储文件）与内部采集；
- 自托管或完整样本回溯：选择满足数据所有权要求的自建或商业方案。

### 接入与验收清单

- [ ] 锁定 BoM、Performance plugin 和 Google services plugin 版本；当前复核值分别为 `34.17.0`、`2.0.2`、`4.5.0`。
- [ ] 分别配置构建插桩开关与运行时采集开关。
- [ ] 确认只依赖主进程数据，没有把远程进程误算为已覆盖。
- [ ] 在测试构建核对 `_app_start`、screen trace 和受支持网络请求。
- [ ] 为 Cronet、native 或自研网络 client 增加独立 `HttpMetric`。
- [ ] 按资源族设计 URL pattern，禁止动态 id、query 和 token 进入维度。
- [ ] custom trace 的 attribute key 遵守最长 32 字符的公开文档规则，attribute 不含 PII。
- [ ] 把采样、展示延迟和 100 样本告警门槛写进看板说明。
- [ ] 按需启用 BigQuery，并确认导出对象是 captured events，不是全部端侧事件。
- [ ] Android 17 发布前用真实 90/120 Hz 设备检查 Firebase 固定 60 Hz 口径的偏差。

### 从 Firebase 迁移时应保留的字段

迁移到自建或商业 APM 时，不要只复制 trace 名。至少保留这些分析字段的定义：

- app id、version name、version code、build type、distribution channel；
- device model、OS/API level、country/region、network type；
- trace name、start time、duration、metric、取值少且固定的 attribute；
- URL pattern、HTTP method、status code、payload size、Content-Type；
- screen name、total/slow/frozen frame count 及其阈值；
- SDK/plugin version、采样率、限流规则、客户端采集时间和服务端接收时间；
- 错误类型、重试次数、服务端 request id 的脱敏规则，以及它与服务端日志的关联方式。

应把字段名、单位、计算公式、分母和采样规则写成可版本化的数据字典，也就是一份说明每个字段含义和统计方式的规范。缺少这份规范时，迁移前后的曲线即使同名，也可能没有可比性。

## 源码核对点

| 结论 | `firebase-perf:22.0.6` 对应实现 |
| --- | --- |
| `_app_start` 的起点和终点 | `AppStartTrace.logAppStartTrace()` 使用 Firebase class-load timer 到首次 `onResume()` |
| API 24+ 进程起点 | `Process.getStartElapsedRealtime()` 进入实验性 TTID trace，不是稳定 `_app_start` 起点 |
| API 34+ 后台启动过滤 | `AppStartCause` 读取 `ActivityManager.getMyMemoryState()` 的 importance（进程重要性等级） |
| 帧阈值 | `Constants.SLOW_FRAME_TIME=16`、`FROZEN_FRAME_TIME=700` |
| Fragment 统计方式 | `FragmentStateMonitor` 配合 Activity `FrameMetricsRecorder` 计算区间差值 |
| attribute 端侧校验 | `PerfMetricValidator.validateAttribute()`；其宽松边界不能替代公开文档约束 |
| URL 脱敏 | `NetworkRequestMetricBuilder.setUrl()` 调用 `Utils.stripSensitiveInfo()` |

## 参考资料

- [Firebase Performance Monitoring for Android：接入与当前版本](https://firebase.google.com/docs/perf-mon/get-started-android)
- [Custom code traces](https://firebase.google.com/docs/perf-mon/custom-code-traces?platform=android)
- [Automatic app start、foreground 和 background traces](https://firebase.google.com/docs/perf-mon/app-start-foreground-background-traces?platform=android)
- [Screen rendering performance data](https://firebase.google.com/docs/perf-mon/screen-traces?platform=android)
- [Network request performance data](https://firebase.google.com/docs/perf-mon/network-traces?platform=android)
- [Custom URL patterns](https://firebase.google.com/docs/perf-mon/custom-url-patterns)
- [Troubleshooting and FAQ](https://firebase.google.com/docs/perf-mon/troubleshooting?platform=android)
- [Performance alerts](https://firebase.google.com/docs/perf-mon/alerts)
- [Disable Performance Monitoring](https://firebase.google.com/docs/perf-mon/disable-sdk?platform=android)
- [Export Performance Monitoring data to BigQuery](https://firebase.google.com/docs/perf-mon/bigquery-export)
- [Firebase Android SDK release notes](https://firebase.google.com/support/release-notes/android)
- [Firebase Android BoM 版本元数据](https://dl.google.com/dl/android/maven2/com/google/firebase/firebase-bom/maven-metadata.xml)
- [`firebase-perf` 版本元数据](https://dl.google.com/dl/android/maven2/com/google/firebase/firebase-perf/maven-metadata.xml)
- [Performance Gradle plugin 版本元数据](https://dl.google.com/dl/android/maven2/com/google/firebase/perf-plugin/maven-metadata.xml)
- [Google services plugin 版本元数据](https://dl.google.com/dl/android/maven2/com/google/gms/google-services/maven-metadata.xml)
- [`firebase-perf:22.0.6` source package](https://dl.google.com/dl/android/maven2/com/google/firebase/firebase-perf/22.0.6/firebase-perf-22.0.6-sources.jar)
- [Firebase Android SDK：Performance 源码](https://github.com/firebase/firebase-android-sdk/tree/main/firebase-perf/src/main/java/com/google/firebase/perf)
