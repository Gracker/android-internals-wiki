---
title: heapprofd、procfs CPU 与 Page Fault 分析
chapter: '26.13'
section: '26.13'
status: finalized
applicable_versions: Android 10 (API 29) - Android 17 (API 37); ProfilingManager 路径要求 Android 15 (API 35) 或更新版本
tags:
- heapprofd
- heap-profiling
- memory
- production
- perfetto
- permissions
- native-leak
- proc
- ProcessCpuTracker
- CPU
- monitoring
- observability
- /proc/stat
- page-fault
- minor-fault
- major-fault
- mmap
related_chapters:
- '4.4'
- '10.1'
- '14.8'
- '14.1'
- '15.3'
- '15.7'
- '20.11'
- '20.3'
- '20.6'
- '23.2'
- '23.3'
- '23.7'
- '26.6'
- '5.1'
- '5.2'
- '9.2'
- '14.3'
- '14.9'
- '15.16'
- '26.1'
- '26.14'
- '4.1'
- '4.8'
- '4.9'
- '15.2'
- '4.5'
last_verified: '2026-08-15'
last_source_verified_at: '2026-08-15'
last_verified_against: AOSP android-17.0.0_r1 heapprofd, Bionic, Perfetto Profiling module, and init sources; current Perfetto native heap profiler and SQL docs; current Android Developers profileable, ProfilingManager, ProfilingResult, and AndroidX HeapProfileRequestBuilder references, retrieved 2026-08-15
confidence: high
sources:
- type: legacy-reference-preserved
  path: external/perfetto/src/profiling/memory/heapprofd.cc
- type: legacy-reference-preserved
  path: external/perfetto/src/profiling/common/producer_support.cc
- type: legacy-reference-preserved
  path: external/perfetto/src/profiling/common/profiler_guardrails.cc
- type: legacy-reference-preserved
  path: external/perfetto/heapprofd.rc
- type: legacy-reference-preserved
  path: external/perfetto/src/profiling/memory/java_hprof_producer.cc
- type: legacy-reference-preserved
  path: external/perfetto/src/traced/probes/packages_list/packages_list_parser.cc
- type: legacy-reference-preserved
  path: system/memory/libmemunreachable/MemUnreachable.cpp
- type: legacy-reference-preserved
  path: developer.android.com/topic/performance/memory
- type: legacy-reference-preserved
  path: Clippings/Android 应用稳定性剖析与优化 - Native 内存泄漏监控：寻找 Native 中不可达内存.md
- type: legacy-reference-preserved
  path: Clippings/Android 性能优化 - Native 内存优化（上）：so 库申请的内存优化.md
- type: aosp
  path: https://android.googlesource.com/platform/external/perfetto/+/refs/tags/android-17.0.0_r1/src/profiling/memory/heapprofd_producer.cc
- type: aosp
  path: https://android.googlesource.com/platform/bionic/+/refs/tags/android-17.0.0_r1/libc/bionic/malloc_heapprofd.cpp
- type: aosp
  path: https://android.googlesource.com/platform/external/perfetto/+/refs/tags/android-17.0.0_r1/src/profiling/common/producer_support.cc
- type: aosp
  path: https://android.googlesource.com/platform/external/perfetto/+/refs/tags/android-17.0.0_r1/src/traced/probes/packages_list/packages_list_parser.cc
- type: aosp
  path: https://android.googlesource.com/platform/external/perfetto/+/refs/tags/android-17.0.0_r1/protos/perfetto/config/profiling/heapprofd_config.proto
- type: aosp
  path: https://android.googlesource.com/platform/external/perfetto/+/refs/tags/android-17.0.0_r1/heapprofd.rc
- type: aosp
  path: https://android.googlesource.com/platform/external/perfetto/+/refs/tags/android-17.0.0_r1/src/profiling/common/profiler_guardrails.cc
- type: aosp
  path: https://android.googlesource.com/platform/external/perfetto/+/refs/tags/android-17.0.0_r1/tools/heap_profile
- type: aosp
  path: https://android.googlesource.com/platform/packages/modules/Profiling/+/refs/tags/android-17.0.0_r1/service/java/com/android/os/profiling/Configs.java
- type: aosp
  path: https://android.googlesource.com/platform/packages/modules/Profiling/+/refs/tags/android-17.0.0_r1/service/java/com/android/os/profiling/ProfilingService.java
- type: official
  path: https://perfetto.dev/docs/data-sources/native-heap-profiler
- type: official
  path: https://perfetto.dev/docs/getting-started/memory-profiling
- type: official
  path: https://perfetto.dev/docs/analysis/sql-tables#heap_profile_allocation
- type: official
  path: https://developer.android.com/guide/topics/manifest/profileable-element
- type: official
  path: https://developer.android.com/reference/android/os/ProfilingManager
- type: official
  path: https://developer.android.com/reference/android/os/ProfilingResult
- type: official
  path: https://developer.android.com/topic/performance/tracing/profiling-manager/how-to-capture
- type: official
  path: https://developer.android.com/reference/androidx/core/os/HeapProfileRequestBuilder
- type: legacy-reference-preserved
  path: frameworks/base/core/java/com/android/internal/os/ProcessCpuTracker.java
- type: legacy-reference-preserved
  path: frameworks/base/core/java/com/android/internal/os/CpuTracker.java
- type: legacy-reference-preserved
  path: developer.android.com/reference/android/os/Debug.MemoryInfo
- type: legacy-reference-preserved
  path: Clippings/线上疑难问题 45.md
- type: legacy-reference-preserved
  path: https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/Documentation/filesystems/proc.rst
- type: legacy-reference-preserved
  path: https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/kernel/sched/cputime.c
- type: legacy-reference-preserved
  path: https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/fs/proc/stat.c
- type: legacy-reference-preserved
  path: https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/fs/proc/array.c
- type: legacy-reference-preserved
  path: https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/fs/proc/loadavg.c
- type: legacy-reference-preserved
  path: https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/kernel/sched/loadavg.c
- type: aosp
  path: https://android.googlesource.com/platform/system/sepolicy/+/refs/tags/android-17.0.0_r1/private/app_neverallows.te
- type: aosp
  path: https://android.googlesource.com/platform/system/sepolicy/+/refs/tags/android-17.0.0_r1/private/untrusted_app_all.te
- type: aosp
  path: https://android.googlesource.com/platform/system/core/+/refs/tags/android-17.0.0_r1/init/first_stage_init.cpp
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/os/Process.java
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/com/android/internal/os/ProcessCpuTracker.java
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/am/AppProfiler.java
- type: kernel
  path: https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r39/Documentation/filesystems/proc.rst
- type: kernel
  path: https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r39/kernel/sched/cputime.c
- type: kernel
  path: https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r39/fs/proc/stat.c
- type: kernel
  path: https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r39/fs/proc/array.c
- type: kernel
  path: https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r39/fs/proc/loadavg.c
- type: kernel
  path: https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r39/kernel/sched/loadavg.c
- type: official
  path: https://developer.android.com/about/versions/10/privacy/changes#restriction-access-proc-net
- type: official
  path: https://perfetto.dev/docs/data-sources/cpu-scheduling
- type: official
  path: https://perfetto.dev/docs/data-sources/memory-counters
- type: official
  path: https://source.android.com/docs/core/architecture/kernel/bpf
- type: official
  path: https://developer.android.com/reference/android/os/Process#getElapsedCpuTime()
- type: official
  path: https://developer.android.com/reference/android/os/SystemClock
- type: legacy-reference-preserved
  path: frameworks/base/core/jni/android_os_Debug.cpp
- type: legacy-reference-preserved
  path: https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/arch/arm64/mm/fault.c
- type: legacy-reference-preserved
  path: https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/mm/memory.c
- type: legacy-reference-preserved
  path: https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/include/linux/mm_types.h
- type: aosp
  path: https://android.googlesource.com/platform/system/extras/+/refs/tags/android-17.0.0_r1/simpleperf/event_table_generator.py
- type: aosp
  path: https://android.googlesource.com/platform/system/extras/+/refs/tags/android-17.0.0_r1/simpleperf/doc/android_application_profiling.md
- type: aosp
  path: https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/runtime/gc/collector/mark_compact.cc
- type: kernel
  path: https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r39/arch/arm64/mm/fault.c
- type: kernel
  path: https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r39/mm/memory.c
- type: kernel
  path: https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r39/include/linux/mm_types.h
- type: kernel
  path: https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r39/Documentation/admin-guide/mm/userfaultfd.rst
- type: official
  path: https://source.android.com/docs/core/perf/mmd
- type: official
  path: https://source.android.com/docs/core/architecture/16kb-page-size/getting-page-size
- type: official
  path: https://source.android.com/docs/core/tests/debug/native-crash
pipeline_stage: finalized
task2b_state: fixed
task6_state: reviewed
task9_state: reviewed
last_draft_polish_at: '2026-08-15T22:54:40+08:00'
last_draft_polish_run_id: 20260815-225440-gracker-writing-480
last_review_finalize_at: '2026-08-15T22:54:40+08:00'
last_review_finalize_run_id: 20260815-225440-gracker-writing-480
last_rework_at: '2026-08-15T22:54:40+08:00'
last_rework_run_id: 20260815-225440-gracker-writing-480
last_consolidated_at: '2026-08-24'
consolidated_from:
- src/part5-app/ch26-observability/19-heapprofd-production-deployment-permissions.md
- src/part5-app/ch26-observability/20-proc-filesystem-cpu-monitoring.md
- src/part5-app/ch26-observability/21-page-fault-analysis-android.md
---

# heapprofd、procfs CPU 与 Page Fault 分析

本文把三类低层资源证据放在一条排障链上：heapprofd 用采样调用栈回答 native 分配来自哪里，procfs 累计计数回答进程或线程在窗口内用了多少 CPU，Page Fault 计数与时间线则解释页面何时需要建立映射、读入或重试。三者观察对象、权限和分母不同，不能互相替代，但可以共同解释“内存上升、CPU 异常或关键路径等待”这类线上症状。

user build 是面向量产设备的系统构建类型，许多只供调试使用的权限会在其中关闭。普通应用只能稳定读取自身 CPU 与 fault 计数；系统级 native heap profile、全机 CPU 和内核事件还受 `ProfilingManager`、profileable、SELinux、Perfetto 会话身份或平台权限约束。

native heap 是 App 通过 `malloc`、C++ `new` 等接口，在 ART（Android Runtime）管理的 Java/Kotlin 对象堆之外维护的内存。Page Fault 则发生在 CPU 访问虚拟地址、页表或权限不能直接满足访问时。

平台源码以 `android-17.0.0_r1` 为锚点；procfs、CPU 记账与 Page Fault 实现另以 Android Common Kernel `android17-6.18-2026-06_r39` 复核。

heapprofd 随 Android 10 引入。Android 12 增加 named heap（由分配器注册名称、可单独选择的一类堆）、`all_heaps` 和 installer 过滤等配置。

Android 15 又通过 `ProfilingManager` 向普通应用开放受系统约束的 heap profile 请求，Android 17 保留这些入口。`<profileable>` 元素从 API 29 可用，`android:enabled` 属性从 API 30 可用；heapprofd 的起始版本仍是 Android 10。

## Native 分配采样、权限与开销

### heapprofd 记录什么

heapprofd 是 Perfetto 的 native heap 采样器。allocator（内存分配器）负责向进程发放和回收内存。

heapprofd 观察目标进程在采集窗口内经过受支持分配器的分配与释放，把采样大小、调用栈和内存映射写入 Perfetto trace。这里的 trace 是按时间保存多类诊断事件的跟踪文件。

默认 heap 为 `libc.malloc`。Bionic 是 Android 的 C 标准库实现，这个 heap 覆盖它的 `malloc`、`free`、`calloc`、`realloc` 以及 C++ `new`、`delete` 等路径。

一次 allocation 就是一次内存分配。heapprofd 记录采集期间抽样到的分配和释放事件，不扫描完整的进程堆快照，也不保存对象内容。不同内存对象需要配合不同证据：

| 对象 | heapprofd 可见性 | 补充数据源 |
|---|---|---|
| 会话期间的 `malloc` / `free` | 可采样并归因到调用栈 | Perfetto heap flamegraph（按调用栈聚合大小的火焰图） |
| 会话开始前已有的分配 | 缺少历史分配事件，无法还原来源 | 更早启动采集或做基线对照 |
| 直接用 `mmap` / `munmap` 建立或解除虚拟内存映射 | 默认不经过 `libc.malloc` heap | Perfetto ftrace 系统调用事件、`/proc/<pid>/maps` |
| DMA-BUF（供驱动或进程共享的内核缓冲区）、图形 buffer | 缺少分配器调用栈语义 | 图形内存统计工具 memtrack、`dmabuf_dump`、GpuMem |
| Java 对象引用关系 | native heap profile 不提供 | Java heap dump、Android Studio profiler |
| 分配器内部缓存 | 能看到应用层 free，无法直接说明 RSS 是否已归还 | `dumpsys meminfo`、smaps、分配器指标 |

