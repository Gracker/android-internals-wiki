---
title: Notification 性能与 ANR
chapter: '9.5'
section: '9.5'
status: finalized
applicable_versions: Android 12 (API 31) - Android 17 (API 37)
task9_state: reviewed
last_verified: '2026-08-29'
last_verified_against: AOSP android-17.0.0_r1
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
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/services/core/java/com/android/server/am/ActivityManagerService.java
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
tags:
- notification
- anr
- notificationmanagerservice
- remoteviews
- performance
- notificationlistenerservice
- foreground-service
related_chapters:
- '9.1'
- '9.2'
- '9.3'
- '1.9'
- '9.4'
pipeline_stage: ready-to-publish
task6_state: reviewed
task2b_state: fixed
last_idle_audit_at: '2026-08-29T18:35:04+08:00'
last_idle_audit_run_id: 20260829-183504-idle-audit-cb8e7f3a
---

# Notification 性能与 ANR

通知发布会跨越应用构建、Binder 调用、系统服务处理、`RemoteViews` 加载和监听器分发，多处阻塞都可能最终表现为主线程超时。分析时应按调用方向和线程归属还原链路，而不是把所有通知 ANR 都归因于 NotificationManagerService。

## 为什么 Notification 会引发 ANR

“通知导致 ANR”至少包含四条不同的执行链。它们处理同一份 Notification 数据，但运行在线程和超时检测器各不相同的进程中。NMS 是 `NotificationManagerService`，负责系统侧的通知管理；NLS 是 `NotificationListenerService`，供获得授权的监听器接收通知事件。

| 执行链 | 同步边界 | 可能出现的故障 |
|---|---|---|
| 发布应用调用 `notify()` | 构造对象、写入 Parcel（Binder 序列化容器）、同步 Binder、NMS 同步处理段 | 发布应用主线程 Input ANR、Binder 长等待 |
| NMS 异步入队与分发 | `system_server` 的 notification handler（消息处理线程）、锁和 CPU | 通知积压、`system_server` 延迟，极端情况下还需检查 Watchdog（系统服务存活监视器）证据 |
| SystemUI 消费并渲染 | SystemUI 创建/复用视图、加载图片和主线程提交界面 | 通知延迟显示、面板卡顿；有输入事件时可能形成 SystemUI Input ANR |
| NLS 接收回调 | 监听器的 Binder stub（接收跨进程调用的入口）把消息转给主线程 `MyHandler` | 监听器回调积压；进程持有窗口且输入超时时可能形成自己的 Input ANR |

前台服务还有一条相邻的超时：调用 `startForegroundService()` 后若没有及时完成 `Service.startForeground()`，AMS（ActivityManagerService）的 `serviceForegroundTimeout()` 会为该服务构造 timeout record（超时记录）、停止仍在等待的服务，并延迟派发 `SERVICE_FOREGROUND_TIMEOUT_ANR_MSG`；`serviceForegroundCrash()` 则使用 `ForegroundServiceDidNotStartInTimeException` 报告崩溃路径。复杂通知经常消耗这段时间预算，所以诊断报告仍会把它与通知性能放在一起，但要按前台服务转换超时单独归类。

## 通知发布流程与 ANR 触发点

### `notify()` 返回前做了哪些工作

`NotificationManager.notify()` 最终调用 `INotificationManager.enqueueNotificationWithTag()`。该 AIDL（Android 接口定义语言）方法没有声明 `oneway`，因此它是同步 Binder 调用，调用线程会等待 `system_server` 返回。

Android 17 / `android-17.0.0_r1` 的调用顺序可以拆成六段：

1. 应用构造 `Notification`、样式、`RemoteViews`、`Icon` 和 extras（附加字段）。
2. `NotificationManager` 执行兼容性修正，并把对象写入 Binder Parcel。
3. NMS 校验调用 UID、包名、用户、受限类别、通知渠道和前台服务策略。
4. NMS 修正通知、创建 `StatusBarNotification` / `NotificationRecord`，再检查通知数量和更新速率。
5. NMS 为 PendingIntent 设置临时 allowlist（允许后台启动等受限操作的名单）等状态，然后把 `EnqueueNotificationRunnable` post（投递）到 handler。
6. Binder 返回；排序、正式加入列表、向各 listener 分发和 SystemUI 渲染继续执行。

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

