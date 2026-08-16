---

title: Measure
chapter: '19'
section: '19.07'
status: "finalized"
applicable_versions: Android 5.0 (API 21) - Android 17 (API 37); Measure Android SDK 0.19.0
last_verified: '2026-08-14'
last_verified_against: measure-sh android-v0.19.0 tag + Maven Central and Gradle Plugin Portal metadata + main 7501820c8e6f8bfc8a512061e1d2504b465e0466 + current Measure docs + Android 17 API reference/AOSP + 0.19.0 AAR ELF headers
confidence: medium
tags: 
- apm
related_chapters: 
- '19.0'
sources:
- type: historical-reference
  path: https://raw.githubusercontent.com/measure-sh/measure/main/docs/hosting/README.md
- type: reference
  path: https://github.com/measure-sh/measure/tree/8a189ea1e9728105773c1c81fb6cc8797e6b2d15
- type: reference
  path: https://github.com/measure-sh/measure/tree/7501820c8e6f8bfc8a512061e1d2504b465e0466
- type: reference
  path: https://github.com/measure-sh/measure/releases/tag/android-v0.19.0
- type: artifact-metadata
  path: https://repo.maven.apache.org/maven2/sh/measure/measure-android/maven-metadata.xml
- type: artifact
  path: https://repo.maven.apache.org/maven2/sh/measure/measure-android/0.19.0/measure-android-0.19.0.aar
- type: artifact-metadata
  path: https://plugins.gradle.org/m2/sh/measure/android/gradle/sh.measure.android.gradle.gradle.plugin/maven-metadata.xml
- type: reference
  path: https://github.com/measure-sh/measure/blob/8a189ea1e9728105773c1c81fb6cc8797e6b2d15/android/measure-android/measure/build.gradle.kts
- type: reference
  path: https://github.com/measure-sh/measure/blob/8a189ea1e9728105773c1c81fb6cc8797e6b2d15/android/measure-android/measure/src/main/java/sh/measure/android/config/DynamicConfig.kt
- type: reference
  path: https://github.com/measure-sh/measure/blob/8a189ea1e9728105773c1c81fb6cc8797e6b2d15/android/measure-android/measure/src/main/jni/anr_handler.c
- type: reference
  path: https://github.com/measure-sh/measure/blob/8a189ea1e9728105773c1c81fb6cc8797e6b2d15/android/measure-android/measure/src/main/CMakeLists.txt
- type: reference
  path: https://github.com/measure-sh/measure/blob/8a189ea1e9728105773c1c81fb6cc8797e6b2d15/android/measure-android/measure/src/main/java/sh/measure/android/performance/MemoryReader.kt
- type: reference
  path: https://github.com/measure-sh/measure/blob/8a189ea1e9728105773c1c81fb6cc8797e6b2d15/android/measure-android/measure/src/main/java/sh/measure/android/profiling/ProfileCollector.kt
- type: reference
  path: https://github.com/measure-sh/measure/blob/8a189ea1e9728105773c1c81fb6cc8797e6b2d15/android/measure-android/measure/src/main/java/sh/measure/android/Measure.kt
- type: reference
  path: https://github.com/measure-sh/measure/blob/8a189ea1e9728105773c1c81fb6cc8797e6b2d15/self-host/compose.prod.yml
- type: reference
  path: https://github.com/measure-sh/measure/blob/7501820c8e6f8bfc8a512061e1d2504b465e0466/self-host/compose.yml
- type: reference
  path: https://github.com/measure-sh/measure/blob/7501820c8e6f8bfc8a512061e1d2504b465e0466/android/measure-gradle-plugin/src/main/kotlin/sh/measure/asm/NavigationTransformer.kt
- type: reference
  path: https://measure.sh/docs/sdk-integration-guide
- type: reference
  path: https://measure.sh/docs/getting-started/android
- type: reference
  path: https://measure.sh/docs/getting-started/kotlin-multiplatform
- type: reference
  path: https://measure.sh/docs/features/feature-session-timelines
- type: historical-reference
  path: https://measure.sh/docs/features/feature-crash-reporting
- type: historical-reference
  path: https://measure.sh/docs/features/feature-anr-reporting
- type: reference
  path: https://measure.sh/docs/features/feature-network-monitoring
- type: historical-reference
  path: https://measure.sh/docs/features/feature-performance-tracing
- type: historical-reference
  path: https://measure.sh/docs/features/feature-profiling
- type: reference
  path: https://measure.sh/docs/error-monitoring
- type: reference
  path: https://measure.sh/docs/performance-tracing
- type: reference
  path: https://measure.sh/docs/performance-tracing/profiling
- type: reference
  path: https://measure.sh/docs/configuration-options
- type: reference
  path: https://measure.sh/docs/adaptive-capture
- type: reference
  path: https://measure.sh/docs/performance-impact
- type: reference
  path: https://measure.sh/docs/hosting
- type: official
  path: https://developer.android.com/sdk/api_diff/37/changes/android.os.ProfilingTrigger
- type: official
  path: https://developer.android.com/reference/android/os/ProfilingTrigger
- type: official
  path: https://developer.android.com/about/versions/17/features
- type: aosp
  path: https://android.googlesource.com/platform/packages/modules/Profiling/+/refs/tags/android-17.0.0_r1
task2b_state: "fixed"
task6_state: "reviewed"
task9_state: "reviewed"
pipeline_stage: "ready-to-publish"
---
# Measure

## 产品定位与版本边界

Measure 是一套面向移动端的 APM（Application Performance Monitoring，应用性能监控）与问题诊断平台。项目提供 Android、iOS、Flutter、React Native SDK；官网还提供 KMP（Kotlin Multiplatform）薄封装，让共享 Kotlin 代码调用 Android、iOS 原生 SDK。它把 Crash（未捕获崩溃）、ANR（Application Not Responding，应用无响应）、启动、HTTP、CPU、内存、点击、页面导航、业务 span（一段有起止时间的操作）和 bug report（用户主动提交的问题报告）组织到同一套 session（一次连续使用会话）模型里。

