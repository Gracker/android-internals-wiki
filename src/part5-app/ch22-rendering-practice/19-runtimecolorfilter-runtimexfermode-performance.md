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

Android 16 把 AGSL 从 `RuntimeShader` 扩到 `RuntimeColorFilter` 和 `RuntimeXfermode`。这两个 API 解决的是更细的绘制挂点：`RuntimeColorFilter` 改写单次 draw 的颜色输出，`RuntimeXfermode` 改写源像素和目标像素的混合结果。`RenderEffect + RuntimeShader` 适合处理一整块 RenderNode 内容；这两个新 API 更适合挂在 `Paint` 上，随某一次 `Canvas` 绘制生效。[已验证: 官方文档, developer.android.com/about/versions/16/features]

性能判断要从 draw call 开始，而不是从“用了 GPU shader”开始。作用区域、采样次数、目标像素数量、是否触发离屏层，决定了它是轻量颜色处理，还是每帧纹理带宽问题。GPU 渲染基础详见 2.10 节，标准 View 管线详见 18.2 节，`RenderEffect` 与 `RuntimeShader` 的整节点后处理详见 22.10 节。

## API 边界

`RuntimeColorFilter` 的 AGSL 入口只接收当前输入颜色。AOSP 类注释给出的函数签名是 `vec4 main(half4 color)`；官方参考文档也把它描述为按用户提供的 AGSL 函数计算每个像素颜色的 `ColorFilter`。它适合做 threshold、sepia、hue / saturation、灰度、品牌 tint、状态色映射这类不需要读取邻域像素的处理。[已验证: AOSP master, frameworks/base/graphics/java/android/graphics/RuntimeColorFilter.java][已验证: 官方文档, developer.android.com/reference/android/graphics/RuntimeColorFilter]

`RuntimeXfermode` 的入口接收源颜色和目标颜色。AOSP `RuntimeXfermode` 注释给出的函数签名是 `vec4 main(half4 src, half4 dst)`，并说明输入和输出按 sRGB 解释。它适合自定义混合，例如只在亮部叠加、按蒙版权重混合两层颜色、实现标准 `BlendMode` 覆盖不到的业务效果。[已验证: AOSP master, frameworks/base/graphics/java/android/graphics/RuntimeXfermode.java][已验证: 官方文档, developer.android.com/reference/android/graphics/RuntimeXfermode]

三类 AGSL 能力的区别可以按输入对象拆开：

| API | 最低版本 | 挂载位置 | AGSL 输入 | 适合场景 | 主要风险 |
| --- | --- | --- | --- | --- | --- |
| `RuntimeShader` | Android 13 / API 33 | `Shader` 或 `RenderEffect` | 坐标、uniform、输入 shader | 自定义填充、整节点像素处理 | 多次 `eval()`、链式 effect、离屏层 |
| `RuntimeColorFilter` | Android 16 / API 36 | `Paint.colorFilter` | 当前颜色 | 灰度、threshold、色相调整、状态色映射 | 大面积每帧处理、对象反复创建 |
| `RuntimeXfermode` | Android 16 / API 36 | `Paint.xfermode` | 源颜色、目标颜色 | 自定义混合、局部叠加、特殊遮罩 | 目标读取、透明区域、离屏语义差异 |

这个表也决定了选型顺序：标准 `BlendMode`、`ColorMatrixColorFilter`、资源预处理能完成的效果，不要先上 AGSL；需要表达业务专属公式且作用区域可控时，再使用 Runtime API。

## 适合实时处理的效果

`RuntimeColorFilter` 最稳的目标是“一入一出”的颜色变换。输入是当前像素颜色，输出仍是一个颜色，中间不需要读纹理周围像素，也不需要把整块 View 内容先存成中间纹理。常见例子包括黑白图标着色、图片灰度、色温调整、暗色蒙版、阈值化。

