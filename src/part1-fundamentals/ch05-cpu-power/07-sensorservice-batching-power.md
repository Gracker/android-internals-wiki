---
title: SensorService 与传感器批处理功耗模型
chapter: '5.7'
section: '5.7'
status: finalized
applicable_versions: Android 4.4 (API 19) - Android 17 (API 37)
last_verified: '2026-10-27'
last_verified_against: AOSP android-17.0.0_r1 + Android Source sensors docs
last_source_verified_at: '2026-10-27'
last_idle_audit_at: '2026-10-27'
confidence: medium-high
sources:
- type: official
  path: https://source.android.com/docs/core/interaction/sensors/batching
- type: official
  path: https://source.android.com/docs/core/interaction/sensors/suspend-mode
- type: official
  path: https://source.android.com/docs/core/interaction/sensors/sensor-stack
- type: official
  path: https://source.android.com/docs/core/interaction/sensors/sensors-hal2
- type: official
  path: https://source.android.com/docs/core/interaction/sensors/sensors-aidl-hal
- type: aosp
  path: frameworks/base/core/java/android/hardware/SensorManager.java
- type: aosp
  path: frameworks/base/core/java/android/hardware/SystemSensorManager.java
- type: aosp
  path: frameworks/native/services/sensorservice/SensorService.cpp
- type: aosp
  path: frameworks/native/services/sensorservice/SensorDevice.cpp
- type: aosp
  path: frameworks/native/services/sensorservice/SensorEventConnection.cpp
tags:
- sensorservice
- sensors
- power
- batching
- cpu-wakeup
related_chapters:
- '5.2'
- '11.2'
- '25.4'
- '15.5'
---

# SensorService 与传感器批处理功耗模型

SensorService 的功耗问题常被简化为“采样频率越低越省电”，但这只覆盖传感器本体的一部分成本。

一次传感器请求可能使用传感器中枢（sensor hub，用低功耗处理器代替主处理器收集和处理传感器数据）及其先进先出缓冲区（First In, First Out，FIFO），还可能唤醒应用处理器（Application Processor，AP），并让 `system_server`（承载 Android 核心系统服务的进程）、原生 SensorService 和应用回调线程参与数据交付。Sensor hub 是可选组件，部分 sensor 也可以绕过它；硬件 FIFO 与 hub 缓冲能力需要按设备查询。

本文按照 Android 17 / API 37 / `android-17.0.0_r1` 核对源码，分析采样周期、批量延迟、唤醒（wake-up）属性、多客户端请求聚合和 AP 挂起（suspend）之间的关系。

版本沿革只保留理解当前行为所需的节点：Android 4.4 引入标准化的批处理（batching），API 26 增加 Sensor Direct Channel，Android 12 对部分运动 / 姿态传感器增加高采样率限制；Android 17 继续保留这些机制，并增加由功能开关（flag）控制的冻结进程（frozen-PID）处理路径。

## 传感器耗电来自三个位置

一次传感器请求的成本可以分成三处，它们的影响因素和优化手段并不相同：

<!-- gracker-diagram: ch05-07-three-power-costs -->
![传感器功耗的三个位置](../../assets/diagrams/ch05/ch05-07-three-power-costs.png)

图：Batching 主要合并交付与 AP 唤醒，不会自动降低传感器采样量。元数据 getPower() 是厂商估算电流，不能代替本次场景实测能量。

| 成本 | 发生位置 | 主要影响因素 | 常见误判 |
|---|---|---|---|
| 采样与计算 | 微机电系统（MEMS）、模数转换器（ADC）、sensor hub、融合算法 | 采样频率、传感器类型、融合复杂度 | 只看应用回调次数 |
| 缓冲与搬运 | hub 的静态随机存取内存（SRAM）、硬件 FIFO、HAL 快速消息队列（FMQ）、SensorService 队列 | FIFO 深度、事件大小、共享方式 | 认为 batching 会减少采样 |
| AP 唤醒与处理 | 片上系统（SoC）从低功耗状态恢复（resume）、SensorService、应用线程 | wake-up 属性、批量窗口、回调工作量 | 认为低频一定等于少唤醒 |

对于连续型传感器（continuous sensor），采样频率与采样周期可以互相换算：

```text
frequency_hz ≈ 1_000_000 / samplingPeriodUs
```

公式中的 `samplingPeriodUs` 以微秒为单位，因此只有**增大**它才会降低请求频率。例如，20,000 µs 约为 50 Hz，200,000 µs 约为 5 Hz。

硬件通常只支持若干离散的输出数据率（Output Data Rate，ODR），硬件抽象层（Hardware Abstraction Layer，HAL）会将请求映射到可用档位；`SensorManager` 也将采样周期定义为提示值（hint），应用不能假定回调严格等间隔到达。

`Sensor.getPower()` 返回厂商写入传感器元数据（sensor metadata）的估算电流，适合粗略比较传感器类型，但不是针对当前频率和设备状态的实时功耗测量值。

## 先区分上报模式（reporting mode）

`samplingPeriodUs` 的含义取决于上报模式（reporting mode，即传感器以何种规则产生事件），不同模式下并不相同：

