---

title: "Notification 性能与 ANR"
chapter: "9.6"
section: "9.6"
status: "finalized"
applicable_versions: "Android 12 (API 31) - Android 17 (API 37)"
task9_state: reviewed
last_verified: "2026-07-14"
last_verified_against: "AOSP android-17.0.0_r1"
confidence: medium
sources:
- type: reference
  path: intake/research-feeds/2026-04-03-11-android16-live-updates-progressstyle.md
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/app/NotificationManager.java
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/app/INotificationManager.aidl
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/services/core/java/com/android/server/notification/NotificationManagerService.java
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/service/notification/NotificationListenerService.java
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/service/notification/INotificationListener.aidl
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/app/Notification.java
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/widget/RemoteViews.java
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/graphics/java/android/graphics/drawable/Icon.java
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/services/core/java/com/android/server/am/ActiveServices.java
- type: official
  path: https://developer.android.com/develop/ui/views/notifications
- type: official
  path: https://developer.android.com/develop/ui/views/notifications/notification-permission
- type: official
  path: https://developer.android.com/develop/background-work/services/fgs/troubleshooting
- type: official
  path: https://developer.android.com/about/versions/16/features/progress-centric-notifications
- type: official
  path: https://developer.android.com/develop/ui/views/notifications/metric-style
- type: official
  path: https://developer.android.com/develop/ui/views/notifications/live-update
- type: official
  path: https://developer.android.com/about/versions/17/features#live-update-semantic-color
- type: official
  path: https://developer.android.com/topic/performance/vitals/anr
- type: aosp
  path: frameworks/base/core/java/android/app/NotificationManager.java
- type: aosp
  path: frameworks/base/services/core/java/com/android/server/notification/NotificationManagerService.java
tags: [notification, anr, notificationmanagerservice, remoteviews, performance, notificationlistenerservice, foreground-service]
related_chapters: ["9.2", "9.3", "9.4", "1.4", "9.5"]
pipeline_stage: ready-to-publish
task6_state: "reviewed"
task2b_state: fixed
---

# 9.6 Notification 性能与 ANR

## 为什么 Notification 会引发 ANR

“通知导致 ANR”至少包含四条不同的执行链。它们共享 Notification 数据，却不共享线程和超时检测器。

| 执行链 | 同步边界 | 可能出现的故障 |
|---|---|---|
| 发布应用调用 `notify()` | 构造对象、写 Parcel、同步 Binder、NMS 前半段 | 发布应用主线程 Input ANR、Binder 长等待 |
| NMS 异步入队与分发 | system_server 的 notification handler、锁和 CPU | 通知积压、system_server 延迟，极端情况下进入 Watchdog 取证范围 |
| SystemUI 消费并渲染 | SystemUI 的 inflate/apply、图片加载和主线程提交 | 通知晚显示、面板卡顿；有输入事件时可能形成 SystemUI Input ANR |
| NLS 接收回调 | 监听器 Binder stub 转主线程 `MyHandler` | 监听器回调积压；进程持有窗口且输入超时时可能形成自己的 Input ANR |

前台服务还有一条相邻的超时：`startForegroundService()` 启动后没有及时完成 `Service.startForeground()`，AMS 会让应用收到 `ForegroundServiceDidNotStartInTimeException`。这是进程崩溃路径，不是 `am_anr`。复杂通知经常消耗这段预算，所以诊断报告仍会把它与通知性能放在一起。

## 通知发布流程与 ANR 触发点

### `notify()` 返回前做了哪些工作

`NotificationManager.notify()` 最终调用 `INotificationManager.enqueueNotificationWithTag()`。该 AIDL 方法没有 `oneway`，调用线程会等 system_server 返回。

Android 17 / `android-17.0.0_r1` 的调用顺序可以拆成六段：

1. 应用构造 `Notification`、样式、`RemoteViews`、`Icon` 和 extras。
2. `NotificationManager` 执行兼容性修正并把对象写入 Binder Parcel。
3. NMS 校验调用 UID、包名、用户、受限类别、通知渠道和前台服务策略。
4. NMS 修正通知、创建 `StatusBarNotification` / `NotificationRecord`，检查数量和更新速率。
5. NMS 为 PendingIntent 设置临时 allowlist 等状态，然后把 `EnqueueNotificationRunnable` post 到 handler。
6. Binder 返回；排序、正式加入列表、listener fan-out 和 SystemUI 渲染继续执行。

