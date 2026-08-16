---
title: "ContentProvider 超时与 ANR 四路径"
chapter: "9.8"
section: "9.8"
status: ready-for-review
applicable_versions: "Android 12 (API 31) - Android 17 (API 37)"
tags: [anr, content-provider, publish-timeout, call-hang, ams]
related_chapters: ["1.10", "9.2", "9.4", "9.7"]
last_verified: "2026-06-07"
last_verified_against: "AOSP android-16.0.0_r1 ContentResolver / ContentProviderHelper / ContentProviderClient; 官方 ANR 文档 developer.android.com/topic/performance/anrs/diagnose-and-fix-anrs"
confidence: medium
sources:
  - type: aosp
    path: frameworks/base/core/java/android/content/ContentResolver.java
  - type: aosp
    path: frameworks/base/core/java/android/content/ContentProviderClient.java
  - type: aosp
    path: frameworks/base/services/core/java/com/android/server/am/ContentProviderHelper.java
  - type: aosp
    path: frameworks/base/services/core/java/com/android/server/am/ActivityManagerService.java
  - type: official
    path: developer.android.com/topic/performance/anrs/diagnose-and-fix-anrs
---

# 9.8 ContentProvider 超时与 ANR 四路径

ContentProvider 相关卡死至少涉及四个计时器，其中只有一条路径会直接对 Provider 宿主进程发起 ANR 处理：

1. 已 attach（连接到 `system_server`）的进程没有按期发布 Provider：系统以初始化失败为由移除宿主进程。
2. 获取方等待 Provider ready（完成发布）到期：系统结束本次获取或唤醒等待者。
3. `ContentResolver` 等待异步回调到期：调用返回空结果或进入错误处理。
4. 特权调用方启用 `ContentProviderClient.setDetectNotResponding()`，远程调用超过调用方配置的期限：Provider 宿主进入 `AnrHelper` 的 ANR 处理流程。

“Publish 超时”和“ContentProvider not responding”在日志中都带 ContentProvider 字样，但处理对象、计时起点和退出原因不同。诊断时应先确认触发入口，再看 Provider 的 `onCreate()`、Binder 线程或数据库栈。

本章的平台实现以 `android-17.0.0_r1` 为核对版本。ContentProvider 的发布、引用计数和 Binder Transport 结构见 [§1.10 ContentProvider 性能与优化](../../part1-fundamentals/ch01-architecture/10-content-provider.md)；通用 ANR 证据流程见 [§9.3 ANR 分析方法](03-anr-analysis.md)。

## 1. 四个常量，四种语义

Android 17 的四个常量都定义在 `ContentResolver`，但它们并非都对应 AMS Handler（ActivityManagerService 的消息处理器），也不会全部产生 ANR。

下面的源码片段用于确认四个预算之间的计算关系：

```java
public static final int CONTENT_PROVIDER_PUBLISH_TIMEOUT_MILLIS =
        10 * 1000 * Build.HW_TIMEOUT_MULTIPLIER;

public static final int CONTENT_PROVIDER_READY_TIMEOUT_MILLIS =
        CONTENT_PROVIDER_PUBLISH_TIMEOUT_MILLIS
        + 10 * 1000 * Build.HW_TIMEOUT_MULTIPLIER;

private static final int CONTENT_PROVIDER_TIMEOUT_MILLIS =
        3 * 1000 * Build.HW_TIMEOUT_MULTIPLIER;

private static final int REMOTE_CONTENT_PROVIDER_TIMEOUT_MILLIS =
        CONTENT_PROVIDER_READY_TIMEOUT_MILLIS
        + CONTENT_PROVIDER_TIMEOUT_MILLIS;
```

默认倍率为 1 时，它们依次是 10 秒、20 秒、3 秒和 23 秒。这里的“预算”指计时器允许等待的最长时间，表中的 `HW` 是 `HW_TIMEOUT_MULTIPLIER` 的缩写。具体用途如下。

