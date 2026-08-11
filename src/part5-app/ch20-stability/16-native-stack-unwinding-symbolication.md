---
title: "Native 堆栈回溯与符号化机制"
chapter: "20.16"
status: ready-for-review
applicable_versions: "Android 10 (API 29) - Android 17 (API 37)"
drafted_date: "2026-06-27"
last_verified: "2026-06-27"
last_verified_against: "AOSP android-17.0.0_r1"
confidence: high
sources:
  - type: aosp
    path: "system/core/debuggerd/crash_dump.cpp"
  - type: aosp
    path: "system/core/debuggerd/libdebuggerd/BacktraceMap.cpp"
  - type: aosp
    path: "system/core/libcutils/include/cutils/threads.h"
  - type: aosp
    path: "external/libunwind/src/UnwindCursor.hpp"
  - type: official
    path: "developer.android.com/ndk/guides/cpu-arm-neon"
  - type: blog
    path: "Android NDK r23 release notes — FP unwinding default"
tags: [native, crash, stack-unwinding, symbolication, ndk, elf, tombstone, cfi]
related_chapters: ["20.3", "9.3", "14.2", "14.26"]
created_by: "task2a-knowledge-gap"
created_date: "2026-06-26"
gap_source: "素材驱动/参考书"
---

# Native 堆栈回溯与符号化机制

Native Crash 报告中的一行 `#00 pc 0000000000008a3c libfoo.so` 已经不是进程里的绝对地址。系统回溯器先找到了该 PC 所属的内存映射，再把它换算成 ELF 内的相对 PC；离线工具还要找到 Build ID 完全一致的未裁剪 ELF，才可能恢复函数、内联调用链与源码行。

因此，“拿到地址”只完成了分析链的一小段。稳定的 Native 诊断系统至少包含五步：

1. **采集**：保存信号、`siginfo_t`、寄存器、线程栈和内存映射。
2. **回溯**：按 DWARF CFI、ARM EHABI 或其他可用信息恢复调用者寄存器。
3. **地址归一化**：把运行时 PC 换算成对应 ELF 可以识别的地址。
4. **符号化**：以匹配的符号产物解析函数、文件、行号和内联帧。
5. **质量判定**：识别错符号、截断栈和缺失帧，不能把“工具输出了一串函数名”当成正确答案。

平台源码锚点是 Android 17 / API 37 / `android-17.0.0_r1`，重点说明这五步如何衔接，以及每一步的证据边界。

## 要点

### 🔹 先分清两个都叫 CFI 的概念

Native 诊断里经常出现两个缩写相同、含义无关的术语：

| 缩写 | 全称 | 解决的问题 |
|---|---|---|
| CFI | Call Frame Information | 描述给定 PC 处如何恢复调用者的 SP、PC 和其他寄存器，用于异常处理与栈回溯 |
| CFI | Control Flow Integrity | 检查间接调用或跳转的目标是否合法，用于控制流安全加固 |

没有特殊说明时，CFI 指 **Call Frame Information**。Control Flow Integrity 的违规表现受编译参数、运行库和 trap 模式影响，不能统一写成某个固定信号，也不应拿它解释普通的回溯失败。

### 🔹 Android 17 的系统 tombstone 路径

#### 崩溃线程只提交现场，重活交给 `crash_dump`

Bionic 的 debuggerd 信号处理代码接收 `siginfo_t` 和 `ucontext_t`，把崩溃现场通过管道交给 `crash_dump`。`crash_dump` 对目标进程的线程执行 `PTRACE_SEIZE` / `PTRACE_INTERRUPT`，读取寄存器和线程信息。为了缩短原进程被冻结的时间，它还创建一个保留目标地址空间快照的 VM 进程，随后让原进程继续退出。

Android 17 源码中的关键对象是：

- `crash_dump.cpp`：停止线程、读取崩溃现场、建立地址空间快照并连接 `tombstoned`。
- `AndroidRemoteUnwinder`：解析快照进程的 maps，并通过 `libunwindstack` 回溯。
- `engrave_tombstone()`：构建 protobuf tombstone，再生成文本表示。

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

这个模型解释了两个常见现象：tombstone 可以包含多个线程，而应用自己的信号处理器通常只天然掌握当前线程；系统回溯器可以读取目标地址空间和 ART 的 JIT/Dex 信息，而一个简单的 `_Unwind_Backtrace()` 调用没有同等能力。