Matrix、KOOM 更偏向在设备内完成专项采集与诊断；Measure 还提供事件入库、检索、聚合、告警、附件保存和团队协作。它们解决的问题有交集，部署层次与运维范围不同，可以同时使用。

截至 2026-08-14，Maven Central 上最新稳定 Android SDK 仍为 `0.19.0`，Gradle Plugin Portal 上最新插件仍为 `0.13.0`；最新 self-host（自托管）版本为 `v0.12.1`。稳定版行为以 `android-v0.19.0` 标签提交 `0ab6595d5671dbbcb326fef908dee351ed8ca1c4` 为准。当前主分支已到北京时间 2026-08-13 的 `7501820c8e6f8bfc8a512061e1d2504b465e0466`，SDK 与插件版本仍分别是 `0.20.0-SNAPSHOT`、`0.14.0-SNAPSHOT`；`SNAPSHOT` 表示开发中的未发布版本。上一轮使用的北京时间 2026-07-25 快照 `8a189ea1e9728105773c1c81fb6cc8797e6b2d15` 保留在参考资料中，便于复现差异。平台核对边界为 Android 17 / API 37 / `android-17.0.0_r1`。

评估前要记住三条边界：

- Android 端尚不支持 C/C++ native crash reporting（原生层崩溃上报）。`ApplicationExitInfo` 能记录 `REASON_CRASH_NATIVE`，这只是退出原因；Measure 还不能解析、聚合并 symbolicate（把地址或混淆名称还原成可读符号）这类崩溃。
- Measure 能给出线上问题发生前后的上下文，但 CPU 抖动、对象泄漏、掉帧或调度问题仍需 Perfetto（Android 系统 trace 分析工具）、heap dump（堆转储）和 Android Studio Profiler 等专项工具继续定位。
- 当前 SDK 源码以 `compileSdk 36` 构建，`compileSdk` 表示编译时可见的最高 Android API。这个 SDK 可以按向后兼容规则运行在 Android 17 设备上，但还没有接入 API 37 新增的全部 `ProfilingTrigger`（由系统事件触发性能采样的配置对象）。后文会单独说明这个差距。

此前流传的 `android.app.Measure`、`MeasureSession` 以及 “Measure → DropBoxManager → statsd → Play Vitals” 链路不存在于 `android-17.0.0_r1`。开源产品 Measure 的入口是 `sh.measure.android.Measure`，数据上传到配置的 Measure ingest 服务，也就是接收 SDK 上报数据的入口。Android 平台的 `DropBoxManager` 位于 `android.os`；`statsd` 是系统统计守护进程，Play Vitals 是 Google Play 的质量指标服务，这些名称都不能证明它们与开源产品 Measure 有调用关系。

## 平台数据怎样流动

Measure 的数据流可以分成端侧采集、支持重试的上传、服务端处理和查询四段。下面这张图只画影响容量与故障处理的主要部件。

```mermaid
flowchart LR
    A["Android App"] --> B["Measure Android SDK"]
    B --> C["本地 SQLite / 附件文件"]
    C --> D["Ingest API"]
    D --> E["Apache Iggy"]
    E --> F["Ingest Worker"]
    F --> G["ClickHouse：事件与查询数据"]
    F --> H["MinIO：截图、profile 等附件"]
    I["Gradle Plugin：构建信息与 mapping"] --> J["API / Symboloader"]
    J --> H
    J --> K["Symbolicator"]
    L["PostgreSQL：团队、应用、配置等元数据"] --> M["Dashboard / API"]
    G --> M
    H --> M
    K --> M
    N["Cleanup / Alerts"] --> G
    N --> L
```

图中的 Ingest API 是数据接收入口，Apache Iggy 是在写入存储前缓冲消息的流式消息系统。ClickHouse 保存适合聚合查询的事件数据，PostgreSQL 保存团队、应用和配置等关系数据，MinIO 保存截图、profile（性能采样文件）和符号文件等对象，Valkey 提供缓存。Symboloader 负责接收 mapping 等符号文件，Symbolicator 再用这些文件把混淆栈还原成可读调用栈。

SDK 先把 event 与 span 写入本地 SQLite 数据库，再按批上传；附件走独立上传路径。默认本地空间上限为 50 MB，可配置在 20～1500 MB，达到上限后会先清理旧数据。离线、服务不可达或附件偏大时，本地容量决定故障现场能保留多久，网络重试次数只是其中一个因素。

self-host 的 Docker Compose 文件用 YAML 统一编排容器服务，包含 dashboard、API、agent、ingest、ingest-worker、cleanup、alerts、symboloader、migrator、Symbolicator、PostgreSQL、ClickHouse、MinIO、Apache Iggy 和 Valkey。当前 main 的基础 Compose 还在 `debug` profile（调试配置组）中提供 ClickStack 日志界面与 Iggy Web 管理界面；生产覆盖文件会移除 ClickStack，Iggy Web 也不会随默认生产配置启动。这个服务清单说明 Measure 需要持续运维，接入工作远超添加一个 AAR（Android Archive，Android 库归档）依赖。

## 会话、事件、span 与附件

### Session 的生命周期

SDK 初始化时创建 session。应用进入后台超过 30 秒后再次回到前台，会创建新 session；更短的前后台切换仍属于原 session。每个 event 和 span 都带 `session_id`，页面、点击、资源曲线、错误与业务耗时由此按时间归入同一次使用过程。

默认动态配置为 Crash、ANR、bug report 各保留问题发生前 300 秒的 session replay（会话回放）上下文。这里的“5 分钟”是错误现场窗口，不代表服务端只保存 5 分钟数据。服务端应用级 retention（保留期）是另一项配置，范围 30～365 天，默认 30 天。

### Event 与 span 是两种对象

Event 表示一个时间点发生的事情或一次状态采样。它有统一外壳：`id`、`session_id`、时间、类型、类型专属 `data`、系统属性、用户自定义属性、附件引用和采样标记。事件类型包括 `exception`、`anr`、`app_exit`、`gesture_click`、`screen_view`、`http`、`cpu_usage`、`memory_usage`、`cold_launch`、`profile` 等。

