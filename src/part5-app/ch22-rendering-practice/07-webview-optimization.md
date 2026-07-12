---
title: "WebView 性能优化实战"
chapter: "22.7"
section: "22.7"
status: ready-for-review
applicable_versions: "Android 10 (API 29) - Android 17 (API 37)"
last_verified: "2026-07-12"
last_verified_against: "AOSP android-17.0.0_r1, Android Developers docs, Chromium android_webview docs, Clippings 结构参考, AIW 既有章节"
confidence: medium
drafted_date: "2026-05-13"
polish_count: 1
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
related_chapters: ["22.1", "7.11", "18.13", "26.2"]
pipeline_stage: task6_pending
task6_state: revisiting
task9_state: reviewed
task2b_state: fixed
reviewed_by: openclaw-task6
reviewed_date: "2026-06-03"
task6_reviewed_date: "2026-06-03"
task6_result: pass-light-edit
last_task6_at: "2026-06-03T10:05:00+08:00"
last_task6_review_log: "logs/review/2026-06-03-07-review.md"
task6_review_notes: "2026-06-03 Task6：revisiting 复审通过；L1/L2 轻修 1 处（否定-纠正式句型收束）；无新增 L3/L4 回炉项，转入 Task9 pending。 | 2026-06-03 10:05 Task6 revisiting 复审：pass-light-edit。L1 禁用词/高频词/否定-纠正/元叙述/物理动词 grep 全部零命中；L2 结构/节奏/开头/读者视角均通过；无新增 L3/L4 回炉项。送 Task9 复审。"
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
last_deepseek_cn_review_at: 2026-06-06
last_task9_audit: "2026-07-12"
last_task9_audit_log: "logs/deep-review/2026-07-12-11-audit.md"
last_task9_audit_at: "2026-07-12T11:24:32+08:00"
last_task9_audit_result: "auto-fixed"
last_task9_audit_notes: "idle audit auto-fix: AOSP WebView framework evidence labels and source links anchored to android-17.0.0_r1; no queue item needed; returned to Task6 for light review."
---

# WebView 性能优化实战

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 WebView 初始化耗时优化
- 🔹 预创建与 WebView 池
- 🔹 离线包与资源拦截
- 🔹 JS Bridge 性能优化

### 扩展（可选深入）

- 🔸 WebView 内存泄漏治理

### OpenClaw 加工指引

> **锚点**是最低覆盖要求，加工时必须逐条落实并标注验证结果。
> **扩展**视素材丰富程度选择性深入。
> 如果从 Obsidian 素材或 AOSP 源码中发现大纲未列出但与本节强相关的知识点，
> 可**就地插入**最相关的锚点之后，并用 `[自动发现]` 标注，方便后续 review。
> 锚点内容需 L1/L2 验证，扩展内容至少 L2 验证，自动发现内容至少标注来源。
<!-- outline-end -->

## 为什么要了解 WebView 性能优化实战

WebView 页面慢，用户通常感知到的是白屏、点不动、滑不顺、偶发重载。对客户端来说，这类问题不能只交给前端，也不能只看 Android 的 View 渲染。WebView 打开一个页面时，会同时消耗宿主 Activity 创建、WebView provider 初始化、网络请求、HTML/CSS/JS 解析、Chromium 合成、Android 显示提交几段时间。

工程侧治理集中在预热、复用、离线包、资源拦截、JS Bridge 和内存回收这些能落到代码里的动作。WebView 的 Chromium 线程模型、GL Functor、`SurfaceControl` 子 Surface 和 Perfetto 识别方式，详见 7.11 与 18.13 节。

[结构参考: Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 39.md]

## 先定义 WebView 页面打开时间

WebView 优化先把目标量出来。只看 `Activity.onCreate()` 或 `WebView.loadUrl()` 的耗时不够，用户关心的是页面从点击到首屏可读、可点的时间。可以按下面三个点拆分：

