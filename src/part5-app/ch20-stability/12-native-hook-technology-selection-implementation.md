---
title: Native Hook 技术选型与实现
chapter: '20.12'
section: '20.12'
status: finalized
applicable_versions: Android 17 (API 37) - Android 17 (API 37)
tags:
- Native Hook
- Inline Hook
- GOT/PLT
- ARM64
- bionic linker
- debuggerd
related_chapters:
- '20.7'
- '20.3'
- '14.7'
confidence: medium-high
last_verified: '2026-08-14'
sources:
- type: deepresearch
  path: DeepResearch/2026-07-14-android17-native-hook-three-schools-inlinhook-arm64.md
- type: aosp
  path: bionic/linker/linker.cpp android-17.0.0_r1
- type: aosp
  path: bionic/linker/linker_relocate.cpp android-17.0.0_r1
- type: aosp
  path: system/core/debuggerd/handler/debuggerd_handler.cpp android-17.0.0_r1
last_body_apply_at: '2026-07-28T07:15:05+08:00'
last_body_apply_run_id: 20260728-071505-5c898420
task2b_state: fixed
task6_state: reviewed
task9_state: reviewed
pipeline_stage: finalized
last_review_finalize_at: '2026-07-28T08:18:33+08:00'
last_review_finalize_run_id: 20260728-081833-99d1a2d7
---

# Native Hook 技术选型与实现

Native Hook 指在进程内修改本地代码（C/C++）的函数解析结果或执行入口，让调用先经过代理函数。改一个地址通常很容易，难点集中在命中范围、并发发布、ABI 一致性、动态装载和平台防护。只按 GOT、Trap、Inline 三个名字选型，容易把不同层级的机制混在一起。

本文以 `android-17.0.0_r1` 为源码基线，讨论普通应用进程中的 arm64（AArch64，64 位 Arm 指令集）Native Hook。Android 17 没有公开的 Hook API，Hook 框架也不会因此获得额外权限。业务代码应优先选择公开 NDK（Native Development Kit）API、编译期插桩、显式代理或系统诊断工具。无法改造调用方，并且诊断收益足以覆盖稳定性成本时，再评估运行时 Hook。

文中沿用源码和业内常用名称：proxy 指 Hook 命中后先进入的代理函数；linker 指 bionic 动态链接器；debuggerd 指 Android 的 Native 崩溃转储组件；ART 指 Android Runtime。

## 1. 先确定要改写哪一层

Native Hook 常见方案处理三个不同对象。PLT（Procedure Linkage Table）负责把外部函数调用引向动态链接结果；GOT（Global Offset Table）保存这类运行时地址。实践中所说的 PLT/GOT Hook，通常修改 GOT 中与动态重定位对应的槽位。

| 方案 | 改写对象 | 能观察到什么 | 主要盲区 |
|---|---|---|---|
| PLT/GOT Hook | 某个 ELF 调用方的导入重定位槽 | 该调用方经动态链接发出的外部函数调用 | 内部直接调用、内联、直接系统调用、已保存的函数指针 |
| Inline Hook | 目标函数入口或函数内指令 | 所有经过该指令地址的执行流 | 无法安全搬迁的指令、已经内联的调用、未命中的其他实现 |
| Trap/Breakpoint Hook | 指令替换为断点，借 `SIGTRAP` 改写上下文 | 命中断点的执行流和寄存器现场 | 信号冲突、调试器抢占、频繁信号带来的高成本 |

ELF（Executable and Linkable Format）是 Android Native 可执行文件和 `.so` 的二进制格式。PLT/GOT Hook 按调用方修改重定位槽，Inline Hook 按目标指令地址修改执行流。两者即使都针对 `malloc`，覆盖面也不同：修改 `libfoo.so` 中 `malloc` 的导入槽，只影响 `libfoo.so` 经该槽发出的调用；修改 `libc.so` 中 `malloc` 的入口，可能影响进程内更多调用者，也会放大递归和并发风险。

Trap Hook 接近用户态软件断点：用断点指令触发 `SIGTRAP`，再由信号处理函数改写执行现场。它与 debuggerd 没有扩展接口关系，也不同于调试器通过 `ptrace` 控制目标线程。框架必须管理或正确串接 `SIGTRAP` 的 signal disposition（信号处置配置），识别自有断点，并通过 `ucontext_t` 读取或修改信号发生时的寄存器和 PC（Program Counter，程序计数器）。

## 2. 选型从“能否命中”开始

| 需求 | 建议 | 判断依据 |
|---|---|---|
| 自有模块的埋点、耗时或故障注入 | 显式代理或编译期插桩 | 类型、线程和生命周期均可由业务代码控制 |
| 观察指定 `.so` 对 libc/NDK 函数的外部调用 | PLT/GOT Hook | 调用方有对应动态重定位项，且覆盖范围可限定 |
| 拦截函数内部调用、隐藏符号或 `dlsym` 后的直接调用 | Inline Hook | 调用不再经过待改写的导入槽 |
| 低频、短期、实验室级指令探针 | Trap Hook | 需要处理信号与调试器兼容问题 |
| ART、linker、debuggerd 私有函数 | 原则上不用于应用线上路径 | 私有符号、结构和调用约定没有兼容性承诺 |
| 分配器、线程同步等高频基础函数 | 优先 heapprofd、GWP-ASan、Perfetto 等平台工具 | 代理函数极易递归，故障影响整个进程 |

