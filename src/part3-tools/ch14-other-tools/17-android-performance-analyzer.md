---
title: Android Performance Analyzer 与系统性能分析
chapter: 14.17
section: 14.17
status: finalized
applicable_versions: "Android 12 (API 31) - Android 17 (API 37)（APA System Profiler 要求受支持的 Android 12+ 设备；平台源码说明以 Android 17 为锚点）"
tags: [工具使用, 系统分析, 性能诊断]
last_verified: "2026-08-13"
last_verified_against: "APA 首页更新至 2026-08-12；Quickstart、录制、Trace View 与三类分析指南当前版本；android-17.0.0_r1；android17-6.18-2026-06_r6"
confidence: high
task6_state: reviewed
task9_state: reviewed
pipeline_stage: ready-to-publish
last_deep_review_at: "2026-07-26T20:36:00+08:00"
last_deep_review_run_id: "20260726-203519-deep-review-009e010e"
last_rework_at: "2026-07-26T21:35:26+08:00"
last_rework_run_id: "20260726-213526-rework-009e010e"
sources:
  - type: official
    path: "https://developer.android.com/android-performance-analyzer"
  - type: official
    path: "https://developer.android.com/android-performance-analyzer/quickstart"
  - type: official
    path: "https://developer.android.com/android-performance-analyzer/run"
  - type: official
    path: "https://developer.android.com/android-performance-analyzer/view"
  - type: official
    path: "https://developer.android.com/android-performance-analyzer/view/data"
  - type: official
    path: "https://developer.android.com/android-performance-analyzer/analyze/frame-times"
  - type: official
    path: "https://developer.android.com/android-performance-analyzer/analyze/mem-efficiency"
  - type: official
    path: "https://developer.android.com/android-performance-analyzer/analyze/thread-sched"
  - type: official
    path: "https://developer.android.com/blog/posts/introducing-android-performance-analyzer-the-next-evolution-in-profiling-for-android"
  - type: official
    path: "https://perfetto.dev/docs/"
  - type: official
    path: "https://developer.android.com/studio/profile"
  - type: official
    path: "https://developer.android.com/topic/performance/power/battery-historian"
  - type: obsidian
    path: "/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Writer/rendering_pipelines/S13_game_type.md"
  - type: internal
    path: "src/part3-tools/ch13-perfetto/01-perfetto-intro.md"
  - type: internal
    path: "src/part3-tools/ch14-other-tools/01-as-profiler.md"
  - type: internal
    path: "src/part3-tools/ch14-other-tools/02-simpleperf.md"
  - type: internal
    path: "src/part3-tools/ch14-other-tools/07-dumpsys.md"
  - type: internal
    path: "src/part3-tools/ch14-other-tools/08-battery-historian.md"
---
# 14.17 Android Performance Analyzer 与系统性能分析

Android Performance Analyzer（APA）是 Google 面向 Android App 与游戏提供的性能分析工具。官方提供独立桌面应用；2026 年 5 月的发布文还说明，其 System Trace viewer 已进入 Android Studio Panda 4 Canary 及后续版本。本文聚焦独立版 System Profiler。

官方在 2026 年 5 月 19 日以 open beta 发布 System Profiler。截至 2026 年 8 月 13 日，8 月 12 日更新的 APA 下载页已不再标注 Beta；旧 AGI 页面仍保留“public beta”字样，不能用这条滞后的交叉链接判断当前发布状态。当前 APA 文档仍以 System Profiler 为主：录制 system trace（系统追踪）、在 Project（组织多份 trace 的项目容器）中管理数据、查看 CPU/GPU/内存/功耗与 SurfaceFlinger（Android 系统合成器）事件、运行 PerfettoSQL，并为 Vulkan 工作负载补充调试数据。Vulkan render pass（渲染阶段及其附件处理范围）名称和截图属于 trace 增强信息，不能当成逐 draw（逐次绘制调用）的单帧 capture/replay（捕获与回放）。

设备侧平台锚点是 Android 17 / API 37 / `android-17.0.0_r1`，内核侧固定到 `android17-6.18-2026-06_r6`。APA 的发布周期独立于 Android 平台；它支持 Android 12 及以上的受支持设备，不能写成“Android 17 新增的 framework API”。

## 1. APA 在工具链中的位置

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

## 2. 安装与设备要求

APA 首页提供 Windows、macOS 和 Linux 安装包。Quickstart 给出的主机要求如下：

