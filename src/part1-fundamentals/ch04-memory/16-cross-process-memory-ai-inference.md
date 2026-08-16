---
title: "跨进程内存共享与端侧推理预算"
chapter: "4.16"
status: ready-for-review
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
    path: "frameworks/native/libs/binder/Parcel.cpp (Binder 事务缓冲区)"
  - type: aosp
    path: "system/sepolicy/ — SELinux 隔离进程策略"
tags: [ai-agent, memory, sandbox, data-reuse, isolation, ml-runtime, sharedmemory]
related_chapters: ["4.3", "4.5", "4.13", "5.10", "5.11", "5.15", "16.11", "23.1", "23.10"]
---

# 4.16 跨进程内存共享与端侧推理预算

Android 17 / API 37 没有名为“AI Agent 进程”的内核对象，也没有为智能体（Agent）定义专用内存命名空间。模型推理、工具调用和跨应用协作仍受 Android 现有机制约束，包括应用身份 UID、进程地址空间、Binder、文件描述符（fd）、SELinux、第二版控制组 cgroup v2、ActivityManagerService（AMS）进程状态，以及低内存终止守护进程 lmkd。

看到某个产品使用 AICore、私有推理服务或厂商 NPU 服务时，不能把该产品的包名、进程优先级和缓存策略写成 AOSP Android 17 的通用行为。`com.google.android.aicore` 不属于 AOSP `android-17.0.0_r1`；它在具体设备上的生命周期和内存策略，应以该设备的实现为准。

平台层面可以确认以下结论：

- 内存计入分配、映射或导入它的进程与 cgroup；
- 同一物理页可以出现在多个进程的 RSS 中，PSS 才会按映射者分摊；
- Binder 适合传递控制消息和小数据，大块内容应通过 fd、共享缓冲区或受控 URI 传递；
- `android:process`、隔离服务（isolated service）和系统推理服务提供的隔离强度不同；
- Android 17 的 MemoryLimiter 与 lmkd 仍依据进程状态、设备配置和内存压力工作，没有通用的“正在执行 AI”进程标签；设备配置可以单独豁免默认的沙箱推理服务包。

## 4.16.1 先确定内存属于哪个进程

端侧推理常见四种部署方式：

| 方式 | UID / 进程 | 内存计入 | 隔离边界 |
| --- | --- | --- | --- |
| 应用进程内推理 | 应用 UID / 主进程 | 主进程的 Java 堆、原生内存、文件映射、dma-buf 等 | 无额外进程隔离 |
| `android:process=":inference"` | 通常仍是应用 UID / 独立进程 | 独立 PID 的各类内存 | 隔离地址空间和进程故障；不构成跨 UID 安全沙箱 |
| `android:isolatedProcess="true"` 服务 | 系统分配的隔离 UID / 独立进程 | 隔离进程 | 权限和数据访问明显收窄，只能通过获准的进程间通信（IPC）与句柄取得数据 |
| 系统或厂商推理服务 | 服务自己的 UID / 进程 | 服务进程及其 cgroup | 由系统映像、SELinux 和服务协议决定 |

### 独立进程不会自动继承固定的 `oom_score_adj`

AMS 会根据组件状态、绑定关系和前台可感知性等信息，持续计算进程状态和 `oom_score_adj`。这个分值越高，进程通常越容易在内存紧张时被选中终止。同一应用的主进程和 `:inference` 进程可以得到不同分值；前台组件绑定的服务也可能因依赖关系而提高优先级。

因此，不能把“推理服务”固定写成 `oom_score_adj=500～800`，也不能假设系统推理服务永远比调用方更难被终止。应在目标设备和目标场景中读取以下信息：

```shell
adb shell dumpsys activity processes
adb shell cat /proc/<pid>/oom_score_adj
```

第一条命令用于观察 AMS 认定的进程状态和依赖关系，第二条用于确认该时刻写入内核的分值。测量需要覆盖前台、转入后台、解绑、冻结和重新绑定等状态变化。

进程的内存变大不会直接调高它的 `oom_score_adj`。内存大小会影响系统终止该进程后能够释放多少内存，也可能影响同一 `adj` 档位内的选择；进程重要性仍由 AMS 的状态模型决定。

