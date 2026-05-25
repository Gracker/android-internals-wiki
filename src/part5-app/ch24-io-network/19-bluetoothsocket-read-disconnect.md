---
title: "BluetoothSocket read 断开语义与长连接治理"
chapter: "24.19"
section: "24.19"
status: ready-for-review
drafted_date: "2026-05-25"
drafted_by: "openclaw-task2a"
applicable_versions: "Android 5 (API 21) - Android 17 (API 37)"
last_verified: "2026-05-25"
last_verified_against: "Android Developers Android 17 behavior changes / Bluetooth transfer-data guide 2026-05-25; AOSP packages/modules/Bluetooth refs/heads/main"
confidence: medium
tags: [bluetooth, io, network, android17, long-connection]
related_chapters: ["11.6", "12.2", "24.4", "24.14"]
created_by: "task2a-knowledge-gap"
created_date: "2026-05-25"
gap_source: "官方文档/Android17行为变更/Part5结构参考"
gap_score: 18
material_count: 4
sources:
  - type: official
    path: "https://developer.android.com/about/versions/17/behavior-changes-17"
  - type: official
    path: "https://developer.android.com/develop/connectivity/bluetooth/transfer-data"
  - type: official
    path: "https://developer.android.com/reference/android/bluetooth/BluetoothSocket"
  - type: aosp
    path: "packages/modules/Bluetooth/framework/java/android/bluetooth/BluetoothSocket.java"
  - type: clippings-structure
    path: "[结构参考: Clippings/Android 性能优化 - CPU 优化（上）：合理使用线程池，提升 CPU 利用率.md]"
  - type: clippings-structure
    path: "[结构参考: Clippings/Android 性能优化 - 任务调度优化：线程+CPU，提升任务调度优先级.md]"
---

# 24.19 BluetoothSocket read 断开语义与长连接治理

<!-- outline-start -->
## 要点

### 🔹 Android 17 RFCOMM `read()` 返回值变化
梳理 Android 17 面向 `targetSdkVersion >= 37` 的 Bluetooth RFCOMM socket 行为：远端断开或 socket 关闭时，`InputStream.read()` 可返回 `-1`，应用不能只依赖 `IOException` 退出读循环。

### 🔹 读写线程模型与阻塞边界
结合官方 Bluetooth 数据传输文档，说明 `read(byte[])` 和 `write(byte[])` 都可能阻塞，读循环需要专用线程、明确退出条件和可观测状态，不把阻塞等待放进主线程或 UI 回调。

### 🔹 断线归因与状态机
区分主动关闭、远端断开、链路丢失、权限撤销、蓝牙关闭和协议层心跳超时，把 `-1`、`IOException`、业务超时和用户操作分别映射到状态机事件。

### 🔹 长连接重连与退避策略
设计重连预算、指数退避、用户可见状态、前后台切换策略和设备重发现边界，避免断线后立即高频扫描或无限重连。

### 🔹 性能与功耗监控字段
给出连接时长、读循环退出原因、重连次数、扫描时长、线程存活、写入阻塞耗时和蓝牙功耗归因字段，和 11.6 的蓝牙扫描功耗章节建立引用关系。

### 🔹 Android 17 适配测试表
覆盖 targetSdk 36/37、经典蓝牙 RFCOMM、LE CoC、远端主动断开、本地关闭 socket、飞行模式、蓝牙开关、后台限制和弱信号场景。

## 扩展

### 🔸 与 11.6 Bluetooth 功耗章节的边界
11.6 负责扫描、连接和后台功耗；本节聚焦 socket 读写语义、断线状态机和长连接治理。

### 🔸 与 24.14 弱网治理的关系
Bluetooth 不是蜂窝或 Wi-Fi 弱网，但重连退避、请求分段和状态上报可以复用 24.14 的治理框架。

### 🔸 与 26.17 线上网络质量监控的关系
线上监控需要把 Bluetooth socket 断开归入独立通道，不混入 HTTP 错误率或公网弱网指标。

