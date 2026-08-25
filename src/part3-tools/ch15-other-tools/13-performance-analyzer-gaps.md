---
title: Android Performance Analyzer 与 GAPS：性能追踪与目标可达性
chapter: '15.13'
section: '15.13'
status: finalized
applicable_versions: Android 12 (API 31) - Android 17 (API 37)（APA System Profiler 要求受支持的 Android 12+ 设备；平台源码说明以 Android 17 为锚点）
tags:
- 工具使用
- 系统分析
- 性能诊断
- dynamic-analysis
- gui-testing
- static-analysis
- method-reachability
- android-testing
last_verified: '2026-08-14'
last_verified_against: APA 首页更新至 2026-08-12；Quickstart、录制、Trace View 与三类分析指南当前版本；android-17.0.0_r1；android17-6.18-2026-06_r6
confidence: medium
task6_state: reviewed
task9_state: reviewed
pipeline_stage: ready-to-publish
last_deep_review_at: '2026-07-26T20:36:00+08:00'
last_deep_review_run_id: 20260726-203519-deep-review-009e010e
last_rework_at: '2026-07-26T21:35:26+08:00'
last_rework_run_id: 20260726-213526-rework-009e010e
sources:
- type: official
  path: https://developer.android.com/android-performance-analyzer
- type: official
  path: https://developer.android.com/android-performance-analyzer/quickstart
- type: official
  path: https://developer.android.com/android-performance-analyzer/run
- type: official
  path: https://developer.android.com/android-performance-analyzer/view
- type: official
  path: https://developer.android.com/android-performance-analyzer/view/data
- type: official
  path: https://developer.android.com/android-performance-analyzer/analyze/frame-times
- type: official
  path: https://developer.android.com/android-performance-analyzer/analyze/mem-efficiency
- type: official
  path: https://developer.android.com/android-performance-analyzer/analyze/thread-sched
- type: official
  path: https://developer.android.com/blog/posts/introducing-android-performance-analyzer-the-next-evolution-in-profiling-for-android
- type: official
  path: https://perfetto.dev/docs/
- type: official
  path: https://developer.android.com/studio/profile
- type: official
  path: https://developer.android.com/topic/performance/power/battery-historian
- type: obsidian
  path: /Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Writer/rendering_pipelines/S13_game_type.md
- type: internal
  path: src/part3-tools/ch14-perfetto/01-perfetto-intro.md
- type: internal
  path: src/part3-tools/ch15-other-tools/01-as-profiler.md
- type: internal
  path: src/part3-tools/ch15-other-tools/02-simpleperf.md
- type: internal
  path: src/part3-tools/ch15-other-tools/07-dumpsys.md
- type: internal
  path: src/part3-tools/ch15-other-tools/08-battery-historian.md
- type: paper
  path: https://arxiv.org/abs/2511.23213v3
  authors: Samuele Doria, Alexander Pilgun, Jordan Samhi, Jacques Klein, Eleonora Losiouk
  date: '2026-07-17'
- type: artifact
  path: https://anonymous.4open.science/r/GAPS/README.md
  snapshot: README 3c646133；uv.lock dce51b4c
- type: historical-repo
  path: https://github.com/samudoria/GAPS
  availability: 2026-08-14 返回 404；保留该地址用于解释论文 v1 的历史引用
- type: official
  path: https://developer.android.com/reference/android/os/Trace
- type: official
  path: https://perfetto.dev/docs/quickstart/android-tracing
- type: official
  path: https://perfetto.dev/docs/data-sources/frametimeline
related_chapters:
- '7.2'
- '14.1'
- '14.2'
last_consolidated_at: '2026-08-24'
consolidated_from:
- src/part3-tools/ch15-other-tools/17-android-performance-analyzer.md
- src/part3-tools/ch15-other-tools/28-gaps-dynamic-analysis.md
---

# Android Performance Analyzer 与 GAPS：性能追踪与目标可达性

Android Performance Analyzer（APA）是 Google 面向 Android App 与游戏提供的性能分析工具。官方提供独立桌面应用；2026 年 5 月的发布文还说明，其 System Trace viewer 已进入 Android Studio Panda 4 Canary 及后续版本。本文聚焦独立版 System Profiler。

官方在 2026 年 5 月 19 日以 open beta 发布 System Profiler。截至 2026 年 8 月 13 日，8 月 12 日更新的 APA 下载页已不再标注 Beta；旧 AGI 页面仍保留“public beta”字样，不能用这条滞后的交叉链接判断当前发布状态。当前 APA 文档仍以 System Profiler 为主：录制 system trace（系统追踪）、在 Project（组织多份 trace 的项目容器）中管理数据、查看 CPU/GPU/内存/功耗与 SurfaceFlinger（Android 系统合成器）事件、运行 PerfettoSQL，并为 Vulkan 工作负载补充调试数据。Vulkan render pass（渲染阶段及其附件处理范围）名称和截图属于 trace 增强信息，不能当成逐 draw（逐次绘制调用）的单帧 capture/replay（捕获与回放）。

设备侧平台锚点是 Android 17 / API 37 / `android-17.0.0_r1`，内核侧固定到 `android17-6.18-2026-06_r6`。APA 的发布周期独立于 Android 平台；它支持 Android 12 及以上的受支持设备，不能写成“Android 17 新增的 framework API”。

动态分析工具先建立进程、线程、调用和系统事件的观察面，再决定能否到达目标代码或状态。Performance Analyzer 偏向统一性能检查，GAPS 关注动态分析目标的可达路径重建。

## 统一性能检查与系统证据

### 1. APA 在工具链中的位置

APA 的 System Profiler 依赖 Perfetto 采集 system trace。设备侧的 tracing service 协调录制；producer 注册并写入数据；data source 表示可采集的数据类型；trace buffer 暂存生成的 trace packet（追踪数据包）。桌面端 APA 负责配置录制、取回 trace、展示时间轨道和执行查询。AGI 文档仍把 APA 列为 system profiling 的推荐工具；AGI Frame Profiler 则继续负责 Vulkan 单帧命令、pipeline（图形管线）、shader（GPU 程序）、纹理与几何资源分析。

