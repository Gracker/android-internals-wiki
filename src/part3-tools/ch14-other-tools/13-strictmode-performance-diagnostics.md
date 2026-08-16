---
title: "StrictMode 性能检查与开发期诊断"
chapter: "14.13"
section: "14.13"
status: finalized
task2b_state: fixed
task6_state: "reviewed"
task9_state: reviewed
pipeline_stage: ready-to-publish
applicable_versions: "Android 9 (API 28) - Android 17 (API 37)"
tags: [strictmode, disk-read, disk-write, network, custom-penalty, performance-diagnostics]
related_chapters: ["15.6", "14.7", "21.3"]
last_verified: "2026-08-13"
last_verified_against: "AOSP android-17.0.0_r1 + current developer.android.com StrictMode API reference"
confidence: high
sources:
  - type: aosp
    path: "frameworks/base/core/java/android/os/StrictMode.java"
  - type: aosp
    path: "frameworks/base/core/java/android/os/Parcel.java"
  - type: aosp
    path: "frameworks/base/core/java/android/app/ActivityThread.java"
  - type: aosp
    path: "libcore/dalvik/src/main/java/dalvik/system/BlockGuard.java"
  - type: aosp
    path: "libcore/dalvik/src/main/java/dalvik/system/CloseGuard.java"
---

# 14.13 StrictMode 性能检查与开发期诊断

StrictMode 是一组运行时检查规则。代码经过 Android framework 或 libcore（Android 核心 Java 库）预埋的检查点时，detector（检测项）会识别磁盘读写、网络访问、显式 GC（garbage collection，垃圾回收）、资源未关闭和若干安全问题，penalty（处理方式）再决定记录、回调或终止进程。它适合在开发、自动化测试和平台集成阶段暴露可疑行为。

StrictMode 提供的是 violation（规则违规）信号，不是完整性能采样。它不会拦住每一个系统调用，也不会自动判断某段业务代码是否超过 16 ms。需要精确耗时、CPU 调度、Binder（Android 跨进程调用）等待或块 I/O（存储设备读写）证据时，应继续使用 Perfetto。

本文的源码基线是 Android 17 / API 37 / `android-17.0.0_r1`。

## 先分清 ThreadPolicy 和 VmPolicy

| 策略 | 生效范围 | 典型检查 |
| --- | --- | --- |
| `ThreadPolicy` | 调用 `StrictMode.setThreadPolicy()` 的当前 OS 线程 | 磁盘读、磁盘写、网络、自定义慢调用、资源类型不匹配、未缓冲 I/O、显式 GC |
| `VmPolicy` | 当前进程 | Activity/Closeable/SQLite/注册对象泄漏、非 SDK API、明文网络、URI 与 Intent 安全问题 |

`ThreadPolicy` 不等于“主线程策略”。应用通常在 `Application.onCreate()` 中设置它，而 `onCreate()` 恰好运行在进程主线程，所以常见用法只覆盖主线程。线程池、Binder 线程和手工创建的线程不会自动继承这份 Java 线程策略。

`VmPolicy` 由 `StrictMode.setVmPolicy()` 安装到进程级静态状态，进程内各线程触发对应检查点时都受它约束。

每次 `setThreadPolicy()` 或 `setVmPolicy()` 都会替换现有策略。Builder 是通过连续调用配置方法来组装策略的对象；启用了 detector 却没有显式配置 penalty 时，`build()` 会自动补上 `penaltyLog()`。

## 一份可解释的 API 34+ Debug 配置

下面的 Java 代码在每个应用进程的主线程安装显式规则，避免 `detectAll()` 随 target SDK（应用声明的目标 API 级别）、compat change（控制特定应用兼容行为的平台开关）和 feature flag（运行时功能开关）改变覆盖范围。由于 `detectExplicitGc()` 从 API 34 才可用，这段代码原样适用于 API 34–37；API 28–33 必须省略该调用，或在组装 Builder 时用 `Build.VERSION.SDK_INT >= 34` 单独保护，不能在旧系统上直接调用不存在的方法。