`mHandler.post()` 之前的 NMS 工作都在发布者的同步等待范围内，工作量远多于“权限校验后立刻入队”。`INotificationListener.aidl` 则声明为 `oneway interface`，因此 listener 回调和 SystemUI 显示通知都不属于发布者这次 Binder 调用的返回条件。

发布应用主线程停在 `notify()` 时，应继续判断耗时位于哪一侧：

- `notif.build` trace 区间很长：应用在读取文件、缩放图片、创建大量 action 或组装 extras；
- Binder transaction 前的 Running（正在 CPU 上执行）时间很长：Parcel 写入、bitmap 转共享内存或应用侧修正较重；
- 同步 Binder wait 很长：NMS 同步段、`system_server` Binder 线程、内部锁或被调用服务较慢；
- `notify()` 很快返回但用户晚看到：转查 NMS handler 与 SystemUI 消费链。

### 前台服务转换超时

AMS 在启动要求转为前台的 Service 时安排独立 timer（计时器）。服务完成 `startForeground()` 后才取消这段等待。图片下载、磁盘读图、数据库查询和复杂布局都不应放在此前的主线程路径上。

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

`startForeground()` 成功返回只表示系统已经接受这次前台转换和通知，不要求完整版已经生成。增强通知仍要处理取消竞态：后台任务完成时，Service 可能已经停止；更新前应检查任务代次（用于识别过期任务的版本号）或当前 Service 状态。

故障日志含 `Context.startForegroundService() did not then call Service.startForeground()`、`ForegroundServiceDidNotStartInTimeException` 或 service foreground timeout ANR 时，按前台转换超时处理。若同一窗口内还有输入 ANR 或普通 Service 执行 ANR，需要分别保留时间线，不能用其中一条自动解释另一条。

## NotificationManagerService 内部机制

### Binder 线程与 handler 各自负责什么

NMS Binder 线程负责检查调用身份、渠道和策略，修正对象，并完成配额检查和入队准备。`EnqueueNotificationRunnable` 进入 handler 后，NMS 才在通知锁保护下处理旧记录、分组、排序、提醒效果、URI 权限和 listener 通知。

源码里的线程名和 Trace section 会被平台分支调整。诊断时用执行上下文建立证据：

- 发布线程处于 Running、Runnable（具备运行条件但尚未获得 CPU）还是 Binder sleep（等待 Binder 回复）；
- 同一 Binder transaction 的服务端线程何时开始、何时返回；
- NMS handler 是否获得 CPU，是否长时间持有 `mNotificationLock`；
- SystemUI 与每个 NLS 的 Binder 接收线程、主线程消息何时运行。

### 通知排序与分发的开销

`NotificationListeners.prepareNotifyPostedLocked()` 会遍历已注册 listener，按用户、可见性、敏感信息与版本规则准备各自的数据。`makeRankingUpdateLocked(info)` 遍历当前通知列表，只把该 listener 可见的记录写进 `NotificationRankingUpdate`（通知排序与状态快照）。这项工作发生在通知锁内，因此每个 listener 得到的 map（映射表）可能不同。

准备完成后，NMS 把 listener runnable 投递到 handler，再调用 `oneway` Binder 接口。异步只省去了“等待客户端执行完”的过程，以下成本仍由 `system_server` 承担：

- 为 listener 过滤、裁剪或脱敏 `StatusBarNotification`；
- 构造该 listener 可见通知的 ranking 数组；
- 把通知与 ranking update 写入 Binder Parcel；
- 处理 Binder driver 背压（接收端来不及处理时发送端受限）、失败与 listener 生命周期。

通知总数、listener 数量和更新频率共同决定 fan-out（一次更新向多个监听器分发）的成本。不能用固定的“通知超过多少条”阈值代替 Perfetto 测量。

### 通知限流策略

Android 17 的更新速率限制位于 `checkDisqualifyingFeatures()`。它按应用包统计 enqueue rate（入队速率），不按 channel（通知渠道）单独计数。默认配置值是 `DEFAULT_MAX_NOTIFICATION_ENQUEUE_RATE = 5f`，系统可以从 `Settings.Global.MAX_NOTIFICATION_ENQUEUE_RATE` 覆盖，因此应用不能把 `5` 当作固定的系统契约。

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

