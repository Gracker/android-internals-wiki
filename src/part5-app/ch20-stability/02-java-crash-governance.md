---
title: Java Crash 治理
chapter: '20.2'
section: '20.2'
status: finalized
applicable_versions: Android 10 (API 29) - Android 17 (API 37)
last_verified: '2026-07-01'
last_verified_against: AOSP android-17.0.0_r1, developer.android.com
confidence: medium
drafted_date: '2026-05-10'
polish_count: 0
task2b_result: fixed
reviewed_date: "2026-05-18"
reviewed_by: openclaw-task6
task6_result: pass-light-edit
task6_state: revisiting
task9_result: auto-fixed
task9_state: reviewed
task2b_state: fixed
pipeline_stage: task6_pending
sources:
- type: clippings-structure-ref
  path: Clippings/Android 应用稳定性剖析与优化 - Java Crash 监控：实现自定义 Crash 处理器.md
- type: clippings-structure-ref
  path: Clippings/Android 应用稳定性剖析与优化 - Java 堆栈：深入了解 Throwable.md
- type: aosp
  path: frameworks/base/core/java/com/android/internal/os/RuntimeInit.java
- type: official
  path: developer.android.com/reference/java/lang/Thread.UncaughtExceptionHandler
tags:
- java-crash
- exception-handling
- uncaughtexceptionhandler
- stability
related_chapters:
- '20.1'
- '20.7'
- '1.7'
task9_reviewed_date: "2026-05-18"
task9_reviewed_by: openclaw-task9
last_task9_at: "2026-07-01T08:20:00+08:00"
last_task9_audit: "2026-07-01"
last_task9_autofix_at: "2026-07-01"
task9_review_notes: "2026-07-01 Task9 idle audit auto-fix: 已用 AOSP android-17.0.0_r1 复核 RuntimeInit / Thread / ART Throwable 路径，将验证锚点从 android-16.0.0_r1 更新到 android-17.0.0_r1，并修正 KillApplicationHandler 上报异常 catch 边界；无 P0/P1 机制错误，回到 Task6 复审。 | 2026-05-18 task9 deep-review: pass-tech-review。P0 0 / P1 0；UncaughtExceptionHandler 持久化链路已闭合。既有 P2 数据/异常类型建议不重复写入。Task6 已通过且 queue 无 pending，自动晋升 finalized。 | 2026-05-18 task9 deep-review: needs-rework。P0 0 / P1 1 / P2 2。UncaughtExceptionHandler 崩溃上报持久化链路不完整；RuntimeInit 异常类型与 Crash 分布数据需补证据。已写入 queue.json / suggestions.md。 | 2026-05-17 18:20 Task9 idle audit → 2026-05-18 Task2B fixed: Throwable 256 帧说法已修正为 saved_frames 优化阈值。"
last_task9_review_log: "logs/deep-review/2026-07-01-08-audit.md"
reviewed_at: "2026-05-18T03:31:27+08:00"
last_task6_at: "2026-05-18T01:08:00+08:00"
last_task6_audit: "2026-06-23"
task6_reviewed_date: "2026-05-18"
last_task6_review_log: "logs/review/2026-05-18-01-review.md"
task6_review_notes: "2026-05-18 task6 复审：pass-light-edit。补齐 outline 锚点、去重来源、小修 Kotlin 协程段落间距并补验证标注；无新增 B 类问题。Task9 仍需复核，未自动晋升。"
task9_review_log: "logs/deep-review/2026-07-01-08-audit.md"
finalized_date: "2026-05-18"
finalized_by: openclaw-task9-auto-promote
---

# Java Crash 治理

<!-- outline-start -->
- 🔹 Java 异常分类体系：Exception / RuntimeException / Error 的治理差异
- 🔹 UncaughtExceptionHandler 机制：系统默认处理链、自定义 handler 链式调用与退出路径
- 🔹 堆栈获取代价：Throwable 栈回溯、saved_frames 阈值与高频采集风险
- 🔹 Top Crash 模式：NPE、越界、类型转换、生命周期异常的排查要点
- 🔹 治理优先级：影响面、严重度、修复成本与监控反馈流程
<!-- outline-end -->

