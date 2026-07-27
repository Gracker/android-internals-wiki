---
title: "Android 17 信号处理架构迁移与 debuggerd bionic/linker 重构"
chapter: "20.19"
status: ready-for-review
applicable_versions: "Android 14 (API 34) - Android 17 (API 37)"
tags: ["signal-handler", "debuggerd", "bionic", "linker", "crash-monitoring", "native", "MTE", "GWP-ASan"]
related_chapters: ["20.3", "20.9", "20.18", "20.13"]
created_by: "task2a-knowledge-gap"
created_date: "2026-07-07"
drafted_date: "2026-07-07"
last_verified: "2026-07-07"
last_verified_against: "AOSP android-17.0.0_r1"
confidence: high
sources:
  - type: aosp
    path: "bionic/linker/linker_debuggerd.h"
  - type: aosp
    path: "bionic/linker/linker_debuggerd_android.cpp"
  - type: aosp
    path: "bionic/linker/linker_main.cpp"
  - type: aosp
    path: "system/core/debuggerd/handler/debuggerd_handler.cpp"
  - type: aosp
    path: "system/core/debuggerd/include/debuggerd/handler.h"
  - type: deepresearch
    path: "DeepResearch/2026-07-07-android17-linker-debuggerd-init-wiring-source.md"
---

# 20.19 Android 17 信号处理架构与 debuggerd / linker 协作

这一章的题名容易让人产生误解：`debuggerd` 的核心实现没有在 Android 17 搬进 Bionic linker。Android 17 仍由 `system/core/debuggerd/` 维护 handler、`crash_dump`、tombstone 编码和 `tombstoned`；linker 只负责在进程早期安装 handler、提供 libc 共享状态，并把可恢复信号入口暴露给 ART 的 signal chain。

对 Android 14、15、16、17 的 AOSP 首个发布标签逐项比较后，可以得到一个更可靠的结论：

| 机制 | Android 14 | Android 15 | Android 16 | Android 17 |
|---|---|---|---|---|
| `linker_main()` 早期调用 `linker_debuggerd_init()` | 已存在 | 保持 | 保持 | 保持 |
| `bionic/linker/linker_debuggerd_android.cpp` 适配层 | 已存在 | 保持 | 保持 | 增加 Runtime APEX 退役开关分支 |
| ART `sigchainlib/` | 已位于 ART 仓库 | 保持 | 保持 | 保持，修正 SIGSYS 默认/忽略处理 |
| debuggerd wire protocol v4 | 已存在 | 保持并扩展字段 | 保持 | 结构整理，版本号仍为 4 |
| `SA_EXPOSE_TAGBITS` | 已存在 | 保持 | 保持 | 保持 |
| Recoverable GWP-ASan | 已存在 | 保持 | 保持 | 保持 |
| pseudothread 可用栈 | 固定 8 个编译期 `PAGE_SIZE` 页 | 改用 8 个运行时 `getpagesize()` 页 | 保持 | 保持 |
| permissive MTE 经过 ART signal chain 恢复 | GWP-ASan 恢复钩子已存在 | 恢复钩子扩展到 MTE | 保持 | 保持并修正按进程属性读取 |

所以，本章的重点是 Android 17 当前架构及其版本边界，而非构造一条不存在的“大迁移”叙事。

## 要点

### 🔹 三个参与方，各自负责什么

Android 应用进程的 native fatal signal 涉及三套代码：

| 组件 | Android 17 源码位置 | 职责 |
|---|---|---|
| Bionic linker | `bionic/linker/` | 早期调用 `debuggerd_init()`；提供 abort message、fdsan、GWP-ASan、Scudo 等 libc 共享状态 |
| debuggerd | `system/core/debuggerd/` | 安装 fatal signal handler；创建 pseudothread 与 `crash_dump`；生成 tombstone |
| ART sigchain | `art/sigchainlib/` | 在应用进程中让 ART 特殊 handler、debuggerd 可恢复钩子与应用 handler 共存 |

ART 应用进程的链路可以概括为：

```text
linker_main
  -> linker_debuggerd_init
  -> debuggerd_init：安装 debuggerd handler
  -> 加载应用依赖和运行构造函数
  -> ART FaultManager 通过 libsigchain claim 需要的信号
  -> libsigchain 保存原 debuggerd action，并成为内核看到的 dispatcher
  -> 应用或 Crash SDK 调用 sigaction 时，更新 dispatcher 后面的用户 action
```

