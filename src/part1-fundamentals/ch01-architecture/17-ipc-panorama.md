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
created_date: '2026-04-09'
reviewed_date: '2026-07-25'
reviewed_by: Codex
pipeline_stage: ready-to-publish
task6_state: reviewed
task6_result: pass-light-edit
task9_state: reviewed
task9_result: pass-tech-review
task2b_state: fixed
task2b_result: fixed
deepseek_cn_review_state: done
created_by: "manual-request"
review_log: "logs/review/2026-05-08-04-review.md"
last_task2b_at: "2026-04-24T09:54:00+08:00"
task9_reviewed_by: "openclaw-task9"
task9_reviewed_date: "2026-06-19"
last_task9_at: "2026-06-19T05:28:49+08:00"
last_task9_review_log: "logs/deep-review/2026-06-19-05-deep-review.md"
task6_reviewed_date: "2026-06-19"
last_task6_at: "2026-06-19T05:08:51+08:00"
last_task6_audit: "2026-06-17"
task6_review_notes: "2026-06-19 Task6 revisiting-review: pass-light-edit。Task9 auto-fix（Parcel::writeBlob mAllowFds 边界、ashmem/memfd 版本门禁、RpcBinder/vsock 数据边界、Stable AIDL HAL 时间线）回流后写作层复审通过；L1/L2 无需小修，章节文风干净；无 L3/L4 回炉项，送 Task9 终审。"
task9_review_notes: "2026-05-08 04 Task9 deep-review: pass-tech-review。P0 0 / P1 0 / P2 仅建议；无 queue pending，Task6 已通过，自动晋升 finalized / ready-to-publish；详见 logs/deep-review/2026-05-08-04-deep-review.md。 | 2026-05-08 03:44 Task2B rework: P0 BINDER_VM_SIZE 改为 sysconf(_SC_PAGE_SIZE)*2；P0 Parcel::writeBlob BLOB_INPLACE_LIMIT 改为 16KB，ashmem 路径重写 | 2026-05-08 03 Task9 deep-review: needs-rework。P0 2 / P1 0 / P2 1。源码锚点与版本/数据口径需 Task2B 回炉；详见 logs/deep-review/2026-05-08-03-deep-review.md。 | 2026-05-26 20:20 Task9 闲时抽检：pass-tech-review。P0/P1 0；P2 2（RpcBinder/vsock 数据边界、Stable AIDL HAL 时间线表述需修正）；详见 logs/deep-review/2026-05-26-20-audit.md。 | 2026-06-18 Task9 idle-audit: auto-fixed。P1 1：修正 ashmem-compatible memfd 版本边界，android-17.0.0_r1 中默认 memfd 路径要求 memfd SELinux capability、vendor API 202604 与 app target SDK min 37；P2 3：修正 RpcBinder/vsock 数据边界、Stable AIDL HAL 时间线与 Parcel::writeBlob 零拷贝口径。 | 2026-06-19 Task9 deep-review AUTO-FIX: P0 1 / P1 0 / P2 0；复核 AOSP android-17.0.0_r1 Parcel.cpp，修正 writeBlob >16KB 走 ashmem fd 的条件，补充 mAllowFds 为 true 的边界；回到 Task6 复审。详见 logs/deep-review/2026-06-19-01-deep-review.md。 | 2026-06-19 Task9 deep-review: pass-tech-review。P0 0 / P1 0 / P2 0；复核 android-17.0.0_r1 Binder buffer、Parcel::writeBlob、ashmem/memfd 门禁、InputChannel/socketpair 与 HIDL/AIDL HAL 边界，Task6 已通过且 queue 无 pending，自动晋升 finalized。"
last_task9_audit: "2026-07-09"
last_task9_audit_log: "logs/deep-review/2026-07-09-17-audit.md"
last_task9_autofix_at: "2026-06-19"
updated_by: "openclaw-task9"
updated_date: "2026-06-19"
p0: 0
p1: 0
p2: 0
last_deepseek_cn_review_at: 2026-06-22
---

# 1.17 IPC 全景：Android 进程间通信机制对比与性能选型

Android IPC 无法简化为“Binder、Intent、共享内存三选一”。Intent 和 AIDL 描述上层语义；Binder、Unix 域套接字和 vsock 负责传输；共享内存、DMA-BUF 与 FMQ 又常被用作数据面。一条真实链路经常同时使用两到三层机制。

本章以 Android 17 / API 37、AOSP `android-17.0.0_r1` 为当前锚点，介绍如何从源码、文件描述符、线程和跟踪记录还原真实链路，不为各种机制设定脱离条件的固定延迟。

## 1. 先按职责分类，不按 API 名堆清单