| 层次 | 组件 | 职责 |
|---|---|---|
| Android App / 游戏 | Java、Kotlin、C/C++、Vulkan、应用 trace marker（自定义时间标记） | 产生业务工作和可读标记 |
| Android framework | ART（Android Runtime）、Binder IPC（Android 跨进程通信）、HWUI（UI 硬件加速渲染库）、FrameTimeline（预期/实际帧时间线）、SurfaceFlinger | 产生线程、帧、buffer 与系统服务事件 |
| Linux kernel | ftrace（内核事件追踪）、scheduler（调度器）、frequency（频率）、idle（空闲状态）、IRQ（硬件中断请求） | 记录线程何时被唤醒、运行、抢占或阻塞 |
| Perfetto | tracing service、producer、data source、`TraceConfig`（录制配置）、trace packet | 统一配置、时间轴和二进制 trace |
| APA System Profiler | Project、Record Trace、Trace View、PerfettoSQL | 交互录制、项目化管理和人工分析 |

在 Android 17 源码中，自定义录制配置的协议锚点是 `external/perfetto/protos/perfetto/config/trace_config.proto`，tracing service 位于 `external/perfetto/src/traced/service/`。内核 `android17-6.18-2026-06_r6/include/trace/events/sched.h` 定义 `sched_switch`、`sched_wakeup` 等调度 tracepoint（内核事件记录点）。APA 显示这些数据，不改变它们在设备侧的语义。

这也限定了 APA 的证据能力：时间上相邻的两个事件只能构成相关线索。要写成因果结论，还要核对线程状态、flow（跨时间轨道的事件关联）、fence（GPU 或 buffer 的异步完成信号）、调用栈、源码或可重复实验。

### 2. 安装与设备要求

APA 首页提供 Windows、macOS 和 Linux 安装包。Quickstart 给出的主机要求如下：

- Windows：64 位 Windows 10 或更高版本；
- macOS：macOS 12 或更高版本，并且只支持 Apple Silicon；
- Linux：64 位环境需要相应的 64 位运行库；
- 所有平台都要安装 Android SDK Platform-Tools（包含 `adb` 等设备工具），并把 `ANDROID_HOME` 指向 Android SDK 根目录。

设备侧要求为“受支持的 Android 设备 + Android 12 或更高版本 + USB + 可用 adb debugging（通过 Android Debug Bridge 调试）”。Android 版本达标不保证所有机型都通过支持检查。首次连接新设备时，APA 会执行 device validation（设备与采集能力兼容性检查）；验证期间不要操作设备。通过后，Configure a Recording 的设备项旁会出现绿色标记。

不同设备、GPU 与驱动暴露的数据不同。缺少 GPU counter（周期采样的硬件指标）、GPU queue（GPU 硬件执行队列）或 Vulkan 信息时，应检查设备支持、驱动、App 构建和录制配置，不能从空轨道推断“GPU 没有工作”。

### 3. 被测 App 应该用哪种构建

官方 Quickstart 对 managed-code App（主要运行 Java/Kotlin 托管代码的应用）与 Vulkan App 给出了不同建议。这些是提高测量准确性的建议，不是启动 APA 的硬性条件：

- Java/Kotlin 性能测量建议使用 release 版本或开启编译、打包优化的性能构建，并设置 `debuggable=false`，让 ART 运行在接近发布环境的优化状态；
- Vulkan App 或游戏若要采集 Vulkan-specific data（Vulkan 专属数据），建议设置 `debuggable=true`，以便 APA 注入或启用对应的 Vulkan 调试能力；
- 纯 C/C++ 或 native game loop（原生游戏循环）受 ART debug 状态的影响较小，但编译优化、符号、引擎配置和资源包仍要固定。

一个同时包含大量 Java/Kotlin 代码和 Vulkan 渲染的 App 很难用单次录制兼顾两种目标。建议保留两种实验：

1. 接近发布配置（release-like）、不可调试（non-debuggable）的构建，用来测启动、UI、调度和整体帧表现；
2. 原生代码优化保持一致、但 `debuggable=true` 的 Vulkan 诊断构建，用来采集 API timing（CPU 侧 API 调用耗时）、render pass name 或 screenshot（捕获画面）。

两次 trace 不能直接按绝对时间互换结论。构建类型改变后，应记录 APK、代码提交、编译选项和 manifest 状态。

### 4. 从 Project 到一份可分析的 trace

APA 的基本工作流是：

1. 创建或打开 Project；
2. 点击 Record Trace；
3. 选择 Device 与 launch mode；
4. 配置 start/end trigger 和数据源；
5. 执行固定的用户操作；
6. 手工 Stop，或等待 Duration 到期；
7. APA 拉取 trace 并自动打开 Trace View。

Project 适合保存同一问题的多份 trace。文件放在同一 Project 不代表采集条件一致；每次录制仍要记录设备、build fingerprint（系统构建的唯一标识）、GPU driver、App 版本、刷新率、温度、亮度、电量和测试脚本。

#### 4.1 Launch mode 与 trigger

launch mode 决定 APA 是否负责启动 App，trigger 决定录制何时开始或结束。Configure a Recording 提供两种 launch mode：

- Launch app and record：APA 启动目标 App；
- Record a running app：对已经运行的进程录制，Application 相关选项不可用，start trigger 只能选择 Manual。

启动触发器包括 Manual、On Startup、On Startup with Delay；结束触发器包括 Manual 和 Duration。启动问题应使用 On Startup，并确认录制开始覆盖进程创建和首帧。稳态（启动和预热影响已经消退）滑动或游戏场景，可以先准备数据、账号和页面，再用 Manual 进入目标窗口。

#### 4.2 默认配置与自定义 `TraceConfig`

System Profiler 默认采集一组 CPU/GPU 指标，也允许在界面中勾选需要的数据。官方建议一分钟以上的 trace 减少 data source；一分钟以内可以选择更多数据，但“影响较小”不等于无扰动，仍要用相同配置做对照。

Use custom trace configuration 会把界面当前设置自动展开成 Perfetto `TraceConfig` textproto（Protocol Buffers 的文本格式）。可以在此基础上添加 Android 17 支持的数据源。自定义配置要同时检查：

- data source 在目标设备上是否注册；
- buffer 大小与 fill policy（buffer 满后的覆盖或停止策略）是否适合录制时长；
- ftrace event（内核事件）、atrace category（Android 用户态追踪类别）和 App marker 是否真的产生数据；
- 采样频率是否改变被测负载；
- trace 是否因 buffer 覆盖、flush（把暂存数据写出）或 stop 时机而丢掉目标窗口。

截至 2026 年 8 月 13 日，APA 公开文档没有给出 `/system/etc/perfetto-configs/apa-config.textproto`、`--custom-cpu-freq`、`--custom-gpu` 或 `adb shell apa` 这些入口。本文的 APA 操作步骤以独立桌面 GUI 为准；2026 年 5 月发布文还描述了 Android Studio 集成，但两种界面都不是命令行采集接口。需要脚本化采集时，应使用 Perfetto CLI、Macrobenchmark（Jetpack 的可重复性能测试框架）或相应测试工具。

