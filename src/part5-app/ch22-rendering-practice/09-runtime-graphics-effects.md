---

title: "RenderEffect 与 Runtime 图形 API 性能实践"
chapter: "22.9"
section: "22.9"
status: finalized
applicable_versions: "Android 12 (API 31) - Android 17 (API 37)"
last_verified: "2026-07-12"
last_verified_against: "AOSP android-17.0.0_r1 + Android Developers docs"
confidence: high
tags: ["rendereffect", "runtimeshader", "agsl", "hwui", "gpu"]
related_chapters: ["2.7", "2.10", "18.2", "22.5"]
pipeline_stage: ready-to-publish
task6_state: reviewed
task9_state: reviewed
sources:
  - type: aosp
    path: "AOSP android-17.0.0_r1 frameworks/base/graphics/java/android/graphics/RenderEffect.java"
  - type: aosp
    path: "AOSP android-17.0.0_r1 frameworks/base/graphics/java/android/graphics/RuntimeShader.java"
  - type: aosp
    path: "AOSP android-17.0.0_r1 frameworks/base/core/java/android/view/View.java"
  - type: aosp
    path: "AOSP android-17.0.0_r1 frameworks/base/graphics/java/android/graphics/RenderNode.java"
  - type: official
    path: "https://developer.android.com/reference/android/graphics/RenderEffect"
  - type: official
    path: "https://developer.android.com/reference/android/graphics/RuntimeShader"
  - type: official
    path: "https://developer.android.com/develop/ui/views/graphics/agsl/using-agsl"
  - type: official
    path: "https://perfetto.dev/docs/data-sources/frametimeline"
  - type: official
    path: "https://gpuinspector.dev"
  - type: official
    path: "https://developer.android.com/agi/frame-trace/frame-profiler"
  - type: research
    path: "/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/OpenClaw定时任务/AutoResearchClaw调研报告/2026-05-01-rendereffect-gpu-rendering-pipeline-analysis.md"
  - type: clippings
    path: "Clippings/Android 性能优化 - Android 性能优化总结.md"
  - type: clippings
    path: "Clippings/Android 性能优化 - 原理：掌握 App 运行时的内存模型.md"
  - type: clippings
    path: "Clippings/Android 性能优化 - 原理：重新认识应用的速度优化.md"
  - type: clippings
    path: "Clippings/Android 性能优化 - 资源文件的体积优化实战.md"
task2b_state: fixed
consolidated_from:
  - "src/part5-app/ch22-rendering-practice/19-runtimecolorfilter-runtimexfermode-performance.md"
---

# RenderEffect 与 Runtime 图形 API 性能实践

RenderEffect 适合把 View 或 RenderNode 的绘制结果交给 GPU 做后处理：模糊、颜色滤镜、混合、偏移，以及 Android 13（API 33）开始支持的 AGSL 自定义像素处理。它不是“免费特效”。效果需要把节点内容先画进中间层，再读取这块纹理做处理时，成本会落到 RenderThread、GPU 像素处理、纹理带宽和图形内存上。

应用侧要回答三个问题：哪些效果值得实时做，什么时候降级，以及怎样用 trace 和 GPU 工具验证。平台源码锚点是 Android 17 / API 37 / `android-17.0.0_r1`。标准 View 或 Compose 内容仍沿 UI 线程 → RenderThread → BLAST / BufferQueue → SurfaceFlinger → HWC / RenderEngine → present 前进；RenderEffect 改变 HWUI 绘制工作，不会改变这条公共显示路径。关于 RenderNode、Hardware Layer 和 GPU 瓶颈分类，可见 2.7、18.2 和 2.10 节。

## RenderEffect 的适用场景

`RenderEffect` 从 Android 12（API 31）开始提供。AOSP 中 `RenderEffect` 的类注释把它定义为一个中间渲染步骤：效果可以配置到 `RenderNode`，也可以通过 `View.setRenderEffect()` 配置到 View 背后的 RenderNode。`View.setRenderEffect()` 调用 `mRenderNode.setRenderEffect()` 后触发属性失效，下一帧重新参与绘制。`RenderNode.setRenderEffect()` 的注释还明确说明：以 blur 为例，内容会先绘制到独立 layer，再对这块 layer 做模糊处理。

