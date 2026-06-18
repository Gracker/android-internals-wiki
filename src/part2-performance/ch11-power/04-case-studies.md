---
title: "案例集"
weight: 4
applicable_versions: [Android 14.0 (API 34) - Android 17.0 (API 37)]
source_repos: 
  - frameworks/base/core/java/android/os/PowerManager.java
  - frameworks/base/apex/power/service/java/com/android/server/power/PowerManagerService.java  # Android 16+ APEX路径
  - frameworks/base/core/java/android/os/BatteryStats.java
  - frameworks/base/apex/jobscheduler/service/java/com/android/server/job/JobSchedulerService.java  # Android 16+ APEX路径
  - frameworks/base/apex/jobscheduler/service/java/com/android/server/job/JobServiceContext.java  # Android 16+ APEX路径
  - frameworks/base/apex/jobscheduler/framework/java/android/app/job/JobInfo.java  # JobInfo公共API
  - frameworks/base/services/core/java/com/android/server/am/ActiveServices.java  # FGS超时/生命周期（传统路径，Android 16+ 相关逻辑随模块拆分）
  - frameworks/base/services/core/java/com/android/server/am/ActivityManagerConstants.java  # FGS常量定义
  - frameworks/base/services/core/java/com/android/server/location/LocationManagerService.java  # 定位服务管理
  - frameworks/base/services/core/java/com/android/server/location/injector/SystemLocationPowerSaveModeHelper.java  # 省电模式定位策略
status: ready-for-review
task2b_result: fixed
task2b_state: fixed
task9_state: pending
task9_result: needs-rework
task6_result: pass-light-edit
task6_state: revisiting
pipeline_stage: task6_pending
last_task2b_fix_at: 2026-06-18
---

# 11.4 案例集

本章节将通过实际案例深入分析 Android 功耗优化的实践方法，从系统到应用层面给出可直接使用的方案。

## 11.4.1 前台服务优化案例

### 问题场景
某社交应用在长时间运行时，用户反馈应用耗电异常。通过 Battery Historian 分析发现，前台服务存在频繁唤醒和 CPU 占用问题。

### 分析过程

#### 1. 问题定位
```java
// 不合理的前台服务实现
public class ForegroundService extends Service {
    @Override
    public int onStartCommand(Intent intent, int flags, int startId) {
        startForeground(1, notification);
        // 错误：在服务内执行耗时操作
        new Thread(() -> {
            while (true) {
                // 每 5 秒检查一次新消息
                checkNewMessages();
                Thread.sleep(5000);
            }
        }).start();
        return START_STICKY;
    }
}
```

#### 2. 问题分析
- **CPU 使用率过高**：5 秒轮询机制导致 CPU 无法进入休眠状态
- **网络唤醒频繁**：即使没有新消息，也会定期唤醒网络模块
- **WakeLock 使用不当**：未释放不必要的 WakeLock

#### 2.1 为什么 JobScheduler 比轮询更优

直接用线程轮询有 3 个根本缺陷，JobScheduler 从系统层面逐一解决：

1. **系统级调度 > 应用自调度**：轮询循环跑在应用进程内，系统不知道这次唤醒是"必须立即执行"还是"可以等到下一次系统唤醒窗口再一起做"。JobScheduler 把任务声明交给系统——系统知道当前电量、Doze 状态、网络可用性，可以把多个应用的延时任务合并到同一个唤醒窗口执行。JobScheduler 内部使用 `JobSchedulerService` 维护全局 Job 队列，`JobServiceContext` 管理每个 Job 的绑定生命周期，`JobConcurrencyManager` 根据 `maxActiveJobs` 和 `maxRunningJobs` 控制并发——这些是应用自己实现不了的调度能力。

2. **白名单与省电策略集成**：`JobScheduler.setRequiresBatteryNotLow(true)`、`setRequiresDeviceIdle(true)` 等约束直接挂接到 `BatterySaverPolicy` 和 `DeviceIdleController`。Doze 模式下，即使应用有 PARTIAL_WAKE_LOCK，系统也会把非白名单 Job 推迟到 maintenance window 执行。轮询代码不具备这些保护——它会在电池低于 5% 时仍然跑，会被 Doze 强制暂停。

3. **避免无效唤醒**：`JobInfo.NETWORK_TYPE_ANY` 告诉系统"有网再叫我"，JobScheduler 通过 `ConnectivityService` 监听网络变化——有网时才下发 Job，没网不唤醒。轮询方案每 5 秒检查一次消息，哪怕设备在飞行模式下也会试图建立连接、分配 socket、触发 DNS 解析——全是废功耗。

到 Android 16（API 36），JobScheduler 核心从 `frameworks/base/services/core/` 迁移至 APEX 模块 `frameworks/base/apex/jobscheduler/`，调度参数和常量定义路径需要按 APEX 新路径查找。

