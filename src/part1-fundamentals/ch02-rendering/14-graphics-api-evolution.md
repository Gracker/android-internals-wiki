---
title: "图形 API 演进与选择策略（OpenGL ES / Vulkan / ANGLE）"
chapter: "2.14"
status: ready-for-review
drafted_date: "2026-04-05"
drafted_by: "openclaw-task2a"
applicable_versions: "Android 4.0 (API 14) - Android 17 (API 37)"
last_verified: "2026-04-05"
last_verified_against: "AOSP android-17-beta3"
confidence: medium
sources:
  - type: official
    path: "https://developer.android.com/ndk/guides/graphics"
  - type: official
    path: "https://source.android.com/docs/core/graphics/angle"
  - type: blog
    path: "https://android-developers.googleblog.com/"
  - type: aosp
    path: "platform/external/angle"
tags: [opengl-es, vulkan, angle, gpu, graphics-api, rendering]
related_chapters: ["2.1", "2.9", "2.10", "14.8"]
section: "2.14"
---

# 2.14 图形 API 演进与选择策略（OpenGL ES / Vulkan / ANGLE）

我们在 §2.1 中看到了 Android 渲染架构的全景，在 §2.9 中了解了渲染管线从 HWUI 到 SkiaVulkan 的演进，在 §2.10 中分析了 GPU 渲染的深入机制。但有一个维度一直没有展开：当我们要写一个游戏引擎、一个视频滤镜、或者一个需要直接操作 GPU 的应用时，应该选择哪个图形 API？OpenGL ES、Vulkan、还是等 ANGLE 帮我们翻译？这个选择在今天变得前所未有的重要，因为 Android 17 正在把 OpenGL ES 推入维护模式，ANGLE 成为所有 GLES 应用的默认路径。

理解图形 API 的演进脉络和架构差异，不只是"选对工具"的问题。在 Perfetto 中看到 GPU activity slice 时，我们需要知道它是 Vulkan 提交还是 GLES 通过 ANGLE 翻译后提交的；分析帧时间抖动时，需要判断瓶颈是 API 翻译层的开销还是驱动实现的质量问题。

## Android 图形 API 的三代演进

Android 从诞生到现在，GPU 编程接口经历了三代更迭。这个演进不是跳跃式的替换，而是一个长达十余年的渐进迁移过程。

### 第一代：OpenGL ES——移动 GPU 的起点

OpenGL ES（OpenGL for Embedded Systems）是 Khronos Group 为嵌入式设备制定的图形 API 标准。Android 从 1.0 版本就支持 OpenGL ES 1.0/1.1，但真正让 GPU 渲染成为主流的是 OpenGL ES 2.0——它带来了可编程着色器（vertex shader 和 fragment shader），从固定功能管线转向了可编程管线。

Android 各版本对 OpenGL ES 的支持时间线：

| OpenGL ES 版本 | 引入的 Android 版本 | API Level | 关键能力 |
|---|---|---|---|
| 1.0 / 1.1 | Android 1.0 | API 1 | 固定功能管线，基本 2D/3D |
| 2.0 | Android 2.2 (Froyo) | API 8 | 可编程着色器（GLSL ES），现代 GPU 编程的起点 |
| 3.0 | Android 4.3 (JB MR2) | API 18 | 多重渲染目标（MRT）、Transform Feedback、实例化绘制 |
| 3.1 | Android 5.0 (Lollipop) | API 21 | Compute Shader、独立着色器对象 |
| 3.2 | Android 7.0 (Nougat) | API 24 | Android Extension Pack 正式标准化 |

[已验证: 官方文档, developer.android.com/guide/topics/graphics/opengl]

OpenGL ES 2.0 是一个分水岭。在它之前（ES 1.x），开发者只能用固定功能管线：告诉 GPU "画一个三角形、贴一张纹理、加一个光源"，GPU 按预定义的流程执行。ES 2.0 引入了 GLSL ES 着色器语言，开发者可以自己写代码控制 GPU 的顶点处理和片段着色阶段。这打开了移动端 GPU 的真正潜力——后处理滤镜、水面反射、粒子系统都成为可能。

