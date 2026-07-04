---
status: finalized
applicable_versions: "Android 8 (API 26) - Android 17 (API 37)"
chapter: "19"
confidence: high
drafted_by: gemini
drafted_date: "2026-04-24"
last_task6_at: "2026-07-04T08:05:00+08:00"
last_task9_at: "2026-07-01T19:26:42+08:00"
last_verified: "2026-04-25"
deepseek_polish_state: done
last_deepseek_polish_at: "2026-05-25"
last_verified_against: "Android PixelCopy / WebViewRenderProcess APIs, Flutter FrameTiming docs, Flutter 3.32 thread merge (issue #150525 + release-notes-3.32.0)"
pipeline_stage: ready-to-publish
related_chapters:
  - "19.0"
  - "19.01"
review_notes: "2026-04-28 task9 deep-review: needs-rework。P1 2（WebView 可见状态 API 与跨时钟校准）。"
reviewed_by: openclaw-task6
reviewed_date: "2026-07-04"
section: "19.26"
sources:
  - https://developer.android.com/reference/android/view/PixelCopy
  - https://developer.android.com/reference/android/webkit/WebViewClient#onRenderProcessGone(android.webkit.WebView,%20android.webkit.RenderProcessGoneDetail)
  - https://developer.android.com/reference/android/webkit/WebViewRenderProcessClient
  - https://api.flutter.dev/flutter/dart-ui/FrameTiming-class.html
  - https://api.flutter.dev/flutter/scheduler/SchedulerBinding/addTimingsCallback.html
tags:
  - apm
  - webview
  - flutter
  - hybrid
task2b_result: fixed
task2b_state: fixed
last_task2b_lite_at: "2026-07-01"
task6_result: pass-light-edit
task6_review_notes: "2026-07-04 task6 复审：L1 轻修（禁用词\"对齐\"→\"匹配\"）；四层质检通过，task9 已 auto-fixed，queue 无 pending，自动晋升 finalized。"
task6_reviewed_at: "2026-05-16T08:16:00+08:00"
task6_reviewed_by: openclaw-task6
task6_state: reviewed
task9_result: "auto-fixed"
task9_review_notes: "2026-05-16 Task9 deep-review: pass-tech-review。P0 0 / P1 0 / P2 2；WebView 可见状态与 Flutter 时钟误差为 P2 建议，已写入 suggestions。自动晋升 finalized。2026-07-01 Task9 闲时抽检: needs-rework。P1 1（Flutter merged UI+Platform 线程模型版本边界缺失）；已写入 queue.json。 2026-07-01 Task2B 回炉修复: Flutter APM 小节线程模型按 3.29+ merged model (Main(UI+Platform)/Raster/IO) 改写，同步更新大纲、section 5 标题与正文；与 2.11、18.12 口径对齐。 2026-07-01 Task9 deep-review: needs-rework。P0 0 / P1 1 / P2 0；Flutter merged UI+Platform 默认合并版本边界应为 Flutter 3.32 stable+，正文与 2.11/18.12 仍写 3.29+；已写入 queue.json。 2026-07-01 Task9 deep-review: needs-rework。P0 0 / P1 1 / P2 0；AUTO-FIX 19.26 残留 3.29+→3.32 stable+；2.11/18.12 仍是 3.29+，交叉引用未闭环；已写入 queue.json。 2026-07-01 Task9 deep-review: auto-fixed。P0 0 / P1 1 / P2 0；修正 Flutter addTimingsCallback release 批量上报约 1s 的时间轴误差边界，回 Task6 复审。"
task9_reviewed_by: "openclaw-task9"
task9_reviewed_date: "2026-07-01"
task9_state: reviewed
title: "混合栈与跨平台 APM (WebView / Flutter)"
last_task9_review_log: "logs/deep-review/2026-07-01-19-deep-review.md"
last_task6_review_log: "logs/review/2026-07-04-08-review.md"
finalized_date: "2026-07-04"
finalized_by: "openclaw-task6-auto-promote"
task2b_fix_source: "task9-deep-tech-review"
task2b_fix_summary: "Flutter merged UI+Platform 线程模型版本边界从 3.29+→3.32 stable+，旧模型边界从 3.28-→3.31-，与 2.11/18.12 交叉引用闭环（依据 Flutter issue #150525 + release-notes-3.32.0）"
last_task2b_at: "2026-07-01T18:54:04+08:00"
last_task6_audit: "2026-07-04"
last_task9_audit: "2026-07-01"
last_task9_audit_log: "logs/deep-review/2026-07-01-16-audit.md"
last_task9_autofix_at: "2026-07-01"
---
# 混合栈与跨平台 APM (WebView / Flutter)

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 [定位] 解决纯 Native APM（如 JankStats）在遇到 WebView 或 Flutter 容器时缺少内部信号的问题，建立全栈监控视角。
- 🔹 [WebView 性能主要指标] 解释前端性能监控（FCP、LCP、TTI、loadEventEnd）如何与 Android Native 的容器初始化耗时（Container Init）拼接，算出真实的"端到端页面加载耗时"。
- 🔹 [H5 白屏检测] 解析线上识别 WebView 白屏的几种流派：基于 DOM 树节点抓取、基于 `onPageFinished` 拦截、以及基于 Native 层的 `PixelCopy` 异步像素采样。
- 🔹 [JSBridge 监控] 探讨 JS 与 Native 通信桥梁的性能瓶颈监控，如何记录高频注入、大 Payload 序列化及主线程阻塞情况。
- 🔹 [Flutter APM 融合] 说明 Flutter 3.32 stable+ merged model 下 Main(UI+Platform) / Raster / IO 线程的卡顿如何暴露给 Android 宿主；旧版与定制 Embedder 的独立 UI 线程边界何时适用；Dart 异常（Crash）如何由 Native APM 统一收集。线程归因以 2.11、18.12 的版本边界为准。
- 🔹 [Session Timeline 统一] 讲解跨端监控的工程难点：如何在 Native、H5、Flutter 之间传递统一的 Session ID / Trace ID，确保混合页面的交互轨迹不混乱、不中断。