Span 表示一段持续时间，单独保存；核心字段是 `trace_id`、`span_id`、`parent_id`、`session_id`、起止时间、耗时、状态、属性与 checkpoints。checkpoint 是 span 内某个阶段完成时的时间标记。一个 trace（一次调用链）可以由多个有父子关系的 span 组成；event 即使出现在同一条时间线上，也不会自动变成 span。

下面的 JSON 用来理解关联关系，不是 SDK 的原始上传报文。

```json
{
  "session": {
    "id": "s-7f2d",
    "app_version": "8.4.0",
    "os_version": "17",
    "device_model": "Pixel"
  },
  "events": [
    {
      "id": "e-101",
      "session_id": "s-7f2d",
      "timestamp": "2026-07-25T09:00:05.120Z",
      "type": "screen_view",
      "data": {"name": "ProductDetail"}
    },
    {
      "id": "e-102",
      "session_id": "s-7f2d",
      "timestamp": "2026-07-25T09:00:06.220Z",
      "type": "http",
      "data": {
        "method": "get",
        "url": "https://api.example.com/products/42",
        "status_code": 200,
        "client": "okhttp"
      }
    }
  ],
  "spans": [
    {
      "trace_id": "4bf92f3577b34da6a3ce929d0e0e4736",
      "span_id": "00f067aa0ba902b7",
      "parent_id": null,
      "session_id": "s-7f2d",
      "name": "product.detail.load",
      "duration_ms": 1180,
      "status": "ok"
    }
  ]
}
```

示例里 `session_id` 把移动端现场归在一起，`trace_id` 标识一次耗时调用树。用户 ID、session ID 与分布式 trace ID 的生命周期和用途不同，不能互相替代。

### 一条 ANR 时间线能提供什么

假设用户反馈“打开详情页后卡住”，ANR 堆栈只描述取样时各线程的位置，时间线还能还原问题前的顺序。下例中的 PSS（Proportional Set Size）是按共享内存页比例分摊后的进程内存；`SIGQUIT` 是 Android 用来请求 ART 输出线程 dump（线程快照）的信号。

```text
00:00  lifecycle_app: foreground
00:01  screen_view: Home
00:05  gesture_click: feed_item
00:05  screen_view: ProductDetail
00:06  http: GET /products/{id}, 200, 820 ms
00:07  http: GET /recommendations, timeout
00:07  memory_usage: PSS 420 MB -> 680 MB
00:08  gesture_click: back
00:10  anr: SIGQUIT captured
```

这段记录能提出“详情页加载、超时回调、内存增长或返回流程是否阻塞主线程”等假设，却不能单独证明根因。下一步应对照 ANR 全线程堆栈、`ApplicationExitInfo` trace 和服务端请求日志；仍无法定位时，再复现并采集 Perfetto trace。

## Android 端能力与源码边界

下表以稳定版 `0.19.0` 标签、发布制品和同周期源码交叉检查。表中保留原始类名、字段名与行业术语，便于检索；文档与源码冲突时，以目标 release 的实际代码和远端下发配置为准。

| 能力 | 端侧来源与主要字段 | 能回答的问题 | 不能据此得出的结论 |
|---|---|---|---|
| Java / Kotlin Crash | 包装 `Thread.UncaughtExceptionHandler`；`exception` 含异常链、线程、frames（栈帧）、severity（严重级别）、前后台状态 | 崩溃分组、版本回归、混淆栈还原 | 未覆盖 C/C++ native crash；截图也不能替代线程和状态分析 |
| ANR | native `SIGQUIT` 处理器把信号让渡回 ART Signal Catcher（ART 运行时负责输出线程 dump 的线程）；`anr` 保存主线程 Java 栈和有上限的其他 Java 线程栈；API 30+ 另采 `ApplicationExitInfo` trace | ANR 现场、死锁线索、问题前 5 分钟上下文 | 采集方式不同于定时 ping 主线程的 Java watchdog（看门狗）；其他线程收集受 `MAX_THREADS_IN_EXCEPTION=16` 限制，收到 `SIGQUIT` 也不表示每次都能保存完整现场 |
| App exit | API 30+ 调用 `getHistoricalProcessExitReasons(null, 0, 3)`；记录 reason、importance（进程重要级）、trace、process name、pid（进程号） | 最近的系统杀进程、ANR、低内存、native crash 等退出原因 | SDK 单次只读取最多 3 条历史记录；`app_exit: CRASH_NATIVE` 只是退出分类，不代表具备 native crash 堆栈采集能力 |
| HTTP | Gradle 插件对 OkHttp 4.7.0～5.3.2 做自动 instrumentation（构建期插桩）；0.18.0 起支持包装 `HttpURLConnection`；记录 URL、method、status、起止时间、失败、client，可按 URL 开启 body/header | 端侧耗时、失败率、请求与页面/错误的时序 | Retrofit 若只带 transitive dependency（传递依赖），自动插桩可能失效；请求 body 默认关闭；HTTP event 不等同于服务端 trace |
| 启动 | `MeasureInitProvider.attachInfo`、进程启动时间、Activity 生命周期与下一帧 draw；生成 cold/warm/hot launch | TTID（Time to Initial Display，首帧显示时间）趋势、启动 Activity、版本对比 | 初始化太晚会丢失早期崩溃并降低起点精度；当前 launch metric 不计算 TTFD（Time to Full Display，内容完整呈现时间），`reportFullyDrawn()` 在 Measure 中用于触发 profile，TTFD 趋势需另建业务 span |
| App size | Gradle 插件在 `assemble<Variant>` / `bundle<Variant>` 后调用 `GzipSizeCalculator`，或 bundletool 的 `BuildApksCommand` / `GetSizeCommand`；variant 指 build type 与 product flavor 组合出的构建变体 | APK（直接安装包）估算下载大小、AAB（应用包发布格式）可生成 APK 的最大大小趋势 | AAB 数值不代表所有设备的真实商店下载量；关闭该 variant 的插件后不会上传 |
| CPU | 前台周期采样 `/proc/self/stat` 的 utime、stime、cutime、cstime，并按核数、`_SC_CLK_TCK`（每秒时钟 tick 数）和间隔计算百分比 | 错误前后进程 CPU 趋势 | 该数据不是线程级火焰图，也不能说明某个函数耗时 |
| 内存 | `Runtime` Java heap、`Debug.getMemoryInfo()` PSS、`/proc/<pid>/statm` RSS（Resident Set Size，当前驻留物理内存）、native heap；RSS 按运行设备的 `_SC_PAGESIZE` 换算 | PSS/RSS/Java/native heap 趋势，错误前的内存压力 | 曲线上涨不能直接判为泄漏；对象引用链仍需 heap dump |
| 点击与滚动 | Curtains 拦截 Window touch；View hit test（按触摸坐标查找目标 View）；Compose 遍历 semantics（语义树）；事件含 target、id/label、坐标、尺寸和触摸时间 | 用户操作顺序、点击或滚动目标的估算 | 无可识别 target 的触摸会被丢弃，时间线无法覆盖所有 dead click（没有产生预期反馈的点击）；Compose 未设置 `testTag` 时，target id 信息有限 |
| 页面与生命周期 | Activity、Fragment、应用前后台生命周期；稳定插件支持 AndroidX Navigation Compose 2.4.0～2.9.7；也可手动 `trackScreenView` | 页面路径、页面级错误和耗时 | route 若含订单号等动态值，会形成高基数，即不同取值过多，既不利于聚合，也有隐私风险 |
| Trace / span | 手动 span、父子 span、自动 Activity/Fragment screen-load trace；span 含 trace/session/parent、duration、status、attributes、checkpoints | 登录、首屏、支付等业务路径耗时 | 当前 SDK 没有实现通用 OpenTelemetry SDK 的全部能力，也不会自动生成服务端 span |
| Trigger-based profile | API 36+ `ProfilingManager`；当前注册 `APP_FULLY_DRAWN` 与 `ANR`，结果作为 `profile` 附件由 WorkManager（Android 持久后台任务调度器）上传 | 下载平台返回的 running system trace（运行中系统 trace）快照，补充首屏或 ANR 现场 | 默认关闭；需显式依赖 WorkManager；Android 17 新 trigger 尚未全部注册 |