- **T0：入口点击时间**。用户点击 Native 入口，或业务调用打开 H5 容器的时间。
- **T1：容器可见时间**。Activity / Fragment 显示，WebView 已加入 View 树，但页面内容可能还没完成。
- **T2：首屏可交互时间**。页面主文档、首屏 CSS/JS、首屏数据和必要图片完成后，用户能读、能点、能滑。

客户端负责 T0 到 T1，也影响 T1 到 T2。前端资源体积、服务器渲染、缓存命中会直接改变 T2；客户端的 WebView 预热、离线包、资源拦截和 Bridge 设计决定这段时间能不能稳定下来。

一个可执行的埋点方案如下：

```kotlin
class H5PageTiming(private val pageId: String) {
    private val points = linkedMapOf<String, Long>()

    fun mark(name: String) {
        points[name] = SystemClock.elapsedRealtime()
    }

    fun report(extra: Map<String, String>) {
        val start = points["open_click"] ?: return
        val payload = points.mapValues { (_, value) -> value - start } + extra
        H5Metrics.report(pageId, payload)
    }
}
```

这段代码只做时间点收集，业务侧还要补齐 WebView provider 版本、是否命中预热、是否命中离线包、网络类型、页面 URL 模板和前端版本。没有这些维度，平均耗时下降很容易掩盖低端机、弱网或特定 provider 的问题。

[已验证: 官方文档, developer.android.com/reference/android/webkit/WebView]

## WebView 初始化耗时优化

### 初始化成本来自哪里

第一次创建 WebView 时，宿主进程会通过 `WebViewFactory` 选择并装载 provider，初始化 Chromium browser-side 组件，准备 renderer、GPU service、网络服务和缓存目录。这个成本和普通 View inflate 不在一个量级。首次创建之后，同进程内再创建 WebView 通常会复用已装载的 provider 和一部分基础状态，所以首个实例和后续实例的耗时差异会很明显。

Perfetto 里常见的现象是：MainThread 上第一次创建 WebView 有较长的 provider 初始化片段，随后出现 `WebViewChromium*`、`CrRendererMain`、`Compositor` 或 `CrGpuMain` 相关线程。第二次打开同类页面时，宿主侧初始化片段会缩短，瓶颈更多转向网络、JS 和渲染。线程名和进程模型的判断详见 7.11 节。

[已验证: AOSP android-17.0.0_r1, frameworks/base/core/java/android/webkit/WebView.java]
[已验证: AOSP android-17.0.0_r1, frameworks/base/core/java/android/webkit/WebViewFactory.java]

### 预热要放在首帧之后

WebView 预热的目标是把 provider 装载和 Chromium 基础初始化挪到用户点击之前。它不能抢 App 冷启动首帧，也不应该在 `Application.onCreate()` 里无条件执行。更稳的做法是：首屏显示完成后，等主线程空闲，再根据业务命中率预热。

```kotlin
class WebViewWarmup(private val appContext: Context) {
    private var warmed = false
    private var warmupView: WebView? = null

    fun warmupAfterFirstFrame(activity: Activity) {
        if (warmed) return
        activity.window.decorView.post {
            Looper.myQueue().addIdleHandler {
                if (!warmed) {
                    warmupView = WebView(appContext).apply {
                        loadUrl("about:blank")
                    }
                    warmed = true
                }
                false
            }
        }
    }

    fun release() {
        Handler(Looper.getMainLooper()).post {
            warmupView?.destroy()
            warmupView = null
            warmed = false
        }
    }
}
```

这里用 `applicationContext` 是因为这个实例不展示、不弹窗、不参与 Activity 主题。展示态 WebView 仍然要使用 Activity 或带主题的 UI Context，否则文件选择器、窗口 token、Autofill 和主题资源都可能出问题。预热实例如果要复用到真实页面，必须确认 Context、生命周期和页面隔离都可控；大多数业务只用它触发初始化，不直接拿来展示。

