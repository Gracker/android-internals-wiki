---
title: "GPU 图形调试与分析工具"
chapter: "14.15"
section: "14.15"
status: finalized
pipeline_stage: ready-to-publish
applicable_versions: "Android 11 (API 30) - Android 17 (API 37)（AGI 要求 Android 11+ 受支持设备；APA 在 Android 12+ 体验最佳；Sokatoa 要求 Android 13+）"
tags: ["gpu", "agi", "renderdoc", "sokatoa", "gapid", "gpu-counter", "profiling", "vulkan", "opengl-es"]
confidence: "medium"
sources:
- type: material
  path: Cubox/基于gpu counters数据的性能优化-2025-02-27.md
- type: official
  path: https://developer.android.com/android-performance-analyzer
- type: official
  path: https://developer.android.com/blog/posts/introducing-android-performance-analyzer-the-next-evolution-in-profiling-for-android
- type: official
  path: https://developer.android.com/agi
- type: official
  path: https://developer.android.com/agi/start
- type: official
  path: https://developer.android.com/agi/frame-trace/frame-profiler
- type: official
  path: https://perfetto.dev/docs/data-sources/gpu
- type: official
  path: https://perfetto.dev/docs/data-sources/frametimeline
- type: aosp
  path: https://android.googlesource.com/platform/external/perfetto/+/refs/tags/android-17.0.0_r1/protos/perfetto/config/gpu/gpu_counter_config.proto
- type: aosp
  path: https://android.googlesource.com/platform/external/perfetto/+/refs/tags/android-17.0.0_r1/protos/perfetto/config/gpu/gpu_renderstages_config.proto
- type: aosp
  path: https://android.googlesource.com/platform/external/perfetto/+/refs/tags/android-17.0.0_r1/protos/perfetto/trace/gpu/gpu_counter_event.proto
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/services/surfaceflinger/FrameTracer/
- type: official
  path: https://developer.android.com/games/develop/vulkan/overview
- type: official
  path: https://developer.android.com/guide/topics/manifest/profileable-element
- type: reference
  path: https://github.com/sarc-acl/sokatoa
- type: reference
  path: https://developer.arm.com/Tools%20and%20Software/Arm%20Performance%20Studio
- type: reference
  path: https://developer.arm.com/tools-and-software/streamline-performance-analyzer
- type: reference
  path: https://developer.arm.com/tools-and-software/renderdoc-for-arm-gpus
- type: reference
  path: https://developer.qualcomm.com/software/snapdragon-profiler
- type: kernel
  path: https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/drivers/devfreq/
- type: kernel
  path: https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/drivers/dma-buf/dma-fence.c
last_verified: "2026-08-13"
last_verified_against: "APA 页面更新至 2026-08-12；AGI 文档更新至 2026-05-19；Android Vulkan / ANGLE 页面更新至 2026-06-11；Perfetto GPU 与 FrameTimeline 当前文档；Sokatoa README 当前要求；AOSP android-17.0.0_r1 GPU proto"
related_chapters: ["2.10", "2.14", "13.3", "14.1"]
task6_state: reviewed
task9_state: reviewed
task2b_state: fixed
---
# 14.15 GPU 图形调试与分析工具

## 分析对象是一条显示时间线

本文以 Android 17 / API 37 / `android-17.0.0_r1` 作为平台源码基线，以 `android17-6.18-2026-06_r6` 作为 Android common kernel 的源码参照。商业设备可能包含更新或厂商修改，报告仍要记录设备实际 build、kernel 和 GPU driver。GPU producer（向 Perfetto 注册数据源并写入 GPU 数据的组件）、用户态驱动和内核 GPU 驱动大多由厂商提供；两台设备即使都是 API 37，可采集的数据源、counter（硬件计数器）和驱动事件也可能不同。

一次 draw API（提交绘制命令的图形接口）返回，只说明 CPU 已执行到某个提交点。GPU 可能仍在队列中工作，承载图像内容的 buffer 也可能继续等待 SurfaceFlinger latch、HWC 合成或 display present。判断 GPU 瓶颈时，要把以下节点放进同一帧：

