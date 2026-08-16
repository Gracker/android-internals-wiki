---
title: "Native Crash 分析与治理"
chapter: "20.3"
section: "20.3"
section_title: "Native Crash 分析与治理"
status: finalized
applicable_versions: "Android 10 (API 29) - Android 17 (API 37)"
last_verified: "2026-08-14"
pipeline_stage: ready-to-publish
last_verified_against: "AOSP android-17.0.0_r1; Android Developers ApplicationExitInfo, GWP-ASan, memory debugging, C++ support, native symbols and 16 KB page-size docs current on 2026-08-14"
confidence: medium-high
consolidated_from:
  - "src/part5-app/ch20-stability/19-android17-signal-handler-debuggerd-migration.md"
  - "src/part5-app/ch20-stability/09-stability-case-studies.md#案例二"
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
    path: "system/core/debuggerd/tombstoned/tombstoned.cpp"
  - type: aosp
    path: "system/unwinding/libunwindstack/Unwinder.cpp"
  - type: aosp
    path: "external/google-breakpad/src/processor/simple_symbol_supplier.cc"
  - type: aosp
    path: "external/google-breakpad/src/processor/basic_source_line_resolver.cc"
  - type: official
    path: "https://developer.android.com/reference/android/app/ApplicationExitInfo"
  - type: official
    path: "https://developer.android.com/ndk/guides/ndk-stack"
  - type: official
    path: "https://developer.android.com/ndk/guides/memory-debug"
  - type: official
    path: "https://developer.android.com/ndk/guides/gwp-asan"
  - type: official
    path: "https://developer.android.com/ndk/guides/cpp-support"
  - type: official
    path: "https://developer.android.com/build/include-native-symbols"
  - type: official
    path: "https://developer.android.com/guide/practices/page-sizes"
tags: [native-crash, tombstone, signal, breakpad, symbolication, debuggerd]
related_chapters: ["20.1", "20.2", "1.15"]
task6_state: reviewed
task9_state: reviewed
task2b_state: fixed
---

# Native Crash 分析与治理

Native Crash 是 C/C++ 等本地代码执行期间发生的致命崩溃。分析时需要把信号现场、栈回溯、符号版本和对象生命周期放进同一条证据链。Java 异常通常还能沿 `Throwable` 传播；`SIGSEGV`、`SIGABRT` 等同步致命信号往往意味着本地代码状态已经损坏，应用没有可靠的进程内恢复机会。

平台源码按 Android 17 / API 37 / `android-17.0.0_r1` 核对。为便于对照 tombstone、编译产物和命令输出，本文保留以下工具链原名：

| 术语 | 本文含义 |
|---|---|
| signal handler / disposition | signal handler 是信号到达时执行的处理函数；disposition 是内核为某个信号记录的处理方式，包括调用处理函数、执行默认动作或忽略 |
| fault address / allocator | fault address 是触发故障的内存地址；allocator 是负责申请和释放堆内存的分配器 |
| tombstone | Android 为 Native Crash 生成的崩溃转储，通常包含信号、寄存器、内存映射和线程调用栈 |
| frame / backtrace / unwind | frame 是一层函数调用；backtrace 是调用栈列表；unwind 是根据寄存器和展开信息恢复这些栈帧的过程 |
| symbolication / Build ID | symbolication 把模块地址还原为函数、文件和行号；Build ID 用于确认崩溃模块与符号文件来自同一次构建 |
| ABI / ELF / debug info | ABI 约定二进制接口和调用规则；ELF 是 Android `.so` 使用的二进制格式；debug info 保存源码行号等调试信息 |
| minidump | Breakpad、Crashpad 等采集器使用的紧凑二进制转储，保存线程上下文、模块表和选定内存 |

下文依次说明系统收集、tombstone 解读、离线符号化、线上监控和实验性故障隔离。

## 从致命信号到系统 tombstone

### 信号只给出入口，不直接给出根因

CPU、内核、运行库和应用代码都可能触发信号。诊断时要同时读取信号编号、表示具体原因的 `si_code`、fault address、崩溃指令、寄存器和 allocator 报告。

| 信号 | 常见来源 | 容易误判的地方 |
|---|---|---|
| `SIGSEGV` | 未映射地址、权限错误、越界、释放后使用（use-after-free，UAF）、MTE 标签不匹配 | 非零大地址不能单独证明 UAF；也可能是越界、损坏指针或错误映射 |
| `SIGABRT` | `abort()`、未捕获 C++ 异常、`CHECK`/断言、allocator 主动终止 | 它常常是检测器发现错误后的结果，根因要看 abort message（终止原因文本）和上游栈 |
| `SIGBUS` | 文件映射越过当前文件大小、某些架构上的对齐或总线错误 | 不能在所有 ARM64 设备上都归为未对齐访问 |
| `SIGFPE` | 整数除零、溢出陷阱等算术异常 | IEEE 浮点除零通常产生 Inf（无穷大）或 NaN（非数值），不一定发出 `SIGFPE` |
| `SIGILL` | 非法指令、CPU 特性不匹配、代码页损坏 | 也可能由主动 trap 或错误函数指针跳转引起 |
| `SIGTRAP` | 断点、陷阱指令（trap）、调试和部分运行时诊断 | 不一定是业务代码主动崩溃 |

