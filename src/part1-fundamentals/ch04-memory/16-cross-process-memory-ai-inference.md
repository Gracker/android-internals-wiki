---
title: "跨进程内存共享与端侧推理预算"
chapter: "4.16"
status: ready-for-review
drafted_date: "2026-07-06"
applicable_versions: "Android 14 (API 34) - Android 17 (API 37)"
last_verified: "2026-07-06"
last_verified_against: "AOSP android-17.0.0_r1"
confidence: medium
sources:
  - type: aosp
    path: "frameworks/base/core/java/android/os/SharedMemory.java"
  - type: aosp
    path: "frameworks/base/core/java/android/app/appfunctions/AppFunctionService.java"
  - type: aosp
    path: "frameworks/base/core/java/android/app/appfunctions/AppFunctionManager.java"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/am/MemoryLimiter.java"
  - type: aosp
    path: "frameworks/native/libs/binder/Parcel.cpp (Binder transaction buffer)"
  - type: aosp
    path: "system/sepolicy/ — SELinux policy for isolated processes"
tags: [ai-agent, memory, sandbox, data-reuse, isolation, ml-runtime, sharedmemory]
related_chapters: ["4.3", "4.5", "4.13", "5.20", "5.21", "5.27", "23.25"]
created_by: "task2a-knowledge-gap"
created_date: "2026-07-06"
gap_source: "素材驱动/研究素材"
---

# 4.16 跨进程内存共享与端侧推理预算

Android 17 / API 37 没有名为“AI Agent 进程”的内核对象，也没有为 Agent 定义专用内存命名空间。模型推理、工具调用和跨应用协作仍受 Android 已有机制约束：应用 UID、进程地址空间、Binder、文件描述符、SELinux、cgroup v2、AMS 进程状态和 lmkd。

看到某个产品使用 AICore、私有推理服务或厂商 NPU service 时，不能把该产品的包名、进程优先级和缓存策略写成 AOSP Android 17 的通用行为。`com.google.android.aicore` 不属于 AOSP `android-17.0.0_r1`；它在具体设备上的生命周期和内存策略要以该设备实现为准。

平台层面可以确认以下结论：

- 内存计入分配、映射或导入它的进程和 cgroup；
- 同一物理页可以出现在多个进程的 RSS 中，PSS 才会按映射者分摊；
- Binder 适合控制消息和小数据，大块内容应通过 fd、共享缓冲区或受控 URI 传递；
- `android:process`、isolated service 和系统推理服务提供的隔离强度不同；
- Android 17 的 MemoryLimiter 与 lmkd 仍依据进程状态、设备配置和内存压力工作，没有通用的“正在执行 AI”进程标签；设备配置可以单独豁免默认的 sandboxed inference service package。

## 4.16.1 先确定内存属于哪个进程

端侧推理常见四种部署方式：

| 方式 | UID / 进程 | 内存计入 | 隔离边界 |
| --- | --- | --- | --- |
| App 进程内推理 | 应用 UID / 主进程 | 主进程的 Java、native、file mapping、dma-buf 等 | 无额外进程隔离 |
| `android:process=":inference"` | 通常仍是应用 UID / 独立进程 | 独立 PID 的各类内存 | 隔离地址空间和进程故障；不构成跨 UID 安全沙箱 |
| `android:isolatedProcess="true"` service | 系统分配的 isolated UID / 独立进程 | isolated 进程 | 权限和数据访问明显收窄，只能通过获准的 IPC 与句柄取数据 |
| 系统或厂商推理服务 | 服务自己的 UID / 进程 | 服务进程及其 cgroup | 由系统映像、SELinux 和服务协议决定 |

### 独立进程不会自动继承固定的 oom_score_adj

AMS 根据组件状态、绑定关系、前台可感知性等信息持续计算进程状态和 `oom_score_adj`。同一应用的主进程和 `:inference` 进程可以得到不同分值；前台组件绑定的 service 也可能因依赖关系被提升。

因此，不能把“推理 service”固定写成 `oom_score_adj=500～800`，也不能假设系统推理服务永远比调用方更难被杀。应该在目标设备和目标场景中读取：

