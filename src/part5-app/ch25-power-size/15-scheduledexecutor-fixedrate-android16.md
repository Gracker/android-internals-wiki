---
title: "Android 16 固定频率任务补偿执行与后台 CPU 峰值治理"
chapter: "25.15"
status: ready-for-review
drafted_date: "2026-05-23"
applicable_versions: "Android 16 (API 36) - Android 17 (API 37)"
last_verified: "2026-05-23"
last_verified_against: "AOSP main libcore + Android 16 behavior changes"
confidence: medium
sources:
  - type: official
    path: "https://developer.android.com/about/versions/16/behavior-changes-16"
  - type: official
    path: "https://developer.android.com/reference/java/util/concurrent/ScheduledExecutorService"
  - type: official
    path: "https://developer.android.com/reference/java/util/concurrent/ScheduledThreadPoolExecutor"
  - type: aosp
    path: "platform/libcore/ojluni/src/main/java/java/util/concurrent/ScheduledThreadPoolExecutor.java"
  - type: blog
    path: "https://android-developers.googleblog.com/2025/06/android-16-is-here.html"
tags: [power, background-task, scheduledexecutor, android16, cpu]
related_chapters: ["5.10", "25.2", "25.4", "26.3"]
created_by: "task2a-knowledge-gap"
created_date: "2026-05-23"
gap_source: "官方文档/每日信息/源码结构"
---

# 25.15 Android 16 固定频率任务补偿执行与后台 CPU 峰值治理

## 固定频率任务的治理范围

`scheduleAtFixedRate()` 是进程内调度工具，却经常被拿来做埋点上报、心跳、监控采样和配置刷新。这些任务平时不显眼，应用从冻结或 CPU 挂起状态恢复时才会暴露问题：旧实现可能连续执行已经错过的周期，后台线程因此与 Activity 恢复、首帧绘制、Binder 回调和网络重连同时争用 CPU。

Android 16 对这个行为设置了明确的兼容边界。在 Android 16 设备上，面向 `targetSdkVersion >= 36` 的应用回到有效生命周期后，最多立即执行一次错过的固定频率任务；面向较低版本的应用默认保留旧行为。兼容变更名为 `STPE_SKIP_MULTIPLE_MISSED_PERIODIC_TASKS`，Change ID 是 `288912692`。

Android 17 需要单独说明。`android-17.0.0_r1` 的 `ScheduledThreadPoolExecutor` 已经删除上述 Change ID、`targetSdkVersion` 注解和兼容判断，`setNextRunTime()` 直接执行新的校正逻辑。Android 17 r1 的源码行为作为当前平台锚点；Android 16 的 `targetSdkVersion` 分流只用于解释版本迁移和设计 Android 16 测试方案。

这次平台修改只限制线程池追赶错过周期的次数。它没有提供跨进程可靠性，也不会替应用选择更合适的后台调度 API。任务分类、生命周期管理、取消和错误处理仍由应用负责。后台任务的系统调度边界可结合 5.10、25.2、25.4 和 26.3 节阅读。

## 先把固定频率的语义说清楚

`scheduleAtFixedRate(command, initialDelay, period, unit)` 按 `initialDelay + n × period` 计算每一轮的计划时间。这里的“固定频率”指相对于起点的固定节拍，不是对齐某个墙上时钟时间。libcore 用 `System.nanoTime()` 处理相对时间，修改系统日期或时区不应成为这类任务的业务依据。

Java API 还规定了几条容易漏掉的约束：

- 到达计划时间只表示任务具备执行条件，不保证它立即获得 CPU。
- 同一个周期任务的相邻两次执行不会重叠。某次执行超过一个周期时，后续执行可以延迟开始，但不会并发执行同一个 `Runnable`。
- 某次执行抛出异常后，后续执行会被抑制。调用方如果没有检查 `ScheduledFuture`，很容易把“任务已经停止”误判为“线程池偶尔没有调度”。
- 这类计划只存在于当前进程和当前执行器中。进程被终止后，`ScheduledFuture` 不会被系统恢复。

