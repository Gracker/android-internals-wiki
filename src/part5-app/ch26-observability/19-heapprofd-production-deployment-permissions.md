---
title: "heapprofd 生产级部署与权限模型"
chapter: "26.19"
section: "26.19"
status: finalized
applicable_versions: "Android 10 (API 29) - Android 17 (API 37); ProfilingManager 路径要求 Android 15 (API 35) 或更新版本"
tags: [heapprofd, heap-profiling, memory, production, perfetto, permissions, native-leak]
related_chapters: ["4.5", "10.1", "10.3", "13.11", "13.22", "14.5", "14.11", "19.13", "20.10", "20.16", "20.20", "23.1", "23.3", "23.7", "26.10"]
last_verified: "2026-08-15"
last_source_verified_at: "2026-08-15"
last_verified_against: "AOSP android-17.0.0_r1 heapprofd, Bionic, Perfetto Profiling module, and init sources; current Perfetto native heap profiler and SQL docs; current Android Developers profileable, ProfilingManager, ProfilingResult, and AndroidX HeapProfileRequestBuilder references, retrieved 2026-08-15"
confidence: high
sources:
  - type: legacy-reference-preserved
    path: "external/perfetto/src/profiling/memory/heapprofd.cc"
  - type: legacy-reference-preserved
    path: "external/perfetto/src/profiling/common/producer_support.cc"
  - type: legacy-reference-preserved
    path: "external/perfetto/src/profiling/common/profiler_guardrails.cc"
  - type: legacy-reference-preserved
    path: "external/perfetto/heapprofd.rc"
  - type: legacy-reference-preserved
    path: "external/perfetto/src/profiling/memory/java_hprof_producer.cc"
  - type: legacy-reference-preserved
    path: "external/perfetto/src/traced/probes/packages_list/packages_list_parser.cc"
  - type: legacy-reference-preserved
    path: "system/memory/libmemunreachable/MemUnreachable.cpp"
  - type: legacy-reference-preserved
    path: "developer.android.com/topic/performance/memory"
  - type: legacy-reference-preserved
    path: "Clippings/Android 应用稳定性剖析与优化 - Native 内存泄漏监控：寻找 Native 中不可达内存.md"
  - type: legacy-reference-preserved
    path: "Clippings/Android 性能优化 - Native 内存优化（上）：so 库申请的内存优化.md"
  - type: aosp
    path: "https://android.googlesource.com/platform/external/perfetto/+/refs/tags/android-17.0.0_r1/src/profiling/memory/heapprofd_producer.cc"
  - type: aosp
    path: "https://android.googlesource.com/platform/bionic/+/refs/tags/android-17.0.0_r1/libc/bionic/malloc_heapprofd.cpp"
  - type: aosp
    path: "https://android.googlesource.com/platform/external/perfetto/+/refs/tags/android-17.0.0_r1/src/profiling/common/producer_support.cc"
  - type: aosp
    path: "https://android.googlesource.com/platform/external/perfetto/+/refs/tags/android-17.0.0_r1/src/traced/probes/packages_list/packages_list_parser.cc"
  - type: aosp
    path: "https://android.googlesource.com/platform/external/perfetto/+/refs/tags/android-17.0.0_r1/protos/perfetto/config/profiling/heapprofd_config.proto"
  - type: aosp
    path: "https://android.googlesource.com/platform/external/perfetto/+/refs/tags/android-17.0.0_r1/heapprofd.rc"
  - type: aosp
    path: "https://android.googlesource.com/platform/external/perfetto/+/refs/tags/android-17.0.0_r1/src/profiling/common/profiler_guardrails.cc"
  - type: aosp
    path: "https://android.googlesource.com/platform/external/perfetto/+/refs/tags/android-17.0.0_r1/tools/heap_profile"
  - type: aosp
    path: "https://android.googlesource.com/platform/packages/modules/Profiling/+/refs/tags/android-17.0.0_r1/service/java/com/android/os/profiling/Configs.java"
  - type: aosp
    path: "https://android.googlesource.com/platform/packages/modules/Profiling/+/refs/tags/android-17.0.0_r1/service/java/com/android/os/profiling/ProfilingService.java"
  - type: official
    path: "https://perfetto.dev/docs/data-sources/native-heap-profiler"
  - type: official
    path: "https://perfetto.dev/docs/getting-started/memory-profiling"
  - type: official
    path: "https://perfetto.dev/docs/analysis/sql-tables#heap_profile_allocation"
  - type: official
    path: "https://developer.android.com/guide/topics/manifest/profileable-element"
  - type: official
    path: "https://developer.android.com/reference/android/os/ProfilingManager"
  - type: official
    path: "https://developer.android.com/reference/android/os/ProfilingResult"
  - type: official
    path: "https://developer.android.com/topic/performance/tracing/profiling-manager/how-to-capture"
  - type: official
    path: "https://developer.android.com/reference/androidx/core/os/HeapProfileRequestBuilder"
