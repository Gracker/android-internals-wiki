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
related_chapters: ["18.23", "14.20", "17.2", "18.14", "25.10"]
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

Media Performance Class（MPC）是设备声明的一组媒体体验下限。它把 codec、相机、音频、显示、内存、存储和图形等要求绑定到一个整数，App 可在运行时读取该值并选择默认体验。

MPC 不代表通用性能分数，也不能替代某项能力的运行时查询。一个设备可以满足很高的媒体等级，却在特定温度、后台压力或 OEM 策略下表现波动；另一个值为 0 的设备也可能支持某项高规格功能，只是没有可用的 MPC 声明。

平台锚点是 Android 17 / API 37 / `android-17.0.0_r1`。Android 17 对 MPC 做了结构性调整，旧文章里常见的“等级只会等于 Android API level”已经不完整。

## Android 17 新增了四个等级

Android 17 CDD 的 2.2.7 节新增 MPC 1、10、20、37，并把每项阈值移到独立的 supplemental 文档。Android 17 定义的等级集合是：

| 原始值 | 定位 | 版本来源 |
|---:|---|---|
| `0` | 未定义或没有可用声明 | 特殊值 |
| `1` | Android 17 新增的基础等级 | CDD 17 |
| `10` | Android 17 新增的入门媒体等级 | CDD 17 |
| `20` | Android 17 新增的中间等级 | CDD 17 |
| `30` | Android 11 的 MPC 30 | CDD 11 |
| `31` | Android 12 的 MPC 31 | CDD 12 |
| `33` | Android 13 的 MPC 33 | CDD 13 |
| `34` | Android 14 的 MPC 34 | CDD 14 |
| `35` | Android 15 的 MPC 35 | CDD 15 |
| `37` | Android 17 的最高等级 | CDD 17 |

MPC 32 和 36 没有定义。新等级 1、10、20 让厂商可以声明低于 MPC 30 的已验证能力集，减少“只有高端设备有 class，其余全部是 0”的信息缺口。MPC 37 则提高内存、I/O、音频与部分媒体、相机要求。

表中的“基础、入门、中间”只用于区分档位，不是 CDD 的正式等级名称。

Android Developers 的概览页截至 2026 年 5 月仍只列到 MPC 35；Android 17 CDD 和 2026 年 6 月发布的 supplemental 文档已经包含上述新等级。实现与评审 Android 17 功能时，应以 CDD 17 和 supplemental 表为准。

## 读取字段与声明语义

Android 12 起，公开字段是 `Build.VERSION.MEDIA_PERFORMANCE_CLASS`。Android 17 的 `Build.java` 直接读取设备属性：

```java
public static final int MEDIA_PERFORMANCE_CLASS =
        DeviceProperties.media_performance_class().orElse(0);
```

这段代码只返回一个整数。字段值在一次开机期间保持稳定，厂商 OTA 可以提高它。App 不应缓存到跨版本永久配置中；进程启动时重新读取即可。

Android 17 的 `Build.java` 注释仍写着“非零值定义在 `Build.VERSION_CODES`，从 R 开始”。CDD 17 新增的 1、10、20 并不是 Android SDK 版本号，这条注释没有覆盖新规则。业务代码不能用“所有合法值都等于某个 `VERSION_CODES` 常量”作为校验条件。

### 值为 0 时知道了什么

`0` 只表示当前读取路径没有 MPC。常见原因包括：

- 设备没有声明；
- 旧系统没有公开 build 字段；
- Jetpack 或 Play services 回退没有得到认证结果；
- ROM、GMS 可用性或库版本让动态值不可用。

它不能证明设备低端，也不能证明某个 codec、相机或 HDR 能力缺失。业务应给 `0` 安排保守默认值，再通过运行时 capability 打开确认可用的单项功能。

### MPC 与当前 Android 版本分离

设备 OTA 到更高平台后，可以继续报告原有 MPC。例如一台 Android 14 设备可保留 MPC 33，只要它没有满足 MPC 34 的全部要求。反过来，Android 17 设备也可能报告 1、10、20、30、31、33、34、35 或 37。

