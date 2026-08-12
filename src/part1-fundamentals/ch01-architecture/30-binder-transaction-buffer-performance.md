---
title: "Android 17 Binder Transaction Buffer：内核分配、异步预算与 RPC 上限"
chapter: "1.30"
section: "1.30"
status: ready-for-review
applicable_versions: "Android 15 (API 35) - Android 17 (API 37)"
tags: [binder, ipc, transaction-buffer, performance, android17, rpc-binder]
related_chapters: ["1.4", "1.10", "1.17", "1.29", "1.38"]
last_verified: "2026-07-25"
last_verified_against: "AOSP android-17.0.0_r1 / android17-6.18-2026-06_r6"
confidence: high
sources:
  - type: aosp
    path: "frameworks/native/libs/binder/RpcState.cpp (android-15.0.0_r1)"
  - type: aosp
    path: "frameworks/native/libs/binder/Constants.h (android-16.0.0_r1)"
  - type: aosp
    path: "frameworks/native/libs/binder/Constants.h"
  - type: aosp
    path: "frameworks/native/libs/binder/ProcessState.cpp"
  - type: aosp
    path: "frameworks/native/libs/binder/RpcState.cpp"
  - type: aosp
    path: "frameworks/native/libs/binder/RpcTransportUtils.h"
  - type: aosp
    path: "frameworks/native/libs/binder/BpBinder.cpp"
  - type: aosp
    path: "frameworks/native/libs/binder/Binder.cpp"
  - type: aosp
    path: "frameworks/native/libs/binder/IPCThreadState.cpp"
  - type: aosp
    path: "frameworks/native/libs/binder/Parcel.cpp"
  - type: kernel
    path: "common/drivers/android/binder.c (android17-6.18-2026-06_r6)"
  - type: kernel
    path: "common/drivers/android/binder_alloc.c (android17-6.18-2026-06_r6)"
  - type: kernel
    path: "common/include/uapi/linux/android/binder.h (android17-6.18-2026-06_r6)"
  - type: official
    path: "https://developer.android.com/reference/android/os/TransactionTooLargeException"
  - type: official
    path: "https://developer.android.com/reference/android/os/SharedMemory"
  - type: official
    path: "https://source.android.com/docs/core/architecture/hidl/binder-ipc"
last_consolidated_at: "2026-08-11"
consolidated_from:
  - "src/part1-fundamentals/ch01-architecture/1.31-android17-binder-rpc.md"
  - "src/part1-fundamentals/ch01-architecture/1.44-android17-binder-sz4m-kernel-buffer-pool.md"
---

# 1.30 Android 17 Binder Transaction Buffer：内核分配、异步预算与 RPC 上限

Binder 不存在适用于所有调用的“单笔 1 MiB 上限”。kernel Binder 为每个进程建立接收事务的映射区，多笔在途请求、oneway、回复和 Binder object 会共同占用这块空间。RPC Binder 使用另一套传输和协议上限。“Binder 上限是 1 MiB”这种说法缺少并发、方向、异步预算和协议头等必要条件。

以下分析以 `android-17.0.0_r1` 和 `android17-6.18-2026-06_r6` 为准，覆盖映射区大小、驱动分配与回收、单向事务压力，以及 Android 17 中 600 KiB RPC 上限对应的路径。事务时序观测见 [1.31](31-binder-performance-recording-trace.md)，oneway 排队见 [1.29](29-binder-async-transaction-queue.md)。

## 一、三类大小边界

| 边界 | Android 17 的值或规则 | 约束对象 |
| --- | --- | --- |
| libbinder 映射请求 | `1 MiB - 2 × page size` | 一个 kernel Binder 进程的接收缓冲区 |
| Binder 驱动 mmap 上限 | `min(requested size, 4 MiB)` | 驱动接受的单个 `binder_alloc` 映射长度 |
| RPC Binder 协议上限 | `600 KiB`，还要扣除协议头与对象表 | 一条 RPC Binder 命令或回复包 |
| libbinder 大事务告警线 | `300 KiB` | kernel Binder 和 RPC Binder 的诊断告警，不是硬上限 |

第一行和第二行并不矛盾。Android 17 的 AOSP `ProcessState` 主动只映射约 1 MiB；kernel r6 最多接受 4 MiB，这是驱动对调用者请求的保护上限。普通 AOSP 进程不会因为驱动允许 4 MiB 就自动得到 4 MiB。

