---

status: finalized
section: '2.10'
title: GPU 渲染深入
chapter: '2.10'
applicable_versions: Android 5.0 - Android 17 (API 21-37)
last_verified: '2026-07-25'
last_verified_against: AOSP android-17.0.0_r1 + kernel android17-6.18-2026-06_r6 + official Android/Perfetto GPU documentation + AndroidX WebGPU 1.0.0-alpha05 + Writer rendering_pipelines S01/S02/S05/S08/S13
confidence: medium-high
sources:
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/libs/hwui/
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/native/+/android-17.0.0_r1/libs/gui/
- type: aosp
  path: https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/drivers/dma-buf/
- type: official
  path: https://source.android.com/docs/core/graphics/arch-bq-gralloc
- type: official
  path: https://developer.android.com/games/develop/vulkan/overview
- type: official
  path: https://developer.android.com/reference/android/os/health/SystemHealthManager
- type: official
  path: https://developer.android.com/develop/ui/views/graphics/webgpu
- type: official
  path: https://developer.android.com/jetpack/androidx/releases/webgpu
- type: official
  path: https://developer.android.com/games/develop/vulkan/frame-pacing-extensions
- type: official
  path: https://developer.android.com/android-performance-analyzer
- type: official
  path: https://perfetto.dev/docs/data-sources/gpu
- type: official
  path: https://source.android.com/docs/compatibility/17/android-17-cdd
- type: aosp
  path: frameworks/base/libs/hwui/pipeline/skia/PersistentGraphicsCache.cpp (android-17.0.0_r1)
- type: aosp
  path: frameworks/base/libs/hwui/pipeline/skia/ShaderCache.cpp (android-17.0.0_r1)
- type: aosp
  path: frameworks/base/libs/hwui/pipeline/skia/PipelineCache.cpp (android-17.0.0_r1)
- type: aosp
  path: frameworks/base/core/java/android/os/health/SystemHealthManager.java (android-17.0.0_r1)
- type: aosp
  path: frameworks/native/vulkan/libvulkan/swapchain.cpp (android-17.0.0_r1)
- type: kernel
  path: kernel/common/drivers/dma-buf/dma-buf.c (android17-6.18-2026-06_r6)
- type: kernel
  path: kernel/common/drivers/dma-buf/dma-heap.c (android17-6.18-2026-06_r6)
- type: kernel
  path: kernel/common/drivers/dma-buf/dma-fence.c (android17-6.18-2026-06_r6)
- type: kernel
  path: kernel/common/drivers/dma-buf/sync_file.c (android17-6.18-2026-06_r6)
- type: writer
  path: Writer/rendering_pipelines/S01_rendering_types_overview.md
- type: writer
  path: Writer/rendering_pipelines/S02_aosp_standard_type.md
- type: writer
  path: Writer/rendering_pipelines/S05_mixed_rendering_type.md
- type: writer
  path: Writer/rendering_pipelines/S08_native_graphics_type.md
- type: writer
  path: Writer/rendering_pipelines/S13_game_type.md
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
reviewed_date: "2026-06-23"
reviewed_by: openclaw-task6
task6_state: reviewed
task6_result: pass-light-edit
review_round: 11
last_polish_notes: 第2轮出版级精修:修复applicable_versions范围、ANGLE URL拼写、叙述过渡、口语化表达;发现L3/L4问题需Task2B加工
polish_count: 2
polish_date: '2026-04-10'
polish_by: task2b-polish
task9_state: reviewed
task2b_state: "fixed"
task2b_result: fixed
pipeline_stage: ready-to-publish
last_task2b_at: "2026-06-02T22:50:00+08:00"
last_task2b_lite_at: "2026-06-01"
review_notes: "2026-05-09 task2b rework: ASTC vs ETC2 带宽对比表、gpu_busy Android 16 标准化轨道。 | 2026-05-12 task6 review: needs-rework。L1/L2 小修 2 处;参考资料后源码调研补充未整合、实战案例缺一手 Trace/AGI 证据,已写入 queue。 | 2026-06-02 task6 review: pass-light-edit。L1/L2 小修 2 处;AOSP mainline 锚点改为 Android 17 待验证边界,删除填充副词。"
review_type: task6-writing-quality-review
task9_result: "auto-fixed"
task9_reviewed_date: "2026-06-03"
task9_reviewed_by: "openclaw-task9"
last_task9_at: "2026-06-03T01:26:00+08:00"
rework_notes_2: "Task 2B 回炉修复: 参考资料后源码调研材料重构为附录(A.1 GPU 内存管理, A.2 GPU 性能排查流程), 保持正文收束结构"
last_task6_at: "2026-06-23T22:20:10+08:00"
last_task6_audit: "2026-06-21"
task6_review_notes: "2026-06-03 Task6 04: pass-light-edit。L1/L2 小修 4 处；未发现新增回炉项，进入 Task9 待审。"
task9_review_notes: "2026-06-03 Task9 deep review: auto-fixed。AUTO-FIX: 修正 graphics Java 源码目录、BufferQueue/GraphicBuffer/HWC2 路径与 BUFFER_RELEASE_CHANNEL 版本边界；P0 1 / P1 0 / P2 0，回到 Task6 复审。"
last_task6_review_log: "logs/review/2026-06-03-04-review.md"
task6_l1_l2_fixes: 4
task6_l3_l4_issues: 0
last_task9_autofix_at: "2026-06-03"
last_task9_review_log: "logs/deep-review/2026-06-03-01-deep-review.md"
p0: "1"
p1: "0"
p2: "0"
deepseek_cn_review_state: done
last_deepseek_cn_review_at: 2026-06-24
---

# GPU 渲染深入

