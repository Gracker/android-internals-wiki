---
title: "Android 17 TelephonyManager 架构、状态传播与性能边界"
chapter: "1.42"
section: "1.42"
status: finalized
applicable_versions: "Android 14 (API 34) - Android 17 (API 37); 主锚点 android-17.0.0_r1"
last_verified: "2026-08-18"
last_verified_against: "AOSP android-17.0.0_r1; Android Developers telephony API references"
confidence: high
sources:
  - type: aosp
    path: "frameworks/base/telephony/java/android/telephony/TelephonyManager.java (android-17.0.0_r1)"
  - type: aosp
    path: "frameworks/base/telephony/java/android/telephony/CellInfo.java (android-17.0.0_r1)"
  - type: aosp
    path: "frameworks/base/telephony/java/android/telephony/SmsManager.java (android-17.0.0_r1)"
  - type: aosp
    path: "frameworks/base/telephony/java/android/telephony/SubscriptionInfo.java (android-17.0.0_r1)"
  - type: aosp
    path: "frameworks/base/telephony/java/android/telephony/SubscriptionManager.java (android-17.0.0_r1)"
  - type: aosp
    path: "frameworks/base/core/java/android/telephony/TelephonyCallback.java (android-17.0.0_r1)"
  - type: aosp
    path: "frameworks/base/core/java/android/telephony/TelephonyRegistryManager.java (android-17.0.0_r1)"
  - type: aosp
    path: "frameworks/base/core/java/com/android/internal/telephony/IPhoneStateListener.aidl (android-17.0.0_r1)"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/TelephonyRegistry.java (android-17.0.0_r1)"
  - type: aosp
    path: "frameworks/opt/telephony/src/java/com/android/internal/telephony/PhoneFactory.java (android-17.0.0_r1)"
  - type: aosp
    path: "frameworks/opt/telephony/src/java/com/android/internal/telephony/RIL.java (android-17.0.0_r1)"
  - type: aosp
    path: "frameworks/opt/telephony/src/java/com/android/internal/telephony/NetworkIndication.java (android-17.0.0_r1)"
  - type: aosp
    path: "frameworks/opt/telephony/src/java/com/android/internal/telephony/SignalStrengthController.java (android-17.0.0_r1)"
  - type: aosp
    path: "frameworks/opt/telephony/src/java/com/android/internal/telephony/DefaultPhoneNotifier.java (android-17.0.0_r1)"
  - type: aosp
    path: "frameworks/opt/telephony/src/java/com/android/internal/telephony/data/DataNetwork.java (android-17.0.0_r1)"
  - type: aosp
    path: "frameworks/opt/telephony/src/java/com/android/internal/telephony/data/DataNetworkController.java (android-17.0.0_r1)"
  - type: aosp
    path: "frameworks/opt/telephony/src/java/com/android/internal/telephony/data/PhoneSwitcher.java (android-17.0.0_r1)"
  - type: aosp
    path: "frameworks/opt/telephony/src/java/com/android/internal/telephony/data/AccessNetworksManager.java (android-17.0.0_r1)"
  - type: aosp
    path: "frameworks/opt/telephony/src/java/com/android/internal/telephony/data/TelephonyNetworkAgent.java (android-17.0.0_r1)"
  - type: aosp
    path: "frameworks/opt/telephony/src/java/com/android/internal/telephony/SmsController.java (android-17.0.0_r1)"
  - type: aosp
    path: "frameworks/opt/telephony/src/java/com/android/internal/telephony/IccSmsInterfaceManager.java (android-17.0.0_r1)"
  - type: aosp
    path: "frameworks/opt/telephony/src/java/com/android/internal/telephony/SmsDispatchersController.java (android-17.0.0_r1)"
  - type: aosp
    path: "frameworks/opt/telephony/src/java/com/android/internal/telephony/subscription/SubscriptionManagerService.java (android-17.0.0_r1)"
  - type: aosp
    path: "packages/services/Telephony/AndroidManifest.xml (android-17.0.0_r1)"
  - type: aosp
    path: "packages/services/Telephony/src/com/android/phone/PhoneApp.java (android-17.0.0_r1)"
  - type: aosp
    path: "packages/services/Telephony/src/com/android/phone/PhoneGlobals.java (android-17.0.0_r1)"
  - type: aosp
    path: "packages/services/Telephony/src/com/android/phone/PhoneInterfaceManager.java (android-17.0.0_r1)"
  - type: aosp
    path: "hardware/interfaces/radio/aidl/android/hardware/radio/ (android-17.0.0_r1)"
  - type: official
    path: "https://developer.android.com/reference/android/telephony/TelephonyManager"
  - type: official
    path: "https://developer.android.com/reference/android/telephony/TelephonyCallback"
  - type: official
    path: "https://developer.android.com/reference/android/telephony/SubscriptionInfo"