1. 应用何时开始逻辑与录制命令；
2. CPU 何时 submit（提交）GPU 工作；
3. GPU 工作何时开始和完成；
4. producer 何时向 BufferQueue 提交 buffer，acquire fence 何时 signal；
5. SurfaceFlinger 何时 latch，是否进入 RenderEngine client composition；
6. HWC 和显示端何时 present。

这些词对应不同时间点：BufferQueue 是图像 buffer 的生产者—消费者队列；acquire fence 是“消费者现在可以安全读取该 buffer”的异步完成信号；latch 是 SurfaceFlinger 选中本帧 buffer；HWC（Hardware Composer）是显示硬件合成层；present 是把合成结果交给显示端。RenderEngine client composition 则表示 SurfaceFlinger 使用 GPU 完成合成。

显示路径需要按这些节点分层观察。标准 HWUI（Android UI 硬件加速渲染库）窗口通常从主线程和 `RenderThread` 开始；SurfaceView、游戏、Camera、视频和自有 Vulkan render loop（持续录制并提交帧的渲染循环）应先找实际承载画面的 Surface 与 producer 线程。只看宿主 Activity 的 FrameTimeline，可能漏掉独立 Surface 的画面。

## 工具按证据深度分层

| 层级 | 适合回答的问题 | 工具 | 主要限制 |
|---|---|---|---|
| 系统时间线 | 哪一帧晚，CPU、GPU、SurfaceFlinger、HWC 谁先偏离预算 | Perfetto、Android Performance Analyzer（APA） | 设备未暴露 GPU producer 时，GPU 轨道可能为空 |
| 系统级 GPU | GPU 频率、render stage、计数器与 CPU 调度如何关联 | APA、AGI System Profiler、厂商 system profiler | counter 名称与语义依赖 GPU 和驱动 |
| 单帧捕获 | 哪个 render pass、draw、pipeline、shader 或资源有问题 | AGI Frame Profiler、RenderDoc、Arm Frame Advisor | 捕获与回放会改变时序，不能拿来测正常帧率 |
| 多帧捕获 | 间歇性 pipeline/state 变化、连续帧资源与 shader 差异 | Sokatoa | 面向 Vulkan，要求 Android 13+，注入 layer 需要 debuggable APK 或 root |
| 微架构分析 | ALU、纹理、tile、cache、带宽、occupancy 受限在哪里 | Arm Streamline、Snapdragon Profiler、厂商工具 | 结论只能绑定对应 GPU 架构与 counter 文档 |

表中的 render stage 是 GPU 工作的一个执行阶段；render pass 定义一组 attachment（渲染输入/输出图像）及其处理过程；pipeline 是着色器与固定功能状态的组合；shader 是运行在 GPU 上的程序。ALU 是算术逻辑单元，tile 是分块渲染中的小块区域，cache 是片上缓存，occupancy 表示执行资源被并行工作占用的程度，具体计算方式仍由厂商定义。

可以先用系统 Trace 找到异常时间窗，再通过单变量实验缩小资源类型，最后用帧捕获或厂商 counter 解释原因。跳过系统时间线直接抓一帧，既可能抓到正常帧，也可能把 SurfaceFlinger 或 BufferQueue 的等待误判为应用 shader 开销。

## Perfetto：Android 17 的 GPU 数据源

Perfetto 的 GPU 能力由多个数据源组成，每个数据源回答不同问题。`linux.ftrace` 是 Linux 内核事件追踪数据源；其余 GPU 数据源通常由系统或厂商 producer 提供。

| 数据源 | Android 17 中的用途 | 不能直接推出的结论 |
|---|---|---|
| `linux.ftrace` 的 `power/gpu_frequency` | GPU 频率变化 | GPU 利用率、shader 耗时 |
| `linux.ftrace` 的 `gpu_mem/gpu_mem_total` | GPU 内存总量事件 | 带宽、完整对象归属或泄漏 |
| `gpu.counters` | 周期采样设备 producer 暴露的硬件计数器 | 跨厂商统一阈值 |
| `gpu.renderstages` | graphics/compute submission 的 GPU 活动时间线 | 每个 draw 的完整 pipeline state |
| `vulkan.memory_tracker` | Vulkan 内存分配（allocation）与绑定（bind）事件 | GLES 和驱动私有内存的完整视图 |
| `gpu.log` | GPU producer 提供的调试消息 | 所有厂商的卡死（hang）、访问或执行故障（fault）与 GPU 重置（reset） |

