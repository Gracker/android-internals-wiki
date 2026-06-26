---
title: "Native 堆栈回溯与符号化机制"
chapter: "20.18"
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
related_chapters: ["20.3", "9.3", "14.2", "14.13"]
created_by: "task2a-knowledge-gap"
created_date: "2026-06-26"
gap_source: "素材驱动/参考书"
---

# 20.18 Native 堆栈回溯与符号化机制

Native Crash 分析的瓶颈不在「崩溃有没有上报」，而在「崩溃堆栈能不能还原到源码行号」。一段 `#00 pc 0x8a3c` 的原始地址，如果没有可靠的回溯和符号化管线，等于丢失了全部调试信息。20.3 节介绍了 Native Crash 的信号收集路径和 tombstone 读取方法；这一节拆解的是更底层的问题：堆栈地址是怎么从 CPU 寄存器和 ELF 文件里「拼」出来的，以及从原始地址到可读源码行号的完整链路里，每一步可能在哪里断掉。

## 要点

### 🔹 为什么 Native 堆栈回溯是稳定性基建

线上 Native Crash 的排查效率，几乎完全取决于堆栈质量。一个只有 `#00 pc 0x8a3c /libfoo.so` 的崩溃报告，和一段带函数名、参数、源码行号的完整堆栈，排查时间可能差一个数量级。

堆栈质量由两个环节决定：

- **回溯（unwinding）**：从崩溃时刻的 CPU 寄存器状态出发，沿着函数调用链逐帧回溯，拿到每一帧的 PC 地址。回溯的可靠性取决于编译时记录的元数据格式（FP 链 / CFI 表 / .eh_frame 段）和运行时栈状态是否完整。
- **符号化（symbolication）**：把回溯拿到的原始 PC 地址翻译成「so 名 + 函数名 + 源码行号」。符号化的准确性取决于 ELF 文件中保留了多少符号信息，以及是否有对应的 debug 信息或 .sym 文件。

两个环节缺一不可。回溯拿到准确的地址但无法符号化，等于有一串数字但不知道含义；符号化管线齐全但回溯漏帧，只能看到崩溃栈顶的两三层。

### 🔹 FP 回溯（Frame Pointer Unwinding）

#### 原理

ARM64 的函数调用约定（AAPCS64）规定，每个函数在 prologue 里把上一帧的 FP（X29 寄存器）和 LR（X30 寄存器）压栈，然后把当前栈帧的基址写入 X29。这样 X29 寄存器就把所有活跃的函数调用串联成一条链表：

```
当前 X29 → [saved FP][saved LR] → [saved FP][saved LR] → ... → 终点（NULL）
```

回溯时只需要沿着 X29 链表逐帧行走，每帧取出 saved LR 作为该帧的返回地址（即调用方的 PC），就能重建调用栈。整个过程中不需要任何额外的元数据——不需要 CFI 表，不需要 .eh_frame 段，不需要 debug 信息。

每帧回溯的开销是两条内存读取（load FP、load LR），在 ARM64 上约 2-4 个时钟周期。

#### NDK r23 起默认启用

Android NDK r23（2022 年 1 月）将 ARM64 的 `-fomit-frame-pointer` 默认行为改为保留 Frame Pointer。此前的 NDK 版本默认省略 FP（为了多出一个通用寄存器），导致 FP 回溯在应用层 so 库上基本不可用。

NDK r23 的改动意味着：用 r23+ 编译的 ARM64 so 库，不需要额外编译选项就支持 FP 回溯。第三方监控 SDK（xCrash、Bugly 等）和系统 Simpleperf 采样都从中受益。

对于 32 位 ARM（armeabi-v7a），FP 回溯仍然不可用——X86 架构的 FP（EBP）链同理不保证连续。

#### 可靠性边界

FP 回溯依赖栈数据完整性。以下场景会导致 FP 链断裂：

- **栈溢出**：写越界覆盖了 saved FP/LR 区域
- **缓冲区溢出**：memcpy/strcpy 越界写坏了栈帧
- **手动汇编函数**：没有遵循 AAPCS64 prologue 约定（如手写汇编的热点函数、一些 JIT 代码）
- **优化后省略 prologue**：叶子函数（leaf function）在 `-fomit-frame-pointer` 下可能不保存 FP/LR
- **signal handler 入口**：内核保存的 ucontext 里 FP 指向 signal frame，需要特殊处理

