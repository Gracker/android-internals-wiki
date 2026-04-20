---
title: "ProfilingManager 系统触发式性能追踪"
chapter: "8.8"
section: "8.8"
status: ready-for-review
applicable_versions: "Android 16 (API 36) - Android 17 (API 37)"
tags: [profiling-manager, system-triggered, cold-start, anr, tracing, performance-monitoring]
related_chapters: ["8.2", "9.3", "13.7"]
created_by: "task2a-knowledge-gap"
created_date: "2026-04-10"
gap_source: "研究素材"
confidence: medium
sources:
  - type: blog
    path: "Android 16/17 ProfilingManager 系统触发式性能追踪"
    title: "系统触发式性能追踪机制"
    date: "2026-04-01"
  - type: official
    path: "https://developer.android.com/reference/android/os/ProfilingManager"
    title: "ProfilingManager API Reference"
    date: "2026"
  - type: official
    path: "https://developer.android.com/reference/android/os/ProfilingTrigger"
    title: "ProfilingTrigger API Reference"
    date: "2026"
  - type: official
    path: "https://developer.android.com/reference/android/os/ProfilingResult"
    title: "ProfilingResult API Reference"
    date: "2026"
  - type: aosp
    path: "packages/modules/Profiling/framework/java/android/os/ProfilingManager.java"
  - type: aosp
    path: "packages/modules/Profiling/framework/java/android/os/ProfilingTrigger.java"
  - type: aosp
    path: "packages/modules/Profiling/framework/java/android/os/ProfilingResult.java"
  - type: aosp
    path: "packages/modules/Profiling/service/java/com/android/os/profiling/ProfilingService.java"
pipeline_stage: task9_pending
task6_state: reviewed
task9_state: pending
task2b_state: fixed
reviewed_by: "openclaw-task6"
reviewed_date: "2026-04-20"
task6_result: pass-light-edit
task9_result: needs-rework
task2b_result: fixed
---

# ProfilingManager 系统触发式性能追踪

## 为什么要了解系统触发式性能追踪

线上冷启动慢、偶发 ANR、一次性 OOM，最麻烦的地方不是不会分析，而是问题发生时根本没开 Trace。ProfilingManager 的 system-triggered profiling 解决的正是这个空档。我们先把关心的系统事件注册给系统，等事件真的发生时，再由系统把结果放到应用目录，回调给应用自己处理。

对启动优化来说，这让 `Activity.reportFullyDrawn()` 前后的启动收尾不再只能靠人工复现。对 ANR 排查来说，我们拿到的也不再只是 `traces.txt` 的定格画面，而是一份围绕触发时刻保存下来的 trace。对 OOM 来说，返回物甚至不是 trace，而是 Java heap dump。只有把这些触发器、产物类型、版本边界和结果交付方式拆开，后面分析时才知道该用什么工具、看什么轨道。

<!-- outline-start -->
## 要点

### 🔹 ProfilingManager 的角色与源码位置
- `ProfilingManager` 本体在 Android 15 提供手动请求能力，system-triggered profiling 从 Android 16 才开始可用
- 公开 API 位于 `packages/modules/Profiling/framework/java/android/os/`
- 服务端实现位于 `packages/modules/Profiling/service/java/com/android/os/profiling/`

### 🔹 trigger → artifact → stop condition → result delivery
- `APP_FULLY_DRAWN`、`ANR`、`COLD_START`、`OOM`、`KILL_EXCESSIVE_CPU_USAGE` 返回的工件并不相同
- 结果统一通过 `registerForAllProfilingResults()` 的全局 listener 取回
- `ProfilingResult#getResultFilePath()` 是结果文件入口，`getTriggerType()` 用来区分触发器

### 🔹 Android 16、36.1、17 的版本分层
- API 36：`APP_FULLY_DRAWN=1`、`ANR=2`
- extension 36.1：`APP_REQUEST_RUNNING_TRACE=3`、`KILL_FORCE_STOP=4`、`KILL_RECENTS=5`、`KILL_TASK_MANAGER=6`
- API 37：`OOM=7`、`ANOMALY=8`、`KILL_EXCESSIVE_CPU_USAGE=9`、`COLD_START=10`、`APP_COMPAT=11`