### 扩展（可选深入）

- 🔸 提供一段利用 `PerformanceObserver` 接口将前端指标回传给 Android 端侧 APM 统一存储的桥接代码示例。
- 🔸 分析 Flutter 引擎中的 `FrameTiming` API 如何映射为 Android 的 Jank 概念。
- 🔸 对比分析"像素截帧判白屏"对低端机带来的额外性能损耗与规避策略。

### 流水线加工要求

- 避免写成纯前端（FE）的性能监控教程，所有的指标与视角必须围绕 Android Native 容器组织。
- 必须明确跨平台引擎（如 Flutter）自成体系的渲染管线与 Android 系统的 Choreographer 之间的时序关系。Flutter APM 小节必须按版本标记线程模型：3.32 stable+ merged model（Main(UI+Platform) / Raster / IO）、旧版/定制 Embedder（独立 UI 线程），与全书 2.11、18.12 口径一致。

### OpenClaw 加工指引

> **锚点**是最低覆盖要求，加工时必须逐条落实并标注验证结果。
> **扩展**视素材丰富程度选择性深入。
<!-- outline-end -->

混合栈 APM 的难点在边界。Native APM 能看到 Activity、Fragment、主线程、网络和崩溃，却看不到 WebView 内部的 FCP、LCP、JS 执行和 DOM 状态；Flutter 页面也有自成体系的 Dart Build/Layout/Paint、Raster 光栅化和 Dart 异常体系——其线程模型因 Flutter 版本而异（3.32 stable+ merged model 用 Main(UI+Platform)/Raster/IO，旧版/定制 Embedder 才有独立 UI 线程）。端侧要把容器生命周期、前端指标、Flutter 帧耗时和统一会话信息放进同一份样本。

Android 容器仍然是主视角。页面从 Native 创建容器开始，到 WebView 或 Flutter 首屏完成，中间经过初始化、资源加载、引擎调度和渲染输出。只看前端 `loadEventEnd` 会漏掉容器创建；只看 Native `Activity.onResume()` 到首帧会漏掉页面内部渲染。混合栈 APM 要记录两边的时钟、事件名和会话 ID，再在端侧或服务端合并。

