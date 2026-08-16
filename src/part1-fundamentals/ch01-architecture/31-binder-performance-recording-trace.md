---
title: "Android 17 Binder 可观测性：Perfetto、AIDL Trace、内核快照与事务录制"
chapter: "1.31"
section: "1.31"
status: finalized
applicable_versions: "Android 17 (API 37)"
last_verified: "2026-08-16"
last_verified_against: "AOSP android-17.0.0_r1 + kernel android17-6.18-2026-06_r6"
confidence: high
sources:
  - type: aosp
    path: "frameworks/native/libs/binder/Binder.cpp"
  - type: aosp
    path: "frameworks/base/core/java/android/os/Binder.java"
  - type: aosp
    path: "frameworks/base/core/jni/android_util_Binder.cpp"
  - type: aosp
    path: "frameworks/native/libs/binder/IPCThreadState.cpp"
  - type: aosp
    path: "frameworks/native/libs/binder/ProcessState.cpp"
  - type: aosp
    path: "frameworks/native/libs/binder/RecordedTransaction.cpp"
  - type: aosp
    path: "frameworks/native/libs/binder/include/binder/RecordedTransaction.h"
  - type: aosp
    path: "frameworks/native/libs/binder/include/binder/Trace.h"
  - type: aosp
    path: "system/tools/aidl/generate_cpp.cpp"
  - type: aosp
    path: "system/tools/aidl/generate_java_binder.cpp"
  - type: aosp
    path: "external/perfetto/src/trace_processor/perfetto_sql/stdlib/android/binder.sql"
  - type: kernel
    path: "include/uapi/linux/android/binder.h (android17-6.18-2026-06_r6)"
  - type: kernel
    path: "drivers/android/binder.c (android17-6.18-2026-06_r6)"
  - type: kernel
    path: "drivers/android/binderfs.c (android17-6.18-2026-06_r6)"
  - type: kernel
    path: "drivers/android/binder_trace.h (android17-6.18-2026-06_r6)"
tags: [binder, ipc, performance-monitoring, tracing, perfetto, aidl, recording]
related_chapters: ["1.4", "1.29", "1.30", "1.38", "13.5"]
last_consolidated_at: "2026-08-11"
consolidated_from:
  - "src/part1-fundamentals/ch01-architecture/01.32-android17-binder-ipc-performance-monitoring.md"
---

# 1.31 Android 17 Binder 可观测性：Perfetto、AIDL Trace、内核快照与事务录制

Binder 可观测性由多套机制组成。分析等待时间、查询冻结状态、读取失败原因、查看 AIDL 方法名和录制 Parcel 内容，各自依赖不同的实现层。混用这些机制会导致两类错误：把状态位当作事务计数，或把调试录制当成可常驻的线上监控。

以下分析以 Android 17 / API 37、AOSP `android-17.0.0_r1` 和内核 `android17-6.18-2026-06_r6` 为准，说明各项能力提供的证据、调用边界及其与 Perfetto 结果的对应关系。

## 一、按证据类型选择工具

| 需要回答的问题 | 首选机制 | 能看到什么 | 看不到什么 |
|---|---|---|---|
| 调用在哪一端等待 | Perfetto Binder flow（跨进程流关联）与线程状态 | 客户端 / 服务端时间、调度和阻塞状态 | Parcel 业务内容 |
| 这次 AIDL 调的是哪个方法 | `ATRACE_TAG_AIDL` 时间片（slice） | 接口、方法、客户端或服务端时间片 | 参数值、返回值 |
| 冻结期间是否收到事务 | `BINDER_GET_FROZEN_INFO` | 同步事务状态位、异步事务状态位 | 事务次数和耗时 |
| 失败来自哪个驱动命令 | `BINDER_GET_EXTENDED_ERROR` | 失败 ID、Binder 返回命令、负 errno（Linux 错误号） | 跨线程历史错误 |
| 发送端是否触发 `oneway` 嫌疑检测 | `BR_ONEWAY_SPAM_SUSPECT` | 当前发送线程收到告警并打印调用栈 | 接收端队列的通用统计报表 |
| 请求和回复的 Parcel 是什么 | `RecordedTransaction` | 接口名、事务码（code）、标志位（flags）、状态、请求 / 回复数据 | 稳定文件协议、低扰动线上采集 |

这些能力没有“粗粒度到细粒度”的固定层级，也不是 Android 17 同时新增。当前版本中的源码入口只能证明 Android 17 的行为，不能反推引入版本。

