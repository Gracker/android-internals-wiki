---
title: "DoraemonKit / DoKit"
chapter: "19"
section: "19.06"
status: finalized
applicable_versions: "Android Maven 3.7.11；README 示例仍为 3.5.0 / 3.5.0.1；3.7.11 插件不支持 AGP 8+；Android 17 / API 37 需宿主回归"
last_verified: "2026-08-14"
last_verified_against: "DoKit Android 3.7.11 Maven metadata, POM/AAR/source JAR/plugin binary; master 626827c; AGP API docs; Android 17 AOSP; 16 KB ELF checks"
confidence: medium
tags: [apm, debug-tools, testing, mock, weak-network]
related_chapters: ["19.0"]
sources:
  - type: official
    path: "https://github.com/didi/DoKit/blob/master/README.md"
  - type: official
    path: "https://github.com/didi/DoKit/blob/master/Android/README.md"
pipeline_stage: ready-to-publish
task6_state: "reviewed"
task9_state: reviewed
task2b_state: fixed
---

# DoraemonKit / DoKit

## DoKit 的位置：研发现场，不是生产观测平台

DoraemonKit（DoKit）把网络查看、弱网模拟、Mock（用预设数据替换响应）、文件与数据库浏览、日志、性能浮窗、UI 检查和业务自定义入口放进同一个 Android 调试包。测试人员可以直接在设备上改变测试条件，开发人员也能在相同场景中查看请求与进程状态。这类现场调试是它最擅长的用途。

这些工具也会改变被测环境。浮窗会增加绘制工作，性能面板会定时采样，网络模块会插入 interceptor（请求拦截器），部分功能还依赖编译期字节码插桩（构建时改写 class）或 hidden API（应用 SDK 未公开的接口）。DoKit 适合回答“哪个页面、哪个操作或哪个网络条件值得继续调查”，浮窗读数不足以支持版本级性能结论，也不适合承担生产 APM（Application Performance Monitoring，应用性能监控）的采集任务。

本文以 Android 17 / API 37 / `android-17.0.0_r1` 做平台源码核对。DoKit 没有面向 API 37 的官方兼容承诺，因此这里的“可用”只表示源码上没有发现确定性阻断；团队仍要用自己的 AGP（Android Gradle Plugin）、完整依赖、目标设备和最终安装包验证。

## 先认清公开版本与源码边界

截至 2026-08-14，DoKit 的公开资料存在四条容易混淆的时间线：

| 对象 | 可核对状态 | 工程判断 |
|---|---|---|
| 官方 README | 示例仍以 `3.5.0`、`3.5.0.1` 和 AGP 3.3.0+ 为主 | 只能说明旧接入方式，不能证明 AGP 8/9 或 API 37 兼容 |
| Maven Central | `dokitx`、`dokitx-plugin`、`dokitx-no-op` 的 latest/release 字段均为 `3.7.11`，仓库元数据更新时间为 2023-02-06 | 引入公开版本时应按 3.7.11 的 AAR、POM 和 source JAR 审计 |
| GitHub Releases | 最新可见的 `3.1.7` 发布于 2025-06-20，但标题明确是 `iOS: 3.1.7` | 不能把跨平台仓库的 iOS release 当成 Android Maven 新版 |
| GitHub `master` | 审阅提交为 `626827cddb2feb2f3aee87a52a064b4e5ca2bed4`；`Android/config.gradle` 写的是未公开发布的 `3.7.14.9-kotlin-13` | `master` 可用于理解后续代码，不能替代 3.7.11 发布物的行为 |

3.7.11 的 POM（Maven 依赖描述文件）仍依赖 Kotlin 1.4.32、OkHttp 3.14.7 和较早的 AndroidX 组件。Gradle 成功下载依赖，只能说明 Maven 坐标可解析；这无法证明旧依赖与当前工程的 Kotlin、R8（代码压缩与优化工具）、AndroidX 或 targetSdk 37 组合可用。

审阅第三方调试 SDK 时，应固定以下四样材料：

- Maven POM：确认传递依赖，也就是该库还会自动带进哪些库。
- AAR（Android 库归档）与合并后的 manifest（Android 清单）：确认权限、组件、资源和 native（C/C++ 原生）库。
- 同版本 source JAR（源码归档）：确认发布版本的运行语义。
- 最终 APK/AAB（安装包/应用商店包）：确认正式构建中实际留下了什么。

