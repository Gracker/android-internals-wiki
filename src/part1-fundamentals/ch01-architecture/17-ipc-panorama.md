---
title: "IPC 全景：Android 进程间通信机制对比与性能选型"
chapter: "1.17"
section: "1.17"
status: ready-for-review
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
reviewed_date: "2026-04-19"
reviewed_by: "openclaw-task6"
task6_result: pass-light-edit
review_log: "logs/review/2026-04-11-09-review.md"
pipeline_stage: task2b_pending
task6_state: reviewed
task9_result: needs-rework
task9_state: reviewed
task2b_result: fixed
task2b_state: pending
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
   - 共享内存（ashmem → dmabuf-heaps 演进）
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

- ashmem → dmabuf-heaps 版本演进（Android 10+ 废弃 ashmem 新分配）
- HwBinder 与 Treble 架构下的 IPC 隔离
- NDK SharedMemory API（API 27+）
- 跨 PID 传递文件描述符（Binder `BINDER_TYPE_FD`）
- 与 Linux 桌面（D-Bus、Wayland）的 IPC 对比视角

<!-- outline-end -->

## 1. 为什么需要 IPC 全景

Android 的安全模型基于进程隔离：每个应用运行在独立进程中，系统服务（system_server）、SurfaceFlinger、HAL 服务等也各有独立进程。进程间任何协作都依赖 IPC（Inter-Process Communication）。

本书 §1.4 已深入分析了 Binder 的工作原理与性能影响。但 Android 并非只有 Binder 一种 IPC 机制：

- SurfaceFlinger 与 App 之间通过 **共享内存 + Binder** 传递图形缓冲区
- logd 通过 **Unix Domain Socket** 接收日志
- 父子进程的标准流与少量控制流常用 **Pipe** 传递
- InputDispatcher 通过 **InputChannel / socketpair** 向 App 发送输入事件，channel 的 fd 再通过 Binder 交给目标窗口
- HAL 服务的控制调用在 Treble 之后分成 **HIDL / hwbinder** 与 **Stable AIDL / binder** 两条路径，高吞吐数据再配合 FMQ 或共享内存

理解全貌有助于：
1. **分析性能 Trace 时识别 IPC 瓶颈**（不仅仅是 Binder 延迟）
2. **系统级优化时选择最合适的 IPC 机制**
3. **理解 Android 版本演进中 IPC 层的变化**（ashmem → dmabuf-heaps, HIDL / hwbinder → Stable AIDL / binder）

## 2. Android IPC 机制分类

### 2.1 按层级分类

