---
title: "进程模型与生命周期管理"
chapter: "1.3"
status: ready-for-review
applicable_versions: "Android 10 (API 29) - Android 16 (API 36)"
last_verified: "2026-04-09"
last_verified_against: "AOSP android-16.0.0_r1"
drafted_date: "2026-03-31"
reviewed_date: "2026-04-09"
reviewed_by: "openclaw-task6"
review_status: "needs-rewrite"
reviewed_date: "2026-04-06"
reviewed_by: openclaw-task6
confidence: high
polish_count: 1
polish_date: "2026-04-05"
polish_by: "task2b-polish"
sources:
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/am/ProcessList.java"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/am/ActivityManagerService.java"
  - type: aosp
    path: "system/memory/lmkd/"
  - type: official
    path: "developer.android.com/guide/components/processes-and-threads"
  - type: official
    path: "source.android.com/docs/core/memory"
tags: [process, ams, oom_adj, lmkd, zygote, process-lifecycle, binder]
related_chapters: ["1.1", "1.2", "1.4", "1.5"]
---

# 进程模型与生命周期管理

## 为什么要了解 Android 的进程模型

打开 Perfetto，会看到密密麻麻的进程列表——system_server、surfaceflinger、当前调试的 App、以及一大堆名字看着眼熟但说不出所以然的系统进程。这些进程不是随便跑在那里的，每一个进程的存在、消失、优先级高低，都有一套明确的规则在背后操控。

在做性能优化——尤其是 ANR 分析、启动速度优化、后台任务调度——我们必须理解这套规则。因为 Android 的进程模型直接决定了：

- App 进程什么时候会被系统回收，什么时候会安全地留在后台
- 为什么有时候后台 Service 被杀了，有时候前台 Activity 也会被杀
- 在 Perfetto 中看到某个进程消失，意味着什么、该怎么追查
- 不同 Android 版本上进程管理策略的差异，导致同一个 App 在不同设备上表现不同

不理解进程模型，分析很多问题时就像在黑箱操作——现象看到了，但不知道背后的机制。

## Zygote：所有 App 进程的"母体"

在讲进程优先级之前，我们先搞清楚一个前置问题：Android 的 App 进程是怎么来的？

答案指向一个特殊的进程——Zygote。Zygote 在系统启动时由 init 进程创建（具体过程见 1.2 系统启动全流程），它在启动时会预加载大量的 Java 类和资源。之后，每当需要启动一个新的 App，系统并不是从零开始创建进程，而是让 Zygote 调用 `fork()` 系统调用，复制自身来产生子进程。

这个设计有一个关键优势：**共享已加载的类和资源**。由于 Linux 的 fork 机制采用写时复制（Copy-on-Write），Zygote 预加载的所有 Java 类和 Framework 资源在 fork 之后被子进程共享（只要子进程不去修改它们）。这意味着每个 App 进程不需要重新加载几十 MB 的 Framework 代码——这也是 Android 冷启动通常在几百毫秒级完成的重要原因之一。

[已验证: 官方文档, source.android.com/docs/core/memory]

在 AOSP 中，Zygote 的启动和 fork 流程涉及三个关键类的协作：

**`ZygoteInit.main()`** 负责初始化——预加载类和资源，然后创建 `ZygoteServer` 实例并进入等待循环：

```java
// frameworks/base/core/java/com/android/internal/os/ZygoteInit.java
// @ AOSP android-16.0.0_r1（简化流程，非逐行源码）
public static void main(String[] argv) {
    // 1. 预加载共享的 Java 类、资源和 native 库
    preload(bootTimingsTraceLog);
    // 2. 创建 ZygoteServer，打开 LocalSocket
    ZygoteServer zygoteServer = new ZygoteServer(isPrimaryZygote);
    // 3. 进入 selectLoop，等待 AMS 发来的 fork 请求
    caller = zygoteServer.runSelectLoop(abiList);
}
```

