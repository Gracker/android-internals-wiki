---

title: "案例集"
chapter: "11.4"
section: "11.4"
status: finalized
pipeline_stage: ready-to-publish
applicable_versions: "['Android 14.0 (API 34) - Android 17.0 (API 37)']"
tags: "[power, battery, energy]"
weight: "4"
source_repos: "['frameworks/base/core/java/android/os/PowerManager.java', 'frameworks/base/apex/jobscheduler/framework/java/android/app/AlarmManager.java', 'frameworks/base/core/java/android/os/BatteryStats.java', 'frameworks/base/services/core/java/com/android/server/power/PowerManagerService.java', 'frameworks/base/apex/jobscheduler/service/java/com/android/server/job/JobSchedulerService.java', 'frameworks/base/apex/jobscheduler/service/java/com/android/server/job/JobServiceContext.java', 'frameworks/base/apex/jobscheduler/framework/java/android/app/job/JobScheduler.java', 'frameworks/base/services/core/java/com/android/server/am/ActiveServices.java', 'frameworks/base/services/core/java/com/android/server/location/injector/SystemLocationPowerSaveModeHelper.java', 'frameworks/base/services/core/java/com/android/server/location/provider/LocationProviderManager.java', 'frameworks/opt/telephony/src/java/com/android/internal/telephony/RadioModemProxy.java', 'hardware/interfaces/radio/aidl/android/hardware/radio/modem/IRadioModem.aidl', 'kernel/power/suspend.c', 'drivers/base/power/wakeup.c', 'mm/vmscan.c']"
last_verified: "2026-07-31"
last_verified_against: "AOSP android-17.0.0_r1; Android 17 / API 37 public API reference; Android common kernel android17-6.18-2026-06_r6; linked AIW DeepResearch notes"
confidence: high
sources:
- type: deepresearch
  path: AOSP android-17.0.0_r1 source paths listed in source_repos; Android Developers Android 17 features, JobScheduler API, foreground-service timeout, Doze/App Standby, and background-location documentation; Android common kernel android17-6.18-2026-06_r6; DeepResearch/2026-06-17-battery-saver-location-power-policy-aosp-deep-dive.md; DeepResearch/2026-06-20-job-scheduler-throttling-mechanism.md; DeepResearch/2026-06-18-jobscheduler-source-verification.md; DeepResearch/2026-06-18-radio-power-state-machine-source-analysis.md; DeepResearch/2026-06-18-adaptive-battery-app-standby-coordination.md
task2b_state: fixed
task9_state: pass-tech-review
task6_state: reviewed
last_idle_audit_at: "2026-07-25T18:35:47+08:00"
last_idle_audit_run_id: "20260725-183547-idle-audit-692dae4f"
---

# 11.4 案例集

功耗问题很少由一行代码单独造成。常见过程是：应用发起工作，系统为它安排 CPU、网络、定位或存储资源，硬件进入高功耗状态，工作结束后资源又未及时释放。以下六个案例说明怎样从业务现象找到系统证据，再选择合适的 Android API 修复问题。

这里不给出通用的“节电百分比”。芯片、基带、信号、屏幕、温度、账号数据和 OEM（设备厂商）策略都会改变结果。缺少 bugreport（系统诊断包）、trace（性能跟踪）、测试脚本与环境记录的数字，无法支撑工程决策。

## 11.4.0 案例分析的共同步骤

每个案例都按同一组问题检查：

1. **功能契约是什么**：用户能接受多大延迟？工作是否由用户发起？错过一次是否可恢复？
2. **谁发起了资源请求**：记录 UID（Linux 用户标识，Android 通常用它区分应用及资源归属）、线程、Job ID、WakeLock tag（唤醒锁标签）、定位请求、网络调用和时间戳。
3. **系统为何准许或推迟**：检查 Doze（设备空闲省电模式）、App Standby bucket（应用待机分组）、Battery Saver（省电模式）、后台限制、热状态和 Job quota（任务配额）。
4. **硬件是否被激活**：CPU 运行不代表蜂窝基带正在发射，收到定位回调也不能说明 GNSS（全球导航卫星系统）只被当前 UID 使用。证据必须区分应用、系统服务和硬件层级。
5. **修复是否破坏业务**：同时比较成功率、端到端延迟、重试量和能耗指标。

推荐保留以下测试信息：

