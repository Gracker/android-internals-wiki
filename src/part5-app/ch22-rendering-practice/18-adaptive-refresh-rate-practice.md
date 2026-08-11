---
title: "Adaptive Refresh Rate 与帧率策略实战"
chapter: "22.18"
status: ready-for-review
drafted_date: "2026-05-26"
applicable_versions: "Android 15 (API 35) - Android 17 (API 37)"
last_verified: "2026-05-26"
last_verified_against: "Android Developers 2026-05, AOSP docs 2026-04"
confidence: high
sources:
  - type: official
    path: "https://developer.android.com/develop/ui/views/animations/adaptive-refresh-rate"
  - type: official
    path: "https://developer.android.com/about/versions/16/features"
  - type: official
    path: "https://developer.android.com/reference/android/view/Display"
  - type: official
    path: "https://developer.android.com/reference/android/view/WindowManager.LayoutParams"
  - type: official
    path: "https://developer.android.com/media/optimize/performance/frame-rate"
  - type: aosp
    path: "https://source.android.com/docs/core/graphics/arr"
  - type: clippings-structure
    path: "Clippings/Android 性能优化 - 如何才能做好 Android 性能优化？.md"
  - type: clippings-structure
    path: "Clippings/Android 性能优化 - 原理：重新认识应用的速度优化.md"
tags: [adaptive-refresh-rate, frame-rate, jank, power, android16]
related_chapters: ["2.18", "2.19", "7.8", "22.2", "25.1"]
created_by: "task2a-knowledge-gap"
created_date: "2026-05-26"
gap_source: "官方文档/章节深挖/素材驱动"
gap_score: "18/20"
---

# 22.18 Adaptive Refresh Rate 与帧率策略实战

## 从三个帧率开始判断

ARR 处理显示节奏，却不会缩短应用一帧的 CPU、GPU 或解码耗时。排查前要分清三个量：

- **内容帧率**：视频、游戏或动画每秒产生多少个不同画面；
- **应用 render rate**：应用收到帧回调并提交新 buffer 的节奏；
- **Display refresh rate**：显示设备更新画面的节奏。

60 fps 的应用可以运行在 120 Hz Display 上，每个应用帧保持两个刷新周期，画面仍然均匀。应用平均达到 60 fps，也可能因为提交间隔忽快忽慢而出现卡顿。帧率平均值、呈现间隔和输入延迟回答的是不同问题。

平台实现固定到 Android 17 / API 37 / `android-17.0.0_r1`，kernel 边界固定到 `android17-6.18-2026-06_r6`。ARR 从 Android 15 进入平台；面向应用的支持条件是 Android 15 QPR1 及以上，并且设备实现对应 Composer3 HAL 能力。版本满足条件仍不能证明某块 Display 支持 ARR。

在 ARR 配置中，Display VSync/TE 节拍可以与内容刷新节拍分开。面板在同一个 display mode 内，按 TE 周期的离散倍数选择呈现时机。这样可以减少仅为改变刷新率而切换 display mode 的次数，也能让静态内容和低频动画降低高刷驻留。相关系统机制见 [2.2 帧率](../../part1-fundamentals/ch02-rendering/02-framerate.md) 和 [18.18 可变刷新率渲染管线](../../part2-performance/ch18-rendering-pipelines/18-variable-refresh-rate.md)。

应用侧保留两项责任：控制产帧成本和节奏，并向系统准确描述内容偏好。ARR 不会修复主线程超时、RenderThread 堵塞、GPU 迟完成、视频时间戳错误或 BufferQueue 堆积。

## Android 15—17 API 边界

工程代码应同时检查 API 可用性和目标 Display 的能力。Android 15 上可以提交 View、Window 与 Surface 提示，但公开的 ARR 能力查询从 Android 16 才可用。

