---
title: MTE 与 GWP-ASan Native 内存安全检测
chapter: '20.11'
section: '20.11'
status: ready-for-review
applicable_versions: Android 12 (API 31) - Android 17 (API 37)
last_verified: '2026-08-14'
last_verified_against: AOSP android-17.0.0_r1 framework, Bionic, linker, debuggerd, and android17-6.18-2026-06_r6 kernel sources; current Android Developers and AOSP memory-safety docs through 2026-08-13
confidence: medium-high
tags:
- mte
- gwp-asan
- memtag
- native-crash
- stability
- security
related_chapters:
- '4.4'
- '10.1'
- '15.3'
- '20.3'
- '23.3'
consolidated_from:
- src/part5-app/ch20-stability/23-gwp-asan-probabilistic-memory-safety-android17.md
sources:
- type: official
  path: https://source.android.com/docs/security/test/memory-safety/arm-mte
- type: official
  path: https://source.android.com/docs/security/test/memory-safety/mte-configuration
- type: official
  path: https://developer.android.com/ndk/guides/arm-mte
- type: official
  path: https://developer.android.com/ndk/guides/memory-debug
- type: official
  path: https://developer.android.com/ndk/guides/gwp-asan
- type: official
  path: https://source.android.com/docs/security/test/memory-safety/mte-reports
- type: official
  path: https://source.android.com/docs/core/tests/debug/native-memory
- type: official
  path: https://developer.android.com/reference/android/app/ApplicationExitInfo
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/com/android/internal/os/Zygote.java
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/jni/com_android_internal_os_Zygote.cpp
- type: aosp
  path: https://android.googlesource.com/platform/bionic/+/android-17.0.0_r1/libc/bionic/malloc_common.cpp
- type: aosp
  path: https://android.googlesource.com/platform/bionic/+/refs/tags/android-17.0.0_r1/libc/bionic/gwp_asan_wrappers.cpp
- type: aosp
  path: https://android.googlesource.com/platform/bionic/+/android-17.0.0_r1/libc/bionic/libc_init_mte.cpp
- type: aosp
  path: https://android.googlesource.com/platform/bionic/+/android-17.0.0_r1/libc/bionic/heap_tagging.cpp
- type: aosp
  path: https://android.googlesource.com/platform/bionic/+/android-17.0.0_r1/linker/linker.cpp
- type: aosp
  path: https://android.googlesource.com/platform/system/core/+/android-17.0.0_r1/debuggerd/handler/debuggerd_handler.cpp
- type: aosp-kernel
  path: https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/arch/arm64/kernel/mte.c
- type: internal-reference
  path: /Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/DeepResearch/2026-07-16-android17-gwp-asan-recoverable-sourcecode.md
  role: Android 17 GWP-ASan defaults, malloc dispatch, recoverable debuggerd path
- type: aosp
  path: https://android.googlesource.com/platform/bionic/+/refs/tags/android-17.0.0_r1/libc/bionic/malloc_common_dynamic.cpp
- type: aosp
  path: https://android.googlesource.com/platform/bionic/+/refs/tags/android-17.0.0_r1/libc/private/bionic_globals.h
pipeline_stage: ready-for-review
task6_state: needs-review
task9_state: needs-review
task2b_state: fixed
last_body_apply_at: '2026-08-26T07:15:59+08:00'
last_body_apply_run_id: 20260826-071559-6e58db7c
note: 'Consolidated-source availability: source page not present in the current vault as of 2026-08-14; its retained content is consolidated here'
---

# MTE 与 GWP-ASan Native 内存安全检测

MTE（Memory Tagging Extension，内存标记扩展）会把一部分 Native 内存越界和释放后访问转换成可识别的 `SIGSEGV` 信号。这里的 Native 内存指 C/C++ 等原生代码直接管理的内存，`SIGSEGV` 则是非法内存访问常见的进程终止信号。MTE 既提供安全缓解，也用于稳定性诊断：错误会更早终止进程，静默内存破坏随之减少，短期内应用崩溃数却可能上升。目标应是发现、定位并修复内存安全缺陷，不能只追求 MTE 崩溃数下降。

平台与用户空间（内核之外运行的系统库和应用代码）源码以 Android 17 / API 37 / `android-17.0.0_r1` 为准，内核源码以 `android17-6.18-2026-06_r6` 为准。MTE 依赖 Arm64 硬件、内核、进程配置、内存映射属性和分配器协作；manifest 中的一行配置不能代表所有 Native 内存都受到检查。

Android 12 提供了内核和用户空间堆分配器支持，当前应用文档则把“部分设备可用”的起点写为 Android 13。这里覆盖 Android 12，是为了说明平台能力出现的版本，不能据此认定任意 Android 12 商用设备都可为应用启用 MTE。

## MTE 检查的对象与盲区

