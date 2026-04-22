---
title: "eBPF/BPF 在 Android 性能分析中的应用"
chapter: "14.10"
section: "14.10"
status: ready-for-review
drafted_date: "2026-04-07"
drafted_by: "openclaw-task2a"
applicable_versions: "Android 10 (API 29) - Android 17 (API 37)"
last_verified: "2026-04-22"
last_verified_against: "AOSP android-16.0.0_r1 + Perfetto/BPF upstream docs + Android GKI release builds"
confidence: medium
sources:
  - type: aosp
    path: "packages/modules/UprobeStats/src/bpf_progs/"
  - type: aosp
    path: "system/bpf/"
  - type: aosp
    path: "frameworks/native/services/gpuservice/bpfprogs/gpuMem.c"
  - type: blog
    path: "Cubox/在 Android 中使用 eBPF：开篇-2022-06-12.md"
  - type: blog
    path: "Cubox/探索Android动态埋点的新视界：UprobeStats深度解析-2025-02-21.md"
  - type: blog
    path: "Cubox/基于eBPF的sched-ext会在产品成功的底层逻辑是什么-2025-10-18.md"
  - type: blog
    path: "Cubox/基于eBPF的CPU利用率精准计算小工具开发-2022-03-13.md"
  - type: blog
    path: "Cubox/simpleperf的使用技巧-2025-11-18.md"
  - type: official
    path: "kernel.org/doc/html/latest/scheduler/sched-ext.html"
  - type: official
    path: "source.android.com/docs/core/architecture/kernel/bpf"
  - type: blog
    path: "Cubox/ebpf在 Android 上的玩法示例-2025-12-22.md"
  - type: blog
    path: "Cubox/aosp15进程异常退出监控工具-ebpf监控signal的发送和接收-2025-12-25.md"
  - type: research
    path: "intake/research-feeds/2026-04-02-15-ch05-sched-ext-bpf-android.md"
  - type: research
    path: "intake/research-feeds/2026-04-03-07-sched-ext-bpf-scheduler.md"
tags: [eBPF, BPF, observability, tracing, sched_ext, simpleperf, kernel, performance]
related_chapters: ["14.2", "13.1", "5.1", "1.14"]
created_by: "task2a-knowledge-gap"
created_date: "2026-04-07"
gap_source: "AOSP结构+官方文档+研究素材"
polish_count: 1
polish_date: "2026-04-08"
polish_by: "task2b-polish"
pipeline_stage: task6_pending
task6_state: revisiting
task9_state: pending
task2b_state: fixed
reviewed_by: "openclaw-task6"
reviewed_date: "2026-04-21"
task6_result: pass-light-edit
task9_result: needs-rework
task9_reviewed_date: "2026-04-20"
task9_reviewed_by: "openclaw-task9"
last_task9_at: "2026-04-20T21:48:59+08:00"
task2b_result: fixed
last_task2b_at: "2026-04-22T10:03:36+08:00"
---

# 14.10 eBPF/BPF 在 Android 性能分析中的应用

在 Android 上做深度性能分析时，经常会遇到这样的困境：想看某个系统调用的延迟分布，strace 的开销几乎无法接受；想追踪一个内核函数的执行路径，却发现设备上没有 ftrace 的权限；想统计 App 在各 CPU 频率上的真实停留时间，发现 `/proc/stat` 的精度只有 Tick 级别（通常 4ms 或 10ms），远远不够。

eBPF（extended Berkeley Packet Filter）改变了这类分析方式。它让我们能在内核中安全运行自定义追踪程序，用更低的观测开销拿到更细粒度的数据。Android 从 10 开始在系统侧使用 eBPF，Android 15 引入 UprobeStats 做动态埋点，Linux 6.12 的 sched_ext 又把 eBPF 推进到调度器扩展。

读完这一节，我们应该能回答四个问题：Android 上已经有哪些 eBPF 基础设施，哪些工具链现在就能用，sched_ext 会给后续调度器演进带来什么变化，以及 eBPF 分析的边界在哪里。

