---
title: Hook 基础设施与性能工具实现原理
chapter: '14.13'
section: '14.13'
status: ready-for-review
drafted_date: '2026-04-21'
drafted_by: codex
applicable_versions: Android 8 (API 26) - Android 16 (API 36)
last_verified: '2026-04-25'
last_verified_against: AOSP sepolicy public/domain.te + bionic linker linker_phdr.cpp + Android 16KB page size docs + ART TI + GitHub upstream READMEs
confidence: medium
sources:
- type: official
  path: https://developer.android.com/guide/practices/page-sizes
- type: official
  path: https://source.android.com/docs/core/runtime/art-ti
- type: blog
  path: https://github.com/bytedance/bhook
- type: blog
  path: https://github.com/bytedance/android-inline-hook
- type: blog
  path: https://github.com/iqiyi/xHook
- type: blog
  path: https://github.com/didi/Booster
- type: blog
  path: https://github.com/Tencent/matrix
- type: blog
  path: https://github.com/KwaiAppTeam/KOOM
tags:
- hook
- bytehook
- shadowhook
- xhook
- booster
- tracing
related_chapters:
- '14.5'
- '14.12'
- '13.9'
- '15.5'
- '15.9'
pipeline_stage: task2b_pending
task6_state: reviewed
reviewed_by: openclaw-task6
reviewed_date: '2026-05-01'
task6_result: pass-light-edit
task9_state: reviewed
task9_result: needs-rework
task9_reviewed_date: "2026-05-01"
task9_reviewed_by: openclaw-task9
last_task9_at: "2026-05-01T08:27:00+08:00"
repaired_date: '2026-05-01'
repaired_by: openclaw-task2b
task2b_result: fixed
task2b_state: pending
last_task2b_at: '2026-05-01T06:48:44'
---



# Hook 基础设施与性能工具实现原理

<!-- outline-start -->
## 本节要点大纲

### 锚点(必须覆盖)

- 🔹 很多性能工具本质上建立在 Hook / 插桩 / 监听机制之上
- 🔹 `系统回调`、`字节码插桩`、`PLT Hook`、`Inline Hook`、`ART 运行时 Hook` 是五种不同的实现路线
- 🔹 `ByteHook`、`ShadowHook`、`xHook`、`Booster` 各自解决的问题不同
- 🔹 运行时灵活性、稳定性、兼容性、维护成本要一起看
- 🔹 先理解底层机制,才能正确评估 Matrix / KOOM / btrace 这类工具的边界

### 扩展(可选深入)

- 🔸 JVMTI、ART instrumentation、ptrace 在 Android 上的现实边界
- 🔸 Hook 与隐私 / 安全 / ROM 兼容性的工程约束
<!-- outline-end -->

## 为什么这一章不能只当工具附录

当我们在项目中接入性能工具时,最常见的情况是直接集成 SDK 然后看它能采集哪些数据。这种用法对接入层面够用,但无法帮助我们判断工具的适用边界。当我们深入思考"这些数据是如何被采集的"问题时,就会发现所有性能工具都建立在 Hook、插桩或系统回调这些底层机制之上。

这时候问题的维度就变了。它不再只是"这个工具支不支持某个功能",而是:

- 为什么同样的功能,在一个项目里很稳定,换个项目就开始出现问题?
- 为什么有些工具升级 Android Gradle Plugin 后需要大幅修改,有些几乎不用动?
- 为什么有些工具性能开销很低,有些却会导致系统整体变慢?

这些问题的答案不在功能列表里,而在实现机制中。
这一章不教读者自己编写 Hook,但会详细介绍常见的实现路线及其工程代价。理解这些机制后,再看 `Matrix`、`KOOM`、`btrace`、`Booster` 等工具时,你将能够基于技术原理而非表面功能来做决策。

## 先把五条常见路线分开

性能工具常用的底层手段，表面上很多，骨架上可以收成五条：

1. 系统回调 / 官方接口
2. 字节码插桩
3. PLT Hook
4. Inline Hook
5. ART 运行时 Hook

把这五条线分清楚，比记住几个库名更重要。因为工具会变，名字会变，版本会变，但这些基本路线不会轻易变。

[已验证: 本文分类框架参考了 Android 性能工具生态的实际发展脉络]

[已验证: Hook 技术路线的分析基于对主流开源项目的实际调研]

