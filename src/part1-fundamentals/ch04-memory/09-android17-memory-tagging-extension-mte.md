---
title: Android 17 ARM MTE 内存标签扩展实战
chapter: '4.9'
status: finalized
applicable_versions: Android 12 (API 31) - Android 17 (API 37)
last_verified: '2026-08-21'
last_verified_against: AOSP android-17.0.0_r1 / android17-6.18-2026-06_r6; bionic ifuncs.cpp MTE dispatch checked 2026-08-21
confidence: high
tags:
- Android 17
- MTE
- Memory Safety
- ARM
- Hardware Architecture
- Scudo
- Bionic
related_chapters:
- '20.11'
- '4.4'
- '14.3'
- '23.3'
task6_state: reviewed
task9_state: reviewed
pipeline_stage: ready-to-publish
last_deep_review_at: '2026-08-21T16:35:04+08:00'
last_deep_review_run_id: 20260821-163504-deep-review-4c57381a
sources:
- type: blog
  path: Cubox/四年之后，重新审视 MTE：从硬件架构到工程落地-2025-12-18.md
- type: blog
  path: Cubox/Android内存安全革命性改变：快手MTE探索与实践-2023-05-23.md
- type: aosp
  path: bionic/libc/bionic/libc_init_common.cpp
- type: aosp
  path: bionic/libc/platform/bionic/mte.h
- type: aosp
  path: frameworks/base/core/java/android/content/pm/ApplicationInfo.java
- type: aosp
  path: frameworks/base/core/java/com/android/internal/os/Zygote.java
- type: aosp
  path: bionic/libc/arch-arm64/ifuncs.cpp
- type: official
  path: https://source.android.com/docs/security/test/memory-safety/arm-mte
- type: official
  path: https://developer.android.com/ndk/guides/arm-mte
- type: research
  path: DeepResearch/2026-05-26-android-mte-asymm-auto-enablement-mechanism.md
---

# Android 17 ARM MTE 内存标签扩展实战

内存标签扩展（Memory Tagging Extension，MTE）通过比较指针标签与内存标签，检测一部分原生内存错误。平台源码以 AOSP `android-17.0.0_r1` 为基准，内核以 `android17-6.18-2026-06_r6` 为基准。讨论范围包括应用的原生堆（native heap）、线程栈（stack）和全局变量（globals），以及 Android 如何把 manifest 配置传给 Bionic C 库与 Scudo 内存分配器。

MTE 只能检查使用标签内存（tagged memory）的原生内存访问。Java/Kotlin 对象仍由 ART 管理；32 位进程、未启用 MTE 的映射，以及没有正确设置标签的自定义分配器，都不在同一保护范围内。

## MTE 硬件能力：从 FEAT_MTE 到 FEAT_MTE4

### 逻辑标签与分配标签的比较

MTE 为每个 16 字节的标签分配粒度（allocation granule）保存一个 4 位分配标签（allocation tag），并把指针虚拟地址的位段 `bits[59:56]` 作为逻辑标签（logical tag）。CPU 访问普通标签内存（Normal Tagged Memory）时会比较两者：

```text
指针：0x0A00_7f12_3456_7800
          ^^
          logical tag = 0xA

内存：[0x...7800, 0x...780f]  allocation tag = 0xA
```

两者相同，访问可以继续；两者不同，处理方式由当前线程的标签检查故障模式（tag-check fault mode）决定。一个标签粒度是 16 字节。只有在把两个 4 位标签紧凑存入一个字节时，才会得到“一个字节标签对应 32 字节数据”的换算关系。

MTE 常用于发现两类原生内存错误：

- **空间错误**：指针越过分配边界，访问到标签不同的相邻粒度。
- **时间错误**：内存释放并重新分配后换了标签，旧指针继续访问时发生不匹配。

4 位标签只有 16 种取值，因此检测带有概率性。越界访问仍落在同一 16 字节粒度内时，也没有标签边界可以触发检查。MTE 是原生内存安全检测与缓解手段，不能证明程序不存在内存错误。

