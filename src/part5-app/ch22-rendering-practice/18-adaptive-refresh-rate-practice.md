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

<!-- outline-start -->
## 要点

### 🔹 ARR 的应用侧收益边界
说明 ARR 解决的是高刷新率驻留和模式切换卡顿问题，应用侧仍要管理内容帧率、触摸 boost 和动画节奏。

### 🔹 Android 15/16 API 版本表
覆盖 Android 15 ARR 基础能力、Android 16 `hasArrSupport()`、`getSuggestedFrameRate(int)` 与 `getSupportedRefreshRates()` 的使用边界。

### 🔹 列表、短动画与低频动态内容策略
结合 RecyclerView 1.4 settling 支持、进度条、音频可视化、轮播图和静态阅读场景设计帧率策略。

### 🔹 `WindowManager.LayoutParams.setFrameRateBoostOnTouchEnabled()` 的取舍
说明禁用触摸 boost 的适用场景、误用风险和交互延迟验证方式。

### 🔹 Perfetto 观测与线上指标
用 FrameTimeline、display refresh rate、SurfaceFlinger 和功耗数据验证降刷新率是否引入 jank。

### 🔹 跨设备降级与灰度
处理 HAL 支持差异、OEM 策略差异、Jetpack 支持进度和线上开关。

## 扩展

### 🔸 ARR 与游戏/视频帧率策略的差异
[待补充]

### 🔸 ARR 与 Compose 动画、LazyList 滚动的协同
[待补充]

### 🔸 高刷新率设备的功耗 A/B 设计
[待补充]

<!-- outline-end -->

## 为什么应用还要管帧率

ARR 把刷新率从“切 display mode”推进到“在一个模式内按内容节奏呈现”。在支持 ARR 的面板上，VSync 频率和面板实际呈现频率可以分开，SurfaceFlinger / HWC 根据内容节奏给显示端提示，面板按离散 VSync 步进调整呈现间隔。[已验证: AOSP docs, source.android.com/docs/core/graphics/arr]

这件事对应用有两个直接收益。高刷新率设备不必因为一个进度条、一段音频可视化或轻量循环动画长期驻留 120 Hz；另一边，系统也减少了传统刷新率模式切换带来的黑屏、延迟和帧预测误差。刷新率机制本身详见 2.18 节和 2.19 节，本节只写应用侧怎么用。

应用侧的边界也要讲清。ARR 不能替应用降低每一帧的 CPU / GPU 成本，也不能替业务判断某段内容该跑 30、60 还是 120 fps。它处理的是“显示端按什么节奏接帧”，应用仍要决定“内容按什么节奏产帧”。这也是高刷新率功耗优化最容易漏掉的一层: 只看 jank 会漏功耗，只看功耗又容易把触摸和滚动压钝。[结构参考: Clippings/Android 性能优化 - 如何才能做好 Android 性能优化？.md]

## Android 15/16 API 版本表

Android 15 引入 ARR 能力，Android 16 补上了更可用的查询接口。工程里不要只用系统版本判断，因为 ARR 还依赖 HAL、面板和厂商策略。版本判断只说明 API 能不能调用，`Display.hasArrSupport()` 才说明当前 display 是否暴露 ARR 能力。[已验证: 官方文档, developer.android.com/about/versions/16/features]

| 能力 | API | 最低版本 | 应用侧用途 | 边界 |
| --- | --- | --- | --- | --- |
| View 帧率投票 | `View.setRequestedFrameRate(float)` | Android 15 / API 35 | 给 View 声明内容帧率或分类 | `ViewGroup` 设置不会自动传给子 View |
| 滚动速度提示 | `View.setFrameContentVelocity(float)` | Android 15 / API 35 | 自定义滚动组件在 fling / smooth scroll 每帧上报内容速度 | 每次重绘会重置，必须每帧更新 |
| Window ARR 开关 | `WindowManager.LayoutParams.setFrameRatePowerSavingsBalanced(boolean)` | Android 15 / API 35 | 窗口级启停省电平衡策略 | 默认开启，只有体验回退时才关 |
| 触摸 boost 开关 | `WindowManager.LayoutParams.setFrameRateBoostOnTouchEnabled(boolean)` | Android 15 / API 35 | 控制触摸后短时升帧 | 禁用后要测输入延迟 |
| ARR 支持查询 | `Display.hasArrSupport()` | Android 16 / API 36 | 判断当前 display 是否支持 ARR | 只代表 display 能力，不代表业务策略已生效 |
| 分类建议帧率 | `Display.getSuggestedFrameRate(int)` | Android 16 / API 36 | 把 `NORMAL` / `HIGH` 映射到设备建议值 | 参数只接受 `FRAME_RATE_CATEGORY_NORMAL` 和 `FRAME_RATE_CATEGORY_HIGH` |
| 支持帧率列表 | `Display.getSupportedRefreshRates()` | Android 16 行为更新 | 获取 display 支持的 render rates | Android 15 及以下只返回默认 display mode 的刷新率 |