| 预算 | 起点与等待对象 | 到期动作 | 会直接进入 `AnrHelper` |
|---|---|---|---|
| publish，`10s × HW` | Provider 宿主 attach 后，等待该进程发布 launching providers（正在启动的 Provider） | 以 `REASON_INITIALIZATION_FAILURE` 移除宿主进程 | 否 |
| ready，`20s × HW` | 获取方等待正在启动的 Provider 发布 | 标记发布失败、唤醒等待方；获取返回 `null` | 否 |
| connected callback，`3s × HW` | 已连接 Provider 的 `getTypeAsync()`、`canonicalizeAsync()` 等回调 | 结束等待并按调用点返回或抛错 | 否 |
| remote callback，`23s × HW` | 经 `system_server` 获取 MIME type 等异步结果 | 结束等待，并由调用点返回空结果或错误 | 否 |
| call detector（调用卡死检测器），调用方配置 | `ContentProviderClient` 的一次远程操作 | 对 Provider 宿主发起 `ContentProvider not responding` ANR | 是 |

前三个固定预算和 call detector 相互独立。某次 Provider 查询还可能触发调用方的输入 ANR，例如调用方在主线程等待 Provider ready；此时到期的是调用方的输入期限，ANR subject（被记录为事件主体的进程）不会因此自动变成 Provider 宿主。

## 2. Publish guard：初始化失败清进程

### 2.1 计时从 attach 开始

AMS 启动承载 Provider 的进程后，把对应的 `ContentProviderRecord` 放入 `mLaunchingProviders`。进程 attach 到 `system_server` 时，`ActivityManagerService.attachApplicationLocked()` 检查它是否仍承载正在启动的 Provider；满足条件便发送一条延迟消息：

- message：`CONTENT_PROVIDER_PUBLISH_TIMEOUT_MSG`；
- `what`：57；
- delay：`CONTENT_PROVIDER_PUBLISH_TIMEOUT_MILLIS`；
- `obj`：宿主 `ProcessRecord`。

这个 10 秒窗口不包含 Zygote fork（由 Zygote 创建应用进程）到进程 attach 之前的时间。它覆盖 attach 之后的 `bindApplication` 准备、Application 实例创建、Provider 安装及各 Provider 的 `onCreate()`。

Android 17 的 `ActivityThread.handleBindApplication()` 顺序很容易被写反：

1. 创建 Application 对象；
2. `installContentProviders()` 顺序安装 Provider，并调用每个 Provider 的 `onCreate()`；
3. `publishContentProviders()` 把 holder 列表交给 AMS；
4. 随后才调用 `Application.onCreate()`。

因此，在普通启动场景中，`Application.onCreate()` 不消耗 publish guard（发布保护计时器）；Application 类加载、构造、attach 和更早的 bind 初始化仍会消耗这段预算。Provider 已发布后，远程 query 可能与尚未结束的 `Application.onCreate()` 并发，这部分时间会计入远程调用等待。

### 2.2 多个 Provider 共用一次 publish

`installContentProviders()` 逐个安装清单中的 Provider，把成功安装的 holder（包含 Provider 及连接信息的容器）收集到列表，再调用一次 `IActivityManager.publishContentProviders()`。任何一个排在前面的 `onCreate()` 卡住，后面的 Provider 都无法安装，整批 holder 也无法发布。

常见阻塞点包括：

- Provider `onCreate()` 中同步打开或迁移数据库；
- 文件锁、进程锁或跨进程 Binder 循环等待；
- 主线程文件 I/O、资源解压和 page fault（缺页异常）；
- SDK 自动初始化器之间的依赖或递归获取 Provider；
- 等待一个尚未启动的业务 executor（执行器）、Future（异步结果）或 CountDownLatch（计数等待器）。

网络请求不应放进 `onCreate()`。即使网络栈在某台设备上很快，它的外部时延和失败重试也不适合 Provider 发布期限。

### 2.3 到期动作

message 57 到期后，AMS 调用 `ContentProviderHelper.processContentProviderPublishTimedOutLocked()`。Android 17 的处理是：

1. 清理该进程仍占用的 launching-provider（正在启动）状态；
2. 调用 `removeProcessLocked()`；
3. exit reason（退出主原因）记为 `ApplicationExitInfo.REASON_INITIALIZATION_FAILURE`；
4. subreason（细分原因）使用 `SUBREASON_UNKNOWN`；
5. 描述为 `timeout publishing content providers`。