MTE 以 16 字节为一个 allocation granule（分配标记粒度），为每个粒度保存 4-bit allocation tag（内存标签），同时让指针携带 logical tag（指针标签）。CPU 读写启用了 MTE 的内存映射时会比较两种标签；不匹配就按当前检查模式报告错误。

Android 的标准 Native heap 使用 Scudo（Android 默认的加固型 Native 分配器）管理标签，可发现两类高价值缺陷：

- heap buffer overflow / underflow（堆缓冲区上溢 / 下溢）跨越到不同标签的粒度；
- use-after-free（释放后继续访问）在旧指针标签与新分配标签不匹配时被捕获。

检测存在概率边界。4 位最多编码 16 种标签，释放后重新分配可能碰巧得到相同标签；越界仍落在同一个 16 字节粒度内时也不会跨越标签边界。官方工具对比把 MTE 的典型漏检概率写作 1/16。MTE 提高发现概率，未报告错误不等于代码没有内存缺陷。

还要区分三类存储：

| 存储 | 只设置 `android:memtagMode` 是否足够 | 补充条件 |
| --- | --- | --- |
| 标准 Native heap（原生堆） | 对支持 MTE 的 64 位进程生效 | 由 Bionic/Scudo 管理 |
| 自定义 allocator（内存分配器）/ 自建映射 | 不足 | 映射需要 `PROT_MTE`，分配器负责指针标签与内存标签 |
| Native stack / globals（原生栈 / 全局变量） | 不足 | 需要编译器插桩、ELF（Native 二进制文件格式）标记，以及动态链接器和运行时库支持 |

Java/Kotlin 对象仍由 ART（Android 运行时）管理；32 位进程、未启用 MTE 的映射、同一标记粒度内的越界和不配合的自定义分配器都不在同一保护范围。面向应用的 Stack MTE（原生栈标记）从 Android 14 QPR3（第三次季度平台更新）开始提供，插桩后的应用只能运行在支持 MTE 的设备上。

MTE 也不统计 Native heap 大小。定位“哪些调用栈分配最多”应使用 heapprofd（低开销的抽样堆分析器）、`dumpsys meminfo`、`/proc/<pid>/smaps` 等工具；MTE 回答的是某次访问是否违反标签约束。

## `android:memtagMode` 的四个值

应用可在 `<application>` 或 `<process>` 上设置 `android:memtagMode`。进程级值覆盖应用级值。

| 值 | 请求语义 | 建议用途 |
| --- | --- | --- |
| `off` | 不请求 MTE 访问检查 | 尚未完成 MTE 测试或明确不启用的进程 |
| `default` | 交给兼容性开关、平台默认和设备策略继续决定 | 事件记录中不能直接写成 off |
| `sync` | 请求同步检查 | 调试包、实验室和小范围诊断包 |
| `async` | 请求异步检查，并允许设备按 CPU 首选模式增强 | 充分测试后的正式发布候选 |

下面的 debug manifest 只让 debug 变体请求 SYNC：

```xml
<?xml version="1.0" encoding="utf-8"?>
<manifest xmlns:android="http://schemas.android.com/apk/res/android"
    xmlns:tools="http://schemas.android.com/tools">
    <application
        android:memtagMode="sync"
        tools:replace="android:memtagMode" />
</manifest>
```

把文件放在 `app/src/debug/AndroidManifest.xml`，可以避免调试策略进入普通发布包。最终 merged manifest（构建工具合并后的 manifest）才是检查对象；依赖库 manifest、构建类型和产品变体都可能改变结果。

这段配置只表达应用请求，不能探测设备能力。设备缺少 MTE 时，Android 17 的 Zygote 会按硬件能力降级到 TBI（Top Byte Ignore，CPU 忽略指针最高字节，Bionic 可在释放时检查标签，但不会逐次检查内存访问）或 NONE（不启用标签）。即使硬件支持，检查模式也可能受兼容性开关、系统属性和设备的逐 CPU 策略影响。

## SYNC、ASYNC 与 ASYMM

### SYNC

SYNC（同步检查）会在发生标签不匹配的内存读写指令处终止进程：

```text
signal 11 (SIGSEGV), code 9 (SEGV_MTESERR)
```

PC（Program Counter，程序计数器）和 fault address（触发信号的地址）通常就是错误访问现场。进程被配置为 SYNC 时，Android 分配器还会记录每次分配与释放的调用栈，用于解释释放后访问、上溢或下溢。同步检查和全量分配历史会增加成本，因此更适合测试与定向诊断。

AOSP 的设备配置指南要求普通正式版本在构建配置和 manifest 中请求 `async`，不要直接写 `sync`。若某个会处理大量外部不可信输入的进程确有更强安全需求，需要安全、性能和业务团队基于实测共同决定，不能沿用调试包结论。

### ASYNC

