---
title: "WebView Renderer OOM 与白屏恢复"
chapter: "20.9"
section: "20.9"
status: finalized
applicable_versions: "Android 8 (API 26) - Android 17 (API 37)"
last_verified: "2026-08-14"
last_verified_against: "AOSP android-17.0.0_r1 WebView APIs and HWUI sources; current Android Developers, AndroidX WebKit, and Chromium WebView architecture documentation"
confidence: medium-high
sources:
  - type: clippings-structure-ref
    path: "Clippings/Android 应用稳定性剖析与优化 - OOM 发生路径：了解 OOM 是如何产生的.md"
    availability: "not present in the current vault as of 2026-08-14; retained as legacy provenance"
  - type: research-note
    path: "OpenClaw定时任务/AutoResearchClaw调研报告/2026-05-05-webview-render-process-oom-recovery-onrendeprocessgone.md"
    availability: "not present in the current vault as of 2026-08-14; retained as legacy provenance"
  - type: aosp
    path: "https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/webkit/WebViewClient.java"
  - type: aosp
    path: "https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/webkit/RenderProcessGoneDetail.java"
  - type: aosp
    path: "https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/webkit/WebView.java"
  - type: aosp
    path: "https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/webkit/WebViewRenderProcessClient.java"
  - type: aosp
    path: "https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/webkit/WebViewRenderProcess.java"
  - type: aosp
    path: "https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/libs/hwui/private/hwui/WebViewFunctor.h"
  - type: aosp
    path: "https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/libs/hwui/WebViewFunctorManager.cpp"
  - type: chromium-source
    path: "https://chromium.googlesource.com/chromium/src/+/refs/heads/main/android_webview/docs/architecture.md"
  - type: aosp-kernel
    path: "https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/mm/vmscan.c"
  - type: official
    path: "https://developer.android.com/develop/ui/views/layout/webapps/handle-termination"
  - type: official
    path: "https://developer.android.com/develop/ui/views/layout/webapps/managing-webview"
  - type: official
    path: "https://developer.android.com/reference/android/webkit/WebViewClient"
  - type: official
    path: "https://developer.android.com/reference/android/webkit/WebView"
  - type: official
    path: "https://developer.android.com/reference/android/app/ActivityManager#getHistoricalProcessExitReasons(java.lang.String,%20int,%20int)"
  - type: official
    path: "https://developer.android.com/reference/android/app/ApplicationExitInfo"
  - type: official
    path: "https://developer.android.com/reference/androidx/webkit/WebViewCompat"
tags: [webview, oom, stability, renderer-process, recovery]
related_chapters: ["18.13", "22.7", "26.2"]
task6_state: reviewed
task9_state: reviewed
task2b_state: fixed
pipeline_stage: ready-to-publish
---

# WebView Renderer OOM 与白屏恢复

WebView 页面突然变白时，宿主 Activity 可能仍能响应，导航栏和原生按钮也都正常。若同时收到 `onRenderProcessGone()`，可以确认关联的 Renderer（负责网页解析、脚本执行与绘制的渲染进程）已经退出。此时旧 `WebView` 失效，`reload()`、`goBack()`、`evaluateJavascript()` 和 JS Bridge（JavaScript 与原生代码之间的通信接口）调用都救不回它。

标题中的 OOM 是 Out of Memory（内存不足）的缩写。本文讨论的是系统在内存压力下结束 Renderer 这一类情况；每次白屏或每个 `didCrash=false` 都不能直接定为 OOM。

下文把一次 `onRenderProcessGone()` 回调简称为 gone 事件。本文以 Android 17 / API 37 / `android-17.0.0_r1` 的 framework（Android 系统框架）契约为准。WebView provider（向 framework 提供 WebView 实现的可更新系统包）可能来自 Chromium，也可能由厂商定制，因此排查时还要记录设备上的 provider 包名与版本。文中涉及内核内存压力的源码名词时，以 Android common kernel（Android 公共内核源码仓库）的 `android17-6.18-2026-06_r6` 标签为参照；这个标签用于固定源码版本，不代表所有 Android 17 设备都运行同一内核。

## 先分清平台、Provider 和进程

标准 `android.webkit.WebView` 同时跨越两条版本线：

- Android 平台提供 `WebView`、`WebViewClient`、Renderer 优先级和终止处理 API；
- WebView provider 包提供 Chromium/Blink、页面合成、沙箱 Renderer 和大部分实现，并可独立于系统版本更新。

