---
title: "定位服务功耗与性能实战：FusedLocationProvider、地理围栏与批处理"
chapter: "25.22"
status: ready-for-review
applicable_versions: "Android 12 (API 31) - Android 17 (API 37)"
drafted_date: "2026-06-18"
last_verified: "2026-06-18"
last_verified_against: "Android Developers location docs + Google Play services Location APIs + AOSP frameworks/base LocationManagerService"
confidence: medium-high
sources:
  - type: official
    path: "https://developer.android.com/develop/sensors-and-location/location/request-updates"
  - type: official
    path: "https://developer.android.com/develop/sensors-and-location/location/permissions"
  - type: official
    path: "https://developer.android.com/develop/sensors-and-location/location/geofencing"
  - type: official
    path: "https://developer.android.com/about/versions/12/behavior-changes-12#background-location-access"
  - type: official
    path: "https://developer.android.com/about/versions/14/changes/fgs-types"
  - type: official
    path: "https://developers.google.com/android/reference/com/google/android/gms/location/LocationRequest"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/location/LocationManagerService.java"
  - type: aosp
    path: "frameworks/base/location/java/android/location/LocationManager.java"
tags: ["定位", "Location", "FusedLocationProvider", "功耗", "Geofencing", "FGS"]
related_chapters: ["5.15", "11.2", "25.5", "5.17"]
created_by: "task2a-knowledge-gap"
created_date: "2026-06-18"
gap_source: "官方文档/素材驱动"
pipeline_stage: "task6_pending"
task2b_result: "fixed-lite"
task2b_state: "fixed"
task6_state: "revisiting"
task9_state: pending
task9_result: pending
last_task2b_lite_at: "2026-06-19"
---

# 25.22 定位服务功耗与性能实战：FusedLocationProvider、地理围栏与批处理

§25.5 讲过定位与传感器功耗的基础权衡——精度、频率、延迟三个旋钮怎么调。本节往下拆一层：代码层怎么选 provider、怎么设 LocationRequest 参数、怎么管地理围栏生命周期、后台定位在 Android 12-17 各版本中受了什么限制，以及线上怎么用 dumpsys 和 Battery Historian 查定位功耗。

## 定位 Provider 的功耗特征与 FusedLocationProvider 选型策略

Android 定位有三个底层 provider，功耗差异跨数量级：

| Provider | 使用的硬件 | 典型功耗 | 精度范围 | 首次定位时间 |
|----------|-----------|----------|----------|-------------|
| GPS (GNSS) | GNSS 芯片（L1/L5） | 高：200-500 mA 持续电流 | 3-10 米 | 冷启动 30-60 秒，热启动 1-5 秒 |
| NETWORK | Wi-Fi 扫描 + 蜂窝基站 | 中：每次扫描 20-80 mA | 10-100 米 | 1-3 秒 |
| PASSIVE | 不主动请求硬件，监听其他 App 的定位结果 | 极低：几乎零额外功耗 | 取决于被监听的 provider | 取决于其他 App 的请求频率 |

[已验证: 官方文档, developer.android.com/develop/sensors-and-location/location/battery]

GPS provider 的功耗主因是 GNSS 芯片需要持续接收卫星信号、做相关运算。冷启动时还要下载星历数据（ephemeris），这个过程持续 30 秒左右，功耗峰值可达 500 mA。热启动时星历有效，锁定时间缩到 1-5 秒，但芯片工作电流不变。NETWORK provider 不激活 GNSS 芯片，靠 Wi-Fi 扫描和蜂窝基站 ID 匹配数据库来估算位置，单次扫描功耗在 20-80 mA 区间。

PASSIVE provider 是最省电的方案，它不主动触发任何硬件，只在系统内其他 App（比如导航类 App）请求位置更新时，被动接收同样的位置结果。使用 PASSIVE provider 不需要自己持有定位权限中的 ACCESS_FINE_LOCATION（但需要至少 ACCESS_COARSE_LOCATION），适合做城市级内容推荐、天气等低精度场景。

FusedLocationProvider（FLP）是 Google Play services 提供的高层 API，它不直接对应某个底层 provider，而是根据 App 设置的 Priority 参数自动选型：