tags: [telephony, architecture, system-service, binder, radio-hal, callback, multi-sim]
related_chapters: ["1.8", "1.38", "1.43", "24.10"]
task2b_state: reviewed
task6_state: reviewed
task9_state: reviewed
pipeline_stage: ready-to-publish
last_review_finalize_at: "2026-08-18"
last_review_finalize_run_id: "20260818-124458-491e1683"
---

# 1.42 Android 17 TelephonyManager 架构、状态传播与性能边界

## 进程模型

`TelephonyManager` 是应用访问蜂窝通信能力的 SDK 入口。它会做参数整理、选择 subscription（框架中代表一份可用移动通信订阅的记录）和少量兼容处理，主要状态与控制仍由跨进程服务完成。Android 17 的主路径已经不再使用早期的 `RILJ ↔ Unix Socket ↔ rild` 模型。

以 `android-17.0.0_r1` 为准，常见调用会跨过以下边界：

```text
App 进程
  TelephonyManager / TelephonyCallback
      │
      ├─ ITelephony Binder
      │      ↓
      │  com.android.phone
      │    PhoneInterfaceManager
      │    Phone / ServiceStateTracker / DataNetwork / RIL
      │      │
      │      ├─ AIDL Radio HAL Binder（优先）
      │      └─ HIDL IRadio HwBinder（兼容回退）
      │              ↓
      │          Vendor Radio HAL → Modem
      │
      └─ ITelephonyRegistry Binder
             ↓
         system_server
           TelephonyRegistry
             │
             └─ oneway IPhoneStateListener → App Binder Stub → Executor
```

图中的 RIL 是 framework 与 Radio HAL 之间的适配层，Radio HAL 是 Android 与厂商无线电实现之间的接口，Modem 则是实际处理蜂窝协议的基带系统。AIDL/Binder 是当前优先的 IPC 接口，HIDL/HwBinder 是为旧实现保留的兼容路径。

这张图里有三个容易混淆的角色：

- `TelephonyManager` 是应用侧客户端入口，不保存完整的蜂窝系统状态。
- `PhoneInterfaceManager` 运行在 `com.android.phone`，实现 `ITelephony.Stub`，承接大量查询与控制 API。
- `TelephonyRegistry` 运行在 `system_server`，缓存部分状态并把一次变化分发给多个监听者。

短信、订阅和通话控制还有独立入口：

| SDK 入口 | Binder 接口 | 主要服务端 |
| --- | --- | --- |
| `TelephonyManager` | `ITelephony` | `PhoneInterfaceManager`，`com.android.phone` |
| `TelephonyCallback` 注册 | `ITelephonyRegistry` | `TelephonyRegistry`，`system_server` |
| `SmsManager` | `ISms` | `SmsController` / `IccSmsInterfaceManager`，Phone 进程 |
| `SubscriptionManager` | `ISub` | `SubscriptionManagerService`，Phone 进程 |
| `TelecomManager` | Telecom Binder 接口 | Telecom 系统服务；负责面向用户的呼叫账户、界面和路由等管理 |

因此，不能把所有 Telephony API 都画成一条 `TelephonyManager → RIL → Modem` 直线。查询可能只读 framework 缓存；回调走 `TelephonyRegistry`；短信与 subscription 走各自的 Binder 服务；呼叫 UI 和 `PhoneAccount` 管理由 Telecom 协调。

## 1. Phone 进程怎样提供 `ITelephony`

`packages/services/Telephony` 的 manifest 使用 `android.uid.phone` shared UID（让受平台签名与配置约束的组件共享同一个 Linux UID），默认应用进程名是 `com.android.phone`。`PhoneApp.onCreate()` 进入 `PhoneGlobals` 初始化，`PhoneInterfaceManager` 最终通过 `TelephonyFrameworkInitializer` 提供的服务注册入口发布 `ITelephony`。

应用侧 `TelephonyManager.getITelephony()` 从同一个注册入口取得 Binder 服务句柄：

```java
return ITelephony.Stub.asInterface(
        TelephonyFrameworkInitializer
                .getTelephonyServiceManager()
                .getTelephonyServiceRegisterer()
                .get());
```

这段代码说明两件事：

1. 调用依赖 Phone 进程中的 Binder 服务是否可用。
2. `RemoteException` 往往表示 Phone 进程正在重启或 Binder 已死亡，不能直接解释成 Modem 故障。