Java Crash 在线上稳定性问题中通常占比较高 [待验证: 需补充具体业务或公开报告数据来源]，也是工程师日常接触最多的崩溃类型。本节从异常分类出发，讲清楚 UncaughtExceptionHandler 的正确用法，给出 Top Crash 模式的排查思路和治理优先级判定方法。

## Java 异常分类体系

Android Java 层的异常按 ART 虚拟机处理路径分为 Exception 和 Error 两类，都继承自 `Throwable`。

**Exception — 可恢复的异常条件**

- **Checked Exception**：编译器强制要求处理，不处理则编译不通过。典型如 `IOException`、`SQLException`。这类异常表示外部条件不可控（网络断开、文件不存在），不代表程序逻辑有 bug。
- **RuntimeException（Unchecked）**：编译器不强制处理，运行时抛出。典型如 `NullPointerException`、`IndexOutOfBoundsException`、`ClassCastException`。这类异常几乎都指向代码逻辑缺陷——某个前置条件没检查、某个类型假设错误。

**Error — 虚拟机层面的严重问题**

`OutOfMemoryError`、`StackOverflowError`、`NoSuchMethodError` 等。默认行为是终止进程。部分 Error 可以通过技术手段拦截或缓解：

- `OutOfMemoryError`：堆增量（Heap Expansion）技术可以在 OOM 时扩大虚拟机堆上限，延长应用在线时间（详见 20.5 OOM 治理）
- `StackOverflowError`：通常由无限递归触发，修复递归终止条件即可

工程上的区别：Checked Exception 的治理重点是"是否该 catch、catch 后做什么"；RuntimeException 的治理重点是"为什么会发生、在哪个版本引入"。两类问题的排查策略不同。

[适用版本: Android 10 - Android 17]
[结构参考: Clippings/Android 应用稳定性剖析与优化 - Java Crash 监控：实现自定义 Crash 处理器.md]

## UncaughtExceptionHandler 机制与全局捕获

### 系统默认处理链

当一个异常在 Java 层未被捕获，ART 虚拟机的处理流程（`art/runtime/thread.cc`）：

1. 虚拟机在各检查点检测到未处理异常，调用 `art::Thread::HandleUncaughtExceptions()`（`art/runtime/thread.cc`）
2. 通过 JNI 调用 Java 层 `Thread.dispatchUncaughtException(Throwable)`
3. 沿 handler 链执行：`getUncaughtExceptionPreHandler()` → `getUncaughtExceptionHandler()` → `ThreadGroup.uncaughtException()`

在 `com.android.internal.os.RuntimeInit.commonInit()`（`frameworks/base/core/java/com/android/internal/os/RuntimeInit.java`）中，系统注册了两个默认 handler：

| Handler | 职责 | 行为 |
|---------|------|------|
| `LoggingHandler` | 打印 crash 日志 | 输出 `FATAL EXCEPTION` 日志（线程名、进程名、PID、Throwable 堆栈） |
| `KillApplicationHandler` | 终止进程 | 通知 AMS → `Process.killProcess(Process.myPid())` + `System.exit(10)` |

[已验证: AOSP android-17.0.0_r1, frameworks/base/core/java/com/android/internal/os/RuntimeInit.java]

`KillApplicationHandler` 通知 AMS 这一步不保证完成。Android 17 源码对上报路径捕获的是 `Throwable`，其中 `DeadObjectException` 只表示 system_server 已不可用；其他上报异常会被额外记录后同样进入 `finally` 块杀进程——crash 信息可能来不及写入系统日志。

### 自定义 UncaughtExceptionHandler 的正确做法

通过 `Thread.setDefaultUncaughtExceptionHandler()` 注册自定义 handler，可以在进程终止前拿到异常并上报。

