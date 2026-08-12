---
title: "DoraemonKit / DoKit"
chapter: "19"
section: "19.06"
status: finalized
applicable_versions: "版本需按 artifact / AndroidX / Gradle / AGP 单独验证；README 明确覆盖 3.5.0 / 3.5.0.1 与 AGP 3.3.0+"
last_verified: "2026-04-27"
last_verified_against: "didi/DoKit README + Android/README + DoKitPlugin.kt + Okhttp3ClassTransformer.kt + PerformanceDataManager.java"
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

DoraemonKit（DoKit）把网络查看、弱网、Mock、文件与数据库浏览、日志、性能浮窗、UI 检查和业务自定义入口放进同一个 Android 调试包。测试人员可以在手机上改变测试条件，开发人员可以在同一路径下查看请求与进程状态，这正是它最擅长的场景。

这类便利也会改变被测环境。浮窗需要绘制，性能面板会轮询，网络模块会插入 interceptor，部分功能还依赖编译期插桩或隐藏 API。DoKit 适合回答“哪个页面、哪个操作或哪个网络条件值得继续调查”，不能据此发布版本级性能结论，更不该负责生产 APM 的采集任务。

平台审阅锚点为 Android 17 / API 37 / `android-17.0.0_r1`。DoKit 没有面向 API 37 的官方兼容承诺，因此这里的“可用”只表示某项实现经过源码分析后具备试接条件，仍需在项目自己的 AGP、依赖图、设备和最终安装包上验证。

## 先认清公开版本与源码边界

截至 2026 年 7 月，DoKit 的公开资料存在三条不同时间线：

| 对象 | 可核对状态 | 工程判断 |
|---|---|---|
| 官方 README | 示例仍以 `3.5.0`、`3.5.0.1` 和 AGP 3.3.0+ 为主 | 只能说明旧接入方式，不能证明 AGP 8/9 或 API 37 兼容 |
| Maven Central | `dokitx`、`dokitx-plugin`、`dokitx-no-op` 的 release 均为 `3.7.11`，仓库元数据更新时间为 2023-02-06 | 引入公开制品时应按 3.7.11 的 AAR、POM 和 source JAR 审计 |
| GitHub `master` | 审阅提交为 `626827cddb2feb2f3aee87a52a064b4e5ca2bed4`；工程内版本号已高于公开制品 | `master` 可帮助理解后续修订，但不能替代 3.7.11 发布物的行为 |

3.7.11 的 POM 仍依赖 Kotlin 1.4.32、OkHttp 3.14.7 和较早的 AndroidX 组件。依赖解析成功只代表 Gradle 找到了制品；它没有证明这些旧依赖与当前工程的 Kotlin、R8、AndroidX 或 targetSdk 37 组合可用。

审阅第三方调试 SDK 时，应固定以下四样材料：

- Maven POM：确认传递依赖。
- AAR 与合并后的 manifest：确认权限、组件、资源和 native 库。
- 同版本 source JAR：确认运行语义。
- 最终 APK/AAB：确认 Release 变体里留下了什么。

不要用 GitHub `master` 的代码替公开 3.7.11 背书，也不要把 README 的 AGP 下限理解为对所有更高版本的承诺。

## 能力地图：每项能力能回答什么

| 能力 | 主要使用者 | 适合现场 | 不适合下的结论 |
|---|---|---|---|
| FPS、CPU、内存浮窗 | 开发、性能专项 | 在手工路径中找到数值突变的位置 | 版本帧率、CPU 或内存达标 |
| 网络查看 | 测试、开发 | 核对 URL、Header、Body、响应和图片大小 | DNS、连接、TLS 各阶段的精确耗时 |
| 弱网 | 测试、开发 | 在安全接口上观察慢请求、慢 Body 和页面等待 | 还原真实蜂窝网络、丢包、切网或系统超时 |
| Mock | 测试、开发 | 让 UI 消费指定响应，检查空态和容错页面 | 阻止原请求到达服务端，或验证网络异常类型 |
| 文件、数据库、日志 | 开发、测试 | 检查本地缓存、数据库迁移和业务状态 | 证明线上数据安全或并发写入正确 |
| 环境切换、业务入口 | 开发、测试 | 统一收纳测试域名、清缓存、诊断页 | 作为面向用户的运维入口 |
| UI 层级、取色、边界 | 客户端开发、UI QA | 检查控件信息和布局问题 | 替代可访问性、截图或渲染基准测试 |
| 卡顿、启动、函数耗时 | 开发、性能专项 | 找到值得抓 trace 的路径 | 给出可跨设备比较的性能结果 |