```shell
adb shell dumpsys activity processes
adb shell cat /proc/<pid>/oom_score_adj
```

第一条用于观察 AMS 认定的进程状态和依赖，第二条用于确认该时刻写入内核的分值。量测需要覆盖前台、退后台、解绑、冻结和重新绑定等状态变化。

进程的内存变大不会直接调高它的 `oom_score_adj`。内存大小会影响系统释放内存的收益，并可能在同一 adj 档位的选择中发挥作用；进程重要性仍由 AMS 的状态模型决定。

### `android:process` 解决故障隔离，不解决数据保密

以冒号开头的私有进程名通常让组件运行在应用自己的另一个 Linux 进程中，但仍使用应用 UID。它适合：

- 把 native 推理引擎崩溃限制在单独 PID；
- 让主界面与推理进程分别观测内存；
- 在组件不再使用时终止推理进程，回收其整个地址空间。

它不适合用作“不可信模型代码”的保密沙箱。相同应用身份能够使用该应用获准的数据和能力，具体可访问范围还受 SELinux、文件模式和组件实现影响。

### isolated service 的能力要显式传入

Manifest 可以声明：

```xml
<service
    android:name=".InferenceService"
    android:isolatedProcess="true"
    android:exported="false" />
```

`attrs_manifest.xml` 对 isolated process 的定义是“运行在与系统其余部分隔离的特殊进程”，通信入口为 service 的启动和绑定 API。这个进程不以宿主应用 UID 运行，也不能假设拥有宿主的运行时权限、私有文件访问或任意系统服务访问能力。

宿主应通过受约束的 Binder 接口传入完成一次请求所需的 fd、只读共享区和最少元数据。需要 GPU、codec 或其他硬件服务时，还要确认该设备为对应 isolated domain 配置了哪些服务与设备权限。AOSP 的 `isolated_compute_app` 有单独的 SELinux 规则，普通 `isolated_app` 不能据此获得相同能力。

## 4.16.2 RSS、PSS 与共享页怎样记账

跨进程复用常见的误判是：“两个进程都显示 400 MiB RSS，所以系统用了 800 MiB。”RSS 会把当前驻留在每个进程页表中的共享页完整计入每个进程，直接相加会重复。

对一页被 `N` 个进程映射的物理页，可用下面的简化关系理解 PSS：

```text
每个映射进程的 PSS 贡献 ≈ 页大小 / N
所有映射进程的 PSS 贡献之和 ≈ 页大小
```

它只适用于当时驻留且由这些进程共同映射的页。若有进程尚未 fault-in、已经解除映射，或私有写入触发 COW，`N` 和物理页集合都会变化。

| 内存来源 | RSS 表现 | PSS / 共享语义 | 常见遗漏 |
| --- | --- | --- | --- |
| Java heap、匿名 native heap | 通常只计入一个进程 | 主要计入该进程 | allocator 缓存使 free 后 RSS 未立即下降 |
| 只读文件 `mmap` | 每个进程计入驻留页 | 同一文件页可由 page cache 分摊 | 解压、重排或写时复制会新增私有页 |
| `SharedMemory` | 每个映射者计入驻留共享页 | PSS 按映射者分摊 | fd 已关闭时，现有 mapping 仍可存活 |
| `HardwareBuffer` / dma-buf | 可能不完整体现在普通匿名/file 分类 | 由导入者、驱动和统计接口决定 | CPU、GPU、display、NPU 可同时持有引用 |
| 加速器私有内存 | 依赖驱动 | 未必能归到调用进程的常规 PSS | 驱动复制、常驻缓存和固件内存 |

分析模型内存时，至少要分别记录 Java heap、native heap、file mapping、shared/dma-buf、swap 和驱动侧内存。单看 `Debug.MemoryInfo.getTotalPss()` 无法解释每一类生命周期。

## 4.16.3 IPC 先传控制信息，再传大块数据

Android 17 的 libbinder 在 `ProcessState.cpp` 为接收端映射：