适合用 `RenderEffect` 的场景有三个共同点：效果区域可控、内容变化频率不高、视觉收益足以覆盖 GPU 成本。

| 场景 | 可用 API | 适合程度 | 判断口径 |
|---|---|---|---|
| 局部卡片自身内容模糊、头像遮罩 | `createBlurEffect()` / `createColorFilterEffect()` | 高 | 作用区域小，帧内内容变化少，可以接受离屏处理 |
| 浮动 Window 的跨窗口毛玻璃 | `Window.setBackgroundBlurRadius()` | 取决于设备 | 需要透明浮动 Window，并处理系统运行时关闭 cross-window blur |
| 同一 Window 内的毛玻璃背板 | 明确提供背景图层或快照，再对该内容使用 `RenderEffect` | 中 | `RenderEffect` 只处理目标 RenderNode 内容，不会读取背后的兄弟 View |
| 列表 item 每帧动态模糊 | `createBlurEffect()` | 低 | item 数量多、区域反复进入离开，纹理分配和采样成本会叠加 |
| 颜色统一处理、灰度、tint | `createColorFilterEffect()` | 中到高 | 简单颜色处理比 blur 轻，但仍需在目标机型上验证 |
| 自定义像素效果 | `RuntimeShader` + `createRuntimeShaderEffect()` | 中 | Android 13+，适合小范围、可降级、可缓存的动态效果 |

与传统 Bitmap 预处理相比，`RenderEffect` 的优势是少一次 CPU 侧像素拷贝，能直接在 HWUI 管线里处理 View 的当前绘制结果。代价是每次内容变动都可能让 GPU 重新处理这块区域。静态背景、固定遮罩、品牌氛围图这类效果优先预生成或缓存；手势跟随、转场、局部反馈这类短时动态效果再考虑 `RenderEffect`。

`RenderEffect` blur 与 Window blur 是两套接口。前者处理同一 RenderNode 的输出；后者由系统对窗口后方内容做跨窗口模糊。Window blur 可能因 GPU 能力、省电模式、视频 multimedia tunneling 或系统配置被动态关闭，应用要监听 `WindowManager.addCrossWindowBlurEnabledListener()`，并准备不透明度更高的无 blur 背景。不要调用隐藏 backdrop API。

版本封装的要点是：API 31 之前直接返回，不调用 `View.setRenderEffect()`，因为 Android 11 及以下没有这个方法。

```kotlin
fun View.applyBlurEffectIfSupported(
    enabled: Boolean,
    radiusPx: Float,
) {
    if (Build.VERSION.SDK_INT < Build.VERSION_CODES.S) return

    if (!enabled || radiusPx <= 0f) {
        setRenderEffect(null)
        return
    }

    setRenderEffect(
        RenderEffect.createBlurEffect(
            radiusPx,
            radiusPx,
            Shader.TileMode.CLAMP,
        ),
    )
}
```

这段代码的边界是：API 31 以下直接返回；API 31+ 才允许清空或设置效果。动画性能里的 RenderEffect 降级封装详见 22.5 节。

## HWUI 管线中的成本来源

`RenderEffect` 的成本不只来自 API 调用本身。对 blur 这类效果，AOSP 注释已经给出运行路径：先把目标 RenderNode 的内容绘制到独立 layer，再对这个 layer 做处理。这会增加中间纹理以及对应的读写开销。

一块 1080 × 2400、RGBA_8888 格式的全屏中间纹理，理论像素数据约 9.9 MB。实际 GPU 内存还会受到 stride、内存对齐、tile buffer、驱动池化和格式影响，所以这个数字只能当下限估算。做图形内存分析时，可以把 Graphics / GL / EGL mtrack 拆开看：不要只看 Java heap，要同时看 Graphics、GL mtrack、EGL mtrack 和 GPU memory track。

成本主要有四类：