这些边界决定了 heapprofd 最适合回答“采集窗口内，哪些调用栈产生了仍未释放的 native 分配”。

PSS（Proportional Set Size）会按比例计入共享页，用来估算可归属到进程的物理内存。仅凭 heapprofd 无法判断 PSS 增长的全部原因，也无法找出保住 native 对象的某个 Java 引用。

### Android 17 的工作流程

在 Perfetto 中，`traced` 是管理跟踪会话的核心服务，producer 是向会话提供数据包的组件，data source 是可启用的一类数据。Android 17 的 `heapprofd` producer 为 `android.heapprofd` data source 供数。

PID 是系统为一个运行中进程分配的数字 ID。对已运行进程的一次采集依次经过这些步骤：

1. `traced` 把 `android.heapprofd` data source 配置交给 heapprofd；
2. heapprofd 规范化进程名，扫描 `/proc` 找出目标 PID；
3. producer 向目标发送实时信号 `__SIGRTMIN + 4`，整数载荷 `si_value` 为 0，用来触发 Bionic 安装 heapprofd client；
4. Bionic 的 heapprofd 入口在专用线程中加载 `heapprofd_client.so`，安装 malloc dispatch；dispatch 是把分配调用转交给具体实现的一组函数入口；
5. 目标进程把采样事件写入共享 ring buffer；ring buffer 会循环复用一块固定内存，写满时等待空间或报错停止取决于 `block_client`；
6. heapprofd 的 unwinder（栈回溯器）读取事件，根据采样现场还原调用层级，并维护仍未释放的分配账目；
7. 会话停止或到达 continuous dump 时间点时，producer 写出 `ProfilePacket` 数据包；continuous dump 会在同一会话中周期性输出当前分配账目。

信号处理函数只触发安装流程。动态加载、连接 daemon（常驻后台的系统进程）和 hook 初始化由专用线程继续执行，不会全部堆在 signal handler 中。hook 是拦截原有函数入口以观察调用的机制。

Bionic 还会处理 heapprofd 与 GWP-ASan、malloc debug 等分配器 dispatch 的兼容关系。已有 malloc hook 不兼容时，heapprofd 可能拒绝安装。

GWP-ASan 会抽样保护少量分配，以发现越界或释放后使用；malloc debug 是 Bionic 提供的分配检查机制。

启动期目标使用另一条入口。heapprofd 在会话开始时设置按进程名匹配的系统属性，Bionic 随后在新进程初始化期间接入客户端。配置中的 `no_startup` 会关闭启动期接入，`no_running` 会跳过已经运行的进程。

### user build 的权限判定

UID 是 Android 用来区分应用和系统主体的数字身份。Android 17 的 `CanProfileAndroid()` 先看 build type：`userdebug` 和 `eng` 通过这一层，`user` build 继续检查 UID、会话发起者以及 `/data/system/packages.list` 中的包属性。

session initiator 表示是谁发起 Perfetto 会话。表中的规则适用于直接提交给 `android.heapprofd` data source 的配置。通过 `ProfilingManager` 请求时，应用不能自行填写 `session_initiator`；系统服务先核对 Binder 调用 UID 与包名，再生成只指向调用方包名的配置。两种入口采用不同的权限流程，结论不能混用。

#### 普通应用与两类发起者

普通 App UID 和 SDK sandbox UID 的 Android 17 判定如下：

| 会话发起者 | user build 所需属性 |
|---|---|
| shell / `SESSION_INITIATOR_UNSPECIFIED` | `profileable_from_shell` 或 `debuggable` |
| `SESSION_INITIATOR_TRUSTED_SYSTEM` | `profileable` 或 `debuggable` |

`profileable_from_shell` 对应 Manifest 中的 `android:shell="true"`，表示 shell 调试工具可以分析该应用；`profileable` 对应 `<profileable>` 处于 enabled 状态。trusted-system 允许系统服务采集未向 shell 开放的应用，但目标仍要声明 profileable 或 debuggable。

`SESSION_INITIATOR_TRUSTED_SYSTEM` 是 `traced` 赋予受信系统会话的身份。普通 App 即使在自己的 textproto 中写入该字段，也不会获得这项身份。

#### 其他 UID

`AID_APP_START` 是平台 UID 与普通应用 UID 的起始分界。平台 UID、isolated UID 和普通应用的处理不同：

- 平台 UID 小于 `AID_APP_START` 时，user build 只允许 trusted-system 发起者；
- SDK sandbox 是替 SDK 隔离运行代码的进程，其 UID 会映射回所属 App UID，再读取该包的 profileable 属性；
- isolated process 使用临时隔离 UID，无法直接映射到来源包。Android 17 只在 trusted-system 会话且 `packages.list` 中所有包都允许 trusted initiator 采集时放行；
- 其余 UID 范围在 user build 上拒绝。

isolated process 的判定有意从严。目标应用即使声明了 `<profileable>`，它的 isolated service 仍可能得不到 profile。排查时需要同时查看 trace 中的拒绝信息和 heapprofd 日志，只看主进程 Manifest 不足以确认权限。

#### installer 过滤

installer 是把目标 APK 安装到设备上的包或系统来源。`target_installed_by` 是 `HeapprofdConfig` 的可选过滤项，支持普通 installer 包名以及 `@system`、`@product`、`@null`；`@null` 表示 sideload，也就是没有 installer 包记录的侧载安装。配置未填写该字段时，`CanProfileAndroid()` 不检查 installer。

installer 过滤只会缩小候选集合，不会授予 profile 权限。这组约束要求目标来自 system 或 product 分区，但目标仍须通过相应的 profileable 判定：

```textproto
target_installed_by: "@system"
target_installed_by: "@product"
```

这两行适合平台采集策略用来限制目标来源。把它们加入 shell 配置，仍无法采集未开放 shell profiling 的应用。

### Manifest 应怎样声明

面向本地 shell 工具采集 release 构建时，最小声明如下：

```xml
<application
    ...>
    <profileable android:shell="true" />
</application>
```

`android:enabled` 默认是 `true`，通常不用重复写。设为 `false` 会禁止系统服务和 shell profiler。`android:shell="true"` 允许 shell 工具读取 profiling 所需的调用栈信息，不会把任意堆字节开放给第三方 App。

发布策略要根据产品威胁模型决定；威胁模型用于列出需要保护的数据、可能的攻击者和允许的访问方式。调用栈、模块路径、Build ID（二进制文件的唯一构建标识）、线程名和进程名仍可能暴露实现信息。应用若不接受终端用户通过本地调试工具采集 release 版本，应保留 `android:shell="false"`，由受信系统组件执行线上采集。

`ProfilingManager` 不要求 `android:shell="true"`。平台服务 profiling 默认允许，应用可通过 `<profileable android:enabled="false" />` 明确退出；退出后，shell 与平台服务都不能采集。Android 15–17 的普通应用若要采自己的生产 profile，应优先使用 `ProfilingManager`，不必为了远程采集向设备 shell 开放 release APK。

可以通过包管理器输出核对最终 APK 的合并结果。这组命令查看设备侧 package 信息：

```bash
adb shell dumpsys package com.example.app |
  rg -i 'profileable|debuggable'
```

输出字段会随系统版本和 OEM 改动而变化。是否可采还要用一次短会话验证，单个 `dumpsys` 字段不足以代表完整权限判定。

### daemon、SELinux 与能力边界

Android 17 的 `heapprofd.rc` 把服务定义为 disabled，由 `traced.lazy.heapprofd=1` 或持久属性按需启动。服务以 `nobody` 用户运行，加入 `nobody` 和 `readproc` 组，并声明 `KILL`、`DAC_READ_SEARCH` capability。capability 是把 root 权限拆成较小能力单元的 Linux 机制。

SELinux 会按安全策略限制进程可执行的操作。同一份 rc 文件明确说明：SELinux 在 user build 上拒绝 `DAC_READ_SEARCH` 对应权限，userdebug/eng 才允许这部分访问。因此，rc 中出现 capability 不能推出生产设备可任意读取 `/proc/<pid>/mem`。

`/dev/socket/heapprofd` 的 socket mode 只控制文件系统层面的连接条件，无法单独证明调用者已获采集授权。连接建立后，producer 会读取 peer UID（连接对端的 UID）、目标 UID 和 `packages.list`，再执行 `CanProfile()`。文件 mode、Linux capability、SELinux 和 Perfetto 会话身份共同构成权限边界。

### native 进程名按规范化结果精确匹配

`process_cmdline` 是 `HeapprofdConfig` 用来指定目标进程命令行名称的字段。Android 17 的 native producer 会先规范化名称，再做精确匹配：

- 路径只保留末尾 `/` 后面的程序名；
- 第一个 `@` 后的版本后缀被去掉；
- 比较对象是 `/proc/<pid>/cmdline` 的第一个参数。

glob 是用 `*` 等符号描述一组名称的模式。`com.example.app*` 不会匹配 `com.example.app:remote`。Java HPROF producer 使用支持 glob 的 matcher；该规则只属于 `android.java_hprof`，不能套用到 native heapprofd。

多进程 App 要逐个填写完整进程名。这个片段同时选择主进程和 remote 进程：

```textproto
process_cmdline: "com.example.app"
process_cmdline: "com.example.app:remote"
```

heapprofd 会分别为匹配到的 PID 建立记录。`upid` 是 trace processor 为一次进程生命周期分配的唯一进程 ID，可以避免系统 PID 被复用后的混淆。分析时应按 `upid` 区分进程，不能把两个进程的分配直接相加后归到主进程。

### 三种采集入口

#### Android 15–17 使用 `ProfilingManager`

API 35 起，普通应用可以请求自己的 native heap profile，也就是按调用栈抽样记录 native 分配与释放。Android 官方建议通过 AndroidX `HeapProfileRequestBuilder` 构造参数。系统会限制时长、buffer、采样间隔和请求频率；请求被接受只表示系统开始尝试采集，不保证一定生成结果文件。

这段 Kotlin 代码用于启动 native allocation profile，并把停止时机交给调用方：

```kotlin
@RequiresApi(35)
fun requestNativeHeapProfile(
    context: Context,
    executor: Executor,
    listener: Consumer<ProfilingResult>,
): CancellationSignal {
    val stopSignal = CancellationSignal()
    val request = HeapProfileRequestBuilder()
        .setTrackJavaAllocations(false)
        .setTag("native-heap")
        .setCancellationSignal(stopSignal)
        .build()

    requestProfiling(context, request, executor, listener)
    return stopSignal
}
```

调用方应在目标场景前发起请求，并在场景结束后执行 `stopSignal.cancel()`。`CancellationSignal` 在这里用于提前结束采集。成功结果的 `ProfilingResult.getResultFilePath()` 指向应用 files 目录；失败时应同时记录 `getErrorCode()` 和 `getErrorMessage()`，以区分参数错误、并发冲突、进程级限流和系统级限流。

Binder 是 Android 的跨进程调用机制，服务端可从请求中取得真实调用 UID。Android 17 的 Profiling 模块会校验该 UID 与包名，然后把包名写入 `HeapprofdConfig.process_cmdline`。

应用无法借此采集其他包，`:remote` 等次要进程也不会自动加入。

`setTrackJavaAllocations(true)` 会把采样对象从 native 分配改为 `com.android.art` Java 分配，记录 Java 分配调用栈和大小。这种 allocation profile 不含对象引用关系，与 Java heap dump 提供的证据不同。

trace redactor 会按策略删除或改写跟踪文件中的敏感字段。系统 trace 会经过通用 redactor；`android-17.0.0_r1` 的 `ProfilingService.needsRedaction()` 没有把 heap profile 列入该流程。heap profile 依靠目标包限制来隔离其他应用数据，但返回文件中的本应用调用栈、映射与地址仍属于敏感诊断数据。

#### 使用官方 `tools/heap_profile`

本地开发、QA 和问题复现应优先使用与目标平台版本接近的 Perfetto 工具。这个命令采集 120 秒，每 30 秒形成一个 dump，采样间隔为 4 KiB：