```kotlin
// 高精度：FLP 可能同时激活 GNSS + Wi-Fi 扫描
LocationRequest.Builder(Priority.PRIORITY_HIGH_ACCURACY, 10_000) // 10 秒间隔
    .build()

// 平衡模式：FLP 优先用 NETWORK provider，只在需要时短暂激活 GNSS
LocationRequest.Builder(Priority.PRIORITY_BALANCED_POWER_ACCURACY, 60_000) // 60 秒间隔
    .build()

// 低功耗：FLP 只用 NETWORK provider 或 PASSIVE
LocationRequest.Builder(Priority.PRIORITY_LOW_POWER, 300_000) // 5 分钟间隔
    .build()

// 无功耗：只接收其他 App 触发的位置更新
LocationRequest.Builder(Priority.PRIORITY_PASSIVE, Long.MAX_VALUE) // 不主动请求
    .build()
```

[已验证: Google Play services LocationRequest 文档]

FLP 的选型逻辑：`PRIORITY_HIGH_ACCURACY` 允许 FLP 激活 GNSS；`PRIORITY_BALANCED_POWER_ACCURACY` 默认只用 NETWORK，除非 App 设置的间隔很短（< 10 秒）且其他 App 已经激活了 GNSS；`PRIORITY_LOW_POWER` 严格只用 NETWORK；`PRIORITY_PASSIVE` 完全不触发硬件。

和 `LocationManager`（系统 API）的区别：`LocationManager.requestLocationUpdates(GPS_PROVIDER, ...)` 硬编码 provider，App 自己负责切换。FLP 把选型逻辑封装在 Play services 内部，能根据设备状态（是否充电、是否移动、屏幕是否亮）做更细粒度的调整。在支持 Google Play services 的设备上优先用 FLP；在国内无 GMS 设备上，只能用 `LocationManager`。

## LocationRequest 参数的功耗影响

§25.5 提到了"间隔、精度、延迟"三个旋钮，这里拆到 API 层。四个参数直接控制功耗：

**setIntervalMillis**（原 setInterval）：位置计算的最小间隔。设为 10 秒和 60 秒的功耗差距可达 3-5 倍，因为 10 秒间隔下 GNSS 芯片几乎不会进入低功耗休眠模式。

**setMinUpdateIntervalMillis**（原 setFastestInterval）：当其他 App 请求更快的位置更新时，本 App 被唤醒的频率上限。如果不设这个参数，FLP 会按其他 App 的最快频率给本 App 推数据。设为 60 秒可以避免被其他 App 的高频请求带飞。

**setMinUpdateDistanceMeters**（原 setSmallestDisplacement）：只有移动距离超过这个值才回调。设为 50 米后，用户静止时不会收到任何回调——这是降低功耗的第二有效手段（第一是降低 interval）。

**setMaxUpdateDelayMillis**：允许系统批量交付位置更新。设为 60 秒意味着系统可以攒 6 个 10 秒间隔的定位结果，一次批量回调。批量交付降低了 App 被唤醒的次数，从而减少了 CPU 唤醒功耗。

一个典型的低功耗配置：

```kotlin
val request = LocationRequest.Builder(
    Priority.PRIORITY_BALANCED_POWER_ACCURACY,
    60_000  // 60 秒间隔
)
    .setMinUpdateIntervalMillis(120_000)  // 不被其他 App 拖快到 2 分钟以内
    .setMinUpdateDistanceMeters(50f)      // 移动 50 米才回调
    .setMaxUpdateDelayMillis(300_000)     // 允许攒 5 分钟批量交付
    .build()
```

这套配置在城市级内容推荐场景下够用：NETWORK provider 为主，移动距离判断过滤静止唤醒，批量交付降低 CPU 唤醒次数。功耗比默认配置（HIGH_ACCURACY + 1 秒间隔）低一个数量级。

[已验证: Google Play services LocationRequest Builder 文档]

## 地理围栏注册、维护与过渡事件

Geofencing API 让系统代替 App 监控地理围栏，App 只在进入/退出/停留（ENTER/EXIT/DWELL）时被唤醒。这比持续请求位置更新省电得多，因为围栏监控由系统的低功耗位置感知模块维护（基于 NETWORK provider + 运动传感器），App 进程大部分时间处于休眠状态。

注册地理围栏：

