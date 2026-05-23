---
title: "IPC 全景：Android 进程间通信机制对比与性能选型"
chapter: "1.17"
section: "1.17"
status: finalized
applicable_versions: "Android 8.0 (API 26) - Android 17 (API 37)"
last_verified: "2026-04-11"
last_verified_against: "AOSP main（ProcessState.cpp、Looper.cpp、InputTransport.cpp、InputChannel.java）, source.android.com"
confidence: medium
sources:
  - type: official
    path: "https://developer.android.com/guide/components/aidl"
  - type: official
    path: "https://source.android.com/docs/core/architecture/hals"
  - type: official
    path: "https://developer.android.com/reference/android/os/SharedMemory"
  - type: aosp
    path: "frameworks/native/libs/binder/ProcessState.cpp"
  - type: aosp
    path: "system/core/libutils/Looper.cpp"
  - type: aosp
    path: "frameworks/native/libs/input/InputTransport.cpp"
  - type: aosp
    path: "frameworks/base/core/java/android/view/InputChannel.java"
  - type: aosp
    path: "frameworks/base/core/java/android/os/MemoryFile.java"
tags: [ipc, binder, socket, pipe, shared-memory, mmap, ashmem, intent, aidl, messenger, contentprovider, hwbinder, unix-domain-socket, performance]
related_chapters: ["1.4", "1.10", "1.13", "2.15", "4.1", "9.1"]
created_by: "manual-request"
created_date: "2026-04-09"
reviewed_date: "2026-05-08"
reviewed_by: "openclaw-task6"
task6_result: "pass-light-edit"
review_log: "logs/review/2026-05-08-04-review.md"
pipeline_stage: ready-to-publish
task6_state: reviewed
task9_result: "pass-tech-review"
task9_state: reviewed
task2b_result: fixed
task2b_state: fixed
last_task2b_at: "2026-04-24T09:54:00+08:00"
task9_reviewed_by: "openclaw-task9"
task9_reviewed_date: "2026-05-08"
last_task9_at: "2026-05-08T04:31:55+08:00"
task6_reviewed_date: "2026-05-08"
last_task6_at: "2026-05-08T04:05:00+08:00"
last_task6_audit: "2026-05-23"
task6_review_notes: "2026-05-08 03:09 task6 revisiting-review: pass-light-edit。复核 Task2B 修正后写作层，修复 18 处 L1/L2 文风、格式与代码说明问题；无新增回炉项，送 Task9 复审。 | 2026-05-08 04:05 task6 revisiting-review: pass-light-edit。复核 Task2B 修正后写作层，修复 frontmatter、数据口径示意与代码块语言标注；无新增回炉项，送 Task9 复审。"
task9_review_notes: "2026-05-08 04 Task9 deep-review: pass-tech-review。P0 0 / P1 0 / P2 仅建议；无 queue pending，Task6 已通过，自动晋升 finalized / ready-to-publish；详见 logs/deep-review/2026-05-08-04-deep-review.md。 | 2026-05-08 03:44 Task2B rework: P0 BINDER_VM_SIZE 改为 sysconf(_SC_PAGE_SIZE)*2；P0 Parcel::writeBlob BLOB_INPLACE_LIMIT 改为 16KB，ashmem 路径重写 | 2026-05-08 03 Task9 deep-review: needs-rework。P0 2 / P1 0 / P2 1。源码锚点与版本/数据口径需 Task2B 回炉；详见 logs/deep-review/2026-05-08-03-deep-review.md。"
---

# IPC 全景：Android 进程间通信机制对比与性能选型

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

1. **Android IPC 机制全景图** — 以树状/表格列出 Android 上所有 IPC 机制，按层级分类（内核级 / 框架级 / 应用级）
2. **各机制原理与性能特征**
   - Binder（含 oneway / 同步 / hwbinder）→ 详细分析见 §1.4
   - Unix Domain Socket（LocalSocket）
   - 匿名/命名 Pipe
   - 共享内存、DMA-BUF 与 FMQ 的边界
   - mmap（文件映射跨进程）
   - Signal
3. **框架层 IPC 抽象**
   - Intent（底层走 Binder）
   - ContentProvider（底层走 Binder + 匿名共享内存）
   - AIDL 生成代码的 Binder 调用路径
   - Messenger（单线程 Binder 封装）
   - BroadcastReceiver（Binder + AMS 中转）
4. **性能对比表** — 延迟 / 吞吐 / 拷贝次数 / 数据量上限 / 适用场景
5. **选型决策树** — 根据数据量、频率、方向性、安全需求选择 IPC 机制
6. **Perfetto 中识别 IPC 开销** — Binder 延迟追踪、socket 通信追踪、共享内存零拷贝验证

### 扩展点（建议覆盖）

- 通用共享内存、ION/dmabuf-heaps 与 FMQ 的边界
- HwBinder 与 Treble 架构下的 IPC 隔离
- NDK SharedMemory API（API 27+）
- 跨 PID 传递文件描述符（Binder `BINDER_TYPE_FD`）
- 与 Linux 桌面（D-Bus、Wayland）的 IPC 对比视角

