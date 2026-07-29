---
title: "RuntimeColorFilter 与 RuntimeXfermode 性能实践"
chapter: "22.19"
status: ready-for-review
drafted_date: "2026-05-26"
applicable_versions: "Android 16 (API 36) - Android 17 (API 37)"
last_verified: "2026-05-26"
last_verified_against: "Android Developers 2026-05; AOSP master graphics/java/android/graphics"
confidence: medium
sources:
  - type: official
    path: "https://developer.android.com/about/versions/16/features"
  - type: official
    path: "https://developer.android.com/develop/ui/views/graphics/agsl/using-agsl"
  - type: official
    path: "https://developer.android.com/reference/android/graphics/RuntimeColorFilter"
  - type: official
    path: "https://developer.android.com/reference/android/graphics/RuntimeXfermode"
  - type: aosp
    path: "frameworks/base/graphics/java/android/graphics/RuntimeColorFilter.java"
  - type: aosp
    path: "frameworks/base/graphics/java/android/graphics/RuntimeXfermode.java"
  - type: aosp
    path: "frameworks/base/graphics/java/android/graphics/Paint.java"
  - type: clippings-structure
    path: "Clippings/Android 性能优化 - 原理：掌握 App 运行时的内存模型.md"
  - type: clippings-structure
    path: "Clippings/Android 性能优化 - 原理：重新认识应用的速度优化.md"
  - type: clippings-structure
    path: "Clippings/Android 性能优化 - 任务调度优化：线程+CPU，提升任务调度优先级.md"
  - type: clippings-structure
    path: "Clippings/Android 性能优化 - Native 内存优化（下）：Bitmap 的内存占用优化.md"
tags: [agsl, runtimecolorfilter, runtimexfermode, gpu, android16]
related_chapters: ["2.10", "18.2", "22.5", "22.10", "22.17"]
created_by: "task2a-knowledge-gap"
created_date: "2026-05-26"
gap_source: "官方文档/AOSP结构/章节深挖"
gap_score: "16/20"
---

# 22.19 RuntimeColorFilter 与 RuntimeXfermode 性能实践

<!-- outline-start -->
## 要点

### 🔹 Android 16 AGSL 绘制 API 的新增边界
区分 RuntimeShader、RuntimeColorFilter、RuntimeXfermode 三类能力，说明 ColorFilter 与 Xfermode 各自进入绘制管线的位置。

### 🔹 适合实时处理的效果类型
覆盖 threshold、sepia、hue saturation、局部蒙版和自定义混合，区分简单颜色处理与复杂采样效果。

### 🔹 Shader 编译、uniform 更新与缓存
设计 shader 对象复用、参数更新频率、线程归属和动画帧内开销的检查清单。

### 🔹 与 RenderEffect / Hardware Bitmap 的选型关系
说明何时直接挂到 draw call，何时使用 RenderEffect，何时预生成 Bitmap 或 RenderNode 缓存。

### 🔹 GPU、内存带宽与离屏渲染风险
围绕作用区域、过度绘制、纹理读写和低端 GPU 差异建立验证方法。

### 🔹 兼容性与降级路径
处理 API 36 以下设备、厂商 GPU 差异、效果关闭和远程配置策略。

## 扩展

### 🔸 AGSL 单元测试与截图回归
[待补充]

### 🔸 RuntimeXfermode 与传统 PorterDuff 语义对照
[待补充]

### 🔸 Compose graphicsLayer / drawWithCache 接入方式
[待补充]

<!-- outline-end -->

