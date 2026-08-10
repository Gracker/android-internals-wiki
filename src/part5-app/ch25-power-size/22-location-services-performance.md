---

title: "定位服务功耗与性能实战：FusedLocationProvider、地理围栏与批处理"
chapter: "25.22"
status: "finalized"
pipeline_stage: "ready-to-publish"
applicable_versions: "Android 12 (API 31) - Android 17 (API 37)"
tags: ["定位", "Location", "FusedLocationProvider", "功耗", "Geofencing", "FGS"]
confidence: "medium-high"
sources:
- type: aosp
  path: frameworks/base/location/java/android/location/LocationManager.java
- type: official
  path: https://developer.android.com/develop/sensors-and-location/location/request-updates
- type: official
  path: https://developer.android.com/develop/sensors-and-location/location/geofencing
- type: official
  path: https://developer.android.com/develop/sensors-and-location/location/battery/optimize
- type: official
  path: https://developer.android.com/develop/sensors-and-location/location/permissions/runtime
- type: official
  path: https://developer.android.com/develop/sensors-and-location/location/background
- type: official
  path: https://developer.android.com/develop/background-work/services/fgs/service-types#location
- type: official
  path: https://developer.android.com/develop/background-work/services/fgs/restrictions-bg-start
- type: official
  path: https://developer.android.com/develop/sensors-and-location/sensors/gnss
- type: official
  path: https://developer.android.com/develop/connectivity/wifi/wifi-rtt
- type: official
  path: https://developer.android.com/reference/android/bluetooth/le/ScanSettings
- type: reference
  path: https://developers.google.com/android/reference/com/google/android/gms/location/LocationRequest.Builder
- type: reference
  path: https://developers.google.com/android/reference/com/google/android/gms/location/Geofence.Builder
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/location/LocationManagerService.java
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/location/provider/LocationProviderManager.java
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/powerstats/PowerStatsService.java
last_verified: "2026-06-18"
last_verified_against: "Android Developers location/background + FGS service type docs + Google Play services LocationRequest/GeofenceStatusCodes + Android API GnssStatus + AOSP android-17.0.0_r1 LocationManagerService"
drafted_date: "2026-06-18"
reviewed_date: "2026-06-26"
reviewed_by: "openclaw-task6"
related_chapters: ["5.15", "11.2", "25.5", "5.17"]
created_by: "task2a-knowledge-gap"
created_date: "2026-06-18"
gap_source: "官方文档/素材驱动"
task2b_result: "fixed-lite"
task2b_state: "fixed"
task6_state: "reviewed"
task9_state: "reviewed"
task9_result: "auto-fixed"
last_task2b_lite_at: "2026-06-26"
task6_result: "pass-light-edit"
last_task6_at: "2026-06-26T08:10:15+08:00"
task6_l1_l2_fixes: "0"
task6_l3_l4_issues: "0"
last_task9_at: "2026-06-19T08:25:51+08:00"
task9_reviewed_date: "2026-06-19"
task9_reviewed_by: "openclaw-task9"
last_task9_autofix_at: "2026-06-19"
updated_by: "openclaw-task9-auto-fix"
updated_date: "2026-06-19"
p0: "5"
p1: "1"
p2: "1"
deepseek_cn_review_state: done
last_deepseek_cn_review_at: 2026-06-26
---

# 25.22 定位服务功耗与性能实战：FusedLocationProvider、地理围栏与批处理

§25.5 从精度、频率、延迟三个维度介绍了定位功耗的基本权衡。这里把这些原则映射到 API 与排障工具：怎样选择平台 provider 或 Fused Location Provider，怎样理解 `LocationRequest` 的尽力而为语义，地理围栏与前台服务各自适合什么场景，以及怎样在 Android 17 上定位没有释放的请求。

## 定位 Provider 的功耗特征与 FusedLocationProvider 选型策略

先区分两层概念：

- Android Framework 的 `LocationManager` 面向具名 provider。Android 17 的 `LocationManagerService` 管理 `gps`、`network`、`fused`、`passive` 等 provider，设备是否提供其中某个 provider 仍取决于产品实现。
- Google Play services 的 `FusedLocationProviderClient`（下文简称 FLP）面向精度与功耗目标。调用方提交 `Priority` 和时间、距离约束，由 Play services 选择可用信号源并融合结果。