```text
上层语义 / 框架抽象
├─ AIDL、Messenger、ResultReceiver
├─ Intent、BroadcastReceiver
└─ ContentProvider / Cursor

控制面传输
├─ Binder：/dev/binder
├─ HIDL / HwBinder：/dev/hwbinder（存量 HAL）
├─ Unix 域套接字：命名套接字或 socketpair
├─ 管道：单向字节流
└─ 经套接字 / AF_VSOCK 的 Binder RPC：宿主机 ↔ pVM

数据面 / 共享对象
├─ SharedMemory / mmap
├─ CursorWindow
├─ DMA-BUF / AHardwareBuffer / GraphicBuffer
└─ FMQ：共享内存环形队列

通知与唤醒
├─ eventfd
└─ 信号
```

这四层会组合：

- AIDL 定义接口，普通跨进程调用由 Binder 承载。
- Binder 先传递 `SharedMemory` 文件描述符，之后双方直接读写映射。
- InputManager 通过 Binder 把 `InputChannel` 文件描述符交给应用，后续输入事件走 Unix `SOCK_SEQPACKET`。
- HAL 用 AIDL/HIDL 建立 FMQ，持续数据走共享内存队列。
- Microdroid 复用 Binder/AIDL 对象模型，但传输改为套接字/vsock。

同一套 API 也可能不跨进程。AIDL 的客户端与服务在同一进程、使用同一后端时可以直接调用，不产生 Parcel 编组和 Binder 驱动事务。分析前先确认 PID。

## 2. 选型先回答六个问题

### 2.1 需要 RPC 还是流

- “调用方法并拿到结果”是 RPC，Binder/AIDL 最自然。
- “持续传任意长度字节流”更接近套接字或管道。
- “持续传定长元素”可考虑 FMQ。
- “共享一块大对象”可考虑 SharedMemory 或 DMA-BUF。

### 2.2 负载是控制信息还是大数据

控制信息适合 Parcel：方法号、少量参数、令牌、文件描述符、状态码。图像、音频帧、模型权重或大型结果集不应反复内联到 Parcel；常见做法是只传句柄、文件描述符或描述符对象。

### 2.3 谁拥有内存，谁负责回收

很多 IPC 缺陷源于所有权不清，传输本身并没有失败：

- Binder 对象何时调用 `linkToDeath()`、何时释放引用。
- 文件描述符是借用、复制后拥有，还是随 `ParcelFileDescriptor` 关闭。
- mmap 何时取消映射，SharedMemory 何时关闭。
- DMA-BUF 围栏未完成前谁不能复用缓冲区。
- FMQ 写入方或读取方死亡后如何重建。

### 2.4 需要什么顺序和背压

- 同步 Binder 自带请求/回复和调用线程阻塞。
- 单向调用没有业务回复，但仍受驱动队列和服务端处理速度约束。
- 套接字/管道由内核缓冲区提供背压，写满后阻塞或返回 `EAGAIN`。
- FMQ 容量固定，需要明确溢出/欠载语义。
- 共享内存本身没有消息边界、顺序或唤醒。

### 2.5 安全边界在哪里

Binder 提供调用方 UID/PID、对象引用与 SELinux Binder 策略；套接字依赖套接字命名空间、文件权限、对端凭据和 SELinux；文件描述符传递则把内核对象的访问能力交给对端。共享内存若未降低保护权限，对端可能获得超出预期的写权限。

### 2.6 如何证明性能结论

IPC 延迟至少包含：

```text
客户端编组
+ 驱动 / 内核传输
+ 服务端排队与调度
+ 服务端业务
+ 回复编组与返回
```

固定写“Binder 0.5ms、套接字 0.1ms、管道 0.05ms”没有工程价值。负载、CPU、构建、线程池、SELinux、调度和服务端工作稍有变化，数字就会改变。需要比较时，应在同一设备上用相同负载、同步语义和统计口径做基准。

## 3. Binder：Android 控制面的主干

### 3.1 一次同步调用发生了什么

以跨进程 AIDL 为例：

```text
客户端方法
  └─ 代理将方法号与参数写入 Parcel
       └─ ioctl 到 Binder 驱动
            └─ 驱动把事务复制到服务端接收映射
                 └─ 服务端 Binder 线程
                      └─ 存根解包并调用实现
                           └─ 回复 Parcel 原路返回
```

Binder 不是端到端零拷贝。Android 8 的分散/聚集优化减少了额外编组复制，但驱动仍要把事务内容复制到目标进程地址空间；复杂 Parcelable 仍有编码、对象表、字符串和容器处理成本。

### 3.2 同步与单向调用

同步事务要等服务端返回。调用方看到的墙上时间可能来自：

