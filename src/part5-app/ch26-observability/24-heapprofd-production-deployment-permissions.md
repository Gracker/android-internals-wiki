---
title: "heapprofd 生产级部署与权限模型"
chapter: "26.24"
status: ready-for-review
applicable_versions: "Android 12 (API 31) - Android 17 (API 37)"
tags: [heapprofd, heap-profiling, memory, production, perfetto, permissions, native-leak]
related_chapters: ["4.3", "4.9", "8.39", "10.8", "13.22", "14.1", "14.3", "23.11", "23.25", "26.16"]
created_by: "task2a-knowledge-gap"
created_date: "2026-07-06"
drafted_date: "2026-07-12"
last_verified: "2026-07-12"
last_verified_against: "AOSP android-17.0.0_r1"
confidence: high
sources:
  - type: aosp
    path: "external/perfetto/src/profiling/memory/heapprofd.cc"
  - type: aosp
    path: "external/perfetto/src/profiling/common/producer_support.cc"
  - type: aosp
    path: "external/perfetto/src/profiling/common/profiler_guardrails.cc"
  - type: aosp
    path: "external/perfetto/heapprofd.rc"
  - type: aosp
    path: "external/perfetto/src/profiling/memory/java_hprof_producer.cc"
  - type: aosp
    path: "external/perfetto/src/traced/probes/packages_list/packages_list_parser.cc"
  - type: aosp
    path: "system/memory/libmemunreachable/MemUnreachable.cpp"
  - type: official
    path: "developer.android.com/topic/performance/memory"
  - type: book
    path: "Clippings/Android 应用稳定性剖析与优化 - Native 内存泄漏监控：寻找 Native 中不可达内存.md"
  - type: book
    path: "Clippings/Android 性能优化 - Native 内存优化（上）：so 库申请的内存优化.md"
---

# 26.24 heapprofd 生产级部署与权限模型

Android 17 user build 上的 native heap 采集涉及目标进程、会话发起者、公开入口、开销限制和结果解释。平台源码锚定 `android-17.0.0_r1`；相关机制不涉及内核接口，因此没有引用 kernel tag。

heapprofd 随 Android 10 引入。Android 12 增加了 named heap、`all_heaps` 和 installer 过滤等配置能力；Android 15 又通过 `ProfilingManager` 向普通应用提供受系统约束的 heap profile 请求。Android 17 延续这几条入口。`<profileable>` 元素从 API 29 可用，`android:enabled` 属性从 API 30 可用。版本时间线应按这些可核验事实描述，不能把 Android 12 写成 heapprofd 的起点。

## 26.24.1 heapprofd 记录什么

heapprofd 观察目标进程在采集窗口内经过受支持 allocator 的分配与释放，并把采样大小、调用栈和映射信息写入 Perfetto trace。默认 heap 是 `libc.malloc`，覆盖 bionic 的 `malloc`、`free`、`calloc`、`realloc`、`new` 和 `delete` 等分配路径。

它不扫描一份完整的进程堆快照，也不保存对象内容。下面这些对象需要其他数据源：

| 对象 | heapprofd 可见性 | 补充数据源 |
|---|---|---|
| 会话期间的 `malloc` / `free` | 可采样并归因到调用栈 | Perfetto heap flamegraph |
| 会话开始前已存在的 allocation | 没有历史分配事件，不能还原来源 | 更早启动采集或做基线对照 |
| 直接 `mmap` / `munmap` | 默认不经过 `libc.malloc` heap | Perfetto ftrace syscall 事件、`/proc/<pid>/maps` |
| DMA-BUF、图形 buffer | 没有 allocator 调用栈语义 | memtrack、`dmabuf_dump`、GpuMem |
| Java 对象引用关系 | native heap profile 不提供 | Java heap dump、Android Studio profiler |
| allocator 内部缓存 | 能看到应用层 free，不能直接解释 RSS 是否归还 | `dumpsys meminfo`、smaps、allocator 指标 |

