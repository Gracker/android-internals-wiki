---
title: ART 编译管线与 dex2oat 优化
chapter: '1.7'
section: '1.7'
drafted_date: '2026-04-05'
drafted_by: openclaw-task2a
applicable_versions: Android 7.0 (API 24) - Android 17 (API 37)
last_verified: '2026-04-05'
last_verified_against: AOSP android-16.0.0_r1 + Android 17 official docs
confidence: medium
polish_count: 2
polish_date: '2026-04-17'
polish_by: task2b-polish
reviewed_date: "2026-05-07"
reviewed_by: openclaw-task6
task6_result: pass-light-edit
sources:
- type: official
  path: https://developer.android.com/topic/performance/baselineprofiles/overview
- type: official
  path: https://source.android.com/docs/core/runtime
- type: blog
  path: https://android-developers.googleblog.com/ (ART Performance Updates 2025)
- type: aosp
  path: art/compiler/ + art/dex2oat/ + art/runtime/jit/
- type: blog
  path: https://android-developers.googleblog.com/ (AutoFDO GKI Kernel)
tags:
- ART
- dex2oat
- JIT
- AOT
- Baseline-Profiles
- Startup-Profiles
- PGO
- compilation
- cold-start
related_chapters:
- '1.6'
- '1.12'
- '4.3'
- '8.2'
- '8.3'
- '16.1'
task2b_result: "fixed"
task6_state: "revisiting"
review_round: 5
repaired_date: "2026-04-25"
repaired_by: "openclaw-task2b"
review_notes: "2026-05-03 task9 deep-review: needs-rework。P0 1 / P1 1 / P2 1；P0/P1 写入 queue.json，P2 写入 suggestions.md。"
last_task6_at: "2026-05-07T09:06:00+08:00"
last_task6_review_log: "logs/review/2026-05-07-09-review.md"
task6_review_notes: "2026-05-07 task6 revisiting review 09:06: pass-light-edit。小修 Cloud Compilation 命中时的 `dex2oat` 进程表述；L1/L2 通过，无新增 B 类大问题，转入 Task9 复审。"
status: "ready-for-review"
pipeline_stage: "task6_pending"
task9_result: needs-rework
task9_state: "pending"
last_task2b_at: "2026-05-26T03:19:12+08:00"
task2b_state: "fixed"
task9_reviewed_date: 2026-05-07
task9_reviewed_by: openclaw-task9
last_task9_at: "2026-05-26T00:20:00+08:00"
task9_review_notes: "2026-05-26 Task9 00:20 闲时抽检：needs-rework。P0 1 / P1 1 / P2 0；compiler filter 源码锚点应改为 libartbase/base/compiler_filter.{h,cc}；`android-17-beta3` 不是公开 AOSP ref，Android 17 行为需改用官方 docs / 可复现公开分支口径。"
last_task6_audit: "2026-05-22"
last_task6_audit_log: "logs/review/2026-05-22-20-audit.md"
last_task9_review_log: "logs/deep-review/2026-05-26-00-audit.md"
last_task9_audit: 2026-05-26
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
  说明 DEX 到 OAT / VDEX 的转换流程，以及 `verify`、`speed`、`speed-profile` 等编译级别的取舍。

- 🔹 **PGO / Baseline Profiles / Startup Profiles 的分工**：[已验证: developer.android.com/topic/performance/baselineprofiles/overview]
  区分本地 JIT Profile、Baseline Profiles、Cloud Profiles 和 Startup Profiles 分别解决的启动与运行时问题。

- 🔹 **在 Perfetto 和命令行工具中的观测方式**：[待补充: 真实 Trace 截图]
  说明 `art::jit::*`、`dex2oat` 进程、`oatdump`、`profman` 等观测入口，用于判断编译是否成为性能瓶颈。

- 🔹 **应用侧实践与常见误区**：[已验证: developer.android.com + source.android.com]
  结合 Baseline Profiles、Startup Profiles、CI 自动生成流程和常见误区，把编译知识落到启动优化实践中。
<!-- outline-end -->

## 为什么要了解 ART 编译管线

在 Perfetto 中分析冷启动时，经常会看到应用进程的 `bindApplication` 阶段耗时几百毫秒甚至几秒，其中一个容易被忽略的变量是：**这段代码是以解释执行的方式跑的，还是已经编译成了机器码？**

