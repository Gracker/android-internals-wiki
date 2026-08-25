---
title: Perfetto UI、状态轨道与版本边界
chapter: '13.2'
section: '13.2'
section_title: Perfetto View 解读
status: finalized
applicable_versions: Android 9 (API 28) - Android 17 (API 37)
last_verified: '2026-08-13'
last_verified_against: AOSP android-17.0.0_r1（external/perfetto ece66975738007dd0978b911d8a2077e49b8f31e、frameworks/native ae266dcb706d083868578cfedce381ef44488a07）+ android17-6.18-2026-06_r6 + Perfetto UI/Trace Processor v57.2 + 2026-08-13 Perfetto/Android 官方文档
confidence: high
sources:
- type: internal-reference
  path: /Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/DeepResearch/当 Perfetto 显示 Running 时,Android 程序到底在做什么? .md
  role: Running、Runnable 与线程状态解释边界
- type: internal-reference
  path: /Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/DeepResearch/2026-07-13-android17-surfaceflinger-perfetto-trace.md
  role: Android 17 SurfaceFlinger trace 入口与调用阶段
- type: internal-reference
  path: /Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/DeepResearch/2026-05-06-binder-transaction-trace-perfetto-analysis.md
  role: Binder transaction、线程状态与跨进程关联
- type: official
  path: https://perfetto.dev/docs/visualization/perfetto-ui
  role: 当前 UI 的加载、导航、选区、过滤、Pin 与快捷键
- type: official
  path: https://perfetto.dev/docs/visualization/ui-automation
  role: 命令面板、启动命令与宏
- type: official
  path: https://perfetto.dev/docs/analysis/debug-tracks
  role: SQL 模式与 Debug Track
- type: official
  path: https://perfetto.dev/docs/data-sources/cpu-scheduling
  role: CPU 调度轨道、waker 与 end_state 定义
- type: official
  path: https://perfetto.dev/docs/data-sources/frametimeline
  role: FrameTimeline Expected/Actual、颜色、字段与 Flow
- type: official
  path: https://perfetto.dev/docs/instrumentation/track-events
  role: Flow Event 与 Counter 的数据语义
- type: official
  path: https://perfetto.dev/docs/analysis/sql-tables
  role: slice、sched 与 thread_state 表字段
- type: official
  path: https://perfetto.dev/docs/analysis/stdlib-docs
  role: slices.self_dur 与 Android Binder 标准库
- type: official
  path: https://perfetto.dev/docs/analysis/common-queries
  role: Uninterruptible Sleep 与 blocked_function 分析
- type: official
  path: https://perfetto.dev/docs/visualization/large-traces
  role: 大型 trace 的本机 Trace Processor 后端
- type: official
  path: https://developer.android.com/studio/profile/cpu-profiler
  role: Android Studio System Trace 的系统级视图
- type: upstream
  path: https://github.com/google/perfetto/blob/main/ui/src/components/colorizer.ts
  role: 上游 UI 配色实现入口；具体颜色不作为稳定分析接口
- type: aosp
  path: https://android.googlesource.com/platform/external/perfetto/+/refs/tags/android-17.0.0_r1/src/trace_processor/types/task_state.cc
  role: Android 17 Trace Processor 的内核 task state 解码
- type: aosp
  path: https://android.googlesource.com/platform/external/perfetto/+/refs/tags/android-17.0.0_r1/src/trace_processor/perfetto_sql/stdlib/slices/self_dur.sql
  role: Android 17 slice_self_dur 实现
- type: aosp
  path: https://android.googlesource.com/platform/external/perfetto/+/refs/tags/android-17.0.0_r1/src/trace_processor/perfetto_sql/stdlib/android/binder.sql
  role: Android 17 Binder transaction 关联
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/services/surfaceflinger/Scheduler/Scheduler.cpp
  role: Android 17 onFrameSignal、commit 与 composite 调度
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/services/surfaceflinger/SurfaceFlinger.cpp
  role: Android 17 SurfaceFlinger commit/composite 实现
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/services/surfaceflinger/CompositionEngine/src/Output.cpp
  role: Android 17 Output present 与 release 阶段
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/services/surfaceflinger/Scheduler/FrameTimeline.cpp
  role: Android 17 FrameTimeline 分类与 trace 输出
- type: kernel
  path: https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/include/linux/sched.h
  role: Android 17 common kernel 线程状态位定义
- type: official
  path: https://github.com/google/perfetto/releases/tag/v57.1
- type: aosp
  path: protos/perfetto/trace/track_event/track_event.proto (v57.1 tag)
- type: aosp
  path: protos/perfetto/trace/track_event/state_descriptor.proto (v57.1 tag)
tags:
- android
- perfetto
- trace-view
- frame-timeline
- binder
- thread-state
- cpu-scheduling
- Perfetto
- TrackEvent
- 状态追踪
- 版本边界
related_chapters:
- '13.1'
- '2.5'
- '14.2'
- '14.3'
- '13.7'
- '13.11'
- '13.12'
- '13.6'
pipeline_stage: finalized
task6_state: reviewed
task9_state: reviewed
task2b_state: fixed
last_consolidated_at: '2026-08-24'
consolidated_from:
- src/part3-tools/ch13-perfetto/03-perfetto-view.md
- src/part3-tools/ch13-perfetto/21-perfetto-v57-state-tracks.md
---

# Perfetto UI、状态轨道与版本边界

Perfetto UI 用 track、slice、counter 和 flow 展示时间关系；状态轨道把线程、进程或系统组件在某段时间内的离散状态直接呈现。版本变化会调整轨道命名和数据源，不能只凭颜色判断。

## 轨道、切片、计数器与因果连接

### 读图顺序比轨道数量更重要

Perfetto UI 把多个 data source 的事件放在同一时间轴上；data source 是产生某类 trace 数据的采集组件。UI 无法补回缺失的调度事件、FrameTimeline、Binder 或应用标记，也不会自动给出因果关系。读图时要把“轨道上发生了什么”和“为什么发生”分开。

一轮可靠分析按下面的顺序推进：

1. 在 Info/Stats 中确认 trace 时间范围、目标进程和数据完整性；Stats 会列出解析错误和丢包等诊断信息。
2. 用 Area Selection 圈出复现动作对应的时间窗，避免在整份 trace 里无目标地浏览。
3. 用 FrameTimeline、启动标记、ANR、输入事件或业务 Slice 确定异常事件。
4. 回到相关线程，区分 Running、Runnable、Sleeping 和 Uninterruptible Sleep。
5. 沿 Binder、Flow、waker 或帧 token 检查跨线程、跨进程和显示下游。
6. 需要批量比较时，把 UI 观察写成 PerfettoSQL。

