---
title: BluetoothSocket read() 断开语义与长连接治理
chapter: '24.10'
section: '24.10'
status: finalized
applicable_versions: Android 5 (API 21) - Android 17 (API 37)
last_verified: '2026-08-15'
last_verified_against: Android 17 stable behavior changes and API reference 2026-08 / Bluetooth transfer-data and foreground-service guides / AOSP android-17.0.0_r1
confidence: high
tags:
- bluetooth
- io
- network
- android17
- long-connection
related_chapters:
- '11.4'
- '12.1'
- '24.3'
- '26.11'
sources:
- type: official
  path: https://developer.android.com/about/versions/17/behavior-changes-17
- type: official
  path: https://developer.android.com/develop/connectivity/bluetooth/transfer-data
- type: official
  path: https://developer.android.com/reference/android/bluetooth/BluetoothSocket
- type: official
  path: https://developer.android.com/reference/android/bluetooth/BluetoothSocketException
- type: official
  path: https://developer.android.com/guide/app-compatibility/test-debug
- type: official
  path: https://developer.android.com/develop/background-work/services/fgs/service-types#connected-device
- type: aosp
  path: https://android.googlesource.com/platform/packages/modules/Bluetooth/+/refs/tags/android-17.0.0_r1/framework/java/android/bluetooth/BluetoothSocket.java
- type: aosp
  path: https://android.googlesource.com/platform/packages/modules/Bluetooth/+/refs/tags/android-17.0.0_r1/framework/java/android/bluetooth/BluetoothInputStream.java
- type: aosp
  path: https://android.googlesource.com/platform/packages/modules/Bluetooth/+/refs/tags/android-17.0.0_r1/flags/sockets.aconfig
- type: clippings-structure
  path: '[结构参考: Clippings/Android 性能优化 - CPU 优化（上）：合理使用线程池，提升 CPU 利用率.md]'
- type: clippings-structure
  path: '[结构参考: Clippings/Android 性能优化 - 任务调度优化：线程+CPU，提升任务调度优先级.md]'
pipeline_stage: finalized
---

# BluetoothSocket read() 断开语义与长连接治理

阻塞中的 `BluetoothSocket.read()` 以 EOF、异常或数据返回来表达连接状态，业务层不能把任一结果简单等同于可立即重连。可靠长连接需要把读写线程、关闭顺序、状态机和退避预算放在同一套治理中。

## 问题范围与结论边界

`BluetoothSocket` 是 Android 用于蓝牙连接的套接字 API。长连接的一个返回值处理错误，可能同时造成读线程不退出、界面仍显示已连接、旧连接事件覆盖新状态，以及重连反复触发扫描。Android 17 改变了 RFCOMM 输入流结束时的表现，只捕获 `IOException` 的旧代码已经不能覆盖全部退出路径。

RFCOMM（Radio Frequency Communication，射频通信）是经典蓝牙中面向连接的字节流传输，常用于串行端口规范（Serial Port Profile，SPP）。EOF（end of file）是输入流已经没有后续数据的结束标记。低功耗蓝牙面向连接信道（LE Credit-based Connection-Oriented Channel，LE CoC）是另一种蓝牙套接字传输类型。本节保留这些协议和 API 名称，便于与日志、源码及官方文档对照。

需要回答四个工程问题：

- Android 17 的变化由哪些设备版本、目标 SDK 和套接字类型共同触发。目标 SDK（target SDK）是应用声明采用的 Android 行为级别。
- `-1` 能证明什么，以及为什么它不能直接命名为远端正常断开。
- 阻塞的 `connect()`、`read()` 与 `write()` 应怎样取消和分线程。
- 状态机怎样区分关闭意图、流结束、传输错误和过期连接事件。

平台与模块源码以 `android-17.0.0_r1` 标签作为可复现基线，当前公开行为以 Android Developers 文档为准。相关实现位于 `packages/modules/Bluetooth` 的 Java 框架层。应用面对的是 `BluetoothSocket` 公开契约，本节不从 Linux 内核的套接字实现推导额外结论。

## Android 17 的 RFCOMM EOF 语义

