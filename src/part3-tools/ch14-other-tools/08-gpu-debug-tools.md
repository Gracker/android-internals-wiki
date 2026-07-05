---
title: "GPU 图形调试与分析工具"
chapter: "14.8"
section: "14.8"
status: "finalized"
pipeline_stage: "ready-to-publish"
applicable_versions: "Android 8.0 (API 26) - Android 17 (API 37) (AGI 要求 Android 11+, APA 要求 Android 12+, Sokatoa 要求 Android 13+)"
tags: ["gpu", "agi", "renderdoc", "sokatoa", "gapid", "gpu-counter", "profiling", "vulkan", "opengl-es"]
confidence: "medium"
last_verified: "2026-06-12"
last_verified_against: "developer.android.com/agi, developer.android.com/android-performance-analyzer, developer.android.com/blog/posts/introducing-android-performance-analyzer-the-next-evolution-in-profiling-for-android, perfetto.dev/docs/data-sources/gpu, github.com/sarc-acl/sokatoa, AOSP android-17.0.0_r1 external/perfetto/protos/perfetto/config/gpu/gpu_counter_config.proto"
drafted_date: "2026-04-05"
drafted_by: "openclaw-task2a"
reviewed_date: "2026-06-12"
reviewed_by: "openclaw-task6"
path: "Cubox/基于gpu counters数据的性能优化-2025-02-27.md"
related_chapters: ["2.10", "2.14", "13.3", "14.1"]
created_by: "task2a-knowledge-gap"
created_date: "2026-04-05"
gap_source: "AOSP结构+官方文档+研究素材"
last_task2b_at: "2026-06-12T16:50:00+08:00"
task2b_result: "fixed-lite"
task6_result: "pass-light-edit"
task6_state: "reviewed"
task9_state: "pending"
task2b_state: "fixed"
task9_result: "pass-tech-review"
task9_reviewed_date: "2026-06-12"
task9_reviewed_by: "openclaw-task9"
last_task9_at: "2026-06-12T18:20:00+08:00"
last_task6_audit: "2026-06-29"
last_task6_audit_log: "logs/review/2026-06-29-15-audit.md"
last_task9_audit: "2026-06-25T16:24:00+0800"
queue_entry: "task9-audit-20260612-14.8-apa-system-profiler-boundary"
last_task6_at: "2026-07-05T18:17:09+08:00"
task6_reviewed_at: "2026-07-05T18:17:09+08:00"
task6_reviewed_by: "openclaw-task6"
finalized_date: "2026-07-05"
finalized_by: "openclaw-task6-auto-promote"
deepseek_cn_review_state: "done"
last_deepseek_cn_review_at: "2026-06-12"
last_task9_audit_log: "logs/deep-review/2026-06-12-16-audit.md"
task9_review_summary: "pass-tech-review; queue 无 pending; 自动晋升 finalized。"
last_task2b_lite_at: "2026-07-05"
---

# 14.8 GPU 图形调试与分析工具

<!-- outline-start -->
## 本节要点大纲

### 锚点(必须覆盖)

- 🔹 **GPU 工具分层与选型**:[已验证:developer.android.com/agi,perfetto.dev/docs/data-sources/gpu,renderdoc.org]
  先区分系统级追踪、帧级分析和厂商专用工具,再按"先确认 GPU 是否是瓶颈,再定位具体环节"的路径选工具。

- 🔹 **AGI 的两种模式与适用场景**:[已验证:developer.android.com/agi]
  System Profiler 用来观察 GPU 利用率、频率、计数器和进程级 GPU 时间;Frame Profiler 用来定位单帧中的慢 Draw Call、Shader 和资源热点。

- 🔹 **Perfetto 中的 GPU 观察点**:[已验证:perfetto.dev/docs/data-sources/gpu]
  `gpu.counters` 用来观察频率、利用率、带宽,`gpu.renderstages` 用来对齐 CPU 提交和 GPU 执行时间,适合作为 GPU 分析入口。

- 🔹 **RenderDoc 与 Sokatoa 的角色差异**:[已验证:renderdoc.org,github.com/sarc-acl/sokatoa]
  RenderDoc 适合单帧图形调试和状态检查,Sokatoa 适合多帧对比和间歇性 GPU 卡顿定位,两者与 AGI 互补。

- 🔹 **GPU 瓶颈判断指标**:[来源:Cubox/移动平台的GPU性能分析-2024-12-07.md,Cubox/基于gpu counters数据的性能优化-2025-02-27.md]
  重点看 GPU 时间、Draw Call 数量、Overdraw、显存带宽、Shader 复杂度与 ALU 利用率,并结合具体场景判断是 GPU bound、CPU bound 还是 buffer/backpressure 问题。

### 扩展(可选深入)

- 🔸 **厂商专用工具的适用边界**:Mali / Adreno / Xclipse 各自能看到哪些专有计数器
- 🔸 **Release 包与调试包的工具权限差异**:`profileable`、`debuggable` 与帧捕获能力的关系
<!-- outline-end -->

## 为什么要用专门的 GPU 分析工具

在 Perfetto 中看到一帧的渲染时间超标,我们通常先看 CPU 侧:主线程是不是被什么阻塞了,RenderThread 的 draw 操作是不是太重。如果 CPU 侧一切正常,主线程闲着,RenderThread 也没有长时间阻塞,但帧时间还是超了 16.6 ms,这时候瓶颈大概率在 GPU。

Perfetto 能告诉我们"GPU 在忙",但它看不到 GPU 内部发生了什么。GPU 是不是在等显存带宽?Shader 太复杂了导致 ALU 打满?还是 Draw Call 数量太多,驱动开销成了瓶颈?这些问题的答案,CPU profiling 工具给不了。


