---
title: "Android 17 App Memory Limits 与内存泄漏治理"
chapter: "23.9"
status: ready-for-review
drafted_date: "2026-05-19"
applicable_versions: "Android 17 (API 37); Android Studio Panda 1+"
last_verified: "2026-05-19"
last_verified_against: "Android Developers 2026-05-18; AOSP main ApplicationExitInfo / Profiling module"
confidence: medium
sources:
  - type: official
    path: "https://developer.android.com/about/versions/17/behavior-changes-all#app-memory-limits"
  - type: official
    path: "https://developer.android.com/blog/posts/the-fourth-beta-of-android-17"
  - type: official
    path: "https://developer.android.com/reference/android/os/ProfilingTrigger"
  - type: official
    path: "https://developer.android.com/topic/performance/tracing/profiling-manager/trigger-based-capture"
  - type: official
    path: "https://developer.android.com/topic/performance/memory"
  - type: aosp
    path: "frameworks/base/core/java/android/app/ApplicationExitInfo.java"
  - type: aosp
    path: "packages/modules/Profiling/framework/java/android/os/ProfilingManager.java"
  - type: aosp
    path: "packages/modules/Profiling/framework/java/android/os/ProfilingTrigger.java"
  - type: local
    path: "intake/daily-info/2026-05-19.md"
  - type: clipping
    path: "Clippings/Android 性能优化 - 原理：掌握 App 运行时的内存模型.md"
  - type: clipping
    path: "Clippings/Android 性能优化 - 物理内存优化实战：Java Heap 内存优化.md"
  - type: clipping
    path: "Clippings/Android 性能优化 - Native 内存优化（上）：so 库申请的内存优化.md"
  - type: clipping
    path: "Clippings/Android 性能优化 - 虚拟内存优化（上）：线程+多进程优化.md"
tags: [android17, memory-limits, memory-leak, applicationexitinfo, profilingmanager, leakcanary]
related_chapters: ["4.1", "4.4", "10.2", "14.14", "20.5", "23.1", "26.9", "26.12"]
created_by: "task2a-knowledge-gap"
created_date: "2026-05-19"
gap_source: "官方文档/每日信息/章节深挖/Clippings结构参考"
---

# 23.9 Android 17 App Memory Limits 与内存泄漏治理

Android 17（API 37）新增 App Memory Limits，用于处理极端内存泄漏和异常内存膨胀。它提供了新的系统退出信号与触发式诊断材料，也改变了 Android 17 设备上的内存回归测试方式。

平台源码锚点为 AOSP `android-17.0.0_r1`，内核文档锚点为 `android17-6.18-2026-06_r6`。Java Heap OOM、LMKD、一般内存泄漏与线上监控分别见 20.5、4.4、23.1、23.7；这里只讨论 MemoryLimiter 的特有边界。

## 适用范围：不按 targetSdk 限制，只在部分设备启用

App Memory Limits 位于 Android 17 的“影响所有应用”行为变更页面，含义是它不受应用 `targetSdkVersion` 控制。应用只要运行在启用了该机制的 Android 17 设备上，就可能受到影响。

这不表示每台 Android 17 设备都会启用。官方页面明确注明，限制只施加在部分设备上。`android-17.0.0_r1` 的源码给出了启用条件：

- `MemoryLimiter` 功能标志处于启用状态；
- 设备存在 `/vendor/etc/memory-limiter-config.xml`；
- 配置中至少有一组 `minimumRequiredMemTotal` 不高于设备的 `/proc/meminfo` `MemTotal`；
- 目标进程不在系统维护的豁免集合中。

配置按设备总 RAM 选择匹配项，并分别提供 visible 与 not-visible 进程状态的内存、swap 限制。具体数值由设备配置决定。AOSP 中的 `sDefaultConfig` 明确标为测试用途，不应当被引用为量产阈值。

