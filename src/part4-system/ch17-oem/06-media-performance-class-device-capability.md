---
title: "Media Performance Class 与设备能力分级"
chapter: "17.6"
status: ready-for-review
drafted_date: "2026-05-18"
applicable_versions: "Android 12 (API 31) - Android 17 (API 37); Android 11 可通过 Jetpack Core / Google Play services 回退读取"
last_verified: "2026-05-18"
last_verified_against: "AOSP main Build.java + Android 16 CDD + Android Developers Performance class docs"
confidence: high
sources:
  - type: official
    path: "https://developer.android.com/topic/performance/performance-class"
  - type: official
    path: "https://android-developers.googleblog.com/2025/01/performance-class-helps-google-maps-deliver-premium-experiences.html"
  - type: official
    path: "https://android-developers.googleblog.com/2022/03/using-performance-class-to-optimize.html"
  - type: official
    path: "https://source.android.com/docs/compatibility/16/android-16-cdd#227_handheld_media_performance_class"
  - type: official
    path: "https://source.android.com/docs/compatibility/cts/media-cts"
  - type: aosp
    path: "frameworks/base/core/java/android/os/Build.java#Build.VERSION.MEDIA_PERFORMANCE_CLASS"
  - type: aosp
    path: "frameworks/support/core/core-performance/src/main/java/androidx/core/performance/DevicePerformance.kt"
  - type: aosp
    path: "frameworks/support/core/core-performance-play-services/src/main/java/androidx/core/performance/play/services/PlayServicesDevicePerformance.kt"
tags: [media-performance-class, device-capability, oem, camera, media]
related_chapters: ["8.8", "14.9", "17.2", "18.14", "25.10"]
created_by: "task2a-knowledge-gap"
created_date: "2026-05-18"
gap_source: "官方文档"
source_candidates:
  - "https://developer.android.com/topic/performance/performance-class"
  - "https://source.android.com/docs/compatibility/16/android-16-cdd"
  - "https://source.android.com/docs/compatibility/cts/media-cts"
  - "https://android-developers.googleblog.com/2022/03/using-performance-class-to-optimize.html"
---

# 17.6 Media Performance Class 与设备能力分级

Media Performance Class（MPC）把设备能力从机型名、SoC 型号、内存大小这些松散信号里抽出来，变成一个可在运行时读取的能力等级。App 侧用它做功能分级：高等级设备打开更高规格的视频、相机、图像处理或复杂 UI，低等级设备走保守配置，避免把体验押在机型白名单上。

MPC 不是通用跑分。它来自 Android CDD 中的兼容性要求，并由 CTS、Media CTS、Camera ITS 等测试验证，覆盖媒体、相机、图形、内存和存储等与体验强相关的能力。工程上要把它当成“能力分桶”，再结合运行时 API 和线上指标做最终决策。[已验证: 官方文档, developer.android.com/topic/performance/performance-class]

## 能力等级的读取边界

Android 12 开始，系统通过 `Build.VERSION.MEDIA_PERFORMANCE_CLASS` 暴露设备声明的 MPC。AOSP `Build.java` 对这个字段的定义很直接：返回 0 表示没有声明；非 0 值对应 `Build.VERSION_CODES` 中的 Android 版本号，从 `R`（Android 11 / API 30）开始；设备启动后这个值不变，但厂商 OTA 后可能提高。[已验证: AOSP main, frameworks/base/core/java/android/os/Build.java]

这个字段有三个边界要写进业务判断：

- `0` 是一个正常分桶：它表示系统没有可用的 MPC 信息，不等于设备不能运行高规格功能。低端机、未声明设备、Google Play services 不可用的环境都可能落到这一档。
- MPC 与当前系统版本分离：一台 Android 14 设备可以继续报告 MPC 33，因为它满足 Android 13 的能力要求，但没有达到 MPC 34 的要求。[已验证: 官方文档, Performance class forward-compatible]
- 同一 Android 版本下能力不同：版本号只能说明平台 API 集合，不能说明并发编解码、相机启动延迟、存储随机读写、HDR 显示等硬件能力。

官方现在推荐通过 Jetpack Core Performance 读取 MPC。`core-performance` 提供 `DevicePerformance` 接口，`core-performance-play-services` 提供 `PlayServicesDevicePerformance`；后者会先尝试从 Google Play services 获取基于认证结果更新的 MPC，取不到时回退到设备声明的 build 常量。[已验证: AOSP androidx, PlayServicesDevicePerformance.kt]

