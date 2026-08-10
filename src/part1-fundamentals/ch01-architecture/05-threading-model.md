---
title: "线程模型"
chapter: "1.5"
section: "1.5"
status: finalized
pipeline_stage: finalized
applicable_versions: "Android 5.0 (API 21) - Android 17 (API 37)"
confidence: high
tags:
  - thread
  - handler
  - looper
  - messagequeue
  - renderthread
  - coroutine
  - workmanager
  - thread-priority
sources:
  - type: official
    path: "https://developer.android.com/guide/components/processes-and-threads"
  - type: official
    path: "https://developer.android.com/reference/android/os/Handler"
  - type: official
    path: "https://developer.android.com/reference/android/os/HandlerThread"
  - type: official
    path: "https://developer.android.com/reference/android/os/AsyncTask"
  - type: official
    path: "https://developer.android.com/kotlin/coroutines"
  - type: official
    path: "https://developer.android.com/topic/libraries/architecture/workmanager"
  - type: official
    path: "https://developer.android.com/about/versions/17/behavior-changes-17"
  - type: aosp
    path: "frameworks/base/core/java/android/app/ActivityThread.java @ android-17.0.0_r1"
  - type: aosp
    path: "frameworks/base/core/java/android/os/Looper.java @ android-17.0.0_r1"
  - type: aosp
    path: "frameworks/base/core/java/android/os/Handler.java @ android-17.0.0_r1"
  - type: aosp
    path: "frameworks/base/core/java/android/os/LegacyMessageQueue/MessageQueue.java @ android-17.0.0_r1"
  - type: aosp
    path: "frameworks/base/core/java/android/os/CombinedMessageQueue/MessageQueue.java @ android-17.0.0_r1"
  - type: aosp
    path: "frameworks/base/core/java/android/os/CombinedDeliMessageQueue/MessageQueue.java @ android-17.0.0_r1"
  - type: aosp
    path: "frameworks/base/core/java/Android.bp @ android-17.0.0_r1"
  - type: aosp
    path: "frameworks/base/graphics/java/android/graphics/HardwareRenderer.java @ android-17.0.0_r1"
  - type: aosp
    path: "frameworks/base/core/java/android/view/ThreadedRenderer.java @ android-17.0.0_r1"
  - type: aosp
    path: "frameworks/base/libs/hwui/renderthread/RenderThread.cpp @ android-17.0.0_r1"
  - type: aosp
    path: "frameworks/base/libs/hwui/renderthread/DrawFrameTask.cpp @ android-17.0.0_r1"
  - type: aosp
    path: "frameworks/base/libs/hwui/renderthread/RenderProxy.cpp @ android-17.0.0_r1"
  - type: aosp
    path: "system/core/libutils/Looper.cpp @ android-17.0.0_r1"
  - type: aosp
    path: "frameworks/base/core/java/android/os/Process.java @ android-17.0.0_r1"
  - type: aosp
    path: "system/core/libprocessgroup/profiles/task_profiles.json @ android-17.0.0_r1"
  - type: aosp
    path: "libcore/ojluni/src/main/java/java/lang/Thread.java @ android-17.0.0_r1"
  - type: aosp
    path: "libcore/api/current.txt @ android-17.0.0_r1"
  - type: kernel
    path: "kernel/sched/fair.c @ android17-6.18-2026-06_r6"
last_verified: "2026-08-06"
last_verified_against: "AOSP android-17.0.0_r1; ACK android17-6.18-2026-06_r6; Android Developers"
related_chapters:
  - "1.2"
  - "1.4"
  - "1.13"
  - "2.4"
  - "2.5"
  - "5.1"
