---
title: IPC 全景：Android 进程间通信机制对比与性能选型
chapter: '1.17'
section: '1.17'
status: finalized
applicable_versions: Android 8.0 (API 26) - Android 17 (API 37)
last_verified: '2026-07-25'
last_verified_against: AOSP android-17.0.0_r1 + Android 17 API 37 official documentation
confidence: high
sources:
  - type: official
    path: "https://source.android.com/docs/core/architecture/ipc/binder-overview"
  - type: official
    path: "https://source.android.com/docs/core/architecture/aidl"
  - type: official
    path: "https://developer.android.com/reference/android/os/IBinder"
  - type: official
    path: "https://developer.android.com/reference/android/os/TransactionTooLargeException"
  - type: official
    path: "https://developer.android.com/reference/android/os/SharedMemory"
  - type: official
    path: "https://developer.android.com/reference/android/database/CursorWindow"
  - type: official
    path: "https://source.android.com/docs/core/architecture/kernel/dma-buf-heaps"
  - type: official
    path: "https://source.android.com/docs/core/architecture/hidl/fmq"
  - type: official
    path: "https://source.android.com/docs/core/architecture/aidl/fmq"
  - type: official
    path: "https://source.android.com/docs/core/architecture/hal"
  - type: official
    path: "https://source.android.com/docs/core/architecture/aidl/aidl-hals"
  - type: official
    path: "https://source.android.com/docs/core/virtualization/microdroid"
  - type: official
    path: "https://perfetto.dev/docs/analysis/stdlib-docs"
  - type: aosp
    path: "frameworks/native/libs/binder/ProcessState.cpp @ android-17.0.0_r1"
  - type: aosp
    path: "frameworks/native/libs/binder/Parcel.cpp @ android-17.0.0_r1"
  - type: aosp
    path: "frameworks/native/libs/input/InputTransport.cpp @ android-17.0.0_r1"
  - type: aosp
    path: "system/core/libutils/Looper.cpp @ android-17.0.0_r1"
  - type: aosp
    path: "system/core/libcutils/ashmem-dev.cpp @ android-17.0.0_r1"
  - type: aosp
    path: "frameworks/base/libs/androidfw/CursorWindow.cpp @ android-17.0.0_r1"
  - type: aosp
    path: "bionic/libc/platform/bionic/reserved_signals.h @ android-17.0.0_r1"
tags:
  - android
  - ipc
  - binder
  - aidl
  - unix-domain-socket
  - pipe
  - shared-memory
  - mmap
  - dma-buf
  - fmq
  - rpcbinder
related_chapters:
  - '1.4'
  - '1.10'
  - '1.13'
  - '2.15'
  - '4.1'
  - '9.1'
pipeline_stage: ready-to-publish
task6_state: reviewed
task9_state: reviewed
task2b_state: fixed
---

# 1.17 IPC 全景：Android 进程间通信机制对比与性能选型

Android IPC 无法简化为“Binder、Intent、共享内存三选一”。Intent 和 AIDL 描述上层语义；Binder、Unix domain socket 和 vsock 负责传输；共享内存、DMA-BUF 与 FMQ 又常被用作数据面。一条真实链路经常同时使用两到三层机制。

当前锚点为 Android 17 / API 37、AOSP `android-17.0.0_r1`。分析从源码、fd、线程和 trace 还原真实链路，不为各种机制设定脱离条件的固定延迟。

## 1. 先按职责分类，不按 API 名堆清单

```text
上层语义 / 框架抽象
├─ AIDL、Messenger、ResultReceiver
├─ Intent、BroadcastReceiver
└─ ContentProvider / Cursor

控制面 transport
├─ Binder：/dev/binder
├─ HIDL / HwBinder：/dev/hwbinder（存量 HAL）
├─ Unix domain socket：命名 socket 或 socketpair
├─ Pipe：单向字节流
└─ Binder RPC over socket / AF_VSOCK 的 Binder RPC：host ↔ pVM

数据面 / 共享对象
├─ SharedMemory / mmap
├─ CursorWindow
├─ DMA-BUF / AHardwareBuffer / GraphicBuffer
└─ FMQ：共享内存环形队列

通知与唤醒
├─ eventfd
└─ Signal
```

这四层会组合：

- AIDL 定义接口，普通跨进程调用由 Binder 承载。
- Binder 先传递 `SharedMemory` fd，之后双方直接读写映射。
- InputManager 通过 Binder 把 `InputChannel` fd 交给 App，后续输入事件走 Unix `SOCK_SEQPACKET`。
- HAL 用 AIDL/HIDL 建立 FMQ，持续数据走共享内存队列。
- Microdroid 复用 Binder/AIDL 对象模型，但传输改为 socket/vsock。

同一套 API 也可能不跨进程。AIDL 的 client 与 service 在同一进程、使用同一 backend 时可以直接调用，不产生 Parcel 编组和 Binder driver 事务。分析前先确认 PID。

## 2. 选型先回答六个问题

