---
title: "Scudo 分配器与 Native Heap 性能边界"
chapter: "23.11"
status: ready-for-review
drafted_date: "2026-05-24"
applicable_versions: "Android 11 (API 30) - Android 17 (API 37)"
last_verified: "2026-05-24"
last_verified_against: "AOSP main / Android Developers 2026-03~04 文档"
confidence: medium
sources:
  - type: aosp
    path: "source.android.com/docs/security/test/scudo"
  - type: aosp
    path: "source.android.com/docs/core/tests/debug/native-memory"
  - type: aosp
    path: "frameworks/base/core/jni/android_os_Debug.cpp"
  - type: aosp
    path: "bionic/libc/bionic/malloc_common.cpp"
  - type: aosp
    path: "system/memory/libmemunreachable/MemUnreachable.cpp"
  - type: official
    path: "developer.android.com/studio/profile/record-native-allocations"
  - type: official
    path: "developer.android.com/ndk/guides/gwp-asan"
  - type: official
    path: "developer.android.com/guide/practices/page-sizes"
  - type: official
    path: "source.android.com/docs/security/test/memory-safety/arm-mte"
  - type: book
    path: "Clippings/Android 性能优化 - Native 内存优化（上）：so 库申请的内存优化.md"
  - type: book
    path: "Clippings/Android 性能优化 - 原理：掌握 App 运行时的内存模型.md"
  - type: book
    path: "Clippings/Android 应用稳定性剖析与优化 - Native 内存泄漏监控：寻找 Native 中不可达内存.md"
tags: [native-memory, scudo, allocator, heapprofd, gwp-asan]
related_chapters: ["4.5", "14.3", "20.11", "23.3", "26.16"]
created_by: "task2a-knowledge-gap"
created_date: "2026-05-24"
gap_source: "素材驱动/官方文档/Clippings结构参考"
---

# 23.11 Scudo 分配器与 Native Heap 性能边界

Native Heap 治理容易被写成一条 `malloc` 曲线的治理，但线上问题很少这么干净。`dumpsys meminfo` 里的 Native Heap、`Debug.getNativeHeapAllocatedSize()`、`smaps` 里的匿名映射、heapprofd 的分配栈、Bitmap 像素内存和图形缓冲区，回答的是不同问题。把这些口径混在一起，会把 allocator 行为、业务分配、图形资源和文件映射揉成一个无法解释的指标。

这一节只处理实践边界：Scudo 在 Android Native 分配路径中管什么，Native Heap 异常该按什么顺序观察，哪些开关适合线上采样，哪些只能放到调试或灰度环境。Native 内存的基础分层见 4.5 节，工具总览见 14.3 节，Native 内存管理的常规排查见 23.3 节，MTE 崩溃治理见 20.11 节。

[结构参考: Clippings/Android 性能优化 - Native 内存优化（上）：so 库申请的内存优化.md]
[结构参考: Clippings/Android 性能优化 - 原理：掌握 App 运行时的内存模型.md]
[结构参考: Clippings/Android 应用稳定性剖析与优化 - Native 内存泄漏监控：寻找 Native 中不可达内存.md]

## Native Heap 不等于所有 Native 内存

Native Heap 指标要拆成三层看。

- 分配器口径：`malloc()`、`calloc()`、`realloc()`、`new`、`delete` 等 C/C++ 堆分配入口，最终由 bionic 的 malloc dispatch 交给当前 allocator。Android 11 之后，常规 native 代码默认使用 Scudo，低内存设备仍可能使用 jemalloc。[已验证: AOSP Scudo 文档, source.android.com/docs/security/test/scudo]
- 进程地址空间口径：`/proc/<pid>/maps` 和 `/proc/<pid>/smaps` 按 VMA 记录地址区间、权限、映射文件、匿名映射和 RSS/PSS 等统计。`mmap()` 既能映射文件，也能申请匿名内存；匿名映射未必都来自 `malloc()`。
- Android 内存分类口径：`dumpsys meminfo` 把 smaps、libmemtrack、allocator 统计等数据整理成 Native Heap、Dalvik Heap、Graphics、Stack、Code、Unknown 等类别。Graphics 中一部分可能不映射到应用进程地址空间，需要 libmemtrack 补齐。[已验证: AOSP main, frameworks/base/core/jni/android_os_Debug.cpp]

这三层口径的误差就是排查入口。`Debug.getNativeHeapAllocatedSize()` 走 `mallinfo().uordblks`，适合低成本记录分配器已分配字节数；`dumpsys meminfo` 更适合看系统分类和 PSS；heapprofd 更适合把 Native Heap 分配归因到调用栈；`smaps` 适合确认匿名映射、文件映射、线程栈和 so 映射的具体分布。[已验证: AOSP main, frameworks/base/core/jni/android_os_Debug.cpp]