“主线程不忙，所以 GPU 慢”会混淆不同的完成边界。UI 线程结束、RenderThread 提交、GPU completion、buffer queue 和显示提交彼此独立；任何一个边界迟到，都可能让画面错过目标周期。

以下分析以 Android 17 / API 37 的 `android-17.0.0_r1` 为源码锚点，覆盖三类内容：

- View/Compose 经过 HWUI 与 Skia 生成 App Window buffer；
- Native Graphics 或游戏通过 GLES/Vulkan 自己生产 Surface buffer；
- SurfaceFlinger 必要时用 RenderEngine 做 CLIENT composition。

它们可以共享同一块 GPU，也会竞争内存带宽，但线程、Surface、fence 和工具入口并不相同。

## 画面的生产者

同一个页面可能同时存在多条 GPU 路径：

| 内容类型 | 主要 Producer | GPU 工作出现在哪里 | SurfaceFlinger 看到什么 |
| --- | --- | --- | --- |
| 普通 View / Compose | App HWUI RenderThread | SkiaOpenGL 或 SkiaVulkan | 宿主 App Window Layer |
| TextureView 视频/相机 | 外部 Producer + 宿主 HWUI | 外部生产一次，HWUI 再采样一次 | 通常只有宿主 App Window Layer |
| SurfaceView 视频/游戏 | codec、Camera、GLES/Vulkan engine | 独立 Producer | 独立的子 child Surface Layer |
| SurfaceFlinger CLIENT composition | RenderEngine | SurfaceFlinger 进程的 GPU 工作 | client target 交给 HWC |
| HWC DEVICE composition | Composer/display hardware | 不一定使用通用 GPU | 独立图层由硬件平面合成 |

看到 GPU 忙碌度升高时，应先确认负载属于应用、另一个进程还是 SurfaceFlinger。页面里存在 `SurfaceView`、`TextureView`、游戏引擎或视频时，宿主 `RenderThread` 不能代表全部内容。

## Android GPU 渲染管线：从 API 到颜色附件

### “Vertex → Fragment → Framebuffer”是简化模型

传统图形管线可以概括为：

```text
CPU record / submit
  → vertex processing
  → primitive assembly + clipping
  → rasterization
  → fragment shading
  → depth/stencil tests + blending
  → color attachment / presentable image
```

这个模型适合建立概念，但不能据此断言每个 Canvas 操作固定生成多少顶点或使用哪一种 shader。Skia 可以根据图形、抗锯齿、clip、transform、backend 和 GPU 能力选择 analytic shader、实例化几何、tessellation、纹理 quad、离屏绘制或其他策略。

`View.invalidate()` 也不会立即启动 GPU。它标记需要更新并安排遍历；UI 线程在帧回调中记录或更新 RenderNode，随后由 RenderThread 同步状态、准备 GPU 工作并提交窗口缓冲。

### Vertex Shader 与几何阶段

Vertex Shader 对每个输入顶点执行位置变换，并输出后续插值所需的属性。primitive assembly、viewport clipping、culling 和 rasterization 还会在后续阶段处理图元；“Vertex Shader 自己判断所有不可见图元”并不准确。

Android UI 中的矩形、圆角、文字和 Path 最终可能变成几何、coverage mask、glyph atlas 采样或特定 GPU primitive。一个 `drawRect()` 不保证始终是“四个顶点”，复杂 Path 的成本也可能落在 CPU tessellation、GPU 几何、片元覆盖或缓存失效中的任一处。

对原生 3D engine，vertex/geometry 压力常来自：

- 过多顶点和小 draw call；
- 过细网格、粒子或阴影几何；
- skinning、morph、复杂 vertex shader；
- 可见性裁剪和 LOD 不充分；
- 顶点缓冲访问与缓存未命中。

标准 View 页面出现纯 vertex bound 的概率通常低于游戏，但需要用目标设备 counter 或帧分析确认，不能按 UI 元素数量猜测。

### Fragment Shader、测试与混合

光栅器为被覆盖的采样点生成片元。片元着色器计算颜色、纹理采样或覆盖值；随后还可能经过深度/模板测试、颜色写入掩码和混合。

alpha blending 通常由固定功能混合阶段按 pipeline state 完成，不应笼统写成 Fragment Shader 的内部职责。`RuntimeShader`、复杂滤镜、模糊、阴影、颜色空间转换和多纹理效果会增加 shader、采样或额外 pass 的成本。

片元压力大致与下面几项相关：

- render target 的像素/采样数；
- 同一像素被覆盖的次数；
- 每个片元的 shader 指令和纹理采样；
- MSAA、HDR/宽色格式、blend 和颜色转换；
- 离屏层、后处理和 SurfaceFlinger client target。

纹理访问会经过 GPU 缓存和设备内存系统，并不等于每次采样都访问一次外部 DRAM。带宽是否成为瓶颈，要看缓存命中、压缩、格式、采样模式、render pass 和设备 counter。

### Framebuffer、render target 与 Android GraphicBuffer

“Framebuffer”在不同 API 中含义不同：

- GLES 帧缓冲是一组附件的绑定状态；
- Vulkan 帧缓冲与传统 render pass 绑定附件；使用 dynamic rendering 时也可以不创建 `VkFramebuffer` 对象；
- HWUI/Skia 可能绘制到窗口缓冲，也可能先绘制到离屏表面；
- Android 窗口最终交付的是 `ANativeWindow`/BufferQueue 中的图形缓冲。

App Window buffer 可以作为 GPU color attachment，完成后随 producer fence queue 给下游。SurfaceFlinger 获得缓冲以后，还要处理事务、acquire fence、Layer snapshot 和合成。HWC 可能直接使用该图层，也可能让 RenderEngine 把多个 CLIENT 图层合成到另一张 client target。

