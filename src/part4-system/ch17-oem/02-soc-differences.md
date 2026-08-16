---
title: "SoC 平台差异"
chapter: "17.2"
section: "17.2"
applicable_versions: "Android 12 (API 31) - Android 17 (API 37)"
last_verified: "2026-08-14"
last_verified_against: "Qualcomm Snapdragon 8 Elite Gen 5 产品页与产品简报，MediaTek Dimensity 9500、Samsung Exynos 2600、Google Tensor G5、Arm Mali-G1 Ultra 官方资料，AOSP android-17.0.0_r1，Android common android17-6.18-2026-06_r6，Perfetto / AGI / NNAPI 官方文档"
confidence: medium
sources:
  - type: blog
    path: "obsidian/Cubox/高通Oryon处理器微架构分析-2025-03-25.md"
  - type: blog
    path: "obsidian/Cubox/高通Perflock - yooooooo - 博客园-2024-11-18.md"
  - type: blog
    path: "obsidian/Cubox/2023年Arm最新处理器架构分析--X4、A720和A520-2023-08-02.md"
  - type: official
    path: "qualcomm.com/products/mobile/snapdragon"
  - type: official
    path: "mediatek.com/products/smartphones"
  - type: official
    path: "arm.com/products/silicon-ip-cpu"
  - type: official
    path: "blog.google/products-and-platforms/devices/pixel/tensor-g5-pixel-10/"
  - type: official
    path: "support.google.com/pixelphone/answer/7158570"
  - type: official
    path: "developer.arm.com/documentation/102807/0002"
  - type: web
    path: "多来源综合(web search 验证)"
  - type: official
    path: "https://www.qualcomm.com/smartphones/products/8-series/snapdragon-8-elite-gen-5"
  - type: official
    path: "https://www.qualcomm.com/content/dam/qcomm-martech/dm-assets/documents/Snapdragon-8-Elite-Gen-5-product-brief.pdf"
  - type: official
    path: "https://www.qualcomm.com/processors/adreno"
  - type: official
    path: "https://docs.qualcomm.com/bundle/publicresource/topics/80-78185-2/landing.html?product=1601111740035277"
  - type: official
    path: "https://www.mediatek.com/products/smartphones/mediatek-dimensity-9500"
  - type: official
    path: "https://semiconductor.samsung.com/processor/mobile-processor/exynos-2600/"
  - type: official
    path: "https://semiconductor.samsung.com/technologies/processor/gpu-technology/"
  - type: official
    path: "https://blog.google/products-and-platforms/devices/pixel/tensor-g5-pixel-10/"
  - type: official
    path: "https://www.arm.com/products/silicon-ip-multimedia/gpu/mali-g1-ultra"
  - type: official
    path: "https://www.arm.com/products/cortex-x"
  - type: official
    path: "https://newsroom.arm.com/blog/arm-c1-cpu-cluster-on-device-ai-performance"
  - type: official
    path: "https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/kernel/sched/fair.c"
  - type: official
    path: "https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/kernel/sched/cpufreq_schedutil.c"
  - type: official
    path: "https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/kernel/sched/ext.c"
  - type: official
    path: "https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/kernel/Kconfig.preempt"
  - type: official
    path: "https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/Documentation/scheduler/sched-energy.rst"
  - type: official
    path: "https://perfetto.dev/docs/data-sources/cpu-scheduling"
  - type: official
    path: "https://perfetto.dev/docs/analysis/sql-tables"
  - type: official
    path: "https://perfetto.dev/docs/data-sources/gpu"
  - type: official
    path: "https://developer.android.com/agi"
  - type: official
    path: "https://developer.android.com/agi/start"
  - type: official
    path: "https://developer.android.com/android-performance-analyzer"
  - type: official
    path: "https://learn.arm.com/install-guides/streamline/"
  - type: official
    path: "https://developer.qualcomm.com/software/snapdragon-profiler"
  - type: official
    path: "https://developer.android.com/ndk/guides/neuralnetworks/migration-guide"
  - type: official
    path: "https://source.android.com/docs/core/interaction/neural-networks"