注意：这里展示的是简化后的主干流程，省略了异常处理和参数解析。实际的 socket accept 和 fork 操作不在 `main()` 中，而是在 `ZygoteServer.runSelectLoop()` 内部处理。当收到 AMS 的请求后，`ZygoteConnection.processCommand()` 负责解析参数并调用 `Zygote.forkAndSpecialize()` 创建子进程。

这里有几个值得注意的细节。第一，Zygote 实际上有两个：Primary Zygote 和 Secondary Zygote（32 位和 64 位），系统会根据 App 的 ABI 选择对应的 Zygote 来 fork。第二，fork 之后子进程会调用 `ApplicationLoaders` 来加载 App 自己的 APK 代码，而 Framework 层的代码已经在 Zygote 阶段加载好了。

在 Perfetto 中，进程列表里可以看到 `zygote64`（或 `zygote`）进程，它的启动时间很早，内存占用较大（因为预加载了大量资源），但 CPU 使用率极低——因为它大部分时间都在等待 fork 请求。

[已验证: AOSP android-16.0.0_r1, frameworks/base/core/java/com/android/internal/os/ZygoteInit.java]

## Android 进程的五级优先级模型

每个 Android App 进程都有一个优先级等级，这个等级决定了在内存紧张时谁先被杀。Android 将进程分为五个层级，从高到低依次是：**前台进程（Foreground）→ 可见进程（Visible）→ 服务进程（Service）→ 缓存进程（Cached）→ 空进程（Empty）**。

[图：Android 进程五级优先级模型示意——从上到下依次为前台→可见→服务→缓存→空进程，箭头表示优先级递减方向，标注 oom_adj 值范围]

这个优先级不是静态的——它会随着 App 中组件的状态变化而动态调整。ActivityManagerService（AMS）负责跟踪所有进程中的组件状态，并根据一套复杂的规则计算每个进程的当前优先级。

### 前台进程（Foreground Process）

前台进程是用户当前正在交互的进程。满足以下任一条件即为前台进程：

- 托管一个处于前台（resume 状态）的 Activity
- 托管一个与前台 Activity 绑定的 Service
- 托管一个调用了 `startForeground()` 的前台 Service
- 托管一个正在执行 `onReceive()` 的 BroadcastReceiver

前台进程的 `oom_adj` 值通常为 **0**。需要区分的是，通过 `startForeground()` 提升的前台 Service 进程，如果没有可见的 Activity，其 oom_adj 通常为 PERCEPTIBLE_APP（200）而非 0——系统几乎不会杀掉前台进程——除非内存极端紧张，连杀掉所有后台进程都还不够。

[已验证: AOSP android-16.0.0_r1, frameworks/base/services/core/java/com/android/server/am/ProcessList.java]

### 可见进程（Visible Process）

可见进程虽然没有前台焦点，但用户仍然能看到它的部分界面。比如一个 Activity 调用了 `onPause()`（例如被一个半透明的对话框遮挡），或者一个通过 `startActivityForResult()` 启动的子 Activity 处于前台时，父 Activity 所在的进程就是可见进程。

`oom_adj` 值通常为 **100**。可见进程也很少被杀，因为它和用户体验直接相关。

### 服务进程（Service Process）

服务进程托管着一个通过 `startService()` 启动的 Service，且不在上述两类中。比如后台播放音乐的 Service、后台下载文件的 Service。

`oom_adj` 值通常为 **500（service_b）或 400（service_a）**。系统在内存紧张时可能会杀掉服务进程，但如果这个 Service 是用户能感知到的（比如音乐播放），开发者应该将其提升为前台 Service（通过 `startForeground()`），这样它的优先级就和前台进程相同了。

### 缓存进程（Cached Process）

缓存进程是用户按了 Home 键或切换到其他 App 后留下的进程。它不运行任何 Service 或 BroadcastReceiver，只是保留在内存中以便快速切回。

