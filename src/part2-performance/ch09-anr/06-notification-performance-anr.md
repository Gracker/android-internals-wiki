---
title: "Notification 性能与 ANR"
chapter: "9.6"
section: "9.6"
status: "ready-for-review"
drafted_date: "2026-04-09"
drafted_by: "openclaw-task2a"
applicable_versions: "Android 12 (API 31) - Android 16 (API 36)"
last_verified: "2026-04-13"
last_verified_against: "AOSP android-16.0.0_r1"
confidence: medium
sources:
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/notification/NotificationManagerService.java"
  - type: aosp
    path: "frameworks/base/core/java/android/app/NotificationManager.java"
  - type: aosp
    path: "frameworks/base/core/java/android/widget/RemoteViews.java"
  - type: aosp
    path: "frameworks/base/core/java/android/service/notification/NotificationListenerService.java"
  - type: aosp
    path: "frameworks/base/core/java/android/service/notification/INotificationListener.aidl"
  - type: official
    path: "https://developer.android.com/develop/ui/views/notifications"
  - type: official
    path: "https://developer.android.com/develop/ui/views/notifications/notification-permission"
  - type: official
    path: "https://developer.android.com/develop/background-work/services/fgs/troubleshooting"
  - type: official
    path: "https://developer.android.com/about/versions/16/features/progress-centric-notifications"
  - type: official
    path: "https://developer.android.com/reference/android/app/Notification.ProgressStyle"
  - type: research
    path: "intake/research-feeds/2026-04-03-11-android16-live-updates-progressstyle.md"
tags: [notification, anr, notificationmanagerservice, remoteviews, performance, notificationlistenerservice, foreground-service]
related_chapters: ["9.2", "9.3", "9.4", "1.4", "9.5"]
pipeline_stage: task6_pending
task6_state: revisiting
reviewed_by: openclaw-task6
reviewed_date: "2026-05-06"
task6_result: pass-light-edit
task9_state: "reviewed"
task9_result: "needs-rework"
task2b_result: fixed
task2b_state: fixed
task9_reviewed_date: "2026-05-25"
task9_reviewed_by: "openclaw-task9"
last_task9_at: "2026-05-25T14:20:00+08:00"
last_task2b_at: "2026-05-06T19:28:51+08:00"
last_task6_at: "2026-05-06T17:26:00+08:00"
last_task6_audit: "2026-05-25"
last_task6_review_log: "logs/review/2026-05-06-17-review.md"
task6_review_notes: "2026-05-06 17:26 Task6：Task2B 修复后写作复审；L1/L2 轻修 2 组（RemoteViews reapply 段和 Icon 成本阶梯标点/术语间距）；无新增 L3/L4 回炉项，转 Task9 复审。"
last_task9_review_log: "logs/deep-review/2026-05-25-14-audit.md"
task9_review_notes: "2026-05-06 Task9 14:37：needs-rework。P0 2 / P1 0 / P2 1。L245、L508 Icon.createWithBitmap()/Bitmap.asShared() 回退描述；L518 NotificationListeners.java 源码路径不存在；L504 标准模板 RemoteViews 口径沿用既有 P2。 | 2026-05-06 18:45 Task9：needs-rework。P0 1 / P1 0 / P2 0。L504 “标准模板不需要 RemoteViews inflate” 与 android-16 Notification.Builder/NotificationContentInflater 源码矛盾。 | 2026-05-06 19:57 Task9：pass-tech-review。P0 0 / P1 0 / P2 2。旧 P0 已闭环；仅余 RemoteViews reapply flag 与 RankingMap 可见性过滤两个 P2，已写 suggestions；自动晋升 finalized。 | 2026-05-25 14:20 Task9 闲时抽检：needs-rework。P0 0 / P1 1 / P2 0。Android 17/API 37 已有官方 Notification.MetricStyle 与 Live Update Semantic Coloring API，章节仍写 Android 17 条目暂缓，已写 queue。"
review_notes: "2026-05-06 19:57 Task9：pass-tech-review。P0 0 / P1 0 / P2 2。旧 P0 已闭环；仅余 RemoteViews reapply flag 与 RankingMap 可见性过滤两个 P2，已写 suggestions；自动晋升 finalized。 | 2026-05-25 14:20 Task9 闲时抽检：needs-rework。P0 0 / P1 1 / P2 0。Android 17/API 37 已有官方 Notification.MetricStyle 与 Live Update Semantic Coloring API，章节仍写 Android 17 条目暂缓，已写 queue。"
last_task9_audit: "2026-05-25"
---