tags: [qualcomm, mediatek, samsung, exynos, tensor, adreno, mali, xclipse, soc, cpu, gpu]
related_chapters: ["5.1", "5.3", "5.4", "2.10", "17.1"]
pipeline_stage: "ready-to-publish"
task6_state: reviewed
task9_state: "reviewed"
status: finalized
task2b_state: fixed
---
# SoC 平台差异

## SoC 名称不能代替设备证据

SoC（System on Chip，片上系统）把 CPU、GPU、内存控制器和专用加速器集成在同一芯片中。同一款应用在两台手机上的帧时间不同，原因可能来自 CPU 拓扑、GPU、内存系统，也可能来自内核配置、驱动版本、散热结构、屏幕分辨率或 OEM 策略。芯片型号只能缩小排查范围，不能直接给出故障结论。

分析时应区分三层证据：

1. **IP 与 SoC 规格**：这里的 IP 指可复用的硬件设计模块。芯片厂商公开的 CPU、GPU、NPU（神经网络处理器）、ISP（图像信号处理器）和内存能力，适合回答硬件提供了什么。
2. **整机实现**：OEM 选择的内存颗粒、频率表、散热方案、内核配置和驱动，决定这些能力在一台量产设备上如何工作。
3. **当前负载**：温度、电量模式、刷新率、前后台状态和并发任务，决定一次 trace（性能跟踪记录）捕获到了什么。

这三层不能互相替代。厂商产品页无法证明某台手机持续运行时的频率，单次 Perfetto 也无法证明 SoC 的架构上限。

平台锚点为 Android 17（API 37）、AOSP `android-17.0.0_r1` 和 Android common kernel `android17-6.18-2026-06_r6`。历史型号用于解释演进，涉及量产设备时仍以该设备的内核、驱动和运行状态为准。

## 四类代表性平台

在当前核对范围内，四家厂商公开的新一代移动平台可以这样描述：

| 平台 | 官方公开的 CPU / GPU | 专用计算单元 | 分析边界 |
| --- | --- | --- | --- |
| Snapdragon 8 Elite Gen 5 | 第三代 Oryon CPU，最高 4.74 GHz；Adreno GPU | Hexagon NPU、三路 20-bit Spectra ISP | Qualcomm 另有 4.6 GHz 和七核版本；产品页的 API 列表不等于每台整机的驱动能力 |
| Dimensity 9500 | 1× C1-Ultra、3× C1-Premium、4× C1-Pro；Mali-G1 Ultra MC12（12 核配置） | NPU 990、Imagiq 1190 ISP | 官方还公开 16 MB L3、10 MB SLC 和 `LPDDR5X 10667`；整机频率表与内存配置由 OEM 决定 |
| Exynos 2600 | 1× C1-Ultra、3× 性能调优 C1-Pro、6× 能效调优 C1-Pro；Xclipse 960 | NPU、带 VPS / DVNR 的 ISP | Samsung 将其描述为 2 nm GAA、Armv9.3 平台；不要从 Xclipse 940 的 RDNA 3 资料推导 Xclipse 960 的未公开代际 |
| Tensor G5 | Google 官方材料公开 TSMC 3 nm，但未在该材料中列出完整 CPU 拓扑和 GPU 型号 | 新一代 TPU（张量处理器）、定制 ISP | 官方的 CPU 与 TPU 提升比例都是相对 Tensor G4 的代际数据，不能横向换算成其他厂商的性能 |

表中的 L3 是三级缓存，SLC（System Level Cache）是多个处理单元可共享的系统级缓存。GAA（Gate-All-Around）指全环绕栅极晶体管结构；VPS（Visual Perception System）是视觉感知系统，DVNR（Deep learning Video Noise Reduction）是深度学习视频降噪。

这张表用于定位架构家族，不用于给平台排次序。即使两台设备使用同一 SoC，内存容量、散热空间和软件版本也可能让持续性能出现明显差异。

## CPU：分别看指令集、微架构、拓扑和策略

