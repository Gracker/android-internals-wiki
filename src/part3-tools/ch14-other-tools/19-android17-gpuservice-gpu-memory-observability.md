---
title: "GpuService GPU 内存可观测性：GpuMem/eBPF 当前总量、GpuMemTracer/Perfetto 时间线与 GpuStats/statsd 驱动统计"
chapter: "14.19"
section: "14.19"
status: finalized
applicable_versions: "Android 12 (API 31) - Android 17 (API 37)"
tags: [GPU, GpuService, GpuMem, eBPF, Perfetto, statsd, memory-tracking, observability]
related_chapters: ["10.7", "14.15", "14.16", "14.23", "14.24", "14.25", "2.32"]
sources:
  - type: aosp
    tag: "android-17.0.0_r1"
    path: "frameworks/native/services/gpuservice/GpuService.cpp"
  - type: aosp
    tag: "android-17.0.0_r1"
    path: "frameworks/native/services/gpuservice/gpumem/GpuMem.cpp"
  - type: aosp
    tag: "android-17.0.0_r1"
    path: "frameworks/native/services/gpuservice/gpumem/include/gpumem/GpuMem.h"
  - type: aosp
    tag: "android-17.0.0_r1"
    path: "frameworks/native/services/gpuservice/bpfprogs/gpuMem.c"
  - type: aosp
    tag: "android-17.0.0_r1"
    path: "frameworks/native/services/gpuservice/tracing/GpuMemTracer.cpp"
  - type: aosp
    tag: "android-17.0.0_r1"
    path: "frameworks/native/services/gpuservice/tracing/include/tracing/GpuMemTracer.h"
  - type: aosp
    tag: "android-17.0.0_r1"
    path: "frameworks/native/services/gpuservice/gpustats/GpuStats.cpp"
  - type: aosp
    tag: "android-17.0.0_r1"
    path: "frameworks/native/services/gpuservice/gpustats/include/gpustats/GpuStats.h"
  - type: aosp
    tag: "android-17.0.0_r1"
    path: "hardware/interfaces/memtrack/aidl/android/hardware/memtrack/IMemtrack.aidl"
last_draft_polish_at: "2026-07-25T19:35:53+08:00"
last_draft_polish_run_id: "20260725-193553-draft-polish-1ef0e8ab"
last_deep_review_at: "2026-07-25T20:35:01+08:00"
last_deep_review_run_id: "20260725-203501-deep-review-1ef0e8ab"
task6_state: reviewed
task9_state: reviewed
pipeline_stage: finalized
last_verified: "2026-08-13"
last_verified_against: "AOSP android-17.0.0_r1 frameworks/native GpuService/GpuMem/GpuMemTracer/GpuStats + hardware/interfaces memtrack；Android common kernel android17-6.18-2026-06_r6 gpu_mem tracepoint；checked 2026-08-13"
last_review_finalize_at: "2026-07-25T22:08:43+08:00"
last_review_finalize_run_id: "20260725-220514-28dd4501"
confidence: high
---

# 14.19 GpuService GPU 内存可观测性架构

Android 17（`android-17.0.0_r1`）中，`frameworks/native/services/gpuservice/` 承载多条 GPU 观测路径。这里的“可观测性”是把驱动上报的数值和事件提供给诊断工具，不表示 GpuService 负责管理这些内存。

GPU 内存路径从 `gpu_mem_total` tracepoint（内核或驱动预先定义的静态追踪事件）开始。`gpuMem.c` 中的 BPF 程序读取事件，把每个 GPU 与进程最近上报的当前总量写入 map；`GpuMem` 再读取 map，通过 dumpsys 和 Perfetto 暴露结果。

`GpuStats` 是另一条路径，只记录 GL、Vulkan、ANGLE 驱动加载和图形功能使用信息，并通过 dumpsys 与 statsd（Android 系统统计守护进程）输出；它不记录 GPU 内存字节。buffer 的分配、复用与回收仍由 gralloc（系统与厂商之间的图形 buffer 分配接口）、图形实现和厂商驱动负责。