#### 当前主回溯器是 `libunwindstack`

`crash_dump.cpp` 在 `android-17.0.0_r1` 中直接包含 `unwindstack/AndroidUnwinder.h`，并以快照进程 PID 创建 `AndroidRemoteUnwinder`。旧的 `libunwind`、`libbacktrace` 路径不再代表当前 debuggerd 实现。

`libunwindstack` 自 Android 9 / API 28 引入。其版本说明记录了这些 Android 相关能力：

- DWARF 回溯信息，早期已支持到 DWARF 4，并逐步兼容部分 DWARF 5 数据。
- 32 位 ARM 的 `.ARM.exidx`。
- gdb JIT 接口，用于识别 ART JIT 代码。
- ART 解释器通过特殊 CFI 标记暴露的 Dex PC 虚拟帧。
- Android 10—12 对 load bias、分段 ELF 和 APK 内嵌 ELF 偏移的多轮修正。
- Android 15 / API 35 起读取以 zlib 或 zstd 压缩的 `.debug_frame`。

这些属于回溯器能力，不等于每个栈都能恢复。目标 ELF、栈内存、寄存器和映射只要缺少一项，调用链仍可能中断。

### 🔹 回溯器怎样恢复上一帧

#### DWARF Call Frame Information

编译器通常把调用帧恢复规则写入 `.eh_frame`，也可能写入 `.debug_frame`。规则会针对给定 PC 描述以下信息：

- 当前 PC 属于哪个 FDE（Frame Description Entry）。
- CFA（Canonical Frame Address）如何计算。
- 返回地址、栈指针和被调用者保存寄存器位于 CFA 的什么位置，或应由什么表达式求得。

`libunwindstack` 的 Android 17 实现会初始化 `.eh_frame_hdr` / `.eh_frame` 与 `.debug_frame`。执行一步回溯时，它优先尝试信息更具体的 `.debug_frame`，再尝试 `.eh_frame`，之后还可尝试 `.gnu_debugdata`；32 位 ARM 由 `ElfInterfaceArm` 补充 `.ARM.exidx` 路径。

`.eh_frame_hdr` 是 `.eh_frame` 的索引入口。缺少它不必然让回溯失效：Android 17 的实现会在存在 `.eh_frame` 时直接初始化该段，只是查找路径和成本可能不同。也不应给 `.eh_frame` 的体积写一个跨项目通用百分比；模板展开、异常处理、优化级别与链接器选项都会改变结果，应在自己的 Release ELF 上测量。

CFI 的强项是能表达省略 FP、动态调整 SP、signal frame 等场景。它也有明确限制：

- 栈或寄存器已被破坏时，恢复规则没有可信输入。
- 当前 PC 找不到对应 FDE 时，规则无从执行。
- 回溯器读取不到 ELF、maps 或目标内存时，会停止或进入有限的推测路径。
- 手写汇编、运行时生成代码需要提供兼容的 unwind 信息。
- 一帧的 CFI 能描述如何恢复直接调用者，但不能越过任意损坏的栈数据“自动修好”后续调用链。

#### Frame Pointer 链

在 arm64 代码保留 frame pointer 时，常见函数序言会保存上一帧的 X29 和返回地址 X30，并令 X29 指向当前 frame record。沿 X29 读取 frame record，便可快速取得一串返回地址。

它适合高频采样或分配追踪，但需要整条路径遵守兼容的帧布局。任何一层省略 FP、破坏 frame record、切换到特殊栈或进入没有标准帧的生成代码，都可能截断后续结果。32 位 ARM 的帧布局和寄存器压力也使 FP 链远不如 arm64 稳定。

Android 官方的 GWP-ASan 文档给出的工程边界很直接：arm64 默认保留 frame pointer，arm32 默认不保留；如果分配/释放栈缺失，应检查是否使用了 `-fomit-frame-pointer`。这比把行为绑定到某个 NDK 小版本更可靠，因为 CMake、第三方预编译库、LTO 和单目标编译参数都可能覆盖工具链默认值。

需要稳定的 FP 采样时，可以在目标级别明确参数。下面的配置用于让 `native-lib` 保留 FP，并继续生成 unwind table：

```cmake
target_compile_options(native-lib PRIVATE
    -fno-omit-frame-pointer
    -funwind-tables
)
```