Android 16（API 36）新增 `RuntimeColorFilter` 和 `RuntimeXfermode`，让 AGSL 可以作为 `Paint` 的颜色过滤器或自定义 blender 参与一次绘制。Android 17 沿用这组公开 API。本文以 Android 17 / API 37 / `android-17.0.0_r1` 为平台源码锚点，GPU buffer 与 fence 的内核边界以 `android17-6.18-2026-06_r6` 为锚点。[Android 16 图形能力](https://developer.android.com/about/versions/16/features)

这两个类不应被概括为“给 View 加一个 GPU 特效”。它们进入的是 Skia 的颜色过滤和混合位置：硬件加速窗口通常由 HWUI/Skia 交给 GPU 执行；软件 Canvas 则可能走 CPU 栅格路径。AGSL 编译、每像素算术、绘制面积、重绘频率、目标读写和中间层共同决定成本。标准 HWUI 显示路径见 [18.2 Android View 标准管线](../../part2-performance/ch18-rendering-pipelines/02-android-view-standard.md)，GPU 工作分类见 [2.10 GPU 渲染](../../part1-fundamentals/ch02-rendering/10-gpu-rendering.md)。

## 三类 Runtime API 的输入边界

三个 Runtime 类都接受 AGSL，却处在不同的 Skia 挂点。

| API | 引入版本 | 典型挂载位置 | `main()` 的内建输入 | 适合的工作 |
| --- | --- | --- | --- | --- |
| `RuntimeShader` | Android 13 / API 33 | `Paint.shader`、`RenderEffect` | 当前坐标 | 自定义填充、纹理采样、RenderNode 后处理 |
| `RuntimeColorFilter` | Android 16 / API 36 | `Paint.colorFilter` | 本次绘制产生的颜色 | 灰度、阈值、色相/饱和度、状态色映射 |
| `RuntimeXfermode` | Android 16 / API 36 | `Paint.xfermode` | 源颜色 `src`、绘制目标中的 `dst` | 自定义合成、条件遮罩、标准 `BlendMode` 无法表达的混合 |

[`RuntimeColorFilter`](https://developer.android.com/reference/android/graphics/RuntimeColorFilter) 的入口形状是 `vec4 main(half4 in_color)`，[`RuntimeXfermode`](https://developer.android.com/reference/android/graphics/RuntimeXfermode) 的入口形状是 `vec4 main(half4 src, half4 dst)`。两份类文档都把输入和输出定义为 sRGB。它们没有 `RuntimeShader.main(float2 coord)` 那样的内建像素坐标，所以不适合直接编写邻域模糊、卷积或按屏幕位置变化的纹理效果。

“入口只有颜色”也不等于“对象只能接一个颜色”。Android 17 的两个类都提供 `setInputShader()`、`setInputColorFilter()` 和 `setInputXfermode()`。子效果可以由 AGSL 调用，不过坐标并不会凭空出现；调用 child shader 时仍要有可用坐标表达式。需要逐像素坐标和多点采样的效果，通常交给 `RuntimeShader` 更清楚。

标准能力应排在自定义 AGSL 前面：

- 线性 RGBA 变换与偏移可由 `ColorMatrixColorFilter` 表达；
- 固定颜色叠加可查看 `BlendModeColorFilter`；
- Porter-Duff 和常见图像混合优先使用 `BlendMode`；
- 静态大图效果可在构建、服务端或图片处理阶段生成。

阈值函数含有 `step()`，无法由单个 `ColorMatrix` 表达；业务专属的条件混合也可能超出标准 `BlendMode`。这些场景才体现 Runtime API 的表达价值。

## sRGB、预乘 alpha 与透明边缘

Android 图形管线常用预乘 alpha：合法颜色应满足 RGB 已乘以 A。AGSL 的 `main()` 返回值也应遵守这个约束；返回半透明颜色时，形状应为 `[R×A, G×A, B×A, A]`。[RuntimeShader 的预乘 alpha 说明](https://developer.android.com/reference/android/graphics/RuntimeShader)

原始输入的 RGB 也可能已经预乘。若效果的亮度判断应与透明度无关，应先恢复 straight RGB，再做亮度计算。下面的阈值示例保留原 alpha，并保证输出继续预乘；它适合图标、头像或局部图片的黑白阈值处理。

```kotlin
@RequiresApi(36)
class ThresholdFilterOwner {
    private val filter = RuntimeColorFilter(
        """
        uniform half threshold;

        half4 main(half4 color) {
            half3 straightRgb = color.a > 0.0
                ? color.rgb / color.a
                : half3(0.0);
            half luminance = dot(
                straightRgb,
                half3(0.2126, 0.7152, 0.0722)
            );
            half bw = step(threshold, luminance);
            return half4(half3(bw * color.a), color.a);
        }
        """.trimIndent(),
    )

    fun updateAndBind(paint: Paint, threshold: Float) {
        filter.setFloatUniform(
            "threshold",
            threshold.coerceIn(0f, 1f),
        )

        paint.colorFilter = null
        paint.colorFilter = filter
    }

    fun clear(paint: Paint) {
        paint.colorFilter = null
    }
}
```

`updateAndBind()` 中的清空与重绑有明确的 Android 17 源码原因。`RuntimeColorFilter` 更新 uniform 后会丢弃 native 侧缓存的 `SkColorFilter`，但 Java `ColorFilter` 包装对象地址保持不变；同一个 `Paint` 只按该地址判断是否重新安装过滤器。清空再设置会把 `Paint` 的缓存标记为失效，使下一次绘制取得带新参数的过滤器。静态参数可以在第一次绑定前设置，无需这一步。

若产品希望“越透明的像素越难通过阈值”，亮度可直接使用预乘后的 `color.rgb`。两种行为都能成立，评审时要写出预期并为 alpha 边缘建立截图基线。原稿那种输出 `half4(value, value, value, color.a)` 的写法会在 `alpha < 1` 时产生 RGB 大于 A 的结果，圆角和抗锯齿边缘容易出现亮边。

示例中的三个系数直接作用于 sRGB 编码值，得到的是适合 UI 阈值的亮度近似。需要线性光计算时，应先调用 `toLinearSrgb(straightRgb)`，做完亮度或光照运算后再按输出需求调用 `fromLinearSrgb()`。两种算法的阈值分布不同，不能只替换函数而沿用原参数。

## RuntimeXfermode：先定义 `dst` 的范围

`RuntimeXfermode` 的 `src` 是当前 draw command 生成的源颜色，`dst` 是该绘制位置在当前 render target 中已有的颜色。`dst` 随绘制顺序、裁剪、layer 和目标内容变化，同一段 AGSL 换一个 `saveLayer()` 边界就可能得到另一幅图。

下面的示例只把源图中的亮部按 SourceOver 语义叠到目标上。亮度计算使用 straight RGB，输出重新构造为预乘颜色。

```kotlin
@RequiresApi(36)
class HighlightXfermodeOwner {
    val mode = RuntimeXfermode(
        """
        uniform half strength;

        half4 main(half4 src, half4 dst) {
            half3 straightSrc = src.a > 0.0
                ? src.rgb / src.a
                : half3(0.0);
            half luminance = dot(
                straightSrc,
                half3(0.2126, 0.7152, 0.0722)
            );
            half gate = smoothstep(
                half(0.55),
                half(0.95),
                luminance
            ) * strength;
            half sourceAlpha = src.a * gate;
            half3 sourceRgb = straightSrc * sourceAlpha;

            return half4(
                sourceRgb + dst.rgb * (1.0 - sourceAlpha),
                sourceAlpha + dst.a * (1.0 - sourceAlpha)
            );
        }
        """.trimIndent(),
    )

    fun update(strength: Float) {
        mode.setFloatUniform(
            "strength",
            strength.coerceIn(0f, 1f),
        )
    }
}
```

这段公式把经过亮度门控的源颜色当作一层新的预乘 SourceOver 输入。`strength = 0` 时返回 `dst`，`strength = 1` 时只让足够亮的源像素参与合成。宿主仍要调用 `invalidate()` 或 `postInvalidateOnAnimation()` 请求下一帧；uniform setter 不负责调度 View 重绘。

若效果只应读取某个局部背景，可用有界 `saveLayer()` 明确隔离目标。下面的绘制顺序把 `base` 先画进局部 layer，再让 `highlightPaint` 的 `RuntimeXfermode` 读取这块 layer 的 `dst`。

```kotlin
val checkpoint = canvas.saveLayer(bounds, null)
canvas.drawBitmap(base, null, bounds, basePaint)
canvas.drawBitmap(highlight, null, bounds, highlightPaint)
canvas.restoreToCount(checkpoint)
```

这里的 `saveLayer()` 会引入中间渲染目标，成本至少受 `bounds` 面积和格式影响。没有 `saveLayer()` 时，`RuntimeXfermode` 读取 `dst` 也不能直接推导出“框架一定分配离屏纹理”；Skia 与图形后端可以使用 blend、framebuffer fetch、目标拷贝或其他实现。诊断结论要来自目标设备上的 render pass、GPU trace 和内存变化。

标准 multiply、screen、src-over、dst-in 等模式继续使用 `BlendMode`。自定义公式要为以下组合保留基准图：

- 源和目标都不透明；
- 源透明、目标不透明；
- 源不透明、目标透明；
- 两者都半透明；
- 抗锯齿边缘、圆角裁剪和不同 draw 顺序；
- sRGB 图片与宽色域窗口。

## 构造、uniform 更新与 native 对象

Android 17 源码把“解析/编译 AGSL”和“用当前参数生成 Skia 对象”分成不同阶段：

1. `RuntimeColorFilter` 构造函数立即调用 `getNativeInstance()`。JNI 进入 `SkRuntimeEffect::MakeForColorFilter()`，校验程序并创建 `SkRuntimeEffectBuilder`。
2. `RuntimeXfermode` 构造函数进入 `SkRuntimeEffect::MakeForBlender()` 并创建 builder；具体 `SkBlender` 在 `getNativeInstance()` 时由 `makeBlender()` 生成。
3. `setFloatUniform()`、`setIntUniform()` 和 child setter 通过 `RuntimeEffectUtils` 查找名称并校验类型、元素数和 `layout(color)`。错误会抛 `IllegalArgumentException`。
4. 更新 uniform 不会重新解析整段 AGSL。它会修改 builder 数据，并使已有 native filter/blender 实例失效。生成新的 filter/blender 仍有成本，所以“只改 uniform”也不能写成零开销。

两个类的刷新方式不同，工程封装不能共用一套假设：

| 对象 | Android 17 更新后的行为 | 应用侧处理 |
| --- | --- | --- |
| `RuntimeColorFilter` | native wrapper 丢弃缓存的 `SkColorFilter`；Java 包装地址不变 | 已绑定同一 `Paint` 时强制重绑，并做像素测试 |
| `RuntimeXfermode` | setter 调用 `invalidateXfermode()`；下次 `Paint.getNativeInstance()` 取得新的 native blender 地址 | 保持同一个 Java 对象即可，仍要触发下一次绘制 |

缓存应按“不可变源码”和“可变实例”分开：

- AGSL 文本可以是进程级常量，也可以由小型工厂按效果类型选择；
- `RuntimeColorFilter`、`RuntimeXfermode`、`Paint` 由 View、Drawable 或渲染组件持有；
- 每个可变实例只服务一个渲染 owner，页面退出后释放引用；
- 多个 item 参数不同，就为每个活跃 owner 保存独立实例，避免相互覆盖 uniform；
- 线上配置只下发开关和经过约束的数值，不接收任意 AGSL 文本。

[`Paint.getNativeInstance()`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/graphics/java/android/graphics/Paint.java) 的注释明确警告：一个线程修改 Shader、ColorFilter 或 Xfermode 时，另一个线程访问 native Paint 仍然不安全。构造放到后台线程并不能自动解决问题；发布对象后，参数更新、Paint 绑定和绘制应由同一个 owner 的绘制线程管理。

## 与 RenderEffect、RenderNode 和 Hardware Bitmap 的分工

`RuntimeColorFilter` 与 `RuntimeXfermode` 作用于使用该 `Paint` 的 draw command。`RenderEffect` 作用于 View 或 RenderNode 的输出。Android 17 的 `RenderNode.setRenderEffect()` 文档以 blur 为例说明：节点内容会先画到独立 layer，再对该 layer 处理。两种路径的成本形态不同，选型时要先确定处理对象。

`RenderEffect` 与 `RuntimeShader` 的节点级用法、失效和 GPU 验证见 [22.10 RenderEffect 与 RuntimeShader](10-rendereffect-runtime-shader-performance.md)。

| 需求 | 推荐入口 | 原因与检查项 |
| --- | --- | --- |
| 小图标灰度、色相、阈值 | 标准 `ColorFilter` 或 `RuntimeColorFilter` | 绘制范围小；检查 alpha、sRGB 语义和重绑成本 |
| 自定义源/目标混合 | `BlendMode`，表达不足时用 `RuntimeXfermode` | 先固定 draw 顺序和 `dst` 边界 |
| 整个卡片或 View 子树后处理 | `RenderEffect` | 输入是 RenderNode 内容；检查独立 layer 和链式效果 |
| 静态全屏背景 | 预生成图片 | 避免每帧覆盖整屏的像素计算 |
| 列表焦点项的短时效果 | 只处理焦点项的局部 draw | 检查滑动期间的可见实例数和失效次数 |

`RuntimeColorFilter` 本身不要求先把整个 View 画进中间纹理。`RuntimeXfermode` 暴露 `dst` 也不保证创建 layer。显式 `Canvas.saveLayer()`、View hardware layer、`RenderEffect` 和 Compose 离屏合成才提供清晰的中间目标语义。这个区分来自作者的 rendering_pipelines 中 [Software / 离屏类型](../../part2-performance/ch18-rendering-pipelines/03-android-view-software.md) 所采用的两轴判断：谁生成像素，以及像素先写到哪里。

Hardware Bitmap 只改变图片像素 backing 与 HWUI 的纹理准备路径。ColorFilter 或 Xfermode 的每像素工作仍要执行；复杂效果不会因源图是 `Bitmap.Config.HARDWARE` 而消失。Android 17 还允许 GL 驱动把部分 Hardware Bitmap 传输延后到首次绘制，不能把首次使用写成无成本。细节见 [22.17 Hardware Bitmap 与 RenderNode 缓存](17-hardware-bitmap-rendernode.md)。

RenderNode 可以复用 display list；uniform、混合目标或输入内容变化后，像素结果仍需更新。应用还要主动触发 View/Compose 绘制失效，否则新的参数没有机会进入显示帧。

## 硬件路径、软件路径与离屏成本

AGSL 描述的是 Skia runtime effect，API 文档没有把 `RuntimeColorFilter` 或 `RuntimeXfermode` 限定为 GPU 专用。Android 17 的 `BaseCanvas` 会在软件 Canvas 上拒绝作为 `Paint.shader` 的 `RuntimeShader`，却没有对这两个新对象设置同样的 Java guard。硬件加速开关因此会改变执行单元和性能形态，截图与性能测试都应覆盖两种 Canvas。

在硬件加速窗口中，成本通常包括：

- draw 覆盖的像素数量与 overdraw；
- 每像素算术、分支和 child effect 调用；
- 源纹理读取、目标混合和 render target 写入；
- `saveLayer()`、`RenderEffect` 或合成策略带来的中间目标；
- GPU 后端、驱动、target 格式、MSAA、tile 大小与热状态。

“面积扩大四倍，耗时就扩大四倍”只能作为待测假设。tile-based GPU、缓存命中、固定提交成本、fragment 饱和度和目标切换都会改变曲线。有效测试应固定内容、分辨率、窗口色彩模式、刷新率与设备温度，分别测小区域、半屏和全屏。

软件 Canvas 要观察 CPU 栅格化时间、Bitmap 内存和后续宿主上传。`LAYER_TYPE_SOFTWARE` 还会把 View 子树先画到软件 Bitmap，再由宿主 HWUI 采样；此时 CPU 处理与宿主 RenderThread 都存在。把软件渲染和离屏渲染混成一个结论，会漏掉一半成本。

## 用证据定位慢帧

FrameTimeline 用于回答帧有没有错过 deadline，无法单独证明 fragment shader 是瓶颈。建议使用同一设备、同一脚本做四组 A/B：

1. 关闭效果；
2. 开启标准 `ColorFilter` 或 `BlendMode`；
3. 开启 Runtime 效果；
4. 开启 Runtime 效果并扩大作用区域。

每组至少保留这些数据：

| 证据 | 能回答的问题 | 不能独自回答的问题 |
| --- | --- | --- |
| Macrobenchmark `frameOverrunMs`、Perfetto FrameTimeline | 哪些帧超过各自 deadline | 超期由哪条 GPU 指令造成 |
| UI Thread 与 RenderThread slices | 重绘、display list、提交是否变长 | GPU 完成时间和 shader 热点 |
| GPU completion / render stages | GPU 工作是否延后 App SurfaceFrame | 具体算术或纹理瓶颈 |
| AGI、厂商 profiler | render pass、fragment、texture、bandwidth 变化 | 线上全部设备的固定增量 |
| `dumpsys meminfo`、dmabuf/GPU 工具 | Graphics/GL/总 PSS 与中间资源趋势 | 每个驱动分类都具备相同名称 |
| 截图或 PixelCopy 回归 | 颜色、alpha、裁剪与 draw 顺序是否正确 | 性能是否达标 |

图形内存分类受 memtrack、驱动和共享归属影响。旧资料中的 Gfx dev、GL mtrack、EGL mtrack 不能当作所有 Android 17 设备都有的固定三栏。记录设备提供的分类、总 PSS、dmabuf/GPU memory 与页面退出后的回落，再与效果开关对照。

60 Hz 与 120 Hz 要分开跑。刷新率升高会缩短每帧 deadline，也会改变动画更新次数；只用“16.67 ms”判断自适应刷新率设备会误分帧。刷新率和 FrameTimeline 边界见 [22.18 自适应刷新率实践](18-adaptive-refresh-rate-practice.md)。

## kernel 锚点在哪里

AGSL 解析、SkRuntimeEffect builder、颜色过滤和 blender 都位于 framework/Skia 用户空间，kernel 不理解 threshold、sRGB 或 `src`/`dst` 公式。`android17-6.18-2026-06_r6` 的观察边界出现在 GPU 提交后的 dma-fence、sync_file、dma-buf 共享和驱动调度。

当 trace 中出现 GPU completion 或 fence wait，结论只能写成“某项 GPU/consumer 工作尚未完成”。还要用 render pass、buffer id、调用栈和 A/B 场景确认等待来自 Runtime 效果、中间 layer、窗口 buffer，或同进程的其他 GPU 工作。[2.16 Sync Fence](../../part1-fundamentals/ch02-rendering/16-sync-fence.md) 解释了 acquire、present 和 release 的不同所有权边界。

## 兼容与降级

所有构造和方法调用都要放在 API 36 guard 内。Android 13—15 虽有 `RuntimeShader`，也不能直接调用这两个 API。降级方案应按视觉语义选择：

| API 36+ 效果 | 低版本候选 |
| --- | --- |
| 灰度、sepia、线性色彩调整 | `ColorMatrixColorFilter` |
| 标准混合 | `BlendMode` / `PorterDuffXfermode` |
| 小范围坐标型自定义效果 | API 33+ `RuntimeShader` |
| 非线性阈值且输入静态 | 预处理 Bitmap 或预生成资源 |
| 大范围静态氛围图 | WebP/AVIF/Bitmap 素材 |

设备开关不宜只改 `strength`。缩小区域、降低更新频率、减少同时启用的 item、换静态素材或关闭效果，通常更容易控制 deadline。远程参数要有数值范围和默认值；AGSL 源码随服务端下发会把编译错误、视觉安全和驱动差异带到线上。

## 测试与 Compose 接入

构造测试应在 API 36+ 设备或模拟器运行。无效 AGSL、缺少 uniform、类型或数组长度不匹配、`layout(color)` 使用错误都要断言 `IllegalArgumentException`。JVM local test 无法替代 Skia/JNI 编译路径。

像素测试至少覆盖：

- alpha 为 0、接近 0、0.5 和 1.0；
- 黑、白、三原色与阈值两侧的颜色；
- 软件 Bitmap Canvas 与硬件加速 View；
- sRGB 与宽色域窗口；
- `RuntimeColorFilter` 绑定前更新、绑定后更新；
- `RuntimeXfermode` 在有无 `saveLayer()` 时的 `dst` 差异。

硬件 View 的截图可使用 instrumentation 截图或 `PixelCopy`，再用容差比较像素。容差应按设备/后端分级，alpha 规则和结构边缘不能只靠整图平均误差。

Compose 有两条不同路径：

- `graphicsLayer { renderEffect = ... }` 仍属于 RenderEffect/RenderNode 后处理；
- Android 平台上的 `drawIntoCanvas` 可取得 native Canvas，并用 `android.graphics.Paint` 进入 draw-command 语义。

`drawWithCache` 适合保存 Paint、AGSL 文本对应的 Runtime 对象和静态几何。动画参数变化后仍要更新对应 owner、请求 draw，并遵守前文的 `RuntimeColorFilter` 重绑边界。AndroidX 对 Paint 和 RenderEffect 的包装会随版本变化，升级时用编译测试和截图确认自定义 Xfermode 没有在转换过程中丢失。

## 小结

`RuntimeColorFilter` 处理一次绘制产生的颜色，`RuntimeXfermode` 决定这次源颜色怎样与当前目标合成。两者从 Android 16 / API 36 提供，Android 17 的源码仍通过 SkRuntimeEffect builder 接入 Skia。

上线前应守住五条边界：输出保持预乘 alpha；标准 ColorFilter/BlendMode 能覆盖时沿用标准 API；可变实例按渲染 owner 隔离；`RuntimeColorFilter` 已绑定后的 uniform 更新要重绑并回归；`dst` 读取与离屏 allocation 分开取证。完成这些工作，再用 FrameTimeline、RenderThread、GPU 工具、图形内存和像素截图共同验收。

## Android 17 源码索引

- [`RuntimeColorFilter.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/graphics/java/android/graphics/RuntimeColorFilter.java) 与 [`RuntimeXfermode.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/graphics/java/android/graphics/RuntimeXfermode.java)：公开 API、sRGB 输入、uniform/child setter 与 blender 失效。
- [`ColorFilter.h`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/libs/hwui/ColorFilter.h) 与 [`ColorFilter.cpp`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/libs/hwui/jni/ColorFilter.cpp)：`MakeForColorFilter()`、builder、缓存丢弃和 `makeColorFilter()`。
- [`RuntimeXfermode.cpp`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/libs/hwui/jni/RuntimeXfermode.cpp) 与 [`RuntimeEffectUtils.cpp`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/libs/hwui/jni/RuntimeEffectUtils.cpp)：`MakeForBlender()`、`makeBlender()` 与参数校验。
- [`Paint.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/graphics/java/android/graphics/Paint.java) 与 [`Paint.cpp`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/libs/hwui/jni/Paint.cpp)：Java/native Paint 的 filter、blender 缓存和线程安全边界。
- [`BaseCanvas.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/graphics/java/android/graphics/BaseCanvas.java)：软件 Canvas 的硬件特性 guard。
- [`dma-fence.c`](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/drivers/dma-buf/dma-fence.c) 与 [`sync_file.c`](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/drivers/dma-buf/sync_file.c)：kernel 侧 GPU/consumer 完成与 fence fd 边界。