### FEAT_MTE、MTE2、MTE3、MTE4 与 Android 的关系

Arm 架构用 FEAT_MTE 到 FEAT_MTE4 表示逐步扩展的硬件能力。Android 工程中最需要区分的边界有两个：

- Armv8.5-A 引入 MTE 的标签指令、标签内存和检查机制。
- Armv8.7-A 的 FEAT_MTE3 加入非对称模式（asymmetric mode）：读取错误同步报告，写入错误异步报告。

FEAT_MTE4 属于后续 CPU 架构能力集合，不能把它理解成 Android 的第四种 `memtagMode`。截至 Android 17 / API 37，应用 manifest 仍只接受 `off`、`default`、`sync` 和 `async`。在支持的 CPU 上，系统可以按首选模式把 ASYNC 请求运行成 ASYMM，但应用 manifest 没有 `asymm` 或 `mte4` 这两个值。

判断设备能力时应直接查询运行设备，不能只根据 Android 版本或 SoC 宣传名称反推。下面的命令检查内核公布的 CPU 特性：

```bash
adb shell grep -w mte /proc/cpuinfo
```

输出中出现 `mte`，表示内核向用户空间公布了相应的 CPU 能力。部分设备还要求通过开发者选项，重启到支持 MTE 的系统配置；如果设备没有该选项，应用也无法自行补齐硬件或内核支持。

## 标签生成与硬件检测机制

### 逻辑标签、分配标签与 TBI

AArch64 的高字节忽略（Top Byte Ignore，TBI）允许地址翻译忽略虚拟地址高字节中的一部分信息。MTE 使用位段 `bits[59:56]` 携带逻辑标签，内存侧则为每个 16 字节粒度保存分配标签。

常用指令可以按职责分为以下几类：

| 指令 | 用途 |
| --- | --- |
| `IRG` | 从允许集合中生成逻辑标签，并写入指针 |
| `STG` / `ST2G` | 为一个或两个 16 字节粒度写入分配标签 |
| `STZG` / `STZ2G` | 写入标签，同时把对应数据清零 |
| `LDG` | 读取地址对应的分配标签 |

`IRG` 只改变指针标签，不会写入内存标签；`STG` 才会更新内存的分配标签。自定义分配器若只完成其中一步，合法访问也会发生标签不匹配（tag mismatch）。

Android 17 的 `bionic/libc/platform/bionic/mte.h` 定义：

```cpp
#define PR_MTE_TAG_SET_NONZERO (0xfffeUL << PR_MTE_TAG_SHIFT)
```

Bionic 初始化 MTE 时，会把这个位掩码（mask）交给 `prctl()`。非零标签可用于普通分配，标签 0 留给 Scudo 分配块头（chunk header），从而帮助捕获线性越界对分配器元数据的破坏。这是 Android Scudo 的实现约定，不是所有 MTE 分配器都必须遵循的架构规则。

### 一次访问满足哪些条件才会检查

用户态内存读取/写入指令（load/store）要接受 MTE 检查，需要同时满足以下条件：

1. CPU 与内核公布 MTE 能力。
2. 地址所在映射以 `PROT_MTE` 建立，属于 Normal Tagged Memory。
3. 当前线程通过 `PR_SET_TAGGED_ADDR_CTRL` 选择了检查模式。
4. 当前执行上下文没有通过 `PSTATE.TCO` 临时关闭检查。

CPU 随后比较逻辑标签与分配标签。架构只定义外部可观察的异常语义，并不规定每款 CPU 必须采用相同的 TLB（地址转换缓存）、高速缓存、ROB（乱序执行的重排序缓冲区）或写缓冲区（store buffer）实现。因此，不能用一套推测的流水线时序解释所有 Arm CPU 的开销。

## 三种检测模式的 CPU 流水线级分析

### SYNC：同步报告

同步模式会在发生标签不匹配的那条读取/写入指令上报告错误。Linux 发送以下信号信息：