pipeline_stage: ready-to-publish
task2b_state: fixed
task6_state: reviewed
task9_state: reviewed
last_draft_polish_at: "2026-08-15T22:54:40+08:00"
last_draft_polish_run_id: "20260815-225440-gracker-writing-480"
last_review_finalize_at: "2026-08-15T22:54:40+08:00"
last_review_finalize_run_id: "20260815-225440-gracker-writing-480"
last_rework_at: "2026-08-15T22:54:40+08:00"
last_rework_run_id: "20260815-225440-gracker-writing-480"
---

# 26.19 heapprofd 生产级部署与权限模型

本文讨论 Android 17 user build 上的 native heap 采集。user build 是面向量产设备的系统构建类型，许多只供调试使用的权限会在其中关闭。

native heap 是 App 通过 `malloc`、C++ `new` 等接口，在 ART（Android Runtime）管理的 Java/Kotlin 对象堆之外维护的内存。要让采集在量产环境中可用，需要同时处理目标进程、会话发起者、公开入口、开销限制和结果解释。

平台源码以 `android-17.0.0_r1` 为锚点；这些实现没有依赖本文需要单独核对的内核接口，因此不引用 kernel tag。

heapprofd 随 Android 10 引入。Android 12 增加 named heap（由分配器注册名称、可单独选择的一类堆）、`all_heaps` 和 installer 过滤等配置。

Android 15 又通过 `ProfilingManager` 向普通应用开放受系统约束的 heap profile 请求，Android 17 保留这些入口。`<profileable>` 元素从 API 29 可用，`android:enabled` 属性从 API 30 可用；heapprofd 的起始版本仍是 Android 10。

## 26.19.1 heapprofd 记录什么

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

## 26.19.2 Android 17 的工作流程

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

## 26.19.3 user build 的权限判定

UID 是 Android 用来区分应用和系统主体的数字身份。Android 17 的 `CanProfileAndroid()` 先看 build type：`userdebug` 和 `eng` 通过这一层，`user` build 继续检查 UID、会话发起者以及 `/data/system/packages.list` 中的包属性。

session initiator 表示是谁发起 Perfetto 会话。表中的规则适用于直接提交给 `android.heapprofd` data source 的配置。通过 `ProfilingManager` 请求时，应用不能自行填写 `session_initiator`；系统服务先核对 Binder 调用 UID 与包名，再生成只指向调用方包名的配置。两种入口采用不同的权限流程，结论不能混用。

### 普通应用与两类发起者

普通 App UID 和 SDK sandbox UID 的 Android 17 判定如下：

| 会话发起者 | user build 所需属性 |
|---|---|
| shell / `SESSION_INITIATOR_UNSPECIFIED` | `profileable_from_shell` 或 `debuggable` |
| `SESSION_INITIATOR_TRUSTED_SYSTEM` | `profileable` 或 `debuggable` |

`profileable_from_shell` 对应 Manifest 中的 `android:shell="true"`，表示 shell 调试工具可以分析该应用；`profileable` 对应 `<profileable>` 处于 enabled 状态。trusted-system 允许系统服务采集未向 shell 开放的应用，但目标仍要声明 profileable 或 debuggable。

`SESSION_INITIATOR_TRUSTED_SYSTEM` 是 `traced` 赋予受信系统会话的身份。普通 App 即使在自己的 textproto 中写入该字段，也不会获得这项身份。

### 其他 UID

`AID_APP_START` 是平台 UID 与普通应用 UID 的起始分界。平台 UID、isolated UID 和普通应用的处理不同：

- 平台 UID 小于 `AID_APP_START` 时，user build 只允许 trusted-system 发起者；
- SDK sandbox 是替 SDK 隔离运行代码的进程，其 UID 会映射回所属 App UID，再读取该包的 profileable 属性；
- isolated process 使用临时隔离 UID，无法直接映射到来源包。Android 17 只在 trusted-system 会话且 `packages.list` 中所有包都允许 trusted initiator 采集时放行；
- 其余 UID 范围在 user build 上拒绝。

isolated process 的判定有意从严。目标应用即使声明了 `<profileable>`，它的 isolated service 仍可能得不到 profile。排查时需要同时查看 trace 中的拒绝信息和 heapprofd 日志，只看主进程 Manifest 不足以确认权限。

### installer 过滤

installer 是把目标 APK 安装到设备上的包或系统来源。`target_installed_by` 是 `HeapprofdConfig` 的可选过滤项，支持普通 installer 包名以及 `@system`、`@product`、`@null`；`@null` 表示 sideload，也就是没有 installer 包记录的侧载安装。配置未填写该字段时，`CanProfileAndroid()` 不检查 installer。

