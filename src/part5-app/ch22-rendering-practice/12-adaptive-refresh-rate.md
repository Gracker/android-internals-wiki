---
title: 自适应刷新率与帧率策略实战
chapter: '22.12'
status: finalized
applicable_versions: Android 15 (API 35) - Android 17 (API 37)
last_verified: '2026-08-24'
last_verified_against: Android Developers ARR（更新于 2026-02-26），AOSP Android 17 android-17.0.0_r1
confidence: high
sources:
- type: official
  path: https://developer.android.com/develop/ui/views/animations/adaptive-refresh-rate
- type: official
  path: https://developer.android.com/about/versions/16/features
- type: official
  path: https://developer.android.com/reference/android/view/Display
- type: official
  path: https://developer.android.com/reference/android/view/WindowManager.LayoutParams
- type: official
  path: https://developer.android.com/media/optimize/performance/frame-rate
- type: aosp
  path: https://source.android.com/docs/core/graphics/arr
- type: clippings-structure
  path: Clippings/Android 性能优化 - 如何才能做好 Android 性能优化？.md
- type: clippings-structure
  path: Clippings/Android 性能优化 - 原理：重新认识应用的速度优化.md
tags:
- adaptive-refresh-rate
- frame-rate
- jank
- power
- android16
- android17
related_chapters:
- '2.2'
- '22.2'
- '25.1'
---

# 自适应刷新率与帧率策略实战

应用能表达内容期望帧率，但最终刷新节奏仍由窗口、Surface、系统策略和显示能力共同决定。接入时要让请求贴近实际更新源，并通过 FrameTimeline 与显示模式验证，而不是只检查 API 调用成功。

## 从三个帧率开始判断

自适应刷新率（Adaptive Refresh Rate，ARR）调整的是显示节奏，不会缩短应用生成一帧时的 CPU、GPU 或解码耗时。排查前要分清三个量：

- **内容帧率**：视频、游戏或动画每秒产生多少个不同画面；
- **应用渲染速率**：应用收到帧回调并提交新图形缓冲区的节奏；
- **显示刷新率**：显示设备每秒更新画面的次数。

`fps` 表示每秒生成的画面数，`Hz` 表示显示设备每秒刷新的次数。60 fps 的应用可以运行在 120 Hz 显示设备上，每个应用帧保持两个刷新周期，画面仍然均匀。应用平均达到 60 fps，也可能因为提交间隔忽快忽慢而出现卡顿。帧率平均值、呈现间隔和输入延迟回答的是不同问题。

本文的平台实现基线是 Android 17、API 37 和 `android-17.0.0_r1`，内核源码基线是 `android17-6.18-2026-06_r6`。ARR 从 Android 15 进入平台；应用要使用完整能力，系统需为 Android 15 QPR1 或更高版本，设备还要实现相应的 Composer3 硬件抽象层（Hardware Abstraction Layer，HAL）能力。系统版本符合要求，并不表示每块显示设备都支持 ARR。

在 ARR 配置中，显示设备的垂直同步（VSync）或面板 TE（Tearing Effect，面板扫描时序信号）可以与内容刷新节奏分开。面板能在同一个显示模式内，按 TE 周期的离散倍数选择呈现时机。这样可以减少只为改变刷新率而切换显示模式的次数，也能缩短静态内容和低频动画占用高刷新率的时间。平台选择链、ARR/MRR 分支和 attached Choreographer 反馈统一见 [2.2 帧率、刷新率与显示模式选择](../../part1-fundamentals/ch02-rendering/02-framerate-refresh-display-mode.md)；本文只负责应用接入、跨设备实验和回退策略。

应用仍有两项责任：控制生成一帧的成本和节奏，并向系统准确描述内容偏好。ARR 不会修复主线程超时、`RenderThread` 堵塞、GPU 迟完成、视频时间戳错误或 `BufferQueue` 中待显示缓冲区堆积。

