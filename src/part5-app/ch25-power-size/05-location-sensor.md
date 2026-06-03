title: "定位与传感器功耗优化"
chapter: "25.5"
section: "25.5"
status: finalized
applicable_versions: "Android 10 (API 29) - Android 16 (API 36)"
last_verified: "2026-05-14"
last_verified_against: "Android Developers location / sensors docs + Google Play services LocationRequest docs + AOSP sensor batching docs + Clippings structure references"
confidence: medium-high
drafted_date: "2026-05-14"
polish_count: 0
sources:
  - type: official
    path: "https://developer.android.com/develop/sensors-and-location/location/battery"
  - type: official
    path: "https://developer.android.com/develop/sensors-and-location/location/battery/optimize"
  - type: official
    path: "https://developer.android.com/develop/sensors-and-location/location/battery/scenarios"
  - type: official
    path: "https://developer.android.com/about/versions/oreo/background-location-limits"
  - type: official
    path: "https://developer.android.com/develop/sensors-and-location/location/geofencing"
  - type: official
    path: "https://developers.google.com/android/reference/com/google/android/gms/location/LocationRequest"
  - type: official
    path: "https://developers.google.com/android/reference/com/google/android/gms/location/Priority"
  - type: official
    path: "https://developer.android.com/develop/sensors-and-location/sensors/sensors_overview"
  - type: official
    path: "https://developer.android.com/reference/android/hardware/SensorManager"
  - type: aosp
    path: "https://source.android.com/devices/sensors/batching"
  - type: clippings-structure-ref
    path: "Clippings/Android 性能优化 - 如何才能做好 Android 性能优化？.md"
tags: [location, fused-location, geofencing, sensor-batching, power]
related_chapters: ["25.1", "25.2", "11.2"]
pipeline_stage: ready-to-publish
task6_state: reviewed
task9_state: reviewed
last_task9_autofix_at: "2026-06-03"
task9_result: auto-fixed
last_task9_at: "2026-05-14T18:30:00+08:00"
task9_reviewed_by: openclaw-task9
task9_reviewed_date: "2026-05-14"
last_task9_review_log: "logs/deep-review/2026-05-14-18-deep-review.md"
task2b_state: fixed
task2b_result: fixed
last_task2b_at: "2026-06-03T14:54:49+08:00"
task2b_fixed_by: "openclaw-task2b"
task2b_fixed_date: "2026-06-03"
reviewed_by: openclaw-task6
reviewed_date: "2026-06-03"
task6_result: pass-light-edit
last_task6_at: "2026-06-03T21:36:06+08:00"
last_task6_review_log: logs/review/2026-05-14-19-review.md
task6_review_notes: "2026-05-14 Task6：L1/L2 小修 2 处；写作层通过。保留 Task9 P1 回炉队列，未自动晋升。"

# 定位与传感器功耗优化

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 定位精度与功耗的权衡
- 🔹 Fused Location Provider 最佳实践
- 🔹 Geofencing 与被动定位
- 🔹 传感器批处理与采样率控制

### 扩展（可选深入）

- 🔸 （待扩展）

### OpenClaw 加工指引

> **锚点**是最低覆盖要求，加工时必须逐条落实并标注验证结果。
> **扩展**视素材丰富程度选择性深入。
> 如果从 Obsidian 素材或 AOSP 源码中发现大纲未列出但与本节强相关的知识点，
> 可**就地插入**最相关的锚点之后，并用 `[自动发现]` 标注，方便后续 review。
> 锚点内容需 L1/L2 验证，扩展内容至少 L2 验证，自动发现内容至少标注来源。
<!-- outline-end -->

## 为什么要了解定位与传感器功耗优化

定位和传感器功耗的治理对象很明确：减少 GNSS、Wi-Fi 扫描、蜂窝定位、传感器采样和 App 进程唤醒次数。§11.2 已经讲过 App 耗电入口，§25.1 负责诊断工具，§25.2 负责后台限制；后文围绕代码参数、生命周期和验证口径展开。