这套流程不同于“VSync 到来时交换 front/back 指针”的简单桌面双缓冲模型。BufferQueue 管理多个槽位和缓冲，Producer dequeue/queue，Consumer acquire/release，并用栅栏表达异步完成关系。

### buffer 大小只能做下界估算

对于线性 RGBA_8888，`width × height × 4` 可以估算紧密排列像素的下界。实际分配还会受步长、对齐、layer count、像素格式、压缩 modifier、metadata、保护属性和 allocator 实现影响。三块 1080p 缓冲也不能直接代表“GPU 总内存”，因为还存在 depth/stencil、纹理、glyph atlas、离屏层、client target 与 driver allocation。

## 着色器编译卡顿与管线创建

### 一次“首次出现效果”的卡顿包含多层工作

从源码到 GPU 可执行状态，可能经历：

1. 解析或编译 GLSL、SkSL、AGSL；
2. 生成中间表示，例如 Vulkan SPIR-V；
3. 链接程序或组合管线状态；
4. 驱动针对具体 GPU 生成机器码；
5. 创建管线、descriptor layout 或其他关联对象；
6. 把结果放入进程内或磁盘缓存。

GLES 的 `glCompileShader()` / `glLinkProgram()` 可以触发编译与链接。Vulkan 使用 SPIR-V，仍可能在 `vkCreateGraphicsPipelines()`、首次使用管线或驱动内部阶段完成面向硬件的编译。SPIR-V 能前移一部分工作，但不能消除 pipeline compilation jank。

卡顿发生在 CPU 线程等待编译、驱动 worker、RenderThread、RHI 线程或 GPU 管线切换中的哪一处，由后端和驱动决定。不能把这类卡顿简单解释为“GPU 第一次看到 shader 后阻塞”。

### Android 17 的 HWUI 持久缓存

`android-17.0.0_r1` 的 HWUI Skia 路径包含：

- `pipeline/skia/PersistentGraphicsCache.*`；
- `pipeline/skia/ShaderCache.*`；
- `pipeline/skia/PipelineCache.*`；
- `renderthread/CacheManager.*`。

`CacheManager::configureContext()` 把 `PersistentGraphicsCache` 挂到 Skia 的 `fPersistentCache`。`separate_pipeline_cache()` 关闭时，shader 与 Vulkan 管线数据都交给 `ShaderCache`；该标志开启时，`PipelineCache` 只接收描述为 `VkPipelineCache` 的数据，其余条目仍进 `ShaderCache`。Vulkan 帧刷新后，代码会检查是否出现新的 pipeline cache 数据，再按大小上限和写入节流策略持久化。缓存命中可以减少重复编译，以下情况仍可能产生 miss：

- 首次使用新的 shader/pipeline 变体；
- app、framework、Skia 或 GPU 驱动更新；
- cache identity、格式或 backend 变化；
- 不同 blend、clip、色彩空间、render target 或 effect 组合；
- 缓存淘汰、损坏或被清理。

普通应用不能假设自己能直接控制 HWUI 内部缓存，也不应把历史 Flutter `--cache-sksl` 方案套到所有 Skia/HWUI 页面。

### 怎样确认是编译或管线创建卡顿

建议做冷/热两组采集：

1. 清理或使用新安装状态，首次进入目标效果；
2. 保持同一进程，再次进入同一效果；
3. 比较 UI/RenderThread/RHI 的编译、link、pipeline creation、cache load/store 和 driver slice；
4. 用 AGI 查看受支持帧的管线、shader、render pass 与命令；
5. 改变一个 shader/pipeline 维度，验证卡顿是否随 cache key 变化复现。

“第一次慢、第二次快”只是线索。首次纹理上传、字形图集、类加载、磁盘 I/O 和页面初始化也会产生相同形态。

### 预热要控制范围

应用自管 GLES/Vulkan 渲染器可以在非关键阶段创建已知 program/pipeline，并持久化 Vulkan pipeline cache。预热应：

- 只覆盖高概率场景；
- 避免阻塞启动关键线程；
- 绑定正确的渲染轮次、格式与状态变体；
- 处理驱动或应用更新后的缓存失效；
- 记录预热时间、缓存大小和实际命中率。

把所有组合一次性创建出来，可能增加启动时间、内存和 cache churn。

## Vulkan、OpenGL ES 与 ANGLE

### 性能差异来自控制模型

| 维度 | OpenGL ES | Vulkan |
| --- | --- | --- |
| 状态模型 | 全局/上下文状态较多，驱动负责更多隐式验证 | pipeline 与资源状态更显式 |
| 命令记录 | 典型路径由持有 context 的线程发调用 | 支持多线程记录 command buffer |
| 同步 | API/驱动包含较多隐式行为 | semaphore、fence、barrier 等由应用显式设计 |
| 内存 | 驱动管理较多 | 应用选择 memory type、分配与绑定 |
| pipeline | program 与驱动状态组合 | pipeline creation 更显式，也更需要缓存 |
| 工程复杂度 | 接入较简单 | 生命周期、同步和兼容判断更复杂 |

Vulkan 可以降低 CPU driver overhead，并让成熟引擎更好地并行记录命令。它也允许应用制造昂贵的屏障、频繁分配、pipeline miss 和过多 in-flight work。GLES 驱动在简单场景中可能足够快。不存在“同一 draw call 固定快十倍”这类跨设备结论。

### Vulkan 与 Android 窗口的连接

Android 17 的 `frameworks/native/vulkan/libvulkan/swapchain.cpp` 把 Vulkan 交换链图像与 `ANativeWindowBuffer` 对应起来：