这条路径没有调用 `mAnrHelper.appNotResponding()`，不会生成 `ContentProvider not responding` 类型的 ANR。进程退出是否有用户可见界面，取决于前台状态和上层启动场景；它不会进入 `AppNotRespondingDialog` 对话框流程。

### 2.4 如何取证

应用下次启动后，可以查询自己的历史退出原因。下面的 Kotlin 代码用于筛选初始化失败记录：

```kotlin
val activityManager =
    context.getSystemService(ActivityManager::class.java)

val initializationFailures =
    activityManager.getHistoricalProcessExitReasons(
        context.packageName,
        0,
        32
    ).filter {
        it.reason == ApplicationExitInfo.REASON_INITIALIZATION_FAILURE
    }

initializationFailures.forEach { exit ->
    Log.i(
        "ProviderExit",
        "process=${exit.processName}, time=${exit.timestamp}, " +
            "description=${exit.description}"
    )
}
```

`description` 属于诊断信息，格式可能变化。识别 publish timeout 时，还应结合同一时段的 `ActivityManager` 日志、Provider authority（唯一标识 Provider 的名称）、进程 attach 和 `bindApplication` trace。

## 3. Ready timeout：获取失败，不是 Provider ANR

当调用方请求一个尚未发布的远程 Provider 时，AMS 可以先返回 `provider == null` 的 `ContentProviderHolder`。应用进程中的 `ActivityThread.acquireProvider()` 随后在 `ProviderKey.mLock` 上等待，最长为 `CONTENT_PROVIDER_READY_TIMEOUT_MILLIS`。

system_server 同时为该 `ContentProviderRecord` 安排 `WAIT_FOR_CONTENT_PROVIDER_TIMEOUT_MSG`：

- `what`：73；
- delay：`20s × HW_TIMEOUT_MULTIPLIER`；
- 到期：`onProviderPublishStatusLocked(false)`，通知等待者发布失败。

应用侧等待结束后若 holder 仍为空，`acquireProvider()` 记录 `Failed to find provider info` 并返回 `null`。shell 等 external client（外部调用方）的特殊路径会在 `system_server` 内等待同一 ready 预算，到期后写入 `Timeout waiting for provider` 并返回 `null`。

Ready timeout 比 publish guard 长 10 秒，是为了给宿主的 publish timeout、进程清理和等待方通知留下顺序空间。它不会把等待方或 Provider 宿主直接送入 `AnrHelper`。

这里还有一个同时运行的计时器：调用方若在 UI 线程同步执行 `ContentResolver.query()`，可能在 ready timeout 到达前，就因输入事件、Service 或 Broadcast 的期限到期而发生调用方 ANR。栈中常见 `ActivityThread.acquireProvider()`、`Object.wait()` 或 AMS Binder 调用。归因时要写“调用方主线程同步等待 Provider 发布”，不能标成 call detector 触发的 Provider ANR。

## 4. Call hang detector：由特权调用方开启

### 4.1 API 权限与计时方式

`ContentProviderClient.setDetectNotResponding(long)` 在 Android 17 中是 `@SystemApi`、`@hide`，并要求 `android.permission.REMOVE_TASKS`。普通 SDK 应用无权把它当作 CRUD（增、删、改、查）操作的通用 timeout API。

启用后，`ContentProviderClient` 的远程方法经 `execute()` 包装：

1. `beforeRemote()` 把 `NotRespondingRunnable` 延迟投递到调用方进程的 main looper（主线程消息循环）；
2. 当前线程执行 Binder 调用；
3. 调用及时返回时，`afterRemote()` 移除 runnable；
4. runnable 到期执行时，调用 `ContentResolver.appNotRespondingViaProvider()`。

检测 runnable（可执行任务）使用 main looper 的异步 `Handler`。若调用方恰好在自己的主线程阻塞执行远程调用，main looper 无法按期运行 detector；调用方更可能先触发输入或组件 ANR。系统组件使用此能力时，应让 main looper 保持可调度，并在 worker（工作线程）上执行被监控调用。

### 4.2 AMS 如何找到被归责进程

`ActivityThread.appNotRespondingViaProvider()` 通过 Provider binder 找到本进程持有的 `ProviderRefCount`（引用计数记录），再把 holder 中的 connection（跨进程连接）传给 AMS。`ContentProviderHelper.appNotRespondingViaProvider()` 随后执行：