这张表的读法很简单：DoKit 提供线索和测试条件，专项工具提供可复核证据。

## 接入由运行时 AAR 和编译插件两部分组成

`dokitx` 是运行时工具箱，`dokitx-plugin` 负责字节码改写。3.7.11 的插件在 `DoKitPlugin.kt` 中取得旧版 `AppExtension` / `LibraryExtension`，随后调用 `registerTransform()`。Android Gradle Plugin 7.2 已弃用 Transform API，AGP 8.0 将它移除；API 37 项目常用的现代 AGP 不能直接套用这条插件链路。

插件还有一个容易漏掉的变体问题。它通过顶层 Gradle task 名是否包含 `release` / `Release` 判断 Release 构建。执行 `assembleRelease` 时通常能命中，执行 `assemble` 这类聚合任务时却可能返回 false，插件仍可能注册 Transform。它不能负责 Release 隔离的安全边界。

可以按能力拆开决策：

| 接入方式 | 可以保留 | 会失去或需要另做 |
|---|---|---|
| 只接 `dokitx` 运行时 AAR | 面板、自定义 kit、部分本地工具 | 依赖 ASM 的 OkHttp 注入、函数耗时、部分启动采集 |
| 接 3.7.11 原插件 | 旧 AGP 项目中的字节码能力 | 不适用于 AGP 8+；还要验证变体隔离和构建稳定性 |
| 维护内部 fork | 可按项目需要迁移字节码能力 | 要改用 Android Components 的 Instrumentation / Artifacts API，并维护版本测试 |
| Release 接 `dokitx-no-op` | 共享源码可继续引用 DoKit API | no-op 只能降低误引用成本，仍要检查最终产物 |

如果团队不准备维护插件 fork，在 API 37 工程中更稳妥的选择是只评估运行时 AAR，把字节码类功能交给 Perfetto、Macrobenchmark、Profiler 或网络库自身的调试 interceptor。

## Debug-only 的工程结构

依赖要按变体声明。下面的例子以 Maven Central 公开的 3.7.11 为审计对象，并有意不应用旧插件：

```kotlin
dependencies {
    debugImplementation("io.github.didi.dokit:dokitx:3.7.11")
    releaseImplementation("io.github.didi.dokit:dokitx-no-op:3.7.11")
}
```

这种写法让 Release 源码仍能解析 DoKit 的 API，但不会带入完整运行时。若项目有 `internal`、`qa`、`benchmark` 等 flavor，应逐个声明允许的变体，不要假设 `debugImplementation` 会自动符合所有组合。

业务代码也不宜四处直接打开 DoKit 页面。下面的接口把业务诊断入口收在一个注册点，Release 实现什么也不做：

```kotlin
interface DevToolRegistry {
    fun register(name: String, action: () -> Unit)
}

class NoopDevToolRegistry : DevToolRegistry {
    override fun register(name: String, action: () -> Unit) = Unit
}
```

Debug 实现可以把“切换接口环境”“清理指定缓存”“打开当前页面状态”“导出诊断日志”注册为自定义 kit；Release 注入 `NoopDevToolRegistry`。这样既能保留共享业务代码，也不会把 DoKit 类型扩散到各个功能模块。

初始化时应主动关闭默认使用统计。下面的调用放在允许 DoKit 的 source set 中，`customKits` 接收项目自己的 `AbstractKit` 列表：