| reporting mode | `samplingPeriodUs` 的含义 | 典型 sensor |
|---|---|---|
| continuous（连续） | 期望的连续采样周期 | 加速度计（accelerometer）、陀螺仪（gyroscope） |
| on-change（变化时上报） | 事件最快产生间隔；值不变时可以长时间没有事件 | 光线传感器（light）、计步器（step counter） |
| one-shot（单次触发） | 被忽略；触发一次后自动停用 | 显著运动检测（significant motion） |
| special trigger（特殊触发） | 按具体 sensor 定义 | 步伐检测器（step detector）等 |

应用应通过 `Sensor.getReportingMode()` 判断模式，不能对所有 sensor 都使用 `1 / period` 计算事件频率。one-shot sensor 应使用 `requestTriggerSensor()`，不应注册到普通 `registerListener()`。

<!-- gracker-diagram: ch05-07-reporting-modes -->
![上报模式决定采样周期的含义](../../assets/diagrams/ch05/ch05-07-reporting-modes.png)

图：只有合适的连续型场景才可用周期换算请求频率。One-shot 用 requestTriggerSensor，触发后停用；特殊类型遵循自己的定义。

## 从应用请求到硬件 FIFO

普通监听器（listener）路径中，请求从应用经过 framework、SensorService 和 HAL 到达硬件 FIFO，事件沿反方向返回：

<!-- gracker-diagram: ch05-07-request-and-event-path -->
![请求配置与传感器事件的往返路径](../../assets/diagrams/ch05/ch05-07-request-and-event-path.png)

图：展示普通 listener 路径。配置经服务聚合到 HAL，事件反向进入应用队列；AIDL Event FMQ 位于 HAL→framework，并非 App 直接读取。

```mermaid
flowchart LR
    App["App SensorEventListener"] --> SSM["SystemSensorManager"]
    SSM --> EQ["SensorEventQueue"]
    EQ --> SS["native SensorService"]
    SS --> SD["SensorDevice"]
    SD --> HAL["Sensors AIDL/HIDL HAL"]
    HAL --> Hub["sensor hub / hardware FIFO"]
    Hub --> HW["physical / composite sensor"]
    HAL --> SD
    SD --> SS
    SS --> EQ
    EQ --> App
```

这条路径中，Android 17 的 `SystemSensorManager.registerListenerImpl()` 为 listener 创建或复用 `SensorEventQueue`，`BaseEventQueue.addSensor()` 再调用原生层启用接口。

SensorService 在启用前根据 sensor 的 `minDelay` / `maxDelay` 限制采样周期，然后将 `samplingPeriodNs` 和 `maxBatchReportLatencyNs` 传给 sensor 接口的 `batch()`，再调用 `activate()`（framework 侧同名参数以微秒为单位，原生层字段以纳秒为单位）。

在 HAL 一侧，Android 17 同时保留使用 Android 接口定义语言（AIDL）的现代 Sensors HAL，以及兼容 HAL 接口定义语言（HIDL）2.0 / 2.1 的封装层（wrapper）。`SensorDevice::connectHalService()` 先尝试 AIDL，再尝试 HIDL。AIDL `ISensors` 的关键接口包括：

- `batch(handle, samplingPeriodNs, maxReportLatencyNs)`：配置采样与最大上报延迟；
- `activate(handle, enabled)`：启停 sensor；
- `flush(handle)`：请求尽快交付当前 FIFO 中的事件，在该 sensor 的事件流末尾加入 flush-complete 元数据；请求返回不等于应用已收到全部回调；
- Event FMQ：HAL 向 framework 传递事件；
- Wake Lock FMQ：framework 确认 wake-up 事件已经处理。

这里的 `batch()` 只负责提交配置。真正的省电效果来自 hub / FIFO 在 AP 之外暂存事件，从而合并交付和唤醒。没有硬件 FIFO 或低功耗 hub 时，即使 `batch()` 返回成功，也可能无法减少 AP 唤醒。另外，r1 的 `BaseEventQueue.addSensor()` 在正数 latency 的启用请求失败后，会以 latency=0 再试一次；所以 `registerListener()` 返回 true 也不能证明 batching 已按原参数启用。

<!-- gracker-diagram: ch05-07-registration-batch-fallback -->
![注册成功不等于 batching 成功](../../assets/diagrams/ch05/ch05-07-registration-batch-fallback.png)

图：r1 的 addSensor 可在批量启用失败后退回实时模式。true 只证明最终启用成功，实际 batching 还要核对 selected 参数与事件时间线。

## `samplingPeriodUs` 与 `maxReportLatencyUs`

`maxReportLatencyUs` 约束事件在 AP 醒着时从产生到经 HAL 上报的最大延迟；它不是应用回调完成的硬性期限，后续 framework 与 Looper 排队还会增加等待。AP suspend 时 non-wake-up sensor 的例外见下文。正数表示允许批量交付，0 表示尽快上报。它不会降低采样频率，也不保证事件一定等到整个窗口结束；实际交付时机还受 FIFO 容量、其他 sensor 和 AP 状态影响，见「AP 醒着时的 batching」一节。