因此：

- `SDK_INT` 回答平台 API 和兼容行为；
- MPC 回答声明等级对应的能力下限；
- runtime capability 回答当前设备某项功能是否可用；
- 实测数据回答当前负载下能否达到业务体验目标。

这四类信号不能互相替换。

## Jetpack Core Performance 在 Android 17 的兼容缝隙

Android 官方建议通过 Jetpack Core Performance 的 `DevicePerformance` 读取 MPC。`PlayServicesDevicePerformance` 会从本地 DataStore 读取 Google Play services 的结果，与默认读取器取最大值，并异步请求新结果写回 DataStore。

这个实现有两个容易忽略的细节：

1. 当前对象的 `mediaPerformanceClass` 使用 lazy 值。若首次访问发生在异步 Play services 更新完成前，本次对象可能继续使用旧的持久化结果，适合在 `Application` 层初始化并在后续进程使用更新值。
2. 截至本轮核对的 `androidx-main`，`DefaultDevicePerformance.isPerformanceClassValid()` 仍要求值至少为 `Build.VERSION_CODES.R`，即 30。它会把 `Build.VERSION.MEDIA_PERFORMANCE_CLASS` 返回的 1、10、20 当作无效值并回退到 0。

第二点是 CDD 17 新等级与当前 Jetpack fallback 代码之间的兼容缝隙。它不影响 Play services 已写入 1、10、20 后的读取，因为 `PlayServicesDevicePerformance` 对持久化结果直接取 `max`；但只依赖 build property 的 fallback 会丢失新低阶值。

接入前应对所用 Jetpack 版本做一次单元测试。在 API 31 及以上，业务若要完整识别 CDD 17 等级，可以同时保留 raw platform 值，并明确二者的取值优先级。

下面的 Kotlin 代码展示一种只接受 Android 17 已定义等级的规范化方法。

```kotlin
object MpcLevel {
    const val UNDEFINED = 0
    const val BASIC = 1
    const val ENTRY = 10
    const val MID = 20
    const val LEVEL_30 = 30
    const val LEVEL_31 = 31
    const val LEVEL_33 = 33
    const val LEVEL_34 = 34
    const val LEVEL_35 = 35
    const val LEVEL_37 = 37

    val defined = setOf(
        BASIC, ENTRY, MID,
        LEVEL_30, LEVEL_31, LEVEL_33,
        LEVEL_34, LEVEL_35, LEVEL_37
    )
}

enum class MediaTier {
    Unknown,
    Basic,
    Entry,
    Mid,
    Established,
    High,
    Premium,
}

fun normalizeMpc(raw: Int): MediaTier = when (raw) {
    MpcLevel.BASIC -> MediaTier.Basic
    MpcLevel.ENTRY -> MediaTier.Entry
    MpcLevel.MID -> MediaTier.Mid
    MpcLevel.LEVEL_30,
    MpcLevel.LEVEL_31,
    MpcLevel.LEVEL_33 ->
        MediaTier.Established
    MpcLevel.LEVEL_34,
    MpcLevel.LEVEL_35 -> MediaTier.High
    MpcLevel.LEVEL_37 -> MediaTier.Premium
    else -> MediaTier.Unknown
}
```

显式集合能避免把 MPC 1、10、20 当成旧版非法值，也不会把未定义的 32、36 或损坏数据静默归到某个等级。`MediaTier` 是产品分桶，不能反向解释为 CDD 的正式名称。

业务如果使用 `PlayServicesDevicePerformance`，建议同时上报 `raw_build_mpc` 与 `resolved_mpc`。两者不一致时，可以区分 OTA 声明、Play services 认证结果和库兼容问题。

## CDD 17 怎样组织要求

Android 17 CDD 2.2.7 保留五类要求：

1. Media
2. Camera
3. Hardware
4. Performance
5. Graphics

每一项 CDD 条款指向 supplemental 文档中的等级表。例如 video decoder concurrent session、camera startup latency、screen resolution、available memory、file-system I/O 都按 MPC 值列出阈值。