这段顺序解释了 SDK 为什么必须保存并转交旧 handler：在 ART 应用进程中，旧 action 可能通向 debuggerd；在 native-only 进程中，它也可能直接就是 debuggerd handler。覆盖后不转交，会丢掉系统 tombstone 或可恢复内存错误处理。由 Zygote 派生的应用进程继承其进程启动期已建立的系统处理状态，应用 `ContentProvider` 和 `Application` 初始化发生得更晚。

### 🔹 linker 的工作是早期 wiring

#### 注册时机

Android 17 的 `linker_main()` 依次执行环境清洗、系统属性初始化、平台属性初始化，然后调用 `linker_debuggerd_init()`。此时还没有进入应用依赖库的构造函数。

`linker_debuggerd_init()` 组装三类回调后调用 `debuggerd_init()`：

- `get_process_info`：读取 libc shared globals 中的诊断地址。
- `get_gwp_asan_callbacks`：提供 GWP-ASan 恢复前后的回调。
- `post_dump`：通知 GDB 动态库列表发生变化。

这套 wiring 在 Android 14 标签中已经存在。Android 17 不能被描述为“把 debuggerd 提前到 linker 初始化”；在本章适用范围内，早期注册一直是基线行为。

#### Android 17 的 Runtime APEX 条件分支

Android 17 在这条路径上增加了 `RELEASE_DEPRECATE_RUNTIME_APEX` 构建开关：

- 开关启用时，handler 从 `/system/bin/crash_dump32|64` 启动 `crash_dump`。
- 否则仍使用 `/apex/com.android.runtime/bin/crash_dump32|64`。
- linker 侧的 process info 与 GWP-ASan callbacks 也按该开关或 `__ANDROID_APEX__` 条件编译。

这是构建布局兼容处理，不能据此认定 debuggerd 逻辑迁入 linker。具体产品镜像走哪条路径取决于发布配置，应用代码不应硬编码任一路径。

### 🔹 两层 signal handler：内核 action 与 ART signal chain

#### debuggerd 注册哪些信号

`debuggerd_register_handlers()` 为以下信号安装同一份 action：

- `SIGABRT`
- `SIGBUS`
- `SIGFPE`
- `SIGILL`
- `SIGSEGV`
- `SIGSTKFLT`
- `SIGSYS`
- `SIGTRAP`

action 使用 `SA_RESTART | SA_SIGINFO | SA_ONSTACK | SA_EXPOSE_TAGBITS`。在 debuggable 平台构建上，`debug.debuggerd.disable=1` 可以跳过这些 fatal signal；内部的 `BIONIC_SIGNAL_DEBUGGER` 仍会注册。

这里的 `SA_ONSTACK` 只表示“当前线程已经配置 alternate signal stack 时使用它”。`debuggerd_init()` 自己没有调用 `sigaltstack()`，也没有为进程中的每个线程统一安装 altstack。

#### ART 为什么还需要 `libsigchain`

ART 需要先检查某些 fault 能否转换成受控的运行时行为，例如隐式空指针异常、栈溢出或运行时内部 fault。直接让 ART 与 SDK 反复覆盖 `SIGSEGV` action，会破坏任意一方。

`libsigchain` 通过全局符号优先级包装 `sigaction`、`signal` 和 `sigprocmask`。`FaultManager::Init()` 使用内部的 `AddSpecialSignalHandlerFn()` claim `SIGSEGV`，并在需要时 claim `SIGBUS`、`SIGSYS`。claim 时，`libsigchain` 把内核中原有的 debuggerd action 保存下来，再把 `SignalChain::Handler` 注册给内核。

一个已 claim 信号的分发顺序如下：

```text
kernel
  -> SignalChain::Handler
     1. ART / native bridge 等 special handlers
     2. libdl::android_handle_signal
        -> linker::debuggerd_handle_signal
        -> 只处理可恢复 GWP-ASan 或 permissive MTE
     3. 当前用户 action
        -> 无 SDK 时通常是此前保存的 debuggerd action
        -> 有 SDK 时是 SDK action；SDK 应继续调用保存的旧 action
```

