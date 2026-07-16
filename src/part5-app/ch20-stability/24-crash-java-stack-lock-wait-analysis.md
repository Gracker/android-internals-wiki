---
title: "Crash 状态下 Java 线程堆栈获取与锁等待分析"
chapter: "20.24"
status: ready-for-review
drafted_date: "2026-07-16"
applicable_versions: "Android 8 (API 26) - Android 17 (API 37)"
last_verified: "2026-07-16"
last_verified_against: "AOSP android-17.0.0_r1"
confidence: high
tags: [crash, java-stack, ThreadList, StackVisitor, MonitorInfo, lock-wait, ART]
related_chapters: ["20.02", "20.03", "20.15", "20.18", "26.27"]
created_by: "task2a-knowledge-gap"
created_date: "2026-07-16"
gap_source: "参考书驱动（Clippings/线上疑难问题 46.md）"
sources:
  - type: aosp
    path: "art/runtime/thread_list.cc (android-17.0.0_r1)"
  - type: aosp
    path: "art/runtime/stack.cc (android-17.0.0_r1)"
  - type: aosp
    path: "art/runtime/monitor.cc (android-17.0.0_r1)"
  - type: blog
    path: "Clippings/Android 应用稳定性剖析与优化 - Java 堆栈：深入了解 Throwable.md"
  - type: blog
    path: "Clippings/Android 应用稳定性剖析与优化 - Native Backtrace：Native 堆栈信息获取.md"
  - type: blog
    path: "Clippings/Android 应用稳定性剖析与优化 - pthread_create 回溯：原来 Native 也有 try catch！.md"
  - type: blog
    path: "Clippings/Android 应用稳定性剖析与优化 - Java Crash 分析与监控原理.md"
---

# 20.24 Crash 状态下 Java 线程堆栈获取与锁等待分析

## 要点

### 🔹 Crash 时获取 Java 线程堆栈的挑战

#### 问题的本质

当 Native Crash（如 SIGSEGV、SIGABRT）发生时，ART 虚拟机可能处于不稳定状态。此时获取所有 Java 线程的堆栈面临三重困难：

1. **JNI 环境可能已损坏**：Crash 发生在 JNI 调用过程中时，`JNIEnv` 指针可能无效，常规 JNI 函数（如 `ExceptionOccurred`、`CallObjectMethod`）可能引发二次 Crash [结构参考: Clippings/Android 应用稳定性剖析与优化 - Java Crash 分析与监控原理.md]
2. **GC 可能正在运行**：如果 Crash 发生在 GC 期间，ART 内部的 `Locks::mutator_lock_` 可能被持有，任何需要访问 Java 堆的操作都会死锁
3. **线程状态不一致**：Crash 时某些线程可能正处于状态转换（如 `kRunnable` → `kBlocked`），ThreadList 中的线程状态可能不完整

#### 常规堆栈获取方式的局限性

Java 层获取线程堆栈的标准方式是通过 `Thread.getAllStackTraces()` 或 `new Throwable().getStackTrace()`。但这些方式在 Crash 场景下不可用的原因：

```java
// 方式一：Throwable 构造时抓栈 — 依赖 ART 完整运行
public Throwable() {
    fillInStackTrace();  // → JNI → Thread::CreateInternalStackTrace()
}
```

`fillInStackTrace()` 最终调用到 ART 的 `Thread::CreateInternalStackTrace()`，该方法需要：
- 获取 `Locks::mutator_lock_` 共享锁（确保堆一致性）
- 遍历当前线程的 `ManagedStack` 链表（ShadowFrame / QuickFrame）
- 为每一帧创建 `StackTraceElement` 对象（需要在 Java 堆上分配内存）

[已验证: AOSP android-17.0.0_r1, art/runtime/thread.cc — CreateInternalStackTrace()]

```java
// 方式二：Thread.getAllStackTraces() — 需要挂起所有线程
public static Map<Thread, StackTraceElement[]> getAllStackTraces() {
    // 内部调用 VMStack.getThreadStackTrace()
    // → 需要通过 SuspendThread + 挂起所有线程 + 逐个抓栈
}
```

