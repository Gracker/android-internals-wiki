---
title: "Android 17 ARM MTE 内存标签扩展实战"
chapter: "4.15"
status: ready-for-review
applicable_versions: "Android 12 (API 31) - Android 17 (API 37)"
last_verified: "2026-07-06"
last_verified_against: "AOSP android-17.0.0_r1"
confidence: high
tags: [Android 17, MTE, Memory Safety, ARM, Hardware Architecture, Scudo, Bionic]
related_chapters: ["20.10", "4.5", "14.5", "23.3"]
sources:
  - type: blog
    path: "Cubox/四年之后，重新审视 MTE：从硬件架构到工程落地-2025-12-18.md"
  - type: blog
    path: "Cubox/Android内存安全革命性改变：快手MTE探索与实践-2023-05-23.md"
  - type: aosp
    path: "bionic/libc/bionic/libc_init_common.cpp"
  - type: aosp
    path: "bionic/libc/platform/bionic/mte.h"
  - type: aosp
    path: "frameworks/base/core/java/android/content/pm/ApplicationInfo.java"
  - type: aosp
    path: "frameworks/base/core/java/com/android/internal/os/Zygote.java"
  - type: official
    path: "https://source.android.com/docs/security/test/memory-safety/arm-mte"
  - type: official
    path: "https://developer.android.com/ndk/guides/arm-mte"
  - type: research
    path: "DeepResearch/2026-05-26-android-mte-asymm-auto-enablement-mechanism.md"
---

# 4.15 Android 17 ARM MTE 内存标签扩展实战

平台源码以 AOSP `android-17.0.0_r1` 为基准，内核以 `android17-6.18-2026-06_r6` 为基准。讨论范围包括应用 native heap、stack、globals，以及 Android 如何把 manifest 配置传给 bionic 和 Scudo。

MTE 只能检查使用了 tagged memory 的 native 内存访问。Java/Kotlin 对象仍由 ART 管理；32 位进程、未启用 MTE 的映射、未正确设置 tag 的自定义分配器也不在同一保护范围内。

## MTE 硬件能力：从 FEAT_MTE 到 FEAT_MTE4

### Logical tag 与 allocation tag 的比较

MTE 为每个 16 字节 allocation granule 保存一个 4-bit allocation tag，并把指针虚拟地址的 bit 59～56 作为 logical tag。CPU 访问 Normal Tagged Memory 时比较两者：

```text
指针：0x0A00_7f12_3456_7800
          ^^
          logical tag = 0xA

内存：[0x...7800, 0x...780f]  allocation tag = 0xA
```

两者相同，访问可以继续；两者不同，处理方式由当前线程的 tag-check fault mode 决定。一个 granule 是 16 字节。32 字节只是在把两个 4-bit tag 紧凑存入一个字节时对应的数据量。

MTE 常用于发现两类 native 内存错误：

- **空间错误**：指针越过 allocation 边界，碰到 tag 不同的相邻 granule。
- **时间错误**：内存释放并重新分配后换了 tag，旧指针继续访问时发生不匹配。

4-bit tag 只有 16 种取值，因此检测带有概率性质。越界仍落在同一 16 字节 granule 内时也没有 tag 边界可触发检查。MTE 是 native 内存安全检测与缓解手段，不能证明程序不存在内存错误。

### FEAT_MTE、MTE2、MTE3、MTE4 与 Android 的关系

Arm 架构用 FEAT_MTE 到 FEAT_MTE4 表示逐步扩展的硬件能力。Android 工程中最需要区分的边界有两个：

- Armv8.5-A 引入 MTE 的 tag 指令、tagged memory 和检查机制。
- Armv8.7-A 的 FEAT_MTE3 加入 asymmetric mode：读按同步方式检查，写按异步方式报告。

