---
title: "Perfetto View 解读"
chapter: "13.3"
section: "13.3"
section_title: "Perfetto View 解读"
status: finalized
drafted_date: "2026-04-03"
drafted_by: "openclaw-task2a"
applicable_versions: "Android 9 (API 28) - Android 17 (API 37)"
last_verified: "2026-07-31"
last_verified_against: "AOSP android-17.0.0_r1（external/perfetto ece66975738007dd0978b911d8a2077e49b8f31e、frameworks/native ae266dcb706d083868578cfedce381ef44488a07）+ android17-6.18-2026-06_r6 + 2026-07-31 Perfetto/Android 官方文档"
confidence: high
reviewed_date: "2026-06-09"
reviewed_by: "openclaw-task6"
task6_result: pass-light-edit
task6_l1_l2_fixes: 4
task6_l3_l4_issues: 0
last_task6_at: "2026-06-09T20:10:00+08:00"
last_task6_review_log: "logs/review/2026-06-09-20-review.md"
task6_review_notes: "2026-05-28 12 Task6 复审：L1/L2 小修 4 处，清理重复表述、冗余强调和少量术语化表达；无 L3/L4 回炉项，送 Task9 技术复审。"
sources:
  - type: internal-reference
    path: "/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/DeepResearch/当 Perfetto 显示 Running 时,Android 程序到底在做什么? .md"
    role: "Running、Runnable 与线程状态解释边界"
  - type: internal-reference
    path: "/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/DeepResearch/2026-07-13-android17-surfaceflinger-perfetto-trace.md"
    role: "Android 17 SurfaceFlinger trace 入口与调用阶段"
  - type: internal-reference
    path: "/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/DeepResearch/2026-05-06-binder-transaction-trace-perfetto-analysis.md"
    role: "Binder transaction、线程状态与跨进程关联"
  - type: official
    path: "https://perfetto.dev/docs/visualization/perfetto-ui"
    role: "当前 UI 的加载、导航、选区、过滤、Pin 与快捷键"
  - type: official
    path: "https://perfetto.dev/docs/visualization/ui-automation"
    role: "命令面板、启动命令与宏"
  - type: official
    path: "https://perfetto.dev/docs/analysis/debug-tracks"
    role: "SQL 模式与 Debug Track"
  - type: official
    path: "https://perfetto.dev/docs/data-sources/cpu-scheduling"
    role: "CPU 调度轨道、waker 与 end_state 定义"
  - type: official
    path: "https://perfetto.dev/docs/data-sources/frametimeline"
    role: "FrameTimeline Expected/Actual、颜色、字段与 Flow"
  - type: official
    path: "https://perfetto.dev/docs/instrumentation/track-events"
    role: "Flow Event 与 Counter 的数据语义"
  - type: official
    path: "https://perfetto.dev/docs/analysis/sql-tables"
    role: "slice、sched 与 thread_state 表字段"
  - type: official
    path: "https://perfetto.dev/docs/analysis/stdlib-docs"
    role: "slices.self_dur 与 Android Binder 标准库"
  - type: official
    path: "https://perfetto.dev/docs/analysis/common-queries"
    role: "Uninterruptible Sleep 与 blocked_function 分析"
  - type: official
    path: "https://perfetto.dev/docs/visualization/large-traces"
    role: "大型 trace 的本机 Trace Processor 后端"
  - type: official
    path: "https://developer.android.com/studio/profile/cpu-profiler"
    role: "Android Studio System Trace 的系统级视图"
  - type: upstream
    path: "https://github.com/google/perfetto/blob/main/ui/src/components/colorizer.ts"
    role: "2026-07-31 当前 UI 的线程状态配色实现"
  - type: aosp
    path: "https://android.googlesource.com/platform/external/perfetto/+/refs/tags/android-17.0.0_r1/src/trace_processor/types/task_state.cc"
    role: "Android 17 Trace Processor 的内核 task state 解码"
  - type: aosp
    path: "https://android.googlesource.com/platform/external/perfetto/+/refs/tags/android-17.0.0_r1/src/trace_processor/perfetto_sql/stdlib/slices/self_dur.sql"
    role: "Android 17 slice_self_dur 实现"
  - type: aosp
    path: "https://android.googlesource.com/platform/external/perfetto/+/refs/tags/android-17.0.0_r1/src/trace_processor/perfetto_sql/stdlib/android/binder.sql"
    role: "Android 17 Binder transaction 关联"
  - type: aosp
    path: "https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/services/surfaceflinger/Scheduler/Scheduler.cpp"
    role: "Android 17 onFrameSignal、commit 与 composite 调度"
  - type: aosp
    path: "https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/services/surfaceflinger/SurfaceFlinger.cpp"
    role: "Android 17 SurfaceFlinger commit/composite 实现"
  - type: aosp
    path: "https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/services/surfaceflinger/CompositionEngine/src/Output.cpp"
    role: "Android 17 Output present 与 release 阶段"
  - type: aosp
    path: "https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/services/surfaceflinger/Scheduler/FrameTimeline.cpp"
    role: "Android 17 FrameTimeline 分类与 trace 输出"
  - type: kernel
    path: "https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/include/linux/sched.h"
    role: "Android 17 common kernel 线程状态位定义"