<!-- outline-end -->

## 1. 为什么需要 IPC 全景

Android 的安全模型基于进程隔离：每个应用运行在独立进程中，系统服务（system_server）、SurfaceFlinger、HAL 服务等也各有独立进程。进程间任何协作都依赖 IPC（Inter-Process Communication）。

本书 §1.4 已深入分析了 Binder 的工作原理与性能影响。Android 还同时使用多种 IPC 机制：

- SurfaceFlinger 与 App 之间通过 **共享内存 + Binder** 传递图形缓冲区
- logd 通过 **Unix Domain Socket** 接收日志
- 父子进程的标准流与少量控制流常用 **Pipe** 传递
- InputDispatcher 通过 **InputChannel / socketpair** 向 App 发送输入事件，channel 的 fd 再通过 Binder 交给目标窗口
- HAL 服务的控制调用在 Treble 之后分成 **HIDL / hwbinder** 与 **Stable AIDL / binder** 两条路径，高吞吐数据再配合 FMQ 或共享内存

理解全貌有助于：
1. **分析性能 Trace 时识别 IPC 瓶颈**（不只看 Binder 延迟）
2. **系统级优化时选择最合适的 IPC 机制**
3. **理解 Android 版本演进中 IPC 层的变化**（通用共享内存、图形 allocator 与 HAL 接口各自怎么演进）

## 2. Android IPC 机制分类

### 2.1 按层级分类

```text
┌─────────────────────────────────────────────────┐
│                  应用层 IPC                       │
│  Intent · ContentProvider · BroadcastReceiver    │
│  AIDL · Messenger · ResultReceiver              │
│  （底层均通过 Binder 实现）                        │
├─────────────────────────────────────────────────┤
│                 框架层 IPC                        │
│  Binder（同步/oneway）· HIDL/HwBinder            │
│  Stable AIDL HAL · LocalSocket · SharedMemory   │
│  mmap                                            │
├─────────────────────────────────────────────────┤
│                 内核层 IPC                        │
│  binder 驱动 · /dev/socket/* · pipe()            │
│  ashmem/dmabuf · signal · eventfd               │
└─────────────────────────────────────────────────┘
```

### 2.2 完整机制清单

| 机制 | 传输方向 | 数据量 | 拷贝次数 | 安全模型 | 主要使用场景 |
|------|---------|--------|---------|---------|-------------|
| **Binder（同步）** | 双向 | ≤进程级 buffer 约 1MB | 1（mmap） | UID/GID + SELinux | 系统服务调用 |
| **Binder（oneway）** | 单向异步 | ≤进程级 buffer 约 1MB | 1 | UID/GID + SELinux | 异步通知、回调 |
| **HIDL / HwBinder** | 双向 | ≤进程级 buffer 约 1MB | 1 | SELinux + HAL 域 | Treble 早期/存量 HAL 控制调用 |
| **Stable AIDL HAL / Binder** | 双向 | ≤进程级 buffer 约 1MB | 1 | SELinux + 稳定接口约束 | 新 HAL 控制调用 |
| **Unix Domain Socket** | 双向 | 无硬限制 | 2（send+recv） | 文件系统权限 | logd、input、本地服务 |
| **Pipe** | 单向 | 受内核缓冲限制 | 2 | fd 继承/传递 | 子进程标准流、少量控制流 |
| **共享内存 / DMA-BUF** | 双向 | 大块数据 | 0（零拷贝） | fd 传递 + SELinux | SharedMemory、CursorWindow、GraphicBuffer |
| **mmap 文件映射** | 双向 | 文件大小 | 0 | 文件权限 | 配置共享、数据库 WAL |
| **Signal** | 单向 | 无数据 | 0 | 内核级 | ANR SIGQUIT、进程杀死 |
| **eventfd / epoll** | 单向事件 | 8 字节 | 0 | fd 继承 | 线程/进程事件通知 |
| **Intent** | 双向（底层 Binder） | ≤进程级 buffer 约 1MB | 1 | UID + 权限 | 组件间通信 |
| **ContentProvider** | 双向（Binder + shm） | 大块 | 0~1 | UID + 权限 | 数据共享 |
| **AIDL** | 双向（Binder） | ≤进程级 buffer 约 1MB | 1 | UID/GID + SELinux | 自定义服务接口 |
| **Messenger** | 单向队列（Binder） | ≤进程级 buffer 约 1MB | 1 | UID/GID | 轻量消息传递 |
| **FMQ（Fast Message Queue）** | 双向 | 可配置 | 0（零拷贝） | HAL 进程 | 高吞吐 HAL 数据流 |
| **AF_VSOCK / RpcBinder** | 双向 | 与 Binder 同量级 | 1 | SELinux + VM 域 | AVF/Microdroid VM 间通信 |

## 3. 核心机制详解

### 3.1 Binder — 系统骨干

> 详见 §1.4 Binder IPC 机制与性能影响，此处只补充性能要点。

**Binder 在 Android IPC 中的地位：**

Android 框架内的大多数系统服务调用走 Binder 路径。四大组件的生命周期管理、权限检查、资源获取也依赖 Binder。

