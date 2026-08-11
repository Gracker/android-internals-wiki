---

title: "WebView Renderer OOM 与白屏恢复"
chapter: "20.10"
section: "20.10"
status: finalized
applicable_versions: "Android 8 (API 26) - Android 17 (API 37)"
last_verified: "2026-06-08"
last_verified_against: "AOSP android-16.0.0_r1 frameworks/base WebView APIs, Android Developers API refs through API 37, AndroidX WebKit API reference, Clippings structure reference"
confidence: medium
drafted_date: "2026-05-15"
polish_count: 0
sources:
  - type: clippings-structure-ref
    path: "Clippings/Android 应用稳定性剖析与优化 - OOM 发生路径：了解 OOM 是如何产生的.md"
  - type: research-note
    path: "OpenClaw定时任务/AutoResearchClaw调研报告/2026-05-05-webview-render-process-oom-recovery-onrendeprocessgone.md"
  - type: aosp
    path: "android-16.0.0_r1: frameworks/base/core/java/android/webkit/WebViewClient.java"
  - type: aosp
    path: "android-16.0.0_r1: frameworks/base/core/java/android/webkit/RenderProcessGoneDetail.java"
  - type: aosp
    path: "android-16.0.0_r1: frameworks/base/core/java/android/webkit/WebView.java"
  - type: aosp
    path: "android-16.0.0_r1: frameworks/base/core/java/android/webkit/WebViewRenderProcessClient.java"
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
created_by: "task2a-knowledge-gap"
created_date: "2026-05-15"
gap_source: "素材驱动/官方文档"
reviewed_by: "openclaw-task6"
reviewed_date: "2026-05-15"
task6_result: pass-light-edit
task6_state: reviewed
last_task6_audit: "2026-07-04"
task9_state: reviewed
task2b_state: fixed
pipeline_stage: ready-to-publish
task9_result: auto-fixed
task9_reviewed_date: '2026-06-08'
task9_reviewed_by: openclaw-task9
last_task9_at: '2026-06-08T16:24:00+08:00'
last_task9_audit: '2026-06-08'
last_task9_audit_log: 'logs/deep-review/2026-06-08-16-audit.md'
last_task9_autofix_at: '2026-06-08'
task9_review_notes: '2026-05-15 task9 deep-review: pass-tech-review。无 P0/P1；P2 3；满足 Task6 pass 与 queue 无 pending，自动晋升 finalized。 | 2026-06-08 16 Task9 idle audit: auto-fixed。将 AOSP master 源码锚点收敛到 android-16.0.0_r1；补正 rendererPriorityAtExit 共享 Renderer 语义、WebViewCompat(context) 签名和 ApplicationExitInfo 证据标签；未使用 Android 18/API 38+ 内容。'
last_task9_review_log: 'logs/deep-review/2026-06-08-16-audit.md'
deepseek_cn_review_state: done
last_deepseek_cn_review_at: 2026-06-09
---

# 20.10 WebView Renderer OOM 与白屏恢复

WebView 页面突然变白时，宿主 Activity 可能仍能响应，导航栏和原生按钮也都正常。若同时收到 `onRenderProcessGone()`，可以确认关联的 WebView Renderer 已退出；此时旧 `WebView` 失效，`reload()`、`goBack()`、`evaluateJavascript()` 和 JS Bridge 调用都不能作为补救手段。

平台锚点是 Android 17 / API 37 / `android-17.0.0_r1` 的 framework 契约。WebView provider 是独立更新的 Chromium 或厂商实现，还要记录设备上的 provider 包名与版本。涉及内存压力的内核观察统一以 `android17-6.18-2026-06_r6` 为锚点。

## 先分清平台、Provider 和进程

标准 `android.webkit.WebView` 同时跨越两条版本线：

- Android 平台提供 `WebView`、`WebViewClient`、Renderer 优先级和终止处理 API；
- WebView provider 包提供 Chromium/Blink、合成、沙箱 Renderer 和大部分实现，可独立于系统版本更新。

因此，`android-17.0.0_r1` 能固定公开 API 与 framework 注释，不能唯一确定设备上的 Chromium revision。复盘至少要记录 Android build、provider package、`versionName`、`versionCode`、ABI、设备型号，以及应用使用的是系统 WebView、定制 Chromium 还是第三方内核。

