---
title: "Android 17 ARM64 内核安全缓解机制性能开销与调优"
chapter: "16.10"
section: "16.10"
status: ready-for-review
applicable_versions: "Android 12 (API 31) - Android 17 (API 37)"
tags: [kernel-security, ARM64, KASLR, KPTI, Spectre, PAC, BTI, MTE, GCS, CFI, performance-overhead]
related_chapters: ["4.15", "5.1", "5.4", "5.5", "16.4", "16.5", "16.9", "20.10"]
last_verified: "2026-08-14"
last_verified_against: "Android 17 / API 37 / AOSP android-17.0.0_r1; Android Common Kernel android17-6.18-2026-06_r6 (gki_defconfig, ARM64 and arch Kconfig, entry, KASLR, Spectre, PAC, MTE, GCS, kernel parameters)"
confidence: high
sources:
  - type: kernel
    path: "https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/arch/arm64/Kconfig"
  - type: kernel
    path: "https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/arch/Kconfig"
  - type: kernel
    path: "https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/arch/arm64/configs/gki_defconfig"
  - type: kernel
    path: "https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/arch/arm64/include/asm/barrier.h"
  - type: kernel
    path: "https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/include/linux/nospec.h"
  - type: kernel
    path: "https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/arch/arm64/kernel/entry.S"
  - type: kernel
    path: "https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/arch/arm64/kernel/kaslr.c"
  - type: kernel
    path: "https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/arch/arm64/kernel/proton-pack.c"
  - type: kernel
    path: "https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/Documentation/admin-guide/kernel-parameters.txt"
  - type: kernel
    path: "https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/Documentation/arch/arm64/pointer-authentication.rst"
  - type: kernel
    path: "https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/Documentation/arch/arm64/memory-tagging-extension.rst"
  - type: kernel
    path: "https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/Documentation/arch/arm64/gcs.rst"
  - type: official
    path: "https://source.android.com/docs/security/test/memory-safety/arm-mte"
  - type: official
    path: "https://developer.android.com/ndk/guides/stable_apis"
---

# Android 17 ARM64 内核安全缓解机制性能开销与调优

> **版本口径**：平台源码以 Android 17 / API 37 / `android-17.0.0_r1` 为准，内核源码以 `android17-6.18-2026-06_r6` 为准。配置、硬件能力和运行时策略共同决定安全机制是否生效。
>
> MTE 的应用实践见 [§4.15](../../part1-fundamentals/ch04-memory/15-android17-memory-tagging-extension-mte.md)，Rust 系统组件的边界见 [§16.9](09-rust-system-services-performance.md)。

## 1. 先确认三个条件

Kconfig 是 Linux 内核描述配置选项、依赖关系和默认值的系统。看到其中的 `default y`，只能说明依赖满足且没有其他配置覆盖时，该选项默认取 `y`。它无法单独证明某台 Android 设备正在使用对应机制。设备结论需要同时满足三个条件：

1. **构建条件**：最终 `.config` 含有所需选项，编译器和链接器也支持相应插桩。
2. **硬件与固件条件**：CPU 实现架构特性，或固件提供内核所需的漏洞缓解调用。
3. **运行时条件**：内核没有通过启动参数关闭功能；用户态机制还需要二进制或进程显式启用。

Android 17 GKI（Generic Kernel Image，通用内核镜像）的基准配置 `gki_defconfig` 明确设置了 `CONFIG_RANDOMIZE_BASE=y`、`CONFIG_SHADOW_CALL_STACK=y` 和 `CONFIG_CFI=y`。

同一配置关闭了 `CONFIG_RANDOMIZE_MODULE_REGION_FULL`。

PAC、BTI、MTE 与 GCS 在 `arch/arm64/Kconfig` 中是 `default y`，仍受工具链、硬件和运行时条件约束。

下面这张表用于确定排查入口，不提供脱离设备和负载的固定性能百分比。