| 类别 | 至少记录的内容 |
|---|---|
| 构建 | 设备型号、Android build（系统构建版本）、应用版本、target SDK（目标 API 级别） |
| 环境 | Wi-Fi/蜂窝、信号、温度区间、屏幕状态、充电状态 |
| 负载 | 账号数据量、请求数量、文件大小、测试时长 |
| 功能 | 成功率、延迟分布、丢失与重复次数 |
| 系统 | bugreport、Perfetto、`dumpsys batterystats`、相关服务的 dumpsys（状态快照） |
| 统计 | 样本数、预热规则、中位数与离散程度 |

`BatteryStats` 和 Battery Historian 适合按 UID 归因，也就是把活动关联到具体应用，并对齐事件时间；设备支持的电源轨（芯片或模块的供电通道）或外接功耗仪更适合测量总能量。两类证据回答的问题不同，不能互相代替。

## 11.4.1 案例一：用前台服务轮询消息

### 故障代码

下面的示例展示一种常见错误：为了让进程长期存活（常称“保活”），每五秒在前台服务中查询一次服务端。

```java
public final class MessagePollingService extends Service {
    private volatile boolean stopped;

    @Override
    public int onStartCommand(Intent intent, int flags, int startId) {
        startForeground(1, buildNotification());
        new Thread(() -> {
            while (!stopped) {
                checkNewMessages();
                SystemClock.sleep(5_000);
            }
        }, "message-poll").start();
        return START_STICKY;
    }

    @Override
    public void onDestroy() {
        stopped = true;
    }
}
```

这段代码把“消息送达”实现成应用侧定时查询。没有新消息时，它仍会产生定时器唤醒、网络握手和维持进程的成本；`START_STICKY` 还可能在进程被终止后恢复服务。通知只说明服务对用户可见，不会降低这类轮询的开销。

### 按业务时效选择机制

| 业务要求 | 合适机制 | 说明 |
|---|---|---|
| 用户可见的实时消息 | 共享推送通道；高优先级只用于会立即展示通知的消息 | 避免每个应用维护独立的定时探测连接（心跳） |
| 后台内容刷新 | 普通优先级推送触发一次同步，另加低频恢复同步 | Doze 中允许延后 |
| 可延迟上传或同步 | WorkManager / JobScheduler | 声明网络、电量、充电等约束 |
| 用户正在感知的连续任务 | 与用途匹配的前台服务类型 | 导航、播放等工作结束后立即停服务 |

下面的 WorkManager 示例用于一次可恢复同步。多次触发会复用同名工作，避免在调度器中排出一串等价任务。

```java
public final class MessageSync {
    private static final String UNIQUE_WORK = "message-recovery-sync";

    public static void enqueue(Context context) {
        Constraints constraints = new Constraints.Builder()
                .setRequiredNetworkType(NetworkType.CONNECTED)
                .build();

        OneTimeWorkRequest request =
                new OneTimeWorkRequest.Builder(MessageSyncWorker.class)
                        .setConstraints(constraints)
                        .setBackoffCriteria(
                                BackoffPolicy.EXPONENTIAL,
                                30,
                                TimeUnit.SECONDS)
                        .build();

        WorkManager.getInstance(context).enqueueUniqueWork(
                UNIQUE_WORK,
                ExistingWorkPolicy.KEEP,
                request);
    }
}
```

`KEEP` 只消除同一时刻的重复待执行工作。Worker 仍需使用服务端游标或幂等键处理漏消息、重试和重复投递。周期任务的 15 分钟是最小周期边界，不是准点承诺，也不适合实时收消息。

### Android 17 下的调度边界

`JobScheduler` 在 Android 16 起位于 `frameworks/base/apex/jobscheduler/`。应用无需为正在执行的 Job 再持有 CPU WakeLock，系统会在 Job 从开始到结束的执行期内代持。下面几条边界比内部可调常量更适合作为应用契约：

- Android 12 起，每个应用最多保有 150 个已调度 Job，expedited job（加急任务）也计入。
- Android 11 起，高频调用 `schedule()`、`enqueue()` 等调度入口会被节流。
- App Standby bucket、后台限制、Doze、Battery Saver、热状态、约束和 quota 都可能让 Job 等待。
- Android 16 的 `getPendingJobReasons()` 能返回同时存在的 pending reason（等待原因）。
- Android 17 的 `getPendingJobReasonStats()` 会按原因累计等待时长；统计在重启后不保留，Job 成功完成或取消后也会清除。