ASYNC（异步检查）发现标签不匹配后允许程序暂时继续执行，到下一次进入内核附近才终止：

```text
signal 11 (SIGSEGV), code 8 (SEGV_MTEAERR)
```

报告位置可能是后续系统调用、定时器中断或无关 Native 调用，错误地址通常不可用。它更适合作为低开销的正式版本检测与缓解；报告可以证明发生过 MTE 错误，但通常不能直接给出最初的错误访问点。

### ASYMM

ASYMM（非对称检查）对读访问做同步检查，对写访问做异步报告。它是 Armv8.7-A 的 CPU 能力，不是 Android 应用 manifest 可填写的值。

应用请求 ASYNC 时，Android 17 的 Bionic 会把 `PR_MTE_TCF_ASYNC | PR_MTE_TCF_SYNC` 交给内核；若内核不接受组合值，再退回单独 ASYNC。设备可在启动时通过 `/sys/devices/system/cpu/cpu*/mte_tcf_preferred` 为每个 CPU 配置 `async`、`sync` 或 `asymm`。线程迁移到不同 CPU 后，有效检查行为可能随首选模式变化。

这带来两个诊断边界：

- manifest 的 `async` 只能记为 `requested_mode=async`，不能直接写成 `effective_mode=async`；
- ASYNC 请求在某个 CPU 上被增强为 SYNC 时，错误现场可能更精确，但进程并未按 SYNC 配置分配器，因此仍未必具有分配 / 释放调用栈。

普通应用没有公开的 `asymm` 请求值，也没有可靠 API 读取每次访问所在 CPU 的最终首选模式。事件上报应保留原始 `tagged_addr_ctrl`（线程的 tagged-address 控制位）或 tombstone（系统生成的 Native 崩溃报告）证据，并允许 `effective_mode=unknown`。

## Android 17 的进程生效路径

Android 17 的 Java 应用路径可以简化为：

```text
merged AndroidManifest.xml
  -> ApplicationInfo / ProcessInfo.memtagMode
  -> Zygote.getRequestedMemtagLevel()
  -> Zygote.decideTaggingLevel()
  -> runtimeFlags MEMORY_TAG_LEVEL_*
  -> native SpecializeCommon()
  -> mallopt(M_BIONIC_SET_HEAP_TAGGING_LEVEL, ...)
  -> Bionic SetHeapTaggingLevel()
  -> Scudo 管理标准 Native heap tag
```

`Zygote.getRequestedMemtagLevel()` 依次考虑平台为指定包设置的覆盖值、`<process>`、`<application>`、兼容性开关和平台默认值。`decideTaggingLevel()` 再检查 MTE/TBI 硬件能力；`userdebug` 或 `eng` 调试系统还可能通过平台属性把 ASYNC 请求升为 SYNC。64 位 `system_server` 创建 32 位子进程时，不会把 MTE 运行时标志传给非 arm64 进程。

Native `SpecializeCommon()` 把运行时标志映射到 `M_HEAP_TAGGING_LEVEL_TBI`、`ASYNC`、`SYNC` 或 `NONE`，再调用 `mallopt(M_BIONIC_SET_HEAP_TAGGING_LEVEL, ...)`。Bionic 的 `malloc_common.cpp` 在锁保护下调用 `SetHeapTaggingLevel()`，标准分配器随后按该级别管理堆标签。

这条路径说明了一项发布限制：manifest 配置在进程创建阶段生效。普通应用不能用业务远程配置把一个已经以 off 启动的进程切到 async，也不能保证正在运行的进程立刻响应新发布的 manifest。

## 怎样确认支持与请求状态

测试设备不能只看预先列出的型号名单。官方推荐先检查：

```shell
adb shell grep -w mte /proc/cpuinfo
```

出现 `mte` 说明当前内核向用户空间公布了对应 CPU 能力。有些设备默认未启用，但开发者选项允许重启到 MTE 配置；没有该选项时，应用不能自行补齐硬件或系统支持。

对正在运行的测试进程，可用 debuggerd（Android 的 Native 崩溃转储服务）查看 `tagged_addr_ctrl`：

```shell
adb shell debuggerd 12345 | head -30 | grep tagged_addr
```

把 `12345` 换成测试进程的 PID（进程号）。ASYNC 请求若允许逐 CPU 自动增强，输出应同时包含 `PR_MTE_TCF_ASYNC` 和 `PR_MTE_TCF_SYNC` 对应位。该字段描述线程允许的模式集合，不是某次内存访问最终采用的模式。

应用代码若用 `prctl(PR_GET_TAGGED_ADDR_CTRL)` 检查，也只能得到调用线程状态；它不能证明任意地址映射带有 `PROT_MTE`，也不能证明所有线程或所有 CPU 此刻采用同一模式。

官方设备清单会更新。工程记录应保存设备实测能力、build fingerprint（系统构建指纹）和 MTE 启动方式；型号只作为分组字段。

