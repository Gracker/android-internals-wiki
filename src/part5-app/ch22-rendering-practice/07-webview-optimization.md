---
title: "WebView 性能优化实战"
chapter: "22.7"
section: "22.7"
status: finalized
applicable_versions: "Android 10 (API 29) - Android 17 (API 37)"
last_verified: "2026-07-12"
last_verified_against: "AOSP android-17.0.0_r1, Android Developers docs, Chromium android_webview docs, Clippings 结构参考, AIW 既有章节"
confidence: medium
drafted_date: "2026-05-13"
polish_count: 1
consolidated_from:
  - "src/part2-performance/ch07-smoothness/11-webview-performance.md"
sources:
  - type: clippings-structure-ref
    path: "Clippings/Android 性能优化 - 原理：重新认识应用的速度优化.md"
  - type: clippings-structure-ref
    path: "Clippings/Android 性能优化 - 虚拟内存优化（下）：一些“黑科技”优化手段.md"
  - type: clippings-structure-ref
    path: "Clippings/Android 性能优化 - 物理内存优化实战：Java Heap 内存优化.md"
  - type: clippings-structure-ref
    path: "Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 39.md"
  - type: existing-aiw
    path: "src/part2-performance/ch07-smoothness/11-webview-performance.md"
  - type: existing-aiw
    path: "src/part2-performance/ch18-rendering-pipelines/13-webview-rendering.md"
  - type: aosp
    path: "https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/webkit/WebView.java"
  - type: aosp
    path: "https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/webkit/WebViewFactory.java"
  - type: aosp
    path: "https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/webkit/WebViewClient.java"
  - type: aosp
    path: "https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/webkit/WebSettings.java"
  - type: aosp
    path: "https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/webkit/RenderProcessGoneDetail.java"
  - type: official
    path: "https://developer.android.com/develop/ui/views/layout/webapps/webview"
  - type: official
    path: "https://developer.android.com/reference/android/webkit/WebView"
  - type: official
    path: "https://developer.android.com/reference/android/webkit/WebViewClient"
  - type: official
    path: "https://developer.android.com/reference/android/webkit/JavascriptInterface"
  - type: official
    path: "https://developer.android.com/reference/android/webkit/WebSettings"
  - type: research-note
    path: "OpenClaw定时任务/AutoResearchClaw调研报告/2026-05-02-webview-render-process-recovery.md"
  - type: research-note
    path: "OpenClaw定时任务/AutoResearchClaw调研报告/2026-05-05-webview-render-process-oom-recovery-onrendeprocessgone.md"
tags: [webview, preload, offline-package, jsbridge, h5-performance]
related_chapters: ["22.1", "18.13", "26.2"]
pipeline_stage: ready-to-publish
task6_state: reviewed
task9_state: reviewed
task2b_state: fixed
reviewed_by: openclaw-task6
reviewed_date: "2026-07-12"
task6_reviewed_date: "2026-06-03"
task6_result: pass-light-edit
last_task6_at: "2026-07-12T12:15:00+08:00"
last_task6_review_log: "logs/review/2026-06-03-07-review.md"
task6_review_notes: "2026-07-12 Task6 revisiting 复审：pass-light-edit。L1 禁用词/高频词/否定-纠正/元叙述 grep 全部零命中；L2 结构/节奏/读者视角通过；task9 idle audit auto-fixed（P2 源码标签）等效通过；无新增 L3/L4 回炉项。自动晋升 finalized。"
task9_result: auto-fixed
task9_reviewed_by: openclaw-task9
task9_reviewed_date: "2026-07-12"
last_task9_at: "2026-07-12T11:24:32+08:00"
last_task9_review_log: "logs/deep-review/2026-07-12-11-audit.md"
task9_review_notes: "2026-07-12 Task9 idle audit auto-fix：WebView framework source labels and links updated to android-17.0.0_r1 baseline; no API behavior drift found; Task6 revisiting requested for light review."
task2b_result: fixed
last_task2b_at: "2026-06-03T04:50:00+08:00"
last_task2b_notes: "frontmatter fallback：修复 WebView destroy 线程约束、UA 预热边界、离线包白名单、renderer 退出生命周期 guard 与重试预算。"
last_task9_autofix_at: "2026-07-12"
deepseek_cn_review_state: done
last_deepseek_cn_review_at: 2026-07-12
last_task9_audit: "2026-07-12"
last_task9_audit_log: "logs/deep-review/2026-07-12-11-audit.md"
last_task9_audit_at: "2026-07-12T11:24:32+08:00"
last_task9_audit_result: "auto-fixed"
last_task9_audit_notes: "idle audit auto-fix: AOSP WebView framework evidence labels and source links anchored to android-17.0.0_r1; no queue item needed; returned to Task6 for light review."
finalized_date: "2026-07-12"
finalized_by: openclaw-task6-auto-promote
---

# WebView 性能优化实战

## WebView 优化要同时看四段

WebView 页面打开后出现白屏、无法点击、滚动掉帧或页面重载，责任点可能分布在四段：

1. 宿主容器创建与 WebView startup；
2. 网络、HTTP 缓存、离线资源与页面数据；
3. Blink 的 JavaScript、style、layout、paint、raster 与 compositor；
4. 宿主 View 遍历、HWUI WebView functor、窗口 buffer、SurfaceFlinger 与显示。