下面的 API 37 代码用于在问题仍存在时读取等待时间。

```java
if (Build.VERSION.SDK_INT >= 37) {
    JobScheduler scheduler = context.getSystemService(JobScheduler.class);
    Map<Integer, Duration> stats =
            scheduler.getPendingJobReasonStats(MESSAGE_SYNC_JOB_ID);
    stats.forEach((reason, duration) ->
            Log.i("JobDebug", "reason=" + reason + ", wait=" + duration));
}
```

多个约束可同时阻止 Job，因而各项时长之和可能大于按现实时间计算的总等待时长。采集代码应在 Job 完成或取消前运行，并把 Job ID 与业务请求 ID 一起记录。

### 前台服务超时不是调度方案

| 类型 | Android 14—17 的边界 |
|---|---|
| `shortService` | 约三分钟；超时回调后仍不停止会进入 ANR 流程 |
| `dataSync` | target SDK 35+ 时，应用位于后台的累计运行额度通常为每 24 小时 6 小时 |
| `mediaProcessing` | target SDK 35+ 时，单独统计每 24 小时 6 小时 |

`dataSync` 与 `mediaProcessing` 按类型分别计时；同一类型下的多个服务共享运行额度。应用回到前台会重置可用时间。收到 `Service.onTimeout(int, int)` 后必须在数秒内 `stopSelf()`，否则进程会因服务未及时停止而异常终止。Android 17 延续这组行为。

这些超时限制用于约束前台服务滥用，不会把轮询自动变成可靠同步。可恢复的数据传输应保存进度，交给调度 API；用户可见且不可中断的工作才进入对应的前台服务。

### 验证

修复前后比较：

- 单位时间内进程唤醒次数、CPU running（CPU 保持运行）时间和网络请求次数；
- Job 的 pending reason、stop reason（停止原因）、重试次数和端到端消息延迟；
- 前台服务运行时长以及 `onTimeout()`、ANR（应用无响应）、crash（崩溃）日志；
- Wi-Fi 与蜂窝两组测试，避免把基带变化误算成代码收益。

## 11.4.2 案例二：后台持续请求高精度定位

### 故障代码

下面的请求在组件存活期间持续向 GPS provider（位置提供方）请求更新，期望间隔为一秒，最小位移门槛为零。

```java
public final class LocationTracker implements LocationListener {
    private final LocationManager locationManager;

    public LocationTracker(Context context) {
        locationManager = context.getSystemService(LocationManager.class);
    }

    public void start() {
        locationManager.requestLocationUpdates(
                LocationManager.GPS_PROVIDER,
                1_000,
                0,
                this);
    }
}
```

问题有两部分：请求参数没有依据产品场景确定，生命周期中也没有与注册对应的 `removeUpdates()`。系统可能因后台限制而降低回调频率，但应用仍应主动修正请求并及时注销。

### 把定位需求写成产品参数

定位策略至少要区分三类场景：

| 场景 | 请求方式 | 退出条件 |
|---|---|---|
| 页面展示一次附近位置 | `getCurrentLocation()` 或缓存位置 | 得到结果、超时、页面离开 |
| 用户主动导航 | 连续高精度请求；按运动状态和 UI 需求设间隔、最小距离 | 导航停止、权限撤销、FGS（Foreground Service，前台服务）结束 |
| 后台地理围栏 | Geofencing（地理围栏）等系统能力 | 围栏移除、业务失效 |

下面的示例用于“页面需要一次新鲜位置”。取消信号跟随页面生命周期，避免页面退出后继续等待。

```java
public final class CurrentLocationRequest {
    private final LocationManager locationManager;
    private CancellationSignal cancellationSignal;

    public CurrentLocationRequest(Context context) {
        locationManager = context.getSystemService(LocationManager.class);
    }

    public void request(
            Executor executor,
            Consumer<Location> consumer) {
        cancellationSignal = new CancellationSignal();
        locationManager.getCurrentLocation(
                LocationManager.FUSED_PROVIDER,
                cancellationSignal,
                executor,
                consumer);
    }

    public void cancel() {
        if (cancellationSignal != null) {
            cancellationSignal.cancel();
            cancellationSignal = null;
        }
    }
}
```

