---
title: "特殊场景的 ANR"
chapter: "9.4"
section: "9.4"
polish_count: 1
polish_date: "2026-04-08"
polish_by: "task2b-polish"
drafted_date: "2026-04-02"
drafted_by: "openclaw-task2a"
applicable_versions: "Android 8.0 (API 26) - Android 16 (API 36)"
last_verified: "2026-04-27"
last_verified_against: "AOSP android-15.0.0_r1 ART heap/gc_cause anchors, SQLite WAL docs, Android 14-17 FGS timeout research"
confidence: medium
sources:
  - type: aosp
    path: "frameworks/base/core/java/android/app/ActivityThread.java"
  - type: aosp
    path: "frameworks/base/core/java/android/app/SharedPreferencesImpl.java"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/am/ActivityManagerService.java"
  - type: aosp
    path: "frameworks/base/core/java/android/app/IActivityManager.aidl"
  - type: web
    url: "https://androidperformance.com/"
    note: "高爷原创 ANR 分析系列"
tags: ['anr', 'sharedpreferences', 'contentprovider', 'binder', 'broadcast', 'io-blocking', 'system-load']
related_chapters: ['9.1', '9.2', '9.3', '1.4', '4.3', '4.4', '6.3']
task6_state: revisiting
task6_result: pass-light-edit
task2b_result: fixed
last_task2b_at: "2026-05-22T15:21:00+08:00"
reviewed_by: openclaw-task6
reviewed_date: "2026-05-22"
rework_date: "2026-04-16"
rework_by: "task2b-rework"
repaired_date: "2026-04-27"
repaired_by: "openclaw-task2b"
status: ready-for-review
pipeline_stage: task6_pending
task9_state: pending
task9_result: needs-rework
task9_reviewed_by: openclaw-task9
task9_reviewed_date: "2026-05-22"
last_task9_at: "2026-05-22T11:40:27+08:00"
auto_promoted_by: "openclaw-task6"
auto_promoted_date: "2026-05-04"
task2b_state: fixed
p0: 0
p1: 1
p2: 1
updated_by: "openclaw-task6"
updated_date: "2026-05-22"
review_notes: "2026-05-22 task2b rework: P0×2 IActivityManager.aidl路径+ModernBroadcastQueue线程模型；P1×2 Freezer广播口径收窄+16KB SQLite条件化。2026-05-22 Task6 re-review: pass-light-edit。L1/L2 小修 2 处（ContentProvider 顺序句式、占位提示改为 Trace 观察点）。既有 Task9 16KB SQLite P1 queue pending，保持 task2b_pending。"
rework_round_2: "2026-05-04"
last_task9_audit: "2026-05-22"
task9_audit_notes: "2026-05-22 idle audit: P0×2 / P1×2; see logs/deep-review/2026-05-22-08-audit.md."
last_task6_audit: "2026-05-22"
task6_audit_notes: "2026-05-22 idle audit: L1 wording fixes; status changed from finalized to ready-for-review because Task9 queue has pending P0/P1 issues."
auto_promotion_revoked_by: "openclaw-task6"
auto_promotion_revoked_date: "2026-05-22"
auto_promotion_revoked_reason: "Task9 audit queue pending; finalized status was inconsistent."
last_task9_review_log: "logs/deep-review/2026-05-22-11-deep-review.md"
task9_review_notes: "2026-05-22 Task9 re-review: needs-rework。P1 1：16KB Page Size / SQLite WAL 段仍把 Android 16 旗舰、kernel page size、SQLite page_size、物理写放大 4 倍与固定 wal_autocheckpoint=250 绑定，需条件化。"
last_task6_at: "2026-05-22T12:13:00+08:00"
last_task6_review_log: "logs/review/2026-05-22-12-review.md"
---

# 特殊场景的 ANR

> **阅读本章前，你需要了解：** §9.1 ANR 的设计思想（ANR 的超时机制与触发流程）、§9.2 ANR 类型与触发条件。
> **阅读本章后，你可以去看：** §9.5 案例集（本章讨论的场景在真实 Trace 中的完整分析过程）。

## 为什么要了解"特殊场景的 ANR"

在 §9.2 中，我们梳理了 ANR 的标准触发条件——Input 事件 5 秒超时、Service 20 秒超时。Broadcast 的窗口要再细分一步：Android 13 及以下通常按前台 10 秒、后台 60 秒计时；Android 14 及以上如果接收进程处于 CPU starvation，`FLAG_RECEIVER_FOREGROUND` 广播会放宽到 10-20 秒，后台广播会放宽到 60-120 秒。把这些窗口看成固定常量，后面的 trace 很容易读偏。

但在实际分析工作中，有一类 ANR 让人头疼：**traces 文件里主线程的堆栈看起来"没干什么坏事"**——可能只是在等一个 Binder 回复、在等一个 SharedPreferences 写入完成、或者干脆处在 RUNNABLE 状态但 CPU 已经被其他进程占满。这类 ANR 的根因不在 App 代码本身，而在系统层面的资源竞争、跨进程依赖或者一些容易被忽视的框架行为。

我们把这些情况称为"特殊场景的 ANR"。它们的共同特点：

第一，**不容易从 App 代码直接定位**。在 traces 里看到主线程在等 Binder 调用返回，但问题可能发生在对端进程。

第二，**往往涉及多个因素叠加**。一个 SharedPreferences apply() 引起的 ANR，背后可能是磁盘 I/O 慢、系统负载高、加上 Activity 切换时机三者的综合作用。