因此，heapprofd 适合回答“采集窗口内哪些调用栈产生了仍存活的 native allocation”。它单独回答不了“进程 PSS 为何增长”或“哪一个 Java 引用保住了 native 对象”。

## 26.24.2 Android 17 的工作链路

Android 17 中，`heapprofd` 是 Perfetto producer。一次对已运行进程的采集会经过以下环节：

1. `traced` 把 `android.heapprofd` data source 配置交给 heapprofd；
2. heapprofd 规范化进程名，扫描 `/proc` 找出目标 PID；
3. producer 向目标发送 `__SIGRTMIN + 4`，`si_value` 为 heapprofd 定义的值；
4. bionic 的 heapprofd 入口在专用线程中加载 `heapprofd_client.so`，安装 malloc dispatch；
5. 目标进程把采样事件写入共享 ring buffer；
6. heapprofd 的 unwinder 读取事件、展开调用栈并维护存活 allocation 账目；
7. 停止会话或到达连续 dump 时间点时，producer 写出 `ProfilePacket`。

信号处理函数只负责启动安装流程。动态加载、连接 daemon 和 hook 初始化不会全部压在 signal handler 上执行。bionic 还会处理与 GWP-ASan、malloc debug 等 dispatch 的兼容关系；存在不兼容 malloc hook 时，heapprofd 可能拒绝安装。

启动期目标使用另一条入口。heapprofd 在会话开始时设置按进程名匹配的系统属性，之后由 bionic 在新进程初始化期间接入客户端。配置中的 `no_startup` 会关闭这条路径，`no_running` 会跳过已经运行的进程。

## 26.24.3 user build 的权限判定

Android 17 的 `CanProfileAndroid()` 会先看 build type。`userdebug` 和 `eng` 直接通过这一层；`user` build 继续检查 UID、会话发起者和 `/data/system/packages.list`。

下面的判定表描述直接提交给 Perfetto 的 `android.heapprofd` data source。`ProfilingManager` 不是让应用自行填写 `session_initiator`：系统服务先核对 Binder 调用 UID 与包名，再代为生成限定到调用方包名的配置。两条入口不能混用权限结论。

### 普通应用与两类发起者

对普通 App UID 和 SDK sandbox UID，Android 17 的判定可概括为下表：

| 会话发起者 | user build 所需属性 |
|---|---|
| shell / `SESSION_INITIATOR_UNSPECIFIED` | `profileable_from_shell` 或 `debuggable` |
| `SESSION_INITIATOR_TRUSTED_SYSTEM` | `profileable` 或 `debuggable` |

`profileable_from_shell` 对应 Manifest 中的 `android:shell="true"`。`profileable` 对应 profileable element 处于 enabled 状态。trusted-system 允许系统服务采集没有向 shell 开放的应用，但目标仍要声明 profileable 或 debuggable。

`SESSION_INITIATOR_TRUSTED_SYSTEM` 是 traced 赋予受信系统会话的身份。普通 App 不能在自己的 textproto 中写一个字段就获得该身份。

### 其他 UID

平台 UID、isolated UID 和普通应用的处理不同：

- 平台 UID 小于 `AID_APP_START` 时，user build 只允许 trusted-system 发起者；
- SDK sandbox UID 会映射回所属 App UID，再读取该包的 profileable 属性；
- isolated UID 无法直接映射到来源包。Android 17 只在 trusted-system 会话且 `packages.list` 中所有包都可被 trusted initiator profile 时放行；
- 其余 UID 范围在 user build 上拒绝。

isolated process 的限制很保守。目标应用即使声明了 `<profileable>`，它的 isolated service 也可能得不到 profile；排查时应查看 trace 中的拒绝信息和 heapprofd 日志，不能只看主进程 Manifest。

### installer 过滤

`target_installed_by` 是 `HeapprofdConfig` 的可选过滤项，支持普通 installer 包名以及 `@system`、`@product`、`@null`。配置没有填写该字段时，`CanProfileAndroid()` 不检查 installer。