<!-- outline-end -->

Bluetooth 长连接的问题通常不是“连不上”这么简单。读线程退不出来、业务状态还显示在线、重连循环把扫描和连接拉满、后台还在持有前台服务，这些问题都落在 `BluetoothSocket` 的读写语义和状态机设计上。

Android 17 给 RFCOMM `BluetoothSocket` 补了一条兼容性边界：`targetSdkVersion >= 37` 时，socket 关闭或连接断开后，RFCOMM `InputStream.read()` 可以返回 `-1`。老代码如果只在 `catch IOException` 里退出读循环，就有机会在 Android 17 上漏掉 EOF 分支。 [已验证: 官方文档, developer.android.com/about/versions/17/behavior-changes-17]

参考书只用于组织本节的工程顺序：IO 等待要移出主流程，线程池要按任务类型收口，重要任务要有线程名、优先级和拒绝策略。正文不使用参考书原文和代码。 [结构参考: Clippings/Android 性能优化 - CPU 优化（上）：合理使用线程池，提升 CPU 利用率.md] [结构参考: Clippings/Android 性能优化 - 任务调度优化：线程+CPU，提升任务调度优先级.md]

## Android 17 的 RFCOMM EOF 语义

Android Developers 的 Android 17 行为变更页面把范围限定得很清楚：对象是 RFCOMM-based `BluetoothSocket` 的 `InputStream`；触发条件是 socket 被关闭或连接丢失；影响对象是 `targetSdkVersion >= 37` 的 App；返回值从“只靠 `IOException` 感知断开”扩展为“`read()` 可能返回 `-1`”。官方文档同时说明，这个变化让 RFCOMM 与 LE CoC socket、Java `InputStream.read()` 的 EOF 约定保持一致。 [已验证: 官方文档, developer.android.com/about/versions/17/behavior-changes-17]

旧写法的问题在于退出条件太窄：

```kotlin
while (running) {
    try {
        val size = input.read(buffer)
        onFrame(buffer, size)
    } catch (e: IOException) {
        onDisconnected(e)
        break
    }
}
```

这段代码只把异常当成断开信号。Android 17 上如果 `read(buffer)` 返回 `-1`，`onFrame(buffer, -1)` 会进入业务解析层。轻则记录一条无意义的空包，重则状态机继续停在 connected，读线程还会再次进入循环。

读循环要同时处理正常字节、EOF 和异常：

```kotlin
class BtReadLoop(
    private val socket: BluetoothSocket,
    private val onBytes: (ByteArray, Int) -> Unit,
    private val onExit: (BtExitReason) -> Unit,
) : Runnable {
    @Volatile private var localClosing = false

    fun requestClose() {
        localClosing = true
        socket.close()
    }

    override fun run() {
        val input = socket.inputStream
        val buffer = ByteArray(1024)

        try {
            while (!localClosing) {
                val count = input.read(buffer)
                if (count == -1) {
                    onExit(BtExitReason.RemoteEof)
                    return
                }
                if (count > 0) {
                    onBytes(buffer, count)
                }
            }
            onExit(BtExitReason.LocalClose)
        } catch (e: IOException) {
            val reason = if (localClosing) BtExitReason.LocalClose else BtExitReason.TransportError(e)
            onExit(reason)
        }
    }
}
```

这段代码的用途是把平台返回值先归一成业务事件。`RemoteEof` 表示对端断开或 socket 关闭后读到流结束；`LocalClose` 表示业务主动关闭；`TransportError` 承接旧版本、链路错误和栈内异常。后续状态机只消费 `BtExitReason`，不直接依赖 `read()` 的平台差异。

AOSP `packages/modules/Bluetooth` main 分支当前公开文件中仍能看到 legacy read path 的异常分支：`BluetoothSocket.read(byte[], int, int)` 在默认路径下读取 `mSocketIS`，负返回值会走 `IOException`。Android 17 官方文档已经给出 API 37 行为契约，但公开 main 分支与最终 Android 17 tag 之间仍需按发布 tag 复核。本文按官方兼容性文档适配，源码实现细节标为待复核。 [待验证: AOSP android-17 tag 发布后复核 packages/modules/Bluetooth/framework/java/android/bluetooth/BluetoothSocket.java]

