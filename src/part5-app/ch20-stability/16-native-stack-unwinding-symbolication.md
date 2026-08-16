---
title: "Native 堆栈回溯与符号化机制"
chapter: "20.16"
section: "20.16"
status: finalized
applicable_versions: "Android 10 (API 29) - Android 17 (API 37)"
last_verified: "2026-08-14"
last_verified_against: "AOSP android-17.0.0_r1 debuggerd, libunwindstack, and Bionic; current Android NDK, ApplicationExitInfo, and native-symbol documentation"
confidence: high
sources:
  - type: aosp
    path: "https://android.googlesource.com/platform/system/core/+/refs/tags/android-17.0.0_r1/debuggerd/crash_dump.cpp"
  - type: aosp
    path: "https://android.googlesource.com/platform/system/core/+/refs/tags/android-17.0.0_r1/debuggerd/handler/debuggerd_handler.cpp"
  - type: aosp
    path: "https://android.googlesource.com/platform/system/core/+/refs/tags/android-17.0.0_r1/debuggerd/libdebuggerd/tombstone.cpp"
  - type: aosp
    path: "https://android.googlesource.com/platform/system/core/+/refs/tags/android-17.0.0_r1/debuggerd/libdebuggerd/tombstone_proto.cpp"
  - type: aosp
    path: "https://android.googlesource.com/platform/system/unwinding/+/refs/tags/android-17.0.0_r1/libunwindstack/AndroidUnwinder.cpp"
  - type: aosp
    path: "https://android.googlesource.com/platform/system/unwinding/+/refs/tags/android-17.0.0_r1/libunwindstack/Unwinder.cpp"
  - type: aosp
    path: "https://android.googlesource.com/platform/system/unwinding/+/refs/tags/android-17.0.0_r1/libunwindstack/Elf.cpp"
  - type: aosp
    path: "https://android.googlesource.com/platform/system/unwinding/+/refs/tags/android-17.0.0_r1/libunwindstack/ElfInterface.cpp"
  - type: aosp
    path: "https://android.googlesource.com/platform/system/unwinding/+/refs/tags/android-17.0.0_r1/libunwindstack/RegsArm64.cpp"
  - type: aosp
    path: "https://android.googlesource.com/platform/system/unwinding/+/refs/tags/android-17.0.0_r1/libunwindstack/AndroidVersions.md"
  - type: aosp
    path: "https://android.googlesource.com/platform/bionic/+/refs/tags/android-17.0.0_r1/libc/platform/bionic/android_unsafe_frame_pointer_chase.h"
  - type: official
    path: "https://developer.android.com/ndk/guides/ndk-stack"
  - type: official
    path: "https://developer.android.com/ndk/guides/debug"
  - type: official
    path: "https://developer.android.com/reference/android/app/ApplicationExitInfo"
  - type: official
    path: "https://developer.android.com/ndk/guides/gwp-asan"
  - type: official
    path: "https://developer.android.com/build/include-native-symbols"
  - type: official
    path: "https://source.android.com/docs/core/tests/debug/native-crash"
tags: [native, crash, stack-unwinding, symbolication, ndk, elf, tombstone, cfi]
related_chapters: ["20.3", "20.10", "20.11", "14.2", "14.26"]
---

# Native 堆栈回溯与符号化机制

Native 崩溃指 C/C++、Rust 等 native 代码导致的进程崩溃。报告中的 `#00 pc 0000000000008a3c libfoo.so` 包含第 0 帧、程序计数器（PC，指向当前或返回位置的指令地址）和模块名。这里的 `pc` 通常已经不是进程中的绝对地址：系统回溯器先找到该地址所属的内存映射，再换算成 ELF 内的相对地址。

ELF（Executable and Linkable Format，可执行与可链接格式）是 Android native 可执行文件和 `.so` 的文件格式。离线工具还要找到 Build ID 完全一致、未剥离调试信息的 ELF，才可能恢复函数、内联调用链和源码行。Build ID 是链接器写入 ELF 的构建指纹，用来区分文件名和版本号相同、实际字节却不同的二进制。

取得地址只完成了分析链的一小段。可复核的 Native 诊断系统至少包含五步：

1. **采集**：保存信号、`siginfo_t`（信号编号、原因码和故障地址等信息）、寄存器、线程栈和内存映射。
2. **回溯**：按 DWARF CFI、ARM EHABI（32 位 ARM 的异常处理 ABI）或其他可用信息恢复调用者寄存器。
3. **地址归一化**：把运行时 PC 换算成对应 ELF 可以识别的地址。
4. **符号化**：用匹配的调试符号把地址还原成函数、文件、行号和内联帧。
5. **质量判定**：识别错符号、截断栈和缺失帧，不能把“工具输出了一串函数名”当成正确答案。

本文以 Android 17 / API 37 / `android-17.0.0_r1` 为平台源码依据，说明这五步如何衔接，以及每一步能证明什么。

## 1. 两个 CFI 表示不同概念

Native 诊断里经常出现两个缩写相同、含义无关的术语：

| 缩写 | 全称 | 解决的问题 |
|---|---|---|
| CFI | Call Frame Information，调用帧信息 | 描述给定 PC 处如何恢复调用者的 SP（Stack Pointer，栈指针）、PC 和其他寄存器，用于异常处理与栈回溯 |
| CFI | Control Flow Integrity，控制流完整性 | 检查间接调用或跳转的目标是否合法，用于控制流安全加固 |