ES 3.0/3.1/3.2 在 ES 2.0 的基础上逐步添加了更高级的 GPU 特性：多重渲染目标允许一次绘制输出多张纹理（延迟渲染的基础）、Compute Shader 让 GPU 执行通用计算、实例化绘制减少了 draw call 数量。

但 OpenGL ES 有一个根本性的架构限制：它是一个**状态机模型**。每次调用 `glBindTexture()`、`glBlendFunc()`、`glDrawArrays()` 时，都在改变一个全局状态机的状态。驱动需要在每次 draw call 时检查完整的状态组合是否合法、是否需要重新编译着色器、是否需要同步 CPU 和 GPU——这些都在调用线程上同步完成。这个设计在高 draw call 数量的场景下会成为严重的 CPU 瓶颈。

### 第二代：Vulkan——显式控制的现代 API

Vulkan 同样由 Khronos Group 制定，2016 年发布 1.0 版本。与 OpenGL ES 的"驱动替你做决定"不同，Vulkan 的设计哲学是"开发者自己控制一切"：内存分配、命令提交时机、GPU/CPU 同步策略、管线状态——全部由应用显式指定。

Android 对 Vulkan 的支持时间线：

| Vulkan 版本 | 强制要求的 Android 版本 | 关键能力 |
|---|---|---|
| 1.0 | Android 7.0 (可选) | 显式 API、Command Buffer、多线程渲染 |
| 1.1 | Android 10 (64 位设备强制) | subgroup 操作、YCbCr 转换、多视图渲染 |
| 1.3 | Android 13 (新设备强制) | 动态渲染（无 RenderPass）、同步 2.0、内联 uniform block |
| 1.4 | Android 17 (新设备强制) | 简化的管线创建、scalar block layout、额外内存特性 |

[已验证: 官方文档, developer.android.com/ndk/guides/graphics]

Vulkan 1.0 就已经提供了 OpenGL ES 不具备的核心能力：Command Buffer 允许多线程并行构建 GPU 命令、显式内存管理让应用控制 GPU 内存的分配和回收时机、Pipeline State Object（PSO）将着色器和渲染状态预编译为一个不可变对象，避免了运行时的状态验证开销。

但 Vulkan 1.0 的 API 复杂度极高。创建一个"画一个三角形"的最小 Vulkan 程序需要约 800 行代码——同样的功能在 OpenGL ES 中只需要不到 100 行。Vulkan 1.1/1.3/1.4 的迭代本质上是在降低这个复杂度：Vulkan 1.3 的动态渲染让开发者不再需要显式定义 RenderPass 对象，Vulkan 1.4 进一步简化了管线创建流程。

Android 17 强制要求新设备支持 Vulkan 1.4，同时定义了 **Android Vulkan Profile 2025 (AVP 2025)**——这是一个 Vulkan 扩展和特性的标准集合，确保所有 Android 设备提供一致的 GPU 能力基线。AVP 2025 包含了额外内存特性、细粒度浮点控制、GPU query 重置、标准化像素格式等扩展。

[已验证: 官方文档, source.android.com/docs/core/graphics/angle]

### 第三代：ANGLE——翻译层，不是新 API

严格来说，ANGLE（Almost Native Graphics Layer Engine）不是一个独立的图形 API，它是一个**翻译层**：接收 OpenGL ES API 调用，将其翻译为 Vulkan（或 macOS/iOS 上的 Metal）调用。

ANGLE 的定位可以用一句话概括：它让 OpenGL ES 应用无需修改代码就能跑在 Vulkan 上。

Google 的策略是分阶段推进：

| Android 版本 | ANGLE 策略 | 含义 |
|---|---|---|
| 12 ~ 14 | 开发者可选 opt-in | 仅特定应用主动启用 |
| 15 | 扩展 opt-in | 更多应用可以选用 |
| 16 | 新设备 allowlist | 特定应用强制使用 ANGLE |
| **17** | **新设备 denylist** | **所有应用默认使用 ANGLE，仅排除列表中的应用使用原生 GLES 驱动** |

[已验证: 官方文档, developer.android.com/about/versions/17]