NMS 在超限时记录 `Shedding <notification-key>` 并返回 `false`；这里的 Shedding 表示系统丢弃本次更新。外部 AIDL 返回类型是 `void`，发布应用通常收不到异常或失败回调，所以进度值可能跳跃。限流本身不会触发 ANR，它用于阻止高频更新继续增加 NMS 与消费者负载。

同一方法还限制普通应用保留的未完成通知数量。前台服务、user-initiated job（由用户主动发起的任务）和聚合组有各自例外，不能把速率配额、数量配额和 channel 限制混成一个概念。

## RemoteViews 的性能开销

### 传输的是布局标识和 action

`RemoteViews` 保存布局标识、应用信息、action（要在远端视图上执行的操作）和 bitmap/collection cache（图片与集合数据缓存）。它会被写入 Parcel；消费者收到后再创建或复用 View 树。

Android 17 的同步 `apply()` 路径可以缩写成下面三步：

```java
private View apply(Context context, ViewGroup parent, ...) {
    RemoteViews rvToApply = getRemoteViewsToApply(context, size);
    View result = inflateView(context, rvToApply, directParent, ...);
    rvToApply.performApply(result, rootParent, params);
    return result;
}
```

`writeToParcel()` 会写入 bitmap cache、应用信息、layout ID 和逐个 action。`mActions` 是内存字段，Parcel 中保存的是 action count（数量）、tag（类型标记）和各 action 数据，不存在名为 `mActions` 的 Parcel 字段。

### 布局复杂度会放大 SystemUI 的工作量

自定义布局会增加两端成本。发布端要创建更多 action 并写入 Parcel；SystemUI 要 inflate（从布局资源创建 View）、执行 action、measure/layout（测量和布局），并在主线程完成 View 绑定。耗时取决于设备、图片、布局、缓存和当时的 SystemUI 负载，不适合写成固定毫秒数。

工程上优先选择 `BigTextStyle`、`BigPictureStyle`、`MessagingStyle`、`ProgressStyle` 或 `MetricStyle` 等系统样式。标准样式仍通过框架生成的 `RemoteViews` 渲染；它的优势是布局和 action 由系统控制、适配更一致，但仍存在 `RemoteViews` 的处理开销。

### RemoteViews 的 reapply 机制

SystemUI 会先检查复用条件，通过后才能调用 `reapply()` / `reapplyAsync()`。package 和 layout ID 保持不变是常见必要条件；旧或新 `RemoteViews` 带有 `FLAG_REAPPLY_DISALLOWED`，或视图类型不匹配时，系统会放弃复用。

`reapply()` 会跳过根布局的 inflate，但仍会执行新对象中的 action。频繁更新进度时，保持模板和布局标识不变有助于复用；`setText`、`setImageViewBitmap` 等 action 的成本仍然存在。需要在目标 build（系统构建版本）的 SystemUI trace 中分别测量 inflate、async apply、reapply 和主线程提交。

### 图片通知的开销落在三段

图片型通知的成本分布在三个位置：

1. 应用侧取图、缩放和构造通知对象；
2. 通过 Parcel、共享内存和 Binder FD（文件描述符）传输；
3. SystemUI 侧加载、apply、布局与渲染。

三种 `Icon` 输入的成本模型不同：

- `createWithResource()` 传包名与资源 ID，消费者按资源解析，适合应用内稳定资源；
- `createWithContentUri()` 传 URI 字符串，消费者稍后打开并解码，需要 URI 在通知存活期间可读；
- `createWithBitmap()` 在 `Icon.writeToParcel()` 中调用 `Bitmap.asShared()`。已由共享内存支持且不可变的 bitmap 可直接复用，其余情况要创建共享副本。

共享内存可以避免把每个像素作为普通 Parcel 数据复制，但并非零成本。首次 `asShared()`、FD 管理、接收端对象创建和 GPU 上传仍会产生开销。AOSP 没有要求通知 bitmap 必须是 `ARGB_8888`；应根据图像内容选择合适格式，并在发布前缩放到实际需要的尺寸。

## NotificationListenerService 与性能

### NLS 回调的线程模型

`NotificationListenerService.attachBaseContext()` 用 `getMainLooper()` 创建 `MyHandler`。Binder stub 收到通知后先更新内部 ranking（排序与状态）信息，再把 `MSG_ON_NOTIFICATION_POSTED` 发给这个 handler；公开回调也标注为 `@MainThread`。

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

