---

title: "RenderEffect 与 Runtime 图形 API 性能实践"
chapter: "22.9"
section: "22.9"
status: finalized
applicable_versions: "Android 12 (API 31) - Android 17 (API 37)"
last_verified: "2026-08-15"
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
    path: "AOSP android-17.0.0_r1 frameworks/base/graphics/java/android/graphics/RuntimeColorFilter.java"
  - type: aosp
    path: "AOSP android-17.0.0_r1 frameworks/base/graphics/java/android/graphics/RuntimeXfermode.java"
  - type: aosp
    path: "AOSP android-17.0.0_r1 frameworks/base/core/java/android/view/View.java"
  - type: aosp
    path: "AOSP android-17.0.0_r1 frameworks/base/graphics/java/android/graphics/RenderNode.java"
  - type: official
    path: "https://developer.android.com/reference/android/graphics/RenderEffect"
  - type: official
    path: "https://developer.android.com/reference/android/graphics/RuntimeShader"
  - type: official
    path: "https://developer.android.com/reference/android/graphics/RuntimeColorFilter"
  - type: official
    path: "https://developer.android.com/reference/android/graphics/RuntimeXfermode"
  - type: official
    path: "https://developer.android.com/develop/ui/views/graphics/agsl/using-agsl"
  - type: official
    path: "https://developer.android.com/develop/ui/compose/graphics/draw/modifiers"
  - type: official
    path: "https://source.android.com/docs/compatibility/16/android-16-cdd"
  - type: official
    path: "https://perfetto.dev/docs/data-sources/frametimeline"
  - type: official
    path: "https://gpuinspector.dev"
  - type: official
    path: "https://developer.android.com/agi/frame-trace/frame-profiler"
  - type: official
    path: "https://developer.android.com/android-performance-analyzer"
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

`RenderEffect` 让 HWUI 在 View 或 RenderNode 已经画完后，再由 GPU 处理这些像素，例如模糊、颜色滤镜、混合和偏移。Android 13（API 33）又加入了基于 Android Graphics Shading Language（AGSL，Android 图形着色语言）的自定义效果。遇到需要先画入离屏缓冲区、再读取纹理的效果，RenderThread 的提交工作、GPU 的逐像素计算、纹理读写带宽和图形内存都会增加。

应用侧要回答三个问题：哪些效果值得实时做，什么时候降级，以及怎样用性能 trace（按时间记录系统事件的轨迹）和 GPU 工具验证。平台源码锚点是 Android 17 / API 37 / `android-17.0.0_r1`。标准 View 或 Compose 内容仍沿 UI 线程 → RenderThread → BLAST / BufferQueue（把图形缓冲区交给系统）→ SurfaceFlinger（系统合成服务）→ HWC / RenderEngine（硬件合成器或系统 GPU 合成器）→ present（送往显示设备）前进。`RenderEffect` 改变的是 HWUI 的绘制工作，不会绕开这条显示路径。RenderNode、Hardware Layer（硬件图层）和 GPU 瓶颈分类分别见 2.7、18.2 和 2.10 节。

## RenderEffect 的适用场景

`RenderEffect` 从 Android 12（API 31）开始提供。AOSP 把它定义为一个中间渲染步骤：效果可以配置到 `RenderNode`，也可以通过 `View.setRenderEffect()` 配置到 View 背后的 RenderNode。`View.setRenderEffect()` 调用 `mRenderNode.setRenderEffect()`；属性确有变化时，View 会请求重新绘制。以模糊为例，`RenderNode.setRenderEffect()` 的注释说明内容会先绘制到独立图层，再对该图层做模糊。这里指离屏图层：像素先写入一块暂不直接显示的缓冲区，处理完成后再合成到目标画面。

适合用 `RenderEffect` 的场景有三个共同点：效果区域可控、内容变化频率不高、视觉收益足以覆盖 GPU 成本。