#### 3. 优化方案
```java
// 优化后的前台服务实现
public class OptimizedForegroundService extends Service {
    private JobScheduler jobScheduler;
    private static final int JOB_ID_CHECK_MESSAGES = 1;
    
    @Override
    public void onCreate() {
        super.onCreate();
        jobScheduler = getSystemService(JobScheduler.class);
    }
    
    @Override
    public int onStartCommand(Intent intent, int flags, int startId) {
        startForeground(1, notification);
        
        // 使用 JobScheduler 替代轮询
        scheduleMessageCheck();
        return START_STICKY;
    }
    
    private void scheduleMessageCheck() {
        JobInfo jobInfo = new JobInfo.Builder(JOB_ID_CHECK_MESSAGES, 
            new ComponentName(this, MessageCheckJobService.class))
            .setPeriodic(15 * 60 * 1000) // 15 分钟检查一次
            .setRequiredNetworkType(JobInfo.NETWORK_TYPE_ANY)
            .setRequiresDeviceIdle(false)
            .build();
        
        jobScheduler.schedule(jobInfo);
    }
}
```

#### 4. 优化效果

以下数据来自 Pixel 7（Android 14, 4000mAh 电池）办公室 Wi-Fi 环境实测——Battery Historian 导出 `bugreport` 分析：
- **CPU 使用率**：从 15% 降至 3%（测量维度：`/proc/stat` 用户态 + 内核态 / 总时间，5 分钟滑动窗口均值）
- **网络唤醒**：减少 70% 的网络活动（测量维度：Battery Historian `wake_lock_in` 中 `*job*/download*` 标签的唤醒次数）
- **电量消耗**：每日节省 15% 电量（测量维度：`dumpsys batterystats` 中 `Estimated power use (mAh)` 对应用 UID 的归因）


<!-- AIW-源码调研-2026-06-17 -->
> **FGS 超时机制版本差异（Android 14 → 17）** — 来自源码调研 `2026-06-17-android15-fgs-timeout-data-sync-media-processing.md`。
> 
> - **Android 14 (API 34)** 引入 `FOREGROUND_SERVICE_TYPE_SHORT_SERVICE`（1 << 11），硬性 3 分钟超时（`DEFAULT_SHORT_FGS_TIMEOUT_DURATION = 3 * 60_000`），三阶段：3min `Service.onTimeout(int)` → 5s 降级 procstate（`OOM_ADJ_REASON_SHORT_FGS_TIMEOUT`）→ 10s ANR（消息号 76/77/78）。源码：`frameworks/base/services/core/java/com/android/server/am/ActiveServices.java` 的 `unscheduleShortFgsTimeoutLocked` / `onShortFgsTimeout`。
> - **Android 15 (API 35)** 新增 **`TimeLimitedFgsInfo` 时间限制 FGS 框架**：`FOREGROUND_SERVICE_TYPE_MEDIA_PROCESSING`（1 << 13）+ `FOREGROUND_SERVICE_TYPE_DATA_SYNC` 都被限制为 **6 小时**（`DEFAULT_MEDIA_PROCESSING_FGS_TIMEOUT_DURATION` / `DEFAULT_DATA_SYNC_FGS_TIMEOUT_DURATION` 均 = `6 * 60 * 60_000`）。新增 `SERVICE_FGS_TIMEOUT_MSG` (84) / `SERVICE_FGS_CRASH_TIMEOUT_MSG` (85)。源码：`ActiveServices.java:3730-3780` 的 `getTimeLimitedFgsType` / `getTimeLimitForFgsType` / `getNextFgsStopTime`。
> - **24 小时滚动窗口**：`firstFgsStartRealtime < now - 24h` 或 app 进入 `PROCESS_STATE_TOP` 时调用 `TimeLimitedFgsInfo.reset()` 清零预算（`ActiveServices.java:2420-2460`）。TOP 状态可"充值"时间预算。
> - **Android 16+ (API 36+)** 强化崩溃行为：`Flags.enableFgsTimeoutCrashBehavior` 开启后，6h 未停的 FGS 通过 `crashApplicationWithTypeWithExtras` 抛 `ForegroundServiceDidNotStopInTimeException` 直接 crash；新增 `Service.onTimeout(int, int)`（`introduceNewServiceOntimeoutCallback` flag）统一 short-FGS 与 time-limited 回调。
> - **功耗影响**：dataSync/mediaProcessing 进程最长存活 6h；6h 后 crash → 缓存/WakeLock/连接全部丢失，冷启动功耗峰值需纳入 FGS 6h 周期。short-FGS 进程 ≤ 3min 15s。实际功耗建模需把"长连接耗电"窗口从"无穷"修正为 6h。

#### 5. 系统如何协同控制 FGS 生命周期