第三，**在 Trace 中的表现比较隐蔽**。需要知道该看哪里——CPU 全局利用率、D 状态线程、Binder 调用的对端。

[已验证: 来源见 综合分析 AOSP 源码与 Perfetto 实践经验] [已验证: AOSP android-14.0.0_r1]

## 系统负载高导致的 ANR

### 现象：主线程看起来没做错什么，但还是 ANR 了

Bug report 里的 ANR traces 显示主线程要么在 `nativePollOnce()`（idle 等待），要么在做很轻量的操作，但 input event 还是超时了。这时候查看 CPU 使用率，会发现整机负载极高。

这种情况的本质是：**App 本身没做错什么，但它被系统环境拖累了。** 当 CPU 饱和时，即使主线程只需要几毫秒就能处理完 input event，调度器也可能等了几秒才把 CPU 时间片分给它。

### CPU 饱和：调度器来不及调度

在正常情况下，Android 的主线程优先级（`THREAD_PRIORITY_FOREGROUND`，-2）足以让调度器在几毫秒内把 CPU 分配给它。但当整机 CPU 饱和时，情况就不同了。

CPU 饱和通常由以下因素造成：后台有大量进程同时运行（比如刚开机、批量安装应用）、某个进程的 worker 线程池全部跑满、系统服务的 Binder 线程池被打满导致请求排队。

在 Perfetto 中，通过 CPU Scheduling track 可以直接看到这个状态：所有 CPU 核心都被占满，主线程长时间处于 Runnable 状态（青色条）但无法被调度执行。

### I/O 阻塞：D 状态与磁盘带宽竞争

在 Perfetto 的线程状态 track 中，会看到线程进入 D 状态（Uninterruptible Sleep），通常标注为 `D (disk sleep)` 或 `D (iowait)`。线程在等待磁盘 I/O 完成，而且这个等待不可中断。

当整机 I/O 压力大时，以下看似无害的操作都可能变成 ANR 的导火索：主线程读取一个 SharedPreferences 文件；主线程通过 `open()` 打开一个文件；ContentResolver 执行一次 `query()`；甚至主线程执行一次 Binder 调用，而对端进程正好在做 I/O 无法响应。


### 进程冻结导致的 ANR：Android 16+ 的诊断简化

[来源: External Review — Android 16+ Freezer 豁免逻辑]

在 Android 15 及以下，进程被系统冻结（Cached Apps Freezer）后，如果在该进程被冻结期间收到了 input event 或 broadcast，系统会等待进程解冻后再处理。解冻本身需要时间（从冻结到可调度通常需要几百毫秒到数秒），如果这个等待叠加到 ANR 超时窗口内，就会出现"应用什么都没做但还是 ANR 了"的情况。

在 Perfetto 中，这类问题的特征是主线程在 ANR 时间窗内有 `__refrigerator` 或 `D (frozen)` 状态段，说明进程当时被系统冻结了。

**Android 16+ 的变化**：Android 16 的 `BroadcastQueueImpl` 在调度 receiver 前会调用 `unfreezeTemporarily(... START_RECEIVER)` 临时解冻目标进程，广播 ANR 计时使用 `BroadcastAnrTimer`（`AnrTimer.Args` 配置 `extend(true)` 和 `freeze(true)`），`extend(true)` 表示可按 CPU delay 做一次软超时延长。广播/回调调度对 freezer 更敏感——投递前先解冻，并可基于 CPU starvation 延长超时。排查广播 ANR 时仍要看 freezer/unfreeze 事件、binder callback 是否在冻结期积压、以及具体 ANR 类型。不要把这个结论扩展到 Input、Service、ContentProvider 等所有 ANR 场景——那些路径的 freezer 处理逻辑不同，需要分别确认。

### 在 Perfetto 中怎么分析

先看 CPU 概览 track：确认在 ANR 发生的时间段，所有 CPU 核心的占用率是否接近 100%。

然后看主线程的线程状态 track。如果主线程长时间是 Runnable（青色）而不是 Running（蓝色），说明它"想跑但跑不了"——CPU 被其他线程占了。

如果主线程长时间是 `D (iowait)`（深红色），说明它在等磁盘。需要去看是哪个进程在做密集 I/O。

再检查 ANR 发生时刻的 `loadavg`。如果 1 分钟平均负载远超 CPU 核心数（比如 8 核设备上负载 > 16），说明整机处于过载状态。

## Broadcast 风暴导致的连锁 ANR

### 什么是 Broadcast 风暴

Android 的广播机制中，AMS 是**串行分发**有序广播的——必须等上一个接收者的 `onReceive()` 返回后，才能发给下一个。广播风暴发生在大批量广播在短时间内同时发出的情况。

### 连锁 ANR 的形成过程

AOSP 会对每个 receiver 单独计时，不存在“前面排队太久，后面自动继承超时”的累计模型。`FLAG_RECEIVER_FOREGROUND` 广播在 Android 13 及以下通常按 10 秒算，后台广播按 60 秒算；Android 14 及以上如果进程明显拿不到 CPU，这两个窗口会放宽到 10-20 秒和 60-120 秒。判断边界别只看业务语义，直接看 ANR subject 里的 `flg=` 字段；带 `0x10000000` 就是 `FLAG_RECEIVER_FOREGROUND`。