installer 过滤只会缩小候选集合，不会授予 profile 权限。例如，下面的约束要求目标来自 system 或 product 分区，但目标仍须通过相应的 profileable 判定：

```textproto
target_installed_by: "@system"
target_installed_by: "@product"
```

这两行适合由平台采集策略用来限制目标来源。把它们加入 shell 配置不会让未开放 shell profiling 的应用变得可采。

## 26.24.4 Manifest 应怎样声明

面向本地 shell 工具采集 release 构建时，最小声明如下：

```xml
<application
    ...>
    <profileable android:shell="true" />
</application>
```

`android:enabled` 默认是 `true`，通常不用重复写。设为 `false` 会禁止系统服务和 shell profiler。`android:shell="true"` 允许 shell 工具读取 profiling 所需的调用栈信息，不会把任意堆字节开放给第三方 App。

发布策略要根据产品威胁模型决定。调用栈、模块路径、Build ID、线程名和进程名仍可能暴露实现信息。应用若不接受终端用户通过本地调试工具采集 release 版本，应保留 `android:shell="false"`，由受信系统组件执行线上采集。

`ProfilingManager` 不要求 `android:shell="true"`。平台服务 profiling 默认允许，应用可通过 `<profileable android:enabled="false" />` 明确退出；退出后，shell 与平台服务都不能采集。Android 15–17 的普通应用若要采自己的生产 profile，应优先使用 `ProfilingManager`，不必为了远程采集向设备 shell 开放 release APK。

可通过包管理器输出核对最终 APK 的合并结果。下面的命令查看设备侧 package 信息：

```bash
adb shell dumpsys package com.example.app |
  rg -i 'profileable|debuggable'
```

输出字段会随系统版本和 OEM 改动而变化。是否可采还要用一次短会话验证，不能把单个 dumpsys 字段当作完整权限判定。

## 26.24.5 daemon、SELinux 与能力边界

Android 17 的 `heapprofd.rc` 把服务定义为 disabled，由 `traced.lazy.heapprofd=1` 或持久属性按需启动。服务以 `nobody` 用户运行，加入 `nobody` 和 `readproc` 组，并声明 `KILL`、`DAC_READ_SEARCH` capability。

同一份 rc 文件明确说明：SELinux 在 user build 上拒绝 `DAC_READ_SEARCH` 对应权限，userdebug/eng 才允许这部分访问。因此，rc 中出现 capability 不能推出生产设备可任意读取 `/proc/<pid>/mem`。

`/dev/socket/heapprofd` 的 socket mode 也不是授权结论。连接建立后，producer 会读取 peer UID、目标 UID 和 packages.list，再执行 `CanProfile()`。文件 mode、Linux capability、SELinux 和 Perfetto 会话身份共同构成边界。

## 26.24.6 进程名匹配没有 native 通配符

`HeapprofdConfig.process_cmdline` 在 Android 17 的 native producer 中做规范化后精确匹配。规范化规则包括：

- 路径只保留末尾 `/` 后面的程序名；
- 第一个 `@` 后的版本后缀被去掉；
- 比较对象是 `/proc/<pid>/cmdline` 的第一个参数。

`com.example.app*` 不会匹配 `com.example.app:remote`。Java HPROF producer 使用 glob-aware matcher，但那是 `android.java_hprof` 的实现，不能据此推导 native heapprofd 支持 glob。

多进程 App 要逐个填写完整进程名。下面的片段同时选择主进程和 remote 进程：

```textproto
process_cmdline: "com.example.app"
process_cmdline: "com.example.app:remote"
```

heapprofd 会分别为匹配到的 PID 建立状态。分析时还要按 `upid` 区分进程，不能把两个进程的 allocation 直接相加后归到主进程。

## 26.24.7 三种可执行的采集方式

### Android 15–17 使用 `ProfilingManager`

API 35 起，普通应用可以请求自己的 native heap profile。Android 官方建议通过 AndroidX `HeapProfileRequestBuilder` 构造参数；系统会限制时长、buffer、采样间隔和请求频率，调用成功也不保证每次都获得结果。