**性能关键指标：**

- 单次同步调用延迟：**~0.5-2ms**（同设备进程间，空服务 RPC 参考；调用 framework 服务时由于服务端处理逻辑，实际延迟通常更高）
- oneway 调用延迟：**~0.2-0.8ms**
- 默认 worker 上限约 15 线程（`DEFAULT_MAX_BINDER_THREADS = 15`）；很多人口语里说的“16 线程”通常把发起调用的 caller 线程也算进去了
- 单次事务数据上限：受进程级 Binder transaction buffer 约束（约 1MB 减 2 个 page，由同进程并发事务共享）。AOSP `ProcessState.cpp` 中 `BINDER_VM_SIZE` 为 `((1*1024*1024) - sysconf(_SC_PAGE_SIZE) * 2)`；4KB 设备约 1MB - 8KB，16KB 设备约 1MB - 32KB。`TransactionTooLargeException` 的实际触发条件受并发事务放大影响——多个线程同时发起 Binder 调用时，buffer 空间是共享的
- 优化：一次 mmap 拷贝（vs 传统 IPC 的两次）

[已验证: AOSP main, frameworks/native/libs/binder/ProcessState.cpp — `DEFAULT_MAX_BINDER_THREADS = 15`]

**性能陷阱：**

1. **高频小调用累积**：频繁 Binder 调用（如每帧查询 WindowInfo）导致的线程池争用
2. **oneway 不保证顺序**：同一目标的 oneway 调用按序发送，但跨目标无序
3. **大对象 Parcel 序列化开销**：`writeToParcel` / `createFromParcel` 的 CPU 时间常被忽略

### 3.2 Unix Domain Socket

**原理：** 基于 `AF_UNIX` 的本地套接字，通过 Linux 网络栈的本地环回路径传输。

**Android 中的关键使用：**

| 使用者 | 路径 | 用途 |
|--------|------|------|
| logd | `/dev/socket/logd/*` | 日志写入与读取 |
| InputDispatcher | `InputChannel / socketpair(AF_UNIX, SOCK_SEQPACKET)` | 触摸/按键事件分发 |
| vold | `/dev/socket/vold` | 存储管理命令 |
| installd | `/dev/socket/installd` | 应用安装命令 |
| netd | `/dev/socket/netd` | 网络管理命令 |
| WebView | Chromium IPC | 渲染进程通信 |

InputDispatcher 这一路径容易写错。输入事件不是通过 `/data/system/input_manager/*` 这类命名 socket 路径发出去的。WMS / InputDispatcher 会创建一对 `InputChannel`，底层是 `socketpair(AF_UNIX, SOCK_SEQPACKET, ...)`；客户端那一端作为 `Parcelable` 经 Binder 送到 App，之后事件和 `FINISHED` 回执都在这对未命名 Unix domain socket 上流动。

[已验证: AOSP main, frameworks/native/libs/input/InputTransport.cpp — `InputChannel::openInputChannelPair()` 使用 `socketpair(AF_UNIX, SOCK_SEQPACKET, ...)`；frameworks/base/core/java/android/view/InputChannel.java — `InputChannel` 可通过 `Parcelable` 随 Binder 传递]

**性能特征：**

- 延迟：**~0.1-0.5ms**（本地 socket 比 Binder 略快或相当，取决于数据量）
- 两次数据拷贝（send buffer → 内核 → recv buffer）
- 无 1MB 事务限制，适合流式数据
- 支持 `sendmsg` + `SCM_RIGHTS` 传递文件描述符
- **SELinux 策略控制访问**

**与其他 IPC 配合：** InputDispatcher 的事件面走的是 `InputChannel` 的 socketpair，channel 本身通过 Binder parcel 把 fd 交给 App，所以它更像“Binder 控制面 + socket 数据面”的组合式 IPC。

### 3.3 Pipe

**原理：** 内核缓冲区实现的单向字节流，`pipe()` 系统调用创建一对 fd（read fd + write fd）。

**Android 中的关键使用：**

- **Process 重定向**：`Runtime.exec()` / `ProcessBuilder` 的 stdin/stdout/stderr 通过 pipe 连接父子进程
- **父子进程控制流**：shell 或守护进程内部的少量字节流通知仍常用 pipe
- **历史背景**：Looper 早期实现用过 pipe 唤醒 poll，但本书覆盖的 Android 8-17 不应再这样描述

现代 Android 需要把 pipe 和 `eventfd` 分开看。`system/core/libutils/Looper.cpp` 在 `Looper` 构造时创建的是 `mWakeEventFd = eventfd(0, EFD_NONBLOCK | EFD_CLOEXEC)`，再把这个 fd 注册进 epoll。也就是说，MessageQueue/Looper 的唤醒路径在 Android 8-17 范围内应理解为 `eventfd + epoll`，pipe 只能作为更早实现的历史背景。

[已验证: AOSP main, system/core/libutils/Looper.cpp — `mWakeEventFd.reset(eventfd(...))`]

**性能特征：**