应用可以通过四参数重载同时指定采样周期和最大批量延迟。例如这次注册请求约 50 Hz 采样，并允许最多延迟约 5 秒交付：

```kotlin
val registered = sensorManager.registerListener(
    listener,
    sensor,
    20_000,     // 约 50 Hz 的采样周期
    5_000_000,  // 最多延迟约 5 秒交付
)
```

这段请求会继续以约 50 Hz 产生事件，只是允许每批事件最多等待 5 秒；它不会将 sensor 改为 0.2 Hz。应用可能在短时间内连续收到多个 `onSensorChanged()` 回调，每次普通回调仍只交付一个 `SensorEvent`，其时间戳（timestamp）早于回调时刻。

<!-- gracker-diagram: ch05-07-sampling-versus-batching -->
![采样频率与批量交付是两个参数](../../assets/diagrams/ch05/ch05-07-sampling-versus-batching.png)

图：请求 5 秒 latency 不会把 50 Hz 改成 0.2 Hz。事件 timestamp 仍是发生时刻；应用排队时间不属于硬件 FIFO 上报期限。轨道只表示概念。

批量时长的理论上限可以用 FIFO 能容纳的事件数估算，即用 FIFO 事件数除以采样频率：

```text
fifo_duration_seconds ≈ fifo_event_count / frequency_hz
```

估算前需要选择正确的 FIFO 数值：

- `Sensor.getFifoReservedEventCount()` 是多个 sensor 并发使用 FIFO 时，为该 sensor 保证的事件数；
- `Sensor.getFifoMaxEventCount()` 是该 sensor 在理想条件下最多可用的事件数；
- `getFifoMaxEventCount() == 0` 表示该 sensor 不支持硬件 batching。

共享 FIFO 会被其他 sensor 占用，实际容量可能介于保留值（reserved）与最大值（max）之间。如果 50 Hz sensor 只有 100 个可用槽位，即使请求延迟 5 秒，FIFO 也可能在约 2 秒后填满并提前上报。

<!-- gracker-diagram: ch05-07-fifo-capacity-window -->
![FIFO 容量如何限制批量窗口](../../assets/diagrams/ch05/ch05-07-fifo-capacity-window.png)

图：100 槽与 50 Hz 是正文中的计算示例，实际可用槽数受共享占用影响。Wake-up 与 non-wake-up 事件使用不同 FIFO，挂起时的满队列处理也不同。

## SensorService 如何合并多个客户端

同一个传感器句柄（sensor handle，即系统识别传感器实例的整数标识）可能被多个应用和系统组件同时请求。

Android 17 的 `SensorDevice` 为每个连接保存一组 `BatchParams`，再由 `Info::selectBatchParams()` 选择硬件能够同时满足的聚合参数。

聚合规则可按下面的顺序理解：

1. 忽略当前被标记为禁用（disabled）的连接；
2. 采样周期取所有有效连接中的最小值，满足最快请求；
3. 每个连接的有效批量周期至少不能短于它自己的采样周期；
4. 聚合批量周期取这些有效值中的最小值；
5. 如果聚合批量周期不大于聚合采样周期，`SensorDevice` 会将其设为 0，明确要求实时流式交付（streaming）。

因此，一个请求 200 Hz 且 `maxReportLatencyUs=0` 的客户端，会使同一 handle 的硬件采用高频实时交付配置。另一个请求 10 Hz、10 秒 batching 的应用，无法用自己的参数覆盖前一个更严格的请求。

<!-- gracker-diagram: ch05-07-multi-client-aggregation -->
![同一 handle 的多客户端参数聚合](../../assets/diagrams/ch05/ch05-07-multi-client-aggregation.png)

图：本例聚合为约 200 Hz、latency=0。B 的低频长延迟不能覆盖 A 的严格要求；最终采样与回调表现还须实测。

`SensorDevice::updateBatchParamsLocked()` 只在选中参数发生变化，而且仍有有效客户端时调用 HAL `batch()`。客户端注销、用户标识符（User Identifier，UID）进入空闲状态（idle）、服务受到限制（restricted），以及 Android 17 条件性启用的 frozen-PID 路径，都可能使某个连接退出聚合，随后系统会重新计算硬件参数。

Android 调试桥（ADB）命令 `adb shell dumpsys sensorservice` 会输出各连接的请求值和最终选中值（selected）：

```text
active-count = ...
sampling_period(ms) = {...}, selected = ... ms
batching_period(ms) = {...}, selected = ... ms
```

输出中的 `selected` 是 framework 选中并用于 HAL `batch()` 的聚合参数，不等于实测硬件 ODR 或应用回调间隔；HAL 还会按硬件档位和能力执行配置。回调比预期密集时，先检查 selected batching period。如果 selected 已经为 0，应检查请求聚合和其他客户端；如果 selected 较大但事件仍提前到达，再检查 FIFO 容量、共享 FIFO、flush 和 AP resume。

## AP 醒着时的 batching

AP 处于运行（on）或空闲但未挂起（idle）状态时，HAL 可以将事件留在 FIFO，直到发生以下任一条件：