## 读写线程模型与阻塞边界

Bluetooth 官方数据传输文档给出的读写模型很直接：通过 `getInputStream()` 和 `getOutputStream()` 拿到 socket 流，用 `read(byte[])` 和 `write(byte[])` 收发数据；`read(byte[])` 会阻塞到有数据可读，`write(byte[])` 通常不阻塞，但远端读得太慢、中间缓冲区满时也会因为 flow control 阻塞。官方文档因此要求使用专用线程处理流读写。 [已验证: 官方文档, developer.android.com/develop/connectivity/bluetooth/transfer-data]

`BluetoothSocket` API 文档还给了两条工程边界：`connect()` 会阻塞到连接成功或失败；`close()` 会立即中止正在进行的操作并关闭 socket。 [已验证: 官方文档, developer.android.com/reference/android/bluetooth/BluetoothSocket]

落到 App 侧，线程模型建议分成三层：

| 线程/队列 | 职责 | 不该做什么 |
|---|---|---|
| 连接线程 | 执行 `connect()`、取消 discovery、输出连接结果 | 不承载业务解析，不在 UI 回调里同步连接 |
| 读线程 | 独占 `InputStream.read()`，把字节转成帧或包 | 不直接改 UI，不吞掉 `-1` 和异常 |
| 写队列 | 串行写 `OutputStream.write()`，记录写入阻塞耗时 | 不让多个业务线程并发写同一个 socket |

读线程要有稳定命名，例如 `bt-rfcomm-read-$deviceIdHash`。线程池可以复用参考书里的 IO 任务分离原则，但不要把 Bluetooth 读循环丢进一个无限扩张的通用 IO 池。长连接读循环是长期占位任务，更适合独立 `HandlerThread`、单线程 executor 或受控的连接会话线程；普通文件 IO、网络请求、图片解码不应该和它争同一个无界队列。

写入侧也要串行化。RFCOMM 是流式传输，业务层如果从多个线程同时 `write()`，包边界只能靠自己的协议恢复。更稳的做法是所有写请求进同一个队列，由写线程按顺序写出，同时记录每次写入的字节数、耗时和失败原因。对于 request/response 协议，还要给每个请求分配业务序号，断线后按幂等规则决定是否重发。

`getMaxReceivePacketSize()` 和 `getMaxTransmitPacketSize()` 可用于了解底层传输支持的收发包上限。API 文档说明，读取可能最多返回该 receive packet size，部分 transport 会按其倍数返回；发送侧可以用 transmit packet size 避免发送半空 packet。 [已验证: 官方文档, developer.android.com/reference/android/bluetooth/BluetoothSocket] 工程里不要把 `1024` 当成协议事实，它只是缓冲区选择；业务包长仍要由自己的 framing 处理。

## 断线归因与状态机

Bluetooth 长连接不能只维护一个 `connected: Boolean`。至少要把“谁关闭的”“怎么感知的”“是否允许重连”拆开。

| 事件 | 典型证据 | 状态机输入 | 默认动作 |
|---|---|---|---|
| 用户主动断开 | 用户点击断开、页面销毁、业务调用 `close()` | `LocalClose` | 停止读写线程，不自动重连 |
| 远端正常断开 | Android 17 RFCOMM `read()` 返回 `-1` | `RemoteEof` | 标记离线，按业务策略决定重连 |
| 传输异常 | `IOException`、connect failed、write failed | `TransportError` | 记录错误码/消息，进入退避重连 |
| Bluetooth 关闭 | 系统 Bluetooth 状态广播、后续调用失败 | `AdapterOff` | 停止扫描和重连，等待用户打开 |
| 权限撤销 | `BLUETOOTH_CONNECT` 不再可用，调用抛安全异常或前置检查失败 | `PermissionLost` | 切到需要授权状态，不重连 |
| 协议心跳超时 | 业务心跳 N 次未收到 ACK | `HeartbeatTimeout` | 主动关闭 socket，再进入退避 |
| 弱信号/链路抖动 | 重连成功率低、RSSI 下降、短时间多次断开 | `UnstableLink` | 降低发送频率，延长退避 |

