---
title: "设备分级性能策略实战"
chapter: "21.16"
section: "21.16"
status: finalized
applicable_versions: "Android 10 (API 29) - Android 17 (API 37)"
tags: [device-tier, performance-strategy, device-year-class, feature-flag, degradation]
related_chapters: ["21.14", "21.15", "23.07", "25.06"]
created_by: "task2a-knowledge-gap"
created_date: "2026-07-17"
gap_source: "素材驱动/章节深挖"
last_draft_polish_at: "2026-08-06T23:45:29+08:00"
last_draft_polish_run_id: "20260806-234529-draft-polish-b425a06d"
last_verified: "2026-08-06"
last_verified_against: "AOSP android-17.0.0_r1 + android17-6.18-2026-06_r6 + Android developer docs"
reviewed_date: "2026-08-07"
reviewed_by: "hermes-aiw-review-finalize-apply"
last_review_finalize_at: "2026-08-07T12:09:10+08:00"
last_review_finalize_run_id: "20260807-120726-dea40797"
confidence: high
task6_state: reviewed
task9_state: reviewed
pipeline_stage: finalized
sources:
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/os/health/SystemHealthManager.java
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/os/PowerManager.java
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/app/ActivityManager.java
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/os/Build.java
- type: official
  path: https://developer.android.com/topic/performance/performance-class
---

# 设备分级性能策略实战

设备分级的目的，是给一次具体工作选择可承受的资源预算。图片解码关心内存和屏幕尺寸，视频播放关心编解码能力，复杂动画关心 GPU、刷新率和当前温控状态。把这些差异压成一个“高、中、低”总分，往往会让某项能力很强、另一项能力较弱的设备收到错误策略。

平台源码锚点为 Android 17 / API 37 / `android-17.0.0_r1`。普通应用不应读取隐藏的 `SystemProperties`、私有 `DeviceConfig` 命名空间或内核节点来猜测整机性能。涉及内存语义时，以 Android 17 framework 对 Linux 可访问内存的解释为准；内核版本锚定 `android17-6.18-2026-06_r6`，应用策略仍只依赖公开 Android API。

## 先拆成三类信息

一套可维护的性能策略至少包含三层：

| 层次 | 典型内容 | 生命周期 | 用途 |
| --- | --- | --- | --- |
| 稳定能力画像 | low-RAM 标记、应用堆上限、Media Performance Class、ABI、明确的硬件特性 | 安装、系统升级或配置版本变化时重算 | 判断某项功能有没有稳定的资源基础 |
| 工作负载策略 | 图片缓存预算、预取条数、视频规格、特效复杂度 | 随应用版本和远端策略版本变化 | 把能力映射到某个业务场景 |
| 会话期压力 | 温控状态、省电模式、内存压力、丢帧率、启动耗时 | 运行期间变化 | 临时收缩或恢复工作量 |

这三层不能共用一个分数。`isLowRamDevice()` 适合影响缓存和预加载，Media Performance Class 适合辅助选择媒体体验；热节流和省电模式只描述此刻的运行条件。一次发热也不应把设备永久记成“低端机”。

策略名称也应描述约束，例如 `memory_constrained`、`media_enhanced`、`render_reduced`。`low`、`middle`、`high` 看似省事，几个月后很难解释每一档究竟约束了 CPU、内存还是媒体能力。策略数量宜少，但“三档”并非平台规则；一项业务只有两个有效配置时，保留两个配置更容易验证。

## 公开 API 能告诉应用什么

### Media Performance Class

`Build.VERSION.MEDIA_PERFORMANCE_CLASS` 从 API 31 开始公开。Android 17 源码从只读设备属性取得该值；返回 `0` 表示设备或当前系统构建没有声明等级。非零值对应某个 Android 版本的 CDD 性能等级，例如 31、33、34、35，Android 官方文档明确说明不存在 MPC 32。它也可能在 OTA 后提高，平台升级却不保证同步提高。

Media Performance Class 覆盖媒体、相机、显示、编解码和部分通用要求，适合回答“能否提供某种媒体体验”。它没有承诺所有 App 工作负载的 CPU 或 GPU 吞吐，因此不能直接充当整机跑分。需要兼顾设备声明和 Google Play services 补充数据时，可以使用 Jetpack Core Performance；只读取平台声明时，`Build.VERSION.MEDIA_PERFORMANCE_CLASS` 已足够。

### 内存信号