drafted_date: "2026-03-31"
drafted_by: "openclaw-task2"
reviewed_date: "2026-08-07"
reviewed_by: "hermes-aiw-review-finalize-apply"
reviewed_at: "2026-05-26T01:12:00+08:00"
task6_state: reviewed
task6_result: pass-light-edit
task6_reviewed_date: "2026-07-07"
last_task6_at: "2026-07-07T08:10:16+08:00"
last_task6_audit: "2026-07-08"
task6_review_notes: "2026-07-07 08:10 Task6：Task2B lite 修复后重审（版本引用已更新至 android-17.0.0_r1）；L1 小修 4 处（承担→中性动词 ×2、对齐→对照、结构性元叙述 ×1）；无新增 L3/L4 回炉项；转 Task9 复核 P1 版本修复。"
task9_state: reviewed
task9_result: pass-tech-review
task9_reviewed_date: "2026-07-07"
task9_reviewed_by: "openclaw-task9"
last_task9_at: "2026-07-07T08:21:00+08:00"
last_task9_audit: "2026-07-05"
last_task9_audit_at: "2026-07-05T15:20:00+08:00"
last_task9_audit_log: "logs/deep-review/2026-07-05-15-audit.md"
last_task9_audit_result: "p1-issue-found"
task9_review_notes: "2026-07-07 Task9 review: pass-tech-review。复核源码引用准确性、原理链完整性、版本差异覆盖。发现 1 处 P2 建议改进：16KB page size 对 metadata region 影响可补充。写入 suggestions.md。Task6 已通过且 queue 无 pending，自动晋升 finalized。"
task9_audit_notes: "2026-07-05 Task9 idle audit: 发现 P1 版本覆盖不匹配问题。章节声明适用 Android 5.0 - Android 17，但源码引用基于 android-16.0.0_r1，与 Android 17 (android-17.0.0_r1) 存在版本差异。已写入 suggestions.md 建议修正版本覆盖声明。"
task2b_state: fixed
task2b_result: fixed-lite
last_task2b_lite_at: "2026-07-07"
last_task2b_at: "2026-07-07T07:36:00+08:00"
review_round: 11
polish_count: 2
polish_date: "2026-04-10"
polish_by: "task2b-polish"
last_task9_review_log: "logs/deep-review/2026-05-26-01-deep-review.md"
last_task6_review_log: "logs/review/2026-07-07-08-review.md"
review_notes: "2026-05-26 Task9 deep-review: pass-tech-review。P0 0 / P1 0 / P2 0;Binder ioctl、硬件加速版本边界、MessageQueue 观察点复核通过;Task6 已通过且 queue 无 pending,自动晋升 finalized。"
deepseek_cn_review_state: done
last_deepseek_cn_review_at: "2026-07-07"
last_body_apply_at: "2026-08-06T23:15:01+08:00"
last_body_apply_run_id: "20260806-231501-982bb83c"
last_body_apply_source: "queue:freshness:src/part1-fundamentals/ch01-architecture/05-threading-model.md"
last_review_finalize_at: "2026-08-07T08:18:06+08:00"
last_review_finalize_run_id: "20260807-081516-9264ee2d"
review_finalize_notes: "Hermes AIW review/finalize：按 android-17.0.0_r1 / android17-6.18 基线复核主线程 Looper、MessageQueue 实现选择、RenderThread 交接、调度优先级、虚拟线程边界；未发现 P0/P1/P2 阻断项，推进 finalized。"
---

# 线程模型

Android 应用的线程模型远比“主线程加几个后台线程”复杂。一次点击可能依次经过主线程的输入分发、业务代码、Binder 调用和渲染提交；其中任何线程被锁、I/O 或调度延迟拖住，都可能让这一帧错过显示期限。

理解线程模型，是为了建立三种判断能力：

1. 这段工作为什么运行在当前线程？
2. 当前线程是在执行、等待 CPU，还是等待另一个线程或内核事件？
3. 这段工作应该留在当前线程，还是交给其他执行机制？

## 主线程负责什么

应用进程由 Zygote fork 后，`ActivityThread.main()` 在进程初始线程上完成主消息循环的初始化。`ActivityThread` 是应用进程的调度中枢，不是另一个 `Thread` 对象。

Android 17 中的关键顺序如下，代码省略了参数解析、日志和调试初始化：

```java
// frameworks/base/core/java/android/app/ActivityThread.java
// @ android-17.0.0_r1，节选
public static void main(String[] args) {
    // 参数解析可在此前处理 --use-deliqueue。
    Looper.prepareMainLooper();

    ActivityThread thread = new ActivityThread();
    thread.attach(false, startSeq);

    if (sMainThreadHandler == null) {
        sMainThreadHandler = thread.getHandler();
    }
    Looper.loop();

    throw new RuntimeException("Main thread loop unexpectedly exited");
}
```

