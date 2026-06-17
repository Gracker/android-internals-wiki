---
title: "案例集"
weight: 4
applicable_versions: [Android 14.0 (API 34) - Android 16 (API 36)]
source_repos: 
  - frameworks/base/core/java/android/os/PowerManager.java
  - frameworks/base/services/core/java/com/android/server/power/PowerManagerService.java
  - frameworks/base/core/java/android/os/BatteryStats.java
status: ready-for-review
task9_state: reviewed
task6_result: pass-light-edit
pipeline_stage: task6_pending
---

# 11.4 案例集

本章节将通过实际案例深入分析 Android 功耗优化的实践方法，从系统到应用层面提供可落地的解决方案。

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
- **CPU 使用率**：从 15% 降至 3%
- **网络唤醒**：减少 70% 的网络活动
- **电量消耗**：每日节省 15% 电量


<!-- AIW-源码调研-2026-06-17 -->
> **FGS 超时机制版本差异（Android 14 → 17）** — 来自源码调研 `2026-06-17-android15-fgs-timeout-data-sync-media-processing.md`。
> 
> - **Android 14 (API 34)** 引入 `FOREGROUND_SERVICE_TYPE_SHORT_SERVICE`（1 << 11），硬性 3 分钟超时（`DEFAULT_SHORT_FGS_TIMEOUT_DURATION = 3 * 60_000`），三阶段：3min `Service.onTimeout(int)` → 5s 降级 procstate（`OOM_ADJ_REASON_SHORT_FGS_TIMEOUT`）→ 10s ANR（消息号 76/77/78）。源码：`frameworks/base/services/core/java/com/android/server/am/ActiveServices.java` 的 `unscheduleShortFgsTimeoutLocked` / `onShortFgsTimeout`。
> - **Android 15 (API 35)** 新增 **`TimeLimitedFgsInfo` 时间限制 FGS 框架**：`FOREGROUND_SERVICE_TYPE_MEDIA_PROCESSING`（1 << 13）+ `FOREGROUND_SERVICE_TYPE_DATA_SYNC` 都被限制为 **6 小时**（`DEFAULT_MEDIA_PROCESSING_FGS_TIMEOUT_DURATION` / `DEFAULT_DATA_SYNC_FGS_TIMEOUT_DURATION` 均 = `6 * 60 * 60_000`）。新增 `SERVICE_FGS_TIMEOUT_MSG` (84) / `SERVICE_FGS_CRASH_TIMEOUT_MSG` (85)。源码：`ActiveServices.java:3730-3780` 的 `getTimeLimitedFgsType` / `getTimeLimitForFgsType` / `getNextFgsStopTime`。
> - **24 小时滚动窗口**：`firstFgsStartRealtime < now - 24h` 或 app 进入 `PROCESS_STATE_TOP` 时调用 `TimeLimitedFgsInfo.reset()` 清零预算（`ActiveServices.java:2420-2460`）。TOP 状态可"充值"时间预算。
> - **Android 16+ (API 36+)** 强化崩溃行为：`Flags.enableFgsTimeoutCrashBehavior` 开启后，6h 未停的 FGS 通过 `crashApplicationWithTypeWithExtras` 抛 `ForegroundServiceDidNotStopInTimeException` 直接 crash；新增 `Service.onTimeout(int, int)`（`introduceNewServiceOntimeoutCallback` flag）统一 short-FGS 与 time-limited 回调。
> - **功耗影响**：dataSync/mediaProcessing 进程最长存活 6h；6h 后 crash → 缓存/WakeLock/连接全部丢失，冷启动功耗峰值需纳入 FGS 6h 周期。short-FGS 进程 ≤ 3min 15s。实际功耗建模需把"长连接耗电"窗口从"无穷"修正为 6h。

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
> 11.4.2 上文从应用层给出了定位频率优化方案，但**真正的节能闭环在系统层**。Android 通过两层 PowerSave 框架叠加控制定位功耗：
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

| 状态 | 电流消耗 | 说明 |
|------|----------|------|
| **Sleep Mode** | 5-10mA | 低功耗待机状态 |
| **Idle Mode** | 15-20mA | 基础连接维持状态 |
| **DCH (Connected)** | 100-200mA | 数据连接活跃状态 |
| **PCH (Power Saving)** | 50-80mA | 省电模式连接状态 |

#### 2. 状态转换开销
- **Idle → DCH**：约 50ms，功耗 15-25mA
- **DCH → Idle**：约 30ms，功耗 20-30mA
- **网络搜索**：功耗 80-120mA，持续 2-5s

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

通过以上案例可以看出，Android 功耗优化的关键在于：

1. **避免频繁唤醒**：合理使用 JobScheduler、AlarmManager 等机制
2. **批量处理**：合并网络请求、IO 操作等任务
3. **智能选择**：根据场景选择合适的定位、网络等资源使用方式
4. **内存管理**：避免内存泄漏，减少 GC 压力
5. **模式兼容**：充分考虑 Doze 模式、应用待机等系统限制

这些优化方案可以显著降低应用的电量消耗，同时保持良好的用户体验。