# 9.6 Notification 性能与 ANR

<!-- outline-start -->
## 要点

### 🔹 锚点 1:为什么 Notification 会引发 ANR
### 🔹 锚点 2:NotificationManagerService 内部机制
### 🔹 锚点 3:RemoteViews 的性能开销
### 🔹 锚点 4:NotificationListenerService 与性能
### 🔹 锚点 5:通知与 ANR 的典型模式
### 🔹 锚点 6:Android 17 通知性能变更
### 🔹 锚点 7:在 Perfetto 中诊断通知 ANR

<!-- outline-end -->

## 为什么 Notification 会引发 ANR

做 Android 稳定性优化时,经常会遇到两类栈:一类停在 `NotificationManager.notify()`,另一类停在 `NotificationListenerService.onNotificationPosted()`。它们看起来都和"通知"有关,阻塞位置却不一样。

`notify()` 侧的问题,通常落在应用构造通知对象、Binder 过进程,或 NotificationManagerService(NMS)入口校验和入队这段同步路径上。`onNotificationPosted()` 侧的问题,通常落在监听器进程自己的主线程。SystemUI 渲染慢会拖迟通知实际显示出来,但默认不会让调用方一直等到界面画完。

把这三段边界拆开,排查方向就清楚了:调用方卡住,先看应用线程与 Binder;监听器卡住,先看 NLS 主线程;通知晚到或下拉卡顿,再看 SystemUI 和 system_server 的调度状态。

## 通知发布流程与 ANR 触发点

### 一次 notify() 经历了什么

`NotificationManager.notify()` 会走到 `INotificationManager.enqueueNotificationWithTag()`。这一步是同步 Binder 调用,调用线程会等 system_server 的 Binder 入口返回,但不会一直等到 SystemUI 把通知画出来。

[图:App 线程调用 notify(),进入 system_server Binder 入口,NMS 把任务 post 到 Handler,再异步分发给 listener 和 SystemUI]

AOSP android-16 的边界在两处最清楚:

```java
// frameworks/base/core/java/android/app/NotificationManager.java
service.enqueueNotificationWithTag(
        targetPackage, sender, tag, id,
        fixNotification(notification),
        mContext.getUser().getIdentifier());
```

```java
// frameworks/base/services/core/java/com/android/server/notification/NotificationManagerService.java
final int packageImportance = getPackageImportanceWithIdentity(pkg);
boolean isAppForeground = packageImportance == IMPORTANCE_FOREGROUND;
mHandler.post(new EnqueueNotificationRunnable(
        userId, r, isAppForeground, isAppProvided, tracker));
return true;
```

对调用方来说,同步段通常只覆盖三类成本:

- 应用侧构造 `Notification`、`RemoteViews`,以及把对象写入 `Parcel`
- Binder 过进程和 NMS 入口的权限校验、建档、入队
- system_server 入口处的锁竞争或 Binder 线程繁忙

这些环节默认不在 `notify()` 的同步返回时间里:

- `EnqueueNotificationRunnable` 之后的排序、记录更新、listener fan-out
- `INotificationListener` 回调
- SystemUI 中的 `RemoteViews.apply()`、图片解码和完成上屏

`INotificationListener.aidl` 在 android-16 中声明为 `oneway interface`。SystemUI 和其他通知监听器属于异步消费者,不能把它们的耗时直接记成调用方 `notify()` 的同步阻塞。

### ANR 的三种核心触发场景

**场景一:`startForegroundService()` 到 `Service.startForeground()` 的预算被通知构造吃掉。**
官方故障文案是 `Context.startForegroundService() did not then call Service.startForeground()`。超时窗口发生在启动前台服务之后、服务调用 `startForeground()` 之前。复杂通知构造、图片解码、磁盘读图如果都放在这段路径里,预算会很快耗尽。

更稳妥的写法,是先发一个简单通知满足时限,再异步补全完整版:

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