这段封装用于把系统能力和业务策略拆开。调用方拿到设备建议值，业务层还要结合内容类型和实验结果选择投票值。

```kotlin
fun Display.arrProfile(): ArrProfile {
    if (Build.VERSION.SDK_INT < 36 || !hasArrSupport()) {
        return ArrProfile.Unsupported
    }

    val normal = getSuggestedFrameRate(Display.FRAME_RATE_CATEGORY_NORMAL)
    val high = getSuggestedFrameRate(Display.FRAME_RATE_CATEGORY_HIGH)
    val supported = getSupportedRefreshRates().toList().sorted()

    return ArrProfile.Supported(
        normalFrameRate = normal,
        highFrameRate = high,
        supportedFrameRates = supported,
    )
}

sealed interface ArrProfile {
    data object Unsupported : ArrProfile
    data class Supported(
        val normalFrameRate: Float,
        val highFrameRate: Float,
        val supportedFrameRates: List<Float>,
    ) : ArrProfile
}
```

这里不直接返回“使用 60 Hz”或“使用 120 Hz”。同一台设备在省电模式、外接屏、多窗口、厂商游戏模式下都可能给出不同策略，业务层只消费 `normalFrameRate`、`highFrameRate` 和 supported 列表，再按场景决定投票值。

## 列表、短动画与低频动态内容策略

帧率策略要按内容节奏切，不按页面类型一刀切。一个信息流页面里可能同时有列表 fling、点赞动画、视频卡片、倒计时和静态正文；给根 View 统一投 120 Hz 会让所有内容跟着升帧，省电目标会失效。官方文档也明确: `setRequestedFrameRate()` 调在 `ViewGroup` 上不会自动传播到子 View。[已验证: 官方文档, developer.android.com/develop/ui/views/animations/adaptive-refresh-rate]

| 场景 | 推荐策略 | 验证点 |
| --- | --- | --- |
| `RecyclerView` fling settling | 升级 `androidx.recyclerview:recyclerview:1.4.0`，`androidx.core:core:1.15.0` 起步 | 松手后刷新率应随速度下降，按 7.8 节的 GapWorker 与帧时间一起看 |
| 自定义滚动容器 | 在 fling / smooth scroll 每帧写入 `frameContentVelocity` | Perfetto 中速度下降段不应继续长期驻留最高刷新率 |
| 进度条、波形、音频可视化 | 直接给控件投 `NORMAL` 或 30/60 fps | 交互前后 slow frame 比例不升高，功耗有下降 |
| 短点击动效、按钮反馈 | 保留默认触摸 boost，局部控件可投 `HIGH` | touch down 到首帧反馈不变慢 |
| 静态阅读、设置页、表单页 | 不主动投高帧率，动态装饰降到 `NORMAL` | 静止 3-5 秒后刷新率不应维持高位 |
| 视频卡片 | 视频 Surface 用 `Surface.setFrameRate()` 表达内容 fps，外层 UI 不跟着高刷 | 视频节奏与 UI 动画分开验收 |

自定义滚动组件要在每次重绘时刷新速度值。下面代码只表达接入位置，速度计算要使用组件自己的滚动模型。

```kotlin
class ArrAwareScroller @JvmOverloads constructor(
    context: Context,
    attrs: AttributeSet? = null,
) : View(context, attrs) {
    private var currentVelocityPxPerSecond = 0f

    override fun computeScroll() {
        super.computeScroll()
        if (Build.VERSION.SDK_INT >= 35 && isSettling()) {
            frameContentVelocity = currentVelocityPxPerSecond
        }
    }

    fun onScrollVelocityChanged(velocityPxPerSecond: Float) {
        currentVelocityPxPerSecond = velocityPxPerSecond
    }

    private fun isSettling(): Boolean {
        return currentVelocityPxPerSecond > 0f
    }
}
```

写这类封装时要避免“低刷新率等于低卡顿”的误判。60 fps 内容跑在 120 Hz display 上不一定卡，但 60 fps 内容如果生产节奏不稳，会在 FrameTimeline 里表现成 app deadline missed。ARR 只降低无意义驻留，不能掩盖主线程、RenderThread 或 GPU 工作过重。RecyclerView 的复用、预取和局部刷新仍按 22.2 节处理。

## `WindowManager.LayoutParams.setFrameRateBoostOnTouchEnabled()` 的取舍

