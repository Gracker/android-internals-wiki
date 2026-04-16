---
title: "ART 编译管线与 dex2oat 优化"
chapter: "1.7"
section: "1.7"
status: ready-for-review
drafted_date: "2026-04-05"
drafted_by: "openclaw-task2a"
applicable_versions: "Android 7.0 (API 24) - Android 17 (API 37)"
last_verified: "2026-04-05"
last_verified_against: "AOSP android-17-beta3"
confidence: medium
polish_count: 1
polish_date: "2026-04-08"
polish_by: "task2b-polish"
reviewed_date: "2026-04-13"
reviewed_by: "openclaw-task6"
task6_result: needs-rework
sources:
  - type: official
    path: "https://developer.android.com/topic/performance/baselineprofiles/overview"
  - type: official
    path: "https://source.android.com/docs/core/runtime"
  - type: blog
    path: "https://android-developers.googleblog.com/ (ART Performance Updates 2025)"
  - type: aosp
    path: "art/compiler/ + art/dex2oat/ + art/jit/"
  - type: blog
    path: "https://android-developers.googleblog.com/ (AutoFDO GKI Kernel)"
tags: [ART, dex2oat, JIT, AOT, Baseline-Profiles, Startup-Profiles, PGO, compilation, cold-start]
related_chapters: ["1.6", "1.12", "4.3", "8.2", "8.3", "16.1"]
task9_result: needs-rework
pipeline_stage: task6_pending
task6_state: revisiting
task9_state: pending
task2b_result: fixed
task2b_state: fixed
---

# 1.7 ART 编译管线与 dex2oat 优化

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 **ART 编译策略的演进**：[已验证: source.android.com/docs/core/runtime]
  从 Dalvik 时代的解释执行 / JIT，到 ART 全量 AOT，再到 Android 7.0 之后的混合编译模式，核心取舍围绕安装时间、存储占用和运行时性能展开。

- 🔹 **JIT 编译器的工作原理**：[已验证: AOSP art/runtime/jit/]
  包括方法热度追踪、JIT code cache、Profile 收集与持久化，以及这些行为对冷启动路径的影响。

- 🔹 **dex2oat 的编译流程与 compiler filter**：[已验证: AOSP art/dex2oat/ + source.android.com/docs/core/runtime/dex2oat]
  说明 DEX 到 OAT / VDEX 的转换链路，以及 `verify`、`speed`、`speed-profile` 等编译级别的取舍。

- 🔹 **PGO / Baseline Profiles / Startup Profiles 的分工**：[已验证: developer.android.com/topic/performance/baselineprofiles/overview]
  区分本地 JIT Profile、Baseline Profiles、Cloud Profiles 和 Startup Profiles 分别解决的启动与运行时问题。

- 🔹 **在 Perfetto 和命令行工具中的观测方式**：[待补充: 真实 Trace 截图]
  说明 `art::jit::*`、`dex2oat` 进程、`oatdump`、`profman` 等观测入口，帮助我们判断编译是否成为性能瓶颈。

- 🔹 **应用侧实践与常见误区**：[已验证: developer.android.com + source.android.com]
  结合 Baseline Profiles、Startup Profiles、CI 自动生成流程和常见误区，把编译知识落到启动优化实践中。
<!-- outline-end -->

## 为什么要了解 ART 编译管线

我们在 Perfetto 中分析冷启动时，经常会看到应用进程的 `bindApplication` 阶段耗时几百毫秒甚至几秒，其中一个容易被忽略的变量是：**这段代码是以解释执行的方式跑的，还是已经编译成了机器码？**

同一个 APK，在首次安装（没有 Profile）和经过几天使用后（积累了 JIT Profile），冷启动速度可能差距 30% 以上。[待验证: 此数据需与官方基准测试或实测数据核对] 这不是因为代码变了，而是因为**编译策略**变了。ART 编译管线决定了应用代码从 DEX 字节码到机器指令走哪条路，也就是解释执行、JIT 即时编译，还是 AOT 预编译。了解这条管线后，我们就能回答这些问题：

