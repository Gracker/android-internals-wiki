---

title: "ProfilingManager 系统触发式性能追踪"
chapter: '8.10'
section: '8.10'
status: "ready-for-review"
pipeline_stage: "task6_pending"
applicable_versions: "Android 15 (API 35) - Android 17 (API 37)"
tags: [responsiveness, latency, launch]
confidence: medium
last_verified: '2026-06-24'
last_verified_against: "AOSP android-17.0.0_r1 + Android Developers + Task9 audit 2026-06-24 (源码路径修正; AnomalyDetectorService 非 AOSP 公开组件已更正)"
created_by: task2a-knowledge-gap
created_date: '2026-04-10'
gap_source: 研究素材
path: "https://developer.android.com/reference/android/os/ProfilingManager"
last_task9_audit: "2026-06-23"
task6_state: "revisiting"
task9_state: "pending"
task2b_state: "fixed"
task2b_result: "fixed"
last_task2b_lite_at: '2026-06-23'
repaired_date: '2026-05-09'
repaired_by: openclaw-task2b
reviewed_by: openclaw-task6
reviewed_date: 2026-06-24
task6_result: pass-light-edit
task6_review_notes: "2026-06-24 Task6 四轮复审(Task2B fix后回归): 常量值一致性已修复。本轮修复3处编辑残留(元叙述)和2处否定-纠正句式超限,判定pass-light-edit。等待Task9复审。"
task9_result: needs-rework
verifier_pass: "2026-06-23T11:26:00+08:00"
task9_reviewed_date: 2026-06-24
task9_reviewed_by: openclaw-task9
last_task9_at: "2026-06-23T13:20:00+08:00"
last_task6_audit: '2026-06-24'
deepseek_cn_review_state: done
last_deepseek_cn_review_at: 2026-06-08
last_task9_autofix_at: "2026-06-23"
last_task6_at: "2026-06-24T09:15:00+08:00"
last_task6_review_log: "logs/review/2026-06-24-09-review.md"
last_task2b_at: "2026-06-24T08:57:10+08:00+08:00"
task9_review_notes: "2026-06-23 Task9 deep-review: P0 事实错误 - AOSP 源码路径不存在，无法验证章节技术准确性；P1 重要缺失 - 交叉引用错误，引用不存在章节；P2 建议改进 - 缺少实际数据支撑和案例。2026-06-23 已写入 queue.json 要求 Task2B 重构章节。"
last_task9_review_log: "logs/deep-review/2026-06-23-13-deep-review.md"
---

----


# ProfilingManager 系统触发式性能追踪

## 为什么要了解系统触发式性能追踪

线上冷启动慢、偶发 ANR、一次性 OOM，最麻烦的地方不是不会分析，而是问题发生时没有开启 Trace。ProfilingManager 的 system-triggered profiling 解决的正是这个空档。我们先把关心的系统事件注册给系统，等事件发生时，再由系统把结果放到应用目录，回调给应用自己处理。

对启动优化来说，这让 `Activity.reportFullyDrawn()` 前后的启动收尾不再只能靠人工复现。对 ANR 排查来说，我们拿到的也不再只是 `traces.txt` 的定格画面，而是一份围绕触发时刻保存下来的 trace。对 OOM 来说，返回物是 Java heap dump，与其他 trigger 返回的 trace 不同。

Android 17 新增的 `TRIGGER_TYPE_ANOMALY` 把这个能力又往前推了一步：系统检测到异常行为时，可以根据 anomaly-detector 规则触发日志或 profiling。MemoryLimiter 的 anon+swap 超限路径会在延迟 kill 目标进程之前先触发 ANOMALY；binder spam 这类规则则不等同于"马上杀进程"的信号。排查"应用被杀但不知道为什么"的问题时，ANOMALY 能补上部分进程终止前的现场；但收到结果后仍要看 tag 和返回物，不能把所有 ANOMALY 都按 kill 前 trace 处理。

只有把这些触发器、产物类型、版本边界和结果交付方式拆开，后面分析时才知道该用什么工具、看什么轨道。

<!-- outline-start -->
## 要点