下面的示例只做一次颜色计算，适合放在静态图标、局部图片或小范围状态效果上。读代码时关注两点：`RuntimeColorFilter` 对象被缓存，帧内只更新 uniform。

```kotlin
@RequiresApi(Build.VERSION_CODES.BAKLAVA)
class ThresholdColorFilter {
    private val filter = RuntimeColorFilter(
        """
        uniform float threshold;

        half4 main(half4 color) {
            float luminance = dot(float3(color.rgb), float3(0.2126, 0.7152, 0.0722));
            float value = step(threshold, luminance);
            return half4(value, value, value, color.a);
        }
        """.trimIndent(),
    )

    fun applyTo(paint: Paint, threshold: Float) {
        filter.setFloatUniform("threshold", threshold.coerceIn(0f, 1f))
        paint.colorFilter = filter
    }

    fun clear(paint: Paint) {
        paint.colorFilter = null
    }
}
```

这段代码不在 `onDraw()` 里创建 AGSL 对象，只更新一个 `float` uniform。进入工程后，还要按目标区域加开关：列表滑动中大图每帧重绘、全屏背景每帧变色、多个叠加层同时使用 ColorFilter，都要放进低端机灰度实验。

`RuntimeXfermode` 要更谨慎。混合函数读取 `src` 和 `dst`，这使它天然依赖目标已有内容。标准 multiply、screen、src-over、dst-in 一类操作优先使用平台 `BlendMode` 或已有 `Xfermode` 语义；AGSL 只用于标准混合无法表达的公式。

这个示例表达“只把源像素亮部叠到目标上”。代码保持一次混合计算，不做纹理邻域采样。

```kotlin
@RequiresApi(Build.VERSION_CODES.BAKLAVA)
class HighlightXfermode {
    private val mode = RuntimeXfermode(
        """
        uniform float strength;

        half4 main(half4 src, half4 dst) {
            float luminance = dot(float3(src.rgb), float3(0.2126, 0.7152, 0.0722));
            half amount = half(smoothstep(0.55, 0.95, luminance) * strength);
            half3 mixed = mix(dst.rgb, max(dst.rgb, src.rgb), amount);
            return half4(mixed, max(dst.a, src.a));
        }
        """.trimIndent(),
    )

    fun applyTo(paint: Paint, strength: Float) {
        mode.setFloatUniform("strength", strength.coerceIn(0f, 1f))
        paint.xfermode = mode
    }

    fun clear(paint: Paint) {
        paint.xfermode = null
    }
}
```

混合类效果必须截图回归。透明边界、宽色域图片、半透明背景、抗锯齿边缘和硬件加速开关都会影响结果。PorterDuff 语义和传统混合模式的机制不在这里重写，必要时只对照 2.10 节和 Android `Paint` / `BlendMode` 文档。

## 编译、uniform 与缓存

AGSL 字符串解析和底层 native 对象创建不要放在高频绘制路径里。`RuntimeColorFilter` 和 `RuntimeXfermode` 都提供多种 `setFloatUniform()`、`setColorUniform()`、`setInputShader()` 方法，异常路径也很明确：uniform 名称不存在、类型不匹配、颜色 uniform 没按要求声明时会抛 `IllegalArgumentException`。这类错误应该在开发期通过测试暴露，不要让线上动态字符串临时拼接 shader。[已验证: AOSP master, frameworks/base/graphics/java/android/graphics/RuntimeColorFilter.java][已验证: AOSP master, frameworks/base/graphics/java/android/graphics/RuntimeXfermode.java]

缓存策略按生命周期拆：

- **进程级模板**：AGSL 源码固定、只靠 uniform 变化的效果，可以用小型工厂按字符串和参数类型缓存对象模板，但不要把所有效果在启动阶段全部创建。
- **页面级实例**：同一个页面反复使用的 `RuntimeColorFilter`、`RuntimeXfermode` 放在 View、Drawable 或渲染组件持有者里，页面销毁时释放引用。
- **帧内更新**：动画帧只更新 `float`、`float2`、颜色 uniform 或少量 input shader，不创建新 `Paint`、新 Runtime 对象或新 Bitmap。
- **远程配置**：线上只下发启停、强度、半径、阈值、目标页面，不下发任意 AGSL 源码。动态 shader 编译失败会把视觉问题变成线上稳定性问题。