不要用 GitHub `master` 的代码证明公开 3.7.11 具备同样行为，也不要把 README 的 AGP 下限理解为对所有更高版本的承诺。

## 能力地图：每项能力能回答什么

| 能力 | 主要使用者 | 适合现场 | 不适合下的结论 |
|---|---|---|---|
| FPS、CPU、内存浮窗 | 开发、性能专项 | 在手工路径中找到数值突变的位置 | 版本帧率、CPU 或内存达标 |
| 网络查看 | 测试、开发 | 核对 URL、Header（请求/响应头）、Body（请求/响应正文）、状态码和图片大小 | DNS 解析、连接、TLS 握手各阶段的精确耗时 |
| 弱网 | 测试、开发 | 在安全接口上观察慢请求、慢 Body 和页面等待 | 还原真实蜂窝网络、丢包、切网或系统超时 |
| Mock | 测试、开发 | 让 UI 消费指定响应，检查空态和容错页面 | 阻止原请求到达服务端，或验证网络异常类型 |
| 文件、数据库、日志 | 开发、测试 | 检查本地缓存、数据库迁移和业务状态 | 证明线上数据安全或并发写入正确 |
| 环境切换、业务入口 | 开发、测试 | 统一收纳测试域名、清缓存、诊断页 | 作为面向用户的运维入口 |
| UI 层级、取色、边界 | 客户端开发、UI QA | 检查控件信息和布局问题 | 替代可访问性、截图或渲染基准测试 |
| 卡顿、启动、函数耗时 | 开发、性能专项 | 找到值得录制 trace（事件时间线）的路径 | 给出可跨设备比较的性能结果 |

这张表的读法很简单：DoKit 提供线索和测试条件，专项工具提供可复核证据。

## 接入由运行时 AAR 和编译插件两部分组成

`dokitx` 是运行时工具箱，`dokitx-plugin` 负责构建期字节码改写。3.7.11 的插件在 `DoKitPlugin.kt` 中取得旧版 `AppExtension` / `LibraryExtension`，随后调用 `registerTransform()`。AGP 8.0 已移除 Transform API；官方替代接口在 AGP 7.2 时已经齐备。使用 AGP 8+ 的项目不能直接加载这套旧插件实现。

插件还有一个容易漏掉的构建变体问题。它只检查本次命令中的顶层 Gradle task 名是否包含 `release` / `Release`。执行 `assembleRelease` 时通常会跳过插件，执行会聚合多个变体的 `assemble` 时却可能判断为非 Release，继而注册 Transform。因此，不能把正式包隔离完全交给这段 task 名判断。

可以按能力拆开决策：

| 接入方式 | 可以保留 | 会失去或需要另做 |
|---|---|---|
| 只接 `dokitx` 运行时 AAR | 面板、自定义 kit（DoKit 工具入口）、部分本地工具 | 依赖 ASM（JVM 字节码读写库）改写的 OkHttp 注入、函数耗时、部分启动采集 |
| 接 3.7.11 原插件 | 旧 AGP 项目中的字节码能力 | 不适用于 AGP 8+；还要验证变体隔离和构建稳定性 |
| 维护内部 fork（从上游代码派生并自行维护的版本） | 可按项目需要迁移字节码能力 | 要改用 Android Components 的 Instrumentation API（改写 class）与 Artifacts API（读写构建产物），并持续测试 AGP 版本 |
| Release 接 `dokitx-no-op` | 共享源码可继续引用 DoKit API | no-op 是不执行实际工作的占位实现；它只能降低误引用成本，仍要检查最终产物 |

3.7.11 发布插件把 OkHttp 改写放在 `CommClassTransformer`；当前 `master` 已拆出 `Okhttp3ClassTransformer`。类名变化说明两条源码线不能混作同一份实现证据。

如果团队不准备维护插件 fork，在 API 37 工程中更稳妥的选择是只评估运行时 AAR，把字节码类功能交给 Perfetto、Macrobenchmark（Jetpack 场景基准测试）、Profiler，或由网络库显式安装调试 interceptor。

## 只在 Debug 变体接入

依赖要按 build variant（构建变体）声明。下面的例子以 Maven Central 公开的 3.7.11 为审计对象，并且不加载旧插件：

```kotlin
dependencies {
    debugImplementation("io.github.didi.dokit:dokitx:3.7.11")
    releaseImplementation("io.github.didi.dokit:dokitx-no-op:3.7.11")
}
```