### 🔹 ProfilingManager 的角色与源码位置
- `ProfilingManager` 本体在 Android 15 提供手动请求能力,system-triggered profiling 从 Android 16 才开始可用
- 公开 API 位于 `packages/modules/Profiling/framework/android/os/`
- 服务端实现位于 `packages/modules/Profiling/service/java/com/android/os/profiling/`

### 🔹 trigger → artifact → stop condition → result delivery
- `APP_FULLY_DRAWN`、`ANR`、`COLD_START`、`OOM`、`KILL_EXCESSIVE_CPU_USAGE` 返回的工件并不相同
- 结果统一通过 `registerForAllProfilingResults()` 的全局 listener 取回
- `ProfilingResult#getResultFilePath()` 是结果文件入口,`getTriggerType()` 用来区分触发器

### 🔹 Android 16、36.1、17 的版本分层
- API 36:`APP_FULLY_DRAWN=1`、`ANR=2`
- extension 36.1:`APP_REQUEST_RUNNING_TRACE=3`、`KILL_FORCE_STOP=4`、`KILL_RECENTS=5`、`KILL_TASK_MANAGER=6`,运行时还要做 Extension SDK gating
- API 37:`OOM=7`、`ANOMALY=8`、`KILL_EXCESSIVE_CPU_USAGE=9`、`COLD_START=10`、`APP_COMPAT=11`

### 🔹 冷启动、ANR、OOM 的使用方式
- 冷启动要分清 `APP_FULLY_DRAWN` 和 `COLD_START`
- ANR 结果是 running system trace snapshot
- OOM 结果是 Java heap dump,不是 LMK / lmkd 现场

### 🔹 工具中的观测入口
- `.perfetto-trace` 结果走 Perfetto UI
- Java heap dump 结果按 heap dump 工具链分析
- 每类结果都要先看 artifact,再决定分析工具

### 🔹 常见误区
- 不要把 `APP_FULLY_DRAWN` 写成 `COLD_START`
- 不要把 OOM 写成 LMK
- 不要把系统触发结果写成 request-scoped listener 可接收
<!-- outline-end -->

## 核心机制

### ProfilingManager 在这里到底负责什么

Android 15 引入 `ProfilingManager`,先解决"应用怎样在公开设备上请求 profiling"这个问题。到了 Android 16,系统又在这个接口上补了 `addProfilingTriggers(List<ProfilingTrigger>)`,让应用可以提前声明自己关心哪些系统事件。事件真的发生时,系统把结果文件落到应用目录,再把文件路径和触发器类型通过 `ProfilingResult` 回传。

源码位置也要先摆正。公开 API 位于 Mainline Profiling 模块：`packages/modules/Profiling/framework/android/os/ProfilingManager.java`、`ProfilingTrigger.java`、`ProfilingResult.java`。服务端实现位于 `packages/modules/Profiling/service/java/com/android/os/profiling/ProfilingService.java`。这说明 ProfilingManager 不是老式 framework 服务路径上的普通类。

### 结果是怎么回来的

system-triggered profiling 有一个容易写错的地方，结果只会发给全局 listener，不会发给某一次单独请求的 listener。公开文档和 AOSP 注释都写得很直白，`registerForAllProfilingResults(Executor, Consumer<ProfilingResult>)` 是接收 system-triggered profiling 结果的唯一公开入口。`addProfilingTriggers()` 只是注册触发器，不负责直接把结果塞回调用现场。

拿到 `ProfilingResult` 之后，我们先看两件事：

1. `getTriggerType()`，分辨是 `APP_FULLY_DRAWN`、`ANR`、`OOM` 还是别的触发器
2. `getResultFilePath()`，拿到结果文件路径

如果这两个字段都没先看清,后面的分析工具就很容易选错。

### 最小可用流程

下面这段代码只做一件事,注册全局结果回调,再添加两个 Android 16 就能使用的触发器。
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

这段代码还顺带说明了两个边界。其一，`setRateLimitingPeriodHours()` 是"同一种 trigger 两次结果之间最短间隔"的应用侧约束，0 代表不加应用侧限流。其二，同一种 trigger 同时只能保留一个注册项，新注册会覆盖旧注册。

### trigger、产物和停止条件要分开看

