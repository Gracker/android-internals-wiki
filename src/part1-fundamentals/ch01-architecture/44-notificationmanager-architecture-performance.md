---
title: "Android 17 NotificationManager 架构与性能优化"
chapter: "1.44"
section: "1.44"
status: ready-for-review
applicable_versions: "Android 13 (API 33) - Android 17 (API 37)"
last_verified: "2026-07-25"
last_verified_against: "AOSP android-17.0.0_r1"
confidence: high
sources:
  - type: aosp
    path: "frameworks/base/services/java/com/android/server/SystemServer.java"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/notification/NotificationManagerService.java"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/notification/NotificationRecord.java"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/notification/NotificationUsageStats.java"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/notification/PreferencesHelper.java"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/notification/RankingHelper.java"
  - type: aosp
    path: "frameworks/base/core/java/android/app/NotificationManager.java"
  - type: aosp
    path: "frameworks/base/core/java/android/app/Notification.java"
  - type: aosp
    path: "frameworks/base/core/java/android/app/INotificationManager.aidl"
  - type: aosp
    path: "frameworks/base/core/java/android/app/PendingIntent.java"
  - type: aosp
    path: "frameworks/base/core/java/android/service/notification/INotificationListener.aidl"
  - type: aosp
    path: "frameworks/base/core/java/android/service/notification/NotificationListenerService.java"
  - type: aosp
    path: "frameworks/base/core/java/android/widget/RemoteViews.java"
  - type: aosp
    path: "frameworks/base/core/res/res/values/config.xml"
  - type: aosp
    path: "frameworks/base/packages/SystemUI/src/com/android/systemui/statusbar/notification/collection/NotifPipeline.kt"
  - type: aosp
    path: "frameworks/base/packages/SystemUI/src/com/android/systemui/statusbar/notification/collection/NotifCollection.java"
  - type: aosp
    path: "frameworks/base/packages/SystemUI/src/com/android/systemui/statusbar/notification/row/NotificationRowContentBinderImpl.kt"
  - type: official
    path: "developer.android.com/develop/ui/views/notifications"
  - type: official
    path: "developer.android.com/develop/ui/views/notifications/live-update"
  - type: official
    path: "developer.android.com/develop/ui/views/notifications/metric-style"
  - type: official
    path: "developer.android.com/about/versions/17/summary"
  - type: official
    path: "developer.android.com/blog/posts/android-17-is-here"
  - type: official
    path: "developer.android.com/about/versions/16/features/progress-centric-notifications"
  - type: official
    path: "developer.android.com/develop/ui/compose/notifications/notification-permission"
  - type: official
    path: "developer.android.com/about/versions/14/behavior-changes-all"
  - type: official
    path: "developer.android.com/develop/background-work/services/fgs/timeout"
tags: [notification, system-service, binder, notification-channel, ranking, systemui, performance]
related_chapters: ["1.8", "1.38", "1.45", "4.11", "8.11", "9.6"]
---

# 1.44 Android 17 NotificationManager 架构与性能优化

`NotificationManager` 是应用访问通知系统的 SDK 入口类。通知从应用到屏幕要依次穿过三个职责边界：

1. 应用把 `Notification` 组装成可跨进程传输的数据；
2. `system_server` 中的 `NotificationManagerService`（下文简称 NMS）校验、入队、排序并通知监听器；
3. SystemUI 把系统通知快照转换为通知栏中的列表项和视图。

这三段的线程、状态和失败方式各不相同。`notify()` 返回，只能说明同步提交阶段已经结束；它不能证明通知已经入列，更不能证明 SystemUI 已经画出界面。

源码基线是 AOSP `android-17.0.0_r1`，公开 API 基线是 Android 17 / API 37。涉及 Binder 驱动的一般性说明以 common kernel `android17-6.18-2026-06_r6` 为准；通知权限、渠道、排序和限流都属于平台策略，不能从内核 Binder 代码推导。

性能优化实战和 ANR 案例分别见 §8.11 与 §9.6。以下结构模型可用于阅读源码、分析 trace 和解释故障。

## 进程边界与职责

```text
App process
  Notification.Builder
  NotificationManager
        │  INotificationManager（同步 Binder）
        ▼
system_server
  NotificationManagerService
    ├─ PreferencesHelper      渠道和包级偏好
    ├─ NotificationUsageStats 入队速率与使用统计
    ├─ RankingHelper          信号提取与全局排序
    ├─ ZenModeHelper          勿扰拦截
    ├─ NotificationAssistants 助手调整
    └─ NotificationListeners  监听器分发
        │  INotificationListener（oneway Binder）
        ├───────────────┐
        ▼               ▼
SystemUI process    其他 NotificationListenerService
  NotifCollection
  NotifPipeline
  NotificationRowBinderImpl
```

`NotificationManager` 不保存系统的通知列表。它在应用进程中完成客户端限流、图标和图片整理，然后调用 `INotificationManager`。NMS 保存权威通知记录；SystemUI 保存用于显示的副本，并允许 `lifetime extender` 组件为完成动画或交互而短暂保留已经从 NMS 撤回的通知。因此，NMS 列表与通知栏列表在短窗口内可以不同。

NMS 还会调用多个系统组件，但要区分本地服务调用和 Binder 调用：