下面的代码展示一种业务侧封装方式，重点是把 `0` 单独处理，并且不要在每个页面重复初始化 `DevicePerformance`。

```kotlin
import android.app.Application
import android.os.Build
import androidx.core.performance.DevicePerformance
import androidx.core.performance.play.services.PlayServicesDevicePerformance

class App : Application() {
    lateinit var devicePerformance: DevicePerformance
        private set

    override fun onCreate() {
        super.onCreate()
        devicePerformance = PlayServicesDevicePerformance(applicationContext)
    }
}

enum class MediaTier {
    Unknown,
    Functional,
    High,
    Premium,
}

fun DevicePerformance.toMediaTier(): MediaTier {
    val mpc = mediaPerformanceClass
    return when {
        mpc == 0 -> MediaTier.Unknown
        mpc >= Build.VERSION_CODES.UPSIDE_DOWN_CAKE -> MediaTier.Premium // MPC 34+
        mpc >= Build.VERSION_CODES.TIRAMISU -> MediaTier.High           // MPC 33
        else -> MediaTier.Functional                                    // MPC 30/31
    }
}
```

这里没有把 `Unknown` 等同于“低端”。线上灰度时可以让 `Unknown` 进入保守默认值，也可以继续按内存、SoC、屏幕刷新率、运行时 capability 做二次分组。

## CDD 约束覆盖哪些硬件能力