### 2.1 需要 RPC 还是流

- “调用方法并拿到结果”是 RPC，Binder/AIDL 最自然。
- “持续传任意长度字节流”更接近 socket 或 pipe。
- “持续传定长元素”可考虑 FMQ。
- “共享一块大对象”可考虑 SharedMemory 或 DMA-BUF。

### 2.2 payload 是控制信息还是大数据

控制信息适合 Parcel：方法号、少量参数、token、fd、状态码。图像、音频帧、模型权重或大型结果集不应反复内联到 Parcel；常见做法是只传 handle / fd / descriptor。

### 2.3 谁拥有内存，谁负责回收

IPC bug 通常源于所有权不清，传输本身并没有失败：

- Binder object 何时调用 `linkToDeath()`、何时释放引用。
- fd 是借用、dup 后拥有，还是随 `ParcelFileDescriptor` 关闭。
- mmap 何时 unmap，SharedMemory 何时 close。
- DMA-BUF fence 未完成前谁不能复用 buffer。
- FMQ writer 或 reader 死亡后如何重建。

### 2.4 需要什么顺序和背压

- 同步 Binder 自带请求/回复和调用线程阻塞。
- oneway 没有业务回复，但仍受 driver queue 和服务端处理速度约束。
- socket/pipe 由内核 buffer 提供背压，写满后阻塞或返回 `EAGAIN`。
- FMQ 容量固定，需要明确 overflow/underflow 语义。
- 共享内存本身没有消息边界、顺序或唤醒。

### 2.5 安全边界在哪里

Binder 提供 calling UID/PID、对象引用与 SELinux binder policy；socket 依赖 socket namespace、文件权限、peer credentials 和 SELinux；fd 传递则把内核对象的访问能力交给对端。共享内存若未降低 protection，对端可能获得超出预期的写权限。

### 2.6 如何证明性能结论

IPC 延迟至少包含：

```text
client 编组
+ driver / kernel transport
+ server 排队与调度
+ server 业务
+ reply 编组与返回
```

固定写“Binder 0.5ms、Socket 0.1ms、Pipe 0.05ms”没有工程价值。payload、CPU、build、线程池、SELinux、调度和服务端工作稍有变化，数字就会改变。需要比较时，应在同一设备上用相同负载、同步语义和统计口径做基准。

## 3. Binder：Android 控制面的主干

### 3.1 一次同步调用发生了什么

以跨进程 AIDL 为例：

```text
client method
  └─ Proxy 将方法号与参数写入 Parcel
       └─ ioctl 到 Binder driver
            └─ driver 把 transaction 复制到 server receive mapping
                 └─ server Binder thread
                      └─ Stub 解包并调用实现
                           └─ reply Parcel 原路返回
```

Binder 不是端到端零拷贝。Android 8 的 scatter-gather 优化减少了额外编组复制，但 driver 仍要把 transaction 内容复制到目标进程地址空间；复杂 Parcelable 仍有编码、对象表、字符串和容器处理成本。

### 3.2 同步与 oneway

同步 transaction 要等服务端返回。调用方看到的 wall time 可能来自：

- 服务端 Binder thread 尚未空闲。
- 服务端拿锁、做 I/O 或调用下一个 Binder 服务。
- 调用方等待回复时被调度出去。
- reply 本身过大或编组昂贵。

`oneway` 只表示远程调用不等待业务返回，不表示：

- 不经过 Binder driver。
- 永不排队或永不失败。
- 服务端可以无限快消费。
- 任意 oneway 调用全局有序。

多个 oneway 调用只有在发往同一个 `IBinder` object 时，才保证按发送顺序一次分发一个；不同 Binder object，或 oneway 与同步调用混用时，没有这项顺序保证。若调用是同进程直调，`oneway` 也不会把它自动变成异步。

### 3.3 1MB 是共享预算，不是安全 payload 上限

Java `TransactionTooLargeException` 文档把 Binder transaction buffer 描述为当前 1MB，并强调它由进程所有进行中的 transaction 共享。Android 17 native `ProcessState.cpp` 的 receive mapping 更具体：

```cpp
#define BINDER_VM_SIZE \
        ((1 * 1024 * 1024) - sysconf(_SC_PAGE_SIZE) * 2)
```

因此：

- 4KB page 设备：约 1016KiB。
- 16KB page 设备：约 992KiB。

这仍不是“单个请求可放心塞到 992KiB”的承诺。同一进程的并发请求、回复、对象元数据和对端 receive buffer 都会占空间。异常发生时，client 甚至无法可靠区分请求尚未发出还是回复过大。

工程规则很简单：transaction 保持小；大数据使用 fd、分页或流传递。

### 3.4 默认 15 不是“进程总共只有 15 个 Binder 线程”

Android 17 `ProcessState.cpp`：

```cpp
#define DEFAULT_MAX_BINDER_THREADS 15
```

