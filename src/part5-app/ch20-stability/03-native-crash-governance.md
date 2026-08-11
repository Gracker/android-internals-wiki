---

title: "Native Crash 分析与治理"
chapter: "20.3"
section: "20.3"
section_title: "Native Crash 分析与治理"
status: finalized
applicable_versions: "Android 10 (API 29) - Android 17 (API 37)"
last_verified: "2026-07-12"
task9_result: auto-fixed
task9_reviewed_date: "2026-07-12"
task9_reviewed_by: "openclaw-task9"
pipeline_stage: ready-to-publish
last_verified_against: "AOSP android-17.0.0_r1 (debuggerd/crash_dump, tombstoned CrashQueue default 32 tombstone slots, libunwindstack BuildId format, native crash notification chain)"
confidence: medium
drafted_date: "2026-05-11"
polish_count: 0
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
tags: [native-crash, tombstone, signal, breakpad, symbolication, debuggerd]
related_chapters: ["20.1", "20.2", "1.15"]
task6_state: reviewed
task6_review_notes_final: "2026-07-02 Task6 round3 (post-Task9-autofix): pass-light-edit. L1 clean. L2 pass. Anchors all covered. Auto-promoted: task9=pass, queue=completed."
task6_review_notes_round4: "2026-07-03 Task6 round4 (re-confirm): pass-light-edit. L1 clean (对齐=技术内存对齐, 非黑话). L2 pass. 限制句式×2 at limit. No new L3/L4 issues. AUTO-PROMOTED: task6=pass-light-edit, task9=auto-fixed(=pass), queue=completed."
task6_result: pass-light-edit
task9_state: reviewed
last_task9_at: "2026-07-12T19:26:24+08:00"
task2b_state: fixed
task2b_result: fixed
last_task2b_at: "2026-07-02T18:50:00+08:00"
task2b_notes: "2026-06-01 Task2B fallback: 修复 ApplicationExitInfo tombstone protobuf 边界、Breakpad 源码锚点、JNI native resolve 口径、CFI/Java frame、Crashpad handler 与 mooner 安全边界。2026-07-02 Task2B round2: 补充符号服务器架构设计、Native Crash 排查实战思路与分级排查流程。"
reviewed_by: openclaw-task6
reviewed_date: 2026-07-12
last_task6_at: "2026-07-12T20:19:00+08:00"
last_task6_audit: "2026-06-09"
task6_reviewed_by: "openclaw-task6"
task6_reviewed_at: "2026-05-19T20:25:44+08:00"
last_task6_review_log: "logs/review/2026-06-21-20-review.md"
task6_review_notes_round2: "2026-07-02 Task6 revisiting-review round2: pass-light-edit. L1 fix: remove banned word. L2 pass. Anchors all covered. No new L3/L4 issues."
task6_review_notes: '2026-07-02 18:10 Task6 revisiting-review: needs-rework。L1修复: 链路→流程×3, meta-narrative×1。L3/L4问题已在queue.json(pending)。保持ready-for-review, 送Task2B。 | 2026-06-01 18 Task6 revisiting-review: pass-light-edit。修正 C++ 异常 typo 与英文所有格表达；L1/L2 通过，无新增回炉项，送 Task9 复核。'
last_task9_review_log: "logs/deep-review/2026-07-12-19-audit.md"
task9_review_notes: "2026-07-12 Task9 idle audit AUTO-FIX：对照 AOSP android-17.0.0_r1 tombstoned.cpp，修正 tombstone 默认保留数量旧口径：Android 17 由 tombstoned.max_tombstone_count 控制，默认 32 个槽位，并补充 tombstoned.cpp 源码锚点；回到 Task6 复审。"
last_task9_autofix_at: "2026-07-12"
deepseek_cn_review_state: done
last_deepseek_cn_review_at: 2026-07-12
last_task9_audit: "2026-07-12"
last_task2b_verify_at: "2026-06-21T19:30:09+08:00"
task2b_verifier_notes: "状态修正：Task9 auto-fix 后 status 应为 ready-for-review，原 finalized 已回退。"
last_task9_audit_at: "2026-07-12T19:26:24+08:00"
last_task9_audit_log: "logs/deep-review/2026-07-12-19-audit.md"
last_task9_audit_result: "auto-fixed"
last_task9_audit_notes: "idle audit auto-fix: AOSP android-17.0.0_r1 tombstoned uses tombstoned.max_tombstone_count default 32, not 00-09 ten-slot rotation; added tombstoned.cpp source anchor."
task6_promotion_notes: "2026-07-12 20H Task6 revisiting review (post-task9-idle-audit): pass-light-edit。L1禁用词扫描零命中（\"对齐\"为技术内存对齐，非黑话）。L2开头/节奏/结构/读者视角全通过。锚点6/6覆盖，扩展2/2覆盖。Task9 idle audit auto-fix（tombstone默认32槽位口径修正）后写作质量未受影响。无新增L3/L4回炉。AUTO-PROMOTED: task6=pass-light-edit, task9=auto-fixed(=pass), queue=clear。"
---