下面的 Kotlin 代码用于启动 native allocation profile，并把停止时机交给调用方：

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

调用方应在目标场景前发起请求，并在场景结束后执行 `stopSignal.cancel()`。结果通过 `ProfilingResult.getResultFilePath()` 指向应用 files 目录；失败时要记录 `getErrorCode()` 和 `getErrorMessage()`，其中包括进程级或系统级限流。

Android 17 的 Profiling 模块会校验调用 UID 与包名，然后把包名写入 `HeapprofdConfig.process_cmdline`。应用不能借此采集其他包，`:remote` 等次要进程也不会自动加入。`setTrackJavaAllocations(true)` 会把 heap 改为 `com.android.art`，它是 Java allocation profile，不是包含对象引用关系的 Java heap dump。

系统 trace 会经过通用 trace redactor；`android-17.0.0_r1` 的 `ProfilingService.needsRedaction()` 没有把 heap profile 放进该流程。heap profile 依靠目标包限制来隔离其他应用数据，返回文件中的本应用调用栈、映射与地址仍应按敏感诊断数据管理。

### 使用官方 `tools/heap_profile`

本地开发、QA 和问题复现优先使用与目标平台接近版本的 Perfetto 工具。下面的命令采集 120 秒，每 30 秒形成一个 dump，采样间隔为 4 KiB：

```bash
python3 tools/heap_profile android \
  -n com.example.app \
  -i 4096 \
  -d 120000 \
  -c 30000
```

Android 17 tag 中脚本的默认采样间隔是 4096 bytes，共享内存默认 8 MiB。命令结束后会生成 raw trace 和可选的 pprof 产物；raw trace 可直接在 Perfetto UI 中打开。

生产体验敏感的测试应考虑加 `--no-block-client`。官方脚本默认在共享 buffer 满时阻塞客户端等待空间，能保留更多数据，也可能拉长目标进程的 allocation 延迟。禁用阻塞后，buffer overrun 会提前结束该进程的 profile，分析时必须检查错误标志。

### 手写 Perfetto textproto

需要与调度、进程内存或业务 marker 同时采集时，可以直接配置 `android.heapprofd`。下面的两分钟示例沿用上一条命令的采样间隔、dump 周期和官方脚本 buffer 默认值，并附带 process stats：

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

这份配置用周期 dump 观察存活 allocation 的变化，并用 process stats 提供 RSS 侧背景。示例没有填写 `max_heapprofd_memory_kb` 和 `max_heapprofd_cpu_secs`，因为这两个 guardrail 没有跨设备通用值；生产配置应先测量 daemon 基线，再设置并验证阈值。

下面的命令把配置送入设备侧 Perfetto，并拉回 trace：

```bash
adb push heapprofd.pbtxt /data/local/tmp/heapprofd.pbtxt
adb shell perfetto --txt \
  -c /data/local/tmp/heapprofd.pbtxt \
  -o /data/misc/perfetto-traces/heapprofd.pftrace
adb pull /data/misc/perfetto-traces/heapprofd.pftrace
```

`perfetto` 会运行到 `duration_ms` 结束。若目标不满足 profileable 条件，trace 可能仍生成，但没有该进程的 heap profile；此时应同步检查 heapprofd 日志与 trace 中的 profile 错误。

## 26.24.8 参数怎样影响开销和证据质量

Android 17 的 `HeapprofdConfig` 已经把资源控制项写进 proto，部署时应理解每个阈值保护的对象：

