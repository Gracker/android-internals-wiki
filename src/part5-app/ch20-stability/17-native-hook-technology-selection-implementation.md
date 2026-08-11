---
title: "Native Hook 技术选型与实现"
chapter: "20.17"
status: finalized
applicable_versions: "Android 17 (API 37) - Android 17 (API 37)"
tags: ['Native Hook', 'Inline Hook', 'GOT/PLT', 'ARM64', 'bionic linker', 'debuggerd']
related_chapters: ['20.12', '20.3', '14.26']
created_by: "task2a-knowledge-gap"
created_date: "2026-07-14"
gap_source: "章节深挖"
confidence: medium-high
last_verified: "2026-07-28"
sources:
  - type: deepresearch
    path: "DeepResearch/2026-07-14-android17-native-hook-three-schools-inlinhook-arm64.md"
  - type: aosp
    path: "bionic/linker/linker.cpp android-17.0.0_r1"
  - type: aosp
    path: "bionic/linker/linker_relocate.cpp android-17.0.0_r1"
  - type: aosp
    path: "system/core/debuggerd/handler/debuggerd_handler.cpp android-17.0.0_r1"
last_body_apply_at: "2026-07-28T07:15:05+08:00"
last_body_apply_run_id: "20260728-071505-5c898420"
last_body_apply_source: "source-index:18:DeepResearch/2026-07-14-android17-native-hook-three-schools-inlinhook-arm64.md"
task2b_state: fixed
task6_state: reviewed
task9_state: reviewed
pipeline_stage: finalized
reviewed_date: "2026-07-28"
reviewed_by: "hermes-aiw-review-finalize-apply"
last_review_finalize_at: "2026-07-28T08:18:33+08:00"
last_review_finalize_run_id: "20260728-081833-99d1a2d7"
---

# Native Hook 技术选型与实现

Native Hook 的风险不在“把地址换掉”这一行代码，而在命中范围、并发改写、ABI 一致性、动态装载和平台防护。只按 GOT、Trap、Inline 三个名词选型，很容易把不同层次的机制混在一起。

平台锚点为 `android-17.0.0_r1`，重点分析普通应用进程内的 arm64 Native Hook。Android 17 没有提供公开的 Hook API，也没有让 Hook 框架获得额外权限。应用仍应优先使用公开 NDK API、编译期插桩、显式代理或系统诊断工具；只有无法改造调用方、且收益足以覆盖稳定性成本时，才考虑运行时 Hook。

## 1. 先确定要改写哪一层

Native Hook 常见方案处理的是三个不同对象：

| 方案 | 改写对象 | 能观察到什么 | 主要盲区 |
|---|---|---|---|
| PLT/GOT Hook | 某个 ELF 调用方的导入重定位槽 | 该调用方经动态链接发出的外部函数调用 | 内部直接调用、内联、直接系统调用、已保存的函数指针 |
| Inline Hook | 目标函数入口或函数内指令 | 所有经过该指令地址的执行流 | 无法安全搬迁的指令、已经内联的调用、未命中的其他实现 |
| Trap/Breakpoint Hook | 指令替换为断点，借 `SIGTRAP` 改写上下文 | 命中断点的执行流和寄存器现场 | 信号冲突、调试器抢占、频繁信号带来的高成本 |

PLT/GOT Hook 是“按调用方改写”，Inline Hook 是“按被调用方改写”。两者即使都针对 `malloc`，覆盖面也不同：修改 `libfoo.so` 中 `malloc` 的导入槽，只影响 `libfoo.so` 发出的相应调用；修改 `libc.so` 中 `malloc` 的入口，则可能影响进程内更多调用者，也会显著放大递归和并发风险。

Trap Hook 更接近用户态软件断点。它不是 debuggerd 的扩展接口，也不应和 `ptrace` 调试混为一谈。Hook 框架需要自己拥有或正确串接 `SIGTRAP` disposition，并在信号处理函数中识别断点、修正 `ucontext_t`、决定是否恢复执行。