# Native Crash 分析与治理

Native Crash 的难点不在“看到一个信号”，而在于把信号现场、栈回溯、符号版本和对象生命周期放到同一条证据链里。Java 异常通常还能沿 `Throwable` 传播；`SIGSEGV`、`SIGABRT` 等同步致命信号往往意味着 Native 状态已经损坏，应用没有可靠的进程内恢复机会。

平台源码锚点是 Android 17 / API 37 / `android-17.0.0_r1`。下文依次说明系统收集、tombstone 解读、离线符号化、线上监控和实验性线程安全点。

## 从致命信号到系统 tombstone

### 信号只给出入口，不直接给出根因

CPU、内核、运行库和应用代码都可能触发信号。诊断时要同时读取信号编号、`si_code`、fault address、崩溃指令、寄存器和 allocator 报告。

| 信号 | 常见来源 | 容易误判的地方 |
|---|---|---|
| `SIGSEGV` | 未映射地址、权限错误、越界、use-after-free、MTE tag fault | 非零大地址不等于 UAF；也可能是越界、损坏指针或错误映射 |
| `SIGABRT` | `abort()`、未捕获 C++ 异常、`CHECK`/assert、allocator 主动终止 | 它常常是检测器发现错误后的结果，根因要看 abort message 和上游栈 |
| `SIGBUS` | 文件映射越过当前文件大小、某些架构上的对齐或总线错误 | 不能在所有 ARM64 设备上都归为未对齐访问 |
| `SIGFPE` | 整数除零、溢出陷阱等算术异常 | IEEE 浮点除零通常产生 Inf/NaN，不一定发出 `SIGFPE` |
| `SIGILL` | 非法指令、CPU 特性不匹配、代码页损坏 | 也可能由主动 trap 或错误函数指针跳转引起 |
| `SIGTRAP` | 断点、trap、调试和部分运行时诊断 | 不一定是业务代码主动崩溃 |

`SEGV_MAPERR` 表示地址没有有效映射，`SEGV_ACCERR` 表示映射存在但访问权限不允许。Android 的 MTE、GWP-ASan、Scudo 等还会在 tombstone 的 `Cause`、abort message 或专用字段中补充证据。不能只凭信号编号完成归因。

### Android SignalChain 不是任意长度的应用 handler 链表

ART 的 [`sigchain.cc`](https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/sigchainlib/sigchain.cc) 包装 `signal`、`sigaction` 与 `sigprocmask`，让 ART 等平台 special handler 有机会先处理被 claim 的信号。Android 17 的关键结构是：

- 每个信号有一个 `SignalChain`；
- 内部 `special_handlers_` 是容量受限的平台处理数组；
- `action_` 保存一个用户 signal disposition，而不是“应用 handler 1、2、3”组成的无界链表；
- 对已 claim 的信号，包装后的 `sigaction` 更新保存的用户 action，不直接替换内核中的 SignalChain handler。

[`SignalChain::Handler()`](https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/sigchainlib/sigchain.cc) 先尝试 special handlers，再调用 linker/debuggerd 暴露的 `android_handle_signal()`，之后才按保存的 `action_` 交给用户 handler。Recoverable GWP-ASan 是一个特殊分支：debuggerd 若已经完成报告并确认可恢复，`android_handle_signal()` 可以返回 `true`，SignalChain 随即返回；普通致命故障不会因此变成可恢复。

这套顺序不能简化成“谁注册得晚谁就在链尾”。直接绕过 SignalChain 改写内核 disposition，可能破坏 ART 隐式空检查、recoverable GWP-ASan 和系统 tombstone。

### Android 17 的 debuggerd 收集流程