`RemoteEof` 和 `TransportError` 的处理不要完全一样。`RemoteEof` 更像流结束，日志里应记录为 EOF；`IOException` 可能来自底层 socket 错误、本地关闭 race、Bluetooth 关闭、权限或栈内失败。把两者都写成 `IOException: disconnected`，后续线上看板会失去 Android 17 适配价值。

一个可执行的状态集合如下：

| 状态 | 进入条件 | 允许的出口 |
|---|---|---|
| `Idle` | 无连接任务 | `Connecting` |
| `Connecting` | 开始 `connect()` | `Connected`、`Backoff`、`Idle` |
| `Connected` | socket 已连接，读写线程已启动 | `Closing`、`Backoff`、`PermissionRequired`、`AdapterOff` |
| `Closing` | 本地关闭中 | `Idle` |
| `Backoff` | 远端 EOF、传输异常、心跳超时 | `Connecting`、`Idle` |
| `PermissionRequired` | 连接权限缺失 | `Idle`、`Connecting` |
| `AdapterOff` | Bluetooth 关闭 | `Idle`、`Connecting` |

状态迁移要单线程执行，避免读线程、写线程、UI 线程、Bluetooth 广播接收器同时改连接状态。可以把所有事件投递到一个 connection actor 或 `HandlerThread`，由它顺序处理。

## 重连退避要带预算

Bluetooth 断开后立即扫描、立即连接、失败后再立即扫描，是长连接最常见的耗电来源。11.6 节已经覆盖扫描、连接和后台功耗；本节只给 socket 断线后的策略边界。

建议把重连拆成四个预算：

| 预算 | 示例字段 | 作用 |
|---|---|---|
| 单次连接预算 | `connect_timeout_ms`、`service_discovery_timeout_ms` | 防止一次连接卡住整条状态机 |
| 重试次数预算 | `retry_count_in_session`、`max_retry_count` | 防止无限重连 |
| 时间窗口预算 | `first_disconnect_elapsed_ms`、`retry_window_ms` | 防止短时间请求风暴 |
| 扫描预算 | `scan_duration_ms`、`scan_count_after_disconnect` | 防止断线后高频扫描 |

退避建议用“前台短、后台长、失败越多越长”的模型。前台用户正在等待时，可以在 1s、2s、4s 这类短间隔内试几次；用户离开页面或应用进入后台后，重连间隔要拉长，必要时改成事件唤醒或等待下次用户打开页面。具体阈值要按设备类型和业务期望配置，不能写死在 SDK 里。

设备重发现也要分清楚。已配对设备或已知地址的经典 Bluetooth 连接，不应该每次断线都从无过滤扫描开始；BLE 设备或配网设备需要扫描时，要复用 11.6 节的规则：短时、带 filter、有停止条件。断线后的扫描要记录来源为 reconnect，不要混入用户主动配网的扫描指标。

## 性能与功耗监控字段

线上监控要把 Bluetooth socket 独立出来，不要混进 HTTP 错误率，也不要只上报一条 `disconnect`。最小字段集如下：

| 类别 | 字段 | 用途 |
|---|---|---|
| 版本边界 | `sdk_int`、`target_sdk`、`socket_type`、`transport` | 区分 Android 17 RFCOMM、LE CoC 和旧版本 |
| 连接身份 | `device_hash`、`profile`、`paired`、`foreground` | 保护隐私，同时保留设备类别 |
| 读循环 | `read_exit_reason`、`bytes_read`、`read_thread_alive_ms` | 判断 EOF、异常、本地关闭和线程泄漏 |
| 写入 | `write_bytes`、`write_block_ms_p50/p95`、`write_error` | 判断远端不读或缓冲区压力 |
| 重连 | `retry_count`、`backoff_ms`、`reconnect_result` | 判断请求风暴和恢复率 |
| 扫描 | `scan_after_disconnect_ms`、`scan_filter_present` | 和 11.6 的扫描功耗归因关联 |
| 系统状态 | `adapter_state`、`permission_state`、`battery_saver`、`background_restricted` | 区分系统约束和链路异常 |