注意关键细节：Android 17 的 denylist 策略仅对**新设备**生效。旧设备升级到 Android 17 不受此强制约束。所谓 denylist 是指"不在排除名单中的应用都走 ANGLE"，与之前的 allowlist（"在名单中的应用才走 ANGLE"）正好相反。

## Vulkan 与 OpenGL ES 的架构差异

理解这两种 API 的架构差异，不只是理论问题。当我们在 Perfetto 中分析 GPU activity 时，看到的 slice 行为、时间分布和抖动模式都跟底层 API 的架构选择直接相关。

### 状态机 vs 显式命令

OpenGL ES 是一个全局状态机。以下伪代码展示了典型的 OpenGL ES 绘制流程：

```cpp
// OpenGL ES 绘制流程——全局状态机模式
glBindTexture(GL_TEXTURE_2D, textureA);    // 绑定纹理
glUniform1f(uAlphaLoc, 0.5f);              // 设置 uniform
glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA);  // 混合模式
glDrawArrays(GL_TRIANGLES, 0, vertexCount); // 提交绘制——驱动在此做完整状态验证
```

每次 `glDrawArrays()` 被调用时，OpenGL ES 驱动需要做以下工作（全部在调用线程上同步完成）：

1. **状态验证**：检查当前的纹理、着色器、混合模式、帧缓冲等状态组合是否合法
2. **状态追踪**：将应用设置的状态映射到 GPU 硬件寄存器
3. **资源同步**：确认 GPU 是否还在使用上一次提交的资源
4. **错误检查**：在 Debug 模式下进行完整的参数验证

这个过程在简单的场景下不是问题，但当 draw call 数量达到数百甚至数千（复杂 UI、游戏场景），CPU 侧的驱动开销就会成为帧时间的瓶颈。实测数据表明，一个 OpenGL ES 的 draw call 的 CPU 侧开销通常在 10-50μs，而同样的操作在 Vulkan 中只需要 1-5μs——差距达一个数量级。

[来源: ARM GPU Best Practices, developer.arm.com]

Vulkan 的做法完全不同。它没有全局状态机，取而代之的是不可变的 **Pipeline State Object（PSO）**：

```cpp
// Vulkan 绘制流程——显式命令模式
// 1. 预先创建 Pipeline（一次性开销，通常在加载时完成）
VkGraphicsPipelineCreateInfo pipelineInfo = {
    .stageCount = 2,
    .pStages = shaderStages,        // 着色器阶段
    .pVertexInputState = &vertexInputState,  // 顶点输入
    .pRasterizationState = &rasterState,     // 光栅化
    .pColorBlendState = &blendState,         // 混合状态
};
vkCreateGraphicsPipelines(device, pipelineCache, 1, &pipelineInfo, NULL, &pipeline);

// 2. 录制命令到 Command Buffer（可在任意线程）
vkCmdBindPipeline(cmdBuffer, VK_PIPELINE_BIND_POINT_GRAPHICS, pipeline);
vkCmdBindDescriptorSets(cmdBuffer, ..., descriptorSet);  // 绑定资源
vkCmdDraw(cmdBuffer, vertexCount, 1, 0, 0);  // 提交绘制——无需状态验证

// 3. 提交 Command Buffer 到 GPU（在主线程）
vkQueueSubmit(graphicsQueue, 1, &submitInfo, fence);
```

关键区别在于：Vulkan 将状态验证的工作从"每次 draw call 时做"移到了"创建 Pipeline 时做一次"。`vkCmdDraw()` 本身只是一个轻量级的命令记录操作——往 Command Buffer 里追加一条指令，不涉及任何 GPU 交互或状态检查。

### 多线程渲染

OpenGL ES 的全局状态机设计导致它本质上是一个单线程 API。虽然可以通过 EGL 共享上下文在多个线程中使用 OpenGL ES，但状态机的全局性使得多线程同时操作 GL 上下文需要大量的锁同步，实际收益有限。

Vulkan 的 Command Buffer 天然支持多线程。不同的线程可以各自独立地构建 Command Buffer，最后在一个线程上统一提交：

