---
title: "Native Crash 分析与治理"
chapter: "20.3"
section: "20.3"
section_title: "Native Crash 分析与治理"
status: "finalized"
applicable_versions: "Android 10 (API 29) - Android 16 (API 36)"
last_verified: "2026-05-11"
last_verified_against: "AOSP android-16.0.0_r1"
confidence: medium
drafted_date: "2026-05-11"
polish_count: 0
sources:
  - type: aosp
    path: "system/core/debuggerd/crash_dump.cpp"
  - type: aosp
    path: "art/sigchainlib/sigchain.cc"
  - type: aosp
    path: "art/runtime/fault_handler.cc"
  - type: aosp
    path: "system/core/debuggerd/handler/debuggerd_handler.cpp"
  - type: aosp
    path: "system/core/debuggerd/libdebuggerd/tombstone.cpp"
  - type: aosp
    path: "external/google-breakpad/src/processor/simple_symbol_supplier.cc"
  - type: aosp
    path: "external/google-breakpad/src/processor/basic_source_line_resolver.cc"
tags: [native-crash, tombstone, signal, breakpad, symbolication, debuggerd]
related_chapters: ["20.1", "20.2", "1.15"]
pipeline_stage: "task6_pending"
task6_state: "revisiting"
task6_result: "pass-light-edit"
task9_state: "reviewed"
task9_result: "auto-fixed"
task9_reviewed_date: "2026-06-21"
task9_reviewed_by: "openclaw-task9"
last_task9_at: "2026-06-21T16:27:03+08:00"
task2b_state: "fixed"
task2b_result: "fixed"
last_task2b_at: "2026-06-01T12:50:00+08:00"
task2b_notes: "2026-06-01 Task2B fallback: 修复 ApplicationExitInfo tombstone protobuf 边界、Breakpad 源码锚点、JNI native resolve 口径、CFI/Java frame、Crashpad handler 与 mooner 安全边界。"
reviewed_by: "openclaw-task6"
reviewed_date: "2026-06-01"
last_task6_at: "2026-06-01T18:10:00+08:00"
last_task6_audit: "2026-06-09"
task6_reviewed_by: "openclaw-task6"
task6_reviewed_at: "2026-05-19T20:25:44+08:00"
last_task6_review_log: "logs/review/2026-06-01-18-review.md"
task6_review_notes: "2026-06-01 18 Task6 revisiting-review: pass-light-edit。修正 C++ 异常 typo 与英文所有格表达；L1/L2 通过，无新增回炉项，送 Task9 复核。"
last_task9_review_log: "logs/deep-review/2026-06-21-16-audit.md"
task9_review_notes: "2026-06-21 Task9 idle-audit：auto-fixed。Android 17/API 37 源码抽检发现 native crash 通知链路方法名不准；已将 AppErrors.crashApplication()/handleApplicationCrash() 修正为 NativeCrashListener -> handleApplicationCrashInner()，回到 Task6 复审。"
last_task9_autofix_at: "2026-06-21"
deepseek_cn_review_state: done
last_deepseek_cn_review_at: 2026-06-13
last_task9_audit: "2026-06-21"
---

# Native Crash 分析与治理

Native Crash 与 Java Crash 的区别：Java Crash 的异常信息由 ART 虚拟机在进程内部生成，调用栈完整、格式统一；Native Crash 由 Linux 信号触发，堆栈解析依赖独立的崩溃收集机制，排查路径更长。

在 Perfetto 分析或线上故障排查时，我们经常遇到这样的情况：一个应用突然崩溃，但 crash 堆栈只有一行 `SIGSEGV`，或者 Native 代码抛出的异常在 Java 层完全看不到痕迹。如果不知道 Native Crash 的收集机制和解读方法，这些崩溃就像黑盒一样，很难定位问题原因。

分析 Native Crash 时，四条线最容易影响定位效率：信号怎么产生、tombstone 怎么读、堆栈怎么还原到源码行号、线上监控怎么搭。掌握这几条线，排查时就不必只盯着系统生成的 tombstone 文件。

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 **信号与收集路径**：说明 SIGSEGV、SIGABRT、SIGBUS 等信号如何进入 SignalChain、debuggerd 和 crash_dump
- 🔹 **tombstone 解读**：覆盖头部信息、寄存器、backtrace、stack dump 和线上获取路径
- 🔹 **符号化链路**：说明 addr2line、ndk-stack、Breakpad `.sym` 文件、目录查找协议和 minidump_stackwalk 流程
- 🔹 **常见崩溃模式**：区分空指针、野指针、SIGABRT、SIGBUS 与 JNI 边界崩溃的排查方向
- 🔹 **线上监控方案**：比较系统 tombstone、Breakpad、第三方 SDK、APM 信号捕获策略的边界
- 🔹 **线程级安全点**：说明 sigsetjmp/siglongjmp、mooner、ByteHook、shadowhook 和 mutex use-after-destroy 检测

### 扩展（可选深入）

- 🔸 **符号文件治理**：CI 归档未 strip so、Build ID 查找、服务端离线符号化
- 🔸 **交叉引用**：JNI 类型安全与异常边界问题回到 §1.15 展开
<!-- outline-end -->

## Linux 信号机制与 Native 崩溃产生流程

### 信号是内核对进程的通知

