---
title: "Firebase Performance"
deepseek_polish_state: done
last_deepseek_polish_at: '2026-05-25'
chapter: "19"
section: "19.14"
status: finalized
drafted_date: "2026-04-24"
drafted_by: "codex"
applicable_versions: "Android 8 (API 26) - Android 17 (API 37)"
last_verified: "2026-04-25"
last_verified_against: "Firebase Performance custom-code-traces / screen-traces / troubleshooting docs, Firebase Android SDK 20.1.0+ Fragment screen rendering boundary, external review 2026-04-25"
confidence: medium
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
pipeline_stage: "ready-to-publish"
task6_state: reviewed
task6_result: pass-light-edit
task9_state: "reviewed"
task2b_state: fixed
task2b_result: fixed
task9_result: "pass-tech-review"
task9_reviewed_by: "openclaw-task9"
task9_reviewed_date: "2026-05-08"
last_task9_at: "2026-05-08T02:30:38+08:00"
reviewed_by: openclaw-task9
reviewed_date: "2026-05-08"
last_task2b_at: "2026-05-07T23:47:13+08:00"
repaired_date: "2026-04-25"
repaired_by: openclaw-task2b
last_task6_at: "2026-05-08T02:09:46+08:00"
last_task6_audit: 2026-07-05
task6_review_notes: "2026-05-08 01:08 task6 revisiting-review: pass-light-edit。复核 Task2B 回炉修正后的写作层，修复 6 处 L1/L2 文风与可读性问题；保留 task9_result=pending 等待 Task9 复审。 | 2026-05-08 02:09 task6 revisiting-review: pass-light-edit。修复 YAML 引号、重复验证句和 8 处 L1/L2 表达问题；Task9 仍为 pending，未自动晋升。"
task9_review_notes: "2026-05-08 01:32 Task9 deep-review: needs-rework。P0 2 / P1 1 / P2 1。 | 2026-05-08 01:40 Task2B rework: P0 attribute key 32->40 + reserved prefix；P0 Cronet 改为 HttpMetric manual trace；P1 EventListener 删除无证据断言 | 2026-05-08 02 Task9 deep-review: pass-tech-review。P0 0 / P1 0 / P2 1。Task6 已通过且 queue 无 pending，自动晋升 finalized。"
last_task9_audit: "2026-07-10"
last_task9_audit_log: "logs/deep-review/2026-07-10-18-audit.md"
last_task9_audit_at: "2026-07-10T18:28:45+08:00"
last_task9_audit_result: "pass-audit-p2-only"
task9_audit_notes: "2026-07-10 Task9 idle audit: pass-audit-p2-only。P0 0 / P1 0 / P2 2；复核 Firebase Performance 官方 get-started/troubleshooting/network/screen-traces/custom-code-traces 文档、Firebase Android SDK Trace/HttpMetric/AppStartTrace 源码与 Android 17 Process API；未发现需写入 queue.json 的源码错误或版本越界。P2：_app_start 起点表述可在下次编辑时从平台 uptime API 收紧到 SDK 当前 elapsedRealtime 源码口径；screen rendering 60Hz 假设仍建议补正文。"
deepseek_cn_review_state: done
last_deepseek_cn_review_at: 2026-07-14
---
# Firebase Performance

## Firebase Performance 的定位

Firebase Performance Monitoring 是 Firebase 提供的托管型性能监控服务。它用较少的接入工作采集启动、前后台、屏幕渲染和部分 HTTP/S 请求，还允许应用补充业务 trace。控制台负责版本、设备、国家或地区等维度的聚合。

它适合中小团队快速建立基础性能看板，也适合作为成熟监控体系中的趋势观测层。它不提供自托管采集服务，端侧还有采样和限流，控制台展示也不是秒级。因此，Firebase Performance 不能单独负责实时故障发现、单次请求复原、逐帧归因或 native 现场诊断。

截至 2026 年 7 月，采用以下 Firebase 构建锚点：