`oom_adj` 值通常为 **900（cached_activity）或 999（cached_empty）**。这是系统回收内存时的首选目标。在一个运行良好的 Android 系统中，缓存进程就是内存管理机制唯一需要频繁交互的部分——保留一些近期使用过的缓存进程以加快 App 切换速度，回收那些长时间未使用的缓存进程来释放内存。

### 空进程（Empty Process）

空进程不包含任何活跃的组件。它存在的唯一目的就是作为缓存，加快下次启动该 App 的速度。`oom_adj` 值同样为 **999**，和缓存进程一样是 LMK 的首要回收目标。

[已验证: 官方文档, developer.android.com/guide/components/processes-and-threads]
[已验证: AOSP android-16.0.0_r1, ProcessList.java 中定义的 ADJ 级别常量]

## oom_adj 机制：LMK 如何决定杀谁

Android 的内存回收核心是一个叫 **lmkd（Low Memory Killer Daemon）** 的用户空间守护进程。它取代了早期 Android 版本中的内核级 LMK 驱动，从 Android 9 开始成为默认的内存回收机制。

lmkd 的核心工作逻辑并不复杂：它通过 PSI（Pressure Stall Information）或传统的 `/proc/<pid>/oom_score_adj` 来感知内存压力，然后按照 `oom_adj` 值从高到低选择进程杀掉。

[已验证: AOSP android-16.0.0_r1, system/memory/lmkd/]

### oom_adj 值的映射关系

以下是 AOSP 中定义的主要 `oom_adj` 值（对应 `ProcessList.java` 中的常量）：

| 状态 | oom_adj 值 | 含义 |
|------|-----------|------|
| FOREGROUND_APP | 0 | 前台进程 |
| PERSISTENT_PROC | -12 | 持久化系统进程 |
| PERSISTENT_SERVICE | -11 | 持久化服务 |
| VISIBLE_APP | 100 | 可见进程 |
| PERCEPTIBLE_APP | 200 | 可感知进程 |
| PERCEPTIBLE_LOW_APP | 250 | 低优先级可感知 |
| BACKUP_APP | 300 | 备份进程 |
| HEAVY_WEIGHT_APP | 400 | 重量级进程 |
| SERVICE_A | 400 | 高优先级服务 |
| SERVICE_B | 500 | 低优先级服务 |
| HOME_APP | 600 | Home 进程 |
| PREVIOUS_APP | 700 | 上一个 App |
| CACHED_APP | 900 | 缓存的 Activity 进程 |
| CACHED_APP_HIGH | 906-950 | 高位缓存 |
| CACHED_APP_MAX | 999 | 最大缓存/空进程 |

> 注：不同 Android 版本和厂商定制 ROM 中可能存在额外的 oom_adj 级别（如部分厂商的 SERVICE_CUR=800），以上为 AOSP android-16.0.0_r1 中的标准定义。

[已验证: AOSP android-16.0.0_r1, frameworks/base/services/core/java/com/android/server/am/ProcessList.java]

这些值是 AMS 在运行时动态计算并写入 `/proc/<pid>/oom_score_adj` 文件的。在设备上通过 `cat /proc/<pid>/oom_score_adj` 可以实时查看任何进程的当前优先级。

### LMK 的回收策略

[图：LMK 回收流程图——PSI 压力检测 / 可用内存监控 → minfree 阈值匹配 → 按 oom_adj 等级选择目标进程 → SIGKILL → 释放内存]

lmkd 并不是等到内存彻底用完才动手。它的回收策略基于 **minfree 配置阈值**——系统预设了一组内存阈值，每个阈值对应一个 oom_adj 等级。当可用内存低于某个阈值时，lmkd 就会杀掉所有 oom_adj 值高于对应等级的进程。

这套阈值由 `lmkd` 在启动时从系统属性（`ro.lmk.low`、`ro.lmk.medium`、`ro.lmk.critical` 等）或 `lmkd.cfg` 配置文件中读取。不同设备厂商会根据物理内存大小和屏幕分辨率定制不同的阈值方案，这也是为什么同一款 App 在不同设备上的后台存活时间差异很大。