几类请求的稳定语义如下。表中不写固定电流、精度或首次定位时间，因为射频环境、芯片、天线、辅助数据和 OEM 算法都会改变这些数值；跨设备套用单一数字会误导容量评估。

| 请求方式 | API 能保证的含义 | 工程上的功耗判断 |
|---|---|---|
| `LocationManager.GPS_PROVIDER` | 向 GNSS provider 请求位置 | 持续或高频请求通常会保持 GNSS 路径活跃，需在目标设备实测 |
| `LocationManager.NETWORK_PROVIDER` | 向网络位置 provider 请求位置 | 依赖设备的网络位置实现，不应假定只使用 Wi‑Fi 或只使用蜂窝 |
| `LocationManager.PASSIVE_PROVIDER` | 接收其他请求已经产生的位置，不为本请求主动启动位置计算 | 不增加位置推导需求，但回调、IPC 和应用处理仍会消耗 CPU |
| FLP 非被动优先级 | 表达精度与功耗偏好 | 信号源选择是实现细节，不能从优先级反推某个硬件一定开启 |
| `Priority.PRIORITY_PASSIVE` | 只接收其他客户端促成的位置 | 不为本请求额外推导位置；回调频率仍需用最小更新间隔约束 |

`PASSIVE_PROVIDER` 和 `PRIORITY_PASSIVE` 也要经过定位权限检查。只有 `ACCESS_COARSE_LOCATION` 时，应用只能依赖模糊后的位置；需要精确位置时仍要获得 `ACCESS_FINE_LOCATION`。被动请求的价值是“不增加位置推导需求”，并不等于应用侧零功耗，也不保证何时会收到结果。

下面的代码只负责表达四种不同的服务目标，不把优先级写成硬件开关：

```kotlin
fun buildLocationRequest(
    priority: Int,
    desiredIntervalMillis: Long,
    fastestAcceptedIntervalMillis: Long
): LocationRequest =
    LocationRequest.Builder(priority, desiredIntervalMillis)
        .setMinUpdateIntervalMillis(fastestAcceptedIntervalMillis)
        .build()

val navigationRequest = buildLocationRequest(
    priority = Priority.PRIORITY_HIGH_ACCURACY,
    desiredIntervalMillis = navigationIntervalMillis,
    fastestAcceptedIntervalMillis = navigationFastestIntervalMillis
)

val nearbyContentRequest = buildLocationRequest(
    priority = Priority.PRIORITY_BALANCED_POWER_ACCURACY,
    desiredIntervalMillis = nearbyContentIntervalMillis,
    fastestAcceptedIntervalMillis = nearbyContentFastestIntervalMillis
)

val passiveRequest = buildLocationRequest(
    priority = Priority.PRIORITY_PASSIVE,
    desiredIntervalMillis = passiveDesiredIntervalMillis,
    fastestAcceptedIntervalMillis = passiveFastestIntervalMillis
)
```

三个间隔都应来自产品需求与设备测试，而不是从示例代码复制。`PRIORITY_HIGH_ACCURACY` 偏向更高精度并可能付出更多功耗；`BALANCED_POWER_ACCURACY` 和 `LOW_POWER` 分别表达平衡与低功耗偏好；`PASSIVE` 不促成新的位置计算。除被动语义外，API 没有承诺采用哪种传感器组合。

FLP 还会同时考虑设备可用的 provider、应用已有权限和请求参数。只获得 coarse 权限时，结果可能被模糊并降频；即使请求 high accuracy，也不能绕过用户选择的近似位置。反过来，收到高精度结果也不能证明某一颗射频芯片一定由当前请求独占启动。

`FusedLocationProviderClient` 属于 Google Play services，不是 AOSP SDK 的一部分。没有 Google Play services 的产品可以使用 `LocationManager`，也可以接入厂商提供且经过验证的位置 SDK。不要把“无 GMS”简化成所有设备行为一致；provider 可用性应通过 API 查询，降级路径也要在对应设备上测试。

