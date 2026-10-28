---
title: Android 17 NFC 性能：标签读取、HCE 与无接触支付
chapter: '24.12'
section: '24.12'
status: finalized
applicable_versions: Android 15 (API 35) - Android 17 (API 37)
tags:
  - 连接性
  - nfc
related_chapters:
- '5.2'
last_verified: '2026-10-25'
last_source_verified_at: '2026-10-25'
last_verified_against: Android 17/API 37 official NFC docs reviewed 2026-10-25 and AOSP packages/modules/Nfc android-17.0.0_r1 source anchors
confidence: high
last_deep_review_at: '2026-07-27T12:35:27+08:00'
last_rework_at: '2026-08-09T03:14:43+08:00'
last_draft_polish_at: '2026-08-15T13:40:51+08:00'
last_review_finalize_at: '2026-08-15T13:40:51+08:00'
sources:
- type: official-docs
  ref: Android 17 / API 37 android.nfc API diff
  status: source-evidence
  path: https://developer.android.com/sdk/api_diff/37/changes/pkg_android.nfc
- type: official-docs
  ref: 'Android Developers: NFC basics'
  status: source-evidence
  path: https://developer.android.com/develop/connectivity/nfc/nfc
- type: official-docs
  ref: 'Android Developers: Host-based card emulation'
  status: source-evidence
  path: https://developer.android.com/develop/connectivity/nfc/hce
- type: official-docs
  ref: 'Android Developers: NfcAdapter / HostApduService API reference'
  status: source-evidence
  path: https://developer.android.com/reference/android/nfc/NfcAdapter
- type: aosp-source
  ref: 'packages/modules/Nfc @ android-17.0.0_r1: NfcAdapter.java, HostApduService.java, NfcDispatcher.java, NfcService.java, HostEmulationManager.java, NfcProprietaryCaps.java, NfcShellCommand.java'
  status: source-evidence
  path: https://android.googlesource.com/platform/packages/modules/Nfc/+/android-17.0.0_r1/
- type: android-common-kernel
  ref: android17-6.18-2026-06_r6
  status: boundary-reference
  path: https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6
- type: upstream-docs
  path: https://kotlinlang.org/api/kotlinx.coroutines/kotlinx-coroutines-core/kotlinx.coroutines/with-context.html
- type: aosp-source
  path: https://android.googlesource.com/platform/packages/modules/Nfc/+/android-17.0.0_r1/NfcNci/src/com/android/nfc/cardemulation/RegisteredServicesCache.java
- type: aosp-source
  path: https://android.googlesource.com/platform/packages/modules/Nfc/+/android-17.0.0_r1/NfcNci/src/com/android/nfc/cardemulation/RegisteredAidCache.java
- type: routed-material
  ref: DeepResearch/2026-07-05-background-audio-hardening-power.md
  status: rejected-unrelated-to-nfc-payment
  path: DeepResearch/2026-07-05-background-audio-hardening-power.md
---

# Android 17 NFC 性能：标签读取、HCE 与无接触支付

NFC（Near Field Communication，近场通信）既能读标签，也能反过来让手机当一张卡用。这篇文章讲手机一侧的性能：标签怎么分发到应用、HCE 服务怎么被路由和绑定、一次无接触支付的延迟落在哪几段，以及 API 37 带来了什么变化，覆盖标签分发、Reader Mode、主机卡模拟（Host Card Emulation，HCE）与 off-host 卡模拟。off-host 的交易在安全元件（Secure Element，SE）里完成，普通应用进程只做声明。

> 源码基线：AOSP `android-17.0.0_r1`（Android 17，API 37）；内核 `android17-6.18-2026-06_r6`。

NFC 框架和系统服务的源码在 `packages/modules/Nfc`；旧路径 `frameworks/base/core/java/android/nfc/` 与 `packages/apps/Nfc/` 里已经没有完整实现，查代码以新路径为准。

一次无接触支付会经过支付终端、手机的射频控制器（NFC Controller）、Android NFC 服务、钱包应用或 SE、收单系统和支付网络。Android 文档与 AOSP 源码覆盖的是手机一侧的分发、路由、服务绑定和数据传递；固定响应时间、成功率、离线额度这些指标，取决于具体终端和支付协议。性能目标要在目标设备、终端和协议组合上测量。

## 1. 三条 NFC 路径

我们先把三条路径摆清楚。读标签有两条入口：标签分发（tag dispatch）由系统解析标签，再向匹配的 Activity 发 `Intent`；Reader Mode 则让前台 Activity 通过回调直接拿到 `Tag`。NDEF（NFC Data Exchange Format）是 NFC Forum 定义的标签消息格式，标签上带的就是这种消息。

卡模拟换了一套语言：应用协议数据单元（Application Protocol Data Unit，APDU）承载命令与响应，应用标识符（Application Identifier，AID）用来选中卡应用。

| 模式 | 手机扮演的角色 | Android 应用入口 | 数据经过应用进程吗 | 常见场景 |
| --- | --- | --- | --- | --- |
| 标签分发 / Reader Mode | 读卡器 | NFC `Intent`、`ReaderCallback`、`TagTechnology.transceive()` | 经过 | 读标签、门禁读卡、设备配网 |
| HCE | 卡片 | `HostApduService.processCommandApdu()` | 经过 | 软件卡、商户专用储值卡、部分钱包方案 |
| Off-host card emulation | 卡片 | `OffHostApduService` 只声明 AID 与路由信息 | 交易 APDU 不经过 | 嵌入式安全元件（eSE）或 SIM 类安全模块（UICC）中的卡应用 |