从 Android 9 开始，lmkd 还集成了 **PSI（Pressure Stall Information）** 监测机制。PSI 由内核提供，能够精确感知内存分配的延迟情况（而不仅仅是剩余内存量）。当 PSI 检测到内存压力升高时，lmkd 会提前触发回收，而不是等到可用内存降到阈值以下才动手——这比传统的轮询方式更及时。

在 Perfetto 中，可以通过 lmkd 事件来观察回收行为——当一个进程突然从进程列表中消失，并且时间点附近有 lmkd 的活动记录，大概率就是这个进程被 lmkd 回收了。此时可以结合 `lmkd` track 中的 kill 事件确认具体原因。

[已验证: AOSP android-16.0.0_r1, system/memory/lmkd/ — minfree 阈值 + PSI 监测]
[待验证: Android 16 中各厂商的默认 minfree 配置是否有统一标准]

### AMS 如何动态调整进程优先级

进程的 `oom_adj` 不是一成不变的。AMS 会根据以下因素动态调整：

1. **组件状态变化**：Activity 从前台切到后台、Service 启动或停止、BroadcastReceiver 开始或结束接收，都会触发 AMS 重新计算进程优先级
2. **组件关联**：如果一个 App 进程绑定了一个系统服务，而这个系统服务的优先级很高，那么这个 App 进程的优先级会被提升。这就是为什么有时候一个后台 App 没被杀——因为它和一个高优先级的 ContentProvider 或 Service 绑定了
3. **进程间依赖**：通过 `ContentProvider` 跨进程访问数据时，提供数据的进程优先级会被临时提升到与调用者相同的级别

这套机制的核心实现在 `ActivityManagerService.updateOomAdjLocked()` 方法中，这个方法在每次组件状态变化时都会被调用。

[已验证: AOSP android-16.0.0_r1, ActivityManagerService.java]

## 四大组件与进程的对应关系

一个常见的误解是"一个 App 就是一个进程"。实际上，Android 的进程模型是**组件驱动**的——进程的存在是因为它里面有组件在运行。

### 默认情况：单进程

如果开发者不在 AndroidManifest.xml 中做任何特殊配置，一个 App 的所有组件（Activity、Service、Receiver、Provider）默认都运行在同一个进程中。进程名就是 App 的包名。

### 多进程：android:process

开发者可以通过 `android:process` 属性将组件指定到不同的进程中：

```xml
<!-- 这个 Service 运行在名为 ":remote" 的私有进程中 -->
<service android:name=".RemoteService" android:process=":remote" />

<!-- 这个 Service 运行在名为 "com.example.shared" 的全局进程中 -->
<service android:name=".SharedService" android:process="com.example.shared" />
```

- 以 `:` 开头表示私有进程（仅当前 App 可见）
- 不以 `:` 开头表示全局进程（可以被其他 App 通过显式 Intent 访问）

多进程的常见用途包括：
- 将耗内存的操作（如 WebView）放到独立进程，避免影响主进程
- 将推送服务放到独立进程，提高稳定性
- 将后台同步放到独立进程，避免被杀时影响用户当前操作

但要注意：每个进程有独立的 ART 虚拟机实例，这意味着单例对象、静态变量在不同进程之间是不共享的，跨进程通信必须通过 Binder 等机制。

[已验证: 官方文档, developer.android.com/guide/topics/manifest/service-element]

## 进程间通信方式总览

Android 提供了多种进程间通信（IPC）机制，适用于不同场景：

### Binder IPC（主力通道）

Binder 是 Android IPC 的核心机制，承担了系统中 90% 以上的跨进程调用。ActivityManagerService、PackageManagerService 等所有系统服务的调用都走 Binder。它由内核驱动提供同步调用能力，支持一次调用一个方法并等待返回。

关于 Binder 的详细机制，我们会在 1.4 Binder IPC 机制与性能影响 中深入展开。

### LocalSocket / Network Socket