## 分批启用：按发布版本和进程控制

MTE 对标准 Native heap 是进程级属性，普通应用没有安全的远程启停开关。可执行的分批启用方式有：

1. debug 与内部测试包使用 SYNC，覆盖 Native 代码的单测、集成测试和长稳场景；
2. 单独制作 canary build（只交给少量用户验证的候选包），或通过 Play 分阶段发布请求 ASYNC；
3. 多进程应用先选择 Native 风险高、业务可恢复的独立进程；
4. 观察稳定性、安全收益和性能后再扩大版本覆盖；
5. 出现不可接受的回归时，停止扩大发布范围，并回到上一版本或发布关闭 MTE 的修正版。

远程配置仍有用途：它可以关闭高风险 Native 功能、降低并发、展示原生错误页或阻止问题页面进入；它不能修改 Zygote 已经创建出的进程检查模式。

发布前要具备：

- 精确的 Build ID（每份 ELF 二进制的构建标识）与未剥离符号归档；
- 只负责一次 fatal signal（会终止进程的致命信号）采集的 Native 崩溃方案；
- tombstone 或系统进程退出记录的保留与解析；
- 关键状态的进程外持久化，能够承受 MTE 主动终止；
- 同一 workload（可重复的测试负载）下 off、SYNC 与正式发布配置的性能/功耗对照；
- 按进程、ABI（应用二进制接口，也就是 32/64 位和指令集）、设备能力和发布版本分组的停用依据。

SYNC 测试不能只跑“正常路径”。还要覆盖不可信输入解析、跨语言 ownership（对象由谁创建、持有和释放）、异步回调、取消、对象池、JNI 引用、线程退出、热更新资源和第三方 `.so` 动态库。

## 怎样阅读崩溃报告

SYNC 与 ASYNC 报告的排查权重不同。

| 证据 | SYNC / `SEGV_MTESERR` | ASYNC / `SEGV_MTEAERR` |
| --- | --- | --- |
| 当前 PC | 接近错误访问指令 | 常是延迟报告点 |
| fault address（错误地址） | 通常可用于定位 | 通常缺失或不精确 |
| access type（读或写） | 可从指令和报告分析 | 通常未知 |
| allocation/free stack（分配 / 释放栈） | 进程配置为 SYNC 时可用 | 通常没有 |
| 栈顶 fingerprint（聚合特征） | 可结合 Build ID 使用 | 不适合作为根因特征 |

SYNC 报告优先读取：

1. `Cause: [MTE]` 的错误类型；
2. 错误地址、指针标签与内存标签；
3. faulting PC 的 Build ID、relative PC（模块内相对地址）和反汇编；
4. 分配 / 释放调用栈；
5. 涉及对象的线程与所有权关系。

ASYNC 报告先用于确认受影响版本、进程、设备与业务入口。不能按当前 PC 强行归并；下一步应制作相同版本、相同测试负载的 SYNC 诊断包，或在后续小范围候选包中把目标进程改为 SYNC。

## APM 事件字段

APM（Application Performance Monitoring，应用性能监控）中的每个 MTE 事件至少保留：

| 字段组 | 内容 |
| --- | --- |
| 信号 | signal、`si_code`、错误地址是否存在、原始带标签地址 |
| 模式 | manifest / 应用兼容性开关请求值、`tagged_addr_ctrl`、由报告推断的错误模式、推断置信度 |
| 二进制 | ABI、`.so` 动态库、Build ID、relative PC、符号版本 |
| MTE 报告 | `Cause: [MTE]`、访问类型、分配 / 释放调用栈是否存在 |
| 进程 | 进程名、线程名、前后台、进程存活时长 |
| 设备 | build fingerprint、API、内核版本、MTE 能力、CPU/SoC（芯片型号） |
| 业务 | 去敏入口、分批发布版本、Native 模块、最近一次安全 checkpoint（可恢复业务状态） |
| 质量 | tombstone / APM 来源、截断状态、符号化状态、重复事件 ID |

聚合要按报告质量分层：

- SYNC：优先用错误类型、faulting Build ID + relative PC、分配 / 释放栈生成稳定的聚合键；
- ASYNC：按应用版本、进程、Native 模块、设备族、业务入口和时间相关性归为候选组，并保留低置信度标记；
- 未符号化：先完成 Build ID 匹配，不用库内绝对地址聚合；
- 同一事件多来源：以稳定事件 ID 去重，保留 tombstone 与应用采集结果的差异。

MTE 崩溃率必须同时报告用户、会话或进程启动分母。启用初期崩溃增加，可能说明以前隐藏的缺陷被暴露；修复后，同一版本和测试负载下的 MTE 事件下降，才说明缺陷得到处理。

## 与 Native 崩溃采集器协作