FEAT_MTE4 属于后续 CPU 架构能力集合，不能把它理解成 Android 的第四种 `memtagMode`。截至 Android 17 / API 37，应用 manifest 仍只接受 `off`、`default`、`sync` 和 `async`。系统可在支持的 CPU 上把 ASYNC 请求按首选模式运行成 ASYMM，但应用没有 `asymm` 或 `mte4` manifest 值。

判断设备能力时应查询运行设备，不要从 Android 版本或 SoC 宣传名反推：

```bash
adb shell grep -w mte /proc/cpuinfo
```

出现 `mte` 表示内核向用户空间公布了相应 CPU capability。部分设备还要求通过开发者选项重启到支持 MTE 的系统配置；没有该选项也不能由应用自行补齐硬件或内核支持。

## Tag 生成与硬件检测机制

### Logical tag、allocation tag 与 TBI

AArch64 的 Top Byte Ignore（TBI）允许地址翻译忽略虚拟地址高字节中的一部分信息。MTE 使用 bit 59～56 携带 logical tag，内存侧则为每个 16 字节 granule 保存 allocation tag。

常用指令可按职责分成三组：

| 指令 | 用途 |
| --- | --- |
| `IRG` | 从允许集合中生成 logical tag，并写入指针 |
| `STG` / `ST2G` | 为一个或两个 16 字节 granule 写 allocation tag |
| `STZG` / `STZ2G` | 写 tag，同时把对应数据清零 |
| `LDG` | 读取地址对应的 allocation tag |

`IRG` 只改变指针 tag，不会给内存写 tag；`STG` 才更新内存的 allocation tag。自定义分配器若只做其中一步，合法访问也会发生 tag mismatch。

Android 17 的 `bionic/libc/platform/bionic/mte.h` 定义：

```cpp
#define PR_MTE_TAG_SET_NONZERO (0xfffeUL << PR_MTE_TAG_SHIFT)
```

bionic 初始化 MTE 时把这个 mask 交给 `prctl()`。非零 tag 可用于分配，tag 0 留给 Scudo chunk header，从而帮助捕获线性越界对 allocator 元数据的破坏。该结论来自 Android 的 Scudo 约定，不是所有 MTE 分配器都必须遵循的架构规则。

### 一次访问满足哪些条件才会检查

用户态 load/store 要接受 MTE 检查，需要同时满足：

1. CPU 与内核公布 MTE capability。
2. 地址所在映射以 `PROT_MTE` 建立，属于 Normal Tagged Memory。
3. 当前线程通过 `PR_SET_TAGGED_ADDR_CTRL` 选择了检查模式。
4. 当前执行上下文没有用 `PSTATE.TCO` 临时关闭检查。

CPU 随后比较 logical tag 与 allocation tag。架构定义可观察的异常语义，但不规定每款 CPU 必须使用相同的 TLB、cache、ROB 或 store buffer 实现。因此，不能用一套推测的流水线时序解释所有 Arm CPU 的开销。

## 三种检测模式的 CPU 流水线级分析

### SYNC

同步模式在发生 tag mismatch 的那条 load/store 上报告错误。Linux 发送：

```text
SIGSEGV
si_code = SEGV_MTESERR
si_addr = fault address
```

访问不会完成，tombstone 可以给出出错 PC 和地址。Android 在进程配置为 SYNC 时还让 Scudo记录 allocation/deallocation stack，以补充 use-after-free 或 buffer overflow 的上下文。

SYNC 更适合开发、测试和需要精确归因的高价值进程。它的成本会随 CPU、分配模式、内存访问和 Scudo 栈记录而变化，不能把 3%～30% 当作通用范围。

### ASYNC

异步模式允许 CPU 先继续执行，在后续时刻向出错线程报告：

```text
SIGSEGV
si_code = SEGV_MTEAERR
si_addr = 0
```

故障地址和触发指令通常无法精确恢复，一次报告也可能对应一个或多个先前的 tag mismatch。它适合低开销的生产检测，但发现问题后仍应在相同场景切到 SYNC 复现。