| 组件 | 与通知发布相关的职责 |
| --- | --- |
| ActivityManager / `ActivityManagerInternal` | 处理 user、前台服务（FGS）通知策略、应用前台状态，以及让 `PendingIntent` 目标在受限后台环境中短暂获准执行的临时 allowlist |
| PackageManager | 解析发布包和 `ApplicationInfo`，检查包身份与权限 |
| `PermissionHelper` / AppOps | `POST_NOTIFICATIONS`、promoted notification（可被系统提升展示的通知）等授权状态 |
| `PreferencesHelper` | 渠道、包级重要性、用户锁定字段、通知圆点（badge）偏好 |
| `ShortcutHelper` | 会话通知的 shortcut 校验与缓存 |
| `ZenModeHelper` | 勿扰模式及自动规则 |
| `NotificationAttentionHelper` | 声音、振动、灯光和 heads-up（屏幕顶部悬浮提醒）相关决策 |

`NotificationUsageStats` 是 NMS 自己的统计类。它不是 `UsageStatsManager`，`getAppEnqueueRate()` 也不会查询 UsageStats 系统服务。混淆两者会误判通知更新被丢弃时的依赖关系。

## 一次 `notify()` 到底做了什么

### 应用进程：构建、整理与客户端限流

`NotificationManager.notify()` 最终进入 `notifyAsUser()`。发起 Binder 调用之前，Android 17 的客户端会依次完成：

- 用 `(user, package, tag, id)` 识别更新；
- 对“同一个通知且进度状态未改变”的高频更新执行以 5 次/秒为目标上限的客户端限流；
- 补充上下文字段和旧版 small icon；
- 调用 `Notification.reduceImageSizes()`；
- 通过 `Notification.Builder.maybeCloneStrippedForDelivery()` 去掉可由接收端重建的冗余内容；
- 把 `Notification` 序列化后执行同步 Binder 调用。

下面是 Android 17 客户端路径的关键调用关系，省略了日志和异常转换：

```java
if (discardNotify(user, pkg, tag, id, notification)) {
    return;
}
service.enqueueNotificationWithTag(
        pkg, opPkg, tag, id, fixNotification(notification), userId);

private Notification fixNotification(Notification notification) {
    Notification.addFieldsFromContext(mContext, notification);
    fixLegacySmallIcon(notification, pkg);
    notification.reduceImageSizes(mContext);
    return Builder.maybeCloneStrippedForDelivery(notification);
}
```

这段代码说明两件事。第一，`notify()` 可能在 App 侧直接丢弃一次高频更新，连 Binder 都不会发生。第二，大图缩放、对象 clone 和 Parcel write 都计入 calling thread 时间。把大图 decode、文本拼装和 `Notification.Builder.build()` 全放在 main thread，会先造成 App 自身卡顿，随后才轮到 NMS。

### 同步 Binder 阶段：远不止“快速入队”

`INotificationManager.enqueueNotificationWithTag()` 是同步接口。应用线程要等 NMS 的 Binder 方法返回。Android 17 中，返回前已经可能执行以下工作：

- 处理目标 user，验证调用 UID 是否可以代表目标包发布；
- 应用 FGS 通知策略，修正不允许由应用设置的 flag；
- 读取 `ApplicationInfo`，校验 full-screen intent（全屏通知意图）等权限；
- 检查自定义 `RemoteViews`（可跨进程应用的受限视图描述）的估算内存；
- 根据 channel ID 从 `PreferencesHelper` 读取渠道，渠道不存在时拒绝发布；
- 创建 `StatusBarNotification` 和 `NotificationRecord`；
- 执行速率、数量、snooze（稍后提醒）、包状态等淘汰检查；
- 为通知内的 PendingIntent 设置临时 allowlist；
- 查询应用前台状态；
- 完成这些检查后才执行 `mHandler.post(new EnqueueNotificationRunnable(...))`。

因此，`notify()` 的同步耗时可能来自客户端构建与 Parcel、NMS Binder 线程上的验证、包管理查询、FGS 策略或 `mNotificationLock` 竞争。SystemUI 对通知布局执行 inflate（从布局创建 View）不在这段等待里。

### 异步阶段：enqueue、assistant、post

NMS 把同一条通知的异步处理分成两步：

1. `EnqueueNotificationRunnable` 把记录放进 `mEnqueuedNotifications`，继承旧记录的 ranking（排序）信息，处理稍后提醒、分组和 instance ID（本次记录的实例标识），并把新通知交给 Notification Assistant（通知助手）；
2. `PostNotificationRunnable` 再检查包和渠道是否被禁用，把记录写入 `mNotificationList` 与 `mNotificationsByKey`，提取信号、排序、决定提醒效果，并准备监听器回调，完成正式发布（post）。

如果启用了 Notification Assistant，NMS 会用 `DELAY_FOR_ASSISTANT_TIME` 延后 `PostNotificationRunnable`，为助手提交 `Adjustment` 留出时间。这个延迟属于设计行为，不能直接判定为线程阻塞。

`NotificationRecord` 包含 `StatusBarNotification`、渠道、最终 importance（重要性级别）、group、ranking time、assistant 调整和统计信息。NMS 同时维护：

| 结构 | 含义 |
| --- | --- |
| `mEnqueuedNotifications` | 已通过同步校验、尚未完成 post 的记录 |
| `mNotificationList` | 已发布记录，按 NMS 全局顺序保存 |
| `mNotificationsByKey` | 以通知 key 查找当前记录 |
| `mSummaryByGroupKey` | group summary 的快速索引 |

这些容器并非各自独立的数据副本；同一记录可能同时出现在列表和索引中。源码中的 `mNotificationLock` 保护跨结构一致性。诊断“更新丢失”时，要先分清记录仍在 enqueued、已被淘汰，还是 post 后尚未到达 SystemUI。

## NMS 的线程模型

### `mHandler` 绑定 `system_server` 主 Looper

