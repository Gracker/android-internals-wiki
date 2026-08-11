---
title: "Binder IPC 故障与性能监控"
chapter: "20.15"
status: ready-for-review
applicable_versions: "Android 12 (API 31) - Android 17 (API 37)"
tags: [binder, ipc, exception, transaction-too-large, dead-object, stability, performance]
related_chapters: ["1.4", "1.17", "1.18", "20.4", "26.9"]
consolidated_from:
  - "src/part5-app/ch20-stability/22-binder-communication-monitoring.md"
created_by: "task2a-knowledge-gap"
created_date: "2026-06-04"
drafted_date: "2026-06-04"
last_verified: "2026-06-04"
last_verified_against: "AOSP android-17.0.0_r1 / android-16.0.0_r1"
confidence: medium
gap_source: "素材驱动+Clippings参考书"
gap_score: 15
gap_score_detail: "素材丰富度 4 | 相关性 4 | 读者需求度 4 | 时效性 3"
sources:
  - type: aosp
    path: "frameworks/native/libs/binder/ProcessState.cpp"
  - type: aosp
    path: "frameworks/base/core/java/android/os/Binder.java"
  - type: aosp
    path: "frameworks/base/core/java/android/os/RemoteException.java"
  - type: aosp
    path: "frameworks/base/core/java/android/os/DeadObjectException.java"
  - type: aosp
    path: "frameworks/base/core/java/android/os/TransactionTooLargeException.java"
  - type: aosp
    path: "frameworks/base/core/java/android/os/ServiceSpecificException.java"
  - type: aosp
    path: "kernel/common/drivers/android/binder.c"
  - type: official
    path: "developer.android.com/reference/android/os/RemoteException"
  - type: official
    path: "developer.android.com/reference/android/os/TransactionTooLargeException"
  - type: official
    path: "source.android.com/docs/core/architecture/ipc/binder-freezer"
  - type: blog
    path: "DeepResearch/2026-05-08-binder-freezer-driver-cgroup-v2-coordination-mechanism.md"
  - type: research
    path: "intake/research-feeds/2026-04-01-07-ch09-binder-anr-android15-16-17.md"
  - type: research
    path: "intake/research-feeds/2026-04-05-07-cursorwindow-binder-performance.md"
  - type: structure-reference
    path: "Clippings/Android 应用稳定性剖析与优化 - Binder 异常：原来 Binder 异常真不少！.md"
---

# Binder IPC 故障与性能监控

Binder 是 Android 本机跨进程通信的核心机制，但不是应用之间唯一的数据通道：socket、pipe、共享内存和文件描述符同样存在。Binder 的优势是对象引用、身份传递、线程调度和 AIDL 契约都由系统协同完成；代价是一次看似普通的方法调用，可能同时受 Parcel 大小、目标进程存活、线程池、冻结状态和远端异常影响。

稳定性治理的第一条规则是：**把传输是否完成、服务端是否执行、业务是否成功分开记录。** `RemoteException` 只说明 IPC 边界出现问题，不能直接证明服务端没有执行；`oneway` 调用返回也不能证明目标已经处理。

平台源码锚点为 `android-17.0.0_r1`，Binder 驱动锚点为 `android17-6.18-2026-06_r6`。

## 1. 一次同步 Binder 调用有四个失败位置

| 阶段 | 可能失败 | 调用方能看到什么 | 能否断言服务端未执行 |
|---|---|---|---:|
| 请求序列化 | Parcelable 格式错误、对象图过大、FD 无效 | 本地运行时异常或 `RemoteException` 子类 | 多数情况下可以，但要看异常发生点 |
| 驱动投递 | 目标死亡、buffer 分配失败、目标被冻结 | `DeadObjectException`、`TransactionTooLargeException` 或其他传输失败 | 不能只靠异常类判断 |
| 服务端执行 | 权限拒绝、参数错误、业务错误、线程池阻塞 | reply 中编码的异常、超时/ANR、业务状态 | 已经进入服务端 |
| 回复序列化与返回 | 返回值过大、服务端在执行后死亡、客户端 buffer 紧张 | 传输异常；请求侧与回复侧难以区分 | 不能，可能已经产生副作用 |

Android 官方对 `TransactionTooLargeException` 的表述很谨慎：请求可能没有送达，也可能是服务端执行后无法返回过大的 reply；客户端应按 partial failure 处理。这条规则也适用于“服务端在提交副作用后死亡”一类 transport failure。涉及扣款、提交订单、删除文件等非幂等操作时，不能看到异常就直接重放。

