---
title: Media Performance Class 与设备能力分级
chapter: '19.5'
section: '19.5'
status: finalized
applicable_versions: Android 12 (API 31) - Android 17 (API 37); Android 11 可通过 Jetpack Core / Google Play services 补充读取
last_verified: '2026-08-14'
last_verified_against: AOSP android-17.0.0_r1 Build.java; Android 17 CDD and MPC supplemental (2026-06-24); AndroidX androidx-main; Android Developers Performance class; CTS guidance (2026-07-13)
confidence: high
task6_state: reviewed
task9_state: reviewed
pipeline_stage: ready-to-publish
sources:
- type: official
  path: https://developer.android.com/topic/performance/performance-class
- type: official
  path: https://android-developers.googleblog.com/2025/01/performance-class-helps-google-maps-deliver-premium-experiences.html
- type: official
  path: https://android-developers.googleblog.com/2022/03/using-performance-class-to-optimize.html
- type: official
  path: https://source.android.com/docs/compatibility/16/android-16-cdd#227_handheld_media_performance_class
- type: official
  path: https://source.android.com/docs/compatibility/cts/media-cts
- type: official
  path: https://source.android.com/docs/compatibility/17/android-17-cdd#227_handheld_media_performance_class
- type: official
  path: https://source.android.com/docs/compatibility/17/mpc
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/os/Build.java
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/support/+/refs/heads/androidx-main/core/core-performance/src/main/java/androidx/core/performance/DevicePerformance.kt
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/support/+/refs/heads/androidx-main/core/core-performance/src/main/java/androidx/core/performance/DefaultDevicePerformance.kt
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/support/+/refs/heads/androidx-main/core/core-performance-play-services/src/main/java/androidx/core/performance/play/services/PlayServicesDevicePerformance.kt
- type: aosp
  path: frameworks/base/core/java/android/os/Build.java#Build.VERSION.MEDIA_PERFORMANCE_CLASS
- type: aosp
  path: frameworks/support/core/core-performance/src/main/java/androidx/core/performance/DevicePerformance.kt
- type: aosp
  path: frameworks/support/core/core-performance-play-services/src/main/java/androidx/core/performance/play/services/PlayServicesDevicePerformance.kt
tags:
- media-performance-class
- device-capability
- oem
- camera
- media
related_chapters:
- '13.10'
- '15.14'
- '19.2'
- '13.9'
- '25.8'
---

# Media Performance Class 与设备能力分级

Media Performance Class（MPC，媒体性能等级）是 Android 兼容性规范定义的一组设备能力下限。它用一个整数关联编解码器（codec）、相机、音频、显示、内存、存储和图形要求，应用可以在运行时读取该值，选择初始体验档位。

MPC 不是通用跑分，也不能替代单项能力查询。设备即使声明了高等级，也可能因温度、后台负载或厂商策略而出现性能波动。值为 0 的设备也可能支持某项高规格功能，只是当前读取路径没有可用的 MPC 声明。

本文以 Android 17、API 37 和 `android-17.0.0_r1` 为平台基线。Android 17 调整了 MPC 的等级结构，“非零等级一定等于某个 Android API 级别”这条旧假设已不再成立。

## Android 17 新增了四个等级

Android 17 兼容性定义文档（CDD）的 2.2.7 节新增 MPC 1、10、20、37，并把各项测量阈值放入独立的补充文档（supplemental document）。Android 17 明确使用的等级集合如下：

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

MPC 32 和 36 没有定义。新等级 1、10、20 为低于 MPC 30 的设备提供了可验证的能力下限，避免它们只能返回 0。MPC 37 则提高了内存、存储 I/O、音频，以及部分媒体和相机要求。

表中的“基础、入门、中间”只是本文为方便阅读使用的档位说明，不是 CDD 的正式等级名称。

截至 2026 年 8 月 14 日，Android Developers 的概览页仍只逐级介绍到 MPC 35，页面标注的更新日期为 2026 年 5 月 19 日。Android 17 CDD 与 2026 年 6 月 24 日更新的 MPC 补充文档已经包含新等级。实现 Android 17 功能时，应以 CDD 17 的 2.2.7 节和对应补充表为等级依据。