Android 17 的 `NotificationManagerService.onStart()` 中有如下初始化：

```java
mRankingThread.start();
WorkerHandler handler = new WorkerHandler(Looper.myLooper());

HandlerThread broadcastsThread = new HandlerThread("NMS Broadcasts");
broadcastsThread.start();

init(
    handler,
    new RankingHandlerWorker(mRankingThread.getLooper()),
    new Handler(broadcastsThread.getLooper()),
    ...
);
```

`SystemServer` 在主线程依次启动服务，随后才调用 `Looper.loop()`。所以这里的 `Looper.myLooper()` 是 `system_server` 主 Looper。常见的“NotificationManager 专用 `ServiceThread`”模型不适用于这个版本。

`WorkerHandler` 上会运行 enqueue、post、listener dispatch runnable 以及多类 NMS 消息。耗时任务会与其他 `system_server` 主线程工作相互影响。NMS 仍有两个专用线程：

- `ranker`：处理 `MESSAGE_RECONSIDER_RANKING` 与 `MESSAGE_RANKING_SORT`；
- `NMS Broadcasts`：承载 NMS 的广播相关工作。

初次 post 中的 `mRankingHelper.extractSignals()` 和 `mRankingHelper.sort()` 仍由 `PostNotificationRunnable` 所在线程执行。看到名为 `ranker` 的线程，不能据此认定所有排序都已从主线程移走。

### 排序类是 `RankingHelper`

Android 17 源码中没有 `NotificationRankerService.java`。排序由 NMS 持有的 `RankingHelper` 完成：

1. `extractSignals()` 依次调用 `NotificationSignalExtractor.process()`；
2. extractor 可以返回 `RankingReconsideration`，交给 `ranker` 的 Handler 延后处理；
3. `sort()` 先用 `NotificationTimeComparator` 排预排序结果；
4. 为每条记录计算分组代理与全局排序键；
5. 再用 final comparator 完成全局排序。

NMS 的全局顺序也不是屏幕上的最终顺序。SystemUI 收到 `RankingMap` 后，还会按自己的 section、filter、group 与 comparator 构建 shade list。两层排序解决的问题不同：NMS 提供系统权威 ranking，SystemUI 决定当前界面如何组织和显示。

## 两级更新限流与数量上限

### 客户端和服务端都可能丢更新

Android 17 对高频更新设置了两级保护，但两者的作用域和算法不同：

| 位置 | 默认阈值 | 触发条件 |
| --- | ---: | --- |
| 应用进程的 `NotificationManager` 实例 | 目标上限 5 次/秒 | 同一 `(user, package, tag, id)` 已知已入队，且新旧 `getProgressState()` 相同 |
| NMS `checkDisqualifyingFeatures()` | 每包目标上限 5 次/秒 | 已有同 key 的已发布或待发布记录，进度状态相同，且不是系统自动分组记录（autogroup） |

`getProgressState()` 只有 `NONE`、`ONGOING`、`COMPLETE` 三种内部状态。进度从 41% 变为 42% 时仍是 `ONGOING`，所以持续刷新百分比会进入限流；从 `ONGOING` 变为 `COMPLETE` 的关键更新可以通过“状态改变”条件。这里的豁免依据是状态变化，不会对每个进度值做特殊判断。

客户端的 `mUpdateRateLimiter` 是 `NotificationManager` 的实例字段，同一实例中的合格更新共用一个 `RateEstimator`；通知 key 用于判断这次调用是否属于更新并记录拒绝日志，不会为每个 key 建立独立的 5 次/秒计数桶。`eventExceedsRate()` 比较估算输出速率与 `5f`，所以它也不是按自然秒清零的固定窗口计数器。

服务端判断使用 `NotificationUsageStats.getAppEnqueueRate(pkg)`，阈值来自 `Settings.Global.MAX_NOTIFICATION_ENQUEUE_RATE`，AOSP 默认 `5f`。这是 NMS 的包级速率估算。超限时记录日志和统计后返回 `false`。应用通常收不到异常或成功回调，因此业务层不能把每次 `notify()` 当成可靠消息投递。

合适的处理方式是按通知 key 合并状态，只发送用户能看见的变化；完成、失败、暂停等状态切换立即发送，中间进度按时间窗口采样。

### 每包 50 条并非无条件配额

`MAX_PACKAGE_NOTIFICATIONS` 在 AOSP Android 17 中为 50。NMS 统计同包、同 user 已发布和正在入队的记录，排除本次更新所替换的 `(id, tag)`。达到上限后，新记录会被拒绝。

这个上限的源码条件还排除了系统或电话进程、已注册 listener 包，以及 FGS、user-initiated job 和系统聚合 group 的特定记录。应用不应利用这些例外堆积通知；它们用于防止关键任务被普通通知配额误伤。

## NotificationChannel：配置的所有权比 API 调用更重要

### 创建和更新规则

`NotificationChannel` 从 API 26 开始就是发布通知的必要路由。渠道 ID 是持久身份，不应把版本号、语言或临时业务状态编码进 ID。

`createNotificationChannel()` 可以重复调用，但重复调用不会覆盖全部配置。Android 17 的 `PreferencesHelper.createNotificationChannel()` 对应用侧更新采用以下规则：

- 可以更新 name、description 和 blockable 等少数字段；
- 现有渠道尚未加入 group 时，可以补上 group；已加入后不能由应用迁移；
- 用户从未修改该渠道时，应用可以降低 importance；
- 应用不能提高现有渠道的 importance；
- 用户在设置中可以提高或降低 importance，应用不能覆盖用户选择；
- sound、vibration 等多数行为在首次创建后由系统保存，后续使用同一 ID 创建不会重置。