下面的 TraceConfig（Perfetto 录制配置）展示 Android 17 tag 中 GPU frequency、GPU memory 和 render stages 的请求方式。设备也可能只注册带厂商后缀的名字，例如 `gpu.renderstages.mali`；录制前应查询 data-source descriptor，也就是 producer 上报的数据源能力说明。

```textproto
buffers {
  size_kb: 32768
  fill_policy: RING_BUFFER
}

data_sources {
  config {
    name: "linux.ftrace"
    ftrace_config {
      ftrace_events: "power/gpu_frequency"
      ftrace_events: "gpu_mem/gpu_mem_total"
    }
  }
}

data_sources {
  config {
    name: "gpu.renderstages"
    gpu_renderstages_config {
      low_overhead: true
    }
  }
}
```

这段配置只说明要请求哪些数据，不能保证每台设备都会返回结果。内核 tracepoint（内核事件记录点）、GPU producer、数据源名称、应用 Graphics API、权限或驱动支持不满足时，都可能产生空轨道。`low_overhead` 会把 render stages 合并为一个 workload stage，以更少细节换取更低 GPU 扰动；只有短窗口确实需要分开观察 load/store stage 时才关闭它。

### `gpu.counters` 的正确配置

Android 17 的 `GpuCounterConfig` 包含 `counter_period_ns`、`counter_ids`、`instrumented_sampling` 和 `fix_gpu_clock`。常规周期采样只需要前两个字段。`counter_ids` 是 repeated（可重复）字段，在 TextProto（Protocol Buffers 的文本格式）中要逐项重复书写。`instrumented_sampling` 会在 GPU command buffer 中插入采样，`fix_gpu_clock` 会请求固定 GPU 频率；两者都会改变采集方式或运行条件，不应默认用于正常基线。

下面的 counter ID 只用于展示配置结构，必须替换为目标设备 descriptor 中公布的 ID。

```textproto
data_sources {
  config {
    name: "gpu.counters"
    gpu_counter_config {
      counter_period_ns: 1000000
      counter_ids: 1
      counter_ids: 3
    }
  }
}
```

`android-17.0.0_r1` 的 `GpuCounterEvent` 支持两类 descriptor。Android OEM producer 按 CDD/CTS（Android 兼容性定义与兼容性测试套件）要求，使用全局 counter ID 的 `GpuCounterDescriptor`；sequence-scoped（只在一条可信数据序列内有效）的 `InternedGpuCounterDescriptor` 面向多 producer、多 GPU 等复杂用途。两种模式处理的是 descriptor 传输和 ID 作用范围，并未统一各家 counter 的名称、单位或计算方法。

### 频率、利用率和带宽怎么读

GPU frequency 反映 DVFS（Dynamic Voltage and Frequency Scaling，动态电压频率调节）的当前频点。高频可能来自持续负载、响应性策略或固定性能模式；低频可能来自轻载、温控、功耗限制或 governor（频率调节策略）选择。单看频率无法判断 GPU 是否占满。

“GPU utilization”“shader core active”“ALU busy”“external memory read”这类 counter 的分母、采样窗口和包含的等待状态由厂商定义。分析时应：

1. 找到目标帧对应的 GPU stage；
2. 读取同一时间窗内的 counter；
3. 以同一设备、同一画质和相近热状态的基线比较；
4. 每轮只改变分辨率、pass、shader、纹理或 draw 组织中的一个变量；
5. 用该 GPU 的 counter 文档解释变化。

没有通用的“ALU 超过 80%”或“单帧超过多少 draw”阈值。draw 数量增加可能拖慢 CPU 侧的驱动提交，也可能让 GPU 工作量上升；要结合调用栈、GPU stage 和硬件 counter 区分这两种情况。

## 从 Trace 判断瓶颈方向

下表中的 deadline 是一帧必须完成的时间点；backpressure（背压）表示下游队列已满，反过来阻塞上游；frame pacing 是安排帧生成与提交节奏；completion fence 在 GPU 工作完成后发出信号；release fence 通知 producer 何时可以重新使用 buffer；present fence 则标记一帧完成显示的时间。

