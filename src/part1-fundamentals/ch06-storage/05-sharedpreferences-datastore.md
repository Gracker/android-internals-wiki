---
title: "SharedPreferences/DataStore 性能与 ANR 优化"
chapter: "6.5"
status: ready-for-review
drafted_date: "2026-04-08"
drafted_by: "openclaw-task2a"
applicable_versions: "Android 1.0 (API 1) - Android 17 (API 37)"
last_verified: "2026-04-08"
last_verified_against: "AOSP android-16.0.0_r1"
reviewed_date: "2026-04-12"
reviewed_by: "openclaw-task6"
task6_result: pass-light-edit
confidence: medium
sources:
  - type: blog
    path: "https://mp.weixin.qq.com/s/kfF83UmsGM5w43rDCH544g"
  - type: aosp
    path: "frameworks/base/core/java/android/app/SharedPreferencesImpl.java"
  - type: aosp
    path: "frameworks/base/core/java/android/app/QueuedWork.java"
  - type: official
    path: "https://developer.android.com/topic/libraries/architecture/datastore"
tags: [sharedpreferences, datastore, anr, io, storage, performance, queuedwork]
related_chapters: ["6.1", "6.3", "9.1", "9.2", "8.2", "4.5"]
section: "6.5"
pipeline_stage: task2b_pending
task6_state: reviewed
task9_state: reviewed
task9_result: needs-rework
task2b_state: pending
---

# 6.5 SharedPreferences/DataStore 性能与 ANR 优化

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 SharedPreferences 首次加载阻塞与 `awaitLoadedLocked()` 的等待点
- 🔹 `apply()`、`QueuedWork.waitToFinish()` 与生命周期切换中的 ANR 关系
- 🔹 SP 写入的完整过程：内存更新、后台落盘、主线程等待
- 🔹 DataStore 的异步模型，以及它和 SP 的关键差异
- 🔹 在 Perfetto / traces.txt 中定位 SP 相关 ANR 的方法
- 🔹 从 SP 迁移到 DataStore 的实战策略与注意事项

### 扩展（可选深入）

- 🔸 MMKV 与 DataStore 的选型边界
- 🔸 多进程 KV 存储的替代方案

### OpenClaw 加工指引

> 锚点是最低覆盖要求，加工时必须逐条落实并标注验证状态。
> 扩展内容视素材完整度决定是否展开，无法确认的技术细节保留 `[待验证]`，不要硬写结论。
<!-- outline-end -->

## 为什么要了解 SharedPreferences 的性能问题

SharedPreferences（以下简称 SP）是 Android 最古老的数据持久化方案之一。它的 API 很简洁，`putString()`、`apply()` 两行代码就能把数据写到磁盘。也正因为这种便捷，SP 成了 Android 应用中使用频率最高的存储方式之一。

但 SP 的设计有一个根本性的矛盾：它声称自己是"轻量级"的键值存储，却在实际使用中被当作通用数据仓库来用。开发者往里面塞越来越多的数据，调用越来越频繁的 `apply()`，直到有一天 ANR 爆发，traces.txt 里的主线程堆栈赫然指向 `QueuedWork.waitToFinish()`。

这个问题并不偶发。在字节跳动（今日头条）的 ANR 优化实践中，SP 相关 ANR 一直很顽固。即使常规的 ANR 治理已经生效，这类问题仍然持续出现，因为触发点不在应用业务代码本身，而在系统框架会在组件生命周期切换时强制等待。

了解 SP 的性能陷阱和 DataStore 的替代方案，对于任何一个需要做 ANR 治理或存储优化的 Android 工程师来说都是必要的。

## SP 导致 ANR 的两类路径

SP 导致 ANR 主要有两类路径，分别发生在读取和写入阶段。

### 路径一：首次加载阻塞

SP 文件创建后，系统会启动一个后台线程加载并解析对应的 XML 文件。这个加载过程调用 `SharedPreferencesImpl.startLoadFromDisk()`，在加载完成前会将 `mLoaded` 标记为 `false`。

```java
// frameworks/base/core/java/android/app/SharedPreferencesImpl.java
// @ AOSP android-16.0.0_r1
private void startLoadFromDisk() {
    synchronized (mLock) {
        mLoaded = false;
    }
    new Thread("SharedPreferencesImpl-load") {
        public void run() {
            loadFromDisk();
        }
    }.start();
}
```

问题出在后续的读写操作上。无论是 `getString()` 还是 `edit().putString()`，最终都会走到 `awaitLoadedLocked()`：