这就是 GPU 专用分析工具存在的意义。它们能深入 GPU 内部,告诉我们每一帧的 GPU 时间花在了哪里:哪个 Draw Call 最耗时,哪个 Shader 吃掉了最多的 ALU 周期,显存带宽是不是被 Overdraw 吃光了。

GPU 分析工具和 CPU 分析工具不是替代关系,是互补关系。先用 Perfetto 定位"问题在 GPU",再用 GPU 工具找到"GPU 的哪个环节慢"。两者配合,才能完成一次完整的渲染性能分析。

不同场景对 GPU 分析的需求也不同:游戏开发者需要逐 Draw Call 的帧分析,UI 渲染优化关注带宽利用率和 Overdraw,视频解码关注 GPU 编解码单元的利用率。本章介绍的工具覆盖了这些场景。

## GPU 分析工具全景

Android 平台上的 GPU 分析工具大致分三层,对应的定位也不同:


**系统级追踪工具**:不分析单帧的 Draw Call 细节,而是看 GPU 在时间轴上的整体行为。适合回答"GPU 是不是瓶颈""GPU 利用率如何""显存带宽够不够"这类问题。

- **Perfetto GPU counter track**:Perfetto 自带的 GPU 计数器,无需额外安装,抓 Trace 时顺便就能采集。精度有限但最方便。
- **APA System Profiler**:Android Performance Analyzer 的系统级模式,2026 年 5 月发布,是当前官方推荐的 system profiling 工具。覆盖 CPU/GPU/Memory/power,基于 Perfetto,Android 12+ 提供最佳体验。后续 frame profiling/debugging 由 GFXReconstruct 支撑。
- **AGI System Profiler**:Android GPU Inspector 的系统级模式,数据比 Perfetto 更详细,支持 Adreno/Mali/PowerVR 三大移动 GPU。APA 发版后被官方建议向 APA 迁移,但仍有设备兼容和功能覆盖价值。
- **PerfDog**:腾讯出品的跨平台性能监控工具,不深入 GPU 内部,但可以实时显示 GPU 利用率、帧率、温度等宏观指标。

**帧级分析工具**:捕获一帧的所有 GPU 命令,逐 Draw Call 分析。适合"已经确定 GPU 是瓶颈,需要知道具体哪个渲染 Pass 或 Shader 拖慢了这一帧"。

- **AGI Frame Profiler**:Google 官方工具,支持 Vulkan 和 OpenGL ES 的帧捕获和分析。
- **RenderDoc**:开源图形调试器,功能最全面的单帧分析工具。Arm、Samsung、Meta 都维护了自己的 fork。
- **Sokatoa**:Samsung 2026 年发布的多帧 GPU profiler,基于 GFXReconstruct,计划 2026 年底开源,是唯一支持多帧分析的工具。

**厂商专用工具**:针对特定 GPU 提供更深度的分析。

- **ARM Streamline Performance Analyzer**:Mali GPU 的官方分析工具,集成 CPU/GPU/内存的联合分析。
- **Snapdragon Profiler**:高通 Adreno GPU 的专用分析工具,提供 Adreno 微架构级别的深度性能计数器和实时性能监控,与 AGI 互补。

### 工具选择决策

选哪个工具?取决于我们要回答什么问题:

1. **GPU 是不是瓶颈?** → Perfetto GPU counter、AGI System Profiler 或 APA System Profiler
2. **GPU 哪个环节慢?** → AGI Frame Profiler 或 RenderDoc
3. **偶发性 GPU 卡顿(间歇性掉帧)?** → Sokatoa 多帧分析
4. **Mali GPU 深度分析?** → ARM Streamline
5. **游戏实时性能监控?** → PerfDog



## Android GPU Inspector (AGI)

AGI 是 Google 官方的 Android GPU 分析工具,前身是 GAPID(Graphics API Debugger)。2020 年更名为 AGI 后,重心从"图形 API 调试"转向"GPU 性能分析"。AGI 同时支持 Vulkan 和 OpenGL ES 应用。对 GLES 应用,AGI 通过自定义的 ANGLE 构建将 GLES 命令翻译为 Vulkan 再做追踪。

### AGI 的两种模式

AGI 提供两种分析模式,覆盖不同的分析需求:

**System Profiler** 是系统级分析模式。在一段时间内追踪 GPU 的整体行为,包括 GPU 利用率、GPU 频率、显存使用量和各进程的 GPU 时间。它不深入单个 Draw Call,但能快速判断 GPU 是不是瓶颈,以及 GPU 时间花在了哪个进程。在 Perfetto 中看到的 GPU 信息只是 System Profiler 的子集,AGI 提供的 GPU 硬件计数器更丰富。

**Frame Profiler** 帧级分析。捕获一个应用的单帧,记录所有 GPU 命令(Vulkan 或 GLES),然后逐 Draw Call 分析 GPU 时间。它会显示每个 Draw Call 占了多少 GPU 时间、绑定了什么 Shader、使用了什么纹理、产生了多少 Overdraw。

### System Profiler 的使用

System Profiler 的使用比较直观:

1. 用 USB 连接设备,确保 adb 可用
2. 打开 AGI,选择 System Profiler 模式
3. 选择要追踪的应用(或选择全系统追踪)
4. 配置追踪时长和 GPU 计数器
5. 开始追踪

追踪完成后,AGI 展示一个时间轴视图,上面有 GPU 利用率曲线、GPU 频率曲线、各进程的 GPU 时间切片。如果某个时间段 GPU 利用率接近 100% 但帧率还是上不去,说明瓶颈在 GPU 侧。