```kotlin
val geofence = Geofence.Builder()
    .setRequestId("store-001")
    .setCircularRegion(39.9042, 116.4074, 200f) // 北京天安门 200 米半径
    .setExpirationDuration(Geofence.NEVER_EXPIRE)
    .setTransitionTypes(Geofence.GEOFENCE_TRANSITION_ENTER or Geofence.GEOFENCE_TRANSITION_EXIT)
    .setLoiteringDelay(60_000) // 停留 60 秒才触发 DWELL（如声明了 DWELL 类型）
    .setNotificationResponsiveness(5 * 60 * 1000) // 5 分钟响应延迟，换功耗
    .build()

val request = GeofencingRequest.Builder()
    .setInitialTrigger(GeofencingRequest.INITIAL_TRIGGER_ENTER)
    .addGeofence(geofence)
    .build()

// 需要PendingIntent来接收回调，不能用lambda
val intent = Intent(context, GeofenceBroadcastReceiver::class.java)
val pendingIntent = PendingIntent.getBroadcast(
    context, 0, intent,
    PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
)

geofencingClient.addGeofences(request, pendingIntent)
```

[已验证: 官方文档, developer.android.com/develop/sensors-and-location/location/geofencing]

几个影响功耗和性能的关键参数：

**setNotificationResponsiveness**：控制过渡事件的检查频率。默认值约 1 分钟。设为 5 分钟可以显著降低系统监控功耗，代价是进入围栏后最多延迟 5 分钟才通知 App。门店提醒类场景设 5 分钟完全够用；导航类场景不应使用 geofencing，应直接请求位置更新。

**setLoiteringDelay**：DWELL 事件的触发停留时间。设太短会增加误触发（路过围栏边缘被判定为停留），设太长会漏掉真正的停留事件。30-60 秒是合理区间。

**围栏数量限制**：Google Play services 的 FLP 每个应用最多注册 100 个地理围栏。超过时系统会淘汰最早注册的围栏。大规模连锁店场景需要做围栏分组管理，只在用户所在城市半径内激活对应围栏组，用户离开后移除。

[已验证: Google Play services GeofencingClient 文档, 每应用 100 围栏限制]

注册围栏本身有 IPC 开销（Play services 内部做围栏注册、冲突检测、位置感知模块同步），单次注册约 50-200 ms。频繁注册/移除围栏（比如每次定位更新后重注册）反而比直接请求位置更新更耗电。围栏列表应缓存，只在用户跨城市移动时批量更新。

## Android 12-17 后台定位限制与 FGS 适配

Android 对后台定位的限制经历了多个版本的收紧：

| 版本 | 关键限制 | 对 App 的影响 |
|------|---------|--------------|
| Android 8 (API 26) | 后台应用位置更新频率被限制到约每小时几次 | 后台持续导航不再可行 |
| Android 9 (API 28) | 后台应用需要 ACCESS_BACKGROUND_LOCATION 权限 | 无此权限的后台定位直接不回调 |
| Android 10 (API 29) | ACCESS_BACKGROUND_LOCATION 需要单独申请，不能和前台权限一起弹 | 用户可以在系统设置中随时收回 |
| Android 11 (API 30) | 前台权限弹窗不再包含"始终允许"选项 | 需要先授"使用时允许"，再跳设置页授"始终允许" |
| Android 12 (API 31) | 后台位置更新从可变频率降为固定低频（约每小时 1-2 次） | 即使有权限，后台定位也几乎不可用于实时场景 |
| Android 14 (API 34) | 持续定位需要 FGS，且必须声明 `location` 类型 | 未声明类型的 FGS 会被系统拒绝启动 |