| 观察到的证据 | 候选方向 | 下一步 |
|---|---|---|
| CPU 录制或 submit 已晚，GPU stage 随后正常完成 | CPU、锁、调度、资源加载、driver CPU 开销 | 看 CPU 调度事件（sched）、调用栈、锁、Binder IPC 与命令录制 |
| CPU submit 按时，应用 GPU completion fence 越过 deadline | 应用提交的 GPU 工作量 | 降分辨率或关闭一个 pass，再进入帧 profiler |
| producer 长时间卡在 acquire、dequeue 或 swap，GPU stage 不长 | BufferQueue backpressure、release fence、frame pacing | 看队列深度、release fence、present 间隔 |
| 应用 buffer 按时，SurfaceFlinger 的 client composition 或 present 晚 | RenderEngine、HWC、显示端 | 看合成类型（composition type）、RenderEngine、HWC 与 present fence |
| GPU track 空白 | 数据源或设备支持缺失，也可能没有覆盖该 API | 查 descriptor、trace config、驱动与权限 |
| GPU frequency 高，frame 正常 | 当前 DVFS 状态 | 不单独作为性能缺陷 |

FrameTimeline 的 `GPU Composition` 只说明 SurfaceFlinger 是否使用 GPU/client composition，不说明应用内容是否由 GPU 生成。游戏 Surface 可以由应用 GPU 渲染，随后由 HWC 直接扫描输出；此时应用仍可能 GPU bound（GPU 工作决定帧耗时），而 DisplayFrame（SurfaceFlinger 把多个 layer 合成后的屏幕帧）没有 client composition 标记。

Perfetto 官方文档仍说明 SurfaceView 不受标准 FrameTimeline 支持。遇到游戏、Camera、视频或独立 native Surface，应结合 layer name（SurfaceFlinger 图层名）、buffer frame number、`android.surfaceflinger.frame`、acquire/release fence、HWC 和 display present 还原显示路径。

## Android Performance Analyzer（APA）

截至 2026 年 8 月 13 日，APA 下载页已不再标注 Beta。APA 以 Perfetto 为系统追踪基础，覆盖 CPU、GPU、内存和功耗，并支持自定义 TraceConfig。官方说明 Android 12+ 设备能提供较好的 system-wide（应用与系统进程同一时间线）性能分析、GPU counter 和 render stage 体验。

APA 与 Perfetto 的区别主要在入口和分析体验：

- APA 提供独立桌面应用、项目管理、截图、轨道整理、标注和 GPU counter 浏览；当前首页还展示了 Vulkan render pass debug marker 和多 trace A/B 对比；
- Perfetto CLI 与 Trace Processor 适合固定配置、批量采集、SQL 回归和自动化；
- 两者都受目标设备 GPU producer 与驱动数据限制。

AGI quickstart 当前仍把 APA 列为 system profiling 的推荐工具。AGI System Profiler 仍可使用，尤其是团队已有 AGI 设备验证和 counter 流程时。2026 年 5 月的 APA 公告把逐帧 capture/replay（捕获与回放）列为后续能力；2026 年 8 月的 APA 首页虽然新增 Vulkan debug marker 展示，却仍没有发布逐 draw 的 Frame Profiler 文档。因此不能把 trace 中的 render pass 名称，当成 AGI Frame Profiler 那类单帧命令与资源捕获。

## Android GPU Inspector（AGI）

AGI 运行在 Android 11+ 的受支持真机上，并在首次连接以及 Android 或 GPU driver 变化后执行兼容性验证。官方列出的 System Profiler GPU 包括 Qualcomm Adreno、Arm Mali 和 Imagination PowerVR。设备验证失败或 counter 缺失，只能说明当前设备、系统与驱动组合没有通过 AGI 要求。

AGI 有两种主要模式：

| 模式 | 数据 | 使用位置 |
|---|---|---|
| System Profiler | CPU/GPU/内存/电池、GPU counter、系统时间线 | 找到长时间运行中的异常窗口 |
| Frame Profiler | Vulkan API call、framebuffer、mesh draw、内存、pipeline、state、shader、texture | 检查单帧命令与资源 |

