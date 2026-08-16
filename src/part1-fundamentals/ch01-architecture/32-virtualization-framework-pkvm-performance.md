---
title: "Android 17 AVF 架构与 pKVM 隔离性能边界"
chapter: "1.32"
section: "1.32"
status: ready-for-review
applicable_versions: "Android 13 (API 33) - Android 17 (API 37)"
tags: [avf, virtualization, pkvm, crosvm, microdroid, vm-lifecycle, isolation-overhead]
related_chapters: ["1.3", "1.4", "4.1", "4.2"]
last_verified: "2026-07-25"
last_verified_against: "AOSP android-17.0.0_r1 + kernel android17-6.18-2026-06_r6"
confidence: high
sources:
  - type: official
    path: "source.android.com/docs/core/virtualization"
  - type: official
    path: "source.android.com/docs/core/virtualization/architecture"
  - type: official
    path: "source.android.com/docs/core/virtualization/virtualization-service"
  - type: official
    path: "source.android.com/docs/core/virtualization/microdroid"
  - type: official
    path: "source.android.com/docs/core/virtualization/security"
  - type: aosp
    path: "packages/modules/Virtualization/android/virtualizationservice/src/main.rs"
  - type: aosp
    path: "packages/modules/Virtualization/android/virtmgr/src/main.rs"
  - type: aosp
    path: "packages/modules/Virtualization/libs/framework-virtualization/src/android/system/virtualmachine/"
  - type: aosp
    path: "packages/modules/Virtualization/tests/benchmark/"
  - type: aosp
    path: "external/crosvm/"
  - type: kernel
    path: "arch/arm64/kvm/hyp/nvhe/mem_protect.c (android17-6.18-2026-06_r6)"
  - type: kernel
    path: "arch/arm64/include/asm/kvm_pkvm.h (android17-6.18-2026-06_r6)"
---

# 1.32 Android 17 AVF 架构与 pKVM 隔离性能边界

Android Virtualization Framework（Android 虚拟化框架，AVF）从 Android 13 开始提供受保护虚拟机能力。它面向需要抵御宿主（host）Android 被攻破的敏感工作负载：宿主仍负责创建、调度和终止虚拟机，但不能读取 protected VM（受保护虚拟机，pVM）的私有内存，也不能悄悄替换通过验证的 Microdroid 和其中运行的载荷（payload）。

“运行在虚拟机里会慢多少”没有跨设备固定答案。AVF 的成本取决于 vCPU（虚拟 CPU）调度、VM exit（执行从客户机退出到虚拟机监控器或宿主）、共享内存窗口、virtio 虚拟 I/O、验证启动以及 payload 行为。可复现的测量必须建立在 Android 17 的组件关系和安全边界之上。

## 一、Android 17 中的 AVF 组件

### 1.1 宿主侧有两个服务层次

AVF 文档里的 `VirtualizationService` 容易与 `system_server` 中的 Java 服务混淆。API 37 的实现由多个独立进程组成：

```text
Host app / system component
        │  VirtualMachineManager / VirtualMachine (@SystemApi)
        ▼
framework-virtualization Java library
        │  spawn + RpcBinder over Unix-domain socket
        ▼
virtmgr child process (Rust）
        │  one crosvm child process for each running VM
        ├─────────────────────────────┐
        ▼                             ▼
VirtualizationServiceInternal     crosvm
(global Rust lazy Binder service)          │ /dev/kvm ioctl
        │ CID / global resources     ▼
        └────────────────────────► pKVM at EL2
                                      │
                                      ▼
                           pvmfw → bootloader → guest OS
```

`libs/framework-virtualization/.../VirtualizationService.java` 明确说明，该类代表一个正在运行并承载 AIDL 服务的 `virtmgr` 实例。`nativeSpawn()` 创建子进程，Unix 域套接字（一种本机进程间通信通道）上的 RpcBinder 负责宿主客户端与 `virtmgr` 通信。

`android/virtualizationservice/src/main.rs` 则注册全局的 `android.system.virtualizationservice` lazy Binder 服务；lazy 表示有请求时按需启动。它负责虚拟机上下文 ID（CID）、全局资源、统计和维护。它与每个客户端启动的 `virtmgr` 不在同一进程，也不位于 `system_server`。

每个 crosvm 进程只运行一台 VM；一个 `virtmgr` 可以管理多台 crosvm 子进程。crosvm 通过 `/dev/kvm` 的系统、VM、vCPU 和设备 ioctl（用户态控制内核设备的系统调用）创建并运行虚拟机。