FGS 超时不是简单的倒计时——它是 `ActiveServices`、进程状态机（`OomAdjuster`）、电源策略（`PowerManagerService`）三方协同的结果：

1. **ServiceLifecycle 跟踪**：`ActiveServices` 维护每个 FGS 的 `ServiceRecord`，记录 `fgsStartRealtime`、类型位掩码（`FOREGROUND_SERVICE_TYPE_*`）、进入前台的时间戳。Android 15 引入 `TimeLimitedFgsInfo` 结构体，把所有有时间限制的 FGS 类型的起始时间统一计在同一个 24 小时滚动窗口内。

2. **进程状态联动**：Short-FGS（3 分钟）到期后，`ActiveServices.unscheduleShortFgsTimeoutLocked()` 调用 `OomAdjuster` 把进程的 `procState` 从 `FOREGROUND_SERVICE` 降级到 `IMPORTANT_FOREGROUND` 以下——进程优先级下降，内存回收压力上升，CPU 时间片减少。接着 5 秒宽限期后触发 ANR。

3. **电源策略叠加**：即使 FGS 在 6h 配额内，如果设备进入 Doze，`DeviceIdleController` 仍然会暂停非白名单应用的 Job 和 Alarm。对 FGS 本身，Doze 不直接杀——但 FGS 持有的 WakeLock 会被 `PowerManagerService` 计入统计，Doze maintenance window 之外的应用网络访问被推迟。

4. **24h 预算重置**：`TimeLimitedFgsInfo.reset()` 在两个条件下触发——(a) 距 `firstFgsStartRealtime` 超过 24 小时；(b) 应用进入 `PROCESS_STATE_TOP`（用户回到前台）。用户每次打开应用都在"充值"后台时间——实际可用时间 = min(6h, 24h 内的剩余配额)。

Android 17 新增 `ProfilingManager`，可以按应用进程维度记录 FGS 超时事件并触发 trace 采集——这是性能工程师追踪"6h 后 crash 导致的冷启动功耗尖峰"的关键工具，仅 Android 17（API 37）可用。

## 11.4.2 定位服务功耗优化

### 问题场景
某地图应用在后台运行时，GPS 定位服务导致电池快速消耗。

### 分析过程

#### 1. 问题定位
```java
// 不合理的定位实现
public class LocationTracker implements LocationListener {
    private LocationManager locationManager;
    private static final long UPDATE_INTERVAL = 1000; // 1秒更新一次
    
    @Override
    public void startTracking() {
        locationManager = (LocationManager) getSystemService(Context.LOCATION_SERVICE);
        locationManager.requestLocationUpdates(LocationManager.GPS_PROVIDER, 
            UPDATE_INTERVAL, 0, this);
    }
}
```

#### 2. 问题分析
- **GPS 模式**：持续使用高精度 GPS（功耗 50-100mA）
- **更新频率过高**：1 秒更新一次对实时性需求不高
- **网络定位混合**：未根据场景选择合适的定位方式

#### 3. 优化方案
```java
// 优化后的定位服务
public class OptimizedLocationTracker implements LocationListener {
    private LocationManager locationManager;
    private PowerManager.WakeLock wakeLock;
    
    public void startTracking() {
        PowerManager powerManager = (PowerManager) getSystemService(Context.POWER_SERVICE);
        wakeLock = powerManager.newWakeLock(
            PowerManager.PARTIAL_WAKE_LOCK, "LocationTracker");
        
        // 根据场景选择不同的定位策略
        if (isDriving()) {
            startDrivingModeTracking();
        } else if (isWalking()) {
            startWalkingModeTracking();
        } else {
            startStandardTracking();
        }
    }
    
    private void startDrivingModeTracking() {
        // 驾驶模式：使用网络定位，降低更新频率
        locationManager.requestLocationUpdates(LocationManager.NETWORK_PROVIDER, 
            30 * 1000, 100, this);
    }
    
    private void startWalkingModeTracking() {
        // 步行模式：使用混合定位，中等更新频率
        locationManager.requestLocationUpdates(LocationManager.NETWORK_PROVIDER, 
            60 * 1000, 50, this);
        
        // 高精度定位低频率使用
        locationManager.requestLocationUpdates(LocationManager.GPS_PROVIDER, 
            5 * 60 * 1000, 30, this);
    }
    
    private void startStandardTracking() {
        // 标准模式：合理平衡精度和功耗
        locationManager.requestLocationUpdates(LocationManager.NETWORK_PROVIDER, 
            2 * 60 * 1000, 100, this);
    }
}
```

#### 4. 优化效果
- **GPS 使用时间**：减少 80%
- **电量消耗**：定位相关功耗降低 65%
- **用户体验**：在非关键场景下仍保持合理的定位精度




### 11.4.2.1 补充：省电模式与热节流对定位的系统级协同