## Android 15—17 API 边界

工程代码应同时检查 API 可用性和目标显示设备的能力。Android 15 可以提交 `View`、`Window` 与 `Surface` 的帧率请求，公开的 ARR 能力查询则从 Android 16 才可用。

| 能力 | API | 版本 | 用途与限制 |
| --- | --- | --- | --- |
| Surface 内容帧率 | `Surface.setFrameRate()` | API 30；三参数版本 API 31 | 提交 Surface 级偏好；不会替画面生产方限速 |
| 清除 Surface 请求 | `Surface.clearFrameRate()` | API 34 | 内容结束或目标改变时撤销旧请求 |
| View 帧率请求 | `View.setRequestedFrameRate(float)` | API 35 | 可传具体值或 View 帧率类别；View 需要重绘时才参与 |
| 滚动速度提示 | `View.setFrameContentVelocity(float)` | API 35 | 平滑滚动或惯性滚动期间，每个绘制帧上报像素/秒 |
| Window 省电平衡 | `Window.setFrameRatePowerSavingsBalanced(boolean)` | API 35 | 控制窗口是否采用 ARR 省电平衡；默认开启 |
| Window 触摸升帧 | `Window.setFrameRateBoostOnTouchEnabled(boolean)` | API 35 | 控制该窗口的触摸升帧；默认开启 |
| ARR 能力查询 | `Display.hasArrSupport()` | API 36 | 查询当前显示设备是否公开支持 ARR |
| 类别建议值 | `Display.getSuggestedFrameRate(int)` | API 36 | 只接受 `NORMAL`、`HIGH` 两个显示帧率类别 |
| UI Surface 下限语义 | `Surface.FRAME_RATE_COMPATIBILITY_AT_LEAST` | API 36 | 用于 UI、动画、滚动和惯性滚动；视频、游戏有各自语义 |
| 支持的渲染速率 | `Display.getSupportedRefreshRates()` | API 21，API 36 改变返回语义 | API 36 及以上返回显示设备支持的渲染速率；旧版本只覆盖默认显示模式的刷新率 |
| 速度—帧率映射 | `Display.getFrameRateVelocityMapping()` | API 37 | 返回当前显示设备的滚动速度映射；换屏或显示设备变化后要重新读取 |

`getSuggestedFrameRate()` 返回设备为指定类别配置的建议值。它不是当前刷新率，系统也不保证采用这个值。`getSupportedRefreshRates()` 从 API 21 就已存在，只在 API 36 更新了返回语义，不能把它写成 Android 16 新增的方法。

下面的封装只读取能力，不替业务选择固定的 60 Hz 或 120 Hz。

```kotlin
sealed interface ArrCapability {
    data object QueryUnavailable : ArrCapability
    data object Unsupported : ArrCapability

    data class Supported(
        val normalFrameRate: Float,
        val highFrameRate: Float,
        val supportedRenderRates: List<Float>,
    ) : ArrCapability
}

fun Display.readArrCapability(): ArrCapability {
    if (Build.VERSION.SDK_INT < 36) {
        return ArrCapability.QueryUnavailable
    }
    if (!hasArrSupport()) {
        return ArrCapability.Unsupported
    }
    return ArrCapability.Supported(
        normalFrameRate =
            getSuggestedFrameRate(Display.FRAME_RATE_CATEGORY_NORMAL),
        highFrameRate =
            getSuggestedFrameRate(Display.FRAME_RATE_CATEGORY_HIGH),
        supportedRenderRates = supportedRefreshRates.sorted(),
    )
}
```

`QueryUnavailable` 表示 API 35 没有公开查询入口，不表示设备一定缺少 ARR。应用仍可提交公开的 `View` 或 `Surface` 帧率请求，由系统按设备能力处理。折叠屏内外屏、外接屏和窗口迁移都可能改变关联的 `Display` 对象；缓存结果时应带上 `displayId`，并在收到显示设备变化回调后重新读取。