- 某个事件达到 `maxReportLatency`；
- FIFO 即将满；
- framework 调用 `flush()`；
- HAL 或共享 FIFO 中的其他 sensor 需要上报；
- AP 因其他原因醒来。

一旦某批事件必须上报，FIFO 中其他 sensor 的事件也可能同时交付，即使它们各自的最大延迟尚未到期。因此，硬件可以提前交付一批事件，`maxReportLatencyUs` 不能当作固定定时器周期。应用回调还受调度与队列影响，不能用相邻回调的墙钟间隔是否超过该值，单独判定 HAL 违约。

<!-- gracker-diagram: ch05-07-early-batch-delivery -->
![批量窗口为何提前结束](../../assets/diagrams/ch05/ch05-07-early-batch-delivery.png)

图：同批提前交付可能涉及其他 sensor，甚至不同 FIFO。Wake-up 与 non-wake-up 事件仍须存放在各自 FIFO；应用线程还可能增加后续排队。

事件 timestamp 必须对应物理事件发生时间，延迟上报不能改写它。应用可以用与 `elapsedRealtimeNanos()` 相同时间基准记录回调到达时间，再减去 `SensorEvent.timestamp`，估算事件在 FIFO、framework 和回调队列中的总等待时间。不能用可能受校时影响的墙钟时间（wall clock）减去 sensor timestamp。

## Suspend 中的 wake-up 与 non-wake-up 行为

AP 挂起期间的行为由 sensor 实例的 wake-up 属性决定。应用应使用 `Sensor.isWakeUpSensor()` 判断当前 sensor 实例；相同传感器类型（type）可以同时存在 wake-up 和 non-wake-up 两个独立实例，不能只根据 `TYPE_ACCELEROMETER`、`TYPE_STEP_COUNTER` 等类型名称推断。

### Non-wake-up sensor

非唤醒型传感器（non-wake-up sensor）不会阻止 AP 进入 suspend，也不能为了上报事件主动唤醒 AP。AP 挂起期间：

- 有 FIFO 时，事件继续写入 non-wake-up FIFO；
- FIFO 满后按环形缓冲处理，较老的 continuous 事件可能被覆盖；
- 没有 FIFO 时，suspend 期间产生的事件会丢失；
- `maxReportLatency` 不会为了 non-wake-up sensor 把 AP 唤醒；
- AP 因其他原因醒来后，FIFO 中仍保留的事件才会交付。

on-change sensor 有一项特殊保证：HAL 要在共享 FIFO 之外保存最新事件，避免最新状态被其他 continuous sensor 覆盖。Step counter 等累计值尤其依赖这项语义。

<!-- gracker-diagram: ch05-07-on-change-latest-retention -->
![On-change 最新状态为何保存在 FIFO 外](../../assets/diagrams/ch05/ch05-07-on-change-latest-retention.png)

图：Non-wake-up on-change 最新事件须避免被其他 continuous 数据覆盖。AP 恢复时可得到最新累计值，但不能据此推断每个历史变化都被保留。

Non-wake-up FIFO 在容量足够的有限挂起窗口内可以保留全部事件，但不能对任意长的 suspend 保证完整性，也不会按上报期限主动唤醒 AP。若业务要求挂起时仍按期完整交付，需要评估合适的 wake-up sensor，或让 AP 保持唤醒；两种方式都要验证系统访问限制与实际事件完整性。持有部分唤醒锁（partial wake lock）会阻止 CPU 完全休眠，显著改变功耗模型；通常应先确认业务是否只需要最新状态或累计结果。

### Wake-up sensor

唤醒型传感器（wake-up sensor）允许 AP suspend，但必须在下列时机唤醒 AP：

- 事件达到最大上报延迟；
- wake-up FIFO 即将满；
- one-shot wake-up 事件触发。

正数 `maxReportLatencyUs` 可以让多个 wake-up 事件共用一次 AP resume。如果使用不支持 batching 参数的 listener 重载，或将最大延迟设为 0，事件会更接近实时交付，唤醒成本也更高。

连续模式的 wake-up sensor 有一项持锁例外：官方 Batching 文档允许驱动在 `maxReportLatency` 小于 1 秒时持有 wake lock。因此，即使最大延迟为正数，也不能据此认定 AP 会在批次之间进入 suspend；需要结合 suspend / resume 与 wake lock 时间线判断设备的实际行为。

设备从 suspend 恢复时，平台会尽量交付 FIFO 中的全部内容，包括尚未达到各自延迟的批次，从而减少 AP 刚回到 suspend 后又被另一批事件唤醒的概率。

<!-- gracker-diagram: ch05-07-suspend-wakeup-contrast -->
![Suspend 时的 wake-up 与 non-wake-up](../../assets/diagrams/ch05/ch05-07-suspend-wakeup-contrast.png)

图：以 isWakeUpSensor() 判断实例属性，同一类型可能有两种实例。Non-wake-up 在 suspend 中不会因 maxReportLatency 到期主动唤醒 AP；on-change 还有最新状态保留例外。

## Wake lock 确认链

