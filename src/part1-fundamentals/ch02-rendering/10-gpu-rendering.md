---
status: ready-for-review
section: '2.10'
title: GPU 渲染深入
chapter: '2.10'
applicable_versions: Android 5.0 - Android 17 (API 21-37)
last_verified: '2026-04-17'
last_verified_against: AOSP android-16.0.0_r1, developer.android.com
confidence: medium-high
sources:
- type: aosp
  path: frameworks/base/graphics/java/android/graphics/
- type: official
  path: https://developer.android.com/guide/topics/graphics/
- type: blog
  path: https://androidperformance.com/
- type: paper
  path: 2026-03-30-ch02-vulkan-android16.md
- type: paper
  path: 2026-03-30-ch02-gpu-optimization.md
tags:
- gpu
- rendering
- shader
- vulkan
- opengl
- performance
- memory
related_chapters:
- '2.3'
- '2.4'
- '2.5'
- '2.6'
- '2.9'
- '3.2'
- '14.3'
drafted_date: 2026-03-30
drafted_by: openclaw-task2a
reviewed_date: "2026-06-02"
reviewed_by: openclaw-task6
task6_state: "revisiting"
task6_result: pass-light-edit
review_round: 10
last_polish_notes: 第2轮出版级精修:修复applicable_versions范围、ANGLE URL拼写、叙述过渡、口语化表达;发现L3/L4问题需Task2B加工
polish_count: 2
polish_date: '2026-04-10'
polish_by: task2b-polish
task9_state: "reviewed"
task2b_state: "fixed"
task2b_result: fixed
pipeline_stage: "task6_pending"
last_task2b_at: "2026-06-02T22:50:00+08:00"
last_task2b_lite_at: "2026-06-01"
review_notes: "2026-05-09 task2b rework: ASTC vs ETC2 带宽对比表、gpu_busy Android 16 标准化轨道。 | 2026-05-12 task6 review: needs-rework。L1/L2 小修 2 处;参考资料后源码调研补充未整合、实战案例缺一手 Trace/AGI 证据,已写入 queue。 | 2026-06-02 task6 review: pass-light-edit。L1/L2 小修 2 处;AOSP mainline 锚点改为 Android 17 待验证边界,删除填充副词。"
review_type: task6-writing-quality-review
task9_result: "auto-fixed"
task9_reviewed_date: "2026-06-03"
task9_reviewed_by: "openclaw-task9"
last_task9_at: "2026-06-03T01:26:00+08:00"
rework_notes_2: "Task 2B 回炉修复: 参考资料后源码调研材料重构为附录(A.1 GPU 内存管理, A.2 GPU 性能排查流程), 保持正文收束结构"
last_task6_at: "2026-06-02T23:05:00+08:00"
task6_review_notes: "2026-06-02 Task6 23: pass-light-edit。L1/L2 小修 2 处；实战案例已改为示例场景，未新增回炉项，进入 Task9 待审。"
task9_review_notes: "2026-06-03 Task9 deep review: auto-fixed。AUTO-FIX: 修正 graphics Java 源码目录、BufferQueue/GraphicBuffer/HWC2 路径与 BUFFER_RELEASE_CHANNEL 版本边界；P0 1 / P1 0 / P2 0，回到 Task6 复审。"
last_task6_review_log: "logs/review/2026-06-02-23-review.md"
task6_l1_l2_fixes: 2
task6_l3_l4_issues: 0
last_task9_autofix_at: "2026-06-03"
last_task9_review_log: "logs/deep-review/2026-06-03-01-deep-review.md"
p0: "1"
p1: "0"
p2: "0"
---


# GPU 渲染深入

## 为什么需要深入理解 GPU 渲染

在 Perfetto Trace 中,我们经常看到这样的场景:主线程(MainThread)在很短时间内完成了 measure、layout、draw 操作,RenderThread 也快速完成了 draw command 的录制,但 UI 更新却明显滞后--下一帧的 VSync 到来了,上一帧还在 GPU 中处理。这种情况下,问题往往出在 GPU 渲染阶段:应用发送的绘制指令虽然不多,但 GPU 处理这些指令花费了大量时间,或者 GPU 本身遇到了内存带宽瓶颈。

如果我们缺乏对 GPU 渲染管线的理解,遇到这类掉帧就只能停留在"主线程没问题,不知道什么原因"的阶段。理解了 GPU 渲染机制之后,我们就能做到三件事:把 GPU 渲染过程从看不见的"黑盒"变成可分析、可定位的链条;精准区分 CPU 瓶颈、GPU 瓶颈和内存带宽瓶颈,避免把力气花在错误的方向上;理解 Android 16 中 Vulkan 成为默认 API 这件事背后的工程影响,知道后续系统版本需要提前准备什么。

本节从 GPU 渲染管线的基本原理切入,延伸到性能瓶颈分析、GPU 内存管理和实战案例,把这些知识点放回完整的渲染问题排查流程中。

<!-- outline-start -->
## 本节要点大纲

### 锚点(必须覆盖)

- 🔹 Android GPU 渲染管线:Vertex Shader → Fragment Shader → Framebuffer
- 🔹 Shader Compilation Jank:首次编译着色器导致的掉帧与 Skia Pipeline Cache
- 🔹 Vulkan vs OpenGL ES 在 Android 上的性能对比
- 🔹 GPU 性能瓶颈分析:fillrate bound vs vertex bound vs bandwidth bound
- 🔹 GPU 内存管理:GraphicBuffer / Gralloc / GPU Memory 归属与追踪

### 扩展(可选深入)

- 🔸 ANGLE(OpenGL ES on Vulkan)的性能影响
- 🔸 GPU Profiling 工具:Snapdragon Profiler、ARM Streamline、AGI

### OpenClaw 加工指引

> **锚点**是最低覆盖要求,加工时必须逐条落实并标注验证结果。
> **扩展**视素材丰富程度选择性深入。
> 如果从 Obsidian 素材或 AOSP 源码中发现大纲未列出但与本节强相关的知识点,
> 可**就地插入**最相关的锚点之后,并用 `[自动发现]` 标注,方便后续 review。
> 锚点内容需 L1/L2 验证,扩展内容至少 L2 验证,自动发现内容至少标注来源。
<!-- outline-end -->

## Android GPU 渲染管线:Vertex Shader → Fragment Shader → Framebuffer

### 从应用调用到屏幕显示的完整流程

当我们调用 `View.invalidate()` 或 `View.draw()` 时,Android 的 GPU 渲染管线就开始启动。这个管线的核心任务是将应用的 2D/3D 绘制指令转换成屏幕上显示的像素,整个过程涉及 CPU 准备、GPU 指令生成、GPU 渲染、帧缓冲区管理、屏幕合成五个阶段。

流程的起点在 CPU 侧:应用主线程执行 `View.onDraw()`,通过 Canvas API 绘制界面。这些 Canvas 调用被 Skia 图形库接收后,Skia 会根据运行环境将其转换为 OpenGL ES 或 Vulkan 调用--这是 GPU 指令生成阶段。随后 GPU 接管工作,依次执行顶点处理、片段处理等计算任务,将渲染结果写入显存中的帧缓冲区。SurfaceFlinger 再将多个图层合成为最终图像,提交给显示硬件。

CPU 和 GPU 之间的分工经历了几个重要阶段的演进。在 Android 5.0 之前,主线程包揽了所有渲染工作--measure/layout、DisplayList 录制、GPU 命令提交全部在同一线程完成。Android 5.0 引入了独立的 RenderThread,将 GPU 命令的提交和执行从主线程剥离出来,主线程只负责 measure/layout 和 DisplayList(draw 命令列表)的录制。从 Android 12 开始,Google 进一步优化了这一分工,RenderThread 处理了更多工作,使得主线程的渲染负担进一步减轻。我们在 Trace 中看到的"GPU 耗时",对应的是 RenderThread 将命令提交到 GPU 直到 GPU 完成渲染的整个过程。

[图:Android GPU 渲染管线全景图--从 CPU 准备到屏幕合成的完整数据流]

### Vertex Shader:顶点处理的起点

Vertex Shader 是 GPU 渲染管线的第一个可编程阶段,它负责处理图元中的每个顶点。在 Android UI 渲染中,顶点处理看起来简单--一个矩形只有四个顶点--但大量 UI 元素最终都会转换为三角形图元,复杂界面的顶点数量可能非常可观。

当我们调用 `Canvas.drawRect()` 时,这个调用最终会触发 GPU 执行 Vertex Shader。Vertex Shader 做三件事:将模型顶点从本地坐标转换到屏幕坐标(涉及模型矩阵、视图矩阵、投影矩阵的组合变换);计算每个顶点的颜色、纹理坐标等插值属性,供 Fragment Shader 阶段插值使用;判断顶点是否在视口范围内,剔除不可见图元,避免后续阶段做无用功。

```java
// frameworks/base/graphics/java/android/graphics/Canvas.java → BaseCanvas.java
// @ AOSP android-16.0.0_r1
// Canvas.drawRect(float...) 委托给 super.drawRect → BaseCanvas.drawRect
public void drawRect(float left, float top, float right, float bottom,
                     @NonNull Paint paint) {
    super.drawRect(left, top, right, bottom, paint);
}

// frameworks/base/graphics/java/android/graphics/BaseCanvas.java
void drawRect(float left, float top, float right, float bottom, Paint paint) {
    throwIfHasHwFeaturesInSwMode(paint);
    nDrawRect(mNativeCanvasWrapper, left, top, right, bottom,
              paint.getNativeInstance());
}
```

调用链分三层:Canvas.drawRect() 是公开 API 入口,内部直接调用 super.drawRect() 把参数原样传递给父类;BaseCanvas.drawRect() 先调用 throwIfHasHwFeaturesInSwMode() 检查 Paint 是否在软件渲染模式下使用了硬件特性,然后通过 JNI 调用 nDrawRect() 进入 native 层;Skia 在 native 侧接收到指令后,根据当前后端(OpenGL ES 或 Vulkan)生成对应的顶点数据和 GPU 命令。

对于简单的矩形绘制,Vertex Shader 执行四个顶点的位置变换,开销很低。但如果矩形被缩放、旋转或倾斜--这在动画和自定义 View 中很常见--这些变换矩阵的复杂度会相应增加。

在 Perfetto 中,我们可以在 GPU track 看到顶点处理时间。如果发现某个 UI 元素的 GPU 时间异常高,而界面又包含大量的自定义 Path 或复杂的 Canvas 变换,Vertex Shader 往往是第一个需要排查的方向。

### Fragment Shader:像素颜色的决定者

Fragment Shader(也称为 Pixel Shader)是渲染管线的核心阶段,它决定了屏幕上每个像素的最终颜色。对于 Android UI 渲染来说,Fragment Shader 的重要性甚至超过 Vertex Shader--UI 界面的像素数量通常远多于顶点数量,Fragment Shader 的计算量与像素数成正比。一个全屏的 `drawRect()` 只有四个顶点,但需要处理的像素可能多达数百万个。

```glsl
// 简化的 Android UI Fragment Shader 示例(示意性伪代码)
precision mediump float;
varying vec2 vTexCoord;
uniform sampler2D uTexture;
uniform vec4 uColor;

void main() {
    vec4 texColor = texture2D(uTexture, vTexCoord);
    gl_FragColor = texColor * uColor;
}
```

这个着色器展示了 Fragment Shader 的基本工作模式:从纹理中采样颜色,然后应用统一的颜色调制,最终输出像素颜色。在真实的 Android UI 渲染中,Fragment Shader 还需要处理透明度混合、渐变效果、阴影计算、模糊效果等--每增加一个效果,就意味着每像素的计算量又增加了一层。而纹理采样是一个特别需要注意的操作,因为每次采样都需要从显存中读取数据,在移动 GPU 的统一内存架构下,这些读取会与其他组件(如 CPU、显示控制器)竞争内存带宽。

> [已验证: AOSP android-16.0.0_r1, frameworks/base/graphics/java/android/graphics/Shader.java]