## LocationRequest 参数的功耗影响

`LocationRequest` 的大部分参数是约束或提示，不是调度器的精确时钟：

- `setIntervalMillis()` 是期望的更新间隔。结果可能更慢；如果系统已经为其他请求产生了位置，也可能更快，但不能快过显式设置的最小更新间隔。
- `setMinUpdateIntervalMillis()` 是应用愿意接收的最快间隔，主要用于限制机会式更新和回调负担。它不应大于期望间隔；否则请求意图自相矛盾。
- `setMinUpdateDistanceMeters()` 过滤与上一次已交付位置距离不足的结果。在某些设备和请求组合上，它也可能节电，但 API 只保证交付过滤，不保证 provider 因此停止计算。
- `setMaxUpdateDelayMillis()` 允许批量交付。只有最大延迟至少为期望间隔的两倍时，请求才允许批处理；硬件和实现可以选择不批处理。
- `setDurationMillis()` 或 `setMaxUpdates()` 给请求设置止损条件，适合一次交互或有界采样，不能代替正常的生命周期注销。

批量位置可能跨批次乱序，单批内部才保证有序。消费端应按 `Location.getElapsedRealtimeNanos()` 或等价的单调时间字段判断先后，不能用回调到达时间排序。

下面采用官方电池优化文档中的量级，演示“十分钟采样、最多延迟一小时交付”的批处理请求：

```kotlin
val request = LocationRequest.Builder(
    Priority.PRIORITY_HIGH_ACCURACY,
    10 * 60 * 1000L
)
    .setMaxUpdateDelayMillis(60 * 60 * 1000L)
    .setDurationMillis(sessionDurationMillis)
    .build()
```

这表示设备可以把大约六个位置合并交付，而不是承诺每小时一定回调一次或一定包含六个结果。结束交互时仍要调用 `removeLocationUpdates()`；`setDurationMillis()` 只是异常路径的上限。

如果业务只要一个当前位置，不要注册持续更新再等待首个回调。FLP 提供 `getCurrentLocation()`，它对单次请求的取消、缓存年龄和时限表达更清晰。若业务能接受最近一次缓存，则再根据时间戳判断 `getLastLocation()` 是否足够新。

下面的会话对象展示成对注册与注销，并防止同一实例重复注册：

```kotlin
class LocationSession(
    private val client: FusedLocationProviderClient,
    private val request: LocationRequest,
    private val callback: LocationCallback,
    private val looper: Looper
) : AutoCloseable {
    private var started = false

    @SuppressLint("MissingPermission")
    fun start() {
        if (started) return
        started = true
        client.requestLocationUpdates(request, callback, looper)
    }

    override fun close() {
        if (!started) return
        started = false
        client.removeLocationUpdates(callback)
    }
}
```

调用方应在获得相应定位权限后执行 `start()`，并在页面、导航会话或拥有者结束时执行 `close()`。不要只依赖进程进入后台的通知：多窗口、画中画和前台服务会让“应用前后台”与“功能是否仍需定位”不完全相同。

## 地理围栏注册、维护与过渡事件

地理围栏适合“到达某片区域时通知我”，不适合轨迹、转向指引或秒级接近判断。应用提交圆形区域和过渡类型，由 Google Play services 监控并通过 `PendingIntent` 交付事件。服务内部采用哪些 provider 或传感器不是公开契约，因此不能把某种融合策略写进应用正确性假设。

下面的函数把围栏参数交给业务层，并正确声明 `DWELL` 与可变 `PendingIntent`：