```java
// 1. 保存系统默认 handler（通常是 KillApplicationHandler）
Thread.UncaughtExceptionHandler defaultHandler =
    Thread.getDefaultUncaughtExceptionHandler();

// 2. 注册自定义 handler
Thread.setDefaultUncaughtExceptionHandler((thread, throwable) -> {
    // 收集 crash 信息，生成最小 crash record
    CrashRecord record = CrashRecord.fromThrowable(thread, throwable);

    // 有界同步落盘——写入本地文件（如 app 私有目录或 DropBox）
    // 注意：不能写入内存缓存，因为 KillApplicationHandler.finally 会
    // 调用 Process.killProcess() + System.exit(10)，进程内存不会保留
    CrashStore.persistSync(record);

    // 如果有独立 crash 上报进程，可通过 IPC 转发
    // CrashReporterService.forward(record);

    // 必须链式调用上一个 handler，否则进程不会正常退出
    if (defaultHandler != null) {
        defaultHandler.uncaughtException(thread, throwable);
    }
});
```

[已验证: AOSP RuntimeInit.KillApplicationHandler finally 会执行 Process.killProcess() + System.exit(10)，崩溃进程内存不会保留，所以 crash 信息必须在 handler 内同步持久化到磁盘或转发给独立进程。]

实操中三个容易踩的坑：

**1. 链式调用不能断**

如果应用集成了多个 SDK（Crash SDK、APM SDK），每个 SDK 都可能调用 `setDefaultUncaughtExceptionHandler`。后注册的会覆盖先注册的。解法：每个 SDK 在注册前保存前一个 handler，处理完后链式调用。不保存直接覆盖 = 前 SDK 的 crash 上报静默丢失。

**2. handler 中不能做耗时操作**

自定义 handler 执行完后才会到 `KillApplicationHandler` 的 `System.exit(10)`。在 handler 中做磁盘 IO 或网络同步请求，会延迟进程退出时间，可能触发系统的 ANR watchdog。`KillApplicationHandler.finally` 会执行 `Process.killProcess(Process.myPid())` 和 `System.exit(10)`——崩溃进程的内存不会保留到“下次启动”。所以 crash 信息的持久化策略只有三条路：

1. **有界同步落盘**：在 handler 内将最小 crash record 写入本地文件（控制写入量和超时），下次启动时读取并上报
2. **独立进程接力**：通过 ContentProvider / Binder / Socket 将 crash record 转发给常驻的 crash 上报进程，由该进程负责异步网络上报
3. **DropBox 代持**：调用 `DropBoxManager.addData()` 写入系统 DropBox，进程退出后数据仍在磁盘

不能把 crash 信息放在“内存缓存”里指望下次启动读取——进程被 kill 后内存内容全部丢失。

**3. 初始化时机**

`setDefaultUncaughtExceptionHandler` 应该在 `Application.attachBaseContext()` 中调用，而不是 `onCreate()`。`attachBaseContext` 是 Application 生命周期中最早可用的回调，确保 Application 创建过程中的异常也能被捕获。

[已验证: 官方文档, developer.android.com/reference/java/lang/Thread.UncaughtExceptionHandler]
[结构参考: Clippings/Android 应用稳定性剖析与优化 - Java Crash 监控：实现自定义 Crash 处理器.md]

### 堆栈获取的代价

`new Throwable()` 在构造函数中调用 `nativeFillInStackTrace()`，触发 ART 栈回溯。回溯过程遍历 `ManagedStack` 链表中的 `ShadowFrame`/`QuickFrame`，解析每个 `ArtMethod` 指针。ART `CreateInternalStackTrace()` 内部用 `kMaxSavedFrames = 256` 做快速路径缓存——深度小于 256 时复用 saved_frames，达到或超过 256 时执行二次 `WalkStack()` 构建完整 internal stack trace。256 是 saved_frames 优化阈值，不是 Java 堆栈的最大深度。

堆栈捕获有性能开销。不能在高频路径上频繁创建 `Throwable` 对象。如需在性能敏感位置采集调用栈，考虑用 `Thread.getStackTrace()` 替代，或做采样（如每 100 次采集 1 次）。

[已验证: AOSP android-17.0.0_r1, art/runtime/thread.cc CreateInternalStackTrace; art/runtime/native/java_lang_Throwable.cc]
[结构参考: Clippings/Android 应用稳定性剖析与优化 - Java 堆栈：深入了解 Throwable.md]

## Top Crash 模式与根因分析

线上 Java Crash 的分布高度集中。Top 5 类型覆盖 80% 以上的 Java Crash：