`scheduleWithFixedDelay()` 的计算方式不同：它从本轮执行结束时开始等待下一段延迟。任务执行慢时，后续计划会整体向后移动，不存在为了维持原节拍而追赶的需求。两种 API 都保证同一周期任务不会自我重叠，也都具有“未处理异常会停止后续执行”的语义。

## Android 16 与 Android 17 的源码差异

周期任务执行成功后，`ScheduledFutureTask.run()` 会调用 `setNextRunTime()`，再把任务放回延迟队列。Android 16 r1 对固定频率任务先执行 `time += period`，随后仅在兼容变更开启时检查新的计划时间是否已经落后超过一个周期。若是，代码会把它移到离当前时间最近的一个错过周期。这样恢复后仍可能立即执行一次，但不会逐个追赶更早的周期。

Android 16 r1 的开关定义带有 `@EnabledAfter(targetSdkVersion = VersionCodes.VANILLA_ICE_CREAM)`，也就是默认从 `targetSdkVersion` 36 开始启用。源码同时允许 libcore 功能标志启用新行为，所以测试结论应以兼容框架状态为准，不应只从 Manifest 推断。

到了 `android-17.0.0_r1`，`setNextRunTime()` 保留了同一套时间校正公式，却不再调用兼容判断。基于这一标签可以得到以下版本边界：

| 运行平台 | 默认行为 | 测试重点 |
| --- | --- | --- |
| Android 15 及更早版本 | 可能连续追赶多个错过周期 | 作为旧行为基线，核对应用和三方库是否依赖补跑 |
| Android 16，`targetSdkVersion <= 35` | 兼容变更默认关闭，除非测试或平台标志覆盖 | 分别启用和关闭 Change ID 复现两种行为 |
| Android 16，`targetSdkVersion >= 36` | 兼容变更默认开启，最多立即补一次 | 关闭 Change ID 做回归对照 |
| Android 17 r1 | AOSP 源码无兼容分支，直接使用新公式 | 验证当前平台结果，不照搬 Android 16 的 `targetSdkVersion` 分组结论 |

Android 17 这一行是对 `android-17.0.0_r1` 源码的结论，不应扩写成所有厂商构建、所有后续分支都必然相同。排查设备差异时仍要记录构建指纹，并在对应源码或实机上复核。

## 连续补跑为什么会增加恢复成本

单次任务未必很慢；大量原本分散执行的工作被压到同一个恢复阶段，仍会增加以下成本：

- 调度等待：`ScheduledThreadPoolExecutor` 使用固定数量的核心线程和无界延迟队列，`maximumPoolSize` 对它没有实用作用。多个任务具备执行条件后，要观察线程的 Runnable 状态和获得 CPU 前的等待，而不是只调大最大线程数。
- 计算集中：序列化、加解密、压缩、图片处理或数据库整理连续执行，会增加恢复阶段的 CPU 时间并可能触发升频。
- 前台争用：Activity 恢复、主线程布局、RenderThread、Binder 回调和网络初始化也发生在这段时间。后台周期任务越多，前台路径受到调度干扰的机会越大。
- 电量波动：短时峰值可能在长窗口平均值里不明显。线程级原因适合用 Perfetto 判断，整段场景的电量趋势再用 Batterystats 或功耗设备复核。

Android 16 的兼容变更和 Android 17 r1 的新实现只减少 libcore 自己造成的多次追赶。应用手写的补发循环、旧系统设备、SDK 内部实现，以及多个彼此独立的周期任务同时恢复，仍可能形成相同现象。

## 周期任务先分类，再决定调度方式

固定频率适合对相位有要求、允许在进程退出时丢失、单次成本可控的任务。很多后台工作只关心“条件合适时执行一次”，补齐每一个历史周期没有业务价值。

| 任务类型 | 常见例子 | 推荐处理 |
| --- | --- | --- |
| 监控采样 | CPU、内存、线程状态采样 | 允许跳过历史周期，只保留当前样本；恢复延迟由采样目标和性能预算决定。采集口径详见 26.3 节。 |
| 心跳上报 | IM 长连、设备状态保活 | 前台长连可以维持轻量周期；后台优先依赖推送、网络回调或系统调度，恢复后做一次状态校准。 |
| 缓存刷新 | 首页配置、推荐缓存、实验参数 | 用 WorkManager periodic work 或 JobScheduler periodic job，接受系统批处理和约束；不要用进程内固定频率保障后台可靠性。详见 25.4 节。 |
| 实时处理 | 前台音视频、导航、运动记录 | 保留固定节拍，但要放在业务生命周期内，并和前台服务、音频、定位权限边界一起评估。 |
| SDK 内部轮询 | 广告、埋点、APM、风控 | 接入层增加线程命名、采样开关和生命周期接口；无法修改 SDK 时，通过 Perfetto、线程转储和调用次数指标定位来源。 |