“高值一定在每个单项指标上严格大于低值”并不成立。有些等级提高工作负载后允许的计数阈值相同或口径不同，例如 frame-drop 测试会同时改变分辨率、帧率和并发负载。需要判断某项能力时，应查看该 CDD 条款明确列出的适用等级和测试条件。

### Android 17 的选定阈值

下面的表只列对 App 分级较有解释力的项目，完整要求以 supplemental 文档为准：

| 项目 | MPC 1 | MPC 10 | MPC 20 | MPC 30/31 | MPC 33 | MPC 34/35 | MPC 37 |
|---|---:|---:|---:|---:|---:|---:|---:|
| 屏幕最低分辨率 | 320×240 | 1280×720 | 1920×1080 | 1920×1080 | 1920×1080 | 1920×1080 | 1920×1080 |
| kernel 可用内存 | 1.37 GiB | 3.05 GiB | 5 GiB | 5 GiB | 6.64 GiB | 6.64 GiB | 8 GiB |
| 顺序写最低值 | 35 MB/s | 50 MB/s | 100 MB/s | 100/125 MB/s | 125 MB/s | 150 MB/s | 250 MB/s |
| 顺序读最低值 | 125 MB/s | 200 MB/s | 200 MB/s | 200/250 MB/s | 250 MB/s | 250 MB/s | 700 MB/s |
| tap-to-tone native latency 上限 | 110 ms | 110 ms | 100 ms | 100 ms | 80 ms | 80 ms | 65 ms |
| rear primary camera | 无该项要求 | 5 MP、720p30 | 5 MP、720p30 | 12 MP、4K30 | 12 MP、4K30 | 12 MP、4K30；MPC 35 还要求 1080p60/720p60 | 12 MP、4K30、1080p60、720p60 |

表中的 `30/31` 和 `34/35` 用斜线展示相近等级，不能据此认为阈值完全相同。比如 MPC 31 要求 rear RAW capability，MPC 30 不要求；MPC 35 增加 JPEG_R、Ultra HDR 原生相机输出和特定 HLG10 preview stabilization 组合。

### MPC 37 的新增重点

MPC 37 延续 MPC 35 的高规格相机、HDR、codec、DPU overlay、EGL 与 Vulkan要求，并在以下方向提高门槛：

- available memory 提高到 8 GiB；
- 顺序读提高到 700 MB/s，顺序写提高到 250 MB/s，随机读写也有更高阈值；
- tap-to-tone 与 round-trip audio latency 上限降到 65 ms；
- speaker path 必须支持 MMAP；
- 音频 CPU workload 测试要求从 1 个 sine wave 切到 20 个时不发生 buffer underrun；
- USB audio 至少支持 8 路输出和 4 路输入；
- primary front camera 最低分辨率提高到 7.99 MP；
- 继续要求 6 路混合硬件视频 decoder 场景，并限制掉帧。

这些要求说明 MPC 37 仍是媒体体验等级。它不能证明 NPU 算力、通用 CPU 单核跑分、网络质量或整机持续满载性能。

## MPC 与 runtime capability 怎样组合

MPC 适合决定“默认尝试哪组体验”，单项能力仍应从对应 API 读取。

| 业务问题 | MPC 的作用 | 还要查询的运行时信息 |
|---|---|---|
| 多路视频播放 | 选默认路数、分辨率和码率档 | `getMaxSupportedInstances()`、performance points、profile/level、secure codec |
| HDR 播放或编辑 | 选高规格候选设备 | codec color format、HDR type、display HDR capability、surface format |
| 相机 4K/HDR/RAW | 选默认入口和推荐配置 | `CameraCharacteristics`、dynamic range profile、stream configuration、extension availability |
| 实时滤镜 | 估算可用内存、I/O 与媒体能力下限 | GPU API、纹理格式、实测 GPU time、thermal |
| 低延迟音频 | 选初始 buffer 与效果复杂度 | AAudio feature、actual stream path、burst size、xrun、round-trip measurement |
| 离线包与素材导入 | 选并发数和批次大小 | 当前可用空间、文件系统耗时、温度与后台限制 |

推荐的决策顺序如下：