CPU 分析常把四个概念混在一起：

- **指令集**描述软件能够使用哪些指令，例如 Armv9.x。
- **微架构**描述核心如何取指、乱序执行和访问缓存，例如 Oryon、C1-Ultra、C1-Pro。
- **拓扑**描述核心数量、共享缓存和调频策略域（cpufreq policy，即共享一套调频控制的 CPU 集合）的组织方式。
- **策略**描述调度器、调频器、Power HAL（负责传递系统性能与功耗策略的硬件抽象层）和 OEM 服务如何使用这些硬件。

两个核心都支持 Armv9，不代表它们的 IPC（instructions per cycle，每周期完成的指令数）、缓存或能耗相同；两个核心出现在同一个调频策略域，也不能据此断定它们共享某一级缓存。

### 从目标设备读取拓扑

下面这组只读命令用于记录 CPU 调频策略域、图形驱动和内核版本，适合放进一次性能实验的设备信息中：

```bash
adb shell cat /sys/devices/system/cpu/possible
adb shell 'for p in /sys/devices/system/cpu/cpufreq/policy*; do
  echo "$p"
  cat "$p/related_cpus" "$p/scaling_driver" "$p/scaling_governor"
done'
adb shell getprop ro.hardware.egl
adb shell 'dumpsys SurfaceFlinger | grep -m 1 GLES'
adb shell 'pm list features | grep -E "vulkan|opengles"'
adb shell uname -a
```

`policy*` 展示的是调频策略域，不等同于物理核心簇（cluster）；`related_cpus` 也不能单独证明缓存共享关系。部分用户版本（user build）会隐藏节点，`SurfaceFlinger` 输出格式也可能变化。缺项应记为“设备未公开”，不要凭 SoC 名称补值。

### Android 17 的公平调度与 EAS

`android17-6.18-2026-06_r6` 的公平调度类使用 EEVDF（Earliest Eligible Virtual Deadline First）。它根据运行资格和虚拟截止时间，从公平调度类中选择任务。EAS（Energy Aware Scheduling，能效感知调度）则借助 Energy Model（能耗模型），在异构 CPU 之间评估唤醒任务应放到哪个核心。两套机制处理的决策层次不同。

在这条 Android common 分支中，`select_task_rq_fair()` 会先执行 Android vendor hook（厂商钩子，即内核预留的扩展回调点）。若 hook 给出非负 CPU，函数直接采用该目标。在唤醒选核分支中，若 hook 没有接管，而且 root domain（根调度域）未进入 `overutilized` 状态，代码才调用 `find_energy_efficient_cpu()`。这里的根调度域是共享一套负载均衡状态的 CPU 范围，`overutilized` 表示该范围的整体利用率已经超过 EAS 的适用条件。下面的摘录只保留 hook 返回和 EAS 判断相关的控制流：

```c
trace_android_rvh_select_task_rq_fair(p, prev_cpu, sd_flag,
		wake_flags, &target_cpu);
if (target_cpu >= 0)
	return target_cpu;

if (!is_rd_overutilized(this_rq()->rd)) {
	new_cpu = find_energy_efficient_cpu(p, prev_cpu, sync);
	if (new_cpu >= 0)
		return new_cpu;
	new_cpu = prev_cpu;
}
```

EAS 的 `compute_energy()` 会调用 `em_cpu_energy()`，估算候选 performance domain（性能域，即共享一组性能状态的 CPU 集合）的活动能耗。Energy Model 不直接记录任务迁移造成的私有 L1/L2 缓存局部性损失，因此不能把“EAS 选中了某个 CPU”解释为“内核已经精确计算了缓存迁移成本”。

`schedutil` 依据调度器利用率请求频率，但 cpufreq 驱动、OPP 表、调频间隔限制、温控约束、uclamp 和 Power HAL 都会改变结果。OPP（Operating Performance Point，工作频点）是一组配套的频率与电压；uclamp（utilization clamp，利用率钳制）用于限制调度器采用的利用率范围。一次频率抬升可能来自负载，也可能来自性能提示、任务分组或厂商服务。把调用链、调度信息与频率轨迹对齐后，才有条件判断来源。