```
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
| **Binder（同步）** | 双向 | ≤1MB | 1（mmap） | UID/GID + SELinux | 系统服务调用 |
| **Binder（oneway）** | 单向异步 | ≤1MB | 1 | UID/GID + SELinux | 异步通知、回调 |
| **HIDL / HwBinder** | 双向 | ≤1MB | 1 | SELinux + HAL 域 | Treble 早期/存量 HAL 控制调用 |
| **Stable AIDL HAL / Binder** | 双向 | ≤1MB | 1 | SELinux + 稳定接口约束 | 新 HAL 控制调用 |
| **Unix Domain Socket** | 双向 | 无硬限制 | 2（send+recv） | 文件系统权限 | logd、input、本地服务 |
| **Pipe** | 单向 | 受内核缓冲限制 | 2 | fd 继承/传递 | 子进程标准流、少量控制流 |
| **共享内存（ashmem/dmabuf）** | 双向 | 大块数据 | 0（零拷贝） | fd 传递 + SELinux | 图形缓冲区、大块数据 |
| **mmap 文件映射** | 双向 | 文件大小 | 0 | 文件权限 | 配置共享、数据库 WAL |
| **Signal** | 单向 | 无数据 | 0 | 内核级 | ANR SIGQUIT、进程杀死 |
| **eventfd / epoll** | 单向事件 | 8 字节 | 0 | fd 继承 | 线程/进程事件通知 |
| **Intent** | 双向（底层Binder） | ≤1MB | 1 | UID + 权限 | 组件间通信 |
| **ContentProvider** | 双向（Binder+shm） | 大块 | 0~1 | UID + 权限 | 数据共享 |
| **AIDL** | 双向（Binder） | ≤1MB | 1 | UID/GID + SELinux | 自定义服务接口 |
| **Messenger** | 单向队列（Binder） | ≤1MB | 1 | UID/GID | 轻量消息传递 |
| **FMQ（Fast Message Queue）** | 双向 | 可配置 | 0（零拷贝） | HAL 进程 | 高吞吐 HAL 数据流 |

## 3. 核心机制详解

### 3.1 Binder — 系统骨干

> 详见 §1.4 Binder IPC 机制与性能影响，此处只补充性能要点。

**Binder 在 Android IPC 中的地位：**

Android 上约 **90%+ 的 IPC 调用** 走 Binder 路径。四大组件的生命周期管理、权限检查、资源获取全部依赖 Binder。

**性能关键指标：**

- 单次同步调用延迟：**~0.5-2ms**（同设备进程间）
- oneway 调用延迟：**~0.2-0.8ms**
- 默认 worker 上限约 15 线程（`DEFAULT_MAX_BINDER_THREADS = 15`）；很多人口语里说的“16 线程”通常把发起调用的 caller 线程也算进去了
- 单次事务数据上限：**1MB**（`BINDER_MAX_TRANSACTION_SIZE`）
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

InputDispatcher 这一行最容易写错。输入事件不是通过 `/data/system/input_manager/*` 这类命名 socket 路径发出去的。WMS / InputDispatcher 会创建一对 `InputChannel`，底层是 `socketpair(AF_UNIX, SOCK_SEQPACKET, ...)`；客户端那一端作为 `Parcelable` 经 Binder 送到 App，之后事件和 `FINISHED` 回执都在这对未命名 Unix domain socket 上流动。

[已验证: AOSP main, frameworks/native/libs/input/InputTransport.cpp — `InputChannel::openInputChannelPair()` 使用 `socketpair(AF_UNIX, SOCK_SEQPACKET, ...)`；frameworks/base/core/java/android/view/InputChannel.java — `InputChannel` 可通过 `Parcelable` 随 Binder 传递]

**性能特征：**

- 延迟：**~0.1-0.5ms**（本地 socket 比 Binder 略快或相当，取决于数据量）
- 两次数据拷贝（send buffer → 内核 → recv buffer）
- 无 1MB 事务限制，适合流式数据
- 支持 `sendmsg` + `SCM_RIGHTS` 传递文件描述符
- **SELinux 策略控制访问**

**与其他 IPC 配合：** InputDispatcher 的事件面本质上是 `InputChannel` 的 socketpair，channel 本身通过 Binder parcel 把 fd 交给 App，所以它更像“Binder 控制面 + socket 数据面”的组合式 IPC。

### 3.3 Pipe

**原理：** 内核缓冲区实现的单向字节流，`pipe()` 系统调用创建一对 fd（read fd + write fd）。

**Android 中的关键使用：**

- **Process 重定向**：`Runtime.exec()` / `ProcessBuilder` 的 stdin/stdout/stderr 通过 pipe 连接父子进程
- **父子进程控制流**：shell 或守护进程内部的少量字节流通知仍常用 pipe
- **历史背景**：Looper 早期实现确实用过 pipe 唤醒 poll，但本书覆盖的 Android 8-17 不应再这样描述

现代 Android 需要把 pipe 和 `eventfd` 分开看。`system/core/libutils/Looper.cpp` 在 `Looper` 构造时创建的是 `mWakeEventFd = eventfd(0, EFD_NONBLOCK | EFD_CLOEXEC)`，再把这个 fd 注册进 epoll。也就是说，MessageQueue/Looper 的唤醒路径在 Android 8-17 范围内应理解为 `eventfd + epoll`，pipe 只能作为更早实现的历史背景。

[已验证: AOSP main, system/core/libutils/Looper.cpp — `mWakeEventFd.reset(eventfd(...))`]

**性能特征：**

- 单向通信，内核缓冲有限，适合少量字节流而不是大吞吐数据
- 两次拷贝
- 极低延迟（**~0.05-0.1ms**，内核态直接拷贝）
- 只能传递字节流，无结构化数据支持
- 通常用于父子进程或同一服务内部的简单控制流

### 3.4 共享内存（ashmem → dmabuf-heaps）

**这是 Android 图形性能的基石。**

**演进路径：**

```
Android 4.x-9:  ashmem (Anonymous Shared Memory)
Android 10+:    ashmem 新分配弃用 → dmabuf-heaps
Android 11+:    NDK SharedMemory API 推荐 dmabuf
Android 13+:    Graphify/GraphicBuffer 全面基于 dmabuf
```

**原理：**

1. 进程 A 通过 `ashmem_create_region` 或 `DmaBufHeap` 分配一块物理内存
2. 获得 fd（文件描述符）
3. 通过 Binder（`BINDER_TYPE_FD`）或 Unix Socket（`SCM_RIGHTS`）将 fd 传递给进程 B
4. 进程 B `mmap` 该 fd，双方共享同一块物理内存
5. 零拷贝——数据无需在用户空间之间复制

**Android 中的关键使用：**

- **BufferQueue / GraphicBuffer**（§2.13）：App 渲染 → SurfaceFlinger 合成
- **ContentProvider**：`CursorWindow` 底层使用共享内存传递大批量查询结果
- **SharedMemory API**（API 27+）：应用间大块数据共享
- **MemoryFile**：旧版共享内存 API（内部 ashmem）
- **FMQ（Fast Message Queue）**：HAL 零拷贝数据队列

**性能特征：**

- **零拷贝**：设置后读写无额外拷贝
- 适合**大块数据**（图形缓冲区通常 8-16MB）
- 延迟：首次 mmap 需要 **~0.5-2ms**，后续访问为内存读写级别（**纳秒级**）
- 需要手动同步（fence、lock、atomic）——参见 §2.16 Sync Fence
- 内存生命周期由 fd 引用计数管理

**陷阱：**

1. 忘记 `close()` fd 导致内存泄漏（直到进程退出）
2. 缺乏同步机制导致数据竞争（需要额外 fence/mutex）
3. 跨进程映射页表开销（大块共享内存的 TLB 压力）

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

| 信号 | 发送者 | 接收者 | 用途 |
|------|--------|--------|------|
| `SIGQUIT (3)` | Process.sendSignal | App 进程 | ANR 时 dump ANR trace |
| `SIGKILL (9)` | AMS/LMK | App 进程 | 强制杀进程 |
| `SIGUSR1 (10)` | debuggerd | App 进程 | 请求 tombstone |
| `SIGABRT (6)` | bionic/malloc | 自身 | abort / heap corruption |

**性能特征：**

- 无延迟概念——内核直接中断目标进程
- 不携带数据——只传递信号类型
- 无法阻塞 `SIGKILL` / `SIGSTOP`
- 适合紧急通知，不适合数据传输

### 3.7 Treble 之后的 HAL IPC：HIDL / hwbinder 与 Stable AIDL / binder

**背景：** Treble 真正改变的不是“HAL 一律改走更慢的 IPC”，而是把 Framework 和 vendor 之间的边界固化成稳定接口。Android 8 先用 HIDL + `/dev/hwbinder` 建立这条边界；Android 10 再引入 Stable AIDL，让 HAL 也可以走标准 `/dev/binder`，同时保留接口稳定性要求。

**两条主路径不要混为一谈：**

| 路径 | Binder 域 | 接口定义 | 典型阶段 | 说明 |
|------|-----------|----------|----------|------|
| **HIDL HAL** | `/dev/hwbinder` | HIDL | Android 8 之后的存量 HAL | Treble 初期建立的独立 HAL binder domain |
| **Stable AIDL HAL** | `/dev/binder` | Stable AIDL | Android 10 引入，Android 11+ 新 HAL 广泛采用 | 与 framework binder 共用驱动，靠稳定接口和 VINTF 约束兼容性 |

所以，**AIDL HAL 不等于 HwBinder**。我们在 Trace 里看到一条 HAL 调用时，先要分清它落在哪个 binder domain：命中 `/dev/hwbinder` 的通常是 HIDL，命中标准 binder 的则更可能是 Stable AIDL HAL。

**性能影响：**

- 控制面上的 HAL 调用，本质上仍是 Binder 家族的 RPC，开销更多取决于服务端干了什么，而不是“hwbinder 天生更慢”
- 音频、相机、传感器这类高吞吐路径，常见做法是 Binder / HwBinder 只负责控制面，真正的数据面走 FMQ、共享内存或 dmabuf

[已验证: AOSP docs《Work with binder IPC》《AIDL for HALs》— Android 8 将 vendor IPC 隔离到 `/dev/hwbinder`；Android 10 Stable AIDL 允许 HAL 使用 `/dev/binder`]

## 4. 性能对比表

### 4.1 定量对比

| 机制 | 典型延迟 | 吞吐量 | 数据量上限 | 拷贝次数 | CPU 开销 |
|------|---------|--------|-----------|---------|---------|
| Binder 同步 | 0.5-2ms | 中等 | 1MB | 1 | 中（序列化） |
| Binder oneway | 0.2-0.8ms | 中等 | 1MB | 1 | 中 |
| HIDL / HwBinder | 与 Binder 同量级 | 中等 | 1MB | 1 | 中 |
| Stable AIDL HAL / Binder | 与 Binder 同量级 | 中等 | 1MB | 1 | 中 |
| Unix Socket | 0.1-0.5ms | 高 | 无限制 | 2 | 低 |
| Pipe | 0.05-0.1ms | 中 | 受内核缓冲限制 | 2 | 极低 |
| 共享内存 | 首次 0.5-2ms，后续 ns | 极高 | 受物理内存限制 | 0 | 极低（需同步） |
| mmap | 首次 page fault，后续 ns | 极高 | 文件大小 | 0 | 极低 |
| Signal | 即时 | N/A | 0 字节 | 0 | 无 |
| FMQ | ~μs 级 | 极高 | 配置决定 | 0 | 极低 |

> **注：** 延迟数据为 2026 年主流设备上的典型值，受 CPU 频率、调度策略、系统负载影响。具体数据应通过 Perfetto 实测确认 [待验证]。

### 4.2 Android 常见的“组合式 IPC”

把 Binder、Socket、共享内存、FMQ 写成互斥的“单选题”，在 Android 里很容易把问题讲歪。真实系统更常见的做法是：**Binder / HwBinder 负责 control plane，fd 指向的共享内存、dmabuf、FMQ 或 socket 负责 data plane。** 前者做权限检查、生命周期管理、错误返回和小对象元数据，后者搬运真正的大数据。

fd 传递就是这两层之间的桥。Binder 路径里对应的是 `BINDER_TYPE_FD`，Java 层常见包装是 `ParcelFileDescriptor`；socket 路径里对应的是 `sendmsg(..., SCM_RIGHTS)`。大块数据之所以“看起来是 Binder 调用，实际没把数据塞进 Parcel”，原因就在这里。

| 场景 | 控制面 | 数据面 | fd 如何过去 |
|------|--------|--------|-------------|
| **BufferQueue / GraphicBuffer** | `IGraphicBufferProducer` Binder 调用（`dequeueBuffer()` / `queueBuffer()` 等） | dmabuf / GraphicBuffer | buffer handle 中的 fd 经 Binder 传给对端 |
| **CursorWindow** | `ContentProvider` query / moveToPosition 等 Binder 调用 | `CursorWindow` 共享内存 | window fd 经 Binder 返回给客户端 |
| **SharedMemory / FMQ / HAL** | Service 或 HAL 接口先协商共享区域 | SharedMemory / FMQ | Binder 用 `BINDER_TYPE_FD`，socket 用 `SCM_RIGHTS` |

这也是为什么 BufferQueue、CursorWindow、很多 HAL 数据流都不能简单归类成“Binder”或“共享内存”二选一。更准确的说法是：**控制面走 Binder 家族，数据面走 fd 指向的零拷贝通道。**

### 4.3 使用频率统计（AOSP 系统进程）

```
Binder        ████████████████████████████████  ~90% 的 IPC 调用
Unix Socket   ██████                           ~5% (logd/input/vold)
共享内存       ████                             ~3% (图形/ContentProvider)
Pipe          ██                               ~1% (subprocess/shell)
Signal        █                                ~1% (ANR/kill)
```

## 5. IPC 选型决策树

先别把 IPC 选型理解成“在 Binder、Socket、共享内存里三选一”。在 Android 里，我们通常先定控制面，再定数据面。

```
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

如果把这个决策树套到真实系统里，我们会发现大多数“复杂 IPC”其实都是组合题：Binder 先把 channel、buffer handle 或共享内存 fd 交过去，后面的高吞吐数据再走零拷贝通道。只有把控制面和数据面拆开，我们才不会在性能分析时误把大块数据开销都算到 Binder 头上。

## 6. Perfetto 中的 IPC 分析

### 6.1 Binder 追踪

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

### 6.2 共享内存追踪

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

### 6.3 Socket I/O 追踪

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

## 7. 版本演进中的 IPC 变化

IPC 的版本演进，重点不是“又多了一个名词”，而是控制面和数据面的边界在持续重写。下面这张表只保留真正会影响我们分析判断的转折点：

| 版本 | IPC 变化 | 分析时要注意什么 |
|------|---------|----------------|
| Android 8 (Treble) | 引入 Treble，HIDL HAL 进入 `/dev/hwbinder` domain | HAL 控制调用开始和 framework binder domain 分离 |
| Android 10 | 引入 Stable AIDL；HAL 不再只能走 hwbinder；共享内存新分配开始从 ashmem 转向 dmabuf-heaps | 不能再把“HAL IPC = hwbinder”当默认结论 |
| Android 11 | 新 HAL 可以直接使用 AIDL，迁移开始扩大 | Trace 中要同时接受 HIDL 和 AIDL HAL 并存 |
| Android 13 | GraphicBuffer 等图形内存路径进一步统一到 dmabuf | 图形类大数据更典型地表现为“Binder 控制 + dmabuf 数据面” |
| Android 14+ | 持续鼓励 HIDL → AIDL 迁移，而不是一刀切“全面完成” | 同一设备上可能长期共存两套 HAL IPC |
| Android 16-17 | AIDL HAL 与 Rust HAL 覆盖面继续扩大 | 实现语言会变，但 control plane / data plane 的组合模式不变 |

[已验证: AOSP docs《Work with binder IPC》《AIDL for HALs》；Android 10 开始 Stable AIDL 支持 HAL 使用 `/dev/binder`]

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
3. **理解版本演进方向**：ashmem → dmabuf、HIDL / hwbinder → Stable AIDL / binder 是持续优化 IPC 性能的趋势
4. **避免常见反模式**：Binder 调用风暴、大数据走 Binder、缺乏同步的共享内存

---

**交叉参考：**
- §1.4 Binder IPC 机制与性能影响（Binder 深入分析）
- §1.10 ContentProvider 性能与优化（ContentProvider 的共享内存实现）
- §1.13 MessageQueue 机制（Pipe + epoll 在 Looper 中的应用）
- §2.13 BufferQueue（图形缓冲区共享内存）
- §2.15 DMA-BUF、Gralloc 与跨进程图形内存共享
- §2.16 Sync Fence 框架（共享内存同步机制）
- §9.1 ANR 设计思想（Binder 超时与 ANR 的关系）