| 机制 | 保护对象 | Android 17 / 6.18 源码入口 | 生效条件 |
|---|---|---|---|
| KASLR | 内核与模块地址布局 | `CONFIG_RANDOMIZE_BASE`、`kaslr.c` | 构建开启、启动阶段获得熵、未传入 `nokaslr` |
| KPTI | EL0 与内核地址空间隔离 | `CONFIG_UNMAP_KERNEL_AT_EL0`、异常入口代码 | 构建开启，CPU 运行时判定需要或通过 `kpti=1` 强制 |
| Spectre v1 | 越界推测访问 | `array_index_nospec()`、架构屏障 | 易受影响的代码点完成局部修复 |
| Spectre v2 | 间接分支预测注入 | `proton-pack.c`、CPU capability 与固件接口 | 取决于 CPU 型号、固件和运行时选择 |
| Spectre-BHB | 分支历史注入 | `CONFIG_MITIGATE_SPECTRE_BRANCH_HISTORY` | CPU 需要缓解，内核选择分支序列或固件调用 |
| PAC | 返回地址或用户指针认证 | `CONFIG_ARM64_PTR_AUTH*` | 构建、硬件、二进制策略共同满足 |
| BTI | 计算分支合法落点 | `CONFIG_ARM64_BTI*` | 构建与硬件支持，目标代码带 BTI 属性 |
| SCS | 内核返回地址 | `CONFIG_SHADOW_CALL_STACK` | 编译器插桩与内核运行时支持 |
| KCFI | 内核间接调用目标类型 | `CONFIG_CFI` | 编译器支持 `-fsanitize=kcfi` |
| MTE | 用户态内存访问标签 | `CONFIG_ARM64_MTE` | 构建、硬件、映射属性与进程模式共同满足 |
| GCS | 用户态返回地址栈 | `CONFIG_ARM64_GCS`、GCS 用户 ABI | 构建、硬件和线程级 `prctl()` 启用 |

表中的 EL0 是非特权用户态执行所在的最低异常级。CPU capability 是内核根据特性寄存器、CPU 型号和勘误表得到的能力标志，不等同于产品宣传中的架构名称。

这几组机制保护的边界不同。BTI 约束间接分支的落点，Spectre v2 缓解处理分支预测器状态；两者不能互相替代。SCS 保护内核返回地址，KCFI 检查内核间接调用的静态类型；GCS 是内核向用户态提供的受保护返回地址栈 ABI。

这里的 ABI（Application Binary Interface）指内核与用户程序约定的寄存器、系统调用和数据结构接口。

## 2. KASLR：启动阶段的地址随机化

KASLR（Kernel Address Space Layout Randomization）启用并获得有效随机种子后，会在启动时改变内核及模块的基地址，使攻击者更难预先知道内核对象的位置。ARM64 KASLR 由 `CONFIG_RANDOMIZE_BASE` 控制。

`arch/arm64/Kconfig` 规定，bootloader（引导程序）可通过设备树 `/chosen/kaslr-seed` 传入随机 `u64`，即 64 位无符号种子。经 UEFI stub 启动时，这段早期引导代码可从 `EFI_RNG_PROTOCOL` 获取熵。

这里的熵指难以预测的随机输入，`arch/arm64/kernel/kaslr.c` 用它计算内核镜像与模块区域的偏移。

`CONFIG_RELOCATABLE` 让 AArch64 内核保留运行时重定位所需的信息。重定位是按实际加载基址修正代码或数据中的地址引用，发生在启动阶段。这个成本应在同一构建、同一设备上测量，不能从镜像体积推导固定毫秒数。KASLR 也不会因为地址变化就给每次间接调用附加一项固定成本。

模块区域还有一项容易写错的配置：

- `CONFIG_RANDOMIZE_MODULE_REGION_FULL=y` 会在覆盖核心内核的 2 GiB 窗口内随机化模块区域，并可能让模块到核心内核的调用经过 module PLT veneer。PLT（Procedure Linkage Table）veneer 是位于模块 PLT 中的跳转桩，用来跨越 AArch64 直接分支指令的距离限制。
- Android 17 的 6.18 GKI `gki_defconfig` 明确写着 `# CONFIG_RANDOMIZE_MODULE_REGION_FULL is not set`。模块区域仍会在较小范围内随机化，不等于模块地址固定。

量产设备常用 `kptr_restrict` 限制内核指针暴露，因而 `/proc/kallsyms` 可能把地址显示为全零。这种结果不能用来判断 KASLR 失效。工程构建可结合最终配置、启动日志和多次冷启动后的符号地址检查；量产结论应以厂商构建产物与启动链配置为依据。