“一定在下一次系统调用报告”过于绝对。内核文档只保证异步语义，具体报告时机受架构与内核处理影响。

### ASYMM

ASYMM 对读使用同步检查，对写使用异步检查。AOSP 文档指出，它通常具有接近 ASYNC 的性能特征，同时能精确定位读错误。

应用接口不直接请求 ASYMM。Android 的 bionic 在请求 ASYNC 时，先把 `PR_MTE_TCF_ASYNC | PR_MTE_TCF_SYNC` 一并交给内核；新内核可结合当前 CPU 的首选模式选择 ASYNC、ASYMM 或 SYNC。若内核不接受多 mode bits，bionic 再回退到单独的 ASYNC 请求。

### 性能结论应来自目标设备

固定开销百分比无法覆盖不同 CPU 与工作负载。建议至少比较：

- 关键场景耗时与帧长尾；
- CPU time、指令数和 cache miss；
- RSS/PSS 及 Scudo 诊断元数据；
- native allocation rate；
- MTE crash 的数量和可归因比例。

对同一个 release build 分别运行 MTE off、ASYNC/实际首选模式、SYNC，才能评估产品设备的成本。硬件检查、Scudo tag 管理和 SYNC 栈记录都可能贡献开销。

## 内核 MTE 管理与 prctl 接口

### `PROT_MTE` 作用于映射

用户空间通过 `mmap()` 或 `mprotect()` 给映射加入 `PROT_MTE`。Linux 只允许 anonymous mapping 和基于 RAM 的文件映射，如 tmpfs、memfd；其他文件映射会返回 `EINVAL`。

有三个容易遗漏的约束：

- 新映射的 allocation tag 初始为 0。
- `PROT_MTE` 一旦加入，不能通过 `mprotect()` 清除。
- `MADV_DONTNEED` 或 `MADV_FREE` 之后，内核可以把相关 tag 清为 0。

`PROT_MTE` 只让映射具备 tag 存取能力。线程若处于 `PR_MTE_TCF_NONE`，tag mismatch 仍不会按 SYNC/ASYNC 方式报告。

### `prctl()` 控制当前线程

`PR_SET_TAGGED_ADDR_CTRL` 同时配置 tagged-address ABI、fault mode 和 `IRG` 可用 tag mask。下面的代码只用于确认当前线程是否选择了某种 MTE 检查模式：

```cpp
#include <sys/prctl.h>

bool running_with_mte() {
  int ctrl = prctl(PR_GET_TAGGED_ADDR_CTRL, 0, 0, 0, 0);
  return ctrl >= 0 && (ctrl & PR_MTE_TCF_MASK) != PR_MTE_TCF_NONE;
}
```

这个结果不能证明任意地址都映射了 `PROT_MTE`。它也只反映调用线程的配置；Linux 的 tag-check mode 是 per-thread 状态，线程创建和上下文切换由 libc、内核共同处理。

### CPU 首选模式

特权系统组件可通过以下 sysfs 节点设置每个 CPU 的首选检查模式：

```text
/sys/devices/system/cpu/cpu<N>/mte_tcf_preferred
```

可写值是 `async`、`asymm`、`sync`，默认首选值为 `async`。只有任务请求了多个可接受 mode bits 时，内核才有选择空间。单独请求 SYNC 的线程不会因 CPU 首选值而降到 ASYNC。

### `PSTATE.TCO` 只适合局部免检

`PSTATE.TCO=1` 会暂时关闭当前线程的 tag check。bionic 用 `ScopedDisableMTE` 保存旧值、写入 TCO，再在析构时恢复。它适合必须处理未知 tag 的底层代码，不适合用来掩盖业务崩溃。

signal handler 进入时，内核保证 `PSTATE.TCO=0`，`sigreturn()` 后再恢复被中断上下文的值。

## Bionic/Scudo MTE 集成路径