```kotlin
DoKit.Builder(this)
    .disableUpload()
    .customKits(internalKits)
    .alwaysShowMainIcon(false)
    .build()
```

`disableUpload()` 关闭的是 DoKit 的默认接入量与使用统计开关。它不等于关闭健康检查、Mock 平台或业务自定义 kit 发出的全部请求，仍需通过抓包核对测试包的出站流量。

## 性能面板：数据从哪里来

### FPS

3.7.11 的 `PerformanceDataManager` 注册连续的 `Choreographer.FrameCallback`，每次回调把计数加一；主线程上的另一个 `Handler` 任务按 1000 ms 读取并清零计数。显示刷新率取自 `defaultDisplay.refreshRate`，当前值会被该刷新率限制。

这里有两个口径陷阱：

- 统计任务也在主线程。主线程堵塞时，“一秒窗口”可能延后执行，但代码没有按真实经过时间归一化。
- 健康检查上传路径还会把帧率上限压到 60。90 Hz、120 Hz 设备上的信息会丢失。

因此，浮窗 FPS 能提示“这次滑动明显异常”，不能回答慢帧发生在哪个阶段，也不能替代 FrameTimeline 或 JankStats。

### CPU

Android 8.0 及以上，DoKit 每 500 ms 执行一次 `top -n 1`，查找当前 PID 所在行，再把 `%CPU` 按 `availableProcessors()` 归一化；更早系统读取 `/proc/stat` 与 `/proc/<pid>/stat`。

`top` 的输出格式不是 Android SDK 契约，命令执行本身也会制造开销。按核数归一化后的百分比与 Profiler、Perfetto 或其他监控库未必同口径。它适合发现“某一步骤 CPU 持续抬高”，不适合拿几次浮窗读数做版本对比。

### 内存

Android 10 及以上，DoKit 每 500 ms 调用 `Debug.getMemoryInfo()`，展示 `totalPss / 1024` 的 MB 值；较低版本使用 `ActivityManager.getProcessMemoryInfo()`。

PSS 是进程在采样时刻的物理内存分摊值。它不会告诉你哪个对象仍被引用，也不能把一次上涨直接判为泄漏。需要解释 Java/Kotlin 对象时看 heap dump 和引用链；需要解释进程整体内存时，再结合 `dumpsys meminfo`、Perfetto 和 native 分配信息。

### 网络流量

DoKit 每 500 ms 读取 `NetworkManager` 中累计的请求与响应字节数，再计算窗口差值。数据来自被 DoKit hook 或 interceptor 覆盖的网络栈，并非系统为整个 UID 统计的全部流量。

3.7.11 插件能给 OkHttp / HttpURLConnection 路径插入采集逻辑，但现代 AGP 项目如果不加载该插件，覆盖面会随之缩小。健康检查代码还有对响应调用 `peekBody(Long.MAX_VALUE)` 的路径，大响应可能被复制进内存，反过来干扰内存与网络测试。

网络面板适合确认“哪个请求、哪类 Body 值得查”，精确分解 DNS、connect、TLS、请求发送和响应读取时，应使用 OkHttp `EventListener`、服务端 trace 或系统 trace。

### 启动、函数耗时与卡顿

启动和函数耗时很依赖插件插桩；没有插件时不能假设这些面板仍保留完整能力。即便插件可运行，Debug 构建、插桩和浮窗也会改变启动与方法耗时，发布结论应回到 Macrobenchmark 与 Perfetto。

DoKit 自带的卡顿监控也有明确边界：

- 阈值固定为 200 ms。
- 堆栈采样在 300 ms 后开始，并继续以 300 ms 间隔采样。
- 200～300 ms 的主线程事件可能已越过阈值，却因没有采到堆栈而被丢弃。
- `MonitorCore` 依赖 `Looper.setMessageLogging()` 的开始/结束日志，并以 `System.currentTimeMillis()` 和线程 CPU 时间计时。
- 堆栈最多保留 100 份，连续相同的堆栈会被过滤。

