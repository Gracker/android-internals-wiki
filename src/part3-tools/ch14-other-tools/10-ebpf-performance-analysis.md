---
title: "eBPF/BPF 在 Android 性能分析中的应用"
chapter: "14.10"
section: "14.10"
status: ready-for-review
drafted_date: "2026-04-07"
drafted_by: "openclaw-task2a"
applicable_versions: "Android 10 (API 29) - Android 17 (API 37)"
last_verified: "2026-04-07"
last_verified_against: "AOSP android-16.0.0_r1 + kernel.org sched-ext docs"
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
reviewed_date: "2026-04-14"
task6_result: needs-rework
task9_result: needs-rework
task9_reviewed_date: "2026-04-20"
task9_reviewed_by: "openclaw-task9"
last_task9_at: "2026-04-20T21:48:59+08:00"
task2b_result: fixed
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

eBPF 是 Linux 内核中的一个轻量级虚拟机。它的核心思想很简单：在内核中运行一段经过验证的安全小程序，这段程序可以挂载到内核的各种事件点（系统调用、内核函数、网络包、硬件事件等），在事件触发时执行自定义的逻辑——比如记录时间戳、统计计数、收集调用栈。

eBPF 与传统的性能分析工具（perf、strace、ftrace）工作机制完全不同：

**strace** 基于 ptrace，会在每次系统调用时暂停目标进程、收集信息、再恢复执行。这种"断点式"的追踪方式开销很高——开启 strace 后，程序性能可能下降数倍甚至一个数量级，而且很多应用会检测 ptrace 环境并拒绝运行。

**perf** 基于 `perf_event_open` 系统调用，通过硬件 PMU 采样来统计 CPU 热点。它的优势是开销较低（通常 <5% [待验证: 来源为 perf 社区经验数据，实际取决于采样频率和事件类型]），但只能看到"采样到"的函数，无法追踪特定事件的发生次数和精确时间。

**ftrace** 是内核的内置追踪框架，功能强大但需要 root 权限和 debugfs 访问，在用户设备上基本不可用。

eBPF 的工作方式完全不同。它的事件处理程序运行在内核态，由 JIT 编译为本机指令，执行效率接近原生代码。同时，eBPF 程序在加载时会经过内核验证器的严格安全检查——确保不会死循环、不会越界访问内存、不会导致内核 panic。这种"安全 + 高效"的组合，在 eBPF 出现之前是不存在的。

[图：eBPF 与传统性能分析工具的对比——从开销、精度、安全性、适用场景四个维度]

对 Android 来说，GKI（General Kernel Image）的出现让 eBPF 真正可用。在 GKI 之前，不同设备的内核编译选项千差万别，eBPF 的核心功能（如 BTF 类型信息）在很多设备上根本不可用。Android 12 开始强制要求设备使用 GKI 内核，而 GKI 内核完整支持 eBPF 的几乎所有功能。这样一来，在一台 GKI 设备上编写的 eBPF 程序，可以在任何其他 GKI 设备上运行。

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

eBPF 程序的一个传统难题是内核版本兼容性。不同内核版本的结构体布局可能不同，直接硬编码偏移量会导致程序在新内核上崩溃。BPF CO-RE（Compile Once, Run Everywhere）通过 BTF（BPF Type Format）解决了这个问题：编译时记录"需要访问哪些字段"，运行时根据当前内核的 BTF 信息自动重定位。

对 Android 来说，CO-RE 的意义特别重大：GKI 统一了核心内核，所以 CO-RE 程序可以在所有 GKI 设备上无缝运行，不需要为每个内核版本单独编译。不过目前 Android 上直接从 App 加载自定义 eBPF 程序仍然受限，通常需要通过 adb shell 或编译自定义的可执行文件来运行。

[待验证: Android 17 是否开放了 App 级 eBPF 程序加载 API]

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

Google 在 Simpleperf 中增加了 `--uprobe` 选项，允许在不修改目标代码的情况下追踪指定函数的调用。这在分析闭源库（如 GPU 驱动、系统 .so）的行为时特别有用。

使用步骤分两步：先找到目标函数在 .so 中的偏移地址，然后用 Simpleperf 设置 uprobe 事件。

```bash
# 第一步：获取函数符号地址
unwind_info /system/lib64/libc.so | grep "kill"
# PC 0xbfea0-0xbfeb8 <kill>

# 第二步：设置 uprobe 追踪
simpleperf record --app com.example.app -g \
  -e "uprobes:myret" \
  --uprobe 'p:myret /system/lib64/libc.so:0xbfea0' \
  -o /data/perf.data
```