### Native executable 的初始化

动态可执行文件由 linker 调用 `__libc_init_mte()`；静态可执行文件从 libc 初始化路径进入同一函数。Android 17 的选择过程可概括为：

1. 从 ELF dynamic entries 读取 `DT_AARCH64_MEMTAG_MODE`、heap/stack/globals 标记；旧静态程序可回退读取 Android ELF note。
2. 用环境或属性配置覆盖 heap mode。
3. 调用 `PR_SET_TAGGED_ADDR_CTRL`。
4. 把初始 heap tagging level、stack ABI 状态写入 `__libc_shared_globals`。
5. Scudo 初始化时读取这些状态，决定是否给 heap allocation 使用 MTE。

覆盖来源的顺序由 `libc_init_mte.cpp` 固定：`MEMTAG_OPTIONS`、`arm64.memtag.process.<basename>`、远端 DeviceConfig process override、`persist.arm64.memtag.default`。它们是平台与调试配置，不应成为普通应用依赖的稳定 API。

### App 进程由 Zygote 决策

应用从 zygote fork，不能复用 native executable 的完整启动选择。`Zygote.getRequestedMemtagLevel()` 在 Android 17 tag 中按以下顺序取值：

1. `persist.arm64.memtag.app.<package>`；
2. `<process android:memtagMode>`；
3. `<application android:memtagMode>`；
4. `NATIVE_MEMTAG_SYNC` compat change；
5. `NATIVE_MEMTAG_ASYNC` compat change；
6. `persist.arm64.memtag.app_default`；
7. 旧的 TBI pointer-tagging compat 行为。

随后 `decideTaggingLevel()` 再按硬件能力降级，并在 userdebug/eng 且平台默认要求 SYNC 时把应用的 ASYNC 升为 SYNC。fork 后，native `SpecializeCommon()` 把 runtime flag 转成 `M_HEAP_TAGGING_LEVEL_*`，调用：

```cpp
mallopt(M_BIONIC_SET_HEAP_TAGGING_LEVEL, heap_tagging_level);
```

`ApplicationInfo` 内部常量在 Android 17 是 `DEFAULT=-1`、`OFF=0`、`ASYNC=1`、`SYNC=2`。这些整数是隐藏实现；应用只应使用 manifest 字符串。

### Scudo 如何参与

开启 heap MTE 后，Scudo 在 `malloc`/`free` 时管理 pointer tag 和 allocation tag，用于发现 heap buffer overflow/underflow 与 use-after-free。SYNC 配置还开启 allocation stack tracking；ASYNC 配置关闭这项全量栈记录，以降低诊断成本。

AOSP 暴露了两种分配 tag 倾向：

- `M_MEMTAG_TUNING_BUFFER_OVERFLOW`：让相邻 allocation 使用不同 tag，优先发现线性越界。
- `M_MEMTAG_TUNING_UAF`：独立随机 tag，平衡空间错误与 use-after-free 的概率。

即使选择 buffer-overflow 倾向，同一 16 字节 granule 内的越界仍无法由 MTE 识别。

### heap tagging level 的状态转换

`SetHeapTaggingLevel()` 允许 ASYNC 与 SYNC 反复切换。ASYNC/SYNC 降到 `NONE` 后，bionic 会关闭各线程 TCF、停止 stack MTE 并通知 Scudo 禁用 memory tagging。

从 `NONE` 重新开启 tagging 会失败，TBI 与 ASYNC/SYNC 之间也不能随意互换。原因在于进程中已经存在的 pointer、allocation 和 stack 状态无法安全恢复成统一 tagged 状态。应用应在进程启动时选好策略，把运行时切换主要用于 ASYNC 与 SYNC 之间的复现。

## Android 17 MTE 增进：栈与全局变量检测