`SEGV_MAPERR` 表示地址没有有效映射，`SEGV_ACCERR` 表示映射存在但访问权限不允许。MTE（Memory Tagging Extension，内存标记扩展）、GWP-ASan（低开销抽样堆内存检测器）和 Scudo（Android 使用的强化堆分配器）还会在 tombstone 的 `Cause`、abort message 或专用字段中补充证据。不能只凭信号编号完成归因。

### Android SignalChain 的平台处理与用户处理

ART 的 [`sigchain.cc`](https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/sigchainlib/sigchain.cc) 包装 `signal`、`sigaction` 与 `sigprocmask`，让 ART 等平台特殊处理器先处理由平台接管的信号。Android 17 的关键结构是：

- 每个信号有一个 `SignalChain`；
- 内部 `special_handlers_` 是包含两个槽位的平台处理数组；
- `action_` 只保存一份用户 signal disposition，不会形成“应用处理器 1、2、3”这样的无界链表；
- 对平台接管的信号，包装后的 `sigaction` 更新保存的用户 action，不直接替换内核中的 SignalChain 处理器。

[`SignalChain::Handler()`](https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/sigchainlib/sigchain.cc) 先尝试平台特殊处理器，再调用动态链接器与 debuggerd 暴露的 `android_handle_signal()`，之后才按保存的 `action_` 交给用户处理器。Recoverable GWP-ASan 是一个特殊分支：debuggerd 若已经完成报告并确认可恢复，`android_handle_signal()` 可以返回 `true`，SignalChain 随即返回；普通致命故障不会因此变成可恢复。

注册时间无法推导处理器在这套流程中的位置。直接绕过 SignalChain 改写内核 disposition，可能破坏 ART 隐式空检查、Recoverable GWP-ASan 和系统 tombstone。

### Android 17 的 debuggerd 收集流程