“应用不能提高渠道 importance”与“用户不能提高 importance”是两件事。后一个说法是错误的。用户拥有渠道配置的最终决定权。

### 删除留下标记，重建会恢复

删除渠道时，`PreferencesHelper` 把 `isDeleted` 设为 `true` 并记录删除时间，没有立即移除对象。应用再次创建同 ID 渠道时，系统会把它标回可用，并保留原有设置。Android SDK 对 `deleteNotificationChannel()` 的说明也明确写出了这项行为。

可以把状态理解为：

```text
不存在
  └─ create(id) ──> 活跃
                      ├─ 用户修改 ──> 活跃（带 user-locked fields）
                      └─ delete ──────> 已删除 tombstone
                                         └─ create(同一 id) ──> 恢复原配置
```

这项设计防止应用用“删掉再创建”绕过用户选择。需要一套全新的声音、重要性或用途时，应设计新的稳定 channel ID，并向用户解释迁移原因。

### 渠道不存在时不会替现代应用兜底

通知中的 channel ID 随 `Notification` 一起传给 NMS。NMS 在同步提交阶段查询 `PreferencesHelper`；普通应用发布到不存在的渠道时，记录会被拒绝，并在日志中出现 `No Channel found`。它不会把 API 26 及以上应用的错误 channel 自动改成另一个默认渠道。

`notify()` 也不会先额外发起一次“渠道是否存在”的客户端查询。应用主动调用 `getNotificationChannel()` 才是查询 API。创建多个渠道时，应使用 `createNotificationChannels(List)`，它把列表装进一次 Binder 调用；在循环中逐个调用会产生多次往返。

### importance 是输入，不是界面承诺

渠道 importance 会参与提醒和显示决策，但 `IMPORTANCE_HIGH` 不保证每次都出现 heads-up。勿扰模式、用户设置、设备状态、通知内容、近期提醒频率和 OEM 策略都会改变结果。

高 importance 通知一旦满足 heads-up 条件，SystemUI 还要更新通知栏面板（shade）、heads-up 容器、动画和相关图标。把普通状态更新都放进高 importance 渠道，会同时增加打扰和 UI 工作量。性能优化不能以提高 importance 为手段。

## NMS 到监听器：oneway 只消除远端返回等待

### 分发准备仍在 NMS 内完成

NMS 排序后调用 `NotificationListeners.notifyPostedLocked()`。它会在持有 `mNotificationLock` 的上下文中为每个可见 listener（通知监听服务）：

- 判断 user/profile 和敏感内容的可见性；
- 按 listener 的 trim 级别准备 `StatusBarNotification`；trim 决定发送完整通知还是删减内容后的轻量版本；
- 构造对应的 `NotificationRankingUpdate`；
- 更新 URI 授权与包可见性；
- 生成一个稍后执行回调的 `Runnable` 任务。

这些任务再被投递到 `mHandler`，随后调用 `INotificationListener.onNotificationPosted()`。AIDL 将接口声明为 `oneway`（异步单向调用），NMS 不等待远端 listener 方法执行完毕。

`oneway` 不代表零成本。NMS 仍要创建快照、写 Parcel、把事务放进 Binder 队列；远端进程不消费时，异步队列也可能形成压力。远端业务回调耗时不计入应用最初 `notify()` 的同步等待。

普通 `NotificationListenerService` 从 Android 7.0 起在服务主线程收到回调。监听器应只做轻量索引和任务转交，不能在 `onNotificationPosted()` 中同步访问网络、解析大图或遍历全部历史通知。

## SystemUI：现代通知管线

Android 17 已经使用 `NotifCollection` 与 `NotifPipeline`，不应再用旧的 `NotificationEntryManager` 解释主路径：

```text
NotificationListener callback
  └─ NotifCollection.onNotificationPosted()       [SystemUI main]
       ├─ 新建或更新 NotificationEntry
       ├─ 应用 RankingMap
       └─ dispatchEventsAndRebuildList()
            └─ NotifPipeline / ShadeListBuilder
                 ├─ pre-group filters
                 ├─ grouping / promoters
                 ├─ sections / comparators
                 ├─ finalize filters
                 └─ render list
                      └─ NotificationRowBinderImpl
                           ├─ RowInflaterTask
                           └─ NotificationRowContentBinderImpl
```

`NotifCollection.onNotificationPosted()` 有 `Assert.isMainThread()`。列表事件、ranking 应用和重建请求会经过 SystemUI 主线程。视图内容随后由 `NotificationRowContentBinderImpl` 异步构建 `RemoteViews` 并 apply 到 row；主线程仍需接收结果、替换 view、执行测量与 layout 并提交绘制。

图中的 pre-group filter 会在分组前排除记录，promoter 可把子通知提升为顶层条目，section 与 comparator 决定分区和区内顺序，finalize filter 在列表输出前再做最后过滤。这里的 row 指一条通知对应的界面项，apply 指把 `RemoteViews` 中记录的操作应用到该界面项。

因此，分析通知 UI 卡顿时至少要同时看：

- SystemUI 主线程是否积压 listener callback 和 shade list rebuild；
- notification inflation executor（通知视图构建线程池）是否被大图、复杂 `RemoteViews` 或大量 row 占满；
- 主线程接收 apply 结果后是否发生密集 layout；
- RenderThread/GPU 是否只是后续受到影响。

## `RemoteViews`、系统模板与重用

### 传输的是布局描述和操作

