---
title: Hook 基础设施与性能工具实现原理
chapter: '14.13'
section: '14.13'
status: ready-for-review
drafted_date: '2026-04-21'
drafted_by: codex
applicable_versions: Android 8 (API 26) - Android 16 (API 36)
last_verified: '2026-05-28'
last_verified_against: AOSP sepolicy public/domain.te + bionic linker linker_phdr.cpp + bionic linker libdl.map.txt (android-9/10/11 tags) + Android Developers 16KB page size docs (2026-04-24) + ART TI + GitHub upstream READMEs
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
pipeline_stage: task6_pending
task6_state: "revisiting"
task9_state: pending
repaired_date: '2026-05-08'
repaired_by: openclaw-task2b
task2b_result: fixed-lite
task2b_state: fixed
last_task2b_lite_at: '2026-05-28'
last_task2b_at: "2026-05-22T07:21:00+08:00"
task9_review_notes: "2026-05-22 Task9 07: needs-rework。P0 1：16KB 表混淆 NDK ELF p_align 与 AGP 打包对齐；P1 1：Google Play 2025-11-01 要求缺 target/API/发布范围。已写入 logs/deep-review/2026-05-22-07-deep-review.md。"
last_task6_at: "2026-05-22T08:20:00+08:00"
last_task6_review_log: "logs/review/2026-05-22-08-review.md"
review_notes: '2026-05-13 task9 deep-review: needs-rework。P0 1，P1 1，P2 0；问题已写入 queue/suggestions，等待 Task2B 回炉。'
task6_result: "pass-light-edit"
reviewed_by: "openclaw-task6"
reviewed_date: "2026-05-22"
task6_review_notes: "2026-05-22 Task6 08:20：revisiting 写作复审；L1/L2 小修 1 处（第一人称/读者代称、结构元叙述、填充强调或编辑痕迹清理）；无新增 L3/L4 回炉项。Task9 07:43 已有 P0/P1 pending queue，pipeline 保持 task2b_pending。"
task9_result: needs-rework
task9_reviewed_date: "2026-05-22"
task9_reviewed_by: openclaw-task9
last_task9_at: "2026-05-22T07:43:01+08:00"
last_task9_review_log: logs/deep-review/2026-05-22-07-deep-review.md
---



# Hook 基础设施与性能工具实现原理

<!-- outline-start -->
## 本节要点大纲

### 锚点(必须覆盖)

- 🔹 很多性能工具建立在 Hook / 插桩 / 监听机制之上
- 🔹 `系统回调`、`字节码插桩`、`PLT Hook`、`Inline Hook`、`ART 运行时 Hook` 是五种不同的实现路线
- 🔹 `ByteHook`、`ShadowHook`、`xHook`、`Booster` 各自解决的问题不同
- 🔹 运行时灵活性、稳定性、兼容性、维护成本要一起看
- 🔹 先理解底层机制，才能正确评估 Matrix / KOOM / btrace 这类工具的边界

### 扩展(可选深入)

- 🔸 JVMTI、ART instrumentation、ptrace 在 Android 上的现实边界
- 🔸 Hook 与隐私 / 安全 / ROM 兼容性的工程约束
<!-- outline-end -->

## 为什么这一章不能只当工具附录

当我们在项目中接入性能工具时，最常见的情况是直接集成 SDK 然后看它能采集哪些数据。这种用法对接入层面够用，但无法帮助我们判断工具的适用边界。当我们追问"这些数据是如何被采集的"时，就会发现性能工具通常建立在 Hook、插桩或系统回调这些底层机制之上。

这时问题会变得更具体：

- 为什么同样的功能，在一个项目里很稳定，换个项目就开始出现问题？
- 为什么有些工具升级 Android Gradle Plugin 后需要大幅修改，有些几乎不用动？
- 为什么有些工具性能开销很低，有些却会导致系统整体变慢？

这些问题的答案不在功能列表里，而在实现机制中。
读者不需要自己编写 Hook，也要看懂常见实现路线及其工程代价。理解这些机制后，再看 `Matrix`、`KOOM`、`btrace`、`Booster` 等工具时，就能基于技术原理而不是表面功能来做决策。

## 五条常见路线的边界

性能工具常用的底层手段很多，常见路线有五条：

1. 系统回调 / 官方接口
2. 字节码插桩
3. PLT Hook
4. Inline Hook
5. ART 运行时 Hook

把这五条线分清楚，比记住几个库名更重要。工具会变，名字会变，版本会变，但这些基本路线不会轻易变。

[已验证: 分类框架已对照 ByteHook、ShadowHook、xHook、Booster、Matrix、KOOM 公开仓库与 Android ART TI 文档。]

## 第一条路线：系统回调 / 官方接口

这是最稳的一条路，也是大多数团队最应该优先尝试的一条路。

典型例子包括：

- `FrameMetrics`：每帧渲染耗时、输入延迟、布局/绘制阶段的分项耗时（Android 7 / API 24+，含 `TOTAL_DURATION`）；GPU 执行时间（`GPU_DURATION`）与帧截止时间（`DEADLINE`）从 API 31 (Android 12) 起可用
- `JankStats`：基于 FrameMetrics 的卡顿检测与归因库（AndroidX）
- `ApplicationExitInfo`：系统记录的进程退出原因（ANR、crash、LMK 等，Android 11 / API 30+）
- `Choreographer.FrameCallback`：VSync 回调接口，用于帧时间对齐和自定义帧调度
- `JVMTI`：JVM Tool Interface，debuggable 进程可用的运行时诊断接口（Android 8+）

这条路线有三个优势：

- 兼容性通常最好
- 升级成本最低
- 对系统行为的破坏最小

它的边界也很明确：系统暴露什么，工具就只能拿到什么；系统没有开放的信号，工具也拿不到。

所以它非常适合作为第一层信号源，却不适合解决"平台没给，但团队非常想看"的那部分需求。

`JVMTI` 要单独拎出来看。它是 Android 8.0 起提供给 debuggable 进程的官方工具接口，Android Studio Profiler 的很多深层能力都建立在这层之上。它能拿到方法、对象和 heap 级别的运行时信号，但默认不适合线上常驻，更适合线下诊断、实验室复现和短时 attach 的问题取证。