广播风暴仍然会打出一串 ANR，因为 system_server 串行分发有序广播时，大量 receiver 会一起争抢 CPU、I/O 和 Binder 线程池。某个 receiver 如果在 `onReceive()` 里做数据库写入、网络等待或跨进程同步调用，会把后面的分发起点整体往后推；等这些 App 拿到执行机会时，各自的超时窗口已经被系统负载吃掉了一大截。

因此，这里的因果链要写成“每个 receiver 仍然按自己的窗口超时，但广播风暴把整机拖慢了”，不要写成“广播队列自己累计超时”。

### Trace 特征

在 Perfetto 中，广播风暴的典型表现是：system_server 的 Binder 线程中看到大量连续的 `broadcastIntent` 调用；多个 App 进程几乎同时出现主线程被阻塞；ANR traces 中多个 App 的主线程都停在 `ActivityThread.handleReceiver()`。

[已验证: 来源见 AOSP ActivityManagerService 广播分发机制] [已验证: AOSP android-14.0.0_r1]


### 异步广播的优先级反转陷阱

[来源: External Review — Modern Broadcast Queue 调度陷阱]

Android 14+ 引入了 Modern Broadcast Queue（`BroadcastQueueModernImpl` + `BroadcastProcessQueue`，Android 16 侧为 `BroadcastQueueImpl`），将广播按目标进程组织成队列，解决了旧模型中串行分发导致的"队头阻塞"问题。这一改动发生在 system_server 侧——system_server 按进程维度排队与调度广播投递，不再让同一个进程的多个 receiver 互相阻塞。

App 侧 `onReceive()` 的线程模型没有变。Manifest 注册的 receiver 仍由 `IApplicationThread.scheduleReceiver()` 投递到 `ActivityThread.H.RECEIVER`，再在 `ActivityThread.handleReceiver()` 中直接调用 `receiver.onReceive(...)`——跑在主线程上。动态注册 receiver 默认也是注册线程或主线程 Handler，除非调用方显式传入其他 Handler。framework 没有把 `onReceive()` 投递到进程内部的线程池。

如果 trace 里看到 BG Thread 池的 Runnable 执行了广播相关逻辑，应归因到 App 自己的 `goAsync()` / executor / SDK 内部线程池，而不是 framework 的 ModernBroadcastQueue。

排查 Modern Broadcast Queue 相关问题时，Perfetto 中要看两个层面：system_server 侧按进程排队的投递节奏（`BroadcastQueueModernImpl` / `BroadcastQueueImpl` 的调度 slice），以及目标 App 主线程 `handleReceiver()` 的执行耗时。整机负载高时，ANR 的根因可能是主线程被其他工作占满，也可能是 system_server 调度延迟导致投递本身推后——两种情况在 trace 里表现不同。

## ContentProvider 冷启动导致的 ANR

### ContentProvider 的初始化时序陷阱

ContentProvider 有一个容易被忽视的特性：**它在 `Application.onCreate()` 之前就被初始化了。** 当系统启动一个 App 进程时，`ActivityThread.handleBindApplication()` 的执行顺序是：创建 Application 对象 → 逐一安装所有声明的 ContentProvider → 调用每个 ContentProvider 的 `onCreate()` → 才调用 `Application.onCreate()`。

如果某个 ContentProvider 的 `onCreate()` 做了耗时操作（数据库初始化、读取大文件、网络请求），它会直接拉长整个 App 的冷启动时间，而这个时间是被算在 ANR 超时里的。

更隐蔽的问题来自第三方 SDK。很多 SDK 通过声明 ContentProvider 来实现自动初始化。如果有五六个 SDK 都这样做，每个在 `onCreate()` 里花几百毫秒，累计下来可能就是两三秒。

### 跨进程 ContentProvider 查询的超时

在 Perfetto 中，重点看调用方的长段 WAITING 是否与对端进程的 `ActivityThread.handleBindApplication()` / Provider 初始化时间对齐。

另一个常见场景是 App A 通过 ContentResolver 查询 App B 的 ContentProvider。如果 App B 的进程还没有启动（冷启动），系统需要先启动 App B 的进程，初始化它的 ContentProvider，然后才能响应查询。这个冷启动的全过程对 App A 来说就是一个 Binder 同步调用等待。

### Jetpack App Startup 的解决方案

Google 推出了 Jetpack App Startup 库。核心思路是用一个 ContentProvider 统一管理所有 SDK 的初始化，减少 ContentProvider 数量，同时支持按依赖顺序和懒加载初始化。（关于 ContentProvider 初始化的完整时序分析，参见 §1.10。）

[已验证: 来源见 AOSP ActivityThread.handleBindApplication()] [已验证: AOSP android-14.0.0_r1]

## SharedPreferences apply() 导致的 ANR

### apply() 的危险点在组件边界等待

`SharedPreferencesImpl.apply()` 会先把修改提交到内存，再通过 `enqueueDiskWrite()` 把 XML 写盘放进 `QueuedWork`。单看调用点，它比 `commit()` 更接近异步接口。

问题出在另一头：框架会在 BroadcastReceiver、Service，以及部分组件收尾路径上调用 `QueuedWork.waitToFinish()`，要求进程里尚未完成的 `QueuedWork` 先处理完。旧应用的 Activity pause 也会走这条路径，但 Android 8-16 的日常排查里，更常见的是 receiver 和 service 边界被慢刷盘拖住。

### 从 apply() 到阻塞的过程

一个页面或 receiver 里频繁调用了 `apply()` 保存状态。修改先进入内存，磁盘写入随后排进 `QueuedWork`。如果这时整机 I/O 压力很高，`writeToFile()` 里的 XML 落盘和 `fsync()` 会明显变慢。