### 5. Vulkan Layers：能力与扰动

APA 可在录制时注入 Vulkan layers，也就是加载能拦截 Vulkan API 调用并写入额外调试数据的模块。当前文档列出三类选项。

#### 5.1 CPU Timing

CPU Timing 把 Vulkan API 调用耗时显示为调用线程上的 slice（带开始时间和持续时间的事件）。`vkCmdDraw` 一类高频函数会被有意排除，因为逐次追踪会造成明显开销并扭曲结果。该轨道适合找 API 提交侧的长调用，不能代表 GPU 执行时间。

#### 5.2 Render Pass Debug Names

Render Pass Debug Names 目前标为 Experimental。它把代码设置的 Vulkan render pass debug annotation（调试标注）带入 Trace View，便于把 GPU 工作对应到 Shadow、Lighting、PostProcess 等引擎阶段。若名字缺失，应检查 App 是否 debuggable、对象是否设置 debug name、录制选项是否开启，以及驱动是否提供所需数据。

#### 5.3 Screenshots

Screenshots 也处于 Experimental。它依赖拦截标准 `VK_KHR_swapchain`（管理待显示图像队列的 Vulkan 扩展）；使用其他 present（把图像提交到显示路径）机制时不会得到截图。截图可以帮助辨认捕获时对应的应用画面内容，但不能证明该画面已经交给显示端，也不能用图片时间戳代替 present fence 或 FrameTimeline。

启用 Vulkan layer 会改变运行环境。需要对外报告性能数字时，应另录一份未启用 layer 的基线 trace；诊断 trace 用来查找可疑阶段，基线 trace 用来确认修改后的真实收益。

### 6. Trace View 中能看到什么

APA 把每条时间轨道（track）中的 trace event 分为 slice、counter 与 flow：

- slice 有开始时间与持续时间，例如函数、阶段或 render pass；
- counter 是时点数值，例如频率、内存或电流；
- flow 连接不同 track 上有关联的 slice，用来表示一次工作如何跨线程或子系统传递。

下表中的 command buffer 是提交给 GPU 的命令列表；render pass 定义一组渲染附件及其处理范围；framebuffer 是本次渲染使用的颜色、深度等图像附件集合；submission 是一次 GPU 队列提交。stall 表示硬件单元因等待数据或资源而停顿，async event 则是开始与结束可能落在不同时间或线程上的异步事件。

当前官方文档列出的主要区域包括：

| 区域 | 数据 | 常见用途 |
|---|---|---|
| CPU Scheduling / Utilization / Frequency | 每核调度 slice、利用率、频率 | 区分 Running、Runnable delay（可运行但尚未获得 CPU）、抢占和频率变化 |
| Battery | current、charge、capacity | 观察趋势；USB 连接会持续充电，不能直接当作脱机功耗 |
| GPU Memory | GPU 内存及全 trace 的 min/max/average | 找资源增长或场景峰值 |
| GPU Queues | 硬件队列工作；Vulkan 场景可含 command buffer、render pass、framebuffer | 估算 GPU 阶段与 submission 关系 |
| Vulkan Events | `vkQueueSubmit` 与 `submission_id` | 关联 CPU submit 和 GPU queue slice |
| GPU Counters | 设备支持的周期采样 counter | 分析利用率、stall、纹理/顶点带宽；具体含义以 GPU 厂商文档为准 |
| SurfaceFlinger Events | 各 layer 的 On Display、active buffer 与生命周期 | 关联 buffer 到显示阶段 |
| Processes / Threads | 进程、线程、counter、async event | 回到主线程、RenderThread 与工作线程 |
| Actual Timeline | janky frame（卡顿帧）的严重程度与详情 | 从问题帧进入跨层分析 |

USB 充电对 Battery Usage track 有直接影响。APA Quickstart 要求 USB 连接，官方数据说明也提醒设备会在测试期间充电；需要能量结论时，应转到规范化功耗测试、Batterystats（Android 电池用量统计）、power rail（硬件电源域计量）或实验室仪器。

### 7. 浏览、对照与 SQL

Trace View 支持按名称过滤 track、缩放和平移、pin track（把轨道固定在顶部）、添加 bookmark（时间书签）、选择时间范围，以及用 box selection 一次框选多条轨道中的事件。关闭 trace 后，APA 会保存 pinned tracks、bookmark、zoom 与 scroll position。多份 trace 可以用 tab、window 或 split view（分栏视图）同时打开；视觉对齐适合复盘，定量比较仍应使用相同 SQL 或 benchmark metric（固定定义的基准指标）。

SQL 标签页执行 PerfettoSQL，并保存跨 trace、跨 Project 共享的 query history（历史查询）。下面的查询用于查找 `com.android.systemui` 中持续至少 8 ms 的 Runnable 区间。

```sql
SELECT
  p.name AS process_name,
  t.name AS thread_name,
  ts.ts / 1e9 AS start_s,
  ts.dur / 1e6 AS runnable_ms
FROM thread_state AS ts
JOIN thread AS t USING (utid)
JOIN process AS p USING (upid)
WHERE ts.state = 'R'
  AND p.name = 'com.android.systemui'
  AND ts.dur >= 8e6
ORDER BY ts.dur DESC;
```

结果表示线程已经可运行、但在该区间内没有执行。它可能来自 CPU 竞争、优先级、调度约束或更高优先级工作，不能仅凭一行结果断言根因。下一步应回到对应时间窗，检查 CPU Scheduling、wakeup（线程唤醒事件）、当前运行线程、频率与相关 slice。更多查询模式见 14.7 的 Perfetto SQL 查询手册。

官方还提供 `perfetto-sql` 与 `perfetto-trace-analysis` 两个 skill，供 AI agent 生成查询或给出分析起点。使用前需要安装对应 skill；生成结果仍要检查当前 trace 的表、字段、单位和进程范围，AI 给出的自然语言解释不能替代 trace 证据。

### 8. 三类常用分析

#### 8.1 帧耗时

分析一帧时，先区分 CPU total time（两次帧提交之间包含等待的总时长）、CPU active time（CPU 实际运行该 App 代码的时长）、GPU time 与最终 present 结果。