这张表的关键一列是“数据经过应用进程吗”。HCE 的 APDU 交给 `HostApduService`，应用的启动与执行时间直接计入响应；off-host 的 APDU 由 SE 处理，应用只声明路由，SE 内部每一步的耗时在外面看不到。

下面这张流程图把 HCE 与 off-host 分流的位置标了出来。图里的 NFCC 指 NFC 控制器，负责射频收发和底层协议；ISO-DEP 是其上基于 ISO/IEC 14443-4 的数据交换协议：

Host 路径经过 Android 服务和应用；off-host 路径在安全元件里处理交易 APDU。

<!-- gracker-diagram: a272-01-host-and-se-routing -->
![NFCC路由将主机HCE与安全元件交易分流](../../assets/diagrams/ch24/a272-01-host-and-se-routing.png)

图：交易 APDU 是否经过应用，是两条路径的关键边界；off-host 的声明服务并不参与逐条交易处理。

顺着图看路由：NFCC 路由表先把用于选择应用的 `SELECT AID` 命令指向 host 或 SE。走 host 的一路进入 `NfcService`，由 `RegisteredAidCache` 与 `HostEmulationManager` 从已注册的 HCE 服务里挑出目标组件；走 off-host 的一路直接把 APDU 交给 SE。off-host 省掉了应用处理这一环，但端到端延迟仍由终端、射频、SE 中的卡应用和支付协议共同决定。

## 2. HCE 交易的延迟来自哪些阶段

一笔 HCE 交易为什么慢？我们先把它拆成六个可观测阶段：

1. **射频发现与激活**：终端持续发出轮询帧，手机进入射频场后完成多卡冲突检测和 ISO-DEP 连接。天线、手机摆放位置、NFCC 固件和终端参数都会影响这一段。
2. **AID 路由**：终端发送 `SELECT AID`，Android 根据已注册服务、默认钱包、前台偏好和设备状态选择目标。
3. **服务就绪**：首选支付服务一般已经由 NFC 进程绑定；普通 HCE 服务可能在首个 `SELECT AID` 到达后才绑定，未运行进程的启动时间会计入这一段。
4. **APDU 处理**：`HostApduService` 在应用主线程收到命令，生成同步响应，或把耗时工作交给其他线程后调用 `sendResponseApdu()`。
5. **响应回传**：应用通过基于 Binder 的消息通道 `Messenger`，把响应 APDU（R-APDU）返回 `HostEmulationManager`，再经原生 NFC 协议栈、NFCC 和射频送回终端。NCI（NFC Controller Interface）是主处理器与 NFCC 之间的标准命令接口。
6. **支付协议与外部系统**：钱包后端、支付令牌（token）、持卡人验证、收单系统和终端界面都在 AOSP 的 APDU 分发过程之外。

`HostEmulationManager` 的状态机把路由与服务绑定过程记录在案：

- 激活后从空闲状态 `STATE_IDLE` 进入等待选择命令的 `STATE_W4_SELECT`。
- 系统解析 `SELECT AID`；已有服务连接时立即转发，没有连接时保存该 APDU，并进入等待服务的 `STATE_W4_SERVICE`。
- `onServiceConnected()` 收到绑定结果后，再发送缓存的 `SELECT AID`。
- APDU 转发时进入传输状态 `STATE_XFER`；只有当前活动服务返回的非空响应才会交给 `NfcService.sendData()`。
- 射频链路断开，或新 `SELECT AID` 被解析为另一服务时，系统调用 `onDeactivated()` 并清理活动服务状态。同一服务承接另一 AID 时未必触发停用，不能只用这个回调划分所有协议交易。

<!-- gracker-diagram: a272-03-host-manager-state-flow -->
![HostEmulationManager缓存首条命令等待服务就绪](../../assets/diagrams/ch24/a272-03-host-manager-state-flow.png)

图：服务预绑定、普通绑定和应用处理分别记录；没有SELECT回调时先核对AID、角色与解锁条件。

有了这六个阶段，排查就有了分流判据：首个 APDU 慢而后续正常，先查进程启动和服务绑定；每个 APDU 都慢，就去查应用计算、锁竞争、存储访问和异步依赖。

<!-- gracker-diagram: a272-02-hce-latency-phases -->
![HCE延迟按射频、路由绑定、应用与回传拆分](../../assets/diagrams/ch24/a272-02-hce-latency-phases.png)

图：首条慢先看路由和服务就绪；每条都慢再看主线程、锁、存储、密钥操作和异步依赖。

### 首选支付服务的预绑定

`HostEmulationManager.bindPaymentServiceLocked()` 用 `BIND_AUTO_CREATE` 预绑定当前首选支付服务，并保留独立的 `mPaymentService` 连接；普通服务则可能要等 AID 命中后才临时绑定。服务死亡后系统会尝试重新绑定，但进程重建、内存状态丢失和支付令牌（token，用来代替真实卡号的受限凭据）失效这些事，仍要应用自己处理。

从 Android 15 开始，`CATEGORY_PAYMENT` 类别（category）通常由默认钱包角色持有者（Wallet role holder）处理；前台 Activity 也可以用 `CardEmulation.setPreferredService()` 临时指定服务。AID 组是一组必须整体路由到同一服务的标识符，系统同一时刻只启用一个支付类别 AID 组。所以 HCE 服务收不到命令时，我们先核对钱包角色、AID 和用户选择——配置错了，APDU 在路由层就走丢了，再快的应用也接不到。

## 3. Android 17 / API 37 的 NFC 变化

API 37 的官方差异页列出了 `NfcAdapter`、`NfcAdapter.ReaderCallback` 和 `NfcAntennaInfo` 的变化：