选择 API 时，要同时回答四个问题：任务是否要求固定相位，错过的周期是否还有价值，进程退出后是否必须继续，以及是否需要充电、网络、空闲等系统约束。

| API | 时间语义 | 进程退出后 | 适用场景 |
| --- | --- | --- | --- |
| `scheduleAtFixedRate()` | 相对起点维持固定节拍；延迟后可能立即执行一次 | 丢失 | 进程内、对相位敏感、可跳过历史周期的轻量任务 |
| `scheduleWithFixedDelay()` | 本轮结束后再等待固定延迟 | 丢失 | 进程内轮询；不需要追赶，执行时长可能波动 |
| `Handler.postDelayed()` | 消息进入指定 `Looper` 的延迟队列 | 丢失 | 与该线程或界面生命周期绑定的短任务；不提供后台可靠性 |
| WorkManager / JobScheduler | 系统根据约束、配额和批处理机会安排 | 可由系统重新调度 | 可延后的持久工作、数据同步、缓存维护 |
| AlarmManager | 在允许的系统策略内提供时间触发 | 可在进程不存活时触发组件 | 用户可感知闹钟或有明确时间语义的触发；任务本体仍应短小 |

`AlarmManager`、WorkManager 和 JobScheduler 都不是固定频率线程池的等价替换。选择它们意味着接受各自的最小间隔、配额、约束和省电策略，不能继续承诺进程内定时器级别的触发精度。

## 用生命周期管理固定延迟任务

多数采样、轮询和批量上报不需要固定相位，用 `scheduleWithFixedDelay()` 更容易表达业务意图。下面的示例用于展示一个可启动、可停止的进程内周期任务，并处理取消后队列保留与未捕获异常两个常见问题。

```kotlin
import java.util.concurrent.ScheduledFuture
import java.util.concurrent.ScheduledThreadPoolExecutor
import java.util.concurrent.TimeUnit

class LifecyclePeriodicTask(
    private val executor: ScheduledThreadPoolExecutor,
    private val delayMs: Long,
    private val task: Runnable,
    private val onFailure: (Exception) -> Unit,
) {
    private val stateLock = Any()
    private val runLock = Any()
    private var generation = 0L
    private var future: ScheduledFuture<*>? = null

    init {
        require(delayMs > 0L)
        executor.setRemoveOnCancelPolicy(true)
    }

    fun start(initialDelayMs: Long = delayMs) {
        require(initialDelayMs >= 0L)

        synchronized(stateLock) {
            val current = future
            if (current != null && !current.isDone && !current.isCancelled) {
                return
            }

            val token = ++generation
            future = executor.scheduleWithFixedDelay(
                Runnable {
                    synchronized(runLock) {
                        val isCurrent = synchronized(stateLock) {
                            token == generation
                        }
                        if (isCurrent) {
                            try {
                                task.run()
                            } catch (error: Exception) {
                                onFailure(error)
                            }
                        }
                    }
                },
                initialDelayMs,
                delayMs,
                TimeUnit.MILLISECONDS,
            )
        }
    }

    fun stop(mayInterruptIfRunning: Boolean = false) {
        synchronized(stateLock) {
            generation++
            future?.cancel(mayInterruptIfRunning)
            future = null
        }
    }
}
```

调用方应在明确的生命周期边界调用 `start()` 和 `stop()`。`generation` 使已取消计划无法在稍后进入任务本体，`runLock` 避免一次停止后很快重启时出现旧任务与新任务并行。`setRemoveOnCancelPolicy(true)` 让已取消任务立即从延迟队列移除；默认策略会保留它直到原延迟到期。

