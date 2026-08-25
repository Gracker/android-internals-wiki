---
title: Binder 事务缓冲区与可观测性
chapter: '1.11'
section: '1.11'
status: finalized
applicable_versions: Android 15 (API 35) - Android 17 (API 37)
tags:
- binder
- ipc
- transaction-buffer
- performance
- android17
- rpc-binder
- performance-monitoring
- tracing
- perfetto
- aidl
- recording
related_chapters:
- '1.9'
- '1.15'
- '1.10'
- '14.3'
pipeline_stage: ready-to-publish
task6_state: reviewed
task9_state: reviewed
last_verified: '2026-08-16'
last_verified_against: AOSP android-17.0.0_r1 / external/perfetto android-17.0.0_r1 / android17-6.18-2026-06_r6
last_review_finalize_at: '2026-08-16'
last_review_finalize_run_id: 20260816-140530-1396d202
confidence: high
sources:
- type: aosp
  path: frameworks/native/libs/binder/RpcState.cpp (android-15.0.0_r1)
- type: aosp
  path: frameworks/native/libs/binder/Constants.h (android-16.0.0_r1)
- type: aosp
  path: frameworks/native/libs/binder/Constants.h (android-17.0.0_r1)
- type: aosp
  path: frameworks/native/libs/binder/ProcessState.cpp (android-17.0.0_r1)
- type: aosp
  path: frameworks/native/libs/binder/RpcState.cpp (android-17.0.0_r1)
- type: aosp
  path: frameworks/native/libs/binder/RpcTransportUtils.h (android-17.0.0_r1)
- type: aosp
  path: frameworks/native/libs/binder/BpBinder.cpp (android-17.0.0_r1)
- type: aosp
  path: frameworks/native/libs/binder/Binder.cpp (android-17.0.0_r1)
- type: aosp
  path: frameworks/native/libs/binder/IPCThreadState.cpp (android-17.0.0_r1)
- type: aosp
  path: frameworks/native/libs/binder/Parcel.cpp (android-17.0.0_r1)
- type: aosp
  path: external/perfetto/src/trace_processor/perfetto_sql/stdlib/android/binder.sql (android-17.0.0_r1)
- type: kernel
  path: common/drivers/android/binder.c (android17-6.18-2026-06_r6)
- type: kernel
  path: common/drivers/android/binder_alloc.c (android17-6.18-2026-06_r6)
- type: kernel
  path: common/drivers/android/binder_trace.h (android17-6.18-2026-06_r6)
- type: kernel
  path: common/include/uapi/linux/android/binder.h (android17-6.18-2026-06_r6)
- type: official
  path: https://developer.android.com/reference/android/os/TransactionTooLargeException
- type: official
  path: https://developer.android.com/reference/android/os/SharedMemory
- type: official
  path: https://source.android.com/docs/core/architecture/hidl/binder-ipc
- type: aosp
  path: frameworks/native/libs/binder/Binder.cpp
- type: aosp
  path: frameworks/base/core/java/android/os/Binder.java
- type: aosp
  path: frameworks/base/core/jni/android_util_Binder.cpp
- type: aosp
  path: frameworks/native/libs/binder/IPCThreadState.cpp
- type: aosp
  path: frameworks/native/libs/binder/ProcessState.cpp
- type: aosp
  path: frameworks/native/libs/binder/RecordedTransaction.cpp
- type: aosp
  path: frameworks/native/libs/binder/include/binder/RecordedTransaction.h
- type: aosp
  path: frameworks/native/libs/binder/include/binder/Trace.h
- type: aosp
  path: system/tools/aidl/generate_cpp.cpp
- type: aosp
  path: system/tools/aidl/generate_java_binder.cpp
- type: aosp
  path: external/perfetto/src/trace_processor/perfetto_sql/stdlib/android/binder.sql
- type: kernel
  path: include/uapi/linux/android/binder.h (android17-6.18-2026-06_r6)
- type: kernel
  path: drivers/android/binder.c (android17-6.18-2026-06_r6)
- type: kernel
  path: drivers/android/binderfs.c (android17-6.18-2026-06_r6)
- type: kernel
  path: drivers/android/binder_trace.h (android17-6.18-2026-06_r6)
last_consolidated_at: '2026-08-24'
consolidated_from:
- src/part1-fundamentals/ch01-architecture/1.31-android17-binder-rpc.md
- src/part1-fundamentals/ch01-architecture/1.44-android17-binder-sz4m-kernel-buffer-pool.md
- src/part1-fundamentals/ch01-architecture/01.32-android17-binder-ipc-performance-monitoring.md
- src/part1-fundamentals/ch01-architecture/30-binder-transaction-buffer-performance.md
- src/part1-fundamentals/ch01-architecture/31-binder-performance-recording-trace.md
---

