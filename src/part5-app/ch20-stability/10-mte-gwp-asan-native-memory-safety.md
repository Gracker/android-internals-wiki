---
title: "MTE 与 GWP-ASan Native 内存安全检测"
chapter: "20.10"
section: "20.10"
status: finalized
drafted_date: "2026-05-16"
applicable_versions: "Android 12 (API 31) - Android 17 (API 37)"
last_verified: "2026-05-16"
last_verified_against: "AOSP android-17.0.0_r1 / Android Developers MTE and GWP-ASan docs / source.android.com memory-safety docs"
confidence: medium
tags: ["mte", "gwp-asan", "memtag", "native-crash", "stability", "security"]
related_chapters: ["4.5", "10.5", "14.5", "20.3", "23.3"]
consolidated_from:
  - "src/part5-app/ch20-stability/23-gwp-asan-probabilistic-memory-safety-android17.md"
created_by: "task2a-knowledge-gap"
created_date: "2026-05-15"
gap_source: "素材驱动/官方文档"
sources:
  - type: official
    path: "https://source.android.com/docs/security/test/memory-safety/arm-mte"
  - type: official
    path: "https://source.android.com/docs/security/test/memory-safety/mte-configuration"
  - type: official
    path: "https://developer.android.com/ndk/guides/arm-mte"
  - type: official
    path: "https://developer.android.com/ndk/guides/memory-debug"
  - type: official
    path: "https://developer.android.com/ndk/guides/gwp-asan"
  - type: aosp
    path: "frameworks/base/core/java/com/android/internal/os/Zygote.java"
  - type: aosp
    path: "frameworks/base/core/jni/com_android_internal_os_Zygote.cpp"
  - type: aosp
    path: "bionic/libc/bionic/malloc_common.cpp"
  - type: aosp
    path: "bionic/libc/bionic/gwp_asan_wrappers.cpp"
  - type: material
    path: "DeepResearch/2026-05-13-android-mte-memtag-async-asymm-analysis.md"
  - type: structure
    path: "Clippings/Android 应用稳定性剖析与优化 - Native Crash 监控：为我们应用插上监控 Native Crash 的电子眼.md"
pipeline_stage: "ready-to-publish"
task6_state: reviewed
reviewed_by: openclaw-task6
reviewed_date: "2026-05-16"
task6_result: pass-light-edit
task9_state: "reviewed"
task9_result: "auto-fixed"
task2b_state: "fixed"
task9_reviewed_date: "2026-05-16"
task9_reviewed_by: openclaw-task9
last_task9_at: "2026-05-16T01:26:00+08:00"
finalized_date: "2026-05-16"
finalized_by: openclaw-task9
last_task6_audit: "2026-07-05"
deepseek_cn_review_state: done
last_deepseek_cn_review_at: "2026-06-01"
last_task9_audit: "2026-06-30"
last_task9_autofix_at: "2026-06-30"
---

# MTE 与 GWP-ASan Native 内存安全检测

MTE 把一部分 Native 内存越界和释放后访问转换成可识别的 `SIGSEGV`。它同时是安全缓解和稳定性诊断能力：错误会更早终止进程，静默内存破坏减少，短期 Crash 数却可能上升。治理目标应写成“发现、定位并修复内存安全缺陷”，不能只追求 MTE Crash 数下降。

平台与用户空间源码锚点是 Android 17 / API 37 / `android-17.0.0_r1`，内核以 `android17-6.18-2026-06_r6` 为锚点。MTE 依赖 Arm64 硬件、内核、进程配置、映射属性和分配器协作；manifest 中的一行配置不能代表所有 Native 内存都受到检查。

## MTE 检查的对象与盲区

MTE 为每个 16 字节 allocation granule 保存一个 4-bit allocation tag，指针携带 logical tag。CPU 访问启用了 MTE 的映射时比较两者，tag 不匹配便按当前检查模式报告错误。

Android 的标准 Native heap 使用 Scudo 管理 tag，可发现两类高价值缺陷：

- heap buffer overflow / underflow 跨越到不同 tag 的 granule；
- use-after-free 在旧指针 tag 与新 allocation tag 不匹配时被捕获。