```kotlin
data class MonitoredRegion(
    val id: String,
    val latitude: Double,
    val longitude: Double,
    val radiusMeters: Float,
    val loiteringDelayMillis: Int,
    val responsivenessMillis: Int
)

fun geofencePendingIntent(context: Context): PendingIntent {
    val mutabilityFlag =
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
            PendingIntent.FLAG_MUTABLE
        } else {
            0
        }

    return PendingIntent.getBroadcast(
        context,
        0,
        Intent(context, GeofenceBroadcastReceiver::class.java),
        PendingIntent.FLAG_UPDATE_CURRENT or mutabilityFlag
    )
}

@SuppressLint("MissingPermission")
fun registerRegion(
    context: Context,
    client: GeofencingClient,
    region: MonitoredRegion
): Task<Void> {
    val transitions =
        Geofence.GEOFENCE_TRANSITION_EXIT or
            Geofence.GEOFENCE_TRANSITION_DWELL

    val geofence = Geofence.Builder()
        .setRequestId(region.id)
        .setCircularRegion(
            region.latitude,
            region.longitude,
            region.radiusMeters
        )
        .setExpirationDuration(Geofence.NEVER_EXPIRE)
        .setTransitionTypes(transitions)
        .setLoiteringDelay(region.loiteringDelayMillis)
        .setNotificationResponsiveness(region.responsivenessMillis)
        .build()

    val request = GeofencingRequest.Builder()
        .setInitialTrigger(GeofencingRequest.INITIAL_TRIGGER_DWELL)
        .addGeofence(geofence)
        .build()

    return client.addGeofences(request, geofencePendingIntent(context))
}
```

`PendingIntent` 从 Android 12 起必须显式声明可变性。Geofencing 文档要求 S 及以上使用 `FLAG_MUTABLE`，因为位置服务需要把过渡信息写入待发送的 Intent；这里不能照搬普通通知点击事件常用的 `FLAG_IMMUTABLE`。`setLoiteringDelay()` 只有在过渡类型包含 `GEOFENCE_TRANSITION_DWELL` 时才生效。

几个参数需要按业务语义确定：

- `setNotificationResponsiveness()` 是尽力而为的通知响应目标。值越大，系统越有机会节电；即使填写很小的值，也不保证在该时间内回调。
- `setLoiteringDelay()` 定义进入后持续停留多久才产生 `DWELL`。它应来自“路过是否算到店”这类产品定义，而不是一个通用秒数。
- 圆半径不能小于定位误差所能支持的范围。官方指南建议多数普通场景从至少 100 米考虑，再用目标地区和设备的实测误差调整。
- 每个应用、每个设备用户最多有 100 个活动围栏。超过上限会失败，不会替应用淘汰旧围栏。

注册成功不代表永远存在。设备重启、应用重装或清除数据、清除 Google Play services 数据，以及收到 `GEOFENCE_NOT_AVAILABLE` 后，都需要按业务状态重新注册。Google Play services 自身升级、进程因资源限制被终止或位置进程崩溃时，服务会恢复已登记的围栏，应用不应在每次进程启动时无条件重复注册。

围栏规模超过上限时，可以按用户所在的大区保留候选集合，但“何时换组”仍需一种粗粒度位置来源。不要在每次位置回调后删除并重建全部围栏；比较请求 ID 和区域版本，只提交发生变化的部分，并记录 `addGeofences()` 的失败状态码。

## Android 12-17 后台定位限制与 FGS 适配

理解后台定位时要同时看运行系统版本、`targetSdkVersion`、权限授予状态与应用当前可见性。只看 manifest 不足以判断能否启动服务或读取位置。

| 平台版本 | 规则 | 实现要点 |
|---|---|---|
| Android 8（API 26） | 普通后台应用的位置更新被限制为每小时少数几次 | 持续导航、运动记录等用户可感知会话使用前台服务；区域事件优先考虑围栏 |
| Android 9（API 28） | 使用前台服务的应用需要声明基础 `FOREGROUND_SERVICE` 权限 | 该权限不是 location 类型专属权限 |
| Android 10（API 29） | 引入 `ACCESS_BACKGROUND_LOCATION`；位置前台服务需声明 `android:foregroundServiceType="location"` | 只有核心功能确需在后台访问位置时才申请后台权限 |
| Android 11（API 30） | target 30 及以上不能同时申请前台与后台定位权限；“始终允许”通过设置页授予 | 先在功能上下文申请前台定位，之后再解释后台用途并引导用户设置 |
| Android 12（API 31） | 用户可把应用限制为近似位置；从后台启动 FGS 受到通用限制 | 同时申请 coarse 与 fine，并完整测试只有 coarse 的分支 |
| Android 14（API 34） | target 34 及以上必须声明 FGS 类型专属权限；创建 location FGS 时检查 while-in-use 前置条件 | 声明 `FOREGROUND_SERVICE_LOCATION`，启动时位置服务已开启且至少有 coarse 或 fine |
| Android 17（API 37） | 上述定位与 location FGS 约束继续生效；只需会话级定位的功能应评估 Android 17 Location Button | 不要把 FGS 当作获取权限或绕过后台启动限制的手段 |