# Binder 事务缓冲区与可观测性

Binder Transaction Buffer（事务缓冲区）没有适用于所有调用的“单笔 1 MiB 上限”。走 `/dev/binder` 驱动的内核 Binder 会为每个进程建立接收事务的映射区，多笔在途请求、`oneway`（单向）事务、回复和 Binder 对象会共同占用这块空间。RPC Binder 使用另一套传输机制和协议上限。“Binder 上限是 1 MiB”这种说法缺少并发、方向、异步预算和协议头等必要条件。

以下分析以 `android-17.0.0_r1` 和 `android17-6.18-2026-06_r6` 为准，覆盖映射区大小、驱动分配与回收、单向事务压力，以及 Android 17 中 600 KiB RPC 上限对应的路径。事务时序观测见本文后半部分，`oneway` 排队见 [1.10 Binder 线程池、异步事务与 Freezer](10-binder-scheduling-freezer-threadpool.md)。

Binder 故障既要看事务是否进入驱动，也要看目标进程的缓冲区和异步预算是否允许继续分配。内核分配状态、AIDL Trace 与 Perfetto 事务切片提供的是同一问题的不同观察面。

## 事务缓冲区、分配器与大小限制

### 一、三类大小边界

| 边界 | Android 17 的值或规则 | 约束对象 |
| --- | --- | --- |
| libbinder 映射请求 | `1 MiB - 2 × 页大小` | 一个使用内核 Binder 的进程接收缓冲区 |
| Binder 驱动内存映射（mmap）上限 | `min(请求长度, 4 MiB)` | 驱动接受的单个 `binder_alloc` 映射长度 |
| RPC Binder 协议上限 | `600 KiB`，还要扣除协议头与对象表 | 一条 RPC Binder 命令或回复包 |
| libbinder 大事务告警线 | `300 KiB` | 内核 Binder 和 RPC Binder 的诊断告警，不是硬上限 |

第一行和第二行并不矛盾。Android 17 的 AOSP `ProcessState` 主动只映射约 1 MiB；r6 内核最多接受 4 MiB，这是驱动对调用者请求的保护上限。普通 AOSP 进程不会因为驱动允许 4 MiB 就自动得到 4 MiB。

RPC Binder 不通过目标进程的 `/dev/binder` 映射区传输数据，因此 600 KiB 与内核 Binder 的约 1 MiB 接收池不能互相替代。

### 二、内核 Binder 映射区如何建立

#### 1. `BINDER_VM_SIZE` 的准确计算

Android 17 的 `ProcessState.cpp` 定义：

```cpp
#define BINDER_VM_SIZE \
    ((1 * 1024 * 1024) - sysconf(_SC_PAGE_SIZE) * 2)
```

常见页大小下的结果如下：

| 页大小 | 计算 | 映射长度 |
| --- | --- | --- |
| 4 KiB | `1,048,576 - 2 × 4,096` | `1,040,384` 字节，即 1016 KiB |
| 16 KiB | `1,048,576 - 2 × 16,384` | `1,015,808` 字节，即 992 KiB |

16 KiB 页设备的映射长度比 4 KiB 页设备少 24 KiB。这个差值来自宏中扣除的“两页”，不能解释成驱动把每笔事务按 16 KiB 对齐。

`ProcessState` 使用以下方式建立映射：

```cpp
mVMStart = mmap(
    nullptr,
    BINDER_VM_SIZE,
    PROT_READ,
    MAP_PRIVATE | MAP_NORESERVE,
    opened.get(),
    0
);
```

这块用户虚拟地址用于接收驱动写入的事务。`MAP_NORESERVE` 表示不为映射预留交换空间；它不能推导出“Binder 页面不计入 RSS（进程当前驻留在物理内存中的大小）”。驱动在事务需要覆盖相应范围时安装后备物理页，内存统计仍要以目标内核和设备实测为准。

#### 2. 映射属于接收方

内核 Binder 为目标进程分配请求 buffer。A 调用 B 时，请求占用 B 的 `binder_alloc`；B 返回同步回复时，回复占用 A 的 `binder_alloc`。因此，某个进程的压力既可能来自它作为服务端接收大量请求，也可能来自它作为客户端同时等待大量回复。

发送方用户态 `Parcel` 的内存是另一份数据。驱动将 Parcel 数据区、对象偏移数组和附加 buffer 复制或修正到接收方映射区，不能把发送方 Parcel 容量与接收方 Binder 空间视为同一个指标。

#### 3. 驱动的 4 MiB 上限

r6 内核的 `binder_alloc_mmap_handler()` 使用下面的限制：

```c
alloc->buffer_size = min_t(
    unsigned long,
    vma->vm_end - vma->vm_start,
    SZ_4M
);
```