| 排名 | 异常类型 | 典型场景 | 根因特征 |
|------|---------|---------|---------|
| 1 | `NullPointerException` | 解析服务端返回的 JSON 字段为 null 时直接调用方法 | 服务端字段变更、网络超时返回默认值、多版本兼容 |
| 2 | `IndexOutOfBoundsException` | 列表/数组越界访问 | 数据源变更（列表为空）、分页加载竞态、RecyclerView adapter 与数据不同步 |
| 3 | `ClassCastException` | 序列化/反序列化类型不匹配 | Parcelable 字段类型变更、跨进程传参类型假设错误 |
| 4 | `IllegalStateException` | 生命周期状态不正确 | Fragment 已 destroy 后操作 View、Activity 已 finish 后启动新 Activity |
| 5 | `OutOfMemoryError` | Java 堆内存耗尽 | Bitmap 未回收、内存泄漏积累、大图加载 |

> OOM 的完整治理方案见 20.5 节。本节聚焦前四类 Exception 的排查方法。

### 各模式的排查要点

**NullPointerException**

线上堆栈通常能直接定位到类和行号。排查时关注三个问题：

- 服务端字段在哪个版本开始变化？→ 对照服务端 changelog 时间线
- null 是正常业务逻辑（字段可选）还是 bug（应该有值但丢失了）？→ 看服务端接口文档
- 影响范围：特定机型/系统版本/用户群，还是全量？→ crash 日志中的自定义维度（App 版本、OS 版本、用户标签）

快速止血：加 null check。长期方案：根因在服务端的推服务端修，根因在客户端的补防御逻辑。

**IndexOutOfBoundsException**

列表场景中的高频原因：

- `RecyclerView.Adapter` 的 `notifyDataSetChanged()` 在异步回调中调用，但数据源已被清空或替换
- 分页加载的并发问题：前一页还没加载完，用户滑到末尾触发第二次加载，两次回调操作同一个列表

排查手段：在 crash 堆栈附近找数据源操作（add/remove/clear），检查是否有并发修改。`ConcurrentModificationException` 是更明确的信号。

**IllegalStateException**

Fragment/Activity 生命周期场景中的高频模式：

- `commitAllowingStateLoss()` 看起来解决了 crash，实际可能导致状态丢失——需要判断是状态可以丢（弹个非关键 toast），还是不能丢（事务提交）
- `viewLifecycleOwner` 在 `onDestroyView` 之后仍被引用——协程或 LiveData observer 没有正确取消订阅

**ClassCastException**

通常出现在跨进程或反序列化场景：

- `Bundle.getSerializable()` 返回的类型与预期不一致——服务端在某个版本改了字段类型
- `Parcelable` 对象的 `CREATOR` 反序列化时，发送方和接收方的类定义不一致（多进程场景下版本不同步）

[待验证: Top Crash 分布数据来自行业经验，不同应用场景可能有差异]

## 治理优先级排序与修复策略

### 优先级判定

不是按 crash 类型排优先级，而是按**影响面 × 严重度 × 修复成本**三维度评估：

| 维度 | 高优先级 | 低优先级 |
|------|---------|---------|
| 影响面 | 核心路径（启动、首页、支付） | 边缘功能（设置页、低频入口） |
| 严重度 | crash rate > 0.1%（千分之一） | crash rate < 0.01% |
| 修复成本 | 一行 null check | 需要重构数据流或改服务端协议 |

排序时用 crash 影响用户数（UV）而不是 crash 次数——一个用户 crash 100 次和 100 个用户各 crash 1 次，后者优先级更高。

### 修复策略分级

**L1 防御性编程（快速止血）**

```java
// 直接访问，可能 NPE
String name = response.getUser().getName();

// 防御性访问
User user = response != null ? response.getUser() : null;
String name = user != null ? user.getName() : "";
```

每加一层 null check，都要回答：这个 null 是业务允许的还是 bug？如果是 bug，根源在哪？防御性编程是紧急止血的有效手段，长期方案必须追到根因。

**L2 根因修复**

