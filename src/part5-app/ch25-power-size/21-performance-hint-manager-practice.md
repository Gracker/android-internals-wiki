---
title: "Android 12+ PerformanceHintManager 实战：Java/NDK 集成与 Android 17 源码校准"
chapter: "25.21"
section: "25.21"
task9_result: "auto-fixed"
task9_reviewed_date: "2026-07-10"
last_task6_audit: "2026-07-10"
task9_reviewed_by: "openclaw-task9"
last_task9_at: "2026-07-10T15:29:22+08:00"
last_task9_review_log: "logs/deep-review/2026-07-10-15-deep-review.md"
task2b_state: "fixed"
task2b_result: "fixed"
task6_state: "reviewed"
task6_result: "pass-light-edit"
task6_review_notes: "2026-07-10 Task6 revisiting-review: pass-light-edit。L1: 2 fixes (banned word 闭环→完整衔接, 链路→路径)。L2通过(开头直接、结构清晰)。无B类大问题。"
task6_review_notes_round3: "2026-07-10 Task6 revisiting-review round3: pass-light-edit (章节技术内容完整，符合writing-guide规范，无新增问题)"
reviewed_date: "2026-07-10"
reviewed_by: "openclaw-task6"
task6_review_notes_round4: "2026-07-10 Task6 review round4: pass-light-edit, auto-promoted to finalized (task6+task9 passed, queue clean, removed editing process notes from bottom per writing-guide L1 rule)"
task9_state: "reviewed"
task9_review_notes: "2026-07-10 Task9 deep-review: auto-fixed。修正 Java setThreads API 级别、Session close 后状态说明、NDK API36 Java session bridge、dumpsys/statsd 字段、未证实 trust/low-memory 断言；回到 Task6 复审。详见 logs/deep-review/2026-07-10-15-deep-review.md。"
updated_by: "openclaw-task9"
updated_date: "2026-07-10"
last_task2b_at: "2026-07-10T14:52:47+08:00"
last_task9_autofix_at: "2026-07-10"
status: "finalized"
drafted_date: "2026-07-10"
applicable_versions: "Android 12 (API 31) - Android 17 (API 37)"
pipeline_stage: "ready-to-publish"
last_verified: "2026-07-10"
last_verified_against: "AOSP android-17.0.0_r1 + developer.android.com 官方文档"
confidence: medium
sources:
  - type: official
    path: "https://developer.android.com/reference/android/os/PerformanceHintManager"
  - type: official
    path: "https://developer.android.com/reference/android/os/PerformanceHintManager.Session"
  - type: official
    path: "https://developer.android.com/reference/android/os/WorkDuration"
  - type: official
    path: "https://developer.android.com/ndk/reference/group/performance"
  - type: official
    path: "https://developer.android.com/about/versions/13/features/13#performance-hints"
  - type: aosp
    path: "frameworks/base/core/java/android/os/PerformanceHintManager.java"
  - type: aosp
    path: "frameworks/base/core/jni/android_os_PerformanceHintManager.cpp"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/power/hint/HintManagerService.java"
  - type: aosp
    path: "frameworks/base/services/core/jni/com_android_server_hint_HintManagerService.cpp"
  - type: aosp
    path: "frameworks/native/include/android/performance_hint.h"
tags: [PerformanceHintManager, ADPF, 启动优化, 性能框架, Android12, NDK]
related_chapters: ["1.43", "8.33", "8.36"]
created_by: "task2a-knowledge-gap"
created_date: "2026-07-10"
gap_source: "AOSP结构+官方文档+章节深挖"
task2b_rework_source: "logs/deep-review/2026-07-10-14-deep-review.md"
p0: 0
p1: 0
p2: 0
deepseek_cn_review_state: done
last_deepseek_cn_review_at: 2026-07-10
---

# 25.21 Android 12+ PerformanceHintManager 实战：Java/NDK 集成与 Android 17 源码校准

> `PerformanceHintManager` 是 ADPF 面向周期性负载的提示接口。源码锚点为 `android-17.0.0_r1`，下面说明它能向系统提供什么信息、调用经过哪些组件，以及如何用 trace 判断接入是否有效。

## 1. 先界定问题：它接收周期目标，不提供“加速开关”