AGI 支持的 GPU 计数器因 GPU 厂商而异:

- **Qualcomm Adreno**:ALU 利用率、纹理读取带宽、L2 cache 命中率
- **ARM Mali**:Fragment 线程活跃数、Vertex 线程活跃数、内存带宽
- **PowerVR**:Tiler 利用率、Renderer 利用率、Shader 处理量


### Frame Profiler 的使用

Frame Profiler 更强大也更复杂。

#### 使用 Frame Profiler 的前置条件

在开始帧捕获之前,需要确认以下条件:

1. **应用必须是 debuggable 的**。Frame Profiler 需要注入 Vulkan/GLES 拦截层来捕获 GPU 命令,这要求 `android:debuggable="true"`(或在 AndroidManifest 中声明)。Release 包无法使用 Frame Profiler,需要临时切换到 debuggable 构建。

2. **目标 API 最低要求 Android 11 (API 30)**。AGI 的完整功能(包括 System Profiler 和 Frame Profiler)从 Android 11 开始支持。Android 10 及以下只能使用部分功能。

3. **Vulkan 应用无需额外配置**。AGI 通过 Vulkan Layer 拦截 API 调用,Vulkan 应用开箱即用。

4. **GLES 应用会通过 ANGLE 翻译为 Vulkan**。AGI 使用自定义 ANGLE 构建处理 GLES 命令。在 Android 17+ 上(ANGLE denylist 生效后),这条路径更接近系统默认值;更早版本要先确认应用是不是已经被切到 ANGLE。开发阶段常见的固定方法是先把目标包锁到 ANGLE:

```bash
adb shell settings put global angle_gl_driver_selection_pkgs <pkg>
adb shell settings put global angle_gl_driver_selection_values angle
```

部分新系统镜像还会把同样的动作封成 `adb shell cmd gpu set-graphics-driver --package <pkg> --driver angle`。命令缺失时,改从 Settings / Graphics Driver Preferences 进入。

5. **Vulkan 应用需要启用 AGI 的 Vulkan Layer 完成帧捕获**。AGI 官方 quickstart 要求 Vulkan 应用启用 Vulkan validation layers;若应用未自行启用,需要通过 `adb shell settings put global enable_gpu_debug_layers 1` 和 `adb shell settings put global gpu_debug_layers <agi_layer_name>` 注入 AGI APK 中的 layer。AGI Frame Profiler 的定位是 draw call / shader / render target 分析,不用于测量真实帧率。如果讨论应用自带调试 validation layer 的性能扰动,需要另起一句说明,但不要覆盖 AGI 必需的 layer 配置。

使用步骤:

1. 在 AGI 中选择 Frame Profiler 模式
2. 选择目标应用
3. AGI 会自动捕获一帧的 GPU 命令流
4. 捕获完成后,在 AGI 中打开分析

Frame Profiler 的核心视图:

**命令列表**:按时间顺序列出所有 GPU 命令(vkCmdDraw、vkCmdDrawIndexed 等),每个命令旁边显示 GPU 执行时间。通过排序 GPU 时间列,可以快速找到最耗时的 Draw Call。

**管线状态(Pipeline State)**:选中一个 Draw Call 后,会展开完整的渲染管线状态,包括 Vertex Shader、Fragment Shader、Blend State、Rasterizer State 等。如果某个 Draw Call 特别慢,先看它的 Shader 复杂度和纹理分辨率,通常最容易找到突破口。

**资源查看器**:查看每个 Draw Call 的输入纹理和输出 render target。如果一个 4096×4096 的纹理被一个只画 100×100 像素的 Draw Call 采样,这就是一个明显的优化点,缩小纹理通常就能减少带宽消耗。

### AGI 的近期演进与 APA 的出现


AGI 继续围绕 System Profiler 和 Frame Profiler 两条线完善功能。System Profiler 负责长时间 trace、GPU counter 和进程级 GPU 时间;Frame Profiler 负责单帧命令、shader 和 render target 的深入查看。

2026 年 5 月,Google 发布了 **Android Performance Analyzer (APA)**,这是一个基于 Perfetto 的新一代 system profiling 工具,覆盖 CPU、GPU、Memory 和 power 分析。APA System Profiler 已经 open beta,官方在 AGI 文档中建议开发者向 APA 迁移。

当前工具分工如下:

- **system profiling**(GPU counter、进程级 GPU 时间、长时间 trace):首选 **APA System Profiler**;AGI System Profiler 保留为可用兼容路径,Perfetto GPU counter 作为快速入口
- **frame profiling**(单帧 GPU 命令、Draw Call、Shader / Render Pass 定位):用 **AGI Frame Profiler** 或 RenderDoc
- **frame profiling / debugging 后续方向**:APA 官方博客提到 upcoming frame profiling/debugging 将由 **GFXReconstruct** 支撑,未列入当前公开 beta 范围
- **多帧 GPU 分析**:优先看 **Sokatoa**,基于 GFXReconstruct 且已公开实现路径

### AGI 对 GLES 应用的分析路径


Android 15 开始,ANGLE 已经有了更明确的系统开关和每应用切换入口。到 Android 16 的新设备,ANGLE 覆盖范围继续扩大;Android 17 的新设备再转到 denylist 策略,默认大多数应用经由 ANGLE,兼容性例外回退到原生 GLES 驱动。AGI 的帧分析沿着这条迁移线工作:它会用自定义 ANGLE 构建把 GLES 命令翻译为 Vulkan 再做追踪。