```java
public final class App extends Application {
    @Override
    public void onCreate() {
        super.onCreate();

        if ((getApplicationInfo().flags & ApplicationInfo.FLAG_DEBUGGABLE) == 0) {
            return;
        }

        StrictMode.setThreadPolicy(
                new StrictMode.ThreadPolicy.Builder()
                        .detectDiskReads()
                        .detectDiskWrites()
                        .detectNetwork()
                        .detectCustomSlowCalls()
                        .detectResourceMismatches()
                        .detectUnbufferedIo()
                        .detectExplicitGc()
                        .penaltyLog()
                        .build());

        StrictMode.setVmPolicy(
                new StrictMode.VmPolicy.Builder()
                        .detectActivityLeaks()
                        .detectLeakedClosableObjects()
                        .detectLeakedSqlLiteObjects()
                        .detectLeakedRegistrationObjects()
                        .detectNonSdkApiUsage()
                        .penaltyLog()
                        .build());
    }
}
```

Android 会为应用的每个进程创建 `Application` 实例，因此同一个 `Application` 类的 `onCreate()` 会分别运行。上面的 `ThreadPolicy` 覆盖各进程主线程，`VmPolicy` 覆盖各自进程；它不会把策略送到另一个进程。

团队可以从少量 detector 开始，确认日志能够及时处理后再逐项增加。`detectNonSdkApiUsage()` 宜尽早安装，因为启用前发生的访问可能不会被补报。

## ThreadPolicy：检查的是操作类别

### 磁盘读写

`detectDiskReads()` 和 `detectDiskWrites()` 通过当前线程的 `BlockGuard.Policy` 接收 `onReadFromDisk()`、`onWriteToDisk()` 回调。`BlockGuard` 是 libcore 提供的线程操作检查接口；参与接入的文件系统与 Android framework 代码会在 I/O 前触发这些检查点。

边界需要写清楚：

- 直接从 native（C/C++）代码发起、且没有经过对应检查点的 syscall（系统调用）可能绕过检测；
- 检测到磁盘访问不代表该访问一定很慢；
- 主线程通过 `Future.get()` 等待后台 I/O 时，磁盘检查点发生在工作线程，主线程不会因此自动得到 `DiskReadViolation`；
- 第三方库若在后台线程读写，而后台线程没有安装策略，主线程策略看不到那次操作。

`SharedPreferences` 是典型例子。`SharedPreferencesImpl` 可以在后台加载 XML，主线程 getter 随后等待加载完成。磁盘 syscall 不在主线程时，主线程 StrictMode 可能没有 `DiskReadViolation`，界面仍会因等待而卡住。遇到这种现象要看 Perfetto 中的线程状态和工作线程 I/O。

`commit()` 允许调用线程同步完成持久化，可能触发主线程磁盘写；`apply()` 把持久化工作排入后台，仍要避免在紧邻路径等待它完成。

### 网络

`detectNetwork()` 由 `BlockGuard.Policy.onNetwork()` 触发。Java socket 和基于它的常见 HTTP 客户端会经过这类检查点。native socket 代码不保证进入同一检查。

`penaltyDeathOnNetwork()` 是一个特殊 penalty：启用 `detectNetwork()` 后，它会在其他 penalty 之前抛出 `NetworkOnMainThreadException`。若网络违规只需记录，就只配置 `penaltyLog()`，不要同时启用这个提前终止 penalty。

### 自定义慢调用

`detectCustomSlowCalls()` 只让 `StrictMode.noteSlowCall(name)` 生效。调用 `noteSlowCall()` 就会产生 `CustomViolation`；它没有内建耗时阈值，也不会自动包围并测量后续方法。

下面的写法用于标记一条团队认定不应出现在主线程的同步路径：

```java
StrictMode.noteSlowCall("decode-startup-config");
decodeStartupConfig();
```

日志中的名字用于辨认检查点。若要知道 `decodeStartupConfig()` 花了多少时间，给它添加 trace section（带开始、结束时间的跟踪区段），再在 Perfetto 中读取对应 slice（时间线片段）。