这个值配置的是 driver 可以按需启动的 threadpool 线程默认上限。`startThreadPool()` 启动的线程、主动调用 `joinThreadPool()` 的线程，以及进程自行调整的配置会影响总数。把它口语化成“每个进程固定 16 个 Binder 线程”会误导容量分析。

判断线程池是否饥饿，应看：

- server Binder threads Binder 线程是否全在执行或阻塞。
- client transaction 是否长时间等不到 server slice。
- 服务端是否在 Binder thread 上做阻塞 I/O、跨服务调用或持有大锁。
- `binder thread pool ... starved` 类日志是否出现。

### 3.5 Binder object、fd 与普通字节不是一回事

Parcel 除普通数据外，还维护对象表。它可以传：

- Binder object/ handle。
- file descriptor（`BINDER_TYPE_FD`）。
- native handle 中的一组 fd 与整数。

driver 会为接收方安装/复制相应引用或 fd。传 fd 后，后续大数据不必继续进入 Parcel，但双方仍要定义：

- fd 的访问权限。
- 由谁 close。
- 是否允许写。
- 对端死亡后的清理。
- 数据完成条件。

## 4. AIDL、Messenger、Intent 和 Provider 在哪一层

### 4.1 AIDL 是接口与编组语言

AIDL 编译器为接口生成 Proxy/Stub 和类型编解码代码。跨进程时走 Binder；同进程使用同 backend 时可以直接调用。

```text
client interface call
  ├─ local object → direct call
  └─ remote proxy
       └─ Parcel + Binder transaction
            └─ server stub + implementation
```

AIDL 解决类型契约、版本与 backend，不改变底层 transaction buffer 约束。把一个 5MB `byte[]` 换成 AIDL 参数，并不会自动变成共享内存。

### 4.2 Messenger 是 Handler 语义叠在 Binder 上

Messenger 用 Binder 传 `Message`，接收端最终把消息投递到指定 Handler / Looper。它适合不希望自己管理并发 RPC、而是希望按某个 Looper 顺序处理的场景。

“Messenger 是单线程 Binder”也不够准确：

- transport 仍是 Binder。
- Binder 收到消息后再投递 Handler。
- 一个 Messenger 入口的消息由它绑定的 Handler / Looper 串行分发；Handler 内部是否再把工作拆到线程池并行执行，由应用决定。
- Message payload 仍受 Parcel 与 transaction buffer 限制。

### 4.3 Intent 与 Broadcast 是系统调度协议

`Intent` 是描述操作、组件和 extras 的 Parcelable，不是独立内核 IPC。跨进程组件启动或广播通常经过 `system_server` 中的 ActivityManager 等服务，再由 Binder 调用目标进程。

它附带的是更高层语义：

- 组件解析与 exported/permission 检查。
- 生命周期和进程启动。
- 后台启动、广播队列与缓存进程策略。
- ordered broadcast 的结果传播。

因此 Intent 性能不能只用“一次 Binder 耗时”解释。冷启动目标进程、组件调度和生命周期回调的成本通常远大于 transport 本身。

### 4.4 ContentProvider 不等于“Binder + 共享内存”一条固定路径

Provider 的 query/insert/update/delete 是框架层 RPC，跨进程控制调用由 Binder 承载。query 返回的数据窗口常使用 `CursorWindow`，但小窗口和大窗口路径不同。

Android 17 `CursorWindow.cpp`：

- 初始 inline capacity 为 16KiB。
- 数据能放下时，跨进程可把 compacted window 内联写入 Parcel。
- 需要更大空间时才 inflate 到 ashmem-compatible region。
- 大窗口通过 fd 传递，对端使用只读 mmap。

“所有 ContentProvider 结果都零拷贝”不成立。列值填充、CursorWindow 构建、inline copy 或共享区域初始化仍有 CPU 和内存成本。

### 4.5 ResultReceiver 是回调抽象

跨进程 `ResultReceiver` 内部同样依靠 Binder callback。它适合一次或少量结果通知，不适合无界数据流。结果 `Bundle` 仍要保持小，并处理接收方生命周期。

## 5. Unix domain socket

Unix domain socket 提供本机字节流或有消息边界的 packet 语义，常见类型包括：

- `SOCK_STREAM`：连续字节流，无消息边界。
- `SOCK_SEQPACKET`：保留消息边界与顺序。
- 命名 socket：由 init 创建在 `/dev/socket/*` 等 namespace。
- 匿名 `socketpair()`：创建一对已连接 fd。

它没有 Binder 的“transaction 共享 1MB receive mapping”口径，但仍受 socket send/receive buffer、单个 packet、内存和协议 framing 约束。大流可以分块持续发送，不等于单次 `send()` 没有上限。

### 5.1 InputChannel：Binder 交 fd，socket 传事件

Android 17 `InputChannel::openInputChannelPair()`：

```cpp
socketpair(AF_UNIX, SOCK_SEQPACKET, 0, sockets);
```

InputDispatcher 持有 server 端；client 端作为 Parcelable 经 Binder 交给窗口所在进程。之后：