AGI quickstart 要求目标应用设置 `android:debuggable="true"`。原生 Vulkan 应用还要启用 validation layer（检查 Vulkan API 使用是否合法的验证层），先修复已有 validation error，再采集 profile。AGI 会管理自身的捕获流程；手工配置全局 Vulkan layer 时，应严格使用当前 AGI 文档给出的包名、ABI（Application Binary Interface，应用二进制接口）和清理命令，避免把验证层与捕获层写进同一项配置。

### OpenGL ES on ANGLE

AGI Frame Profiler 的类型选择是 `Vulkan` 或 `OpenGL on ANGLE`。ANGLE 会把 OpenGL ES（GLES）命令翻译为 Vulkan。GLES 应用经这条路径捕获后，看到的是翻译生成的 Vulkan command、pipeline 和 shader；backend 指实际执行图形命令的后端实现。若问题只在设备原生 GLES driver 出现，这份 capture 已改变 backend，必须同时保留原生路径的 Perfetto、日志和厂商数据。

Android 15+ 提供按包测试 ANGLE 的入口。Android 17 又允许 game 在 manifest 中表达“优先使用 ANGLE”的请求：

```xml
<application android:appCategory="game">
    <meta-data
        android:name="com.android.graphics.driver.prefer_angle"
        android:value="true" />
</application>
```

这项 metadata 是请求信号，不保证系统选择 ANGLE。设备配置、graphics driver 包、应用兼容性和厂商策略仍会参与选择。即使系统是 Android 17，也不能据此认定所有 GLES 应用默认运行在 ANGLE 上。

对照 native GLES 与 ANGLE 时，可用官方测试命令设置 `angle_gl_driver_selection_pkgs` 和 `angle_gl_driver_selection_values=angle`，重启目标进程后再检查 EGL vendor/renderer、进程加载的 library、Graphics Driver 日志和 `gpu.angle` trace event。这两个 global setting 在重启后仍会保留，测试结束必须删除，避免影响后续基线。

## RenderDoc：图形状态与资源调试

RenderDoc 可以检查帧内 API event、pipeline state、texture、buffer、framebuffer 和 shader，适合定位渲染错误、资源绑定错误与状态配置问题。framebuffer 是一帧渲染使用的颜色、深度等图像集合，pipeline state 是该 draw 生效的管线配置。通用 RenderDoc capture 不一定包含目标移动 GPU 的全部微架构 counter，API replay 的耗时也不能直接视为正常运行时帧耗时。

Android 捕获通常要求 debuggable 应用、ADB 连接和受支持的 Vulkan driver。具体 API 与 extension（图形 API 扩展）能力要以所用 RenderDoc 版本为准。Arm Performance Studio 提供 RenderDoc for Arm GPUs，补充部分 Arm/Android 特性、设备兼容处理、Vulkan ray tracing 与 ray query 调试；这些能力不代表 upstream RenderDoc（主项目版本）的每个发行版都具备相同支持。

如果要判断性能开销来自哪里，可先用 AGI 或厂商 profiler 找到慢 render pass，再用 RenderDoc 检查该 pass 的 attachment、pipeline、descriptor（资源绑定描述）、texture 和 shader。若要调查画面错误，可以从错误帧逐个 event 检查 framebuffer 变化。

## Sokatoa：Vulkan 多帧视角

Sokatoa 由 Samsung Austin Research Center 发起，并与 Google、LunarG 协作。项目面向 Android Vulkan 应用，提供 system 与 frame 两种视角的多帧捕获、Vulkan API/pipeline/shader 分析和设备端 replay（在设备上重放已捕获工作）。

项目当前文档给出的边界是：

- Android 13 或更高；
- 注入 GFXR（GFXReconstruct 捕获与回放层）和 Sokatoa Vulkan layer 时，需要 debuggable APK 或 rooted device（已取得 root 超级用户权限的设备）；
- performance view 支持 Xclipse、Mali、Adreno 和 PowerVR；
- 当前可免费下载，README 表示计划在 2026 年底开放源码。