## 1. WebView 页面加载：把容器耗时和前端指标合并

WebView 页面加载至少分成四段：Native 容器创建、WebView 初始化、URL 加载、前端可见内容生成。APM 的事件模型可以这样设计：

| 阶段 | Native 侧事件 | H5 侧事件 | 说明 |
| --- | --- | --- | --- |
| 容器初始化 | Activity/Fragment 创建、WebView 构造、`loadUrl()` | 无 | 记录容器启动到发起加载的耗时 |
| 导航开始 | `shouldOverrideUrlLoading`、`onPageStarted` | `navigationStart` | 需要记录 URL 脱敏后的页面名 |
| 首屏可见 | Native 首帧、WebView 可见 | FCP / LCP | FCP 更接近首个内容出现，LCP 更接近主要内容出现 |
| 页面可交互 | Native 交互事件、JSBridge ready | TTI / 自定义 ready | 移动端 H5 往往需要业务自定义 ready 事件 |
| 加载结束 | `onPageFinished` | `loadEventEnd` | 只能说明主文档加载结束，不能等同于无白屏 |

时钟映射要在桥接层处理。JS 的 `performance.now()` 基于页面 `timeOrigin`，Native 常用 `SystemClock.elapsedRealtime()`。注入脚本时记录校准对：`nativeElapsedRealtimeAtInjection`、`nativeWallClockAtInjection`（可选，用于服务端合并）、`jsPerformanceNowAtInjection`。H5 侧 `entry.startTime` 回传后，用 `nativeElapsedAtInjection + (entry.startTime - jsNowAtInjection)` 归一到端侧单调时钟。如果需要用 `timeOrigin` 做服务端时序合并，还要保留 wall-clock offset，并标注 clock-skew 边界（`elapsedRealtime` 是单调时钟，wall-clock 存在 NTP 调整风险）。这样才能把"容器初始化 180ms + FCP 620ms"合成一条端到端加载样本。

这段 JS 的用途是把前端 FCP/LCP 指标回传给 Android。重点看：只传脱敏页面名、相对时间和统一 session，不传完整 URL query。

```javascript
(function () {
  const sessionId = window.__APM_SESSION_ID__;

  function sendMetric(name, value) {
    if (!window.NativeApm || !sessionId) return;
    window.NativeApm.reportPerformance(JSON.stringify({
      sessionId: sessionId,
      metric: name,
      valueMs: Math.round(value),
      page: location.origin + location.pathname
    }));
  }

  // FCP: paint 类型在所有支持 PerformanceObserver 的 WebView 中可用
  try {
    if (typeof PerformanceObserver !== 'undefined') {
      new PerformanceObserver((entryList) => {
        for (const entry of entryList.getEntries()) {
          if (entry.name === 'first-contentful-paint') {
            sendMetric('fcp', entry.startTime);
          }
        }
      }).observe({ type: 'paint', buffered: true });
    }
  } catch (e) {
    // WebView 不支持 paint 类型或 PerformanceObserver，回退到 onPageFinished + 业务 ready
  }

  // LCP: 需要浏览器支持 'largest-contentful-paint' 入口类型
  // WebView 的前端性能 API 能力取决于 Android System WebView / Chromium 版本，不只取决于 Android API level
  // 旧版 WebView 可能不支持 LCP，必须先检查 supportedEntryTypes
  try {
    if (typeof PerformanceObserver !== 'undefined' &&
        PerformanceObserver.supportedEntryTypes &&
        PerformanceObserver.supportedEntryTypes.includes('largest-contentful-paint')) {
      new PerformanceObserver((entryList) => {
        const entries = entryList.getEntries();
        const latest = entries[entries.length - 1];
        if (latest) sendMetric('lcp', latest.startTime);
      }).observe({ type: 'largest-contentful-paint', buffered: true });
    }
  } catch (e) {
    // LCP 不可用时回退到 FCP + 业务 ready 指标
  }
})();
```