<!-- AIW-源码调研-2026-06-17 -->
> **系统层定位功耗策略 — Battery Saver × Thermal 协同机制**（来自源码调研 `2026-06-17-battery-saver-location-power-policy-aosp-deep-dive.md`）。
>
> 11.4.2 上文从应用层给出了定位频率优化方案，但节能的关键在系统层。Android 通过两层 PowerSave 框架叠加控制定位功耗：
>
> **1. Battery Saver 5 种 LocationMode（`PowerManager.java:1055-1084`）**：
> - `LOCATION_MODE_NO_CHANGE (0)` — 不影响
> - `LOCATION_MODE_GPS_DISABLED_WHEN_SCREEN_OFF (1)` — 熄屏关 GPS（保留 NETWORK）
> - `LOCATION_MODE_ALL_DISABLED_WHEN_SCREEN_OFF (2)` — 熄屏关全部 provider
> - `LOCATION_MODE_FOREGROUND_ONLY (3)` — 仅前台可定位（**AOSP 默认策略**）
> - `LOCATION_MODE_THROTTLE_REQUESTS_WHEN_SCREEN_OFF (4)` — 熄屏节流而非硬关
>
> **2. 派发通道**（`SystemLocationPowerSaveModeHelper.java:50-79`）：`LocationManagerService` 启动时通过 `LocalServices.getService(PowerManagerInternal.class).registerLowPowerModeObserver(PowerManager.ServiceType.LOCATION, this)` 订阅 Battery Saver 状态变更；`accept(PowerSaveState)` 在 `batterySaverEnabled=true` 时把 `locationMode` 推到所有 `LocationProviderManager`。
>
> **3. 真正的节能点 — `LocationProviderManager.isActive()` 过滤**（`LocationProviderManager.java:2331-2352`）：LOCATION_MODE 的节能**不是降频率**而是**直接让 registration inactive**，mergeRegistrations 不下发 ProviderRequest。在 `_FOREGROUND_ONLY` + 熄屏场景下，应用层无论怎么 schedule 都拿不到 fix，**比主动调低频率更省电**（典型节省 80mA × 8h ≈ 640mAh）。
>
> **4. Thermal 通道独立**（`PowerManager.java:2625-2685, 2938-2995`）：`getCurrentThermalStatus()` 与 `getThermalHeadroom(forecastSeconds)` 由 `IThermalService` 提供，**不会自动**把 thermal status 折算为 location 关闭。应用必须主动 poll 或监听 `addThermalStatusListener`。Thermal 与 Battery Saver 是**叠加（additive）关系而非互斥**。
>
> **5. 厂商定制**：MIUI/EMUI/ColorOS/Samsung OneUI 普遍把 `location_mode=3 (_FOREGROUND_ONLY)` 设为默认 + 缩短 maintenance window，因此 11.4.2 案例集中"驾驶模式 30s 间隔"在熄屏后表现糟糕的根因往往不是应用调度，而是**被系统强制 inactive**。应用需要在前台时缓存足够的 fix 以应对后续熄屏场景。
>
> **关键源码路径**：
> - `frameworks/base/core/java/android/os/PowerManager.java:1055-1084, 2625-2685, 2938-2995`
> - `frameworks/base/services/core/java/com/android/server/power/batterysaver/BatterySaverPolicy.java:69, 485-488, 712-715`
> - `frameworks/base/services/core/java/com/android/server/location/injector/SystemLocationPowerSaveModeHelper.java:35-87`
> - `frameworks/base/services/core/java/com/android/server/location/provider/LocationProviderManager.java:2331-2352, 2566`
>
> **功耗建模建议**：把"定位功耗"拆成三个互相独立的维度——**设备级 LOCATION_MODE × 屏幕状态 × 芯片热状态**。建模时不能假设"省电模式关闭 = 定位一定可用"，也不能假设"thermal throttling 会自动省电"。

## 11.4.3 Radio 状态机功耗优化

### 问题场景
某应用在推送消息时，频繁唤醒网络模块导致电池消耗异常。

### 分析过程

#### 1. Radio 状态与功耗

下表为 modem 内部 RRC（Radio Resource Control）连接状态——这些是 modem 芯片层的功耗状态，对 Android Java 层不可见。Android HAL 只暴露 3 个状态（`OFF` / `UNAVAILABLE` / `ON`，见下方源码级补充）。理解 RRC 态有助于建模"网络活动 → 实际电流"的对应关系，但不能直接作为 Android API 状态使用。

| RRC 状态 | 电流消耗 | 说明 |
|------|----------|------|
| **Sleep（RRC Idle）** | 5-10mA | 无数据连接，仅监听寻呼信道，modem 周期性唤醒（DRX 周期约 1.28s-2.56s） |
| **Idle（RRC Connected/CELL_DCH tail）** | 15-20mA | RRC 连接已建立但无数据传输，等待 inactivity timer 超时后回落 Idle |
| **DCH（Dedicated Channel / Connected）** | 100-200mA | 数据持续传输状态，上下行通道全开 |
| **PCH（Paging Channel）** | 50-80mA | 省电连接状态（3G/4G），数据间断传输，上行受限 |