MTE 错误仍以 `SIGSEGV` 进入 Native 崩溃采集体系。Android 17 的 debuggerd 信号处理器使用 `SA_SIGINFO | SA_ONSTACK | SA_EXPOSE_TAGBITS` 等标志：前两项让处理器收到完整信号上下文并使用备用信号栈，`SA_EXPOSE_TAGBITS` 则保留 arm64 错误地址中的标签位。

应用侧要遵守以下边界：

- 致命信号只由一个采集器负责，避免多个 SDK 反复覆盖信号处理配置；
- 信号处理函数不分配堆内存、不做完整符号化、不发网络请求；
- 原样保存 `siginfo_t`（信号信息）和 `ucontext_t`（寄存器与线程上下文）中的可用字段；
- 不盲目调用注册顺序和安全性未知的旧处理函数，也不尝试从 MTE 错误恢复业务执行；
- 保留系统默认终止和 debuggerd/tombstone 生成路径；
- ASYNC 报告不能把信号处理函数看到的当前 PC 写成“内存破坏发生点”。

第三方采集器必须用受控故障验证：SYNC 释放后访问、SYNC 越界、ASYNC 错误、栈溢出和多线程同时崩溃。每个用例都要确认应用报告、系统 tombstone、Build ID、MTE `si_code` 和上传结果。

## 性能、兼容性与“误报”

MTE 的开销受 CPU 实现、检查模式、分配栈记录、分配行为和测试负载影响。不能引用单一百分比作为全项目结论。应使用同一个正式版本、相同设备电源状态和相同测试负载比较：

- 启动、交互和长任务时延分布；
- CPU time、功耗与温升；
- 内存占用和分配器行为；
- Native 崩溃、ANR（Application Not Responding，应用无响应）、业务失败与进程重启；
- 不同进程和设备档位的差异。

MTE 标签不匹配通常表示进程违反了 tagged-memory（带标签内存）的访问约束，不应简单归为误报。错误可能出在归因过程，例如把 ASYNC 报告点当作访问点、使用了不匹配的符号版本、自定义分配器没有遵循标签语义，或旧代码破坏了指针高位。应修复证据指向的内存使用错误，不能靠屏蔽检查消除报告。

第三方 `.so` 也运行在同一进程中。启用前要完成 SDK 清单和 MTE 设备测试；无法更新且持续触发缺陷的 SDK，短期只能隔离进程、回到上一版本，或发布关闭该进程 MTE 的新构建，不能吞掉 `SIGSEGV`。

## Android 17 与内核边界

平台与内核各自负责不同部分：

| 层 | 责任 |
| --- | --- |
| Arm CPU | 标签比较与 SYNC / ASYNC / ASYMM 错误行为 |
| kernel `arch/arm64/kernel/mte.c` | 带标签地址控制、各 CPU 首选模式与线程状态管理 |
| Android Zygote | 应用 / 进程请求值、兼容性开关与硬件能力决策 |
| Bionic/Scudo | 标准 Native heap 标签与诊断信息 |
| 动态链接器 / 编译器 | 栈和全局变量插桩，以及 ELF 元数据 |
| debuggerd | 信号上下文、tombstone 与 MTE 报告 |

分析 Android 17 应用时，framework、Bionic 与 debuggerd 固定到 `android-17.0.0_r1`，内核固定到 `android17-6.18-2026-06_r6`。设备厂商内核、SoC 的 MTE 模式性能和发布配置仍需结合系统构建指纹与实测结果。

## 发布检查表

- [ ] 合并后的 manifest 中每个进程的 `memtagMode` 已确认
- [ ] 只在 64 位、实测支持 MTE 的设备上执行诊断
- [ ] 标准堆、自定义分配器、栈与全局变量的覆盖范围没有混写
- [ ] 调试包的 SYNC 已覆盖高风险 Native 场景
- [ ] 正式发布配置未把 SYNC 当作普通默认值
- [ ] 分批启用依赖分阶段发布或构建变体，没有假设远程动态切换
- [ ] Build ID、符号、tombstone 与事件去重可用
- [ ] SYNC 和 ASYNC 使用不同聚合规则
- [ ] 致命信号采集器不会破坏 debuggerd 语义
- [ ] 性能、功耗、应用崩溃与业务恢复都完成对照
- [ ] 回到上一版本的流程和关键状态持久化已经演练

## GWP-ASan：抽样保护少量堆分配

MTE 用硬件标签检查受保护内存映射的访问。GWP-ASan（名称来自 “GWP-ASan Will Provide Allocation SANity”）则从 Native 堆分配中抽样，把少量对象放进 guarded pool（由不可访问页面包围的受保护内存池）。两者都能发现释放后访问和越界，但命中范围、成本和报告含义不同；正式版本可以组合使用，不能把两种覆盖率相加成“内存安全百分比”。

### 两层抽样决定覆盖面