这段代码会延长该 listener 本次回调的执行时间，也会推迟后续主线程消息。若进程没有窗口或输入连接，回调耗时过长只表现为通知处理积压；只有输入事件也被派发到该进程，并且等待超过 InputDispatcher 预算时，才会形成 Input ANR。

### 回调只做快照与转交

NLS 回调参数来自系统状态，后台任务应复制所需字段，并定义队列容量、覆盖和去重策略。下面的示例用单线程 executor（执行器）保持处理顺序，同时避免把整个 `RankingMap` 长期留在队列中：

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

`NotificationSnapshot` 是应用自定义 DTO（只承载数据的对象）。复制时只取业务需要的 key、package、post time（发布时间）、文本摘要和当前通知的 ranking；图片、完整 extras、历史 `RankingMap` 与大 `RemoteViews` 不应默认进入后台队列。队列满时，可以按 notification key 合并同一通知的多次 update，并保留移除事件和最终状态。

### RankingMap 的成本与可见性

每次 posted callback（通知已发布回调）携带的是该 listener 当前可见通知的 ranking map。NMS 会按 listener 过滤用户、通知类型、锁定模式与敏感内容，再构造 `Ranking[]`。因此：

- map 只包含该 listener 可见的通知，并非系统全部通知；
- 不同 listener 的条目数和内容可能不同；
- 构造和 Parcel 成本随可见通知数量与 listener 数量增长；
- 应用缓存旧 map，会让整批 ranking 对象更久不能释放。

如果业务只关心本次 `sbn.getKey()`，在回调里调用 `rankingMap.getRanking(key, reusableRanking)` 取出需要字段即可。不要为“以后也许会用”保存每一代 map。

## 通知与 ANR 的典型模式

### 模式一：发布应用主线程卡在同步 Binder

trace 位于 `NotificationManager.notify*()`、`BinderProxy.transactNative()` 或 Parcel/bitmap 路径。取证要覆盖应用 slice 和对应的 `system_server` Binder 线程。若发布发生在主线程，长等待可能叠加输入事件并触发应用 Input ANR。

### 模式二：前台服务转换超时

日志含 `ForegroundServiceDidNotStartInTimeException`、前台转换 timeout record 或 service foreground timeout ANR。检查 Service 回调入口到 `startForeground()` 的所有同步工作，先提交最小合规通知，再构造增强内容。

### 模式三：NLS 主线程回调积压

监听器自己的主线程栈落在数据库、JSON、锁或网络等待。输入 ANR 还需证明该进程存在等待中的输入事件；没有这项证据时，结论写成 NLS 主线程长任务和回调积压。

### 模式四：高频 update 被限流丢弃

下载、导航、计时和指标通知反复更新同一个 key。应用反复构造对象，NMS 反复检查并向各监听器分发；同一 progress state（进度状态）内的 update 还可能在没有回调通知应用的情况下被丢弃。更新频率应根据用户可见变化、允许信息滞后的最长时间和最终状态发布要求来设计，不应跟随每个底层采样点发布。

### 模式五：SystemUI 渲染长任务

发布线程很快返回，通知显示却明显延后；Perfetto 显示 SystemUI 在 apply、图片加载、布局或主线程提交上耗时。若通知面板正接收触摸事件，SystemUI 主线程长任务还可能形成它自己的 Input ANR。

### 模式六：渠道创建进入首次关键启动路径

`createNotificationChannel()` 与 `notify()` 都会进入 NMS。固定 channel 可以在可控的初始化阶段幂等创建，也就是重复执行不会改变最终结果；首次启动前台服务时，不应同时执行大量 channel 迁移、图片读取和通知发布。必需 channel 也不能为减少启动耗时而延后创建，否则首个通知会因 channel 缺失被拒绝。

## Android 17 通知性能变更

### 版本边界

