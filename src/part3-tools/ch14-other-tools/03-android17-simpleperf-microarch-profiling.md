---
title: "Android 17 simpleperf 微架构级性能采样与工作流增强"
chapter: "14.3"
section: "14.3"
status: finalized
applicable_versions: "Android 17 (API 37)"
tags: [simpleperf, ARM-SPE, TRBE, profiling, microarchitecture, AutoFDO]
related_chapters: ["14.2", "14.23", "14.24"]
last_verified: "2026-08-13"
last_verified_against: "AOSP android-16.0.0_r1 与 android-17.0.0_r1 源码差异 + android17-6.18-2026-06_r6"
confidence: high
sources:
  - type: aosp
    path: "system/extras/simpleperf/SPERecorder.cpp"
  - type: aosp
    path: "system/extras/simpleperf/SPEDecoder.cpp"
  - type: aosp
    path: "system/extras/simpleperf/event_selection_set.cpp"
  - type: aosp
    path: "system/extras/simpleperf/ETMRecorder.cpp"
  - type: aosp
    path: "system/extras/simpleperf/cmd_record.cpp"
  - type: aosp
    path: "system/extras/simpleperf/cmd_stat.cpp"
  - type: aosp
    path: "system/extras/simpleperf/cmd_inject.cpp"
  - type: kernel
    path: "drivers/perf/arm_spe_pmu.c"
  - type: kernel
    path: "drivers/hwtracing/coresight/coresight-trbe.c"
  - type: blog
    path: "Obsidian/技术文章/Android/Android-17系统层面新特性/20-simpleperf-ARM-SPE-硬件采样.md"
  - type: blog
    path: "Obsidian/技术文章/Android/Android-17系统层面新特性/21-simpleperf-TRBE-Trace-Buffer-Extension.md"
---

# 14.3 Android 17 simpleperf 微架构级性能采样与工作流增强

§14.2 讲解了 Simpleperf 的常规 PMU（Performance Monitoring Unit，处理器性能监控单元）采样。Android 17 在这套基础上加入 SPE（Statistical Profiling Extension，统计分析扩展）的采集与解码，并改进后台采集、应用进程跟踪和 ETM profile（性能数据）转换。这里的“微架构”指缓存、地址转换和分支预测等处理器内部行为。讨论范围限于已经进入 `android-17.0.0_r1` 的实现；设备能否使用这些能力，仍由 SoC（System on Chip，片上系统）、内核配置和权限共同决定。

Android 16 与 Android 17 的差异需要分开看：

| 能力 | Android 16 | Android 17 |
|---|---|---|
| Arm SPE | Simpleperf 尚无 `SPERecorder` / `SPEDecoder` | 新增 SPE 发现、采集和 `report` 解码 |
| CoreSight TRBE | `ETMRecorder` 已能识别 ETR 与 TRBE，发现 TRBE 时已把 sink 选择交给内核 | 列出多个 ETR 名称、记录 TRBE 支持的 CPU，并按 CPU 判断通用事件是否实际使用 TRBE |
| `record --background` | 无此选项 | 新增单次 `fork()` 的后台模式 |
| `--app` | `record`、`stat` 已支持 | `stat --monitor-new-thread` 可继续发现同一包名的新进程 |
| devfreq / `pmu_lib` | `--use-devfreq-counters` 已能临时切换并恢复 `mem_latency` governor | 保留原流程，并在未找到该 governor 时增加 `pmu_lib` 后备路径与恢复动作 |
| 内核模块 ETM AutoFDO | 已识别模块 DSO，但 branch-list 未保存运行时模块信息，`.ko` 也缺少可供转换器使用的 program header | 保存模块内存范围与首个符号，并从 `.text` section 建立 AutoFDO 偏移映射 |

DSO（Dynamic Shared Object）在 Simpleperf 中是被分析二进制的对象抽象，范围也包括内核与内核模块。branch-list 是序列化保存已解码分支路径的中间文件；ELF program header 描述运行时装载段，`.text` section 则保存机器指令。AutoFDO 是一种基于实际执行数据的反馈优化格式，编译器可用其中的指令范围和分支计数调整代码布局。生成 profile 只准备了优化输入，不代表编译产物一定会变快。