<!-- outline-start -->
<!--
本节大纲与锚点

1. eBPF 是什么，为什么 Android 性能分析需要它
   - 传统工具的局限（strace / perf / ftrace）
   - eBPF 的核心优势：内核态安全小程序
   - GKI 让 eBPF 在 Android 上可用
2. Android eBPF 基础设施
   - BPF Loader 与系统级 eBPF 程序（网络统计 / CPU 频率 / GPU 内存 / 能耗）
   - BPF CO-RE：一次编译，到处运行
   - AOSP 中 eBPF 程序的位置
3. Simpleperf 与 eBPF 的结合
   - uprobe：追踪用户态函数
   - kprobe：追踪内核函数
   - 实战示例：追踪 RenderThread 帧耗时
4. UprobeStats 与动态埋点
   - 工作原理（StatsD → 配置 → uprobe attach → RingBuf → 上报）
   - 预置 BPF 程序（GenericInstrumentation / BitmapAllocation / ProcessManagement）
   - 安全限制（user 版本仅允许特定类前缀）
5. sched_ext 与可扩展调度器
   - 为什么需要可扩展调度器
   - sched_ext 架构（BPF 驱动 / 安全兜底 / 部分切换）
   - 对 Android 的意义与实验性调度器
6. eBPF 实战场景
   - CPU 利用率精准计算
   - 系统调用延迟追踪
   - I/O 延迟分布统计
   - 进程异常退出监控
   - Binder 调用追踪
7. 常见问题与误区
8. 限制与注意事项（权限 / 开销 / SELinux / 调试）
9. 与其他章节的关联
10. 参考资料
-->
<!-- outline-end -->



## eBPF 是什么，为什么 Android 性能分析需要它

eBPF 是 Linux 内核中的一个轻量级虚拟机。它允许把一段经过验证的程序挂到 tracepoint、kprobe、uprobe、cgroup hook、socket hook 等事件点，在事件发生时执行过滤、计数、聚合、栈采样或少量上下文提取。

它和传统性能工具最大的差别，在于数据在哪里先被处理。细粒度 tracing 场景里，ftrace 或 perf 往往会先把大量事件写进 ring buffer，再由用户态读取并聚合；eBPF 可以先在内核里的 BPF map 中做计数、直方图、top-N 或过滤，只把汇总结果或少量命中事件写出来。eBPF 常见的低开销，主要来自这层 in-kernel aggregation。

**strace** 基于 ptrace，会在系统调用边界暂停目标进程、抓取参数、再恢复执行。事件一密，停顿和上下文切换成本会迅速抬高。

**perf** 基于 `perf_event_open`，非常适合 CPU 热点采样；采样频率合适时，开销通常可控。它的短板在于“精确事件级追踪”并不是默认强项：如果目标是看某个函数每次调用的耗时分布、精确次数或参数过滤，仍然需要额外的事件记录和后处理。

**ftrace** 是内核自带的 tracing 框架，观测面很广，但 raw event 流一旦拉得太细，输出体积和用户态消费成本会很快上升。

eBPF 还有两个系统级前提：

- **安全边界**：程序加载前会经过 verifier 检查，限制循环、内存访问和 helper 使用方式。
- **执行效率**：通过 JIT 编译后，热点 BPF 程序会变成原生机器码执行。

对 Android 来说，GKI（General Kernel Image）把核心内核 ABI、配置和 BTF 能力收拢到了更统一的基线上，eBPF 才开始具备跨设备复用的现实基础。

[图：eBPF 与传统性能分析工具的对比——从开销、精度、安全性、适用场景四个维度]

[已验证: 官方文档, source.android.com/docs/core/architecture/kernel/bpf]

## Android eBPF 基础设施

### BPF Loader 与系统级 eBPF 程序

Android 在启动阶段会自动加载 `/system/etc/bpf/` 目录下的所有 eBPF 程序。这些程序是预编译的 `.o` 文件（ELF 格式），由 AOSP 构建系统从 C 源码编译。加载后，系统自动创建 eBPF maps 并将程序和 maps pin 到 BPF 文件系统（`/sys/fs/bpf/`）。