一次定位也可能启用高成本 provider；这种 API 的价值是给请求设置明确终点。导航等连续场景仍应使用 `LocationRequest`，参数须由可接受延迟、路径误差和运动速度推导，并在停止导航时移除 listener（监听器）。

### 系统端的检查链

Android 17 的 `LocationProviderManager` 会综合检查：

1. Manifest 声明、runtime permission（运行时权限）与 AppOps（应用操作权限状态）；
2. 用户是否启用位置、当前用户与 allowlist（允许列表）；
3. UID 前后台状态及后台定位资格；
4. Battery Saver 对 location service 的模式；
5. 后台请求的最小间隔与其他豁免条件。

未通过检查的 registration（已注册的定位请求）不会参与 provider request（提供方请求）的合并，当前 UID 的请求也就不会驱动底层 provider。设备上若还有导航、系统服务或其他应用请求定位，GNSS 或融合定位仍可能工作，所以“当前应用无回调”不能推导出整机定位功耗为零。

Battery Saver 的位置模式定义在 `PowerManager`，包括不改变、熄屏禁 GPS、熄屏禁全部位置、只允许前台请求、熄屏时降低请求频率等策略。`SystemLocationPowerSaveModeHelper` 接收 `PowerManagerInternal` 的状态，`LocationProviderManager` 再据此更新 registration。OEM 可以选择不同策略；应用不能假定某一模式永远是设备默认值。

后台位置限制从 Android 8.0 就已存在。AOSP 中能找到后台节流间隔的配置默认值，设备配置和 OEM 策略可以修改它；“后台大约每小时只有少量更新”才是应用应依赖的公开行为边界。Android 12 增加的是精确/大致位置等权限变化，不是后台节流的起点。

运行 `location` 类型 FGS 也不代表任何时刻都能启动定位。Android 12+ 的后台 FGS 启动限制和 Android 14+ 的 while-in-use（仅使用期间授权）权限检查仍然生效。导航应用应由用户可见操作启动，声明正确的前台服务类型，并在导航结束后释放请求。

### Battery Saver 与 Thermal 是两条通道

Battery Saver 会把位置策略传给 location service（位置服务）。Thermal service（热管理服务）提供当前热状态和 headroom（距离热限制还有多少余量），平台不会把热状态自动换算为某个 location power-save mode。产品若允许在温度升高时降低更新频率，可以监听热状态后调整自身请求；不要用高频轮询热状态制造新的负载。

### 验证

- `adb shell dumpsys location`：检查各 provider 的 request、registration、前后台与频率限制状态；
- bugreport 与 Battery Historian：对齐位置请求、WakeLock、屏幕、Doze 和 Battery Saver 时间线；
- Perfetto：检查 CPU 调度、Binder（进程间通信）与设备提供的定位 trace；
- 设备电源轨或外接仪表：判断 GNSS、CPU 和整机能量是否同步下降。

测试必须覆盖权限被撤销、仅大致位置、熄屏、后台、Battery Saver、导航 FGS 和其他应用同时定位等状态。

## 11.4.3 案例三：零散网络请求反复激活蜂窝链路

### 先划清 Android 与 modem 的边界

Android Radio HAL（无线硬件抽象层）的 `RadioState` 描述 modem（蜂窝基带）控制面处于 `OFF`、`UNAVAILABLE` 还是 `ON`。Android 17 的新实现使用稳定 AIDL（Android 接口定义语言）接口 `IRadioModem`；`RadioModemProxy` 仍保留旧的 HIDL（HAL 接口定义语言）分支以兼容旧设备。`setRadioPower()` 属于系统 telephony（电话与蜂窝网络）控制路径，普通应用不能用它做网络节能。

LTE/5G 的 RRC（Radio Resource Control，无线资源控制）连接态、DRX（Discontinuous Reception，非连续接收）周期、inactivity timer（空闲计时器）和发射功率，由 modem、网络制式、运营商参数及信号共同决定。公开 Android API 不提供一套跨设备可靠的 RRC 状态。把 3G 的 DCH/PCH（专用信道/寻呼信道）、LTE 的 RRC Connected/Idle 和 5G 状态放进同一张固定电流表，会产生错误结论。

应用层可以确认：大量间隔很短的请求会增加 DNS、连接建立、TLS、CPU 与网络活动；在蜂窝环境下，它们还可能延长 modem 活跃时间。请求结束后基带继续保持活跃的 tail time（尾时长）有多长、消耗多少能量，必须在目标设备和网络上测量。