配置只影响这个 target。静态库、预编译 `.so` 和其他 CMake target 仍需逐个审计，Release 构建的实际编译命令才是有效证据。

平台内部还存在 `android_unsafe_frame_pointer_chase()`，其头文件明确说明它面向 sanitizer 等平台组件，不是 NDK 应用 API；遇到无 FP 的帧时，只保证此前帧可靠，并不保证继续回溯。应用不应通过私有头文件或 `dlsym` 把它当成线上兼容接口。

#### `_Unwind_Backtrace()` 的能力边界

`_Unwind_Backtrace()` 可用于当前进程、当前线程的常规 native 调用链。它依赖目标代码提供兼容的 unwind table，并可能经过分配器、动态链接器或运行库内部状态；不能据此认定它适合在任意致命信号现场调用。

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

这段代码只收集 PC。`dladdr()` 最多依赖进程内可见的动态符号恢复模块和导出符号，不能替代带 DWARF 的离线符号化，也不会自动生成 `libunwindstack` 注入的 ART Dex 虚拟帧。

#### 不要写死“哪种回溯快多少”

FP 回溯通常比 DWARF 回溯更适合高频采样，但“每帧几纳秒”没有跨设备意义。缓存命中、栈是否在本进程、是否要读取远端内存、FDE 编码、ELF 缓存、线程数和最大深度都会改变成本。

选型应基于同一台目标设备、同一份 Release 二进制测量这些指标：

| 指标 | 说明 |
|---|---|
| 单次延迟分位数 | 关注 P50、P95、P99，不能只看平均值 |
| 完整栈率 | 能否回到线程入口，或达到业务定义的最低有效深度 |
| 应用帧命中率 | 是否至少得到一帧业务 `.so` |
| 采样丢失率 | 采样缓冲、栈拷贝和回溯耗时是否导致丢样 |
| CPU 与内存开销 | 在目标采样频率下测量，而非由单帧操作数估算 |

崩溃采集偏向完整性和可诊断性，高频 profiler 偏向低扰动。两者不该共享一套未经测量的策略。

### 🔹 地址归一化：最容易被忽略的一步

#### ASLR 不是只减一个“so 基址”

运行时绝对 PC 需要先落到某条 `/proc/<pid>/maps` 映射。Android 17 的 `Elf::GetRelPc()` 计算式是：

```text
rel_pc = runtime_pc - map_start + load_bias + elf_offset
```

这里的 `elf_offset` 与 `load_bias` 不能随意省略。现代 ELF 常有独立的只读映射和可执行映射；`.so` 还可能直接从 APK 中加载。`MapInfo` 会判断当前 map 的 offset 是完整 ELF 起点、可执行段起点，还是 APK 内嵌 ELF 起点，并尝试关联前一条只读 map。

手工只算 `runtime_pc - map_start`，在这些布局上很容易稳定地错到另一个函数。Android 10—12 的 `libunwindstack` 版本记录专门列出了多次 load bias、rosegment 与 APK offset 修复，也说明这不是理论上的边角问题。

#### Tombstone 的 `pc` 列通常已完成归一化

`libunwindstack::Unwinder::FormatFrame()` 输出的是 `FrameData.rel_pc`。它还会对非栈顶的返回地址做架构相关 PC adjustment，避免把返回地址错误归到调用点之后。

因此，看到下面的 tombstone 帧时：

```text
#02 pc 0000000000012340  /data/app/.../base.apk!libfoo.so
    (offset 0x2a4000) (Foo::run()+84) (BuildId: 4d7c...)
```

交给 `ndk-stack` 或匹配 ELF 时，应把 `0000000000012340` 当作 tombstone 已给出的相对 PC。不要再减 ASLR 基址，也不要因为存在 `(offset 0x2a4000)` 就机械地再减一次；该 offset 描述 ELF 在容器文件中的位置。

若采集系统上报的是运行时绝对 PC，而非标准 tombstone 文本，则服务端必须同时获得当时的 maps、架构和模块标识，才能重算相对地址。

#### Build ID 是符号产物的主键

版本号、ABI 和 `.so` 文件名不足以唯一定位二进制。同一版本可能有灰度包、热修复、不同链接顺序或不同渠道产物；地址仍可能落在一个“看起来合理”的错误符号中。

建议使用 `.note.gnu.build-id` 作为符号库主键，并同时保存：