这种写法让 Release 源码仍能解析 DoKit API，但不会带入完整运行时。若项目有 `internal`、`qa`、`benchmark` 等 product flavor（产品维度的构建配置），应逐个声明允许的组合；`debugImplementation` 只描述 build type（Debug/Release 这类构建类型），不会自动表达所有变体的发布意图。

业务代码也不宜四处直接打开 DoKit 页面。下面的接口把业务诊断入口集中到一个注册点，Release 使用空实现：

```kotlin
interface DevToolRegistry {
    fun register(name: String, action: () -> Unit)
}

class NoopDevToolRegistry : DevToolRegistry {
    override fun register(name: String, action: () -> Unit) = Unit
}
```

Debug 实现可以把“切换接口环境”“清理指定缓存”“打开当前页面状态”“导出诊断日志”注册为自定义 kit；Release 注入 `NoopDevToolRegistry`。这样可以保留共享业务代码，同时把 DoKit 类型限制在调试模块内。

初始化时应主动关闭默认使用统计。下面的调用只放进允许 DoKit 的 source set（例如仅参与 Debug 编译的 `src/debug`）中，`customKits` 接收项目自己的 `AbstractKit` 列表：

```kotlin
DoKit.Builder(this)
    .disableUpload()
    .customKits(internalKits)
    .alwaysShowMainIcon(false)
    .build()
```

`disableUpload()` 只把 `DoKitManager.ENABLE_UPLOAD` 设为 false，阻止初始化时上传应用基本信息。空 `productId` 也不会自动关闭这项默认统计。内置“健康体检”、Mock 平台和业务自定义 kit 有各自的请求路径，因此还要抓包核对测试包实际发出的流量。

## 性能面板：数据从哪里来

### FPS

这里的 FPS（frames per second）是每秒收到的帧回调数。3.7.11 的 `PerformanceDataManager` 注册连续的 `Choreographer.FrameCallback`（每次界面帧调度时收到回调），每次回调把计数加一；主线程上的 `Handler` 任务每 1000 ms 读取并清零计数。显示上限取自 `defaultDisplay.refreshRate`（屏幕刷新率），超过上限的计数会被截到该值。

这里有两个计数问题：

- 统计任务也在主线程。主线程堵塞时，“一秒窗口”可能延后执行，但代码没有按真实经过时间归一化。
- 内置“健康体检”的保存路径还会把帧率上限压到 60。90 Hz、120 Hz 设备上的高刷新率信息会丢失。

因此，浮窗 FPS 能提示“这次滑动明显异常”，但不能说明慢帧发生在应用、RenderThread（渲染线程）还是系统合成阶段，也不能替代 FrameTimeline（帧各阶段时间线）或 JankStats（关联 App 状态与慢帧的库）。

### CPU

Android 8.0 及以上，DoKit 每 500 ms 执行一次 `top -n 1`，查找当前 PID（进程 ID）所在行，再把 `%CPU` 除以 `availableProcessors()`；更早系统读取 `/proc/stat` 与 `/proc/<pid>/stat`。

`top` 的输出格式不属于 Android SDK 兼容契约，执行命令本身也有开销。除以核数后的百分比与 Profiler、Perfetto 或其他监控库未必采用同一算法。它适合发现“某一步骤 CPU 持续升高”，几次浮窗读数不足以支持版本对比。

### 内存

Android 10 及以上，DoKit 每 500 ms 调用 `Debug.getMemoryInfo()`，展示 `totalPss / 1024` 的 MB 值；较低版本使用 `ActivityManager.getProcessMemoryInfo()`。

PSS（Proportional Set Size）是进程在采样时刻的驻留内存：私有页全部计入，共享页按比例分摊。它不会告诉你哪个对象仍被引用，一次上涨也不足以判定泄漏。解释 Java/Kotlin 对象要看 heap dump 和引用链；解释进程整体内存则要结合 `dumpsys meminfo`、Perfetto 和 native 分配信息。

### 网络流量

DoKit 每 500 ms 读取 `NetworkManager` 中累计的请求与响应字节数，再计算这 500 ms 内的增量。数据只来自 DoKit hook（运行时替换/代理）或 interceptor 覆盖的网络路径，不是系统为整个 UID（应用在 Linux 层的用户标识）统计的全部流量。

3.7.11 插件能给 OkHttp / HttpURLConnection 路径插入采集逻辑，但现代 AGP 项目如果不加载该插件，覆盖面会随之缩小。健康检查代码还有对响应调用 `peekBody(Long.MAX_VALUE)` 的路径，大响应可能被复制进内存，反过来干扰内存与网络测试。