## 3. KPTI：是否执行页表切换由 CPU 判定

KPTI（Kernel Page Table Isolation）用于隔离用户态与内核态页表。`CONFIG_UNMAP_KERNEL_AT_EL0` 的帮助文本描述了 ARM64 实现：CPU 在 EL0 运行时取消大部分内核映射。

发生系统调用、中断或异常后，CPU 经 exception vector table（异常向量表）找到入口，再由 trampoline page（仅保留入口所需映射的跳板页）恢复内核映射。

Android 17 的内核仍把该选项设为 `default y`。

运行时策略比 Kconfig 值更具体。6.18 的启动参数文档对 `kpti=` 的定义是：

- 默认只在需要缓解的核心上启用；
- `kpti=0` 强制关闭；
- `kpti=1` 强制开启。

因此，不能根据 CPU 产品名、上市年份或营销架构名称编制一张“必定启用/跳过”的表。ARM64 内核会综合 CPU capability、MIDR（Main ID Register，CPU 型号与版本标识）匹配、架构特性和勘误信息做判定。

同一 SoC（System on Chip，系统级芯片）还可能包含多种核心。以设备的内核日志、漏洞状态节点和源码匹配结果为准。

KPTI 的热点位于用户态与内核态的往返路径。系统调用、缺页异常和中断密集的负载更值得测量；纯用户态计算的结果不能代表 Binder、网络或存储负载。

TLB（Translation Lookaside Buffer）缓存虚拟地址到物理地址的转换，ASID（Address Space Identifier）用于区分不同地址空间的缓存项。页表切换对 TLB 的影响取决于 ASID、CPU 特性和内核实现，不能概括为“每次都完整刷新 TLB”。

## 4. ARM64 投机执行漏洞缓解

### 4.1 Spectre v1：局部代码修复

Spectre v1 属于 bounds-check bypass（边界检查绕过）：CPU 可能在边界判断完成前推测执行后续访问。

通用 `array_index_nospec()` 会调用架构提供的 mask 实现。6.18 ARM64 的 `array_index_mask_nospec()` 用比较结果生成全零或全一掩码，使越界索引失去可用值，并在返回前执行 `CSDB`，限制后续指令提前使用推测得到的数据。

`SSBS`（Speculative Store Bypass Safe）控制 Spectre v4 相关的推测存储绕过，不能用来概括这条数组索引修复路径。

局部修复分布在各子系统中，开销也与命中这些路径的次数有关。若性能回退集中在一个驱动或系统调用，需要检查该路径生成的指令和采样结果，不能把整机差异统一归到 Spectre v1。

### 4.2 Spectre v2：CPU、固件和运行时代码选择

ARM64 的主实现位于 `arch/arm64/kernel/proton-pack.c`。内核识别 CPU 是否受影响，再选择架构提供的硬件行为、固件调用、CPU 专用回调或内核指令序列。

ARM64 alternatives 是其中一项启动期代码选择机制：内核启动时按 CPU 能力改写预留的指令片段。它参与部分异常入口和 BHB 缓解路径，不能概括所有 Spectre v2 处理方式。

Retpoline 是 x86 中常见的返回跳板软件方案，不能用来描述 Android ARM64 的 Spectre v2 主路径。`CONFIG_ARM64_BTI_KERNEL` 也不负责“替换 Retpoline”：BTI 检查计算分支能否到达目标位置，Spectre v2 缓解则约束推测执行利用分支预测状态的方式。

### 4.3 Spectre-BHB 与 Speculative Store Bypass

BHB（Branch History Buffer）保存近期分支历史，攻击者可能借此影响后续推测路径。`CONFIG_MITIGATE_SPECTRE_BRANCH_HISTORY` 在 6.18 中为 `default y`。Kconfig 对处理方式的描述是：从用户态进入异常时，用一段分支序列或固件调用覆盖分支历史。

`SB` 是 Speculation Barrier 指令，但具体 CPU 还可能使用 `ClearBHB`、分支循环、固件调用或硬件保证，不能把实现固定写成“入口插入一条 `SB`”。

Speculative Store Bypass 使用另一套控制。`ssbd=` 是 SSBD（Speculative Store Bypass Disable）的启动参数，支持 `force-on`、`force-off` 和 `kernel`；`kernel` 表示内核持续使用缓解，并允许用户线程通过 `prctl()` 按需请求。