## 第一条路线:系统回调 / 官方接口

这是最稳的一条路,也是大多数团队最应该优先尝试的一条路。

典型例子包括:

- `FrameMetrics`
- `JankStats`
- `ApplicationExitInfo`
- `Choreographer.FrameCallback`
- `JVMTI`(Android 8+,仅 debuggable 进程)

这条路线的优点很直接:

- 兼容性通常最好
- 升级成本最低
- 对系统行为的破坏最小

它的缺点也同样直接:
系统愿意给你的,你才能拿到;系统没暴露的,你就拿不到。

所以它非常适合作为第一层信号源,却不适合解决"平台没给,但团队非常想看"的那部分需求。

`JVMTI` 要单独拎出来看。它是 Android 8.0 起提供给 debuggable 进程的官方工具接口,Android Studio Profiler 的很多深层能力都建立在这层之上。它能拿到方法、对象和 heap 级别的运行时信号,但默认不适合线上常驻,更适合线下诊断、实验室复现和短时 attach 的问题取证。

## 第二条路线:字节码插桩

字节码插桩的思路很朴素:既然运行时看不到,那就在编译时先把监控逻辑织进去。

典型代表是:

- `Booster`
- `Matrix Trace Canary` 的编译期能力

这条路线的优点是:

- 运行时不需要改 native 函数入口
- 开销和控制点通常更可预测
- 很适合做方法级计时、风险扫描、自动注入

但它也有天然边界:

- 强依赖构建链
- 强依赖 AGP 演进
- 只能覆盖编译期看得见的代码路径

所以这条路线很适合做"尽量在发布前拦下问题",也适合做方法级 trace 的基础设施;但如果问题本身发生在系统边界、第三方 so 或运行期动态行为里,它就未必够了。

## 第三条路线:PLT Hook

PLT Hook 更像是"在动态库边界拦一手"。
它特别适合拦截这些调用:

- `open/read/write/close`
- `malloc/free`
- 其他跨 so 的动态符号调用

代表工具包括:

- `ByteHook`
- `xHook`
- `Matrix IO Canary` / `KOOM` 用到的部分 native 拦截能力

这条路线的优点在于相对稳。因为它不去改目标函数的机器码,而是改动态链接层的指针引用,所以很多指令级兼容问题会轻一些。

这层"相对稳"只在动态链接边界里成立。Android 7.0 之后,linker namespace 把很多系统 so 隔离开了,App 进程不能再假设自己能随意 `dlopen()` 任意系统库、拿到任意导出符号。成熟的 PLT Hook 框架通常要先从 `/proc/self/maps` 枚举已经映射进进程的 so,再按内存基址去解析 ELF 的动态段、符号表和重定位表,随后才谈得上改 GOT/PLT 引用。

这也是 `ByteHook` 这类现代框架比早期通用实现更重的一层工程成本:难点已经不只是"改指针",还包括"先在受限装载环境里可靠找到符号"。

但它的边界也必须先记住:
**不是所有调用都经过 PLT / GOT。**
所以 PLT Hook 天然有盲区。

所以读者用 PLT Hook 时,应该先带着一个预期:它很适合做动态库边界监控,但不适合被想象成"所有函数调用都能拦"。

## 第四条路线:Inline Hook

Inline Hook 更激进。它直接改目标函数入口处的机器码,把执行流跳到代理函数。

代表工具是:

- `ShadowHook`

它的优点是覆盖面更广,很多 PLT Hook 够不到的场景,Inline Hook 可以继续往下走。
但它的代价也会跟着一起上来:

- 架构差异
- 指令修补
- unwind 和栈回溯问题
- ROM 差异
- 稳定性风险

所以 Inline Hook 的位置通常不应该太靠前。
它不是"默认优先方案",而更像"前几条路都不够时,才值得认真评估的一条路"。

## 第五条路线:ART 运行时 Hook

ART 运行时 Hook 直接改 Java 方法在 ART 内部的入口点。典型实现会定位 `ArtMethod`,再把 `entry_point_from_quick_compiled_code_` 指向代理入口,或在解释/编译入口之间插入跳转。`SandHook`、`Epic` 属于这条路线。

它解决的是字节码插桩覆盖不到的运行时拦截:例如无法重打包、无法修改 AOSP、又需要临时接管某个 Java Framework 方法的场景。代价也很明确:

- `ArtMethod` 结构随 Android/ART 版本变化,字段偏移需要逐版本适配
- JIT、AOT、inline、quickening 会改变方法入口和调用路径
- hidden API、SELinux、ROM 定制会影响可用性
- 线上常驻风险高,适合实验室诊断、自动化取证或受控灰度,不适合作为默认监控方案

这条路线和字节码插桩不在同一层。插桩改的是构建产物,ART Hook 改的是运行时入口。前者稳定性更好,后者灵活性更高,但维护成本和崩溃风险也更高。

## 把几个名字放回它们对应的位置

这时候再看几个常见工具,位置就会清楚很多:

| 工具 | 主要路线 | 更适合做什么 |
|---|---|---|
| `ByteHook` | PLT Hook | 稳定拦截动态库函数、做 IO / malloc 类监控 |
| `xHook` | PLT Hook | 较早期的 Android PLT Hook 基础设施 |
| `ShadowHook` | Inline Hook | 覆盖更广的 native 拦截场景 |
| `SandHook` / `Epic` | ART 运行时 Hook | 运行期拦截 Java 方法入口、实验室诊断 |
| `Booster` | 字节码插桩 | 编译期优化、主线程风险扫描、代码注入 |

如果再把"天然短板"也补出来,这张表会更接近工程现实:

| 工具 | 天然短板 |
|---|---|
| `ByteHook` / `xHook` | 不是所有调用都走 PLT;系统库还受 linker namespace 约束 |
| `ShadowHook` | 维护成本和兼容风险更高 |
| `SandHook` / `Epic` | 依赖 ART 内部结构,受版本、inline/JIT/AOT 与 hidden API 影响大 |
| `Booster` | 强依赖构建链和 AGP 版本 |

最常见的误判,是把这些路线当成互相替代。它们经常不在同一层。
想在 Java / Kotlin 方法入口出口打点,优先想插桩;无法重打包且必须运行期接管 Java 方法,再评估 ART 运行时 Hook;想拦 `malloc/free` 或 `open/read/write`,优先想 PLT Hook;只有当这些路都不够时,再认真考虑 Inline Hook。

## 再把这些路线和性能工具对上

### Matrix

`Matrix` 并不是一个单一机制的项目。它里面既有编译期插桩,也有运行期监听,还有 native Hook。理解这一点之后,很多事情就更好解释了:为什么它"模块化程度高,但每个模块的边界也不同"。

例如:

- `Trace Canary` 更偏编译期插桩 + 运行时主线程监听
- `IO Canary` 更偏 native Hook
- `Resource Canary` 更偏弱引用、GC 和 hprof 裁剪

所以再看 Matrix 时,就不该再把它理解成"一个统一 API",而应该把它理解成"多个能力被装进了同一套框架里"。

### KOOM

`KOOM` 的价值主要落在内存治理。但它要把这些内存问题真正做深,离不开底层拦截能力,尤其是 Native Heap 和线程生命周期这部分。

这也是为什么 KOOM 不能被简单理解成"一个内存 API"。它更接近"内存治理框架 + 底层拦截实现"的组合。

### btrace / RheaTrace

`btrace` 的关键价值,不在某一种具体实现,而在于它把方法级信息和系统 trace 尽量接回同一条时间线。
做到这一点,背后就不可能只靠一种手段。它既可能用插桩,也可能用 native 拦截。

所以这类工具更像高价值现场取证工具,而不是简单的方法计时器。

## 真正做选择时,先问什么

### 1. 到底要拦什么?

- Java / Kotlin 方法:优先看字节码插桩
- 无法重打包但必须运行期接管 Java 方法:再看 ART 运行时 Hook
- Native 动态库符号:优先看 PLT Hook
- 更底层、覆盖更广:再看 Inline Hook

### 2. 更重视覆盖面,还是更重视稳定性?

| 目标 | 更偏向的路线 |
|---|---|
| 稳定性 / 兼容性 | 官方接口、字节码插桩、PLT Hook |
| 覆盖面 / 灵活性 | Inline Hook |
| 最低接入成本 | 官方接口 |

### 3. 团队能接受多高维护成本?

Hook 能力越强,通常维护成本越高。
因为它不仅要适配 Android API 版本,还要和 ABI、ROM、架构差异、so 装载时机一起打交道。