检测具有概率边界。4-bit tag 只有 16 种取值，释放后重新分配可能碰巧得到相同 tag；越界仍落在同一个 16 字节 granule 内时也没有 tag 边界。MTE 提升发现概率，不证明代码不存在内存错误。

还要区分三类存储：

| 存储 | 只设置 `android:memtagMode` 是否足够 | 补充条件 |
| --- | --- | --- |
| 标准 Native heap | 对 MTE-capable 的 64 位进程生效 | 由 Bionic/Scudo 管理 |
| 自定义 allocator / 自建映射 | 不足 | 映射需要 `PROT_MTE`，allocator 负责指针与内存 tag |
| Native stack / globals | 不足 | 需要编译器插桩、ELF 标记与 linker/runtime 支持 |

Java/Kotlin 对象仍由 ART 管理；32 位进程、未启用 MTE 的映射、同 granule 越界和不配合的自定义 allocator 都不在同一保护范围。Stack MTE 的官方应用支持从 Android 14 QPR3 开始，插桩产物只应运行在 MTE-capable 设备上。

MTE 也不统计 Native heap 大小。定位“谁分配最多”应使用 heapprofd、`dumpsys meminfo`、`/proc/<pid>/smaps` 等工具；MTE 回答的是访问是否违反 tag 约束。

## `android:memtagMode` 的四个值

应用可在 `<application>` 或 `<process>` 上设置 `android:memtagMode`。进程级值覆盖应用级值。

| 值 | 请求语义 | 建议用途 |
| --- | --- | --- |
| `off` | 不请求 MTE access check | 尚未完成 MTE 测试或明确不启用的进程 |
| `default` | 交给 compat change、平台默认和设备策略继续决定 | 不应在遥测中直接写成 off |
| `sync` | 请求同步检查 | debug、实验室、受控 canary |
| `async` | 请求异步检查，并允许设备按 CPU 首选模式增强 | 充分测试后的生产候选 |

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

把文件放在 `app/src/debug/AndroidManifest.xml`，可以避免调试策略进入普通发布包。最终 merged manifest 才是审计对象；库 manifest、build type 和产品 flavor 都可能改变结果。

这段配置是请求，不是能力探测。设备缺少 MTE 时，Android 17 的 Zygote 会按硬件能力降级到 TBI 或 NONE。即使硬件支持，检查模式也可能受 compat change、系统属性和设备的 per-CPU 策略影响。

## SYNC、ASYNC 与 ASYMM

### SYNC

SYNC 在发生 tag mismatch 的 load/store 指令处终止进程：

```text
signal 11 (SIGSEGV), code 9 (SEGV_MTESERR)
```

PC 和 fault address 更接近错误访问。进程被配置为 SYNC 时，Android allocator 还会记录 allocation/deallocation stack，用于解释 use-after-free、overflow 或 underflow。代价来自同步检查和全量分配历史记录，适合测试与定向诊断。

AOSP 的生产配置指南要求普通 shipping 配置使用 `async`，不要把 `sync` 直接写进生产 manifest。若某个高攻击面进程确有安全需求，需要安全、性能和业务团队基于实测明确批准，不能沿用调试包结论。

### ASYNC

ASYNC 发现 tag mismatch 后允许继续执行，到下一次内核入口附近才终止：

```text
signal 11 (SIGSEGV), code 8 (SEGV_MTEAERR)
```

报告位置可能是后续 syscall、timer interrupt 或无关 Native 调用，fault address 通常不可用。它更适合作为低开销的生产检测与缓解；报告负责证明“发生过 MTE fault”，通常不能直接给出错误访问点。

### ASYMM

ASYMM 对读访问做同步检查，对写访问做异步报告。它是 Armv8.7-A 的 CPU 能力，不是 Android 应用 manifest 值。

应用请求 ASYNC 时，Android 17 的 Bionic 会把 `PR_MTE_TCF_ASYNC | PR_MTE_TCF_SYNC` 交给内核；若内核不接受组合值，再退回单独 ASYNC。设备可在启动时通过 `/sys/devices/system/cpu/cpu*/mte_tcf_preferred` 为每个 CPU 配置 `async`、`sync` 或 `asymm`。线程迁移到不同 CPU 后，有效检查行为可能随首选模式变化。

这带来两个诊断边界：