Wake-up 事件需要跨越 HAL、SensorService 和应用进程；在事件尚未被消费时，系统必须防止 AP 再次 suspend。Android 17 AIDL 路径包含两段确认：Wake Lock FMQ 确认 HAL→framework 的交接，应用队列 ACK 确认 SensorService→应用的交接；HAL 与 SensorService 分别持锁：

1. HAL 在将 wake-up 事件写入 Event FMQ 前，持有名称以 `SensorsHAL_WAKEUP` 开头的唤醒锁（wake lock）；
2. framework 读到事件并先取得自己的 wake lock 后，通过 Wake Lock FMQ 告知 HAL 已处理的 wake-up 事件数；
3. 正常路径中，SensorService 自身持有 `SensorService_wakelock`，由应用 native 队列的 ACK 减少连接欠账，直到所有相关连接不再需要持锁。

r1 的 Java 监听器路径由 JNI 在一组事件回调处理后调用 `sendAck()`；回调只把工作提交给另一个线程时，ACK 并不等待那个异步任务完成。异常路径也有回收：AIDL HAL 规定最近一次写入 wake-up 事件后 1 秒仍未收到 Wake Lock FMQ 消息时释放自己的锁；SensorService 的 ACK looper 在持锁且一次 5 秒轮询超时时清理引用。后者不是每个事件固定最多持锁 5 秒的承诺。

<!-- gracker-diagram: ch05-07-two-stage-wakelock-ack -->
![Wake-up 事件的两段确认与持锁交接](../../assets/diagrams/ch05/ch05-07-two-stage-wakelock-ack.png)

图：HAL 与 SensorService 分别持锁。正常交接先由服务接管锁，再确认 HAL；应用 ACK 的计数与 HAL 原始事件计数不同。超时与错误回收另按 r1 契约处理。

这个机制解释了两类耗电：

- wake-up sensor 事件本身导致 AP resume；
- 应用回调长时间未读取、连接阻塞或事件缓存堆积，会延长 framework 侧 wake lock 持有时间。

`dumpsys sensorservice` 的 `WakeLock Status` 可用于确认采集诊断信息时 SensorService 是否仍持锁。它只代表命令执行当时的状态；若要判断持续时长，还需结合 Perfetto / Battery Historian 的时间线。

## `flush()` 的正确含义

`SensorManager.flush(listener)` 请求尽快交付当前批量数据，并通过 `SensorEventListener2.onFlushCompleted()` 通知完成。AIDL `ISensors.flush()` 会将 `FLUSH_COMPLETE` 元数据放入指定 sensor 的事件流。

`flush()` 不会：

- 改变采样周期；
- 注销 listener；
- 清空后停止 sensor；
- 保证今后按更短窗口上报；
- 为 one-shot sensor 提供普通 flush 语义。

Android 17 的 `SensorService::enable()` 还有一项避免事件混入新连接的逻辑：当 continuous sensor 已有其他连接时，新连接启用前会先请求 flush，并等待属于该连接的首个 flush-complete，然后才开始发送普通事件。这样可以避免将先前连接积累的旧事件误交给新连接。注册后立即看到 flush 相关活动，不表示应用主动调用过 `flush()`。

<!-- gracker-diagram: ch05-07-flush-completion-and-new-client -->
![公开 flush 与新连接的首个 flush 边界](../../assets/diagrams/ch05/ch05-07-flush-completion-and-new-client.png)

图：flush 返回不等于所有应用回调已执行。右列仅适用于已有连接的 continuous sensor；one-shot、on-change、旧 HAL 错误路径需按各自规则处理。

## Android 12 以来的 200 Hz 访问限制

高采样率限制并非 Android 17 新增。目标版本为 Android 12（API 31）及以上的应用访问部分运动 / 姿态传感器（motion / position sensor）时，普通 listener 默认最多约 200 Hz；Sensor Direct Channel 默认最高为 `RATE_NORMAL`，通常约 50 Hz。需要更高频率时，应在应用清单（manifest）中声明以下权限：

```xml
<uses-permission
    android:name="android.permission.HIGH_SAMPLING_RATE_SENSORS" />
```

这段声明允许应用请求超过默认限制的采样率，但系统仍可施加其他限制。Android 17 中受限（capped）的集合包含六种类型：

- 加速度计（accelerometer）；
- 未校准加速度计（uncalibrated accelerometer）；
- 陀螺仪（gyroscope）；
- 未校准陀螺仪（uncalibrated gyroscope）；
- 磁场传感器（magnetic field）；
- 未校准磁场传感器（uncalibrated magnetic field）。

`SensorService.h` 将普通 listener 的受限周期（capped period）设为 5 ms。`SensorService::getSensorList()` 会根据调用包的权限，返回经过限制的 `minDelay` 和直接上报速率等级（direct-report rate level）；`SensorEventConnection` 与 `SensorDirectConnection` 在启用时还会再次检查请求。

当用户通过设备隐私开关关闭麦克风访问（microphone access）时，这六类 sensor 即使已经获得高采样权限，也会受到限制。原因是高频运动 / 姿态数据可能泄露音频相关信息。