tags:
  - android
  - perfetto
  - trace-view
  - frame-timeline
  - binder
  - thread-state
  - cpu-scheduling
related_chapters: ["13.1", "13.2", "13.4", "2.6", "14.2", "14.5"]
polish_count: 1
polish_date: "2026-04-10"
polish_by: "task2b-polish"
pipeline_stage: ready-to-publish
task6_state: reviewed
task9_state: reviewed
task2b_state: fixed
task2b_result: fixed
task9_result: auto-fixed
last_task2b_at: "2026-05-28T10:50:00+08:00"
task2b_fixed_by: openclaw-task2b
updated_date: "2026-06-09"
updated_by: openclaw-task9
last_task9_audit: "2026-06-09"
last_task9_at: "2026-06-09T17:25:15+08:00"
last_task6_audit: "2026-06-10"
last_task9_review_log: "logs/deep-review/2026-06-09-17-audit.md"
last_task9_autofix_at: "2026-06-09"
task9_review_notes: "2026-05-28 11 Task9 auto-fix: 修正 Perfetto UI 404 文档链接/打开入口说明，并修正 SurfaceFlinger Android 13+ commit/composite/present 排查入口；回到 Task6 复审。 | 2026-05-28 12 Task9 复审：pass-tech-review。P0 0 / P1 0 / P2 0；自动晋升 finalized。 | 2026-06-09 17 Task9 idle audit auto-fix: 修正 Perfetto v52 暗色主题实验状态与当前 UI Theme 命令说明；未发现 Android/API 38+ 越界内容，回到 Task6 复审。"
task9_reviewed_date: "2026-06-09"
task9_reviewed_by: openclaw-task9
p0: 0
p1: 0
p2: 0
deepseek_cn_review_state: done
last_deepseek_cn_review_at: 2026-06-19
---


# 13.3 Perfetto View 解读

## 读图顺序比轨道数量更重要

Perfetto UI 把多个数据源放在同一时间轴上。它不会为缺失的调度事件、FrameTimeline、Binder 或应用标记补数据，也不会替分析者决定因果关系。读图时要把“轨道上发生了什么”和“为什么发生”分开。

一轮可靠分析按下面的顺序推进：

1. 在 Info / Stats 中确认 trace 时间范围、目标进程和数据完整性。
2. 圈出复现动作对应的时间窗，不在整份 trace 里漫游。
3. 用 FrameTimeline、启动标记、ANR、输入事件或业务 Slice 锁定异常事件。
4. 回到相关线程，区分 Running、Runnable、Sleeping 和 Uninterruptible Sleep。
5. 沿 Binder、Flow、waker 或帧 token 检查跨线程、跨进程和显示下游。
6. 需要批量比较时，把 UI 观察写成 PerfettoSQL。