这个上限允许其他 Binder 用户态实现请求不同长度，同时阻止无限放大映射。AOSP `ProcessState` 仍传入 `BINDER_VM_SIZE`，所以最终 `alloc->buffer_size` 是前一节算出的 1016 KiB 或 992 KiB。

### 三、`binder_alloc` 如何分配一笔事务

#### 1. 分配大小不只有 `data_size`

`binder_alloc_new_buf()` 接收三部分：

- `data_size`：Parcel 普通数据区；
- `offsets_size`：指向 Binder 对象、文件描述符（FD）等对象的偏移数组；
- `extra_buffers_size`：分散—聚集（scatter-gather）传输使用的附加缓冲区及相关数据。

r6 内核的 `sanitized_size()` 分别把三者按 `sizeof(void *)` 对齐，再求和；零长度事务也至少占一个指针大小，以保证地址唯一。

```text
allocated = align(data_size, pointer_size)
          + align(offsets_size, pointer_size)
          + align(extra_buffers_size, pointer_size)
```

事务 buffer 按指针大小切分。内存页只提供后备存储，相邻小事务可以位于同一页。16 KiB 页会改变页面安装和回收粒度，不会让每个小事务固定浪费 16 KiB。

#### 2. 最佳适配、切分与合并

这里的“最佳适配”是指从空闲 buffer 红黑树中，选择能够容纳请求的最小块。`binder_alloc_new_buf_locked()` 找到更大的空闲块后，会把它切成已分配部分和剩余空闲 buffer；释放时再与相邻空闲块合并。

分配成功后，`binder_install_buffer_pages()` 只安装覆盖该 buffer 所需的页面。页面级回收还要考虑相邻 buffer 是否在使用，因此事务 buffer 释放与页面可回收发生在不同时间。

#### 3. 空间不足直接失败

如果找不到合适的空闲 buffer，`binder_alloc_new_buf_locked()` 返回 `-ENOSPC`。异步预算不足也返回 `-ENOSPC`。这条路径不会阻塞等待旧 buffer 释放，也不会借 `BR_SPAWN_LOOPER` 扩大线程池。

`BR_SPAWN_LOOPER` 处理的是服务进程缺少可用 Binder 线程，与接收缓冲区分配失败属于不同问题。native 调用通常看到 `FAILED_TRANSACTION`；Java 层如何映射为 `TransactionTooLargeException` 或其他异常，取决于 JNI 的启发式规则，本文后文会继续说明。

#### 4. buffer 何时归还

接收方 libbinder 通过 `BR_TRANSACTION` 或 `BR_REPLY` 得到映射区地址，构造一个引用这段内存的 `Parcel`。处理完成后，释放回调向驱动发送 `BC_FREE_BUFFER`，驱动才把对应 `binder_buffer` 放回空闲树。

对于同步请求，Android 17 的 `IPCThreadState` 在发送回复前执行 `buffer.setDataSize(0)`，释放请求 buffer，避免客户端收到回复后立即发起下一笔调用时，旧请求仍占用服务端空间。

`oneway` 没有回复。它可能在目标进程或目标 node 的异步队列中等待，buffer 要到服务端完成处理并释放 Parcel 后才归还。高频 `oneway` 的 buffer 生命周期不一定比同步调用短。

### 四、同步与异步共享地址池，但异步有预算

#### 1. “一半给 `oneway`”不是两块物理分区

初始化 `binder_alloc` 时，r6 内核设置：

```c
alloc->free_async_space = alloc->buffer_size / 2;
```

同步和异步事务仍从同一棵空闲 buffer 树分配。`free_async_space` 是额外的记账预算：异步分配前检查预算，成功后扣减，释放后归还。同步事务不扣这项预算，但仍需要地址池中存在足够大的连续空闲 buffer。

一半空间没有被提前划成 `oneway` 专用区。该预算只限制异步事务最多消耗的总量，为同步请求和回复保留余地。

#### 2. `oneway` 的 node 级串行会延长占用

Binder node 是驱动中代表目标 Binder 对象的节点。同一 node 的 `oneway` 事务按顺序处理：第一笔异步事务正在执行时，后续事务进入该 node 的 `async_todo`；当前 buffer 释放后，驱动才把下一笔移到目标进程的可执行队列。

如果生产速度高于服务端消费速度，多个 `oneway` buffer 会同时占据目标进程地址池；调用方已从 `BR_TRANSACTION_COMPLETE` 返回，也不代表服务端完成处理或 buffer 已经释放。

#### 3. Android 17 r6 内核的 spam 判定

这里的 spam 指同一发送进程大量占用目标异步空间的可疑行为。r6 内核只有在 `free_async_space < buffer_size / 10` 时才开始查找主要发送方，也就是剩余异步预算少于初始异步预算的 20%。随后按当前发送进程统计尚未释放的异步 buffer：