### 资源不匹配、未缓冲 I/O 与显式 GC

- `detectResourceMismatches()`：例如用 `TypedArray.getInt()` 读取 String 类型资源，转换可成功但会报告类型不匹配；
- `detectUnbufferedIo()`：由参与的 I/O 实现调用 `BlockGuard.onUnbufferedIO()`，用于发现逐字节等没有缓冲批处理的访问；
- `detectExplicitGc()`：由显式 `Runtime.gc()` / `System.gc()` 检查点报告。Android 17 的 `detectAll()` 是否自动包含它还受 compat change 控制，显式调用 Builder 方法更稳定。

这些 detector 不会覆盖分配抖动、系统触发 GC、GPU 工作或普通 CPU 密集计算。

## VmPolicy：资源生命周期、API 与安全检查

### 资源泄漏类检查

| 方法 | Android 17 行为 |
| --- | --- |
| `detectActivityLeaks()` | 跟踪预期 Activity 实例数；快速计数超限后执行 GC/finalization（垃圾回收与终结清理），再用 `VMDebug.countInstancesOfClass()` 复核 |
| `detectLeakedClosableObjects()` | 启用 `CloseGuard` reporter；只有接入 `CloseGuard`、且终结时仍为 open 的资源才会上报 |
| `detectLeakedSqlLiteObjects()` | 接收 `SQLiteCursor` 等 SQLite 对象在未关闭却进入终结清理时的专用报告 |
| `detectLeakedRegistrationObjects()` | 在 `Context` 清理时报告未注销的 `BroadcastReceiver` 或 `ServiceConnection` |
| `setClassInstanceLimit()` | 为指定类设置实例数上限，进程空闲检查时可触发 `InstanceCountViolation` |

`detectLeakedClosableObjects()` 不是对所有实现了 `Closeable` 的对象做全堆扫描。资源类必须接入 `CloseGuard`（跟踪资源是否显式关闭的 libcore 辅助机制），调用 `open()`、`close()` 与 `warnIfOpen()` 后才能参与检测。

Activity 实例检查会主动 GC 和遍历堆，测试时可能带来明显扰动。它也依赖对象回收与生命周期时序，不宜把一次异步出现的日志当成稳定的单元测试断言。

### API、网络与组件安全类检查

Android 17 的 `VmPolicy.Builder` 还包含：

- `detectNonSdkApiUsage()`：ART（Android Runtime）把非 SDK API 使用消息交给 StrictMode；底层访问限制仍由 ART 自己执行；
- `detectCleartextNetwork()`：通过 UID 明文网络策略与 `netd`（系统网络守护进程）协作，记录模式和拒绝模式的行为不同；
- `detectUntaggedSockets()`：报告未用 `TrafficStats` 添加流量分类标签的 Java socket，native socket 不在当前保证范围；
- `detectFileUriExposure()`、`detectContentUriWithoutPermission()`：检查跨应用 URI 使用；
- `detectUnsafeIntentLaunch()`：检查外部来源 Intent 被继续转发时可能产生的组件与 URI 授权风险；
- `detectCredentialProtectedWhileLocked()`：用户尚未解锁时访问 credential-protected storage（解锁后才能读取的凭据保护存储）路径；
- `detectIncorrectContextUse()`：例如从不关联显示区域的非 visual Context 获取 `WindowManager` 等 UI 服务。

这组 detector 中有性能、资源和安全检查。看到 `VmPolicy` 违规时，应按 violation 类型分派给对应负责人，不能全部归为“卡顿”。

### 受 flag 控制的 API 36/37 detector

`android-17.0.0_r1` 还定义了两个受 feature flag 或 compat change 控制的 Builder API。`@FlaggedApi` 表示 API 是否生效还受平台运行时开关约束：