Android 17 的 `getFrameRateVelocityMapping()` 主要服务滚动组件。`setFrameContentVelocity()` 接收像素/秒，返回映射中的 `FrameRateVelocityPoint.dpPerSecond` 则使用密度无关像素/秒。普通自定义 `View` 只需按接口要求上报像素速度，由框架结合当前显示设备选择偏好；应用不应复制一套固定速度阈值，也不能直接比较这两种单位的数值。

## View 帧率请求要贴近会更新的内容

官方文档把这套汇总机制称为“投票”（voting）：每个可见且需要重绘的 `View` 提交帧率偏好，系统再汇总成宿主窗口的提示。“投票”只是请求合并的比喻，不表示每个 `View` 有固定票数，也不表示结果一定采用最高请求。可用类别包括：

- `REQUESTED_FRAME_RATE_CATEGORY_DEFAULT`：恢复框架默认行为；
- `REQUESTED_FRAME_RATE_CATEGORY_NO_PREFERENCE`：该 View 明确不影响结果；
- `REQUESTED_FRAME_RATE_CATEGORY_LOW`：适合低速、小面积且高平滑度收益有限的动画；
- `REQUESTED_FRAME_RATE_CATEGORY_NORMAL`：适合不依赖高刷的动画，设备通常把它映射到 60 Hz 附近；
- `REQUESTED_FRAME_RATE_CATEGORY_HIGH`：适合高平滑度收益明确的动画，功耗也可能上升。

同一帧中，`View` 层通常采用较高的有效请求。进入 `SurfaceFlinger` 后，系统还会综合其他应用的图层（layer，即 `SurfaceFlinger` 的合成单元）、系统界面、触摸状态、空闲状态、功耗策略、可用显示模式和能否无缝切换。这里不存在“某个 View 请求 120，屏幕就锁定 120 Hz”的保证。

`ViewGroup.setRequestedFrameRate()` 在 API 35 不会自动传给子 `View`。API 36 增加的接口是 `ViewGroup.propagateRequestedFrameRate(frameRate, forceOverride)`：调用方要明确提供帧率值；`forceOverride=false` 保留子 `View` 已明确设置的值，`true` 则允许覆盖；恢复时传入 `DEFAULT` 类别。给页面根节点长期请求 `HIGH` 会扩大高刷新率范围，进度条、视频卡片、列表与静态正文也更难按各自节奏工作。

场景策略可以按下面的边界制定：

| 场景 | 合适的表达 | 验收重点 |
| --- | --- | --- |
| 小型进度条、低频波形 | 局部 View 请求 `NORMAL` 或经设备验证的具体值 | 动画节奏稳定，高刷新率驻留时间下降 |
| 点击反馈、短位移动画 | 保留触摸升帧；卡顿时对局部 View 评估 `HIGH` | `ACTION_DOWN` 到首个可见反馈 |
| 静态阅读、表单 | 不触发无意义的无效化与重绘，不主动请求高值 | 静止后不再持续生成应用帧 |
| `RecyclerView` 惯性滚动 | `RecyclerView` 1.4.0 及以上；配套 AndroidX Core 1.15.0 及以上 | 松手后随速度降低渲染速率 |
| `NestedScrollView` | AndroidX Core 1.15.0 及以上 | 速度下降段的节拍与滚动位移 |
| 自定义滚动容器 | 惯性滚动或平滑滚动的每个绘制帧上报速度 | 速度值、帧回调与滚动位移同步 |
| 视频卡片 | 视频 Surface 表达源帧率，宿主控件单独提交请求 | 视频帧节奏与宿主界面分开观察 |

下面的例子从 `OverScroller` 读取当前惯性滚动速度，并在每个绘制帧更新提示。