- buffer 数量超过 50；或
- 总占用超过 `buffer_size / 4`；

满足其一，当前 buffer 会被标记为 `oneway_spam_suspect`。libbinder 默认启用驱动检测，调用方收到 `BR_ONEWAY_SPAM_SUSPECT` 时记录调用栈。

这些条件只用于内核诊断，不能作为业务接口的容量目标。接近这些条件时，目标进程的异步预算已经非常紧张。

### 五、FD、Binder 对象与分散—聚集传输也占元数据空间

通过 Binder 传递 `ParcelFileDescriptor` 或 Binder 对象时，大文件内容不会复制进 `data_size`，但事务仍包含 `flat_binder_object` 以及对象偏移条目。驱动还要完成对象引用或 FD 的校验与转换。

FD 方案的主要价值是让大块数据留在文件、共享内存或其他专用缓冲区中，Binder 只承载描述符和控制信息。这不表示端到端没有数据复制：生产者可能先把数据写进共享区域，接收者也要执行 `mmap`、同步并管理生命周期。

Android 8 已引入 scatter-gather Binder，即把分散在多处的 buffer 作为一次事务描述并交给驱动处理。Android 17 的 `BC_TRANSACTION_SG` 可以通过 `binder_transaction_data_sg` 提供 `buffers_size`，驱动把相应内容计入 `extra_buffers_size`。它属于长期沿用的机制，不是 Android 17 新增的应用开关。

### 六、怎样理解“大事务”与失败

#### 1. 没有安全的固定单笔值

一笔事务能否成功，至少取决于：

- 目标进程当前剩余的连续空闲 buffer；
- 同时在途的请求与回复；
- 此调用的数据区、对象偏移数组和附加 buffer；
- `oneway` 是否还受 `free_async_space` 限制；
- 事务发送期间目标进程是否死亡或被冻结；
- 走内核 Binder 还是 RPC Binder。

即使单笔数据明显低于映射长度，并发事务也可能使它失败。反过来，失败也不必然意味着本次 Parcel 本身接近 1 MiB。

#### 2. 300 KiB 是主动告警线

Android 17 的 `Constants.h` 定义：

```cpp
constexpr size_t kLogTransactionsOverBytes = 300 * 1024;
```

`BpBinder` 对超过该值的发出 Parcel 记录 `Large outgoing transaction`。`BBinder` 对超过该值的请求和回复分别记录 `Large data transaction`、`Large reply transaction`。

这条线比常见映射长度小很多，因为大事务会增加复制成本，并挤压同一进程的并发空间。日志出现不等于当前事务必然失败，但应检查接口是否把大块数据、无界列表或图片直接塞进 Parcel。

#### 3. 服务端 1000 ms 日志测的是执行区间

Android 17 的 `BBinder::transact()` 从进入方法开始计时；超过 1000 ms 时记录接口、方法、请求字节数、回复字节数和 `flags`（标志位）。这个区间主要覆盖服务端 `onTransact()` 及其嵌套工作，不是调用方端到端耗时，也不含事务到达服务线程之前的全部等待。

#### 4. Perfetto 的大小证据

r6 内核的 `binder_transaction_alloc_buf` tracepoint（内核静态跟踪点）直接给出 `data_size`、`offsets_size`、`extra_buffers_size`，并通过事务 ID 与 `binder_transaction` 关联。Perfetto 标准 `android_binder_txns` 表没有通用的 `dataSize` / `replySize` 列；分析大小时，应在录制中加入该 ftrace（内核跟踪框架）事件，再查看原始事件参数。

debugfs（内核调试文件系统）的 `stats` 还能看到各进程的 buffer 数量和 `free async space`，但它只反映读取时刻的快照，不能代替逐事务时间轴。

### 七、RPC Binder 的 600 KiB 边界

#### 1. 版本变化发生在 Android 16

`Constants.h` 在 `android-16.0.0_r1` 和 `android-17.0.0_r1` 中都存在。其注释说明 RPC Binder 上限在 Android V 及以前是 100 KB，Baklava 时期改为：

```cpp
constexpr size_t kRpcTransactionLimitBytes = 600 * 1024;
```

因此版本边界应写成：

| 版本 | RPC Binder 边界 |
| --- | --- |
| Android 15 / V 及以前 | 100 KB |
| Android 16 / Baklava | 600 KiB，并引入统一的 300 KiB 告警常量 |
| Android 17 | 延续 600 KiB 协议上限与 300 KiB 告警线 |

Android 17 是当前验证基线，但不是这次上限调整的首发版本。

#### 2. Parcel 可用空间小于 600 KiB

`RpcState::transactAddress()` 计算的 `bodySize` 包含 `RpcWireTransaction`、Parcel 数据和对象表，并要求：