这一节最容易混淆的地方，是把所有 trigger 都写成"抓一份 Trace"。公开 API 不是这么设计的。

| Trigger | 版本 | 系统返回物 | 何时触发 | 停止条件 / 备注 |
|---|---|---|---|---|
| `TRIGGER_TYPE_APP_FULLY_DRAWN = 1` | API 36 | running system trace snapshot | 冷启动里调用 `Activity.reportFullyDrawn()` 之后 | 适合复盘启动尾段 |
| `TRIGGER_TYPE_ANR = 2` | API 36 | running system trace snapshot | 系统已经识别到 ANR,但还没按公开契约结束该应用时 | 文档强调它不等同于"应用一定已被杀" |
| `TRIGGER_TYPE_COLD_START = 10` | API 37 | newly started system trace + stack sampling | 应用冷启动尽早阶段,且 `ApplicationStartInfo.getStartType()` 为 `START_TYPE_COLD` | 调用 `reportFullyDrawn()` 时停止;没有调用时默认约 5 秒停止 |
| `TRIGGER_TYPE_OOM = 7` | API 37 | Java heap dump | 应用抛出 `OutOfMemoryError` | 自定义 `UncaughtExceptionHandler` 必须继续调用默认 handler |
| `TRIGGER_TYPE_KILL_EXCESSIVE_CPU_USAGE = 9` | API 37 | running system trace snapshot | 应用因 `ApplicationExitInfo.REASON_EXCESSIVE_RESOURCE_USAGE` 被系统杀掉 | 文档没有公开 CPU 阈值 |
| `TRIGGER_TYPE_ANOMALY = 8` | API 37 | **依异常类型动态变化**:heap dump 或 stack sampling | 系统检测到异常行为;MemoryLimiter 这类 kill 路径会在终止前触发,binder spam 等规则可能只收集 profile | 产物类型和 tag 由 anomaly-detector 规则决定;`ProfilingResult.getTag()` 携带异常分类信息 |
| `TRIGGER_TYPE_APP_COMPAT = 11` | API 37 | **依兼容性问题类型动态变化** | 应用表现出兼容性回退行为 | 产物和 tag 随具体 compat 问题而定 |

这张表比散落的清单更有用,因为后续分析的入口已经固定下来了。`APP_FULLY_DRAWN` 和 `ANR` 的结果都可以走 Perfetto UI，`OOM` 该走 heap dump 分析，`COLD_START` 既有 system trace，也有 stack sampling。`ANOMALY` 和 `APP_COMPAT` 的产物不固定，收到结果后要先读 `getTag()` 判断异常类别，再根据文件后缀选择分析工具；Android 17 `ProfilingService` 中 Java heap dump 使用 `.perfetto-java-heap-dump` 后缀，system trace 使用 `.perfetto-trace` 后缀。

### 36.1 trigger 还要单独判 extension version

`APP_REQUEST_RUNNING_TRACE`、`KILL_FORCE_STOP`、`KILL_RECENTS`、`KILL_TASK_MANAGER` 都挂在 36.1 扩展上。运行时不能只看 API level,还要再用 `SdkExtensions.getExtensionVersion()` 或等价封装确认对应的 platform extension 已经到位。扩展值不够时,应用侧只能回退到 API 36 公开的 `APP_FULLY_DRAWN` 和 `ANR`。

### `APP_FULLY_DRAWN` 和 `COLD_START` 不是同一件事

Android 16 的 `TRIGGER_TYPE_APP_FULLY_DRAWN = 1`，语义是"冷启动里已经调用 `Activity.reportFullyDrawn()`，系统给出一份 running system trace snapshot"。它更像在启动完成点拿一张快照，帮助我们比对启动后段和 fully drawn 时刻前后的线程活动。

Android 17 的 `TRIGGER_TYPE_COLD_START = 10` 则往前迈了一步。它要求系统在应用冷启动尽早阶段就开始录制，并持续到 `reportFullyDrawn()`，或者在没有调用 `reportFullyDrawn()` 时按默认 5 秒截止。公开文档还说明这类 trigger 使用 discard buffer，缓冲区满时会丢新事件，优先保留最早阶段的 tracepoint。写启动章节时，如果把这两个 trigger 混成一个名字，读者对采样窗口的判断就会直接错位。