示例只捕获 `Exception`，使一次可恢复失败不会按照周期任务的默认规则停止全部后续执行；`onFailure` 自身也必须保证不向外抛出异常。`Error` 等严重故障仍会终止计划。若业务要求失败即停，应删除捕获并监控 `ScheduledFuture` 的完成状态；若任务支持中断，还要自行设计资源清理与协作式取消，不能只依赖 `cancel(true)`。

还要加三条工程约束：

- 调度池与工作池分开评估。调度线程只负责触发时，可以把重任务提交给容量受控的工作执行器；若直接在调度线程里执行，线程数要按任务阻塞特征和实测数据选择。
- `ScheduledThreadPoolExecutor` 使用无界延迟队列，常规运行时不能依靠拒绝策略限制队列压力；拒绝通常发生在执行器关闭后。需要限流时，应在任务入口或下游有界工作队列中实现。
- 周期、采样率和禁用开关要可配置，但每次调整都应保留任务来源、执行次数、耗时、失败和取消原因，避免远端配置掩盖持续存在的生命周期错误。

## 观测方法：截取完整的恢复区间

平均 CPU 使用率无法说明任务是否与首帧恢复重叠。采集时应覆盖“进入后台、进程被冻结或 CPU 挂起、解除限制、Activity 恢复、首帧完成、网络恢复”这一整段过程，再按产品的恢复性能目标标记分析区间。

Perfetto 里建议看四组轨道：

- Thread state / CPU scheduling：确认工作线程何时进入 Runnable、何时获得 CPU，以及每次执行之间是否几乎没有空隙。CPU scheduling 数据来自 Linux ftrace。
- CPU frequency / idle state：对照周期任务执行区间观察 CPU 簇的频率和空闲状态变化。
- Main thread / RenderThread / FrameTimeline：判断后台任务是否与 Activity 恢复、首帧和卡顿帧相交。
- 自定义跟踪与指标：使用固定的 trace section 名称标注周期任务执行，在结构化日志中记录任务名、计划类型、开始时间、耗时、结果和取消原因，避免动态名称造成轨道碎片。

Batterystats / Battery Historian 适合比较较长场景中的唤醒、作业、网络和电量趋势，不能代替 Perfetto 解释线程调度关系。若要比较短时能耗，应固定设备状态、温度、网络、后台驻留方式和操作脚本，并结合设备支持的功耗轨道或外部功耗测量。

## 测试范围

测试不能只覆盖 `targetSdkVersion`。Android 16 的兼容分流和 Android 17 r1 的无分支实现应分开验证。

| 场景 | 操作 | 应验证的结果 |
| --- | --- | --- |
| Android 16，`targetSdkVersion` 35 / 36 | 使用同一任务、周期和冻结方式 | 默认兼容状态是否分别呈现旧行为与最多一次立即补跑 |
| Android 16，兼容变更启用 / 禁用 | 不修改 APK，仅切换 Change ID | 行为是否随开关改变，从而排除业务版本差异 |
| Android 17 r1 | 使用不同 `targetSdkVersion` 的测试包 | 实机是否与 r1 无兼容分支的源码一致；不要预设 Android 16 开关仍有效 |
| 任务执行时间超过周期 | 人为阻塞某次执行 | 同一周期任务不得并行；后续计划是否符合固定频率或固定延迟语义 |
| 任务抛出异常 | 让指定轮次抛出受控异常 | 原生周期任务后续执行被抑制；应用封装能上报并按约定继续或停止 |
| 取消与重启 | 在等待和执行期间分别调用 `cancel()` | 旧计划不再进入任务本体，延迟队列不会长期保留已取消项 |
| 进程终止 | 强制停止或杀死进程后等待 | 进程内计划不会自行恢复；需要持久性的工作应交给系统调度 API |
| 系统限制 | 覆盖 Cached Apps Freezer、Battery Saver、Doze 相关场景 | 记录任务错过、恢复、网络与前台状态，不把系统限制误判成线程池故障 |

下面的命令用于在 Android 16 测试设备上隔离这个兼容变更：

```bash
adb shell am compat enable STPE_SKIP_MULTIPLE_MISSED_PERIODIC_TASKS com.example.app
adb shell am compat disable STPE_SKIP_MULTIPLE_MISSED_PERIODIC_TASKS com.example.app
adb shell am compat reset STPE_SKIP_MULTIPLE_MISSED_PERIODIC_TASKS com.example.app
```