## 第二条路线：字节码插桩

字节码插桩把监控逻辑提前织入编译产物：运行时看不到的调用点，编译阶段先改掉。

典型代表是：

- `Booster`：基于 AGP Transform/API 的编译期优化和代码注入框架
- `Matrix Trace Canary`：微信团队的方法级编译期插桩 + 运行时主线程监控

这条路线的优点是：

- 运行时不需要改 native 函数入口
- 开销和控制点通常更可预测
- 很适合做方法级计时、风险扫描、自动注入

但它也有天然边界：

- 强依赖构建链
- 强依赖 AGP 演进
- 只能覆盖编译期看得见的代码路径

所以这条路线很适合做"尽量在发布前拦下问题"，也适合做方法级 trace 的基础设施；但如果问题发生在系统边界、第三方 `.so` 或运行期动态行为里，它就未必够了。

## 第三条路线：PLT Hook

PLT Hook 的入口在动态库边界。
它特别适合拦截这些调用：

- `open/read/write/close`
- `malloc/free`
- 其他跨 so 的动态符号调用

代表工具包括：

- `ByteHook`：字节跳动开源的现代 PLT Hook 框架，支持 Android 4.1–15
- `xHook`：爱奇艺开源的早期 PLT Hook 方案，不支持 Android 14+
- `Matrix IO Canary` / `KOOM`：腾讯的 IO 监控和内存治理工具，底层用 PLT Hook 拦截 open/read/write 等系统调用

这条路线的优点在于相对稳。因为它不去改目标函数的机器码，而是改动态链接层的指针引用，所以很多指令级兼容问题会轻一些。

这层"相对稳"只在动态链接边界里成立。Android 7.0 之后，linker namespace 把很多系统 `.so` 隔离开了，App 进程不能再假设自己能随意 `dlopen()` 任意系统库、拿到任意导出符号。成熟的 PLT Hook 框架通常要先从 `/proc/self/maps` 枚举已经映射进进程的 `.so`，再按内存基址去解析 ELF 的动态段、符号表和重定位表，随后才谈得上改 GOT/PLT 引用。

这也是 `ByteHook` 这类现代框架比早期通用实现更重的一层工程成本：难点从"改指针"扩展到"在受限装载环境里可靠找到符号"。

但它的边界需要提前说明：
**不是所有调用都经过 PLT / GOT。**
所以 PLT Hook 天然有盲区。

使用 PLT Hook 时，应该带着这个预期：它很适合做动态库边界监控，但不适合被想象成"所有函数调用都能拦"。

## 第四条路线：Inline Hook

Inline Hook 更激进。它直接改目标函数入口处的机器码，把执行流跳到代理函数。

代表工具是：

- `ShadowHook`：字节跳动开源的 Inline Hook 框架，支持 ARM32/ARM64，覆盖 Android 4.1–16

它的优点是覆盖面更广，很多 PLT Hook 够不到的场景，Inline Hook 可以继续往下走。
但它的代价也会跟着一起上来：

- 架构差异
- 指令修补
- unwind 和栈回溯问题
- ROM 差异
- 稳定性风险

所以 Inline Hook 的位置通常不应该太靠前。
它不该作为默认优先方案，更适合在前几条路都不够时再认真评估。

## 第五条路线：ART 运行时 Hook

ART 运行时 Hook 直接改 Java 方法在 ART 内部的入口点。典型实现会定位 `ArtMethod`，再把 `entry_point_from_quick_compiled_code_` 指向代理入口，或在解释/编译入口之间插入跳转。`SandHook`、`Epic` 属于这条路线。

它解决的是字节码插桩覆盖不到的运行时拦截：例如无法重打包、无法修改 AOSP、又需要临时接管某个 Java Framework 方法的场景。代价也随之出现：

- `ArtMethod` 结构随 Android/ART 版本变化，字段偏移需要逐版本适配
- JIT、AOT、inline、quickening 会改变方法入口和调用路径
- hidden API、SELinux、ROM 定制会影响可用性
- 线上常驻风险高，适合实验室诊断、自动化取证或受控灰度，不适合作为默认监控方案

这条路线和字节码插桩不在同一层。插桩改的是构建产物，ART Hook 改的是运行时入口。前者稳定性更好，后者灵活性更高，但维护成本和崩溃风险也更高。

## 把几个名字放回它们对应的位置

把常见工具放回各自路线，位置会更清楚：

| 工具 | 主要路线 | 更适合做什么 |
|---|---|---|
| `ByteHook` | PLT Hook | 稳定拦截动态库函数、做 IO / malloc 类监控 |
| `xHook` | PLT Hook | 较早期的 Android PLT Hook 基础设施 |
| `ShadowHook` | Inline Hook | 覆盖更广的 native 拦截场景 |
| `SandHook` / `Epic` | ART 运行时 Hook | 运行期拦截 Java 方法入口、实验室诊断 |
| `Booster` | 字节码插桩 | 编译期优化、主线程风险扫描、代码注入 |

如果再把"天然短板"也补出来，这张表会更接近工程现实：

| 工具 | 天然短板 |
|---|---|
| `ByteHook` / `xHook` | 不是所有调用都走 PLT；系统库还受 linker namespace 约束 |
| `ShadowHook` | 维护成本和兼容风险更高 |
| `SandHook` / `Epic` | 依赖 ART 内部结构，受版本、inline/JIT/AOT 与 hidden API 影响大 |
| `Booster` | 强依赖构建链和 AGP 版本 |

最常见的误判，是把这些路线当成互相替代。它们经常不在同一层。
想在 Java / Kotlin 方法入口出口打点，优先想插桩；无法重打包且必须运行期接管 Java 方法，再评估 ART 运行时 Hook；想拦 `malloc/free` 或 `open/read/write`，优先想 PLT Hook；只有当这些路都不够时，再认真考虑 Inline Hook。

## 再把这些路线和性能工具对上

### Matrix

`Matrix` 并不是一个单一机制的项目。它里面既有编译期插桩，也有运行期监听，还有 native Hook。理解这一点之后，很多事情就更好解释了：为什么它"模块化程度高，但每个模块的边界也不同"。

例如：