- 单向通信，内核缓冲有限，适合少量字节流而不是大吞吐数据
- 两次拷贝
- 极低延迟（**~0.05-0.1ms**，内核态直接拷贝）
- 只能传递字节流，无结构化数据支持
- 通常用于父子进程或同一服务内部的简单控制流

### 3.4 共享内存、DMA-BUF 与 FMQ

这一组机制最容易被写成一条单线演进，但 Android 里有三条要分开看的路线。

| 路线 | 常见 API / 类型 | 底层对象 | 典型场景 | 版本节点 | 可观测点 |
|------|----------------|----------|----------|----------|----------|
| **应用通用共享内存** | `MemoryFile`、`SharedMemory`、`ASharedMemory`、`CursorWindow` | ashmem-compatible fd + `mmap`；Android 12 之后这条线逐步以 memfd 为底层承载，并保留 ashmem 兼容语义 | 应用间大块数据、Provider 窗口、匿名共享区域 | Android 8 系列开始提供 `SharedMemory` / `ASharedMemory`；Android 12 是 ashmem → memfd 的分水岭；`MemoryFile` 仍是兼容层 | Binder 事务中的 `BINDER_TYPE_FD`、`/proc/<pid>/maps` 里的 ashmem / memfd 区域 |
| **图形与 DMA buffer** | `GraphicBuffer`、`AHardwareBuffer`、gralloc buffer handle | ION → dmabuf / dmabuf-heaps | BufferQueue、SurfaceFlinger、相机/编解码器缓冲区 | Android 10 之后更常见把新分配放到 dmabuf-heaps；Android 13 之后图形路径更统一 | gralloc handle 中的 buffer fd、`/dev/dma_heap/*`、BufferQueue / SurfaceFlinger trace |
| **HAL 零拷贝队列** | FMQ（`MQDescriptorSync` / `MQDescriptorUnsync`） | 共享内存环形队列 + event flag | 音频、相机、传感器、NNAPI 等高吞吐 HAL 数据流 | Treble 之后广泛使用，接口协商走 HIDL 或 AIDL | HAL 调用里的 descriptor 传递、libfmq 映射、队列读写 trace |

[已验证: AOSP main `MemoryFile.java` 把 MemoryFile 写成 SharedMemory wrapper；`android_os_MemoryFile.cpp` 与 `CursorWindow.cpp` 仍直接使用 `cutils/ashmem.h` / `ashmem_create_region()`；Android 12 之后通用匿名共享内存的底层实现逐步转向 memfd，并保留 ashmem 兼容语义；`MessageQueueBase.h` 明确 FMQ 可用 ashmem shared memory 创建队列]

把三条路线拆开之后，边界会清楚很多：

- `SharedMemory` / `MemoryFile` / `CursorWindow` 讨论的是通用匿名共享内存。这条线的 API 语义仍可按 ashmem-compatible fd + `mmap` 理解，但版本边界要单独记住：Android 12 是底层实现从 ashmem 向 memfd 过渡的分水岭。memfd 的 `F_ADD_SEALS` 可以限制 `grow` / `shrink`，避免对端在共享期间改区域大小。
- `GraphicBuffer` / `AHardwareBuffer` / gralloc 讨论的是图形与设备共享 buffer allocator。这条线从 ION 走到 dmabuf-heaps，关注点是 allocator、buffer handle 和硬件设备共享。
- FMQ 讨论的是 HAL 场景下的环形队列抽象。它可以建立在共享内存之上，但语义是“有读写指针的队列”，和单块共享区域、图形 buffer handle 不是一类对象。

**原理：**

1. 分配共享区域或 buffer，并拿到 fd / descriptor
2. 通过 Binder（`BINDER_TYPE_FD`）或 Unix Socket（`SCM_RIGHTS`）把句柄交给对端
3. 对端 `mmap` 共享区域，或按 GraphicBuffer / FMQ 的约定映射后访问
4. 数据面走零拷贝路径，控制面仍由 Binder / HwBinder / Socket 协商

**Android 中的关键使用：**

- **BufferQueue / GraphicBuffer**（§2.13）：Binder 协商 buffer 生命周期，图形数据走 dmabuf / GraphicBuffer
- **ContentProvider / CursorWindow**：查询窗口在需要扩容时会 inflate 到匿名共享内存。旧路径常见 ashmem，新设备上这类 fd 更多由 memfd 承载，再通过 Binder 返回给客户端
- **SharedMemory API / MemoryFile**：应用或系统服务共享匿名内存
- **FMQ**：HAL 侧高频、小单元、连续读写的数据流

**性能特征：**

- 数据面建立完成后读写没有额外用户态拷贝
- 适合大块数据或高频队列，不适合拿来替代控制面 RPC
- 首次映射的成本主要来自 `mmap` 与页表建立，后续访问接近普通内存读写
- 同步要靠 fence、event flag、原子变量或协议约定，零拷贝不等于自动有序
- 生命周期由 fd、buffer handle 或 descriptor 持有关系决定

**陷阱：**