Android 17 的 6.18 分支也含有 `sched_ext`，它是允许用 BPF 程序定义调度策略的 Linux 可扩展调度框架。设备需要启用 `CONFIG_SCHED_CLASS_EXT`，再加载相应的 BPF 调度器，任务才会受这个扩展调度类影响。源码中存在 `kernel/sched/ext.c`，不能证明量产设备已经启用某个 OEM BPF 调度器。

### 厂商策略应按可观测结果描述

Snapdragon、Dimensity、Exynos 和 Tensor 设备都可能在 AOSP 调度机制之上加入厂商钩子、Power HAL 性能提示、uclamp、任务配置档（task profile）、cpufreq 服务质量约束（QoS）或私有守护进程。公开 AOSP 不能证明某家厂商在所有产品上“更激进”或“更保守”，私有接口也会随产品线与版本改变。

遇到一段突发提频，可按以下顺序查证：

1. 用 `sched` 和 `thread_state` 表判断线程处于运行态、可运行态还是阻塞态。
2. 对齐 CPU 频率、空闲状态、温控状态与电源模式。
3. 检查关键线程所属的控制组（cgroup）、任务配置档和 uclamp。
4. 在可用的 userdebug（带调试能力的系统构建）或厂商调试环境中追踪 Power HAL 性能提示与厂商事件。
5. 用固定脚本重复实验，比较冷机、热机和不同电源模式。

不能访问厂商服务时，结论应停在“观测到频率与负载不成比例”这一层，避免给私有机制指定名称。

### 用 Perfetto 统计运行片段之间的 CPU 变化

下面的 PerfettoSQL 用于统计指定时间窗内，同一线程相邻运行片段之间观察到的 CPU 编号变化：

```sql
WITH ordered_runs AS (
  SELECT
    s.utid,
    s.ts,
    s.cpu,
    LAG(s.cpu) OVER (
      PARTITION BY s.utid
      ORDER BY s.ts
    ) AS previous_cpu
  FROM sched s
  WHERE s.ts BETWEEN 1000000000 AND 11000000000
)
SELECT
  t.tid,
  t.name,
  COUNT(*) AS observed_cpu_changes
FROM ordered_runs r
JOIN thread t USING (utid)
WHERE r.previous_cpu IS NOT NULL
  AND r.previous_cpu != r.cpu
GROUP BY r.utid, t.tid, t.name
ORDER BY observed_cpu_changes DESC;
```

示例时间戳是 trace 起点后的 1～11 秒，需要替换为目标交互区间。这个计数描述相邻 CPU 运行片段的编号变化，不等同于 `sched_migrate_task` 事件数量，也不直接衡量迁移代价。若要判断代价，还要结合运行片段时长、唤醒延迟、PMU（Performance Monitoring Unit，性能监控单元）记录的缓存未命中与业务阶段。

## GPU：架构名称只给出排查方向

### Adreno、Mali / Immortalis 与 Xclipse

Qualcomm 将 Adreno 作为自研 GPU 系列。官方资料把 Snapdragon 8 Elite 引入的设计称为 sliced architecture（分片式架构）；Adreno 开发文档还说明 FlexRender 可以在分块渲染与直接渲染路径之间选择。TBR（tile-based rendering）指先按屏幕分块再处理图元的渲染方式，不能用一条固定的 TBR 流程概括所有 Adreno 工作负载。

Arm 的 Mali 与 Immortalis 是可配置 GPU IP，也就是可以由 SoC 厂商选择规模并集成的 GPU 设计。同一代 IP 可以有不同的着色器核心（shader core）数量、缓存和频率。Mali-G1 Ultra 的公开范围为 10～24 个着色器核心，Dimensity 9500 采用 MC12 的 12 核配置。看到 “Mali-G1 Ultra” 时，仍需确认具体核心数、驱动和整机功耗限制。