- Vulkan 场景可用相邻 `vkQueuePresentKHR` 之间的区间估算 CPU total frame time；其中包含等待 GPU 或 buffer 的时间；
- CPU active time 要统计该帧窗口内主线程、render thread 和 worker（工作线程）的 Running slice，不能只量一条线程；
- GPU slice 可用时，它比 counter 更适合估算 GPU frame time；
- GPU slice 缺失时，可以用 GPU utilization（利用率）、instruction（指令活动）或 queue counter 的周期模式估算边界，但精度较低；
- 一帧可能包含多次 Vulkan submission，应使用 Vulkan Events 与 `submission_id` 关联同一帧的 GPU 工作；
- Actual Timeline 的 jank slice（卡顿帧区间）、SurfaceFlinger On Display 和 expected/actual present（预期/实际显示时间）用来确认用户是否晚看到这一帧。

CPU submit 返回、GPU producer completion fence、SurfaceFlinger latch、display present fence 和 layer release fence 是不同的时序边界。completion fence 表示 producer 已完成 buffer 写入，consumer 可以安全读取；latch 表示 SurfaceFlinger 选中该 buffer 参与本轮合成；present fence 是本轮 display present 的系统时间锚点；release fence 则通知 producer 何时可以复用旧 buffer。APA 中 `vkQueuePresentKHR` 或 GPU queue slice 结束都不能单独证明一帧已经显示；应沿 submission ID、buffer/layer、fence 与 FrameTimeline 对齐。队列中存在多帧 in flight（已提交、尚未显示）时，FPS 稳定也可能伴随较高的输入到显示延迟。

#### 8.2 GPU 内存效率与带宽

APA 官方的 Memory Efficiency 分析主要讨论 GPU counter 与 memory bandwidth（单位时间内通过内存总线的数据量），不等同于 Java heap allocation（堆对象分配）或泄漏分析。建议按以下顺序读取：

1. 用 counter 周期确定单帧窗口，避免把独立采集的 GPU slice 边界直接套到 counter；
2. 查看总 read/write bandwidth；
3. 再区分 texture（纹理）、vertex（顶点）、cache（缓存）与 fetch stall（取数等待）；
4. 将峰值与 render pass、GPU queue 和帧耗时对齐；
5. 到 AGI Frame Profiler 或引擎资源统计中检查纹理格式、mipmap（多级缩小纹理）、vertex layout（顶点数据内存布局）、render target（渲染输出图像）和 draw submission（绘制提交批次）。

Adreno 与 Mali 的 counter 名称和计算方法不同，阈值也依赖 GPU、总线、分辨率与工作负载。团队看板应绑定 GPU 型号、driver、counter 名称和单位，不应把一台设备的数值直接推广到其他 SoC（System on Chip，片上系统）。

Java/Kotlin 对象增长、GC（垃圾回收）与调用栈交给 Android Studio Memory Profiler、heap dump（堆转储）或 LeakCanary；native heap 可结合 `heapprofd`（Perfetto 原生堆采样器）。APA 提供的是系统时间线上下文。

#### 8.3 线程调度

线程调度分析要区分三类时间：

- Running：线程占用 CPU；
- Runnable：线程具备运行条件，但尚未获得 CPU；
- Sleeping/Blocked：线程等待 timer（定时器）、futex（用户态同步原语的内核等待）、Binder IPC、I/O 或其他依赖。

长 Running 指向工作量，长 Runnable 指向调度延迟，长 Blocked 指向依赖等待。这三类只能确定排查方向。若线程频繁迁核或落在不合适的 CPU 上，先检查线程优先级、任务划分、负载和 ADPF（Android Dynamic Performance Framework）的 Performance Hint。官方 APA 调度指南建议使用 Performance Hint API 向系统表达性能需求，不建议把手工 affinity（把线程绑定到指定 CPU）作为通用修复。

Android 17 的调度 tracepoint 来自固定内核锚点 `android17-6.18-2026-06_r6`。APA 展示的 `sched_switch`、`sched_wakeup` 反映内核调度事实；CPU topology（核心层级与大小核布局）、uclamp（调度利用率上下限）、cpuset（任务可使用的 CPU 集合）、thermal（温控限制）和厂商 scheduler 策略仍要结合设备源码与 Perfetto 轨道解释。

### 9. APA 与其它工具如何分工

| 问题 | 首选工具 | APA 的角色 |
|---|---|---|
| 系统级卡顿、线程调度、CPU/GPU/帧关联 | APA 或 Perfetto UI | Project 化录制、Trace View、SQL、A/B 对照 trace |
| Java/Kotlin 方法热点 | Android Studio CPU Profiler | 提供系统上下文与目标时间窗 |
| Java/Kotlin 分配、GC、对象泄漏 | Memory Profiler、heap dump、LeakCanary | 关联场景、进程内存与帧变化 |
| Vulkan 单帧 shader、pipeline、纹理、几何 | AGI Frame Profiler | 确定异常帧与系统侧 CPU/GPU 上下文 |
| WindowManager、SurfaceFlinger 状态机和跨窗口问题 | Winscope | 提供 buffer、layer 和帧时间线线索 |
| 可重复启动、滚动和帧指标 | Macrobenchmark | 对异常样本做人工 trace 复盘 |
| CI 批量指标 | Trace Processor、PerfettoSQL | 人工打开回归 trace |
| 线上真实用户 trace | `ProfilingManager` + Perfetto UI | APA 不提供线上采集 API；导出的脱敏 trace 能否完整显示，要按 APA 版本验证 |
| 长时间耗电与后台行为 | Batterystats、Battery Historian、statsd | 在短时 trace 中关联 CPU/GPU/电流变化 |

Winscope 用于查看 WindowManager 与 SurfaceFlinger 状态；Macrobenchmark 是 Jetpack 的可重复性能基准框架；CI（Continuous Integration）是持续集成流水线；`ProfilingManager` 是面向真实用户设备采集脱敏 profile 的 Android API；statsd 是 Android 系统统计守护进程。它们解决的问题不同，APA 主要承担本地 system trace 的交互分析。

2026 年 5 月发布文把 APA System Profiler 称为 open beta，当前 APA 下载页已移除这一标记；AGI 页面中的“public beta”属于尚未同步的旧文案。官方仍推荐 APA 做 system profiling，但没有宣布 AGI Frame Profiler、Android Studio Profiler、Perfetto CLI 或 Trace Processor 停止使用。

### 10. Android 17 平台边界

在 `android-17.0.0_r1` 上评审 APA 结论时，分三层记录版本：

- APA 桌面版本：决定 GUI、默认配置、Vulkan layer、SQL 与文件管理能力；
- Android build fingerprint / `android-17.0.0_r1`：决定 framework trace event、Perfetto producer、FrameTimeline 和系统服务行为；
- kernel `android17-6.18-2026-06_r6` 与 vendor driver：决定 scheduler/ftrace 语义、GPU counter、render stage 和设备能力。