- **离屏层分配**：效果区域越大，中间纹理越大。全屏 blur、沉浸式背景 blur、多个浮层叠加，都会放大 GPU 内存和带宽压力。
- **额外绘制与采样**：内容先画到中间层，再作为纹理读取并写回目标帧。blur 半径越大，单个输出像素周围要读取的输入像素范围越大。
- **失效与重绘**：`setRenderEffect()` 变更会触发 View 属性失效；内容本身频繁 `invalidate()` 时，效果输入也会跟着更新。动画中同时改变内容和效果参数，最容易把成本放进每一帧。
- **链式效果叠加**：`createChainEffect(outer, inner)` 表示 `outer(inner(source))`。链越长，中间结果越多，调试时也更难判断是哪一层推高了 GPU 时间。

这些代价和 2.7 节的 Hardware Layer 很像，但语义不同：Hardware Layer 主要为“复用同一批绘制结果”服务；RenderEffect 为“对绘制结果做视觉处理”服务。两者都可能产生离屏渲染，收益都依赖区域、复用次数和内容变化频率。

## RuntimeShader / AGSL 的实践边界

`RuntimeShader` 从 Android 13（API 33）开始提供。AOSP `RuntimeShader` 注释说明，AGSL 用于在 Canvas 或 RenderNode 绘制管线的某个阶段计算每个像素颜色，并不定义完整 GPU 管线阶段。官方文档也说明，shader uniform 可以通过 `eval()` 按坐标读取输入 shader；`RenderEffect.createRuntimeShaderEffect(shader, uniformShaderName)` 会把安装该效果的 RenderNode 内容绑定到指定 uniform 上。

AGSL 适合做系统 blur API 覆盖不到的小范围像素处理，例如水波、局部遮罩、扫描线、渐变扰动。它不适合把复杂图像算法直接搬进每帧 UI 渲染里。每一次 `input.eval(coord)` 都是一次输入采样；多点采样、循环采样、多个输入 shader 叠加，会把每像素工作量推高。

AGSL 的安全用法是：初始化时创建 `RuntimeShader` 和 `RenderEffect`，帧内只更新少量 uniform。

```kotlin
@RequiresApi(Build.VERSION_CODES.TIRAMISU)
class HighlightEffect {
    private val shader = RuntimeShader(
        """
        uniform shader content;
        uniform float2 size;
        uniform float progress;

        half4 main(float2 coord) {
            half4 src = content.eval(coord);
            float x = coord.x / max(size.x, 1.0);
            float band = smoothstep(progress - 0.08, progress, x)
                       - smoothstep(progress, progress + 0.08, x);
            return src + half4(half3(band * 0.12), 0.0);
        }
        """.trimIndent(),
    )

    private val effect = RenderEffect.createRuntimeShaderEffect(shader, "content")

    private var effectApplied = false

    fun applyTo(view: View, progress: Float) {
        shader.setFloatUniform("size", view.width.toFloat(), view.height.toFloat())
        shader.setFloatUniform("progress", progress.coerceIn(0f, 1f))
        // 同一个 RenderEffect 已安装后，更新 uniform 不会请求下一帧
        if (!effectApplied) {
            view.setRenderEffect(effect)
            effectApplied = true
        } else {
            view.postInvalidateOnAnimation()
        }
    }

    fun clear(view: View) {
        view.setRenderEffect(null)
        effectApplied = false
    }
}
```

这段示例只做一次输入采样，并把动态参数限制在 `size` 和 `progress` 两个 uniform 上。`View.setRenderEffect()` 在 RenderNode 属性变化时会触发属性失效；同一个 `RenderEffect` 已经安装后，后续只改 `RuntimeShader` uniform 不会自动请求下一帧，所以动画场景要显式调用 `postInvalidateOnAnimation()`，或交给动画框架驱动重绘。进入工程后，还要补三个保护：API 33 以下走静态效果或无效果；页面不可见时清空效果；低端机或省电模式下关闭动态 shader。

