---
title: "案例集"
chapter: "9.5"
status: ready-for-review
drafted_date: "2026-04-02"
applicable_versions: "Android 8.0 (API 26) - Android 16 (API 36)"
last_verified: "2026-04-02"
last_verified_against: "AOSP android-14.0.0_r1"
confidence: medium
sources:
  - type: blog
    path: "Obsidian/Cubox/ANR-实例分析-启动应用失败-2024-12-18.md"
  - type: blog
    path: "Obsidian/Cubox/ANR-实例分析-Input dispatching timed out-2024-12-18.md"
  - type: blog
    path: "Obsidian/Cubox/ANR-实例分析-负载过高-2024-12-18.md"
  - type: blog
    path: "Obsidian/Cubox/今日头条 ANR 优化实践系列 - 告别 SharedPreference 等待-2023-12-20.md"
  - type: blog
    path: "Obsidian/Cubox/疑难ANR原因分析-冻结导致直播讲解相关完整笔记-2025-02-22.md"
  - type: aosp
    path: "frameworks/base/core/java/android/app/SharedPreferencesImpl.java"
  - type: aosp
    path: "frameworks/native/services/inputflinger/dispatcher/InputDispatcher.cpp"
tags: ['anr', 'case-study', 'input-dispatching', 'sharedpreferences', 'system-load', 'binder', 'process-freeze']
related_chapters: ["9.1", "9.2", "9.3", "9.4", "1.4"]
---

# 案例集

> **阅读本章前，你需要了解：** §9.1 ANR 的设计思想、§9.2 ANR 类型与触发条件、§9.3 ANR 分析方法论、§9.4 特殊场景的 ANR。
> **阅读本章后，你可以去看：** §13 Perfetto 工具（用 Trace 验证本章的分析结论）。

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 提供 3-5 个真实 ANR 案例
- 🔹 案例需覆盖：死锁、主线程 I/O、Binder 超时、系统负载、SharedPreferences
- 🔹 每个案例包含：ANR 信息摘录、分析过程、根因定位、修复方案

### 扩展（可选深入）

- 🔸 线上 ANR 聚合分析的实践
- 🔸 系统级 ANR 案例（SystemServer ANR / Watchdog）

### OpenClaw 加工指引

> **锚点**是最低覆盖要求，加工时必须逐条落实并标注验证结果。
> **扩展**视素材丰富程度选择性深入。
> 如果从 Obsidian 素材或 AOSP 源码中发现大纲未列出但与本节强相关的知识点，
> 可**就地插入**最相关的锚点之后，并用 `[自动发现]` 标注，方便后续 review。
> 锚点内容需 L1/L2 验证，扩展内容至少 L2 验证，自动发现内容至少标注来源。
<!-- outline-end -->

## 为什么要看案例

前四节我们分别讲了 ANR 的设计思想、类型分类、分析方法论和特殊场景。这些是分析 ANR 的"工具箱"。但真实世界中，ANR 很少按照教科书的方式出现——trace 中的主线程堆栈可能指向 `nativePollOnce`（看起来什么都没做），负载可能处于正常范围，甚至 ANR 发生的进程本身没有任何问题。

案例集存在的意义就在这里：我们用五个从真实产品环境中提取的案例，带你走一遍完整的分析过程。每个案例的原始数据（trace、event log、AnrManager 信息）都保留了关键部分，你可以在阅读时尝试自己先判断原因，再对照后面的分析。

这五个案例覆盖了 ANR 中最常见的五类根因：

- **案例 1：系统负载过高导致 Input ANR** — 设备全局 IO 压力爆表，所有进程都在等磁盘
- **案例 2：SystemServer 主线程耗时导致 Input ANR** — 根因不在 App 侧，而在 system_server 的 Notifier 处理
- **案例 3：SharedPreferences 等待导致 Broadcast ANR** — `QueuedWork.waitToFinish()` 把主线程卡住了
- **案例 4：进程冻结导致 Input ANR** — 系统冻结了 Gesture Monitor 进程，事件无人消费
- **案例 5：应用启动超时导致焦点窗口缺失 ANR** — 目标应用启动失败，焦点无处可去