`android-17.0.0_r1` 只能固定公开 API 与 framework 注释，不能唯一确定设备使用的 Chromium 源码版本（revision）。复盘至少要记录 Android build（系统构建号）、provider 包名、`versionName`、`versionCode`、ABI（应用二进制接口，也就是 32/64 位和指令集）、设备型号，以及应用使用的是系统 WebView、定制 Chromium 还是第三方内核。

现代标准 WebView 可以按三个执行域理解：

1. 宿主进程保存 `WebView` Java 对象、Activity/Fragment 状态、业务 Bridge，以及 provider 的 browser-side 代码；这里的 browser-side 指导航、网络、权限等浏览器控制逻辑，并不表示另有一个浏览器应用；
2. 沙箱 Renderer 运行 Blink 排版引擎、JavaScript，以及样式计算、布局、绘制和部分页面合成工作；
3. 宿主的 HWUI RenderThread（Android UI 硬件加速渲染线程）通过 WebView functor 接收 provider 的绘制回调。functor 是 provider 与 HWUI 之间的原生绘制桥，结果通常先合入应用窗口，再交给 SurfaceFlinger（Android 的系统画面合成服务）和 HWC（Hardware Composer，硬件合成器）。

视频、受保护内容或 provider overlay（由 provider 单独提交的叠加画面）可能增加独立的 `SurfaceControl` 图层。Renderer 退出后，已提交的旧帧可能短暂保留，也可能变成空白或静止画面。宿主窗口仍在，只能说明应用进程尚未退出，不能说明网页仍可交互。

## `onRenderProcessGone()` 能证明什么

Android 8 / API 26 起，`WebViewClient.onRenderProcessGone(view, detail)` 是 Renderer 退出后的公开入口。Android 17 的 `WebViewClient.java` 给出四条硬约束：

- 多个 WebView 可能关联同一个 Renderer；
- 每个受影响的 WebView 都会收到回调；
- 当前回调只清理参数中的 `view`，不能假设其他实例也已退出；
- 传入的 WebView 不能继续使用，必须从 View 层级移除并清理引用。

返回值决定宿主是否继续运行：

| 返回值 | Android 17 契约 | 工程含义 |
| --- | --- | --- |
| `true` | 应用声明已处理退出 | 当前旧实例已被移除、销毁，业务开始恢复或展示原生错误页 |
| `false` | Renderer 崩溃时宿主随之崩溃；Renderer 被系统结束时宿主也被结束 | 应用没有能力安全处理，保留默认终止语义 |

默认实现返回 `false`。只有在清理动作已完成、后续代码不会再触碰旧实例时，才应返回 `true`。用 `true` 隐藏回调后仍在访问旧对象的错误，会把一次清晰的 Renderer 退出变成随机异常或长期白屏。

### `didCrash()` 只做二分类，不能给出完整原因

`RenderProcessGoneDetail.didCrash()` 返回：

- `true`：Renderer 被观察到发生崩溃；
- `false`：Renderer 被系统结束，AOSP 注释说明最常见背景是低内存。

`false` 仍不足以单独证明“页面 OOM”。应用在 API 29 及以上可能主动调用 `WebViewRenderProcess.terminate()`；设备实现和系统资源管理也会影响进程寿命。provider 更新通常会结束已经加载 WebView 的整个应用进程，这类进程重启要单独记录，不能假定一定会留下 renderer-only gone 事件。若应用会主动终止 Renderer，应在调用前生成一条短时有效的“预期终止标记”（下文简称 termination token），至少包含会话、调用时间、有效期和关联的 WebView 实例。随后到达且命中这条标记的 gone 事件，才归为预期终止。未命中时，再结合设备内存档位、前后台状态、Renderer 优先级、系统内存压力和问题页面是否反复出现来判断。

`rendererPriorityAtExit()` 返回退出时的最终 Renderer 优先级。一个 Renderer 可被多个 WebView 共享；`WebView.java` 规定，最终优先级取所有关联实例请求值中的最高值，实例销毁后不再参与计算。`RenderProcessGoneDetail.java` 也提醒，退出值可能高于某个单独实例请求的值。这个字段适合描述现场，不能反推出是哪一个 WebView 提高了优先级，也不能单独解释它为何被回收。