Android 17 源码中，`TelephonyManager` 的服务句柄缓存仍可被关闭。分析单次调用耗时时，不能预设应用进程已经缓存了 Binder 句柄。

## 2. RIL 与 Radio HAL：Binder 化的异步请求模型

### 2.1 每个 logical phone 有一套 RIL

`PhoneFactory` 按 active modem 数量创建 `Phone` 与 `RIL`：

```text
sCommandsInterfaces[i] = new RIL(context, ..., phoneId=i, ...)
```

这里的 `phoneId` 表示 framework 当前管理的一部 logical phone（逻辑电话实例）。它通常与当前 logical slot（映射到某个 modem 的逻辑槽位）关联，但不能与设备上的物理卡槽、eSIM profile 使用的 port，或 subscription ID 混为一个概念。

### 2.2 AIDL 分域服务优先，HIDL 仍是兼容路径

Android 17 的 `RIL` 为以下功能域维护 `RadioServiceProxy`：

| AIDL Radio HAL | 功能 |
| --- | --- |
| `IRadioData` | 建立、更新和释放蜂窝数据连接（data call），以及 QoS 等 |
| `IRadioMessaging` | GSM/CDMA SMS 等 radio messaging |
| `IRadioModem` | Modem 状态、能力、重启 |
| `IRadioNetwork` | 注册状态、信号、小区、网络扫描 |
| `IRadioSim` | SIM/UICC 操作 |
| `IRadioVoice` | CS（电路交换）语音相关 radio 操作 |
| `IRadioIms` | IMS（基于 IP 的运营商多媒体子系统）相关 radio 能力 |

RIL 先用 `ServiceManager.waitForDeclaredService()` 获取分域 AIDL 服务，并为每个域设置 response（请求响应）与 indication（Modem 主动上报）回调。目标 AIDL 服务不可用且版本条件允许时，源码会依次尝试 HIDL `IRadio` 1.6、1.5 和 1.4。Android 17 保留 HIDL 回退，因此“已经全面迁移、旧 HAL 不再存在”的说法不准确。

AIDL `IRadio*` 接口是异步的 `oneway`：调用线程不等待 HAL 方法直接返回业务结果。一次 radio 请求的基本过程如下：

```text
框架创建 RILRequest
  → 分配 serial
  → 放入 mRequestList，并持有 RIL wakelock
  → 调用某个 IRadio* oneway 方法
  → Vendor HAL / Modem 异步处理
  → IRadio*Response 带 serial 返回
  → RIL 用 serial 找到原 RILRequest
  → 完成对应 Message / callback
```

主动上报走 `IRadio*Indication`，没有等待中的应用请求与它一一对应。例如 `IRadioNetworkIndication.currentSignalStrength()` 把 HAL `SignalStrength` 转成 framework 对象，再通知 RIL 中预先登记的监听者（registrant）。

RIL 还处理 Binder/HwBinder 服务死亡、服务重连和未完成请求。RIL wakelock（阻止 CPU 在请求处理中休眠的唤醒锁）timeout 用于避免唤醒锁长期不释放，不等同于取消请求；源码会保留已经等到 wakelock timeout 的 `mRequestList` 项，以便处理迟到的响应。

Vendor HAL 到 Modem 的传输由厂商实现决定，可能涉及共享内存、字符设备、专有 IPC 或其他机制。AOSP framework 无法证明某台产品一定使用 AT 命令，也无法证明一定存在独立的 `/vendor/bin/rild` 进程。现场分析应查看该设备的 VINTF manifest（声明 framework 与 vendor 接口实例的设备清单）、服务列表与 vendor 进程。

## 3. 同步 API 的耗时取决于服务端实现

“查询类 API 都会同步访问 Modem”不适用于 Android 17，其中至少有三种情况。

### 3.1 读取 Phone 进程缓存

`getNetworkTypeForSubscriber()` 读取 `phone.getServiceState().getDataNetworkType()`；`getServiceStateForSlot()` 读取 `phone.getServiceState()`，随后按权限清除涉及位置隐私的字段。这些 API 仍有 Binder、权限检查和 Parcelable（Binder 传输对象的序列化格式）成本，但正常路径不要求当场查询 Modem。

`getAllCellInfo()` 对 target SDK Q 及以上同样返回缓存：

```java
if (targetSdk >= Build.VERSION_CODES.Q) {
    return getCachedCellInfo();
}
```