### 使用持久化 outbox 合并可延迟上传

outbox 是本地持久化的待发送队列。下面的示例在业务事件写入 outbox 后，只保留一个待执行的上传 Worker。

```java
public final class TelemetryUpload {
    private static final String UNIQUE_UPLOAD = "telemetry-outbox-upload";

    public static void notifyOutboxChanged(Context context) {
        Constraints constraints = new Constraints.Builder()
                .setRequiredNetworkType(NetworkType.CONNECTED)
                .build();

        OneTimeWorkRequest upload =
                new OneTimeWorkRequest.Builder(OutboxUploadWorker.class)
                        .setConstraints(constraints)
                        .setBackoffCriteria(
                                BackoffPolicy.EXPONENTIAL,
                                30,
                                TimeUnit.SECONDS)
                        .build();

        WorkManager.getInstance(context).enqueueUniqueWork(
                UNIQUE_UPLOAD,
                ExistingWorkPolicy.KEEP,
                upload);
    }
}
```

Worker 在一次运行中循环读取大小受限的批次，收到服务端确认后再通过事务删除；达到本次执行额度且 outbox 尚未清空时返回 `Result.retry()`。数据库保存唯一可信的待发送记录，还要安排低频恢复同步，以处理“写入 outbox”与“调用 enqueue”无法纳入同一事务的问题，以及 `KEEP` 判断期间出现并发请求的竞争窗口。网络客户端应复用连接，并分别设置连接、读写与整次调用的超时。交互请求、支付确认和用户正在等待的发送操作不能为了批量而任意延后，它们需要单独的及时执行路径。

### 诊断证据

| 问题 | 证据 |
|---|---|
| 请求是否过碎 | 客户端调用日志、服务端 access log（访问日志）、包大小与时间间隔 |
| 是否重复握手 | 网络库 event listener（事件监听器）、Perfetto socket/CPU 事件、抓包 |
| 哪个 UID 产生流量 | `NetworkStatsManager`、`TrafficStats`、bugreport |
| modem 是否长时间活跃 | 设备支持的 modem/ODPM（设备端功耗测量）电源轨、厂商 trace、外接仪表 |
| 是否由弱信号放大 | 相同业务在 Wi-Fi、强信号蜂窝、弱信号蜂窝下分组测试 |

`TrafficStats` 的字节数不能直接换算为毫安时。传输相同字节数时，Wi-Fi、5G 弱信号和漫游网络的能量消耗可能相差很大。

## 11.4.4 案例四：组件泄漏伴随周期回调

### 故障代码

下面的 Activity 注册网络回调后没有注销。匿名内部类会经由回调引用 Activity，页面销毁后仍可能收到事件。

```java
public final class NetworkScreen extends Activity {
    private final ConnectivityManager.NetworkCallback callback =
            new ConnectivityManager.NetworkCallback() {
                @Override
                public void onAvailable(Network network) {
                    renderNetwork(network);
                }
            };

    @Override
    protected void onStart() {
        super.onStart();
        getSystemService(ConnectivityManager.class)
                .registerDefaultNetworkCallback(callback);
    }
}
```

泄漏的直接后果是对象无法随生命周期结束而回收。若回调还会刷新 UI、查询数据库或发起网络请求，已销毁的页面会继续触发 CPU、Binder 和 I/O 工作。较高的堆占用不能单独证明耗电，还要找到对象被保留后继续执行工作的证据链。

### 对称释放

下面的修复让注册与注销处于同一生命周期区间。

```java
public final class NetworkScreen extends Activity {
    private boolean registered;
    private final ConnectivityManager.NetworkCallback callback =
            new ConnectivityManager.NetworkCallback() {
                @Override
                public void onAvailable(Network network) {
                    renderNetwork(network);
                }
            };

    @Override
    protected void onStart() {
        super.onStart();
        getSystemService(ConnectivityManager.class)
                .registerDefaultNetworkCallback(callback);
        registered = true;
    }

    @Override
    protected void onStop() {
        if (registered) {
            getSystemService(ConnectivityManager.class)
                    .unregisterNetworkCallback(callback);
            registered = false;
        }
        super.onStop();
    }
}
```