Clippings 的《Android 性能优化》没有单独展开定位或传感器，但它给出的组织方式适合迁移到本节：先把硬件资源、系统调度和 App 业务放在同一张表里，再按场景决定使用频率。定位和传感器的写法也是这样，先问业务要什么精度、多久交付、能否延迟，再选择 FLP、Geofencing、被动定位或传感器批处理。

[结构参考: Clippings/Android 性能优化 - 如何才能做好 Android 性能优化？.md]

## 定位精度与功耗的权衡

Android 官方把定位耗电拆成三个旋钮：精度、频率、延迟。精度越高，系统越可能使用 GNSS、Wi-Fi、蜂窝和传感器融合；频率越高，位置计算越频繁；延迟越低，App 被唤醒得越频繁。App 侧优化不是把定位关掉，而是把这三个旋钮调到业务能接受的最低档。

[已验证: 官方文档, developer.android.com/develop/sensors-and-location/location/battery]

| 场景 | 推荐定位策略 | 更新间隔 | 交付延迟 | 退出条件 |
|------|--------------|----------|----------|----------|
| 地图拖动、导航前台态 | `PRIORITY_HIGH_ACCURACY` 或 `PRIORITY_BALANCED_POWER_ACCURACY` | 秒级到分钟级，按交互强度决定 | 低延迟 | 页面不可见或导航结束立刻移除请求 |
| 天气、城市级内容推荐 | `getLastLocation()` / `PRIORITY_BALANCED_POWER_ACCURACY` | 用户打开页面时取一次 | 可接受缓存 | 页面展示完成后不持续监听 |
| 门店附近提醒 | Geofencing | 系统维护 | 5 到 10 分钟更省电 | 围栏过期、用户退出城市级范围后移除 |
| 后台轨迹补点 | 批量 FLP 或被动定位 | 10 分钟级 | 30 到 60 分钟批量交付 | 业务会话结束、超时或用户关闭开关 |
| 计步、姿态、运动检测 | 低频传感器、on-change / one-shot 优先 | 按动作语义选择 | 能批量就批量 | `onPause()`、前台服务停止或任务完成 |

Android 8.0 起，后台 App 的位置更新会被系统限制到每小时少数几次；同一版本也把后台 Geofencing 的平均响应调整到几分钟级。这个限制不看 target SDK，运行在 Android 8.0 及以上设备就会生效。后台场景要把“延迟几分钟”当成设计前提，不要用秒级轮询去对抗系统策略。

[已验证: 官方文档, developer.android.com/about/versions/oreo/background-location-limits]

## Fused Location Provider 最佳实践

Fused Location Provider（FLP）适合大多数 App 定位场景。它把 GNSS、Wi-Fi、蜂窝和传感器输入交给 Google Play services 融合，业务代码只表达优先级、间隔、最小交付间隔、最大批量延迟和持续时长。Google Play services 文档也明确说明，这些参数是请求提示，系统返回结果可能受权限、设备状态和其他客户端请求影响。

[已验证: Google Play services 文档, developers.google.com/android/reference/com/google/android/gms/location/LocationRequest]

前台连续定位要把“短时间、高精度、强生命周期”写进请求。下面这段代码适合地图选点、短时运动记录这类用户可见场景，重点看 `setDurationMillis()` 和页面停止时的 `removeLocationUpdates()`。

```kotlin
private val foregroundLocationRequest = LocationRequest.Builder(
    Priority.PRIORITY_HIGH_ACCURACY,
    TimeUnit.SECONDS.toMillis(5)
).setMinUpdateIntervalMillis(TimeUnit.SECONDS.toMillis(2))
    .setMinUpdateDistanceMeters(10f)
    .setDurationMillis(TimeUnit.MINUTES.toMillis(20))
    .build()

fun startForegroundTracking() {
    fusedLocationProviderClient.requestLocationUpdates(
        foregroundLocationRequest,
        locationCallback,
        Looper.getMainLooper()
    )
}

fun stopForegroundTracking() {
    fusedLocationProviderClient.removeLocationUpdates(locationCallback)
}
```

`setDurationMillis()` 是兜底超时，不替代 `removeLocationUpdates()`。页面进入后台、导航结束、用户关闭开关时仍要主动移除请求；超时只负责处理异常路径，防止定位请求因为生命周期遗漏一直存在。