排查时先确认设备当前走的是哪条 driver 路径,再决定怎么解读 Draw Call 和 Shader 时间。开发阶段常用的固定方法有两类:用前面的 `settings put global angle_gl_driver_selection_*`,或在带 gpu shell 封装的系统镜像上用 `adb shell cmd gpu set-graphics-driver --package <pkg> --driver angle`。命令缺失时,改从 Settings / Graphics Driver Preferences 进入。

## Perfetto 中的 GPU 分析能力

Perfetto 本身也提供了一些 GPU 分析能力,虽然不如 AGI 全面,但胜在不需要额外工具。抓 Perfetto trace 时多加几个配置,就能同时采集 GPU 数据。

### GPU Counter Track 的启用

在 Perfetto 的 trace config 中,需要启用 `gpu.counters` 数据源来采集 GPU 计数器:

```textproto
data_sources {
  config {
    name: "gpu.counters"
    gpu_counter_config {
      counter_ids: [1, 2, 3, ...]   # 先用设备暴露的 counter 列表确认具体 ID
      counter_period_ns: 1000000    # 1 ms 采样间隔
    }
  }
}
```


`gpu_counter_config` 的字段定义在 AOSP `android-17.0.0_r1 external/perfetto/protos/perfetto/config/gpu/gpu_counter_config.proto`。`counter_ids` 对应设备 producer 返回的 `GpuCounterSpec`。自己手写 Trace Config 时,先用 Perfetto UI 的 Trace Config 页面把设备支持的 counter 列出来,再回填这些 ID;不同 GPU 的编号和含义都不通用。

### 关键 GPU 指标

在 Perfetto 的 GPU counter track 中,以下几个指标最有分析价值:

**GPU Frequency(`gpu.frequency`)**:GPU 当前运行频率。GPU 频率会根据负载动态调节(DVFS)。如果 GPU 频率在高负载时没有升到最高档,可能是 Thermal Throttling 在限频。这种情况要从散热和功耗角度处理,不是单纯优化 GPU 代码。

**GPU Utilization**:GPU 计算单元的利用率。100% 意味着 GPU 在满负荷运行,是瓶颈的直接证据。但低利用率不一定说明 GPU 不是瓶颈,GPU 也可能在等内存数据,也就是带宽瓶颈,ALU 空闲但内存控制器已经打满。

**GPU Memory Bandwidth**:显存读写带宽。Overdraw 严重的场景带宽会打满,GPU 虽然不是在"计算"而是在等数据。

### GPU Activity Slice

Perfetto 中还有 `gpu.renderstages` 数据源,可以显示 Vulkan 或 GLES 提交在 GPU 上的执行时间。在 Perfetto UI 中,这些数据显示为 GPU activity slice,一条水平条就表示 GPU 正在执行某个渲染任务。

通过对比 CPU 侧的 RenderThread 提交时间和 GPU 侧的执行时间,我们可以判断渲染管线是在等 GPU(GPU bound)还是在等 CPU(CPU bound):

- CPU 提交很快完成,GPU 执行时间长 → GPU bound
- CPU 提交耗时长(比如在等 dequeueBuffer),GPU 执行很快 → CPU/buffer bound


### Perfetto GPU 分析的局限

Perfetto 的 GPU 分析能力有两个主要局限:

1. **计数器粒度太粗**。只能看到整体利用率、频率、带宽这些宏观指标,无法定位到具体的 Draw Call 或 Shader。
2. **不同 GPU 厂商的计数器 ID 不同**。Adreno、Mali、PowerVR 各有自己的计数器定义,跨设备对比时需要特别注意。

当 Perfetto 的 GPU 数据显示 GPU 是瓶颈但无法定位具体原因时,就需要切换到 AGI 或 RenderDoc 进行帧级分析。

## RenderDoc 在 Android 上的使用

RenderDoc 是开源图形调试器里最全面的单帧分析工具之一。它最初面向 PC 图形开发,但通过远程调试模式也支持 Android 设备。对 Android 开发者来说,它提供了很深的单帧分析能力。

### Android 远程调试配置

在 Android 上使用 RenderDoc 需要:

1. 在 PC 上安装 RenderDoc(1.x 版本)
2. USB 连接 Android 设备,启用 ADB 调试
3. 目标应用需要是 debuggable 的(或者使用 `android:debuggable="true"`)
4. 在 RenderDoc 中配置 Android 远程连接

Arm 维护了一个专门的 fork,"RenderDoc for Arm GPUs",增强了对 Mali GPU 的支持。Samsung 也向 RenderDoc 主线贡献了不少 Android 相关代码。

### 核心功能

RenderDoc 的核心价值在于对单帧的全方位检查:

**Frame Capture**:捕获一帧的所有 GPU 命令。捕获后可以逐步回放每个 Draw Call,观察渲染管线的中间状态。

**Texture Viewer**:查看每个 Draw Call 的输入纹理和输出 render target。这在排查渲染错误时特别有用。如果最终画面颜色不对,可以逐 Draw Call 检查每一步的输出,找到颜色开始出错的那一步。

**Pipeline State**:查看完整的渲染管线状态。Vertex Shader、Fragment Shader、Blend Mode、Depth/Stencil State,所有状态一览无余。很多渲染 Bug 的根因就是某个 State 被错误设置(比如忘记关闭 Depth Write)。

**Shader Debugger**:单步调试 Shader 代码。可以在 Shader 的任意一行设断点,查看变量值,甚至编辑 Shader 代码后在设备上即时生效,不需要重新编译应用。这个功能在优化 Shader 性能时非常有用。

### RenderDoc 的性能分析价值

RenderDoc 最初是调试工具,不是性能分析工具。但它的一些功能对性能分析有帮助:

1. **Draw Call 时间**:虽然不如 AGI 的硬件级计时精确,但 RenderDoc 可以给出每个 Draw Call 的粗略执行时间
2. **Overdraw 可视化**:RenderDoc 可以用热力图显示屏幕上每个像素被绘制了几次。红色区域(Overdraw > 4 次)通常是性能热点
3. **资源统计**:统计一帧使用的纹理总内存、Buffer 总量、Draw Call 数量等


### 与 AGI 的对比

RenderDoc 和 AGI 的 Frame Profiler 功能有重叠但定位不同:

- **AGI** 更适合性能分析:GPU 计数器更丰富,对移动 GPU 的优化更到位
- **RenderDoc** 更适合图形调试:Shader 调试、State 检查、资源查看功能更成熟
- 两者不是竞争关系:AGI 侧重移动 GPU 性能,RenderDoc 侧重通用图形状态调试,实际工作中结合使用

### Arm 和 Samsung 的 Fork

RenderDoc 有几个重要的厂商 fork:

- **RenderDoc for Arm GPUs**(Arm Performance Studio 的一部分):增强对 Mali GPU 的支持,包括 Vulkan Ray Tracing 调试、Ray Query Shader 调试、自动配置 Vulkan Layer 等
- **Samsung 贡献**:Samsung 向主线贡献了大量 Android Vulkan/GLES 支持代码
- **Meta Fork**:针对 Quest XR 设备的 fork,支持 Snapdragon 835/XR2/XR2+ 的底层 GPU 数据


## Sokatoa:多帧 GPU 分析的新范式

2026 年 3 月,Samsung 发布了 Sokatoa,这是一个面向 Android 的多帧 GPU 性能分析器,基于 LunarG GFXReconstruct 引擎构建,计划 2026 年底开源。它的核心创新是多帧分析能力,和 AGI / RenderDoc 的单帧分析正好互补。


### 为什么需要多帧分析

AGI 和 RenderDoc 都是捕获一帧来分析。这在问题稳定复现时够用,但有一种场景单帧分析很难搞:**间歇性 GPU 卡顿**。每隔几十帧突然掉一帧,但大部分帧的 GPU 时间正常。

这种间歇性卡顿的常见原因:

- **Shader 编译尖刺**:运行时遇到新的 Shader 变体,驱动需要即时编译,这一帧的 GPU 时间就暴涨
- **GPU Cache Thrash**:某些帧的工作集超出 GPU Cache 容量,导致频繁的显存访问
- **渲染状态变化**:每隔一段时间切换到一个使用不同渲染路径的场景

单帧捕获很可能正好捕获到正常帧,错过了异常帧。Sokatoa 的多帧分析可以同时查看连续数十帧的 GPU 行为,精确定位哪个帧异常、异常帧有什么共同特征。

### 技术架构

Sokatoa 基于 LunarG 的 GFXReconstruct 引擎构建。GFXReconstruct 的工作方式是拦截应用的 Vulkan API 调用,记录所有命令和参数,然后在离线回放时精确重演。因为记录的是 API 级别的调用,而不是硬件状态,所以回放结果在不同 GPU 架构上仍然确定,在 Adreno 上捕获的 trace 也可以在 Mali 上回放。

Sokatoa 支持 Exynos/Xclipse(基于 AMD RDNA 架构)、Qualcomm Adreno、ARM Mali 和 PowerVR。它原生只支持 Vulkan 应用,对于 GLES 应用,需要先通过 ANGLE 转换为 Vulkan。目标设备要求 Android 13 or later,且需要 debuggable APK 或 rooted device 才能注入 GFXReconstruct/Sokatoa Vulkan layers。

### 开源计划

Sokatoa 当前可免费下载使用,Samsung 计划在 2026 年底开源(GitHub: sarc-acl/sokatoa)。开源后将成为继 RenderDoc 之后第二个主流的开源移动 GPU profiler,也是第一个开源的多帧 GPU profiler。

## GPU 性能分析的核心指标

不管是用哪个工具,GPU 性能分析的核心思路是一样的:通过几个关键指标判断 GPU 瓶颈在哪个环节。

### GPU 时间 vs CPU 时间

这是最基本的判断。在 Perfetto 中,对比 `RenderThread` 的 CPU 执行时间和 GPU activity slice 的 GPU 执行时间:

- **GPU 时间 > CPU 时间**:GPU bound,需要优化 GPU 工作负载(减少 Draw Call、简化 Shader、降低纹理分辨率)
- **CPU 时间 > GPU 时间**:CPU bound,问题在 CPU 侧(主线程阻塞、RenderThread draw 调用太多等)
- **两者都不是瓶颈但帧率还是低**:可能是 BufferQueue 管理问题(§2.13),GPU 和 CPU 都在等 buffer

### Draw Call 数量

Draw Call 是 CPU 向 GPU 提交的一次绘制命令。每个 Draw Call 都有 CPU 侧的开销(驱动需要验证状态、准备命令缓冲区)。当 Draw Call 数量过多时,即使每个 Draw Call 的 GPU 执行时间很短,总时间也会超过帧预算。

在移动设备上,单帧 Draw Call 数量的参考阈值:

- UI 渲染:通常 < 100 个 Draw Call
- 2D 游戏:< 500 个 Draw Call 通常没问题
- 3D 游戏:> 2000 个 Draw Call 需要考虑合批优化

### Overdraw 与带宽

Overdraw 是同一个像素被绘制了多次。每多绘制一次,就多消耗一次 Fragment Shader 的执行时间和相应的显存带宽。在移动 GPU 上,带宽往往比 ALU 更容易先成为瓶颈,因为移动 GPU 的显存和系统内存共享,带宽预算本来就有限。