1. 校验调用方具有 `REMOVE_TASKS`；
2. 从 `ContentProviderConnection` 取出 `conn.provider.mProc`；
3. 创建 reason（超时原因）为 `ContentProvider not responding` 的 `TimeoutRecord`；
4. 调用 `mAnrHelper.appNotResponding(host, timeoutRecord)`。

被标记无响应的是 Provider 宿主，调用方继续卡在原来的 Binder 调用中。前台、后台和系统设置会影响后续处置：后台 silent ANR（不显示前台 ANR 对话框的处理）可以直接终止进程，前台记录则可能进入 ANR UI；不能笼统写成“每次都会弹框”。

### 4.3 Android 17 的 cancellation-aware（取消感知）变体

Android 17 源码还包含受 feature flag（功能开关）控制的 `setDetectNotRespondingOnCancel(fixed, onCancel)`：

- 不支持 cancellation 的调用使用 fixed timeout；
- 支持 cancellation（取消）且配置了 on-cancel timeout 时，从 `CancellationSignal.cancel()` 后开始计时；
- cancellable（可取消）调用配置 on-cancel timeout 后，不再套用 fixed timeout；
- 调用长期没有响应 cancellation 时，可以把 Provider 宿主送入相同的 ANR 路径。

旧的 `setDetectNotResponding(fixed)` 在对应 flag 启用时委托给新方法，并把 on-cancel timeout 设为 0，从而保留固定期限语义。系统应用若依赖这条新路径，应核对目标 build 的 flag，而不能只看 API 37。

## 5. Async callback timeout：结果降级

`CONTENT_PROVIDER_TIMEOUT_MILLIS` 用在已取得 Provider 后的短异步回调，例如：

- `getTypeAsync()`；
- `canonicalizeAsync()`；
- `uncanonicalizeAsync()`。

`REMOTE_CONTENT_PROVIDER_TIMEOUT_MILLIS` 用于通过 ActivityManager 异步获取远程 MIME type 等结果，预算包含 ready timeout 再加 3 秒回调等待。

这两条到期路径会结束 `ResultListener` 等待，再由调用点返回 `null`、传播记录的异常或返回能力较弱的结果。它们没有调用 `appNotRespondingViaProvider()`。看到 3 秒或 23 秒等待，不能据此声称 Provider 宿主发生 ANR。

## 6. 诊断决策表

| 证据 | 对应路径 | 被处理对象 | 下一步 |
|---|---|---|---|
| exit reason 为 `INITIALIZATION_FAILURE`，描述含 publish timeout | publish guard | Provider 宿主 | 看 attach→publish、各 `onCreate()` |
| `Failed to find provider info` 或 `Timeout waiting for provider` | ready wait | 本次获取 | 看进程启动、publish status 与调用线程 |
| 调用返回 `null`，窗口约 3/23 秒 | async callback wait | 本次 API 调用 | 看 callback 是否回送、是否有 `RemoteException` |
| ANR subject 为 `ContentProvider not responding` | call detector | Provider 宿主 | 看 detector 配置方、Binder call 与宿主线程 |
| 调用方 ANR，栈在 `acquireProvider()` | 调用方其他 deadline | 调用方 | 查主线程同步获取与对应 ANR 类型 |
| Provider binder 线程全忙，缺少目标 query 开始 slice | call detector 或普通慢调用 | Provider 宿主 | 查 Binder 线程池是否饱和，以及是否存在嵌套同步调用 |

这张表里的日志字符串是 Android 17 AOSP 提供的线索，厂商可能修改文案。退出原因、ANR reason、PID 和源码路径比单条日志更稳定。

## 7. Perfetto 怎么看

### 7.1 Publish 路径

采集至少包含：

- `am`、`binder_driver`、`sched`、`freq`；
- 目标进程的 atrace app category（应用自定义 trace 标记）；
- `linux.process_stats`（进程与线程信息）；
- 按需加入 disk、reclaim（内存页回收）和 CPU sampling（定期采样调用栈）。

在 Provider 宿主主线程上定位 `bindApplication`，展开到 Provider 类名、`installProvider` 或 `onCreate()`。下面的 SQL 用于列出目标进程中与启动和 Provider 相关的 thread slice（带起止时间的线程事件片段）：