调用方应检查每个 `CellInfo.getTimestampMillis()` 判断数据新鲜度。这个值使用设备启动后持续递增、不会受校时影响的 elapsed realtime，不是日历时间；应与相同时间基准下的当前值比较。反复调用 `getAllCellInfo()` 不会让现代应用得到更频繁的 radio 扫描。

### 3.2 异步请求 Modem 刷新

需要较新 CellInfo 时，应使用：

```java
telephonyManager.requestCellInfoUpdate(executor, callback);
```

`PhoneInterfaceManager` 通过 `sendRequestAsync(CMD_REQUEST_CELL_INFO_UPDATE, ...)` 请求更新，结果从 `ICellInfoCallback` 返回。系统会限制请求频率，而且文档明确说明不保证每次都得到新数据。应用需要处理 `ERROR_TIMEOUT`、`ERROR_MODEM_ERROR`、空列表和旧时间戳。

### 3.3 Phone 主 Looper 上的同步桥接

部分仅向特权应用或系统组件开放的 API 会进入 `PhoneInterfaceManager.sendRequest()`。它把命令投递给 Phone 进程的主 Looper（串行处理消息的主事件循环），然后让 Binder 线程等待 `MainThreadRequest.result`：

```text
Binder thread
  → Message 发往 Phone main Looper
  → wait(result)
  → Handler 完成请求并 notify
```

`sendRequest()` 明确禁止从 Phone 主 Looper 自身调用，以避免线程等待自己处理消息而死锁。许多调用使用负 timeout，表示一直等到完成；另一些调用传入明确 timeout。这里没有覆盖全部 Telephony API 的“5–10 秒默认超时”，Binder 也没有可依赖的通用事务超时。

对应用的建议很简单：

- 已确认只读缓存的轻量 API，也不要在每帧或紧循环中调用。
- 对提供 callback 的网络/Modem 操作，使用 callback，不要轮询同步 getter。
- 无法确认服务端是否阻塞的 Binder API，不放在主线程的关键交互路径。
- 性能测量要区分 Binder 排队、Phone 主 Looper 排队、Radio HAL 请求和 Modem 响应四段时间。

## 4. TelephonyRegistry 的注册与扇出

### 4.1 注册记录保存了什么

`TelephonyManager.registerTelephonyCallback()` 先经 `TelephonyRegistryManager` 发起调用，再由 `ITelephonyRegistry.listenWithEventList()` 进入 `system_server`。`TelephonyRegistry.Record` 为每次注册保存以下信息：

- callback Binder
- 调用方 UID/PID、包名与用于说明数据访问来源的 attribution tag
- `subId` 与 `phoneId`
- 监听的 event 集合
- 是否主动放弃精确/粗略位置（fine/coarse location）数据

注册时会执行包名、权限和位置访问检查。若 `notifyNow=true`，`TelephonyRegistry` 会把已有缓存立即回调给新注册者。一次注册可能触发多个初始 callback，因此其成本不只是“向列表追加一项”。

Android 17 按 PID 限制 callback 数量，源码默认值是 50，可由运行时配置系统 DeviceConfig 调整；配置值小于 1 时不执行数量限制。达到上限后，只有 `PHONE_STATE_LISTENER_LIMIT_CHANGE_ID` 这项兼容变更对调用 UID 生效时才抛出 `IllegalStateException`，否则服务端只记录错误。兼容变更允许平台按应用目标版本等条件逐步启用新行为。

同一个 `TelephonyCallback` 在未注销前再次注册也受兼容变更控制。`PREVENT_CALLBACK_REREGISTRATION` 生效时，`TelephonyCallback.init()` 直接抛出 `IllegalStateException`；未生效时，旧 Binder stub（接收远程调用的本地端点）可能暂时保留，初始状态回调还会再次触发。应用代码不应依赖兼容模式，应始终成对注册和注销。

### 4.2 状态怎样扇出

以信号强度为例，主路径是：

```text
Modem
  → Vendor Radio HAL
  → IRadioNetworkIndication.currentSignalStrength()
  → NetworkIndication
  → RIL registrant
  → SignalStrengthController
  → Phone.notifySignalStrength()
  → DefaultPhoneNotifier
  → TelephonyRegistryManager
  → ITelephonyRegistry.notifySignalStrengthForPhoneId()
  → TelephonyRegistry 遍历 Record
  → oneway IPhoneStateListener.onSignalStrengthsChanged()
  → App Binder Stub
  → 注册时提供的 Executor
```

