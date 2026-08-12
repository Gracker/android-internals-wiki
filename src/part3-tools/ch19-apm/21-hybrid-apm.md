---
status: finalized
applicable_versions: "Android 8 (API 26) - Android 17 (API 37)"
chapter: "19"
confidence: high
last_verified: "2026-04-25"
last_verified_against: "Android PixelCopy / WebViewRenderProcess APIs, Flutter FrameTiming docs, Flutter 3.32 thread merge (issue #150525 + release-notes-3.32.0)"
pipeline_stage: ready-to-publish
related_chapters:
  - "19.0"
  - "19.01"
section: "19.21"
sources:
- type: official
  path: https://developer.android.com/reference/android/view/PixelCopy
- type: official
  path: https://developer.android.com/reference/android/webkit/WebViewClient#onRenderProcessGone(android.webkit.WebView,%20android.webkit.RenderProcessGoneDetail)
- type: official
  path: https://developer.android.com/reference/android/webkit/WebViewRenderProcessClient
- type: reference
  path: https://api.flutter.dev/flutter/dart-ui/FrameTiming-class.html
- type: reference
  path: https://api.flutter.dev/flutter/scheduler/SchedulerBinding/addTimingsCallback.html
tags:
  - apm
  - webview
  - flutter
  - hybrid
task2b_state: fixed
task6_state: reviewed
task9_state: reviewed
title: "混合栈与跨平台 APM (WebView / Flutter)"
---
# 混合栈与跨平台 APM (WebView / Flutter)

混合栈 APM 需要同时尊重三套运行时的语义。Android 宿主知道 Activity、Window、主线程、网络和 native crash；WebView 才知道 Navigation Timing、FCP、LCP、DOM 与 JavaScript；Flutter engine 才能把 framework build、raster 和 Dart 异常分开。把三边事件放进同一条会话时间线很有价值，把它们压成一个“首屏耗时”会丢失诊断信息。

平台源码固定在 Android 17 / API 37 / `android-17.0.0_r1`。WebView 能力还取决于可独立更新的 provider/Chromium 版本，Flutter 行为取决于 APK 携带的 engine revision。Android 版本不能替代这两个版本轴。

## 1. WebView 加载：用事件时间线计算端到端耗时

### 1.1 容器、导航和内容就绪是不同阶段

Native 负责创建一次 `session_id`，每次 main-frame 导航再分配 `navigation_id`。一条 WebView 加载时间线可以包含：

| 阶段 | Native 事件 | Web 事件 | 结论边界 |
| --- | --- | --- | --- |
| 容器创建 | Activity/Fragment 进入、WebView 构造、attach | 无 | 宿主准备成本 |
| 导航请求 | `loadUrl()`、用户点击、重定向策略 | Navigation Timing | 请求发起和页面 time origin |
| main-frame 状态 | `onPageStarted()`、`onPageCommitVisible()`、`onPageFinished()` | `DOMContentLoaded`、`loadEventEnd` | 文档生命周期；不直接证明内容有效 |
| 内容出现 | Window 首帧、visual-state callback | FCP、LCP candidate | 页面开始绘制和主要内容候选 |
| 业务可用 | Bridge ready、首个可用交互 | 业务 `app_ready` | 产品定义的可操作状态 |

`onPageFinished()` 只表示 main frame 加载完成。官方 API 还明确说明，它不保证下一帧已经包含当时的 DOM。FCP、LCP 和业务 ready 各自回答不同问题：FCP 关注首个内容，LCP 关注加载过程中的最大内容候选，业务 ready 才能表达数据、路由和关键交互已经可用。

TTI 没有对应的浏览器 Performance Entry。Lighthouse 10 已移除 TTI，因为它对离群网络请求和 long task 过于敏感。线上 WebView 应采用明确的业务 `app_ready`，并按 provider 支持情况补充 LCP、Long Tasks 或 INP；不要从 `loadEventEnd` 推导一个名为 TTI 的值。

SPA 的 same-document 路由也不会自动产生新的 Navigation Timing 或重置 LCP。H5 路由层需要发出独立的 `route_id`、route start 和 route ready，APM 不能把一次 document load 的 LCP 重复归给后续每个软导航。

### 1.2 `performance.now()` 与 `elapsedRealtime` 需要校准

Web 指标的 `startTime` 和 `performance.now()` 都相对于当前页面的 `performance.timeOrigin`。Native 事件通常使用 `SystemClock.elapsedRealtime()`。把 Native 发起 `evaluateJavascript()` 的时刻直接配给脚本中的 `performance.now()` 会忽略 UI 排队、renderer 调度和回传延迟。

可操作的校准方法是做多次往返采样：

1. Native 在调用 `evaluateJavascript("performance.now()")` 前记录 `t0`。
2. 回调到达 Native 时记录 `t1`，解析 JS 返回的 `jsNow`。
3. 暂用 `(t0 + t1) / 2` 估计 JS 执行时刻，误差下限记录为 round-trip time 的一半。
4. 取多次采样中 round-trip time 最小的一组，得到 `nativeElapsed ≈ jsTime + offset`。
5. 每次 main-frame 导航重新校准；进程从长时间后台恢复后再做一次，检查漂移。