```sql
SELECT
  slice.ts,
  slice.dur / 1e6 AS dur_ms,
  thread.name AS thread_name,
  slice.name
FROM slice
JOIN thread_track ON slice.track_id = thread_track.id
JOIN thread USING (utid)
JOIN process USING (upid)
WHERE process.name = 'com.example.provider'
  AND (
    slice.name GLOB '*bindApplication*'
    OR slice.name GLOB '*Provider*'
    OR slice.name GLOB '*provider*'
  )
ORDER BY slice.ts;
```

用户代码没有自定义 trace 标记时，结果可能只显示 framework（系统框架）阶段。此时应使用主线程调度状态、CPU sampling、文件系统事件和启动日志补足，不能根据空白区间猜测某个 Provider 的耗时。

### 7.2 Call hang 路径

Call detector 会进入标准 ANR 处理流程。Android 17 采到 `debug.anr` Track Event（自定义时间标记）时，可以搜索 `ANR Detected`，再核对 reason 是否为 `ContentProvider not responding`。分析重点在 Provider 宿主：

- main 线程是否仍在 `Application.onCreate()`；
- Binder 线程是否进入 `ContentProvider$Transport.query/insert/call`；
- 目标 Binder 线程在 Running（正在执行）、R（等待 CPU）、S（可中断睡眠）、D（不可中断睡眠）中各持续多久；
- 是否等待数据库锁、文件 I/O、另一个 Binder 服务或主线程；
- 全部 Binder 线程是否被同步事务占满。

主机侧 Perfetto 工具支持 Binder 标准查询库时，可以用下面的查询筛选 Provider 宿主接收的慢调用：

```sql
INCLUDE PERFETTO MODULE android.binder;

SELECT
  client_ts,
  client_process,
  client_thread,
  server_process,
  server_thread,
  client_dur / 1e6 AS client_wall_ms,
  server_dur / 1e6 AS server_wall_ms,
  aidl_name
FROM android_binder_txns
WHERE server_process = 'com.example.provider'
  AND client_ts BETWEEN 123000000000 AND 143000000000
ORDER BY client_dur DESC;
```

`aidl_name` 能否解析出 `IContentProvider` 方法，取决于 trace 数据和解析器版本。即使方法名缺失，client/server（调用方/服务端）PID、事务 slice 和双方线程状态仍可用于还原等待阶段。

### 7.3 不依赖 `am_anr` 字符串 SQL

`am_proc_died`、`am_anr` 是否以 slice 名出现，会受 atrace、EventLog 导入、Perfetto parser（解析器）和厂商实现影响。若只用 `slice.name LIKE '%am_anr%'` 同时发现事件并判断原因，很容易漏报或误报。

更稳定的入口是：

1. `ApplicationExitInfo` 或系统 EventLog 确认退出类型；
2. Android 17 `ANR Detected` instant（瞬时事件）与 ANR reason 确认 call detector；
3. PID、process start/attach/publish 时序确认宿主；
4. Binder flow（跨线程事务关联）和线程状态解释耗时。

## 8. `HW_TIMEOUT_MULTIPLIER` 的边界

Android 17 的定义是：

```java
public static final int HW_TIMEOUT_MULTIPLIER =
        SystemProperties.getInt("ro.hw_timeout_multiplier", 1);
```

它是整数，默认值为 1。源码注释说明它面向速度远低于真机的软件模拟器；真机和硬件加速虚拟设备不应设置。它与 Android Performance Class（设备性能等级）没有自动换算关系，也不存在由平台统一配置的 1.5 倍档位。

下面的命令用于读取测试设备的属性值：

```bash
adb shell getprop ro.hw_timeout_multiplier
```

空值按 `Build` 中的默认值 1 解释。若输出 2，publish、ready、connected callback 和 remote callback 分别变成 20、40、6、46 秒。`setDetectNotResponding()` 的时长由调用方传入，不会自动乘这个倍率。

## 9. 修复策略

### 9.1 Publish 超时

