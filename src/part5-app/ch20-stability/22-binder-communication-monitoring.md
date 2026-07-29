---
title: "Binder 通信监控实战：传输耗时、异常检测与 IPC 性能治理"
chapter: "20.22"
status: draft
applicable_versions: "Android 12 (API 31) - Android 17 (API 37)"
tags: [Binder, IPC监控, 稳定性, 性能监控]
related_chapters: ["1.44", "1.53", "1.54", "17.17", "20.17"]
created_by: "task2a-knowledge-gap"
created_date: "2026-07-16"
gap_source: "素材驱动(Clippings)"
confidence: medium
---

# 20.22 Binder 通信监控实战：传输耗时、异常检测与 IPC 性能治理

<!-- outline-start -->
## 要点

### 🔹 Binder 通信监控的应用层需求
- 为什么需要监控 Binder：跨进程调用的延迟、异常、死锁对用户体验的影响
- 典型痛点：系统服务调用超时、TransactionTooLargeException、DeadObjectException
- [结构参考: Clippings/Android 应用稳定性剖析与优化 - Binder 通信监控]

### 🔹 Binder 传输耗时监控方案
- watchdog 方案：在 Binder.transact() 前后埋点计时
- Proxy/Stub 动态代理：拦截系统服务接口调用
- 利用 StrictMode 的 Binder 耗时检测能力

### 🔹 Binder 异常体系与线上治理
- TransactionTooLargeException：Binder buffer 1MB 限制（每进程）
- DeadObjectException：对端进程已死，IPC 目标不可达
- SecurityException：权限不足导致的调用失败
- RemoteException 家族的统一处理策略

### 🔹 Binder 监控的性能开销与采样策略
- 全量监控 vs 采样监控的取舍
- AOP 字节码插桩在 Binder 监控中的应用
- 监控本身的 Binder 调用开销（递归风险）

### 🔹 Binder 调用链路与 ANR 关系
- 主线程 Binder 同步等待是 ANR 的常见原因
- ServiceManager.getService() 缓存机制与失效场景
- Android 17 Binder 优先级继承对监控的影响 [已验证: AOSP android-17.0.0_r1]

### 🔹 线上 Binder 性能画像建设
- Binder 调用 P50/P90/P99 耗时分布
- 按 target 进程/target 接口聚合的 TopN 耗时排行
- Binder 异常率与 Service 死亡率的实时告警

## 扩展

### 🔸 Binder 缓冲区监控与优化
- /dev/binder 的 buffer 使用情况采集
- 大数据传输的替代方案（SharedMemory、Socket）

### 🔸 Android 17 Binder 批处理与监控适配
- 异步批处理流水线对现有监控方案的兼容性
- [待验证: Android 17 Binder 批处理监控的准确方案]

<!-- outline-end -->

Binder 监控最容易出现的误区，是把一次方法调用的总耗时直接命名成“Binder 传输耗时”。客户端在 AIDL 方法外计时，得到的是序列化、驱动投递、服务端排队与执行、回复传输、客户端反序列化的总和；只看这个数，无法判断时间消耗在哪一段。

本文的平台源码锚点为 `android-17.0.0_r1`，Binder 驱动锚点为 `android17-6.18-2026-06_r6`。结论适用于 Android 12～Android 17；涉及隐藏接口和内核诊断能力时，会单独说明量产应用能否使用。

## 1. 先定义监控问题

一套可用的 Binder 监控至少要回答四个不同问题：

1. 哪个逻辑服务、哪个接口方法出现了长尾？
2. 慢调用发生在主线程还是后台线程，会不会成为卡顿或 ANR 的组成部分？
3. 失败属于传输、远端死亡、协议、权限，还是业务返回？
4. 客户端等待时间来自本地、驱动排队、服务端调度、服务端执行，还是 reply 路径？

前两个问题可由应用内埋点持续回答；第三个问题需要保留原始异常和接口语义；第四个问题通常要把客户端、服务端与 Perfetto 时间线放在一起。不要让一个“ipc_cost”字段承担全部含义。

主线程同步 Binder 调用值得优先治理，但“主线程栈停在 `BinderProxy.transactNative()`”只证明采样时正在等待 IPC。它不能单独证明服务端死锁，也不能说明目标进程正在运行。连续多次短调用的累计时间，同样可能越过帧预算或 ANR 时间窗口。