## 2. Java 层会出现哪些异常

### 2.1 `RemoteException` 家族

`RemoteException` 是 checked exception，常见子类包括：

| 类型 | 含义 | 注意点 |
|---|---|---|
| `DeadObjectException` | 远端进程不存在，或底层 Binder 出现等价的存活失败 | 旧 proxy 已失效；`isBinderAlive()` 为真也只代表检查时刻 |
| `DeadSystemException` | Android 核心系统正在 runtime restart | 它继承 `DeadObjectException`；应用随后通常也会被终止 |
| `TransactionTooLargeException` | 大 transaction 失败后的启发式分类 | 可能是 request 或 reply；异常名不能证明精确字节原因 |
| 其他 `RemoteException` | 未实现 transaction、低层传输失败等 | 要结合接口版本、日志和服务端证据 |

普通应用调用 `PackageManager`、`ActivityManager` 等 framework manager 时，manager 往往已在内部捕获 `RemoteException`，再调用 `rethrowFromSystemServer()` 或转换成该 API 定义的运行时异常。因此，“给所有系统 API 加 `catch (RemoteException)`”既不能编译，也覆盖不了完整边界。只有自有 AIDL proxy 或明确声明 `RemoteException` 的接口，才在调用处处理这组 checked exception。

### 2.2 reply 中传播的运行时异常

服务端 `Binder.execTransactInternal()` 会把 `onTransact()` 抛出的、Parcel 支持的异常编码进同步 reply。`android-17.0.0_r1` 的 `Parcel` 支持 `SecurityException`、`BadParcelableException`、`IllegalArgumentException`、`NullPointerException`、`IllegalStateException`、`NetworkOnMainThreadException`、`UnsupportedOperationException` 和 `ServiceSpecificException` 等类型。

这类异常表示请求通常已经到达服务端。处理方式取决于接口契约：

- `SecurityException` 是权限、用户或调用身份问题，不应自动重试。
- `IllegalArgumentException`、`BadParcelableException` 多半是客户端/服务端版本或数据契约问题。
- `ServiceSpecificException` 携带服务自定义 `errorCode`。AOSP Java backend 用它表达 `EX_SERVICE_SPECIFIC`，错误码应在 AIDL 接口中用 `const int` 或 int-backed enum 定义。
- `oneway` 没有 reply 通道，服务端异常无法按这条路径返回给调用方。

现稿曾写到 AIDL 用 `@Throw` 声明异常，这个语法不存在。`ServiceSpecificException` 在 Android 17 源码中属于 platform/System API；普通 SDK 应用自建 AIDL 时，更适合用公开的结果 parcelable 或回调状态表达业务失败，不要依赖隐藏平台类。平台代码使用 service-specific error 时，也要把每个 error code 的可重试性写入接口契约。

### 2.3 本地解包和协议错误

`BadParcelableException`、`ParcelFormatException`、class loader 找不到 Parcelable、Stable AIDL 版本不兼容等问题，可能在客户端读 reply 或服务端读 request 时发生。它们不等同于远端进程死亡。错误证据至少要包含接口版本、transaction code、Parcelable schema 版本和出错方向，不能只按顶层异常名聚类。

## 3. `TransactionTooLargeException` 的真实边界

### 3.1 1MiB 是进程共享额度，不是每次调用配额

Android 17 的 `ProcessState.cpp` 使用：

`BINDER_VM_SIZE = 1 * 1024 * 1024 - 2 * page_size`

这块映射是进程接收 Binder transaction 的虚拟地址区。公开文档将其概括为固定 1MiB buffer，并明确说明：进程中所有进行中的 transaction 共享这份有限空间。因此，中等大小的并发 request/reply 也可能失败。应用不能把“每次小于 1MiB”写成放行条件。

驱动还要为对象偏移、Binder 引用和 FD 等元数据留空间。发送方 `Parcel.dataSize()` 只能描述当前 Parcel 的 inline 大小，无法预知目标进程并发占用，也无法覆盖 reply 大小。

### 3.2 Java 异常名来自启发式映射

`android_util_Binder.cpp` 在收到 `FAILED_TRANSACTION` 时，会记录 request Parcel 大小。Android 17 锚点中，request 大于 200KiB 才启发式抛 `TransactionTooLargeException`；更小的失败可能映射成 `DeadObjectException`，因为 `FAILED_TRANSACTION` 也可能来自 malformed transaction、已关闭 FD、远端在途死亡或 buffer 空间不足。