installer 过滤只会缩小候选集合，不会授予 profile 权限。这组约束要求目标来自 system 或 product 分区，但目标仍须通过相应的 profileable 判定：

```textproto
target_installed_by: "@system"
target_installed_by: "@product"
```

这两行适合平台采集策略用来限制目标来源。把它们加入 shell 配置，仍无法采集未开放 shell profiling 的应用。

## 26.19.4 Manifest 应怎样声明

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

## 26.19.5 daemon、SELinux 与能力边界

Android 17 的 `heapprofd.rc` 把服务定义为 disabled，由 `traced.lazy.heapprofd=1` 或持久属性按需启动。服务以 `nobody` 用户运行，加入 `nobody` 和 `readproc` 组，并声明 `KILL`、`DAC_READ_SEARCH` capability。capability 是把 root 权限拆成较小能力单元的 Linux 机制。

SELinux 会按安全策略限制进程可执行的操作。同一份 rc 文件明确说明：SELinux 在 user build 上拒绝 `DAC_READ_SEARCH` 对应权限，userdebug/eng 才允许这部分访问。因此，rc 中出现 capability 不能推出生产设备可任意读取 `/proc/<pid>/mem`。

`/dev/socket/heapprofd` 的 socket mode 只控制文件系统层面的连接条件，无法单独证明调用者已获采集授权。连接建立后，producer 会读取 peer UID（连接对端的 UID）、目标 UID 和 `packages.list`，再执行 `CanProfile()`。文件 mode、Linux capability、SELinux 和 Perfetto 会话身份共同构成权限边界。

## 26.19.6 native 进程名按规范化结果精确匹配

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

## 26.19.7 三种采集入口

### Android 15–17 使用 `ProfilingManager`

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

### 使用官方 `tools/heap_profile`

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

### 手写 Perfetto textproto

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

## 26.19.8 参数怎样影响开销和证据质量

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

## 26.19.9 采集主体与部署位置

### Android 15–17 普通 App 请求自己的 profile

`ProfilingManager` 是应用在公开用户设备上请求自身 heap profile 的标准入口。它不要求 adb，也不会把 trusted-system 身份交给应用。系统服务施加这些约束：

- Binder 调用 UID 必须与请求包名对应；
- 配置目标固定为调用方包名；
- 请求同时受单应用与全系统限流；
- DeviceConfig（系统服务可动态读取的一组配置项）可以限制参数范围或关闭 profile 类型；
- 结果复制到应用目录，由应用负责上传和删除。

这条路径适合少量、按场景触发的线上取证。它的可配置范围小于手写 Perfetto config，无法选择其他进程名、installer 过滤、连续 dump 或自定义 heapprofd guardrail。

### QA 在 user build 上采 release APK

第三方应用最容易复现的方式是让 QA 在 user build 上通过 shell 采集：

1. release APK 声明 `android:shell="true"`；
2. 测试设备保持 user build；
3. QA 通过 adb、Perfetto UI 或 `tools/heap_profile` 发起会话；
4. trace 离开设备前按内部数据策略处理。

这条路径同时覆盖 release 优化和 user-build 权限，适合灰度前问题复现。它仍依赖本地调试通道，不代表 App 能在用户手机上自行启动系统采集。

### 平台拥有受信采集组件

OEM 或系统产品可以让受信系统服务按设备健康信号发起 Perfetto 会话。目标 App 只需 enabled profileable，是否向 shell 开放由产品策略决定。采集服务还应负责：

- 目标包和 installer 允许名单；
- 采样窗口、次数与资源预算；
- 充电、温度、前后台和低内存条件；
- trace 存储、上传、访问审计与过期删除；
- Build ID、版本号和符号文件映射。

受信发起者身份来自系统集成，普通 APK 无法模拟。设备管理权限或远程配置本身也不会自动获得该身份。

### Android 12–14 的普通 App 无法自主启动系统级 heapprofd

Android 12–14 的普通 App 没有 `ProfilingManager`，也没有公开 API 可以把自己声明为 trusted-system 会话。

若产品必须在这些版本的终端用户设备上由 App 自主触发，只能改用应用内 allocator instrumentation（在分配器调用处自行记录）、SDK 自带 native hook、GWP-ASan 或轻量内存指标，并单独评估兼容性、性能和隐私。

若想用 `onTrimMemory()`、PSS 阈值或 `ApplicationExitInfo` 触发 heapprofd，必须先确认设备上存在有权执行采集的系统主体。Android 15–17 可以请求 `ProfilingManager`，但仍受限流和并发会话约束。更低版本中的事件信号只能决定何时记录应用内证据，无法增加 Perfetto 系统权限。