| 方法 | 报告内容 | API 与使用限制 |
| --- | --- | --- |
| `detectBlockedBackgroundActivityLaunch()` | 应用发起的后台 Activity 或 PendingIntent 启动被系统阻止 | API 36；`@FlaggedApi(FLAG_BAL_STRICT_MODE_RO)`，设备 flag 与客户端策略都要满足 |
| `detectImplicitUriPermissionGrant()` | Intent 未携带显式 grant flag，系统仍向应用授予 URI 访问权限 | API 37；受 security flag 与 compat change 控制 |

当前官方 API 文档还指出，隐式 URI 权限授予将在 Android 18（API 38）停止；这个 detector 用来提前找出未显式添加 `FLAG_GRANT_READ_URI_PERMISSION` 或 `FLAG_GRANT_WRITE_URI_PERMISSION`、升级后可能失效的路径。

`detectAll()` 会根据 target SDK 和设备开关决定是否加入这些检测。面向多版本设备的测试若依赖某个明确 violation，应显式启用并先判断 API/flag 可用性。

## Penalty 的执行语义

| penalty | 行为与边界 |
| --- | --- |
| `penaltyLog()` | 通过 StrictMode logger 输出 violation；相同调用栈指纹会限流 |
| `penaltyDeath()` | ThreadPolicy 在 penalty 处理末尾抛 `RuntimeException`；VmPolicy 调用 `killProcess()` 并退出 |
| `penaltyDeathOnNetwork()` | ThreadPolicy 网络检查点立即抛 `NetworkOnMainThreadException` |
| `penaltyListener(executor, listener)` | 把原始 `Violation` 交给指定 Executor（安排回调在哪个线程执行的调度器）；Executor 参数必填 |
| `penaltyDropBox()` | 经 ActivityManager 写入 DropBox（系统诊断记录存储），源码定位是平台集成与 beta 现场采集 |
| `penaltyDialog()` / `penaltyFlashScreen()` | 面向交互式平台调试，受系统服务和限流约束 |

所有启用的通用 penalty 会应用于该 Builder 中的全部 detector。若某类违规只想记录、另一类要让测试失败，可以在不同测试阶段替换策略，或用 listener 分类后由测试框架做断言。

### 正确使用 penaltyListener

下面的代码把回调放到专用 Executor，避免在发生违规的线程里执行日志 I/O：

```java
Executor strictModeExecutor = Executors.newSingleThreadExecutor();

StrictMode.setThreadPolicy(
        new StrictMode.ThreadPolicy.Builder()
                .detectDiskReads()
                .detectDiskWrites()
                .penaltyListener(
                        strictModeExecutor,
                        violation -> violationQueue.add(violation))
                .build());
```

`onThreadPolicyViolation()` 会在回调执行期间临时放开回调线程的 ThreadPolicy，避免 listener 内部的日志等操作再次触发 listener，形成递归。队列消费、Executor 关闭和测试结束时的清理仍由应用负责。

不要在回调里同步上传网络、写文件或执行重型符号化（把地址解析成函数名和源码位置）。堆栈、路径与明文网络数据也可能包含敏感信息，发布环境采集前要做数据评审。

### Looper 上的 duration 代表什么

线程带 Looper（Android 的消息循环）时，StrictMode 记录 violation 时刻，并把处理任务插到消息队列前部。`durationMillis` 表示从 violation 到 Looper 完成本轮工作、准备再次进入等待之间的时间，可能包含违规操作后的其他同步代码。它不是磁盘 syscall 或网络请求的精确耗时。

同一 Looper 循环的记录数量有上限，日志、Dialog、DropBox 与 VM violation 也有各自限流。日志数量不能直接当成违规发生次数。

## 跨 Binder 的 ThreadPolicy 传播

`setThreadPolicyMask()` 中的 mask 是把多个检测项和 penalty 编码到一个整数里的位集合。它会同步更新两个线程局部状态：

1. libcore `BlockGuard` 的 Java policy；
2. Binder native 层保存的 StrictMode policy mask。