- 服务端 Binder 线程尚未空闲。
- 服务端拿锁、做 I/O 或调用下一个 Binder 服务。
- 调用方等待回复时被调度出去。
- 回复本身过大或编组昂贵。

`oneway` 只表示远程调用不等待业务返回，不表示：

- 不经过 Binder 驱动。
- 永不排队或永不失败。
- 服务端可以无限快消费。
- 任意单向调用全局有序。

多个单向调用只有在发往同一个 `IBinder` 对象时，才保证按发送顺序一次分发一个；不同 Binder 对象，或单向与同步调用混用时，没有这项顺序保证。若调用是同进程直调，`oneway` 也不会把它自动变成异步。

### 3.3 1MB 是共享预算，不是安全负载上限

Java `TransactionTooLargeException` 文档把 Binder 事务缓冲区描述为当前 1MB，并强调它由进程所有进行中的事务共享。Android 17 原生 `ProcessState.cpp` 的接收映射更具体：

```cpp
#define BINDER_VM_SIZE \
        ((1 * 1024 * 1024) - sysconf(_SC_PAGE_SIZE) * 2)
```

因此：

- 4KB page 设备：约 1016KiB。
- 16KB page 设备：约 992KiB。

这仍不是“单个请求可放心塞到 992KiB”的承诺。同一进程的并发请求、回复、对象元数据和对端接收缓冲区都会占空间。异常发生时，客户端甚至无法可靠区分请求尚未发出还是回复过大。

工程规则很简单：事务保持小；大数据使用文件描述符、分页或流传递。

### 3.4 默认 15 不是“进程总共只有 15 个 Binder 线程”

Android 17 `ProcessState.cpp`：

```cpp
#define DEFAULT_MAX_BINDER_THREADS 15
```

这个值配置的是驱动可以按需启动的线程池线程默认上限。`startThreadPool()` 启动的线程、主动调用 `joinThreadPool()` 的线程，以及进程自行调整的配置会影响总数。把它口语化成“每个进程固定 16 个 Binder 线程”会误导容量分析。

判断线程池是否饥饿，应看：

- 服务端 Binder 线程是否全在执行或阻塞。
- 客户端事务是否长时间等不到服务端片段。
- 服务端是否在 Binder 线程上做阻塞 I/O、跨服务调用或持有大锁。
- `binder thread pool ... starved` 类日志是否出现。

### 3.5 Binder 对象、文件描述符与普通字节不是一回事

Parcel 除普通数据外，还维护对象表。它可以传：

- Binder 对象/句柄。
- 文件描述符（`BINDER_TYPE_FD`）。
- 原生句柄中的一组文件描述符与整数。

驱动会为接收方安装/复制相应引用或文件描述符。传递文件描述符后，后续大数据不必继续进入 Parcel，但双方仍要定义：

- 文件描述符的访问权限。
- 由谁关闭。
- 是否允许写。
- 对端死亡后的清理。
- 数据完成条件。

## 4. AIDL、Messenger、Intent 和 Provider 在哪一层

### 4.1 AIDL 是接口与编组语言

AIDL 编译器为接口生成代理/存根和类型编解码代码。跨进程时走 Binder；同进程使用同一后端时可以直接调用。

```text
客户端接口调用
  ├─ 本地对象 → 直接调用
  └─ 远程代理
       └─ Parcel + Binder 事务
            └─ 服务端存根 + 实现
```

AIDL 解决类型契约、版本与后端，不改变底层事务缓冲区约束。把一个 5MB `byte[]` 换成 AIDL 参数，并不会自动变成共享内存。

### 4.2 Messenger 是 Handler 语义叠在 Binder 上

Messenger 用 Binder 传 `Message`，接收端最终把消息投递到指定 Handler / Looper。它适合不希望自己管理并发 RPC、而是希望按某个 Looper 顺序处理的场景。

“Messenger 是单线程 Binder”也不够准确：

- 传输仍是 Binder。
- Binder 收到消息后再投递 Handler。
- 一个 Messenger 入口的消息由它绑定的 Handler / Looper 串行分发；Handler 内部是否再把工作拆到线程池并行执行，由应用决定。
- Message 负载仍受 Parcel 与事务缓冲区限制。

### 4.3 Intent 与广播是系统调度协议

`Intent` 是描述操作、组件和附加数据的 Parcelable，不是独立内核 IPC。跨进程组件启动或广播通常经过 `system_server` 中的 ActivityManager 等服务，再由 Binder 调用目标进程。

它附带的是更高层语义：

- 组件解析与导出/权限检查。
- 生命周期和进程启动。
- 后台启动、广播队列与缓存进程策略。
- 有序广播的结果传播。