Android 已经在系统级使用 eBPF 的场景包括：

- **网络统计**：`netd` 使用 eBPF 程序统计每个 UID 的网络流量，区分前台/后台流量，实现按应用的网络用量监控和防火墙规则。这也是 eBPF 在 Android 上最早的大规模应用。

- **CPU 频率统计**：`time_in_state` eBPF 程序精确统计每个 App 在不同 CPU 频率上停留的时间，用于功耗分析。比起 `/proc/stat` 的 Tick 级精度（通常 4ms），eBPF 可以在每次频率切换时记录精确时间戳，精度达到纳秒级。

- **GPU 内存追踪**：Android 12 引入的 `gpu_mem` eBPF 程序，追踪每个进程和整个系统的 GPU 内存使用量。

- **能耗统计**：`netd` 中的 eBPF 程序还用于统计每个 UID 的网络流量相关的功耗。

[已验证: AOSP, system/bpf/ + source.android.com]


### BPF CO-RE：一次编译，到处运行

eBPF 程序长期受内核版本兼容性影响。结构体布局一变，硬编码偏移就会失效。BPF CO-RE（Compile Once, Run Everywhere）通过 BTF（BPF Type Format）记录“程序要访问哪些类型和字段”，加载时再按当前内核的 BTF 做重定位。

放到 Android 上，CO-RE 的收益主要体现在 GKI 公共内核面：核心 ABI 更稳定，BTF 也更可预期，跨设备复用难度明显下降。边界同样要写清楚——厂商私有驱动、额外模块或缺失 BTF 的路径，仍然可能需要按设备单独处理。CO-RE 不能替代所有兼容性验证。

目前 Android 上直接从普通 App 加载自定义 eBPF 程序仍然受 SELinux 和权限限制，常见做法还是通过系统组件、root / userdebug 设备，或 AOSP 构建出来的专用工具去加载。

### AOSP 中 eBPF 程序的位置

按 android-16.0.0_r1 去看，能直接落到源码文件的目录主要是下面几处：

| 路径 | 这里放的是什么 | 本章要用到的观察点 |
|---|---|---|
| `system/bpf/` | Android 的 BPF loader、共享头文件和基础框架 | 系统级 BPF 能力的装载入口 |
| `packages/modules/UprobeStats/src/bpf_progs/` | UprobeStats 随模块下发的 BPF 程序，如 `BitmapAllocation.c`、`GenericInstrumentation.c`、`MalwareSignal.c`、`ProcessManagement.c` | 动态埋点与 user space instrumentation 的主线源码 |
| `frameworks/native/services/gpuservice/bpfprogs/gpuMem.c` | GPU 内存统计用的 BPF 程序 | GPU memory tracking 的具体实现锚点 |

`netd` 确实大量使用 BPF maps 和程序，但在 android-16.0.0_r1 中，`system/netd/bpf_progs/` 不是可直接定位到源码文件的目录。`frameworks/base/services/core/jni/` 里也没有适合作为本章锚点的 BPF program，它更接近 JNI bridge 和服务侧 native 代码。写 AOSP 路径时，最好把“谁在使用 BPF”和“BPF 程序源码放在哪里”拆开。

[已验证: AOSP android-16.0.0_r1]

## Simpleperf 与 eBPF 的结合

我们在 14.2 节已经介绍过 Simpleperf 作为 Android 原生 CPU profiling 工具的基础用法。这里聚焦 Simpleperf 与 eBPF 相关的能力——uprobe 和 kprobe 动态追踪。


### uprobe：追踪用户态函数

Simpleperf 记录 uprobe 时，事件选择更稳的写法是 `-e probe:<event_name>`，探针定义仍通过 `--uprobe` 传入。示例：