Android 17 文档中还有两处遗留冲突。CDD 7.11 节仍要求非零值至少为 `Build.VERSION_CODES.R`（30），并保留只谈 Android T、S、R 的旧文字；`Build.java` 注释也仍说非零值定义在 `VERSION_CODES` 中。它们都与 CDD 2.2.7 明确新增 1、10、20 相冲突。应用解析 Android 17 等级时不能沿用“值必须不小于 30”的校验，设备认证与争议判断则应跟随后续 CDD、CTS 或官方勘误。

## 读取字段与声明语义

从 Android 12（API 31）起，公开字段是 `Build.VERSION.MEDIA_PERFORMANCE_CLASS`。Android 17 的 `Build.java` 直接读取构建时写入的设备属性：

```java
public static final int MEDIA_PERFORMANCE_CLASS =
        DeviceProperties.media_performance_class().orElse(0);
```

这段代码只返回一个整数。字段值在同一次开机期间保持稳定，厂商通过系统更新（OTA）可以提高它。应用不应把该值永久缓存并跨系统版本复用；新进程启动后重新读取即可。

CDD 17 新增的 1、10、20 不是 Android SDK 版本号。平台读取代码不会过滤这些值，过时的是旁边的注释。业务代码也不能再用“所有合法值都等于某个 `VERSION_CODES` 常量”作为校验条件。

### 值为 0 时知道了什么

`0` 只表示当前读取路径没有可用的 MPC。常见原因包括：

- 设备没有声明；
- 旧系统没有公开的 `Build.VERSION` 字段；
- Jetpack 或 Google Play services 的补充读取没有得到结果；
- 系统版本、Google 移动服务（GMS）可用性或库版本使动态结果不可用。

它不能证明设备定位低端，也不能证明某个编解码器、相机或 HDR 能力缺失。业务应为 `0` 选择保守默认值，再通过运行时能力 API 开启已经确认可用的单项功能。

### MPC 与当前 Android 版本分离

设备 OTA 到更高平台后，可以继续报告原有 MPC。例如一台 Android 14 设备可保留 MPC 33，只要它没有满足 MPC 34 的全部要求。反过来，Android 17 设备也可能报告 1、10、20、30、31、33、34、35 或 37。

因此：

- `SDK_INT` 回答平台 API 是否存在以及适用哪套兼容行为；
- MPC 回答声明等级对应的能力下限；
- 运行时能力查询回答当前设备是否支持某项功能；
- 实测数据回答当前负载下能否达到业务体验目标。

这四类信号不能互相替换。

## Jetpack Core Performance 在 Android 17 的兼容性问题

Android 官方建议通过 Jetpack Core Performance 的 `DevicePerformance` 读取 MPC。`PlayServicesDevicePerformance` 先从本地 DataStore 持久化存储中读取 Google Play services 的上次结果，与平台默认读取器的值取较大者；同时异步请求新结果并写回 DataStore。

这个实现有两个容易忽略的细节：

1. `mediaPerformanceClass` 使用延迟初始化值（lazy）：第一次访问时才计算，之后在该对象中缓存。若第一次访问发生在异步 Play services 更新完成前，这个对象会继续使用旧的本地结果；官方因此建议在 `Application.onCreate()` 中只创建一次对象，新结果通常供后续进程使用。
2. 截至 2026 年 8 月 14 日的 `androidx-main`，`DefaultDevicePerformance.isPerformanceClassValid()` 仍要求值至少为 `Build.VERSION_CODES.R`，即 30。它会把 `Build.VERSION.MEDIA_PERFORMANCE_CLASS` 返回的 1、10、20 视为无效并退回 0。

第二点是 CDD 17 新等级与当前 Jetpack 默认读取路径之间的兼容问题。若 Play services 已把 1、10、20 写入 DataStore，`PlayServicesDevicePerformance` 会直接对该持久化结果取 `max`，低等级仍能保留；只依赖平台构建属性的默认读取路径则会丢失这些值。

接入前应对项目实际使用的 Jetpack 版本做一次单元测试。在 API 31 及以上，业务若要完整识别 CDD 17 等级，可以同时保留平台原始值，并明确它与 `DevicePerformance` 结果的取值优先级。

下面的 Kotlin 代码展示一种显式识别 Android 17 已定义等级的转换方法。

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