生产代码还要防止重复注册，并根据 UI 是否需要后台更新，选择 `onStart/onStop` 或更长的生命周期。协程、Rx stream（ReactiveX 数据流）、sensor listener（传感器监听器）、location listener（位置监听器）和 Handler callback（回调）都要明确由谁注册、由谁取消。

### 证明它与功耗有关

证据应按顺序建立：

1. heap dump（堆转储）显示已销毁组件仍被某个 listener、线程或队列引用；
2. trace 或日志显示该对象仍收到回调；
3. 回调带来可量化的 CPU、binder、网络、定位或存储工作；
4. 修复后 retained object（仍被引用的对象）数量、回调量和对应资源使用时间同时下降。

GC（垃圾回收）次数增加可能带来 CPU 成本，内存压力也可能触发 reclaim（内存回收）、内存压缩或 swap（交换空间）；具体路径取决于设备内核与内存配置。`android17-6.18-2026-06_r6` 中页面回收的通用入口可从 `mm/vmscan.c` 追踪，但应用侧不能把 RSS（Resident Set Size，进程驻留内存）的变化直接换算成能耗。

Android 17 的 `ProfilingManager` 增加 anomaly trigger（异常触发器），可在系统检测到 Binder 调用过量或内存超限等异常时提供采样或 heap dump 线索。这个接口可以辅助取证，但不能取代复现脚本、对象引用链和功耗测量。

## 11.4.5 案例五：用 WakeLock 和 Alarm 对抗 Doze

### 错误思路

一种常见实现会在服务中长时间持有 WakeLock；检测到 `isDeviceIdleMode()` 后，再安排 `setExactAndAllowWhileIdle()` 继续唤醒设备。这样会减少系统合并后台工作的机会：

- Doze 会推迟普通 Job、sync、alarm 和网络访问，并忽略普通应用的 WakeLock；
- allow-while-idle Alarm（可在设备空闲时交付的闹钟）会唤醒设备，频率受系统限制，只应服务于用户可感知且有精确时刻要求的功能。

即时消息应优先使用共享推送通道。普通后台刷新交给 WorkManager/JobScheduler，接受维护窗口或 quota 带来的延迟。只有闹钟、日历提醒等用户明确要求准时发生的事件，才评估 exact Alarm（精确闹钟）资格。

### Android 17 的 listener 型 idle Alarm

API 37 增加接收 `Executor` 与 `OnAlarmListener` 的 `setExactAndAllowWhileIdle()`。这种 listener（监听器）形式的 Alarm 依赖调用进程继续存活。下面的代码只适合当前组件仍存活时需要的精确回调。

```java
public final class VisibleSessionDeadline {
    private final AlarmManager alarmManager;
    private final Executor executor;
    private AlarmManager.OnAlarmListener listener;

    public VisibleSessionDeadline(Context context) {
        alarmManager = context.getSystemService(AlarmManager.class);
        executor = context.getMainExecutor();
    }

    public void schedule(long delayMillis, Runnable action) {
        if (Build.VERSION.SDK_INT < 37) {
            throw new UnsupportedOperationException("API 37 required");
        }
        cancel();
        listener = action::run;
        alarmManager.setExactAndAllowWhileIdle(
                AlarmManager.ELAPSED_REALTIME_WAKEUP,
                SystemClock.elapsedRealtime() + delayMillis,
                "visible-session-deadline",
                executor,
                listener);
    }

    public void cancel() {
        if (listener != null) {
            alarmManager.cancel(listener);
            listener = null;
        }
    }
}
```

系统可在调用进程不再有 Activity、Service 或 ContentProvider 时取消 listener Alarm。组件结束时也应调用 `cancel(listener)`。需要在进程终止后仍可靠送达的用户提醒，应使用合适的 `PendingIntent` 方案，并遵守 exact Alarm 权限和政策。

### Doze 与 Low Power Standby

Doze 关注设备长时间闲置时的 CPU、网络、Job、Alarm 和 WakeLock。Low Power Standby（低功耗待机）还会在非交互状态下限制网络与 WakeLock；设备支持、启用状态和豁免都可能不同。运行前台服务也不会自动获得这些网络与电源策略的豁免。

平台进入 suspend（系统挂起）时会检查 wakeup source（内核唤醒源）。Android 17 的内核锚点是 `kernel/power/suspend.c` 与 `drivers/base/power/wakeup.c`。应用在 BatteryStats 中看到的 WakeLock 归因和内核 wakeup source 处于不同层级，排查时要通过时间线建立关联。