### 🔹 冷启动、ANR、OOM 的使用方式
- 冷启动要分清 `APP_FULLY_DRAWN` 和 `COLD_START`
- ANR 结果是 running system trace snapshot
- OOM 结果是 Java heap dump，不是 LMK / lmkd 现场

### 🔹 工具中的观测入口
- `.perfetto-trace` 结果走 Perfetto UI
- Java heap dump 结果按 heap dump 工具链分析
- 每类结果都要先看 artifact，再决定分析工具

### 🔹 常见误区
- 不要把 `APP_FULLY_DRAWN` 写成 `COLD_START`
- 不要把 OOM 写成 LMK
- 不要把系统触发结果写成 request-scoped listener 可接收
<!-- outline-end -->

## 核心机制

### ProfilingManager 在这里到底负责什么

Android 15 引入 `ProfilingManager`，先解决“应用怎样在公开设备上请求 profiling”这个问题。到了 Android 16，系统又在这个接口上补了 `addProfilingTriggers(List<ProfilingTrigger>)`，让应用可以提前声明自己关心哪些系统事件。事件真的发生时，系统把结果文件落到应用目录，再把文件路径和触发器类型通过 `ProfilingResult` 回传。

[已验证: 官方文档, developer.android.com/reference/android/os/ProfilingManager]
[已验证: AOSP main, packages/modules/Profiling/framework/java/android/os/ProfilingManager.java]

源码位置也要先摆正。公开 API 不在 `frameworks/base/core/java/android/os/`，而在 Mainline Profiling 模块：`packages/modules/Profiling/framework/java/android/os/ProfilingManager.java`、`ProfilingTrigger.java`、`ProfilingResult.java`。服务端实现位于 `packages/modules/Profiling/service/java/com/android/os/profiling/ProfilingService.java`。这说明 ProfilingManager 不是老式 framework 服务路径上的普通类。

[已验证: AOSP main, packages/modules/Profiling/service/java/com/android/os/profiling/ProfilingService.java]

### 结果是怎么回来的

system-triggered profiling 有一个容易写错的地方，结果不是发给某一次单独请求的 listener，而是只会发给全局 listener。公开文档和 AOSP 注释都写得很直白，`registerForAllProfilingResults(Executor, Consumer<ProfilingResult>)` 是接收 system-triggered profiling 结果的唯一公开入口。`addProfilingTriggers()` 只是注册触发器，不负责直接把结果塞回调用现场。

拿到 `ProfilingResult` 之后，我们先看两件事：

1. `getTriggerType()`，分辨是 `APP_FULLY_DRAWN`、`ANR`、`OOM` 还是别的触发器
2. `getResultFilePath()`，拿到真正的结果文件路径

如果这两个字段都没先看清，后面的分析工具就很容易选错。

[已验证: 官方文档, developer.android.com/reference/android/os/ProfilingResult]
[已验证: 官方文档, developer.android.com/reference/android/os/ProfilingManager]

### 最小可用流程

下面这段代码只做一件事，注册全局结果回调，再添加两个 Android 16 就能使用的触发器。它没有把上一版草稿里那些虚构回调、虚构 Builder 和伪字段再写回来。

```java
import android.content.Context;
import android.os.ProfilingManager;
import android.os.ProfilingResult;
import android.os.ProfilingTrigger;

import java.util.List;
import java.util.concurrent.Executor;
import java.util.function.Consumer;

public final class TriggeredProfilingRegistrar {
    private final ProfilingManager profilingManager;
    private final Executor executor;
    private final Consumer<ProfilingResult> listener;

    public TriggeredProfilingRegistrar(Context context, Executor executor) {
        this.profilingManager = context.getSystemService(ProfilingManager.class);
        this.executor = executor;
        this.listener = result -> {
            int triggerType = result.getTriggerType();
            String resultFilePath = result.getResultFilePath();
            // 这里按 triggerType 分发到冷启动、ANR、OOM 各自的离线分析流程
        };
    }

    public void register() {
        profilingManager.registerForAllProfilingResults(executor, listener);

        profilingManager.addProfilingTriggers(List.of(
                new ProfilingTrigger.Builder(ProfilingTrigger.TRIGGER_TYPE_APP_FULLY_DRAWN)
                        .setRateLimitingPeriodHours(24)
                        .build(),
                new ProfilingTrigger.Builder(ProfilingTrigger.TRIGGER_TYPE_ANR)
                        .setRateLimitingPeriodHours(24)
                        .build()
        ));
    }
}
```