```text
SIGSEGV
si_code = SEGV_MTESERR
si_addr = fault address
```

该次访问不会完成。Android 原生崩溃报告 tombstone 可以给出出错的程序计数器（PC）和地址。进程配置为 SYNC 时，Android 还会让 Scudo 记录内存分配与释放调用栈（allocation/deallocation stack），以补充释放后使用（use-after-free）或缓冲区溢出的上下文。

SYNC 更适合开发、测试和需要准确归因的高价值进程。它的成本会随 CPU、分配模式、内存访问和 Scudo 调用栈记录而变化，不能把 3%～30% 当作通用范围。

### ASYNC：异步报告

异步模式允许 CPU 先继续执行，在之后某个时刻向出错线程报告：

```text
SIGSEGV
si_code = SEGV_MTEAERR
si_addr = 0
```

故障地址和触发指令通常无法准确恢复，一次报告也可能对应先前的一次或多次标签不匹配。它适合开销较低的生产环境检测，但发现问题后仍应在相同场景切换到 SYNC 复现。

“一定在下一次系统调用报告”过于绝对。内核文档只保证异步语义，具体报告时机受架构与内核处理影响。

### ASYMM：读同步、写异步

ASYMM 对读取使用同步检查，对写入使用异步检查。AOSP 文档指出，它通常具有接近 ASYNC 的性能特征，同时可以准确定位读取错误。

应用接口不能直接请求 ASYMM。Android 的 Bionic 在请求 ASYNC 时，先把 `PR_MTE_TCF_ASYNC | PR_MTE_TCF_SYNC` 两个可接受模式位一并交给内核；新内核可以结合当前 CPU 的首选模式选择 ASYNC、ASYMM 或 SYNC。若内核不接受多个模式位，Bionic 再回退到单独请求 ASYNC。

### 性能结论应来自目标设备

固定的开销百分比无法代表不同 CPU 与工作负载。建议至少比较：

- 关键场景耗时与帧耗时长尾；
- CPU 时间、指令数和高速缓存未命中次数；
- RSS（驻留集大小）/PSS（按比例分摊共享页后的内存）及 Scudo 诊断元数据；
- 原生内存分配速率；
- MTE 崩溃数量和能够准确归因的比例。

对同一个发布构建（release build）分别运行 MTE OFF、ASYNC/实际首选模式和 SYNC，才能评估产品设备上的真实成本。硬件检查、Scudo 标签管理和 SYNC 调用栈记录都可能产生开销。

## 内核 MTE 管理与 prctl 接口

### `PROT_MTE` 作用于映射

用户空间通过 `mmap()` 或 `mprotect()` 为映射加入 `PROT_MTE`。Linux 只允许匿名映射和基于内存的文件映射，例如 tmpfs、memfd；其他文件映射会返回 `EINVAL`。

有三个容易遗漏的约束：

- 新映射的分配标签初始为 0。
- `PROT_MTE` 一旦加入，不能通过 `mprotect()` 清除。
- 执行 `MADV_DONTNEED` 或 `MADV_FREE` 后，内核可以把相关标签清为 0。

`PROT_MTE` 只让映射具备标签存取能力。线程若处于 `PR_MTE_TCF_NONE`，标签不匹配仍不会按 SYNC 或 ASYNC 方式报告。

### `prctl()` 控制当前线程

`prctl()` 是 Linux 的进程控制系统调用。这里使用的 `PR_SET_TAGGED_ADDR_CTRL` 会同时配置带标签地址 ABI（应用二进制接口约定）、故障报告模式，以及 `IRG` 可用的标签位掩码。下面的代码只用于确认当前线程是否选择了某种 MTE 检查模式：

```cpp
#include <sys/prctl.h>

bool running_with_mte() {
  int ctrl = prctl(PR_GET_TAGGED_ADDR_CTRL, 0, 0, 0, 0);
  return ctrl >= 0 && (ctrl & PR_MTE_TCF_MASK) != PR_MTE_TCF_NONE;
}
```