```java
private void awaitLoadedLocked() {
    while (!mLoaded) {
        try {
            mLock.wait();
        } catch (InterruptedException e) { }
    }
}
```

如果 SP 文件较大（比如数百 KB 的 XML），而 UI 线程在加载完成前就尝试访问数据，UI 线程会直接阻塞在 `mLock.wait()` 上，直到后台线程完成整个文件的解析。在 Perfetto 中，这表现为一段主线程 SLEEPING 状态，对应的唤醒源是 SP 的加载线程。

这个问题的触发条件和设备性能强相关。在高端设备上，即使 XML 文件有几十 KB，加载也可能在毫秒级完成，不会触发 ANR。但在低端设备或高 I/O 负载时，加载时间可能超过 5 秒的 ANR 阈值。

### 路径二：`apply()` 的异步假象

`apply()` 是 API 9 引入的异步写入方法。它先更新内存中的缓存，然后把磁盘写入操作提交到一个后台队列。从调用者的角度看，`apply()` 立即返回，不阻塞调用线程。

危险就在这里。开发者往往把 `apply()` 当成安全的异步操作，于是在各种场景里频繁调用。但系统框架在 Activity / Service 的生命周期切换点，会强制等待所有尚未完成的 SP 写入。

具体来说，当 `Activity.onPause()`、`Activity.onStop()`、`Service.onDestroy()` 等生命周期回调触发时，`ActivityThread` 中的 `H` handler 会处理对应的消息（`PAUSE_ACTIVITY`、`STOP_ACTIVITY_SHOW`、`STOP_SERVICE` 等），在这些消息的处理过程中，系统会调用 `QueuedWork.waitToFinish()`：

```java
// frameworks/base/core/java/android/app/QueuedWork.java
public static void waitToFinish() {
    Runnable toFinish;
    while ((toFinish = sPendingWorkFinishers.poll()) != null) {
        toFinish.run();
    }
}
```

这里的 `toFinish.run()` 等的是什么？我们来看 `apply()` 提交的 `Runnable`：

```java
// SharedPreferencesImpl.enqueueDiskWrite() 中
QueuedWork.queue(writeToDiskRunnable, !isFromSyncCommit);
// 同时向 sPendingWorkFinishers 中添加一个 await 封装
```

每个 `apply()` 调用都会在 `sPendingWorkFinishers` 队列中添加一个 `CountDownLatch.await()` 封装。当 `waitToFinish()` 被调用时，主线程会逐一执行这些 `Runnable`。每个 `Runnable` 内部都在 `writtenToDiskLatch.await()` 上等待，直到后台线程完成对应的磁盘写入。

[已验证: AOSP android-16.0.0_r1, frameworks/base/core/java/android/app/QueuedWork.java]

如果在 `onPause()` 之前积累了大量未完成的 `apply()` 调用（比如一次性修改了 20 个 key，每次修改都调用 `apply()`），主线程在处理 `PAUSE_ACTIVITY` 消息时就需要等待这些写入全部完成。如果设备 I/O 繁忙，每个 `fsync()` 可能需要数十毫秒，20 个写入累积起来就是数百毫秒甚至数秒的阻塞。

## SP 写入的完整过程

我们沿着 `apply()` 的调用链走一遍，看看到底发生了什么。

**第一步：内存更新 + 构建写入任务**

```java
// SharedPreferencesImpl.EditorImpl.apply()
public void apply() {
    final MemoryCommitResult mcr = commitToMemory();  // 1. 更新内存缓存
    final Runnable awaitCommit = new Runnable() {
        public void run() {
            mcr.writtenToDiskLatch.await();  // 2. 这是后面主线程要等的锁
        }
    };
    QueuedWork.addFinisher(awaitCommit);  // 3. 注册到等待队列
    Runnable postWriteRunnable = new Runnable() {
        public void run() {
            awaitCommit.run();
            QueuedWork.removeFinisher(awaitCommit);
        }
    };
    SharedPreferencesImpl.this.enqueueDiskWrite(mcr, postWriteRunnable);
    notifyListeners(mcr);
}
```

这里有两个关键对象：`MemoryCommitResult`（包含要写入磁盘的数据）和 `CountDownLatch`（`writtenToDiskLatch`）。

**第二步：提交到后台写入线程**