`PerformanceHintManager` 属于 Android Dynamic Performance Framework（ADPF）。应用把一组相互关联的线程放进同一个 hint session，给出每个工作周期的目标耗时，并在周期结束后回报实际耗时。系统据此尝试调整这些线程的 CPU core placement 或所在 CPU 核的频率，同时还要服从整机功耗、温度和其他负载的约束。

这套接口适合帧生产、音视频处理、游戏循环以及节奏稳定的计算流水线。它要求工作线程长期存在，应用也要持续提供可靠的 target/actual 数据。一次性的 `Application.onCreate()` 初始化、偶发网络回调或生命周期很短的线程，通常没有足够的连续样本，不适合仅为了“启动更快”建立 session。

应用提交的是 advisory input。公开 API 没有让应用指定 CPU 核、频点或调度策略的能力，也不承诺一次调用后立即升频。是否支持 hint session、Power HAL 如何解释提示、温控状态会压缩多少性能空间，都由设备实现和当时的系统状态决定。

## 2. API 漏斗：Android 17 没有新增一套公开接口

下表区分 Java 与 NDK 的引入版本。Android 17 这一章的更新重点是以 `android-17.0.0_r1` 校准实现和边界，不能把早期已有的能力写成 Android 17 新特性。

| 平台版本 | Java API | NDK API |
|---|---|---|
| Android 12 / API 31 | `PerformanceHintManager`、`createHintSession()`、`updateTargetWorkDuration()`、`reportActualWorkDuration(long)`、`close()` | 尚无公开 C API |
| Android 13 / API 33 | 延续基础 Session API | `APerformanceHint_getManager()`、创建/更新/报告/关闭等基础 C API |
| Android 14 / API 34 | `Session.setThreads()` | `APerformanceHint_setThreads()` |
| Android 15 / API 35 | `setPreferPowerEfficiency()`、`WorkDuration` 分项报告 | 能效模式、`AWorkDuration`、`APerformanceHint_reportActualWorkDuration2()` |
| Android 16 / API 36 | 没有与 NDK 扩展一一对应的公开 Java API | session creation config、feature probing、workload increase/reset/spike、surface 关联、Java Session 借用、graphics-pipeline thread 上限 |
| Android 17 / API 37 | `android-17.0.0_r1` 未新增公开方法 | `performance_hint.h` 未新增 API 37 函数 |

API 36 起，`APerformanceHint_getPreferredUpdateRateNanos()` 在 NDK 头文件中被标记为 deprecated：客户端无需自行按该值限流，framework 已处理报告频率；探测 session 或扩展能力应改用 `APerformanceHint_isFeatureSupported()`。Java 端仍有 `getPreferredUpdateRateNanos()`，但应用不应据此跳过每个有效周期的测量。

## 3. Android 17 的调用路径

Java 调用到 Power HAL 之间有五个可核验节点：

1. `SystemServiceRegistry` 用 `Context.PERFORMANCE_HINT_SERVICE` 注册 `PerformanceHintManager`，`Context.getSystemService(PerformanceHintManager.class)` 最终调用 `PerformanceHintManager.create()`。
2. `android_os_PerformanceHintManager.cpp` 动态加载 `libandroid.so`，再解析 `APerformanceHint_*` 与 `AWorkDuration_*` 符号。Java `Session` 持有的是 native session 指针。
3. `native/android/performance_hint.cpp` 中的客户端通过 `IHintManager` 与 system_server 通信。创建 session 必须经过 Binder，因为服务端要验证 TID、创建 HAL session 并登记生命周期。
4. `HintManagerService` 以 `performance_hint` 为 Binder 服务名发布，校验调用 UID、PID、TID 所属关系和进程状态，再经服务 JNI 连接 Power HAL。
5. Power HAL AIDL 的 `IPowerHintSession` 提供 `updateTargetWorkDuration`、`reportActualWorkDuration2`、`setThreads`、`setMode`、`sendHint`、`pause`、`resume` 与 `close` 等操作。厂商可按硬件与功耗策略实现这些建议。

高频操作还有一条低开销路径。Android 17 客户端初始化 manager 时会请求每进程的 `ChannelConfig`；当 Power HAL 版本和设备实现支持 FMQ，target 更新、actual report、load hint 与 mode 更新可写入 FMQ。FMQ 未建立、session 没有有效 `SessionConfig` 或队列异常时，代码回退到 `IHintSession` Binder 调用。因此，“每一帧报告都进行一次跨进程 Binder 调用”并不准确。