APA 安装包不属于 `android-17.0.0_r1` framework 源码。平台 tag 中找不到 APA 可执行文件，不能据此否定这个桌面产品；反过来，APA 文档出现一项 UI 能力，也不能证明所有 Android 17 设备都有对应 data source。

### 11. 一轮可复查的 APA 实验

建议把一次分析记录成以下结构：

1. 固定设备、build fingerprint、GPU/driver、刷新率、亮度、电量和温度；
2. 固定 App APK、代码提交、构建类型、`debuggable` 与引擎配置；
3. 固定 APA 版本与 Project；
4. 切换到 Use custom trace configuration，复制并保存界面生成的 `TraceConfig`；
5. 固定 launch mode、trigger、duration、测试数据和操作脚本；
6. 录制基线 trace，标记异常帧和时间窗；
7. 用 track、flow、详情面板与 SQL 形成一个能被后续证据验证或推翻的原因假设；
8. 修改后用同一配置、同一场景重录；
9. 并排打开两份 trace，再用同一 SQL 或 Macrobenchmark metric 做 A/B 对照；
10. 保存 trace、查询、截图、结论、反例和仍未验证的部分。

短 trace 适合定位一轮交互，长时间功耗、温升和降频需要专门实验。不要为了让 Trace View 更丰富而开启所有数据源；记录不到目标事件时再按证据缺口增加 data source。


## 动态目标可达性与路径重建

系统性能检查定位异常区域后，GAPS 类方法用于回答目标函数或状态怎样被实际执行路径触达。静态存在不等于运行时可达。

### 方法可达性有两个判定阶段

“静态找到路径”和“设备上执行到目标方法”是两个不同事件。这里的 Android 入口指外部可启动的组件或框架回调，不等同于 Java `main()`：

| 阶段 | 成功条件 | 不能推出的结论 |
| --- | --- | --- |
| 静态路径重建 | 至少生成一条包含目标方法的路径 | 路径在当前账号、权限和 UI 状态下一定可执行 |
| 动态目标触达 | AndroLog 日志插桩或 Frida 动态 Hook 观察到目标方法调用 | 该方法造成卡顿、ANR（应用无响应）、耗电或安全影响 |

论文使用 AndroTest 自动交互基准中的 56 个开源应用，每个应用固定随机选择 50 个目标方法，并让各工具使用同一组目标。只有 34.39% 的目标位于 `Activity`（Android 界面组件）中，多数目标无法通过浅层页面遍历直接命中。

v3 报告的结果如下：

#### 静态路径重建

| 工具 | 生成至少一条路径的目标占比 | 平均分析时间/应用 |
| --- | ---: | ---: |
| DroidReach | 9.48% | 23.46 秒 |
| FlowDroid | 58.81% | 35.06 秒 |
| GAPS | 88.24% | 12.67 秒 |

这里的 88.24% 是“至少生成一条路径”的目标占比，不是路径精确率，也不能解释成 88.24% 的目标已经在设备上执行。

#### 动态目标触达

| 工具 | 动态触达率 | 论文表中的平均运行时间 |
| --- | ---: | ---: |
| GoalExplorer | 4.75% | 30 分钟超时 |
| APE | 11.12% | 30 分钟超时 |
| Guardian | 34% | 30 分钟超时 |
| GAPS（关闭 PHIL） | 23.24% | 2 分 26 秒 |
| GAPS（启用 PHIL） | 56.93% | 3 分 15 秒 |

动态基线均运行三轮，每轮上限 30 分钟。GAPS 在这些实验中没有超过 5 分钟，表中的 3 分 15 秒是平均运行时间，不能写成“所有工具统一使用 5 分钟超时”。PHIL 从 23.24% 提升到 56.93% 的消融实验（关闭一个模块后比较结果）也说明，v3 的完整动态结果包含 agent fallback（确定性步骤失败后的代理补救）；LLM（Large Language Model，大型语言模型）已是论文实验的一部分。

### GAPS 的处理链

GAPS 把一次查询分成静态分析与动态执行。call graph（调用图）记录方法之间的调用关系，GUI 触发点是需要点击或输入的界面元素：

`目标方法` → `目标导向的反向调用图` → `入口、条件和 GUI 触发点` → `JSON 交互指令` → `设备执行` → `运行时触达证据`

#### 1. 从 APK/DEX 建立分析表示

静态阶段使用 Androguard 的 `AnalyzeAPK`/`AnalyzeDex` 读取 APK、DEX、基本块和 smali（DEX 的汇编式文本表示）指令，并用 Python 图算法库 NetworkX 表示局部调用图。Apktool 负责反编译资源表，后续可把 smali 中的整型资源值映射为 `public.xml` 里的字面量资源 ID。

这条路线直接分析编译产物，不要求应用源码。代价是信息上限受 DEX、资源表、混淆和框架建模能力约束；源码中的类型语义、生成过程和运行期状态不会自动恢复。

#### 2. 识别 Android 入口与 ICC

Android 应用没有单一 `main()` 入口。ICC（Inter-Component Communication，组件间通信）通过 Intent 连接 `Activity`、`Service`、`BroadcastReceiver` 等组件。GAPS 会检查 manifest（应用清单）中导出的组件和 intent filter（Intent 匹配规则），也会分析动态注册的 receiver（广播接收器）及其注册路径。ICC 映射保存组件类名、action（动作字符串）或关联路径，供反向遍历在合法入口处停止。

论文也限定了这一步的能力：带权限的入口、只能由系统发送的广播，以及要求额外 data 参数的 Intent，可能有静态路径却无法自动构造出可执行输入。当前实现不能概括为已经完整求解 action、category（分类）、URI（数据地址）和 extras（附加键值参数）。

#### 3. 按目标反向生成局部调用图

GAPS 从目标方法向调用者反向扩展，按需构建 CHA（Class Hierarchy Analysis，类层次分析）图，对运行时才确定实现的虚调用保守列出潜在调用者；遇到已识别入口时停止该分支。它不预先构建整应用的完整调用图。

v3 的 Algorithm 2 把路径提取写成深度优先遍历 `dfs_visit`；同一论文的实现说明与公开快照 `path_generation.py` 则使用自定义 `all_shortest_paths()`，在 `path_limit` 上限内枚举入口与目标之间的最短路径。复现实验应固定快照文件，不能只按伪代码名称推断枚举策略。论文将整体分析描述为 target-oriented（围绕目标）、demand-driven（按需扩展）、inter-procedural（跨方法）和 context-sensitive（区分调用上下文）。EdgeMiner 与 Soot virtual edges（框架隐式回调边）提供回调映射，但未跟踪的 implicit flow（由框架隐式触发、源码中没有直接调用语句的执行流程）仍会让调用图漏边。