```bash
# 第一步：获取函数符号地址
unwind_info /system/lib64/libc.so | grep "kill"
# PC 0xbfea0-0xbfeb8 <kill>

# 第二步：定义 uprobe 并录制它
simpleperf record --app com.example.app -g \
  -e probe:libc_kill \
  --uprobe 'p:libc_kill /system/lib64/libc.so:0xbfea0' \
  -o /data/local/tmp/perf.data
```

这里 `probe:libc_kill` 是录制事件名，`--uprobe` 里的 `p:libc_kill ...` 负责把探针挂到目标 ELF 和偏移上。若要记录返回点，可以把定义改成 `r:<event_name>` 或 `%return` 形式。

这类探针适合追踪 JNI 边界、闭源 `.so` 的关键函数、低频控制路径调用次数等场景。若目标函数本身已经很热，再叠加栈回溯、参数抓取或 ring buffer 写出，探针成本会很快放大。

[图：Simpleperf uprobe 追踪 libc.so:kill 的输出示例——展示调用栈和采样热点分布]

[来源: Cubox/simpleperf的使用技巧-2025-11-18.md]

### kprobe：追踪内核函数

Simpleperf 也支持 `--kprobe`，事件名同样建议用 `probe:` 前缀：

```bash
# 追踪文件打开操作
simpleperf record -a -g --duration 30 \
  -e probe:open_entry \
  --kprobe "p:open_entry do_sys_open" \
  -o /data/local/tmp/perf.data

# 追踪特定大小的内存分配
simpleperf record -e probe:system_heap_alloc \
  --kprobe "p:system_heap_alloc system_heap_do_allocate len=%x1" \
  --tp-filter "len == 49942528" \
  --call-graph dwarf -a \
  -o /data/cam5.data
```

第二个例子展示了 kprobe 的高级用法：不仅追踪函数调用，还通过 `len=%x1` 读取第一个参数的值，然后用 `--tp-filter` 过滤出特定大小的分配。这种"在内核中过滤"的方式避免了大量无关事件传到用户态，保持了低开销。

[来源: Cubox/simpleperf的使用技巧-2025-11-18.md]

### 实战示例：追踪 RenderThread 帧耗时

一个典型的 Android 性能分析场景：我们想知道 RenderThread 每一帧的 `eglSwapBuffers` 调用耗时。使用 bpftrace（eBPF 的高层前端）可以这样做：

> ⚠️ bpftrace 不是 Android 标准工具链的一部分，需要在设备上单独编译安装（或使用 userdebug/eng 版本中预装的版本）。在生产环境分析中，更推荐使用 Simpleperf 的 `probe:` 事件配合 `--uprobe` 定义探针。

```bash
# 找到 eglSwapBuffers 在 libEGL.so 中的符号
# 然后用 bpftrace 统计每次调用的时间间隔
bpftrace -e 'uprobe:/system/lib64/libEGL.so:eglSwapBuffers
  { @swap_interval = stats(nsec - @last_swap); @last_swap = nsec; }'
```

bpftrace 的 `stats()` 函数会自动计算均值、方差、最大值、最小值。比起用 Systrace 手动标记每一帧，这种方式更高效，而且每次 uprobe 触发只执行几条指令。

[图：bpftrace stats() 输出示例——展示 eglSwapBuffers 调用间隔的均值 / 方差 / 分位数]

[来源: Cubox/ebpf在 Android 上的玩法示例-2025-12-22.md]


## UprobeStats 与动态埋点

Android 15 引入的 UprobeStats 是 eBPF 在 Android 上的一个代表性使用场景。它利用 uprobe 机制做“无需改业务代码”的动态埋点：系统按配置 attach 到目标方法，把命中事件写进 BPF map / ring buffer，再汇总给 StatsD。

### UprobeStats 的工作原理

UprobeStats 以 APEX 模块形式集成（`/system/apex/com.android.uprobestats.apex`），核心组件包括：

- `uprobestats`：主执行程序，负责读取配置、解析方法偏移、attach BPF 程序、收集数据
- `uprobestatsbpfload`：BPF 程序加载器，开机时加载预编译的 eBPF 程序到内核
- `etc/bpf/*.o`：预编译的 BPF 程序模板（BitmapAllocation、GenericInstrumentation、ProcessManagement）
- `libuprobestats_client.so`：提供给 StatsD 动态加载的客户端库