LCP 在部分旧 WebView 中不可用。没有 `supportedEntryTypes` 检查和 `try/catch` 时，注入脚本会异常退出，导致 FCP 和 LCP 都不上报。样本字段还应包含 `webviewProviderPackage` 和 Chromium major version，用于在服务端区分不同 WebView 版本的指标覆盖情况。对不支持 LCP 的 WebView，APM 回退到 FCP、业务 ready 事件和像素/DOM 采样。

## 2. H5 白屏检测：API 26+ 优先用 `PixelCopy`

白屏检测常见三类信号：DOM 信号、生命周期信号、像素信号。DOM 节点数量、首屏可见节点面积、业务 ready 事件适合低成本采样；`onPageFinished` 只能说明主文档加载结束，无法证明首屏已经有有效内容；像素采样能观察最终显示结果，但实现不当会把监控本身变成卡顿来源。

`onPageFinished` 之外还有两个官方可见状态锚点。API 23+ 的 `WebViewClient.onPageCommitVisible()` 在当前导航的新内容首次绘制到屏幕时回调，表示旧页面内容不再可见，适合作为"页面已切换"的判据。`WebView.postVisualStateCallback(long requestId, VisualStateCallback)` 提供更细粒度的 visual state 更新通知：requestId 是调用方自定义的标识（例如自增序号），用于匹配请求和回调；回调触发时表示当前 DOM 更新已在下一次 draw 中可见（不含 video tag 状态）。白屏采样建议先等 `onPageCommitVisible` 或 `postVisualStateCallback` 确认渲染管线就绪，再做低频 `PixelCopy` 或 DOM/业务 ready 交叉判断，避免采到旧内容或未提交到渲染管线的中间状态。

API 26+ 的 Android 应优先使用 `PixelCopy` 从 Window 或 Surface 异步复制像素。它比在 UI 线程调用 `WebView.draw(Canvas)` 更适合线上采样，原因是 WebView 使用硬件加速和 Chromium 渲染管线，同步 `draw()` 会增加主线程的绘制成本，还可能拿不到视频、GL 或硬件层的真实像素。`PixelCopy.request()` 通过回调返回结果，采样区域也能限制在首屏或关键区域。

这段 Kotlin 示例用于说明 API 26+ 的白屏像素采样。重点看 `srcRect` 限定采样范围，以及回调线程不做重计算。

```kotlin
@RequiresApi(26)
fun sampleWebViewPixels(
    activity: Activity,
    webView: WebView,
    workerHandler: Handler,
    onResult: (Boolean) -> Unit
) {
    val location = IntArray(2)
    webView.getLocationInWindow(location)

    val srcRect = Rect(
        location[0],
        location[1],
        location[0] + webView.width,
        location[1] + minOf(webView.height, 480)
    )
    val bitmap = Bitmap.createBitmap(srcRect.width(), srcRect.height(), Bitmap.Config.ARGB_8888)

    PixelCopy.request(activity.window, srcRect, bitmap, { result ->
        if (result != PixelCopy.SUCCESS) {
            onResult(false)
            return@request
        }
        onResult(WhiteScreenDetector.isMostlyBlank(bitmap))
    }, workerHandler)
}
```

`WhiteScreenDetector.isMostlyBlank()` 应只做低成本统计，例如抽样计算近白色像素比例、有效色块数量和透明区域比例。采样频率要低，常见触发点是 `onPageFinished` 后延迟一次、业务 ready 超时后一次、用户投诉白屏时一次。API 26 以下没有 Window 级 `PixelCopy`，线上默认使用 DOM/业务 ready 信号，必要时用低频 `draw()` 作为诊断兜底，不能按帧采样。

## 3. WebView 渲染进程：把崩溃和无响应纳入 APM

现代 WebView 的渲染工作常在独立进程中完成，页面白屏不一定伴随 App 进程崩溃。APM 要接入两类信号，但它们的版本边界不同：

**API 26+：`WebViewClient.onRenderProcessGone()`**