- `Trace Canary` 更偏编译期插桩 + 运行时主线程监听
- `IO Canary` 更偏 native Hook
- `Resource Canary` 更偏弱引用、GC 和 hprof 裁剪

所以再看 Matrix 时，不该把它理解成"一个统一 API"，它更像是"多个能力被装进了同一套框架里"。

### KOOM

`KOOM` 的价值主要落在内存治理。要把这些内存问题做深，离不开底层拦截能力，尤其是 Native Heap 和线程生命周期这部分。

这也是为什么 KOOM 不能被简单理解成"一个内存 API"。它更接近"内存治理框架 + 底层拦截实现"的组合。

### btrace / RheaTrace

`btrace` 的关键价值，不在某一种具体实现，而在于它把方法级信息和系统 trace 尽量接回同一条时间线。
做到这一点，背后就不可能只靠一种手段。它既可能用插桩，也可能用 native 拦截。

所以这类工具更像高价值现场取证工具，而不是简单的方法计时器。

## 做选择时，先问什么

### 1. 到底要拦什么？

- Java / Kotlin 方法：优先看字节码插桩
- 无法重打包但必须运行期接管 Java 方法：再看 ART 运行时 Hook
- Native 动态库符号：优先看 PLT Hook
- 更底层、覆盖更广：再看 Inline Hook

### 2. 更重视覆盖面，还是更重视稳定性？

| 目标 | 更偏向的路线 |
|---|---|
| 稳定性 / 兼容性 | 官方接口、字节码插桩、PLT Hook |
| 覆盖面 / 灵活性 | Inline Hook |
| 最低接入成本 | 官方接口 |

### 3. 团队能接受多高维护成本？

Hook 能力越强，通常维护成本越高。
因为它不仅要适配 Android API 版本，还要和 ABI、ROM、架构差异、`.so` 装载时机一起打交道。

## 什么情况下不该优先上 Hook

遇到这些情况，通常先用更轻的方案：

- 只需要帧级信号：优先 `JankStats` / `FrameMetrics`
- 只需要启动时间：优先手动埋点 / Macrobenchmark / Android Vitals
- 只需要本地排障：优先 Perfetto、LeakCanary、Profiler

Hook 的价值在于补上系统没直接暴露、业务又需要的那部分信息。
官方接口已经能回答问题时，先用官方接口通常更稳。

## 把机制和风险一起看

只讲"怎么 Hook"是不够的，决定它能否在实际项目中应用的，是它附带的风险。

### 兼容性风险

#### Android 15 的 16KB Page Size 会直接改变 Hook 成败

Native Hook 无论是改 GOT/PLT 还是改函数入口，实现时都绕不开 `mprotect()` 这类页权限修改。`mprotect()` 的硬约束是起始地址 `addr` 必须按系统页大小对齐；`len` 参数指定覆盖范围，内核会自动按页粒度向上取整，不需要调用方手动传入页大小的整数倍。4KB 时代很多老框架把页大小硬编码成 `4096`，只影响 `addr` 对齐计算；到了 Android 15 的 16KB 设备上，如果 `addr` 仍按 4KB 对齐计算，`mprotect()` 会返回 `EINVAL`，表现成 Hook 失败，重则直接把进程带崩。

工程上至少要补三件事：

- 用 `getpagesize()` 或 `sysconf(_SC_PAGESIZE)` 在运行时读取真实页大小，不要写死 `4096`
- 按 `page_start = addr & ~(page_size - 1)` 计算对齐起始地址，`page_end = align_up(addr + patch_len, page_size)` 计算覆盖终止地址，`len = page_end - page_start`；不要假设 `len` 必须由调用方手动凑成页大小的整数倍
- 重新构建 native 库时确认 ELF 满足 16KB 页边界要求；旧构建链通常还需要显式补 `-Wl,-z,max-page-size=16384`

构建侧检查不能被运行时代码替代。`readelf -l libxxx.so` 里 `LOAD` 段的 `p_align` 要满足 16KB 设备的加载要求；旧 NDK/CMake 链接参数不足时，可以在目标库上补一条链接选项：

```cmake
# 旧构建链适配 16KB page size 的检查项
# NDK r27/r28 之后的默认行为仍要以项目实际链接参数为准
target_link_options(your_native_lib PRIVATE "-Wl,-z,max-page-size=16384")
```

如果某个 Hook 库几年没维护，又默认假设 4KB 页，这在 Android 15/16 设备上就是上线前必须先排掉的兼容性红线。

- **Android API 版本变化**：每个大版本的 Bionic Linker、SELinux 策略、execmem/execmod 判定逻辑都可能调整，Hook 库需要逐版本验证
- **Android 14 (API 34) 动态代码加载要求变严**：targetSdk 34 要求动态加载的 DEX/JAR/APK 文件在加载前必须只读（Safer dynamic code loading 行为变更）；native 代码页的 W^X / execmem / execmod 约束在 Android 8-13 已存在，Android 14 未新增通用 `mprotect()` 限制
- **linker / namespace 行为差异**：Android 7 起引入的 linker namespace 隔离，不同版本对 `dlopen` 路径和符号可见性的限制逐步变严
- **Android 15+ (API 35+) 的 16KB Page Size**：页大小变化直接影响 `mprotect` 的地址对齐要求和 ELF 加载兼容性
- **ABI 与指令集差异**：ARM32/ARM64 的指令修补策略不同，Thumb/ARM 模式切换、分支距离限制都需要分别处理
- **ROM 定制**：厂商可能修改 so 装载策略、SELinux 策略或 linker 行为，同一 Hook 库在不同 ROM 上的表现可能不一致

### 运维风险

- 升级 AGP / NDK 后是否需要额外适配
- 某些机型上是否存在特定 crash / deadlock 风险
- debug / release 行为是否一致

### 数据正确性风险

Hook 到了，不代表结论就一定对。例如：

- PLT Hook 可能漏掉未经过动态符号表的调用
- Inline Hook 可能因为指令修补或调用链差异导致栈信息不完整
- 插桩可能只覆盖了自己的代码，没覆盖第三方 SDK

所以评估工具时，要同时问"它能拿到什么"和"它会漏掉什么"。

## 一条更实用的决策顺序

当团队为了某个监控能力考虑上 Hook 时，更稳的顺序通常是：