- application ID、version code、variant、渠道和源码 revision；
- ABI、模块名、Build ID；
- NDK、Clang、链接器和构建参数；
- 未裁剪 ELF或独立 debug 文件；
- R8 `mapping.txt`，用于相邻的 Java 栈；
- 符号上传校验和与保留期限。

下面的命令用于从发布 ELF 读取 Build ID 和关键段：

```bash
NDK_BIN="$ANDROID_NDK_HOME/toolchains/llvm/prebuilt/darwin-x86_64/bin"
"$NDK_BIN/llvm-readelf" -nW libfoo.so
"$NDK_BIN/llvm-readelf" -SW libfoo.so
"$NDK_BIN/llvm-readelf" -lW libfoo.so
```

输出应检查 `.note.gnu.build-id`、`.eh_frame` / `.debug_frame`、符号与 debug 段，以及 `PT_LOAD` 的文件偏移和虚拟地址。Apple Silicon 上的预编译目录名随 NDK 发行版可能仍是 `darwin-x86_64`，脚本应从已安装 NDK 中发现目录，不要凭主机 CPU 名拼接。

### 🔹 Release 符号产物怎样保存

#### AGP 原生符号包

Android Gradle Plugin 4.1+ 可以在 AAB 中生成 native debug symbols。下面的 Kotlin DSL 配置用于保留文件、行号和函数信息：

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

`SYMBOL_TABLE` 主要恢复函数名；`FULL` 还提供文件和行号。构建输出位于 `app/build/outputs/native-debug-symbols/<variant>/native-debug-symbols.zip`，可随 AAB 交给 Play Console，也应按团队的崩溃数据保留周期归档。

第三方依赖如果在进入构建前已经丢掉 debug 信息，AGP 无法凭空恢复。构建日志中的 “native debug metadata has already been stripped” 应当作为发布阻断项或明确的风险豁免。

#### 自建符号服务

自建服务可以保留完整未裁剪 ELF，也可以提取独立 debug 文件。下面的命令为每个 `.so` 生成 debug 副本并裁剪交付文件：

```bash
NDK_BIN="$ANDROID_NDK_HOME/toolchains/llvm/prebuilt/darwin-x86_64/bin"

"$NDK_BIN/llvm-objcopy" --only-keep-debug \
  libfoo.so libfoo.so.debug
"$NDK_BIN/llvm-strip" --strip-unneeded libfoo.so
"$NDK_BIN/llvm-objcopy" \
  --add-gnu-debuglink=libfoo.so.debug libfoo.so
```

这套做法仍需验证裁剪前后 Build ID 一致，并确认交付 ELF 保留运行时需要的 unwind 信息。符号服务的索引建议以 `Build ID + ABI` 为主，模块名只作为检索字段。

### 🔹 离线符号化工具

#### `ndk-stack`

`ndk-stack` 适合处理 logcat 或 tombstone 文本，并能批量解析其中的多帧。下面的命令把 tombstone 与该 variant 的未裁剪库目录配对：

```bash
"$ANDROID_NDK_HOME/ndk-stack" \
  -sym app/build/intermediates/cxx/Release/<hash>/obj/arm64-v8a \
  -dump tombstone.txt
```

`-sym` 指向未裁剪 ELF 目录，不是 APK 中已经 strip 的 `.so`。如果输出仍只有模块加偏移，应检查 ABI、Build ID、输入 tombstone 的分隔头，以及第三方库是否已经丢失 debug 信息。

#### `llvm-symbolizer` 与 `llvm-addr2line`

单地址排查优先使用 NDK LLVM 工具链。下面的命令展开内联调用并 demangle C++ 名称：

```bash
NDK_BIN="$ANDROID_NDK_HOME/toolchains/llvm/prebuilt/darwin-x86_64/bin"
"$NDK_BIN/llvm-symbolizer" \
  --obj=libfoo.so.debug \
  --inlines \
  --demangle \
  0x12340
```

输入 `0x12340` 必须是该 ELF 对应的归一化地址。输出多组函数和行号并不重复：优化后的一个机器指令可能同时属于若干层内联函数。

需要接近 `addr2line` 的输出格式时，可使用 NDK 自带的 LLVM 版本：

```bash
"$NDK_BIN/llvm-addr2line" \
  -e libfoo.so.debug \
  -f -C -i \
  0x12340
```