同一个 APK，在首次安装（没有 Profile）和经过几天使用后（积累了 JIT Profile），冷启动速度的差距取决于应用体积、启动路径复杂度和 Profile 覆盖率。Google 官方文档给出 Baseline Profiles 的冷启动收益参考：平均提升约 30%，低端设备上可达 40%。这些数值来自 Google 内部 Macrobenchmark 基准测试，具体条件（设备型号、Android 版本、样本量）参见 developer.android.com/topic/performance/baselineprofiles/overview。实际收益需用同一 release 包、同一设备、同一测试脚本对照确认。背后的变量是**编译策略**：ART 编译管线决定了应用代码从 DEX 字节码到机器指令走哪条路，也就是解释执行、JIT 即时编译，还是 AOT 预编译。了解这条管线后，可以回答这些问题：

- 冷启动慢，有没有可能是编译策略不够优化？
- 安装耗时过长，跟 dex2oat 有什么关系？
- Baseline Profiles 和 Startup Profiles 到底做了什么？
- 在 Perfetto 中看到 `art::jit::*` 相关的 Slice，该怎么解读？

这篇文章把 ART 的编译策略从历史演进到当前架构梳理一遍，目标是读完之后，读者能在 Trace 中定位编译相关的性能问题，并知道如何通过 Profile 体系优化应用的编译路径。

## ART 编译策略的演进史

要理解现在的编译架构，需要知道它为什么长成这样。Android 的编译策略经历了几个关键阶段，每个阶段都是在解决前一个阶段遗留的问题。

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

这个架构的核心原则是"**按需编译**"——只编译用户实际用到的代码路径。大部分应用有大量冷门功能，全量 AOT 浪费了大量编译时间和存储空间。

### Android 12+：ART 模块化与持续优化

从 Android 12 开始，ART 成为 Mainline 模块（com.android.art），编译优化可以通过 Google Play 系统更新推送，不再需要等系统 OTA。具体变化：

- **编译器优化独立推送**：dex2oat 内部的优化 Pass 改进（如 2025 年的 18% 编译时间缩减）作为 Mainline 模块更新推送到所有 Android 12+ 设备，不需要 OEM 适配
- **Profile 格式版本解耦**：Profile 文件格式（`primary.prof`）的升级不再依赖系统版本，ART 模块自行处理向后兼容
- **BackgroundDexOptService 演进为 ART Service**（Android 14+）：后台编译调度从 `BackgroundDexOptService`（系统框架代码）迁移到 ART Service（Mainline 模块代码），使得编译调度策略可以更快迭代
- **Cloud Profiles 的分发通道**：Cloud Profiles 的解析和合并逻辑随 ART 模块更新，Google 可以在不发版的情况下调整 Profile 合并策略

### Android 16/17：编译体系的最新演进

**Cloud Compilation 与 SDM（Android 16）。** Android 16 公开了 Cloud Compilation 路径：Play Store 可直接下发预编译的 `.odex` / `.vdex` 产物，设备跳过本地 dex2oat。配合 SDM（Secure Dex Metadata）校验机制，确保下载的编译产物与设备上的 APK 完全匹配。这解决了两个长期问题：OTA 后首次开机的批量 dex2oat（"正在优化应用"），以及低端设备上 dex2oat 本身耗时过长。对性能分析的影响：Cloud Compilation 命中时，Perfetto 中安装阶段的 `dex2oat` 独立进程将不再出现；如果仍然看到 `dex2oat` 活动，说明该安装来源或设备策略未命中 Cloud Compilation。

**Android 17 编译侧变化。** Android 17 把 `static final` 的行为约束收得更紧（运行时不可通过反射修改），这给编译器提供了更稳定的前提——常量传播、分支裁剪和内联缓存的假设空间更宽。但具体能换来多少常量折叠或内联收益，还要看 ART 版本和实际命中的优化路径。此外，Android 17 将分代 GC（Generational GC）设为默认，GC 暂停时间分布与旧版 CC 有显著差异，这在 §4.3 ART 内存管理中有详细讨论。

[图：ART 编译策略演进时间线——从 Dalvik JIT 到混合编译到 Cloud Compilation]

## JIT 编译器的工作原理

混合编译模式下，JIT 编译器是运行时性能的"第一道防线"。应用启动后，在还没有 AOT 编译代码可用之前，性能完全依赖解释执行和 JIT。

### 方法热度追踪

ART 为每个方法维护热度计数。这个计数同时观察方法调用和后向分支（循环）次数；达到阈值后，运行时才会把该方法送进 JIT 编译路径。阈值由系统属性 `dalvik.vm.jitthreshold` 控制，默认值常见为 10000。这个属性的 `dalvik.vm.` 前缀沿用了 Dalvik 时代的命名，但 ART 仍会读取它，`AndroidRuntime.cpp` 会把它转换成 `-Xjitthreshold:` 运行时参数，再传给 `art/runtime/jit/` 中的 JIT 实现。