1. 官方接口能不能回答问题？
2. 不能的话，编译期插桩能不能回答？
3. 再不行，PLT Hook 是否足够？
4. 必须运行期拦 Java 方法时，ART Hook 的版本风险能不能接受？
5. 只有前面几条路都不够时，再考虑 Inline Hook。

这个顺序的价值，是把高风险能力尽量后置。

## 补充：W^X 约束下的 Inline Hook 与 iCache 失效机制

<!-- AIW-源码调研-2026-04-24 -->

Inline Hook 在 Android 上长期受 W^X / execmem / execmod / SELinux 共同约束。约束的严格程度因版本、设备和 SELinux 策略而异。**Android 14 (API 34) 新增的是 Safer dynamic code loading 行为变更（DEX/JAR/APK 加载前必须只读），和 `mprotect()` 修改代码页权限不是同一个问题**；**Android 15+ (API 35) 的 16KB Page Size 改变了 `mprotect()` 的页边界假设**。三条线性质不同，不能混在一起。

### W^X 在 Hook 场景里的三层约束

Inline Hook 修改的是已映射的代码页，不能只用一句“Bionic Linker 限制”解释。工程约束分三层：

- `mprotect()` 是内核接口，页面权限变更最终要经过内核 VMA 检查和 SELinux 判定；是否允许 `PROT_WRITE | PROT_EXEC`（RWX）组合取决于内核配置和 SELinux 策略，不能一概而论。部分设备/内核允许匿名 RWX mmap，部分则严格禁止。
- SELinux 权限标签按内存来源区分：匿名可执行内存、JIT trampoline 更接近 `execmem`；文件映射代码页被改脏后再执行，会落到 `execmod` / text relocation 这类约束。AOSP sepolicy `private/app.te` 中仍有 `allow appdomain self:process execmem` 规则，但 OEM 可以改严或移除。
- Bionic Linker 在处理 text relocation 等场景时遵循 RX→RW→RX 的转换，不保留同时可写可执行的页面。`bionic/linker/linker_phdr.cpp` 的加载流程体现了这种约束，但这只规范 Linker 自身行为，不影响用户态 `mmap`/`mprotect` 的内核级判定。

因此 Inline Hook 的工程实现通常包含三个动作：短时间切到可写、写完后恢复可执行、刷新 icache。但具体是走两步 `mprotect`（RW→RX）还是直接 RWX mmap，取决于目标设备的 SELinux 策略和 Hook 库的实现选择。

### Inline Hook 在 W^X 约束下的标准执行流程

现代 Android 上的 Inline Hook 执行流程通常包含五个阶段：

```text
1. 查询目标函数地址（从 /proc/self/maps 或 ELF 符号表）
2. 用 mprotect(PROT_READ|PROT_WRITE) 使页面可写
3. 覆盖目标函数入口机器码（长度不固定，取决于架构、目标距离和框架实现；ARM64 近跳可用 4 字节 B/BL，远跳常见 16 字节级的 LDR/BR + literal stub）
4. 用 mprotect(PROT_READ|PROT_EXEC) 恢复页面为只读+可执行
5. 调用 __builtin___clear_cache() 刷新 icache
```

**现代 Android 上的 Inline Hook 约束**：
- `mprotect(PROT_WRITE|PROT_EXEC)` 在部分设备/SELinux 策略下会被拒绝，应优先使用两步 RW→RX 模式；但某些 Hook 库（如 ShadowHook upstream）在匿名内存上直接使用 RWX mmap，依赖 `execmem` 权限可用
- 不能跳过 icache flush（ARM64 icache 和 dcache 是非一致性的，CPU 可能继续取旧指令）
- 每次 `mprotect()` 调用的起始地址必须按页对齐（`getpagesize()` 返回值，非 4096 硬编码）；`len` 覆盖范围由内核自动按页取整，不需要手动凑整

### iCache 失效的 ARM64 实现

`__builtin___clear_cache()` 是编译器提供的可移植接口，在 ARM64 架构上展开为以下指令序列：

| 指令 | 作用 | 备注 |
|------|------|------|
| `dc cvau` | Clean Data Cache to point of Unification | 将 dcache 中的修改推送到一致点，确保内存中的新代码对 icache 可见 |
| `dsb ish` | Data Synchronization Barrier (Inner Shareable) | 等待 dcache clean 完成并传播到所有 PE |
| `ic ivau` | Invalidate Instruction Cache to point of Unification | 失效 icache 中可能缓存的旧指令 |
| `dsb ish` | Data Synchronization Barrier (Inner Shareable) | 确保 icache invalidation 完成并传播到所有 PE |
| `isb` | Instruction Synchronization Barrier | 刷新流水线，确保后续指令从内存/icache 获取 |

ARM 自修改代码推荐序列包含两次 DSB：dcache clean 后一次，icache invalidate 后一次。`__builtin___clear_cache()` 由编译器/运行时封装，具体指令文本可能因编译器版本和目标微架构不同而略有差异，上表给出的是 ARM 推荐的规范序列。

### Android 14 对动态代码加载的强制要求

Android 14（API 34）针对 targetSdkVersion 34 的应用引入了 “Safer dynamic code loading” 行为变更：动态加载的 DEX/JAR/APK 等代码文件在加载前必须是只读文件，否则系统会抛出异常。这个限制处理的是加载来源被篡改的风险，和 `mprotect()` 改代码页权限不是同一个问题。

### 主流 Hook 库的 W^X 适配现状

| 库 | 类型 | 支持版本 | W^X 适配 |
|----|------|---------|---------|
| ShadowHook（字节跳动） | Inline Hook | Android 4.1 - 16（API 16-36） | upstream 使用 RWX mmap/mprotect，依赖 execmem 可用；W^X 严格设备可能失效 |
| ByteHook（字节跳动） | PLT Hook | Android 4.1 - 15（API 16-35） | PLT/GOT 改写不 patch 目标函数代码页；但 ARM/ARM64 上 upstream 通过 shadowhook 依赖 RWX trampoline 与 dlopen 监控，仍需验证 execmem/RWX 可用性 |
| xHook（爱奇艺） | PLT Hook | Android 4.0 - 10（API 14-29） | **不支持 Android 14+** |