`RenderProcessGoneDetail` 不提供 Renderer PID（进程号）、页面内存、JavaScript 堆、Native 代码调用栈或最近网络请求。公开 API 没有精确的 Renderer 内存读数，不能用宿主进程的 PSS 冒充；PSS 的含义会在“怎样判断内存诱因”一节说明。

## 恢复是一段状态迁移

可靠的容器应把 Renderer gone 处理成一组有先后顺序的状态。下面的大写名称可以直接作为容器内部的状态枚举：

```text
ACTIVE
  -> GONE_CALLBACK
  -> DETACHED_AND_DESTROYED
  -> RECOVERY_UI
  -> NEW_WEBVIEW_LOADING
  -> VISUAL_COMMITTED
  -> BUSINESS_READY
```

任一步失败都进入原生错误页。`VISUAL_COMMITTED` 对应 `onPageCommitVisible()`：旧导航的内容不会再被绘制，响应正文已经进入 DOM，后续绘制可以出现新页面内容，但 CSS、图片等资源此时可能尚未完成。支付、编辑、登录等页面还需要 H5（运行在 WebView 中的 Web 前端页面）主动发出可校验的 `BUSINESS_READY`，表示业务接口和关键交互已经可用；宿主还要为这次握手设置超时。

恢复前要回答三个问题：

1. 当前页面能否安全重放？
2. 是否已有一次自动恢复尝试？
3. Activity 是否仍处于可展示状态？

资讯详情、帮助页等幂等页面（重复加载不会额外改变业务结果）可以自动恢复。支付提交、表单编辑、身份验证和一次性 URL 应跳转到服务端状态查询或原生错误页，不能原样重放。原始 URL 可能含登录凭证、订单号和查询参数，上报与恢复检查点都要按业务规则去掉敏感信息。

## 一个可控的 Activity 恢复骨架

下面的示例展示单 WebView Activity 的最小恢复状态。`WebCheckpoint` 是业务自定义的恢复检查点，只保存去敏后的安全重载地址、页面类型和是否允许自动重载。业务方法留作接口，重点是旧实例清理、延后重建、自动恢复次数上限和页面可用信号：

```kotlin
class H5Activity : AppCompatActivity() {
    private lateinit var container: ViewGroup
    private var webView: WebView? = null
    private var checkpoint: WebCheckpoint? = null
    private var autoRecoveryUsed = false

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.h5_activity)
        container = findViewById(R.id.webview_container)

        checkpoint = restoreCheckpoint(savedInstanceState)
        autoRecoveryUsed =
            savedInstanceState?.getBoolean("auto_recovery_used") == true
        installWebView(checkpoint)
    }

    private fun installWebView(target: WebCheckpoint?) {
        check(webView == null)

        val next = WebView(this)
        configureWebView(next)
        next.webViewClient = object : WebViewClient() {
            override fun onPageStarted(
                view: WebView,
                url: String,
                favicon: Bitmap?,
            ) {
                checkpointFor(url)?.let { checkpoint = it }
            }

            override fun onPageCommitVisible(view: WebView, url: String) {
                if (view === webView) {
                    reportVisualCommit(checkpoint)
                }
            }

            override fun onRenderProcessGone(
                view: WebView,
                detail: RenderProcessGoneDetail,
            ): Boolean {
                val targetAtExit = checkpoint
                val didCrash = detail.didCrash()
                val priorityAtExit = detail.rendererPriorityAtExit()

                detachAndDestroy(view)
                reportRendererGoneSafely(
                    didCrash = didCrash,
                    priorityAtExit = priorityAtExit,
                    target = targetAtExit,
                )
                showRecoveringUi()

                container.post {
                    if (!isFinishing && !isDestroyed) {
                        recoverAfterRendererExit(targetAtExit, didCrash)
                    }
                }
                return true
            }
        }

        webView = next
        container.addView(
            next,
            ViewGroup.LayoutParams.MATCH_PARENT,
            ViewGroup.LayoutParams.MATCH_PARENT,
        )

        if (target == null) {
            next.loadUrl(homeUrl())
        } else {
            next.loadUrl(target.safeReloadUrl)
        }
    }

    private fun detachAndDestroy(target: WebView) {
        (target.parent as? ViewGroup)?.removeView(target)
        if (webView === target) {
            webView = null
        }
        target.destroy()
    }

    private fun recoverAfterRendererExit(
        target: WebCheckpoint?,
        didCrash: Boolean,
    ) {
        val mayAutoReload =
            !didCrash &&
                !autoRecoveryUsed &&
                target?.autoReloadAllowed == true

        if (mayAutoReload) {
            autoRecoveryUsed = true
            installWebView(target)
        } else {
            showFallbackPage(target)
        }
    }

    override fun onSaveInstanceState(outState: Bundle) {
        saveCheckpoint(outState, checkpoint)
        outState.putBoolean("auto_recovery_used", autoRecoveryUsed)
        super.onSaveInstanceState(outState)
    }

    override fun onDestroy() {
        webView?.let(::detachAndDestroy)
        super.onDestroy()
    }
}
```