`SignalStrengthController.notifySignalStrength()` 比较完整的 `SignalStrength` 对象与 `subId`；对象或 `subId` 变化时才继续通知。进入 `TelephonyRegistry` 后，匹配 `EVENT_SIGNAL_STRENGTHS_CHANGED` 的记录都会收到一份新的 `SignalStrength` 副本。因此，分发条件不只取决于面向 UI 的 0–4 级信号等级。

### 4.3 O(N) 的含义

`TelephonyRegistry` 使用一个 `mRecords` 列表。notify 方法在 `synchronized (mRecords)` 锁内遍历记录，再按事件、`subId`、`phoneId` 和权限筛选，所以扫描成本与注册记录数近似线性，即常说的 O(N)。

应用 callback 接口 `IPhoneStateListener` 是 `oneway`。system_server 顺序发出异步 Binder 事务，App 的 Binder Stub 再把工作投递到指定的 `Executor`（应用提供的任务执行器）。因此：

- App callback 中的业务代码不在 system_server 线程里执行。
- 过多记录仍会增加 system_server 的筛选、对象复制和 Binder 投递成本。
- App 的 Executor 太慢会在 App 内积压 callback，使业务读到过期状态并增加内存压力。
- 使用主线程 Executor 时，重计算、数据库和网络操作会直接造成 App 卡顿。
- Binder 失效会加入 `mRemoveList`，遍历后统一移除。

每个生命周期范围应复用少量 callback，在停止观察时调用 `unregisterTelephonyCallback()`。framework 只保存 callback 对象的弱引用，不会阻止它被垃圾回收；应用因此还要在注册期间持有强引用。

## 5. 数据网络状态机与 Connectivity

Android 17 的 `DataNetwork` 继承 `StateMachine`，也就是以显式状态和事件驱动转换来管理一条数据网络。主要状态如下：

```text
Connecting
    ├─ 成功 → Connected
    └─ 失败 → Disconnected

Connected
    ├─ handover → Handover → Connected / Disconnected
    └─ tear down → Disconnecting → Disconnected
```

外围组件各有分工：

- `DataNetworkController` 根据 Telephony network request（对网络能力的需求）、data profile（APN、认证等建链参数）、重试状态和 service state 创建或释放 `DataNetwork`。
- `PhoneSwitcher` 根据 subscription、默认数据选择、紧急呼叫和 Modem 并发能力决定哪些 logical phone 可以承载数据。
- `AccessNetworksManager` 管理 WWAN（蜂窝广域无线接入）与 WLAN（Wi-Fi）等候选接入网络的选择。
- `DataNetwork` 进入 `ConnectingState` 时创建并注册 `TelephonyNetworkAgent`，把 network capabilities（网络能提供什么能力）、link properties（地址、DNS、路由等链路参数）和 score（供网络选择使用的评分）发送给 Connectivity；连接建立后再调用 `markConnected()`。Connectivity 的 validation（验证能否按预期访问互联网）结果通过 `onValidationStatus()` 反向通知 Telephony。
- Connectivity 负责跨 transport（蜂窝、Wi-Fi 等传输类型）的网络选择、路由与应用 `NetworkCallback`。

`TelephonyManager.DATA_DISCONNECTED/CONNECTING/CONNECTED/SUSPENDED/DISCONNECTING/HANDOVER_IN_PROGRESS` 是给调用方的概括状态。它们无法一一代表所有内部 `DataNetwork` 实例，也无法说明 Connectivity 是否已经验证互联网，或是否选择该网络作为默认网络。

排查“蜂窝有信号但应用无网”时，至少分开检查：

1. `ServiceState` 是否已注册到蜂窝网络。
2. 蜂窝数据连接是否建立，`DataNetwork` 是否处于 connected 状态。
3. `TelephonyNetworkAgent` 是否已向 Connectivity 注册。
4. `NetworkCapabilities` 是否包含目标能力。
5. Connectivity validation、默认网络选择、DNS 和路由是否完成。

默认数据 `subId` 变化会触发 `PhoneSwitcher` 重新评估，并可能建立、迁移或释放数据网络。具体是否出现完整的 `DISCONNECTED → CONNECTING → CONNECTED`，取决于 Modem 并发能力、当前网络请求、切换（handover）方式与产品配置，不能把该序列写成固定行为。

## 6. 通话状态：Telephony 与 Telecom 要分层

`TelephonyManager` 对普通应用暴露三个概括性的通话状态：

| 状态 | 含义 |
| --- | --- |
| `CALL_STATE_IDLE` | 没有响铃、拨号中或通话中的呼叫 |
| `CALL_STATE_RINGING` | 有来电正在响铃或等待接听 |
| `CALL_STATE_OFFHOOK` | 至少一个呼叫处于拨号、通话或保持等非空闲状态 |