| 变化 | 适用对象 | 工程含义 |
| --- | --- | --- |
| NFC `Intent`（系统分发给应用的消息对象）限制 | `targetSdkVersion > BAKLAVA`，也就是以 API 37 或更高版本为目标的应用 | 接收 Activity 必须以 `android.permission.DISPATCH_NFC_MESSAGE` 保护；处于 stopped 状态的应用不接收 NFC `Intent` |
| `ACTION_TAG_DISCOVERED` 废弃 | 标签分发应用 | 改用更具体的 `ACTION_NDEF_DISCOVERED` 或 `ACTION_TECH_DISCOVERED` |
| `ReaderCallback.onTagLost(Tag)` | Reader Mode 应用 | API 37 可以收到标签离场回调；它是带空实现的默认方法，旧实现无需立即增加方法 |
| `allowOneTransaction()` | 首选 HCE 服务 / 默认钱包角色持有者 | Observe Mode 开启时临时允许一笔交易，交易结束或射频场消失后恢复 Observe Mode |
| 退出帧（exit frame）与 Reader Mode 注释帧查询 | 钱包、终端模拟与设备集成 | 使用前查询设备能力；具体行为依赖 NFCC 固件 |
| NFC 节电模式查询与设置 | 系统或特权集成 | 设置接口需要 `NFC_SET_CONTROLLER_ALWAYS_ON`；普通应用不能用它控制省电 |
| `NfcAntennaInfo.isDeviceFoldable()` 废弃 | 展示天线位置的界面 | 不再根据该布尔值推断设备形态 |

我们按标签分发、读卡、支付和特权硬件控制把变化分开看。新增方法进入 API 37 SDK，只说明接口就绪，具体设备支不支持对应硬件能力，仍要以 `is...Supported()` 的查询结果为准。表中的 Observe Mode 让手机先监听终端轮询、暂缓进入交易；退出帧与 Reader Mode 注释帧是依赖 NFCC 固件的可选能力。这三项都在第 5 节展开。

官方差异页还列出 `getGestureExchangeAid()`：它需要 `PERFORM_GESTURE_EXCHANGE` 权限，只服务于 Tap to Share 的手势交换。

部分参考页把节电模式和退出帧 API 标为 Android API 36.1，API 37 的 36→37 差异页也收录了这些符号。面向 Android 17 就用 API 37 SDK 编译；还要覆盖 API 36.1 的话，按对应 SDK 版本与功能开关判断，硬件能力查询只是其中一步。

### 3.1 目标 SDK 37 的 NFC `Intent` 适配

适配从 Manifest 开始。这个片段接收一种明确 MIME 类型的 NDEF 标签：

```xml
<uses-permission android:name="android.permission.NFC" />
<uses-feature
    android:name="android.hardware.nfc"
    android:required="true" />

<application>
    <activity
        android:name=".NdefActivity"
        android:exported="true"
        android:permission="android.permission.DISPATCH_NFC_MESSAGE">
        <intent-filter>
            <action android:name="android.nfc.action.NDEF_DISCOVERED" />
            <category android:name="android.intent.category.DEFAULT" />
            <data android:mimeType="application/vnd.example.asset" />
        </intent-filter>
    </activity>
</application>
```

`DISPATCH_NFC_MESSAGE` 写在 Activity 的 `android:permission` 上，意思是：要启动该组件的调用方必须持有这项签名级权限。它由 Android NFC 系统服务持有，普通应用既无需申请，在普通运行时权限体系里也拿不到它。

`NfcDispatcher.isMatchAdditionalActivityFilters()` 会检查目标 SDK、应用的 stopped 标志和 Activity 声明。尚未被用户启动过、或被强行停止（force-stop）的应用处于 stopped 状态；对上述目标 API 37 及以上的附加过滤，系统拒绝向其分发 NFC `Intent`。用户手动启动可解除 stopped 状态，不能把这段 target 门控外推到所有旧目标应用。

`ACTION_TAG_DISCOVERED` 是前两种分发都未命中时的宽泛后备入口，API 37 已将它废弃；应用优先匹配具体的 NDEF MIME 类型、URI 或标签技术列表。

Android 16 起，含 HTTP/HTTPS 链接的 NFC 标签改走 `ACTION_VIEW`；Android 17 会先显示打开链接通知，用户确认后才触发 `ACTION_VIEW`。需要接收自有域名的应用应配置 Android App Links，不再等待 `ACTION_NDEF_DISCOVERED`。

<!-- gracker-diagram: a272-04-intent-target-and-url -->
![目标37的标签Intent保护与URL入口分别处理](../../assets/diagrams/ch24/a272-04-intent-target-and-url.png)

图：ACTION_TAG_DISCOVERED 已废弃；优先采用具体 NDEF 或技术过滤，URL 不再等待旧NDEF入口。

### 3.2 Reader Mode 的标签离场回调

这个示例展示前台 Reader Mode 的生命周期和 API 37 标签离场处理：

```kotlin
class ReaderActivity : AppCompatActivity(), NfcAdapter.ReaderCallback {
    private val adapter by lazy { NfcAdapter.getDefaultAdapter(this) }

    override fun onResume() {
        super.onResume()
        adapter?.enableReaderMode(
            this,
            this,
            NfcAdapter.FLAG_READER_NFC_A or NfcAdapter.FLAG_READER_NFC_B,
            null
        )
    }

    override fun onPause() {
        adapter?.disableReaderMode(this)
        super.onPause()
    }

    override fun onTagDiscovered(tag: Tag) {
        // 把 connect/transceive 交给工作线程，并将 UI 更新切回主线程。
    }

    override fun onTagLost(tag: Tag) {
        // API 37：取消与该 Tag 实例关联的任务和界面状态。
    }
}
```