下面的 Kotlin 结构展示一个校准样本。它必须在 WebView 所在线程调用，回调也位于该线程。

```kotlin
data class WebClockSample(
    val navigationId: String,
    val offsetMs: Double,
    val uncertaintyMs: Double,
    val roundTripMs: Double
)

@MainThread
fun sampleWebClock(
    webView: WebView,
    navigationId: String,
    onSample: (WebClockSample?) -> Unit
) {
    val sentNs = SystemClock.elapsedRealtimeNanos()
    webView.evaluateJavascript("performance.now()") { encodedResult ->
        val receivedNs = SystemClock.elapsedRealtimeNanos()
        val jsNowMs = encodedResult?.toDoubleOrNull()
        if (jsNowMs == null) {
            onSample(null)
            return@evaluateJavascript
        }

        val roundTripMs = (receivedNs - sentNs) / 1_000_000.0
        val midpointNs = sentNs + (receivedNs - sentNs) / 2
        onSample(
            WebClockSample(
                navigationId = navigationId,
                offsetMs = midpointNs / 1_000_000.0 - jsNowMs,
                uncertaintyMs = roundTripMs / 2.0,
                roundTripMs = roundTripMs
            )
        )
    }
}
```

映射后的事件时间是 `native_elapsed_ms = offset_ms + web_entry.startTime`。端到端 FCP 应计算为“映射后的 FCP 时刻减去容器开始时刻”，不应把若干可能重叠的阶段时长相加。wall clock 只用于跨设备日志关联，并额外记录时钟偏移；用户改时间或网络校时都会使它跳变。

### 1.3 PerformanceObserver 上报要兼容 provider 差异

下面的脚本假设 Native 已通过带 origin allowlist 的 Web message listener 注入 `AndroidApm`，并注入只含短期 session、navigation 和低基数 route key 的上下文。脚本不读取原始 URL。

```javascript
(() => {
  const context = window.__APM_CONTEXT__;
  const sink = window.AndroidApm;
  if (!context || !sink || typeof sink.postMessage !== 'function') return;

  const emit = (metric, valueMs, extra = {}) => {
    sink.postMessage(JSON.stringify(Object.assign({
      sessionId: context.sessionId,
      navigationId: context.navigationId,
      routeKey: context.routeKey,
      metric,
      valueMs: Math.round(valueMs)
    }, extra)));
  };

  const canObserve = (type) => {
    if (typeof PerformanceObserver === 'undefined') return false;
    const supported = PerformanceObserver.supportedEntryTypes;
    return !Array.isArray(supported) || supported.includes(type);
  };

  if (canObserve('paint')) {
    try {
      const paintObserver = new PerformanceObserver((list, observer) => {
        const fcp = list.getEntries().find(
          (entry) => entry.name === 'first-contentful-paint'
        );
        if (fcp) {
          emit('fcp', fcp.startTime);
          observer.disconnect();
        }
      });
      paintObserver.observe({type: 'paint', buffered: true});
    } catch (_) {
      // Provider does not expose Paint Timing.
    }
  }

  let latestLcp = null;
  let lcpObserver = null;
  let lcpFlushed = false;

  const flushLcp = (reason) => {
    if (lcpFlushed || !latestLcp) return;
    lcpFlushed = true;
    emit('lcp', latestLcp.startTime, {finalizationReason: reason});
    if (lcpObserver) lcpObserver.disconnect();
  };

  if (canObserve('largest-contentful-paint')) {
    try {
      lcpObserver = new PerformanceObserver((list) => {
        const entries = list.getEntries();
        if (entries.length > 0) {
          latestLcp = entries[entries.length - 1];
        }
      });
      lcpObserver.observe({
        type: 'largest-contentful-paint',
        buffered: true
      });
      document.addEventListener('visibilitychange', () => {
        if (document.visibilityState === 'hidden') {
          flushLcp('visibility_hidden');
        }
      });
      ['pointerdown', 'keydown'].forEach((eventName) => {
        window.addEventListener(
          eventName,
          () => flushLcp('first_input'),
          {once: true, capture: true}
        );
      });
      window.addEventListener('pagehide', () => flushLcp('pagehide'));
    } catch (_) {
      lcpObserver = null;
    }
  }

  emit('bridge_ready', performance.now());
})();
```

LCP observer 给出的是候选序列。上面的实现会在首次 pointer/keyboard 输入、页面隐藏或 pagehide 时上报末个候选。页面长期可见且没有输入时，超时快照只能标记为 `lcp_candidate`，不能伪装成已结束的 LCP。LCP 规范还列出了轮播占位、bfcache 和 same-document 导航等限制，服务端要保留 `finalizationReason`。

样本同时记录 WebView provider package、versionName/Chromium major、AndroidX WebKit 版本以及 `supportedEntryTypes`。某项能力缺失时写 `unsupported`，回退到 FCP、业务 ready、DOM 与像素信号；缺失值不能当成 0。

## 2. H5 白屏：多信号判定，PixelCopy 失败不能算“有内容”