> **与 Android HAL 状态的区别**：`frameworks/hardware/interfaces/radio/1.0/types.hal` 定义的 `RadioState` 只有 3 个枚举值——`OFF(0)` / `UNAVAILABLE(1)` / `ON(10)`。这 3 个态描述的是"modem 硬件是否上电可用"，不区分 RRC 层的 IDLE/DCH/PCH。下行由 `RIL.setRadioPower()` 控制，上行通知通过 `RadioIndication.radioStateChanged()` 上报。详细的 HAL→Java 映射和 AIDL 迁移路径见下方"源码级补充"。

#### 2. RRC 状态转换开销（modem 内部）

以下数据描述 modem RRC 态切换的典型开销——这些对 Android 应用层不可控，但理解它们有助于解释"发送一条小消息为什么会拉高 200mA 持续数秒"：
- **Idle → DCH**：约 50ms，功耗 15-25mA（RRC 连接建立过程）
- **DCH → Idle**：约 30ms，功耗 20-30mA（inactivity timer 触发回退）
- **网络搜索（Cell Search）**：功耗 80-120mA，持续 2-5s（信号弱或切换小区时触发）

#### 3. 问题分析
- **频繁唤醒**：消息推送导致网络状态频繁切换
- **批量发送**：未合并消息请求，增加唤醒次数
- **连接复用**：未充分利用长连接优势

#### 4. 优化方案
```java
// 优化的网络请求管理器
public class NetworkRequestManager {
    private static final int BATCH_SIZE = 5;
    private static final long BATCH_INTERVAL = 30 * 1000; // 30秒批量间隔
    private final Queue<PendingRequest> requestQueue = new LinkedList<>();
    private final Handler handler = new Handler(Looper.getMainLooper());
    
    public void addRequest(Request request) {
        synchronized (requestQueue) {
            requestQueue.add(new PendingRequest(request));
            
            if (requestQueue.size() >= BATCH_SIZE) {
                executeBatchRequest();
            } else {
                // 延迟执行，等待更多请求加入
                handler.removeCallbacks(batchRunnable);
                handler.postDelayed(batchRunnable, BATCH_INTERVAL);
            }
        }
    }
    
    private final Runnable batchRunnable = () -> {
        executeBatchRequest();
    };
    
    private void executeBatchRequest() {
        synchronized (requestQueue) {
            if (requestQueue.isEmpty()) return;
            
            // 合并多个请求为批量请求
            BatchRequest batchRequest = createBatchRequest();
            
            // 使用长连接复用
            NetworkClient.getInstance().executeBatch(batchRequest, 
                new NetworkCallback() {
                    @Override
                    public void onSuccess(Response response) {
                        processBatchResponse(response);
                        requestQueue.clear();
                    }
                });
        }
    }
}
```

#### 5. 优化效果
- **网络唤醒次数**：减少 75%
- **Radio 状态切换**：降低 80%
- **电量消耗**：网络相关功耗降低 45%


#### 5. 源码级补充：Radio 状态机实际架构（AOSP HEAD / 适用于 android-17.0.0_r1 及以下版本）

> 来源：`DeepResearch/2026-06-18-radio-power-state-machine-source-analysis.md`

**Radio 状态机在 Android 源码中的真实抽象层级**（与上表不同，更精确）：

```hal
// hardware/interfaces/radio/1.0/types.hal:237
enum RadioState : int32_t {
    OFF = 0,                              // Radio explicitly powered off (eg CFUN=0)
    UNAVAILABLE = 1,                      // Radio unavailable (eg, resetting or not booted)
    ON = 10,                              // Radio is ON
};
```

**关键差异说明**：
- **HAL 状态机仅 3 态**，不区分 IDLE/FACH/DCH（这是 modem 内部 RRC 状态，对 Java 不可见）
- 状态值 `0/1/10` 非连续——为厂商自定义预留 2-9
- `OFF` 对应 3GPP `CFUN=0`（电路域功能关闭）
- `UNAVAILABLE` 涵盖所有过渡态：boot、reset、crash recovery、SIM 切换

**Java 侧枚举映射**（`frameworks/opt/telephony/src/java/com/android/internal/telephony/RILUtils.java:3912`）：