平台侧核验基线是 `android-17.0.0_r1`，内核侧核验基线是 `android17-6.18-2026-06_r6`。Android 12 至 Android 16 只用于说明能力演进。

## 14.19.1 三条并列观测链路：GPU 内存总量与驱动统计要分开

GpuService 中与 GPU 内存和驱动状态相关的主体分为三条链路。前两条描述 GPU 内存当前总量及其时间变化，第三条描述驱动加载和功能使用：

| 链路 | 组件 | 输入 | 输出 / 消费方 | 适合回答的问题 |
| --- | --- | --- | --- | --- |
| 当前总量 | `GpuMem` + `gpuMem.c` BPF 程序 | GPU 驱动发出的 `gpu_mem/gpu_mem_total` tracepoint | `dumpsys gpu --gpumem`、`traverseGpuMemTotals()` | 每个 `(gpu_id, pid)` 最近上报的当前总量是多少？ |
| Perfetto 时间线 | `GpuMemTracer` + ftrace | BPF map 起始值；驱动后续发出的 tracepoint | Perfetto 的初始 `gpu_mem_total_event` 与持续 `gpu_mem/gpu_mem_total` 更新 | trace 开始时占用多少，随后怎样变化？ |
| 驱动统计 | `GpuStats` | GL / Vulkan / ANGLE 驱动加载与功能使用上报 | statsd pull atom、`dumpsys gpu --gpustats` | 驱动加载是否成功、耗时多久、使用了哪些图形功能？ |

这三个通道术语分别表示：

- BPF map：内核 BPF 程序与用户态共享的键值表；
- ftrace：把内核 tracepoint 事件写入 trace 的追踪机制；
- statsd pull atom：statsd 在采集时向数据提供方主动拉取的结构化记录。

`GpuMem` 持有只读 BPF map，`GpuMemTracer` 通过 `GpuMem::traverseGpuMemTotals()` 遍历它，Perfetto 的 ftrace 更新来自驱动的同一个 tracepoint ABI（事件字段与布局约定）。排查 GPU 内存增长时，GpuMem 与 Perfetto 负责占用趋势，GpuStats 只补充驱动选择和失败模式。

## 14.19.2 GpuService 启动与初始化边界

`GpuService.cpp` 的构造函数同步创建核心对象，然后把可能阻塞的 BPF 初始化放到独立线程里。BPF 在这里指由内核校验后执行、用于处理 tracepoint 事件的小程序。下面的源码片段展示两条初始化线程：

```cpp
GpuService::GpuService()
    : mGpuMem(std::make_shared<GpuMem>()),
      mGpuWork(std::make_shared<gpuwork::GpuWork>()),
      mGpuStats(std::make_unique<GpuStats>()),
      mGpuMemTracer(std::make_unique<GpuMemTracer>()),
      mFeatureOverrideParser(kConfigFilePath) {
    mGpuMemAsyncInitThread = std::make_unique<std::thread>([this] {
        mGpuMem->initialize();
        mGpuMemTracer->initialize(mGpuMem);
    });
    mGpuWorkAsyncInitThread = std::make_unique<std::thread>([this] {
        mGpuWork->initialize();
    });
}
```

这段代码体现了三个边界：

1. `GpuMem → GpuMemTracer` 是串行依赖：`GpuMemTracer::initialize()` 要求传入的 `GpuMem` 已经初始化成功，否则不能从 BPF map 读取起始 counter（计数值）。
2. `GpuWork` 独立并行：GPU work period（GPU 工作时长区间）的 BPF 聚合与 GPU memory total 的 BPF 聚合是两条互补链路，这里只把 GpuWork 作为旁路观测来源。
3. 主服务构造不等待 BPF attach：attach 指把 BPF 程序挂到 tracepoint，使事件发生时执行该程序。`mGpuMem->initialize()` 会等待 bpfloader（系统 BPF 加载器），并可能等待 GPU tracepoint 出现；独立线程让构造函数先返回。

析构期会给 GpuMem 与 GpuWork 设置停止标志，再用 `join()` 等待两条初始化线程退出。成员对象随后析构，`GpuMem::~GpuMem()` 调用 `bpf_detach_tracepoint()`。