这里的“Android 17”表示当前源码锚点能确认的实现，不表示所有能力都首次出现在 Android 17。Stack MTE 的官方应用支持从 Android 14 QPR3 开始；globals 的首次版本需要逐个历史 tag 核实，不能在缺少证据时推断首发版本。

### Heap、stack、globals 是三个保护面

只设置 `android:memtagMode` 会让普通系统 allocator 的 native heap 使用 MTE。stack 上的局部对象需要编译器插桩，globals 还需要编译器、LLD 与 Android linker 配合。

当前 NDK 文档给出的 CMake 配置如下：

```cmake
target_compile_options(
    ${TARGET} PUBLIC
    -fsanitize=memtag
    -fno-omit-frame-pointer
    -march=armv8-a+memtag)

target_link_options(
    ${TARGET} PUBLIC
    -fsanitize=memtag
    -fsanitize-memtag-mode=sync
    -march=armv8-a+memtag)
```

这类插桩构建只应在 MTE-capable 设备上运行，官方定位是调试用途。发布包若只希望检查 native heap，可以启用 manifest mode 而不把所有 native 目标编译成 memtag instrumentation。

### Stack MTE

LLVM 的 AArch64 stack-tagging pass 为符合条件的 stack object 设置生命周期 tag，并可记录 PC、frame pointer 和 base tag。Android 17 bionic 负责运行时支持：

- 主程序或依赖声明 `DT_AARCH64_MEMTAG_STACK` 时，在启动阶段准备 stack MTE。
- 后续 `dlopen()` 加载带 stack MTE 的库时，linker 通过 callback 要求 libc 处理现有线程栈。
- MTE 已启用时，把 stack remap 为 `PROT_MTE`。
- 每个线程为 stack history 准备 ring buffer；只要进程含 stack-tagged 代码，即使运行设备未开启 MTE，代码生成约定仍要求 TLS 中存在相应 buffer。

stack instrumentation 能发现跨 tag granule 的 stack overflow/underflow，并提高部分 use-after-return 的发现机会。编译器优化、对象布局、16 字节 granule 和 tag 碰撞仍会影响覆盖率。

### Globals MTE

Android 17 linker 识别：

```text
DT_AARCH64_MEMTAG_GLOBALS
DT_AARCH64_MEMTAG_GLOBALSSZ
```

只有 ELF 含 globals descriptor、大小非零且进程启用了 MTE 时，`should_tag_memtag_globals()` 才成立。linker 的处理包括：

1. 找到可写、不可执行的 `PT_LOAD` data segment。
2. 尝试直接加入 `PROT_MTE`；文件映射不支持时，复制到固定地址的 private anonymous mapping。
3. 解析 ULEB128 descriptor stream，为每个 global 范围写 allocation tag。
4. 对 symbol address 和相关 relocation 应用对应 logical tag。
5. 调用 segment 保护步骤，并为替换文件映射的匿名 VMA 命名以便诊断；当前 tagging 范围仍限于可写 data segment。

这种 remap 会失去原文件页共享，所以 linker 只在 ELF 明确请求 globals tagging 且设备支持 MTE 时执行。

### Android 17 的 MTE-aware libc ifunc

`android-17.0.0_r1` 的 arm64 `ifuncs.cpp` 为 `wcslen` 和 `wmemchr` 增加了基于 `HWCAP2_MTE` 的选择：

```cpp
DEFINE_IFUNC_FOR(wcslen) {
  if (arg->_hwcap2 & HWCAP2_MTE) {
    RETURN_FUNC(wcslen_func_t, portable_simd_wcslen_neon_mte);
  }
  RETURN_FUNC(wcslen_func_t, portable_simd_wcslen_neon);
}
```

`wmemchr` 使用相同判断选择 `_neon_mte` 版本。portable-simd 的 MTE 构建把 `kReadAheadToPageBoundaryIsOK` 设为 false，避免采用普通实现允许的向页边界预读。这个 ifunc 选择不会自动给调用者的内存开启 MTE。