把所有耗时压成一个“WebView 加载时间”，很难判断改动省下了哪一段。预热也许缩短了首次 provider 装载，却提高了 App 启动期内存；离线包也许省掉网络等待，却因版本混用制造白屏；WebView 池也许省掉实例构造，却把旧页面状态带入新页面。每项优化都应有命中、代价、失败和回退指标。

版本基线分为三组：

- Android 平台固定为 Android 17 / API 37 / `android-17.0.0_r1`，用于解释 framework、HWUI 和显示系统；
- kernel 固定为 `android17-6.18-2026-06_r6`，用于解释内存回收、dma-buf 与 fence 等基础语义；
- WebView provider 由设备上的可更新包提供。复现记录还要包含 provider 包名、`versionName` 和 `versionCode`。

同为 Android 17 的设备可以安装不同 provider 版本。平台源码能说明 `WebViewFactory` 怎样选择和装入 provider，却无法替代对应 Chromium revision。更完整的线程和显示链路见 [18.13 WebView 渲染管线](../../part2-performance/ch18-rendering-pipelines/13-webview-rendering.md)。

## 页面打开时间怎样量

### 用业务可用性定义终点

一条 H5 打开链路至少记录下列时间点：

| 时间点 | 含义 | 适合回答的问题 |
|---|---|---|
| `open_requested` | Native 收到打开页面请求 | 用户等待从何时开始 |
| `container_attached` | WebView 已加入可见容器 | 宿主容器花了多久 |
| `navigation_started` | App 调用 `loadUrl()` 或页面导航开始 | 导航前准备花了多久 |
| `page_commit_visible` | `onPageCommitVisible()` 到达 | 复用实例何时不会再画旧页面 |
| `page_usable_signal` | 页面主动报告首屏数据、事件处理与关键内容就绪 | 用户何时能完成当前业务动作 |
| `usable_visual_state` | 收到页面可用信号后，再通过 visual state callback 确认对应 DOM 状态可被绘制 | 页面状态何时进入 WebView 绘制序列 |

`onPageFinished()` 只说明主 frame 完成加载。Android 官方文档明确指出，它不保证下一帧已经反映当时的 DOM 状态，也无法证明首屏数据和交互处理已经就绪。`onPageCommitVisible()` 的用途更窄：它保证后续绘制不会带出上一次导航的旧内容，适合控制复用 WebView 的显示时机。

`page_usable_signal` 应由页面按业务定义发出。例如商品页可在标题、价格、主图占位和购买按钮事件完成后上报；帮助页可在首屏正文与目录点击就绪后上报。页面侧还可以上报 FCP、LCP、Long Task 与资源时间，但这些指标由可更新 provider 的 Web 能力实现，采集前要在目标 provider 上验证。

### 使用单调时钟并记录导航身份

下面的代码用于收集 Native 侧时间点，并把 provider 身份写进同一条报告。

```kotlin
class H5OpenTiming(
    private val pageKey: String,
    private val navigationId: String
) {
    private val startNs = SystemClock.elapsedRealtimeNanos()
    private val marksNs = ConcurrentHashMap<String, Long>()

    fun mark(name: String) {
        marksNs.putIfAbsent(name, SystemClock.elapsedRealtimeNanos())
    }

    fun snapshot(): H5OpenReport {
        val provider = WebView.getCurrentWebViewPackage()
        val elapsedMs = marksNs.mapValues { (_, valueNs) ->
            TimeUnit.NANOSECONDS.toMillis(valueNs - startNs)
        }
        return H5OpenReport(
            pageKey = pageKey,
            navigationId = navigationId,
            elapsedMs = elapsedMs,
            providerPackage = provider?.packageName,
            providerVersionName = provider?.versionName,
            providerVersionCode = provider?.longVersionCode
        )
    }
}
```

`elapsedRealtimeNanos()` 不受用户改时间或网络校时影响，适合计算进程内耗时。`navigationId` 用来隔离重定向、刷新和并发打开；缺少它时，旧页面的迟到回调可能写进新导航。`WebView.getCurrentWebViewPackage()` 在 API 26 起可用，查询本身不会装载 provider；适用范围最低为 API 29。

报告还应带上页面 bundle 版本、离线包版本、预热状态、实例来源、网络类型、设备内存档位、前后台状态和错误码。平均值只适合观察趋势，发布判定至少要看分位数、低内存设备、弱网和各 provider 版本。

## WebView 初始化耗时优化

### 把 startup、实例创建和首个页面分开

第一次使用 WebView 时，主线程可能同时负责 provider 选择、Java 类加载、native library 装载和 Chromium startup。后续工作还包括单个 WebView 的 provider-side 对象创建、renderer 建立、网络请求、解析、raster、functor 绘制与窗口提交。这些阶段的触发时机受 provider revision 影响，不能统一写成“构造 WebView 就创建 renderer 和 GPU 资源”。

更适合实验的拆分方式如下：

| 阶段 | 对照实验 | 观察证据 |
|---|---|---|
| WebView startup | 进程内首次调用与已经 startup 后的同一路径 | 主线程阻塞位置、provider / native library 装载 |
| 实例创建 | startup 完成后比较 `WebView(context)` 的首个与后续实例 | 构造耗时、Java / native / graphics 内存增量 |
| 导航启动 | 空白实例调用 `loadUrl()` | renderer、network service、DNS / TLS、主文档 |
| 页面可用 | 导航开始到页面可用信号 | HTML、CSS、JS、数据、图片与 Bridge |
| 用户看到 | 页面状态到宿主窗口 present | renderer、functor、HWUI、SF / HWC |

