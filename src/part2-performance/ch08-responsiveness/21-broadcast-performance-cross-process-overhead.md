---
title: "Broadcast 性能与跨进程通信开销治理"
chapter: "8.21"
status: ready-for-review
drafted_date: "2026-07-17"
applicable_versions: "Android 14 (API 34) - Android 17 (API 37)"
last_verified: "2026-07-17"
last_verified_against: "AOSP android-17.0.0_r1"
confidence: high
sources:
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/am/BroadcastQueueModernImpl.java"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/am/BroadcastProcessQueue.java"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/am/BroadcastRecord.java"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/am/ActivityManagerService.java"
  - type: aosp
    path: "frameworks/base/core/java/android/content/BroadcastReceiver.java"
  - type: aosp
    path: "frameworks/base/core/java/android/content/Context.java"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/am/BroadcastConstants.java"
tags: [broadcast, broadcast-receiver, ipc, ordered-broadcast, performance, goasync]
related_chapters: ["1.33", "9.02", "9.09", "9.11", "1.17"]
created_by: "task2a-knowledge-gap"
created_date: "2026-07-16"
gap_source: "素材驱动"
---

# 8.21 Broadcast 性能与跨进程通信开销治理

Broadcast 适合把一条事件通知给数量未知、可能分属不同进程的接收者。它的代价也来自这项能力：系统要解析接收者、检查权限、安排目标进程、控制并发、必要时启动进程，再把回调交给应用线程。

因此，Broadcast 没有稳定的低延迟承诺。一次发送很快返回，只能说明 AMS 已接受请求；接收者何时运行还取决于目标进程、cached 策略、冷启动、队列槽、ordered 依赖和应用线程负载。需要同步结果、背压或稳定尾延迟的协议，应使用 bound service/AIDL 等明确的点对点接口。

应用工程需要关注四个问题：

- 怎样区分发送入队、系统排队、进程启动和 `onReceive()` 执行；
- normal、ordered、manifest 与 context-registered receiver 的完成语义；
- `goAsync()`、cached app、delivery group 和 sticky broadcast 的边界；
- 怎样选择替代 IPC，并用 Android 17 的观测数据验证结论。

平台源码锚点为 AOSP `android-17.0.0_r1`。BroadcastQueue 的数据结构与调度算法详见 [§1.33 Android 17 BroadcastQueue](../../part1-fundamentals/ch01-architecture/33-broadcastqueue-scheduling-performance.md)，这里不重复完整源码导读。

## 1. 从发送到接收的四段时间

一条广播的端到端延迟可拆成：

`端到端延迟 = 发送请求 + 接收者解析/校验 + 队列/冷启动 + 应用线程排队与执行`

| 阶段 | 起止点 | 主要变量 | 应用侧能否直接测量 |
| --- | --- | --- | --- |
| 发送请求 | 调用 `sendBroadcast()` 到方法返回 | Binder、Intent 序列化、AMS 锁、解析和入队 | 可以 |
| 系统排队 | `BroadcastRecord` 入队到选中目标进程 | runnableAt、running 槽、ordered 依赖、cached 状态 | 需系统 trace/dump |
| 进程准备 | 冷启动请求到 `ApplicationThread` 可用 | Zygote、bindApplication、应用初始化、系统负载 | 需进程启动 trace |
| 应用执行 | schedule 到 `onReceive()`/`finish()` | Binder、Handler、主线程、receiver 代码 | 应用埋点与 trace |

表中没有写固定毫秒数。已安装包数量、IntentFilter 形状、设备存储冷热和进程初始化都能改变结果。类似“解析固定 5～15 ms”“冷启动固定 300～800 ms”的数字只能描述某次实验，不能用作 Android 17 平台规则。

### 1.1 `sendBroadcast()` 是同步入队请求

Android 17 的 `ContextImpl.sendBroadcast()` 调用 `IActivityManager.broadcastIntentWithFeature()`。该 AIDL 方法返回 `int`，没有 `oneway` 标记，所以发送线程会同步等待 system_server 处理这次请求。

AMS 返回前会执行调用身份与权限检查、接收者查询、`BroadcastRecord` 构造和入队等工作。它不会等待所有接收者执行完毕。由此应同时保留两个判断：