白屏检测至少需要三类信号：

| 信号 | 优点 | 容易误判的场景 |
| --- | --- | --- |
| 生命周期 | `onPageCommitVisible()`、visual-state callback、`onPageFinished()` 成本低 | 页面只画了背景，资源还未到达 |
| DOM / 业务 | 可见节点面积、文本/图片、`app_ready` | canvas、WebGL、video、跨域 iframe 与骨架屏 |
| 像素 | 接近用户看到的 Window 合成结果 | 合法白色页面、深色主题、遮罩、loading、键盘与其他覆盖层 |

`onPageCommitVisible()` 的官方语义是旧导航内容不会再被绘制；下一次 draw 可能只显示 WebView 背景，也可能显示新页面的一部分。它不能单独证明首屏有效。

`postVisualStateCallback()` 表示“调用时的 DOM 状态已经为下一次 draw 准备好”，而非“这一帧已经显示”。回调后还要等待下一次 draw，例如在 callback 中安排 `postOnAnimation`，随后才做 Window PixelCopy。visual state 覆盖普通元素、图片、CSS animation、WebGL 和 canvas，不覆盖 video tag。

### 2.1 低分辨率 PixelCopy 与三态结果

Android 8 / API 26 起可以从 Window 的指定 Rect 异步 PixelCopy。源区域会被缩放到目标 Bitmap，因此没有必要创建 WebView 原尺寸位图。Window 必须已经有 backing surface，官方建议至少等一次 draw；WebView 还要处于 attached、可见且尺寸有效的状态。

下面的 Kotlin 示例把结果分成 `Classified` 和 `Inconclusive`。PixelCopy error、空区域或尚未 attach 都不能被记成“非白屏”。

```kotlin
sealed interface PixelSample {
    data class Classified(
        val blank: Boolean,
        val blankScore: Double
    ) : PixelSample

    data class Inconclusive(
        val reason: String,
        val copyResult: Int? = null
    ) : PixelSample
}

@MainThread
@RequiresApi(26)
fun sampleWebViewPixels(
    activity: Activity,
    webView: WebView,
    workerHandler: Handler,
    onResult: (PixelSample) -> Unit
) {
    if (!webView.isAttachedToWindow ||
        webView.width <= 0 ||
        webView.height <= 0
    ) {
        workerHandler.post {
            onResult(PixelSample.Inconclusive("view_not_ready"))
        }
        return
    }

    val location = IntArray(2)
    webView.getLocationInWindow(location)
    val source = Rect(
        location[0],
        location[1],
        location[0] + webView.width,
        location[1] + minOf(webView.height, 720)
    )

    val decor = activity.window.decorView
    if (!source.intersect(0, 0, decor.width, decor.height) ||
        source.isEmpty
    ) {
        workerHandler.post {
            onResult(PixelSample.Inconclusive("empty_window_rect"))
        }
        return
    }

    val sampleWidth = 160
    val sampleHeight = (
        source.height().toDouble() * sampleWidth / source.width()
    ).roundToInt().coerceIn(1, 320)
    val bitmap = Bitmap.createBitmap(
        sampleWidth,
        sampleHeight,
        Bitmap.Config.ARGB_8888
    )

    try {
        PixelCopy.request(activity.window, source, bitmap, { copyResult ->
            val sample = try {
                if (copyResult == PixelCopy.SUCCESS) {
                    WhiteScreenDetector.classify(bitmap)
                } else {
                    PixelSample.Inconclusive(
                        reason = "pixel_copy_failed",
                        copyResult = copyResult
                    )
                }
            } catch (error: RuntimeException) {
                PixelSample.Inconclusive("classifier_failed")
            } finally {
                bitmap.recycle()
            }
            onResult(sample)
        }, workerHandler)
    } catch (error: IllegalArgumentException) {
        bitmap.recycle()
        workerHandler.post {
            onResult(PixelSample.Inconclusive("window_surface_not_ready"))
        }
    }
}
```

几何信息在主线程读取，所有结果都在 worker Handler 交付，便于接入串行状态机。分类器即使抛出运行时异常，`finally` 也会回收 Bitmap。API 34 新增了 `PixelCopy.Request` / `Result` 形式，API 26 的回调形式在 Android 17 上仍可使用。

像素分类可组合近背景色比例、颜色熵、边缘/有效色块和页面主题基线。Bitmap 只在设备内分析，随后立即释放，不上传截图。采样 Rect 还要排除 Native toolbar、骨架层和固定遮罩，否则分类的是整个窗口覆盖关系，未必是 WebView 内容。

### 2.2 从“疑似”到“确认”

建议采用状态机：

- `loading`：main-frame 导航已开始；
- `visual_committed`：旧内容已经退出，等待下一次 draw；
- `suspected_blank`：业务 ready 超时，且 DOM 或首次像素信号为空；
- `confirmed_blank`：间隔采样仍为空，并排除 renderer gone、网络错误、容器隐藏和合法空状态；
- `inconclusive`：PixelCopy 失败、页面在后台、尺寸无效或证据相互冲突。