Perfetto 中看到 `CrRendererMain`、raster worker 或 GPU service 线程出现，只能证明对应执行域已经活动。线程名会随 provider 改版变化，诊断时还要结合进程关系、slice、调用栈与 SurfaceFlinger layer。

### AndroidX WebKit 1.16.0+ 的异步 startup

AndroidX WebKit 1.16.0 提供稳定版 `WebViewCompat.startUpWebView()`。它把允许后台执行的 startup 工作交给指定 executor，并把必须留在 UI 线程的工作分段执行。startup 每个进程只发生一次；调用完成前访问其他 `android.webkit` 或 `androidx.webkit` API，UI 线程仍可能等待尚未完成的部分。

下面的代码用于在可控时机启动 WebView，并记录 startup 是否曾阻塞 UI 线程。

```kotlin
class WebViewBootstrap(
    private val executor: Executor,
    private val metrics: WebViewStartupMetrics
) {
    fun start(
        context: Context,
        onReady: () -> Unit,
        onFailure: (WebViewStartupException) -> Unit
    ) {
        val config = WebViewStartUpConfig.Builder(executor).build()

        WebViewCompat.startUpWebView(
            context.applicationContext,
            config,
            object : WebViewOutcomeReceiver<
                WebViewStartUpResult,
                WebViewStartupException
            > {
                override fun onResult(result: WebViewStartUpResult) {
                    metrics.record(
                        uiBlockingLocations =
                            result.uiThreadBlockingStartUpLocations.orEmpty(),
                        backgroundBlockingLocations =
                            result.nonUiThreadBlockingStartUpLocations.orEmpty()
                    )
                    onReady()
                }

                override fun onError(error: WebViewStartupException) {
                    onFailure(error)
                }
            }
        )
    }
}
```

回调运行在主线程。正常路径可以等待 `onResult()` 后再创建 WebView；异常路径要记录并停止继续访问 WebView API，因为官方文档指出 startup 失败后，后续调用很可能抛异常或使进程崩溃。`startUpWebView()` 允许多处调用，已经完成时会很快回调，业务层仍应避免无限重试。

调度时机取决于页面是不是启动主路径：

- App 启动不依赖 H5：在首屏关键工作结束后、预测用户即将进入 H5 前启动，并尽量等待回调；
- App 启动依赖 H5：可在 `Application.onCreate()` 较早调用，让后台部分与其他启动工作并行；创建 WebView 前仍要减少同一时段的 UI 线程任务；
- H5 使用率很低：保持按需 startup，通常比常驻 provider 与 renderer 更省内存。

如果业务只想提前执行后台部分，可用 `setShouldRunUiThreadStartUpTasks(false)` 构建第一次配置；需要 WebView 前再以 `true` 调用一次，完成余下的 UI 线程工作。两次调用之间访问 WebView API，仍会让调用线程等待 startup 进度。

通过 `WebSettings.getDefaultUserAgent()` 强制预热属于旧式 workaround。当前官方 startup 指南建议迁移到 `startUpWebView()`，因为 UA 查询的隐式初始化范围与时序缺少稳定契约，也无法提供 startup 阻塞位置。

### 预创建只能解决剩余的实例成本

异步 startup 完成后，如果 trace 仍显示单个 WebView 实例创建占用可观主线程时间，并且目标页面命中率高，可以评估预创建。预创建实例需要一个可解释的 owner：

- 它在 UI 线程创建和销毁；
- 它使用将来展示它的 Activity Context；
- 它只服务同一个 Activity 生命周期和同一个安全域；
- Activity 结束、进程进入内存压力状态或预测失效时销毁。

下面的单槽实现只缓存尚未导航的空白实例，用于说明最小所有权边界。

```kotlin
@MainThread
class ActivityWebViewSlot(
    private val activity: Activity
) : Closeable {
    private var idle: WebView? = null

    fun prepare() {
        check(!activity.isFinishing && !activity.isDestroyed)
        if (idle == null) {
            idle = WebView(activity)
        }
    }

    fun take(): WebView {
        check(!activity.isFinishing && !activity.isDestroyed)
        return idle.also { idle = null } ?: WebView(activity)
    }

    override fun close() {
        idle?.destroy()
        idle = null
    }
}
```

该实现没有复用加载过页面的实例，也没有跨 Activity 改 Context。用 application Context 创建后再展示，可能在主题资源、窗口 token、文件选择、Autofill、弹窗和其他 UI 能力上产生边界问题；用 `MutableContextWrapper` 切换 base Context 也不等于 provider 内部保存的所有引用都已更新。仅为 startup 提速时，异步 startup 比缓存一个不可见 WebView 更容易控制。

### WebView 池需要完整状态机

加载过页面的 WebView 带有导航历史、页面 JavaScript 状态、Bridge、客户端回调、表单、焦点、滚动位置、媒体、权限请求和 provider-side 资源。把它放回池之前，需要经历 `ACTIVE → RESETTING → IDLE`，任何清理失败都转入 `DESTROYED`。`about:blank` 导航是异步操作，发起后立即把实例交给下一位调用者，会产生旧页面回调、旧内容短暂显示和历史串页。

池的准入条件应同时满足：