`ActivityManager.isLowRamDevice()` 是面向应用的稳定提示，设备厂商通过系统配置声明它，适合收缩高内存功能。`getMemoryClass()` 返回当前应用近似的 Java 堆上限，单位是 MB；它没有表示整机 RAM，也没有涵盖 native、图形和共享内存。

`ActivityManager.MemoryInfo` 中几个字段的语义不同：

- `totalMem` 从 API 16 提供，表示内核可访问的总内存，不含基带、TEE 等低于内核层的固定保留区。
- `advertisedMem` 从 API 34 提供，更接近零售规格标称的物理内存，可能与 `totalMem` 不同。
- `availMem`、`lowMemory` 和 `threshold` 描述当前内存压力，属于会话期信号。
- `freeMem` 从 API 37 提供，只统计未使用 RAM，不含可回收页。Linux 会主动用闲置内存做文件页缓存，单看 `freeMem` 很容易误判压力。

缓存预算应同时受应用堆上限、资源类型和内存回调约束。按整机 `totalMem` 固定取一个百分比，会漏掉进程堆限制以及图形内存等开销。

### CPU、SoC、GPU 与屏幕

`Runtime.availableProcessors()` 返回当前 Java 虚拟机可用的处理器数量。它既不保证列出完整 SoC 拓扑，也没有表达大小核性能、调度容量或当前频率。`Build.SOC_MANUFACTURER` 和 `Build.SOC_MODEL` 从 API 31 提供，可以帮助诊断机型聚类；型号值维度很高，还存在厂商命名差异，不适合单独映射为分档。

Vulkan 版本、扩展和编解码器能力适合做功能门控。支持某个 Vulkan 特性只能证明接口可用，无法证明着色器吞吐足以承受某个场景。实验室可以用固定 workload 测量 GPU、CPU 和存储，线上冷启动阶段不应运行微基准：它会延长启动、增加发热，并产生受后台负载影响很大的样本。

屏幕分辨率和刷新率同时代表能力与负载。120 Hz 面板提供更高刷新上限，也把每帧预算压得更紧；更高分辨率会增加填充和带宽成本。渲染策略需要结合当前窗口尺寸、目标刷新率和帧数据，不能把屏幕规格简单加到“高端分”上。

## 采集一份稳定能力画像

这段示例只收集公开、成本低且含义可解释的稳定信号，适合在后台线程初始化后缓存：

```kotlin
data class StableDeviceSignals(
    val mediaPerformanceClass: Int?,
    val isLowRamDevice: Boolean,
    val appHeapClassMb: Int,
    val kernelVisibleMemoryBytes: Long,
    val availableProcessors: Int,
    val has64BitAbi: Boolean,
    val socManufacturer: String?,
    val socModel: String?,
)

fun collectStableDeviceSignals(context: Context): StableDeviceSignals {
    val activityManager =
        context.getSystemService(ActivityManager::class.java)
    val memoryInfo = ActivityManager.MemoryInfo().also {
        activityManager.getMemoryInfo(it)
    }

    val mediaClass = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
        Build.VERSION.MEDIA_PERFORMANCE_CLASS.takeIf { it != 0 }
    } else {
        null
    }

    val socManufacturer = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
        Build.SOC_MANUFACTURER.takeUnless { it == Build.UNKNOWN }
    } else {
        null
    }
    val socModel = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
        Build.SOC_MODEL.takeUnless { it == Build.UNKNOWN }
    } else {
        null
    }

    return StableDeviceSignals(
        mediaPerformanceClass = mediaClass,
        isLowRamDevice = activityManager.isLowRamDevice,
        appHeapClassMb = activityManager.memoryClass,
        kernelVisibleMemoryBytes = memoryInfo.totalMem,
        availableProcessors = Runtime.getRuntime().availableProcessors(),
        has64BitAbi = Build.SUPPORTED_64_BIT_ABIS.isNotEmpty(),
        socManufacturer = socManufacturer,
        socModel = socModel,
    )
}
```

这份数据仍是“信号集合”，没有自动成为性能等级。采集结果可连同 `Build.FINGERPRINT`、应用版本和策略版本存入本地；系统升级、应用升级或远端规则版本变化时再求策略。不要在每个页面、每一帧重复采集。

若应用最低版本低于示例中的 API 门槛，应保留版本判断。适用范围从 Android 10 开始，`isLowRamDevice`、`memoryClass` 与 `totalMem` 均已可用。