- acquire 路径调用 `ANativeWindow::dequeueBuffer()`；
- image 通过 `ANativeWindowBuffer_getHardwareBuffer()` 关联底层 AHardwareBuffer；
- present 路径最终调用 `queueBuffer()` 并携带完成栅栏；
- BufferQueue、BLAST、SurfaceFlinger 和 HWC 继续负责 Android 显示后半段。

`vkQueuePresentKHR()` 返回不表示面板已显示，`vkQueueSubmit()` 返回也不表示 GPU 已完成。需要区分 GPU fence/semaphore、producer fence、SurfaceFlinger latch、display present fence 和 buffer release。

Android 17 的 loader/swapchain 路径增加 `VK_EXT_present_timing` 支持，可以按显示 ID 查询出队、queue operations end、first pixel out、first pixel visible 等阶段。它并非所有 Android 17 设备都可用：应用要枚举扩展，同时检查 `VK_KHR_present_id2`、`presentTiming` / `presentId2` feature，并在创建 swapchain 时启用 `VK_SWAPCHAIN_CREATE_PRESENT_TIMING_BIT_EXT`。缺少条件时可回退到 `VK_GOOGLE_display_timing` 或 Swappy。

### Render pass 与 tile-based GPU

移动 GPU 多采用 tile-based 架构，但 Vulkan 不保证某次绘制如何映射到物理 tile memory。频繁切换 render target、需要保留旧内容、全尺寸离屏绘制和高带宽附件可能增加 load/store。

`VK_ATTACHMENT_LOAD_OP_DONT_CARE` 或 store-op 优化只能在内容语义允许丢弃时使用。错误使用会破坏像素结果。现代 Vulkan 还支持 dynamic rendering，优化应围绕附件生命周期与实际 counter，不要机械追求最少的 `VkRenderPass` 对象。

### ANGLE：GLES API，Vulkan backend

ANGLE 可以把 GLES/EGL 调用翻译到 Vulkan。应用仍提交 GLES 状态和 draw call，ANGLE 负责状态跟踪、shader 翻译、pipeline/descriptor 管理和 Vulkan command。

ANGLE 的结果有两面：

- 统一后端有助于兼容性和驱动一致性；
- 状态翻译、pipeline 变体和缓存 miss 也会产生 CPU/内存成本。

Android 15 起 ANGLE 是可选 GLES-on-Vulkan 层；Android 17 的 `com.android.graphics.driver.prefer_angle` manifest metadata 只表达偏好，平台无法使用时会回到厂商 GLES driver。比较性能前应记录 EGL 厂商/渲染器、实际驱动、ANGLE 版本和相同负载。

Android 17 HWUI 目录中没有 Graphite pipeline。ANGLE 的开发分支也不能直接当作 `android-17.0.0_r1` 平台行为；“四级 PSO 缓存”“固定 2 ms 节流”等说法无法映射到该平台标签，不能用来解释当前版本。

## GPU 瓶颈分类

GPU 慢帧常被分为 vertex/geometry bound、fragment/fill bound 和 bandwidth bound。工程分析还要加入 CPU submission、同步/back-pressure、频率/温控和 SurfaceFlinger composition。

| 类别 | 常见现象 | 有区分力的 A/B 实验 | 需要的直接证据 |
| --- | --- | --- | --- |
| CPU / driver bound | GPU 队列有空洞，submit 晚 | 减少 draw call、状态切换或 command record | CPU profile、RHI/driver slice、GPU queue |
| Vertex / geometry bound | 几何工作增加时 GPU 时间上升 | 降低 mesh/粒子或阴影几何，保持像素条件 | vertex/primitive counter、AGI geometry |
| Fragment / fill bound | 分辨率、overdraw、shader 复杂度影响大 | 降 render scale、简化 fragment shader、缩小效果面积 | fragment/sample counter、shader 分析 |
| Bandwidth bound | 大纹理、HDR target、多 pass、upload 影响大 | 降纹理/target 带宽，减少 load/store | external-memory/cache counter、render pass |
| 同步 / back-pressure | GPU 可能有空洞，线程等 acquire/fence | 降 in-flight、修 pacing、减少资源 hazard | fence owner、queue depth、wait dependency |
| SF client composition | App buffer ready，SF GPU 工作增加 | 比较 DEVICE/CLIENT composition | layer composition type、RenderEngine、HWC |
| Thermal / power bound | 运行一段时间后频率下降 | 固定温度/电源条件做短长对照 | GPU frequency、thermal、power rail |

没有跨 GPU 通用的“Fragment Shader 超过 60% 就是 fill bound”阈值。counter 名称、单位与统计范围由 GPU 生产者/驱动在 descriptor 中声明。

### Fillrate bound

fillrate 问题与 samples、shader、blend、overdraw 和 render-target 格式有关。降低原生游戏 Surface 的 render scale，如果 GPU 时间随像素数明显下降，说明片元或带宽压力值得继续查；标准 View 页面没有通用的独立 render-scale 开关。

Debug GPU Overdraw GPU 过度绘制”只能定位 HWUI 应用窗口的逻辑重复绘制。它会额外重放一遍内容，不能在开启时测性能，也不能覆盖独立 `SurfaceView` 或最终 HWC composition。颜色语义与完整流程见 2.8。

优化方向包括：

- 移除没有视觉贡献的背景或 pass；
- 缩小模糊、阴影、半透明遮罩与后处理面积；
- 减少不必要的 MSAA/sample count；
- 降低昂贵 fragment shader 的采样和分支；
- 在视觉允许时减少 HDR/高精度中间目标；
- 避免重复的全屏离屏合成。

### Vertex bound

应先确认 GPU 的 vertex/primitive counter 与几何复杂度相关。复杂 Path 在 HWUI 中可能走 CPU tessellation、mask/coverage 或缓存，不能因为 Path 多就归为 vertex bound。