| 参数 | Android 17 语义 | 调整方向 |
|---|---|---|
| `sampling_interval_bytes` | 平均每 N bytes 采一个样本；1 表示完整记录 | 数值增大可降开销，也更易漏掉小 allocation |
| `shmem_size_bytes` | 目标进程与 daemon 之间的 buffer；默认 8 MiB，最大 500 MiB | 突发 allocation 多时可增大 |
| `block_client` | buffer 满时是否阻塞目标进程 | 线上测量通常关闭，复现实验可按数据完整性决定 |
| `max_heapprofd_memory_kb` | heapprofd 的 `RssAnon + VmSwap` 上限 | 防止 daemon 自身占用失控 |
| `max_heapprofd_cpu_secs` | 当前 data source 启动后 daemon 累计 CPU 秒上限 | 限制 unwinding 消耗 |
| `continuous_dump_config` | 第一次 dump 延迟与后续 dump 周期 | 用于比较存活 allocation 趋势 |
| `min_anonymous_memory_kb` | 过滤匿名 RSS 与 swap 低于阈值的进程 | 全局或多目标采集时减少噪声 |
| `no_running` / `no_startup` | 只采新进程或只采已运行进程 | 按启动问题或运行期问题选择 |

memory 和 CPU guardrail 每 30 秒检查一次。阈值触发后，producer 关闭对应 data source；它们不会把 sampling interval 自动调大。需要自适应采样时，应使用 `adaptive_sampling_shmem_threshold` 和 `adaptive_sampling_max_sampling_interval_bytes`。

不要引用固定的“CPU 增加 1%”或“daemon RSS 80 MB”作为跨设备结论。开销会受 allocation 速率、采样间隔、调用栈深度、ABI、符号信息、目标进程数和 CPU 性能影响。可靠做法是在相同 workload 下分别测量无采集、目标采样间隔和更大间隔三组数据。

## 26.24.9 采集主体与部署位置

### Android 15–17 普通 App 请求自己的 profile

`ProfilingManager` 是应用在公开用户设备上采集 heap profile 的标准入口。它不要求 adb，也不把 trusted-system 身份交给应用。系统服务执行以下约束：

- Binder 调用 UID 必须与请求包名对应；
- 配置目标固定为调用方包名；
- 请求同时受单应用与全系统限流；
- DeviceConfig 可以限制参数范围或关闭 profile 类型；
- 结果复制到应用目录，由应用负责上传和删除。

这条路径适合少量、按场景触发的线上证据。它的可配置范围小于手写 Perfetto config，不能选择其他进程名、installer 过滤、连续 dump 或自定义 heapprofd guardrail。

### QA 在 user build 上采 release APK

这是第三方应用最容易复现的路径：

1. release APK 声明 `android:shell="true"`；
2. 测试设备保持 user build；
3. QA 通过 adb、Perfetto UI 或 `tools/heap_profile` 发起会话；
4. trace 离开设备前按内部数据策略处理。

这条路径验证了 release 优化和 user-build 权限，适合灰度前问题复现。它仍依赖本地调试通道，不能等同于 App 在用户手机上自行启动采集。

### 平台拥有受信采集组件

OEM 或系统产品可以让受信系统服务按设备健康信号发起 Perfetto 会话。目标 App 只需 enabled profileable，是否向 shell 开放由产品策略决定。采集服务还应负责：

- 目标包和 installer allowlist；
- 采样窗口、次数与资源预算；
- 充电、温度、前后台和低内存条件；
- trace 存储、上传、访问审计与过期删除；
- Build ID、版本号和符号文件映射。

受信发起者身份来自系统集成，不能由普通 APK 模拟。设备管理权限或远程配置本身也不自动获得该身份。

### Android 12–14 只有普通 App 权限

Android 12–14 的普通 App 没有 `ProfilingManager`，也没有公开 API 可以把自己声明为 trusted-system 会话。若产品必须在这些版本的终端用户设备上由 App 自主触发，应选择应用内 allocator instrumentation、SDK 自带 native hook、GWP-ASan 或轻量内存指标，并单独评估兼容性、性能和隐私。

把 `onTrimMemory()`、PSS 阈值或 `ApplicationExitInfo` 接到“启动 heapprofd”之前，要先确认执行采集的系统主体存在。Android 15–17 可以请求 `ProfilingManager`，但仍会受限流和并发会话约束；更低版本中的事件信号只能决定何时记录应用内证据，不能创造 Perfetto 系统权限。

## 26.24.10 如何判断 native heap 是否持续增长