这段命令在 `libc.so` 的 `kill` 函数入口处设置了一个 uprobe 探针。每当 App 调用 `kill` 时，Simpleperf 就会记录一次采样，包含完整的调用栈。

[图：Simpleperf uprobe 追踪 libc.so:kill 的输出示例——展示调用栈和采样热点分布]

实际应用场景：追踪 App 的线程创建（pthread_create）、追踪 Binder 调用（binder 相关函数）、追踪特定 JNI 函数的调用频率和耗时。

[来源: Cubox/simpleperf的使用技巧-2025-11-18.md]

### kprobe：追踪内核函数

Simpleperf 也支持 `--kprobe` 选项，追踪内核函数：

```bash
# 追踪文件打开操作
simpleperf record -a -g --duration 30 \
  -e "kprobes:myprobe" \
  --kprobe "p:myprobe do_sys_open" \
  -o /data/local/tmp/perf.data

# 追踪特定大小的内存分配
simpleperf record -e "kprobes:myprobe" \
  --kprobe "p:myprobe system_heap_do_allocate len=%x1" \
  --tp-filter "len == 49942528" \
  --call-graph dwarf -a \
  -o /data/cam5.data
```

第二个例子展示了 kprobe 的高级用法：不仅追踪函数调用，还通过 `len=%x1` 读取第一个参数的值，然后用 `--tp-filter` 过滤出特定大小的分配。这种"在内核中过滤"的方式避免了大量无关事件传到用户态，保持了低开销。

[来源: Cubox/simpleperf的使用技巧-2025-11-18.md]

### 实战示例：追踪 RenderThread 帧耗时

一个典型的 Android 性能分析场景：我们想知道 RenderThread 每一帧的 `eglSwapBuffers` 调用耗时。使用 bpftrace（eBPF 的高层前端）可以这样做：

> ⚠️ bpftrace 不是 Android 标准工具链的一部分，需要在设备上单独编译安装（或使用 userdebug/eng 版本中预装的版本）。在生产环境分析中，更推荐使用 Simpleperf 的 `--uprobe` 方案。

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

Android 15 引入的 UprobeStats 是 eBPF 在 Android 上的一个代表性使用场景。它利用 eBPF 的 uprobe 机制实现了"零代码侵入"的动态埋点——不需要在 Framework 代码中插入统计逻辑，只需编写一个配置文件指定要监控的 Java 方法，系统就会自动采集执行数据并上报给 StatsD。

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
4. `uprobestats` 进程启动后读取配置，通过 `oatdump` 或 `DynamicInstrumentationManagerService` 解析目标方法在 OAT/ODEX 文件中的偏移地址
5. 对每个目标方法调用 `bpfPerfEventOpen()` attach BPF 程序并启用 uprobe
6. 启动 collector 线程，在 RINGBUF map 上 poll，读取 BPF 程序写入的数据
7. 将采集到的数据组装成 `AStatsEvent` 原子埋点上报给 StatsD

[图：UprobeStats 端到端数据流——StatsD 订阅触发 → 配置解析 → BPF attach → RingBuf 读取 → StatsD 上报]

[来源: Cubox/探索Android动态埋点的新视界：UprobeStats深度解析-2025-02-21.md]
[已验证: AOSP, packages/modules/UprobeStats/src/]

### 预置的 BPF 程序

AOSP 中 UprobeStats 预置了三类 BPF 程序模板：

**GenericInstrumentation.c** 是最通用的模板，包含两个 BPF 程序。`call_detail` 程序捕获调用线程上下文的所有寄存器数据（包括 PC），通过配置中指定的寄存器位置提取 Java 方法参数；`call_timestamp` 程序获取当前系统时间（mono clock），用于精确测量方法执行时间。

**BitmapAllocation.c** 用于追踪 Bitmap 分配行为。当 attach 的 Java 方法被调用时触发，RINGBUF map 保存一个固定标记（123），主要用于统计调用次数。

**ProcessManagement.c** 是专用程序，仅适用于 `OomAdjuster#setUidTempAllowlistStateLSP` 方法。BPF 程序通过 ART Native 调用约定的寄存器（x2 = uid，x3 = onAllowlist）直接读取方法参数。

### 安全限制

UprobeStats 有严格的安全限制。在 user 版本上，仅允许监控特定类前缀的方法：