## 2. Android 17 上各类手段能看见什么

| 手段 | 普通应用可用 | 能看到的范围 | 关键限制 |
|---|---:|---|---|
| 自有 AIDL client wrapper | 是 | 逻辑接口、方法、调用线程、同步端到端耗时、客户端异常 | 不能拆分服务端排队和执行；`oneway` 不代表远端完成 |
| 自有 AIDL server wrapper | 是 | 服务端入口、执行耗时、业务结果 | 没有请求 ID 时，跨进程样本难以可靠关联 |
| 系统 API 调用点插桩 | 是 | 某个公开 manager API 的调用耗时与异常 | 看到的是 framework API，不一定能取得底层 transaction code |
| `Debug.getBinderSentTransactions()` / `getBinderReceivedTransactions()` | 是 | 本进程累计发送、接收 transaction 数 | 读取失败返回 -1；没有接口名、目标、耗时和失败原因 |
| `Binder.ProxyTransactListener` | 否，隐藏/System API | 当前进程 Java Binder proxy 的全局回调 | 不覆盖全部 native/Rust 路径；位于关键路径，且禁止在回调中再发 Binder |
| `BinderInternal.Observer` | 否，平台内部接口 | Java Binder 服务端调用、异常、request/reply 大小 | 供 framework 进程使用；源码还标明不覆盖 C++/Rust |
| Perfetto `android.binder` | 调试、实验和专项采集 | client/server slice、调度、接口与方法、阶段耗时 | 不是普通应用常驻采集接口；字段质量受 trace 配置和符号信息影响 |
| binderfs/debugfs 统计 | 通常否 | 驱动节点、进程、线程、transaction 等内核状态 | 受构建、SELinux、挂载和权限限制，不能作为线上应用依赖 |

`BinderProxy.transact()` 在 Android 17 源码中会调用进程级 `ProxyTransactListener`，然后进入 `transactNative()`，并在 `finally` 中结束监听。这个入口看起来适合做全局 Hook，但 API 带有 `@hide`/`@SystemApi` 限制。通过反射、替换系统服务缓存或修改隐藏静态字段来接入，会同时面对隐藏 API 限制、系统实现变化和全进程并发安全问题，不适合作为业务应用的监控基座。

应用拥有 AIDL 契约时，优先使用显式 wrapper。对 `ActivityManager`、`PackageManager` 等 framework manager，则在少数已知的公开调用点记录业务语义，不要尝试把系统进程里的全部 transaction 劫持到应用进程。

## 3. 客户端计时的语义

### 3.1 同步调用

在生成的 AIDL proxy 外层计时，同步调用的观测值可近似写成：

`T_client = T_marshal + T_driver_out + T_queue + T_server + T_driver_reply + T_unmarshal`

这是调用方感受到的等待时间，适合做用户体验指标。它不等于驱动传输时间。客户端单点埋点无法继续拆解上式；想知道服务端是没获得 CPU、等待 Binder 线程、持锁，还是执行慢，需要服务端时间戳或 Perfetto 的 `binder_driver`、AIDL 和 `sched` 数据。

计时必须使用单调时钟，例如 `SystemClock.elapsedRealtimeNanos()`。墙上时间可能因为自动校时而跳变，不适合计算时长。

### 3.2 `oneway` 调用

`oneway` 的客户端方法不等待 reply。外层计时只覆盖序列化和本地提交路径，不能作为服务端执行耗时，也不能证明目标已经处理。目标被冻结、服务端队列积压或进程随后死亡时，客户端仍可能很快返回。

如果业务需要“远端处理完成”的指标，应在协议中增加 request ID，并由服务端通过回调、状态流或后续查询确认。这个确认是业务协议的一部分，不应伪装成 `oneway` 本身提供的保证。

### 3.3 本地 Binder

同一进程中的 AIDL Stub 可能通过 `queryLocalInterface()` 直接调用实现，不经过 Binder 驱动。它仍值得记录，因为服务实现可能很慢，但不能与跨进程样本混成同一分布。自有接口可以在建连时把 transport 标记为 `local` 或 `remote`；普通 framework API wrapper 不一定能拿到这项信息。

## 4. 自有 AIDL 的推荐埋点