- 同一个 Activity 或明确的容器 owner；
- 同一账号与同一隐私边界；
- 同一组可信 origin、Bridge 能力和 WebSettings 策略；
- 页面明确支持复用；
- trace 证明复用收益仍然存在；
- 有内存压力收缩与 renderer 退出处理。

池容量没有跨设备通用值。应从空闲实例 PSS / graphics 增量、并发打开数量、低内存设备回收率和池命中率推导。支付、第三方登录、用户输入 URL、外部网页、文件上传和权限敏感页面更适合新建实例或交给 Custom Tabs。

归还时常见的全局误操作也要避开：

- `clearCache(true)` 会影响共享 profile 的 HTTP cache；
- 清 Cookie 或 Web Storage 会影响同一数据目录下的其他 WebView；
- 替换 `WebViewClient`、`WebChromeClient` 与 Bridge 后，业务持有的协程、回调表和权限请求仍需显式取消；
- `clearHistory()` 只处理历史列表，无法证明页面执行环境已经清空。

### 多进程要先配置 data directory

Android P / API 28 起，`WebView.setDataDirectorySuffix()` 用于给同一 App 的不同进程分配独立 WebView 数据目录。调用顺序很严格：它必须早于本进程的任何 WebView 实例，也必须早于其他 `android.webkit` 方法。需要异步 startup 的进程，应先设置 suffix，再调用 `startUpWebView()`。

每个使用 WebView 的进程使用不同 suffix，suffix 不能包含路径分隔符。不同目录不会直接共享 Cookie、LocalStorage 与缓存；确有跨进程登录需求时，要通过受控协议显式同步。大多数 App 更适合把 WebView 集中在一个进程，并在其他进程尽早调用 `WebView.disableWebView()`，防止 SDK 意外初始化。

## 离线包与资源拦截

### 缓存层各自解决什么

WebView 的缓存与预取可以按控制者拆分：

| 层级 | 控制者 | 适合内容 | 主要约束 |
|---|---|---|---|
| HTTP cache | provider 与服务器响应头 | 可缓存的 HTML、CSS、JS、图片与接口响应 | 遵守 `Cache-Control`、验证器、Vary 与 Cookie 语义 |
| Service Worker / Cache Storage | 受控网页 | 页面团队可维护的离线与更新策略 | 生命周期、作用域、版本迁移与 provider 支持 |
| APK 静态资源 | App | 协议、帮助、内置说明等固定内容 | 随 App 发版，适合 `WebViewAssetLoader` |
| 动态离线包 | App 与发布系统 | 强控制业务的 HTML、CSS、JS、图片 | 签名、原子切换、同版本资源、灰度与回退 |
| speculative loading | provider 与 App | 高概率的后续导航 | 网络、CPU、内存、隐私与未命中流量 |

缓存命中必须保留 HTTP 与 origin 语义。将任意 URL 映射到本地文件、忽略 MIME、把多个版本的 HTML 与 JS 混用，都会让“加速”转成安全或一致性问题。

### `shouldInterceptRequest()` 的线程与协议边界

`WebViewClient.shouldInterceptRequest()` 在非 UI 线程回调，且可能并发发生。实现中不要访问 View，不要等待 UI 线程，不要在热路径解压大包或校验整包。更新线程应先完成下载、签名 / hash 验证和解压，再用不可变索引原子切换到新版本。

下面的代码只对已经验证并发布的 HTTPS GET 资源返回离线内容。

```kotlin
class SignedOfflineClient(
    private val index: OfflineIndex
) : WebViewClient() {
    override fun shouldInterceptRequest(
        view: WebView,
        request: WebResourceRequest
    ): WebResourceResponse? {
        val url = request.url
        if (request.method != "GET" || url.scheme != "https") {
            return null
        }
        if (request.requestHeaders.keys.any {
                it.equals("Range", ignoreCase = true)
            }) {
            return null
        }

        val entry = index.openVerified(
            url = url,
            isMainFrame = request.isForMainFrame
        ) ?: return null

        return WebResourceResponse(
            entry.mimeType,
            entry.charset,
            200,
            "OK",
            entry.responseHeaders,
            entry.inputStream
        )
    }
}
```

`OfflineIndex` 应绑定一份不可变 manifest，并区分主文档与子资源。主文档按规范化后的完整 URL 或受控模板匹配；子资源还要核对该 manifest 中的 URL、hash、MIME、响应头和版本。示例把 Range 请求交回 provider；若离线包需要承载音视频或大文件，必须完整实现字节范围与 `206 Partial Content` 语义。返回 `null` 表示交回 provider 正常加载。响应头要保留页面所需的 CSP、缓存与内容类型语义，不能给所有资源套同一组 header。

该回调还有三个常被漏掉的限制：

- `javascript:`、`blob:`、`file:///android_asset/` 与 `file:///android_res/` 不进入该回调；
- 发生重定向时，只为初始资源 URL 回调，后续重定向 URL 不会再次进入；
- Safe Browsing 默认仍会检查相应 URL。

因此，离线 manifest 不应依赖“拦截重定向后的地址”来维持安全边界。主 frame 的导航白名单还要在导航策略中独立校验。

### 静态本地内容使用 `WebViewAssetLoader`

`WebViewAssetLoader` 可以把 APK assets 或 resources 映射到 HTTP(S)-like URL，使页面继续使用 Same-Origin Policy。它比 `file://` 更适合协议、帮助与内置说明页面。`file://` 与 `data:` 属于 opaque origin；开启 `setAllowFileAccessFromFileURLs(true)` 或 `setAllowUniversalAccessFromFileURLs(true)` 会扩大文件访问风险。