Linux 信号是一种异步通知机制。当硬件异常（非法内存访问、除零）、软件条件（`abort()` 调用、`raise()` 发送）或外部事件（`kill` 命令）发生时，内核向目标进程投递一个信号编号。

Android 上常见的崩溃信号：

| 信号 | 编号 | 典型触发原因 |
|------|------|-------------|
| SIGSEGV | 11 | 访问未映射内存、写只读页、解引用野指针/空指针 |
| SIGABRT | 6 | `abort()` 调用、`assert()` 失败、`__android_log_assert()` |
| SIGBUS | 7 | 未对齐的内存访问（ARM 上少见但存在）、映射文件被截断 |
| SIGFPE | 8 | 整数除零（浮点除零通常返回 NaN，不触发信号） |
| SIGTRAP | 5 | 断点指令、`__builtin_trap()`、调试器中断 |


### Android 的信号处理链：SignalChain 机制

Android 应用进程中，信号处理不是直接注册到 Linux 内核，而是经过了 ART 虚拟机的 **SignalChain** 机制拦截。

SignalChain 的核心设计：维护一个信号处理器的链表，保证 ART 虚拟机自身的异常处理（如 null pointer 的隐式 null 检查优化）优先于应用注册的信号处理器。链表结构：

```text
chains[SIGSEGV] → [art::HandleSigsegvFault] → [应用注册的 handler 1] → [应用注册的 handler 2] → ...
```

`art_sigsegv_handler` 在链头（位置 0），负责处理 ART 优化产生的隐式空指针检查。如果判断不是 ART 内部异常，通过 `InvokeUserSignalHandler()` 传递给下一个 handler。

SignalChain 的拦截发生在 `sigaction()` 调用时：应用通过 JNI 调用的 `sigaction()` 实际执行的是 `art/sigchainlib/sigchain.cc` 中的包装函数，而非直接调用 libc 的 `sigaction`。这个包装函数将新的 handler 追加到链表末尾。


### 崩溃收集流程：debuggerd → crash_dump

当信号到达且没有被任何 handler 拦截（或 handler 选择传递），Android 的崩溃收集流程启动：

1. **debuggerd signal handler**（`system/core/debuggerd/handler/debuggerd_handler.cpp`）在崩溃进程内被触发，创建 pseudothread，然后 `_Fork()` + `execle(CRASH_DUMP_PATH, ...)` 直接 fork+exec 出 `crash_dump` 子进程
2. `crash_dump` 连接 **tombstoned** 守护进程获取输出 fd，通过 `ptrace` attach 回崩溃进程，读取寄存器状态和内存映射
3. `crash_dump` 使用 `libunwindstack` 回溯调用栈，收集所有线程的堆栈并生成 tombstone
4. tombstone 通过 tombstoned 写入 `/data/tombstones/`
5. `crash_dump` 通过 `/data/system/ndebugsocket` 通知 **ActivityManagerService** 中的 `NativeCrashListener`，再由 AMS 的 `handleApplicationCrashInner()` 处理（不经过 Java 层的 `UncaughtExceptionHandler`——Native Crash 走的是 AMS → CrashDialog / kill 进程路径）

`ptrace` + 独立进程的设计是关键：崩溃进程的内存空间可能已经损坏，如果在进程内部做堆栈回溯，可能二次崩溃。`crash_dump` 通过 `ptrace` 从外部读取，安全性更高。pseudothread 机制保证崩溃线程在 fork+exec 期间不会阻塞在信号处理上下文中。


## Tombstone 结构解读

### 一份完整的 tombstone 长什么样

tombstone 文件位于 `/data/tombstones/`，每个 Native Crash 生成一个，文件名格式 `tombstone_XX`（XX 从 00 到 09 循环覆盖）。一份典型的 tombstone 包含以下部分：

```text
*** *** *** *** *** *** *** *** *** *** *** *** *** *** *** ***
Build fingerprint: 'samsung/beyond1qlzh/beyond1q:15/AP3A.241005.015/S10...'
Revision: '12'
ABI: 'arm64'
Timestamp: 2026-04-15 14:23:01.123456789+0800
pid: 12345, tid: 12367, name: Thread-7  >>> com.example.app <<<
uid: 10234
signal 11 (SIGSEGV), code 1 (SEGV_MAPERR), fault addr 0x0000000000000000
Cause: null pointer dereference
    x0  0000000000000000  x1  0000007ffe123456  x2  0000000000000004
    x3  0000000000000000  x4  0000000000000000  x5  0000000000000000
    x6  0000007ffe123460  x7  0000007ffe123468
    x8  0000000000000000  x9  0000000000000010  x10 0000000000000000
    ...
    x29 0000007ffe123800  x30 (lr) 0000007abc123456
    sp  0000007ffe1237f0  pc  0000007abc123400  pstate 0000000060000000

backtrace:
      #00 pc 0000000000123400  /data/app/.../libnative.so!libnative.so (offset 0x100000) (Java_com_example_NativeLib_process+128)
      #01 pc 000000000013ced4  /apex/com.android.art/lib64/libart.so (art_quick_generic_jni_trampoline+148)
      #02 pc 0000000000133564  /apex/com.android.art/lib64/libart.so (art_quick_invoke_stub+548)
      ...

stack:
      #00  0000007ffe1237f0  0000000000000000  ???
      #00  0000007ffe1237f8  0000007abc123456  /data/app/.../libnative.so!libnative.so
      ...
```