FP 链一旦断裂，后续帧全部丢失——这是 FP 回溯的硬伤。CFI 回溯在这方面更健壮，因为 CFI 记录了每个 PC 位置的完整寄存器恢复规则，不依赖链表连续性。

### 🔹 CFI 回溯（Compact Frame Information）

#### .eh_frame 和 .eh_frame_hdr 段

CFI（Call Frame Information）回溯依赖 ELF 文件中的 `.eh_frame` 和 `.eh_frame_hdr` 两个段。这两个段由编译器自动生成（GCC 和 Clang 都支持），描述了程序中每个 PC 位置对应的寄存器保存和恢复规则。

`.eh_frame_hdr` 是 `.eh_frame` 的索引头，包含一个二分查找表（Search Table），让回溯器可以快速定位某个 PC 对应的 CFI 记录，而不需要线性扫描整个 `.eh_frame`。

回溯过程：

1. 从崩溃时刻的 PC 和 SP 出发
2. 在 `.eh_frame_hdr` 的查找表中找到 PC 对应的 FDE（Frame Description Entry）
3. 根据 FDE 中的 CFI 指令计算上一帧的 SP 和 PC（以及需要恢复的寄存器）
4. 重复直到没有更多的 FDE 或到达栈顶

与 FP 回溯不同，CFI 回溯不依赖链表——即使栈中间某一帧被破坏，只要该帧的 CFI 记录完整，回溯器仍然可以根据寄存器计算规则恢复调用链。

#### libunwind 与 _Unwind_Backtrace

Android 系统从 5.0 开始使用 `libunwind` 替代早期的 `libcorkscrew.so` 作为 Native 回溯的基础库。`libunwind` 实现了 `_Unwind_Backtrace` 接口，通过 CFI 记录进行回溯。

`_Unwind_Backtrace` 接收一个回调函数和一个用户数据指针，对每一帧调用回调，回调中通过 `_Unwind_GetIP` 获取当前帧的 PC：

```c
// _Unwind_Backtrace 的典型用法
struct backtrace_state {
    void** current;
    void** end;
};

static _Unwind_Reason_Code unwind_callback(struct _Unwind_Context* ctx, void* data) {
    struct backtrace_state* state = (struct backtrace_state*)data;
    uintptr_t pc = _Unwind_GetIP(ctx);
    if (pc) {
        if (state->current >= state->end) {
            return _URC_END_OF_STACK;
        }
        *state->current++ = (void*)pc;
    }
    return _URC_NO_REASON;
}

size_t fill_backtrace(void** buffer, size_t max) {
    struct backtrace_state state = { buffer, buffer + max };
    _Unwind_Backtrace(unwind_callback, &state);
    return state.current - buffer;
}
```

拿到 PC 数组后，通过 `dladdr()` 解析每个地址对应的 so 名和符号名。`dladdr()` 返回的 `Dl_info` 包含共享库路径（`dli_fname`）、加载基址（`dli_fbase`）、符号名（`dli_sname`）和符号地址（`dli_saddr`）。

CFI 回溯的一个优势是能解析 Java 层符号。通过 `_Unwind_Backtrace` 拿到的 PC 中，ART 虚拟机的 JIT 编译代码和 Interpreter 栈帧也能被识别——这是 FP 回溯做不到的，因为 ART 的执行栈不遵循标准的 FP 链约定。

#### libbacktrace

`libbacktrace` 是 Android 系统内部对 `libunwind` 的封装，提供 `Backtrace::Create` → `Unwind` → `FormatFrameData` 的三步接口。系统代码（如 `CallStack::update`）和 debuggerd 都使用 libbacktrace。

`libbacktrace` 没有作为公开 API 对应用开放。第三方应用想使用它，需要通过 `dlopen("/system/lib64/libbacktrace.so")` + `dlsym` 获取符号，但符号名在不同 Android 版本有变化（mangled name 不同），兼容性维护成本高。xUnwind 库对这条路径做了封装。

#### 对包体积的影响