整个流程如下：

1. StatsD 检测到特定订阅触发，调用 `StartUprobeStats()`
2. 配置写入 `/data/misc/uprobestats-configs/config`
3. 通过系统属性 `uprobestats.start_with_config` 触发启动
4. `uprobestats` 进程启动后读取配置，通过 `oatdump` 或 `DynamicInstrumentationManagerService` 解析目标方法在 OAT / ODEX 文件中的偏移地址
5. 对每个目标方法调用 `bpfPerfEventOpen()` attach BPF 程序并启用 uprobe
6. collector 线程在 RINGBUF map 上 poll，读取 BPF 程序写入的数据
7. 采集结果组装成 `AStatsEvent` 原子埋点上报给 StatsD

[图：UprobeStats 端到端数据流——StatsD 订阅触发 → 配置解析 → BPF attach → RingBuf 读取 → StatsD 上报]

[来源: Cubox/探索Android动态埋点的新视界：UprobeStats深度解析-2025-02-21.md]
[已验证: AOSP, packages/modules/UprobeStats/src/]

### 预置的 BPF 程序

AOSP 中 UprobeStats 预置了三类 BPF 程序模板：

**GenericInstrumentation.c** 是通用模板，负责提取寄存器上下文、拿时间戳、把采集结果写到 ring buffer。

**BitmapAllocation.c** 用于追踪 Bitmap 分配相关调用，偏向计数和事件采样。

**ProcessManagement.c** 面向特定系统方法，直接按 ART / ABI 约定读取参数。

### 频率边界与性能陷阱

uprobe 命中一次，至少会经历用户态 → 内核态 → 用户态这条路径；如果还要做 map 更新、ring buffer 写出、参数提取或栈回溯，成本会继续往上叠。社区基准里，简单 uprobe 常见就已经到微秒级。对冷路径和低频控制流，这个代价通常可接受；对每帧、每次分配、锁热路径或高频 JNI 边界，探针本身就可能改写工作负载。

UprobeStats 更适合低频关键路径、系统服务里的诊断点、临时排障窗口。要挂到热点路径时，先估调用频率，再决定是否改成采样、加过滤，或缩小探针覆盖范围。

### 安全限制

UprobeStats 有严格的安全限制。在 user 版本上，仅允许监控特定类前缀的方法：

```cpp
constexpr std::array kAllowedMethodPrefixes = {
    "com.android.server.am.CachedAppOptimizer",
    "com.android.server.am.OomAdjuster",
    "com.android.server.am.OomAdjusterModernImpl",
};
```

非 user 版本（userdebug / eng）没有这组限制。这套白名单把动态埋点约束在系统自管范围内，避免被滥用到任意用户应用。

## sched_ext 与可扩展调度器

sched_ext 是 Linux 6.12 合并的可扩展调度器类，它可能是 eBPF 对 Android 性能影响最深远的方向。

### 为什么需要可扩展调度器

Linux 内核的默认调度器（从 CFS 到 EEVDF）追求通用性——在各种工作负载下都"还行"。但"还行"和"最优"之间有巨大的差距。一个具体的例子：

在 big.LITTLE 架构上，如果进程 A 频繁通过 pipe 唤醒进程 B，默认调度器可能把它们放在不同的 cluster 上。跨 cluster 的 cache 同步开销远高于 cluster 内部，导致通信性能下降。如果把 A 和 B 手动放在同一个 cluster，pipe 吞吐量会有显著提升（取决于 cache 大小和 cluster 拓扑，实测中可能有显著差异 [待验证: 来源为 sched_ext 社区实验数据，具体取决于 cache 大小和 cluster 拓扑]）。