```cpp
bodySize < kRpcTransactionLimitBytes - sizeof(RpcWireHeader)
```

因此，应用可用的 Parcel 数据必须小于 600 KiB，还要为协议结构和对象表留出空间。回复使用同样的包级约束；超出时，服务端清空回复数据，并以 `FAILED_TRANSACTION` 返回。

`CommandData` 的动态分配也拒绝超过 600 KiB 的请求。`RpcTransportUtils` 把 600 KiB 用作初始最大传输块（chunk），并可在底层返回 `ENOMEM` 时缩小传输块重试。传输分块不会放宽整个 RPC 命令的协议上限。

#### 3. 它不影响普通应用到系统服务的内核 Binder

`BpBinder::transact()` 先判断 `isRpcBinder()`：RPC 端点（endpoint）交给 `RpcSession`，其余调用交给 `IPCThreadState` 和内核 Binder。普通应用调用 Activity Manager、Package Manager 或 ContentProvider，通常属于后一条路径，不会因为 RPC 上限从 100 KB 变为 600 KiB 就获得更大的内核 Binder 空间。

`Constants.h` 的注释将设限原因归于 Baklava 时期 RPC Binder 尚不支持共享内存。Android 17 标签仍保留同一常量和注释；设计 RPC 接口时应遵守 600 KiB 包级上限，不能假设存在自动切换到共享内存的后备路径。

### 八、`TF_ONE_WAY` 与 `TF_CLEAR_BUF` 的 buffer 语义

#### 1. `TF_ONE_WAY`

`TF_ONE_WAY` 让调用方不等待回复，但数据仍要在目标进程成功分配并复制。`BR_TRANSACTION_COMPLETE` 只说明驱动接受了发送请求；服务端执行、同一 node 上的 `oneway` 排队和 buffer 回收都可能发生在之后。

适合 `oneway` 的接口应当无需返回结果、允许异步处理并有容量控制。把同步方法机械改成 `oneway`，只会把调用方等待变成目标进程的隐式队列和异步空间压力。

#### 2. `TF_CLEAR_BUF`

r6 内核在创建目标 `binder_buffer` 时把 `TF_CLEAR_BUF` 写入 `clear_on_free`。释放 buffer 前，`binder_alloc_clear_buf()` 遍历后备物理页，把整个 buffer 清零后再归还分配器（allocator）。

同步调用中，Android 17 的 `IPCThreadState` 会把 `TF_CLEAR_BUF` 转发给回复；`BBinder::transact()` 还会对用户态回复 Parcel 调用 `markSensitive()`，使 libbinder 在释放自己拥有的数据区前清零。因此，该标志同时覆盖接收方的内核 buffer 和相关用户态回复数据，不能写成“只清用户态、不清内核”。

清零成本随 buffer 覆盖范围增加，源码没有承诺固定微秒数。它是敏感数据的安全语义，不能为了减少耗时随意移除；应避免把大块敏感数据放进 Parcel。

### 九、16 KiB 页设备上的影响

16 KiB 页带来两个可直接从源码确认的变化：

1. `BINDER_VM_SIZE` 从 4 KiB 页设备的 1016 KiB 变为 992 KiB；
2. `binder_install_buffer_pages()` 和页面 LRU（按近期使用情况组织的可回收页列表）以 16 KiB 为安装、回收粒度。

事务 buffer 的逻辑大小仍按指针宽度对齐，多个小 buffer 可以共享一页。较大的页面可能改变后备物理页数量、回收时机和内存局部性，但“每个小事务多浪费 12 KiB”之类结论无法从分配器实现中得出，必须通过实测验证。

做 4 KiB / 16 KiB 对比时，应固定 APK、调用并发、Parcel 分布和设备内存状态，并分别报告事务大小、失败率、页面统计与端到端时延。

### 十、接口设计与验证方法

#### 1. 控制数据可以直接走 Parcel

固定字段、数量有界的小型请求适合 AIDL `structured` Parcelable，即在接口定义中声明固定字段结构。集合应使用有明确元素类型的 typed collection，避免通用 Bundle 携带不受控对象；服务端还要校验元素数、字符串长度和嵌套集合深度。

不要按“20 个操作”或“500 KB 以下”写死通用规则。同一种 `ContentProviderOperation` 的 URI、`selection`、`values` 和 `back reference`（引用批次中前一项结果）都会改变 Parcel 大小。批量接口应同时限制条目数量和预估字节数，并在压力测试中记录序列化后的大小。

#### 2. 大块数据使用描述符协议

图片、模型、媒体帧、大型表格或可重复访问的数据，更适合放在文件、`ParcelFileDescriptor`、`SharedMemory` 或业务专用共享 buffer 中。Binder 只传递描述符、偏移、长度、格式、版本和所有权。

协议还要明确：