触摸 boost 默认开启，用户触摸窗口后系统会在一段时间内提高 render rate。它适合大多数页面，因为触摸后的第一批帧承载了按压反馈、滚动起步和状态变化。禁用 touch boost 的窗口应该非常少，典型目标是低频动态内容长期展示窗口，例如只做慢速进度展示、阅读器自动翻页、后台投屏控制面板。

推荐做法是只对独立窗口做开关，不在全应用统一关闭。代码里要通过 `WindowManager.LayoutParams` 写入，再把 attributes 设回窗口。

```kotlin
fun Window.setTouchBoost(enabled: Boolean) {
    if (Build.VERSION.SDK_INT < 35) return
    attributes = attributes.apply {
        setFrameRateBoostOnTouchEnabled(enabled)
    }
}

fun Window.setArrPowerSavingsBalanced(enabled: Boolean) {
    if (Build.VERSION.SDK_INT < 35) return
    attributes = attributes.apply {
        setFrameRatePowerSavingsBalanced(enabled)
    }
}
```

验收时不要只看平均帧率。禁用 touch boost 后至少要测三类指标: touch down 到按压态首帧的延迟、松手后 fling 起步 200 ms 内的 missed frame、手指连续拖动时的 input / traversal 间隔。任一项变差，就不该把这个开关放进主流程。

## Perfetto 观测与线上指标

ARR 相关问题不能只靠肉眼判断。Perfetto 里同时看 FrameTimeline、SurfaceFlinger、display refresh rate、CPU 频点和功耗计数，才能区分“降刷新率省电成功”和“降刷新率把 jank 带出来”。FrameTimeline 的基础用法详见 13.3、13.4 和 2.18 节，本节只保留验收清单。

| 观察对象 | 看什么 | 结论口径 |
| --- | --- | --- |
| FrameTimeline | `Expected` / `Actual` 是否分叉，jank type 是否增加 | 降帧后 app deadline missed 不能升 |
| SurfaceFlinger | layer frame rate vote、present cadence、refresh rate 变化 | 目标 View 的投票要能影响对应 layer |
| Display / refresh rate counter | 静止、慢动画、fling settling 时是否从高位降下来 | 有降频且无突刺才算有效 |
| UI thread / RenderThread | traversal、draw、syncFrameState、GPU command submit | 若 app 产帧不稳，先修渲染成本 |
| CPU / GPU / battery | 大核占用、GPU busy、功耗曲线 | 功耗下降不能以交互延迟上升换来 |

一次可复现的本地验收可以按这个顺序跑。

```bash
adb shell settings put system peak_refresh_rate 120
adb shell settings put system min_refresh_rate 0
adb shell am force-stop com.example.app
adb shell monkey -p com.example.app 1
# 打开目标页面后录制 Perfetto: gfx, view, sched, freq, power, surfaceflinger, frametimeline
```

线上的指标要分桶。`hasArrSupport=false`、Android 15 支持但无 API 36 查询、Android 16+ 且支持 ARR、厂商高刷策略强干预，这几类设备不能混在一个实验组。只看全量平均值会把 ARR 设备收益和普通高刷设备噪声混到一起。

建议看四组数: 页面级 slow frame / frozen frame、触摸响应分位数、场景功耗或耗电归因、刷新率驻留分布。功耗实验按 25.1 节的 Battery Historian / batterystats 方法保留测试条件，不写没有设备、亮度、网络、温度约束的绝对收益。

## 跨设备降级与灰度

ARR 的跨设备差异比 API 表更复杂。AOSP 文档要求设备实现 HWC composer3 相关能力，并通过 `DisplayConfiguration.vrrConfig`、`vsyncPeriod`、`minFrameIntervalNs`、`notifyExpectedPresent` 等字段描述面板节奏。厂商可以基于自己的功耗策略实现 ARR，应用不能假设所有 120 Hz 设备都支持同样的离散步进。[已验证: AOSP docs, source.android.com/docs/core/graphics/arr]

降级策略按三层写:

- API 不可用: Android 14 及以下不走 ARR 查询，只保留旧的 `Surface.setFrameRate()` 或业务内部帧节流。
- API 可用但 display 不支持: Android 16+ 上 `hasArrSupport()` 为 false 时，不展示 ARR 相关实验开关，不把设备计入 ARR 收益统计。
- display 支持但策略异常: 某些机型可能出现触摸后长期高刷、低频动画过度降帧或外接屏行为不同，要靠远端开关按品牌、型号、系统版本、display id 限制。

灰度开关不要只有一个总开关。至少拆成 View 投票、滚动速度提示、touch boost 调整、Window ARR 开关四类。某一类出问题时只关对应策略，避免把系统默认 ARR 收益一并关掉。

## [自动发现] SurfaceView、TextureView 与普通 View 要分开投票