本文没有特别说明时，CFI 均指 Call Frame Information。Control Flow Integrity 违规后的表现取决于编译参数、运行库和触发陷阱的方式，不能统一写成某个固定信号，也不能拿它解释普通的回溯失败。

## 2. Android 17 如何生成系统 tombstone

### 2.1 崩溃线程提交现场，`crash_dump` 完成采集

Bionic 是 Android 的 C 标准库、数学库和动态链接器。它的 debuggerd 信号处理代码接收 `siginfo_t` 和 `ucontext_t`；后者包含信号发生时的寄存器上下文。处理代码通过 pipe（进程间字节管道）把现场交给 `crash_dump`。

`crash_dump` 通过 Linux ptrace 接口的 `PTRACE_SEIZE` / `PTRACE_INTERRUPT` 暂停目标线程，并读取寄存器和线程信息。随后，崩溃进程经两次 `clone()` 留下一个写时复制的地址空间副本；`crash_dump` 继续暂停并读取这个孤儿进程，让原进程可以退出。这里的“快照”是这一固定版本的实现路径，不是应用可调用的公开 VM 快照 API。

Android 17 源码中的关键对象是：

- `crash_dump.cpp`：停止线程、读取崩溃现场、建立地址空间副本并连接 `tombstoned`。`tombstoned` 是接收和保存系统崩溃报告的守护进程。
- `AndroidRemoteUnwinder`：解析快照进程的 maps（内存映射表），并通过 `libunwindstack` 回溯。
- `engrave_tombstone()`：构建 protobuf tombstone，再生成文本表示。protobuf 是按预定义字段结构编码的二进制格式。

这段流程可以简化为：

```text
fatal signal
  -> bionic debuggerd handler 保存 siginfo/ucontext
  -> crash_dump ptrace 停止各线程并读取寄存器
  -> VM snapshot 保留待分析的地址空间
  -> AndroidRemoteUnwinder / libunwindstack 回溯
  -> tombstoned 接收文本与 protobuf tombstone
  -> ActivityManager 获得崩溃摘要
```

tombstone 是 Android 为 native 崩溃生成的结构化诊断记录。上面的流程解释了两个常见现象：系统 tombstone 可以包含多个线程，而应用自己的信号处理器通常只直接掌握当前线程；系统回溯器还能读取目标地址空间和 ART 的 JIT/Dex 信息，一个简单的 `_Unwind_Backtrace()` 调用不具备同等能力。

### 2.2 当前主回溯器是 `libunwindstack`

`crash_dump.cpp` 在 `android-17.0.0_r1` 中直接包含 `unwindstack/AndroidUnwinder.h`，并以快照进程 PID 创建 `AndroidRemoteUnwinder`。旧的 `libunwind`、`libbacktrace` 路径不再代表当前 debuggerd 实现。

`libunwindstack` 从 Android 9 / API 28 起进入平台。版本说明记录了这些 Android 相关能力：

- 读取 DWARF 回溯信息；早期版本支持到 DWARF 4，后续逐步兼容部分 DWARF 5 数据。
- 读取 32 位 ARM 的 `.ARM.exidx` 回溯索引。
- 通过 gdb JIT 接口识别 ART 即时编译（JIT）生成的代码。
- 识别 ART 解释器用特殊 CFI 标记暴露的 Dex PC 虚拟帧。Dex PC 是 Android 字节码方法内的位置。
- 在 Android 10—12 间多次修正 load bias、分段 ELF 和 APK 内嵌 ELF 偏移处理。
- 从 Android 15 / API 35 起读取用 zlib 或 zstd 压缩的 `.debug_frame`。

这些只是回溯器具备的能力。目标 ELF、栈内存、寄存器和映射只要缺少一项，调用链仍可能中断。

## 3. 回溯器怎样恢复上一帧

### 3.1 DWARF Call Frame Information

DWARF 是编译器和调试工具共用的一组调试数据格式。编译器通常把调用帧恢复规则写入运行时使用的 `.eh_frame`，也可能写入包含更完整调试信息的 `.debug_frame`。规则会针对给定 PC 描述以下信息：

- 当前 PC 属于哪个 FDE（Frame Description Entry，描述一段指令地址范围的帧规则）。
- CFA（Canonical Frame Address，当前调用帧的稳定参考地址）如何计算。
- 返回地址、栈指针和被调用者负责保存的寄存器位于 CFA 的什么位置，或应由什么表达式求得。

Android 17 的 `libunwindstack` 会初始化 `.eh_frame_hdr` / `.eh_frame` 与 `.debug_frame`。每恢复一帧，它先尝试信息更具体的 `.debug_frame`，再尝试 `.eh_frame`，随后可尝试 `.gnu_debugdata`；`.gnu_debugdata` 是 ELF 内可选的压缩迷你调试信息。32 位 ARM 还由 `ElfInterfaceArm` 补充 `.ARM.exidx` 路径。

`.eh_frame_hdr` 是 `.eh_frame` 的索引入口。缺少它不一定导致回溯失败：Android 17 在仍有 `.eh_frame` 时可以直接初始化该段，只是查找路径和成本可能不同。`.eh_frame` 也没有适用于所有项目的固定体积比例；模板展开、异常处理、优化级别和链接器选项都会改变结果，应在自己的 Release ELF 上测量。