```cpp
#define BINDER_VM_SIZE ((1 * 1024 * 1024) - sysconf(_SC_PAGE_SIZE) * 2)
```

这是每个进程共享的 Binder 接收缓冲区，多个正在进行的事务共同使用，不能理解成“每个 Binder 线程 1 MiB”。请求、返回值、对象偏移以及并发事务都会占用空间。

`TransactionTooLargeException` 的 Java 文档也强调，它只是大事务失败时的启发式异常。调用方无法可靠判断是请求未送达，还是服务端已经处理请求但返回值发送失败，所以要按“可能部分完成”设计幂等性。

公开 API `IBinder.getSuggestedMaxIpcSizeBytes()` 返回 64 KiB；它引用的 `MAX_IPC_SIZE` 常量在源码中带有 `@hide`，应用不能直接访问。64 KiB 是让事务安全低于接收缓冲区上限的建议值，并非驱动硬上限。工程上可按下面的分工选择通道：

| 内容 | 优先方式 | 原因 |
| --- | --- | --- |
| 命令、token、状态、小型结构体 | AIDL / Parcelable | 边界清楚，易做权限与版本校验 |
| 一次性大块字节数据 | `SharedMemory` + Binder fd | payload 不占 Binder 大缓冲区 |
| 图像、视频帧、硬件可导入 tensor | `HardwareBuffer` | 允许硬件组件共享同一缓冲对象 |
| 持久内容或可分页记录 | `ContentProvider` + URI / fd | 有权限、生命周期和查询语义 |
| 跨应用受控动作 | App Functions | system_server 做调用资格校验，目标 App 执行业务 |

“通过 Binder 传 fd”仍会传一个小 Parcel。被共享的是 fd 指向的对象，控制消息本身没有消失。

## 4.16.4 SharedMemory：共享页加上能力句柄

`android.os.SharedMemory` 是 `Parcelable`。Android 17 Java 实现通过 native `ashmem_create_region()` 创建区域，映射时调用 `mmap(..., MAP_SHARED, ...)`。是否由 libcutils 在设备上使用 memfd 兼容实现，不应仅凭 Java 类名推断。

下面的示例用于传递一块写完后只读的数据。AIDL 接口可定义为 `void consume(in SharedMemory region, int validBytes)`：

```java
SharedMemory region = SharedMemory.create("agent-context", capacity);
ByteBuffer writable = region.mapReadWrite();
try {
    writable.put(payload);
} finally {
    SharedMemory.unmap(writable);
}

if (!region.setProtect(OsConstants.PROT_READ)) {
    region.close();
    throw new IllegalStateException("Failed to make shared region read-only");
}

try {
    remote.consume(region, payload.length);
} finally {
    region.close();
}
```

先解除发送方的可写 mapping，再调用 `setProtect(PROT_READ)`，可以让以后基于该区域创建的 mapping 只读。源码明确说明：`setProtect()` 只能移除权限，而且不改变已经存在的 mapping。若发送方保留旧的可写 mapping，就不能把这块区域称为不可变快照。

接收方读取后要分别释放 mapping 和 fd：

```java
ByteBuffer readable = region.mapReadOnly();
try {
    consumeBytes(readable, validBytes);
} finally {
    SharedMemory.unmap(readable);
    region.close();
}
```

`close()` 只关闭当前 `SharedMemory` 对象持有的 fd；已经打开的 mapping 保持有效。物理页要等所有 fd 关闭且所有 mapping 解除后才可释放。

### “零拷贝”要说明观察范围

把 `SharedMemory` 交给另一个进程可避免把整块 payload 序列化进 Binder，也避免接收端为了获得同一组页再复制一次。以下操作仍会产生复制或额外物理页：

- 发送方先把源数组写入共享区；
- 接收方又调用 `ByteBuffer.get(byte[])`；
- 推理 runtime 把数据重排到自己的 arena；
- 加速器驱动导入失败后创建私有 staging buffer；
- 任一可写私有映射触发 COW。

所以应把它表述为“可共享同一组页”，再用 PSS、page fault 和驱动统计验证端到端是否避免复制。