因此，应用侧不能根据“设备是 Android 17”推算限制值，也不能用一个固定 MB 数覆盖所有厂商和 RAM 档位。测试前先运行 `adb shell am memory-limiter status`；若设备不施加限制，后续 `am memory-limiter` 调整命令不会产生预期效果。

## MemoryLimiter 的系统实现

### cgroup 控制文件与用户空间判定

内核 cgroup v2 文档对几个控制文件的定义如下：

- `memory.high` 是内存使用的节流边界。超过边界会让进程承受直接回收压力；这个控制文件本身不会调用 OOM killer。
- `memory.swap.max` 是 swap 使用的硬上限；达到该值后，该 cgroup 的匿名页不能继续换出。
- `memory.stat` 提供匿名页、共享内存等分类数据。
- `memory.swap.current` 提供当前 cgroup 的 swap 使用量。

Android 17 的 `MemoryLimiter.cpp`使用这些内核接口，但终止进程的决定来自 Android 用户空间。它先监视 `memory.high`事件；进入高压区后，轮询下面的指标：

> `memory.stat` 中的 `anon + shmem`，再加 `memory.swap.current`

源码把这项指标称为 `AnonSwap`。对应上限由当前进程状态的 `memHigh + swapMax` 得出；Java 配置字段名仍是 `swapHigh`，native 层写入的文件则是 `memory.swap.max`。超过上限后，native 层通知 `MemoryLimiter.java`，由后者执行 profiling 与终止流程。这里要保留两个边界：

- `AnonSwap` 不是 PSS、RSS 或 Java Heap 的别名；
- cgroup 的 `memory.high` 负责节流和回收，`MemoryLimiter` 才负责 Android 侧的超限判定与进程处置。

### 进程状态会改变限制

`MemoryLimiter.java`按 `ActivityManager` 的进程状态选择 visible 或 not-visible 配置。例如 top、bound-top、important-foreground 使用 visible 配置，foreground-service、service、receiver 等状态使用 not-visible 配置。cached 与 persistent 类进程还有单独处理。

同一个进程在前台正常、进入后台后命中限制，并不矛盾。复盘时必须记录退出前的进程状态、前后台切换和相关时间点，不能只比较进程启动后的最高 RSS。

### 超限后的顺序

在 `android-17.0.0_r1` 中，`AnonSwap` 超限后的主要步骤是：

1. 解除该进程当前的 `memory.high` 与 `memory.swap.max` 限制，避免 profiling 阶段继续受原限制影响。
2. 条件满足时，向 Profiling 服务发送 `TRIGGER_TYPE_ANOMALY`。
3. 延迟 30 秒发送终止请求，为 profiler 留出处理时间。
4. 使用 `MemoryLimiter:AnonSwap` 作为终止原因字符串。

30 秒是该源码版本中的实现常量，不是应用可以依赖的 API 契约。厂商修改、平台维护版本和 profiling 状态都可能影响应用观察到的时间。应用也不能把这段时间当作保存业务数据的宽限期。

## 与其他内存故障的区别

| 类型 | 系统或应用信号 | 主要压力来源 | 取证入口 |
| --- | --- | --- | --- |
| Java Heap OOM | `OutOfMemoryError` 与 Java 崩溃栈 | ART 管理堆达到分配极限或无法满足连续分配 | Heap Dump、GC/分配记录、引用链 |
| Native 分配失败 | native crash、分配返回失败或进程异常退出 | malloc、mmap、线程栈、图像与第三方 so | tombstone、heapprofd、`smaps` |
| LMKD 终止 | `ApplicationExitInfo.REASON_LOW_MEMORY`，且设备支持该报告 | 系统整体内存压力与进程优先级 | exit info、lmkd/系统压力记录 |
| MemoryLimiter 终止 | Android 17 r1 上为 `REASON_OTHER`，description 包含 `MemoryLimiter:AnonSwap` | 受控进程的 anon、shmem 与 swap 指标超过设备配置 | exit info、anomaly profile、cgroup/进程内存证据 |