CFI 的强项是能表达省略 FP、动态调整 SP、signal frame（内核和运行库为信号处理保存的栈帧）等场景。它也有明确限制：

- 栈或寄存器已被破坏时，恢复规则没有可信输入。
- 当前 PC 找不到对应 FDE 时，规则无从执行。
- 回溯器无法读取 ELF、内存映射表或目标内存时，会停止或进入能力有限的推测路径。
- 手写汇编、运行时生成代码需要提供兼容的回溯信息。
- 一帧的 CFI 能描述如何恢复直接调用者，却无法越过任意损坏的栈数据自动修复后续调用链。

### 3.2 Frame Pointer 链

Frame Pointer（FP，帧指针）是指向当前调用帧固定位置的寄存器。在 arm64 代码保留 FP 时，常见函数序言会保存上一帧的 X29 和返回地址寄存器 X30，并让 X29 指向当前 frame record（保存上一帧 FP 和返回地址的记录）。沿 X29 逐帧读取，便可快速取得一串返回地址。

FP 链适合高频采样或内存分配追踪，但要求经过的每一帧都遵守兼容布局。任何一层省略 FP、破坏 frame record、切换到特殊栈，或进入没有标准帧的运行时生成代码，都可能截断后续结果。32 位 ARM 的帧布局差异和寄存器压力也使 FP 链不如 arm64 稳定。

Android 的 GWP-ASan 文档明确指出：arm64 默认保留 frame pointer，arm32 默认不保留；分配或释放栈缺失时，应检查是否使用了 `-fomit-frame-pointer`。不能只按某个 NDK 小版本推断最终结果，因为 CMake、第三方预编译库、LTO（Link Time Optimization，链接时优化）和单个编译目标的参数都可能覆盖工具链默认值。

需要稳定的 FP 采样时，可以在目标级别明确参数。下面的配置让 CMake 构建目标 `native-lib` 保留 FP，并继续生成回溯表：

```cmake
target_compile_options(native-lib PRIVATE
    -fno-omit-frame-pointer
    -funwind-tables
)
```

配置只影响 `native-lib` 这个构建目标。静态库、预编译 `.so` 和其他 CMake 目标仍需逐个审计，Release 构建实际执行的编译命令才是有效证据。

平台内部还有 `android_unsafe_frame_pointer_chase()`。其头文件明确说明，这个函数面向 sanitizer（在运行时检测内存错误等问题的工具）等平台组件，不是 NDK 应用 API；遇到没有 FP 的帧时，它只保证此前帧可靠，不保证还能继续回溯。应用不应通过私有头文件或 `dlsym` 动态查找这个符号，并把它当作跨版本兼容接口。

### 3.3 `_Unwind_Backtrace()` 的能力边界

`_Unwind_Backtrace()` 可用于当前进程、当前线程的常规 native 调用链。它依赖目标代码提供兼容的回溯表，并可能进入内存分配器、动态链接器或运行库内部状态；这不代表它能在任意致命信号处理器中安全调用。

下面的示例只用于普通诊断路径，不是信号处理器模板：

```cpp
#include <cstddef>
#include <cstdint>
#include <unwind.h>

struct BacktraceState {
  uintptr_t* cursor;
  uintptr_t* end;
};

static _Unwind_Reason_Code CollectFrame(
    _Unwind_Context* context, void* arg) {
  auto* state = static_cast<BacktraceState*>(arg);
  if (state->cursor == state->end) return _URC_END_OF_STACK;

  uintptr_t pc = _Unwind_GetIP(context);
  if (pc != 0) *state->cursor++ = pc;
  return _URC_NO_REASON;
}

size_t CaptureCurrentThread(uintptr_t* frames, size_t capacity) {
  BacktraceState state{frames, frames + capacity};
  _Unwind_Backtrace(CollectFrame, &state);
  return static_cast<size_t>(state.cursor - frames);
}
```

这段代码只收集 PC。`dladdr()` 只能依据进程内可见的模块和动态导出符号解析有限信息，无法替代带 DWARF 的离线符号化，也不会自动生成 `libunwindstack` 插入的 ART Dex 虚拟帧。

### 3.4 回溯性能必须在目标设备实测

FP 回溯通常比 DWARF 回溯更适合高频采样，但“每帧几纳秒”没有跨设备意义。缓存命中、栈是否在本进程、是否要读取远端内存、FDE 编码、ELF 缓存、线程数和最大深度都会改变成本。

选型应基于同一台目标设备、同一份 Release 二进制测量这些指标：

| 指标 | 说明 |
|---|---|
| 单次延迟分位数 | 关注 P50、P95、P99，分别表示约 50%、95%、99% 的样本延迟不超过对应值 |
| 完整栈率 | 能否回到线程入口，或达到业务定义的最低有效深度 |
| 应用帧命中率 | 是否至少得到一帧业务 `.so` |
| 采样丢失率 | 采样缓冲、栈拷贝和回溯耗时是否导致丢样 |
| CPU 与内存开销 | 在目标采样频率下测量，而非由单帧操作数估算 |

崩溃采集更关注完整性和可诊断性，高频 profiler（性能采样器）更关注对被测进程的低干扰。两种场景需要分别测量和选择策略。

## 4. 地址归一化