网络面板适合确认“哪个请求、哪类 Body（请求或响应内容）值得查”。若要分别测量 DNS 解析、TCP connect、TLS 握手、请求发送和响应读取，应使用 OkHttp `EventListener`、服务端 trace 或系统 trace。

### 启动、函数耗时与卡顿

启动和函数耗时很依赖插件插桩；没有插件时，这些面板不具备完整采集路径。即便插件能够运行，Debug 构建、字节码改写和浮窗也会改变启动与方法耗时，正式性能结论仍应使用 Macrobenchmark 与 Perfetto 复测。

DoKit 自带的卡顿监控也有明确边界：

- 阈值固定为 200 ms。
- 堆栈采样在 300 ms 后开始，并继续以 300 ms 间隔采样。
- 200～300 ms 的主线程事件可能已越过阈值，却因没有采到堆栈而被丢弃。
- `MonitorCore` 依赖 `Looper.setMessageLogging()` 在主线程消息执行前后发出的日志，并同时记录墙上时间与主线程 CPU 时间。
- 堆栈最多保留 100 份，连续相同的堆栈会被过滤。

Android 17 的 `Looper` 仍只有一个 `mLogging` 字段，`setMessageLogging()` 每次都会替换这个 `Printer`。DoKit 的卡顿与 TimeCounter（页面跳转耗时）模块会互相停用，停止时还会把 logger 设为 null；应用内另一个使用相同接口的监控器也可能被覆盖。现场没有记录，不能证明没有卡顿；一份堆栈也只代表某个 300 ms 采样时刻。

## Android 17 上的运行时兼容边界

### 隐藏 API 与主线程 Handler hook

3.7.11 的 `DoKitReal.install()` 会在主进程调用 `HandlerHooker.doHook()`。Android 9 及以上，它先调用 FreeReflection 2.1.0 提供的 `Reflection.unseal(app)`，尝试放宽 hidden API 反射限制；随后反射：

- `ActivityThread.currentActivityThread`
- `ActivityThread.mH`
- `Handler.mCallback`

`android-17.0.0_r1` 源码中这些成员仍存在，但它们不属于公开 SDK 兼容契约。字段“还在”不代表第三方应用一定有权访问；hidden API 执行策略、OEM（设备厂商）修改、反射库行为或应用加固都可能让 hook 失败。`HandlerHooker` 会捕获 `Exception` 并打印堆栈，依赖该 hook 的功能可能无法工作，因此 API 37 测试要检查日志和具体功能，不能只看 App 是否崩溃。

公开 3.7.11 还在 Android 12（API 31）及以上跳过 SandHook 全局 runtime hook；SandHook 是一种原生方法 hook 框架，源码注释直接写明 Android S 上会崩溃。API 37 设备至少要覆盖冷启动、Activity 跳转、横竖屏、分屏、前后台切换和加固后的安装包，不能只验证面板能打开。

### Manifest、权限与前台服务

3.7.11 核心 AAR 的 manifest 仍写着 `targetSdkVersion 31`，并声明了网络、Wi-Fi、存储、电话状态、相机、悬浮窗、前台服务和唤醒锁等多项权限。构建时，库 manifest 会合并进宿主 App；库里的 targetSdk 不会把最终应用固定在 31。最终 App target 37 后，平台按宿主的目标版本执行新规则。

合并 manifest 时要特别审查：

- `READ_EXTERNAL_STORAGE`、`WRITE_EXTERNAL_STORAGE`：target 30 及以上不能靠 `requestLegacyExternalStorage` 恢复旧存储模型。文件工具应使用应用私有目录、SAF（Storage Access Framework，由用户选择文件）或受控的测试导出路径。
- `SYSTEM_ALERT_WINDOW`：这是允许界面显示在其他 App 上方的特殊权限。能用应用内悬浮层完成的调试包，优先避免请求系统级悬浮窗。
- `POST_NOTIFICATIONS`：库没有声明。target 33 及以上若依赖通知展示状态，需要由宿主声明并按产品流程请求；拒绝通知时功能也应可诊断。
- `FOREGROUND_SERVICE_MEDIA_PROJECTION`：库的录屏 service 标了 `mediaProjection` 类型，却没有 Android 14 起所需的对应前台服务权限。宿主还要先通过 `createScreenCaptureIntent()` 让用户授权，再按规定启动服务；不准备维护这套流程时应禁用录屏工具。
- `READ_PHONE_STATE`、`CAMERA`、Wi-Fi 与存储权限：若团队不用对应 kit，应在 Debug manifest 中用 manifest merger（清单合并）规则移除，减少测试包权限范围。

