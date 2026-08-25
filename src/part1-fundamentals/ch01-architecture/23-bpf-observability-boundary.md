---
title: Android 17 / ACK 6.18 BPF 可观测性与可编程边界
chapter: '1.23'
section: '1.23'
status: finalized
applicable_versions: Android 17 (API 37) / AOSP android-17.0.0_r1 / ACK android17-6.18-2026-06_r6
last_verified: '2026-08-06'
last_verified_against: AOSP android-17.0.0_r1; ACK android17-6.18-2026-06_r6; AIW freshness audit no Android 18/API38+ conclusion
confidence: high
sources:
- type: blog
  path: intake/daily-info/2026-07-16.md RSS订阅第二条 (Linux 6.10 BPF 内存管理，仅作线索)
- type: aosp
  path: system/bpf/loader/bpfloader.rs (android-17.0.0_r1)
- type: aosp
  path: system/bpf/loader/Android.bp (android-17.0.0_r1)
- type: aosp
  path: system/core/rootdir/init.rc (android-17.0.0_r1)
- type: kernel
  path: arch/arm64/configs/gki_defconfig, kernel/bpf/arena.c, kernel/sched/ext.c (android17-6.18-2026-06_r6)
- type: official
  path: https://source.android.com/docs/core/architecture/kernel/android-common
- type: official
  path: https://source.android.com/docs/core/architecture/kernel/gki-android17-6_18-release-builds
- type: official
  path: https://source.android.com/docs/core/architecture/kernel/bpf
- type: official
  path: https://docs.kernel.org/scheduler/sched-ext.html
- type: official
  path: https://docs.kernel.org/bpf/btf.html
tags:
- bpf
- ebpf
- kernel
- observability
- gki
- ack-6.18
- android17
related_chapters:
- '1.29'
- '2.5'
- '4.3'
- '5.2'
- '14.11'
- '14.16'
last_body_apply_at: '2026-08-06T15:15:49+08:00'
last_body_apply_run_id: 20260806-151549-82978455
task2b_state: fixed
task6_state: reviewed
task9_state: reviewed
pipeline_stage: ready-to-publish
last_review_finalize_at: '2026-08-06T16:08:13+08:00'
last_review_finalize_run_id: 20260806-160557-24b5c632
---

# Android 17 / ACK 6.18 BPF 可观测性与可编程边界

Android 上“内核支持 BPF”不等于普通应用可以任意装载程序。可观测范围同时受内核配置、平台加载器、SELinux 与公开接口约束，排查时要把编译能力、系统已部署程序和应用可访问证据分开。

## 范围与判断

BPF 是 Linux 内核中的受限程序运行机制，可在 verifier 检查通过后附着到网络、跟踪、安全或调度等内核位置；本文沿用内核与 Android 源码中的 BPF 名称。版本范围是 Android 17（API 37）、AOSP `android-17.0.0_r1` 与 ACK `android17-6.18-2026-06_r6`。ACK 是 Android Common Kernel，即 Android 共同内核分支。本文关于 6.18、Arena、`sched_ext` 和平台 BPF 加载器的结论，都以这些源码版本为准。

Android 17 的新 ACK 是 `android17-6.18`，`android17-6.18-2026-06_r6` 是对应的一次发布标签（release tag）。兼容表仍列有旧 ACK，但不能因此把 6.12 当作 Android 17 的最高内核版本。

判断一项 BPF 能力能否在设备上使用，至少要依次通过四道检查：

1. 当前 ACK 源码是否包含对应的 map（共享数据容器）、program type（程序类别）、helper（内核提供给 BPF 的辅助函数）、kfunc（允许 BPF 调用的内核函数）或 attach 点（程序挂接并接收事件的位置）。
2. 设备内核配置是否编译该能力，当前 CPU 架构的 JIT（把 BPF 字节码即时编译为机器码）是否支持它。
3. BPF 对象是否随系统镜像安装，loader 是否按内核版本和功能开关（feature flag）加载，程序是否已经附着到目标事件或内核对象。
4. 调用方是否有相应的文件权限、Linux capability（细分的特权能力）与 SELinux 权限。

