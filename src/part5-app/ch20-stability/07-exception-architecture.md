---
title: "异常处理架构设计"
chapter: "20.7"
section: "20.7"
status: draft
applicable_versions: "Android 10 (API 29) - Android 16 (API 36)"
last_verified: "2026-05-10"
last_verified_against: "待验证"
confidence: low
drafted_date: "2026-05-10"
polish_count: 0
sources: []
tags: [exception-handling, safemode, hotfix, graceful-degradation]
related_chapters: ["20.2", "20.3", "26.2"]
pipeline_stage: draft
task6_state: pending
task9_state: pending
task2b_state: pending
---

# 异常处理架构设计

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 全局异常捕获框架设计
- 🔹 安全气囊（SafeMode）机制
- 🔹 降级策略：功能降级、页面降级、兜底页
- 🔹 灰度发布与热修复集成

### 扩展（可选深入）

- 🔸 多进程异常隔离
- 🔸 Kotlin Coroutine 异常处理

### OpenClaw 加工指引

> **锚点**是最低覆盖要求，加工时必须逐条落实并标注验证结果。
> **扩展**视素材丰富程度选择性深入。
> 如果从 Obsidian 素材或 AOSP 源码中发现大纲未列出但与本节强相关的知识点，
> 可**就地插入**最相关的锚点之后，并用 `[自动发现]` 标注，方便后续 review。
> 锚点内容需 L1/L2 验证，扩展内容至少 L2 验证，自动发现内容至少标注来源。
<!-- outline-end -->

## 为什么要了解异常处理架构设计

（待加工）

## 扩展

### Kotlin协程异常处理机制与UncaughtExceptionHandler的关系

> 本节为源码调研补充，2026-05-11，调研人：AutoResearchClaw
> 关联章节：§20.2 Java Crash 治理

Kotlin协程的异常处理与Java的UncaughtExceptionHandler形成三层级联体系，两者紧密关联但职责不同。

#### 异常处理的优先级链

当协程内发生未捕获异常时，`kotlinx.coroutines`按以下顺序查找handler：

**第一层：CoroutineContext中的CoroutineExceptionHandler**

```kotlin
// kotlinx-coroutines-core/common/src/CoroutineExceptionHandler.kt, handleCoroutineException()
context[CoroutineExceptionHandler]?.let {
    it.handleException(context, reportException)
    return  // 存在则直接处理，终止分发
}
```

这是**最高优先级**，因为它是协程创建者明确指定的。例如：

```kotlin
val handler = CoroutineExceptionHandler { ctx, ex ->
    // 仅处理没有传播路径的协程异常
    log("Coroutine exception: $ex")
}

GlobalScope.launch(handler) {
    throw RuntimeException("test")
}
// → handler.handleException() 被调用
```

**第二层：ServiceLoader注册的全局CoroutineExceptionHandler**

```kotlin
// kotlinx-coroutines-core/jvm/src/internal/CoroutineExceptionHandlerImpl.kt
internal actual val platformExceptionHandlers: Collection<CoroutineExceptionHandler> = 
    ServiceLoader.load(
        CoroutineExceptionHandler::class.java,
        CoroutineExceptionHandler::class.java.classLoader
    ).iterator().asSequence().toList()
```

在Android上，`kotlinx-coroutines-android`库通过以下文件注册`AndroidExceptionPreHandler`：

```
META-INF/services/kotlinx.coroutines.CoroutineExceptionHandler
→ kotlinx.coroutines.android.AndroidExceptionPreHandler
```

**第三层：Thread.uncaughtExceptionHandler（JVM兜底）**

```kotlin
// kotlinx-coroutines-core/jvm/src/internal/CoroutineExceptionHandlerImpl.kt
internal actual fun propagateExceptionFinalResort(exception: Throwable) {
    val currentThread = Thread.currentThread()
    currentThread.uncaughtExceptionHandler.uncaughtException(currentThread, exception)
}
```

这最终会触发`RuntimeInit`中注册的`LoggingHandler`和`KillApplicationHandler`，打印FATAL日志并杀进程。

#### 传播路径（Propagation Paths）的判定

协程异常处理的核心设计是**结构化并发**。异常是否有"传播路径"决定它是否会调用CoroutineExceptionHandler：

**有传播路径（不需要CoroutineExceptionHandler处理）**：
- `coroutineScope { launch { throw Error() } }` — 异常传播给父协程
- `async { ... }.await()` — 调用方通过Deferred获取异常
- `lifecycleScope.launch { ... }` — 异常传播给lifecycle，最后到Activity/Fragment的lifecycleObserver

**无传播路径（必须由CoroutineExceptionHandler处理）**：
- `GlobalScope.launch { throw Error() }`
- `supervisorScope { launch { throw Error() } }` — supervisorScope不传播子协程异常

#### Android 8.0/8.1的特殊问题：pre-handler丢失

Android 8.0引入了私有API `Thread.getUncaughtExceptionPreHandler()`，用于日志记录。但协程直接调用`thread.uncaughtExceptionHandler.uncaughtException()`绕过了这个pre-handler，导致协程异常在Android 8.0上不会写入系统日志。

**源码位置**：`ui/kotlinx-coroutines-android/src/AndroidExceptionPreHandler.kt`

```kotlin
override fun handleException(context: CoroutineContext, exception: Throwable) {
    // Android 8.0/8.1 (API 26/27) 特殊处理
    if (Build.VERSION.SDK_INT in 26..27) {
        (preHandler()?.invoke(null) as? Thread.UncaughtExceptionHandler)
            ?.uncaughtException(Thread.currentThread(), exception)
    }
}
```

Android 8.1在默认handler中加了检查自动调用pre-handler，所以问题只存在于API 26/27。

#### 与Java UncaughtExceptionHandler的关键区别

| 维度 | CoroutineExceptionHandler | Thread.UncaughtExceptionHandler |
|------|--------------------------|--------------------------------|
| 作用范围 | 仅无传播路径的协程异常 | 所有未捕获异常（包括协程的兜底） |
| 调用时机 | 协程异常传播链末端 | Java层异常最终兜底 |
| 注册方式 | CoroutineContext或ServiceLoader | Thread.setDefaultUncaughtExceptionHandler() |
| Android 8.0/8.1 | 有特殊处理修复pre-handler问题 | 原始pre-handler机制被绕过 |

#### 工程实践建议

1. **在GlobalScope或supervisorScope中始终指定CoroutineExceptionHandler**，否则异常会直接触发系统crash处理
2. **CoroutineExceptionHandler中的操作要轻量**，因为它运行在协程的dispatcher线程上
3. **Android 8.0/8.1设备上协程异常日志会丢失**，如果需要在这些设备上调试，需要额外的日志手段
4. **ServiceLoader加载时机是惰性的**，首次协程异常时才会触发

#### 源码索引

| 文件 | 关键内容 |
|------|---------|
| `kotlinx-coroutines-core/common/src/CoroutineExceptionHandler.kt` | `handleCoroutineException()`分发逻辑、传播路径文档 |
| `kotlinx-coroutines-core/jvm/src/internal/CoroutineExceptionHandlerImpl.kt` | JVM平台实现、ServiceLoader加载 |
| `ui/kotlinx-coroutines-android/src/AndroidExceptionPreHandler.kt` | Android Oreo pre-handler问题修复 |
| `kotlinx-coroutines-core/common/src/JobSupport.kt` | 协程状态机、异常在Job生命周期中的处理 |

<!-- AIW-源码调研-2026-05-11 -->