[Android 17 行为变更](https://developer.android.com/about/versions/17/behavior-changes-17#bluetooth-rfcomm-socket-change) 给出的范围很明确：

- 设备运行 Android 17。
- 应用的 `targetSdkVersion` 为 37 或更高。
- 输入流来自 RFCOMM `BluetoothSocket`。
- 套接字被关闭或连接丢失后，`read()` 返回 `-1`。

这个变化让 RFCOMM 与 LE CoC 的结束语义都符合 Java `InputStream` 契约。I/O 是输入与输出（input/output）的缩写；其他 I/O 故障仍可抛出 `IOException`，所以兼容代码必须同时处理正数字节数、`-1` 和异常。

这段旧写法用来说明迁移缺口：

```kotlin
while (running) {
    try {
        val count = input.read(buffer)
        onFrame(buffer, count)
    } catch (e: IOException) {
        onDisconnected(e)
        break
    }
}
```

如果 `read()` 返回 `-1`，这段代码会把负数交给协议解析器，并继续下一次循环。它还把每次 `read()` 当成一个业务帧：RFCOMM 是字节流，一次读取可能只得到半帧，也可能同时得到多帧。

### `-1` 只表示流结束

官方契约把两种情况都映射到 `-1`：应用调用 `close()`，以及连接丢失。应用不能只凭 `-1` 区分本地主动关闭、远端主动关闭或连接意外中断。

合理的归因顺序是：

1. 状态机在调用 `close()` 前记录本地关闭意图。
2. 读线程收到 `-1` 或 `IOException` 后，先检查这项意图。
3. 没有本地关闭意图的 `-1` 记为 `EndOfStream`，不要伪装成更精确的远端原因。
4. 结合适配器状态、权限状态、业务心跳和设备侧日志做二次分类。业务心跳是应用协议定期发送的存活探测，只能提供辅助证据。

这段读循环展示关闭意图和流结束的最小安全处理。`onBytes` 获得独立字节数组，适合把数据异步交给协议解析器：

```kotlin
import android.bluetooth.BluetoothSocket
import java.io.IOException
import java.util.concurrent.atomic.AtomicBoolean
import kotlin.io.DEFAULT_BUFFER_SIZE

sealed interface BtReadExit {
    data object LocalClose : BtReadExit
    data object EndOfStream : BtReadExit
    data class IoFailure(val error: IOException) : BtReadExit
}

class BtReadLoop(
    private val socket: BluetoothSocket,
    private val onBytes: (ByteArray) -> Unit,
    private val onCloseFailure: (IOException) -> Unit,
    private val onExit: (BtReadExit) -> Unit,
) : Runnable {
    private val closeRequested = AtomicBoolean(false)

    fun requestClose() {
        closeRequested.set(true)
        try {
            socket.close()
        } catch (e: IOException) {
            onCloseFailure(e)
        }
    }

    override fun run() {
        val reason = try {
            val input = socket.inputStream
            val buffer = ByteArray(DEFAULT_BUFFER_SIZE)
            var terminalReason: BtReadExit? = null

            while (!closeRequested.get()) {
                val count = input.read(buffer)
                if (count < 0) {
                    terminalReason = if (closeRequested.get()) {
                        BtReadExit.LocalClose
                    } else {
                        BtReadExit.EndOfStream
                    }
                    break
                }
                if (count > 0) {
                    onBytes(buffer.copyOf(count))
                }
            }

            terminalReason ?: BtReadExit.LocalClose
        } catch (e: IOException) {
            if (closeRequested.get()) {
                BtReadExit.LocalClose
            } else {
                BtReadExit.IoFailure(e)
            }
        }

        onExit(reason)
    }
}
```

`closeRequested` 是原子布尔值，供关闭线程与读线程安全地共享意图。它必须先更新，再调用 `close()`，这样被 `close()` 终止阻塞的读线程才能看见本地意图。EOF 分支在观察到返回值时保存原因，避免稍后的关闭请求改写已经发生的结果。示例复制有效字节，避免异步消费者继续引用下一次读取会覆盖的数组；高吞吐场景可以改用容量受限、且规定缓冲区归还前只能由一个消费者持有的缓冲池。`onBytes` 应只移交字节且不抛异常，协议解析错误由独立事件返回状态机。`onCloseFailure` 还应触发读线程存活检查，防止关闭失败后线程持续阻塞。

### 源码中的生效条件

这段 `android-17.0.0_r1` 源码用于核对 RFCOMM 负返回值的生效条件，应用无需复制：

```java
@EnabledSince(targetSdkVersion = Build.VERSION_CODES.CINNAMON_BUN)
@ChangeId
static final long MAKE_SOCKET_READ_BEHAVIOR_CONSISTENT = 383671392L;

// BluetoothSocket.read(byte[], int, int)
if (ret < 0) {
    mSocketState = SocketState.CLOSED;
    if (Flags.makeSocketReadBehaviorConsistent()
            && CompatChanges.isChangeEnabled(
                    MAKE_SOCKET_READ_BEHAVIOR_CONSISTENT)
            && SdkLevel.isAtLeastC()) {
        return -1;
    }
    throw new IOException("bt socket closed, read return: " + ret);
}
```

[`BluetoothSocket.java`](https://android.googlesource.com/platform/packages/modules/Bluetooth/+/refs/tags/android-17.0.0_r1/framework/java/android/bluetooth/BluetoothSocket.java) 中，RFCOMM 路径先调用底层 `mSocketIS.read()`。负返回值会先把私有 `mSocketState` 设为 `CLOSED`，再根据 aconfig 特性开关、兼容性变更 383671392 和设备版本选择返回 `-1` 或抛出 `IOException`。aconfig 是 Android 平台声明并生成特性开关的配置机制，`CINNAMON_BUN` 是源码中代表 Android 17 的版本常量。`@EnabledSince` 标在兼容性变更常量上，`read()` 方法本身没有这个注解。

[`BluetoothInputStream.java`](https://android.googlesource.com/platform/packages/modules/Bluetooth/+/refs/tags/android-17.0.0_r1/framework/java/android/bluetooth/BluetoothInputStream.java) 的数组读取直接委托给 `BluetoothSocket.read()`。[`sockets.aconfig`](https://android.googlesource.com/platform/packages/modules/Bluetooth/+/refs/tags/android-17.0.0_r1/flags/sockets.aconfig) 则说明 `make_socket_read_behavior_consistent` 的用途是统一 RFCOMM 与 LE CoC 的 EOF 返回值。

LE CoC 在该源码中已经在接收缓冲为空且底层读到 EOF 时直接返回 `-1`。Android 17 的公开行为变更只承诺 RFCOMM 的新语义，不应从共享实现继续推断同步面向连接（Synchronous Connection-Oriented，SCO）等其他套接字类型的公开契约；SCO 主要承载蓝牙语音数据。

可调试应用可在 Android 17 测试设备上执行这些命令，切换兼容性变更：

```bash
adb shell am compat enable 383671392 com.example.app
adb shell am compat disable 383671392 com.example.app
adb shell am compat reset 383671392 com.example.app
```

前两条命令便于在相同 Android 安装包（APK）上对比新旧分支，测试结束后用 `reset` 清除覆盖。兼容性开关不改变设备系统版本，模块的 aconfig 标志也仍须启用。面向普通用户的公开 user 构建，只允许为可调试应用切换由目标 SDK 门控的变更；其他组合受构建类型和应用是否可调试限制，详见[兼容性框架工具](https://developer.android.com/guide/app-compatibility/test-debug)。

## 读写线程模型与阻塞边界

[Bluetooth 数据传输指南](https://developer.android.com/develop/connectivity/bluetooth/transfer-data) 明确指出，`read(byte[])` 与 `write(byte[])` 都可能阻塞。读取会等待数据、EOF 或异常；远端读取太慢且中间缓冲区已满时，写入也会因流量控制而阻塞。流量控制是接收方根据处理能力限制发送速度的机制。

[`BluetoothSocket` API](https://developer.android.com/reference/android/bluetooth/BluetoothSocket) 还给出两个取消边界：

- `connect()` 会阻塞到连接成功或失败，没有公开的超时参数。
- `BluetoothSocket` 是线程安全的，另一个线程调用 `close()` 会立即中止进行中的操作并关闭套接字。

因此，协程取消或中断 Java 线程本身不足以保证 `connect()`、`read()` 退出。取消处理必须调用同一个 `BluetoothSocket.close()`。连接超时由管理本次连接生命周期的任务执行：到达设定的截止时间后关闭当前套接字；下一次重试创建新的 `BluetoothSocket`，不复用已关闭对象。

状态机是串行接收事件、按规则转换连接状态的组件。一次连接会话可分成四个执行单元：

| 执行单元 | 职责 | 约束 |
| --- | --- | --- |
| 连接任务 | 取消设备发现，执行阻塞的 `connect()` | 不在主线程运行；状态机可通过 `close()` 取消 |
| 读任务 | 独占 `InputStream.read()`，产生字节与退出事件 | 长期占用一个工作线程；不直接修改界面状态 |
| 写队列 | 串行执行 `OutputStream.write()` | 有容量上限、取消策略和单次写入耗时记录 |
| 状态机 | 顺序处理连接、关闭、读写失败和系统事件 | 不执行任何阻塞 I/O |

不要让阻塞读循环与状态机共用一个 `HandlerThread`。`HandlerThread` 是带消息循环（Looper）的线程；`read()` 阻塞期间，它无法处理关闭或超时消息。可以使用独立读线程或由执行器管理的有限 I/O 工作线程，再把事件投递到单线程状态机。活跃连接数量必须受业务限制，因为每个阻塞读循环都会长期占用执行资源。

### RFCOMM 没有业务消息边界

RFCOMM 向应用提供字节流。发送方一次 `write()`，接收方可能经过多次 `read()` 才拿全；接收方的一次 `read()` 也可能包含多条业务消息。协议至少需要一种明确的定界方式，例如长度前缀、分隔符或固定长度字段，并处理这些情况：

- 一次读取只有一条消息的部分内容，常称半包；解析器应把它留在缓冲区，等待后续字节。
- 一次读取包含多条完整消息，常称粘包；解析器应逐条取出。
- 长度字段超过协议上限，按协议错误关闭连接。
- 校验失败、未知消息类型和重复业务序号有确定处理规则。

写入也应串行。即使 `BluetoothSocket` 被文档描述为线程安全，应用协议仍需要稳定的消息顺序，以及明确规定哪些消息允许重发。多个调用方先进入有界队列，即容量固定的等待队列，再由单一写任务写入；队列已满时由产品策略决定拒绝、合并或关闭连接，避免任务无限积压。

`getMaxReceivePacketSize()` 与 `getMaxTransmitPacketSize()` 描述底层传输的包尺寸，可用于优化每次读写大小。它们不定义业务帧长度，也不保证一次读取对应一个底层包。示例中的 `DEFAULT_BUFFER_SIZE` 同样只是内存选择，不是协议常量。

`isConnected()` 只能反映调用时套接字的连接状态，不能保证下一次读写成功。业务在线状态应由当前连接代次、读写结果和协议活性共同决定；协议活性通常来自业务心跳或请求响应是否按时完成。

## 断线归因与状态机

`connected: Boolean` 无法表达关闭意图、失败阶段和是否允许重连。连接事件至少应携带 `connectionId`，即应用为每次连接会话生成的短期唯一标识；每次创建新套接字都生成新值。新值也代表新的连接代次。状态机忽略旧 `connectionId` 的迟到事件，避免旧读线程在新连接成功后又把状态改成离线。

| 事件 | 直接证据 | 状态机处理 |
| --- | --- | --- |
| `LocalCloseRequested` | 业务先记录意图，再调用 `close()` | 进入 `Closing`，禁止自动重连 |
| `EndOfStream` | 无本地关闭意图，`read()` 返回 `-1` | 记录 EOF，按当前重连预算处理 |
| `ReadFailure` | 无本地关闭意图，读取抛 `IOException` | 记录读取阶段与异常类别 |
| `WriteFailure` | 写入抛 `IOException` | 关闭当前套接字，避免继续使用只能读或只能写的连接 |
| `ConnectFailure` | `connect()` 抛 `BluetoothSocketException` 或 `IOException` | API 34 及以上保留 [`BluetoothSocketException.getErrorCode()`](https://developer.android.com/reference/android/bluetooth/BluetoothSocketException)，进入等待或终止 |
| `AdapterOff` | 观察到适配器状态关闭 | 主动关闭当前会话，等待适配器恢复 |
| `PermissionLost` | 新操作前权限检查失败，或调用抛 `SecurityException` | 主动关闭会话，转到授权状态 |
| `ProtocolTimeout` | 协议定义的响应截止时间到达 | 记为协议层事件，关闭套接字后再决定重连 |

`EndOfStream` 不等于远端正常关闭。官方文档把连接丢失也映射到 `-1`，平台没有提供公开的关闭原因。`IOException` 也不应只记一段消息文本；至少保留发生阶段、异常类名、是否存在本地关闭意图和适配器状态。MAC 是蓝牙设备的硬件地址；日志不应包含完整 MAC、设备名或业务负载。

API 34 及以上的 `BluetoothSocketException.getErrorCode()` 提供结构化整数错误码，比异常消息文本更适合聚合；低版本和普通 `IOException` 仍按发生阶段与异常类别记录。Android 12（API 31）及以上的连接操作通常需要 `BLUETOOTH_CONNECT` 运行时权限，扫描还涉及 `BLUETOOTH_SCAN`；不同系统版本应按各自权限模型检查，不能把权限错误记为传输失败。

推荐状态集合见表：

| 状态 | 进入条件 | 允许的出口 |
| --- | --- | --- |
| `Idle` | 没有连接意图 | `Connecting` |
| `Connecting` | 新套接字正在执行 `connect()` | `Connected`、`Backoff`、`Idle`、`PermissionRequired`、`AdapterOff` |
| `Connected` | 连接成功且读写任务已启动 | `Closing`、`Backoff`、`PermissionRequired`、`AdapterOff` |
| `Closing` | 已记录本地关闭意图 | `Idle` |
| `Backoff` | EOF、连接失败、读写失败或协议超时 | `Connecting`、`Idle`、`PermissionRequired`、`AdapterOff` |
| `PermissionRequired` | 缺少 `BLUETOOTH_CONNECT` 等所需权限 | `Idle`、`Connecting` |
| `AdapterOff` | Bluetooth 适配器关闭 | `Idle`、`Connecting` |

所有迁移由单线程状态机执行。读任务、写任务、界面、权限回调和适配器广播只提交事件，不直接写共享状态。状态机对每个 `connectionId` 只接受一个终止结果，并在进入终止状态时关闭读写入口。

这里还要处理两个常见竞态：

- 本地关闭与远端掉线同时发生时，以状态机已经记录的本地意图为归因依据，不宣称知道无线连接事件的先后顺序。
- 新连接已经进入 `Connected` 后，旧连接的 `EndOfStream` 或 `ReadFailure` 只能清理旧资源，不能影响当前连接。

## 重连等待要有预算

重连开始前，状态机要同时满足四个条件：业务仍希望保持连接、必要权限仍在、Bluetooth 适配器已开启、当前预算允许重试。任一条件不成立都应停止，后台计时器也不得继续创建套接字。状态表中的 `Backoff` 就是失败后等待下一次连接的阶段。

建议分别配置这些预算：

| 预算 | 建议记录 | 用途 |
| --- | --- | --- |
| 单次连接截止时间 | `connect_deadline_ms`、`connect_duration_ms` | 到期后由连接生命周期管理任务调用 `close()` 取消阻塞连接 |
| 会话重试次数 | `attempt_index`、`attempt_limit` | 限制一次用户连接意图内的尝试数量 |
| 总时间窗口 | `retry_window_ms`、`elapsed_in_window_ms` | 限制持续失败占用的总时间 |
| 扫描 | `scan_reason`、`scan_duration_ms`、`scan_attempts` | 区分重连扫描与用户主动配网 |
| 写入重放 | `pending_request_count`、`replay_decision` | 只重放协议允许且幂等的请求 |

等待时间可以使用有上限的指数退避：每次失败后成倍延长等待，但不超过设定上限。再加入少量随机时间偏移，也就是重连抖动，可以减少多台设备或大量客户端同时发起连接。初始等待、上限和尝试次数属于产品参数，应由设备类型、前后台状态和用户等待预期决定。连接刚成功时不要立即清零失败计数；等连接持续稳定或完成一次有效业务交换后再重置，更能减少短连接反复建立和断开。

对已配对且地址已知的经典蓝牙（Bluetooth Classic）设备，断线后通常可以直接创建新的 RFCOMM 套接字。全量设备发现会扫描周围设备，不应成为每次重连的固定前置步骤。确需发现设备时，应带过滤条件、截止时间和停止条件，并把原因标记为 `reconnect`。执行 `connect()` 前还要调用 `BluetoothAdapter.cancelDiscovery()`；官方 API 文档说明，进行中的设备发现会显著拖慢新连接。

协议层也要决定断线后的数据处理：

- 已写入不等于远端已经处理，不能按写成功盲目重放。
- 请求携带业务序号或幂等键，重连后由双方确认进度。幂等键是用于识别同一业务请求的唯一标识，使重复提交可以复用已有结果。
- 不能安全重复执行的操作，需要先查询结果或让用户确认。
- 旧连接写队列中的任务不能自动转移到新 `connectionId`。

### 后台连续连接

应用需要在后台持续与外部设备传输数据时，应按场景评估 `connectedDevice` 前台服务或配套设备管理器（Companion Device Manager）。普通后台线程本身不会提高进程被系统保留的优先级。[前台服务类型文档](https://developer.android.com/develop/background-work/services/fgs/service-types#connected-device) 要求 Android 14 及以上在服务上声明 `android:foregroundServiceType="connectedDevice"`，并在清单中声明 `FOREGROUND_SERVICE_CONNECTED_DEVICE` 权限。启动服务时还要满足文档列出的至少一项运行前提；已经授予 `BLUETOOTH_CONNECT` 可满足蓝牙连接场景的这一条件。

前台服务只影响进程执行条件，不改变 `BluetoothSocket.read()` 的 EOF 语义，也不允许无限扫描和重连。用户主动断开、权限撤销或预算用尽后，应停止连接任务和不再需要的前台服务。若使用配套设备管理器，还要按设备进入或离开通信范围的事件设计恢复流程，不能假设旧套接字会跨进程存活。

## 性能与功耗监控字段

Bluetooth 套接字指标应与 HTTP 指标分开，单独保留传输类型与失败阶段。每个事件记录原始耗时，分位数在聚合系统中计算。`p50` 是中位数，`p95` 是 95% 样本不超过的值；它们是多条样本的统计结果，不是单次事件字段。

| 类别 | 事件字段 | 用途 |
| --- | --- | --- |
| 版本 | `sdk_int`、`target_sdk`、`build_fingerprint_group` | 验证 Android 17 与目标 SDK 边界 |
| 连接 | `connection_id`、`socket_type`、`connect_duration_ms`、`connect_result` | 区分 RFCOMM、LE CoC 和连接阶段 |
| 读取 | `read_exit_reason`、`bytes_read`、`reader_lifetime_ms` | 发现 EOF 漏处理、异常和未退出线程 |
| 写入 | `write_bytes`、`write_duration_ms`、`write_result`、`queue_depth` | 观察流量控制、队列压力和失败 |
| 重连 | `attempt_index`、`backoff_ms`、`retry_stop_reason` | 检查退避与预算是否执行 |
| 扫描 | `scan_reason`、`scan_duration_ms`、`filter_present` | 与 11.4 的扫描功耗分析关联 |
| 系统 | `adapter_state`、`permission_state`、`app_importance`、`battery_saver` | 区分系统状态与传输失败 |

遥测是应用自动采集并上报的运行指标。`connection_id` 应是应用生成的短期随机标识。若必须按设备族聚合，优先上传非唯一的产品型号或固件大版本；需要识别同一设备产生的重复事件时，使用定期更换的密钥生成仅在指定业务范围内有效、且不能还原设备地址的标识。`build_fingerprint_group` 也应是粗粒度构建分组，不能上传完整构建指纹。完整 MAC、设备名、广播负载和业务数据都不应进入遥测。

Perfetto 是 Android 的系统跟踪工具，BatteryStats 统计设备电量使用；二者结合应用跟踪，可以核对断线后的线程、唤醒锁、扫描和重连是否仍在运行。Perfetto 中的 Bluetooth 与电源时间轴随设备实现变化，测试脚本应先枚举当前设备可用数据源，再选择分析字段，不依赖某一台设备的时间轴名称。

观测结论还要区分没有业务数据和读线程已经退出。空闲连接可能长时间阻塞在 `read()`，这本身不是线程泄漏；本地关闭后仍未退出，或连接换代后旧线程仍存活，才是需要告警的异常。

## Android 17 适配测试表

测试必须在 Android 17 设备上同时覆盖设备版本、目标 SDK、兼容性开关和断开来源。表中的 `sdk_int` 表示设备 API 级别，`target_sdk` 表示应用的目标 SDK。

| 维度 | 覆盖项 | 通过标准 |
| --- | --- | --- |
| 目标 SDK | 36、37 | 36 的旧异常分支与 37 的 EOF 分支都能终止读任务 |
| 兼容性开关 | `targetSdkVersion 36` 强制启用、`targetSdkVersion 37` 强制禁用、重置默认值 | 相同 APK 可隔离 383671392 的影响，测试后没有遗留覆盖 |
| 套接字类型 | RFCOMM、LE CoC | RFCOMM 处理新 EOF；LE CoC 原有 EOF 行为没有回归 |
| 本地关闭 | 用户断开、会话销毁、连接超时取消 | 先记录关闭意图，结果为 `LocalClose`，不触发自动重连 |
| 远端与无线连接 | 对端关闭、对端进程退出、设备关机、距离与干扰 | `EndOfStream` 或 `IoFailure` 都能终止当前连接 |
| 连接换代 | 旧连接退出延迟到新连接成功之后 | 旧 `connectionId` 事件不能修改新连接状态 |
| Bluetooth 状态 | 手动关闭和重新开启适配器 | 关闭时停止连接与扫描，恢复后按业务意图决定是否连接 |
| 飞行模式 | Bluetooth 随飞行模式关闭、用户在飞行模式中重新开启 Bluetooth | 以实际适配器状态为准，不把飞行模式直接等同于 Bluetooth 关闭 |
| 权限 | 启动前拒绝、连接期间撤销、重新授权 | 不循环请求或重连；授权后创建新套接字 |
| 后台执行 | 进入后台、停止前台服务、进程被系统终止 | 状态与通知一致，恢复流程不复用失效套接字 |
| 写入阻塞 | 对端暂停读取、写队列达到容量限制 | 主线程不阻塞，截止时间和拒绝策略生效 |
| 协议分帧 | 半包、粘包、超长长度、校验失败 | 解析器不把一次 `read()` 当作一帧，错误路径可关闭会话 |

每个用例至少记录 `sdk_int`、`target_sdk`、兼容性开关状态、`connection_id`、`read_exit_reason` 和重试终止原因。远端关闭在不同蓝牙控制器芯片、固件和时序下可能表现为 EOF 或异常，断言应检查状态机结果，不固定要求某一种底层表现。

## 与相邻章节的边界

11.4 节负责 Bluetooth 扫描、连接和功耗分析。这里仅在断线扫描、重连预算和套接字线程处引用 11.4，不重复低功耗蓝牙（Bluetooth Low Energy，BLE）的扫描限制。

24.3 节负责公网请求的弱网处理和重试预算。Bluetooth 套接字可以复用失败分类、安全重试规则和总时间预算，但错误仍需独立建模，不能归入 HTTP 的 DNS、连接或读取超时。

26.11 节负责线上网络质量监控。Bluetooth 套接字应作为独立通道上报，原始事件保留 `socket_type`、`read_exit_reason`、`connection_id` 和 `retry_stop_reason`。

## 检查清单

- `InputStream.read()` 同时处理正数字节数、`-1` 和 `IOException`。
- 不把 `-1` 直接命名为远端正常关闭；本地关闭意图在 `close()` 前记录。
- `connect()`、`read()`、`write()` 都不在主线程或界面回调中执行。
- 取消协程或线程时会调用同一套接字的 `close()`，连接超时后创建新套接字。
- RFCOMM 解析器支持半包、粘包和非法长度，不依赖单次 `read()` 划分消息。
- 写入使用有界串行队列，并记录写入耗时、队列深度和失败阶段。
- 每次连接使用新 `connectionId`，旧连接迟到事件不会覆盖当前状态。
- 重连有连接、次数、总时间、扫描和数据重放预算。
- Bluetooth 关闭、权限撤销、用户断开和预算耗尽都会停止重连。
- Android 17 / API 37 用例覆盖默认分支与兼容性开关对照。
- 遥测不上传完整 MAC、设备名、广播负载或业务数据。

## 全文小结

Android 17 在 `targetSdkVersion 37` 下让 RFCOMM 输入流在套接字关闭或连接丢失时返回 `-1`，应用仍要保留 `IOException` 路径。`-1` 只能证明输入流结束，不能单独证明远端主动关闭。

可靠实现需要把本地关闭意图、EOF、I/O 失败和系统状态转换为带 `connectionId` 的状态机事件。阻塞读写放在独立工作线程，取消动作通过 `BluetoothSocket.close()` 完成；协议解析负责消息边界，重连负责预算、幂等和后台执行条件。这样 Android 17 的返回值变化只影响传输适配层，不会让界面状态、重连和业务重放各自猜测断开原因。