这段代码还顺带说明了两个边界。其一，`setRateLimitingPeriodHours()` 是“同一种 trigger 两次结果之间最短间隔”的应用侧约束，0 代表不加应用侧限流。其二，同一种 trigger 同时只能保留一个注册项，新注册会覆盖旧注册。

[已验证: 官方文档, developer.android.com/reference/android/os/ProfilingTrigger.Builder]
[已验证: AOSP main, packages/modules/Profiling/framework/java/android/os/ProfilingManager.java]

### trigger、产物和停止条件要分开看

这一节最容易混淆的地方，是把所有 trigger 都写成“抓一份 Trace”。公开 API 不是这么设计的。

| Trigger | 版本 | 系统返回物 | 何时触发 | 停止条件 / 备注 |
|---|---|---|---|---|
| `TRIGGER_TYPE_APP_FULLY_DRAWN = 1` | API 36 | running system trace snapshot | 冷启动里调用 `Activity.reportFullyDrawn()` 之后 | 适合复盘启动尾段 |
| `TRIGGER_TYPE_ANR = 2` | API 36 | running system trace snapshot | 系统已经识别到 ANR，但还没按公开契约结束该应用时 | 文档强调它不等同于“应用一定已被杀” |
| `TRIGGER_TYPE_COLD_START = 10` | API 37 | newly started system trace + stack sampling | 应用冷启动尽早阶段，且 `ApplicationStartInfo.getStartType()` 为 `START_TYPE_COLD` | 调用 `reportFullyDrawn()` 时停止；没有调用时默认约 5 秒停止 |
| `TRIGGER_TYPE_OOM = 7` | API 37 | Java heap dump | 应用抛出 `OutOfMemoryError` | 自定义 `UncaughtExceptionHandler` 必须继续调用默认 handler |
| `TRIGGER_TYPE_KILL_EXCESSIVE_CPU_USAGE = 9` | API 37 | running system trace snapshot | 应用因 `ApplicationExitInfo.REASON_EXCESSIVE_RESOURCE_USAGE` 被系统杀掉 | 文档没有公开 CPU 阈值 |

这张表比散落的清单更有用，因为后续分析的入口已经固定下来了。`APP_FULLY_DRAWN` 和 `ANR` 的结果都可以走 Perfetto UI，`OOM` 该走 heap dump 分析，`COLD_START` 既有 system trace，也有 stack sampling。

[已验证: 官方文档, developer.android.com/reference/android/os/ProfilingTrigger]

### `APP_FULLY_DRAWN` 和 `COLD_START` 不是同一件事

Android 16 的 `TRIGGER_TYPE_APP_FULLY_DRAWN = 1`，语义是“冷启动里已经调用 `Activity.reportFullyDrawn()`，系统给出一份 running system trace snapshot”。它更像在启动完成点拿一张快照，帮助我们比对启动后段和 fully drawn 时刻前后的线程活动。

Android 17 的 `TRIGGER_TYPE_COLD_START = 10` 则往前迈了一步。它要求系统在应用冷启动尽早阶段就开始录制，并持续到 `reportFullyDrawn()`，或者在没有调用 `reportFullyDrawn()` 时按默认 5 秒截止。公开文档还说明这类 trigger 使用 discard buffer，缓冲区满时会丢新事件，优先保留最早阶段的 tracepoint。写启动章节时，如果把这两个 trigger 混成一个名字，读者对采样窗口的判断就会直接错位。

[已验证: 官方文档, developer.android.com/reference/android/os/ProfilingTrigger]

### OOM 说的是 Java 层 OOM，不是 LMK

`TRIGGER_TYPE_OOM` 的公开语义非常具体，应用发生 Out Of Memory Exception 时，系统返回 Java heap dump。它和 `lmkd`、LMK、`Low Memory Killer` 不是一条问题路径。LMK 处理的是系统内存压力下的杀进程策略，章节 §4.4 已经单独展开；这里说的是应用自己因为堆分配失败抛出 OOM。