### fd 是能力，不代替身份校验

拿到有效 fd 的进程就能在该 fd 允许的保护范围内映射数据。发送前仍要校验 Binder 调用者、数据用途、长度和版本；发送后要限定句柄生命周期。敏感上下文还应考虑：

- 发送只读快照，不复用长期可写区域；
- 每次请求使用新的区域或带世代号的槽位；
- 不在共享区留下上一位用户或上一会话内容；
- 对长度、offset、格式和校验值做边界检查；
- 取消请求时关闭不再需要的 fd，并让双方解除 mapping。

## 4.16.5 HardwareBuffer：硬件互操作能力由契约决定

`HardwareBuffer` 是可 Parcelable 的硬件缓冲对象，格式与 usage flags 描述预期用途。它可以被 GPU、传感器、codec 或其他辅助处理单元访问，但这不等于任意 NPU 都能直接读取任意 `HardwareBuffer`。

使用前要同时确认：

1. producer 与 consumer 支持相同格式、尺寸、层数和 usage；
2. HAL/driver 能导入该 buffer；
3. 缓存一致性和 fence 同步由接口正确处理；
4. CPU 映射是否允许，以及是否引入额外 flush/invalidate；
5. consumer 是否会为布局、量化或对齐要求再分配一块内存。

图像帧已经位于 gralloc buffer 中，且推理服务明确接受同一格式的 `HardwareBuffer` 时，它通常比“读回 CPU byte[]、写进 Binder、服务端再上传”更合适。模型权重和通用文本上下文没有对应硬件导入协议时，`SharedMemory` 或只读文件 mapping 更简单。

不要把 `HardwareBuffer` 统一称为“GPU 显存”。许多 Android 设备使用统一物理内存，buffer 的分配 heap、缓存属性和硬件可见性由 gralloc 与驱动决定。

## 4.16.6 ContentProvider：共享数据，不暴露进程内存

`ContentProvider` 适合让目标 App 保留数据所有权，调用方按 URI、权限和查询条件读取。它提供的关键能力是访问控制和数据协议，而不是让 Agent 任意读取另一个 App 的地址空间。

结构化查询的 `CursorWindow` 初始为可写，写入 Parcel 后接收端得到只读视图。Android 17 的 native 实现先创建最多 16 KiB 的进程内区域，写入空间不足时才扩展为 ashmem 区域；构造参数 `windowSizeBytes` 是扩展后的上限。无参构造使用设备资源 `config_cursorWindowSize`，因此“默认永远是 2 MiB”不能作为接口约束。

处理大对象时：

- Cursor 只返回 id、类型、长度、版本和内容 URI；
- 用 `openFileDescriptor()` / `openAssetFileDescriptor()` 流式读取 blob；
- 通过 URI grant 限定接收方和有效期；
- 查询结果分页，避免单次构造过大的 Cursor 或 Bundle；
- 及时关闭 Cursor、ParcelFileDescriptor 和输入流。

这样可以把“小型索引”和“大型内容”分开，也能在 provider 侧执行撤销、审计和按用户隔离。

## 4.16.7 App Functions：受控函数调用，不是共享内存 API

`AppFunctionManager.executeAppFunction()` 和 `AppFunctionService` 从 Android 16 / API 36 开始提供。Android 17 / API 37 仍由 system_server 处理执行请求；permission-v2 路径的 AOSP 校验包括：

- 声明的调用包名必须与 Binder calling UID 匹配；
- permission-v2 开启时，普通调用方不能跨用户或从 secondary profile 发起执行；旧分支要求 `INTERACT_ACROSS_USERS_FULL`，两条路径还会检查 DevicePolicyManager 的 App Functions policy；
- 调用自身函数可以走同包规则，不要求跨包执行权限；
- 调用其他包时，普通调用方需要 `EXECUTE_APP_FUNCTIONS`，permission-v2 还要求 caller-target 组合命中 allowlist；持有 `EXECUTE_APP_FUNCTIONS_SYSTEM` 的系统调用方不受该 allowlist 限制；
- 目标 service 必须要求 `android.permission.BIND_APP_FUNCTION_SERVICE`，外部应用不能绕开 system_server 直接绑定。