`RuntimeShader(shaderSource)` 构造时会编译 AGSL，源码或 uniform 声明不合法时会抛出 `IllegalArgumentException`。不要在动画回调或 composable 热路径里构造它，也不要在页面加载时创建所有 shader。更稳的做法是按场景懒创建、按效果实例复用，并在功能灰度前用目标设备覆盖编译失败与驱动差异。需要预热时，只预热首屏短时间内会使用的效果，避免把启动阶段变成 shader 初始化阶段。

## 常见 UI 效果的选型

RenderEffect 的选型可以按“动态性”和“面积”拆开：越动态、越大面积，越不适合实时效果。

| UI 效果 | 推荐方案 | 不推荐方案 | 验证指标 |
|---|---|---|---|
| 浮动弹窗背后的毛玻璃 | 设备支持时使用 Window background blur；无支持时提高背景不透明度 | 在空白背板 View 上设置 `RenderEffect` 并期待它读取后方窗口 | FrameTimeline jank、cross-window blur 状态、GPU memory |
| 同一窗口局部背景模糊 | 把明确的背景图层/快照限制在背板区域，再应用 `RenderEffect` | 对整页根 View 做全屏 blur | `frameOverrunMs`、RenderThread `DrawFrame`、GPU memory |
| 首页大背景氛围图 | 预模糊 Bitmap / WebP / 远端下发素材 | 每次进入页面实时生成大半径 blur | 首帧耗时、纹理上传、Graphics 内存 |
| 列表 item 圆角 + 阴影 + 蒙版 | 尽量用图片解码裁剪、Outline、静态阴影资源；只对焦点 item 使用动态效果 | 每个 item 同时启用 blur、mask、alpha 和 RuntimeShader | 滑动 P90 / P99、GPU busy、过度绘制 |
| 转场中的背景淡化 | alpha / scale / color filter 优先；必要时短时间局部 blur | 转场全程改变 blur 半径并覆盖全屏 | 转场期间 actual timeline、GPU completion |
| 品牌动效或扫描光 | AGSL 小范围、低采样、uniform 驱动 | 多层 RuntimeShader 链式叠加 | AGI 中 fragment / texture 相关计数器 |

列表场景需要单独保守处理。RecyclerView 的 item 复用意味着同一个 View 会不断绑定新内容——离屏层的输入也在不断变化。单个 item 的效果看着轻，几十个 item 在滑动中轮流进入可视区，GPU 纹理分配、采样和过度绘制就会同时叠加。工程上的稳妥做法是：列表中只给“有交互焦点”的那个 item 保留动态效果，其余 item 使用静态资源。

## Perfetto 与 GPU 工具观测

RenderEffect 问题在 trace 里常见的模式是：UI Thread 很短，RenderThread 或 GPU 时间变长，FrameTimeline 的 actual timeline 超过 expected timeline。标准 App Window 中，App actual slice 可以覆盖 GPU work 与 buffer post，但 `queueBuffer()` 或 App slice 结束仍不证明 SurfaceFlinger 已 latch 或 display 已 present。要用同一帧的 SurfaceFrame、DisplayFrame 与 jank type 继续核对系统侧结果。

排查时按四步走：

1. **先看 deadline 与 FrameTimeline**：API 31+ 用 Macrobenchmark `frameOverrunMs` 或 FrameMetrics overrun 找超期帧，再对齐 expected / actual timeline。不要只看平均帧耗时。
2. **再看 UI Thread 与 RenderThread**：UI Thread 短而 RenderThread `DrawFrame` 拉长，通常指向绘制、纹理上传或 GPU 提交；UI Thread 自身很长，则先回到布局、绘制命令和主线程任务排查。
3. **接着看 GPU 轨道和 counter**：先枚举设备 producer 暴露的 counter name/id；若存在 `gpu_busy` 或类似的利用率 counter 则纳入对照。Android 16 CDD 7.1.4.6 要求支持 GPU profiling 的设备输出符合 Perfetto GPU counters / RenderStage 规范的数据，但 `gpu_busy` 不在该规范的标准命名里，不同设备的 GPU 利用率精度也不对齐。旧版本按设备厂商查可用 counter。counter 不可用或不稳定时，退回 AGI 或厂商工具拆分 fragment、texture、bandwidth。
4. **做开关对照**：同一设备、同一页面、同一脚本分别跑“无效果 / 小半径 / 大半径 / 静态预渲染”，确认变化来自效果本身，而不是网络、数据加载或动画时序。