| 组件 | 版本 | 说明 |
| --- | --- | --- |
| Firebase Android BoM | `34.16.0` | 统一 Firebase Android 库版本 |
| `firebase-perf` | `22.0.6` | BoM 对应的 Performance SDK |
| Performance Gradle plugin | `2.0.2` | 网络请求和 `@AddTrace` 字节码插桩 |
| Google services plugin | `4.5.0` | 处理 `google-services.json` |

`firebase-perf:22.0.6` 的 AAR 最低支持 API 23。以下内容按 Android 8（API 26）到 Android 17（API 37）复核。Firebase Android BoM 从 `34.0.0` 起不再包含独立 KTX module；Kotlin 扩展 API 已并入主 module，依赖仍写 `firebase-perf`。

## 数据模型：trace、metric、attribute

Firebase Performance 的基本时间区间是 trace。自动 trace 和 custom trace 都带有内建 metric；custom trace 还能记录自定义 metric 与 attribute。Network request trace 则保存 URL pattern、HTTP method、status code、payload size 和 Content-Type 等网络字段。

| 对象 | 含义 | 例子 | 使用建议 |
| --- | --- | --- | --- |
| trace | 一段被计时的执行窗口 | `_app_start`、`home_first_feed` | 名称固定，不拼动态值 |
| metric | trace 中的整数计数或内建耗时 | duration、`item_count`、`retry_count` | 用数值表达次数或数量 |
| attribute | 过滤维度 | `entry=cold_start`、`result=success` | 只放低基数枚举上下文，不放 user id |
| network request trace | 一次被捕获的 HTTP/S 请求 | `GET api.example.com/v1/items/**` | 用 URL pattern 聚合动态路径 |

metric 适合记录条目数、重试次数等整数；trace duration 由 `start()` 到 `stop()` 自动计算。attribute 用于筛选和分组。用户 id、订单号、完整搜索词等高基数或可识别用户的信息既会破坏统计，也不应交给 Performance Monitoring。

这套模型擅长回答“哪个版本变慢”“哪类设备更慢”“哪条业务路径分布异常”，但不能还原一次故障的完整调用栈。

## 构建接入：插件与运行库分工

Performance Gradle plugin 与运行时 SDK 负责不同工作：

- `com.google.firebase.firebase-perf` 在构建期对受支持的网络库和 `@AddTrace` 做字节码插桩。
- `firebase-perf` 在进程中记录、采样、暂存并上传性能事件。
- `com.google.gms.google-services` 读取 `google-services.json`，把 Firebase 项目配置生成到 Android resources。

下面的 Kotlin DSL 示例锁定上述版本：

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

BoM 只管理 Firebase 库版本，不管理 Gradle plugin 版本。版本目录或根构建脚本可以采用等价写法。

### 构建插桩和数据采集不是同一个开关

团队经常只关闭运行时采集，却仍让 debug 构建执行字节码插桩。两类开关要分开配置：

| 控制项 | 作用时机 | 结果 |
| --- | --- | --- |
| `FirebasePerfExtension.setInstrumentationEnabled(false)` | 指定 variant 的构建期 | 不对该 variant 执行自动网络和 `@AddTrace` 插桩 |
| Gradle property `firebasePerformanceInstrumentationEnabled=false` | 整次构建 | 全局关闭 Performance 插桩；适合 CI 参数或临时诊断 |
| `firebase_performance_collection_enabled=false` | 应用运行期 | 默认不采集；之后可由 `setPerformanceCollectionEnabled(true)` 改变 |
| `firebase_performance_collection_deactivated=true` | 应用运行期 | 强制停用并覆盖 enabled；只有删除该 Manifest 项并重新发版才能恢复 |

下例把运行时采集默认关闭，待用户同意隐私政策或命中灰度策略后再开启：

```xml
<application>
    <meta-data
        android:name="firebase_performance_collection_enabled"
        android:value="false" />
</application>
```

这个配置不会自动关闭构建插桩。若 debug variant 不需要插桩，还要在构建配置中调用 `FirebasePerfExtension.setInstrumentationEnabled(false)`；若只想停止上传，则无需关闭插桩。

Firebase 并没有“debug 构建默认关闭”的通用规则。更稳妥的发布策略是：debug variant 明确关闭插桩与采集，内部测试包只采少量受控设备，release 再按产品政策启用。接入清单还应覆盖 Firebase IAM、BigQuery 权限、服务可用地区、数据保留说明、用户同意机制和隐私政策。Google Analytics 权限不是 Performance Monitoring 的基本接入条件。