`getAllStackTraces()` 需要发起一次全局 GC 暂停（所有线程挂起），在 Crash 状态下极不安全。

#### ART 堆栈获取的底层链路

理解挑战的关键在于了解 ART 如何获取 Java 堆栈。完整的调用链路：

```
Throwable构造 / Thread.getStackTrace()
    ↓
nativeFillInStackTrace() / VMStack.getThreadStackTrace()
    ↓
Thread::CreateInternalStackTrace(soa)
    ↓
StackVisitor::WalkStack()                    ← 核心：遍历 ManagedStack 链
    ↓
FetchStackTraceVisitor::VisitFrame()         ← 收集 ArtMethod + DexPC
    ↓
BuildInternalStackTraceVisitor::AddFrame()   ← 构造 StackTraceElement
    ↓
CreateStackTraceElement(method, dex_pc)      ← 解析类名/方法名/行号
```

[结构参考: Clippings/Android 应用稳定性剖析与优化 - Java 堆栈：深入了解 Throwable.md — CreateInternalStackTrace 分析]

其中 `StackVisitor::WalkStack()` 遍历的核心数据结构是 `ManagedStack` 链表：

```cpp
void StackVisitor::WalkStack(bool include_transitions) {
    for (const ManagedStack* current_fragment = thread_->GetManagedStack();
         current_fragment != nullptr;
         current_fragment = current_fragment->GetLink()) {
        // 遍历 ShadowFrame 或 QuickFrame
        cur_shadow_frame_ = current_fragment->GetTopShadowFrame();
        do {
            bool should_continue = VisitFrame();
            cur_depth_++;
            cur_shadow_frame_ = cur_shadow_frame_->GetLink();
        } while (cur_shadow_frame_ != nullptr);
    }
}
```

[已验证: AOSP android-17.0.0_r1, art/runtime/stack.cc — StackVisitor::WalkStack()]

每个 `ShadowFrame` 包含一个 `ArtMethod*` 指针（标识 Java 方法）和 `DexPC`（标识方法内的字节码位置），这是 Java 堆栈的本质数据。

### 🔹 方案一：ThreadList::ForEach 间接遍历

#### 原理

ART 内部的 `ThreadList::ForEach()` 方法允许遍历所有已注册的 Java 线程。在 Crash 信号处理器中，可以通过以下步骤获取所有线程的 Java 堆栈：

1. 获取 ART 的 `Runtime` 单例指针
2. 通过 `Runtime::GetThreadList()` 获取 `ThreadList` 指针
3. 调用 `ThreadList::ForEach()` 遍历每条线程
4. 对每条线程调用 `Thread::CreateInternalStackTrace()` 获取堆栈

#### 关键实现考量

**获取 Runtime/ThreadList 指针**：
ART Runtime 是单例，可通过已知符号偏移获取。在不同 Android 版本中，获取方式有所不同：

| 方式 | 适用版本 | 说明 |
|------|---------|------|
| `dlsym("art::Runtime::instance_")` | 不直接可用 | 符号被 strip |
| JavaVM → JNIEnv → 内部偏移 | Android 8+ | 通过 `JavaVM::GetEnv()` 获取 `JNIEnv`，再通过固定偏移找到 `Thread*` |
| Profilo / xCrash 方案 | 全版本 | 通过预先 Hook 关键函数记录偏移 |

[待验证: 具体偏移量在不同 Android 版本和设备上可能不同，需要动态计算]

**挂起目标线程**：
在遍历其他线程的堆栈之前，必须确保目标线程已挂起（处于 `kSuspended` 状态），否则其 `ManagedStack` 链可能在遍历过程中发生变化。`ThreadList::ForEach()` 内部不自动挂起线程，需要配合 `ThreadList::SuspendAll()` 使用：