这解释了两个排障现象：

- 小 Parcel 也可能因为并发占用而失败，异常未必叫 `TransactionTooLargeException`。
- reply 过大时，客户端日志里的 request size 可能很小；服务端已经执行完成，只是在回包阶段失败。

200KiB 是当前 Java JNI 分类阈值，不是协议预算。公开 API `IBinder.getSuggestedMaxIpcSizeBytes()` 从 API 30 起返回 64KiB 的安全建议值，文档还建议 transaction 尽量更小。团队可以为具体接口设置更低预算，但不要把 64KiB 误写成驱动硬上限。

### 3.3 `CursorWindow` 与共享内存不要算成 inline Parcel

`CursorWindow`、`SharedMemory`、`ParcelFileDescriptor` 等对象通过 Binder 传递描述符和少量元数据，大块内容位于共享内存、memfd、pipe 或文件中。`CursorWindow` 自身的窗口容量不能直接相加成 Binder inline payload。需要关注的是 Parcel 中的描述符/元数据数量、接收端资源以及共享区域生命周期。

适合拆出 Binder inline 数据的对象包括：大型 `Bundle`、字符串/对象列表、`byte[]`、层层嵌套的 Parcelable，以及 Activity/Fragment 保存状态。生命周期调用产生的 `TransactionTooLargeException` 常在 framework 提交 `savedInstanceState` 时出现，业务代码未必有一个可见的 AIDL 调用点；应检查 View state、Fragment arguments、Navigation 参数和 `onSaveInstanceState()`。

### 3.4 在自有协议里设置可测预算

下面的函数用于测试或 debug 构建中估算一个 `Bundle` 的序列化大小：

```kotlin
fun marshalledSize(bundle: Bundle): Int {
    val parcel = Parcel.obtain()
    return try {
        parcel.writeBundle(bundle)
        parcel.dataSize()
    } finally {
        parcel.recycle()
    }
}
```

这个值适合做自有 request 的回归断言，不能证明线上 transaction 一定成功：它没有包含并发 buffer 压力、reply、驱动对象开销和 framework 额外字段。建议同时对 request 与 reply 建预算，并把 `IBinder.getSuggestedMaxIpcSizeBytes()` 当公开上界建议。

大数据协议优先使用：

- 分页或基于 continuation token 的增量查询；
- `ParcelFileDescriptor` pipe 做流式传输；
- `SharedMemory` 传递有明确尺寸和访问权限的共享区域；
- 文件/ContentProvider URI，只在 Binder 中传 capability；
- 对状态型回调只发 version/sequence，让接收方按需拉取完整状态。

分片不应只是把一笔非幂等操作拆成多次无标识调用。每片需要 request ID、序号、总数、校验和与提交协议，才能在进程死亡或重复投递后恢复。

## 4. 死亡通知、重连与幂等性

`linkToDeath()` 让客户端在远端 Binder 所在进程死亡时收到 `DeathRecipient`。注册和回调都有竞态：注册时目标可能已经死亡，`linkToDeath()` 会抛 `RemoteException`；`isBinderAlive()` 返回后目标也可能立即退出。

死亡回调只做三件事：

1. 递增连接 epoch，并把当前 proxy 标成不可用。
2. 清除依附于旧进程的 session、callback 注册和缓存句柄。
3. 把重新 bind/获取服务的工作投递到受控 executor。

回调线程不应用来做磁盘、网络或等待新服务。重新连接后要拿到新 proxy，重新协商接口版本并恢复必要状态；继续调用旧 proxy 没有意义。

重试策略由操作语义决定：

| 操作 | transport failure 后的动作 |
|---|---|
| 纯读取、可重复查询 | 重新获取 proxy 后可做一次有上限重试 |
| 带稳定 request ID 的幂等写入 | 先查询服务端状态，确认未提交后再重放 |
| 扣款、消费一次性 token、追加日志 | 结果未知；查询提交状态，不能盲目重放 |
| `TransactionTooLargeException` | 改协议或减小 payload；原样重试没有价值 |
| `SecurityException` / 参数错误 | 修复权限、身份或参数；退避重试无效 |
| `oneway` | 本地返回只代表无需等 reply；可靠投递要另建 ack/sequence 协议 |