显式集合能避免把 MPC 1、10、20 当成旧版非法值，也不会把未定义的 32、36 或异常数据悄悄归入某个等级。`MediaTier` 只是产品侧分组，不能反向解释为 CDD 的正式名称。

业务如果使用 `PlayServicesDevicePerformance`，建议同时上报平台原始值 `raw_build_mpc` 与库的最终值 `resolved_mpc`。两者不一致时，可以进一步区分 OTA 后的设备声明、Play services 结果和库兼容问题。

## CDD 17 怎样组织要求

Android 17 CDD 2.2.7 按五类组织要求：

1. Media（媒体）
2. Camera（相机）
3. Hardware（硬件）
4. Performance（性能）
5. Graphics（图形）

各条 CDD 要求会指向补充文档中的等级表。例如硬件视频解码器并发路数、相机启动延迟、屏幕分辨率、可用内存和文件系统 I/O 都按 MPC 值列出阈值。

MPC 数字更高，不表示每个单项阈值都严格高于低等级。有些等级在提高测试负载后仍使用相同的计数阈值，测试口径也可能改变。例如掉帧测试会同时改变分辨率、帧率和并发负载。判断某项能力时，要查看条款明确列出的适用等级、工作负载和通过条件。

### Android 17 的选定阈值

下面只摘录对应用分级较有帮助的项目，完整要求仍以 CDD 与补充文档为准：

| 项目 | MPC 1 | MPC 10 | MPC 20 | MPC 30/31 | MPC 33 | MPC 34/35 | MPC 37 |
|---|---:|---:|---:|---:|---:|---:|---:|
| 屏幕最低分辨率 | 320×240 | 1280×720 | 1920×1080 | 1920×1080 | 1920×1080 | 1920×1080 | 1920×1080 |
| 可供内核使用的内存 | 1.37 GiB | 3.05 GiB | 5 GiB* | 5 GiB | 6.64 GiB | 6.64 GiB | 8 GiB |
| 顺序写最低值 | 35 MB/s | 50 MB/s | 100 MB/s | 100/125 MB/s | 125 MB/s | 150 MB/s | 250 MB/s |
| 顺序读最低值 | 125 MB/s | 200 MB/s | 200 MB/s | 200/250 MB/s | 250 MB/s | 250 MB/s | 700 MB/s |
| 点击到声音反馈的原生延迟上限 | 110 ms | 110 ms | 100 ms | 100 ms | 80 ms | 80 ms | 65 ms |
| 后置主相机 | 无该项要求 | 5 MP、720p30 | 5 MP、720p30 | 12 MP、4K30 | 12 MP、4K30 | 12 MP、4K30；MPC 35 还要求 1080p60/720p60 | 12 MP、4K30、1080p60、720p60 |

`*` Android 17 文档对 MPC 20 内存给出了两个数值：CDD 2.2.7.3 写至少 5.12 GiB，补充表写 5 GiB。表中按补充表抄录并保留此注记。涉及设备合规判定时，应等待官方勘误或以对应 CTS/认证要求为准，不能自行忽略差值。

表中的 `30/31` 和 `34/35` 只是把相近等级合并展示，阈值并非完全相同。例如 MPC 31 要求后置主相机支持 RAW，MPC 30 没有这项要求；MPC 35 增加 `JPEG_R`、原生相机默认输出 Ultra HDR，以及特定 HLG10 预览防抖组合。

### MPC 37 的新增重点

MPC 37 延续 MPC 35 的高规格相机、HDR、编解码器、显示处理单元硬件叠加层（DPU overlay）、EGL 与 Vulkan 要求，并提高了以下门槛：

- 可供内核使用的内存提高到 8 GiB；
- 顺序读提高到 700 MB/s，顺序写提高到 250 MB/s，随机读写也有更高阈值；
- 点击到声音反馈延迟与音频往返延迟上限降到 65 ms；
- 扬声器路径必须支持 MMAP，即内存映射式低延迟音频数据通路；
- 音频 CPU 负载测试从播放 1 个正弦波切换到 20 个正弦波时，不能发生音频缓冲区欠载；
- USB 音频设备至少支持 8 路输出和 4 路输入；
- 前置主相机最低分辨率提高到 7.99 MP；
- 继续要求 6 路硬件视频解码器并发组合，并限制每秒掉帧数。

