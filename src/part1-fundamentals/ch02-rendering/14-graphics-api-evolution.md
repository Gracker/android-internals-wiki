---
status: ready-for-review
title: 图形 API 演进与选择策略（OpenGL ES / Vulkan / ANGLE）
chapter: '2.14'
drafted_date: '2026-04-05'
drafted_by: openclaw-task2a
applicable_versions: Android 4.0 (API 14) - Android 17 (API 37)
last_verified: '2026-04-26'
last_verified_against: source.android.com implement-vulkan + developer.android.com
  AVP / ProfilingManager docs + perfetto.dev frametimeline + AOSP main + AndroidX
  WebGPU docs + AOSP vk_android_native_buffer.h
confidence: medium
sources:
- type: official
  path: https://developer.android.com/ndk/guides/graphics
- type: official
  path: https://source.android.com/docs/core/graphics/implement-vulkan
- type: official
  path: https://developer.android.com/ndk/guides/graphics/android-vulkan-profile
- type: official
  path: https://developer.android.com/about/versions/15/features#graphics
- type: aosp
  path: frameworks/base/core/java/android/os/GraphicsEnvironment.java
- type: aosp
  path: frameworks/native/opengl/libs/EGL/Loader.cpp
- type: aosp
  path: frameworks/native/libs/graphicsenv/GraphicsEnv.cpp
- type: aosp
  path: frameworks/native/vulkan/include/vulkan/vk_android_native_buffer.h
- type: aosp
  path: external/angle/
- type: official
  path: https://developer.android.com/ndk/guides/graphics/validation-layer
- type: official
  path: https://developer.android.com/games/optimize/adpf
- type: official
  path: https://developer.android.com/develop/ui/views/graphics/webgpu
- type: official
  path: https://developer.android.com/jetpack/androidx/releases/webgpu
- type: official
  path: https://perfetto.dev/docs/data-sources/frametimeline
tags:
- opengl-es
- vulkan
- angle
- gpu
- graphics-api
- rendering
related_chapters:
- '2.1'
- '2.9'
- '2.10'
- '2.17'
- '14.8'
section: '2.14'
pipeline_stage: "task6_pending"
task6_state: reviewed
task9_state: "reviewed"
task2b_state: "fixed"
reviewed_by: openclaw-task6
reviewed_date: '2026-05-12'
task6_result: needs-rework
task9_result: "pass-tech-review"
task9_reviewed_date: 2026-05-19
task2b_result: "fixed"
last_task2b_at: '2026-05-12T19:36:00+08:00'
last_task9_at: "2026-05-19T00:30:02+08:00"
task9_reviewed_by: openclaw-task9
task9_review_notes: "2026-05-19 Task9 00:20：pass-tech-review。无 P0/P1；P2 3 处已写入 suggestions。Task6 仍需回炉，未自动晋升。"
review_type: task6-writing-quality-review
review_notes: "2026-05-12 task6 review: needs-rework。L1/L2 小修 4 处；WebGPU 90%-95% 吞吐量缺基准条件，已写入 queue。"
last_task9_review_log: logs/deep-review/2026-05-19-00-deep-review.md
---



# 2.14 图形 API 演进与选择策略（OpenGL ES / Vulkan / ANGLE）

我们在 §2.1 中看到了 Android 渲染架构的全景，在 §2.9 中了解了渲染管线从 HWUI 到 SkiaVulkan 的演进，在 §2.10 中分析了 GPU 渲染的深入机制。但有一个维度一直没有展开：当我们要写一个游戏引擎、一个视频滤镜、或者一个需要直接操作 GPU 的应用时，应该选择哪个图形 API？OpenGL ES、Vulkan，还是把 GLES 交给 ANGLE 翻译？这个选择在 Android 15 之后尤其重要。Google 已经把 Vulkan 明确为 Android 首选 GPU 接口，并把 ANGLE 定位为在 Vulkan 之上承载 OpenGL ES 的过渡层。同样是一段 GLES 代码，在不同设备上可能仍走厂商原生驱动，也可能被平台切到 ANGLE，再落到 Vulkan 驱动。

理解图形 API 的演进脉络和架构差异，不只是“选对工具”的问题。我们在 Perfetto 里看到 GPU 工作时，需要先分清自己手上拿到的是哪一层信号：是应用侧 API 调用、驱动暴露的 GPU renderstage，还是系统合成层记录的帧结果。只有把这些层次分开，后面的兼容性判断和性能分析才不会混线。

## Android 图形 API 的三代演进

Android 从诞生到现在，GPU 编程接口经历了三代更迭。这个演进跨越十余年，是渐进式的。

### 第一代：OpenGL ES——移动 GPU 的起点

OpenGL ES（OpenGL for Embedded Systems）是 Khronos Group 为嵌入式设备制定的图形 API 标准。Android 从 1.0 版本就支持 OpenGL ES 1.0/1.1，但让 GPU 渲染成为主流的是 OpenGL ES 2.0——它带来了可编程着色器（vertex shader 和 fragment shader），从固定功能管线转向了可编程管线。

Android 各版本对 OpenGL ES 的支持时间线：

| OpenGL ES 版本 | 引入的 Android 版本 | API Level | 关键能力 |
|---|---|---|---|
| 1.0 / 1.1 | Android 1.0 | API 1 | 固定功能管线，基本 2D/3D |
| 2.0 | Android 2.2 (Froyo) | API 8 | 可编程着色器（GLSL ES），现代 GPU 编程的起点 |
| 3.0 | Android 4.3 (JB MR2) | API 18 | 多重渲染目标（MRT）、Transform Feedback、实例化绘制 |
| 3.1 | Android 5.0 (Lollipop) | API 21 | Compute Shader、独立着色器对象 |
| 3.2 | Android 7.0 (Nougat) | API 24 | Android Extension Pack 正式标准化 |

[已验证: 官方文档, developer.android.com/guide/topics/graphics/opengl]