下面的包装器用于自有同步 AIDL 边界。它分类结果但不自动重试，避免把不确定结果重复执行：

```kotlin
inline fun <T> callRemote(block: () -> T): IpcCallResult<T> {
    return try {
        IpcCallResult.Success(block())
    } catch (e: TransactionTooLargeException) {
        IpcCallResult.Indeterminate(
            kind = IpcFailureKind.TRANSACTION_FAILED_LARGE,
            cause = e,
        )
    } catch (e: DeadObjectException) {
        IpcCallResult.Indeterminate(
            kind = IpcFailureKind.REMOTE_DIED,
            cause = e,
        )
    } catch (e: RemoteException) {
        IpcCallResult.TransportUnavailable(e)
    } catch (e: SecurityException) {
        IpcCallResult.PolicyRejected(e)
    } catch (e: BadParcelableException) {
        IpcCallResult.ProtocolMismatch(e)
    }
}
```

`Indeterminate` 的含义是“不能仅凭客户端异常判断服务端副作用”。调用方只有在接口具备幂等键或状态查询能力时才重试。不要把所有 framework API 都包进 `catch (RuntimeException)`；只处理该公开 API 文档声明或自有协议约定的异常。

## 5. Binder Freezer：同步调用与 oneway 的行为相反

Android 17 的 freezer 行为与旧文中“同步调用一直等到解冻”不同。当前官方文档与驱动源码给出的路径是：

- 向 frozen app 发送同步 Binder transaction 时，驱动返回 `BR_FROZEN_REPLY`；系统会终止被冻结的目标 app，避免调用线程无限等待。目标进程的退出记录可表现为 `ApplicationExitInfo.REASON_FREEZER`。
- 向 frozen app 发送 `oneway` transaction 时，驱动把它放到目标 node 的 `async_todo`，并向发送方报告 `BR_TRANSACTION_PENDING_FROZEN`。目标解冻后才处理；队列过多可能让接收进程崩溃，事件也可能已经过期。
- `TF_UPDATE_TXN` 只有在设置该 flag 且 code、发送 pid、目标 node 等条件一致时，才允许新异步 transaction 替换冻结队列里的旧项；普通 AIDL 不能把它当作自动合并保证。

API 36 起，`IBinder.addFrozenStateChangeCallback()` 是公开 API。它适合服务端持有客户端 callback Binder 时观察对方冻结状态。回调可能合并中间状态，只能拿来维护“当前 frozen/unfrozen”，不能统计冻结次数。

管理一组远程 callback 时，优先使用 `RemoteCallbackList` 的 frozen callee policy：

- `FROZEN_CALLEE_POLICY_DROP`：实时事件，过期即无意义。
- `FROZEN_CALLEE_POLICY_ENQUEUE_MOST_RECENT`：状态同步，只保留最新值。
- `FROZEN_CALLEE_POLICY_ENQUEUE_ALL`：必须保留每个事件时使用，并设置有界队列；仍需评估解冻后的突发处理。
- `FROZEN_CALLEE_POLICY_UNSET`：兼容旧行为，不建议作为新代码默认值。

普通 bound service 会因绑定关系提升进程重要性，是否进入 cached/frozen 还受 bind flag 和进程状态影响。不要通过包名猜冻结状态；需要时观察具体 remote Binder，或让 callback 管理器采用明确策略。

## 6. 线程池耗尽、嵌套调用与 ANR

同步 Binder 调用会阻塞调用线程直到 reply 或失败。主线程上的一次长尾系统服务调用就足以造成卡顿，多次连续 Binder 调用还会把各自延迟累加。Android 的 ANR 指南也把“主线程等待慢 Binder reply”列为常见原因。

### 6.1 不要把 15/16 当作所有进程的固定线程数

Android 17 C++ libbinder 的 `DEFAULT_MAX_BINDER_THREADS` 是 15。源码同时说明：这个值是允许内核按需启动的线程数，`startThreadPool()` 还会额外启动一个线程，手工 `joinThreadPool()` 也可能增加参与者。Java app、native daemon、HAL 和 `system_server` 的配置并不完全相同。

排障时要读取目标进程在 trace/bugreport 中的真实 Binder 线程及其状态。看到 15 个线程不能直接下结论，看到 16 个也不代表已经达到某个统一上限。

### 6.2 三类常见耗尽路径