等到组件离开当前边界，框架调用 `QueuedWork.waitToFinish()`，主线程就会被迫等这些未完成的写盘收尾。这里看到的是组件边界上的等待，耗时通常落在尚未完成的 XML 落盘和 `fsync()`。

### 源码里注册的是什么

```java
// frameworks/base/core/java/android/app/SharedPreferencesImpl.java
// @ AOSP android-14.0.0_r1
@Override
public void apply() {
    final MemoryCommitResult mcr = commitToMemory();
    final Runnable awaitCommit = new Runnable() {
        @Override
        public void run() {
            try {
                mcr.writtenToDiskLatch.await();
            } catch (InterruptedException ignored) {
            }
        }
    };

    QueuedWork.addFinisher(awaitCommit);

    Runnable postWriteRunnable = new Runnable() {
        @Override
        public void run() {
            awaitCommit.run();
            QueuedWork.removeFinisher(awaitCommit);
        }
    };

    SharedPreferencesImpl.this.enqueueDiskWrite(mcr, postWriteRunnable);
}
```

这里塞进 `sFinishers` 的是 `awaitCommit()`。`QueuedWork.waitToFinish()` 在 apply 场景里跑到的 `toFinish.run()`，对应的是等待 `writtenToDiskLatch`；`writeToFile()` 则在 `enqueueDiskWrite()` 安排的 `writeToDiskRunnable` 里执行。

`QueuedWork.waitToFinish()` 还会先尽快清空 pending work，所以 trace 里经常会同时看到等待和慢 I/O 叠在一起。分析时把视线放在慢 `fsync()`、存储拥塞、批量 `apply()` 调用即可；如果把 `sFinishers` 写成“主线程亲自逐条刷盘队列”，整段解释就会偏掉。

### 解决方案

最佳方案是迁移到 Jetpack DataStore（Preferences DataStore），它把持久化调度和类型约束放到了更清晰的异步模型里。

短期缓解方案：减少 `apply()` 调用频率，把多次修改合并成一次；对必须立刻落盘的状态单独安排时机；避开广播、服务收尾和其他容易触发 `QueuedWork.waitToFinish()` 的边界。

[已验证: 来源见 AOSP SharedPreferencesImpl.java + QueuedWork.java + ActivityThread.java] [已验证: AOSP android-14.0.0_r1]

## 多进程场景的 Binder 死锁 ANR

### Binder 死锁的经典模型

进程 A 的主线程持有一个锁 L1，然后通过 Binder 同步调用进程 B；进程 B 的 Binder 线程在处理这个请求时，需要通过 Binder 同步调用回进程 A；但进程 A 的主线程正阻塞在等进程 B 的返回，无法响应进程 B 的 Binder 调用。这就形成了死锁。

### Binder 线程池耗尽

普通进程通过 libbinder 的 `ProcessState` 初始化 Binder 线程池时，默认上限为 **15** 个 Binder worker 线程（`DEFAULT_MAX_BINDER_THREADS`，见 `frameworks/native/libs/binder/ProcessState.cpp`，Android 14/15/16 均为 15）。system_server 等系统进程会通过 `ProcessState::setThreadPoolMaxThreadCount()` 显式调高。排查时看接近 15 个 Binder worker 被同步调用占满的情况。

这个问题的触发条件比严格的死锁更容易满足：多个组件同时发起 Binder 调用 → 对端响应慢 → Binder 线程逐渐被占满 → 形成活锁。

### 在 ANR traces 中怎么识别

主线程堆栈显示 `BinderProxy.transact(Native Method)`，说明在等待 Binder 同步调用返回。然后去看对端进程的 traces，如果对端的 Binder 线程也在等另一个 Binder 调用返回，形成环形依赖，就确认是死锁。

### 预防和解决方案

核心原则：**永远不要在持锁状态下发起同步 Binder 调用。** 在实际项目中，如果必须在处理 Binder 请求时再发起另一个 Binder 调用，优先使用 `oneway` 接口（异步，不等待返回）。同时需要监控 Binder 线程池的使用率——如果经常出现接近 15 个线程全部占满的情况，说明调用频率或对端响应时间有问题，需要从这两个方向排查。

[已验证: 来源见 AOSP Binder 驱动机制] [已验证: AOSP android-14.0.0_r1]

## 低内存触发频繁 GC 导致的 ANR

### GC 不是免费的：STW 停顿的累积效应

ART 的垃圾回收器从 Android 8.0 开始采用 Concurrent Copying（CC）GC，大部分标记和拷贝工作与应用线程并发执行。但"并发"不等于"零暂停"——CC GC 在处理线程 root（栈引用、JNI 全局引用等）时仍然需要短暂地暂停所有线程（Stop-The-World）。

在正常情况下，年轻代 GC（Young Generation Collection）的 STW 暂停时间在 1-3ms 之间（实测平均约 1.83ms），对 60fps 的帧渲染周期（16.67ms）影响可以忽略。但当 Java 堆使用率持续攀升时，情况会迅速恶化。

ART 的 GC 触发不能按固定 50% 线理解。`TargetHeapUtilization` 是 GC 后计算 heap growth target / target footprint 的输入，影响下一次 GC 的触发距离；触发还会看 `concurrent_start_bytes_`、`target_footprint_` / `growth_limit_`、本次分配是否触顶、native allocation 压力、显式 `System.gc()`、后台 trim 等 `GcCause`。在 trace 里判断 GC 风暴，要同时看 GC cause、heap size、allocated bytes、concurrent GC 间隔和 STW slice，不能只看 heap 利用率。[待验证: Android 17 CMC GC 是否调整了默认触发阈值]