heapprofd 是采样式 Native 堆分析器，GWP-ASan 通过抽样和 guard page（不可访问的保护页）捕获部分堆越界或释放后使用，Perfetto 用于系统级跟踪。它们的覆盖范围不同，但都能减少直接改写分配器或同步原语的需求。

“PLT Hook 失败就换 Inline Hook”缺少必要的风险判断。选型前还要回答这些问题：

- 目标调用是否被 LTO（Link Time Optimization，链接时优化）、内联、隐藏可见性或直接绑定消掉了？
- 目标 ABI（Application Binary Interface，二进制接口）是否稳定？函数签名是否包含 C++ 隐式参数、可变参数或聚合返回？
- 安装 Hook 时，其他线程是否可能正在执行待覆盖的指令？
- 新装载和卸载的 ELF 如何加入或移出 Hook 集合？
- Hook 失败、重复安装、多个 SDK 同时 Hook、远程关闭时，状态是否可判定？
- 代理函数能否在递归、信号、低内存和进程退出阶段安全运行？

只要其中一项没有答案，就不应把 Hook 放入面向全部用户的路径。

## 3. Android 17 linker 的约束

### 3.1 立即绑定：装载时完成函数地址解析

linker 是 Android 的动态链接器，负责装载 ELF、查找符号并应用 relocation（重定位）。在 `android-17.0.0_r1` 的 `soinfo::prelink_image()` 中，`DT_JMPREL` 和 `DT_PLTRELSZ` 描述 PLT 重定位表及其大小；`DT_PLTGOT` 分支则注明 `RTLD_LAZY` 不受支持并直接跳过：

```cpp
case DT_JMPREL:
  plt_rela_ = reinterpret_cast<ElfW(Rela)*>(load_bias + d->d_un.d_ptr);
  break;
case DT_PLTRELSZ:
  plt_rela_count_ = d->d_un.d_val / sizeof(ElfW(Rela));
  break;
case DT_PLTGOT:
  // Ignored (because RTLD_LAZY is not supported).
  break;
```

随后 `link_image()` 调用 `relocate()`。`process_relocation_impl<RelocMode::General>()` 的 fast path（常见类型的快速处理分支）会把 `R_GENERIC_JUMP_SLOT` 的解析结果写入 GOT slot（GOT 槽位）：

```cpp
if (r_type == R_GENERIC_JUMP_SLOT) {
  const ElfW(Addr) result = sym_addr + get_addend_norel();
  *static_cast<ElfW(Addr)*>(rel_target) = result;
  return true;
}
```

主干调用关系可以概括为：`dlopen(name)` → `do_dlopen()` → 库查找与装载 → `soinfo::prelink_image()` → `soinfo::link_image()` → `relocate()` → `process_relocation_impl<General>()` 的 `R_GENERIC_JUMP_SLOT` 分支。中间的内部函数属于源码实现细节，不应成为应用兼容性假设。

这段流程带来三个结论：

1. 传入 `RTLD_LAZY` 不会启用桌面 Linux 常见的 lazy binding（首次调用时再解析地址）；Android 仍在装载期间完成相关重定位。
2. PLT/GOT Hook 修改 linker 已写好的重定位结果，不依赖 `DT_PLTGOT` 提供延迟解析入口。
3. 新装载的 ELF 有独立的重定位槽，必须另行扫描。已经完成解析的普通调用不会自行重新解析并覆盖 Hook。

IFUNC（indirect function，运行时选择实现的函数）需要单独说明。`dlsym()` 会返回解析后的符号地址；`R_GENERIC_IRELATIVE` 则是一类重定位，linker 会调用其 resolver 并把结果写入目标槽。两条路径都可能得到最终实现地址，但它们没有共用同一个 `R_GENERIC_IRELATIVE` 分支。校验旧值时，应比较最终实现地址，不能把 resolver 地址当作普通函数入口。

### 3.2 RELRO 限制写权限，同进程修改仍需显式处理

RELRO（Relocation Read-Only）让动态链接器在重定位完成后把指定内存段改为只读，降低 GOT 等控制数据被覆盖的风险。`soinfo::link_image()` 在 relocation 完成后调用 `protect_relro()`：

```cpp
bool soinfo::link_image(...) {
  ...
  if (this != solist_get_vdso() && !relocate(lookup_list)) return false;
  ...
  if (!is_linker() && !protect_relro()) return false;  // 关键：RELRO 写保护
  if (!protect_16kib_app_compat_code()) return false;
  ...
}
```

待修改的函数地址可能位于 `.got.plt`、`.data` 或 `.data.rel.ro`。是否落入 `PT_GNU_RELRO`、当前页有哪些权限，都要按目标 ELF 和运行时映射判断。

MTE（Memory Tagging Extension，内存标记扩展）globals 会给符合条件的全局对象使用地址标记。该支持在 Android 16 已存在，Android 17 延续了这套重定位语义。当 `should_tag_memtag_globals()` 返回 true 时，`R_AARCH64_RELATIVE` 会利用 relocation place（重定位目标位置的原始值）中的位生成带标记的结果：

