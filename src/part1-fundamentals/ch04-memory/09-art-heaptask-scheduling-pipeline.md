---
title: "ART HeapTask 调度、启动维护与冻结边界"
chapter: "4.9"
status: ready-for-review
applicable_versions: "Android 12 (API 31) - Android 17 (API 37)"
last_verified: "2026-07-05"
last_verified_against: "AOSP android-17.0.0_r1"
confidence: high
tags: [ART, GC, HeapTask, TaskProcessor, GC抑制, 启动性能, 内存管理]
related_chapters: ["4.3", "4.7", "4.8", "4.11", "4.14", "21.11", "23.6"]
sources:
  - type: aosp
    path: "art/runtime/gc/task_processor.cc (android-17.0.0_r1)"
  - type: aosp
    path: "art/runtime/gc/task_processor.h (android-17.0.0_r1)"
  - type: aosp
    path: "art/runtime/gc/heap.cc:4113-5196 (android-17.0.0_r1)"
  - type: aosp
    path: "libcore/libart/src/main/java/java/lang/Daemons.java:743-768 (android-17.0.0_r1)"
  - type: aosp
    path: "libcore/libart/src/main/java/dalvik/system/VMRuntime.java:871-905 (android-17.0.0_r1)"
  - type: aosp
    path: "art/runtime/gc/reference_processor.cc:364-404 (android-17.0.0_r1)"
  - type: aosp
    path: "art/runtime/startup_completed_task.cc:42-72 (android-17.0.0_r1)"
  - type: aosp
    path: "art/runtime/native/dalvik_system_VMRuntime.cc:339-340 (android-17.0.0_r1)"
  - type: deepresearch
    path: "DeepResearch/2026-07-05-android17-art-heaptask-system-7-subclasses-source-closed-loop.md"
---

# 4.9 ART HeapTask 调度、启动维护与冻结边界

`HeapTask` 是 ART 进程内的延时任务抽象。它把“何时执行”和“执行什么”分开：`TaskProcessor` 按目标时间维护任务队列，Java 层的 `HeapTaskDaemon` 串行执行到期任务。GC 请求、堆裁剪、启动期清理、低开销方法追踪停止等工作都可以使用这套机制。任务到期只表示获得执行机会，是否执行 GC 或清理，还取决于各任务自己的检查条件。

它有两个边界：

- 它是 ART 运行时的内部设施，应用没有受支持的 API 可以启动、停止或改写队列。
- `target_footprint_` 是 ART 用来决定堆增长和 GC 时机的目标值，不是进程的硬内存上限，也不是 `lmkd` 的评分输入。

源码以 `android-17.0.0_r1` 为当前锚点。由于缺少逐版本源码标签证据，不能根据标题中的“新增子类”反推历史起点。Android 17 的生产源码中可以找到 **10 个** `HeapTask` 派生类，其中 6 个定义在 `heap.cc`。

## 4.9.1 从 Java 守护线程进入原生调度器

`libcore` 的 `Daemons` 创建四个守护线程：`HeapTaskDaemon`、`ReferenceQueueDaemon`、`FinalizerDaemon` 和 `FinalizerWatchdogDaemon`。其中 `HeapTaskDaemon` 的主循环可简化为：

```java
private static class HeapTaskDaemon extends Daemon {
    public synchronized void interrupt(Thread thread) {
        VMRuntime.getRuntime().stopHeapTaskProcessor();
    }

    @Override public void runInternal() {
        synchronized (this) {
            if (isRunning()) {
                VMRuntime.getRuntime().startHeapTaskProcessor();
            }
        }
        VMRuntime.getRuntime().runHeapTasks();
    }
}
```

这段代码说明了三个运行时事实：

1. Java 线程名固定为 `HeapTaskDaemon`，抓取线程调度数据时可以直接定位。
2. `startHeapTaskProcessor()` 注册当前运行线程并把处理器设为运行态。
3. `runHeapTasks()` 进入原生层主循环；停止守护线程时，`interrupt()` 调用的是 `stopHeapTaskProcessor()`。