现代标准 WebView 可以按三个执行域理解：

1. 宿主进程保存 `WebView` Java 对象、Activity/Fragment 状态、业务 Bridge，以及 provider 的 browser-side 代码；
2. 沙箱 Renderer 运行 Blink、JavaScript、style、layout、paint 和 renderer 合成工作；
3. 宿主 HWUI RenderThread 通过 WebView functor 消费 provider 结果，通常把网页主体合入 App Window，再交给 SurfaceFlinger 和 HWC。

视频、受保护内容或 provider overlay 可能增加独立 `SurfaceControl` layer。Renderer 退出后，已提交的旧帧可能短暂保留，也可能变成空白或静止画面；页面能否继续交互不能由宿主窗口是否还在来判断。

## `onRenderProcessGone()` 能证明什么

Android 8 / API 26 起，`WebViewClient.onRenderProcessGone(view, detail)` 是 Renderer 退出后的公开入口。Android 17 的 `WebViewClient.java` 给出四条硬约束：

- 多个 WebView 可能关联同一个 Renderer；
- 每个受影响的 WebView 都会收到回调；
- 当前回调只清理参数中的 `view`，不能假设其他实例也已退出；
- 传入的 WebView 不能继续使用，必须从 View 层级移除并清理引用。

返回值决定宿主是否继续运行：

| 返回值 | Android 17 契约 | 工程含义 |
| --- | --- | --- |
| `true` | 应用声明已处理退出 | 当前旧实例已被移除、销毁，业务进入恢复或兜底状态 |
| `false` | Renderer crash 时宿主 crash；Renderer 被系统 kill 时宿主被结束 | 应用没有能力安全处理，保留默认终止语义 |

默认实现返回 `false`。只有在清理动作已完成、后续代码不会再触碰旧实例时，才应返回 `true`。用 `true` 隐藏回调后仍在访问旧对象的错误，会把一次清晰的 Renderer 退出变成随机异常或长期白屏。

### `didCrash()` 是二分类，不是完整归因

`RenderProcessGoneDetail.didCrash()` 返回：

- `true`：Renderer 被观察到发生 crash；
- `false`：Renderer 被系统 kill，AOSP 注释说明最常见背景是低内存。

`false` 仍不足以单独证明“页面 OOM”。应用在 API 29 及以上可能主动调用 `WebViewRenderProcess.terminate()`；provider 更新、设备实现和系统资源管理也会影响进程寿命。若应用有主动终止策略，要在调用前记录一次短时有效的 termination token，随后将对应 gone 事件标记为“预期终止”。没有 token 时，再结合设备内存档位、前后台状态、Renderer 优先级、系统内存压力和复发页面判断。

`rendererPriorityAtExit()` 返回退出时的最终 Renderer 优先级。一个 Renderer 可被多个 WebView 共享，`WebView.java` 按已关联实例请求优先级的最大值计算最终优先级；`RenderProcessGoneDetail.java` 也明确提醒，退出值可能高于某个单独实例请求的值。因此，它适合描述现场，不能反推出是哪一个 WebView 导致 Renderer 被保活或回收。

`RenderProcessGoneDetail` 不提供 Renderer PID、页面内存、JS heap、Native 栈或最近网络请求。公开 API 没有精确的 Renderer 内存读数，不能用宿主 PSS 冒充。

## 恢复是一段状态迁移

可靠的容器应把 Renderer gone 处理成状态迁移：

```text
ACTIVE
  -> GONE_CALLBACK
  -> DETACHED_AND_DESTROYED
  -> RECOVERY_UI
  -> NEW_WEBVIEW_LOADING
  -> VISUAL_COMMITTED
  -> BUSINESS_READY
```

任一步失败都进入兜底页。`VISUAL_COMMITTED` 只能说明新页面内容已提交到 WebView；支付、编辑、登录等页面还需要 H5 自己发出可校验的 `BUSINESS_READY`，并由宿主设置超时。

恢复前要回答三个问题：

1. 当前页面能否安全重放？
2. 是否已有一次自动恢复尝试？
3. Activity 是否仍处于可展示状态？