```cpp
if (relocator.si->should_tag_memtag_globals()) {
  int64_t* place = static_cast<int64_t*>(rel_target);
  int64_t offset = *place;
  result = relocator.si->apply_memtag_if_mte_globals(result + offset) - offset;
}
```

这段代码只说明启用 MTE globals 的二进制会改变部分重定位的地址计算，不能推导出“每个 GOT 槽都带有 MTE 元数据”。Hook 仍要按具体 relocation type、当前槽值以及目标地址是否保留 tag 校验。

加载完成后，落入 RELRO 的槽位已经只读。普通应用中的 Hook 通常只能在 `dlopen()` 返回后看到新 ELF，此时需要确认页边界和原权限，再决定是否用 `mprotect()` 临时增加写权限。该调用可能因地址、长度、映射类型或进程安全策略而失败，失败应进入可观测的降级分支。

监听 `dlopen()` 只解决“何时重新扫描”的问题，不会获得 linker 内部从重定位结束到 `protect_relro()` 之前的公开插入点。依赖这个内部时机的方案必须 Hook linker 私有实现，版本风险会随之增加。

ByteHook 当前实现会记录 program header（程序头）推导出的原页权限，对不可写槽增加 `PROT_WRITE`，先回调原函数地址，再用原子写替换 GOT。源码中的权限恢复语句目前被注释，因此“写完是否恢复原权限”必须作为显式的框架策略记录，不能假定库会自动恢复。这也说明，可靠的 PLT/GOT Hook 包含 ELF 解析、权限处理、发布顺序和错误恢复，扫描 `/proc/self/maps` 后写一个指针远远不够。

### 3.3 `DT_TEXTREL` 与 Inline Hook 受不同机制约束

Android 17 linker 在 LP64（64 位进程）中遇到 `DT_TEXTREL` 或 `DF_TEXTREL` 时会报告错误并拒绝装载。`TEXTREL` 表示 ELF 需要在装载重定位阶段修改代码段；对应检查位于 `soinfo::prelink_image()`：

```cpp
case DT_TEXTREL:
#if defined(__LP64__)
  DL_ERR("\"%s\" has text relocations", get_realpath());
  return false;
#else
  has_text_relocations = true;
  break;
#endif
```

64 位 `.so` 一旦声明 `DT_TEXTREL`，`dlopen()` 就会失败。这项检查针对 ELF 自己声明的装载期代码重定位。

Inline Hook 发生在库装载完成后，由进程调用 `mprotect()` 并修改内存中的指令。`DT_TEXTREL` 的装载检查无法预测 Inline Hook 会成功还是失败，也不能为其安全性背书；两条路径需要分别评估。

### 3.4 私有库和 linker namespace

linker namespace（动态链接器命名空间）决定一组 ELF 可访问哪些库。从 Android 7.0 起，应用动态链接非 NDK 平台库受到限制；namespace 又进一步约束可见范围。内存中存在某个符号，只能证明该构建包含它，不能证明平台允许应用链接，也不能证明 ABI 稳定。

如果诊断方案必须依赖私有符号，至少要把设备 API、ABI、Build ID（二进制构建标识）、符号名和函数开头的指令摘要纳入允许列表。任何一项不匹配都应停用，不能用猜测的偏移继续执行。

### 3.5 16 KB page size

page size（页大小）是内核管理虚拟内存和设置页权限的最小粒度。Android 从 15 起已支持 16 KB 页设备，这项约束并非 Android 17 独有。arm64 指令仍固定为 4 字节，`B` 的编码范围也不随页大小变化；受影响的是 `mmap()`、`mprotect()`、trampoline 分配和页权限恢复：

- 用 `getpagesize()` 或 `sysconf(_SC_PAGESIZE)` 获取运行时页大小；
- 按运行时页大小向下、向上对齐保护区间；
- 处理“改写跨页”以及一页内存在其他函数的情况；
- 不把 `4096`、`PAGE_SIZE` 或 4 KB 掩码写死。

ShadowHook 和 ByteHook 当前源码都通过 `getpagesize()` 初始化页大小，并据此计算保护区间。自研实现可以使用 `getpagesize()` 或 `sysconf(_SC_PAGESIZE)`，但不能用编译期常量替代运行时结果。

## 4. PLT/GOT Hook：改写调用方的重定位结果

### 4.1 从 ELF 到目标槽

下面这条链路用来判断一个调用能否被 PLT/GOT Hook 命中。`PT_DYNAMIC` 是 ELF 的动态链接信息段；Android packed relocations 是 Android 用于压缩保存重定位表的格式。

```text
dl_iterate_phdr()
  -> 选中调用方 ELF
  -> PT_DYNAMIC
  -> DT_SYMTAB / DT_STRTAB
  -> DT_JMPREL、DT_REL[A] 或 Android packed relocations
  -> r_info 中的 symbol index + relocation type
  -> slot = load_bias + r_offset
  -> 校验旧值并写入 proxy 地址
```

判断时要同时锁定调用方 ELF 和 relocation type。以 arm64 为例，常见函数导入会涉及 `R_AARCH64_JUMP_SLOT`，部分函数地址引用还可能落在 `R_AARCH64_GLOB_DAT` 或 `R_AARCH64_ABS64`。同名字符串只提供候选符号，不能据此修改附近地址。

定位出的槽地址可写成：

```text
runtime_slot = load_bias + relocation.r_offset
```