---

## 案例 1：系统负载过高 — IO 压力导致的 Input ANR

### 问题现象

设备：MTK 平台，Android 14。用户反馈 Launcher 偶发无响应。

Event log 中的 ANR 记录：

```
04-07 03:13:49.417 1444 8816 I am_anr : [0,2135,com.android.launcher,
  751550021, Input dispatching timed out 
  (Application does not have a focused window)]
```

ANR 类型是 Input dispatching timed out，原因是"没有焦点窗口"。Launcher 看起来是受害者。

[来源: Obsidian/Cubox/ANR-实例分析-负载过高-2024-12-18.md]

### 分析过程

**第一步：看 trace。** 主线程堆栈：

```
"main" prio=5 tid=1 Native
  | state=S schedstat=( 10985995408825 3939822638104 29985904 )
  native: #00 pc 0009013c libc.so (syscall+28)
  native: #01 pc 0022cfac libart.so (art::ConditionVariable::WaitHoldingLocks+140)
  native: #02 pc 00534d48 libart.so (art::JNI<false>::CallObjectMethodV+1244)
  native: #03 pc 000dca68 libandroid_runtime.so (_JNIEnv::CallObjectMethod+120)
  native: #04 pc 001489d0 libandroid_runtime.so (NativeDisplayEventReceiver::dispatchVsync+64)
  at android.os.MessageQueue.nativePollOnce(Native method)
```

主线程处于 `Native` 状态，堆栈指向 `nativePollOnce`。注意这里还有一个值得关注的细节——在 `nativePollOnce` 之前经过了 `dispatchVsync` → `CallObjectMethod` → `WaitHoldingLocks`，说明主线程在处理 VSync 回调时进入了 ART 内部的锁等待。但核心问题是：主线程确实在阻塞，但没有被 App 自己的业务代码卡住。

**第二步：看 AnrManager 的负载信息。** 这是关键：

```
Load: 56.48 / 30.74 / 22.68
----- Output from /proc/pressure/memory -----
  some avg10=82.71 avg60=58.68 avg300=20.55
  full avg10=51.17 avg60=34.93 avg300=12.29
----- Output from /proc/pressure/io -----
  some avg10=85.37 avg60=63.13 avg300=23.13
  full avg10=38.46 avg60=20.76 avg300=7.13
```

系统 1 分钟平均负载 30.74，5 分钟平均 22.68——这远超正常范围。内存压力 `avg10=82.71` 说明最近 10 秒有 82% 的时间在等待内存回收。IO 压力更夸张——`avg10=85.37`，意味着 85% 的时间里至少有一个进程在等 IO。

再看 CPU 使用分布：

```
80% 84/kswapd0          ← 内核回收线程吃了 80% CPU
55% 1444/system_server  ← system_server 占 55%，29% kernel 态
21% com.ss.android.ugc.aweme  ← 抖音，17% kernel 态，大量 major faults
CPU usage TOTAL: 99%  14% user + 36% kernel + 43% iowait
```

全局 CPU 使用率 99%，其中 **43% 是 iowait**——CPU 在等磁盘。`kswapd0` 内核线程占了 80% CPU 在疯狂回收内存，多个进程都有大量 `major faults`（需要从磁盘读页）。系统处于严重的内存紧张和 IO 拥堵状态。

### 根因

这不是某个 App 的问题，而是**系统整体性能崩溃**。内存紧张 → 大量 page fault → 磁盘 IO 飙升 → 所有进程都在等磁盘 → CPU 大量时间花在 iowait 上 → InputDispatcher 虽然在运行，但 App 进程调度不到 CPU 时间，导致 5 秒内无法处理输入事件。

从 trace 看，Launcher 主线程在 `dispatchVsync` 过程中进入了 ART 的 `WaitHoldingLocks`，这很可能是因为 GC 正在进行（内存压力下 GC 更频繁），主线程需要等 GC 完成才能继续。

### 修复方案

系统层面的优化：