Performance Class 的定义放在每个 Android 版本对应的 CDD 中。Android Developers 文档按 MPC 31、33、34、35 展示能力范围；Android 16 CDD 的 2.2.7 节继续列出 Handheld Media Performance Class 要求，并把媒体、相机、硬件、性能、图形分开描述。[已验证: 官方文档, source.android.com/docs/compatibility/16/android-16-cdd#227_handheld_media_performance_class]

| 覆盖类别 | CDD/官方文档中的约束方向 | App 侧可用来判断什么 |
| --- | --- | --- |
| 媒体编解码 | 并发硬件 decoder / encoder 数量、`CodecCapabilities.getMaxSupportedInstances()`、`VideoCapabilities.getSupportedPerformancePoints()`、帧丢失、HDR codec、编码质量 | 多路视频播放、拍摄后转码、短视频导出、直播推流的默认分辨率和码率 |
| 相机 | 主摄分辨率、4K/1080p/720p 采集能力、Camera2 hardware level、timestamp source、启动延迟、JPEG capture latency、RAW、预览防抖、夜景扩展、JPEG_R | 拍摄规格、预览尺寸、滤镜开关、连拍/夜景入口、相机冷启动体验预期 |
| 显示与图形 | 屏幕分辨率、密度、HDR display、硬件 overlay、EGL/Vulkan 扩展、受保护内容能力 | HDR 预览、透明层/叠加层、地图/视频 UI 特效、Surface 合成路径风险 |
| 内存 | 物理内存与 kernel 可用内存下限 | 图像缓存、视频 buffer 数量、端侧模型大小、后台任务并发度 |
| 存储与系统性能 | 顺序/随机读写、并行读写要求，CTS 文件系统测试 | 首次解压、素材导入、离线包写入、数据库批量迁移的默认策略 |

这张表不能替代运行时 API。MPC 给的是一组被验证过的能力下限，具体设备在发热、低电量、后台压力、厂商调度策略下仍然会波动。涉及单项硬件能力时，仍要查询 `MediaCodecInfo`、`CameraCharacteristics`、`Display.Mode`、`ActivityManager.MemoryInfo` 等 API。[已验证: 官方文档, Google Maps Performance Class blog]

## App 侧按能力分级做功能降级

MPC 最适合处理“高规格体验要不要默认打开”这类问题。它比机型白名单更适合新机发布，因为通过认证的新设备可以直接进入对应分桶；它也比单看内存更稳，因为 CDD 同时约束媒体、相机、图形和存储能力。

常见策略可以按场景拆成几类：

- 视频拍摄与导出：MPC 34+ 设备默认启用更高分辨率、更高码率或 HDR 入口；MPC 33 设备保留高质量但降低并发转码；MPC 30/31 或 `Unknown` 设备默认 720p/1080p、30 fps，并把 4K、HDR、实时美颜放到手动开关后面。
- 相机预览：高等级设备可以优先尝试高分辨率预览、预览防抖、夜景扩展；低等级设备优先保证 preview frame 稳定、拍照成功率和首帧时间。相机规格仍要以 `CameraCharacteristics` 和 CameraX capability 查询为准，MPC 只决定默认候选集合。
- 图片处理：高等级设备允许更大的 bitmap tile、更高阶滤镜和更多中间 buffer；低等级设备限制滤镜链长度，优先使用分块处理、降采样和后台队列。
- WebView / Hybrid：Google Maps 的案例说明，透明层这类 UI 调整会增加渲染面积和延迟。可以先按 MPC 分桶观察 `seconds to UI item visibility`、首屏时间和掉帧，再决定从高等级设备向下扩灰。[已验证: 官方博客, Performance Class helps Google Maps]
- 端侧 AI 推理：MPC 可作为初始分桶，决定模型大小、输入分辨率、线程数和是否启用实时预览推理；最终还要结合 NNAPI / GPU delegate 支持、可用内存、温度和实测耗时。

业务配置不要只写“`mpc >= 34` 打开功能”。更稳的做法是把 MPC 放进 feature flag 规则，再加运行时 capability 和灰度指标。某些功能只依赖单项能力，例如 AV1 解码、HDR display、RAW capture，直接查对应 API 更准确；MPC 更适合一组能力一起影响体验的场景。

## 线上指标要携带设备能力标签

MPC 的工程价值在后台分析里更容易体现。没有能力标签时，同一个版本的性能波动容易被误判成代码回归；补上标签后，可以区分三类问题：功能本身变慢、低能力设备承压、厂商配置差异。

建议至少上报这些维度：

| 维度 | 用途 | 取值建议 |
| --- | --- | --- |
| `media_performance_class` | 按能力等级切性能指标、错误率和灰度结果 | 原始 int 值；`0` 单独成桶 |
| `sdk_int` / `device_initial_sdk_int` | 区分当前系统版本和出厂版本 | `Build.VERSION.SDK_INT`；出厂版本只在内部工具或可用 API 中读取 |
| SoC / ABI / CPU core 信息 | 分析厂商调度、架构差异和 native 性能 | 只上报规范化后的平台标签，避免高基数字段失控 |
| 内存与低内存标记 | 区分缓存策略、OOM 和低端设备压力 | 总内存区间、`isLowRamDevice()`、进程可用内存区间 |
| 存储与 I/O 指标 | 解释启动解压、数据库迁移、素材导入耗时 | 线上耗时分位数优先，设备静态标签只作辅助 |
| 屏幕与刷新率 | 分析 UI 掉帧、功耗和合成成本 | 分辨率区间、刷新率区间、HDR capability |

灰度平台可以把 MPC 作为实验维度。Google Developers Blog 的 Google Maps 案例就是先把关键指标按 MPC 分桶，发现无 MPC 设备延迟上升最大，再将高风险 UI 调整限制到有 MPC 的设备上发布。这个做法比一次性全量更容易定位问题，也能为后续向低等级设备扩灰提供数据。[已验证: 官方博客, Performance Class helps Google Maps]

## OEM 差异与 CTS 证据链

同一 SoC 不必然对应同一 MPC。厂商的 camera HAL、codec 配置、存储颗粒、散热策略、显示能力和 OTA 认证状态都会影响最终等级。AOSP 对 `MEDIA_PERFORMANCE_CLASS` 的注释也说明，设备启动后值不变，但 OTA 后可能提高。[已验证: AOSP main, Build.java]

排查设备能力差异时，证据优先级可以这样排：

1. App 运行时读取的 `DevicePerformance.mediaPerformanceClass` 或 `Build.VERSION.MEDIA_PERFORMANCE_CLASS`。
2. 对应 Android 版本 CDD 的 MPC 条款，确认这一等级承诺了哪些能力。
3. CTS / Media CTS / Camera ITS 结果，确认厂商声明背后的测试依据。[已验证: 官方文档, source.android.com/docs/compatibility/cts/media-cts]
4. `MediaCodecInfo`、`CameraCharacteristics`、`Display`、`ActivityManager` 等运行时 API，确认当前设备当前状态能用什么能力。
5. 实机 Perfetto、APM 分位数、灰度指标，确认功能打开后的用户体验。

这套顺序可以避免两个常见误判：把“设备没有 MPC”直接判成“设备差”，以及把“设备有高 MPC”直接判成“任何高规格功能都安全”。MPC 给的是认证时能力下限，业务体验仍要接受当前负载、温度、电量、后台状态和厂商策略的影响。

## 与媒体、相机和渲染章节的引用关系

本节只处理设备能力分级和工程决策。媒体管线的 buffer、codec、Muxer、Extractor 和 AudioTrack 细节详见 8.8 节；Camera Trace 抓取和 SQL 分析详见 14.9 节；Camera 预览、SurfaceTexture、SurfaceView、TextureView 的渲染路径详见 18.14 节；WebView / Hybrid 的功耗取舍详见 25.10 节。

在 Part 5 的实战章节里，MPC 应该作为“默认策略怎么选”的输入，不重复展开 CDD 和 CTS 背景。遇到具体问题时，仍按对应章节的工具链回到 trace、runtime capability 和线上指标。

## Android 17 媒体与相机新能力的分级接入

[自动发现] 截至本轮校验，Android Developers Performance Class 文档公开到 MPC 35（Android 15）。Android 16 CDD 仍通过 `MEDIA_PERFORMANCE_CLASS` 引用 Android 14 / Android 15 等既有等级要求；Android 17 相关媒体、相机和 AI 能力不应直接推导成新的 MPC 等级。[待验证: Android 17 CDD / MPC 37 公共定义尚未纳入本轮来源]

接入新能力时建议按三层判断：

- 平台 API：新 API 是否存在，目标 SDK、权限和兼容行为是什么。
- 设备声明：Camera、MediaCodec、Display、GPU、NNAPI 等 capability 是否返回支持。
- 业务策略：MPC 是否足够高，线上指标是否允许默认打开，低等级设备是否有可接受的替代路径。

这样处理后，Android 17 的新能力不会被系统版本号绑死。高等级设备可以更早试点，低等级设备仍然能保留稳定体验。

## 低等级设备的体验保护策略

低等级和 `Unknown` 设备需要的是保守默认值，不是功能缺席。体验保护可以从这些位置开始：

- 帧率：默认 30 fps，只有在持续帧间隔稳定、温度正常、用户主动选择时才提高到 60 fps。
- 分辨率：拍摄、预览、导出分开配置；预览优先稳定，导出可以后台慢一点。
- 码率：按网络和存储一起限制，避免低端设备在编码和上传阶段同时承压。
- 滤镜：限制实时滤镜链长度，把高成本效果放到拍后处理或离线导出。
- 后台任务：限制并发转码、上传、预热和索引任务，避免与前台预览抢 CPU / GPU / I/O。
- 缓存：降低图片 tile、视频 buffer、WebView 资源预取和端侧模型缓存上限。

这类策略要配合线上 P90 / P95 观察。P50 变快不能说明低等级设备安全，还要看失败率、温度相关降频、前后台切换和低电量场景。

## 参考资料

- [官方文档: Performance class | Android Developers](https://developer.android.com/topic/performance/performance-class)
- [官方博客: Using performance class to optimize your user experience](https://android-developers.googleblog.com/2022/03/using-performance-class-to-optimize.html)
- [官方博客: Performance Class helps Google Maps deliver premium experiences](https://android-developers.googleblog.com/2025/01/performance-class-helps-google-maps-deliver-premium-experiences.html)
- [Android 16 CDD: Handheld Media Performance Class](https://source.android.com/docs/compatibility/16/android-16-cdd#227_handheld_media_performance_class)
- [AOSP: Build.VERSION.MEDIA_PERFORMANCE_CLASS](https://android.googlesource.com/platform/frameworks/base/+/refs/heads/main/core/java/android/os/Build.java)
- [AOSP AndroidX: DevicePerformance](https://android.googlesource.com/platform/frameworks/support/+/refs/heads/androidx-main/core/core-performance/src/main/java/androidx/core/performance/DevicePerformance.kt)
- [AOSP AndroidX: PlayServicesDevicePerformance](https://android.googlesource.com/platform/frameworks/support/+/refs/heads/androidx-main/core/core-performance-play-services/src/main/java/androidx/core/performance/play/services/PlayServicesDevicePerformance.kt)