公开 SDK 文档要求应用声明权限，并提示高频请求可能抛出 `SecurityException`。Android 17 源码还包含兼容模式（compatibility）、可调试构建（debuggable）和服务端不抛异常而直接限制采样率的分支。

应用不应依赖某一种失败表现，而应声明权限、检查注册结果，并根据实际事件时间戳（event timestamp）验证最终采样率。

<!-- gracker-diagram: ch05-07-high-rate-permission-and-privacy -->
![高采样率限制的权限与隐私条件](../../assets/diagrams/ch05/ch05-07-high-rate-permission-and-privacy.png)

图：Android 12 起目标 API≥31 的受限六类型适用默认限制；声明高采样权限仍不绕过设备麦克风隐私开关。返回结果与真实事件频率都要检查。

## Sensor Direct Channel 的适用边界

API 26 增加的 Sensor Direct Channel 允许 HAL 将高频事件写入共享内存，应用再从 `MemoryFile` 或符合要求的 `HardwareBuffer` 读取。它可以减少普通 `SensorEventQueue` 回调和线程调度开销，适合虚拟现实（VR）、增强现实（AR）、姿态跟踪和需要稳定高频数据流的原生（native）管线。

Direct Channel 的支持必须逐 sensor 查询：

- `Sensor.isDirectChannelTypeSupported()`；
- `Sensor.getHighestDirectReportRateLevel()`；
- 目标内存类型（memory type）和速率等级（rate level）；
- Android 12 及以上的高采样权限与麦克风隐私限制（microphone privacy cap）。

Direct Channel 不提供普遍的节能保证。高频 sensor、持续轮询共享内存和后续算法仍会消耗传感器器件、hub、内存和 CPU。比较普通 listener 与 Direct Channel 时，要固定传感器频率、消费算法和测试时长，再测量 CPU 时间、请求能量、温度和丢样率。

<!-- gracker-diagram: ch05-07-direct-channel-data-path -->
![Direct Channel 的控制与数据路径](../../assets/diagrams/ch05/ch05-07-direct-channel-data-path.png)

图：Direct Channel 减少普通回调与队列调度，但高频采样、共享内存消费和算法仍有成本。无节制忙轮询可能抵消收益。

## Android 17 的 frozen-PID 条件路径

`android-17.0.0_r1` 的 SensorService / `SensorDevice` 包含由 `android::hardware::flags::suspend_sensor_event_delivery_on_frozen_pid()` 控制的路径。这里的 frozen-PID 表示进程已被系统冻结、线程暂停执行。flag 开启时：

1. SensorService 为客户端 listener 注册 Binder（Android 进程间通信机制）冻结状态回调（frozen-state callback）；
2. 进程标识符（Process Identifier，PID）进入 frozen 状态后，`onClientFrozenStateChange()` 调用 `SensorDevice::setFrozenStateForConnection()`；
3. 该连接被标记为 `DISABLED_REASON_PID_FROZEN`；
4. `Info::selectBatchParams()` 不再让它参与硬件参数聚合；
5. 如果它是最后一个有效客户端，底层 sensor 会停用；
6. `SensorEventConnection::hasSensorAccess()` 也会在 PID frozen 时拒绝向该连接投递事件。

解冻只移除该连接的 PID_FROZEN 禁用原因；UID idle、服务限制等其他禁用原因也清除后，连接才会重新参与参数聚合，必要时重新激活 sensor。源码没有向普通应用承诺补发冻结期间的全部事件，因此应用不能将进程冻结器（freezer）当作另一种 batching 机制。

这条路径受 Android 配置系统 aconfig / 硬件 flag 控制。`android-17.0.0_r1` 中存在调用点，不能证明所有 Android 17 产品都默认启用它。分析具体设备时，要结合 `dumpsys sensorservice` 中客户端冻结 / 禁用（client frozen / disabled）信息、产品 flag 和实际事件时间线。

<!-- gracker-diagram: ch05-07-frozen-pid-conditional-path -->
![Android 17 冻结连接的条件处理](../../assets/diagrams/ch05/ch05-07-frozen-pid-conditional-path.png)

图：这是由 flag 控制的普通事件连接路径。解冻只清除 PID_FROZEN，UID idle 等其他原因仍可能阻止恢复；源码存在不等于所有产品默认开启。

## 批处理失效或收益变小的常见原因

批次表现和预期不一致时，可以按下表从现象反查可能原因和验证入口：

| 现象 | 可能原因 | 验证入口 |
|---|---|---|
| 设置 10 秒，仍频繁回调 | 其他客户端的延迟（latency）为 0、共享 FIFO 提前交付 | `dumpsys sensorservice` selected 参数 |
| 批次约 2 秒到达 | FIFO 按当前频率约 2 秒填满 | FIFO count、event rate、批次大小 |
| 灭屏后 non-wake-up 事件缺失 | AP suspend，FIFO 被覆盖或不存在 | suspend 时间线、事件 timestamp 缺口 |
| wake-up sensor 频繁唤醒 AP | latency=0、FIFO 小、事件过密 | 唤醒源（wakeup source）、SensorService wake lock |
| 请求高于 200 Hz 但结果被限制 | 缺权限、target SDK、microphone privacy | manifest、异常、event timestamp |
| 只有某些设备不能有效 batching | 设备厂商（OEM）的 FIFO / hub / HAL 能力不同 | sensor metadata、HAL / 厂商测试套件（VTS）、实机 trace |
| 注销后 sensor 仍高频 | 其他客户端仍在，或 listener 泄漏 | active-count、连接列表、selected period |
| 应用 frozen 后没有事件 | Android 17 frozen-PID 路径或 UID idle | disabled 标记、PID / UID 状态 |
| Direct Channel CPU 仍很高 | 消费端忙轮询或算法本身较重 | CPU 性能记录（profile）、读取周期、算法 slice |