## 2. 选型从“能否命中”开始

| 需求 | 建议 | 判断依据 |
|---|---|---|
| 自有模块的埋点、耗时或故障注入 | 显式代理或编译期插桩 | 类型、线程和生命周期均可由业务代码控制 |
| 观察指定 `.so` 对 libc/NDK 函数的外部调用 | PLT/GOT Hook | 调用方有对应动态重定位项，且覆盖范围可限定 |
| 拦截函数内部调用、隐藏符号或 `dlsym` 后的直接调用 | Inline Hook | 调用不再经过待改写的导入槽 |
| 低频、短期、实验室级指令探针 | Trap Hook | 需要处理信号与调试器兼容问题 |
| ART、linker、debuggerd 私有函数 | 原则上不用于应用线上路径 | 私有符号、结构和调用约定没有兼容性承诺 |
| 分配器、线程同步等高频基础函数 | 优先 heapprofd、GWP-ASan、Perfetto 等平台工具 | 代理函数极易递归，故障影响整个进程 |

“PLT Hook 失败就换 Inline Hook”不是充分的决策过程。还要回答下面几个问题：

- 目标调用是否被 LTO、内联、隐藏可见性或直接绑定消掉了？
- 目标 ABI 是否稳定，函数签名是否包含 C++ 隐式参数、可变参数或聚合返回？
- 安装 Hook 时，其他线程是否可能正在执行待覆盖的指令？
- 新装载和卸载的 ELF 如何加入或移出 Hook 集合？
- Hook 失败、重复安装、多个 SDK 同时 Hook、远程关闭时，状态是否可判定？
- 代理函数能否在递归、信号、低内存和进程退出阶段安全运行？

只要其中一项没有答案，就不应把 Hook 放入面向全部用户的路径。

## 3. Android 17 动态链接器给出的边界

### 3.1 Android 使用立即绑定

在 `android-17.0.0_r1` 的 `soinfo::prelink_image()` 中（`bionic/linker/linker.cpp` line 2987-3018），linker 解析 `DT_JMPREL` 和 `DT_PLTRELSZ`，但 `DT_PLTGOT` 分支只有注释 `Ignored (because RTLD_LAZY is not supported)` 并直接 break：

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

随后 `link_image()` 调用 `relocate()`，`process_relocation_impl<RelocMode::General>()`（`linker_relocate.cpp` line 165+）的 fast path 直接把解析结果写入 GOT slot：

```cpp
if (r_type == R_GENERIC_JUMP_SLOT) {
  const ElfW(Addr) result = sym_addr + get_addend_norel();
  *static_cast<ElfW(Addr)*>(rel_target) = result;
  return true;
}
```

完整调用链为：`dlopen(name)` → `do_dlopen()` → `find_library()` → `soinfo::prelink_image()` → `soinfo::link_image()` → `relocate()` → `process_relocation()` → `process_relocation_impl<General>()` 的 `R_GENERIC_JUMP_SLOT` 分支。

这段流程带来三个结论：

1. Android 上不能套用桌面 Linux 的“第一次调用时由 lazy resolver 回填 GOT”模型。
2. PLT Hook 改写的是 linker 已完成的重定位结果，并不依赖 `DT_PLTGOT`。
3. IFUNC/IRELATIVE resolver 也是装载期重定位的一部分。解析完成后，普通调用不会自动再次解析并覆盖 Hook；新装载的 ELF 拥有自己的重定位槽，需要单独处理。具体而言，通过 `dlsym()` 取得的是绝对地址；若目标函数是 IFUNC（`STT_GNU_IFUNC`），linker 在 `R_GENERIC_IRELATIVE` 分支中会先调用 `call_ifunc_resolver()` 求出最终实现地址再写入 GOT slot。

### 3.2 RELRO 是权限边界，不是“无法 Hook”