- Windows：64 位 Windows 10 或更高版本；
- macOS：macOS 12 或更高版本，并且只支持 Apple Silicon；
- Linux：64 位环境需要相应的 64 位运行库；
- 所有平台都要安装 Android SDK Platform-Tools（包含 `adb` 等设备工具），并把 `ANDROID_HOME` 指向 Android SDK 根目录。

设备侧要求为“受支持的 Android 设备 + Android 12 或更高版本 + USB + 可用 adb debugging（通过 Android Debug Bridge 调试）”。Android 版本达标不保证所有机型都通过支持检查。首次连接新设备时，APA 会执行 device validation（设备与采集能力兼容性检查）；验证期间不要操作设备。通过后，Configure a Recording 的设备项旁会出现绿色标记。

不同设备、GPU 与驱动暴露的数据不同。缺少 GPU counter（周期采样的硬件指标）、GPU queue（GPU 硬件执行队列）或 Vulkan 信息时，应检查设备支持、驱动、App 构建和录制配置，不能从空轨道推断“GPU 没有工作”。

## 3. 被测 App 应该用哪种构建

官方 Quickstart 对 managed-code App（主要运行 Java/Kotlin 托管代码的应用）与 Vulkan App 给出了不同建议。这些是提高测量准确性的建议，不是启动 APA 的硬性条件：

- Java/Kotlin 性能测量建议使用 release 版本或开启编译、打包优化的性能构建，并设置 `debuggable=false`，让 ART 运行在接近发布环境的优化状态；
- Vulkan App 或游戏若要采集 Vulkan-specific data（Vulkan 专属数据），建议设置 `debuggable=true`，以便 APA 注入或启用对应的 Vulkan 调试能力；
- 纯 C/C++ 或 native game loop（原生游戏循环）受 ART debug 状态的影响较小，但编译优化、符号、引擎配置和资源包仍要固定。

一个同时包含大量 Java/Kotlin 代码和 Vulkan 渲染的 App 很难用单次录制兼顾两种目标。建议保留两种实验：

1. 接近发布配置（release-like）、不可调试（non-debuggable）的构建，用来测启动、UI、调度和整体帧表现；
2. 原生代码优化保持一致、但 `debuggable=true` 的 Vulkan 诊断构建，用来采集 API timing（CPU 侧 API 调用耗时）、render pass name 或 screenshot（捕获画面）。

两次 trace 不能直接按绝对时间互换结论。构建类型改变后，应记录 APK、代码提交、编译选项和 manifest 状态。

## 4. 从 Project 到一份可分析的 trace

APA 的基本工作流是：

1. 创建或打开 Project；
2. 点击 Record Trace；
3. 选择 Device 与 launch mode；
4. 配置 start/end trigger 和数据源；
5. 执行固定的用户操作；
6. 手工 Stop，或等待 Duration 到期；
7. APA 拉取 trace 并自动打开 Trace View。

Project 适合保存同一问题的多份 trace。文件放在同一 Project 不代表采集条件一致；每次录制仍要记录设备、build fingerprint（系统构建的唯一标识）、GPU driver、App 版本、刷新率、温度、亮度、电量和测试脚本。

### 4.1 Launch mode 与 trigger

launch mode 决定 APA 是否负责启动 App，trigger 决定录制何时开始或结束。Configure a Recording 提供两种 launch mode：

- Launch app and record：APA 启动目标 App；
- Record a running app：对已经运行的进程录制，Application 相关选项不可用，start trigger 只能选择 Manual。

启动触发器包括 Manual、On Startup、On Startup with Delay；结束触发器包括 Manual 和 Duration。启动问题应使用 On Startup，并确认录制开始覆盖进程创建和首帧。稳态（启动和预热影响已经消退）滑动或游戏场景，可以先准备数据、账号和页面，再用 Manual 进入目标窗口。

### 4.2 默认配置与自定义 `TraceConfig`

System Profiler 默认采集一组 CPU/GPU 指标，也允许在界面中勾选需要的数据。官方建议一分钟以上的 trace 减少 data source；一分钟以内可以选择更多数据，但“影响较小”不等于无扰动，仍要用相同配置做对照。

Use custom trace configuration 会把界面当前设置自动展开成 Perfetto `TraceConfig` textproto（Protocol Buffers 的文本格式）。可以在此基础上添加 Android 17 支持的数据源。自定义配置要同时检查：