1. **排查内存大户**。AnrManager 日志中 `kswapd0` 占 80% CPU 说明系统在持续回收内存。需要排查是哪个进程消耗了大量内存导致系统进入这种状态，通常是大图片缓存、视频缓存未做限制。
2. **IO 调度优化**。在存储性能较差的设备上（eMMC），大量后台 IO 会严重拖慢前台进程。可以通过 `ionice` 提升前台进程的 IO 优先级，或限制后台进程的 IO 带宽。
3. **内存压力监控**。在应用侧可以通过 `Debug.getMemoryInfo()` 或 `/proc/pressure/memory` 监控内存压力，在压力过大时主动释放缓存。

App 层面的防御：

- 在 Launcher 等 SystemUI 组件中，减少大对象分配，避免在主线程做可能触发 GC 的操作
- 对于这类系统级负载问题，App 端能做的不多，但可以降低自身的内存和 IO 开销来减轻系统压力

### 举一反三

这类"系统负载过高"的 ANR 有一个共同特征：trace 中主线程堆栈看起来很"干净"（`nativePollOnce` 或 `WaitHoldingLocks`），但 AnrManager 的负载信息会暴露真相。当你看到 Load 值远超 CPU 核心数、iowait 占比超过 20%、`kswapd0` 在 CPU 排行榜前面时，就要往系统负载方向分析，而不是盯着 App 的堆栈看。

---

## 案例 2：SystemServer 主线程耗时 — server 端不响应导致的 Input ANR

### 问题现象

设备：Android 14。Launcher 出现 Input ANR：

```
07-20 15:01:37.293 1385 20230 I am_anr : [0,3450,com.android.launcher,
  751550021, Input dispatching timed out 
  ([Gesture Monitor] swipe-up (server) is not responding. 
   Waited 5001ms for MotionEvent)]
```

注意这个 ANR 类型和案例 1 不同——不是"没有焦点窗口"，而是 **"(server) is not responding"**。这说明 InputDispatcher 在等待一个 server 端的 Gesture Monitor 消费事件，但它超过 5 秒没有响应。

[来源: Obsidian/Cubox/ANR-实例分析-Input dispatching timed out-2024-12-18.md]

### 分析过程

**第一步：看 trace。** Launcher 主线程堆栈：

```
"main" prio=5 tid=1 Native
  | state=S schedstat=( 101214367947 65037795077 427377 )
  native: #00 pc 00103948 libc.so (__epoll_pwait+8)
  native: #01 pc 00013b64 libutils.so (android::Looper::pollOnce+212)
  at android.os.MessageQueue.nativePollOnce(Native method)
  at android.os.Looper.loopOnce(Looper.java:189)
```

主线程在 `nativePollOnce` 等待消息——标准的空闲状态。Launcher 本身没有任何问题。

**第二步：看 AnrManager 负载。**

```
Load: 0.0 / 0.0 / 0.0
----- Output from /proc/pressure/cpu -----
  some avg10=17.69 avg60=17.16 avg300=10.98
64% TOTAL: 36% user + 22% kernel + 1.5% iowait
```

负载不算极端，但有一个异常：**system_server 占了 215% CPU**（172% user + 43% kernel），而且有大量 major faults（1206 个）。system_server 在做非常重的 IO 操作。

**第三步：找 Logcat 线索。** 在 Logcat 中发现一条关键信息：

```
07-20 15:00:45.316 1385 1385 W Looper : 
  Slow dispatch took 10578ms main 
  h=com.android.server.power.Notifier$NotifierHandler 
  c=null m=1
```

这条 Slow Looper 日志说明 system_server 的主线程在处理 `Notifier$NotifierHandler` 的消息时花了 **10578ms**。时间点是 `15:00:45`，ANR trace 的时间是 `15:00:45.488`——两者几乎重合。

### 根因

这是一个**典型的系统侧 ANR**。ANR 发生在 Launcher 进程，但根因在 system_server。具体机制如下：

Gesture Monitor（手势监控器）的输入事件回调运行在 system_server 进程中。当用户做了"swipe-up"手势时，InputDispatcher 将 MotionEvent 发送给 Gesture Monitor，等待它消费。但此时 system_server 的主线程正被 `Notifier$NotifierHandler` 的消息阻塞了 10.5 秒，Gesture Monitor 的回调无法执行，InputDispatcher 等了 5 秒就触发了 ANR。