`stop()` 只会让 attach 重试循环退出。已经启动的 `GpuMemTracerThread` 是 detached thread（与创建者分离、不能再 `join()` 的线程），源码没有为它定义独立停止协议。gpuservice 通常与所在进程同寿命，不能把这段实现当作可反复创建和销毁的通用组件模板。

## 14.19.3 GpuMem：基于 eBPF 的进程级 GPU 内存快照

`GpuMem.h` 定义了 tracepoint，以及 pinned program 和 map 的路径。pinned object 是绑定到 BPF 文件系统路径的 BPF 对象，用户态进程可通过该路径重新打开它。下面是与初始化直接相关的常量：

```cpp
static constexpr char kGpuMemTraceGroup[]      = "gpu_mem";
static constexpr char kGpuMemTotalTracepoint[] = "gpu_mem_total";
static constexpr char kGpuMemTotalProgPath[]   =
    "/sys/fs/bpf/prog_gpuMem_tracepoint_gpu_mem_gpu_mem_total";
static constexpr char kGpuMemTotalMapPath[]    =
    "/sys/fs/bpf/map_gpuMem_gpu_mem_total_map";
static constexpr int  kGpuWaitTimeout          = 30;  // seconds
```

`GpuMem::initialize()` 的工作顺序是：

1. 调 `bpf::waitForProgsLoaded()` 等待系统 BPF 程序加载完成；
2. 从 `/sys/fs/bpf/prog_gpuMem_tracepoint_gpu_mem_gpu_mem_total` 取出 pinned BPF program 的 fd（文件描述符）；
3. 调 `bpf_attach_tracepoint(fd, "gpu_mem", "gpu_mem_total")` 绑定 GPU 驱动 tracepoint；
4. 如果 attach 失败且 `mStop` 未置位，每次失败后等待 1 秒再试；累计等待约 30 秒后，下一次 attach 仍失败便结束初始化，用来覆盖 GPU 驱动晚于 gpuservice 启动的窗口；
5. 用只读包装 `bpf::BpfMapRO<uint64_t, uint64_t>(kGpuMemTotalMapPath)` 打开 map，成功后把 `mInitialized` 置为 true。

用户态使用 `BpfMapRO`，表示 GpuService 只读；附着在 tracepoint 上的 BPF 程序负责更新。pinned object 的文件权限和 SELinux（Android 强制访问控制机制）规则仍参与访问控制，`BpfMapRO` 本身不负责判断驱动上报是否正确。

### BPF key 编码与 map 更新语义

内核 `android17-6.18-2026-06_r6` 的 `gpu_mem_total` tracepoint 规定：

- `pid == 0` 表示该 GPU 的全局总量；
- 正 PID 表示进程总量；
- `size` 是更新后的总字节数，不是本次分配的增量；
- 驱动在 GPU 可寻址空间发生 allocate、free、import 或 unimport 后发出事件；这里的 GPU 可寻址空间指已经映射、可由 GPU 访问的内存范围。

GpuService 的 BPF 程序把事件保存到 map。下面是删减后的片段，用中文注释省略了实际的 delete/update 语句，只展示容量、key 和零值删除语义：

```c
#define GPU_MEM_TOTAL_MAP_SIZE 1024

DEFINE_BPF_MAP_GRO(gpu_mem_total_map, HASH, uint64_t, uint64_t,
                   GPU_MEM_TOTAL_MAP_SIZE, AID_GRAPHICS);

struct gpu_mem_total_args {
    uint64_t ignore;
    uint32_t gpu_id;
    uint32_t pid;
    uint64_t size;
};

DEFINE_BPF_PROG("tracepoint/gpu_mem/gpu_mem_total", AID_ROOT, AID_GRAPHICS,
                tracepoint_gpu_mem_gpu_mem_total)
(struct gpu_mem_total_args* args) {
    uint64_t key = ((uint64_t)args->gpu_id << 32) | args->pid;
    uint64_t cur_val = args->size;
    /* cur_val == 0 时删除 key；否则 update / insert size */
}
```