原生引擎可尝试：

- LOD、frustum/occlusion culling；
- 合理合批，减少微小绘制；
- 降低粒子、阴影 caster 与蒙皮顶点；
- 改善顶点缓冲布局和复用；
- 把与顶点无关的 CPU/RHI 成本分开。

### Bandwidth bound

带宽压力可能来自：

- 大尺寸/高精度纹理与 render target；
- 多次全屏读写和离屏绘制；
- texture upload、readback 或频繁 resolve；
- 低缓存命中、各向异性过滤或多采样；
- GPU、CPU、ISP、codec 与 display 共享内存带宽；
- SurfaceFlinger client composition。

GPU 忙碌度高而 shader stage 利用率不高，只能作为线索。应使用厂商定义的 external-memory、cache、texture、tile 或 stall counter，并做受控 A/B。

## ASTC、ETC2 与普通 Android Bitmap 的边界

ASTC/ETC2 是 GPU 纹理压缩格式，主要服务 GLES/Vulkan 游戏资源。它们不等于 JPEG/PNG 文件压缩，也不会自动改变普通 `Bitmap`、App Window `GraphicBuffer` 或 SurfaceFlinger 客户端目标的格式。

| 格式 | 能力边界 | 使用建议 |
| --- | --- | --- |
| ETC1 | RGB、4 bpp、无原生 alpha | 兼容很老的设备；alpha 常需额外纹理 |
| ETC2 | GLES 3.0 级设备广泛支持；可支持 RGB、RGBA、sRGB 等 | 现代设备的兼容 fallback |
| ASTC | 多种 block size，可在质量与大小间选择 | 设备支持时常作为现代游戏主格式 |

纹理压缩可以减少存储、GPU 内存占用和采样带宽，但也会引入编码质量、解码支持和发布包管理问题。应用应：

1. 运行时查询 GLES 扩展或 Vulkan format feature；
2. 为不支持 ASTC 的设备准备 ETC2 等 fallback；
3. 用 Play Asset Delivery 的 texture-compression targeting 分发合适资产；
4. 在同一场景比较画质、内存、加载和 GPU counter。

ASTC 块越大通常压缩率越高、质量风险也越高。透明纹理、法线、UI 图集和 HDR 资源应分别测试，不能只按文件大小选格式。

## 分块式渲染的性能含义

典型分块式 GPU 会先把几何分配到屏幕图块，再在片上存储中完成一个图块的 raster、fragment 和混合，最终把需要保留的结果写回设备内存。

这能减少某些中间颜色的外部内存流量，但不会消除过度绘制、纹理采样和复杂着色器的成本。以下行为仍可能增加开销：

- 渲染轮次开始时加载已有附件；
- pass 结束时保存附件；
- tile memory 容量不足或格式过大；
- 多个全屏 target、resolve、readback；
- 半透明内容和依赖旧颜色的混合；
- driver 无法应用预期的隐藏面或压缩优化。

不同 Adreno、Mali、PowerVR 或其他 GPU 的图块大小、压缩、early test 和 counter 都不同。架构名只能指导实验，不能代替目标设备数据。

## GPU 内存：对象、分配与共享

### Android 17 的对象链

从应用到内核，可以按以下层次理解：

```text
Bitmap / HardwareBuffer / Surface / ANativeWindow
  → AHardwareBuffer / ANativeWindowBuffer / GraphicBuffer
  → GraphicBufferAllocator + graphics allocator HAL
  → GraphicBufferMapper + mapper HAL
  → native_handle: fd + metadata
  → dma-buf exporter / heap or vendor allocator
  → GPU, codec, SurfaceFlinger, HWC imports and mappings
```

这些名称不表示“每层复制一份像素”。多个进程/设备可以导入同一个 dma-buf，对应不同虚拟映射、IOMMU 映射和引用。GraphicBuffer 是原生图形栈中的包装对象，AHardwareBuffer 是公开 NDK/Java 边界，底层句柄描述共享缓冲。

Android 17 的 `frameworks/native/libs/ui/GraphicBufferAllocator.cpp` / `GraphicBufferMapper.cpp` 对接 graphics allocator/mapper；`hardware/interfaces` 同时保留历史 HIDL 版本，并提供分配器 AIDL 与映射器 stable-C 接口。具体产品使用哪个版本，应看 vendor manifest 和运行时服务。

### Gralloc 根据描述符选择布局

分配请求至少包含 width、height、layer count、format 和 usage。usage 会描述 CPU 读写、GPU texture/render target、video encoder、composer、protected content 等需求。Allocator/mapper 与厂商 gralloc 可以据此选择：

- stride 与对齐；
- 线性、tiled 或厂商压缩布局；
- 元数据与平面；
- cache 属性；
- protected 或设备专用堆。

`width × height × bytesPerPixel` 只能估算简单线性格式。应用不要依赖未公开的物理布局。

### BufferQueue 槽位不等于常驻分配

BufferQueue 管理槽位、dequeued/acquired 状态和缓冲引用。Producer dequeue 时可以触发新分配，也可以复用已有缓冲。buffer 数量受 producer/consumer、usage、尺寸变化、async/shared 模式和在途约束影响。

释放栅栏表示消费者何时不再使用旧缓冲，生产者必须在重新写入前遵守依赖。队列满或释放晚会让出队、获取、交换或显示提交等待，这属于背压。

### ION 到 DMA-BUF Heaps

Android 12 GKI 2.0 开始用 DMA-BUF 堆替代 ION。DMA-BUF 堆提供稳定 UAPI，并按 `/dev/dma_heap/<name>` 分开访问控制；vendor 仍可提供特定堆，protected heap 也常由厂商实现。