## 从能力向量生成工作负载策略

同一台设备可以同时得到“内存受限”和“媒体能力较强”两个判断。策略解析器应按业务维度消费信号，不要先算出通用总分再分配功能。

以下代码展示一种可测试的映射方式。阈值只用于说明结构，项目需要用自己的线上分布和基准数据校准：

```kotlin
enum class MediaPreset {
    COMPATIBLE,
    CDD_ENHANCED,
}

data class WorkloadPolicy(
    val decodedImageCacheFraction: Double,
    val feedPrefetchItems: Int,
    val mediaPreset: MediaPreset,
)

data class PolicyRules(
    val constrainedHeapMb: Int = 192,
    val enhancedMediaClass: Int = 35,
)

fun resolvePolicy(
    signals: StableDeviceSignals,
    rules: PolicyRules,
): WorkloadPolicy {
    val memoryConstrained =
        signals.isLowRamDevice ||
            signals.appHeapClassMb < rules.constrainedHeapMb

    val mediaEnhanced =
        (signals.mediaPerformanceClass ?: 0) >= rules.enhancedMediaClass

    return WorkloadPolicy(
        decodedImageCacheFraction = if (memoryConstrained) 0.08 else 0.16,
        feedPrefetchItems = if (memoryConstrained) 1 else 3,
        mediaPreset = if (mediaEnhanced) {
            MediaPreset.CDD_ENHANCED
        } else {
            MediaPreset.COMPATIBLE
        },
    )
}
```

这里的内存判断只影响缓存和预取，媒体等级只影响媒体预设。选中 `CDD_ENHANCED` 后仍要查询目标编解码器、相机或图形特性，因为业务所需能力未必属于该 MPC 等级的保证范围。

映射函数应保持纯函数特征：相同信号、规则版本和应用版本得到相同结果。这样既能写单元测试，也能在故障报告里复现用户收到的策略。

## 会话期压力单独处理

Android 10 起，`PowerManager.getCurrentThermalStatus()` 可读取当前热状态，`isPowerSaveMode()` 可读取省电模式。Android 11 / API 30 增加 `getThermalHeadroom()`：返回值 `1.0` 对应预计达到 `THERMAL_STATUS_SEVERE` 的阈值，设备不支持时可能返回 `NaN`。该接口跟踪慢变化温度，约一秒以内重复调用没有收益，过快调用还可能得到 `NaN`。

Android 16 / API 36 的 `android.os.health.SystemHealthManager` 增加 CPU、GPU headroom API。Android 17 源码显示：

- 有效结果范围为 0～100，`0` 表示没有更多容量可供分配；暂时不可用时可能返回 `Float.NaN`。
- 不支持该接口的设备会抛出 `UnsupportedOperationException`。
- 每次有效查询至少包含一次同步 Binder 调用，耗时可能超过 1 ms，不应在主线程、渲染线程或其他关键线程等待。
- 调用方应读取 `getCpuHeadroomMinIntervalMillis()` 或 `getGpuHeadroomMinIntervalMillis()`，遵守设备给出的最小轮询间隔。

这些 headroom 值描述当前工作负载还能获得多少容量，适合参与会话期调节。它们不适合作为稳定机型等级，也不应成为首帧前的同步依赖。

动态质量控制还要防止来回振荡。常用办法是设置不同的降级与恢复阈值，加上最短驻留时间。以下状态机用温控和丢帧率说明迟滞逻辑：

```kotlin
enum class RenderQuality {
    NORMAL,
    REDUCED,
}

class RenderQualityController(
    private val minDwellMillis: Long = 30_000,
) {
    private var quality = RenderQuality.NORMAL
    private var lastChangeMillis = Long.MIN_VALUE

    fun update(
        nowMillis: Long,
        thermalStatus: Int,
        missedFrameRatio: Double,
    ): RenderQuality {
        if (
            lastChangeMillis != Long.MIN_VALUE &&
            nowMillis - lastChangeMillis < minDwellMillis
        ) {
            return quality
        }

        val shouldReduce =
            thermalStatus >= PowerManager.THERMAL_STATUS_SEVERE ||
                missedFrameRatio >= 0.10
        val safeToRecover =
            thermalStatus <= PowerManager.THERMAL_STATUS_LIGHT &&
                missedFrameRatio <= 0.03

        val next = when (quality) {
            RenderQuality.NORMAL ->
                if (shouldReduce) RenderQuality.REDUCED else quality
            RenderQuality.REDUCED ->
                if (safeToRecover) RenderQuality.NORMAL else quality
        }
        if (next != quality) {
            quality = next
            lastChangeMillis = nowMillis
        }
        return quality
    }
}
```