## 14.3.1 先分清 PMU、SPE 和 ETM

三种机制都可以由 Simpleperf 驱动，但它们回答的问题不同。

| 机制 | 输入数据 | 适合回答的问题 | 主要代价 |
|---|---|---|---|
| PMU 计数与溢出采样 | cycles、instructions、cache miss 等事件 | 哪些函数消耗 CPU，事件率是否异常 | 计数器数量有限；采样依赖溢出中断 |
| SPE 统计采样 | CPU 生成的 SPE packet | 哪些指令与访存、TLB、分支事件相关 | 依赖可选硬件和 AUX 缓冲；当前解码器只使用部分字段 |
| ETM/ETE 指令 trace | 控制流 trace | 执行过哪些分支路径，如何生成 AutoFDO profile | 数据量大，容易因 sink 与缓冲压力丢失 trace |

SPE packet 是硬件写出的一条采样记录；TLB（Translation Lookaside Buffer）是缓存虚拟地址到物理地址转换结果的结构；AUX 则是 Linux perf 为大体积硬件 trace 准备的辅助缓冲区。SPE 从 Armv8.2-A 起成为可选扩展，运行在 AArch64，也就是 64 位 Arm 执行状态中，不以 Armv9 为前提。

ETM（Embedded Trace Macrocell）和 ETE（Embedded Trace Extension）是 CoreSight 中的指令控制流 trace 源。CoreSight 是 Arm 的片上硬件跟踪框架；sink 指接收并保存 trace 的终点。TRBE（Trace Buffer Extension）是每 CPU 的内存 sink，ETR（Embedded Trace Router）则可把 trace 写入系统内存。二者都不负责生成 SPE 微架构样本。

## 14.3.2 Android 17 的 SPE 采集链路

### 从 sysfs 事件到 AUX 数据

Android 17 的 `SPETypeFinder` 会扫描 `/sys/bus/event_source/devices/arm_spe*`。`sysfs` 是内核把设备属性暴露给用户空间的虚拟文件系统；发现逻辑从中读取 PMU 数字类型 `type` 和 `format/*` 配置位，并把 `arm_spe` 作为默认设备 `arm_spe_0` 的别名。`SPERecorder` 还会读取：

- `caps/min_interval`：CPU 建议的最小采样间隔，并非硬件强制下限；读取失败时，Simpleperf 把采样周期设为 4096。
- 每个在线 CPU 的 MIDR（Main ID Register，处理器型号与版本标识）：解码时据此判断 SPE 版本和 CPU 型号。
- PMU `type`：交给 `perf_event_open()` 创建使用 AUX 缓冲的性能事件。

一次 `record` 命令只能选择一个 SPE 设备。带配置的事件名采用 sysfs 暴露的字段，例如 `arm_spe_0/<field>=<value>/`；字段名称不应从其他芯片照搬。

开始采集前，可以用下面的命令核对目标设备实际暴露的事件。它的用途是阻止脚本把“不支持 SPE”和“权限不足”混为一类错误：

```bash
adb shell su root simpleperf list | grep arm_spe
adb shell 'ls -d /sys/bus/event_source/devices/arm_spe* 2>/dev/null'
```

`su root` 表示切换为超级用户。两条命令都没有输出时，当前内核没有向 perf 子系统注册 SPE PMU。sysfs 存在而 `record` 失败时，再检查 root、SELinux 强制访问控制策略、perf 权限和事件配置。

目标设备支持通用 `arm_spe` 事件后，可以用以下流程采集一个已经运行的应用进程：

```bash
target_pid=$(adb shell pidof -s com.example.app)
adb shell su root simpleperf record \
  -e arm_spe -p "$target_pid" --duration 10 \
  -o /data/local/tmp/spe.data
adb shell su root simpleperf report \
  -i /data/local/tmp/spe.data
```

`pidof -s` 只取一个匹配进程的 PID（Process ID，进程编号）。`record` 把原始 SPE packet 写入 perf AUX 数据，`report` 再调用 `SPEDecoder` 生成可聚合的 sample。示例使用 root，是因为量产设备通常不允许 shell 任意分析其他进程；可调试应用还可以按 §14.2 的 `run-as` 流程操作。

### 当前解码器能给出什么