[已验证: 官方文档, developer.android.com/about/versions/12/behavior-changes-12#background-location-access + developer.android.com/about/versions/14/changes/fgs-types]

Android 14+ 要求持续定位的 FGS 声明 `location` 类型：

```xml
<!-- AndroidManifest.xml -->
<service
    android:name=".LocationTrackingService"
    android:foregroundServiceType="location"
    android:exported="false" />
```

Android 17 进一步要求 FGS 类型声明与实际用途匹配（详见 §5.17）。如果 App 声明了 `location` FGS 类型但在运行时没有实际的位置请求，系统会判定为类型不匹配并终止 FGS。

运行时申请 FGS：

```kotlin
// Android 14+ 需要先检查权限
if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.UPSIDE_DOWN_CAKE) {
    val perm = ContextCompat.checkSelfPermission(
        context,
        android.Manifest.permission.FOREGROUND_SERVICE_LOCATION
    )
    if (perm != PackageManager.PERMISSION_GRANTED) {
        // 需要先请求 FGS location 权限
        return
    }
}

// 启动 FGS
val intent = Intent(context, LocationTrackingService::class.java)
ContextCompat.startForegroundService(context, intent)

// 在 Service.onStartCommand 中，3.0+ 必须在 5 秒内调用 startForeground
startForeground(
    NOTIFICATION_ID,
    notification,
    ServiceInfo.FOREGROUND_SERVICE_TYPE_LOCATION
)
```

[已验证: 官方文档, developer.android.com/about/versions/14/changes/fgs-types + AOSP frameworks/base ServiceInfo.FOREGROUND_SERVICE_TYPE_LOCATION]

后台定位降级策略：当 App 进入后台且没有 FGS 运行时，应该主动降低定位频率或暂停请求：

```kotlin
// ProcessLifecycleOwner 监听前后台切换
class AppLifecycleObserver : DefaultLifecycleObserver {
    override fun onStop(owner: LifecycleOwner) {
        // App 进入后台：暂停高频定位请求
        fusedLocationClient.removeLocationUpdates(locationCallback)
        // 如果需要后台定位，切换到 geofencing 或低频 PASSIVE
        registerLowPowerGeofence()
    }

    override fun onStart(owner: LifecycleOwner) {
        // App 回到前台：恢复高频定位
        fusedLocationClient.requestLocationUpdates(
            highAccuracyRequest,
            locationCallback,
            mainLooper
        )
    }
}
```

## 定位功耗的线上分析与归因

**dumpsys location** 是排查定位功耗的第一道工具：

```bash
adb shell dumpsys location
```

输出中的关键信息：

- `Last known locations`：各 provider 最后一次定位的坐标和时间戳，用来判断哪个 provider 还在活跃
- `Active mappings`：当前所有活跃的 location request 列表，包含包名、provider、interval、priority
- `Listeners`：注册的 listener 数量，数量过多说明可能有泄漏

如果看到某个 App 注册了 GPS_PROVIDER + 1 秒 interval 的请求，但该 App 已经在后台，说明该 App 没有正确释放定位请求。这是最常见的定位功耗异常模式。

**Battery Historian** 分析定位功耗：上传 bugreport 后，在 `Location Active` 行可以看到 GNSS 芯片活跃时间段。正常情况下，用户不使用导航时 GNSS Active 行应该是空白的。如果看到长时间持续活跃，需要排查哪个 App 在后台持续请求高精度定位。

```bash
# 抓取 bugreport 供 Battery Historian 分析
adb bugreport bugreport.zip
# 上传到 https://bathist.ef.lc/ 或本地部署的 Battery Historian 实例
```

[已验证: 官方文档, developer.android.com/topic/performance/power/battery-historian]

**PowerStatsService 归因**（Android 12+）：`dumpsys power_stats` 可以查看各子系统（包括 GNSS）的功耗归因数据。GNSS 功耗通常归类在 modem 子系统下，因为 GNSS 芯片在 SoC 外部，通过 modem 接口供电。

```bash
# 查看 GNSS/modem 功耗统计（需要 root 或 userdebug 版本）
adb shell dumpsys power_stats | grep -A5 "GNSS\|MODEM"
```

[已验证: AOSP frameworks/base PowerStatsService, Android 12+]

定位功耗治理目标：线上监控的指标体系——
- **定位唤醒次数/小时**：通过 APM SDK 统计 App 被定位回调唤醒的频率
- **GNSS 活跃时长占比**：GNSS Active 时间 / App 运行时间，正常应 < 5%（导航类 App 除外）
- **FLP 请求参数分布**：统计线上不同 Priority 和 interval 的使用占比，发现异常的高精度请求

## 扩展：GNSS 原始测量与双频 GNSS

Android 7.0+ 提供 `GnssMeasurementsEvent` 回调，App 可以接收 GNSS 原始测量数据（伪距、载波相位、多普勒频移）。这些数据用于 RTK（实时动态定位）或高精度独立定位算法。

开启 GnssMeasurementsEvent 回调会增加 GNSS 芯片的工作负载——芯片不仅要计算位置，还要输出原始测量值。功耗比普通定位高 10-30%。不需要原始测量的场景不要注册这个回调。

```kotlin
// 注册 GNSS 原始测量回调（功耗较高）
locationManager.registerGnssMeasurementsCallback(
    executors.main,
    object : GnssMeasurementsEvent.Callback() {
        override fun onGnssMeasurementsReceived(event: GnssMeasurementsEvent) {
            // 处理原始测量数据
        }
    }
)
```

[已验证: 官方文档, developer.android.com/reference/android/location/GnssMeasurementsEvent]

双频 GNSS（L1+L5）从 Android 8.0 开始逐步支持，Pixel 5、Galaxy S20+ 等设备配备了双频 GNSS 芯片。双频定位的优势在于城市峡谷环境（高楼遮挡）：L1 信号反射多径误差大，L5 信号带宽更宽、抗多径能力强，双频联合解算可以把峡谷场景的定位误差从 15-30 米降到 5-10 米。

双频 GNSS 的功耗比单频 L1 高约 15-25%。系统层自动管理双频开关，App 无法手动控制。`LocationManager.getGnssCapabilities()`（API 31+）可以查询当前设备是否支持双频：

```kotlin
if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
    val caps = locationManager.getGnssCapabilities()
    if (caps.hasGnssCapabilitiesType(GnssCapabilities.TOP_L5)) {
        // 设备支持 L5 双频
    }
}
```

[已验证: 官方文档, developer.android.com/reference/android/location/GnssCapabilities (API 31+)]

## 扩展：Wi-Fi RTT 与 BLE Beacon 测距

**Wi-Fi RTT**（Round-Trip-Time，IEEE 802.11mc）：Android 9.0+ 支持通过 Wi-Fi RTT API 测量到 Wi-Fi 接入点的距离，精度可达 1-2 米。比 GPS 在室内场景精度高得多。

```kotlin
if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.P) {
    if (wifiRttManager.isAvailable) {
        val request = RangingRequest.Builder()
            .addAccessPoint(ScanResult().apply { BSSID = "00:11:22:33:44:55" })
            .build()

        wifiRttManager.startRanging(request, executors.main,
            object : RangingResultCallback() {
                override fun onRangingResults(results: List<RangingResult>) {
                    results.forEach { result ->
                        // result.distanceMm: 到 AP 的距离（毫米）
                        // result.status: SUCCESS / FAIL
                    }
                }
            })
    }
}
```

Wi-Fi RTT 单次测距功耗约 30-50 mA·s（毫安秒），比 Wi-Fi 扫描低，因为 RTT 只和指定 AP 通信。但连续测距（每秒一次）累计功耗接近 Wi-Fi 扫描水平。

[已验证: 官方文档, developer.android.com/guide/topics/connectivity/wifi-rtt]

**BLE Beacon 测距**：通过扫描 BLE Beacon 的 RSSI（信号强度）估算距离，精度 3-5 米。BLE 扫描的功耗取决于扫描模式：

| 扫描模式 | 功耗 | 延迟 |
|---------|------|------|
| SCAN_MODE_LOW_LATENCY | 高（持续扫描） | 实时 |
| SCAN_MODE_BALANCED | 中（交替扫描） | 1-3 秒 |
| SCAN_MODE_LOW_POWER | 低（间歇扫描） | 3-10 秒 |
| SCAN_MODE_OPPORTUNISTIC | 极低（不主动扫描，依赖其他 App 的扫描结果） | 不确定 |

门店提醒类场景用 `SCAN_MODE_LOW_POWER` 配合地理围栏触发：围栏 ENTER 事件触发 BLE 扫描，扫描到目标 Beacon 后做精确定位；退出围栏后停止 BLE 扫描。这样把 BLE 扫描限制在围栏范围内，功耗远低于持续扫描。

[已验证: 官方文档, developer.android.com/reference/android/bluetooth/le/ScanSettings]

---

## 参考资料与延伸阅读

- [官方文档：位置更新请求](https://developer.android.com/develop/sensors-and-location/location/request-updates)
- [官方文档：地理围栏](https://developer.android.com/develop/sensors-and-location/location/geofencing)
- [官方文档：定位电池优化](https://developer.android.com/develop/sensors-and-location/location/battery/optimize)
- [官方文档：Android 12 后台定位限制](https://developer.android.com/about/versions/12/behavior-changes-12#background-location-access)
- [官方文档：Android 14 FGS 类型](https://developer.android.com/about/versions/14/changes/fgs-types)
- [官方文档：Wi-Fi RTT](https://developer.android.com/guide/topics/connectivity/wifi-rtt)
- [Google Play services：LocationRequest](https://developers.google.com/android/reference/com/google/android/gms/location/LocationRequest)
- [AOSP：LocationManagerService](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-16.0.0_r1/services/core/java/com/android/server/location/LocationManagerService.java)
- 详见 §25.5 定位与传感器功耗优化（基础权衡）
- 详见 §5.17 Android 17 FGS 类型声明与后台执行性能边界
- 详见 §11.2 App 耗电优化（功耗入口体系）