降级阈值高于恢复阈值，且两次切换至少间隔 30 秒，因此短时抖动不会反复改变画质。示例里的丢帧比例和时间窗口需要按场景校准；恢复时也宜逐级增加工作量，避免一次恢复全部特效后再次触发降级。

内存压力可通过 `onTrimMemory()`、`MemoryInfo.lowMemory` 和业务缓存命中率处理。网络质量则属于另一条动态轴，应依据计量网络、Data Saver、请求时延和吞吐选择图片或预取策略，不能由设备等级代替。

## 各类策略如何收缩

### 启动

- 保留 Baseline Profile 和 Startup Profile。它们让关键路径更早获得 AOT 编译与更好的 DEX 布局，较慢设备通常更受益。
- 只有在 trace 证明并发初始化发生 CPU 争用、锁竞争或 I/O 拥塞时，才减少并发任务；线程少不等于启动更快。
- 把非首屏依赖移出启动关键路径，为初始化任务设置明确的触发条件和超时。
- 不在冷启动期间探测 CPU 峰值、存储吞吐或 GPU 跑分。

### 渲染

- 根据目标帧预算、窗口像素数和实测帧时间调整模糊半径、粒子数、阴影层级或动画采样率。
- 矢量图不会必然比 PNG 慢；PNG 也可能增加包体、解码内存和缩放成本。应针对具体资源测量。
- `RGB_565` 只能在无 alpha 且可接受色彩精度损失的内容上评估，不能作为低内存设备的全局开关。
- 对质量变化使用迟滞、最短驻留时间和渐进过渡，避免用户看到频繁跳变。

### 内存

- 图片缓存按应用堆预算、平均对象大小和命中收益设计，并响应 `onTrimMemory()`。
- 缩短列表预取窗口前，应测量占用与滚动命中率；过度收缩会增加重复解码和网络请求。
- native、GPU、共享内存和 Java 堆要分别观测，`getMemoryClass()` 只约束其中一部分。

### 媒体

- 用 Media Performance Class 选择 CDD 已覆盖的体验，再用 `MediaCodecList`、Camera2 characteristics 或图形能力查询确认业务所需特性。
- 编解码器初始化耗时、掉帧与温控表现应进入实验设备组合。一个声明值无法覆盖厂商驱动质量。

### 网络与后台任务

- 图片规格应综合容器像素、屏幕密度、网络策略和缓存，不按 SoC 型号固定。
- 低带宽或计量网络可以减少预取；设备 CPU 较慢不代表网络较慢。
- App 无权修改 JobScheduler 的系统配额。可以减少任务数量、延长周期，并使用充电、空闲、网络类型等约束，让系统选择执行时机。

## 远端策略必须能离线启动

远端配置适合修正规则和控制发布范围，但不能成为冷启动网络依赖。可采用以下数据契约：

- APK 内置经过验证的安全默认值。
- 本地保存上一份通过校验的配置；拉取失败继续使用它。
- 配置带 `schemaVersion`、`policyRevision`、适用应用版本、过期时间和各项边界。
- 未识别字段按兼容规则忽略，越界值拒绝生效。
- 高风险开关提供独立 kill switch，服务端可快速回退到上一版本。
- 策略在一个前台会话内保持稳定；热更新先记录，下个安全边界再切换。
- 记录分组、配置版本和曝光事件，只有发生曝光的样本才进入实验分析。

灰度分组应使用稳定标识做确定性散列，并在能力画像或机型群内随机分配。直接比较“高端组”和“低端组”会把用户、系统版本、地区和业务行为差异混进结论。汇总数据还可能出现辛普森悖论：各设备层内都变好，合计结果却因流量构成改变而变差。

设备等级也不是安全边界。客户端参数可以被篡改，服务端不能据此授予权限、跳过风控或信任内容。

## 设备老化与厂商模式

公开 Android SDK 没有一个通用 API，能够可靠给出“电池老化百分比 + 存储健康度”，再转换为设备性能等级。电量、充电状态、剩余空间和单次 I/O 延迟各自只解释一个局部现象。对普通应用，更可靠的做法是观察当前会话的帧时间、解码耗时、启动耗时、内存压力和温控状态，并在压力持续存在时临时收缩工作量。