| 场景 | 可用 API | 适合程度 | 判断依据 |
|---|---|---|---|
| 局部卡片自身内容模糊、头像遮罩 | `createBlurEffect()` / `createColorFilterEffect()` | 高 | 作用区域小，帧内内容变化少，可以接受离屏处理 |
| 浮动 Window 的跨窗口毛玻璃 | `Window.setBackgroundBlurRadius()` | 取决于设备 | 需要透明浮动 Window，并处理系统在运行中关闭跨窗口模糊 |
| 同一 Window 内的毛玻璃背板 | 明确提供背景图层或快照，再对该内容使用 `RenderEffect` | 中 | `RenderEffect` 只处理目标 RenderNode 内容，不会读取背后的兄弟 View |
| 列表项（item）每帧动态模糊 | `createBlurEffect()` | 低 | 列表项数量多、区域反复进入和离开，离屏纹理占用与采样量会增加 |
| 颜色统一处理、灰度、着色（tint） | `createColorFilterEffect()` | 中到高 | 简单颜色处理通常比模糊轻，但仍需在目标机型上验证 |
| 自定义像素效果 | `RuntimeShader` + `createRuntimeShaderEffect()` | 中 | Android 13+，适合小范围、可降级、可缓存的动态效果 |

需要处理 View 的当前画面时，`RenderEffect` 无需先把内容读回 Bitmap，再由 CPU 逐像素修改，可以直接留在 HWUI 管线中。每次内容变化仍可能让 GPU 重新处理这块区域。静态背景、固定遮罩、品牌氛围图优先预生成或缓存；手势跟随、转场、局部反馈这类短时动态效果再考虑 `RenderEffect`。

`RenderEffect` 模糊与 Window blur（窗口模糊）是两套接口。前者只处理同一 RenderNode 的输出；后者由系统模糊窗口后方的画面。Window blur 可能因 GPU 能力、省电模式、视频直通（multimedia tunneling，编解码器与显示路径直接协作的播放模式）或系统配置而动态关闭。应用要监听 `WindowManager.addCrossWindowBlurEnabledListener()`，并准备不透明度更高的无模糊背景。不要通过反射调用 `setBackdropRenderEffect()` 一类隐藏接口。

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

`RenderEffect` 的成本不只来自 API 调用本身。对模糊这类效果，AOSP 注释已经给出运行路径：先把目标 RenderNode 的内容绘制到独立图层，再处理该图层。这会增加中间纹理以及对应的读写开销。

一块 1080 × 2400、RGBA_8888 格式的全屏中间纹理，未压缩的逻辑像素量是 9.9 MiB，按十进制计量约 10.4 MB。实际占用还受行跨度（stride，每行实际分配的字节数）、内存对齐、分块渲染缓冲区（tile buffer）、驱动复用池、压缩和实际格式影响，这个数字只表示量级，不能当作进程图形内存的下限。分析时也不要只看 Java 堆；`dumpsys meminfo` 或 trace 若提供 Graphics、GL/EGL mtrack 与 GPU memory（GPU 内存）轨道，应分别核对。mtrack 是内核或驱动上报的内存记账分类，各设备提供的分类不完全相同。

成本主要有四类：

- **离屏层分配**：效果区域越大，中间纹理越大。全屏模糊、沉浸式背景模糊、多个浮层叠加，都会增加 GPU 内存和带宽压力。
- **额外绘制与采样**：内容先画到中间层，再作为纹理读取并写回目标帧。模糊半径越大，单个输出像素周围要读取的输入像素范围越大。
- **失效与重绘**：`setRenderEffect()` 变更会触发 View 属性失效；内容本身频繁 `invalidate()` 时，效果输入也会跟着更新。动画中同时改变内容和效果参数，最容易把成本放进每一帧。
- **链式效果叠加**：`createChainEffect(outer, inner)` 表示 `outer(inner(source))`。每个子效果都会增加处理工作，但链长不等于临时纹理数量；是否需要独立的中间纹理由 HWUI / Skia 的具体实现决定。是否变慢、慢在哪一层，要靠逐项开关和 trace 判断。

这些代价和 2.7 节的 Hardware Layer 很像，但用途不同。Hardware Layer 把相对稳定的绘制结果缓存为 GPU 图层，供后续帧复用；`RenderEffect` 处理已经画好的像素。两者都可能使用离屏缓冲区，收益取决于作用区域、复用次数和内容变化频率。

## RuntimeShader / AGSL 的实践边界

`RuntimeShader` 从 Android 13（API 33）开始提供。AGSL 在 Canvas 或 RenderNode 绘制过程的某个位置计算每个像素颜色，并不负责顶点处理、光栅化等完整 GPU 管线。uniform 是一次绘制中对所有像素保持一致、可由应用更新的参数；`shader` 类型的 uniform 则能通过 `eval(coord)` 求出指定坐标的输入颜色。`RenderEffect.createRuntimeShaderEffect(shader, uniformShaderName)` 会把目标 RenderNode 的内容绑定到这个 `shader` uniform。AGSL 的 `coord` 使用 Canvas 的局部像素坐标，原点在左上角，不是 0—1 的归一化纹理坐标。