Bitmap 是最容易混入口径的对象。Android 8.0 之后，Bitmap 像素内存计入 Native 侧，但治理入口通常仍在 Java/Kotlin 层：图片尺寸、解码格式、缓存策略、生命周期引用。Bitmap 原理和常规优化见 4.5 节与 23.3 节；在 Native 指标解释里，它主要是一个分叉项。

一个实用判断：如果 `Debug.getNativeHeapAllocatedSize()` 和 heapprofd 的趋势一起涨，优先看 C/C++ 分配栈；如果 `dumpsys meminfo` 的 Graphics 或 Unknown 涨得更快，就不要急着改 allocator 配置，先回到 `smaps`、libmemtrack、Bitmap 与图形资源路径。

## Scudo 在 Android 分配路径中的位置

Scudo 是用户态 heap allocator，提供 `malloc/free` 和 `new/delete` 等标准分配与释放入口。它的目标是提高堆内存安全性，例如检测堆溢出、use-after-free、double free 等风险；它不是 ASan/HWASan 那种完整内存错误检测器。[已验证: AOSP Scudo 文档, source.android.com/docs/security/test/scudo]

在 Android 运行时路径里，可以按职责分层：

- bionic libc：暴露 `malloc()`、`calloc()`、`realloc()`、`free()`、`mallinfo()` 等接口，并通过 malloc dispatch 指向当前分配器或调试实现。[已验证: AOSP main, bionic/libc/bionic/malloc_common.cpp]
- Scudo：服务常规 native heap 分配，维护 chunk metadata、quarantine、校验、随机化等安全机制。它发现不可恢复的堆损坏时，会打印 `Scudo ERROR` 并终止进程。
- GWP-ASan：抽样拦截一小部分 heap allocation，把样本放进特殊区域，用来捕获 use-after-free 和 heap-buffer-overflow。它不要求重新编译，Android 11+ 面向 targetSdk 30+ 应用可用。[已验证: 官方文档, developer.android.com/ndk/guides/gwp-asan]
- MTE：Arm 硬件内存标记能力，由硬件、内核、用户态 allocator 和进程配置共同生效。`android:memtagMode` 的选择和崩溃归因见 20.11 节。[已验证: AOSP MTE 文档, source.android.com/docs/security/test/memory-safety/arm-mte]
- heapprofd / Android Studio Native Allocations / malloc debug：它们是观测工具，负责采样、记录栈和展示分配事件，不负责改变业务分配模式。

因此，线上 Native Heap 治理不应从“换 allocator”开始。Android 平台已经提供默认 allocator，应用侧更常见的工作是降低异常大块分配、减少泄漏、拿到可归因的分配栈、为灰度开关设定回滚条件。

## 安全检查与性能成本的取舍

Scudo 的安全能力不是零成本。quarantine 会延迟释放 chunk，使 use-after-free 更容易被发现，但也会增加内存占用；chunk metadata 和校验能发现损坏，但会增加 allocator 内部工作；释放回 OS 的策略影响 RSS 回落速度。AOSP 文档列出的 `QuarantineSizeKb`、`ThreadLocalQuarantineSizeKb`、`QuarantineChunksUpToSize`、`ZeroContents`、`hard_rss_limit_mb`、`soft_rss_limit_mb`、`allocator_release_to_os_interval_ms` 等选项，适合平台进程、系统调试或受控实验，不适合作为普通 App 的线上调参入口。[已验证: AOSP Scudo 文档, source.android.com/docs/security/test/scudo]

应用侧更可控的是 GWP-ASan 和 MTE：

| 能力 | 适用场景 | 线上建议 | 成本边界 |
| --- | --- | --- | --- |
| GWP-ASan `android:gwpAsanMode="always"` | 复现困难的 native heap use-after-free / overflow | 小流量灰度或问题进程单独开启 | 固定 RAM 开销约 70 KiB/受影响进程；命中后进程终止 |
| Recoverable GWP-ASan | Android 14+ 生产环境发现内存破坏 | 保留默认行为，APM 侧接入历史退出原因 | 约 1% app launch 抽样；每次启动最多一份报告；报告后继续运行但进程状态不可再假设安全 |
| MTE ASYNC | 低开销发现内存安全问题 | 已充分测试的进程可灰度 | 错误定位不如 SYNC 精确 |
| MTE SYNC | 测试、专项复现、攻击面高的进程 | 不作为大盘默认开关 | 命中时立即 SIGSEGV，开销更高 |
| HWASan / ASan | 本地复现和开发测试 | 不作为线上方案 | 需要专门构建或运行环境，开销大 |