#### 4. 补足条件路径

候选路径中的条件会进入 points-to analysis（指向分析，追踪引用可能指向哪些对象）与 constant propagation（常量传播，推导变量可能取到的常量）。v3 明确覆盖三类操作数：

- `int`、`String`、`float` 等变量和基本类型；
- 与 `null` 比较的对象；
- 方法返回值。

分析器回溯左右操作数的来源，传播候选常量，再合并能满足条件的赋值路径。这里得到的是静态可满足路径；账号态、网络返回、随机数、服务端配置等运行期输入仍可能让设备执行停住。

#### 5. 找到 GUI 事件和资源 ID

GAPS 识别 `onClick()`、`onItemSelected()` 等 handler（事件处理方法），沿 listener（监听器）注册和对象来源回溯到 `findViewById()`，再解析其资源参数。生成的 JSON 指令包含：

- 可执行入口；
- `Activity` 名称；
- 需要交互的图形元素 ID 序列；
- 对应 call sequence（方法调用序列）。

XML View 体系能提供稳定资源 ID，正好适合这套分析。Jetpack Compose 通过 Kotlin lambda（匿名函数）挂接事件，界面节点还会随 recomposition（状态变化后的重组）改变；v3 的 Limitations 明确说明当前不支持 Compose。

### 动态执行：确定性指令加受限 PHIL

动态阶段安装应用，并用 AndroidViewClient 的 `findViewById()` 与 `touch()` 执行静态指令。论文 Algorithm 5 在每条候选路径开始前调用 `restart_app()`，执行器持续轮询 runtime monitor（运行时触达监视器）；方法被观察到后返回 `REACHED`，当前路径无法继续时转试下一条。公开快照的具体重启范围与这段伪代码不同，见下文边界说明。

确定性操作（同一输入按既定指令执行）遇到权限弹窗、广告或动态布局时，v3 会调用 PHIL（Predictive Handler for Interface Limitations，界面障碍预测处理器）。它接收经过筛选的当前 GUI 层级、目标方法和静态路径，并输出 `click`、`type` 等结构化动作。论文实验写的是 GPT-5.4、temperature（采样随机度）0.7；2026-08-14 可访问的复现快照 `phil.py` 则配置 `gpt-5.4-mini`、temperature 0.7。PHIL 是 LLM 组件，可关闭也可替换模型，因此模型名必须随实验记录，不能视为 GAPS 的稳定接口。

PHIL 的调用受到两层约束：

- 每条路径中的同一个 `Activity` 最多介入一次；
- 障碍仍未清除，或该 `Activity` 已用过 PHIL 时，当前路径会终止。

以上是论文 Algorithm 5 的语义。复现快照 `gaps_run.py`（`b87d111d`）把 `llm_used` 保存在 `GAPSRUN` 实例上，没有在每条候选路径开始时清空；快照中的 PHIL 线程单次还可尝试最多 15 个动作。工程复现不能把“每路径每 Activity 一次”直接套到该快照，必须以固定代码和运行日志确认实际预算。

论文中的约束用于避免 agent（自动决策代理）无限探索，并保留静态路径的主导地位。PHIL 仍带有非确定性，论文通过每个应用运行三轮并报告平均值来反映部分波动。

#### 当前仓库命令的含义

下面的命令展示 4open.science 复现快照中的两阶段入口。`uv` 是 Python 环境与依赖管理工具，`uv.lock` 锁定具体依赖版本；实际使用时还应保存快照文件哈希：

```bash
uv sync

uv run gaps static \
  -i app-under-test.apk \
  -sig 'Lcom/example/Target;->work(Ljava/lang/String;)V' \
  -cond \
  -o gaps-output

uv run gaps run \
  -i app-under-test.apk \
  -instr gaps-output/path-to-instructions.json \
  -frida
```

`static` 生成路径和高层指令，`-sig` 接收 smali 格式的方法签名；`run` 才会操作设备。示例中的 `path-to-instructions.json` 是占位文件名，快照实际写到 `<输出目录>/<APK 基名>/<APK 基名>-instr.json`。`-frida` 需要具有 root 权限且运行 frida-server 的设备或模拟器；PHIL 所用模型还可能要求通过环境变量提供 API 凭据。自动化环境不应只记录“使用最新版”。

### Runtime monitor 只回答“是否触达”

论文使用了两种目标方法触达证据：

- AndroTest 应用可重新打包，使用 AndroLog 在方法中插入日志；
- 真实应用无法稳定通过 AndroLog 重新打包时，使用 GAPS 的 Frida integration（Frida 集成模块）动态 Hook 目标方法。

这两种证据都比“页面已经打开”严格，因为页面完成不保证特定方法执行。它们仍不提供性能因果关系：一次 hook 命中没有说明方法耗时，也没有说明其调用发生在 missed frame、ANR 前兆或功耗尖峰内。

Frida Hook 本身会改变执行时间。短方法、锁竞争、JIT（运行时即时编译）/AOT（预先编译）边界和高频调用尤其容易受探针开销干扰。性能实验应把“无 Hook 的基线 trace”和“带 Hook 的定位 trace”分开，必要时改用应用源码中的 `Trace.beginSection()` 或 Perfetto SDK 埋点做低扰动复测。

### Perfetto 是 Android 17 工程扩展

GAPS 论文没有把 Perfetto 纳入路径生成、动态执行或 reachability（目标方法触达）判定。把二者组合时，职责应保持分离：

| 工具 | 在组合流程中的问题 |
| --- | --- |
| GAPS 静态阶段 | 怎样从入口走到目标方法 |
| GAPS 动态阶段 | 这套交互能否执行并命中方法 |
| Frida/AndroLog/应用 marker（时间标记） | 目标方法在什么时间被观察到 |
| Perfetto | 同一时间窗内哪些线程、帧、调度、I/O（文件或网络输入输出）或 fence（图形同步栅栏）出现异常 |
| simpleperf | CPU 样本主要落在哪些调用栈 |

#### 一套可复现的接入顺序