## 二、binderfs 功能文件表示能力，不表示运行状态

binderfs 是 Binder 驱动导出的专用文件系统，`features` 目录中的文件用于声明驱动能力。Android 17 的 `ProcessState::isDriverFeatureEnabled()` 只探测三项能力：

```cpp
#define DRIVER_FEATURES_PATH "/dev/binderfs/features/"

bool ProcessState::isDriverFeatureEnabled(const DriverFeature feature) {
    if (feature == DriverFeature::ONEWAY_SPAM_DETECTION) {
        static bool enabled = readDriverFeatureFile(
                DRIVER_FEATURES_PATH "oneway_spam_detection");
        return enabled;
    }
    if (feature == DriverFeature::EXTENDED_ERROR) {
        static bool enabled = readDriverFeatureFile(
                DRIVER_FEATURES_PATH "extended_error");
        return enabled;
    }
    if (feature == DriverFeature::FREEZE_NOTIFICATION) {
        static bool enabled = readDriverFeatureFile(
                DRIVER_FEATURES_PATH "freeze_notification");
        return enabled;
    }
    return false;
}
```

每项结果以函数内的 `static bool` 缓存，因此同一进程不会在每次事务中重复打开功能文件。`readDriverFeatureFile()` 只读取首字符并判断是否为 `'1'`。

内核 `binderfs.c` 在 Android 17 的 6.18 分支中创建四个文件：

- `oneway_spam_detection`
- `extended_error`
- `freeze_notification`
- `transaction_report`

第四项存在于当前内核，但 `ProcessState::DriverFeature` 没有对应枚举，不能将它视为 libbinder 的通用能力探测接口。

还要区分 `freeze_notification` 与冻结 ioctl（用户态控制驱动的系统调用）。前者表示客户端能否通过 `BC_REQUEST_FREEZE_NOTIFICATION` 订阅远端 Binder 的冻结状态变化；`IPCThreadState::freeze()` 和 `getProcessFreezeInfo()` 直接调用 `BINDER_FREEZE`、`BINDER_GET_FROZEN_INFO`，不会预先读取这个功能文件。功能文件只声明驱动是否实现该项协议，不包含调用量、队列长度或延迟。

## 三、冻结查询返回状态位，不是事务计数

### 3.1 `sync_recv` 与 `async_recv` 的含义

framework 的封装只做参数传递：调用方传入进程 ID（PID），驱动填充两个 `uint32_t` 字段。

```cpp
status_t IPCThreadState::getProcessFreezeInfo(
        pid_t pid, uint32_t* syncReceived, uint32_t* asyncReceived) {
    binder_frozen_status_info info = {};
    info.pid = pid;
    if (ioctl(self()->mProcess->mDriverFD,
              BINDER_GET_FROZEN_INFO, &info) < 0) {
        return -errno;
    }
    *syncReceived = info.sync_recv;
    *asyncReceived = info.async_recv;
    return NO_ERROR;
}
```

字段语义由内核 UAPI（用户态和内核态共享的接口定义）明确规定：

| 字段 | 位 | Android 17 含义 |
|---|---:|---|
| `sync_recv` | bit 0 | 进程冻结后收到过同步事务 |
| `sync_recv` | bit 1 | 冻结过程中出现等待回复的同步事务 |
| `async_recv` | bit 0 | 进程自上次进入冻结状态后收到过异步事务 |

内核在目标进程已冻结时使用按位或记录事件：

```c
if (proc->is_frozen) {
    frozen = true;
    proc->sync_recv |= !oneway;
    proc->async_recv |= oneway;
}
```

查询时，驱动又把 `binder_txns_pending_ilocked()` 的布尔结果放进 `sync_recv` 的 bit 1。`sync_recv == 3` 表示两个状态位都为 1，不代表发生了三次同步事务；`async_recv` 也不能作为单调增长计数器。

### 3.2 `timeout_ms` 只控制等待排空

`freeze(pid, true, timeout_ms)` 先把目标进程标记为冻结，随后最多等待 `outstanding_txns` 清空。驱动还会检查正在等待回复的事务；仍有待处理项时返回 `-EAGAIN`，并撤销本次冻结状态。

```c
target_proc->is_frozen = true;

if (info->timeout_ms > 0)
    ret = wait_event_interruptible_timeout(
        target_proc->freeze_wait,
        !target_proc->outstanding_txns,
        msecs_to_jiffies(info->timeout_ms));

if (ret >= 0 && binder_txns_pending_ilocked(target_proc))
    ret = -EAGAIN;
```