AGI 和 RenderDoc 都提供 Overdraw 可视化。典型的优化手段:

- **移除不必要的透明背景 View**:Android 的布局经常导致大面积 Overdraw
- **使用 `android:background="@null"` 清除默认背景**:很多 View 的默认背景在 Theme 中设置,子 View 又画了自己的背景
- **Canvas.clipRect()**:手动裁剪绘制区域,避免 GPU 处理被遮挡的像素
- **尽早做 Depth Test**:对于 3D 场景,按从近到远的顺序绘制,让 GPU 通过 Early-Z 剔除被遮挡的片元

### Shader 复杂度与 ALU 利用率

Shader 太复杂会吃满 GPU 的 ALU(算术逻辑单元)。判断 Shader 是不是瓶颈:

- 在 AGI 的 Frame Profiler 中,看 Fragment Shader 的执行时间占比
- GPU 计数器中,ALU 利用率 > 80% 说明 Shader 复杂度是瓶颈
- 解决方向:简化 Shader 逻辑、减少纹理采样次数、使用 LOD(Level of Detail)让远处的物体用更简单的 Shader


## 实战案例

### 案例 1:UI 渲染中的 GPU 带宽瓶颈

**现象**:一个社交 App 的消息列表页,在快速滑动时帧率从 120fps 掉到 80fps。Perfetto 中 CPU 侧没有明显阻塞。

**分析过程**:

1. 打开 Perfetto GPU counter track,发现滑动时 GPU Memory Bandwidth 达到设备峰值
2. 在 AGI Frame Profiler 中捕获一帧,发现 Overdraw 热力图中列表项区域显示深红色(Overdraw > 4x)
3. 检查布局层级:每个列表项有 3 层重叠的半透明背景(卡片背景 + 圆角裁剪 + 图片遮罩)
4. 每个像素被 Fragment Shader 处理了 4 次以上

**优化方案**:

- 移除中间层的半透明背景,改为不透明色
- 使用 `clipRect()` 裁剪不可见区域
- 将圆角裁剪从 Canvas 操作改为 Shape Drawable

**结果**:Overdraw 从 4x 降到 1.5x,GPU 带宽使用量降低 60%,滑动帧率恢复到 115fps。


### 案例 2:Shader 编译导致的间歇性卡顿

**现象**:3D 游戏在运行过程中,每隔 30-60 秒出现一次 2-3 帧的掉帧。Perfetto 中显示掉帧期间 GPU 时间从正常的 8ms 飙升到 40ms。

**分析过程**:

1. 用 Sokatoa 进行多帧捕获,覆盖 60 秒的连续渲染
2. 在多帧视图中发现,异常帧总是伴随着新的 Shader Variant 被使用
3. 检查 Vulkan Pipeline Cache,发现游戏没有在启动时预热所有可能用到的 Pipeline
4. 新 Shader Variant 触发了即时编译,编译期间 GPU 空闲等待

**优化方案**:

- 在加载画面期间,用所有可能用到的 Shader Variant 做一次"预热渲染"
- 启用 Vulkan Pipeline Cache 并在本地持久化

**结果**:间歇性卡顿消失,帧时间方差从 3.2ms 降到 0.8ms。


### 案例 3:Perfetto GPU counter 定位功耗热点

**现象**:一款导航 App 在导航模式下功耗异常高,GPU 占总功耗的 45%。

**分析过程**:

1. Perfetto trace 中发现 GPU 频率持续保持在最高档(800MHz),但 GPU Utilization 只有 30%
2. GPU 频率高 → 功耗高,但利用率低 → GPU 并不是真的在忙,只是频率没有降下来
3. 检查应用的帧率需求:导航地图使用 `setFrameRate()` 设置了 60fps,但大部分帧在 16ms 内完成,GPU 有大量空闲时间
4. DVFS 调度策略在高频场景下倾向于保守(不降频),导致 GPU 频率降不下来

**优化方案**:

- 降低地图渲染的帧率需求(导航场景 30fps 已经足够流畅)
- 在不需要频繁更新的场景使用 Choreographer.postFrameCallback 的节流机制

**结果**:GPU 平均频率从 800MHz 降到 400MHz,GPU 功耗降低约 40%。


## 与其他章节的关系

GPU 分析工具的使用建立在几个前置章节的知识上:

- **§2.10 GPU 渲染深入**:理解 GPU 渲染管线是使用 GPU 分析工具的前提。不知道 Vertex Shader → Rasterizer → Fragment Shader 的流程,就看不懂 AGI Frame Profiler 的输出
- **§2.14 图形 API 演进与选择策略**:Android 17 的 ANGLE denylist 意味着 GLES 应用实际通过 Vulkan 运行,这影响 GPU 分析工具的选择和结果解读
- **§13.3 Perfetto View 解读**:Perfetto GPU counter track 是 GPU 分析的起点,在深入帧级分析之前先用 Perfetto 确认瓶颈
- **§14.1 Android Studio Profiler**:AS Profiler 也有 GPU 分析能力(虽然不如 AGI 专业),适合快速检查

## 常见问题与误区

### 误区 1:"GPU 利用率高 = GPU 是瓶颈"

GPU 利用率高只是 GPU 繁忙的必要条件,不是充分条件。GPU 也可能在执行很多低效操作,比如大量 Overdraw 导致带宽浪费。优化的目标是减少 GPU 的工作量,而不是单纯降低利用率。如果优化后 GPU 利用率没变,但帧时间缩短了,说明去掉了无效工作。

### 误区 2:"AGI 和 RenderDoc 功能一样,随便选一个"