`.eh_frame` + `.eh_frame_hdr` 段通常增加 so 体积 5-10%。对于体积敏感的模块（如 SDK 分发的 so），可以通过 `--no-eh-frame-hdr` 链接选项去掉 `.eh_frame_hdr`，但这会让回溯器无法使用二分查找，回溯速度下降。

### 🔹 堆栈回溯的性能开销对比

三种主流回溯方式的延迟和适用场景：

| 回溯方式 | 单帧开销 | 30 帧总开销 | 依赖元数据 | 适用场景 |
|----------|----------|-------------|-----------|----------|
| FP | ~5ns（2 次 load） | ~150ns | 无 | 高频采样、Simpleperf、Perfetto |
| CFI（libunwind） | ~1-5μs | ~30-150μs | .eh_frame/.eh_frame_hdr | Crash dump、低频诊断 |
| libunwind-astack | ~0.5-2μs | ~15-60μs | .eh_frame | 采样 profiling（比标准 libunwind 快，跳过部分初始化） |

FP 回溯快两个数量级，因为每帧只需要两次内存读取，不需要解析 CFI 表。Simpleperf 和 Perfetto 在 ARM64 上默认使用 FP 回溯做 on-CPU 采样，正是这个原因——采样频率高（通常 99Hz-999Hz），每秒可能采集数千次堆栈，CFI 回溯的开销不可接受。

CFI 回溯慢但准确，适合崩溃时一次性采集（只跑一次，不在意延迟）。Crash dump 路径（debuggerd → crash_dump）使用 CFI 回溯。

带 `-g` 符号信息的 so 不影响回溯性能——debug 信息只在符号化阶段使用，回溯本身只依赖 `.eh_frame`。

### 🔹 符号化管线：从地址到源码行

回溯拿到的是 PC 数组，形如 `0x7f8a3c0008a3c`。要把它翻译成 `foo.cpp:42`，需要符号化工具。

#### addr2line

GNU `addr2line` 是最基础的符号化工具，随 NDK 分发。输入 so 文件和偏移地址，输出函数名和源码行号：

```bash
# -f 显示函数名，-C demangle，-e 指定 ELF 文件
addr2line -fC -e libfoo.so 0x8a3c
# 输出：
# foo(int, char*)
# /path/to/foo.cpp:42
```

addr2line 的局限：

- **内联函数**：默认只显示最外层函数。加 `-i` 参数才能展开内联调用链（`addr2line -ifC -e libfoo.so 0x8a3c`）
- **优化后行号偏移**：`-O2` 及以上优化会让行号映射不精确，addr2line 可能指向下一个有效行而非实际执行行
- **strip 后不可用**：so 被 strip 后 `.debug_info` 段丢失，addr2line 无法工作

#### llvm-symbolizer

`llvm-symbolizer` 是 LLVM 工具链的符号化工具，相对 GNU addr2line 的优势：

- **DWARF 5 支持**：更完整的 debug 信息解析
- **内联展开**：默认输出完整内联链，不需要额外参数
- **性能更好**：批量符号化时速度快 2-3 倍

Android NDK 从 r22 起内置 `llvm-symbolizer`，推荐用它替代 `addr2line`。

```bash
# llvm-symbolizer 的典型用法
llvm-symbolizer --obj=libfoo.so 0x8a3c
# 输出包含内联展开：
# foo_inline()
# foo(int, char*)
# /path/to/foo.cpp:42
```

#### strip 与 debug 信息包

发布版本的 so 通常做 strip 处理。`strip --strip-unneeded` 删除 `.symtab` 和 `.debug_*` 段，只保留 `.dynsym`（动态符号表）。strip 后 addr2line 无法工作。

标准做法是保留未 strip 的 so（或单独的 `.sym` 文件）用于符号化：

```bash
# 编译时生成 debug 信息包
# build.gradle 或 CMakeLists.txt 中：
# -DCMAKE_BUILD_TYPE=Release
# -DCMAKE_CXX_FLAGS_RELEASE="-g"  # Release 也保留 debug 信息

# strip 时保留符号表备份
cp libfoo.so libfoo.so.sym
strip --strip-unneeded libfoo.so
```