平台结论固定到 Android 17 / API 37 / `android-17.0.0_r1`，内核状态固定到 `android17-6.18-2026-06_r6`。`ui.perfetto.dev` 和主机 Trace Processor 独立更新，界面文字、命令和轨道布局以 2026-07-31 的官方文档为准。

## 打开并整理 Trace

### 加载方式与大文件边界

[Perfetto UI](https://ui.perfetto.dev/) 可以通过侧边栏的 “Open trace file” 或拖放加载本地 trace。一次选择多个文件时，当前 UI 会进入合并配置流程，把它们放到共享时间轴；合并前要确认各文件的时钟来源和对齐依据。

浏览器能否顺利处理大文件取决于 trace 内容、主机内存、浏览器限制和查询复杂度，不能用一个固定体积判断。加载或交互开始受限时，使用本机 `trace_processor server http <trace>` 作为 UI 后端，或直接用 `trace_processor_shell` 查询，具体流程见 §13.4。把二进制 trace 全量转成文本通常会扩大体积，也会失去 UI 的索引优势，不适合作为大文件的默认方案。

### 时间轴、选择与详情抽屉

当前 UI 的常用操作如下：

| 目的 | 操作 | 结果 |
| --- | --- | --- |
| 缩放与平移 | `W` / `S`、`A` / `D`；也可用 `Ctrl` + 滚轮和 `Shift` + 拖动 | 改变可见时间窗 |
| 聚焦事件 | 选中事件后按 `F`；再按一次 `F` | 居中，再把事件适配到视口 |
| 相邻事件 | `,` / `.` | 在同一轨道切换前一个或后一个事件 |
| 时间选区 | 在时间轴或轨道区域拖动 | 创建带起止时间和轨道集合的 Area Selection |
| 事件转选区 | 选中事件后按 `R` | 用事件边界创建 Area Selection |
| 详情抽屉 | `Q` | 显示或隐藏 Tab Drawer |
| 命令面板 | `Ctrl+Shift+P`；macOS 用 `Cmd+Shift+P` | 搜索并执行 UI 命令 |
| 当前快捷键 | `?` | 查看该 UI 构建实际注册的快捷键 |

Area Selection 不只有起止时间，还包含所选轨道。修改轨道外壳上的勾选项会改变统计范围；分享截图或结论时，应把选区边界和轨道集合一起说明。

### 找轨道、过滤和 Pin

长 trace 的效率来自减少同时可见的轨道：

- Track Finder 按名称查找轨道。
- Timeline 工具栏的过滤器可按轨道名、进程或线程缩小显示范围；清除过滤后数据仍在。
- 轨道外壳的 Pin 按钮把轨道移到工作区顶部。

分析一帧时，常用组合是 App 主线程、RenderThread、FrameTimeline、`surfaceflinger` 主线程和相关 CPU。分析同步 Binder 时，把客户端线程与服务端 Binder 线程一起 Pin。Pin 只改变显示位置，不改变数据或时间对齐。

Omnibox 输入 `:` 可以进入 SQL 模式。查询结果包含 `ts` 与 `dur` 时，可以生成 Debug Slice Track；包含 `ts` 与 `value` 时，可以生成 Debug Counter Track。复杂查询留到 §13.9，这里只把它当作“把筛选结果放回时间轴”的入口。

## 轨道描述的是哪一层

### CPU Scheduling、Frequency 与 Idle

CPU Scheduling 轨道来自内核调度事件。每个 Slice 表示某个线程在一颗 CPU 上运行的区间；详情中的 `priority`、`end_state` 和线程身份可以解释这次运行如何结束。它回答“哪条线程在何时占用哪颗 CPU”，不回答线程执行了哪一行代码。代码热点还需要应用 Slice、采样调用栈或方法跟踪。

CPU Frequency 轨道来自设备提供的频率事件。它能显示记录到的频率变化，但频率值不能单独证明某段代码变慢：CPU 微架构、容量、热限制、空闲状态、调度放置和内存等待都会影响完成时间。判断迁核是否有害也要结合 Runnable 延迟、各 CPU 的并发负载和设备拓扑，不能要求主线程一直固定在某颗“大核”。

CPU Idle 轨道描述 CPU 的空闲状态。线程处于 Sleeping 或 D 状态时，本来就没有资格运行；此时看到部分 CPU idle 并不构成调度异常。只有线程已 Runnable、满足 affinity/cpuset 等约束，却长期没有进入 Running，才需要继续检查优先级、CPU 可用集合、系统负载和调度策略。

### 进程、线程、Slice 与线程状态

进程分组把同一进程的线程、Counter 和其他轨道放在一起。线程轨道上常同时出现两类数据：

- **Slice**：应用或平台标记的命名区间，例如 `Choreographer#doFrame`、`performTraversals`、`DrawFrame`。Slice 说明某个逻辑区间尚未结束，不保证线程全程占用 CPU。
- **Thread State**：Trace Processor 根据 `sched_switch`、`sched_waking` 等事件重建的调度状态。它说明线程在 CPU 上运行、等待 CPU，或等待某个唤醒条件。

App 主线程负责 Looper 消息、输入分发、生命周期和 View/Compose 工作；`Choreographer#doFrame` 是传统 View/HWUI 帧的重要入口。RenderThread 负责 HWUI 渲染工作的记录、准备与图形提交，其中可能包含 CPU 执行、GPU 工作排队和 fence 等待。名称相同的 Slice 在不同 Android 版本、渲染后端和厂商实现中可能覆盖不同子阶段，要结合子 Slice 与源码核对。

Binder 线程名能帮助定位服务端执行线程，但 Binder transaction 本身不保证包含 Java 方法名。方法名是否可见取决于平台或业务是否在服务端路径添加了 ATrace / Track Event 标记。

### Counter Track

Counter 表示某个数值随时间变化，例如频率、RSS、堆大小、BufferQueue 积压量或自定义队列深度。Counter 的来源和单位由数据源决定，图形上升不自动等于泄漏或性能退化。

内存 Counter 持续上升时，要区分采样区间、GC、缓存上限、映射文件、共享内存和进程生命周期。GPU Counter 是否存在、含义是什么，也受 GPU 数据源和厂商支持限制。报告中应记录 Counter 名称、单位、数据源和比较窗口。

## Slice 详情：三种时间不能混用

### Wall Duration

`slice.dur` 是 Slice 起点到终点的墙上时长，对应时间轴上的宽度。线程在这段时间内可能运行、等待 CPU、休眠或阻塞。长 Slice 只证明命名区间长，不能直接判定为 CPU 计算重。

### Thread Duration / CPU 时间

`slice.thread_dur` 是 Slice 消耗的线程时间，只有 Track Event 开启线程时间采集时才会填充。Android ATrace 产生的普通 Slice 往往没有这个字段。UI 未显示 Thread Duration 时，不能把缺失值当作 0。

需要计算某个线程 Slice 内的 on-CPU 时间时，应将该 Slice 的 `[ts, ts + dur)` 与 `thread_state.state = 'Running'` 求交。只有调度数据覆盖完整时，墙上时间才能按 Running、Runnable、Sleeping、D 等互斥状态分解；trace 边界、丢包和未知区间必须单列。

### Self Duration

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

## 线程状态与颜色编码

### 状态值是证据，颜色只是导航

Android 17 Trace Processor 按内核 `prev_state` 解码调度状态；`android17-6.18-2026-06_r6/include/linux/sched.h` 定义了 `TASK_RUNNING`、`TASK_INTERRUPTIBLE`、`TASK_UNINTERRUPTIBLE` 等状态位。UI 颜色帮助快速浏览，但主题、轨道类型和 UI 版本可能调整配色。结论应写状态名或 SQL 值，不能只写“绿色段”“橙色段”。

| UI / SQL 状态 | 内核或处理器含义 | 可以确认 | 仍需补证据 |
| --- | --- | --- | --- |
| `Running` | 线程正在某颗 CPU 上运行 | 该区间获得了 CPU | 执行哪段代码、是否受缓存或内存延迟影响 |
| `R` / Runnable | 已具备运行资格，等待调度 | 该区间没有获得 CPU | 是负载、优先级、affinity、cpuset 还是调度策略 |
| `R+` | Runnable，并由抢占结束上一段运行 | 线程被抢占后等待 | 抢占者、优先级和 CPU 负载 |
| `S` / Sleeping | 可中断睡眠，等待显式唤醒 | 线程不在运行队列 | Binder、futex、条件变量、定时器或其他等待对象 |
| `D` / Uninterruptible Sleep | 不可中断睡眠 | 线程等待内核条件 | 是否为 I/O、具体 `blocked_function`、设备驱动或内存回收 |

2026-07-31 的 Perfetto UI `colorForState()` 用深绿表示 Running、亮绿表示 Runnable。Sleeping / Idle 使用透明白，会随亮色或暗色背景呈现为低对比度色块；一般 D 状态使用橙色，能够识别为 non-I/O 的 D 状态使用低饱和红色。配色不能替代详情字段。FrameTimeline 的绿、浅绿、红、黄、蓝属于另一套帧结果编码，也不能套用到线程状态。

### D 状态不等于磁盘 I/O

`TASK_UNINTERRUPTIBLE` 表示等待条件不会被普通信号打断，磁盘 I/O 只是常见来源之一。驱动等待、页回收、文件系统、块设备和其他内核等待都可能产生 D 状态。

采集了 `sched/sched_blocked_reason` 时，`thread_state` 可以提供 `blocked_function`，部分 trace 还会给出 `io_wait`。缺少这些字段时，只能写“Uninterruptible Sleep，原因未由本次 trace 识别”，不能直接归为磁盘瓶颈。

### 红色锁竞争标记不是调度状态

`Lock contention on a monitor lock` 等红色 Slice 来自 ART / 平台锁竞争埋点。等待线程的内核状态在同一时间窗内通常是 Sleeping，也可能随实现变化。红色表示已得到更具体的锁证据，不是 Linux `thread_state` 新增了一个 Blocked 状态。

详情面板若提供 owner、blocking thread 或关联跳转，应切到持锁线程检查：

1. 持锁线程是否在 Running。
2. 持锁线程是否又在等 Binder、I/O 或另一把锁。
3. 锁持有区间是否覆盖昂贵操作。
4. 这段等待是否位于当前帧、启动或 ANR 的时间窗内。

红色 Slice 本身不能证明优先级反转。优先级反转还需要等待者、持锁者、抢占者及其优先级和调度状态形成闭合证据。

### Waker 的使用边界

采集 `sched_waking` 或相关 wakeup 事件后，线程状态详情可以关联 waker。waker 说明哪个线程触发了状态转换，不保证它是业务事件源，也不保证被唤醒线程立刻获得 CPU。wakeup 到 Running 之间的区间才是调度等待。

跨 CPU 唤醒时，`sched_waking` 记录在发起唤醒的一侧，`sched_wakeup` 的记录位置受唤醒路径影响。普通延迟分析优先保证 `sched_waking` 存在；要区分 IPI 和调度器唤醒路径的各段耗时时，再同时检查更底层事件。

## Flow Events 与跨进程关联

Flow 把不同轨道上的相关事件连接起来。选中带 Flow 的事件后，UI 会突出相关箭头；未选中时可能为了可读性减少显示。箭头表达“trace 数据声明两者相关”，不自动证明同步阻塞或单一因果。

### Binder transaction

Binder 分析依赖相应的驱动 tracepoint 和 Trace Processor 解析。同步调用通常可以关联客户端 transaction、服务端 transaction 和 reply；oneway 调用没有同步 reply，客户端也不等待服务端完成。嵌套 Binder、回调和线程池排队会让路径分叉，不能把第一条箭头当成完整调用树。

读一个同步 Binder 调用时，依次检查：

1. 客户端 transaction Slice 的墙上时长和线程状态。
2. 服务端 Binder 线程何时开始处理，开始前是否存在排队空窗。
3. 服务端 Slice 内是 Running、锁等待、D 状态还是再次发起 Binder。
4. reply 何时返回，客户端从唤醒到 Running 又等了多久。

Android 17 的 `stdlib/android/binder.sql` 会把 Binder transaction 与 reply、线程和进程关联起来。UI 跳转适合看单个案例，批量统计应使用该标准库或 §13.9 的查询模板。

### FrameTimeline Flow

选中 App 的 Actual Timeline Slice 时，Perfetto 可以通过 surface frame token 关联对应的 SurfaceFlinger display frame；选中 display frame 时，也可以显示这次合成包含的多个应用 frame。这个 Flow 表达帧的消费关系，比仅按时间重叠匹配可靠。

Flow 不等于 BufferQueue frame number，也不替代 acquire、present 和 release fence。SurfaceView 等独立 Surface 路径还受 FrameTimeline 覆盖范围限制，具体边界见 §13.19 和 §15。

## FrameTimeline：从异常帧进入

FrameTimeline 从 Android 12 / API 31 起可用。Android 9-11 没有 Expected / Actual 主轨道，应从 `Choreographer#doFrame`、RenderThread、调度事件和 SurfaceFlinger 时间窗建立关联。

Expected Timeline 表示调度器给这一帧的预计窗口。App Actual Timeline 从 `Choreographer#doFrame` 或 NDK Choreographer 回调开始，结束点取 GPU 完成与 post 到 SurfaceFlinger 两者中较晚者。SurfaceFlinger Actual Timeline 覆盖合成到屏幕更新的结果。Actual Slice 的 `dur` 不是主线程 CPU 时间，也不是所有显示路径的端到端延迟。

选中 Actual Slice 后，按下面的字段读：

- `Present Type`：Early、On-time 或 Late。
- `On time finish`：生产者是否按预计 deadline 完成工作。
- `Jank Type`：平台分类，可包含 App、SurfaceFlinger、Display HAL、预测和调度原因。
- `Prediction Type`：预测是否有效或已经过期。
- `GPU Composition`：该帧是否使用 GPU 合成。
- `Layer Name`：区分同一进程更新的不同 Surface。
- `Is Buffer`：区分 buffer frame 与非 buffer 动画。

### FrameTimeline 的颜色

官方 UI 为 FrameTimeline 定义了独立颜色语义：

| 颜色 | 含义 |
| --- | --- |
| 绿色 | 未观察到 jank 的帧 |
| 浅绿色 | 帧率可能平稳，但帧晚呈现并增加输入延迟 |
| 红色 | 该 Slice 所属进程被归因为 jank 来源 |
| 黄色 | App 帧发生 jank，但归因在 SurfaceFlinger |
| 蓝色 | Dropped frame |

颜色负责找候选帧，报告应记录 `present_type`、`on_time_finish`、`jank_type`、layer 和 token。Android 17 `FrameTimeline.cpp` 把 `BufferStuffing`、`SurfaceFlingerStuffing` 等状态与 deadline jank 分开计算，不能把所有非绿色帧合并成“App Deadline Missed”。

官方文档仍提示 SurfaceView 不在 FrameTimeline 的完整支持范围内。Camera、视频、游戏和跨进程嵌入常有独立 Producer / Surface / layer，宿主窗口的帧 token 不能代替这些路径的逐帧证据。

## Android 17 SurfaceFlinger 轨道

Android 17 的主循环由 `Scheduler::onFrameSignal()` 组织。`Scheduler.cpp` 在同一帧信号中调用 `compositor.commit()`，满足合成条件后调用 `compositor.composite()`；对应实现落在 `SurfaceFlinger::commit()` 和 `SurfaceFlinger::composite()`。显示输出阶段继续进入 CompositionEngine `Output::present()` 与 `presentFrameAndReleaseLayers()`。

版本演进要保留，因为旧 trace 的 Slice 名称不同：

| 平台 | SurfaceFlinger 观察入口 |
| --- | --- |
| Android 12 / 12L | 常见 `onMessageReceived`、`onMessageInvalidate`、`onMessageRefresh`、`REFRESH` |
| Android 13-17 | 按 `onFrameSignal`、`commit`、`composite` 以及可见的 present 子阶段阅读 |

Slice 名称受埋点和版本影响，不能要求每份 Android 17 trace 都出现一条字面为 `presentFrameAndReleaseLayers` 的 Slice。源码调用关系用于解释已出现的阶段，不用于虚构 trace 中没有的数据。

`composite` 变长也不能直接归为 GPU Client Composition。要同时找到 RenderEngine / `drawLayers` 等 GPU 合成证据、HWC composition type、layer 特征和 fence 时间。事务处理变重、latch 等待、HWC validate/present 或显示提交都可能拉长 SurfaceFlinger 一帧。

## 日志与原始事件

只有采集配置包含 Android log 数据源时，UI 才能显示抓取窗口内的日志。只有保留相应 ftrace event 时，原始事件表才有对应记录。看不到 Android Logs 或 Ftrace Events 时，应回查配置与数据完整性，不能把“UI 没有轨道”解释为“系统没有发生事件”。

日志适合定位业务阶段和错误点，时间线负责验证线程、调度与依赖关系。日志时间戳、trace 时钟和跨文件合并存在偏差时，要先确认时钟转换，再做毫秒级因果判断。

## 与 Android Studio Profiler 的关系

Android Studio 的 System Trace 也是系统级视图，能够展示 CPU 核心、线程、显示、内存和部分功耗数据。把它描述成“只能看单个 App、看不到 SurfaceFlinger 或调度”已经不符合当前工具。

| 工具 | 适合的工作 |
| --- | --- |
| Android Studio System Trace | 在 IDE 内录制、围绕目标 App 查看线程和显示问题、结合工程工作流 |
| Perfetto UI | 打开多种 trace、完整时间轴导航、PerfettoSQL、Debug Track、宏和跨进程系统分析 |
| Android Studio Method / Function Trace | 查看方法或函数调用树、Flame Chart、Top Down / Bottom Up |
| Simpleperf / `linux.perf` | 调用栈采样、热点和 CPU profile |

Android Studio 的 System Trace 与 Java Method Trace 是不同录制类型，不能用统一的 `.trace` 口径描述。复杂系统问题可以从 Android Studio 导出 System Trace，再放到 Perfetto UI 做 SQL 与跨进程分析。

## 一轮掉帧分析怎么走

拿到滑动卡顿 trace 后，可以按这条主线检查：

1. 在 Info / Stats 确认复现窗口、目标进程、FrameTimeline 与调度数据存在，相关丢包不影响结论。
2. Android 12-17 从 App Actual Timeline 选择候选帧；Android 9-11 从 `doFrame`、RenderThread 与 SurfaceFlinger 的共同时间窗开始。
3. 记录 `Jank Type`、`Present Type`、`On time finish`、layer 与 token，不只记录颜色。
4. 回到主线程和 RenderThread，把长 Slice 与 Running、Runnable、S、D 状态求交。
5. Running 长时结合子 Slice 或调用栈找 CPU 工作；Runnable 长时检查全机 CPU、优先级和放置约束；S 状态沿 Binder、锁、条件变量或 waker；D 状态检查 `blocked_function` 与 `io_wait`。
6. 沿 FrameTimeline Flow 检查对应 display frame，再读 Android 17 的 `commit`、`composite` 和显示输出阶段。
7. Binder 或锁跨进程时，把客户端、服务端、持锁线程和 reply 放进同一选区。
8. 用 SQL 复核同类帧是否重复出现，避免用一个案例代表整段运行。

这套流程给出的是“证据落在哪一层”。修复动作要回到对应代码、配置和设备复现验证；FrameTimeline 的分类也不能替代源码与 fence 证据。

## 常见误区

**Slice 很长，所以 CPU 计算很重。** Slice 是墙上区间，线程可能大部分时间在等待。要看线程状态或可用的线程时间。

**Running 就能知道热点函数。** Running 只证明线程占用 CPU。函数级归因需要嵌套 Slice、调用栈采样或方法跟踪。

**Runnable 长就提高线程优先级。** Runnable 只证明线程在等 CPU。优先级、负载、affinity、cpuset、热限制和调度策略都要核对，盲目提权还会伤害其他线程和功耗。

**D 状态就是磁盘慢。** D 表示不可中断等待。没有 `blocked_function`、`io_wait` 或驱动证据时，不能把原因限定为磁盘。

**红色都代表同一种问题。** Thread State、锁竞争 Slice 和 FrameTimeline 各有自己的颜色语义。结论应写轨道类型和字段值。

**Android Studio System Trace 只看 App。** 当前 System Trace 能展示系统级活动。Perfetto UI 的优势集中在开放时间轴、SQL、扩展和跨进程分析，不是“有没有系统数据”的二分。

## Android 17 源码核对点

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

## 参考资料

- [Perfetto UI](https://perfetto.dev/docs/visualization/perfetto-ui)、[Commands and Macros](https://perfetto.dev/docs/visualization/ui-automation)、[Debug Tracks](https://perfetto.dev/docs/analysis/debug-tracks) 与当前 [`colorForState()`](https://github.com/google/perfetto/blob/main/ui/src/components/colorizer.ts)：加载、导航、Area Selection、Pin、命令面板、SQL 轨道和线程状态配色。
- [CPU Scheduling events](https://perfetto.dev/docs/data-sources/cpu-scheduling)、[PerfettoSQL tables](https://perfetto.dev/docs/analysis/sql-tables) 与 [Android trace cookbook](https://perfetto.dev/docs/analysis/common-queries)：调度状态、waker、`thread_state`、D 状态和 `blocked_function`。
- [Android Jank detection with FrameTimeline](https://perfetto.dev/docs/data-sources/frametimeline) 与 [Track Event flows](https://perfetto.dev/docs/instrumentation/track-events)：Expected / Actual、帧字段、颜色和 Flow 语义。
- [PerfettoSQL standard library](https://perfetto.dev/docs/analysis/stdlib-docs)：`slices.self_dur`、Binder 和 Android 分析模块。
- [Android Studio System Trace](https://developer.android.com/studio/profile/cpu-profiler)：Android Studio 当前系统级时间轴的能力边界。
- Android 17 [`Scheduler.cpp`](https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/services/surfaceflinger/Scheduler/Scheduler.cpp)、[`SurfaceFlinger.cpp`](https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/services/surfaceflinger/SurfaceFlinger.cpp)、[`Output.cpp`](https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/services/surfaceflinger/CompositionEngine/src/Output.cpp) 与 [`FrameTimeline.cpp`](https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/services/surfaceflinger/Scheduler/FrameTimeline.cpp)：帧调度、提交、合成、显示输出和帧分类。
- Android 17 [`task_state.cc`](https://android.googlesource.com/platform/external/perfetto/+/refs/tags/android-17.0.0_r1/src/trace_processor/types/task_state.cc)、[`self_dur.sql`](https://android.googlesource.com/platform/external/perfetto/+/refs/tags/android-17.0.0_r1/src/trace_processor/perfetto_sql/stdlib/slices/self_dur.sql) 与 [`binder.sql`](https://android.googlesource.com/platform/external/perfetto/+/refs/tags/android-17.0.0_r1/src/trace_processor/perfetto_sql/stdlib/android/binder.sql)：调度状态、Self Duration 和 Binder 关联实现。
- common kernel [`android17-6.18-2026-06_r6/include/linux/sched.h`](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/include/linux/sched.h)：Linux task 状态位定义。