```cpp
// [流程示意，非 AOSP 原始实现]
// 公开分支里可直接核对的是 Jit::CompileMethod() / CompileMethodInternal()；
// 热度统计和编译触发条件分布在解释器与运行时路径中。
if (method_hotness >= hot_method_threshold_) {
    jit->CompileMethod(/* current thread */, /* target method */);
}
```

JIT 不会在方法第一次执行时就把所有代码编译成机器码。冷启动路径的首轮执行常常仍然落在解释执行上，Profile-Guided AOT 的价值也就落在这里。

### JIT 代码缓存

JIT 编译后的机器码存放在代码缓存（JIT code cache）中。这个缓存的大小可配置：

- 初始大小：`dalvik.vm.jitinitialsize`，默认 64KB（同属 Dalvik 遗留前缀，ART 仍读取）
- 最大容量：`dalvik.vm.jitmaxsize`，默认 64MB

代码缓存会在空间压力下触发回收，`JitCodeCache::GarbageCollectCache()`（`art/runtime/jit/jit_code_cache.cc`）负责处理这件事。公开源码能稳定确认的边界主要有三条：

- **触发条件**：新的编译产物放不进当前 code cache 时，会进入回收流程。
- **回收约束**：仍被活动栈帧引用的代码不能直接回收，调试信息和 code/data 区的管理也要一起维护。
- **结果形态**：回收后腾出的空间会继续提供给后续 JIT 编译使用，但具体淘汰顺序属于 `JitCodeCache` 的内部策略，正文不把它写成固定算法。

在实际的大型应用中，JIT 代码缓存的内存占用通常稳定在 4MB 左右。[待验证: 此数值为工程经验值，需在不同设备/应用规模下验证] 这不会对前台应用的内存造成显著压力。

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

当设备进入空闲维护窗口时，后台 dexopt / ART Service 会读取这些 Profile，并按设备策略选择 compiler filter。命中 Baseline、本地 JIT 或云侧 Profile 时，常见结果是 `speed-profile`；如果没有可用 Profile，或者安装来源与设备策略不同，也可能退回到 `verify` 等其他结果。下次启动能否直接用上机器码，最终要看当前设备上实际落下来的编译状态。

### JIT 在 Perfetto 中的表现

在 Perfetto 中，JIT 编译活动主要体现在以下位置：

- **Track**：应用进程下的 `art::jit::*` 相关 Slice
- **典型 Slice**：`Jit compilation`、`Jit method compilation`
- **特征**：如果 Trace 中出现大量 `Jit compilation` Slice 集中在启动阶段，说明应用的 AOT 编译覆盖率不够——热点方法没有在安装时被预编译

**Perfetto 抓取配置建议。** 观察 JIT 编译活动时，建议在 Perfetto config 中启用以下数据源：

```protobuf
data_sources: {
    config {
        name: "linux.ftrace"
        ftrace_config {
            ftrace_events: "sched/sched_switch"
            atrace_categories: "dalvik"
        }
    }
}
```

AOSP atrace category 表中 ART/VM 对应的是 `dalvik`（`ATRACE_TAG_DALVIK`），不是 `art`。使用 `atrace_categories: "dalvik"` 才能捕获 `art::jit::*` 系列 Slice。如果看不到这些 Slice，检查设备是否为 userdebug/eng 版本（user 版本可能限制了 atrace category），以及 `persist.sys.atrace.rcpreroll` 设置。抓取完成后，在 Perfetto UI 的进程轨道中搜索 `Jit compilation` 即可定位编译活动。

## dex2oat 编译器深入

JIT 解决了“没有 AOT 编译时怎么办”的问题，但有两个本质限制：每次启动都要重新热身，编译优化深度受限于运行时时间预算。dex2oat 的 AOT 编译正好互补——它有充足的时间做深度优化，编译结果持久化到磁盘，下次启动直接使用。理解 dex2oat 的编译流程和编译级别，是优化应用安装时间和运行时性能的基础。

### 编译流程：DEX → OAT

dex2oat 的输入是 DEX 文件（APK 中的 classes.dex），输出是 OAT 文件（ELF 格式的共享对象，包含编译后的机器码）。编译流程大致如下：