因此，`timeout_ms` 是等待旧事务排空的期限，不是“冻结多长时间”。冻结成功后持续到调用 `freeze(pid, false, ...)`；解冻路径同时清除 `sync_recv` 和 `async_recv`。

冻结后的新同步事务会失败，并向发送端返回冻结相关错误。`oneway`（单向）事务可进入冻结进程的待处理队列，发送端还可能收到 `BR_TRANSACTION_PENDING_FROZEN`。分析长时间的异步 Binder flow 时，冻结是候选原因之一，但当前内核没有名为 `binder_freeze` 的 Binder tracepoint（静态跟踪点），不能用这个不存在的事件标记区间。

### 3.3 冻结通知是另一条协议

客户端若持有某个远端 Binder 句柄（handle），可以通过 `addFrozenStateChangeCallback()` 请求冻结通知。libbinder 先检查 `freeze_notification` 功能文件，再发送 `BC_REQUEST_FREEZE_NOTIFICATION`；内核以 `BR_FROZEN_BINDER` 回传 `is_frozen` 与用于关联回调对象的 `cookie`。

这条协议用于判断持有的远端 Binder 是否发生冻结状态变化。`BINDER_GET_FROZEN_INFO` 则按 PID 查询冻结期间是否收到过事务。两者的对象、数据结构和使用目的不同。

以上接口属于平台原生 Binder 组件，不是 Android SDK 提供给普通应用的健康检查 API。能够打开相应 Binder 设备，也不代表产品的 SELinux 策略和调用方身份允许将它们用于任意进程管理。

## 四、扩展错误是线程级的一次性信息

一次事务失败后，`IPCThreadState::waitForResponse()` 会调用 `logExtendedError()`。它确认 `extended_error` 功能文件可用后，再通过 `BINDER_GET_EXTENDED_ERROR` 读取：

```c
struct binder_extended_error {
    __u32 id;
    __u32 command;
    __s32 param;
};
```

- `id`：失败操作的驱动标识；
- `command`：`BR_FAILED_REPLY` 等 Binder 返回命令；
- `param`：负 errno 错误号。

内核把错误保存在当前 `binder_thread` 中。`BINDER_GET_EXTENDED_ERROR` 复制结果后立即把该线程的记录重置为 `BR_OK`。它不是进程级错误历史，也不适合跨线程延后查询。

Android 17 的 `logExtendedError()` 只为 `ENOSPC` 增加一段解释：Binder 缓冲区已满，事务过多或过大。其他 errno 仍使用通用错误字符串。`ENOSPC` 也不能单独证明“这一条 Parcel 超过固定 1 MiB”；同一接收进程的并发同步 / 异步分配都会消耗 Binder 映射与异步预算，详见 [1.30 Android 17 Binder Transaction Buffer](30-binder-transaction-buffer-performance.md)。

## 五、`oneway` 嫌疑告警发生在发送端

`ProcessState::open_driver()` 在打开 Binder 驱动后，默认执行 `BINDER_ENABLE_ONEWAY_SPAM_DETECTION`。当驱动把某次事务完成工作标记为 `BINDER_WORK_TRANSACTION_ONEWAY_SPAM_SUSPECT` 时，发送端线程收到 `BR_ONEWAY_SPAM_SUSPECT`：

```cpp
case BR_ONEWAY_SPAM_SUSPECT:
    ALOGE("Process seems to be sending too many oneway calls.");
    CallStack::logStack("oneway spamming",
                        CallStack::getCurrent().get(),
                        ANDROID_LOG_ERROR);
    [[fallthrough]];
case BR_TRANSACTION_COMPLETE:
    // complete the sender-side transaction
```

这里打印的是正在发送 `oneway` 的线程调用栈。告警不由接收端的 `BBinder::onTransact()` 生成，也不表示驱动已经对调用方实施通用限流。定位时应回到发送栈，再用 Perfetto 的异步 Binder flow 核对接口、频率和目标进程。

## 六、AIDL Trace 提供方法名，不提供 Parcel 内容

这里的 AIDL Trace 指方法级时间轨迹：它给切片命名，方便把 Binder 活动对应到接口方法，但不会记录方法参数。

### 6.1 libbinder 的服务端切片

`BBinder::transact()` 每次进入服务端本地 Binder 对象时，先检查 `ATRACE_TAG_AIDL`：