| 根因类型 | 修复方向 |
|---------|---------|
| 服务端字段变更 | 加版本协商或字段兼容层 |
| 数据源与 UI 不同步 | 统一数据源，消除并发竞态（如用 `DiffUtil` 替代 `notifyDataSetChanged()`） |
| 生命周期问题 | 用 `Lifecycle` 组件约束操作时机（`repeatOnLifecycle` / `viewLifecycleOwner.lifecycleScope`） |
| 类型假设错误 | Parcelable 字段加版本号，反序列化时做类型检查 |

**L3 监控与反馈**

1. crash 发生 → APM 后台实时告警（crash rate 超阈值）
2. 按版本聚合 → 确认是否是某个版本引入（回归检测）
3. 按 OS 版本聚合 → 确认是否是系统行为变更
4. 修复上线 → 验证 crash rate 下降 → 持续观察

[适用版本: Android 10 - Android 17]
[自动发现: 监控与反馈流程]

## 扩展

### ART 虚拟机异常处理流程

Java 异常在 ART 中的传递路径：`art::Thread::SetException()` 设置异常标志 → 各检查点检测 → `art::Thread::HandleUncaughtExceptions()`（`art/runtime/thread.cc`）→ JNI 到 Java 层 → `Thread.dispatchUncaughtException()` → handler 链。

异常标志设置后线程不会立即终止。ART 在多个位置插入异常检查：

- **编译执行的方法返回时**：编译器在每个可能抛异常的调用点之后插入 `IsExceptionClear()` 检查（`art/compiler/optimizing/code_generator.cc` 生成）
- **解释执行时**：`ExecuteGoto()` 解释器在每条指令执行前检查异常标志（`art/runtime/interpreter/interpreter.cc`）
- **JNI 调用返回时**：`CheckJNI` 在 JNI 方法返回后检查是否有待处理异常
- **线程销毁时**：`Thread::Destroy()` 中调用 `HandleUncaughtExceptions()` 处理残留异常

编译模式下，异常检查窗口通常只有一条指令——编译器在调用指令后立即插入检查。解释模式下，每条字节码指令前都有检查，窗口更短。

详见 1.7 节 ART 编译管线中关于异常表和 deoptimization 的部分。

### 第三方库崩溃的隔离与降级

第三方 SDK 的 crash 在大型应用中占比可达 20-30%。治理思路：

- **handler 链保护**：注册自定义 handler 时保存前一个，确保 SDK 的 handler 不被覆盖
- **线程池隔离**：第三方 SDK 代码运行在独立线程池中，通过 `Thread.UncaughtExceptionHandler` 捕获该线程池中未处理异常，阻止扩散到主线程
- **降级开关**：对关键 SDK（广告、推送）设置远程开关，crash rate 飙升时动态禁用

[待补充: 第三方 SDK crash 隔离的具体实现方案]

### Kotlin 协程异常与 UncaughtExceptionHandler 的关系

> 源码调研补充，2026-05-11，详见 §20.7 扩展章节或 [DeepResearch/2026-05-11-kotlin-coroutine-exception-handler-analysis.md](../DeepResearch/2026-05-11-kotlin-coroutine-exception-handler-analysis.md)

Kotlin 协程异常处理与 Java 的 UncaughtExceptionHandler 形成级联体系：

1. **Context 中的 CoroutineExceptionHandler**（最高优先级）— 协程创建者明确指定
2. **ServiceLoader 注册的全局 handler** — `kotlinx-coroutines-android` 通过 `META-INF` 注册 `AndroidExceptionPreHandler`
3. **Thread.uncaughtExceptionHandler**（兜底）— 最终触发 RuntimeInit 的 LoggingHandler / KillApplicationHandler

**关键区别**：CoroutineExceptionHandler 只处理“无传播路径”的协程异常。在 `coroutineScope` 中，异常会通过结构化并发传播给父协程，不需要 CoroutineExceptionHandler 介入。在 `supervisorScope` 或 `GlobalScope` 中，异常没有传播路径，必须由 CoroutineExceptionHandler 处理。

Android 8.0/8.1 存在 pre-handler 丢失问题（协程直接调用 uncaughtExceptionHandler 绕过了 pre-handler），`kotlinx-coroutines-android` 通过反射调用修复了这个问题。

详细分析见 §20.7 扩展章节。

<!-- AIW-源码调研-2026-05-11-kotlin -->