页面进入后台后，JS timer、renderer 和 App 进程都可能被节流或冻结。此时 heartbeat 超时与 PixelCopy 无数据只能记成不可判定。线上按关键超时点采样一到两次，不按帧截图；白屏检测的 CPU、Bitmap 字节和执行时长也应进入 APM 自监控。

## 3. WebView renderer：退出是直接证据，无响应是状态信号

WebView 在 Android 8 及以上可能把网页渲染放在沙箱 renderer 进程。renderer 退出时，App 进程未必退出，因此只接 Java/Kotlin crash handler 会漏掉一类黑屏、白屏和页面重载。

### 3.1 API 26+：`onRenderProcessGone()` 之后不能复用旧 WebView

`WebViewClient.onRenderProcessGone()` 是 renderer 已退出的直接证据：

- `didCrash()` 为 `true` 表示 renderer crash，为 `false` 通常表示系统终止了 renderer；
- `rendererPriorityAtExit()` 记录退出时的绑定优先级，它不是进程被杀原因；
- 一个 renderer 可以服务同一 App 的多个 WebView，每个受影响 WebView 都会收到回调；
- 回调只负责参数中的 WebView，不应猜测其他实例是否受影响；
- 该 WebView 已不可用，必须移出视图树、销毁并清除 Activity、Fragment、adapter 和缓存中的引用；
- 只有完成清理并准备恢复页面时才返回 `true`。返回 `false` 会让 renderer crash 导致 App crash，或让系统结束 App。

下面的客户端只展示退出处理的关键顺序。`onDeadWebView` 需要由容器清除自己持有的强引用，并决定显示错误页还是创建新 WebView。

```kotlin
class ApmWebViewClient(
    private val navigationIdOf: (WebView) -> String?,
    private val reportExit: (RendererExitSample) -> Unit,
    private val onDeadWebView: (WebView) -> Unit
) : WebViewClient() {

    override fun onRenderProcessGone(
        view: WebView,
        detail: RenderProcessGoneDetail
    ): Boolean {
        reportExit(
            RendererExitSample(
                navigationId = navigationIdOf(view),
                didCrash = detail.didCrash(),
                rendererPriorityAtExit =
                    detail.rendererPriorityAtExit(),
                observedElapsedMs =
                    SystemClock.elapsedRealtime()
            )
        )

        (view.parent as? ViewGroup)?.removeView(view)
        onDeadWebView(view)
        view.destroy()
        return true
    }
}
```

这段代码没有自动重放 POST、表单和支付导航。恢复策略必须依据业务幂等性决定；无条件 reload 可能产生重复提交。样本还要记录 provider 版本、前后台状态、进程内存压力、容器是否仍可见，以及退出前最近一次导航和 Bridge 活动。

### 3.2 API 29+：unresponsive 回调可能重复

`WebViewRenderProcessClient.onRenderProcessUnresponsive()` 表示 renderer 在合理时间内没有处理输入或导航，常见诱因包括长时间 JavaScript 任务。只要 renderer 保持无响应，回调就可能继续到达，连续两次的最短间隔是 5 秒；恢复时 `onRenderProcessResponsive()` 回调一次。注册同一 client 的多个 WebView 也可能因同一个 renderer 事件分别收到通知。

这类回调适合形成一段状态区间：

```text
renderer_unresponsive_start
renderer_unresponsive_repeat
renderer_responsive
```

APM 对 repeat 做计数，避免每 5 秒生成一条独立故障。`renderer` 参数在 single-process 模式下可以为 `null`。收到 unresponsive 后也不应默认调用 `terminate()`：终止共享 renderer 会影响其他 WebView，并要求所有受影响实例都正确处理随后到达的 `onRenderProcessGone()`。

AndroidX WebKit 的兼容接口要先用相应 `WebViewFeature` 检查 provider 能力。它可以让某些功能在较低 Android API 上由新 provider 提供，所以“API level 不够”与“当前 provider 不支持”是两种不同结论。

### 3.3 没有直接回调时只能标记 `suspected`

API 26—28 没有平台 `WebViewRenderProcessClient`；provider 不支持兼容接口时，只能组合业务 ready 超时、Bridge heartbeat、DOM 状态和像素采样。这些信号不能证明 renderer 已卡死：

- 后台页面的 timer、renderer 与 App 进程都可能被节流或冻结；
- main frame 完成不代表异步数据和子资源完成；
- 长任务会延迟 heartbeat，但它也可能是业务允许的计算；
- 网络失败、页面跳转和容器销毁都可能让心跳消失。

因此样本要明确写 `signal_strength=direct|state|suspected` 和 `signal_source`。只有 `onRenderProcessGone()` 能把 renderer 退出写成直接事件；超时推断不能冒充 crash。

## 4. JSBridge：先保证来源可信，再测排队和序列化

Bridge 的风险与性能问题经常同时出现。一个允许任意 frame 调用的高频接口，既可能被不可信 iframe 触发，也会把解析和线程切换成本压到宿主。

### 4.1 优先使用带 origin 规则的 Web message listener