[已验证: 官方文档, developer.android.com/ndk/guides/gwp-asan]
[已验证: AOSP MTE 文档, source.android.com/docs/security/test/memory-safety/arm-mte]

线上策略应写成灰度矩阵，而不是单一开关：先按进程、ABI、机型、Android 版本、targetSdk 切分，再设定退出条件。退出条件至少包括 native crash 率、`ApplicationExitInfo` 中的 native tombstone 占比、PSS/RSS 抖动、启动和核心页面耗时。MTE 和 GWP-ASan 报告都指向真实内存安全问题，但报告触发具有抽样性；没有报告不代表没有 bug。

## Native 内存异常的观测路径

排查顺序从低成本到高证据密度推进。

### 1. 大盘指标确认异常形态

线上监控先记录这些字段：

- PSS/RSS：用于判断进程对系统内存压力的贡献。PSS 更适合大盘统计，RSS 更适合低成本趋势和 LMKD 风险判断。
- Native Heap Alloc / Free：来自 allocator 统计，适合观察 `malloc` 家族分配趋势。它不覆盖所有映射和图形资源。
- Graphics / Unknown / Code / Stack：来自 `dumpsys meminfo` 分类，用来判断异常是否偏离 Native Heap。
- 分配速率和峰值回落：持续增长指向泄漏或缓存无上限，尖峰后不回落要区分 allocator 保留、业务缓存和匿名映射残留。
- 进程退出归因：native crash、low memory kill、ANR 和用户主动退出要分开统计。

指标层只负责确认问题形态，不负责裁决代码归因。

### 2. 线下用 `dumpsys meminfo` 和 `smaps` 建立分类

这组命令用于把系统分类和地址空间明细拉到本地，比单看 Android Studio 面板更适合做一次完整快照。

```bash
adb shell dumpsys meminfo <package_or_pid> > meminfo.txt
adb shell cat /proc/<pid>/smaps > smaps.txt
adb shell showmap <pid> > showmap.txt
```

`meminfo.txt` 看 Native Heap、Graphics、Unknown、Code、Stack 的相对占比；`smaps.txt` 看匿名映射、文件映射、线程栈和 so 映射；`showmap.txt` 适合快速按 VMA 汇总。没有 root 时，应用读取其他进程的 `/proc/<pid>/smaps` 会受权限限制，调试环境可通过本进程或 debuggable 包补证据。

### 3. heapprofd 把 Native Heap 分配归因到调用栈

Android 10 支持 heapprofd，它是低开销采样 heap profiler，可以把 native memory usage 归因到调用栈。[已验证: AOSP native-memory 文档, source.android.com/docs/core/tests/debug/native-memory]

heapprofd 适合回答三个问题：哪条调用栈分配最多，哪类分配持续留存，哪段操作触发分配尖峰。它不适合回答 Graphics buffer、文件映射、线程栈数量等非 allocator 问题。若 heapprofd 样本无法解释 `dumpsys meminfo` 的增长，回到 smaps 分类，不要硬套 `malloc` 结论。

### 4. Android Studio Native Allocations 做交互式确认

Android Studio 的 Native Allocations 任务会记录指定时间段内 native code 的 allocations、deallocations、allocation size、remaining size，并用默认 2048 bytes 采样间隔生成快照。调小 sample size 会提高精度，也会增加记录开销。[已验证: 官方文档, developer.android.com/studio/profile/record-native-allocations]

它适合本地复现场景：打开目标页面、执行固定操作、停止录制、按 remaining size 或 allocation size 找调用栈。线上归因仍建议用 heapprofd、tombstone、GWP-ASan/MTE 报告和自研采样数据汇合。

### 5. malloc debug、libmemunreachable 和 Native hook 只放到受控场景

malloc debug 能拦截 allocator 事件并记录更多调试信息，适合 root、userdebug 或本地复现环境。libmemunreachable 使用类似 mark-and-sweep 的方式扫描 native memory，报告不可达块；AOSP 代码中会遍历 heap mapping，也识别 `[anon:libc_malloc]`、`[anon:scudo:]`、`[anon:GWP-ASan]` 等映射，并通过 fork 出的 heap walker 进程收集结果。[已验证: AOSP main, system/memory/libmemunreachable/MemUnreachable.cpp]

Native hook 适合自研监控或专项排查，但要把成本写清楚：hook 范围、栈回溯方式、符号化、采样率、线程安全和崩溃兜底。第三方 so 无源码时，拿到分配栈也不等于能修复，只能支撑版本替换、功能降级、进程隔离或供应商反馈。