1. **DEX 解析**：读取 DEX 文件，构建类、方法、字段的内部表示
2. **字节码验证**（verify）：检查字节码的合法性（类型安全、栈平衡等）
3. **H 图构建**：将 DEX 字节码转换为 SSA 形式的 H 图（高级中间表示）
4. **优化 Pass**：在 H 图上进行各种优化。H 图采用 **SSA 形式**（Static Single Assignment）——每个变量只被赋值一次，每个使用点通过 φ 函数（phi node）合并控制流分支的值。SSA 形式简化了数据流分析，使得常量传播、死代码消除等优化可以在一次遍历中完成。主要的优化 Pass 包括：
   - **方法内联**：将短小方法的调用替换为方法体本身，消除函数调用开销（参数传递、栈帧切换）
   - **常量折叠与传播**：编译时可确定的计算直接算出结果，如 `int x = 2 * 3` → `int x = 6`。Android 17 收紧了 `static final` 的行为边界，这给此类优化提供了更稳定的前提（详见版本演进表）
   - **死代码消除（DCE）**：移除不可达的代码路径和未使用的变量赋值
   - **逃逸分析**：判断对象是否"逃逸"出方法范围。未逃逸的对象可以在栈上分配而非堆上，减少 GC 压力
   - **去虚化（Devirtualization）**：将虚方法调用（`invoke-virtual`）转换为直接调用，基于类型信息或 Profile 中的内联缓存
   - **边界检查消除**：数组访问的边界检查在能证明索引安全时被移除
5. **寄存器分配**：将虚拟寄存器映射到物理寄存器。ARM64 有 31 个通用寄存器，溢出（spill）到栈的操作代价较高。ART optimizing compiler 使用 linear scan register allocation（线性扫描寄存器分配），通过活跃区间分析、寄存器约束和 spill heuristics 分配物理寄存器——源码锚点为 `compiler/optimizing/register_allocator.cc`。编译时间复杂度低于图着色算法，适合移动设备上 dex2oat 的编译预算
6. **代码生成**：将优化后的 H 图 lowering 为目标架构的机器码（ARM64/x86_64）
7. **输出 OAT**：将编译结果写入 OAT 文件（ELF 格式），同时生成 VDEX 文件（存储原始 DEX 的快速验证信息）