目标 App 通过 `AppFunctionService.onExecuteFunction()` 接收请求。该回调在主线程触发，模型推理、磁盘读取和网络访问必须切换到 worker，再通过 callback 返回结果，并处理 `CancellationSignal`。Android 17 的 permission-v2 路径会把 `callingPackage` 置为空字符串，并把 `callingPackageSigningInfo` 置为 unknown；函数实现不能再用这两个参数鉴权。

请求中的 `GenericDocument`、`Bundle extras` 和响应对象都实现 Parcelable，仍受 Binder 事务空间约束。大图像、文档或音频应传受控 URI 或小型句柄描述；App Functions 负责“谁可以调用哪个函数”，大块数据仍走适合的内容接口。

Android 17 / API 37 新增了 `AppFunctionUriGrant` 和 `ExecuteAppFunctionResponse.getUriGrants()`。permission-v2 开启后，目标函数可以在响应中同时返回 URI 和对应授权。system_server 只处理 `content://` URI，接收者固定为本次请求的 calling package；目标函数只能选择 URI 以及 read、write、prefix、persistable mode。provider 还要允许 URI grant。临时授权通常持续到设备重启；persistable 标志只表示接收方可以调用 `takePersistableUriPermission()`，不会自动把授权持久化。要求更短生命周期时，仍需由 provider 设计一次性 URI、过期检查或主动撤销。

App Functions 也不会自动获得目标 App 的全部数据。目标函数只能读取目标 App 自己有权访问的内容，并由函数实现决定返回哪些字段。

## 4.16.8 模型推理内存要按阶段和后端计算

端侧生成式模型的常见内存可拆成：

```text
进程可见内存
  = 权重与常量
  + KV cache / recurrent state
  + 计算工作区
  + runtime、代码与普通业务对象
  + 输入输出缓冲
  + allocator 与驱动保留
```

其中任何一项都可能位于 Java heap、native heap、文件映射、共享内存或 dma-buf。只写“模型占 1.4 GB”无法说明内存压力来自何处。

### 权重大小：位宽只是理论下限

参数量为 `P`、平均权重位宽为 `q` 时，纯权重的理论下限是：

```text
weight_bytes = P × q / 8
```

2B 参数、4 bit 权重的理论值约为 1,000,000,000 bytes，即约 0.93 GiB。文件与运行时还可能包含量化 scale、zero point、张量 metadata、词表、对齐填充和重排后的权重副本，所以不能从“INT4”直接断言文件或 RSS 是 1.0 GiB、1.1 GiB 或 1.4 GiB。

若 runtime 对同一只读模型文件使用 `MAP_PRIVATE` 映射，未修改的驻留文件页可以通过 page cache 被多个进程共享。要满足这个结论，至少需要：

- 映射的是同一底层文件和相同页；
- 页保持只读，没有 COW；
- runtime 没有解压、反量化或重排到私有 buffer；
- 驱动没有为每个 session 复制一份设备侧权重。

### KV cache：用模型结构计算

标准注意力实现中，KV cache 的近似字节数为：

```text
kv_bytes
  = 2 × layers × kv_heads × head_dim
    × tokens × batch × bytes_per_element
```

前面的 `2` 代表 K 和 V。假设 26 层、4 个 KV head、每个 head 256 维、FP16、batch=1：

- 1024 token：约 104 MiB；
- 4096 token：约 416 MiB。

这只是示例。MHA、GQA、MQA 的 `kv_heads` 不同；分页 KV、滑动窗口、量化 KV、beam 数和多会话并发都会改变结果。评估具体模型时，应从模型配置和 runtime 分配日志代入参数，不应拿参数量或层数单独估算。

### 工作区：复用 buffer 不代表没有峰值

推理 runtime 往往预分配 arena 或复用计算 buffer，以减少频繁 `malloc/free`。峰值仍可能来自：