AGI 专为移动 GPU 优化,支持移动端特有的 GPU 计数器和渲染路径(如 Tile-Based Rendering)。RenderDoc 更偏向 PC 图形开发。对于 Android GPU 性能分析,AGI 的数据质量通常更高。但 RenderDoc 的 Shader 调试功能目前更成熟。

### 误区 3:"GPU 分析需要 root 权限"

大部分 GPU 分析工具只需要 adb 权限和 debuggable 应用。AGI 从 Android 11 开始支持非 root 设备。但 Perfetto 的 GPU counter 采集在某些设备上可能需要特定权限或厂商支持。

### 误区 4:"profileable 和 debuggable 对 GPU 工具没有影响"

`<profileable>` 和 `debuggable` 决定的是"哪些工具能在什么包上工作"。`<profileable>` 是 `<application>` 下的子标签(不是属性),Android 10 引入,能让 Perfetto、simpleperf 这类 shell/system profiling 工具采集 release 包的 CPU 和 GPU counter 数据。但 AGI Frame Profiler 和 RenderDoc 的帧捕获入口仍然要求 `android:debuggable="true"`,`profileable` 不够。

### 误区 5:"GPU 分析工具本身不会影响性能"

帧捕获工具(AGI Frame Profiler、RenderDoc)会显著影响被分析帧的渲染性能,因为它们需要拦截并记录所有 GPU 命令。System Profiler 的开销小得多。所以不要用帧捕获工具测量帧率。宏观性能测量用 Perfetto 或 PerfDog,只有在需要深入分析时才做帧捕获。

## 不同 GPU 厂商的专用工具

移动 GPU 市场有三家主要厂商,每家都有自己的专用分析工具:

### ARM Mali:Streamline Performance Analyzer

ARM Streamline 集成在 ARM Development Studio 中,可以同时分析 CPU、GPU、内存子系统。对 Mali GPU,它提供很细的计数器,包括 Shader Core 的各类利用率、Tile Buffer 的命中率和 L2 Cache 的行为。

Streamline 的独特价值在于 CPU-GPU 联合分析。它可以在同一个时间轴上显示 CPU 调度、GPU 执行和内存访问模式,帮助定位 CPU 和 GPU 之间的数据依赖问题。


### Qualcomm Adreno:Snapdragon Profiler

Snapdragon Profiler 是高通的 GPU 分析工具,专为 Adreno GPU 设计。Snapdragon Profiler 仍在活跃维护,它和 AGI 的定位是互补的。AGI 擅长通用的 GPU 性能分析(跨 GPU 厂商),Snapdragon Profiler 擅长 Adreno 微架构级别的深度分析--比如 Adreno 专属的性能计数器、实时 GPU 频率/电压监控、Shader 编译器优化建议。在 Adreno 设备上做 GPU 深度优化时,两个工具配合使用效果最好。

### MediaTek

MediaTek 没有独立的 GPU 分析工具,但 AGI 对 Mali GPU(MediaTek SoC 通常使用 Mali)提供支持。MediaTek 开发者通常使用 AGI + Perfetto 的组合。

### 工具数据对比

| 工具 | 最低版本 | 系统级 | 帧级分析 | Release 包 | GPU 厂商 |
|------|---------|--------|---------|-----------|----------|
| Perfetto GPU | Android 8+ | ✅ | ❌ | ✅ (profileable) | 通用 |
| APA | Android 12+ | ✅ | ⏳ (roadmap) | ✅ (profileable) | 通用 |
| AGI | Android 11+ | ✅ | ✅ | ⚠️ 需 debuggable | Adreno/Mali/PowerVR |
| RenderDoc | Android 8+ | ❌ | ✅ | ❌ 需 debuggable | 通用 |
| Sokatoa | Android 13+ | ❌ | ✅ 多帧 | ❌ 需 debuggable/rooted | Adreno/Mali/Xclipse/PowerVR |
| Snapdragon Profiler | Android 7+ | ✅ | ✅ | ⚠️ 需 debuggable | Adreno 专用 |
| ARM Streamline | Android 8+ | ✅ | ❌ | ✅ (部分功能) | Mali 专用 |
| PerfDog | Android 5+ | ✅ | ❌ | ✅ | 通用 |

按分析场景选型:

| 场景 | 首选工具 | 备选 |
|------|---------|------|
| GPU 是否瓶颈 | APA System Profiler | Perfetto GPU / AGI System Profiler |
| 哪个 Draw Call 慢 | AGI Frame Profiler | RenderDoc |
| Shader 为什么慢 | RenderDoc | AGI Frame Profiler |
| 间歇性 GPU 卡顿 | Sokatoa | Perfetto 长时间采集 |
| Adreno 深度分析 | Snapdragon Profiler + AGI | - |
| Mali 深度分析 | ARM Streamline + AGI | - |


## GPU 分析的注意事项

### GPU Profiling 的性能开销

帧捕获工具的性能开销很大。AGI Frame Profiler 捕获一帧可能需要几秒甚至几十秒(取决于帧的复杂度),捕获期间应用是暂停的。因此要注意:

- 不能用帧捕获来测量真实帧率
- 捕获的帧的 GPU 时间数据可能因为工具注入的拦截代码而不完全准确
- System Profiler 的开销小得多(通常 < 5%),适合长时间采集
- GPU counter 采样频率拉得很高时,System Profiler 也会引入可观测扰动;某些 Mali 驱动上会看到额外的 CPU 中断或 kworker 活动。长时间录制先用默认采样率,只在短窗口提高采样频率

### profileable vs debuggable