旧实例按官方要求从视图树移除、清除引用并调用 `destroy()`，之后不再设置 client、停止加载或执行 JavaScript。代码先把 `RenderProcessGoneDetail` 中需要的字段复制成普通值，避免延后任务继续持有回调对象；事件上报函数也必须自行处理异常，不能让异常从回调中抛出。重建通过 `container.post` 放入主线程消息队列，等回调返回后再执行，避免尚未退出回调又开始创建 WebView。任务执行前还会检查 Activity 是否正在结束或已经销毁。自动恢复次数写入 `savedInstanceState`（Activity 重建时由系统传回的状态 Bundle），避免屏幕旋转等配置变更把次数重新置零。

示例对崩溃采取保守策略：同一页面可能稳定复现 Chromium 或页面内容触发的问题，因此不自动重载。被系统结束的页面也只有一次自动恢复机会。`WebCheckpoint` 应保存去敏后的业务路由和重放规则，不应序列化完整浏览历史、POST 数据或 JavaScript 运行时状态。

`configureWebView()` 要统一安全与功能配置，包括允许访问的 origin（协议、主机名和端口三者组成的来源）、Safe Browsing、Cookie 策略、文件访问、混合内容、`WebChromeClient` 和 JS Bridge。只有可信页面需要的 Bridge 才能重新注册。若每个业务页面都直接创建 WebView，恢复出的实例很容易漏掉安全配置。

### 多 WebView 容器

共享 Renderer 时，同一次退出会触发多个回调。每个回调都只销毁参数中的 `view` 并返回 `true`；容器管理器再按页面栈决定统一展示错误页，或等待所有实例完成清理。不能在第一个回调中假设其余 WebView 已失效，也不能漏掉后台、缓存池或 `ViewHolder` 中的实例。

引用清理至少覆盖：

- Activity、Fragment 与自定义 View 字段；
- Adapter、ViewHolder 和页面栈；
- WebView 缓存池；
- JS Bridge、ValueCallback、下载与文件选择回调；
- 延迟 Runnable、协程和业务观察者。

回调完成后仍持有旧 WebView 的任务要被取消。另一种做法是给每次新建的实例分配递增代号，任务执行前比对代号，不匹配就放弃，避免旧任务操作新实例。

## Renderer 优先级与低内存策略

`WebView.setRendererPriorityPolicy(priority, waivedWhenNotVisible)` 只影响多进程模式下 Renderer 在系统内存不足时被选为回收对象的可能性，不会限制它最多能用多少内存。Android 17 定义三个级别：

| 级别 | 含义 |
| --- | --- |
| `RENDERER_PRIORITY_IMPORTANT` | 默认值，Renderer 绑定优先级与宿主主进程相近 |
| `RENDERER_PRIORITY_BOUND` | 中等，内存紧张时更容易成为回收目标 |
| `RENDERER_PRIORITY_WAIVED` | 最低，系统低内存时会更积极回收 |

下面的设置请求可见时使用 `BOUND`，不可见时按 `WAIVED` 处理：

```kotlin
webView.setRendererPriorityPolicy(
    WebView.RENDERER_PRIORITY_BOUND,
    true,
)
```

降低优先级只会让系统在内存紧张时更容易选中 Renderer，不会立即释放页面内存。只有当容器能处理全部关联 WebView 的 `onRenderProcessGone()`、能够识别不可重放页面，并且允许后台页面重建时，才适合调整这项策略。可见交易页通常不应只为节省内存就降低优先级。

多个 WebView 共享 Renderer 时，最终优先级取关联实例请求值的最大值；销毁某个 WebView 后，它不再参与计算。只修改一个后台实例，未必改变共享 Renderer 的最终优先级。