### OOM 说的是 Java 层 OOM,不是 LMK

`TRIGGER_TYPE_OOM` 的公开语义非常具体，应用发生 Out Of Memory Exception 时，系统返回 Java heap dump。它和 `lmkd`、LMK、`Low Memory Killer` 不是一条问题路径。LMK 处理的是系统内存压力下的杀进程策略，章节 §4.4 已经单独展开；这里说的是应用自己因为堆分配失败抛出 OOM。

这里还有一个经常漏写的条件。官方文档明确要求，如果应用自定义了 `Thread.UncaughtExceptionHandler`，它仍然要继续调用默认的 `UncaughtExceptionHandler`。不然这个 trigger 不会生效。

### ANOMALY:按异常类型收集现场

`TRIGGER_TYPE_ANOMALY`(API 37,常量值 8)由 Android 17 系统层的异常检测机制驱动。设备端根据规则监控异常行为,Android 17 `ProfilingService` 源码中已包含 binder spam detector 的采集路径;MemoryLimiter 的 anon+swap 超限路径会先通知 `ProfilingServiceHelper` 触发 ANOMALY,再延迟 kill 目标进程。也就是说,ANOMALY 不是"所有异常都代表进程马上被杀"的统一信号:有些规则只触发日志或 profile 收集,只有 MemoryLimiter 这类 kill 路径才适合按进程终止前现场来理解。

**产物的动态性**:ANOMALY 不像其他 trigger 返回固定的文件格式。`ProfilingResult#getTag()` 会携带异常分类信息(如 `memory_limit`),`getResultFilePath()` 返回的文件后缀决定分析工具--`.perfetto-java-heap-dump` 走 Java heap dump 工具链,`.perfetto-trace` 走 Perfetto UI。处理 ANOMALY 结果时,要先读 tag 再决定分析路径,不能一律当 system trace 处理。

**MemoryLimiter 场景**:当 MemoryLimiter 的 anon+swap 限额路径触发时,`frameworks/base` 会先向 `ProfilingServiceHelper` 发送 ANOMALY,再延迟 kill,kill reason 可见类似 `MemoryLimiter:AnonSwap`。`ProfilingService` 对这类异常使用 `memory_limit` tag,并返回 Java heap dump,用于定位是哪些对象占住了内存。这个场景的排查顺序是:`ApplicationExitInfo.getReason()` 指向资源过量或描述里出现 MemoryLimiter 线索 → `ProfilingResult.getTag()` 为 `memory_limit` → heap dump 进 MAT 或 Android Studio Profiler → 找 retained size 最高的引用路径。

**边界**:公开 API 文档没有列出系统异常检测的全部判定规则和触发阈值,这些属于系统内部策略。同一 UID 下多个包注册 ANOMALY trigger 时,系统可能不为某些异常提供产物;多进程应用也不要假设每个进程都能收到独立的 profiling 结果。线上接入时要考虑这种不确定性,不能假设注册了就一定能拿到产物。

### ANR 和 excessive CPU 也不要发明内部阈值

`TRIGGER_TYPE_ANR` 的公开定义是"ANR 已被识别,但系统还没准备按公开契约结束该应用"。文档没有公开具体的预警阈值。`TRIGGER_TYPE_KILL_EXCESSIVE_CPU_USAGE` 也只公开到了"应用因 `ApplicationExitInfo.REASON_EXCESSIVE_RESOURCE_USAGE` 被杀后返回 running system trace snapshot"这一层,没有把 CPU 百分比、持续时间、采样窗口当成 API 契约。

所以这一类章节不该写成一组固定百分比、固定时长和固定预警窗口。如果没有源码、实验或 device_config 证据支撑,那就是把内部策略猜想写成公开合同。

## 在工具中的表现与验证路径

### 冷启动样例:`APP_FULLY_DRAWN` / `COLD_START`

对冷启动来说,我们先确认返回物是不是 `.perfetto-trace`,再用 Perfetto UI 打开。`APP_FULLY_DRAWN` 更适合复盘启动收尾阶段,`COLD_START` 更适合看进程创建后的完整启动窗口。