### `android:process` 提供故障隔离，不保证数据保密

以冒号开头的私有进程名通常让组件运行在应用自己的另一个 Linux 进程中，但仍使用应用 UID。它适合：

- 把原生推理引擎的崩溃限制在单独的 PID；
- 让主界面与推理进程分别观测内存；
- 在组件不再使用时终止推理进程，回收其整个地址空间。

它不适合充当“不可信模型代码”的保密沙箱。使用相同应用身份的进程能够访问该应用已经获准的数据和能力；具体范围还受 SELinux、文件权限模式和组件实现影响。

### 隔离服务所需的能力要显式传入

Manifest 可以声明：

```xml
<service
    android:name=".InferenceService"
    android:isolatedProcess="true"
    android:exported="false" />
```

`attrs_manifest.xml` 把隔离进程（isolated process）定义为“运行在与系统其余部分隔离的特殊进程”，通信入口是服务的启动与绑定 API。这个进程不以宿主应用的 UID 运行，也不能假设它拥有宿主的运行时权限、私有文件访问权或任意系统服务访问能力。

宿主应通过受约束的 Binder 接口，只传入完成一次请求所需的 fd、只读共享区和最少元数据。需要 GPU、编解码器或其他硬件服务时，还要确认设备为相应的隔离安全域（isolated domain）配置了哪些服务和设备权限。AOSP 的 `isolated_compute_app` 有单独的 SELinux 规则，普通 `isolated_app` 不会因此获得相同能力。

## 4.16.2 RSS、PSS 与共享页怎样记账

跨进程复用常见的误判是：“两个进程都显示 400 MiB RSS，所以系统用了 800 MiB。”RSS（Resident Set Size，驻留集大小）会把每个进程页表中当前驻留的共享页完整计入该进程，直接相加会重复。PSS（Proportional Set Size）则按映射者数量分摊共享页。

对一页被 `N` 个进程映射的物理页，可用下面的简化关系理解 PSS：

```text
每个映射进程的 PSS 贡献 ≈ 页大小 / N
所有映射进程的 PSS 贡献之和 ≈ 页大小
```

这个简化关系只适用于当时已经驻留，并且由这些进程共同映射的页面。如果某个进程尚未因首次访问而调入页面（fault-in）、已经解除映射，或私有写入触发写时复制（Copy-on-Write，COW），`N` 和对应的物理页集合都会变化。

| 内存来源 | RSS 表现 | PSS / 共享语义 | 常见遗漏 |
| --- | --- | --- | --- |
| Java 堆、匿名原生堆 | 通常只计入一个进程 | 主要计入该进程 | 分配器缓存可能让 `free()` 后的 RSS 不会立即下降 |
| 只读文件 `mmap` | 每个进程计入驻留页 | 同一文件页可通过页缓存（page cache）分摊 | 解压、重排或写时复制会新增私有页 |
| `SharedMemory` | 每个映射者计入驻留共享页 | PSS 按映射者分摊 | fd 已关闭时，已有映射仍可存活 |
| `HardwareBuffer` / dma-buf | 可能无法完整归入普通匿名/文件分类 | 由导入者、驱动和统计接口决定 | CPU、GPU、显示系统和 NPU 可同时持有引用 |
| 加速器私有内存 | 依赖驱动 | 未必能归入调用进程的常规 PSS | 驱动复制、常驻缓存和固件内存 |

分析模型内存时，至少要分别记录 Java 堆、原生堆、文件映射、共享内存/dma-buf、交换空间和驱动侧内存。只看 `Debug.MemoryInfo.getTotalPss()`，无法解释每一类内存的生命周期。

## 4.16.3 IPC 先传控制信息，再传大块数据

Android 17 的原生 Binder 库 libbinder 会在 `ProcessState.cpp` 中按下面的大小建立接收端映射：

```cpp
#define BINDER_VM_SIZE ((1 * 1024 * 1024) - sysconf(_SC_PAGE_SIZE) * 2)
```

这是进程内所有 Binder 线程共享的接收缓冲区，多个正在进行的事务会共同使用它，不能理解成“每个 Binder 线程各有 1 MiB”。请求、返回值、对象偏移表和并发事务都会占用这块空间。