`-i` 展开内联帧，`-C` 反解 C++ 名称。不要把宿主机上的 GNU `addr2line` 与 NDK 目标架构、DWARF 版本混用后再比较结果。

### 🔹 怎样读 tombstone，而不是只看 `#00`

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

建议按以下证据顺序阅读：

1. **信号与 `si_code`**：`SIGSEGV` 只是类别；`SEGV_MAPERR`、`SEGV_ACCERR`、MTE 子类型等会改变排查方向。
2. **fault address 与故障指令**：`0x10` 常见于空对象加字段偏移，但仍要反汇编 `#00`，确认哪条指令访问了哪个寄存器。
3. **abort message**：`SIGABRT` 常是主动终止，断言、fdsan、Scudo、sanitizer 或运行库消息往往比栈顶更有信息。
4. **寄存器与 maps**：确认 PC、LR、SP 和 fault address 是否落在合理映射，留意 tagged address。
5. **完整调用链**：`#00` 可能是 `abort`、allocator 或信号 trampoline；业务触发点常在更深处。
6. **其他线程和诊断区块**：锁等待、内存破坏、GWP-ASan、Scudo、MTE、fdsan 等附加信息可能给出分配栈或原因判断。

“栈顶在系统库”不能直接推出系统缺陷。应用传入无效对象、违反 API 前置条件或破坏内存后，故障指令完全可能位于 `libc.so`、`libart.so` 或 `libbinder.so`。

### 🔹 Java、JIT 与 native 混合调用链

Android 17 的 `AndroidUnwinder::Initialize()` 会在 `libart.so` / `libartd.so` 中定位 JIT 和 Dex 支持数据。`Unwinder` 遇到 ART 标记的 Dex PC 时，可以插入一个代表解释器 Java 方法的虚拟帧；JIT ELF 则通过 gdb JIT 接口查找。

这项能力属于 `libunwindstack` 与 ART 的协作，不能推广为“任意 native unwinder 都能回溯 Java”。应用侧的 `_Unwind_Backtrace()` 或 FP 链通常只看到 ART 的 native 桥接帧，无法独立还原完整 Java 调用链。

线上混合栈应保留三组不同的数据：

- tombstone / minidump 中的 native 寄存器、maps 和 PC；
- Java 异常或采样系统得到的 Java 帧与 dex pc；
- 对应版本的 native symbols 与 R8 `mapping.txt`。

服务端可按进程、线程、事件时间和桥接帧关联两类调用链，但不要把 Java dex pc 当作 ELF 地址交给 `llvm-symbolizer`。旧文中不存在公开依据的 `artDebuggable_getStackFrameAt` 不是可用方案。

### 🔹 应用侧崩溃采集的安全边界

#### 信号处理器里只做最小工作

致命信号可能发生在 allocator、动态链接器或某把锁的临界区。此时调用 `malloc()`、C++ 容器、`dladdr()`、完整 DWARF unwinder、普通日志 API 或互斥锁，都可能死锁、递归崩溃或覆盖原现场。

建议在进程正常阶段完成这些准备：

- 通过 `sigaltstack()` 配置独立且带 guard 的备用信号栈；
- 预分配固定大小的崩溃记录；
- 预先打开文件描述符或建立与独立 handler 的 socket；
- 记录模块清单更新机制，但不要在 handler 中解析 ELF；
- 设计重入保护、超时与二次信号策略；
- 明确如何保留系统 debuggerd 和先前 handler 的处理机会。

信号处理器内只复制 `siginfo_t`、`ucontext_t` 和有限的原始字节，再用经过审计的 async-signal-safe 操作通知外部处理者。POSIX 的 `write()` 可作为基础原语；“某函数在多数设备没出事”不等于它满足异步信号安全。

下面的伪代码只表达职责分界，不是一份可直接复制的完整 handler：

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

其中 `CopyFixedSize`、`WriteFullySignalSafe`、handler 链和重新触发信号都必须由实现方针对 Bionic、部分写入、`EINTR`、备用栈和线程定向信号逐项验证。代码中的抽象函数故意不冒充通用实现。

#### 优先利用系统已提供的 tombstone

普通应用无权直接遍历 `/data/tombstones`。Android 12 / API 31 起，应用可从 `ActivityManager.getHistoricalProcessExitReasons()` 查询自己的历史退出记录；当 reason 为 `REASON_CRASH_NATIVE` 时，`ApplicationExitInfo.getTraceInputStream()` 可以返回 protobuf tombstone。