可用能力满足以下交集：

```text
可用能力 = 内核实现 ∩ 内核配置 ∩ 已加载并附着的程序 ∩ 调用方权限
```

四项取交集后，才是某台 Android 17 设备上的 BPF 能力。仅看到 `CONFIG_BPF_SYSCALL=y`、某个 `.bpf` 文件或 `/sys/fs/bpf` 目录，都不足以单独得出“可用”的结论。

## 1. Android 17 的内核版本边界

### 1.1 新 ACK 与兼容旧 ACK 要分开看

AOSP 的 Android 17 兼容表列出了多条受支持的 GKI 内核。GKI 是 Generic Kernel Image，即用稳定内核模块接口支持不同设备的通用内核镜像：

| Android 17 上的 ACK | 定位 | 使用方式 |
| --- | --- | --- |
| `android17-6.18` | Android 17 新 ACK | 主锚点 |
| `android16-6.12` | 前一代 ACK，可用于 Android 17 | 兼容设备 |
| `android15-6.6` | 较早 ACK，可用于 Android 17 | 升级或兼容设备 |
| `android14-6.1`、`android14-5.15` | 更早 ACK | 升级或兼容设备 |
| `android13-5.15` | 更早 ACK | 升级或兼容设备 |
| `android13-5.10`、`android12-5.10` | Android 17 初始版本仍列入兼容表 | Android 17 QPR1 起不再受支持 |

因此，“系统版本是 Android 17”不能推出“内核一定是 6.18”。反方向同样要谨慎：在 `android17-6.18-2026-06_r6` 中确认存在的 Arena 或 `sched_ext`，不应直接写成所有 Android 17 设备都有。

设备排查的第一步是记录运行内核：

```bash
adb shell uname -r
```

这条命令只确认运行内核的版本字符串。若要确认它是否对应受支持的 GKI 构建，还要结合 GKI 构建版本、KMI generation（内核模块接口的代际标识）、Android 安全补丁级别和厂商模块版本。

### 1.2 Linux 6.10 的定位

Linux 6.10 是上游演进过程中的一个版本阶段，并非 Android 17 的 GKI 分支名。Android 17 的 6.18 ACK 已包含 Arena、`sched_ext`、BPF iterators（由 BPF 程序遍历内核对象的接口）、BPF LSM 安全钩子和 `struct_ops`（用 BPF 实现一组内核操作回调）等机制。

分析 Android 平台时，应直接检查目标 ACK，不应只根据上游版本推测某项特性是否已被回移（backport）到 Android 内核。这里的检查对象是：

```text
android17-6.18-2026-06_r6
```

除非明确说明兼容分支，内核实现和配置都以这个固定 tag 为准。

## 2. ACK 6.18 编译了哪些 BPF 基础能力

`android17-6.18-2026-06_r6` 的 `arch/arm64/configs/gki_defconfig` 包含以下关键配置：

```text
CONFIG_BPF_SYSCALL=y
CONFIG_BPF_JIT=y
CONFIG_BPF_JIT_ALWAYS_ON=y
CONFIG_BPF_LSM=y
CONFIG_SCHED_CLASS_EXT=y
CONFIG_CGROUP_BPF=y
CONFIG_NET_CLS_BPF=y
CONFIG_NET_ACT_BPF=y
CONFIG_DEBUG_INFO_BTF=y
```

这些配置分别说明：

- 内核实现了 `bpf()` 系统调用，并始终使用 BPF JIT。
- BPF LSM、cgroup BPF、网络流量分类和处理动作等程序类别具备编译基础。
- BTF 类型信息可供 verifier（在加载前检查程序安全性和合法性的验证器）、tracing 和 CO-RE 重定位使用。
- `sched_ext` 调度类被编入内核。