## 16KB Page、MTE 与 allocator 行为的交叉影响

从 Android 15 开始，AOSP 支持配置为 16 KB page size 的设备。Google Play 从 2025-11-01 起要求面向 Android 15+ 设备的新应用和更新在 64 位设备上支持 16 KB page size。含 NDK 或三方 native library 的应用需要重新构建并检查 ELF segment alignment。[已验证: 官方文档, developer.android.com/guide/practices/page-sizes]

16 KB page 影响的是页粒度、ELF 对齐、映射和内存回收边界，不应被写成“某个 allocator 一定更省内存”。AOSP 文档给出的测试收益包括启动、功耗、相机启动、系统启动时间等平均改善，但也明确 16 KB 设备平均内存使用略高，真实收益会随设备和 App 场景变化。[已验证: 官方文档, developer.android.com/guide/practices/page-sizes]

排查 16 KB 相关 Native 内存问题时，按这个顺序切分：

- APK 层：用 APK Analyzer、lint、`llvm-objdump` 和 `zipalign -P 16` 检查 so 对齐与打包状态。
- 映射层：用 `smaps` 看 so、匿名映射、线程栈和 ashmem/dma-buf 变化，不把所有 PSS 增长归到 allocator。
- 分配层：用 heapprofd 或 Native Allocations 看业务分配栈是否变化。
- 安全层：MTE 与 GWP-ASan 报告看内存破坏，不用它们解释常规内存峰值。

MTE 的 SYNC/ASYNC 选择、ASYMM 平台行为和 `android:memtagMode` 详见 20.11 节。这里的实践结论是：16 KB page、MTE、Scudo 是三条不同轴线。一个问题可能同时受它们影响，但证据也要分别采集。

## 线上治理指标与降级策略

Native Heap 的线上治理要把指标、样本和动作绑定起来。

| 目标 | 指标 | 触发条件示例 | 动作 |
| --- | --- | --- | --- |
| 发现持续泄漏 | Native Heap Alloc、PSS、remaining size、进程存活时长 | 同一会话内持续增长且退出页面后不回落 | 开启 heapprofd 采样或上报轻量分配栈；关联页面路径 |
| 发现大块分配 | 单次分配大小、调用栈、线程名 | 超过页面预算或设备分档阈值 | 降低图片/缓冲区尺寸；延迟加载；拆分批处理 |
| 发现内存破坏 | GWP-ASan/MTE tombstone、Scudo ERROR | use-after-free、heap-buffer-overflow、double free | 按 so、ABI、版本聚合；灰度停发；切换安全实现 |
| 控制系统压力 | PSS/RSS、LMKD 退出、后台存活时长 | 低内存设备或后台进程被杀上升 | 关闭大缓存；降低预加载；拆进程或延迟初始化 |
| 管住三方 so | so 名、版本、分配栈、tombstone build id | 同一三方库聚合异常 | 版本回滚、供应商升级、进程隔离、功能限流 |

阈值不要写成全量统一数字。高端机、低内存机、32 位进程、64 位进程、16 KB page 设备、图像密集页面、常驻后台进程，预算都不同。比较稳的做法是按设备内存档位设 P90/P95/P99 基线，再对单会话增长率、页面退出回落率和异常栈聚合设告警。

降级策略也要能被远程配置：关闭超大图预解码、降低 native cache 上限、延迟 so 初始化、暂停问题特性、切换三方 SDK 版本、把高风险任务移到独立进程。对 Native 内存安全问题，降级只是止血；GWP-ASan、MTE、Scudo 报告指向的代码路径仍要修。

## 扩展：malloc debug、heapprofd 与 Android Studio Native Allocations 的对照表

| 工具 | 适合回答的问题 | 版本/权限边界 | 线上使用 |
| --- | --- | --- | --- |
| `dumpsys meminfo` | 进程内存分类、PSS/RSS、Native Heap 与 Graphics 占比 | adb 或调试权限；线上只能采集低频摘要 | 可采摘要，不上传敏感映射明细 |
| `smaps` / `showmap` | VMA 级别映射来源、匿名映射、so、线程栈 | `/proc` 权限受系统版本和调试状态影响 | 只在授权调试或崩溃诊断中使用 |
| heapprofd | Native Heap 分配调用栈、分配热点、留存样本 | Android 10+；采样 profiler | 可做低频、受控采样 |
| Android Studio Native Allocations | 本地交互式录制 allocations/deallocations | Android Studio Profiler；调试设备 | 不作为线上方案 |
| malloc debug | 更重的 allocator 调试信息 | 多用于 root/userdebug/本地复现 | 不建议常态线上开启 |
| libmemunreachable | Native 不可达内存扫描 | 调用条件和权限受系统限制 | 可作为专项方案验证，不做大盘常开 |
| GWP-ASan | 抽样发现 heap use-after-free / overflow | Android 11+；manifest 或平台默认 | 可灰度，Android 14+ 关注 recoverable 报告 |
| MTE | 硬件标记发现内存安全问题 | 设备硬件、系统、manifest 共同决定 | ASYNC/ASYMM 可灰度，SYNC 更偏测试 |