使用默认的 `https://appassets.androidplatform.net/` 时，要明确资源路径与线上 origin 的边界；使用自有域名时，要防止本地映射和线上同域资源产生含混。动态离线包仍需自己的签名、版本与回退系统，`WebViewAssetLoader` 不负责这些发布问题。

### 动态离线包的发布协议

一份可回退的离线包至少需要：

1. manifest 标识业务页面、包版本、最低容器版本、资源列表、MIME 与 hash；
2. 下载后验证签名和每个资源的 hash；
3. 在临时目录完成验证与解压，再通过原子指针发布；
4. 单次导航固定一个 manifest snapshot，禁止中途切版本；
5. 本地 miss 回网络，校验失败回上一个健康版本；
6. 监控命中率、校验失败、解析错误、JS 异常、白屏、回退和版本分布。

HTML、JS 与 CSS 必须来自同一兼容集合。只更新主文档或只更新一个 bundle，可能导致 Bridge 协议、chunk 清单或资源 hash 对不上。回退单位也应是一整份 manifest。

### 预连接、预取与预渲染

当前 AndroidX WebKit 与 provider 能力允许三类 speculative loading：

- `Profile.preconnect()` 按 origin 提前完成 DNS、TCP / TLS 等连接准备，资源成本最低；
- `Profile.prefetchUrlAsync()` 按 HTTPS URL 获取主 HTML 并写入 profile 的网络缓存，不会一并执行 JS 或拉取 CSS；
- `WebViewCompat.prerenderUrlAsync()` 绑定具体 WebView，后台创建可激活页面，CPU、内存与网络成本最高。

这些 API 要以项目采用的 AndroidX WebKit 版本和 `WebViewFeature` 检查为准。Prefetch 的后台请求会跳过 `shouldInterceptRequest()`；用户导航时，主 HTML 才进入拦截回调。如果此时返回自定义 `WebResourceResponse`，provider 会采用拦截结果并绕过 prefetch cache。离线包与 provider prefetch 同时启用时，必须设计清楚谁拥有主文档。

触发阈值不应写成固定点击率或固定字节数。策略需要由页面转化率、网络类型、未命中流量、服务端 QPS、取消率、过期率、内存压力和用户隐私共同决定，并通过远程配置与 A/B 实验调整。预渲染只适合用户高度可能进入且副作用受控的页面；带登录写操作、支付、音视频或敏感权限的页面要单独评估。

## JS Bridge 性能优化

### 明确两侧线程

`addJavascriptInterface()` 暴露的方法运行在该 WebView 的私有后台线程。方法仍是一次同步跨边界调用：JavaScript 需要等待 Java 方法返回。Bridge 方法内执行磁盘 I/O、数据库等待、网络请求或跨线程 `join()`，会阻塞网页调用方；如果它又同步等待主线程，而主线程正在等待 WebView 相关结果，还可能形成循环等待。

`evaluateJavascript()` 只能在创建 WebView 的 UI 线程调用，结果回调也在 UI 线程。它是异步 API，禁止用 `CountDownLatch.await()`、`Future.get()` 或阻塞式协程桥接把它改成同步等待。

Bridge 的处理步骤更适合保持短小：

1. 校验长度、协议版本、方法名与字段；
2. 生成或读取 `requestId`；
3. 把工作投递到有生命周期的协程或 executor；
4. 立即从 Java 暴露方法返回；
5. 完成后在 UI 线程通过消息通道或安全编码的 JS 回调响应；
6. 页面销毁、导航切换、超时或 renderer 退出时取消未完成请求。

### 优先采用可校验 origin 的消息通道

`addJavascriptInterface()` 会把对象注入符合页面加载条件的所有 frame，Native 无法从方法调用中得知具体调用 frame 的 origin。页面包含第三方 iframe 时，仅校验主 frame URL 无法保护 Bridge。

支持 `WEB_MESSAGE_LISTENER` 的 provider 可以通过 `WebViewCompat.addWebMessageListener()` 指定 origin 规则，并在回调中获得 `sourceOrigin` 与 `isMainFrame`。下面的代码把耗时工作移到业务 dispatcher，并使用 reply proxy 返回结果。

```kotlin
@MainThread
fun installAccountBridge(
    webView: WebView,
    scope: CoroutineScope,
    dispatcher: CoroutineDispatcher,
    service: AccountBridgeService
) {
    check(WebViewFeature.isFeatureSupported(WebViewFeature.WEB_MESSAGE_LISTENER))
    val trustedOrigin = Uri.parse("https://h5.example.com")

    WebViewCompat.addWebMessageListener(
        webView,
        "AccountBridge",
        setOf(trustedOrigin.toString()),
        object : WebViewCompat.WebMessageListener {
            override fun onPostMessage(
                view: WebView,
                message: WebMessageCompat,
                sourceOrigin: Uri,
                isMainFrame: Boolean,
                replyProxy: JavaScriptReplyProxy
            ) {
                if (
                    !isMainFrame ||
                    sourceOrigin != trustedOrigin ||
                    message.type != WebMessageCompat.TYPE_STRING
                ) {
                    return
                }
                val raw = message.data ?: return
                if (raw.length > service.maxRequestChars) {
                    return
                }

                scope.launch(dispatcher) {
                    val reply = service.handle(raw)
                    withContext(Dispatchers.Main.immediate) {
                        replyProxy.postMessage(reply)
                    }
                }
            }
        }
    )
}
```