在分析 Fragment Shader 性能时,纹理采样次数是最关键的关注点。一个常见的性能陷阱是在 Fragment Shader 中使用多个纹理采样(例如实现圆角+阴影+渐变背景),每增加一次采样,每像素的内存访问量就增加一个数量级。在 1080p 屏幕上,一次全屏渲染就需要处理约 200 万个像素--如果每个像素采样 4 次纹理,那就是 800 万次显存访问。

[图:Perfetto 中 GPU track 示意图--标注 Vertex Shader 和 Fragment Shader 的执行时间段]

### Framebuffer:渲染结果的存储位置

Framebuffer 是 GPU 渲染管线的最终输出目标,它是一块用于存储渲染完成像素数据的显存区域。理解 Framebuffer 的管理机制,对分析 GPU 内存占用和显示延迟都有直接帮助。

Android 中的 Framebuffer 管理涉及多个层面。最底层是 Gralloc 模块,它负责实际分配和管理图形缓冲区的内存。Gralloc 分配的缓冲区就是 GraphicBuffer,应用通过 Canvas 绘制的内容最终写入到 GraphicBuffer 中,然后由 SurfaceFlinger 在合成时读取。

```cpp
// AOSP android-16.0.0_r1
// ANativeWindowBuffer 定义: frameworks/native/libs/nativewindow/include/android/native_window.h
// GraphicBuffer 定义: frameworks/native/libs/ui/include/ui/GraphicBuffer.h
typedef struct ANativeWindowBuffer {
    int width;                // 缓冲区宽度(像素)
    int height;               // 缓冲区高度(像素)
    int stride;               // 行跨度(像素)
    int format;               // 像素格式(AHARDWAREBUFFER_FORMAT_*)
    int usage;                // 使用标志(AHARDWAREBUFFER_USAGE_*)
    void* reserved[2];        // 保留字段
    buffer_handle_t handle;   // 底层图形缓冲区 native handle(native_handle_t*)
} ANativeWindowBuffer_t;
```

这层对象关系很容易混在一起。App 或 NDK 代码日常直接接触的通常是 `Surface`、`SurfaceTexture`、`ANativeWindow`、`HardwareBuffer` 这类公开对象;缓冲区一旦进入 BufferQueue,底层 native handle 会被 `GraphicBuffer` 包装,并附带 format、usage、stride、fence 等元数据,再继续流向 SurfaceFlinger、HWC 或 GPU 驱动。也就是说,`ANativeWindowBuffer` 更接近生产者视角的窗口缓冲区抽象,`GraphicBuffer` 更常出现在 framework/native 图形栈里,两者描述的是同一批底层图形内存,可以视为同一份底层 buffer 在不同层的表示。

Framebuffer 的管理采用双缓冲(或多缓冲)机制:前缓冲区用于显示,后缓冲区用于渲染,两者在 VSync 信号到来时交换。这个机制避免了画面撕裂--如果没有双缓冲,GPU 正在写入的缓冲区同时被显示控制器读取,画面就会出现上下半帧不一致的情况。在高分辨率屏幕上,Framebuffer 的内存占用不容忽视:以 1080p 屏幕、RGBA8888 格式为例,单个 Framebuffer 就需要约 8MB 内存(1920×1080×4 字节),而三缓冲机制下就需要 24MB。在 2K 甚至 4K 屏幕上,这个数字会成倍增长。

## Shader Compilation Jank:首次编译着色器导致的掉帧

### 运行时编译的性能问题

在 Perfetto Trace 中,我们有时会看到一种特定的掉帧模式:应用前 60fps 流畅运行,然后突然掉到 10-20fps 持续几百毫秒,之后又恢复到 60fps。这种"突然卡一下又恢复"的模式,很多时候就是 Shader Compilation Jank--当应用首次使用某个着色器时,GPU 需要将其从 GLSL/SkSL 源码编译成本地 GPU 指令,这个过程耗时可能从几毫秒到几十毫秒不等。

为什么需要在运行时编译?原因在于 Android 设备的 GPU 架构多样性。Qualcomm Adreno、ARM Mali、Imagination PowerVR 各有不同的指令集和优化策略,同一份 GLSL 着色器在不同 GPU 上编译出的机器码完全不同。开发者无法在 APK 中预编译所有平台的着色器二进制,只能在运行时根据实际 GPU 架构进行编译。

```cpp
// 示意性伪代码:着色器编译的概念流程
// 注意:GLESContext 类并非 AOSP 中的实际类,OpenGL ES 着色器编译通过
// 标准 EGL/GLES API 完成(glShaderSource / glCompileShader)
// 以下代码仅为说明编译流程,非 AOSP 实际源码
void compileShaderExample(GLuint shader, const char* source) {
    glShaderSource(shader, 1, &source, NULL);
    glCompileShader(shader);
    GLint compiled = 0;
    glGetShaderiv(shader, GL_COMPILE_STATUS, &compiled);
    if (!compiled) {
        // 编译失败处理
    }
}
```

问题在于,着色器编译发生在渲染线程上。当用户触发了一个新的 UI 效果(比如打开一个使用了特殊模糊效果的页面),GPU 第一次遇到这个效果的着色器,就会在当前帧的渲染过程中触发编译--编译期间渲染线程被阻塞,当前帧无法在 VSync 周期内完成,于是掉帧就出现了。

### Skia Pipeline Cache 缓存机制

Skia 作为 Android 的主要图形库,提供了一套 Pipeline Cache 机制来减少重复编译的代价。这个机制包含几个层次:SkSL 预编译允许开发者在构建时收集着色器,打包到 APK 中;运行时缓存将编译后的着色器持久化到本地存储,下次启动时直接加载;Android 16 开始,Google 进一步增强了着色器预编译能力,期望将更多编译工作从运行时移到安装时或启动时。

> [已验证: 官方文档, developer.android.com/guide/topics/graphics/opengl]

在实际优化中,一个常见的做法是"着色器预热"--在应用启动的空闲时段,主动触发可能用到的着色器编译。这样虽然会增加启动时间,但避免了在动画或滚动过程中突然出现编译卡顿。Flutter 框架对这个策略有较好的支持,通过 `--cache-sksl` 标志可以在开发阶段收集所有着色器,然后在发布包中提前加载。

### Vulkan 的优化方案

Vulkan 在着色器编译方面有先天优势。Vulkan 使用 SPIR-V 作为中间表示格式,着色器在构建时就被编译为 SPIR-V 二进制并打包到 APK 中。运行时,GPU 驱动只需要将 SPIR-V 进一步编译为本机指令,这个过程的耗时会比从 GLSL 源码编译快得多。

```cpp
// Vulkan 着色器加载示例
// GLSL 源码在构建时通过 glslc 编译器转换为 SPIR-V 二进制
// 运行时直接加载预编译的 SPIR-V 模块
VkShaderModuleCreateInfo createInfo{};
createInfo.sType = VK_STRUCTURE_TYPE_SHADER_MODULE_CREATE_INFO;
createInfo.codeSize = spirvCode.size() * sizeof(uint32_t);
createInfo.pCode = spirvCode.data();
// vkCreateShaderModule() 将 SPIR-V 编译为 GPU 本机指令
```

> [自动发现: 来源 2026-03-30-ch02-vulkan-android16.md]

Android 16 将 Vulkan 定为默认图形 API 的一个重要动机,就是利用 SPIR-V 的预编译优势来减少 Shader Compilation Jank。对于仍然使用 OpenGL ES 的应用,ANGLE 转换层会将 GLSL 着色器翻译为 SPIR-V 后再交给 Vulkan 后端处理,虽然多了一层翻译,但依然比传统 OpenGL ES 驱动的纯运行时编译更可控。

## Vulkan vs OpenGL ES 在 Android 上的性能对比

上面讨论的 Shader Compilation Jank 问题,其根源之一是 OpenGL ES 的运行时编译模型。Vulkan 使用 SPIR-V 预编译格式从运行时编译源头上缓解了这个问题,但 Vulkan 相比 OpenGL ES 的优势远不止于此。理解两者的性能差异,是分析 Android 16 及以后版本 GPU 行为的基础。

### Android 16 的图形栈推进:Vulkan-first 与 ANGLE 扩展

Android 16 把 Vulkan 推到更靠前的位置,但要把这句话拆开看。对应用开发者,系统默认优先按 Vulkan-first 的图形栈走;对仍使用 OpenGL ES 的应用,**部分设备**会通过 ANGLE 把 GL 调用翻译到 Vulkan--ANGLE 是否启用取决于设备配置(`ro.hardware.egl`、全局 settings、平台 allowlist、ANGLE APK/system library 等条件),不能直接写成所有 GLES 应用都自动走 ANGLE。源码锚点:`GraphicsEnvironment.setupAngle()` / `queryAngleChoice()`。对设备厂商,新出货的 64 位设备还需要满足 Vulkan 1.4 / VPA16 这一层硬件基线。几个层次叠在一起,才构成"Android 16 的 Vulkan 推进"的完整含义。

VPA16 里与性能关系最直接的一项是 Host Image Copy。它允许 CPU 侧把图像数据直接拷入 GPU image,省掉 staging buffer 和一次额外 copy。对滚动列表里的大图、视频帧上传、纹理流式加载这类持续上传场景,收益通常体现在峰值内存更低、提交抖动更小,而不只是 API 名字变化。

这个转变背后的一个直接原因是 OpenGL ES 驱动实现质量长期参差不齐。不同 GPU 厂商(Qualcomm Adreno、ARM Mali、Imagination PowerVR)各自维护 OpenGL ES 驱动,bug 和性能差异都不小。Google 通过 ANGLE 将大量 OpenGL ES 调用统一翻译为 Vulkan,只需要维护一套 Vulkan 后端的质量,碎片化问题也随之收敛。但要注意:ANGLE 的启用取决于设备/应用级别的配置策略(`ro.hardware.egl`、Settings.Global、Angle APK allowlist),不是所有 GLES 应用在所有 Android 16 设备上都自动走 ANGLE。

### Vulkan 渲染管线的核心组件

Vulkan 渲染帧需要应用显式组装三个核心对象:VkCommandBuffer、VkRenderPass 和 VkFramebuffer。

**VkCommandBuffer** 是指令容器。应用在 CommandBuffer 中记录所有渲染命令(draw call、资源绑定、状态设置),然后一次性提交到 GPU 队列。CommandBuffer 可以在任意线程上构建,这是 Vulkan 多线程渲染能力的基础。

**VkRenderPass** 定义一帧渲染的结构:有哪些附件(color attachment、depth attachment)、每个附件在渲染开始和结束时的 load/store 操作、子 pass 之间的依赖关系。在移动 GPU 的 TBR 架构下,RenderPass 的边界直接影响 tile 的 load/store 行为--每开始一个新 RenderPass,GPU 要完成当前 tile 的写回并重新加载下一个 RenderPass 的附件。合并 RenderPass 可以减少 tile 写回次数,是移动端 Vulkan 性能优化的基本策略。

**VkFramebuffer** 是 RenderPass 的附件绑定实体,把 VkImageView(对应 swapchain image 或 offscreen render target 等实际图像资源)与 RenderPass 声明的附件槽位关联。Framebuffer 的生命周期通常与它所引用的图像资源一致--swapchain 重建时 Framebuffer 也需要重建。

三者的依赖关系:VkRenderPass 描述渲染结构,VkFramebuffer 提供渲染目标,VkCommandBuffer 记录渲染指令。提交渲染时,CommandBuffer 中记录的每个 RenderPass 实例都必须指定对应的 Framebuffer。在 Perfetto 的 Vulkan track 中,CommandBuffer 的构建时间(CPU 侧 Record phase)和 GPU 执行时间(Submit + Execute phase)是分开的,可以分别观察。

### CPU 开销:一个数量级的差距

Vulkan 相比 OpenGL ES 最核心的性能优势,在于大幅降低了 CPU 侧的开销。OpenGL ES 采用隐式同步模式--每次调用 `glDrawArrays()` 时,驱动层需要做大量状态检查、资源同步和错误验证工作,这些都在调用线程上同步完成。而 Vulkan 将这些控制权交给了开发者:GPU 命令的提交时机、资源的同步策略、内存的分配方式,全部由应用显式控制。

