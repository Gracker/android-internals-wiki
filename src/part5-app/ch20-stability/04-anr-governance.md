---
title: ANR 治理策略
chapter: '20.4'
section: '20.4'
status: finalized
applicable_versions: Android 10 (API 29) - Android 17 (API 37)
last_verified: '2026-08-14'
last_verified_against: AOSP android-17.0.0_r1; Android Developers ANR, API 37 warning, API 36 profiling, FGS and Android vitals docs; kotlinx.coroutines 1.11.0 current on 2026-08-14
confidence: medium-high
consolidated_from:
- src/part5-app/ch20-stability/09-stability-case-studies.md#案例三
sources:
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/am/ActivityManagerService.java
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/am/ActivityManagerConstants.java
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/am/BroadcastConstants.java
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/app/ActivityManager.java
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/content/ContentResolver.java
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/services/inputflinger/dispatcher/InputDispatcher.cpp
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/libs/input/android/os/IInputConstants.aidl
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/am/ActiveServices.java
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/app/Service.java
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/os/Binder.java
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/content/BroadcastReceiver.java
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/am/ContentProviderHelper.java
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/am/CachedAppOptimizer.java
- type: aosp
  path: https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/runtime/monitor.cc
- type: official
  path: https://developer.android.com/topic/performance/vitals/anr
- type: official
  path: https://developer.android.com/topic/performance/anrs/diagnose-and-fix-anrs
- type: official
  path: https://developer.android.com/topic/libraries/architecture/workmanager
- type: official
  path: https://developer.android.com/reference/android/app/ActivityManager
- type: official
  path: https://developer.android.com/reference/android/app/AnrWarningResult
- type: official
  path: https://developer.android.com/reference/android/app/ApplicationExitInfo.AnrInfo
- type: official
  path: https://developer.android.com/reference/android/os/ProfilingTrigger#TRIGGER_TYPE_ANR
- type: official
  path: https://developer.android.com/develop/background-work/services/fgs/timeout
- type: official
  path: https://developer.android.com/develop/background-work/services/fgs/service-types
- type: official
  path: https://developer.android.com/topic/libraries/app-startup
- type: official
  path: https://developer.android.com/reference/android/content/SharedPreferences.Editor
- type: official
  path: https://developer.android.com/reference/android/content/BroadcastReceiver
- type: clippings-structure-ref
  path: Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 2.md
- type: clippings-structure-ref
  path: Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 8.md
tags:
- anr
- main-thread
- binder
- lock-contention
- watchdog
- broadcast
- contentprovider
related_chapters:
- '20.1'
- '9.1'
- '9.2'
- '1.3'
- '1.1'
pipeline_stage: ready-to-publish
task6_state: reviewed
task9_state: reviewed
task2b_state: fixed
---

# ANR 治理策略

ANR（Application Not Responding，应用无响应）是系统对应用在特定时限内未完成响应的判定。它可能来自输入分发、组件回调、进程启动、Binder 等待或锁竞争；主线程卡顿是常见成因之一。治理工作要把 ANR 类型、计时起止点和阻塞线程对应起来，再决定移出主线程、缩短临界区、调整进程间协议，还是修复组件生命周期。

[9.1 ANR 机制、类型与触发条件](../../part2-performance/ch09-anr/01-anr-mechanism-types-triggers.md) 和 [9.2 ANR 与 Kernel Trace 联合诊断](../../part2-performance/ch09-anr/02-anr-kernel-trace-diagnosis.md) 已经说明系统判定与现场分析。平台源码按 Android 17 / API 37 / `android-17.0.0_r1` 核对，这里关注修复动作、预警能力和回归验证。

本文中的 ANR traces 指系统在 ANR 现场采集的线程堆栈与诊断信息；后文的 system trace 和 `Trace` section 指性能时间线及其中的标记区间。两类证据用途不同，分析时不能混用。

## ANR 触发场景与超时阈值

Android 不存在覆盖所有 ANR 的统一“5 秒计时器”。`InputDispatcher`、广播队列、`ActiveServices` 和 `ContentProviderHelper` 各自维护状态与时限；冷启动和线程排队会消耗窗口，Android 14 及以上的广播窗口还会在进程无法获得足够 CPU 时间时扩展。排查时先用 ANR 主题（报告中的概要描述）、`ApplicationExitInfo`、系统 traces 和事件日志确定类型。

### 常见计时器

下表列出排查时可使用的基线。数值描述的是 AOSP 或官方文档的默认行为，设备厂商可以通过资源、设备配置或系统属性调整。部分 AOSP 常量还会乘以硬件超时系数（`Build.HW_TIMEOUT_MULTIPLIER`，由系统属性统一放大相关时限，通常为 1）。应用不能把系统上限当作自己的执行预算。

| 类型 | Android 17 基线 | 计时范围与边界 |
|---|---|---|
| 输入分发 | 常见基线为 5 秒，并应用硬件超时系数 | `InputDispatcher` 按目标应用或窗口的分发超时判断；“无焦点窗口”等场景也有独立状态。5 秒不能简化成“触摸事件进入主线程后开始计时”，目标窗口、焦点和待确认事件都参与判定。 |
| 前台优先级广播 | Android 13 及以下为 10 秒；Android 14 及以上为 10～20 秒 | `Intent.FLAG_RECEIVER_FOREGROUND` 决定短窗口。Android 14 及以上在进程 CPU 饥饿时可扩展到上限；冷启动也占用时间。 |
| 后台优先级广播 | Android 13 及以下为 60 秒；Android 14 及以上为 60～120 秒 | 未设置 `FLAG_RECEIVER_FOREGROUND` 时使用长窗口。`goAsync()` 延续同一次计时，截止点变为 `PendingResult.finish()`。 |
| 执行 Service | 前台 20 秒，后台 200 秒，再应用硬件超时系数 | AOSP 的服务执行基线由 `ActivityManagerConstants` 管理；冷启动以及 `onCreate()`、`onBind()`、`onStartCommand()` 都可能消耗窗口。 |
| 发布 ContentProvider | 10 秒 × 硬件超时系数 | `ContentResolver.CONTENT_PROVIDER_PUBLISH_TIMEOUT_MILLIS` 约束应用启动阶段的 provider 发布。provider 就绪等待、远程请求无响应属于另外的检测路径，不能都叫“10 秒 publish 超时”。 |
| 短时前台服务 | 约 3 分钟，随后还有短暂宽限 | Android 14 及以上的 `shortService` 到期会收到 `Service.onTimeout()`；继续不停止会进入短时前台服务 ANR 路径。具体值由系统配置决定。 |

