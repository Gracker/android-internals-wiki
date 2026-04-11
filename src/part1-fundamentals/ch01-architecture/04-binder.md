---
title: "Binder IPC 机制与性能影响"
chapter: "1.4"
section: "ch01-architecture"
status: ready-for-review
reviewed_date: "2026-04-10"
reviewed_by: "openclaw-task6"
applicable_versions: "Android 8 (API 26) - Android 16 (API 36)"
drafted_date: "2026-04-10"
drafted_by: "openclaw-task2a"
last_verified: "2026-03-31"
last_verified_against: "AOSP android-16.0.0_r1, 官方文档"
confidence: medium
sources:
  - type: blog
    path: "Personal-Knowlodge/source/Android-Systrace-Binder.md"
  - type: blog
    path: "Personal-Knowlodge/source/Android-Perfetto-10-Binder.md"
  - type: blog
    path: "Personal-Knowlodge/source/2026-03-06_wechat_Binder驱动中的流程详解.md"
  - type: official
    path: "developer.android.com/reference/android/os/IBinder"
  - type: official
    path: "developer.android.com/guide/components/aidl"
tags: [binder, ipc, aidl, oneway, 线程池, 锁竞争, perfetto]
related_chapters: ["1.1", "2.5", "7.2", "8.2", "9.1"]
pipeline_stage: task6_pending
task6_state: pending
task9_state: pending
task2b_state: idle
---

# Binder IPC 机制与性能影响

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 Binder 架构：Client → Proxy → Binder Driver → Stub → Server，一次拷贝的实现原理（mmap）
- 🔹 AIDL 接口定义与代码生成：Proxy/Stub 模式
- 🔹 Binder 线程池模型：默认最大 15 个 binder 线程（可配置）、线程池动态管理、线程耗尽对 ANR 的影响
- 🔹 同步 Binder 调用的性能开销：上下文切换、调度延迟、数据序列化
- 🔹 oneway 异步调用 vs 同步调用的性能差异与适用场景
- 🔹 Binder 调用在 Perfetto/Systrace 中的表现：binder transaction、binder reply

### 扩展（可选深入）

- 🔸 Binder 与传统 IPC（Socket、管道、共享内存）的性能对比
- 🔸 Binder 调用频率与系统负载：如何在 Trace 中识别 binder 风暴
- 🔸 AIDL 与 HIDL 的区别及演进（HAL 层 Binder 化）

### OpenClaw 加工指引

> **锚点**是最低覆盖要求，加工时必须逐条落实并标注验证结果。
> **扩展**视素材丰富程度选择性深入。
> 如果从 Obsidian 素材或 AOSP 源码中发现大纲未列出但与本节强相关的知识点，
> 可**就地插入**最相关的锚点之后，并用 `[自动发现]` 标注，方便后续 review。
> 锚点内容需 L1/L2 验证，扩展内容至少 L2 验证，自动发现内容至少标注来源。
<!-- outline-end -->

## 为什么要了解 Binder

如果你做过 Android 性能优化，你大概率在 Perfetto 里见过这样的场景：主线程一段 `doFrame` 执行中间，突然出现一个 10ms 甚至 30ms 的 Sleeping 状态——没有 Java 代码在跑，CPU 也没在忙，线程就是停在那儿。当你放大去看 `thread_state`，`blocked_function` 显示的是 `binder_thread_read`。这意味着你的主线程发起了一次跨进程调用，正在等对方回复。

这不是偶然。Android 的多进程架构决定了几乎所有系统服务调用都走 Binder：启动 Activity、获取窗口信息、查询定位、读写设置……一个典型的冷启动流程，主线程可能发起 30-50 次同步 Binder 调用。其中任何一次耗时过长，都会直接表现为启动变慢或卡顿。更严重的是，如果调用端是主线程且超时，就会触发 ANR。

理解 Binder 的工作原理和在 Perfetto 中的表现形式，意味着你能回答这些问题：主线程那段 Sleeping 时间到底在等谁？是服务端处理慢、还是排队等线程、还是锁竞争？是同步调用还是 oneway？答案不同，优化方向完全不同。

[已验证: 官方文档 developer.android.com/reference/android/os/IBinder, 来源: obsidian/Personal-Knowlodge/source/Android-Perfetto-10-Binder.md]

## Binder 的核心架构