- 冷启动慢，有没有可能是编译策略不够优化？
- 安装耗时过长，跟 dex2oat 有什么关系？
- Baseline Profiles 和 Startup Profiles 到底做了什么？
- 在 Perfetto 中看到 `art::jit::*` 相关的 Slice，意味着什么？

这篇文章把 ART 的编译策略从历史演进到当前架构梳理一遍，目标是读完之后，我们能在 Trace 中定位编译相关的性能问题，并知道如何通过 Profile 体系优化应用的编译路径。

## ART 编译策略的演进史

要理解现在的编译架构，需要知道它为什么长成这样。Android 的编译策略经历了几个关键阶段，每个阶段都是在解决前一个阶段的痛点。

### Dalvik 时代：纯 JIT（Android 2.2）和纯解释执行

最早的 Android（1.x）只有解释执行——每条 DEX 指令都在运行时逐条翻译执行。Android 2.2 引入了 Dalvik JIT，对热点方法进行即时编译。但 JIT 编译本身有开销，而且每次重启应用后 JIT 缓存丢失，需要重新"热身"。

### ART 全量 AOT（Android 4.4–6.0）：解决"热身"问题

ART 在 Android 4.4 引入，核心思路是：**安装时就把所有 DEX 代码编译成机器码**（dex2oat）。这样运行时不需要解释执行也不需要 JIT，直接跑机器码，性能显著提升。

但全量 AOT 有严重的副作用：

- **安装时间暴增**：一个几十 MB 的 APK，dex2oat 可能跑几分钟（低端机上更久）。用户更新应用时看到的"正在优化"进度条就是 dex2oat 在干活。
- **存储占用翻倍**：OAT 文件（编译后的机器码）可能跟原 APK 一样大，甚至更大。
- **OTA 升级痛苦**：系统升级后，所有应用都要重新 dex2oat，这导致 OTA 后首次开机可能要等十几分钟。

### 混合编译模式（Android 7.0+）：JIT + Profile-Guided AOT

Android 7.0 引入了当前架构的基石——**混合编译模式**。核心思路变了：不再一股脑全编译，而是：

1. **安装时只做 verify**（验证 DEX 代码合法性，不做 AOT 编译），安装速度回归正常。
2. **运行时用 JIT 编译热点方法**，同时记录 Profile（哪些方法被频繁调用）。
3. **设备空闲充电时**，后台 dex2oat 根据 Profile 做 AOT 编译，只编译 Profile 中标记的热点方法。

这个架构的关键在于"**按需编译**"——只编译用户真正用到的代码路径。大部分应用有大量冷门功能，全量 AOT 浪费了大量编译时间和存储空间。

### Android 12+：ART 模块化与持续优化

从 Android 12 开始，ART 成为 Mainline 模块（com.android.art），编译优化可以通过 Google Play 系统更新推送，不再需要等系统 OTA。这样一来，Google 在 2025 年推送的 dex2oat 编译时间缩减 18% 优化，就可以直接覆盖 Android 12+ 设备。

### Android 16/17：编译体系的最新演进

Android 16 引入了云编译（Cloud Compilation）系统，Google Play 可以为应用预编译优化后的二进制格式（SDM）。Android 17 强制 static final 字段不可变，使 dex2oat 可以更激进地进行常量折叠和内联。

[图：ART 编译策略演进时间线——从 Dalvik JIT 到混合编译到 Cloud Compilation]

## JIT 编译器的工作原理

混合编译模式下，JIT 编译器是运行时性能的"第一道防线"。应用启动后，在还没有 AOT 编译代码可用之前，性能完全依赖解释执行和 JIT。

### 方法热度追踪

ART 为每个方法维护一个"热度计数器"（hotness counter）。这个计数器跟踪方法的调用次数和后向分支（循环）次数。当计数器超过阈值时，该方法成为 JIT 编译候选。阈值通过系统属性 `dalvik.vm.jitthreshold` 配置，默认值为 10000。注意：这个属性的 `dalvik.vm.` 前缀是 Dalvik 时代的遗留命名，但 ART 运行时仍然读取它——`AndroidRuntime.cpp` 将其解析为 `-Xjitthreshold:` 运行时参数，最终设置到 ART 内部的 `hot_method_threshold_`（art/runtime/jit/jit.cc）。