### 三处容易混淆的版本差异

`0.19.0` 的 `DynamicConfig` 把 CPU 与内存采样间隔都设为 5 秒；同一标签中的旧功能页仍分别写 3 秒和 2 秒。当前 main 已把文档合并到新的 CPU/内存页面，不再重复这两个旧值。判断运行行为时，应检查所用 release 的源码和服务端下发配置。

`0.19.0` 代码默认开启 Crash/ANR 截图，并把 `screenshotMaskLevel` 设为 `AllTextAndMedia`，即默认遮住全部文字与媒体。同一标签里的旧 Crash/ANR 页面仍写着“遮罩默认关闭”；当前官网已经改正。接入验收仍应在目标环境制造一条测试事件，确认远端配置和 SDK release 共同得到的有效值。

稳定版 Gradle 插件 `0.13.0` 的 Navigation Compose 上限是 `2.9.7`。当前官网写 `2.9.8`，对应 main 中尚未发布的 `0.14.0-SNAPSHOT` 插件；如果项目已经升级到 Navigation Compose `2.9.8`，不能只凭当前网页断定稳定插件会插桩成功。

### Android 17 / API 37 的新增机会

Measure 为 `SIGQUIT` ANR 采集带有 `libmeasure-ndk.so`。稳定版 CMake 链接参数包含 `-Wl,-z,max-page-size=16384`，`0.19.0` AAR 内四个 ABI（CPU 架构）版本的 `.so` 也都显示 ELF LOAD segment 的 `p_align` 为 `2**14`，即 16 KB。RSS 计算同时读取运行设备的 `_SC_PAGESIZE`，没有把页大小写死为 4 KB。ELF LOAD segment 是系统把 native 库装入内存时使用的段；这两项检查分别覆盖 native 库对齐与内存页换算。应用仍要对最终 release APK/AAB 做 16 KB page-size 检查，因为宿主工程的 AGP（Android Gradle Plugin）、NDK（Native Development Kit）、其他 `.so` 和 ZIP 打包对齐不由 Measure 控制。

Android 17 为 `ProfilingTrigger` 新增了九种类型。与性能和内存最相关的例子包括 `TRIGGER_TYPE_COLD_START`、`TRIGGER_TYPE_OOM`、`TRIGGER_TYPE_ANOMALY`、`TRIGGER_TYPE_KILL_EXCESSIVE_CPU_USAGE`：冷启动触发器返回新启动的 system trace 与 stack sampling profile（按时间抽样的调用栈），OOM 返回 Java heap dump，anomaly 的附件随异常类型变化，过量 CPU 退出触发器返回 running system trace 快照。

稳定版 `0.19.0` 与当前 main `7501820…` 都仍以 `compileSdk 36` 构建，`ProfileCollector.triggerTypes()` 也都只返回 `TRIGGER_TYPE_APP_FULLY_DRAWN` 和 `TRIGGER_TYPE_ANR`。因此：

- Android 17 用户不会因为 SDK 未使用新 API 就失去既有 Crash、ANR、HTTP、session 等能力。
- 看板里出现 `profile` 不能笼统写成“已经支持 Android 17 OOM 自动 heap dump”。
- 产品后续升级到 `compileSdk 37` 并注册新 trigger 后，还要补充 profile 类型、附件容量、WorkManager 上传、采样和隐私验收。

`ProfileCollector` 能识别 `.hprof` 和 `.heapprofd` 文件，只说明上传模型为这些格式留了入口。当前注册列表没有 OOM trigger，不能据此宣传 Android 17 自动 heap dump。这个边界也说明了源码锚点的价值：只看“支持 Android”或“支持 profiling”无法判断 API 37 能力是否已经进入 SDK。

## 接入还包括平台侧工作