这些 `VMRuntime` 方法都带有 `@hide`，不属于公开 SDK；`notifyStartupCompleted()` 和 `updateProcessState()` 也只是面向系统模块库的 `@SystemApi(client = MODULE_LIBRARIES)`。普通应用不应通过反射或 JNI 把它们当作性能开关。

原生层调用路径如下：

```text
java.lang.Daemons$HeapTaskDaemon
  -> dalvik.system.VMRuntime
  -> dalvik_system_VMRuntime.cc
  -> gc::TaskProcessor::RunAllTasks()
  -> HeapTask::Run()
  -> SelfDeletingTask::Finalize()
```

`HeapTask` 继承 `SelfDeletingTask`。任务从队列取出并执行 `Run()` 后，`RunAllTasks()` 紧接着调用 `Finalize()`；默认实现会释放任务对象。因此，任务一旦把所有权交给处理器，提交方就不能再次释放它。

## 4.9.2 队列怎样保证时间顺序

`TaskProcessor` 的核心容器是：

```cpp
std::multiset<HeapTask*, CompareByTargetRunTime> tasks_;
```

比较器只读取 `HeapTask::target_run_time_`，单位为纳秒。`GetTask()` 每次检查 `tasks_.begin()`，也就是目标时间最早的任务：

- 队列为空且处理器仍在运行时，线程在条件变量上睡眠，直到队列状态变化。
- 最早任务已经到期时，将它移出队列并返回。
- 最早任务尚未到期时，通过 `TimedWait()` 等待剩余时间。
- 新任务加入后会触发 `Signal()`，使等待线程重新检查队首。

`AddTask()` 会切换线程状态、获取互斥锁、插入 `multiset`，然后发送条件变量信号。它不会等待任务执行完毕，但提交过程仍需要加锁，不能描述成“无锁、无阻塞投递”。

### 修改执行时间为何要先移除再插入

`multiset` 不会在元素的排序字段原地改变后自动重排。`UpdateTargetRunTime()` 因而必须：

1. 在相同目标时间的范围内按指针找到任务；
2. 从集合移除任务；
3. 修改 `target_run_time_`；
4. 重新插入；
5. 如果它成为新队首，唤醒等待线程。

Android 17 中的 `CollectorTransitionTask` 和 `TimeBasedGcThresholdCheckTask` 会利用这种改期机制。理解这一点有助于排查“为什么更新了延时，任务仍按旧顺序运行”一类自定义 ART 问题。

### Stop 的含义是排空，而非丢弃

`TaskProcessor::Stop()` 把 `is_running_` 设为 `false`、清空 `running_thread_`，再广播条件变量。此后 `GetTask()` 遇到非空队列会忽略目标时间，立即返回任务。队列清空后才返回 `nullptr`，`RunAllTasks()` 随之退出。

因此：

- 停止处理器不会取消队列中的任务；
- 原定未来执行的任务可能在停止阶段提前运行；
- 析构时若仍有未处理任务，处理器会记录警告并调用它们的 `Finalize()`。

这个语义与 Java 源码中的注释一致：运行到停止，且没有待处理任务。

## 4.9.3 Android 17 中到底有多少种 HeapTask

统计数量必须先约定范围。只看 `art/runtime/gc/heap.cc` 有 6 种；搜索 Android 17 ART 运行时的生产 C++ 源码，共有 10 种。测试文件里的 `RecursiveTask`、`TestOrderTask` 不计入生产类型。