当前 AndroidX WebKit 首选 `WebViewCompat.addWebMessageListener()`。它按 `allowedOriginRules` 注入对象，回调还能得到 `sourceOrigin` 与 `isMainFrame`。使用前检查 `WebViewFeature.WEB_MESSAGE_LISTENER`，规则写完整 scheme、host 和必要的 port，不使用 `*`。

下面的安装代码只接受受控 HTTPS 主 frame，并在 UI 回调中限制字符串长度。JSON 解析和落盘交给有界 worker queue。

```kotlin
@UiThread
fun installApmMessageListener(
    webView: WebView,
    worker: Executor,
    enqueue: (
        payload: String,
        sourceOrigin: Uri,
        receivedElapsedNs: Long,
        workerStartElapsedNs: Long
    ) -> Unit
): Boolean {
    if (!WebViewFeature.isFeatureSupported(
            WebViewFeature.WEB_MESSAGE_LISTENER
        )
    ) {
        return false
    }

    val trustedOrigin = Uri.parse("https://m.example.com")
    WebViewCompat.addWebMessageListener(
        webView,
        "AndroidApm",
        setOf(trustedOrigin.toString()),
        object : WebViewCompat.WebMessageListener {
            override fun onPostMessage(
                view: WebView,
                message: WebMessageCompat,
                sourceOrigin: Uri,
                isMainFrame: Boolean,
                replyProxy: JavaScriptReplyProxy
            ) {
                val receivedNs =
                    SystemClock.elapsedRealtimeNanos()
                val payload = message.data ?: return

                if (!isMainFrame ||
                    sourceOrigin != trustedOrigin ||
                    payload.length > 64 * 1024
                ) {
                    return
                }

                worker.execute {
                    enqueue(
                        payload,
                        sourceOrigin,
                        receivedNs,
                        SystemClock.elapsedRealtimeNanos()
                    )
                }
            }
        }
    )
    return true
}
```

allowlist 是第一道来源约束，回调里的 main-frame 与精确 origin 检查是防御性校验。生产实现还要验证消息 schema、事件名、session 与 navigation 是否仍有效，并对 worker queue 设置容量；队列满时丢弃低价值性能样本并累计 drop count，不能无限堆积。Native 主动向页面发送 Web message 时也应指定精确 `targetOrigin`。

### 4.2 `addJavascriptInterface()` 的兼容边界

旧 provider 只能使用 `addJavascriptInterface()` 时，需要接受以下约束：

- 对象会注入页面的所有 frame，包括 iframe；
- App 无法从接口调用中可靠识别调用 frame 的 origin，`WebView.getUrl()` 也不能回答这个问题；
- JavaScript 调 Java 是同步的，JavaScript 会等方法返回；
- 被注解的 Java 方法运行在 WebView 的私有后台线程，不在主线程；
- `removeJavascriptInterface()` 的变化要到下一次页面 reload 才反映到 JavaScript。

所以该接口只用于 App 完全控制的文档，不加载第三方 iframe，不让不可信导航复用同一 WebView。暴露的方法只复制小载荷并入有界队列，不同步等待主线程、网络或磁盘。需要切到主线程的工作应异步完成，再由独立消息返回结果。

Native 调 JavaScript 时，`evaluateJavascript()` 必须在 WebView 的 UI 线程调用，结果回调也在 UI 线程。它虽然是异步 API，调用之前的 UI 排队、renderer 执行、结果序列化和回调派发仍可能很慢。

### 4.3 一次 Bridge 调用要拆成可解释的阶段

建议为抽样调用记录：

- `direction`：`js_to_native` 或 `native_to_js`；
- `method_key`：低基数方法标识，不存业务参数；
- `payload_bytes` 与 `result_bytes`：按 UTF-8 或二进制实际字节计算；
- `source_origin_key`、`is_main_frame`、provider 版本；
- `receive_elapsed_ns`、`worker_start_elapsed_ns`、`finish_elapsed_ns`；
- queue wait、解析、业务处理、结果编码和端到端耗时；
- queue depth、drop count、是否超时或取消。

高频埋点按批发送，动画与滚动期间提高丢弃优先级。base64 图片、完整 HTML、token、URL query 和用户输入不进入 APM。监控代码的 CPU、内存分配、queue wait 与主线程占用也要抽样上报，否则 Bridge APM 可能成为新的卡顿来源。

## 5. Flutter APM：版本决定线程归属，`FrameTiming` 决定诊断语义

Flutter 不能按一个固定线程模型解释。APK 携带的 framework/engine revision、embedder 配置与运行时 trace 比 Android API level 更有判别力。

### 5.1 merged platform/UI thread 的版本边界

| Flutter 范围 | Android 主线行为 | APM 处理 |
| --- | --- | --- |
| 3.28 及更早 | Platform 与 UI runner 通常分离 | 分开观察 Android 主线程和 Dart UI runner |
| 3.29—3.31 | merged-thread 迁移期 | 读取 engine revision 与 trace，不凭版本号猜测 |
| 3.32—3.37 | stable 默认合并，仍存在 opt-out | 记录实际配置；默认 Main(UI+Platform) / Raster / IO |
| 3.38 及以后 Android 主线 | `FlutterLoader` 拒绝旧 opt-out manifest key | 主线按合并模型解释；定制 engine/embedder 仍需核验 |