这种"针对特定场景的手动调度优于通用调度器"的情况在实践中反复出现。但在 sched_ext 之前，定制调度策略只有两条路：向内核打补丁（SCHED_CLUSTER 从提交到合入主线花了 2 年），或者让应用开发者用 `sched_setattr()` 表达需求（开发者往往不知道怎么表达，甚至乱表达）。

sched_ext 打开了第三条路：通过 eBPF 程序实现自定义调度策略，运行时动态加载和切换，无需重启系统。

[来源: Cubox/基于eBPF的sched-ext会在产品成功的底层逻辑是什么-2025-10-18.md]

### sched_ext 的架构

sched_ext 在调度优先级栈中位于 SCHED_IDLE 和 SCHED_NORMAL 之间。它管理 SCHED_NORMAL/BATCH/IDLE/EXT 任务，而 SCHED_FIFO/RR/DEADLINE 等实时调度类不受影响。

关键设计特征：

- **BPF 驱动调度决策**：任务选择、CPU 迁移、时间片分配等决策由用户态编写的 BPF 程序完成。调度器的核心逻辑从内核代码变成了可动态加载的 BPF 程序。

- **安全兜底**：Bypass Mode 机制——当检测到 BPF 调度器出错或任务停滞时，自动回退到简单的 FIFO 调度器，确保系统不会挂死。这是 sched_ext 可以在生产环境使用的基础。

- **部分切换**：`SCX_OPS_SWITCH_PARTIAL` 标志允许只将明确设置为 SCHED_EXT 的任务交给 BPF 调度器管理，其余任务继续使用默认调度器（EEVDF）。这种渐进式部署方式降低了风险。

- **sched_deadline Server**：为防止 RT 任务饿死 sched_ext 任务，引入了 deadline server 机制。

[已验证: kernel.org Documentation, scheduler/sched-ext]
[来源: intake/research-feeds/2026-04-02-15-ch05-sched-ext-bpf-android.md]


### 对 Android 的意义

Meta 和 Google 都在持续投入 sched_ext。Meta 的 Oculus 团队已经在 Android 移植版上实验 sched_ext，Google 也在把 ghOSt 这类调度实验往 sched_ext 方向收拢。

一些已有的实验性调度器展示了它的空间：

- **scx_bpfland**：把大部分调度策略写在 BPF 用户态组件里，便于快速迭代。
- **scx_flash**：面向低延迟交互负载，强调 wakeup latency 和交互稳定性。
- **scx_rustland**：在游戏等持续负载场景里验证帧稳定性收益。
- **scx_chaos**：故意注入调度抖动，用来暴露竞态和时序依赖问题。

放到 Android 平台上，先要看 GKI 版本时间线。官方 release builds 已经给出比较清楚的映射：Android 14 对应 `android14-6.1`，Android 15 对应 `android15-6.6`，Android 16 对应 `android16-6.12`。因此，`sched_ext` 真正开始具备平台侧评估条件，是 Android 16 / GKI 6.12 这一代，不是 Android 17 才第一次出现。

这只解决了“底层内核版本够不够”的问题。设备上能不能真正启用，还要继续看内核配置、CTS / VTS、OEM 适配、功耗与稳定性回归，以及是否允许在 shipping build 中开放相应能力。

[来源: intake/research-feeds/2026-04-03-07-sched-ext-bpf-scheduler.md + Android GKI release builds]

## eBPF 在 Android 性能分析中的实战场景

### CPU 利用率精准计算

传统方式通过读 `/proc/stat` 获取 CPU 利用率，精度受限于 Tick 频率（通常 250Hz 或 1000Hz，即 4ms 或 1ms）。而且 `/proc/stat` 的数据来自 `account_process_tick()`，只在时钟中断时更新——如果一个任务在两次 Tick 之间跑了很多短任务，这些时间会被归入下一次 Tick 的统计中。

eBPF 通过挂载到 `sched_switch` tracepoint，在每次上下文切换时精确记录前一个任务的运行时间和当前任务开始运行的时间戳。精度从 Tick 级别（4ms）提升到纳秒级（ns）。