`SPEDecoder` 会从 packet 中提取采样指令虚拟地址（也称 IP，Instruction Pointer）、数据虚拟地址、上下文线程 ID 和事件位。Android 17 能据此生成的事件包括：

- architecturally retired；
- L1 data cache access / refill；
- TLB access / walk；
- branch condition not taken / branch mispredicted；
- LLC access / miss；
- remote access、misalignment；
- SPE 新版本提供的 L2 access / miss 等事件。

这些名称来自 decoder 的事件表。LLC 指 last-level cache，也就是处理器缓存层级中的末级缓存；实际事件集合还受 CPU 所实现 SPE 版本的约束。报告中的地址能帮助定位关联指令或数据访问，但“被采样到”仍属于统计结果，不能解释为对每一次 load/store（内存读写）的完整追踪。

Android 17 的 decoder 没有把以下 packet 信息转换成 perf sample 字段：

| 尚未输出的字段 | 对分析结论的限制 |
|---|---|
| `PERF_SAMPLE_DATA_SRC` | 该 perf 标准字段没有写入，因此无法直接给出 L1、L2、LLC、内存构成的逐级访问来源 |
| operation type | 不能仅凭报告稳定区分 load、store 或其他操作 |
| branch target / previous branch | 不能从 SPE 报告还原完整分支路径 |
| physical address | 报告只使用虚拟地址 |
| latency counter / `PERF_SAMPLE_WEIGHT` | 不能报告 issue 到完成的周期数 |
| timestamp | 当前生成的 sample 时间为 0，不能用它与其他 trace 做逐样本时间对齐 |

因此，`simpleperf report --spe-cache-miss` 不是 Android 17 的有效命令，固定的“缓存延迟链”和“TLB walk 深度”也不是当前报告能够提供的数据。需要这些字段时，应先检查后续平台版本的 decoder 是否已经实现，再决定分析方案。

### 采样事件不能简单相加

一条 SPE record 可以同时携带多个事件位。Android 17 的 `report` 会为这些事件分别建立视图，同一条 record 可能同时计入 L1 refill、TLB walk 和 remote access。各类 sample 数量适合分别排序热点，不适合相加后当作互斥事件总数。

SPE 的 packet 由硬件写入 profiling buffer，不要求每个样本触发一次 PMU 溢出中断。不过，Linux SPE 驱动仍要处理 AUX 缓冲区装填、截断、碰撞和 IRQ（Interrupt Request，硬件中断请求）。采样间隔过小或缓冲消费不及时会产生丢失记录。开销与丢失率必须在目标设备和目标负载上测量，不能套用固定百分比。

## 14.3.3 TRBE 是 CoreSight sink

CoreSight 链路可以概括为：

> CPU 上的 ETM/ETE 生成控制流 trace → CoreSight 选择 sink → ETR 或每 CPU 的 TRBE 把 trace 保存到内存

TRBE 是每 CPU 的 trace sink，对应 CPU 的 ETE 可以把 trace 写入该 CPU 的内存缓冲。缓冲到达边界时，内核驱动通过 maintenance IRQ（维护中断）更新 AUX 状态；wrap（写指针绕回）、碰撞、截断和硬件 erratum（已知设计缺陷）都可能造成 trace gap，也就是控制流记录缺口。由此不能推出“独立带宽必然无丢包”或“固定低延迟”。

### Android 17 的选择逻辑

Android 16 的 `ETMRecorder::FindSinkConfig()` 已能识别 ETR 和 TRBE，并在发现 TRBE 时把 `config2` 设为 0，让内核选择合适的 sink。`config2` 是 `perf_event_attr` 中用于传递 CoreSight sink 配置的字段。Android 17 的变化集中在更细的 sink 建模：

- `CheckSinkSupport()` 收集所有可用 ETR 配置，并保存支持 TRBE 的 CPU ID。
- 事件列表除通用 `cs-etm` 外，还可以列出 `cs-etm/@tmc_etr0/` 这类显式 ETR 事件。
- 通用 `cs-etm` 在存在可用 TRBE 时令 `config2` 为 0，交给内核按 CPU 选择 TRBE；没有 TRBE 时选择可用的 ETR。
- 显式 ETR 事件把对应 sink 配置写入 `config2`。
- `IsUsingTRBE()` 同时检查 `config2` 和目标 CPU 是否支持 TRBE。

