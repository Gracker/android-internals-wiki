---
title: "Compose Pager 从基础到高级动画"
chapter: "22.44"
status: finalized
applicable_versions: "Android 14+ (API 34) - Android 17 (API 37)"
tags: ["Jetpack Compose", "动画", "Pager", "性能"]
related_chapters: ["2.1", "2.3"]
created_by: "task2a-knowledge-gap"
created_date: "2026-07-09"
gap_source: "素材驱动"
confidence: medium
last_verified: "2026-07-23"
sources:
- type: official
  path: https://developer.android.com/develop/ui/compose/layouts/pager
- type: official
  path: https://developer.android.com/reference/kotlin/androidx/compose/foundation/pager/package-summary
- type: official
  path: https://developer.android.com/develop/ui/compose/animation
reviewed_by: "hermes-aiw-review-finalize-apply"
reviewed_date: "2026-07-23"
task6_state: reviewed
task9_state: reviewed
pipeline_stage: finalized
last_review_finalize_at: "2026-07-23T19:06:04+08:00"
last_review_finalize_run_id: "20260723-190536-4cc75b06"
---

# 22.44 Compose Pager 从基础到高级动画

## 范围与版本边界

范围只包含 Compose Pager 的高级视觉变换、页面副作用和性能验证。基础 API、Paging 3、page size 与完整调参流程见 [§2.52 Compose Pager 从基础到高级动画](part2-performance/ch2-rendering/2.52-Compose-Pager-从基础到高级动画.md)。

API 与源码以 **Compose Foundation 1.11.4 stable** 为参考。Android 14—17 是这里的验证范围，不是 Pager 的最低系统要求。Compose Foundation 独立发布；Android 17 / API 37 的 `android-17.0.0_r1` 只约束 Choreographer、HWUI、SurfaceFlinger 等平台实现。

普通 Pager 仍画进宿主 App Window：

`Compose composition / layout / draw → HWUI RenderThread → App Window buffer → SurfaceFlinger → HWC → present`

`graphicsLayer` 通常对应窗口内部的绘制图层，不会自动变成 SurfaceFlinger layer。page 中嵌入 SurfaceView、Camera、视频或 native engine 后才可能出现独立 Producer 与 layer，此时宿主 Pager 的 frame 数据不能解释全部画面。

## 1. 为不同业务选择正确的 page 状态

| 状态 | 语义 | 合适的用途 |
|---|---|---|
| `currentPage` | 当前最靠近 snap position 的 page，滚动中可能切换 | 指示器、Tab 视觉选中 |
| `settledPage` | 滚动停止后停靠的 page | 曝光、播放主页面、提交业务选择 |
| `targetPage` | 本轮 fling 或动画预计停靠的 page | 轻量预热、目标提示 |
| `currentPageOffsetFraction` | 当前 page 到 snap position 的高频偏移，范围 `-0.5..0.5` | 图层与绘制变换 |
| `layoutInfo.visiblePagesInfo` | 当前测量结果中的可见 page 集合 | 诊断、可见集合策略；不要在大范围 composition 中直接高频读取 |

`currentPage` 不是“滚动结束页”。拖动跨过 snap position 附近的判定点后，它会在手指抬起前改变；若用户再拖回去，曝光逻辑可能被调用多次。

下面的代码用于在滚动稳定后发送一次业务事件：

```kotlin
LaunchedEffect(pagerState) {
    snapshotFlow { pagerState.settledPage }
        .distinctUntilChanged()
        .collect { page ->
            analytics.onPagerPageSettled(page)
        }
}
```

`snapshotFlow` 只把 state 变化转换为 Flow。事件去重、页面 ID 映射和进程重建后的统计规则仍需业务层定义。

## 2. 页面距离：避免手写错符号

`currentPageOffsetFraction` 只覆盖当前 page，并会在 `currentPage` 切换时改变基准。Foundation 1.11.4 提供 `getOffsetDistanceInPages(page)` 计算任意 page 到当前吸附状态的距离：

```text
page - currentPage - currentPageOffsetFraction
```

结果保留方向，目标 page 可以得到大于一页的绝对距离。旧写法 `(currentPage - page) + currentPageOffsetFraction` 的符号相反；它能用于对称 alpha / scale，但套进 rotation 或 translation 时很容易把方向写反。

### 2.1 把滚动 state 读取推迟到图层阶段

下面的例子把高频 state 读取放在 `graphicsLayer` lambda 内：