1. 用 `SDK_INT` 判断 API 是否存在。
2. 用规范化 MPC 选择保守、标准或高规格候选。
3. 用 runtime capability 删除设备不支持的候选项。
4. 用实测耗时、温度、内存压力和失败率调整默认值。
5. 通过 feature flag 保留快速回退能力。

这个顺序可以避免两类故障：高 MPC 设备因某项 capability 不满足而配置失败，以及值为 0 的设备被无条件关掉本来可用的功能。

## 业务分级不要直接照搬数字比较

旧代码经常这样写：`mpc >= 34` 就启用某个“高级模式”。对只覆盖旧等级的功能，这种写法能工作；Android 17 新增 1、10、20 后，粗略大小比较会掩盖等级集合和条款差异。

更稳的做法是给每个 feature 维护明确要求：

- HDR display 候选：MPC 34、35、37，并继续查询显示 HDR capability；
- rear RAW 候选：MPC 31、33、34、35、37，并继续查询 camera capability；
- JPEG_R 候选：MPC 35、37，并继续查询输出格式与 stream configuration；
- MPC 37 音频路径：只在值等于 37 时使用该等级承诺，再做 stream 实测；
- 未定义或未识别值：进入 Unknown，不自动套用相邻等级。

下面的代码用显式集合表达 feature gate，避免把产品 tier 和 CDD 条款混成一套规则。

```kotlin
private val hdrDisplayMpc = setOf(34, 35, 37)
private val rearRawMpc = setOf(31, 33, 34, 35, 37)
private val jpegRMpc = setOf(35, 37)

fun canOfferHdr(
    mpc: Int,
    displayReportsHdr: Boolean,
    codecSupportsProfile: Boolean,
): Boolean {
    return mpc in hdrDisplayMpc &&
        displayReportsHdr &&
        codecSupportsProfile
}
```

这段逻辑把 CDD 等级、显示声明和 codec profile 都设为必要条件。产品若希望在 MPC 0 设备上灰度 HDR，可以另建一条只依赖完整 runtime capability 与实测名单的实验规则，避免篡改正式 CDD gate。

## 低等级与 Unknown 的体验设计

MPC 1、10、20 不是失败状态。它们提供了比 0 更多的下限信息，可以设计稳定的基础体验：

- MPC 1：侧重轻量媒体、低内存和低 I/O 环境，严格限制 buffer、bitmap、缓存与并发；
- MPC 10：可把 720p30 和较低并发作为初始候选，再查 codec 与 camera；
- MPC 20：具备更高内存、1080p 屏幕与更多 720p codec 并发下限，可采用中等缓存和任务并发；
- MPC 30/31：进入旧版完整媒体 class 范围，但 RAW、codec 组合等差异仍要逐项判断；
- MPC 33 及以上：逐步增加 AV1、secure codec、camera、HDR、图形和音频要求；
- MPC 37：适合高规格默认候选，持续负载仍要看 thermal 与实测。

值为 0 或未识别值时，可以使用以下保护策略：

- 视频默认从单路 720p/1080p30 开始；
- 相机 preview 与 capture 分开选尺寸，优先保证首帧与成功率；
- 实时滤镜控制中间 buffer 数量，提供关闭入口；
- 转码、上传、索引和模型任务限制并发；
- 缓存预算结合 `isLowRamDevice()`、可用内存和进程 trim 信号；
- 通过线上性能与失败率逐步开放，而非维护庞大的机型白名单。

## 上报和灰度要保留原始值

Android 17 新增非 API-level 数值后，原始 MPC 更值得保留。建议至少上报：

| 字段 | 用途 |
|---|---|
| `raw_build_mpc` | 设备 build property 声明 |
| `resolved_mpc` | Jetpack / Play services 对外提供值 |
| `normalized_mpc_tier` | 产品分桶 |
| `sdk_int` | 当前平台 API |
| `device_initial_sdk_int` | 出厂平台，API 可用时记录 |
| runtime capability bitset | codec、camera、display、GPU 等关键能力 |
| memory / low-RAM bucket | 解释缓存、OOM 与进程回收 |
| thermal state / sustained duration | 区分短时峰值与稳定表现 |