```
线程 A: 构建 Command Buffer (场景渲染命令)
线程 B: 构建 Command Buffer (UI 覆盖层命令)
线程 C: 构建 Command Buffer (后处理命令)
   ↓
主线程: vkQueueSubmit(A + B + C) → 一次性提交到 GPU
```

在 Perfetto 中，如果应用使用 Vulkan 的多线程命令构建，我们可以在多个线程的 track 上同时看到 GPU 命令的录制活动，而最终的 `vkQueueSubmit` 只在提交线程上出现一个很短的 slice。

### Command Buffer 复用

OpenGL ES 没有命令缓冲区的概念——每次绘制都是"即时的"（虽然驱动内部可能做批处理，但开发者无法控制）。Vulkan 的 Command Buffer 可以在帧之间复用：如果一帧的渲染命令没有变化（比如静态 UI），只需要在第一帧录制 Command Buffer，后续帧直接重新提交即可。

这个特性对 UI 渲染特别有价值。Android 的 View 系统在 UI 没有变化时不会重新走一遍 measure/layout/draw 流程，但 GPU 命令仍然需要提交。如果使用 Vulkan 的 Command Buffer 复用，静态 UI 的帧提交开销几乎为零。

## ANGLE 的角色与 Android 17 强制迁移

### ANGLE 的翻译架构

ANGLE 在 AOSP 中的源码路径为 `platform/external/angle`，其核心翻译流程如下：

```
App 的 GLES 调用
    ↓
GLES 入口函数 (eglMakeCurrent, glDrawArrays, ...)
    ↓
验证层（Validation Layer）—— 检查 API 使用是否合法
    ↓
状态追踪层（State Tracking）—— 维护 OpenGL ES 的状态机
    ↓
Vulkan 后端（src/libANGLE/renderer/vulkan/）
    ├─ vk::Renderer —— 管理 VkDevice, VkQueue, 格式表, 内部着色器
    ├─ ContextVk —— 处理 OpenGL Context 的状态变更和命令执行
    └─ Pipeline 缓存 —— 将 OpenGL 状态向量映射到 Vulkan PSO
    ↓
Vulkan 驱动 → GPU
```

[已验证: AOSP 源码, platform/external/angle, src/libANGLE/renderer/vulkan/]

ANGLE 的翻译不是简单的 API 映射。最复杂的部分是**状态转换**：OpenGL ES 的"随时改变状态"模型需要被翻译为 Vulkan 的"预编译 Pipeline"模型。ANGLE 内部维护了一个状态向量到 Vulkan PSO 的哈希映射表——当应用改变了 OpenGL ES 状态时，ANGLE 会查找是否已经有匹配的 Vulkan Pipeline，如果没有就创建一个新的。

这意味着 ANGLE 引入的额外开销主要来自两方面：

1. **GLSL ES 到 SPIR-V 的着色器翻译**：ANGLE 内置了一个着色器编译器，将 GLSL ES 源码翻译为 Vulkan 使用的 SPIR-V 二进制格式。这个翻译发生在着色器首次编译时，之后会被缓存
2. **状态追踪和 Pipeline 查找**：每次 GLES draw call 都需要在哈希表中查找匹配的 Vulkan Pipeline，如果未命中则创建新的 Pipeline（这个创建过程本身是耗时的）

### ANGLE 的性能实测

Google 在多个公开场合（Google I/O、Android Dev Summit）展示了 ANGLE 的性能数据。对于大多数应用来说，ANGLE 的性能影响在可接受范围内：

| 应用类型 | ANGLE 性能开销 | 说明 |
|---|---|---|
| 2D UI 应用 | 2-5% | 简单的 GLES 操作，翻译开销极小 |
| 3D 游戏（中等复杂度） | 5-10% | 更多的着色器和状态切换 |
| 合成基准测试 | 10-20% | 极端场景，大量状态切换 |

[来源: Google I/O 技术演讲及社区基准测试，非官方系统性基准数据，具体数值可能因设备和驱动版本而异]

有意思的是，部分游戏通过 ANGLE 运行反而比原生 GLES 驱动更快。原因是某些 GPU 厂商的原生 GLES 驱动实现质量较差（这也是 Google 推 ANGLE 的根本原因之一），而 ANGLE→Vulkan 路径绕过了这些问题驱动代码。