批次变短不一定表示实现错误。FIFO 已满或其他 sensor 到期时，提前交付符合平台规则。应先确认平台 API 约定，再判断厂商实现。

## 观测方法

### 1. 应用侧记录请求和事件

每次注册至少应记录：

- sensor 名称 / 类型 / handle；
- `isWakeUpSensor()` 与 reporting mode；
- 最小 / 最大延迟（min / max delay）；
- FIFO 保留 / 最大事件数（reserved / max event count）；
- 请求的 sampling period 与 max latency；
- 注册结果、flush 结果和注销时刻。

事件侧应记录 `SensorEvent.timestamp`、回调到达时的系统启动后经过时间（elapsed realtime）、批次内事件数和线程。不要为每个高频事件写磁盘日志；可以只保留环形内存统计或按时间窗口聚合，以免测量本身改变结果。

### 2. 检查 SensorService 的聚合结果

在测试开始和结束时分别执行下面的命令，读取 SensorService 当前状态：

```bash
adb shell dumpsys sensorservice
```

输出中重点关注活动连接（active connections）、`active-count`、每个连接后的 `(disabled)` 标记、`sampling_period(ms)` / `batching_period(ms)` 及 selected 值、`WakeLock Status`。部分连接只显示身份摘要，具体可见信息受系统构建（build）类型和权限影响。

### 3. 对齐 AP suspend 与事件交付

Perfetto 可按设备能力采集：

- `power/suspend_resume`；
- `power/cpu_idle` 与 `power/cpu_frequency`；
- `sched/sched_switch`、`sched/sched_wakeup`；
- wakeup source 或中断请求（Interrupt Request，IRQ）事件；
- 应用注册、回调和处理的时间区间（slice）。

公开的性能跟踪（trace）不一定提供独立的 sensor FIFO 轨道（track）。诊断时，应将 sensor timestamp、回调 slice 和 suspend / resume 放在同一时间线上；厂商 sensor hub trace 只能作为特定设备的补充证据。

<!-- gracker-diagram: ch05-07-sensor-observation-evidence -->
![传感器诊断的三组证据](../../assets/diagrams/ch05/ch05-07-sensor-observation-evidence.png)

图：事件发生时间与回调到达时间使用相同 elapsed realtime 基准。selected 是请求配置；单次持锁快照或 sensor active time 都不能独自证明硬件能量和唤醒原因。

### 4. 看电池统计

Battery Historian 或 `dumpsys batterystats` 可以观察 UID 的 sensor 使用、wake lock 和测试窗口内的电量活动。严谨测试应：

1. 记录系统 build、设备、电池和环境温度；
2. 重置统计或标记明确的开始时间；
3. 断开通用串行总线（USB）连接，避免充电改变 suspend 行为与电流；
4. 固定屏幕、网络和后台任务；
5. 重复测试不使用批处理（no-batching）与使用 batching 的配置；
6. 同时报告事件数、丢样率、AP 唤醒次数（wakeup）、CPU 时间和请求能量。

电池统计（Battery stats）中的 sensor active time 不是 sensor 芯片的精确能量；Battery Historian 也不能单独证明某次 wakeup 由哪个 FIFO 触发。需要与 trace 和 SensorService 状态交叉验证。

## 一个可复现的对照实验

以连续型加速度计（continuous accelerometer）为例，可以设计三组对照：

| 组别 | 采样周期（sampling period） | 最大延迟（max latency） | 目的 |
|---|---:|---:|---|
| A | 20 ms | 0 | 高频、尽快交付的对照基线 |
| B | 20 ms | 5 s | 保持采样量，观察减少 AP 唤醒的收益 |
| C | 200 ms | 5 s | 同时减少采样和交付成本 |

每组都要确认 `dumpsys sensorservice` 的 selected 参数没有被其他客户端改变。如果 A 与 B 的事件总数接近，而 B 的回调批次更大、AP wakeup 更少，可以将主要差异归因于 batching；如果 B 与 C 的事件总数也明显不同，C 还包含降低采样率带来的收益。

灭屏测试还要区分 wake-up 和 non-wake-up 实例。Non-wake-up 组出现事件缺口可能符合 suspend 规则，不能直接判断为 HAL 丢失数据包。

<!-- gracker-diagram: ch05-07-sensor-three-group-experiment -->
![采样与 batching 的三组对照](../../assets/diagrams/ch05/ch05-07-sensor-three-group-experiment.png)