load bias 是 ELF 虚拟地址映射到进程地址时使用的装载偏移。上面的公式只完成这一步换算。写入前仍需核对 relocation 对应的符号、当前槽值、目标映射和 ABI，避免把同名数据符号或已被其他框架改写的槽当作函数入口。

### 4.2 安装顺序

一个可审计的安装过程通常包含这些步骤：

1. 通过 `dl_iterate_phdr()` 枚举当前 ELF，在回调内复制后续需要的元数据，并按调用方路径或 Build ID 过滤。
2. 从 `PT_DYNAMIC` 解析动态符号表、字符串表和 relocation 表。
3. 同时校验符号名、relocation type、当前槽值和预期目标函数。
4. 读取槽所在映射的原权限，并按运行时页大小计算 `mprotect()` 区间。
5. 在发布 proxy 前保存原函数地址；多个 Hook 共存时，由统一调度入口维护调用链。
6. 用对齐的原子指针写更新槽，记录调用方、槽地址、旧值、新值和结果。
7. 明确决定是否恢复原权限；若保留写权限，记录原因、影响范围和框架版本。

orig 指代理函数继续调用的原目标地址。它必须先于新槽值发布；如果槽已替换，而 `orig` 对其他线程仍不可见，proxy 可能在这个窗口跳到空地址。发布顺序需要使用与并发模型匹配的原子操作和 memory order（内存序），不能只依赖普通 C 赋值。

### 4.3 覆盖盲区

下面这些调用不会因为修改某个 PLT/GOT 槽就自动被拦截：

- 同一 ELF 内部已解析为直接分支的调用；
- 编译器内联或 LTO 合并后的调用；
- hidden/protected visibility（隐藏或受保护的符号可见性）、`-Bsymbolic` 等导致的本地绑定；
- 通过 `dlsym()` 保存到其他变量后再发出的间接调用；
- 直接执行 `svc`（进入内核的 AArch64 异常指令）的系统调用封装；
- 在 Hook 安装后通过 `dlopen()` 加载的新调用方；
- 已卸载又复用同一地址区间的 ELF。

因此，“Hook 成功”只能说明某些 relocation slot 已改写，不能说明目标函数的所有调用都被覆盖。测试报告应同时给出命中调用方列表和明确的盲区。

### 4.4 动态装载和多框架共存

`dlopen()` 成功后，新 ELF 才会进入普通应用可枚举的模块集合。此时该 ELF 的 relocation 和构造函数已经执行完成；返回后再安装 Hook，只能覆盖后续调用，无法补采构造函数中的调用。若框架声称能在构造函数之前介入，应检查它是否依赖 linker 私有路径以及适配范围。

ByteHook 会在动态装载后刷新 ELF 管理器；ShadowHook 也能为尚未装载的目标保存 pending task（等待目标出现的安装任务）。无论采用哪种方式，都要把新装载、卸载和重复装载纳入生命周期测试。

不要在业务 proxy 里随意递归调用 `dlopen()`、`dlsym()` 或日志组件。它们可能再次经过被 Hook 的路径。常见处理方式包括：

- 线程局部重入标记；
- 不分配内存的最小记录器；
- 统一使用 proxy 调度入口，避免多个 SDK 互相覆盖槽；
- unhook 前确认槽仍指向本框架入口，发现第三方改写时拒绝盲目恢复。

## 5. Inline Hook：指令搬迁比跳转更难

### 5.1 基本过程

Inline Hook 会覆盖目标位置的一组指令，再把这些指令搬到 trampoline（保存原指令并跳回原函数的跳板代码）。搬迁后，所有依赖原 PC 的指令都要重新编码。AArch64 没有 Thumb 状态，但这并没有消除指令重写的风险。

| 维度 | ARM32 (AArch32/Thumb) | ARM64 (AArch64) |
|------|----------------------|------------------|
| 指令宽度与状态 | A32 指令为 4 字节；Thumb 同时存在 2 字节和 4 字节编码，还要保留执行状态 | 指令固定为 4 字节，没有 Thumb 状态切换 |
| PC-relative（相对当前指令地址） | `B/BL`、`ADR`、literal load 等；读取 PC 时还要区分 A32 与 Thumb 语义 | `B/BL`、`B.cond`、`CBZ/CBNZ`、`TBZ/TBNZ`、`ADR/ADRP`、literal load 等 |
| 返回地址 | 通常使用 LR（Link Register，链接寄存器）/R14，调用和状态切换规则取决于指令集状态 | X30 是 LR；PC 不能作为普通通用寄存器直接读取 |
| 远距离跳转 | 常用 veneer（中转跳转序列）处理范围和状态切换 | 直接 `B` 超出约 ±128 MiB 时，常用 `BR Xn` 的绝对跳转序列或近地址 branch island |

AArch64 Inline Hook 一般需要完成：

1. 选择函数入口或确定的指令地址。
2. 计算需要覆盖的完整指令数，并保存原字节。
3. 把被覆盖指令搬到 trampoline。
4. 重写所有受新 PC 影响的指令。
5. 在 trampoline 尾部跳回未覆盖的原函数。
6. 在原地址写入通往 proxy 或 branch island 的跳转。branch island 是分配在直接分支范围内的短中转代码。
7. 对生成和修改的代码区间执行 instruction-cache maintenance（指令缓存同步）。