- 首次编译或 delegate 初始化；
- prompt prefill 的大临时张量；
- CPU 与加速器之间的 staging buffer；
- 动态 shape 触发 arena 重新规划；
- 多 session 同时执行；
- allocator 保留已经 free 的 span。

会话结束后 Java/native 对象已经不可达，也不保证 RSS 立刻下降。要区分“对象仍被引用”“allocator 留存”“干净文件页仍驻留”和“驱动仍持有 buffer”。

## 4.16.9 Android 17 MemoryLimiter 与 lmkd 的边界

### MemoryLimiter 的生产值由设备配置决定

Android 17 的 `MemoryLimiter.java` 包含一份 `sDefaultConfig`：visible 内存 4 GiB、notVisible 内存 2 GiB，两类 swap 都是 2 GiB。源码注释明确说它用于测试，不应未经复核用于生产。生产系统从：

```text
/vendor/etc/memory-limiter-config.xml
```

选择与设备总内存匹配的配置。功能还受 feature flag、配置文件存在性和设备内存条件控制，某台 Android 17 设备完全可能没有启用。

启用后，进程状态大致映射为：

| 类别 | Android 17 中的状态示例 | 限制来源 |
| --- | --- | --- |
| visible | TOP、BOUND_TOP、IMPORTANT_FOREGROUND、TOP_SLEEPING | vendor 配置的 visible memory/swap |
| notVisible | FOREGROUND_SERVICE、SERVICE、RECEIVER、HOME 等 | vendor 配置的 notVisible memory/swap |
| cached | 各类 cached state | `memory.high` 忽略，`memory.swap.max` 设为 `max` |
| persistent | PERSISTENT、PERSISTENT_UI | 两项均不限制 |

这里的 visible 是 MemoryLimiter 自己的分组，不能与窗口可见性或某个 App 组件名直接等同。

还有一个与端侧推理直接相关的例外：`initializeExemptList()` 会读取 `config_defaultOnDeviceSandboxedInferenceService`，把配置的 package 加入豁免列表。设备默认的 sandboxed inference service 因而可能不受该 limiter 管理。第三方 `:inference` 进程不会仅因名字含有 inference 就自动获得豁免。

`memory.high` 是 cgroup v2 的高水位控制，会让超限分配进入回收和节流压力；它不是“到值立即 OOM”的硬上限。Android 17 JNI 实际写入 `memory.swap.max`，它限制该 cgroup 可使用的 swap。具体延迟变化取决于页面类型、工作集、swap、存储与内核回收，不能从阈值推导固定的 P99 倍数。

### lmkd 仍以进程优先级和设备策略选受害者

Android 17 lmkd 从较高 `oom_score_adj` 向较低档位搜索满足最低阈值的进程。`kill_heaviest_task` 属性和进入 perceptible 档位等条件会影响是否在同档位选择内存最重的进程；否则可能按进程队列选择。

这带来三点结论：

1. 推理内存增加会提高系统压力，但不会给进程创建“AI 保护”。
2. 把推理拆到另一进程后，两个 PID 都要单独观察 procstate、adj 和内存。
3. 系统推理服务占用大量内存时，被杀的对象可能是其他更高 adj 进程；具体结果取决于当时进程集合和设备配置。

Android 17 lmkd 的 kill 日志还读取 RSS、匿名 RSS、swap、dma-buf PSS 和 dma-buf RSS。排查硬件推理时，不要只截取 Java heap 或匿名 RSS。

相关内核行为以 `android17-6.18-2026-06_r6` 为 kernel 锚点；Android 用户空间源码以 `android-17.0.0_r1` 为锚点。

## 4.16.10 一套可执行的测量方法

### 第一步：画出 PID、UID 与 fd 所有权

记录每个组件的：

- package、PID、UID 和 SELinux domain；
- AMS procstate、`oom_score_adj` 和绑定关系；
- 模型文件、SharedMemory、HardwareBuffer 的创建者与持有者；
- 会话结束后由谁关闭 fd、解除 mapping 和释放 session。

多进程问题若没有这张表，很容易把调用方内存、服务内存和共享页重复相加。

### 第二步：记录推理阶段

至少划分：