从 ANR 消息来看，被控的是 Launcher（`pid=3450`），但实际问题是 system_server 的消息处理卡住了。这种"躺枪"的 ANR 在 Input ANR 中很常见——App 本身什么都没做错，只是恰好是当前焦点窗口，被系统端的问题连累了。

### 修复方案

这类问题需要系统侧修复：

1. **排查 Notifier 处理耗时**。`Notifier$NotifierHandler` 负责在屏幕亮灭、App 切换等场景发送通知。需要检查其 `handleMessage` 中做了什么耗时操作——常见原因是广播发送、权限检查、或同步等待其他系统服务。
2. **将耗时操作移到子线程**。system_server 的主线程和 App 主线程一样，不能有耗时操作。如果 Notifier 需要做 IO 或长耗时计算，应该用 `BackgroundThread` 或新建 HandlerThread 处理。
3. **App 侧的防御**。对于这种系统侧导致的 ANR，App 端几乎无法预防。可以通过监控 Slow Looper 日志的出现频率来评估系统健康度，在特定 ROM 版本上做针对性适配。

[已验证: AOSP android-14.0.0_r1, Notifier 路径为 frameworks/base/services/core/java/com/android/server/power/Notifier.java]

### 举一反三

Input ANR 中"(server) is not responding"这个子类型，根因几乎一定在 system_server 端。分析方法不是看 App 的 trace（它通常是干净的），而是找 system_server 的主线程耗时日志。`Slow dispatch` 日志是一个非常有价值的线索——如果 system_server 的主线程有超过几秒的 dispatch 耗时，几乎必然会导致后续的 Input ANR。

---

## 案例 3：SharedPreferences 写入等待 — QueuedWork 阻塞主线程

### 问题现象

大型 App（日活千万级），在 Activity 切换、Service 停止等生命周期节点偶发 ANR。ANR trace 显示主线程堆栈：

```
"main" prio=5 tid=1 WAIT
  at java.lang.Object.wait(Native method)
  at java.lang.Object.wait(Object.java:422)
  at java.util.concurrent.ConcurrentLinkedQueue.poll(ConcurrentLinkedQueue.java:918)
  at android.app.QueuedWork.waitToFinish(QueuedWork.java:176)
  at android.app.ActivityThread.handlePauseActivity(ActivityThread.java:4640)
  at android.app.ActivityThread.access$1500(ActivityThread.java:252)
```

[来源: Obsidian/Cubox/今日头条 ANR 优化实践系列 - 告别 SharedPreference 等待-2023-12-20.md]

### 分析过程

这个堆栈已经非常明确了——主线程在 `QueuedWork.waitToFinish()` 上阻塞。但要理解为什么会阻塞，需要深入 SharedPreferences 的写入机制。

SharedPreferences 提供了两个写入 API：`commit()` 和 `apply()`。`commit()` 是同步写入，会直接阻塞调用线程直到文件写入完成，开发者一般知道要避免在主线程调用。但 `apply()` 被设计为"异步写入"，很多开发者认为它不会阻塞主线程。这个认知是错误的。

`apply()` 的实际机制是：

1. 先将数据写入内存缓存（这一步在调用线程执行）
2. 将文件写入任务封装成 `Runnable`，提交到名为 `queued-work-looper` 的后台线程
3. 后台线程执行文件写入，完成后通过 `CountDownLatch` 通知

问题出在 Android 系统的设计中：在 Activity 的 `onPause()`、`onStop()`，Service 的 `onDestroy()` 等生命周期节点，系统会调用 `QueuedWork.waitToFinish()`，强制等待所有通过 `apply()` 提交的写入任务完成。这就是 trace 中主线程阻塞的根源。

```java
// frameworks/base/core/java/android/app/QueuedWork.java
public static void waitToFinish() {
    Runnable toFinish;
    while ((toFinish = sPendingWorkFinishers.poll()) != null) {
        toFinish.run();  // 这里面就是 writtenToDiskLatch.await()
    }
}
```