```bash
python3 tools/heap_profile android \
  -n com.example.app \
  -i 4096 \
  -d 120000 \
  -c 30000
```

Android 17 tag 中脚本的默认采样间隔为 4096 bytes，共享内存默认为 8 MiB。

命令结束后会生成 raw trace，并可进一步导出 pprof 产物。pprof 是按调用栈聚合 profile 的通用格式；raw trace 保留 Perfetto 会话数据，可直接在 Perfetto UI 中打开。

对交互延迟敏感的量产场景，应考虑加 `--no-block-client`。官方脚本默认在共享 buffer 满时让目标进程等待可用空间，这能保留更多数据，也可能拉长分配操作。禁用阻塞后，buffer overrun（写入速度超过缓冲区消费速度）会提前结束该进程的 profile，因此分析前必须检查错误标志。

#### 手写 Perfetto textproto

textproto 是 Protocol Buffers 的可读文本格式。需要把 heap profile 与调度、进程内存或业务 marker（标记操作起止位置的 trace 事件）放进同一会话时，可以直接配置 `android.heapprofd`。

这个两分钟示例沿用官方脚本的采样间隔、dump 周期和共享 buffer 默认值，并附带 process stats：

```textproto
buffers {
  size_kb: 63488
  fill_policy: RING_BUFFER
}

data_sources {
  config {
    name: "android.heapprofd"
    target_buffer: 0
    heapprofd_config {
      process_cmdline: "com.example.app"
      sampling_interval_bytes: 4096
      shmem_size_bytes: 8388608
      continuous_dump_config {
        dump_phase_ms: 30000
        dump_interval_ms: 30000
      }
    }
  }
}

data_sources {
  config {
    name: "linux.process_stats"
    target_buffer: 0
    process_stats_config {
      scan_all_processes_on_start: true
      proc_stats_poll_ms: 5000
    }
  }
}

duration_ms: 120000
write_into_file: true
flush_timeout_ms: 30000
```

这份配置用周期 dump 观察仍未释放分配的变化，并用 process stats 提供 RSS 侧背景。RSS（Resident Set Size）表示进程当前驻留在物理内存中的页面总量。

guardrail 是超过资源阈值就停止采集的保护条件。示例没有填写 `max_heapprofd_memory_kb` 和 `max_heapprofd_cpu_secs`，因为这两个 guardrail 没有跨设备通用值。

量产配置应先测量 daemon 基线，再设置并验证阈值。

这组命令把配置送入设备侧 Perfetto，并拉回 trace：

```bash
adb push heapprofd.pbtxt /data/local/tmp/heapprofd.pbtxt
adb shell perfetto --txt \
  -c /data/local/tmp/heapprofd.pbtxt \
  -o /data/misc/perfetto-traces/heapprofd.pftrace
adb pull /data/misc/perfetto-traces/heapprofd.pftrace
```

`perfetto` 会运行到 `duration_ms` 结束。若目标不满足 profileable 条件，trace 仍可能生成，却不包含该进程的 heap profile；此时应同步检查 heapprofd 日志与 trace 中的 profile 错误。

### 参数怎样影响开销和证据质量

Android 17 的 `HeapprofdConfig` 已经把资源控制项写进 proto。配置阈值前，要先确认它限制的是目标进程、heapprofd daemon 还是 trace 输出：

| 参数 | Android 17 语义 | 调整方向 |
|---|---|---|
| `sampling_interval_bytes` | 平均每分配 N bytes 记录一个样本；1 表示逐次记录 | 数值增大可降低开销，也更容易漏掉小分配 |
| `shmem_size_bytes` | 目标进程与 daemon 之间的共享 buffer；默认 8 MiB，最大 500 MiB | 突发分配多时可增大 |
| `block_client` | buffer 满时是否让目标进程等待 | 线上测量通常关闭，复现实验可按数据完整性决定 |
| `max_heapprofd_memory_kb` | heapprofd 的 `RssAnon + VmSwap` 上限 | 防止 daemon 自身占用失控 |
| `max_heapprofd_cpu_secs` | 当前 data source 启动后 daemon 累计 CPU 秒上限 | 限制 unwinding 消耗 |
| `continuous_dump_config` | 第一次 dump 延迟与后续 dump 周期 | 用于比较仍未释放分配的趋势 |
| `min_anonymous_memory_kb` | 过滤匿名 RSS 与 swap 低于阈值的进程 | 全局或多目标采集时减少噪声 |
| `no_running` / `no_startup` | 只采新进程或只采已运行进程 | 按启动问题或运行期问题选择 |

`RssAnon` 是匿名内存中驻留在 RAM 的部分，`VmSwap` 是被换出的内存；两者相加用于约束 heapprofd 自身内存。

memory 和 CPU guardrail 每 30 秒检查一次。阈值触发后，producer 会关闭对应 data source，不会自动增大 sampling interval。

需要自适应采样时，应显式使用 `adaptive_sampling_shmem_threshold` 和 `adaptive_sampling_max_sampling_interval_bytes`。

固定的“CPU 增加 1%”或“daemon RSS 80 MB”不能作为跨设备结论。开销会受分配速率、采样间隔、调用栈深度、ABI、符号信息、目标进程数和 CPU 性能影响。ABI 规定二进制代码的调用约定和数据布局，例如 `arm64-v8a`。可靠做法是在相同操作序列下，分别测量无采集、目标采样间隔和更大间隔三组数据。

### 采集主体与部署位置

#### Android 15–17 普通 App 请求自己的 profile

`ProfilingManager` 是应用在公开用户设备上请求自身 heap profile 的标准入口。它不要求 adb，也不会把 trusted-system 身份交给应用。系统服务施加这些约束：

- Binder 调用 UID 必须与请求包名对应；
- 配置目标固定为调用方包名；
- 请求同时受单应用与全系统限流；
- DeviceConfig（系统服务可动态读取的一组配置项）可以限制参数范围或关闭 profile 类型；
- 结果复制到应用目录，由应用负责上传和删除。

这条路径适合少量、按场景触发的线上取证。它的可配置范围小于手写 Perfetto config，无法选择其他进程名、installer 过滤、连续 dump 或自定义 heapprofd guardrail。

#### QA 在 user build 上采 release APK

第三方应用最容易复现的方式是让 QA 在 user build 上通过 shell 采集：

1. release APK 声明 `android:shell="true"`；
2. 测试设备保持 user build；
3. QA 通过 adb、Perfetto UI 或 `tools/heap_profile` 发起会话；
4. trace 离开设备前按内部数据策略处理。

这条路径同时覆盖 release 优化和 user-build 权限，适合灰度前问题复现。它仍依赖本地调试通道，不代表 App 能在用户手机上自行启动系统采集。

#### 平台拥有受信采集组件

OEM 或系统产品可以让受信系统服务按设备健康信号发起 Perfetto 会话。目标 App 只需 enabled profileable，是否向 shell 开放由产品策略决定。采集服务还应负责：

- 目标包和 installer 允许名单；
- 采样窗口、次数与资源预算；
- 充电、温度、前后台和低内存条件；
- trace 存储、上传、访问审计与过期删除；
- Build ID、版本号和符号文件映射。

受信发起者身份来自系统集成，普通 APK 无法模拟。设备管理权限或远程配置本身也不会自动获得该身份。

#### Android 12–14 的普通 App 无法自主启动系统级 heapprofd

Android 12–14 的普通 App 没有 `ProfilingManager`，也没有公开 API 可以把自己声明为 trusted-system 会话。

若产品必须在这些版本的终端用户设备上由 App 自主触发，只能改用应用内 allocator instrumentation（在分配器调用处自行记录）、SDK 自带 native hook、GWP-ASan 或轻量内存指标，并单独评估兼容性、性能和隐私。

若想用 `onTrimMemory()`、PSS 阈值或 `ApplicationExitInfo` 触发 heapprofd，必须先确认设备上存在有权执行采集的系统主体。Android 15–17 可以请求 `ProfilingManager`，但仍受限流和并发会话约束。更低版本中的事件信号只能决定何时记录应用内证据，无法增加 Perfetto 系统权限。

### 如何判断 native heap 是否持续增长

单个 dump 只是某一时刻的采样账目，展示此前记录且尚未释放的分配。判断泄漏至少需要两个连续 dump、可重复的操作序列，以及场景结束后用于观察是否回落的稳定窗口。

推荐记录这些关联信息：

- 包名、PID、`upid`、进程启动时间与版本号；
- 采样间隔、dump 周期、是否命中 guardrail；
- 业务动作的起止 marker 和重复次数；
- 每个 dump 中由样本折算出的存活字节数（sampled bytes）；
- 同期 RSS、PSS、anon RSS、swap 和 mmap 变化；
- trace 是否出现 buffer overrun、unwinding error，或目标进程因权限判定被拒。

anon RSS 是匿名映射当前驻留在 RAM 的大小，swap 是已换出到交换空间的大小。`heap_profile_allocation` 中的正数表示分配，负数表示已经释放的样本。callsite 是把一次分配归因到的调用栈位置；这段 SQL 按 dump、进程、heap 和 callsite 汇总净存活量：

```sql
SELECT
  ts,
  upid,
  heap_name,
  callsite_id,
  SUM(size) AS net_live_bytes,
  SUM(count) AS net_live_count
FROM heap_profile_allocation
GROUP BY ts, upid, heap_name, callsite_id
HAVING SUM(size) > 0
ORDER BY ts, net_live_bytes DESC;
```

查询结果仍是采样估计。相同调用栈跨 dump 增长、场景退出后不回落，并且多轮复现一致，才构成较强的泄漏线索。

flamegraph（火焰图）用矩形宽度表示聚合量，可沿父子调用关系查看完整栈。调用栈展开与符号化可交给 Perfetto UI flamegraph 或命令行转换工具 `traceconv`。

只连接 leaf frame（栈最末端函数）的 SQL 无法还原完整调用栈。

#### 三类常见误判

1. **attach 之前的存量缺失**：attach 指采集器接入已经运行的进程。旧分配没有对应事件，所以运行期采集的第一次 dump 无法代表完整 native heap；
2. **分配器缓存仍保留页面**：应用已经 free，分配器仍可能保留 arena 或 page。arena 是分配器管理的一组内存区域，page 是操作系统映射和回收内存的基本页单位；此时仍存活分配的估算字节数已回落，RSS 仍可能不变；
3. **增长来自 `mmap` 或图形内存**：PSS 上升而 heapprofd 平稳时，应转查 anonymous mapping（匿名内存映射）、文件 mapping、DMA-BUF 与 GPU 内存。

heapprofd 证据与 PSS 证据应并排解释。两者趋势一致时，可把调用栈作为主要线索；趋势分离时，应先确定增长所在的内存类别。

### 失败场景排查

#### `ProfilingManager` 请求被拒绝

API 35 以上的应用应先检查 `ProfilingResult` 的错误码：

- `ERROR_FAILED_RATE_LIMIT_PROCESS` 表示调用应用的小时、天或周预算已经用完；
- `ERROR_FAILED_RATE_LIMIT_SYSTEM` 表示整台设备的共享预算已经用完；
- `ERROR_FAILED_PROFILING_IN_PROGRESS` 表示已有不兼容的 profiling 会话；
- `ERROR_FAILED_INVALID_REQUEST` 常见于参数越界、未知参数或 profile 类型被关闭。

命中限流后立即重试通常仍会失败。应用应记录错误分类，并等待下一次有诊断价值的场景。listener 是接收异步结果的回调；若进程在采集期间退出，系统会停止并保存已有结果，应用下次启动并注册全局 listener 后才有机会收到补发通知。

#### 手写 Perfetto 会话没有生成 profile

按以下顺序检查：

1. 设备是否为 Android 10 或更新版本；
2. 最终 APK 是否 debuggable，或 `<profileable android:shell="true">` 是否生效；
3. `process_cmdline` 是否与 `adb shell ps -A` 的 NAME 精确一致；
4. 目标是普通 App、SDK sandbox、isolated process 还是平台 UID；
5. 配置是否误用了 `no_running` 或 `no_startup`；
6. `sampling_interval_bytes` 是否为非零值；
7. heapprofd 和 traced 日志是否报告 `not profileable`（目标不可采）、signal 失败或 client 连接失败。

#### profile 提前结束

共享 buffer 跟不上分配速率时，目标进程内的 heapprofd client 会出现 buffer overrun。可以增大 sampling interval 或 `shmem_size_bytes`，也可以在可控实验中启用 `block_client`。线上场景不应为了保住 trace 而无条件阻塞高频分配线程。