AGI 适合在开发和预发布阶段做 GPU 分析。Frame Profiler 直接追踪 Vulkan；OpenGL ES 模式会通过 AGI 提供的 ANGLE 转成 Vulkan 后再捕获，因此结果可能包含图形后端变化，不能当作原厂 GLES 驱动的无扰动测量。System Profiler 的 counter、GPU slice 和支持程度随设备变化。官方目前把 Android Performance Analyzer beta 作为系统 profiling 的新推荐工具；项目切换工具时仍要保留 Perfetto trace 与同一对照脚本。

## 优化清单

上线前把 RenderEffect 作为可降级的 GPU 功能处理，不要把它当普通 View 属性。

- **限制区域**：优先给最小子 View 设置效果，不要把根 View、整页容器、RecyclerView 作为默认作用对象。
- **限制半径**：blur 半径做成配置项，按设备档位和运行时 overrun 分级。可变刷新率设备不使用固定 16 ms 或 8.33 ms 阈值，API 31+ 直接看该帧 deadline。
- **限制时长**：转场结束后清空 `setRenderEffect(null)`；页面不可见、进入后台、列表 item 离屏时释放效果引用。
- **减少输入变化**：内容每帧变化时，优先拆成两层：静态背景层做效果，动态内容层直接绘制。
- **避免链式叠加**：blur、color filter、RuntimeShader、alpha、clip 同时叠加时，每加一层都要重新跑一轮 Trace 对照。
- **缓存静态结果**：大背景、固定蒙版、品牌氛围图优先用预渲染资源；资源策略也要按图片压缩、格式选择和使用频率拆开考虑。
- **建立降级开关**：Android 16 / API 36+ 设备若支持 `SystemHealthManager.getGpuHeadroom()`，可把 GPU Headroom 作为质量调节信号之一。有效结果范围是 0—100，也可能暂时返回 `Float.NaN`；一次有效调用至少包含一笔同步 Binder transaction，可能超过 1 ms，不能在 UI/RenderThread 或逐帧回调中查询。调用侧要处理 `UnsupportedOperationException`、`IllegalArgumentException`，并遵守 `getGpuHeadroomMinIntervalMillis()`。旧版本或不支持该能力的设备，继续使用设备档位、温控、帧 overrun 和灰度开关。
- **写清版本边界**：`RenderEffect` 需要 API 31+，`RuntimeShader` / `createRuntimeShaderEffect()` 需要 API 33+。API guard 要包住所有调用点，包括清空效果。

## RuntimeColorFilter 与 RuntimeXfermode：区分节点效果和绘制命令

`RenderEffect` 作用于 RenderNode/图层的结果；API 36 的 `RuntimeColorFilter` 与 `RuntimeXfermode` 则进入具体 draw command。两者都使用 AGSL，却不能互换：前者适合对一整棵已绘制内容做 blur、shader 或 chain，后者分别改变 source 颜色或 source/destination 的混合关系。

`RuntimeColorFilter` 的 shader 输入是当前 draw command 产生的 source color；`RuntimeXfermode` 同时接收 source 与 destination。destination 指“当前 Canvas 目标里已经存在的像素”，其范围受 draw 顺序、clip、`saveLayer()` 和离屏 layer 影响。需要把混合限制在组件 bounds 时，应显式建立最小离屏作用域；没有隔离就直接使用 dst 语义，可能影响父 Canvas 已绘制内容。

AGSL 颜色遵守 premultiplied alpha。shader 输出若把 RGB 与 alpha 当作互不相关的直通道，透明边缘容易产生色边；使用 wide color 或 HDR 时还要验证输入/输出色域与精度。动态 uniform 可复用同一个 shader/filter/xfermode 实例并更新数值，不要逐帧重新解析 AGSL 或重建对象；shader 结构、混合模式或作用范围改变时再重建。