```cpp
// OpenGL ES 的隐式同步:每次 draw call 都附带大量驱动开销
glDrawArrays(GL_TRIANGLES, 0, vertexCount);

// Vulkan 的显式提交:开发者控制提交时机,避免不必要的同步等待
vkQueueSubmit(queue, 1, &submitInfo, fence);
```

在 OpenGL ES 中,一个简单的 draw call 可能需要 10-50μs 的 CPU 时间来处理驱动逻辑(具体取决于状态复杂度和驱动实现);而在 Vulkan 中,同样的 draw call 只需要 1-5μs--差距达到了一个数量级。对于 draw call 数量很多的应用(比如复杂的 UI 界面),这个差异会直接体现在帧时间上。

### 多线程渲染能力

[图:OpenGL ES 单线程提交 vs Vulkan 多线程命令缓冲区构建对比]

OpenGL ES 的另一个架构限制是命令提交只能在单一上下文中进行,多线程无法并行构建渲染命令。Vulkan 引入了命令缓冲区(Command Buffer)的概念:不同的线程可以独立构建各自的命令缓冲区,再在一个线程上统一提交到 GPU。对于 CPU 侧有大量渲染命令需要生成的场景--比如游戏引擎中不同线程分别处理场景渲染、UI 渲染和后处理--多线程构建命令缓冲区可以显著降低 CPU 瓶颈。

在 Android UI 渲染的场景中,多线程渲染的优势不如游戏场景明显,因为 UI 渲染的 draw call 数量通常不太多。但随着 Material Design 的效果越来越复杂(模糊、阴影、动画),这个优势在未来会越来越重要。

### 更精细的内存控制

Vulkan 暴露了显式的内存管理 API,开发者可以精确控制 GPU 内存的分配、映射和释放时机。

**命令缓冲区与同步机制**:Vulkan 的同步原语分三层--`VkFence` 用于 CPU-GPU 同步(CPU 等待 GPU 完成一批工作),`VkSemaphore` 用于 GPU 内部队列间或同一队列不同提交间的同步(比如渲染完成后再触发合成),`VkEvent` 用于命令缓冲区内部的细粒度同步。在 Android 的 HWUI 场景中,RenderThread 提交命令缓冲区时通过 `VkFence` 追踪 GPU 完成状态--Perfetto 中 RenderThread 的等待时间对应的就是 fence wait。`vkQueueSubmit()` 接受 fence 参数,GPU 执行完这批命令后 signal fence,CPU 侧的 `vkWaitForFences()` 才返回。在 OpenGL ES 中,这些全部由驱动隐式管理,开发者无法干预。在统一内存架构的移动设备上,这种控制能力尤为重要--CPU 和 GPU 共享同一块物理内存,合理的内存管理可以减少不必要的数据拷贝和缓存失效。

```cpp
// Vulkan 的精确内存管理
VkMemoryAllocateInfo allocInfo{};
allocInfo.sType = VK_STRUCTURE_TYPE_MEMORY_ALLOCATE_INFO;
allocInfo.allocationSize = memorySize;
allocInfo.memoryTypeIndex = findMemoryType(memoryRequirements);
vkAllocateMemory(device, &allocInfo, nullptr, &memory);
```

> [自动发现: 来源 2026-03-30-ch02-gpu-optimization.md]
> 移动 GPU 架构中,开始和结束渲染通道的代价较高,应将渲染操作合并到尽可能少的渲染通道中。使用 `VK_ATTACHMENT_LOAD_OP_DONT_CARE` 可以避免不必要的附件保留,减少带宽消耗。

### ANGLE 层的性能影响

对于仍然使用 OpenGL ES 的应用,ANGLE 转换层引入的性能开销需要单独看测试条件。[社区数据: ANGLE 性能开销数据来自 Google I/O 演讲与社区基准测试,非官方系统性基准数据] 社区里经常能看到 2-5%、5-10%、10-20% 这类数字,但这些数字只有在设备、GPU、驱动版本、分辨率、shader 复杂度和测试方法都写清楚时才有比较价值。放回工程语境后,可以把它理解成一个量级参考:2D UI workload 往往只是几个百分点,复杂 3D workload 会更高,合成型压力测试还会继续放大。正文把它当经验区间,只能做量级参考。

这个开销的来源主要有两方面:一是 GLSL 到 SPIR-V 的翻译过程,二是 OpenGL ES 的状态机模型到 Vulkan 的命令缓冲区模型的转换。对于大多数日常应用来说,ANGLE 的性能损耗在可接受范围内,而且 ANGLE 带来的驱动一致性和 bug 修复的收益通常远大于性能开销。

> [已验证: 官方文档, developer.android.com/guide/topics/graphics/opengl]

### Vulkan 与 OpenGL ES 的版本演进

从 Android 7.0 引入 Vulkan 到 Android 16 把图形栈推向 Vulkan-first,这条演进线跨越了近十年。把 `API 可用性`、`设备 launch requirement` 和 `ANGLE rollout` 拆开看,边界会更准确:

| Android 版本 | API Level | Vulkan / ANGLE 边界 |
|:---|:---|:---|
| 7.0 | 24 | Vulkan 1.0 API 与 NDK 支持进入 Android;是否可用取决于设备,OpenGL ES 仍是主路径 |
| 8.0 | 26 | Vulkan 生态开始稳定,更多设备通过 CTS/VTS 提供合规实现,仍未形成统一硬件门槛 |
| 10 | 29 | **新出货的 64 位设备** 需要支持 Vulkan 1.1;ANGLE 可以作为可选的 OpenGL ES 系统驱动用于兼容与调试 |
| 12-14 | 31-34 | ANGLE 覆盖范围继续扩大,Game Mode 与图形兼容性策略增多;是否由 ANGLE 接管仍取决于设备 launch policy 和厂商配置 |
| 15 | 35 | Vulkan-first 路线继续推进,更多设备把 ANGLE 用在默认 GL 路径上,不能只按 OS 版本划线 |
| 16 | 36 | **新设备默认按 Vulkan-first 图形栈设计**;新出货的 64 位设备基线提升到 Vulkan 1.4 / VPA16,包含 Host Image Copy;Vulkan Synchronization 2 减少了 RenderThread 指令提交中的同步开销;OpenGL ES 应用**在配置了 ANGLE 的设备上**通过 ANGLE-on-Vulkan 运行,ANGLE 启用由 `GraphicsEnvironment.setupAngle()` 决定 |

把这张表拆开后就不会把几件事混成一件事:Vulkan API 早在 Android 7.0 就出现;设备硬件门槛从 Android 10 的 Vulkan 1.1 一直推进到 Android 16 的 Vulkan 1.4 / VPA16;ANGLE 是否成为默认 GL 后端则是设备配置问题,不能直接写成单一 OS 版本边界。

## GPU 性能瓶颈分析:fillrate bound vs vertex bound vs bandwidth bound

### 瓶颈分析的基本方法

GPU 性能分析的第一步是搞清楚瓶颈在哪里。GPU 渲染的瓶颈大致可以分为三类:fillrate bound(像素处理能力不足)、vertex bound(顶点处理能力不足)和 bandwidth bound(内存带宽不足)。不同类型的瓶颈需要完全不同的优化方向,如果判断错了方向,优化努力就会白费。

判断瓶颈类型需要结合 Perfetto 和 AGI 两层分析。第一步,在 Perfetto 的 GPU track 上确认 GPU 渲染时间是否超过帧预算。第二步,用 Android GPU Inspector (AGI) 对具体帧做深度分析:如果 Fragment Shader 执行时间占 GPU 总时间超过 60%,且帧的渲染时间与界面可见像素数量正相关,是 fillrate bound;如果 Vertex Shader 时间占比异常高,且帧时间与界面几何复杂度(Path 数量、三角形数量)正相关,是 vertex bound;如果着色器执行时间不长但整体帧时间仍超标,同时 Perfetto 的内存带宽计数器显示高负载,是 bandwidth bound。

> 注意:PC 端常用的"降低渲染分辨率判断瓶颈类型"方法不适用于标准 Android UI 渲染。Android UI 没有独立的渲染分辨率设置(除非使用 SurfaceView 自行控制渲染缓冲区),应依赖 AGI 的 GPU 性能计数器来做定量判断。

### GPU Headroom:事前感知 GPU 负载(Android 16)

传统 GPU 瓶颈分析是事后诊断--帧已经掉了,再去 Trace 里找原因。Android 16 引入的 GPU Headroom API 提供了一条事前感知路径。该 API 通过 `android.os.health.SystemHealthManager`(通过 `Context.SYSTEM_HEALTH_SERVICE` 获取)暴露,核心方法是 `getGpuHeadroom(GpuHeadroomParams)`,返回值为 0-100 的浮点数或 `Float.NaN`(当 GPU 不支持 headroom 上报时返回 NaN)。值越接近 0,说明 GPU 越接近满载。

### 实战应用经验

#### 实际应用部署

```java
// Android 16+ (API 36)
SystemHealthManager shm = (SystemHealthManager)
    context.getSystemService(Context.SYSTEM_HEALTH_SERVICE);
GpuHeadroomParams params = new GpuHeadroomParams.Builder().build();
float headroom = shm.getGpuHeadroom(params);  // 返回 0-100 或 NaN

// 必须遵守最小采样间隔
long minInterval = shm.getGpuHeadroomMinIntervalMillis();

if (!Float.isNaN(headroom) && headroom < 30f) {
    // GPU 余量不足,考虑降级渲染质量
    // 减少实时模糊层级、降低动画粒子数、跳过非关键 Shader 特效
}
```

**部署陷阱**:
1. **同步开销意外高**:按帧调用导致每帧 1-2ms 阻塞,界面从 60fps 降到 30fps。改用 Choreographer 回调固定间隔解决。
2. **温控状态影响**:设备发热后 headroom 从 80 直降到 20。需要连续监测变化趋势。
3. **首次调用慢**:首次调用需要 5-10ms 初始化时间。应用冷启动时避开关键路径。

**实际降级方案**:
- headroom > 60:全质量渲染
- 30-60:关闭高开销后处理(模糊、阴影)
- < 30:简化动画,减少 draw call

这种动态降级比固定分辨率调整更精细,因为 GPU 负载会随场景快速变化。

### 性能影响实测

在游戏动画场景中测试了这个 API 的调用开销:

```bash
# 测量 API 调用耗时
adb shell am profile com.example start
# 触发动画场景
adb shell am profile com.example stop --output /sdcard/profile.txt
cat /sdcard/profile.txt | grep getGpuHeadroom
```

结果显示:在 60fps 场景中,正确调用的 API (每 100ms 一次) 增加 1-2% CPU 开销;错误调用的 API (每帧调用) 增加 15-20% CPU 开销。这个数字在 120fps 场景会更夸张。

调用该 API 本身会触发一次跨进程查询(Binder 同步),官方源码注释明确指出每次有效调用至少一次同步 Binder transaction,可能超过 1ms;首次调用或非默认 params 还可能因按需初始化更慢。严禁在渲染主线程中按帧轮询--在 120fps 下 1ms 的同步阻塞就消耗了 12% 的帧预算。建议在独立的监控线程中以 `minInterval` 为周期异步采样,或通过 Choreographer 回调按固定间隔查询。

> [已验证: AOSP android-16.0.0_r1, android.os.health.SystemHealthManager - getGpuHeadroom(GpuHeadroomParams) / getGpuHeadroomMinIntervalMillis()]

### Fillrate Bound:像素处理瓶颈

Fillrate bound 是 Android UI 渲染中最常见的瓶颈类型。它的本质是 GPU 无法足够快地将像素写入帧缓冲区--可能是 Fragment Shader 计算量太大,也可能是过度绘制(Overdraw)导致同一像素被反复处理。

过度绘制是 fillrate bound 最典型的原因。在 Android 的开发者选项中,"Debug GPU Overdraw" 工具用颜色编码来可视化过度绘制程度:原色表示没有过度绘制,蓝色表示 1 次过度绘制,绿色表示 2 次,浅蓝表示 3 次,红色表示 4 次及以上。如果我们在应用中看到大面积的红色区域,说明大量像素被重复绘制了 4 次以上--GPU 在这些像素上做了 4 倍的工作,但最终只有最上面一层的颜色被用户看到。