内核源码锚点 `android17-6.18-2026-06_r6` 包含以下相关文件：

- `drivers/dma-buf/dma-buf.c`；
- `drivers/dma-buf/dma-heap.c`；
- `drivers/dma-buf/dma-fence.c`；
- `drivers/dma-buf/sync_file.c`。

通用内核定义共享、引用和同步语义。GPU page table、压缩 metadata、heap 选择、eviction 和 job scheduler 多在厂商驱动。

### 16 KB 页与 GPU buffer

16 KB 页兼容性约束原生 ELF 的段对齐、APK 中未压缩 `.so` 的 ZIP 对齐，以及 mmap 等代码对 page size 的假设。它不会把 gralloc 缓冲自动改成线性 16 KB 分块，也不表示每张纹理固定浪费 16 KB。GraphicBuffer 仍应以 allocator 返回的 allocation size、stride、plane layout、heap 与映射数据为准。

## GPU 内存怎样追踪

没有单一数字能代表“应用独占 GPU 内存”。同一 dma-buf 可被应用、SurfaceFlinger、codec 和 HWC 导入，简单相加会重复计数。

### Perfetto

根据设备支持，可以采集：

- `linux.ftrace` 中的 `gpu_mem/gpu_mem_total`：进程 GPU memory total；
- `vulkan.memory_tracker`：Vulkan allocation/bind；
- `gpu.counters`，或 `gpu.counters.adreno` 等硬件后缀名称：设备声明的 counters；
- `gpu.renderstages`，或 `gpu.renderstages.mali` 等硬件后缀名称：graphics/compute submission timeline；
- dma-buf、process memory、频率和调度 ftrace。

Perfetto 对 data source 名称做精确匹配，带后缀的 producer 必须在 trace config 中写出完整名称。counter id/name、单位和分组由 descriptor 声明；不存在跨 Android 16/17 通用的单一 `gpu_busy` 轨道或固定计数器 ID。

### 系统与厂商数据

按设备权限与构建类型补充：

- `dumpsys meminfo <package>` 的 graphics/EGL 等分类；
- `dumpsys SurfaceFlinger`、layer/buffer dump；
- dma-buf heap/bufinfo；
- Vulkan 分配回调或引擎分配器遥测；
- Adreno/Mali/PowerVR 的厂商 profiler；
- AGI 内存面板与 Vulkan memory tracker。

这些口径覆盖范围不同。报告中应写清是否包含 driver private allocation、共享缓冲、SurfaceFlinger、纹理、render target 和缓存。

## Android 16 GPU Headroom

API 36 的 `SystemHealthManager.getGpuHeadroom()` 返回 `[0, 100]` 的可用 GPU 容量估计，0 表示系统无法再提供更多 GPU 资源；暂时无数据时返回 `Float.NaN`，设备不支持时抛 `UnsupportedOperationException`。

每次有效调用至少包含一次同步 Binder transaction，官方说明它可能超过 1 ms，首次调用或更换参数还可能因延迟初始化更慢。不能在 UI、RenderThread 或游戏关键 render loop 中逐帧调用。

以下示例把一次查询放到后台 executor，并读取设备声明的最小采样间隔；周期调度应保证相邻查询不短于这个值：

```java
SystemHealthManager health =
        context.getSystemService(SystemHealthManager.class);

executor.execute(() -> {
    try {
        long intervalMs = health.getGpuHeadroomMinIntervalMillis();
        float headroom = health.getGpuHeadroom(null);
        if (!Float.isNaN(headroom)) {
            gpuPolicy.onSample(headroom, intervalMs);
        }
    } catch (UnsupportedOperationException ignored) {
        gpuPolicy.disableHeadroomInput();
    }
});
```

这段代码只展示线程和异常边界。采样调度、阈值、滞回、最短档位保持时间与画质策略应根据应用测试确定。

Headroom 是容量估计，不能区分片元、顶点或带宽瓶颈，也不表示某一帧的 GPU duration。应结合 thermal status、帧时间、GPU 计数器和业务质量档位使用。

## Profiling 工具怎样分工

### Perfetto：定位系统责任边界

Perfetto 适合把以下时间放在同一时钟域：

- UI、RenderThread、Game/RHI 和驱动线程；
- GPU render stages、频率和 counters（设备支持时）；
- BufferQueue/BLAST、fence 和 FrameTimeline；
- SurfaceFlinger、RenderEngine、HWC 与 display present；
- CPU scheduling、thermal、memory 和 I/O。

用 FrameTimeline 选中目标 `SurfaceFrame` / `DisplayFrame` 后，再追 producer fence 和 GPU submission。GPU 数据缺失时，不要用 RenderThread 切片代替 GPU completion。

### APA 与 AGI：区分系统 profile、单帧分析

截至 2026 年 5 月，Android Performance Analyzer（APA）处于 public beta，官方已把它作为 system profiling 的推荐工具，可联合查看 CPU、GPU、memory、power 和系统行为。AGI System Profiler 仍可采集 Perfetto 与 GPU 数据，但新建 system profile 应优先评估 APA 的设备支持与数据源覆盖。

AGI Frame Profiler 继续负责单帧检查：对受支持应用查看 Vulkan API call、framebuffer、draw call、pipeline、shader、texture、render state 与内存。

当前 AGI Frame Profiler 直接支持 Vulkan；GLES 单帧分析使用 OpenGL on ANGLE 模式，由工具的 ANGLE 构建转成 Vulkan 进行抓取。capture 和插桩会改变时序，适合分析命令与相对差异，不宜把抓帧耗时当作生产性能。

工具版本变化独立于 Android platform，要记录 APA/AGI 版本、capture 模式与 supported-device 状态。

### 厂商 profiler