```cpp
// [伪代码示意，非 AOSP 原始实现]
// 实际入口：art/runtime/jit/jit.cc -> Jit::MaybeCompileMethod(ArtMethod*, Thread*)
// 热度追踪在 interpreter 中通过计数器实现（hotness_count_）
bool MaybeCompileMethod(ArtMethod* method) {
    if (method->GetHotnessCount() > hot_method_threshold_) {
        return jit_code_cache->CompileMethod(method, thread);
    }
    return false;
}
```

这里的关键信息是：JIT 不会立刻编译所有代码。首次执行的方法仍是解释执行，只有被"反复调用"的方法才值得 JIT 编译。应用冷启动路径上的首轮执行，因此往往要先经过解释执行，这也是 Profile-Guided AOT 对冷启动很关键的原因。

### JIT 代码缓存

JIT 编译后的机器码存放在代码缓存（JIT code cache）中。这个缓存的大小可配置：

- 初始大小：`dalvik.vm.jitinitialsize`，默认 64KB（同属 Dalvik 遗留前缀，ART 仍读取）
- 最大容量：`dalvik.vm.jitmaxsize`，默认 64MB

代码缓存会进行垃圾回收——当空间不足时，最早编译且不再被调用的方法会被清除。在实际的大型应用中，JIT 代码缓存的内存占用通常稳定在 4MB 左右。[待验证: 此数值为工程经验值，需在不同设备/应用规模下验证] 这不会对前台应用的内存造成显著压力。

[已验证: AOSP art/runtime/jit/jit_code_cache.cc, JIT 代码缓存管理]

### JIT 的优化策略

JIT 编译器在编译单个方法时，会进行一系列优化：

- **方法内联**：将短小的方法体直接嵌入调用处，消除函数调用开销
- **逃逸分析**：判断对象是否逃逸出方法范围，未逃逸的对象可以在栈上分配而非堆上
- **循环优化**：循环不变量外提、强度削减等
- **类型推导与内联缓存（Inline Cache）**：记录虚方法的实际调用目标，后续可以将虚调用去虚化（devirtualize）为直接调用

JIT 的优化深度通常不及 dex2oat 的 AOT 编译。JIT 受限于编译时间预算，不能让用户在前台感到卡顿；而 dex2oat 在后台编译时有更充足的时间做激进优化。


### 去优化机制（Deoptimization）

AOT 编译的前提是编译时能确定类型和调用关系。但运行时类加载可能引入新的子类，使编译阶段的内联和去虚化决策失效。这时 ART 需要**去优化**（deoptimize）——将已编译的机器码回退到解释执行。

去优化的典型触发场景：

- **类加载导致内联失效**：编译时 A 方法内联了 B 类的实现，运行时加载了 B 的子类 C，内联假设不再成立
- **调试器附加**：`jdwp` 调试器附加时，所有 JIT 编译代码需要去优化，以支持单步执行和断点
- **Proxy 类动态创建**：运行时通过 `java.lang.reflect.Proxy` 创建的类，可能使已有的去虚化决策失效

去优化后，受影响的方法回到解释执行，直到 JIT 重新编译或下一次后台 dex2oat 生成新的 AOT 代码。

在 Perfetto 中，去优化活动表现为 `Deoptimization` Slice。如果在 Trace 中看到大量 Deoptimization，说明运行时的类加载行为与编译阶段的假设不一致，可能需要检查是否有运行时字节码操作（如插件化框架）或动态代理使用过重。

### JIT Profile 的收集与持久化

JIT 运行时收集的 Profile 信息被持久化到 `/data/misc/profiles/cur/0/{package_name}/primary.prof`。这个 Profile 文件记录了：

- 哪些方法被频繁调用
- 方法的调用关系（用于内联决策）
- 类型信息（用于去虚化）