`Looper.loop()` 正常情况下不会返回。主线程持续处理消息，直到进程退出。

应用组件和 View 体系的大部分回调都在主线程运行，包括：

- Activity、Service 和 BroadcastReceiver 的主要生命周期回调；
- 输入事件分发；
- View 的 measure、layout 和显示列表记录；
- `Choreographer` 驱动的动画与帧回调；
- 主线程 Handler、主线程 Executor 和 `Dispatchers.Main` 上的任务；
- 直接在主线程发起的同步 Binder 调用。

“Binder 回调都在主线程”则是错误的。远程 AIDL 调用默认由进程的 Binder 线程池接收；服务代码是否再切回主线程，取决于组件和实现。反过来，主线程主动发起同步 Binder 调用时会等待远端返回，因此仍可能造成主线程卡顿。

## Looper、MessageQueue 与 Handler

一个已经调用 `Looper.prepare()` 的线程拥有一个 `Looper` 和一个 `MessageQueue`，可以有多个绑定到这个 Looper 的 `Handler`。

- `Handler` 负责投递消息或 Runnable，并在消息被取出时分发回调；
- `MessageQueue` 保存尚未处理的消息，并计算下一次唤醒时间；
- `Looper` 循环取出到期消息，调用消息对应 Handler 的 `dispatchMessage()`。

`Looper` 通过 `ThreadLocal` 与当前线程关联。它不会自己创建线程，也不会把回调自动搬到后台。回调在哪个线程执行，只取决于 Handler 绑定的 Looper。

Android 17 的循环主体仍可以概括为：

```java
// frameworks/base/core/java/android/os/Looper.java
// @ android-17.0.0_r1，按调用关系简化
for (;;) {
    if (!loopOnce(me, ident, thresholdOverride)) {
        return;
    }
}

// loopOnce() 内部取得消息后执行：
msg.target.dispatchMessage(msg);
msg.recycleUnchecked();
```

创建 Handler 时应显式指定 Looper，或者使用能够表达执行位置的 Executor。无参 `Handler()` 和隐式绑定当前线程的构造方式已经废弃，因为调用点一旦换到没有 Looper 的线程，或者意外绑定到错误的 Looper，问题通常要到运行时才暴露。

```kotlin
private val mainHandler = Handler(Looper.getMainLooper())

fun updateUiLater() {
    mainHandler.post {
        // 这里明确运行在主线程。
    }
}
```

构造点已经把执行目标固定为 main Looper，因此调用方位于哪条线程都不会改变消息归属。它只解决投递位置问题，不保证任务能在某个固定时限内执行。

### Android 17 的 MessageQueue 不能再只按链表理解

经典 `LegacyMessageQueue` 以 `mMessages` 为头结点，维护按执行时间排序的单向链表。这个模型适合解释旧版本的插入、同步屏障和 `next()`，但不能代表 Android 17 的全部实现。

Android 17 有两层选择：

1. **构建时选择源码实现。** `frameworks/base/core/java/Android.bp` 排除各个 MessageQueue 实现目录，再由 `messagequeue-gen` 选择一套源码生成最终的 `android.os.MessageQueue`。默认配置和产品变量可以选择不同实现。
2. **运行时选择兼容模式。** `CombinedMessageQueue` 和 `CombinedDeliMessageQueue` 自身还会根据兼容性变更、平台进程身份与功能开关，在 legacy 路径和新路径之间选择。

因此，源树中存在多个同名源码文件，不代表它们会作为三个公开类同时装入应用进程。最终 Java API 仍然是 `android.os.MessageQueue`。

Android 17 对以 API 37 为目标版本的应用启用新的无锁 MessageQueue 实现。依赖 `mMessages` 等私有字段的反射代码可能失效。测试代码应使用公开或测试框架提供的同步机制，例如 IdlingResource；不要通过遍历私有链表判断“队列已空”。具体数据结构和 DeliQueue 见 §1.13。

### Looper 空闲时为什么不消耗 CPU

没有到期消息时，Java MessageQueue 会进入 native poll。Android 17 的 `system/core/libutils/Looper.cpp` 创建 epoll 实例和用于唤醒的 eventfd，等待时调用 `epoll_wait()`。