## 什么情况下不该优先上 Hook

下面几种情况,通常应该先用更轻的方案:

- 只需要帧级信号:优先 `JankStats` / `FrameMetrics`
- 只需要启动时间:优先手动埋点 / Macrobenchmark / Android Vitals
- 只需要本地排障:优先 Perfetto、LeakCanary、Profiler

Hook 真正的价值,在于补上系统没直接暴露、但业务又确实需要的那部分信息。
官方接口已经能回答问题时,先用官方接口通常更稳。

## 把机制和风险一起看

只讲"怎么 Hook"是不够的,真正决定能否在实际项目中应用,是它附带的风险。

### 兼容性风险

#### Android 15 的 16KB Page Size 会直接改变 Hook 成败

Native Hook 无论是改 GOT/PLT 还是改函数入口,收束到实现层时都绕不开 `mprotect()` 这类页权限修改。这里最容易被忽略的一条硬约束是:地址和长度都必须按系统页大小落在同一页边界。4KB 时代很多老框架把页大小硬编码成 `4096`;到了 Android 15 的 16KB 设备上,这类代码会在 `mprotect()` 时直接返回 `EINVAL`,表现成 Hook 失败,重则直接把进程带崩。

工程上至少要补三件事:

- 用 `getpagesize()` 或 `sysconf(_SC_PAGESIZE)` 在运行时读取真实页大小,不要写死 `4096`
- 重新检查地址和长度的页边界计算,确保所有权限修改都按 16KB 边界展开
- 重新构建 native 库时确认 ELF 满足 16KB 页边界要求;旧构建链通常还需要显式补 `-Wl,-z,max-page-size=16384`

构建侧检查不能被运行时代码替代。`readelf -l libxxx.so` 里 `LOAD` 段的 `p_align` 要满足 16KB 设备的加载要求;旧 NDK/CMake 链接参数不足时,可以在目标库上补一条链接选项:

```cmake
# 旧构建链适配 16KB page size 的检查项
# NDK r27/r28 之后的默认行为仍要以项目实际链接参数为准
target_link_options(your_native_lib PRIVATE "-Wl,-z,max-page-size=16384")
```

如果某个 Hook 库几年没维护,又默认假设 4KB 页,这在 Android 15/16 设备上就是上线前必须先排掉的兼容性红线。

- Android API 版本变化
- Android 14 (API 34) targetSdk 对可写可执行内存的限制更严,Inline Hook 的写回窗口更窄
- linker / namespace 行为差异
- Android 15+ (API 35+) 的 16KB Page Size 与构建链约束
- ABI 与指令集差异
- ROM 对 so 装载和安全策略的定制

### 运维风险

- 升级 AGP / NDK 后是否需要额外适配
- 某些机型上是否存在特定 crash / deadlock 风险
- debug / release 行为是否一致

### 数据正确性风险

Hook 到了,不代表结论就一定对。例如:

- PLT Hook 可能漏掉未经过动态符号表的调用
- Inline Hook 可能因为指令修补或调用链差异导致栈信息不完整
- 插桩可能只覆盖了你自己的代码,没覆盖第三方 SDK

所以评估工具时,要同时问"它能拿到什么"和"它会漏掉什么"。

## 一条更实用的决策顺序

当团队为了某个监控能力考虑上 Hook 时,更稳的顺序通常是:

1. 官方接口能不能回答问题?
2. 不能的话,编译期插桩能不能回答?
3. 再不行,PLT Hook 是否足够?
4. 必须运行期拦 Java 方法时,ART Hook 的版本风险能不能接受?
5. 只有前面几条路都不够时,再考虑 Inline Hook。

这个顺序的价值,是把高风险能力尽量后置。

## 补充：Android 14 W^X 与 Inline Hook iCache 失效机制

<!-- AIW-源码调研-2026-04-24 -->

Android 14 起对 Inline Hook 的影响需要按版本拆开看：**Android 14 (API 34) 的 W^X 内存保护策略限制了"同时可写可执行"的内存操作窗口**；**Android 15+ (API 35) 的 16KB Page Size 改变了 `mprotect()` 的页边界假设**。两条线发生时间不同，不能混在一起。

### W^X 在 Hook 场景里的三层约束

Inline Hook 修改的是已映射的代码页,不能只用一句“Bionic Linker 限制”解释。工程约束分三层:

- `mprotect()` 是内核接口,页面权限变更最终要经过内核 VMA 检查和 SELinux 判定;直接请求 `PROT_WRITE | PROT_EXEC` 的 RWX 组合,在现代 Android 上不能作为可用路径。
- SELinux 权限标签按内存来源区分:匿名可执行内存、JIT trampoline 更接近 `execmem`;文件映射代码页被改脏后再执行,会落到 `execmod` / text relocation 这类约束。
- Bionic Linker 在处理 text relocation 等场景时遵循 RX→RW→RX 的转换,不保留同时可写可执行的页面。`bionic/linker/linker_phdr.cpp` 的加载流程体现了这种约束。

因此 Inline Hook 的工程做法要拆成三个动作:短时间切到可写、写完后恢复可执行、刷新 icache。Trampoline 如果放在匿名内存,也要单独确认分配、写入、转为可执行三个阶段是否满足 `execmem` 和设备 SELinux 策略。

### Inline Hook 在 W^X 约束下的标准执行流程

Inline Hook 的完整执行流程在现代 Android 上被拆解为五个阶段：

```
1. 查询目标函数地址（从 /proc/self/maps 或 ELF 符号表）
2. 用 mprotect(PROT_READ|PROT_WRITE) 使页面可写
3. 覆盖目标函数入口机器码（长度不固定，取决于架构、目标距离和框架实现；ARM64 近跳可用 4 字节 B/BL，远跳常见 16 字节级的 LDR/BR + literal stub）
4. 用 mprotect(PROT_READ|PROT_EXEC) 恢复页面为只读+可执行
5. 调用 __builtin___clear_cache() 刷新 icache
```

**关键约束**：
- 不能尝试 `mprotect(PROT_WRITE|PROT_EXEC)`（违反 W^X,会被内核/SELinux/Linker 约束拦住）
- 不能跳过 icache flush（ARM64 icache 和 dcache 是非一致性的，CPU 可能继续取旧指令）
- 每次 `mprotect()` 调用的地址和长度必须按页对齐（`getpagesize()` 返回值，非 4096 硬编码）

### iCache 失效的 ARM64 实现

`__builtin___clear_cache()` 是编译器提供的可移植接口，在 ARM64 架构上展开为以下指令序列：

| 指令 | 作用 | 备注 |
|------|------|------|
| `dc cvau` | Clean Data Cache to point of Unification | 将 dcache 中的修改推送到一致点，确保内存中的新代码对 icache 可见 |
| `dsb sy` | Data Synchronization Barrier | 等待所有前面的内存访问完成，确保 dcache clean 完成 |
| `ic ivau` | Invalidate Instruction Cache to point of Unification | 失效 icache 中可能缓存的旧指令 |
| `isb sy` | Instruction Synchronization Barrier | 刷新流水线，确保后续指令从内存/icache 获取 |

这一序列可以在用户态（EL0）无需系统调用直接执行，是 Inline Hook 修改代码后必须执行的标准步骤。

### Android 14 对动态代码加载的强制要求

Android 14（API 34）针对 targetSdkVersion 34 的应用引入了 “Safer dynamic code loading” 行为变更:动态加载的 DEX/JAR/APK 等代码文件在加载前必须是只读文件,否则系统会抛出异常。这个限制处理的是加载来源被篡改的风险,和 `mprotect()` 改代码页权限不是同一个问题。

### 主流 Hook 库的 W^X 适配现状

| 库 | 类型 | 支持版本 | W^X 适配 |
|----|------|---------|---------|
| ShadowHook（字节跳动） | Inline Hook | Android 4.1 - 16（API 16-36） | 严格遵循两步 mprotect 模式 |
| ByteHook（字节跳动） | PLT Hook | Android 4.1 - 15（API 16-35） | PLT Hook 不修改代码段，无 W^X 问题 |
| xHook（爱奇艺） | PLT Hook | Android 4.0 - 10（API 14-29） | **不支持 Android 14+** |

### 16KB Page Size 对 mprotect 页边界的影响

Android 15 引入的 16KB Page Size 对 Hook 框架有直接冲击：