- 不要在主线程高频发送大型或宽范围 implicit broadcast，发送动作本身可能占用主线程；
- 不要用 `sendBroadcast()` 的返回时刻代表接收完成。

源码入口：

- [`ContextImpl.sendBroadcast()`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/app/ContextImpl.java)
- [`IActivityManager.broadcastIntentWithFeature()`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/app/IActivityManager.aidl)
- [`BroadcastController.broadcastIntentLockedTraced()`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/am/BroadcastController.java)

### 1.2 缩小接收范围能减少工作，也能改善安全性

发送方知道目标包时，应使用 `Intent.setPackage()`；知道 manifest receiver 的确切组件时，可使用 `setComponent()`。跨应用私有协议还应配置发送或接收权限。

下面的发送代码把事件限制到一个已知包，并只携带资源标识：

```kotlin
private const val ACTION_INDEX_INVALIDATED =
    "com.example.search.action.INDEX_INVALIDATED"
private const val EXTRA_INDEX_ID = "index_id"
private const val RECEIVER_PERMISSION =
    "com.example.search.permission.RECEIVE_INDEX_EVENTS"

fun notifyIndexInvalidated(
    context: Context,
    targetPackage: String,
    indexId: String,
) {
    val intent = Intent(ACTION_INDEX_INVALIDATED)
        .setPackage(targetPackage)
        .putExtra(EXTRA_INDEX_ID, indexId)

    context.sendBroadcast(intent, RECEIVER_PERMISSION)
}
```

`setPackage()` 会缩小候选集合，权限阻止未授权接收者。事件只传 `indexId`，接收方再从权威数据源读取状态，避免把大对象复制到每个接收进程。

## 2. Android 17 的进程级队列模型

Android 14 的 AOSP 同时保留旧 `BroadcastQueueImpl` 与默认启用的 `BroadcastQueueModernImpl`。Android 15 使用 `BroadcastQueueModernImpl`；Android 16 起，进程级实现更名为 `BroadcastQueueImpl`。Android 17 标签中已经没有 `BroadcastQueueModernImpl.java`。

类名变化不影响公开 API，却会影响源码检索。基于 `android-17.0.0_r1` 做证据定位时，应查看：