新消息改变下一次到期时间时，生产者写入 eventfd 唤醒 Looper。通过原生 Looper 或 MessageQueue 文件描述符监听接口注册的 fd，也可以由同一轮 epoll 等待发现。线程此时处于阻塞睡眠，不是在 Java 层不断检查队列。

Binder 线程池是另一条等待路径。Binder 工作线程通过 Binder 驱动的读写 ioctl 等待事务，默认不依赖主线程 Looper 的 epoll。Perfetto 中看到主线程睡在 `epoll_wait`，不能据此判断 Binder 线程也处于同一种等待。

### 延迟消息不是精确定时器

`postDelayed()` 和 `sendMessageAtTime()` 表达的是“到这个时刻后才有资格执行”，不是“保证在这个时刻执行”。消息到期后仍可能受以下因素影响：

- 队列前方正在执行的长消息；
- 同步屏障对同步消息的阻挡；
- 线程处于 Runnable 状态但没有及时获得 CPU；
- 进程冻结、省电策略或系统负载；
- 系统时钟和休眠语义。

如果业务要求持久化、跨进程存活或由系统在约束满足后调度，应使用 Alarm、JobScheduler 或 WorkManager 等相应机制，而不是让主线程 Handler 保存一个很长的延迟任务。

### IdleHandler 只能做有界的轻量工作

`MessageQueue.IdleHandler` 在队列暂时没有可执行消息时运行，回调仍发生在所属 Looper 线程。它并没有一段由系统保证的“空闲预算”。回调运行期间新消息可以入队，而新消息必须等回调返回。

适合放入 IdleHandler 的是短小、可中断或只做一次的初始化。磁盘扫描、网络访问、大对象反序列化和不可控循环都应移出主线程。返回 `false` 会在本次调用后移除该 IdleHandler；返回 `true` 表示以后队列进入空闲状态时仍可调用。

## 主线程与 RenderThread 如何分工

硬件加速窗口不会把整个绘制过程都放到主线程。

主线程主要负责：

- 执行动画和 View 回调；
- measure 与 layout；
- 遍历 View 树并记录显示列表；
- 把本帧状态同步给渲染管线。

RenderThread 主要负责：

- 消费已记录的渲染节点和显示列表；
- 准备、批处理并提交 GPU 工作；
- 管理 HWUI 的渲染上下文；
- 执行一部分可以脱离主线程推进的属性动画。

Android 17 的 `RenderThread::getInstance()` 懒加载名为 `RenderThread` 的线程。`threadLoop()` 把线程 nice 调整为 `PRIORITY_DISPLAY`，然后初始化原生 Looper、Choreographer 及图形后端。普通应用的 RenderThread 不应被笼统描述为 `SCHED_FIFO` 实时线程。

### `syncAndDrawFrame()` 是主线程与 RenderThread 的交接点

主线程经过 `ThreadedRenderer`、`HardwareRenderer` 和 `RenderProxy`，最终调用 `DrawFrameTask::drawFrame()`。后者把任务投递给 RenderThread，并等待同步阶段推进：

```cpp
// frameworks/base/libs/hwui/renderthread/DrawFrameTask.cpp
// @ android-17.0.0_r1，节选
int DrawFrameTask::drawFrame() {
    mSyncResult = SyncResult::OK;
    mSyncQueued = systemTime(SYSTEM_TIME_MONOTONIC);
    postAndWait();
    return mSyncResult;
}

void DrawFrameTask::postAndWait() {
    AutoMutex _lock(mLock);
    mRenderThread->queue().post([this]() { run(); });
    mSignal.wait(mLock);
}
```

RenderThread 执行 `run()` 时先同步帧状态。满足条件时，它可以在提交绘制前解除主线程等待；如果纹理准备等工作要求继续持有同步点，则会在稍后解除。因此，不能把这段关系简化成“主线程提交后立即自由运行”，也不能理解成“主线程必须等 GPU 完成整帧”。

Perfetto 中常见三种情况：

- 主线程长：输入、业务、布局或显示列表记录成为瓶颈；
- RenderThread 长：渲染准备、图形驱动或 GPU 侧压力更可疑；
- 主线程在同步点等待 RenderThread：需要沿唤醒关系继续看 RenderThread 当时是在运行、等 CPU、等锁，还是等图形资源。