Android 12 及以上，申请精确位置时应在同一次前台权限请求中同时请求 coarse 与 fine。用户选择 approximate 后，应用只获得 coarse；进程还可能在用户从 precise 降为 approximate 时被系统重启，状态恢复代码必须覆盖该路径。

下面的 manifest 同时展示基础 FGS 权限、API 34 的类型权限和位置运行时权限。`ACCESS_BACKGROUND_LOCATION` 只应在功能离开前台后仍需访问位置时添加：

```xml
<uses-permission android:name="android.permission.FOREGROUND_SERVICE" />
<uses-permission android:name="android.permission.FOREGROUND_SERVICE_LOCATION" />
<uses-permission android:name="android.permission.ACCESS_COARSE_LOCATION" />
<uses-permission android:name="android.permission.ACCESS_FINE_LOCATION" />

<service
    android:name=".LocationTrackingService"
    android:foregroundServiceType="location"
    android:exported="false" />
```

`FOREGROUND_SERVICE_LOCATION` 是普通 manifest 权限，没有运行时弹窗。coarse/fine 是运行时权限；位置总开关也必须开启。声明了 `location` 类型不会自动获得任何位置访问权。

前台服务应从用户可见界面启动，再由 `Service` 自己调用 `startForeground()`。下面省略通知渠道创建和定位回调，只展示调用位置与类型参数：

```kotlin
// 在可见 Activity 中，由用户操作启动。
fun startTrackingFromVisibleUi(context: Context) {
    ContextCompat.startForegroundService(
        context,
        Intent(context, LocationTrackingService::class.java)
    )
}

class LocationTrackingService : Service() {
    override fun onStartCommand(
        intent: Intent?,
        flags: Int,
        startId: Int
    ): Int {
        val hasCoarse = PermissionChecker.checkSelfPermission(
            this,
            Manifest.permission.ACCESS_COARSE_LOCATION
        ) == PermissionChecker.PERMISSION_GRANTED
        val hasFine = PermissionChecker.checkSelfPermission(
            this,
            Manifest.permission.ACCESS_FINE_LOCATION
        ) == PermissionChecker.PERMISSION_GRANTED

        if ((!hasCoarse && !hasFine) || !locationManager.isLocationEnabled) {
            stopSelf(startId)
            return START_NOT_STICKY
        }

        val type =
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
                ServiceInfo.FOREGROUND_SERVICE_TYPE_LOCATION
            } else {
                0
            }

        ServiceCompat.startForeground(
            this,
            LOCATION_NOTIFICATION_ID,
            buildTrackingNotification(),
            type
        )

        startLocationUpdates()
        return START_NOT_STICKY
    }

    override fun onDestroy() {
        stopLocationUpdates()
        super.onDestroy()
    }

    override fun onBind(intent: Intent?): IBinder? = null
}
```

权限检查必须发生在服务创建前的业务流程中，服务内部再做一次防御性检查。Android 14 及以上的 coarse/fine 属于 while-in-use 权限：应用在后台且没有 `ACCESS_BACKGROUND_LOCATION` 时，通常不能创建 location FGS。即使有后台定位权限，Android 12 起的通用“禁止从后台启动 FGS”仍独立生效，调用点还需满足可见状态或文档列出的豁免条件。

地理围栏事件、普通后台更新和 location FGS 是三条不同路径：

- 只关心进入、离开或停留区域：用 geofencing，并申请其所需的 fine 与后台定位权限。
- 用户明确开始且需要持续可见的导航或位置共享：用 location FGS，提供持续通知与停止入口。
- 页面可见时刷新附近内容：请求前台位置，在页面会话结束时移除。
- 后台没有明确用户价值：停止请求，不要用 FGS 维持进程存活。