这个结果不能证明任意地址都映射了 `PROT_MTE`。它也只反映调用线程的配置；Linux 的标签检查模式是线程私有（per-thread）状态，线程创建和上下文切换由 libc 与内核共同处理。

### CPU 首选模式

特权系统组件可以通过下面的 sysfs 内核属性节点，为每个 CPU 设置首选检查模式：

```text
/sys/devices/system/cpu/cpu<N>/mte_tcf_preferred
```

可写值是 `async`、`asymm`、`sync`，默认首选值为 `async`。只有任务请求了多个可接受的模式位时，内核才有选择空间。单独请求 SYNC 的线程，不会因为 CPU 的首选值而降为 ASYNC。

### `PSTATE.TCO` 只适合局部免检

`PSTATE.TCO=1` 会暂时关闭当前线程的标签检查。Bionic 使用 `ScopedDisableMTE` 保存旧值、写入 TCO，再在析构时恢复。它适合必须处理未知标签的底层代码，不适合用来掩盖业务崩溃。

进入信号处理函数（signal handler）时，内核保证 `PSTATE.TCO=0`；`sigreturn()` 返回后，再恢复被中断上下文中的原值。

## Bionic/Scudo MTE 集成路径

### 原生可执行文件的初始化

动态可执行文件由链接器（linker）调用 `__libc_init_mte()`；静态可执行文件则从 libc 初始化路径进入同一函数。Android 17 的选择过程可以概括为：

1. 从 ELF 动态表项读取 `DT_AARCH64_MEMTAG_MODE` 以及堆、栈、全局变量标记；旧静态程序可以回退读取 Android ELF note 段。
2. 用环境变量或系统属性覆盖堆模式。
3. 调用 `PR_SET_TAGGED_ADDR_CTRL`。
4. 把初始堆标签级别、栈 ABI 状态写入 `__libc_shared_globals`。
5. Scudo 初始化时读取这些状态，决定是否为堆分配启用 MTE。

覆盖来源的顺序由 `libc_init_mte.cpp` 固定：`MEMTAG_OPTIONS`、`arm64.memtag.process.<basename>`、DeviceConfig 中的进程覆盖值，以及 `persist.arm64.memtag.default`。这些都是平台或调试配置，不是供普通应用依赖的稳定 API。

### 应用进程由 Zygote 决策

应用进程由 Zygote 派生（fork），不能复用原生可执行文件的完整启动选择流程。`Zygote.getRequestedMemtagLevel()` 在 `android-17.0.0_r1` 中按以下顺序取值：

1. `persist.arm64.memtag.app.<package>`；
2. `<process android:memtagMode>`；
3. `<application android:memtagMode>`；
4. `NATIVE_MEMTAG_SYNC` 兼容性变更开关（compat change）；
5. `NATIVE_MEMTAG_ASYNC` 兼容性变更开关；
6. `persist.arm64.memtag.app_default`；
7. 旧版 TBI 指针标签兼容行为。

随后，`decideTaggingLevel()` 会按硬件能力降级；在 userdebug/eng 调试系统且平台默认要求 SYNC 时，它还会把应用的 ASYNC 升为 SYNC。进程派生后，原生函数 `SpecializeCommon()` 把运行时标志转换成 `M_HEAP_TAGGING_LEVEL_*`，再调用：

```cpp
mallopt(M_BIONIC_SET_HEAP_TAGGING_LEVEL, heap_tagging_level);
```

这次 `mallopt()` 调用把 Zygote 选出的堆标签级别交给 Bionic 内存分配器。

`ApplicationInfo` 的内部常量在 Android 17 中是 `DEFAULT=-1`、`OFF=0`、`ASYNC=1`、`SYNC=2`。这些整数属于隐藏实现；应用只应使用 manifest 字符串。

### Scudo 如何参与