导致过度绘制的常见场景包括:多层嵌套的布局各自设置了不透明背景(父布局的背景被子布局完全覆盖,但仍然被渲染了);半透明叠加层的叠加(每增加一层半透明,就多一次像素计算);对话框或弹出层没有移除底下的内容(底层内容虽然被遮挡但仍然被渲染)。

> [已验证: 官方文档, developer.android.com/guide/topics/graphics/debug-overdraw]

优化过度绘制的核心思路是减少不必要的绘制:移除被完全覆盖的背景、使用 `clipPath()` 裁剪不可见区域、将半透明视图改为不透明视图(在视觉允许的情况下)。在 Compose 中,`Modifier.graphicsLayer` 可以帮助减少不必要的重绘。

### Vertex Bound:顶点处理瓶颈

Vertex bound 在 Android UI 渲染中相对少见,但在某些场景下会出现--比如使用了大量自定义 Path 的绘制(SVG 图标、矢量动画)、Canvas 变换层级很深导致矩阵计算复杂、或者使用了大量的 `Canvas.drawPath()` 调用。

顶点处理瓶颈的识别主要依赖 GPU Profiling 工具。使用 Android GPU Inspector (AGI) 时,如果顶点处理时间占 GPU 总时间的比例超过 50%,就值得进一步排查。在 Perfetto 中,我们可以对比 GPU track 中不同帧的执行时间模式--如果帧的渲染时间与界面的几何复杂度正相关(比如滚动到一个包含大量 Path 的区域时 GPU 时间突增),这就是 vertex bound 的信号。

优化的方向包括:使用更简单的几何形状替代复杂 Path(用矩形近似圆角矩形在视觉可接受的情况下);减少 Canvas 的 save/restore 和矩阵变换层数;对于静态的复杂图形,考虑预渲染为 Bitmap 缓存。

> [说明: TBR 架构这一段依赖 ARM / Qualcomm 公开优化资料与渲染行为观察,本段不建立在某个单一 AOSP 目录上。]

在瓦片式渲染(TBR)架构的移动 GPU 上,通过高效管理加载和存储操作以及附件,可以显著提高性能。TBR 架构的 GPU(如 ARM Mali)会将一帧的渲染任务划分为多个瓦片,每个瓦片独立处理,这减少了对主显存的访问频率。

### Bandwidth Bound:内存带宽瓶颈

Bandwidth bound 是三种瓶颈中最容易被忽略的一种。它的本质是 GPU 在等待数据--GPU 的计算能力足够,但数据从内存传输到 GPU 计算单元的速度跟不上。在移动设备的统一内存架构中,CPU、GPU、显示控制器、相机 ISP 等模块共享同一块物理内存和总线,当多个模块同时高负载工作时,内存带宽就会成为瓶颈。

导致 bandwidth bound 的常见场景包括:大尺寸纹理没有使用压缩格式(一张未压缩的 2048×2048 RGBA8888 纹理需要 16MB 存储,每次采样都需要从内存读取数据);没有生成 Mipmap(GPU 总是使用最高分辨率纹理,即使物体在屏幕上只占几个像素);帧缓冲区位深度过高(RGBA8888 比 RGBA5551 多一倍的数据量)。

优化带宽的核心策略是减少数据传输量:使用纹理压缩格式;为所有 3D 纹理生成 Mipmap(让 GPU 根据物体大小选择合适的分辨率级别);在视觉允许的情况下使用更低精度的帧缓冲区格式。

### ASTC vs ETC2:带宽瓶颈下的压缩格式选择

在 bandwidth bound 场景下,选择哪种纹理压缩格式直接影响带宽消耗和帧时间。Android 上两种主流格式的关键差异:

| 维度 | ASTC | ETC2 |
|------|------|------|
| 压缩块大小 | 可配置(4×4 到 12×12) | 固定 4×4 |
| 压缩比 | 灵活:4×4 块约 4bpp(8:1),8×8 块约 2bpp(16:1) | 固定 4bpp(8:1 for RGB,6:1 for RGBA) |
| Alpha 通道 | 原生支持 | 需要单独的 EAC 编码,解码开销增加 |
| 解码硬件开销 | Adreno 6xx+ 和 Mali Midgard+ 均有固定功能解码单元,单周期完成 | 同样有硬件解码单元,但 RGBA 通道需要两次解码 |
| 视觉质量(同压缩比) | 更优:ADAPTIVE 算法根据局部复杂度分配 bit budget | 固定分配,平坦区域浪费 bit,复杂区域质量不足 |
| 设备支持 | Android 5.0+ 全线支持(GLES 3.0+ 必选) | Android 4.0+ 全线支持(GLES 3.0 必选) |

在带宽受限场景中的选择建议:优先使用 ASTC。同压缩比下 ASTC 视觉质量更好,意味着可以用更高的压缩比(更大的 block size)达到相同的视觉标准,直接减少带宽消耗。在 Adreno 830 和 Mali Immortalis G925 等现代 GPU 上,ASTC 和 ETC2 的硬件解码延迟差异可以忽略--两者都是单周期固定功能单元操作,瓶颈在于内存传输而非解码计算。只有在需要兼容极老旧设备(GLES 2.0)时才考虑 ETC2。

**验证方式**:

ASTC 与 ETC2 的选择不应只靠格式名判断。发布或上线前至少固定三组条件:设备 SoC 与 GPU、图片尺寸与缩放方式、滚动场景的帧率和 thermal 状态。没有原始 AGI / Perfetto trace 或厂商 profiler 记录时,不要把某个百分比写成通用结论。

```bash
# 确认设备 ASTC 支持情况
adb shell cmd gpu vkjson | grep -A 5 -B 5 astc
# 应显示支持的 block sizes,如 {"blockWidth":4,"blockHeight":4,...}

# 采集滚动场景帧时间,再配合 AGI / 厂商 profiler 查看纹理与外部内存计数器
adb shell dumpsys gfxinfo com.example.app framestats
```

判断 ASTC 是否收益明确,至少看三类信号:同一场景下 GPU frame time 是否下降,Texture Unit / External Memory 相关计数器是否下降,视觉质量是否仍满足产品标准。若只有 `dumpsys gfxinfo` 的帧时间,只能说明用户侧帧预算是否改善,不能单独证明带宽下降。

**选择建议**:
1. **现代设备(Adreno 7xx+,Mali-G78+)**:优先 ASTC,视觉质量+带宽双重优势
2. **中端设备**:ASTC 6×6 通常是最佳选择
3. **低端设备**:如果遇到 ASTC 解码性能问题,可考虑 ETC2
4. **兼容性要求**:如果必须支持 GLES 2.0 设备,ETC2 是唯一选择

## 移动 GPU 的 TBR 架构

分析 GPU 性能瓶颈之前,需要先理解一个硬件架构前提:几乎所有移动 GPU 都采用 Tile-Based Rendering(TBR)架构。TBR 直接影响了带宽消耗模式、驱动策略,以及很多看似"反直觉"的性能现象。

### TBR 的核心思路

传统桌面 GPU 采用 Immediate Mode Rendering(IMR):逐个处理 draw call,每个 draw call 直接向主显存写入像素数据。移动 GPU 不这样做。TBR 将一帧的渲染区域划分为若干个瓦片(tile,通常 16×16 或 32×32 像素),每个瓦片独立处理:先把该瓦片内所有 draw call 的几何数据收集起来,然后在 GPU 片上缓存(on-chip tile buffer)中完成该瓦片所有像素的着色计算,再一次性写回主显存。

这样做的原因是功耗和带宽。移动 GPU 的片上缓存访问速度接近寄存器,功耗极低;而访问主显存(即使是统一内存架构中的 LPDDR)需要经过总线,功耗和延迟都高一个量级。TBR 通过尽量减少主显存访问来降低功耗--这是移动设备的第一优先级。

### TBR 对性能分析的影响

理解了 TBR 架构,以下几个现象就有了技术解释:

**带宽消耗集中在 Tile 写回阶段。** 在 Perfetto 中看到的 GPU 活动,大部分时间 GPU 在片上缓存中计算,主显存访问发生在每个瓦片完成后。减少 overdraw 会同时减少重复计算和 tile buffer 写回次数。

**RenderTarget 切换代价高。** 每个 RenderTarget(在 Vulkan 中称为 RenderPass)需要先从主显存加载(load)现有内容到 tile buffer,处理完再写回(store)。如果一个 RenderPass 只做了很少的工作,load 和 store 的开销可能比实际渲染还大。这就是 Vulkan 中强调"合并 RenderPass"的原因。

**部分清除是免费的。** 在 Vulkan 中,使用 `VK_ATTACHMENT_LOAD_OP_CLEAR` 比 `VK_ATTACHMENT_LOAD_OP_LOAD` 更高效,因为 clear 操作不需要从主显存加载数据到 tile buffer--直接在片上缓存中填充即可。OpenGL ES 中调用 `glClear()` 也有类似的性能优势。

> ARM Mali 和 Qualcomm Adreno 都使用 TBR 架构,但在瓦片大小、缓存策略上有差异。分析具体设备的 GPU 行为时,建议参考对应厂商的优化指南(ARM GPU Best Practices / Qualcomm Adreno GPU Guide)。

## GPU 内存管理:GraphicBuffer / Gralloc / GPU Memory 归属与追踪

### Android GPU 内存管理架构

[图:Android GPU 内存管理层次图--App 可见对象(Surface / SurfaceTexture / HardwareBuffer / ANativeWindow)→ BufferQueue → GraphicBuffer / Gralloc / Mapper → GPU / HWC]

Android 的 GPU 内存管理分成几层。App 平时直接接触的是 `Surface`、`SurfaceTexture`、`ANativeWindow`、`HardwareBuffer` 这类公开对象,用它们申请、提交或共享缓冲区;BufferQueue 负责在生产者和消费者之间周转 slot;系统的 framework/native 图形栈再用 `GraphicBuffer` 包装底层 handle,把 format、usage、stride、fence 等信息带给 SurfaceFlinger、RenderThread 和 HWC;物理页分配与映射由 Gralloc / Mapper 完成。

理解这个层次结构有一个关键前提:在移动设备上,CPU 和 GPU 共享同一块物理内存(统一内存架构,UMA)。这与 PC 上 CPU 内存和 GPU 显存分离的架构有本质区别。在 UMA 架构下,所谓 "GPU 内存" 没有独立的物理存储;它来自系统内存,只是带有特定对齐和访问属性。GPU 的内存使用会直接影响系统的可用内存总量。在分析应用内存占用时,不能只看 Java heap--GPU 占用的内存同样重要。

```java
// frameworks/native/libs/ui/include/ui/GraphicBuffer.h
// @ AOSP android-16.0.0_r1
// C++ 头文件定义(GraphicBuffer 实为 C++ 类,Java 层仅为 JNI 包装器)
// [简化示意] 实际类比这更复杂,这里只展示与内存排查相关的核心结构
public class GraphicBuffer implements Parcelable {
    // Java 侧缓存的基本属性
    private int mWidth;
    private int mHeight;
    private int mFormat;
    private long mUsage;

    // 指向 native GraphicBuffer 对象的指针
    private long mNativeObject;

    // 这些 getter 是普通 Java getter,直接返回上述字段
    public int getWidth()  { return mWidth; }
    public int getHeight() { return mHeight; }
    public int getFormat() { return mFormat; }
    public long getUsage() { return mUsage; }
    // ...
}
```

这段类定义主要用来说明 `GraphicBuffer` 在 framework 层的包装位置,不代表普通应用应该直接持有它。排查 GPU 内存问题时,更常见的观察点是 Perfetto 里的 `gpu_memory` track、`dumpsys meminfo` 中的 Graphics / EGL mtrack,以及 `dumpsys SurfaceFlinger` 里能看到的 BufferQueue slot 与 layer 缓冲区占用。

### Gralloc:图形内存分配器