`prctl()` 是调整进程或线程行为的系统调用。它与 Spectre v1、v2、BHB 应分别核查。

设备上的只读状态节点比 CPU 名称推断更可靠。工程机可读取以下信息建立证据链。

```bash
adb shell 'cat /proc/cmdline'
adb shell 'for f in /sys/devices/system/cpu/vulnerabilities/*; do
  printf "%s: " "$(basename "$f")"
  cat "$f"
done'
```

第一项显示启动参数，第二项遍历 sysfs（内核导出的虚拟文件系统）的 `vulnerabilities` 节点，读取内核向用户空间报告的漏洞和缓解状态。节点集合与文本由设备内核决定；缺少某个节点时应回到该设备的源码和配置核查。

## 5. PAC、BTI、SCS 与 KCFI：四条控制流防线

### 5.1 PAC：指针认证码

PAC（Pointer Authentication Code）把密钥、指针值及上下文计算成认证码，用于检测指针被替换或破坏。ARM64 用户态 PAC 支持由 `CONFIG_ARM64_PTR_AUTH` 控制。Linux 文档列出五个密钥：APIA、APIB 用于指令地址，APDA、APDB 用于数据地址，APGA 用于通用认证码。

内核在 `exec()` 时为进程初始化密钥，同一进程内的线程共享这些密钥；`fork()` 后子进程继承。文档没有规定密钥必须由 `RNDR` 或 `RNDRRS` 指令直接生成，也不能据此推导一个固定的进程创建耗时。

`CONFIG_ARM64_PTR_AUTH_KERNEL` 的范围更窄：编译器为内核函数返回地址加入保护。该选项不能概括成“所有内核函数指针都会被 PAC 签名”。对间接函数指针调用的前向保护，应查看 KCFI 与 BTI。

用户态通过 `HWCAP_PACA` 和 `HWCAP_PACG` 获知相应能力。HWCAP（hardware capability）是内核通过 ELF 辅助向量交给进程的硬件能力位。二进制是否使用 PAC 取决于生成的指令与运行库策略；硬件支持本身不会给已有代码自动加入函数序言与尾声。

ELF note 是二进制中的构建属性记录，可作为静态证据；反汇编中的 `PAC*`/`AUT*` 指令才能直接说明目标代码包含认证序列。

### 5.2 BTI：限制间接分支入口

`CONFIG_ARM64_BTI` 允许内核为用户态提供 BTI 支持，`CONFIG_ARM64_BTI_KERNEL` 让内核及其模块带有 BTI 标记并在硬件支持时执行检查。后者依赖 PAC 内核配置和编译器的 `-mbranch-protection` 能力。

BTI（Branch Target Identification）把合法目标缩小到带相应 landing pad 的位置。landing pad 是编译器放在允许入口处的兼容指令，常见形式为 `BTI`；CPU 可拒绝间接分支跳入其他位置。BTI 与 PAC 配合保护控制流，但覆盖面仍取决于全部参与链接和加载的代码是否带兼容属性。内核模块也必须满足同一要求。

### 5.3 Shadow Call Stack

`CONFIG_SHADOW_CALL_STACK`（SCS）使用编译器插桩，把返回地址的受保护副本保存在独立的 shadow stack（影子调用栈）中，降低普通栈内存破坏覆盖返回地址的风险。Android 17 GKI `gki_defconfig` 已开启该项。它是内核构建期机制，与后文的用户态 GCS 不属于同一个 ABI。

### 5.4 KCFI

6.18 的 `CONFIG_CFI` 使用 KCFI（Kernel Control-Flow Integrity）。编译器在间接函数调用处加入类型检查，只允许目标落到静态类型匹配的函数。这里的前向保护指调用者到间接调用目标的边，SCS 和 PAC return-address protection 则处理函数返回路径。

检查本地 ELF 是否声明 AArch64 branch protection，可使用 NDK 中对应版本的 `llvm-readelf`。下面的命令用于观察 GNU property 和 note，不能单独证明运行时硬件已经执行检查。

```bash
llvm-readelf -n libexample.so
llvm-objdump -d libexample.so | grep -E '\bbti\b|\bpaci[ab]sp\b|\bauti[ab]sp\b'
```