### 一次调用经历了什么

Binder 的设计目标是让跨进程调用看起来像本地函数调用。当你写 `windowManager.addView()` 时，实际发生的事情远比一行代码复杂。

整个调用链可以简化为五个角色和四个步骤：

**五个角色：** Client（调用方进程中的线程）→ **Proxy**（AIDL 生成的代理类）→ **Binder Driver**（`/dev/binder` 内核模块）→ **Stub**（AIDL 生成的桩类）→ **Server**（服务方进程中的 Binder 线程）。

**四个步骤：**

1. Client 线程通过 Proxy 将参数序列化到 `Parcel`，调用 `IBinder.transact()`。
2. Binder Driver 接管，将数据从 Client 进程的地址空间拷贝到 Server 进程可以访问的共享内存区域，然后唤醒一个空闲的 Server 端 Binder 线程。
3. Server 端的 Binder 线程被唤醒，Stub 类从 `Parcel` 反序列化参数，调用真正的实现代码，将结果序列化回 `Parcel`。
4. Binder Driver 将结果数据传回 Client，唤醒等待中的 Client 线程。

[已验证: AOSP 源码, frameworks/native/libs/binder/BpBinder.cpp] [来源: obsidian/Personal-Knowlodge/source/2026-03-06_wechat_Binder驱动中的流程详解.md]

### 为什么 Binder 只需要"一次拷贝"

传统 IPC 机制（管道、Socket）传输数据需要至少两次拷贝：从发送方用户空间到内核空间一次，从内核空间到接收方用户空间又一次。Binder 通过 `mmap()` 把这个过程压缩到了一次。

工作原理是这样的：每个使用 Binder 的进程在初始化时，会对 `/dev/binder` 调用 `mmap()`，在用户空间映射一块内存（默认约 1MB）。这块内存同时被内核的 Binder Driver 映射。当 Client 发送数据时，Binder Driver 只需要把 `Parcel` 数据拷贝到这块共享内存区域，Server 端进程就能直接读到它——不需要再从内核拷贝到 Server 的用户空间。

严格地说，这不是真正的"零拷贝"，而是"单次拷贝"（single copy）。发送方仍然需要从自己的用户空间拷贝到共享区域，但接收方不需要再拷贝一次。Android 8（Oreo）进一步引入了 scatter-gather 优化，将原来需要三次拷贝的流程减少到一次。

这个 mmap 缓冲区的大小限制是 Binder 的一个重要约束：每个进程的所有 Binder 事务共享这块约 1MB 的缓冲区。如果你一次性传输一个大 Bitmap 或一个超长列表，就可能撞到 `TransactionTooLargeException`。传输大数据应该使用 `SharedMemory`（基于 ashmem/memfd）或 `ParcelFileDescriptor`，只通过 Binder 传递一个文件描述符句柄。

[已验证: 官方文档, developer.android.com/reference/android/os/TransactionTooLargeException] [已验证: AOSP, frameworks/native/libs/binder/ProcessState.cpp 中 mmap 调用]

### AIDL：让跨进程调用看起来像本地调用

AIDL（Android Interface Definition Language）是 Binder 在应用层的使用接口。你写一个 `.aidl` 文件定义接口，编译器帮你生成两个类：`Stub`（服务端基类）和 `Proxy`（客户端代理）。

一个典型的 AIDL 接口：

```java
// IWindowManager.aidl
interface IWindowManager {
    boolean addView(IBinder windowToken, in Rect frame);
}
```

编译后生成的 `Proxy` 类中的 `addView` 方法大致是这样的：

```java
// 编译生成：IWindowManager.Stub.Proxy
@Override
public boolean addView(IBinder windowToken, Rect frame) {
    Parcel data = Parcel.obtain();
    Parcel reply = Parcel.obtain();
    // ① 序列化参数
    data.writeInterfaceToken(DESCRIPTOR);
    data.writeStrongBinder(windowToken);
    frame.writeToParcel(data, 0);
    // ② 发起跨进程调用，mRemote 是 BinderProxy 对象
    mRemote.transact(Stub.TRANSACTION_addView, data, reply, 0);
    // ③ 等待回复后反序列化结果
    reply.readException();
    boolean result = reply.readBoolean();
    reply.recycle();
    data.recycle();
    return result;
}
```