合并后，Dart framework 的 build/layout/paint 与 Android Platform/插件回调共享宿主主线程；Raster 和 IO runner 仍是独立角色。耗时 MethodChannel handler 会挤压 Dart UI 工作，反过来，长 Dart build 也会推迟 platform callback。旧版或定制 engine 中，两类任务可能在不同 OS 线程，不能套用这一因果关系。

### 5.2 Flutter 与 Android Choreographer 的关系

Flutter 并非脱离 Android vsync。engine 的 Android VsyncWaiter 会从平台 vsync 源取得时序：当前 engine 可走 NDK `AChoreographer` 路径，Java 实现使用 `Choreographer.postFrameCallback()` 并把 vsync 交给 `FlutterJNI.onVsync()`。engine 再据此调度 Dart frame 与 raster。

但“使用同一个 vsync 源”不等于“走完整 Android View 绘制阶段”。FlutterView 完成宿主接入后，纯 Flutter 内容的 build、layer tree 与 raster 位于 engine 内部。JankStats、FrameMetrics 或主线程 message 只能看到宿主侧症状，不能回答是 Dart build 慢、raster 慢还是 pipeline latency 高。`FrameTiming` 才提供这三个维度；需要逐帧线程关联时再采 Perfetto。

### 5.3 `FrameTiming` 同时看 build、raster 与 total span

`SchedulerBinding.addTimingsCallback()` 是适合线上采样的入口：

- `buildDuration` 是 framework build 阶段耗时；
- `rasterDuration` 是 raster 阶段耗时；
- `totalSpan` 从 vsync start 延伸到 raster finish，用于观察端到端 pipeline latency；
- 回调列表按帧时间升序排列；
- release 约每 1 秒批量交付，debug/profile 约每 100 ms；首帧立即交付；
- 同一 callback 添加两次会执行两次，停止采集时要用同一实例移除。

判断 missed frame 时，build 或 raster 超过当帧预算值得关注；判断触控延迟时还要看 `totalSpan`。流水并行下，build 和 raster 可能各自未超预算，但组合后的 pipeline latency 已超过一个刷新周期。固定阈值 `16 ms` 只适合约 60 Hz；可变刷新率设备要记录当时 display mode 或可观测的 vsync interval，并允许阈值带有不确定性。

下面的 reporter 保留 callback 引用、直接把 Map 交给 StandardMethodCodec，并提供采样入口。它不会先 `jsonEncode()` 再让 MethodChannel 编码第二次。

```dart
import 'dart:async';
import 'dart:ui';

import 'package:flutter/scheduler.dart';
import 'package:flutter/services.dart';

class FlutterFrameReporter {
  FlutterFrameReporter({
    required this.sessionId,
    required this.engineId,
    required this.shouldKeep,
    MethodChannel? channel,
  }) : _channel =
           channel ?? const MethodChannel('apm/flutter_frame');

  final String sessionId;
  final String engineId;
  final bool Function(FrameTiming timing) shouldKeep;
  final MethodChannel _channel;

  TimingsCallback? _callback;

  void start() {
    if (_callback != null) return;

    _callback = (List<FrameTiming> timings) {
      final frames = <Map<String, Object>>[];
      for (final timing in timings) {
        if (!shouldKeep(timing)) continue;

        frames.add(<String, Object>{
          'frameNumber': timing.frameNumber,
          'buildUs': timing.buildDuration.inMicroseconds,
          'rasterUs': timing.rasterDuration.inMicroseconds,
          'totalSpanUs': timing.totalSpan.inMicroseconds,
          'rawVsyncStartUs': timing.timestampInMicroseconds(
            FramePhase.vsyncStart,
          ),
          'rawBuildStartUs': timing.timestampInMicroseconds(
            FramePhase.buildStart,
          ),
          'rawRasterFinishUs': timing.timestampInMicroseconds(
            FramePhase.rasterFinish,
          ),
        });
      }

      if (frames.isNotEmpty) {
        unawaited(_send(frames));
      }
    };

    SchedulerBinding.instance.addTimingsCallback(_callback!);
  }

  void stop() {
    final callback = _callback;
    if (callback == null) return;
    SchedulerBinding.instance.removeTimingsCallback(callback);
    _callback = null;
  }

  Future<void> _send(
    List<Map<String, Object>> frames,
  ) async {
    try {
      await _channel.invokeMethod<void>(
        'frameTimings',
        <String, Object>{
          'sessionId': sessionId,
          'engineId': engineId,
          'frames': frames,
        },
      );
    } on PlatformException {
      // Increment an in-memory drop counter; do not retry on the UI isolate.
    }
  }
}
```

这个 reporter 只解决注册、编码与批量边界。`shouldKeep` 应优先保留超预算帧，并从正常帧中抽样；`_send()` 还需要受控的 in-flight 数量，避免 Native 消费慢时累积 Future。合并线程模型下，MethodChannel 发送也会与 UI 工作竞争，采集频率不能按帧无条件全量开启。