- input event 走这对匿名 Unix socket。
- App 处理完成的 finish signal 也走同一 channel。
- Binder 主要负责 channel 生命周期和控制，不搬运每个 MotionEvent 的数据。

这条链是“Binder 控制面 + socket 数据面”的典型例子。

### 5.2 `SCM_RIGHTS`：socket 也能传 fd

Unix socket 可用 `sendmsg()` / `recvmsg()` 和 `SCM_RIGHTS` 把 fd 交给对端。它传递的是对同一内核对象的新引用，不会把文件内容复制进 ancillary data。

接收方必须：

- 校验 fd 数量和类型。
- 设置/确认 `CLOEXEC`。
- 定义 close 时机。
- 不信任对端提供的文件大小、offset、格式或权限。

### 5.3 什么时候比 Binder 更合适

Unix socket 更适合：

- 已有流式 framing 协议。
- 需要长连接和显式 backpressure。
- 非 Android Binder 环境也要复用协议。
- 需要 packet 边界或 bidirectional byte stream。

它不自动提供 Binder object identity、calling UID API、death recipient 和服务管理。把系统服务从 Binder 改成 socket，往往要自己补回身份、授权、版本、生命周期和错误协议。

## 6. Pipe、eventfd 与 Signal

### 6.1 Pipe：单向字节流

`pipe()` 创建 read fd 和 write fd：

- 单向。
- 没有消息边界。
- 由有限 kernel buffer 提供背压。
- 常通过 fork 继承或显式传递 fd 建立连接。

Android/Java 常见场景是 `ProcessBuilder` / `Runtime.exec()` 的 stdin、stdout、stderr。需要双向通信时要两条 pipe，或直接使用 socketpair。

### 6.2 Looper 当前使用 eventfd

本书覆盖 Android 8–17。`android-17.0.0_r1` 的 `Looper.cpp` 在构造时：

```cpp
mWakeEventFd.reset(
        eventfd(0, EFD_NONBLOCK | EFD_CLOEXEC));
epoll_ctl(mEpollFd.get(), EPOLL_CTL_ADD,
          mWakeEventFd.get(), &wakeEvent);
```

`wake()` 向 eventfd 写入一个 64-bit 计数，`epoll_wait()` 被唤醒后再读取。Pipe 是更早实现的历史背景，不应拿来解释当前 MessageQueue 唤醒路径。

eventfd 主要传递计数/通知，不承载业务 payload。跨进程使用时，双方仍需继承或传递 fd。

### 6.3 Signal：异步通知，不是数据通道

Signal 的交付仍受目标线程调度、signal mask 和 handler 行为影响，不能写成“内核直接中断，延迟为零”。标准 signal 通常只表达编号；带 `siginfo_t` 的机制能附带少量元数据，但依然不适合业务数据流。

Android 常见用途：

| Signal | 用途 |
| --- | --- |
| `SIGQUIT` | 请求 ART/进程生成 Java stack 信息，ANR 流程会使用 |
| `BIONIC_SIGNAL_DEBUGGER` | debuggerd native dump/tombstone 内部通道 |
| `SIGABRT` | 主动 abort，进入 native crash 流程 |
| `SIGKILL` | 不可捕获、不可忽略的强制终止 |

Android 17 bionic 把 `BIONIC_SIGNAL_DEBUGGER` 定义为 `__SIGRTMIN + 3`。这是平台保留信号，App 不应复用。

Signal handler 还受 async-signal-safe 规则约束。不要在 handler 里分配内存、获取普通 mutex、记录复杂日志或调用非安全 API。

## 7. SharedMemory 与 mmap

### 7.1 共享页不等于端到端零拷贝

共享内存建立后，两个进程可以访问同一组物理页，持续读写无需每条消息再经 kernel transport copy。但仍可能发生：

- producer 把数据复制进共享区域。
- page fault、页表建立和 cache miss。
- CPU 与设备之间的 cache maintenance。
- consumer 再复制到自己的数据结构。

更准确的表述是“数据面可避免重复 IPC copy”，不能把整条业务链写成“0 copy”。

### 7.2 Java `SharedMemory`

`android.os.SharedMemory` 从 API 27 提供，可通过 Parcelable 传 fd：

```java
SharedMemory shm = SharedMemory.create("model-input", size);
ByteBuffer writable = shm.mapReadWrite();
try {
    writable.put(payload);
} finally {
    SharedMemory.unmap(writable);
}

if (!shm.setProtect(OsConstants.PROT_READ)) {
    shm.close();
    throw new IllegalStateException("failed to remove write access");
}

try {
    remote.consume(shm);
} finally {
    shm.close();
}
```

`setProtect()` 只能移除权限，不能重新增加。它只约束之后创建的 mapping；已有可写 mapping 保持原权限。因此“写入 → unmap → 降为只读 → 传给对端”是更清晰的 least-privilege 顺序。

接收方 map 后也要 unmap，并关闭自己收到的 fd wrapper。发送方 close 不会立即让接收方复制的 dup fd 失效。