其中步骤 4 的 PC-relative 重写难度最高。以 `ADRP` 指令为例：

```text
原始指令：   ADRP   X0, page_of(sym)        ; page 是 PC-relative
             ADD    X0, X0, #lo12_of(sym)
移到 trampoline 后：page_of(sym) 表达的是 "PC+page*4096"
                     PC 变了 → page_of(sym) 必须重算，
                     否则 X0 指向错误页（典型 4K 偏差，多线程场景下崩在不可预期位点）
```

示例中的“典型 4K 偏差”只用于展示错误现象；`ADRP` 按 4 KB 地址页计算，但搬迁错误造成的最终偏差取决于新旧 PC，不能固定按 4 KB 判断。

步骤 7 也不能省略。代码通过数据写入路径更新后，其他核心取指前必须看到新指令；在 Android NDK 代码中通常使用 `__builtin___clear_cache(begin, end)`。Android 17 的 bionic 只在 32 位 `__arm__` 下声明 `cacheflush()`，头文件也建议新代码使用跨架构的 builtin。

ShadowHook 的 arm64 重写器显式识别 `B`、`BL`、`B.cond`、`ADR`、`ADRP`、literal load、`CBZ/CBNZ`、`TBZ/TBNZ` 等类型。每类指令都有独立的长度计算和 rewrite 分支，因此“复制几条指令后跳回去”不足以构成可靠实现。

### 5.2 branch island 与并发改写

AArch64 的直接 `B` 使用 26 位有符号立即数并按 4 字节缩放，目标范围约为当前 PC 的前后 128 MiB。若能在范围内分配 branch island，原入口只需改写一条对齐的 4 字节指令；若无法分配，通常要写入多条指令组成的绝对跳转序列。

单条对齐的 32 位写入比多指令覆盖容易控制，但“数据写入不可撕裂”仍不等于“其他核心立即按新指令执行”。发布协议还要包含线程协调和指令缓存同步。多指令 patch 的窗口更大，其他核心可能取到新旧混合的指令序列；一次 `memcpy()` 无法提供所需的并发保证。

因此，在可证明安全的前提下，近地址 branch island 还能把原入口的发布动作缩小到一条指令；节省 trampoline 空间只是附带收益。

### 5.3 PAC、BTI 与 CFI

Android 17 的 arm64 代码可能同时使用几类控制流保护：

- **PAC（Pointer Authentication Code，指针认证码）**：函数序言或返回路径可能对 LR 签名、认证。搬迁序言时不能遗漏或重复这些指令，也不能改变它们依赖的栈状态。
- **BTI（Branch Target Identification，分支目标识别）**：bionic linker 会读取 GNU property（ELF 中声明处理器特性的 note）；当 ELF 声明兼容且硬件支持时，为可执行段加入 `PROT_BTI`。若 proxy 或 trampoline 所在映射受 BTI 保护，通过间接 `BR/BLR` 到达的入口必须有匹配的 landing pad（允许间接分支落入的入口指令）。
- **CFI（Control-Flow Integrity，控制流完整性）**：函数指针等间接调用到达签名不兼容的代理地址时，可能触发类型检查并终止进程。Hook 私有 CFI helper 以绕过检查，又会新增一组没有兼容性承诺的依赖。

Hook 框架需要把这些能力纳入测试组合，CPU 架构只能作为第一层筛选。至少要覆盖启用 `-mbranch-protection`、LTO/CFI、不同链接可见性和不同系统库 Build ID 的产物。

### 5.4 代码页权限

Inline Hook 需要修改可执行映射。当前 ShadowHook 源码会把目标区间 `mprotect()` 为 `PROT_READ | PROT_WRITE | PROT_EXEC`，写入后调用 `__builtin___clear_cache()`。这条运行时 patch 路径独立于 linker 的 `DT_TEXTREL` 检查。W+X 表示同一页同时可写、可执行，这段权限窗口本身就增加了攻击面。

工程上应缩短可写可执行窗口、限制可修改目标、记录权限变更失败，并在框架设计允许时恢复最小权限。不能用关闭 SELinux、修改系统属性或依赖 root 作为普通应用方案。

## 6. Trap Hook：框架必须维护完整的信号语义

arm64 软件断点通常用 `BRK` 指令触发 `SIGTRAP`。信号可能来自软件断点、硬件断点、调试器或其他组件，处理函数至少要完成：

- 只消费 `si_code` 符合预期、且指令地址命中自有断点表的事件；
- 从 `ucontext_t` 读取并按 ABI 修改寄存器与 PC；
- 保证处理路径满足 async-signal-safe（异步信号安全）约束，即只调用 POSIX 明确允许在信号处理函数中使用的操作；
- 处理嵌套信号、线程退出、unhook 和断点表并发；
- 对非本框架事件调用前序 handler 或恢复默认处置；
- 与 ptrace 调试器、采样器、崩溃 SDK 和 native bridge（让一种 ABI 的 Native 代码运行在另一种架构环境中的转换层）一起测试。

Android 17 的 debuggerd 在 `debuggerd_init()` 中为 `SIGTRAP` 等致命信号注册处理函数，并设置 `SA_SIGINFO | SA_ONSTACK | SA_RESTART | SA_EXPOSE_TAGBITS`：