因此 Intent 性能不能只用“一次 Binder 耗时”解释。冷启动目标进程、组件调度和生命周期回调的成本通常远大于传输本身。

### 4.4 ContentProvider 不等于“Binder + 共享内存”一条固定路径

内容提供者的查询、插入、更新、删除是框架层 RPC，跨进程控制调用由 Binder 承载。查询返回的数据窗口常使用 `CursorWindow`，但小窗口和大窗口路径不同。

Android 17 `CursorWindow.cpp`：

- 初始内联容量为 16KiB。
- 数据能放下时，跨进程可把压缩后的窗口内联写入 Parcel。
- 需要更大空间时才扩展到 ashmem 兼容区域。
- 大窗口通过文件描述符传递，对端使用只读 mmap。

“所有 ContentProvider 结果都零拷贝”不成立。列值填充、CursorWindow 构建、内联复制或共享区域初始化仍有 CPU 和内存成本。

### 4.5 ResultReceiver 是回调抽象

跨进程 `ResultReceiver` 内部同样依靠 Binder 回调。它适合一次或少量结果通知，不适合无界数据流。结果 `Bundle` 仍要保持小，并处理接收方生命周期。

## 5. Unix 域套接字

Unix 域套接字提供本机字节流或有消息边界的分组语义，常见类型包括：

- `SOCK_STREAM`：连续字节流，无消息边界。
- `SOCK_SEQPACKET`：保留消息边界与顺序。
- 命名套接字：由 init 创建在 `/dev/socket/*` 等命名空间。
- 匿名 `socketpair()`：创建一对已连接的文件描述符。

它没有 Binder 的“事务共享 1MB 接收映射”口径，但仍受套接字发送/接收缓冲区、单个分组、内存和协议分帧约束。大流可以分块持续发送，不等于单次 `send()` 没有上限。

### 5.1 InputChannel：Binder 交文件描述符，套接字传事件

Android 17 `InputChannel::openInputChannelPair()`：

```cpp
socketpair(AF_UNIX, SOCK_SEQPACKET, 0, sockets);
```

InputDispatcher 持有服务端；客户端作为 Parcelable 经 Binder 交给窗口所在进程。之后：

- 输入事件走这对匿名 Unix 套接字。
- 应用处理完成的结束信号也走同一通道。
- Binder 主要负责通道生命周期和控制，不搬运每个 MotionEvent 的数据。

这条链是“Binder 控制面 + 套接字数据面”的典型例子。

### 5.2 `SCM_RIGHTS`：套接字也能传文件描述符

Unix 套接字可用 `sendmsg()` / `recvmsg()` 和 `SCM_RIGHTS` 把文件描述符交给对端。它传递的是对同一内核对象的新引用，不会把文件内容复制进辅助数据。

接收方必须：

- 校验文件描述符数量和类型。
- 设置/确认 `CLOEXEC`。
- 定义关闭时机。
- 不信任对端提供的文件大小、offset、格式或权限。

### 5.3 什么时候比 Binder 更合适

Unix 套接字更适合：

- 已有流式分帧协议。
- 需要长连接和显式背压。
- 非 Android Binder 环境也要复用协议。
- 需要分组边界或双向字节流。

它不自动提供 Binder 对象身份、调用方 UID API、死亡通知和服务管理。把系统服务从 Binder 改成套接字，往往要自己补回身份、授权、版本、生命周期和错误协议。

## 6. 管道、eventfd 与信号

### 6.1 管道：单向字节流

`pipe()` 创建读文件描述符和写文件描述符：

- 单向。
- 没有消息边界。
- 由有限的内核缓冲区提供背压。
- 常通过进程派生继承或显式传递文件描述符建立连接。

Android/Java 常见场景是 `ProcessBuilder` / `Runtime.exec()` 的标准输入、标准输出、标准错误。需要双向通信时要两条管道，或直接使用 socketpair。

### 6.2 Looper 当前使用 eventfd

本书覆盖 Android 8–17。`android-17.0.0_r1` 的 `Looper.cpp` 在构造时：

```cpp
mWakeEventFd.reset(
        eventfd(0, EFD_NONBLOCK | EFD_CLOEXEC));
epoll_ctl(mEpollFd.get(), EPOLL_CTL_ADD,
          mWakeEventFd.get(), &wakeEvent);
```

`wake()` 向 eventfd 写入一个 64 位计数，`epoll_wait()` 被唤醒后再读取。管道是更早实现的历史背景，不应拿来解释当前 MessageQueue 唤醒路径。

eventfd 主要传递计数/通知，不承载业务负载。跨进程使用时，双方仍需继承或传递文件描述符。

### 6.3 信号：异步通知，不是数据通道