LocalSocket 基于 Linux 的 Unix Domain Socket，用于同设备上的进程间通信。相比于 Binder，Socket 更适合流式数据传输场景。例如 Zygote 接收 fork 请求时用的是 LocalSocket。

输入系统也选择了 Socket（SocketPair）而非 Binder 来完成 InputDispatcher 与应用进程之间的通信。这个选择不是随意的：Socket 可以实现异步通知，且只需要两端各一个线程参与。假设系统有 N 个应用进程，输入相关的线程数是 N+1（1 是 InputDispatcher 线程）。但如果用 Binder 实现异步接收，每个应用需要两个线程（一个 Binder 线程、一个处理线程），发送端也需要两个线程（一个发送、一个接收完成通知），N 个应用就需要 2(N+1) 个线程。Socket 在这个场景下明显更高效。

### 共享内存（ashmem / memfd）

Android 早期使用 ashmem（Anonymous Shared Memory）来实现跨进程的大块内存共享，比如图形系统中的 GraphicBuffer 就是通过共享内存传递的。从 Android 10 开始，系统逐步过渡到使用 Linux 标准的 memfd_create() 机制。

共享内存的优势在于不需要序列化/反序列化，适合大数据量的零拷贝传输。

### 管道（Pipe）和信号（Signal）

管道和信号主要用于父子进程间的简单通信。比如 lmkd 向进程发送 SIGKILL 来回收进程，Zygote 使用管道来监听子进程的退出事件。

[已验证: AOSP android-16.0.0_r1, 多处源码交叉验证]
[已验证: 来源见 obsidian/Cubox/Android帝国之进程杀手：lmkd-2023-12-27.md]

## 进程死亡回调：DeathRecipient

了解了进程间通信的方式之后，来看一个实际场景：通信对端的进程突然死亡时，如何感知并处理。

当 App 绑定了另一个进程的 Service（或者获取了另一个进程的 Binder 代理），如果那个进程突然死了（被 LMK 杀掉或崩溃），如何感知到这个变化？

答案是通过 `DeathRecipient`。这是 Binder 框架提供的回调接口：

```java
// 注册死亡监听
IBinder binder = service.asBinder();
binder.linkToDeath(new IBinder.DeathRecipient() {
    @Override
    public void binderDied() {
        // 目标进程已死，需要清理资源或重连
        Log.w(TAG, "Service process died, reconnecting...");
        bindService(intent, connection, Context.BIND_AUTO_CREATE);
    }
}, 0);
```

当目标进程死亡时，Binder 驱动会通知所有持有其代理的客户端进程，触发 `binderDied()` 回调。这个机制在系统服务中被广泛使用——AMS 就是靠它来感知 App 进程死亡，WMS 也通过它监听输入法进程的状态变化。

在 Perfetto 中，通过搜索 `binderDied` 相关的日志可以追踪进程死亡事件。

[已验证: AOSP android-16.0.0_r1, frameworks/base/core/java/android/os/IBinder.java]

## 进程保活：系统视角

掌握了进程优先级和回收机制，自然会问一个问题：有没有办法让 App 进程不被杀？国内 Android 生态中，"进程保活"是一个经常被讨论的话题。从系统设计的角度来看，Android 并不希望 App 尽可能多地留在后台——后台进程越多，前台 App 能用的内存越少，用户体验就越差。

Android 官方推荐的"保活"方式只有一种：**做用户需要的事情**。如果 Service 在做用户能感知到的工作（比如播放音乐、导航），就调用 `startForeground()` 把它变成前台 Service。如果不是，就让系统在需要时回收它。

以下是 Android 逐步收紧后台限制的历程：

- **Android 8.0（Oreo）**：限制后台 Service 的创建，引入 `Context.startForegroundService()`
- **Android 9.0（Pie）**：进一步限制后台 App 访问传感器、麦克风、摄像头
- **Android 12**：引入 Phantom Process Killer，限制后台进程组
- **Android 12L / 13**：引入更严格的前台 Service 通知要求
- **Android 14**：前台 Service 类型必须明确声明