### 关键字段逐行解读

**头部信息**：

- `pid/tid/name`：崩溃进程 ID、线程 ID、线程名。注意 `name` 后面的 `>>> com.example.app <<<` 是进程的包名——多进程应用通过这个字段区分是主进程还是子进程
- `signal`：信号编号和原因码。`SEGV_MAPERR` 表示访问了未映射的地址（通常是空指针或已释放的内存）；`SEGV_ACCERR` 表示访问权限错误（写只读页）
- `fault addr`：触发异常的虚拟地址。`0x0000000000000000` 是空指针解引用的典型值；如果是一个非零小值（如 `0x0000000000000010`），通常是对 null 结构体字段的偏移访问（`ptr->field`，其中 `ptr == NULL`，`field` 偏移 16 字节）

**寄存器**：

- `pc`（Program Counter）：崩溃时的执行地址，用于定位出问题的代码行
- `lr`（Link Register / x30）：函数返回地址，帮助理解调用来源
- `x0-x7`：ARM64 的前 8 个参数寄存器，用来确认传给崩溃函数的参数值
- `sp`（Stack Pointer）：栈指针，配合 stack dump 分析栈上数据

**backtrace**：

- `pc` 后面的偏移量是相对 so 加载基地址的偏移，不是文件偏移
- 括号中的 `+128` 是相对函数入口的偏移字节数
- `!libnative.so (offset 0x100000)` 表示该 so 在 APK 中的文件偏移（APK 内嵌 so 的情况）

**stack**：

- 栈内存的 hex dump，每行显示地址、内容、所属 so。栈上残留的指针可以帮助追踪调用链中已返回的函数

### 线上获取 tombstone 的途径

- **adb**：`adb bugreport` 包含最近的所有 tombstone
- **API 30+**：`ActivityManager.getHistoricalProcessExitReasons()` 返回 `ApplicationExitInfo`，可用于确认进程退出原因、时间、PSS/RSS 等元数据；API 31+ 的 `REASON_CRASH_NATIVE` 才能通过 `getTraceInputStream()` 读取 native tombstone 数据。该接口返回 tombstone protobuf 输入流，不提供 tombstone 文本原文；底层历史记录可能被系统循环缓冲覆盖，调用方要处理 `null`。
- **dropbox**：系统将 tombstone 同时写入 `dropbox`（`adb shell dumpsys dropbox --print` 可查看）


## 堆栈还原与符号化

tombstone 中的 backtrace 只有 `pc` 偏移和函数名（可能被 strip 掉）。还原到源码行号需要**符号化**。

### 三种堆栈回溯方式

Android 上 Native 堆栈获取有三种底层机制：

| 方式 | 全称 | 特点 |
|------|------|------|
| CFI | Call Frame Information | 写在 `.eh_frame` 段中，用于 native 栈帧解卷，速度较慢但覆盖面较好 |
| EH | Exception Handling (GCC) | 编译器生成的异常处理信息，速度较快 |
| FP | Frame Pointer | ARM64 上可用，依赖 `x29`（fp）寄存器，速度最快但编译优化可能省略 fp |

`debuggerd/crash_dump` 的 native 栈解卷依赖 `libunwindstack` 读取 CFI、EH 或 FP 信息；Java / Dex / JIT / interpreter 帧由 `libunwindstack` 结合 ART runtime、Dex/JIT 元数据和 maps 信息识别，不能归因给 `.eh_frame` 符号化。排查混合栈时，要把 native so 的行号还原和 Java 方法帧解析分开看。


### addr2line / ndk-stack 实战

**addr2line** 将 pc 偏移转换为源文件和行号。使用未 strip 的 so 文件：

```bash
# NDK 中的 addr2line（路径根据 NDK 版本和架构调整）
$NDK/toolchains/llvm/prebuilt/darwin-x86_64/bin/llvm-addr2line \
  -e libnative.so \
  -f -C 0x12340
```

参数说明：
- `-e`：指定 so 文件（必须是带符号的版本，不是 strip 后的）
- `-f`：显示函数名
- `-C`：demangle C++ 符号名（`_ZN3foo3barEi` → `foo::bar(int)`）

**ndk-stack** 是 addr2line 的批处理封装，直接解析 tombstone 文件：

```bash
# 从文件解析
$NDK/ndk-stack -sym /path/to/symbols/ -dump tombstone_00

# 从 adb logcat 实时解析
adb logcat | $NDK/ndk-stack -sym /path/to/symbols/
```

`-sym` 参数指向包含未 strip so 文件的目录。Android Studio 构建的符号文件通常在 `app/build/intermediates/merged_native_libs/` 或 `app/build/intermediates/cxx/` 下。

**符号文件管理**：CI 流水线中，每次构建保留未 strip 的 so 文件，以构建号或版本号命名归档。线上 crash 上报时，用对应版本的符号文件做符号化。如果符号文件丢失，对应版本的 Native Crash 堆栈无法还原到行号。


### Breakpad 符号文件（.sym）生成与查找协议

tombstone 中的 backtrace 需要通过符号文件才能还原到源码行号。Android 崩溃监控体系使用的是 **Breakpad 符号文件格式**，这套机制包含三个核心环节：**符号生成**、**目录布局**、**离线符号还原**。

#### 符号生成：`dump_syms`