**场景二:`NotificationListenerService` 回调把监听器进程主线程拖住。**
`NotificationListenerService` 在 `attachBaseContext()` 里把 `MyHandler` 绑到 `getMainLooper()`,`onNotificationPosted()` 也是 `@UiThread`。数据库 I/O、网络请求、复杂解析如果直接放在回调里,触发的是监听器进程自己的 Input ANR,不是发布方 `notify()` 一定同步变慢。

**场景三:高频 update 命中 NMS 的更新速率限制。**
android-16 的 `checkDisqualifyingFeatures()` 走的是包级 update 限流,不是通知渠道限流。命中条件是 `isUpdate && !hasCompletedProgress() && !isAutogroup`,速率来自 `mUsageStats.getAppEnqueueRate(pkg)`,默认阈值是 `DEFAULT_MAX_NOTIFICATION_ENQUEUE_RATE = 5f`。下载进度、歌词、导航剩余距离这类场景如果几百毫秒就 `notify()` 一次,很容易被 shed。

还有一类现象容易误判:SystemUI 过载会拉长"通知何时显示给用户"的时间,也会让下拉通知栏更卡。但这件事默认不等于调用方一直卡在 `notify()` 里,结论要回到 Perfetto 的线程状态和 Binder 边界来下。

## NotificationManagerService 内部机制

### NMS 的执行上下文

AOSP 当前实现里,`notify()` 的 Binder 入口会把发布任务 post 到 NMS 的 Handler 路径,后续 ranking / listener 相关工作继续异步执行。OEM 机型上的线程名、trace slice 名和打桩粒度可能与 AOSP 不同。

做排查时,建议把"线程名"降级为辅证,主证据放在三类信号上:

- App 调用线程的 `slice` 和 `thread_state`
- system_server 中与 `NotificationManagerService` 相关的方法调用或调度片段
- NLS / SystemUI 进程自己的主线程负载

### 通知排序与分发的开销

通知发布后,NMS 需要更新 `NotificationRecord`,执行拦截与排序,再把变化分发给 listener 和状态栏。通知数量很多、通知对象很重、监听器很多时,system_server 的 CPU 时间会明显上升。

公开文档和当前 AOSP 分支不足以把"Android 14 起并行分发""Android 15 起增量排序"这类变化逐版钉死。诊断时更实用的做法,是直接看当前 build 上 `system_server` 的实际调度和 listener 分发耗时。

### 通知限流策略

速率限制的观察点需要改正两件事。

一是它不是"每个通知渠道单独限流"。android-16 的实现是包级 enqueue rate,比较的是 `mUsageStats.getAppEnqueueRate(pkg)` 和 `mMaxPackageEnqueueRate`。

二是它主要针对 update path。AOSP 条件是:

```java
boolean isUpdate = mNotificationsByKey.get(r.getSbn().getKey()) != null
        || findNotificationByListLocked(mEnqueuedNotifications, r.getSbn().getKey()) != null;
if (isUpdate && !r.getNotification().hasCompletedProgress() && !isAutogroup) {
    final float appEnqueueRate = mUsageStats.getAppEnqueueRate(pkg);
    if (appEnqueueRate > mMaxPackageEnqueueRate) {
        return false;
    }
}
```

这段逻辑对进度型通知很有现实意义。已经完成的 progress 更新、autogroup 摘要和普通首次发布,处理路径不一样;需要重点压频的是"同一条通知不断 update"的场景。

## RemoteViews 的性能开销

### 跨进程 inflate 的工作原理

`RemoteViews` 存的不是一棵已经 inflate 好的 View 树,而是"要对哪一个布局做哪些操作"的描述。android-16 的类定义里,动作集合是 `ArrayList<Action> mActions`;应用到目标 View 树上时,走的是 `inflateView()` + `performApply()`。

```java
// frameworks/base/core/java/android/widget/RemoteViews.java
private ArrayList<Action> mActions;

private View apply(...) {
    RemoteViews rvToApply = getRemoteViewsToApply(context, size);
    View result = inflateView(context, rvToApply, directParent, ...);
    rvToApply.performApply(result, rootParent, params);
    return result;
}
```

`mActions` 是内存中的动作列表,不是源码里的 `Parcel` 字段;示意代码也不能当作 AOSP 实现引用。更准确的理解是:`RemoteViews` 在跨进程传输时会被 parcelize;到 SystemUI 侧后,再把动作列表应用到真实 View 上。

