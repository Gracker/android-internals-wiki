---
title: "ART HeapTask 调度管线与 Android 17 新增子类"
chapter: "4.21"
status: ready-for-review
drafted_date: "2026-07-05"
applicable_versions: "Android 12 (API 31) - Android 17 (API 37)"
last_verified: "2026-07-05"
last_verified_against: "AOSP android-17.0.0_r1"
confidence: high
tags: [ART, GC, HeapTask, TaskProcessor, GC抑制, 启动性能, 内存管理]
related_chapters: ["4.8", "4.9", "4.11", "4.14", "4.16", "21.13", "23.5"]
created_by: "task2a-knowledge-gap"
created_date: "2026-07-05"
gap_source: "研究素材"
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

# 4.21 ART HeapTask 调度管线与 Android 17 新增子类

ART 的垃圾回收不是由某个单一函数驱动的，而是由一条 **4 层任务管线** 异步串联：Java 层的 `HeapTaskDaemon` 线程通过 JNI 进入 native 层的 `TaskProcessor` 主循环，后者从一个按时间排序的优先队列中取出 `HeapTask` 子类实例并依次执行。Android 17 对这条管线做了两项重大重构——C++ 侧类名从 `HeapTaskDaemon` 改为 `TaskProcessor`，以及新增 2 种服务于 zygote fork 后延迟收缩的 HeapTask 子类。本节以 `android-17.0.0_r1` 源码为基准，逐层拆解这条管线的完整链路。

[已验证: AOSP android-17.0.0_r1, art/runtime/gc/task_processor.cc + heap.cc]

---

## 4.21.1 四层任务管线架构

### Java 层：HeapTaskDaemon

ART 启动时会创建 4 个守护线程，`HeapTaskDaemon` 是其中之一（另三个是 `ReferenceQueueDaemon`、`FinalizerDaemon`、`FinalizerWatchdogDaemon`）：