| 能力 | API | 版本 | 用途与限制 |
| --- | --- | --- | --- |
| Surface 内容帧率 | `Surface.setFrameRate()` | API 30；三参数版本 API 31 | 提交 Surface 级偏好；不会替 Producer 限速 |
| 清除 Surface 投票 | `Surface.clearFrameRate()` | API 34 | 内容结束或目标改变时撤销旧投票 |
| View 帧率投票 | `View.setRequestedFrameRate(float)` | API 35 | 可传具体值或 View category；View 需要重绘时才参与 |
| 滚动速度提示 | `View.setFrameContentVelocity(float)` | API 35 | smooth scroll / fling 每个绘制帧上报 pixels/second |
| Window 省电平衡 | `Window.setFrameRatePowerSavingsBalanced(boolean)` | API 35 | 控制窗口是否采用 ARR 省电平衡；默认开启 |
| Window 触摸升帧 | `Window.setFrameRateBoostOnTouchEnabled(boolean)` | API 35 | 控制该窗口的 touch boost；默认开启 |
| ARR 能力查询 | `Display.hasArrSupport()` | API 36 | 查询当前 Display 是否公开支持 ARR |
| category 建议值 | `Display.getSuggestedFrameRate(int)` | API 36 | 只接受 `NORMAL`、`HIGH` 两个 Display category |
| UI Surface 下限语义 | `Surface.FRAME_RATE_COMPATIBILITY_AT_LEAST` | API 36 | 用于 UI、动画、滚动和 fling；视频、游戏有各自语义 |
| 支持的 render rates | `Display.getSupportedRefreshRates()` | API 21，API 36 改变返回语义 | API 36+ 返回 Display 支持的 render rates；旧版本只覆盖默认 mode 的刷新率 |
| 速度—帧率映射 | `Display.getFrameRateVelocityMapping()` | API 37 | 返回当前 Display 的滚动速度映射；换屏或 Display 变化后要重查 |

`getSuggestedFrameRate()` 返回设备为 category 配置的建议值。它不是当前刷新率，也不是系统对请求结果的承诺。`getSupportedRefreshRates()` 的方法年龄与 API 36 的行为更新也要分开记录，不能把它写成 Android 16 新增的方法。

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

`QueryUnavailable` 表示 API 35 没有公开查询入口，不表示设备一定缺少 ARR。应用仍可安全提交公开的 View 或 Surface hint，由系统按设备能力处理。折叠屏内外屏、外接屏和窗口迁移都可能改变 `Display`，缓存结果时应带上 `displayId`，并在 display changed 后重新读取。

Android 17 的 `getFrameRateVelocityMapping()` 主要服务滚动组件。普通自定义 View 上报速度即可，`View` 会按当前 Display 的映射换算偏好；应用没有必要复制一套固定速度阈值。

## View 投票要贴近会更新的内容

View 系统在每个绘制帧收集可见、需要重绘的 View 投票，再汇总为宿主窗口 layer 的提示。category 包含：

- `REQUESTED_FRAME_RATE_CATEGORY_DEFAULT`：恢复框架默认行为；
- `REQUESTED_FRAME_RATE_CATEGORY_NO_PREFERENCE`：该 View 明确不影响结果；
- `REQUESTED_FRAME_RATE_CATEGORY_LOW`：适合低速、小面积且高平滑度收益有限的动画；
- `REQUESTED_FRAME_RATE_CATEGORY_NORMAL`：适合不依赖高刷的动画，设备通常把它映射到 60 Hz 附近；
- `REQUESTED_FRAME_RATE_CATEGORY_HIGH`：适合高平滑度收益明确的动画，功耗也可能上升。

同一帧中，View 层通常采用较高的有效投票。进入 SurfaceFlinger 后，还会综合其他应用 layer、SystemUI、touch、idle、功耗 policy、可用 mode 和 seamless 条件。这里不存在“某个 View 投 120，屏幕就锁定 120 Hz”的保证。