### 4.1 ASLR 地址换算需要三项修正

ASLR（Address Space Layout Randomization，地址空间布局随机化）会让模块每次加载到不同的运行时位置。绝对 PC 要先落到 `/proc/<pid>/maps` 中对应的内存映射。Android 17 的 `Elf::GetRelPc()` 计算式如下：

```text
rel_pc = runtime_pc - map_start + load_bias + elf_offset
```

`map_start` 是当前映射的起始地址；`load_bias` 是 ELF 虚拟地址与文件偏移之间的装载修正；`elf_offset` 表示当前映射相对 ELF 起点的文件偏移。现代 ELF 常有独立的只读映射和可执行映射，`.so` 还可能直接从 APK 中加载。`MapInfo` 会判断当前映射的 offset 指向完整 ELF 起点、可执行段起点，还是 APK 内嵌 ELF 起点，并尝试关联前一条只读映射。

手工只算 `runtime_pc - map_start`，在这些布局上很容易稳定地错到另一个函数。Android 10—12 的 `libunwindstack` 版本记录列出了多次 load bias、只读段和 APK offset 修复，说明这些布局已经造成过实际错误。

### 4.2 Tombstone 的 `pc` 列通常已完成归一化

`libunwindstack::Unwinder::FormatFrame()` 输出的是 `FrameData.rel_pc`。它还会对非栈顶的返回地址做架构相关 PC adjustment，避免把返回地址错误归到调用点之后。

因此，看到下面的 tombstone 帧时：

```text
#02 pc 0000000000012340  /data/app/.../base.apk!libfoo.so
    (offset 0x2a4000) (Foo::run()+84) (BuildId: 4d7c...)
```

交给 `ndk-stack` 或匹配 ELF 时，应把 `0000000000012340` 当作 tombstone 已给出的相对 PC，不能再次减去 ASLR 基址。`(offset 0x2a4000)` 描述 ELF 在 APK 等容器文件中的位置，也不能机械地从 `pc` 再减一次。

若采集系统上报运行时绝对 PC，而非标准 tombstone 文本，服务端必须同时取得当时的内存映射表、CPU 架构和模块标识，才能重算相对地址。

### 4.3 Build ID 是符号产物的主键

版本号、ABI 和 `.so` 文件名不足以唯一定位二进制。同一版本可能存在分批发布的不同构建、热修复、不同链接顺序或不同渠道产物；地址仍可能落在一个“看起来合理”的错误符号中。

建议使用 `.note.gnu.build-id` 作为符号库主键，并同时保存：

- application ID、version code、构建变体（variant）、渠道和源码 revision（提交版本）；
- ABI（应用二进制接口，例如 `arm64-v8a`）、模块名、Build ID；
- NDK、Clang、链接器和构建参数；
- 未剥离调试信息的 ELF 或独立调试文件（debug file）；
- R8 `mapping.txt`，用于相邻的 Java 栈；
- 符号上传校验和与保留期限。

下面的命令用于从发布 ELF 读取 Build ID 和关键段：

```bash
NDK_BIN="$ANDROID_NDK_HOME/toolchains/llvm/prebuilt/darwin-x86_64/bin"
"$NDK_BIN/llvm-readelf" -nW libfoo.so
"$NDK_BIN/llvm-readelf" -SW libfoo.so
"$NDK_BIN/llvm-readelf" -lW libfoo.so
```

输出中应检查 `.note.gnu.build-id`、`.eh_frame` / `.debug_frame`、符号和调试信息段，以及 `PT_LOAD` 可装载段的文件偏移与虚拟地址。Apple Silicon 上的预编译目录名随 NDK 发行版可能仍是 `darwin-x86_64`；脚本应从已安装 NDK 中发现目录，不能根据主机 CPU 名自行拼接。

## 5. 保存 Release 符号产物

### 5.1 AGP 原生符号包

Android Gradle Plugin（AGP）4.1+ 可以为 Android App Bundle（AAB）生成 native debug symbols。下面的 Kotlin DSL 配置用于保留函数名、文件和行号：

```kotlin
android {
    buildTypes {
        release {
            ndk {
                debugSymbolLevel = "FULL"
            }
        }
    }
}
```

`SYMBOL_TABLE` 主要恢复函数名；`FULL` 还提供文件和行号。构建输出位于 `app/build/outputs/native-debug-symbols/<variant>/native-debug-symbols.zip`，可随 AAB 交给 Play Console，也应按团队的崩溃数据保留周期归档。当前 Play 文档给出的符号文件上限为 1.6 GB；超过时应评估改用 `SYMBOL_TABLE`，不能在未知缺失范围的情况下随意删除模块符号。

第三方依赖若在进入构建前已经剥离调试信息，AGP 无法重新生成。构建日志出现 `native debug metadata has already been stripped` 时，应阻止发布，或留下明确的风险豁免记录。

### 5.2 自建符号服务

自建服务可以保留完整的未剥离 ELF，也可以提取独立 debug 文件。下面的命令为每个 `.so` 生成调试副本，再从交付文件中移除非运行时必需的符号；这个过程通常称为 strip：

```bash
NDK_BIN="$ANDROID_NDK_HOME/toolchains/llvm/prebuilt/darwin-x86_64/bin"

"$NDK_BIN/llvm-objcopy" --only-keep-debug \
  libfoo.so libfoo.so.debug
"$NDK_BIN/llvm-strip" --strip-unneeded libfoo.so
"$NDK_BIN/llvm-objcopy" \
  --add-gnu-debuglink=libfoo.so.debug libfoo.so
```