下面的包装器用于记录自有同步或 `oneway` AIDL 调用。它只保留稳定的逻辑标签，不依赖隐藏 API：

```kotlin
data class IpcCallMeta(
    val service: String,
    val method: String,
    val oneway: Boolean,
)

data class IpcCallSample(
    val meta: IpcCallMeta,
    val durationNanos: Long,
    val mainThread: Boolean,
    val failureClass: String?,
)

interface IpcRecorder {
    /**
     * 必须非阻塞、无 Binder/网络调用、不会向调用方抛异常。
     * 缓冲区满时返回 false 并丢弃当前样本。
     */
    fun tryRecord(sample: IpcCallSample): Boolean
}

private inline fun protectMonitoring(block: () -> Unit) {
    try {
        block()
    } catch (_: Throwable) {
        // 监控边界内禁止记录日志或调用其他故障上报设施。
    }
}

fun <T> measuredIpc(
    meta: IpcCallMeta,
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
        protectMonitoring {
            recorder.tryRecord(
                IpcCallSample(
                    meta = meta,
                    durationNanos =
                        SystemClock.elapsedRealtimeNanos() - started,
                    mainThread =
                        Looper.myLooper() == Looper.getMainLooper(),
                    failureClass = failureClass,
                ),
            )
        }
    }
}
```

`IpcRecorder` 的“不抛异常”是生产契约，不是 Kotlin 类型系统能保证的属性。示例只在监控边界捕获 `Throwable`，目的是让样本构造或 recorder 故障不遮蔽业务异常；业务调用自身的异常仍原样抛出。这个保护分支不能写日志或启动另一条故障上报路径。实现侧应使用固定容量或有界队列，容量不足就计数并丢弃。高频路径还要控制对象分配，可以把样本写入预分配的 ring buffer，再由独立线程批量编码和上传。

调用包装器时，标签应来自编译期常量，例如 `account/IAccountService/getProfile`。不要把 URI、文件名、用户 ID、完整参数或异常 message 放进指标标签；这些数据既可能包含隐私，也会造成无法控制的维度数量。

### 4.1 为什么显式 wrapper 比动态代理更稳

Java `Proxy` 或字节码插桩可以包住 AIDL 接口方法，但只能自动取得 Java 层方法信息。它不会凭空得到：

- 驱动 transaction 的目标 PID；
- request/reply 的准确 Parcel 大小；
- Binder 线程排队时间；
- 服务端执行时长；
- `oneway` 的远端完成时间。

字节码插桩适合在明确的接口白名单上批量生成同等 wrapper，并在编译期检查遗漏。不要对所有方法名包含 `transact` 的调用做宽泛匹配，也不要假设 framework manager 的实现类在各 Android 版本中稳定。

### 4.2 服务端补齐执行时间

自有服务端可以在 Stub 实现入口记录 `server_enter`、`server_exit` 和结果类型。需要端到端关联时，把随机 request ID 或单调递增 sequence 作为 AIDL 参数的一部分；不要依靠两端墙上时间相减，因为设备内不同进程虽然共享同一内核单调时钟，日志采集、缓冲和事件重排仍会引入误判。

服务端入口时间能分离“已经进入实现后的执行”，但客户端开始到服务端入口之间仍包含序列化、驱动与调度。精确定位这段时间仍要看 trace。

## 5. 系统服务调用与 `ServiceManager` 缓存

Android 17 的 `ServiceManager.getService(name)` 先查询进程内私有 `sCache`；未命中时调用 `rawGetService(name)`。需要注意，普通的 miss 路径不会在该方法里把结果重新写回 `sCache`。`initServiceCache()` 是系统进程启动时的一次性缓存注入接口，也不是应用可以控制的动态缓存。

因此，不能把系统服务耗时简单解释成“ServiceManager 缓存失效”。很多 framework manager 会自行持有 AIDL proxy；应用通过 `bindService()` 获得的服务则由 `ServiceConnection` 生命周期管理。远端死亡后，旧 proxy 不会因为再次调用同一个 Java 方法而自动恢复成新服务。

对自有 bound service，记录连接 epoch 比记录 proxy 对象地址更有用：

- `onServiceConnected()` 取得新 proxy 时递增 epoch；
- `binderDied()` 或 `onServiceDisconnected()` 使当前 epoch 失效；
- 每条 IPC 样本携带逻辑 service 和 epoch；
- 重连后重新注册 callback，并按接口契约恢复状态。