```java
// Daemons.java:58-63, 743-768 (android-17.0.0_r1)
private static final Daemon[] DAEMONS = {
    HeapTaskDaemon.INSTANCE,
    ReferenceQueueDaemon.INSTANCE,
    FinalizerDaemon.INSTANCE,
    FinalizerWatchdogDaemon.INSTANCE,
};

private static class HeapTaskDaemon extends Daemon {
    private static final HeapTaskDaemon INSTANCE = new HeapTaskDaemon();
    HeapTaskDaemon() { super("HeapTaskDaemon"); }

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

关键设计：线程名 `"HeapTaskDaemon"` 始终保持——这意味着在 Perfetto / Systrace 中可以直接按线程名搜索定位，无需额外 instrumentation。

`runInternal()` 的生命周期很简单：先 `startHeapTaskProcessor()` 启动 native 侧的 `TaskProcessor`，然后 `runHeapTasks()` 进入 native 阻塞循环。当 `Daemons.stop()` 调用 `interrupt()` 时，实际语义不是发中断信号，而是调用 `stopHeapTaskProcessor()` 让 `TaskProcessor::Stop()` 把 `is_running_` 置为 false，主循环执行完剩余任务后退出。

### JNI 层：VMRuntime

`VMRuntime` 暴露了 4 个与 HeapTask 相关的 native 方法：

```java
// VMRuntime.java:871-905 (android-17.0.0_r1)
public native void startHeapTaskProcessor();
public native void stopHeapTaskProcessor();
public native void runHeapTasks();
public native void notifyStartupCompleted();
```

前三个方法对应 `TaskProcessor` 的启动 / 停止 / 主循环。`notifyStartupCompleted()` 是 Android 13 引入的启动完成通知，在 native 侧构造 `StartupCompletedTask` 交给 `Heap::AddHeapTask` 入队（`dalvik_system_VMRuntime.cc:339-340`）。

### Native 层：TaskProcessor 主循环

Android 17 将文件从 `heap_task_daemon.cc` 重命名为 `task_processor.cc`，但核心循环结构没有大变：

```cpp
// task_processor.cc:106-156 (android-17.0.0_r1)
void TaskProcessor::RunAllTasks(Thread* self) {
    while (true) {
        HeapTask* task = GetTask(self);
        if (task != nullptr) {
            task->Run(self);
            task->Finalize();
        } else if (!IsRunning()) {
            break;
        }
    }
}
```

每次循环取出一个 task → `Run()` 执行任务逻辑 → `Finalize()` 自删除（`SelfDeletingTask::Finalize` 做 `delete this`）。`GetTask()` 是阻塞的：队列空时 `cond_.Wait()` 等待新任务入队；非空时按 `target_run_time_` 排序取出最早到期的任务，若还没到执行时间则 `cond_.TimedWait(ms, ns)` 精确等待。

### 任务基类：HeapTask

```cpp
// task_processor.h:30-44 (android-17.0.0_r1)
class HeapTask : public SelfDeletingTask {
public:
    explicit HeapTask(uint64_t target_run_time) : target_run_time_(target_run_time) {}
    uint64_t GetTargetRunTime() const { return target_run_time_; }
private:
    void SetTargetRunTime(uint64_t new_target_run_time) {
        target_run_time_ = new_target_run_time;
    }
    uint64_t target_run_time_;
    friend class TaskProcessor;
};
```

继承链 `HeapTask → SelfDeletingTask → Task → Closure`。`Run` 是 `Task` 的虚函数，`Finalize` 是 `SelfDeletingTask` 的虚函数。这种虚函数设计是后续 GC 抑制方案能够通过 vtable 修改实现 Hook 的结构性前提。

> 🔗 详见 §4.8（ART 分代 GC）中关于 GC 触发时机与 `ShouldConcurrentGCForJava` 阈值判断的讨论。

---

## 4.21.2 七种 HeapTask 子类全景

Android 17 将 HeapTask 子类从历史版本的 5 种扩展到 **7 种**。下表为完整清单：

| 子类 | 定义位置 | 触发入口 | 核心行为 |
|---|---|---|---|
| `ConcurrentGCTask` | heap.cc:4113 | `RequestConcurrentGC()` | 触发并发 GC；`continuous_gc_mode_` 时自循环追加 |
| `CollectorTransitionTask` | heap.cc:4211 | `RequestCollectorTransition()` | GC 类型切换（如 NC→CC） |
| `HeapTrimTask` | heap.cc:4259 | `RequestTrim()` | `Heap::Trim()` + madvise 归还内存 |
| `ClearedReferenceTask` | reference_processor.cc:364 | `CollectClearedReferences()` | 异步将 cleared references 加入 `ReferenceQueue` |
| `StartupCompletedTask` | startup_completed_task.cc:42 | `VMRuntime.notifyStartupCompleted()` | 删除启动 dex cache + 写 runtime image |
| **`TriggerPostForkCCGcTask`** | heap.cc:5050 | `PostForkChildAction()` | **Android 17 新增**：fork 后强制触发一次后台 GC |
| **`ReduceTargetFootprintTask`** | heap.cc:5069 | `PostForkChildAction()` | **Android 17 新增**：渐进式收缩 heap target footprint |

### ConcurrentGCTask

```cpp
// heap.cc:4113-4141 (android-17.0.0_r1)
class Heap::ConcurrentGCTask : public HeapTask {
public:
    ConcurrentGCTask(uint64_t target_time, GcCause cause, bool force_full, uint32_t gc_num)
        : HeapTask(target_time), cause_(cause), force_full_(force_full), my_gc_num_(gc_num) {}
    void Run(Thread* self) override {
        gc::Heap* heap = Runtime::Current()->GetHeap();
        heap->ConcurrentGC(self, cause_, force_full_, my_gc_num_);
        if (UNLIKELY(heap->continuous_gc_mode_) && heap->task_processor_->IsRunning()) {
            usleep(1'000);  // 1ms backoff 防止 GC 线程吃满 CPU
            heap->RequestConcurrentGC(self, kGcCauseBackground, false, my_gc_num_);
        }
    }
};
```

`my_gc_num_` 是 GC 序列号，`RequestConcurrentGC` 在 `heap.cc:4158` 用 `max_gc_requested_.compare_exchange_weak` 做单飞（single-flight），避免同一 GC 号被多次入队。`continuous_gc_mode_` 是 debug/stress 模式开关，正常生产环境不开启。

### ClearedReferenceTask 与异步 Reference 入队

```cpp
// reference_processor.cc:364-377 (android-17.0.0_r1)
class ClearedReferenceTask : public HeapTask {
public:
    explicit ClearedReferenceTask(jobject cleared_references)
        : HeapTask(NanoTime()), cleared_references_(cleared_references) {}
    void Run(Thread* thread) override {
        ScopedObjectAccess soa(thread);
        WellKnownClasses::java_lang_ref_ReferenceQueue_add->InvokeStatic<'V', 'L'>(
            thread, soa.Decode<mirror::Object>(cleared_references_));
        soa.Env()->DeleteGlobalRef(cleared_references_);
    }
};
```

Android 17 默认 `kAsyncReferenceQueueAdd = true`，意味着 GC 清理出的 Reference 对象不再在 GC 暂停阶段同步入队，而是通过 HeapTask 异步处理。这是从「GC 暂停时同步」到「后台异步」的关键优化，减少了 GC 暂停时长。

> 🔗 详见 §4.9（FinalizerDaemon 与 ReferenceQueue 性能边界），其中讨论了 `ClearedReferenceTask` 异步入队对 Finalizer 时序的影响。

### StartupCompletedTask

```cpp
// startup_completed_task.cc:42-72 (android-17.0.0_r1)
void StartupCompletedTask::Run(Thread* self) {
    Runtime* const runtime = Runtime::Current();
    if (runtime->NotifyStartupCompleted()) {
        if (!runtime->IsJavaDebuggable()) {
            // 仅在非 AOT 编译模式下生成 runtime app image
            if (!CompilerFilter::IsAotCompilationEnabled(filter)
                && !runtime->GetHeap()->HasAppImageSpaceFor(primary_apk_path)) {
                RuntimeImage::WriteImageToDisk(&error_msg);
            }
        }
        DeleteStartupDexCaches(self, /* called_by_gc= */ false);
    }
    Runtime::Current()->DeleteThreadPool();
}
```

调用链：`ActivityThread.callApplicationOnCreate()` → 框架侧 → `VMRuntime.notifyStartupCompleted()` → JNI → `Heap::AddHeapTask(new StartupCompletedTask(NanoTime()))`。这是 Android 13 起的「首屏后异步清理启动 dex cache」机制，Android 17 沿用。

[已验证: AOSP android-17.0.0_r1, art/runtime/startup_completed_task.cc:42-72]

### TriggerPostForkCCGcTask（Android 17 新增）

```cpp
// heap.cc:5050-5067 (android-17.0.0_r1)
class Heap::TriggerPostForkCCGcTask : public HeapTask {
public:
    TriggerPostForkCCGcTask(uint64_t target_time, uint32_t initial_gc_num)
        : HeapTask(target_time), initial_gc_num_(initial_gc_num) {}
    void Run(Thread* self) override {
        gc::Heap* heap = Runtime::Current()->GetHeap();
        if (heap->GetCurrentGcNum() == initial_gc_num_) {  // fork 后还没 GC 过
            heap->RequestConcurrentGC(self, kGcCauseBackground, false, initial_gc_num_);
        }
    }
};
```

核心逻辑：检查 `GetCurrentGcNum() == initial_gc_num_`，即从 fork 到任务执行期间是否已经发生过 GC。如果已经 GC 过，说明其他路径已经清理了启动垃圾，本任务跳过；否则强制触发一次后台并发 GC。`gc_num` 检查是幂等保证，避免重复 GC。

### ReduceTargetFootprintTask（Android 17 新增）

```cpp
// heap.cc:5069-5092 (android-17.0.0_r1)
class Heap::ReduceTargetFootprintTask : public HeapTask {
public:
    ReduceTargetFootprintTask(uint64_t target_time, size_t new_target_sz, uint32_t initial_gc_num)
        : HeapTask(target_time), new_target_sz_(new_target_sz), initial_gc_num_(initial_gc_num) {}
    void Run(Thread* self) override {
        gc::Heap* heap = Runtime::Current()->GetHeap();
        MutexLock mu(self, *(heap->gc_complete_lock_));
        if (heap->GetCurrentGcNum() == initial_gc_num_
            && heap->collector_type_running_ == kCollectorTypeNone) {
            size_t target_footprint = heap->target_footprint_.load(std::memory_order_relaxed);
            if (target_footprint > new_target_sz_) {
                if (heap->target_footprint_.CompareAndSetStrongRelaxed(target_footprint, new_target_sz_)) {
                    heap->SetDefaultConcurrentStartBytesLocked();
                }
            }
        }
    }
};
```

同样通过 `gc_num` 做幂等检查。`CompareAndSetStrongRelaxed` 是原子操作，确保在多线程环境下安全地缩小 heap 上限。如果当前 footprint 已经小于目标值（可能因为其他 GC 已经收缩过），则不做操作。

[已验证: AOSP android-17.0.0_r1, art/runtime/gc/heap.cc:5050-5092]

---

## 4.21.3 优先队列调度模型

Android 14 起，`TaskProcessor` 的任务队列从 FIFO 链表重写为 **按 `target_run_time_` 排序的 `std::multiset`**：

```cpp
// task_processor.h (android-17.0.0_r1)
std::multiset<HeapTask*, CompareByTargetRunTime> tasks_;
```

`CompareByTargetRunTime` 是一个比较器，按 `HeapTask::GetTargetRunTime()` 升序排列。这意味着：

1. **最早到期的任务排在最前**，`GetTask` 每次取 `tasks_.begin()`
2. **支持动态重排序**：`UpdateTargetRunTime` 可以修改已在队列中的任务的 `target_run_time_`，multiset 会自动重新排序
3. **多个任务可以有相同的 target_run_time**（multiset 允许重复）

`GetTask()` 的核心逻辑（task_processor.cc:41-72）：

```
循环 {
    如果队列空 && is_running_:
        cond_.Wait()  // 无限等待新任务
    如果队列非空:
        task = *tasks_.begin()
        如果 now < task.target_run_time:
            cond_.TimedWait(delta_ms, delta_ns)  // 精确等待到目标时间
        否则:
            tasks_.erase(task)
            return task
    如果 !is_running_ && 队列空:
        return nullptr  // 触发 RunAllTasks 退出
}
```

`AddTask()` 仅做 `tasks_.insert(task)` + `cond_.Signal()`，是非阻塞操作。

这个调度模型的关键影响：任务不是先到先执行，而是 **按预定时间执行**。一个 `HeapTrimTask`（延迟 1s）和一个 `ConcurrentGCTask`（延迟 0ms）同时入队时，后者会先执行。`CollectorTransitionTask` 的 `RequestCollectorTransition` 入队前会检查是否已有 pending 的同类型任务——如果有，只调用 `UpdateTargetRunTime` 调整时间，不重复入队，这就是 **去重（dedup）** 机制。

---

## 4.21.4 PostForkChildAction 与启动 GC 窗口

`PostForkChildAction` 是 Android 17 新增的 zygote fork 后处理逻辑（heap.cc:5113-5161），它一次性向 `TaskProcessor` 入队 **3 个任务**：

| 序号 | 任务 | 延迟 | 目标 |
|---|---|---|---|
| 1 | `ReduceTargetFootprintTask` | `kPostForkMaxHeapDurationMS`（≈2s） | 第一次收缩到 `max(growth_limit/4, initial_heap_size)` |
| 2 | `ReduceTargetFootprintTask` | `5 × kPostForkMaxHeapDurationMS`（≈10s） | 第二次收缩到 `initial_heap_size` |
| 3 | `TriggerPostForkCCGcTask` | `4 × kPostForkMaxHeapDurationMS + random` | 强制触发一次后台 GC |

```
// heap.cc:5132-5161 (简化伪代码)
size_t first_shrink = max(growth_limit_ / 4, initial_heap_size_);
last_adj_time += MsToNs(kPostForkMaxHeapDurationMS);  // +2s
AddTask(new ReduceTargetFootprintTask(last_adj_time, first_shrink, starting_gc_num));

if (initial_heap_size_ < first_shrink) {
    last_adj_time += MsToNs(4 * kPostForkMaxHeapDurationMS);  // 再 +8s
    AddTask(new ReduceTargetFootprintTask(last_adj_time, initial_heap_size_, starting_gc_num));
}

uint64_t post_fork_gc_time = last_adj_time + GetPseudoRandomFromUid();
AddTask(new TriggerPostForkCCGcTask(post_fork_gc_time, starting_gc_num));
```

### GetPseudoRandomFromUid：防 GC 风暴

```cpp
// heap.cc:5077-5082 (android-17.0.0_r1)
uint64_t Heap::GetPseudoRandomFromUid() {
    std::default_random_engine engine(getuid());
    std::uniform_int_distribution<int> dist(0, 20000);  // [0, 20000) ms
    return MsToNs(dist(engine));
}
```

基于 `getuid()` 生成 `[0, 20)` 秒的伪随机偏移。不同应用 uid 不同，fork 后触发 GC 的时刻被自然分散开。这解决了多应用同时启动时「GC 风暴」的问题——在没有这个机制的历史版本中，系统启动阶段所有应用几乎同时触发 GC，造成 CPU 抖动和 IO 竞争。

### 启动窗口的故障模式

如果 `HeapTaskDaemon` 被阻塞（无论是 native hook 还是系统资源竞争），这 3 个 PostFork 任务无法执行，后果是：

1. **启动垃圾无法回收**：fork 从 zygote 继承的大量启动期对象继续占用 heap
2. **target_footprint 不收缩**：app 内存上限保持 zygote 级别，LMKd 评分偏高
3. **ANR / OOM 风险**：启动后 5×`kPostForkMaxHeapDurationMS`（≈10s）窗口内如果还不回收，新分配叠加启动残留可能导致 OOM

[已验证: AOSP android-17.0.0_r1, art/runtime/gc/heap.cc:5077-5161]

---

## 4.21.5 GC 抑制在 Android 17 的风险升级

### 守门条件

所有 HeapTask 入队前都经过 `CanAddHeapTask` 守门：

```cpp
// heap.cc:4143-4148 (android-17.0.0_r1)
static bool CanAddHeapTask(Thread* self) {
    Runtime* runtime = Runtime::Current();
    return runtime != nullptr && runtime->IsFinishedStarting() && !runtime->IsShuttingDown(self)
        && !self->IsHandlingStackOverflow<kNativeStackType>();
}
```

4 个条件：runtime 非空、启动完成、未在 shutdown、未处理 native 栈溢出。只要 `HeapTaskDaemon` 线程在跑，任务就会持续入队。

### 虚函数 Hook 路径

`HeapTask::Run` 是虚函数。理论上可以通过以下步骤实现 GC 抑制：

1. 在 libart.so 的 `.symtab` 段定位 `HeapTask` 的 vtable
2. 找到 `Run` 虚函数的 entry
3. `mprotect` 修改内存页权限
4. 将 `Run` 函数指针替换为一个直接 `return` 的 stub

替换后，任务照常入队、出队、执行——但 `Run()` 立即返回，GC 逻辑不会被执行。`Finalize()` 仍然正常调用（`delete this`），不会内存泄漏。

### Android 17 的风险升级点

Android 17 **没有引入任何 anti-hook 校验**（如 vtable 完整性检查、代码段只读校验等），因此上述 Hook 方案在技术上仍然可行。但风险显著升高：

| 风险维度 | Android 16 及以前 | Android 17 |
|---|---|---|
| PostFork 任务 | 无或单次 | **3 个任务（2 次收缩 + 1 次 GC）** |
| 抑制有效窗口 | 启动全程可抑制 | **严格限制在首屏后 ≈10s 内** |
| 收缩失败后果 | footprint 保持偏高 | **target_footprint 不收缩 → LMKd 评分高 → 更易被杀** |
| GC 不执行后果 | 启动垃圾堆积 | **叠加 PostFork GC 不触发 → 启动垃圾 + zygote 残留双重堆积** |

核心结论：Android 17 的 PostFork 任务让 GC 抑制的 **有效窗口被严格压缩到 ≈10 秒**，超过这个窗口后 `TriggerPostForkCCGcTask` 的缺失会直接导致内存压力累积。抑制方案在启动加速场景下仍有短期价值，但长期运行风险显著高于历史版本。

> 🔗 详见 §23.5（内存抖动与 GC 抑制实战），其中讨论了业务侧 GC 抑制方案的实施细节和收益评估。

---

## 4.21.6 Perfetto 可观测性

HeapTask 管线的运行状态可以通过 Perfetto / Systrace 直接观测：

### 线程级观测

- **线程名**：`HeapTaskDaemon`（Java 层保持不变），可在 trace 的 thread track 中直接搜索
- **调度状态**：通过 `sched_switch` 事件观察该线程的唤醒 / 睡眠模式
- **等待模式**：`TaskProcessor::GetTask` 中的 `cond_.Wait()` 和 `cond_.TimedWait()` 表现为 futex 系统调用，在 trace 中可见

### 各子类的 trace 特征

| 子类 | trace 识别方式 |
|---|---|
| `ConcurrentGCTask` | atrace 的 `ConcurrentGC` slice，持续时间 ≈ 并发 GC 标记阶段 |
| `HeapTrimTask` | atrace 的 `HeapTrim` slice，包含 `madvise` 系统调用 |
| `CollectorTransitionTask` | atrace 的 `CollectorTransition` slice |
| `ClearedReferenceTask` | 通常很短（<1ms），在 trace 中不容易单独识别 |
| `StartupCompletedTask` | atrace 的 `StartupCompleted` slice，可能包含 `WriteImageToDisk` |
| `TriggerPostForkCCGcTask` | 间接触发一次 `ConcurrentGC` slice，在 fork 后 ≈10s |
| `ReduceTargetFootprintTask` | 极短（CAS 操作），通常不可见；间接效果是后续 GC 阈值变化 |

### 推荐的 trace 抓取命令

```bash
# 抓取包含 ART GC 和 sched 事件的 trace
adb shell perfetto -o /data/misc/perfetto-traces/trace.pb -t 30s \
    sched freq idle am wm view dalvik gc
```

关键分析路径：在 trace 中找到 `HeapTaskDaemon` 线程 → 观察其唤醒频率和每次执行的任务类型 → 对照 `ConcurrentGC` slice 确认 GC 执行时间 → 检查 fork 后 10s 窗口内是否有 PostFork 相关的 GC 活动。

[已验证: 官方文档, perfetto.dev/docs/data-sources]

---

## 扩展

### 🔸 GC 抑制方案的替代策略

直接 Hook vtable 是最激进但也是最高风险的 GC 抑制方式。更低风险的替代策略包括：

1. **调整 GC 阈值**：通过 `VMRuntime.getRuntime().updateProcessState(int)` 通知 ART 进入非感知状态，降低 concurrent GC 的触发频率。这是官方 API，无 Hook 风险。

2. **修改 concurrent start bytes**：通过 native 层修改 `concurrent_start_bytes_` 的值，让 ART 误判 heap 还未达到触发阈值。比 vtable Hook 风险低，但需要符号偏移。

3. **利用 `continuous_gc_mode_ = false`**：确保不会进入 stress 模式的自循环追加路径。

> 🔗 §21.13 中讨论了启动阶段 GC 抑制的业务实践方案和收益/风险评估。

[待验证: 替代方案的具体实现细节需要结合业务侧框架源码进一步验证]

### 🔸 TaskProcessor 与 Cached App Freezer 的交互

当应用被 Cached App Freezer 冻结时（详见 §4.11），整个进程的线程被冻结，`HeapTaskDaemon` 也不例外。解冻后 `TaskProcessor` 的行为取决于冻结期间是否有任务到期：

- 如果 `target_run_time` 在冻结期间已过，解冻后 `GetTask` 会立即返回该任务（`now > target_run_time`），造成 **任务积压 burst**
- `ConcurrentGCTask` 可能堆积多个（但由于 `max_gc_requested_` 的 single-flight 去重，实际只执行一次）
- `ReduceTargetFootprintTask` 的 `gc_num` 检查会导致过期任务被跳过

Android 17 没有为 freezer 场景做特殊处理——`TaskProcessor` 不感知冻结状态，冻结只是暂停了时间流逝。

> 🔗 详见 §4.11（Cached App Freezer 与 GC 触发边界）

### 🔸 跨版本 HeapTask 演进

| 维度 | Android 11-13 | Android 14-16 | **Android 17** |
|---|---|---|---|
| 文件名 | `heap_task_daemon.cc` | `heap_task_daemon.cc` | **`task_processor.cc`** |
| 任务队列 | FIFO 链表 | multiset（按时间排序） | 同 Android 14+ |
| HeapTask 子类数 | 4 | 5 | **7** |
| `kAsyncReferenceQueueAdd` | 默认 false | 默认 true | **默认 true** |
| PostFork 收缩 | 无 HeapTask 机制 | 单次收缩 | **2 次渐进 + 1 次后置 GC** |
| 防 GC 风暴 | 无 | 无 | **`GetPseudoRandomFromUid`** |
| StartupCompletedTask | 无 | Android 13 引入 | **沿用** |

关键拐点：
- **Android 13**：引入 `StartupCompletedTask` 和 `kAsyncReferenceQueueAdd`，HeapTask 从单纯的 GC 触发器扩展为通用任务调度器
- **Android 14**：任务队列从 FIFO 重写为 multiset 优先队列，支持精确的时间调度
- **Android 17**：新增 PostFork 任务族 + 防 GC 风暴随机化，完成了 zygote fork 后内存管理的 HeapTask 化改造

[已验证: AOSP android-17.0.0_r1 对比历史版本源码; Android 11-13 的 FIFO 链表和子类数量基于历史源码记录]
[待验证: Android 14-16 的中间态部分细节未经逐版本源码比对]