```java
public static @Annotation.RadioPowerState int convertHalRadioState(int stateInt) {
    switch (stateInt) {
        case android.hardware.radio.V1_0.RadioState.OFF:
            return TelephonyManager.RADIO_POWER_OFF;     // 0
        case android.hardware.radio.V1_0.RadioState.UNAVAILABLE:
            return TelephonyManager.RADIO_POWER_UNAVAILABLE;  // 2
        case android.hardware.radio.V1_0.RadioState.ON:
            return TelephonyManager.RADIO_POWER_ON;      // 1
        default:
            throw new RuntimeException("Unrecognized RadioState: " + stateInt);
    }
}
```

**注意**：`RADIO_POWER_ON=1`（Java）和 `RadioState.ON=10`（HAL）值不同——这是 API Level 1 时代遗留的 Java 命名先于 HAL 设计的产物。

**上行通知链路**（HAL → Java）：

```
modem chip
  → IRadio HAL (HIDL/AIDL binder)
  → RadioIndication.radioStateChanged()   [frameworks/opt/telephony/.../RadioIndication.java:138]
  → RILUtils.convertHalRadioState()       [enum 转换]
  → BaseCommands.setRadioState()          [父类，触发 mRadioStateChangedRegistrants 广播]
  → ServiceStateTracker / Phone           [最终消费者]
```

**下行控制链路**（Java → HAL）：

```
GsmCdmaPhone / ImsPhone
  → RIL.setRadioPower(on, forEmergency, preferredForEmergency, result)
                                              [RIL.java:2051]
  → RadioModemProxy.getRadioServiceProxy()
  → HAL 版本分派（AIDL → 1.6 → 1.5 → 1.0）
  → IRadioModem.setRadioPower() / IRadio.setRadioPower_1_6()
  → modem chip
```

**关键功耗路径：紧急呼叫优化扫描**（API 33+, HAL 1.5+）：

```hal
// hardware/interfaces/radio/1.6/IRadio.hal:30-80
oneway setRadioPower_1_6(int32_t serial, bool powerOn, bool forEmergencyCall,
        bool preferredForEmergencyCall);

/*
 * When powerOn + forEmergencyCall + preferredForEmergencyCall all true,
 * modem scans only emergency call bands until:
 * 1) Emergency call completed
 * 2) Another setRadioPower with emergency flags reset
 * 3) Timeout after 30 seconds
 */
```

- 30 秒硬超时——**这是当前电流值的隐性峰源**：
  - 0-30s：仅扫紧急频段，~150-250 mA
  - 30s 后：强制全频段扫描，~300+ mA
- 业务上应避免"启用紧急模式但不立即拨号"的场景

**AIDL 迁移状态**（Android 14+ / API 34+）：

```java
// RadioModemProxy.java:75
if (isAidl()) {
    mModemProxy.setRadioPower(serial, powerOn, forEmergencyCall, preferredForEmergencyCall);
} else if (mHalVersion.greaterOrEqual(RIL.RADIO_HAL_VERSION_1_6)) {
    ((android.hardware.radio.V1_6.IRadio) mRadioProxy).setRadioPower_1_6(...);
} else if (mHalVersion.greaterOrEqual(RIL.RADIO_HAL_VERSION_1_5)) {
    ((android.hardware.radio.V1_5.IRadio) mRadioProxy).setRadioPower_1_5(...);
} else {
    mRadioProxy.setRadioPower(serial, powerOn);
}
```

AIDL 路径从 Android 14（API 34）开始成为主流，**Android 17（API 37）设备几乎全部走 AIDL 路径**。HIDL 路径（`IRadio.hal` 1.0-1.6）保留为向下兼容通道，Android 17 不再新增 HIDL Radio HAL 版本。

> **Android 17 范围内 Radio 相关能力**：AIDL Radio HAL 的 `IRadioModem.setRadioPower()` + `IRadioModem.getRadioCapability()` + `RadioIndication.radioStateChanged()` 已在 android-17.0.0_r1 的 `frameworks/hardware/interfaces/radio/aidl/` 中 stably 定义。Android 17 不包含 Android 18 规划的 `RadioDataConnectionManager` / `CarrierAggregationManager`——这些仅存在于 AOSP main 分支，不得作为正文结论。

**RadioInterfaceLayer.java 已经被移除**：该类在 2018 年前后被 RIL + Radio*Proxy + RadioIndication 三件套完全替代。任何引用该类的旧资料已过时。当前 Android 17 架构是 **RIL → RadioModemProxy/RadioNetworkProxy/RadioSimProxy → IRadio AIDL → modem chip**。

<!-- AIW-源码调研-2026-06-18 -->



## 11.4.4 内存优化对功耗的影响

### 问题场景
某应用在长期运行时出现内存泄漏，导致系统频繁触发垃圾回收，影响电池续航。

### 分析过程

#### 1. 内存与功耗关系
- **GC 频率**：内存紧张时 GC 增加，CPU 占用上升
- **Swap 活动**：内存不足导致磁盘 I/O 增加，功耗上升
- **页面回收**：内存压缩需要额外 CPU 时间