### 1.2 pKVM、crosvm 与 Microdroid 的分工

| 组件 | 所在位置 | 主要职责 | 不负责什么 |
|---|---|---|---|
| pKVM | ARM64 的虚拟机监控器异常级别 EL2，来自 Android Common Kernel（ACK）的 KVM | 宿主 / 客户机 Stage-2 二阶段地址转换权限、页面所有权、vCPU 切换和 pVM 保护 | VM 配置、磁盘组装、payload 生命周期 |
| crosvm | 宿主用户空间 Rust 进程 | 虚拟机监控器（VMM）、KVM ioctl、vCPU 线程、virtio 设备、VM 内存布局 | 判定 APK / payload 的业务可信性 |
| `virtmgr` | 宿主用户空间 Rust 进程 | AIDL 生命周期、镜像 / 文件描述符（FD）准备、启动和监控 crosvm | 在 `system_server` 中常驻 |
| pvmfw | pVM 首段固件 | 验证初始镜像、维护实例身份、派生每台 VM 的机密 | 提供 Android framework API |
| Microdroid | 客户机 OS | 验证启动、SELinux、Bionic、原生 payload、Binder RPC | 完整 Android UI 和应用框架 |

Microdroid 是 AVF 提供的一种轻量客户机 OS，但不是 AVF 唯一支持的客户机。API 37 还允许自定义 VM 配置；Android 的 Linux 开发环境也是基于 AVF 的 non-protected VM（非受保护虚拟机）用例。

## 二、Microdroid 不是“小号完整 Android”

Microdroid 为原生 payload 提供 Android 基础设施：Bionic C 库、验证启动（Verified Boot）、SELinux、APEX 系统组件包、日志 / 崩溃调试能力，以及基于 vsock（宿主与客户机通信的虚拟套接字）的 Binder RPC。它明确不提供：

- `system_server` 和 Zygote；
- 图形/UI；
- HAL；
- `android.*` Java framework API。

启用 ART APEX 后可以使用 `java.*` 核心 API，但这不等于拥有常规 Android 应用运行环境。payload 通常是 APK 内嵌的原生共享库，由 Microdroid payload launcher（载荷启动器）执行。

因此，下列推断在 API 37 中没有依据：

- Microdroid 默认含完整 ART、SystemServer 和 Service Manager 服务集；
- protected 模式的 Microdroid 可以直接使用 virtio-gpu 或 NPU 硬件抽象层（HAL）加速通用 AI 推理；
- 它能直接承载完整工作资料、Launcher 或 SystemUI。

需要 UI、GPU 或设备直通的自定义 VM，应按具体客户机、crosvm 构建选项和产品安全策略单独评估，不能套用 Microdroid 的能力表。

## 三、pKVM 如何阻止宿主读取 pVM 内存

### 3.1 宿主也受 Stage-2 约束

传统 KVM 通常不使用 Stage-2 限制宿主，因此宿主内核可以访问承载客户机内存的物理页。pKVM 在宿主上下文中也启用 Stage-2：

- 宿主 Stage-2 使用恒等映射（identity mapping），即映射前后地址不变，主要负责访问控制；
- 客户机仍有自己的 Stage-2，把客户机中间物理地址（IPA）映射到真实物理地址；
- EL2 维护页面所有者，并决定宿主、某台 pVM、虚拟机监控器或设备能否映射该页。

Android 启动之初，除虚拟机监控器保留区外的内存归宿主所有。创建 pVM 时，宿主把页面 donate（捐赠）给客户机；EL2 随后从宿主 Stage-2 中撤销这些页的访问权限。crosvm 进程仍保留用于建立 KVM memslot（客户机内存槽）的虚拟地址区间和内存记账关系，但对应物理页已不在宿主 Stage-2 的可访问映射中。宿主 CPU 或受宿主控制的设备，不能凭借这段用户空间地址绕过 EL2 读取 pVM 私有页。

当前内核把宿主 Stage-2 标记为 `KVM_PGTABLE_S2_IDMAP`，并在 `host_stage2_set_owner_locked()` 中根据所有者 ID 建立宿主映射或记录其他所有者。保护来自 EL2 管理的权限，与某个用户空间 `shared_buf` 名称无关。

### 3.2 `donate`、`share`、`unshare`、`relinquish` 四类动作