AGSL 适合做系统模糊 API 覆盖不到的小范围像素处理，例如水波、局部遮罩、扫描线、渐变扰动。复杂图像算法若每帧覆盖大面积 UI，GPU 很容易超出帧预算。每次 `input.eval(coord)` 都会计算一次输入；输入是 BitmapShader 时通常涉及纹理采样，输入是渐变或另一个 RuntimeShader 时则执行相应着色器。多点采样、循环采样和多个输入叠加都会增加每个像素的工作量。

下面的写法避免每帧重建对象：初始化时创建 `RuntimeShader` 和 `RenderEffect`，帧内只更新少量 uniform。

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

这段示例只调用一次 `content.eval()`，动态参数也只有 `size` 和 `progress`。AGSL 的 `float2` 是两个 `float` 组成的向量，`half4` 是四个半精度分量，常用来表示 RGBA。`View.setRenderEffect()` 只在 RenderNode 的效果属性变化时请求重绘；同一个 `RenderEffect` 安装后，更新 `RuntimeShader` uniform 不会自动请求下一帧，所以动画场景要显式调用 `postInvalidateOnAnimation()`，或由动画框架驱动重绘。`effectApplied` 属于 `HighlightEffect` 实例，这个示例要求一个实例只服务一个 View。

示例中的加法还假定目标内容完全不透明。AGSL 要求 `main()` 返回预乘 alpha 颜色，也就是透明度为 A 时，RGB 要先乘 A；若输入带透明边缘，新增高光也要乘 `src.a`，否则透明像素可能保留非零 RGB，合成后出现色边。工程中还要补三个保护：API 33 以下使用静态效果或不加效果；页面不可见时清空效果；低端机或省电模式下关闭动态着色器。

`RuntimeShader(shaderSource)` 构造时会编译 AGSL，源码或 uniform 声明不合法时会抛出 `IllegalArgumentException`。不要在动画回调或 Composable 的频繁执行路径里构造它，也不要在页面加载时创建所有着色器。按场景懒创建、按效果实例复用，并在扩大用户范围前用目标设备检查编译失败与驱动差异。如果要提前初始化，只创建首屏短时间内会用到的效果，避免延长启动时间。

默认情况下，`RuntimeShader` 在目标缓冲区的颜色空间中计算。Android 17（API 37）新增 `setWorkingColorSpace()`，可以先在指定 RGB 颜色空间中计算，再转换到目标颜色空间；需要在线性空间做光照等运算时再使用，它不是性能开关。颜色 uniform 应声明为 `layout(color)` 并通过 `setColorUniform()` 赋值，Android 才会做相应的颜色空间转换。

## 常见 UI 效果的选型

判断 `RenderEffect` 是否合适，可以同时看内容变化频率和作用面积：变化越频繁、面积越大，实时处理越容易超出帧预算。

| UI 效果 | 推荐方案 | 不推荐方案 | 验证指标 |
|---|---|---|---|
| 浮动弹窗背后的毛玻璃 | 设备支持时使用 Window background blur（窗口背景模糊）；不支持时提高背景不透明度 | 在空白背板 View 上设置 `RenderEffect` 并期待它读取后方窗口 | FrameTimeline 卡顿类型、跨窗口模糊开关、图形内存 |
| 同一窗口局部背景模糊 | 把明确的背景图层或快照限制在背板区域，再应用 `RenderEffect` | 对整页根 View 做全屏模糊 | `frameOverrunMs`、RenderThread `DrawFrame`、图形内存 |
| 首页大背景氛围图 | 预模糊 Bitmap / WebP / 远端下发素材 | 每次进入页面实时生成大半径模糊 | 首帧耗时、纹理上传、图形内存 |
| 列表项圆角 + 阴影 + 蒙版 | 尽量用图片解码裁剪、Outline、静态阴影资源；只对焦点列表项使用动态效果 | 每个列表项同时启用模糊、蒙版、透明度和 RuntimeShader | 滑动帧耗时 P90 / P99（90 / 99 分位数）、GPU 忙碌率、过度绘制次数 |
| 转场中的背景淡化 | 透明度、缩放或颜色滤镜优先；必要时短时间使用局部模糊 | 转场全程改变模糊半径并覆盖全屏 | 转场期间的 actual timeline、GPU completion（GPU 完成时间） |
| 品牌动效或扫描光 | AGSL 小范围、低采样，只更新 uniform | 多层 RuntimeShader 链式叠加 | AGI 中片元着色、纹理采样相关计数器 |