- **debuggable**:AGI 帧捕获、RenderDoc 都需要。但 debuggable 应用会有性能损失(JIT 不做某些优化、运行时检查更多)
- **`<profileable>`**:从 Android 10 (API 29) 引入。Perfetto 可以采集(包括 GPU counter),但 AGI 帧捕获不可用。Android 14 增强了 GPU counter 采集能力。性能损失比 debuggable 小得多
- 建议:日常性能测试用 profileable 包 + Perfetto,深入 GPU 分析时临时切换到 debuggable

### GPU 工具在不同 Android 版本上的可用性

- Android 11+:AGI 完整支持
- Android 10+ (API 29):`<profileable android:shell="true" />` 进入 Manifest,支持基本 Perfetto 采集
- Android 14+:profileable 应用的 Perfetto GPU counter 采集能力增强
- Android 17+:ANGLE denylist 可能影响 GLES 应用的帧分析路径

### 不同设备的 GPU 计数器差异

同一个"GPU Utilization"计数器,在 Adreno 和 Mali 上的含义不完全一样。Adreno 的 Utilization 可能只计算 ALU 活跃时间,而 Mali 的 Utilization 可能包含等待内存的时间。跨设备对比 GPU 计数器数据时,需要查阅对应 GPU 厂商的计数器文档。


## 版本演进

GPU 分析工具在 Android 生态中的几次大变化,直接影响我们今天的工具选择和结果解读。

### GAPID → AGI(2020 年)

GAPID(Graphics API Debugger)是 Google 早期的图形调试工具,定位偏向图形 API 的调试(捕获和回放 GLES/Vulkan 调用)。2020 年,Google 将 GAPID 更名为 AGI(Android GPU Inspector),重心从"API 调试"转向"GPU 性能分析"。这次更名也伴随着功能的扩展:System Profiler 模式和硬件级 GPU 计数器支持是 GAPID 时代没有的。

### profileable 的版本增强

- **Android 10 (API 29)**:引入 `<profileable>` 子标签,允许非 debuggable 应用被 Perfetto 采集 CPU 性能数据
- **Android 11 (API 30)**:给 `<profileable>` 补 `android:enabled` 字段,AGI 从此版本开始完整支持
- **Android 14**:增强 profileable 应用的 Perfetto GPU counter 采集能力,不再需要 debuggable 即可获取 GPU 计数器数据
- **实际影响**:Android 14 之前,采集 GPU counter 通常需要 debuggable 应用或 root 权限;Android 14 之后,profileable 应用配合 Perfetto 就能采集 GPU 计数器,降低了 Release 包 GPU 分析的门槛

### ANGLE 对 GLES 帧分析的影响

Android 15 开始,ANGLE 已经从"可选实验路径"走到"系统内可显式切换的兼容层"。Android 16 的新设备继续扩大默认覆盖,Android 17 的新设备转到 denylist 策略,默认大多数 GLES 应用经由 ANGLE。

这对 GPU 帧分析的影响:

- **Android 15**:开发者已经可以在系统设置或 adb 中强制指定应用走 ANGLE,排查时要先确认真实 driver 选择
- **Android 16 新设备**:ANGLE 覆盖范围继续扩大,很多新机型上的 GLES 工作负载已经更接近 GLES-over-Vulkan
- **Android 17 新设备**:默认大多数应用走 ANGLE,只有 denylist 例外回退到原生 GLES
- **旧设备升级场景**:系统版本升上去,不等于所有旧设备都立刻切到同一条 ANGLE 策略,结论仍要和设备实测一致

### APA 发布(2026 年 5 月)

2026 年 5 月 19 日,Google 发布了 Android Performance Analyzer。APA System Profiler 在 open beta 阶段覆盖 CPU/GPU/Memory/power 分析,基于 Perfetto,Android 12+ 设备上体验最佳。官方在 AGI 文档中推荐开发者向 APA 迁移。APA 的 frame profiling/debugging 路线图指向 GFXReconstruct,目前尚未进入公开 beta。

对工具选型的影响:system profiling 从"AGI System Profiler 为主"变成"APA 为首选,AGI 保留为兼容路径"。

### AGI 2025-2026 演进

公开文档已经明确的是 System Profiler / Frame Profiler 两条产品线会继续增强。APA 发版后,AGI System Profiler 的重心可能逐步转向兼容维护,但 Frame Profiler 仍然在单帧分析领域保持唯一官方工具的定位。

## 参考资料

### 官方文档
- AGI 官方文档:https://developer.android.com/agi
- Perfetto GPU 数据源:https://perfetto.dev/docs/data-sources/gpu
- Sokatoa GitHub:https://github.com/sarc-acl/sokatoa
- RenderDoc 官方文档:https://renderdoc.org/docs/

### 厂商工具
- ARM Streamline:https://developer.arm.com/Tools%20and%20Software/Streamline%20Performance%20Analyzer
- Snapdragon Profiler:https://developer.qualcomm.com/software/snapdragon-profiler

### 研究素材
- AGI 2025-2026 路线图(本地素材:intake/research-feeds/2026-04-05-11-agi-2026-roadmap-system-frame-profiler.md)
- Samsung Sokatoa 发布分析(本地素材:intake/research-feeds/2026-04-05-11-samsung-sokatoa-gpu-profiler.md)
- Android 17 ANGLE/Vulkan 强制路线(本地素材:intake/research-feeds/2026-04-05-11-android17-angle-vulkan14-gles-deprecation.md)

### 进阶阅读
- 移动平台 GPU 性能分析(知乎):https://zhuanlan.zhihu.com/p/560738175
- 基于 GPU Counters 数据的性能优化(Cubox 收藏)- 价值:能把"先 Perfetto 定位,再用帧级或厂商工具定位细节"的工具链方法论讲清。