目标设备的 sink 名称由内核提供，下面的命令用于查看 Simpleperf 已经识别出的实际事件：

```bash
adb shell su root simpleperf list | grep cs-etm
```

只有列表中出现显式 ETR 事件时，才能指定它与默认 `cs-etm` 做对照。默认事件是否使用 TRBE 还取决于采集 CPU 的支持集合，不能只根据产品宣传材料判断。

下面的命令用于做一次短时的系统级内核指令 trace，以便先检查权限、sink 和数据丢失情况：

```bash
adb shell su root simpleperf record \
  -a -e cs-etm:k --duration 5 \
  -o /data/local/tmp/kernel-etm.data
```

`:k` 将事件限制在内核态。系统级 ETM 通常要求 root；Simpleperf 也会阻止应用 UID（Android 用于隔离应用的数字身份）采集内核 ETM，以免泄露受 KASLR（Kernel Address Space Layout Randomization，内核地址空间布局随机化）保护的地址。

## 14.3.4 `record --background` 的进程语义

Android 17 新增的 `--background` 适合脚本启动有限时长的采集。实现只调用一次 `fork()`，也就是从当前进程复制出一个子进程：

1. 父进程打印子进程 PID，然后成功返回。
2. 子进程忽略终端断开时常见的 `SIGHUP` 信号，并调用 `setsid()` 脱离原会话、创建新会话。
3. 子进程把标准输入、标准输出和标准错误重定向到 `/dev/null` 空设备，随后执行采集。

这里没有第二次 `fork()`。命令行解析发生在分叉前，但输出文件准备和正式采集发生在子进程中。分叉后的报错不会出现在当前终端，所以后台采集应使用绝对输出路径，并在长任务前做一次短时前台预检。

下面的脚本在设备端定位目标进程、启动 60 秒采集，并在主机端保存 Simpleperf 返回的后台 PID。它假设当前设备端 `simpleperf` 已有采样目标的权限；`--background` 不会绕过 profileable、root、SELinux 或内核权限：

```bash
background_pid=$(adb shell '
  target_pid=$(pidof -s com.example.app) &&
  simpleperf record --background \
    -p "$target_pid" --duration 60 \
    -o /data/local/tmp/app-perf.data
')
printf 'simpleperf background pid: %s\n' "$background_pid"
```

父进程输出的是纯 PID，便于脚本保存。若 `background_pid` 为空，应立即检查包进程、权限和前台预检结果，不要等待输出文件凭空出现。

需要提前结束采集时，向这个 PID 发送 `SIGINT` 中断信号，让 Simpleperf 关闭事件并写完 `perf.data`：

```bash
adb shell kill -INT "$background_pid"
adb shell ls -l /data/local/tmp/app-perf.data
```

`SIGKILL` 会强制终止进程，不给清理逻辑执行机会，可能留下不完整数据；它不适合作为常规停止方式。后台模式也不等同于无人值守的全天采集，文件增长、设备温度、丢样和静默失败仍需外部监控。

## 14.3.5 `--app` 与新进程跟踪

`--app <package>` 在 Android 16 已经存在。它让 Simpleperf 等待包对应的初始进程；非 root 场景依赖 `run-as`，目标 APK 必须允许调试。Android 16 的 `NewThreadMonitor` 已能扫描初始 PID 集合中的新线程。Android 17 的增量是让 `stat` 在 `--app` 场景继续发现同包名进程：

- 只有启用 `--monitor-new-thread` 时才持续扫描新进程与线程。
- 扫描器遍历 `/proc` 进程信息，读取进程对应的应用包名，把新出现且包名匹配的进程加入监控。
- 新进程加入后，它的现有线程和随后创建的线程都可以成为统计目标。
- 帮助文本要求把该选项与 `--per-thread --no-inherit` 配合使用。

下面的命令用于观察应用冷启动期间出现的同包名进程和线程。先停止旧进程，再让第一条 adb 在主机后台等待，随后启动应用：

```bash
adb shell am force-stop com.example.app

adb shell simpleperf stat \
  --app com.example.app \
  --per-thread --no-inherit --monitor-new-thread \
  --duration 10 &
stat_adb_pid=$!

adb shell am start -n com.example.app/.MainActivity
wait "$stat_adb_pid"
```