Android 17 的 `Looper` 仍只有一个 `mLogging` / `setMessageLogging()` 日志出口。DoKit 的卡顿与 TimeCounter 模块还会互相停用或把 logger 设为 null，也可能覆盖应用内另一个使用相同接口的监控器。现场没看到记录，不代表没有卡顿；看到一份堆栈，也只代表某个采样时刻。

## Android 17 上的运行时兼容边界

### 隐藏 API 与主线程 Handler hook

3.7.11 的 `DoKitReal.install()` 会在主进程调用 `HandlerHooker.doHook()`。Android 9 及以上，它先通过 FreeReflection 尝试解除隐藏 API 限制，再反射：

- `ActivityThread.currentActivityThread`
- `ActivityThread.mH`
- `Handler.mCallback`

`android-17.0.0_r1` 源码中这些成员仍存在，但它们不是公开 SDK 契约。字段“还在”不等于第三方应用可以稳定访问；隐藏 API 执行策略、OEM 改动、反射库行为或应用加固都可能让 hook 失败。DoKit 捕获异常能减少崩溃，却也可能留下功能静默失效的情况。

公开 3.7.11 还在 Android 12 及以上关闭了一条 SandHook 全局 runtime hook 路径，源码注释直接记录了 Android S 崩溃问题。这说明兼容策略本身带有历史补丁色彩。API 37 设备至少要覆盖冷启动、Activity 跳转、横竖屏、分屏、前后台切换和加固包回归，不能只验证面板能打开。

### Manifest、权限与前台服务

3.7.11 核心 AAR 的 manifest 仍以 `targetSdkVersion 31` 发布，并声明了网络、Wi-Fi、存储、电话状态、相机、悬浮窗、前台服务和唤醒锁等多项权限。库的 targetSdk 不会把最终应用固定在 31；最终 App target 37 后，平台按应用的目标版本执行新规则。

合并 manifest 时要特别审查：

- `READ_EXTERNAL_STORAGE`、`WRITE_EXTERNAL_STORAGE`：target 30 及以上不能靠 `requestLegacyExternalStorage` 恢复旧存储模型。文件工具应改走应用私有目录、SAF 或受控的测试导出路径。
- `SYSTEM_ALERT_WINDOW`：这是特殊权限。能用应用内悬浮层完成的调试包，优先避免请求系统级悬浮窗。
- `POST_NOTIFICATIONS`：库没有声明。target 33 及以上若依赖通知展示状态，需要由宿主声明并按产品流程请求；拒绝通知时功能也应可诊断。
- `FOREGROUND_SERVICE_MEDIA_PROJECTION`：库的录屏 service 标了 `mediaProjection` 类型，却没有 Android 14 起所需的对应权限与完整启动约束。宿主要补齐权限和授权时序，或禁用录屏工具。
- `READ_PHONE_STATE`、`CAMERA`、Wi-Fi 与存储权限：若团队不用对应 kit，应在 Debug manifest 中用 manifest merger 规则移除，减少测试包权限面。

AAR 还声明了未导出的 `FileProvider`，authority 为 `${applicationId}.debugfileprovider`，其 paths 配置使用根路径。即使 provider 不导出，获得临时 URI grant 的接收方也可能访问被授予的广泛路径。只在受控测试包启用文件能力，并检查分享目标、URI 范围和日志。

库中附带 `dokit_network_config.xml`，内容允许明文流量，但核心 manifest 没有自动引用它。风险判断应看最终合并 manifest：如果宿主主动把它设为 `networkSecurityConfig`，才会把明文策略带入应用。

### Native 库与 16 KB 页

3.7.11 的核心 `dokitx` AAR 不含 `.so`，不能据此推断所有可选模块都没有 native 风险：

- `dokitx-gps-mock` 带多 ABI 的 native 库。抽查 arm64 ELF 的 `LOAD` 对齐为 `0x10000`，但还要验证最终 APK/AAB 的 ZIP 对齐和安装运行。
- `dokitx-pthread-hook` 会传递依赖 Matrix 2.0.2 的 hook / fd 模块。该版本 arm64 `.so` 的 `LOAD` 对齐仍为 `0x1000`，不能视为 16 KB ELF 对齐。