| 定义位置 | 派生类 | 用途 | 队列行为 |
|---|---|---|---|
| `gc/heap.cc` | `ConcurrentGCTask` | 发起并发 GC | 立即任务；用 GC 序号合并重复请求 |
| `gc/heap.cc` | `CollectorTransitionTask` | 执行待处理的收集器状态切换或后台压缩 | 同类任务只保留一个，可更新时间 |
| `gc/heap.cc` | `HeapTrimTask` | 裁剪 ART 空间、JNI 引用表和内存分配区（arena） | 同类任务只保留一个，重复请求直接忽略 |
| `gc/heap.cc` | `TimeBasedGcThresholdCheckTask` | 检查时间与存活堆大小相关的 GC 阈值 | 可改期，也可自行安排下一次检查 |
| `gc/heap.cc` | `ReduceTargetFootprintTask` | 进程派生后分阶段降低目标堆大小 | 到期时按 GC 序号决定是否仍需执行 |
| `gc/heap.cc` | `TriggerPostForkCCGcTask` | 启动后长时间没有 GC 时补发后台 GC | GC 序号已变化则成为空操作 |
| `gc/reference_processor.cc` | `ClearedReferenceTask` | 把已清理引用加入 Java `ReferenceQueue` | 该源码标签下默认不进入 `TaskProcessor` |
| `startup_completed_task.*` | `StartupCompletedTask` | 结束启动期、清理启动缓存和线程池 | 显式通知可立即提交，另有 5 秒兜底任务 |
| `trace_profile.cc` | `TraceStopTask` | 到期停止低开销方法追踪 | 按追踪结束时间执行 |
| `jit/jit.cc` | `MapBootImageMethodsTask` | 在即时编译器（JIT）通知后重映射启动镜像（boot image）方法 | 首次延时 10 秒，条件未满足则再延时 10 秒 |

只统计 `heap.cc` 会得到 6 种，统计整个 ART 运行时则会得到 10 种。分析代码时，应先说明统计目录，以及是否包含“继承了 `HeapTask`、但当前配置不经过队列”的类型。

### `ClearedReferenceTask` 是一个重要例外

Android 17 源码把：

```cpp
static constexpr bool kAsyncReferenceQueueAdd = false;
```

设为 `false`。`ReferenceProcessor::CollectClearedReferences()` 仍会创建 `ClearedReferenceTask`，但会把它作为 `SelfDeletingTask*` 返回给 GC 调用方，由调用方在合适的 GC 阶段执行；只有常量为 `true` 时才调用 `TaskProcessor::AddTask()`。

所以，继承关系只能证明它具备任务接口，不能证明当前构建会把它交给 `HeapTaskDaemon` 异步执行。

## 4.9.4 GC、切换和裁剪任务怎样避免重复工作

### ConcurrentGCTask：用 GC 序号合并请求

`RequestConcurrentGC()` 围绕 `max_gc_requested_` 做原子比较交换。GC 序号是随已完成回收单调递增的编号，用来判断某个请求是否已经被其他回收满足。只有成功把“已请求的最大 GC 序号”推进到下一号的线程会创建任务。任务运行时再比较当前 GC 序号：

- 若目标序号尚未完成，执行请求的 GC；
- 若别的线程已经完成相应 GC，不再重复执行；
- 调试用的连续 GC 模式会等待 1 ms 后申请下一项任务，避免 GC 线程持续占用执行机会。

这里的去重依据是单调递增的 GC 序号，不能简化成“队列按任务类型去重”。

### CollectorTransitionTask：保留一个对象并允许改期

`pending_collector_transition_` 保存当前待处理任务的指针。新请求到来时：

- 已有任务：更新目标时间，不再分配新对象；
- 没有任务：创建并保存指针，再加入队列；
- 任务运行结束：清空待处理任务指针。

这种策略适合“只关心末次状态与末次执行时间”的工作。

### HeapTrimTask：重复请求不改变原计划

`RequestTrim()` 发现 `pending_heap_trim_` 非空时直接返回，既不创建新任务，也不更新时间。裁剪可能扫描空间并持有空间锁，因此 ART 不会让相邻 GC 持续堆积裁剪请求。

`Heap::Trim()` 的范围比“调用一次 malloc 内存裁剪”更广：

- 在不关心暂停时间的进程状态下收缩监视器（monitor）结构；
- 裁剪全局和各线程的 JNI 间接引用表；
- 裁剪受管堆空间；
- 裁剪 JIT、验证器等使用的内存分配区映射。

大对象空间会自行裁剪；Zygote 空间在派生应用进程前已经裁剪，之后不再变化。

### TimeBasedGcThresholdCheckTask：按进度重新估算时间

该任务检查由“GC 后新增的堆量”和“距上次 GC 的时间”共同形成的进度，也可由功能开关切换到时间积分算法。达到阈值时，它会在 `PureTimeGcTrigger` 性能轨迹区间内申请后台 GC；尚未达到时，则按当前分配速度估算下一次检查时间。

为了避免每次分配都改期，源码还会：