Phone 进程内部仍需区分承载通话的 radio domain：

- `GsmCdmaCallTracker` 处理传统 CS voice（电路交换语音）路径。
- `ImsPhoneCallTracker` 处理 IMS voice，包括分别承载于 LTE、Wi-Fi 和 5G NR 的 VoLTE、VoWiFi 与 VoNR 会话。
- `DefaultPhoneNotifier` 把合并后的概括/详细（coarse/precise）状态送往 `TelephonyRegistry`。
- Telecom 管理 `ConnectionService`、PhoneAccount、呼叫 UI、路由和用户级呼叫生命周期。

`CALL_STATE_OFFHOOK` 不能解释成“语音媒体流已经建立”，`CALL_STATE_RINGING` 也不能单独说明呼叫来自 CS、IMS 或卫星相关能力。分析建立时延时，要按阶段记录拨号请求、IMS/CS 信令、radio 状态、Telecom connection 状态、音频模式和首个有效媒体包。

第三方应用通常使用 `TelephonyCallback.CallStateListener` 观察概括状态。读取号码、precise call state、IMS quality 等信息需要更高权限或 carrier privilege（由 SIM 卡规则授予运营商应用的特权），回调内容还会按权限删除敏感字段。

## 7. 短信发送与接收

### 7.1 发送

Android 17 的发送路径可以概括为：

```text
SmsManager
  → ISms / SmsController
  → 对应 Phone 的 IccSmsInterfaceManager
  → SmsDispatchersController
      ├─ ImsSmsDispatcher
      ├─ GsmSMSDispatcher
      └─ CdmaSMSDispatcher（兼容路径）
  → IMS service 或 RadioMessaging HAL
  → 网络
```

`IccSmsInterfaceManager` 负责权限、AppOps（系统对具体敏感操作的运行时授权记录）、目标 subscription 和调用方信息检查，再交给 `SmsDispatchersController`。controller 根据 IMS 可用性、语音/数据注册域、短信格式和重试状态选择具体 dispatcher。

`SmsManager.sendTextMessage()` 返回只表示请求已交给系统，不表示网络已接收或对端已收到。应用应使用 `sentIntent` 区分发送结果，并在需要时使用 `deliveryIntent` 观察网络交付报告。长短信分段、重试、IMS 失败后的兼容路径（fallback）、发送限额确认和运营商服务都会改变时序。

“权限检查固定 5–30 ms”没有测试条件，不能作为平台指标。耗时受 Binder 排队、AppOps、短信分段、默认短信应用策略、IMS 状态和 vendor radio 实现影响，必须在目标设备测量。

### 7.2 接收

Radio 或 IMS 上报进入相应的接收处理器（inbound handler），framework 完成 PDU（承载短信协议字段和正文的协议数据单元）解析、去重、过滤、存储和默认短信应用分发。广播只是其中一个阶段。接收时延可能来自：

- Radio/IMS indication 到达时间。
- 多段消息是否收齐。
- 运营商过滤与垃圾信息过滤。
- 数据库 I/O。
- 默认短信应用进程启动和广播处理。

看到 `SMS_RECEIVED_ACTION` 较晚时，应先查找前一阶段的时间戳，避免把 Modem、framework 和应用接收器的时间全部算到 BroadcastQueue。

Android 17 包含 NTN（非地面网络）/satellite 相关 Telephony API 与 callback，但某台设备是否支持卫星消息，取决于硬件 feature、运营商、区域、业务开通状态（provisioning）和具体 API 功能开关。不能只根据系统版本推定普通 `SmsManager` 请求会经卫星发送。

## 8. Subscription 与多 SIM

### 8.1 四个 ID 不要混用

多卡代码中常见四种标识：

| 标识 | 表示什么 | 是否适合持久化 |
| --- | --- | --- |
| physical slot index | 设备上的物理卡槽 | 只描述硬件位置 |
| logical slot / `phoneId` | framework 当前管理的逻辑 modem/phone | 会随多 SIM 配置变化 |
| eSIM port index | eUICC（支持配置 eSIM profile 的 UICC）上可启用 profile 的逻辑端口 | 需结合 card/slot 理解 |
| `subscriptionId` | 当前 subscription 记录的 framework ID | 不应当作永久 SIM 身份 |

公开 API 返回 `SubscriptionInfo`。Phone 进程内部由 `SubscriptionManagerService extends ISub.Stub` 提供 Binder 服务，并使用 `SubscriptionInfoInternal` 与 `SubscriptionDatabaseManager` 管理记录。旧称 `SubInfoRecord` 已不适合描述 Android 17 的内部数据模型。SIM 更换、eSIM profile 变化或记录重建都可能改变 `subscriptionId`。