| 版本 | 已确认变化 | 性能诊断含义 |
|---|---|---|
| Android 12（API 31） | 支持范围的基线；NMS 已有通知数量与更新速率保护 | 不把这些保护误写成 Android 17 新增 |
| Android 13（API 33） | `POST_NOTIFICATIONS` 成为 runtime permission（运行时权限） | 发布前处理授权状态；它不改变已获授权通知的 NMS 同步边界 |
| Android 16（API 36） | `Notification.ProgressStyle` 与 promoted ongoing / Live Update API | 进度场景可使用系统样式；是否获得 Live Update 的显著展示位置需要另行判断 |
| Android 17（API 37） | `Notification.MetricStyle`、Metric value 类型、Semantic Coloring | 指标场景新增系统样式，语义颜色由状态栏等系统 surface（展示区域）解释 |

没有 Android 17 一手证据支持“后台 NLS 统一按包限频”，因此不能采用该说法。

### ProgressStyle 与 Live Update 是两个概念

`ProgressStyle` 描述通知内容。Live Update 则表示系统是否把 ongoing（持续进行中）通知提升为 promoted ongoing，并放到更显眼的 surface。它还要满足 manifest permission（清单声明的权限）、channel importance（渠道重要性）、样式和用户设置等条件；OEM 可以增加资格规则。

官方 Android 17 文档允许 Standard、`BigTextStyle`、`CallStyle`、`ProgressStyle` 和 `MetricStyle` 申请 Live Update，并禁止设置 `customContentView`。这条限制排除了 Live Update 上的任意自定义布局，但不能据此保证某个通知耗时一定降低。

### MetricStyle 与 Semantic Coloring

`Notification.MetricStyle` 在 API 37 加入，展开状态最多展示三个指标。每个 `Notification.Metric` 包含 label（标签）和一种 `MetricValue`；系统提供整数、浮点、日期、时间、时间差和文本等 value 类型。被提升为 Live Update 时，critical metric（关键指标）可能用于状态栏 chip（胶囊形提示区域）。

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

`MetricStyle` 至少要包含一个 metric（指标），否则 `build()` 会抛出 `IllegalArgumentException`。源码只绑定前三个 metric，更多条目不会进入展开布局；应用应在构造前把列表限制为三个。

Android 17 的 semantic style 常量包括 `UNSPECIFIED`、`INFO`、`SAFE`、`CAUTION` 和 `DANGER`。它们表达信息、安全、警示与危险等语义，由系统 surface 选择颜色，应用不能把这些值简化为直接指定绿、红、蓝。源码只在满足 feature flag（功能开关）、promoted ongoing 和非 unspecified 等条件时给 metric value 应用语义色。

MetricStyle 数值反复 update 时，`getProgressState()` 通常保持 `NONE`，新旧状态相同，仍会进入包级速率检查。采用系统样式不会绕过 NMS 配额。

## 在 Perfetto 中诊断通知 ANR

平台内部 slice（带起止时间的事件片段）和线程名会随 build 改变。应用自己的 Trace section（自定义 trace 区间）可以稳定标记通知构造、同步发布、前台转换和 NLS 回调，再结合 Binder 与调度数据追踪系统侧耗时。

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

`notif.build` 衡量应用构造耗时，`notif.notify` 包含 Parcel 与同步 Binder，`nls.callback` 只应覆盖快照和入队。前台服务可以另加 `notif.startForeground`。

### 最小采集配置

下面的 textproto（Perfetto 文本配置格式）采集 30 秒环形缓冲，包含应用 atrace、Binder 和调度事件：

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

15 秒固定窗口容易错过故障前因；这里使用 30 秒只是起点。线上触发器还要保留触发前的环形缓冲数据，并按设备内存调整 buffer（缓冲区）大小。

### 查询应用 section

下面的 Perfetto SQL 按耗时列出应用自定义 Trace section：

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

找到长 slice 后，回到对应时间范围检查 Binder transaction（事务）、线程状态和服务端调度。只看 section 总时长，无法区分线程是在 Running 还是睡眠等待。

### 查询主线程状态

下面的查询列出目标应用主线程持续超过 1 毫秒的状态片段：

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

长时间 Running 表示本进程正在执行 CPU 工作；`R` 表示线程已经可以运行，却还未获得 CPU；线程处于睡眠状态且 blocked function（阻塞位置）落在 Binder 路径时，需要继续寻找对应的 `system_server` transaction。线程状态只能给出排查方向，仍要用 slice 与调用栈确认具体代码。

### 三条链分别核对