`ViewGroup.setRequestedFrameRate()` 在 API 35 不会自动传给子 View。API 36 增加了 `ViewGroup.propagateRequestedFrameRate()`，需要对子树传播时也应明确覆盖规则。给页面根节点长期投 `HIGH` 会扩大高刷范围，进度条、视频卡片、列表与静态正文也更难按各自节奏工作。

场景策略可以按下面的边界制定：

| 场景 | 合适的表达 | 验收重点 |
| --- | --- | --- |
| 小型进度条、低频波形 | 局部 View 投 `NORMAL` 或经设备验证的具体值 | 动画节奏稳定，高刷驻留下降 |
| 点击反馈、短位移动画 | 保留 touch boost；卡顿时对局部 View 评估 `HIGH` | ACTION_DOWN 到首个可见反馈 |
| 静态阅读、表单 | 不制造无意义 invalidation，不主动投高值 | 静止后无持续 App 帧 |
| `RecyclerView` fling | `RecyclerView` 1.4.0 及以上；配套 AndroidX Core 1.15.0 及以上 | 松手后随速度降低 render rate |
| `NestedScrollView` | AndroidX Core 1.15.0 及以上 | 速度下降段的节拍与滚动位移 |
| 自定义滚动容器 | fling / smooth scroll 的每个绘制帧上报速度 | 速度值、帧回调与 scroll offset 同步 |
| 视频卡片 | 视频 Surface 表达源帧率，宿主控件单独投票 | 视频 cadence 与宿主 UI 分开观察 |

下面的例子从 `OverScroller` 读取当前 fling 速度，并在每个绘制帧更新提示。

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

`currVelocity` 已是非负的 pixels/second。`setFrameContentVelocity()` 的值只对下一次 drawn frame 有效，所以一次手势只写一次无法覆盖完整 fling。触摸按住期间仍由 touch boost 保持较高节奏；速度映射用于松手后的减速阶段。

ARR 只改变目标节拍。若滚动仍有 app deadline missed，应继续检查布局、绑定、图片、预取、RenderThread 和 GPU，相关 RecyclerView 方法见 [22.2 RecyclerView 性能优化](02-recyclerview-practice.md)。

## Window 开关属于回退手段

touch boost 默认开启。ACTION_DOWN 之后以及手指抬起的一段时间内，系统可以提高 render rate，用于按压态、拖动起步和窗口内的交互反馈。官方文档明确不建议关闭它。

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

`powerSavingsBalanced=false` 会关闭该窗口的 ARR 省电平衡，通常提高耗电；它不能指定一个固定 Hz。`touchBoostEnabled=false` 也不适合作为全应用默认值。两项都应有独立远端开关，避免一次回退影响另一项策略。

关闭 touch boost 的实验至少测量：

- ACTION_DOWN 到按压态首个 present 的延迟；
- 松手后 200 ms 内的 fling 位移、deadline miss 和 cadence；
- 连续拖动时输入事件、traversal、SurfaceFrame 与 DisplayFrame 的间隔；
- 普通、低电量、热限制和多窗口条件下的差异。

## SurfaceView、TextureView 与普通 View 的投票路径

这三类对象的显示拓扑不同，不能合并成“独立内容层”：

| 承载方式 | Android 17 路径 | 投票与观测对象 |
| --- | --- | --- |
| 普通 View | View/HWUI 绘入宿主 App Window buffer | View 投票汇总到宿主 layer |
| `TextureView` | 外部 Producer 写入 `SurfaceTexture`；HWUI 取纹理并采样进宿主 buffer | Producer 设置的帧率可传回 TextureView 偏好，SurfaceFlinger 通常仍看到宿主 layer |
| `SurfaceView` | Producer 写入独立 BufferQueue；BLAST child 作为独立 buffer layer 进入 SurfaceFlinger | 内容 Surface 与宿主窗口可拥有不同 cadence、buffer 和 fence |