> 多进程应用要特别留意：官方只支持主进程中的 Performance Monitoring。独立 `:remote`、`:push` 或其他进程的数据不能按主进程能力推断，应用自己的多进程监控仍需保留。

## 自动采集能力与版本边界

自动采集覆盖的是 SDK 明确识别的生命周期和网络调用，不等于应用发生的每一个性能事件。

| 能力 | 采集方式 | 稳妥边界 | 局限 |
| --- | --- | --- | --- |
| App start | 自动 | 记录 Firebase SDK 定义的启动区间 | 不是进程 fork 到首帧，也不是完整首屏 |
| Foreground / background | 自动 | 依据进程生命周期记录会话区间 | 不等同于业务页面停留 |
| Screen rendering | 自动 | Activity；SDK `20.1.0+` 增加 Fragment | 固定 60 Hz 阈值，缺少逐帧业务状态 |
| HTTP/S request | 自动 + 手工 | 自动覆盖受支持的 JVM 网络调用 | Cronet、native 或自研栈需要手工记录 |
| Custom trace | 手工或 `@AddTrace` | 业务阶段、解码、查询等代码区间 | 需要设计稳定字段，`@AddTrace` 不能附加自定义数据 |

Android 17 / API 37 没有一套单独的 Firebase Performance 语义。这里以 SDK `22.0.6` 的官方文档和源码为准；跨版本比较时，SDK 升级、采样策略变化也要作为实验变量。

## App start：不要把 `_app_start` 当成完整启动

在 `firebase-perf:22.0.6` 中，稳定上报的 `_as`（控制台显示为 `_app_start`）使用单调时钟 `elapsedRealtime`。它的区间是：

1. 起点：Firebase 的早期 class-load 时间。
2. 终点：第一个 Activity 的 `onResume()` 回调时间。
3. 子区间：首次 `onCreate()`、`onStart()` 和 `onResume()` 的相对耗时。

因此，它没有覆盖 Firebase 初始化之前的全部进程时间，也没有等待第一帧或首屏内容可用。API 24 以后，源码会读取 `Process.getStartElapsedRealtime()`，但该时间用于实验性 TTID trace 及 `process start → class load` 子区间，不能把它写成稳定 `_app_start` 的起点。`Process.getStartUptimeMillis()` 更不是此处使用的时钟。

SDK 会过滤后台触发的进程启动。`22.0.6` 修复了 Android 14（API 34）及以上版本的判断：在 Firebase 的早期初始化阶段调用 `ActivityManager.getMyMemoryState()`，只有 `IMPORTANCE_FOREGROUND` 才允许生成 `_app_start`。这个变化同样覆盖 Android 17。

`_app_start` 可用于比较版本趋势，不能替代应用定义的 TTID/TTFD。若“启动完成”要求首页骨架绘制、首批数据展示或可交互，需要另建 custom trace，并用 Macrobenchmark 或 Perfetto 校验端侧阶段。

## Screen rendering：指标是“屏幕实例比例”

Firebase 自动 screen trace 的时间窗口取决于页面类型：

- Activity：`onActivityStarted()` 到 `onActivityStopped()`。
- Fragment：`onFragmentResumed()` 到 `onFragmentPaused()`，需要 SDK `20.1.0+`。

Fragment 不是独立读取一条 FrameMetrics 流。SDK 从宿主 Activity 的 `Window` 收集 FrameMetrics，在 Fragment 生命周期区间计算计数差值。多个 Fragment 重叠、生命周期管理不规范或单 Activity Compose Navigation 都会影响解释。

SDK `22.0.6` 对单帧的分类仍是：

- slow frame：耗时 `> 16 ms`；
- frozen frame：耗时 `> 700 ms`。

官方文档明确指出，自动 screen rendering trace 按固定 60 Hz 屏幕阈值计算。在 90/120 Hz 设备上，一帧虽然错过真实刷新周期，却可能没有超过 16 ms，所以 Firebase 可能低估相对于设备刷新率的卡顿。