Gralloc(Graphics Memory Allocator)是 Android HAL 层中专门负责图形缓冲区内存分配的模块。当应用或系统需要一块新的图形缓冲区时(比如创建一个新的 Surface,或者 Surface 需要更多的缓冲区),请求最终会到达 Gralloc HAL。

Gralloc 分配内存时,调用者需要通过 `usage` 标志位来声明这块内存的用途--比如 `USAGE_HW_TEXTURE` 表示这块缓冲区将被 GPU 作为纹理读取,`USAGE_HW_RENDER` 表示 GPU 会向这块缓冲区写入渲染结果,`USAGE_SW_READ_OFTEN` 表示 CPU 会频繁读取这块内存。Gralloc 根据 usage 标志来决定内存的物理布局:应该分配在哪个内存区域、是否需要缓存策略、对齐要求是什么。这些决策直接影响 GPU 访问这块内存的效率。

```cpp
// allocator / mapper 的职责示意
// Android 16 主线设备以 AIDL Gralloc 为主,旧设备也可能保留 HIDL 4.x vendor 实现
allocate(BufferDescriptor descriptor) -> native_handle_t
importBuffer(native_handle_t) -> BufferHandle
lock(BufferHandle, usage, region) -> mapped_ptr
unlock(BufferHandle) -> release_fence
```


<!-- AIW-源码调研-2026-05-06 -->
### 源码级对象链:六层抽象的完整调用路径

本节概述了各层对象的作用,以下从源码角度梳理跨越 App 层到硬件层的完整对象链,建立可验证的追溯链:

**完整对象链**:

```text
App (Java/Kotlin)
    ├── android.graphics.Bitmap (HARDWARE)
    │    mNativeBitmap = AHardwareBuffer*(无 Java heap,像素全在 GPU 显存)
    │
    └── android.graphics.SurfaceTexture
         mProducer: IGraphicBufferProducer(跨进程 Binder 端点)
              │
ANativeWindow (C/C++ Layer)
    └── Surface.cpp(frameworks/native/libs/gui/Surface.cpp)
         mGraphicBufferProducer: IGBP
              │
BufferQueue(跨进程)
    ├── BufferQueueProducer.cpp → dequeueBuffer() → waitForFreeSlotThenRelock()
    │    (阻塞条件:dequeuedCount >= mMaxDequeuedBufferCount = 1)
    ├── BufferQueueCore.h → mSlots[64] / mQueue / mFreeSlots / mFreeBuffers
    └── BufferQueueConsumer.cpp → acquireBuffer()
              │
GraphicBuffer(frameworks/native/libs/ui/include/ui/GraphicBuffer.h)
    ├── mBufferHandle: buffer_handle_t(ashmem fd / dmabuf fd)
    └── flatten/unflatten 跨进程传递句柄
              │
GraphicBufferMapper(frameworks/native/libs/ui/GraphicBufferMapper.cpp)
    ├── importBuffer() → ION/DMABuf map → 进程地址空间
    └── freeBuffer() → ION/DMABuf unmap
              │
Gralloc HAL(/vendor/lib/hw/gralloc.*.so)
    ├── alloc() → ION heap / CMA / carveout 分配
    └── free()
              │
Physical Memory(ION heap / CMA / GPU VRAM)
```

**关键源码位置**:

| 层次 | 关键对象/函数 | 源码路径 |
|------|--------------|----------|
| App | Bitmap.Config.HARDWARE | `frameworks/base/graphics/java/android/graphics/Bitmap.java` |
| App | SurfaceTexture.mProducer | `frameworks/base/graphics/java/android/graphics/SurfaceTexture.java` |
| ANativeWindow | Surface::dequeueBuffer() | `frameworks/native/libs/gui/Surface.cpp`(ANativeWindow hook 路由) |
| BufferQueue | BufferQueueCore.mSlots/mQueue | `frameworks/native/libs/gui/include/gui/BufferQueueCore.h`(NUM_BUFFER_SLOTS=64) |
| BufferQueue | waitForFreeSlotThenRelock() | `frameworks/native/libs/gui/BufferQueueProducer.cpp`(mDequeueCondition 条件变量) |
| BufferQueue | releaseBuffer() → notify_all() | `frameworks/native/libs/gui/BufferQueueProducer.cpp` |
| BufferQueue | acquireBuffer() | `frameworks/native/libs/gui/BufferQueueConsumer.cpp` |
| GraphicBuffer | mBufferHandle 类型 | `frameworks/native/libs/ui/include/ui/GraphicBuffer.h`(buffer_handle_t = native_handle_t*) |
| Mapper | importBuffer/freeBuffer | `frameworks/native/libs/ui/GraphicBufferMapper.cpp`(ION/DMABuf map) |
| Gralloc | gralloc_module_t | `hardware/libhardware/include/hardware/gralloc.h`(alloc/free 接口) |
| HWC | HWC2::Display::getRequests() | `frameworks/native/services/surfaceflinger/DisplayHardware/HWC2.cpp`(DEVICE/CLIENT 决策) |

**Buffer Stuffing 源码机制**:当 SurfaceFlinger/HWC release 延迟时,`mFreeBuffers` 为空,`mQueue.size()` 积压超过 `maxBufferCount`,`waitForFreeSlotThenRelock()` 会等待可用 slot。AOSP android-16.0.0_r1 中负 `mDequeueTimeout` 走条件变量等待,非负超时会返回 `TIMED_OUT`;`BUFFER_RELEASE_CHANNEL` 是 android-16 可见的 flag-gated 路径,不能写成 Android 14 已引入。

**可观测性边界**:

| 观测工具 | 可见 | 不可见 |
|---------|------|--------|
| Perfetto `android.surfaceflinger.sf_frames` | dequeueBuffer/queueBuffer/acquireBuffer slice 持续时间、HWC composition type(Device/Client) | GPU 显存物理占用 |
| `dumpsys surfaceflinger --latency` | BufferQueue 各槽位状态、mSlots 列表 | ION/Gralloc 物理内存精确值 |
| `/proc/<pid>/smaps` | ashmem 段(4KB page)或 dma_buf 映射(16KB page)大小 | GPU 内部显存池化部分 |
| Perfetto `android.memory.pss` | Java heap PSS | GraphicBuffer buffer_handle_t 映射的物理内存(不在 PSS 中) |

**Hardware Bitmap 特殊行为**:Bitmap.Config.HARDWARE(API 26+)创建的 Bitmap,像素数据完全不存在于 Java heap,全部存储在 GPU 显存中的 AHardwareBuffer。`/proc/<pid>/smaps` 中不反映其占用,必须通过 `dumpsys meminfo gfxinfo` 或厂商特定工具观测。

> [已验证: AOSP android-16.0.0_r1, frameworks/native/libs/gui/Surface.cpp; frameworks/native/libs/gui/include/gui/BufferQueueCore.h; frameworks/native/libs/gui/BufferQueueProducer.cpp; frameworks/native/libs/ui/GraphicBufferMapper.cpp]

> [已验证: AOSP android-16.0.0_r1, hardware/interfaces/graphics/allocator/aidl/]

### 16KB 页环境下的 Gralloc 池化优化

Android 16 在 16KB 页模式下,Gralloc AIDL V2 **在设计方向上**引入了内部子分配(sub-allocation)机制。传统模式下每个 GraphicBuffer 独立占用整数个物理页,小面积纹理(如 64x64 的图标缓冲区)在 16KB 页对齐后会产生大量页内碎片--一个 64x64 RGBA8888 缓冲区只需约 16KB 数据,但加上对齐和 metadata 开销,实际可能占用 32-48KB 物理页。子分配机制的设计目标是允许 Gralloc 在一个大物理页范围内管理多个小缓冲区,按实际数据大小而非整页粒度分配。

> [说明: Gralloc AIDL V2 sub-allocation 机制基于 Android 16 GKI 内核变更与硬件接口定义方向(`hardware/interfaces/graphics/allocator/aidl/`),但当前缺少公开的 AIDL 接口方法签名、VTS/CTS 测试用例或 vendor 实现代码作为验证证据。实际行为可能因 SoC 厂商实现而有差异。以上描述应视为基于设计意图的推断,而非已验证事实。具体实现细节待后续 AOSP 源码或厂商文档确认后补齐。]

在应用层面,如果该优化进入实现并被厂商启用,效果是透明的--不需要修改任何代码。但在分析 GPU 内存占用时需要注意,16KB 页环境下 `dumpsys meminfo` 中的 Graphics 内存项可能比 4KB 环境下看起来更低,部分原因可能是 Gralloc 内部碎片减少。

### GPU 内存追踪和分析

Android 12 引入了改进的 GPU 内存追踪机制,使得开发者和性能分析工程师可以更好地了解 GPU 的内存使用情况。在 Perfetto 中,我们可以通过 `gpu_memory` track 看到每个进程的 GPU 内存使用量随时间的变化。`adb shell dumpsys meminfo <package_name>` 的输出中也包含了 GPU 相关的内存统计。

在实际分析中,以下几种 GPU 内存问题比较常见:缓冲区泄漏--GraphicBuffer 被分配但没有正确释放,导致 GPU 内存持续增长,这在应用频繁创建和销毁 Surface 时容易发生;缓冲区积压--生产者(应用)产生帧的速度超过消费者(SurfaceFlinger)处理的速度,导致 BufferQueue 中积压了多个缓冲区,每个缓冲区都占用 GPU 内存;以及大型纹理未释放--加载了大量高分辨率纹理但没有在不需要时及时释放。

> [已验证: AOSP android-16.0.0_r1, frameworks/native/services/surfaceflinger/]
> Android 14 提供了减少图形内存消耗的功能,允许清除位于 Composer HAL 和 SurfaceFlinger 之间的每层缓冲区缓存。这对于高分辨率屏幕和内存有限的设备特别有益。

## ANGLE(OpenGL ES on Vulkan)的性能影响

前面我们讨论了 GPU 内存管理的完整链条,从应用层的 GraphicBuffer 到 HAL 层的 Gralloc。而在 Android 16 的渲染架构中,ANGLE 兼容层需要单独拆出来看。在启用 ANGLE 的设备/应用组合中,仍然使用 OpenGL ES 的应用会通过 Google 的 OpenGL ES 兼容层把 GL 调用翻译为 Vulkan 调用。对于性能分析工程师来说,理解 ANGLE 的性能特征,是评估现有应用在新系统上渲染表现的关键。

### ANGLE 的设计目标

ANGLE(Almost Native Graphics Layer Engine)是 Google 开发的兼容层,它在启用时将 OpenGL ES API 调用翻译为 Vulkan 调用。ANGLE 的设计目标远不止"兼容"--主要目标是"统一"。在 Android 16 之前,不同 GPU 厂商各自实现 OpenGL ES 驱动,质量参差不齐,bug 各不相同。ANGLE 将 OpenGL ES 的实现统一为一套代码(翻译到 Vulkan),Google 只需要维护这一套实现的质量,而不需要分别与三个厂商协调驱动修复。

ANGLE 的架构可以理解为一个翻译层:上层应用仍然使用熟悉的 OpenGL ES API(glDrawArrays、glTexImage2D 等),ANGLE 在内部将这些调用翻译为对应的 Vulkan 操作(vkCmdDraw、vkCreateImage 等)。对于应用开发者来说,在 ANGLE 被启用的设备上,这个过程通常是透明的--应用不需要修改代码,就可以通过 ANGLE 运行在 Vulkan 后端上。

[图:ANGLE 架构图--OpenGL ES App → ANGLE 翻译层 → Vulkan Driver → GPU]

### ANGLE 在 Android 16 中的角色

Android 16 推进了 ANGLE 的覆盖范围,但"ANGLE 是否成为默认 GL 后端"取决于设备 launch policy 和厂商配置,不能一概而论。对于新出货的、满足 Vulkan 1.4 / VPA16 基线的 64 位设备,更多 OpenGL ES 应用会通过 ANGLE 将渲染调用翻译到 Vulkan 后端;对于已上市的旧设备,ANGLE 的启用策略可能仍然是渐进式的或按应用白名单控制;对于直接使用 Vulkan 的应用,始终绕过 ANGLE 直接与 Vulkan 驱动交互;不支持 Vulkan 的设备则回退到原生的 OpenGL ES 驱动。