Reader Mode 只在 Activity 位于前台时有效。API 并未承诺 `ReaderCallback` 在主线程执行，所以界面更新要派发回主线程；`TagTechnology.connect()` 和 `transceive()` 这类可能阻塞的 I/O 操作，放到应用自己的工作线程。

`Tag`、`TagTechnology` 的连接对象同样别存到 Activity 生命周期之外。上述代码只示范注册骨架；生产实现还需在 `onPause()`、标签离场或任务结束时停用旧任务并调用相应 `TagTechnology.close()` 释放连接，后者也会取消其他线程上阻塞的 `connect()` 等 I/O。仅 `disableReaderMode()` 不能替代应用自己的任务与资源清理。

<!-- gracker-diagram: a272-05-reader-lifecycle-and-io -->
![ReaderMode按前台生命周期管理Tag任务](../../assets/diagrams/ch24/a272-05-reader-lifecycle-and-io.png)

图：SKIP_NDEF_CHECK 仅用于无需NDEF的协议；开启后不枚举Ndef，不能当所有标签的通用加速开关。

标签离场、手机移动和射频噪声都可能让 `connect()` 或 `transceive()` 抛出 I/O 异常；`onTagLost()` 管的是任务取消和界面清理这一层，每次 I/O 自己的异常处理仍然要写。

`FLAG_READER_SKIP_NDEF_CHECK` 留给明确无需 NDEF 解析的专有协议。启用后平台跳过 NDEF 检查，也不像常规流程那样枚举 `Ndef` 标签技术；对原本依赖 NDEF 的标签，无条件开启可能让它们处理不了。

## 4. HCE 服务：注册、路由与 APDU 延迟敏感路径

### 4.1 HCE 服务声明与 AID 组

系统接受一个 HCE 服务，先看声明。下面这份声明注册一个示例 HCE 服务，示例 AID 只用于演示，和任何支付网络的正式 AID 都没关系：

```xml
<service
    android:name=".DemoApduService"
    android:exported="true"
    android:permission="android.permission.BIND_NFC_SERVICE">
    <intent-filter>
        <action android:name="android.nfc.cardemulation.action.HOST_APDU_SERVICE" />
    </intent-filter>
    <meta-data
        android:name="android.nfc.cardemulation.host_apdu_service"
        android:resource="@xml/apdu_service" />
</service>
```

系统扫描 HCE 服务时检查两件事：应用声明了 `NFC` 权限，服务由 `BIND_NFC_SERVICE` 保护；两条都齐了，`RegisteredServicesCache` 才会收录这个服务。

配套的 XML 把一个示例 AID 组注册给同一服务：

```xml
<host-apdu-service
    xmlns:android="http://schemas.android.com/apk/res/android"
    android:description="@string/hce_service_name"
    android:requireDeviceUnlock="true">
    <aid-group
        android:category="other"
        android:description="@string/hce_aid_group">
        <aid-filter android:name="F0010203040506" />
    </aid-group>
</host-apdu-service>
```

路由以 AID 组为单位：系统把整组 AID 交给同一个服务，想给组里某一个 AID 单独换服务，整组都得跟着动。生产支付应用要使用按规范分配的 AID、正确的 `payment` 类别和钱包角色；示例值只够演示用，上不了线。

### 4.2 `processCommandApdu()` 的线程模型

命令进入应用后，`HostApduService.processCommandApdu()` 运行在应用主线程上，官方文档对此有明确说明；实现上也是如此：`HostApduService` 用一个绑定主线程 `Looper` 的 `Handler` 接收 `MSG_COMMAND_APDU`，消息一到就直接调用回调。

能立即算出的响应直接返回；要异步处理就返回 `null`，工作完成后从任意线程调用非阻塞的 `sendResponseApdu()`。

这个骨架同时展示同步响应、异步响应和链路断开后的取消处理：

```kotlin
class DemoApduService : HostApduService() {
    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.Default)
    private val transactionEpoch = AtomicLong(0L)
    private val commandEpoch = AtomicLong(0L)

    override fun processCommandApdu(
        commandApdu: ByteArray,
        extras: Bundle?
    ): ByteArray? {
        val commandId = commandEpoch.incrementAndGet()
        parseCheapCommand(commandApdu)?.let { return buildImmediateResponse(it) }

        val epoch = transactionEpoch.get()
        scope.launch {
            val response = buildResponseFromLocalState(commandApdu)
            withContext(Dispatchers.Main.immediate) {
                if (transactionEpoch.get() == epoch
                    && commandEpoch.get() == commandId
                ) {
                    sendResponseApdu(response)
                }
            }
        }
        return null
    }

    override fun onDeactivated(reason: Int) {
        transactionEpoch.incrementAndGet()
        scope.coroutineContext.cancelChildren()
    }

    override fun onDestroy() {
        scope.cancel()
        super.onDestroy()
    }
}
```

这个骨架只表达线程与生命周期关系，支付协议本身没有实现。`transactionEpoch` 实际标记服务停用代次，每次 `onDeactivated()` 递增；`commandEpoch` 标记同一服务收到的新命令。后台结果回到主线程后，与停用回调串行检查两者，再提交响应，避免在后台检查后被已处理的停用或新命令取代。

这只是应用提交前的失效检查。固定 `android-17.0.0_r1` 的 `sendResponseApdu()` 还会把响应排入服务自己的 `Handler`，公开接口既不携带交易 ID，也没有撤回已入队响应的操作。系统只检查活动服务、Messenger 和传输状态；同一服务被新交易再次使用时，这些条件不构成旧响应的交易隔离保证。生产协议仍须关联当前命令与交易、拒绝迟到或重放结果，不能把本例当作完整支付实现。