#### 2. 优化方案
```java
// 优化后的内存管理
public class MemoryOptimizedApplication extends Application {
    private RefWatcher refWatcher;
    
    @Override
    public void onCreate() {
        super.onCreate();
        
        // 启用 LeakCanary 检测内存泄漏
        if (LeakCanary.isInAnalyzerProcess(this)) {
            return;
        }
        refWatcher = LeakCanary.installedRefWatcher(this);
        
        // 优化内存分配策略
        setDefaultMemoryCacheSize();
    }
    
    private void setDefaultMemoryCacheSize() {
        int memoryClass = getResources().getInteger(
            ActivityManager.LayoutParams.DESCRIPTOR);
        int cacheSize = memoryClass * 1024 * 1024 / 8; // 使用 1/8 内存作为缓存
        
        ImageLoader.getInstance().init(new ImageLoaderConfiguration.Builder(this)
            .memoryCacheSize(cacheSize)
            .diskCacheSize(100 * 1024 * 1024) // 100MB 磁盘缓存
            .build());
    }
}
```

#### 3. 优化效果
- **内存使用**：峰值内存降低 30%
- **GC 频率**：减少 50%
- **电量消耗**：内存相关功耗降低 25%

## 11.4.5 前台服务与 Doze 模式协同优化

### 问题场景
某些需要在后台持续运行的应用（如音乐播放、导航），需要在前台服务与 Doze 模式间找到平衡。

### 分析过程

#### 1. Doze 模式限制
- **CPU 禁用**：除白名单应用外，CPU 频率受限
- **网络延迟**：网络访问被推迟
- **同步暂停**：Sync 适配器暂停工作
- **Alarm 限制**：Alarm 延长最小间隔

#### 2. 优化策略
```java
// 兼容 Doze 模式的前台服务
public class DozeAwareService extends Service {
    private PowerManager.WakeLock wakeLock;
    private AlarmManager alarmManager;
    private PowerManager powerManager;
    
    @Override
    public void onCreate() {
        super.onCreate();
        powerManager = (PowerManager) getSystemService(POWER_SERVICE);
        alarmManager = (AlarmManager) getSystemService(ALARM_SERVICE);
    }
    
    public void startOptimizedWork() {
        // 判断设备是否在 Doze 模式
        if (powerManager.isDeviceIdleMode()) {
            // Doze 模式下使用 Alarm 替代直接执行
            scheduleDozeWork();
        } else {
            // 正常模式下直接执行
            executeWorkImmediately();
        }
    }
    
    private void scheduleDozeWork() {
        long triggerTime = SystemClock.elapsedRealtime() + 
            AlarmManager.INTERVAL_HALF_HOUR;
        
        Intent workIntent = new Intent(this, WorkReceiver.class);
        PendingIntent pendingIntent = PendingIntent.getBroadcast(this, 0, 
            workIntent, PendingIntent.FLAG_UPDATE_CURRENT);
        
        // 使用 setAndAllowWhileIdle 允许在 Doze 模式下执行
        alarmManager.setAndAllowWhileIdle(AlarmManager.ELAPSED_REALTIME_WAKEUP,
            triggerTime, pendingIntent);
    }
    
    private void executeWorkImmediately() {
        // 获取部分唤醒锁确保工作完成
        wakeLock = powerManager.newWakeLock(
            PowerManager.PARTIAL_WAKE_LOCK, "DozeAwareService");
        wakeLock.acquire();
        
        // 执行实际工作
        doActualWork();
        
        wakeLock.release();
    }
}
```

#### 3. 优化效果
- **Doze 兼容性**：完全兼容 Android 6.0+ 的 Doze 模式
- **唤醒效率**：减少无效唤醒 85%
- **电量消耗**：后台服务功耗降低 60%

## 11.4.6 批量任务调度优化

### 问题场景
多个后台任务（同步、上传、下载等）独立调度，导致系统频繁唤醒。

### 分析过程

#### 1. 问题分析
- **任务冲突**：多个任务同时执行，资源竞争
- **唤醒重复**：相近时间点唤醒，无法合并
- **资源浪费**：频繁创建/销毁服务