下面的命令用于在测试设备上强制进入和退出 Doze。

```bash
adb shell dumpsys deviceidle force-idle
adb shell dumpsys deviceidle
adb shell dumpsys deviceidle unforce
```

测试期间应确认设备未充电，并在结束后执行 `unforce`。用例要检查推送送达、普通同步延迟、维护窗口恢复、网络失败后的幂等重试，以及用户唤醒设备后的状态一致性。

## 11.4.6 案例六：多个模块各自注册后台任务

### 问题

同步、日志、配置和清理模块若各自创建周期 Job，容易产生这些后果：

- 多个 Job 具有相同网络约束与相近时限，却分别启动进程和网络；
- 页面、广播和 push（推送）都重复调用 `schedule()`；
- 每个模块独立重试，服务恢复时形成请求峰值；
- Job 数量、调度入口频率和 App Standby quota 更快触及限制。

合并任务时不能只看时间接近。精确时限、网络类型、充电要求、失败语义或用户可见性不同的工作应保留独立调度。

### 同约束工作使用一个 JobInfo

Android 14 起，`JobWorkItem`（Job 队列中的工作项）可以随 persisted Job（跨重启保留的任务）一起持久化。下面的示例让一组“需要联网且允许延迟”的工作共享内容稳定的 `JobInfo`。

```java
public final class DeferredWorkQueue {
    private static final int JOB_ID = 4100;

    public static int enqueue(
            Context context,
            String operation,
            long recordId) {
        ComponentName service =
                new ComponentName(context, DeferredJobService.class);

        JobInfo job = new JobInfo.Builder(JOB_ID, service)
                .setRequiredNetworkType(JobInfo.NETWORK_TYPE_UNMETERED)
                .setPersisted(true)
                .build();

        PersistableBundle extras = new PersistableBundle();
        extras.putString("operation", operation);
        extras.putLong("record_id", recordId);

        JobWorkItem item = new JobWorkItem.Builder()
                .setExtras(extras)
                .build();

        return context.getSystemService(JobScheduler.class)
                .enqueue(job, item);
    }
}
```

`NETWORK_TYPE_UNMETERED` 表示系统判定的非计量网络，不等同于 Wi-Fi。persisted Job 需要在 Manifest 中声明 `RECEIVE_BOOT_COMPLETED`，`DeferredJobService` 需要受 `BIND_JOB_SERVICE` 权限保护。服务应逐个调用 `dequeueWork()` 取出工作项，成功后调用 `completeWork()`，并在异步处理结束时调用 `jobFinished()`。业务记录需要自己的幂等键，以保证重复处理不会产生额外副作用；`JobWorkItem` 只负责排队，不能作为业务数据的唯一可信来源。

官方 API 建议同一队列持续使用相同的 `JobInfo`。反复改变 extras（附加参数）、ClipData（可携带 URI 等内容的数据容器）或约束，可能让系统认为任务描述发生变化，导致正在运行的 Job 被停止后重启。合并后仍受 150 个 Job 上限、调度入口频率限制、standby bucket、quota 和设备状态限制。

### App Standby 只解释“为何等”，不替应用做优先级

Adaptive Battery（自适应电量管理）或系统使用记录会影响 App Standby bucket，`QuotaController` 再按 bucket 与设备状态判断 Job 是否还有可用 quota。应用应根据业务时限选择普通、expedited（加急）或 user-initiated（用户发起）工作，不能靠频繁重新调度争取执行机会。

Android 17 可使用 `getPendingJobReasonStats()` 区分等待主要来自网络约束、App Standby、quota、设备状态还是调度优化。等待时间符合已声明的约束时，这是正常调度结果；若 SLA（服务时限承诺）不允许这段延迟，应重新选择 API 或调整业务契约。

### 验证

比较合并前后的：

- 待调度 Job 数与每小时调度 API 调用数；
- 进程启动、Job session（任务执行批次）、网络连接和失败重试数量；
- 每类操作的最长等待、成功率和重复处理；
- `STOP_REASON_*`、pending reason stats 与当前 standby bucket；
- 单位业务量的 CPU time、网络字节和设备能量。

## 11.4.7 跨案例判断表