这条路径适合应用在下次启动后补采系统报告，也能减少在致命信号现场做复杂工作的必要。它有几个边界：

- 返回值可能为空，调用方必须容错。
- 它查询的是历史退出，不是让当前崩溃进程继续执行。
- protobuf schema 和读取逻辑应随目标 Android 版本验证。
- 数据仍需取得用户同意，并按隐私与保留策略上传。

#### Crashpad / Breakpad 的位置

Minidump 方案把寄存器、线程栈、模块清单和模块标识保存为紧凑快照，由服务端结合符号文件回溯和符号化。Crashpad 在 Linux/Android 上可让信号 handler 通知独立 handler；按连接方式，它还可能由崩溃进程派生 ptrace broker，代替 handler 读取进程。

这类方案降低了在崩溃线程内解析 DWARF 和符号的需求，但没有消除工程风险：

- handler 启动、SELinux / ptrace、进程模型和 OEM 差异需要实机验证；
- minidump 必须包含足够的线程栈和模块标识；
- 文件写入、磁盘配额、加密、上传与去重都要处理；
- 栈已被破坏时，离线回溯同样可能截断；
- 接入方必须确认所用 fork 的 Android 版本、维护状态和许可证。

不要把系统私有 `debuggerd_client` 或 `libunwindstack` 符号作为普通应用的兼容 API。跨 Android 版本稳定的能力应来自 NDK 公共接口、`ApplicationExitInfo`，或由应用完整控制的采集库。

### 🔹 PAC、BTI、MTE 与 16 KB 页

#### PAC

arm64 的返回地址可能包含 Pointer Authentication Code。Android 17 的 `RegsArm64` 在确认返回地址已签名时，会按 PAC mask 清除签名位；缺少 mask 时，Bionic 构建还可调用 `__bionic_clear_pac_bits()`。`crash_dump` 也会通过 ptrace 读取目标线程启用的 PAC key 状态。

离线系统若自己解析原始 LR 而未清除 PAC 位，可能无法把地址匹配到 maps。使用标准 tombstone 的 `rel_pc` 时不应再次手工“去 PAC”，因为系统回溯器已处理架构细节。

PAC 认证失败的外部表现受指令、内核和后续地址使用方式影响，不应固定写成 `SIGILL`。排查时应联合信号、`si_code`、fault address、PC/LR 和反汇编判断。

#### BTI

Branch Target Identification 约束间接分支的合法落点。它不改变 `runtime_pc -> rel_pc` 的换算公式，也不要求符号服务器给 PC 加减固定字节。若怀疑 BTI 违规，应查看 fault 指令、ELF GNU property 和编译参数，不能只依据栈里出现 `bti` 指令。

#### MTE

Android 17 的 `crash_dump` 同时保存可能带 tag 的 fault address 与去 tag 后的地址。MTE 同步、异步故障的定位能力不同；不要在上传前只保留一个被清洗过的地址。更完整的 MTE/GWP-ASan 诊断与治理见 20.10。

#### 16 KB 页

16 KB 页会影响 ELF segment 对齐与 APK 内嵌 `.so` 的打包要求，但不会把符号地址统一放大或缩小四倍。符号化仍以 maps、ELF program header、load bias 和 Build ID 为准。Native 库兼容性检查见 20.11。

### 🔹 回溯失败时怎样定位是哪一层断了

| 现象 | 优先检查 | 常见原因 |
|---|---|---|
| 只有 `#00` 或两三帧 | unwind 段、SP 所在 map、错误码 | 缺失 CFI、FP 链断、栈损坏、不可读 ELF |
| 地址有模块但无函数名 | Build ID、`.symtab` / `.dynsym` | 使用了 strip 后 ELF、内部函数未导出、符号产物不匹配 |
| 有函数名但无文件行号 | `.debug_info`、`debugSymbolLevel` | 只保留 `SYMBOL_TABLE`、第三方库已提前 strip |
| 行号稳定地偏到别处 | PC 是否重复归一化、APK offset、load bias | 多减一次基址、符号文件版本错误 |
| 内联函数缺失 | symbolizer 参数、DWARF | 未启用 inline 展开、只保留符号表 |
| 某 ABI 正常、另一个 ABI 截断 | 编译参数与 unwind 格式 | arm32 FP 缺失、预编译库参数不同、`.ARM.exidx` 问题 |
| Java 帧只剩 ART 桥接层 | 采集器能力 | 使用通用 native unwinder，未取得 ART JIT/Dex 信息 |
| PAC 设备地址不在 maps | 原始 LR 处理 | 上报的是带 PAC 的地址，服务端未做架构处理 |