这里的 `stat_adb_pid` 是主机端 adb 进程，不是设备上的 Simpleperf PID。`--app` 单独使用时，不应宣称它会持续纳入全部后续子进程；动态纳入依赖 `--monitor-new-thread`。

## 14.3.6 `--use-devfreq-counters` 与 `pmu_lib`

devfreq 是 Linux 为内存控制器等非 CPU 设备提供的动态频率框架，governor 是它选择频率的策略。`--use-devfreq-counters` 在 Android 16 已存在；Android 17 新增的是 `pmu_lib` 供应商驱动后备路径。相关处理位于 `DevfreqCounters::Use()`，只在显式传入该选项时运行，而且要求 root。

处理顺序如下：

1. 扫描 `/sys/class/devfreq/*/governor`。
2. 读取各节点的 governor；值恰好为 `mem_latency` 时记录文件路径，并临时写入 `performance`。
3. 只有未找到这类节点时，才检查 `/sys/devices/system/cpu/pmu_lib/enable_counters`。
4. 文件当前值为 `1` 时写入 `DEADBEEF`，对象析构时写入 `BEEFDEAD`。

这两个 magic value（约定好的特殊常量）来自供应商驱动，不能推广为通用 PMU 控制接口。路径不存在时，Simpleperf 跳过该后备路径。

下面的命令只适合受控、已 root 的实验设备，用于在需要 devfreq 计数器的统计任务中触发这套流程：

```bash
adb shell su root simpleperf stat \
  --use-devfreq-counters \
  -e cpu-cycles,instructions \
  --duration 10 -a
```

该选项会改变内存延迟相关 governor 或暂时停用供应商计数器，测量结果也会受到状态切换影响。正常退出时，`DevfreqCounters` 对象的析构逻辑负责恢复；进程被 `SIGKILL` 或崩溃时，恢复逻辑没有机会运行。实验脚本应在运行前后记录 governor 和 `enable_counters`，发现状态未恢复时按设备内核文档处理。

## 14.3.7 从内核模块 ETM trace 生成 AutoFDO profile

内核模块 `.ko` 是可动态装载的 ELF 目标文件，通常没有描述运行时装载段的 program header。`KernelModuleDso` 在 Android 16 已存在，但当时 `inject` 的通用转换路径没有携带足够的模块运行时信息，也无法从 program header 得到 AutoFDO 所需的可执行范围。Android 17 改进了两段链路：

- 生成 branch-list 时保存模块的内存起止地址和首个符号；转换时据此重建 `KernelModuleDso`，把 trace 内存地址对齐到 `.ko` 文件地址。
- 从存放机器指令的 `.text` section 构造一个只用于文件偏移换算的伪可执行 segment。
- 支持从 ETM `perf.data` 直接生成 AutoFDO，也支持先转成 branch-list 再生成。

源码测试以 zram 模块数据覆盖这两条转换路径。zram 是把压缩数据保存在内存中的块设备内核模块。测试证明的是地址映射和格式转换能力，不代表 zram 或其他模块会自动获得固定比例的性能提升。

采集阶段可以使用前文的内核 ETM 命令。把数据拉到构建主机后，先把 `module_symdir` 设为匹配设备构建产物中存放未剥离符号模块的目录。下面的命令会拒绝未设置的变量，并把输出限定到 zram 模块：

```bash
adb pull /data/local/tmp/kernel-etm.data ./kernel-etm.data

: "${module_symdir:?set module_symdir to the matching unstripped module directory}"
simpleperf inject \
  -i kernel-etm.data \
  --symdir "$module_symdir" \
  --binary 'zram\.ko$' \
  --output autofdo \
  -o zram.afdo
```

`--symdir` 会递归查找调试二进制和模块，Android 17 没有 `--kernel-module-dir` 选项。输入的 `perf.data` 或 branch-list 需要包含模块 map（运行时地址区间记录），地址对齐还依赖采集时保存的 kallsyms（内核符号表）首符号信息；主机上的 `.ko` 也要与设备运行版本和 build ID 对应。若一个 AutoFDO 文件包含多个二进制，Simpleperf 会提示拆分；`--binary` 可在转换时把范围限定到单个模块。