下面的源码片段标出同步 Binder 入口和异步分界：

```java
// frameworks/base/core/java/android/app/NotificationManager.java
service.enqueueNotificationWithTag(
        targetPackage, sender, tag, id,
        fixNotification(notification),
        mContext.getUser().getIdentifier());

// frameworks/base/services/core/java/com/android/server/notification/NotificationManagerService.java
mHandler.post(new EnqueueNotificationRunnable(
        userId, r, isAppForeground, isAppProvided, tracker));
return true;
```

`mHandler.post()` 之前的 NMS 工作都在发布者的同步等待范围内，远多于“权限校验后立刻入队”。`INotificationListener.aidl` 则声明为 `oneway interface`；listener 回调和 SystemUI 上屏不会加入发布者这次 Binder 的返回条件。

发布应用主线程停在 `notify()` 时，应继续判断耗时位于哪一侧：

- `notif.build` 很长：应用在读取文件、缩放图片、创建大量 action 或组装 extras；
- Binder transaction 前的 Running 很长：Parcel 写入、bitmap 转共享内存或应用侧修正较重；
- 同步 Binder wait 很长：NMS 同步段、system_server Binder 线程、内部锁或被调用服务较慢；
- `notify()` 很快返回但用户晚看到：转查 NMS handler 与 SystemUI 消费链。

### 前台服务转换超时

AMS 在启动要求转为前台的 Service 时安排独立 timer。服务完成 `startForeground()` 后才取消这段等待。图片下载、磁盘读图、数据库查询和复杂布局都不应放在此前的主线程路径上。

下面的两阶段写法先提交满足渠道、small icon 和内容要求的通知，再在后台生成增强内容：

```java
Notification stub = new Notification.Builder(this, CHANNEL_ID)
        .setSmallIcon(R.drawable.ic_stat)
        .setContentTitle("服务启动中")
        .build();
ServiceCompat.startForeground(this, ID, stub, FOREGROUND_SERVICE_TYPE_DATA_SYNC);

backgroundExecutor.execute(() -> {
    Notification full = buildFullNotification();
    notificationManager.notify(ID, full);
});
```

`startForeground()` 成功返回只表示系统已经接受这次前台转换和通知，不要求完整版已经生成。增强通知仍要处理取消竞态：后台任务完成时，Service 可能已经停止；更新前应检查任务代次或当前 Service 状态。

故障日志含 `Context.startForegroundService() did not then call Service.startForeground()` 时，按前台转换超时处理。若同时存在 `am_anr`，需要分别保留两条时间线，不能用其中一条自动解释另一条。

## NotificationManagerService 内部机制

### Binder 线程与 handler 各自负责什么

NMS Binder 线程完成调用身份、渠道、策略、对象修正、配额检查和入队准备。`EnqueueNotificationRunnable` 进入 handler 后，NMS 才在通知锁保护下处理旧记录、分组、排序、提醒效果、URI 权限和 listener 通知。

源码里的线程名和 Trace section 会被平台分支调整。诊断时用执行上下文建立证据：

- 发布线程是否处于 Running、Runnable 或 Binder sleep；
- 同一 Binder transaction 的服务端线程何时开始、何时返回；
- NMS handler 是否获得 CPU，是否长时间持有 `mNotificationLock`；
- SystemUI 与每个 NLS 的 Binder 接收线程、主线程消息何时运行。

### 通知排序与分发的开销

`NotificationListeners.prepareNotifyPostedLocked()` 会遍历已注册 listener，按用户、可见性、敏感信息与版本规则准备各自的数据。`makeRankingUpdateLocked(info)` 遍历当前通知列表，只把该 listener 可见的记录写进 `NotificationRankingUpdate`。这项工作发生在通知锁内；每个 listener 得到的 map 可能不同。

准备完成后，NMS 把 listener runnable post 到 handler，再调用 `oneway` Binder 接口。异步只消除了“等待客户端执行完”的依赖，以下成本仍在 system_server 内：

- 为 listener 过滤、裁剪或脱敏 `StatusBarNotification`；
- 构造该 listener 可见通知的 ranking 数组；
- 把通知与 ranking update 写入 Binder Parcel；
- 处理 Binder driver 背压、失败与 listener 生命周期。