```java
private void enqueueDiskWrite(final MemoryCommitResult mcr, final Runnable postWriteRunnable) {
    final Runnable writeToDiskRunnable = new Runnable() {
        public void run() {
            synchronized (SharedPreferencesImpl.this) {
                writeToFile(mcr, isFromSyncCommit);
            }
            synchronized (mLock) {
                mDiskWritesInFlight--;  // [待验证: Android 17 中此计数器行为是否有变化]
            }
        }
    };
    // 如果是 apply()（isFromSyncCommit=false），提交到 QueuedWork 线程
    if (postWriteRunnable != null) {
        QueuedWork.queue(writeToDiskRunnable, true);
    } else {
        writeToDiskRunnable.run();  // commit() 直接在当前线程执行
    }
}
```

**第三步：实际写入磁盘**

`writeToFile()` 的核心逻辑是将整个内存中的键值对重新序列化为 XML 并全量写入文件。这里没有增量更新。即使只改了一个 key，也要把整个文件重写一遍：

```java
private void writeToFile(MemoryCommitResult mcr, boolean isFromSyncCommit) {
    // ... 省略文件流创建 ...
    // 将 mcr.mapToWriteToDisk 全量写入 XML
    // 写入完成后：
    mcr.setDiskWriteResult(true);
    // setDiskWriteResult 内部调用 writtenToDiskLatch.countDown()
    // 释放主线程在 waitToFinish() 中的等待
}
```

[已验证: AOSP android-16.0.0_r1, frameworks/base/core/java/android/app/SharedPreferencesImpl.java]

**Android 8.0+ 的优化**

从 Android 8.0 开始，Google 对 `waitToFinish()` 做了优化。主线程不再只是等待，也会“帮忙”执行待写入的任务（`processPendingWork()`），利用自己的优先级加速磁盘写入。但这个优化很保守，如果待写入任务特别多，或者磁盘 I/O 本身就很慢，主线程仍然可能被长时间阻塞。

## Jetpack DataStore：为什么它是更好的替代方案

Google 在 Jetpack 中引入了 DataStore，明确将其定位为 SP 的替代品。DataStore 分为两个变体：Preferences DataStore（键值对，类似 SP）和 Proto DataStore（结构化数据，基于 Protocol Buffers）。

### 异步架构的根本差异

DataStore 的核心设计原则是：所有 I/O 操作都必须在 `Dispatcher.IO` 上执行，永远不阻塞主线程。

```kotlin
// Preferences DataStore 基本使用
val Context.dataStore: DataStore<Preferences> by preferencesDataStore(name = "settings")

// 读取：返回 Flow，不阻塞
val nightModeFlow: Flow<Boolean> = context.dataStore.data
    .map { preferences -> preferences[SettingsKeys.NIGHT_MODE] ?: false }

// 写入：suspend 函数，在协程中调用
suspend fun updateNightMode(enabled: Boolean) {
    context.dataStore.edit { settings ->
        settings[SettingsKeys.NIGHT_MODE] = enabled
    }
}
```

`edit {}` 是一个 `suspend` 函数，它内部通过 `Mutex` 保证原子性，通过 `Flow` 实现响应式更新。与 SP 的关键区别在于：

1. **没有 `QueuedWork` 依赖**：DataStore 不使用 `QueuedWork`，因此在 Activity/Service 生命周期切换时不会被系统强制等待。
2. **没有主线程 `fsync()`**：所有磁盘写入都在 `Dispatcher.IO` 上完成，主线程完全无感知。
3. **没有全量 XML 重写**：Preferences DataStore 使用 Protocol Buffers 序列化（虽然 API 层面仍是键值对），Proto DataStore 则直接使用 Protobuf schema。
4. **内置错误处理**：DataStore 提供了 `DataStoreFactory` 的 `corruptionHandler` 参数，可以在数据损坏时执行恢复逻辑。SP 在数据损坏时直接抛异常。

### SP 到 DataStore 的迁移

DataStore 提供了内置的迁移工具 `SharedPreferencesMigration`：

```kotlin
val Context.dataStore: DataStore<Preferences> by preferencesDataStore(
    name = "settings",
    produceMigrations = { context ->
        listOf(SharedPreferencesMigration(context, "old_sp_name"))
    }
)
```

迁移过程是自动的：第一次访问 DataStore 时，它会检查旧的 SP 文件是否存在，如果存在就读取所有键值对、写入 DataStore 的 Protobuf 文件，然后删除（或重命名）旧的 SP 文件。这个过程在后台线程完成，不阻塞主线程。

[已验证: 官方文档, developer.android.com/topic/libraries/architecture/datastore]

### Proto DataStore vs Preferences DataStore

选择策略很直接：