### 7.3 `MemoryFile` 是兼容包装

Android 17 `MemoryFile.java` 已明确写成 `SharedMemory` wrapper。新代码通常优先使用 SharedMemory；MemoryFile 的 purgeable 兼容行为不应被当作新的通用共享内存设计基础。

### 7.4 Android 17 的 ashmem 兼容 fd 可能由 memfd 承载

`ashmem_create_region()` 是兼容 API 名，不保证底层一定是 legacy `/dev/ashmem`。Android 17 `ashmem-dev.cpp` 的默认判定是：

1. kernel/SELinux policy 支持 `memfd_class` capability。
2. `ro.vendor.api_level >= 202604`。
3. 当前 application target SDK >= 37。

满足后走 `memfd_create()`；否则回到 ashmem device。`sys.use_memfd=true` 仍可用于强制 override，源码注明未来会移除。

因此调试时要看 `/proc/<pid>/fd/*`、maps 和设备属性，不能只看 Java API 名推断底层对象。

## 8. `Parcel::writeBlob()`：16KiB 分界的真实含义

Android 17 C++ `Parcel.cpp` 定义：

```cpp
static const size_t BLOB_INPLACE_LIMIT = 16 * 1024;

if (!mAllowFds || len <= BLOB_INPLACE_LIMIT) {
    // BLOB_INPLACE
} else {
    // ashmem_create_region + mmap + fd in Parcel
}
```

边界是：

- `len <= 16KiB`：inline。
- `len > 16KiB` 且 Parcel 允许 fd：创建 ashmem-compatible region，映射后通过 Parcel 传 fd。
- `len > 16KiB` 但不允许 fd：仍走 inline。

`writeBlob()` 返回可写区域给调用者，数据仍要被写进 inline buffer 或共享 mapping。fd 分支避免把整块 blob 再次塞进 Binder transaction buffer，但 producer 仍有写入成本。

这个行为也不能外推成“所有大 AIDL `byte[]` 自动走共享内存”。只有实际使用 blob/fd-backed Parcelable 的路径才有这项分流。普通 byte array 仍会被内联编组。

## 9. DMA-BUF、GraphicBuffer 与共享内存不是同一条线

DMA-BUF 解决的是 CPU、GPU、display、camera、codec 等设备之间共享 buffer：

- allocator 返回 DMA-BUF fd/ native handle。
- gralloc 描述 format、stride、usage 和 plane layout。
- Binder 传 handle 与生命周期控制。
- fence 表达 producer/consumer 完成时序。

Android 12 的 GKI 2.0 路线用 DMA-BUF heaps 替代 ION allocator；每个 heap 通常表现为 `/dev/dma_heap/<name>`。这项迁移不等于 SharedMemory 从 ashmem 迁到 DMA-BUF。

| 对象 | 主要用途 | 同步 |
| --- | --- | --- |
| SharedMemory / memfd / ashmem-compatible region | CPU 进程间共享普通字节 | 原子、锁、协议、eventfd |
| DMA-BUF / AHardwareBuffer / GraphicBuffer | CPU 与硬件设备共享结构化 buffer | sync fence、cache/coherency 规则 |
| mmap file | 文件页映射与持久化共享 | 文件锁、数据库协议、原子/锁 |

图像数据走 DMA-BUF，也不等于 App 可以忽略 format、stride、usage 和 fence。

## 10. FMQ：共享内存上的有界单向队列

FMQ 先通过 HIDL 或 AIDL RPC 传递 `MQDescriptor`，双方映射 ring buffer、读写位置和可选 event flag。建立完成后，非阻塞 read/write 不需要每条消息进入 Binder driver。

单个 FMQ 的基本约束：

- 只有一个 writer。
- synchronized queue：一个 reader，不允许 overflow。
- unsynchronized queue：可有多个 reader，writer 可覆盖旧数据；落后的 reader 会丢数据。
- 两种 queue 都不允许 underflow。
- bidirectional 协议通常需要两条方向相反的 queue。

因此把 FMQ 表格写成“天然双向”是错误的。它适合固定布局、频繁、小单元的数据流，不适合：

- 可变长复杂对象。
- 含 pointer、Binder interface 或任意嵌套 buffer 的 payload。
- 需要每条消息独立权限检查的协议。
- 无界队列。

HIDL FMQ 从 Android 8 提供；AIDL NDK backend 从 Android 12 可使用 FMQ。Java backend 可以转交 descriptor，但没有 Java FMQ library 直接读写队列。

## 11. HAL IPC：HIDL/hwbinder 与 Stable AIDL / binder

Android 8 的 Treble 用 HIDL 和独立的 `/dev/hwbinder` domain 固化 framework/vendor 边界。Android 10 引入稳定 AIDL 机制，Android 11 开始允许 HAL 使用 AIDL。Stable AIDL HAL：