ANGLE 还带来了一个间接的优化：Pipeline Cache。Vulkan 支持将编译好的 Pipeline 序列化到磁盘，下次启动时直接加载，避免了运行时的 Pipeline 创建开销。社区测试（如 Fortnite Mobile）显示，加载 Pipeline Cache 可以将 Pipeline 创建的平均耗时降低 95%。ANGLE 作为系统级服务，可以为所有 GLES 应用统一管理 Pipeline Cache。

[来源: ARM GPU Best Practices, developer.arm.com]

### Android 17 ANGLE 强制化的实际影响

对于开发者来说，Android 17 的 ANGLE denylist 策略意味着：

1. **不需要修改代码**：GLES 应用自动通过 ANGLE 运行，API 行为不变
2. **性能可能略有变化**：大多数场景持平或略慢，少数场景可能反而更快
3. **调试方式改变**：使用 ANGLE 后，GPU activity 在 Perfetto 中会通过 Vulkan 路径呈现，而不是 GLES 路径
4. **驱动 bug 表现可能变化**：原来在原生 GLES 驱动上的 bug 在 ANGLE→Vulkan 路径上可能出现不同的表现

需要特别注意的是：WebView 和 WebGL 仍然走 GLES 路径。WebView 内部的渲染引擎（Skia）有自己的 GPU 后端选择逻辑，ANGLE 的系统级策略不会直接干预 WebView 内部的图形 API 选择。

## API 选择对渲染性能的实际影响

### 隐式优化 vs 显式控制

OpenGL ES 的驱动会替开发者做很多"隐式优化"——自动合并 draw call、在后台编译着色器、预取纹理、调整 GPU 频率。这些优化让开发者用更少的代码获得不错的性能，但也意味着：不同厂商的驱动优化策略不同，同一个应用在不同设备上的性能表现可能差异巨大。这正是 Android GPU 碎片化问题的根源。

Vulkan 则要求开发者自己做这些优化。它不会替你合并 draw call、不会自动预编译着色器、不会隐式同步 CPU 和 GPU。如果开发者不主动管理 Pipeline Cache、不预创建 Pipeline、不做正确的同步，Vulkan 的性能可能比 OpenGL ES 更差。但反过来，如果开发者做对了这些优化，Vulkan 可以提供 OpenGL ES 无法达到的性能上限。

这个权衡可以总结为：**OpenGL ES 的性能下限高、上限低；Vulkan 的性能下限低、上限高。**

### 游戏引擎的 API 选择

主流游戏引擎的 API 选择策略：

| 引擎 | 默认 API | 策略 |
|---|---|---|
| Unity | Vulkan (Android) | 2020+ 默认 Vulkan，GLES 作为 fallback |
| Unreal Engine | Vulkan | Android 平台仅 Vulkan（ES3.2 作为降级备选） |
| Godot | Vulkan (4.x) / GLES (3.x) | 4.x 默认 Vulkan Clustered，GLES 兼容模式可选 |

[已验证: Unity 2020+ release notes, Unreal Engine 5 Android requirements, Godot 4.x documentation]

对于使用游戏引擎的开发者，通常不需要关心底层 API 选择——引擎已经做好了适配。但如果开发自定义渲染引擎或需要极致性能的场景（AR/VR、实时视频处理），直接使用 Vulkan 是更好的选择。

## 图形 API 与 Perfetto / 工具分析

### 在 Perfetto 中识别图形 API

在 Perfetto Trace 中，我们可以通过以下方式判断应用使用的图形 API：

1. **GPU Activity Track**：Vulkan 提交的 GPU 工作通常标记为 `vkQueueSubmit` 相关的 slice；GLES 提交则可能显示为 `gles*` 或通过 ANGLE 显示为 `vk*` slice
2. **GPU Counter Track**：启用 `gpu.counters` 数据源后，可以看到 GPU 频率、利用率和内存带宽等指标。不同 API 的 GPU counter 可用性不同
3. **进程级信息**：检查进程加载的共享库——加载 `libvulkan.so` 表示使用 Vulkan，加载 `libGLESv2.so` 表示使用 OpenGL ES，两者都加载则可能使用 ANGLE