面向 Android 17 的项目如果启用这些可选模块，应展开完整依赖图，替换或重编 4 KB native 依赖，再对最终制品运行 16 KB 检查。该问题属于 ELF、打包和设备运行时兼容性；Android common kernel 的审阅锚点为 `android17-6.18-2026-06_r6`，量产设备采用的 vendor kernel 与配置仍以目标设备为准。

## 弱网：名称很像断网，语义并不是断网

3.7.11 的 `DokitWeakNetworkInterceptor` 是 OkHttp network interceptor。它的几个模式需要按源码语义理解：

| 模式 | 代码做了什么 | 能测试什么 | 不能测试什么 |
|---|---|---|---|
| 断网 | 先调用 `chain.proceed(realRequest)`，再丢弃真实结果并返回人造 HTTP 400 | UI 面对 400 响应的状态 | 请求未出网、`UnknownHostException`、无服务端副作用 |
| 超时 | 先 sleep 配置时长，随后执行真实请求，再返回人造 HTTP 400 | 页面等待后收到错误码 | `SocketTimeoutException`、连接超时、读取超时 |
| 限速 | 包装请求/响应 Body，按 KB 窗口 sleep | 大 Body 慢速读写时的 UI 表现 | DNS、TCP、TLS、丢包、切网、无线电状态 |

这里最重要的事实是：所谓“断网”和“超时”都会执行真实请求。支付、下单、创建、删除、上传、埋点等有副作用操作不得用这两个模式测试。用户界面可能看到失败，服务端操作却已经成功，重试还可能再执行一次。

要验证 `IOException`、`UnknownHostException`、`SocketTimeoutException` 分支，可使用受控测试服务器、MockWebServer、网络代理或系统级网络条件，按目标异常构造真实失败。DoKit 弱网更适合安全、幂等的测试接口，以及慢 Body 对页面状态的影响。

## Mock：替换响应之前，真实请求已经发送

`DokitMockInterceptor.intercept()` 同样会先执行 `chain.proceed(oldRequest)`。命中本地规则后，它再向 Mock 平台发出第二个 GET 请求，用平台返回的数据替换应用收到的响应。

这带来三个直接后果：

- 原请求总会到达业务后端。
- 命中规则时还会多一次对 Mock 平台的请求。
- 应用看到的是 Mock 响应，服务端状态却可能已经改变。

因此，DoKit Mock 适合在无副作用的查询接口上检查空列表、字段缺失、超大列表和错误码页面。对下单、支付、发帖、删数据、上传等接口，应改用测试环境的服务端 Mock、依赖注入替换 repository，或在发请求前完成短路的自建 interceptor。

## 一个可复现的网络测试场景

以商品列表页为例，目标是检查慢响应、缓存和降级逻辑，不碰状态修改接口：

| 步骤 | 条件 | 观察点 | 合格标准 |
|---|---|---|---|
| 基线 | 测试环境、正常网络 | 首屏、分页、图片与缓存 | 记录请求顺序，不把浮窗值作为基准 |
| 慢 Body | DoKit 对 GET 列表接口限速 | loading、取消请求、页面退出 | 无主线程阻塞，退出后不更新旧页面 |
| HTTP 400 | DoKit“断网”模式，仅用于该幂等 GET | 错误页、重试入口 | 文案正确，不清掉可用缓存 |
| 空列表 | Mock 平台或本地 repository 返回空数组 | 空态与埋点 | 不应崩溃，不误显示网络错误 |
| 大列表 | Mock 返回上限数据 | diff、布局、图片请求 | 用 Perfetto / Macrobenchmark 复核卡顿 |
| 真实超时 | MockWebServer 或代理制造 read timeout | 异常分类、退避重试 | 命中 `SocketTimeoutException` 分支，重试次数受控 |