- **服务端慢工作**：Binder 线程持锁、做磁盘 I/O、等待硬件或调用慢下游。
- **嵌套同步调用**：A 调 B，B 在处理时同步回调 A。Binder 支持递归，A 中正在等待的线程可能参与处理回调；若双方还持有业务锁，容易形成跨进程锁环。
- **oneway 处理过慢**：同一 `IBinder` 对象上的多个 oneway 调用按发送顺序逐个分派；可能换线程执行，但前一笔完成前不会分派下一笔。`oneway` 消除了发送方等待，没有提供服务端并行能力。

服务端 `onTransact()` 应快速校验和复制必要参数，把可异步的耗时任务交给有界业务 executor，再尽快释放 Binder 线程。不要持有应用锁发起外部同步 Binder 调用；无法避免时要有明确的跨进程锁顺序和超时/取消协议。

## 7. oneway buffer 与 spam detection

`android17-6.18-2026-06_r6` 的 `binder_alloc` 初始化时把总 buffer 的一半留作 async transaction 额度。空间不足时，新的 oneway 分配会失败；这不是“静默丢弃且继续成功”。

当前驱动的 spam detector 在 async 空间低于总 buffer 的 10% 后开始检查发送 pid；同一 pid 占用超过 50 个 async buffer，或占用量超过总 buffer 的 25%，会把某笔 transaction 标成 suspect。libbinder 收到 `BR_ONEWAY_SPAM_SUSPECT` 后打印“oneway spamming”和调用栈。

这些数值是当前 kernel 锚点的实现细节，不是应用协议可以依赖的限流阈值。检测器提供诊断信号，不会替应用合并状态，也不保证可靠投递。高频事件应在发送前做采样、去重或 latest-only 合并；需要每条不丢的业务流应使用有背压和确认的协议，而不是无限发送 oneway。

## 8. 排障：同时看客户端、服务端和驱动时间线

### 8.1 客户端证据

- 完整 Java/Kotlin 堆栈，保留 `BinderProxy.transactNative` 上方的 AIDL/manager 方法。
- 接口名、方法/transaction code、同步或 oneway、调用线程、耗时。
- 自有协议的 request/reply 估算字节、列表项数、FD 数和 schema 版本。
- request ID、重试序号、连接 epoch、调用前后的 proxy 存活观察。
- 原始异常类、message、cause；message 脱敏后再上传。

### 8.2 服务端证据

- 对应 request ID 是否进入、是否完成副作用、reply 序列化是否开始。
- `onTransact()`/业务 handler 耗时，Binder 线程状态，持有锁和下游 IPC。
- 进程 crash、LMK、force-stop、freezer 或重启时间。
- oneway 队列策略、丢弃/合并数、处理序号缺口。

### 8.3 工具边界

Perfetto 采集 `binder_driver`、`sched` 和相关 app/系统 atrace 类别后，可以把客户端 transaction、服务端处理、reply 与线程调度放在同一时间轴。PerfettoSQL 的 `android.binder` 标准库还提供 transaction breakdown、blocked functions 和图关系。不要只按 track 名称模糊筛选 slice。

ANR 先看主线程是否停在 `BinderProxy.transactNative`，再沿 Perfetto flow 找服务端线程，确认它在运行、等锁、I/O 还是下游 Binder。只有客户端栈时，最多能证明“正在等待某次 IPC”。

`/sys/kernel/debug/binder` 或 binderfs stats 受 build、SELinux、root 权限和设备配置限制，适合 userdebug/eng 或实验室设备。`dumpsys binder <pid>` 不是所有量产设备都存在的稳定命令；使用前先通过 `dumpsys -l` 和设备构建确认服务。线上应用也不能依赖内核 debug 节点。

日志可搜索 `FAILED BINDER TRANSACTION`、`oneway spamming`、`Sending oneway calls to frozen process`，但 tag、级别和可见性会随构建变化。日志只作为辅助证据。

## 9. 自有 AIDL 的持续监控

客户端在 AIDL proxy 外层计时，得到的是同步端到端等待：

```text
marshal + driver out + server queue + server execution
        + reply + unmarshal
```

这个值适合衡量用户体验，但不能命名为“Binder 传输耗时”。`oneway` 外层计时只覆盖序列化和本地提交，不表示远端已经执行；同进程 local Binder 可能直接调用 Stub，也应与跨进程样本分开。