资讯详情、帮助页等幂等页面可以自动恢复。支付提交、表单编辑、身份验证和一次性 URL 应跳转到服务端状态查询或兜底页，不能原样重放。原始 URL 可能含 token、订单号和查询参数，上报与 checkpoint 都要按业务规则裁剪。

## 一个可控的 Activity 恢复骨架

下面的示例展示单 WebView Activity 的最小恢复状态。业务方法留作接口，重点是旧实例清理、异步重建、恢复预算和页面可用信号：

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

旧实例只调用官方要求的移除与 `destroy()`，没有再设置 client、停止加载或执行 JS。代码先把 `RenderProcessGoneDetail` 快照成普通值，避免异步任务继续持有回调对象；遥测函数也必须保证异常不会逃逸。重建通过 `container.post` 延后到回调返回之后，减少回调内重入；任务执行前再次检查 Activity 状态。自动恢复预算写入 `savedInstanceState`，避免一次配置变更重新获得恢复次数。

示例对 crash 采取保守策略：同一页面可能稳定复现 Chromium 或内容触发的崩溃，因此不自动重载。被 kill 的页面也只有一次自动恢复机会。`WebCheckpoint` 应保存去敏后的业务路由和重放策略，不应序列化完整 Web history、POST 数据或 JS 运行时状态。

`configureWebView()` 要统一恢复安全与功能配置，包括允许的 origin、Safe Browsing、Cookie 策略、文件访问、混合内容、WebChromeClient 和 Bridge。只有可信页面需要的 Bridge 才能重新注册。若每个业务页面自行 new WebView，很容易在恢复实例上漏掉安全配置。

### 多 WebView 容器

共享 Renderer 时，同一轮退出会触发多个回调。每个回调都只销毁自己的 `view` 并返回 `true`；容器管理器再按页面栈决定统一展示错误页或等待所有实例完成清理。不能在第一个回调中假设其余 WebView 已失效，也不能漏掉后台、缓存池或 ViewHolder 中的实例。

引用清理至少覆盖：

- Activity、Fragment 与自定义 View 字段；
- Adapter、ViewHolder 和页面栈；
- WebView 缓存池；
- JS Bridge、ValueCallback、下载与文件选择回调；
- 延迟 Runnable、协程和业务观察者。

回调完成后仍持有旧 WebView 的任务要被取消或通过实例 token 拒绝执行。

## Renderer 优先级与低内存策略

`WebView.setRendererPriorityPolicy(priority, waivedWhenNotVisible)` 只影响 multiprocess Renderer 的 OOM 调整倾向，不是内存上限。Android 17 定义三个级别：

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

这项策略释放的是系统选择权，不会立即释放页面内存。它只适合已经覆盖全部关联 WebView 的 `onRenderProcessGone()`、能够识别敏感页面、并且允许后台页面重建的容器。可见交易页通常不应为了节省内存盲目降低优先级。

多个 WebView 共享 Renderer 时，最终优先级取关联实例请求值的最大值；销毁某个 WebView 后，它不再参与计算。只修改一个后台实例，未必改变共享 Renderer 的最终优先级。

## 怎样判断内存诱因

WebView 页面资源分布在多个域：

- Renderer：DOM、JS heap、Blink 对象、已解码图片和部分 raster 资源；
- 宿主/provider：browser-side 状态、Bridge、缓存与 WebView 对象；
- GPU/图形：纹理、tile、buffer 与驱动分配；
- 系统：其他进程竞争、zram、reclaim 和设备内存档位。

所以，宿主 Java heap 正常不能排除 Renderer 或图形内存压力；Renderer 被 kill 也不能反向证明某个 JS 对象泄漏。

一次有效的 gone 事件至少记录：

| 维度 | 字段 |
| --- | --- |
| 页面 | 去敏 route、H5 build、页面类型、停留时长、幂等策略 |
| 容器 | WebView 数量、是否来自缓存池、可见性、自动恢复次数 |
| 退出 | `didCrash`、`rendererPriorityAtExit`、预期 termination token |
| Provider | package、`versionName`、`versionCode`、系统/定制内核类型 |
| 宿主 | 进程前后台、PSS/RSS、最近 `onTrimMemory()`、进程存活时长 |
| 设备 | Android build、API、ABI、内存档位、设备型号 |
| 恢复 | 销毁完成、新实例创建、visual commit、H5 ready、兜底原因 |