源码锚点放在三处：

- `art/runtime/gc/heap.cc`：`Heap::GrowForUtilization()` 更新 GC 后的目标占用、`target_footprint_` 和 `concurrent_start_bytes_`。
- `art/runtime/gc/heap.cc`：分配慢路径会根据 footprint / growth limit 和 concurrent start 阈值请求 concurrent GC 或 for-alloc GC。
- `art/runtime/gc/gc_cause.h`：`kGcCauseForAlloc`、`kGcCauseBackground`、`kGcCauseExplicit`、`kGcCauseNativeAlloc` 等原因会影响 pause 形态和排查方向。

下面是概念伪代码，用来说明判断顺序，不是 AOSP 函数体摘录：

```text
if allocated_bytes >= concurrent_start_bytes_:
    request concurrent GC, cause = background / collector transition 等

if allocation fails within current target_footprint_ or growth_limit_:
    run for-alloc GC, cause = kGcCauseForAlloc

after GC:
    GrowForUtilization(...) updates target_footprint_ and concurrent_start_bytes_
```

Concurrent Copying 仍然包含短暂停顿，例如暂停线程处理 roots、处理 dirty objects 或完成收尾。正常情况下这些 STW slice 很短；当内存抖动、native allocation 压力或系统内存回收叠加时，GC 频率和调度延迟一起上升，主线程就可能在 ANR 窗口里拿不到足够执行时间。

### 从"偶尔 GC"到"GC 风暴"的临界点

假设一个 App 在正常状态下每秒触发 1-2 次 Young GC，每次 STW 1-3ms，一秒内 GC 总暂停约 2-6ms——主线程还有 10ms+ 的 CPU 时间。但当这个 App 存在内存抖动（Memory Churn）——比如在 `onDraw()` 中频繁创建临时对象——堆的分配速度会远超回收速度，ART 被迫从 Young GC 升级到 Partial GC 甚至 Full GC。

此时会出现一个恶性循环：GC 越频繁，每次回收的对象越少（因为大部分是短期对象还没到回收时机），堆使用率居高不下，触发更频繁的 GC。在极端情况下，GC 频率可以飙升到每秒几十次，累积 STW 时间达到数百毫秒。

更严重的情况发生在系统内存不足时。当 LMK（Low Memory Killer）开始杀后台进程（参见 §4.4），被杀进程释放的内存页可能需要通过磁盘 I/O 重新分配给存活进程。这个过程中，kswapd 内核线程会加大回收力度，进一步增加 I/O 压力和 CPU 占用。此时即使主线程没有被 GC 直接暂停，调度器也可能因为 CPU 被 kswapd 和其他系统进程占满而无法及时调度主线程。

### 与 §4.3 的关系

这一节讨论的 GC 机制在 §4.3（ART 虚拟机内存管理）中有完整的原理分析。这里聚焦的是 GC 在极端情况下如何成为 ANR 的间接推手——问题本质不在 GC 本身，而在于 App 的内存抖动或系统内存压力导致 GC 频率失控。

[已验证: 来源见 ART GC 机制分析 + AOSP art/runtime/gc/heap.cc] [已验证: AOSP android-14.0.0_r1 + android-15.0.0_r1] [待验证: Android 17 CMC GC 在极端内存压力下的暂停时间是否有进一步优化]

## 前台服务的启动超时与后台启动限制

### 两条路径不要写混

`startForegroundService()` 之后迟迟不调用 `startForeground()`，走的是 `RemoteServiceException$ForegroundServiceDidNotStartInTimeException` 这条“已启动但没有及时晋升前台”的路径。Android 12 之后在后台直接启动前台服务被拒绝，走的是 `ForegroundServiceStartNotAllowedException` 这条“当前时机不允许启动”的路径。两者都会出现在 logcat 里，但语义完全不同。

| 版本 / 场景 | 规则 | 常见表现 |
|:---|:---|:---|
| Android 8 | `startForegroundService()` 后宽限期 5 秒（`SERVICE_START_FOREGROUND_TIMEOUT = 5*1000`，见 `ActiveServices.java` android-8.1.0_r81） | `RemoteServiceException` / 服务启动超时 |
| Android 9-13 已启动未晋升 | 宽限期提升到 10 秒（`SERVICE_START_FOREGROUND_TIMEOUT = 10*1000`，从 android-9.0.0_r61 起）；Android 12+ 的后台启动限制不改变这条“已启动但未及时前台化”路径 | `ForegroundServiceDidNotStartInTimeException` |
| Android 12+ 宽限期乘数 | Android 12 起 `SERVICE_START_FOREGROUND_TIMEOUT` 乘以 `Build.HW_TIMEOUT_MULTIPLIER`，实际宽限期 = `10 * HW_TIMEOUT_MULTIPLIER` 秒 | 同上，部分硬件平台宽限期更长 |
| Android 12+ 后台启动限制 | 后台启动前台服务必须满足豁免条件，入口处直接判定 | `ForegroundServiceStartNotAllowedException` |
| Android 14 shortService | `foregroundServiceType="shortService"` 有独立短超时；超时后回调 `Service.onTimeout()`，服务未及时停止会进入异常或 ANR 路径；源码看 `ActiveServices` 与 `ServiceRecord.ShortFgsInfo` | `Service.onTimeout()`、shortService timeout ANR |
| Android 15 dataSync / mediaProcessing | `dataSync`、`mediaProcessing` 属于 time-limited FGS 类型，公开资料常按 6h / 24h 配额讨论；超时后先给 `Service.onTimeout()` 收尾窗口 | `Service.onTimeout()`、超时后的内部 exception / ANR 判定 |
| Android 16 / 17 后续演进 | time-limited FGS 的配额、迟到 ANR 和 system_server 归因细节继续演进；核验时看 `ActiveServices`、`AnrTimer`、`ServiceRecord` | 同一个 logcat 关键字背后可能是不同版本规则 |