## 定位功耗的线上分析与归因

### 从活动请求查起

下面的命令读取 Android 17 的位置服务状态，并可进一步只看 `gps` provider：

```bash
adb shell dumpsys location
adb shell dumpsys location gps
adb shell dumpsys location --gnssmetrics
```

在 `android-17.0.0_r1` 中，完整输出以 `Location Manager State:` 开始，`Location Providers:` 下逐个打印 provider。每个 provider 的 `service:` 是合并后的 provider 请求；存在客户端时会出现 `listeners:`，其后能看到调用方身份与请求参数；`last location=` 和 `enabled=` 分别表示最近缓存位置和启用状态。字段由系统版本与 OEM 分支决定，排障脚本不要依赖旧版本的 `Active mappings` 或 `Last known locations` 文本。

判断泄漏时同时看四项：请求所属 UID/包名、请求是否 active、间隔与质量、功能会话是否已经结束。缓存中还有 `last location` 不能证明 provider 此刻仍在工作；注册项数量多也不必然是泄漏，只有功能会话结束后仍无有效拥有者的注册项才属于异常。

### 用 bugreport、batterystats 与系统跟踪建立时间线

下面的命令保存 bugreport 和自充满以来的电池统计，便于把位置请求与唤醒、前台服务和进程状态放在同一条时间线上：

```bash
adb bugreport bugreport.zip
adb shell dumpsys batterystats --charged your.package.name
```

`your.package.name` 要替换为被测应用的真实包名。bugreport 可由团队自建的 Battery Historian 分析，也可以保留为问题证据；不要上传包含用户数据的报告到不受控的公共实例。对可复现场景，优先使用 Android Studio Power Profiler 或 Perfetto/System Trace，在已知操作窗口中关联应用线程、唤醒和设备支持的电源轨数据。

Android 17 的 Binder 服务名是 `powerstats`，不是 `power_stats`。下面的命令列出设备 Power Stats HAL 暴露的实体、通道和 energy consumer：

```bash
adb shell dumpsys powerstats
```

这份输出依赖设备是否实现相应 HAL，也可能受构建类型或 dump 权限限制。电源轨名字由设备定义，GNSS 能量可能没有独立 rail；累计 rail 数据也不等于某个应用的精确归因。若要比较改动，固定设备、系统版本、网络与运动条件，记录操作窗口的差值，并用多轮重复测试观察分布。

线上指标应从业务会话出发，而不是设一个适用于所有应用的“GNSS 占比正常值”。至少记录请求用途、优先级、期望/最小间隔、最大延迟、注册与注销时间、前后台状态、回调次数和有效结果数。服务端按导航、附近内容、到店提醒等场景分别建立基线，才能区分“用户持续导航”与“页面退出后请求未释放”。

## GNSS 原始测量、双频 GNSS、Wi-Fi RTT 与 BLE 测距

原始 GNSS、Wi‑Fi RTT 与 BLE 扫描都比普通“获取当前位置”更接近测量系统。它们提供观测值或测距输入，不自动提供稳定的业务坐标，也没有统一的功耗常数。评估时要把硬件能力、权限、前后台限制、采样会话和算法误差一起纳入设计。

### GNSS 原始测量与双频 GNSS

Android 7.0（API 24）加入 `GnssMeasurementsEvent`。原始测量可用于伪距、载波相位/累积增量距离、钟差与多普勒等分析，但字段支持仍随芯片变化。Android 10 及以上设备必须支持原始 GNSS 测量，部分字段与多频能力仍是可选项。

下面把 callback 保存为字段，以便在同一拥有者结束时注销：

```kotlin
class GnssMeasurementSession(
    private val locationManager: LocationManager,
    private val executor: Executor,
    private val consumer: (GnssMeasurementsEvent) -> Unit
) : AutoCloseable {
    private val callback = object : GnssMeasurementsEvent.Callback() {
        override fun onGnssMeasurementsReceived(
            event: GnssMeasurementsEvent
        ) {
            consumer(event)
        }
    }

    fun start(): Boolean =
        locationManager.registerGnssMeasurementsCallback(executor, callback)

    override fun close() {
        locationManager.unregisterGnssMeasurementsCallback(callback)
    }
}
```