RPC Binder 不通过目标进程的 `/dev/binder` 映射区传输数据，因此 600 KiB 与 kernel Binder 的约 1 MiB 接收池不能互相替代。

## 二、kernel Binder 映射区如何建立

### 1. `BINDER_VM_SIZE` 的准确计算

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

16 KiB 页设备的映射长度比 4 KiB 页设备少 24 KiB。这个差值来自宏中的“两页”，不是驱动把每笔事务按 16 KiB 对齐。

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

这块用户虚拟地址用于接收驱动写入的事务。`MAP_NORESERVE` 表示不为映射预留交换空间；它不能推导出“Binder 页面不计入 RSS”。驱动在事务需要覆盖相应范围时安装后备物理页，内存统计仍要以目标内核和设备实测为准。

### 2. 映射属于接收方

kernel Binder 为目标进程分配请求 buffer。A 调用 B 时，请求占用 B 的 `binder_alloc`；B 返回同步回复时，回复占用 A 的 `binder_alloc`。因此，某个进程的压力既可能来自它作为服务端接收大量请求，也可能来自它作为客户端同时等待大量回复。

发送方用户态 `Parcel` 的内存是另一份数据。驱动将 Parcel data、offset 数组和附加 buffer 复制或修正到接收方映射区，不能把发送方 Parcel capacity 与接收方 Binder 空间视为同一个指标。

### 3. 驱动的 4 MiB 上限

kernel r6 的 `binder_alloc_mmap_handler()` 使用：

```c
alloc->buffer_size = min_t(
    unsigned long,
    vma->vm_end - vma->vm_start,
    SZ_4M
);
```

这个上限允许其他 Binder 用户态实现请求不同长度，同时阻止无限放大映射。AOSP `ProcessState` 仍传入 `BINDER_VM_SIZE`，所以最终 `alloc->buffer_size` 是前一节算出的 1016 KiB 或 992 KiB。

## 三、`binder_alloc` 如何分配一笔事务

### 1. 分配大小不只有 `data_size`

`binder_alloc_new_buf()` 接收三部分：

- `data_size`：Parcel 普通数据区；
- `offsets_size`：指向 Binder object、FD 等对象的偏移数组；
- `extra_buffers_size`：scatter-gather 附加缓冲区及相关数据。

kernel r6 的 `sanitized_size()` 分别把三者按 `sizeof(void *)` 对齐，再求和；零长度事务也至少占一个指针大小，以保证地址唯一。

```text
allocated = align(data_size, pointer_size)
          + align(offsets_size, pointer_size)
          + align(extra_buffers_size, pointer_size)
```

事务 buffer 按指针大小切分。页只负责后备范围，相邻小事务可以位于同一页。16 KiB 页会改变页面安装和回收粒度，不会让每个小事务固定浪费 16 KiB。

### 2. 最佳适配、切分与合并

`binder_alloc_new_buf_locked()` 在 free-buffer 红黑树中查找能容纳请求的最小 buffer。找到更大的空闲块后，驱动把它切成已分配部分和剩余 free buffer；释放时再与相邻空闲块合并。

分配成功后，`binder_install_buffer_pages()` 只安装覆盖该 buffer 所需的页面。页面级回收还要考虑相邻 buffer 是否在使用，因此 transaction buffer 释放与页面可回收发生在不同时间。

### 3. 空间不足直接失败

如果找不到合适的 free buffer，`binder_alloc_new_buf_locked()` 返回 `-ENOSPC`。异步预算不足也返回 `-ENOSPC`。这条路径不会阻塞等待旧 buffer 释放，也不会借 `BR_SPAWN_LOOPER` 扩大线程池。

`BR_SPAWN_LOOPER` 处理的是服务进程缺少可用 Binder 线程，与接收缓冲区分配失败属于不同问题。native 调用通常看到 `FAILED_TRANSACTION`；Java 层如何映射为 `TransactionTooLargeException` 或其他异常，取决于 JNI 的启发式规则，详见 [1.31](31-binder-performance-recording-trace.md)。

### 4. buffer 何时归还

接收方 libbinder 通过 `BR_TRANSACTION` 或 `BR_REPLY` 得到映射区地址，构造一个引用这段内存的 `Parcel`。处理完成后，release callback 向驱动发送 `BC_FREE_BUFFER`，驱动才把对应 `binder_buffer` 放回 free tree。