| 动作 | 所有权 | 宿主是否可访问 | 常见用途 |
|---|---|---|---|
| `donate` | 宿主 → pVM | 否 | 客户机私有 RAM |
| `share` | 所有者不变 | 是，按授权范围 | virtio 共享窗口、宿主 / 客户机通信 |
| `unshare` | 所有者不变 | 取消宿主映射 | 结束临时共享 |
| `relinquish` | pVM → 宿主 | 是，重新归宿主 | 内存 balloon 或长期运行的 VM 归还不用的页 |

客户机归还页面时，内核会撤销客户机 Stage-2 映射，清理页面内容，再把所有者改回宿主。下面的片段展示归还私有页的核心顺序：

```c
/* Zap the guest stage2 pte and return ownership to the host */
WARN_ON(kvm_pgtable_stage2_unmap(&vm->pgt, ipa, PAGE_SIZE));

if (!(flags & KVM_FUNC_MEM_RELINQUISH_NO_POISON))
    hyp_poison_page(phys, PAGE_SIZE);
else
    hyp_flush_page(phys, PAGE_SIZE);

ret = __host_stage2_set_owner_locked(
        phys, PAGE_SIZE, PKVM_ID_HOST, 0,
        HOST_SET_PSCI_MEM_PROTECT);
```

页面回收伴随权限变更和内容处理；配置给 VM 的内存也可以在 VM 销毁前归还。pKVM 提供 `relinquish` hypercall（客户机请求虚拟机监控器执行操作的调用），virtio balloon（由客户机配合归还内存的虚拟设备）可以借此回收长期运行 VM 中不用的页。

### 3.3 共享窗口为什么影响 I/O

virtio 的常规设计假设宿主设备后端可以根据 virtqueue（virtio 队列）描述符访问客户机 buffer。pVM 私有页不满足这个假设。若每次请求都临时 `share` 一个小 buffer，页面粒度共享还可能暴露同页中的无关数据。

AVF 的受保护客户机因此为 virtqueue 和数据 buffer 预留固定共享内存窗口，客户机在私有页与共享窗口之间执行 bounce copy（中转复制）。性能影响包括：

- 小型内存映射 I/O（MMIO）控制访问，可能触发客户机 → EL2 → 宿主 VMM → 客户机的往返；
- 大数据通常走共享 virtqueue，不需要每个字节都触发 VM exit；
- bounce copy、缓存维护和唤醒次数会影响吞吐与尾延迟；
- buffer 大小、批量深度和 I/O 模式不同，结果会相差很大。

这也是不能给所有 virtio 块设备（virtio-blk）、vsock 或 Binder RPC 写一个固定微秒数的原因。

## 四、内存占用与宿主内存压力

### 4.1 客户机 RAM 记在 crosvm 名下

crosvm 通过 `mmap`（内存映射）分配 VM 物理内存，再用 `KVM_SET_USER_MEMORY_REGION` 建立 memslot。Android 官方架构文档指出，这部分内存归属管理该 VM 的 crosvm 进程；宿主内存不足时，crosvm 可以被终止，整台 VM 也会随之停止。

对于已经捐赠给 pVM 的私有页：

- 宿主不能把页面换出到 swap，也不能执行 KSM（合并相同内存页）；
- 宿主不能把它当作普通匿名页读取；
- 客户机通过 `relinquish` 或 balloon 归还后，页面可以回到宿主；
- VM 停止时，虚拟机监控器清理并归还剩余页面。

“128 MiB 配置永久硬占 128 MiB，直到销毁”过于绝对；“宿主的低内存终止守护进程（lmkd）能直接回收客户机内某几页”也不准确。内存压力的控制单元通常是 crosvm 或整台 VM，细粒度回收依赖客户机主动配合。

### 4.2 不要用静态组件表估算最小内存

Microdroid 的最低可启动内存受下列因素影响：

- protected 或 non-protected 模式；
- 调试级别（debug level）；
- 启用的 APEX、ART 和 payload；
- vCPU 数、内核和厂商模块；
- 大页（huge page）可用性；
- 客户机页缓存（page cache）与运行时峰值。

AOSP 的 `MicrodroidBenchmarks.canBootMicrodroidWithMemory()` 在 16～512 MiB 区间做二分尝试，只有 payload 成功启动才记录结果。源码选择运行时探测，说明“内核 8 MiB + ART 24 MiB + 设备 4 MiB”这类静态加法不能作为产品容量结论。