origin 规则应写成明确的 HTTPS origin，避免通配符。`scope` 必须由页面 owner 管理；页面离开后取消它，防止旧请求回到新导航。长度限制只是入口保护，`service.handle()` 还需完成协议版本、方法白名单、参数类型、授权、超时和响应大小检查。

当 provider 缺少该特性而必须回退到 `addJavascriptInterface()` 时，只对全内容受控、不会加载第三方 frame 的页面注入。导航离开可信域之前移除接口；对外部链接更适合新容器或 Custom Tabs。

### 协议要支持批量、超时和取消

一个可维护的 Bridge envelope 可以包含这些字段：

| 字段 | 用途 |
|---|---|
| `version` | 协议演进和兼容判断 |
| `requestId` | 响应配对、去重与取消 |
| `method` | 进入 Native 方法白名单 |
| `params` | 结构化参数 |
| `deadlineMs` | 调用方允许的等待时间 |
| `traceId` | 串接页面、Native 与服务端日志 |

页面获取用户、设备、网络、主题与实验配置时，优先一次批量请求。埋点也应分批提交，并在页面隐藏或达到上限时 flush。调用次数减少后，序列化、线程切换和回调调度都会下降；单包仍要受大小限制，避免把大图片、文件或超长 JSON 经字符串 Bridge 传输。

每个方法记录调用量、排队时间、执行时间、响应大小、失败码、超时和取消原因。只记录总平均耗时，会漏掉某个高频小调用造成的累计调度成本。

### `evaluateJavascript()` 只负责异步执行

下面的 helper 用 JSON 字符串编码参数，避免把未转义内容直接拼进脚本。

```kotlin
@MainThread
fun WebView.resolveBridgeCall(
    requestId: String,
    payload: String,
    onEvaluated: (String?) -> Unit
) {
    val script = buildString {
        append("window.__nativeResolve(")
        append(JSONObject.quote(requestId))
        append(',')
        append(JSONObject.quote(payload))
        append(')')
    }
    evaluateJavascript(script, onEvaluated)
}
```

`onEvaluated` 收到的是 JavaScript 表达式结果的编码形式，并非页面业务响应本身。业务通常依靠 `requestId` 完成响应配对；页面已销毁或导航身份变化时直接丢弃。脚本函数名也应固定在受控协议中，不能接受页面传入任意 JavaScript 代码。

## 页面侧需要一起治理

Native 优化只能缩短容器、缓存和通信部分。页面仍要控制解析、执行、布局、绘制与资源：

- 主文档尽快给出可读骨架，关键 CSS 避免被非关键资源阻塞；
- JS bundle 按路由和功能拆分，非首屏任务延后，长任务拆成可调度的小段；
- 服务端或页面缓存直接提供首屏数据时，要处理过期与一致性；
- 图片按显示尺寸与设备能力下发，使用响应式资源，减少解码和 GPU 纹理压力；
- 滚动中合并样式读写，减少强制同步 layout；动画评估 `transform`、`opacity` 与合成层数量；
- Native 运行时信息批量提供，避免页面启动阶段循环调用 Bridge；
- 页面通过 `PerformanceObserver`、资源时间和业务 mark 上报可用性，并带 bundle 与容器版本。

资源预算应按页面类型制定。资讯正文、商品详情和活动页的 DOM、JS、图片与交互目标不同，统一的固定阈值会把合理页面误报，也会放过高端机上暂时不显著的问题。预算由线上分位数、低端机 trace 和发布回归共同校准。

## WebView 卡顿要沿显示路径定位

### 普通网页主体通常进入宿主窗口

标准硬件加速路径可以概括为：

1. renderer 侧执行 JavaScript、style、layout、paint，并准备 compositor frame 与 raster 资源；
2. provider 的 browser / GPU 侧把结果交给宿主 WebView；
3. App 主线程在 View traversal 中记录 WebView functor 与绘制边界；
4. HWUI RenderThread 执行 DrawFn，把网页内容与其他 View 合入 App Window buffer；
5. 窗口 buffer 经 BLAST / BufferQueue 交给 SurfaceFlinger，再由 CompositionEngine / HWC 送显。

普通 DOM layer、CSS transform、canvas 和图片通常不会逐个成为 SurfaceFlinger layer。视频、受保护内容、provider overlay 或 `WebChromeClient.onShowCustomView()` 托管的全屏媒体可能增加独立 Surface / `SurfaceControl` layer。看到额外 layer 时，要核对 owner、parent、buffer 与 transaction，不能直接把它认作整个 WebView。

窗口关闭硬件加速、目标 Canvas 为软件 Canvas，或 provider 的硬件 draw 请求无法执行时，WebView 可能进入软件绘制路径。该结论需要 Canvas acceleration、调用栈、provider 日志和 GPU / DrawFn trace 共同支持；设备性能较低或某段 CSS 很复杂，只能作为排查线索。

### Perfetto 证据表