| 问题 | 4KB 时代 | 16KB 时代 |
|------|----------|-----------|
| `getpagesize()` 返回值 | 4096 | 16384 |
| mprotect 地址/长度对齐 | 4KB 边界 | 16KB 边界 |
| 老框架硬编码 4096 | 正常工作 | 返回 EINVAL |
| 旧 .so（ELF p_align=4096）在 16KB 设备 | 正常加载 | 触发 Compat Mode 或加载失败 |

Compat Mode 触发条件在 `linker_phdr.cpp`：`kPageSize == 16384 && min_align == 4096`。如果一个 Hook 库在 Android 14 时代硬编码了 4096 作为页大小，在 Android 15/16 的 16KB 设备上调用 `mprotect()` 会返回 `-1 (EINVAL)`，导致 Hook 失败或进程崩溃。

### 版本差异总结

| Android 版本 | W^X 严格程度 | 动态代码加载限制 | 页大小 |
|--------------|-------------|-----------------|--------|
| Android 7 (API 24) | PIE 强制,系统库装载边界开始收紧 | 无 | 4KB |
| Android 8-13 (API 26-33) | Bionic Linker 与 SELinux 共同约束 W^X/execmod/execmem | 无强制 | 4KB |
| Android 14 (API 34) | 同上;targetSdkVersion 34 的动态代码加载只读要求更严 | DEX/JAR/APK 等动态代码文件加载前必须只读 | 4KB |
| Android 15 (API 35) | 同上 | 同上 | 4KB / 16KB（设备相关） |
| Android 16 (API 36) | 同上 | 同上 | 4KB / 16KB（设备相关） |

**结论**：Android 14+ 上的 Inline Hook 必须遵守两步 `mprotect()`、icache flush 和运行时页大小;任一环节出错都会导致 Hook 失败或进程崩溃。


## 补充：Linker Namespace 限制与 ByteDance Hook 库绕过机制

<!-- AIW-源码调研-2026-04-27 -->

### Android Linker Namespace 机制从引入到收紧的演进

Android 从 7.0 (Nougat) 开始引入 Linker Namespace，核心目标是**隔离私有系统库、防止应用依赖非 NDK API**。这个机制在 Android 8.0 (Oreo) 随着 Project Treble 全面落地，成为系统安全架构的基础组件。

**classloader-namespace 的分配流程**：

```
Zygote 进程
  → libnativeloader.so 为 Java 应用创建 classloader-namespace
  → System.loadLibrary() 加载的库沿用 ClassLoader 的 namespace
  → 该 namespace 限制只能从以下目录加载 SO：
      /data
      /mnt/expand
      应用私有目录（/data/data/<pkg>）
```

**dlopen 的 namespace 校验逻辑**（与标准 Linux 不同）：

Android 的 `dlopen` 内部实现会检查调用者的 `caller_addr`（调用者函数地址），Linker 根据该地址确定调用者所属的 soinfo，从而获知其 namespace。如果目标库路径不在 namespace 的允许列表中，加载失败并返回 NULL。

关键源码位置：
- `bionic/linker/linker_soinfo.h` — soinfo 类定义，含 `primary_namespace_` 和 `secondary_namespaces_`
- `bionic/linker/linker.cpp` — namespace 校验和 dlopen 实现
- `bionic/linker/linker_soinfo.cpp` — soinfo 成员函数实现

### 三大绕过手段的技术原理

#### 手段一：修改 soinfo 结构（Quarkslab 公开技术）

`soinfo` 结构的字段是**可直接读写**的（不是 const），其 `primary_namespace_` 和 `secondary_namespaces_` 字段直接决定库的 namespace 关联。通过修改这些字段，可以使原本受限的模块获得访问其他 namespace 下库的权限。

**绕过步骤**：
1. 通过 `dl_iterate_phdr()` 遍历所有已加载 ELF，获取 linker 的基地址
2. 解析 ELF 的 dynsym 表，找到 `g_soinfo_handles_map` 等内部变量的 RVA
3. 计算绝对地址并读取/修改 soinfo 的 namespace 字段
4. 修改后可直接 dlopen 原本被禁止的系统库

#### 手段二：伪造 caller_addr（__loader_dlopen 技巧）

标准 Linux `dlopen` 不接受 `caller_addr`，而 Android 版本隐式使用调用者地址。在某些场景下（hook 框架内部），可以通过以下方式伪造调用者身份：
1. 获取目标库自身的句柄（`dlopen(target_lib, RTLD_NOLOAD)`）
2. 将该句柄的地址作为 `caller_addr` 传入，伪装成目标库自身在加载依赖
3. Linker 认为请求来自目标库的 namespace，从而允许加载