配置只能证明代码被编入 GKI。普通应用仍受 Android UID、capability、SELinux 和 bpffs 节点权限约束；bpffs 是用于保存并共享 BPF 对象的虚拟文件系统。因此，不能因为 `CONFIG_BPF_SYSCALL=y` 就认定普通应用可以加载任意内核 BPF 程序。BPF LSM 被编译也不代表 Android 以 BPF LSM 替换 SELinux；两者是否启用、以何种顺序参与安全决策，还取决于启动参数、LSM 列表和产品策略。

### 2.1 BTF、CO-RE 与 KMI 是三件事

这三个概念需要分别理解：

- **BTF（BPF Type Format）** 描述内核或 BPF 对象中的类型、成员和部分源码行信息。
- **CO-RE（Compile Once – Run Everywhere）** 利用 BTF relocation，让同一个已经编译的 BPF 对象在类型布局发生兼容变化时修正字段访问。
- **GKI KMI（Kernel Module Interface）** 约束 vendor module 可以依赖哪些内核符号接口。

CO-RE 能降低 BPF 程序适配内核结构布局变化的成本，但不会承诺任意 tracepoint（内核预先定义的稳定跟踪事件）、kfunc 或 vendor hook 永远存在。程序仍需检查目标内核是否提供 attach 点，loader 仍可能根据 `min_kver`、`max_kver` 或功能开关拒绝加载。

## 3. Android 17 平台怎样装载 BPF

Android 17 的平台装载逻辑不能简化成“扫描 `/system/etc/bpf` 并加载所有对象”。`android-17.0.0_r1` 已使用 Rust 实现的 `bpfloader`，它维护明确的文件、map 和 program 描述表。

启动阶段可以按下面的顺序理解：

```text
init 挂载 bpffs
    ↓
/sys/fs/bpf 可用于 pin map、program 和 link
    ↓
Rust bpfloader 读取显式描述表
    ↓
按 build 类型、feature flag、CPU 架构和 min/max kernel version 筛选
    ↓
加载平台 BPF 对象并设置节点 owner/group/mode
    ↓
进入旧版厂商 legacy vendor BPF loader
    ↓
继续处理 vendor 与 Connectivity/Tethering 的 BPF 程序
```

这里的 pin 是给 BPF 对象建立 bpffs 路径，使其在创建进程退出后仍可被其他进程引用；link 则表示程序与 attach 点之间的连接。`system/core/rootdir/init.rc` 中的挂载参数是：

```text
mount bpf bpf /sys/fs/bpf nodev noexec nosuid
```

同一文件在 Zygote 启动前触发 `load-bpf-programs`。这使需要常驻的系统观测能力可以先于应用进程准备，但加载成功不等于所有程序都已附着：

- 描述项的 `auto_attach=true` 时，loader 会立即附着程序，并 pin 相应 link。
- `auto_attach=false` 时，loader 主要负责加载并 pin program；后续组件还要执行具体 attach。
- 非 `critical` 对象加载失败时会记录错误并继续启动。
- `skip_on_user=true` 的测试对象不会在量产用的 user build 中加载。
- `allow_missing`、feature flag、架构条件和内核版本条件都会改变设备上的对象集合。

`loader/Android.bp` 的 `required` 表示对象会被构建并安装到镜像依赖中，不表示运行时一定会加载、附着或向任意进程开放。

## 4. `android-17.0.0_r1` 的平台 BPF 程序清单

平台 BPF 程序不止 `cyclePerUid`、`dmabufIter`、`kernelWakelockDuration` 和锁竞争程序。每项支持的 CPU 架构、功能开关和 attach 状态也不同。

### 4.1 loader 固定描述表中的对象