- [`BroadcastQueueImpl.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/am/BroadcastQueueImpl.java)
- [`BroadcastProcessQueue.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/am/BroadcastProcessQueue.java)
- [`BroadcastRecord.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/am/BroadcastRecord.java)

### 2.1 一次发送会拆到多个目标进程队列

`BroadcastController` 合并 manifest receiver 与 context-registered receiver 后创建一个 `BroadcastRecord`。`BroadcastQueueImpl.enqueueBroadcastLocked()` 再按接收者的 `processName + uid`，把“BroadcastRecord + receiver 下标”放进对应的 `BroadcastProcessQueue`。

这项设计带来几条性能语义：

- normal broadcast 的不同目标进程具备并行推进的条件；
- 并行度仍受 running process queue 数量限制；
- 同一时刻最多发起一个广播冷启动；
- 同一目标进程的队列一次激活一个接收项；
- 无序动态 receiver 被系统视为已投递后，应用 Handler 中仍可能排着多个回调。

Android 17 的默认普通并发槽是 4，low-RAM 设备为 2，urgent 可额外使用 1 个槽。这些值可由 DeviceConfig 调整，不能当成所有设备的固定值。

### 2.2 “normal 是并行广播”不等于所有回调同时运行

无序广播没有跨 receiver 的完成依赖，但仍会经过：

1. 目标进程队列的 runnableAt 排序；
2. 全局 running 槽竞争；
3. 必要的进程冷启动；
4. 目标进程 Binder 线程接收；
5. receiver 指定 Handler 或默认主线程排队。

多个 receiver 恰好位于同一进程时，它们最终仍要由该进程的线程模型执行。默认主线程 receiver 无法并行运行。不同进程也可能因 running 槽和单冷启动槽分批得到调度。

## 3. receiver 类型决定完成语义

应用代码常把所有 `BroadcastReceiver` 当成同一种执行模型。Android 17 的 system_server 会按 receiver 类型、广播是否 ordered、是否有 completion callback 选择是否等待完成。

| receiver/广播组合 | 能否冷启动进程 | system_server 是否等待完成 | 广播 ANR 定时器 |
| --- | --- | --- | --- |
| manifest receiver | 可以 | 等待 `finishReceiver()` | 通常有 |
| ordered receiver | 视注册方式而定 | 等待，完成后才解除后继依赖 | 通常有 |
| 无序动态 receiver，无 completion callback | 进程已经存在 | schedule 成功后按 delivered 处理 | BroadcastQueue 不启动 |
| 动态 receiver，需回传结果 | 进程已经存在 | 等待完成 | 通常有 |

`BroadcastRecord.isAssumedDelivered()` 对“无序 + context-registered + 无 resultTo”的接收项返回 true。system_server 调用 `scheduleRegisteredReceiver()` 成功后，会立即标记该项完成并继续队列，不等 `onReceive()` 返回。

这不赋予动态 receiver 长时间占用主线程的许可。它仍会造成 UI 卡顿、阻塞应用后续广播，并可能触发输入、service 等其他 ANR。区别只在 BroadcastQueue 没有为这类投递等待完成回执。

### 3.1 `onReceive()` 默认在主线程，也可以指定 Handler

Manifest receiver 由 `ActivityThread` 的主线程 Handler 执行。调用 `registerReceiver(receiver, filter)` 时，`ReceiverDispatcher` 默认也投递到主线程。带 `Handler` 的 `registerReceiver` 重载可以选择其他 Looper。

即使回调已经放在后台 Handler，receiver 的广播完成窗口与进程生命周期规则仍然存在。线程位置只解决主线程占用，不会把 receiver 变成适合无限时长工作的组件。应用侧路径可从 [`LoadedApk.ReceiverDispatcher`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/app/LoadedApk.java) 和 [`ActivityThread.handleReceiver()`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/app/ActivityThread.java) 核对。

## 4. ordered broadcast 的串行边界

Ordered broadcast 会为 receiver 建立完成依赖。第 N 个接收者要等前面的接收者到达 delivered、skipped、timeout、failure 或可继续的 deferred 状态。它允许 result code/data/extras 传递，也允许符合规则的 receiver 中止剩余投递。

端到端延迟可以近似写成：

`总延迟 ≈ 接收者解析 + Σ(各 receiver 排队、启动、执行与回执) + resultTo`

任意一个 receiver 调用 `goAsync()` 后迟迟不 `finish()`，都会延长后继等待。某个目标进程尚未运行时，单冷启动槽和应用初始化也会进入依赖链。

### 4.1 Android 16～17 不提供跨进程 priority 全序

从 Android 16 开始，`android:priority` 与 `IntentFilter.setPriority()` 只保证在同一应用进程内的优先级关系。不同进程之间的顺序没有公开保证；应用 priority 还会被限制在系统保留上下界之间。

由此得到三条接口规则：

- 不要用跨应用 receiver priority 实现主从协议；
- 请求/确认、严格顺序和失败重试应放入 Binder 服务或持久化任务队列；
- ordered broadcast 只在业务需要 result/abort 语义时使用。

官方版本说明见 [Broadcasts overview](https://developer.android.com/develop/background-work/background-tasks/broadcasts#changes-system-broadcasts)。

## 5. 广播超时与 `goAsync()`

Android 17 的 AOSP 基准值为：

| 类型 | 选择条件 | 基准软超时 |
| --- | --- | ---: |
| foreground broadcast | Intent 带 `FLAG_RECEIVER_FOREGROUND` | `10 s × Build.HW_TIMEOUT_MULTIPLIER` |
| background broadcast | 未带上述标志 | `60 s × Build.HW_TIMEOUT_MULTIPLIER` |

AMS 会把这两个值写入 foreground/background `BroadcastConstants`。设备还可以通过 `Settings.Global.BROADCAST_FG_CONSTANTS`、`BROADCAST_BG_CONSTANTS` 改写 `bcast_timeout`；Android 17 的 `AnrTimer` 也启用了调度延展策略。表中数值是源码基准，不是应用可以使用的工作预算。

广播 ANR 计时在目标进程即将被 schedule 时开始。此前的队列等待与进程冷启动不计入 receiver 执行定时器。排障时，一条广播“发送后 70 秒才收到”和“`onReceive()` 执行 70 秒”属于两类问题。

### 5.1 `goAsync()` 改变完成方式，不会取消时限

`goAsync()` 返回 `PendingResult`，让 `onReceive()` 返回后仍可在其他线程完成短任务。系统等待 `PendingResult.finish()`，计时窗口不会重新开始。

下面的示例把工作交给应用级受控 scope，并保证所有退出路径完成 PendingResult：

```kotlin
private object ReceiverWork {
    val scope = CoroutineScope(
        SupervisorJob() + Dispatchers.IO
    )
}

class IndexInvalidatedReceiver : BroadcastReceiver() {
    override fun onReceive(
        context: Context,
        intent: Intent,
    ) {
        val pendingResult = goAsync()
        val appContext = context.applicationContext
        val event = Intent(intent)

        ReceiverWork.scope.launch {
            try {
                withTimeout(8_000) {
                    refreshIndexMetadata(appContext, event)
                }
            } catch (error: CancellationException) {
                recordReceiverCancellation(error)
                throw error
            } catch (error: Exception) {
                recordReceiverFailure(error)
            } finally {
                pendingResult.finish()
            }
        }
    }
}
```

示例复制 Intent 并使用 application context，避免把短命 receiver/context 状态带入异步工作。8 秒是应用内部保护值，不是系统统一建议；项目应根据前台 10 秒边界、任务最坏时长和设备数据设置更短上限。

这段模式只适合进程内可完成、允许失败的短任务。下载、上传、数据库迁移、大目录扫描和必须在进程死亡后重试的工作，应由 receiver 快速写入状态，再交给 WorkManager、JobScheduler 或具有明确生命周期的服务。

### 5.2 `finish()` 与业务完成要分清

过早调用 `finish()` 后再继续访问 receiver 专属结果，会失去广播生命周期保护；遗漏 `finish()` 则会让系统一直等到超时。正确设计应确定一个清楚的提交点：

- 已把幂等任务持久化入队，可以 `finish()`；
- 仍要回传 ordered result，等结果写入后再 `finish()`；
- 仅启动一条裸线程，任务没有持久化保证，进程在 receiver 失活后可能被回收。

[`BroadcastReceiver.goAsync()`](https://developer.android.com/reference/android/content/BroadcastReceiver#goAsync%28%29) 的公开文档同样要求保持响应，并在工作结束后调用 `PendingResult.finish()`。

## 6. cached app、deferral 与 delivery group

### 6.1 Android 14 起允许延迟 cached 进程的低价值广播

应用处于 cached 状态时，系统可以延后较低价值的 context-registered system broadcast。进程回到 active 后，再处理符合条件的积压项。重要的 manifest broadcast 可以让目标应用暂时离开 cached 状态并完成投递。

Android 17 的进程队列还会区分：

- ordered、alarm、prioritized、manifest 等不采用普通 cached 延迟的记录；
- cached 且允许无限 defer 的记录，等进程 active；
- cached 但不能无限 defer 的记录，默认增加 120 秒调度偏移；
- pending 数达到保护上限时，绕过部分延迟帮助排空。

120 秒来自 `BroadcastConstants.DELAY_CACHED_MILLIS` 的默认值，可由设备配置改变。应用只能依赖“cached 投递可能延后”的公开行为，不能写死这段时长。

### 6.2 delivery group 解决积压去重

Android 14 的 `BroadcastOptions` 可以明确指定 deferral 与 delivery group。下面的发送方式表示：目标不活跃时允许延后，同一账户的待投递事件只保留最近一条。

```kotlin
@RequiresApi(34)
fun sendLatestAccountState(
    context: Context,
    accountId: String,
) {
    val options = BroadcastOptions.makeBasic()
        .setDeferralPolicy(
            BroadcastOptions.DEFERRAL_POLICY_UNTIL_ACTIVE
        )
        .setDeliveryGroupMatchingKey(
            "com.example.account.STATE",
            accountId,
        )
        .setDeliveryGroupPolicy(
            BroadcastOptions.DELIVERY_GROUP_POLICY_MOST_RECENT
        )

    val intent = Intent(
        "com.example.account.action.STATE_CHANGED"
    )
        .setPackage("com.example.account.client")
        .putExtra("account_id", accountId)

    context.sendBroadcast(
        intent,
        null,
        options.toBundle(),
    )
}
```

只有业务允许丢弃中间状态时才使用 `MOST_RECENT`。例如“当前同步进度已变化”可以读取最终状态；“订单 42 已创建”和“订单 42 已取消”若需要逐事件审计，就不能随意折叠。

系统不会因两条广播发往同一进程就自动合并。Android 17 应用 delivery group 时还会核对发送 uid、user、group 匹配和 receiver 范围。`FLAG_RECEIVER_REPLACE_PENDING` 也只替换符合匹配条件的 pending 项。

Deferral 与 delivery group 解决不同问题：

| 配置 | 回答的问题 | 不提供什么 |
| --- | --- | --- |
| `DEFERRAL_POLICY_UNTIL_ACTIVE` | 目标何时适合接收 | 不去重 |
| `DELIVERY_GROUP_POLICY_MOST_RECENT` | 同组积压保留哪一条 | 不保证立即投递 |
| `FLAG_RECEIVER_REPLACE_PENDING` | 匹配 pending 项能否被新项替换 | 不替换任意同 action 广播 |

API 与语义见 [`BroadcastOptions`](https://developer.android.com/reference/android/app/BroadcastOptions)。

## 7. manifest、动态注册与 exported 标志

### 7.1 Android 8 的隐式广播限制仍适用于 Android 17

面向 API 26 及以上的应用，不能在 manifest 中声明大多数面向全系统的 implicit broadcast receiver。平台保留一组例外，例如 boot、部分存储介质、SMS 等具有明确系统语义的广播。

这项限制不表示“所有系统广播仍可静态注册”。接入前应查询具体 action 的 API 文档与 [implicit broadcast exceptions](https://developer.android.com/develop/background-work/background-tasks/broadcasts/broadcast-exceptions)。

选择 receiver 类型时按生命周期判断：

| 需求 | 合适方式 |
| --- | --- |
| 进程不存在时仍需接收，且 action 允许 manifest 注册 | manifest receiver |
| 只在页面可见或服务存活时关注 | 按生命周期动态注册 |
| 只在同一进程分发状态 | 回调、`StateFlow`/`SharedFlow` |
| 已知跨进程服务，需要请求或结果 | bound service/AIDL |

Manifest receiver 能拉起进程，代价可能包含完整应用初始化。动态 receiver 只在注册进程存活时存在，减少无意义冷启动，但它并不绕过 system_server。

### 7.2 `RECEIVER_NOT_EXPORTED` 是身份边界

面向 Android 14 的应用动态注册非纯 protected system broadcast 时，要显式选择 `RECEIVER_EXPORTED` 或 `RECEIVER_NOT_EXPORTED`。`RECEIVER_NOT_EXPORTED` 限制外部身份发送，仍然要在 AMS 注册、匹配并通过广播分发。

所以它不能作为“本地广播优化开关”。同进程事件若不需要系统参与，直接调用或 Flow 更节省，也更容易表达生命周期。

监听来自 Bluetooth、telephony 等高权限系统应用的广播时，官方文档提示这些发送者不一定使用 system UID；若业务要接收完整系统广播集合，应根据 action 文档选择 `RECEIVER_EXPORTED` 并配合权限与 action 校验。

### 7.3 receiver 仍要验证 action、来源和数据

IntentFilter 只是候选匹配条件，显式 Intent 可以绕开常规 filter 选择。`onReceive()` 应：

- 只接受已知 action；
- 验证必需 extras、URI scheme/authority 与长度；
- 对跨应用协议使用 signature permission 或可验证身份；
- 不从不可信 extras 直接构造文件路径、类名或命令；
- 把大数据放到受权限保护的 provider/file，广播只传引用。

安全检查也能保护性能。攻击者若能反复发送昂贵事件，会放大进程启动、I/O 和队列成本。

## 8. sticky broadcast 的精确边界

应用侧 sticky broadcast API 自 API 21 起废弃。Android 17 仍保留系统实现和若干系统 sticky action，兼容代码可能通过 `registerReceiver(null, filter)` 查询当前状态。

`BroadcastController` 的存储结构按 userId、action 和 Intent `filterEquals()` 组织。发送一条 sticky 时：

1. 调用方必须具备 `BROADCAST_STICKY` 权限；
2. Intent 不能指定 component，也不能附带 receiver permission；
3. 同 user/action 且 `filterEquals()` 的旧值被替换；
4. 同 action 但 data/type/categories 不同的记录可以并存；
5. 新注册 receiver 只遍历其 filter action 对应的 sticky 列表，再执行完整匹配。

“同 action 永远只有一个值”和“每次注册扫描所有 sticky × 所有 filter”都过度简化。准确的成本取决于 filter action 数，以及每个 action 下可匹配 sticky 的数量。

应用自定义状态不应再依赖 sticky broadcast：

| 状态范围 | 建议 |
| --- | --- |
| 同进程可观察状态 | `StateFlow`、生命周期感知回调 |
| 跨进程权威数据 | ContentProvider/bound service 保存状态，通知只做失效提示 |
| 需要持久化与恢复 | 数据库、DataStore 或服务端状态，按对应多进程能力设计 |
| 已有系统 sticky action | 按 action 文档读取，不自行重发 |

源码可查阅 [`BroadcastController.mStickyBroadcasts`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/am/BroadcastController.java)。

## 9. IPC 与任务机制怎样选择

没有一种 IPC 在所有维度都更快。应按通信拓扑、结果、可靠性和进程生命周期选择。

| 需求 | 推荐机制 | 选择理由 | 主要代价 |
| --- | --- | --- | --- |
| 同进程状态观察 | 回调、Flow | 无 system_server 与 Binder | 要管理订阅生命周期 |
| 已知服务的请求/响应 | AIDL/bound service | 接口明确，可同步或异步返回，可做背压 | 绑定、线程池、死亡通知 |
| 单向点对点消息 | oneway AIDL、Messenger | 目标明确，可自行定义队列 | 仍需处理积压与进程死亡 |
| 跨进程数据查询 | ContentProvider | 数据与权限模型清楚，支持 observer | 查询和序列化成本 |
| 一对多、接收者集合未知 | Broadcast | 系统负责发现与生命周期策略 | 时延无保证，可能冷启动多个进程 |
| 延迟、约束、需重试的任务 | WorkManager/JobScheduler | 具备持久化与系统约束 | 不适合即时 RPC |

Broadcast 适合“状态已变化，请自行读取”。AIDL 适合“执行请求并返回结果”。ContentObserver 适合“某个 URI 的权威数据失效”。WorkManager 适合“这项工作要在满足条件时可靠执行”。把这些语义混在一条 broadcast 中，往往会同时失去低延迟、可靠性和可观测性。

更完整的比较见 [§1.17 IPC 全景](../../part1-fundamentals/ch01-architecture/17-ipc-panorama.md)。

## 10. BOOT_COMPLETED 与 PACKAGE_* 的性能处理

### 10.1 BOOT_COMPLETED

Manifest receiver 使应用能在进程不存在时接收 boot 广播，也会把进程启动和 Application 初始化带入系统启动后的资源竞争。应用应让 `onReceive()` 只完成：

- 校验 direct boot/user unlocked 状态；
- 检查任务是否已经安排，保证幂等；
- 向 JobScheduler/WorkManager 提交必要工作；
- 快速返回。

不要在 receiver 中同步打开大型数据库、扫描目录、初始化全部 SDK 或发网络请求。系统可能按后台限制延后部分应用的 boot 广播，设备也可能在启动阶段负载很高，因此不能把“收到 BOOT_COMPLETED 的时刻”当成严格业务时钟。

### 10.2 PACKAGE_ADDED / REPLACED / CHANGED

Package 广播可能在安装、更新和组件变化期间连续出现。Android 17 的 per-process queue 能让同一目标进程在 running 时段连续处理多项，却仍会对每个 receiver 分别调用 `scheduleReceiver()` 或 `scheduleRegisteredReceiver()`。

所以“同进程 package 广播自动合成一次 Binder IPC”没有源码依据。业务只关心最终包状态时，可使用 delivery group、`FLAG_RECEIVER_REPLACE_PENDING` 或接收后按包名去重；需要完整审计时，应逐事件持久化。

## 11. 应用侧测量

### 11.1 同一启动周期可用 elapsed realtime 对齐

`SystemClock.elapsedRealtimeNanos()` 在同一设备的进程间共享开机时间基准。自有发送方与接收方可以把发送时间放进受权限保护的 Intent，分开记录：

- `send_call_duration`：`sendBroadcast()` 调用耗时；
- `dispatch_delay_app`：发送前到 `onReceive()` 入口；
- `receiver_sync_duration`：`onReceive()` 同步部分；
- `receiver_finish_delay`：入口到 `PendingResult.finish()`；
- `business_completion_delay`：业务结果可用时刻。

下面的代码展示发送与接收两个测点：

```kotlin
private const val EXTRA_SENT_NS = "sent_elapsed_ns"

fun sendMeasuredBroadcast(
    context: Context,
    intent: Intent,
) {
    val sentNs = SystemClock.elapsedRealtimeNanos()
    intent.putExtra(EXTRA_SENT_NS, sentNs)

    val callStartNs = SystemClock.elapsedRealtimeNanos()
    context.sendBroadcast(intent)
    val callEndNs = SystemClock.elapsedRealtimeNanos()

    recordSendCallDuration(callEndNs - callStartNs)
}

class MeasuredReceiver : BroadcastReceiver() {
    override fun onReceive(
        context: Context,
        intent: Intent,
    ) {
        val receiveNs = SystemClock.elapsedRealtimeNanos()
        val sentNs = intent.getLongExtra(
            EXTRA_SENT_NS,
            -1L,
        )
        if (sentNs in 0..receiveNs) {
            recordAppDispatchDelay(receiveNs - sentNs)
        }

        handleSmallEvent(intent)
    }
}
```

extra 来自发送方，只有在自有包或签名权限协议中才能作为可信测点。公共广播的发送时间可能缺失或被伪造，应以 system_server trace 为准。

端到端指标要按 receiver 类型、warm/cached/cold 进程、normal/ordered 和 foreground flag 分组。混在一起计算平均值会掩盖冷启动与 cached 延迟。

### 11.2 Android 17 的 dumpsys 与常量查询

下面的命令用于保存队列快照、历史统计和设备当前配置：

```bash
adb shell dumpsys activity broadcasts
adb shell dumpsys activity broadcast-stats

adb shell cmd activity get-broadcast-constant \
  bcast_max_running_process_queues
adb shell cmd activity get-broadcast-constant \
  bcast_delay_normal_millis
adb shell cmd activity get-broadcast-constant \
  bcast_delay_cached_millis
adb shell cmd activity get-broadcast-constant \
  bcast_timeout
```

`dumpsys activity broadcasts` 会输出 process queue、pending/active、runnableAt 原因、history 和前后台常量。`get-broadcast-constant bcast_timeout` 读取的是前台常量实例；后台 60 秒基准及设备覆盖值要结合完整 dump 核对。

EventLog 中可用的丢弃事件是 `am_broadcast_discard_filter` 和 `am_broadcast_discard_app`。Android 17 的 `EventLogTags.logtags` 没有 `am_broadcast_reschedule`，排障脚本不要依赖这个不存在的 tag。

### 11.3 Perfetto 区分排队与执行

Android 17 的 `BroadcastQueueImpl` 在 Perfetto SDK tracing v3 开启时，可以向 `broadcasts` category 写入 `broadcast_delivered` instant event。结构化字段包括：

- action、sender/receiver uid 与 pid；
- manifest/runtime receiver 类型；
- warm/cold process start 类型；
- `dispatch_delay_ms` 与 `finish_delay_ms`；
- Intent flags、receiver priority 和 delivery group policy。

`dispatch_delay_ms` 主要反映入队到 schedule 的等待，包含进程准备影响；`finish_delay_ms` 反映 schedule 到终态。无序动态 receiver 采用 assumed-delivered 时，finish 数据只表示系统已经提交，不能当成 `onReceive()` 执行完成。

目标设备没有该 category/event 时，结合 `am_proc_start`、Binder、sched 和应用主线程 slice 还原路径。SQL 前先检查 trace 的 `slice`/`args` 实际字段，不要假设所有构建都打开同一 feature flag。通用查询方法见 [§13.10 Perfetto SQL](../../part3-tools/ch13-perfetto/10-perfetto-sql-cookbook.md)。

## 12. 广播 ANR 的排查顺序

广播 ANR 到达后，按以下顺序缩小范围：

1. 从 ANR `TimeoutRecord` 确认 action、接收包和 receiver 类；
2. 判断 receiver 是 manifest、ordered，还是需要完成回执的动态 receiver；
3. 检查 Intent 是否带 `FLAG_RECEIVER_FOREGROUND`；
4. 在 trace 中找到 schedule 时刻，区分此前 dispatch delay 与此后 finish delay；
5. 检查主线程是在执行 receiver、等待锁、Binder、I/O，还是被更早消息阻塞；
6. 搜索 `goAsync()` 的每一条退出路径，确认 `finish()` 恰好调用一次；
7. 核对 coroutine/executor 是否饱和、取消或拒绝任务；
8. 若进程由广播冷启动，分开审阅 Application/ContentProvider 初始化；
9. 对 ordered broadcast，检查当前 receiver 前后的依赖与 result 传递；
10. 修复后同时回归 receiver 时长和端到端 P50/P90/P99。

广播超时的系统判定与 ANR 文件分析见 [§9.2 ANR 类型与触发条件](../ch09-anr/02-anr-types.md)。企业侧归档与聚合见 [§9.11 ANR 监控平台](../ch09-anr/9.11-enterprise-anr-monitoring-platform-design.md)。

## 13. 版本边界

| Android 版本 | 主要影响 |
| --- | --- |
| Android 14 / API 34 | cached app 广播可延后；动态 receiver exported flag 要求；公开 deferral 与 delivery group |
| Android 15 / API 35 | 进程级队列继续使用 `BroadcastQueueModernImpl` 类名 |
| Android 16 / API 36 | 实现类更名为 `BroadcastQueueImpl`；跨进程 receiver priority 不再保证 |
| Android 17 / API 37 | 源码以单个 `BroadcastQueueImpl`、per-process queue 和结构化 broadcast trace 为准 |

Android 17 上可保留六条工程规则：

- `sendBroadcast()` 同步完成 AMS 请求，但不等待接收者；
- normal broadcast 没有 receiver 完成依赖，执行并发仍受系统和目标线程约束；
- ordered broadcast 会把每个 receiver 的等待时间带给后继；
- 无序动态 receiver 可能被 assumed-delivered，系统完成不等于应用回调结束；
- `goAsync()` 不增加无限时间，长任务要交给有持久化或明确生命周期的机制；
- cached 投递、去重和安全导出是三组独立策略，不能用一个开关代替另两个。

## 参考资料

- [Broadcasts overview](https://developer.android.com/develop/background-work/background-tasks/broadcasts)
- [BroadcastReceiver API](https://developer.android.com/reference/android/content/BroadcastReceiver)
- [BroadcastOptions API](https://developer.android.com/reference/android/app/BroadcastOptions)
- [Implicit broadcast exceptions](https://developer.android.com/develop/background-work/background-tasks/broadcasts/broadcast-exceptions)
- [AOSP Android 17 BroadcastQueue design](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/am/BroadcastQueue.md)
- [AOSP Android 17 `BroadcastQueueImpl`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/am/BroadcastQueueImpl.java)
- [AOSP Android 17 `BroadcastProcessQueue`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/am/BroadcastProcessQueue.java)
- [AOSP Android 17 `BroadcastConstants`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/am/BroadcastConstants.java)

## 交叉引用

- [§1.33 Android 17 BroadcastQueue 调度与性能边界](../../part1-fundamentals/ch01-architecture/33-broadcastqueue-scheduling-performance.md)
- [§1.17 IPC 全景与性能选型](../../part1-fundamentals/ch01-architecture/17-ipc-panorama.md)
- [§9.2 ANR 类型与触发条件](../ch09-anr/02-anr-types.md)
- [§9.11 企业级 ANR 监控平台](../ch09-anr/9.11-enterprise-anr-monitoring-platform-design.md)
- [§13.10 Perfetto SQL 性能分析](../../part3-tools/ch13-perfetto/10-perfetto-sql-cookbook.md)