信号的交付仍受目标线程调度、信号掩码和处理函数行为影响，不能写成“内核直接中断，延迟为零”。标准信号通常只表达编号；带 `siginfo_t` 的机制能附带少量元数据，但依然不适合业务数据流。

Android 常见用途：

| 信号 | 用途 |
| --- | --- |
| `SIGQUIT` | 请求 ART/进程生成 Java 栈信息，ANR 流程会使用 |
| `BIONIC_SIGNAL_DEBUGGER` | debuggerd 原生转储/墓碑内部通道 |
| `SIGABRT` | 主动中止，进入原生崩溃流程 |
| `SIGKILL` | 不可捕获、不可忽略的强制终止 |

Android 17 bionic 把 `BIONIC_SIGNAL_DEBUGGER` 定义为 `__SIGRTMIN + 3`。这是平台保留信号，应用不应复用。

信号处理函数还受异步信号安全规则约束。不要在处理函数里分配内存、获取普通互斥锁、记录复杂日志或调用非安全 API。

## 7. SharedMemory 与 mmap

### 7.1 共享页不等于端到端零拷贝

共享内存建立后，两个进程可以访问同一组物理页，持续读写无需每条消息再经过内核传输复制。但仍可能发生：

- 生产者把数据复制进共享区域。
- 缺页、页表建立和缓存未命中。
- CPU 与设备之间的缓存维护。
- 消费者再复制到自己的数据结构。

更准确的表述是“数据面可避免重复 IPC 复制”，不能把整条业务链称为零拷贝。

### 7.2 Java `SharedMemory`

`android.os.SharedMemory` 从 API 27 提供，可通过 Parcelable 传递文件描述符：

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

`setProtect()` 只能移除权限，不能重新增加。它只约束之后创建的映射；已有可写映射保持原权限。因此“写入 → 取消映射 → 降为只读 → 传给对端”是更清晰的最小权限顺序。

接收方映射后也要取消映射，并关闭自己收到的文件描述符包装对象。发送方关闭自身描述符，不会立即让接收方复制的文件描述符失效。

### 7.3 `MemoryFile` 是兼容包装

Android 17 `MemoryFile.java` 已明确写成 `SharedMemory` 包装。新代码通常优先使用 SharedMemory；MemoryFile 的可清除兼容行为不应被当作新的通用共享内存设计基础。

### 7.4 Android 17 的 ashmem 兼容文件描述符可能由 memfd 承载

`ashmem_create_region()` 是兼容 API 名，不保证底层一定是旧的 `/dev/ashmem`。Android 17 `ashmem-dev.cpp` 的默认判定是：

1. 内核/SELinux 策略支持 `memfd_class` 能力。
2. `ro.vendor.api_level >= 202604`。
3. 当前应用的目标 SDK >= 37。

满足后走 `memfd_create()`；否则回到 ashmem 设备。`sys.use_memfd=true` 仍可用于强制覆盖，源码注明未来会移除。

因此调试时要看 `/proc/<pid>/fd/*`、内存映射和设备属性，不能只看 Java API 名推断底层对象。

## 8. `Parcel::writeBlob()`：16KiB 分界的真实含义

Android 17 C++ `Parcel.cpp` 定义：

```cpp
static const size_t BLOB_INPLACE_LIMIT = 16 * 1024;

if (!mAllowFds || len <= BLOB_INPLACE_LIMIT) {
    // 内联数据块
} else {
    // ashmem_create_region + mmap + Parcel 中的文件描述符
}
```

边界是：

- `len <= 16KiB`：内联。
- `len > 16KiB` 且 Parcel 允许文件描述符：创建 ashmem 兼容区域，映射后通过 Parcel 传文件描述符。
- `len > 16KiB` 但不允许文件描述符：仍走内联。

`writeBlob()` 返回可写区域给调用者，数据仍要被写进内联缓冲区或共享映射。文件描述符分支避免把整块数据再次塞进 Binder 事务缓冲区，但生产者仍有写入成本。

这个行为也不能外推成“所有大 AIDL `byte[]` 自动走共享内存”。只有实际使用数据块/文件描述符支撑的 Parcelable 路径才有这项分流。普通字节数组仍会被内联编组。

## 9. DMA-BUF、GraphicBuffer 与共享内存不是同一条线

DMA-BUF 解决的是 CPU、GPU、显示、相机、编解码器等设备之间共享缓冲区：

- 分配器返回 DMA-BUF 文件描述符/原生句柄。
- gralloc 描述格式、步幅、用途和平面布局。
- Binder 传递句柄与生命周期控制。
- 围栏表达生产者/消费者完成时序。