```kotlin
class ArrAwareScrollView @JvmOverloads constructor(
    context: Context,
    attrs: AttributeSet? = null,
) : View(context, attrs) {
    private val scroller = OverScroller(context)

    override fun computeScroll() {
        if (!scroller.computeScrollOffset()) {
            return
        }

        if (Build.VERSION.SDK_INT >= 35) {
            frameContentVelocity = scroller.currVelocity
        }
        scrollTo(scroller.currX, scroller.currY)
        postInvalidateOnAnimation()
    }
}
```

`currVelocity` 已是非负的像素/秒。`setFrameContentVelocity()` 的值只对下一个绘制帧有效，所以一次手势只写一次无法覆盖完整的惯性滚动。触摸按住期间仍由触摸升帧保持较高节奏；速度映射用于松手后的减速阶段。

ARR 只改变目标节拍。若滚动仍出现“应用错过帧截止时间”（`app deadline missed`），应继续检查布局、数据绑定、图片处理、预取、`RenderThread` 和 GPU。相关 `RecyclerView` 方法见 [22.2 RecyclerView 与 Compose LazyList 性能](02-recyclerview-compose-lazylist.md)。

## Window 开关属于回退手段

触摸升帧（touch boost）默认开启。收到 `ACTION_DOWN` 后以及手指抬起的一段时间内，系统可以提高渲染速率，用于按压态、拖动起步和窗口内的交互反馈。官方文档明确不建议关闭它。

窗口级 API 可以直接调用，无需手动修改 `WindowManager.LayoutParams` 再写回 `attributes`。下面的函数适合实验开关和少量经验证的窗口策略。

```kotlin
fun Window.configureFrameRatePolicy(
    touchBoostEnabled: Boolean,
    powerSavingsBalanced: Boolean,
) {
    if (Build.VERSION.SDK_INT < 35) {
        return
    }
    setFrameRateBoostOnTouchEnabled(touchBoostEnabled)
    setFrameRatePowerSavingsBalanced(powerSavingsBalanced)
}
```

`powerSavingsBalanced=false` 会关闭该窗口的 ARR 省电平衡，通常会增加耗电；它不能指定一个固定刷新率。`touchBoostEnabled=false` 也不适合作为全应用默认值。两项都应有独立的远端开关，避免一次回退影响另一项策略。

关闭触摸升帧的实验至少测量：

- `ACTION_DOWN` 到按压态首帧呈现的延迟；
- 松手后 200 ms 内的惯性滚动位移、错过截止时间次数和帧间隔；
- 连续拖动时输入事件、View 树遍历（traversal）、`SurfaceFrame` 与 `DisplayFrame` 的间隔；
- 普通、低电量、热限制和多窗口条件下的差异。

## SurfaceView、TextureView 与普通 View 的请求路径

这三类对象的显示拓扑不同，不能都视为“独立内容层”：

| 承载方式 | Android 17 路径 | 请求与观测对象 |
| --- | --- | --- |
| 普通 View | View/HWUI 绘入宿主应用窗口的图形缓冲区（buffer） | View 请求汇总到宿主图层 |
| `TextureView` | 外部画面生产方写入 `SurfaceTexture`；HWUI 读取纹理并采样进宿主缓冲区 | 生产方设置的帧率可以传回 TextureView 偏好，SurfaceFlinger 通常仍只看到宿主图层 |
| `SurfaceView` | 画面生产方写入独立的 `BufferQueue`；BLAST 子层作为独立缓冲区图层进入 SurfaceFlinger | 内容 Surface 与宿主窗口可拥有不同帧节奏、缓冲区和同步栅栏（fence） |

在 Android 17 的 AOSP 实现中，只有 `Flags.toolkitSetFrameRateReadOnly()` 特性开关启用时，`TextureView` 才会在 `SurfaceTexture` 上安装帧率监听器。画面生产方对其 `Surface` 调用 `setFrameRate()` 后，监听器会更新 `TextureView` 请求的帧率；内容仍要经过 `TextureLayer.updateSurfaceTexture()` 和宿主 HWUI。这个回传过程不会把 `TextureView` 变成独立的 SurfaceFlinger 视频图层。