`soinfo::link_image()`（`bionic/linker/linker.cpp` line 3386+）在 relocation 完成后调用 `protect_relro()`，把 GNU RELRO 段设为只读：

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

待修改的函数地址可能位于 `.got.plt`、`.data` 或 `.data.rel.ro`，不能假定所有槽都处于同一种保护状态。

Android 17 还引入了 MTE globals tagging：当 `should_tag_memtag_globals()` 返回 true 时，`linker_relocate.cpp`（line 343+）在 `R_AARCH64_RELATIVE` 重定位阶段对写入地址额外应用 MTE tag：

```cpp
if (relocator.si->should_tag_memtag_globals()) {
  int64_t* place = static_cast<int64_t*>(rel_target);
  int64_t offset = *place;
  result = relocator.si->apply_memtag_if_mte_globals(result + offset) - offset;
}
```

加载完成后，RELRO 内的 GOT 段即为只读，且可能携带 MTE tag metadata。框架不能直接写入受保护的槽，需要先确认所在映射的权限和页范围，再进行受控的 `mprotect()` 与指针更新。RELRO 不是密码学保护，也不会让同进程代码永远无法修改该页。修改是否成功还受映射方式、SELinux 策略和进程策略影响，失败必须被当作正常结果处理。

GOT Hook 框架可以在 `dlopen()` 内安装 Hook，但时机必须晚于 JUMP_SLOT 解析、早于 `protect_relro()`，可用窗口很短。

ByteHook 的实现会根据 ELF program header 记录原页权限，对非可写槽增加 `PROT_WRITE`，再以原子指针写替换地址。这个实现也说明，可靠的 PLT Hook 远不止扫描 `/proc/self/maps` 后写一个指针。

### 3.3 `DT_TEXTREL` 与运行时 Inline Hook 是两件事

Android 17 linker 在 LP64（64 位进程）中遇到 `DT_TEXTREL` 或 `DF_TEXTREL` 时会直接 `DL_ERR` 拒绝装载。源码位置在 `soinfo::prelink_image()`（`linker.cpp` line 3183+）：

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

64 位 `.so` 一旦声明 `DT_TEXTREL`，整个 `dlopen` 会直接失败。这里约束的是 ELF 在装载重定位阶段修改不可写代码段的声明。

Inline Hook 则是库装载完成后，进程主动调用 `mprotect()` 并改写内存中的指令。前者被拒绝不能推出后者必然失败，也不能证明后者安全。两条路径要分别评估。

### 3.4 私有库和 linker namespace

应用不能把“内存里能看到一个符号”理解为“平台承诺它可用”。从 Android 7.0 起，应用动态链接非 NDK 平台库受到限制；linker namespace 进一步限制库的可见范围。绕过 namespace 查找 `libart.so`、linker 内部符号，只解决了地址发现问题，没有获得 ABI 兼容承诺。

Android 17 上如果必须依赖私有符号，至少要把设备 API、ABI、Build ID、符号名、函数开头指令摘要纳入允许列表。任何一项不匹配都应停用，而不是猜测一个偏移继续执行。

### 3.5 16 KB page size

arm64 指令仍是固定 4 字节，`B` 的编码范围也不因页大小改变。受影响的是 `mmap()`、`mprotect()`、trampoline 分配和页权限恢复：

- 用 `getpagesize()` 或 `sysconf(_SC_PAGESIZE)` 获取运行时页大小；
- 按运行时页大小向下、向上对齐保护区间；
- 处理“改写跨页”以及一页内存在其他函数的情况；
- 不把 `4096`、`PAGE_SIZE` 或 4 KB 掩码写死。

ShadowHook 和 ByteHook 当前源码都通过 `getpagesize()` 初始化页大小，并据此计算保护区间。这是 Android 17 兼容 16 KB 设备时必须保留的行为。

## 4. PLT/GOT Hook：改写调用方的重定位结果

### 4.1 从 ELF 到目标槽

下面这条链路用来判断一个调用是否能被 PLT/GOT Hook 命中：

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