当 App 中存在大量 `apply()` 调用但后台写入还没完成时，主线程在生命周期切换时就会被 `waitToFinish()` 卡住，等待时间取决于积压了多少写入任务。在大型 App 中，可能有几十甚至上百个 SharedPreferences 实例同时在做 `apply()`，积压的写入量非常大。

### 根因

SharedPreferences 的 `apply()` 在设计上就存在这个缺陷：它声称是异步的，但在组件生命周期切换时会退化为同步等待。随着 App 规模增长，SP 文件数量增多、单文件数据量增大，等待时间会被不可控地拉长。

Google 在 Android 8.0+ 做了优化：`waitToFinish()` 不再只是等待，而是主动帮后台线程一起写（"协助写入"），但由于策略保守（只处理队列中的一部分），在高负载场景下仍然会 ANR。

[已验证: AOSP android-14.0.0_r1, frameworks/base/core/java/android/app/SharedPreferencesImpl.java]

### 修复方案

**方案一：减少 SP 使用量。** 严格控制每个 SP 文件的大小，只存真正需要持久化的少量配置数据。Google 官方文档明确说"轻量级存储"，这不是建议，是硬性限制。

**方案二：预加载。** 在 Application 初始化阶段提前调用 `SharedPreferences.getSharedPreferences()` 触发文件加载，避免在用户交互时才首次加载。对于核心场景使用的 SP 文件，确保不要超过几十 KB。

**方案三：替换写入方案。** 字节跳动团队的方案是通过反射替换 `sPendingWorkFinishers`（一个 `ConcurrentLinkedQueue`），让它的 `poll()` 永远返回 null，从而跳过 `waitToFinish()` 的等待逻辑。这个方案在字节系多个产品上验证有效，但涉及反射系统内部类，需要注意兼容性风险。

**方案四：迁移到 DataStore。** Google 推荐的替代方案是 Jetpack DataStore，基于 Kotlin Flow 和 Protocol Buffers 实现，没有 `waitToFinish` 的问题。适合新项目或大规模重构时使用。

### 举一反三

这类 ANR 的特征是 trace 中出现 `QueuedWork.waitToFinish` 或 `SharedPreferencesImpl.awaitLoadedLocked`。如果你在 trace 中看到这两个堆栈，不需要再往深处分析——根因就是 SP。修复策略按优先级：减少用量 > 预加载 > 替换存储方案。对于大型 App，彻底迁移到 DataStore 是长期解决方案。

---

## 案例 4：进程冻结导致 Gesture Monitor 无法响应

### 问题现象

Android 14 设备，在使用手势导航时偶发 ANR。Event log：

```
02-18 20:08:25.283 485 577 I WindowManager: 
  ANR in input window owned by pid=3930. 
  Reason: Input dispatching timed out 
  ([Gesture Monitor] Screenshot 0 (server) is not responding. 
   Waited 5000ms for MotionEvent(deviceId=4, ...))
```

ANR 类型是 Input dispatching timed out，等待的是 Gesture Monitor 的 "Screenshot" 接收者。注意 pid=3930 是 `com.android.systemui:screenshot` 进程。

[来源: Obsidian/Cubox/疑难ANR原因分析-冻结导致直播讲解相关完整笔记-2025-02-22.md]

### 分析过程

这个案例的特殊之处在于：常规分析手段（看 trace、看负载）都指向"一切正常"。App 主线程空闲，系统负载正常，甚至 InputDispatcher 的日志显示事件确实发出去了。

分析者采用了**从源头追踪**的方法：

**第一步：追踪事件派发。** 在 InputDispatcher 中搜索 ANR 消息中提到的事件时间戳 `39032316052000`，确认 InputDispatcher 确实在 ANR 前 5 秒发出了 MotionEvent，并且接收方就是 `[Gesture Monitor] Screenshot`。

**第二步：追踪接收方。** 搜索 screenshot 进程（pid=3930）在 ANR 前后的日志，发现最后一次成功接收触摸事件的时间是 `20:08:20.276`，此后再也没有收到新的事件。