渲染进程退出时回调，`RenderProcessGoneDetail.didCrash()` 能区分崩溃和系统回收。回调后原 WebView 已不可继续使用，应从视图树移除并释放引用，返回 `true` 表示应用已处理。所有 Android 8+ 设备都能用这个接口。

**API 29+：`WebViewRenderProcessClient`**

可观察渲染进程 responsive / unresponsive 状态，适合记录长时间 JS 执行、页面死循环、Chromium 渲染卡住等问题。它属于 API 29 新增的 `WebViewRenderProcessClient` 体系（`WebView.setWebViewRenderProcessClient()`、`onRenderProcessUnresponsive()`、`onRenderProcessResponsive()`）。

**API 26-28 的降级信号**

API 26-28 没有 `WebViewRenderProcessClient`。检测渲染进程卡死需要依赖间接信号：

- 页面 ready 超时：`onPageStarted()` 后设定超时窗口（如 10 秒），超时未收到 `onPageFinished()` 或业务 ready 回调，标记为疑似卡死。
- JSBridge 心跳：注入轻量心跳脚本，定期通过 JSBridge 回调 Native，超时未收到视为渲染进程可能无响应。
- PixelCopy / DOM 采样：结合白屏检测手段，在超时后采样一次像素或 DOM 状态。

端侧样本应记录 WebView id、页面名、渲染进程状态、信号来源（`onRenderProcessGone` / `WebViewRenderProcessClient` / 降级检测）、API level、前后台、内存压力和最近的 JSBridge 调用。这样才能区分"页面资源加载失败""JS 死循环""渲染进程被系统回收"和"业务容器提前销毁"。

## 4. JSBridge 监控：看调用频率、载荷和线程等待

JSBridge 的性能问题通常不在单次调用，而在高频、小粒度、带大 JSON 的调用组合。APM 侧记录三类数据即可定位大部分问题：

- 调用频率：同一页面每秒调用次数、同一方法名调用次数、是否集中发生在滑动或动画期间。
- 载荷大小：JSON 字符串长度、数组条目数、是否携带图片/base64/大段 HTML。
- 线程等待：Native 方法是否切回主线程、主线程等待时长、回调是否阻塞 JS 执行。

Native 调 JS 时，`evaluateJavascript()` 是优先选择。它异步执行并通过回调返回字符串结果，适合替代旧式 `loadUrl("javascript:...")`。JS 调 Native 时，`addJavascriptInterface` 暴露的方法要保持短小，复杂工作转到后台线程；如果方法内部再同步等待主线程，就会形成 WebView 侧和 Android 主线程之间的互相等待。

## 5. Flutter APM：按版本标记线程模型，用 `FrameTiming` 量化帧耗时

Flutter 页面有独立的渲染调度。线程模型因版本而异：Flutter 3.32 stable+ 在 Android 上的主线是 Main(UI+Platform) / Raster / IO——Dart Build/Layout/Paint 与 Platform/插件回调共用宿主主线程；Flutter 3.31- 或定制 Embedder 才按独立 UI 线程（Dart isolate）观察。Raster 线程始终独立，负责把 layer tree 栅格化并提交到 Surface。版本边界以 2.11、18.12 的详细说明为准。Android 的 Choreographer 只能观察宿主视图的帧节奏，无法直接告诉你 Flutter 内部是 build 慢还是 raster 慢。

Flutter 官方的 `FrameTiming` 是线上采样的主要入口。`buildDuration` 对应 Dart Build/Layout/Paint 的 CPU 耗时（3.32 stable+ merged model 在宿主主线程上运行，Flutter 3.31-、opt-out 或定制 Embedder 在独立 UI 线程上运行），`rasterDuration` 对应 Raster 线程光栅化耗时。60Hz 下单项超过约 16.6ms 就可能丢帧；90Hz、120Hz 设备阈值更短。端侧 APM 应把 Flutter 帧预算按设备刷新率计算，避免固定写死 16ms。

这段 Dart 示例用于把 `FrameTiming` 批量回传给 Native。重点看 `buildDuration` 与 `rasterDuration` 分开上报。

