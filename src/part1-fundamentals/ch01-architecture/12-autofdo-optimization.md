---
title: "AutoFDO 反馈导向编译优化"
chapter: "1.12"
section: "1.12"
status: ready-for-review
drafted_date: "2026-04-06"
drafted_by: "openclaw-task2a"
reviewed_date: "2026-04-11"
reviewed_by: "openclaw-task6"
applicable_versions: "Android 12 (API 31) - Android 17 (API 37)"
last_verified: "2026-04-11"
last_verified_against: "Google blog 2026-03 + AOSP android16-6.12/android15-6.6 + simpleperf ETM doc"
confidence: medium
sources:
  - type: blog
    path: "https://android-developers.googleblog.com/2026/03/BoostingAndroid%20PerformanceIntroducingAutoFDO.html"
  - type: aosp
    path: "kernel/common (branch: android16-6.12) / gki/aarch64/afdo/README.md"
  - type: aosp
    path: "kernel/common (branch: android16-6.12) / gki/aarch64/afdo/kernel.afdo"
  - type: aosp
    path: "kernel/common (branch: android15-6.6) / android/gki/aarch64/afdo/README.md"
  - type: aosp
    path: "kernel/common (branch: android15-6.6) / android/gki/aarch64/afdo/kernel.afdo"
  - type: aosp
    path: "system/extras/simpleperf/doc/collect_etm_data_for_autofdo.md"
  - type: aosp
    path: "drivers/hwtracing/coresight/"
  - type: official
    path: "https://source.android.com/docs/core/architecture/kernel/generic-kernel-image"
tags:
  - android
  - research
  - AutoFDO
  - PGO
  - LLVM
  - GKI
  - kernel
  - simpleperf
related_chapters:
  - "1.7"
  - "8.3"
  - "8.7"
task9_reviewed_date: "2026-04-18"
task9_reviewed_by: "openclaw-task9"
last_task9_at: "2026-04-18T21:43:38+08:00"
pipeline_stage: task2b_pending
task6_state: revisiting
task9_state: reviewed
task2b_result: fixed
task2b_state: pending
task6_result: needs-rework
task9_result: needs-rework
---

# 1.12 AutoFDO 反馈导向编译优化

## 为什么要了解 AutoFDO