AAR 还声明了未导出的 `FileProvider`，authority（ContentProvider 的唯一名称）为 `${applicationId}.debugfileprovider`，其 paths 配置是 `<root-path path="" />`。即使 provider 不导出，获得临时 URI grant（单个 URI 的临时访问授权）的接收方仍可读取被授予的文件。只在受控测试包启用文件能力，并检查分享目标、可生成的 URI 范围和日志。

库中附带 `dokit_network_config.xml`，内容允许明文 HTTP 流量，但核心 manifest 没有自动引用它。风险判断应看最终合并 manifest：只有宿主把它设为 `android:networkSecurityConfig` 时，这条明文策略才会生效。

### Native 库与 16 KB 页

3.7.11 的核心 `dokitx` AAR 不含 `.so`，这个结果不能外推到所有可选模块：

- `dokitx-gps-mock` 带多 ABI（CPU 架构）的 native 库。3.7.11 AAR 中 6 个 arm64 `.so` 的 ELF `LOAD` 段对齐均为 `0x10000`（64 KB），满足 16 KB 的 ELF 对齐要求；最终 APK/AAB 的 ZIP 条目对齐和设备安装运行仍要另测。
- `dokitx-pthread-hook` 会传递依赖 Matrix 2.0.2 的 hooks / fd 模块。`matrix-hooks` 与 `matrix-fd` AAR 中 6 个 arm64 `.so` 的 `LOAD` 对齐均为 `0x1000`（4 KB），不满足 16 KB ELF 对齐要求。

面向 Android 17 的项目如果启用这些可选模块，应展开完整依赖图，替换或重新编译 4 KB native 依赖，再对最终 APK/AAB 运行 16 KB 检查。这里要分别检查 ELF `LOAD` 段、包内 ZIP 对齐和目标设备运行。

早期审阅记录使用过 `android17-6.18-2026-06_r6`，截至本次复核同系列已到 `r39`。common kernel tag 只能说明 AOSP 通用内核代码版本，不能代替 App 原生库与量产设备验证；vendor kernel（设备厂商内核）和实际页大小仍以目标机为准。

## DoKit 的“断网”仍会发送真实请求

3.7.11 的 `DokitWeakNetworkInterceptor` 是 OkHttp network interceptor，运行在实际网络交换附近。几个模式要按源码执行顺序理解：

| 模式 | 代码做了什么 | 能测试什么 | 不能测试什么 |
|---|---|---|---|
| 断网 | 先调用 `chain.proceed(chain.request())`；真实请求成功后，丢弃其响应内容并构造 HTTP 400 | UI 收到 400 响应后的状态 | 请求未出网、`UnknownHostException`、无服务端副作用 |
| 超时 | 先 sleep 配置时长，再执行真实请求；真实请求成功后构造 HTTP 400 | 页面延迟一段时间后收到错误码 | `SocketTimeoutException`、连接超时、读取超时 |
| 限速 | 包装请求/响应 Body，按 KB 窗口 sleep | 大 Body 慢速读写时的 UI 表现 | DNS、TCP、TLS、丢包、切网、无线电状态 |

如果底层真实请求本身抛出异常，异常会直接向上返回，DoKit 不会生成 HTTP 400。更危险的情况是请求成功：所谓“断网”和“超时”都会让真实请求到达服务端，只把 App 最后看到的结果改成 400。支付、下单、创建、删除、上传、统计事件（埋点）等会改变服务端状态的操作不得用这两个模式测试；界面可能显示失败，服务端却已成功执行，用户重试还会再提交一次。

要验证 `IOException`、`UnknownHostException`、`SocketTimeoutException` 分支，可使用受控测试服务器、MockWebServer、网络代理或系统级网络条件，按目标异常构造真实失败。DoKit 弱网只适合安全、幂等的接口；幂等表示同一请求重复执行不会产生额外业务结果。它也可用于观察慢 Body 对页面状态的影响。

## Mock：替换响应之前会先执行真实请求