`android_handle_signal()` 返回 `true` 时，signal chain 立即返回，用户 action 不再执行；返回 `false` 才进入用户 action。官方 GWP-ASan 文档也明确说明：Recoverable GWP-ASan fault 不会调用应用自定义的 `SIGSEGV` handler。

#### `sigaction()` 在 claimed 信号上仍然有效

`libsigchain` 的 wrapper 不会把新的 action 直接交给内核，而是更新 `chains[signal].action_`。应用 handler 仍会在 special handlers 和可恢复 debuggerd 钩子之后执行。

这带来三个工程结论：

1. “普通 `sigaction()` 在 ART 进程中完全无效”是错误判断。
2. 通过 `sigaction(..., &old_action)` 得到的是 signal chain 保存的用户 action，不是内核当前的 `SignalChain::Handler`。
3. SDK 仍要按标准链式安装方式保存旧 action；不能根据查询结果的函数地址猜测自己位于第几层。

#### 不要接入 ART 私有 special handler

Android 17 的 `SignalChain` 内部只有两个 `special_handlers_` 槽位，`AddSpecialSignalHandlerFn()` 超额时会终止进程。但这些槽位属于 ART 与平台 native bridge 等内部实现：

- 接口不属于 NDK 公共 API。
- `libsigchain` 的 APEX stub version script 不导出这些入口。
- 槽位数量、调用顺序和 TLS 重入策略都可随平台实现调整。

Crash SDK 不应通过 `dlsym(RTLD_DEFAULT, "AddSpecialSignalHandlerFn")` 争抢内部槽位。标准 `sigaction()`、保存旧 action、最小化采集并可靠转交，才是应用可控制的兼容边界。

### 🔹 两块栈解决两类问题

#### alternate signal stack

altstack 属于线程。某线程调用 `sigaltstack()` 后，带 `SA_ONSTACK` 的 signal action 才能在该线程的备用栈上运行；其他线程不会自动继承一份可用的独立 altstack。

它解决的是“崩溃线程原栈已溢出或接近耗尽时，handler 还有空间执行”。在没有配置 altstack 的线程上，`SA_ONSTACK` 不会创造备用栈，handler 仍使用该线程当前栈。

Crash SDK 如果为自己创建的 native 线程提供 altstack，需要在线程入口完成安装，并验证 guard page、对齐、析构与线程退出。只在 `Application.onCreate()` 配置一次，覆盖不了后续所有线程。

#### debuggerd pseudothread 栈

`debuggerd_init()` 还会预留一块独立映射，供崩溃发生后 `clone()` 创建 pseudothread。Android 17 的大小关系是：

```text
usable pseudothread stack = 8 * getpagesize()
whole virtual mapping     = 10 * getpagesize()
guard pages               = 1 page at each end
```

4 KB 页设备对应 32 KiB 可读写栈和 40 KiB 整段虚拟映射；16 KB 页设备对应 128 KiB 可读写栈和 160 KiB 整段虚拟映射。这里描述的是地址空间映射大小，不能直接当作常驻 RSS。

Android 14 版本使用编译期 `PAGE_SIZE`。Android 15 改为运行时 `getpagesize()`，Android 17 延续该实现。页大小自适应由这次替换带来，和“动态估算 signal altstack 所需容量”无关。

### 🔹 fatal signal 到 tombstone 的精确路径

`debuggerd_signal_handler()` 起初仍运行在崩溃线程上，可能位于该线程已配置的 altstack。它取得 process info，判断 GWP-ASan / MTE 恢复条件，并用 `crash_mutex` 保证同一时刻只有一个线程进入 dump 主流程。

非 fallback 路径按下面的阶段运行：

```text
crashing thread
  -> 暂时 PR_SET_DUMPABLE=1，并按内核能力放宽 ptracer
  -> clone pseudothread
       flags: CLONE_THREAD | CLONE_SIGHAND | CLONE_VM
       deliberately omits CLONE_FILES
  -> crashing thread 通过 futex 等待 pseudothread 完成

pseudothread
  -> 在自己的 FD table 中关闭一批描述符，释放可用槽位
  -> 创建传递 CrashInfo 的 pipe
  -> _Fork 后 exec crash_dump
  -> 等待 crash_dump 建立 ptrace 关系
  -> double-clone 一个保留地址空间的 VM snapshot

crash_dump
  -> ptrace 停止并读取各线程寄存器
  -> 读取 CrashInfo、maps、open files 与 allocator 元数据
  -> 从 VM snapshot 使用 libunwindstack 回溯
  -> 交给 tombstoned 写文本和 protobuf tombstone
```