memory 或 CPU guardrail 命中也会关闭 data source。检查阈值时要区分 daemon 总开销和目标进程开销；`max_heapprofd_memory_kb` 不限制目标 App 的 native heap。

#### 栈缺帧或符号缺失

常见原因包括缺少 Build ID 对应符号、栈展开信息被裁剪、JIT/AOT frame 缺少可用元数据、相同代码折叠，以及 trace 与符号包版本不一致。JIT 是运行时即时编译，AOT 是安装或构建阶段的提前编译，frame 表示调用栈中的一层函数记录。

相同代码折叠是编译器或链接器把内容相同的函数实现合并到同一地址；它会让一个地址对应多个候选符号。

符号化是把程序地址还原成函数名和源码位置。build fingerprint 是标识一套系统构建的字符串。

符号服务应以 APK version、ABI、Build ID 和系统 build fingerprint 定位文件；只按 so 文件名匹配容易拿错版本。

### 与其他工具的职责分工

UAF（use-after-free）是释放内存后继续访问，double free 是同一块内存被重复释放。reachability 检查会从已知根指针出发寻找仍能访问的内存，找不到路径的分配会被标为不可达。

| 工具 | 主要证据 | 适用问题 | 主要限制 |
|---|---|---|---|
| heapprofd | 采样的分配/释放调用栈 | native heap 增长来源 | 不覆盖全部 mmap、图形内存和会话前存量 |
| Perfetto process stats / meminfo | RSS、PSS、内存类别 | 进程总量和类别变化 | 没有 malloc callsite |
| GWP-ASan | 被采样分配的 UAF、double free、越界 | native 内存安全错误 | 不负责统计泄漏增长 |
| `libmemunreachable` | 某时刻的不可达 native 分配 | 平台调试中的 reachability 快照 | 平台内部接口、暂停与权限成本 |
| malloc debug | allocator 检查、回溯与泄漏信息 | 可控 debug 环境 | 开销高，发布环境受限 |
| 应用内 native hook | App 自己定义的事件和调用栈 | 无系统采集权限的长期监控 | 兼容 allocator、递归、信号安全和版本维护成本高 |

`libmemunreachable` 不属于稳定 NDK API。通过 `dlopen` 加载私有系统库并硬编码 C++ 符号，会受到 linker namespace、符号变化和 SELinux 限制。linker namespace 用来规定一个进程能加载哪些 native 库，因此这类调用不适合作为通用量产方案。

Scudo 是强调内存安全检查的 native 分配器。它的 error callback 只报告分配器发现的错误，不能充当通用 allocation 事件回调。

需要记录自定义 named heap 时，Perfetto 提供 `AHeapProfile_registerHeap` 一类注册接口；接入前仍要确认目标平台提供的头文件、ABI 和集成方式。

### 数据安全与归档

heapprofd 不复制任意 heap payload（堆中对象或缓冲区的原始内容），但 trace 仍可能包含：

- 进程名、线程名与 UID 关联；
- 映射路径、模块名、Build ID 和地址；
- native 与可展开的 Java 调用栈；
- trace 中同时开启的其他 data source 数据。

线上采集策略应把完整 trace 当作诊断数据管理。建议只启用必要的 data source，限制目标包和时长，在设备侧加密存储，为上传通道做身份校验，服务端按角色授权，并设置明确的删除期限。

符号化宜在受控环境中按 Build ID 完成。只上传 `heap_profile_allocation` 表会丢失完整调用栈、错误标志和会话关联信息，不能视为默认的“脱敏等价物”。

若要裁剪，应定义可复现的 trace-to-report（从 trace 转换为摘要报告）格式，并保留采样参数、版本和错误元数据。

### 发布前检查表

- [ ] 源码与配置以 `android-17.0.0_r1` 为基准；
- [ ] release APK 的 profileable 合并结果已在 user build 验证；
- [ ] shell 会话和 trusted-system 会话的权限主体没有混写；
- [ ] Android 15–17 的普通 App 优先使用 `ProfilingManager`，并处理限流与结果文件；
- [ ] 所有 native 进程名均为精确值，没有使用 `*`；
- [ ] sampling interval、shmem、dump 周期和 guardrail 有设备基线；
- [ ] 线上配置不会因 `block_client` 放大业务延迟；
- [ ] trace 中检查了 rejected、buffer overrun、unwinding 和 guardrail 状态；
- [ ] 泄漏判断使用连续 dump、稳定窗口和重复操作序列；
- [ ] heapprofd 与 PSS、mmap、DMA-BUF 等口径分开解释；
- [ ] 原始 trace、符号文件和分析结果有访问与删除策略。


## procfs CPU 计数器与采样窗口

内存分配采样回答谁在申请内存，procfs CPU 统计回答进程和线程在窗口内消耗多少 CPU。累计值必须通过相邻样本求差。

### CPU 使用率的三种口径

Android 上的“CPU 使用率”至少有三种口径：

- 系统在采样窗口内有多少 CPU 容量处于忙碌状态；
- 某个进程在采样窗口内消耗了多少个“核等价”的 CPU 时间；
- 某个线程何时被调度、在哪个 CPU 上运行，以及等待运行队列多久。

核等价把一个逻辑 CPU 在整个采样窗口内满负荷运行定义为 100%；多线程进程因此可以超过 100%。运行队列保存已经可以运行、正在等待 CPU 的线程，调度事件则记录线程何时进入或离开 CPU。

这三类问题分别适合用 `/proc/stat`、进程 CPU 时间和调度事件回答。load average 衡量一段时间内活跃任务的平均数量，与 CPU 利用率采用不同口径。混成一个百分比后，单核占满可能被误报成整机占满，load average 也可能被错当成利用率。

`ProcessCpuTracker` 是 Android 系统框架内部的全进程 CPU 采样类。`system_server` 是承载多数 Android 系统服务的核心进程。普通应用无法照搬它使用 `ProcessCpuTracker` 的方案，因此需要先区分应用侧与平台侧权限。

平台源码以 AOSP `android-17.0.0_r1` 为准，内核源码以最新 Android Common Kernel `android17-6.18-2026-06_r39` 为准。页面保留的 6 条 r6 内核链接用于历史追溯；对应文件与 r39 字节一致，相关结论按 r39 复核。

### procfs 提供动态内核接口

`procfs` 是内核提供的虚拟文件系统。PID（process ID）是系统分配给进程的数字标识。procfs 的内容不来自磁盘快照；读取 `/proc/stat`、`/proc/<pid>/stat` 等节点时，内核会按节点实现即时生成文本。有些节点也允许写入，用来调整内核参数。

使用它时需要记住四个边界：

- `st_size` 是文件元数据中声明的长度。procfs 节点的该值可能为零，也可能提供其他值，不能用“所有文件大小都为零”判断内容是否存在。
- 一次读取看到的是生成过程中的内核状态。多个节点之间没有事务；原子采样要求相关值在同一不可分割操作中取得，procfs 不提供这种保证。
- 进程可能在 `open()`、`read()` 之间退出，PID 还可能被复用。跨时刻跟踪进程时，应同时校验 `/proc/<pid>/stat` 的 `starttime`。
- `seq_file` 是内核逐段生成较长文本节点的辅助接口。节点是否支持 `lseek()` 定位由具体实现决定，业务代码不应套用统一假设。

因此，可靠的采样器应给每次样本附加单调时钟时间戳，允许单个节点读取失败，并在计数回退、进程实例变化或字段不足时丢弃本轮差值。

内核接口与挂载选项可在 [`Documentation/filesystems/proc.rst`](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/Documentation/filesystems/proc.rst) 中核对。

### Android 17 的访问边界

#### 普通应用不能读取全局 CPU 节点

UID（user ID）是 Android 用来区分应用与系统主体的数字身份。AOSP Android 17 的 `app_neverallows.te` 使用 neverallow 规则，明确禁止所有普通应用域读取 `proc_stat` 和 `proc_loadavg`。neverallow 是 SELinux 在策略编译阶段强制检查的禁止项。该规则覆盖不同 `targetSdk` 对应的 `untrusted_app_*` 域，因此降低 `targetSdk` 也无法恢复 `/proc/stat`。

`untrusted_app_all.te` 还保留了从 Android O 开始对 `proc_stat` 读取拒绝的 `dontaudit` 处理。`dontaudit` 只抑制审计日志，不会授予权限；应用读取失败时，设备日志中未必出现醒目的 SELinux denial（拒绝审计记录）。

Android 的 `/proc` 还使用 `hidepid=2` 隐藏其他 UID 的进程目录。first-stage init 是系统启动时最早运行的 init 阶段；Android 17 在该阶段以 `gid=AID_READPROC` 挂载 procfs。获得 `AID_READPROC` 组的受信进程可按策略读取更多目录。

普通应用只能稳定依赖自身数据，其他 PID 是否可见不属于 SDK 保证。Android 10 的公开隐私变更针对 `/proc/net`，并影响设备上的所有应用；整个 `/proc/<pid>` 的隔离不能归因于 Android 10 按 `targetSdk` 新增的一条开关。

| 调用方 | Android 17 上适合依赖的数据 | 不应依赖的数据 |
|---|---|---|
| 普通应用或 APM（Application Performance Monitoring，应用性能监控）SDK | `Process.getElapsedCpuTime()`、`/proc/self/stat`、自身可见的 `task` 节点 | `/proc/stat`、`/proc/loadavg`、全系统 PID 遍历 |
| 具有专用 SELinux 规则的平台服务 | 策略允许的全局节点与进程节点 | 仅凭“预装”或“平台签名”推定访问权 |
| `shell`、root、系统 tracing 服务 | Perfetto、受控的 procfs/ftrace/BPF 采集 | 把调试权限当作线上应用权限 |

厂商策略可以比 AOSP 更严格。采集器应把节点访问视为可能失败的能力，品牌或系统版本不能替代运行时验证。

对应证据包括：