Android 17 的 `TextureView` 在 `SurfaceTexture` 上安装 set-frame-rate listener。Producer 对其 `Surface` 调用 `setFrameRate()` 时，回调会更新 TextureView 的 requested frame rate；内容仍要经过 `TextureLayer.updateSurfaceTexture()` 和宿主 HWUI。它没有因此变成独立 SurfaceFlinger 视频 layer。

Android 17 的 `SurfaceView` 则创建 container、BLAST content child 和条件性的 background color layer。视频或相机 Producer 可以按自己的节奏更新 BLAST child，宿主 View 树只负责普通 UI、位置、裁剪、可见性与相对层级。Perfetto 中要分别观察宿主和 SurfaceView 内容。

固定帧率视频适合在承载视频的 Surface 上提交 `FIXED_SOURCE`。下面的调用表达 24 fps 固定源，并把 mode 变化限制为无缝切换。

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

长时间播放且产品接受一次可见切换时，才评估 `CHANGE_FRAME_RATE_ALWAYS`。播放结束、Surface 复用或内容帧率改变时要更新投票；API 34 及以上可用 `clearFrameRate()` 清除。调用成功只表示提示已提交，不表示 Display 已选择 24 Hz 或 120 Hz。

API 36 及以上的普通 UI、动画、滚动 Surface 可以使用 `FRAME_RATE_COMPATIBILITY_AT_LEAST`；游戏继续使用 `DEFAULT`，并由引擎控制 pacing；视频继续使用 `FIXED_SOURCE`。相机预览要按捕获帧率、宿主 UI 和产品延迟目标单独评估，不能因输出到 Surface 就套用视频语义。

## Android 17 怎样处理这些提示

View 层先汇总当前绘制帧的 category 或具体值。Surface 级请求和提交历史进入 layer 状态。Android 17 的 SurfaceFlinger 再沿下面的路径处理：

1. `LayerHistory::summarize()` 生成可见 layer 的需求，带上 vote 类型、期望值、面积权重、focus 与目标 Display；
2. `Scheduler::chooseRefreshRateForContent()` 收集内容需求和全局信号；
3. `RefreshRateSelector::getRankedFrameRates()` 过滤候选并评分；
4. policy、seamless 条件、touch、idle、功耗状态和其他 layer 共同约束结果；
5. 选出的 render rate 或 display mode 改变应用/SF 节拍，并向 HWC 提交显示配置或 ARR cadence。

Android 17 的 `RefreshRateSelector` 区分 `ExplicitDefault`、`ExplicitExactOrMultiple`、`ExplicitExact`、`ExplicitGte`、`ExplicitCategory`、`Heuristic` 等语义。`FRAME_RATE_COMPATIBILITY_AT_LEAST` 对应的最低值请求，与 fixed-source 的精确值或整数倍诉求采用不同评分。touch 和 idle 也有提前返回及延后 boost 分支，不能写成“触摸必定拉满，固定若干秒后降频”。

Composer3 的设备能力位于另一层。`DisplayConfiguration.vrrConfig` 非空时，该配置才属于 ARR；`vsyncPeriod` 表示 VSync/TE 周期，`VrrConfig.minFrameIntervalNs` 约束最短呈现间隔。设备若配置 `notifyExpectedPresentConfig`，framework 可通过 `IComposerClient.notifyExpectedPresent()` 提前告知预计呈现时间和后续 `frameIntervalNs` cadence。厂商仍可按面板与功耗策略决定具体行为。

kernel common `android17-6.18-2026-06_r6` 的 `drivers/gpu/drm/drm_vblank.c` 提供通用 DRM VBlank 计数、事件和时间戳机制。Android 设备不保证采用相同 DRM 显示路径，面板 TE、最低刷新率、plane、带宽与厂商 HWC 策略不能从 common kernel 单独推出。定位到 HWC 之后，还要结合目标设备的 Composer、display driver 和厂商 trace。