key 是 `uint64_t = (gpu_id << 32) | pid`：高 32 位放 `gpu_id`，低 32 位放 `pid`。value 保存该 GPU / PID 组合最近一次上报的总字节数。`cur_val == 0` 时 BPF 程序删除 entry（map 中的一条键值记录）；若驱动完整遵守 tracepoint ABI，条目消失表示该组合已归零。

这里还有三个容易漏掉的限制：

1. tracepoint payload（事件携带的字段）只有 `gpu_id`、`pid`、`size`，没有 DMA-BUF inode、fd、buffer handle 或 allocation callsite。DMA-BUF 是 Linux 跨设备共享 buffer 的机制，inode 是内核对象标识，callsite 是触发分配的代码位置；
2. `GPU_MEM_TOTAL_MAP_SIZE = 1024` 限制的是 `(gpu_id, pid)` entry 数，pid 0 的全局 entry 也占一个位置；
3. 新 key 使用 `BPF_NOEXIST`（仅当 key 不存在时插入），程序没有检查插入返回值。map 填满后，新组合可能没有进入统计。

`dump()` 和 `traverseGpuMemTotals()` 通过 `getFirstKey()` / `getNextKey()` 逐项读取 map。遍历期间驱动仍可更新 map，因此输出是 best-effort（尽力而为、不同 entry 可能取自相邻时刻）快照，不具备跨 entry 的原子一致性；中途的 value 或 next-key 读取错误还会提前结束遍历。

GpuMem 能回答驱动最近上报的进程总量，无法指出哪一个 DMA-BUF 或 BufferQueue slot（队列中复用 buffer 的槽位）占用最大。

## 14.19.4 `dumpsys gpu`：即时查询入口

`GpuService.cpp::doDump()` 对 shell / dump 权限调用方开放，调用方需要满足 `uid == AID_SHELL` 或持有 `android.permission.DUMP`。常用命令如下：

C++ 组件名是 `GpuService`，注册到 ServiceManager（Binder 系统服务注册表）的服务名是 `gpu`：`GpuService::SERVICE_NAME = "gpu"`。`dumpsys` 按 Binder 服务名查找目标，因此命令入口是 `dumpsys gpu`。

| 命令 | 触发模块 | 用途 |
| --- | --- | --- |
| `dumpsys gpu` | dumpAll=true，全部模块输出 | 一次性查看 GameDriverInfo、GpuMem、GpuStats、GpuWork |
| `dumpsys gpu --gpumem` | `mGpuMem->dump()` | 只看 `(gpu_id, pid)` GPU 内存快照 |
| `dumpsys gpu --gpustats` | `mGpuStats->dump()` | 只看 GL / Vulkan / ANGLE 驱动加载统计 |
| `dumpsys gpu --gpudriverinfo` | GameDriverInfo | 查看 `ro.gfx.driver.*` 相关驱动信息 |
| `dumpsys gpu --gpuwork` | `mGpuWork->dump()` | 查看按 UID / GPU 聚合的 work period 统计 |

`GpuMem::dump()` 中的两个边界输出很适合排查启动问题：

- `Failed to initialize GPU memory eBPF`：`mInitialized` 为 false 或 BPF map 无效，通常意味着 BPF 程序、tracepoint attach 或初始化时序未完成；
- `GPU memory total usage map is empty`：源码在 `getFirstKey()` 返回任意错误时输出这句话。常见情况是 GPU 驱动尚未上报非零条目或当前没有活跃占用，但该字符串没有区分空 map 与其他 key 枚举错误。

排查建议：不要用单次 dumpsys 判断泄漏。`--gpumem` 是瞬时快照，应在场景前、中、后多次采样，关注同一 pid 的 `size` 是否随场景退出归零或回落。

## 14.19.5 GpuMemTracer 与 ftrace：初始值加后续更新

`GpuMemTracer` 把同一份 `GpuMem` map 作为 Perfetto 初始状态。下面的常量是 Android 17 注册的数据源名，配置时必须逐字匹配：