当设备空闲且在充电时，`bg-dexopt` 后台编译守护进程会读取这些 Profile，调用 dex2oat 以 `speed-profile` 编译级别对这些热点方法进行 AOT 编译。这样，下次启动应用时，这些热点方法就有了编译好的机器码，不再需要 JIT "热身"。

### JIT 在 Perfetto 中的表现

在 Perfetto 中，JIT 编译活动主要体现在以下位置：

- **Track**：应用进程下的 `art::jit::*` 相关 Slice
- **典型 Slice**：`Jit compilation`、`Jit method compilation`
- **特征**：如果我们在 Trace 中看到大量 `Jit compilation` Slice 集中在启动阶段，说明应用的 AOT 编译覆盖率不够——热点方法没有在安装时被预编译

[待补充：JIT 编译活动在 Perfetto 中的 Trace 截图]

## dex2oat 编译器深入

JIT 解决了“没有 AOT 编译时怎么办”的问题，但有两个本质限制：每次启动都要重新热身，编译优化深度受限于运行时时间预算。dex2oat 的 AOT 编译正好互补——它有充足的时间做深度优化，编译结果持久化到磁盘，下次启动直接使用。理解 dex2oat 的编译流程和编译级别，是优化应用安装时间和运行时性能的基础。

### 编译流程：DEX → OAT

dex2oat 的输入是 DEX 文件（APK 中的 classes.dex），输出是 OAT 文件（ELF 格式的共享对象，包含编译后的机器码）。编译流程大致如下：

1. **DEX 解析**：读取 DEX 文件，构建类、方法、字段的内部表示
2. **字节码验证**（verify）：检查字节码的合法性（类型安全、栈平衡等）
3. **H 图构建**：将 DEX 字节码转换为 SSA 形式的 H 图（高级中间表示）
4. **优化 Pass**：在 H 图上进行各种优化（内联、常量折叠、死代码消除、逃逸分析、去虚化等）
5. **代码生成**：将优化后的 H 图 lowering 为目标架构的机器码（ARM64/x86_64）
6. **输出 OAT**：将编译结果写入 OAT 文件（ELF 格式），同时生成 VDEX 文件（存储原始 DEX 的快速验证信息）

```
DEX bytecode
    ↓ verify
    ↓ H-Graph construction
    ↓ optimization passes (inline, constant folding, DCE, escape analysis)
    ↓ register allocation
    ↓ code generation (ARM64/x86_64)
    ↓
OAT (ELF) + VDEX
```

### 编译级别（Compiler Filter）

dex2oat 通过编译过滤器（compiler filter）控制编译的深度和范围。不同的编译级别在安装时间、存储占用和运行时性能之间做不同的权衡：

| 编译级别 | 行为 | 适用场景 |
|---------|------|---------|
| `verify` | 只做字节码验证，不编译 | 首次安装（快速）、OTA 后首次启动 |
| `quicken` | 验证 + 部分 DEX 指令优化 | Android 11 及以下的首次启动 |
| `speed` | 全量 AOT 编译所有方法 | 性能要求高的系统应用 |
| `speed-profile` | 只编译 Profile 中标记的方法 | **默认的编译级别**（Android 12+） |
| `everything` | 编译所有方法（含未验证的） | 极少使用 |

[已验证: AOSP art/dex2oat/dex2oat_options.cc, 编译过滤器定义]

**`speed-profile` 是 Android 12+ 的默认编译级别**。如果应用没有提供 Baseline Profiles、没有积累本地 JIT Profile，`speed-profile` 实际上等于 `verify`，也就是不会产生 AOT 编译结果。这也解释了为什么首次安装的应用启动特别慢。

### dex2oat 的多线程编译

dex2oat 支持多线程并行编译，线程数由 `dalvik.vm.dex2oat-threads` 控制。在 8 核设备上，默认可能使用 4-6 个线程并行编译不同的 DEX 方法。

对于大型应用（如包含多个 DEX 文件的应用），多线程编译可以显著减少编译时间。但同时，编译过程会消耗大量 CPU 和内存，这也是为什么 dex2oat 通常在设备空闲充电时才全量运行。

### dex2oat 编译优化进展