`TransactionTooLargeException` 的 Java 文档也强调，它只是大事务失败时的启发式异常。调用方无法可靠判断请求是否未送达，也可能是服务端已经处理请求、但返回值发送失败。因此，接口要按“操作可能已经部分完成”设计幂等性，也就是同一请求重复执行时不应产生额外副作用。

公开 API `IBinder.getSuggestedMaxIpcSizeBytes()` 返回 64 KiB；它引用的 `MAX_IPC_SIZE` 常量在源码中带有 `@hide`，应用不能直接访问。64 KiB 是让事务安全低于接收缓冲区上限的建议值，并非驱动的硬上限。可以按下面的分工选择传输通道：

| 内容 | 优先方式 | 原因 |
| --- | --- | --- |
| 命令、令牌、状态、小型结构体 | AIDL / Parcelable | 边界清楚，便于校验权限与版本 |
| 一次性大块字节数据 | `SharedMemory` + Binder fd | 数据载荷不占用大块 Binder 缓冲区 |
| 图像、视频帧、硬件可导入张量（tensor） | `HardwareBuffer` | 允许硬件组件共享同一个缓冲对象 |
| 持久内容或可分页记录 | `ContentProvider` + URI / fd | 有权限、生命周期和查询语义 |
| 跨应用受控动作 | App Functions | `system_server` 校验调用资格，目标应用执行业务逻辑 |

“通过 Binder 传 fd”仍会发送一个小型 Parcel。真正共享的是 fd 指向的对象，控制消息本身仍然存在。

## 4.16.4 SharedMemory：共享页加上能力句柄

`android.os.SharedMemory` 实现了 `Parcelable`，因此可以通过 Binder 传递对应句柄。Android 17 的 Java 实现通过原生函数 `ashmem_create_region()` 创建区域，映射时调用 `mmap(..., MAP_SHARED, ...)`。设备上的 libcutils 是否改用 memfd 兼容实现，不能只根据 Java 类名推断。

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

先解除发送方的可写映射，再调用 `setProtect(PROT_READ)`，可以让以后基于该区域创建的映射只读。源码明确说明，`setProtect()` 只能移除权限，而且不会改变已经存在的映射。如果发送方保留旧的可写映射，这块区域就不能称为不可变快照。

接收方读取完成后，要分别解除映射并关闭 fd：

```java
ByteBuffer readable = region.mapReadOnly();
try {
    consumeBytes(readable, validBytes);
} finally {
    SharedMemory.unmap(readable);
    region.close();
}
```

`close()` 只关闭当前 `SharedMemory` 对象持有的 fd；已经建立的映射仍然有效。只有等所有 fd 都已关闭、所有映射都已解除，相关物理页才具备释放条件。

### “零拷贝”要说明观察范围

把 `SharedMemory` 交给另一个进程，可以避免把整块数据序列化进 Binder，也不需要接收端为获得同一组页面再复制一次。以下操作仍会产生复制或额外物理页：

- 发送方先把源数组写入共享区；
- 接收方又调用 `ByteBuffer.get(byte[])`；
- 推理运行时把数据重排到自己的内存区（arena）；
- 加速器驱动导入失败后创建私有暂存缓冲区（staging buffer）；
- 任一可写私有映射触发 COW。

所以，更准确的说法是“两个进程可以共享同一组页面”。还要结合 PSS、缺页（page fault）和驱动统计，验证从输入到推理后端的完整路径是否真的避免了复制。

### fd 代表访问能力，不能代替身份校验

拿到有效 fd 的进程，就获得了在该 fd 保护范围内映射数据的能力。发送前仍要校验 Binder 调用者身份、数据用途、长度和版本；发送后还要限定句柄生命周期。处理敏感上下文时，还应考虑：

- 发送只读快照，不复用长期可写区域；
- 每次请求使用新的区域，或使用带世代编号的槽位；
- 不在共享区留下上一位用户或上一会话内容；
- 对长度、偏移量（offset）、格式和校验值做边界检查；
- 取消请求时关闭不再需要的 fd，并让双方解除映射。

## 4.16.5 HardwareBuffer：硬件互操作能力由契约决定