该 API 需要 `ACCESS_FINE_LOCATION`。API 30 的 `Executor` 重载只在 GPS provider 已启用且客户端处于前台时交付测量；注册返回成功也不代表每个字段都有值。API 31 的 `GnssMeasurementRequest.setFullTracking(true)` 会要求芯片关闭占空比，只有算法确需连续载波相位时才应使用，并在目标硬件上测量能耗。

多频能力不能用单一布尔开关概括。下面只记录当前卫星观测的载波频率，不把它当作“系统融合定位正在使用双频”的证据：

```kotlin
fun observedCarrierFrequenciesHz(status: GnssStatus): List<Float> =
    buildList {
        for (index in 0 until status.satelliteCount) {
            if (status.hasCarrierFrequencyHz(index)) {
                add(status.getCarrierFrequencyHz(index))
            }
        }
    }
```

`hasCarrierFrequencyHz()` 与 `getCarrierFrequencyHz()` 从 API 26 起可用。解释频段时还要结合星座和信号规范；观察到某个频率只说明本次状态中存在该信号，不能证明位置解算采用了它，更不能据此承诺精度改善。

### Wi-Fi RTT 与 BLE Beacon 测距

Wi‑Fi RTT 从 Android 9（API 28）起支持 IEEE 802.11mc FTM；Android 15（API 35）加入 IEEE 802.11az NTB 测距支持。对三个或更多位置已知的 AP 做多边定位时，官方给出的典型位置精度是 1–2 米，这不是单次到单个 AP 的固定误差保证。

`RangingRequest` 必须使用 Wi‑Fi 扫描得到的真实 `ScanResult`，不能手工构造一个只填 BSSID 的对象。下面的函数从现有扫描结果筛选支持的 responder：

```kotlin
@RequiresApi(Build.VERSION_CODES.P)
fun rangeToResponders(
    manager: WifiRttManager,
    scanResults: List<ScanResult>,
    executor: Executor,
    onDistance: (MacAddress, Int) -> Unit,
    onPeerBusy: (MacAddress, Int) -> Unit,
    onFailure: (Int) -> Unit
) {
    val responders = scanResults.filter { result ->
        result.is80211mcResponder ||
            (
                Build.VERSION.SDK_INT >= Build.VERSION_CODES.VANILLA_ICE_CREAM &&
                    result.is80211azNtbResponder
            )
    }

    if (!manager.isAvailable || responders.isEmpty()) return

    val request = RangingRequest.Builder()
        .addAccessPoints(responders)
        .build()

    manager.startRanging(
        request,
        executor,
        object : RangingResultCallback() {
            override fun onRangingFailure(code: Int) {
                onFailure(code)
            }

            override fun onRangingResults(results: List<RangingResult>) {
                results.forEach { result ->
                    val macAddress = result.macAddress ?: return@forEach
                    when {
                        result.status == RangingResult.STATUS_SUCCESS -> {
                            onDistance(macAddress, result.distanceMm)
                        }
                        Build.VERSION.SDK_INT >= Build.VERSION_CODES.CINNAMON_BUN &&
                            result.status == RangingResult.STATUS_BUSY_TRY_LATER -> {
                            onPeerBusy(
                                macAddress,
                                result.retryAfterDurationMillis
                            )
                        }
                    }
                }
            }
        }
    )
}
```

调用前还要确认 `FEATURE_WIFI_RTT`、位置总开关与 Wi‑Fi 扫描均可用。target 33 及以上需要运行时 `NEARBY_WIFI_DEVICES` 权限；较低 target 使用 `ACCESS_FINE_LOCATION`。测距必须发生在应用可见时或前台服务中，过于频繁的请求可能被限流。回调列表顺序不保证与请求顺序一致，必须按 MAC 地址关联；只有 `STATUS_SUCCESS` 时，距离等测量字段才有效。Android 17（API 37）新增 `STATUS_BUSY_TRY_LATER`，此时按 `getRetryAfterDurationMillis()` 返回的建议延迟安排重试，不要立即循环请求。