列表场景需要单独保守处理。RecyclerView 会把同一个列表项 View 绑定到不同数据，离屏层的输入也随之变化。单个列表项的效果耗时不多，几十个列表项在滑动中轮流进入可视区时，离屏纹理占用、采样量和过度绘制仍会一起增加。列表中可以只给当前有交互焦点的列表项保留动态效果，其余列表项使用静态资源。

## Perfetto 与 GPU 工具观测

`RenderEffect` 导致的卡顿常表现为 UI Thread 用时不多，RenderThread 或 GPU 用时却增加。FrameTimeline 的 expected timeline 表示系统给这一帧安排的目标时间，actual timeline 记录实际工作；actual slice（实际时间片）越过预期截止时间，说明该帧没有按计划完成。标准 App Window 的 App actual slice 可以覆盖 GPU 工作和缓冲区提交，但 `queueBuffer()` 返回或 App slice 结束，只表示应用已提交缓冲区。SurfaceFlinger 是否 latch（接收该缓冲区参与合成）、显示设备是否 present（显示该帧），还要看同一帧的 SurfaceFrame、DisplayFrame 和卡顿类型。

排查顺序如下：

1. **FrameTimeline 与截止时间**：截止时间（deadline）是这一帧按计划完成的最晚时刻。API 31+ 可以用 Macrobenchmark `frameOverrunMs`，或比较 FrameMetrics 的 `TOTAL_DURATION` 与 `DEADLINE`，找出超期帧，再按时间戳核对 expected / actual timeline。平均帧耗时会掩盖偶发慢帧，不适合作为唯一指标。
2. **UI Thread 与 RenderThread**：UI Thread 用时不多而 RenderThread `DrawFrame` 耗时增加，原因可能是绘制、纹理上传、GPU 提交或等待 GPU；UI Thread 自身耗时很长，则检查布局、绘制命令记录和主线程任务。
3. **GPU 轨道与计数器**：先枚举设备的 Perfetto producer（负责写入 trace 数据的组件）实际提供的 counter name/id。若有 `gpu_busy` 或类似利用率计数器，再放进对照。Android 16 CDD 7.1.4.6 规定：设备声明支持 GPU 性能分析后，输出必须符合 Perfetto GPU counters / RenderStages 的数据格式；CDD 没有规定一个统一名为 `gpu_busy` 的计数器，各设备的采样口径和精度也可能不同。计数器不可用或不稳定时，改用 AGI 或厂商工具查看片元着色、纹理采样和内存带宽。
4. **开关对照**：在同一设备、页面和操作脚本下，分别测量“无效果 / 小半径 / 大半径 / 静态预渲染”，排除网络、数据加载和动画时序的影响。

AGI 适合在开发和预发布阶段分析 GPU。Frame Profiler 可以直接捕获 Vulkan；捕获 OpenGL ES 时，AGI 要求应用走 OpenGL on ANGLE，由 ANGLE 把 GLES 调用转换到 Vulkan。这条捕获路径改变了图形后端，结果不能当作原厂 GLES 驱动下的无扰动测量。System Profiler 能显示哪些计数器和 GPU 时间片，也取决于设备。Android 官方现已把仍处于公测阶段的 Android Performance Analyzer（APA）列为系统性能分析的新推荐工具；切换工具时应保留同一份 Perfetto trace 配置和操作脚本，方便比较前后结果。

## 优化清单

上线前把 RenderEffect 作为可降级的 GPU 功能处理，不要把它当普通 View 属性。