```dart
import 'dart:convert';
import 'package:flutter/scheduler.dart';
import 'package:flutter/services.dart';

const MethodChannel _apmChannel = MethodChannel('apm/flutter_frame');

void installFlutterFrameReporter(String sessionId) {
  SchedulerBinding.instance.addTimingsCallback((List<FrameTiming> timings) {
    final payload = timings.map((timing) => {
      'sessionId': sessionId,
      'buildMs': timing.buildDuration.inMicroseconds / 1000.0,
      'rasterMs': timing.rasterDuration.inMicroseconds / 1000.0,
      'totalMs': timing.totalSpan.inMicroseconds / 1000.0,
    }).toList();

    _apmChannel.invokeMethod('frameTimings', jsonEncode(payload));
  });
}
```

### Flutter 时间戳到 Native 时钟的校准

`FrameTiming` 上报的 `buildDuration` / `rasterDuration` / `totalSpan` 是时长，可以直接用。但如果想把 Flutter 帧事件和 Native ANR、网络、WebView 事件放在同一条 Session Timeline（按 `elapsed_realtime_ms` 排列），就需要解决时钟归一问题。

`FrameTiming.timestampInMicroseconds(FramePhase)` 返回的是 Flutter 引擎内部的 raw timestamp（同一 epoch 下的微秒计数），官方文档未保证它与 Dart `DateTime` epoch 协调，更不等于 Native 的 `SystemClock.elapsedRealtime()`。直接把 `timestampInMicroseconds` 除以 1000 当作 `elapsed_realtime_ms` 写入 Timeline，时间轴会偏移。

工程上分三步做近似校准：

1. **用 MethodChannel 接收时间作为帧事件锚点**：`FrameTiming.timestampInMicroseconds` 的 epoch 与 Dart `DateTime` epoch 不保证一致（官方文档明确标注"the epoch may not match DateTime epoch"），不能通过 `DateTime.now()` 建立可靠校准对。替代方案：Native 端以 MethodChannel 收到帧事件回调的时间（`SystemClock.elapsedRealtime()`）作为这批帧的观测锚点；帧内部的 `buildMs` / `rasterMs` / `totalMs` 用作相对时长。如果需要把帧事件放在 Session Timeline 上，写入的是"Native 收到这批帧回调的时刻"，而不是从 raw timestamp 换算出的伪精确时间。

2. **帧内部用 raw timestamp 推算相对时序**：`buildMs` / `rasterMs` / `totalMs` 是 Flutter 引擎保证的相对时长，可以直接使用。如果需要帧内部的时序关系（如 build 开始到 raster 结束的间隔），可以用 `rawVsyncStartUs`、`rawBuildStartUs`、`rawRasterFinishUs`（来自 `FrameTiming.timestampInMicroseconds(FramePhase)`）做差值计算——这些 raw timestamp 在同一 Engine 进程内是自洽的，只是 epoch 不等于 Native monotonic clock。不要尝试把它们换算为 `elapsed_realtime_ms`。

3. **标注误差来源和范围**：误差来自两方面。一是 MethodChannel 传输延迟，二是 `addTimingsCallback` 的批量上报延迟。Flutter 官方文档说明，`FrameTiming` 在 release 模式大约每 1 秒批量回调一次，在 debug/profile 模式大约每 100ms 回调一次；所以 Session Timeline 中若把 Flutter 帧事件时间戳记为 Native 接收回调时刻，它只能作为批次观测时间，不是帧实际发生时间。样本应标注 `clock_source: "native_receive_time"` 和 `clock_error_ms`：release 取约 1000ms+，debug/profile 取约 100ms+，另加通道传输延迟。只做按秒聚合的丢帧率分析时，直接使用 `buildMs` / `rasterMs` 时长指标。

**进程挂起边界**：App 进入后台后系统可能冻结进程（CachedAppOptimizer / cgroup freezer），恢复后 `elapsedRealtime()` 持续计时但 `DateTime.now()` 可能跳变。如果会话锚点是在挂起前采集的，恢复后应重新发送一次锚点事件。实现方式：监听 `WidgetsBindingObserver.didChangeAppLifecycleState`，在 `resumed` 时重发锚点事件。