## 扩展：Scudo / GWP-ASan / MTE 在 Native Crash 治理中的分工

Scudo 的 crash 多表现为 allocator 在释放、复用或检查 chunk 时发现状态不合法，例如 chunk header 损坏、double free、misaligned pointer、allocation/deallocation type mismatch。它提供的是“堆已经被破坏”的就地信号。[已验证: AOSP Scudo 文档, source.android.com/docs/security/test/scudo]

GWP-ASan 的价值在样本报告：命中的 allocation/deallocation trace、访问类型和错误原因会进入 native crash report。Android 14+ 的 Recoverable GWP-ASan 默认约 1% app launch 抽样，报告可通过 `ActivityManager#getHistoricalProcessExitReasons` 获取；报告后进程继续运行，但不应把后续行为当作可靠状态。[已验证: 官方文档, developer.android.com/ndk/guides/gwp-asan]

MTE 的价值在硬件标记检查。SYNC 模式定位更准，ASYNC/ASYMM 更适合低开销发现。它与 GWP-ASan 都能发现 use-after-free 和 buffer overflow，但触发方式、设备覆盖、报告形态和性能成本不同。章节 20.11 已展开 memtagMode 与 Native 崩溃治理。这里沿用那里的实践口径：线上按进程灰度，APM 聚合时保留 signal、si_code、fault address、allocation/deallocation trace、so build id、ABI、设备和系统版本。

## 扩展：三方 so 的 Native 内存治理

三方 so 的治理不要停在“找到堆栈”。没有源码、没有符号、没有稳定复现时，能做的动作主要有四类：

- 版本替换：对比三方 SDK 版本、build id、ABI 和异常占比，优先回滚或升级。
- 灰度隔离：按设备、系统、用户分组关闭高风险功能，避免全量触发。
- 调用路径限流：对图片处理、音视频编解码、模型推理、加密压缩等 native-heavy 路径加并发和尺寸上限。
- 进程隔离：把高风险 native 任务放到独立进程，结合进程级 GWP-ASan/MTE、退出原因和重启策略降低主进程损伤。

符号化链路要提前准备。native crash、GWP-ASan 报告、heapprofd 样本和自研分配栈都依赖 so build id、未 strip 符号、maps/smaps、ABI 和版本号。缺少这些字段时，只能得到“某个三方 so 异常”，很难把问题推进到可修复状态。

## 小结

Scudo 负责服务 Android 默认 native heap 分配并提供堆安全缓解；heapprofd、Native Allocations、malloc debug、libmemunreachable 负责观察；GWP-ASan 和 MTE 负责把抽样或硬件层面的内存安全问题暴露出来。线上治理的主线是分清口径、拿到栈、按进程灰度、按指标回滚。只看一条 Native Heap 曲线，无法判断问题属于 allocator、业务分配、Bitmap、图形缓冲区、线程栈还是文件映射。

## 参考资料

- [结构参考: Clippings/Android 性能优化 - Native 内存优化（上）：so 库申请的内存优化.md]
- [结构参考: Clippings/Android 性能优化 - 原理：掌握 App 运行时的内存模型.md]
- [结构参考: Clippings/Android 应用稳定性剖析与优化 - Native 内存泄漏监控：寻找 Native 中不可达内存.md]
- [已验证: AOSP Scudo 文档, source.android.com/docs/security/test/scudo]
- [已验证: AOSP native-memory 文档, source.android.com/docs/core/tests/debug/native-memory]
- [已验证: AOSP main, frameworks/base/core/jni/android_os_Debug.cpp]
- [已验证: AOSP main, bionic/libc/bionic/malloc_common.cpp]
- [已验证: AOSP main, system/memory/libmemunreachable/MemUnreachable.cpp]
- [已验证: 官方文档, developer.android.com/studio/profile/record-native-allocations]
- [已验证: 官方文档, developer.android.com/ndk/guides/gwp-asan]
- [已验证: 官方文档, developer.android.com/guide/practices/page-sizes]
- [已验证: AOSP MTE 文档, source.android.com/docs/security/test/memory-safety/arm-mte]