当前官方接入页列出的最低要求是 minSdk 21、targetSdk 35、AGP 8.1.0。minSdk 表示能够安装 SDK 的最低系统版本；targetSdk 表示宿主应用声明适配的 Android 行为版本。稳定坐标如下，升级时应同时查看 release notes（版本说明）和 self-host 兼容表。

```kotlin
plugins {
    id("sh.measure.android.gradle") version "0.13.0"
}

dependencies {
    implementation("sh.measure:measure-android:0.19.0")
}
```

Gradle 插件负责 OkHttp、HttpURLConnection、AndroidX Navigation 等字节码插桩，还负责构建大小与 R8/ProGuard mapping 上传。R8/ProGuard 会压缩并混淆 Java/Kotlin 字节码，mapping 文件记录混淆前后的名称对应关系，服务端用它还原调用栈。禁用某个 variant 的插件会减少构建步骤，也可能让该 variant 缺少自动网络采集、包大小趋势或混淆栈还原。

初始化要尽量靠近 `Application.onCreate()` 开头，并把 API key 与 ingest URL 放在不同 build type、product flavor 的 manifest placeholder 或其他受控配置中。build type 是 release/debug 等构建模式，product flavor 是产品或环境维度，manifest placeholder 会在构建时把指定值代入 Manifest。若延迟初始化，早期 Crash 与启动耗时会缺少数据，之后无法补采。

SDK 接好后，平台侧仍有这些工作：

- 为线上 release、预发 staging、调试 debug 决定是否拆分应用或环境，防止测试数据混入线上参照值。
- 让 API key、API URL、mapping、版本名、version code（整型构建版本号）与构建产物一一对应。
- 配置采样率（实际保留的数据比例）、URL 规则、截图、日志、retention、权限与告警。
- 建立告警负责人、去重规则、分批发布判断和处置时限。
- 监控 SDK 自身的启动耗时、主线程操作、磁盘占用、网络量与附件量。

官方在 Pixel 4a / Android 13 的简单样例上用 Macrobenchmark 重复测试 35 次，测得 SDK `0.16.0` 增加约 17.5～31.3 ms TTID，中位数 24.3 ms；识别点击目标并生成 layout snapshot（布局快照）约增加 0.6～1 ms。这组数字只适合作为回归参照。业务应用应使用自己的基准机、启动路径和 release 构建复测，尤其要关注低端机、首装、离线积压和大量 Compose 节点。

## 自定义 trace 要能聚合，也要能跨端关联

### 命名与属性

Span 名称上限为 64 个字符，checkpoint 名称上限也是 64 个字符，每个 span 最多 100 个 checkpoints。命名应表达稳定的业务步骤，动态值放到值域、类型和隐私范围都受约束的属性里。

| 场景 | 推荐 span 名 | 推荐属性 | 不应放进名称的内容 |
|---|---|---|---|
| 登录 | `auth.login` | `login_method`、`result` | 用户 ID、手机号、错误全文 |
| 首屏 | `home.first_content` | `source`、`item_count`、`cache_hit` | 实验参数拼接串、时间戳 |
| 支付 | `checkout.payment.submit` | `provider`、`result`、`retry_count` | 订单号、金额、token |
| 图片解码 | `media.thumbnail.decode` | `format`、`width_bucket`、`cache_hit` | 图片 URL、文件路径 |

单位要写进属性名，例如 `payload_bytes`、`image_width_px`、`queue_wait_ms`。枚举值应受控，布尔量用布尔类型，避免把任意异常文本、完整 URL 或用户输入当成聚合维度。

下面示例使用当前 Android 源码存在的 `SpanBuilder` API 创建父子 span。

```kotlin
val payment = Measure.startSpan("checkout.payment.submit")
    .setAttribute("provider", "example_pay")

try {
    val tokenize = Measure.createSpanBuilder("checkout.payment.tokenize")
        ?.setParent(payment)
        ?.startSpan()

    tokenizeCard()
    tokenize?.setStatus(SpanStatus.Ok)?.end()

    submitOrder()
    payment
        .setCheckpoint("order_accepted")
        .setAttribute("retry_count", 0)
        .setStatus(SpanStatus.Ok)
        .end()
} catch (t: Throwable) {
    payment
        .setAttribute("error_type", t.javaClass.simpleName)
        .setStatus(SpanStatus.Error)
        .end()
    throw t
}
```

父 span 表示支付提交，子 span 只表示令牌化步骤。代码不要把异常 message 写入属性，因为 message 常含服务端返回、账号或订单信息。`0.19.0` 标签中的旧性能 tracing 页面曾展示源码不存在的 `startSpan(name, parent=...)` Kotlin 重载；当前官网已经改用 `.setParent(...)`。复制示例时仍要对照项目实际使用的 SDK 公共 API。

### 与 OpenTelemetry 的关系

移动 session 和分布式 trace 解决不同问题。session 关注应用前后台、设备、页面、手势、Crash、ANR 和资源曲线；OpenTelemetry（OTel，一套跨语言可观测性标准）trace 关注跨进程调用树、服务与依赖耗时。二者可以通过 W3C Trace Context 关联：它规定如何在请求头中传递 trace 上下文，无需把 session ID 改造成服务端 trace ID。

Measure Android SDK 能从 span 生成标准 `traceparent` 请求头；值中包含版本、`trace_id`、父 `span_id` 和采样标记。下面示例把移动根 span 的上下文显式放进业务请求。

```kotlin
val span = Measure.startSpan("checkout.payment.submit")

val request = Request.Builder()
    .url(paymentUrl)
    .header(
        Measure.getTraceParentHeaderKey(),
        Measure.getTraceParentHeaderValue(span),
    )
    .build()
```

服务端 OpenTelemetry instrumentation（自动提取并创建 trace 的中间件或 SDK）读取 `traceparent` 后，可继续同一个 `trace_id`。Measure 的自动 HTTP event 仍是 session 时间线事件，不会自动把每个 OkHttp 请求挂到自定义 span 下。

建议把三类 ID 分工固定下来：