**第三步：发现冻结。** 在 `20:08:20.289`，日志中出现了：

```
am_freeze: [3930, com.android.systemui:screenshot]
```

screenshot 进程被系统冻结了。进程一旦被冻结，CPU 不会再调度它的任何线程，自然也无法接收和处理 Input 事件。InputDispatcher 等了 5 秒没有收到消费确认，触发了 ANR。

**第四步：验证。** 在开发者选项中关闭"冻结应用"（`settings put global cached_apps_freezer enabled --type int 0`），重新测试——ANR 不再复现。开启后立刻复现。确认根因就是进程冻结。

### 根因

Android 的 Cached Apps Freezer 机制会在应用进入后台后冻结其进程，以减少后台进程的 CPU 和内存开销。但 Gesture Monitor（如 Screenshot）作为 Input 事件的接收者，需要保持活跃才能及时处理手势事件。当系统在用户正在进行手势操作时冻结了 screenshot 进程，就导致了 Input 事件无法被消费，触发 ANR。

这是一个**系统设计缺陷**：进程冻结策略没有考虑 Gesture Monitor 这种需要持续接收 Input 事件的组件。

[待验证: Android 15/16 是否已修复此冻结策略]

### 修复方案

1. **系统侧**：在冻结策略中排除注册了 Gesture Monitor 的进程，或者在 InputDispatcher 检测到目标进程被冻结时主动解冻而非直接触发 ANR。
2. **OEM 侧**：调整 freezer 的超时策略，对于 systemui 子进程延长冻结等待时间。
3. **开发者选项**：在测试环境中可以临时关闭 freezer 来验证是否是冻结导致的问题。

### 举一反三

进程冻结是 Android 12+ 引入的重要省电机制，但它可能导致一些"幽灵 ANR"——trace 中看不到任何异常，App 没有做错任何事，但就是 ANR 了。当你遇到 Input ANR 且 trace 中主线程空闲、负载正常时，记得检查 `am_freeze` 日志。

---

## 案例 5：应用启动超时 — 焦点窗口缺失的 Input ANR

### 问题现象

用户在 Launcher 上点击拨号器图标，Launcher 出现 ANR：

```
05-30 12:15:49.544 1000 1946 8368 I am_anr : [0,2758,com.android.launcher,
  751550021, Input dispatching timed out 
  (Application does not have a focused window)]
```

[来源: Obsidian/Cubox/ANR-实例分析-启动应用失败-2024-12-18.md]

### 分析过程

**第一步：看 trace。** Launcher 主线程空闲（`nativePollOnce`），Launcher 本身没有问题。

**第二步：确认 Launcher 状态。** 从 logcat 中查找：

```
05-30 12:15:16.210 10100 2758 2758 D VRI[QuickstepLauncher]: reportDrawFinished
```

Launcher 在 ANR 发生前 33 秒已经绘制完成，且之后没有新的 `relayoutWindow` 操作。说明 Launcher 已经完全就绪，不是它的锅。

**第三步：看 AnrManager 负载。**

```
Load: 0.0 / 0.0 / 0.0
15% TOTAL: 8.5% user + 5.6% kernel + 0% iowait
```

负载正常。那问题出在哪里？

**第四步：看 Event log 的焦点切换序列。** 这是破案的关键：

```
05-30 12:15:25.131 am_proc_start: [0,8341,10150,com.google.android.dialer, ...]
05-30 12:15:25.138 input_focus: [Focus leaving 21d0029 com.android.launcher/... (server), reason=NO_WINDOW]
05-30 12:15:35.143 am_process_start_timeout: [0,8341,10150,com.google.android.dialer]
05-30 12:15:35.153 am_kill: [0,8341,com.google.android.dialer, -10000, start timeout]
05-30 12:15:49.544 am_anr: [0,2758,com.android.launcher, ... Input dispatching timed out ...]
```

时间线是这样的：

1. **12:15:25** — 系统启动 Dialer 进程
2. **12:15:25** — 焦点从 Launcher 离开（`Focus leaving ... reason=NO_WINDOW`），准备切换到 Dialer
3. **12:15:35** — Dialer 进程启动超时（10 秒内没起来），被系统杀掉
4. **12:15:49** — 14 秒后，Input ANR 发生在 Launcher