| 对象 | 主要观测或功能 | 关键程序/数据 | 权限边界 |
| --- | --- | --- | --- |
| `cputimeinstate/timeInState.bpf` | CPU 频点驻留时间、并发时间和 UID/PID 聚合 | `power:cpu_frequency`、`sched:sched_process_free`、`sched:sched_switch` | map 和 program 主要归 `system` 组 |
| `fuseMedia.bpf` | Media FUSE（用户空间文件系统）的 BPF 路径 | `fuse_media` | program 归 `media_rw` 组 |
| `gpuMem.bpf` | GPU memory total 事件统计 | `gpu_mem:gpu_mem_total` | map 和 program 归 `graphics` 组 |
| `gpuWork.bpf` | GPU work period 统计 | `power:gpu_work_period` | map 和 program 归 `graphics` 组 |
| `memevents/bpfMemEvents.bpf` | OOM（内存耗尽）、直接回收、kswapd 和 vendor LMK 事件 | 面向 AMS/lmkd 的 ring buffer | map 和 program 归 `system` 组；部分程序要求内核至少 6.1 |

`bpfMemEvents.bpf` 的两个 ring buffer（生产者顺序写入、消费者顺序读取的环形事件缓冲区）分别服务 AMS（ActivityManagerService）和 lmkd（low memory killer daemon，低内存终止守护进程）。它观察的是已经发生或正在发生的内存管理事件，例如：

- `oom:mark_victim`
- 进程在分配路径中直接回收内存（direct reclaim）的开始/结束
- 后台页回收线程 kswapd 的唤醒/休眠
- vendor LMK kill
- total reserve pages 计算

这套程序没有提供通用的“内存压力预测器”。LMKD 使用的 PSI（Pressure Stall Information，资源压力造成任务停顿的累计指标）仍是独立的内核压力信号；BPF 事件可以补充事件时间点和上下文，不能替代 PSI 的 stall 语义。

### 4.2 受 feature flag、内核版本或架构约束的对象

| 对象 | 装载条件 | attach 行为 | 主要用途 |
| --- | --- | --- | --- |
| `kernelWakelockDuration.bpf` | `kernel_wakelock_duration` flag | 自动附着到 wakeup source activate/deactivate 事件 | 累计内核唤醒源持有时间 |
| `dmabuf/dmabufIter.bpf` | `load_dmabuf_iterator` flag | `iter_dmabuf` 自动 attach | 按需遍历 DMA-BUF 信息 |
| `lock_contention/bpfLockContention.bpf` | `load_bpf_lock_contention` flag，内核至少 6.1 | 自动附着到 contention begin/end 事件 | 汇总锁竞争延迟 |
| `cpucycleperuid/cyclePerUid.bpf` | 仅 x86_64，且 `x86_cpu_energy_attribution` flag 开启 | loader pin 程序 | 按 UID 聚合 CPU cycle |

这张表解释了为什么 `cyclePerUid` 不能写成 Android 17 arm64 手机的通用能力，也解释了“镜像里有文件”和“设备上正在采集”之间的差别。

测试用的 `bpfMemEventsTest.bpf`、`bpfRingbufProg.bpf` 和 `kernelWakelockDurationTest.bpf` 带有 user build 跳过或 debuggable 构建条件，不应列入量产 user build 的功能基线。

网络流量统计、防火墙和网络共享（Tethering）BPF 由 Connectivity/Tethering 侧的 `netbpfload` 与相关组件管理。它们属于 Android BPF 体系的一部分，但不在 Rust loader 的上述平台观测对象表内。

## 5. 这些程序能回答什么问题

### 5.1 CPU 与调度

`timeInState.bpf` 把线程切换事件 `sched_switch` 与 CPU 频率变化结合起来，可以按 UID/PID 聚合运行时间和频点驻留。它适合回答：

- 某 UID 在各个 CPU frequency policy（共享一套调频策略的 CPU 集合）的频点上运行了多久。
- 某个观测窗口内的并发运行情况如何。
- CPU 频率变化前后，任务累计时间怎样变化。

它不能从聚合结果中单独还原每次调度选择的因果关系。分析唤醒延迟、抢占、迁核和 runnable（任务已经可以运行但仍在等待 CPU）时间时，仍应采集 Perfetto/ftrace 的 `sched_switch`、`sched_wakeup` 等事件，再结合 EEVDF（按虚拟截止时间选择合格任务的公平调度算法）、uclamp 调度利用率限制、cpuset CPU 集合和 DVFS 动态调频状态解释。