```cpp
bool tracingEnabled = get_trace_enabled_tags() & ATRACE_TAG_AIDL;
if (tracingEnabled) {
    tracingEnabled = startTrace(code);
}

scope_guard guard = make_scope_guard([&]() {
    if (tracingEnabled) trace_end(ATRACE_TAG_AIDL);
});
```

`startTrace()` 通过接口描述符、事务码（transaction code）与后端类型组成名称，例如：

```text
AIDL::cpp::android.foo.IExample::doWork::server
```

C++ AIDL 生成器会把事务码到方法名的映射交给 `BBinder::setTransactionCodeMap()`。Java Binder 由生成的 `getTransactionName()` 提供方法名。映射缺失或事务码不在用户方法范围时，时间片名称可能退化为 `UNKNOWN_CODE_<n>`。

### 6.2 生成代码还可以增加客户端和服务端切片

C++ 后端在 `options.GenTraces()` 开启时，会分别在代理方法和服务端 Stub 分发代码中生成 `ScopedTrace`：

```cpp
::android::binder::ScopedTrace trace(
    ATRACE_TAG_AIDL,
    "AIDL::cpp::IExample::doWork::cppClient");
```

服务端对应名称以 `cppServer` 结尾。它们与 `BBinder::transact()` 的通用服务端时间片来自不同代码位置，因此同一线程轨道中可能出现嵌套时间片。遇到名称相近的 AIDL 时间片时，应检查名称后缀和所在进程 / 线程，不能按时间片数量推算调用次数。

源码没有给出“关闭时固定 10 ns”或“开启时固定多少微秒”的保证。关闭跟踪标签会绕过名称构造和 `trace_begin()`；开启后的成本与生成代码、名称处理、轨迹缓冲区和调用频率有关，应在目标设备上测量。

### 6.3 最小 Perfetto 配置

下面的配置同时采集 AIDL 方法切片、Binder flow 与线程调度。缓冲区大小和时长应按复现窗口调整。

```protobuf
buffers {
  size_kb: 32768
  fill_policy: RING_BUFFER
}

data_sources {
  config {
    name: "linux.ftrace"
    ftrace_config {
      atrace_categories: "aidl"
      ftrace_events: "binder/binder_transaction"
      ftrace_events: "binder/binder_transaction_received"
      ftrace_events: "binder/binder_transaction_alloc_buf"
      ftrace_events: "binder/binder_txn_latency_free"
      ftrace_events: "sched/sched_switch"
      ftrace_events: "sched/sched_waking"
    }
  }
}

duration_ms: 10000
```

`ATRACE_TAG_AIDL` 只提供方法时间片。跨进程连线来自 Binder ftrace（内核跟踪框架）事件，线程迟迟没有运行的原因则依赖调度事件。只打开 `aidl` 分类，不能替代 Binder 驱动事件与 `sched` 调度数据。

## 七、API 37 的 Perfetto 表没有 `dispatch_dur`

`android-17.0.0_r1` 中 `android_binder_txns` 的主要字段包括：

- `client_ts`、`client_dur`：客户端 Binder 时间片的起点与墙钟时长；
- `server_ts`、`server_dur`：服务端 Binder 时间片的起点与墙钟时长；
- `client_process`、`server_process` 及两端进程 ID（PID）和线程 ID（TID）；
- `aidl_name`、`interface`、`method_name`；
- `is_sync`；
- 去除系统挂起（suspend）区间后的 `client_monotonic_dur`、`server_monotonic_dur`。

表中没有 `dispatch_dur`。下面的查询把“服务端切片起点相对客户端切片起点的差值”显式命名为 `server_start_delay_ms`：

```sql
INCLUDE PERFETTO MODULE android.binder;

SELECT
  client_process,
  server_process,
  aidl_name,
  client_dur / 1e6 AS client_ms,
  server_dur / 1e6 AS server_ms,
  (server_ts - client_ts) / 1e6 AS server_start_delay_ms
FROM android_binder_txns
WHERE is_sync = 1
ORDER BY client_dur DESC
LIMIT 50;
```

这个差值适合筛选服务端开始较晚的事务，但不能直接命名为纯排队时间：它还可能包含客户端到驱动、驱动选择线程以及调度唤醒等区间。`client_dur - server_dur` 同样混合了内核传输、等待、回复和调度开销。还需查看 `android_sync_binder_thread_state_by_txn` 或两端线程轨道，区分 runnable 延迟（线程已就绪但尚未获得 CPU）、睡眠和锁阻塞。