通知总数、listener 数量和更新频率一起决定 fan-out 成本。不能用一个固定的“通知超过多少条”阈值代替 Perfetto 测量。

### 通知限流策略

Android 17 的更新速率限制位于 `checkDisqualifyingFeatures()`。它按包统计 enqueue rate，不按 channel 单独计数。默认配置值是 `DEFAULT_MAX_NOTIFICATION_ENQUEUE_RATE = 5f`，系统可从 `Settings.Global.MAX_NOTIFICATION_ENQUEUE_RATE` 覆盖，因此 `5` 不是应用可依赖的协议常量。

下面是 `android-17.0.0_r1` 的核心判断：

```java
NotificationRecord previous = findPreviousNotificationLocked(r.getKey());
if (previous != null
        && previous.getNotification().getProgressState()
                == r.getNotification().getProgressState()
        && !isAutogroup) {
    final float appEnqueueRate = mUsageStats.getAppEnqueueRate(pkg);
    if (appEnqueueRate > mMaxPackageEnqueueRate) {
        return false;
    }
}
```

首次发布没有 `previous`，不会命中这段更新限流。进度状态从 NONE 变为 ONGOING、从 ONGOING 变为 COMPLETE 时，新旧状态不同，也会放行这次状态转换。同一状态内的反复更新受限；autogroup 路径另行处理。

NMS 在超限时记录 `Shedding <notification-key>` 并返回 `false`，外部 AIDL 返回类型是 `void`。发布应用通常收不到异常或失败回调，所以进度值可能跳跃。限流本身不是 ANR，它负责抑制高频更新继续放大 NMS 与消费者负载。

同一方法还限制普通应用保留的未完成通知数量。前台服务、user-initiated job 和聚合组有各自例外，不能把速率配额、数量配额和 channel 限制混成一个概念。

## RemoteViews 的性能开销

### 传输的是布局标识和 action

`RemoteViews` 保存布局标识、应用信息、action 和 bitmap/collection cache。它会被写入 Parcel；消费者拿到后再创建或复用 View 树。

Android 17 的同步 `apply()` 路径可以缩写成下面三步：

```java
private View apply(Context context, ViewGroup parent, ...) {
    RemoteViews rvToApply = getRemoteViewsToApply(context, size);
    View result = inflateView(context, rvToApply, directParent, ...);
    rvToApply.performApply(result, rootParent, params);
    return result;
}
```

`writeToParcel()` 会写 bitmap cache、应用信息、layout ID 和逐个 action。`mActions` 是内存字段，Parcel 中保存的是 action count、tag 和各 action 数据，不存在一个叫 `mActions` 的 Parcel 字段。

### 布局复杂度会放大 SystemUI 的工作量

自定义布局会增加两端成本。发布端要创建更多 action 并写入 Parcel；SystemUI 要 inflate、执行 action、measure/layout，并在主线程完成 View 绑定。耗时取决于设备、图片、布局、缓存和当时的 SystemUI 负载，不适合写成固定毫秒数。

工程上优先选择 `BigTextStyle`、`BigPictureStyle`、`MessagingStyle`、`ProgressStyle` 或 `MetricStyle` 等系统样式。标准样式仍通过框架生成的 `RemoteViews` 渲染，优势是布局和 action 受系统控制、适配一致，不能宣传为“没有 RemoteViews 开销”。

### RemoteViews 的 reapply 机制

SystemUI 可以在复用谓词通过时调用 `reapply()` / `reapplyAsync()`。package 和 layout ID 稳定是常见必要条件，旧或新 `RemoteViews` 带 `FLAG_REAPPLY_DISALLOWED`、视图类型不匹配等情况会阻止复用。

`reapply()` 跳过根布局 inflate，仍会执行新对象中的 action。频繁更新进度时，保持模板和布局身份稳定有助于复用；`setText`、`setImageViewBitmap` 等 action 的成本仍然存在。需要在目标 build 的 SystemUI trace 中分别测量 inflate、async apply、reapply 和主线程提交。

### 图片通知的开销落在三段

图片型通知的成本分布在三个位置：

1. 应用侧取图、缩放、构造通知对象
2. Parcel、共享内存和 Binder FD 传输
3. SystemUI 侧加载、apply、布局与渲染

三种 `Icon` 输入的成本模型不同：