<!-- gracker-diagram: a272-06-async-apdu-submission-boundary -->
![异步APDU发送前失效检查与框架排队边界](../../assets/diagrams/ch24/a272-06-async-apdu-submission-boundary.png)

图：停用递增交易代次并取消工作；应用发送前检查不能替代协议对迟到响应、当前命令和交易的验证。

生产实现还要校验 APDU 长度与字段：CLA 是命令类别，INS 是指令，P1/P2 是指令参数，Lc 是命令数据长度，Le 是期望响应长度；返回值要带协议状态字，密钥隔离、重放防护和认证要求也一样要满足。

### 4.3 APDU 路径的优化顺序

APDU 是半双工交换，同一时刻只有一方在发，终端发出一条命令后就等响应；Android HCE 又只有一个逻辑通道，一段耗时任务会拖住同一交易里的后续命令。所以排查 APDU 路径时，我们按这个顺序来：

1. **确认路由**：核对 AID、类别、钱包角色、前台偏好、解锁要求和亮屏要求。错误路由的典型表现，是服务迟迟收不到首条命令。
2. **减少主线程工作**：解析固定头部时避免反复创建十六进制字符串、JSON 对象和临时集合；不要在回调中访问数据库、文件或网络。
3. **预先加载可安全缓存的数据**：协议允许时，提前读取只读配置、索引和有效支付令牌。缓存仍要遵守密钥策略、有效期、计数器和风控规则。
4. **分别记录异步依赖耗时**：本地存储、硬件密钥操作和后端请求单独计时，网络等待归网络，别记到 NFC 框架头上。
5. **在 `onDeactivated()` 清理交易态**：终端移开、AID 切换或链路异常都可能中止交换，迟到响应必须取消。
6. **限制日志与临时对象**：发布版本不记录完整 APDU、主账号（Primary Account Number，PAN，即卡号）、支付令牌、密钥材料或可关联用户的 AID 组合；性能日志只留命令类型、长度、状态和去标识化延迟。

维持 HCE 进程用不着自己起前台服务：首选支付服务已经有 NFC 系统绑定机制，额外保活既增加功耗与后台限制风险，也抹不平设备、终端和协议的差异。

### 4.4 用 Trace 标记应用计算区间

Perfetto 是 Android 的系统追踪工具，`Trace` 可以在记录里创建带名称的 slice。这个示例标记的是应用生成响应的区间：

```kotlin
override fun processCommandApdu(commandApdu: ByteArray, extras: Bundle?): ByteArray {
    Trace.beginSection("HCE_build_response")
    return try {
        responseEngine.build(commandApdu)
    } finally {
        Trace.endSection()
    }
}
```

这个 slice 只覆盖应用计算：此前的射频激活、AID 解析和服务绑定，以及响应离开应用后的 NCI 与终端处理，都在它之外。我们把这个 slice 与系统调度、Binder 事件和外部读卡器时间戳对应起来，端到端延迟才能解释得通。

## 5. Observe Mode 与 API 37 的单次交易

NFC 终端会循环发送轮询帧（polling frames），找附近可用的卡。观察模式（Observe Mode）让手机先只听这些帧，暂缓应答，也暂缓进入卡交易。它从 Android 15（API 35）开始提供；API 37 在此之上增加了单次允许交易、退出帧能力查询和 Reader Mode 注释帧支持。

### `allowOneTransaction()` 的调用条件

`NfcAdapter.allowOneTransaction()` 会临时关闭 Observe Mode，让一笔 HCE 交易继续。`NfcService` 会检查：

- NFC 适配器必须已开启，当前状态不可用时直接返回。
- 特权进程的 UID（Linux 用户标识）可以通过调用资格检查。
- 普通应用的 UID 必须属于当前用户的默认钱包或前台首选支付服务。
- HCE 交易已经激活时，调用会被拒绝。
- `HostEmulationManager` 会在交易结束后恢复（suspend/resume） Observe Mode；交易开始前射频场消失时也会恢复。

这个方法管的只是 Observe Mode 下的那一笔 HCE 交易，NFC 调度优先级与它无关。普通标签应用本来就在调用资格之外；钱包也要等轮询序列匹配自身过滤规则后再调用，免得对任意终端放行。

<!-- gracker-diagram: a272-08-observe-one-transaction -->
![ObserveMode按调用资格临时放行一笔HCE交易](../../assets/diagrams/ch24/a272-08-observe-one-transaction.png)

图：退出帧、自动交易过滤和Reader注释帧另查NFCC支持；Android扩展不保证POS识别。

### 退出帧与注释帧的能力查询

退出帧让 NFCC 固件在特定的自动交易轮询过滤器命中时离开 Observe Mode；我们判断它可用与否，看 `isExitFramesSupported()`——固件支持、且控制器报告了至少一个可用退出帧，它才会返回 `true`。

`isReaderModeAnnotationSupported()` 同样来自设备能力。`NfcProprietaryCaps` 解析控制器上报的厂商能力数据，里面就有节电模式、自动交易过滤器、退出帧数量和 Reader Mode 注释帧支持。

Reader Mode 注释帧是读卡端 Android 设备放进 NFC-A 轮询序列的一段字节数据；另一台处于 Observe Mode 的 Android 设备经 `HostApduService.processPollingFrames()` 收到一个未知类型帧。POS（Point of Sale，销售点支付终端）并不保证识别这种 Android 扩展；AID 选择、终端支付内核和支付协议协商仍按各自的流程走。

## 6. NFC 节电模式

API 37 SDK 提供三个接口：

- `isPowerSavingModeSupported()`
- `isPowerSavingModeEnabled()`
- `setPowerSavingMode(boolean)`