`DokitMockInterceptor.intercept()` 同样会先执行 `chain.proceed(oldRequest)`。命中本地规则后，它再向 Mock 平台发出第二个 GET 请求，用平台数据替换 App 最终收到的响应。这里的 Mock 发生在真实请求之后，不是请求发出前的短路。

这带来三个直接后果：

- DoKit 不会在客户端拦下原请求；真实网络允许时，它会到达业务后端。
- 命中规则时还会多一次对 Mock 平台的请求。
- 应用看到的是 Mock 响应，服务端状态却可能已经改变。

因此，DoKit Mock 适合在无副作用的查询接口上检查空列表、字段缺失、超大列表和错误码页面。对下单、支付、发帖、删数据、上传等接口，应改用测试环境的服务端 Mock、通过依赖注入替换 repository（数据访问层），或使用能在发请求前直接返回的自建 interceptor。

## 一个可复现的网络测试场景

以商品列表页为例，目标是检查慢响应、缓存和降级逻辑，不碰状态修改接口：

| 步骤 | 条件 | 观察点 | 合格标准 |
|---|---|---|---|
| 正常条件 | 测试环境、正常网络 | 首屏、分页、图片与缓存 | 记录请求顺序，作为后续场景的对照；不把浮窗值当性能基准 |
| 慢 Body | DoKit 对 GET 列表接口限速 | loading、取消请求、页面退出 | 无主线程阻塞，退出后不更新旧页面 |
| HTTP 400 | DoKit“断网”模式，仅用于该幂等 GET | 错误页、重试入口 | 文案正确，不清掉可用缓存 |
| 空列表 | Mock 平台或本地 repository 返回空数组 | 无数据页面与统计事件 | 不应崩溃，不误显示网络错误 |
| 大列表 | Mock 返回上限数据 | 列表差量计算（diff）、布局、图片请求 | 用 Perfetto / Macrobenchmark 复核卡顿 |
| 真实超时 | MockWebServer 或代理制造 read timeout（读取超时） | 异常分类、逐步延长间隔的重试策略 | 命中 `SocketTimeoutException` 分支，重试次数受控 |

每轮记录应用版本、设备、账号、接口环境、DoKit 开关和操作路径。开发拿到这些条件后，才能复现场景并录制 Perfetto trace 或 Profiler 数据。

## DoKit 面板与专项工具如何分工

| 工具 | 适合回答 | 何时改用该工具 |
|---|---|---|
| Android Studio Profiler | 方法调用、对象分配、heap dump、进程内存与网络细节 | 已找到 CPU 或内存突变的操作 |
| Perfetto | 主线程、RenderThread、GPU、Binder（Android 进程间通信）、调度、I/O、FrameTimeline 的时间关系 | 已有稳定复现路径，需要判断事件的先后与因果关系 |
| JankStats | 带 App 状态标签的 jank（视觉卡顿/慢帧）事件 | 要把页面、交互状态与慢帧关联 |
| FrameMetrics | Window 帧耗时及 layout、draw、sync 等阶段 | 要检查单个窗口内帧耗时构成 |
| Macrobenchmark | 在独立测试进程中重复测量启动、滚动与交互 | 修复前后需要同设备、同条件的统计比较 |
| OkHttp `EventListener` | DNS、connect、TLS、请求与响应阶段 | DoKit 网络列表只显示总体请求信息 |

可以按下面的顺序处理：

1. 测试用 DoKit 记下异常页面、账号、手势、网络条件和请求。
2. 用安全的幂等接口或专用测试环境把问题稳定复现。
3. 开发按问题类型录制 Perfetto、Profiler、heap dump 或网络阶段数据。
4. 修复后用同一路径做专项测量，再回 DoKit 快速确认主要流程仍可用。

DoKit 缩短“发现到复现”的时间，专项工具负责定位原因和比较修复前后的结果。

## 出站数据与隐私边界

DoKit 不能按“纯本地面板”审查。3.7.11 的运行时默认把 `DoKitManager.ENABLE_UPLOAD` 设为 true，初始化时会尝试上传包名、应用名、版本、DoKit 版本、系统类型和语言等接入信息；内置工具使用统计、“健康体检”和 Mock 还有各自的平台请求。

3.7.11 source JAR 中写死的目的地址包括：

- `https://doraemon.xiaojukeji.com/uploadAppData`
- `https://www.dokit.cn/pointData/addPointData`
- `https://www.dokit.cn/healthCheck/addCheckData`