- 使用 `/dev/binder`。
- vendor native code 使用 NDK 或 Rust backend 等稳定 runtime。
- 通过 VINTF、frozen interface version 和 VTS 管理兼容性。

HIDL 从 Android 13 起 deprecated，但既有 HIDL HAL 仍受支持。分析 Android 17 设备不能凭 OS 版本断言“所有 HAL 都已 AIDL 化”。

| HAL 接口 | 常见 driver domain | 当前定位 |
| --- | --- | --- |
| HIDL binderized HAL | `/dev/hwbinder` | 存量兼容，不用于新接口 |
| Stable AIDL HAL | `/dev/binder` | 新实现优先 |
| `/dev/vndbinder` + vndservicemanager | vendor 进程间旧 AIDL | Android 11 起 deprecated |

控制调用之外，音频、相机、传感器和图形仍常把持续数据放在 FMQ、SharedMemory 或 DMA-BUF 中。AIDL/HIDL 决定接口语言和控制 transport，不等于高吞吐 payload 必须内联。

## 12. AVF：Binder RPC over vsock

Microdroid/pVM 不能直接使用 host 的 Binder driver。Binder RPC 保留 AIDL/Binder object 模型，把协议改为 socket transport；pVM 场景通常使用 AF_VSOCK。

```text
host RpcSession
  └─ Binder RPC framing
       └─ AF_VSOCK / virtio transport
            └─ pVM RpcServer root Binder object
```

它不继承 kernel Binder 的 `BINDER_VM_SIZE` receive mapping，也不能套用“Binder driver 一次 copy”的结论。开销要拆成：

- Parcel / Binder RPC framing。
- socket/vsock buffer 与 virtio。
- VM 调度和服务端工作。

AVF 还限制 pVM 之间直接通信；host 的 VirtualizationService 控制连接建立。大文件交换可使用 AuthFS 等专门通道，不能依赖超大的 Binder RPC transaction。

## 13. 定性对比

| 机制 | 消息/数据语义 | 背压与顺序 | 大数据策略 | 主要风险 |
| --- | --- | --- | --- | --- |
| Binder sync | 方法调用 + reply | caller 等 reply；跨 Binder object 可并发 | 传 fd /分页 | threadpool、嵌套调用、transaction buffer |
| Binder oneway | 无 reply 的远程调用 | 同一 Binder object 串行有序；queue 有界 | 传 fd，避免 oneway 洪泛 | backlog、冻结进程 buffer overflow |
| Unix socket | stream 或 packet | kernel socket buffer；协议自行分帧 | 分块流或 `SCM_RIGHTS` fd | 自建认证、版本、生命周期 |
| Pipe | 单向 stream | kernel pipe buffer；无消息边界 | 不适合随机访问大对象 | 双向需两条、peer 协议简单 |
| SharedMemory / mmap | 共享字节区域 | 无内建消息顺序；需同步 | 直接访问共享页 | race、权限、fd/mapping 泄漏 |
| DMA-BUF | 设备共享 buffer | fence + ownership | handle/fd 指向 buffer | format/stride/fence/cache |
| FMQ | 有界元素队列 | one writer；flavor 决定 reader/overflow | 固定布局 ring | capacity、丢数、重建 |
| eventfd | 计数/唤醒 | 计数累积 | 不承载 payload | 忘记 drain、fd 生命周期 |
| Signal | 异步进程/线程通知 | signal semantics | 不承载业务数据 | handler 安全、调度、保留信号 |
| Binder RPC / vsock | 跨 VM RPC | socket/vsock 与 RPC session | 专门共享/文件通道 | VM 调度、framing、连接安全 |

这张表没有“谁最快”。同样传 16 bytes，RPC 语义、线程唤醒与权限检查可能是主要成本；同样传 10MB，是否复用 mapping、是否复制到共享区、cache 与同步策略更加重要。

## 14. 选型决策树

```text
需要跨进程协作
├─ 是命令、状态、权限或生命周期 RPC？
│  ├─ App / Framework → AIDL + Binder
│  ├─ 新 HAL → Stable AIDL HAL + /dev/binder
│  ├─ 存量 HIDL HAL → /dev/hwbinder
│  └─ 已有流式本地协议 → Unix domain socket
│
├─ 是持续大数据或高频数据面？
│  ├─ 普通 CPU 字节区域 → SharedMemory + fd
│  ├─ CPU/GPU/display/camera buffer → DMA-BUF / AHardwareBuffer
│  ├─ HAL 固定布局元素流 → FMQ
│  ├─ 文件型共享 → mmap
│  └─ 任意长度字节流 → Unix socket
│
├─ 只需要通知？
│  ├─ poll/epoll 唤醒 → eventfd
│  ├─ 父子进程单向字节流 → pipe
│  └─ 平台级异步信号 → Signal
│
└─ host ↔ pVM？
   └─ 通过 vsock 的 Binder RPC / AIDL；大数据另行设计通道
```

当一条链既有控制又有大数据，优先设计成：