软件渲染窗口不走这条 `ThreadedRenderer` 硬件渲染路径。但不能据此断言“进程中一定没有 RenderThread”，因为同一进程中的其他硬件加速窗口仍可能创建它。

## 如何选择后台执行机制

先判断任务是否需要立即完成、是否必须持久化、是否要求串行和线程亲和性，再选择工具。

| 需求 | 首选工具 | 关键边界 |
|---|---|---|
| 很短的 UI 更新 | 主线程 Handler、Main Executor、`Dispatchers.Main` | 不做阻塞 I/O 或长计算 |
| 与生命周期绑定的异步任务 | Kotlin 协程 + `lifecycleScope`/`viewModelScope` | 保留结构化取消关系 |
| CPU 密集型并行计算 | `Dispatchers.Default` 或有界 Executor | 控制并行度，避免超过设备承受能力 |
| 阻塞式磁盘或网络调用 | `Dispatchers.IO` 或专用有界 Executor | 线程池不能消除底层阻塞，只是移出主线程 |
| 必须在一个带 Looper 的专用线程串行执行 | HandlerThread | 明确所有权，并安全退出 |
| 必须在约束满足后可靠执行的持久任务 | WorkManager | 调度时刻不精确，普通 Worker 有运行时长限制 |
| 需要立即运行且用户可感知的长任务 | 前台服务及相应任务 API | 遵守后台启动和通知限制 |

### HandlerThread：仅在需要 Looper 时使用

HandlerThread 适合要求线程亲和、顺序处理，且依赖 Handler/Looper API 的组件。只为了“开一个后台线程”时，Executor 或协程通常更容易管理并发、返回值和取消。

```kotlin
class SerialWorker : Closeable {
    private val thread = HandlerThread(
        "serial-worker",
        Process.THREAD_PRIORITY_BACKGROUND
    ).apply { start() }

    private val handler = Handler(thread.looper)

    fun submit(block: () -> Unit) {
        check(handler.post(block)) { "worker is shutting down" }
    }

    override fun close() {
        thread.quitSafely()
        thread.join()
    }
}
```

`quitSafely()` 会处理已经到期的消息，再丢弃未来消息并退出；`quit()` 会更直接地终止队列。调用方还要避免在该线程自身执行 `join()`，并保证关闭后不再投递。

### 协程管理任务结构，不会让代码自动变快

协程可以用较少线程表达大量挂起任务，但实际的阻塞调用仍会占住承载它的线程。Dispatcher 选择需要与工作类型相符：

```kotlin
class UserRepository(
    private val api: UserApi,
    private val db: UserDatabase,
) {
    suspend fun refresh(id: String): User = withContext(Dispatchers.IO) {
        val user = api.load(id)   // 阻塞式接口会占用 IO worker
        db.users().upsert(user)
        user
    }
}
```

- `Dispatchers.Main` 用于短小的 UI 工作；
- `Dispatchers.Default` 用于 CPU 密集工作；
- `Dispatchers.IO` 用于阻塞式 I/O；
- 专用 dispatcher 用于线程亲和、资源隔离或严格并发上限。

不要依赖 Default 或 IO 当前的具体线程数。它们会随 Kotlin 版本、系统属性和运行环境调整。协程在挂起后也可能由另一个工作线程继续执行，因此普通 `ThreadLocal` 不能自然表达跨挂起点的上下文；需要时使用协程上下文或 `ThreadLocal.asContextElement()`。

结构化并发要求每项任务都有明确的 scope，由页面、ViewModel、服务或应用级组件持有；生命周期结束时，取消关系才能沿父子任务传播。只看任务在哪条线程运行，无法判断其所有权和取消边界。

### WorkManager 用于持久任务调度

WorkManager 面向需要在应用退出、进程重建后仍应继续安排的持久后台任务。它会根据系统版本使用 JobScheduler 等调度设施，并在约束满足后尽力执行，但不保证精确启动时间，也不保证恰好执行一次业务副作用。