这些要求仍围绕媒体体验。MPC 37 不能证明 NPU 算力、通用 CPU 单核性能、网络质量或整机长时间满载表现。

## MPC 与运行时能力怎样组合

MPC 适合决定“默认尝试哪组体验”，单项能力仍要从对应 API 读取。

| 业务问题 | MPC 的作用 | 还要查询的运行时信息 |
|---|---|---|
| 多路视频播放 | 选默认路数、分辨率和码率档 | `getMaxSupportedInstances()`、性能点（支持的分辨率与帧率组合）、编码档次与级别、硬件安全解码能力 |
| HDR 播放或编辑 | 筛选高规格候选设备 | 编解码器颜色格式、HDR 类型、显示屏 HDR 能力、Surface 格式 |
| 相机 4K/HDR/RAW | 选默认入口和推荐配置 | `CameraCharacteristics`、动态范围配置、输出流组合、扩展模式可用性 |
| 实时滤镜 | 估算可用内存、I/O 与媒体能力下限 | GPU API、纹理格式、实测 GPU 用时、温控状态 |
| 低延迟音频 | 选初始缓冲区与效果复杂度 | AAudio 功能、实际音频通路、每次突发传输帧数、xrun（缓冲区欠载或溢出）次数、往返延迟实测 |
| 离线包与素材导入 | 选并发数和批次大小 | 当前可用空间、文件系统耗时、温度与后台限制 |

推荐的决策顺序如下：

1. 用 `SDK_INT` 判断 API 是否存在。
2. 用经过显式识别的 MPC 选择保守、标准或高规格候选。
3. 用运行时能力查询剔除设备不支持的候选项。
4. 用实测耗时、温度、内存压力和失败率调整默认值。
5. 通过可远程关闭的功能开关保留快速回退能力。

这个顺序可以避免两类故障：高 MPC 设备因某项能力不满足而配置失败，以及 MPC 为 0 的设备被无条件关闭原本可用的功能。

## 业务分级不要直接照搬数字比较

旧代码经常这样写：`mpc >= 34` 就启用某个“高级模式”。对只覆盖旧等级的功能，这种写法能工作；Android 17 新增 1、10、20 后，粗略大小比较会掩盖等级集合和条款差异。

更稳的做法是为每项功能维护明确的等级集合：

- HDR 显示候选：MPC 34、35、37，并继续查询显示屏的 HDR 能力；
- 后置 RAW 候选：MPC 31、33、34、35、37，并继续查询相机能力；
- `JPEG_R` 候选：MPC 35、37，并继续查询输出格式与输出流组合；
- MPC 37 音频路径：只在值等于 37 时使用该等级承诺，再对实际音频流做测量；
- 未定义或未识别值：进入 `Unknown`，不自动套用相邻等级。

下面的代码用显式集合表达功能启用条件，避免把产品分组与 CDD 条款混成一套规则。

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

这段逻辑把 CDD 等级、显示声明和编解码器档次都设为必要条件。产品若希望在 MPC 0 设备上小范围试验 HDR，可以另建一条依赖完整运行时能力查询与实测名单的实验规则，不要改写正式的 CDD 等级条件。

## 低等级与 Unknown 的体验设计

MPC 1、10、20 不是失败状态。它们比 0 提供了更多经过规范定义的下限信息，可以据此设计基础体验：

- MPC 1：面向轻量媒体、低内存和低 I/O 环境，应严格限制缓冲区、位图、缓存与并发；
- MPC 10：可以把 720p30 和较低并发作为初始候选，再查询编解码器与相机能力；
- MPC 20：提供更高内存、1080p 屏幕与更多 720p 编解码器并发下限，可以采用中等缓存和任务并发；
- MPC 30/31：进入 Android 11/12 定义的媒体等级范围，但 RAW 与编解码器组合等差异仍要逐项判断；
- MPC 33 及以上：逐步增加 AV1、硬件安全解码、相机、HDR、图形和音频要求；
- MPC 37：可以作为高规格默认候选，长时间负载仍要结合温控状态与实测。

值为 0 或未识别值时，可以使用以下保护策略：