控制台中的汇总百分比也不是“慢帧数除以总帧数”：

- slow rendering：slow frame 超过该 screen instance 总帧数 50% 的 screen instance 占比；
- frozen frames：frozen frame 超过该 screen instance 总帧数 0.1% 的 screen instance 占比。

这里的 screen instance 可以理解为一次 Activity 或 Fragment 展示区间。自动 screen trace 不能附加 custom metric 或 custom attribute。单 Activity + Compose 应用若要区分具体 route、滚动阶段或业务动作，应使用 JankStats 记录逐帧状态，并按需增加 custom trace。

## 自定义 trace：字段规则和安全子集

custom trace 的命名要保持长期稳定，也要符合控制台和后端的公开约束：

| 项目 | 公开约束 | 工程建议 |
| --- | --- | --- |
| trace name | 最长 100 个字符；无首尾空格；不能以 `_` 开头 | 使用固定 snake_case |
| metric name | 最长 100 个字符；无首尾空格；不能以 `_` 开头 | 表达可累加的整数计数 |
| trace metrics | 每条 custom trace 最多 32 个，duration 也计入 | 只保留诊断需要的少量指标 |
| attribute | 每条 custom trace 最多 5 个 | 采用低基数枚举 |
| attribute key | 文档口径最长 32 个字符，只使用英文字母与 `_` | 遵循文档口径，不依赖 SDK 的宽松校验 |
| attribute value | 最长 100 个字符 | 不写 PII、token 或自由文本 |

这里存在一个容易误读的源码差异：SDK `22.0.6` 的端侧校验允许 attribute key 最长 40 个字符，也允许首字母后的数字，并拒绝 `firebase_`、`google_`、`ga_` 前缀；当前 Android 官方文档给出的后端契约更窄，即 32 个字符和字母/下划线。生产代码应遵循 32 个字符的文档安全子集，否则端侧通过不代表后端和控制台会长期接受。

| 场景 | trace 名 | metric 名 | attribute | 不要写 |
| --- | --- | --- | --- | --- |
| 首屏首批内容 | `home_first_feed` | `item_count`、`payload_kb` | `entry=cold_start` | 完整接口 URL、user id |
| 登录流程 | `login_request` | `retry_count` | `result=success|fail` | 手机号、邮箱 |
| 图片解码 | `image_decode_list` | `image_count`、`decode_ms` | `source=disk|network` | 图片 hash、CDN 签名 |
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

`trace {}` 内部使用 `try/finally` 停止 trace。若项目不用该扩展，应显式写 `start()`、`try/finally` 和 `stop()`，避免异常或取消让 trace 长时间不结束。`@AddTrace` 适合简单方法计时，但它不能附加 custom metric 和 attribute，关键业务路径更适合显式 API。

## 网络请求聚合和 URL pattern

自动 network request trace 记录请求 URL、HTTP method、response code、request/response payload size、Content-Type 和 duration。官方对成功率的定义是 response code `100..399` 视为成功；duration 从发出请求算到完整接收响应。它不能拆分 DNS、TCP、TLS、服务器处理和重试阶段。

Performance Gradle plugin `2.0.2` 的插桩类覆盖以下调用：

- OkHttp 3.x 的 `Call.execute()` / `enqueue()`；
- `HttpURLConnection` / `HttpsURLConnection`；
- Apache HttpClient。

官方文档明确列的是 OkHttp **3.x.x**。即使较新 OkHttp 版本可能保持二进制兼容，也不要仅凭依赖存在就假定自动采集有效；升级网络库或插件后，应通过测试请求和 SDK debug log 核对。Cronet、native 网络栈、自研协议栈以及未命中的封装需要手工 `HttpMetric`。

### 手工记录不受支持的网络栈

下面的示例为 Cronet 或自研 client 创建一次独立的 `HttpMetric`：

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

`HttpMetric` 不是线程安全对象，一次请求创建一个实例，不要放进 singleton 复用。异常分支也要 `stop()`；若 client 能区分 DNS、TLS、timeout 等错误，可在应用自己的低基数字段或错误监控中记录，因为 `HttpMetric` 没有通用的 network-stage 字段。