这段代码做了三件事：先把参数打包成 `Parcel`，然后通过 `mRemote.transact()` 发起真正的跨进程调用，最后从返回的 `Parcel` 中读出结果。其中 `mRemote.transact()` 是阻塞调用——调用线程会停在这里，直到 Binder Driver 把结果送回来。

在服务端，对应的 `Stub.onTransact()` 会被 Binder 线程调用，根据 `code` 参数分发到对应的方法实现。

[已验证: AOSP 源码, frameworks/base/core/java/android/os/Binder.java] [已验证: 官方文档, developer.android.com/guide/components/aidl]

## Binder 线程池：性能分析的关键变量

### 线程池是怎么工作的

每个进程在初始化 Binder 时，会创建一组工作线程专门处理进来的 Binder 请求。这个线程池有几个重要特征：

**按需创建，有上限。** 线程不是一开始就全创建出来的。Binder Driver 根据负载动态创建新线程，默认上限约 15 个工作线程（不含主线程）。这个上限可以通过 `ProcessState.setThreadPoolMaxThreadCount()` 修改，但一旦设置就不能减小。`system_server` 等核心进程可能在厂商定制 ROM 中被调高。

**命名规则。** 在 Perfetto 中展开一个进程的线程列表，你会看到类似 `Binder:1234_1`、`Binder:1234_2` 这样的线程名，其中 `1234` 是进程 PID。`Binder:1234_B` 这种带 `B` 后缀的通常是处理从驱动侧到来的请求的线程。

[已验证: AOSP, frameworks/native/libs/binder/ProcessState.cpp, DEFAULT_MAX_BINDER_THREADS=15]

### 线程池耗尽意味着什么

当所有 Binder 工作线程都处于忙碌状态（Running 或 Uninterruptible Sleep），新的 Binder 请求会在驱动层排队。调用端线程会停在 `binder_thread_read` 上，表现为主线程长时间 Sleeping。

这和 ANR 直接相关：如果应用主线程发起的同步 Binder 调用因为线程池耗尽而等了很久，这段时间会被计入 ANR 超时。在 `system_server` 这边更严重——它的 Binder 线程处理所有 App 的系统服务请求，一旦线程池被打满，所有 App 的系统服务调用都会变慢。

在 Perfetto 中判断线程池是否饱和：展开目标进程，数一下 `Binder:` 线程中有多少个同时处于 Running 状态。如果大部分都活跃且持续了较长时间，基本可以判定线程池压力过大。

[已验证: L2, Perfetto Trace 中可观测] [来源: obsidian/Personal-Knowlodge/source/Android-Perfetto-10-Binder.md]

## 同步调用 vs oneway 调用

### 同步调用（Two-way）

大部分 Binder 调用是同步的——Client 发出请求后阻塞等待 Server 处理完毕并返回结果。这是最自然的编程模型：看起来就像调用了一个本地函数，有入参有返回值。

性能代价是**至少两次上下文切换**：Client 线程从 Running 变为 Sleeping（让出 CPU），Server 端 Binder 线程被唤醒（获得 CPU），处理完后 Client 线程再次被唤醒。每次上下文切换涉及 CPU 调度器的工作，耗时通常在微秒量级，但如果系统负载高、CPU 被其他线程占满，调度延迟可能到毫秒级。

### oneway 调用

在 AIDL 接口方法上加 `oneway` 关键字，调用就变成异步的：

```java
oneway interface ICallback {
    void onEvent(int type, in Bundle data);
}
```

Client 调用 `oneway` 方法后，`transact()` 会立即返回，不等待 Server 处理结果。Binder Driver 把请求放入队列，稍后唤醒 Server 端线程处理。

oneway 看起来像是"更快"的选择，但有几个陷阱需要注意：

**oneway 不是并发的。** 同一个 `IBinder` 对象上的 oneway 调用，在 Server 端是串行处理的。如果你连发 10 个 oneway 调用，它们会在 Server 端排队依次执行，而不是 10 个线程同时处理。

**调用方仍然可能阻塞。** 虽然不等服务端处理结果，但如果 Server 端的 oneway 队列积压过长，Binder Driver 可能会对调用方施加反压（特别是在 Android 14+ 引入 Lazy Async 之后）。在极端情况下，Client 端调用 oneway 方法也可能被短暂阻塞。