- [`app_neverallows.te` 的 procfs 禁止规则](https://android.googlesource.com/platform/system/sepolicy/+/refs/tags/android-17.0.0_r1/private/app_neverallows.te)
- [`untrusted_app_all.te` 的历史兼容说明](https://android.googlesource.com/platform/system/sepolicy/+/refs/tags/android-17.0.0_r1/private/untrusted_app_all.te)
- [`first_stage_init.cpp` 的 procfs 挂载参数](https://android.googlesource.com/platform/system/core/+/refs/tags/android-17.0.0_r1/init/first_stage_init.cpp)
- [Android 10 对 `/proc/net` 的公开说明](https://developer.android.com/about/versions/10/privacy/changes#restriction-access-proc-net)

### `/proc/stat`：全机 CPU 容量口径

possible CPU 是内核可能管理的逻辑 CPU 集合，其中可以包含当前离线成员；online CPU 则是此刻参与调度的子集。平台进程读取 `/proc/stat` 时，首行汇总所有 possible CPU 的累计值，后续 `cpu0`、`cpu1` 等行只列出 online CPU。首行字段顺序为：

```text
cpu  user nice system idle iowait irq softirq steal guest guest_nice
```

这些数值自启动以来累计，单位为 `USER_HZ`。`USER_HZ` 是用户空间读取内核 CPU 计数时使用的每秒 tick 数；不能把它写死为 100。Android 17 的 `ProcessCpuTracker` 通过 `Os.sysconf(OsConstants._SC_CLK_TCK)` 获取换算系数。

各字段的含义如下：

| 字段 | 含义 |
|---|---|
| `user` | 普通优先级任务在用户态运行的时间 |
| `nice` | `nice > 0` 的低优先级任务在用户态运行的时间 |
| `system` | 任务在内核态运行的时间 |
| `idle` | CPU 空闲时间 |
| `iowait` | 内核归入等待 I/O 的空闲时间 |
| `irq` | 处理硬中断的时间 |
| `softirq` | 处理软中断的时间 |
| `steal` | 虚拟化环境中被宿主占用的时间 |
| `guest` | 运行普通优先级虚拟 CPU 的时间，已经计入 `user` |
| `guest_nice` | 运行低优先级虚拟 CPU 的时间，已经计入 `nice` |

`guest` 和 `guest_nice` 是细分项，不能再次加进总时间。Android 17 内核的 `account_guest_time()` 同时更新 `user`/`nice` 与对应的 guest 计数，这一包含关系可在 [`kernel/sched/cputime.c`](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/kernel/sched/cputime.c) 中看到。

若产品要计算本机任务消耗的 CPU 时间，可以采用下列定义：

- `total = user + nice + system + idle + iowait + irq + softirq + steal`
- `localBusy = user + nice + system + irq + softirq`
- `localBusyPercent = ΔlocalBusy / Δtotal × 100%`

`steal` 表示虚拟机等待宿主提供 CPU 的时间，不计入本机任务执行时间。若指标要表达“对虚拟机不可用的 CPU 容量”，可以把 `steal` 加入分子，但应使用不同名称。`guest` 和 `guest_nice` 仍不能重复相加。

`cpu` 首行汇总多个 CPU。假设八个 CPU 在一个窗口内都保持在线，一个进程只占满其中一个 CPU，`Δprocess / Δtotal` 会接近整机容量的八分之一。若先把该结果称为“单核百分比”，随后再除一次 CPU 数，就会重复归一化。

还要注意：

- 内核文档明确指出 `iowait` 在多核和 NO_HZ 场景下并不可靠，某些条件下甚至会回退。NO_HZ 是空闲时减少或停止周期时钟 tick 的内核模式。计数回退时应丢弃样本，不能用零替代负差值。
- CPU hotplug（热插拔）会改变在线 CPU 集合。固定核数无法可靠补偿 `/proc/stat` 的聚合差值。
- CPU 时间没有表达核心微架构、频率和调度容量。调度容量是内核对不同 CPU 相对处理能力的归一化表示；同样一毫秒在小核与大核上不代表相同工作量或能耗。

Android 17 对应实现位于 [`fs/proc/stat.c`](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/fs/proc/stat.c)。该文件还输出：

- `ctxt`：全机累计 `context switch`（任务切换）次数，即 CPU 从一个线程切换到另一个线程的累计次数；
- `btime`：启动时间的 Unix 时间戳；
- `processes`：创建过的进程和线程数量；
- `procs_running`：正在运行或可运行的线程数量；
- `procs_blocked`：等待 I/O 的阻塞任务数量。

这些值适合补充描述系统压力，但不能替代调度 trace。

### 两种进程 CPU 百分比不要混用

`/proc/<pid>/stat` 的第 14、15 个字段分别是 `utime` 和 `stime`，两者相加得到进程累计 CPU 时间。对两次样本做差后，可以定义两种常见口径。

#### 核等价利用率

`ΔprocessCpu / Δwall × 100%` 表示进程用了多少个核：

- 100% 表示窗口内约占用一个 CPU；
- 150% 表示平均约占用 1.5 个 CPU；
- 多线程进程可以超过 100%。

这是应用性能监控中更直观的口径。它不需要 `/proc/stat`，普通应用可以用公开 API [`Process.getElapsedCpuTime()`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/os/Process.java) 获取当前进程累计 CPU 毫秒数。

这段 Kotlin 示例同时保留“设备唤醒期间”和“完整观察窗口”两个分母，避免睡眠时间是否计入指标变成隐含条件：

```kotlin
import android.os.Process
import android.os.SystemClock

data class CpuPoint(
    val processCpuMs: Long,
    val uptimeMs: Long,
    val realtimeMs: Long,
)

data class CpuUsage(
    val awakeCorePercent: Double,
    val windowCorePercent: Double,
)

class SelfCpuSampler {
    private var previous: CpuPoint? = null

    fun sample(): CpuUsage? {
        val current = CpuPoint(
            processCpuMs = Process.getElapsedCpuTime(),
            uptimeMs = SystemClock.uptimeMillis(),
            realtimeMs = SystemClock.elapsedRealtime(),
        )
        val old = previous
        previous = current
        if (old == null) return null

        val cpuDelta = current.processCpuMs - old.processCpuMs
        val uptimeDelta = current.uptimeMs - old.uptimeMs
        val realtimeDelta = current.realtimeMs - old.realtimeMs
        if (cpuDelta < 0 || uptimeDelta <= 0 || realtimeDelta <= 0) return null

        return CpuUsage(
            awakeCorePercent = cpuDelta * 100.0 / uptimeDelta,
            windowCorePercent = cpuDelta * 100.0 / realtimeDelta,
        )
    }
}
```

`uptimeMillis()` 在深度睡眠期间停止，适合描述设备醒着时的 CPU 密度；`elapsedRealtime()` 包含深度睡眠，适合描述完整观察窗口内的平均负担。这个示例只统计当前进程，不会自动合并应用的 `:remote` 等其他进程。

#### 整机容量占比

`ΔprocessCpu / ΔallCpu × 100%` 表示进程占全机累计 CPU 容量的比例，通常位于 0% 到 100% 之间。它需要全局 CPU 计数，普通应用在 AOSP Android 17 上无法直接计算。

若产品为了跨设备比较而把核等价利用率除以 CPU 数量，必须先定义分母：物理核心、当前在线 CPU、进程 cpuset 允许的 CPU，或者按调度容量加权的 CPU。cpuset 是限制一组进程可以在哪些 CPU 上运行的内核机制。移动设备会热插拔，大小核性能也不同，简单除以 `Runtime.availableProcessors()` 只能得到近似值。

### `/proc/<pid>/stat` 的解析规则

CPU 采集常用字段如下，索引从 1 开始：

| 索引 | 字段 | 说明 |
|---:|---|---|
| 1 | `pid` | 进程或线程 ID |
| 2 | `comm` | 括号包围的任务名，可包含空格和右括号 |
| 3 | `state` | `R` 为运行或可运行，`S` 为可中断睡眠，`D` 为不可中断睡眠，`Z` 为僵尸，`T` 为停止或被跟踪 |
| 14 | `utime` | 用户态累计 CPU 时间，单位为 `USER_HZ` |
| 15 | `stime` | 内核态累计 CPU 时间，单位为 `USER_HZ` |
| 16 | `cutime` | 已等待子进程累计的用户态 CPU 时间 |
| 17 | `cstime` | 已等待子进程累计的内核态 CPU 时间 |
| 20 | `num_threads` | 线程数量 |
| 22 | `starttime` | 任务从系统启动起算的创建时刻，单位为 clock tick；一个 tick 是 `1 / USER_HZ` 秒 |
| 23 | `vsize` | 虚拟地址空间大小，单位为字节 |
| 24 | `rss` | 驻留页数量，需要乘页大小得到字节 |
| 39 | `processor` | 任务上次运行所在的 CPU 编号 |

不能直接按空格切整行，因为 `comm` 可以包含空格和 `)`。应找到整行中最末一个 `)`；其后的第一个 token（由空白分隔的字段）才是字段 3。这段代码只解析 CPU 采集需要的稳定前缀，并保留 `starttime` 用于识别进程实例：

```kotlin
import android.system.Os
import android.system.OsConstants
import java.io.File

data class ProcCpuTicks(
    val cpuTicks: Long,
    val startTicks: Long,
)

private val whitespace = Regex("\\s+")

fun readSelfCpuTicks(): ProcCpuTicks? {
    return try {
        val line = File("/proc/self/stat").readText()
        val closingParen = line.lastIndexOf(')')
        require(closingParen > 0)

        // tail[0] 对应字段 3；utime、stime、starttime 分别对应 11、12、19。
        val tail = line.substring(closingParen + 1).trim().split(whitespace)
        require(tail.size > 19)
        ProcCpuTicks(
            cpuTicks = tail[11].toLong() + tail[12].toLong(),
            startTicks = tail[19].toLong(),
        )
    } catch (_: Exception) {
        null
    }
}

fun clockTicksPerSecond(): Long =
    Os.sysconf(OsConstants._SC_CLK_TCK)
```

解析失败返回 `null`，调用方应丢弃这一轮样本。不要返回 `-1` 后继续计算差值，否则一次权限拒绝或进程退出会产生很大的伪 CPU 峰值。跟踪任意 PID 时，还要在两次样本之间比较 `startTicks`；数值变化说明 PID 已对应另一个进程。

内核可能在末尾追加字段，因此不应断言 `/proc/<pid>/stat` 固定有 44 个字段。按需要解析稳定前缀，比校验总字段数更兼容。Android 17 生成这些字段的代码位于 [`fs/proc/array.c`](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/fs/proc/array.c)。

### 线程级采集

TID 是系统为线程分配的数字 ID。`/proc/<pid>/task/<tid>/stat` 与进程 stat 使用相同字段格式，但 `utime`、`stime` 对应单个线程。对普通应用而言，`/proc/self/task/` 可用于：

- 区分主线程与后台工作线程的 CPU 消耗；
- 查看 Binder 线程是否持续占用 CPU；
- 观察线程数量和线程 CPU 时间是否持续增长；
- 在卡顿前后保留轻量的线程 CPU 快照。

逐线程轮询的成本随线程数增长，并且目录枚举会遇到线程创建、退出的竞争。它适合短时诊断或低频摘要，无法替代调度事件。

Binder 是 Android 的跨进程调用机制。主线程 CPU 较低也不能证明主线程健康：锁等待、Binder 等待和 I/O 阻塞都可能让线程几乎不消耗 CPU，却仍造成卡顿或 ANR（应用无响应）。

### Android 17 `ProcessCpuTracker` 的准确模型

`ProcessCpuTracker` 位于 `com.android.internal.os`，是系统框架内部类，不属于 SDK API。Android 17 源码直接声明 `public class ProcessCpuTracker`；该目录没有它继承的 `CpuTracker` 基类。

它的主要入口与数据结构可以概括为：

```text
ProcessCpuTracker(boolean includeThreads)
  init(): void
  update(): void
  countStats(): int
  getStats(index): Stats
  countWorkingStats(): int
  getWorkingStats(index): Stats
  getCpuTimeForPid(pid): long
  getCpuDelayTimeForPid(pid): long

Stats
  pid, uid, name, baseName
  base_utime, base_stime, base_uptime
  rel_utime, rel_stime, rel_uptime
  rel_minfaults, rel_majfaults
  active, working, added, removed
```

`base_*` 保存累计基线，`rel_*` 保存本轮与基线的差值。minor fault 是无需从存储读取页面即可处理的缺页，major fault 通常需要存储 I/O；`rel_minfaults` 和 `rel_majfaults` 分别记录两类缺页增量。

`update()` 的返回类型为 `void`。Android 17 r1 的类也没有声明 `addCpuTime()`、`getProcessStats()` 或 `getIdleCpuTime()`；完整定义见 [`ProcessCpuTracker.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/com/android/internal/os/ProcessCpuTracker.java)。

一次 `update()` 的流程是：

1. 用 `Process.readProcFile()` 读取 `/proc/stat` 的 `user` 到 `softirq` 七个字段，并按 `_SC_CLK_TCK` 换算为毫秒。
2. 用 `Process.getPids("/proc", ...)` 枚举全部可见进程；它不会只更新预先注册的 PID。
3. 对已有 PID 读取 `/proc/<pid>/stat`，计算 CPU 时间和缺页次数增量。
4. 新 PID 还会读取任务名与 `vsize`；退出的 PID 标记为 `removed` 后从活动列表移除。
5. `includeThreads` 为 `true` 时，在进程 CPU 发生变化后继续扫描其 `task` 目录。
6. 读取 `/proc/loadavg`，在数值变化时调用 `onLoadChanged()`。

`Stats.active` 表示本次 CPU 累计值发生变化；`Stats.working` 表示本轮需要进入工作集合，新发现的进程也可能被标为 working。退出项会短暂设置 `removed` 后从活动列表移除。三者不能互换。

源码虽然保留了“累计计数不能回退”的条件，但 Android 17 r1 写成 `if (true || ...)`，该分支实际总会接受读数。自建采样器遇到负差值时应丢弃样本；这与 `ProcessCpuTracker` 当前行为不同。

#### 同一个类中也存在不同百分比定义

Android 17 先把 `/proc/stat` 的 `user + nice` 合入 `mRelUserTime`。`getTotalCpuPercent()` 再用 `mRelUserTime + system + irq` 作为忙时间，并以该值加 `idle` 作分母；`iowait` 和 `softirq` 都未进入这个方法。

`printCurrentState()` 与 Protocol Buffers（proto）输出在计算总时间时则包含 `iowait` 和 `softirq`。

这属于现有内部实现的语义差异，不应把 `getTotalCpuPercent()` 抄成通用 CPU 公式。使用内部数据时，应直接选取需要的增量字段并在指标协议中记录公式。

#### Framework 为什么能用，应用为什么不能照搬

Android 17 的 `AppProfiler` 在 `system_server` 内持有一个 `ProcessCpuTracker`。源码注释明确说明它会遍历 `/proc`，并要求调用方避免在关键锁路径上持有其锁。

采样结果用于 ANR 等诊断输出、进程 CPU 统计和 BatteryStats 归因。BatteryStats 是系统累计应用耗电归因数据的服务端账本。

同一份采样还用于 phantom process 的 CPU 状态更新。phantom process 是 App 派生、但没有作为常规应用进程由 ActivityManager 完整管理的子进程。

对应调用链可在 [`AppProfiler.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/am/AppProfiler.java) 中核对。

普通应用同时受两层约束：

- 类本身是隐藏 API，反射调用没有兼容性保证；
- 即使设法调用成功，SELinux 与 procfs 挂载权限也不会随反射绕过。

所以第三方 APM 应使用公开 API 采集自身进程 CPU，并把系统级诊断交给 Perfetto、bugreport（系统诊断包）或受控的平台服务。

### `/proc/loadavg` 记录任务负载

Android 17 内核将 load average 定义为 `nr_running + nr_uninterruptible` 的指数衰减平均值。指数衰减会让新样本权重更高，三个结果通常称为 1、5、15 分钟负载。

`nr_running` 包含正在运行或已可运行的任务，`nr_uninterruptible` 包含处于不可中断睡眠的任务，后者通常显示为 D 状态。高负载既可能来自 CPU 竞争，也可能来自等待内核 I/O 的 D 状态任务。

这个示例只用于说明文件布局：

```text
1.23 1.45 1.67 3/1024 12345
```

前三个值是三个时间尺度的负载平均值；`3/1024` 是读取时刻的 runnable（正在运行或等待 CPU）线程数与系统线程总数。末尾值是当前 PID namespace（PID 隔离空间）最近分配的 PID。第四列按线程或任务计数，不能解释成“运行进程数/总进程数”，也不能只统计进程主线程。

不要为所有设备设定固定的 load average 告警线。Android 设备存在 CPU 热插拔、大小核、cpuset 和功耗策略，同一个数值在不同设备和温控状态下含义不同。更稳妥的做法是：

- 与同机型、同场景的历史基线比较；
- 同时查看系统 CPU 忙碌率、`procs_running`、`procs_blocked` 与 PSI；PSI（Pressure Stall Information）记录 CPU、内存或 I/O 资源不足造成的停顿时间；
- 用调度 trace 区分运行队列等待、锁等待和不可中断 I/O；
- 把温控、频率和在线 CPU 集合纳入解释条件。

生成第四列的代码位于 [`fs/proc/loadavg.c`](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/fs/proc/loadavg.c)，负载平均算法位于 [`kernel/sched/loadavg.c`](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/kernel/sched/loadavg.c)。普通应用在 AOSP Android 17 上不能读取该节点。

### 采样器的工程约束

采样间隔没有脱离产品场景的固定答案。短间隔能看见更短的尖峰，也会增加唤醒、文件解析、线程枚举和上报成本。设计时应明确：

- 常态只采当前进程的累计 CPU 时间，异常窗口再临时增加线程维度；
- 不在主线程读取 procfs；Android `StrictMode` 会把这类文件 API 调用归入 disk read 检查，即使内容由内核动态生成，也可能触发策略告警；
- 使用单调时钟，不用 `currentTimeMillis()` 计算采样间隔；
- 记录原始累计值、差值、时间分母和指标口径，服务端不要凭字段名猜公式；
- 对读取失败、差值为负、时间不前进、`starttime` 变化分别计数；
- 通过设备实验测量采集线程 CPU、唤醒次数、分配量与包体影响，再决定频率；
- 后台和温控状态下允许降频或停止，异常触发的高频模式应有持续时间限制。

`ProcessCpuTracker` 自身也说明了全 PID 扫描属于长操作。它缓存已有 `Stats` 和进程名，按 PID 合并新增、存续、退出记录，每轮仍需枚举 `/proc`。

### Perfetto 与 eBPF：何时换成事件数据

#### CPU 调度分析用 `linux.ftrace`

ftrace 是 Linux 内核事件跟踪框架。Perfetto 的 `linux.process_stats` 主要提供进程/线程身份关系，以及按周期采集的内存、`oom_score_adj`（进程被低内存回收的优先级调整值）等数据；它不提供进程 CPU 时间样本。

`linux.ftrace` 中的 `sched_switch` 记录 CPU 从一个线程切换到另一个线程，可还原线程何时运行以及运行多久。`sched_waking` 记录线程被唤醒，可补充唤醒到实际运行之间的调度延迟。

data source 是 Perfetto 会话中可启用的一类跟踪数据。这份配置同时启用两类 data source，使调度事件带有完整的进程和线程名称：

```textproto
data_sources {
  config {
    name: "linux.ftrace"
    ftrace_config {
      ftrace_events: "sched/sched_switch"
      ftrace_events: "sched/sched_waking"
    }
  }
}

data_sources {
  config {
    name: "linux.process_stats"
    process_stats_config {
      scan_all_processes_on_start: true
    }
  }
}
```

`linux.ftrace` 给出 CPU 时间轴，`linux.process_stats` 补充名称和线程归属。若要周期采集进程内存，再显式配置 `proc_stats_poll_ms`；它不应被描述成 CPU 采样频率。可继续阅读 Perfetto 的 [CPU Scheduling events](https://perfetto.dev/docs/data-sources/cpu-scheduling) 与 [Memory counters and events](https://perfetto.dev/docs/data-sources/memory-counters)。

#### eBPF 适用于受信平台组件

eBPF（extended Berkeley Packet Filter）允许经过校验的小程序在内核事件点执行。BPF map 是内核程序与用户空间共享的键值存储。平台团队可以在 `sched_switch` 等事件上运行 BPF 程序，把时间归因到 UID、PID 或 TID，再通过 map 输出聚合结果。

Android BPF loader 会在开机时加载由 Android 构建系统生成并放入系统镜像的 BPF 二进制对象，访问权再由 SELinux 策略约束。

这条路线有三个前提：

- Android 需要由受信任的 loader、固定对象和 SELinux 规则管理 BPF 能力，普通应用不能只靠声明权限获得访问；
- BPF 程序在每次调度切换时执行，事件驱动仍会产生随事件频率增长的成本；
- 读取并清空同一张 map 会与内核侧更新竞争。按 CPU 聚合可减少共享写竞争，双缓冲会轮换两张 map，世代号则标识记录属于哪一轮；这些协议用于避免把读取期间的新数据误删。

`BPF_MAP_LOOKUP_AND_DELETE_ELEM` 是 `bpf()` 系统调用中“读取一个元素并将其删除”的操作命令，map 类型需要另外定义。Android 的 loader、对象编译与固定规则可参考 AOSP 的 [Extend the kernel with eBPF](https://source.android.com/docs/core/architecture/kernel/bpf)。

普通应用性能诊断可以使用由平台管理的 Perfetto 调度数据。设备厂商或系统组件需要长期、定制化聚合时，才有理由维护专用 BPF 方案。

### 排查顺序

遇到 CPU 告警时，可以按问题粒度选择数据：

1. 用 `Process.getElapsedCpuTime()` 判断当前进程是否持续消耗核等价 CPU。
2. 对短时异常读取自身线程 stat，确认 CPU 时间集中在哪些线程。
3. 若线程 CPU 不高但用户仍感到卡顿，转向 Perfetto 检查 runnable 等待、锁、Binder、I/O 与调度抢占。
4. 只有具备平台权限并且问题涉及全机竞争时，才读取 `/proc/stat`、load average 或使用 `ProcessCpuTracker`。
5. 需要长期系统级归因时，再评估平台服务或 BPF 聚合，并单独验证开销与权限模型。

这套顺序让每种数据回答它擅长的问题，也避免普通应用依赖 Android 17 已经关闭的全局 procfs 接口。


## Minor、Major Fault 与页面来源

CPU 或启动异常伴随缺页时，需要继续区分匿名页、文件页、首次映射和存储读取。fault 次数本身不等于阻塞时间。

### 先分清计数与失败结果

Page Fault（缺页异常）是 CPU 访问虚拟地址时，因页表缺项或权限不符而交给内核处理的同步异常。“同步”表示异常由当前指令直接触发；内核补齐映射或向线程发送信号之前，这条指令无法继续。信号是内核向线程或进程报告事件的机制。Page Fault Handler（缺页处理程序）泛指接收异常并尝试修复映射的内核代码。

Linux 的统计结果分为两类成功计数和一类失败结果：

| 指标或结果 | Android 17 / Linux 6.18 中的含义 | 常见原因 |
|---|---|---|
| Minor Fault | 内核成功完成 fault，最终未带 `VM_FAULT_MAJOR`，处理过程也未发生重试 | 匿名页按需分配、写时复制（COW）、页缓存已有数据但进程页表项（PTE）尚未建立 |
| Major Fault | 内核成功完成 fault，最终带 `VM_FAULT_MAJOR`，或处理过程发生过重试 | 文件页需要读入、交换页需要从 zRAM（内存压缩块设备）或后备存储取回 |
| 失败访问 | 内核不能为该访问建立合法映射，通常向线程发送 SIGSEGV 或 SIGBUS | 地址未映射、权限不符、文件映射越过 EOF、硬件内存错误 |

“Invalid Page Fault”可用于口头描述失败访问；`/proc/<pid>/stat` 并没有与 minor、major 并列的第三个同名计数器。`min_flt + maj_flt` 只覆盖成功完成的 fault，native crash 需要另行统计。

页表项（Page Table Entry，PTE）记录虚拟页到物理页的映射与访问权限。转译后备缓冲区（Translation Lookaside Buffer，TLB）是 CPU 保存近期地址转换结果的硬件高速缓冲。PTE 有效而转换结果未命中 TLB 时，硬件执行 `page-table walk`（逐级查页表）后即可继续；这类 TLB miss 通常不会进入内核的 Page Fault Handler，应与 Page Fault 分开分析。

### Android 17 arm64 的处理路径

本文保留 `android-17.0.0_r1` 平台源码和 `android17-6.18-2026-06_r6` 内核源码作为历史核验锚点。arm64 的入口在 [`arch/arm64/mm/fault.c`](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/arch/arm64/mm/fault.c)，通用内存管理在 [`mm/memory.c`](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/mm/memory.c)。

截至 2026-08-15，同系列最新标签是 `android17-6.18-2026-06_r39`。两版的 `fault.c` 字节一致；`mm/memory.c` 其他位置虽有改动，`mm_account_fault()` 的函数体保持一致。图中的 ESR（Exception Syndrome Register，异常综合寄存器）记录异常原因，VMA（Virtual Memory Area，虚拟内存区域）记录一段连续地址的权限和后备对象。调用关系只用于定位职责，每次 fault 会按原因选择其中一条分支。

```text
do_mem_abort()
  └─ fault_info[] 按 ESR 分发
      ├─ do_translation_fault() ── 用户地址 ─┐
      └─ do_page_fault()                     │
                                             ▼
             校验访问类型、VMA 与权限
                       │
                       ▼
               handle_mm_fault()
                       │
                       ▼
              __handle_mm_fault()
                 ├─ do_anonymous_page()
                 ├─ do_wp_page()
                 ├─ do_fault()
                 └─ do_swap_page()
```

`do_page_fault()` 根据 ESR 判断读、写或执行访问。内核先尝试用只保护目标 VMA 的 per-VMA lock 查找它，条件不满足时再使用覆盖整个地址空间的 `mmap_lock`。VMA 存在且权限匹配后，`handle_mm_fault()` 才进入匿名页、COW、文件页或 swap（交换页）等通用处理；错误结果返回 arm64 入口后，再转换成对应信号。

三处计数时机决定了各指标的边界：

- arm64 在校验 VMA 之前调用 `perf_sw_event(PERF_COUNT_SW_PAGE_FAULTS, ...)`。perf software event 是由内核代码递增、供性能工具读取的软件计数器；Simpleperf 的 `page-faults` 会包含这条主处理路径中后来失败的访问。
- `handle_mm_fault()` 返回前调用 `mm_account_fault()`。`PGFAULT` 是内核虚拟内存事件，系统级结果可在 `/proc/vmstat` 的 `pgfault` 字段看到。它计入已经到达 `handle_mm_fault()` 的成功与失败结果；`VM_FAULT_RETRY` 表示退出本轮处理并稍后重试，未完成的 retry 会先返回，待处理完成时再计数。VMA 查找或权限检查阶段提前失败的访问不会到达这里。
- `mm_account_fault()` 遇到 `VM_FAULT_ERROR` 时，不更新 `current->min_flt`、`current->maj_flt` 及对应的 perf minor/major 事件。成功结果最终带 `VM_FAULT_MAJOR`，或之前设置过 `FAULT_FLAG_TRIED`，都会记作 major；其余记作 minor。

所以，`page-faults` 与 `minor-faults + major-faults` 出现差值有源码依据。解释差值时需要同时检查失败访问、统计区间和工具权限。

### Minor Fault：能在内存中完成的映射修复

Minor Fault 的记账条件是成功完成、最终未带 `VM_FAULT_MAJOR`，并且处理过程没有 retry。它通常能用内存中已有的数据完成映射，常见来源包括：

- **匿名页按需分配**：`MAP_ANONYMOUS` 表示映射没有文件作为后备对象。`mmap(MAP_ANONYMOUS)` 或堆扩展先建立 VMA，线程首次访问时再建立物理页和 PTE；读取可能先映射共享零页，写入时再获得私有页。
- **写时复制（Copy-on-Write，COW）**：Zygote 是预加载框架代码并 `fork` 出应用进程的系统进程。父子进程先共享只读页，某一方写入时，`do_wp_page()` 才为它准备私有副本。
- **文件页已在页缓存中**：页缓存（`page cache`）保存内核近期读过的文件数据。数据已在内存而当前进程缺少对应 PTE 时，内核可以直接建立映射，无需再次读取存储。

Minor 只表示“成功处理且未归为 major”。它无法证明页面此前已经映射，也无法证明发生了一次对象分配。一次 fault 仍可能分配页表页、处理 folio、执行 memcg 计费、维护反向映射并等待锁；folio 是把一个或多个连续基础页作为整体管理的内核对象，memcg 是按控制组统计和限制内存的机制，反向映射则用于从物理页找到映射它的进程地址。耗时会随内存压力、页大小、folio 大小和并发状态变化，不存在跨设备通用的固定微秒阈值。

`malloc()` 何时改用 `mmap()` 由分配器实现、进程状态和版本共同决定。固定字节阈值既不能解释 COW，也不适合作为通用的 Page Fault 判断规则。

### Major Fault：处理过程需要读取或等待

Linux 6.18 在 [`include/linux/mm_types.h`](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/include/linux/mm_types.h) 中把 `VM_FAULT_MAJOR` 注释为 “Page read from storage”。`do_swap_page()` 需要从交换区读页时会设置该标志，文件映射的 fault handler 需要读页时也会返回 major。

记账规则还把发生过 retry 的成功 fault 归入 major。retry 表示本轮无法立即完成，处理程序需要释放条件、等待或重新进入；它可能与 I/O 有关，也可能由其他等待触发。因此，major 只能作为“需要读页或重试”的调查线索，单凭该计数无法证明闪存 I/O 已经发生。

Android 上常见的来源有：

- 冷启动访问尚未进入页缓存的 APK、DEX、OAT/VDEX、共享库或资源文件页面；
- 后台进程的匿名页进入交换区，进程恢复后从 zRAM 读取并解压；
- 设备启用 zRAM writeback 后，交换页已写入后备存储，恢复访问需要从闪存取回；
- fault handler 等待页面 I/O 或发生 retry，最终按 major 计数。

一次 fault 可能触发 readahead（内核预读后续文件页），一次 I/O 也可能满足多个后续 fault。folio 大小、页缓存命中和 I/O 合并都会改变“fault 次数”与“读取字节数”的关系。UFS（Universal Flash Storage，移动设备常用闪存接口）、I/O 调度器、文件系统和当前负载还会影响时延。只有 major 增长与关键线程等待存储在同一时间段出现，才能支持“存储影响用户体验”的判断。

#### Android 17 的 zRAM 与 MMD

swap（交换）是把匿名页内容写入交换设备、释放原物理页，并在再次访问时读回的机制。zRAM 是位于内存中的压缩块设备，Android 通常把它用作交换设备；从 zRAM 读回并解压页面仍会走 swap-in 路径并记作 major。

Android 17 起，[Memory Management Daemon（MMD）](https://source.android.com/docs/core/perf/mmd) 统一管理 zRAM 配置和维护任务。recompression 会用压缩率更高的算法重新压缩冷页；writeback 会把符合条件的 zRAM 页移到 `/data` 上的后备存储；prefetch 则在应用按需访问前先把指定进程的交换页取回。应用从缓存冻结状态恢复时，`system_server` 可以请求 MMD 异步执行按进程预取，以减少主界面初始化期间等待后备存储的概率。

MMD 由系统策略调用，普通应用没有可移植的直接控制接口。zRAM 大小、压缩算法、writeback 开关、后备设备和预取策略都由产品配置决定；设备分析应读取实际配置和内核统计。

### 失败访问与 native crash

`si_code` 记录信号的具体原因。arm64 找不到目标 VMA 时通常发送 `SIGSEGV`，并把 `si_code` 设为 `SEGV_MAPERR`；VMA 存在但访问权限不符时通常得到 `SIGSEGV/SEGV_ACCERR`。文件映射越过有效文件内容等 `VM_FAULT_SIGBUS` 路径会产生 `SIGBUS/BUS_ADRERR`，硬件内存错误还可能产生 `BUS_MCEERR_*`。

MTE（Memory Tagging Extension，内存标签扩展）会比较指针标签与内存标签，标签检查失败时也可能发送带专用 `si_code` 的 `SIGSEGV`。因此，同为 signal 11，根因仍可能不同。

排查失败访问时还要考虑三个边界：

- use-after-free（释放后使用）未必立即 crash。被释放地址可能仍在 VMA 内，甚至已被分配器复用，此时页表层面仍允许访问。
- 栈访问落入允许增长的区域时，内核可能扩展映射；越过 guard 区或资源限制后才会失败。guard 区是留在栈边界附近、用于捕获越界访问的保护区域。
- tombstone 是 Android native crash 的诊断文件。判断根因时应一起读取 signal、`si_code`、fault address、寄存器和内存映射表，单看 `signal 11` 信息不足。

这类失败属于 native 稳定性调查，不应混入性能侧的 `min_flt`/`maj_flt` 趋势。完整方法见 [20.3 Native Crash、堆栈回溯与符号化](../ch20-stability/03-native-crash-unwinding-symbolication.md)。

### `/proc/<pid>/stat` 计数的精确语义

字段顺序由内核 [`fs/proc/array.c`](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/fs/proc/array.c) 输出。Linux 源码中的 task 是可被调度的执行单元，在这个接口里可对应单个线程，也可按线程组汇总。字段布局如下，可直接用于检查解析器索引。

```text
字段 10  minflt   当前任务或线程组的 minor fault
字段 11  cminflt  已回收子进程的 minor fault
字段 12  majflt   当前任务或线程组的 major fault
字段 13  cmajflt  已回收子进程的 major fault
字段 22  starttime  任务自系统启动后的创建时刻，单位为 clock tick
```

clock tick 是内核用于表示时间的离散单位，频率由系统的 `CLK_TCK` 决定，与 CPU 时钟周期含义不同。`starttime` 可用于判断两次读取是否仍属于同一个进程实例。

读取 `/proc/<pid>/stat` 时，`minflt` 和 `majflt` 是整个线程组的聚合值；读取 `/proc/<pid>/task/<tid>/stat` 时，得到指定线程的值。`cminflt`、`cmajflt` 累计已经由父进程等待回收的子进程 fault，不包含当前进程的其他线程。

Android 17 的 [`ProcessCpuTracker`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/com/android/internal/os/ProcessCpuTracker.java) 读取字段 10 和 12，保存 `base_minfaults`、`base_majfaults`，下一次采样计算 `rel_minfaults`、`rel_majfaults`。这也是系统 CPU dump 中 fault 增量的来源。

#### 应用内安全解析自身计数

`comm` 字段被圆括号包围，进程名本身可以包含空格和右括号。直接按空格切整行会错位。下面的示例从末尾的 `)` 后解析字段，并用 `starttime` 防止 PID 复用或进程重启造成负增量。

```kotlin
import android.os.SystemClock
import java.io.File

data class FaultSnapshot(
    val startTimeTicks: Long,
    val minor: Long,
    val major: Long,
    val elapsedRealtimeNanos: Long,
)

data class FaultDelta(
    val minor: Long,
    val major: Long,
    val durationNanos: Long,
)

fun readSelfFaults(): FaultSnapshot {
    val line = File("/proc/self/stat").readText().trim()
    val commEnd = line.lastIndexOf(')')
    require(commEnd >= 0 && commEnd + 2 < line.length) {
        "Malformed /proc/self/stat"
    }

    // fields[0] 对应内核文档中的字段 3（state）。
    val fields = line
        .substring(commEnd + 2)
        .trim()
        .split(Regex("\\s+"))
    require(fields.size > 19) { "Incomplete /proc/self/stat" }

    return FaultSnapshot(
        startTimeTicks = fields[19].toLong(), // 字段 22
        minor = fields[7].toLong(),           // 字段 10
        major = fields[9].toLong(),           // 字段 12
        elapsedRealtimeNanos = SystemClock.elapsedRealtimeNanos(),
    )
}

fun delta(
    previous: FaultSnapshot,
    current: FaultSnapshot,
): FaultDelta? {
    if (current.startTimeTicks != previous.startTimeTicks) return null
    if (current.minor < previous.minor || current.major < previous.major) return null
    if (current.elapsedRealtimeNanos <= previous.elapsedRealtimeNanos) return null

    return FaultDelta(
        minor = current.minor - previous.minor,
        major = current.major - previous.major,
        durationNanos = current.elapsedRealtimeNanos - previous.elapsedRealtimeNanos,
    )
}
```

`comm` 是 stat 中用圆括号包住的任务名，内容可以含空格和右括号；找到最末尾的 `)` 后再解析，才能保持后续字段位置稳定。示例只读取当前应用自己的 proc 节点，并用 `starttime` 识别 PID 复用或进程重启。采样应放在低频诊断窗口，避免文件读取干扰短场景；进程或线程退出、读取失败及计数回退都按无效样本处理。

#### 为什么不能用 fault 数估算分配字节

`Δfaults × 4 KB` 无法表示这段时间的内存分配量，原因包括：

- Android 15 及更高版本支持 16 KB page-size 设备；Android 17 设备可能使用 4 KB 或 16 KB 页，页大小要在运行时查询；
- minor fault 还包含 COW 和文件页缓存映射，同一虚拟区域在回收后也可能再次 fault；
- 分配器可以复用已经驻留的堆页，发生分配却没有新增 fault；
- readahead 和大 folio 会让一次 major fault 与一个基础页的 I/O 失去一一对应关系。

Java/Kotlin 可按 [AOSP 页大小指南](https://source.android.com/docs/core/architecture/16kb-page-size/getting-page-size) 调用 `Os.sysconf(OsConstants._SC_PAGE_SIZE)`，原生代码使用 `getpagesize()`。页大小只适合换算明确以 page 为单位的内核字段；对象或原生分配应使用 Heap Profile、heapprofd，或通过 JVMTI（Java Virtual Machine Tool Interface）对分配事件采样。

### 从计数建立因果证据

Page Fault 调查要回答三个问题：计数在哪个阶段增长、增长的是 minor 还是 major、当时访问的是文件映射还是匿名映射。计数只能提示现象，时间线和映射对象才能把现象与用户可感知时延联系起来。

#### 用 Simpleperf 区分事件

Android 17 Simpleperf 的生成器在 [`event_table_generator.py`](https://android.googlesource.com/platform/system/extras/+/refs/tags/android-17.0.0_r1/simpleperf/event_table_generator.py) 中注册 `page-faults`、`minor-faults` 和 `major-faults` 三个软件事件。命令应先列出目标设备可用事件，再对指定应用计数。

```shell
adb shell simpleperf list
adb shell simpleperf stat \
  --app com.example.app \
  -e page-faults,minor-faults,major-faults \
  --duration 10
```

`simpleperf list` 的实际输出就是本机能力边界。应用还要满足 [Android application profiling](https://android.googlesource.com/platform/system/extras/+/refs/tags/android-17.0.0_r1/simpleperf/doc/android_application_profiling.md) 的权限条件：面向发布的 release 包通常需要 `profileableFromShell`，调试用 debug 包可依赖 `debuggable`，root 设备另有更宽权限。user build 是面向量产设备的系统构建，预装工具版本和厂商策略仍可能缩小其可用范围。统计结果中 `page-faults` 与 minor、major 之和的差值，应按三类事件各自的计数时机解释。

#### 用 Perfetto 定位等待发生在哪一段

Perfetto 可以把 fault 增长与启动阶段、线程调度、文件 I/O、内存回收和块设备 I/O 放在同一时间线上。tracepoint 是内核预先定义并命名的静态事件点；tracefs 是列出、启用和读取这类事件的内核虚拟文件系统。arm64 设备不保证暴露 `exceptions/page_fault_user`，把它固定写进配置可能得到没有该事件的数据。

系统侧调试应先查询 tracefs，再从目标设备已经暴露的 `sched`、`vmscan`、`filemap`、`kmem` 和 `block` 事件中选择配置。

```shell
adb shell su 0 sh -c \
  "grep -E 'page_fault|vmscan|filemap|kmem|block' \
  /sys/kernel/tracing/available_events"
```

这条命令需要 root 或等价系统调试权限。结果为空时，应改用 Simpleperf 计数和常规 Perfetto 调度/I/O 数据，不要假定 tracepoint 名称跨内核版本稳定。

eBPF 是经过内核校验、可在事件点执行的小程序，也只能挂到设备已有且安全策略允许的位置。`kprobe` 会在内核函数或指令位置安装动态探针，BTF 描述内核类型信息，ABI 规定函数调用约定；内核升级可能改变三者依赖的符号、类型或参数布局。这些方案适合受控的系统调试环境，不适合作为普通应用的通用监控接口。

#### 把计数对齐到关键路径

建议按以下顺序收集证据：

1. 给冷启动、页面切换、滚动或后台恢复添加时间标记，按阶段计算 fault 增量和持续时间。
2. 读取 `/proc/<pid>/maps`，或使用 Perfetto 文件系统事件、采样调用栈，确认相关 VMA 对应 DEX/OAT、共享库、资源、匿名堆还是 swap。
3. 同时观察线程状态、内存回收和块设备 I/O。major 增长并且关键线程同期等待存储，才构成 I/O 影响关键路径的证据。
4. 在同一设备、同一安装状态和相近内存压力下做基线对照，分别记录冷页缓存与热页缓存场景。

`/proc/stat` 中的 `iowait` 表示 CPU 被记为空闲且系统有待完成 I/O 的时间，它无法把等待归因到具体进程，内核文档也提醒该值很难精确计算。较高的 kernel CPU 表示 CPU 正在执行内核代码，也不表示 CPU 正在等待 I/O。两项数据都需要进程级时间线补充。

### 按原因选择改进手段

#### 冷启动文件页

先确认 major fault 出现在启动关键路径，并定位到 DEX/OAT、原生库或资源。DEX 保存应用字节码，OAT/VDEX 是 ART 编译或校验这些字节码时生成和使用的产物。Baseline Profile 记录常用代码，帮助 ART 提前编译；Startup Profile 描述启动期间常用类和方法，还可参与 DEX 布局优化。检查两类 profile 是否覆盖实际启动调用，再比较编译产物与布局变化。

原生库、资源和 APK 条目的压缩、对齐会影响能否直接 `mmap` 及读取范围，需要结合构建产物和安装形态验证。文件体积变小与 fault 等待缩短没有必然关系。

#### 匿名页与 COW

minor fault 集中在首次访问大块匿名内存时，应检查分配时机、初始化范围和执行线程。Zygote 继承页的大量写入还会增加 COW。PSS（Proportional Set Size，按共享比例分摊后的驻留内存）、堆剖析和调用栈可以帮助定位写入来源。

评价改动时同时比较关键路径时延、总内存和后台压力。单独降低 fault 数不能证明优化有效。

#### swap-in 与后台恢复

后台恢复出现 major fault 时，要同时查看内存压力、进程冻结、zRAM、writeback 和 LMKD 事件。LMKD（Low Memory Killer Daemon，低内存终止守护进程）会在内存压力下选择进程终止，它的事件可帮助区分“从交换区恢复”和“进程已被杀后重启”。

Android 17 的 MMD prefetch 属于系统策略能力，普通应用不应复制其内核机制。系统开发者调整策略时，要同时比较恢复时延、后台 I/O、内存占用和闪存写入量。

#### 谨慎使用预取建议

`madvise(MADV_WILLNEED)` 是向内核提示“近期可能访问这段映射”，不保证立即读入，也不保证保留页面。它、readahead 或主动访问页面都可能把等待移到更早时刻，也可能产生无效 I/O、挤占页缓存并增加内存压力。采用前要在冷态场景验证访问集合和收益，并确认预取不与前台关键任务竞争。

### `userfaultfd`：ART 的生产用例与应用边界

`userfaultfd` 允许进程注册一段虚拟地址，并通过文件描述符接收该区域的 fault 通知，再用 `UFFDIO_*` ioctl 完成映射。文件描述符是进程引用内核对象的整数句柄，ioctl 是向该对象发送控制命令的系统调用。`userfaultfd` 把部分缺页处理交给用户态线程，适合需要自行控制页面到达时机的内存管理器。

Android 17 已有生产用例。ART 的 Concurrent Mark-Compact GC 在 [`mark_compact.cc`](https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/runtime/gc/collector/mark_compact.cc) 中调用 `userfaultfd(..., UFFD_USER_MODE_ONLY)`。Concurrent Mark-Compact 会标记存活对象并移动它们以压缩堆；moving space 是这次移动涉及的 ART 堆区域。

ART 先通过 `UFFDIO_API` 查询可用 feature，这一步称为 feature negotiation（能力协商）。它还检查所需内核能力和 `UFFD_FEATURE_SIGBUS`。创建失败或条件不满足时，`uffd_` 进入 fallback mode，改用 stop-the-world compaction；后者会暂停应用线程再完成压缩。

这个实现给出两条使用边界：

- `userfaultfd` 的可用性由内核能力、Android 安全限制和系统配置共同决定；
- 接管 fault 会改变线程阻塞与内存访问行为，适合受控的运行时或系统组件，无法充当低干扰的应用性能计数器。

普通应用只需 Page Fault 指标时，应读取 `/proc/self/stat` 或使用设备支持的 perf 工具。系统组件确需 `userfaultfd` 时，应像 ART 一样完成能力协商、失败降级和逐版本验证。

### 判读清单

1. `min_flt`、`maj_flt` 与 Simpleperf minor/major 只统计成功完成的 fault；`page-faults` 的计数边界更靠近架构入口。
2. SIGSEGV、SIGBUS 等失败访问交给 tombstone、signal 和 `si_code` 分析，不把它们虚构成第三个 proc fault 计数。
3. major 是页面读入或 retry 的线索。只有它与关键线程存储等待同时出现，才支持 I/O 影响关键路径的判断。
4. 设备页大小在运行时可能是 4 KB 或 16 KB；fault 数仍不能换算对象分配字节。
5. 文件冷页、匿名页/COW 与 swap-in 需要分别验证，预取、布局或初始化改动都要用同场景对照评估。

## 全文小结

heapprofd、procfs CPU 与 Page Fault 分别提供分配调用栈、累计运行时间和虚拟内存映射修复计数。排障时应先用低成本的自身计数确认异常窗口，再按问题选择 heapprofd、Simpleperf 或 Perfetto；任何百分比、增长量和 fault 次数都必须保留采样分母、进程实例、权限与缺失状态。

三类证据的联合价值在于缩小原因范围，而不是从单个数字直接推断根因。native 存活分配要与 RSS/PSS 和映射类别对照，CPU 时间要与调度等待分开，major fault 也只有在关键线程同期等待存储时才支持 I/O 归因。量产接入还要把 profileable、系统限流、采集器开销、符号文件与原始 trace 的访问控制纳入同一协议。


## 参考资料

- [AOSP android-17.0.0_r1：heapprofd producer](https://android.googlesource.com/platform/external/perfetto/+/refs/tags/android-17.0.0_r1/src/profiling/memory/heapprofd_producer.cc)
- [AOSP android-17.0.0_r1：bionic heapprofd hook 安装](https://android.googlesource.com/platform/bionic/+/refs/tags/android-17.0.0_r1/libc/bionic/malloc_heapprofd.cpp)
- [AOSP android-17.0.0_r1：user build profile 权限判定](https://android.googlesource.com/platform/external/perfetto/+/refs/tags/android-17.0.0_r1/src/profiling/common/producer_support.cc)
- [AOSP android-17.0.0_r1：packages.list parser](https://android.googlesource.com/platform/external/perfetto/+/refs/tags/android-17.0.0_r1/src/traced/probes/packages_list/packages_list_parser.cc)
- [AOSP android-17.0.0_r1：HeapprofdConfig proto](https://android.googlesource.com/platform/external/perfetto/+/refs/tags/android-17.0.0_r1/protos/perfetto/config/profiling/heapprofd_config.proto)
- [AOSP android-17.0.0_r1：heapprofd init service](https://android.googlesource.com/platform/external/perfetto/+/refs/tags/android-17.0.0_r1/heapprofd.rc)
- [AOSP android-17.0.0_r1：profiler guardrails](https://android.googlesource.com/platform/external/perfetto/+/refs/tags/android-17.0.0_r1/src/profiling/common/profiler_guardrails.cc)
- [AOSP android-17.0.0_r1：官方 heap_profile 脚本](https://android.googlesource.com/platform/external/perfetto/+/refs/tags/android-17.0.0_r1/tools/heap_profile)
- [Perfetto：Native heap profiler](https://perfetto.dev/docs/data-sources/native-heap-profiler)
- [Perfetto：Memory profiling guide](https://perfetto.dev/docs/getting-started/memory-profiling)
- [PerfettoSQL：heap_profile_allocation](https://perfetto.dev/docs/analysis/sql-tables#heap_profile_allocation)
- [Android Developers：`<profileable>` element](https://developer.android.com/guide/topics/manifest/profileable-element)
- [Android Developers：`ProfilingManager`](https://developer.android.com/reference/android/os/ProfilingManager)
- [Android Developers：`ProfilingResult`](https://developer.android.com/reference/android/os/ProfilingResult)
- [Android Developers：App-driven profiling](https://developer.android.com/topic/performance/tracing/profiling-manager/how-to-capture)
- [AndroidX：`HeapProfileRequestBuilder`](https://developer.android.com/reference/androidx/core/os/HeapProfileRequestBuilder)
- [AOSP android-17.0.0_r1：Profiling heap profile 配置](https://android.googlesource.com/platform/packages/modules/Profiling/+/refs/tags/android-17.0.0_r1/service/java/com/android/os/profiling/Configs.java)
- [AOSP android-17.0.0_r1：ProfilingService 权限、限流与结果处理](https://android.googlesource.com/platform/packages/modules/Profiling/+/refs/tags/android-17.0.0_r1/service/java/com/android/os/profiling/ProfilingService.java)

- [Android Common Kernel r39：procfs 文档](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r39/Documentation/filesystems/proc.rst)
- [Android Common Kernel r39：`/proc/stat` 实现](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r39/fs/proc/stat.c)
- [Android Common Kernel r39：CPU 时间记账](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r39/kernel/sched/cputime.c)
- [Android Common Kernel r39：进程 stat 输出](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r39/fs/proc/array.c)
- [Android Common Kernel r39：`/proc/loadavg` 输出](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r39/fs/proc/loadavg.c)
- [Android Common Kernel r39：load average 算法](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r39/kernel/sched/loadavg.c)
- [Android Developers：`Process.getElapsedCpuTime()`](https://developer.android.com/reference/android/os/Process#getElapsedCpuTime())
- [Android Developers：`SystemClock`](https://developer.android.com/reference/android/os/SystemClock)

- [Android Common Kernel r39：arm64 fault 入口](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r39/arch/arm64/mm/fault.c)
- [Android Common Kernel r39：通用 fault 处理与计数](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r39/mm/memory.c)
- [Android Common Kernel r39：`VM_FAULT_*` 定义](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r39/include/linux/mm_types.h)
- [Android Common Kernel r39：`userfaultfd` 文档](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r39/Documentation/admin-guide/mm/userfaultfd.rst)
- [AOSP：Android 17 Simpleperf 软件事件表](https://android.googlesource.com/platform/system/extras/+/refs/tags/android-17.0.0_r1/simpleperf/event_table_generator.py)
- [AOSP：Android 应用 Simpleperf 权限与用法](https://android.googlesource.com/platform/system/extras/+/refs/tags/android-17.0.0_r1/simpleperf/doc/android_application_profiling.md)
- [Android 官方文档：Memory Management Daemon](https://source.android.com/docs/core/perf/mmd)
- [Android 官方文档：运行时获取页大小](https://source.android.com/docs/core/architecture/16kb-page-size/getting-page-size)
- [Android 官方文档：native crash 与 tombstone](https://source.android.com/docs/core/tests/debug/native-crash)
- [Perfetto：CPU scheduling events](https://perfetto.dev/docs/data-sources/cpu-scheduling)
