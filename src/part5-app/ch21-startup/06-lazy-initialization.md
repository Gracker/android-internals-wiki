---
title: "延迟初始化与按需加载"
chapter: "21.6"
section: "21.6"
status: finalized
applicable_versions: "Android 10 (API 29) - Android 17 (API 37)"
last_verified: "2026-06-29"
last_verified_against: "AOSP android-17.0.0_r1 LegacyMessageQueue / CombinedDeliMessageQueue, Android Developers launch-time / App Startup / Play Feature Delivery docs"
confidence: medium
drafted_date: "2026-05-13"
polish_count: 0
sources:
  - type: aosp
    path: "frameworks/base/core/java/android/os/LegacyMessageQueue/MessageQueue.java + frameworks/base/core/java/android/os/CombinedDeliMessageQueue/MessageQueue.java (android-17.0.0_r1, IdleHandler / next())"
  - type: official
    path: "https://developer.android.com/topic/performance/vitals/launch-time"
  - type: official
    path: "https://developer.android.com/topic/libraries/app-startup"
  - type: official
    path: "https://developer.android.com/guide/playcore/feature-delivery"
  - type: clippings-structure-ref
    path: "Clippings/Android 性能优化 - CPU 优化（下）：减少 CPU 闲置时刻和等待，提升利用率.md"
  - type: clippings-structure-ref
    path: "Clippings/Android 性能优化 - 原理：重新认识应用的速度优化.md"
  - type: clippings-structure-ref
    path: "Clippings/Android 性能优化 - so 文件的体积优化实战.md"
tags: [lazy-init, idlehandler, on-demand-loading, app-startup]
related_chapters: ["21.2", "21.3", "1.13"]
pipeline_stage: ready-to-publish
task6_state: reviewed
task9_state: reviewed
task2b_state: fixed
reviewed_by: openclaw-task6
reviewed_date: "2026-06-29"
task6_reviewed_date: "2026-06-29"
last_task6_audit: "2026-06-29"
task6_result: pass-light-edit
task9_result: auto-fixed
task9_reviewed_by: openclaw-task9
task9_reviewed_date: "2026-06-29"
last_task9_at: "2026-06-29T21:30:52+08:00"
last_task9_audit: "2026-06-29"
task9_review_notes: "2026-06-29 闲时抽检 AUTO-FIX：将 IdleHandler / MessageQueue 源码锚点从 android-15.0.0_r1 更新到 android-17.0.0_r1 LegacyMessageQueue + CombinedDeliMessageQueue，并补 targetSdk 37 DeliQueue 版本边界；回到 Task6 复审。"
last_task9_review_log: "logs/deep-review/2026-06-29-21-audit.md"
last_task9_autofix_at: "2026-06-29"
task2b_result: fixed
deepseek_cn_review_state: done
last_deepseek_cn_review_at: 2026-06-27
---

# 延迟初始化与按需加载

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 延迟初始化策略：首帧后、首次使用、后台空闲
- 🔹 IdleHandler 与空闲加载
- 🔹 按需加载与模块懒加载
- 🔹 延迟初始化的风险与兜底

### 扩展（可选深入）

- 🔸 （待扩展）

### OpenClaw 加工指引

> **锚点**是最低覆盖要求，加工时必须逐条落实并标注验证结果。
> **扩展**视素材丰富程度选择性深入。
> 如果从 Obsidian 素材或 AOSP 源码中发现大纲未列出但与本节强相关的知识点，
> 可**就地插入**最相关的锚点之后，并用 `[自动发现]` 标注，方便后续 review。
> 锚点内容需 L1/L2 验证，扩展内容至少 L2 验证，自动发现内容至少标注来源。
<!-- outline-end -->

## 本节定位

21.2 节讲启动任务如何编排，21.3 节讲 ContentProvider 自动初始化怎么治理。本节处理更靠后的动作：**哪些初始化可以移出首帧前，移到哪里执行，什么时候再补回来**。

启动优化里最容易做错的事，是把所有任务都异步化。异步只改变线程，不一定改变用户等待时间；延迟初始化改变的是执行时机，把非首屏必需任务从 Time to initial display（TTID）之前移走，再用 Time to full display（TTFD）、首次使用耗时和异常率约束风险。

[已验证: 官方文档, developer.android.com/topic/performance/vitals/launch-time]
[结构参考: Clippings/Android 性能优化 - 原理：重新认识应用的速度优化.md]

## 延迟初始化策略：首帧后、首次使用、后台空闲