对于同步请求，Android 17 的 `IPCThreadState` 在发送回复前执行 `buffer.setDataSize(0)`，释放请求 buffer，避免客户端收到回复后立即发起下一笔调用时，旧请求仍占用服务端空间。

oneway 没有回复。它可能在目标进程或目标 node 的异步队列中等待，buffer 要到服务端完成处理并释放 Parcel 后才归还。高频 oneway 的 buffer 生命周期并不天然比同步调用短。

## 四、同步与异步共享地址池，但异步有预算

### 1. “一半给 oneway”不是两块物理分区

初始化 `binder_alloc` 时，kernel r6 设置：

```c
alloc->free_async_space = alloc->buffer_size / 2;
```

同步和异步事务仍从同一棵 free-buffer 树分配。`free_async_space` 是额外的记账预算：异步分配前检查预算，成功后扣减，释放后归还。同步事务不扣这项预算，但仍需要地址池中存在足够的连续 free buffer。

一半空间没有被提前划成 oneway 专用区。该预算只限制异步事务最多消耗的总量，为同步请求和回复保留余地。

### 2. oneway 的 node 级串行会延长占用

同一个 Binder node 的 oneway 事务按顺序处理。第一笔异步事务正在执行时，后续事务进入该 node 的 `async_todo`。当前 buffer 释放后，驱动才把下一笔移到目标进程的可执行队列。

如果生产速度高于服务端消费速度，多个 oneway buffer 会同时占据目标进程地址池；调用方已从 `BR_TRANSACTION_COMPLETE` 返回，也不代表服务端完成处理或 buffer 已经释放。

### 3. Android 17 kernel r6 的 spam 判定

kernel r6 只有在 `free_async_space < buffer_size / 10` 时才开始查找主要发送方，也就是剩余异步预算少于初始异步预算的 20%。随后按当前发送进程统计尚未释放的异步 buffer：

- buffer 数量超过 50；或
- 总占用超过 `buffer_size / 4`；

满足其一，当前 buffer 会被标记为 `oneway_spam_suspect`。libbinder 默认启用驱动检测，调用方收到 `BR_ONEWAY_SPAM_SUSPECT` 时记录调用栈。

这些是内核诊断条件，不是业务接口应追求的容量目标。接近这些条件时，目标进程的异步预算已经非常紧张。

## 五、FD、Binder object 与 scatter-gather 也占元数据空间

通过 Binder 传递 `ParcelFileDescriptor` 或 Binder object 时，大文件内容不会复制进 `data_size`，但事务仍包含 `flat_binder_object` 以及 offset 条目。驱动还要完成对象引用或 FD 的校验与转换。

FD 方案的主要价值是让大块数据留在文件、共享内存或其他专用缓冲区中，Binder 只承载描述符和控制信息。它不表示端到端没有数据复制：生产者可能先把数据写进共享区域，接收者也要 mmap、同步并管理生命周期。

Android 8 已引入 scatter-gather Binder。Android 17 的 `BC_TRANSACTION_SG` 可以通过 `binder_transaction_data_sg` 提供 `buffers_size`，驱动把相应内容计入 `extra_buffers_size`。它属于稳定演进机制，不是 Android 17 新增的应用开关。

## 六、怎样理解“大事务”与失败

### 1. 没有安全的固定单笔值

一笔事务能否成功，至少取决于：

- 目标进程当前剩余的连续 free buffer；
- 同时在途的请求与回复；
- 此调用的 data、offsets 和 extra buffers；
- oneway 是否还受 `free_async_space` 限制；
- 事务发送期间目标进程是否死亡或被冻结；
- 走 kernel Binder 还是 RPC Binder。

即使单笔数据明显低于映射长度，并发事务也可能使它失败。反过来，失败也不必然意味着本次 Parcel 本身接近 1 MiB。

### 2. 300 KiB 是主动告警线

Android 17 的 `Constants.h` 定义：

```cpp
constexpr size_t kLogTransactionsOverBytes = 300 * 1024;
```

`BpBinder` 对超过该值的发出 Parcel 记录 `Large outgoing transaction`。`BBinder` 对超过该值的请求和回复分别记录 `Large data transaction`、`Large reply transaction`。