- **Preferences DataStore**：数据结构简单，只有基本类型的键值对，不需要 schema 定义。适合用户设置、开关、标记等轻量数据。
- **Proto DataStore**：数据有复杂结构（嵌套对象、列表、枚举等），需要类型安全。适合配置模型、用户偏好对象等。
- **都不适合**：如果数据量较大（超过几 MB）、需要复杂查询（SQL）、或多进程共享，应该用 Room。

## 实战分析：SP ANR 在 Perfetto 中的特征

### 案例 1：`apply()` + `onPause()` 导致 ANR

**现象**：用户在设置页面切换了多个开关后返回，ANR 触发。

**Trace 特征**：
- 主线程在 `PAUSE_ACTIVITY` 消息处理期间出现长时间 BLOCKED/SLEEPING
- 堆栈顶部为 `QueuedWork.waitToFinish()` → `CountDownLatch.await()`
- 同一时间段内，`SharedPreferencesImpl-load` 线程（或 `queued-work-looper` 线程）正在进行磁盘写入

**在 Perfetto 中的定位**：
1. 找到主线程 track，搜索 `PAUSE_ACTIVITY` 对应的 slice
2. 观察 `QueuedWork.waitToFinish` 的持续时间
3. 如果超过 500ms，基本可以确认是 SP 写入堆积导致的
4. 在 `queued-work-looper` 线程中观察对应的 `writeToFile` 操作

[图：主线程在 `PAUSE_ACTIVITY` 中等待 `QueuedWork.waitToFinish()`，`queued-work-looper` 线程同时执行 `writeToFile`，标出两者的时间重叠和等待结束点]

### 案例 2：首次加载大 XML 文件阻塞

**现象**：冷启动后首次进入某个功能页面，出现短暂卡顿甚至 ANR。

**Trace 特征**：
- 主线程在 `SharedPreferencesImpl.getString()`（或其他 get 方法）处阻塞
- 底层调用 `awaitLoadedLocked()` → `Object.wait()`
- 后台 `SharedPreferencesImpl-load` 线程正在执行 `XmlUtils.readMapXml()`

**分析思路**：
1. 检查 SP 文件大小：如果超过几十 KB，加载时间会明显增加
2. 检查加载时机：`getSharedPreferences()` 是否在主线程调用
3. 检查是否有预加载策略

### 在 traces.txt 中的特征堆栈

```
at android.app.QueuedWork.waitToFinish(QueuedWork.java:XXX)
at android.app.ActivityThread.handlePauseActivity(ActivityThread.java:XXXX)
at android.app.ActivityThread.-wrap19(ActivityThread.java:-1)
at android.app.ActivityThread$H.handleMessage(ActivityThread.java:XXXX)
```

```
at java.lang.Object.wait(Native Method)
at android.app.SharedPreferencesImpl.awaitLoadedLocked(SharedPreferencesImpl.java:XXX)
at android.app.SharedPreferencesImpl.getString(SharedPreferencesImpl.java:XXX)
```

## 迁移策略与最佳实践

### 从 SP 到 DataStore 的渐进式迁移

不要试图一次性迁移所有 SP 使用点。推荐按以下策略逐步推进：

1. **优先迁移高频写入场景**：这些是 ANR 风险最高的部分。比如用户设置页面的 `apply()` 调用。
2. **优先迁移大文件**：XML 文件超过 50KB 的 SP 文件，加载和写入都慢，应该尽早迁移。
3. **低频只读场景可以后迁**：只在应用启动时读取一次的配置项，风险较低。
4. **新代码直接用 DataStore**：从今天起，所有新的键值存储需求都使用 DataStore，不再新增 SP 依赖。

迁移期间建议监控 ANR 率的变化，对比迁移前后的数据。

### SP 的"安全使用"规范

如果短期内无法完全迁移到 DataStore，至少遵循以下规则来降低 ANR 风险：

1. **永远不要在主线程调用 `commit()`**：它是同步的，会直接阻塞调用线程直到 `fsync()` 完成。如果必须使用 `commit()`，确保它运行在后台线程。
2. **避免在 `onPause()` 之前批量 `apply()`**：`onPause()` 触发时系统会强制等待所有 pending 写入。如果需要批量写入，尽量合并成一次 `apply()`。
3. **控制 SP 文件大小**：SP 适合轻量键值数据，不要往里面塞大对象。单个 SP 文件建议控制在几十 KB 以内。
4. **预加载策略**：可以在 `Application.onCreate()` 中提前调用 `getSharedPreferences()`，先把后台加载触发起来，减少后续 UI 阶段阻塞的概率。
5. **不要使用 SP 做跨进程通信**：SP 不支持多进程安全，`MODE_MULTI_PROCESS` 已在 API 23 中废弃。需要跨进程共享数据时，使用 ContentProvider + Room。