```text
Binder/AIDL：鉴权、建会话、传 fd、状态与错误
SharedMemory/DMA-BUF/FMQ/socket：持续数据
eventfd/fence/event flag：完成通知与同步
```

## 15. Perfetto 与现场证据

### 15.1 抓 Binder 与调度

```bash
adb shell perfetto \
  -o /data/misc/perfetto-traces/ipc.perfetto-trace \
  -t 10s -b 64mb \
  sched freq binder_driver

adb pull \
  /data/misc/perfetto-traces/ipc.perfetto-trace
```

Binder slice 的 wall time 要拆开：

1. client 编组前后的 App slice。
2. `binder transaction` 到 server thread 开始之间的排队。
3. server thread running、runnable、sleeping 或 blocked。
4. server 内部的嵌套 Binder、锁与 I/O。
5. reply 与 client 重新被调度。

Perfetto SQL 标准库已经提供 Binder 结构化表，不必只用 `slice.name LIKE '%binder%'` 猜：

```sql
INCLUDE PERFETTO MODULE android.binder;

SELECT
  client_process,
  client_thread,
  interface,
  method_name,
  COUNT(*) AS calls,
  AVG(client_dur) / 1e6 AS avg_ms,
  MAX(client_dur) / 1e6 AS max_ms
FROM android_binder_txns
GROUP BY
  client_process, client_thread, interface, method_name
ORDER BY max_ms DESC
LIMIT 50;
```

不同 Perfetto 版本的标准库字段会演进；查询失败时先看当前 Trace Processor 的 `android.binder` module 文档。

### 15.2 socket/pipe 不能只搜 slice 名

系统 trace 不保证每次 `sendmsg()` / `recvmsg()` 都自动产生有语义的 userspace slice。更可靠的方法：

- App/服务在协议请求与完成处加 trace。
- 必要时采集 syscall ftrace 或 CPU callstack。
- 同时看线程状态、socket buffer/backpressure 日志与 payload 计数。
- InputChannel 结合 input category、InputDispatcher 和目标 App 线程分析。

没有名为 `sendto` 的 slice，不等于没有 socket I/O。

### 15.3 如何验证共享内存路径

共享内存“少了一次 IPC copy”不能只根据 trace 中没有 memcpy 推断。组合证据包括：

- Parcel 里传的是 fd/handle，不是大 payload。
- `/proc/<pid>/fd` 与 `/proc/<pid>/maps` 显示两端映射同一对象。
- source path 走 `writeFileDescriptor()` / `mmap()`。
- CPU profile 没有持续出现 payload-sized 编组 copy。
- 协议计数、fence/event flag 与数据生命周期吻合。

即使共享同一物理页，producer 或 consumer 仍可能在业务层复制。

## 16. 常见反模式

### 16.1 高频 getter 风暴

```java
// 差：一帧里 N 次同步 Binder
for (long id : ids) {
    states.add(remote.getState(id));
}
```

```java
// 好：一次快照，或订阅增量
List<State> states = remote.getStates(ids);
```

批量接口还要设置合理上限。把 N 次小 transaction 合成一个超大 Bundle，只是把调用风暴换成 `TransactionTooLargeException`。

### 16.2 oneway 当成无限队列

生产速度长期高于服务端消费速度时，oneway 只会把压力移到 async transaction queue。应设计：

- 合并/去重。
- 有界序列号与 latest-state 语义。
- 丢弃策略。
- 服务端健康与 backlog 指标。
- cached/frozen 进程边界。

### 16.3 共享内存没有协议

只有一块 mmap，没有 header、版本、长度、状态和内存序，接收方就可能读到只写了一半的数据。最小协议至少需要：

```text
magic / version
capacity / payload_length
sequence
state: EMPTY → WRITING → READY → READING
校验与错误恢复
```

跨 CPU 或设备时再加入正确的原子操作、fence 和 cache/coherency 规则。

### 16.4 传 fd 后忘记缩权

可写 fd 是 capability。能够只读时，应先完成写入、unmap writer、降低 future mapping protection，再传给不可信对端。接收方也要校验 size 和格式，不能因为 fd 来自 Binder 就假设内容安全。

## 17. 版本边界

| 版本 | 变化 | 分析含义 |
| --- | --- | --- |
| Android 8（API 26） | Treble、HIDL/hwbinder、FMQ；Binder scatter-gather | HAL 控制面与高吞吐数据面开始更明确分离 |
| Android 8.1（API 27） | Java `SharedMemory` 公共 API | App 可显式传递共享区域 fd |
| Android 10 | Stable AIDL 稳定性机制 | 面向 system/vendor 边界的 AIDL 接口需要显式考虑稳定性 |
| Android 11 | AIDL HAL；`vndbinder` 路线 deprecated | 新 HAL 可使用 Stable AIDL `/dev/binder` |
| Android 12 | AIDL NDK backend 支持 FMQ；GKI 2.0 推进 ION → DMA-BUF heaps | SharedMemory 与 DMA-BUF allocator 仍是两条线 |
| Android 13 | HIDL deprecated；AVF/Microdroid 扩展通过 Binder RPC over vsock 场景 | 存量 HIDL 仍可能存在；跨 VM 不走 kernel Binder |
| Android 17（API 37） | 默认 ashmem-compatible memfd 路径增加 vendor API 202604 与 targetSdk 37 等门禁 | 当前 AOSP 源码统一锚定 `android-17.0.0_r1` |