## Perfetto 验收：把请求、生产和呈现放在一起

ARR 验收至少同时覆盖四条证据：

| 证据层 | 观察内容 | 能回答的问题 |
| --- | --- | --- |
| 应用输入与工作 | input、Choreographer、UI thread、RenderThread、GPU | 交互是否变慢，应用是否按新 deadline 完成 |
| App SurfaceFrame | expected/actual timeline、`on_time_finish`、`jank_type` | 宿主应用帧是否迟交或迟完成 |
| SurfaceFlinger DisplayFrame | expected/actual timeline、present type、SF jank | 合成与显示提交是否按目标时间完成 |
| 刷新率与 layer | active mode、render rate、layer vote、选择 slice、present cadence | 何时改变节拍，哪个显示对象参与决策 |

App SurfaceFrame 与 SF DisplayFrame 是两种对象。expected 与 actual 的关联用于判断目标时间和完成结果，不能把两条 slice 的视觉“分叉”直接当成某类 jank。`SurfaceView`、视频、相机和游戏的独立 Producer 也未必拥有与标准 HWUI App Window 同样完整的 FrameTimeline 信息；缺失时要回到对应 layer 的 `queueBuffer`、`BufferTX`、acquire fence、latch、HWC 和 present。

View vote 不等于独立 layer vote。普通 View 和 TextureView 的结果通常要在宿主 App Window 上验证；SurfaceView 内容则要找到它自己的 BLAST buffer layer。只看刷新率 counter 下降，无法证明是哪项应用策略触发，也无法证明交互没有受损。

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

脚本只用于实验机。运行前应从 Display modes 或设备设置确认目标值受支持，并在 trace 中验证设置是否生效。日常基线还要保留一组完全不改系统设置的数据，避免把调试 override 当成量产 policy。

应用线上可记录 `displayId`、API level、`hasArrSupport()`、应用提交的策略、窗口模式、FrameMetrics/卡顿指标和交互时延。普通应用拿不到通用、可信的面板刷新率驻留统计；请求值或 `Display.getRefreshRate()` 也不能代替面板功耗证据。刷新率驻留、CPU/GPU 频点和耗电应在实验室 trace、功耗仪或设备提供的可靠计数器中验证。

## 跨设备实验与回退

实验分桶至少包含：

- API 35：可以提交 ARR 相关 hint，无法用公开 API 查询 ARR；
- API 36—37 且 `hasArrSupport=false`：保留安全的 hint，排除在 ARR 收益统计之外；
- API 36—37 且 `hasArrSupport=true`：按 `displayId`、设备型号、build fingerprint、窗口模式和电源状态分组；
- 折叠屏、外接屏、多窗口：分别记录目标 Display，不能沿用主屏能力；
- OEM 高刷、游戏、低电量或热策略介入：单独标记，避免与默认 policy 混算。

回退开关应拆成 View category/具体值、滚动速度提示、touch boost、Window 省电平衡和 Surface 投票五类。出现机型问题时只撤销对应提示。系统默认 ARR 本身仍可继续工作。

功耗 A/B 需要固定亮度、网络、温度起点、电量区间、账号数据、页面停留、输入脚本和刷新率系统设置。每个场景至少比较：

- 系统默认 ARR，应用不增加额外投票；
- 系统默认 ARR，低频动态内容提交局部投票；
- 同一策略下关闭指定窗口 touch boost，仅作为专项实验；
- 关闭 Window 省电平衡，仅作为问题复现和回退对照。

通过标准同时约束高刷驻留、slow/frozen frame、输入到呈现分位数和单位场景能耗。单独降低刷新率不能作为上线结论。

## 游戏、视频与 Compose

视频拥有固有 cadence，24/30/60 fps 应使用 `FIXED_SOURCE`，并保持播放器时间戳、解码输出和 Surface 提交节奏一致。24 fps 内容在 120 Hz Display 上可以形成 5:5 cadence；系统也可能因为其他可见 layer、policy 或 seamless 限制选择别的结果。