Android 12 的 GKI 2.0 路线用 DMA-BUF 堆替代 ION 分配器；每个堆通常表现为 `/dev/dma_heap/<name>`。这项迁移不等于 SharedMemory 从 ashmem 迁到 DMA-BUF。

| 对象 | 主要用途 | 同步 |
| --- | --- | --- |
| SharedMemory / memfd / ashmem 兼容区域 | CPU 进程间共享普通字节 | 原子、锁、协议、eventfd |
| DMA-BUF / AHardwareBuffer / GraphicBuffer | CPU 与硬件设备共享结构化缓冲区 | 同步围栏、缓存/一致性规则 |
| mmap 文件 | 文件页映射与持久化共享 | 文件锁、数据库协议、原子/锁 |

图像数据走 DMA-BUF，也不等于应用可以忽略格式、步幅、用途和围栏。

## 10. FMQ：共享内存上的有界单向队列

FMQ 先通过 HIDL 或 AIDL RPC 传递 `MQDescriptor`，双方映射环形缓冲区、读写位置和可选事件标志。建立完成后，非阻塞读写不需要每条消息进入 Binder 驱动。

单个 FMQ 的基本约束：

- 只有一个写入方。
- 同步队列：一个读取方，不允许溢出。
- 非同步队列：可有多个读取方，写入方可覆盖旧数据；落后的读取方会丢数据。
- 两种队列都不允许欠载。
- 双向协议通常需要两条方向相反的队列。

因此把 FMQ 表格写成“天然双向”是错误的。它适合固定布局、频繁、小单元的数据流，不适合：

- 可变长复杂对象。
- 含指针、Binder 接口或任意嵌套缓冲区的负载。
- 需要每条消息独立权限检查的协议。
- 无界队列。

HIDL FMQ 从 Android 8 提供；AIDL NDK 后端从 Android 12 可使用 FMQ。Java 后端可以转交描述符，但没有 Java FMQ 库直接读写队列。

## 11. HAL IPC：HIDL/hwbinder 与稳定 AIDL/binder

Android 8 的 Treble 用 HIDL 和独立的 `/dev/hwbinder` 域固化框架层/厂商边界。Android 10 引入稳定 AIDL 机制，Android 11 开始允许 HAL 使用 AIDL。稳定 AIDL HAL：

- 使用 `/dev/binder`。
- 厂商原生代码使用 NDK 或 Rust 后端等稳定运行时。
- 通过 VINTF、冻结的接口版本和 VTS 管理兼容性。

HIDL 从 Android 13 起弃用，但既有 HIDL HAL 仍受支持。分析 Android 17 设备不能凭系统版本断言“所有 HAL 都已 AIDL 化”。

| HAL 接口 | 常见驱动域 | 当前定位 |
| --- | --- | --- |
| HIDL binderized HAL | `/dev/hwbinder` | 存量兼容，不用于新接口 |
| 稳定 AIDL HAL | `/dev/binder` | 新实现优先 |
| `/dev/vndbinder` + vndservicemanager | 厂商进程间旧 AIDL | Android 11 起弃用 |

控制调用之外，音频、相机、传感器和图形仍常把持续数据放在 FMQ、SharedMemory 或 DMA-BUF 中。AIDL/HIDL 决定接口语言和控制传输，不等于高吞吐负载必须内联。

## 12. AVF：通过 vsock 的 Binder RPC

Microdroid/pVM 不能直接使用宿主机的 Binder 驱动。Binder RPC 保留 AIDL/Binder 对象模型，把协议改为套接字传输；pVM 场景通常使用 AF_VSOCK。

```text
宿主机 RpcSession
  └─ Binder RPC 分帧
       └─ AF_VSOCK / virtio 传输
            └─ pVM RpcServer 根 Binder 对象
```

它不继承内核 Binder 的 `BINDER_VM_SIZE` 接收映射，也不能套用“Binder 驱动一次复制”的结论。开销要拆成：

- Parcel / Binder RPC 分帧。
- 套接字/vsock 缓冲区与 virtio。
- 虚拟机调度和服务端工作。

AVF 还限制 pVM 之间直接通信；宿主机的 VirtualizationService 控制连接建立。大文件交换可使用 AuthFS 等专门通道，不能依赖超大的 Binder RPC 事务。

## 13. 定性对比