兼容框架接受 Change ID 或 Change Name；切换会终止应用进程，使覆盖项立即生效。测试结束后执行 `reset`，恢复由 `targetSdkVersion` 决定的默认状态。公开用户版本对可切换项和可调试应用有限制，自动化脚本应检查命令返回值与 `dumpsys platform_compat`，不要只看测试用例是否通过。

## SDK 与三方库迁移清单

三方 SDK 的风险在于接入方看不到内部线程池。广告、埋点、IM、APM、风控 SDK 都可能用固定频率任务做状态刷新或批量上报，接入方至少要补四个保护面：

- 线程识别：要求 SDK 线程命名，或者在自定义 `ThreadFactory` 里加业务前缀；无法改 SDK 时，用线程快照和 Perfetto 反查线程名。
- 生命周期入口：让 SDK 暴露 pause / resume / flush 接口，App 后台时暂停低优先级周期任务，恢复后只触发一次校准。
- 恢复调度：为埋点批量上报、配置刷新和 APM 上传定义优先级，不要让所有 SDK 在 `onStart()` 或 `onResume()` 同时恢复轮询。
- 指标约束：按 SDK 统计周期任务次数、执行耗时、失败、取消和恢复阶段 CPU 时间；调整周期后继续保留同一指标口径。

若 SDK 的周期任务负责持久上传，应由 SDK 提供 WorkManager、JobScheduler 或宿主调度接口；若只是进程内采样，就应允许丢弃历史采样点。接入方还要检查 SDK 是否自行实现了补发循环，因为平台只限制 `ScheduledThreadPoolExecutor` 的错过周期校正，不会识别业务队列里的历史事件。

## 小结

Android 16 在 `targetSdkVersion >= 36` 时默认限制 `scheduleAtFixedRate()` 的连续补跑，Android 17 r1 则已经在 libcore 中直接采用新时间校正逻辑。版本变化减少了单个固定频率任务追赶历史周期的次数，但没有改变它“仅在当前进程有效”的定位。

治理时要从任务语义出发：需要固定相位才使用 `scheduleAtFixedRate()`；只需间隔轮询时选 `scheduleWithFixedDelay()`；需要持久性、约束或系统批处理时交给 WorkManager / JobScheduler。再配合生命周期取消、异常处理、线程池隔离和 Perfetto 回归，才能判断恢复阶段的 CPU 成本来自平台补跑、业务任务，还是三方 SDK。

## 参考资料

- [官方文档: Android 16 behavior changes - Fixed rate work scheduling optimization](https://developer.android.com/about/versions/16/behavior-changes-16)
- [官方文档: Android 16 compatibility framework changes](https://developer.android.com/about/versions/16/reference/compat-framework-changes)
- [官方文档: Compatibility framework tools](https://developer.android.com/guide/app-compatibility/test-debug)
- [官方文档: ScheduledExecutorService](https://developer.android.com/reference/java/util/concurrent/ScheduledExecutorService)
- [官方文档: ScheduledThreadPoolExecutor](https://developer.android.com/reference/java/util/concurrent/ScheduledThreadPoolExecutor)
- [AOSP Android 17 r1: ScheduledThreadPoolExecutor.java](https://android.googlesource.com/platform/libcore/+/refs/tags/android-17.0.0_r1/ojluni/src/main/java/java/util/concurrent/ScheduledThreadPoolExecutor.java)
- [AOSP Android 16 r1: ScheduledThreadPoolExecutor.java](https://android.googlesource.com/platform/libcore/+/refs/tags/android-16.0.0_r1/ojluni/src/main/java/java/util/concurrent/ScheduledThreadPoolExecutor.java)
- [Perfetto docs: CPU Scheduling events](https://perfetto.dev/docs/data-sources/cpu-scheduling)
- [Perfetto docs: CPU frequency and idle states](https://perfetto.dev/docs/data-sources/cpu-freq)
- [官方文档: Profile battery usage with Batterystats and Battery Historian](https://developer.android.com/topic/performance/power/setup-battery-historian)