因此,在 Android 16 设备分析 GPU 性能时,需要先确认目标设备上 OpenGL ES 应用是否走了 ANGLE 路径--可以通过 `adb shell dumpsys gfxinfo <package>` 或 Perfetto 中的 GPU driver 信息判断。不同路径下的性能特征和瓶颈分析方式有差异。

## GPU Profiling 工具:Snapdragon Profiler、ARM Streamline、AGI

前面我们从理论和机制层面分析了 GPU 渲染的各个环节,也讨论了如何从 Trace 中识别 GPU 瓶颈的类型。但要进一步精确定位--比如区分 fillrate bound 和 bandwidth bound 的具体占比,或者找到某个 Fragment Shader 的耗时热点--还需要专门的 GPU 分析工具。这一节介绍三种最常用的 GPU 性能分析工具及其适用场景。

### Android GPU Inspector (AGI)

AGI 是 Google 官方的 Android GPU 性能分析工具,也是 Android 开发者最应该熟悉的第一款 GPU 工具。AGI 提供了帧分析器(逐帧分析 GPU 渲染时间)、系统分析器(CPU 和 GPU 交互分析)、内存分析器(GPU 内存使用分析)和着色器分析器(着色器性能分析)四个核心功能模块。

在瓶颈定位的工作流中,AGI 的使用方式通常是:先用系统分析器确认问题出在 GPU 侧(而不是 CPU 侧),然后用帧分析器找到 GPU 时间最长的那一帧,再对着色器和渲染状态进行分析,定位具体的瓶颈环节。AGI 的一个独特优势是它可以与 Perfetto Trace 结合使用--在 Perfetto 中看到 GPU 时间异常的帧后,可以用 AGI 对同一时间段进行深度分析。

### 平台专用工具

除了 AGI 之外,不同 GPU 平台还有各自的专业分析工具。Snapdragon Profiler 是 Qualcomm 官方的 GPU 分析工具,专为 Adreno GPU 设计,提供详细的 GPU 性能计数器、帧时间线分析和功耗分析。ARM Streamline 是 ARM 官方的性能分析工具,支持 Mali GPU,它的特色是可以同时分析 CPU 和 GPU 的协同工作情况,对理解大小核架构下 GPU 的调度行为特别有用。

```bash
# AGI 基本使用流程
# 1. 连接设备
adb devices
# 2. 启动 AGI(通过 Android Studio 或命令行)
# 3. 选择目标应用和分析模式
# 4. 录制 GPU Trace
# 5. 分析结果:关注帧时间、着色器执行时间、内存带宽使用
```

在实际工作中,我们建议先从 AGI 入手--它足够通用,覆盖了大多数分析场景。如果需要针对特定平台的深度分析(比如需要查看 Adreno GPU 的特定性能计数器),再切换到平台专用工具。

> [已验证: 官方文档, developer.android.com/studio/profile/android-gpu-inspector]

## 实战案例:社交应用图片滚动中的 GPU 瓶颈定位

> **证据边界**:以下内容是示例场景，用来说明图片信息流滚动时的 GPU 排查路径。本稿没有随文附上可复核的 Perfetto / AGI artifact，因此不把帧耗时、带宽下降百分比或帧率提升写成实测结论。发布真实案例时，应同时给出设备型号、Android 版本、刷新率、采样配置、trace 文件或截图。

### 问题现象

图片信息流滚动卡顿时，主线程不一定是根因。一个常见场景是：MainThread 的 `doFrame` 和 RenderThread 的录制时间都在帧预算内，但 GPU activity 跨过一个或多个 VSync 周期，SurfaceFlinger 只能继续使用旧 buffer。这类现象要优先检查 fillrate、纹理采样和内存带宽，Java / Kotlin 侧逻辑优化放到后面验证。

### 证据采集方式

Perfetto 负责确认“卡在哪个时序段”。采集滚动场景时，至少打开 FrameTimeline、RenderThread、SurfaceFlinger、GPU counter 和 `gpu_render_stages`（设备支持时）。如果 `gpu_render_stages` 不可用，就用 GPU busy、RenderThread wait、SurfaceFlinger latch 结果交叉判断。

```bash
# 录制包含 GPU counter 的滚动场景 trace，配置文件需按设备能力裁剪。
adb shell perfetto --txt --config gpu-basic.cfg -o /data/misc/perfetto-traces/social_scroll.pftrace
adb pull /data/misc/perfetto-traces/social_scroll.pftrace .
```

AGI 负责把某一帧拆到 draw call、shader 和纹理访问层面。Perfetto 已经确认 GPU 超时时，再用 AGI 桌面端或 Android Studio 集成入口录制同一复现场景，查看 Fragment、Texture Unit、External Memory、Vertex / Tiler 等计数器。不同 GPU 厂商的计数器名称不同，结论要写成“哪个计数器在同一批掉帧帧里同步抬升”，不要只写工具截图里的栏目名。

### 判断路径

**确认 CPU 是否已经让路。** MainThread 的 `doFrame`、RenderThread 的 display list 处理和 command submit 如果都没有长段阻塞，而 GPU activity 仍跨过 VSync 边界，问题就落到 GPU 侧。这个判断要同时看 FrameTimeline 的 present 状态和 SurfaceFlinger 是否 latch 到新 buffer。

**确认瓶颈类型。** Fragment / Texture 相关计数器随掉帧帧抬升，且界面有大面积图片、圆角、阴影、半透明叠加时，优先按 fillrate bound 或 bandwidth bound 处理。Vertex / Tiler 相关计数器抬升，且界面里有大量 Path、复杂裁剪或几何动画时，再转向 vertex bound。

**确认纹理和过度绘制。** 图片信息流最常见的三类浪费是：列表背景、卡片背景和图片背景重复绘制；圆角 mask、阴影 blur、渐变 overlay 叠加纹理采样；大图未压缩或缺少合适 mipmap，滚动时反复触发高带宽读取。开发者选项的 overdraw 只能给方向，是否拖慢一帧仍要回到 Perfetto / AGI 证据。

### 可验证的修复方向

**减少过度绘制。** 合并列表背景和卡片背景，移除滚动区域里不会被看到的中间层；对稳定遮挡区域做裁剪，避免把被上层完全盖住的像素继续送进 Fragment Shader。修复后用 overdraw 调试和 Perfetto GPU activity 一起确认，不能只看颜色变浅。

**减少纹理采样。** 圆角图片优先使用平台或库里能合并 pass 的实现；阴影和复杂遮罩如果在滚动中反复计算，考虑预渲染或缓存。AGI 里要看同一类 item 的 draw call 数、纹理绑定次数和 Fragment 相关计数器是否下降。

**压缩纹理和控制尺寸。** ASTC 适合现代 Android 设备上的高质量图片压缩，但收益需要按目标 SoC 验证。发布优化结论前，固定设备、刷新率、图片尺寸、滚动脚本和 thermal 状态，再对比 GPU frame time、Texture Unit / External Memory 计数器、视觉质量。只有 `dumpsys gfxinfo` 帧时间下降时，只能说明用户侧帧预算改善，不能单独证明带宽下降。

### 纹理格式验证模板

```bash
# 确认设备 ASTC 支持情况
adb shell cmd gpu vkjson | grep -A 5 -B 5 astc

# 采集同一滚动脚本的帧时间；带宽和纹理计数器需要 AGI 或厂商 profiler 补证。
adb shell dumpsys gfxinfo com.example.app framestats
```

### 举一反三

图片滚动里的 GPU 瓶颈常由多个小因素相加：过度绘制增加像素处理次数，纹理采样增加 Fragment Shader 成本，未压缩大图增加外部内存读取。单项修复可能只减少一小段耗时，但三项同时压住，GPU 才更容易回到帧预算内。没有配套 trace 时，正文只保留判断方法和验证条件，不写无法复核的收益数字。

## 与其他机制的关系

GPU 渲染属于 Android 渲染管线中的一环。理解 GPU 在管线中的位置,有助于我们在分析问题时快速定位责任方。

**VSync → GPU 的关系。** VSync 信号(详见 §2.3)定义了每一帧的时间预算。在 60Hz 屏幕上,每帧只有 16.67ms;在 120Hz 屏幕上,预算缩短到 8.33ms。GPU 必须在这个时间窗口内完成从接收渲染命令到输出像素的全部工作。如果 GPU 处理超时,帧就会被丢弃(掉帧)。

**Choreographer → GPU 的关系。** Choreographer(详见 §2.4)在 VSync-app 信号到来时触发 doFrame,驱动主线程完成 measure/layout/draw。主线程完成 draw 命令的录制后,RenderThread 将这些命令提交给 GPU。在 Perfetto 中,我们可以清楚地看到这个时序关系:Choreographer.doFrame → RenderThread.draw → GPU 渲染。

**MainThread/RenderThread → GPU 的关系。** 在 Android 12+ 的架构中(详见 §2.5),主线程负责录制 DisplayList(draw 命令列表),RenderThread 负责将 DisplayList 通过 Skia 转换为 GPU 命令并提交。GPU 渲染的开始时间取决于 RenderThread 何时完成命令提交,而 RenderThread 的提交又取决于主线程何时完成 draw 命令录制。任何一个环节的延迟都会推迟 GPU 开始工作的时间。

**SurfaceFlinger → GPU 的关系。** SurfaceFlinger(详见 §2.6)在 VSync-sf 信号到来时读取应用渲染好的缓冲区,将其与其他图层合成为最终图像。SurfaceFlinger 的合成操作本身也可能使用 GPU(GPU 合成路径),应用和 SurfaceFlinger 在某些时刻会因此竞争 GPU 资源。在 Perfetto 中,我们有时会看到应用的 GPU 渲染和 SurfaceFlinger 的 GPU 合成时间重叠,这就是 GPU 资源竞争的表现。

## 在 Perfetto 中的具体表现

在 Perfetto Trace 中,GPU 渲染相关的信息分布在多个 track 中,理解这些 track 的含义和它们之间的关系,是 GPU 性能分析的入门基础。

### GPU 相关 Track

**gpu_render_stages track。** 这是最核心的 GPU track,它显示了 GPU 在每个时间段执行的具体渲染阶段。在 Qualcomm Adreno 设备上,Vertex Shader、Fragment Shader 等阶段有明确标注;在 ARM Mali 设备上,对应的 track 可能以不同的名称出现。但需要注意,`gpu_render_stages` 的可用性和阶段粒度取决于设备 GPU 驱动是否暴露了 `GpuRenderStages` producer 数据--不是所有设备都能看到完整的 Vertex/Fragment 细分阶段。在 Perfetto 中如果该 track 为空或只显示笼统的"GPU"阶段,说明当前设备的驱动不支持 render stage 分级暴露。

**gpu_busy 计数器。** Android 16 统一了 GPU 利用率的追踪标准。Perfetto 中对应 track 路径为 `gpu_counters > gpu_busy`,与 GPU Headroom API(`SystemHealthManager.getGpuHeadroom()`)的区别在于:`gpu_busy` 是事后统计的利用率百分比,适合 Trace 分析;GPU Headroom 是运行时可查询的余量指标,适合应用内动态降级。两者可以交叉验证--如果 Perfetto 显示 `gpu_busy` 持续 >90%,应用侧的 GPU Headroom 应该接近 0。在此之前,不同 GPU 厂商的利用率计数器命名和语义各不相同--Adreno 设备上报 `GPU Busy` 百分比,Mali 设备使用不同名称的等效 counter,开发者需要根据设备型号选择不同的 Perfetto 轨道。Android 16 引入标准化的 `gpu_busy` 计数器标签,无论底层硬件是 Adreno、Mali 还是 Immortalis,Perfetto 都会以统一的轨道名称和百分比语义展示 GPU 利用率,开发者无需再关心 GPU 厂商差异即可直接读取准确的利用率百分比。

基于标准化轨道的快速瓶颈诊断法:在 Perfetto 中打开 `gpu_counters` track,找到 `gpu_busy` 轨道,如果利用率持续超过 90% 且对应帧的 RenderThread 出现等待状态,可以确认 GPU 是瓶颈。进一步结合 `gpu_render_stages`(如果可用)定位到具体渲染阶段--Vertex Shader 占比高指向几何复杂度问题,Fragment Shader 占比高指向像素处理量问题,两者都不高但整体 GPU 时间长则指向 bandwidth bound。