- data source 在目标设备上是否注册；
- buffer 大小与 fill policy（buffer 满后的覆盖或停止策略）是否适合录制时长；
- ftrace event（内核事件）、atrace category（Android 用户态追踪类别）和 App marker 是否真的产生数据；
- 采样频率是否改变被测负载；
- trace 是否因 buffer 覆盖、flush（把暂存数据写出）或 stop 时机而丢掉目标窗口。

截至 2026 年 8 月 13 日，APA 公开文档没有给出 `/system/etc/perfetto-configs/apa-config.textproto`、`--custom-cpu-freq`、`--custom-gpu` 或 `adb shell apa` 这些入口。本文的 APA 操作步骤以独立桌面 GUI 为准；2026 年 5 月发布文还描述了 Android Studio 集成，但两种界面都不是命令行采集接口。需要脚本化采集时，应使用 Perfetto CLI、Macrobenchmark（Jetpack 的可重复性能测试框架）或相应测试工具。

## 5. Vulkan Layers：能力与扰动

APA 可在录制时注入 Vulkan layers，也就是加载能拦截 Vulkan API 调用并写入额外调试数据的模块。当前文档列出三类选项。

### 5.1 CPU Timing

CPU Timing 把 Vulkan API 调用耗时显示为调用线程上的 slice（带开始时间和持续时间的事件）。`vkCmdDraw` 一类高频函数会被有意排除，因为逐次追踪会造成明显开销并扭曲结果。该轨道适合找 API 提交侧的长调用，不能代表 GPU 执行时间。

### 5.2 Render Pass Debug Names

Render Pass Debug Names 目前标为 Experimental。它把代码设置的 Vulkan render pass debug annotation（调试标注）带入 Trace View，便于把 GPU 工作对应到 Shadow、Lighting、PostProcess 等引擎阶段。若名字缺失，应检查 App 是否 debuggable、对象是否设置 debug name、录制选项是否开启，以及驱动是否提供所需数据。

### 5.3 Screenshots

Screenshots 也处于 Experimental。它依赖拦截标准 `VK_KHR_swapchain`（管理待显示图像队列的 Vulkan 扩展）；使用其他 present（把图像提交到显示路径）机制时不会得到截图。截图可以帮助辨认捕获时对应的应用画面内容，但不能证明该画面已经交给显示端，也不能用图片时间戳代替 present fence 或 FrameTimeline。

启用 Vulkan layer 会改变运行环境。需要对外报告性能数字时，应另录一份未启用 layer 的基线 trace；诊断 trace 用来查找可疑阶段，基线 trace 用来确认修改后的真实收益。

## 6. Trace View 中能看到什么

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

## 7. 浏览、对照与 SQL

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

结果表示线程已经可运行、但在该区间内没有执行。它可能来自 CPU 竞争、优先级、调度约束或更高优先级工作，不能仅凭一行结果断言根因。下一步应回到对应时间窗，检查 CPU Scheduling、wakeup（线程唤醒事件）、当前运行线程、频率与相关 slice。更多查询模式见 13.9 的 Perfetto SQL 查询手册。

官方还提供 `perfetto-sql` 与 `perfetto-trace-analysis` 两个 skill，供 AI agent 生成查询或给出分析起点。使用前需要安装对应 skill；生成结果仍要检查当前 trace 的表、字段、单位和进程范围，AI 给出的自然语言解释不能替代 trace 证据。

## 8. 三类常用分析

### 8.1 帧耗时

分析一帧时，先区分 CPU total time（两次帧提交之间包含等待的总时长）、CPU active time（CPU 实际运行该 App 代码的时长）、GPU time 与最终 present 结果。

- Vulkan 场景可用相邻 `vkQueuePresentKHR` 之间的区间估算 CPU total frame time；其中包含等待 GPU 或 buffer 的时间；
- CPU active time 要统计该帧窗口内主线程、render thread 和 worker（工作线程）的 Running slice，不能只量一条线程；
- GPU slice 可用时，它比 counter 更适合估算 GPU frame time；
- GPU slice 缺失时，可以用 GPU utilization（利用率）、instruction（指令活动）或 queue counter 的周期模式估算边界，但精度较低；
- 一帧可能包含多次 Vulkan submission，应使用 Vulkan Events 与 `submission_id` 关联同一帧的 GPU 工作；
- Actual Timeline 的 jank slice（卡顿帧区间）、SurfaceFlinger On Display 和 expected/actual present（预期/实际显示时间）用来确认用户是否晚看到这一帧。