`HardwareBuffer` 是可以通过 Parcelable 传递的硬件缓冲对象，其格式与用途标志（usage flags）共同描述预期用法。GPU、传感器、编解码器或其他辅助处理单元可以访问它，但这不表示任意神经网络处理器（NPU）都能直接读取任意 `HardwareBuffer`。

使用前要同时确认：

1. 生产者（producer）与消费者（consumer）支持相同的格式、尺寸、层数和用途；
2. 硬件抽象层（HAL）或驱动能够导入该缓冲区；
3. 接口能够正确处理缓存一致性和同步栅栏（fence）；
4. 是否允许 CPU 映射，以及映射是否引入额外的缓存刷新/失效操作（flush/invalidate）；
5. 消费者是否会因布局、量化或对齐要求，再分配一块内存。

如果图像帧已经位于 gralloc 图形缓冲区中，而且推理服务明确接受同一格式的 `HardwareBuffer`，那么它通常比“读回 CPU 字节数组、写进 Binder、服务端再上传”更合适。模型权重和通用文本上下文没有相应的硬件导入协议时，`SharedMemory` 或只读文件映射更简单。

不要把 `HardwareBuffer` 统一称为“GPU 显存”。许多 Android 设备使用统一物理内存；缓冲区来自哪个分配堆、具有何种缓存属性、哪些硬件可以访问，都由 gralloc 与驱动决定。

## 4.16.6 ContentProvider：共享数据，不暴露进程内存

`ContentProvider` 适合让目标应用保留数据所有权，调用方按 URI、权限和查询条件读取。它提供的是访问控制与数据协议，不会让智能体任意读取另一个应用的地址空间。

结构化查询使用的 `CursorWindow` 初始可写；写入 Parcel 后，接收端得到只读视图。Android 17 的原生实现会先创建最多 16 KiB 的进程内区域，写入空间不足时才扩展为 ashmem 共享内存区域；构造参数 `windowSizeBytes` 是扩展后的上限。无参构造使用设备资源 `config_cursorWindowSize`，因此，“默认永远是 2 MiB”不能作为接口约束。

处理大对象时：

- Cursor 只返回 id、类型、长度、版本和内容 URI；
- 用 `openFileDescriptor()` / `openAssetFileDescriptor()` 流式读取二进制大对象（blob）；
- 通过 URI 授权（URI grant）限定接收方和有效期；
- 对查询结果分页，避免单次构造过大的 Cursor 或 Bundle；
- 及时关闭 Cursor、`ParcelFileDescriptor` 和输入流。

这样可以把“小型索引”和“大型内容”分开，也能在 ContentProvider 一侧执行撤销、审计和按用户隔离。

## 4.16.7 App Functions：受控函数调用，不是共享内存 API

`AppFunctionManager.executeAppFunction()` 和 `AppFunctionService` 从 Android 16 / API 36 开始提供，用于受控地调用另一个应用公开的函数。Android 17 / API 37 仍由 `system_server` 处理执行请求；v2 权限流程（permission-v2）的 AOSP 校验包括：

- 声明的调用包名必须与 Binder 记录的调用方 UID 匹配；
- permission-v2 开启时，普通调用方不能跨用户，也不能从次要用户配置文件（secondary profile）发起执行；旧分支要求 `INTERACT_ACROSS_USERS_FULL`，两条路径还会检查 DevicePolicyManager 的 App Functions 策略；
- 调用自身函数可以走同包规则，不要求跨包执行权限；
- 调用其他包时，普通调用方需要 `EXECUTE_APP_FUNCTIONS`；permission-v2 还要求“调用方—目标”组合命中允许列表（allowlist）。持有 `EXECUTE_APP_FUNCTIONS_SYSTEM` 的系统调用方不受该列表限制；
- 目标服务必须要求 `android.permission.BIND_APP_FUNCTION_SERVICE`，外部应用不能绕过 `system_server` 直接绑定。

目标应用通过 `AppFunctionService.onExecuteFunction()` 接收请求。该回调在主线程触发，模型推理、磁盘读取和网络访问必须切换到后台工作线程，再通过回调返回结果，并处理取消信号 `CancellationSignal`。Android 17 的 permission-v2 路径会把 `callingPackage` 置为空字符串，并把 `callingPackageSigningInfo` 置为 unknown；函数实现不能再使用这两个参数鉴权。