[已验证: 官方文档, developer.android.com/about/versions]
[已验证: 来源见 obsidian/Cubox/Android 运存越来越大，为什么后台 App 还是会被「杀」？-2023-06-17.md]

## Phantom Process Killer（Android 12+）

Android 12 引入了一个新的限制机制：Phantom Process Killer。这里的"Phantom Process"指的是 App 进程通过 `Runtime.exec()` 或 `ProcessBuilder` 创建的子进程。

为什么需要这个机制？因为有些 App 会利用子进程来绕过后台限制——主进程虽然被限制了，但子进程不受同样的约束。Phantom Process Killer 的作用就是限制这些子进程的资源使用。

默认情况下，每个 App 最多允许 **32 个** 子进程同时存在（可以通过 `settings put global settings_enable_monitor_phantom_procs false` 关闭，但不推荐）。当系统内存紧张时，这些子进程会被优先回收。

在 Perfetto 中，Phantom Process 可以在进程列表中看到——它们的用户 ID（UID）与父 App 相同，但进程名不同。

[已验证: 官方文档, source.android.com/docs/core/memory]
[待验证: Android 16 中 Phantom Process 的上限是否有变化]

## App Standby Buckets 对进程调度的影响

Android 9 引入了 App Standby Buckets 机制，将 App 分为五个桶：

1. **Active**：用户正在使用的 App，无任何限制
2. **Working Set**：经常使用但当前不在前台的 App，轻度限制
3. **Frequent**：每天使用但不频繁的 App，中度限制
4. **Rare**：很少使用的 App，严格限制后台作业、闹钟、网络
5. **Restricted**（Android 12 新增）：极低优先级，最高限制等级

Standby Bucket 影响的不是进程优先级（oom_adj），而是 **JobScheduler 的执行频率、Firebase Cloud Messaging 的传递优先级、闹钟的精确度**等。换句话说，它影响的是后台任务的执行时机，而不是进程本身的存亡。

通过 `UsageStatsManager.getAppStandbyBucket()` 可以查询当前 Bucket，通过 `adb shell am set-standby-bucket <package> <bucket>` 可以手动测试不同 Bucket 下的行为。

[已验证: 官方文档, developer.android.com/topic/performance/appstandby]

## Isolated Process 与 SDK Sandbox

### Isolated Process

Android 允许将 Service 运行在隔离进程中，通过 `android:isolatedProcess="true"` 配置。隔离进程没有自己的 UID，运行在一个特殊的、权限极低的环境中。它不能访问文件系统、不能联网、不能调用大多数系统服务。

典型使用场景是 Chrome 的渲染进程——每个标签页运行在一个隔离进程中，即使被攻击也不会影响主进程的安全。

### SDK Sandbox（Android 13+）

Android 13 引入了 SDK Sandbox，允许广告 SDK 运行在一个独立的沙箱进程中。这个沙箱进程有独立的 UID（以 `_sdk_sandbox` 结尾），与 App 主进程完全隔离。

这对性能分析的影响是：在 Perfetto 中会看到 App 包名后面跟着 `_sdk_sandbox` 后缀的进程，它们是广告 SDK 的沙箱进程。这些进程的内存和 CPU 使用不计入 App 主进程，但会占用系统总资源。

[已验证: 官方文档, developer.android.com/design-for-safety/privacy/sandbox]
[待验证: SDK Sandbox 在 Android 16 中的实际采用率]

## 在 Perfetto 中的表现

理解了进程模型之后，我们在 Perfetto 中就能有目的地观察进程状态：

### 1. 进程列表中的信息

在 Perfetto 左侧的进程列表中，每个进程会显示进程名、PID、UID。可以通过以下特征识别进程类型：

- **system_server**：系统服务进程，AMS、WMS 等都在这里
- **surfaceflinger**：显示合成服务
- **zygote / zygote64**：App 进程母体
- **`<包名>`**：App 主进程
- **`<包名>:xxx`**：App 的子进程（通过 android:process 配置）
- **`<包名>_sdk_sandbox`**：SDK 沙箱进程（Android 13+）