诊断报告应保存回溯器错误码和警告，而不是只保留已生成的 frames。`libunwindstack` 可能报告 invalid map、memory invalid、unwind info 缺失等不同失败；这些信息能区分“符号文件没有上传”和“调用链在设备上已经丢失”。

### 🔹 一套可执行的发布门禁

每个包含 native 代码的 Release variant，至少验证以下项目：

1. 所有自研与第三方 `.so` 都记录 `ABI + Build ID + 来源`。
2. 交付 ELF 的 `.eh_frame` / `.ARM.exidx` 等运行时回溯信息符合预期。
3. `FULL` 符号包或等价的未裁剪产物已生成、可读取并完成异地归档。
4. 用该构建制造一次已知 native crash，`ndk-stack` 和 `llvm-symbolizer` 都能命中正确源码 revision。
5. 覆盖普通函数、内联函数、LTO、异常处理、signal frame、栈溢出和第三方预编译库。
6. 覆盖 `arm64-v8a` 以及仍支持的其他 ABI，不能用 arm64 结果替代 arm32 验证。
7. 覆盖 APK 内直接加载、Split APK / 动态特性中的 `.so`。
8. 在 PAC / MTE 设备和 16 KB 页设备上检查地址与 Build ID。
9. 验证 `ApplicationExitInfo` 或 minidump 的补采、去重、加密、上传和过期删除。
10. 监控符号化率、Build ID 匹配率、完整栈率、业务帧命中率和未知模块占比。

当符号化率下降时，按 `Build ID 缺失 -> 产物不匹配 -> 地址归一化失败 -> 设备端回溯截断` 的顺序拆分指标。把所有失败归为“没符号”会掩盖采集器和构建链中的问题。

## 扩展

### 🔸 与 Simpleperf / Perfetto 采样栈的关系

崩溃回溯拿到的是一次故障现场，性能采样会在短时间内采集大量现场。Simpleperf 的 DWARF 模式需要内核记录用户栈与寄存器，再由 `libunwindstack` 处理；FP 模式更轻，但要求被经过的帧保留兼容 frame pointer。

因此，发布门禁里的 unwind 完整性测试也会影响 profiler、GWP-ASan 分配栈和其他诊断工具。仍需分别评估：崩溃栈完整不代表高频采样成本可接受，FP 火焰图完整也不代表 signal frame 与 ART 混合栈都能恢复。

### 🔸 符号化结果为什么会“看起来对”

错误 ELF 也可能在相同偏移附近存在函数，输出一个可读且语法完整的函数名。仅用“是否输出函数名”做校验，会把错符号当成成功。

更可靠的服务端校验包含：

- tombstone / minidump 的模块 Build ID 与符号文件完全匹配；
- 地址位于 ELF 可执行 `PT_LOAD` 范围；
- 返回的函数范围覆盖输入地址；
- source revision 属于该发布产物；
- 同一事件的所有同模块帧使用同一个 Build ID；
- 不匹配时明确标记 `symbol artifact missing/mismatch`，不回退到同名最新版。

### 🔸 与相邻章节的分工

- 20.3：Native Crash 信号类型、采集治理与线上处置。
- 20.10：MTE/GWP-ASan 的检测机制、报告和灰度策略。
- 20.11：16 KB 页下的 ELF、打包和第三方库兼容。
- 14.2、14.26：ART/JNI 与 native 内存相关基础。

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
- [Android NDK：GWP-ASan](https://developer.android.com/ndk/guides/gwp-asan)
- [Android Developers：为发布构建加入 native symbols](https://developer.android.com/build/include-native-symbols)
- [AOSP：Diagnose native crashes](https://source.android.com/docs/core/tests/debug/native-crash)
- [Crashpad overview design](https://chromium.googlesource.com/crashpad/crashpad/+/HEAD/doc/overview_design.md)

> 源码核查基线：AOSP `android-17.0.0_r1`。编译器、NDK 和 AGP 行为还应以项目锁定版本及 Release 构建产物为准。