GWP-ASan 先决定某次进程启动是否启用，再从该进程的内存分配中抽样。`always` 模式把第一层命中率设为 100%，其他模式由平台策略决定。只有同时通过两层选择的对象才进入 guarded slot（受保护池中的对象槽位），因此“应用启用了 GWP-ASan”不代表所有 `malloc` 都受保护，也不能用固定的 `1/N` 推导某个缺陷的准确发现率。

在 Android 17 的 Bionic 适配层中，默认 `Recoverable=true`，`SampleRate=25000` 表示被选中进程内的分配级抽样分母，`MaxSimultaneousAllocations=32` 表示同一进程同时可占用的保护槽上限；`SYSTEM_PROCESS_OR_SYSTEM_APP` 与 `APP_MANIFEST_DEFAULT` 分支默认 `process_sample_rate=128`，所以默认覆盖还要先经过进程启动级抽样。进程被选中后，每个分配入口先调用 `GuardedAlloc.shouldSample()`；未命中或 guarded pool 已满时，再委派给下一层原生分配器。[来源: DeepResearch/2026-07-16-android17-gwp-asan-recoverable-sourcecode.md; AOSP android-17.0.0_r1 bionic/libc/bionic/gwp_asan_wrappers.cpp]

GWP-ASan 可用于 `targetSdkVersion >= 30`（面向 Android 11 / API 30 或更高版本）的应用。`android:gwpAsanMode` 支持三种请求：

| 值 | 语义 | 适用范围 |
|---|---|---|
| `default` 或未填写 | Android 13 及以下对普通应用关闭；Android 14+ 使用约 1% 启动命中的 Recoverable GWP-ASan | Android 14+ 的正式版本基线 |
| `never` | 对该应用或进程关闭 GWP-ASan | 已有明确兼容问题时使用 |
| `always` | 每次进程启动都启用，但仍只抽样部分内存分配；命中错误后终止进程 | 测试包、内部日常使用包或小范围候选包 |

进程级配置可以覆盖 application 级配置。最终合并后的 manifest 才是检查对象；`always` 只取消进程启动这一层抽样，不会让每次内存分配都进入受保护池。

Android 17 的大致路径是：Zygote/AndroidRuntime 从应用配置和平台策略得到 GWP-ASan mode，每个 fork 出来的子进程在分配器初始化阶段调用 Bionic 的 `MaybeInitGwpAsan()`；Zygote 自身的 `app_process` 初始化会被显式跳过，避免一次采样影响所有子进程。命中进程抽样后，Bionic 把 `gwp_asan_dispatch` 放到 malloc dispatch chain 的第一站，`prev_dispatch` 指向下一层原生分配器；它不会逐个修改 ELF 的导入跳转项。应用若安装自己的 `malloc` 拦截器，能否与 GWP-ASan 共存取决于安装顺序和 Bionic 分派链，不能只看 manifest 配置。[来源: DeepResearch/2026-07-16-android17-gwp-asan-recoverable-sourcecode.md; AOSP android-17.0.0_r1 bionic/libc/bionic/gwp_asan_wrappers.cpp; AOSP android-17.0.0_r1 bionic/libc/bionic/malloc_common_dynamic.cpp]

若本次启动已经由 `malloc_debug`、`malloc_hooks` 或 heapprofd 占用 default dispatch，Android 17 的 `MaybeInitGwpAsan()` 会直接返回未启用；因此泄漏画像和 GWP-ASan 越界 / 释放后访问诊断通常要分开实验，并在报告中记录 allocator hook 状态。[来源: DeepResearch/2026-07-16-android17-gwp-asan-recoverable-sourcecode.md; AOSP android-17.0.0_r1 bionic/libc/bionic/gwp_asan_wrappers.cpp]

### 受保护槽位怎样暴露错误

每个被抽中的内存分配占用一个槽位，邻近的 guard page（权限设为不可访问的保护页）负责拦住跨页越界。对象释放后，槽位进入隔离状态，旧指针再次访问也会触发错误。metadata（分配器保存的诊断元数据）记录分配 / 释放线程和调用栈，debuggerd 会把这些信息写入 Native 崩溃报告。

它有明确盲区：

- 未被抽中的内存分配不受保护；
- 越界仍落在槽位可访问范围内时可能不触发；
- 槽位复用会缩短某个旧地址的可诊断窗口；
- 直接 `mmap`、自研 arena（批量管理对象的内存区域）、栈 / 全局变量和 GPU 缓冲区不属于同一分配器路径；
- 普通内存泄漏不会因为对象长期未释放而自动触发 GWP-ASan。

保护页跟随系统页大小，因此 16 KB 页设备上的虚拟地址布局和固定内存成本可能不同，需要单独测量。这是由保护页机制得出的工程影响，不表示槽位数量或抽样率会自动变成 4 KB 页设备的四分之一。报告应记录实际页大小、ABI、Build ID 和进程配置。