### 5.4 raw timestamp 与 Native 接收时间不是同一个时钟

`FrameTiming.timestampInMicroseconds()` 返回 raw timestamp。同一组 `FrameTiming` 使用同一 epoch，可以做差值与排序；官方没有保证该 epoch 等于 Dart `DateTime`，也没有保证等于 Android `elapsedRealtime`。除以 1000 后直接写入 `elapsed_realtime_ms` 会制造伪精确时间。

Native 收到 `frameTimings` 时记录：

- `batch_receive_elapsed_ns`；
- `delivery_mode=batched`；
- release 约 1 秒、debug/profile 约 100 ms 的交付窗口；
- MethodChannel queue wait；
- 每帧原始 phase timestamp 与时长。

接收时间是“这一批已经到达”的上界观测，不是每帧发生时刻。帧通常位于此前一个有界批次窗口内，窗口之外还存在通道排队；不能把误差写成对称的 `±1000 ms`，也不能写成“至少 1000 ms”。按秒聚合时使用 raw 相对顺序和 duration 即可；需要与 Native ANR、binder 或 SurfaceFlinger 帧做精确关联时，应在相同测试中使用 Perfetto 的 engine、Choreographer、gfx 和 sched 轨迹。

### 5.5 Dart 异常要保留“是否已处理”的语义

`FlutterError.onError` 接收 Flutter framework 捕获的异常。监控 handler 应先安全地复制结构化信息，再调用已有 handler；没有已有 handler 时调用 `FlutterError.presentError`。上报代码自身不能抛异常，否则可能掩盖原异常。

`PlatformDispatcher.instance.onError` 处理 root isolate 未捕获错误，返回 `true` 表示调用方已经处理。APM 不能只因为“写入了队列”就把返回值强制改为 `true`，而要保留应用原有 handler 的返回语义。child isolate 不由这个回调覆盖，需要通过 isolate error listener 或应用已有的转发机制接入。

事件类型至少区分：

- framework-caught error：可能被 ErrorWidget、Zone 或业务恢复，不等于 crash；
- root-isolate unhandled error：保留 handler 的 handled 结果；
- child-isolate error：记录 isolate 与转发来源；
- Android/NDK engine 或 plugin crash：进入 Native crash 管道；
- engine detach、surface 丢失和 OOM：不冒充 Dart exception。

样本同时保留 Flutter framework 版本、engine revision、线程模型、renderer backend、GPU、route 与 `engine_id`。同一进程可以创建多个 engine，仅有 `session_id` 不足以区分它们。

## 6. Session Timeline：共享关联键，保留各运行时语义

统一时间线的目标是关联，不是把 FCP、Flutter build 和 Android first draw 加成一个数字。Native 容器最适合生成根 ID：

- `session_id`：一次业务页面访问或流程；
- `surface_id`：Activity Window、WebView 或 FlutterView 实例；
- `navigation_id`：每次 WebView main-frame navigation；
- `route_id`：H5 soft navigation 或 Flutter route；
- `engine_id`：FlutterEngine 实例；
- `parent_span_id` / `span_id`：容器、导航、网络和渲染事件的因果关系。

### 6.1 事件 schema

| 字段 | 说明 |
| --- | --- |
| `runtime` | `native`、`webview`、`flutter` |
| `event_name` | 如 `container_create`、`fcp`、`renderer_gone`、`flutter_frame` |
| `observed_elapsed_ns` | Native 观察或接收事件的单调时钟 |
| `source_time` / `source_clock` | Web `performance.now`、Flutter raw phase 等原始时间 |
| `uncertainty` | 往返校准误差、批次交付窗口或 `unknown` |
| `value` / `unit` | 指标数值和 `ns`、`us`、`ms`、`bytes`、`count` |
| `signal_strength` | `direct`、`state`、`suspected` |
| `runtime_version` | Android 17、WebView provider、Flutter engine 等版本轴 |
| `sampling` | 采样率、保留原因、drop count |
| `route_key` | 脱敏后的低基数页面标识 |

事件时间与观察时间分开存，查询端才不会把 MethodChannel 收包时刻当作 Flutter 单帧发生时刻，或把 `onPageFinished()` 当作像素已经显示。缺失字段使用 `unsupported`、`not_observed` 或 `inconclusive`，不使用 0。

### 6.2 会话边界要覆盖复用与进程重启

WebView 返回历史页时，旧 document 可能继续存在；bfcache、same-document route 与 main-frame navigation 的指标边界也不同。FlutterView 可以 detach 后再 attach，同一个 FlutterEngine 还可能服务新的页面。建议按以下规则维护 ID：

- 新业务访问生成新 `session_id`；
- WebView 每次 main-frame navigation 生成新 `navigation_id`，SPA route 只换 `route_id`；
- FlutterEngine 创建时生成 `engine_id`，route 变化不更换 engine；
- surface detach/attach 生成新的 surface generation；
- App 进程重启后不续用旧的单调时钟会话；服务端可用业务 trace 做弱关联；
- 页面进入后台时关闭像素判断窗口，恢复后重新校准 Web 时钟与可见状态。