### 5.2 内存

内存侧有三类互补信号：

| 信号 | 适合回答的问题 | 不能直接推出的结论 |
| --- | --- | --- |
| PSI | 任务因内存回收或资源争用累计停顿了多久 | 哪一次分配触发了根因 |
| `bpfMemEvents` | OOM、direct reclaim、kswapd、LMK 等事件在何时发生 | 一段时间内完整的内存占用归因 |
| `dmabufIter` | 读取时刻的 DMA-BUF 共享缓冲区分配与归属信息 | 所有 GPU/NPU 私有内存及完整生命周期 |

ION 已由 DMA-BUF heaps 取代，排查新内核时不应再把 `/proc/ion_heaps` 当作统一接口。厂商 GPU 驱动还可能维护没有通过 DMA-BUF 表达的内存，因此 `dmabufIter` 结果只是图形内存分析的一部分。

### 5.3 GPU、锁与唤醒源

`gpuMem.bpf` 和 `gpuWork.bpf` 依赖相应 tracepoint 是否存在并产生事件。它们能提供 GPU memory total 和 GPU work period 数据，却不能单独说明渲染为何卡顿。分析时还要对齐应用帧、RenderThread、GPU 工作队列、SurfaceFlinger 和 HWC（Hardware Composer，显示硬件合成器）时间线。

lock contention 程序会根据竞争开始/结束事件聚合等待时长，适合筛选热点锁。如果聚合结果没有保留每次竞争的完整调用上下文，还需配合 Perfetto、CPU 采样工具 simpleperf 或针对性插桩继续定位。

kernel wakelock 程序累计内核 wakeup source（阻止系统进入某些低功耗状态的唤醒源）持有时间。持有时间长说明值得检查，但不自动等同于异常耗电；还要判断系统是否有合理任务、硬件是否已进入目标电源状态，以及该唤醒源是否覆盖异步工作。

## 6. BPF Arena 的准确边界

`android17-6.18-2026-06_r6` 的 `kernel/bpf/arena.c` 将 Arena 定义为 BPF 程序与用户进程之间的稀疏共享内存区域。“稀疏”表示预留较大的虚拟地址范围，但只为实际使用的部分建立物理页。它适合构造包含较多指针、由 BPF 与用户空间共同约定布局的数据结构。

创建 Arena 时有几项直接来自源码的限制：

- map 类型是 `BPF_MAP_TYPE_ARENA`。
- 必须设置 `BPF_F_MMAPABLE`。
- 当前架构的 BPF JIT 必须实现 Arena 支持。
- `max_entries × PAGE_SIZE` 表示虚拟范围，最大为 4 GiB。
- 用户空间的 VMA（连续虚拟内存区域）不能跨越一个 32 位地址边界。
- 多个用户进程映射同一 Arena 时，需要使用一致的地址和大小。
- 页面可以在用户空间发生 page fault 时建立，也可以由 BPF 程序通过 Arena kfunc 分配。

Arena 不是普通的键值（key/value）map。源码中的 lookup、update、delete、push、pop 等 map 操作会返回“不支持”或错误，用户空间不能把它当成哈希表调用 `bpf_map_lookup_elem()`。

Arena 可能减少特定数据结构在 BPF 与用户空间之间交换时的系统调用、复制或重新编码成本。它本身不会：

- 自动挂接 page fault、reclaim、GPU 或 NPU 事件。
- 自动收集 DMA-BUF 生命周期。
- 让普通应用绕开 SELinux 和 bpffs 权限。
- 直接减少系统内存占用或改善任务响应时间。

要把 Arena 用于 Android 观测，仍要编写 BPF 程序、选择稳定的 attach 点、定义共享数据结构、编写有权限的用户空间消费程序，并测量引入的内存和 CPU 开销。“内存减少 40%”若没有测试对象、对照基线、设备和复现步骤，不能作为平台结论。

