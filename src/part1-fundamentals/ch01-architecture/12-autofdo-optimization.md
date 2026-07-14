---

title: "AutoFDO 反馈导向编译优化"
chapter: "1.12"
section: "1.12"
status: finalized
drafted_date: "2026-04-06"
drafted_by: "openclaw-task2a"
reviewed_date: "2026-05-19"
reviewed_by: openclaw-task6
applicable_versions: "Android 12 (API 31) - Android 17 (API 37); kernel/GKI AutoFDO 覆盖 android15-6.6、android16-6.12"
last_verified: "2026-06-12"
last_verified_against: "Google blog 2026-03 + AOSP branch HEAD 2026-06-12 (android16-6.12/android15-6.6) + simpleperf ETM doc + AOSP userspace afdo: true examples"
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
task9_reviewed_date: "2026-06-12"
task9_reviewed_by: openclaw-task9
last_task9_at: "2026-07-14T17:26:54+08:00"
pipeline_stage: ready-to-publish
finalized_date: "2026-05-19"
finalized_by: openclaw-task9-auto-promote
task6_state: "reviewed"
task9_state: reviewed
task2b_result: "fixed"
last_task2b_at: "2026-05-19T15:20:11+08:00"
task2b_state: "fixed"
task6_result: pass-light-edit
task6_review_notes_round5: "2026-07-14 Task6 revisiting-review round5 (post-Task9 autofix): pass-light-edit. L1 小修 2 处（形容词+冒号「思路很简单」→「思路」；冗余副词「真正」×1 删除）。L2: 结构完整，outline 5/5 锚点 + 2/2 扩展覆盖。无新增 L3/L4 回炉项。task9_result=auto-fixed（非 pass-tech-review），送 Task9 正式复审。"
last_task6_audit: "2026-06-08"
task9_result: pass-tech-review
last_task9_audit: "2026-06-12"
last_task9_autofix_at: "2026-06-12"
last_task6_at: "2026-07-14T13:14:05+08:00"
last_task6_review_log: "logs/review/2026-05-19-16-review.md"
last_task9_review_log: logs/deep-review/2026-07-14-17-deep-review.md
task9_review_notes: "2026-06-12 Task9 idle audit: auto-fixed android15-6.6 branch HEAD benchmark drift and Android17/module roadmap boundary; no queue entry; return to Task6. | 2026-05-19 Task9 deep review: pass-tech-review。P0 0 / P1 0 / P2 0；AutoFDO kernel profile 命令链、GKI 分支路径、android15/android16 数据口径复核通过；模块化 AutoFDO Android17 段落仅作为 P3 roadmap 口径收紧建议记录。"
deepseek_cn_review_state: done
last_deepseek_cn_review_at: 2026-06-12
---


# 1.12 AutoFDO 反馈导向编译优化

## 为什么要了解 AutoFDO