- **限制区域**：优先给最小子 View 设置效果，不要把根 View、整页容器、RecyclerView 作为默认作用对象。
- **限制半径**：把模糊半径做成配置项，按设备档位和运行时超期值分级。可变刷新率设备不使用固定 16 ms 或 8.33 ms 阈值，API 31+ 直接看该帧的 deadline。
- **限制时长**：转场结束后调用 `setRenderEffect(null)`；页面不可见、应用进入后台、列表项离开可视区时移除效果。若业务对象还持有 `RenderEffect`，清空 View 属性并不会自动释放该对象。
- **减少输入变化**：内容每帧变化时，优先分为两层：静态背景层做效果，动态内容层直接绘制。
- **避免链式叠加**：模糊、颜色滤镜、RuntimeShader、透明度和裁剪同时使用时，每增加一种效果都要重新跑一轮 trace 对照。
- **缓存静态结果**：大背景、固定蒙版、品牌氛围图优先用预渲染资源；图片压缩、格式选择和使用频率要分别考虑。
- **建立降级开关**：Android 16 / API 36+ 设备若支持 `SystemHealthManager.getGpuHeadroom()`，可以把 GPU Headroom 作为质量调节信号之一。它估算 GPU 还能增加多少负载：有效值范围为 0—100，0 表示不能再分配更多 GPU 资源；`Float.NaN` 表示结果暂时不可用。它不是逐帧利用率。一次有效调用至少包含一次同步 Binder transaction，也就是等待另一个进程返回的同步 IPC，耗时可能超过 1 ms，因此不能在 UI Thread、RenderThread 或逐帧回调中查询。调用侧要处理 `UnsupportedOperationException`、`IllegalArgumentException`，并遵守 `getGpuHeadroomMinIntervalMillis()`；调用过密时 API 可能返回缓存值。旧版本或不支持该能力的设备，继续使用设备档位、温控、帧超期分布和远程配置的降级开关。
- **写清版本边界**：`RenderEffect` 需要 API 31+，`RuntimeShader` / `createRuntimeShaderEffect()` 需要 API 33+。版本判断要包住所有调用点，包括清空效果。

## RuntimeColorFilter 与 RuntimeXfermode：区分节点效果和绘制命令

`RenderEffect` 作用于 RenderNode 或图层的最终结果；API 36 的 `RuntimeColorFilter` 与 `RuntimeXfermode` 则装到 `Paint` 上，影响使用该 Paint 发出的具体绘制命令。`Paint.setColorFilter()` 安装前者，`Paint.setXfermode()` 安装后者。三者都能使用 AGSL，但作用位置不同：`RenderEffect` 处理整棵已绘制内容，`RuntimeColorFilter` 改写当前绘制命令产生的新颜色（source color），`RuntimeXfermode` 决定新颜色与目标中已有颜色（destination）怎样合成。

`RuntimeColorFilter` 的 AGSL 入口接收一个 sRGB 输入色，输出也按 sRGB 解释；`RuntimeXfermode` 的入口签名是 `main(src, dst)`，同时接收 source 与 destination，输入和输出同样按 sRGB 解释。destination 是当前 Canvas 渲染目标里已经存在的像素，因此结果受绘制顺序、裁剪区（clip）和 `saveLayer()` 影响。需要把混合限制在组件边界（bounds）内时，可以用 `saveLayer()` 建立尽可能小的离屏作用域；没有这层隔离，该混合函数仍只处理本次命令覆盖的区域，但可能改写该区域内父 Canvas 已经画好的像素。

透明边缘要单独做像素对照，避免把 straight alpha（RGB 尚未乘透明度）与 premultiplied alpha（RGB 已乘透明度）混用；`RuntimeShader` 的预乘约束可参考前面的高光示例。`RuntimeColorFilter` 和 `RuntimeXfermode` 的 sRGB 契约在广色域或 HDR 窗口里尤其需要截图验证，确认色域转换和精度满足设计要求。动态 uniform 可以复用同一个 `RuntimeColorFilter` 或 `RuntimeXfermode` 实例并更新数值；框架会在绘制前通过 `Paint.getNativeInstance()` 取得更新后的底层对象。uniform 的赋值方法不会替 View 请求重绘，动画仍要调用 `invalidate()` 或 `postInvalidateOnAnimation()`。只有 AGSL 程序结构、混合方式或作用范围改变时才重建对象，不要逐帧重新解析源码。

测量时分成四组：普通 `SrcOver`、只加颜色滤镜、只加 `RuntimeXfermode`、完整的颜色滤镜 + `RuntimeXfermode` / 离屏图层。比较 UI 线程的绘制命令记录、RenderThread、GPU 用时、离屏目标和 FrameTimeline。像素正确性用截图覆盖透明边缘、不同背景、裁剪区和版本判断。API 36 以下要使用明确的兼容方案，清理时也要从 Paint 和业务对象中移除旧的 `RuntimeColorFilter` / `RuntimeXfermode` 引用。

## 扩展

### RenderEffect 与 Hardware Layer 的交互