MemoryLimiter 命中不能单独证明存在“泄漏”。未设尺寸上限的大图处理、AI 推理、WebView、多窗口或音视频峰值也可能让匿名页与 swap 达到限制。应沿业务场景和分配证据继续区分长期增长与合法峰值。

## 用 ApplicationExitInfo 识别退出

Android 11（API 30）引入 `ActivityManager.getHistoricalProcessExitReasons()`。Android 17 r1 的 MemoryLimiter 归因规则由官方文档明确指定：

- `ApplicationExitInfo.getReason()` 等于 `REASON_OTHER`；
- `getDescription()` 包含 `MemoryLimiter:AnonSwap`，并可能附带其他信息。

`android-17.0.0_r1` 的 `ApplicationExitInfo.java` 没有专用的 memory-limiter reason 常量，因此不使用其他 reason 值代替这组条件。

下面的代码用于读取当前 UID 可见的历史退出记录，并把 MemoryLimiter 事件转换为单位明确的数据对象。

```kotlin
private const val MEMORY_LIMITER_DESCRIPTION = "MemoryLimiter:AnonSwap"

data class MemoryLimiterExit(
    val timestampMillis: Long,
    val pid: Int,
    val processName: String,
    val importance: Int,
    val pssKb: Long,
    val rssKb: Long,
    val description: String
)

@RequiresApi(37)
fun Context.readMemoryLimiterExits(
    maxRecords: Int = 0
): List<MemoryLimiterExit> {
    require(maxRecords >= 0)

    val activityManager = getSystemService(ActivityManager::class.java)
    return activityManager
        .getHistoricalProcessExitReasons(null, 0, maxRecords)
        .mapNotNull { exit ->
            val description = exit.description ?: return@mapNotNull null
            if (
                exit.reason != ApplicationExitInfo.REASON_OTHER ||
                !description.contains(MEMORY_LIMITER_DESCRIPTION)
            ) {
                return@mapNotNull null
            }

            MemoryLimiterExit(
                timestampMillis = exit.timestamp,
                pid = exit.pid,
                processName = exit.processName,
                importance = exit.importance,
                pssKb = exit.pss,
                rssKb = exit.rss,
                description = description
            )
        }
}
```

`maxRecords = 0`表示不额外限制返回数量，系统仍只保留环形缓冲区中的近期记录。传入 `packageName = null`只能查询调用方 UID 可见的包；共享 UID 或 external service 场景需要结合 API 文档解释结果范围。

`pss`和 `rss` 的单位都是 kB。它们来自系统最近一次采样，不能代表终止前一刻的精确快照；进程来不及被采样时，值还可能为零。代码保留原始 description 用于诊断，但稳定聚合条件只依赖官方指定的 token；`getDescription()`的整体格式没有跨版本稳定保证。

`getTraceInputStream()`也不能当作 MemoryLimiter 的固定附件。API 文档主要保证 ANR trace，并从 API 31 起为 native crash 提供 tombstone；其他原因可能返回 `null`。MemoryLimiter 的主要大对象证据来自 ProfilingManager 结果。

## 用 TRIGGER_TYPE_ANOMALY 获取诊断材料

`ProfilingTrigger.TRIGGER_TYPE_ANOMALY`在 API 37 加入。Android 17 官方说明指出，当应用达到 OS 定义的内存限制时，anomaly trigger 可产生针对该应用的 heap dump；回调发生在系统执行终止动作之前。AOSP r1 中的 30 秒延迟也说明平台会为采集留出时间。

这仍然不是必达接口：

- 系统必须正在运行相应的后台 profiling；
- 系统级和应用自定义限流都允许本次结果；
- 同一 UID 下存在多个包时，部分 anomaly 可能不提供 artifact；
- profiling 或文件交付失败会通过 `ProfilingResult.errorCode` 返回；
- 回调重投、进程重启和文件清理都要求应用使用一个长期存活的统一接收者。