### 布局复杂度会放大 SystemUI 的工作量

自定义通知布局越深、子 View 越多、图片越大,SystemUI 侧的 inflate、measure 和图片处理成本越高。没有设备、图片尺寸、SystemUI 负载和测试条件时,`1-2ms`、`10-20ms`、`10-50ms`、`100ms+` 这类固定数字没有参考价值。

更稳妥的经验规则有三条:

- 能用 `BigTextStyle`、`BigPictureStyle`、`MessagingStyle` 这类系统模板,就不要先上自定义 `RemoteViews`
- 自定义布局控制层级和 View 数量,别把普通页面布局整块搬进通知
- 图片按通知实际显示尺寸缩放,再决定是否放进通知

### RemoteViews 的 reapply 机制

SystemUI 在渲染通知时有一条复用路径：如果新旧通知的 `package` 和 `layoutId` 没变，`NotificationContentInflater.canReapplyRemoteView()` 返回 true，SystemUI 不重新 inflate，而是调用 `RemoteViews.reapply()` 或 `reapplyAsync()` 把新的动作列表应用到已有 View 上。

reapply 跳过了 inflate，但仍然会执行新 `RemoteViews` 的所有 action（如 setText、setImageViewBitmap 等）。成本从「inflate + 全部 action」降到了「全部 action」，action 数量不变时收益有限。实际收益需要用 SystemUI 侧的 Perfetto trace 验证：对比 `inflate` slice 与 `reapply` slice 的耗时差。

对进度条型通知来说，如果布局结构不变、只有进度数字在变，reapply 能省掉 inflate 开销，但 setText 等 action 仍然逐条执行。保持 `package` 和 `layoutId` 稳定、避免每次 update 都换布局文件，是让 reapply 生效的前提。

### 图片通知的开销落在三段

图片型通知的成本通常分布在三段:

1. 应用侧取图、缩放、构造通知对象
2. 跨进程传输 `RemoteViews` 或图片相关数据
3. SystemUI 侧 inflate、解码、绑定和上屏

排查时不要只盯着 `notify()`。如果应用侧主线程已经很轻,但用户还是感觉通知晚到,问题更可能在 SystemUI 侧的 decode / render,而不是调用方的 Binder 返回时间。

**图片通知的成本阶梯。** 通知图片有三条传入路径,成本各不相同:

1. **`Icon.createWithResource(resId)`**：只传资源 ID 引用，SystemUI 侧按自己的 `Context` 解码。跨进程开销最低，推荐优先使用
2. **`Icon.createWithUri(uri)`**：传 URI，SystemUI 侧打开 ContentProvider 或文件流解码。跨进程开销是 URI 字符串本身，但 SystemUI 解码耗时取决于图片来源和尺寸
3. **`Icon.createWithBitmap(bitmap)`**：AOSP `Icon.writeToParcel()` 对 `TYPE_BITMAP` / `TYPE_ADAPTIVE_BITMAP` 调用 `Bitmap.asShared()` 生成不可变的 shared-memory backed bitmap，再通过 `Bitmap.writeToParcel()` 以共享内存 FD 传递。SystemUI 侧从 Parcel 重建 bitmap 对象并绑定渲染。`Bitmap.asShared()` 的行为是：如果源 bitmap 已经是 shared-memory backed 的不可变 bitmap 则直接返回；否则创建一份 ashmem 副本；无法创建时抛异常。这条路径不走像素数据序列化，但 `asShared()` 的格式准备和 SystemUI 侧的解码绑定仍有开销。实战中优先用 `createWithResource`，次选 `createWithUri`，`createWithBitmap` 只在前面两条走不通时使用，且应确保 Bitmap 为 ARGB_8888 格式并已缩放到通知实际显示尺寸。

## NotificationListenerService 与性能

### NLS 回调的线程模型

`NotificationListenerService` 的所有回调(`onNotificationPosted`、`onNotificationRemoved`、`onListenerConnected` 等)默认在**主线程**执行。这是一个容易被忽视的性能陷阱。