发起同步 Binder 调用时，mask 可以随事务到达服务端 Binder 线程。服务端触发 ThreadPolicy 违规后，`PENALTY_GATHER` 把 `ViolationInfo` 放进 `gatheredViolations` ThreadLocal（每条线程独立的存储槽）。`Parcel.writeNoException()` 最多把前三条违规写入 reply Parcel（返回给调用方的序列化数据容器）；调用方的 `Parcel.readException()` 再进入 `readAndHandleBinderCallViolations()`，补上本地调用栈并交给调用方当前策略处理。

所以应用堆栈中可能看到发生在 `system_server` 或其他 Binder 服务里的磁盘违规。它有助于定位同步 IPC（inter-process communication，进程间通信）间接执行的 I/O，也会让“应用源码里没有读文件却报 DiskReadViolation”看起来反常。

这套传播只处理 ThreadPolicy violation。远端进程的 `VmPolicy` 仍属于远端进程，返回的违规信息也不会报告 Binder 调用本身花了多少时间。

## 临时放行要精确恢复

少量同步 I/O 确认无法迁移，且产品能够接受它的延迟时，可以在最小作用域内放行。下面的代码只在读取配置期间移除当前线程的 disk-read detector：

```java
StrictMode.ThreadPolicy oldPolicy = StrictMode.allowThreadDiskReads();
try {
    readSmallBootConfig();
} finally {
    StrictMode.setThreadPolicy(oldPolicy);
}
```

返回值是放行前的完整策略，必须在 `finally` 中恢复。异常、提前返回和嵌套调用都不应让线程永久处于宽松状态。

两个 API 的位操作不同：

- `allowThreadDiskReads()` 只清除 disk-read 检测；
- `allowThreadDiskWrites()` 同时清除 disk-write 与 disk-read 检测，因为写文件通常伴随读取元数据。

放行不会让操作更快，也不会证明它适合主线程。注释应写明数据量上限、调用阶段和无法异步化的原因，并留下可搜索的问题单 ID，便于后续迁移。

## 自动化测试怎样安装策略

### 不要只在测试线程调用 setThreadPolicy

Instrumentation（设备端测试框架）测试的 `@Before` 通常运行在测试线程。在那里调用 `setThreadPolicy()` 只改变测试线程；应用主线程继续使用原策略。

下面的 Kotlin 片段把策略安装动作切到应用主线程：

```kotlin
val instrumentation = InstrumentationRegistry.getInstrumentation()

instrumentation.runOnMainSync {
    StrictMode.setThreadPolicy(
        StrictMode.ThreadPolicy.Builder()
            .detectDiskReads()
            .detectDiskWrites()
            .detectNetwork()
            .penaltyDeath()
            .build()
    )
}
```

这能把主线程违规变成进程异常，测试运行器通常会把它记录为失败。策略应在测试结束时恢复，避免用例之间互相污染。

另一种做法是在 debug/test 专用 `Application` 中安装策略。它更早生效，也自然覆盖每个应用进程的主线程。需要检查线程池时，在工作线程初始化处单独设置 `ThreadPolicy`。

### CI 结果的稳定性

适合直接让 CI 失败的违规通常具备确定触发点，例如主线程网络、明确的同步磁盘访问或代码主动调用的 `noteSlowCall()`。依赖 finalization、GC、系统服务时序或 feature flag 的 VmPolicy 违规更适合先收集证据，再设计带等待和清理步骤的测试。

Gradle JVM 的 `-D` 属性不会自动出现在设备端应用进程。若需让 CI 选择 log/listener/death 模式，应通过 test manifest、instrumentation argument、BuildConfig 字段或设备端可读取的配置传递，并限制在测试构建。

## 与协程、Compose 和多进程配合

### 协程使用当前执行线程的策略

StrictMode 不把 coroutine（协程）当作独立的策略单位。`Dispatchers.Main` 上的协程使用主线程策略；切到 `Dispatchers.IO` 后使用线程池中实际执行它的 OS 线程策略。把 I/O 移到 `Dispatchers.IO` 能离开主线程，但主线程 StrictMode 不能证明后台任务没有造成任务排队、锁竞争，或切回主线程时等待。