不要只上报 tier。原始值能发现三类问题：新等级未被旧客户端识别、Jetpack fallback 与 build property 不一致、设备 OTA 后声明变化。

灰度结果应按 MPC、capability 和 OEM/SoC 交叉观察，同时控制高基数字段。Google Maps 的公开案例采用 performance class 对关键指标分桶，发现无 MPC 设备在 UI 改动下延迟增长更明显，再限制高风险体验的发布范围。这个思路适合功能放量，不代表所有 MPC 0 设备都慢。

## OEM 认证与测试证据

同一个 SoC 可以出现在不同 MPC。camera HAL、codec 配置、存储、内存、音频路径、显示、散热与整机集成都会影响设备能否声明某一级。

Android 17 的证据链包括：

1. 设备通过 `Build.VERSION.MEDIA_PERFORMANCE_CLASS` 声明等级。
2. CDD 17 2.2.7 定义条款，supplemental 文档给出每级阈值。
3. `cts-media-performance-class` test plan 验证 media 与 camera MPC 条款；相关 camera CTS 与 Camera ITS 覆盖相机要求。
4. 设备运行时 API报告具体能力。
5. App 的 trace、耗时分布、温度、功耗和错误率确认业务体验。

App 只能信任公开声明和运行时 API，不能访问 OEM 的完整认证报告。缺少 MPC 时，也不能自行跑少量 benchmark 后伪造一个“等价 MPC”；内部 benchmark 只适合作为产品自己的能力标签。

## Android 17 的工程结论

- Android 17 定义了 MPC 1、10、20、30、31、33、34、35、37；0 表示未定义。
- MPC 1、10、20 打破了“所有非零值都等于 Android API level”的旧假设。
- `Build.VERSION.MEDIA_PERFORMANCE_CLASS` 是 raw platform 声明，一次开机内稳定，OTA 后可能提高。
- 当前 AndroidX 默认 fallback 仍过滤掉小于 30 的 build 值；使用 MPC 1、10、20 前要验证库版本或读取 raw platform 值。
- CDD 17 把阈值放在 supplemental 文档，业务不能只读旧版 Android Developers 概览。
- MPC 是组合能力下限。单项功能仍要查询 codec、camera、display、memory 等 runtime capability。
- 功能 gate 应按 CDD 明确的等级集合表达，未识别值进入 Unknown。
- 高 MPC 不能消除温度、后台负载、OEM 调度与驱动差异，发布决策仍需线上指标。

## 参考资料

- [Android 17 CDD：Handheld Media Performance Class](https://source.android.com/docs/compatibility/17/android-17-cdd#227_handheld_media_performance_class)
- [Android 17 MPC supplemental information](https://source.android.com/docs/compatibility/17/mpc)
- [Android 17 `Build.VERSION.MEDIA_PERFORMANCE_CLASS`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/os/Build.java)
- [Android Developers：Performance class](https://developer.android.com/topic/performance/performance-class)
- [AndroidX `DevicePerformance`](https://android.googlesource.com/platform/frameworks/support/+/refs/heads/androidx-main/core/core-performance/src/main/java/androidx/core/performance/DevicePerformance.kt)
- [AndroidX `DefaultDevicePerformance`](https://android.googlesource.com/platform/frameworks/support/+/refs/heads/androidx-main/core/core-performance/src/main/java/androidx/core/performance/DefaultDevicePerformance.kt)
- [AndroidX `PlayServicesDevicePerformance`](https://android.googlesource.com/platform/frameworks/support/+/refs/heads/androidx-main/core/core-performance-play-services/src/main/java/androidx/core/performance/play/services/PlayServicesDevicePerformance.kt)
- [运行 Media Performance Class 测试](https://source.android.com/docs/compatibility/cts/media-cts)
- [Google Maps 使用 Performance Class 的案例](https://android-developers.googleblog.com/2025/01/performance-class-helps-google-maps-deliver-premium-experiences.html)
- [早期 Performance Class 应用案例](https://android-developers.googleblog.com/2022/03/using-performance-class-to-optimize.html)