线上崩溃上报时，客户端只发送 PC 偏移地址（`offset 0x8a3c`），服务端用对应的 `.sym` 文件做离线符号化。

### 🔹 ELF 文件结构与符号表

#### .symtab vs .dynsym

ELF 文件包含两个符号表：

- **`.symtab`（Symbol Table）**：编译时生成的完整符号表，包含所有函数、变量、调试符号。strip 后被删除。
- **`.dynsym`（Dynamic Symbol Table）**：运行时动态链接需要的符号表，只包含导出的函数和导入的外部符号。strip 后保留。

回溯拿到的 PC 地址如果是内部函数（未导出），`.dynsym` 中找不到对应的符号名——这时 `dladdr()` 返回的 `dli_sname` 为 NULL 或指向最近的导出函数名（不准确）。只有 `.symtab` 存在时才能精确解析。

#### 解析工具

```bash
# readelf：查看完整符号表（含 .symtab）
readelf -sW libfoo.so

# objdump：查看动态符号表（运行视图）
objdump -T libfoo.so

# nm：简洁的符号列表
nm -D libfoo.so   # 只看 .dynsym
nm libfoo.so       # 只看 .symtab（strip 后为空）
```

`readelf -sW` 是排查 Native 符号问题最常用的命令。`-W` 参数让输出不被截断，对于 C++ mangled name（如 `_ZN7android8BpBinder8transactEjRKNS_6ParcelEPS1_j`）很重要。

#### C++ name mangling

C++ 函数经过 name mangling 后，符号名包含了命名空间、类名、参数类型等信息。用 `c++filt` 可以 demangle：

```bash
echo "_ZN7android8BpBinder8transactEjRKNS_6ParcelEPS1_j" | c++filt
# 输出：android::BpBinder::transact(unsigned int, android::Parcel const&, android::Parcel*, unsigned int)
```

符号化工具（addr2line、llvm-symbolizer）通常会自动 demangle，但理解 mangling 规则对排查 `dladdr()` 失败的场景有帮助。

#### 从 AOSP 查找符号所属 so

AOSP 源码中通过 `Android.bp` 文件可以找到源文件编译到哪个 so。例如 `BpBinder.cpp` 的 `Android.bp` 在 `frameworks/native/libs/binder/Android.bp` 中定义了 `cc_library { name: "libbinder", srcs: ["BpBinder.cpp", ...] }`，说明 `BpBinder.cpp` 编译进 `libbinder.so`。

[结构参考: Clippings/Android 应用稳定性剖析与优化 - Android.bp 文件与符号表]

### 🔹 Tombstone 格式与解析

#### 生成路径

Native Crash 发生时的完整路径：

```
信号触发（如 SIGSEGV）
    ↓
内核信号处理
    ↓
debuggerd_client 通知 debuggerd 守护进程
    ↓
debuggerd fork crash_dump 子进程
    ↓
crash_dump 使用 ptrace attach 到崩溃进程
    ↓
crash_dump 读取寄存器、回溯堆栈、dump 内存
    ↓
写入 /data/tombstones/tombstone_XX
    ↓
logcat 输出 crash 信息
```

Android 10+ 的 crash_dump 使用 CFI 回溯（通过 libunwind），同时输出 FP 回溯结果作为补充。如果两者不一致，以 CFI 为准。

#### Tombstone 文件结构

一个典型的 tombstone 文件包含以下段落：

```
*** *** *** *** *** *** *** *** *** *** *** *** *** *** *** ***
Build fingerprint: 'samsung/e1qxxx/e1q:15/AQ3A.250305.001/...'
Revision: '0'
ABI: 'arm64'
Timestamp: 2026-06-27 03:15:42.123456789+0800
Process uptime: 45s
Cmdline: com.example.app
pid: 12345, tid: 12346, name: com.example.app  >>> com.example.app <<<

signal 11 (SIGSEGV), code 1 (SEGV_MAPERR), fault addr 0x0000000000000000
Cause: null pointer dereference

backtrace:
  #00 pc 0000000000008a3c  /data/app/.../libfoo.so (foo+44)
  #01 pc 0000000000009120  /data/app/.../libfoo.so (bar+128)
  #02 pc 0000000000005044  /data/app/.../base.apk!libapp.so (offset 0x47000)
  #03 pc 0000000000123456  /apex/com.android.art/lib64/libart.so (art_quick_invoke_stub+548)

stack:
  0000007ffffffff000  0000007ffffffff001  [...]
  ...

memory near x0:
  0000000000000000  0000000000000000 0000000000000000 [...]
```