自定义通知不会把应用进程中的 View 对象交给 SystemUI。`RemoteViews` 携带包信息、layout ID、受限操作和资源引用，SystemUI 使用目标包的资源上下文创建视图，再执行这些操作。

```text
App                                      SystemUI
RemoteViews(package, layout, actions)
  └─ Notification / Parcel ────────────> package context
                                           ├─ inflate(layout)
                                           └─ apply(actions)
```

可调用的方法受 `RemoteViews` 规则限制。SystemUI 不会加载并运行应用自定义 View 类的任意代码。这个限制兼顾安全、跨进程稳定性和版本兼容。

系统样式也会在 SystemUI 中恢复 `Notification.Builder` 并生成平台模板 `RemoteViews`。这类布局和操作由框架控制，兼容性、内存约束和不同设备形态更可预测。能用 `BigTextStyle`、`MessagingStyle`、`CallStyle`、`ProgressStyle` 或 `MetricStyle` 表达的内容，优先使用系统模板。

### `reapply` 的条件

Android 17 的 `NotificationRowContentBinderImpl.canReapplyRemoteView()` 在以下条件满足时允许复用旧 view：

- 新旧 `RemoteViews` 都存在；
- package 相同；
- layout ID 相同；
- 旧 `RemoteViews` 没有 `FLAG_REAPPLY_DISALLOWED`。

满足条件后可以执行 `reapply`，重新运行操作而不重新 inflate 根布局。它仍会处理文本、图片、点击动作和校验，不能视为无成本更新。改变自定义 layout ID 会失去这条重用路径。

### Android 17 的自定义视图内存约束

`NotificationManager.fixNotification()` 会先调用 `reduceImageSizes()`。NMS 的 `checkRemoteViews()` 随后用 `RemoteViews.estimateMemoryUsage()` 检查每个自定义 collapsed（折叠）、expanded（展开）、heads-up 和 public view（锁屏公开版本）。AOSP `android-17.0.0_r1` 的默认资源值为：

- 估算内存大于 2,000,000 bytes：写 warning；
- 估算内存达到 5,000,000 bytes：剥离该 `RemoteViews`。

这两个值是 framework resource，可被设备配置覆盖，不应作为应用可用预算。上面这一层发生在 NMS，检查的是 `RemoteViews` 传输对象的估算值；它无法完整反映 URI 或资源图片在 SystemUI 解码后的占用。

Android 17 还在 SystemUI 的 `NotificationCustomContentMemoryVerifier` 增加了第二层检查。`NotificationRowContentBinderImpl` apply 自定义视图后，验证器遍历其中的 `ImageView`：`BitmapDrawable` 按实际像素内存 `allocationByteCount` 计入，其他 Drawable（可绘制资源）按固有宽高乘以 4 估算。`CHECK_SIZE_OF_INFLATED_CUSTOM_VIEWS` 使用 `@EnabledAfter(BAKLAVA)`，所以从 target API 37 开始强制拒绝；目标版本较低的应用在同样超限时只收到迁移警告。这个检查针对展开后的 Drawable，因而覆盖了 URI 和资源图片未计入 Parcel 估算的情况。

应用应优先使用系统模板；确需自定义视图时，要在解码前限制图片尺寸，并为视图被 NMS 剥离或被 SystemUI 拒绝准备可接受的退化路径。AOSP 阈值适合用于理解源码和日志，不适合作为应用的图片预算。

共享 bitmap backing（多个对象共用的像素存储）只能减少部分重复拷贝，不能消除解码、缩放、Parcel 元数据、SystemUI 图片解析和 GPU 上传。大图通知的成本需要在应用、NMS、SystemUI 和渲染四段分别观察，详见 §9.6。

## PendingIntent 与通知点击响应

### 可变性（mutability）是安全与功能约束

通知把未来操作封装为系统持有的 `PendingIntent` token（操作凭据）。普通内容点击不需要接收方填入参数，应使用 immutable：

```java
PendingIntent contentIntent = PendingIntent.getActivity(
    context,
    requestCode,
    intent,
    PendingIntent.FLAG_IMMUTABLE | PendingIntent.FLAG_UPDATE_CURRENT);
```

`FLAG_IMMUTABLE` 用于防止其他进程改变封装的 Intent，不代表它天然比 mutable token 更快。通知内直接回复（inline reply）和气泡（bubble）需要系统填充远程输入或启动参数，必须按对应 API 要求使用 mutable；Android 17 的 NMS 会拒绝把 immutable `PendingIntent` 用于 bubble intent 或带 `RemoteInput` 的 action。

`FLAG_UPDATE_CURRENT` 表示匹配到已有 token 时更新创建者提供的 extras。它对 immutable token 同样有效，但不是通用性能开关。PendingIntent 的匹配依赖 Intent 的 action、data、type、component、categories 以及 request code 等身份字段；如果不同通知误用同一身份，后一次更新可能覆盖前一次点击携带的数据。

可以采用以下规则：

- 相同业务对象的通知更新：保持稳定的 request code 与 Intent 身份；
- 不同业务对象：用稳定且不冲突的 data URI 或 request code 区分；
- 无远端填充需求：`FLAG_IMMUTABLE`；
- inline reply、bubble 等明确要求可变：只在所需 PendingIntent 上使用 `FLAG_MUTABLE`；
- 更新结束或业务失效后，不再依赖旧 token；必要时用合适的取消策略清理。

### 点击响应延迟链路

用户点击后的主要步骤是：