```cpp
static constexpr char kGpuMemDataSource[] = "android.gpu.memory";
```

该名称是 `android.gpu.memory`，下划线形式 `android.gpu_mem` 不对应这份源码。

初始化后，GpuMemTracer 向 system backend（系统 Perfetto tracing service）注册 data source，并启动分离的 `GpuMemTracerThread`。Perfetto 调用 `OnStart()` 时，线程执行一次 `traceInitialCounters()`。遍历到的每个 map entry 会形成一个 `GpuMemTotalEvent`：

```cpp
auto* event = packet->set_gpu_mem_total_event();
event->set_gpu_id(gpuId);
event->set_pid(pid);
event->set_size(size);
packet->set_timestamp_clock_id(
    perfetto::protos::pbzero::BUILTIN_CLOCK_MONOTONIC);
packet->set_timestamp(ts);
```

这段代码给 trace 提供起始基线。`traverseGpuMemTotals()` 在遍历每个 entry 时分别调用 `systemTime()`，所以各 packet（trace 数据包）的时间戳可能略有差异，整组数据也不是原子快照。

后续变化由 ftrace 的 `gpu_mem/gpu_mem_total` 事件提供。要得到从起点开始的时间序列，Perfetto 配置应同时启用初始 data source 和 ftrace 事件。下面是这两项的最小配置片段：

```textproto
data_sources {
  config {
    name: "android.gpu.memory"
    target_buffer: 0
  }
}

data_sources {
  config {
    name: "linux.ftrace"
    target_buffer: 0
    ftrace_config {
      ftrace_events: "gpu_mem/gpu_mem_total"
    }
  }
}
```

`android.gpu.memory` 写入 trace 启动时已有的非零 entry；`linux.ftrace` 记录会话期间驱动发出的更新。只启用前者会得到一次起始遍历，只启用后者可能缺少首次变化之前的基线。该链路由事件触发，不做固定周期 polling（定时读取）；驱动没有发出 tracepoint 时，轨道也不会变化。

## 14.19.6 GpuStats：statsd 驱动加载与功能使用统计

`GpuStats` 保存图形驱动加载和功能使用信息，不保存 GPU 内存字节数。GpuStats 通过 pull atom 在 statsd 请求时生成结构化统计记录。`GpuStats.h` 为自身内存占用设置了以下上限：

```cpp
static const size_t MAX_NUM_LOADING_TIMES = 16;
static const size_t MAX_NUM_APP_RECORDS   = 100;
static const size_t APP_RECORD_HEADROOM   = 10;
```

每个 App 的 GL、Vulkan 和 ANGLE loading-time（驱动加载耗时）数组各自最多保存 16 个样本。App 记录达到 100 条时，`purgeOldDriverStats()` 按 `lastAccessTime` 排序并删除最旧的 10 条，为后续记录预留空间。源码注释给出的目标是让 GpuStats 内存占用低于约 10KB。

Android 17 把 ANGLE 作为独立驱动类别。下面的分支累计全局加载次数和失败次数：

```cpp
case GpuStatsInfo::Driver::ANGLE:
    outGlobalInfo->angleLoadingCount++;
    if (!isDriverLoaded) outGlobalInfo->angleLoadingFailureCount++;
    break;
```

应用维度用 driver enum（驱动类别枚举值）或包名识别本次报告是否使用 ANGLE：

```cpp
appInfo.angleInUse =
    driver == GpuStatsInfo::Driver::ANGLE || driverPackageName == "angle";
```

现有记录再次收到 `insertDriverStats()` 时，`angleInUse` 会被这次判断覆盖，无法作为只增不减的历史标志。`angleLoadingCount` 与 `angleLoadingFailureCount` 可帮助解释驱动路径差异，不能证明 GPU 内存泄漏。

GpuStats 在第一次收到驱动或目标统计时，才向 statsd 注册 `GPU_STATS_GLOBAL_INFO` 与 `GPU_STATS_APP_INFO` 两个 pull callback（由 statsd 拉取时调用的回调）。每次 pull 成功返回后，对应的 `mGlobalStats` 或 `mAppStats` 都会被清空。