`CLONE_VM` 让 pseudothread 共享进程地址空间，`CLONE_SIGHAND` 也是 `CLONE_THREAD` 所需组合的一部分。省略 `CLONE_FILES` 才是这里的重要设计：即使原进程耗尽文件描述符，pseudothread 也能在独立 FD table 中关闭描述符并创建 pipe。

所以，pseudothread 没有消除 ptrace。Android 17 的 `crash_dump` 仍通过 ptrace 停止线程、读取非崩溃线程寄存器，并协调 VM snapshot。完整回溯路径见 20.18。

#### `PR_SET_DUMPABLE` 已由系统临时处理

handler 会读取原 `dumpable` 值，临时设为 1，完成 pseudothread 流程后恢复；支持 Yama ptrace 限制的内核上也会临时设置 `PR_SET_PTRACER_ANY` 并恢复。

因此，SDK 不需要在崩溃现场自行把 `dumpable` 改成 1。此类额外操作会扩大短暂攻击面，还可能与系统恢复顺序冲突。若应用在正常运行期主动设置 `dumpable=0`，仍需用目标 OEM、SELinux 策略和 fallback 路径验证 tombstone 完整性。

### 🔹 CrashInfo wire protocol：v4 不是 Android 17 新协议

pseudothread 通过 pipe 向 `crash_dump` 写四部分数据：

```text
part 1: uint32_t version
part 2: siginfo_t
part 3: ucontext_t
part 4:
  dynamic payload -> debugger_process_info
  static payload  -> abort message address
```

Android 17 以 `process_info.fdsan_table != nullptr` 选择 v4，否则选择 v1。v4 payload 包含：

- abort message；
- fdsan table；
- GWP-ASan allocator state 与 allocation metadata；
- Scudo stack depot、region info、ring buffer 及其尺寸；
- `recoverable_crash` 标记；
- crash detail page。

v4 在 Android 14 标签中已经存在。Android 17 重排了 `CrashInfoDataCommon` / `CrashInfoDataDynamic` 的结构表达，并用 `static_assert` 核对发送结构与协议字段偏移，没有把版本改为 v5。

源码注释给出的理由是：动态 sender 与 receiver 版本锁定。linker 也专门避免让可能与 APEX `crash_dump` 版本不匹配的 bootstrap linker 传递 process info。这个 pipe payload 是平台内部 ABI，OEM 修改时需要保持整套构建一致；应用与 SDK 不应解析或构造它。

### 🔹 `SA_EXPOSE_TAGBITS` 的范围

Android 17 debuggerd action 请求 `SA_EXPOSE_TAGBITS`，目的是让支持该标志的内核在 fault signal 的 `siginfo_t.si_addr` 中保留地址 tag，便于诊断 MTE。

它的边界需要说清：

- 该标志在 Android 14 源码中已经存在。
- Linux 语义重点是 fault address 的 tag bits，不能把它扩写为“保证所有 ucontext 寄存器和返回地址自动保留或清洗”。
- `libsigchain` 会探测内核是否支持该 flag。
- 转交用户 `SA_SIGINFO` handler 前，如果用户 action 没请求该 flag，`libsigchain` 会对适用 fault 的 `si_addr` 调用内部 `untag_address()`。
- `untag_address()` 位于 Bionic platform 私有头文件，不是应由 NDK SDK 直接依赖的公共 API。

因此，应用 handler 收到的 `si_addr` 可能已经被 signal chain 去 tag。SDK 若需要 MTE 诊断，应优先保留系统 tombstone；自定义格式要同时记录 signal、`si_code`、原始字节和自身是否获得 tag 的能力，不能假设 Android 17 上总能看到 tagged fault address。

### 🔹 Recoverable GWP-ASan 与 permissive MTE

#### Recoverable GWP-ASan

Android 14 / API 34 起，应用支持 Recoverable GWP-ASan。平台命中被采样保护的地址后：