厂商的游戏模式、性能模式和私有系统属性缺少跨设备契约，普通应用不能把它们写入通用策略。面向持续渲染负载的应用可以检查 `PowerManager.isSustainedPerformanceModeSupported()`，再按公开 API 使用 `Window.setSustainedPerformanceMode()`；该模式追求长时间稳定输出，也不等同于通用“高性能模式”。

历史上的 Facebook Device Year Class 把若干规格映射成“年份”，其分解信号的思路仍可帮助理解早期设备分组。仓库已在 2020 年归档，不宜作为 Android 17 产品策略的现成实现。

## 验证分级有没有收益

每条策略都需要一个主要指标和一组护栏。例如，减少列表预取的主要指标可以是内存峰值，护栏包括滚动卡顿、图片等待时间、网络请求数和用户操作成功率。只看平均 FPS 或平均启动时间，会掩盖长尾和受影响最重的设备。

验证流程可按以下顺序执行：

1. 用 trace 或 heap 数据确认瓶颈归属，明确策略要减少哪类成本。
2. 在代表性的设备组合上跑 Macrobenchmark 或场景基准，覆盖冷、温、热启动以及关键交互。
3. 对每个能力群做随机实验，同时记录策略曝光。
4. 分别检查 P50、P90、P95、P99、失败率和功耗或内存护栏。
5. 上线后结合 Android vitals 与自有遥测按应用版本、系统版本、策略版本和设备群观察。
6. 规则失效或护栏恶化时回退配置，并保留可复现的配置快照。

实验设备应覆盖低 RAM、不同 MPC、主流 SoC 家族、不同屏幕负载和主要系统版本。机型型号可用于定位异常，不应让每个型号长期持有一份手写策略；那会迅速积累无法验证的分支。

## 检查清单

- [ ] 能力画像、业务策略、会话期压力分别建模。
- [ ] 只使用公开 API；没有读取隐藏 `SystemProperties` 或私有 `DeviceConfig`。
- [ ] 没有通用加权分数，也没有在用户冷启动期间跑微基准。
- [ ] Media Performance Class 只用于其 CDD 覆盖的能力，并处理 `0`。
- [ ] `memoryClass`、`totalMem`、`availMem`、`freeMem` 的含义没有混用。
- [ ] CPU/GPU headroom 查询避开关键线程，并遵守最小轮询间隔。
- [ ] 动态降级含迟滞、最短驻留时间和渐进恢复。
- [ ] Baseline Profile 与 Startup Profile 未因设备较慢而关闭。
- [ ] 网络策略依据网络与内容尺寸，未复用硬件等级。
- [ ] JobScheduler 只设置任务和约束，没有假设 App 能调整系统配额。
- [ ] 远端配置具有本地默认、上一有效版本、版本校验、过期和回退能力。
- [ ] 实验按能力群随机，记录曝光，并检查分位数与护栏。

## 源码与文档

- [Android 17 `SystemHealthManager.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/os/health/SystemHealthManager.java)：CPU/GPU headroom 的 Binder 调用、返回值和轮询间隔。
- [Android 17 `PowerManager.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/os/PowerManager.java)：温控状态、thermal headroom 与持续性能模式。
- [Android 17 `ActivityManager.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/app/ActivityManager.java)：low-RAM、应用堆等级和 `MemoryInfo`。
- [Android 17 `Build.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/os/Build.java)：SoC 标识与 Media Performance Class 的来源。
- [Performance class](https://developer.android.com/topic/performance/performance-class)：MPC 的等级、CDD 范围和 Jetpack Core Performance 用法。
- [`SystemHealthManager` API](https://developer.android.com/reference/android/os/health/SystemHealthManager)：API 36 headroom 接口契约。
- [`PowerManager` API](https://developer.android.com/reference/android/os/PowerManager)：温控与省电公开 API。
- [`ActivityManager.MemoryInfo` API](https://developer.android.com/reference/android/app/ActivityManager.MemoryInfo)：各内存字段的 API 版本与语义。
- [Baseline Profiles](https://developer.android.com/topic/performance/baselineprofiles/overview)：AOT 优化与 Startup Profile 的适用方式。
- [Macrobenchmark](https://developer.android.com/topic/performance/benchmarking/macrobenchmark-overview)：跨设备场景基准。
- [Device Year Class archive](https://github.com/facebookarchive/device-year-class)：已归档的历史分级实现。