这里还有一个经常漏写的条件。官方文档明确要求，如果应用自定义了 `Thread.UncaughtExceptionHandler`，它仍然要继续调用默认的 `UncaughtExceptionHandler`。不然这个 trigger 不会生效。

[已验证: 官方文档, developer.android.com/reference/android/os/ProfilingTrigger]

### ANR 和 excessive CPU 也不要发明内部阈值

`TRIGGER_TYPE_ANR` 的公开定义是“ANR 已被识别，但系统还没准备按公开契约结束该应用”。文档没有给出上一版草稿里那组预警数值。`TRIGGER_TYPE_KILL_EXCESSIVE_CPU_USAGE` 也只公开到了“应用因 `ApplicationExitInfo.REASON_EXCESSIVE_RESOURCE_USAGE` 被杀后返回 running system trace snapshot”这一层，没有把 CPU 百分比、持续时间、采样窗口当成 API 契约。

所以这一类章节不该写成一组固定百分比、固定时长和固定预警窗口。如果没有源码、实验或 device_config 证据支撑，那就是把内部策略猜想写成公开合同。

[已验证: 官方文档, developer.android.com/reference/android/os/ProfilingTrigger]

## 在工具中的表现与验证路径

### 冷启动样例：`APP_FULLY_DRAWN` / `COLD_START`

对冷启动来说，我们先确认返回物是不是 `.perfetto-trace`，再用 Perfetto UI 打开。`APP_FULLY_DRAWN` 更适合复盘启动收尾阶段，`COLD_START` 更适合看进程创建后的完整启动窗口。

[图：`TRIGGER_TYPE_APP_FULLY_DRAWN` 返回的 `.perfetto-trace` 在 Perfetto UI 中的观测示意。标出应用主进程、主线程 `Choreographer#doFrame`、RenderThread、SurfaceFlinger 合成轨，并在启动尾段比对 `reportFullyDrawn()` 附近的最后几帧。]

[图：`TRIGGER_TYPE_COLD_START` 返回的 system trace + stack sampling 结果示意。标出应用冷启动早期的进程创建、主线程首个长任务、`reportFullyDrawn()` 停止点，以及默认 5 秒停止的回退边界。]

我们分析这两类结果时，入口不在跑一条固定 SQL，而在先确定时间窗口，再看线程状态、Binder 等待、渲染帧和系统服务干预。这一节原来的伪 SQL 已经删掉，因为它把 `reportFullyDrawn()`、固定表名和时间字面量硬拼在一起，和真实 schema 不是一回事。

### ANR 样例：running system trace snapshot

ANR 结果同样是 `.perfetto-trace`，但目标从启动耗时换成了“找到超时前的阻塞对象”。我们通常会把主线程、Binder 线程池、持锁线程、`system_server` 放在一起看，而不是只盯着一条主线程 slice。

[图：`TRIGGER_TYPE_ANR` 返回的 running system trace 示意。标出应用主线程 blocked 状态、对应的 owner 线程、同步 Binder 调用等待区间，以及 `system_server` 中可能卡住的服务线程。]

这种结果比单独的 `traces.txt` 多了一段历史信息。我们可以把 `traces.txt` 当成终点快照，把 system-triggered trace 当成“终点之前发生了什么”。

### OOM 样例：Java heap dump

`TRIGGER_TYPE_OOM` 不该塞回 Perfetto trace 段落里一起写。它返回的是 Java heap dump，分析目标也从线程调度切到“谁持有对象、谁把堆顶满了、是否存在大对象或意外 retained path”。

[图：`TRIGGER_TYPE_OOM` 返回的 Java heap dump 分析示意。标出 dominator tree 中占用最大的对象组、retained size 最高的引用路径，以及触发 OOM 前最后一次大分配对应的业务对象。]

如果一个章节把 OOM、ANR、cold start 全都说成“自动抓 Trace”，读者在工具选择上就已经走偏了。

## 与其他机制的关系

### 和 `Activity.reportFullyDrawn()` 的关系

`APP_FULLY_DRAWN` 与 `COLD_START` 都和 `Activity.reportFullyDrawn()` 有直接关系。前者在调用之后返回 running trace snapshot，后者把它当作录制截止点之一。启动文章里谈 fully drawn 时，不能只把它当埋点 API；到了 ProfilingManager 这里，它还是 system-triggered profiling 的停止和取样边界。