1. debuggerd 生成一次带分配/释放证据的 crash report。
2. allocator 回调解除对应保护，使线程可以继续。
3. 同一进程后续命中仍会执行修复回调，但 debuggerd 只为首次命中生成报告，避免 ActivityManager 因短时间多次 native crash 记录而终止应用。
4. 在 ART 应用进程中，`android_handle_signal()` 返回 `true`，用户自定义 `SIGSEGV` handler 不会收到这次 fault。

“Recoverable”只描述平台处理策略。官方文档明确指出：内存破坏已经发生，进程后续行为未定义，仍可能在另一个位置崩溃。治理系统必须把该报告当作高优先级真实缺陷，不能当成无害告警。

#### permissive MTE

permissive MTE 是受属性或测试环境控制的平台诊断模式。Android 17 遇到 `SEGV_MTESERR` 或 `SEGV_MTEAERR` 且 permissive 条件成立时，会：

- 把当前线程的 MTE TCF 模式改成 `PR_MTE_TCF_NONE`；
- 生成 recoverable crash report；
- 可按配置使用 `CLOCK_THREAD_CPUTIME_ID` timer，在一段线程 CPU 时间后恢复原检查模式；
- 返回并让线程继续。

同步 MTE 的 `SEGV_MTESERR` 能对应触发 load/store；异步 MTE 的 `SEGV_MTEAERR` 可能延后到内核入口才上报，并没有精确 fault address。两者不能用同一套“重试故障指令”解释。

Android 14 的 direct debuggerd 路径已有 permissive MTE 处理；Android 15 把 ART signal chain 的 `debuggerd_handle_signal()` 扩展到 permissive MTE，使应用进程也能在用户 handler 前完成该恢复。Android 17 的相关修正是用不分配内存的 `/proc/self/cmdline` 读取进程名，以便查询按进程配置的 permissive 属性。

#### SDK 不要自行判定“可恢复”

仅看到 `SEGV_MTESERR` / `SEGV_MTEAERR`，无法得知平台属性、allocator 回调和当前进程路径是否允许恢复。GWP-ASan fault 还需要判断地址是否属于受保护采样区域。

SDK 的安全策略是保留系统链：

- ART recovery hook 成功时，SDK handler 本来就不会被调用。
- SDK handler 被调用时，不能仅凭 `si_code` 吞掉信号。
- SDK 完成最小记录后，应按保存的旧 action 继续分发，让 debuggerd 或其他先安装 handler 作出决定。

### 🔹 `BIONIC_SIGNAL_DEBUGGER` 是平台内部协议

Android 17 把 `BIONIC_SIGNAL_DEBUGGER` 定义为 `__SIGRTMIN + 3`。平台 `debuggerd_client` 会先向 `tombstoned` 注册 intercept，再通过 `sigqueue()` 发送该信号：

- `si_value = 0` 请求 protobuf tombstone；
- `si_value = 1` 请求 native backtrace。

这条协议还包含目标 PID/TID、tombstoned socket、超时、fallback 特殊值和权限约束。直接 `kill()` 或硬编码实时信号编号绕过了这些条件，也可能与 Bionic 的保留信号用途冲突。

`BIONIC_SIGNAL_DEBUGGER`、`debuggerd_client` 和 `AddSpecialSignalHandlerFn()` 都不属于普通应用的 NDK 公共接口。Crash SDK 不应把它们包装成“主动采集 API”。普通应用获取自身历史 native tombstone 应使用 API 31 起的 `ApplicationExitInfo.getTraceInputStream()`；平台或 root 调试工具可使用其权限范围内的 debuggerd 命令。

### 🔹 async-signal-safe 规则没有在 Android 17 才收紧

`malloc()`、`free()`、`dlopen()`、`dladdr()`、C++ 容器、普通日志和 `pthread_mutex_lock()` 从来都不是应用 fatal signal handler 可依赖的通用安全操作。不能写成“Android 14 勉强可用，Android 17 才会失败”。

平台 debuggerd 源码内部会使用专门的 async-safe 日志、raw syscall，也会在受控流程里使用 mutex、property API、clone 和 fork 变体。这些选择依赖 Bionic 内部实现、进程启动时预分配状态和平台测试，不能据此放宽第三方 handler 的约束。