`isBinderAlive()` 只能描述检查瞬间。检查结束后远端仍可能立即死亡，不能用它消除 `DeadObjectException`。

## 6. 异常指标不能代替异常语义

Binder 监控应保留异常的原始 Java 类型，但自动处理策略必须按接口语义制定：

| 观测结果 | 应如何解释 | 常见治理动作 |
|---|---|---|
| `DeadObjectException` | 远端已死或底层映射为等价的存活失败 | 使旧连接失效；按操作幂等性决定是否重连后重试 |
| `TransactionTooLargeException` | 大 transaction 失败的启发式分类，request/reply 方向可能不明确 | 缩小协议、分页或改用 FD/共享内存；不要原样重试 |
| 其他 `RemoteException` | IPC transport 或接口层失败 | 保留子类和调用点，不做无条件统一重试 |
| `SecurityException` | 权限、调用身份或用户边界被拒绝 | 修正权限/身份；退避重试通常无效 |
| `BadParcelableException` 等 | 序列化、class loader 或协议兼容问题 | 记录 schema/接口版本，核查两端实现 |
| 业务错误码 | 服务端已处理并返回业务结果 | 按业务契约处理，不计入 transport failure |

framework manager 常在内部捕获 `RemoteException`，再通过 `rethrowFromSystemServer()` 转成运行时异常。应用侧不应假设所有系统 API 都能统一 `catch (RemoteException)`。更完整的异常、buffer、冻结与幂等重试边界见 [20.17 Binder 异常体系与 IPC 故障性能边界](17-binder-exception-ipc-fault-performance.md)。

监控 wrapper 只记录和原样抛出，不应擅自重试。一次有副作用的同步调用即使以 transport failure 结束，服务端也可能已经执行；没有幂等键和状态查询时，自动重试会制造重复提交。

## 7. 1MiB buffer 应该怎样监控

Android 公开文档常把 Binder transaction buffer 概括为 1MiB。Android 17 的 native Binder 进程映射大小为 `1 MiB - 2 * page_size`，由进程中所有在途 transaction 共享。它不是“每次调用各有 1MiB”，也不是只要单个 request 小于 1MiB 就安全。

`Parcel.dataSize()` 只能描述当前 Parcel 的 inline 数据，无法得知目标进程的并发占用，也不能预测 reply 大小。使用生成 AIDL proxy 的普通 wrapper 时，参数序列化发生在 proxy 内部；为监控再序列化一遍会增加 CPU、内存和 FD 生命周期风险，不适合线上全量执行。

公开 API `IBinder.getSuggestedMaxIpcSizeBytes()` 给出 64KiB 建议值。这个值是保守的开发建议，不是驱动硬上限。自有协议应分别约束 request、reply、列表项数和 FD 数，并通过单元测试或 debug 构建中的 Parcel 序列化检查回归。

较大的数据可以改用：

- 分页或 continuation token；
- `ParcelFileDescriptor` pipe；
- `SharedMemory`；
- 文件或 `ContentProvider` URI，仅通过 Binder 传递描述信息与访问能力；
- 状态版本号加按需拉取，而不是每次推送完整对象图。

应用不能通过读取 `/dev/binder` 得到自己的 buffer 使用率。`/dev/binder` 是驱动设备节点，不是稳定的文本统计接口；binderfs/debugfs 下的诊断文件也常被 SELinux 和量产构建限制。线上应监控自有协议预算、异常和并发数，实验室再用内核统计与 Perfetto 验证。

## 8. StrictMode 的边界

StrictMode 会把线程策略状态随 Binder 调用传播，并能把远端收集到的部分 StrictMode violation 带回调用方。它擅长发现磁盘、网络、自定义慢调用等策略违规，但 Android 17 没有公开的“Binder 调用耗时 detector”。

所以，`detectAll()` 不能替代 AIDL wrapper 的单调时钟计时，也不能生成按接口统计的 P50/P90/P99。开发阶段仍可启用 StrictMode，借此发现“服务端 Binder 线程做了磁盘 I/O”一类问题；这与测量 IPC 本身的延迟是两件事。

## 9. 用 Perfetto 拆解长尾