### Recoverable 模式仍是高优先级故障

Android 14 / API 34 及以上，当 manifest 未填写 `android:gwpAsanMode` 或使用 `default` 时，普通应用采用 Recoverable GWP-ASan：约 1% 的进程启动会启用它。Android 17 的 Bionic 默认把 GWP-ASan 设为 `Recoverable=true`。发生受保护池错误后，debuggerd 会先调用 Bionic 注入的 pre-crash hook，生成首份完整报告，再在 handler 出口调用 post-crash hook，让分配器处理对应故障槽并允许进程继续运行。`debuggerd_handle_gwp_asan_signal()` 还用 `first_crash_mutex` 和 `static bool first_crash` 限制同一进程只有第一次 GWP-ASan 错误走完整 tombstone / DropBoxManager 流程；后续 GWP-ASan 错误只执行 pre/post hook，不再重复触发完整 reporter 输出。应用自定义的 `SIGSEGV` 处理函数不会收到这种可恢复错误，也不应复制平台的恢复判断。[来源: DeepResearch/2026-07-16-android17-gwp-asan-recoverable-sourcecode.md; AOSP android-17.0.0_r1 system/core/debuggerd/handler/debuggerd_handler.cpp; AOSP android-17.0.0_r1 bionic/libc/bionic/gwp_asan_wrappers.cpp]

“进程没有立刻退出”不代表状态安全。发生释放后访问或越界后，官方将后续行为定义为不确定；Recoverable GWP-ASan 事件仍应进入稳定性指标、去重、告警和高优先级修复队列。支付、写入等有副作用的操作不能因为进程继续运行就自动重试。

Recoverable GWP-ASan 与 Permissive MTE 最终都会把 `process_info.recoverable_crash` 设为 true 来避免按普通 fatal signal 终止进程，但入口条件不同：Permissive MTE 看 `SEGV_MTESERR` / `SEGV_MTEAERR` 与 `is_permissive_mte()`，GWP-ASan 则要求 `SIGSEGV` 带有 fault address，且 Bionic 注入的 `NeedsGwpAsanRecovery(si_addr)` 确认地址属于 guarded pool。APM 分类要把两条路径分开，不能把所有可恢复 `SIGSEGV` 都归为 MTE 或都归为 GWP-ASan。[来源: DeepResearch/2026-07-16-android17-gwp-asan-recoverable-sourcecode.md; AOSP android-17.0.0_r1 system/core/debuggerd/handler/debuggerd_handler.cpp]

### 报告、聚合与修复

GWP-ASan 报告优先读取错误类型、错误地址与槽位边界、分配 / 释放栈、访问线程、模块 Build ID 和 relative PC。它依靠 frame pointer（栈帧指针）低成本记录分配与释放栈；64 位应用不应使用 `-fomit-frame-pointer`，而 32 位报告通常缺少这两类调用栈。采样、元数据生命周期、栈回溯或符号缺失也会让字段不完整；缺失值要原样记录，不能补猜。

Android 17 还会把 `gwp_asan_state` 与 `gwp_asan_metadata` 指针放进 `libc_shared_globals`，debuggerd 通过发送给 `crash_dump` 的结构偏移读取这些信息。若报告缺少 GWP-ASan metadata，排查顺序应先确认本进程是否被抽样、是否安装了 GWP-ASan dispatch、以及 tombstone / 符号收集是否完整，而不是把缺失字段补猜成“非 GWP-ASan”。[来源: DeepResearch/2026-07-16-android17-gwp-asan-recoverable-sourcecode.md; AOSP android-17.0.0_r1 bionic/libc/private/bionic_globals.h; AOSP android-17.0.0_r1 system/core/debuggerd/handler/debuggerd_handler.cpp]

聚合键可以使用：

```text
error type
+ allocation top stable frames
+ deallocation top stable frames
+ faulting module/function
+ app build / ABI / module Build ID
```

绝对地址、线程 ID 和完整错误文本不适合充当长期聚合特征。一个事件可能同时出现在应用 SDK、tombstone、`ApplicationExitInfo` 和 Play 平台，应按启动 ID、时间、信号、Build ID 与关键栈帧去重，同时保留来源差异。Android 12 / API 31 起，`ApplicationExitInfo.getTraceInputStream()` 可为 Native 崩溃返回 tombstone protobuf（二进制结构化数据），但全局环形缓冲区中的记录可能被覆盖，返回值也可能为空。

修复仍要回答对象所有权问题：谁分配、谁释放，异步任务或容器为何在释放后继续持有地址。先在相同 Build ID 上用报告定位，再用 `always`、HWASan 或 MTE SYNC 的受控构建提高复现概率；提高抽样率不能代替生命周期修复。