多帧捕获适合调查间歇性 pipeline 创建、状态变化、资源生命周期和异常帧前后的差异。capture replay 仍受 API feature、extension、格式、driver 和 GPU 能力约束；记录了 Vulkan API，并不代表捕获结果能在任意 GPU 上等价回放。

## 厂商工具的边界

| GPU | 工具 | 适合的数据 | 使用时的限制 |
|---|---|---|---|
| Arm Mali / Immortalis | Arm Performance Studio：Streamline、Frame Advisor、Mali Offline Compiler、RenderDoc for Arm GPUs | CPU/GPU 联合 timeline、Mali counter、单帧几何与 API、shader 静态分析 | 支持范围按 GPU 世代、driver 和工具版本确认 |
| Qualcomm Adreno | Snapdragon Profiler，配合 APA/AGI | Adreno counter、GPU driver instrumentation（驱动插桩数据）、系统资源、frame snapshot（单帧快照） | 设备与功能覆盖按 Qualcomm 文档确认 |
| Samsung Xclipse | Sokatoa，配合 APA/Perfetto 与 Samsung 扩展 | 多帧 Vulkan、Xclipse performance view、系统时间线 | 扩展与设备支持仍在演进，报告要记录版本 |
| Imagination PowerVR | AGI、Sokatoa 与 Imagination 工具 | PowerVR counter、系统与帧分析 | counter 名称和可用性依设备 producer |

Arm Streamline 能在未 root 的受支持 Android 设备上采集 CPU、GPU、内存、调度和硬件 counter。Frame Advisor 面向问题帧的 API 与几何分析；RenderDoc for Arm GPUs 偏重图形调试；Mali Offline Compiler 不运行 App，而是估算 shader 在不同 Arm GPU 上的指令、寄存器和周期成本。三者用途不同，报告不能只写“Arm profiler”后混用结论。

厂商 counter 应保留原名称、单位、采样方式、GPU 型号、driver 和文档版本。把 Adreno 的 busy、Mali 的 shader core active 与 Xclipse 的相似名称放进一张跨机型排行榜，数值很容易失去可比性。

## `profileable`、`debuggable` 与 root

`<profileable>` 从 API 29 引入，是 `<application>` 的子元素；`android:enabled` 属性在 API 30 加入。设置 `android:shell="true"` 后，本地 shell profiling 工具可以分析 release 构建，同时只能访问平台允许的有限数据。与 debuggable 构建相比，这种方式对运行时序的扰动通常更小。debuggable 允许调试器和图形 layer 注入；root 则表示设备取得系统超级用户权限，三者不是同一种授权。

它不保证 `gpu.counters`、`gpu.renderstages` 或厂商内核事件出现。GPU 数据源由系统 producer、驱动、设备配置和调用权限决定。一个 profileable 包得到空 GPU 轨道时，排查方向应包含 data-source descriptor 与厂商支持。

帧捕获通常需要把 Vulkan layer 加载进目标进程，或替换 graphics backend：

- AGI quickstart 要求 debuggable 应用；
- RenderDoc Android capture 通常要求 debuggable 应用；
- Sokatoa 要求 debuggable APK 或 rooted device；
- 厂商工具各有设备、包类型和权限条件。

debuggable 会改变运行时优化与安全检查，捕获 layer 还会记录命令、资源和内存。应使用 profileable/release 包采集低扰动基线，再用 debuggable 包做短窗口详细诊断；两类结果不能直接比较绝对帧时间。

## 不设固定阈值，改做对照实验

### 怀疑 fragment、overdraw 或带宽

fragment 是光栅化后进入片元着色阶段的候选像素；overdraw 指同一屏幕位置被重复绘制。在同一设备上降低渲染分辨率或停用一个全屏 pass，如果 GPU stage 与外部内存相关 counter 同步下降，再检查 overdraw、blend（颜色混合）、render-target format（渲染目标格式）、attachment load/store、texture sampling（纹理采样）和 SurfaceFlinger client composition。

Android View 的开发者选项 overdraw overlay 适合查找 UI 重复覆盖，游戏和 native renderer 则应使用帧 capture 与厂商 counter。Tile-based GPU 会把画面分块，并在片上 tile memory 中处理部分中间结果；因此“画了 N 次”不能直接换算成 N 倍外部内存带宽。