普通 View 通过 View hierarchy 投票，`SurfaceView` / `TextureView` 更接近独立内容层。视频、相机预览、游戏 Surface 不应该跟随外层容器的 UI 帧率。视频长播放场景用 `Surface.setFrameRate(fps, Surface.FRAME_RATE_COMPATIBILITY_FIXED_SOURCE, strategy)` 表达内容 fps；普通非视频场景使用 `FRAME_RATE_COMPATIBILITY_DEFAULT`。官方媒体文档明确 `FRAME_RATE_COMPATIBILITY_FIXED_SOURCE` 只面向视频。[已验证: 官方文档, developer.android.com/media/optimize/performance/frame-rate]

这也是 ARR 实战和 2.19 节机制的分工: 2.19 讲 SurfaceFlinger 怎么仲裁多 layer，本节的工程规则是让每个 layer 表达自己的内容节奏，不把页面根节点当作唯一入口。

## 扩展

### ARR 与游戏/视频帧率策略的差异

游戏和视频都可能绕过 View hierarchy，但两者目标不同。视频追求内容帧率和显示节奏匹配，24/30/60 fps 的固定源要避免 judder；游戏追求稳定 frame pacing 和输入延迟，可能主动锁 60 fps 以压功耗，也可能在战斗场景请求高帧率。视频优先 `FIXED_SOURCE`，游戏优先 `DEFAULT` 和游戏引擎自己的帧节奏控制。[已验证: 官方文档, developer.android.com/media/optimize/performance/frame-rate]

游戏还要看 Android vitals 的 Slow Sessions。非 View 渲染路径不一定进入 Android vitals 的 UI Toolkit render time 统计，Perfetto、引擎帧时间和 Play Console 游戏指标要一起看。

### ARR 与 Compose 动画、LazyList 滚动的协同

Compose 1.9 开始提供 `Modifier.preferredFrameRate(...)`，作用类似 View 的 `setRequestedFrameRate()`。使用方式仍按局部内容投票: 小型循环动画投 `Normal`，高反馈动效投 `High`，LazyList 的滚动行为优先等 Jetpack 自身支持。Compose 性能问题本身仍按 22.3 节处理，ARR 不替代 recomposition、layout、draw 阶段的成本治理。[已验证: 官方文档, developer.android.com/develop/ui/views/animations/adaptive-refresh-rate]

Compose 页面里最常见的误用是把整个 screen 包一层高帧率 modifier。这样做会让静态文本、按钮、列表和装饰动画一起投高帧率，功耗回到老问题。帧率 modifier 应该贴近会动的 composable。

### 高刷新率设备的功耗 A/B 设计

ARR 的 A/B 不适合只跑 5 分钟。高刷功耗受亮度、温度、网络、触摸频率、后台同步和 SoC 调频影响，短测试容易被噪声盖住。建议每个实验场景至少固定以下条件: 亮度、刷新率系统设置、网络类型、电量区间、温度起点、是否插电、账号数据规模、滚动脚本和页面停留时长。

实验组可以这样拆:

- A 组: 系统默认 ARR，应用不主动投票。
- B 组: 系统默认 ARR，应用对低频内容投 `NORMAL` 或具体低帧率。
- C 组: 同 B 组，禁用指定窗口 touch boost。
- D 组: 关闭 Window ARR，用作回退对照，只在测试包使用。

验收通过的条件不能写成“刷新率降得越低越好”。合格结果应同时满足三条: 目标场景的高刷驻留下降，slow frame / frozen frame 不上升，触摸响应分位数不变差。只满足其中一条都不能进默认策略。

## 本节小结

ARR 实战的判断点很具体: 用 API 查询设备能力，用 View / Surface 表达内容节奏，用 Perfetto 和功耗数据验收，再用灰度开关处理厂商差异。应用侧不要重复实现刷新率选择器，也不要把所有页面统一锁到高刷或低刷。每个会动的内容层给出准确提示，系统才有空间在流畅和功耗之间选到合适的呈现节奏。

## 参考资料

- [Optimize frame rate with adaptive refresh rate](https://developer.android.com/develop/ui/views/animations/adaptive-refresh-rate)
- [Android 16 Features and APIs: Adaptive refresh rate](https://developer.android.com/about/versions/16/features)
- [Display API reference](https://developer.android.com/reference/android/view/Display)
- [WindowManager.LayoutParams API reference](https://developer.android.com/reference/android/view/WindowManager.LayoutParams)
- [Frame rate for media apps](https://developer.android.com/media/optimize/performance/frame-rate)
- [AOSP: Adaptive refresh rate](https://source.android.com/docs/core/graphics/arr)
- [结构参考: Clippings/Android 性能优化 - 如何才能做好 Android 性能优化？.md]
- [结构参考: Clippings/Android 性能优化 - 原理：重新认识应用的速度优化.md]