`HintManagerService` 还会根据 UID 进程状态暂停或恢复 session。TID 消失、归属失效或线程列表清理后为空时，服务也能强制暂停。此时应用继续调用 API，不代表 Power HAL 会接收并采用每条数据；`dumpsys` 中的 `AllowedByProcState` 和 `ForcePaused` 用来确认这两类状态。

## 4. Session 的语义约束

### 4.1 线程必须相关、稳定，并属于同一进程线程组

一个 session 表示一组共同完成同一周期工作的线程。Java 文档明确要求这些线程长期存在，不应按周期动态创建和销毁。传入的是 Linux TID，应在线程自身执行 `Process.myTid()` 获取；`Thread.getId()` 是 Java 线程标识，不能代替内核 TID。

`createHintSession()` 会拒绝空数组和非正数 target。设备不支持 hint session，或者 TID 无效、不属于调用应用时，它可以返回 `null`。多线程池场景应在 worker 启动时登记 TID，等成员稳定后创建 session；线程集合改变时再调用 `setThreads()`。该调用会替换整个 TID 列表，而且是同步调用，错误会以 `IllegalStateException`、`IllegalArgumentException` 或 `SecurityException` 暴露。

### 4.2 target 与 actual 必须描述同一个工作周期

target 表示一次周期希望完成的总时长，actual 表示刚完成周期的实测总时长。Android 17 Java 源码要求时间戳采用 `SystemClock.uptimeNanos()`；这个公开方法与 `WorkDuration` 都从 API 35 可用。API 31—34 使用基础的 `reportActualWorkDuration(long)` 时，只需提交持续时间，可用 `System.nanoTime()` 的差值。不能用“帧间隔”作为 target，却把某个子函数耗时当 actual，也不能只在慢帧时上报。这样的样本会让反馈失去含义。

target 发生变化时调用 `updateTargetWorkDuration()`，例如显示刷新率或工作批次规格改变。不要把每个周期的自然抖动原样写回 target，否则系统看不到稳定的预算。target 来自业务时限，actual 来自测量。

### 4.3 调用方负责线程安全和关闭顺序

`Session` 的每个方法都会修改内部数据，Java 文档要求调用方处理并发竞争。最省事的方案是让创建、更新、报告和关闭都在同一个 owner thread 上执行。`close()` 之后不得再调用任何 Session 方法；公开 API 也没有 CREATED、ACTIVE、DESTROYED 之类的状态枚举可供补救。

## 5. Java：在 owner thread 上运行一个周期负载

下面的类片段用于展示最小的正确结构：TID 在工作线程内部取得，session 的全部操作也留在该线程。`runPeriodicWork()` 代表应用已有的周期性工作，示例省略业务实现和异常上报。

```java
final class PeriodicHintWorker implements AutoCloseable {
    private static final long TARGET_NS = 8_000_000L;
    private static final long PERIOD_MS = 16L;

    private final HandlerThread thread = new HandlerThread("hint-owner");
    private final Handler handler;
    private final PerformanceHintManager manager;

    private PerformanceHintManager.Session session;
    private boolean stopped;

    PeriodicHintWorker(Context context) {
        thread.start();
        handler = new Handler(thread.getLooper());
        manager = context.getSystemService(PerformanceHintManager.class);
    }

    void start() {
        handler.post(() -> {
            int ownerTid = Process.myTid();
            session = manager.createHintSession(new int[]{ownerTid}, TARGET_NS);
            runOneCycle();
        });
    }

    private void runOneCycle() {
        if (stopped) {
            return;
        }

        long startNs = System.nanoTime();
        runPeriodicWork();
        long actualNs = System.nanoTime() - startNs;

        if (session != null) {
            session.reportActualWorkDuration(actualNs);
        }
        handler.postDelayed(this::runOneCycle, PERIOD_MS);
    }

    private void runPeriodicWork() {
        // Run one application-defined periodic work unit on this thread.
    }

    @Override
    public void close() {
        handler.post(() -> {
            stopped = true;
            if (session != null) {
                session.close();
                session = null;
            }
            thread.quitSafely();
        });
    }
}
```

这个片段没有把 `null` 当异常：它表示当前设备或线程集合无法建立 session，业务仍应正常运行。示例中只有 owner thread 执行工作；如果 `runPeriodicWork()` 把任务继续分发给其他线程，就要把关键路径上的长期线程一并登记，并保证 actual 覆盖同一工作周期。