1. 进程启动；
2. runtime / delegate 初始化；
3. 模型打开与映射；
4. 首次 page fault 或预热；
5. prompt prefill；
6. token decode 与 KV 增长；
7. session 释放；
8. 进程退后台、冻结和解冻；
9. 进程退出。

每个阶段记录延迟、RSS、PSS、匿名内存、file mapping、swap 和 dma-buf。这样才能判断峰值来自权重驻留、KV cache、工作区还是驱动导入。

### 第三步：组合工具，不依赖单一数字

可用的设备侧命令包括：

```shell
adb shell dumpsys meminfo <package-or-pid>
adb shell dumpsys activity processes
adb shell cat /proc/<pid>/status
adb shell cat /proc/<pid>/smaps_rollup
adb shell cat /proc/<pid>/oom_score_adj
```

`/proc` 可见性受 user build、adb 权限和 SELinux 限制，读取失败不代表指标不存在。cgroup 路径也由设备配置决定，先从进程的 `/proc/<pid>/cgroup` 找归属，不要硬编码 `/dev/memcg/<uid>`。

Perfetto 中可启用：

- `linux.process_stats`：采样各进程计数；
- `linux.sys_stats`：观察系统内存与 VM 计数；
- `android.heapprofd`：采样 native allocator 分配；
- Binder、调度、page fault 和 lmkd 相关 ftrace/atrace 事件。

heapprofd 面向 native heap 分配，不能覆盖只读模型文件 mapping 的全部驻留页，也不能替代 dma-buf 和加速器驱动统计。Java heap 还要结合 ART heap dump、allocation sampling 或 `dumpsys meminfo`。

## 4.16.11 设计评审清单

### 进程与隔离

- 推理代码需要故障隔离、权限隔离，还是只需避免主进程 RSS 峰值？
- `:inference` 同 UID 是否满足威胁模型？
- isolated service 所需的文件、Binder service 和硬件节点是否都经过明确授权？
- 调用方死亡、service 被杀和设备冻结后，session 能否安全取消或重建？

### 数据传递

- Binder Parcel 是否稳定小于建议的 64 KiB？
- 大数据能否改为 SharedMemory、HardwareBuffer 或 URI？
- SharedMemory 发送前是否解除写 mapping 并降为只读？
- 谁负责 fd、mapping、fence 和 session 的最终释放？
- 接收方是否会再复制、解压或重排，导致所谓共享失去效果？

### 内存预算

- 权重计算是否包含量化 metadata 与运行时副本？
- KV cache 是否按 `kv_heads`、token、batch 和数据类型计算？
- prefill、decode 和多会话峰值是否分别测量？
- file、anon、swap、dma-buf 和驱动内存是否分开记录？
- MemoryLimiter 是否启用，生产 vendor 配置是什么，目标 package 是否被豁免？

### 安全

- 共享句柄发送前是否验证 Binder 调用身份与用户边界？
- URI grant、App Functions 权限和 allowlist 是否覆盖预期调用者？
- 共享区是否可能残留上一会话的敏感内容？
- 参数长度、offset、格式、版本和取消时序是否做了防御性校验？

## 4.16.12 源码索引