- 视频默认从单路 720p/1080p30 开始；
- 相机预览与拍照分别选择尺寸，优先保证首帧时间与成功率；
- 实时滤镜限制中间缓冲区数量，并提供关闭入口；
- 转码、上传、索引和模型任务限制并发；
- 缓存预算结合 `isLowRamDevice()`、当前可用内存和进程内存回收通知；
- 根据线上耗时与失败率逐步开放，避免维护庞大的机型白名单。

## 上报与分阶段发布要保留原始值

Android 17 新增不对应 API 级别的数值后，保留原始 MPC 更有助于排查问题。建议至少上报：

| 字段 | 用途 |
|---|---|
| `raw_build_mpc` | 平台构建属性中的设备声明 |
| `resolved_mpc` | Jetpack / Play services 最终提供的值 |
| `normalized_mpc_tier` | 产品侧归一化分组 |
| `sdk_int` | 当前平台 API |
| `device_initial_sdk_int` | 出厂平台，API 可用时记录 |
| 运行时能力位掩码 | 用一组二进制位记录编解码器、相机、显示和 GPU 等关键能力 |
| 内存 / 低内存设备分组 | 解释缓存、内存不足（OOM）与进程回收 |
| 温控状态 / 持续时长 | 区分短时峰值与稳定表现 |

不要只上报产品分组。原始值可以暴露三类问题：旧客户端没有识别新等级、Jetpack 的备用读取结果与平台构建属性不一致，以及设备 OTA 后声明发生变化。

小范围发布结果应按 MPC、运行时能力、设备厂商和 SoC 交叉观察，同时避免直接上报机型等取值数量过多的字段。Google Maps 的公开案例按 MPC 切分“界面元素可见所需秒数”，发现各组延迟都有小幅增加，而没有 MPC 的设备增幅最大，因此只向报告 MPC 的设备发布新的透明图层效果。这个案例说明 MPC 适合作为实验分组信号，不能推导出所有 MPC 0 设备都慢。

## 设备厂商认证与测试证据

同一款 SoC 可以出现在不同 MPC 等级。相机硬件抽象层（Camera HAL）、编解码器配置、存储、内存、音频路径、显示、散热与整机集成都会影响设备能否声明某一级。

Android 17 的证据链包括：

1. 设备通过 `Build.VERSION.MEDIA_PERFORMANCE_CLASS` 声明等级。
2. CDD 17 2.2.7 定义条款，补充文档给出每级阈值。
3. `cts-media-performance-class` 测试计划验证 2.2.7.1 媒体与 2.2.7.2 相机条款；相机 CTS 与 Camera ITS 继续覆盖具体相机要求。
4. MediaDrm、文件系统 I/O 等条款还有各自的 CTS 或验证步骤，不能由上一项测试计划代替。
5. 设备运行时 API 报告具体能力。
6. 应用的系统跟踪、耗时分布、温度、功耗和错误率确认业务体验。

应用只能使用公开声明和运行时 API，通常无法访问厂商的完整认证报告。缺少 MPC 时，也不能运行少量基准测试（benchmark）后伪造一个“等价 MPC”；内部测试结果只能作为产品自己的能力标签。

## Android 17 的工程结论

- Android 17 的 2.2.7 节与补充表定义了 MPC 1、10、20、30、31、33、34、35、37；0 表示没有可用声明。
- MPC 1、10、20 打破了“所有非零值都等于 Android API 级别”的旧假设。
- CDD 7.11 与 `Build.java` 注释仍保留“非零值至少为 30”的旧规则，应用不能用这段遗留文字过滤 Android 17 的新低等级。
- `Build.VERSION.MEDIA_PERFORMANCE_CLASS` 是平台原始声明，同一次开机内稳定，OTA 后可能提高。
- 当前 AndroidX 默认读取路径仍过滤小于 30 的平台值；使用 MPC 1、10、20 前要验证库版本或读取平台原始值。
- CDD 17 把测量阈值放在补充文档中，业务不能只读仍停留在 MPC 35 的 Android Developers 概览。
- MPC 是多项能力的下限集合。单项功能仍要查询编解码器、相机、显示和内存等运行时能力。
- 功能启用条件应使用 CDD 明确列出的等级集合，未识别值进入 `Unknown`。
- 高 MPC 不能消除温度、后台负载、厂商调度与驱动差异，发布决策仍需线上指标。

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