游戏的帧率目标通常可以跟随设备和负载变化，使用 `DEFAULT`，并由引擎或 AGDK Frame Pacing 控制逻辑节拍、presentation time 与 in-flight 深度。Surface 投票不会替游戏节流，也不会修复 queue stuffing。非 View 渲染还要结合引擎帧时间、Perfetto 和对应游戏质量指标。

Compose 1.9 提供 `Modifier.preferredFrameRate(Float)` 和 `Modifier.preferredFrameRate(FrameRateCategory)`。投票应靠近持续变化的 composable。整屏统一包 `High` 会扩大高刷范围；`LazyList` 优先使用当前 Compose/AndroidX 自带的滚动支持，再用 trace 判断是否还需局部调整。ARR 也不会减少 recomposition、layout 或 draw 本身的工作量。

## 小结

ARR 策略从内容对象出发：普通 View 和 Compose 在宿主窗口内投票，TextureView 的外部内容回到宿主 HWUI，SurfaceView、视频和游戏 Surface 可以形成独立 layer 节奏。应用提交偏好，SurfaceFlinger 结合所有可见 layer 与系统 policy 做选择，Composer3 和面板能力决定可用的离散呈现节拍。

验收时同时检查输入响应、App SurfaceFrame、SF DisplayFrame、layer cadence、刷新率选择和功耗。提示没有被原样采纳属于允许行为；应用帧迟到、Producer 节奏错误或设备策略异常则要沿各自证据继续定位。

## Android 17 源码与资料

- [Android Developers：Adaptive Refresh Rate](https://developer.android.com/develop/ui/views/animations/adaptive-refresh-rate)
- [AOSP：Adaptive refresh rate](https://source.android.com/docs/core/graphics/arr)
- [Android Developers：View API](https://developer.android.com/reference/android/view/View)
- [Android Developers：ViewGroup API](https://developer.android.com/reference/android/view/ViewGroup)
- [Android Developers：Display API](https://developer.android.com/reference/android/view/Display)
- [Android Developers：Window API](https://developer.android.com/reference/android/view/Window)
- [Android Developers：Surface API](https://developer.android.com/reference/android/view/Surface)
- [Android Developers：Media frame rate](https://developer.android.com/media/optimize/performance/frame-rate)
- [`View.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/view/View.java)、[`Display.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/view/Display.java)、[`Window.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/view/Window.java) 与 [`Surface.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/view/Surface.java)
- [`SurfaceView.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/view/SurfaceView.java) 与 [`TextureView.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/view/TextureView.java)
- [`Scheduler.cpp`](https://android.googlesource.com/platform/frameworks/native/+/android-17.0.0_r1/services/surfaceflinger/Scheduler/Scheduler.cpp) 与 [`RefreshRateSelector.cpp`](https://android.googlesource.com/platform/frameworks/native/+/android-17.0.0_r1/services/surfaceflinger/Scheduler/RefreshRateSelector.cpp)
- [`DisplayConfiguration.aidl`](https://android.googlesource.com/platform/hardware/interfaces/+/android-17.0.0_r1/graphics/composer/aidl/android/hardware/graphics/composer3/DisplayConfiguration.aidl)、[`VrrConfig.aidl`](https://android.googlesource.com/platform/hardware/interfaces/+/android-17.0.0_r1/graphics/composer/aidl/android/hardware/graphics/composer3/VrrConfig.aidl) 与 [`IComposerClient.aidl`](https://android.googlesource.com/platform/hardware/interfaces/+/android-17.0.0_r1/graphics/composer/aidl/android/hardware/graphics/composer3/IComposerClient.aidl)
- kernel [`drm_vblank.c`](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/drivers/gpu/drm/drm_vblank.c) 与 [`drm_vblank.h`](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/include/drm/drm_vblank.h)