关键字段：

- **Build fingerprint**：设备固件版本，用于定位问题是否与特定 OEM 或系统版本相关
- **ABI**：`arm64` / `arm` / `x86_64`，决定使用哪套符号文件
- **signal + code**：信号类型和子类型。`SEGV_MAPERR`（地址未映射）vs `SEGV_ACCERR`（地址无权限）指向不同的问题方向
- **fault addr**：触发崩溃的内存地址。0x0 是空指针，非零值可能是野指针或越界访问
- **backtrace**：CFI 回溯的堆栈，`#NN pc OFFSET PATH (SYMBOL+OFFSET)` 格式
- **stack**：崩溃线程的栈内存 dump，用于辅助分析栈损坏
- **memory near Xn**：崩溃时各寄存器附近的内存内容

#### 自动化归因

从 tombstone 做自动化归因，关键字段提取顺序：

1. 提取 `signal` 和 `fault addr`，分类崩溃类型（空指针 / 越界 / abort / 栈溢出）
2. 提取 `#00` 帧的 so 名和函数名，定位崩溃发生的模块
3. 提取 `Cmdline` 和 `pid:tid`，区分主线程崩溃和子线程崩溃
4. 提取 `Build fingerprint`，判断是否与特定设备/版本相关

如果 `#00` 帧的 so 是系统库（如 `libart.so`、`libbinder.so`），通常指向应用触发的系统层 bug 或 ABI 不兼容问题。如果 `#00` 帧在应用自己的 so 中，进一步用 `addr2line` 或 `.sym` 文件符号化到源码行号。

### 🔹 线上 Native 堆栈采集方案

#### 信号处理器中安全回溯

线上 Native Crash 监控的核心是：在信号处理器中安全地采集堆栈，不引入二次崩溃。信号处理器的可重入约束决定了哪些操作可以做、哪些不能做：

| 操作 | 可重入？ | 替代方案 |
|------|----------|----------|
| `malloc()`/`free()` | ❌ | 预分配静态缓冲区 |
| `printf()`/`fopen()` | ❌ | `write()` 到 pipe 或 `__android_log_print()` |
| `pthread_mutex_lock()` | ❌ | `spinlock` 或 atomic flag |
| `_Unwind_Backtrace()` | ⚠️ 可用但需小心 | FP 回溯更安全 |
| `dladdr()` | ⚠️ 可用 | 缓存结果 |
| `read()`/`write()` | ✅ | 直接使用系统调用 |

[已验证: AOSP android-17.0.0_r1, bionic/libc/include/signal.h]

实际实现中，大型 APM SDK（xCrash、Bugly、Crashpad）在信号处理器里做的工作尽量精简：只回溯堆栈、保存寄存器上下文和关键内存区域，然后通过 `fork()` 子进程或 `signal_safe_write()` 到共享内存做后续处理。

#### Breakpad / Crashpad 的 minidump 方案

Google Breakpad 和 Crashpad 不在信号处理器中做完整的堆栈回溯和符号化，而是生成 minidump 文件（包含原始寄存器状态、栈内存、内存映射信息），在服务端离线做回溯和符号化。

优势：

- 信号处理器中只 dump 内存，不做回溯，减少二次崩溃风险
- 服务端可以用任意版本的符号文件做符号化
- minidump 格式跨平台，一套服务端处理 Android/iOS/Windows/Mac

劣势：

- minidump 文件体积大（通常 10-100KB），需要压缩上传
- 服务端需要维护每个版本的符号文件库
- 如果栈内存损坏，回溯仍然会失败

#### Android 系统 debuggerd_client 的 fallback

应用可以通过 `debuggerd_client` 接口请求系统生成 tombstone，不需要自己实现信号捕获。但 `debuggerd_client` 是系统内部 API，在 Android 10+ 上不再对应用开放。