ART 团队持续在优化 dex2oat 的编译速度。2025 年的两个里程碑：

- **2025-06**：第一批优化推送，编译时间缩减约 10%
- **2025-12**：第二批优化推送，累计编译时间缩减 **18%**（不降低编译质量、不增加峰值内存）

这些优化通过 Mainline 更新推送到 Android 12+ 的设备。

[已验证: Google Blog, Android Performance Updates 2025, dex2oat 18% 编译时间缩减]

## Profile-Guided Optimization (PGO) 体系

ART 的编译优化核心是 **Profile-Guided Optimization**——用真实的使用数据指导编译决策。整个 PGO 体系由三层 Profile 构成：

### 三层 Profile 来源

**第一层：本地 JIT Profile**

设备在运行应用时，JIT 编译器自动收集的热点方法信息。存储在 `/data/misc/profiles/cur/0/{pkg}/primary.prof`。这是我们前面提到的——应用用了几天之后，后台 dex2oat 会根据这个 Profile 做编译。

限制：需要用户实际使用过应用才能积累，冷启动路径在首次安装时没有覆盖。

**第二层：Baseline Profiles（开发者主导）**

Baseline Profiles 是**开发者在应用中预先定义的 Profile**，告诉系统哪些代码路径是关键的（如启动路径、核心交互路径）。它的工作方式是：

1. 开发者编写 `baseline-prof.txt`（人类可读的规则文件）
2. AGP 在构建时将其转换为二进制格式 `baseline.prof` 和 `baseline.profm`
3. 打包进 APK/AAB
4. 应用安装时，ART Service 读取 Baseline Profiles，以 `speed-profile` 级别编译其中标记的方法

Baseline Profiles 的核心价值：**Day-0 性能**。不需要等用户先用几天，安装完就立刻有 AOT 编译覆盖。Google 官方数据表明，正确配置 Baseline Profiles 可以提升约 30% 的代码执行速度。[待验证: 需定位 Google 官方基准测试报告出处]

**第三层：Cloud Profiles（Google Play 聚合）**

Google Play 收集大量用户的使用数据，聚合生成 Cloud Profiles。当用户从 Play Store 安装应用时，Cloud Profiles 会跟 Baseline Profiles 合并，指导安装时的 dex2oat 编译。

Cloud Profiles 的优势是覆盖面广——它反映的是真实用户的普遍使用模式，而不仅仅是开发者的假设。但只有通过 Google Play 分发的应用才能获取。

### Startup Profiles：DEX 布局优化

上面三层 Profile 优化的都是“编译哪些方法”，但编译覆盖率只是冷启动性能的一个维度。另一个容易被忽视的维度是 **DEX 文件的物理布局**——即使所有启动方法都已 AOT 编译，如果这些方法散落在不同的 DEX 文件中，类加载器的 I/O 开销仍然不可忽视。Startup Profiles 解决的就是这个问题。

Startup Profiles 是 Baseline Profiles 的**启动子集**，但它影响的不是编译策略，而是 DEX 文件的物理布局。

这里的关键在于类加载器的加载顺序：它按顺序从 classes.dex 开始加载类。如果启动路径上的类散落在 DEX 文件的不同位置（甚至不同的 DEX 文件中），类加载器需要更多的 I/O 操作和内存映射。Startup Profiles 的作用是告诉 R8/D8 编译器：**把这些启动类排列到 classes.dex 的前部**。

```
没有 Startup Profiles：
  classes.dex: [辅助类, 工具类, 启动关键类A, 配置类, 启动关键类B, ...]
  classes2.dex: [启动关键类C, 其他类, ...]

有 Startup Profiles：
  classes.dex: [启动关键类A, 启动关键类B, 启动关键类C, 辅助类, 工具类, ...]
  classes2.dex: [配置类, 其他类, ...]
```

AGP 8.3 起，DEX 布局优化（`dexLayoutOptimization`）默认启用。实际效果：**使用 Startup Profiles + DEX Layout 后，冷启动速度比单独使用 Baseline Profiles 快 15-30%**。

[已验证: 官方文档 developer.android.com, Startup Profiles 与 DEX Layout 优化]