Android 17 的 `SurfaceView` 会创建容器层、BLAST 内容子层，以及按需创建的背景色层。视频或相机画面生产方可以按自己的节奏更新 BLAST 子层，宿主 View 树只负责普通界面、位置、裁剪、可见性与相对层级。使用 Perfetto 分析时，要分别观察宿主窗口和 `SurfaceView` 内容层。

固定帧率视频适合在承载视频的 `Surface` 上提交 `FIXED_SOURCE`。下面的调用表达 24 fps 固定源，并把显示模式变化限制为无缝切换。

```kotlin
fun Surface.setVideoFrameRate(frameRate: Float) {
    if (Build.VERSION.SDK_INT < 30) {
        return
    }
    if (Build.VERSION.SDK_INT >= 31) {
        setFrameRate(
            frameRate,
            Surface.FRAME_RATE_COMPATIBILITY_FIXED_SOURCE,
            Surface.CHANGE_FRAME_RATE_ONLY_IF_SEAMLESS,
        )
    } else {
        setFrameRate(
            frameRate,
            Surface.FRAME_RATE_COMPATIBILITY_FIXED_SOURCE,
        )
    }
}
```

只有在长时间播放且产品接受一次可见切换时，才评估 `CHANGE_FRAME_RATE_ALWAYS`。播放结束、`Surface` 复用或内容帧率改变时要更新请求；API 34 及以上可用 `clearFrameRate()` 清除旧值。调用成功只表示提示已提交，不表示显示设备已选择 24 Hz 或 120 Hz。

API 36 及以上的普通界面、动画和滚动 `Surface` 可以使用 `FRAME_RATE_COMPATIBILITY_AT_LEAST`；游戏继续使用 `DEFAULT`，并由引擎控制产帧节奏；视频继续使用 `FIXED_SOURCE`。相机预览要按捕获帧率、宿主界面和产品延迟目标单独评估，不能因为输出到 `Surface` 就套用视频语义。

## Android 17 怎样处理这些帧率请求

View 层先汇总当前绘制帧的类别或具体值。Surface 级请求和帧提交历史进入图层状态。Android 17 的 SurfaceFlinger 再按以下路径处理：

1. `LayerHistory::summarize()` 汇总可见图层的需求，包含请求类型、期望值、图层面积占显示面积的权重、是否获得焦点，以及目标显示设备；
2. `Scheduler::chooseRefreshRateForContent()` 收集内容需求和全局信号；
3. `RefreshRateSelector::getRankedFrameRates()` 过滤候选并评分；
4. 显示策略、无缝切换条件、触摸状态、空闲状态、功耗状态和其他图层共同约束结果；
5. 选出的渲染速率或显示模式改变应用与 SurfaceFlinger 的调度节拍，并向硬件合成器（Hardware Composer，HWC）提交显示配置或 ARR 呈现间隔。

Android 17 的 `RefreshRateSelector` 用一组内部类型区分请求语义：`ExplicitDefault` 表示默认值，`ExplicitExactOrMultiple` 表示精确值或其整数倍，`ExplicitExact` 表示精确值，`ExplicitGte` 表示不低于给定值，`ExplicitCategory` 表示类别请求，`Heuristic` 表示系统根据历史推断。`FRAME_RATE_COMPATIBILITY_AT_LEAST` 对应最低值请求，与固定源的精确值或整数倍诉求采用不同评分。触摸状态和空闲状态也有提前结束选择及延后升帧分支，不能概括成“触摸必定拉满，固定若干秒后降频”。