UI 渲染接入还要多做一步：确定被测关键路径。不能在主线程的 `Choreographer.FrameCallback` 中测量一段时间，却把另一个 render worker 的 TID 放入 session。使用 graphics pipeline 模式时，NDK API 36 还要求按端到端图形流水线理解 thread 与 surface 的关系，线程数需服从 `APerformanceHint_getMaxGraphicsPipelineThreadsCount()` 返回的设备上限。

## 6. `WorkDuration`：分开描述 total、CPU 与 GPU

API 35 的 `WorkDuration` 允许应用报告一个周期的开始时间、总 wall time、CPU wall duration 与 GPU wall duration。下面的片段只展示对象填充顺序；`measuredCpuNs`、`measuredGpuNs` 必须来自应用已有且可信的测量。

```java
long startNs = SystemClock.uptimeNanos();
runCpuAndGpuWork();
long totalNs = SystemClock.uptimeNanos() - startNs;

WorkDuration duration = new WorkDuration();
duration.setWorkPeriodStartTimestampNanos(startNs);
duration.setActualTotalDurationNanos(totalNs);
duration.setActualCpuDurationNanos(measuredCpuNs);
duration.setActualGpuDurationNanos(measuredGpuNs);
session.reportActualWorkDuration(duration);
```

源码校验条件很具体：start 和 total 必须大于 0；CPU、GPU 必须大于等于 0；CPU 与 GPU 至少有一个大于 0。CPU 与 GPU 工作可能重叠，API 没有要求两者之和等于 total。无法可靠测到分项时，继续使用 `reportActualWorkDuration(long)` 比填入猜测值更稳妥；native 实现会把这个单值映射为 total 和 CPU duration，start 与 GPU duration 置 0。

## 7. NDK：复用 session，并检查返回码

NDK 基础 API 从 API 33 可用。下面的骨架把初始化、单周期报告和释放分开，目的是避免每个周期重复创建 Binder/HAL session。调用者应保证三个函数在约定的 owner thread 上串行执行。

```cpp
#include <android/performance_hint.h>
#include <time.h>
#include <unistd.h>

struct HintLoop {
    APerformanceHintSession* session = nullptr;
};

static int64_t monotonic_nanos() {
    timespec ts{};
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return static_cast<int64_t>(ts.tv_sec) * 1'000'000'000LL + ts.tv_nsec;
}

bool init_hint_loop(HintLoop* loop, int64_t target_ns) {
    APerformanceHintManager* manager = APerformanceHint_getManager();
    if (manager == nullptr) {
        return false;
    }

    const pid_t owner_tid = gettid();
    loop->session =
            APerformanceHint_createSession(manager, &owner_tid, 1, target_ns);
    return loop->session != nullptr;
}

int report_hint_cycle(HintLoop* loop, int64_t cycle_start_ns) {
    if (loop->session == nullptr) {
        return 0;
    }
    const int64_t actual_ns = monotonic_nanos() - cycle_start_ns;
    return APerformanceHint_reportActualWorkDuration(loop->session, actual_ns);
}

void close_hint_loop(HintLoop* loop) {
    if (loop->session != nullptr) {
        APerformanceHint_closeSession(loop->session);
        loop->session = nullptr;
    }
}
```

`APerformanceHint_reportActualWorkDuration()` 返回 0 才表示本次调用成功；常见失败包括参数错误和与服务通信失败。session 创建失败不能阻断业务。API 36 设备还可以先用 `APerformanceHint_isFeatureSupported(APERF_HINT_SESSIONS)` 探测支持情况，API 33—35 则直接处理 manager/session 为空和函数返回码。

### 7.1 Java 与 native 共用同一个 Session

API 36 的 `APerformanceHint_borrowSessionFromJava()` 解决同进程 JNI 边界上的重复建会话问题。下面的 JNI 片段只演示所有权规则。

```cpp
APerformanceHintSession* borrowed =
        APerformanceHint_borrowSessionFromJava(env, java_session);
int rc = APerformanceHint_updateTargetWorkDuration(borrowed, new_target_ns);
```

返回的是 Java `Session` 背后的借用指针，native 代码不能对它调用 `APerformanceHint_closeSession()`。指针只在对应 Java 对象仍然有效时可用，Java 侧关闭 session 后也不能继续借用。这是同进程对象桥接，不是跨进程 session 共享。