请求中的 `GenericDocument`、`Bundle extras` 和响应对象都实现了 Parcelable，仍受 Binder 事务空间限制。大图像、文档或音频应传递受控 URI 或小型句柄描述；App Functions 负责判断“谁可以调用哪个函数”，大块数据仍应使用合适的内容接口。

Android 17 / API 37 新增了 `AppFunctionUriGrant` 和 `ExecuteAppFunctionResponse.getUriGrants()`。permission-v2 开启后，目标函数可以在响应中同时返回 URI 和对应授权。`system_server` 只处理 `content://` URI，接收者固定为本次请求的调用包；目标函数只能选择 URI，以及读、写、前缀匹配和可持久化等授权模式。ContentProvider 还必须允许 URI 授权。临时授权通常持续到设备重启；可持久化标志只表示接收方可以调用 `takePersistableUriPermission()`，不会自动把授权持久化。需要更短生命周期时，仍要由 ContentProvider 设计一次性 URI、过期检查或主动撤销。

App Functions 也不会自动获得目标应用的全部数据。目标函数只能读取目标应用自己有权访问的内容，并由函数实现决定返回哪些字段。

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

其中任何一项都可能位于 Java 堆、原生堆、文件映射、共享内存或 dma-buf。只写“模型占 1.4 GB”，无法说明内存压力究竟来自哪里。

### 权重大小：位宽只是理论下限

参数量为 `P`、平均权重位宽为 `q` 时，纯权重的理论下限是：

```text
weight_bytes = P × q / 8
```

2B（20 亿）参数、4 位权重的理论值约为 1,000,000,000 字节，即约 0.93 GiB。文件与运行时还可能包含量化比例因子（scale）、零点（zero point）、张量元数据、词表、对齐填充和重排后的权重副本，所以不能只根据“INT4（4 位整数权重）”就断言文件或 RSS 是 1.0 GiB、1.1 GiB 或 1.4 GiB。

如果推理运行时对同一只读模型文件使用 `MAP_PRIVATE` 映射，未修改的驻留文件页可以通过页缓存被多个进程共享。要满足这个结论，至少需要：

- 映射的是同一底层文件和相同页；
- 页保持只读，没有 COW；
- 推理运行时没有把权重解压、反量化或重排到私有缓冲区；
- 驱动没有为每个会话（session）复制一份设备侧权重。

### KV 缓存：用模型结构计算

KV 缓存保存注意力机制已经计算过的 Key/Value 状态，避免生成每个新 token（模型处理的文本单位）时重复计算全部历史。标准注意力实现中，KV 缓存的近似字节数为：

```text
kv_bytes
  = 2 × layers × kv_heads × head_dim
    × tokens × batch × bytes_per_element
```

前面的 `2` 代表 K 和 V。假设模型有 26 层、4 个 KV 头（head）、每个头 256 维、采用 16 位浮点数 FP16，且批大小 `batch=1`：

- 1024 个 token：约 104 MiB；
- 4096 个 token：约 416 MiB。

这只是示例。MHA、GQA、MQA 对 KV 头的共享方式不同：MHA 为各注意力头保留独立 KV，GQA 让一组查询头共享 KV，MQA 则让所有查询头共享 KV。分页 KV、滑动窗口、量化 KV、候选序列数（beam）和多会话并发也会改变结果。评估具体模型时，应从模型配置和推理运行时分配日志中取得参数，不能只用参数量或层数估算。

### 工作区：复用缓冲区不代表没有峰值

推理运行时往往预先分配内存区，或复用计算缓冲区，以减少频繁调用 `malloc/free`。峰值仍可能来自：

- 首次编译或硬件后端委托器（delegate）初始化；
- 提示词预填充阶段（prompt prefill）使用的大型临时张量；
- CPU 与加速器之间的暂存缓冲区；
- 动态形状（dynamic shape）触发内存区重新规划；
- 多个会话同时执行；
- 分配器保留已经释放的内存块（span）。