Android 17 的动态链接器（linker）在早期调用 [`linker_debuggerd_init()`](https://android.googlesource.com/platform/bionic/+/refs/tags/android-17.0.0_r1/linker/linker_debuggerd_android.cpp)，把 allocator、GWP-ASan 和额外崩溃详情（crash detail）等回调交给 [`debuggerd_init()`](https://android.googlesource.com/platform/system/core/+/refs/tags/android-17.0.0_r1/debuggerd/handler/debuggerd_handler.cpp)。平台随后为致命信号安装 `debuggerd_signal_handler`。

下面的流程图用于区分崩溃进程内的最小入口和进程外的重工作。图中的 `ptrace` 是一个进程检查另一个进程线程与内存的系统机制，maps 是进程内存映射表，protobuf 是结构化二进制数据格式。

```text
同步致命信号
  → ART special handlers / android_handle_signal / 用户 action
  → debuggerd_signal_handler（崩溃进程内，保存 siginfo 与 ucontext）
  → 派生并 exec crash_dump32 或 crash_dump64
  → crash_dump ptrace 目标线程，读取寄存器、maps 与进程信息
  → libunwindstack 生成线程 backtrace
  → tombstoned 分配并轮转文本/protobuf 输出
  → crash_dump 通知 ActivityManager 的 NativeCrashListener
  → 恢复致命信号 disposition，使父进程观察到正确退出状态
```

[`debuggerd_handler.cpp`](https://android.googlesource.com/platform/system/core/+/refs/tags/android-17.0.0_r1/debuggerd/handler/debuggerd_handler.cpp) 使用预先准备的 pseudothread（专用于崩溃协作的伪线程）栈和受控的 `fork`/`exec` 协议；[`crash_dump.cpp`](https://android.googlesource.com/platform/system/core/+/refs/tags/android-17.0.0_r1/debuggerd/crash_dump.cpp) 通过 `ptrace` 读取现场，并创建崩溃地址空间的快照进程来缩短原进程所有线程的暂停时间。进程内处理器仍处于约束严格的信号处理上下文，只能执行很小一组安全操作，不能据此认为任意 C++ 逻辑都可以安全运行。

`crash_dump` 还会连接 `/data/system/ndebugsocket` 通知 ActivityManager。Native Crash 不经过 Java `UncaughtExceptionHandler`；应用安装 Java 致命异常处理器无法覆盖这条路径。

#### 动态链接器接入与 Runtime APEX 边界

动态链接器负责尽早把 allocator、GWP-ASan、crash detail 等回调接入 debuggerd，tombstone 则由后续组件生成。Android 17 的 Runtime APEX 组合会影响接入代码所在文件和条件分支；这属于平台内部装配差异，也没有面向应用的稳定接口。应用不应查找 linker 私有 `soinfo`、debuggerd 私有处理器或 ART 特殊处理器来拼装自己的崩溃链。

评审平台差异时，应沿“linker 注册入口 → debuggerd 处理器 → crash_dump → tombstoned”逐段核对，并固定 Android 源码标签与模块 Build ID。只看到同名函数或某个偏移存在，不能证明厂商构建具有相同 ABI。

#### 备用信号栈与 pseudothread 栈各有用途

`SA_ONSTACK` 让致命信号处理器在当前线程已经安装可用的备用信号栈（alternate signal stack，也称 altstack）时切换过去，主要应对线程栈损坏或接近耗尽的现场。debuggerd 预留的 pseudothread 栈供崩溃转储协作任务使用，前后还有设置为不可访问的保护页（guard page）。它不会为进程中每条业务线程自动安装备用信号栈。

自研采集器若依赖 altstack，必须明确谁安装、谁恢复、大小如何按 ABI 验证，以及与其他 SDK 共存时是否覆盖旧配置。把 debuggerd 的 pseudothread 栈大小照搬成业务 `sigaltstack()` 参数没有依据。

#### CrashInfo 进程间协议与地址标签位

崩溃进程和 `crash_dump` 之间通过版本化的 CrashInfo 二进制布局传递最小现场。协议版本、字段和内部信号编号都属于平台私有实现；Android 17 中出现 v4 不能推导为“Android 17 首次引入 v4”，应用也不应硬编码这一内部结构。

Android 17 debuggerd 的注册标志包含 `SA_EXPOSE_TAGBITS`，允许内核在支持时保留 fault address 的地址标签信息。它能改善 MTE/GWP-ASan 报告的可读性，却不会为普通 `SIGSEGV` 自动给出内存错误根因。Recoverable GWP-ASan 和 permissive MTE（允许记录故障后重试的 MTE 宽松模式）只有在平台确认并完成报告的特定分支才可能返回；Crash SDK 不应根据地址形态自行决定吞掉信号或继续执行。

## Tombstone 逐层解读

### 文件、轮转与可访问性

[`tombstoned`](https://android.googlesource.com/platform/system/core/+/refs/tags/android-17.0.0_r1/debuggerd/tombstoned/tombstoned.cpp) 管理 `/data/tombstones/tombstone_<slot>` 与对应的 `.pb`。Android 17 的 tombstone 数量由 `tombstoned.max_tombstone_count` 控制，AOSP 默认保留 32 组产物；设备厂商可以调整该属性，不能依赖固定槽号或长期保留。

生产应用通常不能直接遍历 `/data/tombstones`。可用入口包括：

- 可调试设备、取得 root（最高系统权限）的环境，或 bugreport（系统错误报告）中的系统 tombstone；
- Play Console、设备厂商后台或稳定性 SDK 提供的 Native Crash 报告；
- API 30+ 的 `ActivityManager.getHistoricalProcessExitReasons()`；
- API 31+ 对 `REASON_CRASH_NATIVE` 调用 [`ApplicationExitInfo.getTraceInputStream()`](https://developer.android.com/reference/android/app/ApplicationExitInfo)，读取 tombstone protobuf。

`getTraceInputStream()` 可能因全局循环缓冲轮转、记录缺失或权限边界返回 `null`。返回内容是 protobuf，不是文本 tombstone；解析必须使用平台 API 文档链接的数据结构定义（schema），并限制输入大小。`adb shell dumpsys dropbox`、bugreport 等属于调试或受权限约束的系统入口，不应设计成普通线上应用的采集 API。

### 一份最小 tombstone

下面的示例只展示字段关系，地址和模块名均为示意值。

```text
*** *** *** *** *** *** *** *** *** *** *** *** *** *** *** ***
ABI: 'arm64'
Timestamp: 2026-07-20 10:30:00.123456789+0800
pid: 18421, tid: 18477, name: RenderWorker  >>> com.example.app:worker <<<
signal 11 (SIGSEGV), code 1 (SEGV_MAPERR), fault addr 0x10
Cause: null pointer dereference
    x0  0000000000000000  x1  0000007fc1234560
    x29 0000007fc1234700  x30 0000007123456870
    sp  0000007fc12346c0  pc  0000007123456810

backtrace:
      #00 pc 0000000000012810  /data/app/.../lib/arm64/libcodec.so
          (codec::Frame::width() const+16) (BuildId: 8f...)
      #01 pc 0000000000014a44  /data/app/.../lib/arm64/libcodec.so
          (codec::Decoder::decode()+196) (BuildId: 8f...)
```

`>>> ... <<<` 是进程命令行标识（cmdline），常与包名或 `package:process` 相似，但不应一律称为包名。PID 是进程编号，TID 是线程编号；`pid == tid` 通常表示进程主线程。多进程应用仍要结合 cmdline 和 `processName` 判断具体进程。

### 头部、寄存器与调用栈

解读时按以下顺序进行：

1. **ABI、时间、进程与线程**：决定使用哪套构建产物和运行环境。
2. **signal、`si_code`、fault address、`Cause`**：给出错误类别和检测器证据。
3. **abort message**：`SIGABRT` 时常比 fault address 更有价值。
4. **寄存器**：`pc` 指向当前指令，`sp` 指向当前栈顶；ARM64 的 `x30` 常用作链接寄存器（link register），`x29` 常用作帧指针（frame pointer）。
5. **backtrace 与 maps**：每帧的模块相对指令地址（relative pc）、模块、函数、Build ID 和映射信息共同用于符号化。
6. **其他线程、栈内存转储（stack dump）与故障地址附近内存（memory near）**：用于寻找锁等待、线程所有者、损坏指针和上下文。

ARM64 ABI 规定函数入口的前八个整数或指针参数通常使用 `x0-x7`，但崩溃可能发生在函数中部，编译器早已复用这些寄存器。`x0 == 0` 不能自动证明“第一个源码参数为空”。同理，`x30` 在优化、叶函数或异常展开中也不一定等于可靠调用者；应优先采用经过栈展开元数据（unwind metadata）验证的 backtrace。

tombstone 的 `pc` 列通常是模块相对地址，可能还伴随非零的映射文件偏移（map offset）或装载基址修正值（load bias）。手工计算时要读同一份 maps；更稳妥的方式是把完整 tombstone 交给 `ndk-stack`，或使用报告中明确标出的 relative pc。把进程绝对 `pc` 原样传给 `addr2line`，经常会得到错误结果。

### 栈内存转储的证据等级

stack dump 是对原始栈内存的解释结果。某个值“看起来像代码地址”只能形成候选线索，因为：

- 栈上会残留已经返回的地址；
- 普通整数也可能落在模块地址范围；
- 栈破坏后 `sp` 和保存寄存器可能都不可信；
- 指针认证（pointer authentication）、带地址标签的指针（tagged pointer）与编译优化都会改变表象。

只有当候选地址与 maps、Build ID、控制流和其他线程证据一致时，才把它纳入调用关系。

## 区分栈回溯（unwind）与符号化（symbolication）

### Unwind：从现场恢复栈帧

`libunwindstack` 根据寄存器、maps、进程内存和 unwind metadata 恢复栈帧。常见信息来源包括 DWARF CFI（Call Frame Information，调用帧恢复规则，通常位于 `.eh_frame` 或 `.debug_frame`）、ARM EHABI（ARM 异常处理 ABI）的 `.ARM.exidx`、frame pointer，以及 JIT/Dex 相关映射信息。

“EH”表示异常处理（Exception Handling），并不代表一套独立且必然更快的回溯算法。`.eh_frame` 原本服务于异常展开，其中存放的 CFI 同样可用于 Crash 时的栈回溯。Frame pointer 的遍历规则较简单，但能否得到完整栈取决于架构、编译选项、尾调用、栈损坏和生成代码。

| 信息来源 | 优点 | 主要限制 |
|---|---|---|
| DWARF CFI / ARM EHABI | 优化构建也能描述寄存器恢复规则 | 元数据可能缺失、损坏或被错误裁剪（strip） |
| Frame pointer | 读取规则简单，适合低开销采样与部分 allocator 记录 | 编译时省略帧指针、尾调用或栈破坏都会导致截断 |
| 启发式栈扫描（stack scan） | unwind 失败后提供候选地址 | 误报高，不能作为精确调用栈 |

### Symbolication：从栈帧地址找到源码

符号化要求模块身份和地址同时正确：

- ABI、Build ID、模块文件必须匹配；
- 使用保留符号的 ELF，或使用从该 ELF 同次构建产生的独立符号文件；
- 地址必须转换为模块能够理解的相对虚拟地址（relative virtual address）；
- 源码、编译器、优化、LTO（链接时优化）和 split-debug（调试信息拆分）配置要与发布构建对应。

下面的命令用于核对 Build ID、单地址解析和整份 tombstone 批处理。

```bash
llvm-readelf --notes path/to/unstripped/libcodec.so

llvm-addr2line \
  --functions --demangle \
  --exe=path/to/unstripped/libcodec.so \
  0x12810

ndk-stack \
  -sym path/to/intermediates/cxx/Release/hash/obj/arm64-v8a \
  -dump path/to/tombstone.txt
```

`llvm-readelf` 的 Build ID 必须与 tombstone 模块帧一致。`llvm-addr2line` 的输入示例使用报告中的 relative pc。`ndk-stack` 需要指向按 ABI 分类、保留符号的 `.so` 目录；从日志复制 tombstone 时还要保留开头的星号分隔行。AGP 中间目录会随版本变化，应从构建任务产物或官方 [ndk-stack 文档](https://developer.android.com/ndk/guides/ndk-stack)确认，不能在脚本中写死一个长期不变的路径。

## Breakpad `.sym` 与 minidump 离线符号化

### 先明确两种产物

系统 debuggerd 生成 tombstone。Breakpad/Crashpad 一类应用级收集器通常生成 minidump；两种产物的字段和格式不同，minidump 保存线程上下文、模块表和选定内存。

Breakpad 在开发机运行的工具 `dump_syms` 会从匹配的 ELF 与 debug info 生成文本 `.sym`。常见记录为：

| 记录 | 关键字段 |
|---|---|
| `MODULE` | 操作系统、架构、模块唯一标识（module identifier）、模块名 |
| `FILE` | 文件编号与源码路径 |
| `FUNC` | 地址、范围大小、参数区大小、函数名 |
| 行记录 | 地址、范围大小、源码行、文件编号 |
| `PUBLIC` | 地址、参数区大小、公开符号名 |
| `STACK CFI` | 指定地址范围的栈恢复规则 |

不要自行猜测或截断 module identifier。目录键应直接使用同一版 `dump_syms` 输出的 `MODULE` 行标识，并与 minidump 处理器的标识规则保持一致。

下面的目录展示 `SimpleSymbolSupplier` 默认文件系统布局。

```text
symbols/
  libcodec.so/
    <module-identifier>/
      libcodec.so.sym
```

`<module-name>/<module-identifier>/<module-name>.sym` 三层都参与查找。模块同名但构建不同，必须落在不同标识目录。

### `minidump_stackwalk` 的处理步骤

1. 解析 minidump 中的线程、异常和模块列表；
2. 用模块名与 module identifier 请求对应 `.sym`；
3. 以模块装载基址（module base）与栈帧地址计算模块相对地址；
4. 用 `STACK CFI` 等记录恢复更多栈帧；
5. 用 `FUNC`、`PUBLIC`、行记录还原函数、文件和行号。

AOSP Breakpad 的 [`SimpleSymbolSupplier`](https://android.googlesource.com/platform/external/google-breakpad/+/refs/tags/android-17.0.0_r1/src/processor/simple_symbol_supplier.cc) 实现目录查找，[`BasicSourceLineResolver`](https://android.googlesource.com/platform/external/google-breakpad/+/refs/tags/android-17.0.0_r1/src/processor/basic_source_line_resolver.cc) 完成地址到符号和行号的解析。

Breakpad 客户端还要处理信号上下文之外的采集流程，远比“在 signal handler 中调用 `libunwind` 并拼出完整栈”复杂。成熟实现会尽量缩短信号上下文内的工作，并用受控的 `clone`/`fork`、预分配状态或进程外处理器生成转储。Crashpad 进一步使用独立处理器进程，但 Android 集成仍有信号入口、进程权限、`ptrace`、启动时机和设备厂商兼容问题。

### 符号文件治理

每次发布至少归档以下对象：

- 最终 APK/AAB 和版本、渠道、ABI 清单；
- 每个发布 `.so` 的 Build ID；
- 保留符号的 ELF、拆分出的 debug info 或 Breakpad `.sym`；
- 编译器、NDK、AGP、LTO 和符号裁剪配置；
- 第三方 Native SDK 的版本与供应商符号获取方式；
- 产物哈希、访问权限和保留策略。

上传 Play 的应用可以配置 `android.buildTypes.release.ndk.debugSymbolLevel`。`SYMBOL_TABLE` 提供函数名，`FULL` 还提供文件和行号；具体体积限制与配置以 [官方 Native debug symbols 文档](https://developer.android.com/build/include-native-symbols)为准。自建服务也应以 Build ID 为主键，版本号只作检索维度，不能替代二进制身份。

符号化服务需要记录“未找到模块”“module identifier 不匹配”“只有函数无行号”“unwind 失败”等状态。返回 `??` 时不能直接判定业务库缺少符号；地址换算、ABI、符号包或 module identifier 错误也会产生相同结果。

## 常见崩溃模式与排查顺序

### 先读系统给出的强证据

建议顺序如下：

1. 核对应用版本、ABI、进程、线程和 Build ID；
2. 读取 signal、`si_code`、`Cause`、abort message 和 allocator 报告；
3. 符号化崩溃线程，再看其他线程；
4. 将 fault address 放回 maps，判断映射、权限和地址标签；
5. 检查寄存器与相关内存，但不越过 ABI 和优化边界；
6. 用能复现该类错误的内存检查器（sanitizer）、MTE 或 allocator 工具验证假设。

### `SIGSEGV`：空指针、越界与悬空指针

- fault address 为 0 或较小偏移，常见于空基址（null base）加字段偏移，但也要用崩溃指令确认读取了哪个基址寄存器；
- 地址位于对象邻近区域，可能是堆或栈缓冲区越界；
- 地址曾有效但当前未映射，可能是 UAF、`munmap` 后访问或损坏指针；
- `SEGV_ACCERR` 常见于写只读页、执行不可执行页或访问保护页；
- MTE/GWP-ASan 报告若给出分配栈与释放栈，其证据强于仅凭地址形态的猜测。

`pc` 落在 `libart.so` 不能直接推断为 JNI 错误。它也可能是 Java/Native 过渡、GC、类链接、运行时检查，或只是本地内存破坏后的受害位置。判断时要看相邻的应用 Native 栈帧、JNI 调用、CheckJNI/allocator 报告和可复现性。

### `SIGABRT`：谁主动判定状态不可接受

从 abort message 向上查找触发者：

- libc/Scudo/GWP-ASan 检测到重复释放、无效释放或堆内存损坏；
- `std::terminate` 处理未捕获 C++ 异常或违反 `noexcept` 承诺的异常；
- `CHECK`、断言、fdsan（文件描述符生命周期检查）、FORTIFY（libc 边界强化检查）或 JNI 检查失败；
- 应用或 SDK 显式调用 `abort()`。

[`C++ library support`](https://developer.android.com/ndk/guides/cpp-support) 文档说明：CMake 与独立工具链默认启用 C++ 异常，`ndk-build` 默认关闭；自定义构建系统还要看编译和链接参数。因此不能笼统写成“NDK 默认 `-fno-exceptions`”。启用异常后，未在 Native 边界捕获的异常仍可能进入 `std::terminate`；禁用时，含 `throw` 的代码通常无法按预期编译。

### `SIGBUS`：优先检查文件映射生命周期

访问 `mmap` 文件时，如果底层文件被截短，读取仍在原映射范围但已经超出新文件末尾的页可能触发 `SIGBUS`。需要记录 inode（内核中的文件身份标识）与文件长度、映射起点和长度、截短或替换文件的时序，以及多进程写入者。

对齐约束取决于架构、指令和访问类型。原子对象、SIMD（单条指令并行处理多个数据）指令、紧凑布局结构体（packed struct）与来自网络或文件的强转指针都值得检查，但不能把所有 ARM64 `SIGBUS` 都归为未对齐访问。

### JNI 边界

JNI 诊断至少覆盖：

- 静态命名或 `RegisterNatives` 的方法名、签名与函数指针是否一致；常规失败通常表现为 `UnsatisfiedLinkError`，手写 `dlsym` 查找符号或使用错误函数指针才更可能跳到错误地址；
- 每次 JNI 调用后是否存在待处理的 Java 异常（pending exception）；有异常时继续调用多数 JNI API 会扩大问题；
- 局部引用、全局引用和弱全局引用的生命周期是否正确；局部引用容量是实现和上下文相关限制，不使用固定“512 个”作为跨版本契约；
- `jobject` 是受 GC 管理的句柄，不能当作稳定 C++ 对象地址解引用或跨线程裸存；
- `GetPrimitiveArrayCritical`、字符串指针和直接缓冲区（direct buffer）地址是否遵守持有期限；
- C++ 异常是否在 JNI 导出函数边界内转换成 Java 异常或错误结果，不能穿越 C ABI/JNI 边界。

`PushLocalFrame`/`PopLocalFrame` 和 `DeleteLocalRef` 用于约束循环中的局部引用；调试构建开启 CheckJNI 能更早暴露错误。相关基础见 [1.15 JNI / NDK 性能与安全边界](../../part1-fundamentals/ch01-architecture/15-jni-ndk-performance.md)。

## 用内存工具验证地址假设

| 工具 | 适合阶段 | 能发现什么 | 关键限制 |
|---|---|---|---|
| Recoverable GWP-ASan | Android 14+ 线上抽样 | 部分堆 UAF 与堆缓冲区越界，并写入 Native Crash 报告 | 抽样率低；报告后继续运行不代表内存状态安全 |
| HWASan | 自动化测试、团队内部真实使用测试（dogfood） | 堆或栈越界、UAF 等，并提供分配栈和释放栈 | 仅 64 位，CPU、内存和包体开销高 |
| MTE | 支持硬件上的测试与受控线上策略 | 检测地址标签不匹配，帮助发现和缓解内存破坏 | 仅 64 位且依赖硬件、系统与构建策略，存在漏检概率 |
| ASan | HWASan 不适用的旧设备或遗留环境 | 多类地址错误 | 官方自 2023 年起不再支持，打包和运行开销高 |
| malloc debug | 可调试构建与专项复现 | 分配回溯、保护区和内存填充值等 allocator 诊断 | 启动配置和开销取决于选项，不适合作为通用线上方案 |

Android 14+ 未显式配置时，约 1% 的应用启动会启用 [Recoverable GWP-ASan](https://developer.android.com/ndk/guides/gwp-asan)。它生成一次报告后允许进程继续，但官方明确说明后续行为没有定义；团队仍应高优先级修复。自定义 `SIGSEGV` 处理器不会收到这类故障的回调，不能用“APM（Application Performance Monitoring，应用性能监控）没有捕获”否定报告。

工具选择与当前命令以 [Memory error debugging and mitigation](https://developer.android.com/ndk/guides/memory-debug)、[GWP-ASan](https://developer.android.com/ndk/guides/gwp-asan) 和 [HWASan](https://developer.android.com/ndk/guides/hwasan) 为准。`wrap.sh` 只用于可调试 APK，并需要随 ABI 正确打包；一条 `setprop wrap.<package>` 命令无法充当所有设备通用的 ASan 开关。

## 线上 Native Crash 采集方案

| 方案 | 证据 | 优势 | 边界 |
|---|---|---|---|
| 系统 tombstone / bugreport | 系统完整文本或 protobuf、线程、maps、allocator 信息 | 与平台 Crash 流程一致 | 生产应用不能直接读取目录；保留数量与获取权限有限 |
| `ApplicationExitInfo` | API 30+ 退出元数据，API 31+ 可取 Native tombstone protobuf | 可在下次启动补采集，覆盖进程内 SDK 来不及完成的场景 | 非实时；输入流可能为 `null`，必须去重 |
| Google Play / 设备平台 | 聚类、受影响用户与设备维度 | 无需自建信号处理器 | 数据条件、延迟、符号上传与上下文受平台约束 |
| Breakpad / Crashpad / 托管 SDK | minidump、业务轨迹（breadcrumb）、服务端符号化 | 可控制上下文和告警 | 信号处理器兼容、隐私、成本、符号和版本维护 |
| 自研 `sigaction` | 自定义固定大小的最小记录 | 代码入口少 | 容易破坏平台处理器、遗漏 tombstone，或在信号处理上下文中再次崩溃 |

建议把系统与 SDK 记录按进程启动 ID、时间、信号、TID、Build ID 和关键栈帧去重，同时保留来源字段。SDK minidump 与 `ApplicationExitInfo` tombstone 提供互补证据，应同时保留并关联。

### Signal handler 的执行边界

POSIX 信号处理上下文中只能调用 async-signal-safe 操作，即标准明确允许在异步信号处理器中调用的小范围函数。工程上应进一步缩小范围：

- 不调用 `malloc/new`、`free/delete`、`std::string`、iostream、普通日志格式化和大多数 libc 高层函数；
- 不进入 JNI、ART、数据库、网络栈和业务锁；
- 不使用可能已被当前线程持有的互斥锁（mutex）；
- 使用预分配内存、固定大小结构、原子状态和已经打开的文件描述符（fd）；
- 处理重入、嵌套信号、多个线程同时故障、备用信号栈和写入中断；
- 保存并正确恢复或转发原 action、信号屏蔽集（signal mask）与 `SA_SIGINFO` 等语义。

通过 `dlopen("libc.so") + dlsym("sigaction")` 绕过 ART 包装层，无法保证 APM 处理器会被调用。Android 的 SignalChain 自己就用类似方式寻找真实 libc 符号，以保护平台先行处理；应用再次绕过会直接竞争内核 disposition。若处理器消费信号、转发错误或返回到同一条故障指令，系统 tombstone 可能缺失，进程也可能陷入重复信号。

自研前应评估成熟 SDK 是否已经处理 Android 版本、处理器顺序、备用信号栈、恢复默认 disposition 和重新投递信号。任何自研实现都要在 Android 10～17、各 ABI、MTE/GWP-ASan、多个 SDK 共存和 [16 KB 页大小设备](https://developer.android.com/guide/practices/page-sizes)上做故障注入。

### 多个 Native Crash 采集器的冲突验证

接入第二个采集器后缺少堆栈时，先不要把原因归到处理器覆盖。应逐段确认现场是否生成、文件是否完整、符号是否匹配、上传与解析是否成功；原始产物和 Build ID 均无误后，再检查 signal disposition。

内核对每个信号维护一份 disposition；后一次 `sigaction()` 会替换前一次，并通过 `oldact` 返回旧值。保存旧处理器不会自动形成安全调用链：`SIG_DFL`、`SIG_IGN`、`SA_SIGINFO`、线程信号屏蔽集、重复进入、altstack 和重新投递都必须保留原语义。两个闭源 SDK 都试图独占崩溃链控制权时，很难证明组合正确。

下面的只读探针只适合可调试构建的集成测试，调用点应位于各 SDK 初始化前后，不能放进致命信号处理器：

```cpp
struct HandlerSnapshot {
  int flags;
  uintptr_t entry;
};

int SnapshotHandler(int signo, HandlerSnapshot* out) {
  struct sigaction current = {};
  if (sigaction(signo, nullptr, &current) != 0) return errno;

  out->flags = current.sa_flags;
  out->entry = (current.sa_flags & SA_SIGINFO)
      ? reinterpret_cast<uintptr_t>(current.sa_sigaction)
      : reinterpret_cast<uintptr_t>(current.sa_handler);
  return 0;
}
```

函数地址受 ASLR（Address Space Layout Randomization，地址空间布局随机化）影响，只用于同一进程内比较。即使入口被正确串接，也必须用行为结果验收。推荐让一个组件负责致命 Native 信号，其他 SDK 关闭 Native 捕获，只保留 Java、性能或上传能力；依赖升级后重跑冲突测试。

每个支持的 ABI 和主要 Android 版本至少注入 `abort()`、空指针读写、栈溢出、多线程同时故障，以及设备支持时的 MTE/GWP-ASan 错误。通过标准同时覆盖应用产物、`ApplicationExitInfo`、系统 tombstone、离线符号化和服务端接收；缺少其中一项时，应标出失败阶段，不能用一个“堆栈完整率”掩盖原因。

## 线程级跳转恢复点：仅用于实验性故障隔离

### `sigsetjmp` / `siglongjmp` 能做什么

`sigsetjmp(env, 1)` 保存当前线程的寄存器上下文和 signal mask；同一线程后续调用 `siglongjmp` 可以回到仍然存活的保存点。它只改变控制流，不会修复内存或恢复已经损坏的状态。

要满足的最低条件包括：

- `sigjmp_buf` 属于当前线程，保存点所在栈帧尚未返回；
- 跳转目标必须是预先设计的错误出口，原任务随即终止；
- 不依赖跳过区间内应执行的 C++ 析构等清理；
- 不假设业务锁、allocator、JNI、TLS（Thread-Local Storage，线程局部存储）或全局状态仍一致；
- 只处理经过严格限定的同步故障，其他信号仍交给系统。

C++ 析构和栈展开被跳过，自动变量还受 `setjmp`/`longjmp` 语义限制。若故障来自堆内存损坏、栈破坏或错误函数指针，跳回后继续使用同一进程可能造成数据损坏、死锁，或稍后在无关位置崩溃。

### mooner `prevent_pthread_crash` 的证据边界

[TestPlanB/mooner](https://github.com/TestPlanB/mooner) 展示了一个实验方案：用 ByteHook 代理 `pthread_create`，在线程入口函数（start routine）外层保存 `sigjmp_buf`，目标线程故障时跳回包装函数（wrapper），再结束该线程。

它适合作为研究样本，不能直接推导出通用线上容错能力：

- 当前示例把 `sig_env` 和 `handleFlag` 定义为进程级 `static` 全局变量，多条线程会共享并覆盖跳转上下文；
- 代理 `pthread_create` 只能覆盖经指定 Hook 点创建、并在包装函数内执行的任务；
- `siglongjmp` 会跳过锁释放、RAII（用对象生命周期自动清理资源）析构、JNI 线程分离和线程局部清理；
- 故障已经破坏共享堆或全局状态时，结束单个线程也不能恢复进程一致性；
- 若转发旧 signal action、恢复 disposition 或重新投递不完整，会干扰 debuggerd。

若业务仍要试验，应限制在可丢弃、无共享可变状态的隔离工作线程（worker）；命中后停止接收新任务，保存最小证据，并尽快重建独立进程或让宿主按明确策略退出。跳回后不应再附加到 JVM、分配大量对象并执行普通 Java 回调，更不能据此宣称“线程已经恢复”。

### ByteHook、shadowhook 与私有 pthread 状态

[ByteHook](https://github.com/bytedance/bhook) 通过 PLT/GOT（保存外部函数跳转与地址的链接表）改写调用目标，[shadowhook](https://github.com/bytedance/android-inline-hook) 修改函数入口或指令流。二者提供 Hook 基础设施；被 Hook 对象的线程安全与生命周期仍由接入方负责。

Android 17 使用它们时要重新验证：

- 目标符号是否导出，是否被 LTO、内联展开（inlining）或直接调用绕过；
- linker namespace（动态库可见范围）、RELRO（重定位后只读保护）、PAC/BTI 与 CFI（控制流完整性保护），以及 16 KB 页大小的影响；
- 动态加载/卸载、新增 `.so` 和多 ABI；
- Hook 回调重入、取消 Hook 时的并发调用和原函数递归；
- 第三方库声明的 Android/NDK 支持范围。

不要依赖 `pthread_mutex_t` 私有布局或某个版本中的 `state == 0xffff` 来判断互斥锁已经销毁。bionic 内部结构不属于 NDK 稳定 ABI，设备厂商和 Android 版本都可能改变它。更可靠的做法是在自有锁包装层维护生命周期代次（generation）、当前持有者（owner）和销毁状态，并用 HWASan/MTE、压力测试和严格所有权修复对象销毁后仍被使用的问题。

## Native Crash 治理清单

### 构建阶段

- 每个发布 ABI 生成并归档 Build ID，以及保留符号的 ELF 或独立调试符号文件；
- 在 CI 校验 APK/AAB 中 `.so` 与符号归档一一对应；
- 为自有 Native 模块启用适合发布配置的 unwind 信息和 arm64 帧指针策略；
- 使用 HWASan/MTE、模糊测试（fuzz）、压力与并发测试覆盖内存和 JNI 边界；
- 对第三方 Native SDK 建立版本、符号和撤回开关清单。

### 采集阶段

- 系统 `ApplicationExitInfo` 与 SDK minidump 都保留来源和唯一键；
- signal handler 只写固定大小的最小记录，不做网络和 JNI；
- 记录应用、进程、会话、ABI、Build ID、信号、`si_code`、TID 与关键栈帧；
- 验证多个处理器共存时系统 tombstone 仍能生成；
- 对启动后反复崩溃的 crash loop 提供禁用故障 Native 功能或安全模式。

### 诊断与验证

- 先匹配 Build ID，再谈源码行号；
- 把 fault address 放回 maps 和崩溃指令，不用地址形态替代证据；
- 对 allocator/MTE/GWP-ASan 报告优先读取分配栈和释放栈；
- JNI Crash 同时检查待处理异常、引用生命周期、线程和函数签名；
- 修复后用同类 sanitizer 或故障注入验证，并观察原问题簇是否迁移为新信号、ANR 或数据损坏。

## 源码与官方文档

- 平台：AOSP [`android-17.0.0_r1`](https://android.googlesource.com/platform/manifest/+/refs/tags/android-17.0.0_r1/)
- SignalChain：[`art/sigchainlib/sigchain.cc`](https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/sigchainlib/sigchain.cc) · [`art/runtime/fault_handler.cc`](https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/runtime/fault_handler.cc)
- debuggerd：[`debuggerd_handler.cpp`](https://android.googlesource.com/platform/system/core/+/refs/tags/android-17.0.0_r1/debuggerd/handler/debuggerd_handler.cpp) · [`crash_dump.cpp`](https://android.googlesource.com/platform/system/core/+/refs/tags/android-17.0.0_r1/debuggerd/crash_dump.cpp) · [`tombstone.cpp`](https://android.googlesource.com/platform/system/core/+/refs/tags/android-17.0.0_r1/debuggerd/libdebuggerd/tombstone.cpp) · [`tombstoned.cpp`](https://android.googlesource.com/platform/system/core/+/refs/tags/android-17.0.0_r1/debuggerd/tombstoned/tombstoned.cpp)
- unwind：[`libunwindstack/Unwinder.cpp`](https://android.googlesource.com/platform/system/unwinding/+/refs/tags/android-17.0.0_r1/libunwindstack/Unwinder.cpp)
- Breakpad：[`symbol_files.md`](https://android.googlesource.com/platform/external/google-breakpad/+/refs/tags/android-17.0.0_r1/docs/symbol_files.md) · [`simple_symbol_supplier.cc`](https://android.googlesource.com/platform/external/google-breakpad/+/refs/tags/android-17.0.0_r1/src/processor/simple_symbol_supplier.cc) · [`basic_source_line_resolver.cc`](https://android.googlesource.com/platform/external/google-breakpad/+/refs/tags/android-17.0.0_r1/src/processor/basic_source_line_resolver.cc)
- 应用可见 tombstone：[`ApplicationExitInfo`](https://developer.android.com/reference/android/app/ApplicationExitInfo)
- NDK 诊断：[ndk-stack](https://developer.android.com/ndk/guides/ndk-stack) · [Memory error debugging](https://developer.android.com/ndk/guides/memory-debug) · [GWP-ASan](https://developer.android.com/ndk/guides/gwp-asan) · [HWASan](https://developer.android.com/ndk/guides/hwasan)
- 构建与发布：[C++ library support](https://developer.android.com/ndk/guides/cpp-support) · [Native debug symbols](https://developer.android.com/build/include-native-symbols) · [16 KB page sizes](https://developer.android.com/guide/practices/page-sizes)