| 机制 | 消息/数据语义 | 背压与顺序 | 大数据策略 | 主要风险 |
| --- | --- | --- | --- | --- |
| Binder 同步调用 | 方法调用 + 回复 | 调用方等待回复；跨 Binder 对象可并发 | 传文件描述符/分页 | 线程池、嵌套调用、事务缓冲区 |
| Binder 单向调用 | 无回复的远程调用 | 同一 Binder 对象串行有序；队列有界 | 传文件描述符，避免单向调用洪泛 | 积压、冻结进程缓冲区溢出 |
| Unix 套接字 | 字节流或分组 | 内核套接字缓冲区；协议自行分帧 | 分块流或 `SCM_RIGHTS` 文件描述符 | 自建认证、版本、生命周期 |
| 管道 | 单向字节流 | 内核管道缓冲区；无消息边界 | 不适合随机访问大对象 | 双向需两条、对端协议简单 |
| SharedMemory / mmap | 共享字节区域 | 无内建消息顺序；需同步 | 直接访问共享页 | 竞态、权限、文件描述符/映射泄漏 |
| DMA-BUF | 设备共享缓冲区 | 围栏 + 所有权 | 句柄/文件描述符指向缓冲区 | 格式/步幅/围栏/缓存 |
| FMQ | 有界元素队列 | 单写入方；模式决定读取方/溢出 | 固定布局环形缓冲区 | 容量、丢数、重建 |
| eventfd | 计数/唤醒 | 计数累积 | 不承载业务负载 | 忘记排空、文件描述符生命周期 |
| 信号 | 异步进程/线程通知 | 信号语义 | 不承载业务数据 | 处理函数安全、调度、保留信号 |
| Binder RPC / vsock | 跨虚拟机 RPC | 套接字/vsock 与 RPC 会话 | 专门共享/文件通道 | 虚拟机调度、分帧、连接安全 |

这张表没有“谁最快”。同样传 16 字节，RPC 语义、线程唤醒与权限检查可能是主要成本；同样传 10MB，是否复用映射、是否复制到共享区、缓存与同步策略更加重要。

## 14. 选型决策树

```text
需要跨进程协作
├─ 是命令、状态、权限或生命周期 RPC？
│  ├─ 应用 / 框架层 → AIDL + Binder
│  ├─ 新 HAL → Stable AIDL HAL + /dev/binder
│  ├─ 存量 HIDL HAL → /dev/hwbinder
│  └─ 已有流式本地协议 → Unix 域套接字
│
├─ 是持续大数据或高频数据面？
│  ├─ 普通 CPU 字节区域 → SharedMemory + 文件描述符
│  ├─ CPU/GPU/显示/相机缓冲区 → DMA-BUF / AHardwareBuffer
│  ├─ HAL 固定布局元素流 → FMQ
│  ├─ 文件型共享 → mmap
│  └─ 任意长度字节流 → Unix 套接字
│
├─ 只需要通知？
│  ├─ poll/epoll 唤醒 → eventfd
│  ├─ 父子进程单向字节流 → 管道
│  └─ 平台级异步信号 → 信号
│
└─ 宿主机 ↔ pVM？
   └─ 通过 vsock 的 Binder RPC / AIDL；大数据另行设计通道
```

当一条链既有控制又有大数据，优先设计成：