下面的类用于集中注册 anomaly trigger，并在结束时移除同类 trigger 与全局监听器。它把限流周期交给调用方决定，不写入通用固定值。

```kotlin
@RequiresApi(37)
class MemoryAnomalyProfiler(
    context: Context,
    executor: Executor,
    rateLimitHours: Int,
    private val onArtifact: (filePath: String, tag: String?) -> Unit,
    private val onFailure: (errorCode: Int, message: String?) -> Unit
) : AutoCloseable {

    private val manager = context.getSystemService(ProfilingManager::class.java)

    private val listener = Consumer<ProfilingResult> { result ->
        if (result.errorCode == ProfilingResult.ERROR_NONE) {
            val filePath = result.resultFilePath
            if (filePath != null) {
                onArtifact(filePath, result.tag)
            } else {
                onFailure(result.errorCode, "successful result has no file path")
            }
        } else {
            onFailure(result.errorCode, result.errorMessage)
        }
    }

    init {
        require(rateLimitHours >= 0)

        manager.registerForAllProfilingResults(executor, listener)
        manager.addProfilingTriggers(
            listOf(
                ProfilingTrigger
                    .Builder(ProfilingTrigger.TRIGGER_TYPE_ANOMALY)
                    .setRateLimitingPeriodHours(rateLimitHours)
                    .build()
            )
        )
    }

    override fun close() {
        manager.removeProfilingTriggersByType(
            intArrayOf(ProfilingTrigger.TRIGGER_TYPE_ANOMALY)
        )
        manager.unregisterForAllProfilingResults(listener)
    }
}
```

`registerForAllProfilingResults()`是 UID 级的全局结果监听器，`addProfilingTriggers()`注册的是当前进程感兴趣的 trigger。一个进程只允许同一 trigger type 保留一份，新注册会替换旧配置。因此，这个类应由进程级诊断组件统一持有，不能让多个页面分别创建实例。

成功回调中的 `resultFilePath`才是文件位置依据；官方不保证目录结构固定。`result.tag`包含异常类型的补充信息，接收端仍要验证文件类型、大小和关联事件，不能把所有 anomaly 结果都标成内存限制。

## 在测试设备上验证限制

官方提供三个 `am memory-limiter` 子命令：

- `status`：查看设备是否启用以及 visible、not-visible 限制；
- `ignore <uid>|none|all`：调整 UID 的忽略状态；
- `manual <pid> <limit>|max|none`：为测试进程设置、移除或恢复限制。

命令只应在专用测试设备和可恢复的测试账号上使用。手动限制可能直接终止进程，`ignore all`会改变整台设备的系统行为。

源码锚点还存在一个必须注意的版本差异：当前官方页面记录了 `manual ... max`，但 `android-17.0.0_r1` 的 `ActivityManagerShellCommand`只解析整数和 `none`。针对 r1 的自动化脚本不要发送 `max`；每条变更命令后都用 `status`核对，并以结束目标进程、重新启动测试环境作为恢复步骤。

建议用两组对照验证：

1. 相同设备、构建和动作脚本，在默认限制下记录基线。
2. 在测试进程上设置经过风险评估的较低手动限制，确认退出记录、description 和 anomaly artifact 是否能关联到同一场景。

测试数值来自该场景已测得的内存分布，不应抄录其他项目的 MB 数。测试报告还要记录 `am memory-limiter status`原始输出、设备构建指纹、PID、进程状态、动作时间与结果文件。

## Android Studio Panda 与 LeakCanary

Android Studio Panda 在 Profiler 中提供独立的 LeakCanary task，并把分析结果与 IDE 源码上下文结合。它适合把线上 MemoryLimiter 样本还原为本地可重复路径：