这条线比常见映射长度小很多，因为大事务会增加复制成本，并挤压同一进程的并发空间。日志出现不等于当前事务必然失败，但应检查接口是否把大块数据、无界列表或图片直接塞进 Parcel。

### 3. 服务端 1000 ms 日志测的是执行区间

Android 17 的 `BBinder::transact()` 从进入方法开始计时；超过 1000 ms 时记录接口、方法、请求字节数、回复字节数和 flags。这个区间主要覆盖服务端 `onTransact()` 及其嵌套工作，不是调用方端到端耗时，也不含事务到达服务线程之前的全部等待。

### 4. Perfetto 的大小证据

kernel r6 的 `binder_transaction_alloc_buf` tracepoint 直接给出 `data_size`、`offsets_size`、`extra_buffers_size`，并通过 transaction id 与 `binder_transaction` 关联。Perfetto 标准 `android_binder_txns` 表没有通用的 `dataSize`/`replySize` 列；分析大小时，应在录制中加入该 ftrace event，再查看原始事件参数。

debugfs `stats` 还能看到逐进程 buffer 数量和 `free async space`，但它是快照，不能代替 transaction 级时间轴。

## 七、RPC Binder 的 600 KiB 边界

### 1. 版本变化发生在 Android 16

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

### 2. Parcel 可用空间小于 600 KiB

`RpcState::transactAddress()` 计算的 `bodySize` 包含 `RpcWireTransaction`、Parcel data 和对象表，并要求：

```cpp
bodySize < kRpcTransactionLimitBytes - sizeof(RpcWireHeader)
```

因此，应用可用的 Parcel data 必须小于 600 KiB，还要为协议结构和对象表留出空间。回复使用同样的包级约束；超出时，服务端清空回复数据，并以 `FAILED_TRANSACTION` 返回。

`CommandData` 的动态分配也拒绝超过 600 KiB 的请求。`RpcTransportUtils` 把 600 KiB 用作初始最大传输 chunk，并可在底层返回 `ENOMEM` 时缩小 chunk 重试。传输分块不会放宽整个 RPC 命令的协议上限。

### 3. 它不影响普通 App 到系统服务的 kernel Binder

`BpBinder::transact()` 先判断 `isRpcBinder()`：RPC endpoint 交给 `RpcSession`，其余交给 `IPCThreadState` 和 kernel Binder。普通 App 调用 Activity Manager、Package Manager 或 ContentProvider 通常属于后一条路径，不会因为 RPC 上限从 100 KB 变为 600 KiB 就获得更大的 kernel Binder 空间。

`Constants.h` 的注释将设限原因归于 Baklava 时期 RPC Binder 尚不支持共享内存。Android 17 tag 仍保留同一常量和注释；设计 RPC 接口时应遵守 600 KiB 包级上限，不能假设存在自动共享内存后备路径。

## 八、`TF_ONE_WAY` 与 `TF_CLEAR_BUF` 的 buffer 语义

### 1. `TF_ONE_WAY`

`TF_ONE_WAY` 让调用方不等待回复，但数据仍要在目标进程成功分配并复制。`BR_TRANSACTION_COMPLETE` 只说明驱动接受了发送请求；服务端执行、oneway node 排队和 buffer 回收都可能发生在之后。

适合 oneway 的接口应当无需返回结果、允许异步处理并有容量控制。把同步方法机械改成 oneway，只会把调用方等待变成目标进程的隐式队列和异步空间压力。

### 2. `TF_CLEAR_BUF`

kernel r6 在创建目标 `binder_buffer` 时把 `TF_CLEAR_BUF` 写入 `clear_on_free`。释放 buffer 前，`binder_alloc_clear_buf()` 遍历后备物理页，把整个 buffer 清零后再归还 allocator。

同步调用中，Android 17 的 `IPCThreadState` 会把 `TF_CLEAR_BUF` 转发给回复；`BBinder::transact()` 还会对用户态回复 Parcel 调用 `markSensitive()`，使 libbinder 在释放自己拥有的数据区前清零。因此，该 flag 同时覆盖接收方 kernel buffer 和相关用户态回复数据，不能写成“只清用户态、不清内核”。

清零成本随 buffer 覆盖范围增加，源码没有承诺固定微秒数。它是敏感数据的安全语义，不能为了减少耗时随意移除；应避免把大块敏感数据放进 Parcel。

## 九、16 KiB 页设备上的影响