Compose 的 composition（界面组合阶段）、`LaunchedEffect` 和事件回调只要运行在主线程并经过检查点，就与 View 代码一样受 ThreadPolicy 约束。`AndroidView` 中的 `onMeasure()`、`onLayout()` 或回调也没有特殊例外。

### 每个进程分别安装

`android:process` 创建的是另一个 Linux/ART 进程。系统会在那个进程内创建应用的 `Application`，然后调用其 `onCreate()`。同一配置代码会再次运行，策略状态和违规限流表与主进程相互独立。

ThreadPolicy mask 只在一次 Binder 调用期间传播，不能代替远端进程自己的长期配置。

## StrictMode 没覆盖什么

| 问题 | StrictMode 能给出的信息 | 后续工具 |
| --- | --- | --- |
| 主线程命中磁盘/网络检查点 | violation 类型和调用栈，Looper 场景带近似区间 | Perfetto `sched`（CPU 调度事件）、Binder、文件系统与自定义 slice |
| 主线程等待后台任务 | 常常没有磁盘 violation | Perfetto 线程状态、锁与工作线程轨道 |
| Binder 调用慢 | 可能回传远端的 ThreadPolicy 违规；没有 IPC 精确耗时 | Perfetto Binder 轨道 |
| GPU/RenderThread 慢 | 无对应 detector | Perfetto GPU/Frame Timeline、AGI（Android GPU Inspector）、Winscope |
| 分配抖动与系统 GC | 可报告显式 GC；不能刻画分配率和系统 GC 原因 | Android Studio Profiler、Perfetto ART 事件 |
| native 代码直接 I/O | 可能绕过 Java/libcore 检查点 | Perfetto/ftrace（内核函数跟踪）、native tracing |
| 完整资源泄漏证明 | 只覆盖接入的 detector，且部分依赖 GC | LeakCanary、HPROF（Java 堆快照）、Perfetto ART Heap Graph |

StrictMode 适合把“这条路径不该做这类操作”变成可见信号。Perfetto 再回答发生时间、持续区间、调度等待和跨线程因果。

下面的 trace section 用于给已经由 StrictMode 定位的同步路径增加时间轴标记：

```java
Trace.beginSection("decode-startup-config");
try {
    decodeStartupConfig();
} finally {
    Trace.endSection();
}
```

在 Perfetto 中检查这个 slice 与主线程 running/runnable/sleeping（正在执行/等待 CPU/休眠）状态、Binder transaction（一次跨进程调用）和 I/O 事件的重叠，才能判断时间花在 CPU、锁、IPC 还是存储。

## Android 17 排障清单

遇到“没有报”“报错线程不对”或“日志数量对不上”时，按这个顺序检查：

1. `setThreadPolicy()` 是在哪条 OS 线程调用的；
2. 后续代码是否替换过策略，或临时放行后没有恢复；
3. 目标操作是否经过 `BlockGuard`、`CloseGuard` 或 framework 检查点；
4. Builder 是否包含对应 detector，是否依赖 `detectAll()` 的 target/flag 判断；
5. penalty 是否被限流，Looper 是否还没处理队列中的 violation；
6. 堆栈是否包含 Binder 远端违规和调用方补上的本地栈；
7. 多进程场景中，出问题的进程是否运行过初始化代码；
8. flagged API 在设备构建与运行时配置中是否启用。

## 参考源码与文档

- [StrictMode.java（android-17.0.0_r1）](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/os/StrictMode.java)
- [Parcel.java（android-17.0.0_r1）](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/os/Parcel.java)
- [ActivityThread.java（android-17.0.0_r1）](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/app/ActivityThread.java)
- [BlockGuard.java（android-17.0.0_r1）](https://android.googlesource.com/platform/libcore/+/refs/tags/android-17.0.0_r1/dalvik/src/main/java/dalvik/system/BlockGuard.java)
- [CloseGuard.java（android-17.0.0_r1）](https://android.googlesource.com/platform/libcore/+/refs/tags/android-17.0.0_r1/dalvik/src/main/java/dalvik/system/CloseGuard.java)
- [Android Developers：StrictMode](https://developer.android.com/reference/android/os/StrictMode)