- Qualcomm 平台可用 Snapdragon Profiler/相关厂商 GPU 工具；
- Arm Mali 可用 Streamline 与 Mali counter；
- 其他 GPU 使用对应 IHV 工具。

厂商工具能解释缓存、shader core、tiler、external memory 或停顿等硬件 counter。counter 语义和权限随 GPU/driver 变化，不能跨厂商直接比较数值。

### GPU 呈现模式分析柱状图

开发者选项中的柱状图主要反映 HWUI 各阶段的时间代理。它适合快速发现 View 页面是否接近帧预算，不适合分析独立 Vulkan game Surface，也不能单独区分顶点、fragment 和 bandwidth。

## 一套可复现的 GPU 排查流程

### 1. 固定场景

记录设备、build、GPU/driver、刷新率、分辨率/render scale、图形 API、ANGLE 状态、温度、充电状态和页面数据。预热与冷启动要分开。

### 2. 建立 Surface 拓扑

列出每个可见内容对象的 Producer、Consumer、SurfaceFlinger Layer、buffer format/size、fence 和 composition type。TextureView 输入需要展开到宿主 HWUI，SurfaceView 则单独跟踪。

### 3. 锁定一帧

用 FrameTimeline 选择 janky App `SurfaceFrame` 和对应 `DisplayFrame`。对 Native Graphics/游戏，额外记录引擎帧 ID、submit、swap/present、buffer id 和 producer fence。

### 4. 分开 CPU、GPU 与显示

- submit 晚：查 UI/Game/RHI/driver CPU；
- submit 早、producer fence 晚：查 GPU workload、queue、frequency；
- buffer ready、display 晚：查 SF/HWC/composition；
- 获取、出队或交换周期等待：查节拍、在途帧和释放操作。

### 5. 用 A/B 区分瓶颈

一次只改变一个维度：

- 渲染比例或效果面积；
- fragment shader/采样；
- mesh/粒子/阴影几何；
- texture/target 格式与分辨率；
- 绘制调用/状态数量；
- SurfaceFlinger DEVICE/CLIENT 条件；
- 在途帧与节拍控制。

比较 GPU completion、counter、帧 deadline、功耗和画质。平均 FPS 不能代替长帧分布与输入到 present 延迟。

### 6. 检查首次编译与资源上传

对比冷/热路径，查 pipeline/cache、texture upload、glyph atlas、磁盘 I/O 和 driver worker。不要把所有首次慢帧都归因于 shader。

### 7. 做持续运行测试

至少覆盖热稳定后的频率、温度和功耗。首分钟通过、十分钟降频的方案仍需调整画质、帧率或 ADPF 策略。

## 示例：图片列表滚动

图片列表同时可能有 UI、纹理上传、采样、overdraw 和带宽压力。不应预设“图片太大就是 bandwidth bound”，可以按以下证据推进：

1. Layout Inspector 与“调试 GPU 过度绘制”检查宿主窗口的重复背景；
2. 关闭 overdraw 调试后抓取 Perfetto，确认 UI、RenderThread、GPU 完成和 App deadline；
3. 对比首次进入与二次滚动，分开 decode/upload/cache miss；
4. 固定图片内容，A/B 纹理尺寸、色彩格式、圆角/阴影和预取；
5. 有 GPU 计数器时观察片元、texture、cache/external memory 的相对变化；
6. 若存在 TextureView/SurfaceView，展开独立 Producer 和最终合成。

如果降低图片纹理尺寸后 upload、GPU time 和外部带宽同时下降，证据支持纹理/带宽方向；如果只有 UI 线程解码或布局耗时下降，应记录为 CPU 改善。

## Android 12–17 相关边界

| 版本 | 与 GPU 渲染直接相关的变化 |
| --- | --- |
| Android 12 / API 31 | FrameTimeline；`FrameMetrics.GPU_DURATION` 与 `DEADLINE`；GPU/SF 责任更容易关联。 |
| Android 13 / API 33 | AGSL `RuntimeShader`；Choreographer FrameData/FrameTimeline 公共 API。 |
| Android 15 / API 35 | ANGLE 作为可选 GLES-on-Vulkan 层；支持设备引入 ARR。 |
| Android 16 / API 36 | GPU Headroom；64 位、非 low-memory launch device 的 Vulkan 1.4 要求；`RuntimeColorFilter` / `RuntimeXfermode`。 |
| Android 17 / API 37 | 当前源码锚点；`VK_EXT_present_timing`；Jetpack WebGPU `1.0.0-alpha05`；GLES `prefer_angle` 请求。HWUI 仍按设备选择 SkiaOpenGL/SkiaVulkan。 |

版本号不能替代运行时 capability。Vulkan extension、ASTC、ANGLE、GPU counter、ARR 和 HWC 平面都要在目标设备上查询。

## Kernel 与厂商驱动边界

`android17-6.18-2026-06_r6` 固定了通用 dma-buf、dma-heap、dma-fence/sync_file 和 scheduler 语义。它不能证明目标设备使用哪种 GPU job scheduler、tile 大小、压缩、counter 或内存回收策略。

fence wait 只说明依赖尚未完成。判断 GPU 为何晚，需要找到 fence owner、对应提交、frequency、queue 和负载。dma-buf 被多个模块共享时，还要避免重复计算内存。

## 常见误区

### “Perfetto 有 GPU Track，就能直接看 Vertex/Fragment 时间”

设备可能只提供粗粒度 render stage 或 busy/frequency。Vertex、fragment、tiler、cache 和带宽通常依赖厂商 counter 或 AGI/厂商 profiler。

### “Vulkan 使用 SPIR-V，所以没有 shader jank”

驱动仍需生成硬件代码并创建管线。pipeline cache、预热和稳定 state 设计依然重要。