图：A/B 保持请求采样周期一致，B/C 再改变采样周期。只有排除其他客户端干扰、确认实际事件率和访问状态后，才能解释 batching 与降采样各自收益。

## 与应用治理章节的分工

本节从系统侧讨论采样请求的合并、借助 FIFO 减少 AP wakeup，以及 Android 17 的采样率和 frozen-PID 边界。25.4 节负责应用侧决策：选择 sensor、确定哪个组件管理其生命周期、页面不可见后注销、业务降级，以及定位功能与 sensor 的协同。

应用侧最重要的规则仍然是：

- 只在功能需要时注册；
- 请求业务可接受的最大 `samplingPeriodUs`；
- 请求业务可接受的最大 `maxReportLatencyUs`；
- 优先选择符合业务且功耗较低的 sensor，例如 step counter、significant motion；
- 退出使用场景时注销，不能依赖熄屏自动停用；
- 统一评估 wake-up sensor、partial wake lock 和后台任务。

WakeLock、Doze 和后台限制决定 AP / 应用能否继续运行；SensorService batching 决定 sensor 事件如何生成、缓存和交付。三类机制需要放在同一时间线中分析。

## 实机验证清单

- [ ] 记录设备 build，区分 `android-17.0.0_r1` 源码行为与产品配置；
- [ ] 核对 `samplingPeriodUs`，用增大周期的配置测试降低请求频率；
- [ ] 分开比较降低采样率与 batching 的功耗收益；
- [ ] 查询当前 sensor 的 reporting mode；
- [ ] 通过当前 Sensor 实例确认 wake-up / non-wake-up 属性；
- [ ] 记录 FIFO reserved / max，并检查共享 FIFO 的影响；
- [ ] 对照应用请求与 `dumpsys sensorservice` selected 参数；
- [ ] 请求高于 200 Hz 时，检查 Android 12 起的 target SDK 与权限条件；
- [ ] 测试 microphone privacy 对高采样率的影响；
- [ ] 比较 Direct Channel 与普通 listener 的实测能耗，不预设前者更省电；
- [ ] 检查 frozen-PID 的产品 flag，解冻后核对事件缺口；
- [ ] 对齐 AP suspend、wakeup、SensorService wake lock 与回调时间；
- [ ] 功耗测试断开 USB，并固定温度和后台条件；
- [ ] 同时记录事件完整性与能耗。

## Android 17 源码索引

以下路径均已按照 `android-17.0.0_r1` 复核：

- `frameworks/base/core/java/android/hardware/SensorManager.java`
  - 四参数 `registerListener()`
  - batching、wake-up / non-wake-up 的 SDK 说明
- `frameworks/base/core/java/android/hardware/SystemSensorManager.java`
  - `registerListenerImpl()`
  - `BaseEventQueue.addSensor()` / `enableSensor()`
  - 200 Hz 和 Direct Channel 速率限制（rate cap）
- `frameworks/base/core/java/android/hardware/Sensor.java`
  - reporting mode、wake-up、FIFO metadata
- `frameworks/native/services/sensorservice/SensorService.cpp`
  - `enable()`
  - wake lock 确认
  - high-sampling-rate cap
  - frozen-state callback
- `frameworks/native/services/sensorservice/SensorDevice.cpp`
  - `batch()` / `updateBatchParamsLocked()`
  - `Info::selectBatchParams()`
  - disabled/frozen client 处理
- `frameworks/native/services/sensorservice/SensorEventConnection.cpp`
  - 事件过滤（event filter）、应用确认（app ACK）、200 Hz cap、`hasSensorAccess()`
- `frameworks/native/services/sensorservice/SensorDirectConnection.cpp`
  - Direct Channel rate cap
- `hardware/interfaces/sensors/aidl/android/hardware/sensors/ISensors.aidl`
  - AIDL HAL、Event FMQ、Wake Lock FMQ
- `hardware/interfaces/sensors/aidl/android/hardware/sensors/SensorInfo.aidl`
  - FIFO、power、delay 和 wake-up metadata

## 参考资料

- Batching：<https://source.android.com/docs/core/interaction/sensors/batching>
- Suspend mode：<https://source.android.com/docs/core/interaction/sensors/suspend-mode>
- Sensor stack：<https://source.android.com/docs/core/interaction/sensors/sensor-stack>
- Sensors AIDL HAL：<https://source.android.com/docs/core/interaction/sensors/sensors-aidl-hal>
- [r1 SystemSensorManager](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/hardware/SystemSensorManager.java)：注册失败后的 latency=0 重试与逐事件回调。
- [r1 Sensors AIDL](https://android.googlesource.com/platform/hardware/interfaces/+/refs/tags/android-17.0.0_r1/sensors/aidl/android/hardware/sensors/ISensors.aidl)：FMQ 交接和 HAL 持锁超时。
- [r1 SensorService](https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/services/sensorservice/SensorService.cpp)：聚合、flush、持锁接管与 ACK 超时清理。
- SensorManager API：<https://developer.android.com/reference/android/hardware/SensorManager>
- Sensors overview / rate limiting：<https://developer.android.com/develop/sensors-and-location/sensors/sensors_overview>