- 活跃分配时按当前增长速率提前估算检查点；
- 在离旧检查点不足 10 ms 时不反复重排；
- 没有新增分配、处理器未运行或无法提交任务时，清除待处理状态，等待以后由分配行为再次触发。

这是一套“检查—估算—再检查”机制，不是固定周期定时器。

## 4.9.5 进程派生后为何先放宽堆目标，再逐步降低

应用进程刚由 Zygote 派生（fork）出来时，类加载、资源初始化和首帧准备会产生集中分配。Android 17 的 `Heap::PostForkChildAction()` 会先降低启动期 GC 干扰，再逐步恢复常态。

### 第一步：作废过早请求并放宽目标

函数开头先递增 `gcs_completed_`，使从 Zygote 继承或过早排入队列的 GC 请求因序号过期而失效。随后：

- 把下一次 GC 类型设为覆盖范围更大的非 sticky 类型（sticky 是源码中的回收范围分类）；
- 把理想堆占用目标（footprint）暂时提高到 `growth_limit_`；
- 按该目标设置并发 GC 启动阈值；
- 若启用了 time-based GC，清空相应阈值和积分状态。

`target_footprint_` 控制 ART 何时认为堆需要收集或增长，`growth_limit_` 才约束堆能够增长到的上界。把前者暂时提高到后者，是为了减少启动阶段因目标过紧而触发 GC 的机会。

它不会扩大清单中 `largeHeap` 对应的堆等级，也不会修改 `lmkd` 的 `oom_score_adj`、PSI 或内存控制组（memcg）状态。

### 第二步：按堆配置安排 0、1 或 2 次目标降低

源码常量 `kPostForkMaxHeapDurationMS` 为 2000 ms。调度分支如下：

| 条件 | 第一次降低 | 第二次降低 |
|---|---:|---:|
| `initial_heap_size_ >= growth_limit_` | 无 | 无 |
| `initial_heap_size_ < growth_limit_`，且等于第一次目标 | 派生后 2 秒 | 无 |
| `initial_heap_size_ < max(growth_limit_/4, initial_heap_size_)` | 派生后 2 秒 | 派生后 10 秒 |

第一次目标是 `max(growth_limit_ / 4, initial_heap_size_)`，第二次目标是 `initial_heap_size_`。`ReduceTargetFootprintTask` 只有在“自安排任务以来尚未发生 GC，且当前没有收集器运行”时才尝试降低目标，并重新计算并发 GC 启动点。若期间已经发生 GC，收集完成逻辑已经更新目标，这个任务无需再做相同工作。

降低 `target_footprint_` 本身不会马上执行 GC。只有后续分配跨过调整后的阈值时，才更可能触发收集。

### 第三步：为空闲进程安排一次兜底 GC

末尾一个 `TriggerPostForkCCGcTask` 会在基础时间上再等待：

```text
4 * 2000 ms + UID 确定的 [0, 19999] ms 偏移
```

偏移使用 UID 作为伪随机数种子，因此同一 UID 的结果稳定，不同 UID 的时间通常会分散。结合前面的可选目标降低任务，兜底任务相对进程派生时刻的目标时间为：

| 已安排的目标降低次数 | 兜底 GC 目标时间 |
|---:|---:|
| 0 次 | 8～27.999 秒 |
| 1 次 | 10～29.999 秒 |
| 2 次 | 18～37.999 秒 |

任务运行时还会比较 GC 序号。若启动期间已经发生 GC，它不会再申请一轮；只有长期未做 GC 的进程才会收到后台 GC 请求。因此，不能把这段代码概括为“派生后固定 10 秒强制 GC”或“每个进程固定创建三个有效任务”。

## 4.9.6 启动完成、追踪与 JIT 任务

### StartupCompletedTask 有显式通知和超时兜底

非 Zygote 应用进程完成派生后的设置时，会安排一个 5 秒后的 `StartupCompletedTask`，防止上层没有调用 `VMRuntime.notifyStartupCompleted()`。显式通知发生时，原生方法还会提交一个目标时间为当前时刻的任务。

`StartupCompletedTask::Run()` 会先调用 `Runtime::NotifyStartupCompleted()`。若这是首次成功完成通知，它会：