1. 从 `ApplicationExitInfo` 事件确定设备、进程、前后台状态、版本和时间。
2. 从 anomaly artifact、页面埋点或业务日志恢复输入规模与动作序列。
3. 在同类设备上重复场景，用 LeakCanary task 检查 retained object、GC Root 和引用路径。
4. 同时观察 Java Heap、Native Heap、Graphics、线程和总体 PSS。
5. 修改后重复相同脚本，比较对象存活、峰值和退出后的回落。

LeakCanary 只能分析 Java/Kotlin 可达对象。若 retained object 没有异常，而 Native Heap、Graphics、线程栈或匿名映射继续增长，应转向 heapprofd、`dumpsys meminfo`、`smaps`或图形资源分析。线上退出信号、本地 Java 引用链与 native 分配栈分别回答不同问题。

开发包也不等同于量产包。debuggable、调试器、LeakCanary、未压缩资源和不同的 native 符号都会改变内存曲线。复现根因后，还要用接近发布配置的 profileable 构建验证预算。

## 建立内存基线与灰度门禁

MemoryLimiter 面向分布尾部和长期异常，单一“平均 PSS”无法支持发版判断。每条基线至少绑定以下条件：

| 维度 | 记录内容 | 原因 |
| --- | --- | --- |
| 设备 | 型号、RAM、page size、ABI、构建指纹、是否启用 MemoryLimiter | 设备限制与内存行为不可跨组推断 |
| App | version、commit、构建类型、实验组 | 保证二进制和配置可追溯 |
| 进程 | 进程名、进程状态、是否独立 WebView/播放器/工具进程 | 限制按进程与状态变化 |
| 场景 | 输入规模、动作序列、前后台切换、窗口模式 | 区分泄漏、峰值与组合场景 |
| 检查点 | 动作前、峰值、退出、冷却后 | 同时观察峰值和回落 |
| 指标 | Java Heap、Native Heap、Graphics、线程、PSS、RSS、swap 相关观测 | 避免只看一种内存 |
| 统计 | 样本量、P50/P90/P99、异常值处理、采集失败率 | 说明尾部结果是否可信 |
| 退出 | reason、description、PSS/RSS 采样值、artifact 状态 | 把增长与系统处置关联 |

设备分组应从真实用户分布和实测差异得到，不要预设“4 GB 以下、6 GB、8 GB”后长期不变。高 RAM 设备也会在多窗口、相机、视频或端侧 AI 组合场景中产生较高匿名页。

灰度阶段可以设置三类决策条件：

- 新版本出现此前没有的 `MemoryLimiter:AnonSwap` 事件时，暂停扩大灰度，先检查进程与场景聚类；
- 同设备组、同场景的尾部分位数或冷却后残留量超过预先批准的预算时，由所属模块给出证据和处置；
- Java Heap 稳定而 RSS/AnonSwap 相关观测增长时，不要继续只查 Java 引用链，转向 native、线程、图片、WebView 与 mmap。

P50/P90/P99 只是样本分布，门禁线必须来自稳定版本、业务风险和样本量。`ApplicationExitInfo.pss/rss`又是最近采样值，适合用于退出事件聚类，不适合单独替代持续监控曲线。

## 线上诊断与隐私

MemoryLimiter 退出记录属于低敏感度的系统诊断摘要；heap dump 可能包含字符串、URL、用户输入、令牌、图片元数据和业务对象，应按高敏感数据处理。

推荐分三层采集：

- **默认事件**：reason、官方 description token、进程、版本、设备组、最近页面和 PSS/RSS 采样值；
- **诊断摘要**：artifact 类型、大小、成功/失败码、类名与 retained-size 聚合，类名也要经过白名单；
- **原始 artifact**：仅在授权样本中上传，端到端加密，限制访问者和保留期，并提供服务端删除审计。

应用收到成功回调后，应把文件登记到持久任务队列再处理。不能假设当前 Activity 存活，也不能在主线程解析或上传 heap dump。上传失败、用户退出诊断计划或样本过期时，都要能删除本地副本。