- manifest 的 `async` 只能记为 requested mode，不能写成 effective ASYNC；
- ASYNC 请求在某个 CPU 上被增强为 SYNC 时，fault 可以更精确，但 allocator 仍未必有 SYNC 配置才会采集的 allocation/deallocation stack。

普通应用没有公开的 `asymm` 请求值，也没有可靠 API 读取每次访问所在 CPU 的最终首选模式。遥测应保留原始 `tagged_addr_ctrl` 或 tombstone 证据，并允许 `effective_mode=unknown`。

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

`Zygote.getRequestedMemtagLevel()` 的优先级包括平台包级 override、`<process>`、`<application>`、compat change 和平台默认。`decideTaggingLevel()` 再检查 MTE/TBI 硬件能力；userdebug/eng 设备还可能按平台调试属性把 ASYNC 请求升为 SYNC。64 位 system_server 创建 32 位子进程时，不会把 MTE runtime flag 传给非 arm64 进程。

Native `SpecializeCommon()` 把 runtime flag 映射到 `M_HEAP_TAGGING_LEVEL_TBI`、`ASYNC`、`SYNC` 或 `NONE`，再调用 `mallopt(M_BIONIC_SET_HEAP_TAGGING_LEVEL, ...)`。Bionic 的 `malloc_common.cpp` 在锁保护下调用 `SetHeapTaggingLevel()`，标准 allocator 随后按该级别管理 heap tag。

这条路径解释了一个运维限制：manifest 配置在进程创建阶段生效。普通应用不能用业务远程配置把一个已经以 off 启动的进程切到 async，也不能保证正在运行的进程立刻响应新发布的 manifest。

## 怎样确认支持与请求状态

测试设备不要只靠型号 allowlist。官方推荐的基础检查是：

```shell
adb shell grep -w mte /proc/cpuinfo
```

出现 `mte` 说明当前内核向用户空间公布了对应 CPU capability。有些设备默认未启用，但开发者选项允许重启到 MTE 配置；没有该选项时，应用不能自行补齐硬件或系统支持。

对正在运行的测试进程，可用 debuggerd 查看 `tagged_addr_ctrl`：

```shell
adb shell debuggerd 12345 | head -30 | grep tagged_addr
```

把 `12345` 换成测试进程的 PID。ASYNC 请求若允许 per-CPU 自动增强，输出应同时包含 `PR_MTE_TCF_ASYNC` 和 `PR_MTE_TCF_SYNC` 对应位。该字段描述线程请求集合，不是某次内存访问的最终执行模式。

应用代码若用 `prctl(PR_GET_TAGGED_ADDR_CTRL)` 检查，也只能得到调用线程状态；它不能证明任意地址映射带有 `PROT_MTE`，也不能证明所有线程或所有 CPU 此刻采用同一模式。

官方设备清单会更新。工程内更适合保存“设备实测 capability + build fingerprint + MTE 启动方式”，型号只作为分组字段。

## 灰度策略：按发布和进程控制

MTE 对标准 Native heap 是进程级属性，普通应用没有安全的远程启停开关。可执行的灰度方式有：

1. debug 与内部测试包使用 SYNC，覆盖 Native 代码的单测、集成测试和长稳场景；
2. 单独的 canary build 或 Play 分阶段发布请求 ASYNC；
3. 多进程应用先选择 Native 风险高、业务可恢复的独立进程；
4. 观察稳定性、安全收益和性能后再扩大版本覆盖；
5. 出现不可接受回归时，通过停止发布、回滚版本或发布关闭 MTE 的新版本恢复。

远程配置仍有用途：它可以关闭高风险 Native 功能、降低并发、切换业务兜底或阻止问题页面进入；它不能修改已经 fork 的进程检查模式。

发布前要具备：

- 精确的 Build ID 与未剥离符号归档；
- 只负责一次 fatal signal 采集的 Native Crash 方案；
- tombstone 或系统退出记录的保留与解析；
- 关键状态的进程外持久化，能够承受 MTE 主动终止；
- 同一 workload 下 off、SYNC 与 shipping 配置的性能/功耗对照；
- 按进程、ABI、设备能力和发布版本拆分的回滚观测。

SYNC 测试不能只跑“正常路径”。需要覆盖解析不可信输入、跨语言 ownership、异步回调、取消、对象池、JNI 引用、线程退出、热更新资源和第三方 `.so`。

## Crash 报告怎么读