16 KiB 页带来两个可直接从源码确认的变化：

1. `BINDER_VM_SIZE` 从 4 KiB 页设备的 1016 KiB 变为 992 KiB；
2. `binder_install_buffer_pages()` 和 page LRU 以 16 KiB 为安装、回收粒度。

事务 buffer 的逻辑大小仍按指针宽度对齐，多个小 buffer 可以共享一页。较大的页面可能改变后备物理页数量、回收时机和内存局部性，但“每个小事务多浪费 12 KiB”之类结论无法从 allocator 得出，必须通过实测验证。

做 4 KiB/16 KiB 对比时，应固定 APK、调用并发、Parcel 分布和设备内存状态，并分别报告 transaction 大小、失败率、页面统计与端到端时延。

## 十、接口设计与验证方法

### 1. 控制数据可以直接走 Parcel

固定字段、数量有界的小型请求适合 AIDL structured Parcelable。使用 typed collection，避免通用 Bundle 携带不受控对象；服务端同时校验元素数、字符串长度和嵌套集合深度。

不要按“20 个操作”或“500 KB 以下”写死通用规则。同一种 `ContentProviderOperation` 的 URI、selection、values 和 back reference 都会改变 Parcel 大小。批量接口应同时限制 item count 和预估字节数，并在压力测试中记录序列化后的大小。

### 2. 大块数据使用描述符协议

图片、模型、媒体帧、大型表格或可重复访问的数据更适合文件、`ParcelFileDescriptor`、`SharedMemory` 或领域专用共享 buffer。Binder 只传递描述符、offset、length、格式、版本和所有权。

协议还要明确：

- 谁创建和关闭 FD；
- 何时允许复用或覆盖；
- 读写权限与 `SharedMemory.setProtect()`；
- 生产者与消费者之间如何同步；
- 对端死亡后的清理；
- 长度、offset 与整数溢出的校验。

### 3. 为 oneway 建立背压

oneway 接口可以用序列号合并过时状态，用有界窗口限制未确认事件，或将高频细粒度事件聚合成批次。生产速度需要长期低于消费速度，不能等到驱动发出 spam suspect 才处理。

### 4. 同时测单笔大小和并发

建议至少覆盖以下用例：

1. 单请求逐步增加 data、object 和 extra buffer；
2. 多线程并发同步请求；
3. 服务端故意延迟消费 oneway；
4. 请求小、回复大，以及请求大、回复小；
5. 4 KiB 与 16 KiB 页设备；
6. kernel Binder 与 RPC Binder 分开测试；
7. Perfetto 记录 `binder_transaction_alloc_buf`，复现前后读取 debugfs stats；
8. 检查 300 KiB 日志、`FAILED_TRANSACTION`、扩展 `ENOSPC` 和 oneway spam 日志。

只有把事务大小分布与并发数放在一起，才能解释“同一个调用有时成功、有时失败”。

## 十一、Android 17 源码核对入口

| 结论 | 文件与入口 |
| --- | --- |
| AOSP 映射长度 | `ProcessState.cpp`：`BINDER_VM_SIZE`、`mmap()` |
| 驱动 4 MiB 上限、async 初始预算 | `binder_alloc.c`：`binder_alloc_mmap_handler()` |
| 大小对齐、最佳适配与 `-ENOSPC` | `binder_alloc.c`：`sanitized_size()`、`binder_alloc_new_buf_locked()` |
| oneway spam 条件 | `binder_alloc.c`：`debug_low_async_space_locked()` |
| kernel buffer 清零 | `binder.c`：`clear_on_free`；`binder_alloc.c`：`binder_alloc_clear_buf()` |
| 300 KiB 日志与 600 KiB RPC 上限 | `Constants.h` |
| RPC 请求/回复包级检查 | `RpcState.cpp`：`transactAddress()`、回复发送路径 |
| 传输 chunk | `RpcTransportUtils.h`：`kChunkMax` |
| 大事务与慢事务日志 | `BpBinder.cpp`、`Binder.cpp` |
| 请求释放与 clear flag 转发 | `IPCThreadState.cpp`：`BR_TRANSACTION` 处理分支 |

分析 Transaction Buffer 时，应标明目标进程、事务方向、kernel/RPC 通道、同步/oneway 和并发数。缺少这些条件，“1 MiB 上限”只是容易误导的近似说法。