广播文档里的“前台”和“后台”描述的是 Intent 优先级标志，不等同于应用界面是否可见。服务表里的前台/后台则是系统用于选择执行超时的服务状态。两个维度不要混用。

输入超时也不能只看主线程。窗口没有焦点、目标窗口迟迟未创建、应用正在等待同步 Binder 返回，都会表现为输入没有按时完成。修复前应从 ANR 类型和 traces 还原计时期间发生了什么。

### 前台服务的三类时限

FGS（Foreground Service）指前台服务。相关故障经常把三套计时器混在一起：

| 约束 | Android 17 AOSP 行为 | 超时结果 |
|---|---|---|
| `startForegroundService()` 后转入前台状态 | `mServiceStartForegroundTimeoutMs` 默认 30 秒；系统随后还有 `mServiceStartForegroundAnrDelayMs` 默认 10 秒的处理窗口 | 未及时调用 `startForeground()` 会进入 start-foreground-service ANR 处理。后台启动限制是另一套准入规则。 |
| `FOREGROUND_SERVICE_TYPE_SHORT_SERVICE` | `mShortFgsTimeoutDuration` 默认约 3 分钟；`onTimeout()` 后还有 `mShortFgsAnrExtraWaitDuration` 默认 10 秒 | 仍未停止服务时触发 ANR。 |
| 以 Android 15 及以上为目标平台的 `dataSync` / `mediaProcessing` | 应用处于后台时，每种类型在 24 小时内累计约 6 小时；用户把应用带到前台会重置额度 | 收到 `onTimeout()` 后仍不停止会抛出内部 `RemoteServiceException` 并导致崩溃，不能归类为 ANR。 |

这些默认值用于读懂 `android-17.0.0_r1`。产品代码仍应在业务可接受的时间内结束工作，不要用系统超时减去一小段时间作为日常预算。

### 从类型进入修复路径

ANR 主题决定后续要看哪条执行路径：

| ANR 主题或类型 | 优先核对的线程与状态 | 常见修复方向 |
|---|---|---|
| input dispatch（输入分发） | 主线程、焦点窗口、同步 Binder、锁持有者 | 缩短主线程任务，移除同步等待，修复焦点或窗口创建异常 |
| broadcast of intent（广播处理） | receiver 所在线程、冷启动、`goAsync()` 工作线程 | 缩短启动与 receiver 工作，使用独立工作线程，保证 `finish()` |
| executing service（执行 Service） | 主线程和进程启动 | 缩短 Application 与 Service 回调，后台执行可中断工作 |
| content provider not responding | provider 发布线程、provider Binder 线程、调用方 | 精简初始化，限制查询成本，修复 Binder 或锁等待 |
| start foreground / short FGS | Service 回调与停止时序 | 按时调用 `startForeground()` 或停止服务，处理 `onTimeout()` |
| job service start/stop | `JobService` 主线程回调 | 立即返回并异步执行，遵守通知与完成协议 |

一份主线程快照只能说明采样瞬间。广播可能运行在自定义 `Handler`，`goAsync()` 工作也可能在后台工作线程（worker）上；主线程出现表示 Looper 正在等待消息的 `nativePollOnce`，不能直接排除这类 ANR。

## 缩短主线程同步工作并异步化

主线程负责 Looper（线程消息循环）消息、组件回调、窗口与输入相关工作。治理目标是让每个同步阶段都有明确的耗时预算、所有等待都有所有者，并让超出预算的工作可以取消、降级或延后。

### 先按工作性质选择执行位置