Samsung 的 Xclipse 系列使用 AMD RDNA 技术。Samsung 明确说明 Xclipse 940 基于 RDNA 3；Exynos 2600 产品页列出 Xclipse 960，但没有在该页给出可供核验的 RDNA 代际。分析 Xclipse 960 时，应读取实机 Vulkan、OpenGL ES 和驱动信息。

Google 的 Tensor G5 官方介绍强调 TPU、ISP 与 3 nm 工艺，没有在该文中公开 GPU 型号。文档缺少规格时，设备查询结果比第三方参数表更可靠。

### API 支持由整机驱动决定

SoC 产品页、GPU IP 页面和 Android 设备报告回答的是不同问题。产品页可能列出 IP 支持的 OpenGL ES / Vulkan 上限；应用能使用哪些扩展，要看量产设备驱动、系统镜像和功能级别（feature level）。跨设备问题至少要记录：

- GPU 厂商标识（vendor）、渲染器字符串（renderer）、驱动版本与系统构建指纹（build fingerprint）；
- Vulkan API 版本、扩展和队列族（queue family，即具备同类操作能力的一组 Vulkan 队列）；
- OpenGL ES 版本与扩展；
- 显示分辨率、刷新率、色彩格式和渲染比例；
- 图形 API、着色器变体、纹理格式与帧率上限。

Android GPU Inspector（AGI）文档列出 Qualcomm Adreno、Arm Mali 和 Imagination PowerVR。快速入门还要求设备在支持列表中、运行 Android 11 或更高版本，并通过兼容 GPU 驱动的校验。文档没有列出 Xclipse，不能据此推导 Xclipse 的 AGI 支持状态。

### Perfetto GPU 数据依赖数据生产端

Perfetto 定义了 `gpu.counters`、`gpu.renderstages`、`vulkan.memory_tracker`、`gpu.log` 等数据源，也能通过 ftrace（Linux 内核跟踪机制）采集部分 GPU 频率与内存事件。producer（数据生产端）是向 Perfetto 跟踪服务注册并写入数据的组件，它可能把硬件后缀写进数据源名称，例如 `gpu.renderstages.mali`。下面的配置用于请求渲染阶段，以及内核提供的 GPU 频率和分配量事件：

```proto
data_sources {
  config {
    name: "gpu.renderstages"
  }
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
```

采集前应查询设备公布的数据源并使用完全匹配的名称。缺少 `gpu.renderstages` 或某个 ftrace 事件时，删去该项并记录缺口；空轨道（Track）不能证明 GPU 没有工作。`gpu_mem_total` 表示内存分配量，不能当作 DRAM 带宽。

不同数据生产端的阶段标签和粒度没有跨厂商的等价保证。跨设备比较应固定画面、分辨率、刷新率、API、着色器、驱动版本、温度与功耗模式，再比较端到端帧时间、错过帧截止时间的次数和持续稳态。单独比较两个厂商阶段名称下的绝对耗时容易得出错误结论。

## NPU、DSP 与 ISP：加速器是否接管要靠运行证据

### NPU / TPU

Hexagon、MediaTek NPU、Samsung NPU 和 Google TPU 面向端侧推理，也就是直接在设备上执行机器学习模型。厂商公布的代际百分比通常使用各自的模型、数值精度、功耗模式和上一代基线，不能据此组成公平的横向排行榜。

评估一个模型时，更有解释力的指标包括：

- 算子、数据类型与动态形状（dynamic shape）是否受硬件加速器支持；
- 计算图被切成多少个子图（partition），哪些算子回退到 CPU 或 GPU；
- 编译和缓存耗时，输入输出复制与布局转换耗时；
- 冷启动、预热后延迟、吞吐、尾延迟和持续功耗；
- 模型精度、量化误差，以及不同运行时（runtime）和委派后端（delegate）的版本。

NNAPI 的 NDK 接口从 Android 15 起已弃用。Android 17 应用应根据模型格式和目标硬件选择仍受支持的推理运行时与委派后端，并通过分析器或运行时日志确认委派结果。Neural Networks HAL 仍可作为系统框架与设备驱动之间的接口；应用不能仅凭设备有 NPU 就断定整张模型会在 NPU 上运行。