- `session_id`：从移动错误或用户反馈回到 Measure 会话。
- `trace_id`：从移动 span 跳到服务端 APM，并追踪跨服务调用。
- `request_id`：保留服务端日志系统自己的单请求检索键，作为尚未全面接入 trace 的补充。

如果网关会丢弃未知 header，要把 `traceparent` 加入转发规则，并验证服务端是否遵循其中的采样位。若服务端另起 trace，至少在移动 span 和服务端日志同时记录一个不直接识别用户的 request ID，并通过真实请求验证两端可以互查。

## 自托管的成本与故障点

### 官方自托管定位

当前官方文档把安装脚本定位为单台虚拟机部署，并说明 self-host 更适合云服务不可用、又有资深基础设施工程师持续维护的强监管环境。若需要分布式、安全且可横向扩展的部署，官方推荐其托管云。文档同时警告，配置错误可能造成数据丢失、安全漏洞和停机。最低机器规格是 x86-64 Ubuntu 24.04 / Debian 12、4 vCPU、16 GB RAM、100 GB 系统盘。

这组配置是安装下限，不是容量承诺。上线前至少要用“日活用户数 × 每会话事件数 × 采样率 × 单事件/附件大小 × 保留天数”估算写入量，再测试 ClickHouse 查询、MinIO 增长、Iggy 积压与清理吞吐。

### 数据分别保存在哪里

| 数据 | 主要存储或服务 | 容量与恢复重点 |
|---|---|---|
| 事件、span、聚合查询数据 | ClickHouse | 分区、TTL（Time To Live，到期清理规则）、cleanup、磁盘水位、查询并发 |
| 团队、应用、权限、配置等元数据 | PostgreSQL | 一致性备份、迁移、凭据与恢复演练 |
| 截图、layout snapshot、profile、符号文件等对象 | MinIO | 对象生命周期、跨区备份、删除一致性 |
| ingest 缓冲 | Apache Iggy | 消费积压、磁盘保护、重放与重复处理 |
| 缓存/短期状态 | Valkey（Compose 服务名为 `redis`） | 丢失后的可恢复性、内存与淘汰策略 |
| 符号处理 | Symboloader + Symbolicator | mapping/符号文件与 app version/build 的关联 |

Android R8/ProGuard mapping 由 Gradle 插件在 assemble 任务后上传。自托管环境要保证构建上传与事件 ingest 使用同一个 app/API 配置，并以 version name、version code、app identifier（应用包标识）关联。Compose 中存在 Symbolicator 只说明平台具备符号处理服务；Android native crash reporting 当前仍未实现。

### 保留期、附件与备份

Dashboard API 的应用 retention 范围为 30～365 天，默认 30 天。它会影响事件数据的清理节奏，但运维团队仍要逐项确认附件、数据库备份和对象存储快照是否遵循同一期限。若备份保留 180 天而线上 retention 是 30 天，用户删除请求和合规说明不能只写“Dashboard 已设 30 天”。

至少进行以下恢复演练：

- PostgreSQL 与 ClickHouse 在同一恢复点附近恢复后，应用、session 和查询是否仍对应。
- MinIO 恢复后，截图、profile、mapping 引用是否还可读取。
- Iggy 有积压时升级或重启，是否会漏数据或造成重复入库。
- 从一个稳定 `vMAJOR.MINOR.PATCH` tag 升级前，是否完成官方 migration guide 要求，并验证回滚数据兼容性。

生产部署不应直接追随 `main`。自托管文档要求选择面向部署的稳定 `v*` tag；SDK 与 self-host 也有最低版本配对关系，例如 Android SDK `>=0.16.0` 要求 self-host `>=0.10.0`。

### 小团队也要算的账

| 阶段 | 推荐范围 | 主要成本 |
|---|---|---|
| 2～4 周试点 | 单应用、一个 release 版本、Crash/ANR/HTTP/会话 | 机器、接入、隐私审查、mapping 与告警验证 |
| 中型团队 | 多应用、多环境、按版本灰度、业务 trace | 容量规划、查询性能、权限、值班、备份与升级 |
| 强合规私有化 | 区域隔离、审计、删除流程、灾备 | 安全加固、身份系统、密钥轮换、证据留存与恢复演练 |

这张表没有给固定金额，因为附件比例、事件采样、日活和查询频率比团队人数更能决定成本。试点要记录每千 session 的 ClickHouse 增量、MinIO 增量和 ingest 峰值，再外推预算。

## 隐私策略要先于全量采集

Measure 把远端采集配置称为 Adaptive Capture：可以在 Dashboard 修改采样、截图遮罩和日志等选项，无需发布新 APK。Android SDK 会先获取并缓存配置，通常到下一次启动才应用，因此一次修改需要经历两次应用启动才完全生效。这个能力便于在故障期临时提高采集率，也意味着有权限的人可以扩大数据范围；相关角色和变更记录都应纳入权限审计。

| 采集内容 | 当前默认或控制点 | 建议 |
|---|---|---|
| 用户 ID | `setUserId()` 会跨启动持久化，`clearUserId()` 只影响后续标识 | 使用匿名内部 ID；登出清理；不要上传邮箱、手机号 |
| Intent data | `trackActivityIntentData=false` | 保持关闭，除非逐字段确认 deep link（打开应用内页面的链接）与 extras（Intent 附加参数）不含 token 或账号 |
| HTTP body/header | 默认不采；按 URL 精确或 `*` 规则开启；Authorization、Cookie、Set-Cookie、Proxy-Authorization、WWW-Authenticate、X-Api-Key 永久阻断 | 只对白名单接口短期开启；业务层先脱敏；不要把 GraphQL 全量 body 当成普通诊断字段 |
| URL | HTTP event 会记录完整 URL | 上传前去掉 query（`?` 后参数）、fragment（`#` 后片段）、签名参数和路径中的用户/订单 ID；统一成取值数量受控的 endpoint（接口路径） |
| 自动日志 | 默认关闭，最低采集 severity 与 ignore regex 可远端配置 | severity 是日志级别，regex 是正则过滤规则；日志正文仍要按敏感级别审查，异常对象不要直接拼完整请求 |
| Crash/ANR 截图 | 当前代码默认开启，默认 mask `AllTextAndMedia`；远端配置可改变 | 支付、实名、聊天、密码页做禁采验证；不要只相信配置名称 |
| 点击 layout snapshot | click 默认可生成，连续 snapshot 有 750 ms 节流 | 检查文本、content description、Compose semantics 和 `testTag` 是否泄露业务数据 |
| Bug report 附件 | 最多 5 个，描述最多 4000 字符 | 让用户预览并删除附件；服务端校验类型、大小和访问权限 |
| 本地磁盘 | 默认 50 MB，离线时保留到上限 | 退出登录、账号切换和用户拒绝采集时定义本地数据处置方式 |
| 服务端 retention | 30～365 天，默认 30 天 | 把线上库、对象存储与备份的期限放在同一张清单 |