普通应用没有可依赖的全局 Binder Hook。`Binder.ProxyTransactListener` 和 `BinderInternal.Observer` 属于隐藏或平台内部接口，native/Rust Binder 也不一定经过同一 Java 入口。应用拥有 AIDL 契约时，优先用显式 client/server wrapper；系统服务只在少数公开 manager 调用点记录业务语义。

下面的包装器保留逻辑接口、线程、耗时和原始失败类型，不依赖隐藏 API：

```kotlin
data class IpcCallSample(
    val service: String,
    val method: String,
    val oneway: Boolean,
    val durationNanos: Long,
    val mainThread: Boolean,
    val failureClass: String?,
)

interface IpcRecorder {
    // 非阻塞、无 Binder/网络调用、不会向调用方抛异常。
    fun tryRecord(sample: IpcCallSample): Boolean
}

inline fun <T> measuredIpc(
    service: String,
    method: String,
    oneway: Boolean,
    recorder: IpcRecorder,
    block: () -> T,
): T {
    val started = SystemClock.elapsedRealtimeNanos()
    var failureClass: String? = null
    try {
        return block()
    } catch (failure: Throwable) {
        failureClass = failure.javaClass.name
        throw failure
    } finally {
        try {
            recorder.tryRecord(
                IpcCallSample(
                    service,
                    method,
                    oneway,
                    SystemClock.elapsedRealtimeNanos() - started,
                    Looper.myLooper() == Looper.getMainLooper(),
                    failureClass,
                )
            )
        } catch (_: Throwable) {
            // 监控故障不能遮蔽业务结果；这里也不能递归记录日志。
        }
    }
}
```

标签只能来自编译期稳定枚举，不能包含 URI、用户 ID、参数或异常 message。recorder 使用固定容量缓冲，满时丢弃并计数；高频接口可写入预分配 ring buffer，编码和上传放到独立线程。服务端 wrapper 记录 `server_enter/server_exit`；需要关联时把 request ID 纳入业务协议，不能靠两端墙钟日志猜测。

### 长尾采样与 Perfetto

总体分位数和慢调用诊断需要两条采样路径：低比例均匀采样估计 P50/P90/P99，超过接口阈值的调用进入有冷却与速率上限的诊断缓冲。若只上传慢样本，得到的只是“慢调用中的分布”。远端一次死亡可能让多条并发调用同时抛 `DeadObjectException`，死亡率要按 connection epoch 或 death notification 去重。

常驻指标发现接口后，再用 Perfetto 对齐 `android.binder`、`binder_driver`、`sched`、AIDL atrace 和应用 slice：先看客户端线程，再沿 flow 找服务端是否排队、等 CPU、等锁、执行或发起下游 IPC，最后看 reply 后客户端何时恢复。trace debug ID 只适合单次 trace 关联，不是长期业务主键。

监控实现不得在关键路径发 Binder、写同步日志、访问磁盘或网络，也不得争用全局重锁。采样决策在调用前完成，配置错误时可以熔断监控，但不能改变业务异常、重试或返回值。

## 10. 稳定性与性能指标

建议把 IPC 作为独立指标域，不要只看 Java crash：

| 指标 | 作用 |
|---|---|
| 同步调用 P50/P95/P99 与主线程占比 | 找慢服务和 UI 风险 |
| 每接口 request/reply size bucket | 找协议膨胀 |
| `DeadObjectException` 与连接 epoch | 找服务重启和代理复用错误 |
| `TransactionTooLargeException` / `FAILED_TRANSACTION` | 找大 payload、并发 buffer 或低层失败 |
| 权限/协议/业务错误码 | 区分 transport 与 domain failure |
| oneway 发送、合并、丢弃、消费序号 | 找积压和过期事件 |
| callback frozen policy 命中数 | 验证 drop/latest/all 是否符合语义 |
| 重试次数、去重命中、未知提交状态 | 发现重放风险 |
| 服务端 Binder 线程忙时与下游等待 | 找线程池耗尽根因 |

APM hook 只能覆盖自己能安全观察的边界。普通应用无法可靠全局 hook 所有 Binder proxy；反射或 native hook 还可能改变时序。自有 AIDL 应在生成代码外的 client wrapper 和 service implementation 记录，系统 API 则依赖公开 trace、异常和方法级埋点。

## 11. Android 17 验证清单