我们在 Perfetto 里分析性能问题时，注意力通常集中在 App 层和 Framework 层——主线程在做什么、Binder 调用耗时多少、GC 暂停了多久。但有一个事实经常被忽略：**在 Android 设备上，Linux 内核占用了大约 40% 的 CPU 时间**（[来源: Google Android LLVM toolchain team, 2026](https://android-developers.googleblog.com/2026/03/BoostingAndroid%20PerformanceIntroducingAutoFDO.html)）。

这意味着，即使我们把 App 层的优化做到了极致，剩下的 40% CPU 时间仍然消耗在内核里——进程调度、内存管理、Binder 驱动、文件系统、驱动中断。而这 40% 的性能，App 开发者几乎无法直接控制。

AutoFDO（Automatic Feedback-Directed Optimization）是 Google 从系统层面解决这个问题的手段：通过采集真实运行时的执行热点数据，反过来指导编译器对内核和原生库进行优化。这不是一个需要 App 开发者做什么的功能——它是系统构建阶段的工作，但它直接影响所有 App 的运行性能。

读完这篇文章，我们能够回答：

- Android 的编译优化体系里，AutoFDO 处在什么位置？它和 Baseline Profiles、dex2oat 的 speed-profile 是什么关系？
- AutoFDO 是怎么从 CPU 硬件层面采集数据的？采集出来的 profile 又是怎么变成编译器能用的信息？
- Google 给出的性能数据有多少可信度？OEM 和 App 开发者分别能做什么？

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 **AutoFDO 在 Android 编译体系中的位置**：[已验证: Google blog + AOSP 文档]
  Baseline Profiles 决定 Java/Kotlin 方法的 AOT 范围；AutoFDO 优化内核与系统 native binary 的机器码质量，两者不是同一层。

- 🔹 **ARM64 场景下的采样基础**：[已验证: simpleperf ETM 文档 + Coresight 驱动]
  Android 内核 AutoFDO 依赖 ETM / Coresight 采集分支轨迹；PMU 负责计数采样，ETM / ETE / TRBE 决定 profile 的精细度。

- 🔹 **ETM → perf.data → branch-list → LLVM profile 的转换顺序**：[已验证: simpleperf ETM 文档 + AutoFDO 工具说明]
  `simpleperf record` 先生成 `perf.data`，`simpleperf inject --output branch-list` 再生成 `branch_list.data`，最后 `create_llvm_prof` 为单个 binary 生成 `kernel.afdo`。

- 🔹 **GKI 分支对应的 profile 路径**：[已验证: AOSP kernel/common android15-6.6 / android16-6.12]
  `android15-6.6` 使用 `android/gki/aarch64/afdo/`，`android16-6.12` 使用 `gki/aarch64/afdo/`，不能把两个分支写成同一路径。

- 🔹 **OEM 自行复现所需的前置条件**：[已验证: simpleperf ETM 文档 + Kleaf/DDK 文档]
  需要 ARM64 ETM/ETE 能力、`userdebug/eng` + root、未剥离的 `vmlinux` / 模块符号，以及 Kleaf / DDK 的构建配置入口。

### 扩展（可选深入）
- 🔸 **如何把 kernel AutoFDO 与 Baseline Profiles 一起看**
- 🔸 **如何用 simpleperf / Perfetto 做优化前后的回归对比**
<!-- outline-end -->

## 从 PGO 到 AutoFDO：编译优化的思路变迁

编译器在编译代码时需要做很多决策：这个函数要不要内联？这个 if 分支是走 true 还是 false 的概率更高？这些代码块在内存中怎么排列能让 CPU 缓存命中率更高？

传统的做法是靠编译器的静态启发式规则——编译器根据代码结构猜测。但猜测终究是猜测，真实运行的代码路径和编译器猜的经常不一样。

Profile-Guided Optimization（PGO）的思路很简单：**先跑一遍，看看哪些路径走得多，再拿这个信息重新编译**。知道热点在哪里之后，编译器就能做出更精准的决策——把热点代码排在一起提高缓存命中率，对热点分支做更激进的内联，把冷代码移到不占缓存的角落。

PGO 有两种主要的实现方式：

**Instrumentation-based PGO（插桩 PGO）**：在代码里插入计数器，每个基本块执行一次就加一。精度高，但插桩本身会改变代码的行为（Heisenbug 的近亲），而且有运行时开销。Google 的服务器基础设施广泛使用这种方式。

**Sampling-based PGO（采样 PGO）**：不修改代码，而是利用 CPU 硬件的性能监控单元（PMU）定期采样程序的执行状态。精度比插桩略低，但零代码侵入，运行时开销极小。**AutoFDO 就是这条路**。

Google 早在 2014 年就发表了 AutoFDO 的[研究论文](https://research.google/pubs/autofdo-automatic-feedback-directed-optimization-for-warehouse-scale-applications/)，在其数据中心大规模使用。Android 从 Android 12 开始为用户态的原生库和可执行文件启用 AutoFDO，而 **2026 年 3 月正式宣布将 AutoFDO 应用于 Android 内核**（GKI，Generic Kernel Image）。

## AutoFDO 的工作机制

### 硬件基础：PMU 和 ETM

AutoFDO 的数据来源是 ARM 处理器上的两个硬件特性：

**PMU（Performance Monitoring Unit）**：ARM CPU 内置的性能计数器，能统计 CPU 周期、缓存命中/未命中、分支预测成功/失败等事件。simpleperf 通过 Linux 内核的 `perf_event_open` 系统调用读取这些计数器。

**ETM（Embedded Trace Macrocell）**：ARM Coresight 调试架构的一部分，能实时记录 CPU 执行的每一条分支指令的方向（taken / not taken）。这是 AutoFDO 采集分支 profile 的核心硬件。ETM 数据通过内核的 Coresight 驱动（`drivers/hwtracing/coresight`）导出给用户态。

对于 AutoFDO 来说，关键信息是"哪些代码路径被执行了"和"分支走向是什么"。PMU 提供采样粒度的数据（每隔 N 个事件采一次），ETM 提供全量分支追踪。实际生产环境中，Android 使用 ETM 来获取内核的精确分支 profile。

`[适用版本: Android 12+ 用户态 AutoFDO；Android 16+ 内核 AutoFDO（GKI）]`

### 数据采集流程

这里最容易写错的是顺序。设备侧先把 ETM 数据录成 `perf.data`，host 侧再把 `perf.data` 转成 branch-list，最后才由 `create_llvm_prof` 为单个 binary 生成 LLVM sample profile。把这三个阶段写反，后面的命令和文件名就会全部错位。

[图：AutoFDO 数据流程示意。设备侧运行 `simpleperf record` 产出 `perf.data`；host 侧运行 `simpleperf inject --output branch-list` 产出 `branch_list.data`；随后 `create_llvm_prof` 针对 `vmlinux` 生成 `kernel.afdo`；最后构建系统在 Kleaf / DDK 中消费 `kernel.afdo`。]

**Step 1：构建代表性工作负载**

Google 在实验室环境中模拟真实用户的使用模式。工作负载包括：

- 启动 Top 100 最受欢迎的应用（来自 [Android App Compatibility Test Suite (C-Suite)](https://android.googlesource.com/platform/test/app_compat/csuite/)）
- 覆盖前台交互、后台工作、跨进程通信等系统级行为

Google 的测试表明，这套合成工作负载与从内部设备 fleet 采集到的真实执行模式有 **85% 的相似度**，已经足够接近真实用户场景。

**Step 2：设备侧使用 simpleperf 采集 ETM 数据**

在测试设备上运行：

```bash
adb root
adb shell simpleperf record -e cs-etm:k -a -o /data/local/tmp/perf.data --duration 60
```

这一步的产物是 `perf.data`。`cs-etm:k` 表示 Coresight ETM 事件，只追踪内核态（`:k` 后缀）。

`[已验证: AOSP system/extras/simpleperf/doc/collect_etm_data_for_autofdo.md]`

**Step 3：host 侧把 `perf.data` 转成 branch-list**

把设备上的采样结果拉回 host 后，再执行转换：

```bash
adb pull /data/local/tmp/perf.data .
simpleperf inject -i perf.data --output branch-list -o branch_list.data
```

`branch_list.data` 才是后续 AutoFDO 工具真正消费的输入。也就是说，branch-list 是 `simpleperf inject` 的输出，不是 `create_llvm_prof` 的输出。

**Step 4：为单个 binary 生成 LLVM sample profile**

```bash
create_llvm_prof -profile branch_list.data -profiler text -binary vmlinux -out kernel.afdo -format binary
```

这里有两个细节必须说清楚。

第一，`create_llvm_prof` 的输入是 `branch_list.data`，不是 `perf.data`，也不是某个“injected.data”中间文件。第二，它一次只处理一个 binary。内核场景通常就是 `vmlinux`；如果 branch-list 里混入多个目标，需要先按 binary 拆分，再分别生成 profile。

`[待验证: create_llvm_prof 的具体 flag 名称会随 AutoFDO 工具版本调整，但 branch-list 是输入、LLVM sample profile 是输出，这个顺序是稳定的]`

### 编译器如何利用 Profile

拿到 profile 文件后，LLVM 编译器在编译内核时可以利用这些信息做以下优化：

**基本块排列（Basic Block Layout）**：将频繁执行的基本块在内存中连续排列，提高指令缓存命中率。这是 AutoFDO 最大的性能收益来源——当热点代码集中在一两个缓存行里时，CPU 不需要频繁从主存取指令。

**分支预测提示（Branch Prediction Hints）**：编译器根据 profile 中的分支概率数据，将"大概率会走"的分支放在 fall-through 位置（CPU 流水线默认预测方向），减少分支预测失败带来的流水线冲刷。

**函数内联（Function Inlining）**：对热点调用路径中的小函数更激进地内联，消除函数调用开销。同时减少冷函数的内联，控制二进制体积。

**寄存器分配优化**：在热点路径上给关键变量分配物理寄存器，减少栈访问。

值得注意的是，Google 采用了"保守策略"：profile 中没有覆盖到的函数（冷函数），使用标准编译优化——不因为缺少 profile 数据就降低优化级别，也不盲目优化导致代码膨胀。

### 与 dex2oat 的关系

这里最容易混的是“谁决定编什么”和“谁自己被编得更好”。

Baseline Profiles 和 `speed-profile` 解决的是前者。App 安装或后台 dexopt 时，ART 根据 profile 决定哪些 Java/Kotlin 方法值得做 AOT 编译，重点是**编译范围**。这一层发生在 `dex2oat` 处理 DEX / OAT 的时候。这部分内容我们已经在 [1.7 ART 编译管线](07-art-compilation.md) 里展开过。

AutoFDO 解决的是后者。它不告诉 ART “哪些 Java 方法要编译”，而是把真实运行时的热点反馈给 LLVM / Clang，让内核、Bionic、系统 native library，甚至 `dex2oat` 这样的原生可执行文件，在重新构建时得到更好的代码布局、分支预测和内联结果。冷启动收益的主路径来自**内核与系统 native binary 的运行时 hot path 被优化**，不是 `dex2oat` 自己跑得更快这一点。

所以更准确的关系应该写成：

- Baseline Profiles / `speed-profile` → 决定哪些 App 方法做 AOT
- AutoFDO → 优化内核和系统 native binary 的机器码质量
- `dex2oat` → 只是可能从 AutoFDO 受益的一个 native executable，不是 AutoFDO 在启动优化里的唯一目标

这三者可以叠加，但不能互相替代。

## 实测性能数据

Google 在 Pixel 设备上，对 `android16-6.12`、`android15-6.6` 和 `6.1` 三个内核版本进行了测试，给出了以下量化数据：

**内核 AutoFDO 的收益**（2026 年 3 月官方博客）：

- 开机时间提升 **2.1%**
- 冷启动速度提升 **4.3%**（这是所有 App 的几何平均）
- 综合性能几何平均提升 **10.5%**
- 部分受控测试中单项指标最高提升 **26.4%**

**用户态 AutoFDO 的收益**（此前已上线多年）：

- 冷启动提升约 **4%**
- 开机时间降低约 **1%**

`[来源: https://android-developers.googleblog.com/2026/03/BoostingAndroid%20PerformanceIntroducingAutoFDO.html]`

这些数字的可信度较高，因为：测试在真实 Pixel 设备上进行、使用 Top 100 App 作为工作负载、覆盖多个内核版本。

但我们也要注意几个前提条件：

1. 这些是 Google Pixel 上的数据，OEM 自家驱动和内核模块的优化程度会影响实际收益
2. "几何平均"意味着某些场景收益可能远高于 10.5%，某些可能几乎没有
3. 内核 AutoFDO 需要 GKI 架构支持——如果设备使用非 GKI 内核，需要自行构建 profile

## 与 Baseline Profiles 的关系与区别

这是理解 Android 编译优化全景的关键。我们用一张表把两个机制放在一起对比：

| 维度 | Baseline Profiles | AutoFDO |
|------|-------------------|---------|
| **优化目标** | Java/Kotlin 字节码 | 原生代码（内核、系统库、原生可执行文件） |
| **Profile 来源** | App 开发者通过 Macrobenchmark 生成 | Google 在实验室中用 Top 100 App 采集 |
| **编译器** | dex2oat（ART 内部编译器） | LLVM/Clang |
| **Profile 内容** | 热点方法列表 | 分支频率、基本块热度 |
| **优化方式** | AOT 编译热点 Java 方法 | 函数内联、基本块排列、分支预测提示 |
| **作用范围** | 单个 App | 整个系统 |
| **开发者可控性** | 完全可控 | 对 App 开发者透明 |
| **引入版本** | Android 9（作为 App Profiles）/ Android 13（正式名称） | Android 12（用户态）/ Android 16（内核） |

简单来说：**Baseline Profiles 让你的 App 跑得更快，AutoFDO 让你的 App 跑在更快的系统上**。两个机制不冲突，同时生效。

在启动优化中（参见 [8.3 启动优化策略](../../part2-performance/ch08-responsiveness/03-launch-optimization.md) 和 [8.7 Baseline Profiles](../../part2-performance/ch08-responsiveness/07-baseline-profiles.md)），Baseline Profiles 直接减少 App 自身的冷启动耗时，AutoFDO 则通过优化内核和系统服务的响应速度来间接减少冷启动中的系统调用开销。

## Android 16 中的支持状态

### 系统级集成

这里要先把两类对象分开。Android 12 起，Google 已经在 userspace / native binary 上使用 AutoFDO；Android 15 和 Android 16 则把同样的思路推进到 GKI 内核。读 AOSP 时最容易犯的错，就是把不同 GKI 分支的 profile 目录写成同一路径。

| 方向 | 版本 / 分支 | 主要对象 | AOSP 验证锚点 |
|------|-------------|----------|---------------|
| userspace / native AutoFDO | Android 12+ | 系统 native library、native executable | Google blog + 系统构建说明 |
| kernel AutoFDO | `android15-6.6` | GKI `vmlinux` | `android/gki/aarch64/afdo/README.md`、`kernel.afdo` |
| kernel AutoFDO | `android16-6.12` | GKI `vmlinux` | `gki/aarch64/afdo/README.md`、`kernel.afdo` |

如果把仓库前缀也写全，可以理解成在 `kernel/common` 仓库里，只是分支内部的相对路径不同：

- `android15-6.6` → `android/gki/aarch64/afdo/`
- `android16-6.12` → `gki/aarch64/afdo/`

这个 `android/` 目录的差别看起来很小，但会直接决定你能不能找到正确的 `README.md` 和 `kernel.afdo`。

`[已验证: AOSP kernel/common 仓库中，android15-6.6 与 android16-6.12 分支目录结构不同；可用 README.md 与 kernel.afdo 交叉核对]`

### OEM 能做什么

对于直接使用 GKI 的 OEM，内核 AutoFDO 的基础收益会跟着 Google 维护的 profile 一起进入构建流程。真正需要自己处理的，主要是 vendor module 和自研内核这两类额外目标。

在动手之前，我们先确认四个前置条件：

- 设备是 ARM64，并且具备 ETM 能力；ARMv9 设备通常会把这套能力演进为 ETE + TRBE。
- 构建版本至少是 `userdebug` / `eng`，并能 `adb root`，否则 ETM 采集往往拿不到完整数据。
- host 侧要有未剥离的 `vmlinux` 或目标模块符号，`create_llvm_prof` 需要把 branch-list 映射回真实符号。
- 构建系统要能把生成的 profile 接到 Kleaf / DDK 的构建配置里，否则采集结果没法真正进入编译。

最小可复现流程可以按三个阶段理解。

**device 侧：采集 `perf.data`**

```bash
adb root
adb shell simpleperf record -e cs-etm:k -a -o /data/local/tmp/perf.data --duration 120
adb pull /data/local/tmp/perf.data .
```

**host 侧：转换成 branch-list，再生成 LLVM sample profile**

```bash
simpleperf inject -i perf.data --output branch-list -o branch_list.data
create_llvm_prof -profile branch_list.data -profiler text -binary vmlinux -out kernel.afdo -format binary
```

**build 侧：把 profile 接回目标构建**

- GKI 内核：把 `kernel.afdo` 放回对应分支的 `gki/aarch64/afdo/` 或 `android/gki/aarch64/afdo/` 目录，由 Kleaf 在对应 `kernel_build` 中消费。
- vendor module：在 DDK 模块的 profile 配置里显式引用对应的 `.afdo` 文件，再触发模块重编。
- 如果 profile 覆盖多个 target，要按 binary 拆分，分别生成 profile；`create_llvm_prof` 不是“一个 profile 喂所有 binary”的工具。

`[待验证: Kleaf / DDK 的具体属性名会随分支演进调整，但“device 采集 → host 转换 → build 接入”这三段职责划分是稳定的]`

### App 开发者能做什么

内核 AutoFDO 对 App 开发者完全透明，不需要任何操作。但 App 开发者能做的是：确保自己的 App 使用了 **Baseline Profiles**（参见 [8.7 Baseline Profiles 与编译优化实践](../../part2-performance/ch08-responsiveness/07-baseline-profiles.md)），这样 App 层和系统层的编译优化可以同时生效，叠加收益最大。

## 在 Perfetto 中的观测

AutoFDO 的效果不会在 Perfetto 中表现为某个可以直接点击的 Slice——它是一个"全局背景优化"。但我们有一些间接的方法来判断它是否生效：

### 对比同设备不同版本的内核性能

在 GKI 更新前后（比如从 `android15-6.6` 更新到 `android16-6.12`），对同一 App 做冷启动 Trace 对比：

- 关注内核态 CPU 占比：如果整体 CPU 时间不变但 App 启动更快，说明内核执行效率提升了
- 关注 `sched` Slice 中内核相关的调用耗时
- Binder 驱动（`binder.c`）的耗时是一个很好的观测点——Binder 在内核中占比很高，AutoFDO 对它的优化效果明显

### 使用 simpleperf 直接验证

如果需要验证 AutoFDO profile 的效果，可以用 simpleperf 做对比测试：

```
# 不带 AutoFDO profile 的内核
simpleperf stat -e cycles,instructions,cache-misses \
  --app com.example.app -c 1 --duration 10

# 带 AutoFDO profile 的内核
# （同样的测试命令）
```

对比 IPC（Instructions Per Cycle）和缓存未命中率。AutoFDO 优化后的内核应该在热点路径上有更高的 IPC 和更低的缓存未命中率。

`[待补充: 具体的 Perfetto Trace 截图对比 — AutoFDO 前后冷启动的内核 CPU 分布]`

## 版本演进

| 版本 | AutoFDO 相关变化 |
|------|------------------|
| Android 12 | 用户态原生库和可执行文件的 AutoFDO 默认启用 |
| Android 13 | Baseline Profiles 正式命名，与 dex2oat speed-profile 深度集成 |
| Android 14 | ART Service 统一管理 on-device AOT 编译，Profile 体系进一步完善 |
| Android 15 | 内核 AutoFDO 开始在 `android15-6.6` 分支部署 |
| Android 16 | 内核 AutoFDO 扩展到 `android16-6.12`，Google 官方博客正式公布数据；计划扩展到 GKI 模块和 vendor 驱动 |
| Android 17（计划） | 支持更多 GKI 版本（如 `android17-6.18`），扩展到更多构建目标和架构（当前仅 aarch64） |

`[待验证: Android 17 的 AutoFDO 扩展计划尚未在 AOSP 中确认]`

## 常见问题与误区

**"AutoFDO 是不是替代了 Baseline Profiles？"**

不是。两者作用于不同的层——AutoFDO 优化原生代码（内核 + 系统库），Baseline Profiles 优化 Java/Kotlin 字节码。它们是互补关系，同时使用收益最大。

**"App 开发者需要为自己的 App 开启 AutoFDO 吗？"**

不需要。内核 AutoFDO 由 Google 和 OEM 在系统构建时处理，对 App 开发者完全透明。用户态原生库的 AutoFDO 也由系统镜像的构建流程管理。App 开发者应该关注的是 Baseline Profiles。

**"AutoFDO 会不会导致内核不稳定？"**

Google 的官方说法是：AutoFDO 主要影响编译器的启发式决策（内联、代码排列、分支预测），不改变源码逻辑。Google 内部已经在 ChromeOS、Android 平台库、自家的服务器基础设施上多年使用 AutoFDO，稳定性有保障。此外，Google 采用"保守策略"——未在 profile 中出现的函数使用标准优化，不会因为缺少数据而做错误的优化。

**"自研内核的 OEM 怎么用 AutoFDO？"**

参考 AOSP 中 simpleperf 的文档（`system/extras/simpleperf/doc/collect_etm_data_for_autofdo.md`）和 AutoFDO 项目的 [GitHub 仓库](https://github.com/google/autofdo)，自行搭建采集→转换→构建的管线。

## 参考资料

- [Google 官方博客：Introducing AutoFDO for the Kernel（2026-03）](https://android-developers.googleblog.com/2026/03/BoostingAndroid%20PerformanceIntroducingAutoFDO.html) — 本文主要数据来源
- [AutoFDO 研究论文（Google Research, 2014）](https://research.google/pubs/autofdo-automatic-feedback-directed-optimization-for-warehouse-scale-applications/)
- [AOSP AutoFDO Profile 仓库（android16-6.12）](https://android.googlesource.com/kernel/common/+/refs/heads/android16-6.12/gki/aarch64/afdo/)
- [AOSP AutoFDO Profile 仓库（android15-6.6）](https://android.googlesource.com/kernel/common/+/refs/heads/android15-6.6/android/gki/aarch64/afdo/)
- [simpleperf ETM 数据采集文档](https://android.googlesource.com/platform/prebuilts/simpleperf/+/refs/heads/mirror-goog-main-prebuilts/doc/collect_etm_data_for_autofdo.md)
- [AutoFDO GitHub 项目](https://github.com/google/autofdo)
- [GKI（Generic Kernel Image）文档](https://source.android.com/docs/core/architecture/kernel/generic-kernel-image)
- [Coresight 内核驱动](https://android.googlesource.com/kernel/common/+/refs/heads/android16-6.12/drivers/hwtracing/coresight)