**源码位置**：`external/google-breakpad/src/tools/linux/dump_syms/dump_syms.cc`（AOSP 内置为 host_tool）

`dump_syms` 是 Breakpad 提供的 host 端工具，从未 strip 的 ELF（.so）中提取调试信息，输出为纯文本符号文件。Android.bp 中的构建定义（行 134）标注为 `dump_syms host tool`。

```bash
# 用法（host 上运行，不在 Android 设备上）
./dump_syms path/to/libnative.so

# 输出到 stdout：
MODULE Linux arm64 DA7778FB66018A4E9B4110ED06E730D00 libnative.so
FILE 0 /path/to/NativeLib.cpp
FILE 1 /path/to/Utils.cpp
FUNC 41420 18 0 _ZN7Native9processEv
PUBLIC 41510 0 _ZN7NativeC1Ev
...
```

第一行 MODULE 描述符的格式：`MODULE <os> <arch> <debug-id> <debug-file>`。其中 `<debug-id>` 是 Build ID 的 hex 表达（Breakpad 称为 debug identifier），Android/Linux 上使用 ELF `.note.gnu.build-id` 段内容；`<debug-file>` 是模块文件名。

#### 符号文件格式

**源码位置**：`external/google-breakpad/docs/symbol_files.md`（AOSP 内置，Breakpad 官方文档）

每行一个记录类型：

| 记录类型 | 格式 | 含义 |
|----------|------|------|
| `MODULE` | `MODULE <os> <arch> <debug-id> <debug-file>` | 文件头，每个 .sym 一个 |
| `FILE` | `FILE <file-id> <file-path>` | 源码文件表 |
| `FUNC` | `FUNC <addr> <size> <param-size> <name>` | 函数起始地址、大小、MANGLED 名 |
| `<addr>` | `<addr> <param-size> <line> [<file-id>:<line>]` | FUNC 后续行：偏移→行号映射 |
| `PUBLIC` | `PUBLIC <addr> <param-size> <name>` | 导出的零参数函数 |
| `STACK CFI` | `STACK CFI <addr> ...` | 栈帧解卷信息（对应 .eh_frame 段） |

真实 .sym 文件样本（来自 AOSP 测试数据）：

```text
MODULE Linux arm DA7778FB66018A4E9B4110ED06E730D00 breakpad_unittests
FILE 0 /s/clank/src/.../crash_generation_client.cc
...
FUNC 3141e 4 141 51
3141e 4 161 51
FUNC 31424 1c 0 google_breakpad::synth_elf::SymbolTable::~SymbolTable
31424 4 161 51
```

#### 目录结构与查找协议

符号文件必须按固定目录层次存放，这是 `minidump_stackwalk` 和 `minidump_dump` 工具的查找协议：

```text
symbols/
  libnative.so/
    DA7778FB66018A4E9B4110ED06E730D00/
      libnative.so.sym
  libart.so/
    ABCDEF1234567890ABCDEF1234567890/
      libart.so.sym
```

**查找协议**：`<module-name>/<debug-id-from-MODULE>/<module-name>.sym`。`<debug-id>` 必须是符号文件 MODULE 行中的完整十六进制序列（如 `DA7778FB66018A4E9B4110ED06E730D00` 是 32 位 hex），不应截断为固定 16 字符。Breakpad symbol_files.md 只要求 MODULE id 是用于精确匹配模块的十六进制序列；Chrome/Cronet 有独立的 build-id 格式转换逻辑（将 160 bit ELF module ID 压缩到 128 bit），不能泛化为所有 Android 场景的截断规则。

Build ID 格式转换逻辑在 `external/cronet/stable/base/profiler/module_cache.cc`（行 36-43）：Android 和 Linux Chrome builds 使用 breakpad 格式索引 build id，需要将 160 bit 的 Linux ELF module ID 压缩到 128 bit 以匹配 Breakpad 输出。这是 Chrome/Cronet 特定的实现，不是 Breakpad 通用协议。

#### minidump 符号还原流程

**源码位置**：`external/google-breakpad/src/processor/simple_symbol_supplier.cc` 中的 `SimpleSymbolSupplier::GetSymbolFileAtPathFromRoot()` 负责从 `<module>/<debug-id>/<module>.sym` 路径查找符号文件；`external/google-breakpad/src/processor/basic_source_line_resolver.cc` 中的 `BasicSourceLineResolver::Module::LookupAddress()` 负责把模块内偏移映射到函数和源码行。

1. **读取 minidump**：解析 `.dmp` 文件中的 `MDRawModuleList`，获取每个模块的 base_addr 和 build_id
2. **匹配符号文件**：`SimpleSymbolSupplier::GetSymbolFileAtPathFromRoot()` 用 build_id 在 `symbols/` 下查找 `<module>/<build-id>/<module>.sym`
3. **计算段内偏移**：崩溃地址（绝对地址）− 模块 base_addr = 段内偏移
4. **查询 FUNC/PUBLIC**：`BasicSourceLineResolver::Module::LookupAddress()` 查找包含该偏移的 FUNC 记录；如果无匹配，再查找 PUBLIC 记录
5. **查询行号**：在 FUNC 后续行中查找匹配偏移，返回源码文件和行号

这个流程是 `minidump_stackwalk` 工具在 server 端离线执行的。设备上 `crash_dump` 生成 tombstone 时只记录 pc 偏移，符号化在 host 端完成。