因此，一个 atom 只表示相邻两次 pull 之间累计的信息，不是开机以来永不清零的计数。

`dumpsys gpu --gpustats --global` 与 `--app` 可以限定输出；追加 `--clear` 会清除所选统计。`--clear` 会改变后续 dumpsys 和 statsd pull 的结果，采集证据前不要使用。

`toggleAngleAsSystemDriver(enabled)` 只允许 appId 为 `AID_SYSTEM` 且持有 `android.permission.ACCESS_GPU_SERVICE` 的调用方切换，开启时尝试写入持久系统属性 `persist.graphics.egl=angle`。

`/system/etc/angle/feature_config_vk.binarypb` 是另一条配置路径，其中 `binarypb` 表示二进制 protobuf 文件。`FeatureOverrideParser` 在 GpuService 构造期间解析一次并缓存，文件后续变化不会自动重载。系统驱动属性、feature override（功能覆盖配置）与 GpuStats 彼此有关联，但源码没有把它们实现成单向的三阶段处理链。

## 14.19.7 从进程总量走到 DMA-BUF

GpuMem 只有进程总量，没有 DMA-BUF 标识。要定位到具体 buffer，需要补充其他数据源：

| 数据源 | 统计口径 | 能回答的问题 |
| --- | --- | --- |
| `dumpsys gpu --gpumem` | 驱动上报的 `(gpu_id, pid)` 当前总量 | 哪个进程的 GPU 可寻址内存增长？ |
| `dumpsys meminfo <pid>` / memtrack HAL | Framework 内存核算中的 GL 与 Graphics | 未进入 smaps 的 GPU private 和 DMA-BUF PSS 有多少？ |
| `dmabuf_dump <pid>` | 进程持有或映射的 DMA-BUF | 哪些 DMA-BUF inode 被该进程引用？ |
| `dmabuf_dump -b` | 每个 buffer、exporter 和 device 的统计 | 大 buffer 来自哪个 exporter 或设备？ |
| `dumpsys SurfaceFlinger` / `--list` | 当前 layer 与合成状态 | 哪些 layer 与当前 buffer 状态可关联？ |
| Perfetto GPU memory | 初始总量和 tracepoint 更新 | 增长发生在哪个业务时间窗？ |

memtrack HAL 是厂商实现的设备内存核算接口，`dumpsys meminfo` 会使用其数据。`/proc/<pid>/smaps` 是按进程内存映射列出核算信息的内核接口，PSS（Proportional Set Size）把共享内存按引用者比例分摊。GPU private 指厂商 memtrack 按 GL 类别报告、未计入 smaps 的 GPU 私有分配，它不一定有 DMA-BUF identity。inode 是 DMA-BUF 的内核对象标识，exporter 是创建并导出该 DMA-BUF 的驱动或子系统。

`IMemtrack.aidl`（memtrack 的稳定 AIDL 接口定义）对核算口径有明确约束：

- `MemtrackType::GRAPHICS` 与 `FLAG_SMAPS_UNACCOUNTED` 应报告 CPU-mapped 与 GPU-mapped DMA-BUF 的 PSS，并去掉两组之间的重叠；
- `MemtrackType::GL` 与 `FLAG_SMAPS_UNACCOUNTED` 应报告指定 PID 下未计入 `/proc/<pid>/smaps` 的 GPU private allocation；
- PID 0 的 GL 查询应返回全局 GPU-private memory；PID 0 配合其他 type 应返回 0；
- 同一块内存不能同时计入两个 memtrack type。

因此，GpuMem、memtrack 与 DMA-BUF 统计的数字不要求相等。它们覆盖的对象、共享内存分摊方式和去重规则不同。严谨的表述应是“多种口径同时增长”或“某口径没有同步回落”，不能要求数字逐字节守恒。

Android 17 的 `dmabuf_dump` 来自 `system/memory/libmeminfo`。在 6.18 及更新内核上，VTS（Vendor Test Suite，供应商接口测试）要求 DMA-BUF BPF iterator 可用；iterator 是由 BPF 实现的内核对象遍历接口。