- `createWithResource()` 传包名与资源 ID，消费者按资源解析，适合应用内稳定资源；
- `createWithContentUri()` 传 URI 字符串，消费者稍后打开并解码，需要 URI 在通知存活期间可读；
- `createWithBitmap()` 在 `Icon.writeToParcel()` 中调用 `Bitmap.asShared()`。已由共享内存支持且不可变的 bitmap 可直接复用，其余情况要创建共享副本。

共享内存避免把每个像素作为普通 Parcel 数据复制，不代表零成本。首次 `asShared()`、FD 管理、接收端对象创建和 GPU 上传仍要计入。AOSP 没有要求通知 bitmap 必须是 `ARGB_8888`；应根据图像内容选择有效格式，并在发布前缩放到实际需要的尺寸。

## NotificationListenerService 与性能

### NLS 回调的线程模型

`NotificationListenerService.attachBaseContext()` 用 `getMainLooper()` 创建 `MyHandler`。Binder stub 收到通知后更新内部 ranking 状态，再把 `MSG_ON_NOTIFICATION_POSTED` 发给这个 handler；公开回调也标注为 `@MainThread`。

下面的实现把数据库、网络和分析都留在主线程，容易让后续通知回调与应用 UI 消息排队：

```java
public class MyNotificationListener extends NotificationListenerService {
    @Override
    public void onNotificationPosted(
            StatusBarNotification sbn,
            RankingMap rankingMap) {
        saveToDatabase(sbn);
        uploadToServer(sbn);
        analyzeNotification(sbn);
    }
}
```

这段代码会延迟该 listener 的 dispatch completion 和后续主线程消息。若进程没有窗口或输入连接，回调长耗时只表现为通知处理积压；只有输入事件也被派发到该进程并超过 InputDispatcher 预算时，才会形成 Input ANR。

### 回调只做快照与转交

NLS 回调参数来自系统状态，后台任务应复制所需字段，并定义队列容量、覆盖和去重策略。下面的示例用单线程 executor 保序，同时避免把整个 `RankingMap` 长期留在队列中：

```java
public class MyNotificationListener extends NotificationListenerService {
    private final ExecutorService worker =
            Executors.newSingleThreadExecutor();

    @Override
    public void onNotificationPosted(
            StatusBarNotification sbn,
            RankingMap rankingMap) {
        NotificationSnapshot snapshot =
                NotificationSnapshot.copyRequiredFields(sbn, rankingMap);
        worker.execute(() -> persistAndAnalyze(snapshot));
    }
}
```

`NotificationSnapshot` 是应用自定义 DTO。复制时只取业务需要的 key、package、post time、文本摘要和当前通知的 ranking；图片、完整 extras、历史 `RankingMap` 与大 `RemoteViews` 不应默认进入后台队列。队列满时可以按 notification key 合并 update，保留移除事件和终态。

### RankingMap 的成本与可见性

每次 posted callback 携带的是该 listener 当前可见通知的 ranking map。NMS 会按 listener 过滤用户、通知类型、锁定模式与敏感内容，再构造 `Ranking[]`。因此：

- map 不是系统所有通知的无条件快照；
- 不同 listener 的条目数和内容可能不同；
- 构造和 Parcel 成本随可见通知数量与 listener 数量增长；
- 应用缓存旧 map 会延长整批 ranking 对象的生命周期。

如果业务只关心本次 `sbn.getKey()`，在回调里调用 `rankingMap.getRanking(key, reusableRanking)` 取出需要字段即可。不要为“以后也许会用”保存每一代 map。

## 通知与 ANR 的典型模式

### 模式一：发布应用主线程卡在同步 Binder

trace 位于 `NotificationManager.notify*()`、`BinderProxy.transactNative()` 或 Parcel/bitmap 路径。取证要覆盖应用 slice 和对应 system_server Binder 线程。若发布发生在主线程，长等待可能叠加输入事件并触发应用 Input ANR。

### 模式二：前台服务转换超时

异常为 `ForegroundServiceDidNotStartInTimeException`，没有 `am_anr` 也能发生。检查 Service 回调入口到 `startForeground()` 的所有同步工作，先提交最小合规通知，再构造增强内容。

### 模式三：NLS 主线程回调积压

监听器自己的主线程栈落在数据库、JSON、锁或网络等待。输入 ANR 还需证明该进程存在等待中的输入事件；没有这项证据时，结论写成 NLS 主线程长任务和回调积压。