每轮记录应用版本、设备、账号、接口环境、DoKit 开关和操作路径。开发拿到这份记录后，才能在同一条件下抓 Perfetto 或 Profiler。

## DoKit 面板与专项工具如何分工

| 工具 | 适合回答 | DoKit 何时交棒 |
|---|---|---|
| Android Studio Profiler | 方法调用、对象分配、heap dump、进程内存与网络细节 | 已找到 CPU 或内存突变的操作 |
| Perfetto | 主线程、RenderThread、GPU、binder、调度、I/O、FrameTimeline 的时间关系 | 已有稳定复现路径，需要系统级因果证据 |
| JankStats | 带 App 状态标签的 jank 事件 | 要把页面、交互状态与慢帧关联 |
| FrameMetrics | Window 帧耗时及 layout、draw、sync 等阶段 | 要检查单个窗口内帧耗时构成 |
| Macrobenchmark | 可重复的启动、滚动与交互指标 | 修复前后需要同设备、同条件的统计比较 |
| OkHttp `EventListener` | DNS、connect、TLS、请求与响应阶段 | DoKit 网络列表只显示总体请求信息 |

推荐动作链是：

1. 测试用 DoKit 记下异常页面、账号、手势、网络条件和请求。
2. 用安全的幂等接口或专用测试环境把问题稳定复现。
3. 开发按问题类型抓 Perfetto、Profiler、heap dump 或网络阶段数据。
4. 修复后用同一路径做专项测量，再回 DoKit 做快速冒烟。

DoKit 缩短“发现到复现”的时间，专项工具负责定因和比较。

## 出站数据与隐私边界

DoKit 不能按“纯本地面板”审查。3.7.11 的运行时默认把 `DoKitManager.ENABLE_UPLOAD` 设为 true，初始化时可能上传包名、应用名、版本、DoKit 版本、系统类型和语言等接入信息；内置工具使用、健康检查和 Mock 也有各自的平台请求。

公开源码中可见的目的地址包括：

- `https://doraemon.xiaojukeji.com/uploadAppData`
- `https://www.dokit.cn/pointData/addPointData`
- `https://www.dokit.cn/healthCheck/addCheckData`

空 `productId` 不会自动关闭默认统计，应显式调用 `disableUpload()`。这些公网服务的证书、可用性、数据保留和企业网络策略需要在接入时重新核对；某次探测成功或失败都不能替未来可用性作承诺。需要平台能力时，把它当外部依赖管理；不需要时，关闭开关并抓包验证。

网络面板还可能记录 URL、Header、token、Cookie、请求 Body 和响应 Body。截图、日志导出与文件分享都会扩大数据接触面。测试账号也可能含真实用户信息，不能因为包名带 `debug` 就省略隐私审查。

## Release 隔离：依赖图和最终制品都要查

no-op AAR 只保留 API 形状，manifest 很小，适合作为 Release 编译占位。它无法防止开发者误加完整运行时、可选模块或本地重打包 AAR，因此 CI 应同时查解析后的依赖和成品内容。

下面的 Gradle 任务用于拦截 Release 运行时依赖中的 DoKit 实现模块，只允许 `dokitx-no-op`：

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

多 flavor 工程要为每个正式变体生成对应检查，不能把 configuration 名写死后只覆盖一个包。依赖图检查通过后，还要解开最终 APK/AAB 搜索 DoKit 类、组件、权限、资源与 native 库，因为本地 AAR、shade 或重打包可能绕过 groupId 规则。

发布前至少完成这些检查：

- 依赖：正式变体只有 no-op，未包含完整 `dokitx`、插件产物和可选 native 模块。
- 代码与资源：没有 `DoKitReal`、`UniversalActivity`、面板资源、自定义 kit、测试账号菜单、后门手势和调试 deep link。
- Manifest：没有多余的悬浮窗、存储、电话、相机、Wi-Fi、录屏前台服务权限或宽路径 FileProvider。
- 网络：没有 DoKit 统计、健康检查、Mock 平台、网络代理和测试域名请求。
- 数据：没有内网地址、token、Cookie、用户数据、Mock 数据和诊断日志留在 assets、res 或包内数据库。
- 行为：在全新设备、升级安装、通知拒绝、无悬浮窗权限和后台启动限制下测试正式包。
- Native：启用过 GPS mock、pthread hook 等模块时，检查最终包 ABI、16 KB ELF / ZIP 对齐和目标设备运行。