## 7. `sched_ext`：编入内核不等于正在调度

ACK 6.18 的 arm64 GKI 配置包含：

```text
CONFIG_SCHED_CLASS_EXT=y
```

同时，`kernel/sched/ext.c` 在初始化时注册 `sched_ext_ops` 的 BPF `struct_ops`，并创建 `/sys/kernel/sched_ext`。这证明内核具备装载 BPF 调度策略实现的框架。

初始状态仍是 `disabled`。只有用户空间成功加载并附着一份 `sched_ext_ops`，内核才进入 `ENABLING`/`ENABLED` 状态并切换符合条件的任务：

- 未加载 BPF 调度器时，普通任务继续由公平调度类（fair scheduling class）处理；Android 17 的公平调度器使用 EEVDF。
- 调度器未设置 `SCX_OPS_SWITCH_PARTIAL` 时，符合条件的普通、batch、idle 和 ext 任务都会切到 `sched_ext`。
- 设置 `SCX_OPS_SWITCH_PARTIAL` 时，只切换显式使用 `SCHED_EXT` 调度策略的任务。
- BPF 调度器报错、退出或触发 watchdog 超时后，内核会停用它并把任务交回内置调度器，避免任务永久无法继续执行。

在有权限的调试环境中，可以先读只读状态节点：

```bash
adb shell 'cat /sys/kernel/sched_ext/state 2>/dev/null'
adb shell 'cat /sys/kernel/sched_ext/switch_all 2>/dev/null'
adb shell 'cat /sys/kernel/sched_ext/root/ops 2>/dev/null'
adb shell 'cat /sys/kernel/sched_ext/enable_seq 2>/dev/null'
```

`state` 显示框架当前是 `disabled`、`enabling` 还是 `enabled`；`switch_all` 表示当前调度器是否接管全部符合条件的任务；`root/ops` 在调度器对象存在时显示 ops 名称。`enable_seq` 是只增不减的计数器：值为 0 表示本次启动后从未成功启用 BPF 调度器，非 0 只能证明曾经启用过，不能证明当前仍在运行。节点不存在或访问被拒绝时，应记录内核版本、构建类型和 SELinux 拒绝日志，不能把空输出直接解释成某项能力不存在。

Android 17 AOSP 平台源码没有提供名为“ML Scheduler”的系统级 BPF 调度器，也没有 `bpf_runqueue_hook` 或 `bpf_cpufreq_hook` 这类通用接口。调度观测通常依赖已有的 sched/power tracepoint、BPF tracing 程序或 Perfetto；调度控制则需要单独实现 `sched_ext` 策略，并完成权限配置和产品验证。“关键任务响应时间改善 35%”如果缺少可复现实验，不能作为平台结论。

## 8. 安全边界与产品部署

### 8.1 verifier 只是第一道安全检查

BPF 程序加载时，verifier 检查控制流、指针类型、内存访问和 helper/kfunc 调用约束。通过 verifier 后，还要满足：

- 调用进程具备内核要求的 capability；
- SELinux 允许执行相应 BPF 操作和访问目标节点；
- attach 点对该 program type 开放；
- bpffs 中被 pin 的 map、program 或 link，其 owner/group/mode（所有者、用户组和权限位）允许访问；
- BTF、内核版本和程序重定位相容。

Android 17 的 Rust loader 会在 pin 后显式设置 owner、group 和 mode。`system`、`graphics`、`media_rw` 等用户组正是接口隔离的一部分，普通应用不会自动获得这些访问权。

### 8.2 OEM 程序要区分稳定接口与厂商接口

vendor BPF 程序可以放入厂商装载路径，但仍需面对：

- GKI 与 vendor module（厂商内核模块）之间的 KMI 约束；
- tracepoint、BTF 类型和 kfunc 的版本差异；
- vendor hook 是否存在，以及它是否属于允许长期依赖的接口；
- user build 上更严格的 SELinux 和调试限制；
- OTA 后 loader、程序对象、vendor module 和用户空间消费方是否版本配套。