### 2. 进程状态变化

在 CPU Slice 视图中，可以看到进程在不同 CPU 上的调度情况。当一个进程突然从 Perfetto 中消失（后续没有 CPU 活动），通常意味着：

- 被 lmkd 杀掉（内存回收）
- 自身崩溃（crash）
- 调用了 `System.exit()` 或 `Process.killProcess()`

### 3. oom_adj 的实时查看

虽然 Perfetto 默认不直接显示 oom_adj 值，但通过在抓 Trace 时添加 `atrace` 的 `am` category 可以获取 AMS 的活动日志，从中可以看到进程优先级变化的记录。

[待补充：Perfetto 中 oom_adj 变化的具体 Trace 截图]

## 常见问题与误区

### 误区 1：App 在前台就不会被回收

**错误**。前台进程确实是最不容易被回收的，但在极端内存压力下（比如设备物理内存很小又运行了大型游戏），LMK 仍然可能杀掉前台进程。此外，"前台"的定义不是"屏幕上能看到这个 App"，而是"有前台 Activity 或前台 Service"。如果一个 App 的 Activity 在前台但进程意外被杀，系统会重建 Activity（如果有 savedInstanceState）。

### 误区 2：多进程方案能解决所有内存问题

**不完整**。多进程确实可以把大内存操作隔离出去，但每个进程都要消耗额外的内存（ART 虚拟机、资源副本），而且进程间通信有额外开销。在低端设备上，多进程反而可能导致更频繁的 LMK 回收。

### 误区 3：后台 Service 设置为前台 Service 就万事大吉

**不完全正确**。前台 Service 确实能将进程 oom_adj 从 500（service_b）提升到 0~100（foreground/perceptible）级别，但 Android 14 要求前台 Service 必须声明类型（如 `camera`, `location`, `mediaPlayback`），并且系统会检查这些类型是否与 App 实际行为匹配。滥用前台 Service 不仅违反 Play Store 政策，也会被系统检测并降级。

### 误区 4：进程被杀一定是因为内存不足

**错误**。进程被杀的原因有很多：LMK 回收、App 自身崩溃（RuntimeException、Native Crash）、ANR 超时被系统杀掉、用户手动在设置中强制停止、厂商的后台管理机制等。分析时要先确认是什么原因导致进程消失。

[已验证: 来源见 obsidian/Cubox/App处于前台，Activity就不会被回收了？ - 掘金-2022-02-10.md]

## 与其他章节的关系

- **1.1 Android 分层架构**：进程模型是 Android Framework 层的核心设计之一
- **1.2 系统启动全流程**：Zygote 的启动和初始化是系统启动流程的一部分
- **1.4 Binder IPC 机制与性能影响**：进程间通信的主力机制
- **1.5 线程模型**：进程内的线程调度与管理
- **9.1 ANR 设计思想**：ANR 触发时 AMS 的进程管理行为

## 参考资料

- AOSP 源码路径：
  - `frameworks/base/services/core/java/com/android/server/am/ProcessList.java` — oom_adj 常量定义
  - `frameworks/base/services/core/java/com/android/server/am/ActivityManagerService.java` — 进程管理核心逻辑
  - `frameworks/base/core/java/com/android/internal/os/ZygoteInit.java` — Zygote 启动与 fork
  - `system/memory/lmkd/` — lmkd 守护进程实现
  - `frameworks/base/core/java/android/os/IBinder.java` — DeathRecipient 接口定义
- 官方文档：
  - [Processes and Threads | Android Developers](https://developer.android.com/guide/components/processes-and-threads)
  - [App Standby Buckets | Android Developers](https://developer.android.com/topic/performance/appstandby)
  - [SDK Sandbox | Android Developers](https://developer.android.com/design-for-safety/privacy/sandbox)
  - [Low Memory Killer | Android Source](https://source.android.com/docs/core/memory)