执行后仍需验证 strip 前后的 Build ID 一致，并确认交付 ELF 保留运行时需要的回溯信息。符号服务建议以 `Build ID + ABI` 建立索引，模块名只作为检索字段。

## 6. 离线符号化工具

### 6.1 `ndk-stack`

`ndk-stack` 适合处理 logcat（Android 系统日志）或 tombstone 文本，并能批量解析其中的多帧。下面的命令把 tombstone 与该构建变体的未剥离库目录配对：

```bash
"$ANDROID_NDK_HOME/ndk-stack" \
  -sym app/build/intermediates/cxx/Release/<hash>/obj/arm64-v8a \
  -dump tombstone.txt
```

`-sym` 要指向未剥离 ELF 目录，不能指向 APK 中已经 strip 的 `.so`。如果输出仍只有模块名和偏移，应检查 ABI、Build ID、输入 tombstone 的分隔头，以及第三方库是否已经丢失调试信息。

### 6.2 `llvm-symbolizer` 与 `llvm-addr2line`

排查单个地址时，优先使用 NDK 自带的 LLVM 工具链。下面的命令会展开内联调用，并 demangle（把编译器编码后的 C++ 符号还原为可读名称）：

```bash
NDK_BIN="$ANDROID_NDK_HOME/toolchains/llvm/prebuilt/darwin-x86_64/bin"
"$NDK_BIN/llvm-symbolizer" \
  --obj=libfoo.so.debug \
  --inlines \
  --demangle \
  0x12340
```

输入 `0x12340` 必须是该 ELF 对应的归一化地址。输出多组函数和行号并不重复：优化后的一个机器指令可能同时属于若干层内联函数。

需要接近 `addr2line` 的输出格式时，可以使用 NDK 自带的 LLVM 版本：

```bash
"$NDK_BIN/llvm-addr2line" \
  -e libfoo.so.debug \
  -f -C -i \
  0x12340
```

`-i` 展开内联帧，`-C` 还原 C++ 名称。不要混用宿主机的 GNU `addr2line` 和 NDK 工具，再直接比较结果；它们面对的目标架构和 DWARF 支持范围可能不同。

## 7. 读 tombstone 时要看哪些证据

下面是一段压缩过的示例，用于说明字段之间的关系：

```text
ABI: 'arm64'
Timestamp: 2026-07-25 10:18:32.123456789+0800
Cmdline: com.example.app
pid: 18421, tid: 18457, name: RenderThread
signal 11 (SIGSEGV), code 1 (SEGV_MAPERR), fault addr 0x10
    x0  0000000000000010  x1  0000007f...
    lr  0000007a11223344  sp  0000007f...
    pc  0000007a11224560

backtrace:
  #00 pc 0000000000014560  base.apk!libfoo.so
      (Foo::Draw()+96) (BuildId: 4d7c...)
  #01 pc 00000000000139a8  base.apk!libfoo.so
      (Renderer::Run()+120) (BuildId: 4d7c...)
```

可以按以下顺序阅读证据：

1. **信号与 `si_code`**：`SIGSEGV` 只是信号类别；`si_code` 是内核给出的细分原因，`SEGV_MAPERR`、`SEGV_ACCERR`、MTE 子类型会指向不同问题。
2. **fault address 与故障指令**：fault address 是指令试图访问的地址。`0x10` 常见于空对象加字段偏移，但仍要反汇编 `#00`，确认哪条指令访问了哪个寄存器。
3. **abort message**：`SIGABRT` 常表示进程主动终止。断言、fdsan（文件描述符误用检测）、Scudo（Android native 内存分配器）、sanitizer 或运行库消息往往比栈顶更有信息。
4. **寄存器与 maps**：确认 PC、LR（Link Register，arm64 返回地址寄存器）、SP 和 fault address 是否落在合理映射，并留意地址高位是否带有内存标签。
5. **完整调用链**：`#00` 可能是 `abort`、内存分配器或 signal trampoline（内核进入和返回信号处理器时经过的过渡帧）；业务触发点常在更深处。
6. **其他线程和诊断区块**：锁等待、内存破坏、GWP-ASan、Scudo、MTE、fdsan 等附加信息可能给出分配栈或更具体的原因。

“栈顶在系统库”不能直接推出系统缺陷。应用传入无效对象、违反 API 前置条件或破坏内存后，故障指令完全可能位于 `libc.so`、`libart.so` 或 `libbinder.so`。

## 8. Java、JIT 与 native 混合调用链

Android 17 的 `AndroidUnwinder::Initialize()` 会在 `libart.so` / `libartd.so` 中定位 JIT（Just-In-Time，即时编译）和 Dex 支持数据。`Unwinder` 遇到 ART 标记的 Dex PC 时，可以插入一个代表解释器 Java 方法的虚拟帧；JIT ELF 则通过 gdb JIT 接口查找。

这项能力属于 `libunwindstack` 与 ART 的协作，不能推广为“任意 native 回溯器都能回溯 Java”。应用侧的 `_Unwind_Backtrace()` 或 FP 链通常只看到 ART 的 native 桥接帧，无法独立还原完整 Java 调用链。