实际效果：在 120Hz 屏幕上，一帧只有 8.33ms。Tick 级精度可能把 2-3 帧的 CPU 时间混在一起，而 eBPF 可以精确区分每一帧的 CPU 使用量。

[图：/proc/stat Tick 级精度 vs eBPF sched_switch 纳秒级精度的对比——同一 workload 下两种方式给出的 CPU 使用率差异]

[来源: Cubox/基于eBPF的CPU利用率精准计算小工具开发-2022-03-13.md]

### 系统调用延迟追踪

通过 eBPF 挂载到 `raw_syscalls:sys_enter` 和 `raw_syscalls:sys_exit` tracepoint，可以精确测量每个系统调用的延迟分布：

```bash
# 用 simpleperf 追踪特定系统调用
simpleperf record -a -g -c 1 \
  -e "raw_syscalls:sys_enter" \
  --tp-filter 'id == 94 || id == 93 || id == 424 || id == 129 || id == 130' \
  -o /data/perf.data
```

这比 strace 快几个数量级——eBPF 在内核中直接记录，不需要像 strace 那样在每次系统调用时暂停和恢复目标进程。

[来源: Cubox/simpleperf的使用技巧-2025-11-18.md]

### I/O 延迟分布统计

通过 eBPF 挂载到 block 层的 tracepoint（如 `block:block_rq_issue` 和 `block:block_rq_complete`），可以统计每次 I/O 请求的延迟，生成延迟分布直方图。这对分析存储性能（特别是 eMMC/UFS 的随机 I/O 性能）非常有用。

[图：eBPF I/O 延迟直方图——block_rq_issue 到 block_rq_complete 的延迟分布，区分读/写/Sync]

### 进程异常退出监控

AOSP 中有使用 eBPF 监控 signal 发送和接收的示例，通过追踪 `signal_generate` 事件来监控系统中的信号传递，帮助诊断进程被杀的原因。

[来源: Cubox/aosp15进程异常退出监控工具-ebpf监控signal的发送和接收-2025-12-25.md]

### Binder 调用追踪

使用 Simpleperf 的 tracepoint 过滤能力，可以追踪特定类型的 Binder 事务：

```bash
# 追踪发送到冻结 App 的异步 Binder 事务
simpleperf record -a -g --exclude-perf \
  -e binder:binder_return \
  --tp-filter "cmd == 0x7212 || cmd == 0x7214"
```

其中 `kBR_FROZEN_REPLY = 0x7212` 和 `kBR_TRANSACTION_PENDING_FROZEN = 0x7214` 分别代表"目标进程已冻结"的场景。这种追踪对分析 App 冻结/解冻相关的性能问题很有价值。

[来源: Cubox/simpleperf的使用技巧-2025-11-18.md]


## 常见问题与误区

**误区：eBPF 可以在任何 Android 设备上使用。**
实际情况：非 GKI 设备上，BTF、helper、内核版本和配置都可能不满足；即使是 GKI 设备，user build 上的自定义 eBPF 加载仍然受 SELinux 和权限限制。自定义 tracing 通常还是需要 userdebug / eng 或 root。

**误区：eBPF 对性能完全没有影响。**
实际情况：eBPF 程序可以很轻，但开销没有固定常数。helper 调用、map 类型、ring buffer 写出、栈回溯和 probe 频率都会改变结果。尤其是 uprobe / uretprobe，每次命中都要跨一次用户态和内核态边界；方法一热，累计代价就会非常明显。

**误区：bpftrace 可以直接在 Android 上使用。**
实际情况：bpftrace 不是 Android 标准工具链的一部分，通常需要单独构建。Android 上更实用的路径，是用 Simpleperf 的 `probe:` 事件配合 `--uprobe` / `--kprobe` 定义探针，或者直接走 AOSP 自带的 BPF loader / 系统模块能力。

**误区：sched_ext 已经在 Android 上普遍可用了。**
实际情况：`sched_ext` 需要 Linux 6.12+。平台基线已经走到 Android 16 的 GKI 6.12，但这不等于所有 Android 16 设备都会启用它，更不等于所有 OEM 都会把它开放给日常性能分析。