1. 把 `SharedMemory`、dmabuf-heaps、FMQ 写成一条“新 API 替代旧 API”的单线演进
2. 忘记 `close()` fd 或释放 buffer handle，导致共享区域长期存活
3. 只有共享区域，没有同步协议，最终读到半写入数据
4. 用 Binder 传大 payload，而不是传 fd / descriptor



### 3.4.1 Parcel::writeBlob 零拷贝与 ashmem/memfd 演进

Android 的 `Parcel::writeBlob()` 对大于 `BLOB_INPLACE_LIMIT`（`16 * 1024 = 16KB`）的大数据使用共享内存 fd 实现零拷贝：

```cpp
// frameworks/native/libs/binder/Parcel.cpp (AOSP main)
// 简化调用链
Parcel::writeBlob(size, data)
  ├─ if (size <= BLOB_INPLACE_LIMIT)   // 16KB
  │    writeInplace(data)              // 直接写入 Parcel 内部 buffer
  └─ else
       ashmem_create_region("Parcel Blob", size)  // 申请匿名共享内存
       mmap(MAP_SHARED)                            // 发送者映射
       memcpy(data)                                 // 写入数据
       if (immutable)
         ashmem_set_prot_region(fd, PROT_READ)     // 设为只读
       writeFileDescriptor(fd)                      // fd 写入 Parcel
       // Binder 事务中只传 fd，不传数据本身
```

`ashmem_create_region` 在新设备上由 `libcutils/ashmem-dev.cpp` 的 ashmem-compatible 层实现，底层可能走 `memfd_create`；`F_ADD_SEALS` / `F_SEAL_FUTURE_WRITE` 是 memfd 路径的实现细节，对 Parcel 调用者不可见。`art/libartbase/base/memfd.cc` 提供 memfd 的封装和 tmpfile fallback。

[源码验证: AOSP main frameworks/native/libs/binder/Parcel.cpp（writeBlob 阈值判断与 ashmem 路径）；system/core/libcutils/ashmem-dev.cpp（ashmem-compatible memfd 实现）；art/libartbase/base/memfd.cc（memfd 封装）]

### 3.5 mmap 文件映射

**原理：** `mmap()` 将文件映射到进程地址空间，多个进程映射同一文件时共享物理页。

**Android 中的关键使用：**

- **ResourceTable**：资源表通过 mmap 共享
- **ELF 文件加载**：ART 通过 mmap 加载 DEX/OAT 文件
- **SQLite WAL**：Write-Ahead Log 的跨进程共享
- **Properties**：`/dev/__properties__` 区域通过 mmap 共享（init 进程创建）
- **Binder mmap**：Binder 驱动自身使用 mmap 实现单次拷贝

**性能特征：**

- 零拷贝读（写视 `MAP_SHARED` vs `MAP_PRIVATE` 而定）
- 按需分页（page fault 触发实际 I/O）
- 适合读多写少的数据共享

### 3.6 Signal

**原理：** 内核级异步通知机制，不携带数据（仅信号编号）。

**Android 中的关键使用：**

| 信号 | 典型发送者 | 典型接收者 | 用途 |
|------|-----------|-----------|------|
| `SIGQUIT (3)` | AMS / `Process.sendSignal()` / `kill -3` | App 或 system 进程 | 导出 Java backtrace / ANR trace |
| `BIONIC_SIGNAL_DEBUGGER (__SIGRTMIN + 3)` | `libdebuggerd_client` / debuggerd | 目标进程线程 | 请求 native backtrace 或 tombstone dump |
| `SIGKILL (9)` | AMS / LMKD / init | App 进程 | 强制结束进程 |
| `SIGABRT (6)` | bionic / malloc / 进程自身 | 自身 | abort、heap corruption、触发 native crash 流程 |

[已验证: AOSP main `bionic/reserved_signals.h` 把 `BIONIC_SIGNAL_DEBUGGER` 定义为 `__SIGRTMIN + 3`；`debuggerd_client.cpp` 中 Java backtrace 走 `SIGQUIT`，native dump 走 `BIONIC_SIGNAL_DEBUGGER`]

当前默认路径已经由 `SIGQUIT` 和 `BIONIC_SIGNAL_DEBUGGER` 覆盖。文档如果另写自定义信号方案，必须单独给出处。

**性能特征：**

- 无延迟概念——内核直接中断目标进程
- 不携带数据——只传递信号类型
- 无法阻塞 `SIGKILL` / `SIGSTOP`
- 适合紧急通知，不适合数据传输

### 3.7 Treble 之后的 HAL IPC：HIDL / hwbinder 与 Stable AIDL / binder

**背景：** Treble 改变的是 Framework 和 vendor 之间的边界：它把两侧通信固化成稳定接口。Android 8 先用 HIDL + `/dev/hwbinder` 建立这条边界；Android 10 再引入 Stable AIDL，让 HAL 也可以走标准 `/dev/binder`，同时保留接口稳定性要求。

**两条主路径不要混为一谈：**