这段流程的关键点是“调用方 ELF”和“relocation type”。以 arm64 为例，常见函数导入会涉及 `R_AARCH64_JUMP_SLOT`，部分函数地址引用还可能落在 `R_AARCH64_GLOB_DAT` 或 `R_AARCH64_ABS64`。框架不能见到同名字符串就修改附近地址。

定位出的槽地址可写成：

```text
runtime_slot = load_bias + relocation.r_offset
```

这个公式只负责把 ELF 虚拟地址换成进程地址。写入前仍需核对 relocation 对应的符号、当前槽值、目标映射和 ABI，避免把同名数据符号或已被其他框架改写的槽当作函数入口。

### 4.2 安装顺序

一个可审计的安装过程通常包含这些步骤：

1. 通过 `dl_iterate_phdr()` 获取稳定的 ELF 快照，并按调用方路径或 Build ID 过滤。
2. 从 `PT_DYNAMIC` 解析动态符号表、字符串表和 relocation 表。
3. 同时校验符号名、relocation type、当前槽值和预期 callee。
4. 读取槽所在映射的原权限，并按运行时页大小计算 `mprotect()` 区间。
5. 在发布 proxy 前保存原函数地址；多个 Hook 共存时，由统一调度入口维护调用链。
6. 用对齐的原子指针写更新槽，记录调用方、槽地址、旧值、新值和结果。
7. 按设计恢复最小权限，或明确记录框架为何需要保留写权限。

“先保存原函数”是硬约束。如果槽已被替换而 `orig` 尚未对其他线程可见，proxy 可能在这个窗口进入并跳到空地址。发布顺序需要使用与并发模型匹配的原子和内存序，不能只依赖普通 C 赋值。

### 4.3 覆盖盲区

下面这些调用不会因为修改某个 PLT/GOT 槽就自动被拦截：

- 同一 ELF 内部已解析为直接分支的调用；
- 编译器内联或 LTO 合并后的调用；
- hidden/protected visibility、`-Bsymbolic` 等导致的本地绑定；
- 通过 `dlsym()` 保存到其他变量后再发出的间接调用；
- 直接执行 `svc` 的系统调用封装；
- 在 Hook 安装后通过 `dlopen()` 加载的新调用方；
- 已卸载又复用同一地址区间的 ELF。

因此，“Hook 成功”只能说明某些 relocation slot 已改写，不能说明目标函数的所有调用都被覆盖。测试报告应同时给出命中调用方列表和明确的盲区。

### 4.4 动态装载和多框架共存

`dlopen()` 成功后，新 ELF 才会出现可修改的 relocation。成熟框架会监听装载事件、刷新 ELF 集合，并在构造函数运行前后选择一致的安装时点。ByteHook 会在动态装载后刷新 ELF 管理器；ShadowHook 也为尚未装载的目标保存 pending task。

不要在业务 proxy 里随意递归调用 `dlopen()`、`dlsym()` 或日志组件。它们可能再次经过被 Hook 的路径。常见处理方式包括：

- 线程局部重入标记；
- 不分配内存的最小记录器；
- 统一的 proxy 调度入口，而不是多个 SDK 互相覆盖槽；
- unhook 前确认槽仍指向本框架入口，发现第三方改写时拒绝盲目恢复。

## 5. Inline Hook：指令搬迁比跳转更难

### 5.1 基本过程

ARM64 Inline Hook 在指令修复上比 ARM32 简化（无 Thumb 模式切换），但 `ADRP/ADR/LDR` 字面加载指令的 PC-relative 修复仍是工程难点。两种架构的主要差异如下：