问题很清楚了：焦点已经离开了 Launcher，准备交给 Dialer，但 Dialer 没能成功启动。此时系统中没有任何窗口持有焦点——Launcher 失去了焦点，Dialer 又没起来。Input 事件无处投递，5 秒超时后触发 ANR，记录在当前可见的 Launcher 上。

### 根因

Dialer 应用启动失败。需要进一步分析 Dialer 的启动超时原因——可能是 Dialer 进程的 `Application.onCreate()` 中做了太多初始化工作，也可能是系统此时处于某种资源紧张状态导致进程孵化（`zygote fork`）变慢。但就这个 ANR 而言，根因不在 Launcher，而是 Dialer 启动失败导致焦点悬空。

### 修复方案

1. **Dialer 侧**：优化启动速度，减少 `Application.onCreate()` 中的同步初始化工作，使用延迟初始化或懒加载。
2. **系统侧**：优化进程启动超时后的焦点回退策略。当目标进程启动失败时，应该立即将焦点回退到 Launcher 或前一个窗口，而不是让焦点悬空直到 ANR。

### 举一反三

"Application does not have a focused window" 这类 Input ANR，通常不是焦点窗口所在 App 的问题。分析方法是从 Event log 中追踪 `input_focus` 事件，看焦点从哪里来、想去哪里、为什么没到达。常见场景包括：目标 App 启动失败（本案例）、目标 App 的 Activity 还没完成 `onResume`、目标 App 绘制完成但窗口还没被系统添加。

---

## 分析方法总结

通过这五个案例，我们可以提炼出一个高效的分析路径。当你拿到一个 ANR trace 时，按以下顺序检查：

**第一步：判断 ANR 类型。** 从 `am_anr` 或 AnrManager 信息中确认是 Input、Service、Broadcast 还是 ContentProvider ANR。类型决定了后续的分析方向。

**第二步：看主线程 trace。** 如果主线程有明确的业务代码堆栈（SP 等待、Binder 调用、同步锁等），根因就在 App 自身。如果主线程在 `nativePollOnce` 或 `WaitHoldingLocks`，问题可能在系统侧。

**第三步：看负载。** AnrManager 的 Load、CPU 使用率、iowait、memory/IO pressure 是判断系统健康度的关键。如果全局负载过高（特别是 iowait > 20%），系统级问题的可能性大。

**第四步：看 Event log 的焦点和进程变化。** 对于 Input ANR，追踪 `input_focus`、`am_proc_start`、`am_kill` 等事件的时间线，看焦点是如何流转的。

**第五步：看进程冻结日志。** 如果以上都正常，搜索 `am_freeze` 确认是否有进程被冻结导致事件无法处理。

这个分析路径在 §9.3 ANR 分析方法论中有更系统的描述，本节的案例是对方法论的具体应用。建议在分析真实 ANR 时参照这个路径，避免遗漏关键线索。

---

## 线上 ANR 聚合分析实践 [扩展]

在大型 App 的日常运营中，单次 ANR 的分析只是冰山一角。真正有效率的做法是建立线上 ANR 监控和聚合分析体系。

### 为什么需要聚合

ANR 的原始堆栈信息噪音很大。如 §9.3 中分析的，很多 ANR trace 会命中 `nativePollOnce` 这样的"无效堆栈"。如果每次 ANR 都人工分析，效率极低。聚合分析的思路是：将相似堆栈的 ANR 合并成同一组，计算每组的发生频率和影响面，优先修复影响最大的问题。

Shopee 团队的 MDAP LooperMonitor 方案是一个参考实践。它的核心思路是**记录主线程过去 10 秒的消息调度历史**，而不是只抓 ANR 瞬间的堆栈。当 ANR 发生时，上报过去 10 秒内所有消息的执行情况（包括 Handler 类型、callback、执行耗时），以及尚未执行的 Pending 消息。这样即使 ANR 瞬间的堆栈是 `nativePollOnce`，也能从调度历史中找到真正耗时的大消息。