1. SystemUI 处理点击、keyguard（锁屏与解锁验证）和通知收起策略；
2. `PendingIntent.send()` 进入 activity/task 管理；
3. 系统处理后台启动权限、user、task 与 Intent 路由；
4. 目标进程按当前状态复用、解冻或启动；
5. Activity 执行生命周期并提交首帧。

冷启动或 cached app（缓存进程）解冻没有可跨设备使用的固定毫秒数。它取决于存储、代码和资源量、设备负载、进程状态与首帧工作。诊断时应记录点击业务 ID，在 Activity 的 `onCreate()`、`onNewIntent()` 和首帧处添加 trace，再结合 `am_proc_start`、Binder 和调度事件定位。

通知点击应直接使用指向 Activity 的 PendingIntent。Android 12 起，应用不能依赖 notification trampoline（通知跳板），即“点击先启动 broadcast receiver/service，再由它启动 Activity”。直接目标也减少一次组件调度和一次应用内转交。

## 通知分组机制

### 分组决定语义和提醒方式

应用使用 `setGroup(groupKey)` 给相关通知稳定分组，并用一条采用相同 group key、设置 `setGroupSummary(true)` 的通知描述组摘要（summary）。`setSortKey()` 只控制组内相对顺序。

如果只希望摘要发声或振动，应在所有子通知上设置 `GROUP_ALERT_SUMMARY`。反过来，`GROUP_ALERT_CHILDREN` 会静音 summary。默认 `GROUP_ALERT_ALL` 可能让一批同时发布的通知连续提醒用户。

NMS 也会对未正确分组的多条通知执行自动聚合。自动 summary 是系统生成的记录，因此服务端更新限流会排除 `isAutogroup` 路径。自动分组的阈值、延迟和显示效果属于系统策略，应用不能把它当作稳定 API。

消息应用通常应使用 `MessagingStyle` 表达会话内容，再用 group 表达多个会话。不要为同一会话的每条消息创建一个永久通知；用稳定的 `(tag, id)` 更新会话通知，既符合用户预期，也能控制 NMS 和 SystemUI 的记录数量。

### 分组不会自动消除每条通知的成本

组内每个子通知（child）仍是独立的 `NotificationRecord` 和 `NotificationEntry`。它仍要经过权限、渠道、排序、listener fan-out（向多个监听器逐一分发）和 SystemUI collection（收集并维护通知条目）。SystemUI 是否提前 inflate 子项、保留哪些 row，还受当前管线、缓存和可见状态影响。不能承诺“折叠时只 inflate summary”或“NMS 批量排序同组记录”。

分组的可靠收益是减少通知栏的视觉散乱，并允许统一提醒策略。性能收益取决于 SystemUI 当时少渲染、少布局了多少可见内容。若源头仍保留几十条活跃 child，NMS 内存、ranking 和分发成本并未消失。

## 通知权限管理

### POST_NOTIFICATIONS 运行时权限

Android 13 / API 33 起，非豁免通知受 `POST_NOTIFICATIONS` 运行时权限控制。应用仍可以调用 `notify()`；NMS 会创建和检查记录，并在 post 阶段根据包权限与渠道状态决定是否抑制显示。“权限拒绝后通知完全不进入 NMS”的说法并不准确。

对普通通知，权限被拒绝时通常不会因为这项拒绝向 `notify()` 调用抛出异常，通知也不会进入通知栏。参数非法、包身份错误、危险 PendingIntent 或无效 FGS 通知仍可能抛异常，不能把 `notify()` 当成永不失败。

前台服务仍必须提供通知。用户拒绝通知权限后，前台服务任务可能仍出现在系统的 Active apps / Task Manager（活动应用管理）界面，但通知不会按普通方式出现在下拉通知面板（notification drawer）。媒体会话（media session）与满足条件的 self-managed call（由应用自行管理的通话）通知另有豁免边界，不能扩大成整个应用豁免。

### 渠道级可见性控制

`NotificationManager.areNotificationsEnabled()` 在 Android 17 检查调用应用的 `POST_NOTIFICATIONS` 状态。它只回答包级发布权限，不能替代渠道检查。需要决定某类通知是否值得构建时，还应读取对应 `NotificationChannel` 的有效 importance。

即使两个检查都允许，最终显示和提醒仍可能受勿扰、snooze、profile、设备策略、group、assistant 和当前界面策略影响。应用应把通知发布设计成尽力而为的用户界面更新，关键业务状态另存于可靠存储。

## 状态栏图标与 Launcher 通知圆点

### 状态栏图标不是“每包一个”

状态栏使用 `Notification.smallIcon` 生成图标；`largeIcon` 服务于通知内容或通知圆点（badge）的可选表现。Android 17 没有“同一个包最多显示一个状态栏图标”的通用规则。同一包的多条独立通知可以占据多个图标位置，最终可见数量由屏幕空间、优先级、静默图标设置和 SystemUI 策略共同决定。

`IMPORTANCE_LOW` 的 SDK 定义是可能出现在状态栏，但不产生声音式打扰；用户还可以选择隐藏 silent notification icons。不能用单一 importance 值推断图标一定显示或一定隐藏。

一次图标属性更新通常不是通知性能的主要部分。高频更新的问题来自整次 notification callback、ranking、shade list rebuild、内容 reapply 和可能的 layout，不能只估算一个 `ImageView.invalidate()`。

### Launcher Badge（通知圆点）

渠道的 `setShowBadge()` 决定该渠道是否允许出现在支持通知圆点（badging）的 Launcher；`Notification.Builder.setBadgeIconType()` 只向 Launcher 提供圆点图标类型建议。启动器或用户设置都可能忽略这些建议。