### 16KB Page Size 对 mprotect 页边界的影响

Android 15 引入的 16KB Page Size 对 Hook 框架有直接冲击：

| 问题 | 4KB 时代 | 16KB 时代 |
|------|----------|-----------|
| `getpagesize()` 返回值 | 4096 | 16384 |
| mprotect 起始地址对齐 | 4KB 边界 | 16KB 边界（len 由内核自动按页取整） |
| 老框架硬编码 4096 | 正常工作 | 返回 EINVAL |
| 旧 .so（ELF p_align=4096）在 16KB 设备 | 正常加载 | 触发 Compat Mode 或加载失败 |

Compat Mode 触发条件在 `linker_phdr.cpp`：`kPageSize == 16384 && min_align == 4096`。如果一个 Hook 库在 Android 14 时代硬编码了 4096 作为页大小，在 Android 15/16 的 16KB 设备上调用 `mprotect()` 会返回 `-1 (EINVAL)`，导致 Hook 失败或进程崩溃。

### 版本差异总结

| Android 版本 | W^X 严格程度 | 动态代码加载限制 | 页大小 |
|--------------|-------------|-----------------|--------|
| Android 7 (API 24) | PIE 强制，系统库装载边界开始变严 | 无 | 4KB |
| Android 8-13 (API 26-33) | SELinux execmem/execmod 策略因设备/OEM 而异；AOSP 默认允许 appdomain execmem | 无强制 | 4KB |
| Android 14 (API 34) | 同上；targetSdkVersion 34 的动态代码加载只读要求更严 | DEX/JAR/APK 等动态代码文件加载前必须只读 | 4KB |
| Android 15 (API 35) | 同上 | 同上 | 4KB / 16KB（设备相关） |
| Android 16 (API 36) | 同上 | 同上 | 4KB / 16KB（设备相关） |

**结论**：Android 8+ 上的 Inline Hook 需要处理 `mprotect()` 权限、icache flush 和运行时页大小。`execmem` 是否允许以实际 sepolicy / target / OEM 为准，不能假设所有设备都禁止 RWX。Android 14+ 还要额外注意动态代码加载的只读文件要求。任一环节出错都会导致 Hook 失败或进程崩溃。


## 补充：Linker Namespace 限制与 ByteDance Hook 库绕过机制

<!-- AIW-源码调研-2026-04-27 -->

### Android Linker Namespace 机制的演进

Android 从 7.0 (Nougat) 开始引入 Linker Namespace，用来**隔离私有系统库、防止应用依赖非 NDK API**。Android 8.0 (Oreo) 的 Project Treble 进一步强化了这套隔离机制，使它成为系统安全架构的基础组件。

**classloader-namespace 的分配流程**：

```text
Zygote 进程
  → libnativeloader.so 为 Java 应用创建 isolated classloader-namespace
  → namespace 的三层构成：
      1. App 本地 JNI search path：来自 ClassLoader 的 library_path
      2. Permitted path：允许绝对路径加载的额外目录（如 /data/data/<pkg>）
      3. Linked namespace：通过 app_ns->Link() 链接 system namespace
         与 APEX public libraries（public.libraries.txt /
         apex_public_libraries 定义的 NDK/public libs 可见）
  → 私有系统库（非 NDK）仍不可见
```

**dlopen 的 namespace 校验逻辑**（与标准 Linux 不同）：

Android 的 `dlopen` 内部实现会检查调用者的 `caller_addr`（调用者函数地址），Linker 根据该地址确定调用者所属的 soinfo，从而获知其 namespace。如果目标库路径不在 namespace 的允许列表中，加载失败并返回 NULL。

源码位置：
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
1. 获取目标 namespace 内某个已加载 ELF 的真实代码地址（例如通过 `/proc/self/maps` 定位基址后从 `.dynsym` 查符号，或使用 xDL 等库查询已加载 ELF 符号）
2. 将该真实代码地址（而非 dlopen 返回的 opaque handle）作为 `caller_addr` 传入，伪装成目标库自身在加载依赖
3. Linker 通过 `find_containing_library(caller_addr)` 在已加载 soinfo 列表中查找包含该地址的 soinfo，确认其 namespace，从而允许加载

> **dlopen handle 与 caller_addr 的区别**：`dlopen()` 返回的是 opaque handle（内部为 soinfo 指针，地址值本身不指向目标库的代码段），不能直接当作 `caller_addr` 使用。`bionic/linker/linker.cpp` 的 `do_dlopen()` 调用 `find_containing_library(caller_addr)` 期望收到的是进程内某条已执行指令的地址，以便定位调用者所属的 soinfo。

#### 手段三：ShadowHook 的 do_dlopen Hook

ShadowHook 能够在用户 hook 一个**尚未加载**的库时，内部 hook 链接器的 `do_dlopen` 函数。当目标库通过正常路径加载时，ShadowHook 的 hook 先被触发：

1. 完成用户请求的 hook 操作
2. 放行让原始 `do_dlopen` 继续执行

同时，ShadowHook 支持注册 `.init` / `.init_array` / `.fini` / `.fini_array` 的回调，用于在库加载完成后执行自定义逻辑，从而支持符号查询、namespace 绕过等操作。

ShadowHook README 给出这段说明：
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
| **W^X 影响** | PLT/GOT 改写不修改目标函数代码页；但 upstream ARM/ARM64 trampoline 与 dlopen 监控仍需 execmem/RWX | 需修改代码页权限 + icache flush |

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

ShadowHook 在 `.init_array` 段缓存 `dlopen` / `dlsym` 的函数地址（主要用于 Android 4.x 兼容），目的是降低这些符号被 PLT-hook 拦截的概率——因为后续调用走的是保存好的函数指针而非 PLT 表项。

### Android 11+ namespace API 限制变化的历史脉络

| Android 版本 | 关键变更 |
|--------------|---------|
| Android 7.0 (API 24) | 引入 linker namespace，初步隔离 |
| Android 8.0 (API 26) | classloader-namespace 分配给 Java App（Treble 核心） |
| Android 9 (API 28) | 进一步强化限制，禁止加载私有 API |
| Android 10 (API 29) | `android_create_namespace()` 不再从 `libdl.so` 导出；内部实现入口为 `linker/dlfcn.cpp::__loader_android_create_namespace` |
| Android 14 (API 34) | Safer dynamic code loading：DEX/JAR/APK 加载前必须只读；native W^X 约束未变 |
| Android 16 (API 36) | ShadowHook 支持至 API 36 |