SDK handler 建议只做以下工作：

- 从参数复制固定大小的 `siginfo_t` 与 `ucontext_t`；
- 写入预分配缓冲或预打开 FD；
- 使用 `sig_atomic_t` 或经证明 lock-free 的极小重入标记；
- 记录失败与截断，不在 handler 中补做符号化；
- 转交保存的旧 action，并保留原信号退出语义。

即使 `write()` 属于 async-signal-safe，它仍可能在阻塞 FD 上卡住。崩溃通道还要设置非阻塞/超时策略，并处理 partial write 与 `EINTR`。

### 🔹 Android 17 中可以确认的相关改动

与 Android 16 首个发布标签比较，Android 17 这条链上的可见变化主要有：

| 位置 | Android 17 变化 | 影响 |
|---|---|---|
| `linker_debuggerd_android.cpp` | 增加 `RELEASE_DEPRECATE_RUNTIME_APEX` 条件 | Runtime APEX 退役配置下仍提供 process info / GWP-ASan callbacks |
| `debuggerd_handler.cpp` | `crash_dump` 路径按同一开关选择 `/system/bin` 或 Runtime APEX | 产品构建路径差异，应用不可硬编码 |
| `debuggerd_handler.cpp` | permissive MTE 的按进程属性改用无分配 cmdline 读取 | 避免 signal handler 中依赖会分配的字符串路径，并修正 fork 后进程名 |
| `protocol.h` / handler | 整理 CrashInfo common/dynamic 结构和偏移断言 | 内部 wire 表达更清楚，协议号保持 v4 |
| `crash_dump.cpp` / handler | 额外传递原父 PID 等上下文 | 改善 fork/快照场景下的进程关系记录 |
| `sigchain.cc` | `SIGSYS + SYS_SECCOMP + SIG_IGN` 改走默认处置并重新 raise | 避免把内核强制的 seccomp `SIGSYS` 当作可忽略信号 |

这些是局部兼容性和正确性修正。pseudothread、早期 linker wiring、sigchain 三段结构、wire v4 与 Recoverable GWP-ASan 都不是 Android 17 才出现。

## 扩展

### 🔸 Crash SDK 接入检查表

| 检查项 | 合格条件 | 典型故障 |
|---|---|---|
| handler 安装 | 每个信号保存对应旧 `sigaction` | 多个信号共用一份旧 action，转交错误 |
| handler 链 | 采集后按 `SA_SIGINFO`、`SIG_DFL`、`SIG_IGN` 等语义转交 | 吞掉 debuggerd，系统无 tombstone |
| 重入 | 二次 signal 有固定退出或降级路径 | handler 递归直到栈耗尽 |
| signal 安全 | 无分配、无普通锁、无动态链接解析 | allocator/loader 锁中二次死锁 |
| altstack | SDK 自有线程逐线程配置并带 guard | 只配置主线程，误以为覆盖全进程 |
| 系统私有 API | 不使用 reserved signal、debuggerd client、sigchain special API | 系统升级后符号缺失或协议冲突 |
| Recoverable GWP-ASan | 通过系统报告采集，不期待自定义 `SIGSEGV` handler 被调用 | 线上漏报或重复生成伪 crash |
| MTE | 区分 SYNC/ASYNC，保留系统 tombstone | 把异步 fault 错归到当前 PC |
| `dumpable` | 不在 signal handler 里自行切换 | 与系统临时恢复流程冲突 |
| 16 KB 页 | 不写死 pseudothread/altstack 字节数 | guard、对齐或容量假设失效 |

注册时机通常放在 SDK 初始化或 `ContentProvider` 即可。linker 的 debuggerd 注册早于普通应用库构造函数，使用 `_init` 争抢“更早”没有收益，还会增加加载器重入和依赖顺序风险。

### 🔸 建议的验证范围

一套 Crash SDK 至少在以下场景做真机或系统镜像测试：