`RenderEffect` 和 Hardware Layer 都可能让内容先进入离屏 GPU 纹理，但不要把它们混成同一个优化开关。Hardware Layer 的收益来自“内容不变、后续复用”；`RenderEffect` 的收益来自“视觉效果由 GPU 处理”。当一个 View 同时有 `LAYER_TYPE_HARDWARE`、透明度、裁剪和 `RenderEffect` 时，HWUI 的合成策略会更复杂，trace 里也更难把成本归因到某一个属性。

一次只改变一个变量：测出不加 Hardware Layer 时的 `RenderEffect` 成本，再检查 Hardware Layer 是否减少重复绘制。若 Perfetto 中频繁出现 `buildLayer` slice（HWUI 构建硬件图层的时间片），或图形内存反复升降，应先调整 View 层级或缩小效果区域。Hardware Layer 的判断方法见 2.7 节。

### Compose graphicsLayer / RenderEffect 对应关系

Compose 的 `graphicsLayer` 可以通过 Compose `RenderEffect` 把效果应用到图层。只要设置 `RenderEffect`，内容就会先进入离屏缓冲区，不受 `CompositingStrategy` 取值影响。默认 `Auto` 策略下，`alpha < 1f` 也会离屏；`ModulateAlpha` 可以省去仅由透明度引起的离屏缓冲区，但图层内有重叠内容时，合成结果可能不同。裁剪或阴影本身不等于必然新增缓冲区，判断时要看完整的 `graphicsLayer` 参数。效果应挂到能覆盖目标视觉区域的最小 Composable 节点。Compose RenderEffect 在 Android 11（API 30）及以下会被忽略，可以用 `RenderEffect.isSupported()` 做能力判断。

Compose 与 View 在 RenderThread 之后共用标准管线，详见 18.2 节。排查 Compose 页面时，在 `MainThread` 轨道观察重组（recomposition）和布局（layout）；RenderThread 和 GPU 侧仍按上述 `RenderEffect` 方法做对照。

### 厂商 GPU 对模糊效果的差异

不同 GPU 执行模糊和 RuntimeShader 的耗时差异很大。Adreno、Mali、PowerVR 的驱动、分块渲染缓冲区、纹理缓存、着色器编译和 GPU 计数器命名并不统一；同一段 AGSL 在不同设备、驱动和温控状态下可能产生不同程度的帧超期，不能从单台设备推导固定耗时增量。

上线策略不能只依据一台 Pixel 或一台旗舰机。测试设备至少覆盖用户量占比高的低端、中端与高刷新率机型；每类设备都测“冷启动后首次进入页面”和“持续滑动 / 转场”两个受控场景。记录 `frameOverrunMs` 分布、卡顿帧数、总帧数、设备实际提供的 GPU 计数器、图形内存、温度和显示模式（分辨率与刷新率）。

## 参考资料

**AOSP 源码（android-17.0.0_r1）：**

- [`RenderEffect.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/graphics/java/android/graphics/RenderEffect.java)
- [`RuntimeShader.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/graphics/java/android/graphics/RuntimeShader.java)
- [`RuntimeColorFilter.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/graphics/java/android/graphics/RuntimeColorFilter.java)
- [`RuntimeXfermode.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/graphics/java/android/graphics/RuntimeXfermode.java)
- [`View.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/view/View.java)
- [`RenderNode.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/graphics/java/android/graphics/RenderNode.java)

**官方文档：**

- [RenderEffect API](https://developer.android.com/reference/android/graphics/RenderEffect)
- [RuntimeShader API](https://developer.android.com/reference/android/graphics/RuntimeShader)
- [RuntimeColorFilter API](https://developer.android.com/reference/android/graphics/RuntimeColorFilter)
- [RuntimeXfermode API](https://developer.android.com/reference/android/graphics/RuntimeXfermode)
- [AGSL 使用指南](https://developer.android.com/develop/ui/views/graphics/agsl/using-agsl)
- [Compose 图形 modifier](https://developer.android.com/develop/ui/compose/graphics/draw/modifiers)
- [Window blur 指南](https://source.android.com/docs/core/display/window-blurs)
- [SystemHealthManager API](https://developer.android.com/reference/android/os/health/SystemHealthManager)
- [Android 16 CDD](https://source.android.com/docs/compatibility/16/android-16-cdd)
- [FrameTimeline 数据源](https://perfetto.dev/docs/data-sources/frametimeline)
- [AGI Frame Profiler](https://developer.android.com/agi/frame-trace/frame-profiler)
- [AGI System Profiler](https://developer.android.com/agi/sys-trace/system-profiler-gui)
- [Android Performance Analyzer](https://developer.android.com/android-performance-analyzer)