| 路径 | Binder 域 | 接口定义 | 典型阶段 | 说明 |
|------|-----------|----------|----------|------|
| **HIDL HAL** | `/dev/hwbinder` | HIDL | Android 8 之后的存量 HAL | Treble 初期建立的独立 HAL binder domain |
| **Stable AIDL HAL** | `/dev/binder` | Stable AIDL | Android 10 引入，Android 11+ 新 HAL 广泛采用 | 与 framework binder 共用驱动，靠稳定接口和 VINTF 约束兼容性 |

**AIDL HAL 不等于 HwBinder**。Trace 里出现 HAL 调用时，要先分清它落在哪个 binder domain：命中 `/dev/hwbinder` 的通常是 HIDL，命中标准 binder 的则更可能是 Stable AIDL HAL。

**性能影响：**

- 控制面上的 HAL 调用，仍是 Binder 家族的 RPC，开销更多取决于服务端干了什么，而不是“hwbinder 天生更慢”
- 音频、相机、传感器这类高吞吐路径，常见做法是 Binder / HwBinder 只负责控制面，数据面走 FMQ、共享内存或 dmabuf

[已验证: AOSP docs《Work with binder IPC》《AIDL for HALs》— Android 8 将 vendor IPC 隔离到 `/dev/hwbinder`；Android 10 Stable AIDL 允许 HAL 使用 `/dev/binder`]

### 3.7.1 AVF 场景下的 IPC：AF_VSOCK 与 RpcBinder

Android Virtualization Framework (AVF) 引入了虚拟机（pVM/Microdroid）场景。在这种场景下，host 和 VM 之间的通信不再走传统的 `/dev/binder`，而是通过 `AF_VSOCK`——一种基于 virtio-socket 的虚拟化 IPC 机制。AIDL 在 VM 场景下使用 `RpcBinder`（也称为 `libbinder_ndk_rpc`），底层可以绑定到 `AF_VSOCK` 或 Unix Domain Socket。

三类边界要分清：

| 场景 | IPC 路径 | 说明 |
|------|---------|------|
| **host ↔ pVM** | AIDL via RpcBinder → AF_VSOCK | host 的 `virtmgr` 管理 VM 生命周期，AIDL 接口经 RpcBinder 序列化后走 vsock |
| **pVM 内部** | Unix Domain Socket / 共享内存 | VM 内部组件间的 IPC 走标准 UDS 或共享内存 |
| **VM 间** | 无直接 IPC | pVM 之间不直接通信，需经 host 中转 |

RpcBinder 的性能特征与标准 Binder 类似（序列化/反序列化 + 一次数据拷贝），但底层传输从 binder 驱动换成了 vsock。在 Perfetto 中，VM 间 IPC 的开销更多体现在 vsock 的数据传输延迟上，而非 binder driver 的调度。

## 4. 性能对比表

### 4.1 定量对比

| 机制 | 典型延迟 | 吞吐量 | 数据量上限 | 拷贝次数 | CPU 开销 |
|------|---------|--------|-----------|---------|---------|
| Binder 同步 | 0.5-2ms | 中等 | 进程级约 1MB（共享） | 1 | 中（序列化） |
| Binder oneway | 0.2-0.8ms | 中等 | 进程级约 1MB（共享） | 1 | 中 |
| HIDL / HwBinder | 与 Binder 同量级 | 中等 | 进程级约 1MB（共享） | 1 | 中 |
| Stable AIDL HAL / Binder | 与 Binder 同量级 | 中等 | 进程级约 1MB（共享） | 1 | 中 |
| Unix Socket | 0.1-0.5ms | 高 | 无限制 | 2 | 低 |
| Pipe | 0.05-0.1ms | 中 | 受内核缓冲限制 | 2 | 极低 |
| 共享内存 | 首次 0.5-2ms，后续 ns | 极高 | 受物理内存限制 | 0 | 极低（需同步） |
| mmap | 首次 page fault，后续 ns | 极高 | 文件大小 | 0 | 极低 |
| Signal | 即时 | N/A | 0 字节 | 0 | 无 |
| FMQ | ~μs 级 | 极高 | 配置决定 | 0 | 极低 |

> **注：** 延迟数据为方向性参考，受以下条件影响：
> - Binder 延迟：空服务 RPC（无业务逻辑），同设备进程间，ARMv9 旗舰 SoC，主频 2-4GHz
> - Unix Socket / Pipe：本地回环，无 SELinux policy miss
> - 共享内存：首次映射开销，后续为 ns 级内存读写
> - FMQ：零拷贝环形队列读写，不含控制面 Binder 开销
>
> 不同测试口径给出的数字差异很大（binder driver microbenchmark vs framework service end-to-end vs 应用层 AIDL 调用），横向对比时要注意口径一致。具体数据应通过 Perfetto 在目标设备上实测确认。

### 4.2 Android 常见的“组合式 IPC”

把 Binder、Socket、共享内存、FMQ 写成互斥的“单选题”，在 Android 里很容易把问题讲歪。真实系统更常见的做法是：**Binder / HwBinder 负责控制面，fd 指向的共享内存、dmabuf、FMQ 或 socket 负责数据面。** 前者做权限检查、生命周期管理、错误返回和小对象元数据，后者搬运大数据。