### 模式四：高频 update 被 shed

下载、导航、计时和指标通知反复更新同一个 key。应用反复构造对象，NMS 反复检查并 fan-out，同 progress state 内的 update 还可能被静默丢弃。更新频率应依据用户可见变化、最大允许陈旧时间和终态保证设计，不跟随每个底层采样点发布。

### 模式五：SystemUI 渲染长任务

发布线程很快返回，通知显示却明显延后；Perfetto 显示 SystemUI 在 apply、图片加载、布局或主线程提交上耗时。若通知面板正接收触摸事件，SystemUI 主线程长任务还可能形成它自己的 Input ANR。

### 模式六：渠道创建挤入首个热路径

`createNotificationChannel()` 与 `notify()` 都会进入 NMS。固定 channel 可在可控的初始化阶段幂等创建；首个前台服务启动路径不应同时执行大量 channel 迁移、图片读取和通知发布。不要为了避开启动耗时延迟创建必需 channel，否则首个通知会因 channel 缺失被拒绝。

## Android 17 通知性能变更

### 版本边界

| 版本 | 已确认变化 | 性能诊断含义 |
|---|---|---|
| Android 12（API 31） | 支持范围的基线；NMS 已有通知数量与更新速率保护 | 不把这些保护误写成 Android 17 新增 |
| Android 13（API 33） | `POST_NOTIFICATIONS` 成为 runtime permission | 发布前处理授权状态；它不改变已获授权通知的 NMS 同步边界 |
| Android 16（API 36） | `Notification.ProgressStyle` 与 promoted ongoing / Live Update API | 进度场景可使用系统样式，Live Update 资格另行判断 |
| Android 17（API 37） | `Notification.MetricStyle`、Metric value 类型、Semantic Coloring | 指标场景新增系统样式，语义颜色交给系统 surface 解释 |

没有 Android 17 一手证据支持“后台 NLS 统一按包限频”，因此不能采用该说法。

### ProgressStyle 与 Live Update 是两个概念

`ProgressStyle` 描述通知内容。Live Update 描述系统是否把 ongoing 通知提升到更显眼的 surface。Live Update 还要满足 manifest permission、ongoing、channel importance、样式和用户设置等条件；OEM 可以增加资格规则。

官方 Android 17 文档允许 Standard、`BigTextStyle`、`CallStyle`、`ProgressStyle` 和 `MetricStyle` 申请 Live Update，并禁止设置 `customContentView`。这条限制减少了 Live Update 上任意自定义布局，但不能据此保证某个通知耗时一定降低。

### MetricStyle 与 Semantic Coloring

`Notification.MetricStyle` 在 API 37 加入，展开状态最多展示三个指标。每个 `Notification.Metric` 包含 label 和一种 `MetricValue`；系统提供整数、浮点、日期、时间、时间差和文本等 value 类型。被提升为 Live Update 时，critical metric 可能用于状态栏 chip。

下面的 API 37 示例创建一个单指标系统样式：

```java
if (Build.VERSION.SDK_INT >= 37) {
    Notification.Metric steps = new Notification.Metric(
            new Notification.Metric.FixedInt(1979),
            "步数");
    Notification notification =
            new Notification.Builder(context, CHANNEL_ID)
                    .setSmallIcon(R.drawable.ic_stat)
                    .setContentTitle("今日活动")
                    .setStyle(new Notification.MetricStyle()
                            .addMetric(steps))
                    .build();
}
```

`MetricStyle` 至少要包含一个 metric，否则 `build()` 会抛出 `IllegalArgumentException`。源码只绑定前三个 metric，更多条目不会进入展开布局；应用应在构造前把列表限制为三个。

Android 17 的 semantic style 常量包括 `UNSPECIFIED`、`INFO`、`SAFE`、`CAUTION` 和 `DANGER`。它表达信息、安全、警示与危险等语义，由系统 surface 选择颜色；不能简化成应用指定绿、红、蓝。源码只在满足 feature flag、promoted ongoing 和非 unspecified 等条件时给 metric value 应用语义色。

MetricStyle 数值反复 update 时，`getProgressState()` 通常保持 `NONE`，新旧状态相同，仍会进入包级速率检查。采用系统样式不会绕过 NMS 配额。

## 在 Perfetto 中诊断通知 ANR