OpenGL ES 2.0 是一个分水岭。在它之前（ES 1.x），开发者只能用固定功能管线：告诉 GPU "画一个三角形、贴一张纹理、加一个光源"，GPU 按预定义的流程执行。ES 2.0 引入了 GLSL ES 着色器语言，开发者可以自己写代码控制 GPU 的顶点处理和片段着色阶段。这打开了移动端 GPU 的潜力——后处理滤镜、水面反射、粒子系统都成为可能。

ES 3.0/3.1/3.2 在 ES 2.0 的基础上逐步添加了更高级的 GPU 特性：多重渲染目标允许一次绘制输出多张纹理（延迟渲染的基础）、Compute Shader 让 GPU 执行通用计算、实例化绘制减少了 draw call 数量。

但 OpenGL ES 有一个根本性的架构限制：它是一个**状态机模型**。每次调用 `glBindTexture()`、`glBlendFunc()`、`glDrawArrays()` 时，都在改变一个全局状态机的状态。驱动需要在每次 draw call 时检查完整的状态组合是否合法、是否需要重新编译着色器、是否需要同步 CPU 和 GPU——这些都在调用线程上同步完成。这个设计在高 draw call 数量的场景下会成为严重的 CPU 瓶颈。

### 第二代：Vulkan——显式控制的现代 API

Vulkan 同样由 Khronos Group 制定，2016 年发布 1.0 版本。与 OpenGL ES 的"驱动替你做决定"不同，Vulkan 的设计哲学是"开发者自己控制一切"：内存分配、命令提交时机、GPU/CPU 同步策略、管线状态——全部由应用显式指定。

Android 对 Vulkan 的版本基线可以直接看官方 `implement-vulkan` 文档。它给出的对应关系是：

| Vulkan 版本 | 平台 API 可用性 | 新设备 Launch Requirement | 关键能力 |
|---|---|---|---|
| 1.0 | Android 7.0 (API 24) | Android 7.0+ | 显式 API、Command Buffer、多线程命令录制 |
| 1.1 | Android 7.0 (API 24) | Android 10 新 64 位设备 | subgroup 操作、YCbCr 转换、多视图渲染 |
| 1.3 | Android 13 (API 33) | Android 13+ launch devices | 动态渲染、Synchronization 2、更多现代 Vulkan 能力进入主流基线 |
| 1.4 | Android 16 (API 36) | Android 16+ launch devices | 更多此前可选的现代能力进入 core，平台继续向更完整的 Vulkan 功能集收敛 |

[已验证: 官方文档, source.android.com/docs/core/graphics/implement-vulkan]

Vulkan 1.0 就已经提供了 OpenGL ES 不具备的核心能力：Command Buffer 允许多线程并行构建 GPU 命令、显式内存管理让应用控制 GPU 内存的分配和回收时机、Pipeline State Object（PSO）将着色器和渲染状态预编译为一个不可变对象，避免了运行时的状态验证开销。

但 Vulkan 1.0 的 API 复杂度极高。创建一个"画一个三角形"的最小 Vulkan 程序需要约 800 行代码——同样的功能在 OpenGL ES 中只需要不到 100 行。Vulkan 1.1/1.3/1.4 的迭代目标就是降低这个复杂度：Vulkan 1.3 的动态渲染让开发者不再需要显式定义 RenderPass 对象，Vulkan 1.4 继续把更多现代能力并入核心能力集合。

上表说的是平台 / OEM 侧的 Vulkan 版本基线，我们可以把它理解为“这一代 Android 对新设备希望具备什么 Vulkan 能力”；它不等于“所有升级到该版本的旧设备都会自动获得同样的 Vulkan 版本”。

**Android Vulkan Profile 2025（AVP 2025）** 面向活跃设备生态定义了一组兼容能力集合，适合拿来描述更稳定的跨设备能力面。官方页面已经说明，早期资料里的 **Android Baseline Profiles（ABP）** 正在统一更名为 **Android Vulkan Profiles（AVP）**；如果你在旧分享或旧 JSON 里还看到 ABP，可以把它理解为同一条能力线的旧称。

AVP 2025 在 AVP 2022 / 2021 的基础上继续扩展 profile 能力集合，官方点名的是额外内存特性、浮点控制、host query reset，以及更多标准化像素格式。它更适合拿来做 capability audit 和 feature gating：先看目标设备是否满足这组 profile，再决定默认开启哪些渲染路径。到了 Android 16，新发设备的 Vulkan 平台基线已经抬到 1.4，这时像 `VK_EXT_host_image_copy` / Host Image Copy 这样的上传路径能力就值得单独核对：它允许 CPU 直接把数据拷到 image，减少 staging buffer 和额外 copy，纹理流式加载、首帧资源上传和后台资源预热都更容易压住卡顿。是否真的可用，仍要以目标设备暴露的 Vulkan version、feature 和 extension 为准。

[已验证: 官方文档, developer.android.com/ndk/guides/graphics/android-vulkan-profile]

### VP_ANDROID_16 Profile 与 Vulkan 1.4 基线

Android 16 的 Vulkan 要求要拆成两层看：

1. **平台基线**：Android 16 新设备需要支持 Vulkan 1.4（见 `implement-vulkan` 官方表）
2. **VP_ANDROID_16 Profile**：Khronos 发布的 Android 16 Vulkan Profile，定义新设备上应具备的最低兼容能力集合。该 profile 的 api-version 为 1.3.276，额外强制要求 `VK_EXT_host_image_copy`

| 层级 | 版本要求 | 强制扩展 |
|---|---|---|
| Android 16 平台基线 | Vulkan 1.4 | — |
| VP_ANDROID_16 Profile | api-version 1.3.276 | `VK_EXT_host_image_copy` |

`VK_EXT_host_image_copy` 允许 CPU 直接把数据拷到 VkImage，省掉 staging buffer 和额外拷贝。纹理流式加载和首帧资源上传都受益。