不同 Launcher 获取与聚合通知的实现并非公开 API 合同。应用只应设置渠道和通知元数据，不要假设“每次更新必然启动 Launcher 进程”，也不要用通知圆点作为可靠计数存储。未读数应由应用数据维护。

## 可复现的观测方法

### 用应用 trace 划出同步边界

AOSP NMS 没有稳定提供名为 `EnqueueNotificationRunnable` 或 `rankerSort` 的 Perfetto slice（带起止时间的区间事件）。直接用这些名字写 SQL，查询为空时无法区分“没有发生”和“源码没有埋点”。

应用可以在构建与提交两侧分别添加 trace。trace 名称只放阶段和短哈希，不写消息正文、账号或完整业务 ID：

```kotlin
Trace.beginSection("notif:build:$shortHash")
val notification = buildNotification(model)
Trace.endSection()

Trace.beginSection("notif:submit:$shortHash")
notificationManager.notify(TAG, notificationId, notification)
Trace.endSection()
```

`notif:submit` 的 duration（持续时间）覆盖客户端限流、`fixNotification()`、Parcel 和 NMS 同步 Binder 阶段。它不覆盖 enqueue runnable、assistant delay、listener callback 与 SystemUI 渲染。

采集 trace 时至少开启：

- 应用与 `system_server`、SystemUI 的 sched/thread state；
- Binder driver 事件；
- view、gfx、wm 和 am 相关数据源；
- 应用自定义的 atrace section。

在 Android 17 AOSP SystemUI 中，可见的源码 trace 名称包括：

- `NotifCollection.dispatchEventsAndRebuildList`
- `NotifCollection.dispatchEvents`
- `NotificationContentInflater.AsyncInflationTask#doInBackground`
- `NotificationContentInflater.createRemoteViews`
- `NotificationRowContentBinderImpl#apply`

下面的 SQL 只列出实际存在的应用和 SystemUI slice，不假设两者能凭时间自动一一对应：

```sql
SELECT
  ts / 1e6 AS ts_ms,
  dur / 1e6 AS dur_ms,
  name,
  track_id
FROM slice
WHERE name GLOB 'notif:*'
   OR name = 'NotifCollection.dispatchEventsAndRebuildList'
   OR name = 'NotifCollection.dispatchEvents'
   OR name = 'NotificationContentInflater.AsyncInflationTask#doInBackground'
   OR name = 'NotificationContentInflater.createRemoteViews'
   OR name = 'NotificationRowContentBinderImpl#apply'
ORDER BY ts;
```

若需要单条通知的端到端时间，应在可控测试版本中给应用、测试 listener 或 SystemUI 增加同一个无敏感信息的 correlation token（跨阶段关联标识）。仅用“紧跟在 `notify()` 后的第一个 inflate”做关联，在并发通知环境中很容易选错对象。

### `dumpsys`、shell 与日志各回答什么

先确认通知有没有进入 NMS：

```bash
adb shell dumpsys notification --package com.example.app
adb shell cmd notification list
adb shell cmd notification get '<notification-key>'
```

`dumpsys notification` 能看到活跃、enqueued、snoozed、渠道、listener、assistant、包级统计和 NMS 配置。`--noredact` 和 `--reveal` 会暴露通知内容，只能在授权测试设备上使用。

自定义视图被剥离时，可检查 `RemoteViews` 统计与日志：

```bash
adb shell dumpsys notification --remote-view-stats 0
adb logcat -s NotificationManager NotificationService \
  NotifCollection NotifContentInflater
```

常见判读顺序：

1. 应用 `notif:submit` 很长：分解 builder、图片、Parcel 和同步 Binder 等待；
2. NMS 没有记录：查客户端限流、channel、权限、50 条上限和 NMS 日志；
3. NMS 已 post、SystemUI 尚未收到：查 listener dispatch、Binder 队列和 SystemUI 进程状态；
4. `NotifCollection` 收到但 row 很晚：查通知栏列表重建、展开执行器和 shade list rebuild、inflation executor、RemoteViews apply；
5. row 已 apply、首帧仍晚：查 SystemUI 主线程 layout、RenderThread 和 GPU。

## Android 17 / API 37 新能力

### `Notification.MetricStyle`

Android 17 新增 `MetricStyle`，用于健康、计时、天气和出行等需要同时展示少量动态指标的场景。平台模板最多显示三个 metric（指标项）；每个 `Notification.Metric` 由 label（标签）、`MetricValue` 和可选 semantic style（语义样式）组成。

`MetricValue` 提供固定整数、浮点、文本、日期、时间和计时差等类型。计时器优先使用 `TimeDifference`，系统可以在显示端推进时间，应用无需每秒调用 `notify()`。

下面的示例用系统模板显示步数和心率，并把步数设为 `status chip`（状态栏中的紧凑展示区域）首选指标：

```kotlin
@RequiresApi(37)
fun buildFitnessNotification(context: Context): Notification {
    val style = Notification.MetricStyle()
        .addMetric(
            Notification.Metric(
                Notification.Metric.FixedInt(8_420, "步"),
                "步数",
                Notification.SEMANTIC_STYLE_SAFE,
            )
        )
        .addMetric(
            Notification.Metric(
                Notification.Metric.FixedInt(92, "bpm"),
                "心率",
                Notification.SEMANTIC_STYLE_CAUTION,
            )
        )
        .setCriticalMetric(0)

    return Notification.Builder(context, FITNESS_CHANNEL_ID)
        .setSmallIcon(R.drawable.ic_fitness)
        .setContentTitle("户外训练")
        .setStyle(style)
        .setOngoing(true)
        .setRequestPromotedOngoing(true)
        .build()
}
```