### 已启动，但没有及时晋升前台

这一路最常见的触发方式是：`onCreate()` 或 `onStartCommand()` 里先做数据库查询、文件 I/O、远端请求，再去调 `ServiceCompat.startForeground()`。服务已经起来了，但前台通知迟迟没挂上去，系统就会按“did not start in time”处理。

排查时先看 logcat。若出现 `Context.startForegroundService() did not then call Service.startForeground()` 或 `ForegroundServiceDidNotStartInTimeException`，就该把问题定性为“晋升前台太晚”，不要再去搜 `ForegroundServiceStartNotAllowedException`。

在 Perfetto 里，这类问题通常表现为 Service 初始化开始后，主线程还卡在 `Application` 初始化、Provider 初始化或某段同步 I/O 上，前台通知对应的 `notify()` 没有在宽限期内出现。

### Android 12+ 后台启动被拒绝

`ForegroundServiceStartNotAllowedException` 讲的是另一件事：App 已经退到后台，而且当前调用点不满足豁免条件，系统从入口处就不允许启动这个前台服务。这里没有“5 秒内补一个 `startForeground()` 就能救回来”的补救空间，因为服务压根不该从这个时机启动。

### 预防方案

把 `ServiceCompat.startForeground()` 放到 `onCreate()` 或 `onStartCommand()` 的最前面，通知先挂上，再做任何耗时工作。若业务发生在后台，先确认自己是否满足 Android 12+ 的前台服务豁免；若日志里出现 `short service` 或 `Service.onTimeout()`，就转去看 Android 14+ 的类型化前台服务超时规则，不要和启动宽限期混成一类问题。

## 文件锁竞争导致的 ANR

### SQLite WAL：单 writer、多 reader，不套 rollback journal 五态锁

Android 上绝大多数数据库操作（包括通过 Room、ContentProvider 间接使用）最终都落在 SQLite 上。WAL（Write-Ahead Logging）的基本设计是：写事务先追加到 `.db-wal`，checkpoint 再把 WAL 内容合并回主数据库文件。读事务通过 WAL-index 选择自己的 end mark，因此一个 writer 和多个 readers 通常可以并发存在。

这里要把两个模型分开。rollback journal 文档里的 `UNLOCKED` / `SHARED` / `RESERVED` / `PENDING` / `EXCLUSIVE` 是五态锁模型；WAL 的并发主要靠 `.db-shm` WAL-index 里的 read locks、write lock、checkpoint lock 和 recovery lock 协调。WAL 仍然只有一个 writer，checkpoint 也可能被长读事务挡住；WAL 文件持续变大后，后续读写和 checkpoint 都会变慢。

Android 还要区分 compatibility WAL 与 full WAL。Android 9+ framework 引入 compatibility WAL 以兼容旧行为，Room / SupportSQLiteOpenHelper 常见配置会显式启用 WAL。排查时别只看系统版本，还要看 `SQLiteOpenHelper#setWriteAheadLoggingEnabled()`、Room builder 配置、数据库打开日志和实际的 `journal_mode`。

### 锁竞争导致 ANR 的典型场景

常见场景是同一 App 的多个进程访问同一个数据库文件。主进程的 ContentProvider 在主线程上执行 `query()`；后台进程持有长写事务，WAL 文件持续增长，checkpoint 又被某个长读事务挡住。此时主线程可能卡在连接池等待、写事务结束、checkpoint 或文件系统 I/O 上。ANR 根因不一定是“读被写直接挡住”，也可能是 WAL 积压、连接池耗尽和 checkpoint 放大了等待时间。

Perfetto 中的表现要分两类看：如果主线程在 `SQLiteConnectionPool`、Java 锁或 native mutex 上等待，常见状态是 WAITING / futex；如果卡在 `fsync()`、`fcntl()`、checkpoint 或底层 I/O，才更容易看到 D 状态。只用一个“文件锁”标签归因，很容易漏掉连接池和 checkpoint。


### 16KB Page Size 下的数据库 I/O 变化

[来源: External Review — Android 16KB 物理分页对 SQLite 的影响]

Android 15+ 设备开始使用 16KB kernel page size，Google Play 从 2025-11-01 起要求面向 Android 15+ 的新应用和更新兼容 16KB page sizes。kernel page size 的变化可能影响 SQLite 的物理 I/O 行为，但影响程度取决于多个因素的实际配置，不能简单断言为固定倍数的写放大。

**影响链条需要实测确认**：kernel page size、filesystem block size、SQLite `PRAGMA page_size`、Room/SQLite 版本和 WAL 文件大小，这些因素共同决定 checkpoint 的实际 I/O 开销。排查时先确认设备的 kernel page size（`adb shell getconf PAGESIZE` 或 `/proc/sys/vm/page_size`），再读取数据库的 `PRAGMA page_size` 和 `PRAGMA wal_autocheckpoint`。