BLE Beacon 方案从广播 RSSI 估算距离。RSSI 会受到人体遮挡、手机姿态、发射功率、天线和多径影响，因此它更适合区域判定或排序，不能把一个未校准的 RSSI 公式当作米级测距真值。

平台对扫描模式的公开语义如下：

| 扫描模式 | API 语义 | 使用边界 |
|---|---|---|
| `SCAN_MODE_LOW_LATENCY` | 使用最高扫描占空比 | 官方建议只在应用前台使用，并严格限制会话时长 |
| `SCAN_MODE_BALANCED` | 在扫描频率和功耗间折中 | 延迟和占空比由实现决定 |
| `SCAN_MODE_LOW_POWER` | 最低功耗模式，也是默认值 | 应用不在前台时系统会强制该模式 |
| `SCAN_MODE_OPPORTUNISTIC` | 不自行启动 BLE 扫描，只接收其他扫描产生的结果 | 可能长期没有结果，不适用于有时限的业务 |

门店类业务可以先用地理围栏缩小候选区域，再在用户明确进入相关功能或满足后台执行条件时启动有界 BLE 扫描。扫描必须保留同一个 `ScanCallback` 并调用 `stopScan(callback)`；还要遵守 Android 12 起的 `BLUETOOTH_SCAN` 运行时权限与后台执行约束。功耗结论应来自目标设备上的会话测试，不从扫描模式名称推导固定延迟或电流。

## 评审清单

提交定位功能前，逐项确认：

- 每个持续请求都有明确的业务拥有者、时限和同一个 callback 的注销路径。
- 产品只需要一次位置时使用单次 API，不注册持续更新。
- high accuracy、更新间隔、最小间隔、距离和批处理延迟都有需求来源与设备实测。
- coarse-only、位置总开关关闭、权限撤销和进程重启路径均可用。
- 地理围栏的 `PendingIntent` 在 Android 12 及以上为 mutable，`DWELL` 与 loitering delay 成对声明。
- location FGS 从用户可见流程启动，manifest 类型、类型权限、运行时权限和通知均完整。
- Android 17 的 `dumpsys location` 中，功能结束后不再保留对应 listener。
- GNSS、RTT、BLE 等测量会话均有能力检查、权限检查、失败处理与停止路径。

---

## 参考资料与延伸阅读

- [官方文档：位置更新请求](https://developer.android.com/develop/sensors-and-location/location/request-updates)
- [官方文档：地理围栏](https://developer.android.com/develop/sensors-and-location/location/geofencing)
- [官方文档：定位电池优化](https://developer.android.com/develop/sensors-and-location/location/battery/optimize)
- [官方文档：定位运行时权限](https://developer.android.com/develop/sensors-and-location/location/permissions/runtime)
- [官方文档：后台定位限制](https://developer.android.com/develop/sensors-and-location/location/background)
- [官方文档：Foreground service types](https://developer.android.com/develop/background-work/services/fgs/service-types#location)
- [官方文档：前台服务后台启动限制](https://developer.android.com/develop/background-work/services/fgs/restrictions-bg-start)
- [官方文档：原始 GNSS 测量](https://developer.android.com/develop/sensors-and-location/sensors/gnss)
- [官方文档：Wi-Fi RTT](https://developer.android.com/develop/connectivity/wifi/wifi-rtt)
- [官方 API：BLE ScanSettings](https://developer.android.com/reference/android/bluetooth/le/ScanSettings)
- [Google Play services：LocationRequest.Builder](https://developers.google.com/android/reference/com/google/android/gms/location/LocationRequest.Builder)
- [Google Play services：Geofence.Builder](https://developers.google.com/android/reference/com/google/android/gms/location/Geofence.Builder)
- [AOSP：LocationManagerService](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/location/LocationManagerService.java)
- [AOSP：LocationProviderManager](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/location/provider/LocationProviderManager.java)
- [AOSP：PowerStatsService](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/powerstats/PowerStatsService.java)
- 详见 §25.5 定位与传感器功耗优化（基础权衡）
- 详见 §5.17 Android 17 FGS 类型声明与后台执行性能边界
- 详见 §11.2 App 耗电优化（功耗入口体系）