```cpp
struct sigaction action = {.sa_sigaction = debuggerd_signal_handler,
                           .sa_flags = SA_RESTART | SA_SIGINFO};
sigfillset(&action.sa_mask);
action.sa_flags |= SA_ONSTACK;          // alt-stack 应对栈溢出
action.sa_flags |= SA_EXPOSE_TAGBITS;   // 请求内核把 fault addr 的 tag bit 暴露给 user
debuggerd_register_handlers(&action);
```

`SA_EXPOSE_TAGBITS` 请求内核在 `siginfo_t.si_addr` 中保留受支持架构的 address tag bits（地址高位标记），用于分析 MTE 等故障。Android 16 的同一路径已经设置该 flag，因此这里的代码只能证明 Android 17 继续使用它。

`debuggerd_signal_handler()` 处理 `SIGTRAP`、`SIGSEGV`、`SIGBUS`、`SIGFPE`、`SIGILL`、`SIGABRT` 等信号。致命路径会暂时允许 `crash_dump` 使用 `ptrace` 读取进程，通过 `clone()` 建立共享地址空间的 pseudothread（专用于分派崩溃转储的轻量线程），再由 `crash_dump` 暂停线程并生成 tombstone（Native 崩溃转储）。可恢复 GWP-ASan 或 permissive MTE（记录 MTE 故障后允许继续执行的宽松模式）等特定路径可能在记录后返回；其他致命路径会重新发送信号。

应用消费自有 `SIGTRAP` 时不一定生成 tombstone，结果取决于当前 signal chain（信号处理函数调用顺序）、`si_code`、调试器状态以及事件是否继续传给 debuggerd。在 ART 进程中，sigchain（ART 的信号串接库）还可能把平台 special handler（优先运行的特殊处理函数）和用户 handler 组合起来。Hook 不能假设一次 `sigaction()` 调用就获得了 `SIGTRAP` 的独占控制权。

这条链路说明了两个边界：

1. Trap Hook 不能调用 debuggerd 私有 handler 来协助恢复；debuggerd 的接口目标是生成崩溃转储。
2. 自定义 handler 只能消费能够证明属于本框架的事件。硬件断点、调试器事件和其他组件的断点必须继续按原语义处理。

对于高频函数，逐次进入信号处理路径的成本和兼容风险通常不可接受。Trap 更适合短期诊断或低频探针，不适合作为通用线上拦截器。

## 7. 代理函数的 ABI 和重入约束

代理函数必须与被替换目标使用完全兼容的调用约定。参数个数只是其中一项，还要核对：

- 整数、浮点和向量参数分别使用哪些寄存器；
- 大结构体返回是否通过隐藏的结果指针；
- C++ 成员函数的 `this`、name mangling（符号名编码）和异常边界；
- 可变参数、栈对齐和保留寄存器；
- PAC/BTI/CFI 编译选项；
- `errno`（线程局部错误码）是否属于接口语义。

下面的骨架只说明重入保护与保存 `errno` 的基本顺序，不能直接作为完整 Hook 使用：

```cpp
using ReadFn = ssize_t (*)(int, void*, size_t);

static ReadFn g_orig_read = nullptr;
static thread_local bool g_inside_read = false;

ssize_t proxy_read(int fd, void* buffer, size_t count) {
  if (g_inside_read) {
    return g_orig_read(fd, buffer, count);
  }

  g_inside_read = true;
  ssize_t bytes_read = g_orig_read(fd, buffer, count);
  int call_errno = errno;
  record_without_allocation(fd, count, bytes_read, call_errno);
  g_inside_read = false;
  errno = call_errno;
  return bytes_read;
}
```

这个示例仍省略了 cancellation point（线程可响应 pthread cancellation 的位置）、异常退出、信号重入和多线程同时初始化的竞态。`thread_local` 标记只能约束当前线程的常规递归，无法让记录函数自动满足异步信号安全。生产代码还要使用 RAII（让对象析构时自动执行清理）或等价的 scope guard（退出当前作用域时自动清理），保证每条返回路径都清理线程局部状态，并确认代理声明与目标导出声明逐项一致。

## 8. 生命周期设计

### 8.1 状态机

每个 Hook 至少应有以下状态：

```text
DECLARED -> RESOLVING -> INSTALLING -> ACTIVE
                         |             |
                         v             v
                       FAILED       DISABLING -> DISABLED
```

状态机的用途是让重复初始化、动态装载、并发关闭和失败重试有明确结果。`ACTIVE` 必须意味着目标集合、原地址和 proxy 都已发布；`FAILED` 需要保留错误阶段与证据，不能只记录一个布尔值。

### 8.2 优先逻辑停用，谨慎物理卸载

恢复 GOT 指针不等于旧 proxy 已无人执行，恢复函数入口也不等于 trampoline 可以立刻释放。线程可能仍在 proxy、原函数 trampoline 或被覆盖区间内。

风险较低的关闭方式是保留稳定入口，只用原子开关让 proxy 直接调用原函数。若必须物理 unhook，需要有活动调用计数、grace period（等待旧调用退出的宽限期）或暂停线程的协议，并确认目标 ELF 尚未卸载、槽或指令仍属于本框架。

### 8.3 记录可复现证据

安装记录至少包括：