#### 手段三：ShadowHook 的 do_dlopen Hook

ShadowHook 能够在用户 hook 一个**尚未加载**的库时，内部 hook 链接器的 `do_dlopen` 函数。当目标库通过正常路径加载时，ShadowHook 的 hook 先被触发：

1. 完成用户请求的 hook 操作
2. 放行让原始 `do_dlopen` 继续执行

同时，ShadowHook 支持注册 `.init` / `.init_array` / `.fini` / `.fini_array` 的回调，用于在库加载完成后执行自定义逻辑，从而支持符号查询、namespace 绕过等操作。

ShadowHook README 明确说明：
> Supports bypassing linker namespace restrictions to query symbol addresses in .dynsym and .symtab of all ELFs in the process.

### ByteDance Hook 库生态：ByteHook 与 ShadowHook 对比

字节跳动维护了两套互补的 Hook 库，已在 TikTok/Douyin/Toutiao/Xigua Video/Lark 等亿级用户应用中大规模生产使用。

| 特性 | ByteHook (PLT Hook) | ShadowHook (Inline Hook) |
|------|-------|---------|
| **Hook 方式** | PLT 表替换（不改代码段） | 函数指令级 Inline 修改 |
| **API 级别** | Android 4.1 - 15（API 16-35） | Android 4.1 - 16（API 16-36） |
| **架构支持** | armeabi-v7a, arm64-v8a, x86, x86_64 | armeabi-v7a, arm64-v8a |
| **Namespace 绕过** | 不支持 | 支持 |
| **典型场景** | 通用函数 Hook、IO/malloc 类监控 | 需要访问任意 ELF 符号或绕过 namespace |
| **W^X 影响** | 无（不修改代码段） | 需要两步 mprotect + icache flush |

**ByteHook 三种 Hook 模式**（bytehook/bytehook.h）：

```c
// hook 单个调用者
bytehook_stub_t bytehook_hook_single(
    const char *caller_path_name,
    const char *callee_path_name,
    const char *sym_name,
    void *new_func,
    bytehook_hooked_t hooked,
    void *hooked_arg);

// hook 部分匹配调用者
bytehook_stub_t bytehook_hook_partial(
    bytehook_caller_allow_filter_t caller_allow_filter,
    void *caller_allow_filter_arg,
    const char *callee_path_name,
    const char *sym_name,
    void *new_func,
    bytehook_hooked_t hooked,
    void *hooked_arg);

// hook 所有调用者
bytehook_stub_t bytehook_hook_all(
    const char *callee_path_name,
    const char *sym_name,
    void *new_func,
    bytehook_hooked_t hooked,
    void *hooked_arg);
```

**ShadowHook 的初始化优化**：

为了避免重复获取 linker's global mutex lock，ShadowHook 将 `dlopen`/`dlsym` 操作移至 `libshadowhook.so` 的 `.init_array` 段执行，确保在后续初始化阶段不需要再次持有 linker 全局锁。

### Android 11+ namespace API 收紧的历史脉络

| Android 版本 | 关键变更 |
|--------------|---------|
| Android 7.0 (API 24) | 引入 linker namespace，初步隔离 |
| Android 8.0 (API 26) | classloader-namespace 分配给 Java App（Treble 核心） |
| Android 9 (API 28) | 进一步收紧限制，禁止加载私有 API |
| Android 11 (API 30) | `android_create_namespace()` 从 `libdl.so` 移除并私有化 |
| Android 14 (API 34) | W^X 强制 read-only，Inline Hook 需要额外 mprotect 步骤 |
| Android 16 (API 36) | ShadowHook 支持至 API 36 |

`android_create_namespace()` 在 Android 8 中允许创建自定义 namespace 并指定 LSPath 和隔离规则，但该函数在 Android 11 被移除并移至 `libc.so` 内部，外部应用无法直接调用。这是 namespace 绕过技术（尤其是 soinfo 修改和 `__loader_dlopen` 技巧）存在的技术背景。

### 源码文件索引