空 `productId`（DoKit 平台项目 ID）不会自动关闭默认统计，应显式调用 `disableUpload()`。2026-08-14 从当前审阅环境探测时，`doraemon.xiaojukeji.com` 返回自签名证书，两个 `www.dokit.cn` 地址均未完成 TLS 握手。这不是所有网络环境下的可用性结论，但足以说明接入时必须重查证书、服务状态、数据保留方式和企业网络准入策略。需要平台能力时，应按外部服务管理；不需要时，关闭相关功能并抓包验证没有请求发出。

网络面板还可能记录 URL、Header、token（访问凭据）、Cookie、请求 Body 和响应 Body。截图、日志导出与文件分享会让更多人或系统接触这些数据。测试账号也可能含真实用户信息，包名带 `debug` 不能代替隐私审查。

## Release 隔离：依赖与最终包都要查

3.7.11 的 no-op AAR 只保留一组空实现 API，manifest 只有 minSdk/targetSdk 信息，适合作为 Release 编译占位。它无法防止开发者误加完整运行时、可选模块或本地重打包 AAR，因此 CI（持续集成任务）要同时检查解析后的依赖和成品内容。

下面的 Gradle 任务检查 `releaseRuntimeClasspath`（Release 运行时依赖集合），只允许 `dokitx-no-op`，发现其他 DoKit 模块就让构建失败：

```kotlin
import org.gradle.api.artifacts.component.ModuleComponentIdentifier

tasks.register("verifyReleaseWithoutDoKitRuntime") {
    doLast {
        val components = configurations
            .getByName("releaseRuntimeClasspath")
            .incoming.resolutionResult.allComponents
            .mapNotNull { it.id as? ModuleComponentIdentifier }

        val forbidden = components.filter {
            it.group == "io.github.didi.dokit" &&
                it.module != "dokitx-no-op"
        }

        check(forbidden.isEmpty()) {
            "Release contains DoKit runtime modules: ${forbidden.joinToString()}"
        }
    }
}
```

多 flavor 工程要为每个正式变体生成对应检查，不能把 configuration（Gradle 依赖集合）名写死后只覆盖一个包。依赖图检查通过后，还要解开最终 APK/AAB 搜索 DoKit 类、组件、权限、资源与 native 库；本地 AAR、shade（把依赖类复制进另一个包）或重打包都可能绕过 Maven groupId 规则。

发布前至少完成这些检查：

- 依赖：正式变体只有 no-op，未包含完整 `dokitx`、插件产物和可选 native 模块。
- 代码与资源：没有 `DoKitReal`、`UniversalActivity`、面板资源、自定义 kit、测试账号菜单、隐藏调试手势和调试 deep link（用 URL/Intent 直接打开页面的入口）。
- Manifest：没有多余的悬浮窗、存储、电话、相机、Wi-Fi、录屏前台服务权限或宽路径 FileProvider。
- 网络：没有 DoKit 统计、健康检查、Mock 平台、网络代理和测试域名请求。
- 数据：没有内网地址、token、Cookie、用户数据、Mock 数据和诊断日志留在 assets、res 或包内数据库。
- 行为：在全新设备、升级安装、通知拒绝、无悬浮窗权限和后台启动限制下测试正式包。
- Native：启用过 GPS mock、pthread hook 等模块时，检查最终包 ABI、16 KB ELF / ZIP 对齐和目标设备运行。

Release 隔离最终要验收签名后的 APK/AAB，Gradle 文件里的依赖声明只能作为其中一项证据。

## 团队如何使用 DoKit

| 角色 | 现场动作 | 应交付的信息 |
|---|---|---|
| 测试 | 切测试环境、查看请求、构造安全的弱网/Mock 条件 | 版本、设备、账号、环境、开关、复现步骤、请求标识 |
| 业务开发 | 检查网络、本地数据和业务状态，增加短期诊断 kit | 初步假设、相关代码路径、需抓取的专项数据 |
| 性能专项 | 固定路径，关闭无关 kit，录制 trace 或运行 benchmark（基准测试） | trace、指标算法、设备条件、修复前后对比 |
| 安全与发布 | 审查权限、组件、出站域名、日志和最终产物 | 依赖与成品扫描记录、风险处置结果 |

团队还应约定三条纪律：

- 新增自定义 kit 时写明负责人、适用环境、数据范围和移除条件。
- 测试报告记录启用的 DoKit 功能；浮窗、网络记录和 hook 都可能改变结果。
- 性能复核包只打开当前调查所需能力，避免多个采集器互相干扰。