[已验证: 官方文档, developer.android.com/develop/ui/views/layout/webapps/webview]
[已验证: AOSP android-17.0.0_r1, frameworks/base/core/java/android/webkit/WebView.java]

### 用轻量 API 做 provider 预装载

如果目标只是提前装载 provider，而不是预创建完整页面，可以调用 `WebSettings.getDefaultUserAgent(context)`。它比创建 WebView 实例轻，但覆盖范围也更窄：可以提前触发 provider 选择、部分 native library 装载和默认 UA 读取，不会创建 `WebView` 实例、`AwContents`、renderer 进程或 compositor，也不能替代页面加载和资源缓存。

```kotlin
fun warmupUserAgent(context: Context) {
    Handler(Looper.getMainLooper()).post {
        val ua = WebSettings.getDefaultUserAgent(context.applicationContext)
        H5RuntimeCache.defaultUserAgent = ua
    }
}
```

预热策略要和数据一起发布：记录预热开始时间、预热耗时、命中次数、未命中原因、预热后首个页面 T2。命中率低的页面不适合预热；低端机上预热还可能抬高启动期内存峰值。

[已验证: 官方文档, developer.android.com/reference/android/webkit/WebSettings]

## 预创建与 WebView 池

WebView 池适合高频、同质、可信的 H5 页面，例如活动页容器、运营页面、App 内部协议页。它不适合承载外部网页，也不适合跨账号、跨权限、跨 Activity 随意复用。复用带来的收益是减少实例创建和部分初始化成本；风险是状态污染、Context 泄漏、历史栈残留、JS Bridge 暴露面扩大。

一个最小可用的池要包含三类规则：

- **容量规则**：主进程只保留 1 到 2 个空闲实例；低内存、后台、页面退出时主动收缩。
- **准入规则**：只复用受控域名和受控容器页；外部 URL、支付页、登录页、上传页不进池。
- **清理规则**：归还前停止加载、清空历史、解绑客户端、移除 Bridge、加载空白页，并从父容器移除。

```kotlin
class WebViewPool(private val appContext: Context) {
    private val pool = ArrayDeque<WebView>()

    fun acquire(activity: Activity): WebView {
        val cached = pool.removeFirstOrNull()
        return cached ?: WebView(activity)
    }

    fun recycle(webView: WebView) {
        val parent = webView.parent as? ViewGroup
        parent?.removeView(webView)

        webView.stopLoading()
        webView.webChromeClient = null
        webView.webViewClient = null
        webView.removeJavascriptInterface("NativeBridge")
        webView.loadUrl("about:blank")
        webView.post {
            webView.clearHistory()
            if (pool.size < 1) {
                pool.addLast(webView)
            } else {
                webView.destroy()
            }
        }
    }

    fun clear() {
        while (pool.isNotEmpty()) {
            pool.removeFirst().destroy()
        }
    }
}
```

这段代码省略了业务态重置，例如 Cookie 策略、UA、混合协议白名单、调试开关和页面 JS 注入。`about:blank` 是异步加载，上例只用 `post` 避免同一调用栈内立刻清历史；生产实现更适合在空白页 `onPageFinished()` 后归还池，或者使用独立空闲实例，不要把仍在导航中的 WebView 交给下一次 `acquire()`。线上实现要把这些配置放进统一的 `configure(webView, scene)`，每次 `acquire()` 后重新设置，不能假设池里的实例仍然干净。

WebView 运行在多进程或多账号隔离场景时，还要处理 data directory。Android P 起提供 `WebView.setDataDirectorySuffix()`，必须在该进程创建任何 WebView 之前调用。多进程 App 如果没有设置不同 suffix，可能遇到数据目录锁冲突；设置之后 Cookie、LocalStorage 和缓存也会按 suffix 隔离，业务要接受这个边界。