单个 dump 展示该时间点上采样账目中的存活 allocation。泄漏判断至少需要两个连续 dump、可重复 workload 和场景结束后的稳定窗口。

推荐记录这些关联信息：

- 包名、PID、`upid`、进程启动时间与版本号；
- 采样间隔、dump 周期、是否命中 guardrail；
- 业务动作的起止 marker 和重复次数；
- 每个 dump 的存活 sampled bytes；
- 同期 RSS、PSS、anon RSS、swap 和 mmap 变化；
- trace 是否出现 buffer overrun、unwinding error 或 rejected process。

`heap_profile_allocation` 中正数表示分配，负数表示已经释放的样本。下面的 SQL 按 dump、进程、heap 和 callsite 汇总净存活量：

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

查询结果仍是采样估计。相同调用栈跨 dump 增长、场景退出后不回落，并且多轮复现一致，才构成较强的泄漏线索。调用栈展开与符号化可交给 Perfetto UI flamegraph 或 `traceconv`，避免用只连接 leaf frame 的 SQL 误当成完整栈。

### 三类常见误判

1. **attach 之前的存量缺失**：运行期才启动会话时，旧 allocation 没有分配事件，第一次 dump 不能代表完整 native heap；
2. **allocator cache 保留页**：应用已经 free，allocator 仍保留 arena 或 page，heap live bytes 回落而 RSS 不回落；
3. **增长来自 mmap 或图形内存**：PSS 上升但 heapprofd 平稳时，应转查 anonymous mapping、文件 mapping、DMA-BUF 与 GPU 内存。

heapprofd 证据与 PSS 证据应并排解释。两者趋势一致时，可把调用栈作为主要线索；趋势分离时，应先确定增长所在的内存类别。

## 26.24.11 失败场景排查

### `ProfilingManager` 请求被拒绝

API 35 以上的应用应先检查 `ProfilingResult`：

- `ERROR_FAILED_RATE_LIMIT_PROCESS` 表示调用应用的小时、天或周预算已经用完；
- `ERROR_FAILED_RATE_LIMIT_SYSTEM` 表示整台设备的共享预算已经用完；
- `ERROR_FAILED_PROFILING_IN_PROGRESS` 表示已有不兼容的 profiling 会话；
- `ERROR_FAILED_INVALID_REQUEST` 常见于参数越界、未知参数或 profile 类型被关闭。

限流不是“稍后立即重试”的信号。应用应记录错误分类，并等待下一次有诊断价值的场景。若进程在采集期间退出，系统会停止并保存已有结果；应用下次启动并注册全局 listener 后，系统才有机会补发通知。

### 手写 Perfetto 会话没有生成 profile

按以下顺序检查：

1. 设备是否为 Android 10 或更新版本；
2. 最终 APK 是否 debuggable，或 `<profileable android:shell="true">` 是否生效；
3. `process_cmdline` 是否与 `adb shell ps -A` 的 NAME 精确一致；
4. 目标是普通 App、SDK sandbox、isolated process 还是平台 UID；
5. 配置是否误用了 `no_running` 或 `no_startup`；
6. `sampling_interval_bytes` 是否为非零值；
7. heapprofd 和 traced 日志是否报告 not profileable、signal 失败或 client 连接失败。

### profile 提前结束

共享 buffer 跟不上 allocation 速率时，client 会出现 buffer overrun。可增大 sampling interval 或 `shmem_size_bytes`，也可在可控实验中启用 `block_client`。线上场景不要为了保住 trace 而无条件阻塞高频 allocation 线程。

memory 或 CPU guardrail 命中也会关闭 data source。检查阈值时要区分 daemon 总开销和目标进程开销；`max_heapprofd_memory_kb` 不限制目标 App 的 native heap。

### 栈缺帧或符号缺失

常见原因包括缺少 Build ID 对应符号、栈展开信息被裁剪、JIT/AOT frame 缺少可用元数据、相同代码折叠，以及 trace 与符号包版本不一致。符号服务应以 APK version、ABI、Build ID 和系统 build fingerprint 定位文件，不能只按 so 文件名匹配。