## 应用启用、验证与排错

### Debug build 使用 SYNC

建议只在 debug manifest 中覆盖：

```xml
<manifest xmlns:android="http://schemas.android.com/apk/res/android"
    xmlns:tools="http://schemas.android.com/tools">
    <application
        android:memtagMode="sync"
        tools:replace="android:memtagMode" />
</manifest>
```

把文件放到 `app/src/debug/AndroidManifest.xml`，可以避免误把开发策略带到所有 build type。MTE-capable 设备上发生错误时，进程会生成带 `SEGV_MTESERR` 的 tombstone。

### 无需改包的兼容性测试

对 manifest 为 `default` 或未指定的应用，可以临时启用 compat change：

```bash
adb shell am compat enable NATIVE_MEMTAG_SYNC com.example.app
adb shell am force-stop com.example.app
```

ASYNC 对应 `NATIVE_MEMTAG_ASYNC`。配置影响下一次进程启动；测试完成后应恢复 compat change，避免后续样本混用不同模式。

### 读 tombstone

先看 signal code：

- `SEGV_MTESERR`：同步错误，fault address 和 PC 可用于定位访问。
- `SEGV_MTEAERR`：异步错误，fault address 通常为 0，当前 PC 往往只是报告位置。

SYNC 下继续看 `Cause: [MTE]`、allocation/deallocation stack、fault address 周围 tag。若是 stack instrumentation，再结合 unstripped symbols、frame pointer 和 stack history 还原局部对象。

常见排查顺序是：

1. 确认设备 `/proc/cpuinfo` 有 `mte`。
2. 确认应用进程重新启动后采用预期 mode。
3. 用 SYNC 复现 ASYNC 上报的场景。
4. 对照 allocation、deallocation 与 fault stack。
5. 检查自定义 allocator、JNI 指针算术、对象生命周期和跨线程移交。
6. 修复后用同一 workload 重跑，并保留 MTE 与 ASan/HWASan 的互补测试。

## Tag 存储的内存开销与 vMTE 展望

从架构信息量计算，每 16 字节数据需要 4 bit allocation tag，比例是：

```text
4 bit / (16 × 8 bit) = 1 / 32 = 3.125%
```

这个比例描述 tag metadata 容量。具体 SoC 如何存放 tag、是否预留连续物理区域、cache 如何携带 tag，属于硬件实现。Android 应用不能据此断言“32 GB 设备一定由 bootloader carve out 1 GB 且操作系统不可见”，也不能假设统一的 `Tag_PA = Base + (Data_PA >> 5)`。

Linux core dump 把两个 4-bit tag 压成一个字节，所以 tagged memory 对应的 tag segment 文件大小也是数据范围的 `1/32`。运行时内存占用还会受到 allocator 对齐、Scudo 元数据、SYNC allocation stacks、stack history 和 globals remap 失去页共享的影响。

“vMTE”常被用于描述让 tag storage 更灵活或虚拟化的后续方案。它不是 Android 17 SDK/NDK 或 `android17-6.18-2026-06_r6` 向应用提供的接口。评估 Android 17 产品时，应以设备 datasheet、内核 capability 和实测 PSS/RSS 为准，不把未来架构设想计入现有收益。

## MTE 安全攻击面与缓解

### MTE 提供概率检测，不提供 tag 保密承诺

攻击者若猜中 4-bit tag，或错误访问仍在同一 granule 中，MTE 可能不报告。AOSP 的 UAF tuning 使用独立随机 tag 时给出的均匀检测概率约为 93%，对应 15/16 的 tag mismatch 概率；相邻 tag 策略则优先保证常见线性越界跨 allocation 后得到不同 tag。

TIKTAG 等研究展示了利用推测执行与 cache side channel 推断 MTE tag 的可能性。该结果说明安全评估不能把 tag 当作密码学秘密。是否影响某台 Android 17 设备，仍取决于具体微架构、内核与缓解配置，不能仅凭 CPU 声称支持 FEAT_MTE4 就判定已免疫。