当 kernel page size 和 filesystem block size 都切到 16KB，且 SQLite database page size 也是 16KB 时，每个脏页的物理写入从 4KB 变为 16KB，checkpoint 的单次 I/O 开销可能相应增大。但这不是“所有 16KB 设备上的 SQLite 都写放大 4 倍”——database page size 由数据库创建时的参数决定，很多现有数据库的 `PRAGMA page_size` 仍然是 1024 或 4096。

**排查步骤**：
1. 确认设备 kernel page size：`adb shell getconf PAGESIZE`
2. 确认数据库 page size：`PRAGMA page_size`
3. 确认当前 autocheckpoint 阈值：`PRAGMA wal_autocheckpoint`
4. 监控 WAL 文件大小和 checkpoint 耗时
5. 检查 SQLite busy / locked 日志，确认是否存在锁竞争叠加

**checkpoint 调参建议**：只有确认 checkpoint 耗时在实际 workload 下成为瓶颈后，再考虑调低 `wal_autocheckpoint`。具体值取决于业务写入模式、WAL 增长速率和可接受的 checkpoint 停顿时长，不建议固定为某个通用值（如 250）。默认 1000 页在多数场景下工作正常；调低后 checkpoint 更频繁但每次更轻量，反过来也意味着更频繁的写锁竞争机会。

### 源码锚点与防御手段

```java
// frameworks/base/core/java/android/database/sqlite/SQLiteDatabase.java
// @ AOSP android-14.0.0_r1
// beginTransaction() 默认使用 TRANSACTION_MODE_EXCLUSIVE
public void beginTransaction() {
    getThreadSession().beginTransaction(
        SQLiteSession.TRANSACTION_MODE_EXCLUSIVE, ...
    );
}

// beginTransactionNonExclusive() 使用 TRANSACTION_MODE_IMMEDIATE
public void beginTransactionNonExclusive() {
    getThreadSession().beginTransaction(
        SQLiteSession.TRANSACTION_MODE_IMMEDIATE, ...
    );
}
```

这段代码只能说明 Android framework 层事务模式的入口，不能拿来替代 SQLite WAL 锁模型。实践里更稳的策略是：主线程不执行数据库写事务；大事务拆小；Room 使用异步 DAO；跨进程访问通过 ContentProvider 统一调度；批量写入场景评估 `beginTransactionNonExclusive()` 和 `yieldIfContendedSafely()`，并把 checkpoint 时机放到后台窗口。

多进程共用数据库时，还要监控 WAL 文件大小、checkpoint 耗时、SQLite busy / locked 次数、连接池等待时间。只有把这些信号放到同一个 ANR 时间窗里检查，才能区分“业务主线程误用数据库”和“后台写入 / checkpoint 把系统拖慢”。