## 怎样判断内存诱因

WebView 页面资源分布在多个域：

- Renderer：DOM（页面的文档对象树）、JavaScript 堆、Blink 对象、已解码图片和部分光栅化资源；
- 宿主/provider：导航与网络等 browser-side 状态、Bridge、缓存与 WebView 对象；
- GPU/图形：纹理、分块渲染数据、图形缓冲区与驱动分配；
- 系统：其他进程的竞争、zram 压缩交换空间、内存回收活动和设备内存档位。

宿主的 Java 堆处于正常范围，不能排除 Renderer 或图形内存压力；Renderer 被系统结束，也不能反向证明某个 JavaScript 对象泄漏。

一次有效的 gone 事件至少记录：

| 维度 | 字段 |
| --- | --- |
| 页面 | 去敏后的业务路由、H5 构建版本、页面类型、停留时长、是否允许重复加载 |
| 容器 | WebView 数量、是否来自缓存池、可见性、自动恢复次数 |
| 退出 | `didCrash`、`rendererPriorityAtExit`、预期 termination token 是否命中 |
| Provider | 包名、`versionName`、`versionCode`、系统 WebView / 定制 Chromium / 第三方内核 |
| 宿主 | 进程前后台、PSS/RSS、最近 `onTrimMemory()`、进程存活时长 |
| 设备 | Android build、API、ABI、内存档位、设备型号 |
| 恢复 | 销毁完成、新实例创建、视觉提交、H5 就绪、进入原生错误页的原因 |

PSS（Proportional Set Size）把共享内存按比例计入进程，适合估算进程对物理内存的贡献；RSS（Resident Set Size）会把当前驻留的共享页全部计入，跨进程相加可能重复。这里记录二者是为了补充宿主现场，不能把它们当成 Renderer 的内存值。

在 Android 8 及以上，`WebView.getCurrentWebViewPackage()` 可在 WebView 加载前后调用。已经加载时，它返回当前进程实际使用的 provider；尚未加载时，它返回“此刻加载将会使用”的 provider，这个结果随后可能过期。设备不支持 WebView 或配置异常时，返回值也可能为 `null`。AndroidX WebKit 环境可使用对应的兼容 API。provider `versionName` 常能帮助定位 Chromium 版本，但厂商格式不统一；从版本号解析 milestone（Chromium 的主版本代号，如 M140）只能作为针对特定 provider 的逻辑。

实验室可用 Perfetto（系统跟踪工具）、bugreport（系统诊断包）、Chrome DevTools（网页调试工具）和 provider 对应的 Chromium 符号文件调查 Renderer、GPU 与系统内存压力；符号文件用于把原生地址还原成函数名和调用栈。查看内核证据时，reclaim 表示内存回收活动，PSI（Pressure Stall Information）memory 表示任务因内存压力停顿的时间比例，page fault 表示缺页事件，dma-buf 则常用于追踪跨进程共享的图形缓冲区；zram 的含义见上文。若要与本文源码对应，应固定到 `android17-6.18-2026-06_r6`。线上公开 API 通常拿不到 Renderer 的精确 PSS，不要依赖反射、读取其他进程 `/proc` 或私有 Chromium 接口。

`ApplicationExitInfo` 记录的是应用进程的退出信息，适合补充宿主进程为何结束。Renderer 被回收而宿主继续运行时，不一定会产生应用可查询的对应记录；它不能替代 `onRenderProcessGone()` 事件，也不能在没有时间和进程证据时与某次 Renderer gone 一一配对。

## WebViewRenderProcessClient：发现卡死，谨慎终止

Android 10 / API 29 起，`WebViewRenderProcessClient` 提供：

- `onRenderProcessUnresponsive()`：Renderer 因长阻塞任务等原因无法及时处理输入或导航；
- `onRenderProcessResponsive()`：同一 Renderer 恢复响应后回调一次。

Android 17 源码说明，无响应期间会重复回调，相邻回调最短间隔为 5 秒；WebView 不会自动采取动作。一次 unresponsive 回调只说明 Renderer 没有及时处理输入或导航，不等于应用发生 ANR（Application Not Responding，应用无响应），也不等于 Renderer 必须被结束。应记录持续时间、页面阶段、用户是否可退出，以及 H5 是否正在执行预期的耗时任务。

当产品允许用户放弃当前页面，且所有共享 WebView 都已实现终止处理时，才考虑调用 `renderer?.terminate()`。调用前要：