### 4.3 AOSP 的内存测量方式

API 37 的基准测试同时采集三组数据：

1. 客户机 `/proc/meminfo`：`MemTotal`、`MemAvailable`、`Cached`、`Slab`；
2. 宿主 `/proc/<crosvm-pid>/smaps`：区分 `crosvm_guest` 映射与 VMM 自身的 RSS（驻留内存）和 PSS（按共享比例分摊后的内存）；
3. KVM 调试统计（设备支持时）：如 `protected shared` / `hyp` 相关内存，其中 hyp 指虚拟机监控器层。

这三组数的口径不同，不能相加后当作 AVF 总内存。应分别报告客户机配置量、客户机工作集、crosvm 在宿主侧的 PSS、pKVM / KVM 额外开销，以及回收前后的变化。

## 五、CPU 调度与 VM exit

### 5.1 vCPU 是宿主调度器管理的线程

每个 vCPU 对应 crosvm 中的一个 POSIX 线程。线程调用 `KVM_RUN` 后进入客户机；出现需要 VMM 处理的 I/O、vCPU 停机（halt）或其他退出原因时，`KVM_RUN` 返回宿主用户空间。

宿主 Linux 调度器仍可抢占 vCPU 线程，并把客户机执行时间计入该线程。vCPU 线程可以使用常规 QoS（服务质量）机制设置 CPU affinity（亲和性）、cpuset（可运行的 CPU 集合）、uclamp（调度器利用率上下界）和调度策略。客户机不能绕过宿主调度器获得物理 CPU。

因此，VM 内看到的慢任务至少可能来自三层：

1. 客户机内线程没有被客户机调度器选中；
2. 对应 vCPU 线程在宿主上处于 runnable（已就绪）状态，但没有获得 CPU；
3. vCPU 因 MMIO、virtio 或中断等事件退出，在 crosvm 或宿主内核等待。

只看客户机内的 Perfetto 无法区分后两层。性能分析需要把客户机时间线与宿主的 crosvm / vCPU 线程调度对齐。

### 5.2 每次 I/O 不等同于一次完整 VM exit

virtio 用 MMIO 完成设备控制与通知，数据面主要通过共享 virtqueue 传输。一次高层文件读写可能拆成多个队列请求，也可能批量消费多个描述符。eventfd / epoll 事件通知、中断合并（interrupt coalescing）和队列深度，都会改变 VM exit 与唤醒次数。

准确的优化目标通常是：

- 每单位业务数据产生多少次通知和唤醒；
- vCPU 线程退出后在宿主停留多久；
- crosvm 设备处理是否受 CPU、I/O 或锁限制；
- 客户机提交深度能否覆盖宿主处理延迟。

没有设备型号、CPU 频点、负载、virtqueue 配置和统计分布时，`VM exit = 5–10 μs` 或“比系统调用（syscall）慢 3–10 倍”都不能作为 Android 17 平台结论。

## 六、vsock 与 Binder RPC 的边界

### 6.1 vsock 是宿主与 pVM 的基础通信通道

`VirtualizationServiceInternal` 为运行中的 VM 分配上下文 ID（CID）。CID 在 VM 存活期间唯一；VM 结束且相关 `IVirtualMachine` 引用释放后，数值可以复用。端口由客户机服务自行选择。

Java `VirtualMachine.connectVsock(port)` 返回一个新的 `ParcelFileDescriptor`。它是字节流通信入口，调用方负责消息分帧（framing，即如何划分消息边界）、超时、下游压力控制和关闭。一次 `write()` 不一定对应对端的一次 `read()`。

### 6.2 Binder RPC 运行在预连接的 vsock 上

Microdroid 支持基于 vsock 的 Binder RPC。API 37 的 `connectToVsockServer()` 代码关系可以概括为：

```text
connectToVsockServer(port)
    = connectVsock(port)
    + binderFromPreconnectedClient(connectionProvider)
```

这条链路使用 Binder RPC 协议和 Binder 对象模型，但传输不依赖宿主与客户机共享同一个 `/dev/binder` 驱动实例。客户机私有内存也不会因为传递了 Binder 对象而自动对宿主可见。

对 payload API，Binder RPC 适合控制命令和结构化小消息；大数据应评估流式 vsock、文件交换或专用共享机制。选择依据包括复制次数、批量大小、失败恢复和数据敏感性，不能套用未经测量的固定延迟表。

### 6.3 AOSP 的测量方式值得复用