- 在 Java 不可调试、当前编译过滤器未启用预先编译（AOT），且 APK 没有应用镜像空间等条件同时满足时，尝试写入临时运行时应用镜像；
- 释放启动期 DEX 缓存和应用镜像元数据；
- 释放启动期使用的线性分配区（startup linear alloc）。

无论该通知是否已经由另一项任务完成，末尾都会尝试删除启动期使用的线程池。队列可能同时存在“立即任务”和“5 秒兜底任务”，幂等判断会让重复执行不产生额外副作用，从而避免核心清理运行两次。

### TraceStopTask 负责到期结束低开销方法追踪

`TraceProfiler::Start()` 为长耗时的方法追踪计算结束时间，并提交 `TraceStopTask`。任务到期后调用 `TraceProfiler::TraceTimeElapsed()`。若同类追踪延长，源码可能加入新的停止任务；停止逻辑会根据当前追踪状态和结束时间决定是否应结束，不能仅凭队列中存在多个任务判断发生了重复停止。

### MapBootImageMethodsTask 会轮询 JIT 条件

JIT 在进程派生后的阶段，若满足配置条件，会安排一个 10 秒后的任务。若任务发现 Zygote 方法映射的编译通知尚未到达，就再安排一个延后 10 秒的同类任务；条件满足后，它会暂停 Java 线程并调用 `MapBootImageMethods()`。

它展示了 `HeapTask` 的另一个用途：队列不只服务 GC，还可承载需要在 ART 专用守护线程上延后检查的运行时工作。

## 4.9.7 进程被冻结时会发生什么

`TaskProcessor` 没有专门识别缓存应用冻结器（Cached App Freezer）的代码。进程被冻结时，`HeapTaskDaemon` 无法获得 CPU，但墙钟时间会继续前进，所以任务目标时间可能已经过去。进程解冻后：

1. `GetTask()` 看到最早任务已经到期；
2. 取出并执行；
3. 继续检查下一项；
4. 多个逾期任务由同一个 `HeapTaskDaemon` 串行处理。

是否会执行 GC 仍取决于每个任务自身的守卫条件，例如 GC 序号、待处理任务指针和当前收集器状态。看到解冻后连续的 ART 工作时，应逐项核对任务条件，不能直接归因于“冻结期间积累了多轮 GC”。冻结期间任务没有获得 CPU 执行，积累的是已经到期的队列项。

## 4.9.8 如何在 Perfetto 中验证

`TaskProcessor::RunAllTasks()` 没有给每个 `HeapTask` 自动包一层通用性能轨迹，因此不能假定 Perfetto 必然出现与 C++ 类名相同的持续区间（slice）。可以依次核对这些可靠信号：

1. 在线程列表定位 `HeapTaskDaemon`，确认任务执行所在的线程。
2. GC 收集器用 `"<cause> <collector> GC"` 生成持续区间，具体名字取决于 GC 触发原因和收集器。
3. 基于时间的检查可见 `TimeBasedGcThresholdCheck`，达到阈值时还能看到 `PureTimeGcTrigger`。
4. `Heap::TrimSpaces()` 和 `Heap::TrimIndirectReferenceTables()` 使用函数名生成性能轨迹；监视器收缩显示为 `Deflating monitors`。
5. 启动清理可见 `Releasing dex caches and app image spaces metadata`、`Delete startup linear alloc` 和 `Delete thread pool`。
6. 低开销方法追踪有 `LowOverheadTraceLongRunning::Start`、相应停止信号及其生成的追踪数据。

设备是否开放某个 ATrace 类别、Perfetto 配置是否采集 ART 事件，会随构建类型和配置变化。排查时先确认数据源已启用，再用线程名、持续区间和 logcat 的 GC 记录互相校验。

### 一个可复现的排查顺序

面对“启动后十几秒突然出现 GC 或短暂停顿”，建议按下面的顺序判断：

1. 记录进程派生或启动、首帧、进入后台和冻结或解冻的时间。
2. 在 `HeapTaskDaemon` 时间线上定位到期工作。
3. 检查相邻 GC 持续区间的触发原因和收集器，确认是否属于 `Background` 请求。
4. 检查此前是否已经有 GC；若有，`TriggerPostForkCCGcTask` 按源码应成为空操作。
5. 对照设备堆配置，判断进程派生后安排了 0、1 还是 2 次堆占用目标降低。
6. 若只有内存裁剪或启动缓存清理，不把它误报成 GC。
7. 再回到分配速率、存活对象、线程暂停和 RSS/PSS 变化判断性能影响。