[已验证: 官方文档, developer.android.com/reference/android/webkit/WebView#setDataDirectorySuffix]

## 离线包与资源拦截

### 缓存分层怎么选

WebView 首屏慢，很多时候来自主文档、CSS、JS 和首屏数据的网络等待。参考 Clippings 里的拆法，可以把 H5 缓存分为四层：

| 层级 | 适合缓存什么 | 收益 | 主要风险 |
|------|--------------|------|----------|
| Memory Cache | 当前会话内重复访问的资源 | 命中最快 | 页面关闭或进程回收后失效 |
| Client Cache / 离线包 | 受控页面的 HTML、CSS、JS、图片 | 弱网下收益稳定 | 版本、灰度、回滚和完整性校验复杂 |
| HTTP Cache | 标准 Web 资源 | 接入成本低 | 受服务端 header 影响，业务可控性有限 |
| Net Cache / 预连接 | DNS、TLS、连接复用 | 降低建连时间 | 命中率和服务器压力要平衡 |

离线包优先放强控制页面：App 内活动页、频道页、内嵌商城、帮助中心。用户输入 URL、第三方 OAuth、支付收银台这类页面不适合离线包拦截。


### shouldInterceptRequest 的实现边界

`WebViewClient.shouldInterceptRequest()` 可以拦截资源请求并返回本地内容。它不在 UI 线程调用，里面不能访问 View，也不能做长时间锁等待。离线包读取要走只读索引和短路径 I/O，包校验、解压和版本更新必须提前完成。

```kotlin
class OfflinePackageClient(
    private val offlineStore: OfflineStore,
    private val manifest: OfflineManifest,
    private val fallback: WebViewClient = WebViewClient()
) : WebViewClient() {
    override fun shouldInterceptRequest(
        view: WebView,
        request: WebResourceRequest
    ): WebResourceResponse? {
        val uri = request.url ?: return null
        if (request.isForMainFrame && !manifest.isAllowedMainFrame(uri)) return null
        if (!request.isForMainFrame && !manifest.isAllowedSubresource(uri)) return null

        val hit = offlineStore.open(uri) ?: return null
        return WebResourceResponse(
            hit.mimeType,
            hit.encoding,
            200,
            "OK",
            mapOf(
                "Cache-Control" to "no-store",
                "X-Offline-Package" to hit.version
            ),
            hit.inputStream
        )
    }
}
```

`OfflineManifest` 是业务侧的只读 manifest 查询接口，负责判断主文档 URL 模板、子资源 hash、MIME 和包版本。主文档和子资源要分开校验：主文档只能命中 manifest 里明确声明的 URL 模板，子资源只能命中同一包内列出的 hash、MIME 和版本；不要把任意 main frame 请求交给本地 `offlineStore` 兜底，否则外部页面、登录页或支付页可能被错误拦截。

离线包上线前要有四个检查：

- **版本匹配**：HTML、JS、CSS、图片资源使用同一 manifest；manifest 带业务版本和包 hash。
- **完整性校验**：下载后校验 hash；校验失败不能进入可用目录。
- **灰度回滚**：离线包命中率、解析错误、白屏率、JS 异常率异常时能按页面版本回滚。
- **兜底路径**：本地资源缺失时走网络，不让用户卡在空白页。

AndroidX WebKit 的 `WebViewAssetLoader` 更适合把 App 内静态资源映射成 HTTPS-like URL，用于本地帮助页、协议页、内置说明页。业务离线包如果要做动态下发，仍然要自己处理 manifest、签名、灰度和回滚。

[已验证: 官方文档, developer.android.com/reference/android/webkit/WebViewClient#shouldInterceptRequest]

### 预请求不能只看客户端收益

预请求能把主文档或首屏接口提前拉到本地，但它会制造未命中请求。入口曝光大、点击率低的页面，不适合无差别预请求。更稳的策略是按用户行为和场景触发：页面入口进入可视区、用户停留超过阈值、网络为空闲状态、电量不低、服务端允许预取。

```kotlin
fun maybePrefetch(entry: H5Entry, env: RuntimeEnv) {
    if (!entry.prefetchEnabled) return
    if (env.networkMetered || env.batteryLow) return
    if (entry.exposureToClickRate < 0.15f) return

    H5Prefetcher.enqueue(
        url = entry.url,
        priority = entry.priority,
        maxBytes = 256 * 1024
    )
}
```

预请求的指标不能只报页面 T2，也要报未命中流量、服务端 QPS、取消率和过期率。客户端省下 100 ms，如果换来服务端峰值压力和大量废请求，这个方案就不划算。


## JS Bridge 性能优化

### Bridge 方法要短、异步、可取消

`@JavascriptInterface` 方法运行在 WebView 的私有后台线程，但页面发起 JS 到 Java 的调用时，JS 侧会等待返回。Bridge 方法里做同步 I/O、数据库锁等待、网络请求、跨线程 `join()`，会拖住页面执行，严重时会让宿主侧也出现卡顿或 ANR。线程模型和机制解释详见 7.11 节。

```kotlin
class NativeBridge(
    private val scope: CoroutineScope,
    private val dispatcher: CoroutineDispatcher,
    private val callback: (String, String) -> Unit
) {
    @JavascriptInterface
    fun requestUserInfo(callbackId: String) {
        scope.launch(dispatcher) {
            val result = userRepository.loadUserInfo()
            withContext(Dispatchers.Main) {
                callback(callbackId, result.toJson())
            }
        }
    }
}
```

这类接口不要直接返回复杂数据。JS 侧传 `callbackId`，Native 异步完成后通过 `evaluateJavascript()` 回调。这样能把 Bridge 调用从同步返回改成异步完成，避免把耗时任务放进一次 JS 调用里。

[已验证: 官方文档, developer.android.com/reference/android/webkit/JavascriptInterface]

### 批量传输，少做来回调用

Bridge 频繁来回调用比单次大 payload 更容易伤性能。常见问题包括：JS 循环调用 Native 获取配置、Native 分多次回调 JS 更新状态、每个埋点都单独过 Bridge。更好的做法是批量请求、批量返回、批量上报。

```javascript
// JS 侧：批量请求 Native 能力
window.NativeBridge.invoke(JSON.stringify({
  id: "req_1024",
  method: "getRuntimeInfo",
  params: {
    keys: ["user", "device", "network", "ab", "theme"]
  }
}))
```

```kotlin
@JavascriptInterface
fun invoke(raw: String) {
    val request = bridgeCodec.decode(raw)
    bridgeDispatcher.dispatch(request)
}
```

Bridge 协议要固定字段、限制 payload 大小、限制方法白名单，并记录每个方法的调用次数、耗时、失败码和 payload 字节数。线上排查时，Bridge 指标常常比 WebView 自身指标更快暴露问题。

### evaluateJavascript 只做异步回调

`evaluateJavascript()` 必须在 UI 线程调用，结果也在 UI 线程回调。它是异步 API，不能在 MainThread 上用 `CountDownLatch.await()`、`Future.get()` 等方式等待结果。

```kotlin
fun WebView.callJsAsync(script: String, onResult: (String?) -> Unit) {
    if (Looper.myLooper() == Looper.getMainLooper()) {
        evaluateJavascript(script, onResult)
    } else {
        post { evaluateJavascript(script, onResult) }
    }
}
```

如果业务需要“同步语义”，用状态机或协程挂起封装，但底层仍然不能阻塞 MainThread。超时、页面销毁、renderer 退出都要能取消等待。

[已验证: 官方文档, developer.android.com/reference/android/webkit/WebView#evaluateJavascript]

### Bridge 暴露面要收窄

`addJavascriptInterface()` 会把对象暴露给页面脚本。现代 Android 已要求通过 `@JavascriptInterface` 暴露方法，但这不等于可以把完整业务对象塞给 WebView。安全和性能要一起收：

- 只给可信域名注入 Bridge；外部网页不注入或只注入只读能力。
- Bridge 对象只暴露一个 `invoke(String json)` 入口，再在 native 层做方法白名单。
- 每个方法定义最大 payload、超时、线程和可取消策略。
- 页面销毁时调用 `removeJavascriptInterface()` 并清空回调表。

[已验证: 官方文档, developer.android.com/reference/android/webkit/WebView#addJavascriptInterface]

## 页面侧配合：首屏优先

客户端优化不能抵消页面本身过重。WebView 页面首屏通常按三段看：Native 容器时间、网络时间、渲染时间。客户端能做的是缩短容器时间、提高缓存命中、降低 Bridge 往返；页面侧仍然要控制首屏资源和 JS 长任务。

对 App 内受控 H5 页面，可以把下面几条写进页面接入规范：

- 主文档尽量小，首屏 CSS 内联或提前下发，非首屏 JS 延迟加载。
- 首屏图片按展示尺寸裁剪，避免把大图交给 WebView 再缩放。
- 滚动期间避免同步布局读写，动画优先使用 `transform` 和 `opacity`。
- 首屏接口合并，减少串行请求；可 SSR 的页面优先服务端输出可读 HTML。
- Native 注入的运行时信息批量提供，避免 JS 循环调用 Bridge。

这些约束要进入发布前检查，而不是等线上白屏率升高后再人工排查。页面属于运营活动时，客户端还要把离线包版本、前端 bundle 版本和容器版本一起写入埋点。

[结构参考: Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 39.md]

## 扩展：WebView 内存泄漏治理

WebView 内存问题分两类：宿主 App 使用方式造成的泄漏，以及 Chromium / renderer 侧资源没有及时回收。前者要通过生命周期治理解决，后者要靠 provider 版本、页面复杂度和 renderer 容灾一起看。

展示态 WebView 释放时，顺序要稳定：

```kotlin
fun destroyWebView(webView: WebView?) {
    webView ?: return
    if (Looper.myLooper() != Looper.getMainLooper()) {
        webView.post { destroyWebView(webView) }
        return
    }

    val parent = webView.parent as? ViewGroup
    parent?.removeView(webView)

    webView.stopLoading()
    webView.webChromeClient = null
    webView.webViewClient = null
    webView.removeJavascriptInterface("NativeBridge")
    webView.loadUrl("about:blank")
    webView.post {
        webView.clearHistory()
        webView.destroy()
    }
}
```

`destroy()` 必须在创建该 WebView 的线程调用；展示态 WebView 通常就是 MainThread。`about:blank` 导航和历史清理也有异步边界，严格清理要等空白页加载完成，或者至少把 `clearHistory()` 放到下一轮消息后执行。只调用 `destroy()` 但没有从父容器移除，或者 Bridge / callback 仍然持有 Activity，都可能让 Activity 无法释放。内存泄漏排查时可以组合使用 LeakCanary、`dumpsys meminfo`、Perfetto 内存计数器和 Chrome DevTools Memory 面板。

[已验证: AOSP android-17.0.0_r1, frameworks/base/core/java/android/webkit/WebView.java]

### Renderer 退出后的恢复

Android 8.0 之后，WebView renderer 进程异常退出时，应用可以在 `WebViewClient.onRenderProcessGone()` 里处理。默认实现返回 `false`，可能导致宿主 App 崩溃或被系统杀死；业务应该返回 `true`，移除旧实例，清理引用，再按需重建。

```kotlin
interface RendererRetryBudget {
    fun tryAcquire(url: String?, didCrash: Boolean): Boolean
}

class RecoverableWebViewClient(
    private val activity: Activity,
    private val container: ViewGroup,
    private val factory: () -> WebView,
    private val retryBudget: RendererRetryBudget
) : WebViewClient() {
    override fun onRenderProcessGone(
        view: WebView,
        detail: RenderProcessGoneDetail
    ): Boolean {
        val lastUrl = view.url
        (view.parent as? ViewGroup)?.removeView(view)
        view.destroy()

        if (activity.isDestroyed || !container.isAttachedToWindow) {
            H5Metrics.reportRendererGoneAborted("lifecycle_finished")
            return true
        }
        if (!retryBudget.tryAcquire(lastUrl, detail.didCrash())) {
            H5Metrics.reportRendererGoneAborted("retry_budget_exhausted")
            return true
        }

        val next = factory()
        container.addView(next)
        if (!lastUrl.isNullOrBlank()) {
            next.loadUrl(lastUrl)
        }
        H5Metrics.reportRendererGone(
            didCrash = detail.didCrash(),
            priority = detail.rendererPriorityAtExit()
        )
        return true
    }
}
```

多个 WebView 可能关联同一个 renderer；renderer 退出时，系统会对每个受影响的 WebView 分别回调 `onRenderProcessGone()`。每次回调都要移除并销毁参数里的 `view`，不要复用已受影响的实例，也不要把第一轮回调理解成只有这一个实例受影响。重建必须受 Activity/容器生命周期和重试预算约束；如果同一个 URL 模板连续触发 renderer OOM，继续自动重建会形成循环，应该停在错误页或降级页。业务还要记录 `didCrash()`、provider 版本、页面 URL 模板、内存水位、重建结果和预算耗尽原因，这些数据能帮助区分页面内存过高、provider bug 和低内存设备问题。

[已验证: AOSP android-17.0.0_r1, frameworks/base/core/java/android/webkit/WebViewClient.java]
[已验证: AOSP android-17.0.0_r1, frameworks/base/core/java/android/webkit/RenderProcessGoneDetail.java]
[已验证: 官方文档, developer.android.com/reference/android/webkit/WebViewClient#onRenderProcessGone]

### 32 位进程的 WebView 预留地址空间

参考书中提到，部分 Android 版本会在进程 maps 中出现 `libwebview reservation` 一类预留虚拟地址空间。这个点更适合作为专项排查，不适合作为通用优化。只有在 32 位进程、主进程确定不使用系统 WebView、并且已经把 WebView 放到独立进程时，才有讨论释放预留地址空间的价值；而且它依赖 native 实现、系统版本、provider 行为和兼容性验证，风险高于常规内存治理。

本书的建议口径是：优先通过 WebView 独立进程、页面退出释放、renderer 容灾和缓存上限治理内存。对 `libwebview reservation` 的 native 释放方案，只记录为专项研究方向，不进入默认实践清单。

[待验证: 不同 Android 版本和 provider 下 `libwebview reservation` 命名、大小和释放副作用需要实机验证]

## 实战检查清单

| 检查项 | 推荐做法 | 观察指标 |
|--------|----------|----------|
| 初始化 | 首帧后空闲预热，记录预热命中 | 预热耗时、命中率、T1 / T2 |
| WebView 池 | 只复用受控页面，归还前完整清理 | 池命中率、复用后错误率、内存峰值 |
| 离线包 | manifest + hash + 灰度 + 回滚 | 离线包命中率、白屏率、版本错误 |
| 资源拦截 | `shouldInterceptRequest()` 只做短路径读取 | 拦截耗时、miss 原因、兜底成功率 |
| JS Bridge | 异步、批量、白名单、限制 payload | Bridge 调用次数、P95 耗时、失败码 |
| 页面侧 | 首屏资源收敛，SSR / 预请求按命中率使用 | T2、首屏 JS 长任务、首屏请求数 |
| 内存 | 退出移除父容器、解绑客户端、销毁实例 | PSS、native heap、泄漏对象数 |
| Renderer 容灾 | `onRenderProcessGone()` 返回 true 并重建 | renderer gone 次数、重建成功率 |

WebView 的实战优化不要追求单点技巧。预热、离线包、Bridge、页面首屏和内存回收必须一起进指标系统，否则很容易把白屏转成卡顿，把启动收益转成内存峰值，把客户端收益转成服务端压力。