### URL pattern 要在控制台中归一化

SDK 在写入 URL 时会移除 user-info 和 query 参数，并把长度截到 2000 个字符。不过，凭证本来就不应放在 URL 中；自定义 attribute 也不能写 PII、token、签名或自由文本。

控制台会生成自动 URL pattern，也允许创建 custom URL pattern。pattern 语法不是 `{id}` 占位符：

- 字面量 segment：`api.example.com/v1/items/list`
- `*`：匹配一个 path segment
- `**`：匹配 path 的剩余部分，只能放在 pattern 末尾

例如，`/api/item/10001/detail` 与 `/api/item/10002/detail` 应定义为：

```text
api.example.com/api/item/*/detail
```

这个 pattern 只归并单个动态 segment。若后面还有任意层级，才使用末尾 `**`。

同一请求只映射到一个 URL pattern：custom pattern 先于 automatic pattern；多个 custom pattern 同时命中时，按 path 从左到右选择更具体的一条。新增 pattern 不会追溯改写历史数据；修改分组规则后，应从变更时间点比较。当前限制是每个 app 最多 400 个 custom pattern、每个 domain 最多 100 个，设计时应按 API 资源族归并，不要为每个 endpoint 实例建 pattern。

payload size 通常依赖 `Content-Length` 等可用信息，不一定等于线上传输字节数。缺少 Content-Type 可以被接受，非法 Content-Type 则可能让请求不显示。长时间未完成、没有执行 `stop()` 或未被插桩命中的请求，也不会形成可用样本。

排查采集时，可在测试构建的 Manifest 临时设置 `firebase_performance_logcat_enabled=true`，再检查 `FirebasePerformance` debug log 中是否出现完成的 trace/request 和对应 URL。验证完成后移除该开关，避免生产日志噪声。

## 采样、时效和排查边界

SDK 记录到事件，不代表控制台保存了设备上发生的每个事件。设备侧会批量发送，服务端还会执行采样和处理。

| SDK 情况 | 控制台时效 | 适合做什么 |
| --- | --- | --- |
| Android SDK `19.0.10+` 或 BoM `26.1.0+` | SDK 大约每 30 秒批量发送；控制台通常几分钟内出现 | 灰度观察、当日回归、版本趋势 |
| 旧 SDK | 大约 36 小时延迟 | 次日复盘、长期趋势 |

`firebase-perf:22.0.6` 已进入 near real-time 路径，但“几分钟”仍不是实时 SLA。设备离线、省电策略、初始化失败、上传失败或服务端处理都可能继续推迟数据。

官方 troubleshooting 文档给出的设备限流口径是：code trace 和 network trace 合计每 10 分钟 300 个事件。SDK 还会通过 Remote Config 接收按 app/device 调整的采样设置。因此：

- 高频轮询和图片请求不会保证逐条保留；
- 小流量灰度可能因为样本不足而看不出变化；
- 控制台分布只能代表被捕获并被接受的事件。

Performance alerts 也有样本门槛。App start、custom trace、network 和 screen rendering 告警需要过去一小时至少 100 个样本；低流量版本不能把“没有告警”等同于“没有问题”。

### BigQuery 导出能补分析能力，不能取消采样

Firebase Performance 支持把 captured events 导出到 BigQuery，每一行对应一个被捕获的 performance event。它便于做自定义 SQL、长期留存和跨版本分析，但导出数据已经经过端侧采样与限流，不是设备上全部事件的原始副本。

首次启用导出后，数据出现可能需要 48 小时；日常批次通常在一天结束后的 12～24 小时完成。BigQuery 解决的是分析和持有副本的问题，不提供自托管采集入口，字段 schema 也由 Firebase 定义。

## 和 JankStats、FrameMetrics、Android Vitals 的分工

这些工具都会出现渲染或稳定性指标，但观察对象不同：