```kotlin
HorizontalPager(state = pagerState) { page ->
    Card(
        modifier = Modifier
            .fillMaxSize()
            .graphicsLayer {
                val offset = pagerState
                    .getOffsetDistanceInPages(page)
                    .coerceIn(-1f, 1f)
                val distance = offset.absoluteValue

                alpha = lerp(0.60f, 1f, 1f - distance)
                scaleX = lerp(0.92f, 1f, 1f - distance)
                scaleY = lerp(0.92f, 1f, 1f - distance)
                rotationY = -20f * offset
                cameraDistance = 12f * density
            },
    ) {
        PageContent(page)
    }
}
```

lambda 版本允许 Compose 在图层属性更新时跳过页面内容 composition。若在 Composable 正文先算 `val pageOffset = pagerState.currentPageOffsetFraction`，再把结果传给 modifier，依赖该读取的 page 会随滚动持续重组。

这并不表示动画“没有成本”。alpha、rotation、clip、shadow 或 render effect 可能创建独立 graphics layer，某些组合会使用离屏缓冲；RenderThread、GPU 和内存带宽仍要完成工作。

### 2.2 变换的四个边界

- alpha、scale 一般按 `absoluteValue` 做对称映射；
- rotation、translation 和视差需要保留 offset 方向；
- 对距离做 `coerceIn()`，避免预取 page 产生负 alpha 或过大旋转；
- 视觉变换不会自动改变 hit test、语义顺序和焦点范围。

3D 翻页要在 RTL、横竖屏、TalkBack 和 reduced-motion 条件下复查。高角度 rotation 可能让内容难以阅读，不能只凭截图验收。

## 3. Tab、指示器与编程滚动

Tab 的视觉选中可跟随 `currentPage`，业务选中值更适合在 `settledPage` 后提交。点击 Tab 时调用 `animateScrollToPage()`，新的手势或滚动任务可能取消尚未结束的动画。

下面的实现区分视觉状态和稳定事件：

```kotlin
val scope = rememberCoroutineScope()

TabRow(selectedTabIndex = pagerState.currentPage) {
    tabs.forEachIndexed { index, title ->
        Tab(
            selected = pagerState.currentPage == index,
            onClick = {
                scope.launch {
                    pagerState.animateScrollToPage(index)
                }
            },
            text = { Text(title) },
        )
    }
}
```

快速连续点击会启动竞争的滚动 mutation，早先协程可能收到取消。调用方不应在动画调用之后无条件假设目标 page 已展示；需要稳定结果时观察 `settledPage`。

默认 fling 的 `PagerSnapDistance` 是 `atMost(1)`。放宽为多页只能改变目标范围，不会自动增加 `beyondViewportPageCount`，也不保证所有中间 page 完整显示。

## 4. 额外 page、预取与资源生命周期

`beyondViewportPageCount` 表示在可见 page 前后额外组合、测量和放置的数量。它不包含 Pager 自动 prefetch 的 page。Foundation 1.11.4 默认值仍是 0，但内部另有 prefetch / cache-window 策略。

因此，下列推断都不成立：

- `beyondViewportPageCount = 0` 就只有一个 composition；
- page 不可见后资源会立即释放；
- 设为 1 就必然消除首帧卡顿；
- 可暂停 composition 会让任意重页面不再占用主线程帧预算。

重页面应把“UI 是否已组合”和“业务资源是否活跃”分开。视频、地图、WebView、Camera 和传感器通常以 `settledPage`、可见集合和 Lifecycle 共同决定启停。

下面的示例只让稳定停靠页运行重动画：

```kotlin
HorizontalPager(
    state = pagerState,
    key = { index -> items[index].id },
) { page ->
    val isActive by remember(page) {
        derivedStateOf { pagerState.settledPage == page }
    }

    HeavyPage(
        item = items[page],
        runAnimation = isActive,
    )
}
```

`derivedStateOf` 在派生结果不变时减少下游更新，但它不会降低 `HeavyPage` 自身的绘制成本。播放器、相机等外部对象还应使用 `DisposableEffect` 与宿主 Lifecycle 做成对释放。

### 4.1 可见集合不是 page 生命周期

`layoutInfo.visiblePagesInfo` 是测量结果，滚动期间会高频变化。若业务需要记录可见集合，使用 `snapshotFlow` 收集并只保留 page ID，避免把整个 layout info 传播到页面树。

预取数量没有固定推荐值。调优时从默认值开始，每次只增加一页，并比较：

- 首次进入 page 的 composition / measure 时间；
- frame time 与 jank；
- 图片解码、Paging load 和网络请求；
- Java / native / graphics 内存；
- 页面副作用与外部资源实例数。

## 5. 嵌套滚动与页面重叠