fd 传递就是这两层之间的桥。Binder 路径里对应的是 `BINDER_TYPE_FD`，Java 层常见包装是 `ParcelFileDescriptor`；socket 路径里对应的是 `sendmsg(..., SCM_RIGHTS)`。大块数据之所以“看起来是 Binder 调用，实际没把数据塞进 Parcel”，原因就在这里。

| 场景 | 控制面 | 数据面 | fd 如何过去 |
|------|--------|--------|-------------|
| **BufferQueue / GraphicBuffer** | `IGraphicBufferProducer` Binder 调用（`dequeueBuffer()` / `queueBuffer()` 等） | dmabuf / GraphicBuffer | buffer handle 中的 fd 经 Binder 传给对端 |
| **CursorWindow** | `ContentProvider` query / moveToPosition 等 Binder 调用 | `CursorWindow` 共享内存 | window fd 经 Binder 返回给客户端 |
| **SharedMemory / FMQ / HAL** | Service 或 HAL 接口先协商共享区域 | SharedMemory / FMQ | Binder 用 `BINDER_TYPE_FD`，socket 用 `SCM_RIGHTS` |

这也是为什么 BufferQueue、CursorWindow、很多 HAL 数据流都不能简单归类成“Binder”或“共享内存”二选一。更准确的说法是：**控制面走 Binder 家族，数据面走 fd 指向的零拷贝通道。**

### 4.3 使用频率的方向性印象（AOSP 系统进程）

下面这张图只表达常见程度，不作为实测占比。不同设备、系统版本和采样窗口下，IPC 分布会明显变化。

```text
Binder        ████████████████████████████████  系统服务调用最常见
Unix Socket   ██████                           logd / input / vold 等本地守护进程
共享内存       ████                             图形缓冲区、ContentProvider、HAL 数据面
Pipe          ██                               子进程标准流与少量控制流
Signal        █                                ANR、kill、native dump 等紧急通知
```

## 5. IPC 选型决策树

在 Android 里，IPC 选型通常是先定控制面，再定数据面。

```text
需要 IPC？
├── 先判断这是控制面还是数据面？
│   ├── 控制面（命令、状态、权限、生命周期）
│   │   ├── App / Framework 服务接口 → Binder（AIDL）
│   │   ├── HAL 接口 → Stable AIDL HAL / binder 或 HIDL / hwbinder
│   │   └── 本地守护进程、流式命令 → Unix Domain Socket
│   └── 数据面（大数据 / 高吞吐 / 零拷贝）
│       ├── 单块共享数据 → SharedMemory / dmabuf + fd 传递
│       ├── 高频环形队列 → FMQ
│       └── 文件型共享 / 持久化 → mmap
├── 只需要唤醒或通知？
│   ├── 线程 / Looper 唤醒 → eventfd
│   ├── 父子进程简单字节流 → Pipe
│   └── 紧急无载荷通知 → Signal
└── fd 怎么交给对端？
    ├── Binder 路径 → BINDER_TYPE_FD / ParcelFileDescriptor
    └── Socket 路径 → SCM_RIGHTS
```

真实系统里的“复杂 IPC”多数是组合题：Binder 先把 channel、buffer handle 或共享内存 fd 交过去，后面的高吞吐数据再走零拷贝通道。把控制面和数据面拆开后，性能分析时不会把大块数据开销都算到 Binder 头上。

## 6. Perfetto 中的 IPC 分析

### 6.1 Binder 追踪

这条查询用来按 slice 名称聚合 Binder 调用耗时，先找出平均耗时最高的调用类型。

```sql
-- Binder 调用延迟分布
SELECT
  name,
  AVG(dur) / 1e6 as avg_ms,
  MAX(dur) / 1e6 as max_ms,
  COUNT(*) as calls
FROM slice
WHERE name GLOB '*binder*'
GROUP BY name
ORDER BY avg_ms DESC
LIMIT 20;
```

如果结果集中某类 binder slice 的 `avg_ms` 或 `max_ms` 异常升高，再回到线程轨道确认调用端和服务端是否排队。

### 6.2 共享内存追踪

这条查询从 slice 名称里筛出 dmabuf 或 buffer allocator 相关耗时；不同设备的 slice 命名可能不同，结果只作为入口。

```sql
-- dmabuf/图形缓冲区分配
SELECT
  name,
  AVG(dur) / 1e6 as avg_ms,
  COUNT(*) as count
FROM slice
WHERE name GLOB '*dma*'
   OR name GLOB '*buffer*alloc*'
GROUP BY name
ORDER BY avg_ms DESC;
```

命中后再结合 SurfaceFlinger / BufferQueue 章节确认是哪类 buffer 分配，不要只靠名称判断根因。

### 6.3 Socket I/O 追踪

这条查询用来定位 socket 读写相关 slice，并按线程聚合平均耗时，适合排查 logd、input 或本地守护进程通信。

```sql
-- Unix socket 读写延迟
SELECT
  thread.name as thread,
  slice.name,
  AVG(slice.dur) / 1e6 as avg_ms
FROM slice
JOIN thread_track ON slice.track_id = thread_track.id
JOIN thread USING (utid)
WHERE slice.name GLOB '*sock*'
   OR slice.name GLOB '*recvfrom*'
   OR slice.name GLOB '*sendto*'
GROUP BY thread.name, slice.name
ORDER BY avg_ms DESC;
```