平台内部 slice 和线程名会随 build 改变。应用自己的 Trace section 能稳定标记构造、同步发布、前台转换和 NLS 回调，再用 Binder 与调度数据向系统侧扩展。

### 应用侧标记

下面的 Kotlin 代码把构造与发布分成两个 section，并确保异常时关闭 section：

```kotlin
val notification = try {
    Trace.beginSection("notif.build")
    buildNotification()
} finally {
    Trace.endSection()
}
try {
    Trace.beginSection("notif.notify")
    notificationManager.notify(ID, notification)
} finally {
    Trace.endSection()
}

override fun onNotificationPosted(
    sbn: StatusBarNotification,
    rankingMap: RankingMap
) {
    try {
        Trace.beginSection("nls.callback")
        handOffSnapshot(sbn, rankingMap)
    } finally {
        Trace.endSection()
    }
}
```

`notif.build` 衡量应用构造，`notif.notify` 包含 Parcel 与同步 Binder，`nls.callback` 只应覆盖快照和入队。前台服务可另加 `notif.startForeground`。

### 最小采集配置

下面的 textproto 采集 30 秒环形缓冲，包含应用 atrace、Binder 和调度事件：

```textproto
buffers: {
  size_kb: 65536
  fill_policy: RING_BUFFER
}
data_sources: {
  config {
    name: "linux.ftrace"
    ftrace_config {
      atrace_apps: "your.package"
      atrace_categories: "am"
      atrace_categories: "binder_driver"
      atrace_categories: "gfx"
      atrace_categories: "view"
      atrace_categories: "wm"
      ftrace_events: "sched/sched_switch"
      ftrace_events: "sched/sched_wakeup"
      ftrace_events: "sched/sched_waking"
    }
  }
}
duration_ms: 30000
```

15 秒固定窗口容易错过故障前因；这里使用 30 秒只是起点。线上触发器还要预留故障前缓存，并按设备内存调整 buffer。

### 查询应用 section

下面的 Perfetto SQL 按耗时列出应用埋点：

```sql
SELECT
  process.name AS process_name,
  thread.name  AS thread_name,
  slice.name,
  slice.dur / 1000000.0 AS dur_ms
FROM slice
JOIN thread_track ON slice.track_id = thread_track.id
JOIN thread ON thread_track.utid = thread.utid
JOIN process ON thread.upid = process.upid
WHERE slice.name IN (
  'notif.build',
  'notif.notify',
  'notif.startForeground',
  'nls.callback'
)
ORDER BY slice.dur DESC;
```

找到长 slice 后，回到对应时间范围检查 Binder transaction、线程状态和服务端调度。只看 section 总时长无法区分 Running 与睡眠等待。

### 查询主线程状态

下面的查询列出目标应用主线程超过 1 毫秒的状态片段：

```sql
SELECT
  process.name AS process_name,
  thread.name  AS thread_name,
  thread_state.state,
  thread_state.blocked_function,
  thread_state.dur / 1000000.0 AS dur_ms
FROM thread_state
JOIN thread USING (utid)
JOIN process USING (upid)
WHERE process.name = 'your.package'
  AND thread.name = 'main'
  AND thread_state.dur > 1000000
ORDER BY thread_state.dur DESC;
```

长时间 Running 指向本进程 CPU 工作；`R` 表示 runnable 却未获 CPU；睡眠且 blocked function 落在 Binder 路径时，需要继续找对应 system_server transaction。线程状态只能给方向，仍要用 slice 与调用栈确认具体代码。

### 三条链分别核对

- 发布链：`notif.notify`、Binder client/server、NMS 同步段返回；
- 分发链：NMS handler、通知锁、ranking 构造与 listener Binder；
- 消费链：SystemUI/NLS Binder 接收、主线程消息、RemoteViews 或业务回调。

不要依赖 `notif-handler`、`enqueueNotificationInternal` 之类私有 slice 名必然存在。应用 section、Binder transaction、PID/TID 和时间范围更稳定。

### 使用 dumpsys 辅助诊断

下面的命令保存 NMS 当前状态，并从 system log 搜索更新 shed 记录：

```bash
adb shell dumpsys notification
adb logcat -b system -d | grep -E \
  'Package enqueue rate|Shedding .* package='
```