SYNC 与 ASYNC 报告的排查权重不同。

| 证据 | SYNC / `SEGV_MTESERR` | ASYNC / `SEGV_MTEAERR` |
| --- | --- | --- |
| 当前 PC | 接近错误访问指令 | 常是延迟报告点 |
| fault address | 通常可用于定位 | 通常缺失或不精确 |
| access type | 可从指令和报告分析 | 通常未知 |
| allocation/free stack | 进程配置为 SYNC 时可用 | 通常没有 |
| 栈顶 fingerprint | 可结合 Build ID 使用 | 不适合作为根因指纹 |

SYNC 报告优先读取：

1. `Cause: [MTE]` 的错误类型；
2. fault address、pointer tag 与 memory tag；
3. faulting PC 的 Build ID、relative PC 和反汇编；
4. allocation/deallocation stack；
5. 涉及对象的线程与 ownership。

ASYNC 报告先用于确认受影响版本、进程、设备与业务入口。不要按当前 PC 强行归并；更有效的下一步是构造同版本、同 workload 的 SYNC 诊断包，或在后续 canary build 中把目标进程改为 SYNC。

## APM 事件模型

每个 MTE 事件至少保留：

| 字段组 | 内容 |
| --- | --- |
| 信号 | signal、`si_code`、fault address 是否存在、raw tagged address |
| 模式 | manifest/appcompat 请求值、`tagged_addr_ctrl`、由报告推断的 fault mode、推断置信度 |
| 二进制 | ABI、so、Build ID、relative PC、符号版本 |
| MTE 报告 | `Cause: [MTE]`、access type、allocation/deallocation stack 是否存在 |
| 进程 | 进程名、线程名、前后台、进程存活时长 |
| 设备 | build fingerprint、API、kernel、MTE capability、CPU/SoC |
| 业务 | 去敏入口、灰度版本、Native 模块、最近一次安全 checkpoint |
| 质量 | tombstone/APM 来源、截断状态、符号化状态、重复事件 id |

聚合要按报告质量分层：

- SYNC：优先用错误类型、faulting Build ID + relative PC、allocation/deallocation stack 归一化；
- ASYNC：按 build、进程、Native 模块、设备族、业务入口和时间相关性形成候选簇，保留低置信度；
- 未符号化：先完成 Build ID 匹配，不用库内绝对地址聚合；
- 同一事件多来源：以稳定事件 id 去重，保留 tombstone 与应用采集差异。

MTE Crash 率必须同时报告用户、会话或进程启动分母。上线初期 Crash 增加可能说明以前隐藏的缺陷被暴露；若修复后同一版本和 workload 的 MTE 事件下降，才说明缺陷得到处理。

## 与 Native Crash 采集器协作

MTE fault 仍以 `SIGSEGV` 进入 Native Crash 体系。Android 17 的 debuggerd handler 使用 `SA_SIGINFO | SA_ONSTACK | SA_EXPOSE_TAGBITS` 等 flags，`SA_EXPOSE_TAGBITS` 用于保留 arm64 fault address 的 tag 信息。

应用侧要遵守以下边界：

- fatal signal 只由一个采集器负责，避免多个 SDK 覆盖 disposition；
- handler 不分配 heap、不做完整符号化、不发网络请求；
- 原样保存 `siginfo_t` 和 `ucontext_t` 中可用信息；
- 不盲目调用未知旧 handler，也不尝试从 MTE fault 恢复业务执行；
- 保留系统默认终止和 debuggerd/tombstone 生成路径；
- ASYNC 报告不能把 handler 当前 PC 写成“内存破坏发生点”。

第三方采集器必须用受控故障验证：SYNC use-after-free、SYNC overflow、ASYNC fault、栈溢出和多线程同时 crash。每个用例都要确认应用产物、系统 tombstone、Build ID、MTE `si_code` 和上传结果。

## 性能、兼容性与“误报”

MTE 的开销受 CPU 实现、检查模式、allocation stack tracking、分配行为和 workload 影响。不要引用单一百分比作为全项目结论。使用同一 release build、同一设备电源状态和同一 workload 比较：

- 启动、交互和长任务时延分布；
- CPU time、功耗与温升；
- 内存占用和 allocator 行为；
- Native Crash、ANR、业务失败与进程重启；
- 不同进程和设备档位的差异。