`MetricStyle` 至少需要一个 metric；`setCriticalMetric()` 只表达在紧凑界面优先使用哪个指标。请求提升展示（promoted treatment）也不保证系统一定提升通知。

### 实时更新（Live Update）需要同时满足一组条件

Android 17 的 Live Update 可以使用标准系统样式（Standard Style）、`BigTextStyle`、`CallStyle`、`ProgressStyle` 或 `MetricStyle`。希望让进行中通知获得提升展示（promoted ongoing）时，应用需要同时满足：

- manifest 声明非运行时权限 `android.permission.POST_PROMOTED_NOTIFICATIONS`；
- 调用 `setRequestPromotedOngoing(true)`；
- 通知处于进行中；
- 提供 content title（内容标题）；
- 不使用 custom content view（自定义内容视图）；
- 不是 group summary（组摘要）；
- 不请求 colorized（整张通知使用强调色背景）；
- 渠道 importance 不能是 `IMPORTANCE_MIN`；
- 普通 `POST_NOTIFICATIONS` 权限和其他通知条件仍然成立。

`Notification.hasPromotableCharacteristics()` 检查通知对象本身的结构条件，不包含用户是否允许、渠道 importance 或 OEM 附加条件。`NotificationManager.canPostPromotedNotifications()` 用于检查应用当前是否获准发布提升通知。是否设置 `FLAG_PROMOTED_ONGOING` 仍由系统决定。

实时更新适用于已经开始、由用户发起且对时间敏感的活动，例如导航、行程、配送和进行中的训练。普通促销、未来很久才发生的事件或没有明确结束点的状态不符合用途。

### Semantic style 表达含义，不直接指定颜色

Android 17 提供四种语义：

| 常量 | 含义 | AOSP 模板常见映射 |
| --- | --- | --- |
| `SEMANTIC_STYLE_INFO` | 需要突出、但不在风险层级中 | 蓝 |
| `SEMANTIC_STYLE_SAFE` | 安全、及时、低紧迫度 | 绿 |
| `SEMANTIC_STYLE_CAUTION` | 注意、中等紧迫度或延迟 | 黄/橙 |
| `SEMANTIC_STYLE_DANGER` | 危险、极高紧迫度或严重延迟 | 红 |

它可以用于 `Metric`、`ProgressStyle.Segment`、`ProgressStyle.Point`，也可通过 `createSemanticStyleAnnotation()` 为部分文本添加语义注解（annotation）。颜色由平台根据主题和显示界面选择；应用不应依赖某个固定 ARGB 值。文本去掉颜色后仍必须表达完整含义，无障碍信息不能只靠颜色区分。

这些语义样式只有在通知和显示界面符合条件时才会生效。AOSP 的 `Metric` 文档明确把语义显示限定在提升通知，文本 annotation 的文档也把提升通知作为典型资格条件；普通通知中保留语义数据，不代表界面一定着色。

### 自定义通知视图限制

Android 17 针对 target API 37 的 custom notification view 增加了展开后内存检查。迁移时应检查：

- collapsed、expanded、heads-up 与 public view 是否都能在被系统剥离后安全回退；
- 是否可以改用系统 style；
- URI 和 bitmap 指向的图片是否在解码前限制尺寸；
- 更新是否保持 layout ID 稳定；
- 是否在 Android 17 真机上检查 `NotificationService` 与 `NotifContentInflater` 日志。

### 版本演进边界

| 版本 | 直接相关的变化 |
| --- | --- |
| Android 13 / API 33 | `POST_NOTIFICATIONS` 运行时权限；Task Manager 展示运行中的 FGS 应用 |
| Android 14 / API 34 | 多数 ongoing / FGS 通知允许用户单条划走，少数 call、media、DPC（设备策略控制器）等场景例外 |
| Android 15 / API 35 | 部分 FGS 类型增加时长限制，通知存在不能替代 FGS 合规 |
| Android 16 / API 36 | `ProgressStyle` 与 promoted ongoing / Live Update 能力 |
| Android 17 / API 37 | `MetricStyle`、semantic style、Live Update 扩展；custom notification view 内存检查加强 |

版本历史说明兼容边界；当前实现的判断均以 Android 17 为上限。

## 代码审查清单

审查应用通知实现时，可以按以下顺序检查：

1. channel ID 是否稳定，是否批量创建，是否错误尝试覆盖用户设置；
2. `(tag, id)` 是否对应稳定业务对象，进度更新是否合并；
3. builder、图片解码与 `notify()` 是否占用主线程；
4. custom `RemoteViews` 是否有系统 style 替代方案；
5. PendingIntent 身份是否冲突，mutability 是否只按功能需要开放；
6. group 是否同时设置正确的 summary 与 alert behavior；
7. 是否把通知显示当成业务成功确认；
8. Perfetto 是否包含应用、Binder、`system_server`、SystemUI 和图形线程；
9. Android 17 的 Live Update 是否逐项满足条件，而非只调用一个 setter（设置方法）。

## 相关章节

- **§1.38 Binder 线程池与优先级继承**：解释同步 `notify()` 中的 Binder 调度和等待。
- **§1.8 ActivityManagerService**：NMS 使用的 user、进程状态、FGS 与 PendingIntent 能力。
- **§4.11 Cached App Freezer**：通知点击目标进程的解冻边界。
- **§8.11 推送通知管线性能**：从消息到达到通知提交的应用侧路径。
- **§9.6 Notification 性能与 ANR**：图片、RemoteViews、NLS 回调与 Perfetto 案例。