`VK_EXT_shader_object` 不是 VP_ANDROID_16 的强制扩展，但在支持它的设备上对渲染流畅性有直接帮助：传统路径中每个 shader + render state 组合都要预编译成不可变 PSO，着色器变体多的场景（不同材质、光照组合），PSO 创建是冷启动卡顿的主要来源。这个扩展让驱动在运行时按需编译单个着色器，不需要穷举所有组合。排查 Shader Jank 时，如果目标设备支持该扩展但应用仍有着色器编译卡顿，优先检查是否已经在用 shader object 路径。

工程上建议同时核对目标设备的 Vulkan 1.4 支持和 VP_ANDROID_16 profile compliance：前者决定平台能力基线，后者决定跨设备兼容能力的最低集合。具体设备的扩展支持以 `vkEnumerateDeviceExtensionProperties` 返回的结果为准。

### 第三代：ANGLE——翻译层，不是新 API

严格来说，ANGLE（Almost Native Graphics Layer Engine）不是一个独立的图形 API，它是一个**翻译层**：接收 OpenGL ES API 调用，将其翻译为 Vulkan（或 macOS/iOS 上的 Metal）调用。

ANGLE 的定位可以用一句话概括：它让 OpenGL ES 应用在不改 API 的前提下，有机会跑在 Vulkan 后端之上。但在 Android 上，关键的不是“系统里有没有 ANGLE”，而是“这次进程启动时，GLES driver 最终选中了谁”。

Android 15 的图形说明页把 ANGLE 描述为“running OpenGL ES on top of Vulkan”的 optional layer，同时明确写到，后续会在更多**新设备**上把 ANGLE 作为 GL system driver 出厂。因此，我们更应该把 ANGLE 理解为一条持续推进中的路线，而不是一个已经对所有设备统一生效的开关。

**[待验证]** Android 17（API 37）据传会把 ANGLE 升级为新设备上的强制性默认 GLES 驱动，但截至 2026-05，source.android.com/compatibility 公开到 Android 16 CDD，未见 Android 17 CDD 条款直接支撑这一结论。如果后续官方文档确认，以下影响将成立：原生 GLES 驱动不再作为默认选项出厂，GLES 调用由平台统一翻译到 Vulkan 后端。

目前可以确认的结论：

- Android 15 把 ANGLE 定位为 optional layer，官方 roadmap 表明后续会在更多新设备上把 ANGLE 作为 GL system driver 出厂
- 具体设备是否走 ANGLE，需以 CDD 条款、AOSP config/CTS 变更或官方发布文档为依据
- 旧设备升级后的行为取决于厂商实现

排查 Perfetto 时，仍建议先确认"本次进程启动时 GLES driver 最终选中了谁"，不要默认所有 Android 17+ 设备都走 ANGLE。

AOSP `GraphicsEnvironment.queryAngleChoice()` 给出了 Java 层的第一段选路顺序：先看全局开关 `ANGLE_GL_DRIVER_ALL_ANGLE`，再看按包名配置的 `angle_gl_driver_selection_pkgs` / `angle_gl_driver_selection_values`，最后才落到平台资源里的 `config_angleAllowList`。如果显式选了 `native`，Java 层会把 `shouldUseNativeDriver` 传给 native 层；如果选了 ANGLE，则先尝试 ANGLE APK，再回退到 system ANGLE。到了 `frameworks/native/opengl/libs/EGL/Loader.cpp`，loader 的顺序是“先尝试 ANGLE，再尝试 updatable driver，最后再落回 native / system GLES driver”。这也是为什么我们不能把“Android 15+”直接等同于“所有 GLES 应用都会自动经过 ANGLE”。

```java
// frameworks/base/core/java/android/os/GraphicsEnvironment.java
private String queryAngleChoice(...) {
    if (allUseAngle == ANGLE_GL_DRIVER_ALL_ANGLE_ON) return "angle";
    ...
    if (optInValue.equals("angle")) return "angle";
    if (optInValue.equals("native")) return "native";
    ...
    for (String allowedPackage : angleAllowListPackages) {
        if (allowedPackage.equals(packageName)) return "angle";
    }
    return "default";
}
```

开发者选项和 ADB override，就是在改这些 `Settings.Global` 键值。调试单个包时，常见做法是同时写入包名列表和值列表：

```bash
adb shell settings put global angle_gl_driver_selection_pkgs com.example.app
adb shell settings put global angle_gl_driver_selection_values angle
```

如果要回到平台默认选路，再删除对应的 global setting 即可。除此之外，AOSP `GraphicsEnv.cpp` 还暴露了 `ANGLEAndroidParseRulesString()` 和 `ANGLEShouldBeUsedForApplication()` 这条调用链，说明 ANGLE 包自身还可以结合 rules string、设备信息和 app 包名做进一步判断。对排查“为什么这台机型走 ANGLE、那台不走”这类问题时，这条链路比简单的 allowlist / denylist 口号更有解释力。