MTE tag mismatch 通常表示进程违反了 tagged-memory 访问约束，不应简单归为误报。归因仍可能出错，例如 ASYNC 报告点被当作访问点、符号版本不匹配、custom allocator 没有遵循正确的 tag 语义，或指针高位被旧代码破坏。要修复证据指向的内存语义，避免屏蔽检查。

第三方 `.so` 也运行在同一进程中。启用前要完成 SDK 清单和 MTE 设备测试；无法更新且持续触发缺陷的 SDK，短期只能隔离进程、回滚版本或关闭该进程的 MTE build，不能吞掉 `SIGSEGV`。

## Android 17 与 kernel 边界

平台与内核各自负责不同部分：

| 层 | 责任 |
| --- | --- |
| Arm CPU | tag compare 与 SYNC/ASYNC/ASYMM fault 行为 |
| kernel `arch/arm64/kernel/mte.c` | tagged-address 控制、per-CPU preferred mode 与线程状态管理 |
| Android Zygote | 应用/进程请求值、compat 与硬件能力决策 |
| Bionic/Scudo | 标准 Native heap tag 与诊断信息 |
| linker/compiler | stack/global instrumentation 与 ELF 元数据 |
| debuggerd | signal 上下文、tombstone 与 MTE 报告 |

分析 Android 17 应用时，framework、Bionic 与 debuggerd 固定到 `android-17.0.0_r1`，内核固定到 `android17-6.18-2026-06_r6`。设备厂商内核、SoC 的 MTE mode 性能和发布配置仍需用 build fingerprint 与实测补齐。

## 发布检查表

- [ ] merged manifest 中每个进程的 `memtagMode` 已确认
- [ ] 只在 64 位、实测支持 MTE 的设备上执行诊断
- [ ] 标准 heap、自定义 allocator、stack 与 globals 的覆盖范围没有混写
- [ ] debug SYNC 已覆盖高风险 Native 场景
- [ ] shipping 配置未把 SYNC 当作普通默认值
- [ ] 灰度依赖分阶段发布或构建变体，没有假设远程动态切换
- [ ] Build ID、符号、tombstone 与事件去重可用
- [ ] SYNC 和 ASYNC 使用不同聚合规则
- [ ] fatal signal 采集器不会破坏 debuggerd 语义
- [ ] 性能、功耗、Crash 与业务恢复都完成对照
- [ ] 回滚版本和关键状态持久化已经演练

## GWP-ASan：概率式 Guarded Pool

MTE 用硬件 tag 检查受保护映射的访问，GWP-ASan 则把少量 Native heap allocation 放进带 guard page 的独立 pool。两者都能发现 use-after-free 和越界，但命中范围、成本和报告语义不同；线上可以组合使用，不能把它们的覆盖率相加成“内存安全百分比”。

### 两层抽样决定覆盖面

GWP-ASan 先决定某次进程启动是否启用，再从该进程的 allocation 中抽样。只有同时通过两层选择的对象才进入 guarded slot，因此“应用启用了 GWP-ASan”不代表所有 malloc 都受保护，也不能用固定的 `1/N` 推导某个缺陷的准确发现率。

Android 的 `android:gwpAsanMode` 支持三种请求：

| 值 | 语义 | 适用范围 |
|---|---|---|
| `default` | 服从平台默认与进程抽样 | 生产基线 |
| `never` | 不为该应用/进程请求 GWP-ASan | 已有明确兼容阻断时使用 |
| `always` | 每次进程启动启用，但 allocation 仍被抽样 | 测试、dogfood 或受控 canary |

进程级配置可以覆盖 application 级配置。最终 merged manifest 才是审计对象；`always` 只取消进程启动这一层抽样，不会让每次 allocation 都进入 pool。

Android 17 的大致路径是：Zygote 根据应用配置和平台策略选择模式，Bionic 在 allocator 初始化阶段把 GWP-ASan 接入 malloc dispatch，再由 guarded pool 管理被采中的 slot。它不是通过修改每个 ELF 的 PLT/GOT 实现，因此与应用自建 malloc hook 的覆盖和冲突模型不同。

### Guarded slot 怎样暴露错误