### DSP

DSP（Digital Signal Processor，数字信号处理器）常处理音频、传感器、计算机视觉或推理子图。DSP 工作未必出现在 CPU `sched` 轨道中，却可能通过共享内存、DMA（Direct Memory Access，直接内存访问）、唤醒和功耗轨迹影响系统。排查常驻语音或传感器场景时，可组合观察唤醒锁（wakelock）、Binder、HAL 线程、内存分配、厂商 DSP 计数器和电源测量。

仅凭 CPU 利用率低，不能断定系统处于低功耗；仅凭某个 Hexagon 名称，也不能把 NPU 与传统 DSP 负载混为同一种执行路径。

### ISP

ISP 负责传感器数据处理、去噪、HDR、对焦和部分计算摄影。相机流水线还会经过相机系统服务、HAL、BufferQueue、GPU、NPU / DSP 与编码器。拍照延迟需要按请求（request）、传感器曝光（sensor exposure）、缓冲区就绪（buffer ready）、处理与保存阶段分别统计。

ISP 通常缺少跨厂商通用的 Perfetto 计数器。可用证据包括相机框架与 HAL 的 trace、BufferQueue、CPU / GPU 运行片段、厂商 ISP 计数器、内存互连计数器和外部功耗测量。若相机运行时 UI 掉帧，只能先说明两个现象在时间上相关；证明带宽争用还需要计数器或受控扰动实验。

## LPDDR5 / LPDDR5X：标称速率不是有效带宽

一款 SoC “支持 LPDDR5X”，只说明内存控制器的能力范围。OEM 仍会选择颗粒、容量、速率、总线组织和固件策略。Snapdragon 8 Elite Gen 5 产品简报写的是 “LP-DDR5x, up to 5300 MHz”，Dimensity 9500 页面只写 `LPDDR5X 10667`，没有注明单位。资料没有说明采用时钟频率、每引脚数据率还是内存速率等级时，不能把 5300 和 10667 当成同单位数字直接比较。

当厂商给出可核验的总传输率与总数据位宽时，理论峰值可按下式估算：

`理论带宽（Byte/s） = 每秒传输次数（transfer/s） × 总数据位宽（bit） ÷ 8`

若资料只写内存通道（channel）数量，却不写每个通道的数据位宽，公式仍缺参数。MT/s 表示每秒百万次传输，Gb/s 表示每秒十亿比特；两者还要与时钟频率区分，双倍数据率不能重复乘二。

应用拿到的是有效带宽和访问延迟。内存控制器调度、DRAM 时序、SLC / LLC 命中、压缩、NoC、内存互连、CPU / GPU / ISP 并发与温控都会拉开理论值和测量值。LLC（Last Level Cache）是末级缓存；NoC（Network on Chip）是连接芯片内部模块的片上网络。顺序读写微基准（microbenchmark）也不能代表游戏纹理采样或相机流水线。

Perfetto 没有所有 Android 设备都提供的通用 “DRAM bandwidth” 轨道。设备若公开内存互连、devfreq（内核设备调频框架）、PMU 或厂商内存计数器，可以在时间轴上对齐；没有计数器时，可用固定负载做受控扰动，例如保持 GPU 场景不变，逐档增加 CPU 内存流量并记录帧时间、频率和功耗。相关性只能支持提出假设，因果判断还需要可重复的负载变化。

## 工具选择与数据缺口

### Perfetto

Perfetto 适合作为跨平台基线：CPU 调度、频率、空闲状态、进程与线程、Binder、帧时间线、部分温控与 GPU 数据可以放在同一时钟域。各轨道是否存在取决于内核跟踪点（tracepoint）、数据生产端、权限和配置。报告中应同时附采集配置与缺失数据，不能把工具未采到解释成硬件没有活动。

CPU 频率可能按调频策略域变化，也可能由每核事件上报；温度传感器的名字、位置与采样周期也不相同。跨设备报告应说明这些口径差异。

### Android GPU Inspector 与 Android Performance Analyzer