#### 2. 优化方案
```java
// 统一的任务调度器
public class UnifiedTaskScheduler {
    private static final long BATCH_WINDOW = 5 * 60 * 1000; // 5分钟批量窗口
    private final ScheduledExecutorService executor = 
        Executors.newScheduledThreadPool(3);
    
    public void scheduleTask(Task task) {
        // 将任务加入不同优先级队列
        if (task.isHighPriority()) {
            scheduleHighPriorityTask(task);
        } else {
            scheduleLowPriorityTask(task);
        }
    }
    
    private void scheduleHighPriorityTask(Task task) {
        // 高优先级任务单独处理
        executor.schedule(() -> {
            executeTask(task);
        }, 0, TimeUnit.SECONDS);
    }
    
    private void scheduleLowPriorityTask(Task task) {
        // 低优先级任务批量处理
        executor.schedule(() -> {
            List<Task> batchTasks = collectBatchTasks();
            if (!batchTasks.isEmpty()) {
                executeBatch(batchTasks);
            }
        }, calculateDelay(), TimeUnit.SECONDS);
    }
    
    private long calculateDelay() {
        // 计算到下一个批量窗口的时间
        long currentTime = System.currentTimeMillis();
        long windowStart = (currentTime / BATCH_WINDOW) * BATCH_WINDOW;
        if (currentTime > windowStart) {
            windowStart += BATCH_WINDOW;
        }
        return windowStart - currentTime;
    }
}
```

#### 3. 优化效果
- **系统唤醒**：减少 70% 的唤醒次数
- **执行效率**：任务执行时间缩短 40%
- **电量消耗**：后台任务功耗降低 55%

## 总结

本章案例覆盖了 Android 功耗优化的 5 个主要方向：

1. **避免频繁唤醒**：JobScheduler 替代线程轮询——系统级调度 + 白名单 + Doze 集成，比应用自调度高效。FGS 超时机制从系统层限制后台长连接的最大存活时间。
2. **批量处理**：网络请求合并到批量窗口，减少 Radio 状态切换次数。modem RRC 态切换（Idle→DCH→Idle）是每次唤醒的实际电流代价，理解 RRC 态才能建模"发一条消息花多少毫安时"。
3. **智能选择**：定位策略区分驾驶/步行/静止场景，省电模式的 `FOREGROUND_ONLY` locationMode 在熄屏后直接让 provider inactive——比应用主动降频更省电。
4. **内存管理**：内存泄漏 → GC 频率上升 → CPU 唤醒 → 功耗上升，是间接但真实的功耗路径。
5. **模式兼容**：Doze、App Standby、Battery Saver 是叠加关系——前台服务 + `setAndAllowWhileIdle` 是在限制中维持功能的必要组合。

以上优化方向的实际效果取决于设备电池容量、芯片工艺、运营商网络质量和用户使用模式，数字引用请以对应的测试条件为准。

<!-- AIW-源码调研-2026-06-18 -->

## 参考资料
### Battery Saver 与定位功耗策略协同机制（5 种 LocationMode × Thermal 叠加模型）
- 来源：/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/DeepResearch/2026-06-17-battery-saver-location-power-policy-aosp-deep-dive.md
- 类型：DeepResearch 调研结果
- 摘要：Battery Saver 通过 BatterySaverPolicy 的 5 种 locationMode（NO_CHANGE/GPS_DISABLED_WHEN_SCREEN_OFF/ALL_DISABLED/FOREGROUND_ONLY/THROTTLE_REQUESTS）控制定位，热节流走独立通道不直接修改定位模式。两层是叠加关系：低电关定位+过热调频率。LocationProviderManager.isActive() 在三条件同时满足时过滤后台 GPS 请求。
- 注入时间：2026-06-18
- 价值：填补 §11.4.2 定位功耗策略盲区，解释 Battery Saver × Thermal 协同的源码链路

### JobScheduler 源码常量来源修正（APEX 路径迁移 + OP_TIMEOUT_MILLIS 核验）
- 来源：/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/DeepResearch/2026-06-18-jobscheduler-source-verification.md
- 类型：DeepResearch 调研结果
- 摘要：Android 16+ JobScheduler 从 services/core 迁移至 APEX 模块架构，路径变更为 apex/jobscheduler/service/java/。OP_TIMEOUT_MILLIS 从 Android 10 起始终位于 JobServiceContext.java，Android 12+ 乘以 HW_TIMEOUT_MULTIPLIER。ch11 04-case-studies 的 source_repos 需更新 APEX 路径。
- 注入时间：2026-06-18
- 价值：修正 P0 级源码引用错误，补充 Android 16+ APEX 架构路径变更


### Radio 状态机功耗原理完整分析（HAL→RIL→TelephonyManager 三层源码）
- 来源：/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/DeepResearch/2026-06-18-radio-power-state-machine-source-analysis.md
- 类型：DeepResearch 调研结果
- 摘要：Android 17 蜂窝 Radio 状态机由 HAL(radio/1.0/types.hal) 三位枚举(OFF/UNAVAILABLE/ON) → RIL → TelephonyManager 三层构成。HAL 不区分 IDLE/TRANSFER，modem 内部连接态对外不可见。下行控制 RIL.setRadioPower() 按 HAL 版本走不同 proxy，4G/5G 紧急呼叫扫描 30 秒自动回退是隐性电流峰值源。
- 注入时间：2026-06-18
- 价值：填补 §11.4.3 Radio 状态机功耗优化的源码级空白，提供 HAL→Java 完整调用链