常驻指标负责发现“哪个逻辑接口慢”，Perfetto 负责回答“为什么慢”。采集时至少关注：

- `binder_driver`：客户端 transaction、服务端处理和 reply flow；
- `sched`：线程 runnable、running、sleeping 与 CPU 调度；
- AIDL atrace：Java、libbinder 和 NDK Binder 在启用 tracing 时产生的接口/方法切片；
- app 自定义 slice：request ID、业务阶段和关键锁等待。

Android 17 的 Binder 驱动定义了 `binder_transaction`、`binder_transaction_received`、`binder_txn_latency_free`、buffer 分配/释放和优先级等 tracepoint。Perfetto 的 `android.binder` 标准库在这些原始事件之上提供 client/server transaction 与阶段分析。排障时可按以下顺序阅读时间线：

1. 客户端调用发生在哪个线程，是否为主线程；
2. transaction 是否关联到目标进程和服务端线程；
3. 服务端线程收到 transaction 后，是立即运行、等待 CPU、等锁，还是进入下游 IPC；
4. reply 返回后，客户端何时重新获得 CPU；
5. 同一线程前后是否存在一串短 Binder 调用，累计形成长尾。

内核 transaction debug ID 适合 trace 内关联，不应上传为长期业务主键。应用常驻指标也通常拿不到可信的目标 PID；使用稳定的逻辑 service/interface/method，专项 trace 再补进程与线程证据。

## 10. 优先级继承怎样影响计时

Binder 驱动会根据 transaction 和节点策略调整接收线程优先级，Android 17 锚点中可在 `binder_transaction_priority()` 及 `binder_set_priority` tracepoint 看到相关路径。它会影响服务端何时获得 CPU，因此也是端到端耗时的一部分。

优先级继承不会让客户端的单调时钟计时失真，也不需要在应用 wrapper 中“扣除”。如果一个调用的 wall time 很长，trace 却显示服务端执行很短，应继续检查服务端线程被唤醒前的排队、调度和锁等待。不要把所有差值归因于“Binder 传输”。

这些机制不能仅凭 Android 17 版本号解释为新特性。跨版本对比必须固定设备负载、接口、线程优先级和 trace 配置，再用源码差异说明行为变化。

## 11. Android 17 没有通用的 Binder 异步批处理接口

在 `android-17.0.0_r1` 的 libbinder 与 `android17-6.18-2026-06_r6` 的驱动中，没有发现普通应用可依赖的“Binder 异步批处理流水线”。驱动中的 `TF_UPDATE_TXN` 用于特定条件下替换被冻结目标队列中的旧 `oneway` transaction；它不是把任意多次 AIDL 调用自动合并成一批，也不提供通用完成通知。

如果业务希望减少 IPC 次数，应在自有 AIDL 中显式设计批量方法，并明确：

- 单批最大条目和序列化预算；
- 每项结果如何返回；
- 部分成功如何表达；
- request ID、去重和幂等规则；
- 超时或进程死亡后如何查询提交状态；
- `oneway` 队列积压时采用丢弃、latest-only 还是可靠送达。

批量接口会减少固定调用开销，却可能放大单次 Parcel、服务端占用 Binder 线程的时间和失败影响面。需要同时测量单项延迟、整批延迟、批大小与失败率，不能只看 IPC 次数下降。

## 12. 指标、采样与告警

### 12.1 一条样本需要哪些字段

建议的低维字段包括：

- `service`、`interface`、`method`：编译期稳定逻辑名；
- `transport`：已知时记录 local/remote，未知就明确写 unknown；
- `mode`：sync/oneway；
- `thread`：main/background/binder；
- `duration_bucket`：直方图桶或原始纳秒值进入本地聚合；
- `outcome`：success、remote_dead、too_large、security、protocol、other；
- `connection_epoch`：仅自有长连接服务；
- `sampled`、`stack_captured`：说明样本如何产生。

异常 message、调用参数、Binder 对象地址、transaction debug ID 和用户标识不应成为聚合维度。

### 12.2 P50/P90/P99 不能只靠慢样本

如果系统只在超过阈值时上报，就只能计算“已知慢调用中的分布”，不能据此得到全量 P50/P90/P99。可采用两条路径：

- 低比例均匀采样，用来估计总体分位数和调用量；
- 超过慢阈值的调用全量进入本地缓冲，用来发现长尾和抓取有限堆栈。