`setPowerSavingMode()` 需要签名或特权级的 `NFC_SET_CONTROLLER_ALWAYS_ON` 权限。它设置的是 NFC 下次关闭时是否进入节电模式；NFC 已关闭时调用则立即生效。生效后芯片保持极低功耗而非完全断电，NFCC 与主处理器的通信受限，其他 NFC API 也一并停用。

`NfcService.setPowerSavingModeInternal()` 会根据当前 NFC 适配器状态临时启停芯片，再调用设备实现；查询 SE 访问权限、准备发送首选支付服务变化事件的代码，在节电模式中也会提前返回。这套机制服务于系统待机和硬件集成——指望它加速 HCE 响应，或在用户靠近终端时动态切换，都用错了地方。

`NfcService.isPowerSavingModeSupported()` 在 NFC 适配器未开启时直接返回 `false`，开启后才向设备抽象层 `DeviceHost` 查询能力。所以 NFC 关着时拿到的 `false` 只说明当下没开；系统集成代码要等开启后再查，把它长期缓存成“硬件不支持”是要误判的。

<!-- gracker-diagram: a272-09-power-saving-state-and-support -->
![节电模式能力必须结合适配器状态判断](../../assets/diagrams/ch24/a272-09-power-saving-state-and-support.png)

图：分别测静态功耗、恢复可发现时间与失败；不从“节电”这个名字推导交易更快。

系统集成方评估这个模式，要分开测这几项：

- NFC 关闭后的静态功耗；
- 从节电模式恢复到可发现状态的时间；
- 不同 NFCC 和固件版本的支持情况；
- 恢复失败、NFC 适配器状态切换和 SE 可用性；
- 屏幕、锁屏、Doze 待机模式与设备厂商电源策略的组合。

普通应用根据 NFC 适配器状态和公开能力返回值处理界面就够了，反射调用隐藏接口、申请拿不到的特权权限都走不通。

## 7. HCE 与 off-host 的职责划分

| 层 | Android HCE | Off-host Secure Element |
| --- | --- | --- |
| AID 注册 | `host-apdu-service`，可静态或按公开 API 动态注册 | `offhost-apdu-service` 声明已存在于 eSE / UICC 的 AID |
| APDU 执行 | 应用 `HostApduService` | SE 中的卡应用（applet） |
| 服务绑定 | 系统绑定应用服务 | 交易时不会启动或绑定声明用的 Android 服务 |
| 密钥位置 | 由钱包方案决定，可能结合 Android Keystore、可信执行环境（TEE）或服务端 | 通常由 SE 安全域与 applet 管理 |
| Android 可观测点 | 服务绑定、Binder、应用 Trace、NFC 服务日志 | 路由和交易事件可见，applet 内部耗时一般不可见 |

回到两条卡模拟路线的分工：表里的 `OffHostApduService` 只是一份路由声明，交易发生时真正处理 APDU 的是 SE 里的卡应用，这个 Android Service 全程停留在声明层面；想借 Android 卡模拟 API 任意控制 SE 的交易 APDU，平台并没有给出这样的能力。

OMAPI（Open Mobile API）是应用访问 SE 的另一套接口，访问规则独立，与 NFC 终端侧的 APDU 通道各走各的。

支付令牌化（tokenization，用受限令牌替代真实卡号）、动态密码、持卡人验证、离线额度、风险控制、收单结果和终端认证，都由具体支付方案决定；AOSP 没有提供统一配置这些策略的公开 NFC API，这些规则因此留在支付方案一侧，写不进 Android 平台能力。

## 8. 可复现的性能测量

### 8.1 时间点要来自两端

只记 `processCommandApdu()` 的耗时，会漏掉服务首次绑定和射频通信。我们至少要在两端记下这些时间点：

| 时间点 | 采集位置 | 能回答的问题 |
| --- | --- | --- |
| `T_field` | 外部读卡器 / NFC 协议分析仪 | 手机何时进入射频场 |
| `T_select_tx` | 外部读卡器 | 终端何时发出 `SELECT AID` |
| `T_apdu_in` | `HostApduService` | 命令何时到达应用 |
| `T_response_ready` | 应用 Trace | 应用何时生成响应 |
| `T_response_rx` | 外部读卡器 | 终端何时收到 R-APDU |
| `T_deactivate` | 应用与系统日志 | 链路何时结束、为何结束 |

先用外部读卡器自己的时钟计算 `T_response_rx - T_select_tx`，用应用同一单调时钟计算 `T_response_ready - T_apdu_in`。只有建立并校准两端时钟映射后，才可用 `T_apdu_in - T_select_tx` 估算包含射频入站、NFCC、Android 路由与可能绑定的区间、用 `T_response_rx - T_response_ready` 估算包含应用/系统排队、Binder、NCI、NFCC 与射频的回传区间。

未建立映射时，同一测试序号只能关联事件和各端相对间隔，不能直接相减两个设备的时间戳得到单向分段。时间精度应报告工具、时间戳位置与同步误差，不能一概断言某个亚毫秒精度必然可达或必然不可达。

<!-- gracker-diagram: a272-10-two-clock-measurement -->
![外部往返与应用处理可各用本端时钟测量](../../assets/diagrams/ch24/a272-10-two-clock-measurement.png)

图：同序号支持事件关联，不会自动同步两个时钟；分位数连同设备、终端、协议和样本条件报告。

### 8.2 Android 侧只读诊断

这些只读命令保存 NFC 适配器、路由、HCE 绑定和关键日志状态，NFC 配置一个都不会动：