### AutoFDO：内核级 PGO

AutoFDO（Automatic Feedback-Directed Optimization）把 PGO 的思想扩展到了内核层面。Google 在 Pixel 设备上运行 Top 100 热门应用，采集硬件性能计数器（performance counter）数据，然后用这些数据指导 LLVM Clang 编译器对内核代码进行优化。

为什么优化内核很重要？因为 **Android 内核占设备 CPU 时间的约 40%**。内核中 Binder 驱动、内存管理、调度器、I/O 栈都是高频执行路径。

AutoFDO 在 Pixel 设备上的量化效果：

- 冷启动提升 3.0%-4.3%
- Binder-rpc 提升 19.5%-21.7%
- binder-addints 提升 12.3%-37.7%
- HwBinder 提升 11.7%-20%
- 开机时间缩短 2%

目前 AutoFDO 优化已合入 `android16-6.12` 和 `android15-6.6` 两个 GKI 内核分支，覆盖 Pixel 6 及更新设备。非 Pixel 设备需要 OEM 自行集成（依赖 perf 事件采集和 LLVM AutoFDO 工具链）。关于 AutoFDO 的内核实现细节和 OEM 集成方法，详见 §1.12 AutoFDO 反馈导向编译优化。

[已验证: Google Blog, AutoFDO GKI 内核级优化, Pixel 8 量化数据]

## 在 Perfetto 和工具中的表现

了解 ART 编译管线后，我们需要知道在 Trace 中怎么观察编译相关的活动。

### JIT 编译活动

在 Perfetto 中，JIT 编译活动表现为应用进程中的 Slice：

- **Track**：应用进程 → `art::jit` 相关线程
- **关键 Slice**：
  - `Jit compilation` / `Jit method compilation`：单方法的 JIT 编译
  - `Jit trampoline`：JIT 编译前的跳板代码（用于方法首次调用时触发 JIT）
- **诊断场景**：如果启动阶段出现密集的 `Jit compilation` Slice，说明应用的 AOT 编译覆盖率不足

### dex2oat 编译过程

dex2oat 编译在以下场景可见：

- **安装时**：`system_server` 进程中的 `dex2oat` 子进程
- **后台优化**：后台编译服务（Android 13 及以下为 `bg-dexopt`，Android 14+ 为 ART Service `MaintenanceJobs`）
- **OTA 后**：系统更新后的批量 recompile

在 Perfetto 中，dex2oat 会作为一个独立进程出现，我们可以直接观察它的 CPU 使用率和线程活动。

### art::jit::* 相关 Slice 含义

| Slice | 含义 |
|-------|------|
| `Jit compilation` | 正在进行 JIT 编译 |
| `Jit code cache` | 代码缓存的分配/回收 |
| `Jit trampoline` | 方法首次调用时触发编译的跳板 |

### oatdump 和 profman 工具

除了 Trace，还有两个命令行工具对分析编译状态很有用：

- **oatdump**：分析 OAT 文件内容，查看哪些方法被 AOT 编译了
  ```bash
  oatdump --oat-file=/data/app/~~xxx/com.example-xxx/oat/arm64/base.odex
  ```
- **profman**：分析 Profile 文件内容，查看哪些方法被标记为热点
  ```bash
  profman --dump-profile-file=/data/misc/profiles/cur/0/com.example/primary.prof
  ```
  输出中关注 `methods` 条目数——如果为 0，说明 Profile 尚未积累数据或未生效。也可以用 `--dump-only` 快速查看 Profile 中标记的方法数量，判断覆盖率。

### 如何通过 Trace 判断编译瓶颈

当我们怀疑编译策略影响了应用性能时，可以按以下步骤排查：

1. **检查安装时的编译级别**：通过 `dumpsys package dexopt` 查看应用当前的编译状态
2. **对比首次安装 vs 使用后的启动 Trace**：首次安装应该能看到更多 JIT 活动
3. **检查 Baseline Profiles 是否生效**：编译状态应该是 `speed-profile` 而非 `verify`
4. **观察后台编译时间线**：空闲充电时后台编译服务（`bg-dexopt` / ART Service `MaintenanceJobs`）是否正常运行