[已验证: 官方文档 + AOSP 源码, developer.android.com/about/versions/15/features#graphics, frameworks/base/core/java/android/os/GraphicsEnvironment.java, frameworks/native/opengl/libs/EGL/Loader.cpp, frameworks/native/libs/graphicsenv/GraphicsEnv.cpp]

## Vulkan 与 OpenGL ES 的架构差异

理解这两种 API 的架构差异，不只是理论问题。我们在 Perfetto 中分析 GPU Activity 时，看到的 slice 行为、时间分布和抖动模式，都和底层 API 的架构选择直接相关。

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

这个过程在简单的场景下不是问题，但当 draw call 数量达到数百甚至数千（复杂 UI、游戏场景），CPU 侧的状态验证、资源同步和 driver bookkeeping 就会直接堆在提交线程上。Vulkan 把大量验证前移到 Pipeline 创建阶段，单次命令记录路径通常更轻。具体差值强依赖 GPU 架构、驱动质量和 workload，不适合脱离测试条件写成固定微秒表。

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
    // ... 所有状态在创建时一次性确定
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

OpenGL ES 的全局状态机设计导致它是一个单线程 API。虽然可以通过 EGL 共享上下文在多个线程中使用 OpenGL ES，但状态机的全局性使得多线程同时操作 GL 上下文需要大量的锁同步，实际收益有限。

Vulkan 的 Command Buffer 天然支持多线程。不同的线程可以各自独立地构建 Command Buffer，最后在一个线程上统一提交：

```
线程 A: 构建 Command Buffer (场景渲染命令)
线程 B: 构建 Command Buffer (UI 覆盖层命令)
线程 C: 构建 Command Buffer (后处理命令)
   ↓
主线程: vkQueueSubmit(A + B + C) → 一次性提交到 GPU
```

在 Perfetto 中，如果应用使用 Vulkan 的多线程命令构建，我们可以在多个线程的 Track 上同时看到 GPU 命令的录制活动，而最终的 `vkQueueSubmit` 只会在提交线程上出现一个很短的 slice。

### Command Buffer 复用

OpenGL ES 没有命令缓冲区的概念——每次绘制都是"即时的"（虽然驱动内部可能做批处理，但开发者无法控制）。Vulkan 的 Command Buffer 可以在帧之间复用：如果一帧的渲染命令没有变化（比如静态 UI），只需要在第一帧录制 Command Buffer，后续帧直接重新提交即可。

这个特性对 UI 渲染特别有价值。Android 的 View 系统在 UI 没有变化时不会重新走一遍 measure/layout/draw 流程，但 GPU 命令仍然需要提交。如果使用 Vulkan 的 Command Buffer 复用，静态 UI 的帧提交开销几乎为零。

## ANGLE 的角色与 Android 图形栈收敛

### ANGLE 的翻译架构

ANGLE 在 AOSP 中的源码路径为 `external/angle/`，其核心翻译流程如下：

```
App 的 GLES 调用
    ↓
GLES 入口函数 (eglMakeCurrent, glDrawArrays, ...)
    ↓
验证层（Validation Layer）—— 检查 API 使用是否合法
    ↓
状态追踪层（State Tracking）—— 维护 OpenGL ES 的状态机
    ↓
Vulkan 后端（external/angle/src/libANGLE/renderer/vulkan/）
    ├─ vk::Renderer —— 管理 VkDevice, VkQueue, 格式表, 内部着色器
    ├─ ContextVk —— 处理 OpenGL Context 的状态变更和命令执行
    └─ Pipeline 缓存 —— 将 OpenGL 状态向量映射到 Vulkan PSO
    ↓
Vulkan 驱动 → GPU
```

[已验证: AOSP 源码, external/angle, external/angle/src/libANGLE/renderer/vulkan/]

ANGLE 的翻译不是简单的 API 映射。最复杂的部分是**状态转换**：OpenGL ES 的"随时改变状态"模型需要被翻译为 Vulkan 的"预编译 Pipeline"模型。ANGLE 内部维护了一个状态向量到 Vulkan PSO 的哈希映射表——当应用改变了 OpenGL ES 状态时，ANGLE 会查找是否已经有匹配的 Vulkan Pipeline，如果没有就创建一个新的。

ANGLE 引入的额外开销主要来自两方面：

1. **GLSL ES 到 SPIR-V 的着色器翻译**：ANGLE 内置了一个着色器编译器，将 GLSL ES 源码翻译为 Vulkan 使用的 SPIR-V 二进制格式。这个翻译发生在着色器首次编译时，之后会被缓存
2. **状态追踪和 Pipeline 查找**：每次 GLES draw call 都需要在哈希表中查找匹配的 Vulkan Pipeline，如果未命中则创建新的 Pipeline（这个创建过程本身是耗时的）

### ANGLE 的性能影响应该怎么理解

官方资料强调的重点是 compatibility 和 behavior consistency，而不是给出一个统一的“ANGLE 一定慢多少”结论。原因很简单：ANGLE 的成本不只取决于 ANGLE 本身，还取决于 workload 的 draw call 形态、shader 数量、state change 密度，以及原生 GLES driver 自身的质量。

从机制上看，ANGLE 的额外成本主要集中在两个阶段。第一次是 shader 翻译和 pipeline 建立：GLES shader 需要被 ANGLE 翻译到后端可用的形式，首次命中时会有额外 CPU 开销。第二次是 draw call 前的状态映射：ANGLE 需要把 OpenGL ES 的状态机语义折算成 Vulkan 的 pipeline、descriptor 和 render pass 语义。如果 workload 状态切换频繁、pipeline cache 命中率又不高，这部分成本就会更明显。

反过来看，如果某个 SoC 的原生 GLES driver 本身存在较重的 CPU 开销或兼容性问题，ANGLE 走 Vulkan 后端反而可能更稳定，甚至更快。所以我们不应该在文章里给出脱离场景的固定百分比，更合理的结论是：**ANGLE 带来的是“以一定翻译成本换取更一致的驱动行为”。**答案只能在目标 workload 和目标设备上测出来。

另外，Vulkan 支持 pipeline cache，但“系统 ANGLE 一定能替所有 GLES 应用统一管理并稳定复用 cache”并不是官方给出的通用承诺。分析启动抖动时，我们可以把 pipeline / shader 首次编译当成重点怀疑对象，但不要先把它写成一条无条件成立的系统保证。

### ANGLE 路线对开发者的实际影响

对开发者来说，更可靠的判断方式是先回答三个问题：这个设备的 GL system driver 是什么？这个包有没有被 developer option / adb override 改写？如果都没有，平台默认策略是否把它放进了 ANGLE 路径？

因此，现阶段更稳妥的工程结论是：

1. **现有 GLES 应用不一定需要立刻迁移**：如果目标设备仍在原生 GLES driver 上，应用会继续按原路径运行；如果设备把该包选进 ANGLE，API 代码通常不用改，但我们仍要重新做稳定性和性能回归。
2. **性能变化要按 workload 测**：ANGLE 可能变慢，也可能因为绕开厂商 GLES driver 的问题而更稳定。
3. **调试时先确认“是否走 ANGLE”再看 Trace**：没有这一步，后面的 Perfetto 解释很容易错层。
4. **WebView / WebGL 需要单独判断**：Chromium / WebView 先由自身的 Skia backend 决定走 Vulkan 还是 GL。SkiaVulkan 直接调用 Vulkan driver，系统 ANGLE policy 不参与；只有回到 SkiaGL / GLES 路径时，ANGLE 选路才会影响这条栈。

系统 ANGLE policy 只解释“系统 GLES driver 怎么选”，它不能替代 Chromium / WebView backend 检查。

### 热 / 功耗信号也会进入选路

Android 15 在 ADPF 中新增了 power-efficiency mode、GPU + CPU work duration 上报和 thermal headroom thresholds。图形 API 选路不能只看峰值帧率，还要看长时间运行时的热预算。

`GraphicsEnvironment` 负责 driver 选择入口，ADPF 提供热 / 功耗信号，这两套机制经常一起用，但不是同一个开关。工程上可以把它们组合成三档策略：

1. **性能优先**：thermal headroom 充足，目标是峰值帧率，继续走 native Vulkan 或已经验证稳定的 native GLES
2. **功耗优先**：headroom 持续收紧，或 hint session 已切到 power-efficiency mode 时，在目标机型上评估更保守的 ANGLE 路径，并同时降低分辨率、后处理、阴影或 texture streaming 频率
3. **安全 / 兼容优先**：业务含 WebView / WebGPU 时，再叠加浏览器侧的安全与兼容性策略，必要时退回更保守的 backend。系统 GLES driver policy 只能解释 GLES 选路，不能替代 WebGPU 或 Chromium backend 的判断

[已验证: 官方文档, developer.android.com/about/versions/15/features#graphics, developer.android.com/games/optimize/adpf]

### WebGPU / Dawn：另一条新接口

Android 侧新增的一条图形接口路线是 WebGPU。Jetpack 文档把它定义为 WebGPU 标准的 Kotlin bindings，并直接写明它是 WebGL 的后继接口，定位比 Vulkan 更高层，代码量也更小，适合图像处理、数据可视化、ML inference 和游戏这类直接依赖 GPU 的场景。

需要把 WebGPU 和 ANGLE 分开看。ANGLE 是 GLES 到 Vulkan 的翻译层，WebGPU 是另一套 API 语义和 WGSL shader 体系。AndroidX WebGPU 的 release notes 已经写明它会持续更新内部 Dawn source commit，Dawn 项目本身也是 Chromium 中 WebGPU 的底层实现。分析 WebView / WebGL / WebGPU 问题时，要先确认 Chromium / Dawn 这一层的 backend，再去解释系统 ANGLE policy。两者观察路径不同。

Jetpack WebGPU 的 API 代码量比 Vulkan 少一个数量级。计算管线的抽象开销低于渲染管线——这是 Dawn 内部做 command buffer 转写时的结构决定的。图形渲染管线的相对性能取决于 draw call 密度和着色器复杂度，与计算管线的差距更大。选择 WebGPU 的场景（图像处理、ML inference、数据可视化）通常以计算管线为主，可以预期 GPU 活动的开销比例较低。

[待验证: 此前版本中“Jetpack WebGPU 在 Android 17 上达到 Vulkan 原生实现 90%-95% 吞吐量”缺少基准来源、设备、测试 workload 和 API/库版本，已改为定性描述。]

[已验证: 官方文档 + 上游实现, developer.android.com/develop/ui/views/graphics/webgpu, developer.android.com/jetpack/androidx/releases/webgpu, github.com/google/dawn]

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

在 Perfetto 里，最容易出错的地方是把不同层次的数据源混成一条因果链。更稳妥的读法是先分清“这个数据源到底观测的是 CPU API 调用、GPU work submission，还是进程装载状态”。

| 数据源 / 观察面 | 我们能看到什么 | 不能单独回答什么 |
|---|---|---|
| GPU Activity / `gpu.renderstages` | 驱动暴露出来的 GPU 阶段、queue work、部分 `vk*` 或 vendor slice 名称 | 不能只凭一个 `vkQueueSubmit` 就断定“应用一定是原生 Vulkan”或“一定是 GLES 经 ANGLE” |
| `gpu.counters` | 频率、利用率、带宽等时间序列 | 反映负载，不直接反映 API 选路 |
| 进程 maps / 已加载共享库 | `libEGL.so`、`libGLESv2.so`、`libvulkan.so`、ANGLE 相关库是否出现 | 很多栈会同时加载多种库，不能只凭 loaded libs 判断最终渲染后端 |
| App 侧自检日志 | 当前进程向上暴露的 renderer / backend 信息 | 需要应用配合，单独使用时也看不到 GPU 负载细节 |

靠谱的做法是把这些信号组合起来：先用 app 侧自检或 driver selection 配置确认“这次想走哪条路”，再用 maps 和 Perfetto 看“实际加载了什么、GPU 工作怎么分布”，最后再把 Frame Timeline 里的帧结果对上去。这样我们才能区分 native Vulkan、native GLES，以及 GLES-over-ANGLE 这三类路径，而不是被某一个 slice 名字带偏。

GPU counter 的配置方式（在 TraceConfig 中）：

```protobuf
// Perfetto TraceConfig GPU counter 配置
data_sources {
    config {
        name: "gpu.counters"
        gpu_counter_config {
            counter_period_ns: 1000000  // 1ms 采样间隔
            counter_ids: 1  // 按需选择 GPU counter ID
            counter_ids: 2
            counter_ids: 3
        }
    }
}
```

注意：`counter_period_ns` 是 Perfetto `GpuCounterConfig` 的正确字段名；`counter_ids` 为 repeated 字段，每个 ID 单独一行。如果 GPU producer 支持 `counter_names`，也可以用名称代替 ID，但需要确认目标设备的 producer 实现。

因此，`gpu.counters` 更适合回答“这一段 GPU 忙不忙、频率高不高”，不适合单独回答“到底是 GLES 还是 Vulkan”。只有在我们已经通过进程 maps、driver selection 或 app 侧日志确认了 API 路径之后，这些 counters 才能作为性能分析证据继续往下用。

[待补充: Perfetto 中 renderstages / maps / Frame Timeline 的三层对照截图]

### AGI 与不同 API 的兼容性

Android GPU Inspector（AGI）是 Google 官方的 GPU 分析工具（详见 §14.8）。AGI 的支持边界要按具体版本和 capture mode 看，正文里只保留稳定结论：

- **Vulkan 应用**：AGI 可以直接捕获和分析 Vulkan 调用，适合做 draw call、render pass 和 GPU 时间分布分析
- **OpenGL ES 应用**：常见做法是借助 ANGLE 或图形重放路径把 GLES 工作映射到 Vulkan 视角，因此可见内容会受设备、驱动和 capture 模式限制
- **工具能力更新**：长时 system trace、帧截图、Frame Profiler 这类能力更新很快，实战时直接对照当期 AGI release notes，不要把某一年的路线图当成稳定事实

[已验证: AGI 官方文档, developer.android.com/agi]

### Frame Timeline 中的表现差异

Frame Timeline（帧时间线）要求 Android 12(S) 及以上。`Expected Timeline` / `Actual Timeline` 这组轨道适合回答“哪一帧晚了、晚在 App 还是晚在 SurfaceFlinger”。如果你在 Android 10-11 上排查，UI 里不会看到这组轨道，对应的 FrameTimeline 表也不存在。

截至 2026-04，Perfetto 公开文档仍把 `SurfaceView` 标成 `SurfaceViews are currently not supported`。Android 15 引入的 `ProfilingManager`，以及 Android 16 新增的 system-triggered profiling，解决的是 trace 更容易抓、关键事件更容易关联；它们不等于 Frame Timeline 已经补齐 `SurfaceView` 的 `Actual Timeline`。所以在游戏、相机预览、播放器这类 `SurfaceView` 场景里，更稳的入口仍是 `SurfaceView` buffered frames、`gpu.renderstages`、Swappy stats，以及应用自己的 driver / backend 自检日志。Frame Timeline 关注的是 frame result，不直接告诉我们这一帧背后走的是 native Vulkan、native GLES 还是 ANGLE；具体的 Swappy 验证路径见 §2.17。

[已验证: Perfetto 官方文档, https://perfetto.dev/docs/data-sources/frametimeline]

## 迁移策略与最佳实践

### 何时选择 Vulkan，何时保持 GLES

```
新项目？
  ├─ 是 → 直接使用 Vulkan（推荐）
  ├─ 否（已有 GLES 代码）
  │   ├─ 性能关键型（游戏/AR/VR）→ 评估原生 Vulkan，并在目标设备上对比 native GLES / ANGLE 路径
  │   ├─ 普通 UI 应用 → 先维持 GLES，但在 Android 15+ 目标设备上验证是否被切到 ANGLE
  │   └─ WebView/WebGL → 额外检查 Chromium / WebView backend，不直接套用系统 ANGLE 结论
  └─ 使用游戏引擎 → 跟随引擎默认设置，再用目标设备做实测
```

**直接使用 Vulkan 的场景**：
- 新开发的 3D 游戏或 AR/VR 应用
- 需要多线程 GPU 命令构建的场景
- 对 GPU 内存布局有精细控制需求的场景
- 需要使用 Compute Shader 做大规模并行计算

**继续维护 GLES 的场景**：
- 现有的 GLES 应用，目标设备实测稳定
- 以 2D UI 为主，且没有明确的 CPU driver bottleneck
- 跨平台代码仍需要保持 GLES 抽象层
- 开发资源有限，但要把 native GLES / ANGLE 两条路径纳入回归范围

### 从 GLES 迁移到 Vulkan 的关键步骤

迁移不是简单的 API 替换。以下是需要重点关注的事项：

1. **Pipeline 预创建**：Vulkan 的 Pipeline 创建是耗时操作（可能数十毫秒）。必须在应用启动或场景加载时完成所有 Pipeline 的创建，绝不能在渲染循环中创建 Pipeline
2. **Pipeline Cache 持久化**：将 Pipeline Cache 序列化到磁盘，下次启动时加载。这样可以减少重复建管线的冷启动开销，但具体收益取决于 workload 和驱动实现
3. **内存管理**：Vulkan 要求应用自己管理 GPU 内存。移动设备使用统一内存架构（CPU/GPU 共享物理内存），`VK_MEMORY_PROPERTY_DEVICE_LOCAL_BIT` 的选择策略与桌面端不同
4. **Pre-rotation**：设备旋转时，Vulkan 应用需要自己在渲染时处理画面旋转，否则 SurfaceFlinger 会做额外的旋转合成，导致性能下降
5. **验证层**：开发阶段启用 Vulkan Validation Layer（`VK_LAYER_KHRONOS_validation`）检查 API 使用错误，发布时关闭。Android 官方文档把它定位为开发期的 error-checking 机制，用来避免 release build 的 performance penalty。它会拦截 Vulkan entry point 做额外校验，不要把开启验证层时测到的 CPU 帧时间直接当成正式性能数据

[已验证: 官方文档, developer.android.com/ndk/guides/graphics, developer.android.com/ndk/guides/graphics/validation-layer]

### Android 15+ 图形栈收敛后的实际检查项

| 场景 | 我们该关注什么 | 建议动作 |
|---|---|---|
| 现有 GLES 应用 | 该包在目标设备上究竟走 native GLES 还是 ANGLE | 用 developer option、app 日志、进程 maps 做一次确认 |
| 游戏 / 重负载渲染 | ANGLE 是否带来额外 shader / pipeline 抖动，或绕开原生 driver bug | 分别测首帧、稳态帧、shader warm-up |
| Vulkan 应用 | 是否满足 Android 13 / 16 的 Vulkan 1.3 / 1.4 基线，以及目标 AVP profile（旧资料常写 ABP） | 对照 `implement-vulkan` 和 AVP 页面做 capability audit |
| WebView / WebGL / WebGPU | Chromium / Dawn backend 与系统 GLES driver 是否一致，浏览器侧是否单独限制某条能力 | 单独看 Chromium / WebView / Dawn 的构建与运行时配置 |
| NDK 图形代码 | 代码是否把“GLES == 厂商原生驱动”当成硬编码假设 | 清理这些假设，改成运行时检测 |

## 与其他章节的关系

- **§2.1 Android 渲染架构全景**：本章聚焦 API 层面，§2.1 聚焦渲染架构整体
- **§2.9 渲染机制的版本演进**：§2.9 从渲染管线视角讲 HWUI→SkiaGL→SkiaVulkan 的演进，本章从 API 层面讲 GLES→Vulkan 的演进
- **§2.10 GPU 渲染深入**：§2.10 分析 GPU 内部的工作机制和性能分析，本章分析上层 API 的选择对性能的影响
- **§14.8 GPU 图形调试与分析工具**：AGI、RenderDoc 等工具的详细使用方法

## 常见问题与误区

**误区：ANGLE 一定会让所有 GLES 应用变慢**
实际情况：ANGLE 没有统一适用的固定性能百分比。它的开销取决于 workload、shader 首次编译、状态切换密度，以及原生 GLES driver 的质量。可靠的结论只能来自目标设备实测。

**误区：Android 15+ 之后所有 GLES 应用都会自动走 ANGLE**
实际情况：是否走 ANGLE，取决于系统 driver、全局开关、per-app override、平台 allowlist，以及 loader 的 fallback 路径。官方 roadmap 说的是“更多新设备会把 ANGLE 作为 GL system driver”，不是“所有设备、所有应用今天都已经统一切换”。

**误区：WebView / WebGL 一定受系统 ANGLE 路线控制**
实际情况：WebView / Chromium 的 GPU backend 先在 SkiaVulkan 和 SkiaGL 等路径之间选择。SkiaVulkan 路径绕过 GLES / ANGLE；SkiaGL 路径才会落到系统 GLES driver 选路。分析这类问题时，先验证 Chromium / Skia / WebView 当前 build 和运行时 backend。

**误区：Vulkan 一定比 OpenGL ES 快**
实际情况：如果 Vulkan 代码没有做 Pipeline 预创建、cache 预热和正确的同步，性能可能反而比 GLES 更差。Vulkan 提供了更高的性能上限，但也要求更多的工程投入。

## 参考资料

- [Android NDK Graphics Guide](https://developer.android.com/ndk/guides/graphics) — GLES / Vulkan 官方入口
- [Implement Vulkan](https://source.android.com/docs/core/graphics/implement-vulkan) — Android 版本与 Vulkan 能力基线
- [Android Vulkan Profile](https://developer.android.com/ndk/guides/graphics/android-vulkan-profile) — AVP 2025（旧称 ABP）与 profile 说明
- [Android 15 Features: Graphics](https://developer.android.com/about/versions/15/features#graphics) — ANGLE as optional layer 与官方 roadmap
- [Android Dynamic Performance Framework](https://developer.android.com/games/optimize/adpf) — 热 / 功耗信号与 hint session 能力
- [Vulkan validation layers on Android](https://developer.android.com/ndk/guides/graphics/validation-layer) — Validation Layer 的使用边界
- [WebGPU for Android](https://developer.android.com/develop/ui/views/graphics/webgpu) — WebGPU 在 Android 原生应用中的定位
- [AndroidX WebGPU release notes](https://developer.android.com/jetpack/androidx/releases/webgpu) — AndroidX WebGPU 与 Dawn 更新记录
- [Dawn README](https://github.com/google/dawn/blob/main/README.md) — Dawn 与 Chromium WebGPU 的关系
- AOSP 源码路径：`frameworks/base/core/java/android/os/GraphicsEnvironment.java`（driver selection / per-app override）、`frameworks/native/opengl/libs/EGL/Loader.cpp`（ANGLE / native / updated driver 选路）、`frameworks/native/libs/graphicsenv/GraphicsEnv.cpp`（ANGLE APK / system setup 与 rules string 接口）、`external/angle/`（ANGLE 实现）

---

<!-- AIW-源码调研-2026-04-26: ANGLE Vulkan Sync + RenderThread CPU Affinity -->

## 补充：ANGLE Vulkan 同步机制（源码级）

### EGL_ANDROID_native_fence_sync 的实现路径

ANGLE 的 Vulkan backend 在 Android 上通过 `EGL_ANDROID_native_fence_sync` 扩展实现 EGL Sync 对象与 Vulkan 同步原语的互操作。该扩展使得 EGL fence sync 对象可以与 native fence fd 关联，从而在 EGL 与 Vulkan 之间共享同步状态。

**关键调用链**（ANGLE Vulkan backend，源码位于 `external/angle/src/libANGLE/renderer/vulkan/android/`）：

```
eglCreateSync(EGL_ANDROID_native_fence_sync, fd)
  ├─ if fd provided: vkImportFenceFdKHR → VkFence
  └─ if no fd: create VkFence → vkGetFenceFdKHR → export fd

eglClientWaitSync(eglSync, timeout)
  → vkWaitForFences(fence, VK_TRUE, timeout)

eglWaitSync(eglSync, flags)
  → dup(nativeFenceFd) → vkImportSemaphoreFdKHR → VkSemaphore
  → add as wait semaphore to next vkQueueSubmit
```

### vkAcquireImageANDROID：EGL ↔ Vulkan 图像同步

`vkAcquireImageANDROID`（定义于 `vk_android_native_buffer.h`）是 Android 上 Vulkan 获取 EGL 管理图像的关键函数。其签名包含 `nativeFenceFd` 参数，允许 Vulkan 端等待 EGL 端完成图像处理后再复用：

```cpp
// vkAcquireImageANDROID signature
VkResult vkAcquireImageANDROID(
    VkDevice device,
    VkImage image,
    int nativeFenceFd,    // from EGL side — represents GPU completion point
    VkSemaphore semaphore,
    VkFence fence);
```

末尾两个参数分别接收 `VkSemaphore` 和 `VkFence`。这个函数不会返回 `VkImageLayout*`；把末尾参数写成 layout 指针，会把 Android 私有 WSI 扩展和其他 image acquire 路径混在一起。

**典型使用场景**：
1. GLES App 渲染完成 → 创建 EGL fence sync → 获得 fd
2. 同一 Surface 切换到 Vulkan 消费 → `vkAcquireImageANDROID(waitFd)` 阻塞直到 GLES 完成
3. 两个 API 之间的资源安全共享

### vkQueuePresentKHR 的同步陷阱

**核心问题**：`vkQueuePresentKHR` **不返回 fence 或 semaphore** 告知何时 presentation 操作完成。这导致 ANGLE 等 Vulkan 消费者无法安全复用 wait semaphore。

**Validation Layer 警告**（Vulkan SDK 1.4.313+）：
> "your VkSemaphore is being signaled by VkQueue, but it may still be in use by VkSwapchainKHR"

**解决方案**：
- **per-swapchain-image semaphore**：为每个 swapchain image 分配独立 "submit finished" semaphore，而非 per-frame
- **VK_KHR_swapchain_maintenance1**：允许 `vkQueuePresentKHR` 指定 fence，解决了这个长期问题

### Perfetto Trace 切片命名影响

当 ANGLE 开启 Vulkan backend 时，GPU 同步点的 Trace 命名从 GLES 风格变为 Vulkan 风格：

| 场景 | GLES/EGL 路径 | Vulkan/ANGLE 路径 |
|------|-------------|-----------------|
| Frame Signal | `eglSwapBuffers` | `vkQueuePresentKHR` |
| Wait 切片 | `GLFence::ClientWait` | `vkWaitForFences` |
| Image 获取 | N/A | `vkAcquireNextImageKHR` |
| Semaphore 操作 | `eglClientWaitSyncKHR` | `vkSemaphoreWait` |

---

## 补充：RenderThread CPU Affinity（SCHED_FIFO 调度机制）

### 系统级调度策略控制

RenderThread 的 CPU 亲和性通过 cgroup/task_profiles 体系由系统统一分配，**不是**通过显式 `sched_setaffinity` 调用管理。

**关键源码路径**：
```
frameworks/base/services/core/java/com/android/server/am/ActivityManagerService.java
```

RenderThread 调度策略由 `sys.use_fifo_ui` 系统属性控制：

```java
// ActivityManagerService.java (simplified from AOSP)
if (SystemProperties.get("sys.use_fifo_ui", "0").equals("1")) {
    // Apply SCHED_FIFO to UI thread and RenderThread of top-app
    final int renderThreadTid = renderThread.getTid();
    Process.setThreadScheduler(renderThreadTid,
                               Process.SCHED_FIFO | Process.SCHED_RESET_ON_FORK,
                               1 /* priority */);
}
```

**完整调度链**：
```
sys.use_fifo_ui=1
  → ActivityManagerService identifies top-app process
  → ProcessList.SCHED_GROUP_TOP_APP
  → setThreadScheduler(RenderThread, SCHED_FIFO, 1)
  → RenderThread gets SCHED_FIFO with priority 1
```

### cgroup 资源组分配

`SCHED_GROUP_TOP_APP` 是 Android 资源管理框架的调度组概念，与 cpuset 相关但不完全等同于 cpuset 绑定：

```
/dev/cpuset/
├── cpuset.top-app/      ← TOP_APP 调度组的 cpuset
│   ├── cpus             ← 大核（big cores）分配
│   └── mems             ← 对应 memory nodes
```

RenderThread 作为 top-app 进程内的线程，理论上可调度到大核。

### 早期实现的性能问题

RenderThread SCHED_FIFO 的早期实现曾导致显著性能回退：

| 版本 | 问题 | 后果 |
|------|------|------|
| 早期实现 | RenderThread load balancer 非 capacity-aware | RenderThread 抢占大核导致 UI thread 被驱逐到小核 |
| 影响 | App 启动速度降低 **30%** | 关键场景性能降级 |
| 修复 | 引入 capacity-aware RT load balancer | 95th/99th percentile 帧时间降低 10-15% |

### RenderThread 架构确认

Android SDK 文档明确说明：所有 `HardwareRenderer` 实例共享同一个 render thread。源码路径为 `frameworks/base/graphics/java/android/graphics/HardwareRenderer.java`。如果需要追踪 native 层线程行为，对应的实现路径是 `frameworks/base/libs/hwui/renderthread/RenderThread.cpp` 和 `RenderProxy.cpp`——`RenderProxy` 在 native 层持有 `RenderThread` 引用，由 `RenderThread::create()` 保证进程内单例。

> **待核实声明**：AOSP 中未找到 Android 15+ 新增"更激进的 CPU 大核绑定"相关 API 或参数。该说法来源为外部讨论，未经一手源码验证。

[已验证: AOSP ActivityManagerService.java, HardwareRenderer.java, vkAcquireImageANDROID, vkQueuePresentKHR spec]