| 现象 | 不能直接得出的结论 | 需要补的证据 |
|---|---|---|
| UID 网络字节下降 | 蜂窝功耗按同比例下降 | 信号、制式、modem rail（基带电源轨）、请求时间线 |
| 定位回调停止 | GNSS 已关闭 | 其他 registration、provider request、电源轨 |
| RSS 下降 | 电池续航提升 | GC/reclaim/CPU/I/O 与能量变化 |
| Job 长时间 pending | JobScheduler 出错 | pending reason、standby bucket、quota、设备状态 |
| FGS 仍在通知栏 | 网络和 WakeLock 可在 Doze 中自由使用 | Doze/LPS 状态、网络与 WakeLock trace |
| 唤醒次数下降 | 用户体验没有损失 | 成功率、延迟、丢失与恢复结果 |

## 11.4.8 版本边界

| 版本 | 与案例有关的变化 |
|---|---|
| Android 14 / API 34 | Job pending reason API；persisted Job 可携带持久化的 JobWorkItem；`shortService` 类型 |
| Android 15 / API 35 | target 35+ 的 `dataSync`、`mediaProcessing` FGS 进入 6 小时/24 小时限制；`Service.onTimeout(int, int)` |
| Android 16 / API 36 | `getPendingJobReasons()` 返回多个等待原因；后台调度 quota 对 WorkManager 使用更需关注 |
| Android 17 / API 37 | `getPendingJobReasonStats()`；listener 版本 `setExactAndAllowWhileIdle()`；平台源码锚点 `android-17.0.0_r1` |

## 11.4.9 复核清单

- [ ] 后台工作是否有明确的延迟和可靠性契约？
- [ ] 用户不可见的工作是否误用了前台服务、WakeLock 或 exact alarm？
- [ ] 是否用唯一工作、稳定 Job ID 或服务端游标消除了重复调度？
- [ ] 定位请求是否由场景推导精度、间隔、距离和退出条件？
- [ ] 网络批量是否只作用于允许延迟的请求？
- [ ] listener、callback、线程、协程和 WakeLock 是否对称释放？
- [ ] 是否记录 pending reason、stop reason、standby bucket 和系统电源状态？
- [ ] 功耗数字是否附带设备、网络、温度、样本与原始产物？
- [ ] AOSP 引用是否来自 `android-17.0.0_r1`，内核引用是否来自 `android17-6.18-2026-06_r6`？

## 参考资料

### Android 17 / API 37

- [Android 17 features and APIs](https://developer.android.com/about/versions/17/features)
- [JobScheduler API reference](https://developer.android.com/reference/android/app/job/JobScheduler)
- [AlarmManager API reference](https://developer.android.com/reference/android/app/AlarmManager)

### 后台执行与位置

- [Foreground service timeouts](https://developer.android.com/develop/background-work/services/fgs/timeout)
- [Optimize for Doze and App Standby](https://developer.android.com/training/monitoring-device-state/doze-standby)
- [Background location limits](https://developer.android.com/about/versions/oreo/background-location-limits)
- [Android 16 JobScheduler quota changes](https://developer.android.com/about/versions/16/behavior-changes-all#job-scheduler-quota)
- [Power management resource limits](https://developer.android.com/topic/performance/power/power-details)

### AOSP `android-17.0.0_r1`

- `frameworks/base/apex/jobscheduler/service/java/com/android/server/job/JobSchedulerService.java`
- `frameworks/base/apex/jobscheduler/service/java/com/android/server/job/JobServiceContext.java`
- `frameworks/base/apex/jobscheduler/service/java/com/android/server/job/controllers/QuotaController.java`
- `frameworks/base/apex/jobscheduler/framework/java/android/app/AlarmManager.java`
- `frameworks/base/services/core/java/com/android/server/am/ActiveServices.java`
- `frameworks/base/services/core/java/com/android/server/location/injector/SystemLocationPowerSaveModeHelper.java`
- `frameworks/base/services/core/java/com/android/server/location/provider/LocationProviderManager.java`
- `frameworks/opt/telephony/src/java/com/android/internal/telephony/RadioModemProxy.java`
- `hardware/interfaces/radio/aidl/android/hardware/radio/modem/IRadioModem.aidl`

### Android common kernel `android17-6.18-2026-06_r6`

- `kernel/power/suspend.c`
- `drivers/base/power/wakeup.c`
- `mm/vmscan.c`