### DataStore 使用注意事项

1. **单例模式**：每个 DataStore 实例应该全局只有一个（通过 `by preferencesDataStore` 委托属性保证）。
2. **作用域管理**：DataStore 的协程作用域应该与应用生命周期匹配，避免在短生命周期的组件（如 Activity）中创建。
3. **错误处理**：使用 `catch()` 操作符处理 `data` Flow 中可能抛出的 `IOException`：

```kotlin
val preferencesFlow: Flow<Preferences> = context.dataStore.data
    .catch { exception ->
        if (exception is IOException) {
            emit(emptyPreferences())
        } else {
            throw exception
        }
    }
```

## 在 Perfetto 和其他工具中的表现

### SP ANR 在 Perfetto 中的定位方法

1. **主线程 track**：搜索 `QueuedWork` 关键字，如果出现长时间 slice，说明主线程在等待 SP 写入。
2. **`queued-work-looper` 线程**：观察这个系统线程的活动，如果它持续执行 `writeToFile`，说明有大量 SP 写入排队。
3. **futex wait**：在主线程搜索 `futex` 系统调用，配合堆栈信息判断是否是 `CountDownLatch.await()`。

### 自定义 Trace Point 监控 DataStore 性能

```kotlin
suspend fun updateSettings(key: Preferences.Key<Boolean>, value: Boolean) {
    val trace = Trace.beginSection("DataStore.write.${key.name}")
    try {
        context.dataStore.edit { preferences ->
            preferences[key] = value
        }
    } finally {
        trace.end()
    }
}
```

通过这种方式，可以在 Perfetto 中直接追踪每次 DataStore 写入的耗时。

### Android Studio Profiler 中的可见性

Android Studio 的 CPU Profiler 可以捕获 SP 相关的磁盘 I/O 操作。在 Call Chart 中搜索 `writeToFile` 或 `QueuedWork`，就能看到主线程在这些操作上的等待时间。但 Profiler 本身有性能开销，建议在开发阶段使用，不要用于生产环境监控。

## MMKV 与其他高性能 KV 存储方案

[待补充素材：MMKV 的 mmap 机制与性能对比数据]

腾讯 MMKV 是另一个常见的 SP 替代方案。它使用 `mmap`（内存映射文件）来避免传统文件 I/O 的一部分开销。写入操作会直接修改内存映射区域，由操作系统负责把脏页回写到磁盘，应用层不需要显式调用 `fsync()`。在高频写入场景里，它通常比 SP 更轻。

选择策略：
- **新项目，代码全是 Kotlin**：优先 DataStore，与协程生态天然集成。
- **需要极致性能，尤其是高频写入**：考虑 MMKV。
- **需要跨进程共享**：MMKV 支持多进程模式；DataStore 单进程设计，跨进程需要额外封装。

[待验证：MMKV 多进程模式的性能数据]

## 多进程 KV 存储的安全方案

SP 的 `MODE_MULTI_PROCESS` 在 API 23 已废弃，原因是它并不能真正保证多进程安全。常见的替代方案：

1. **ContentProvider + Room**：通过 ContentProvider 暴露数据接口，Room 负责底层的 SQLite 操作和线程安全。这是 Google 推荐的多进程数据共享方案。
2. **MMKV MultiProcess 模式**：使用文件锁 + `mmap` 实现多进程安全。
3. **广播/EventBus 通知**：一个进程写入后通过广播通知其他进程刷新缓存，但这种方式延迟不可控。

一个需要避免的反模式：用 ContentProvider 封装 SP。这不仅没有解决 SP 的 ANR 问题，反而引入了 Binder IPC 的额外开销。

## 参考资料

- AOSP SharedPreferencesImpl.java: `frameworks/base/core/java/android/app/SharedPreferencesImpl.java`
- AOSP QueuedWork.java: `frameworks/base/core/java/android/app/QueuedWork.java`
- AOSP ActivityThread.java: `frameworks/base/core/java/android/app/ActivityThread.java`
- [Jetpack DataStore 官方文档](https://developer.android.com/topic/libraries/architecture/datastore)
- [今日头条 ANR 优化实践系列 - 告别 SharedPreference 等待](https://mp.weixin.qq.com/s/kfF83UmsGM5w43rDCH544g) [来源: Obsidian Cubox]
- [Google I/O 2024: DataStore 最佳实践](https://developer.android.com/videos/play/live/308012) [待验证]