```dart
// 帧事件中附上 raw timestamp 用于帧内部相对时序，不做 epoch 换算
// Native 端以 MethodChannel 收到回调的时刻作为 Session Timeline 锚点
final payload = timings.map((timing) => {
  'sessionId': sessionId,
  'buildMs': timing.buildDuration.inMicroseconds / 1000.0,
  'rasterMs': timing.rasterDuration.inMicroseconds / 1000.0,
  'totalMs': timing.totalSpan.inMicroseconds / 1000.0,
  // raw timestamp 仅用于帧内部的差值计算，epoch 不等于 Native monotonic clock
  'rawVsyncStartUs': timing.timestampInMicroseconds(FramePhase.vsyncStart),
  'rawBuildStartUs': timing.timestampInMicroseconds(FramePhase.buildStart),
  'rawRasterFinishUs': timing.timestampInMicroseconds(FramePhase.rasterFinish),
  'frameNumber': timing.frameNumber,
  'clockSource': 'native_receive_time',
}).toList();
```

Native 端收到帧事件后，以回调接收时刻作为 Session Timeline 锚点，`buildMs` / `rasterMs` 用作帧耗时指标。如果只做粗粒度分析（按秒聚合丢帧率），直接用时长指标即可。需要时序关联的场景（Flutter 帧卡顿与 Native ANR / 网络 / WebView 事件）主要依赖 Native 接收时间做批次级粗粒度匹配；release 模式可能有约 1 秒批量延迟，不能把它当成单帧精确发生时刻，也不能依赖 raw timestamp 的 epoch 换算。

Native 收到数据后，按页面、路由、设备刷新率、前后台和引擎后端聚合。Flutter 3.x 之后，Impeller 在部分平台替代或补充 Skia 路径，着色器编译和栅格化表现会变化。APM 样本里保留 Flutter 版本、渲染后端和设备 GPU 信息，才能解释同一页面在不同设备上的差异。

Dart 异常也要进入 Native APM。常见接法是设置 `FlutterError.onError` 和 `PlatformDispatcher.instance.onError`，把异常类型、栈、路由、session id 发到 Native，再按同一套崩溃/异常管道上报。这样混合页面的 Native 崩溃、Dart 异常、WebView 渲染进程退出不会散在三套系统里。

## 6. Session Timeline：统一会话，不合并语义

混合栈样本要共享同一个 Session ID / Trace ID，但不要把不同层的指标混成一个数字。推荐事件模型如下：

| 字段 | 说明 |
| --- | --- |
| `session_id` | 一次页面访问或业务流程的统一 ID |
| `surface_id` | Native Activity、WebView、FlutterView 的实例标识 |
| `runtime` | `native`、`webview`、`flutter` |
| `event_name` | `container_init_start`、`fcp`、`pixel_blank`、`flutter_frame` 等 |
| `elapsed_realtime_ms` | Native 单调时钟，便于和 trace / ANR / 网络样本放在同一时间轴 |
| `relative_time_ms` | H5 或 Flutter 内部相对时间 |
| `route_or_page` | 脱敏页面名、Flutter route、H5 path |
| `extra` | 指标值、错误码、渲染状态、降采样标记 |

查询时按 session 展开事件序列：Native 容器初始化、WebView URL 加载、FCP、LCP、白屏采样、JSBridge 高耗时、Flutter 帧抖动、网络请求和异常事件都落在同一时间轴上。这样既能定位混合页面"首屏慢在哪里"，也能保留各运行时自己的性能语义。

## 参考资料

- Android `PixelCopy` API reference：Window / Surface 像素异步复制。
- Android `WebViewClient.onRenderProcessGone()` 与 `WebViewRenderProcessClient`：WebView 渲染进程稳定性监控。
- Flutter `FrameTiming` 与 `SchedulerBinding.addTimingsCallback`：Flutter 帧耗时采样入口。