| 现象 | 优先检查 | 后续证据 |
|---|---|---|
| `loadUrl()` 前主线程长时间阻塞 | WebView startup 或实例构造 | startup blocking location、provider load、native library |
| renderer main 长任务 | JS、style、layout、paint | Chrome DevTools、Long Task、renderer CPU 栈 |
| raster / decode 延迟 | tile、图片解码、缓存 miss | raster worker、Skia / decode slice、I/O 与内存 |
| renderer 已有新 frame，宿主迟迟未 draw | App 主线程或 traversal | `Choreographer#doFrame()`、Runnable、ViewRoot |
| RenderThread 的 WebView DrawFn 变长 | 资源导入、functor 同步、GPU service 或 fence | DrawFn slice、GPU queue、线程状态、fence |
| host window 已 queue，屏幕仍旧 | acquire fence、SF latch、transaction 或显示合成 | FrameTimeline、layer、composition type、present fence |
| 网页 UI 正常，视频卡顿或漂移 | media producer / overlay transaction | codec output、video layer buffer、几何 transaction |

长 slice 还要结合线程状态解释。Running 表示 CPU 正在执行；Runnable 长通常指向调度等待；Sleeping、futex 或 blocked 可能在等 IPC、任务或 fence。只看 slice 的 wall time，容易把等待误算成计算。

网页 compositor frame ready 也不是用户已经看到。普通主体要继续追 host App Window 的 buffer 与 FrameTimeline；媒体 overlay 还要分别追视频 buffer、几何 transaction 和 display present。

## 内存、泄漏与 renderer 生命周期

### WebView 内存分布在多个执行域

一个复杂页面可能同时占用：

- 宿主 Java 对象、Activity / Fragment 与回调；
- provider browser-side native 内存；
- renderer 的 DOM、V8 heap、图片解码与 raster tile；
- GPU service 的纹理和图形资源；
- 宿主 HWUI、窗口 buffer 与可选媒体 layer。

只看宿主进程 Java heap 会漏掉 renderer 与 graphics。排查时要记录宿主及关联 renderer PID，结合 `dumpsys meminfo`、`smaps_rollup`、Perfetto process / memory counter、LeakCanary 和 Chrome DevTools Memory。空闲 WebView 池也要纳入 PSS 与 graphics 统计。

在 `android17-6.18-2026-06_r6` 侧，内存抖动可以继续检查 page fault、direct reclaim、`kswapd`、PSI memory、设备启用时的 zram、dma-buf 分配与 GPU driver wait。kernel 证据只能说明系统压力和等待位置，页面对象归属仍要回到宿主、renderer 与 provider 分析。

### 展示实例的销毁顺序

正常销毁时，先切断宿主引用和回调，再在创建 WebView 的线程调用 `destroy()`。展示态 WebView 通常由主线程创建。

下面的代码用于销毁不再复用的实例。

```kotlin
@MainThread
fun destroyWebView(
    webView: WebView,
    bridgeNames: Collection<String>
) {
    (webView.parent as? ViewGroup)?.removeView(webView)
    webView.stopLoading()
    bridgeNames.forEach(webView::removeJavascriptInterface)
    webView.webChromeClient = null
    webView.webViewClient = null
    webView.setDownloadListener(null)
    webView.destroy()
}
```

销毁前，页面 owner 还要取消协程、Bridge 回调表、文件选择、权限请求和业务 listener。已经决定销毁时，无需先导航 `about:blank` 再等待；那会启动一次额外导航并产生更多回调。`clearCache()`、Cookie 清理和 Web Storage 清理属于共享 profile 行为，也不应混进单实例销毁。

如果实例将进入池，流程不同：它要先进入 `RESETTING`，完成异步空白导航、旧内容不可见确认、历史与业务态清理，再进入 `IDLE`。销毁流程和复用流程不要共用一个含糊的 `release()`。

### renderer 退出后旧实例必须作废

API 26 起，renderer crash 或系统回收会触发 `WebViewClient.onRenderProcessGone()`。回调参数中的 WebView 已经不可使用。应用选择继续运行时，必须从 View hierarchy 移除它、清理所有引用并销毁，再按业务状态创建新实例。

下面的 client 把“清理旧实例”和“是否重试”交给明确的 owner 与策略。

```kotlin
class RecoveringWebViewClient(
    private val owner: WebViewOwner,
    private val retryPolicy: RendererRetryPolicy,
    private val metrics: RendererGoneMetrics
) : WebViewClient() {
    override fun onRenderProcessGone(
        view: WebView,
        detail: RenderProcessGoneDetail
    ): Boolean {
        val failedNavigation = owner.navigationSnapshotFor(view)
        owner.detachAndClearReferences(view)
        view.destroy()

        val retry = retryPolicy.shouldRetry(
            navigation = failedNavigation,
            didCrash = detail.didCrash()
        )
        metrics.record(
            didCrash = detail.didCrash(),
            rendererPriorityAtExit = detail.rendererPriorityAtExit(),
            retryAllowed = retry
        )
        owner.showRendererFailure(failedNavigation, retry)
        return true
    }
}
```

`navigationSnapshotFor()` 读取 owner 在导航期间保存的快照，避免在 renderer 已退出后再调用旧 WebView 的 `getUrl()`。返回 `true` 表示宿主已经处理退出；返回 `false` 时，renderer crash 会使 App 崩溃，系统回收则可能使 App 被杀。多个 WebView 可以共享 renderer，系统会为每个受影响实例分别回调；每次只清理参数中的实例。

重试策略要区分 crash 与内存回收，并受页面 URL 模板、前后台、Activity 生命周期和次数预算限制。同一页面连续 crash 时自动反复重载会形成 crash loop，应转错误页并上报 provider 版本、页面版本与复现信息。调用 `setRendererPriorityPolicy()` 降低不可见 renderer 优先级前，必须已经具备这条恢复路径。