线上混合栈应分别保留三组数据：

- tombstone 或 minidump（保存寄存器、线程栈和模块信息的紧凑崩溃快照）中的 native 寄存器、内存映射表和 PC；
- Java 异常或采样系统得到的 Java 帧与 dex pc；
- 对应版本的 native 符号与 R8 `mapping.txt`。

服务端可按进程、线程、事件时间和桥接帧关联两类调用链，但不要把 Java dex pc 当作 ELF 地址交给 `llvm-symbolizer`。`artDebuggable_getStackFrameAt` 没有可验证的公开接口依据，不能作为方案。

## 9. 应用侧崩溃采集的安全边界

### 9.1 信号处理器里只做最小工作

致命信号可能发生在内存分配器、动态链接器，或某把锁保护的临界区。此时调用 `malloc()`、C++ 容器、`dladdr()`、完整 DWARF 回溯器、普通日志 API 或互斥锁，都可能死锁、再次崩溃或覆盖原现场。

建议在进程正常阶段完成这些准备：

- 预先分配独立的备用信号栈，在边界设置不可访问的保护页（guard page），再通过 `sigaltstack()` 注册；
- 预分配固定大小的崩溃记录；
- 预先打开文件描述符，或建立与独立处理进程的 socket；
- 设计模块清单更新机制，但不要在信号处理器中解析 ELF；
- 设计重入保护、超时与二次信号策略；
- 明确如何把信号继续交给系统 debuggerd 或先前注册的处理器。

信号处理器内只复制 `siginfo_t`、`ucontext_t` 和有限的原始字节，再用经过审计的 async-signal-safe 操作通知外部处理者。async-signal-safe 表示函数即使打断了同进程中的其他代码，也不会依赖可能处于不一致状态的锁或全局数据。POSIX 的 `write()` 可作为基础原语；某函数在多数设备没有出过问题，仍不能证明它满足异步信号安全。

下面的伪代码只表达职责边界，不能直接当作完整的信号处理器复制：

```cpp
static volatile sig_atomic_t handling_crash = 0;
static int crash_fd = -1;  // 正常启动阶段预先打开

static void FatalSignalHandler(
    int signo, siginfo_t* info, void* ucontext) {
  if (handling_crash) _exit(128 + signo);
  handling_crash = 1;

  RawCrashRecord record{};
  record.signo = signo;
  CopyFixedSize(&record.siginfo, info, sizeof(*info));
  CopyFixedSize(&record.ucontext, ucontext, sizeof(ucontext_t));
  WriteFullySignalSafe(crash_fd, &record, sizeof(record));

  RestoreOrChainPreviousHandler(signo);
  ReraiseToCurrentThread(signo);
}
```

其中，`CopyFixedSize`、`WriteFullySignalSafe`、处理器链和重新触发信号，都必须由实现方针对 Bionic、部分写入、`EINTR`（系统调用被信号中断）、备用栈和线程定向信号逐项验证。代码中的抽象函数只是职责占位，并非通用实现。

### 9.2 优先利用系统提供的 tombstone

普通应用无权直接遍历 `/data/tombstones`。Android 12 / API 31 起，应用可从 `ActivityManager.getHistoricalProcessExitReasons()` 查询自己的历史退出记录；当 reason 为 `REASON_CRASH_NATIVE` 时，`ApplicationExitInfo.getTraceInputStream()` 可以返回 protobuf tombstone。

这条路径适合应用在下次启动后补采系统报告，也能减少致命信号现场的工作。它有几个边界：

- 返回值可能为空。系统把 trace 保存在全局环形缓冲区，新记录（包括其他应用的记录）可能覆盖旧记录，调用方必须容错。
- 它查询的是历史退出，不是让当前崩溃进程继续执行。
- protobuf schema 和读取逻辑应随目标 Android 版本验证。
- 数据仍需取得用户同意，并按隐私与保留策略上传。

### 9.3 Crashpad / Breakpad 的位置

Crashpad / Breakpad 使用 minidump 保存现场，服务端再结合符号文件完成回溯和符号化。Crashpad 在 Linux/Android 上可以让信号处理器通知独立处理进程；根据接入方式，它也可能由崩溃进程派生 ptrace broker（具备 ptrace 读取职责的中间进程），代替处理进程直接读取目标进程。

这类方案降低了在崩溃线程内解析 DWARF 和符号的需求，但没有消除工程风险：

- 处理进程启动、SELinux / ptrace 权限、进程模型和 OEM 差异需要实机验证；
- minidump 必须包含足够的线程栈和模块标识；
- 文件写入、磁盘配额、加密、上传与去重都要处理；
- 栈已被破坏时，离线回溯同样可能截断；
- 接入方必须确认所用 fork（从上游项目分出的代码版本）的 Android 支持范围、维护状态和许可证。

不要把系统私有 `debuggerd_client` 或 `libunwindstack` 符号作为普通应用的兼容 API。跨 Android 版本稳定的能力应来自 NDK 公共接口、`ApplicationExitInfo`，或由应用完整控制的采集库。

## 10. PAC、BTI、MTE 与 16 KB 页

### 10.1 PAC