开启堆 MTE 后，Scudo 会在 `malloc`/`free` 时管理指针标签和分配标签，用于发现堆缓冲区上溢/下溢，以及释放后使用。SYNC 配置还会开启内存分配调用栈跟踪；ASYNC 配置关闭这项全量调用栈记录，以降低诊断成本。

AOSP 暴露了两种分配标签策略：

- `M_MEMTAG_TUNING_BUFFER_OVERFLOW`：让相邻内存块使用不同标签，优先发现线性越界。
- `M_MEMTAG_TUNING_UAF`：独立生成随机标签，在空间错误与释放后使用之间平衡检测概率。

即使选择偏重缓冲区溢出的策略，同一 16 字节粒度内的越界仍无法由 MTE 识别。

### 堆标签级别的状态转换

`SetHeapTaggingLevel()` 允许 ASYNC 与 SYNC 反复切换。ASYNC/SYNC 降到 `NONE` 后，Bionic 会关闭各线程的标签检查模式（TCF）、停止栈 MTE，并通知 Scudo 禁用内存标签。

从 `NONE` 重新开启标签会失败，TBI 与 ASYNC/SYNC 之间也不能随意互换。原因是进程中现有的指针、内存块和栈状态，无法安全恢复为统一的带标签状态。应用应在进程启动时选好策略，把运行时切换主要用于在 ASYNC 与 SYNC 之间复现问题。

## Android 17 MTE 扩展：栈与全局变量检测

这里的“Android 17”表示当前源码锚点可以确认这些实现，不表示所有能力都首次出现在 Android 17。官方从 Android 14 QPR3 开始支持应用使用栈 MTE；全局变量 MTE 的首次版本仍需逐个核对历史源码标签，缺少证据时不能推断首发版本。

### 堆、栈和全局变量是三个保护范围

只设置 `android:memtagMode`，会让普通系统分配器管理的原生堆使用 MTE。栈上的局部对象还需要编译器插桩；全局变量则需要编译器、LLD 链接器与 Android 动态链接器共同配合。

当前 NDK 文档给出的 CMake 编译与链接配置如下：

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

这类插桩构建只应在支持 MTE 的设备上运行，官方将其定位为调试用途。如果发布包只希望检查原生堆，可以启用 manifest 模式，无需把所有原生目标都编译为 memtag 插桩版本。

### 栈 MTE

LLVM 的 AArch64 栈标签编译阶段（stack-tagging pass）会为符合条件的栈对象设置生命周期标签，并可记录程序计数器、帧指针（frame pointer）和基础标签。Android 17 的 Bionic 负责运行时支持：

- 主程序或依赖声明 `DT_AARCH64_MEMTAG_STACK` 时，在启动阶段准备栈 MTE。
- 后续 `dlopen()` 加载带栈 MTE 的库时，链接器通过回调要求 libc 处理现有线程栈。
- MTE 已启用时，把线程栈重新映射为 `PROT_MTE`。
- 每个线程都为栈历史准备环形缓冲区（ring buffer）；只要进程包含带栈标签的代码，即使运行设备没有开启 MTE，代码生成约定仍要求线程局部存储（TLS）中存在相应缓冲区。

栈插桩可以发现跨标签粒度的栈上溢/下溢，并提高发现部分函数返回后使用（use-after-return）问题的机会。编译器优化、对象布局、16 字节粒度和标签碰撞仍会影响覆盖率。

### 全局变量 MTE

Android 17 的链接器识别以下两个动态表项：

```text
DT_AARCH64_MEMTAG_GLOBALS
DT_AARCH64_MEMTAG_GLOBALSSZ
```

只有 ELF 包含全局变量描述符、描述范围大小非零，并且进程启用了 MTE 时，`should_tag_memtag_globals()` 才成立。链接器会执行以下处理：