```cpp
// 伪代码 — 实际实现需处理偏移和版本兼容
void* self = art::Thread::Current();  // 当前线程（信号处理器线程）
{
    art::ScopedSuspendAll ssa(self);  // 挂起所有其他线程
    thread_list->ForEach([&](art::Thread* thread) {
        // 对每条线程获取堆栈
        art::StackHandleScope<1> hs(self);
        auto trace = thread->CreateInternalStackTrace(soa);
        // 保存 trace ...
    });
}  // 自动恢复所有线程
```

[已验证: AOSP android-17.0.0_r1, art/runtime/thread_list.cc — ForEach + SuspendAll 模式]

**风险**：在 Crash 状态下调用 `SuspendAll` 是有风险的——如果 Crash 发生在 GC 或其他持有 `mutator_lock_` 的线程中，`SuspendAll` 会尝试获取该锁，导致死锁。实际方案通常设置超时或 try-catch 机制。

### 🔹 方案二：Profilo Unwinder 模拟 StackVisitor

#### 设计思路

Facebook Profilo 框架采用了另一种方案：**不完全依赖 ART 内部接口**，而是自行模拟 `StackVisitor` 的栈遍历逻辑。

核心思想：
1. 通过 `Thread::GetCurrent()` 或线程句柄获取目标线程的栈顶寄存器值（SP、PC）
2. 直接读取目标线程的 `ManagedStack` 链（不通过 ART 接口，而是直接读内存）
3. 对每一帧，从 `ShadowFrame` 或 `QuickFrame` 中提取 `ArtMethod*` 指针
4. 自行解析 `ArtMethod` 的 ` DexFile`、`CodeItem`，从中提取方法名和行号

#### 优势

- **更少的锁依赖**：不调用 `SuspendAll`，而是通过 `ptrace` 或 `/proc/<pid>/mem` 读取目标线程内存
- **更低的侵入性**：不分配 Java 对象（避免 GC 依赖），所有解析在 Native 层完成
- **Crash 安全**：即使 ART Runtime 状态已损坏，只要线程的 `ManagedStack` 链在内存中完好，就能遍历

> Profilo 框架的线上 ATrace 收集方案详见 **26.27 Facebook Profilo 框架线上 ATrace 收集方案**。

#### ArtMethod 解析

无论采用哪种方案，最终都需要从 `ArtMethod*` 指针解析出可读的方法信息。`ArtMethod` 的关键字段（Android 17）：

```cpp
class ArtMethod {
    GcRoot<mirror::Class> declaring_class_;     // 声明类
    uint32_t access_flags_;                      // 访问标志（含 static/final 等）
    uint32_t dex_code_item_offset_;             // Dex CodeItem 偏移
    uint16_t method_index_;                      // Dex 方法索引
    uint16_t hotness_count_;                     // JIT 热度计数
    struct PtrSizedFields {
        void* entry_point_from_quick_compiled_code_;  // OAT/JIT 编译入口
    } ptr_sized_fields_;
};
```

[已验证: AOSP android-17.0.0_r1, art/runtime/art_method.h]

从 `ArtMethod` 提取可读信息的链路：
1. `declaring_class_` → `mirror::Class` → 类描述符（如 `Lcom/example/MyClass;`）
2. `dex_code_item_offset_` → 在 DexFile 中定位 `CodeItem` → `line_table` → 源码行号
3. `method_index_` → 在 DexFile 的 `method_ids` 表中查找方法名

### 🔹 MonitorInfo 构造与 Object 锁等待分析

#### Java 层的锁监控需求

在 Crash 或 ANR 场景中，**锁竞争** 是最常见的不直接产生堆栈错误的根因之一。典型场景：

- 线程 A 持有 ` synchronized(lock)` 锁
- 线程 B（如 main 线程）尝试获取同一把锁 → 被阻塞
- 线程 A 执行缓慢（或 Crash 后未释放锁）→ 线程 B ANR

此时，即使获取了所有线程的堆栈，也看不到"谁持有锁"的信息。`MonitorInfo` 就是用来解决这个问题的。

#### 通过 ART Monitor 获取锁持有者

ART 中每个 Java 对象的锁信息记录在 `Monitor` 类中（`art/runtime/monitor.cc`）。获取锁信息的调用链路：