`MicrodroidBenchmarks` 分别测量：

- `testRpcBinderLatency()`：预热 10 次，随后执行 10,000 次小 RPC；
- `testVsockLatency()`：独立的 echo / reverse（回显 / 反转）协议，同样在预热后循环测量；
- `testVsockTransferFromHostToVM()`：48 MiB 连续发送，报告吞吐；
- `testVirtioBlkSeqReadRate()` / `RandReadRate()`：区分顺序与随机读，并丢弃首次受宿主页缓存冷启动影响的样本。

这些用例没有把某一台实验设备的结果固化为平台常量。复用时应保留原始样本，报告 P50 / P90 / P99 分位数，并记录 protected 模式、调试级别、内存、vCPU 数量与拓扑（组织关系）、huge page、uclamp、温度和 CPU 频点。

## 七、VM 生命周期语义

### 7.1 `run()` 返回不代表 payload 已就绪

`VirtualMachine.run()` 完成启动请求后即可返回。VM 是否开始运行、OS 是否启动、payload 是否就绪，要通过 `VirtualMachineCallback` 观察。常用节点包括：

- API 调用开始；
- vCPU 开始；
- 引导加载程序 / pvmfw 完成；
- 客户机内核运行 `/init`；
- `onPayloadStarted()`；
- `onPayloadReady()`。

AOSP 启动基准测试将总时长分成 `VM_START`、`BOOTLOADER`、`KERNEL` 和 `USERSPACE`。更细的分段依赖 `FULL` 调试输出中的日志标记；调试配置本身会改变启动路径，因此总时长与分段测试应分别标注配置。

### 7.2 `stop()` 会强制停止 VM

API 文档把 `VirtualMachine.stop()` 比作拔电源：客户机软件不会收到正常关机通知，加密存储写入可能未持久化。需要正常关机（graceful shutdown）时，应通过 payload 的 Binder / vsock 协议请求退出，并等待 `onPayloadFinished()`。

“正常销毁 100–500 ms，强杀 50–200 ms”没有平台保证。应分别测量：

- payload 收到退出请求到 `onPayloadFinished()`；
- `stop()` 调用到 `onStopped()`；
- crosvm 退出后 RSS、KVM 和 pKVM 页面完成归还的时间。

### 7.3 引用生命周期会影响 VM 存活

`IVirtualMachine` Binder 对象跟踪 VM 所有权。没有强引用后，`VirtualizationService` 会关闭 VM；启动它的客户端若被低内存终止机制（LMK）结束，VM 也会随引用消失而停止，避免孤儿资源长期占用。

### 7.4 并发 VM 没有“Arm 最多 16 台”的通用限制

API 37 的 `VirtualMachine.run()` 注释写明：并发运行数量除可用内存外没有 Java API 固定限制。当前 6.18 内核定义 `KVM_MAX_PVMS = 255`，这是内核对象上限，也不是设备可承载 255 台 VM 的性能承诺。

产品上限还受以下条件约束：

- 每台 VM 的客户机 RAM、crosvm PSS 和共享内存；
- vCPU 总数与调度容量；
- CID、文件描述符（FD）、进程和 SELinux 策略；
- pKVM 固件、IOMMU（I/O 内存管理单元）和可分配设备资源；
- 前后台管理策略。

AOSP 基准测试包含同时创建 8 台 VM 的测试路径，说明“每个应用默认只能运行 1 台”的概括并不成立，但也不代表所有设备都应以 8 台为容量目标。

## 八、protected 与 non-protected 模式的选择

| 维度 | protected VM | non-protected VM |
|---|---|---|
| 宿主是否可映射客户机私有内存 | 不可，除非客户机显式共享 | VMM 保留访问能力 |
| 主要目标 | 宿主被攻破时仍保护客户机机密性和完整性 | 常规虚拟化与开发环境 |
| 启动链 | pvmfw/受保护启动与实例身份参与 | 不需要同等 pVM 保护链 |
| I/O 数据路径 | virtio 固定共享窗口与中转复制更重要 | 可使用常规 KVM / VMM 客户机内存路径 |
| 可用性 | 宿主仍能停止、饿死或拒绝服务 | 宿主同样控制资源 |
| 远程证明 | 依赖设备和 AVF 能力，可用于 pVM | 不提供同等级 pVM 证明 |