当一个 App 注册为通知监听器后,系统中任何 App 发布或取消通知,都会触发 NMS 通过 Binder 回调这个监听器。在通知密集的场景下(如用户同时运行了多个会发送通知的 App),回调频率可能达到每秒数十次。

如果 NLS 的回调实现中做了任何耗时操作,主线程就被占住了:

```java
// ❌ 典型的 NLS ANR 代码模式
public class MyNotificationListener extends NotificationListenerService {
    @Override
    public void onNotificationPosted(StatusBarNotification sbn) {
        // 危险:这个方法在主线程执行
        saveToDatabase(sbn);        // 数据库 I/O,可能 50-200ms
        uploadToServer(sbn);         // 网络请求,可能数秒
        analyzeNotification(sbn);    // CPU 密集计算
    }
}
```

在 Perfetto 中,这类 ANR 的表现是主线程出现一段长时间 Running 或 Sleeping(如果等待数据库锁),stack trace 指向 `onNotificationPosted()` 内部的代码。如果 ANR 发生时主线程没有处理 UI 交互,`InputDispatcher` 的超时倒计时就会启动,5 秒后触发 ANR。

### 推荐做法:回调转发到后台线程

```java
// ✅ 将耗时操作移到后台线程
public class MyNotificationListener extends NotificationListenerService {
    private final ExecutorService backgroundExecutor = Executors.newSingleThreadExecutor();

    @Override
    public void onNotificationPosted(StatusBarNotification sbn) {
        // 主线程只做轻量操作(如更新内存缓存)
        memoryCache.put(sbn.getKey(), sbn);

        // 耗时操作转发到后台线程
        backgroundExecutor.execute(() -> {
            saveToDatabase(sbn);
            // 注意:不要在这里调用 notifyDataSetChanged()
            // NLS 的 UI 更新需要通过 mHandler.post() 回到主线程
        });
    }
}
```

### 大量通知场景下的 RankingMap 重建

`NotificationListenerService.onNotificationPosted()` 的参数中包含 `RankingMap`,它是 NMS 对所有活跃通知的当前排名结果。每次有通知变化时,NMS 会重新生成完整的 `RankingMap` 并分发给所有监听器。

在通知数量较多时(100+),`RankingMap` 的 Parcel 序列化/反序列化开销不可忽略。虽然单次开销在毫秒级,但在高频通知场景下会累积。如果 NLS 回调中持有 `RankingMap` 引用而不及时释放,还可能导致内存压力。

[已验证: AOSP frameworks/base/core/java/android/service/notification/NotificationListenerService.java - 回调在主线程的主 Looper 上执行]

## 通知与 ANR 的典型模式

### 模式一:前台服务启动预算被复杂通知吃掉

这类问题常见于服务刚启动就要立刻变成前台服务的场景。预算窗口是 `startForegroundService()` 到 `Service.startForeground()` 之间,不是 `startForeground()` 之后还要再补一次 `notify()`。如果通知构造里混入图片解码、磁盘读取或复杂 `RemoteViews`,前台服务还没进入前台,预算已经被耗掉了。

两步式策略仍然有效:先用最小通知完成 `startForeground()`,再在后台线程构造完整版并 update 同一条通知。

### 模式二:NLS 回调中的阻塞操作

如果应用实现了 `NotificationListenerService`,`onNotificationPosted()` 里的阻塞 I/O、数据库写入、JSON 解析和网络请求都会直接占住监听器进程的主线程。ANR 栈会落在监听器进程自己的回调实现里,和原始发布方的 `notify()` 不是同一条阻塞链。

### 模式三:高频通知更新导致 update path 过热

下载、歌词、导航、运动记录这类业务容易反复 update 同一条通知。这里的风险有两层:

1. 应用自己频繁构造通知对象,主线程先被拖慢
2. NMS 对同一条通知的 update path 触发包级速率限制,更新被 shed 或明显排队

经验上,进度型通知不应该跟随每个字节、每句歌词或每个定位点都 `notify()` 一次,应该按用户能感知的粒度压频。

### 模式四:通知渠道创建和首次发通知挤在一起

`createNotificationChannel()` 和 `notify()` 都是跨进程调用。把它们放在同一个冷启动主线程片段里,容易把启动时序拉长。更稳妥的做法,是在应用初始化阶段把固定渠道建好,业务路径只负责发布或更新通知。