### “Vulkan 一定比 GLES 快”

结果取决于 renderer、driver、同步、内存、pipeline 和负载。Vulkan 给出更多控制，也要求应用正确使用这些控制。

### “ANGLE 固定增加某个百分比的开销”

ANGLE 可能增加翻译成本，也可能因 Vulkan 驱动质量改善表现。只能在相同设备、driver 和场景下测量。

### “GPU busy 高就一定有问题”

稳定按 deadline 完成的高利用率可能是有效工作。还要看 deadline、功耗、温度和画质目标；系统或其他进程也可能占用 GPU。

### “GraphicBuffer 都计入应用 RSS”

图形缓冲可通过 dma-buf 跨进程和设备共享，RSS/PSS、gpu_mem、dumpsys 和驱动统计口径不同。归属需要结合 exporter、importer 与引用生命周期。

### “SurfaceFlinger 合成不算应用的 GPU 问题”

它不属于 App renderer，但会影响最终 DisplayFrame，并与应用争用 GPU/带宽。报告时应分开归因，再说明共同资源影响。

## Android 17 源码入口

- HWUI [`DrawFrameTask.cpp`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/libs/hwui/renderthread/DrawFrameTask.cpp)、[`CanvasContext.cpp`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/libs/hwui/renderthread/CanvasContext.cpp)：RenderThread 同步、绘制和窗口缓冲。
- HWUI [`PersistentGraphicsCache.cpp`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/libs/hwui/pipeline/skia/PersistentGraphicsCache.cpp)、[`ShaderCache.cpp`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/libs/hwui/pipeline/skia/ShaderCache.cpp)、[`PipelineCache.cpp`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/libs/hwui/pipeline/skia/PipelineCache.cpp)：Skia shader/pipeline cache。
- Native [`GraphicBuffer.cpp`](https://android.googlesource.com/platform/frameworks/native/+/android-17.0.0_r1/libs/ui/GraphicBuffer.cpp)、[`GraphicBufferAllocator.cpp`](https://android.googlesource.com/platform/frameworks/native/+/android-17.0.0_r1/libs/ui/GraphicBufferAllocator.cpp)、[`GraphicBufferMapper.cpp`](https://android.googlesource.com/platform/frameworks/native/+/android-17.0.0_r1/libs/ui/GraphicBufferMapper.cpp)：图形缓冲包装、分配和映射。
- Native [`BufferQueueProducer.cpp`](https://android.googlesource.com/platform/frameworks/native/+/android-17.0.0_r1/libs/gui/BufferQueueProducer.cpp)、[`Surface.cpp`](https://android.googlesource.com/platform/frameworks/native/+/android-17.0.0_r1/libs/gui/Surface.cpp)、[`BLASTBufferQueue.cpp`](https://android.googlesource.com/platform/frameworks/native/+/android-17.0.0_r1/libs/gui/BLASTBufferQueue.cpp)：dequeue/queue、slot 与事务。
- Vulkan [`swapchain.cpp`](https://android.googlesource.com/platform/frameworks/native/+/android-17.0.0_r1/vulkan/libvulkan/swapchain.cpp)：swapchain image、ANativeWindowBuffer 与 queueBuffer。
- SurfaceFlinger [FrontEnd](https://android.googlesource.com/platform/frameworks/native/+/android-17.0.0_r1/services/surfaceflinger/FrontEnd/)、[`HWComposer.cpp`](https://android.googlesource.com/platform/frameworks/native/+/android-17.0.0_r1/services/surfaceflinger/DisplayHardware/HWComposer.cpp)：LayerSnapshot、CLIENT/DEVICE 与 present。
- Graphics HAL [allocator AIDL](https://android.googlesource.com/platform/hardware/interfaces/+/android-17.0.0_r1/graphics/allocator/aidl/)、[mapper stable-C](https://android.googlesource.com/platform/hardware/interfaces/+/android-17.0.0_r1/graphics/mapper/stable-c/)：allocator/mapper 当前接口。
- Kernel [`dma-buf.c`](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/drivers/dma-buf/dma-buf.c)、[`dma-heap.c`](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/drivers/dma-buf/dma-heap.c)、[`dma-fence.c`](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/drivers/dma-buf/dma-fence.c)、[`sync_file.c`](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/drivers/dma-buf/sync_file.c)：共享缓冲与同步。

## 官方资料

- [Android graphics architecture: BufferQueue and Gralloc](https://source.android.com/docs/core/graphics/arch-bq-gralloc)
- [Transition from ION to DMA-BUF heaps](https://source.android.com/docs/core/architecture/kernel/dma-buf-heaps)
- [Perfetto GPU data sources](https://perfetto.dev/docs/data-sources/gpu)
- [Android GPU Inspector](https://developer.android.com/agi)
- [AGI Frame Profiler](https://developer.android.com/agi/frame-trace/frame-profiler)
- [Android Performance Analyzer](https://developer.android.com/android-performance-analyzer)
- [SystemHealthManager GPU Headroom](https://developer.android.com/reference/android/os/health/SystemHealthManager#getGpuHeadroom(android.os.GpuHeadroomParams))
- [Vulkan on Android](https://developer.android.com/games/develop/vulkan/overview)
- [Vulkan frame pacing extensions](https://developer.android.com/games/develop/vulkan/frame-pacing-extensions)
- [WebGPU for Android](https://developer.android.com/develop/ui/views/graphics/webgpu)、[AndroidX WebGPU releases](https://developer.android.com/jetpack/androidx/releases/webgpu)
- [Texture compression](https://developer.android.com/games/optimize/textures)
- [FrameTimeline](https://perfetto.dev/docs/data-sources/frametimeline)