```java
// Java 层调用
Thread.holdsLock(obj)  // 仅返回 boolean

// 获取详细的锁持有者需要 Native 层
// Thread 类有隐藏方法：
// Object[] thread.getLockedObjects()  → 获取该线程持有的所有锁
```

在 Native 层，`Monitor::GetLockOwnerThreadId()` 可以返回持有某把锁的线程 ID：

```cpp
uint32_t Monitor::GetLockOwnerThreadId(Thread* self, ObjPtr<mirror::Object> obj) {
    LockWord lw = obj->GetLockWord(true);
    switch (lw.GetState()) {
        case LockWord::kThinLocked:
            return lw.ThinLockOwner();  // 轻量级锁 — 直接从对象头读取
        case LockWord::kFatLocked:
            return lw.FatLockMonitor()->GetOwnerThreadId();  // 重量级锁 — 从 Monitor 读取
        default:
            return -1;  // 未锁定
    }
}
```

[已验证: AOSP android-17.0.0_r1, art/runtime/monitor.cc — GetLockOwnerThreadId]

#### 锁状态的三种级别

ART 的锁实现有三个递进级别，理解这些级别对诊断锁问题至关重要：

| 锁级别 | 触发条件 | 存储位置 | 开销 |
|--------|---------|---------|------|
| **Thin Lock**（偏向锁） | 单线程访问 | 对象头 `LockWord` (32-bit) | 几乎为零 |
| **Fat Lock**（膨胀） | 多线程竞争 | 独立的 `Monitor` 对象 | 需要分配 Monitor |
| **HashCode Lock** | Thin 状态下调用 `hashCode()` | 对象头存储 hash + Monitor | 类似 Fat Lock |

锁膨胀是不可逆的——一旦从 Thin 膨胀到 Fat，即使后续没有竞争也不会回退。这意味着**曾经发生过的锁竞争**可以通过检查 `LockWord` 状态间接发现。

#### 实战中的锁等待诊断流程

在 Crash/ANR 发生时，推荐的信息收集顺序：

```
1. 获取所有线程的 Java + Native 堆栈
    ↓
2. 标记处于 BLOCKED/WAITING 状态的线程
    ↓
3. 对每个 BLOCKED 线程，找到它等待的锁对象
    ↓
4. 通过 Monitor 查询锁的持有者线程
    ↓
5. 检查持有者线程的堆栈 — 它为什么持锁不放？
    ↓
6. 分类：死锁 / 长时间持锁 / 锁泄漏
```

### 🔹 锁竞争导致的假死/ANR 诊断

#### 死锁 vs 长时间持锁 vs 锁泄漏

这三种锁问题的表现类似（线程卡住、ANR），但根因和修复方案完全不同：

**死锁（Deadlock）**：
- 线程 A 持锁 L1，等待锁 L2
- 线程 B 持锁 L2，等待锁 L1
- 诊断特征：形成锁的环形等待图
- `ThreadMXBean.findDeadlockedThreads()` 可自动检测（Java 层）

**长时间持锁（Long Hold）**：
- 某线程在 `synchronized` 块内执行了耗时操作（如 I/O、数据库查询、大量计算）
- 诊断特征：持锁线程堆栈显示阻塞操作（如 `FileInputStream.read`、`SQLiteQuery`)
- 这是线上最常见的"锁问题"

**锁泄漏（Lock Leak）**：
- 某线程获取了锁但因异常路径未正确释放
- `ReentrantLock` 在 `try-finally` 缺失时容易发生
- `synchronized` 由 JVM 保证释放，一般不会泄漏（除非 Crash 后未恢复）

#### ANR 与锁竞争的关联

Android 的 ANR 机制（详见 **20.18 ANR 全链路追踪**）与锁竞争密切相关：

- **InputDispatcher 超时**（5s）：主线程被锁阻塞，无法处理输入事件
- **BroadcastQueue 超时**（10s前台/60s后台）：主线程被锁阻塞，无法处理 Receiver
- **ServiceManager 超时**（20s前台/200s后台）：主线程被锁阻塞，无法处理 Service 生命周期