- 发布链：`notif.notify`、Binder client/server、NMS 同步段返回；
- 分发链：NMS handler、通知锁、ranking 构造与 listener Binder 调用；
- 消费链：SystemUI/NLS Binder 接收、主线程消息、RemoteViews 或业务回调。

不要假定 `notif-handler`、`enqueueNotificationInternal` 之类私有 slice 名一定存在。应用自定义 section、Binder transaction、PID/TID 和时间范围更稳定。

### 使用 dumpsys 辅助诊断

下面的命令保存 NMS 当前状态，并从 system log 搜索被限流丢弃的更新记录：

```bash
adb shell dumpsys notification
adb logcat -b system -d | grep -E \
  'Package enqueue rate|Shedding .* package='
```

`dumpsys` 适合确认当前活跃记录、listener、channel 与策略状态；某次超速更新是否被丢弃，应以 NMS 日志和 trace 时间线为准。若快照采集发生在故障之后，已经移除的通知和短暂积压可能不再可见。

## 与其他机制的关系

- **§9.1 Service ANR 与超时**：区分 Service 执行 ANR 和前台转换异常。
- **§1.9 Binder IPC 与性能**：`notify()` 的同步返回、listener 的 oneway 回调和 Binder 背压属于不同事务。
- **§6.3 SharedPreferences/DataStore**：NLS 主线程中的 `commit()` 或加载等待会直接延长回调。
- **§1.15 ContentProvider**：URI 图标和 NLS 查询都可能触发 Provider 访问与冷启动。
- **§14.5 Perfetto SQL**：用 Binder、slice 与 thread_state 还原跨进程时间线。

## 常见问题与误区

### 「通知 ANR 只发生在使用 NotificationListenerService 的 App」

发布应用、SystemUI 和带 UI 的监听器，都可能因各自主线程阻塞而触发 Input ANR。NLS 回调本身没有独立的“通知 ANR timer”。前台服务转换失败属于异常崩溃路径，应按 detector（触发超时判定的系统检测器）分开统计。

### 「`notify()` 是异步的，不会阻塞主线程」

入口是同步 Binder。应用线程会等 NMS 完成入队前的校验、修正、记录构造和配额检查，并执行到 `mHandler.post()` 之后。它不等待 SystemUI 上屏，也不等待 NLS 用户回调完成。

### 「更新被限流时会抛异常」

超速 update 在 NMS 内返回 `false` 并写系统日志，外部 `enqueueNotificationWithTag()` 没有布尔返回值。应用通常只会看到某次进度没有展示。要可靠发布最终状态，应降低更新频率，并在状态转换时明确发出终态通知，不能依赖异常重试。

### 「自定义通知布局比标准模板性能更好」

标准模板也会生成 `RemoteViews`。它提供系统维护的布局、尺寸和 action 集合，通常更容易保持布局标识不变。自定义布局是否更慢仍需测量；层级、action、图片与复用失败都会增加开销。Live Update 禁止 `customContentView` 属于展示资格规则，不能当作性能基准测试结论。

### 「Icon 构造方式对性能没影响」

resource、URI 和 bitmap 的成本分别落在资源解析、延迟读取与解码、共享内存复制上。bitmap 应预先缩放；URI 要保证授权在通知存活期间有效；resource 要保证接收端能解析对应包和资源。选择依据是图片来源、更新频率和目标尺寸，不存在适用于所有来源的统一性能排序。

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
- [ActivityManagerService.java：前台服务 timeout / crash 消息分发](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/services/core/java/com/android/server/am/ActivityManagerService.java)

### 官方文档

- [通知开发指南](https://developer.android.com/develop/ui/views/notifications)
- [通知 runtime permission](https://developer.android.com/develop/ui/views/notifications/notification-permission)
- [前台服务超时排查](https://developer.android.com/develop/background-work/services/fgs/troubleshooting)
- [Android 16 ProgressStyle](https://developer.android.com/about/versions/16/features/progress-centric-notifications)
- [Android 17 MetricStyle 指南](https://developer.android.com/develop/ui/views/notifications/metric-style)
- [Live Update 资格与 surface](https://developer.android.com/develop/ui/views/notifications/live-update)
- [Android 17 Semantic Coloring](https://developer.android.com/about/versions/17/features#live-update-semantic-color)
- [ANR 诊断指南](https://developer.android.com/topic/performance/vitals/anr)