在 Android 8 及以上，可在 WebView 已加载后用 `WebView.getCurrentWebViewPackage()` 获取当前 provider 的 `PackageInfo`。在 AndroidX WebKit 环境也可使用相应兼容 API。provider `versionName` 常能帮助定位 Chromium 版本，但厂商格式不统一；解析 milestone 只能作为 provider-specific 逻辑。

实验室可用 Perfetto、bugreport、Chrome DevTools 和 provider 对应的 Chromium 符号调查 Renderer、GPU 与系统内存压力。观察 Android 内核时，把 reclaim、PSI memory、zram、page fault 和 dma-buf 证据固定到 `android17-6.18-2026-06_r6`。线上公开 API 通常拿不到 Renderer 精确 PSS，不要通过反射、读取其他进程 `/proc` 或私有 Chromium 接口构造不稳定方案。

`ApplicationExitInfo` 适合补充宿主进程退出原因。Renderer 被回收而宿主继续运行时，不一定会产生应用可查询的对应记录；它不能替代 `onRenderProcessGone()` 事件，也不能与某次 Renderer gone 强行一一配对。

## WebViewRenderProcessClient：发现卡死，谨慎终止

Android 10 / API 29 起，`WebViewRenderProcessClient` 提供：

- `onRenderProcessUnresponsive()`：Renderer 因长阻塞任务等原因无法及时处理输入或导航；
- `onRenderProcessResponsive()`：同一 Renderer 恢复响应后回调一次。

Android 17 源码说明，无响应期间会重复回调，相邻回调最短间隔为 5 秒；WebView 不会自动采取动作。一次 unresponsive 回调不等于 ANR，也不等于 Renderer 必须被杀。应记录持续时间、页面阶段、用户是否可退出，以及 H5 是否正在执行预期的重任务。

当产品允许用户放弃当前页面，且所有共享 WebView 都已实现终止处理时，才考虑调用 `renderer?.terminate()`。调用前要：

1. 写入短时有效的预期 termination token；
2. 切断新的 JS 注入和导航；
3. 展示不会依赖旧 WebView 的原生 UI；
4. 限制一次会话中的终止次数；
5. 等待随后的 `onRenderProcessGone()` 完成清理。

`WebViewRenderProcess` 是不透明句柄，回调参数在单进程模式下还可能为 `null`。`terminate()` 返回 `true` 只表示终止请求得以发出，不代表新页面已经恢复。

## 指标要覆盖发生、清理和可用

Crash 率看不到那些已返回 `true` 的 Renderer gone。建议用事件状态串记录一次恢复：

| 状态 | 判定 |
| --- | --- |
| `gone_received` | 回调到达，按 crash / killed / expected terminate 拆分 |
| `old_view_destroyed` | 参数 View 已移除、引用已释放并调用 `destroy()` |
| `new_view_created` | 恢复预算允许且新实例已加入容器 |
| `visual_committed` | 新实例收到 `onPageCommitVisible()` |
| `business_ready` | H5 业务握手完成，关键接口可用 |
| `fallback_shown` | 进入原生兜底，并记录原因 |
| `repeat_gone` | 同一会话或短窗口内再次退出 |

核心指标必须有分母：

- Renderer gone 用户率、会话率和页面访问率；
- crash、系统 kill、预期终止的占比；
- 从 gone 到 visual commit、business ready 的成功率和耗时分布；
- 自动恢复后的 repeat gone 率；
- 敏感页面的兜底率与业务完成率；
- 按 provider 版本、route、设备内存档位和前后台状态拆分的差异。

“新 WebView 已创建”不算恢复成功，`onPageFinished()` 也不能保证用户已经看到可操作内容。视觉提交加业务握手更接近用户体验；两者都需要超时和实例 token，防止旧回调误报新实例成功。这个组合仍是产品侧代理信号，不是 SurfaceFlinger display present 的证明；需要逐帧诊断时，应继续检查宿主窗口 FrameTimeline 与显示提交。

## 灰度、回滚和恢复预算

远程配置应位于容器层，常用控制项包括：

- 是否允许 killed 场景自动恢复；
- 哪些 route 只展示兜底页；
- 每个会话的自动恢复次数；
- 是否启用 WebView 缓存池；
- 后台 WebView 是否请求较低 Renderer 优先级；
- 哪些 provider 版本暂停自动重载。