### 模式五:SystemUI 过载让"通知显示"变慢

SystemUI 忙于锁屏动画、面板刷新或大量图片通知时,用户会感觉通知晚到、下拉卡顿,甚至把问题归因到发布方 `notify()` 被系统拖住。这个结论不能靠现象推断,必须回到 Perfetto:如果调用线程很快离开 Binder wait,问题更接近 SystemUI 显示时延;如果调用线程长时间睡在 Binder 边界,再看 system_server 的入口和队列。

## Android 17 通知性能变更

### 可确认的版本边界

能从官方文档或 `android-16.0.0_r1` 直接核对的结论只有三类:Android 13 的通知权限、Android 16 的 `ProgressStyle` / promoted ongoing 相关文档,以及当前 AOSP 下的 NMS / `RemoteViews` 行为。Android 14 并行分发、Android 15 排名优化、Android 17 后台 NLS 限频都缺少足够一手材料,不适合作为固定版本事实。

### POST_NOTIFICATIONS 在 Android 13,不在 Android 12

官方 notification permission 文档写得很清楚:`POST_NOTIFICATIONS` 是 Android 13 (API 33) 起的 runtime permission。Android 12 可以讨论的是通知 update 限流和前台服务相关约束,不该把通知权限提前一代。

### ProgressStyle 与 promoted ongoing 要分开写

`Notification.ProgressStyle` 是 API 36 新增的系统模板样式,用于 rideshare、delivery、navigation 这类有明确起点和终点的进度型通知。promoted ongoing / Live Update 是单独的展示资格,需要额外满足权限和样式约束。

从性能角度,`ProgressStyle` 的收益可以保守地理解成"优先走系统模板,减少自定义 `RemoteViews` 的需求"。

### Android 17 (API 37)：MetricStyle 与 Live Update Semantic Coloring

Android 17 新增 `Notification.MetricStyle` 通知模板，面向健康/健身、计时器、出行等场景，允许在 Always-On Display、锁屏、状态栏同时展示最多三个数据指标。相关类包括 `Notification.Metric`、`Notification.Metric.MetricValue`，用于定义指标名称、单位和数值。

Live Update 扩展到新的模板类型：从 Android 16 的 `ProgressStyle` 扩展到 Android 17 的 `MetricStyle`，并引入 **Semantic Coloring API**，用语义化颜色（绿/红/蓝）标记积极/消极/中性内容，让系统根据语义自动选择展示颜色，减少应用自定义 RemoteViews 的需求。

从性能角度，`MetricStyle` 与 `ProgressStyle` 一样走系统模板渲染，减少自定义 `RemoteViews` 的 inflate 和绘制开销。Live Update 通知通过 promoted ongoing 机制保持展示优先级，对通知 ANR 的影响在于：高频更新指标值时仍受 NMS 包级速率限制约束。

> **边界说明**：后台 NLS 回调限频（per-package rate limiting）目前缺少足够一手公开材料，不写成固定版本结论。

## 在 Perfetto 中诊断通知 ANR

诊断通知 ANR 时,优先使用可复现的方法;不要依赖 `notif-handler`、`enqueueNotificationInternal`、`onNotificationPosted` 这类在不同 build 上不稳定的线程名或 slice 名。

### 采集策略:先埋应用自己的 Trace 标记

如果要抓 `startForeground()`、`notify()`、NLS 回调的耗时,最稳的办法是在应用侧加 `Trace.beginSection()` 标记:

```kotlin
Trace.beginSection("notif.build")
val notification = buildNotification()
Trace.endSection()

Trace.beginSection("notif.startForeground")
ServiceCompat.startForeground(this, ID, notification, FOREGROUND_SERVICE_TYPE_DATA_SYNC)
Trace.endSection()
```

```kotlin
override fun onNotificationPosted(sbn: StatusBarNotification, rankingMap: RankingMap) {
    Trace.beginSection("nls.onNotificationPosted")
    try {
        handOffToExecutor(sbn)
    } finally {
        Trace.endSection()
    }
}
```