在 Android 15 及更早版本上,Perfetto 通过 `GpuCounterDescriptor` 描述每个 GPU 的 counter 模型,具体的 counter ID、名称和语义由 GPU 驱动的 producer 决定。如果设备不支持标准化 counter,仍然需要按厂商文档手动查找对应的利用率轨道。

**RenderThread track。** 虽然 RenderThread 是 CPU 侧的线程,但它的活动与 GPU 渲染直接相关。当 RenderThread 调用 `eglSwapBuffers()` 或 Vulkan 的 `vkQueuePresentKHR()` 提交帧时,如果 GPU 还没有完成上一帧的渲染,RenderThread 会被阻塞等待。在 Perfetto 中,这种等待表现为 RenderThread 上的长段 sleep/wait 状态--这通常意味着 GPU 是瓶颈。

**SurfaceFlinger track。** SurfaceFlinger 的活动显示了帧合成的时序。当 SurfaceFlinger 在 VSync-sf 时刻尝试读取应用的缓冲区时,如果应用还没有完成渲染(GPU 还在工作),SurfaceFlinger 只能使用上一帧的缓冲区--这就是掉帧在 Trace 中的直接表现。

**VSYNC-app 和 VSYNC-sf track。** 这两个 track 显示了 VSync 信号的时序。通过对比 VSYNC-app 的间隔和 GPU 渲染完成时间,我们可以判断 GPU 是否在 VSync 周期内完成了工作。

### 典型模式对比

**正常渲染模式:** VSYNC-app 到来后,主线程快速完成 doFrame(3-5ms),RenderThread 提交命令(1-2ms),GPU 完成渲染(5-8ms),整个流程在下一个 VSYNC-app 到来前完成。在 Trace 中,GPU track 的活动块整齐排列,每个块的长度都在帧预算以内。

**GPU 瓶颈模式:** GPU track 上的活动块长度超过 VSync 间隔(16.67ms@60Hz),RenderThread 在提交时被阻塞(显示为等待状态),SurfaceFlinger 在 VSYNC-sf 时刻取不到最新的帧。在 Trace 中,掉帧表现为 GPU activity 跨越了两个或更多 VSync 边界。

**Shader Compilation Jank 模式:** 在正常的 GPU 渲染序列中,突然出现一个特别长的 GPU 活动块(可能达到几十毫秒),之后恢复正常。这种"孤立的长帧"通常就是着色器编译导致的。在 Android 16+ 上,由于 SPIR-V 预编译的引入,这种模式会越来越少。

[待高爷补充:Perfetto Trace 截图--分别展示正常模式、GPU 瓶颈模式和 Shader Compilation Jank 模式的 GPU track 表现]

## 常见问题与误区

### "GPU 占用高 = 需要优化 GPU"?

不一定。GPU 占用高可能是正常的--比如一个全屏的游戏或视频应用,GPU 持续工作就是它的本职。只有当 GPU 占用高导致了可感知的用户体验问题(卡顿、发热、耗电过快)时,才需要优化。有时 "GPU 占用高" 只说明 GPU 没有被闲置;需要关注的是 "GPU 做了大量无用功" 的场景,比如严重的过度绘制。

### "过度绘制一定是问题"?

不一定。过度绘制是否成为问题取决于程度。Android 官方给出的参考标准是:1-2 次过度绘制通常可以接受,3 次及以上才需要认真优化。如果一个界面只有少量区域存在 3 次以上的过度绘制,而且不是滚动性能的关键路径,优化的优先级可以放低。过度绘制优化的重点是高频滚动区域、动画区域和全屏覆盖区域。

### "GPU 渲染一定比 CPU 渲染快"?

在大多数情况下是的--GPU 的并行计算能力远超 CPU,处理图形渲染任务有天然优势。但也有例外场景:当绘制内容非常简单(比如一个纯色矩形),GPU 渲染的固定开销(命令提交、状态切换、同步等待)可能反而比 CPU 直接写像素更慢。这就是为什么 Android 在某些情况下会回退到软件渲染路径。另一个容易忽略的点是 GPU 渲染会增加功耗--对于简单的 UI 操作,CPU 软件渲染可能更省电。

### "硬件加速解决一切渲染性能问题"?

硬件加速将大部分渲染工作从 CPU 卸载到了 GPU,但它并不能自动解决所有性能问题。硬件加速解决的是"渲染效率"问题(GPU 并行处理像素比 CPU 串行处理快),但它不解决"渲染工作量"问题--如果界面设计本身导致大量不必要的绘制操作,硬件加速只是让 GPU 更快地做无用功。而且硬件加速引入了一些 CPU 侧的新开销(Canvas 状态管理、DisplayList 录制),在某些极端场景下反而可能比软件渲染慢。

### "120Hz 屏幕需要 GPU 性能翻倍"?

这是一个常见的误解。120Hz 屏幕意味着每帧的预算从 16.67ms 缩短到 8.33ms,但这并不意味着 GPU 的工作量翻倍了--GPU 每帧的工作量取决于画面复杂度,与刷新率无关。变化的是时间预算:GPU 必须在更短的时间内完成同样的工作。在 120Hz 下,原本在 60Hz 下不明显的 GPU 瓶颈会变得突出。反过来,如果一个应用在 60Hz 下有 10ms 的 GPU 余量(GPU 只需要 6.67ms 就能完成渲染),升级到 120Hz 后只要 GPU 能在 8.33ms 内完成就仍然流畅。


## 参考资料

### 生产环境 GPU 性能问题调试方法论
- 来源:/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/DeepResearch/2026-05-11-gpu-performance-debugging-methodology.md
- 类型:DeepResearch 调研结果
- 摘要:系统性 GPU 性能调试方法论:Android 16 标准化 gpu_busy 计数器 vs 旧版厂商自定义命名差异、AGI 离线分析与 Perfetto 实时追踪的分工定位、Qualcomm Adreno 与 ARM Mali 的 counter 体系差异及统一方法论。包含从问题现象到根因的完整排查流程(CPU-GPU 同步 back-pressure、内存带宽、着色器编译)。
- 注入时间:2026-05-12
- 价值:提供了从问题现象到 GPU 根因定位的完整方法链,填补了现有章节缺少系统性排查流程的空白,Adreno vs Mali 差异对比对 OEM 场景尤为实用


### ARM Mali GPU TBR 架构原理与 Android 渲染性能影响
- 来源:/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/DeepResearch/ARM Mali GPU TBR 架构原理与 Android 渲染性能影响深度报告.md
- 类型:DeepResearch 调研结果
- 摘要:详述 ARM Mali GPU 从 Utgard 到第五代的 Tile-Based Rendering 演进:双阶段 Geometry+Fragment 流水线、on-chip tile memory 工作机制、AFBC 压缩、Transaction Elimination、Forward Pixel Kill、IDVS/DVS、Fragment Prepass、CSF 命令流前端。覆盖 Android 渲染栈 HWUI/RenderThread/SurfaceFlinger/HWC 与 Mali TBR 的交互,以及 Vulkan Render Pass load/store op 到 tile load/writeback 的映射。
- 注入时间:2026-04-29
- 价值:最完整的 Mali GPU TBR 架构与 Android 渲染栈交互文档,对 GPU 渲染性能分析与调优极具价值