[已验证: 官方文档, developer.android.com/develop/sensors-and-location/location/battery/optimize]

后台或弱可见场景要优先批量交付，但先要过三道版本权限门槛：

| 版本 | 要求 | 影响 |
|------|------|------|
| Android 10 (API 29)+ | `ACCESS_BACKGROUND_LOCATION` | 没有该权限，后台定位请求不会返回有效位置；用户必须在设置中授予"始终允许" |
| Android 12 (API 31)+ | 用户可选择 approximate location | app 声明 `ACCESS_FINE_LOCATION` 后，系统仍可能只返回粗略位置；需要调用 `LocationRequest.Builder.setMinUpdateDistanceMeters()` 或检测 `Location.getLatitude()` 精度判断 |
| Android 14 (API 34)+ | location FGS type + while-in-use 启动限制 | 后台启动 Activity/BroadcastReceiver 受限；定位类 FGS 必须声明 `foregroundServiceType="location"`（或 `health`/`remoteMessaging` 等）；`ACCESS_BACKGROUND_LOCATION` 下从后台启动 activity 需走 `PendingIntent` 或通知入口 |

这些限制对 App 定位策略的影响是递进的：Android 10 先收后台定位权限；Android 12 再加用户可控精度；Android 14 再对前台服务类型和后台启动路径施加额外约束。批量交付请求要在所有三道门槛都满足的前提下才成立。

下面这段请求以 10 分钟作为期望计算间隔，并允许系统在 1 小时窗口内批量交付；实际回调合并效果受设备、权限、系统策略和其他客户端请求影响。业务拿到的是一组带时间戳的位置点，适合低频轨迹补点、门店推荐候选刷新、地理内容预热。

```kotlin
private val batchedBackgroundRequest = LocationRequest.Builder(
    Priority.PRIORITY_BALANCED_POWER_ACCURACY,
    TimeUnit.MINUTES.toMillis(10)
).setMaxUpdateDelayMillis(TimeUnit.HOURS.toMillis(1))
    .setDurationMillis(TimeUnit.HOURS.toMillis(6))
    .build()
```

批量定位换来的是交付延迟。服务端、埋点和产品逻辑都要接受“事件发生时间”和“App 收到时间”不一致，用 `Location.time` 或 `Location.elapsedRealtimeNanos` 参与排序，不要用回调到达时间推断用户轨迹。

## Geofencing 与被动定位

Geofencing 适合“到某个区域再工作”的业务。围栏检测由位置服务统一调度，App 不需要周期性启动进程查询当前位置。官方文档建议把 `setNotificationResponsiveness()` 设为较大的值，5 分钟及以上更省电；真实门店、家和公司这类地点还要使用足够大的半径，常见建议是 100 到 150 米起步，再结合 Wi-Fi、室内定位和业务误触成本调整。

[已验证: 官方文档, developer.android.com/develop/sensors-and-location/location/geofencing]
[已验证: 官方文档, developer.android.com/develop/sensors-and-location/location/battery/scenarios]

下面这段代码展示围栏请求的省电参数，重点是半径、过期时间、停留延迟和通知响应延迟。门店类场景不要为每个门店都长期注册围栏；官方 API 单个 App 同时最多 100 个 geofence，更稳的做法是先注册城市级或商圈级大围栏，进入后再注册附近门店的小围栏。

```kotlin
val storeGeofence = Geofence.Builder()
    .setRequestId("store-10086")
    .setCircularRegion(latitude, longitude, 150f)
    .setTransitionTypes(
        Geofence.GEOFENCE_TRANSITION_ENTER or Geofence.GEOFENCE_TRANSITION_DWELL
    )
    .setLoiteringDelay(TimeUnit.MINUTES.toMillis(5).toInt())
    .setNotificationResponsiveness(TimeUnit.MINUTES.toMillis(10).toInt())
    .setExpirationDuration(TimeUnit.HOURS.toMillis(12))
    .build()
```