## 8. 启动阶段怎么判断是否适用

`PerformanceHintManager` 出现在启动章节，容易被理解成通用启动优化 API。判断标准应放在工作负载形态上：

- 一次性的类加载、依赖初始化和首屏对象构造没有稳定周期，应先用 Perfetto、Macrobenchmark、Baseline Profile 和 AndroidX App Startup 的依赖图找出串行工作。
- 启动后立即进入且会持续运行的帧生产、相机处理或音视频循环，具备长期线程、明确 target 和逐周期 actual，才可能适合建立 session。
- 启动 worker pool 如果只执行一次短任务，session 创建与校验本身还会增加一次控制面开销。把创建操作简单地 `Handler.post()` 到主线程，也没有改变负载不具备周期性的事实。
- session 的关闭应跟 owner 组件或工作循环的终止条件一致。`onTrimMemory()` 只表示内存压力级别，不能代替精确的工作生命周期。

启动顺序与依赖声明由 AndroidX App Startup 或应用自己的初始化框架处理；后台任务执行时机由 `JobScheduler`/`WorkManager` 处理。Performance Hint 只描述一组正在运行的线程，希望在多久内完成一个周期。

## 9. Power efficiency、温控与厂商差异

`setPreferPowerEfficiency(true)` 表示这组线程可以安全地优先考虑能效。`HintManagerService` 将状态传给 session mode，Power HAL 决定怎样采用。接口没有规定必须降频、迁核或使用某种 EAS 策略，因此不能把这个调用写成确定的频率选择结果。

能效模式适合有余量的稳定负载。接近 deadline 的交互循环若盲目开启，可能扩大尾延迟；设备温度高或全局功耗预算受限时，系统也可能覆盖应用期望。测试时应同时记录 thermal status、功耗、帧/任务耗时与 CPU 调度数据，不要只比较平均频率。

## 10. Android 17 上如何观察

### 10.1 `dumpsys performance_hint`

下面的命令用于确认设备能力、活跃 session、线程集合和暂停状态。

```bash
adb shell dumpsys performance_hint
```

`android-17.0.0_r1` 的 `HintManagerService.dump()` 会输出 `HintSessionPreferredRate`、`MaxGraphicsPipelineThreadsCount`、`Hint Session Support`，并按 UID 列出活跃 session。每个 session 可看到 PID、UID、TIDs、Tag、`TargetDurationNanos`、`AllowedByProcState`、`ForcePaused`、`PowerEfficient` 和 `GraphicsPipeline`。Android 17 还包含 CPU/GPU headroom 支持信息；字段是否有有效数据取决于设备 Power HAL。

### 10.2 Perfetto 中有直接的 ADPF counter

`native/android/performance_hint.cpp` 会通过 ATrace 写入以下名称，`<id>` 是 session 的 trace ID：

- `ADPF Session <id> TID: <tid>`：值为 1 表示 TID 当前属于 session，移除后写 0。
- `ADPF Session <id> target duration`：当前目标耗时，单位为 ns。
- `ADPF Session <id> actual duration`：最近一次报告的总耗时，单位为 ns。
- `ADPF Session <id> batch size`：客户端缓存、限流或发送后的报告批量大小。
- `ADPF Session <id> power efficiency mode`：能效模式开关。
- `ADPF Session <id> graphics pipeline mode`：图形流水线模式开关。
- `Sending load hint`：workload hint 发送时的 instant event。

抓取 Perfetto 时应包含目标进程的 atrace 事件，并同时打开 `sched`、CPU frequency、power/thermal 等轨道。分析顺序是先确认 session 的 TID、target 和 actual counter 都存在，再把相同时间窗口内的 runnable、CPU 运行位置、频率、deadline miss 与温控状态放在一起看。

频率在 hint 后变化只说明时间相关，不能单凭一条 trace 证明因果。可靠验证至少需要同一设备、同一温控起点、相同 workload 的 A/B 多轮测试，并报告 P50/P90/P99 或 deadline miss，而不是挑一张“看起来升频了”的截图。

### 10.3 statsd 是系统遥测，不是应用查询接口

`HintManagerService` 写入 `PERFORMANCE_HINT_SESSION_REPORTED`，字段包括 UID、session ID、target duration、TID 数量、session tag、power-efficiency、graphics-pipeline，以及当前固定为 false 的 audio 标记。`ADPF_SESSION_SNAPSHOT` 是 pulled atom，按 UID/tag 汇总最大并发 session、最大线程数、能效 session 数、target duration 列表、graphics-pipeline session 数与 audio session 数。