### 怀疑 shader ALU 或纹理

固定画面、分辨率与 pipeline state，只替换一个 shader 变体或关闭一个纹理采样分支。结合 shader duration、instruction、occupancy、texture/cache 与 external memory counter 判断变化。某个 counter 很高只能描述该架构上的活动状态，仍需通过 A/B 对照实验，也就是每次只改变一个变量，确认改动与结果之间的关系。

### 怀疑 draw call 或 driver CPU 开销

检查 render/RHI 线程调用栈、`vkQueueSubmit()` 前的命令录制、pipeline/descriptor churn 和 driver ioctl。RHI（Render Hardware Interface）是引擎对图形 API 的抽象层；churn 指 pipeline 或 descriptor 被频繁创建、切换；ioctl 是用户态通过系统调用向内核驱动发送控制请求。合批后若 CPU submit 提前而 GPU stage 基本不变，收益来自 CPU 或驱动开销下降；若 GPU stage 也缩短，才能说明 GPU 工作组织同时改善。

### 怀疑 queue-stuffing

持续尽快 present 可能塞满 BufferQueue，这就是 queue stuffing。随后 render thread 会在 acquire、dequeue、swap 或 present 路径等待。此时 CPU 与 GPU 时间线都可能出现空白，但输入仍排在较早的 in-flight frame（已提交、尚未显示的帧）中。应检查队列深度、release fence、present 间隔、输入采样点和 frame pacing，不能把等待函数本身解释为 shader 变慢。

### 怀疑热限制

把 thermal status（温控状态）、thermal headroom（距离进一步触发温控限制的余量）、CPU/GPU frequency、帧时间、画质和持续运行时间放进同一份记录。固定性能模式适合隔离 DVFS 变量，却不能代表用户环境。优化验证应从相近初始温度开始重复多轮，并比较温度和频率趋于稳定后的阶段。

## 捕获扰动与报告要求

system trace、counter sampling、frame capture 和 replay 都会扰动被测程序，程度取决于采样频率、数据量、driver 与工具。报告里至少记录：

- 工具与版本、TraceConfig、设备 build、GPU 和 driver；
- 应用包类型、Graphics API、ANGLE/native driver 选择；
- 分辨率、刷新率、目标帧率、画质与场景；
- 温度、供电、持续运行时间和固定性能模式；
- 捕获是否注入 layer、替换 backend 或启用 validation；
- 原始 Trace/capture，以及每次 A/B 对照只改变的变量。

帧 capture 用来检查命令、状态与资源，不应作为产品帧率基准。性能数字应来自未注入 capture layer 的低扰动运行，再用帧 capture 解释慢帧结构。

## 常见误判

### RenderThread 很短，所以 GPU 很慢

RenderThread 可能只负责异步提交。只有 GPU stage、completion fence、FrameTimeline 和单变量实验共同指向 GPU，才能判断这一帧受 GPU 工作限制。

### GPU utilization 高，所以 shader 复杂

GPU busy 可能来自 fragment、纹理、带宽、compute、copy、driver queue 或 SurfaceFlinger client composition。需要结合不同 stage 和对应 counter 继续区分。

### `gpu.counters` 是 Android 17 统一指标

Android 17 统一了 Perfetto 的传输结构和 Android OEM descriptor 要求，没有统一每家 GPU 的微架构指标。

### Android 17 默认把所有 GLES 转成 ANGLE

Android 17 提供 manifest 请求信号，ANGLE 选择仍受设备与系统策略控制。AGI 的 OpenGL on ANGLE capture 只能说明本次捕获使用了 ANGLE。

### `profileable` 足以使用所有帧工具

AGI、RenderDoc、Sokatoa 等帧捕获会注入 graphics layer，通常要求 debuggable 或 root。`profileable` 主要服务低扰动 profiling。

### GPU 时间短，所以显示没有问题

GPU 工作完成后还有 acquire fence、SurfaceFlinger latch、composition、HWC 与 present。判断用户何时真正看到画面，必须追踪到显示端。

## 执行清单