```cpp
constexpr std::array kAllowedMethodPrefixes = {
    "com.android.server.am.CachedAppOptimizer",
    "com.android.server.am.OomAdjuster",
    "com.android.server.am.OomAdjusterModernImpl",
};
```

非 user 版本（userdebug/eng）没有此限制。这种设计保证了 UprobeStats 不会被滥用于监控任意用户应用。

[来源: Cubox/探索Android动态埋点的新视界：UprobeStats深度解析-2025-02-21.md]

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

Meta 和 Google 都在持续投入 sched_ext。Meta 的 Oculus 团队已经在 Android 移植版上实验 sched_ext，Google 也计划把 ghOSt 调度框架迁移到 sched_ext。

一些已有的实验性调度器展示了 sched_ext 的潜力：

- **scx_lavd**（Latency-criticality Aware Virtual Deadline）：专为游戏工作负载设计，通过感知 waker/wakee 关系和任务 runtime 来调整延迟需求，在游戏中展示了 FPS 提升。

- **scx_rustland**：在游戏中（如 Terraria）展示了即使有其他重负载（如内核编译）运行也能保持 FPS 稳定。

- **scx_chaos**：故意引入延迟和性能下降，帮助暴露应用中的竞态条件和时序依赖错误。

对 Android 性能工程师来说，如果 sched_ext 在 Android 上可用（需要 GKI 内核 6.12+），就可以针对特定场景编写定制调度器，例如 UI 主线程的调度延迟优化、后台任务的 CPU 放置策略、游戏场景的帧率稳定性保障。而且这一切不需要修改内核源码，只需要编写和加载 BPF 程序。

不过，Android 上的大规模部署还需要时间，需要等待平台内核升级到 6.12，通过 Android 兼容性测试，再由 OEM 完成适配。

[来源: intake/research-feeds/2026-04-03-07-sched-ext-bpf-scheduler.md]
[待验证: Android 17 GKI 是否正式包含 Kernel 6.12]

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
实际情况：非 GKI 设备上 eBPF 功能严重受限（缺少 BTF、内核版本过低）。即使是 GKI 设备，在 user 版本上加载自定义 eBPF 程序也受 SELinux 策略限制。自定义 eBPF 追踪通常需要 userdebug/eng 版本或 root 权限。

**误区：eBPF 对性能完全没有影响。**
实际情况：eBPF 回调通常很轻，但开销没有一个跨设备通用常数。probe 类型、helper 调用次数、map 访问、ringbuf 写入、栈回溯和内核版本都会把成本拉开。事件频率一高，哪怕单次开销不大，累计代价也会很快显现。使用前先估目标事件频率，再决定是全量追踪、采样，还是加过滤条件。

**误区：bpftrace 可以直接在 Android 上使用。**
实际情况：bpftrace 不是 Android 标准工具链的一部分，需要从源码编译或使用第三方构建。Android 上更实际的做法是使用 Simpleperf 的 `--uprobe`/`--kprobe` 选项，或者通过 AOSP 构建系统编译自定义 eBPF 程序。

**误区：sched_ext 已经在 Android 上可用了。**
实际情况：sched_ext 需要 Linux Kernel 6.12+，而截至 Android 17，GKI 内核版本为 6.6（Android 16）/ 6.12（Android 17 部分设备）。sched_ext 在 Android 上的大规模部署仍在早期阶段，需要等待平台内核升级和兼容性验证。

## 限制与注意事项

### 非 root / 非 debug 设备的限制

在 user 版本的 Android 设备上，加载自定义 eBPF 程序受到 SELinux 策略的严格限制。普通 App 无法加载 eBPF 程序——只有系统服务（通过 BPF loader）和特定模块（如 UprobeStats）才能加载。要进行自定义 eBPF 追踪，通常需要 userdebug/eng 版本的设备，或者通过 adb root 获取 root 权限。

### 性能开销

虽然 eBPF 程序经过 JIT 编译后通常只做很短的工作，常见 probe 回调往往落在纳秒到亚微秒量级，但这里没有固定的“100ns 标准答案”。helper 调用、map 类型、ringbuf 写入、符号解析、栈回溯和设备内核配置都会改变成本。如果事件频率极高，比如内存分配、调度切换或热点函数入口，累计开销仍然可能不可忽略。在 Perfetto 中，过密的 eBPF 事件也会让 trace 文件快速膨胀。

经验做法是先测频率，再决定追踪粒度。万次每秒以下的 uprobe/kprobe 往往更容易控制；到十万次、百万次每秒这个量级时，过滤条件、采样率和写出路径都要先压住。

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