抓 trace 时,至少把 `sched`、`binder_driver`、`am`、`wm`、`gfx`、`view` 打开,并把目标 App 加到 atrace app 列表。这份 Perfetto text config 可以直接作为最小模板:

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
duration_ms: 15000
```

### 用稳定表名看调用方阻塞

如果应用已经加了 trace section,`slice`、`thread_track`、`thread`、`process` 这组表就足够定位通知相关耗时:

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
  'notif.startForeground',
  'nls.onNotificationPosted'
)
ORDER BY slice.dur DESC;
```

[图:App 主线程中的 `notif.build` / `notif.startForeground` slice 与 `thread_state` 对照]

### 用 thread_state 看 Binder 等待和主线程饥饿

应用主线程到底是在忙自己的逻辑,还是在睡眠等待 Binder 返回,用 `thread_state` 更稳:

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

如果这里长时间停在 `binder_thread_read`,再去对应时间点看 `system_server` 的调度状态;如果长时间是 Running,通常是应用自己在 build notification、图片处理或 NLS 回调里占住了 CPU。

### NLS 场景不要硬搜系统私有 slice

默认 trace 里,`enqueueNotificationInternal`、`onNotificationPosted` 这类系统私有 slice 名不一定稳定出现;不同 OEM 机型对线程命名和打桩粒度也不一样。把 SQL 写成 `slice.name LIKE '%binder%'` 或强行搜索 `notif-handler`,复用性很差。更稳的做法,是用应用自己的 trace section 作为锚点,再配合 `thread_state`、`sched` 和 `dumpsys notification` 做交叉验证。

### 使用 dumpsys 辅助诊断

当线上 ANR 报告里没有可用 trace 时,`dumpsys notification` 仍然有用:

- 活跃通知数量是不是异常偏多
- 当前有哪些 `NotificationListenerService` 注册着
- 哪些包命中过 rate limit 或被系统拦截

```bash
adb shell dumpsys notification
```

[图:`dumpsys notification` 中 NotificationRecord / Listener Services / Rate Limiting 三段重点输出]

## 与其他机制的关系

- **Service ANR(§9.2)**:前台服务启动预算与通知构造是 Notification ANR 和 Service ANR 的交叉点,重点看 `startForegroundService()` 到 `Service.startForeground()` 之间的耗时
- **Binder 性能(§1.4)**:通知发布的整个过程都依赖 Binder IPC,NMS 的线程模型和 Binder 线程池耗尽都可能导致通知延迟
- **SharedPreferences ANR(§6.5)**:NLS 回调中的 SP `apply()` / `commit()` 是常见的 ANR 触发组合
- **ContentProvider(§1.10)**:某些 NLS 实现在回调中通过 ContentProvider 查询数据,Provider 的冷启动会阻塞回调
- **Perfetto SQL 分析(§13.7)**:通知 ANR 的深度分析需要结合 Perfetto SQL 查询 Binder 调用链

## 版本演进

| 版本 | 当前能确认的变化 | 性能含义 |
|------|------------------|----------|
| Android 12 (API 31) | NMS update path 存在包级通知速率限制 | 高频 `notify()` 更新更容易被 shed,进度型通知需要主动压频 |
| Android 13 (API 33) | `POST_NOTIFICATIONS` 成为 runtime permission | 被拒绝的普通通知不会进入常规发布路径,系统总体通知负载会下降 |
| Android 16 (API 36) | `Notification.ProgressStyle` 新增,promoted ongoing / Live Update 文档可用 | 进度型通知更适合走系统模板,减少自定义 `RemoteViews` 的必要性 |
| Android 17 (API 37) | `Notification.MetricStyle` 新增,Semantic Coloring API 与 Live Update 扩展到 MetricStyle | 指标型通知走系统模板渲染,语义颜色减少自定义 RemoteViews；高频更新仍受 NMS 速率限制 |

Android 14 / 15 的分发、排序和后台 listener 行为目前缺少足够一手材料,不写成固定版本结论。

## 常见问题与误区

### 「通知 ANR 只发生在使用 NotificationListenerService 的 App」

不对。`NotificationListenerService` 回调阻塞只是通知 ANR 的一种模式。即使应用完全不使用 NLS,只要前台服务启动路径里的通知构造过重,`startForegroundService()` 到 `Service.startForeground()` 这段预算也可能被耗尽。

### 「notify() 是异步的,不会阻塞主线程」