`android_create_namespace()` 在 Android 8 中允许创建自定义 namespace 并指定 LSPath 和隔离规则，但该函数在 Android 10 起不再从 `libdl.so` 导出（`libdl.map.txt` 已确认）。后续版本内部实现入口为 `linker/dlfcn.cpp` 的 `__loader_android_create_namespace` / `create_namespace`，不再是对外可用的公共 API。这是 namespace 绕过技术（尤其是 soinfo 修改和 `__loader_dlopen` 技巧）存在的技术背景。

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

源码级调研显示，主流 Hook 库已在构建层面显式支持 16KB 对齐：

**ByteHook v1.1.1** (`bytehook/src/main/cpp/CMakeLists.txt`)：
```cmake
if((${ANDROID_ABI} STREQUAL "arm64-v8a") OR (${ANDROID_ABI} STREQUAL "x86_64"))
    set(ARCH_LINK_FLAGS "-Wl,-z,max-page-size=16384")
else()
    set(ARCH_LINK_FLAGS "")
endif()
target_link_options(bytehook PUBLIC ${ARCH_LINK_FLAGS})
```
arm64-v8a 和 x86_64 显式设置 16KB 对齐，armeabi-v7a 保持空（32 位 ARM 无强制要求）。

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

compat mode 使用匿名映射将 4KB 对齐的 ELF 段内容读入进程空间，PSS 和共享内存都有额外代价。RELRO 保护在 compat mode 下仍然执行（`soinfo::protect_relro()` 调用 `mprotect(PROT_READ|PROT_EXEC)`），但布局受连续约束限制：兼容布局为 RO|RX + RELRO prefix + RW，`IsEligibleFor16KiBAppCompat()` 负责检查段排列是否满足此要求。Google Play 的 2025-11-01 要求适用于提交到 Google Play、面向 Android 15 (API 35)+ 设备的新应用和既有应用更新，不是所有存量应用或所有设备在同一天统一强制。

| 构建层 | 负责对象 | 16KB 边界 |
|--------|----------|-----------|
| NDK/LLD r27 及以下 | ELF `PT_LOAD.p_align` | 通常需要显式补 `-Wl,-z,max-page-size=16384` |
| NDK/LLD r28+ | ELF `PT_LOAD.p_align` | 默认生成 16KB 对齐的 native library |
| AGP 8.5.1+ / zipalign | APK 内未压缩 native library 的打包对齐与检查 | 解决 APK 打包侧对齐，不等同于修改 ELF `p_align` |

### mprotect 在 16KB 页面下的约束

Inline Hook 修改被保护页面时：
1. `mprotect(addr, size, PROT_READ|PROT_WRITE)` 去除写保护
2. 修改指令（bl/jmp 等）
3. `mprotect(addr, size, PROT_READ|PROT_EXEC)`
4. `__builtin___clear_cache()` → ARM64: `dc cvau → dsb ish → ic ivau → dsb ish → isb`

**16KB 页面下的 `mprotect` 约束**：`addr` 必须按 16KB 边界对齐（通过 `addr & ~(page_size - 1)` 计算）；`size` 参数指定覆盖范围，内核自动按页粒度向上取整，不需要调用方手动凑成页大小整数倍。如果 `addr` 没有按实际页大小对齐，`mprotect()` 会返回 `EINVAL`。


## 补充：Bionic Linker Namespace 隔离机制与 Hook 库绕过手段源码深度分析

<!-- AIW-源码调研-2026-05-07 -->

### Linker Namespace 隔离的校验逻辑

**源码位置**：`bionic/linker/linker_namespaces.cpp:android_namespace_t::is_accessible`

Android 7 引入的 Linker Namespace 机制通过 `android_namespace_t` 结构管理独立库空间搜索路径。`is_accessible()` 是 dlopen 时的核心校验函数：

```cpp
bool android_namespace_t::is_accessible(const std::string& file) {
  if (!is_isolated_) {
    return true;  // 非隔离命名空间直接放行
  }
  if (!allowed_libs_.empty()) {
    const char *lib_name = basename(file.c_str());
    if (std::find(allowed_libs_.begin(), allowed_libs_.end(), lib_name) == allowed_libs_.end()) {
      return false;  // 不在白名单，拒绝
    }
  }
  // ld_library_paths → default_library_paths → permitted_paths 顺序查找
  for (const auto& dir : ld_library_paths_) {
    if (file_is_in_dir(file, dir)) return true;
  }
  for (const auto& dir : default_library_paths_) {
    if (file_is_in_dir(file, dir)) return true;
  }
  for (const auto& dir : permitted_paths_) {
    if (file_is_under_dir(file, dir)) return true;
  }
  return false;
}
```

当 `is_isolated_ == true` 时，dlopen 加载库必须满足以下条件之一：
1. 库文件名在 `allowed_libs_` 白名单中
2. 库路径在 `ld_library_paths_` 目录下
3. 库路径在 `default_library_paths_` 目录下
4. 库路径在 `permitted_paths_` 目录下

Android 8+ 通过 `/system/etc/ld.config.txt` 配置隔离规则，Android 10 起不再从 `libdl.so` 导出 `android_create_namespace()`，外部应用无法直接创建自定义 namespace。

**符号可见性**：`is_accessible(soinfo*)` 判断符号查找权限时，允许 secondary namespace 成员参与查找，但不含传递依赖：

`is_accessible(soinfo* s)` 判断符号查找权限，逻辑分三步：

1. 检查 `s` 的 `primary_namespace_` 是否为当前 namespace（直接成员直接放行）
2. 检查 `s` 的 `secondary_namespaces_` 是否包含当前 namespace（secondary 成员放行，不含传递依赖）
3. 递归检查 `s` 的所有 parent soinfo：对每个 parent 调用 `is_accessible_ftor(parent, false)`（`allow_secondary=false`，即递归时不允许 secondary 匹配），全部通过则放行