```bash
adb shell cmd nfc status
adb shell dumpsys nfc > nfc-dumpsys.txt
adb shell cmd nfc help
adb logcat -v threadtime \
  -s NfcService NfcHostEmulationManager RegisteredAidCache CardEmulationManager
```

`dumpsys nfc` 会输出 NFC 适配器状态、屏幕状态、节电模式、Observe Mode、轮询与监听技术、当前发现参数、卡模拟管理器、路由表和 NFC 事件日志。`cmd nfc help` 还会列出修改 Observe Mode、Reader Mode、路由与控制器常开状态的命令，其中多数需要 `root`（超级用户） 权限，只适合受控测试设备；日常排查用 `status` 与 `dumpsys` 就够。

HCE 源码在对应功能开关（feature flag）启用时，还会写入 `hce_active`、`hce_bind_payment_service`、`hce_bind_service`、`hce_command_apdu`、`hce_response_apdu` 和 `hce_polling_frames` 异步 Trace。`hce_command_apdu` 从系统发出命令开始，到应用 `Handler` 完成回调并回复确认消息（ACK）为止；应用返回 `null` 之后继续跑的异步工作，落在这个区间之外。`hce_response_apdu` 覆盖应用发送响应到系统回复 ACK 的过程。

<!-- gracker-diagram: a272-07-trace-command-versus-response -->
![命令ACK、应用异步工作和响应ACK分别测量](../../assets/diagrams/ch24/a272-07-trace-command-versus-response.png)

图：同步回调计时不含返回null后继续运行的异步工作；响应ACK也不替代外部读卡器接收时间。

这些 slice 要在设备构建启用相应功能开关后才会产生；slice 缺席，说明不了 NFC 是不是在正常工作。

### 8.3 指标按场景分组

保存分位数与错误分类，别只报平均值：

- 首个 `SELECT AID` 到应用的 P50、P95 和 P99，即 50%、95% 和 99% 样本不超过的耗时；
- 各类命令 APDU（C-APDU）的应用处理与端到端往返分布；
- 进程尚未启动、进程已在运行、首选支付服务和普通 HCE 服务；
- 屏幕开关、锁屏、用户已解锁、默认钱包角色与前台偏好；
- 手机型号、NFCC、固件、终端型号、终端配置和持机姿态；
- 成功、AID 未路由、需要解锁、服务绑定失败、链路丢失和终端超时；
- CPU 调度延迟、主线程阻塞、内存分配量、垃圾回收（GC）、本地存储与后端请求。

实验安排上，我们同一次只改一个变量，并记录系统版本、NFC 模块版本、应用版本和测试卡配置。支付终端自身有协议超时和重试策略，Android 侧没有公开统一的 APDU 响应时限，目标值应来自所用协议、认证要求和目标终端组合。

## 9. 故障现象与定位入口

| 现象 | 优先检查 |
| --- | --- |
| 目标 SDK 改为 37 后，NFC 标签不再启动 Activity | Activity 的 `DISPATCH_NFC_MESSAGE` 保护、应用是否被强行停止、NDEF 或标签技术过滤器 |
| HCE 服务从未收到 `SELECT AID` | AID、类别、钱包角色、前台偏好、锁屏与亮屏要求、路由表 |
| 只有首个 APDU 慢 | `hce_bind_service`、进程启动、类初始化、首个磁盘读取 |
| 所有 APDU 都慢 | 主线程 Trace、锁竞争、分配与 GC、密钥操作、数据库或网络 |
| 应用已生成响应但终端仍超时 | `Messenger` 回传、NFC 服务状态、NCI、NFCC、射频链路和终端协议 |
| Observe Mode 一直不进入交易 | 调用方是否为钱包或首选服务、是否已有活动交易、控制器与退出帧能力 |
| 只在某款手机失败 | 天线位置、NFCC 能力、固件、厂商 NFC 硬件抽象层（HAL）、休眠与中断 |
| off-host 交易慢但 HCE 正常 | SE 路由、applet、NFC 执行环境（NFCEE）链路、终端和厂商实现 |

应用收不到回调时，我们先看 `dumpsys nfc` 里的已绑定服务、AID 缓存和路由表，再看应用日志；确认系统已把 AID 路由到目标组件之后，才轮到分析应用的 APDU 处理时间。

## 10. 内核与厂商实现

内核版本基线为 `android17-6.18-2026-06_r6`。NFC 控制器可能挂在 I²C、SPI、UART 等芯片间总线或厂商专用通道上；驱动、设备树、时钟、电源域、IRQ 和挂起/恢复的行为，还可能出自 SoC 或 OEM 的私有分支。Android common kernel 标签只是共用内核的分析起点，某款设备用的是哪个 NFC 驱动，从它上面看不出来。

拿到下面这些线索，我们再去查内核与厂商实现：

- NFCC IRQ 长时间得不到调度；
- 总线传输出现异常重试、超时或运行时电源管理（runtime PM）唤醒延迟；
- 系统挂起并恢复后，NFCC 状态丢失；
- 原生 NFC 协议栈已发出命令，但厂商 HAL 或传输层没有响应；
- 问题只跟某个 NFCC、固件或 OEM 构建相关。

AID 选择、HCE 服务绑定、`processCommandApdu()` 主线程和钱包角色属于 Android 框架或 NFC 模块的行为，仅凭内核调度器状态是直接推不出来的；跨层排查时保留同一交易序号，应用 Trace、NFC 日志、HAL 日志、内核事件和外部读卡器记录才能相互对应。

<!-- gracker-diagram: a272-11-nfc-evidence-layers -->
![按分发、服务、控制器与外部终端分层取证](../../assets/diagrams/ch24/a272-11-nfc-evidence-layers.png)