### breakpad / crashpad 集成

Google Breakpad 是跨平台的崩溃收集库，Android 上主要用于应用层自主捕获 Native Crash（不依赖系统的 `debuggerd`）。

**Breakpad 的工作流程**：

1. **初始化**：`ExceptionHandler` 注册信号处理器，捕获 SIGSEGV、SIGABRT 等信号
2. **崩溃时**：在信号处理器中通过 `libunwind` 或 CPU 寄存器直接遍历栈帧，收集 pc 值列表
3. **生成 minidump**：将 pc 列表、寄存器值、系统信息写入 minidump 文件（`.dmp` 格式，二进制，体积小）
4. **上报**：崩溃恢复后将 minidump 文件上传到服务端
5. **服务端符号化**：用 `minidump_stackwalk` 工具配合符号文件解析出源码行号

**Crashpad** 是 Breakpad 的继任者（Chrome 团队开发），Android / Linux 侧仍依赖崩溃进程内的 signal handler 做最小通知，handler 再通过 socket 唤醒独立的 handler 进程；后续寄存器、maps、内存读取和 minidump 写入由 handler 进程完成，必要时配合 `ptrace` 或 broker 机制采集。它降低了在崩溃进程内写复杂 dump 的风险，但没有绕开信号处理入口，也不能天然避开 SignalChain 顺序问题。Android 上的集成复杂度高于 Breakpad，大部分应用仍使用 Breakpad 或托管型稳定性 SDK。

**集成注意事项**：

- 信号处理器中只能调用**异步信号安全**（async-signal-safe）的函数。`malloc()`、`std::string`、JNI 调用都不能在信号处理器中执行。Breakpad 的信号处理器内部使用预分配的内存和自定义的 `minidump` 写入逻辑规避这一限制
- 与 SignalChain 的交互：如果 Breakpad 的 `ExceptionHandler` 在 `crash_dump` 之前截获信号，系统 tombstone 可能不会生成。需要在 Breakpad handler 中将信号传递给下一个 handler（通过 `old_action` 参数保存的原始 handler）


## 常见 Native 崩溃模式

### SIGSEGV（信号 11）—— 最常见的 Native Crash

**空指针解引用**：

```text
signal 11 (SIGSEGV), code 1 (SEGV_MAPERR), fault addr 0x0
```

`fault addr` 为 0 或接近 0 的小值。在 C/C++ 中对 `NULL` 指针访问成员：

```c
struct Node* node = NULL;
node->value = 42;  // SIGSEGV, fault addr = offset of value
```

排查方向：查看 `pc` 对应的源码行，确认该行的指针是否可能为 NULL。

**野指针 / Use-After-Free**：

```text
signal 11 (SIGSEGV), code 1 (SEGV_MAPERR), fault addr 0x7abc123456
```

`fault addr` 是一个看起来正常的地址，但对应的内存页已被释放或重新分配。堆栈中可能看不到 `free()` 调用——指针可能在很久之前被释放，崩溃发生在后续使用时。

排查方向：
- 用 ASan（Address Sanitizer）编译 debug 构建，ASan 会在 `free()` 后标记内存为"毒化"状态，访问时立即崩溃并打印分配/释放堆栈
- 开启 `Malloc Debug`：`adb shell setprop wrap.com.example.app '"malloc_debug backtrace_enable_on_signal=1"'`

**JNI 中的 SIGSEGV**：

ART 虚拟机的隐式空指针检查（Implicit Null Check）优化：ART 把 `obj.field` 编译成直接内存访问指令，不生成显式的 null 检查。如果 `obj` 为 null，触发 SIGSEGV，然后 SignalChain 链头的 `art_sigsegv_handler` 会将其转换为 `NullPointerException` 抛给 Java 层。

问题出在 **native 代码直接操作 jobject 时**：如果 native 代码绕过 JNI 函数（如 `GetFieldID` + `GetIntField`），直接通过裸指针访问 Java 对象内存，SIGSEGV 不会被 ART 拦截，而是作为 Native Crash 处理。详见 1.15 节关于 JNI 类型安全和内存访问模式的讨论。

### SIGABRT（信号 6）—— 主动终止

`abort()` 调用触发 SIGABRT。常见来源：

- **assert 失败**：`assert()` 宏在条件为假时调用 `abort()`
- **Android 日志断言**：`__android_log_assert()` 在 log level `ASSERT` 且条件为假时调用 `abort()`
- **C++ 异常未捕获**：如果编译时禁用了异常支持（Android NDK 默认 `-fno-exceptions`），`throw` 语句会调用 `std::terminate()` → `abort()`
- **内存分配失败**：新版 Android（API 33+）的 scudo 分配器在检测到 double-free 或 buffer overflow 时调用 `abort()`

排查方向：SIGABRT 的 tombstone 中通常能看到 `abort()` 的调用栈。往上翻一层就是触发 abort 的位置。

### SIGBUS（信号 7）—— 总线错误

ARM64 上较少见，但以下场景可能触发：

- **未对齐的原子操作**：`std::atomic<int64_t>` 的 `load()` 在某些 ARM 实现上要求 8 字节对齐，如果地址不是 8 的倍数可能触发 SIGBUS
- **mmap 文件被截断**：通过 `mmap()` 映射了一个文件，但文件在映射期间被另一个进程截断（`ftruncate`），访问超出新文件大小的映射区域时触发 SIGBUS