## 实战：优化 App 的编译性能

了解了 ART 编译管线的工作原理，接下来我们看看如何在实际工作中应用这些知识来优化应用的编译路径。

### 如何为应用添加 Baseline Profiles

Android Studio 提供了 Baseline Profiles 的生成模板：

1. 使用 Jetpack Macrobenchmark 库录制关键用户路径
2. Android Studio 自动生成 `baseline-prof.txt`
3. 将其放入 `src/main/` 目录，AGP 构建时自动处理

```kotlin
// build.gradle.kts
android {
    baselineProfile {
        // AGP 8.3+ 默认启用 DEX layout 优化
        // 手动为每个 variant 配置 Startup Profile
    }
}
```

关键建议：Baseline Profiles 应该覆盖**冷启动路径**和**核心交互路径**（如首页滑动、搜索），但不应该包含所有代码——Profile 越大，安装时编译越慢。

### 如何配置 Startup Profiles

Startup Profiles 是 AGP 8.3+ 的新特性，配置在 `baselineProfile {}` 块中：

```kotlin
// build.gradle.kts
android {
    baselineProfile {
        dexLayoutOptimization = true  // AGP 8.3+ 默认 true
    }
}
```

Startup Profiles 的文件名通常是 `startup-prof.txt`，放在 `src/main/` 目录下。它只列出启动路径上的类和方法，R8/D8 编译器会将这些类集中到 classes.dex 的前部。

实测效果：综合使用 Baseline Profiles + Startup Profiles，总体启动和运行时性能可提升 30% 以上。

[已验证: 官方文档, Baseline + Startup Profiles 综合效果]

### 如何在 CI 中自动生成和更新 Profiles

自动化流程：

1. CI 中运行 Macrobenchmark 测试，生成 `baseline-prof.txt`
2. 将生成的 Profile 文件提交到代码仓库
3. 每次发布新版本前，更新 Profile 确保覆盖最新的代码路径

### 常见问题：Profile 不生效的原因排查

- **编译级别是 `verify`**：检查系统属性 `pm.dexopt.install`，确认安装时使用的是 `speed-profile`
- **Profile 文件为空或格式错误**：用 `profman --dump-profile-file` 检查
- **AGP 版本过低**：Startup Profiles 需要 AGP 8.3+，Baseline Profiles 需要 AGP 7.0+
- **应用被系统回退到 `verify`**：存储空间不足时，系统可能清除 OAT 文件，回退到 `verify`
- **Mainline 更新导致编译缓存失效**：ART 模块更新后，所有应用的 OAT 文件需要重新编译

### 编译优化与其他启动优化手段的协同

编译优化不是孤立的。在 §8.3 启动优化策略 中我们会更详细地讨论，但这里需要指出几个协同点：

- **Startup Profiles + DEX Layout** 解决的是类加载 I/O 的问题，跟代码本身的耗时无关
- **Baseline Profiles** 解决的是代码执行效率的问题，把解释执行/JIT 热身变成 AOT 机器码
- 两者加上传统的启动优化（延迟初始化、异步加载、闪屏优化），形成完整的冷启动优化链路

## 与其他机制的关系

ART 编译管线与全书多个章节有交叉：

- **§1.6 版本演进**：编译策略的演进是 Android 架构演进的重要组成部分
- **§4.3 ART 内存管理**：JIT 代码缓存、编译过程的内存占用都在 ART 的内存预算中
- **§8.2 App 启动全流程**：编译策略直接决定启动路径上代码的执行效率
- **§8.3 启动优化策略**：Baseline Profiles 和 Startup Profiles 是启动优化的关键手段
- **§16.1 Google 官方优化思路**：AutoFDO 和 dex2oat 编译优化是 Google 持续投入的方向

## 版本演进