监听 subscription 变化应使用 `SubscriptionManager.addOnSubscriptionsChangedListener(Executor, ...)`，再按需读取 active subscription 列表。不要轮询，也不要让第三方应用直接观察内部 `Telephony.SimInfo` 数据库。

### 8.2 DSDS、DSDA 与并发能力

DSDS（Dual SIM Dual Standby，双卡双待）与 DSDA（Dual SIM Dual Active，双卡双通）描述的是产品的 radio 并发能力：

- DSDS 允许多张 SIM 保持待机，但并发通话、数据与射频资源仍受 Modem 能力和运营商配置约束。
- DSDA 允许更强的双卡并发活动，但“能否同时通话”“通话时另一卡能否保持数据”仍要看设备公开的具体能力。

不能根据 DSDS 名称推导“另一张卡一定周期性丢信号”，也不能假设每台 DSDA 设备都有两套完全独立的射频链路。Android 17 源码提供 `PhoneCapability`、active modem count 和 simultaneous calling 相关状态；应用与系统组件应读取这些能力，避免按卡槽数量猜测。

切换默认数据、语音或短信 subscription 由 `SubscriptionManagerService`、`MultiSimSettingController`、`PhoneSwitcher` 等组件协作。`subId`、`phoneId` 与 slot 的映射可能在 SIM 热插拔、eSIM profile 切换和 Modem 数量变化后更新，异步任务要在执行前重新校验映射。

## 9. 性能与稳定性实践

### 9.1 Callback

下面的示例展示一个 callback 对象和一个单线程顺序执行任务的 Executor，其持有位置应与实际组件生命周期一致：

```java
private final ExecutorService telephonyExecutor =
        Executors.newSingleThreadExecutor();

private static final class RadioStateCallback extends TelephonyCallback
        implements TelephonyCallback.ServiceStateListener,
        TelephonyCallback.SignalStrengthsListener {
    @Override
    public void onServiceStateChanged(ServiceState state) {
        // 只复制需要的字段，再交给业务层。
    }

    @Override
    public void onSignalStrengthsChanged(SignalStrength signalStrength) {
        // 合并重复 UI 更新，避免每次回调触发重计算。
    }
}

private final RadioStateCallback callback = new RadioStateCallback();
```

上面的片段强调 executor 和 callback 生命周期，省略了 Activity/Service 的具体注册位置。注册与注销要跟随明确的生命周期：

```java
telephonyManager.registerTelephonyCallback(telephonyExecutor, callback);
// 生命周期结束时：
telephonyManager.unregisterTelephonyCallback(callback);
telephonyExecutor.shutdown();
```

callback 中先提取不可变的小数据，再把数据库、网络和复杂计算交给业务队列。状态若只用于刷新 UI，可以只保留最新值；通话断开原因、网络注册失败等每次都具有独立含义的事件数据则不能随意丢弃。

### 9.2 查询

- 为同一 `subId` 复用 `TelephonyManager.createForSubscriptionId(subId)` 的结果。
- 对 service state、network type 和 cell info 建立业务缓存，由 callback 标记失效或刷新。
- CellInfo 刷新使用 `requestCellInfoUpdate()`，遵守频率限制，并显示时间戳。
- subscription 变化后使旧 `subId` 缓存失效。
- 在自有代码中用 trace section 标记 Telephony Binder 调用，才能把 App 侧等待与后续 callback 对齐。

### 9.3 错误处理

区分下面几类错误：

| 现象 | 常见含义 |
| --- | --- |
| `SecurityException` | 权限、AppOps、位置访问或 package/UID 校验失败 |
| `UnsupportedOperationException` | 设备未声明对应的 telephony system feature |
| `RemoteException` 后返回 unknown/null | Phone 进程或 Binder 异常 |
| `RADIO_NOT_AVAILABLE` | Radio HAL/Modem 当前不可用 |
| callback timeout/error | 异步 radio 请求未按期完成或 Modem 返回错误 |
| 数据旧但无异常 | 读到缓存，或主动刷新被限频 |

对所有错误采用同一种重试方式，会加重 Radio、Binder 和电量压力。重试策略至少要区分永久权限错误、设备不支持、Phone 进程重启、Radio 暂时不可用和缓存尚未更新。

## 10. 现场核查与 Perfetto

先用以下命令记录服务、subscription 和 registry 状态：