AGI 可在受支持设备上采集 GPU 计数器，并执行系统分析与单帧分析。它适合检查绘制调用（draw call）、着色器、流水线停顿和 GPU 计数器，但使用前必须核对设备、GPU 和驱动是否在当前支持范围内。Google 目前把 Android Performance Analyzer（APA）列为系统分析的新推荐工具；AGI 的单帧分析与现有系统分析功能仍有独立用途。

### Arm Streamline

Streamline 可分析 Arm CPU，以及目标系统支持的 Mali / Immortalis GPU 计数器。能采到哪些 PMU、GPU 与系统计数器，取决于目标内核、驱动、gator 数据采集模块或 agent 代理程序的配置和权限。使用 Arm CPU 不代表一台零售用户版本会自动开放全部计数器。

### Snapdragon Profiler 与厂商工具

Snapdragon Profiler 面向受支持的 Snapdragon 平台，可提供 Adreno、CPU、DSP 等平台数据。具体采集模式、计数器数量、操作系统版本和设备兼容性应以当前工具包文档为准，不应把某一旧版本的功能表写成长期固定能力。

Samsung、MediaTek、Google 或 OEM 也可能提供内部或合作伙伴工具。拿不到这些工具时，Perfetto、simpleperf、AGI、应用埋点和外部功耗设备仍能组成可复现的基础证据集。结论范围要与可见数据一致。

## 一套可复用的跨 SoC 分析流程

1. **定义体验指标**：例如启动首帧、交互帧错过截止时间的次数、推理 P95（第 95 百分位延迟）或拍照保存完成时间。
2. **固定变量**：相同应用构建版本、数据、屏幕参数、网络、环境温度、电量模式和预热轮次。
3. **记录设备清单**：SoC、RAM、系统构建指纹、内核、GPU 驱动、分辨率和刷新率。
4. **采集公共证据**：Perfetto 配置一致，并明确每台设备缺少哪些数据源。
5. **按瓶颈补充数据**：CPU 用 simpleperf / PMU，GPU 用 AGI 或厂商工具，内存用互连计数器，推理用运行时分析器。
6. **区分瞬态与稳态**：同时看冷启动、短时突发和热平衡后的持续运行。
7. **复现实验**：每个结论至少能由固定步骤重复触发，并保留原始 trace、配置和统计脚本。

这套流程得到的是“某个软件版本在某台设备、某种状态下”的结论。扩大到整个 SoC 系列前，需要增加机型、系统版本和运行条件。

## 常见误判

### 用芯片品牌预测流畅度

峰值算力不会自动转换成帧稳定性。OEM 策略、散热、内存、显示负载和应用路径都会影响结果。报告应描述可测量的错过帧截止时间次数、CPU 可运行态等待时延、GPU 完成时间和降频，不给品牌贴“流畅”或“保守”的标签。

### 用 CPU 主频跨架构比较性能

主频只表示每秒时钟周期数。IPC、缓存、内存延迟和向量指令都会改变每个周期完成的工作。跨架构比较应使用相同工作负载的完成时间、指令数（instructions）、周期数（cycles）、缓存未命中次数与功耗。

### 把调频策略域当成物理核心簇

调频策略域表示共享调频控制的 CPU 集合，不保证共享 L2，也不保证核心微架构相同。缓存与 DSU（DynamIQ Shared Unit，共享单元）拓扑需要 TRM（Technical Reference Manual，技术参考手册）、设备树、内核日志或经过验证的硬件资料。

### 把频率同时升高归因于私有提频机制

线程并发、共享调频策略域、温控恢复、Power HAL 性能提示和厂商服务都可能形成相似曲线。没有调用链或厂商事件时，只记录现象和触发条件。

### 把 GPU 轨道缺失当成 GPU 空闲

数据生产端、驱动、权限或采集配置缺失都会造成空轨道。应用帧时间、同步栅栏（fence）、SurfaceFlinger、GPU 频率和厂商分析器可以交叉核对。

### 直接比较厂商 AI 百分比