| 版本 | 编译策略变化 | 性能影响 |
|------|------------|---------|
| Android 4.4 | ART 引入，全量 AOT | 安装慢、存储大、运行快 |
| Android 5.0-6.0 | 全量 AOT 为默认 | OTA 后批量 recompile 痛点 |
| Android 7.0 | 混合编译（JIT + Profile-Guided AOT） | 安装快、存储小、渐进式性能提升 |
| Android 8.0 | JIT code cache 从 2MB 扩展到 64MB；多 dex 支持优化 | JIT 覆盖率大幅提升 |
| Android 9.0 | Profile 引导的后台编译优化 | 后台 dex2oat 覆盖率提升 |
| Android 10 | Hidden API 限制开始执行，影响反射调用编译路径 | 运行时兼容性约束增加 |
| Android 12 | ART 模块化（Mainline） | 编译优化可独立推送 |
| Android 13 | Baseline Profiles 通过 Mainline 推送到设备 | 首次安装 AOT 覆盖率提升 |
| Android 14 | ART Service 统一管理编译调度（取代 BackgroundDexOptService） | 编译管理更统一 |
| Android 16 | Cloud Compilation / SDM 格式 / AutoFDO 内核 | 安装体验改善、内核性能提升 |
| Android 17 | static final 不可变 → 更激进的常量折叠 + 分代 GC | 编译优化深度提升、GC 暂停减少 |

## 常见问题与误区

**误区一："AOT 编译的应用一定比 JIT 快"**

不一定。dex2oat 的 `speed-profile` 只编译 Profile 中的方法。如果 Profile 覆盖率低，大部分方法仍然是解释执行。而 JIT 在运行时会根据实际调用动态编译，理论上可以覆盖更多热点。AOT 的优势在于**不需要运行时编译开销**——没有编译延迟、不占运行时 CPU。

**误区二："Baseline Profiles 能加速所有代码"**

Baseline Profiles 只对其中标记的代码路径生效。如果冷启动路径有 200 个方法，但 Baseline Profiles 只覆盖了 50 个，剩余 150 个方法仍然是解释执行。Profile 的覆盖完整性决定了实际效果。

**误区三："dex2oat 编译越快越好"**

编译速度和编译质量是 trade-off。如果编译速度提升导致优化 pass 被跳过（如方法内联、常量折叠），运行时性能会下降。ART 团队在 2025 年的 18% 编译提速是在**不降低编译质量、不增加峰值内存**的前提下实现的——优化的对象是编译器内部的数据结构和调度策略，而非砍掉优化 pass。

**误区四："安装时不需要优化，后台慢慢编就行"**

后台编译需要设备空闲 + 充电。如果用户安装后立刻使用（这也是最常见的场景），在后台编译完成之前，应用完全依赖解释执行和 JIT。这就是 Baseline Profiles 存在的意义——确保安装时就有编译覆盖。

**误区五："oatdump 显示方法已编译，但启动还是慢——编译没起作用"**

方法被编译不代表被使用。如果应用启动时的类加载器没有正确找到 OAT 文件中的编译代码（如 multi-dex 布局不佳、类加载顺序问题），仍然会回退到解释执行。需要同时检查编译状态和 DEX 布局。

## 参考资料

### AOSP 源码路径
- `art/compiler/`：ART 编译器核心（H 图、优化 pass、代码生成）
- `art/dex2oat/`：dex2oat 工具入口和编译管线
- `art/jit/`：JIT 编译器实现
- `art/runtime/jit/jit_code_cache.cc`：JIT 代码缓存管理
- `art/runtime/jit/profile_saver.cc`：Profile 持久化
- `art/libprofile/`：Profile 文件格式处理

### 官方文档
- [Baseline Profiles 概览](https://developer.android.com/topic/performance/baselineprofiles/overview)
- [ART 与 Dalvik](https://source.android.com/docs/core/runtime)
- [dex2oat 编译选项](https://source.android.com/docs/core/runtime/dex2oat)
- [Profile-Guided 代码优化](https://source.android.com/docs/core/runtime/pgodexopt)

### 深入阅读
- Google Blog: Android Performance Updates 2025（dex2oat 编译优化、AutoFDO）
- Google Blog: AutoFDO for Android Kernel（内核级 PGO）
- Android 17 Developer Features: static final field 不可变性行为变更