## 限制与注意事项

### 非 root / 非 debug 设备的限制

在 user 版本的 Android 设备上，加载自定义 eBPF 程序受到 SELinux 策略的严格限制。普通 App 无法加载 eBPF 程序——只有系统服务（通过 BPF loader）和特定模块（如 UprobeStats）才能加载。要进行自定义 eBPF 追踪，通常需要 userdebug/eng 版本的设备，或者通过 adb root 获取 root 权限。


### 性能开销

虽然 eBPF 程序经过 JIT 后通常只做很短的工作，但开销仍然要按 probe 类型拆开看。tracepoint 和 kprobe 常见是“回调很短、频率决定总代价”；uprobe / uretprobe 额外多一层用户态与内核态切换，若再叠加参数抓取、map 更新、ring buffer 写出或栈回溯，单次成本很快就会从亚微秒抬到微秒级。

经验做法是先估频率，再定粒度。万次每秒以下的 probe 更容易控住；到了十万次、百万次每秒，过滤条件、采样率、写出路径和 trace 时长都要先压住。热点路径上，探针本身就可能把吞吐、尾延迟或 trace 体积推到不可接受的区间。

### 与 SELinux 的交互

Android 的 SELinux 策略严格控制 eBPF 相关操作。`bpf()` 系统调用、BPF map 的读写、perf_event 的创建都需要对应的 SELinux 权限。在自定义 eBPF 追踪方案中，可能需要调整 SELinux 策略（仅在 userdebug/eng 版本上可行）。

### 调试的挑战

eBPF 程序运行在内核态，调试手段有限。不能像用户态程序那样打断点、插入打印日志。常用的调试方法：

- `bpf_trace_printk()`：在 BPF 程序中输出调试信息到 `trace_pipe`（仅限开发调试）
- bpftool：查看已加载的 BPF 程序和 maps
- 日志：通过 BPF map 将调试信息传到用户态程序输出

## 与其他章节的关联

- **5.1 Linux 进程调度基础**：sched_ext 的 BPF 调度器是调度器架构演进的重要方向
- **14.2 Simpleperf**：Simpleperf 的 uprobe/kprobe 功能是 eBPF 在性能分析中最直接的入口
- **13.1 Perfetto 简介**：Perfetto 的 tracepoint 数据源部分依赖 eBPF 采集的数据
- **1.14 锁竞争**：eBPF 的 uprobe 可以用于追踪锁的获取和释放时序
- **4.6 内存版本演进**：eBPF 的 `gpu_mem` 程序追踪 GPU 内存使用量，与内存管理直接关联
- **16.4 Android 17 系统级优化**：sched_ext 是 Kernel 6.12 的核心特性，GKI 升级时间线直接影响 eBPF 在 Android 上的可用性

## 参考资料

- AOSP eBPF 文档：https://source.android.com/docs/core/architecture/kernel/bpf
- AOSP UprobeStats BPF 程序：https://cs.android.com/android/platform/superproject/main/+/main:packages/modules/UprobeStats/src/bpf_progs/
- AOSP GPU memory BPF 程序：https://cs.android.com/android/platform/superproject/main/+/main:frameworks/native/services/gpuservice/bpfprogs/gpuMem.c
- Linux kernel sched_ext 文档：https://kernel.org/doc/html/latest/scheduler/sched-ext.html
- sched-ext 项目：https://github.com/sched-ext/scx
- Cubox/在 Android 中使用 eBPF：开篇-2022-06-12.md
- Cubox/探索Android动态埋点的新视界：UprobeStats深度解析-2025-02-21.md
- Cubox/基于eBPF的sched-ext会在产品成功的底层逻辑是什么-2025-10-18.md
- Cubox/基于eBPF的CPU利用率精准计算小工具开发-2022-03-13.md
- Cubox/simpleperf的使用技巧-2025-11-18.md
- Cubox/ebpf在 Android 上的玩法示例-2025-12-22.md