| 维度 | ARM32 (AArch32/Thumb) | ARM64 (AArch64) |
|------|----------------------|------------------|
| Thumb | 支持，需切换 IT/T16/T32 | 不支持，指令固定 32-bit |
| PC 可见性 | ARM 模式下 R15 即 PC；三级流水线导致 PC+8 | X30 (LR) 是返回地址，没有"PC 读寄存器"概念；PC-relative 通过 ADRP/ADR 指令字面计算 |
| 需要修复的指令 | LDR PC, [PC, #offset] / B / BL (PC ±32MB) / ADR / ADD Rd, PC, #N | B/BL (±128MB) / B.cond / CBZ/CBNZ/TBZ/TBNZ / ADR/ADRP/LDR (literal) |
| 长度变化 | Thumb/ARM 切换需要"veneer + 状态切换"序列 | 指令固定 32-bit，长度对齐容易；但单条指令可能涉及多 register |
| Veneer 中转 | 需要 LDR PC, [PC, #offset] trampoline | B ±128MB 外的目标 → 用 `BR Xn`（绝对 64 位寄存器跳转）+ trampoline 区域 |

arm64 Inline Hook 一般需要完成：

1. 选择函数入口或确定的指令地址。
2. 计算需要覆盖的完整指令数，并保存原字节。
3. 把被覆盖指令搬到 trampoline。
4. 重写所有受新 PC 影响的指令。
5. 在 trampoline 尾部跳回未覆盖的原函数。
6. 在原地址写入通往 proxy 或 branch island 的跳转。
7. 对生成和修改的代码区间执行 instruction-cache maintenance。

其中步骤 4 的 PC-relative 重写难度最高。以 `ADRP` 指令为例：

```text
原始指令：   ADRP   X0, page_of(sym)        ; page 是 PC-relative
             ADD    X0, X0, #lo12_of(sym)
移到 trampoline 后：page_of(sym) 表达的是 "PC+page*4096"
                     PC 变了 → page_of(sym) 必须重算，
                     否则 X0 指向错误页（典型 4K 偏差，多线程场景下崩在不可预期位点）
```

步骤 7 的 icache 同步不可省略：ARM64 采用 Harvard 架构变体，D-cache 写入不自动进 I-cache，必须调用 `__builtin___clear_cache()` 或 `cacheflush()` syscall。

ShadowHook 的 arm64 重写器显式识别 `B`、`BL`、`B.cond`、`ADR`、`ADRP`、literal load、`CBZ/CBNZ`、`TBZ/TBNZ` 等类型。源码中每类指令都有独立的长度计算和 rewrite 分支，这正是“复制几条指令后跳回去”经常崩溃的原因。

### 5.2 branch island 与并发改写

arm64 的直接 `B` 使用 26 位有符号立即数并按 4 字节缩放，目标范围约为当前 PC 的前后 128 MiB。若能在范围内分配 branch island，原入口只需改写一条对齐的 4 字节指令；若不能，则通常要写入多条指令组成的绝对跳转序列。

单条对齐指令的原子写比多指令覆盖容易控制，但仍要做指令缓存同步。多指令 patch 还会出现另一个窗口：其他核心可能取到一半旧指令、一半新指令。可靠实现需要证明其发布协议、线程协调和缓存维护成立，不能把一次 `memcpy()` 当作并发安全。

这也是应优先选择“近跳 island”的原因之一：它不只节省 trampoline 空间，还把原入口的发布动作缩小到一条指令。

### 5.3 PAC、BTI 与 CFI

Android 17 的 arm64 代码可能同时面对几类控制流保护：

- **PAC**：函数序言或返回路径可能签名、认证 LR。搬迁序言时不能丢失、重复或改变相关栈状态。
- **BTI**：bionic linker 会读取 GNU property；当 ELF 声明兼容且硬件支持时，为可执行段加入 `PROT_BTI`。通过间接 `BR/BLR` 到达的 proxy 或 trampoline 入口需要满足对应 landing-pad 约束。
- **CFI**：代理函数签名不一致，或把 GOT 指向不满足类型检查的地址，可能触发 CFI abort。以 Hook 私有 CFI helper 来绕过检查，会把平台防护和版本私有实现一起变成依赖。

Hook 框架需要把这些能力纳入测试组合，而不是只检查 CPU 是否为 arm64。尤其要覆盖启用 `-mbranch-protection`、LTO/CFI、不同链接可见性和系统库 Build ID 的产物。

### 5.4 代码页权限

Inline Hook 需要修改可执行映射。当前 ShadowHook 源码会把目标区间 `mprotect()` 为 `PROT_READ | PROT_WRITE | PROT_EXEC`，完成原子写后调用 `__builtin___clear_cache()`。这证明运行时 patch 与 `DT_TEXTREL` 不是同一条 linker 路径，也提醒我们：W+X 窗口本身就是安全成本。

工程上应缩短可写可执行窗口、限制可修改目标、记录权限变更失败，并在框架设计允许时恢复最小权限。不能用关闭 SELinux、修改系统属性或依赖 root 作为普通应用方案。

## 6. Trap Hook：必须自己负责信号语义

arm64 软件断点通常用 `BRK` 触发 `SIGTRAP`。处理函数至少要完成：

- 只消费属于本框架的 `si_code` 和指令地址；
- 从 `ucontext_t` 读取并按 ABI 修改寄存器与 PC；
- 保证处理路径满足异步信号安全；
- 处理嵌套信号、线程退出、unhook 和断点表并发；
- 对非本框架事件调用前序 handler 或恢复默认处置；
- 与 ptrace 调试器、采样器、崩溃 SDK 和 native bridge 一起测试。

Android 17 的 debuggerd 在 `debuggerd_init()`（`system/core/debuggerd/handler/debuggerd_handler.cpp` line 884+）中为 `SIGTRAP` 等致命信号注册处理函数，并设置 `SA_SIGINFO | SA_ONSTACK | SA_RESTART | SA_EXPOSE_TAGBITS`：

```cpp
struct sigaction action = {.sa_sigaction = debuggerd_signal_handler,
                           .sa_flags = SA_RESTART | SA_SIGINFO};
sigfillset(&action.sa_mask);
action.sa_flags |= SA_ONSTACK;          // alt-stack 应对栈溢出
action.sa_flags |= SA_EXPOSE_TAGBITS;   // 请求内核把 fault addr 的 tag bit 暴露给 user
debuggerd_register_handlers(&action);
```

`SA_EXPOSE_TAGBITS` 是 Android 17 在 sigaction 层面新增的 flag，使 GWP-ASan、MTE 故障可读 tag 字节。

`debuggerd_signal_handler()`（line 663+）处理 `SIGTRAP`、`SIGSEGV`、`SIGBUS`、`SIGFPE`、`SIGILL`、`SIGABRT` 等信号。主要步骤包括：设置 `PR_SET_DUMPABLE=1` 允许 `crash_dump` ptrace attach；通过 `clone()` 派生 pseudothread（`CLONE_THREAD|CLONE_SIGHAND|CLONE_VM|CLONE_CHILD_SETTID`），共享信号处理表和地址空间，`crash_dump` 进程再通过 `ptrace` 暂停和读取目标线程完成 tombstone 落盘；最终按信号语义终止进程。

`SA_EXPOSE_TAGBITS` 不是 Android 17 才加入这条路径的新能力——准确地说，`SA_EXPOSE_TAGBITS` 是 Android 17 新增的 flag 值，但 `SIGTRAP` 走 `debuggerd_signal_handler` 这条链路在更早版本已存在。应用若正确安装并消费自己的 `SIGTRAP`，并不必然生成 tombstone；如果事件进入 debuggerd 的致命处理路径，debuggerd 会创建 pseudothread，启动 `crash_dump`，后者仍通过 `ptrace` 暂停和读取目标线程，完成后再按信号语义终止进程。

这条链路说明了两个边界：

1. Trap Hook 不能调用 debuggerd 私有 handler 来“协助恢复”。debuggerd 的职责是崩溃转储。
2. 自定义 handler 不能吞掉所有 `SIGTRAP`。硬件断点、调试器事件和其他组件的断点必须继续按原语义处理。

对于高频函数，逐次进入信号处理路径的成本和兼容风险通常不可接受。Trap 更适合短期诊断或低频探针，不适合作为通用线上拦截器。

## 7. 代理函数的 ABI 和重入约束

代理函数必须与被替换目标拥有完全兼容的调用约定。需要核对的不只是参数个数：

- 整数、浮点和向量参数分别使用哪些寄存器；
- 大结构体返回是否通过隐藏的结果指针；
- C++ 成员函数的 `this`、name mangling 和异常边界；
- 可变参数、栈对齐和保留寄存器；
- PAC/BTI/CFI 编译选项；
- `errno` 是否属于接口语义。

下面的骨架用于说明重入与 `errno` 的基本顺序，不是可直接复制的完整 Hook：

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

这个示例仍省略了取消点、异常退出、信号重入和初始化竞态。生产代码还要用 RAII 或等价机制保证任何返回路径都清理线程局部状态，并确认代理声明与目标导出声明逐项一致。

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

### 8.2 不要轻率 unhook

恢复 GOT 指针不等于旧 proxy 已无人执行，恢复函数入口也不等于 trampoline 可以立刻释放。线程可能仍在 proxy、原函数 trampoline 或被覆盖区间内。

更安全的关闭方式通常是保留稳定入口，只用原子开关让 proxy 直接调用原函数。若必须物理 unhook，需要有活动调用计数、宽限期或停线程协议，并确认目标 ELF 尚未卸载、槽或指令仍属于本框架。

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

观察自有或指定第三方 ELF 的 `openat`、`close`、`dup`、`socket` 等导入调用时，PLT/GOT Hook 通常比进程级 Inline Hook 更容易限定影响面。代理函数应保存 `errno`，使用无分配记录路径，并把“未经过导入槽的直接 syscall”写入覆盖盲区。

这类方案适合辅助定位 FD 泄漏，不应替代 `/proc/self/fd` 快照、资源所有权和调用栈采样。参见 20.12《FD 资源监控与治理》。

### 9.2 分配器监控

直接 Hook `malloc/free` 会让日志、符号化、容器扩容乃至 Hook 框架自身再次进入分配器。若目标是定位堆问题，优先评估 heapprofd、GWP-ASan、Scudo 诊断和 MTE。只有这些工具无法覆盖且已有无分配采集器时，才考虑限定调用方的 PLT Hook。

### 9.3 私有运行时函数

对 `libart.so` 私有函数做 Inline Hook，即使在某台 Android 17 设备上成功，也不代表同 API、不同主线模块或厂商构建可复用。符号存在不等于签名、序言、CFI 和调用时机一致。

这类 Hook 应按具体 Build ID 管理，并保留“一律不安装”的默认分支。用于研究的偏移和线上允许列表也应分开维护。

### 9.4 新 ELF 装载

若采集目标包含插件、动态特性或运行时 `dlopen()` 的 SDK，只扫描一次进程模块必然漏报。应订阅框架提供的装载回调或在安全时点刷新模块，并对同一 Build ID 和 load bias 做幂等处理。

不要自行 Hook linker 私有 `soinfo` 字段来换取一个看似稳定的回调。ShadowHook 手册明确提到，相关偏移需要按 Android 版本扫描和适配，这本身就是维护成本。

### 9.5 Android 16 与 Android 17 版本差异

以下维度对比 `android-16`（API 36）与 `android-17`（API 37）在 Hook 相关机制上的变化：

| 维度 | android-16 (API 36) | android-17 (API 37) | 来源 |
|------|--------------------|--------------------|------|
| RTLD_LAZY 支持 | 已不支持 | 已不支持 | `bionic/linker/linker.cpp:3017-3018` 注释 |
| DT_PLTGOT 处理 | Ignored | Ignored | 同上 |
| signal handler SA flags | `SA_RESTART\|SA_SIGINFO\|SA_ONSTACK` | + `SA_EXPOSE_TAGBITS` | `debuggerd/handler/debuggerd_handler.cpp:907-914` |
| GWP-ASan 路径 | 支持 | + `is_permissive_mte()` 路径，新增 recoverable `SEGV_MTESERR` | `debuggerd_handler.cpp:735-770` |
| 16KB page size 适配 | LP64 + ELF LLD path 已支持 | + 严格 ABI 对齐校验 | `linker_relocate.cpp:193-211` `handle_text_protection` |
| MEMTAG globals | 实验性 | 默认开启（`should_tag_memtag_globals()`） | `linker_relocate.cpp:345-358` |
| ART sigchain | 强制走 sigchain 优先 | 维持 + 信号 SivalInt 包含 dump 请求；新增 `BIONIC_SIGNAL_ART_PROFILER` 路径 | `debuggerd_handler.cpp` 已覆盖 |

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

## 12. 源码锚点与参考资料

以下平台源码均以 `android-17.0.0_r1` 为准：

- [bionic linker.cpp](https://android.googlesource.com/platform/bionic/+/refs/tags/android-17.0.0_r1/linker/linker.cpp)：`DT_JMPREL`、`DT_PLTGOT`、`DT_TEXTREL`、`protect_relro()`。
- [bionic linker_relocate.cpp](https://android.googlesource.com/platform/bionic/+/refs/tags/android-17.0.0_r1/linker/linker_relocate.cpp)：`R_GENERIC_JUMP_SLOT`、`GLOB_DAT`、IRELATIVE 等重定位处理。
- [bionic linker_phdr.cpp](https://android.googlesource.com/platform/bionic/+/refs/tags/android-17.0.0_r1/linker/linker_phdr.cpp)：GNU property 与 arm64 `PROT_BTI`。
- [debuggerd handler.h](https://android.googlesource.com/platform/system/core/+/refs/tags/android-17.0.0_r1/debuggerd/include/debuggerd/handler.h)：致命信号集合与 `SIGTRAP` 注册。
- [debuggerd_handler.cpp](https://android.googlesource.com/platform/system/core/+/refs/tags/android-17.0.0_r1/debuggerd/handler/debuggerd_handler.cpp)：pseudothread、`crash_dump` 和 `ptrace` 配合链路。
- [ART sigchain.cc](https://android.googlesource.com/platform/art/+/android-17.0.0_r1/sigchainlib/sigchain.cc)：special handler、debuggerd recovery hook 与用户 handler 的转发次序。

工程实现与平台规则：

- [ShadowHook manual](https://github.com/bytedance/android-inline-hook/blob/main/doc/manual.md) 与 [arm64 指令重写源码](https://github.com/bytedance/android-inline-hook/blob/main/shadowhook/src/main/cpp/arch/arm64/sh_a64.c)。
- [ByteHook 原理说明](https://github.com/bytedance/bhook/blob/main/doc/overview.zh-CN.md) 与 [GOT 重定位写入源码](https://github.com/bytedance/bhook/blob/main/bytehook/src/main/cpp/bh_elf_relocator.c)。
- [Android 16 KB page size 指南](https://developer.android.com/guide/practices/page-sizes)。
- [Android 7.0 非公开 Native 库限制](https://developer.android.com/about/versions/nougat/android-7.0-changes)。
- [Android linker namespace](https://source.android.com/docs/core/permissions/namespaces_libraries)。
- [Arm PAC、BTI 与 MTE 指南](https://developer.arm.com/-/media/Arm%20Developer%20Community/PDF/Learn%20the%20Architecture/Providing%20protection%20for%20complex%20software.pdf)。

关联阅读：

- 14.26《Android Hook 基础设施》
- 20.12《FD 资源监控与治理》
- 20.16《Native 栈回溯与符号化》
- 20.3《Native Crash 分析与 debuggerd 链路》