第一行读取 ELF note，第二行抽查反汇编中的 BTI 与 PAC 指令。还需要结合进程映射、设备 HWCAP 和完整链接产物判断覆盖范围；若其中一个静态库没有使用兼容选项，最终二进制的属性或覆盖面也可能变化。

## 6. MTE：标签粒度不等于固定 PSS 增量

ARM64 MTE（Memory Tagging Extension）把内存划分为 16 字节的 allocation granule（分配标签粒度），每个粒度保存 4 位 allocation tag（内存标签），指针高位携带 logical tag（逻辑标签）。CPU 访问内存时比较两者。

tag mismatch（标签不匹配）可同步报告到出错指令，也可异步延迟到稍后的内核入口；asymmetric 模式对读访问同步报告、对写访问异步报告。

内核支持由 `CONFIG_ARM64_MTE` 控制，硬件与内核同时支持时通过 `HWCAP2_MTE` 告知用户空间。带标签的页只能来自使用 `PROT_MTE` 的匿名映射或 RAM-backed 文件映射，例如 tmpfs 或 `memfd`；RAM-backed 表示内容由内存页支撑，不是普通持久化文件。

线程还要通过 `PR_SET_TAGGED_ADDR_CTRL` 设置 tagged-address ABI（允许地址高位携带标签的约定）与 fault mode（标签错误的报告模式）。

Android 应用通常由 `android:memtagMode`、runtime（运行时）和 Scudo 分配器完成进程级原生堆配置，不要求业务代码逐个调用 `mmap()`。

4 位标签是架构标签存储格式，不能换算成“PSS 固定增加 3% 或 5%”。标签存储、分配器元数据、页提交、工作集和故障模式对 CPU 与内存指标的影响不同。评估 MTE 时至少分别记录：

- 进程 PSS、RSS、匿名页和 swap；
- 分配速率、释放速率与 Scudo 路径；
- 同步 fault 的定位收益和用户可见延迟；
- 异步 fault 的发现延迟与崩溃归因；
- 同一业务脚本下的 CPU time、帧时间和功耗。

PSS（Proportional Set Size）把私有页全额计入，并按共享进程数分摊共享页；RSS（Resident Set Size）统计当前驻留在物理内存中的页，swap 是被换出的匿名内存。三者口径不同，应同时查看。Scudo 是 Android 使用的强化型原生堆分配器，分配与释放策略也会影响 MTE 的观测结果。

[§4.15](../../part1-fundamentals/ch04-memory/15-android17-memory-tagging-extension-mte.md) 讨论 MTE 的进程配置。

[§20.10](../../part5-app/ch20-stability/10-mte-gwp-asan-native-memory-safety.md) 讨论 MTE 崩溃检测与治理。这里仅限定内核能力与性能测量边界。

## 7. GCS：Android 17 内核提供用户态 ABI

GCS（Guarded Control Stack）为用户态线程维护一份受硬件保护的返回地址栈。`CONFIG_ARM64_GCS` 位于 ARMv9.4 架构特性菜单，6.18 Kconfig 将其设为 `default y`。这个配置让内核在硬件存在时提供 GCS 用户 ABI；它没有让 Linux 内核函数自动改用 GCS。

用户态通过 `HWCAP_GCS` 发现硬件与内核支持，再按线程调用 `prctl(PR_SET_SHADOW_STACK_STATUS, PR_SHADOW_STACK_ENABLE, ...)` 启用。新线程继承状态，`exec()` 会清除启用状态。

GCS 检查失败通过 `SIGSEGV` 和 `SEGV_CPERR` 上报；`/proc/<pid>/smaps` 是进程内存映射的详细视图，受保护栈页可在其中显示 `ss` 标志。

因此，`CONFIG_ARM64_GCS=y`、CPU 支持 GCS、Android runtime 或 native（原生）程序启用 GCS 是三件独立的事。没有进程侧证据时，不能把 GCS 开销计入应用，也不能给出每次调用固定周期数。

## 8. 设备核查方法

### 8.1 核对构建与启动状态

工程构建可尝试读取压缩内核配置；量产设备往往不暴露 `/proc/config.gz`，此时应读取构建生成的 `.config` 或厂商发布的内核构建产物（kernel build artifact）。