```text
Binder/AIDL：鉴权、建会话、传文件描述符、状态与错误
SharedMemory/DMA-BUF/FMQ/套接字：持续数据
eventfd/围栏/事件标志：完成通知与同步
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

Binder 片段的墙上时间要拆开：

1. 客户端编组前后的应用片段。
2. `binder transaction` 到服务端线程开始之间的排队。
3. 服务端线程处于运行、可运行、休眠或阻塞状态。
4. 服务端内部的嵌套 Binder、锁与 I/O。
5. 回复与客户端重新被调度。

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

不同 Perfetto 版本的标准库字段会演进；查询失败时先看当前 Trace Processor 的 `android.binder` 模块文档。

### 15.2 套接字/管道不能只搜片段名

系统跟踪不保证每次 `sendmsg()` / `recvmsg()` 都自动产生有语义的用户空间片段。更可靠的方法：

- 应用/服务在协议请求与完成处加入跟踪。
- 必要时采集系统调用 ftrace 或 CPU 调用栈。
- 同时看线程状态、套接字缓冲区/背压日志与负载计数。
- InputChannel 结合输入类别、InputDispatcher 和目标应用线程分析。

没有名为 `sendto` 的片段，不等于没有套接字 I/O。

### 15.3 如何验证共享内存路径

共享内存“少了一次 IPC 复制”不能只根据跟踪中没有 memcpy 推断。组合证据包括：

- Parcel 里传的是文件描述符/句柄，不是大负载。
- `/proc/<pid>/fd` 与 `/proc/<pid>/maps` 显示两端映射同一对象。
- 源码路径走 `writeFileDescriptor()` / `mmap()`。
- CPU 配置文件中没有持续出现与负载等大的编组复制。
- 协议计数、围栏/事件标志与数据生命周期吻合。

即使共享同一物理页，生产者或消费者仍可能在业务层复制。

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

批量接口还要设置合理上限。把 N 次小事务合成一个超大 Bundle，只是把调用风暴换成 `TransactionTooLargeException`。

### 16.2 把单向调用当成无限队列

生产速度长期高于服务端消费速度时，单向调用只会把压力移到异步事务队列。应设计：

- 合并/去重。
- 有界序列号与最新状态语义。
- 丢弃策略。
- 服务端健康与积压指标。
- 缓存/冻结进程边界。

### 16.3 共享内存没有协议

只有一块 mmap，没有头部、版本、长度、状态和内存序，接收方就可能读到只写了一半的数据。最小协议至少需要：

```text
magic / version
容量 / 负载长度
sequence
状态：空 → 写入中 → 就绪 → 读取中
校验与错误恢复
```

跨 CPU 或设备时再加入正确的原子操作、围栏和缓存/一致性规则。

### 16.4 传递文件描述符后忘记缩权

可写文件描述符是一种访问能力。能够只读时，应先完成写入、取消写入方映射、降低后续映射保护，再传给不可信对端。接收方也要校验大小和格式，不能因为文件描述符来自 Binder 就假设内容安全。

## 17. 版本边界

| 版本 | 变化 | 分析含义 |
| --- | --- | --- |
| Android 8（API 26） | Treble、HIDL/hwbinder、FMQ；Binder scatter-gather | HAL 控制面与高吞吐数据面开始更明确分离 |
| Android 8.1（API 27） | Java `SharedMemory` 公共 API | 应用可显式传递共享区域文件描述符 |
| Android 10 | 稳定 AIDL 机制 | 面向系统/厂商边界的 AIDL 接口需要显式考虑稳定性 |
| Android 11 | AIDL HAL；`vndbinder` 路线弃用 | 新 HAL 可使用稳定 AIDL `/dev/binder` |
| Android 12 | AIDL NDK 后端支持 FMQ；GKI 2.0 推进 ION → DMA-BUF 堆 | SharedMemory 与 DMA-BUF 分配器仍是两条线 |
| Android 13 | HIDL 弃用；AVF/Microdroid 扩展通过 vsock 的 Binder RPC 场景 | 存量 HIDL 仍可能存在；跨虚拟机不走内核 Binder |
| Android 17（API 37） | 默认 ashmem 兼容 memfd 路径增加厂商 API 202604 与目标 SDK 37 等门禁 | 当前 AOSP 源码统一锚定 `android-17.0.0_r1` |

## 18. 常见误区

### “Intent、AIDL、Binder 是三种并列 IPC”

不成立。Intent/AIDL 是上层协议或接口；跨进程时通常由 Binder 承载。

### “单向调用不会阻塞，也不会失败”

不成立。它不等待业务回复，但驱动提交、队列容量、冻结进程和服务端消费仍构成约束。

### “Binder 单次可以安全传接近 1MB”

不成立。约 1MB 是进程所有进行中事务的共享预算，还要减去页和元数据开销。

### “共享内存就是零拷贝”

不成立。映射后可避免重复 IPC 复制，生产者写入、消费者转换、缺页和缓存同步仍有成本。

### “FMQ 是双向队列”

不成立。单个 FMQ 只有一个写入方；双向协议通常建立两条队列。

### “信号延迟为零”

不成立。它是内核管理的异步通知，交付与处理函数执行仍受信号掩码和调度影响。

### “Android 17 HAL 都走 AIDL”

不成立。新接口优先 AIDL，但设备可保留受支持的 HIDL HAL。

### “通过 vsock 的 RpcBinder 仍受 Binder 1MB 缓冲区限制”

不成立。它复用 Binder 对象/RPC 模型，但传输使用套接字/vsock，不使用内核 Binder 接收映射。

## 19. 复核清单

1. 先确认客户端/服务端 PID，排除同进程直调。
2. 区分上层抽象、控制传输、数据面和通知机制。
3. Binder 调用记录接口、方法、负载和同步/单向语义。
4. 大数据确认 Parcel 内联还是使用文件描述符/句柄/描述符对象。
5. 记录文件描述符所有权、保护、映射与关闭时序。
6. 检查背压、队列容量、溢出与丢弃策略。
7. Binder 慢调用拆成客户端、队列、服务端、嵌套调用和回复。
8. 套接字/管道记录分帧、缓冲区、阻塞模式和对端凭据。
9. SharedMemory/FMQ/DMA-BUF 检查同步、围栏、内存序与版本。
10. HAL 先分 HIDL/hwbinder 与稳定 AIDL/binder。
11. pVM 路径单独按 Binder RPC + vsock 分析。
12. 所有延迟数字都附设备、构建、负载、统计口径和分位数。

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