pKVM 保护机密性和完整性，不承诺客户机相对于宿主的可用性。宿主调度器可以不给 vCPU 时间，宿主也可以终止 crosvm。安全设计不能把“数据不被读取”误写成“服务不会被中断”。

AVF 也没有完全替代 TrustZone。可信执行环境（TEE）仍承载 KeyMint、Gatekeeper 等依赖安全世界（secure world）的设备能力；pVM 提供更丰富、可动态创建的隔离执行环境。两者的信任根、设备访问和攻击面不同，不宜用固定的强弱关系或世界切换微秒数排序。

## 九、Android 17 的性能验证清单

### 9.1 固定实验条件

至少记录以下配置：

- 系统构建指纹（build fingerprint）、AOSP / GKI（通用内核镜像）/ 厂商内核版本；
- `protected` / `non-protected`；
- Microdroid 或自定义客户机；
- 调试级别 `NONE` / `FULL`；
- vCPU 拓扑、客户机内存、huge page；
- payload / APEX 集合与存储镜像；
- 宿主温度、频点、充电状态和前后台负载。

### 9.2 启动

1. 以 `run()` 调用时刻为起点；
2. 以 `onPayloadStarted()` 或业务自定义就绪事件为终点，两者分开报告；
3. `FULL` 调试级别下再采集 vCPU、引导加载程序、内核、用户空间分段；
4. 至少区分首次实例创建、已有实例重启和页缓存冷热；
5. 报告分布，不只报平均值。

### 9.3 CPU 与 I/O

1. 客户机 Perfetto 观察 payload、客户机调度器和客户机 I/O；
2. 宿主 Perfetto 观察 crosvm、vCPU 线程、`sched` 调度事件和块 I/O；
3. 统计每单位请求的 VM exit / 通知次数；
4. 顺序 / 随机、吞吐 / 延迟、小消息 / 大流量分别测试；
5. 检查宿主页缓存、CPU affinity 和 uclamp 是否改变结论。

### 9.4 内存与回收

1. 记录配置内存与客户机 `MemAvailable`；
2. 从 crosvm `smaps` 分开 VMM PSS 和 `crosvm_guest` 映射；
3. 设备允许时，记录 KVM 调试统计中的 `protected shared` / `hyp` 相关内存；
4. 对 balloon / trim（主动回收）前后使用相同工作集；
5. 模拟宿主内存压力，确认 crosvm 被终止后的 VM 停止和客户端恢复策略。

### 9.5 通信与停止

1. Binder RPC 与原始 vsock 使用相同 payload 逻辑和消息大小；
2. 明确预热次数、迭代数、连接复用与序列化格式；
3. 单独测量连接建立、单次 RPC、稳态（steady-state）吞吐和尾延迟；
4. 分开测量 payload 正常退出与 `stop()` 强制终止；
5. 对敏感数据验证它只进入预期共享区或加密存储。

## 十、源码锚点

- Android 17 / API 37：AOSP `android-17.0.0_r1`
  - `packages/modules/Virtualization/android/virtualizationservice/src/main.rs`
  - `packages/modules/Virtualization/android/virtmgr/src/main.rs`
  - `packages/modules/Virtualization/android/virtmgr/src/virtualmachine.rs`
  - `packages/modules/Virtualization/libs/framework-virtualization/src/android/system/virtualmachine/VirtualizationService.java`
  - `.../VirtualMachineManager.java`、`VirtualMachine.java`、`VirtualMachineConfig.java`
  - `packages/modules/Virtualization/tests/benchmark/src/java/com/android/microdroid/benchmark/MicrodroidBenchmarks.java`
  - `external/crosvm/`
- 内核 `android17-6.18-2026-06_r6`
  - `arch/arm64/kvm/hyp/nvhe/mem_protect.c`
  - `arch/arm64/include/asm/kvm_pkvm.h`
- 官方架构说明
  - [AVF overview](https://source.android.com/docs/core/virtualization)
  - [AVF architecture](https://source.android.com/docs/core/virtualization/architecture)
  - [VirtualizationService](https://source.android.com/docs/core/virtualization/virtualization-service)
  - [Microdroid](https://source.android.com/docs/core/virtualization/microdroid)
  - [AVF security](https://source.android.com/docs/core/virtualization/security)

从 Android 13 到 Android 17，AVF 的 API 与客户机能力持续增加；性能结论仍必须绑定设备、内核、客户机、调试级别和具体负载。缺少这些条件的固定启动时间、微秒延迟或百分比开销，不应写成平台事实。