生成 `zram.afdo` 只完成 profile 制备。能否用于内核模块构建、编译器接受哪种 profile，以及优化后是否改善目标负载，都要由对应 Android 17 内核构建规则和基准测试确认。

## 14.3.8 选择分析手段

| 现象 | 优先工具 | 原因 |
|---|---|---|
| 不清楚 CPU 时间消耗在哪些函数 | PMU `cpu-cycles` 采样 | 覆盖面广，调用栈和符号工作流成熟 |
| 怀疑访存、TLB 或分支事件集中在少量指令 | SPE | 可按采样 IP、数据地址和事件位聚合 |
| 需要完整控制流或生成 AutoFDO profile | ETM/ETE | 提供可解码的分支路径 |
| 需要调度、Binder 进程间通信、频率和帧时序上下文 | Perfetto | 提供系统时间线；SPE 报告当前不能逐样本时间对齐 |

一个稳妥的调查顺序是：用 Perfetto 或常规 PMU 缩小问题范围，再按问题类型选择 SPE 或 ETM。SPE 和 ETM 都可能增加数据量与系统负载，应先做短时预检，再记录同一设备、同一负载下的对照基线，并检查丢失记录。

## 14.3.9 核验清单

- `simpleperf list` 中确认目标 SPE 或 `cs-etm` 事件存在。
- 从 sysfs 核对 SPE 配置字段，不复制其他 SoC 的事件字符串。
- SPE 报告不宣称 Android 17 decoder 尚未输出的 latency、`data_src`、物理地址或时间戳。
- 多个 SPE 事件视图不相加为互斥总数。
- TRBE 按 sink 理解，并检查 CPU 支持集合与 trace 丢失。
- 后台采集先做前台预检，保存 PID，使用绝对路径和有限 `--duration`。
- 应用动态进程统计显式启用 `--per-thread --no-inherit --monitor-new-thread`。
- `--use-devfreq-counters` 只在 root 实验设备使用，并核对状态恢复。
- 内核模块 AutoFDO 使用匹配设备且未剥离符号的 `.ko` 和 build ID，并用 `--binary` 限定单个模块。
- 所有性能收益都由目标工作负载的前后对照测量给出，不引用与当前设备无关的固定比例。

## 源码索引

- [SPERecorder.cpp：SPE PMU 发现、配置与 AUX 元数据](https://android.googlesource.com/platform/system/extras/+/refs/tags/android-17.0.0_r1/simpleperf/SPERecorder.cpp)
- [SPEDecoder.cpp：packet 解码、事件映射与当前未实现字段](https://android.googlesource.com/platform/system/extras/+/refs/tags/android-17.0.0_r1/simpleperf/SPEDecoder.cpp)
- [event_selection_set.cpp：SPE min_interval 与 AUX 缓冲配置](https://android.googlesource.com/platform/system/extras/+/refs/tags/android-17.0.0_r1/simpleperf/event_selection_set.cpp)
- [ETMRecorder.cpp：TRBE / ETR sink 发现与选择](https://android.googlesource.com/platform/system/extras/+/refs/tags/android-17.0.0_r1/simpleperf/ETMRecorder.cpp)
- [cmd_record.cpp：`--background` 进程模型](https://android.googlesource.com/platform/system/extras/+/refs/tags/android-17.0.0_r1/simpleperf/cmd_record.cpp)
- [cmd_stat.cpp：应用新线程监控与 devfreq / pmu_lib 保护](https://android.googlesource.com/platform/system/extras/+/refs/tags/android-17.0.0_r1/simpleperf/cmd_stat.cpp)
- [cmd_inject.cpp：内核模块 DSO 地址映射与 AutoFDO 输出](https://android.googlesource.com/platform/system/extras/+/refs/tags/android-17.0.0_r1/simpleperf/cmd_inject.cpp)
- [arm_spe_pmu.c：Android 17 内核 SPE AUX 缓冲与 IRQ 处理](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/drivers/perf/arm_spe_pmu.c)
- [coresight-trbe.c：Android 17 内核 TRBE per-CPU sink 驱动](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/drivers/hwtracing/coresight/coresight-trbe.c)