Worker 可能因为约束变化、进程终止或重试策略重复运行。上传、扣减、写入远端等操作应设计为幂等，或者由服务端提供去重键。普通 Worker 还受到单次运行时长限制；需要长时间运行时，应按 WorkManager 长任务和前台服务规则设计，不能无限阻塞一个 Worker。

立即发生、只需随当前页面存活的任务不应绕到 WorkManager。它既增加调度开销，也会模糊任务所有权。

### AsyncTask 与 IntentService 的版本位置

`AsyncTask` 在 API 30 已废弃。它把线程池、生命周期和主线程回调包装在一个类里，但容易造成 Context 泄漏、配置变更后回调错位、取消语义不完整和异常处理不一致。新代码应按任务性质选择协程或 `java.util.concurrent`。

`IntentService` 同样在 API 30 废弃，原因是 Android 8.0 以后后台执行限制可能中断其工作。替代方案不是固定的：

- 需要持久、可延迟的工作，使用 WorkManager；
- 需要立即执行且用户可感知的长工作，评估前台服务；
- 仅在进程内短时串行执行，使用协程、Executor 或确有 Looper 需求时使用 HandlerThread。

## 线程优先级、调度类与任务配置

Android Java 层的 `Process.setThreadPriority()` 调整的是 Linux nice 值。Android 17 中常见常量包括：

- `THREAD_PRIORITY_DEFAULT = 0`；
- `THREAD_PRIORITY_BACKGROUND = 10`；
- `THREAD_PRIORITY_FOREGROUND = -2`；
- `THREAD_PRIORITY_DISPLAY = -4`；
- `THREAD_PRIORITY_URGENT_DISPLAY = -8`；
- `THREAD_PRIORITY_AUDIO = -16`。

数值越小，nice 优先级越高，但这不等于获得固定比例的 CPU，也不保证立即运行。对普通应用线程，`Process.setThreadPriority()` 比 `Thread.setPriority()` 更能准确表达 Android/Linux 层的调度意图。

在 ACK `android17-6.18-2026-06_r6` 中，普通 `SCHED_NORMAL`/`SCHED_BATCH` 线程进入 fair 调度类，`kernel/sched/fair.c` 使用 EEVDF 选择可运行实体。nice 值会改变调度权重和虚拟时间推进方式，而不是把 CPU 简单切成固定份额。

Android 还通过 task profile、cgroup 和 cpuset 管理进程或线程。AOSP Android 17 的 `task_profiles.json` 为 background、foreground、top-app 等组合作出不同的性能、I/O、timer slack 和 CPU capacity 配置；设备厂商可以覆盖这些配置。因此，“前台组必定运行在某几颗大核”不是跨设备成立的结论。

### 不要把实时调度和 CPU 亲和性当成常规优化

`SCHED_FIFO`/`SCHED_RR` 会绕过普通 fair 调度，配置不当可能饿死主线程、系统服务甚至关键内核工作。设置实时策略通常还需要系统权限和经过约束的系统组件，不是三方应用的通用性能开关。

手动把 RenderThread 或业务线程绑到所谓“大核”也不可移植。SoC 拓扑、能效模型、温控状态和厂商调度策略各不相同，固定亲和性可能降低性能或增加功耗。普通应用应先缩短关键路径、控制并行度，并让系统调度器和 ADPF 等公开机制表达性能需求。

## 线程越多，吞吐量不一定越高

增加线程只有在任务能并行、资源没有成为瓶颈且调度成本可接受时才可能提高吞吐量。过度线程化会带来：

- 每个线程的 native 元数据与栈地址空间开销；
- 更多上下文切换和缓存工作集扰动；
- 更多 Runnable 线程争抢有限 CPU；
- 锁竞争、队列竞争和优先级反转；
- 不受控的并行 I/O，使存储或服务端更拥塞。

线程栈大小和实际物理内存占用会随运行时、架构、线程创建方式及已触碰页面变化，不应把某个固定数值当成所有 Android 设备的成本。

CPU 密集型任务应使用有界并行度，并以目标设备上的吞吐、尾延迟、功耗和温度为依据。I/O 密集型池可以比 CPU 核数大，但仍需限制并发，保护文件描述符、连接池、数据库和远端服务。

## 用 Perfetto 判断线程为什么慢

看到一个很长的 slice，只能说明某段逻辑从开始到结束经历了很长时间。下一步要把时间拆成线程状态：