## 小结

DoKit 的优势是把调试入口和测试条件带到设备现场。它可以帮助团队更快找到异常页面、稳定复现步骤，并把网络、本地状态和业务诊断入口集中管理。

在 Android 17 / API 37 工程中，接入前要确认几个限制：公开 3.7.11 插件仍依赖已从 AGP 8 移除的 Transform API；运行时使用 hidden API hook；旧 manifest 需要按 target 37 重审；弱网与 Mock 都会先发送真实请求；可选 native 模块还可能引入不满足 16 KB 对齐的依赖。

可执行的接入方式是：Debug / QA 变体按需启用，默认关闭上传，只在安全接口上构造网络条件；DoKit 找到复现路径后，再用 Perfetto、Profiler、JankStats、FrameMetrics 或 Macrobenchmark 验证。Release 是否隔离成功，要以最终 APK/AAB 不含 DoKit 实现、入口、权限、数据和出站行为为准。

## 参考资料

- [DoKit 官方仓库](https://github.com/didi/DoKit)
- [DoKit Android 接入说明](https://github.com/didi/DoKit/blob/master/Android/README.md)
- [DoKit `master` 审阅提交](https://github.com/didi/DoKit/tree/626827cddb2feb2f3aee87a52a064b4e5ca2bed4)
- [`master` 固定提交的 `Android/config.gradle`](https://github.com/didi/DoKit/blob/626827cddb2feb2f3aee87a52a064b4e5ca2bed4/Android/config.gradle)
- [GitHub `3.1.7`（iOS）release](https://github.com/didi/DoKit/releases/tag/3.1.7)
- [Maven Central：dokitx 元数据](https://repo.maven.apache.org/maven2/io/github/didi/dokit/dokitx/maven-metadata.xml)
- [Maven Central：dokitx 3.7.11 POM](https://repo.maven.apache.org/maven2/io/github/didi/dokit/dokitx/3.7.11/dokitx-3.7.11.pom)
- [Maven Central：dokitx 3.7.11 AAR](https://repo.maven.apache.org/maven2/io/github/didi/dokit/dokitx/3.7.11/dokitx-3.7.11.aar)
- [Maven Central：dokitx 3.7.11 source JAR](https://repo.maven.apache.org/maven2/io/github/didi/dokit/dokitx/3.7.11/dokitx-3.7.11-sources.jar)
- [Maven Central：dokitx-plugin 3.7.11 source JAR](https://repo.maven.apache.org/maven2/io/github/didi/dokit/dokitx-plugin/3.7.11/dokitx-plugin-3.7.11-sources.jar)
- [Maven Central：dokitx-gps-mock 3.7.11 AAR](https://repo.maven.apache.org/maven2/io/github/didi/dokit/dokitx-gps-mock/3.7.11/dokitx-gps-mock-3.7.11.aar)
- [Maven Central：dokitx-pthread-hook 3.7.11 POM](https://repo.maven.apache.org/maven2/io/github/didi/dokit/dokitx-pthread-hook/3.7.11/dokitx-pthread-hook-3.7.11.pom)
- [Maven Central：Matrix hooks 2.0.2 AAR](https://repo.maven.apache.org/maven2/com/tencent/matrix/matrix-hooks/2.0.2/matrix-hooks-2.0.2.aar)
- [Maven Central：Matrix fd 2.0.2 AAR](https://repo.maven.apache.org/maven2/com/tencent/matrix/matrix-fd/2.0.2/matrix-fd-2.0.2.aar)
- [Android Gradle Plugin API 更新：Transform API](https://developer.android.com/build/releases/gradle-plugin-api-updates)
- [Android 14 前台服务类型要求](https://developer.android.com/about/versions/14/changes/fgs-types-required)
- [Android 13 通知运行时权限](https://developer.android.com/develop/ui/views/notifications/notification-permission)
- [Android 11 分区存储变更](https://developer.android.com/about/versions/11/privacy/storage)
- [Android 16 KB 页支持指南](https://developer.android.com/guide/practices/page-sizes)
- [`android-17.0.0_r1`：`ActivityThread.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/app/ActivityThread.java)
- [`android-17.0.0_r1`：`Handler.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/os/Handler.java)
- [`android-17.0.0_r1`：`Looper.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/os/Looper.java)
- [`android17-6.18-2026-06_r39` current common kernel tag](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r39/)
- [`android17-6.18-2026-06_r6` common kernel](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/)