一条查询结果可以按因果顺序展示：容器创建、WebView 导航、FCP/LCP、业务 ready、白屏证据、Bridge 高耗时、Flutter 慢帧、网络与异常。每个 runtime 仍使用自己的指标定义。

### 6.3 上线前验证采集器本身

混合栈 APM 至少做四组回归：

1. WebView：受控重定向、SPA、跨域 iframe、合法纯白页、canvas/video、renderer crash 与后台冻结；
2. Flutter：build 慢、raster 慢、pipeline latency、多个 engine、旧/新线程模型和异常恢复；
3. 时钟：冷启动、长时间后台、系统时间跳变、provider/engine 更新与高负载队列；
4. 开销：主线程时间、worker queue、Bitmap 峰值、MethodChannel bytes、CPU、drop count 和上传量。

白屏截图不上传，Bridge 参数默认不采集，URL 去掉 query、fragment 与用户标识，异常栈按现有隐私策略脱敏。采样器达到 CPU、内存或队列预算时，优先丢弃正常帧和重复状态，保留 renderer gone、确认白屏与异常摘要。

## 参考资料

### Android 17 / WebView

- [AOSP `WebView.java`（android-17.0.0_r1）](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/webkit/WebView.java)
- [AOSP `WebViewClient.java`（android-17.0.0_r1）](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/webkit/WebViewClient.java)
- [AOSP `WebViewRenderProcessClient.java`（android-17.0.0_r1）](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/webkit/WebViewRenderProcessClient.java)
- [AOSP `PixelCopy.java`（android-17.0.0_r1）](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/graphics/java/android/view/PixelCopy.java)
- [Android WebView API reference](https://developer.android.com/reference/android/webkit/WebView)
- [WebViewClient API reference](https://developer.android.com/reference/android/webkit/WebViewClient)
- [WebViewRenderProcessClient API reference](https://developer.android.com/reference/android/webkit/WebViewRenderProcessClient)
- [PixelCopy API reference](https://developer.android.com/reference/android/view/PixelCopy)
- [AndroidX WebKit `WebViewCompat`](https://developer.android.com/reference/androidx/webkit/WebViewCompat)
- [WebView Native Bridge 指南](https://developer.android.com/develop/ui/views/layout/webapps/native-api-access-jsbridge)
- [WebView Native Bridge 安全风险](https://developer.android.com/privacy-and-security/risks/insecure-webview-native-bridges)

### Web Performance

- [Paint Timing](https://www.w3.org/TR/paint-timing/)
- [Largest Contentful Paint](https://www.w3.org/TR/largest-contentful-paint/)
- [Navigation Timing Level 2](https://www.w3.org/TR/navigation-timing-2/)
- [High Resolution Time Level 3](https://www.w3.org/TR/hr-time-3/)
- [Lighthouse 10 移除 TTI](https://developer.chrome.com/docs/lighthouse/performance/interactive)

### Flutter

- [Flutter 3.32 release notes](https://docs.flutter.dev/release/release-notes/release-notes-3.32.0)
- [Flutter 3.38 release notes](https://docs.flutter.dev/release/release-notes/release-notes-3.38.0)
- [Flutter merged platform/UI thread tracking issue](https://github.com/flutter/flutter/issues/150525)
- [Flutter 3.38.0 `FlutterLoader.java`：拒绝 Android 旧 opt-out](https://github.com/flutter/flutter/blob/3.38.0/engine/src/flutter/shell/platform/android/io/flutter/embedding/engine/loader/FlutterLoader.java)
- [FrameTiming API](https://api.flutter.dev/flutter/dart-ui/FrameTiming-class.html)
- [`timestampInMicroseconds()` API](https://api.flutter.dev/flutter/dart-ui/FrameTiming/timestampInMicroseconds.html)
- [`SchedulerBinding.addTimingsCallback()` API](https://api.flutter.dev/flutter/scheduler/SchedulerBinding/addTimingsCallback.html)
- [`PlatformDispatcher.onReportTimings` API](https://api.flutter.dev/flutter/dart-ui/PlatformDispatcher/onReportTimings.html)
- [`PlatformDispatcher.onError` API](https://api.flutter.dev/flutter/dart-ui/PlatformDispatcher/onError.html)
- [`FlutterError.onError` API](https://api.flutter.dev/flutter/foundation/FlutterError/onError.html)
- [Flutter 3.44.8 `vsync_waiter_android.cc`](https://github.com/flutter/flutter/blob/3.44.8/engine/src/flutter/shell/platform/android/vsync_waiter_android.cc)
- [Flutter 3.44.8 `VsyncWaiter.java`](https://github.com/flutter/flutter/blob/3.44.8/engine/src/flutter/shell/platform/android/io/flutter/view/VsyncWaiter.java)
- [Flutter 渲染管线](../../part2-performance/ch18-rendering-pipelines/12-flutter-rendering.md)
- [WebView 渲染管线](../../part2-performance/ch18-rendering-pipelines/13-webview-rendering.md)