| 工作 | 合适的执行位置 | 约束 |
|---|---|---|
| 磁盘、网络和其他阻塞 I/O | 专用 executor（负责调度任务的执行器）或 `Dispatchers.IO` | 线程数和排队长度要受控；超时后还要确认底层调用能否取消 |
| JSON 解析、图像处理、压缩等 CPU 工作 | `Dispatchers.Default` 或受控计算线程池 | 并行度应匹配 CPU 和产品负载，不能挤占所有可运行线程 |
| UI 状态提交 | 主线程 | 后台先准备不可变结果，主线程只做短时间状态切换 |
| 需要跨进程的查询 | 后台线程、缓存或异步协议 | 同步 Binder 没有通用调用超时，后文单独说明 |
| 可推迟且需要进程重启后继续的任务 | [WorkManager](https://developer.android.com/topic/libraries/architecture/workmanager) / JobScheduler | 适合持久、可延迟工作，不适合当前页面必须立即得到的结果 |

线程切换只改变执行位置。一个无界队列仍会积压，一个不可取消的 I/O 仍会占住 worker，错误地切回 `Dispatchers.Main` 仍会阻塞界面。

### 协程负责结构，不替代码选择线程

协程调度器按工作性质选择即可：阻塞 I/O 用 `Dispatchers.IO`，CPU 计算用 `Dispatchers.Default`，界面状态用 `Dispatchers.Main`。`Dispatchers.IO` 与 `Default` 的内部池和并行度属于 `kotlinx.coroutines` 版本实现细节，项目升级依赖后可能变化，不应成为业务正确性的前提。

下面的示例展示一个可取消的加载过程。读取和解析在后台完成，主线程只接收已经准备好的结果。

```kotlin
class ArticleRepository(
    private val ioDispatcher: CoroutineDispatcher,
    private val cpuDispatcher: CoroutineDispatcher,
) {
    suspend fun load(path: Path): Article {
        val bytes = withContext(ioDispatcher) {
            Files.readAllBytes(path)
        }
        return withContext(cpuDispatcher) {
            parseArticle(bytes)
        }
    }
}

class ArticleViewModel(
    private val repository: ArticleRepository,
) : ViewModel() {
    fun open(path: Path) {
        viewModelScope.launch {
            val article = repository.load(path)
            _uiState.value = UiState.Content(article)
        }
    }
}
```

这段代码把线程选择作为依赖传入，测试时可以替换调度器。取消协程能阻止后续步骤，但 Java 阻塞 I/O、JNI 或同步 Binder 是否立刻停止，取决于底层 API 是否响应中断或提供取消接口。

### 启动阶段不要制造“异步假象”

`Application.onCreate()`、Activity 创建和 provider 安装共享主线程。启动管理框架能整理依赖顺序，却不会自动把初始化移到后台。

- **[AndroidX App Startup](https://developer.android.com/topic/libraries/app-startup)**：`InitializationProvider` 仍在启动时同步执行 `Initializer.create()`。它适合合并 provider、声明依赖和按需关闭自动初始化；耗时初始化仍需由组件作者设计异步接口。
- **第三方 SDK**：先确认 SDK 是否允许延迟或后台初始化。擅自换线程可能违反其线程约束，造成更晚出现的崩溃或数据缺失。
- **StrictMode**：`detectDiskReads()`、`detectDiskWrites()` 等只负责检测，`penaltyLog()`、`penaltyDeath()` 等策略决定处理方式。StrictMode 不会天然“遇到主线程 I/O 就抛异常”。
- **[SharedPreferences](https://developer.android.com/reference/android/content/SharedPreferences.Editor)**：`apply()` 把磁盘写入排队，但 Android 框架会在部分组件生命周期边界等待尚未完成的 queued work（框架登记的待完成任务）。短时间大量 `apply()` 可能把阻塞推迟到 Activity 或 Service 回调，批量写入和减少频率比机械替换 `commit()` 更可靠。
- **WorkManager**：适合需要持久化、满足约束后再执行的工作。页面打开后立刻需要的结果仍要使用明确的异步接口和界面状态。

启动优化应记录每个初始化项的调用线程、依赖、可延迟条件、失败处理与完成时刻。仅记录“已经异步”无法证明主线程预算得到改善。

### 为主线程任务建立预算

固定 500 毫秒之类的全局阈值会把不同业务混成一类。更稳妥的做法是按场景建立基线：

1. 对冷启动、页面切换、广播、Service 和 provider 分别采样。
2. 记录主线程消息耗时、排队时长、同步 Binder 时间、锁等待和设备状态。
3. 按设备等级、系统版本和温度分组，比较 P50、P95、P99（第 50、95、99 百分位）与长尾。
4. 结合输入响应和系统 ANR 数据设置内部告警线；告警线应早于对应系统窗口，并保留足够安全余量。
5. 每次修复同时验证成功路径、失败路径、取消路径和进程重建。

内部告警线服务于趋势发现。超过告警线叫“主线程 stall（长时间未继续处理消息）”或“ANR 风险事件”更准确，系统尚未判定时不要直接记为 ANR。

## IPC（Binder）调用治理

IPC（inter-process communication）指进程间通信，Binder 是 Android 的主要 IPC 机制。同步 Binder 调用会让调用线程等待对端处理完成。Binder 驱动没有给每笔普通同步事务提供应用可配置的通用超时；对端进程 CPU 饥饿、Binder 线程池占满、锁等待或再次调用其他进程，都可能把等待拉长。

### 调用方要控制等待位置与协议

主线程上的同步 Binder 只适合经过测量、结果稳定且无法替代的轻量操作。更常见的处理方式包括：

- 缓存变化不频繁的系统信息，明确缓存失效条件，避免在绘制或输入路径重复查询。
- 合并多次小事务，减少往返和 Parcel（Binder 传递参数时使用的序列化容器）开销；单次数据量仍要受 Binder 事务大小限制。
- 把外部服务调用放到受控后台线程，并给业务结果设计超时、默认值或稍后重试。
- 对自有 AIDL（Android Interface Definition Language，Android 接口定义语言）设计异步回调或可取消请求，使用 request ID（请求标识）丢弃迟到结果。
- 只有调用语义允许单向投递时才使用 AIDL 的 `oneway`。调用方提交后不等返回，但远端处理速度跟不上时，事务会在队列中积压，这就是这里所说的背压。它不是同步调用的通用修复。

`Future.get(timeout)` 等待后台任务时，可以让调用方在超时后停止等待，但执行 Binder 事务的后台工作线程仍可能被占用。协程 `withTimeout` 会发出取消信号，阻塞式 Binder 事务通常不会响应这次取消，工作线程仍要等远端返回。两种写法都不能终止远端正在执行的 `onTransact()`；主线程也不应阻塞等待这类结果。

### 服务端也会制造调用方 ANR

远程 Binder 调用通常进入服务端 Binder 线程池。服务端常见风险有：

- `onTransact()` 把工作同步切到主线程，再等待主线程返回。
- Binder 线程持锁执行磁盘、网络、回调或嵌套 Binder 调用。
- 所有 Binder 线程都被长事务占住，新请求只能排队。
- 服务端持有锁调用客户端回调，客户端又请求服务端同一把锁，形成跨进程环路等待。
- 大对象频繁序列化，占用 Binder 线程和内存带宽。

自有服务应记录接口名、请求 ID、调用方、排队时间、执行时间和结果状态。生产环境的观测代码优先放在自有客户端代理（proxy）、服务端桩（stub）或调用点。依赖隐藏的 `BinderProxy.transactNative()` Hook（拦截内部调用入口）容易随系统实现变化，也可能与运行时或其他 SDK 冲突。系统服务问题可结合 Perfetto、线程采样和系统 traces 判断；`system_server` 是承载 ActivityManager 等 Android 系统服务的进程。

外部 Service 变慢不会自动给 ContentProvider 判 ANR。应用线程在 provider 发布、provider 请求或其他受监控阶段同步等待该 Service，系统计时器到期后，才会形成相应类型的 ANR。

## 锁竞争与死锁预防

主线程等待锁时，堆栈通常停在 `BLOCKED`（等待进入 Java `synchronized` 监视器）、`LockSupport.park()`（线程被并发工具暂停）、`Object.wait()`（等待其他线程通知）或 native mutex（本地代码互斥锁）。修复要沿着“谁持锁、持锁期间做了什么、是否存在反向依赖”追到持锁线程。

下面这段线程摘录用于识别双锁环路，`held by tid=...` 表示该锁当前由哪个线程持有。

```text
"main" tid=1 BLOCKED
  waiting to lock <0x01> held by tid=8

"worker-1" tid=8 BLOCKED
  waiting to lock <0x02> held by tid=1
```

主线程持有 `<0x02>` 等 `<0x01>`，worker 持有 `<0x01>` 等 `<0x02>`，两条依赖构成环。延长超时或增加线程数都不能修复这类死锁。

### 锁设计的工程约束

- **固定获取顺序**：需要多把锁时，在模块内规定稳定顺序，并用代码审查或测试检查反向获取。
- **临界区只保留内存状态变更**：磁盘、网络、Binder、等待 future（代表尚未完成结果的句柄）和外部回调都放到锁外。可以在锁内生成不可变快照，锁外执行耗时操作。
- **明确数据所有者**：单线程所有权、不可变对象或消息传递常比多处共享可变状态更容易验证。
- **主线程可以持有短而无竞争的锁**：绝对禁止会逼出复杂的无锁代码。需要禁止的是不可控等待和锁内阻塞。
- **粗锁与细锁都要测量**：一把粗锁减少嵌套，却可能扩大竞争；多把细锁降低局部冲突，也会增加顺序错误。选择取决于访问模式。
- **原子类只保护对应的原子操作**：`volatile`、`AtomicReference` 和并发容器无法自动保护跨字段不变量或“检查后执行”。
- **`tryLock()` 需要安全退路**：超时后必须能返回旧值、跳过非必要工作或重试。业务必须等待结果时，`tryLock()` 只会把失败改成另一种表现。

`Thread.getStackTrace()` 可以从监测线程取得处于 `BLOCKED` 状态的主线程栈。线上样本还要采集锁持有者和相邻线程，否则只能看到“主线程在等”，看不到等待为何没有结束。

### 把跨进程调用纳入锁图

下面的顺序很容易在单进程代码审查中漏掉：

1. 应用主线程持有锁 A，同步调用远端服务。
2. 远端服务处理请求时回调应用 Binder 接口。
3. 应用 Binder 线程处理回调时也需要锁 A。
4. 主线程等远端返回，Binder 线程等主线程释放锁 A。

锁 A 只存在于应用进程，等待环却跨过了 Binder。规则仍相同：持锁期间不调用未知代码，也不做同步 IPC。

## ContentProvider / BroadcastReceiver 超时治理

组件 ANR 的计时范围常常比组件方法本身更长。冷启动、前置初始化和线程排队都可能包含在系统窗口中，因此只测 `onReceive()` 或 `onStartCommand()` 的函数耗时不够。

### ContentProvider：区分发布和请求

应用冷启动时，`ActivityThread` 安装清单中的 provider，并在 `Application.onCreate()` 之前调用 provider 的 `onCreate()`。多个自动初始化 provider 会依次占用同一条启动路径。治理动作包括：

- provider 的 `onCreate()` 只完成注册和必要状态创建，数据库迁移、网络访问和大文件读取移到可控时机。
- 关闭不需要的 SDK 自动初始化 provider；如果使用 AndroidX App Startup，要逐个审计 `Initializer.create()`，不能把合并成一个 provider 当成异步优化。
- 把可延迟组件改为显式按需初始化，并处理并发首次访问、失败重试和进程重建。
- 记录“进程启动 → provider 安装 → `Application.onCreate()`”的分段时间，不能只统计 provider 方法内部。

provider 发布完成后，`query()`、`insert()`、`call()` 等入口还可能被并发调用。远程调用经 Binder 线程进入进程；同进程调用则可能在调用线程直接执行。provider 实现不能依赖“所有方法都在主线程”，也不能用一把大锁包住数据库、文件和 IPC。

Android 17 的 publish 基线来自 `ContentResolver.CONTENT_PROVIDER_PUBLISH_TIMEOUT_MILLIS`。`ContentProviderHelper` 中等待 provider 就绪、请求方检测 provider 无响应等路径有各自的条件和时限。报告里必须保留 ANR 类型和描述，不能看到 provider 名称就套用 10 秒发布结论。

#### 案例：清单合并引入的 SDK Provider

一次 SDK 升级后，冷启动 P95 和启动附近 ANR 同时上升，主线程栈停在 SDK Provider 的 `onCreate()`。这仍只是候选位置，应依次验证同步磁盘、数据库迁移、Binder/网络等待、类加载与 page fault（访问的内存页尚未映射，需要内核补齐映射，部分情况会读取存储），以及 `Application.onCreate()` 本身的区间。

调查从 release variant（用于发布的构建变体）的 merged manifest（应用清单合并结果）开始，记录 Provider 的来源依赖、authority（系统识别 Provider 的唯一名称）、process（所属进程）、`initOrder`（初始化顺序）、direct-boot（用户解锁前可否运行）属性和官方关闭自动初始化方式。Android 17 的 `ActivityThread.handleBindApplication()` 会先安装本地 Provider，再调用 `Application.onCreate()`；清单合并加入的组件即使没有被业务主动调用，也可能占用启动主线程。外部 Provider 访问、Job、Service、Broadcast 或推送还可能触发非桌面启动，数据必须携带启动原因和进程名。

自有 Provider 可用稳定的 Trace section（性能时间线中的命名区间）标记短区间：

```kotlin
class DiagnosticsProvider : ContentProvider() {
    override fun onCreate(): Boolean {
        Trace.beginSection("DiagnosticsProvider#onCreate")
        return try {
            installLightweightHooks(requireNotNull(context).applicationContext)
            true
        } finally {
            Trace.endSection()
        }
    }
}
```

trace 只负责测量，不会让初始化变快。`installLightweightHooks()` 只能保留主线程可接受的注册工作。明确支持后台执行的磁盘与解析可以移出 Provider；可延迟能力改为按需初始化；要求主线程的 SDK 步骤仍保留在主线程并压缩。不能把所有初始化统一丢给 `Dispatchers.IO`，否则调用方可能在初始化完成前访问能力，或违反 SDK 的线程约束。

修复后至少重放全新安装、数据库 schema（表和字段结构）跨版本覆盖升级、桌面/Provider/Service/Broadcast/Job/推送启动、主/独立进程、离线/弱网、初始化完成前立即调用和多调用方并发等待。Macrobenchmark 用于批量测量启动性能分布，Perfetto 用时间线确认主线程区间，`ApplicationStartInfo` 对齐系统记录的启动节点，`ApplicationExitInfo` 和 ANR traces 复核进程退出与现场栈。若 P95、P99 等高百分位启动延迟下降，但 SDK 初始化失败率上升，修复仍不合格。

### BroadcastReceiver：`goAsync()` 不增加时间

静态注册的 receiver 通常由主线程执行；使用 [`registerReceiver(..., scheduler)`](https://developer.android.com/reference/android/content/BroadcastReceiver) 可以通过 `Handler` 指定接收线程。换到后台线程能保护 UI 响应，但 receiver 仍受广播期限约束，线程池排队也会消耗时间。

`goAsync()` 返回的 `PendingResult` 允许 `onReceive()` 返回后继续处理。系统从分发广播开始计时，直到 `PendingResult.finish()`；异步工作沿用原有截止时间。进程在 receiver 完成后也可能被回收，需要保证进程重建后继续的工作应交给 WorkManager 或 JobScheduler。

下面的示例只适合能在广播期限内完成、支持协程取消的短任务。`receiverScope` 由应用统一持有，避免每次广播创建无人管理的作用域。

```kotlin
class SyncReceiver(
    private val receiverScope: CoroutineScope,
    private val processor: SyncProcessor,
) : BroadcastReceiver() {

    override fun onReceive(context: Context, intent: Intent) {
        val pending = goAsync()
        receiverScope.launch {
            try {
                withTimeout(processor.internalBudgetMillis) {
                    processor.handle(intent)
                }
            } finally {
                pending.finish()
            }
        }
    }
}
```

这里的内部预算必须短于对应广播窗口，并由线上基线确定。`processor.handle()` 还要能响应取消；若它进入不可取消的阻塞调用，`withTimeout` 无法保证按时执行到 `finish()`。超过广播窗口或要求进程重建后继续的任务，应在 `onReceive()` 中只入队持久任务。

### Service：生命周期回调必须很短

`Service.onCreate()`、`onStartCommand()`、`onBind()` 和 `onDestroy()` 默认都在应用主线程。执行 Service ANR 的窗口还可能包含进程冷启动，因此 Service 自身方法看起来很快，也要检查 `Application` 和 provider。

- 回调内完成参数校验、状态切换和任务调度，然后返回。
- 后台工作使用由 Service 持有的 executor 或协程作用域；`onDestroy()` 取消任务并释放资源，避免 Service 销毁后工作仍继续占用线程。
- `startForegroundService()` 后尽早准备并发布通知，不要等待网络、数据库或远端配置。
- `shortService` 实现 `onTimeout()` 并立即停止；测试超时、重复 start 和进程重建。
- 以 Android 15 及以上为目标平台时，`dataSync`、`mediaProcessing` 等受总额度约束的 FGS 要实现 `onTimeout()`，超时后停止，避免被系统以异常结束进程。

返回 `START_STICKY` 只决定服务被杀后的重建策略，不会缩短当前回调，也不会豁免 ANR 时限。

## ANR Watchdog（看门狗）搭建

Watchdog 是周期检查目标是否仍能响应的看门狗式监测器。应用 Watchdog 通过后台线程向主 Looper 投递探针（供主线程执行的轻量 `Runnable`），测量探针多久才被执行。它能发现主 Looper 长时间没有响应，不能复刻 InputDispatcher、广播、Service、provider 和 `system_server` 的全部判定条件。

### 避免探针互相确认

常见示例每个周期把共享计数标记（tick）清零，再投递相同的 `Runnable` 任务。旧探针晚到时可能把新周期标记为成功，连续阻塞也会在主队列里堆积探针。生产实现应始终只保留一个待确认 token（本轮探针的唯一标识），让 `Runnable` 只能确认自己的 token。

下面的精简实现展示单探针设计。`uptimeMillis()` 是设备启动以来、不计深度休眠时间的单调时钟，不受用户修改系统时间影响；系统多条 ANR 计时路径也使用这一时间基准。示例让同一次 stall 只上报一次。

```kotlin
data class MainStallSample(
    val delayedMillis: Long,
    val mainStack: Array<StackTraceElement>,
)

class MainLooperWatchdog(
    private val pollMillis: Long,
    private val stallThresholdMillis: Long,
    private val onStall: (MainStallSample) -> Unit,
) : Thread("main-looper-watchdog") {

    private val mainHandler = Handler(Looper.getMainLooper())
    private val mainThread = Looper.getMainLooper().thread
    private val nextToken = AtomicLong(0L)
    private val pendingToken = AtomicLong(0L)
    private val postedAt = AtomicLong(0L)
    private val reportedToken = AtomicLong(0L)

    override fun run() {
        while (!isInterrupted) {
            val now = SystemClock.uptimeMillis()
            val token = pendingToken.get()

            if (token == 0L) {
                val newToken = nextToken.incrementAndGet()
                postedAt.set(now)

                if (pendingToken.compareAndSet(0L, newToken)) {
                    val accepted = mainHandler.post {
                        pendingToken.compareAndSet(newToken, 0L)
                    }
                    if (!accepted) {
                        pendingToken.compareAndSet(newToken, 0L)
                    }
                }
            } else {
                val delayedMillis = now - postedAt.get()
                if (delayedMillis >= stallThresholdMillis &&
                    reportedToken.getAndSet(token) != token
                ) {
                    onStall(
                        MainStallSample(
                            delayedMillis = delayedMillis,
                            mainStack = mainThread.stackTrace,
                        )
                    )
                }
            }

            try {
                sleep(pollMillis)
            } catch (_: InterruptedException) {
                interrupt()
            }
        }
    }
}
```

旧 `Runnable` 的 token 与当前 token 不同时，`compareAndSet()` 不会确认新周期；当前 token 未完成前也不会再投递探针。示例省略了重复调用 `start()` 时避免创建多个线程的保护、应用退出处理、采样频率上限和持久队列。`onStall` 是发现长时间无响应后的回调，其中不能同步做网络或大文件写入。

### 阈值来自产品基线

Watchdog 阈值没有通用的 3 秒或 5 秒答案。过短会把正常的长消息、调试器暂停和设备休眠边界记成风险事件；过长则失去预警价值。配置时应考虑：

- 对应业务最常见的系统 ANR 类型及其时限。
- 设备等级、系统版本、温度和应用进程状态。
- 主线程消息耗时的线上分布与采样开销。
- 同一 stall 的去重、两次上报之间的最短间隔和每日上报配额。
- debug 构建、性能测试和已连接调试器时的排除规则。

Watchdog 报告应包含 token、投递时间、延迟、主线程栈、若干关键线程栈、进程状态和设备负载。`Thread.getStackTrace()` 能捕获主线程等待锁时的栈，采样一次的证据仍有限；连续样本能帮助区分正在推进的慢任务和停在同一位置的等待。

向自身发送 `SIGQUIT` 会让 ART 生成 thread dump（所有线程在采样时刻的堆栈快照），动作本身有开销，普通应用也通常无法读取系统保存在 `/data/anr` 的文件。它适合内部调试或受控的小流量发布，不适合每次线上 stall 都触发。

### Watchdog 的能力边界

- 它只能证明主 Looper 探针未按时执行，不能直接宣布系统已经产生 ANR。
- receiver 运行在自定义线程或 `goAsync()` worker 卡住时，主 Looper 可能完全正常。
- 无焦点窗口和部分系统侧等待不一定表现为主线程持续阻塞。
- 系统可能在 Watchdog 上报前、同时或之后判定 ANR，没有“必定提前通知”的保证。
- 主线程恢复后，Watchdog 样本仍有价值；ANR 不是 Java Crash，不一定终止进程。

因此，Watchdog 事件应与系统 ANR 分开存储，再通过时间、进程、ANR 类型和堆栈签名（由关键栈帧生成的事件指纹）关联。

## ANR 预警与主动发现

Android 17 增加了接近系统 ANR 时限的公开回调，Android 16 增加了 ANR 触发式 profiling。它们补充了应用 Watchdog 的证据来源，但都只在系统条件允许时提供，不保证每次事件都有回调或结果。

### Android 17：`registerAnrWarningListener`

API 37 的 `ActivityManager.registerAnrWarningListener()` 在应用接近 ANR 超时时通知监听器。官方要求 executor 不要使用主线程；系统不保证一定回调，也不保证回调后还留有足够时间。

下面的接入示例只保存小型结构化记录，`AnrWarningStore` 代表项目自定义的有界存储接口。监听器对象需要保留，以便使用同一个实例注销。

```kotlin
@RequiresApi(37)
class AnrWarningCollector(
    context: Context,
    private val store: AnrWarningStore,
) : AutoCloseable {

    private val activityManager =
        context.getSystemService(ActivityManager::class.java)

    private val executor = Executors.newSingleThreadExecutor { runnable ->
        Thread(runnable, "anr-warning")
    }

    private val listener = Consumer<AnrWarningResult> { result ->
        store.append(
            anrId = result.anrId,
            anrType = result.anrType,
            consumedMillis = result.consumedMillis,
            timeoutMillis = result.timeoutMillis,
            description = result.description,
            mainStack = Looper.getMainLooper().thread.stackTrace,
        )
    }

    fun start() {
        activityManager.registerAnrWarningListener(executor, listener)
    }

    override fun close() {
        activityManager.unregisterAnrWarningListener(listener)
        executor.shutdown()
    }
}
```

`AnrWarningResult` 给出 `anrId`、`anrType`、已消耗时间和总时限；其中已消耗时间使用 `uptimeMillis()` 的时间基准。`description` 面向诊断且格式不稳定，可以保存或用于把相似报告归为一组，不能解析成长期协议。监听器里只采集有限信息并追加到预分配或有界存储，远端上报留给进程恢复后处理。

如果预警最终发展为 ANR，`anrId` 可与 API 37 的 `ApplicationExitInfo.AnrInfo.getAnrId()` 关联。`AnrInfo` 还包含 ANR 类型、系统等待时限和 `isUserPerceptible()`。这里的 user-perceptible（用户可感知）按系统是否展示 ANR 对话框定义；Google Play 的 user-perceived core vital（用户可感知的主要质量指标）当前只统计 input dispatch ANR，两者口径不同。

### Android 16 及以上：ANR Profiling Trigger

API 36 的 `ProfilingTrigger.TRIGGER_TYPE_ANR` 在系统识别 ANR 后、可能结束应用前触发，返回正在采集的 system trace 快照。Profiling 指按配置采集性能数据；system trace 记录一段时间内的线程调度、CPU 和系统事件。触发器不代表应用一定被杀，采集结果也受系统资源、频率限制和配置影响，不能替代 ANR traces、`ApplicationExitInfo` 或业务监控。

可以把三类信号按时间关联：

| 信号 | 发生阶段 | 能回答的问题 |
|---|---|---|
| 应用 Watchdog | 主 Looper 超过内部阈值 | 主线程何时开始不响应，早期栈停在哪里 |
| `AnrWarningResult` | API 37，接近系统时限 | 系统正在观察哪种 ANR、已经消耗多少预算 |
| `ApplicationExitInfo.AnrInfo` / profiling 结果 | 系统认定 ANR 后，或进程退出后 | ANR 类型、ID、系统时限、用户可感知状态和 system trace |

同一个事件用 `anrId`、进程启动标识、单调时钟时间和堆栈签名关联。Wall clock 是可被用户或网络校时调整的日历时间；单调时钟只向前累计，更适合计算同一进程内的时间间隔。

### Looper 与 Binder 的主动监测

`Looper.setMessageLogging()` 可以通过 `Printer` 回调接口观察消息分发前后的文本，但它有三个边界：每个 Looper 只有一个 `Printer` 槽位，没有公开的读取方法；文本格式属于诊断输出；持续解析会增加主线程成本。接入时由一个组件统一持有 `Printer`，把其他消费者加入内部观察者列表，并在目标 Android 版本验证格式。线上使用采样、频率限制和远程开关。

单条消息的风险阈值应来自场景基线，不能统一写成 500 毫秒。总延迟还包括消息排队、同步屏障（临时阻止普通同步消息通过、让异步消息先执行的队列标记）、渲染工作、Binder 和锁等待，Looper 分发时长只覆盖其中一部分。

Binder 监测优先在自有接口的调用点记录开始、结束和请求 ID。隐藏 API Hook 依赖未公开接口，系统升级后可能失效，也很难区分对端排队与执行阶段。无法修改的系统调用使用 Perfetto、采样栈和 ANR traces 交叉判断。

## 后台 ANR 与前台 ANR 的差异化治理

前台、后台和 Google Play 的统计口径要分开描述。

Google Play 当前提供三项以 DAU（daily active users，当日活跃用户）为分母的指标：

- **ANR rate**：当天至少经历一次任意类型 ANR 的活跃用户占比。
- **User-perceived ANR rate**：当天至少经历一次 user-perceived ANR 的活跃用户占比；当前只把 `Input dispatching timed out` 计入该指标。
- **Multiple ANR rate**：当天至少经历两次 ANR 的活跃用户占比。

User-perceived ANR rate 是 Google Play 用于影响曝光判断的 core vital（主要质量指标）。官方当前给出的全局不良行为阈值为 0.47%，单设备型号阈值为 8%。这些数值和定义可能由 Google Play 调整，发布治理规则前要再次核对官方页面。

后台 ANR 可能不展示对话框，但仍会进入 overall ANR（全部类型 ANR）数据。它也可能揭示共享线程池、锁、广播冷启动或 Service 回调问题；“用户没看到”只能影响修复优先级，不能成为忽略依据。

治理看板至少分开：

- 进程重要性与界面可见状态。
- 系统 ANR 类型和 API 37 的 `isUserPerceptible()`。
- Google Play 的 overall（全部类型）、user-perceived（用户可感知）和 multiple（同一用户一天多次发生）指标。
- 会话级 stall、Watchdog 风险事件和系统确认 ANR。
- 设备型号、RAM（运行内存容量）、系统版本、应用版本与场景。

不同指标使用各自分母，不能拿“每千次启动 ANR 数”与 Play 的“受影响日活用户占比”直接比较。

## 系统负载导致的 ANR 识别与过滤

高 CPU、存储等待、内存压力、Binder 拥塞和 thermal throttling（设备过热后主动降低 CPU 等硬件频率）会放大同一段代码的耗时。系统负载应该作为判断原因的证据和分组维度，不能凭一个信号删除 ANR 记录。

### 多信号判断

一条“疑似系统负载”判断至少需要组合以下证据：

- ANR 窗口内本进程和系统 CPU 时间、可运行线程压力。
- I/O wait（CPU 等待存储设备完成读写的时间）、进程读写量与同设备同期基线。
- 内存可用量、回收活动，以及 PSI（Pressure Stall Information，资源压力造成任务等待的比例）记录的 memory/CPU/I/O 压力。
- Binder 线程状态、事务排队与 `system_server` 相关栈。
- 设备温度、降频状态与 CPU 频率。
- 同型号、同系统构建、同时间窗口的其他进程是否一起变慢。
- 应用主线程与相关工作线程是否停在同一业务位置。

固定“I/O wait 大于某百分比”或“RAM 小于 2 GB”都不足以确定原因。低端设备也属于产品用户，统计时应单独分组并保留在整体指标中；从分母排除会让看板变好，却不会改善用户遇到的无响应。

### 容易误判的信号

- **主线程 `nativePollOnce`**：它只说明采样时主 Looper 正在等待。广播可能在自定义 `Handler` 或工作线程上，快照也可能晚于阻塞点；要按 ANR 类型查看相关线程。对于 executing service 的大量同堆栈晚采样，官方文档允许结合其他证据降低问题组的优先级，这条经验不能套用到所有类型。
- **`am_proc_died` / `am_kill` 密集**：这两个事件分别记录进程死亡和系统终止进程。短时间大量出现支持“系统内存压力高”的判断，却不能证明本次 ANR 与应用代码无关。
- **cached app freezer（缓存应用冻结器）**：系统暂时冻结不活跃的缓存进程，减少其 CPU 使用。应用侧没有可靠的“刚解冻”通用 API；不能凭时间差跳过必要的状态恢复，也不能把 freezer 当作删除记录的理由。
- **`getRunningAppProcesses()`**：这是采样时刻的进程列表，无法证明先前的 ANR 为假，也不适合做上报有效性过滤。
- **设备启动后不久**：系统服务可能繁忙，但应用冷启动和同步 IPC 同样可能有优化空间。需要与同设备基线和系统 traces 一起判断。

监控平台可以增加 `system_load_suspected`（疑似系统负载）及证据字段，降低这类事件在告警列表中的排序优先级，或放入单独队列；原始事件、分母和系统确认状态应保留。多次版本对比后，如果问题只出现在某个设备系统构建且应用栈分散，再把证据交给设备厂商或平台团队联合排查。

## 治理与验证流程

ANR 修复要能回答“系统在等什么、哪条线程没有前进、改动如何证明有效”。代码修改如果没有同场景回归，风险只是换了位置。

1. **建立事件关联标识**：组合应用版本、进程启动标识、ANR 类型、单调时钟、场景和可用的 `anrId`，用来判断不同证据是否属于同一次事件。
2. **保全证据**：系统 traces、ANR 主题、事件日志、`ApplicationExitInfo`、性能采集结果、Watchdog 连续栈和设备状态分别存储。
3. **还原计时区间**：确认计时开始、结束与已消耗预算，标出冷启动、排队、执行和等待阶段。
4. **找到等待所有者**：主线程卡住时继续查锁持有者、Binder 对端或工作线程；主线程空闲时转向 receiver 线程、焦点窗口和系统状态。
5. **选择可验证的修改**：移出主线程、减少工作、改变 IPC 协议、缩短锁区，或调整需要在进程重启后继续执行的任务方案；每次修改对应一个可观察指标。
6. **做故障注入**：在测试环境让自有 Binder 服务延迟、锁持有时间增加、I/O 变慢、receiver 冷启动，检查取消、降级、`finish()` 和 `onTimeout()`。
7. **覆盖慢设备与压力状态**：低 RAM、CPU 受限、存储繁忙、冷热启动和前后台切换都要进入回归测试。
8. **观察发布前后趋势**：同时看事件数、受影响用户、会话风险事件、设备分组和堆栈问题组，避免分母变化掩盖回归。

每个高频问题组都应有负责人、证据、修复版本和验证结果。没有完整证据时可以标为“原因待确认”，不能为了报表整洁直接归入“系统原因”。

## 小结

ANR 治理从系统类型和计时窗口开始。主线程、Binder、锁和组件回调分别有不同的等待关系；Watchdog、API 37 预警、profiling 与 `ApplicationExitInfo` 提供的是互补证据。

工程动作可以压缩成四条：让主线程同步阶段可测且短；让跨线程、跨进程等待可取消或可降级；让组件生命周期遵守系统协议；让每次修复都能在同场景和慢设备上复现、对比。系统负载用于解释和分组，原始 ANR 记录与用户分母始终保留。

## 参考资料

- [Android Developers：Diagnose and fix ANRs](https://developer.android.com/topic/performance/anrs/diagnose-and-fix-anrs)
- [Android Developers：Android vitals ANR](https://developer.android.com/topic/performance/vitals/anr)
- [Android Developers：ActivityManager.registerAnrWarningListener](https://developer.android.com/reference/android/app/ActivityManager)
- [Android Developers：AnrWarningResult](https://developer.android.com/reference/android/app/AnrWarningResult)
- [Android Developers：ApplicationExitInfo.AnrInfo](https://developer.android.com/reference/android/app/ApplicationExitInfo.AnrInfo)
- [Android Developers：ProfilingTrigger.TRIGGER_TYPE_ANR](https://developer.android.com/reference/android/os/ProfilingTrigger#TRIGGER_TYPE_ANR)
- [Android Developers：Foreground service timeouts](https://developer.android.com/develop/background-work/services/fgs/timeout)
- [Android Developers：Foreground service types](https://developer.android.com/develop/background-work/services/fgs/service-types)
- [Android Developers：App Startup](https://developer.android.com/topic/libraries/app-startup)
- [Android Developers：WorkManager](https://developer.android.com/topic/libraries/architecture/workmanager)
- [Android Developers：SharedPreferences.Editor](https://developer.android.com/reference/android/content/SharedPreferences.Editor)
- [Android Developers：BroadcastReceiver](https://developer.android.com/reference/android/content/BroadcastReceiver)
- [AOSP Android 17：ActivityManagerService.java](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/am/ActivityManagerService.java)
- [AOSP Android 17：ActivityManagerConstants.java](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/am/ActivityManagerConstants.java)
- [AOSP Android 17：BroadcastConstants.java](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/am/BroadcastConstants.java)
- [AOSP Android 17：ActivityManager.java](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/app/ActivityManager.java)
- [AOSP Android 17：ActivityThread.java](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/app/ActivityThread.java)
- [AOSP Android 17：ContentResolver.java](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/content/ContentResolver.java)
- [AOSP Android 17：ContentProviderHelper.java](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/am/ContentProviderHelper.java)
- [AOSP Android 17：ActiveServices.java](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/am/ActiveServices.java)
- [AOSP Android 17：InputDispatcher.cpp](https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/services/inputflinger/dispatcher/InputDispatcher.cpp)
- [AOSP Android 17：IInputConstants.aidl](https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/libs/input/android/os/IInputConstants.aidl)
- [AOSP Android 17：Service.java](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/app/Service.java)
- [AOSP Android 17：Binder.java](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/os/Binder.java)
- [AOSP Android 17：BroadcastReceiver.java](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/content/BroadcastReceiver.java)
- [AOSP Android 17：CachedAppOptimizer.java](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/am/CachedAppOptimizer.java)
- [AOSP Android 17：ART monitor.cc](https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/runtime/monitor.cc)