| 用例 | 预期 |
|---|---|
| request 在自有预算上下波动 | 超预算在调用前拒绝或改走分页/FD |
| reply 超预算 | 客户端按 partial failure 处理，服务端 request ID 可查询提交状态 |
| 多个中等 transaction 并发 | 能复现共享 buffer 压力，不误判成单笔超过 1MiB |
| request 含关闭 FD/坏 Parcelable | 分类为协议/FD 问题，不只看异常名 |
| 服务端在执行前、执行中、提交后被杀 | 客户端不会盲目重放非幂等操作 |
| `linkToDeath()` 注册时与调用中死亡 | 连接 epoch 正确，旧 proxy 不再使用 |
| 主线程同步调用慢服务 | 测试门禁能发现，业务移动到合适线程或改协议 |
| Binder 线程持锁后反向回调 | 锁顺序检查能发现潜在死锁 |
| 高频 oneway 到同一 Binder | 发送侧合并/背压生效，服务端无无界积压 |
| callback 接收进程被冻结 | drop/latest/all 三种策略符合事件语义 |
| frozen 进程收到同步 transaction | 观察 frozen reply 与 `REASON_FREEZER`，不按普通 ANR 归因 |
| AIDL 客户端/服务端版本错配 | unknown transaction、默认值和错误方向可定位 |

## 12. 与相邻章节的边界

- 1.4 负责 Binder 驱动、对象引用与一次 transaction 的基础链路。
- 1.17 负责不同 IPC 机制的选型和通用性能比较。
- 1.18 负责 cached apps freezer 与进程生命周期。
- 20.4 负责 ANR 证据和超时类型，这里提供 Binder 侧等待链。
- 26.9 负责 Perfetto/eBPF 等观测工具，这里只说明 IPC 需要哪些证据。

## 小结

Binder 故障不能只按一个异常类处理。`TransactionTooLargeException` 是 `FAILED_TRANSACTION` 的启发式映射，request 或 reply 都可能失败，服务端还可能已产生副作用；`DeadObjectException` 要重建连接，不能继续使用旧 proxy；`oneway` 只有“无需等待”的语义，没有成功确认和服务端并行保证。

Android 17 还要求把 freezer 纳入 IPC 设计：同步 transaction 到 frozen app 会触发目标终止路径，oneway 会在 async 队列等待解冻。应用可以用 API 36 起的 frozen-state callback 和 `RemoteCallbackList` policy 管理回调，但协议仍要有大小预算、背压、幂等键、状态查询和三端证据。做到这些，Binder 异常才会从模糊 crash 变成可恢复、可归因的 IPC 故障。

## 参考资料

- [`RemoteException`](https://developer.android.com/reference/android/os/RemoteException)
- [`TransactionTooLargeException`](https://developer.android.com/reference/android/os/TransactionTooLargeException)
- [`IBinder`](https://developer.android.com/reference/android/os/IBinder)
- [Handle cached and frozen apps](https://source.android.com/docs/core/architecture/ipc/binder-freezer)
- [Cached apps freezer](https://source.android.com/docs/core/perf/cached-apps-freezer)
- [AIDL backends - Error handling](https://source.android.com/docs/core/architecture/aidl/aidl-backends#error-handling)
- [Diagnose ANRs](https://developer.android.com/topic/performance/anrs/find-unresponsive-thread)
- [Perfetto：Android system tracing](https://perfetto.dev/docs/learning-more/android)
- [PerfettoSQL：`android.binder` standard library](https://perfetto.dev/docs/analysis/stdlib-docs#android-binder)
- [AOSP `android-17.0.0_r1`：`ProcessState.cpp`](https://android.googlesource.com/platform/frameworks/native/+/android-17.0.0_r1/libs/binder/ProcessState.cpp)
- [AOSP `android-17.0.0_r1`：`IPCThreadState.cpp`](https://android.googlesource.com/platform/frameworks/native/+/android-17.0.0_r1/libs/binder/IPCThreadState.cpp)
- [AOSP `android-17.0.0_r1`：Java Binder JNI mapping](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/jni/android_util_Binder.cpp)
- [AOSP `android-17.0.0_r1`：`Parcel.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/os/Parcel.java)
- [Kernel `android17-6.18-2026-06_r6`：Binder driver](https://android.googlesource.com/kernel/common/+/android17-6.18-2026-06_r6/drivers/android/binder.c)
- [Kernel `android17-6.18-2026-06_r6`：Binder allocator](https://android.googlesource.com/kernel/common/+/android17-6.18-2026-06_r6/drivers/android/binder_alloc.c)