[图:`TRIGGER_TYPE_APP_FULLY_DRAWN` 返回的 `.perfetto-trace` 在 Perfetto UI 中的观测示意。标出应用主进程、主线程 `Choreographer#doFrame`、RenderThread、SurfaceFlinger 合成轨,并在启动尾段比对 `reportFullyDrawn()` 附近的最后几帧。]

[图:`TRIGGER_TYPE_COLD_START` 返回的 system trace + stack sampling 结果示意。标出应用冷启动早期的进程创建、主线程首个长任务、`reportFullyDrawn()` 停止点,以及默认 5 秒停止的回退边界。]

分析这两类结果时，先确定时间窗口，再看线程状态、Binder 等待、渲染帧和系统服务干预。

### ANR 样例:running system trace snapshot

ANR 结果同样是 `.perfetto-trace`,但目标从启动耗时换成了"找到超时前的阻塞对象"。我们通常会把主线程、Binder 线程池、持锁线程、`system_server` 放在一起看,而不是只盯着一条主线程 slice。

[图:`TRIGGER_TYPE_ANR` 返回的 running system trace 示意。标出应用主线程 blocked 状态、对应的 owner 线程、同步 Binder 调用等待区间,以及 `system_server` 中可能卡住的服务线程。]

这种结果比单独的 `traces.txt` 多了一段历史信息。我们可以把 `traces.txt` 当成终点快照,把 system-triggered trace 当成"终点之前发生了什么"。

### OOM 样例:Java heap dump

`TRIGGER_TYPE_OOM` 不该塞回 Perfetto trace 段落里一起写。它返回的是 Java heap dump，分析目标也从线程调度切到"谁持有对象、谁把堆顶满了、是否存在大对象或意外 retained path"。

[图:`TRIGGER_TYPE_OOM` 返回的 Java heap dump 分析示意。标出 dominator tree 中占用最大的对象组、retained size 最高的引用路径,以及触发 OOM 前最后一次大分配对应的业务对象。]

如果一个章节把 OOM、ANR、cold start 全都说成"自动抓 Trace",读者在工具选择上就已经走偏了。

### 本地验证与 redaction 边界

ProfilingManager 返回的结果默认是 redacted 版本,只保留请求进程本身的信息。拿到 `.perfetto-trace` 之后，看不到其他应用的完整上下文，依赖全局系统视角的 Perfetto 标准库查询也可能缩水。

做本地验证时,Android 16+ 和 Android 15 的调试开关不同:

- Android 16+:`device_config put profiling_testing delete_temporary_results.disabled true`。打开后,系统会在临时目录保留 redacted 和 unredacted 结果(适用时),logcat 会给出路径。
- Android 15:`device_config put profiling_testing delete_unredacted_trace.disabled true`。这一代只会在临时目录保留 unredacted 文件;无 root 的设备若想取 redacted 结果,需要把文档里的 `/pkg/files/profiling/file.type` 复制到 `/pkg/cache/file.type`。

要测试 system-triggered trigger,还要给目标包打开 testing mode:

```bash
device_config put profiling_testing system_triggered_profiling.testing_package_name com.your.app
```

这个开关会确保后台 trace 常驻,并让目标包的 trigger 绕过系统级 rate limiter。测试结束后,再执行:

```bash
device_config delete profiling_testing system_triggered_profiling.testing_package_name
```

## 与其他机制的关系

### 和 `Activity.reportFullyDrawn()` 的关系

`APP_FULLY_DRAWN` 与 `COLD_START` 都和 `Activity.reportFullyDrawn()` 有直接关系。前者在调用之后返回 running trace snapshot，后者把它当作录制截止点之一。启动文章里谈 fully drawn 时，不能只把它当埋点 API；到了 ProfilingManager 这里，它还是 system-triggered profiling 的停止和取样边界。

### 和 `ApplicationStartInfo` 的关系

`COLD_START` 的公开文档把触发前提说得很明确,`ApplicationStartInfo.getStartType()` 必须是 `START_TYPE_COLD`。这让 ProfilingManager 和启动类型判断连到一起。我们在 §8.2 里分析冷启动时,可以用 `ApplicationStartInfo` 先分流,再决定是否注册或解释 cold-start profiling 结果。