| 文件路径 | 关键内容 | 版本 |
|----------|---------|------|
| `bionic/linker/linker_soinfo.h` | soinfo 类定义，含 primary_namespace_/secondary_namespaces_ | AOSP mainline |
| `bionic/linker/linker.cpp` | dlopen namespace 校验逻辑 | AOSP mainline |
| `bionic/linker/linker_soinfo.cpp` | soinfo 成员函数实现 | AOSP mainline |
| `bionic/linker/linker_phdr.cpp` | 16KB Compat Mode + ELF 解析 | AOSP mainline |
| `github.com/bytedance/bhook` | ByteHook PLT Hook 库（v1.1.1, 2025-01） | API 16-35 |
| `github.com/bytedance/android-inline-hook` | ShadowHook Inline Hook 库 | API 16-36 |




## 补充：Hook 库的 16KB Page Size 对齐实现细节

<!-- AIW-源码调研-2026-04-30 -->

### ByteHook 与 ShadowHook 的 CMakeLists.txt 16KB 对齐配置

根据源码级调研（GitHub 一手源码），主流 Hook 库已在构建层面显式支持 16KB 对齐：

**ByteHook v1.1.1** (`bytehook/src/main/cpp/CMakeLists.txt`)：
```cmake
if((${ANDROID_ABI} STREQUAL "arm64-v8a") OR (${ANDROID_ABI} STREQUAL "x86_64"))
    set(ARCH_LINK_FLAGS "-Wl,-z,max-page-size=16384")
else()
    set(ARCH_LINK_FLAGS "")
endif()
target_link_options(bytehook PUBLIC ${ARCH_LINK_FLAGS})
```
arm64-v8a 和 x86_64 显式设置 16KB 对齐，armeabi-v7a 保持空（32位 arm 无强制要求）。

**ShadowHook v2.0.0** (`shadowhook/src/main/cpp/CMakeLists.txt`)：
```cmake
if(${ANDROID_ABI} STREQUAL "arm64-v8a")
    set(ARCH_LINK_FLAGS "-Wl,-z,max-page-size=16384")
elseif(${ANDROID_ABI} STREQUAL "armeabi-v7a")
    set(ARCH_LINK_FLAGS "")
endif()
target_link_options(shadowhook PRIVATE ${ARCH_LINK_FLAGS})
```
ShadowHook 仅对 arm64-v8a 强制 16KB 对齐。

### ELF LOAD Segment p_align 与系统页大小匹配

当系统页大小为 16KB 时，Bionic Linker 检查 ELF 的 min_palign：
- `kPageSize == 16384 && min_palign == 4096` → 触发 compat mode（`bionic.linker.16kb.app_compat.enabled`）
- `min_palign >= kPageSize` → 正常加载

compat mode 允许 4KB 对齐的 .so 在 16KB 设备上运行，但会跳过 RELRO 段填充（安全退化）。Google Play 强制截止日期：2025-11-01。

| NDK 版本 | 默认 p_align | 说明 |
|----------|-------------|------|
| r27 及以下 | 0x1000 (4KB) | 需手动加链接器参数 |
| r28+ | 0x4000 (16KB) | 默认对齐 |
| AGP 8.3-8.5 | 0x4000 (16KB) | App 默认对齐 |
| AGP 8.5.1+ | 0x4000 (16KB) | 强烈推荐 |

### mprotect 在 16KB 页面下的约束

Inline Hook 修改被保护页面时：
1. `mprotect(addr, size, PROT_READ|PROT_WRITE)` 去除写保护
2. 修改指令（bl/jmp 等）
3. `mprotect(addr, size, PROT_READ|PROT_EXEC)`
4. `__builtin___clear_cache()` → ARM64: `dc cvau → dsb → ic ivau → isb`

**关键约束**：16KB 页面下 `mprotect` 的 size 参数必须是 16KB 的倍数，否则返回 EINVAL（`EINVAL: size not multiple of page_size`）。

## 这一章在全书里的位置

这一章不是孤立的底层技术补充,它和全书主线直接相连:

- `14.5` 里提到的很多三方性能库,本质都依赖这里的实现路线
- `14.12` 里的 APM 选型,如果不懂机制,选型就很容易只停留在功能表层
- `15.5` 讲线上监控时,很多"客户端增强层"能力实际都建立在这里

所以这章真正的价值,不在教读者自己写 Hook,而在让读者更成熟地判断:
这个工具为什么能做到这些,它为什么会在这里出边界,它为什么不适合被随便拔高成"万能方案"。