测量时把四组变量分开：普通 `SrcOver`、单独 color filter、单独 xfermode、完整 filter+xfermode/layer。比较 UI 线程 draw recording、RenderThread、GPU duration、离屏目标和 FrameTimeline；像素正确性用截图对照覆盖透明边缘、不同背景、裁剪和 API guard。API 36 以下必须走明确 fallback，清理路径也要移除旧的 filter/xfermode 引用。

## 扩展

### RenderEffect 与 Hardware Layer 的交互

RenderEffect 和 Hardware Layer 都可能让内容先进入离屏 GPU 纹理，但不要把它们混成同一个优化开关。Hardware Layer 的收益来自“内容不变、后续复用”；RenderEffect 的收益来自“视觉效果由 GPU 处理”。当一个 View 同时有 `LAYER_TYPE_HARDWARE`、alpha、clip 和 RenderEffect 时，HWUI 的合成策略会更复杂，Trace 里也更难把成本归因到某一个属性。

工程建议是一次只引入一个变量：先验证不加 Hardware Layer 的 RenderEffect 成本，再验证 Hardware Layer 是否减少重复绘制。若 Perfetto 中已经出现密集 `buildLayer` 或 GPU memory 抖动，不要继续叠加效果；先拆 View 层级或缩小效果区域。Hardware Layer 的判断方法详见 2.7 节。

### Compose graphicsLayer / RenderEffect 对应关系

Compose 的 `graphicsLayer` 可以通过 Compose 的 RenderEffect 包装把效果应用到图层。性能模型与 View 一致：设置 RenderEffect 时，Compose 会进入离屏合成语义；`alpha < 1f`、clip、shadow、RenderEffect 组合时更容易触发额外 buffer。Compose 侧不要把效果挂到大范围根节点，优先挂到视觉区域最小的 composable。

Compose 与 View 在 RenderThread 之后共用标准管线，详见 18.2 节。排查 Compose 页面时，MainThread 上看 recomposition / layout；RenderThread 和 GPU 侧仍按上述 RenderEffect 方法做对照。

### 厂商 GPU 对模糊效果的差异

不同 GPU 对 blur 和 RuntimeShader 的表现差异很大。Adreno、Mali、PowerVR 的驱动、tile buffer、纹理缓存、shader 编译和 GPU counter 命名都不一致；同一段 AGSL 在不同设备、驱动和温控状态下可能落在不同的 deadline 位置，不能从单机结果推导固定增量。

上线策略不要只用一台 Pixel 或一台旗舰机判断。测试设备至少覆盖项目用户量占比高的低端、中端与高刷新率机型；每类设备都跑“冷启动后首次进入页面”和“持续滑动/转场”的受控场景。指标记录 `frameOverrunMs` 分布、jank 数、frame count、设备实际暴露的 GPU counter、图形内存，以及温度和 display mode。

## 参考资料

**AOSP 源码（android-17.0.0_r1）：**
- [`RenderEffect.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/graphics/java/android/graphics/RenderEffect.java)
- [`RuntimeShader.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/graphics/java/android/graphics/RuntimeShader.java)
- [`View.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/view/View.java)
- [`RenderNode.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/graphics/java/android/graphics/RenderNode.java)

**官方文档：**
- [RenderEffect API](https://developer.android.com/reference/android/graphics/RenderEffect)
- [RuntimeShader API](https://developer.android.com/reference/android/graphics/RuntimeShader)
- [AGSL 使用指南](https://developer.android.com/develop/ui/views/graphics/agsl/using-agsl)
- [Window blur 指南](https://source.android.com/docs/core/display/window-blurs)
- [SystemHealthManager API](https://developer.android.com/reference/android/os/health/SystemHealthManager)
- [FrameTimeline 数据源](https://perfetto.dev/docs/data-sources/frametimeline)
- [AGI Frame Profiler](https://developer.android.com/agi/frame-trace/frame-profiler)