## 26.24.12 与其他工具的职责分工

| 工具 | 主要证据 | 适用问题 | 主要限制 |
|---|---|---|---|
| heapprofd | 采样的分配/释放调用栈 | native heap 增长来源 | 不覆盖全部 mmap、图形内存和会话前存量 |
| Perfetto process stats / meminfo | RSS、PSS、内存类别 | 进程总量和类别变化 | 没有 malloc callsite |
| GWP-ASan | 被采样 allocation 的 UAF、double free、越界 | native 内存安全错误 | 不负责统计泄漏增长 |
| `libmemunreachable` | 某时刻的不可达 native allocation | 平台调试中的 reachability 快照 | 平台内部接口、暂停与权限成本 |
| malloc debug | allocator 检查、回溯与泄漏信息 | 可控 debug 环境 | 开销高，发布环境受限 |
| 应用内 native hook | App 自己定义的事件和调用栈 | 无系统采集权限的长期监控 | 兼容 allocator、递归、信号安全和版本维护成本高 |

`libmemunreachable` 不是稳定 NDK API。通过 `dlopen` 私有系统库和硬编码 C++ 符号调用会受 linker namespace、符号变化和 SELinux 限制，不应作为通用的生产方案。

Scudo 的 error callback 用于处理 allocator 检出的错误，不是通用 allocation 事件回调。需要记录自定义 heap 时，Perfetto 提供 `AHeapProfile_registerHeap` 一类接口，使用前仍要确认目标平台提供的头文件、ABI 和集成方式。

## 26.24.13 数据安全与归档

heapprofd 不复制任意 heap payload，但 trace 仍可能包含：

- 进程名、线程名与 UID 关联；
- 映射路径、模块名、Build ID 和地址；
- native 与可展开的 Java 调用栈；
- trace 中同时开启的其他 data source 数据。

线上采集策略应把完整 trace 当作诊断数据管理。建议保留最少 data source、限制目标包和时长、设备侧加密存储、上传链路鉴权、服务端按角色授权，并设置明确的删除期限。

符号化宜在受控环境中按 Build ID 完成。只上传 `heap_profile_allocation` 表会丢失完整调用栈、错误标志和会话上下文，不能当作默认的“脱敏等价物”。若要做裁剪，应定义可复现的 trace-to-report 转换格式，并保留采样参数、版本和错误元数据。

## 26.24.14 发布前检查表

- [ ] 源码与配置以 `android-17.0.0_r1` 为基准；
- [ ] release APK 的 profileable 合并结果已在 user build 验证；
- [ ] shell 会话和 trusted-system 会话的权限主体没有混写；
- [ ] Android 15–17 的普通 App 优先使用 `ProfilingManager`，并处理限流与结果文件；
- [ ] 所有 native 进程名均为精确值，没有使用 `*`；
- [ ] sampling interval、shmem、dump 周期和 guardrail 有设备基线；
- [ ] 线上配置不会因 `block_client` 放大业务延迟；
- [ ] trace 中检查了 rejected、buffer overrun、unwinding 和 guardrail 状态；
- [ ] 泄漏判断使用连续 dump、稳定窗口和重复 workload；
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
- [Android Developers：App-driven profiling](https://developer.android.com/topic/performance/tracing/profiling-manager/how-to-capture)
- [AndroidX：`HeapProfileRequestBuilder`](https://developer.android.com/reference/androidx/core/os/HeapProfileRequestBuilder)
- [AOSP android-17.0.0_r1：Profiling heap profile 配置](https://android.googlesource.com/platform/packages/modules/Profiling/+/refs/tags/android-17.0.0_r1/service/java/com/android/os/profiling/Configs.java)
- [AOSP android-17.0.0_r1：ProfilingService 权限、限流与结果处理](https://android.googlesource.com/platform/packages/modules/Profiling/+/refs/tags/android-17.0.0_r1/service/java/com/android/os/profiling/ProfilingService.java)