- 记录每个 Provider `onCreate()` 的开始、结束和 authority，定位这一批 Provider 中最早卡住的位置。
- 把数据库 migration（结构迁移）、全量索引、网络和大文件扫描移出 publish 路径。
- 对必须 lazy（延迟初始化）的资源定义线程安全的 ready 状态；若只把任务放到后台，首个 query 却仍同步等待同一任务，延迟只会转移到远程调用阶段。
- 检查 Provider 之间的相互查询、文件锁和 SDK 初始化依赖，避免启动阶段形成循环等待。
- 为独立进程 Provider 单独测量 attach→publish；把 Provider 放到独立进程只能隔离主进程成本，无法取消远程 Provider 自己的 publish guard。

Jetpack App Startup 会把多个 initializer（初始化器）放进一个 `InitializationProvider`。它减少了 Provider 组件数量，但仍会在该 Provider 的 `onCreate()` 中执行 initializer。耗时过长的 initializer、错误依赖图和同步 I/O 仍会阻塞整批 publish，不应给出“每合并一个 Provider 固定节省若干毫秒”这类跨设备承诺。

### 9.2 Provider call hang（远程调用卡死）

- query 先缩小 projection（返回列）、selection（筛选条件）和返回行数，避免在 Binder 线程扫描数量不受限制的数据。
- 把数据库 migration 与 query 分开，明确数据库锁的持有范围。
- 不在 Provider Binder 线程中同步等待主线程；主线程也不要反向等待同一 Binder 线程。
- 限制嵌套同步 Binder，保留线程池处理新请求的能力。
- 支持 `CancellationSignal` 的操作应及时传播到数据库、文件或下游服务。
- 系统调用方配置 detector 时，要保证 main looper 能运行检测 runnable，并把阈值与接口约定、取消语义和误杀成本一起评估。

普通应用应把远程 Provider 调用移出 UI 完成期限，并通过 cancellation 和业务超时控制自身等待。反射调用 hidden API（隐藏接口）既不稳定，也会因权限校验失败；`setDetectNotResponding()` 会让系统对远端宿主发起 ANR，不能当成普通 Future timeout（只结束本地等待的超时）。

## 10. 版本结论

截至 Android 17 / API 37：

- publish guard 固定为 `10s × HW_TIMEOUT_MULTIPLIER`，入口是 AMS message 57；
- ready wait 固定为 `20s × HW_TIMEOUT_MULTIPLIER`，AMS message 73 和 `ActivityThread` 等待共同处理发布结果；
- connected/remote callback 预算为 `3s × HW` 和 `23s × HW`，到期不自动触发 ANR；
- `setDetectNotResponding()` 属于受权限保护的 System API，期限由调用方设置；
- cancellation-aware detector 受 Android 17 feature flag 控制；
- Provider ANR 的宿主处置沿 `ContentProviderHelper → AnrHelper → ProcessErrorStateRecord` 执行，后台记录可能没有对话框。

遇到 ContentProvider 相关故障时，先把“发布、等待 ready、异步 callback、远程 call”四个阶段分开，再讨论优化。只看 10 秒常量或一行 `ContentProvider` 日志，无法判断被处理的是调用方还是 Provider 宿主。

## 参考资料

- [Android Developers：Content provider not responding](https://developer.android.com/topic/performance/anrs/diagnose-and-fix-anrs#content-provider-not-responding)
- [AOSP android-17.0.0_r1：ContentResolver](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/content/ContentResolver.java)
- [AOSP android-17.0.0_r1：ContentProviderClient](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/content/ContentProviderClient.java)
- [AOSP android-17.0.0_r1：ActivityThread](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/app/ActivityThread.java)
- [AOSP android-17.0.0_r1：ContentProviderHelper](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/am/ContentProviderHelper.java)
- [AOSP android-17.0.0_r1：ActivityManagerService](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/am/ActivityManagerService.java)
- [AOSP android-17.0.0_r1：ProcessErrorStateRecord](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/am/ProcessErrorStateRecord.java)
- [AOSP android-17.0.0_r1：Build.HW_TIMEOUT_MULTIPLIER](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/os/Build.java)
- [§9.2 ANR 类型与触发条件](02-anr-types.md)
- [§9.3 ANR 分析方法](03-anr-analysis.md)
- [§9.7 ANR 与 Kernel Trace 联合诊断](07-anr-kernel-trace-joint-diagnosis.md)