- 谁创建和关闭 FD；
- 何时允许复用或覆盖；
- 读写权限与 `SharedMemory.setProtect()`；
- 生产者与消费者之间如何同步；
- 对端死亡后的清理；
- 长度、偏移与整数溢出的校验。

#### 3. 为 `oneway` 建立下游压力控制

下游消费跟不上时，上游应主动限流、合并或丢弃，这类机制通常称为背压。`oneway` 接口可以用序列号合并过时状态，用设有容量上限的窗口限制未确认事件，或将高频细粒度事件聚合成批次。生产速度需要长期低于消费速度，不能等到驱动发出 `oneway_spam_suspect` 告警才处理。

#### 4. 同时测单笔大小和并发

建议至少覆盖以下用例：

1. 单请求逐步增加 `data_size`、对象数量和 `extra_buffers_size`；
2. 多线程并发同步请求；
3. 服务端故意延迟消费 `oneway`；
4. 请求小、回复大，以及请求大、回复小；
5. 4 KiB 与 16 KiB 页设备；
6. 内核 Binder 与 RPC Binder 分开测试；
7. Perfetto 记录 `binder_transaction_alloc_buf`，复现前后读取 debugfs 的 `stats`；
8. 检查 300 KiB 日志、`FAILED_TRANSACTION`、`ENOSPC` 和 `oneway` spam 日志。

只有把事务大小分布与并发数放在一起，才能解释“同一个调用有时成功、有时失败”。

### 十一、Android 17 源码核对入口

| 结论 | 文件与入口 |
| --- | --- |
| AOSP 映射长度 | `ProcessState.cpp`：`BINDER_VM_SIZE`、`mmap()` |
| 驱动 4 MiB 上限、异步初始预算 | `binder_alloc.c`：`binder_alloc_mmap_handler()` |
| 大小对齐、最佳适配与 `-ENOSPC` | `binder_alloc.c`：`sanitized_size()`、`binder_alloc_new_buf_locked()` |
| `oneway` spam 条件 | `binder_alloc.c`：`debug_low_async_space_locked()` |
| 内核 buffer 清零 | `binder.c`：`clear_on_free`；`binder_alloc.c`：`binder_alloc_clear_buf()` |
| 300 KiB 日志与 600 KiB RPC 上限 | `Constants.h` |
| RPC 请求/回复包级检查 | `RpcState.cpp`：`transactAddress()`、回复发送路径 |
| 传输块（chunk） | `RpcTransportUtils.h`：`kChunkMax` |
| 大事务与慢事务日志 | `BpBinder.cpp`、`Binder.cpp` |
| 请求释放与 clear 标志转发 | `IPCThreadState.cpp`：`BR_TRANSACTION` 处理分支 |

分析 Transaction Buffer 时，应标明目标进程、事务方向、内核 Binder / RPC Binder 通道、同步 / `oneway` 和并发数。缺少这些条件，“1 MiB 上限”只是容易误导的近似说法。


## 从 AIDL Trace 到内核事务快照

缓冲区模型给出失败条件，可观测信号用于确认是哪一个进程、哪类事务和哪个时间窗口触发了限制。

Binder 可观测性由多套机制组成。分析等待时间、查询冻结状态、读取失败原因、查看 AIDL 方法名和录制 Parcel 内容，各自依赖不同的实现层。混用这些机制会导致两类错误：把状态位当作事务计数，或把调试录制当成可常驻的线上监控。

以下分析以 Android 17 / API 37、AOSP `android-17.0.0_r1` 和内核 `android17-6.18-2026-06_r6` 为准，说明各项能力提供的证据、调用边界及其与 Perfetto 结果的对应关系。

### 一、按证据类型选择工具

| 需要回答的问题 | 首选机制 | 能看到什么 | 看不到什么 |
|---|---|---|---|
| 调用在哪一端等待 | Perfetto Binder flow（跨进程流关联）与线程状态 | 客户端 / 服务端时间、调度和阻塞状态 | Parcel 业务内容 |
| 这次 AIDL 调的是哪个方法 | `ATRACE_TAG_AIDL` 时间片（slice） | 接口、方法、客户端或服务端时间片 | 参数值、返回值 |
| 冻结期间是否收到事务 | `BINDER_GET_FROZEN_INFO` | 同步事务状态位、异步事务状态位 | 事务次数和耗时 |
| 失败来自哪个驱动命令 | `BINDER_GET_EXTENDED_ERROR` | 失败 ID、Binder 返回命令、负 errno（Linux 错误号） | 跨线程历史错误 |
| 发送端是否触发 `oneway` 嫌疑检测 | `BR_ONEWAY_SPAM_SUSPECT` | 当前发送线程收到告警并打印调用栈 | 接收端队列的通用统计报表 |
| 请求和回复的 Parcel 是什么 | `RecordedTransaction` | 接口名、事务码（code）、标志位（flags）、状态、请求 / 回复数据 | 稳定文件协议、低扰动线上采集 |