1. 记录设备、GPU/driver、build、分辨率、刷新率、画质、温度与包类型。
2. 确认主体 Surface 和 producer 线程，不把宿主窗口当作独立 Surface 的主体。
3. 用 APA/Perfetto 找到目标帧和 CPU submit、GPU completion、queue、latch、composition、present。
4. 查询设备 data-source descriptor，确认 GPU producer 名字、counter ID 和单位。
5. 用分辨率、pass、shader、HWC/client composition 或 frame pacing 做单变量实验。
6. 依据问题选择 AGI、RenderDoc、Sokatoa 或厂商 profiler。
7. 分开保存低扰动性能基线与注入 layer 后的调试 capture。
8. 优化后在相近热状态重复多轮，保留原始数据和工具版本。
9. 报告按“证据、推断、对照结果”书写，设备特有结论不要写成 Android 通用规则。

## 参考资料

- [Android Performance Analyzer](https://developer.android.com/android-performance-analyzer)
- [Introducing Android Performance Analyzer](https://developer.android.com/blog/posts/introducing-android-performance-analyzer-the-next-evolution-in-profiling-for-android)
- [Android GPU Inspector](https://developer.android.com/agi)
- [AGI quickstart](https://developer.android.com/agi/start)
- [AGI Frame profiling overview](https://developer.android.com/agi/frame-trace/frame-profiler)
- [Perfetto GPU data sources](https://perfetto.dev/docs/data-sources/gpu)
- [Perfetto FrameTimeline](https://perfetto.dev/docs/data-sources/frametimeline)
- [Android 17 `gpu_counter_config.proto`](https://android.googlesource.com/platform/external/perfetto/+/refs/tags/android-17.0.0_r1/protos/perfetto/config/gpu/gpu_counter_config.proto)
- [Android 17 `gpu_renderstages_config.proto`](https://android.googlesource.com/platform/external/perfetto/+/refs/tags/android-17.0.0_r1/protos/perfetto/config/gpu/gpu_renderstages_config.proto)
- [Android 17 `gpu_counter_event.proto`](https://android.googlesource.com/platform/external/perfetto/+/refs/tags/android-17.0.0_r1/protos/perfetto/trace/gpu/gpu_counter_event.proto)
- [Android 17 `FrameTracer`](https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/services/surfaceflinger/FrameTracer/)
- [Android Vulkan and ANGLE overview](https://developer.android.com/games/develop/vulkan/overview)
- [`<profileable>` manifest element](https://developer.android.com/guide/topics/manifest/profileable-element)
- [Sokatoa project and current requirements](https://github.com/sarc-acl/sokatoa)
- [Arm Performance Studio](https://developer.arm.com/Tools%20and%20Software/Arm%20Performance%20Studio)
- [Arm Streamline](https://developer.arm.com/tools-and-software/streamline-performance-analyzer)
- [RenderDoc for Arm GPUs](https://developer.arm.com/tools-and-software/renderdoc-for-arm-gpus)
- [Snapdragon Profiler](https://developer.qualcomm.com/software/snapdragon-profiler)
- [Android 17 common kernel devfreq](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/drivers/devfreq/)
- [Android 17 common kernel dma-fence](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/drivers/dma-buf/dma-fence.c)

## 相关章节

- [2.10 GPU 渲染深入](../../part1-fundamentals/ch02-rendering/10-gpu-rendering.md)：GPU pipeline、tile、带宽与 shader
- [2.14 图形 API 演进与选择](../../part1-fundamentals/ch02-rendering/14-graphics-api-evolution.md)：GLES、Vulkan 与 ANGLE 的版本边界
- [13.3 Perfetto View 解读](../ch13-perfetto/03-perfetto-view.md)：Trace UI 与时间线操作
- [14.1 Android Studio Profiler](01-as-profiler.md)：profileable/debuggable 与低扰动 profiling
- [18.1 渲染管线总览](../../part2-performance/ch18-rendering-pipelines/01-pipeline-overview.md)：Surface、BufferQueue、SurfaceFlinger、HWC 与 display present
- [18.8 OpenGL ES](../../part2-performance/ch18-rendering-pipelines/08-opengl-es.md)：EGL/GLES 提交与 native/ANGLE backend
- [18.9 Vulkan Native](../../part2-performance/ch18-rendering-pipelines/09-vulkan-native.md)：swapchain、submit、present 与 frame pacing