### 16KB Compat Mode 加载逻辑（4KB ELF 在 16KB 设备）

**kCompatPageSize 常量**（`linker_phdr.h:44`）：
```cpp
static constexpr size_t kCompatPageSize = 0x1000;  // 4096
```

**CompatMapSegment** 核心实现（`linker_phdr_16kib_compat.cpp`）：
```cpp
bool ElfReader::CompatMapSegment(size_t seg_idx, size_t len) {
  const ElfW(Phdr)* phdr = &phdr_table_[seg_idx];
  // 4KB 对齐段起始（不是 16KB）
  void* start = reinterpret_cast<void*>(
      __builtin_align_down(phdr->p_vaddr + load_bias_, kCompatPageSize));
  // 从 ELF 文件读取内容到匿名映射（mmap 16KB 对齐无法直接用于 4KB ELF）
  const ElfW(Addr) offset = file_offset_ + __builtin_align_down(phdr->p_offset, kCompatPageSize);
  if (TEMP_FAILURE_RETRY(pread64(fd_, start, len, offset)) == -1) {
    return false;
  }
  return true;
}
```

**段布局兼容性判断** `IsEligibleFor16KiBAppCompat`：
```cpp
// 兼容布局：RO|RX* + (RELRO prefix)? + RW*
// 非兼容布局：多个非相邻 RW 段、RELRO 不在首个 RW 段内
bool ElfReader::IsEligibleFor16KiBAppCompat(ElfW(Addr)* vaddr) {
  // 1. 至多一个 RELRO segment
  if (!HasAtMostOneRelroSegment(&relro_phdr)) return false;
  // 2. 检查 RW 段连续性（多个非相邻 RW → 不兼容）
  // 3. RELRO 必须在第一个 RW 段内
  if (relro_phdr && !segment_contains_prefix(first_rw, relro_phdr)) return false;
  *vaddr = __builtin_align_up(end, kCompatPageSize);  // 计算 RX|RW 边界
  return true;
}
```

触发条件：`linker_phdr.cpp` — `kPageSize == 16384 && min_align_ == 4096`。

### ShadowHook Trampoline Island 与可执行内存放置策略

**Island 与 Gap**：ShadowHook 需要一块可执行内存来存放跳转 stub（trampoline）。首选方案是分配匿名 RWX mmap 页（island），不需要依赖目标 ELF 的空闲区域；当 island 不可用或想节省映射时，则回退到 ELF PT_LOAD 段末尾的未使用空间（gap）。Gap 本身解决的是 trampoline 的放置问题——分支距离超出 ARM64 B 指令 ±128MB 范围时，需要一个中间跳板。

**Namespace 绕过**：ShadowHook 的 namespace bypass 能力来自对已加载 ELF 的符号查询（`.dynsym` / `.symtab`），通过 `xdl_*` 系列函数直接解析进程内存中的 ELF 头和符号表，不经过 `dlsym()`，因此不受 linker namespace 可见性约束。

**gap 发现算法**（`sh_elf.c:sh_elf_get_gaps_from_phdr`）：
```cpp
// ARM: SH_ELF_UNIT_SIZE=8, ARM64: SH_ELF_UNIT_SIZE=4
// 计算段末尾到下一页起始的未使用空间
uintptr_t cur_end = base + cur_phdr->p_vaddr + cur_phdr->p_memsz;
uintptr_t cur_page_end = page_end(cur_end);
uintptr_t next_page_start = page_start(base + next_phdr->p_vaddr);

if (cur_phdr->p_flags & PF_X) {
  gap_start = align_end(cur_end);
  gap_end = next_page_start;
} else if (cur_page_end > cur_file_page_end) {
  // .bss 段（无文件后端）
  gap_start = align_end(cur_end);
  gap_end = next_page_start;
} else if (next_page_start > cur_page_end) {
  // 整页未使用空间
  gap_start = cur_page_end;
  gap_end = next_page_start;
}
```

**useless symbol 策略**：对 linker 等特殊库，转而利用 `__linker_init` 等无用符号的内存空间：
```cpp
void* sym_addr = xdl_sym(handle, sym->sym_name, &sym_sz);
uintptr_t gap_start = align_end(sym_addr);
uintptr_t gap_end = align_start((uintptr_t)sym_addr + sym_sz);
```

**load_bias 重新获取**（绕过 dladdr 限制）：
```cpp
// 使用 getauxval(AT_PHDR) 重新计算 load_bias
uintptr_t base = (AT_PHDR == type ? sh_util_page_start(val) : val);
ElfW(Ehdr) *ehdr = (ElfW(Ehdr) *)base;
uintptr_t min_vaddr = UINTPTR_MAX;
for (size_t i = 0; i < dlpi_phnum; i++) {
  if (PT_LOAD == phdr[i].p_type && min_vaddr > phdr[i].p_vaddr) {
    min_vaddr = phdr[i].p_vaddr;
  }
}
uintptr_t load_bias = base - min_vaddr;
```

**gap trampoline 与 namespace bypass 的关系**：gap/island 解决的是跳转距离和 trampoline 放置问题，本身不是 namespace bypass 手段。Namespace bypass 来自 ShadowHook 对已加载 ELF 的直接符号查询能力（`.dynsym` / `.symtab`），不经过 `dlsym()`。

### 主流 Hook 库 Namespace 绕过能力对比

| 库 | 类型 | dlopen 拦截 | Gap Trampoline | 符号查询 |
|----|------|------------|---------------|---------|
| ByteHook | PLT Hook | ✅ hook dlopen | ❌ | ❌ |
| ShadowHook | Inline Hook | ✅ hook do_dlopen | ✅ | ✅ bypass namespace |
| xHook | PLT Hook | ❌ 不支持 API 29+ | ❌ | ❌ |

**符号查找边界**：ShadowHook 支持绕过 namespace 限制查询任意 ELF 的 `.dynsym` 和 `.symtab`，而 ByteHook 仅在 PLT 层面工作，不涉及 namespace 访问限制。


## 与全书主线的关系

Hook 基础设施和全书主线直接相连：

- `14.5` 里提到的很多三方性能库，都依赖这里的实现路线
- `14.12` 里的 APM 选型，如果不懂机制，选型就很容易只停留在功能表层
- `15.5` 讲线上监控时，很多"客户端增强层"能力实际都建立在这里