### 和 `ApplicationStartInfo` 的关系

`COLD_START` 的公开文档把触发前提说得很明确，`ApplicationStartInfo.getStartType()` 必须是 `START_TYPE_COLD`。这让 ProfilingManager 和启动类型判断连到一起。我们在 §8.2 里分析冷启动时，可以用 `ApplicationStartInfo` 先分流，再决定是否注册或解释 cold-start profiling 结果。

### 和 `ApplicationExitInfo` 的关系

`KILL_EXCESSIVE_CPU_USAGE` 的判断依据不是我们手写的 CPU 百分比，而是 `ApplicationExitInfo.getReason() == REASON_EXCESSIVE_RESOURCE_USAGE`。也就是说，ProfilingManager 这里拿到的是系统已经做出 kill 判断后的 profiling 结果，而不是一个持续轮询 CPU 的前台预警器。

## 版本演进

| 版本 | 能力面 | 这一版该怎么理解 |
|---|---|---|
| Android 15 (API 35) | `ProfilingManager` 基础请求能力 | 重点是 `requestProfiling()` 和结果回调，本节的 system-triggered profiling 还没出现 |
| Android 16 (API 36) | `addProfilingTriggers()`、`APP_FULLY_DRAWN=1`、`ANR=2` | 首次把“由系统条件触发结果采集”放进公开 API |
| Android 16 extension 36.1 | `APP_REQUEST_RUNNING_TRACE=3`、`KILL_FORCE_STOP=4`、`KILL_RECENTS=5`、`KILL_TASK_MANAGER=6` | 这几类都属于 running system trace snapshot，偏系统事件补充 |
| Android 17 (API 37) | `OOM=7`、`ANOMALY=8`、`KILL_EXCESSIVE_CPU_USAGE=9`、`COLD_START=10`、`APP_COMPAT=11` | 触发器不再只返回 running trace，开始出现新开 trace、stack sampling、heap dump 和“artifact varies” 这类更细分的模型 |

`ANOMALY` 和 `APP_COMPAT` 也要点一下。文档没有把它们都固定成某一种结果文件，而是明确写了 artifact 会按 anomaly 类型变化，`ProfilingResult#getTag()` 里会带额外信息。写版本表时，如果把 Android 17 只概括成 OOM 和 excessive CPU，就把 public surface 少写了一截。

[已验证: 官方文档, developer.android.com/reference/android/os/ProfilingTrigger]

## 常见问题与误区

### 误区 1：`APP_FULLY_DRAWN` 就是 `COLD_START`

不是一个东西。`APP_FULLY_DRAWN` 是 API 36 的 running trace snapshot，`COLD_START` 是 API 37 的“尽早开始录制，再到 fully drawn 停止”的完整窗口。两者的采样范围不同，常量值也不同。

### 误区 2：OOM trigger 等于 LMK 现场

`TRIGGER_TYPE_OOM` 处理的是 Java 层 OOM 异常，返回 Java heap dump。LMK 和 `lmkd` 看的是系统内存压力和杀进程策略，应该回到 §4.4 去分析。

### 误区 3：注册 trigger 就能直接在本次回调里拿到结果

system-triggered profiling 的结果只会通过 `registerForAllProfilingResults()` 的全局 listener 回来。把它写成 request-scoped listener，或者再造一个并不存在的注册接口，应用一上手就会编译失败。

### 误区 4：系统公开了 ANR / CPU 的内部阈值

公开 API 没有给出上一版草稿里那组固定阈值。没有源码、实验或 device_config 证据时，章节里就不该擅自补这些数字。

## 参考资料

- 官方文档：`https://developer.android.com/reference/android/os/ProfilingManager`
- 官方文档：`https://developer.android.com/reference/android/os/ProfilingTrigger`
- 官方文档：`https://developer.android.com/reference/android/os/ProfilingResult`
- AOSP：`packages/modules/Profiling/framework/java/android/os/ProfilingManager.java`
- AOSP：`packages/modules/Profiling/framework/java/android/os/ProfilingTrigger.java`
- AOSP：`packages/modules/Profiling/framework/java/android/os/ProfilingResult.java`
- AOSP：`packages/modules/Profiling/service/java/com/android/os/profiling/ProfilingService.java`