### 和 `ApplicationExitInfo` 的关系

`KILL_EXCESSIVE_CPU_USAGE` 的判断依据来自系统已经做出的 kill 判断(`ApplicationExitInfo.getReason() == REASON_EXCESSIVE_RESOURCE_USAGE`),应用侧不需要自行检测 CPU。也就是说,ProfilingManager 这里拿到的是系统已经做出 kill 判断后的 profiling 结果,而不是一个持续轮询 CPU 的前台预警器。

## 版本演进

| 版本 | 能力面 | 这一版该怎么理解 |
|---|---|---|
| Android 15 (API 35) | `ProfilingManager` 基础请求能力 | 重点是 `requestProfiling()` 和结果回调,本节的 system-triggered profiling 还没出现 |
| Android 16 (API 36) | `addProfilingTriggers()`、`APP_FULLY_DRAWN=1`、`ANR=2` | 首次把"由系统条件触发结果采集"放进公开 API |
| Android 16 extension 36.1 | `APP_REQUEST_RUNNING_TRACE=3`、`KILL_FORCE_STOP=4`、`KILL_RECENTS=5`、`KILL_TASK_MANAGER=6` | 这几类都属于 running system trace snapshot,运行时要按 extension 36.1 做 gating |
| Android 17 (API 37) | `OOM=7`、`ANOMALY=8`、`KILL_EXCESSIVE_CPU_USAGE=9`、`COLD_START=10`、`APP_COMPAT=11` | 触发器不再只返回 running trace,开始出现新开 trace、stack sampling、heap dump 和"artifact varies" 这类更细分的模型。系统异常检测机制新增设备端异常检测;MemoryLimiter 等 kill 路径可在终止前触发 ANOMALY,其他 anomaly 规则按配置收集 profile 或日志 |

`ANOMALY` 和 `APP_COMPAT` 也要点一下。文档没有把它们都固定成某一种结果文件,而是明确写了 artifact 会按 anomaly 类型变化,`ProfilingResult#getTag()` 里会带额外信息。写版本表时,如果把 Android 17 只概括成 OOM 和 excessive CPU,就把 public surface 少写了一截。

## 常见问题与误区

### 误区 1:`APP_FULLY_DRAWN` 就是 `COLD_START`

不是一个东西。`APP_FULLY_DRAWN` 是 API 36 的 running trace snapshot,`COLD_START` 是 API 37 的"尽早开始录制,再到 fully drawn 停止"的完整窗口。两者的采样范围不同,常量值也不同。

### 误区 2:OOM trigger 等于 LMK 现场

`TRIGGER_TYPE_OOM` 处理的是 Java 层 OOM 异常,返回 Java heap dump。LMK 和 `lmkd` 看的是系统内存压力和杀进程策略,应该回到 §4.4 去分析。

### 误区 3:注册 trigger 就能直接在本次回调里拿到结果

system-triggered profiling 的结果只会通过 `registerForAllProfilingResults()` 的全局 listener 回来。把它写成 request-scoped listener,或者再造一个并不存在的注册接口,应用一上手就会编译失败。

### 误区 4:系统公开了 ANR / CPU 的内部阈值

公开 API 没有给出具体的 CPU 阈值。没有源码、实验或 device_config 证据时,章节里就不该擅自补这些数字。

## 参考资料

- 官方文档:`https://developer.android.com/reference/android/os/ProfilingManager`
- 官方文档:`https://developer.android.com/reference/android/os/ProfilingTrigger`
- 官方文档:`https://developer.android.com/reference/android/os/ProfilingResult`
- 官方文档:`https://developer.android.com/reference/android/os/ext/SdkExtensions`
- AOSP:`packages/modules/Profiling/framework/android/os/ProfilingManager.java`
- AOSP:`packages/modules/Profiling/framework/android/os/ProfilingTrigger.java`
- AOSP:`packages/modules/Profiling/framework/android/os/ProfilingResult.java`
- AOSP:`packages/modules/Profiling/service/java/com/android/os/profiling/ProfilingService.java`