会话结束后，即使 Java/原生对象已经不可达，也不能保证 RSS 立刻下降。需要区分“对象仍被引用”“分配器留存”“干净文件页仍驻留”和“驱动仍持有缓冲区”这几种情况。

## 4.16.9 Android 17 MemoryLimiter 与 lmkd 的边界

### MemoryLimiter 的生产值由设备配置决定

Android 17 的 `MemoryLimiter.java` 包含一份 `sDefaultConfig`：可见组（visible）内存为 4 GiB，不可见组（notVisible）内存为 2 GiB，两组的交换空间都是 2 GiB。源码注释明确说明这份配置用于测试，不能未经复核就用于生产。生产系统从下面的文件读取配置：

```text
/vendor/etc/memory-limiter-config.xml
```

系统会从中选择与设备总内存匹配的配置。该功能还受功能开关（feature flag）、配置文件是否存在和设备内存条件控制，因此某台 Android 17 设备完全可能没有启用 MemoryLimiter。

启用后，进程状态大致映射为：

| 类别 | Android 17 中的状态示例 | 限制来源 |
| --- | --- | --- |
| 可见（visible） | TOP、BOUND_TOP、IMPORTANT_FOREGROUND、TOP_SLEEPING | 厂商配置的可见组内存/交换空间 |
| 不可见（notVisible） | FOREGROUND_SERVICE、SERVICE、RECEIVER、HOME 等 | 厂商配置的不可见组内存/交换空间 |
| 缓存（cached） | 各类缓存状态 | 忽略 `memory.high`，把 `memory.swap.max` 设为 `max` |
| 常驻（persistent） | PERSISTENT、PERSISTENT_UI | 两项均不限制 |

这里的 visible 是 MemoryLimiter 自己的分组，不能直接等同于窗口可见性或某个应用组件名称。

还有一个与端侧推理直接相关的例外：`initializeExemptList()` 会读取 `config_defaultOnDeviceSandboxedInferenceService`，把配置的包加入豁免列表。因此，设备默认的沙箱推理服务可能不受 MemoryLimiter 管理。第三方 `:inference` 进程不会仅因名称含有 `inference` 就自动获得豁免。

`memory.high` 是 cgroup v2 的内存软边界，超过后会增加内存回收和执行节流压力；它不是“到值立即发生内存耗尽（OOM）”的硬上限。Android 17 的 JNI 实际写入 `memory.swap.max`，用于限制该 cgroup 可使用的交换空间。具体延迟变化取决于页面类型、工作集、交换空间、存储和内核回收，不能根据阈值推导固定的 P99（第 99 百分位）延迟倍数。

### lmkd 仍按进程优先级和设备策略选择终止目标

Android 17 的 lmkd 从较高 `oom_score_adj` 向较低档位搜索满足最低阈值的进程。`kill_heaviest_task` 属性以及是否进入用户可感知（perceptible）档位等条件，会影响系统是否在同一档位选择内存占用最大的进程；否则，系统可能按进程队列选择。

这带来三点结论：

1. 推理内存增加会提高系统压力，但不会给进程创建“AI 保护”。
2. 把推理拆到另一个进程后，两个 PID 的进程状态、`adj` 和内存都要分别观察。
3. 系统推理服务占用大量内存时，被终止的可能是其他 `adj` 更高的进程；具体结果取决于当时的进程集合和设备配置。

Android 17 的 lmkd 终止日志还会读取 RSS、匿名 RSS、交换空间、dma-buf PSS 和 dma-buf RSS。排查硬件推理时，不能只截取 Java 堆或匿名 RSS。

相关内核行为以 `android17-6.18-2026-06_r6` 为 Linux 内核锚点；Android 用户空间源码以 `android-17.0.0_r1` 为锚点。

## 4.16.10 一套可执行的测量方法

### 第一步：画出 PID、UID 与 fd 所有权

记录每个组件的：

- 包名、PID、UID 和 SELinux 安全域；
- AMS 进程状态、`oom_score_adj` 和绑定关系；
- 模型文件、SharedMemory、HardwareBuffer 的创建者与持有者；
- 会话结束后由谁关闭 fd、解除映射并释放会话。

多进程问题若没有这张表，很容易把调用方内存、服务内存和共享页重复相加。