Composer3 的设备能力位于另一层。`DisplayConfiguration.vrrConfig` 非空时，该显示配置才属于 ARR；`DisplayConfiguration.vsyncPeriod` 表示 VSync/TE 周期，`VrrConfig.minFrameIntervalNs` 约束两帧之间允许的最短间隔。设备若提供 `DisplayConfiguration.vrrConfig.notifyExpectedPresentConfig`，Android 框架可以通过 `IComposerClient.notifyExpectedPresent()` 提前告知预计呈现时间和后续的 `frameIntervalNs` 帧间隔。厂商仍可按面板与功耗策略决定具体行为。

通用 Android 内核 `android17-6.18-2026-06_r6` 的 `drivers/gpu/drm/drm_vblank.c` 提供 DRM（Direct Rendering Manager，Linux 显示子系统）的垂直消隐（VBlank）计数、事件和时间戳机制。Android 设备不保证采用相同的 DRM 显示路径，面板 TE、最低刷新率、硬件显示平面、带宽与厂商 HWC 策略都不能只从通用内核推出。定位到 HWC 后，还要结合目标设备的 Composer、显示驱动和厂商跟踪数据。

## Perfetto 验收：把请求、生产和呈现放在一起

ARR 验收至少同时覆盖四条证据：

| 证据层 | 观察内容 | 能回答的问题 |
| --- | --- | --- |
| 应用输入与工作 | 输入事件、`Choreographer`、界面线程、`RenderThread`、GPU | 交互是否变慢，应用是否在新的帧截止时间前完成 |
| 应用 `SurfaceFrame` | 预期/实际时间线、`on_time_finish`、`jank_type` | 宿主应用帧是否迟交或迟完成 |
| SurfaceFlinger `DisplayFrame` | 预期/实际时间线、呈现类型、SurfaceFlinger 卡顿标记 | 合成与显示提交是否按目标时间完成 |
| 刷新率与图层 | 当前显示模式、渲染速率、图层请求、选择过程的区间事件、实际呈现节奏 | 何时改变节拍，哪个显示对象参与决策 |

应用 `SurfaceFrame` 与 SurfaceFlinger `DisplayFrame` 是两种对象：前者描述应用窗口帧，后者描述合成后送往显示设备的帧。预期时间线与实际时间线的关联用于比较目标时间和完成结果，不能把两条区间事件（slice，即有开始和结束时间的跟踪记录）在界面上的“分叉”直接判成某类卡顿。`SurfaceView`、视频、相机和游戏的独立画面生产方，也未必拥有与标准 HWUI 应用窗口同样完整的 `FrameTimeline` 信息。信息缺失时，应依次查看对应图层的 `queueBuffer`（缓冲区入队）、`BufferTX`（图层事务）、`acquire fence`（缓冲区就绪同步）、`latch`（SurfaceFlinger 接收缓冲区）、HWC 合成和 `present`（送显）。

View 请求不等于独立图层请求。普通 `View` 和 `TextureView` 的结果通常要在宿主应用窗口上验证；`SurfaceView` 内容则要找到它自己的 BLAST 缓冲区图层。Perfetto 的计数器（counter）是随时间记录数值的轨道；只看到刷新率计数器下降，无法证明是哪项应用策略触发，也无法证明交互没有受损。

系统刷新率设置属于测试环境变量，且键名和生效方式会受 OEM 影响。需要强制档位做实验时，应保存原值并保证脚本退出后恢复。下面的脚本要求调用者传入目标设备已支持的 peak 值。