后台 Geofencing 在 Android 8.0 及以上设备上不会秒级响应。用户刚进入门店就立即弹券的诉求，更适合前台扫码、蓝牙信标、NFC 或用户主动打开页面后的高精度定位；Geofencing 适合低频提醒和状态切换。

被动定位适合“有数据就用，没有也不主动耗电”的场景。Google Play services 当前 `Priority` 文档使用 `PRIORITY_PASSIVE` 表达这类请求，它不会主动触发定位，只接收其他客户端已经计算出的结果。收到被动位置后仍要控制 CPU 和 I/O，避免把省下来的定位功耗又花在频繁写库、上报和网络请求上。

[已验证: Google Play services 文档, developers.google.com/android/reference/com/google/android/gms/location/Priority]

被动定位请求通常只设置较宽的业务窗口和回调上限。下面这段代码不会主动启动定位源，但会把其他 App 或系统场景产生的位置交给当前 App。

```kotlin
private val passiveLocationRequest = LocationRequest.Builder(
    Priority.PRIORITY_PASSIVE,
    TimeUnit.MINUTES.toMillis(15)
).setMinUpdateIntervalMillis(TimeUnit.MINUTES.toMillis(2))
    .setDurationMillis(TimeUnit.HOURS.toMillis(12))
    .build()
```

这种写法的边界也很清楚：它不能保证一定有位置，也不能保证地点新鲜。天气、内容预取、附近推荐可以用；安全告警、跑步轨迹、导航偏航不能只靠它。

## 传感器批处理与采样率控制

传感器耗电的主要成本来自两处：传感器自身采样，以及应用处理器被事件唤醒。Android 传感器批处理把事件暂存在 sensor hub 或硬件 FIFO 中，到达 `max_report_latency` 或 FIFO 满了再上报，减少应用处理器从 suspend 中醒来的次数。硬件 FIFO 越大、批量窗口越长，省电空间越大。

[已验证: AOSP 文档, source.android.com/devices/sensors/batching]

App 代码里对应的入口是 `SensorManager.registerListener(listener, sensor, samplingPeriodUs, maxReportLatencyUs)`。`samplingPeriodUs` 决定采样频率，`maxReportLatencyUs` 决定最长批量上报延迟；如果设备没有硬件 FIFO 或 sensor hub，批处理收益会下降，系统可能更早上报。

[已验证: 官方文档, developer.android.com/reference/android/hardware/SensorManager]

下面这段代码适合低频姿态、运动趋势、环境变化记录。重点看三处：采样周期不要用最快档；最大上报延迟至少给出几十秒级窗口；Activity 暂停时注销监听。

```kotlin
private fun registerBatchedAccelerometer() {
    val accelerometer = sensorManager.getDefaultSensor(Sensor.TYPE_ACCELEROMETER) ?: return

    val samplingPeriodUs = 200_000       // 5 Hz
    val maxReportLatencyUs = 30_000_000  // 最长 30 秒批量上报

    sensorManager.registerListener(
        accelerometerListener,
        accelerometer,
        samplingPeriodUs,
        maxReportLatencyUs
    )
}

private fun flushBatchedSensorsBeforeStop() {
    sensorManager.flush(accelerometerListener)
}

private fun unregisterBatchedSensors() {
    sensorManager.unregisterListener(accelerometerListener)
}
```

`flush()` 会请求把 FIFO 中仍未上报的事件交付给 listener，适合在停止监听前保留剩余一批数据；如果业务必须保存这批数据，要等 `onFlushCompleted()` 或自定义超时后再注销 listener。它不保证所有设备都能提供同样大小的缓冲，产品逻辑不能依赖“30 秒一定攒满多少条事件”。

传感器还有三个容易踩坑的边界：