延迟初始化要先给任务分层。不能只按耗时排序，也不能只按 SDK 归属排序。判断一个任务能不能延后，至少看四个条件：首屏是否直接用到、失败后能不能降级、是否持有全局状态、是否会在用户操作时造成可见等待。

### 三个可用时机

| 时机 | 适合放什么 | 不适合放什么 | 观察指标 |
|---|---|---|---|
| 首帧后 | 首屏不依赖，但用户很快可能用到的 SDK 或缓存 | 必须参与首屏渲染、登录态判断、灰度路由的任务 | TTID 下降，TTFD 不明显恶化 |
| 首次使用 | 低频功能、二级页面、可明确触发的业务模块 | 首次使用不能等待的支付、风控、消息通道 | 首次点击耗时、功能失败率 |
| 后台空闲 | 预热数据、冷门资源解压、二级缓存构建 | CPU 密集且不可切片的任务 | 空闲窗口长度、前台帧率、功耗 |

Android Vitals 把冷启动 5 秒、温启动 2 秒、热启动 1.5 秒作为过慢启动的判断边界。延迟初始化的目标是把首帧前的必要工作压到合理范围，同时确认延后的任务不会在 TTFD 或首次使用阶段反弹。

[已验证: 官方文档, developer.android.com/topic/performance/vitals/launch-time]

### 首帧后执行

首帧后执行适合放“很快会用到，但不该阻塞首帧”的任务，例如日志 SDK 的批量上传通道、二级页面的路由表预热、图片库的非首屏配置。实现上可以在首帧回调后投递到启动框架的 LOW 队列，由统一线程池分批运行。

这类任务要有时间预算。一个常见做法是每个任务声明 `maxCostMs` 和 `deadlineAfterFirstFrameMs`：任务超过预算就切片，或者放到下一轮空闲窗口。否则首帧虽然提前了，第二帧和第三帧会被集中初始化拖慢。

[结构参考: Clippings/Android 性能优化 - CPU 优化（下）：减少 CPU 闲置时刻和等待，提升利用率.md]

### 首次使用执行

首次使用适合低频且边界清楚的模块。典型例子是扫码、直播、地图、编辑器、AR、美颜、客服 IM。它们的共同点是：入口明确，用户点击前不必完成完整初始化。

首次使用延迟要加两层兜底：

- **轻量门面**：入口层只暴露接口和状态，不直接触发重初始化。调用方先拿到 `READY / LOADING / FAILED`，再决定展示加载态、降级页或错误提示。
- **预触发**：用户靠近入口时提前开始加载，例如进入“发布”页时预热拍摄模块，而不是点下“拍摄”按钮才加载。

下面这段伪代码展示按需模块的门面写法。重点是把“是否已加载”和“怎么加载”收在同一个对象里，避免业务方到处写双重检查。

```kotlin
class FeatureGate<T>(
    private val loader: suspend () -> T,
) {
    @Volatile private var instance: T? = null
    private val lock = Mutex()

    suspend fun getOrLoad(): T {
        instance?.let { return it }
        return lock.withLock {
            instance ?: loader().also { instance = it }
        }
    }

    fun isReady(): Boolean = instance != null
}
```

这段代码只能作为结构示意。真实工程里还要补超时、取消、失败缓存、埋点和多进程状态同步，否则首次使用阶段可能出现重复加载或长时间等待。

### 后台空闲执行

后台空闲适合预加载和缓存重建。参考书里给出的思路是读取 `/proc/stat` 与 `/proc/[pid]/stat`，按时间窗口估算 CPU 使用率，确认应用处于低负载后再执行预加载任务。这个方向适合做跨线程的空闲判断，但它不能替代主线程队列的空闲判断。

工程上通常把两类信号合并：

- 主线程队列空闲：说明 UI 线程暂时没有到期消息，适合投递轻量主线程工作。
- 进程 CPU 空闲：说明后台任务不会明显抢 CPU，适合执行 IO、预解压、缓存构建。

两者都满足时，才执行更重的预热任务；只满足主线程空闲时，只执行几十毫秒内能结束的小任务。

[结构参考: Clippings/Android 性能优化 - CPU 优化（下）：减少 CPU 闲置时刻和等待，提升利用率.md]

## IdleHandler 与空闲加载

`MessageQueue.IdleHandler` 是 Android 主线程空闲加载里最常见的工具。AOSP 对它的定义很明确：当 MessageQueue 没有可立即分发的消息、即将等待更多消息时调用 `queueIdle()`；返回 `true` 会保留这个 IdleHandler，返回 `false` 会在本次执行后移除。