## 26.19.10 如何判断 native heap 是否持续增长

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

### 三类常见误判

1. **attach 之前的存量缺失**：attach 指采集器接入已经运行的进程。旧分配没有对应事件，所以运行期采集的第一次 dump 无法代表完整 native heap；
2. **分配器缓存仍保留页面**：应用已经 free，分配器仍可能保留 arena 或 page。arena 是分配器管理的一组内存区域，page 是操作系统映射和回收内存的基本页单位；此时仍存活分配的估算字节数已回落，RSS 仍可能不变；
3. **增长来自 `mmap` 或图形内存**：PSS 上升而 heapprofd 平稳时，应转查 anonymous mapping（匿名内存映射）、文件 mapping、DMA-BUF 与 GPU 内存。

heapprofd 证据与 PSS 证据应并排解释。两者趋势一致时，可把调用栈作为主要线索；趋势分离时，应先确定增长所在的内存类别。

## 26.19.11 失败场景排查

### `ProfilingManager` 请求被拒绝

API 35 以上的应用应先检查 `ProfilingResult` 的错误码：

- `ERROR_FAILED_RATE_LIMIT_PROCESS` 表示调用应用的小时、天或周预算已经用完；
- `ERROR_FAILED_RATE_LIMIT_SYSTEM` 表示整台设备的共享预算已经用完；
- `ERROR_FAILED_PROFILING_IN_PROGRESS` 表示已有不兼容的 profiling 会话；
- `ERROR_FAILED_INVALID_REQUEST` 常见于参数越界、未知参数或 profile 类型被关闭。

命中限流后立即重试通常仍会失败。应用应记录错误分类，并等待下一次有诊断价值的场景。listener 是接收异步结果的回调；若进程在采集期间退出，系统会停止并保存已有结果，应用下次启动并注册全局 listener 后才有机会收到补发通知。

### 手写 Perfetto 会话没有生成 profile

按以下顺序检查：

1. 设备是否为 Android 10 或更新版本；
2. 最终 APK 是否 debuggable，或 `<profileable android:shell="true">` 是否生效；
3. `process_cmdline` 是否与 `adb shell ps -A` 的 NAME 精确一致；
4. 目标是普通 App、SDK sandbox、isolated process 还是平台 UID；
5. 配置是否误用了 `no_running` 或 `no_startup`；
6. `sampling_interval_bytes` 是否为非零值；
7. heapprofd 和 traced 日志是否报告 `not profileable`（目标不可采）、signal 失败或 client 连接失败。

### profile 提前结束

共享 buffer 跟不上分配速率时，目标进程内的 heapprofd client 会出现 buffer overrun。可以增大 sampling interval 或 `shmem_size_bytes`，也可以在可控实验中启用 `block_client`。线上场景不应为了保住 trace 而无条件阻塞高频分配线程。

memory 或 CPU guardrail 命中也会关闭 data source。检查阈值时要区分 daemon 总开销和目标进程开销；`max_heapprofd_memory_kb` 不限制目标 App 的 native heap。

### 栈缺帧或符号缺失

常见原因包括缺少 Build ID 对应符号、栈展开信息被裁剪、JIT/AOT frame 缺少可用元数据、相同代码折叠，以及 trace 与符号包版本不一致。JIT 是运行时即时编译，AOT 是安装或构建阶段的提前编译，frame 表示调用栈中的一层函数记录。

相同代码折叠是编译器或链接器把内容相同的函数实现合并到同一地址；它会让一个地址对应多个候选符号。

符号化是把程序地址还原成函数名和源码位置。build fingerprint 是标识一套系统构建的字符串。

符号服务应以 APK version、ABI、Build ID 和系统 build fingerprint 定位文件；只按 so 文件名匹配容易拿错版本。

## 26.19.12 与其他工具的职责分工

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

## 26.19.13 数据安全与归档

heapprofd 不复制任意 heap payload（堆中对象或缓冲区的原始内容），但 trace 仍可能包含：

- 进程名、线程名与 UID 关联；
- 映射路径、模块名、Build ID 和地址；
- native 与可展开的 Java 调用栈；
- trace 中同时开启的其他 data source 数据。

线上采集策略应把完整 trace 当作诊断数据管理。建议只启用必要的 data source，限制目标包和时长，在设备侧加密存储，为上传通道做身份校验，服务端按角色授权，并设置明确的删除期限。

符号化宜在受控环境中按 Build ID 完成。只上传 `heap_profile_allocation` 表会丢失完整调用栈、错误标志和会话关联信息，不能视为默认的“脱敏等价物”。

若要裁剪，应定义可复现的 trace-to-report（从 trace 转换为摘要报告）格式，并保留采样参数、版本和错误元数据。

## 26.19.14 发布前检查表

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

## 参考材料

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