这些能力没有“粗粒度到细粒度”的固定层级，也不是 Android 17 同时新增。当前版本中的源码入口只能证明 Android 17 的行为，不能反推引入版本。

### 二、binderfs 功能文件表示能力，不表示运行状态

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

### 三、冻结查询返回状态位，不是事务计数

#### 3.1 `sync_recv` 与 `async_recv` 的含义

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

#### 3.2 `timeout_ms` 只控制等待排空

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

#### 3.3 冻结通知是另一条协议

客户端若持有某个远端 Binder 句柄（handle），可以通过 `addFrozenStateChangeCallback()` 请求冻结通知。libbinder 先检查 `freeze_notification` 功能文件，再发送 `BC_REQUEST_FREEZE_NOTIFICATION`；内核以 `BR_FROZEN_BINDER` 回传 `is_frozen` 与用于关联回调对象的 `cookie`。

这条协议用于判断持有的远端 Binder 是否发生冻结状态变化。`BINDER_GET_FROZEN_INFO` 则按 PID 查询冻结期间是否收到过事务。两者的对象、数据结构和使用目的不同。

以上接口属于平台原生 Binder 组件，不是 Android SDK 提供给普通应用的健康检查 API。能够打开相应 Binder 设备，也不代表产品的 SELinux 策略和调用方身份允许将它们用于任意进程管理。

### 四、扩展错误是线程级的一次性信息

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

Android 17 的 `logExtendedError()` 只为 `ENOSPC` 增加一段解释：Binder 缓冲区已满，事务过多或过大。其他 errno 仍使用通用错误字符串。`ENOSPC` 也不能单独证明“这一条 Parcel 超过固定 1 MiB”；同一接收进程的并发同步 / 异步分配都会消耗 Binder 映射与异步预算，需结合前文的分配器与异步预算一起判断。

### 五、`oneway` 嫌疑告警发生在发送端

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

### 六、AIDL Trace 提供方法名，不提供 Parcel 内容

这里的 AIDL Trace 指方法级时间轨迹：它给切片命名，方便把 Binder 活动对应到接口方法，但不会记录方法参数。

#### 6.1 libbinder 的服务端切片

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

#### 6.2 生成代码还可以增加客户端和服务端切片

C++ 后端在 `options.GenTraces()` 开启时，会分别在代理方法和服务端 Stub 分发代码中生成 `ScopedTrace`：

```cpp
::android::binder::ScopedTrace trace(
    ATRACE_TAG_AIDL,
    "AIDL::cpp::IExample::doWork::cppClient");
```

服务端对应名称以 `cppServer` 结尾。它们与 `BBinder::transact()` 的通用服务端时间片来自不同代码位置，因此同一线程轨道中可能出现嵌套时间片。遇到名称相近的 AIDL 时间片时，应检查名称后缀和所在进程 / 线程，不能按时间片数量推算调用次数。

源码没有给出“关闭时固定 10 ns”或“开启时固定多少微秒”的保证。关闭跟踪标签会绕过名称构造和 `trace_begin()`；开启后的成本与生成代码、名称处理、轨迹缓冲区和调用频率有关，应在目标设备上测量。

#### 6.3 最小 Perfetto 配置

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

### 七、API 37 的 Perfetto 表没有 `dispatch_dur`

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

### 八、`binder_txn_latency_free` 记录对象释放时刻

当前内核的 `binder_txn_latency_free` tracepoint 包含：

- 事务 `debug_id`；
- `from_proc/from_thread` 与 `to_proc/to_thread`；
- `code`、`flags`。

触发点位于 `binder_free_transaction()`。它说明某个内核 `binder_transaction` 对象何时被释放，可借助 `debug_id` 与 `binder_transaction` 事件关联。两事件的时间差是该内核对象的存活区间，不等于应用看到的端到端调用耗时：服务端何时释放接收缓冲区、错误路径以及 `oneway` 处理方式都会影响对象寿命。

当前 `binder_trace.h` 有 `binder_transaction` 和 `binder_transaction_received`，回复仍通过 `binder_transaction` 的 `reply` 字段表示；不存在名为 `binder_reply` 的 tracepoint，也不存在 `binder_freeze` tracepoint。诊断脚本应检查设备的 `/sys/kernel/tracing/events/binder/`，不要把界面中的 `binder reply` 时间片名称当成内核事件名。

### 九、debugfs 只能提供现场快照

debugfs（内核调试文件系统）路径 `/sys/kernel/debug/binder/`（或产品映射的对应调试目录）里的 `state`、`stats`、`transactions`、`transaction_log`、`failed_transaction_log` 和 `proc/<pid>`，用于查看当前对象、线程、buffer 与有限的事务记录。它们不是时序数据库：两次读取之间已经完成并释放的事务可能完全看不到，读取本身也无法恢复 runnable 延迟、锁等待或 CPU 执行区间。