1. 写入前文定义的短时 termination token；
2. 切断新的 JS 注入和导航；
3. 展示不会依赖旧 WebView 的原生 UI；
4. 限制一次会话中的终止次数；
5. 等待随后的 `onRenderProcessGone()` 完成清理。

`WebViewRenderProcess` 是不透明句柄：调用方可以请求终止，却不能从对象中取得稳定的 PID 等实现细节。回调参数在单进程模式下还可能为 `null`。`terminate()` 返回 `true` 只表示当前可以终止这个 Renderer，返回 `false` 表示无法终止；返回值不表示 gone 回调已经到达，更不表示新页面已经恢复。

## 指标要覆盖发生、清理和可用

应用崩溃率看不到那些已返回 `true` 的 Renderer gone。建议按以下状态记录一次恢复过程：

| 状态 | 判定 |
| --- | --- |
| `gone_received` | 回调到达，按崩溃、系统结束、预期终止分类 |
| `old_view_destroyed` | 参数 View 已移除、引用已释放并调用 `destroy()` |
| `new_view_created` | 尚未达到自动恢复次数上限，且新实例已加入容器 |
| `visual_committed` | 新实例收到 `onPageCommitVisible()` |
| `business_ready` | H5 业务握手完成，关键接口可用 |
| `fallback_shown` | 进入原生错误页，并记录原因 |
| `repeat_gone` | 同一会话或短窗口内再次退出 |

核心指标必须有分母：

- Renderer gone 用户率、会话率和页面访问率；
- 崩溃、系统结束、预期终止的占比；
- 从 gone 到视觉提交、业务就绪的成功率和耗时分布；
- 自动恢复后的 repeat gone 率；
- 不可重放页面进入原生错误页的比例与业务完成率；
- 按 provider 版本、业务路由、设备内存档位和前后台状态分组后的差异。

“新 WebView 已创建”不算恢复成功，`onPageFinished()` 也不能保证用户已经看到可操作内容。视觉提交加业务握手更接近用户体验；两者都需要超时，并比对前文所说的实例代号，防止旧回调把新实例误报为成功。这个组合仍是应用侧的间接信号，不能证明某一帧已经由 SurfaceFlinger 提交到屏幕。需要逐帧诊断时，再检查宿主窗口的 FrameTimeline（帧从应用到显示系统的时间线）和实际显示时间。

## 分批启用、紧急停用和自动恢复次数

远程配置应位于容器层，常用控制项包括：

- 是否允许 killed 场景自动恢复；
- 哪些业务路由只展示原生错误页；
- 每个会话的自动恢复次数；
- 是否启用 WebView 缓存池；
- 后台 WebView 是否请求较低 Renderer 优先级；
- 哪些 provider 版本暂停自动重载。

远程开关不能依赖已经退出的 WebView 拉取。配置要在进入 H5 容器前缓存，并为离线状态准备保守默认值。

自动重载或后台降优先级应先对少量设备和用户启用，观察 gone 率、重复退出率和业务完成率后再扩大范围。异常上升时，远程配置应能立即停用对应策略。

若某个 provider 版本集中发生 Renderer 崩溃，应立即停用同一页面的自动重载，并保留 provider、H5 构建版本和去敏后的业务路由。provider 是独立更新组件，同一 Android 版本可能出现不同结果；统计时必须单独按 provider 版本分组。

## 故障演练

测试要覆盖不同退出方式，以及回调与 Activity 生命周期同时变化时可能出现的先后顺序问题：

| 用例 | 需要确认 |
| --- | --- |
| `chrome://crash` | 崩溃被识别，所有共享实例清理，宿主不退出 |
| `WebViewRenderProcess.terminate()` | 预期 token 命中，gone 回调完成，终止次数受限 |
| 内存压力下 Renderer 被回收 | 系统结束分支、后台延迟恢复、前台重建策略 |
| 两个 WebView 共享 Renderer | 每个受影响实例都返回 `true`，没有漏清理 |
| 回调后 Activity 立即销毁 | `container.post` 排队的恢复任务不会创建泄漏实例 |
| 敏感页面退出 | 不重放 POST、一次性 URL 或未确认交易 |
| 新页面再次 gone | 自动恢复次数上限生效并进入原生错误页 |
| provider 更新或切换 | 进程重启后记录的新版本正确 |