远程开关不能依赖已经退出的 WebView 拉取。配置要在进入 H5 容器前缓存，并为离线状态准备保守默认值。

若某个 provider 版本集中发生 Renderer crash，暂停自动重载同一页面，保留 provider、H5 build 和去敏 route 证据。provider 是独立更新组件，同一 Android 版本出现不同结果很常见；Android 平台版本不能替代 provider 分组。

## 故障演练

测试要覆盖不同退出方式与生命周期竞态：

| 用例 | 需要确认 |
| --- | --- |
| `chrome://crash` | crash 被识别，所有共享实例清理，宿主不退出 |
| `WebViewRenderProcess.terminate()` | 预期 token 命中，gone 回调完成，终止次数受限 |
| 内存压力下 Renderer 被回收 | killed 分支、后台延迟恢复、前台重建策略 |
| 两个 WebView 共享 Renderer | 每个受影响实例都返回 `true`，没有漏清理 |
| 回调后 Activity 立即销毁 | posted 恢复任务不创建泄漏实例 |
| 敏感页面退出 | 不重放 POST、一次性 URL 或未确认交易 |
| 新页面再次 gone | 自动恢复预算生效并进入兜底 |
| provider 更新或切换 | 进程重启后记录的新版本正确 |

`chrome://crash` 只能放在 debug/test 工具中，并且可能影响共享 Renderer 的多个 WebView。它验证 crash 处理，不能代替低内存回收。内存压力测试应在可控设备上结合 Perfetto 或 bugreport 确认系统背景，不能用一次手工白屏证明 OOM。

API 26 以下没有 `onRenderProcessGone()`。若产品仍支持更低版本，需要单独定义进程级隔离、页面兜底和 provider 升级策略；不要把 API 26 的恢复契约套到旧系统。

## 常见误判

| 误判 | 更严谨的结论 |
| --- | --- |
| 白屏就是 Renderer OOM | 只有 gone 回调能确认 Renderer 已退出；网络、HTTP、SSL、页面脚本和绘制停滞也会白屏 |
| `didCrash=false` 就是页面 OOM | 它表示非 crash 的 kill；还要排除预期 terminate，并补系统内存压力证据 |
| 返回 `true` 就完成恢复 | 旧实例清理、新实例重建、视觉提交和业务 ready 都要验证 |
| 在旧实例上 `reload()` 能救回页面 | gone 后旧 WebView 不可复用，只能移除、销毁和新建 |
| 恢复时原样加载完整 URL | URL 可能敏感或不可重放，应使用业务 checkpoint |
| 一个 WebView 收到回调就能批量销毁 | 当前回调只处理参数实例，共享 Renderer 会逐个通知 |
| 宿主 PSS 就是 Renderer 内存 | 两者属于不同进程/执行域，公开 API 没有精确 Renderer PSS |
| Android 17 决定 Chromium 行为 | 还要固定设备 provider 包版本与对应 revision |
| Renderer frame ready 代表恢复可用 | 还需宿主绘制、visual commit 和业务握手 |

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
- [Chromium WebView architecture](https://chromium.googlesource.com/chromium/src/+/refs/heads/main/android_webview/docs/architecture.md)
- [AndroidX WebKit `WebViewCompat`](https://developer.android.com/reference/androidx/webkit/WebViewCompat)
- [`ApplicationExitInfo`](https://developer.android.com/reference/android/app/ApplicationExitInfo)
- [Android 17 kernel `mm/vmscan.c`](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/mm/vmscan.c)

## 小结

Renderer gone 的恢复原则可以压缩成五句话：

1. Android 17 固定 framework 契约，设备 provider 版本固定 Chromium 实现；
2. 回调中的旧 WebView 只能移除、销毁和清引用；
3. 每个受影响实例都要处理，共享 Renderer 不能漏；
4. 自动恢复必须受页面幂等性、Activity 状态和次数预算约束；
5. visual commit 与业务 ready 都成功，才能计为用户已恢复。

把 gone 事件、旧实例清理、新实例状态和 provider 版本放在同一条事件记录中，才能区分系统回收、Renderer crash、主动终止和恢复代码自身的缺陷。