逐进程文件适合回答“目标进程当下有多少 Binder 线程、哪些线程在等待、是否存在未释放 buffer、`free async space` 是否异常”；Perfetto 适合回答“事务何时发送、服务端何时开始、线程为何没有运行”。binderfs 的 `features/*` 是第三类信息，只表示驱动是否支持某项协议，不能当作运行状态或调用计数。

出现缓冲区压力时，应把 `binder_transaction_alloc_buf` 的 `data_size`、`offsets_size`、`extra_buffers_size` 与目标进程的并发事务、`free async space`、`oneway` spam 告警一起看。Java 层会根据事务失败时的上下文推测并报告 `TransactionTooLargeException`，它不是驱动用于表示“这一笔精确超过 1 MiB”的专用错误。

### 十、Parcel 与应用侧观测边界

Java `Parcel` 有对象池，带明确类型的 Parcelable 由生成代码或显式代码写入字段；原生 `Parcel` 会按实现策略扩容。无论使用 `byte[]`、`Bundle` 还是 Parcelable，大块数据都不会自动变成共享内存。需要传输图片、模型或批量二进制时，应使用文件描述符（FD）、共享内存或流式协议，只在 Parcel 中传控制信息和句柄。

应用侧的耗时埋点可以定位某个接口的分位数和失败率，但只能看到调用边界，不能独立解释 Binder 驱动、服务端排队与调度。采集时至少记录接口 / 方法、同步或 `oneway`、调用线程、目标进程、Parcel 估算大小和超时 / 错误类型；采样和聚合必须限制字段取值组合的数量（基数），不能在线上记录 Parcel 原文。

### 十一、RecordedTransaction 适合受控复现，不适合常驻监控

#### 11.1 启用条件

`RecordedTransaction` 同时受三个条件限制：

1. libbinder 编译时定义 `BINDER_ENABLE_RECORDING`，否则 `kEnableRecording` 为 `false`；
2. 使用内核 Binder；
3. 发起 `START_RECORDING_TRANSACTION` / `STOP_RECORDING_TRANSACTION` 的调用者 UID 为 root（超级用户）。

`startRecordingTransactions(const Parcel& data)` 从控制事务的 `Parcel` 中读取一个由 `unique_fd` 管理的文件描述符。同一个 `BBinder` 一次只允许一场录制。仅凭系统是 `userdebug` 构建不能确认该能力可用，还要检查目标产品的 libbinder 编译参数。

#### 11.2 它记录服务端收到的事务

录制代码位于 `BBinder::transact()`，在 `onTransact()` 返回后执行。它保存：

- `getInterfaceDescriptor()`；
- 事务 `code` 与 `flags`；
- `onTransact()` 返回状态；
- 请求 Parcel 的数据区与对象偏移；
- 回复 Parcel 的数据区；
- 调用 `timespec_get()` 时取得的时间戳。

时间戳在服务端处理完成后采集，不能当作事务开始时间。AOSP 的 `BpBinder` 发送路径没有与之对称的客户端录制入口，因此“客户端和服务端各打开一次就得到端到端录制”并不成立。端到端时间仍应由 Perfetto 的 Binder flow 解释。

#### 11.3 文件格式与风险

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

### 十二、一个可复用的诊断顺序

#### 12.1 慢事务

1. 用 Perfetto 抓 `binder`、`aidl` 与 `sched`；
2. 从 `android_binder_txns` 找出长 `client_dur`；
3. 比较 `server_ts` 与 `client_ts`，再检查客户端和服务端线程状态；
4. AIDL 时间片有方法名时定位到接口；没有名称时保留事务码和两端 PID / TID，回到服务定义核对；
5. 不用 `binder_txn_latency_free` 的对象寿命替代端到端耗时。

#### 12.2 冻结相关事务

1. 由负责进程冻结的系统组件记录冻结/解冻操作；
2. 把 `sync_recv` 当位图解析，禁止累计求和；
3. 需要观察句柄对应的远端状态变化时使用冻结通知；
4. 用 Binder 异步 flow 判断 `oneway` 是在冻结期间等待，还是服务端线程繁忙。

#### 12.3 失败与内容复现

1. 事务失败后在同一 Binder 线程读取扩展错误；
2. `ENOSPC` 先检查接收进程的缓冲区占用、大事务和并发异步事务；
3. 只有在系统轨迹与日志无法解释协议内容、设备可控且 libbinder 编译开关已打开时，才使用 `RecordedTransaction`；
4. 录制文件按敏感数据管理，完成分析后清理。

### 十三、源码锚点

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