`clearUserId()` 会清除本地持久化标识，使后续 event 不再带该 ID，但不会自动删除已经上传的历史 session。公开 API 中可验证的是应用 retention 配置，不能据此声称平台已经提供“按 user ID 擦除所有历史数据”的完整流程。上线前要用自己的部署版本演练检索、导出、删除、缓存失效、对象删除和备份到期；做不到时，就不应上传可直接识别个人的数据。

## Firebase、Sentry 与 Measure 怎样选

下表比较的是产品重心，不是功能数量排名。各产品都在快速变化，采购或迁移前要用目标版本复核。

| 维度 | Firebase Crashlytics + Performance | Sentry | Measure |
|---|---|---|---|
| 托管形态 | Google 托管，无官方 self-host | 官方 SaaS；提供 self-hosted 发行版 | 官方云；Apache-2.0 仓库与单机 self-host |
| Android 错误 | JVM、NDK Crash；Crashlytics 在 Android 11+ 通过历史退出原因报告 ANR | JVM/NDK 错误、ANR、breadcrumbs（错误前的简短事件轨迹）等，覆盖面成熟 | JVM Crash、SIGQUIT ANR、app exit；无 Android native crash |
| 性能视角 | 自动启动、HTTP、屏幕渲染、自定义 trace | 跨端 error、transaction/span、profiling/replay 能力丰富 | 启动、HTTP、screen-load/custom span、资源曲线与 session timeline |
| 会话上下文 | Crashlytics breadcrumbs 依赖 Analytics；Performance 数据在 Firebase 看板 | breadcrumbs、release health、移动 replay 等 | 点击、导航、HTTP、CPU、内存、错误、附件围绕移动 session 组织 |
| 数据控制 | 服从 Firebase 服务区域、条款与导出能力 | SaaS 或自运维 self-hosted | 适合需要查看完整源码并控制自托管数据面的团队 |
| 运维成本 | 客户端与控制台配置为主 | self-hosted 架构复杂；SaaS 可降低运维负担 | 官方脚本是单机定位；全套服务仍需容量、备份、升级和安全运营 |

可以按问题类型做决策：

- 已深度使用 Firebase，需求集中在 Crash/ANR、启动、HTTP 和屏幕渲染指标：优先验证 Firebase，接入和团队学习成本通常较低。
- 需要 Web、后端、移动统一错误与 trace，或已经使用 Sentry：优先评估 Sentry，避免再建一套跨端问题系统。
- 主要是移动应用，希望源码透明、自托管，并重视错误前的点击、页面、网络与资源上下文：Measure 值得试点。
- 核心需求是 native crash：不要把 Measure 作为唯一稳定性平台。
- 核心需求是精确掉帧归因：三者的聚合指标都不能代替 FrameTimeline、Perfetto 与源码分析。

## 2～4 周试点怎么验收

试点不宜从“把开关全打开”开始。选择一个有稳定发布节奏、能制造测试 Crash/ANR、流量可控的应用，按周逐步扩大验证范围。

### 第 1 周：接入与数据边界

- 固定 SDK `0.19.0`、Gradle 插件 `0.13.0` 和 self-host/cloud 版本。
- 验证 release mapping 上传、混淆 Crash 还原、冷/温/热启动分类。
- 制造前台与后台 Crash、Java deadlock ANR、API 30+ app exit。
- 抓包检查 URL、header、body、用户 ID、截图、layout snapshot。
- 记录 SDK 对 TTID、主线程、网络量和本地磁盘的影响。

### 第 2 周：会话是否能缩短定位

- 用同一条业务路径制造慢接口、接口失败、内存增长和 ANR。
- 让未参与接入的工程师只根据看板还原复现步骤。
- 检查 session 搜索能否按版本、设备、页面、事件和匿名用户 ID 找到目标。
- 记录误导性 target、重复 screen、动态 route 和告警噪声。

### 第 3～4 周：运营与恢复

- 为登录、首屏、支付、图片解码各接一个稳定 span，验证 P50（中位数）、P95（95% 样本不超过的耗时）与样本明细。
- 传播 `traceparent` 到一个服务端接口，从移动 session 跳到后端 trace。
- 调整采样后复核成本、查询速度和故障样本完整度。
- 自托管团队执行一次版本升级、数据备份与恢复演练。
- 演练用户数据检索与删除，确认对象存储和备份的处置时限。

验收表要包含可量化标准：

| 问题 | 建议通过标准 |
|---|---|
| Crash 定位 | release mapping 自动关联；测试混淆栈可还原；分组不被动态 message 打散 |
| ANR 上下文 | 能看到有效线程 dump、问题前页面/点击/HTTP；API 30+ app exit 可关联 |
| Session 检索 | 已知测试 session 在约定时限内可按至少两种维度找到 |
| 告警噪声 | 每类告警有负责人、抑制规则和可接受误报率 |
| Trace 规范 | 名称无动态 ID；属性有类型、单位、基数与隐私约束 |
| 平台成本 | 已测每千 session 数据量、附件占比、查询延迟和恢复时间 |
| Android 17 | 既有能力在 API 37 真机通过；未把 API 37 新 profiling trigger 误报为现有能力 |

只有当“采到数据”转化为“更快找到根因，并且团队愿意持续投入数据治理和平台维护”时，试点才算通过。

## 参考资料