读完后需要能判断三件事：工具为什么能做到这些，边界会出在哪里，为什么不能被当成"万能方案"。

## 补充：ShadowHook 的 Trampoline 注入与 ARM32 Thumb 模式处理

<!-- AIW-源码调研-2026-05-04 -->

### ShadowHook 的 Trampoline 管理架构

ShadowHook upstream 的实现文件主要分布在这些路径：

| 文件 | 职责 |
|------|------|
| `shadowhook/src/main/cpp/sh_trampo.c` | Trampoline 分配与管理（island 内存分配、释放、查找） |
| `shadowhook/src/main/cpp/sh_island.c` | 远跳 island 的核心逻辑（分配可执行代码页） |
| `shadowhook/src/main/cpp/arch/arm64/sh_inst.c` | ARM64 指令生成（LDR/BR literal stub、原始指令备份） |
| `shadowhook/src/main/cpp/arch/arm/sh_t16.c` | ARM32 Thumb-16 指令生成 |
| `shadowhook/src/main/cpp/arch/arm/sh_t32.c` | ARM32 Thumb-32 指令生成 |
| `shadowhook/src/main/cpp/common/sh_util.c` | 工具函数（mprotect 封装、icache flush） |

**ARM64 stub 策略**（区分 with-island 和 no-island）：

- **with-island**（跳转距离 ≤ ±128MB）：函数入口写入 4 字节 `B` 相对跳转指令，跳转到 island 中间跳板。Island 中写入 `LDR X17, #offset` + `BR X17`（16B）+ literal pool。
- **no-island**（远跳转或 island 不可用）：函数入口直接写入 20 字节绝对跳转 stub（`NOP` + `sh_a64_absolute_jump_with_br_ip()`，共 20B），原始指令备份 20 或 24 字节到 trampoline 页。函数入口被替换为：

```asm
; no-island 路径（20 字节，函数入口直接写入）
0x00: nop                          ; 填充对齐
0x04: ldr x17, #0x08              ; 从 [pc+8] 加载 trampoline 地址
0x08: br x17                      ; 无条件跳转至 x17
0x0c: .quad <trampoline_addr>     ; literal pool（8B）
0x14: ...(trampoline 中保存的原始指令)
```

**ARM32 Thumb stub 策略**（区分 with-island 和 no-island）：

- **with-island**（跳转距离 ≤ ±2MB）：函数入口写入 4 字节 Thumb-2 相对跳转（`B.W`），跳转到 island 中间跳板。Island 中写入 `LDR R0, [PC, #imm]` + `BX R0`（4B 指令 + 4B 地址 = 8B）。
- **no-island**（远跳转）：函数入口写入 `sh_t32_absolute_jump`（8 或 10 字节 Thumb-2 绝对跳转），原始指令备份到 trampoline 页：

```asm
; no-island 路径（Thumb-2，函数入口写入）
0x00: ldr r0, [pc, #4]           ; 从 [pc+4] 加载地址到 r0
0x02: bx r0                      ; 跳转至 r0
0x04: .word <trampoline_addr>    ; literal pool（4B）
```

**模式判断逻辑**（源码示意）：
```cpp
static bool is_thumb_mode(uintptr_t addr) {
    return (addr & 0x1);  // Bit[0] = 1 表示 Thumb 模式
}
```

### 远距离跳转的居中 Trampoline 页策略

当跳转距离超过 ±128MB（ARM64 B 指令范围）时：
1. 通过 `sh_trampo.c` 中的 `mmap(NULL, size, PROT_READ|PROT_WRITE|PROT_EXEC, MAP_ANONYMOUS|MAP_PRIVATE, -1, 0)` 分配匿名 RWX 内存页作为 island
2. 在 island 中写入跳转指令（ARM64 为 `LDR X17, #offset` + `BR X17`），然后执行 `__builtin___clear_cache` 刷新 icache。upstream ShadowHook 的 `sh_util_mprotect` 在 island 分配时直接使用 RWX 权限，写入完成后不再单独调整为 RX
3. 原入口处写入跳转指令（`b #offset` 或 `bl #offset`），同样需要 mprotect 和 icache flush
4. 上游 ShadowHook 在 island 分配时直接使用 RWX mmap，简化了写入流程；部分设备上如果 SELinux 禁止 execmem，这一步会失败

**可执行内存的 SELinux 约束**：匿名 mmap 分配 RWX 权限需要 `execmem`，AOSP sepolicy `private/app.te` 中默认 `allow appdomain self:process execmem`，但 OEM 可能改严或移除此规则。ShadowHook 依赖此权限可用，在严格策略的设备上 Hook 会失败。

### ShadowHook v2.0.0 支持 intercept（断点级拦截）

与 hook（全函数替换）不同，intercept 允许在任意指令位置拦截，类似调试器的断点功能：

```c
void artmethod_invoke_interceptor(shadowhook_cpu_context_t *ctx, void *data) {
    // 可读取和修改寄存器值
    if (ctx->regs[19] == 0) {
        ctx->regs[20] = 1;   // 修改 x20 寄存器的值
    }
    // 拦截后继续执行原始指令
}

stub = shadowhook_intercept_instr_addr(
    instr_addr,
    artmethod_invoke_interceptor,
    NULL,
    SHADOWHOOK_INTERCEPT_WITH_FPSIMD_READ_WRITE);
```

intercept 支持 FPSIMD 寄存器读写（ARM64 的 `vregs[0].q` 等），可获取完整的向量寄存器状态。

### ShadowHook 的模式选择（shared / multi / unique）

| 模式 | 多 hook 共存 | 递归检测 | 性能 | 适用场景 |
|------|-------------|---------|------|---------|
| shared | ✅ 互不干扰 | ✅ 自动 | 略低 | 通用场景 |
| multi | ✅ 互不干扰 | ❌ 需自行处理 | 最优 | 高频 hook 点 |
| unique | ❌ 互斥 | ❌ 需自行处理 | 同 multi | 安全/隐私 SDK |

shared 模式的 proxy 函数链自动避免递归/环形调用，每个 proxy 函数执行前会检测目标是否已在执行栈中。