[已验证: AOSP android-17.0.0_r1, frameworks/base/core/java/android/os/LegacyMessageQueue/MessageQueue.java 与 frameworks/base/core/java/android/os/CombinedDeliMessageQueue/MessageQueue.java]
[详见 1.13 节]

Android 17 下，`targetSdkVersion >= 37` 的应用会进入新的 lock-free `MessageQueue` 路径；AOSP `android-17.0.0_r1` 中旧路径在 `LegacyMessageQueue/MessageQueue.java`，新路径在 `CombinedDeliMessageQueue/MessageQueue.java`。`IdleHandler` 的 API、返回值和“没有可立即分发消息时触发”的语义保留，但新路径不再等同于旧版 `synchronized (this) + mMessages` 单链表结构。下面的流程只用于解释旧实现路径；Android 17 DeliQueue 场景要看 `nextDeliQueue()`、`mStack.hasMessages(...)` 和 `mIdleHandlersLock`。

### 它在 `next()` 里的触发条件与 Android 17 边界

旧实现 `MessageQueue.next()` 的流程可以压缩成这样：

```text
nativePollOnce(ptr, timeout)
  ↓
synchronized(this) 取到期消息
  ↓
没有到期消息，且队列为空或头部消息还没到执行时间
  ↓
复制 mIdleHandlers 到 mPendingIdleHandlers
  ↓
退出锁，逐个调用 queueIdle()
  ↓
返回 false 的 handler 从列表移除
```

这段流程给出两个使用边界。

`queueIdle()` 不应该执行重任务。它运行在 Looper 所在线程，主线程上的 IdleHandler 就在主线程执行。一次空闲回调里做 100ms 初始化，等价于把一段主线程长任务插到下一条消息之前。

`queueIdle()` 不是“系统很闲”的信号。它只说明当前队列没有可立即分发的消息，队列里可能已经有未来时间点的消息，也可能马上收到输入事件、VSync 或 Binder 回调。

### 合适的写法

IdleHandler 适合做调度入口，不适合直接做执行容器。主线程只做拆片、登记和轻量检查，耗时任务转到后台线程。

下面这段代码用于说明一次性空闲任务的写法。重点看返回值和主线程停留时间。

```kotlin
Looper.myQueue().addIdleHandler {
    StartupExecutor.executeLowPriority("preload-secondary-route") {
        routeRegistry.preloadSecondaryPages()
    }
    false
}
```

返回 `false` 表示只执行一次。后台任务还要受统一队列控制，避免多个 IdleHandler 同时把低优先级任务灌进线程池。

### 常见误用

| 误用 | 后果 | 修正 |
|---|---|---|
| 在 `queueIdle()` 里直接读大文件 | 主线程空闲窗口被占满，下一帧或输入事件延迟 | 只投递后台任务，主线程不做 IO |
| 返回 `true` 做轮询 | 每次空闲都执行，难以控制频率 | 用一次性 IdleHandler，加显式调度周期 |
| 所有 SDK 都注册 IdleHandler | 空闲窗口被多个 SDK 抢占 | 接入启动框架，由框架统一排队 |
| 把 IdleHandler 当首帧后回调 | 首帧前也可能出现队列空闲 | 首帧后任务用绘制完成信号或启动框架状态触发 |

[已验证: AOSP android-17.0.0_r1, LegacyMessageQueue/MessageQueue.java 与 CombinedDeliMessageQueue/MessageQueue.java, MessageQueue.IdleHandler.queueIdle()]

## 按需加载与模块懒加载

按需加载解决的是“用户没用到就不加载”。它和首帧后延迟不同：首帧后延迟只是换时机，按需加载还会改变加载条件。条件没满足，任务就不执行。

### App Startup 的手动初始化

Jetpack App Startup 默认通过 `InitializationProvider` 自动发现并执行 `Initializer`。官方文档也支持手动初始化：移除对应 initializer 的 manifest 元数据后，用 `AppInitializer` 在需要时触发。这适合从 ContentProvider 自动初始化迁移出来的 SDK。

[已验证: 官方文档, developer.android.com/topic/libraries/app-startup]
[详见 21.3 节]

迁移时要避免两种状态：

- SDK 仍被 `InitializationProvider` 自动拉起，手动初始化没有减少启动成本。
- 自动初始化移除了，但调用方没有走门面，首次使用时直接访问未初始化对象。