1. 记录 APK SHA-256、包名、`versionCode`、完整 smali 方法签名与 GAPS 快照文件哈希。
2. 运行静态阶段，人工检查 entry point（入口）、条件和 GUI ID 是否符合目标应用。
3. 准备独立测试账号、权限、网络响应与初始数据库；记录哪些状态无法由 GAPS 生成。
4. 在交互前启动 Perfetto，配置容量足够的 ring buffer（写满后覆盖最旧数据的环形缓冲区），并包含目标应用的 atrace（应用自定义 trace 事件）、FrameTimeline（帧预期与实际时间线）、调度、CPU 频率及场景所需数据源。
5. 安装 runtime monitor，再运行 GAPS 动态阶段。每轮同时记录 `REACHED`/`FAILED`、采用的候选路径、PHIL 是否介入和 marker 时间。
6. 只在 `REACHED` 样本内对齐目标 marker 与性能异常；`FAILED` 样本用于分析自动化可靠性，不能混入 P50/P95 等性能分位数。
7. 移除 Frida hook 后复测可疑场景，确认异常不由探针、重打包或调试环境引入。

论文 Algorithm 5 的每路径重启会改变进程冷启动/热启动、JIT、页面缓存、数据库连接和图片缓存；复现快照 `gaps_run.py` 则在目标方法级调用 `restart_app()`，遍历候选路径时主要重新启动主 `Activity`，没有逐路径 `force-stop`。若待测问题只在长会话、后台恢复或热缓存条件下出现，需要先确认所用版本的重置范围，再修改执行器或使用 `--manual-setup` 准备状态，不能笼统写成统一的 clean-state（干净初始状态）策略。

#### 用 Frida 注入时间锚点

下面的示例用于测试设备：它在目标 Java 方法的同一线程上包一层 `android.os.Trace` section，Perfetto 必须在 GAPS 执行前启动并采集该应用的 atrace。

```javascript
Java.perform(() => {
  const Trace = Java.use("android.os.Trace");
  const Target = Java.use("com.example.Target");
  const work = Target.work.overload("java.lang.String");

  work.implementation = function (arg) {
    Trace.beginSection("gaps_target:Target.work");
    try {
      return work.call(this, arg);
    } finally {
      Trace.endSection();
    }
  };
});
```

这个 `Trace` section（同步时间片）包围 Hook 调用期间的方法执行，可在应用线程轨道上提供时间锚点；`beginSection()` 与 `endSection()` 必须在同一线程成对调用。它不负责启动或停止 Perfetto，也不能替代 FrameTimeline。目标方法若被内联、位于 C/C++ 等 native 库、存在多个 overload（同名重载），或进程在 Hook 安装前已执行该方法，需要调整探针并单独验证。

#### jank、ANR 与功耗各看什么

- **jank（卡顿帧）**：从 missed `DisplayFrame`（最终显示帧）与对应 `SurfaceFrame`（应用或图层提交帧）出发，检查 marker 是否落在相关帧的生产区间；只在时间重叠且调用链合理时继续归因。
- **ANR**：确认目标方法与主线程、Binder 跨进程调用、锁等待或 input timeout（输入分发超时）的时序。方法命中早于 ANR 数十秒，通常还缺中间证据。
- **功耗/发热**：按同设备、同热状态、同网络条件做多轮对照；单次目标触达无法区分方法成本、PHIL 网络请求、Frida 或屏幕操作开销。
- **native 热点**：GAPS 的 DEX 路径可触达 Java/Kotlin 包装层，native 内部成本仍需 simpleperf、Perfetto native heap/CPU 数据或库内 marker。

### v3 的真实应用实验

论文还在 2026 年 6 月收集的 Google Play 下载量前 50 应用上，以 SPECK（按 Google 安全与隐私规则识别潜在违规的静态分析器）报告的方法为目标。只有 5.55% 的目标位于 `Activity` 中，场景比 AndroTest 更偏向深层代码。

| 指标 | v3 结果 |
| --- | ---: |
| 静态路径生成率 | 62.03% |
| 平均静态分析时间/应用 | 278.9 秒 |
| 生成的 call sequence | 219 条 |
| call sequence 长度 | 1—41，均值 12.42，中位数 4 |
| 三轮动态触达率均值 | 54.80% |
| 动态执行平均时间 | 4 分 48 秒 |

真实应用实验用 Frida 作为触达证据。62.03% 与 54.80% 的差值不能直接叫“静态误报率”：有些静态路径成立，但运行期需要登录、支付、特定文本、动态内容、权限或 Intent 参数，执行器没有构造出对应状态。

这些数字也不应外推为 Android 17 应用的成功率。样本、目标选择、应用版本、设备、模型和时间预算都会改变结果；Compose 在现代应用中的占比还会进一步影响 GUI ID 提取。

### 与相关工具的边界

| 工具 | 主要目标 | 输出/执行方式 | 与 GAPS 的差别 |
| --- | --- | --- | --- |
| FlowDroid | Android 污点与数据流分析 | 全程序抽象、dummy main（合成入口）、数据流结果 | 不生成面向目标方法的可执行 GUI 指令 |
| DroidReach | 静态路径重建 | 基于完整 call graph 输出路径 | 没有 GAPS 的动态执行、条件解析和 GUI trigger 链 |
| APE | 覆盖率导向 GUI 探索 | 模型驱动事件生成 | 不掌握目标方法的静态路径 |
| Guardian | 用户任务导向 LLM 交互 | 根据界面语义规划动作 | v3 中作为独立动态基线；不是 GAPS 内部 fallback |
| GoalExplorer | screen/activity 导向探索 | Screen Transition Graph（页面转换图）+ 动态探索 | 引导单位偏页面和 Activity，不以方法级 backward slice（从目标反推相关语句的切片）为起点 |
| PHIL | GAPS 内部受限 agent | 只在确定性步骤失败时处理 UI 障碍 | 它是 GAPS v3 的 fallback，不是 Guardian 的别名 |

比较百分比时还要核对预算和分母。FlowDroid/DroidReach 的百分比属于静态路径生成，APE/Guardian/GoalExplorer/GAPS Dynamic 属于动态方法触达；把两列按高低排在一起没有统计意义。

### 已验证的限制与工程外推

论文 v3 直接列出的限制包括：

- Flutter/React Native 的主要逻辑不在传统 Dalvik/DEX 字节码中；
- 混淆会引发 path explosion（候选路径数量快速膨胀）并增加分析时间；
- 库中的 dead code（不可达但仍留在输入中的代码）会拖慢路径重建；
- callback mapping（回调映射）未覆盖的 implicit flow 会造成 call graph unsoundness（调用图漏掉真实运行时边）；
- 当前不支持 Jetpack Compose；
- 游戏胜利、账号、支付等复杂状态可能阻断动态执行；
- intent filter 入口可能要求权限、系统身份或额外 data 参数；
- 动态布局和 WebView 会干扰静态 GUI 提取；
- PHIL 引入非确定性。