## 八、`binder_txn_latency_free` 记录对象释放时刻

当前内核的 `binder_txn_latency_free` tracepoint 包含：

- 事务 `debug_id`；
- `from_proc/from_thread` 与 `to_proc/to_thread`；
- `code`、`flags`。

触发点位于 `binder_free_transaction()`。它说明某个内核 `binder_transaction` 对象何时被释放，可借助 `debug_id` 与 `binder_transaction` 事件关联。两事件的时间差是该内核对象的存活区间，不等于应用看到的端到端调用耗时：服务端何时释放接收缓冲区、错误路径以及 `oneway` 处理方式都会影响对象寿命。

当前 `binder_trace.h` 有 `binder_transaction` 和 `binder_transaction_received`，回复仍通过 `binder_transaction` 的 `reply` 字段表示；不存在名为 `binder_reply` 的 tracepoint，也不存在 `binder_freeze` tracepoint。诊断脚本应检查设备的 `/sys/kernel/tracing/events/binder/`，不要把界面中的 `binder reply` 时间片名称当成内核事件名。

## 九、debugfs 只能提供现场快照

debugfs（内核调试文件系统）路径 `/sys/kernel/debug/binder/`（或产品映射的对应调试目录）里的 `state`、`stats`、`transactions`、`transaction_log`、`failed_transaction_log` 和 `proc/<pid>`，用于查看当前对象、线程、buffer 与有限的事务记录。它们不是时序数据库：两次读取之间已经完成并释放的事务可能完全看不到，读取本身也无法恢复 runnable 延迟、锁等待或 CPU 执行区间。

逐进程文件适合回答“目标进程当下有多少 Binder 线程、哪些线程在等待、是否存在未释放 buffer、`free async space` 是否异常”；Perfetto 适合回答“事务何时发送、服务端何时开始、线程为何没有运行”。binderfs 的 `features/*` 是第三类信息，只表示驱动是否支持某项协议，不能当作运行状态或调用计数。

出现缓冲区压力时，应把 `binder_transaction_alloc_buf` 的 `data_size`、`offsets_size`、`extra_buffers_size` 与目标进程的并发事务、`free async space`、`oneway` spam 告警一起看。Java 层会根据事务失败时的上下文推测并报告 `TransactionTooLargeException`，它不是驱动用于表示“这一笔精确超过 1 MiB”的专用错误。

## 十、Parcel 与应用侧观测边界

Java `Parcel` 有对象池，带明确类型的 Parcelable 由生成代码或显式代码写入字段；原生 `Parcel` 会按实现策略扩容。无论使用 `byte[]`、`Bundle` 还是 Parcelable，大块数据都不会自动变成共享内存。需要传输图片、模型或批量二进制时，应使用文件描述符（FD）、共享内存或流式协议，只在 Parcel 中传控制信息和句柄。

应用侧的耗时埋点可以定位某个接口的分位数和失败率，但只能看到调用边界，不能独立解释 Binder 驱动、服务端排队与调度。采集时至少记录接口 / 方法、同步或 `oneway`、调用线程、目标进程、Parcel 估算大小和超时 / 错误类型；采样和聚合必须限制字段取值组合的数量（基数），不能在线上记录 Parcel 原文。

## 十一、RecordedTransaction 适合受控复现，不适合常驻监控

### 11.1 启用条件

`RecordedTransaction` 同时受三个条件限制：

1. libbinder 编译时定义 `BINDER_ENABLE_RECORDING`，否则 `kEnableRecording` 为 `false`；
2. 使用内核 Binder；
3. 发起 `START_RECORDING_TRANSACTION` / `STOP_RECORDING_TRANSACTION` 的调用者 UID 为 root（超级用户）。

`startRecordingTransactions(const Parcel& data)` 从控制事务的 `Parcel` 中读取一个由 `unique_fd` 管理的文件描述符。同一个 `BBinder` 一次只允许一场录制。仅凭系统是 `userdebug` 构建不能确认该能力可用，还要检查目标产品的 libbinder 编译参数。

### 11.2 它记录服务端收到的事务

录制代码位于 `BBinder::transact()`，在 `onTransact()` 返回后执行。它保存：

- `getInterfaceDescriptor()`；
- 事务 `code` 与 `flags`；
- `onTransact()` 返回状态；
- 请求 Parcel 的数据区与对象偏移；
- 回复 Parcel 的数据区；
- 调用 `timespec_get()` 时取得的时间戳。