PAC（Pointer Authentication Code，指针认证码）会在 arm64 指针的部分高位保存签名，返回地址也可能带有这些位。Android 17 的 `RegsArm64` 确认返回地址已签名后，会按 PAC mask（标出签名位位置的掩码）清除签名位；没有 mask 时，Bionic 构建还可调用 `__bionic_clear_pac_bits()`。`crash_dump` 也会通过 ptrace 的 `NT_ARM_PAC_ENABLED_KEYS` 读取目标线程启用了哪些 PAC 密钥。

离线系统若自己解析原始 LR 而未清除 PAC 位，可能无法把地址匹配到 maps。使用标准 tombstone 的 `rel_pc` 时不应再次手工“去 PAC”，因为系统回溯器已处理架构细节。

PAC 认证失败的外部表现取决于指令、内核和后续地址使用方式，不能固定写成 `SIGILL`。排查时应结合信号、`si_code`、fault address、PC/LR 和反汇编判断。

### 10.2 BTI

BTI（Branch Target Identification，分支目标识别）约束间接分支可以跳到哪些指令。它不改变 `runtime_pc -> rel_pc` 的换算公式，也不要求符号服务器给 PC 加减固定字节。怀疑 BTI 违规时，应查看故障指令、ELF GNU property（记录架构特性的属性段）和编译参数，不能只依据栈中出现 `bti` 指令。

### 10.3 MTE

MTE（Memory Tagging Extension，内存标签扩展）用指针标签和内存标签不匹配来发现非法访问。Android 17 的 `crash_dump` 同时维护可能带标签的 fault address 和去标签后的地址。同步 MTE 会在出错指令附近报告，异步 MTE 可能延后报告，定位精度不同；上传前不能只保留清除过标签的地址。更完整的 MTE/GWP-ASan 诊断与治理见 20.10。

### 10.4 16 KB 页

16 KB 页会影响 ELF segment（段）的对齐和 APK 内嵌 `.so` 的打包要求，但不会把符号地址统一放大或缩小四倍。符号化仍以内存映射表、ELF program header（程序装载头）、load bias 和 Build ID 为准。Native 库兼容性检查见 20.11。

## 11. 回溯失败时定位中断位置

| 现象 | 优先检查 | 常见原因 |
|---|---|---|
| 只有 `#00` 或两三帧 | 回溯信息段、SP 所在映射、错误码 | 缺失 CFI、FP 链断、栈损坏、ELF 不可读 |
| 地址有模块但无函数名 | Build ID、`.symtab` / `.dynsym` 符号表 | 使用了 strip 后的 ELF、内部函数未导出、符号产物不匹配 |
| 有函数名但无文件行号 | `.debug_info`、`debugSymbolLevel` | 只保留 `SYMBOL_TABLE`、第三方库已提前 strip |
| 行号稳定地偏到别处 | PC 是否重复归一化、APK offset、load bias | 多减一次基址、符号文件版本错误 |
| 内联函数缺失 | symbolizer 参数、DWARF | 未启用内联帧展开、只保留符号表 |
| 某 ABI 正常、另一个 ABI 截断 | 编译参数与回溯格式 | arm32 FP 缺失、预编译库参数不同、`.ARM.exidx` 问题 |
| Java 帧只剩 ART 桥接层 | 采集器能力 | 使用通用 native 回溯器，未取得 ART JIT/Dex 信息 |
| PAC 设备地址不在 maps | 原始 LR 处理 | 上报的是带 PAC 的地址，服务端未做架构处理 |

诊断报告应同时保存已生成的帧、回溯器错误码和警告。`libunwindstack` 可能分别报告 `invalid map`（映射无效）、`memory invalid`（目标内存不可读）、缺失回溯信息等失败；这些信息能区分“符号文件没有上传”和“调用链在设备上已经丢失”。

## 12. Native 发布门禁

每个包含 native 代码的 Release 构建变体，至少验证以下项目：

1. 所有自研与第三方 `.so` 都记录 `ABI + Build ID + 来源`。
2. 交付 ELF 的 `.eh_frame` / `.ARM.exidx` 等运行时回溯信息符合预期。
3. `FULL` 符号包或等价的未剥离产物已生成、可读取并完成异地归档。
4. 用该构建制造一次已知 native 崩溃，`ndk-stack` 和 `llvm-symbolizer` 都能命中正确源码 revision。
5. 覆盖普通函数、内联函数、LTO、异常处理、signal frame、栈溢出和第三方预编译库。
6. 覆盖 `arm64-v8a` 以及仍支持的其他 ABI，不能用 arm64 结果替代 arm32 验证。
7. 覆盖 APK 内直接加载，以及 Split APK（拆分安装包）或动态特性模块中的 `.so`。
8. 在 PAC / MTE 设备和 16 KB 页设备上检查地址与 Build ID。
9. 验证 `ApplicationExitInfo` 或 minidump 的补采、去重、加密、上传和过期删除。
10. 监控符号化率、Build ID 匹配率、完整栈率、业务帧命中率和未知模块占比。

符号化率下降时，按 `Build ID 缺失 -> 产物不匹配 -> 地址归一化失败 -> 设备端回溯截断` 的顺序拆分指标。把所有失败归为“没符号”，会掩盖采集器和构建链中的问题。

## 13. 与 Simpleperf / Perfetto 采样栈的关系