反射、动态代理、Dagger/Hilt 依赖注入和 JNI 是 Android 程序分析中常见的额外风险，但论文没有提供这些类别的 GAPS 分项命中率。工程报告可以把它们列为待验证条件，不能从 88.24% 或 56.93% 推导专项能力。

Android 17 上还要额外核对：

- 目标应用是否主要采用 Compose；
- entry component（入口组件）是否可从测试环境启动，权限和导出属性是否允许；
- Frida 所需 root、SELinux 与进程架构条件是否满足；
- split APK（拆分安装包）、dynamic feature（按需交付模块）和运行期代码加载是否都进入分析输入；
- 目标方法签名是否因 R8、版本更新或 multi-dex（多个 DEX 文件）布局改变。

### 复现实验检查清单

静态阶段：

- 固定论文版本、4open.science 文件哈希、Python/`uv.lock`、Androguard 与 Apktool 版本。
- 固定 APK hash、目标签名、path limit（每次查询的路径数量上限）、`-cond` 与其他 CLI 参数。
- 保存生成的 JSON、call sequence、分析时长和失败原因。

动态阶段：

- 记录设备型号、Android 版本、ABI（二进制接口/处理器架构）、root/Frida 版本、分辨率和导航模式。
- 固定应用初始状态、账号、权限、locale（语言与地区）、网络响应和广告策略。
- 保存每轮候选路径、PHIL 调用、动作序列、runtime monitor 与执行时间。
- 至少重复三轮，分开报告确定性路径与 PHIL 路径。

性能扩展：

- Android 17 测试写明 API 37 与具体 build fingerprint（系统构建指纹）。
- trace 在自动交互前启动，避免丢失入口和首帧。
- reachability 结果与性能指标使用不同字段。
- hook、重打包和 release 原包分别建基线。
- 结论同时给出目标 marker、线程/帧证据和无探针复测。


## 版本与实现边界

GAPS（Graph-based Automated Path Synthesizer，基于图的自动路径合成器）解决一个方法级问题：给定 APK（Android 安装包）/DEX（Android 字节码）与目标方法，能否找出从 Android 入口到该方法的调用路径，并自动执行对应交互。它不负责衡量一帧是否卡顿，也不替代 Perfetto 系统 trace、`simpleperf` CPU 采样或应用埋点。

以下说明依据 2026 年 7 月 17 日发布的论文 v3 与论文公开的 4open.science 复现快照。v3 已更名为 *GAPS: Targeted Execution of Android Apps via Static Path Reconstruction*，作者也从 v1 的 2 人扩展为 5 人；实验环境、动态基线、运行时间和 PHIL 代理模块数据均有更新。57.44%、Guardian 17.12%、静态分析 4.27 秒及 Android 13 模拟器等数字来自 v1，不能代表 v3。

平台集成部分以 Android 17 / API 37 / `android-17.0.0_r1` 为知识库锚点。论文自身的动态实验使用 Android 16 x86-64 模拟器；需要 ARM 架构时使用 Pixel 2 / Android 11。论文没有报告 Android 17 实验，因此文中的 Android 17 + Perfetto 流程属于工程扩展，不能写成论文已验证结论。

## 小结

APA 和 GAPS 的共同点是帮助自动化工作流程取得“实际发生了什么”的证据，但它们的证明责任不同。APA 用 system trace 定位线程、帧、内存和功耗异常；GAPS 用静态路径重建与动态触达验证目标方法是否可达。“已触达方法”不等于“方法造成性能问题”，两类结果必须使用不同字段、版本边界和复现记录。


## 参考资料

### Android Performance Analyzer

- [Android Performance Analyzer](https://developer.android.com/android-performance-analyzer)
- [APA Quickstart](https://developer.android.com/android-performance-analyzer/quickstart)
- [Record a system trace](https://developer.android.com/android-performance-analyzer/run)
- [View a system trace](https://developer.android.com/android-performance-analyzer/view)
- [Understand trace data](https://developer.android.com/android-performance-analyzer/view/data)
- [Analyze frame processing times](https://developer.android.com/android-performance-analyzer/analyze/frame-times)
- [Analyze memory efficiency](https://developer.android.com/android-performance-analyzer/analyze/mem-efficiency)
- [Analyze thread scheduling](https://developer.android.com/android-performance-analyzer/analyze/thread-sched)
- [Android Developers Blog: Introducing APA](https://developer.android.com/blog/posts/introducing-android-performance-analyzer-the-next-evolution-in-profiling-for-android)
- [AGI System Profiler: APA recommendation](https://developer.android.com/agi/sys-trace/system-profiler-gui)
- [Perfetto documentation](https://perfetto.dev/docs/)
- [Android 17 `TraceConfig`](https://android.googlesource.com/platform/external/perfetto/+/refs/tags/android-17.0.0_r1/protos/perfetto/config/trace_config.proto)
- [Android 17 Perfetto tracing service](https://android.googlesource.com/platform/external/perfetto/+/refs/tags/android-17.0.0_r1/src/traced/service/)
- [Android 17 common kernel scheduler tracepoints](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/include/trace/events/sched.h)

### GAPS 与目标可达性

- GAPS 论文 v3：[GAPS: Targeted Execution of Android Apps via Static Path Reconstruction](https://arxiv.org/abs/2511.23213v3)
- 旧数字对照：[GAPS 论文 v1](https://arxiv.org/abs/2511.23213v1)
- GAPS 公开复现快照：[GAPS README](https://anonymous.4open.science/r/GAPS/README.md)
- 动态交互库：[AndroidViewClient](https://github.com/dtmilano/AndroidViewClient)
- 动态插桩：[Frida](https://frida.re/)
- 资源反编译：[Apktool](https://apktool.org/)
- DEX 静态分析：[Androguard](https://github.com/androguard/androguard)
- 方法日志插桩：[AndroLog](https://arxiv.org/abs/2404.11223)
- Android trace API：[`android.os.Trace`](https://developer.android.com/reference/android/os/Trace)
- Perfetto Android tracing：[Android tracing quickstart](https://perfetto.dev/docs/quickstart/android-tracing)
- Perfetto 应用事件：[ATrace data source](https://perfetto.dev/docs/data-sources/atrace)
- Perfetto 帧判定：[FrameTimeline](https://perfetto.dev/docs/data-sources/frametimeline)
- Perfetto 缓冲区语义：[Trace configuration](https://perfetto.dev/docs/concepts/config)