参考书里的速度优化思路可以迁移到这里：减少当前帧要执行的工作、提高缓存命中率、避免主线程和 RenderThread 在关键帧等待额外初始化。[结构参考: Clippings/Android 性能优化 - 原理：重新认识应用的速度优化.md][结构参考: Clippings/Android 性能优化 - 任务调度优化：线程+CPU，提升任务调度优先级.md]

## 与 RenderEffect 和缓存的分工

`RuntimeColorFilter` / `RuntimeXfermode` 直接跟某次 `Paint` 绘制绑定。`RenderEffect` 绑定的是 View 或 RenderNode 的绘制结果，常见路径是把节点内容先画成中间层再处理。两者都能写 AGSL，但性能形态不同：前者更像 draw call 局部处理，后者更像节点后处理。`RenderEffect` 的离屏层、链式效果和 FrameTimeline 验证详见 22.10 节。

选型可以用这张表落到工程决策：

| 目标 | 优先方案 | 不推荐方案 | 验证点 |
| --- | --- | --- | --- |
| 图标或小图片灰度、tint、threshold | `RuntimeColorFilter` 或已有 `ColorFilter` | 把整块 View 包成 `RenderEffect` | draw 区域、RenderThread 耗时、截图一致性 |
| 自定义源/目标混合 | 标准 `BlendMode` 优先；不足时用 `RuntimeXfermode` | 用多层 View 叠加模拟混合 | 透明边界、目标背景变化、过度绘制 |
| 全屏毛玻璃、整卡片后处理 | `RenderEffect` / 预生成素材 | 每个子元素分别挂 ColorFilter / Xfermode | 离屏层大小、GPU memory、FrameTimeline |
| 静态品牌氛围图 | 预处理 Bitmap、WebP、服务端素材 | 每次进入页面实时 AGSL 处理 | 首帧、纹理上传、graphics memory |
| 列表 item 动态效果 | 只对焦点 item 开启，其他使用静态资源 | 所有 item 同时启用 Runtime API | 滑动 P90 / P99、GPU busy、对象分配 |

Hardware Bitmap 与 RenderNode 缓存也不要和 Runtime API 混用出错误预期。Hardware Bitmap 解决的是图片像素位置和首次 texture upload，不能让一个复杂 color filter 变成零成本；RenderNode 缓存能复用绘制命令和部分层结果，但内容、uniform 或混合目标频繁变化时，GPU 仍要重新计算。相关边界详见 22.17 节。

## GPU、带宽与内存风险

ColorFilter 类效果通常不需要显式离屏，但它仍会让目标像素执行额外 fragment 计算。Xfermode 类效果会读取目标颜色，遇到复杂透明区域、多层叠加或 saveLayer 组合时，可能引入离屏语义。排查时不要只看 UI Thread；很多问题会出现在 RenderThread、GPU completion 或 graphics memory 上。

图形内存统计要拆开看。参考书把 graphic 相关内存分成 Gfx dev、GL mtrack、EGL mtrack 三类，提醒应用不要只盯 Java heap。落到 AGSL 效果，纹理、shader program、中间 layer、窗口 Surface 都可能把成本放到 Java heap 之外。[结构参考: Clippings/Android 性能优化 - 原理：掌握 App 运行时的内存模型.md]

本地验证按四组指标跑：