若一个方案依赖厂商自定义 tracepoint，应把“GKI 通用能力”和“该 SoC 产品能力”分开写。前者有机会跨设备复用，后者必须在目标内核构建上验证。

## 9. 设备核查清单

下面的命令用于建立只读的事实清单，不建议在量产设备上尝试加载未知 BPF 程序。

先记录内核与 Android 版本：

```bash
adb shell uname -r
adb shell getprop ro.build.version.release
adb shell getprop ro.build.version.sdk
adb shell getprop ro.build.version.security_patch
```

再检查 bpffs 是否已挂载，以及平台 pin 了哪些对象。普通 `shell` 用户可能没有读取权限：

```bash
adb shell 'mount | grep " /sys/fs/bpf "'
adb shell 'find /sys/fs/bpf -maxdepth 2 -type f 2>/dev/null | sort | head -100'
```

userdebug/eng 调试构建设备若安装了 `bpftool` 且具备 root 权限，可以进一步检查：

```bash
adb root
adb shell bpftool feature probe kernel
adb shell bpftool prog show
adb shell bpftool map show
adb shell dmesg | grep -i -E 'bpf|bpfloader|verifier'
```

`bpftool feature probe kernel` 用于核对运行内核公开的 BPF 能力，`prog show` 和 `map show` 用于枚举当前对象，最后一条命令则查找加载器或 verifier 报错。这些结果仍不能代替 attach 状态、事件触发和消费方读数检查。

还要确认消费方是否得到数据。程序已加载但没有 attach、目标 tracepoint 未触发、map 权限不匹配，都会产生“节点存在但数据不更新”的现象。排查时按以下顺序缩小范围：

```text
内核是否支持
  → 对象是否安装
  → loader 是否选择并成功加载
  → program/link 是否 attach
  → 事件是否触发
  → map/ring buffer 是否更新
  → 消费方是否有权读取并正确解析
```

这条链路应从左向右验证。前一项没有证据时，后续出现空数据不能直接归因于业务负载或消费方。

## 10. 与其他章节的分工

- §14.16 负责从工具角度组织 BPF 能力表和现场核查方法。
- §4.3 负责 PSI、lmkd 与内存压力处置；这里只说明 BPF 事件可补充哪些上下文。
- §5.2 负责 DVFS 和 schedutil；这里不把 power tracepoint 观测写成调频控制。
- §1.4 已澄清 Android 17 不存在 AOSP 系统级“ML Scheduler”，这里不再以该概念解释 runqueue 或进程优先级。

## 小结

Android 17 的 BPF 边界应同时锚定平台源码和运行内核：

1. Android 17 的新 ACK 是 `android17-6.18`，核验基线为 `android17-6.18-2026-06_r6`。
2. Android 17 也支持多条较早 ACK，所以 6.18 中存在的能力不能直接代表所有 Android 17 设备。
3. ACK 6.18 编译了 BPF JIT、BTF、BPF LSM、cgroup BPF、Arena 和 `sched_ext` 等基础能力。
4. AOSP Rust loader 使用显式描述表，并按功能开关、构建类型、架构和内核版本筛选程序；加载、attach 和读取权限是不同阶段。
5. 平台程序覆盖 CPU time-in-state、内存事件、GPU、FUSE，以及有条件启用的 wakeup source、DMA-BUF iterator、锁竞争和 x86 cycle 统计，不能压缩成“四个固定程序”。
6. Arena 是有明确地址与页管理约束的共享内存机制；`sched_ext` 需要主动加载 BPF ops 才会启用。两者都不会仅因 GKI 配置开启而自动改变产品行为。

面对任何“Android 已支持某项 BPF 能力”的说法，都要回到四个问题：内核有没有、配置开没开、程序装载并附着了吗、调用方有权限吗。四项证据齐全后，结论才适用于目标设备。