```bash
adb shell 'service list | grep -E "phone|telephony.registry|isub|isms"'
adb shell dumpsys phone
adb shell dumpsys telephony.registry
adb shell dumpsys isub
```

这些输出可能包含 cell identity、subscription、运营商和呼叫信息。共享日志前必须脱敏。user build 上部分字段和命令会因权限不可见。

Radio HAL 要从设备声明和当前服务实例开始查：

```bash
adb shell lshal | grep -i radio
adb shell 'service list | grep android.hardware.radio'
adb shell ps -A | grep -i -E 'radio|ril'
```

AIDL 服务出现在 Binder service manager 中，HIDL 服务通常由 `lshal` 展示。进程名由 vendor 决定，不能只搜索 `rild`。

Perfetto 至少启用 Binder、线程调度（sched）、CPU 频率（freq）、CPU 空闲状态（idle）和电源相关数据源，并在 App 调用处增加 trace section。RIL 源码还用 `TRACE_TAG_NETWORK` 建立名为 `RIL` 的异步轨道，以请求序列号作为关联值，可用于对齐 radio 请求与响应。

下面的 SQL 先筛选 Phone 进程与 system_server 的 Binder 时间片，再结合具体设备上的 slice 名称细化：

```sql
SELECT
  p.name AS process_name,
  t.name AS thread_name,
  s.name,
  s.ts,
  s.dur
FROM slice s
JOIN thread_track tt ON s.track_id = tt.id
JOIN thread t ON tt.utid = t.utid
JOIN process p ON t.upid = p.upid
WHERE p.name IN ('com.android.phone', 'system_server')
  AND s.name GLOB 'binder*'
ORDER BY s.dur DESC
LIMIT 100;
```

一段慢 Telephony 操作应拆成：

```text
App 发起 ITelephony
  → Phone Binder thread 收到
  → Phone main Looper 是否排队
  → RIL request serial 发出
  → Radio HAL Binder
  → response serial 返回
  → Phone 完成请求或发出 TelephonyRegistry notify
  → App callback Binder
  → App Executor 开始执行
```

缺少中间某一段时，应先补 trace 或日志时间戳，不能用单个 Binder slice 猜测 Modem 延迟。

## 11. 版本演进边界

| 版本 | 保留的演进事实 |
| --- | --- |
| Android 12 / API 31 | 公共 `TelephonyCallback` 成为替代 `PhoneStateListener` 的主要接口 |
| Android 13 起 | AIDL Radio HAL 按 data、messaging、modem、network、SIM、voice 等域拆分 |
| Android 15 | `SubscriptionInfo` 的 service capability 可表达特定 subscription 的语音、短信等能力 |
| Android 17 / API 37 | AOSP 主锚点同时保留分域 AIDL 与 HIDL 1.4–1.6 回退，并扩展 IMS、NTN/satellite 和 network security 相关接口 |

Android 17 源码中没有名为 `DeliQueue` 的 Telephony callback 优化，也没有名为“Data Plan Streaming API”的 Android 17 公共 API。带 `@FlaggedApi` 的 API 还要检查目标构建的功能开关、system feature、权限和运营商配置；源码中出现方法，不代表第三方应用在所有 Android 17 设备上都能调用。

## 小结

Android 17 Telephony 的性能问题通常跨越多层，但每层都能用源码和 trace 分开：

1. `TelephonyManager` 的查询与控制主要走 `ITelephony` 到 `com.android.phone`；callback 注册走 `ITelephonyRegistry` 到 `system_server`。
2. RIL 使用 serial、`mRequestList` 和 wakelock 管理异步 radio 请求。主要传输路径是分域 AIDL Radio HAL，HIDL 仍作为兼容回退。
3. 查询 API 有缓存读取、异步刷新和 Phone 主 Looper 同步桥接三类，不能用同一个延迟或超时模型解释。
4. `TelephonyRegistry` 在记录列表锁内线性筛选并发出 `oneway` callback；App 的业务代码在注册的 Executor 上执行。
5. 数据网络由 `DataNetworkController`、`DataNetwork`、`PhoneSwitcher`、`AccessNetworksManager` 与 Connectivity 共同完成，公开 `DATA_*` 状态只是摘要。
6. 通话要区分 Telephony radio state 与 Telecom 用户级呼叫，短信要区分系统接收请求与网络交付，多卡要区分 slot、port、`phoneId` 与 `subId`。

排查时应先确定调用属于哪一个 Binder 服务、读取缓存还是访问 Radio、当前使用 AIDL 还是 HIDL，以及状态在哪个进程停止传播。这样才能把“Telephony 慢”定位到一个可验证的具体阶段。