Android 17 linker 在早期调用 [`linker_debuggerd_init()`](https://android.googlesource.com/platform/bionic/+/refs/tags/android-17.0.0_r1/linker/linker_debuggerd_android.cpp)，由它把 allocator、GWP-ASan、crash detail 等回调交给 [`debuggerd_init()`](https://android.googlesource.com/platform/system/core/+/refs/tags/android-17.0.0_r1/debuggerd/handler/debuggerd_handler.cpp)。平台随后为致命信号安装 `debuggerd_signal_handler`。

下面的流程图用于区分崩溃进程内的最小入口和进程外的重工作。

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

[`debuggerd_handler.cpp`](https://android.googlesource.com/platform/system/core/+/refs/tags/android-17.0.0_r1/debuggerd/handler/debuggerd_handler.cpp) 使用预先准备的 pseudothread 栈和受控的 fork/exec 协议；[`crash_dump.cpp`](https://android.googlesource.com/platform/system/core/+/refs/tags/android-17.0.0_r1/debuggerd/crash_dump.cpp) 通过 `ptrace` 读取现场，并创建崩溃地址空间的快照进程来缩短原进程所有线程的暂停时间。进程内 handler 仍处于严格受限的 signal context，不能据此认为任意 C++ 逻辑都可以安全执行。

`crash_dump` 还会连接 `/data/system/ndebugsocket` 通知 ActivityManager。Native Crash 不经过 Java `UncaughtExceptionHandler`；应用安装 Java fatal handler 无法覆盖这条路径。

#### linker wiring 与 Runtime APEX 边界

linker 的职责是尽早把 allocator、GWP-ASan、crash detail 等回调接入 debuggerd，而不是负责生成 tombstone。Android 17 的 Runtime APEX 组合会影响 wiring 所在文件和条件分支；这属于平台内部装配差异，不是应用可调用的稳定接口。应用不应查找 linker 私有 `soinfo`、debuggerd 私有 handler 或 ART special handler 来拼装自己的崩溃链。

评审平台差异时，应沿“linker 注册入口 → debuggerd handler → crash_dump → tombstoned”逐段核对，并固定 Android tag 与模块 Build ID。只看到同名函数或某个偏移存在，不能证明厂商构建具有相同 ABI。

#### alternate signal stack 与 pseudothread 栈不是同一块内存

`SA_ONSTACK` 让致命 signal handler 在当前线程已有可用 alternate stack 时切换过去，主要应对线程栈损坏或接近耗尽的现场。debuggerd 预留的 pseudothread 栈则供崩溃转储协作线程使用，前后还带 guard page。它不会为进程中每条业务线程自动安装一块 alternate stack。

自研采集器若依赖 altstack，必须明确谁安装、谁恢复、大小如何按 ABI 验证，以及与其他 SDK 共存时是否覆盖旧配置。把 debuggerd 的 pseudothread 栈大小照搬成业务 `sigaltstack()` 参数没有依据。

#### CrashInfo wire protocol 与 tag bit

崩溃进程和 `crash_dump` 之间通过版本化的 CrashInfo 协议传递最小现场。协议版本、字段和内部 signal 编号都属于平台私有实现；Android 17 中出现 v4 不能推导为“Android 17 首次引入 v4”，更不能让应用硬编码内部结构解析。

Android 17 debuggerd 注册 flags 包含 `SA_EXPOSE_TAGBITS`，允许内核在支持时保留 fault address 的 tag 信息。它改善 MTE/GWP-ASan 报告可读性，却不会让普通 SIGSEGV 自动获得内存错误根因。Recoverable GWP-ASan 和 permissive MTE 只有在平台确认并完成报告的特定分支才可能返回；Crash SDK 不应从地址形态自行决定吞掉信号或继续执行。

## Tombstone 逐层解读

### 文件、轮转与可访问性

[`tombstoned`](https://android.googlesource.com/platform/system/core/+/refs/tags/android-17.0.0_r1/debuggerd/tombstoned/tombstoned.cpp) 管理 `/data/tombstones/tombstone_<slot>` 与对应的 `.pb`。Android 17 的 tombstone 数量由 `tombstoned.max_tombstone_count` 控制，AOSP 默认 32 个 artifact；设备厂商可以调整属性，不能依赖固定槽号或长期保留。

生产应用通常不能直接遍历 `/data/tombstones`。可用入口包括：

- 可调试设备、root 环境或 bugreport 中的系统 tombstone；
- Play Console、设备厂商后台或稳定性 SDK 提供的 Native crash 报告；
- API 30+ 的 `ActivityManager.getHistoricalProcessExitReasons()`；
- API 31+ 对 `REASON_CRASH_NATIVE` 调用 `ApplicationExitInfo.getTraceInputStream()`，读取 tombstone protobuf。

`getTraceInputStream()` 可能因全局循环缓冲轮转、记录缺失或权限边界返回 `null`。它返回 protobuf，不是文本 tombstone；解析必须使用平台文档链接的 schema，并限制输入大小。`adb shell dumpsys dropbox`、bugreport 等属于调试或受权限约束的系统入口，不应设计成普通线上应用的采集 API。

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

`>>> ... <<<` 是进程 cmdline，常与包名或 `package:process` 相似，但不应一律称为包名。`pid == tid` 通常表示主线程；多进程应用仍要结合 cmdline 和 `processName`。

### 头部、寄存器与 backtrace

解读时按以下顺序进行：

1. **ABI、时间、进程与线程**：决定使用哪套构建、ABI 和运行环境。
2. **signal、`si_code`、fault address、Cause**：给出错误类别和检测器证据。
3. **abort message**：`SIGABRT` 时常比 fault address 更有价值。
4. **寄存器**：`pc` 是当前指令，`sp` 是栈顶；ARM64 的 `x30` 常作 link register，`x29` 常作 frame pointer。
5. **backtrace 与 maps**：每帧的 relative pc、模块、函数、Build ID 和映射信息共同用于符号化。
6. **其他线程、stack dump 与 memory near**：用于寻找锁等待、线程所有者、损坏指针和上下文。

ARM64 ABI 规定函数入口的前八个整数或指针参数通常使用 `x0-x7`，但崩溃可能发生在函数中部，编译器早已复用这些寄存器。`x0 == 0` 不能自动证明“第一个源码参数为空”。同理，`x30` 在优化、叶函数或异常展开中也不一定等于可靠调用者；优先相信经过 unwind metadata 验证的 backtrace。

tombstone 的 `pc` 列通常是模块相对地址，可能还伴随非零 map offset 或 load bias。手工计算时要读同一份 maps；更稳妥的方式是把完整 tombstone 交给 `ndk-stack` 或使用报告中明确标出的 relative pc。把进程绝对 `pc` 原样喂给 `addr2line`，经常会得到错误结果。

### Stack dump 的证据等级

stack dump 是原始栈内存的解释结果。某个值“看起来像代码地址”只能形成候选线索，因为：

- 栈上会残留已经返回的地址；
- 普通整数也可能落在模块地址范围；
- 栈破坏后 `sp` 和保存寄存器可能都不可信；
- pointer authentication、tagged pointer 与优化会改变表象。

只有当候选地址与 maps、Build ID、控制流和其他线程证据一致时，才把它纳入调用关系。

## 把 unwind 与 symbolication 分开

### Unwind：从现场恢复 frame

`libunwindstack` 根据寄存器、maps、进程内存和 unwind metadata 恢复 frame。常见信息来源包括 DWARF CFI（通常位于 `.eh_frame`/`.debug_frame`）、ARM EHABI 的 `.ARM.exidx`、frame pointer，以及 JIT/Dex 相关映射信息。

“EH”不是独立且必然更快的回溯算法。`.eh_frame` 原本服务于异常展开，其中存放的 CFI 同样可用于 crash unwind。Frame pointer 的遍历简单，但能否得到完整栈取决于架构、编译选项、尾调用、栈损坏和生成代码。

| 信息来源 | 优点 | 主要限制 |
|---|---|---|
| DWARF CFI / ARM EHABI | 优化构建也能描述寄存器恢复规则 | 元数据可能缺失、损坏或被错误 strip |
| Frame pointer | 读取规则简单，适合低开销采样与部分 allocator 记录 | 省略 frame pointer、尾调用或栈破坏会截断 |
| 启发式 stack scan | unwind 失败后提供候选地址 | 误报高，不能作为精确调用栈 |

### Symbolication：从 frame 地址找到源码

符号化要求模块身份和地址同时正确：

- ABI、Build ID、模块文件必须匹配；
- 使用未 strip ELF 或与该 ELF 生成的符号文件；
- 地址必须转换为模块能够理解的 relative virtual address；
- 源码、编译器、优化、LTO 和 split-debug 配置要与发布构建对应。

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

`llvm-readelf` 的 Build ID 必须与 tombstone 模块帧一致。`llvm-addr2line` 的输入示例使用报告中的 relative pc。`ndk-stack` 需要包含未 strip `.so` 的 ABI 目录；从日志复制 tombstone 时还要保留开头的星号分隔行。AGP 中间目录会随版本变化，应从构建任务产物或官方 [ndk-stack 文档](https://developer.android.com/ndk/guides/ndk-stack)确认，不能在脚本中写死一个长期不变的路径。

## Breakpad `.sym` 与 minidump 离线符号化

### 先明确两种产物

系统 debuggerd 生成 tombstone。Breakpad/Crashpad 一类应用级收集器通常生成 minidump；minidump 保存线程上下文、模块表和选定内存，不等同于 tombstone 文本。

Breakpad 的 host 工具 `dump_syms` 从匹配的 ELF/debug info 生成文本 `.sym`。常见记录为：

| 记录 | 关键字段 |
|---|---|
| `MODULE` | OS、arch、module identifier、module name |
| `FILE` | file id 与源码路径 |
| `FUNC` | address、size、parameter size、函数名 |
| 行记录 | address、size、line、file id |
| `PUBLIC` | address、parameter size、符号名 |
| `STACK CFI` | 指定地址范围的栈恢复规则 |

不要自行猜测或截断 module identifier。目录键应直接使用同一版 `dump_syms` 输出 `MODULE` 行中的标识，并和 minidump processor 的标识规则保持一致。

下面的目录展示 `SimpleSymbolSupplier` 默认文件系统布局。

```text
symbols/
  libcodec.so/
    <module-identifier>/
      libcodec.so.sym
```

`<module-name>/<module-identifier>/<module-name>.sym` 三层都参与查找。模块同名但构建不同，必须落在不同 identifier 目录。

### `minidump_stackwalk` 的处理步骤

1. 解析 minidump 中的线程、异常和 module list；
2. 用模块名与 module identifier 请求对应 `.sym`；
3. 以模块 base 与 frame 地址计算 module-relative address；
4. 用 `STACK CFI` 等记录恢复更多 frame；
5. 用 `FUNC`、`PUBLIC`、行记录还原函数、文件和行号。

AOSP Breakpad 的 [`SimpleSymbolSupplier`](https://android.googlesource.com/platform/external/google-breakpad/+/refs/tags/android-17.0.0_r1/src/processor/simple_symbol_supplier.cc) 实现目录查找，[`BasicSourceLineResolver`](https://android.googlesource.com/platform/external/google-breakpad/+/refs/tags/android-17.0.0_r1/src/processor/basic_source_line_resolver.cc) 完成地址到符号和行号的解析。

Breakpad 客户端不是“在 signal handler 中调用 `libunwind` 并拼出完整栈”这么简单。成熟实现会尽量缩短信号上下文内工作，并用受控 clone/fork、预分配状态或进程外 handler 生成 dump。Crashpad 进一步强调独立 handler 进程，但 Android 集成仍有 signal 入口、进程权限、`ptrace`、启动时机和 OEM 兼容问题。

### 符号文件治理

每次发布至少归档以下对象：

- 最终 APK/AAB 和版本、渠道、ABI 清单；
- 每个发布 `.so` 的 Build ID；
- 未 strip ELF、拆分 debug info 或 Breakpad `.sym`；
- 编译器、NDK、AGP、LTO 和 strip 配置；
- 第三方 Native SDK 的版本与供应商符号获取方式；
- 产物哈希、访问权限和保留策略。

上传 Play 的应用可以配置 `android.buildTypes.release.ndk.debugSymbolLevel`。`SYMBOL_TABLE` 提供函数名，`FULL` 还提供文件和行号；具体体积限制与配置以 [官方 Native debug symbols 文档](https://developer.android.com/build/include-native-symbols)为准。自建服务也应以 Build ID 为主键，版本号只作检索维度，不能替代二进制身份。

符号化服务需要记录“未找到模块”“identifier 不匹配”“只有函数无行号”“unwind 失败”等状态。返回 `??` 时不能自动判定为业务库被 strip；也可能是地址换算、ABI、符号包或 module identifier 错误。

## 常见崩溃模式与排查顺序

### 先读系统给出的强证据

建议顺序如下：

1. 核对 app version、ABI、进程、线程、Build ID；
2. 读 signal、`si_code`、Cause、abort message 和 allocator 报告；
3. 符号化崩溃线程，再看其他线程；
4. 将 fault address 放回 maps，判断映射、权限和 tag；
5. 检查寄存器与相关内存，但不越过 ABI 和优化边界；
6. 用能复现该类错误的 sanitizer、MTE 或 allocator 工具验证假设。

### `SIGSEGV`：空指针、越界与悬空指针

- fault address 为 0 或较小偏移，常见于 null base 加字段偏移，但也要用崩溃指令确认读取了哪个 base register；
- 地址位于对象邻近区域，可能是 heap/stack buffer overflow；
- 地址曾有效但当前未映射，可能是 UAF、`munmap` 后访问或损坏指针；
- `SEGV_ACCERR` 常见于写只读页、执行不可执行页或访问 guard page；
- MTE/GWP-ASan 报告若给出 allocation/deallocation stack，其证据强于仅凭地址形态的猜测。

`pc` 落在 `libart.so` 不能直接推断为 JNI 错误。它也可能是 Java/Native 过渡、GC、类链接、运行时检查或被 Native 内存破坏后的受害点。要看相邻 app Native frame、JNI 调用、CheckJNI/allocator 报告和可复现性。

### `SIGABRT`：谁主动判定状态不可接受

从 abort message 向上找触发者：

- libc/Scudo/GWP-ASan 检测到 double free、invalid free、heap corruption；
- `std::terminate` 处理未捕获 C++ 异常或 noexcept 违约；
- `CHECK`、assert、fdsan、FORTIFY 或 JNI 检查失败；
- 应用或 SDK 显式调用 `abort()`。

现代 NDK 构建是否启用 C++ exceptions 取决于构建配置，不能写成“NDK 默认 `-fno-exceptions`”。启用异常后，未在 Native 边界捕获的异常仍可能进入 `std::terminate`；禁用时，含 `throw` 的代码通常直接无法按预期编译。

### `SIGBUS`：优先检查文件映射生命周期

访问 `mmap` 文件时，如果底层文件被截断，读取仍在原映射范围但已超出新文件末尾的页可能触发 `SIGBUS`。需要记录文件 inode/长度、映射 offset/length、truncate/replace 时序和多进程写入者。

对齐约束取决于架构、指令和访问类型。原子对象、SIMD 指令、packed struct 与来自网络/文件的强转指针都值得检查，但不能把所有 ARM64 `SIGBUS` 都归为未对齐。

### JNI 边界

JNI 诊断至少覆盖：

- 静态命名或 `RegisterNatives` 的 method、signature 与函数指针是否一致；常规失败通常表现为 `UnsatisfiedLinkError`，手写 `dlsym` 或错误函数指针才更可能跳到错误地址；
- 每次 JNI 调用后是否存在 pending Java exception；有异常时继续调用多数 JNI API 会扩大问题；
- local/global/weak global reference 生命周期是否正确；局部引用容量是实现和上下文相关限制，不使用固定“512 个”作为跨版本契约；
- `jobject` 是受 GC 管理的句柄，不能当作稳定 C++ 对象地址解引用或跨线程裸存；
- `GetPrimitiveArrayCritical`、字符串指针和 direct buffer 地址是否遵守持有期限；
- C++ exception 是否在 JNI 导出函数边界内转换成 Java exception 或错误结果，不能穿越 C ABI/JNI 边界。

`PushLocalFrame`/`PopLocalFrame` 和 `DeleteLocalRef` 用于约束循环中的局部引用；debug 构建开启 CheckJNI 能更早暴露错误。相关基础见 [1.15 JNI / NDK 性能与安全边界](../../part1-fundamentals/ch01-architecture/15-jni-ndk-performance.md)。

## 用内存工具验证，而不是继续猜地址

| 工具 | 适合阶段 | 能发现什么 | 关键限制 |
|---|---|---|---|
| Recoverable GWP-ASan | Android 14+ 线上抽样 | 部分 heap UAF 与 heap buffer overflow，并写入 Native crash report | 抽样低；报告后继续运行不代表内存状态安全 |
| HWASan | 自动化测试、dogfood | heap/stack 越界、UAF 等，提供分配和释放栈 | 仅 64 位，CPU/内存/包体开销高 |
| MTE | 支持硬件上的测试与有控制的线上策略 | tag mismatch，帮助发现与缓解内存破坏 | 仅 64 位且依赖硬件/系统与构建策略，存在漏检概率 |
| ASan | HWASan 不适用的旧设备或遗留环境 | 多类地址错误 | 官方已不再积极支持，打包和运行开销高 |
| malloc debug | 可调试构建与专项复现 | 分配回溯、guard、填充等 allocator 诊断 | 启动配置和开销取决于选项，不适合作为通用线上方案 |

Android 14+ 未显式配置时会在约 1% app launches 使用 Recoverable GWP-ASan。它生成一次报告后允许进程继续，但官方明确说明行为已不再有定义；团队仍应高优先级修复。对这种 fault，自定义 `SIGSEGV` handler 不会收到回调，不能用“APM 没捕获”否定报告。

工具选择与当前命令以 [Memory error debugging and mitigation](https://developer.android.com/ndk/guides/memory-debug)、[GWP-ASan](https://developer.android.com/ndk/guides/gwp-asan)和 [HWASan](https://developer.android.com/ndk/guides/hwasan)为准。`wrap.sh` 只用于可调试 APK，并需要随 ABI 正确打包；不要把一条 `setprop wrap.<package>` 命令当成所有设备都能工作的 ASan 开关。

## 线上 Native Crash 采集方案

| 方案 | 证据 | 优势 | 边界 |
|---|---|---|---|
| 系统 tombstone / bugreport | 系统完整文本或 protobuf、线程、maps、allocator 信息 | 与平台 crash 流程一致 | 生产 app 不能直接读目录；保留数量与获取权限有限 |
| `ApplicationExitInfo` | API 30+ 退出元数据，API 31+ 可取 Native tombstone protobuf | 可在下次启动补采集，覆盖进程内 SDK 来不及完成的场景 | 非实时；trace 可能为 `null`，必须去重 |
| Google Play / 设备平台 | 聚类、受影响用户与设备维度 | 无需自建 signal handler | 数据条件、延迟、符号上传与上下文受平台约束 |
| Breakpad / Crashpad / 托管 SDK | minidump、业务 breadcrumb、服务端符号化 | 可控制上下文和告警 | signal handler 兼容、隐私、成本、符号和版本维护 |
| 自研 `sigaction` | 自定义极小 envelope | 表面接入少 | 最容易破坏平台 handler、漏 tombstone 或在 signal context 二次崩溃 |

建议把系统与 SDK 记录按进程启动 ID、时间、signal、tid、Build ID 和关键 frame 去重，同时保留来源字段。SDK minidump 与 `ApplicationExitInfo` tombstone 是互补证据，不应只保留最早到达的一份。

### Signal handler 的硬边界

POSIX signal context 中只能调用 async-signal-safe 操作。工程上应进一步缩小范围：

- 不调用 `malloc/new`、`free/delete`、`std::string`、iostream、普通日志格式化和大多数 libc 高层函数；
- 不进入 JNI、ART、数据库、网络栈和业务锁；
- 不使用可能已被当前线程持有的 mutex；
- 使用预分配内存、固定大小结构、原子状态和已打开 fd；
- 处理重入、嵌套信号、多个线程同时 fault、备用信号栈和写入中断；
- 保存并正确恢复/转发原 action、signal mask 与 `SA_SIGINFO` 等语义。

通过 `dlopen("libc.so") + dlsym("sigaction")` 绕过 ART wrapper，不是“保证 APM handler 被调用”的推荐方案。Android 的 SignalChain 自己就用类似方式寻找真实 libc 符号，以保护平台先行处理；应用再次绕过会直接竞争内核 disposition。若 handler 消费信号、不正确转发或返回到同一条 fault 指令，系统 tombstone 可能缺失，进程也可能陷入重复信号。

自研前应评估成熟 SDK 是否已经处理 Android 版本、handler 顺序、alternate stack、恢复默认 disposition和重新投递信号。任何自研实现都要在 Android 10～17、各 ABI、MTE/GWP-ASan、多个 SDK 共存和 16 KB page-size 设备上做故障注入。

### 多个 Native Crash 采集器的冲突验证

接入第二个采集器后缺少堆栈，不一定是 handler 覆盖。先把产物链拆成四段：现场是否生成、文件是否完整、符号是否匹配、上传与解析是否成功。只有原始产物和 Build ID 已确认无误，才继续检查 signal disposition。

内核对每个信号维护一份 disposition；后一次 `sigaction()` 会替换前一次，并通过 `oldact` 返回旧值。保存旧 handler 不等于自动获得安全的调用链：`SIG_DFL`、`SIG_IGN`、`SA_SIGINFO`、线程 mask、重复进入、altstack 和重新投递都必须保留原语义。两个闭源 SDK 都试图充当链路 owner 时，很难证明组合正确。

下面的只读探针只适合 debuggable 集成测试，调用点位于各 SDK 初始化前后，而不是 fatal handler 内：

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

函数地址受 ASLR 影响，只用于同一进程内比较。即使入口被正确串接，也必须用行为结果验收。推荐让一个组件负责 fatal Native 信号，其他 SDK 关闭 Native 捕获，只保留 Java、性能或上传能力；依赖升级后重跑冲突测试。

每个支持的 ABI 和主要 Android 版本至少注入 `abort()`、空指针读写、栈溢出、多线程同时 fault，以及设备支持时的 MTE/GWP-ASan 错误。通过标准同时覆盖应用产物、`ApplicationExitInfo`、系统 tombstone、离线符号化和服务端接收；缺少其中一项时，应标出失败阶段，不能用一个“堆栈完整率”掩盖原因。

## 线程级“安全点”：只能作为实验性故障隔离

### `sigsetjmp` / `siglongjmp` 能做什么

`sigsetjmp(env, 1)` 保存当前线程的寄存器上下文和 signal mask；同一线程后续调用 `siglongjmp` 可以回到仍然存活的保存点。它不会修复内存，只会改变控制流。

要满足的最低条件包括：

- `sigjmp_buf` 属于当前线程，保存点所在栈帧尚未返回；
- 跳转目标是预先设计的错误出口，而不是继续执行原任务；
- 不依赖跳过区间内应执行的 C++ 析构等清理；
- 不假设业务锁、allocator、JNI、TLS 或全局状态仍一致；
- 只处理经过严格限定的同步故障，其他信号仍交给系统。

C++ 析构和栈展开被跳过，自动变量还受 `setjmp`/`longjmp` 语义限制。若 fault 来自 heap corruption、栈破坏或错误函数指针，跳回后继续使用同一进程可能造成数据损坏、死锁或稍后在无关位置崩溃。

### mooner `prevent_pthread_crash` 的证据边界

[TestPlanB/mooner](https://github.com/TestPlanB/mooner) 展示了一个实验方案：用 ByteHook 代理 `pthread_create`，在线程 start routine 外层保存 `sigjmp_buf`，目标线程 fault 时跳回 wrapper，再结束该线程。

它适合作为研究样本，不能直接推导出通用线上容错能力：

- 示例中的全局 `sig_env` / `handleFlag` 若不是严格 thread-local，会在多线程同时运行时覆盖上下文；
- 代理 `pthread_create` 只能覆盖经指定 hook 点创建且执行在 wrapper 内的任务；
- `siglongjmp` 跳过锁释放、RAII 析构、JNI detach 和线程局部清理；
- fault 已经破坏共享 heap 或全局状态时，结束单个线程也不能恢复进程一致性；
- 若转发旧 signal action、恢复 disposition 或重新投递不完整，会干扰 debuggerd。

若业务仍要试验，应限制在可丢弃、无共享可变状态的隔离 worker；命中后停止接收新任务，保存最小证据，并尽快重建独立进程或让宿主按明确策略退出。不要在跳回后 Attach JVM、分配大量对象并执行普通 Java 回调来宣称“线程已经恢复”。

### ByteHook、shadowhook 与私有 pthread 状态

[ByteHook](https://github.com/bytedance/bhook) 通过 PLT/GOT 改写调用目标，[shadowhook](https://github.com/bytedance/android-inline-hook) 修改函数入口或指令流。二者是 hook 基础设施，不提供被 hook 对象的线程安全与生命周期正确性。

Android 17 使用它们时要重新验证：

- 目标符号是否导出、是否被 LTO/inlining 或 direct call 绕过；
- linker namespace、RELRO、PAC/BTI、CFI 与 16 KB page size 的影响；
- 动态加载/卸载、新增 `.so` 和多 ABI；
- hook 回调重入、unhook 时并发调用和原函数递归；
- 第三方库声明的 Android/NDK 支持范围。

不要依赖 `pthread_mutex_t` 私有布局或某个版本中的 `state == 0xffff` 来判断 mutex 已销毁。bionic 内部结构不是 NDK 稳定 ABI，厂商和 Android 版本都可能变化。更可靠的做法是在自有锁包装层维护生命周期 generation、owner 和销毁状态，并用 HWASan/MTE、压力测试和严格所有权修复 use-after-destroy。

## Native Crash 治理清单

### 构建阶段

- 每个发布 ABI 生成并归档 Build ID、未 strip ELF 或 debug symbols；
- 在 CI 校验 APK/AAB 中 `.so` 与符号归档一一对应；
- 为自有 Native 模块启用合理的 unwind 信息和 arm64 frame pointer 策略；
- 使用 HWASan/MTE、fuzz、压力与并发测试覆盖内存和 JNI 边界；
- 对第三方 Native SDK 建立版本、符号和撤回开关清单。

### 采集阶段

- 系统 `ApplicationExitInfo` 与 SDK minidump 都保留来源和唯一键；
- signal handler 只写固定大小 envelope，不做网络和 JNI；
- 记录 app/process/session、ABI、Build ID、signal、`si_code`、tid 与关键 frame；
- 验证 handler 共存时系统 tombstone 仍能生成；
- 对 crash loop 提供禁用故障 Native 功能或安全模式。

### 诊断与验证

- 先匹配 Build ID，再谈源码行号；
- 把 fault address 放回 maps 和崩溃指令，不用地址形态替代证据；
- 对 allocator/MTE/GWP-ASan 报告优先读取 allocation/deallocation stack；
- JNI crash 同时检查 pending exception、引用生命周期、线程和函数签名；
- 修复后用同类 sanitizer 或故障注入验证，并观察原簇是否迁移为新 signal、ANR 或数据损坏。

## 源码与文档锚点

- 平台：AOSP [`android-17.0.0_r1`](https://android.googlesource.com/platform/manifest/+/refs/tags/android-17.0.0_r1/)
- SignalChain：[`art/sigchainlib/sigchain.cc`](https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/sigchainlib/sigchain.cc) · [`art/runtime/fault_handler.cc`](https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/runtime/fault_handler.cc)
- debuggerd：[`debuggerd_handler.cpp`](https://android.googlesource.com/platform/system/core/+/refs/tags/android-17.0.0_r1/debuggerd/handler/debuggerd_handler.cpp) · [`crash_dump.cpp`](https://android.googlesource.com/platform/system/core/+/refs/tags/android-17.0.0_r1/debuggerd/crash_dump.cpp) · [`tombstone.cpp`](https://android.googlesource.com/platform/system/core/+/refs/tags/android-17.0.0_r1/debuggerd/libdebuggerd/tombstone.cpp) · [`tombstoned.cpp`](https://android.googlesource.com/platform/system/core/+/refs/tags/android-17.0.0_r1/debuggerd/tombstoned/tombstoned.cpp)
- unwind：[`libunwindstack/Unwinder.cpp`](https://android.googlesource.com/platform/system/unwinding/+/refs/tags/android-17.0.0_r1/libunwindstack/Unwinder.cpp)
- Breakpad：[`symbol_files.md`](https://android.googlesource.com/platform/external/google-breakpad/+/refs/tags/android-17.0.0_r1/docs/symbol_files.md) · [`simple_symbol_supplier.cc`](https://android.googlesource.com/platform/external/google-breakpad/+/refs/tags/android-17.0.0_r1/src/processor/simple_symbol_supplier.cc) · [`basic_source_line_resolver.cc`](https://android.googlesource.com/platform/external/google-breakpad/+/refs/tags/android-17.0.0_r1/src/processor/basic_source_line_resolver.cc)
- 应用可见 tombstone：[`ApplicationExitInfo`](https://developer.android.com/reference/android/app/ApplicationExitInfo)
- NDK 诊断：[ndk-stack](https://developer.android.com/ndk/guides/ndk-stack) · [Memory error debugging](https://developer.android.com/ndk/guides/memory-debug) · [GWP-ASan](https://developer.android.com/ndk/guides/gwp-asan) · [HWASan](https://developer.android.com/ndk/guides/hwasan)