`device_hash` 不要上传完整 MAC、设备名和原始广播 payload。需要排查特定设备族时，用本地白名单映射成设备类型或固件大版本，线上只保留 hash 和类别。

Perfetto 和 BatteryStats 适合验证“断线后是否还在耗电”。抓取时把应用线程、wakelock、Bluetooth 相关轨道、power rails 和重连日志放在同一时间范围内看。Bluetooth 专用事件和 power rail 命名依赖设备，不能把某台 Pixel 的轨道名写成通用脚本条件。 [待验证: Perfetto Bluetooth 事件与 power rail 命名需按实机确认]

## Android 17 适配测试表

适配测试要覆盖 target SDK 差异和断开来源。只测“正常连接后能收发”不够。

| 维度 | 覆盖项 | 通过标准 |
|---|---|---|
| target SDK | 36、37 | 36 兼容旧异常路径；37 下 `-1` 和异常都能退出 |
| socket 类型 | RFCOMM、LE CoC | RFCOMM 适配 Android 17 EOF；LE CoC 不被回归破坏 |
| 本地关闭 | UI 断开、页面销毁、进程退出前关闭 | 读线程退出原因为 `LocalClose`，不自动重连 |
| 远端关闭 | 对端正常 close、对端进程退出、设备关机 | `RemoteEof` 或传输异常均能进入离线状态 |
| 系统状态 | Bluetooth 开关、飞行模式、权限撤销 | 停止扫描和重连，用户可见状态准确 |
| 后台限制 | 后台、低电量、前台服务关闭 | 重连频率降低，扫描预算生效 |
| 弱信号 | 远距离、遮挡、干扰 | 退避生效，不出现高频扫描和连接风暴 |
| 写阻塞 | 远端暂停读取、大包发送 | 写队列有超时/取消策略，UI 不阻塞 |

测试日志要同时记录 `target_sdk`、`read_exit_reason`、`retry_count` 和 `scan_after_disconnect_ms`。Android 17 的回归判定要覆盖断开后读线程退出、状态机迁移、重连预算和用户状态一致性；只验证没有 crash 还不够。

## 与相邻章节的边界

11.6 节负责 Bluetooth 扫描、连接和功耗归因。本节只在断线后扫描、重连预算和 socket 读写线程处引用 11.6，不重复写 BLE 扫描限制和 BatteryStats 归因。

24.14 节负责网络请求分段、弱网治理和重试预算。本节复用“失败类型、幂等性、总耗时预算”的治理方式，但 Bluetooth socket 的失败类型要独立建模，不能归入 HTTP DNS/connect/read timeout。

26.17 节负责线上网络质量监控。Bluetooth socket 应作为独立通道上报，字段和 HTTP 请求分开。统一看板可以合并到“连接质量”层，但原始指标要保留 `socket_type`、`read_exit_reason` 和 `reconnect_result`。

## 检查清单

- `InputStream.read()` 同时处理正数字节数、`-1` 和 `IOException`。
- 本地关闭和远端断开分别上报，不共用一个 `disconnect` 文案。
- `connect()`、`read()`、`write()` 都不在主线程或 UI 回调中执行。
- 写入走串行队列，记录写入阻塞耗时和失败原因。
- 重连有次数、时间窗口、扫描和前后台预算。
- Bluetooth 关闭、权限撤销和低电量状态不会触发无限重连。
- Android 17 target SDK 37 有专门测试用例，验证 RFCOMM `read()` 返回 `-1`。
- 线上监控字段保护设备隐私，不上传完整 MAC、设备名和原始 payload。