`dumpsys` 适合确认活跃记录、listener、channel 与策略状态；超速被丢弃的单次证据以 NMS 日志和 trace 时间线为准。快照发生在故障之后时，已经移除的通知和短暂积压可能看不到。

## 与其他机制的关系

- **§9.2 Service ANR 与超时**：区分 Service 执行 ANR 和前台转换异常。
- **§1.4 Binder IPC 与性能**：`notify()` 的同步返回、listener 的 oneway 回调和 Binder 背压属于不同事务。
- **§6.5 SharedPreferences/DataStore**：NLS 主线程中的 `commit()` 或加载等待会直接延长回调。
- **§1.10 ContentProvider**：URI 图标和 NLS 查询都可能触发 Provider 访问与冷启动。
- **§13.7 Perfetto SQL**：用 Binder、slice 与 thread_state 还原跨进程时间线。

## 常见问题与误区

### 「通知 ANR 只发生在使用 NotificationListenerService 的 App」

发布应用、SystemUI 和带 UI 的监听器都可能因各自主线程阻塞触发 Input ANR。NLS 回调本身没有独立的“通知 ANR timer”。前台服务转换失败又是异常崩溃路径，应按 detector 分开统计。

### 「`notify()` 是异步的，不会阻塞主线程」

入口是同步 Binder。应用线程会等 NMS 完成入队前的校验、修正、记录构造和配额检查，并执行到 `mHandler.post()` 之后。它不等待 SystemUI 上屏，也不等待 NLS 用户回调完成。

### 「更新被限流时会抛异常」

超速 update 在 NMS 内返回 `false` 并写系统日志，外部 `enqueueNotificationWithTag()` 没有布尔返回值。应用通常只看到某一帧进度没有展示。终态需要降低频率并在状态转换时明确发布，不能依赖异常重试。

### 「自定义通知布局比标准模板性能更好」

标准模板也会生成 `RemoteViews`。它提供系统维护的布局、尺寸和 action 集合，通常更容易保持布局身份稳定。自定义布局是否更慢仍需测量；层级、action、图片与复用失败会增加风险。Live Update 直接禁止 `customContentView`，这还是资格规则，不是性能基准测试结论。

### 「Icon 构造方式对性能没影响」

resource、URI 和 bitmap 分别把成本放在资源解析、延迟读取解码和共享内存复制上。bitmap 应预先缩放；URI 要保证授权与生命周期；resource 要保证接收端能解析对应包和资源。选择依据是来源、更新频率和目标尺寸，没有统一的性能排序能覆盖所有图片来源。

## 参考资料

### Android 17 / API 37 源码

- [NotificationManager.java：应用侧 notify 入口](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/app/NotificationManager.java)
- [INotificationManager.aidl：同步 enqueue 接口](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/app/INotificationManager.aidl)
- [NotificationManagerService.java：同步入队、配额、排序与 listener 分发](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/services/core/java/com/android/server/notification/NotificationManagerService.java)
- [NotificationListenerService.java：主线程 Handler 与 RankingMap](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/service/notification/NotificationListenerService.java)
- [INotificationListener.aidl：oneway listener 回调](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/service/notification/INotificationListener.aidl)
- [Notification.java：ProgressStyle、MetricStyle 与 progress state](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/app/Notification.java)
- [RemoteViews.java：Parcel、apply 与 reapply](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/widget/RemoteViews.java)
- [Icon.java：resource、URI 与 bitmap Parcel 路径](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/graphics/java/android/graphics/drawable/Icon.java)
- [ActiveServices.java：前台服务转换 timeout](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/services/core/java/com/android/server/am/ActiveServices.java)

### 官方文档

- [通知开发指南](https://developer.android.com/develop/ui/views/notifications)
- [通知 runtime permission](https://developer.android.com/develop/ui/views/notifications/notification-permission)
- [前台服务超时排查](https://developer.android.com/develop/background-work/services/fgs/troubleshooting)
- [Android 16 ProgressStyle](https://developer.android.com/about/versions/16/features/progress-centric-notifications)
- [Android 17 MetricStyle 指南](https://developer.android.com/develop/ui/views/notifications/metric-style)
- [Live Update 资格与 surface](https://developer.android.com/develop/ui/views/notifications/live-update)
- [Android 17 Semantic Coloring](https://developer.android.com/about/versions/17/features#live-update-semantic-color)
- [ANR 诊断指南](https://developer.android.com/topic/performance/vitals/anr)