- 前后台边界：
- Android 9（API 28）+：后台 App 不能接收 continuous 传感器（accelerometer、gyroscope 等）事件，必须使用前台服务并把通知、权限和退出条件写清楚。
- Android 12（API 31）+：运动/位置传感器的后台采样速率被硬限制在 200 Hz 以下；`HIGH_SAMPLING_RATE_SENSORS` 权限只提升前台采样速率上限，对后台 200 Hz 硬限制和 FGS 约束无影响。
- Android 14（API 34）+：健康/运动类传感器长时使用需配合 `foregroundServiceType="health"` 或对应的 FGS type，且 `while-in-use` 权限下后台启动 Activity 需走 `PendingIntent` 或通知入口。
- wake-up 与 non-wake-up：wake-up sensor 可以在 FIFO 满或最大延迟到期时唤醒应用处理器；non-wake-up sensor 在 suspend 中不会主动唤醒应用处理器，旧事件可能被循环缓冲覆盖。
- 采样率上限：`getMinDelay()` 只告诉传感器可支持的最快采样间隔，不代表业务应该使用这个频率。界面姿态、摇一摇、运动趋势通常不需要最快档。

Android 12（API 31）对后台传感器访问追加了速率硬限制：

| 传感器类别 | 后台速率上限 | 所需权限 | 说明 |
|------------|-------------|----------|------|
| 运动传感器（加速度计、陀螺仪、旋转矢量等 continuous sensor） | 200 Hz | 受限：后台不能接收连续事件（Android 9+） | 即使声明 `HIGH_SAMPLING_RATE_SENSORS`，后台也无法绕过此项 |
| 位置传感器（磁力计、orientation 等） | 200 Hz | 后台需 `ACCESS_BACKGROUND_LOCATION`（Android 10+） | Android 12+ `HIGH_SAMPLING_RATE_SENSORS` 仍不能提升后台速率 |
| 环境/健康传感器（心率、血氧等） | 受限速率 | `BODY_SENSORS` + health FGS type（Android 14+） | 长时后台采样必须使用前台服务，不能静默常驻 |
| 姿态传感器（significant motion、step detector 等 one-shot/on-change） | 不适用 | 不需要 FGS | 优先选择这些语义传感器替代高频轮询 |

`HIGH_SAMPLING_RATE_SENSORS` 权限（Android 12+）只提升前台采样速率上限，不能绕过前台服务或后台采样限制。文档中"200 Hz"是系统允许的软上限，设备传感器硬件本身可能支持更高采样率，但系统不会给 App 返回超过上限的事件。产品需求提到"实时运动姿态"时，先确认 200 Hz 是否满足精度，再决定是否上 FGS。

[已验证: 官方文档, developer.android.com/develop/sensors-and-location/sensors/sensors_overview]

| 传感器场景 | 推荐写法 | 不推荐写法 |
|------------|----------|------------|
| 页面内摇一摇、指南针 | `onResume()` 注册，`onPause()` 注销，按交互选择 5 到 20 Hz | Activity 不可见后仍保持监听 |
| 低频运动趋势 | 设置 `maxReportLatencyUs`，批量读取事件 | 每个事件都唤醒线程、写库、上报 |
| 状态变化检测 | 优先 on-change、one-shot、significant motion 等语义化传感器 | 用高频 accelerometer 自己轮询判断阈值 |
| 长时后台采样 | 前台服务 + 低频 + 批处理 + 明确停止条件 | 静默后台常驻采样 |

## [自动发现] 定位和传感器的回归守门

定位和传感器优化要进入回归守门，不能只靠代码 review。§25.1 已经覆盖 Battery Historian、Power Profiler 和 `dumpsys batterystats`，这里补一组和本节参数直接相关的检查项。

这组命令用于确认 App 是否还在后台持有定位请求、传感器监听或异常唤醒。采集前先固定业务场景，例如“后台 30 分钟门店提醒”“息屏 1 小时低频轨迹”“页面退出后 10 分钟”。

```bash
# 查看系统位置请求、provider、geofence 和后台访问情况
adb shell dumpsys location > location.txt

# 查看传感器注册、FIFO、active connection 等信息
adb shell dumpsys sensorservice > sensorservice.txt

# 导出 UID 级耗电统计，和 §25.1 的 Battery Historian 流程配合使用
adb shell dumpsys batterystats --charged > batterystats.txt
```

检查时按三个问题读结果：页面退出后是否还存在高频请求；后台定位是否被批量交付而不是秒级唤醒；传感器 listener 是否在生命周期结束后注销。只要有一项不满足，就回到对应业务入口补退出条件、超时或批处理参数。