较早内核还可能通过 `CONFIG_DMABUF_SYSFS_STATS` 提供 per-buffer（逐 buffer）统计。这个 BPF iterator 与 GpuMem 的 `gpu_mem_total_map` 是两套独立机制。

下面这组命令先找增长进程，再查该进程引用的 DMA-BUF，最后结合 SurfaceFlinger layer 缩小范围。`dmabuf_dump` 读取其他进程和内核对象时通常需要 userdebug/eng（可调试的系统构建变体）环境与 root 权限。

```bash
app_id=com.example.game
pid=$(adb shell pidof -s "$app_id")
adb shell dumpsys gpu --gpumem
adb shell dumpsys meminfo "$pid"

# userdebug / eng 设备
adb root
adb wait-for-device
pid=$(adb shell pidof -s "$app_id")
adb shell dmabuf_dump "$pid"
adb shell dmabuf_dump -b

adb shell dumpsys SurfaceFlinger --list
adb shell dumpsys SurfaceFlinger
```

示例用 `com.example.game` 演示 PID 获取，运行时改成目标包名；多进程应用应指定执行图形工作的进程。`dumpsys gpu` 定位进程总量，meminfo 核对 Framework 内存分类，`dmabuf_dump` 给出 inode 与 exporter 线索，SurfaceFlinger 输出用于关联 layer。

`adb root` 会重启 adbd（设备侧 adb 守护进程），所以示例在 `adb wait-for-device` 后重新读取 PID。Android 17 的 `SurfaceFlinger::doDump()` 命令表没有 `--bufferstats`，不要依赖该参数。默认 SurfaceFlinger dump 也不是完整的 DMA-BUF 引用跟踪器，只能提供当前合成与 layer 上下文。

### 一次增长排查的时间顺序

1. 记录包名、PID、进程启动时间、GPU ID 和场景起止 marker（写入 trace 的阶段标记）；
2. 在场景前保存一次 `--gpumem`、meminfo 与 DMA-BUF 数据；
3. Perfetto 同时启用 `android.gpu.memory` 和 `gpu_mem/gpu_mem_total`；
4. 执行固定输入的场景，保留峰值和退出后的稳定窗口，即数值不再明显变化的一段时间；
5. 重复快照，确认增长来自 GPU private、DMA-BUF，或两者都有；
6. 用 DMA-BUF inode、exporter、进程引用与 SurfaceFlinger layer 缩小持有者范围；
7. 进程退出后核对旧 PID entry 是否删除，避免 PID 复用造成误判。

进程总量在场景结束后没有立即归零，也不自动构成泄漏。驱动缓存、对象延迟销毁、异步 fence（表示 GPU 或显示工作何时完成的同步对象）和进程仍存活都可能让内存暂时保留。判断依据应包含稳定窗口、多轮重复和对象生命周期证据。

## 14.19.8 各组件的职责边界

- `GpuService / GpuMem`：读取驱动上报的全局与进程 GPU 内存总量，不拥有这些 allocation（内存分配对象）。
- `GpuMemTracer / Perfetto ftrace`：提供 trace 起始值和会话内更新，用于观察时间变化。
- `GpuStats / statsd`：保存驱动加载、失败、耗时和图形功能使用信息；pull 后相应累计值清空。
- `memtrack HAL / dumpsys meminfo`：按 Framework 规则核算 GL、Graphics 和其他设备专属内存。
- `dmabuf_dump`：读取 DMA-BUF identity（对象标识）、exporter、device 与进程引用，是 buffer 级排查的主要补充。
- `SurfaceFlinger dump`：提供 layer 与合成状态，不能替代 DMA-BUF 引用分析。
- `gfxinfo / GraphicsStats`：报告帧耗时与 jank（掉帧或卡顿事件），不提供 GPU 内存总账。

§10.7 讨论应用与图形内存症状，§14.15 介绍 GPU 调试工具，§14.25 展开 eBPF 观测范围。这里的范围限于 GpuService、GPU memory tracepoint、GpuStats 和 DMA-BUF 对账之间的接口关系。