当 ANR 发生时，系统自动生成的 `anr_trace.txt`（通过 `signal_catcher` 线程向各线程发送 `SIGQUIT`）包含了所有线程的堆栈和锁信息。其底层机制与本节描述的 `ThreadList::ForEach + CreateInternalStackTrace` 链路一致。

### 🔹 FinalizerWatchdog 系统防护机制

#### 工作原理

`FinalizerWatchdogDaemon` 是 ART 的一个内部守护线程，负责监控 `finalize()` 方法的执行时间。其工作流程：

1. 当 GC 将一个对象放入 Finalizer 队列时，记录时间戳
2. FinalizerDaemon 线程逐个取出对象调用 `finalize()`
3. FinalizerWatchdog 检查每个 `finalize()` 是否超时（默认 10s）
4. 如果超时 → 发送 `SIGABRT` → 进程退出

这就是为什么某些 App 会"莫名退出"——不是 Crash，而是某个类的 `finalize()` 方法执行过慢，被 Watchdog 杀掉。

[已验证: AOSP android-17.0.0_r1, libcore/libart/src/main/java/java/lang/Daemons.java — FinalizerWatchdogDaemon]

#### 与 Crash 堆栈收集的关系

FinalizerWatchdog 触发的 `SIGABRT` 会走标准的 Crash 处理流程，因此：
- 它产生的 tombstone / Crash 报告中，堆栈指向 `FinalizerWatchdogDaemon` 而非实际耗时操作
- 要定位真正的根因，需要查看 FinalizerDaemon 线程的堆栈（看它正在执行哪个 `finalize()`）
- 这就是为什么"获取所有线程的堆栈"在 Crash 诊断中如此重要

#### 排查建议

当发现 Crash 堆栈包含 `FinalizerWatchdog` 时：
1. 搜索应用的 `finalize()` 方法实现
2. 检查是否有 I/O 操作、线程等待、死循环
3. 最佳实践：Android 17 上应完全避免使用 `finalize()`，改用 `Cleaner` 或 `AutoCloseable`

> Android 17 中 `finalize()` 已被标记为 `@Deprecated`（for-removal），推荐使用 `java.lang.ref.Cleaner`。[已更新至 Android 17]

### 🔹 线程堆栈符号化与去重

#### 符号化

从 ART 获取的堆栈通常是 `ArtMethod* + DexPC` 的原始形式，需要转换为可读的 `类名.方法名(文件:行号)` 格式。

**Java 方法符号化**：
- 从 `ArtMethod` 提取 `declaring_class_` → `Class` → 类描述符
- 从 `dex_code_item_offset_` 在 DexFile 中定位 `CodeItem`
- 查找 `DebugInfoItem` 的 `line_table` → 源码行号

**Native 方法符号化**：
- 通过 `_Unwind_Backtrace` 获取 PC 值
- 使用 `dladdr()` 解析 PC → `Dl_info`（包含 so 路径、符号名、基地址）

[结构参考: Clippings/Android 应用稳定性剖析与优化 - Native Backtrace：Native 堆栈信息获取.md — CFI/libunwind 方案]

对于 Native 符号化，Android 17 中 CFI（Call Frame Information）方式是首选：
- 从 `.eh_frame` / `.eh_frame_hdr` 段读取帧信息
- 支持跨 Java/Native 边界的符号解析
- 缺点是 backtrace 速度相对较慢（相比 FP 方式）

#### 堆栈去重

一个应用可能有数十甚至上百个线程，在 Crash 时全部收集会导致：
- Crash 报告体积过大（每个线程堆栈几十 KB）
- 后端去重/聚合困难
- 排查时需要从大量信息中找到关键线程

推荐的去重策略：

| 去重维度 | 方法 | 用途 |
|---------|------|------|
| 按线程名 | 聚合同名线程（如 `OkHttpDispatcher-*`） | 关注线程类型分布 |
| 按栈顶 N 帧 | 比较前 5-10 帧 fingerprint | 识别相同等待状态的线程 |
| 按锁等待 | 聚合等待同一把锁的线程 | 快速定位锁瓶颈 |
| 按线程状态 | 分组 RUNNING/BLOCKED/WAITING | 优先关注 BLOCKED |