| 工具 | 主要样本 | 长处 | 不足 |
| --- | --- | --- | --- |
| Firebase Performance | Activity/Fragment screen instance、network、custom trace | 接入快，可看版本、设备和地区分布 | 固定 60 Hz 阈值；缺少逐帧状态 |
| JankStats | 逐帧 jank 判定 + `StateInfo` | 能关联 route、滚动和业务状态 | 需要自行聚合、存储和上报 |
| FrameMetrics | Window 级帧阶段耗时 | 能观察 layout/draw/sync/GPU 等阶段 | API 24+；数据较底层，需要自行解释 |
| Android Vitals | Google Play 分发人群的慢帧、ANR 等质量数据 | 适合发布质量门槛和用户影响评估 | 只覆盖 Play 样本，业务上下文少 |

Firebase 的 16/700 ms、screen instance 占比与 Android Vitals 的用户/会话口径不能直接比较。一个百分比变化，应先确认分母、刷新率、版本分布和采样窗口，再决定是否用 JankStats、FrameMetrics、Macrobenchmark 或 Perfetto 继续定位。

## 使用建议

### 适合采用

- 希望用较低接入成本观察启动、页面和网络的版本趋势；
- 产品运行地区可以稳定访问 Firebase 服务；
- 能接受托管服务、采样、分钟级控制台延迟和 Firebase 字段 schema；
- 愿意为首页可用、登录、图片解码、数据库查询等关键路径设计少量 custom trace。

### 需要配合其他工具

- 秒级错误告警：使用业务错误码、日志或实时 APM；
- 逐帧页面状态：使用 JankStats；
- 启动与渲染阶段：使用 Macrobenchmark、FrameMetrics 和 Perfetto；
- ANR/native 现场：使用 Android Vitals、系统 traces、tombstone 与内部采集；
- 自托管或完整样本回溯：选择满足数据所有权要求的自建或商业方案。

### 接入与验收清单

- [ ] 锁定 BoM、Performance plugin 和 Google services plugin 版本。
- [ ] 分别配置构建插桩开关与运行时采集开关。
- [ ] 确认只依赖主进程数据，没有把远程进程误算为已覆盖。
- [ ] 在测试构建核对 `_app_start`、screen trace 和受支持网络请求。
- [ ] 为 Cronet、native 或自研网络 client 增加独立 `HttpMetric`。
- [ ] 按资源族设计 URL pattern，禁止动态 id、query 和 token 进入维度。
- [ ] custom trace 采用 32 字符 attribute key 安全子集，attribute 不含 PII。
- [ ] 把采样、展示延迟和 100 样本告警门槛写进看板说明。
- [ ] 按需启用 BigQuery，并接受导出的是 captured events。
- [ ] Android 17 发布前用真实 90/120 Hz 设备检查 Firebase 固定 60 Hz 口径的偏差。

### 从 Firebase 迁移时应保留的字段

迁移到自建或商业 APM 时，不要只复制 trace 名。至少保留这些分析字段的定义：

- app id、version name、version code、build type、distribution channel；
- device model、OS/API level、country/region、network type；
- trace name、start time、duration、metric、低基数 attribute；
- URL pattern、HTTP method、status code、payload size、Content-Type；
- screen name、total/slow/frozen frame count 及其阈值；
- SDK/plugin version、采样率、限流规则、数据接收时间；
- 错误类型、重试次数、服务端 request id 的脱敏映射规则。

字段名、单位、分母和采样规则要形成可版本化的数据字典。否则迁移前后的曲线即使同名，也可能没有可比性。

## 源码核对点

| 结论 | `firebase-perf:22.0.6` 对应实现 |
| --- | --- |
| `_app_start` 的起点和终点 | `AppStartTrace.logAppStartTrace()` 使用 Firebase class-load timer 到首次 `onResume()` |
| API 24+ 进程起点 | `Process.getStartElapsedRealtime()` 进入实验性 TTID trace，不是稳定 `_app_start` 起点 |
| API 34+ 后台启动过滤 | `AppStartCause` 读取 `ActivityManager.getMyMemoryState()` 的 importance |
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
- [`firebase-perf:22.0.6` source package](https://dl.google.com/dl/android/maven2/com/google/firebase/firebase-perf/22.0.6/firebase-perf-22.0.6-sources.jar)
- [Firebase Android SDK：Performance 源码](https://github.com/firebase/firebase-android-sdk/tree/main/firebase-perf/src/main/java/com/google/firebase/perf)