GPU counter 的配置方式（在 TraceConfig 中）：

```protobuf
// Perfetto TraceConfig GPU counter 配置
data_sources {
    config {
        name: "gpu.counters"
        gpu_counter_config {
            counter_ids: [1, 2, 3]  // 按需选择 GPU counter ID
            sampling_period_ns: 1000000  // 1ms 采样间隔
        }
    }
}
```

Vulkan 通常提供比 GLES 更丰富的 GPU 性能计数器，包括 per-stage 的 GPU 利用率（顶点/片段/Compute）、精确的显存带宽计量、以及 GPU cache 命中率等。这些计数器的可用性取决于 GPU 厂商和驱动实现。

[待补充: Perfetto 中 Vulkan vs GLES 的 GPU Activity slice 截图对比]

### AGI 与不同 API 的兼容性

Android GPU Inspector（AGI）是 Google 官方的 GPU 分析工具（详见 §14.8）。AGI 的 API 支持情况：

- **Vulkan 应用**：AGI 直接捕获和分析 Vulkan 调用，支持逐 draw call 的 GPU 时间分析
- **OpenGL ES 应用**：AGI 通过自定义的 ANGLE build 将 GLES 命令翻译为 Vulkan 进行追踪。这意味着即使是 GLES 应用，AGI 也是通过 Vulkan 路径来分析
- **AGI 2026 路线图**：改进版 System Profiler（2026 H1，支持超大 trace、帧截图、开源）和高级 Frame Profiler Alpha（2026 H2，基于 GFXReconstruct，支持 frame looping 和 render pass graph 分析）

[已验证: AGI 官方文档, developer.android.com/agi]

### Frame Timeline 中的表现差异

Frame Timeline（帧时间线）在 Android 10+ 可用，它展示了每帧从 App 提交到 SurfaceFlinger 合成再到显示的完整时间线。无论是使用 Vulkan 还是 GLES（通过 ANGLE），Frame Timeline 都能正常工作，因为帧的呈现时间戳是在 SurfaceFlinger 层面记录的，与上层的图形 API 无关。

但 GPU 执行时间（Frame Timeline 中的 GPU duration）的精度会因 API 不同而有所差异。Vulkan 应用可以通过 `VkSemaphore` 精确标记 GPU 工作的开始和结束，而 GLES 应用的 GPU 时间戳依赖于驱动实现，精度可能稍低。

## 迁移策略与最佳实践

### 何时选择 Vulkan，何时保持 GLES

**决策路径**：

- 新项目 → 直接使用 Vulkan（推荐）
- 已有 GLES 代码 + 性能关键型（游戏/AR/VR）→ 评估迁移到 Vulkan
- 已有 GLES 代码 + 普通 UI 应用 → 不需要改动，ANGLE 会自动处理
- 已有 GLES 代码 + WebView/WebGL → 保持 GLES，不受 ANGLE 策略影响
- 使用游戏引擎 → 跟随引擎默认设置

**直接使用 Vulkan 的场景**：
- 新开发的 3D 游戏或 AR/VR 应用
- 需要多线程 GPU 命令构建的场景
- 对 GPU 内存布局有精细控制需求的场景
- 需要使用 Compute Shader 做大规模并行计算

**保持 GLES（通过 ANGLE）的场景**：
- 现有的 GLES 应用，性能表现稳定
- 以 2D UI 为主的普通应用
- 跨平台代码需要兼容 iOS（iOS 的 GLES 通过 ANGLE→Metal 运行）
- 开发资源有限，不值得投入 Vulkan 的高学习成本

### 从 GLES 迁移到 Vulkan 的关键步骤

迁移不是简单的 API 替换。以下是需要重点关注的事项：