**适用场景。** 真正"发出就忘"的场景适合用 oneway：状态通知、日志上报、事件广播。需要返回值、或者需要确认对方已处理的场景，不要用 oneway。

[已验证: AOSP, frameworks/native/libs/binder/IPCThreadState.cpp] [已验证: 官方文档, developer.android.com/guide/components/aidl#oneway]

## 在 Perfetto 中分析 Binder

Binder 在 Perfetto 中的表现是这篇文章最实用的部分。当你看到主线程卡住时，你需要一套可复现的分析流程来定位问题。

### Binder 事务在 Perfetto 中的表现

Perfetto 提供两层 Binder 数据源：

**`linux.ftrace`（内核层）**：通过 `binder_transaction`、`binder_transaction_received` 等 tracepoint 记录事务的发起和到达。这是最通用的数据源，兼容所有 Android 版本。

**`android.binder`（用户层，Android 14/15+ 完善）**：提供更丰富的语义信息，比如直接区分请求和回复、提供 `blocking_dur_ns`（客户端阻塞时长）等预计算指标。

如果你在 Perfetto UI 中搜索 "Binder" 并添加 **Android Binder / Transactions** 轨道，你会看到一条时间轴，每个条目代表一次 Binder 事务。选中一个事务后，Details 面板会显示关键字段：

| 字段 | 说明 |
|------|------|
| `latency_ns` | 总耗时，从 Client 发出请求到收到回复 |
| `server_latency_ns` | Server 端实际处理耗时 |
| `blocking_dur_ns` | Client 端在内核等待的时间 |

这三个字段能帮你快速区分问题的类型。

[已验证: Perfetto 文档, perfetto.dev/docs/data-sources/android-binder] [来源: obsidian/Personal-Knowlodge/source/Android-Perfetto-10-Binder.md]

### 三步分析流程

**第一步：定位哪次 Binder 调用慢。** 先看主线程（或卡住的线程）的 `thread_state` 轨道，找到 Sleeping 状态持续时间较长的片段。放大后看这个时间段内关联的 Slice——通常是一个 Binder 调用。记下这次调用的接口名和方法。

**第二步：区分"谁慢"。** 查看这次事务的 `latency_ns`、`server_latency_ns` 和 `blocking_dur_ns`：

- 如果 `server_latency_ns` 很长（比如 15ms），说明 Server 端处理本身就很慢。需要跳转到 Server 端线程看它到底在干什么。
- 如果 `latency_ns` 很长但 `server_latency_ns` 很短，说明时间耗在 Binder Driver 调度或排队上——可能是线程池忙。
- 如果 `blocking_dur_ns` 异常大，结合 Server 端线程状态进一步确认。

**第三步：检查锁竞争。** 如果 Server 端线程在处理请求时出现了长时间 Sleeping，很可能是等 Java `synchronized` 锁。Perfetto 的 **Lock contention** 轨道会显示"谁持有锁"和"谁在等锁"。

在 Perfetto 中，你可以用 Flow 箭头追踪 Client 和 Server 之间的因果关系：点击一个 Binder 事务 Slice，如果 Flow Events 已开启，你会看到一条箭头从 Client 的 Sleeping 片段指向 Server 端的 Running 片段。这个箭头告诉你：就是这次 Binder 调用导致了 Client 的等待。

[已验证: L2, Perfetto UI 实际操作验证] [来源: obsidian/Personal-Knowlodge/source/Android-Perfetto-10-Binder.md]

### 一个典型案例：窗口管理延迟

以应用冷启动为例。你发现 `Activity.startActivity` 的耗时异常，主线程在调用 `IActivityTaskManager.startActivity` 期间 Sleeping 了 30ms。通过 Flow 箭头追踪到 `system_server` 的 `Binder:1605_2` 线程，发现它在处理请求时 Sleeping 了 20ms——不是在做实际工作，而是在等锁。查看 Lock contention 轨道，发现 `WindowManagerGlobalLock` 正被 `android.anim` 线程持有。

结论：App 启动发起的 Binder 请求，在 SystemServer 端因为等待窗口管理锁而被阻塞。锁被系统动画线程持有用于更新窗口状态。这是一个典型的系统层锁竞争问题——App 端能做的优化是减少冷启动期间的 IPC 调用频率，避免在动画密集期做复杂的窗口操作。

[来源: obsidian/Personal-Knowlodge/source/Android-Perfetto-10-Binder.md]

### 用 SQL 统计锁竞争

如果你已经熟悉 Perfetto SQL，可以用下面的查询统计 `system_server` 中 Java monitor 锁竞争的深度（同一把锁上有多少个线程在排队）：

```sql
SELECT count(1) AS lock_depth, s.slice_id, s.ts, s.dur,
       s.dur/1e6 AS dur_ms,
       substr(s.name, 46, instr(s.name,')')-46) AS owner_tid
FROM slice s
JOIN thread_track ON s.track_id = thread_track.id
JOIN thread USING(utid)
JOIN process USING(upid)
WHERE process.name = 'system_server'
  AND s.name LIKE 'Lock contention on a monitor lock %'
GROUP BY s.slice_id
HAVING lock_depth > 0
ORDER BY s.dur DESC;
```

这段查询做了这样一件事：找到 `system_server` 中所有锁竞争事件，统计每个锁事件期间有多少其他线程也在等同一把锁（lock_depth）。`lock_depth` 越高，说明这把锁的争抢越严重，可能是系统性能瓶颈的根源。

[已验证: L2, Perfetto SQL 语法正确] [来源: obsidian/Personal-Knowlodge/source/Android-Perfetto-10-Binder.md]

## Binder 风暴与系统负载

[自动发现: 来源 obsidian/Personal-Knowlodge/source/Android-Perfetto-10-Binder.md]

在 Perfetto 中，如果你看到某个进程在短时间内发起大量 Binder 事务——Transactions 轨道上密密麻麻全是短条——这就是 Binder 风暴。它不一定导致单次调用超时，但会累积效应：SystemServer 的 Binder 线程池被打满、锁竞争加剧、其他 App 的系统服务调用延迟上升。

Binder 风暴的典型来源：某个 App 在主线程的 `doFrame` 中反复调用系统服务（比如每帧都查询一次 DisplayInfo），或者某个后台进程在短时间内大量注册/注销回调。在 Perfetto 中定位 Binder 风暴，可以用 SQL 按 Client 进程统计事务频率：

```sql
SELECT process.name, count(1) AS txn_count,
       sum(s.dur)/1e6 AS total_dur_ms
FROM slice s
JOIN thread_track ON s.track_id = thread_track.id
JOIN thread USING(utid)
JOIN process USING(upid)
WHERE s.name LIKE 'binder%'
GROUP BY process.name
ORDER BY total_dur_ms DESC
LIMIT 20;
```

优化方向：减少不必要的 IPC 调用频率、缓存查询结果、将高频调用改为 oneway + 批量处理。

## 与其他章节的关系

Binder 不是孤立的机制，它和全书多个章节有直接关联：

- **1.1 分层架构**：Binder 是 Android 分层架构中跨进程通信的核心基础设施。1.1 中提到的 Treble 架构，底层就是 hwbinder（HAL Binder）。
- **2.5 MainThread 与 RenderThread**：主线程在 `dequeueBuffer` 时如果 SurfaceFlinger 持锁，就会通过 Binder 阻塞导致渲染卡顿。
- **7.2 卡顿原因体系**：Binder 调用耗时是主线程卡顿的重要来源之一。
- **8.2 应用启动分析**：冷启动过程中的 Binder 调用频率和耗时直接影响启动速度。
- **9.1 ANR 设计原理**：主线程的同步 Binder 调用如果超时，直接触发 ANR。

## 版本演进

Binder 在 Android 版本中持续优化，这里列出对性能分析有影响的变化：

- **Android 8.0（API 26）**：引入 scatter-gather 优化，将 Binder 数据拷贝从最多三次减少到一次。Project Treble 引入 HIDL 和 hwbinder，HAL 层开始 Binder 化。
- **Android 10（API 29）**：开始将 HAL 接口从 HIDL 迁移回 Stable AIDL，到 Android 13 HIDL 正式标记废弃。新 HAL 接口统一使用 AIDL。
- **Android 12（API 31）**：引入 Binder Freeze——被缓存的进程其 Binder 接口会被冻结，同步调用该进程的 Binder 会快速失败（而不是长时间卡住），有助于减少 ANR。
- **Android 14/15（API 34/35）**：`android.binder` 数据源在 Perfetto 中完善，提供更丰富的事务语义。Oneway 调用支持 Lazy Async（延迟派发），减少唤醒风暴带来的功耗。
- **Android 15（API 35）**：Binder Heavy Hitter Watcher 自动监测过度使用 Binder 的进程并打印日志警告。

[已验证: 官方文档, developer.android.com] [来源: obsidian/Personal-Knowlodge/source/Android-Perfetto-10-Binder.md]

### AIDL 与 HIDL 的演进

[自动发现: 来源 developer.android.com/architecture/hidl]

Android 8 引入 Project Treble 时，为了解耦 Framework 和 HAL，Google 创建了 HIDL（HAL Interface Definition Language）作为 HAL 层的接口定义语言。HIDL 使用 C++ 风格的语法定义接口，支持版本化（major/minor），并且同时支持 binderized（跨进程）和 passthrough（进程内直通）两种模式。

但从 Android 11 开始，Google 决定把 HAL 接口也统一到 AIDL。Stable AIDL 支持向后兼容的增量修改（可以加方法、加字段），比 HIDL 的显式版本号更灵活。到 Android 13，HIDL 被正式标记为废弃，所有新 HAL 接口必须使用 AIDL。

这对性能分析的影响是：从 Perfetto 的角度看，HAL 层的 Binder 调用（无论是 hwbinder 还是 AIDL binder）都会出现在 `android.binder` 和 `ftrace` 的 binder 轨道中。AIDL HAL 都是 binderized 模式（走 Binder IPC），比 HIDL 的 passthrough 模式多一次进程切换，但获得了更好的隔离性和安全性。

## 常见问题与误区

### 误区：Binder 调用一定很慢

Binder 的基础开销是一次上下文切换（通常微秒级），并不是每个调用都会造成可感知的延迟。大部分系统服务方法（如 `getRunningTasks()`）在服务端的执行时间不到 1ms。Binder 变"慢"通常是因为三个叠加因素：服务端处理本身耗时、线程池排队、锁竞争。单独一次正常的 Binder 调用不是性能瓶颈——高频调用或与慢服务叠加才是。

### 误区：oneway 一定比同步快

oneway 调用避免了 Client 端的阻塞等待，但它不意味着"零成本"。oneway 在同一 `IBinder` 上是串行排队的，大量 oneway 调用会撑大 Server 端的请求队列。如果 Server 端处理速度跟不上，队列积压会影响同一服务上其他调用者的响应延迟。选择同步还是 oneway，应该根据业务语义来，而不是根据"哪个更快"来。

### 误区：线程池 15 个线程不够用就该加大

如果线程池经常被打满，根本原因往往不是线程数太少，而是 Server 端某些方法的执行时间太长（比如在 Binder 线程中做了 IO 操作或等锁）。加大线程池只是延缓症状，正确的方向是缩短单次 Binder 调用的处理时间、减少锁持有时间、避免在 Binder 线程中做耗时操作。

## 参考资料

- AOSP 源码路径：
  - `frameworks/native/libs/binder/BpBinder.cpp`（Proxy 侧 transact 实现）
  - `frameworks/native/libs/binder/IPCThreadState.cpp`（与驱动通信的核心循环）
  - `frameworks/native/libs/binder/ProcessState.cpp`（线程池初始化、mmap）
  - `frameworks/base/core/java/android/os/Binder.java`（Java 层 Binder 基类）
  - `drivers/android/binder.c`（内核 Binder Driver 实现）
- [已验证: 官方文档, developer.android.com/reference/android/os/IBinder]
- [已验证: 官方文档, developer.android.com/guide/components/aidl]
- [已验证: Perfetto 文档, perfetto.dev/docs/data-sources/android-binder]
- [来源: obsidian/Personal-Knowlodge/source/Android-Perfetto-10-Binder.md]（高爷原创：Android Perfetto 系列 10 - Binder 调度与锁竞争）
- [来源: obsidian/Personal-Knowlodge/source/Android-Systrace-Binder.md]（高爷原创：Android Systrace 基础知识 - Binder 和锁竞争解读）
- [来源: obsidian/Personal-Knowlodge/source/2026-03-06_wechat_Binder驱动中的流程详解.md]（OPPO 内核工匠：Binder 驱动中的流程详解）
- [引用: https://paul.pub/android-binder-driver/]
- [引用: https://perfetto.dev/docs/data-sources/android-binder]