时间戳在服务端处理完成后采集，不能当作事务开始时间。AOSP 的 `BpBinder` 发送路径没有与之对称的客户端录制入口，因此“客户端和服务端各打开一次就得到端到端录制”并不成立。端到端时间仍应由 Perfetto 的 Binder flow 解释。

### 11.3 文件格式与风险

Android 17 的写入顺序是：

```text
Header
Interface Name
Sent Parcel
Reply Parcel
Sent Parcel Object Offsets
End
```

`TransactionHeader` 只包含 `code`、`flags`、返回状态、RPC 版本标记、秒 / 纳秒时间戳和保留字段；接口名位于独立数据块（chunk）中。每个数据块由 `uint32_t chunkType`、`uint32_t dataSize`、数据、0～7 字节补齐和 64 位 XOR 校验值组成。未知数据块可以校验后跳过；同类数据块重复出现时，后读到的值会覆盖前值。

源码明确标记该格式仍在持续开发，不能视为稳定协议。录制内容可能包含账号标识、令牌、路径和业务数据；同时，序列化与文件写入发生在事务返回路径并受录制锁保护，会改变被测路径的时延。没有源码依据支持固定的 `100 ns–1 us` 开销。它适用于实验设备上的协议复现和离线检查，不应用于生产设备的常驻采集。

## 十二、一个可复用的诊断顺序

### 12.1 慢事务

1. 用 Perfetto 抓 `binder`、`aidl` 与 `sched`；
2. 从 `android_binder_txns` 找出长 `client_dur`；
3. 比较 `server_ts` 与 `client_ts`，再检查客户端和服务端线程状态；
4. AIDL 时间片有方法名时定位到接口；没有名称时保留事务码和两端 PID / TID，回到服务定义核对；
5. 不用 `binder_txn_latency_free` 的对象寿命替代端到端耗时。

### 12.2 冻结相关事务

1. 由负责进程冻结的系统组件记录冻结/解冻操作；
2. 把 `sync_recv` 当位图解析，禁止累计求和；
3. 需要观察句柄对应的远端状态变化时使用冻结通知；
4. 用 Binder 异步 flow 判断 `oneway` 是在冻结期间等待，还是服务端线程繁忙。

### 12.3 失败与内容复现

1. 事务失败后在同一 Binder 线程读取扩展错误；
2. `ENOSPC` 先检查接收进程的缓冲区占用、大事务和并发异步事务；
3. 只有在系统轨迹与日志无法解释协议内容、设备可控且 libbinder 编译开关已打开时，才使用 `RecordedTransaction`；
4. 录制文件按敏感数据管理，完成分析后清理。

## 十三、源码锚点

- AOSP `android-17.0.0_r1`
  - `frameworks/native/libs/binder/Binder.cpp`：AIDL 服务端轨迹、录制权限与写入位置
  - `frameworks/base/core/java/android/os/Binder.java`、`frameworks/base/core/jni/android_util_Binder.cpp`：Java Binder 的事务码命名回调与 `UNKNOWN_CODE_<n>` 回退
  - `frameworks/native/libs/binder/IPCThreadState.cpp`：冻结 ioctl、扩展错误、oneway 告警、冻结通知
  - `frameworks/native/libs/binder/ProcessState.cpp`：binderfs 功能探测与默认 oneway 嫌疑检测
  - `frameworks/native/libs/binder/RecordedTransaction.cpp`、`include/binder/RecordedTransaction.h`：数据块格式与不稳定性声明
  - `system/tools/aidl/generate_cpp.cpp`：C++ 客户端 / 服务端 AIDL 轨迹生成
  - `system/tools/aidl/generate_java_binder.cpp`：Java AIDL 生成的 `getTransactionName()` 映射
  - `external/perfetto/src/trace_processor/perfetto_sql/stdlib/android/binder.sql`：`android_binder_txns` 字段定义
- 内核 `android17-6.18-2026-06_r6`
  - `include/uapi/linux/android/binder.h`：冻结状态位与 ioctl UAPI
  - `drivers/android/binder.c`：冻结、扩展错误、oneway 嫌疑告警和事务释放
  - `drivers/android/binderfs.c`：功能文件
  - `drivers/android/binder_trace.h`：Binder tracepoint 字段

以上结论均以这两个版本锚点为准。迁移到旧系统、GKI（通用内核镜像）分支或厂商分支时，应重新核对功能文件、tracepoint 列表、SELinux 策略和 libbinder 编译选项。