```bash
#!/usr/bin/env bash
set -euo pipefail

TEST_PEAK="${1:?pass a supported peak refresh rate, for example 120.0}"
TEST_PACKAGE="${2:-com.example.app}"
PEAK_BEFORE="$(adb shell settings get system peak_refresh_rate | tr -d '\r')"
MIN_BEFORE="$(adb shell settings get system min_refresh_rate | tr -d '\r')"

restore_setting() {
    local key="$1"
    local value="$2"
    if [[ -z "$value" || "$value" == "null" ]]; then
        adb shell settings delete system "$key" >/dev/null
    else
        adb shell settings put system "$key" "$value"
    fi
}

restore_all() {
    restore_setting peak_refresh_rate "$PEAK_BEFORE"
    restore_setting min_refresh_rate "$MIN_BEFORE"
}

trap restore_all EXIT
trap 'exit 130' INT TERM

adb shell settings put system peak_refresh_rate "$TEST_PEAK"
adb shell settings put system min_refresh_rate 0.0
adb shell am force-stop "$TEST_PACKAGE"
adb shell monkey -p "$TEST_PACKAGE" 1

read -r -p "Record the Perfetto trace, then press Enter to restore settings."
```

脚本只用于实验机。运行前应从设备支持的显示模式或系统设置中确认目标值，并在跟踪数据中验证设置是否生效。日常基线还要保留一组完全不改系统设置的数据，避免把调试时的强制设置当成量产策略。

应用线上可以记录 `displayId`、API 版本、`hasArrSupport()`、应用提交的策略、窗口模式、`FrameMetrics`/卡顿指标和交互时延。普通应用拿不到通用、可信的面板刷新率驻留统计；请求值或 `Display.getRefreshRate()` 也不能代替面板功耗证据。刷新率驻留时间、CPU/GPU 工作频点和耗电应通过实验室跟踪数据、功耗仪或设备提供的可靠计数器验证。

## 跨设备实验与回退

实验分桶至少包含：

- API 35：可以提交 ARR 相关请求，无法用公开 API 查询 ARR；
- API 36—37 且 `hasArrSupport=false`：保留安全的帧率请求，排除在 ARR 收益统计之外；
- API 36—37 且 `hasArrSupport=true`：按 `displayId`、设备型号、系统构建指纹（build fingerprint）、窗口模式和电源状态分组；
- 折叠屏、外接屏、多窗口：分别记录目标显示设备，不能沿用主屏能力；
- 设备厂商的高刷新率、游戏、低电量或热策略介入：单独标记，避免与默认策略混算。

回退开关应拆成 View 类别/具体值、滚动速度提示、触摸升帧、Window 省电平衡和 Surface 请求五类。出现机型问题时只撤销对应提示。系统默认 ARR 本身仍可继续工作。

功耗 A/B 需要固定亮度、网络、温度起点、电量区间、账号数据、页面停留、输入脚本和刷新率系统设置。每个场景至少比较：

- 系统默认 ARR，应用不增加额外请求；
- 系统默认 ARR，低频动态内容提交局部请求；
- 同一策略下关闭指定窗口的触摸升帧，仅作为专项实验；
- 关闭 Window 省电平衡，仅作为问题复现和回退对照。

通过标准要同时约束高刷新率驻留时间、慢帧/冻帧（渲染明显超时的帧）、输入到呈现延迟的分位数，以及单位场景能耗。只降低刷新率不能作为上线结论。

## 游戏、视频与 Compose

视频有固有的帧节奏，24/30/60 fps 内容应使用 `FIXED_SOURCE`，并保持播放器时间戳、解码输出和 Surface 提交节奏一致。24 fps 内容在 120 Hz 显示设备上可以形成 5:5 节奏，即每个视频画面连续显示五个刷新周期；系统也可能因为其他可见图层、显示策略或无缝切换限制选择别的结果。

游戏的帧率目标通常可以跟随设备和负载变化，使用 `DEFAULT`，并由引擎或 AGDK Frame Pacing（帧节奏库）控制逻辑节拍、预计呈现时间，以及在途帧深度（已经提交但尚未呈现的帧数）。Surface 帧率请求不会替游戏限制产帧速度，也不会修复缓冲区队列塞入过多帧的 `queue stuffing`。非 View 渲染还要结合引擎帧时间、Perfetto 和对应游戏质量指标。