| 主题 | Android 17 / API 37 源码 |
| --- | --- |
| SharedMemory 映射、保护和关闭语义 | [`frameworks/base/core/java/android/os/SharedMemory.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/os/SharedMemory.java) |
| SharedMemory native 创建 | [`frameworks/base/core/jni/android_os_SharedMemory.cpp`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/jni/android_os_SharedMemory.cpp) |
| Binder 接收映射大小 | [`frameworks/native/libs/binder/ProcessState.cpp`](https://android.googlesource.com/platform/frameworks/native/+/android-17.0.0_r1/libs/binder/ProcessState.cpp) |
| Binder 推荐 IPC 大小 | [`frameworks/base/core/java/android/os/IBinder.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/os/IBinder.java) |
| 大事务失败语义 | [`frameworks/base/core/java/android/os/TransactionTooLargeException.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/os/TransactionTooLargeException.java) |
| HardwareBuffer 格式与 usage | [`frameworks/base/core/java/android/hardware/HardwareBuffer.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/hardware/HardwareBuffer.java) |
| CursorWindow 远端只读与动态分配 | [`frameworks/base/core/java/android/database/CursorWindow.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/database/CursorWindow.java)、[`frameworks/base/libs/androidfw/CursorWindow.cpp`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/libs/androidfw/CursorWindow.cpp) |
| App Functions service 保护 | [`frameworks/base/core/java/android/app/appfunctions/AppFunctionService.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/app/appfunctions/AppFunctionService.java) |
| App Functions API 版本与执行入口 | [`AppFunctionManager` API reference](https://developer.android.com/reference/android/app/appfunctions/AppFunctionManager)、[`AppFunctionService` API reference](https://developer.android.com/reference/android/app/appfunctions/AppFunctionService)、[`AppFunctionManager.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/app/appfunctions/AppFunctionManager.java) |
| 请求和响应 Parcelable 格式 | [`ExecuteAppFunctionRequest.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/app/appfunctions/ExecuteAppFunctionRequest.java)、[`ExecuteAppFunctionResponse.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/app/appfunctions/ExecuteAppFunctionResponse.java) |
| 调用资格校验 | [`frameworks/base/services/appfunctions/.../CallerValidatorImpl.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/services/appfunctions/java/com/android/server/appfunctions/CallerValidatorImpl.java) |
| Android 17 响应 URI grant | [`AppFunctionUriGrant` API reference](https://developer.android.com/reference/android/app/appfunctions/AppFunctionUriGrant)、[`AppFunctionUriGrant.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/app/appfunctions/AppFunctionUriGrant.java)、[`AppFunctionManagerServiceImpl.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/services/appfunctions/java/com/android/server/appfunctions/AppFunctionManagerServiceImpl.java) |
| MemoryLimiter 状态映射与推理服务豁免 | [`frameworks/base/services/core/java/com/android/server/am/MemoryLimiter.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/services/core/java/com/android/server/am/MemoryLimiter.java) |
| lmkd 受害者选择与 dma-buf 统计 | [`system/memory/lmkd/lmkd.cpp`](https://android.googlesource.com/platform/system/memory/lmkd/+/android-17.0.0_r1/lmkd.cpp) |
| isolated / isolated_compute 策略 | [`system/sepolicy/private/isolated_app.te`](https://android.googlesource.com/platform/system/sepolicy/+/android-17.0.0_r1/private/isolated_app.te)、[`isolated_compute_app.te`](https://android.googlesource.com/platform/system/sepolicy/+/android-17.0.0_r1/private/isolated_compute_app.te) |
| Binder buffer 分配 | [`kernel/common/drivers/android/binder_alloc.c`](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/drivers/android/binder_alloc.c)，`android17-6.18-2026-06_r6` |

## 4.16.13 小结

- Android 17 没有通用的 AI Agent 进程类别；先确认内存由哪个 PID、UID、cgroup 和驱动持有。
- `:inference` 提供地址空间与故障隔离，但通常仍是应用 UID；敏感代码需要评估 isolated service。
- Binder 的约 1 MiB 接收区由进程内并发事务共享，64 KiB 是平台建议的安全 IPC 大小。
- SharedMemory 通过 fd 共享同一组页；`setProtect()`、mapping 和 fd 必须分别管理。
- HardwareBuffer 能否避免复制取决于双方格式、usage、HAL 导入和同步协议。
- ContentProvider 与 App Functions 提供访问控制和业务协议，大块 payload 仍应使用 URI、fd 或共享缓冲。
- 权重、KV cache、工作区、file mapping、dma-buf 和驱动内存必须分开估算和测量。
- MemoryLimiter 的生产阈值来自 vendor XML；源码里的 4 GiB/2 GiB 内存阈值及 2 GiB/2 GiB swap 阈值只是测试配置。默认 sandboxed inference service 还可能被豁免。
- lmkd 不识别“AI”标签。进程状态、`oom_score_adj`、设备策略和当时内存集合共同决定结果。