更完整的 OOM 与恢复设计见 [20.10 WebView Renderer OOM 恢复](../ch20-stability/10-webview-renderer-oom-recovery.md)。

### 不使用 native 手段释放 WebView 预留地址

部分 32 位系统与 provider 会在进程 maps 中出现 WebView 相关虚拟地址预留。它不等于物理内存已经被同量占用。通过 hook、`munmap()` 或私有符号释放该区域，会破坏后续 provider 初始化假设，也无法覆盖厂商与 provider 更新差异。

工程治理应采用 64 位进程、明确的 WebView 进程边界、受控池容量、页面资源预算、renderer 恢复与内存压力收缩。预留 VMA 只作为特定设备的研究证据，不进入通用优化方案。

## 一套可执行的优化顺序

WebView 优化适合按证据逐步推进：

1. 固定 Android build、provider、App、容器、页面和离线包版本；
2. 用 `navigationId` 建立 Native、页面与显示端时间点；
3. 冷进程分别测 startup、实例创建、导航和页面可用；
4. 用 `startUpWebView()` 处理确认存在的 startup 阻塞，再复测启动期 CPU 与内存；
5. 实例构造仍是显著成本时，评估 Activity 作用域预创建；池化需要另做状态污染和内存实验；
6. 网络占主导时，按 HTTP cache、静态资源、动态离线包、preconnect / prefetch / prerender 的成本逐级选择；
7. Bridge 按线程、origin、批量、payload、超时和取消检查；
8. 滚动与首屏绘制问题沿 renderer、functor、host window、SF / HWC 追踪；
9. 所有策略配置开关、灰度、观测和回退。

发布检查可以使用下表：

| 项目 | 必须具备的证据 | 失败时的动作 |
|---|---|---|
| startup | blocking location、命中率、T 分位数、启动期内存 | 关闭或推迟 startup |
| 预创建 / 池 | 实例成本、池命中、状态污染测试、空闲 PSS | 收缩容量或停用复用 |
| 离线包 | 签名 / hash、同版本资源、原子发布、回退演练 | 回网络或上一个健康包 |
| speculative loading | 命中、未命中流量、QPS、取消、内存 | 降级为 preconnect 或关闭 |
| Bridge | origin、方法白名单、线程、超时、payload 与取消 | 禁用能力或切只读协议 |
| 页面 | 可用信号、Web 指标、bundle 版本、低端机结果 | 回退 bundle 或关闭重功能 |
| renderer | `onRenderProcessGone()`、重试预算、错误页 | 停止自动重载 |
| 显示 | renderer 到 display present 的证据链 | 在对应执行域修复 |

单个 P50 变快不足以证明方案有效。还要确认 P95 / P99、低内存设备、弱网、后台切前台、provider 更新、页面回退与 App 启动都没有出现可接受范围外的回归。

## Android 17 源码与文档入口

### Android 平台

- [`WebView.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/webkit/WebView.java)：API 线程约束、provider 代理、JS Bridge、data directory 与 renderer 策略。
- [`WebViewFactory.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/webkit/WebViewFactory.java)：provider 选择、包校验、类加载与 factory 缓存。
- [`WebViewClient.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/webkit/WebViewClient.java)：页面生命周期、资源拦截和 renderer 退出回调。
- [`RenderProcessGoneDetail.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/webkit/RenderProcessGoneDetail.java)：退出原因与优先级信息。
- [`WebViewFunctor.h`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/libs/hwui/private/hwui/WebViewFunctor.h)：Android 17 中 HWUI 与 provider 的 DrawFn / overlay 边界。

### WebView provider、Jetpack 与 kernel

- [Chromium Android WebView architecture](https://chromium.googlesource.com/chromium/src/+/refs/heads/main/android_webview/docs/architecture.md)：provider 的 browser、renderer 与 service 架构；排障时切换到设备 provider 对应 revision。
- [WebView startup 优化](https://developer.android.com/develop/ui/views/layout/webapps/optimize-webview-startup) 与 [`WebViewCompat.startUpWebView()`](https://developer.android.com/reference/androidx/webkit/WebViewCompat#startUpWebView(android.content.Context,androidx.webkit.WebViewStartUpConfig,androidx.webkit.WebViewOutcomeReceiver))：稳定版异步 startup 的时序与错误处理。
- [`WebViewClient`](https://developer.android.com/reference/android/webkit/WebViewClient)、[本地内容](https://developer.android.com/develop/ui/views/layout/webapps/load-local-content) 与 [speculative loading](https://developer.android.com/develop/ui/views/layout/webapps/speculative-loading)：回调边界、`WebViewAssetLoader`、preconnect、prefetch 与 prerender。
- [`WebViewCompat.addWebMessageListener()`](https://developer.android.com/reference/androidx/webkit/WebViewCompat#addWebMessageListener(android.webkit.WebView,java.lang.String,java.util.Set%3Cjava.lang.String%3E,androidx.webkit.WebViewCompat.WebMessageListener))：origin-aware Bridge。
- kernel `android17-6.18-2026-06_r6` 的 [`dma-buf.c`](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/drivers/dma-buf/dma-buf.c)、[`sync_file.c`](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/drivers/dma-buf/sync_file.c) 与 [Linux 6.18 dma-buf 文档](https://docs.kernel.org/6.18/driver-api/dma-buf.html)：buffer 共享与 fence 基础语义。