## 线上 Native Crash 监控方案

### 方案对比

| 方案 | 优势 | 局限 |
|------|------|------|
| 系统 tombstone（debuggerd） | 零接入成本，信息最全 | 只能通过 `bugreport` 或 `ApplicationExitInfo` 获取，实时性差 |
| Breakpad 自建 | 自主可控，可定制 minidump 内容 | 需要维护符号化服务，集成和信号处理有坑 |
| 第三方 SDK（Firebase Crashlytics、Bugly、Sentry） | 开箱即用，自带符号化服务 | 数据出三方，可能有合规问题 |
| `sigaction` 直接注册 | 最轻量 | 与 SignalChain 冲突，可能漏捕获 |

### APM 级别的信号捕获策略

要保证 APM 的信号处理器一定被触发，需要绕过 SignalChain 机制，直接调用 libc 的 `sigaction`：

```c
// 通过 dlsym 找到 libc.so 中的真实 sigaction
void* libc = dlopen("libc.so", RTLD_LOCAL);
typedef int (*libc_sigaction_t)(int, const struct sigaction*, struct sigaction*);
libc_sigaction_t real_sigaction = (libc_sigaction_t)dlsym(libc, "sigaction");
dlclose(libc);

// 用 libc 的 sigaction 注册，绕过 ART sigchain 的 interposed sigaction
struct sigaction sa;
sa.sa_sigaction = my_crash_handler;
sigfillset(&sa.sa_mask);
sa.sa_flags = SA_SIGINFO | SA_ONSTACK | SA_RESTART;

struct sigaction old_sa;
real_sigaction(SIGSEGV, &sa, &old_sa);
// 保存 old_sa，在 my_crash_handler 中调用 old_sa.sa_sigaction 传递给系统
```

这种方式让 APM 的 handler 插入到 SignalChain 之前。风险是：如果 handler 内部出错（调用了非 async-signal-safe 函数），可能导致信号处理器链断裂，系统 tombstone 也生成不了。

建议做法：APM handler 只做最小工作（收集 pc 列表、写入共享内存），然后将信号传递给原始 handler，让 `debuggerd` 照常生成 tombstone。两条路径并行，互不干扰。


## JNI 边界崩溃的排查

JNI 是 Java 层和 Native 层之间的桥梁，崩溃经常出现在边界上：

**场景 1：native 函数签名不匹配**

Java 侧声明了 `native void process(byte[] data)`，但 C/C++ 侧的导出符号或注册表写错（参数类型、包名、方法名或签名不匹配）。静态注册路径由 ART 按 JNI 命名规则解析 native method，动态注册路径由 `RegisterNatives()` 绑定函数指针；如果解析或注册失败，常见结果是 `UnsatisfiedLinkError`。少数工程在手写 `dlsym()` 或错误复用函数指针时，才会把问题扩散成错误地址调用。

排查：检查 `javac -h` 生成的头文件、`JNIEXPORT` 导出名、`RegisterNatives()` 方法表和混淆后的类名，确认 Java 声明、JNI 签名和 native 注册逻辑一致。

**场景 2：局部引用表溢出**

在 native 循环中大量创建 JNI 局部引用（`NewStringUTF`、`NewObjectArray` 等）而不释放。默认局部引用表上限 512 个（Android 8.0+）。溢出时：

```text
JNI ERROR (app bug): local reference table overflow (max=512)
```

这不是信号崩溃，是 ART 虚拟机主动 abort。tombstone 中的调用栈会指向 abort 位置，需要往上翻到 JNI 调用层。

排查：用 `DeleteLocalRef()` 及时释放，或用 `PushLocalFrame()`/`PopLocalFrame()` 批量管理。

**场景 3：C++ 异常穿越 JNI 边界**

C++ 代码 `throw` 了异常，但没有在 native 函数内部 `catch`，异常试图穿越 JNI 边界回到 Java 层。ART 不支持 C++ 异常穿越 JNI 边界，行为是未定义的——可能直接 abort，也可能导致内存损坏后延迟崩溃。

排查：所有 JNI 函数的 C++ 实现必须用 `try/catch` 包裹顶层，确保异常不会逃逸。这是 1.15 节强调的 JNI 异常安全原则。


## Native Crash 兜底机制：线程级安全点

前面几节讲的都是「crash 后如何收集信息」，本节介绍一种**在线 crash 发生时不让进程崩溃**的技术：线程级安全点机制。

### 核心原理：sigsetjmp/siglongjmp 非局部跳转

硬件异常（SIGSEGV 等）触发后，信号被投递到崩溃线程的栈帧上执行信号处理器。信号处理器中如果直接调用 `exit()` 或 `abort()`，进程终结。但如果信号处理器能「跳回」到某个安全位置继续执行，线程就能存活。

实现这种跳转的机制是 C 标准的 `sigsetjmp`/`siglongjmp`：

```c
// sigsetjmp 将当前寄存器上下文保存到 sigjmp_buf
// 如果第二个参数=1，同时保存信号掩码
int sigsetjmp(sigjmp_buf env, int savesigs);

// siglongjmp 恢复 env 中的寄存器上下文
// sigsetjmp 调用点之后的代码感受到的就是 sigsetjmp 返回了 val（非零）
void siglongjmp(sigjmp_buf env, int val);
```