崩溃回溯保存一次故障现场，性能采样则在短时间内收集大量线程现场。Simpleperf 是 Android 原生性能采样工具；其 DWARF 模式需要内核记录用户栈和寄存器，再由 `libunwindstack` 处理。FP 模式开销较低，但要求经过的帧都保留兼容的 frame pointer。Perfetto 可以承载和分析这些系统追踪数据。

发布门禁中的回溯完整性测试也会影响 profiler、GWP-ASan 分配栈和其他诊断工具。不同用途仍要分别评估：崩溃栈完整不能证明高频采样成本可接受，FP 火焰图完整也不能证明 signal frame 与 ART 混合栈都能恢复。

## 14. 错误符号为什么也会“看起来对”

错误 ELF 也可能在相同偏移附近存在函数，输出一个可读且语法完整的函数名。仅用“是否输出函数名”做校验，会把错符号当成成功。

更可靠的服务端校验包含：

- tombstone / minidump 的模块 Build ID 与符号文件完全匹配；
- 地址位于 ELF 可执行 `PT_LOAD` 范围；
- 返回的函数范围覆盖输入地址；
- source revision 属于该发布产物；
- 同一事件的所有同模块帧使用同一个 Build ID；
- 不匹配时明确标记 `symbol artifact missing/mismatch`，不回退到同名最新版。

## 15. 与相邻章节的分工

- 20.3：Native 崩溃信号类型、采集治理与线上处置。
- 20.10：MTE/GWP-ASan 的检测机制、报告和灰度策略。
- 20.11：16 KB 页下的 ELF、打包和第三方库兼容。
- 14.2：Simpleperf 的采样、调用链和数据分析。
- 14.26：Hook 基础设施的实现与风险；本篇只讨论崩溃采集中的安全边界。

## 源码与官方资料

- [AOSP `crash_dump.cpp`（android-17.0.0_r1）](https://android.googlesource.com/platform/system/core/+/refs/tags/android-17.0.0_r1/debuggerd/crash_dump.cpp)
- [AOSP `debuggerd_handler.cpp`（android-17.0.0_r1）](https://android.googlesource.com/platform/system/core/+/refs/tags/android-17.0.0_r1/debuggerd/handler/debuggerd_handler.cpp)
- [AOSP `tombstone.cpp`（android-17.0.0_r1）](https://android.googlesource.com/platform/system/core/+/refs/tags/android-17.0.0_r1/debuggerd/libdebuggerd/tombstone.cpp)
- [AOSP `tombstone_proto.cpp`（android-17.0.0_r1）](https://android.googlesource.com/platform/system/core/+/refs/tags/android-17.0.0_r1/debuggerd/libdebuggerd/tombstone_proto.cpp)
- [AOSP `AndroidUnwinder.cpp`（android-17.0.0_r1）](https://android.googlesource.com/platform/system/unwinding/+/refs/tags/android-17.0.0_r1/libunwindstack/AndroidUnwinder.cpp)
- [AOSP `Unwinder.cpp`（android-17.0.0_r1）](https://android.googlesource.com/platform/system/unwinding/+/refs/tags/android-17.0.0_r1/libunwindstack/Unwinder.cpp)
- [AOSP `Elf.cpp`（android-17.0.0_r1）](https://android.googlesource.com/platform/system/unwinding/+/refs/tags/android-17.0.0_r1/libunwindstack/Elf.cpp)
- [AOSP `ElfInterface.cpp`（android-17.0.0_r1）](https://android.googlesource.com/platform/system/unwinding/+/refs/tags/android-17.0.0_r1/libunwindstack/ElfInterface.cpp)
- [AOSP `RegsArm64.cpp`（android-17.0.0_r1）](https://android.googlesource.com/platform/system/unwinding/+/refs/tags/android-17.0.0_r1/libunwindstack/RegsArm64.cpp)
- [libunwindstack 各 Android 版本能力（android-17.0.0_r1）](https://android.googlesource.com/platform/system/unwinding/+/refs/tags/android-17.0.0_r1/libunwindstack/AndroidVersions.md)
- [Bionic `android_unsafe_frame_pointer_chase.h`（android-17.0.0_r1）](https://android.googlesource.com/platform/bionic/+/refs/tags/android-17.0.0_r1/libc/platform/bionic/android_unsafe_frame_pointer_chase.h)
- [Simpleperf：Debug DWARF unwinding（android-17.0.0_r1）](https://android.googlesource.com/platform/system/extras/+/refs/tags/android-17.0.0_r1/simpleperf/doc/debug_dwarf_unwinding.md)
- [Android NDK：ndk-stack](https://developer.android.com/ndk/guides/ndk-stack)
- [Android NDK：调试 native crash 与 ApplicationExitInfo](https://developer.android.com/ndk/guides/debug)
- [`ApplicationExitInfo`](https://developer.android.com/reference/android/app/ApplicationExitInfo)
- [Android NDK：GWP-ASan](https://developer.android.com/ndk/guides/gwp-asan)
- [Android Developers：为发布构建加入 native symbols](https://developer.android.com/build/include-native-symbols)
- [AOSP：Diagnose native crashes](https://source.android.com/docs/core/tests/debug/native-crash)
- [Crashpad overview design](https://chromium.googlesource.com/crashpad/crashpad/+/HEAD/doc/overview_design.md)

> 源码核查基线：AOSP `android-17.0.0_r1`。编译器、NDK 和 AGP 行为还应以项目锁定版本及 Release 构建产物为准。