- Android API 与 ABI；
- 目标 ELF 路径、Build ID、load bias；
- 符号名、相对偏移、原地址和 proxy 地址；
- relocation type 或被覆盖的原指令；
- 页大小、原权限、改写结果；
- 框架版本、配置版本和错误码；
- 是否存在其他 Hook，以及发现时的槽值或指令摘要。

崩溃发生后，这些信息应随稳定性事件上传。否则很难判断崩溃位于业务代码、proxy、trampoline、指令搬迁还是多框架冲突。

## 9. 典型场景

### 9.1 文件描述符监控

观察自有或指定第三方 ELF 的 `openat`、`close`、`dup`、`socket` 等导入调用时，PLT/GOT Hook 通常比进程级 Inline Hook 更容易限定影响面。代理函数应保存 `errno`，使用无分配记录路径，并把“未经过导入槽的直接 syscall（系统调用）”写入覆盖盲区。

FD 是 file descriptor（文件描述符）。这类方案适合辅助定位 FD 泄漏，仍需结合 `/proc/self/fd` 快照、资源所有权和调用栈采样。参见 20.7《FD 耗尽监控与故障排查》。

### 9.2 分配器监控

直接 Hook `malloc/free` 会让日志、符号化、容器扩容乃至 Hook 框架自身再次进入分配器。定位堆问题时，可先评估 heapprofd、GWP-ASan、Scudo 强化分配器提供的错误诊断以及 MTE。只有这些工具无法覆盖，并且已有无分配采集器时，才考虑限定调用方的 PLT/GOT Hook。

### 9.3 私有运行时函数

对 `libart.so` 私有函数做 Inline Hook，即使在某台 Android 17 设备上成功，也不能推导出相同 API level 的其他设备可复用。ART 等 Mainline 模块可以通过系统组件更新机制独立升级，厂商构建选项也会改变符号、函数序言、CFI 和调用时机。

这类 Hook 应按具体 Build ID 管理，并保留“一律不安装”的默认分支。用于研究的偏移和线上允许列表也应分开维护。

### 9.4 新 ELF 装载

若采集目标包含插件、动态特性或运行时 `dlopen()` 的 SDK，只扫描一次进程模块必然漏报。应订阅框架提供的装载回调或在安全时点刷新模块，并对同一路径、Build ID 和 load bias 做幂等处理；幂等表示同一对象被重复通知时不会重复安装。

自行 Hook linker 私有 `soinfo` 字段会把回调机制绑定到内部结构。ShadowHook 手册也说明，相关偏移需要按 Android 版本扫描和适配；采用这条路径时，适配表、失败停用和回滚策略都要随框架发布。

### 9.5 API level 不能替代二进制身份

对照 `android-16.0.0_r1` 与 `android-17.0.0_r1` 可以确认，两者都不支持 `RTLD_LAZY` 的延迟解析，debuggerd 都会设置 `SA_EXPOSE_TAGBITS`，也都包含 permissive MTE 和 MTE globals 相关路径。这些机制不能用来区分 Android 16 与 17，更不能作为某个 Hook 可安装的充分条件。

API level 只适合作为第一层筛选。安装前还要检查：

| 检查项 | 用途 |
|---|---|
| ABI 与运行时页大小 | 选择对应指令重写器，并正确计算 `mprotect()` 区间 |
| 目标 ELF 路径与 Build ID | 区分 Mainline、系统和厂商的不同二进制构建 |
| 符号版本、relocation type 与当前槽值 | 确认 PLT/GOT Hook 修改的是预期调用 |
| 函数入口指令摘要 | 确认 Inline Hook 的已验证序言仍然匹配 |
| GNU property 与编译选项 | 判断 BTI、PAC、CFI、LTO 等控制流条件 |
| Hook 框架版本与已安装项 | 识别版本能力和多框架覆盖冲突 |

## 10. 常见故障定位

| 现象 | 优先检查 | 常见原因 |
|---|---|---|
| 安装成功但没有回调 | 调用方 relocation、反汇编、命中模块列表 | 内联、直接调用、`dlsym` 函数指针、直接 syscall |
| `mprotect` 失败 | 地址、长度、运行时页大小、原映射 | 4 KB 写死、跨页计算错误、映射或策略不允许 |
| proxy 一进入就崩溃 | 完整函数签名、CFI、BTI、原函数发布顺序 | ABI 不匹配、非法间接目标、`orig` 尚未可见 |
| trampoline 附近 `SIGILL/SIGSEGV` | 原指令、重写结果、PC-relative 目标 | ADR/ADRP、literal load、条件分支搬迁错误 |
| 低概率随机崩溃 | patch 长度、安装时并发、I-cache | 多指令非原子改写、线程正在执行目标入口 |
| 动态加载模块漏采 | `dlopen` 事件和 ELF 刷新记录 | 只在启动时扫描一次 |
| 卸载后跳到野地址 | ELF 生命周期、活动 proxy、trampoline 所有权 | `dlclose` 后仍保留槽或目标地址 |
| 与崩溃 SDK 冲突 | `sigaction` 注册顺序和 handler 串接 | 吞信号、错误恢复默认 handler、信号内使用非安全 API |
| Android 17 某些设备才失败 | Build ID、BTI/CFI、16 KB、厂商 ABI | 用 API level 代替了二进制身份校验 |

## 11. Android 17 上线检查表