每个采样 allocation 占用一个 slot，slot 邻近页保持不可访问。越界跨到 guard page 时触发 fault；对象释放后，slot 进入隔离状态，旧指针再次访问也会 fault。metadata 保存 allocation/deallocation 的线程和栈，debuggerd 将其写入 Native crash 报告。

它有明确盲区：

- 未被采中的 allocation 不受保护；
- 越界仍落在 slot 可访问范围内时可能不触发；
- slot 复用会缩短某个旧地址的可诊断窗口；
- 直接 `mmap`、自研 arena、stack/global 和 GPU buffer 不属于同一 allocator 路径；
- 普通内存泄漏不会因为对象长期未释放而自动触发 GWP-ASan。

page size 会改变 guarded pool 的虚拟地址布局和开销，16 KB 设备必须单独压测，但不会把 slot 数量或抽样策略自动变成原来的四分之一。报告必须记录实际页大小、ABI、Build ID 和进程配置。

### Recoverable 模式仍是高优先级故障

Android 14+ 的部分生产配置允许 debuggerd 在完成 GWP-ASan 报告后恢复执行。这个分支由平台根据 metadata 和进程状态确认；应用自定义 `SIGSEGV` handler 通常不会收到该 fault，也不应尝试复刻恢复判断。

“进程没有立刻退出”不代表状态安全。发生 UAF/越界后，业务结果已经不可信；recoverable event 仍应进入稳定性指标、去重、告警和修复队列。对有副作用的操作尤其不能因为继续运行就自动重试。

### 报告、聚合与修复

GWP-ASan 报告优先读取错误类型、fault address 与 slot 边界、allocation/deallocation stack、访问线程、模块 Build ID 和 relative PC。栈可能因采样、metadata 生命周期、unwind 或符号缺失而不完整；字段缺失要显式记录，不能补猜。

聚合键可以使用：

```text
error type
+ allocation top stable frames
+ deallocation top stable frames
+ faulting module/function
+ app build / ABI / module Build ID
```

绝对地址、线程 ID 和完整错误文本不适合长期 fingerprint。一个事件可能同时出现在应用 SDK、tombstone、`ApplicationExitInfo` 和 Play 平台，按启动 ID、时间、signal、Build ID 与关键 frame 去重，同时保留来源差异。

修复仍回到对象所有权：谁分配、谁释放、异步任务或容器为何在释放后继续持有地址。先在相同 Build ID 上用报告定位，再用 `always`、HWASan 或 MTE SYNC 的受控构建扩大复现概率；不能靠提高抽样率代替生命周期修复。

### MTE、GWP-ASan 与其他工具的分工

| 工具 | 强项 | 不负责 |
|---|---|---|
| GWP-ASan | 低成本线上概率捕获 heap UAF/越界 | 普通泄漏、全部 allocation |
| MTE | 硬件 tag 检查与安全缓解，支持受控线上策略 | 精确引用图、同 granule 必然检测 |
| HWASan | 测试/dogfood 高覆盖 heap、stack 错误 | 低开销量产常驻 |
| heapprofd | sampled allocation/free 栈与未释放增长 | 判定 UAF/越界 |
| Scudo | allocator hardening 与部分一致性错误 | 业务 owner 和泄漏根因 |

生产基线通常保留 `default`，用分阶段发布观察命中率、进程启动分母、fatal/recoverable 事件、符号完整率和业务影响；`always` 只进入能承受额外虚拟地址、性能成本与 fatal hit 的范围。灰度报告必须同时写清进程启动覆盖和 allocation sampling，避免把没有命中解释为没有缺陷。

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
- [Android 17 Bionic GWP-ASan allocator](https://android.googlesource.com/platform/bionic/+/refs/tags/android-17.0.0_r1/libc/bionic/gwp_asan_wrappers.cpp)

## 小结

MTE 治理要同时保存四个边界：

1. manifest 记录应用请求，不能代表 CPU 的最终检查模式；
2. heap、custom allocator、stack 与 globals 需要不同的启用条件；
3. SYNC 报告适合定位，ASYNC 报告更适合发现和生产缓解；
4. 进程创建时的配置不能由普通业务远程开关动态替换。

当 Build ID、tombstone、模式证据、设备 capability 和业务入口能够互相校验时，MTE Crash 才能从“新增的 `SIGSEGV`”转化为可修复的 Native 内存缺陷。