更稳的方案是把手动初始化接入 21.2 节的启动任务框架：任务保留依赖声明，但 `trigger` 从 `APP_START` 改成 `FIRST_USE` 或 `AFTER_FIRST_FRAME`。

### 动态 Feature 与资源按需下载

Google Play Feature Delivery 支持把功能拆成 feature module，并配置 install-time、conditional 或 on-demand delivery。on-demand 模块不在安装时默认可用，应用需要在使用前请求下载。

[已验证: 官方文档, developer.android.com/guide/playcore/feature-delivery]

这个能力适合体积大、低频、边界清楚的功能。它不适合首屏必需功能，也不适合从外部 intent 直接启动的 Activity。官方文档明确提醒：feature module 里的 Activity 不应配置 `android:exported=true`，因为设备不一定已经下载了该模块。

按需模块要把加载路径拆成四段：

1. 检查模块是否已安装。
2. 未安装时发起下载，展示明确的加载态。
3. 下载成功后加载代码或资源。
4. 失败时走降级页面或提示重试。

这四段都要埋点。按需加载如果只看启动耗时，会把成本转移到功能入口；只有同时看入口转化率、加载成功率、下载耗时和取消率，才能判断是否值得继续。

### SO / 资源解压的按需化

参考书中提到的 so 压缩与使用时解压，属于按需加载的一种形态。打包时压缩低频 so，运行时在 `System.loadLibrary()` 失败后解压，再用 `System.load()` 加载。这个方案能减少安装包体积，但会把 IO 和解压成本放到首次使用阶段。

[结构参考: Clippings/Android 性能优化 - so 文件的体积优化实战.md]

启动优化场景里更常见的取舍是：首屏相关 so 保持安装时可用，低频功能 so 才压缩或下发。否则首屏可能避开了包体成本，却在首次进入关键功能时出现长等待。

## 延迟初始化的风险与兜底

延迟初始化不是删任务，而是移动任务。移动之后，风险会从启动阶段转到运行阶段。

### 风险清单

| 风险 | 触发方式 | 兜底 |
|---|---|---|
| 首次使用卡顿 | 用户点击功能时才初始化 SDK 或加载模块 | 入口前预触发；展示加载态；设置超时 |
| 依赖顺序错乱 | A 延后后，B 仍假设 A 已完成 | 依赖统一声明；未满足依赖时返回明确状态 |
| 多线程重复初始化 | 多个入口同时触发同一 SDK | 单例门面加互斥；初始化结果缓存 |
| 崩溃归因变难 | 延后任务在运行中失败，堆栈远离启动阶段 | 记录 trigger、任务 ID、耗时和依赖状态 |
| 灰度不稳定 | 不同用户命中不同延迟策略 | 策略版本写入埋点和崩溃报告 |

### 任务声明字段

延迟任务进入框架前，建议强制声明这几个字段：

```yaml
taskId: preload_route_table
trigger: AFTER_FIRST_FRAME | FIRST_USE | MAIN_QUEUE_IDLE | PROCESS_IDLE
dependencies: [base_config, account_state]
thread: MAIN | IO | CPU | ANY
timeoutMs: 300
fallback: skip | retry | degrade_page
metrics: [cost_ms, success, trigger_source]
```

这些字段的用途是在出问题时回放决策：任务为什么没在启动时执行、为什么在这个入口触发、失败后走了什么降级路径。

### 验证方式

延迟初始化接入后，至少跑四组对比：

- 冷启动 TTID / TTFD：确认首帧改善没有换来完整可交互时间恶化。
- 首次使用耗时：确认功能入口没有产生新的长等待。
- 帧率与输入延迟：确认首帧后的任务没有挤占前几帧。
- 异常率与失败率：确认按需加载、动态下载、so 解压没有引入新的崩溃。

Perfetto 中看启动阶段，Android Vitals 中看线上启动分布，业务埋点中看首次使用成本。三类数据放在一起，才能判断延迟策略是否成立。

## 小结

延迟初始化的判断标准很直接：首帧前只保留用户马上能看见、马上会依赖、失败后不能降级的任务。其余任务按首帧后、首次使用、后台空闲三类时机移动，并用统一框架控制依赖、线程、超时和降级。

IdleHandler 可以作为主线程空闲信号，但不能承载重任务。按需加载能减少启动成本和安装成本，但必须把首次使用耗时纳入验收。启动变快只是第一步，用户第一次点进功能时仍然顺，才算这次延迟初始化有效。