水平 Pager 内嵌垂直 Pager 通常能按手势方向分工；同方向 Pager 或 LazyRow 需要明确父子边界、fling 传递和到边后是否继续滚动。`pageNestedScrollConnection` 控制 Pager 消费子组件 nested delta 的方式，添加一个空的 `Modifier.nestedScroll()` 不会自动解决冲突。

负 `pageSpacing` 可以制造重叠页面，但需要验证：

- 绘制顺序与 `zIndex`；
- click / drag 命中区域；
- TalkBack 焦点顺序；
- clip 和阴影；
- 多指手势与边缘返回手势。

若目标只是显示相邻卡片，优先组合 `PageSize`、`contentPadding` 与正 `pageSpacing`，其几何和可访问性更容易解释。

## 6. 帧时间与 Android 17 出图证据

Compose 动画通常通过 Compose frame clock 运行。业务协程需要逐帧时间时，可用 `withFrameNanos`；直接注册 `Choreographer.FrameCallback` 会增加生命周期与重复注册管理，并不能提供 Pager 私有 deadline。

下面的调用只适合轻量记录或自定义动画时间基准：

```kotlin
withFrameNanos { frameTimeNanos ->
    frameRecorder.mark(frameTimeNanos)
}
```

`frameTimeNanos` 是该帧的时间锚点，不是本次代码已经消耗的时长。回调中执行 I/O、图片解码或大对象分配，仍会阻塞 UI 线程。

Pager 卡顿按标准 HWUI 路径排查：

1. Compose tracing 判断 composition、layout、draw 是否晚；
2. UI thread 和 RenderThread 判断生产窗口 buffer 的 CPU 阶段；
3. FrameTimeline 判断 App、SF、Display 的 deadline 与 present；
4. GPU completion 晚时再看 graphics layer、overdraw、纹理和 shader；
5. page 内有独立 Surface 时，另追对应 Producer、BufferQueue、layer 与 present。

Layout Inspector 的 recomposition count 只能圈定候选代码。用户可见帧是否按时，要用 Macrobenchmark `FrameTimingMetric` 与 Perfetto 验证。

## 7. 常见误判

| 误判 | 修正 |
|---|---|
| `currentPage` 是已停止页 | 业务稳定页使用 `settledPage` |
| offset fraction 范围是 `-1..1` | `currentPageOffsetFraction` 的公开约束是 `-0.5..0.5` |
| `graphicsLayer` 不消耗 GPU | 它避免 layout，并可能避免 composition；绘制、合成和离屏缓冲仍有成本 |
| `beyondViewportPageCount = 1` 总有三页 | visible page 可多于一页，自动 prefetch 也另行存在 |
| composition 存在就表示 page 可见 | 预取、额外 page 和 pinned item 都可能不可见 |
| Pausable Composition 让重页面不再卡顿 | 仍要测量版本、启用状态、页面工作与帧时间 |
| 直接接 Choreographer 能获得 Pager deadline | Pager 没有公开这类 deadline API |
| 平均 FPS 能证明动画稳定 | 同时检查长帧、jank、1% low 与输入到显示延迟 |

## 8. 核查清单

- [ ] Compose Foundation 版本已记录，当前基线为 1.11.4 stable
- [ ] Android 平台版本与 Compose artifact 版本分开
- [ ] 曝光和资源主页面使用 `settledPage`
- [ ] 页面变换使用 `getOffsetDistanceInPages(page)`
- [ ] 高频 offset 在 `graphicsLayer` / draw lambda 中读取
- [ ] 动态数据使用稳定、唯一、可保存的 key
- [ ] beyond-viewport page 与自动 prefetch 分开测量
- [ ] 重资源同时受 page 可见性与 Lifecycle 管理
- [ ] nested scroll、RTL、TalkBack 和 reduced motion 已测试
- [ ] Macrobenchmark 与 Perfetto 均有优化前后结果

## 参考资料

- [Pager in Compose](https://developer.android.com/develop/ui/compose/layouts/pager)
- [Compose Foundation release notes](https://developer.android.com/jetpack/androidx/releases/compose-foundation)
- [Compose Foundation Pager API](https://developer.android.com/reference/kotlin/androidx/compose/foundation/pager/package-summary)
- [Graphics modifiers](https://developer.android.com/develop/ui/compose/graphics/draw/modifiers)
- [Compose performance](https://developer.android.com/develop/ui/compose/performance)

平台结论止于 Android 17 / API 37。升级 Compose 后，应重新核对 Pager 状态、prefetch、nested scroll 修复与动画性能，不沿用未注明 artifact 版本的经验值。