- [ ] 只使用公开 NDK API 作为业务依赖，私有符号 Hook 有 Build ID 允许列表
- [ ] 明确记录 Hook 的调用方、被调用方和覆盖盲区
- [ ] arm64 之外的 ABI 有独立实现或明确禁用
- [ ] 使用运行时页大小，没有 4 KB 假设
- [ ] 验证 RELRO 页权限处理与失败分支
- [ ] 验证新 ELF 装载、卸载和重复安装
- [ ] 验证 PAC、BTI、CFI、LTO 与不同可见性组合
- [ ] 代理函数签名完整，保存 `errno`，具备重入保护
- [ ] Inline patch 有并发发布和 I-cache 维护证据
- [ ] Trap handler 只消费自有断点，并正确串接其他信号处理者
- [ ] 关闭功能不立即释放仍可能执行的 proxy 或 trampoline
- [ ] 崩溃事件可还原目标 Build ID、偏移、原指令或 relocation

## 小结

Native Hook 的选型应从“需要命中哪条调用路径”开始：PLT/GOT 修改特定调用方的导入槽，Inline 改写目标指令，Trap 则依赖完整信号语义。上线前必须把 ABI、Build ID、页大小、RELRO、PAC/BTI/CFI、动态装载、并发发布和多框架共存写成可验证的安装条件；任何条件不匹配时默认停用，不用猜测偏移继续执行。

## 12. 源码锚点与参考资料

正文的平台实现以 `android-17.0.0_r1` 为准：

- [bionic linker.cpp](https://android.googlesource.com/platform/bionic/+/refs/tags/android-17.0.0_r1/linker/linker.cpp)：`DT_JMPREL`、`DT_PLTGOT`、`DT_TEXTREL`、`protect_relro()`。
- [bionic linker_relocate.cpp](https://android.googlesource.com/platform/bionic/+/refs/tags/android-17.0.0_r1/linker/linker_relocate.cpp)：`R_GENERIC_JUMP_SLOT`、`GLOB_DAT`、IRELATIVE 等重定位处理。
- [bionic linker_phdr.cpp](https://android.googlesource.com/platform/bionic/+/refs/tags/android-17.0.0_r1/linker/linker_phdr.cpp)：GNU property 与 arm64 `PROT_BTI`。
- [bionic unistd.h](https://android.googlesource.com/platform/bionic/+/refs/tags/android-17.0.0_r1/libc/include/unistd.h)：`cacheflush()` 的架构条件与 builtin 建议。
- [debuggerd handler.h](https://android.googlesource.com/platform/system/core/+/refs/tags/android-17.0.0_r1/debuggerd/include/debuggerd/handler.h)：致命信号集合与 `SIGTRAP` 注册。
- [debuggerd_handler.cpp](https://android.googlesource.com/platform/system/core/+/refs/tags/android-17.0.0_r1/debuggerd/handler/debuggerd_handler.cpp)：pseudothread、`crash_dump` 和 `ptrace` 配合链路。
- [ART sigchain.cc](https://android.googlesource.com/platform/art/+/android-17.0.0_r1/sigchainlib/sigchain.cc)：special handler、debuggerd recovery hook 与用户 handler 的转发次序。

版本对照使用以下 `android-16.0.0_r1` 源码：

- [Android 16 linker.cpp](https://android.googlesource.com/platform/bionic/+/refs/tags/android-16.0.0_r1/linker/linker.cpp)：`RTLD_LAZY`、MTE globals 和 RELRO 路径。
- [Android 16 linker_relocate.cpp](https://android.googlesource.com/platform/bionic/+/refs/tags/android-16.0.0_r1/linker/linker_relocate.cpp)：MTE globals relocation 处理。
- [Android 16 debuggerd_handler.cpp](https://android.googlesource.com/platform/system/core/+/refs/tags/android-16.0.0_r1/debuggerd/handler/debuggerd_handler.cpp)：`SA_EXPOSE_TAGBITS` 与 permissive MTE 路径。

工程实现与平台规则：

- [ShadowHook manual](https://github.com/bytedance/android-inline-hook/blob/main/doc/manual.md) 与 [arm64 指令重写源码](https://github.com/bytedance/android-inline-hook/blob/main/shadowhook/src/main/cpp/arch/arm64/sh_a64.c)：指令重写、动态装载任务和当前实现行为。
- [ByteHook 原理说明](https://github.com/bytedance/bhook/blob/main/doc/overview.zh-CN.md) 与 [GOT 重定位写入源码](https://github.com/bytedance/bhook/blob/main/bytehook/src/main/cpp/bh_elf_relocator.c)：原函数发布、页权限调整与 GOT 原子写。
- [Android 16 KB page size 指南](https://developer.android.com/guide/practices/page-sizes)。
- [Android 7.0 非公开 Native 库限制](https://developer.android.com/about/versions/nougat/android-7.0-changes)。
- [Android linker namespace](https://source.android.com/docs/core/permissions/namespaces_libraries)。
- [Arm PAC、BTI 与 MTE 指南](https://developer.arm.com/-/media/Arm%20Developer%20Community/PDF/Learn%20the%20Architecture/Providing%20protection%20for%20complex%20software.pdf)。

关联阅读：

- 14.7《三方性能库、Hook 与可观测性基础设施》
- 20.7《FD 与资源耗尽监控》
- 20.3《Native Crash、堆栈回溯与符号化》