`siglongjmp` 恢复的上下文包含 PC（程序计数器）、SP（栈指针）、callee-saved 寄存器等。如果 sigsetjmp 在某函数的外层调用帧中执行，`siglongjmp` 就能让执行流「穿越」中间函数直接跳回 sigsetjmp 调用点。

关键约束：siglongjmp 恢复的 SP 指向的栈帧必须仍然有效，不能跳到一个已经返回的函数的栈帧上。因此 sigsetjmp/siglongjmp 做 crash 安全点时，sigsetjmp 必须在 crash 目标函数的**外层调用栈**上执行。

### mooner 的 prevent_pthread_crash 实现

**源码位置**：[TestPlanB/mooner - prevent_pthread_crash.c](https://github.com/TestPlanB/mooner/blob/master/mooner-core/src/main/cpp/prevent_pthread_crash.c)

mooner 是一个开源的 Android Native Crash 兜底库，完整实现了线程级安全点机制。它更适合作为隔离线程里的实验性容错方案，不能作为通用的线上 Native Crash 治理主路径。核心思路：**在 pthread_create 的 start_routine 执行前插入 sigsetjmp，如果 start_routine 执行期间发生 crash，通过 siglongjmp 跳回安全点**。

#### 线程参数封装

```c
// prevent_pthread_crash.c，行 26-30
struct ThreadHookeeArgus {
    void *(*current_func)(void *);  // 原 start_routine
    void *current_arg;              // 原实参
};
```

被 hook 的 pthread_create 调用自己的 wrapper `pthread()` 作为 start_routine，原始的 start_routine 和实参作为参数传递给 wrapper。

#### sigsetjmp 安全点与信号处理器

```c
// prevent_pthread_crash.c，行 37-49
static void *pthread(void *arg) {
    struct ThreadHookeeArgus *temp = (struct ThreadHookeeArgus *) arg;
    if (sigsetjmp(sig_env, 1)) {
        // siglongjmp 跳回此处：crash 被捕获，执行 Java 回调后线程正常退出
        __android_log_print(ANDROID_LOG_INFO, TAG, "crash 了，但被我抓住了");
        JavaVMAttachArgs vmAttachArgs = {...};
        jint attachRet = (*currentVm)->AttachCurrentThread(currentVm, &currentEnv, &vmAttachArgs);
        jmethodID id = (*currentEnv)->GetStaticMethodID(currentEnv, callClass, "onHandleSignal", "()V");
        (*currentEnv)->CallStaticVoidMethod(currentEnv, callClass, id);
    } else {
        temp->current_func(temp->current_arg);  // 正常执行
    }
    handleFlag = 0;  // wrapper 退出时清零
}
```

sigsetjmp 返回 0 时执行原 start_routine；siglongjmp 触发后 sigsetjmp 返回 1，执行 Java 回调后线程正常退出。

#### handleFlag 标志位：区分线程内 crash 和跨线程 crash

```c
// prevent_pthread_crash.c，行 59-66
static void sig_handler(int sig, struct siginfo *info, void *ptr) {
    if (handleFlag == 1) {
        // 线程正在 start_routine 中执行，siglongjmp 跳回安全点
        siglongjmp(sig_env, 1);
    } else {
        // handleFlag==0：跨线程 crash 或非目标信号，透传给原信号处理器
        sigaction(sig, &old, NULL);
    }
}
```

`handleFlag` 在 pthread_create_auto 中设为 1，在 pthread() wrapper 退出时设为 0。因此，**只有被 hook 的 start_routine 执行期间发生的 crash 才会被拦截**。另一个线程 crash 时，handleFlag=0 会透传；pthread wrapper 之外的代码 crash 时，也会透传。

#### sigaltstack：独立的信号栈

```c
// prevent_pthread_crash.c，行 90-101
stack_t ss;
ss.ss_sp = calloc(1, SIGNAL_CRASH_STACK_SIZE);  // 128KB
ss.ss_size = SIGNAL_CRASH_STACK_SIZE;
ss.ss_flags = 0;
sigaltstack(&ss, NULL);  // 为信号处理器分配独立栈
```

崩溃线程的栈可能已经损坏（栈溢出）。sigaltstack 分配一个 128KB 的已知有效的栈空间给信号处理器，保证 siglongjmp 能够执行。

#### 安全边界：只能用于隔离线程和受控故障

`siglongjmp` 跳过了 C++ 栈展开、析构函数、锁释放和线程局部状态清理。如果崩溃点已经破坏堆、全局对象、JNI 状态或业务锁，线程继续运行可能扩大数据损坏范围。多线程场景下，mooner 示例中的全局 `sig_env` / `handleFlag` 还存在竞态风险：两个线程同时进入被 hook 的 start_routine 时，后进入的线程可能覆盖前一个线程的跳转上下文。

因此这类方案只适合隔离 worker、可丢任务、故障后立即退出线程或进程的场景。线上 APM 仍应优先保留系统 tombstone、ApplicationExitInfo 和 minidump 上报；安全点只能作为灰度开关保护的补充能力，不能吞掉信号后继续让宿主进程无条件运行。

#### GOT Hook 劫持 pthread_create

```c
// prevent_pthread_crash.c，行 73-82
static int pthread_create_auto(pthread_t *thread, pthread_attr_t *attr,
                               void *(*start_routine)(void *), void *arg) {
    struct ThreadHookeeArgus *params = malloc(sizeof(struct ThreadHookeeArgus));
    params->current_func = start_routine;
    params->current_arg = arg;
    handleFlag = 1;  // 在调用原 pthread_create 前设为 1
    int fd = BYTEHOOK_CALL_PREV(pthread_create_auto, pthread_create_define,
                                thread, attr, pthread, (void *) params);
    BYTEHOOK_POP_STACK();
    return fd;
}
```

通过 ByteHook 的 `bytehook_hook_single` 将目标 SO 中的 pthread_create 替换为 pthread_create_auto。BYTEHOOK_CALL_PREV 调用原始 pthread_create，BYTEHOOK_POP_STACK 恢复调用者栈。

#### JNI_OnLoad 缓存 JVM 全局引用

```c
// jni_init.c，行 15-27
JNIEXPORT jint JNICALL JNI_OnLoad(JavaVM *vm, void *reserved) {
    currentVm = vm;
    ...
    callClass = (*env)->NewGlobalRef(env, cls);  // 缓存 Java 类全局引用
    return JNI_VERSION_1_6;
}
```

信号处理器（运行在 crash 线程中）需要 Attach 到 JVM 才能调用 Java 回调。JNI_OnLoad 是唯一安全获取 JVM 全局引用的时机（库加载时，Binder 线程池尚未完全初始化，可以安全持有全局引用）。

### ByteHook PLT Hook 框架

**源码位置**：[bytedance/bhook](https://github.com/bytedance/bhook)

ByteHook 是字节跳动的 PLT Hook 库（MIT），支撑抖音、今日头条等亿级 App。核心原理：修改 ELF 的 PLT/GOT 条目，将函数调用重定向到代理函数。API 简洁：

```c
bytehook_stub_t bytehook_hook_single(
    const char *caller_path_name,  // 调用方 SO（NULL = 所有）
    const char *callee_path_name,  // 被 hook SO（NULL = 任意）
    const char *sym_name,          // 符号名
    void *new_func,                // 代理函数
    bytehook_hooked_t hooked,       // hook 成功回调（可选）
    void *hooked_arg);             // 回调实参
```

支持 Android 4.1 - 15（API 16-35），armeabi-v7a、arm64-v8a、x86、x86_64。

### shadowhook inline Hook 框架

**源码位置**：[bytedance/android-inline-hook](https://github.com/bytedance/android-inline-hook)

shadowhook 是 ByteHook 的配套 inline Hook 库（MIT）。与 PLT Hook 不同，inline Hook 直接修改函数开头指令，可 hook 任意地址的函数。mooner 的 memory sponge（ART OOM 拦截）使用 shadowhook：

```c
// msponge.c，行 65-71
shadowhook_hook_sym_name(
    "libart.so",
    "_ZN3art2gc5space13FreeListSpace5AllocEPNS_6ThreadEmPmS5_S5_",
    (void *) los_alloc_proxy,
    (void **) &los_alloc_orig);
```

支持 Android 4.1 - 16（API 16-36），armeabi-v7a、arm64-v8a。

### pthread_mutex_destroy 后使用检测

**源码位置**：[mooner - pthread_mutex_use_after_destroy.c](https://github.com/TestPlanB/mooner/blob/master/mooner-core/src/main/cpp/pthread_mutex_use_after_destroy.c)

这是 prevent_pthread_crash 的补充，不是防止 crash，而是检测并记录谁在 mutex destroy 后还使用了它。通过检测 `pthread_mutex_internal_t.state == 0xffff`（LP64 架构）判断锁是否已销毁：

```c
// check_is_destroy_mutex.cpp
auto *mutex = reinterpret_cast<pthread_mutex_internal_t *>(mutex_interface);
uint16_t old_state = atomic_load_explicit(&mutex->state, memory_order_relaxed);
if (old_state == 0xffff) return 1;  // 锁已销毁
```

hook pthread_mutex_lock/trylock/unlock/timedlock/clocklock，在每个函数入口检查锁状态。如果发现已销毁，记录 backtrace（通过 CFI unwind 获取）。

### 设计意图总结

| 技术要素 | 作用 |
|----------|------|
| sigsetjmp/siglongjmp | 非局部跳转，跳回安全点继续执行 |
| handleFlag | 区分线程内 crash（拦截）和跨线程 crash（透传） |
| sigaltstack | 128KB 独立栈，保证信号处理器在崩溃栈上仍能执行 |
| ByteHook GOT Hook | 劫持 pthread_create，在 start_routine 执行前插入 sigsetjmp |
| JNI_OnLoad 缓存 JVM | 让信号处理器能调用 Java 层回调 |
| shadowhook inline hook | art.so 等内部符号的 hook，ART OOM 拦截等高级功能 |

## 参考资料

### Native Crash / ApplicationExitInfo 补偿链路与 Signal Handler 边界

完整分析了 debuggerd → crash_dump → tombstone 三层 native crash 处理链路，重点厘清 signal handler 的 async-signal-safe 边界（禁止 malloc/printf/堆分配），ApplicationExitInfo 对 native tombstone 的补偿入口及版本差异（API 30–34），Crashpad/Breakpad/debuggerd 的职责边界，SDK envelope 与系统 exit reason 的去重机制。