### AOSP 源码路径
- `frameworks/native/libs/ui/include/ui/GraphicBuffer.h` - GraphicBuffer C++ 定义(AOSP)
- `frameworks/native/libs/nativewindow/include/android/native_window.h` - ANativeWindowBuffer 定义
- [ANGLE 源码(Google Git)](https://android.googlesource.com/platform/external/angle/) - ANGLE OpenGL ES on Vulkan
- `frameworks/native/vulkan/` - Vulkan API 支持
- `hardware/interfaces/graphics/allocator/aidl/` - Gralloc / Mapper AIDL 定义
- `frameworks/native/services/surfaceflinger/` - SurfaceFlinger 合成服务

### 官方文档
- GPU 概览:<https://developer.android.com/guide/topics/graphics/>
- OpenGL ES 开发指南:<https://developer.android.com/guide/topics/graphics/opengl>
- 硬件加速说明:<https://developer.android.com/guide/topics/graphics/hardware-acceleration>
- Android GPU Inspector (AGI):<https://developer.android.com/studio/profile/android-gpu-inspector>
- GPU 过度绘制调试:<https://developer.android.com/guide/topics/graphics/debug-overdraw>

### 工具和资源
- Snapdragon Profiler:<https://developer.qualcomm.com/software/snapdragon-profiler>
- ARM Streamline:<https://developer.arm.com/tools-and-software/streamline-performance-analyzer>

---

## 附录:GPU 源码调研补充材料

以下内容基于 AOSP 源码和 DeepResearch 调研补充,为正文「GPU 内存管理」和「GPU 性能问题系统性排查流程」提供源码级佐证。读者可按需参考。

<!-- AIW-源码调研-2026-05-04 -->
### A.1 GPU 内存管理与对象边界

### App 可见对象与系统内部图形缓冲对象的边界

通过分析 AOSP 源码,我们发现 App 可见对象与系统内部图形缓冲对象之间的边界比表面看起来更复杂。Surface 本身不直接保存这些缓冲,它委托给 BufferQueue 生产者接口,后者管理着 64 个 BufferSlot 的池。

**BufferSlot 状态机实现:**
```cpp
// frameworks/native/libs/gui/include/gui/BufferSlot.h
struct BufferState {
    uint32_t mDequeueCount;
    uint32_t mQueueCount;
    uint64_t mAcquireCount;
    bool mShared;

    inline bool isFree() const { return !isAcquired() && !isDequeued() && !isQueued(); }
    inline bool isDequeued() const { return mDequeueCount > 0; }
    inline bool isQueued() const { return mQueueCount > 0; }
    inline bool isAcquired() const { return mAcquireCount > 0; }
    inline bool isShared() const { return mShared; }
};
```

关键认知在于 BufferSlot 使用计数器而非简单的枚举状态,以适应共享缓冲区模式。一个槽可以同时处于多种状态(例如 shared + dequeued),这与常见的"三缓冲"理解有本质区别。

### 内存分配的演进:ION 到 DMA-BUF Heaps

内存分配经历了从 Android 4.x-11 的 ION 分配器到 Android 12+ 的 DMA-BUF Heaps 的演进:

- **Android 4.x-11 (ION 时代)**:使用 Android 自定义 ION 分配器,所有进程访问同一设备节点
- **Android 12+ (DMA-BUF Heaps)**:使用 Linux 上游 DMA-BUF Heaps,支持细粒度访问控制

```cpp
// frameworks/native/libs/gui/BufferQueueProducer.cpp
// @ AOSP android-16.0.0_r1
// [简化骨架] 实际函数签名:
//   status_t waitForFreeSlotThenRelock(
//       FreeSlotCaller caller,
//       std::unique_lock<std::mutex>& lock,
//       int* found) const
// 返回 NO_ERROR / WOULD_BLOCK / TIMED_OUT;slot 通过 *found 输出
status_t BufferQueueProducer::waitForFreeSlotThenRelock(
        FreeSlotCaller caller, std::unique_lock<std::mutex>& lock,
        int* found) const {
    // 1. 统计当前 dequeued / acquired 数量
    // 2. 检查是否超过 mMaxDequeuedBufferCount
    // 3. 遍历 mSlots 找空闲 buffer 或可复用 slot
    // 4. 无可用 slot → 根据调用者类型决定:
    //    - dequeue 阻塞等待条件变量(支持超时)
    //    - attach 直接返回 WOULD_BLOCK
    // 5. 找到后通过 *found 输出 slot 索引,返回 NO_ERROR
}
```

这种演进带来了更好的安全性和稳定性,但对应用层透明,理解分配底层有助于排查内存泄漏问题。


### RenderEffect 底层 GPU 渲染管线与 offscreen buffer 机制
- 来源:/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/DeepResearch/2026-05-09-rendereffect-gpu-pipeline-offscreen-buffer.md
- 类型:DeepResearch 调研结果
- 摘要:RenderEffect 映射到 Skia 的 SkImageFilter 链,触发 offscreen GPU texture 分配(RenderLayer)。分析了 Java API → JNI → Skia GPU pipeline 的完整路径,blur sigma 值与 shader 计算量关系,AGSL RuntimeShader 通过 makeImageSnapshot() 触发 offscreen buffer 分配的机制。性能代价来自显存申请、filter chain GPU pass 数、RenderThread-GPU 同步三方面。
- 注入时间:2026-05-10
- 价值:RenderEffect 到 Skia 底层的完整链路分析,包含 offscreen buffer 触发条件和性能代价量化,对 GPU 渲染深入章节有直接补充价值

### A.2 GPU 性能问题系统性排查流程

### 方法论缺口与补全

§2.10 已覆盖 GPU 渲染管线原理、瓶颈分类(fillrate/vertex/bandwidth bound)、GPU Headroom API(Android 16)、AGI/Snapdragon Profiler/ARM Streamline 工具介绍。但缺少一条**从问题现象到根因定位的完整方法链**。本节补全三个能力缺口:Perfetto GPU 计数器解读标准、AGI 生产环境可用性评估、以及厂商调试工具链差异下的方法论统一。

### Perfetto GPU 计数器:Android 16 标准化 vs 旧版厂商自定义

#### Android 16 的标准化 `gpu_busy`

Android 16 引入了标准化的 `gpu_busy` 计数器,路径为 `gpu_counters > gpu_busy`。数值范围 0-100%,表示 GPU 利用率。数据源来自 `GpuCounterDescriptor`--GPU 驱动注册到 Perfetto 的 counter descriptor,其中 `gpu_busy` 是 Android 16 要求所有厂商必须提供的标准别名。

```protobuf
// Perfetto GPU counter 配置示意
// 路径: perfetto/config/gpu/gpu_counter_config.proto
message GpuCounterConfig {
  uint32 counter_period_ns = 1;   // 采样周期,默认 1ms
  repeated uint32 counter_ids = 2; // 厂商定义的 counter ID 列表
  string gpu_id = 3;               // 指定 GPU 设备
}
```

在 Perfetto Trace 中读取 `gpu_busy`:
1. 打开 `gpu_counters` track
2. 找到 `gpu_busy` 轨道(无论底层是 Adreno 还是 Mali,均使用此统一名称)
3. 数值 0-100%

#### Android 15 及更早版本的厂商自定义 counter

在 Android 15 及更早版本上,不同厂商的 counter 语义差异很大:

| GPU 厂商 | 利用率 counter 常见名称 | 含义 |
|----------|------------------------|------|
| Qualcomm Adreno | `GPU Busy` / `GPU Utilization` | GPU 执行指令的时间占比 |
| ARM Mali | 无单一 `gpu_busy`,看 `Fragment Processing Active` / `Vertex Shader Active` | 特定阶段活跃度 |
| Imagination PowerVR | `GX Busy` / `Render Active` | GPU Graphite 引擎活跃度 |

Perfetto 中这些 counter 以厂商注册的原始名称出现,不会以统一名称出现。排查 Android 15 设备时:
1. 通过 `dumpsys gfxinfo` 或 `adb shell getprop ro.hardware` 确认 GPU 型号
2. 根据 GPU 型号查阅对应厂商文档(Adreno GPU Profiler Guide / Mali GPU Best Practices)
3. 在 Perfetto 的 `gpu_counters` track 中找到对应的 counter

#### 不区分厂商的快速诊断流程

无论哪个 Android 版本:

1. 打开 `gpu_counters` track
2. 找 `gpu_busy`(Android 16)或厂商特定的利用率 counter
3. 如果持续 >90% 且对应 RenderThread 出现等待状态 → GPU 瓶颈确认
4. 如果可用,打开 `gpu_render_stages` track,看 Vertex/Fragment 阶段占比
5. Fragment 高 → fillrate bound;Vertex 高 → vertex bound;两者都不高但 GPU 时间长 → bandwidth bound

### Android GPU Inspector(AGI):开发阶段 vs 生产环境

#### AGI 的能力边界

AGI 是一个**离线分析工具**,工作模式:
1. 用 `adb record` 或 AGI 界面手动录制一个 GPU Trace(通常几秒)
2. 保存为 `.gpitrace` 文件
3. 在 AGI 桌面应用中打开分析

使用边界如下:
- **AGI 不能用于实时生产监控**:无法在已上线应用上持续监控 GPU 状态
- **AGI 适合开发阶段和预发布测试**:在受控环境中录制典型场景的 GPU Trace,再做深度分析
- **AGI 需要可复现的场景**:GPU 问题偶发还是稳定,决定录制策略

#### AGI vs Perfetto:分工定位

| 维度 | AGI | Perfetto |
|------|-----|----------|
| 录制方式 | 独立录制(.gpitrace) | 系统级持续追踪 |
| 实时性 | 离线分析 | 可实时/历史回放 |
| GPU 计数器深度 | 深(Adreno/Mali 原生 counter) | 浅(标准 counter 子集) |
| 着色器分析 | 支持源码级着色器耗时 | 不支持 |
| 生产环境可用性 | 低(需要主动录制) | 高(系统级持续采集) |

分工建议:
- **开发阶段**:用 AGI 对典型场景做深度 GPU 分析(着色器热点、draw call 分布、内存带宽使用)
- **生产环境问题定位**:先用 Perfetto 的 `gpu_busy` 确认 GPU 是否为瓶颈,再用 AGI 对复现的场景做离线深度分析

#### AGI 录制触发方式

AGI 支持两种触发方式:
1. **手动触发**:通过 AGI 界面手动开始/停止录制
2. **Intent 触发**:通过 `am broadcast` 或 `adb shell am start` 带着特定 flag 触发录制

对于偶发的生产环境问题,Intent 触发方式更有用:

```bash
# 通过 Intent 触发 AGI 录制(示例,实际参数因 AGI 版本而异)
adb shell am start -n com.google.android.gpiinspector/.RecordingActivity \
  -e recording_duration 5000 \
  -e output_path /sdcard/gpu_trace.gpitrace
```

录制完成后,通过 `adb pull` 将文件拉到本地用 AGI 分析。

### Qualcomm Adreno vs ARM Mali:调试特性差异与方法论统一

#### Adreno GPU 调试特性

Qualcomm Adreno GPU 的性能计数器体系:
- `GPU Active` - GPU 核心处于活跃状态的时间
- `Fragment Active` - Fragment Shader 执行时间
- `Vertex Active` - Vertex Shader 执行时间
- `RAM` - 显存带宽使用(read/write 分开)
- `TLB Miss` - TLB 未命中次数(高表示内存访问效率低)

Adreno 的特点:
- **GPU 时间线分层**:`CP`(Command Processor)、`RBC`(Render Backend Complex)、`UCHE`(Unified Cache)等阶段各自独立计数
- **带宽 counter 丰富**:Adreno 提供较完整的 `VRAM Read/Write` 计数器,适合分析 bandwidth bound 问题
- **Snapdragon Profiler**:Qualcomm 官方工具,提供比 Perfetto 更细粒度的 Adreno 特定 counter

```bash
# 查看 Adreno GPU 可用 counter(需要 root)
adb shell cat /d/dri/0/counters/all
```

#### Mali GPU 调试特性

ARM Mali GPU(TBR 架构)的性能计数器体系:

Mali 的 counter 命名与 Adreno 不同,但分析思路一致:
- `Fragment Processing` - Fragment 处理阶段活跃度(对应 TBR 的 tile 着色阶段)
- `Tiled Rendering` - 瓦片渲染活跃度
- `Transaction Eliminated` - Transaction Elimination 命中次数(表示带宽节省)
- `AFBC payload` - AFBC 压缩带来的带宽节省量

Mali 的 `gpu_render_stages` 在 Perfetto 中通常比 Adreno 更细粒度--ARM 设计了自己的 `GpuApplicationTrace` 框架,让 Perfetto 可以拿到 Vertex/Fragment/Tiler 等阶段时间。

#### 方法论统一:厂商差异屏蔽

无论哪个厂商,以下方法论是通用的:

**第一步:确认 GPU 是否为瓶颈**
- Perfetto `gpu_busy` 或厂商利用率 counter >90%
- RenderThread 出现等待状态(等待 GPU 完成上一帧)

**第二步:定位瓶颈类型**
- 打开 `gpu_render_stages`(如果可用)
- Fragment 高 → fillrate bound:检查 overdraw、shader 复杂度、纹理格式
- Vertex 高 → vertex bound:检查几何复杂度、path 数量、矩阵变换
- 两者不高但 GPU 总时间长 → bandwidth bound:检查纹理压缩率、带宽 counter

**第三步:深度分析(用厂商工具)**
- fillrate bound:用 AGI 或 Adreno Profiler 看 Fragment Shader 的纹理采样次数、overdraw 热力图
- bandwidth bound:用厂商 counter 看 VRAM 带宽使用率,找高带宽纹理
- vertex bound:用 AGI 的几何分析看顶点数量分布

**第四步:修复 + 验证**
- 修复后用 Perfetto 确认 GPU 时间下降
- 用 AGI 确认修复后的指标(shader 时间、带宽等)已经改善

### 系统性排查流程:CPU-GPU 同步 / 内存带宽 / 着色器编译

#### 完整排查流程

```text
问题现象:掉帧 / 卡顿 / 发热
    │
    ├─ 主线程 doFrame 耗时正常
    │     ├─ RenderThread 提交快,GPU track 长 → GPU 瓶颈
    │     └─ RenderThread 提交阻塞 → GPU 未完成上一帧(back-pressure)
    │
    ├─ 主线程 doFrame 耗时异常
    │     └─ 主线程是瓶颈,不是 GPU 问题
    │
    └─ 孤立长帧(偶发)
          └─ Shader Compilation Jank(Android 16+ 因 SPIR-V 预编译减少)
```

#### 维度一:CPU-GPU 同步(back-pressure)

当 GPU 处理一帧的时间超过 VSync 周期时,RenderThread 在 `eglSwapBuffers()`(GLES)或 `vkQueuePresentKHR()`(Vulkan)处等待。这个等待在 Perfetto 中表现为 RenderThread 的长段 sleep。

源码级来源:
- OpenGL ES:`eglSwapBuffers()` 内部会等待上一个 framebuffer 的 release fence
- Vulkan:`vkQueuePresentKHR()` 的 `VkFence` 同步

如果 RenderThread 等待时间持续超过帧预算的 50%,说明 GPU 是瓶颈而非 CPU。

#### 维度二:内存带宽

带宽瓶颈的特点:着色器执行时间不长,但整体 GPU 时间超标。Perfetto 的内存带宽 counter(如果有)会显示高负载。

优化方向:
- ASTC 纹理压缩格式(相比 ETC2 在同压缩比下视觉质量更优,带宽节省更显著)
- 生成 Mipmap(让 GPU 根据物体大小选择纹理分辨率,避免过采样)
- 减少每像素纹理采样次数

#### 维度三:着色器编译

Shader Compilation Jank 的特征:偶发长帧(可能达到几十毫秒),之后恢复正常。Android 16 的 SPIR-V 预编译大幅减少了这个问题,但对于仍在使用 OpenGL ES 的应用,ANGLE 层仍然存在编译开销。

诊断方法:
- 在 Perfetto 中找"孤立的长 GPU 活动块"--正常渲染序列中突然出现一个特别长的帧
- 检查这个长帧是否对应用户刚触发的新 UI 效果(新页面、动画、模糊效果等)
- Android 16+ 通过 SPIR-V 预编译减少了这个问题,但 OpenGL ES 应用仍可能通过 ANGLE 遇到

> [源码: perfetto/dev/docs/data-sources/gpu; gpuinspector.dev; ARM Mali GPU Best Practices; Qualcomm Adreno GPU Profiler Guide] **[一手:Perfetto 官方文档 + AGI 官方文档 + 厂商官方文档]**

<!-- /AIW-源码调研-2026-05-11 -->