系统与应用层都有 rate limit，profiling 结果也不保证产生。监控看板必须统计“触发事件数、成功 artifact 数、失败码分布”，否则缺失文件会被误解成没有内存问题。

## 与其他章节的关系

- Java/Kotlin 对象泄漏与 GC Root：23.1。
- OOM 类型、崩溃与进程退出：20.5。
- Native 分配、heapprofd 与所有权：23.3。
- 线上内存采集与 `ApplicationExitInfo` 最近采样边界：23.7。
- LMKD 与进程优先级：4.4。
- 进程退出归因：26.9。
- ProfilingManager 通用能力：26.12。
- Android Studio 内存工具：14.14。

Android 17 的 MemoryLimiter 增加了一类可识别的系统终止原因，但根因仍要回到原有的 Java、native、图形、线程和业务场景证据。

## 小结

Android 17 App Memory Limits 的关键边界可以归纳为五点：

- 它不按 targetSdk 限制，但只在具备 vendor 配置并启用该能力的部分设备上施加；
- `android-17.0.0_r1` 通过 cgroup v2 指标监视进程的 anon、shmem 与 swap，Android 用户空间决定是否终止进程；
- 退出归因使用 `REASON_OTHER` 与包含 `MemoryLimiter:AnonSwap` 的 description；
- `TRIGGER_TYPE_ANOMALY`可以提供 heap dump，但受后台采集、限流和交付状态影响；
- 发版判断要绑定设备、进程状态、场景、检查点和样本量，系统阈值不能由应用猜测。

把退出分类、触发式 artifact、本地复现和灰度基线放在同一份记录里，才能从“进程被系统结束”继续定位到可修改的资源所有权或峰值策略。

## 参考资料

- [Android Developers：Android 17 behavior changes—App memory limits](https://developer.android.com/about/versions/17/behavior-changes-all#app-memory-limits)
- [Android Developers Blog：The Fourth Beta of Android 17](https://developer.android.com/blog/posts/the-fourth-beta-of-android-17)
- [Android Developers：`ApplicationExitInfo`](https://developer.android.com/reference/android/app/ApplicationExitInfo)
- [Android Developers：`ProfilingTrigger`](https://developer.android.com/reference/android/os/ProfilingTrigger)
- [Android Developers：`ProfilingManager`](https://developer.android.com/reference/android/os/ProfilingManager)
- [Android Developers：Trigger-based profiling](https://developer.android.com/topic/performance/tracing/profiling-manager/trigger-based-capture)
- [Android Developers：Manage your app's memory](https://developer.android.com/topic/performance/memory)
- [AOSP `android-17.0.0_r1`：`MemoryLimiter.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/services/core/java/com/android/server/am/MemoryLimiter.java)
- [AOSP `android-17.0.0_r1`：`MemoryLimiter.cpp`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/services/core/jni/com_android_server_am_MemoryLimiter.cpp)
- [AOSP `android-17.0.0_r1`：`ActivityManagerShellCommand.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/services/core/java/com/android/server/am/ActivityManagerShellCommand.java)
- [AOSP `android-17.0.0_r1`：`ApplicationExitInfo.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/app/ApplicationExitInfo.java)
- [AOSP `android-17.0.0_r1`：`ProfilingTrigger.java`](https://android.googlesource.com/platform/packages/modules/Profiling/+/android-17.0.0_r1/framework/java/android/os/ProfilingTrigger.java)
- [AOSP `android-17.0.0_r1`：`ProfilingManager.java`](https://android.googlesource.com/platform/packages/modules/Profiling/+/android-17.0.0_r1/framework/java/android/os/ProfilingManager.java)
- [Android Common Kernel `android17-6.18-2026-06_r6`：cgroup v2 memory controller](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/Documentation/admin-guide/cgroup-v2.rst)