这些 atom 用于平台和设备侧统计。普通应用不能把它们当成实时调试 API；开发阶段优先用 `dumpsys` 和 Perfetto。

## 11. 与相邻机制的边界

| 机制 | 回答的问题 | 时间尺度 | 应用能提供什么 |
|---|---|---|---|
| `PerformanceHintManager` | 正在运行的周期工作希望多快完成 | 帧/周期级，通常为 ms | TID、target、actual、能效或图形模式 |
| `JobScheduler` / `WorkManager` | 延迟后台工作何时满足执行条件 | 秒到小时 | 约束、期限、重试与持久化需求 |
| Linux scheduler | runnable 线程如何获得 CPU | 调度 tick 与唤醒级 | nice/优先级等受限属性；应用不能直接下达频点 |
| AndroidX App Startup | 进程内初始化依赖按什么顺序执行 | 进程启动阶段 | `Initializer` 依赖关系与延迟初始化选择 |

这四者可以出现在同一个应用里，但职责互不替代。尤其不要把不存在于 Android 17 公开平台和 AOSP 源码中的“ML TaskScheduler”放进 Performance Hint 的数据路径。

## 12. 接入检查表

1. 用 Perfetto 确认候选工作是周期性的，并找出关键路径上的长期线程。
2. 在每个 worker 内记录 `Process.myTid()`，核对线程属于当前进程线程组。
3. 用业务 deadline 定义 target；Java API 31—34 可用 `System.nanoTime()` 测量持续时间，API 35+ 的 `WorkDuration` 时间戳用 `uptimeNanos()`，NDK 使用 `CLOCK_MONOTONIC`。
4. session 为空或 NDK 返回错误时保持业务可运行；不能把 ADPF 当硬依赖。
5. 将 session 调用固定在 owner thread，线程集合改变时完整替换 TID 列表。
6. 先从默认模式做 A/B，再评估 `setPreferPowerEfficiency()` 或 API 36 graphics-pipeline 扩展。
7. 同时检查 ADPF counter、`sched`、CPU frequency、thermal 与业务 deadline；单一指标不足以下结论。
8. 工作循环结束时关闭 session，关闭后清空引用并停止后续报告。

## 交叉阅读

- [8.33 Android 17 模块化启动框架：依赖图、按需初始化与进程边界](./8.33-android17-modular-startup-framework-dependency-graph.md)：处理应用初始化依赖和延迟初始化。
- [8.36 AndroidX Benchmark 1.4.1 Startup Insights](./8.36-android17-startup-insights.md)：用 Macrobenchmark 和 trace 观察启动问题。
- [2.18 Adaptive Refresh Rate 与动态帧率控制](../ch02-rendering/18-adaptive-refresh-rate.md)：继续阅读刷新率、VSync 与帧预算之间的关系。

## 源码与官方资料

- [PerformanceHintManager.java（android-17.0.0_r1）](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/os/PerformanceHintManager.java)
- [WorkDuration.java（android-17.0.0_r1）](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/os/WorkDuration.java)
- [Java JNI：android_os_PerformanceHintManager.cpp](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/jni/android_os_PerformanceHintManager.cpp)
- [Native 客户端与 FMQ/ATrace 实现](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/native/android/performance_hint.cpp)
- [HintManagerService.java（android-17.0.0_r1）](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/services/core/java/com/android/server/power/hint/HintManagerService.java)
- [NDK performance_hint.h（android-17.0.0_r1）](https://android.googlesource.com/platform/frameworks/native/+/android-17.0.0_r1/include/android/performance_hint.h)
- [Power HAL IPowerHintSession AIDL](https://android.googlesource.com/platform/hardware/interfaces/+/android-17.0.0_r1/power/aidl/android/hardware/power/IPowerHintSession.aidl)
- [PerformanceHintManager API reference](https://developer.android.com/reference/android/os/PerformanceHintManager)
- [PerformanceHintManager.Session API reference](https://developer.android.com/reference/android/os/PerformanceHintManager.Session)
- [ADPF 指南](https://developer.android.com/games/optimize/adpf)
- [ADPF 最佳实践](https://developer.android.com/games/optimize/adpf/best-practices-adpf)