### MTE、GWP-ASan 与其他工具的分工

| 工具 | 强项 | 不负责 |
|---|---|---|
| GWP-ASan | 低成本地在正式版本概率捕获堆释放后访问 / 越界 | 普通泄漏、全部内存分配 |
| MTE | 硬件标签检查与安全缓解，支持受控的正式版本策略 | 精确引用关系、保证检测同一标记粒度内的越界 |
| HWASan（Hardware-assisted AddressSanitizer，编译期插桩检测器） | 在测试或内部日常使用包中高覆盖检测堆、栈与全局变量错误 | 低开销地长期运行在全部正式版本 |
| heapprofd | 抽样记录分配 / 释放栈，分析未释放内存增长 | 判定释放后访问或越界 |
| Scudo | 加固系统分配器并检查部分分配器一致性错误 | 判断业务对象由谁持有，或给出泄漏根因 |

Android 14+ 的正式版本通常保留 `default`，用分阶段发布观察命中率、进程启动分母、致命 / 可恢复事件、符号完整率和业务影响；Android 13 及以下的 `default` 对普通应用仍是关闭状态。`always` 只用于能承受额外虚拟地址、内存成本和进程终止风险的范围。发布报告必须同时写清进程启动覆盖与内存分配抽样，避免把“没有命中”解释为“没有缺陷”。

## 源码与官方资料

- [Android 17 `Zygote.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/com/android/internal/os/Zygote.java)
- [Android 17 `com_android_internal_os_Zygote.cpp`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/jni/com_android_internal_os_Zygote.cpp)
- [Android 17 Bionic `malloc_common.cpp`](https://android.googlesource.com/platform/bionic/+/android-17.0.0_r1/libc/bionic/malloc_common.cpp)
- [Android 17 Bionic `libc_init_mte.cpp`](https://android.googlesource.com/platform/bionic/+/android-17.0.0_r1/libc/bionic/libc_init_mte.cpp)
- [Android 17 Bionic `heap_tagging.cpp`](https://android.googlesource.com/platform/bionic/+/android-17.0.0_r1/libc/bionic/heap_tagging.cpp)
- [Android 17 linker globals 实现](https://android.googlesource.com/platform/bionic/+/android-17.0.0_r1/linker/linker.cpp)
- [Android 17 debuggerd handler](https://android.googlesource.com/platform/system/core/+/android-17.0.0_r1/debuggerd/handler/debuggerd_handler.cpp)
- [Android 17 kernel arm64 MTE](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/arch/arm64/kernel/mte.c)
- [Android NDK：Arm MTE](https://developer.android.com/ndk/guides/arm-mte)
- [AOSP：Arm MTE](https://source.android.com/docs/security/test/memory-safety/arm-mte)
- [AOSP：MTE configuration](https://source.android.com/docs/security/test/memory-safety/mte-configuration)
- [AOSP：Understand MTE reports](https://source.android.com/docs/security/test/memory-safety/mte-reports)
- [Android NDK：memory error debugging](https://developer.android.com/ndk/guides/memory-debug)
- [Android NDK：GWP-ASan](https://developer.android.com/ndk/guides/gwp-asan)
- [AOSP：调试 Native 内存使用](https://source.android.com/docs/core/tests/debug/native-memory)
- [`ApplicationExitInfo`](https://developer.android.com/reference/android/app/ApplicationExitInfo)
- [Android 17 Bionic GWP-ASan allocator](https://android.googlesource.com/platform/bionic/+/refs/tags/android-17.0.0_r1/libc/bionic/gwp_asan_wrappers.cpp)
- [Android 17 Bionic malloc 初始化](https://android.googlesource.com/platform/bionic/+/refs/tags/android-17.0.0_r1/libc/bionic/malloc_common_dynamic.cpp)
- [Android 17 Bionic `libc_shared_globals`](https://android.googlesource.com/platform/bionic/+/refs/tags/android-17.0.0_r1/libc/private/bionic_globals.h)

## 小结

使用 MTE 时要同时保留四个边界：

1. manifest 记录应用请求，不能代表 CPU 的最终检查模式；
2. 堆、自定义分配器、栈与全局变量需要不同的启用条件；
3. SYNC 报告适合定位，ASYNC 报告更适合发现问题和用于正式版本缓解；
4. 进程创建时的配置不能由普通业务远程开关动态替换。

当 Build ID、tombstone、模式证据、设备实测 MTE 能力和业务入口能够互相校验时，新增的 MTE `SIGSEGV` 才能转化为可修复的 Native 内存缺陷。

GWP-ASan 还要额外记录两层抽样：这次进程启动是否启用，以及具体内存分配是否进入受保护池。Android 14+ 的 `default` 会在少量启动中使用可恢复模式，`always` 则每次启动启用并在命中后终止进程；两种模式都不能用“没有报告”证明没有缺陷。