```text
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
| `speed-profile` | 只编译 Profile 中标记的方法 | 命中 Baseline / JIT / Cloud Profile 时的常见选择 |
| `everything` | 编译所有方法（含未验证的） | 极少使用 |

[已验证: AOSP art/libartbase/base/compiler_filter.h / compiler_filter.cc, 编译过滤器枚举定义；dex2oat_options.cc 为参数解析入口]

`speed-profile` 在 Android 12+ 设备上很常见，但它不是所有安装来源、所有设备策略下的固定默认值。Baseline Profiles、本地 JIT Profile、Cloud Profile 是否命中，都会影响最终选中的 compiler filter；没有可用 Profile 时，结果可能直接落到 `verify`。判断一台设备上的真实状态，直接看 `cmd package art dump`（Android 14+ 常用）或 `dumpsys package dexopt` 的输出更可靠。

<!-- AIW-源码调研-2026-05-23 -->

## 源码调研补充：ART Verifier Quickening 机制（2026-05-23）

> 本补充基于 AOSP 源码分析，验证了 dex2oat quicken 过滤器的具体含义和 vdex 文件的作用。

### Quicken 过滤器的真实行为

官方文档对 `quicken` 的描述（Android 11 及更低）：Runs DEX code verification and optimizes some DEX instructions to get better interpreter performance。"优化 DEX 指令"指的是将符号引用替换为实际偏移量，例如 `INVOKE_VIRTUAL` 的方法索引在 quickened 后变为直接偏移，去掉了运行时符号查找开销。

[已验证: AOSP source.android.com/docs/core/runtime/configure — quicken 官方描述]

### DexToDex 变换的源码证据

AOSP art 仓库中，DexToDex 转换在 `kOptimize` 级别可能引入 quickened opcodes，将符号引用替换为实际偏移：

> // DexToDex at the kOptimize level may introduce quickened opcodes, which replace symbolic references with actual offsets

[已验证: AOSP android.googlesource.com/platform/art/+/2ed8def — DexToDex quickening 说明]

### Vdex 文件的结构与作用

从 Android 8 起，dex2oat 生成 `.vdex` 文件，官方文档描述其内容：contains some additional metadata to speed up verification, sometimes along with the uncompressed DEX code of the APK。

vdex 的核心价值在于"加速验证的元数据"：verifier 在首次验证时记录类解析结果（方法签名一致性、字段偏移合法性），这些结果写入 vdex。下次加载时，verifier 直接读预计算结果，跳过符号解析过程。

[已验证: AOSP source.android.com/docs/core/runtime/configure — vdex 描述]

### Quicken 与 AOT 的正交关系

quicken 和 AOT 编译是正交的优化路径：
- **quicken**：发生在 DEX 字节码层级，将符号引用替换为实际偏移。输出仍是 DEX 格式（但内容被修改），由解释器执行。Android 11 及更低版本支持。
- **AOT**：发生在编译阶段，将 DEX 字节码编译为原生机器码。输出是 .oat 格式（ELF 格式），由 ART 运行时直接执行。

quicken 不生成原生代码，不能替代 speed/speed-profile。两者可以叠加：先 quicken DEX（解释器执行更快），再对同一 DEX 做 AOT 编译（跳过解释器）。

### 版本边界

| 版本 | quicken 可用性 |
|------|--------------|
| Android 8-11 | 官方支持的过滤器 |
| Android 12+ | 官方文档将 quicken 限定在"Android 11 or lower"，具体状态需 AOSP android-12+ 源码确认 |

[已验证: AOSP source.android.com/docs/core/runtime/configure — quicken 版本标注]

*原始调研报告：[`DeepResearch/2026-05-23-android-art-verifier-quickening-mechanism.md`](obsidian://open?vault=Obsidian&file=DeepResearch%2F2026-05-23-android-art-verifier-quickening-mechanism)*

<!-- AIW-源码调研-2026-05-23 -->

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

设备在运行应用时，JIT 编译器自动收集的热点方法信息。存储在 `/data/misc/profiles/cur/0/{pkg}/primary.prof`。前文已经提到，应用用了几天之后，后台 dex2oat 会根据这个 Profile 做编译。

限制：需要用户实际使用过应用才能积累，冷启动路径在首次安装时没有覆盖。

**第二层：Baseline Profiles（开发者主导）**

Baseline Profiles 是**开发者在应用中预先定义的 Profile**，告诉系统哪些代码路径是关键的（如启动路径、核心交互路径）。它的工作方式是：

1. 开发者编写 `baseline-prof.txt`（人类可读的规则文件）
2. AGP 在构建时将其转换为二进制格式 `baseline.prof` 和 `baseline.profm`
3. 打包进 APK/AAB
4. 应用安装或后续 dexopt 命中 Baseline Profiles 时，ART 常会选择 `speed-profile` 编译其中标记的方法

Baseline Profiles 的核心价值：**Day-0 性能**。不需要等用户先用几天，安装完就立刻有 AOT 编译覆盖。Google 官方文档给出的 Baseline Profiles 收益参考：冷启动平均提升约 30%，低端设备可达 40%。具体幅度取决于应用代码结构、启动路径复杂度、Profile 覆盖率和设备性能。发布稿不把固定百分比写成所有场景的通用结论，实际收益需要用 Macrobenchmark 对照测试确认。[来源: developer.android.com/topic/performance/baselineprofiles/overview]

**第三层：Cloud Profiles（Google Play 聚合）**

Google Play 收集大量用户的使用数据，聚合生成 Cloud Profiles。当用户从 Play Store 安装应用时，Cloud Profiles 会跟 Baseline Profiles 合并，指导安装时的 dex2oat 编译。

Cloud Profiles 的优势是覆盖面广——它反映的是真实用户的普遍使用模式，而不仅仅是开发者的假设。但只有通过 Google Play 分发的应用才能获取。

### Startup Profiles：DEX 布局优化

上面三层 Profile 优化的都是“编译哪些方法”，但编译覆盖率只是冷启动性能的一个维度。另一个容易被忽视的维度是 **DEX 文件的物理布局**——即使所有启动方法都已 AOT 编译，如果这些方法散落在不同的 DEX 文件中，类加载器的 I/O 开销仍然不可忽视。Startup Profiles 解决的就是这个问题。

Startup Profiles 是 Baseline Profiles 的**启动子集**，它影响的是 DEX 文件的物理布局，而非编译策略。

类加载器按顺序从 classes.dex 开始加载类。如果启动路径上的类散落在 DEX 文件的不同位置（甚至不同的 DEX 文件中），类加载器需要更多的 I/O 操作和内存映射。Startup Profiles 的作用是告诉 R8/D8 编译器：**把这些启动类排列到 classes.dex 的前部**。

```text
没有 Startup Profiles：
  classes.dex: [辅助类, 工具类, 启动关键类 A, 配置类, 启动关键类 B, ...]
  classes2.dex: [启动关键类 C, 其他类, ...]