Compose 从 1.9 起提供 `Modifier.preferredFrameRate(Float)` 和 `Modifier.preferredFrameRate(FrameRateCategory)`，本文核验基线为 Compose UI 1.12.0。帧率请求应靠近持续变化的可组合函数。给整屏统一设置 `High` 会扩大高刷新率范围；`LazyList` 应优先使用当前 Compose/AndroidX 自带的滚动支持，再用跟踪数据判断是否还需局部调整。ARR 也不会减少重组（recomposition）、布局（layout）或绘制（draw）本身的工作量。

## 小结

ARR 策略从内容对象出发：普通 View 和 Compose 在宿主窗口内提交请求，`TextureView` 的外部内容回到宿主 HWUI，`SurfaceView`、视频和游戏 Surface 可以形成独立图层节奏。应用提交偏好，SurfaceFlinger 结合所有可见图层与系统策略做选择，Composer3 和面板能力决定可用的离散呈现节拍。

验收时要同时检查输入响应、应用 `SurfaceFrame`、SurfaceFlinger `DisplayFrame`、图层呈现节奏、刷新率选择和功耗。系统没有原样采用请求属于正常行为；应用帧迟到、画面生产方节奏错误或设备策略异常，则要沿各自证据继续定位。

## Android 17 源码与资料

- [Android Developers：Adaptive Refresh Rate](https://developer.android.com/develop/ui/views/animations/adaptive-refresh-rate)
- [AOSP：Adaptive refresh rate](https://source.android.com/docs/core/graphics/arr)
- [Android Developers：View API](https://developer.android.com/reference/android/view/View)
- [Android Developers：ViewGroup API](https://developer.android.com/reference/android/view/ViewGroup)
- [Android Developers：Display API](https://developer.android.com/reference/android/view/Display)
- [Android Developers：FrameRateVelocityPoint API](https://developer.android.com/reference/android/view/FrameRateVelocityPoint)
- [Android Developers：Window API](https://developer.android.com/reference/android/view/Window)
- [Android Developers：Surface API](https://developer.android.com/reference/android/view/Surface)
- [Android Developers：Media frame rate](https://developer.android.com/media/optimize/performance/frame-rate)
- [`View.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/view/View.java)、[`Display.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/view/Display.java)、[`Window.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/view/Window.java) 与 [`Surface.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/view/Surface.java)
- [`SurfaceView.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/view/SurfaceView.java) 与 [`TextureView.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/view/TextureView.java)
- [`Scheduler.cpp`](https://android.googlesource.com/platform/frameworks/native/+/android-17.0.0_r1/services/surfaceflinger/Scheduler/Scheduler.cpp)、[`LayerHistory.cpp`](https://android.googlesource.com/platform/frameworks/native/+/android-17.0.0_r1/services/surfaceflinger/Scheduler/LayerHistory.cpp) 与 [`RefreshRateSelector.cpp`](https://android.googlesource.com/platform/frameworks/native/+/android-17.0.0_r1/services/surfaceflinger/Scheduler/RefreshRateSelector.cpp)
- [`DisplayConfiguration.aidl`](https://android.googlesource.com/platform/hardware/interfaces/+/android-17.0.0_r1/graphics/composer/aidl/android/hardware/graphics/composer3/DisplayConfiguration.aidl)、[`VrrConfig.aidl`](https://android.googlesource.com/platform/hardware/interfaces/+/android-17.0.0_r1/graphics/composer/aidl/android/hardware/graphics/composer3/VrrConfig.aidl) 与 [`IComposerClient.aidl`](https://android.googlesource.com/platform/hardware/interfaces/+/android-17.0.0_r1/graphics/composer/aidl/android/hardware/graphics/composer3/IComposerClient.aidl)
- 内核 [`drm_vblank.c`](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/drivers/gpu/drm/drm_vblank.c) 与 [`drm_vblank.h`](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/include/drm/drm_vblank.h)