## 18. 常见误区

### “Intent、AIDL、Binder 是三种并列 IPC”

不成立。Intent/AIDL 是上层协议或接口；跨进程时通常由 Binder 承载。

### “oneway 不会阻塞，也不会失败”

不成立。它不等待业务 reply，但 driver 提交、queue 容量、冻结进程和服务端消费仍构成约束。

### “Binder 单次可以安全传接近 1MB”

不成立。约 1MB 是进程所有 in-flight transaction 共享预算，还要减 page 和元数据开销。

### “共享内存就是 0 copy”

不成立。映射后可避免重复 IPC copy，producer 写入、consumer 转换、page fault 和 cache 同步仍有成本。

### “FMQ 是双向队列”

不成立。单个 FMQ 只有一个 writer；双向协议通常建立两条 queue。

### “Signal 延迟为零”

不成立。它是内核管理的异步通知，交付与 handler 执行仍受 signal mask 和调度影响。

### “Android 17 HAL 都走 AIDL”

不成立。新接口优先 AIDL，但设备可保留受支持的 HIDL HAL。

### “RpcBinder over vsock 仍受 Binder 1MB buffer 限制”

不成立。它复用 Binder object/RPC 模型，但 transport 是 socket/vsock，不使用 kernel Binder receive mapping。

## 19. 检查清单

1. 先确认 client/server PID，排除同进程直调。
2. 区分上层抽象、控制 transport、数据面和通知机制。
3. Binder 调用记录 interface、method、payload 和 sync/oneway。
4. 大数据确认 Parcel 内联还是 fd/handle/descriptor。
5. 记录 fd 所有权、protection、mapping 与 close 时序。
6. 检查 backpressure、queue capacity、overflow 与丢弃策略。
7. Binder 慢调用拆成 client、queue、server、nested call 和 reply。
8. Socket/Pipe 记录 framing、buffer、blocking mode 和 peer credentials。
9. SharedMemory/FMQ/DMA-BUF 检查同步、fence、内存序与版本。
10. HAL 先分 HIDL/hwbinder 与 Stable AIDL/binder。
11. pVM 路径单独按 Binder RPC + vsock 分析。
12. 所有延迟数字都附设备、build、payload、统计口径和分位数。

## 参考资料

- [AOSP：Binder overview](https://source.android.com/docs/core/architecture/ipc/binder-overview)
- [AOSP：AIDL overview](https://source.android.com/docs/core/architecture/aidl)
- [Android API：IBinder](https://developer.android.com/reference/android/os/IBinder)
- [Android API：TransactionTooLargeException](https://developer.android.com/reference/android/os/TransactionTooLargeException)
- [Android API：SharedMemory](https://developer.android.com/reference/android/os/SharedMemory)
- [Android API：CursorWindow](https://developer.android.com/reference/android/database/CursorWindow)
- [AOSP：Fast Message Queue](https://source.android.com/docs/core/architecture/hidl/fmq)
- [AOSP：FMQ with AIDL](https://source.android.com/docs/core/architecture/aidl/fmq)
- [AOSP：HAL overview](https://source.android.com/docs/core/architecture/hal)
- [AOSP：AIDL for HALs](https://source.android.com/docs/core/architecture/aidl/aidl-hals)
- [AOSP：Microdroid / Binder RPC](https://source.android.com/docs/core/virtualization/microdroid)
- [PerfettoSQL standard library](https://perfetto.dev/docs/analysis/stdlib-docs)
- [AOSP：ProcessState.cpp（android-17.0.0_r1）](https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/libs/binder/ProcessState.cpp)
- [AOSP：Parcel.cpp（android-17.0.0_r1）](https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/libs/binder/Parcel.cpp)
- [AOSP：InputTransport.cpp（android-17.0.0_r1）](https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/libs/input/InputTransport.cpp)
- [AOSP：Looper.cpp（android-17.0.0_r1）](https://android.googlesource.com/platform/system/core/+/refs/tags/android-17.0.0_r1/libutils/Looper.cpp)
- [AOSP：ashmem-dev.cpp（android-17.0.0_r1）](https://android.googlesource.com/platform/system/core/+/refs/tags/android-17.0.0_r1/libcutils/ashmem-dev.cpp)
- [AOSP：CursorWindow.cpp（android-17.0.0_r1）](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/libs/androidfw/CursorWindow.cpp)
- [AOSP：reserved_signals.h（android-17.0.0_r1）](https://android.googlesource.com/platform/bionic/+/refs/tags/android-17.0.0_r1/libc/platform/bionic/reserved_signals.h)