`NotificationManager.notify()` 的入口是一次同步 Binder 调用。App 线程至少要等 NMS 的入口校验和入队返回,但默认不会等到 SystemUI 把通知画完,也不会等所有 NLS 回调执行完。排查时要把"同步 Binder 入口"和"后续异步显示"分开。

### 「通知限流会抛异常,所以不用担心」

Android 12+ 的通知限流是静默丢弃,超过频率限制的通知会被 NMS 直接忽略,不会抛异常,也不会回调通知 App。这说明进度更新可能丢失,但调用方收不到错误反馈,因此需要主动控制更新频率。

### 「自定义通知布局比标准模板性能更好」

标准模板（如 `NotificationCompat.BigTextStyle`）也是系统生成的 RemoteViews——`Notification.Builder.createContentView()` 对标准模板调用 `applyStandardTemplate()` 返回 RemoteViews 对象，`NotificationContentInflater` 仍通过 RemoteViews 管线渲染。但标准模板的布局与 action 集合受系统控制，`package`/`layoutId` 稳定，更容易命中 `canReapplyRemoteView()` 走 `reapply` 路径，避免完整 inflate。自定义布局同样走 RemoteViews 管线，但布局嵌套更深、图片和 action 更多时 inflate 与 reapply 的成本都更高。

### 「Icon 构造方式对性能没影响」

`Icon.createWithBitmap()` 在 `writeToParcel()` 时通过 `Bitmap.asShared()` 把 Bitmap 转为共享内存 backed 不可变副本，以 FD 形式跨进程传递，不走像素序列化。`asShared()` 的行为是:已 shared 的不可变 bitmap 直接返回，否则创建 ashmem 副本，无法创建时抛异常。`asShared()` 本身有格式转换和 ashmem 拷贝开销。通知图标优先用 `Icon.createWithResource(resId)`（只传资源 ID 引用，跨进程开销最低）。必须用 Bitmap 时，先按通知显示尺寸缩放并确保 ARGB_8888 格式，降低 `asShared()` 的拷贝开销。

## 参考资料

- **AOSP 源码路径**:
  - `frameworks/base/core/java/android/app/NotificationManager.java` - App 侧 `notify()` 入口
  - `frameworks/base/services/core/java/com/android/server/notification/NotificationManagerService.java` - NMS 核心实现与限流路径
  - `frameworks/base/core/java/android/widget/RemoteViews.java` - `RemoteViews` 的动作列表、inflate 与 apply
  - `frameworks/base/core/java/android/service/notification/NotificationListenerService.java` - NLS 回调线程模型
  - `frameworks/base/core/java/android/service/notification/INotificationListener.aidl` - listener 回调的 `oneway` 边界
  - `frameworks/base/services/core/java/com/android/server/notification/NotificationManagerService.java` — 监听器管理（`NotificationListeners` 为内部类）

- **官方文档**:
  - [developer.android.com/develop/ui/views/notifications](https://developer.android.com/develop/ui/views/notifications) - 通知开发指南
  - [developer.android.com/develop/ui/views/notifications/notification-permission](https://developer.android.com/develop/ui/views/notifications/notification-permission) - `POST_NOTIFICATIONS` 版本边界
  - [developer.android.com/develop/background-work/services/fgs/troubleshooting](https://developer.android.com/develop/background-work/services/fgs/troubleshooting) - 前台服务启动超时排查
  - [developer.android.com/about/versions/16/features/progress-centric-notifications](https://developer.android.com/about/versions/16/features/progress-centric-notifications) - Progress-centric notifications / Live Update
  - [developer.android.com/reference/android/app/Notification.ProgressStyle](https://developer.android.com/reference/android/app/Notification.ProgressStyle) - `Notification.ProgressStyle` API 参考
  - [developer.android.com/topic/performance/vitals/anr](https://developer.android.com/topic/performance/vitals/anr) - ANR 诊断指南

- **研究素材**:
  - [intake/research-feeds/2026-04-03-11-android16-live-updates-progressstyle.md] - Android 16 ProgressStyle API 详细分析

- **交叉引用**:
  - §9.1 ANR 设计思想
  - §9.2 ANR 类型与触发条件
  - §9.4 特殊场景的 ANR
  - §1.4 Binder IPC 与性能
  - §6.5 SharedPreferences/DataStore 性能与 ANR 优化