1. 找到可写、不可执行的 `PT_LOAD` 数据段。
2. 尝试直接加入 `PROT_MTE`；文件映射不支持时，把内容复制到固定地址的私有匿名映射。
3. 解析采用 ULEB128 变长整数编码的描述符流，为每个全局变量范围写入分配标签。
4. 对符号地址和相关重定位项应用对应的逻辑标签。
5. 执行数据段保护步骤，并为替换文件映射的匿名虚拟内存区（VMA）命名，以便诊断；当前标签范围仍限于可写数据段。

这种重新映射会失去原有的文件页共享，因此，只有在 ELF 明确请求全局变量标签且设备支持 MTE 时，链接器才会执行。

### Android 17 中支持 MTE 的 libc ifunc

ifunc（indirect function，间接函数）允许 libc 根据运行时硬件能力选择具体实现。`android-17.0.0_r1` 的 arm64 `ifuncs.cpp` 中，下面这些函数会检查 `HWCAP2_MTE` 并在支持时选择 MTE 分支：

| libc 函数 | MTE 分支 |
| --- | --- |
| `memchr` | `__memchr_aarch64_mte` |
| `strchr` | `__strchr_aarch64_mte` |
| `strchrnul` | `__strchrnul_aarch64_mte` |
| `strlen` | `__strlen_aarch64_mte` |
| `strrchr` | `__strrchr_aarch64_mte` |
| `wcslen` | `portable_simd_wcslen_neon_mte` |
| `wmemchr` | `portable_simd_wmemchr_neon_mte` |

宽字符路径使用 portable-simd 的 `_neon_mte` 版本；对应 MTE 构建会把 `kReadAheadToPageBoundaryIsOK` 设为 `false`，避免采用普通实现所允许的页边界预读。这个 ifunc 选择只改变 libc 内部扫描实现，不会自动为调用者的内存开启 MTE；调用者仍要满足映射、线程模式和标签设置条件。

## 应用启用、验证与排错

### 调试构建使用 SYNC

建议只在调试版 manifest 中加入以下覆盖配置：

```xml
<manifest xmlns:android="http://schemas.android.com/apk/res/android"
    xmlns:tools="http://schemas.android.com/tools">
    <application
        android:memtagMode="sync"
        tools:replace="android:memtagMode" />
</manifest>
```

把文件放到 `app/src/debug/AndroidManifest.xml`，可以避免误把开发策略带到所有构建类型（build type）。在支持 MTE 的设备上发生错误时，进程会生成带有 `SEGV_MTESERR` 的 tombstone 崩溃报告。

### 无需改包的兼容性验证

对于 manifest 为 `default` 或未指定该属性的应用，可以临时启用兼容性变更开关：

```bash
adb shell am compat enable NATIVE_MEMTAG_SYNC com.example.app
adb shell am force-stop com.example.app
```

ASYNC 对应 `NATIVE_MEMTAG_ASYNC`。配置会在下一次进程启动时生效；测试完成后应恢复兼容性变更开关，避免后续样本混用不同模式。

### 读取 tombstone

先查看信号代码（signal code）：

- `SEGV_MTESERR`：同步错误，故障地址（fault address）和 PC 可用于定位出错访问。
- `SEGV_MTEAERR`：异步错误，故障地址通常为 0，当前 PC 往往只是报告错误的位置。

在 SYNC 模式下，还要查看 `Cause: [MTE]`、内存分配/释放调用栈，以及故障地址周围的标签。若使用了栈插桩，再结合未剥离调试符号（unstripped symbols）、帧指针和栈历史还原局部对象。

常见排查顺序是：

1. 确认设备 `/proc/cpuinfo` 有 `mte`。
2. 确认应用进程重新启动后采用预期模式。
3. 用 SYNC 复现 ASYNC 上报的场景。
4. 对照内存分配、释放与故障调用栈。
5. 检查自定义分配器、JNI 指针算术、对象生命周期和跨线程移交。
6. 修复后用同一工作负载重新测试，并保留 MTE 与内存错误检测工具 ASan/HWASan 的互补测试。

## 标签存储的内存开销与 vMTE 展望