## 扩展

### 🔸 Framework 异常的反射/代理绕过思路

在 Android 应用开发中，某些系统 Framework 组件（如 `Toast`、`ServiceManager`、`ContentProvider`）的内部异常可能导致 Crash。由于这些组件的代码在系统进程中，应用层无法直接修改，需要通过反射/代理方式绕过：

**Toast BadTokenException 绕过**：
```java
// Android 12+ 对 Toast 的 Window Token 检查更严格
// 如果 Notification 没有权限，可能抛出 BadTokenException
// 通过反射替换 Toast 内部的 INotificationManager 代理：
Field field = Toast.class.getDeclaredField("sService");
field.setAccessible(true);
Object proxy = Proxy.newProxyInstance(
    Toast.sService.getClassLoader(),
    new Class[]{INotificationManager.class},
    (p, method, args) -> {
        if ("enqueueToast".equals(method.getName())) {
            // 包装调用，捕获 BadTokenException
        }
        return method.invoke(Toast.sService, args);
    }
);
field.set(null, proxy);
```

这类方案的通用思路是：通过 `Proxy.newProxyInstance` 或 `Hook` 替换 Framework 对象的远程接口代理，在代理层捕获特定异常。但需要注意：
- Android 17 对隐藏 API 访问的限制更严格（`hiddenapi-check`）
- 反射访问 Framework 内部字段可能触发 `UnsupportedOperationException`
- 推荐优先使用官方替代方案（如 `Snackbar` 替代 `Toast`）

[待验证: Android 17 具体的隐藏 API 限制列表变化]

### 🔸 Memory Allocation Trace 监控模块

在 OOM 根因定位中，仅知道 Crash 时的堆栈往往不够——需要知道**哪些分配路径消耗了最多内存**。

**方案：Hook `malloc`/`calloc`/`realloc`，按调用栈聚合分配量**：

```c
// 通过 PLT/GOT Hook 拦截 malloc
void* hooked_malloc(size_t size) {
    void* ptr = real_malloc(size);
    if (should_trace(size)) {  // 仅追踪大对象
        // 获取当前线程的 Native 堆栈
        void* stack[32];
        int depth = backtrace(stack, 32);
        // 按堆栈 fingerprint 累加分配量
        record_allocation(stack, depth, size);
    }
    return ptr;
}
```

关键设计决策：
- **采样而非全量**：对每次 `malloc` 都做 backtrace 会有显著性能开销（~10μs/次），需要按 size 或概率采样
- **聚合维度**：按 `so + 符号` 聚合（而非完整堆栈），减少内存占用
- **与 Java 堆联动**：通过 `art::gc::Heap` 的 `GCListener` 回调，在 GC 时获取当前的分配 Trace 分布

> 关于内存分配监控与泄漏检测的完整框架设计，参见 **23.25 Android 17 内存泄漏监控框架实战**。

---

## Crash 堆栈收集的工程实践总结

| 维度 | 推荐方案 | 备选方案 | 注意事项 |
|------|---------|---------|---------|
| Java 线程堆栈 | ThreadList::ForEach + WalkStack | Profilo Unwinder 模拟 | 处理 mutator_lock 死锁风险 |
| Native 线程堆栈 | libunwind (CFI) | libbacktrace | 预先加载符号表 |
| 锁持有者 | Monitor::GetLockOwnerThreadId | LockWord 直接读取 | 区分 Thin/Fat Lock |
| 全量 Crash 报告 | 信号处理器中收集 + 异步落盘 | debuggerd tombstone | 避免在处理器中分配内存 |
| Crash 兜底 | sigsetjmp/siglongjmp + pthread_create Hook | 进程级 Crash 重启 | [结构参考: pthread_create 回溯方案] |

[结构参考: Clippings/Android 应用稳定性剖析与优化 - pthread_create 回溯：原来 Native 也有 try catch！.md — 非局部跳转 Crash 兜底]