我们在 Perfetto 里分析性能问题时，注意力通常集中在 App 层和 Framework 层——主线程在做什么、Binder 调用耗时多少、GC 暂停了多久。但有一个事实经常被忽略：**在 Android 设备上，Linux 内核占用了大约 40% 的 CPU 时间**（[来源: Google Android LLVM toolchain team, 2026](https://android-developers.googleblog.com/2026/03/BoostingAndroid%20PerformanceIntroducingAutoFDO.html)）。

即使把 App 层的优化做到极致，剩下的 40% CPU 时间仍然消耗在内核里——进程调度、内存管理、Binder 驱动、文件系统、驱动中断。而这 40% 的性能，App 开发者几乎无法直接控制。

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

- 🔹 **ARM64 场景下的采样基础**：[已验证: simpleperf ETM 文档 + Coresight 驱动 + Google blog]
  ETM 是通用的 Coresight 分支追踪口径；Android 16 Pixel 的公开实现已经落到 ETE + TRBE，OEM 设备再按 ETM / ETE 能力区分。

- 🔹 **ETM → perf.data → branch-list → AutoFDO text profile → LLVM profile 的转换顺序**：[已验证: simpleperf ETM 文档 + AutoFDO 工具说明]
  `simpleperf record` 先生成 `perf.data`，`simpleperf inject --output branch-list` 生成 `branch_list.data`，再转成 `perf_inject.data` / `perf_inject_kernel.data` 这类 AutoFDO text profile，随后由 `create_llvm_prof` 为单个 binary 生成 `kernel.afdo`。

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

Profile-Guided Optimization（PGO）的思路：**先跑一遍，看看哪些路径走得多，再拿这个信息重新编译**。知道热点在哪里之后，编译器就能做出更精准的决策——把热点代码排在一起提高缓存命中率，对热点分支做更激进的内联，把冷代码移到不占缓存的角落。

PGO 有两种主要的实现方式：

**Instrumentation-based PGO（插桩 PGO）**：在代码里插入计数器，每个基本块执行一次就加一。精度高，但插桩本身会改变代码的行为（Heisenbug 的近亲），而且有运行时开销。Google 的服务器基础设施广泛使用这种方式。

**Sampling-based PGO（采样 PGO）**：不修改代码，而是利用 CPU 硬件的性能监控单元（PMU）定期采样程序的执行状态。精度比插桩略低，但零代码侵入，运行时开销极小。**AutoFDO 就是这条路**。

Google 早在 2014 年就发表了 AutoFDO 的[研究论文](https://research.google/pubs/autofdo-automatic-feedback-directed-optimization-for-warehouse-scale-applications/)，在其数据中心大规模使用。Android 从 Android 12 开始为用户态的原生库和可执行文件启用 AutoFDO，而 **2026 年 3 月正式宣布将 AutoFDO 应用于 Android 内核**（GKI，Generic Kernel Image）。

## AutoFDO 的工作机制

### 硬件基础：PMU、ETM / ETE 与 TRBE

AutoFDO 的采样过程要分成两层看。

**PMU（Performance Monitoring Unit）**：ARM CPU 的性能计数与采样入口。simpleperf 仍通过 Linux 内核的 `perf_event_open` 系统调用接这套基础设施。

**ETM（Embedded Trace Macrocell）**：较早期 ARM Coresight 的分支追踪单元。到了 ARMv9，公开资料里更常见的是 **ETE（Embedded Trace Extension）** 配合 **TRBE（Trace Buffer Extension）** 把分支轨迹写入内存。Google 在 2026 年 kernel AutoFDO blog 里对 Pixel 设备描述的就是 ETE + TRBE 组合。

对内核 AutoFDO 来说，真正需要的是可还原 branch history 的 Coresight trace，而不是普通 PMU 周期采样。simpleperf 的事件名仍常写成 `cs-etm`，因为它暴露的是 Coresight trace 入口；落到具体 SoC 时，底层可能是 ETM，也可能是 ETE + TRBE。


### 数据采集流程

这里最容易写错的是顺序。设备侧先把 Coresight trace 录成 `perf.data`，host 侧转成 `branch_list.data`，再继续生成 AutoFDO text profile，随后才由 `create_llvm_prof` 为单个 binary 生成 LLVM sample profile。把这几个阶段写反，后面的命令和文件名就会全部错位。

整个数据流的顺序是:设备侧 `simpleperf record` → `perf.data`,host 侧 `simpleperf inject --output branch-list` → `branch_list.data`,再转成 `perf_inject.data` / `perf_inject_kernel.data`,最后由 `create_llvm_prof` 针对 `vmlinux` 生成 `kernel.afdo`,交给构建系统在 Kleaf / DDK 中消费。

**Step 1：构建代表性工作负载**

Google 在实验室环境中模拟真实用户的使用模式。工作负载包括：

- 启动 Top 100 最受欢迎的应用（来自 [Android App Compatibility Test Suite (C-Suite)](https://android.googlesource.com/platform/test/app_compat/csuite/)）
- 覆盖前台交互、后台工作、跨进程通信等系统级行为

Google 的测试表明，这套合成工作负载与从内部设备 fleet 采集到的真实执行模式有 **85% 的相似度**，已经足够接近真实用户场景。

**Step 2：设备侧使用 simpleperf 采集 Coresight trace**

在测试设备上运行：

```bash
adb root
adb shell simpleperf record -e cs-etm:k -a -o /data/local/tmp/perf.data --duration 60
```

这一步的产物是 `perf.data`。`cs-etm:k` 仍是 simpleperf 暴露给用户的事件名，代表只追踪内核态的 Coresight 分支轨迹。底层硬件在不同 SoC 上可能是 ETM，也可能是 ETE + TRBE。

`[已验证: AOSP simpleperf ETM 文档 + Google blog 2026-03]`

**Step 3：host 侧把 `perf.data` 转成 branch-list**

把设备上的采样结果拉回 host 后，还要准备与当前内核匹配的 `kernel.kallsyms`。`simpleperf inject` 需要它把 Coresight 里的内核地址映射回符号，只有 `perf.data` 还不够。

```bash
adb pull /data/local/tmp/perf.data .
adb shell cat /proc/kallsyms > kernel.kallsyms
simpleperf inject -i perf.data --output branch-list -o branch_list.data --binary kernel.kallsyms
```

`branch_list.data` 还是中间产物。量产流程通常会先合并多次采集得到的 branch-list，再进入下一步。

**Step 4：把 branch-list 转成 AutoFDO text profile**

用户态 / native binary 场景用通用流程：

```bash
simpleperf inject -i branch_list.data --output autofdo -o perf_inject.data
# 如果 branch-list 里覆盖多个 binary，要先按 binary 拆分
```

kernel / GKI 场景按当前 AOSP GKI README 使用专用的 inject 命令，带 kernel 符号目录和构建 ID 容差参数：

```bash
simpleperf inject -i branch01.data,branch02.data,... --binary kernel.kallsyms --symdir . --allow-mismatched-build-id -o kernel.autofdo -j 20
```

`--binary kernel.kallsyms` 指定内核符号映射，`--symdir .` 让 simpleperf 在当前目录查找内核模块 ELF，`--allow-mismatched-build-id` 容忍 build ID 不完全匹配（内核编译环境常见），`-j 20` 并行加速。`kernel.autofdo` 是 GKI README 当前使用的命名；旧文档或通用流程里的 `perf_inject_kernel.data` 是拆分产物，两者功能相同但命名不同。

**Step 5：用未剥离 `vmlinux` 生成 `kernel.afdo`**

```bash
create_llvm_prof --profiler text --binary vmlinux --profile kernel.autofdo --format=extbinary --use_fs_discriminator --out kernel.afdo --prof_sym_list=false
```

相比通用流程多了 `--use_fs_discriminator`，这是 GKI README 对 kernel 场景的要求——内核编译时如果启用了 `-fdebug-prefix-map` + `-fprofile-use`，discriminator 信息来自文件系统路径映射，需要显式告知 `create_llvm_prof`。

这里有三个约束。

第一，`create_llvm_prof` 的输入是 AutoFDO text profile，不是 `perf.data`，也不是还没拆分 binary 的原始 trace。第二，`vmlinux` 必须是未剥离版本，否则行号和符号映射会断。第三，内核场景要显式指定 `--format=extbinary` 和 `--prof_sym_list=false`，前者对应当前内核 AutoFDO 文档使用的输出格式，后者用来避免把未出现在 profile 里的内核函数一律当成冷函数。

`--prof_sym_list=false` 这一步如果漏掉，后果比较严重：`create_llvm_prof` 默认会把未出现在 profile 中的函数标记为冷函数，编译器会对这些函数降低优化级别或重新排列代码位置。内核函数成千上万，采样覆盖率不可能 100%，如果未覆盖到的热点函数（如调度器关键路径、中断处理）被误降级，内核整体性能反而可能倒退。

### 编译器如何利用 Profile

拿到 profile 文件后，LLVM 编译器在编译内核时可以利用这些信息做以下优化：

**基本块排列（Basic Block Layout）**：将频繁执行的基本块在内存中连续排列，提高指令缓存命中率。这是 AutoFDO 最大的性能收益来源——当热点代码集中在一两个缓存行里时，CPU 不需要频繁从主存取指令。

**分支预测提示（Branch Prediction Hints）**：编译器根据 profile 中的分支概率数据，将"大概率会走"的分支放在 fall-through 位置（CPU 流水线默认预测方向），减少分支预测失败带来的流水线冲刷。

**函数内联（Function Inlining）**：对热点调用路径中的小函数更激进地内联，消除函数调用开销。同时减少冷函数的内联，控制二进制体积。

**寄存器分配优化**：在热点路径上给关键变量分配物理寄存器，减少栈访问。

Google 采用了"保守策略"：profile 中没有覆盖到的函数（冷函数），使用标准编译优化——不因为缺少 profile 数据就降低优化级别，也不盲目优化导致代码膨胀。

### 与 dex2oat 的关系

容易混淆的是“谁决定编什么”和“谁自己被编得更好”。

Baseline Profiles 和 `speed-profile` 解决的是前者。App 安装或后台 dexopt 时，ART 根据 profile 决定哪些 Java/Kotlin 方法值得做 AOT 编译，重点是**编译范围**。这一层发生在 `dex2oat` 处理 DEX / OAT 的时候。这部分内容我们已经在 [1.7 ART 编译管线](07-art-compilation.md) 里展开过。

AutoFDO 解决的是后者。它不告诉 ART “哪些 Java 方法要编译”，而是把真实运行时的热点反馈给 LLVM / Clang，让内核、Bionic、系统 native library，甚至 `dex2oat` 这样的原生可执行文件，在重新构建时得到更好的代码布局、分支预测和内联结果。冷启动收益的主路径来自**内核与系统 native binary 的运行时 hot path 被优化**，不是 `dex2oat` 自己跑得更快这一点。

两者的关系可以这样理解：

- Baseline Profiles / `speed-profile` → 决定哪些 App 方法做 AOT
- AutoFDO → 优化内核和系统 native binary 的机器码质量
- `dex2oat` → 只是可能从 AutoFDO 受益的一个 native executable，不是 AutoFDO 在启动优化里的唯一目标

这三者可以叠加，但不能互相替代。

## 实测性能数据

2026 年 3 月的官方 blog 没有给出“开机 2.1% / 冷启动 4.3% / 几何平均 10.5%”这一组统一口径。公开的原始 benchmark 按 GKI 分支分别放在 `android16-6.12` 和 `android15-6.6` 的 README 里；这些 branch README 会随 profile 刷新更新，下表按 2026-06-12 的 branch HEAD 记录，读的时候要按分支和日期看。

| 指标 | `android16-6.12` | `android15-6.6` |
|------|------------------|-----------------|
| 开机时间 | **1.3%** | **1.7%** |
| 冷启动时间 | **4.8%** | **2.9%** |
| Binder RPC | **20.7%** | **17%** |
| Binder addints | **17.0%** | **15.5%** |
| HWBinder | **26.4%** | **18.9%** |
| Bionic `syscall_mmap` | **9.3%** | **3.8%** |

官方 blog 还给了 userspace native AutoFDO 的历史收益，口径是冷启动约 **4%**、开机约 **1%**。这组数字对应系统原生可执行文件和原生库，与 2026 年这次 kernel rollout 的 README 表格属于两套口径。

`10.5%` 这类几何平均数字要单独看待。它更接近早期 AutoFDO 论文和大规模部署经验里的聚合指标，不属于这篇 Android kernel blog 的原始 benchmark 项。

`[来源: Google 官方 blog（2026-03） + AOSP android16-6.12/android15-6.6 AutoFDO README，branch HEAD 复核时间 2026-06-12]`

这组数据适合这样解读：

1. 这些结果来自 Pixel 设备上的代表性工作负载，能说明方向，但不能直接外推到所有 OEM 机型。
2. 不同基准的收益差异很大，Binder、HWBinder、`syscall_mmap` 这类热点路径更容易看到明显改善，开机时间的提升则更克制。
3. 直接使用 GKI 的设备会先吃到基础收益；自研内核和 vendor module 还要自己补 profile 采集、生成和接入流程。

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
| **引入版本** | Android 9（作为 App Profiles）/ Android 13（正式名称） | Android 12（用户态/native）；kernel/GKI 当前覆盖 `android15-6.6`、`android16-6.12` |

简单来说：**Baseline Profiles 让你的 App 跑得更快，AutoFDO 让你的 App 跑在更快的系统上**。两个机制不冲突，同时生效。

在启动优化中（参见 [8.3 启动优化策略](../../part2-performance/ch08-responsiveness/03-launch-optimization.md) 和 [8.7 Baseline Profiles](../../part2-performance/ch08-responsiveness/07-baseline-profiles.md)），Baseline Profiles 直接减少 App 自身的冷启动耗时，AutoFDO 则通过优化内核和系统服务的响应速度来间接减少冷启动中的系统调用开销。

## Android 16 中的支持状态

### 系统级集成

这里要先区分两类对象。Android 12 起，Google 已经在 userspace / native binary 上使用 AutoFDO；Android 15 和 Android 16 则把同样的思路推进到 GKI 内核。读 AOSP 时最容易犯的错，就是把不同 GKI 分支的 profile 目录写成同一路径。

| 方向 | 版本 / 分支 | 主要对象 | AOSP 验证锚点 |
|------|-------------|----------|---------------|
| userspace / native AutoFDO | Android 12+ | 系统 native library、native executable | `frameworks/base/libs/hwui/Android.bp`、`art/libartbase/Android.bp`、`art/runtime/Android.bp` 中可直接搜索 `afdo: true` |
| kernel AutoFDO | `android15-6.6` | GKI `vmlinux` | `android/gki/aarch64/afdo/README.md`、`kernel.afdo` |
| kernel AutoFDO | `android16-6.12` | GKI `vmlinux` | `gki/aarch64/afdo/README.md`、`kernel.afdo` |

userspace 这一层不是抽象描述。AOSP 里已经有 `hwui`、`libartbase`、`libart` 这类代表性目标在 `Android.bp` 里打开 `afdo: true`，读者可以直接搜这些路径验证。

如果把仓库前缀也写全，可以理解成在 `kernel/common` 仓库里，只是分支内部的相对路径不同：

- `android15-6.6` → `android/gki/aarch64/afdo/`
- `android16-6.12` → `gki/aarch64/afdo/`

这个 `android/` 目录的差别看起来很小，但会直接决定你能不能找到正确的 `README.md` 和 `kernel.afdo`。

`[已验证: AOSP kernel/common 仓库中，android15-6.6 与 android16-6.12 分支目录结构不同；userspace 代表性模块可在对应 Android.bp 中搜索 afdo: true]`

### OEM 能做什么

对于直接使用 GKI 的 OEM，内核 AutoFDO 的基础收益会跟着 Google 维护的 profile 一起进入构建流程。真正需要自己处理的，主要是 vendor module 和自研内核这两类额外目标。

在动手之前，先确认四个前置条件：

- 设备是 ARM64，并且具备 Coresight 分支追踪能力；较早的平台常见 ETM，新一些 ARMv9 平台则是 ETE + TRBE。
- 构建版本至少是 `userdebug` / `eng`，并能 `adb root`，否则 ETM 采集往往拿不到完整数据。
- host 侧要有未剥离的 `vmlinux` 或目标模块符号，`create_llvm_prof` 需要把 branch-list 映射回真实符号。
- 构建系统要能把生成的 profile 接到 Kleaf / DDK 的构建配置里，否则采集结果没法进入编译。

最小可复现流程可以按三个阶段理解。

**device 侧：采集 `perf.data`**

```bash
adb root
adb shell simpleperf record -e cs-etm:k -a -o /data/local/tmp/perf.data --duration 120
adb pull /data/local/tmp/perf.data .
```

**host 侧：先转 branch-list，再转 AutoFDO text profile，再生成 LLVM sample profile**

```bash
adb shell cat /proc/kallsyms > kernel.kallsyms
simpleperf inject -i perf.data --output branch-list -o branch_list.data --binary kernel.kallsyms
simpleperf inject -i branch_list.data --output autofdo -o perf_inject.data
# 如果输入里覆盖多个 binary，要先拆出 [kernel.kallsyms] 对应的 perf_inject_kernel.data
create_llvm_prof --profile perf_inject_kernel.data --profiler text --binary vmlinux --out kernel.afdo --format=extbinary --prof_sym_list=false
```

这里的分工不能写反。`kernel.kallsyms` 负责把运行时地址映射回内核符号，未剥离 `vmlinux` 负责把 text profile 对回真实 binary。单次示例可以直接从一份 branch-list 继续往下跑；如果采了多份 branch-list，先合并，再生成最终的 `perf_inject_kernel.data` 和 `kernel.afdo`。

**build 侧：把 profile 接回目标构建**

- GKI 内核：把 `kernel.afdo` 放回对应分支的 `gki/aarch64/afdo/` 或 `android/gki/aarch64/afdo/` 目录，由 Kleaf 在对应 `kernel_build` 中消费。
- vendor module：在 DDK 模块的 profile 配置里显式引用对应的 `.afdo` 文件，再触发模块重编。
- 如果 profile 覆盖多个 target，要按 binary 拆分，分别生成 profile；`create_llvm_prof` 不是“一个 profile 喂所有 binary”的工具。

`[待验证: Kleaf / DDK 的具体属性名会随分支演进调整，但“device 采集 → host 转换 → build 接入”这三段职责划分是稳定的]`

### App 开发者能做什么

内核 AutoFDO 对 App 开发者完全透明，不需要任何操作。但 App 开发者能做的是：确保自己的 App 使用了 **Baseline Profiles**（参见 [8.7 Baseline Profiles 与编译优化实践](../../part2-performance/ch08-responsiveness/07-baseline-profiles.md)），这样 App 层和系统层的编译优化可以同时生效，叠加收益最大。

## 在 Perfetto 中的观测

AutoFDO 不会在 Perfetto 里多出一个专用 slice。验证方法要分成两层：Perfetto 看系统级症状，函数级热点用采样或 tracepoint。

### 先做同一分支、同一配置的 A/B 构建

不要拿 `android15-6.6` 和 `android16-6.12` 直接对比 AutoFDO 效果。内核版本、配置和代码都变了，变量太多。更稳妥的做法是固定同一分支、同一 defconfig、同一设备和同一工作负载，只切换 `CLANG_AUTOFDO_PROFILE` on / off。

在这个 A/B 设计里，Perfetto 适合看三类现象：

- 冷启动总时长、关键系统服务响应时间、Binder transaction 的端到端延迟
- 主线程或 `system_server` 的 runnable 到 running 等待时间
- 内核态 CPU 时间占比、调度抖动、频繁唤醒等宏观变化

这些指标能说明系统级延迟有没有下降，但不能直接给出 `binder.c`、`hwbinder` 或 `syscall_mmap` 的函数级耗时。

### 函数级热点改用 simpleperf 或 tracepoint

`sched` slice 只能看到线程什么时候在跑，不能直接给出内核函数的热点分布。要验证 Binder、HWBinder 或 `syscall_mmap` 这类路径是不是真的变快了，做法通常是：

- 用 `simpleperf stat` 做 A/B 对比，观察 `cycles`、`instructions`、`cache-misses`、`branch-misses`
- 用 `simpleperf record -g` / `report` 看调用栈热点是否从 Binder、HWBinder、`syscall_mmap` 等路径下降
- 需要 Binder 事务细节时，再配合 binder 相关 ftrace tracepoint 看 transaction / reply / wakeup 时序

```bash
# build A: 不带 AutoFDO profile
simpleperf stat -e cycles,instructions,cache-misses,branch-misses --app com.example.app -c 1 --duration 10

# build B: 同一分支、同一配置，只打开 CLANG_AUTOFDO_PROFILE
simpleperf stat -e cycles,instructions,cache-misses,branch-misses --app com.example.app -c 1 --duration 10
```

如果要把函数级收益和用户可感知收益放在一起看，顺序通常是先用 simpleperf 找热点变化，再回到 Perfetto 看启动时长、Binder 事务延迟和调度等待有没有同步下降。

## 版本演进

这张表只保留 AutoFDO 自身的 rollout，不再把 Baseline Profiles 和 ART Service 的时间线混进来。

| 时间点 | AutoFDO 相关变化 |
|--------|------------------|
| Android 12 | userspace native AutoFDO 已用于系统 native executable 和 native library |
| Android 15 / `android15-6.6` | kernel AutoFDO 进入 GKI `vmlinux`，profile 路径为 `android/gki/aarch64/afdo/` |
| Android 16 / `android16-6.12` | kernel AutoFDO 扩展到 `gki/aarch64/afdo/`，官方 blog 公布了 Boot、Cold Launch、Binder RPC、HWBinder、`syscall_mmap` 等基准数据 |
| 后续 roadmap | 官方 blog 提到 newer GKI versions（如 `android17-6.18`）、GKI module、vendor module 和更多构建目标；这些计划还没进入本文的已验证适用范围 |

后续 roadmap 里，模块化 AutoFDO 还只是扩展方向：官方 blog 明确说当前优化集中在 `vmlinux`，后续可能扩展到 GKI module 和 vendor module。`android17-6.18` 只是 newer GKI versions 的示例，不代表模块化 AutoFDO 已经进入 Android 17 已验证适用范围；本文只把它作为后续观察点。

Baseline Profiles / ART Service 的演进放在相关章节单独讨论，这里不再并表。

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

### AutoFDO：从数据中心到 Android 内核的编译优化革命
- 来源：/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/DeepResearch/AutoFDO：从数据中心到 Android 内核的编译优化革命.md
- 类型：DeepResearch 调研结果
- 摘要：这篇调研把 AutoFDO 从 Google 数据中心一路串到 Android 内核，拆开 ETM/simpleperf 采样、profile 转换和 LLVM 应用流程，并补上 Pixel 设备在 mmap、冷启动、Binder RPC 上的收益数据。
- 注入时间：2026-04-18
- 价值：把 1.12 从概念介绍推进到实验验证和内核集成细节。