- **Running**：线程在 CPU 上执行；
- **Runnable**：可以运行，但在等 CPU；
- **Sleeping / Interruptible sleep**：常见于等消息、Binder、futex、I/O 或条件变量；
- **Uninterruptible sleep**：通常需要继续检查内核 I/O、驱动或等待链。

排查一帧卡顿时，可以按以下顺序推进：

1. 从 FrameTimeline 或对应帧事件确认错过的是应用期限还是显示合成期限；
2. 同时查看主线程和 RenderThread，而不是只盯 `doFrame`；
3. 对长区间展开 thread state，区分在 on-CPU、Runnable 与阻塞；
4. Runnable 很长时查看 CPU 是否被更高优先级或大量线程占用；
5. 阻塞时沿 wakeup、futex、Binder、I/O 或锁持有者寻找实际的唤醒方；
6. 回到源码确认 slice 对应的执行边界，再决定优化业务、并行度还是跨线程协议。

主线程睡在 Looper poll 通常表示“当前没有到期消息”，本身不是卡顿证据。相反，如果关键消息已到期而主线程仍被前一条消息占用，才需要缩短那条消息的执行路径。

## Android 17 的虚拟线程边界

Android 17 的 `libcore` 源码和 API 文本已经出现第一版虚拟线程接口，包括 `Thread.ofVirtual()`、`Thread.startVirtualThread()`、`Thread.isVirtual()` 和 `Executors.newVirtualThreadPerTaskExecutor()`。实现受 `com.android.libcore.virtual_thread_api_v1` 等发布开关控制。

源码与发布开关共同划定了使用边界：

- “Android 的虚拟线程永远没有实现”已经不符合 Android 17 源码；
- “所有 Android 17 设备都可以无条件使用虚拟线程”同样没有依据。

应用需要以实际 SDK 暴露、构建开关和目标设备行为为准，并准备兼容路径。虚拟线程适合表达大量阻塞式并发任务，但不会让 CPU 密集计算突破处理器上限，也不会替代主线程、Looper、生命周期 scope 或 WorkManager 的持久调度语义。面向多个 Android 版本的应用，协程和有界 Executor 仍是更稳定的基础工具。

## 容易混淆的结论

### “只要不在主线程就不会卡”

后台线程过多会抢占 CPU；后台线程持锁、占满 Binder 线程池或制造大量 I/O，也会间接拖慢主线程。

### “RenderThread 会接管所有绘制”

主线程仍要执行布局、显示列表记录和帧状态同步。RenderThread 无法补救主线程上的长业务、复杂布局或错误的同步等待。

### “线程优先级设得越高越快”

优先级只是调度输入，还受 cgroup、CPU 容量、温控和其他实时负载约束。滥用高优先级会把延迟转嫁给别的关键线程。

### “Handler 延迟时间到了就会准时执行”

到期只表示消息可以被选择。队列前方工作、同步屏障和 CPU 调度都可能继续推迟执行。

### “协程等于后台线程”

协程是可挂起任务的结构。它在哪个线程运行由 Dispatcher 和上下文决定；`Dispatchers.Main` 上的协程仍会占用主线程。

## 版本演进

| 版本 | 与线程模型相关的变化 |
|---|---|
| Android 5.0 | 硬件加速渲染管线进一步采用独立 RenderThread，主线程与渲染提交的分工成为常见分析对象 |
| Android 8.0 | 后台执行限制趋严，后台 Service 不再适合承载任意长任务 |
| Android 11 / API 30 | `AsyncTask` 与 `IntentService` 废弃 |
| Android 12 以后 | 前台服务启动和后台工作的限制持续增加，任务类型必须与系统 API 语义匹配 |
| Android 17 / API 37 | 以 API 37 为目标的应用启用新的无锁 MessageQueue；私有字段反射存在兼容风险 |
| Android 17 / API 37 | `libcore` 出现受发布开关控制的虚拟线程 v1 API 与实现，不能假定所有构建均启用 |

分析线程问题时，先确认平台版本、应用 targetSdk、设备构建与实际调度配置，再解释 trace。只凭线程名称、某个 nice 值或旧版 MessageQueue 字段，无法得出可靠结论。