CPU submit 返回、GPU producer completion fence、SurfaceFlinger latch、display present fence 和 layer release fence 是不同的时序边界。completion fence 表示 producer 已完成 buffer 写入，consumer 可以安全读取；latch 表示 SurfaceFlinger 选中该 buffer 参与本轮合成；present fence 是本轮 display present 的系统时间锚点；release fence 则通知 producer 何时可以复用旧 buffer。APA 中 `vkQueuePresentKHR` 或 GPU queue slice 结束都不能单独证明一帧已经显示；应沿 submission ID、buffer/layer、fence 与 FrameTimeline 对齐。队列中存在多帧 in flight（已提交、尚未显示）时，FPS 稳定也可能伴随较高的输入到显示延迟。

### 8.2 GPU 内存效率与带宽

APA 官方的 Memory Efficiency 分析主要讨论 GPU counter 与 memory bandwidth（单位时间内通过内存总线的数据量），不等同于 Java heap allocation（堆对象分配）或泄漏分析。建议按以下顺序读取：

1. 用 counter 周期确定单帧窗口，避免把独立采集的 GPU slice 边界直接套到 counter；
2. 查看总 read/write bandwidth；
3. 再区分 texture（纹理）、vertex（顶点）、cache（缓存）与 fetch stall（取数等待）；
4. 将峰值与 render pass、GPU queue 和帧耗时对齐；
5. 到 AGI Frame Profiler 或引擎资源统计中检查纹理格式、mipmap（多级缩小纹理）、vertex layout（顶点数据内存布局）、render target（渲染输出图像）和 draw submission（绘制提交批次）。

Adreno 与 Mali 的 counter 名称和计算方法不同，阈值也依赖 GPU、总线、分辨率与工作负载。团队看板应绑定 GPU 型号、driver、counter 名称和单位，不应把一台设备的数值直接推广到其他 SoC（System on Chip，片上系统）。

Java/Kotlin 对象增长、GC（垃圾回收）与调用栈交给 Android Studio Memory Profiler、heap dump（堆转储）或 LeakCanary；native heap 可结合 `heapprofd`（Perfetto 原生堆采样器）。APA 提供的是系统时间线上下文。

### 8.3 线程调度

线程调度分析要区分三类时间：

- Running：线程占用 CPU；
- Runnable：线程具备运行条件，但尚未获得 CPU；
- Sleeping/Blocked：线程等待 timer（定时器）、futex（用户态同步原语的内核等待）、Binder IPC、I/O 或其他依赖。

长 Running 指向工作量，长 Runnable 指向调度延迟，长 Blocked 指向依赖等待。这三类只能确定排查方向。若线程频繁迁核或落在不合适的 CPU 上，先检查线程优先级、任务划分、负载和 ADPF（Android Dynamic Performance Framework）的 Performance Hint。官方 APA 调度指南建议使用 Performance Hint API 向系统表达性能需求，不建议把手工 affinity（把线程绑定到指定 CPU）作为通用修复。

Android 17 的调度 tracepoint 来自固定内核锚点 `android17-6.18-2026-06_r6`。APA 展示的 `sched_switch`、`sched_wakeup` 反映内核调度事实；CPU topology（核心层级与大小核布局）、uclamp（调度利用率上下限）、cpuset（任务可使用的 CPU 集合）、thermal（温控限制）和厂商 scheduler 策略仍要结合设备源码与 Perfetto 轨道解释。

## 9. APA 与其它工具如何分工

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

## 10. Android 17 平台边界

在 `android-17.0.0_r1` 上评审 APA 结论时，分三层记录版本：

- APA 桌面版本：决定 GUI、默认配置、Vulkan layer、SQL 与文件管理能力；
- Android build fingerprint / `android-17.0.0_r1`：决定 framework trace event、Perfetto producer、FrameTimeline 和系统服务行为；
- kernel `android17-6.18-2026-06_r6` 与 vendor driver：决定 scheduler/ftrace 语义、GPU counter、render stage 和设备能力。

APA 安装包不属于 `android-17.0.0_r1` framework 源码。平台 tag 中找不到 APA 可执行文件，不能据此否定这个桌面产品；反过来，APA 文档出现一项 UI 能力，也不能证明所有 Android 17 设备都有对应 data source。

## 11. 一轮可复查的 APA 实验

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

## 参考资料

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