1. `SIGABRT`、`SIGSEGV`、`SIGBUS`、`SIGILL`、`SIGFPE`、`SIGSYS` 各自保留原退出语义。
2. 两个线程近同时崩溃时，只产生一份主报告，其他线程不会永久死锁。
3. 文件描述符接近耗尽时，pseudothread 仍能建立 pipe 并启动 `crash_dump`。
4. 原 `dumpable=0`、`no_new_privs=1` 和常规状态分别覆盖系统主路径与 fallback。
5. 主栈溢出时，配置 altstack 的线程能保留原始 PC；未配置线程的失败能被识别。
6. ART 应用进程、纯 native 进程、isolated process 和多进程组件分别验证 handler 顺序。
7. Recoverable GWP-ASan 命中后，自定义 handler 不被调用，但 `ApplicationExitInfo` 能取得报告。
8. MTE SYNC 与 ASYNC 分开验证，不用 ASYNC 的上报 PC 做精确归因。
9. 4 KB 与 16 KB 页设备都运行同一套 crash case。
10. 多个 Crash/APM SDK 共存时，安装顺序交换后仍能到达系统 handler。

性能指标必须来自可复现设备、构建号、信号类型、线程数和 tombstone 大小。没有这些条件的“pseudothread 小于 1 ms”“Android 17 比 Android 14 快 15%”不能进入工程结论。

### 🔸 与相邻章节的分工

- 20.3：Native Crash 分类、信号收集与治理流程。
- 20.11：MTE 的模式、报告解读和灰度策略。
- 20.13：16 KB 页对 ELF、打包和 native 运行时的影响。
- 20.18：`crash_dump`、`libunwindstack`、地址归一化与符号化。
- 20.23：GWP-ASan 采样、Recoverable 模式和线上处置。

## 源码与官方资料

- [Bionic `linker_main.cpp`（android-17.0.0_r1）](https://android.googlesource.com/platform/bionic/+/refs/tags/android-17.0.0_r1/linker/linker_main.cpp)
- [Bionic `linker_debuggerd_android.cpp`（android-17.0.0_r1）](https://android.googlesource.com/platform/bionic/+/refs/tags/android-17.0.0_r1/linker/linker_debuggerd_android.cpp)
- [Bionic `dlfcn.cpp`（android-17.0.0_r1）](https://android.googlesource.com/platform/bionic/+/refs/tags/android-17.0.0_r1/linker/dlfcn.cpp)
- [debuggerd handler（android-17.0.0_r1）](https://android.googlesource.com/platform/system/core/+/refs/tags/android-17.0.0_r1/debuggerd/handler/debuggerd_handler.cpp)
- [debuggerd handler API（android-17.0.0_r1）](https://android.googlesource.com/platform/system/core/+/refs/tags/android-17.0.0_r1/debuggerd/include/debuggerd/handler.h)
- [debuggerd wire protocol（android-17.0.0_r1）](https://android.googlesource.com/platform/system/core/+/refs/tags/android-17.0.0_r1/debuggerd/protocol.h)
- [`crash_dump.cpp`（android-17.0.0_r1）](https://android.googlesource.com/platform/system/core/+/refs/tags/android-17.0.0_r1/debuggerd/crash_dump.cpp)
- [ART `sigchain.cc`（android-17.0.0_r1）](https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/sigchainlib/sigchain.cc)
- [ART `fault_handler.cc`（android-17.0.0_r1）](https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/runtime/fault_handler.cc)
- [Bionic reserved signals（android-17.0.0_r1）](https://android.googlesource.com/platform/bionic/+/refs/tags/android-17.0.0_r1/libc/platform/bionic/reserved_signals.h)
- [Android 14 debuggerd handler：版本对照](https://android.googlesource.com/platform/system/core/+/refs/tags/android-14.0.0_r1/debuggerd/handler/debuggerd_handler.cpp)
- [Android 15 debuggerd handler：版本对照](https://android.googlesource.com/platform/system/core/+/refs/tags/android-15.0.0_r1/debuggerd/handler/debuggerd_handler.cpp)
- [Android NDK：GWP-ASan](https://developer.android.com/ndk/guides/gwp-asan)
- [Android NDK：Arm MTE](https://developer.android.com/ndk/guides/arm-mte)
- [ApplicationExitInfo API](https://developer.android.com/reference/android/app/ApplicationExitInfo)

> 源码核查基线：AOSP `android-17.0.0_r1`；版本演进对照 `android-14.0.0_r1`、`android-15.0.0_r1`、`android-16.0.0_r1`。平台私有信号与协议不构成 NDK 兼容承诺。