平台结论固定到 Android 17 / API 37 / `android-17.0.0_r1`，内核状态固定到 `android17-6.18-2026-06_r6`。`ui.perfetto.dev` 和主机 Trace Processor 独立更新；本文的界面文字、命令和轨道布局按 2026-08-13 的稳定版 v57.2 与官方文档复核。

### 打开并整理 Trace

#### 加载方式与大文件边界

[Perfetto UI](https://ui.perfetto.dev/) 可以通过侧边栏的 “Open trace file” 或拖放加载本地 trace。一次选择多个文件时，当前 UI 会进入合并配置流程，把它们放到共享时间轴；合并前要确认各文件的时钟来源和对齐依据。

浏览器能否顺利处理大文件取决于 trace 内容、主机内存、浏览器限制和查询复杂度，不能用一个固定体积判断。加载或交互开始受限时，可以运行 `./trace_processor server http <trace>`，让本机原生 Trace Processor 作为 UI 后端；也可以直接用 `trace_processor_shell` 查询，具体流程见 §13.1。把二进制 trace 全量转成文本通常会扩大体积，也会失去 UI 的索引优势，不适合作为大文件的默认方案。

#### 时间轴、选择与详情抽屉

当前 UI 的常用操作如下：

| 目的 | 操作 | 结果 |
| --- | --- | --- |
| 缩放与平移 | `W` / `S`、`A` / `D`；也可用 `Ctrl` + 滚轮和 `Shift` + 拖动 | 改变可见时间窗 |
| 聚焦事件 | 选中事件后按 `F`；再按一次 `F` | 居中，再把事件适配到视口 |
| 相邻事件 | `,` / `.` | 在同一轨道切换前一个或后一个事件 |
| 时间选区 | 在时间轴或轨道区域拖动 | 创建 Area Selection，其中包含起止时间和被选轨道集合 |
| 事件转选区 | 选中事件后按 `R` | 用事件边界创建 Area Selection |
| 详情抽屉 | `Q` | 显示或隐藏 Tab Drawer（选中事件、查询结果等详情所在的底部面板） |
| 命令面板 | `Ctrl+Shift+P`；macOS 用 `Cmd+Shift+P` | 搜索并执行 UI 命令 |
| 当前快捷键 | `?` | 查看该 UI 构建实际注册的快捷键 |

Area Selection 不只有起止时间，还包含所选轨道。修改 track shell（轨道左侧的名称和控制区域）上的勾选项会改变统计范围；分享截图或结论时，应把选区边界和轨道集合一起说明。

#### 找轨道、过滤和 Pin

长 trace 的效率来自减少同时可见的轨道：

- Track Finder 按名称模糊查找轨道。
- Timeline 工具栏的过滤器可按轨道名、进程或线程缩小显示范围；清除过滤后数据仍在。
- 轨道外壳的 Pin 按钮把轨道移到工作区顶部。

分析一帧时，常用组合是 App 主线程、RenderThread、FrameTimeline、`surfaceflinger` 主线程和相关 CPU。分析同步 Binder 时，把客户端线程与服务端 Binder 线程一起 Pin。Pin 只改变显示位置，不改变数据或时间对齐。

Omnibox 是页面顶部的统一搜索和命令输入框，输入 `:` 可以进入 SQL 模式。结果能否生成 Debug Track 取决于列的语义：Slice Track 至少要选择名称、非空时间戳和 duration 列，Counter Track 至少要选择时间戳和数值列；列名可以在创建界面中映射，不必固定写成 `name`、`ts`、`dur` 或 `value`。复杂查询留到 §13.7，这里把它作为“将查询结果放回时间轴”的入口。

### 轨道描述的是哪一层

#### CPU Scheduling、Frequency 与 Idle

CPU Scheduling 轨道来自内核调度事件。每个 Slice 表示某个线程在一颗 CPU 上运行的区间；详情中的 `priority`、线程身份和 `end_state` 可以帮助解释这次运行如何结束，其中 `end_state` 是线程被切出 CPU 后进入的调度状态。该轨道回答“哪条线程在何时占用哪颗 CPU”，不回答线程执行了哪一行代码。代码热点还需要应用 Slice、采样调用栈或方法跟踪。

CPU Frequency 轨道来自设备提供的频率事件。它能显示记录到的频率变化，但频率值不能单独证明某段代码变慢：CPU 微架构、单核处理能力、热限制、空闲状态、调度放置和内存等待都会影响完成时间。判断线程迁移到另一颗 CPU 是否有害，还要结合 Runnable 延迟、各 CPU 的并发负载和设备拓扑，不能要求主线程始终固定在某颗“大核”。

CPU Idle 轨道描述 CPU 的空闲状态。线程处于 Sleeping 或 D 状态时，本来就没有资格运行；此时看到部分 CPU idle 并不构成调度异常。只有线程已 Runnable，并且在 affinity（线程允许运行的 CPU 集合）和 cpuset（系统为一组任务限定的 CPU 集合）等约束下有可用 CPU，却长期没有进入 Running，才需要继续检查优先级、系统负载和调度策略。

#### 进程、线程、Slice 与线程状态

进程分组把同一进程的线程、Counter 和其他轨道放在一起。线程轨道上常同时出现两类数据：

- **Slice**：应用或平台标记的命名区间，例如 `Choreographer#doFrame`、`performTraversals`、`DrawFrame`。Slice 说明某个逻辑区间尚未结束，不保证线程全程占用 CPU。
- **Thread State**：Trace Processor 根据 `sched_switch`、`sched_waking` 等事件重建的调度状态。它说明线程在 CPU 上运行、等待 CPU，或等待某个唤醒条件。

App 主线程负责 Looper 消息、输入分发、生命周期和 View/Compose 工作；`Choreographer#doFrame` 是传统 View/HWUI 帧的重要入口。RenderThread 负责 HWUI 渲染工作的记录、准备与图形提交，其中可能包含 CPU 执行、GPU 工作排队和 fence（表示前序图形工作何时完成的同步对象）等待。名称相同的 Slice 在不同 Android 版本、渲染后端和厂商实现中可能覆盖不同子阶段，要结合子 Slice 与源码核对。

Binder 线程名能帮助定位服务端执行线程，但 Binder transaction 本身不保证包含 Java 方法名。方法名是否可见取决于平台或业务是否在服务端路径添加了 ATrace / Track Event 标记。

#### Counter Track

Counter 由一组“时间戳 + 数值”样本组成，例如频率、RSS（进程驻留在物理内存中的页量）、堆大小、BufferQueue 积压量或自定义队列深度。UI 会把离散样本画成折线或阶梯图；Counter 的来源、单位和采样间隔由数据源决定，图形上升不能直接证明泄漏或性能退化。

内存 Counter 持续上升时，要区分采样区间、GC、缓存上限、映射文件、共享内存和进程生命周期。GPU Counter 是否存在、含义是什么，也受 GPU 数据源和厂商支持限制。报告中应记录 Counter 名称、单位、数据源和比较窗口。

### Slice 详情：三种时间不能混用

#### Wall Duration

`slice.dur` 是 Slice 起点到终点的墙上时长，对应时间轴上的宽度。线程在这段时间内可能运行、等待 CPU、休眠或阻塞。长 Slice 只证明命名区间长，不能直接判定为 CPU 计算重。

#### Thread Duration / CPU 时间

`slice.thread_dur` 是 Slice 消耗的线程时间，只有 Track Event 开启线程时间采集时才会填充。Android ATrace 产生的普通 Slice 往往没有这个字段。UI 未显示 Thread Duration 时，缺失值表示没有这份数据，不能按 0 处理。

需要计算某个线程 Slice 内的 on-CPU 时间时，应将该 Slice 的半开区间 `[ts, ts + dur)` 与 `thread_state.state = 'Running'` 求交；半开表示包含起点、不包含终点。只有调度数据覆盖完整时，墙上时间才能按 Running、Runnable、Sleeping、D 等互斥状态分解；trace 边界、丢包和未知区间必须单列。

#### Self Duration

Self Duration 是一个轨道嵌套概念：父 Slice 的墙上区间扣除子 Slice 覆盖区间。它适合判断时间落在哪一层标记中，不等于函数自身的 CPU 时间，也不会自动扣除另一个线程上的异步工作。

下面的查询用于比较 `doFrame` 的墙上时长、自身墙上时长和可选线程时长。

```sql
INCLUDE PERFETTO MODULE slices.self_dur;

SELECT
  s.id,
  s.name,
  s.dur / 1e6 AS wall_ms,
  sd.self_dur / 1e6 AS self_wall_ms,
  s.thread_dur / 1e6 AS thread_ms
FROM slice AS s
JOIN slice_self_dur AS sd USING (id)
WHERE s.name GLOB 'Choreographer#doFrame*'
ORDER BY s.dur DESC
LIMIT 20;
```

`thread_ms` 为 `NULL` 表示该 Slice 没有线程时间，不能据此推断 CPU 消耗。`self_wall_ms` 只扣除同一嵌套栈里的子 Slice；判断等待原因仍要查询 `thread_state`。

### 线程状态与颜色编码

#### 状态值是证据，颜色只是导航

Android 17 Trace Processor 按内核 `prev_state` 解码调度状态；`android17-6.18-2026-06_r6/include/linux/sched.h` 定义了 `TASK_RUNNING`、`TASK_INTERRUPTIBLE`、`TASK_UNINTERRUPTIBLE` 等状态位。UI 颜色帮助快速浏览，但主题、轨道类型和 UI 版本可能调整配色。结论应写状态名或 SQL 值，不能只写“绿色段”“橙色段”。

| UI / SQL 状态 | 内核或处理器含义 | 可以确认 | 仍需补证据 |
| --- | --- | --- | --- |
| `Running` | 线程正在某颗 CPU 上运行 | 该区间获得了 CPU | 执行哪段代码、是否受缓存或内存延迟影响 |
| `R` / Runnable | 已具备运行资格，等待调度 | 该区间没有获得 CPU | 是负载、优先级、affinity、cpuset 还是调度策略 |
| `R+` | Runnable，并由抢占结束上一段运行 | 线程被抢占后等待 | 抢占者、优先级和 CPU 负载 |
| `S` / Sleeping | 可中断睡眠，等待显式唤醒 | 线程不在运行队列 | Binder、futex（用户态锁进入内核等待时使用的机制）、条件变量、定时器或其他等待对象 |
| `D` / Uninterruptible Sleep | 不可中断睡眠 | 线程等待内核条件 | 是否为 I/O、具体 `blocked_function`、设备驱动或内存回收 |

当前稳定版 UI 通常用不同深浅的绿色区分 Running 与 Runnable，Sleeping/Idle 显示为低对比度色块，D 状态则使用暖色。具体色值会随主题和 UI 实现变化，不属于稳定的数据接口。FrameTimeline 的绿、浅绿、红、黄、蓝是另一套帧结果编码，也不能套用到线程状态。分析结论应记录状态值和详情字段。

#### D 状态不等于磁盘 I/O

`TASK_UNINTERRUPTIBLE` 表示等待条件不会被普通信号打断，磁盘 I/O 只是常见来源之一。驱动等待、页回收、文件系统、块设备和其他内核等待都可能产生 D 状态。

采集了 `sched/sched_blocked_reason` 时，`thread_state` 可以提供 `blocked_function`，部分 trace 还会给出 `io_wait`。缺少这些字段时，只能写“Uninterruptible Sleep，原因未由本次 trace 识别”，不能直接归为磁盘瓶颈。

#### 红色锁竞争标记不是调度状态

`Lock contention on a monitor lock` 等红色 Slice 来自 ART/平台锁竞争埋点；monitor lock 是 Java 对象监视器对应的互斥锁。等待线程的内核状态在同一时间窗内通常是 Sleeping，也可能随实现变化。红色表示 trace 提供了更具体的锁证据，不是 Linux `thread_state` 新增了一个 Blocked 状态。

详情面板若提供 owner、blocking thread 或关联跳转，应切到持锁线程检查：

1. 持锁线程是否在 Running。
2. 持锁线程是否又在等 Binder、I/O 或另一把锁。
3. 锁持有区间是否覆盖昂贵操作。
4. 这段等待是否位于当前帧、启动或 ANR 的时间窗内。

红色 Slice 本身不能证明优先级反转。优先级反转是高优先级线程等待低优先级持锁线程，而持锁线程又被其他工作延迟的情况；还要同时确认等待者、持锁者、抢占者及其优先级和调度状态。

#### Waker 的使用边界

采集 `sched_waking` 或相关 wakeup 事件后，线程状态详情可以关联 waker，也就是发起本次唤醒的线程。waker 不一定是最初的业务事件源，被唤醒线程也不会因此立刻获得 CPU。从 wakeup 到 Running 的区间才是本次唤醒后的调度等待时间。

跨 CPU 唤醒时，`sched_waking` 记录在发起唤醒的一侧，`sched_wakeup` 的记录位置受唤醒路径影响。普通延迟分析优先保证 `sched_waking` 存在；若要区分 IPI（Inter-Processor Interrupt，CPU 核之间发送的中断）和调度器唤醒路径的各段耗时，再同时检查更底层事件。

### Flow Events 与跨进程关联

Flow 是 trace 显式记录的跨 track 关联关系，用箭头连接不同轨道上的相关事件。选中带 Flow 的事件后，UI 会突出相关箭头；未选中时可能为了可读性减少显示。箭头只表达“trace 数据声明两者相关”，不能自动证明同步阻塞或单一因果。

#### Binder transaction

Binder 分析依赖相应的驱动 tracepoint 和 Trace Processor 解析。同步调用通常可以关联客户端 transaction、服务端 transaction 和 reply；oneway 是单向异步调用，没有同步 reply，客户端也不等待服务端完成。嵌套 Binder、回调和线程池排队会让路径分叉，第一条箭头不能代表完整调用树。

读一个同步 Binder 调用时，依次检查：

1. 客户端 transaction Slice 的墙上时长和线程状态。
2. 服务端 Binder 线程何时开始处理，transaction 到开始执行之间是否存在排队时间。
3. 服务端 Slice 内是 Running、锁等待、D 状态还是再次发起 Binder。
4. reply 何时返回，客户端从唤醒到 Running 又等了多久。

Android 17 的 `stdlib/android/binder.sql` 会把 Binder transaction 与 reply、线程和进程关联起来。UI 跳转适合看单个案例，批量统计应使用该标准库或 §13.7 的查询模板。

#### FrameTimeline Flow

选中 App 的 Actual Timeline Slice 时，Perfetto 可以通过 surface frame token（标识应用提交帧的关联键）找到对应的 SurfaceFlinger display frame；选中 display frame 时，也可以显示这次合成包含的多个应用 frame。这个 Flow 表达帧的消费关系，比只按时间重叠匹配更可靠。

Flow 与 BufferQueue frame number 是不同的标识，也不能替代 acquire、present 和 release fence 提供的同步证据。SurfaceView 等独立 Surface 路径还受 FrameTimeline 覆盖范围限制，具体边界见 §13.13 和 §15。

### FrameTimeline：从异常帧进入

FrameTimeline 从 Android 12 / API 31 起可用。Android 9-11 没有 Expected / Actual 主轨道，应从 `Choreographer#doFrame`、RenderThread、调度事件和 SurfaceFlinger 时间窗建立关联。

Expected Timeline 表示调度器为这一帧安排的预计时间窗。App Actual Timeline 从 `Choreographer#doFrame` 或 NDK Choreographer 回调开始，结束点取 GPU 完成时间与帧提交给 SurfaceFlinger 的 post time 两者中较晚者。SurfaceFlinger Actual Timeline 覆盖合成到屏幕更新的结果。Actual Slice 的 `dur` 是这套 FrameTimeline 定义下的墙上区间，不代表主线程 CPU 时间，也不能概括所有显示路径的端到端延迟。

选中 Actual Slice 后，按下面的字段读：

- `Present Type`：Early、On-time 或 Late。
- `On time finish`：生产者是否在预计 deadline 前完成工作。
- `Jank Type`：平台分类，可包含 App、SurfaceFlinger、Display HAL（显示硬件抽象接口）、预测和调度原因。
- `Prediction Type`：预测是否有效或已经过期。
- `GPU Composition`：该帧是否使用 GPU 合成。
- `Layer Name`：区分同一进程更新的不同 Surface。
- `Is Buffer`：区分 buffer frame 与非 buffer 动画。

#### FrameTimeline 的颜色

官方 UI 为 FrameTimeline 定义了独立颜色语义：

| 颜色 | 含义 |
| --- | --- |
| 绿色 | 未观察到 jank 的帧 |
| 浅绿色 | 帧率可能平稳，但帧晚呈现并增加输入延迟 |
| 红色 | 该 Slice 所属进程被归因为 jank 来源 |
| 黄色 | App 帧发生 jank，但归因在 SurfaceFlinger |
| 蓝色 | Dropped frame |

颜色用于寻找候选帧，报告应记录 `present_type`、`on_time_finish`、`jank_type`、layer 和 token。`BufferStuffing` 表示应用在旧 buffer 尚未呈现时持续提交新 buffer，导致队列积压并增加延迟。Android 17 `FrameTimeline.cpp` 把它、`SurfaceFlingerStuffing` 等状态与 deadline jank 分开计算，不能把所有非绿色帧合并成“App Deadline Missed”。

官方文档仍提示 SurfaceView 不在 FrameTimeline 的完整支持范围内。Camera、视频、游戏和跨进程嵌入常有独立 Producer / Surface / layer，宿主窗口的帧 token 不能代替这些路径的逐帧证据。

### Android 17 SurfaceFlinger 轨道

Android 17 的主循环由 `Scheduler::onFrameSignal()` 组织。`Scheduler.cpp` 在同一帧信号中调用 `compositor.commit()` 处理事务、layer 状态和本帧准备工作；满足合成条件后，再调用 `compositor.composite()` 组织合成。对应实现位于 `SurfaceFlinger::commit()` 和 `SurfaceFlinger::composite()`。显示输出阶段继续进入 CompositionEngine 的 `Output::present()` 与 `presentFrameAndReleaseLayers()`。

版本演进要保留，因为旧 trace 的 Slice 名称不同：

| 平台 | SurfaceFlinger 观察入口 |
| --- | --- |
| Android 12 / 12L | 常见 `onMessageReceived`、`onMessageInvalidate`、`onMessageRefresh`、`REFRESH` |
| Android 13-17 | 按 `onFrameSignal`、`commit`、`composite` 以及可见的 present 子阶段阅读 |

Slice 名称受埋点和版本影响，不能要求每份 Android 17 trace 都出现一条字面为 `presentFrameAndReleaseLayers` 的 Slice。源码调用关系用于解释已出现的阶段，不用于虚构 trace 中没有的数据。

`composite` 变长也不能直接归为 GPU Client Composition。要同时找到 RenderEngine/`drawLayers` 等 GPU 合成证据、HWC（Hardware Composer，硬件显示合成器）的 composition type、layer 特征和 fence 时间。事务处理变重、latch（选定本轮要合成的 buffer）等待、HWC validate/present 或显示提交都可能拉长 SurfaceFlinger 一帧。

### 日志与原始事件

只有采集配置包含 Android log 数据源时，UI 才能显示抓取窗口内的日志。只有保留相应 ftrace event 时，原始事件表才有对应记录。看不到 Android Logs 或 Ftrace Events 时，应回查配置与数据完整性，不能把“UI 没有轨道”解释为“系统没有发生事件”。

日志适合标记业务阶段和错误点，时间线用于验证线程、调度与依赖关系。日志时间戳、trace 时钟和跨文件合并可能使用不同时间基准；要先确认时钟转换和对齐误差，再做毫秒级因果判断。

### 与 Android Studio Profiler 的关系

Android Studio 的 System Trace 也是系统级视图，能够展示 CPU 核心、线程、显示、内存和部分功耗数据。把它描述成“只能看单个 App、看不到 SurfaceFlinger 或调度”已经不符合当前工具。

| 工具 | 适合的工作 |
| --- | --- |
| Android Studio System Trace | 在 IDE 内录制、围绕目标 App 查看线程和显示问题、结合工程工作流 |
| Perfetto UI | 打开多种 trace、完整时间轴导航、PerfettoSQL、Debug Track、宏和跨进程系统分析 |
| Android Studio Method / Function Trace | 查看方法或函数调用树、按调用栈随时间展开的 Flame Chart，以及从调用者或被调用者方向聚合的 Top Down/Bottom Up 视图 |
| Simpleperf / `linux.perf` | 调用栈采样、热点和 CPU profile |

Android Studio 的 System Trace 与 Java Method Trace 是不同录制类型，不能用统一的 `.trace` 口径描述。复杂系统问题可以从 Android Studio 导出 System Trace，再放到 Perfetto UI 做 SQL 与跨进程分析。

### 一轮掉帧分析怎么走

拿到滑动卡顿 trace 后，可以按这条主线检查：

1. 在 Info / Stats 确认复现窗口、目标进程、FrameTimeline 与调度数据存在，相关丢包不影响结论。
2. Android 12-17 从 App Actual Timeline 选择候选帧；Android 9-11 从 `doFrame`、RenderThread 与 SurfaceFlinger 的共同时间窗开始。
3. 记录 `Jank Type`、`Present Type`、`On time finish`、layer 与 token，不只记录颜色。
4. 回到主线程和 RenderThread，把长 Slice 与 Running、Runnable、S、D 状态求交。
5. Running 长时结合子 Slice 或调用栈找 CPU 工作；Runnable 长时检查全机 CPU、优先级和放置约束；S 状态沿 Binder、锁、条件变量或 waker；D 状态检查 `blocked_function` 与 `io_wait`。
6. 沿 FrameTimeline Flow 检查对应 display frame，再读 Android 17 的 `commit`、`composite` 和显示输出阶段。
7. Binder 或锁跨进程时，把客户端、服务端、持锁线程和 reply 放进同一选区。
8. 用 SQL 复核同类帧是否重复出现，避免用一个案例代表整段运行。

这套流程用于判断现有证据指向应用、调度、跨进程调用、合成还是显示末端。修复后仍要回到对应代码、配置和设备复现验证；FrameTimeline 的分类也不能替代源码与 fence 证据。

### Android 17 源码核对点

| 结论 | Android 17 / kernel 锚点 | 代码能证明什么 |
| --- | --- | --- |
| 调度状态 | `external/perfetto/.../task_state.cc` + kernel `include/linux/sched.h` | Trace Processor 如何解码 `prev_state`，内核如何定义 Running / Interruptible / Uninterruptible 状态位 |
| Self Duration | `external/perfetto/.../slices/self_dur.sql` | `slice_self_dur` 按子 Slice 覆盖区间计算自身墙上时长 |
| Binder 关联 | `external/perfetto/.../android/binder.sql` | transaction、reply、线程与进程的标准库关联 |
| SurfaceFlinger 帧循环 | `Scheduler/Scheduler.cpp:411-506` | `onFrameSignal()` 组织 `commit()` 与 `composite()` |
| SurfaceFlinger 阶段 | `SurfaceFlinger.cpp:2996,3330` | Android 17 的 `commit()` 与 `composite()` 实现入口 |
| 显示输出 | `CompositionEngine/src/Output.cpp:450-517,1726` | `Output::present()` 与 `presentFrameAndReleaseLayers()` 的调用边界 |
| 帧分类 | `Scheduler/FrameTimeline.cpp` | Android 17 jank bit、non-jank 状态、Dropped 与 trace 字段转换 |

源码证明平台具备这些实现，不保证厂商设备采集了对应数据。每份 trace 仍要检查 data source、事件、权限和丢包。


## 状态轨道的语义与版本差异

掌握通用 UI 对象后，状态轨道要继续核对状态枚举、生成数据源和 Perfetto 版本。相同视觉样式不保证语义相同。

> Android 平台内置组件、Perfetto SDK 与开发机上的分析器分别升级，不能用“Android 17 支持 Perfetto v57”笼统概括。本文的平台基线固定为 Android 17 / API 37 / `android-17.0.0_r1`；state track 的功能基线是 v57.1，工具补丁基线是 v57.2。

### 三条版本线

`android-17.0.0_r1` 的 `external/perfetto/CHANGELOG` 顶部记录了一个尚未进入完整上游版本的 Android `aflags` 补丁。`aflags` 是 Android 的功能开关机制，用于让平台代码按 flag 启用或停用行为。紧接着的完整上游版本是 **v54.0（2026-02-27）**；同一 Android 标签下的 `track_event.proto` 只定义到 `TYPE_COUNTER = 4`，没有 `TYPE_STATE`。

Perfetto **v57.1** 于 2026 年 7 月 2 日发布，引入 state track 等能力。**v57.2** 于 7 月 7 日发布，是截至 2026-08-13 最新的 v57 补丁版；它只修复 Trace Processor 解析内嵌 proto descriptor 时的兼容问题，其他 v57 功能仍以 v57.1 发布说明为准。state track、journald 采集和新版 Trace Processor/UI 都属于上游版本线，不会自动升级设备中的 `/system/bin/perfetto`、`traced`、`traced_probes` 或 Android Framework API。

| 对象 | 采用的版本 | 在哪里运行 | 能否直接提供 v57 状态轨道 |
|---|---|---|---|
| Android 平台 Perfetto | `android-17.0.0_r1`：v54.0 加平台补丁 | Android 17 设备 | 不能；平台 proto 没有 `TYPE_STATE` |
| Perfetto v57.2 C++ SDK / Trace Processor / UI | `v57.2` tag | 应用、测试工具或开发机 | C++ 生产与解析路径可用；C high-level 与 Java API 另有版本限制 |

这个拆分会影响方案选择：

- 只升级开发机分析器：可以读取新版 schema（trace 的字段与类型定义）和 PerfettoSQL 标准库，但不会补出设备未录制的数据。
- 想在 trace 中得到原生 `state` 表：producer（生产事件的一端）和 Trace Processor（解析事件的一端）都要具备 v57 state track 能力。
- 只能依赖 Android 17 系统内置组件：继续使用 slice、instant、counter 等 v54 能力。即使自行写出 `TYPE_STATE`，也不能假定平台自带工具能够解释。

### State track 的数据模型

#### Slice、counter 和 state 各自回答什么

| 轨道类型 | 数据形态 | 适合回答的问题 | 常见误用 |
|---|---|---|---|
| Slice | 开始、结束、可嵌套 | “这个操作执行了多久？” | 用大量首尾相接的 slice 模拟长期状态 |
| Counter | 时间戳加数值 | “这一刻的频率、字节数或队列深度是多少？” | 用整数枚举表达状态，却遗漏枚举表 |
| State | 时间戳加字符串状态，单轨道至多一个当前值 | “这个子系统在这段时间处于什么状态？” | 把同一时间可并存的多个活动塞进单条 state track |

state track 表达单值状态机：一条轨道在任一时刻最多有一个当前值，没有当前值时称为 idle。播放器的 `Buffering → Playing → Paused` 适合 state track。并行的下载任务、解码任务和渲染任务可以同时存在，应分别使用 slice 或多条轨道。

#### v57.1 在 trace 二进制格式中增加了什么

v57.1 的 `TrackEvent.Type` 增加 `TYPE_STATE = 5`，v57.2 延续同一 wire format（序列化后的二进制字段格式）。事件的 `track_uuid` 是轨道的 64 位稳定标识，必须指向带 `StateDescriptor` 的轨道；descriptor 是描述轨道类型和属性的元数据。`StateDescriptor` 在 v57.1/v57.2 中是空消息，只负责把轨道标记为 state track。

状态字符串的实际编码走 TrackEvent 的事件名路径，即 `name` 或经过 string interning（把重复字符串换成整数 ID）的 `name_iid`。v57.2 `track_event.proto` 的枚举注释仍写着 `state` 字段，但 schema 已将原字段号 51 标为 `reserved`，表示该编号被保留且不能重新用作普通字段；C++ `TRACE_STATE` 也会把状态值交给事件名参数。手工生成 trace packet（单个 protobuf 事件数据包）时应以真实字段定义和 SDK 实现为准，不能照搬这条过时注释。空字符串或未设置事件名会结束当前状态，使轨道进入 idle。

下面节选只用于展示枚举边界，省略了 proto 中的大段注释和其他字段：

```protobuf
enum Type {
  TYPE_UNSPECIFIED = 0;
  TYPE_SLICE_BEGIN = 1;
  TYPE_SLICE_END = 2;
  TYPE_INSTANT = 3;
  TYPE_COUNTER = 4;
  TYPE_STATE = 5;
}
```

Android 17 标签中的同一枚举止于 `TYPE_COUNTER = 4`。`TYPE_STATE = 5` 只说明 v57 的二进制格式已经分配这个枚举值，不代表每种语言 SDK 都同时提供了高层方法；看到 API 37 或 Android 17 也不能推出设备自带 v57 状态轨道。

#### Trace Processor 如何形成持续时间

v57.2 的 `StateTracker::UpdateState()` 展示了几条容易遗漏的语义：

- 新值与当前值不同：关闭旧行，把 `dur` 写成两次状态事件的时间差，再创建新行；
- 新值与当前值相同：不创建新行，只把新参数附加到当前状态；
- 新值为空：关闭旧行，不创建 idle 行；
- 尚未被下一次转换或清空关闭的行以 `dur = -1` 暂存；`-1` 是“持续时间尚未确定”的哨兵值。

这也解释了为什么查询 `state` 表时不应再用 `LEAD(ts)` 计算时长。`LEAD()` 是读取下一行值的 SQL 窗口函数；Trace Processor 已经维护 `dur`，手工用下一行时间戳相减会忽略相同状态合并、显式清空和开放区间的语义。

### 写入 state 事件

#### C++ SDK

下面的片段展示一个状态轨道上的三次转换。类别注册、Tracing 初始化和 session 配置沿用 Perfetto SDK 的常规写法，此处省略：

```cpp
perfetto::StateTrack player_state("Player state");

TRACE_STATE("player", "Buffering", player_state);
TRACE_STATE("player", "Playing", player_state);
TRACE_STATE("player", "", player_state);  // 清空当前状态，进入 idle
```

第三次调用传入空字符串，作用是关闭 `Playing` 并进入 idle。同一逻辑轨道应复用稳定的 `StateTrack` 身份，也就是每次更新都指向同一 `track_uuid`。状态值应来自受控枚举；cardinality（基数）表示可能出现的不同取值数量，把请求 ID、文件名等高 cardinality 字符串作为状态，会制造大量难以聚合的值，也会增加 trace 体积。

#### 上游 `main` 的 C high-level API

下面的调用展示上游提交 #6464 加入的 C high-level API（用宏封装底层 C ABI 的接口）形态，用于向已经注册的状态轨道写入 `Buffering`。该提交位于 v57.2 之后的 `main` 分支，示例只适用于包含这次变更的 commit（源码提交）或后续明确收录它的版本：

```c
PERFETTO_TE(player, PERFETTO_TE_STATE("Buffering"),
            PERFETTO_TE_REGISTERED_TRACK(&player_state_track));
```

`player_state_track` 的声明和注册必须使用状态轨道 API 完成。普通 counter 或 named track 的 descriptor 不会把轨道标记为 state，不能传给状态事件。v57.2 的公开 C 头文件还没有 `PERFETTO_TE_STATE`、`PerfettoTeStateTrackRegister` 等符号，因此这段代码不能按 v57.2 tag 编译；依赖必须锁定到实际包含 #6464 的版本或 commit。

#### Android Java SDK 的 release tag 差异

v57.1 发布了 state track，但各语言 SDK 的高层 API 并未在同一个 release tag 中全部到位。源码核查得到下面的版本差异：

- `v57.1` 与 `v57.2` tag 下的 `src/android_sdk/.../PerfettoTrace.java` 只公开 slice、instant 和 counter 的事件类型，未出现 `TYPE_STATE` 或 `state(...)`；
- 上游 `main` 的 `sdk: add state track event support (C HL API + Java SDK)` 提交 #6464 才加入 `PerfettoTrace.state(...)`、state track builder、C high-level API 和 JNI（Java 与 C/C++ 之间的调用桥梁）路径；
- release tag 与该变更所在分支已经分开，不能把 `main` 上的方法签名写成 v57.1/v57.2 已发布 API。

工程上应以项目解析到的 Java artifact（构建工具实际下载的库文件）和源码 commit 为准：锁定依赖，查看 `PerfettoTrace` 公共方法并做一次编译验证。若 artifact 没有 state API，可以改用 v57.2 C++ SDK，或等待所采用的 Java SDK 版本明确包含该变更。文档中的 Java 示例也必须由所声明的依赖版本实际编译通过。

### 查询 `state` 表

#### 先确认分析器版本和表结构

Android 17 自带的 v54 Trace Processor 不认识 `state` 表。使用 v57.1 或更高的兼容分析器打开 trace 后，可以先执行下面的结构查询。`PRAGMA table_info(...)` 是 SQLite/PerfettoSQL 用来列出表或视图字段的命令：

```sql
PRAGMA table_info(state);
```

v57.2 的公开 view（由 SQL 查询定义、读取时计算的表状结果）包含 `id`、`ts`、`dur`、`track_id`、`category`、`value` 和 `arg_set_id`。`ts` 与 `dur` 的单位都是纳秒，`arg_set_id` 可关联该状态附带的参数。状态列名是 `value`，不存在名为 `state` 的列。

#### 查询转换与已观测时长

下面的查询列出状态转换，并把 trace 结束时仍开放的 `dur = -1` 行裁剪到 `trace_bounds.end_ts`。`trace_bounds` 给出当前 trace 中数据的起止时间边界：

```sql
SELECT
  t.name AS track_name,
  s.ts,
  s.value,
  s.category,
  CASE
    WHEN s.dur = -1 THEN b.end_ts - s.ts
    ELSE s.dur
  END AS observed_dur_ns,
  ROUND(
    (CASE WHEN s.dur = -1 THEN b.end_ts - s.ts ELSE s.dur END) / 1e6,
    3
  ) AS observed_dur_ms,
  s.arg_set_id
FROM state AS s
JOIN track AS t ON t.id = s.track_id
CROSS JOIN trace_bounds AS b
WHERE t.name = 'Player state'
ORDER BY s.ts;
```

`CROSS JOIN trace_bounds` 把同一行 trace 边界值附到每条状态记录上。`observed_dur_ms` 只表示录制窗口内观察到的时长。开放行可能在 trace 开始前已经处于该状态，也可能在 trace 结束后继续保持；裁剪后的值不能代表完整业务时长。若第一条状态事件晚于 `trace_bounds.start_ts`，更早的状态仍是未知值，查询不会自行补齐。

#### 汇总各状态占比

下面的查询把每行限制在 trace 边界内，再按状态值聚合，适合比较一次录制中播放器的缓冲和播放占比：

```sql
WITH bounded AS (
  SELECT
    s.value,
    CASE
      WHEN s.dur = -1 THEN b.end_ts - s.ts
      ELSE s.dur
    END AS dur
  FROM state AS s
  JOIN track AS t ON t.id = s.track_id
  CROSS JOIN trace_bounds AS b
  WHERE t.name = 'Player state'
)
SELECT
  value,
  ROUND(SUM(dur) / 1e6, 3) AS total_ms,
  ROUND(100.0 * SUM(dur) / SUM(SUM(dur)) OVER (), 2) AS observed_percent
FROM bounded
WHERE dur >= 0
GROUP BY value
ORDER BY total_ms DESC;
```

`SUM(SUM(dur)) OVER ()` 先得到每种状态的合计时长，再计算所有状态的总和。这个分母只覆盖 `state` 表中有值的区间，因为 idle 不会生成状态行。若指标要求把 idle 计入分母，应使用整个观测窗口，或根据相邻状态行另外构造 idle 间隔；报告中应说明采用哪种口径。

### 在 Android 17 上采用 v57 能力

#### 路径一：只升级开发机分析器

这是改动最小的方案：

1. Android 17 继续使用系统 Perfetto 录制 sched、ftrace、atrace、FrameTimeline、heap profile 等既有数据；
2. 开发机安装固定版本的 v57.2 或更高 Trace Processor；
3. 用该分析器读取 trace，执行 SQL 并保存查询结果、工具版本和原始文件。

这个方案能获得新分析器的表结构、PerfettoSQL 标准库和解析修复，但旧 producer 依旧不会产生 `TYPE_STATE`。

#### 路径二：应用携带新版 SDK 生产 state track

需要原生状态轨道时，应把 producer SDK 与 Trace Processor/UI 作为一组有明确版本的能力交付：

1. 应用或测试进程链接包含状态轨道的 Perfetto SDK；
2. 在 in-process backend 或经验证的 system backend 上录制；
3. 使用 v57.2 或更高的兼容 Trace Processor 和 UI 打开结果；
4. 在目标 Android 17 build 上验证注册、SELinux、缓冲区、丢包统计和 SQL 表；
5. 为旧分析器保留可识别的降级标记，或者明确拒绝旧版本工具。

backend 是 SDK 写入 trace 的目标。in-process backend 在本进程内管理缓冲与会话，system backend 则连接设备上的 Perfetto tracing service；trace packet 是 producer 写入服务的 protobuf（Protocol Buffers 序列化格式）数据单元。Android 17 的 tracing service 可以搬运 producer 写入的 packet，但这不表示任意新版 SDK 都能无条件接入 system backend。SDK ABI（二进制调用约定）、Unix socket（本机进程间通信端点）权限、数据源注册策略和产品 SELinux 强制访问规则都可能限制连接，必须在目标系统镜像上实测。

不建议为了追逐上游版本而单独替换产品镜像中的 `traced` 或 `trace_processor_shell`。这些平台二进制会与 Android init 服务启动配置、文件权限、SELinux、AIDL（Android 接口定义语言）生成的 Binder 接口、IPC（进程间通信）协议及系统测试一起交付；只覆盖其中一个文件，可能造成协议、权限或启动流程不匹配。

#### 路径三：维持 Android 17 平台兼容

无法携带新版 SDK 时，可以按数据含义选择 Android 17 已有的轨道类型：

- 有明确开始和结束的活动：slice；
- 某个时刻的数值：counter；
- 单次状态转换提示：instant，并通过稳定名称或参数携带值；
- 需要计算状态持续时间：由生产端维护成对 slice，或在 SQL 中依据经过审核的 instant 事件构造区间。

这种兼容表达缺少 state track 的单值约束和专用 UI 展示。生产代码要自行保证状态转换合法，文档、SQL 和指标名称也应标明所用替代方案，避免与原生 `state` 表混用。

### v57 系列的其他变化及 Android 边界

- `linux.journald` data source 采集使用 systemd 的 Linux 系统日志 journald，并在统一日志表中用 `log_source` 标明来源。Android 使用 logcat；该数据源不会在 Android 17 上取代 logcat。
- JSON Trace Event Format 用 `"ph": "X"` 表示带完整时长的 complete event，同一线程上的这类事件按格式约束不应互相重叠。v57 会把重叠事件放入额外的 overflow track（容纳冲突事件的备用轨道），UI 再合并显示，同时记录导入警告。生产工具应使用异步 `"b"` / `"e"` 事件表达可重叠区间。
- 查询结果网格增加列排序、重排、隐藏和更清楚的 SQL 错误显示。这些是 UI 操作能力，不改变表结构或 SQL 计算结果。
- `heapprofd.process_cmdline` 是按进程命令行选择 native heap profiler（C/C++ 堆分析器）目标的配置项。它支持部分通配符，但通配符只能匹配已经运行的进程；配置必须设置 `no_startup = true`，明确禁用“从进程启动时开始 profiling”的模式。
- C high-level API 和 Android Java SDK 增加嵌套轨道及同级轨道的排序、合并控制。correlation ID（关联 ID）只表示多个事件属于同一逻辑操作，不包含因果方向；需要表达跨线程的先后或因果关系时仍应使用 flow。
- Trace Processor 可从公开 URL 或 Perfetto permalink（Perfetto UI 保存并分享 trace 的链接）加载 trace。生产 trace 常含进程、线程与业务信息，公开 URL 只适合经过授权和脱敏的文件。
- `perfetto` Python 包默认选择与包版本对应的 Trace Processor 二进制，便于重复得到相同结果；切换到 `fetch_latest_trace_processor` 会让同一脚本在不同日期下载不同二进制，产生版本漂移。
- Adreno 是 Qualcomm GPU 系列。它的 `adreno_cmdbatch_retired`、`adreno_cmdbatch_sync` ftrace 事件在 v57.1 中可解析为 GPU timeline slice；目标设备是否提供这些内核事件仍取决于系统 build 与 GPU 驱动。
- v57.2 只修复携带自有 proto descriptor 的 trace 在 wire-compatible schema 变化后可能解析失败的问题。wire-compatible 表示字段变更仍遵守 protobuf 的序列化兼容规则；这项修复不改变 state track 的数据模型。

### 评审清单

评审含 v57 state track 的改动时，可逐项检查：

- [ ] Android 平台版本基线写成 Android 17 / API 37 / `android-17.0.0_r1`
- [ ] 平台内置 Perfetto 标为 v54.0 加平台补丁，没有写成 v57
- [ ] producer SDK、Trace Processor 和 UI 各自记录版本或 commit（源码提交标识）
- [ ] state track 使用稳定轨道身份和有限状态集合
- [ ] idle 通过清空表达，指标没有漏掉 idle 分母
- [ ] SQL 使用 `state.value` 和 `state.dur`，没有重复用 `LEAD()` 推导时长
- [ ] `dur = -1` 按 trace 边界处理，并注明只是观测窗口
- [ ] C high-level 与 Java 示例已经由项目采用的 artifact 编译验证，没有把 `main` API 写成 v57.2 API
- [ ] trace 上传、公开 URL 和提供给 AI 模型的方式符合数据处理规则

### 源码与官方资料

- [Perfetto v57.1 release notes](https://github.com/google/perfetto/releases/tag/v57.1)
- [Android 17 标签下的 Perfetto CHANGELOG](https://android.googlesource.com/platform/external/perfetto/+/refs/tags/android-17.0.0_r1/CHANGELOG)
- [Android 17 标签下的 TrackEvent proto](https://android.googlesource.com/platform/external/perfetto/+/refs/tags/android-17.0.0_r1/protos/perfetto/trace/track_event/track_event.proto)
- [v57.1 TrackEvent proto](https://github.com/google/perfetto/blob/v57.1/protos/perfetto/trace/track_event/track_event.proto)
- [v57.1 StateDescriptor proto](https://github.com/google/perfetto/blob/v57.1/protos/perfetto/trace/track_event/state_descriptor.proto)
- [v57.1 `state` SQL view](https://github.com/google/perfetto/blob/v57.1/src/trace_processor/perfetto_sql/stdlib/prelude/after_eof/views.sql)
- [v57.1 StateTracker](https://github.com/google/perfetto/blob/v57.1/src/trace_processor/importers/common/state_tracker.cc)
- [v57.1 Android Java `PerfettoTrace`](https://github.com/google/perfetto/blob/v57.1/src/android_sdk/java/main/dev/perfetto/sdk/PerfettoTrace.java)
- [上游 Java state track 变更 #6464](https://github.com/google/perfetto/commit/0894477744bf11fa1f08ca81bbceb14cd5385737)


## 常见误区

**Slice 很长，所以 CPU 计算很重。** Slice 是墙上区间，线程可能大部分时间在等待。要看线程状态或可用的线程时间。

**Running 就能知道热点函数。** Running 只证明线程占用 CPU。函数级归因需要嵌套 Slice、调用栈采样或方法跟踪。

**Runnable 长就提高线程优先级。** Runnable 只证明线程在等 CPU。优先级、负载、affinity、cpuset、热限制和调度策略都要核对，盲目提权还会伤害其他线程和功耗。

**D 状态就是磁盘慢。** D 表示不可中断等待。没有 `blocked_function`、`io_wait` 或驱动证据时，不能把原因限定为磁盘。

**红色都代表同一种问题。** Thread State、锁竞争 Slice 和 FrameTimeline 各有自己的颜色语义。结论应写轨道类型和字段值。

**Android Studio System Trace 只看 App。** 当前 System Trace 能展示系统级活动。Perfetto UI 的差异主要在开放时间轴、SQL、扩展和跨进程分析能力，不能用“有没有系统数据”简单二分。


## 参考资料

- [Perfetto UI](https://perfetto.dev/docs/visualization/perfetto-ui)、[Commands and Macros](https://perfetto.dev/docs/visualization/ui-automation)、[Debug Tracks](https://perfetto.dev/docs/analysis/debug-tracks) 与上游 [`colorForState()`](https://github.com/google/perfetto/blob/main/ui/src/components/colorizer.ts)：加载、导航、Area Selection、Pin、命令面板、SQL 轨道和配色实现边界。
- [CPU Scheduling events](https://perfetto.dev/docs/data-sources/cpu-scheduling)、[PerfettoSQL tables](https://perfetto.dev/docs/analysis/sql-tables) 与 [Android trace cookbook](https://perfetto.dev/docs/analysis/common-queries)：调度状态、waker、`thread_state`、D 状态和 `blocked_function`。
- [Android Jank detection with FrameTimeline](https://perfetto.dev/docs/data-sources/frametimeline) 与 [Track Event flows](https://perfetto.dev/docs/instrumentation/track-events)：Expected / Actual、帧字段、颜色和 Flow 语义。
- [PerfettoSQL standard library](https://perfetto.dev/docs/analysis/stdlib-docs)：`slices.self_dur`、Binder 和 Android 分析模块。
- [Android Studio System Trace](https://developer.android.com/studio/profile/cpu-profiler)：Android Studio 当前系统级时间轴的能力边界。
- Android 17 [`Scheduler.cpp`](https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/services/surfaceflinger/Scheduler/Scheduler.cpp)、[`SurfaceFlinger.cpp`](https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/services/surfaceflinger/SurfaceFlinger.cpp)、[`Output.cpp`](https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/services/surfaceflinger/CompositionEngine/src/Output.cpp) 与 [`FrameTimeline.cpp`](https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/services/surfaceflinger/Scheduler/FrameTimeline.cpp)：帧调度、提交、合成、显示输出和帧分类。
- Android 17 [`task_state.cc`](https://android.googlesource.com/platform/external/perfetto/+/refs/tags/android-17.0.0_r1/src/trace_processor/types/task_state.cc)、[`self_dur.sql`](https://android.googlesource.com/platform/external/perfetto/+/refs/tags/android-17.0.0_r1/src/trace_processor/perfetto_sql/stdlib/slices/self_dur.sql) 与 [`binder.sql`](https://android.googlesource.com/platform/external/perfetto/+/refs/tags/android-17.0.0_r1/src/trace_processor/perfetto_sql/stdlib/android/binder.sql)：调度状态、Self Duration 和 Binder 关联实现。
- common kernel [`android17-6.18-2026-06_r6/include/linux/sched.h`](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/include/linux/sched.h)：Linux task 状态位定义。