### 第二步：记录推理阶段

至少划分：

1. 进程启动；
2. 推理运行时与硬件后端委托器初始化；
3. 模型打开与映射；
4. 首次缺页或预热；
5. 提示词预填充；
6. 逐 token 解码与 KV 缓存增长；
7. 会话释放；
8. 进程退后台、冻结和解冻；
9. 进程退出。

每个阶段都要记录延迟、RSS、PSS、匿名内存、文件映射、交换空间和 dma-buf。这样才能判断峰值来自权重驻留、KV 缓存、工作区还是驱动导入。

### 第三步：组合工具，不依赖单一数字

可用的设备侧命令包括：

```shell
adb shell dumpsys meminfo <package-or-pid>
adb shell dumpsys activity processes
adb shell cat /proc/<pid>/status
adb shell cat /proc/<pid>/smaps_rollup
adb shell cat /proc/<pid>/oom_score_adj
```

`/proc` 的可见性受用户版本（user build）、adb 权限和 SELinux 限制，读取失败不表示指标不存在。cgroup 路径也由设备配置决定，应先从进程的 `/proc/<pid>/cgroup` 查找归属，不能硬编码 `/dev/memcg/<uid>`。

Perfetto 中可启用：

- `linux.process_stats`：采样各进程的统计值；
- `linux.sys_stats`：观察系统内存与虚拟内存计数；
- `android.heapprofd`：采样原生内存分配器的分配记录；
- Binder、线程调度、缺页和 lmkd 相关的 ftrace/atrace 跟踪事件。

heapprofd 面向原生堆分配，不能覆盖只读模型文件映射的全部驻留页，也不能替代 dma-buf 和加速器驱动统计。Java 堆还要结合 ART 堆转储、内存分配采样或 `dumpsys meminfo` 分析。

## 4.16.11 设计评审清单

### 进程与隔离

- 推理代码需要故障隔离、权限隔离，还是只需要避免主进程出现 RSS 峰值？
- `:inference` 同 UID 是否满足威胁模型？
- 隔离服务所需的文件、Binder 服务和硬件节点是否都经过明确授权？
- 调用方退出、服务被终止或进程被冻结后，会话能否安全取消或重建？

### 数据传递

- Binder Parcel 是否能稳定保持在建议的 64 KiB 以下？
- 大数据能否改为 SharedMemory、HardwareBuffer 或 URI？
- SharedMemory 发送前是否已经解除可写映射并降为只读？
- 谁负责 fd、映射、同步栅栏和会话的最终释放？
- 接收方是否会再复制、解压或重排，导致所谓共享失去效果？

### 内存预算

- 权重计算是否包含量化元数据与运行时副本？
- KV 缓存是否按 `kv_heads`、token、批大小和数据类型计算？
- 预填充、逐 token 解码和多会话峰值是否分别测量？
- 文件页、匿名页、交换空间、dma-buf 和驱动内存是否分开记录？
- MemoryLimiter 是否启用，生产设备的厂商配置是什么，目标包是否被豁免？

### 安全

- 共享句柄发送前是否验证 Binder 调用身份与用户边界？
- URI 授权、App Functions 权限和允许列表是否覆盖预期调用者？
- 共享区是否可能残留上一会话的敏感内容？
- 参数长度、偏移量、格式、版本和取消时序是否做了防御性校验？

## 4.16.12 源码索引