Release 隔离的验收对象是签名后的成品，不是 Gradle 文件里的几行依赖。

## 团队如何使用 DoKit

| 角色 | 现场动作 | 应交付的信息 |
|---|---|---|
| 测试 | 切测试环境、查看请求、构造安全的弱网/Mock 条件 | 版本、设备、账号、环境、开关、复现步骤、请求标识 |
| 业务开发 | 检查网络、本地数据和业务状态，增加短期诊断 kit | 初步假设、相关代码路径、需抓取的专项数据 |
| 性能专项 | 固定路径，关闭无关 kit，抓 trace 或 benchmark | trace、指标口径、设备条件、修复前后对比 |
| 安全与发布 | 审查权限、组件、出站域名、日志和最终产物 | 依赖与成品扫描记录、风险处置结果 |

团队还应约定三条纪律：

- 新增自定义 kit 时写明负责人、适用环境、数据范围和移除条件。
- 测试报告记录启用的 DoKit 功能；浮窗、抓包和 hook 都可能改变结果。
- 性能复核包只打开当前调查所需能力，避免多个采集器互相干扰。

## 小结

DoKit 的优势是把调试入口和测试条件带到设备现场。它可以帮助团队更快找到异常页面、稳定复现步骤，并把网络、本地状态和业务诊断入口集中管理。

在 Android 17 / API 37 工程中，接入前要接受几个硬边界：公开 3.7.11 插件仍依赖已从 AGP 8 移除的 Transform API；运行时使用隐藏 API hook；旧 manifest 需要按 target 37 重审；弱网与 Mock 都会先发送真实请求；可选 native 模块还可能引入 16 KB 不兼容依赖。

合适的路径是：Debug / QA 变体按需启用、默认关闭上传、只在安全接口上构造网络条件、用 DoKit 提供线索，再交给 Perfetto、Profiler、JankStats、FrameMetrics 或 Macrobenchmark 验证。Release 则以最终 APK/AAB 不含 DoKit 实现、入口、权限、数据和出站行为为准。

## 参考资料

- [DoKit 官方仓库](https://github.com/didi/DoKit)
- [DoKit Android 接入说明](https://github.com/didi/DoKit/blob/master/Android/README.md)
- [Maven Central：dokitx 元数据](https://repo.maven.apache.org/maven2/io/github/didi/dokit/dokitx/maven-metadata.xml)
- [Maven Central：dokitx 3.7.11 source JAR](https://repo.maven.apache.org/maven2/io/github/didi/dokit/dokitx/3.7.11/dokitx-3.7.11-sources.jar)
- [Maven Central：dokitx-plugin 3.7.11 source JAR](https://repo.maven.apache.org/maven2/io/github/didi/dokit/dokitx-plugin/3.7.11/dokitx-plugin-3.7.11-sources.jar)
- [Android Gradle Plugin API 更新：Transform API](https://developer.android.com/build/releases/gradle-plugin-api-updates)
- [Android 14 前台服务类型要求](https://developer.android.com/about/versions/14/changes/fgs-types-required)
- [Android 13 通知运行时权限](https://developer.android.com/develop/ui/views/notifications/notification-permission)
- [Android 11 分区存储变更](https://developer.android.com/about/versions/11/privacy/storage)
- [Android 16 KB 页支持指南](https://developer.android.com/guide/practices/page-sizes)
- [`android-17.0.0_r1`：`ActivityThread.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/app/ActivityThread.java)
- [`android-17.0.0_r1`：`Handler.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/os/Handler.java)
- [`android-17.0.0_r1`：`Looper.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/os/Looper.java)
- [`android17-6.18-2026-06_r6` common kernel](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/)