图：共同内核标签只是边界起点；具体驱动、设备树、固件与支付协议仍以目标设备和终端证据为准。

## 11. 性能改动的安全约束

HCE 服务由 `BIND_NFC_SERVICE` 保护，只有 Android 系统能绑定，APDU 因此经由 NFC 系统进入应用。这项权限只管到“谁能绑定”；支付协议认证、密钥保护、支付令牌生命周期和重放防护，仍要应用自己完成。

做性能改动时，至少要守住下面这些约束：

- 不把密钥、PAN、完整 APDU、动态密码或可关联账户的支付令牌写入日志；
- 不为减少一次 I/O 而延长支付令牌有效期、复用计数器或跳过状态校验；
- 停用后不再主动提交旧结果，并由协议识别已入队的迟到响应；
- 不把服务端失败映射成成功状态字；
- 不因追求冷启动速度而导出无保护组件、放宽 `BIND_NFC_SERVICE` 或解锁要求；
- 按支付方案的认证要求和目标终端集合验证性能版本；两台 Android 手机之间的对测，当不了唯一依据。

## 12. Android 17 迁移与评审清单

- [ ] 源码锚定 `packages/modules/Nfc` 的 `android-17.0.0_r1`。
- [ ] 目标 SDK 为 37 的 NFC `Intent` Activity 使用 `DISPATCH_NFC_MESSAGE` 保护。
- [ ] 已移除 `ACTION_TAG_DISCOVERED` 依赖，URL 标签按 Android App Links 处理。
- [ ] Reader Mode 只注册必要技术，正确处理 I/O 异常与 `onTagLost()`。
- [ ] HCE 服务声明 `BIND_NFC_SERVICE`，AID 组、类别和钱包角色正确。
- [ ] `processCommandApdu()` 主线程无磁盘、数据库和网络阻塞。
- [ ] 异步工作在 `onDeactivated()` 后失效；发送前检查与已入队无法撤回的边界已明确，协议能拒绝迟到或重放响应。
- [ ] Observe Mode、退出帧、注释帧和节电模式都经过能力与权限判断。
- [ ] 外部读卡器与 Android Trace 同时采样，首次绑定与已绑定场景分别统计。
- [ ] 日志不含支付敏感数据，缓存策略没有削弱认证和防重放。
- [ ] 厂商问题按 NFCC、固件、HAL、驱动和内核 `android17-6.18-2026-06_r6` 分层取证。

## 全文小结

标签分发、Reader Mode、HCE 与 off-host 卡模拟走不同的路由，数据经过的进程也不同；Android 17 的 Intent 保护、标签离场回调、Observe Mode 和控制器能力变化也各对各的入口。先把模式、目标 SDK、钱包角色和硬件能力确认清楚，再谈性能。

HCE 延迟要拆成射频激活、AID 路由、服务绑定、应用处理、响应回传和外部支付协议，其中只有应用处理这一段能由 `HostApduService` 直接优化。可靠测量靠外部读卡器与 Android Trace 的关联；缓存、日志和异步执行的任何调整，都不得削弱密钥、令牌、重放防护和交易生命周期方面的安全约束。

## 参考资料

- [Android 17 / API 37 android.nfc API diff](https://developer.android.com/sdk/api_diff/37/changes/pkg_android.nfc)
- [Android Developers：NFC basics](https://developer.android.com/develop/connectivity/nfc/nfc)
- [Android Developers：Host-based card emulation](https://developer.android.com/develop/connectivity/nfc/hce)
- [Android Developers：NfcAdapter API](https://developer.android.com/reference/android/nfc/NfcAdapter)
- [Android Developers：ReaderCallback API](https://developer.android.com/reference/android/nfc/NfcAdapter.ReaderCallback)
- [Android Developers：TagTechnology API](https://developer.android.com/reference/android/nfc/tech/TagTechnology)
- [Android Developers：HostApduService API](https://developer.android.com/reference/android/nfc/cardemulation/HostApduService)
- [AOSP `android-17.0.0_r1`：NfcAdapter.java](https://android.googlesource.com/platform/packages/modules/Nfc/+/android-17.0.0_r1/framework/java/android/nfc/NfcAdapter.java)
- [AOSP `android-17.0.0_r1`：HostApduService.java](https://android.googlesource.com/platform/packages/modules/Nfc/+/android-17.0.0_r1/framework/java/android/nfc/cardemulation/HostApduService.java)
- [AOSP `android-17.0.0_r1`：NfcDispatcher.java](https://android.googlesource.com/platform/packages/modules/Nfc/+/android-17.0.0_r1/NfcNci/src/com/android/nfc/NfcDispatcher.java)
- [AOSP `android-17.0.0_r1`：NfcService.java](https://android.googlesource.com/platform/packages/modules/Nfc/+/android-17.0.0_r1/NfcNci/src/com/android/nfc/NfcService.java)
- [AOSP `android-17.0.0_r1`：HostEmulationManager.java](https://android.googlesource.com/platform/packages/modules/Nfc/+/android-17.0.0_r1/NfcNci/src/com/android/nfc/cardemulation/HostEmulationManager.java)
- [AOSP `android-17.0.0_r1`：NfcProprietaryCaps.java](https://android.googlesource.com/platform/packages/modules/Nfc/+/android-17.0.0_r1/NfcNci/src/com/android/nfc/NfcProprietaryCaps.java)
- [AOSP `android-17.0.0_r1`：NfcShellCommand.java](https://android.googlesource.com/platform/packages/modules/Nfc/+/android-17.0.0_r1/NfcNci/src/com/android/nfc/NfcShellCommand.java)
- [Android common kernel：android17-6.18-2026-06_r6](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6)