从架构信息量计算，每 16 字节数据需要 4 位分配标签，比例为：

```text
4 bit / (16 × 8 bit) = 1 / 32 = 3.125%
```

这个比例只描述标签元数据的容量。具体 SoC 如何存放标签、是否预留连续物理区域，以及高速缓存如何携带标签，都属于硬件实现。Android 应用不能据此断言“32 GB 设备一定由引导加载程序预留 1 GB，且操作系统不可见”，也不能假设所有设备都采用 `Tag_PA = Base + (Data_PA >> 5)` 这一地址关系。

Linux 核心转储（core dump）会把两个 4 位标签压成一个字节，所以标签内存对应的标签段文件大小也是数据范围的 `1/32`。运行时内存占用还会受到分配器对齐、Scudo 元数据、SYNC 内存分配调用栈、栈历史，以及全局变量重新映射后失去文件页共享等因素影响。

“vMTE”常被用于描述让标签存储更灵活或虚拟化的后续方案。它不是 Android 17 SDK/NDK 或 `android17-6.18-2026-06_r6` 向应用提供的接口。评估 Android 17 产品时，应以设备规格书、内核公布的能力和实测 PSS/RSS 为准，不能把未来架构设想计入当前收益。

## MTE 安全攻击面与缓解

### MTE 提供概率检测，不承诺标签保密

攻击者若猜中 4 位标签，或错误访问仍落在同一标签粒度内，MTE 就可能不报告。AOSP 的释放后使用调优策略采用独立随机标签时，给出的均匀检测概率约为 93%，对应 `15/16` 的标签不匹配概率；相邻标签策略则优先让常见线性越界跨过内存块后遇到不同标签。

TIKTAG 等研究展示了利用推测执行与高速缓存侧信道（cache side channel）推断 MTE 标签的可能性。安全评估不能把标签当作密码学秘密。某台 Android 17 设备是否受影响，仍取决于具体微架构、内核与缓解配置；仅凭 CPU 声称支持 FEAT_MTE4，无法判定设备已经免疫。

### 工程上的防护组合

MTE 适合与其他措施共同使用：

- 使用 Rust、Java、Kotlin 等内存安全语言，缩小不安全 C/C++ 代码的范围。
- 在开发和持续集成（CI）阶段使用 HWASan/ASan，覆盖更丰富的错误模式。
- 在量产环境中，对安全价值较高的进程使用经过压测的 ASYNC 或 CPU 首选 ASYMM。
- 对抽样崩溃切换到 SYNC，获取准确的故障位置与分配器历史。
- 保持 CFI（控制流完整性）、FORTIFY（常见 libc 边界检查）、PAC/BTI（指针认证与分支目标保护）、seccomp（系统调用过滤）和最小权限等防护。
- 审计自定义分配器，保证 16 字节对齐、映射属性和标签更新都正确。

MTE 检测到错误时会终止进程，因此仍可能影响可用性。生产环境启用前，应测试故障恢复、崩溃采集、版本回滚和关键数据持久化，避免把内存安全收益变成不可控的用户损失。

## 版本边界与结论

| Android 版本 | 相关能力 |
| --- | --- |
| Android 12 / API 31 | AOSP 平台与用户空间内存分配器开始系统性支持 MTE |
| Android 13 / API 33 | 部分商用设备开始提供可用 MTE 支持 |
| Android 14 QPR3 | NDK 文档确认应用栈标签可用 |
| Android 17 / API 37 | Bionic/链接器已包含堆、栈、全局变量运行时支持，以及支持 MTE 的 `wcslen`/`wmemchr` ifunc |

Android 17 上的实用判断可以归纳为四点：先确认硬件和系统配置；开发阶段用 SYNC 获取准确报告；生产模式按目标 SoC 压测；分别验证堆、栈和全局变量的覆盖范围。

> §20.11 继续讨论 MTE 与抽样式堆内存错误检测器 GWP-ASan 的模式选择、崩溃归因和分阶段启用策略。

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