有 Startup Profiles：
  classes.dex: [启动关键类 A, 启动关键类 B, 启动关键类 C, 辅助类, 工具类, ...]
  classes2.dex: [配置类, 其他类, ...]
```

AGP 8.3 起，DEX 布局优化（`dexLayoutOptimization`）默认启用。它的目标是减少启动路径上的类加载 I/O；收益要用同一 release 包、同一设备、同一 Android 版本和同一 Macrobenchmark 脚本对照确认。

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

了解 ART 编译管线后，还要知道在 Trace 中怎么观察编译相关的活动。

### JIT 编译活动

在 Perfetto 中，JIT 编译活动表现为应用进程中的 Slice：

- **Track**：应用进程 → `art::jit` 相关线程
- **关键 Slice**：
  - `Jit compilation` / `Jit method compilation`：单方法的 JIT 编译
  - `Jit trampoline`：JIT 编译前的跳板代码（用于方法首次调用时触发 JIT）
- **诊断场景**：如果启动阶段出现密集的 `Jit compilation` Slice，说明应用的 AOT 编译覆盖率不足

### dex2oat 编译过程

dex2oat 编译在以下场景可见：

- **安装时**：`system_server` / ART Service 发起 dexopt 请求，经 `installd`（或新版 ART Service / `artd` 路径）触发 `dex2oat`；Trace 中直接搜索 `dex2oat` 进程
- **后台优化**：后台编译服务（Android 13 及以下为 `bg-dexopt`，Android 14+ 为 ART Service `MaintenanceJobs`）
- **OTA 后**：系统更新后的批量 recompile

在 Perfetto 中，dex2oat 会作为一个独立进程出现，可以直接观察它的 CPU 使用率和线程活动。

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

### ProfilingManager（Android 15+）的系统级 Trace 触发

除了手动抓取 Trace，Android 15+ 提供了 `ProfilingManager` API，支持应用请求系统自动捕获性能数据：

```kotlin
// Android 15+ (API 35+)
val profilingManager = getSystemService(ProfilingManager::class.java)
val cancellationSignal = CancellationSignal()
profilingManager.requestProfiling(
    ProfilingManager.PROFILING_TYPE_SYSTEM_TRACE,  // 或 HEAP_PROFILE / STACK_SAMPLING
    Bundle(),                                        // 可选参数（trace 持续时间等）
    "my-trace-tag",                                  // tag，用于标识此次请求
    cancellationSignal,
    ContextCompat.getMainExecutor(this),
    { result -> /* 处理 ProfilingResult: result.statusCode, result.resultFilePath */ }
)
```

公开 API 支持四种类型：`PROFILING_TYPE_SYSTEM_TRACE`、`PROFILING_TYPE_HEAP_PROFILE`、`PROFILING_TYPE_JAVA_HEAP_DUMP`、`PROFILING_TYPE_STACK_SAMPLING`。不存在 `PROFILING_TYPE_JAVA_TRACE` 常量。

Android 16 进一步强化了系统触发能力——应用通过 `ProfilingManager.addProfilingTriggers()` 预先注册触发条件（如 ANR、`onFullyDrawn`），系统在触发条件满足时从背景环形缓冲区导出 Trace。关键前提：**应用必须预先注册触发器**，系统不会对所有 App 自动采集 ANR Trace。注册后，系统在采样时间窗内启动后台 trace，结果通过 `ProfilingResult` 回调或文件交付。这对捕获难以复现的启动卡顿特别有价值，但它不是“无需应用参与”的自动机制——开发者需要在代码中完成触发器注册。

触发式采集与手动 `requestProfiling()` 的区别：`requestProfiling()` 是一次性请求，调用后立即开始采样；`addProfilingTriggers()` 注册的是持续监听条件，系统在后续运行中满足条件时自动触发，不需要在 ANR 当下同步抓取。[已验证：AOSP `ProfilingManager.java` / `ProfilingTrigger.java` android-16.0.0_r1]

### 如何通过 Trace 判断编译瓶颈

怀疑编译策略影响应用性能时，可以按以下步骤排查：

1. **检查当前编译状态**：通过 `cmd package art dump` 或 `dumpsys package dexopt` 查看应用当前落下来的 compiler filter
2. **对比首次安装 vs 使用后的启动 Trace**：首次安装通常会看到更多 JIT 活动
3. **检查 Profile 是否命中**：如果安装后仍停在 `verify`，需要继续看 Baseline / 本地 Profile 是否生效
4. **观察后台编译时间线**：空闲维护窗口里，后台编译服务（`bg-dexopt` / ART Service `MaintenanceJobs`）是否正常运行

## 实战：优化 App 的编译性能

了解 ART 编译管线的工作原理后，实际优化要落到应用的编译路径上。

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

效果验证要拆成两组：Baseline Profiles 看解释执行 / JIT 热身是否减少，Startup Profiles 看启动路径类加载 I/O 是否减少。不要把两者的收益合成一个通用百分比。

[已验证: 官方文档, Baseline + Startup Profiles 综合效果]

### 如何在 CI 中自动生成和更新 Profiles

自动化流程：

1. CI 中运行 Macrobenchmark 测试，生成 `baseline-prof.txt`
2. 将生成的 Profile 文件提交到代码仓库
3. 每次发布新版本前，更新 Profile 确保覆盖最新的代码路径

### 常见问题：Profile 不生效的原因排查

- **编译级别是 `verify`**：用 `cmd package art dump` 或 `dumpsys package dexopt` 先确认当前 filter，再回看安装来源、Profile 是否存在以及设备策略
- **Profile 文件为空或格式错误**：用 `profman --dump-profile-file` 检查
- **AGP 版本过低**：Startup Profiles 需要 AGP 8.3+，Baseline Profiles 需要 AGP 7.0+
- **应用被系统回退到 `verify`**：存储空间不足时，系统可能清除 OAT 文件，回退到 `verify`
- **Mainline 更新导致编译缓存失效**：ART 模块更新后，所有应用的 OAT 文件需要重新编译

### 编译优化与其他启动优化手段的协同

编译优化要和其他启动优化一起看。§8.3 启动优化策略会更完整展开，本章保留三个直接相关的边界：

- **Startup Profiles + DEX Layout** 解决的是类加载 I/O 的问题，跟代码本身的耗时无关
- **Baseline Profiles** 解决的是代码执行效率的问题，把解释执行/JIT 热身变成 AOT 机器码
- 两者加上传统的启动优化（延迟初始化、异步加载、闪屏优化），形成完整的冷启动优化组合

## 与其他机制的关系

ART 编译管线与全书多个章节有交叉：

- **§1.6 版本演进**：编译策略的演进是 Android 架构演进的重要组成部分
- **§4.3 ART 内存管理**：JIT 代码缓存、编译过程的内存占用都在 ART 的内存预算中
- **§8.2 App 启动全流程**：编译策略直接决定启动路径上代码的执行效率
- **§8.3 启动优化策略**：Baseline Profiles 和 Startup Profiles 是启动优化的关键手段
- **§16.1 Google 官方优化思路**：AutoFDO 和 dex2oat 编译优化是 Google 持续投入的方向

## 版本演进

| 版本 | ART / 运行时变化 | 性能影响 |
|------|------------|---------|
| Android 4.4 | ART 引入，可选安装期 AOT | 安装更慢、存储占用更高，运行期解释和 JIT 压力下降 |
| Android 5.0-6.0 | ART 成为默认运行时，全量 AOT 是主路径 | OTA 后批量重新编译时间长，安装与存储成本明显 |
| Android 7.0 | 混合编译（JIT + Profile-Guided AOT）成为主路径 | 安装速度恢复，热点代码在运行和空闲维护窗口中逐步编译 |
| Android 8.0/8.1 | `quicken` / `verify` 等 compiler filter 进入常用路径，JIT code cache 上限扩大 | 首次启动更偏向验证和轻量优化，后台再按 Profile 补 AOT |
| Android 9.0 | Hidden API 限制开始执行，反射访问边界收紧 | 依赖隐藏 API 的热路径更容易出现兼容性和优化前提变化 |
| Android 10 | Hidden API 限制继续收紧，灰名单 / 黑名单规则更严格 | 插件化、反射和 Mock 框架需要按目标版本核对运行时行为 |
| Android 12 | ART 模块化（Mainline，com.android.art 模块） | 编译器和运行时优化可以独立更新，不完全依赖系统 OTA |
| Android 14 | ART Service 统一管理编译调度（取代 BackgroundDexOptService 主路径） | 编译调度更集中，设备策略对 dexopt 结果的影响更明显 |
| Android 16 | Cloud Compilation 等云侧编译资料开始公开 | 安装侧编译流程继续演进，应用侧仍以设备上的实际编译状态为准 |
| Android 17 | targetSdk 37+ 下 `static final` 行为进一步收紧；分代 GC（Generational GC）默认启用 | 编译器假设更稳定，但收益要结合 ART 版本与代码形态验证 |

#### Profile 分发口径

Baseline Profiles、ProfileInstaller 和 Play Cloud Profiles 属于应用分发与 Profile 供给口径，不应该写成某个 Android 平台版本单独“引入”的 ART 行为。

| 版本范围 | Baseline Profiles | Play Cloud Profiles |
|:---|:---|:---|
| API 24-27（Android 7.0-8.1） | APK / AAB 内置的 Baseline Profile 依赖 `androidx.profileinstaller` 在首轮运行后安装，后续 dexopt 可据此选择 `speed-profile` | 不支持 |
| API 28+（Android 9+） | Google Play 可在安装时使用应用内置 Baseline Profile；`ProfileInstaller` 仍可作为兜底 | 支持。Google Play 聚合历史用户 Profile，并可与 Baseline Profile 一起影响后续安装和更新 |

#### Android 17 `static final` 行为变化的编译边界

Android 17 公开确认的是 `static final` 的行为约束进一步收紧，运行时可变性比旧版本更小。对编译器来说，这提供了更稳定的前提，常量传播、分支裁剪和内联缓存的假设空间也会更宽。

正文把这一点落成“dex2oat 一定会更激进地做常量折叠和内联”就写过头了。更稳妥的表述是：

- **行为变化可以确认**：字段可变性边界更清楚，编译器不需要像旧版本那样为一部分运行时改写场景保留同样多的防御性假设
- **优化机会可以确认**：`static final` 参与的常量传播、条件折叠和部分内联决策，更容易满足前提
- **收益幅度要按实现核对**：是否真的落成 OAT 中的额外内联、能带来多少启动收益，仍要结合 ART 版本、目标代码形态和具体优化路径验证

排查时，更有价值的做法是看 `oatdump`、编译日志和目标版本下的实际 trace，而不是直接把行为变化换算成固定收益。

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
> 以下路径基于 AOSP `android-16.0.0_r1` 公开 tag 和 `platform/art` main 分支验证。Android 17 行为以官方 Developer 文档为准，部分文件在早期版本中路径或结构可能不同。

- `art/compiler/`：ART 编译器核心（H 图构建、SSA 优化 pass、寄存器分配、代码生成）
- `art/compiler/optimizing/`：具体优化 pass 实现（常量折叠、内联、逃逸分析、去虚化等）
- `art/dex2oat/`：dex2oat 工具入口和编译管线（`dex2oat.cc` 为 main entry）
- `art/libartbase/base/compiler_filter.h` / `compiler_filter.cc`：编译过滤器枚举定义与字符串解析（`CompilerFilter` 类）
- `art/dex2oat/dex2oat_options.cc`：dex2oat 参数解析入口，从命令行读取 compiler filter 选项
- `art/runtime/jit/`：JIT 编译器实现（`jit.cc` 可核对 `Jit::CompileMethod()` / `CompileMethodInternal()` 等核心逻辑）
- `art/runtime/jit/jit_code_cache.cc`：JIT 代码缓存管理和 `GarbageCollectCache()` 回收逻辑
- `art/runtime/jit/profile_saver.cc`：Profile 持久化（后台线程定期将热点信息写入 `primary.prof`）
- `art/libprofile/`：Profile 文件格式处理（`.prof` / `.profm` 二进制格式读写）

### 官方文档
- [Baseline Profiles 概览](https://developer.android.com/topic/performance/baselineprofiles/overview)
- [ART 与 Dalvik](https://source.android.com/docs/core/runtime)
- [dex2oat 编译选项](https://source.android.com/docs/core/runtime/dex2oat)
- [Profile-Guided 代码优化](https://source.android.com/docs/core/runtime/pgodexopt)

### 深入阅读
- Google Blog: Android Performance Updates 2025（dex2oat 编译优化、AutoFDO）
- Google Blog: AutoFDO for Android Kernel（内核级 PGO）
- Android 17 Developer Features: static final field 不可变性行为变更

### ART 编译管线中的 Deoptimization 机制深度解析:触发路径、内部机制与可观测性
- 来源：/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/DeepResearch/ART 编译管线中的 Deoptimization 机制深度解析-触发路径、内部机制与可观测性.md
- 类型：DeepResearch 调研结果
- 摘要：系统梳理 ART deoptimization 的触发路径与运行时实现：从 `QuickExceptionHandler`、`Instrumentation`、CHA 失效到 JVMTI/Hook/Apply Changes，解释编译代码如何回退解释器与 shadow frame，并给出 Perfetto/atrace 的可观测信号，适合定位 attach 调试、热更与 Hook 带来的 jank。
- 注入时间：2026-04-23
- 价值：把 deopt 机制、触发源与观测手段串到一起，适合补强 ART 编译章节的诊断深度。