### 工程上的防护组合

MTE 适合与其他措施共同使用：

- 使用 Rust、Java、Kotlin 等内存安全语言缩小 unsafe C/C++ 范围。
- 开发和 CI 使用 HWASan/ASan 覆盖更丰富的错误模式。
- 量产高价值进程使用经过压测的 ASYNC 或 CPU 首选 ASYMM。
- 对抽样崩溃切换 SYNC，获取精确 fault 与 allocator history。
- 保持 CFI、FORTIFY、PAC/BTI、seccomp 和最小权限等防护。
- 审计自定义 allocator，保证 16 字节对齐、映射属性和 tag 更新都正确。

MTE 检测到错误时终止进程，仍可能带来可用性影响。生产启用前应测试故障恢复、崩溃采集、版本回滚和关键数据持久化，避免把内存安全提升转化为不可控的用户损失。

## 版本边界与结论

| Android 版本 | 相关能力 |
| --- | --- |
| Android 12 / API 31 | AOSP 平台与用户空间 allocator 开始系统性支持 MTE |
| Android 13 / API 33 | 部分商用设备开始提供可用 MTE 支持 |
| Android 14 QPR3 | NDK 文档确认 app stack tagging 可用 |
| Android 17 / API 37 | bionic/linker 已包含 heap、stack、globals 运行时支持及 MTE-aware `wcslen`/`wmemchr` ifunc |

Android 17 上的实用判断可以归纳为四点：先确认硬件和系统配置；开发阶段用 SYNC 获取精确报告；生产模式按目标 SoC 压测；把 heap、stack、globals 的覆盖范围分开验证。

> §20.10 继续讨论 MTE/GWP-ASan 在稳定性治理中的模式选择、崩溃归因和灰度策略。

## 参考资料

- [Android NDK：Arm Memory Tagging Extension](https://developer.android.com/ndk/guides/arm-mte)
- [AOSP：Arm Memory Tagging Extension](https://source.android.com/docs/security/test/memory-safety/arm-mte)
- [Linux kernel：Memory Tagging Extension in AArch64 Linux](https://docs.kernel.org/arch/arm64/memory-tagging-extension.html)
- [Arm：Memory Tagging Extension whitepaper](https://developer.arm.com/-/media/Arm%20Developer%20Community/PDF/Arm_Memory_Tagging_Extension_Whitepaper.pdf)
- [AOSP android-17.0.0_r1：bionic MTE implementation](https://android.googlesource.com/platform/bionic/+/refs/tags/android-17.0.0_r1/docs/mte.md)
- [AOSP android-17.0.0_r1：libc_init_mte.cpp](https://android.googlesource.com/platform/bionic/+/refs/tags/android-17.0.0_r1/libc/bionic/libc_init_mte.cpp)
- [AOSP android-17.0.0_r1：heap_tagging.cpp](https://android.googlesource.com/platform/bionic/+/refs/tags/android-17.0.0_r1/libc/bionic/heap_tagging.cpp)
- [AOSP android-17.0.0_r1：linker globals implementation](https://android.googlesource.com/platform/bionic/+/refs/tags/android-17.0.0_r1/linker/linker.cpp)
- [AOSP android-17.0.0_r1：Zygote MTE decision](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/com/android/internal/os/Zygote.java)
- [AOSP android-17.0.0_r1：arm64 ifuncs](https://android.googlesource.com/platform/bionic/+/refs/tags/android-17.0.0_r1/libc/arch-arm64/ifuncs.cpp)
- [Arm ABI：Memtag Extension to ELF for the Arm 64-bit Architecture](https://github.com/ARM-software/abi-aa/blob/main/memtagabielf64/memtagabielf64.rst)
- [TIKTAG research paper](https://arxiv.org/abs/2406.08719)