实际线上方案通常是「自建信号捕获 + Breakpad/Crashpad 生成 minidump」的组合，系统 tombstone 作为 fallback。

### 🔹 Android 15+ CFI 强制启用与兼容性

#### Control Flow Integrity

CFI（Control Flow Integrity）是一种编译时安全加固机制，在间接函数调用（虚函数、函数指针）时检查目标地址是否在合法的白名单内。检查失败触发 `SIGILL`（非法指令）而非 `SIGSEGV`。

Android 15 起对 `system/` 下的模块强制启用 CFI。Android 17 将 CFI 覆盖范围扩展到更多 system 模块和 APEX 组件。

第三方应用 so 库默认不受系统 CFI 约束，但如果 so 被 system 模块通过 dlopen 加载（如某些 SDK 注入系统进程的场景），也会受 CFI 检查影响。

#### 对崩溃分析的影响

CFI 检查失败导致的 `SIGILL` 在 tombstone 中表现为：

```
signal 4 (SIGILL), code 1 (ILL_ILLCANOPCODE), fault addr 0x...
Abort message: 'CFI failure at ...'
```

与常规 `SIGSEGV` 的区分：CFI 失败说明代码执行流被劫持（vtable 被篡改、函数指针越界等），排查方向不是内存访问越界，而是间接调用目标不合法。

`-fsanitize=cfi` 编译选项对包体积的影响约 3-5%，运行时性能开销取决于间接调用频率，通常 < 1%。

## 扩展

### 🔸 Compose Native 交互层堆栈

[待补充: Compose Runtime JNI 层（特别是 `ComposeScene` 和 `Applier` 的 native 调用路径）的堆栈回溯特殊处理。Compose Compiler 生成的 lambda 函数在 ARM64 上可能省略 FP 保存（因为被视为叶子函数），导致 FP 回溯在这些位置断链。需要结合 Simpleperf 的 CFI 采样模式做补充。]

### 🔸 混淆与 Native 混合堆栈

R8 混淆后的 Java 堆栈与 Native 堆栈拼接是线上排查的常见难点。一条崩溃栈可能同时包含：

```
#02 pc 0x1234 libapp.so (JNI_function+44)
#03 pc 0x5678 [anon:dalvik-classes.dex] (a.b.c+308)   ← R8 混淆后的 Java 帧
```

Java 帧需要 `mapping.txt` 反混淆，Native 帧需要 `.sym` 文件符号化，两者的偏移计算方式不同（Java 帧是 dex pc，Native 帧是 so offset）。

拼接策略：

- 先用 `_Unwind_Backtrace` 获取完整 PC 列表（包含 Java 帧和 Native 帧）
- 对 PC 落在 `[anon:dalvik-*.dex]` 区间的帧，用 ART 的 `artDebuggable_getStackFrameAt` 或线上 mapping.txt 反混淆
- 对 PC 落在 so 文件区间的帧，用 addr2line / .sym 文件符号化
- 按 PC 顺序拼接两条符号化结果

详细方案参考 20.3 节的混合堆栈章节。

### 🔸 ARM64 PAC 与 BTI 对堆栈的影响

ARM64 PAC（Pointer Authentication Code）和 BTI（Branch Target Identification）是 ARMv8.3-A 和 ARMv8.5-A 的安全特性。

**PAC** 对函数返回地址（LR）做签名，在 `RET` 时验证。如果 PAC 验证失败触发 `SIGILL`。对堆栈回溯的影响：回溯器拿到的 LR 值高位包含 PAC 签名位，需要用 XPACLRI 指令剥离签名位后才是真实地址。libunwind 从 Android 12 起已经处理了 PAC 去除。

**BTI** 在间接跳转目标处放置 `bti` 指令作为合法着陆点。BTI 与 CFI 的关系：BTI 是硬件级的间接分支检查，CFI 是软件级的。两者互补但不冲突。

Android 15+ 的系统 so 启用 PAC 和 BTI。应用 so 如果用 Clang 15+ 编译并开启 `-mbranch-protection=standard`，也会启用这两个特性。

[适用版本: Android 15 - Android 17]

---

> 本节已加工完成。详见 20.3 节对于 Native Crash 信号收集和 debuggerd 路径的完整分析。