`chrome://crash` 只能放在调试或测试工具中，并且可能影响共享 Renderer 的多个 WebView。它验证崩溃处理，不能代替低内存回收。内存压力测试应在可控设备上结合 Perfetto 或 bugreport 确认系统背景，不能用一次手工白屏证明 OOM。

API 26 以下没有 `onRenderProcessGone()`。若产品仍支持更低版本，需要单独定义进程级隔离、原生错误页和 provider 升级策略；不要把 API 26 的恢复契约套到旧系统。

## 常见误判

| 误判 | 更严谨的结论 |
| --- | --- |
| 白屏就是 Renderer OOM | 只有 gone 回调能确认 Renderer 已退出；网络、HTTP、SSL、页面脚本和绘制停滞也会白屏 |
| `didCrash=false` 就是页面 OOM | 它表示 Renderer 并非因崩溃退出；还要排除应用主动终止，并补系统内存压力证据 |
| 返回 `true` 就完成恢复 | 旧实例清理、新实例重建、视觉提交和业务就绪都要验证 |
| 在旧实例上 `reload()` 能救回页面 | gone 后旧 WebView 不可复用，只能移除、销毁和新建 |
| 恢复时原样加载完整 URL | URL 可能敏感或不可重放，应使用去敏后的业务恢复检查点 |
| 一个 WebView 收到回调就能批量销毁 | 当前回调只处理参数实例，共享 Renderer 会逐个通知 |
| 宿主 PSS 就是 Renderer 内存 | 两者属于不同进程/执行域，公开 API 没有精确 Renderer PSS |
| Android 17 决定 Chromium 行为 | 还要记录设备 provider 包版本与对应的 Chromium 源码版本 |
| Renderer 准备好一帧就代表恢复可用 | 还需确认宿主能够绘制、收到视觉提交回调并完成业务握手 |

## 源码与官方资料

- [Android 17 `WebViewClient.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/webkit/WebViewClient.java)
- [Android 17 `RenderProcessGoneDetail.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/webkit/RenderProcessGoneDetail.java)
- [Android 17 `WebView.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/webkit/WebView.java)
- [Android 17 `WebViewRenderProcessClient.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/webkit/WebViewRenderProcessClient.java)
- [Android 17 `WebViewRenderProcess.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/webkit/WebViewRenderProcess.java)
- [Android 17 HWUI `WebViewFunctor.h`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/libs/hwui/private/hwui/WebViewFunctor.h)
- [Android 17 `WebViewFunctorManager.cpp`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/libs/hwui/WebViewFunctorManager.cpp)
- [Android Developers：处理 WebView Renderer 终止](https://developer.android.com/develop/ui/views/layout/webapps/handle-termination)
- [Android Developers：管理 WebView 对象](https://developer.android.com/develop/ui/views/layout/webapps/managing-webview)
- [Android Developers：`WebViewClient` API](https://developer.android.com/reference/android/webkit/WebViewClient)
- [Android Developers：`WebView` API](https://developer.android.com/reference/android/webkit/WebView)
- [Chromium WebView architecture](https://chromium.googlesource.com/chromium/src/+/refs/heads/main/android_webview/docs/architecture.md)
- [AndroidX WebKit `WebViewCompat`](https://developer.android.com/reference/androidx/webkit/WebViewCompat)
- [`ApplicationExitInfo`](https://developer.android.com/reference/android/app/ApplicationExitInfo)
- [`ActivityManager.getHistoricalProcessExitReasons()`](https://developer.android.com/reference/android/app/ActivityManager#getHistoricalProcessExitReasons(java.lang.String,%20int,%20int))
- [Android 17 kernel `mm/vmscan.c`](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/mm/vmscan.c)

## 小结

Renderer gone 的恢复原则可以压缩成五句话：

1. Android 17 固定 framework 契约，设备 provider 版本用于定位具体 Chromium 实现；
2. 回调中的旧 WebView 只能移除、销毁和清引用；
3. 每个受影响实例都要处理，共享 Renderer 不能漏；
4. 自动恢复必须受页面可否重复加载、Activity 状态和次数上限约束；
5. 视觉提交与业务就绪都成功，才能计为用户已恢复。

把 gone 事件、旧实例清理、新实例状态和 provider 版本放在同一条事件记录中，才能区分系统回收、Renderer 崩溃、主动终止和恢复代码自身的缺陷。