如果某个线程的 socket 读写耗时异常，再结合线程状态和调用栈判断是数据量过大、对端处理慢，还是调度延迟。

## 7. 版本演进中的 IPC 变化

IPC 的版本演进重点在于控制面和数据面的边界变化。这张表只保留会影响分析判断的转折点：

| 版本 | IPC 变化 | 分析时要注意什么 |
|------|---------|----------------|
| Android 8 (Treble) | 引入 Treble，HIDL HAL 进入 `/dev/hwbinder` domain | HAL 控制调用开始和 framework binder domain 分离 |
| Android 10 | 引入 Stable AIDL；图形/多媒体 allocator 继续从 ION 向 dmabuf-heaps 迁移 | 不能把 `SharedMemory` / `MemoryFile` / `CursorWindow` 写成 dmabuf-heaps 的直接替代物 |
| Android 11 | 新 HAL 可以直接使用 AIDL，迁移开始扩大 | Trace 中要同时接受 HIDL 和 AIDL HAL 并存 |
| Android 12 | 通用匿名共享内存开始把 memfd 作为主要底层承载，ashmem 兼容语义继续保留 | 分析 `SharedMemory` / `CursorWindow` 时要分清 API 名称和底层内核对象，不要把 memfd 写成 dmabuf 的一部分 |
| Android 13 | GraphicBuffer 等图形内存路径进一步统一到 dmabuf | 图形类大数据更典型地表现为“Binder 控制 + dmabuf 数据面”；应用通用共享内存仍单独看 |
| Android 14+ | 持续鼓励 HIDL → AIDL 迁移，而不是一刀切“全面完成” | 同一设备上可能长期共存两套 HAL IPC |
| Android 16-17 | AIDL HAL 与 Rust HAL 覆盖面继续扩大 | 实现语言会变，但 control plane / data plane 的组合模式不变 |
| Android 13+ (AVF) | AF_VSOCK + RpcBinder 用于 host ↔ VM 通信 | VM 场景下 IPC 走 vsock 而非 binder 驱动；分析 VM trace 时要区分 vsock 和传统 binder 延迟 |

[已验证: AOSP docs《Work with binder IPC》《AIDL for HALs》；Android 图形 allocator 的 ION → dmabuf-heaps 迁移与通用共享内存 API 是两条独立演进线]

## 8. 常见性能反模式

### 8.1 Binder 调用风暴

```java
// ❌ 每帧多次 Binder 调用
void onDrawFrame() {
    for (WindowInfo win : windows) {
        int visibility = service.getWindowVisibility(win.id); // Binder call
    }
}
```

```java
// ✅ 批量查询 + 本地缓存
void onDrawFrame() {
    // 一次 Binder 调用获取所有信息
    Bundle visibilities = service.getAllWindowVisibilities();
}
```

### 8.2 大数据走 Binder

```java
// ❌ 大图片通过 Binder 传递（可能超 1MB 限制）
mRemote.transact(FLAG, data, reply, 0);
```

```java
// ✅ 共享内存传递大数据
SharedMemory shm = SharedMemory.create("big_data", size);
// 通过 Binder 传递 SharedMemory 对象（只传 fd，不传数据）
mRemote.sendSharedMemory(shm);
```

### 8.3 忽视跨进程同步

```cpp
// ❌ 共享内存写入无 fence
memcpy(shared_ptr, data, size);
// 另一端可能读到半写入的数据
```

```cpp
// ✅ 使用 fence/原子操作同步
android_atomic_acquire_store(READY_FLAG, &header->flag);
// 对端用 android_atomic_acquire_load 检查
```

## 9. 小结

Android 的 IPC 生态以 Binder 为核心，但绝非只有 Binder。理解全貌有助于：

1. **Trace 分析时识别 IPC 类型和瓶颈**：Binder 延迟 ≠ 全部 IPC 延迟
2. **系统优化时选择最合适的机制**：大数据用共享内存，紧急通知用 Signal，流式数据用 Socket
3. **理解版本演进方向**：通用共享内存这条线要记住 Android 12 的 memfd 分水岭，图形 allocator 才是 ION → dmabuf-heaps，HAL 接口再看 HIDL / hwbinder → Stable AIDL / binder
4. **避免常见反模式**：Binder 调用风暴、大数据走 Binder、缺乏同步的共享内存

---

**交叉参考：**
- §1.4 Binder IPC 机制与性能影响（Binder 深入分析）
- §1.10 ContentProvider 性能与优化（ContentProvider 的共享内存实现）
- §1.13 MessageQueue 机制（eventfd + epoll 在 Looper 中的应用）
- §2.13 BufferQueue（图形缓冲区共享内存）
- §2.15 DMA-BUF、Gralloc 与跨进程图形内存共享
- §2.16 Sync Fence 框架（共享内存同步机制）
- §9.1 ANR 设计思想（Binder 超时与 ANR 的关系）