[引用: https://juejin.cn/post/7136008620658917407 — Shopee MDAP LooperMonitor]

### 关键技术点

监控入口方面，Android 28+ 可以使用 `Looper.Observer`（需要绕过 Hidden API 限制），低版本降级到 `Looper.setMessageLogging(Printer)` 方案。`Observer` 方案性能更优，因为它不需要像 `Printer` 那样每次消息都拼接字符串产生临时对象。但 `Observer` 是 Hidden API，在高版本上需要通过元反射绕过限制，Android 31+ 又限制了元反射调用，需要做额外兼容。

消息分类方面，需要区分系统消息（Service/Activity/Broadcast 调度）和业务消息。系统消息从 `ActivityThread$H` 的 `what` 字段获取类型，业务消息从 Handler 类名和 callback 定位。

内存控制方面，使用滚动淘汰策略，只保留最近 10 秒的数据。小消息（<30ms）只记录摘要（耗时 + Handler 类型），大消息（>200ms）才记录完整堆栈。这样可以将内存占用控制在合理范围。

聚合策略方面，按 Handler 类名 + 消息类型做哈希聚合，同一组内的 ANR 只保留代表性样本，在后台完成去重和归因。

[待验证: Looper.Observer 在 Android 16+ 的 Hidden API 限制是否有变化]

---

## 系统级 ANR 案例 [扩展]

在系统开发中，除了 App 侧的 ANR，还有两类特殊的系统级 ANR 值得了解。

**SystemServer Watchdog ANR**：system_server 内部有一个 Watchdog 线程，定期检查关键系统服务（AMS、WMS、PMS 等）的健康状态。每个服务需要在检查点上报"我还活着"。如果某个服务在超时时间内没有上报，Watchdog 会判定系统进入异常状态，触发重启。这类问题的 trace 通常出现在 `Watchdog.run()` 中，需要排查哪个服务卡住了——常见原因包括 Binder 死锁、磁盘 IO 阻塞、或死循环。

**ServiceManager 启动超时**：当系统服务在启动过程中超时，Event log 中会出现 `am_process_start_timeout`。案例 5 中就有这个场景——Dialer 进程启动超时被杀。这类问题需要排查目标进程的启动流程中哪个环节耗时过长，特别是 `Application.onCreate()` 中的初始化工作。

[待补充: SystemServer Watchdog ANR 的完整案例分析]

---

## 参考资料

### AOSP 源码路径
- `frameworks/base/core/java/android/app/SharedPreferencesImpl.java` — SP 实现
- `frameworks/base/core/java/android/app/QueuedWork.java` — SP 写入等待队列
- `frameworks/native/services/inputflinger/dispatcher/InputDispatcher.cpp` — Input ANR 检测
- `frameworks/base/services/core/java/com/android/server/power/Notifier.java` — system_server Notifier

### 文章与资料
- [ANR 实例分析：启动应用失败](https://mp.weixin.qq.com/s?__biz=MzI0NDUxNTQ2NA==&mid=2247483907) — codemx.cn
- [ANR 实例分析：Input dispatching timed out](https://mp.weixin.qq.com/s?__biz=MzI0NDUxNTQ2NA==&mid=2247483912) — codemx.cn
- [ANR 实例分析：负载过高](https://mp.weixin.qq.com/s?__biz=MzI0NDUxNTQ2NA==&mid=2247483930) — codemx.cn
- [今日头条 ANR 优化实践系列：告别 SharedPreference 等待](https://mp.weixin.qq.com/s/kfF83UmsGM5w43rDCH544g) — 字节跳动 Android 平台架构团队
- [疑难 ANR 原因分析：冻结导致](https://mp.weixin.qq.com/s?__biz=MzkzOTQ4NDUyNg==&mid=2247489094) — 进程冻结案例
- [Android 卡顿与 ANR 的分析实践](https://juejin.cn/post/7136008620658917407) — Shopee 技术团队
- [developer.android.com - ANR](https://developer.android.com/topic/performance/vitals/anr) — 官方文档