“提升 40%”必须连同上一代基线、模型、精度、批量大小（batch size）、功耗模式和软件栈一起读取。不同厂商的百分比缺少共同分母，不能相加、相减或排序。

### 从时间相关性推断内存带宽争用

CPU 与 GPU 同时变慢只是线索。可靠判断需要 DRAM 或内存互连计数器，也可以改变一方的内存流量，再用受控实验观察另一方是否按预期响应。

## 与相关章节的边界

- §5.1 说明公平调度、唤醒与可运行态等待时延；这里讨论 SoC 拓扑和厂商扩展怎样改变观测条件。
- §5.3 说明 DynamIQ 与异构核心；设备拓扑必须从目标机核验。
- §5.4 说明 DVFS；这里补充调频策略域、Power HAL 和整机散热的差异。
- §2.10 说明 Android GPU 渲染分析；这里补充 GPU IP、驱动与数据生产端的跨平台边界。
- §17.1 说明 OEM 优化的公共框架；这里提供 SoC 侧的证据分层。

## 参考资料

### SoC 与 GPU 官方资料

- [Snapdragon 8 Elite Gen 5](https://www.qualcomm.com/smartphones/products/8-series/snapdragon-8-elite-gen-5)
- [Snapdragon 8 Elite Gen 5 产品简报](https://www.qualcomm.com/content/dam/qcomm-martech/dm-assets/documents/Snapdragon-8-Elite-Gen-5-product-brief.pdf)
- [Qualcomm Adreno](https://www.qualcomm.com/processors/adreno)
- [Qualcomm Adreno FlexRender 开发指南](https://docs.qualcomm.com/bundle/publicresource/topics/80-78185-2/landing.html?product=1601111740035277)
- [MediaTek Dimensity 9500](https://www.mediatek.com/products/smartphones/mediatek-dimensity-9500)
- [Samsung Exynos 2600](https://semiconductor.samsung.com/processor/mobile-processor/exynos-2600/)
- [Samsung Xclipse GPU 技术](https://semiconductor.samsung.com/technologies/processor/gpu-technology/)
- [Google Tensor G5](https://blog.google/products-and-platforms/devices/pixel/tensor-g5-pixel-10/)
- [Arm Mali-G1 Ultra](https://www.arm.com/products/silicon-ip-multimedia/gpu/mali-g1-ultra)
- [Arm C1 CPU 平台](https://www.arm.com/products/cortex-x)
- [Arm C1 CPU cluster](https://newsroom.arm.com/blog/arm-c1-cpu-cluster-on-device-ai-performance)

### Android、内核与分析工具

- [Android 17 common kernel：fair.c](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/kernel/sched/fair.c)
- [Android 17 common kernel：schedutil](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/kernel/sched/cpufreq_schedutil.c)
- [Android 17 common kernel：sched_ext](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/kernel/sched/ext.c)
- [Android 17 common kernel：sched_ext Kconfig](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/kernel/Kconfig.preempt)
- [Linux Energy Aware Scheduling 文档（Android 17 kernel 锚点）](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/Documentation/scheduler/sched-energy.rst)
- [Perfetto CPU scheduling 数据源](https://perfetto.dev/docs/data-sources/cpu-scheduling)
- [Perfetto SQL tables](https://perfetto.dev/docs/analysis/sql-tables)
- [Perfetto GPU 数据源](https://perfetto.dev/docs/data-sources/gpu)
- [Android GPU Inspector](https://developer.android.com/agi)
- [Android GPU Inspector 快速入门与设备校验](https://developer.android.com/agi/start)
- [Android Performance Analyzer](https://developer.android.com/android-performance-analyzer)
- [Arm Streamline 安装指南](https://learn.arm.com/install-guides/streamline/)
- [Snapdragon Profiler](https://developer.qualcomm.com/software/snapdragon-profiler)
- [NNAPI 迁移指南](https://developer.android.com/ndk/guides/neuralnetworks/migration-guide)
- [Android Neural Networks HAL](https://source.android.com/docs/core/interaction/neural-networks)