## 14.19.9 失败模式与结论强度

### GpuMem 初始化失败

初始化失败可能发生在 pinned program 获取、tracepoint attach 或 map 打开阶段。attach 会在约 30 秒内重试；超时后该 GpuMem 实例不会在后台无限重试，GpuMemTracer 也因 `isInitialized() == false` 而不注册数据源。

设备晚加载驱动时，要结合 logcat（Android 系统日志）、tracefs（内核追踪文件系统）event 与 pinned object 状态判断具体停在哪一步。

### map 为空

空 map 可能表示当前没有非零 entry，也可能表示驱动没有实现或没有完整发出 tracepoint。内核头文件只定义 ABI，厂商 GPU 驱动是否在 allocate、free、import、unimport 后准确上报，需要查看对应驱动源码或真机验证。

### Perfetto 只有起始快照

若配置只启用 `android.gpu.memory`，只有启动遍历符合预期。若同时启用 ftrace 后仍没有变化，应确认 tracefs 中存在 `gpu_mem/gpu_mem_total`，并检查场景期间驱动是否发出事件。

### 数值不一致

GpuMem、memtrack 和 DMA-BUF 的口径不同；先按各自定义解释，再判断差异是否异常。GPU private allocation 可能没有 DMA-BUF identity，共享 DMA-BUF 又会按 PSS 分摊。没有厂商实现证据时，只能把差异记录为待验证项。

### 可发布的结论

以下结论可由 Android 17 与 6.18 固定 tag 的源码直接支持：

- GpuMem map 保存驱动上报的 `(gpu_id, pid) → total bytes`；
- pid 0 代表全局总量，size 0 会删除 entry；
- `android.gpu.memory` 负责 Perfetto 初始值，ftrace 负责后续变化；
- GpuStats 不保存 GPU 内存字节，statsd pull 会清空相应累计值；
- memtrack、DMA-BUF 与 GpuMem 使用不同核算口径；
- Android 17 SurfaceFlinger 没有 `--bufferstats` dump 选项。

厂商 tracepoint 是否完整上报、设备权限是否满足、Perfetto UI 怎样展示、HAL 对账是否准确以及缓存何时回收，都需要实机证据。

## 参考材料

- [AOSP android-17.0.0_r1：GpuService.cpp](https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/services/gpuservice/GpuService.cpp)
- [AOSP android-17.0.0_r1：GpuMem.cpp](https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/services/gpuservice/gpumem/GpuMem.cpp)
- [AOSP android-17.0.0_r1：gpuMem.c](https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/services/gpuservice/bpfprogs/gpuMem.c)
- [AOSP android-17.0.0_r1：GpuMemTracer.cpp](https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/services/gpuservice/tracing/GpuMemTracer.cpp)
- [AOSP android-17.0.0_r1：GpuStats.cpp](https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/services/gpuservice/gpustats/GpuStats.cpp)
- [Android common kernel android17-6.18-2026-06_r6：gpu_mem tracepoint](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/include/trace/events/gpu_mem.h)
- [AOSP android-17.0.0_r1：IMemtrack.aidl](https://android.googlesource.com/platform/hardware/interfaces/+/refs/tags/android-17.0.0_r1/memtrack/aidl/android/hardware/memtrack/IMemtrack.aidl)
- [AOSP android-17.0.0_r1：dmabuf_dump.cpp](https://android.googlesource.com/platform/system/memory/libmeminfo/+/refs/tags/android-17.0.0_r1/libdmabufinfo/tools/dmabuf_dump.cpp)
- [AOSP android-17.0.0_r1：6.18 DMA-BUF BPF iterator VTS](https://android.googlesource.com/platform/system/memory/libmeminfo/+/refs/tags/android-17.0.0_r1/libdmabufinfo/vts/vts_dmabufinfo_test.cpp)
- [AOSP android-17.0.0_r1：SurfaceFlinger dump 命令表](https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/services/surfaceflinger/SurfaceFlinger.cpp)
- [Perfetto：GPU memory data source](https://perfetto.dev/docs/data-sources/gpu)