```bash
adb shell 'test -r /proc/config.gz &&
  zcat /proc/config.gz |
  grep -E "CONFIG_(RANDOMIZE_BASE|UNMAP_KERNEL_AT_EL0|ARM64_PTR_AUTH|ARM64_BTI|ARM64_MTE|ARM64_GCS|SHADOW_CALL_STACK|CFI)="'
adb shell 'cat /proc/cmdline'
adb shell 'grep -E "paca|pacg|bti|mte|gcs" /proc/cpuinfo'
```

配置回答“内核是否编入支持”，命令行回答“启动时是否覆盖策略”，`/proc/cpuinfo` 的 CPU features 回答“内核向用户态公布了哪些能力”。三者缺一时，结论应保留条件。

### 8.2 为工作负载建立归因

性能审计应按路径选择指标。下表中的 PMU（Performance Monitoring Unit）事件是 CPU 硬件计数器记录的周期、分支、缓存或 TLB 等事件；事件名称和可用范围由 SoC 决定。

| 怀疑对象 | 适合的负载 | 需要记录 |
|---|---|---|
| KASLR | 冷启动与内核阶段启动 | 同一镜像的启动阶段时间点、重定位日志、样本分布 |
| KPTI | 高频短系统调用、Binder、网络、存储 | 系统调用率、内核/用户 CPU time、调度与 TLB 相关 PMU 事件 |
| Spectre v2/BHB | 频繁进出内核、间接分支密集路径 | CPU 型号、漏洞状态、固件版本、分支预测相关 PMU 事件 |
| PAC/BTI/SCS/KCFI | native 与内核控制流密集负载 | 指令数、cycles、branch miss、文本大小、调用栈分布 |
| MTE | native 分配与访存密集负载 | fault mode、分配器指标、PSS/RSS、CPU time、功耗 |
| GCS | 明确启用 GCS 的 native 进程 | 线程状态、`smaps`、调用密度、fault 记录 |

`simpleperf` 适合核对指令、周期和分支事件，Perfetto 适合把调度、Binder、缺页、I/O 与业务阶段放到同一时间轴。PMU 事件名称随 SoC 和内核权限变化，采集前应运行 `simpleperf list`，只使用设备公布的事件。

下面的命令用于确认设备支持的事件，再对一个可重复的 native workload（原生测试负载）采样。

```bash
adb shell simpleperf list
adb shell simpleperf stat \
  -e task-clock,cycles,instructions,branches,branch-misses \
  -- /data/local/tmp/security_bench
```

输出可用于计算 IPC（instructions per cycle，每周期指令数；这里不是进程间通信）、每次业务操作消耗的 cycles（CPU 周期数）和 branch-miss（分支预测失败）比例。一次采样不足以归因，需要预热、固定业务输入并记录温度与频率状态。

### 8.3 A/B 测试的安全边界

关闭缓解只适用于隔离实验室中的可丢弃工程镜像。测试设备不得承载账号、密钥、个人数据或生产网络访问。每个实验只改一个因素，并保留完整的 boot image、内核配置、启动参数和固件版本。

6.18 文档中与 ARM64 相关的参数如下：

| 参数 | 6.18 定义 | 审计提示 |
|---|---|---|
| `nokaslr` | 关闭内核与模块 base offset ASLR | 独立于 `mitigations=off` |
| `kpti=0` / `kpti=1` | 强制关闭或开启页表隔离 | 默认值是“在需要缓解的核心上开启” |
| `nospectre_v2` | 关闭 ARM64 Spectre v2 缓解 | 会暴露数据泄漏风险 |
| `nospectre_bhb` | 关闭 ARM64 Spectre-BHB 缓解 | 会暴露数据泄漏风险 |
| `ssbd=force-off` | 关闭 Speculative Store Bypass 缓解 | 与 Spectre v1/v2 分开 |
| `arm64.nopauth` | 关闭 Pointer Authentication 支持 | 影响内核公布与使用该能力 |
| `arm64.nomte` | 关闭 MTE 支持 | 影响内核公布与使用该能力 |
| `mitigations=off` | 关闭一组可选 CPU 漏洞缓解 | 不会自动关闭 KASLR |