- [Measure 仓库快照：`8a189ea1e9728105773c1c81fb6cc8797e6b2d15`](https://github.com/measure-sh/measure/tree/8a189ea1e9728105773c1c81fb6cc8797e6b2d15)
- [Measure 当前仓库快照：`7501820c8e6f8bfc8a512061e1d2504b465e0466`](https://github.com/measure-sh/measure/tree/7501820c8e6f8bfc8a512061e1d2504b465e0466)
- [Measure Android SDK `0.19.0` release](https://github.com/measure-sh/measure/releases/tag/android-v0.19.0)
- [Measure Android SDK Maven metadata](https://repo.maven.apache.org/maven2/sh/measure/measure-android/maven-metadata.xml)
- [Measure Android SDK `0.19.0` AAR](https://repo.maven.apache.org/maven2/sh/measure/measure-android/0.19.0/measure-android-0.19.0.aar)
- [Measure Gradle 插件 metadata](https://plugins.gradle.org/m2/sh/measure/android/gradle/sh.measure.android.gradle.gradle.plugin/maven-metadata.xml)
- [Android SDK 构建配置：minSdk 21、compileSdk 36](https://github.com/measure-sh/measure/blob/8a189ea1e9728105773c1c81fb6cc8797e6b2d15/android/measure-android/measure/build.gradle.kts)
- [Android SDK 动态配置默认值](https://github.com/measure-sh/measure/blob/8a189ea1e9728105773c1c81fb6cc8797e6b2d15/android/measure-android/measure/src/main/java/sh/measure/android/config/DynamicConfig.kt)
- [Android ANR `SIGQUIT` handler](https://github.com/measure-sh/measure/blob/8a189ea1e9728105773c1c81fb6cc8797e6b2d15/android/measure-android/measure/src/main/jni/anr_handler.c)
- [Measure native library 16 KB linker alignment](https://github.com/measure-sh/measure/blob/8a189ea1e9728105773c1c81fb6cc8797e6b2d15/android/measure-android/measure/src/main/CMakeLists.txt)
- [Measure RSS page-size conversion](https://github.com/measure-sh/measure/blob/8a189ea1e9728105773c1c81fb6cc8797e6b2d15/android/measure-android/measure/src/main/java/sh/measure/android/performance/MemoryReader.kt)
- [Android `ProfileCollector` 当前注册的触发类型](https://github.com/measure-sh/measure/blob/8a189ea1e9728105773c1c81fb6cc8797e6b2d15/android/measure-android/measure/src/main/java/sh/measure/android/profiling/ProfileCollector.kt)
- [Android span 与 W3C `traceparent` API](https://github.com/measure-sh/measure/blob/8a189ea1e9728105773c1c81fb6cc8797e6b2d15/android/measure-android/measure/src/main/java/sh/measure/android/Measure.kt)
- [Measure self-host production Compose](https://github.com/measure-sh/measure/blob/8a189ea1e9728105773c1c81fb6cc8797e6b2d15/self-host/compose.prod.yml)
- [Measure 当前 self-host Compose](https://github.com/measure-sh/measure/blob/7501820c8e6f8bfc8a512061e1d2504b465e0466/self-host/compose.yml)
- [当前 main 的 Navigation Compose 插桩上限](https://github.com/measure-sh/measure/blob/7501820c8e6f8bfc8a512061e1d2504b465e0466/android/measure-gradle-plugin/src/main/kotlin/sh/measure/asm/NavigationTransformer.kt)
- [Measure Android SDK 接入指南](https://measure.sh/docs/sdk-integration-guide)
- [Measure 当前 Android 接入页](https://measure.sh/docs/getting-started/android)
- [Measure Kotlin Multiplatform 接入页](https://measure.sh/docs/getting-started/kotlin-multiplatform)
- [Measure Session Timeline](https://measure.sh/docs/features/feature-session-timelines)
- [Measure Crash Reporting](https://measure.sh/docs/features/feature-crash-reporting)
- [Measure ANR Reporting](https://measure.sh/docs/features/feature-anr-reporting)
- [Measure Network Monitoring](https://measure.sh/docs/features/feature-network-monitoring)
- [Measure Performance Tracing](https://measure.sh/docs/features/feature-performance-tracing)
- [Measure Android Profiling](https://measure.sh/docs/features/feature-profiling)
- [Measure 当前 Error Monitoring：Crash 与 ANR](https://measure.sh/docs/error-monitoring)
- [Measure 当前 Performance Tracing](https://measure.sh/docs/performance-tracing)
- [Measure 当前 Android Profiling](https://measure.sh/docs/performance-tracing/profiling)
- [Measure SDK Configuration](https://measure.sh/docs/configuration-options)
- [Measure Adaptive Capture](https://measure.sh/docs/adaptive-capture)
- [Measure SDK Performance Impact](https://measure.sh/docs/performance-impact)
- [Measure Self Hosting Guide](https://measure.sh/docs/hosting)
- [Android 17 / API 37 `ProfilingTrigger` API 差异](https://developer.android.com/sdk/api_diff/37/changes/android.os.ProfilingTrigger)
- [Android `ProfilingTrigger` API reference](https://developer.android.com/reference/android/os/ProfilingTrigger)
- [Android 17 Features：新增 profiling triggers](https://developer.android.com/about/versions/17/features)
- [AOSP Profiling 模块：`android-17.0.0_r1`](https://android.googlesource.com/platform/packages/modules/Profiling/+/refs/tags/android-17.0.0_r1)
- [AOSP frameworks/base `android.app` 目录：`android-17.0.0_r1`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/app/)
- [AOSP `android.os.DropBoxManager`：`android-17.0.0_r1`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/os/DropBoxManager.java)
- [Firebase Crashlytics for Android](https://firebase.google.com/docs/crashlytics/android/get-started)
- [Firebase Performance Monitoring for Android](https://firebase.google.com/docs/perf-mon/get-started-android)
- [Sentry Android 文档](https://docs.sentry.io/platforms/android/)
- [Sentry self-hosted](https://github.com/getsentry/self-hosted)