| 主题 | Android 17 / API 37 源码 |
| --- | --- |
| SharedMemory 映射、保护和关闭语义 | [`frameworks/base/core/java/android/os/SharedMemory.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/os/SharedMemory.java) |
| SharedMemory 原生层创建 | [`frameworks/base/core/jni/android_os_SharedMemory.cpp`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/jni/android_os_SharedMemory.cpp) |
| Binder 接收映射大小 | [`frameworks/native/libs/binder/ProcessState.cpp`](https://android.googlesource.com/platform/frameworks/native/+/android-17.0.0_r1/libs/binder/ProcessState.cpp) |
| Binder 推荐 IPC 大小 | [`frameworks/base/core/java/android/os/IBinder.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/os/IBinder.java) |
| 大事务失败语义 | [`frameworks/base/core/java/android/os/TransactionTooLargeException.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/os/TransactionTooLargeException.java) |
| HardwareBuffer 格式与用途 | [`frameworks/base/core/java/android/hardware/HardwareBuffer.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/hardware/HardwareBuffer.java) |
| CursorWindow 远端只读与动态分配 | [`frameworks/base/core/java/android/database/CursorWindow.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/database/CursorWindow.java)、[`frameworks/base/libs/androidfw/CursorWindow.cpp`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/libs/androidfw/CursorWindow.cpp) |
| App Functions 服务保护 | [`frameworks/base/core/java/android/app/appfunctions/AppFunctionService.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/app/appfunctions/AppFunctionService.java) |
| App Functions API 版本与执行入口 | [`AppFunctionManager` API reference](https://developer.android.com/reference/android/app/appfunctions/AppFunctionManager)、[`AppFunctionService` API reference](https://developer.android.com/reference/android/app/appfunctions/AppFunctionService)、[`AppFunctionManager.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/app/appfunctions/AppFunctionManager.java) |
| 请求和响应 Parcelable 格式 | [`ExecuteAppFunctionRequest.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/app/appfunctions/ExecuteAppFunctionRequest.java)、[`ExecuteAppFunctionResponse.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/app/appfunctions/ExecuteAppFunctionResponse.java) |
| 调用资格校验 | [`frameworks/base/services/appfunctions/.../CallerValidatorImpl.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/services/appfunctions/java/com/android/server/appfunctions/CallerValidatorImpl.java) |
| Android 17 响应 URI 授权 | [`AppFunctionUriGrant` API reference](https://developer.android.com/reference/android/app/appfunctions/AppFunctionUriGrant)、[`AppFunctionUriGrant.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/app/appfunctions/AppFunctionUriGrant.java)、[`AppFunctionManagerServiceImpl.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/services/appfunctions/java/com/android/server/appfunctions/AppFunctionManagerServiceImpl.java) |
| MemoryLimiter 状态映射与推理服务豁免 | [`frameworks/base/services/core/java/com/android/server/am/MemoryLimiter.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/services/core/java/com/android/server/am/MemoryLimiter.java) |
| lmkd 终止目标选择与 dma-buf 统计 | [`system/memory/lmkd/lmkd.cpp`](https://android.googlesource.com/platform/system/memory/lmkd/+/android-17.0.0_r1/lmkd.cpp) |
| 隔离进程 / 隔离计算进程策略 | [`system/sepolicy/private/isolated_app.te`](https://android.googlesource.com/platform/system/sepolicy/+/android-17.0.0_r1/private/isolated_app.te)、[`isolated_compute_app.te`](https://android.googlesource.com/platform/system/sepolicy/+/android-17.0.0_r1/private/isolated_compute_app.te) |
| Binder 缓冲区分配 | [`kernel/common/drivers/android/binder_alloc.c`](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/drivers/android/binder_alloc.c)，`android17-6.18-2026-06_r6` |

## 4.16.13 小结

- Android 17 没有通用的 AI Agent 进程类别；应先确认内存由哪个 PID、UID、cgroup 和驱动持有。
- `:inference` 提供地址空间与故障隔离，但通常仍使用应用 UID；敏感代码需要评估隔离服务。
- Binder 的约 1 MiB 接收区由进程内并发事务共享，64 KiB 是平台建议的安全 IPC 大小。
- SharedMemory 通过 fd 共享同一组页面；`setProtect()`、映射和 fd 必须分别管理。
- HardwareBuffer 能否避免复制，取决于双方格式、用途、HAL 导入和同步协议。
- ContentProvider 与 App Functions 提供访问控制和业务协议，大块数据仍应使用 URI、fd 或共享缓冲区。
- 权重、KV 缓存、工作区、文件映射、dma-buf 和驱动内存必须分开估算与测量。
- MemoryLimiter 的生产阈值来自厂商 XML；源码里的 4 GiB/2 GiB 内存阈值及 2 GiB/2 GiB 交换空间阈值只是测试配置。默认沙箱推理服务还可能被豁免。
- lmkd 不识别“AI”标签。进程状态、`oom_score_adj`、设备策略、当时的进程集合与内存压力共同决定结果。