[已验证: 来源见 AOSP SQLiteDatabase.java / SQLiteConnectionPool.java + SQLite WAL 文档] [已验证: AOSP android-14.0.0_r1 + SQLite 官方文档 wal.html / fileformat.html#walformat]

## 在 Perfetto / 工具中的表现

### 系统负载型 ANR

CPU 概览 track 显示所有核心接近满载。主线程出现大段 Runnable（青色）状态。如果主线程有持续的 D 状态段，而且在同一时间段系统 I/O 压力很大，就是 I/O 阻塞导致的。

### SharedPreferences apply() ANR

主线程堆栈如果落在 `QueuedWork.waitToFinish()`，再叠看 `SharedPreferencesImpl.apply()`、`awaitCommit()`、慢 `fsync()` 或 receiver / service 收尾路径，通常就能把问题收敛到 pending 的 SP 刷盘。旧应用可能出现在 `ActivityThread.handlePauseActivity()`，更常见的是 receiver / service 边界。

### Binder 死锁 ANR

在 Perfetto 的 Binder track 中，调用方的线程在等待对端的 Binder 线程响应。如果形成环形依赖，会看到 A 等 B、B 等 A 的环形箭头。

### Broadcast 风暴 ANR

在 system_server 的 Binder 线程 track 中，看到大量连续的 `broadcastIntent` 调用。多个 App 进程的主线程几乎同时出现阻塞（堆栈停在 `ActivityThread.handleReceiver()`）。如果多个 App 在同一时间段内触发 ANR traces，且时间间隔很短（几十毫秒到几秒），就可能是 Broadcast 风暴的连锁反应。

### ContentProvider 冷启动 ANR

在 Perfetto 中，App A 的主线程发起 `ContentProviderClient.query()` 后进入 WAITING 状态（紫色），等待 App B 的 Binder 回复。同时 App B 进程处于冷启动阶段——在 `ActivityThread.handleBindApplication()` 中初始化 ContentProvider。如果 App B 的 ContentProvider `onCreate()` 耗时过长，App A 的主线程就会一直等待。对应的 Track 表现是：App A 主线程的长段 WAITING 与 App B 进程的启动序列在时间线上对齐。

### 低内存 / 频繁 GC ANR

在 Perfetto 的 ART 内部 track 中搜索 `A.RT` 或 `GC` 相关的 slice，能观察到 GC 事件的频率和持续时间。正常情况下 Young GC 的 slice 间隔在 500ms 以上；如果间隔缩短到几十毫秒，且每次 GC 的持续时间增加（从 1-3ms 升高到 10ms+），就是 GC 风暴的信号。同时可以在 CPU track 中看到 `HeapTaskDaemon` 线程的 CPU 占用异常升高。如果是系统级内存压力，`kswapd` 内核线程的 CPU 占用也会显著增加。

### 文件锁竞争 ANR

主线程如果卡在 `SQLiteConnectionPool` 或 Java / native mutex 上，常见状态是 WAITING / futex；如果卡在 `fsync()`、`fcntl()`、checkpoint 或底层 I/O，才更容易进入 D 状态。多进程数据库场景要把后台写事务、WAL 文件增长、checkpoint、SQLite busy / locked 日志和连接池等待时间放到同一时间窗里看。

## 与其他机制的关系

- **§1.4 Binder IPC**：Binder 死锁和线程池耗尽是 Binder 同步调用的固有限制
- **§4.4 LMK**：系统负载高和内存紧张经常同时出现
- **§9.1 / §9.2**：特殊场景的 ANR 仍然遵循标准超时机制，只是根因不在 App 代码本身
- **§6.3 I/O 调度**：系统负载型 ANR 中的 I/O 阻塞问题，与存储子系统的 I/O 调度策略直接相关

## 版本演进

- **Android 8**：`startForegroundService()` 的前台化宽限期 5 秒（`SERVICE_START_FOREGROUND_TIMEOUT = 5*1000`）；后台 service 限制开始明显收紧。
- **Android 9**：前台化宽限期提升到 10 秒（`10*1000`，见 ActiveServices.java android-9.0.0_r61）。
- **Android 10 / 11**：AOSP 常见前台化宽限期提升到 10 秒；广播超时仍以前台 10 秒、后台 60 秒为主。
- **Android 12**：新增 `ForegroundServiceStartNotAllowedException`，把“后台启动被拒绝”和“已启动但未及时前台化”拆成两条路径。
- **Android 14**：Broadcast 在 CPU starvation 条件下会出现前台 10-20 秒、后台 60-120 秒的浮动窗口；`shortService` 前台服务类型引入独立 timeout 与 `Service.onTimeout()`。
- **Android 15 / 16**：`dataSync` / `mediaProcessing` 这类 time-limited FGS 需要按配额、`onTimeout()` 和迟到 ANR / exception 路径排查；本章涉及的 `QueuedWork` / `SharedPreferences.apply()` 机制没有看到公开文档级别的机制改写。

## 常见问题与误区

**"apply() 是异步的，不会导致 ANR"** — `apply()` 会把写盘排进后台队列，但在 BroadcastReceiver、Service 和其他组件边界上，`QueuedWork.waitToFinish()` 仍可能把主线程拖住。

**"ANR 一定是 App 代码的问题"** — 不完全是。系统负载高、I/O 阻塞、Broadcast 风暴等原因导致的 ANR，根因在系统层面。

**"主线程堆栈在 nativePollOnce 就没有问题"** — 如果 input event 已经派发但主线程长时间没被调度到，也可能触发 ANR。需要看 CPU Scheduling track。

**"多进程 App 不会比单进程更容易 ANR"** — 恰恰相反。多进程 App 有更多的 Binder 调用、进程间同步和 ContentProvider 交互，增加了死锁和线程池耗尽的风险。

**"GC 不会导致 ANR"** — 当内存紧张触发频繁 GC 时，每次 GC 的 STW 停顿会累积，效果等同于主线程被长时间阻塞。

## 参考资料

### AOSP 源码

- `frameworks/base/core/java/android/app/ActivityThread.java` — `handlePauseActivity()`、`handleBindApplication()`、receiver / service 边界上的 `QueuedWork.waitToFinish()` 调用点
- `frameworks/base/core/java/android/app/SharedPreferencesImpl.java` — `apply()`、`awaitCommit()`
- `frameworks/base/core/java/android/app/QueuedWork.java` — `waitToFinish()`
- `frameworks/base/services/core/java/com/android/server/am/ActivityManagerService.java` — `broadcastIntentLocked()`
- `frameworks/base/services/core/java/com/android/server/am/ActiveServices.java` / `ServiceRecord.java` — 前台服务 timeout、`ServiceRecord.ShortFgsInfo`、迟到 ANR 判定
- `art/runtime/gc/heap.cc` / `art/runtime/gc/gc_cause.h` — heap growth target、`concurrent_start_bytes_`、GC cause
- `frameworks/base/core/java/android/database/sqlite/SQLiteDatabase.java` / `SQLiteConnectionPool.java` — 事务模式与连接池等待

### 官方文档

- [Jetpack DataStore Guide](https://developer.android.com/topic/libraries/architecture/datastore)
- [Jetpack App Startup](https://developer.android.com/topic/libraries/app-startup)
- [Binder IPC Overview](https://source.android.com/docs/core/architecture/aidl)

### 高质量参考

- 高爷 androidperformance.com ANR 分析系列
- [Perfetto Official Documentation](https://perfetto.dev/docs/)

### Android 14 → Android 17 Foreground Service Timeout / ANR 机制深度解析
- 来源：/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/DeepResearch/Android 14 → Android 17 Foreground Service Timeout : ANR 机制深度解析(AOSP 源码视角).md
- 类型：DeepResearch 调研结果
- 摘要：聚焦 `ActiveServices`、`ServiceRecord.ShortFgsInfo`、`AnrTimer` 等源码，梳理 Android 14–17 中 shortService 与 time-limited FGS 的超时窗口、回调语义、异常抛出与迟到 ANR 触发路径，适合补齐特殊场景 ANR 的系统侧视角。
- 注入时间：2026-04-24
- 价值：直接补上前台服务超时 ANR 的版本演进与 system_server 判责链路。