1. **Pipeline 预创建**：Vulkan 的 Pipeline 创建是耗时操作（可能数十毫秒）。必须在应用启动或场景加载时完成所有 Pipeline 的创建，绝不能在渲染循环中创建 Pipeline
2. **Pipeline Cache 持久化**：将 Pipeline Cache 序列化到磁盘，下次启动时加载。这可以将冷启动的 Pipeline 创建时间减少 95%
3. **内存管理**：Vulkan 要求应用自己管理 GPU 内存。移动设备使用统一内存架构（CPU/GPU 共享物理内存），`VK_MEMORY_PROPERTY_DEVICE_LOCAL_BIT` 的选择策略与桌面端不同
4. **Pre-rotation**：设备旋转时，Vulkan 应用需要自己在渲染时处理画面旋转，否则 SurfaceFlinger 会做额外的旋转合成，导致性能下降
5. **验证层**：开发阶段启用 Vulkan Validation Layer（`VK_LAYER_KHRONOS_validation`）检查 API 使用错误，发布时关闭。验证层会带来显著的性能开销

[已验证: 官方文档, developer.android.com/ndk/guides/graphics]

### Android 17 对开发者的实际影响清单

| 场景 | 影响 | 行动 |
|---|---|---|
| GLES 应用（普通 App） | 自动走 ANGLE，性能基本不变 | 无需行动 |
| GLES 应用（游戏） | 可能有 5-10% 性能变化 | 在 Android 17 设备上测试 ANGLE 路径 |
| Vulkan 应用 | 无直接影响 | 确认 Vulkan 1.4 兼容性 |
| WebView/WebGL 应用 | 不受 ANGLE 策略影响 | 无需行动 |
| NDK 图形代码 | 可能有新的 API 行为差异 | 测试 ANGLE denylist 模式下的表现 |

## 与其他章节的关系

- **§2.1 Android 渲染架构全景**：本章聚焦 API 层面，§2.1 聚焦渲染架构整体
- **§2.9 渲染机制的版本演进**：§2.9 从渲染管线视角讲 HWUI→SkiaGL→SkiaVulkan 的演进，本章从 API 层面讲 GLES→Vulkan 的演进
- **§2.10 GPU 渲染深入**：§2.10 分析 GPU 内部的工作机制和性能分析，本章分析上层 API 的选择对性能的影响
- **§14.8 GPU 图形调试与分析工具**：AGI、RenderDoc 等工具的详细使用方法

## 常见问题与误区

**误区：ANGLE 翻译层会让所有 GLES 应用变慢**
实际情况：对于大多数 2D UI 应用，ANGLE 的性能开销在 2-5% 以内，用户完全感知不到。部分场景下 ANGLE→Vulkan 路径反而比原生 GLES 驱动更快。

**误区：Android 17 之后 OpenGL ES 就不能用了**
实际情况：OpenGL ES 仍然可用，只是通过 ANGLE 翻译为 Vulkan 执行。API 接口不变，应用不需要修改代码。Android 17 的 denylist 策略仅对新设备生效。

**误区：应该把所有 GLES 代码迁移到 Vulkan**
实际情况：对于普通 UI 应用，迁移的投入产出比很低。ANGLE 的翻译质量在持续提升，Google 的策略本身就是"让 GLES 应用无感迁移"。

**误区：Vulkan 一定比 OpenGL ES 快**
实际情况：如果 Vulkan 代码没有做 Pipeline 预创建、Cache 持久化、正确的同步等优化，性能可能反而比 GLES 更差。Vulkan 提供了更高的性能上限，但也要求更多的优化工作。

## 参考资料

- [Android NDK Graphics Guide](https://developer.android.com/ndk/guides/graphics) — Vulkan 和 GLES 的官方开发指南
- [ANGLE on Android](https://source.android.com/docs/core/graphics/angle) — ANGLE 的系统级集成文档
- [Vulkan as official Android graphics API](https://android-developers.googleblog.com/) — Google 官方博客公告
- [Android Vulkan Profile 2025](https://developer.android.com/ndk/guides/graphics) — AVP 2025 设备能力基线
- [ARM GPU Best Practices for Vulkan](https://developer.arm.com/) — 移动端 Vulkan 优化指南
- AOSP 源码路径：`platform/external/angle`（ANGLE 实现）、`frameworks/native/vulkan`（Vulkan NDK wrapper）