`nospectre_v1` 在该文档中只标记为 x86 与 PowerPC 参数，不能列入 ARM64 测试方案。旧写法 `nopti` 也不应替代 ARM64 文档明确给出的 `kpti=0`。

每组测试应执行多轮并交错顺序，报告中给出分位数、离散程度和热状态。若差异小于样本噪声，应记录为“当前负载未检出差异”，避免把微基准结果外推到整机体验。

## 9. 应用与系统性能优化边界

应用开发者通常不能改变内核缓解策略，也不应通过关闭安全机制换取分数。性能工作可以从可控路径入手：

- 用 Perfetto 统计 Binder transaction（一次 Binder 驱动事务）、系统调用、I/O 和调度等待，确认时间花在哪个阶段；
- 批量 Binder 请求前先检查接口语义、错误处理和延迟预算，避免只为减少调用次数扩大单次事务；
- 共享内存适合大块数据传输，但同步、生命周期、权限和一致性成本需要计入；
- native 热点应根据 profile（采样或剖析结果）决定内联、数据布局或间接调用调整，不能为了躲避 KCFI/BTI 破坏类型安全；
- NDK 库启用 branch protection（PAC/BTI 分支保护）时，要核查全部静态库、共享库和装载路径的兼容性；
- MTE 的同步模式适合需要精确故障地址的验证阶段，生产策略要结合崩溃治理、性能和设备覆盖率。

Android NDK 的 Native APIs 文档没有把 `io_uring` 列为 Android 原生 API。直接调用 `io_uring` 面对的是 Linux kernel UAPI，即内核与用户空间之间的底层接口。

即使某个 GKI 构建含有实现，SELinux 强制访问控制、seccomp 系统调用过滤器、系统调用可用性和 Android API 兼容边界仍可能限制普通应用。只有在目标设备、应用沙箱和兼容范围都经过验证后，才能把它作为特定场景方案。

## 10. 核查清单

- [ ] 平台结论锚定 `android-17.0.0_r1`，内核结论锚定 `android17-6.18-2026-06_r6`
- [ ] 使用最终 `.config`，没有把 Kconfig 的 `default y` 写成设备启用证明
- [ ] 同时记录 CPU 型号、固件版本、启动参数和漏洞状态节点
- [ ] 没有把 BTI 写成 Spectre v2 或 Retpoline 的替代机制
- [ ] 没有把 SSBS 写成 Spectre v1 的通用屏障
- [ ] PAC kernel 的范围限定为返回地址保护
- [ ] SCS、KCFI、PAC、BTI 与 GCS 的保护对象分开说明
- [ ] MTE 标签位数没有直接换算成固定 PSS 增量
- [ ] 性能数字来自当前设备、当前镜像和可复现测试负载
- [ ] 关闭缓解的对照实验只在隔离工程设备上执行

## 11. 参考与源码锚点

- [ARM64 Kconfig：KPTI、BHB、PAC、BTI、MTE、GCS 与 KASLR](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/arch/arm64/Kconfig)
- [Android 17 GKI `gki_defconfig`](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/arch/arm64/configs/gki_defconfig)
- [通用 arch Kconfig：Shadow Call Stack 与 KCFI](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/arch/Kconfig)
- [ARM64 KASLR 实现](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/arch/arm64/kernel/kaslr.c)
- [ARM64 Spectre 与 SSBD 运行时实现](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/arch/arm64/kernel/proton-pack.c)
- [通用 `array_index_nospec()`](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/include/linux/nospec.h)
- [ARM64 `array_index_mask_nospec()` 与 `CSDB`](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/arch/arm64/include/asm/barrier.h)
- [ARM64 异常入口实现](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/arch/arm64/kernel/entry.S)
- [Linux 6.18 启动参数](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/Documentation/admin-guide/kernel-parameters.txt)
- [ARM64 Pointer Authentication 用户 ABI](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/Documentation/arch/arm64/pointer-authentication.rst)
- [ARM64 Memory Tagging Extension 用户 ABI](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/Documentation/arch/arm64/memory-tagging-extension.rst)
- [ARM64 Guarded Control Stack 用户 ABI](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/Documentation/arch/arm64/gcs.rst)
- [Android MTE 进程配置](https://source.android.com/docs/security/test/memory-safety/arm-mte)
- [Android NDK Native APIs](https://developer.android.com/ndk/guides/stable_apis)