阈值样本要有接口级冷却时间和进程级速率上限，避免同一故障连续生成堆栈。服务死亡率也应以连接 epoch 或死亡通知去重；一次进程死亡可能让许多并发调用同时收到 `DeadObjectException`，不能直接把异常条数当成死亡次数。

### 12.3 推荐告警组合

单一 P99 容易被低调用量放大。更稳妥的告警条件可同时要求：

- 调用量达到最小样本数；
- P99 或慢调用率持续越过接口阈值；
- 主线程样本占比或 ANR/卡顿指标同步升高；
- 同一接口的异常率、连接死亡或服务端执行时间出现对应变化。

告警按逻辑接口聚合，专项分析时再结合版本、设备档位和进程。不要直接按 target PID 建长期 TopN：PID 会复用，也不是普通应用 wrapper 稳定可得的身份。

## 13. 监控代码自身的安全约束

Binder 监控运行在被测调用的关键路径，至少要守住以下边界：

- callback 中不发 Binder、不写同步日志、不访问磁盘和网络；
- 不等待锁竞争激烈的全局 Map；
- 使用固定容量缓冲，并记录 dropped sample 数；
- 上传线程与业务 Binder 线程隔离；
- 样本编码和压缩放到调用结束之后；
- 配置异常时有本地熔断，监控停用不影响业务；
- 采样决策在进入调用前完成，避免慢调用改变被采样概率；
- 保留原异常类型和堆栈，不包装成监控自定义异常。

AOSP 对隐藏的 `ProxyTransactListener` 也明确要求回调快速、支持并发，并强调监听器内绝不能再执行 Binder transaction。应用自建 wrapper 虽不受该接口约束，但递归风险相同：如果 recorder 通过系统服务打日志、取设备信息或立即上传，监控本身就会产生新的 IPC，延迟和样本会互相放大。

## 14. 验收清单

上线前可以用四组实验检查指标含义：

1. **同步慢服务**：服务端分别制造 CPU、锁等待和磁盘延迟，确认 client duration 都会上升，server duration 只覆盖入口后的执行。
2. **`oneway` 积压**：服务端故意降低消费速度，确认客户端时长不能被解释为处理完成，并观察队列与业务 ack。
3. **进程死亡**：在调用前、执行中和回复前终止服务，确认连接 epoch、异常分类和重试规则不会制造重复副作用。
4. **并发大 Parcel**：使用多个中等大小 transaction 施压，确认方案没有把 1MiB 误当单次配额，也不会在线上重复序列化全部参数。

专项设备再采集 Perfetto，把应用样本时间点和 Binder flow 对齐。只有当客户端、服务端和 trace 对同一阶段的定义一致，P99 排行才具备治理价值。

## 参考资料

- [AOSP `Binder.java`（android-17.0.0_r1）](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/os/Binder.java)
- [AOSP `BinderProxy.java`（android-17.0.0_r1）](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/os/BinderProxy.java)
- [AOSP `IBinder.java`（android-17.0.0_r1）](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/os/IBinder.java)
- [AOSP `ServiceManager.java`（android-17.0.0_r1）](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/os/ServiceManager.java)
- [AOSP `StrictMode.java`（android-17.0.0_r1）](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/os/StrictMode.java)
- [AOSP `Debug.java`（android-17.0.0_r1）](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/os/Debug.java)
- [AOSP libbinder `ProcessState.cpp`（android-17.0.0_r1）](https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/libs/binder/ProcessState.cpp)
- [AOSP Binder driver tracepoints（android17-6.18-2026-06_r6）](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/drivers/android/binder_trace.h)
- [AOSP Binder driver（android17-6.18-2026-06_r6）](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/drivers/android/binder.c)
- [Android Developers：查找无响应线程](https://developer.android.com/topic/performance/anrs/find-unresponsive-thread)
- [Android Developers：`TransactionTooLargeException`](https://developer.android.com/reference/android/os/TransactionTooLargeException)
- [Android Developers：`Debug`](https://developer.android.com/reference/android/os/Debug)
- [Perfetto：Android tracing](https://perfetto.dev/docs/learning-more/android)
- [PerfettoSQL standard library：Android Binder](https://perfetto.dev/docs/analysis/stdlib-docs)