- **帧时间**：Perfetto FrameTimeline 里看目标交互前后的 expected / actual timeline，确认慢帧是否集中在启用效果的窗口。
- **RenderThread**：观察 `DrawFrame`、`syncFrameState`、GPU command submit 附近是否变长；UI Thread 很短不代表绘制便宜。
- **GPU 与图形内存**：用 AGI / GPU Inspector 或厂商工具看 fragment、texture、render target、GPU memory 水位。全屏效果至少按 60 Hz 和 120 Hz 两种刷新率测。
- **区域控制**：同一效果分别跑 100 × 100、半屏、全屏区域。耗时随像素数接近线性增长时，后续优化要先缩小作用区域。

Bitmap 阈值治理的思路也适用于实时效果：先定义页面允许的最大处理面积和设备档位，再按阈值关闭或替换效果。参考书里对超大 Bitmap 的治理使用屏幕尺寸、像素格式和低端机降级口径；AGSL 效果可以用同样方式建立“区域面积 × 刷新率 × 设备档位”的开关表。[结构参考: Clippings/Android 性能优化 - Native 内存优化（下）：Bitmap 的内存占用优化.md]

## 兼容性与降级

`RuntimeColorFilter` 和 `RuntimeXfermode` 从 Android 16 才能作为公开 API 使用。工程封装要把 API 36 以下设备挡在调用点外，不能只依赖资源或反射兜底。Android 13 到 Android 15 可以继续使用 `RuntimeShader`、`RenderEffect`、`ColorMatrixColorFilter`、`BlendModeColorFilter` 或预处理图片；Android 12 及以下按已有 RenderEffect / Bitmap 策略降级。

一个可发布的封装要保留三层开关：

- **版本开关**：`Build.VERSION.SDK_INT >= 36` 才创建 `RuntimeColorFilter` 和 `RuntimeXfermode`。
- **设备开关**：按 GPU、内存档位、刷新率、低电量模式和线上慢帧指标启停。
- **场景开关**：列表、首屏、转场、后台窗口、截图分享等场景独立配置，不做全应用统一开关。

低端机降级不要只改 shader 强度。更有效的路径通常是缩小区域、降低更新频率、改用静态资源、减少叠加层，或者直接关闭效果。用户很少能感知一个 0.12 强度的扫描光少了一点，但能感知列表滑动变卡、首帧变慢、截图边缘异常。

## 扩展：测试与 Compose 接入

AGSL 测试至少有两层。单元层面可以把 shader 字符串、uniform 名称、参数范围和版本封装跑完，避免类型不匹配到线上才抛异常；视觉层面用截图回归覆盖浅色/深色主题、透明背景、宽色域图片、RTL、字体缩放和高刷新率设备。颜色类效果尤其要补 alpha 边缘截图，因为小误差会在圆角、阴影、半透明蒙版上放大。

`RuntimeXfermode` 与传统 PorterDuff 的对照要按语义写，不按名字类比。`src`、`dst` 的定义和 draw 顺序绑定，同一段 AGSL 换到不同 Canvas 状态下可能得到不同结果。迁移前先用标准 `BlendMode` 复现旧效果，再只把标准 API 表达不了的部分交给 `RuntimeXfermode`。[待补充]

Compose 接入路径要分两类。使用 `graphicsLayer { renderEffect = ... }` 的场景仍走 RenderEffect 管线，适合整节点后处理；使用 `drawWithCache` / `drawIntoCanvas` 持有 Android `Paint` 的场景，才更接近 `RuntimeColorFilter` 和 `RuntimeXfermode` 的 draw call 语义。Compose 版本、Android 版本和底层 Canvas 路径需要单独截图回归，本节不把它写成通用结论。[待验证]

## 小结

Android 16 的 `RuntimeColorFilter` 和 `RuntimeXfermode` 让 AGSL 进入更小的绘制挂点。用得稳的前提是：对象复用，帧内只改少量 uniform；效果限制在局部 draw call；标准 API 能覆盖的混合和调色不改用 AGSL；上线前用 FrameTimeline、RenderThread、GPU memory 和截图回归同时验收。它们补齐的是应用自定义颜色和混合的表达能力，不替代 RenderEffect、Hardware Bitmap、RenderNode 缓存和基础渲染优化。