这种方法从可见证据回推具体任务，比看到 `HeapTaskDaemon` 忙碌就推断“ART 在强制回收”更可靠。

## 4.9.9 应用侧能做什么，不能做什么

应用可做的是减少触发任务后的代价：

- 用分配采样、堆转储和 GC 持续区间找到启动期集中分配与高存活对象；
- 推迟非首屏必需的对象构造，控制并发初始化造成的瞬时峰值；
- 区分 Java 堆、原生堆、图形内存、文件页和交换页，避免只用 PSS 判断 ART 堆；
- 结合 `onTrimMemory()` 管理应用缓存，但不要把回调与 `HeapTrimTask` 视为一一对应；
- 在可复现设备上比较首帧、GC 触发原因、暂停时间和释放字节，验证优化是否有效。

应用不应修改 ART 虚函数表（vtable）、私有字段或 `TaskProcessor` 队列来“抑制 GC”。这类做法依赖内部二进制接口（ABI）和对象布局，还会一并阻断堆裁剪、启动缓存释放、基于时间的检查、追踪停止及 JIT 映射任务。错误的任务所有权或待处理指针还可能造成释放后使用（use-after-free）、重复释放，或运行时停止阶段异常。

若系统产品确需调整策略，应在固定 AOSP 源码标签的平台代码中修改，并运行 ART 测试、启动测试、GC 压力测试和冻结或解冻测试，同时保留功能开关或设备配置入口。普通应用的优化目标应放在分配模式和对象生命周期上。

## 4.9.10 源码索引

| 主题 | Android 17 / `android-17.0.0_r1` 源码 |
|---|---|
| `HeapTask`、队列和比较器 | `art/runtime/gc/task_processor.h` |
| 加入、等待、改期、停止和排空 | `art/runtime/gc/task_processor.cc` |
| 6 个堆任务及进程派生后时序 | `art/runtime/gc/heap.cc` |
| Java 守护线程 | `libcore/libart/src/main/java/java/lang/Daemons.java` |
| 隐藏的 VMRuntime 接口 | `libcore/libart/src/main/java/dalvik/system/VMRuntime.java` |
| JNI 注册与启动完成通知 | `art/runtime/native/dalvik_system_VMRuntime.cc` |
| 5 秒启动兜底任务 | `art/runtime/native/dalvik_system_ZygoteHooks.cc` |
| 启动缓存与线程池清理 | `art/runtime/startup_completed_task.cc` |
| 已清理引用任务 | `art/runtime/gc/reference_processor.cc` |
| 追踪停止任务 | `art/runtime/trace_profile.cc` |
| 启动镜像方法映射任务 | `art/runtime/jit/jit.cc` |
| GC 持续区间命名 | `art/runtime/gc/collector/garbage_collector.cc` |

## 4.9.11 小结

- `HeapTaskDaemon` 是 Java 执行线程，`TaskProcessor` 是原生层的时间队列和调度循环。
- 队列按 `target_run_time_` 排序；改期必须移除后重插，停止时会提前排空剩余任务。
- Android 17 ART 运行时的生产源码共有 10 个 `HeapTask` 派生类，`heap.cc` 中有 6 个。
- `ClearedReferenceTask` 在该源码标签下默认由 GC 调用方执行，不能算作正常入队的异步任务。
- 进程派生后会暂时放宽 GC 目标，再按配置逐步降低；兜底 GC 的目标时间范围是 8～37.999 秒，并受先前 GC 序号保护。
- `target_footprint_` 是 ART GC/增长目标，不是硬堆上限，也不参与 lmkd 评分。
- Perfetto 排查应使用 `HeapTaskDaemon`、GC 触发原因、收集器和源码明确声明的持续区间，不能自行假设每个任务类都有同名事件。
- 普通应用没有受支持的 HeapTask 控制接口。绕过 ART 内部调度会同时破坏多类运行时工作。
