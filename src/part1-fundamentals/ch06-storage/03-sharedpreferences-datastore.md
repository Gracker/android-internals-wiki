---
title: SharedPreferences 与 DataStore：I/O、ANR 与多进程一致性
chapter: '6.3'
status: finalized
applicable_versions: Android 1.0 (API 1) - Android 17 (API 37)
last_verified: '2026-10-02'
last_verified_against: AOSP android-17.0.0_r1 SharedPreferencesImpl.java / QueuedWork.java / ActivityThread.java / BroadcastReceiver.java / SharedPreferences.java / ContextImpl.java; Android Developers SharedPreferences/DataStore docs fetched 2026-10-02; AndroidX DataStore 1.2.1 source/AAR (DataStore.kt / DataStoreImpl.kt / FileStorage.kt / MultiProcessCoordinator.android.kt / MulticastFileObserver.android.kt / SharedCounter.android.kt / SharedPreferencesMigration.android.kt)
confidence: medium
sources:
- type: blog
  path: https://mp.weixin.qq.com/s/kfF83UmsGM5w43rDCH544g
- type: aosp
  path: frameworks/base/core/java/android/app/SharedPreferencesImpl.java
- type: aosp
  path: frameworks/base/core/java/android/app/QueuedWork.java
- type: aosp
  path: frameworks/base/core/java/android/content/BroadcastReceiver.java
- type: aosp
  path: frameworks/base/core/java/android/app/ActivityThread.java
- type: official
  path: https://developer.android.com/topic/libraries/architecture/datastore
- type: official
  path: https://developer.android.com/reference/kotlin/androidx/datastore/core/DataStore
- type: official
  path: https://developer.android.com/jetpack/androidx/releases/datastore
- type: androidX
  path: AndroidX DataStore 1.2.1 DataStore.kt / DataStoreImpl.kt / FileStorage.kt / MultiProcessCoordinator.android.kt / MulticastFileObserver.android.kt / SharedCounter.android.kt / SharedPreferencesMigration.android.kt
tags:
  - sharedpreferences
  - datastore
  - anr
  - io
  - storage
  - queuedwork
related_chapters:
- '6.1'
- '6.2'
- '9.1'
- '8.2'
- '4.4'
section: '6.3'
last_review_finalize_at: '2026-10-02T12:05:34+08:00'
last_rework_at: '2026-10-02T09:46:50+08:00'
last_idle_audit_at: '2026-08-04T18:35:51+08:00'
last_consolidated_at: '2026-08-11'
consolidated_from:
- src/part1-fundamentals/ch06-storage/6.03-Android-17-SharedPreferencesImpl-ANR机制.md
- src/part1-fundamentals/ch06-storage/6.1-androidx-datastore--ipc-源码级验证-draft.md
---

# SharedPreferences 与 DataStore：I/O、ANR 与多进程一致性

`SharedPreferences.apply()` 调用返回得快，但写盘工作和主线程生命周期仍然绑在一起，跨进程一致性也从来不在它的承诺范围内。我们选 SharedPreferences（下文简称 SP）还是 DataStore，要同时考虑首次加载、写入收尾、序列化成本和数据所有权。

> 源码基线：平台为 Android 17 / API 37，AOSP `android-17.0.0_r1`；Jetpack 实现为 AndroidX DataStore 1.2.1。手机升级到 Android 17 不会替 App 自动升级 DataStore，最终行为由应用依赖的 AndroidX 版本决定。

## `apply()` 返回后的写盘与主线程关系

先回答一个问题：`apply()` 是异步的，ANR 是怎么找上门的？SP 适合少量、低频、单进程的配置，它的风险来自两层：XML 的读写速度，以及 API 语义本身。

- 首次加载由后台线程执行，但调用方第一次读取可能在 `awaitLoadedLocked()` 等待。
- `apply()` 先更新内存再立刻返回，写盘结果不会反馈给调用方。
- Android 框架会在部分组件收尾点排空 `QueuedWork`，主线程可能执行尚未开始的写盘，也可能等待已经开始的写盘。
- 每次有效修改都要序列化当前整份键值映射，SP 也没有按 key 增量更新文件的能力。
- 平台接口层面没有可靠的跨进程一致性。

`SharedPreferences` 的接口文档已经明确建议：新的小型数据存储需求优先考虑 Jetpack DataStore，关系型数据和较大数据集则使用 Room。

## SP 对象与首次加载

### 同一进程会缓存同一份 SP 实例

要看 SP 的 I/O 行为，得先从对象创建和文件加载说起。`ContextImpl` 使用静态的 `sSharedPrefsCache`，先按包名、再按文件路径缓存 `SharedPreferencesImpl`；同一进程中用相同的 Context/文件名反复获取，通常拿到同一个对象，框架也不会为每次 `getSharedPreferences()` 重新创建加载任务。

这个缓存只解决进程内的对象复用。不同进程各有一份内存 map，变更通知也没有跨进程的可靠协议。`MODE_MULTI_PROCESS` 已废弃，留下的实现只在文件变化时尝试重新加载，事务和一致性都谈不上。

### `startLoadFromDisk()` 异步，`getXxx()` 仍可能同步等待

下面的源码片段给出加载执行器与线程名的定义：

```java
private static final ThreadPoolExecutor sLoadExecutor =
        new ThreadPoolExecutor(
                0, 1, 10L, TimeUnit.SECONDS,
                new LinkedBlockingQueue<Runnable>(),
                new SharedPreferencesThreadFactory());

private static final class SharedPreferencesThreadFactory implements ThreadFactory {
    @Override
    public Thread newThread(Runnable runnable) {
        Thread thread = Executors.defaultThreadFactory().newThread(runnable);
        thread.setName("SharedPreferences");
        return thread;
    }
}
```

`corePoolSize=0`、`maximumPoolSize=1` 意味着同一进程的 SP 加载任务在单个工作线程上依次执行。我们要找的稳定观察点，就是名为 `SharedPreferences` 的线程；旧版本或厂商修改版仍要以现场线程和调用栈为准。

对象构造后，`startLoadFromDisk()` 把 `loadFromDisk()` 交给这个执行器。加载线程负责 `.bak` 备份恢复、文件 `stat` 和 XML 解析，完成后设置 `mLoaded` 并唤醒等待者。

下面的等待循环解释了为什么“后台读盘”仍会卡住主线程：

```java
@GuardedBy("mLock")
private void awaitLoadedLocked() {
    if (!mLoaded) {
        BlockGuard.getThreadPolicy().onReadFromDisk();
    }
    while (!mLoaded) {
        try {
            mLock.wait();
        } catch (InterruptedException unused) {
        }
    }
    if (mThrowable != null) {
        throw new IllegalStateException(mThrowable);
    }
}
```

`getString()`、`getInt()`、`contains()`、`getAll()`，甚至 `edit()` 都会先走这里。后台线程可能还在读盘，主线程已经停在 `mLock.wait()`。即使文件 I/O 发生在另一条线程上，这次调用也会按调用线程的 StrictMode 策略上报一次磁盘读取。

首次等待通常被以下因素放大：

- XML 文件较大或 key 数量很多。
- 同一进程同时首次打开多份 SP，而加载执行器只有一个工作线程。
- 冷启动阶段还有 DEX、资源和数据库等 I/O 在竞争。
- `/data` 正在脏页回写或 F2FS GC，块设备本身也在延迟抖动。
- XML 解析或备份恢复失败，异常最终回到调用方。

“在 `Application` 中提前调用 `getSharedPreferences()`”只是提前创建对象、提前安排加载；紧接着就读 key 的话，仍可能进入等待。要降低首帧风险，要把首次使用挪到有余量的阶段，再用 trace 验证加载有没有在关键路径前完成。

## 从 `edit()` 到 `fsync()`：SP 写入的完整路径

### 第一步：`commitToMemory()` 修改内存状态

无论 `apply()` 还是 `commit()`，第一步都是 `commitToMemory()`。它在锁内把 Editor 的修改合入 `mMap`，递增内存状态版本号，记录受影响的 key 和监听器，并把在途写入计数 `mDiskWritesInFlight` 加一。

如果已有写盘正在使用旧 map，代码会先复制一份再修改，避免写盘序列化期间改动同一个对象。这里的“提交”只覆盖进程内状态；文件有没有落盘，要等写盘结束才知道。

### 第二步：`apply()` 注册 finisher 并排队

下面的精简片段用于说明 `apply()` 与 `QueuedWork` 的关系：

```java
public void apply() {
    final MemoryCommitResult mcr = commitToMemory();
    final Runnable awaitCommit = () -> {
        try {
            mcr.writtenToDiskLatch.await();
        } catch (InterruptedException ignored) {
        }
    };

    QueuedWork.addFinisher(awaitCommit);
    Runnable postWriteRunnable = () -> {
        awaitCommit.run();
        QueuedWork.removeFinisher(awaitCommit);
    };

    enqueueDiskWrite(mcr, postWriteRunnable);
    notifyListeners(mcr);
}
```

调用方看到的顺序是：内存已更新、写盘任务已安排、监听器收到内存变更，然后 `apply()` 返回。`awaitCommit` 作为 finisher（收尾任务）留在 `QueuedWork.sFinishers` 里，直到写盘结束后由 `postWriteRunnable` 移除，或者被框架的收尾逻辑取出来执行。

`apply()` 没有返回值，序列化、`fsync()` 还是重命名失败了，调用方都无从知道。所以写重要安全状态、或必须确认数据已持久化时，判断依据应该是写盘结果本身；只凭“内存已经读到新值”认定成功，是不够的。

### 第三步：`enqueueDiskWrite()` 决定在哪条线程写

`enqueueDiskWrite()` 把文件写入封装成 `writeToDiskRunnable`。这个 Runnable 拿着 `mWritingToDiskLock` 串行执行 `writeToFile()`，结束后把 `mDiskWritesInFlight` 减一，再运行 `postWriteRunnable`。

`commit()` 与 `apply()` 的关键差异如下：

| 维度 | `apply()` | `commit()` |
| --- | --- | --- |
| 返回 | 立即返回 `void` | 等待对应写盘结束，返回 `boolean` |
| 内存可见 | `commitToMemory()` 后立即可见 | 同样先更新内存 |
| 常规写盘安排 | 进入 `QueuedWork`，默认可延迟 100 ms | 若当前写是唯一在途写，可由调用线程直接执行 |
| 已有写盘时 | 排队 | 同样排队，随后调用线程等待 latch（同步闩锁） |
| 监听器 | 写盘完成前即可通知 | 等待本次写盘后通知 |
| 错误信息 | 无磁盘结果 | 只有布尔结果，没有详细失败原因 |
| 生命周期收尾 | pending work（待处理任务）/finisher（收尾任务）可能被框架等待 | 调用点已经同步等待 |

“`commit()` 总在当前线程写”和“`apply()` 总在 `queued-work-looper` 写”这两种说法都不严谨：`commit()` 可能先排队再等待，`apply()` 的任务也可能被随后调用 `waitToFinish()` 的线程取走执行。

### 第四步：`writeToFile()` 重写整份 XML

我们把一次有效写入的步骤完整走一遍：

1. 检查内存状态版本号与磁盘版本号，确认是否需要写。
2. 若原文件存在且没有备份，把原文件重命名为 `.bak`。
3. 创建新的 XML 文件，把 `mapToWriteToDisk` 整体序列化。
4. 对文件描述符执行同步刷新。
5. 更新权限、时间戳和文件大小记录。
6. 成功后删除 `.bak`，更新磁盘代数并释放 `writtenToDiskLatch`。
7. 失败时删除不完整的新文件，保留备份供下次加载恢复。

这套备份协议降低了进程在写入中途退出时留下半份 XML 的风险，也仅止于此：源码没有在每次替换后同步父目录，文件系统、内核与存储设备仍会影响最终的持久性语义。

SP 没有按 key 更新磁盘文件的能力，改一个布尔值也可能重写整份 map。耗时由文件大小、序列化成本、`fsync()` 延迟和前序队列长度共同决定。

### 两个日志阈值只负责观测

平台保留了两个内部观测阈值：

- `SharedPreferencesImpl.MAX_FSYNC_DURATION_MILLIS = 256`：单次 `fsync` 超过 256 ms 时输出累计直方图；每 1024 次同步也会输出。
- `QueuedWork.MAX_WAIT_TIME_MILLIS = 512`：`waitToFinish()` 超过 512 ms 时输出等待直方图；每 1024 次等待也会输出。

这些阈值不会取消写盘，也不会阻止 ANR，也没有面向普通 App 的公开调参接口。256 ms 和 512 ms 只是日志观测线，别当成系统超时线。

## `apply()` 如何进入组件收尾路径

SP 的写盘只是被延后，框架会在组件收尾的几个固定位置把它捡回来。我们先看 `waitToFinish()` 内部做了什么，再看有哪些调用点。

### `waitToFinish()` 可能让主线程写盘

下面的源码片段用于说明收尾时做了哪些工作：

```java
public static void waitToFinish() {
    synchronized (sLock) {
        handlerRemoveMessages(QueuedWorkHandler.MSG_RUN);
        sCanDelay = false;
    }

    StrictMode.ThreadPolicy oldPolicy = StrictMode.allowThreadDiskWrites();
    try {
        processPendingWork();
    } finally {
        StrictMode.setThreadPolicy(oldPolicy);
    }

    try {
        while (true) {
            final Runnable finisher;
            synchronized (sLock) {
                finisher = sFinishers.poll();
            }
            if (finisher == null) break;
            finisher.run();
        }
    } finally {
        sCanDelay = true;
    }
}
```

`processPendingWork()` 先取走 `sWork` 中的待处理任务，并在当前调用线程逐个运行。若主线程调用 `waitToFinish()`，尚未开始的 SP 写盘就可能直接在主线程执行。随后它再运行 finisher；如果写盘已由后台线程取得，finisher 会在 `writtenToDiskLatch.await()` 等待。

`StrictMode.allowThreadDiskWrites()` 会临时放宽这一段的磁盘写策略，所以只靠 StrictMode，可能漏掉生命周期收尾阶段由主线程执行的写盘。

### 组件收尾的四类调用点

`android-17.0.0_r1` 中需要区分四类路径：

- **现代 Activity**：`handleStopActivity()` 在 Activity 停止时调用 `QueuedWork.waitToFinish()`。
- **pre-Honeycomb Activity**：面向 Android 3.0（API 11）之前行为的兼容路径仍在 `handlePauseActivity()` 调用；现代 App 的主路径要按 `handleStopActivity()` 理解，不要写成 `onPause()`。
- **Service**：`handleServiceArgs()` 在命令处理后等待，`handleStopService()` 在销毁清理后等待。
- **BroadcastReceiver**：`PendingResult.finish()` 不直接调用 `waitToFinish()`。若发现 `QueuedWork` 仍有任务，它把 `sendFinished()` 排在队尾，AMS 收到完成回执的时间随之推迟。

BroadcastReceiver 的 Java `onReceive()` 返回，只说明应用侧代码执行完了；系统什么时候收到完成回执，要看队列里 SP 写盘的进度，写盘过慢时广播超时风险随之上升。

组件的 ANR 窗口随组件类型、前后台状态和系统版本变化，统一套用“超过 5 秒必定 ANR”会误判。框架等待点的作用，是把原本延后的持久化成本重新带回组件时限内。

## 用 ANR traces 与 Perfetto 定位 SP

### 先从 ANR 栈判断阻塞类型

下面的示例用于区分三种常见栈形态，行号会随源码版本改变：

```text
# A. 首次加载等待
java.lang.Object.wait
android.app.SharedPreferencesImpl.awaitLoadedLocked
android.app.SharedPreferencesImpl.getString

# B. 生命周期收尾时等待后台写盘
java.util.concurrent.CountDownLatch.await
android.app.SharedPreferencesImpl$EditorImpl.lambda$apply$0
android.app.QueuedWork.waitToFinish
android.app.ActivityThread.handleStopActivity

# C. 生命周期收尾时由主线程执行写盘
android.system.Os.fsync
android.app.SharedPreferencesImpl.writeToFile
android.app.QueuedWork.processPendingWork
android.app.QueuedWork.waitToFinish
```

A 类要关联 `SharedPreferences` 加载线程与 XML 解析；B 类要找后台写盘线程，以及 `writtenToDiskLatch` 尚未释放的时段；C 类的文件 I/O 已经在主线程上。我们先把阻塞类型分对再谈优化——类型分错，很容易只移动耗时而没有消除等待。

Service 栈可能以 `handleServiceArgs()` 或 `handleStopService()` 结尾。BroadcastReceiver 常见的是完成回执延后，未必出现主线程停在 `waitToFinish()` 的相同栈形态。

### Perfetto 中看什么

Perfetto 默认并不会给每个 Java 方法生成名为 `QueuedWork` 的 slice。采集配置里如果没有 Java 调用栈或应用自定义 trace，只搜方法名很可能一无所获。我们把几类信息放在一起看：

1. 主线程在组件收尾区间处于 Running、Runnable 还是 Sleeping 状态。
2. `SharedPreferences` 与 `queued-work-looper` 线程的调度和 CPU 活动。
3. ART/Java 调用栈采样里是否出现 `awaitLoadedLocked()`、`writeToFile()`、`processPendingWork()`。
4. 文件系统与块 I/O 事件是否和等待区间重合。
5. logcat 日志中 `SharedPreferencesImpl` 的慢 `fsync` 直方图、`QueuedWork` 的慢等待直方图。
6. App 自己记录的 SP 文件名、key 数、文件字节数、在途写次数和调用场景；不要记录敏感值。

只看到主线程停在 futex 等待还不够：Java monitor、`CountDownLatch`、Binder 和许多其他同步原语都可能落到 futex 上，等待对象要靠调用栈来确定。

## DataStore 的异步模型

换了存储库，异步模型完全不同。我们先看 DataStore 的一次更新在什么意义上算“完成”，再看它的序列化成本和单例约束。

### 非阻塞 API 的完成时序

DataStore 的 `data` 是 `Flow<T>`，`edit()`/`updateData()` 是挂起 API。默认工厂的协程作用域使用 `Dispatchers.IO + SupervisorJob()`，磁盘 I/O 和更新任务都放在 I/O 调度器上，子任务失败也被隔离在作用域内。调用方线程不会像 SP `commit()` 那样同步执行文件 I/O，但调用方协程会挂起；挂起期间不占用当前线程，直到更新完成或异常抛出。

下面的代码用于展示 Preferences DataStore 的基本读写语义：

```kotlin
val Context.settingsDataStore by preferencesDataStore(name = "settings")

val nightMode: Flow<Boolean> =
    context.settingsDataStore.data.map { prefs ->
        prefs[booleanPreferencesKey("night_mode")] ?: false
    }

suspend fun setNightMode(enabled: Boolean) {
    context.settingsDataStore.edit { prefs ->
        prefs[booleanPreferencesKey("night_mode")] = enabled
    }
}
```

`setNightMode()` 返回时，这次更新已经走完 DataStore 的串行更新与持久化路径；写入失败的话，异常会回到挂起调用方。重试、提示用户还是保留旧状态，由调用者决定——`launch` 启动协程后立刻把业务操作标记为永久成功，等于放弃了失败信号。

官方 API 对 DataStore 的承诺包括线程安全、非阻塞和事务化更新。读取不会被写入锁长期阻塞，但第一次收集仍需要完成初始化、迁移和首次读盘；初始化失败会通过 Flow 或更新调用传播。

### DataStore 的全量序列化

DataStore 没有字段级磁盘更新。官方 API 文档明确说明：任意字段改变后，整个对象都会被序列化并持久化。Preferences DataStore 把键值集合编码为 protobuf（Protocol Buffers 二进制格式），Proto DataStore 使用应用定义的 protobuf schema；两者都不适合不断增长的大数据集。

AndroidX DataStore 1.2.1 的 `FileStorage` 写入路径是：

1. 在更新序列中获得当前数据。
2. 执行 transform 更新函数，得到不可变的新值。
3. 在受协调锁保护的 `writeScope` 中递增协调器版本。
4. 将新值完整序列化到 `<file>.tmp`。
5. 对临时文件执行 `FileDescriptor.sync()`。
6. `writeScope` 的写入代码结束后，`FileStorage` 把临时文件原子移动到目标路径。
7. 整个 `writeScope` 成功返回后，串行处理更新的写入 actor 才唤醒等待该更新的调用方。

源码里仍留着“同步父目录”的待办注释，掉电窗口下的回退风险因此还在。DataStore 的 API 一致性和错误传播显著强于 SP，但存储硬件与文件系统对持久性的影响，任何上层 API 都消不掉。

### Preferences 与 Proto 怎么选

| 需求 | 建议 |
| --- | --- |
| 少量、无固定 schema 的键值配置 | Preferences DataStore |
| 有明确字段、枚举、默认值和版本演进 | Proto DataStore |
| 关系查询、局部更新、索引、分页、大集合 | Room |
| 缓存，可丢失且需要容量淘汰 | 专用缓存方案 |

Proto DataStore 的 schema 更利于审查和演进，但业务迁移仍要应用自己做：字段编号不可复用，删除字段要保留编号；加密、备份排除和敏感数据生命周期也由应用设计。

### 单例是文件级约束

同一进程、同一路径同时存在多个活跃 DataStore 实例会破坏功能，并在读写时触发 `IllegalStateException`。顶层 `by preferencesDataStore` 属性是一种方便的单例组织方式，但指向同一文件创建多个 delegate 依旧是错的。

自建 `DataStoreFactory` 时，传入的协程作用域应与应用级数据拥有者同寿命。Activity、Fragment 或一次请求里都不要重复创建实例，`produceFile` 也不要每次返回不同路径。

多进程场景的实例与路径要求、单进程与多进程工厂的选择，见 MultiProcess DataStore 的实现边界一节。路径要先规范化，transform 返回的数据对象必须保持不可变，否则进程内缓存的 hash 校验就失去了意义。

### 错误与损坏要分开处理

下面的代码用于给 Preferences DataStore 的读流提供 I/O 失败降级：

```kotlin
val safeSettings: Flow<Preferences> =
    context.settingsDataStore.data.catch { error ->
        if (error is IOException) {
            emit(emptyPreferences())
        } else {
            throw error
        }
    }
```

这段代码把普通 `IOException` 临时映射为空配置，适合“默认值可接受”的场景。若数据影响登录、安全或付费状态，静默回退可能产生更严重的问题，应由业务定义恢复策略。

`ReplaceFileCorruptionHandler` 只在 Serializer 抛出 `CorruptionException` 时参与恢复；权限不足、磁盘空间不够等其他 I/O 错误，要走业务自己的恢复策略，恢复值也要满足业务的安全要求。

## 从 SP 迁移到 DataStore

### 使用 `SharedPreferencesMigration`

下面的示例用于迁移指定的基础类型 key：

```kotlin
val Context.settingsDataStore: DataStore<Preferences> by preferencesDataStore(
    name = "settings",
    produceMigrations = { context ->
        listOf(
            SharedPreferencesMigration(
                context = context,
                sharedPreferencesName = "legacy_settings",
                keysToMigrate = setOf("theme", "font_scale"),
            )
        )
    },
)
```

迁移任务在 DataStore 首次可访问之前执行。成功持久化新数据后，清理步骤会从旧 SP 删除已迁移 key；使用 Context/文件名构造器且旧 SP 已空时，还会尝试删除旧文件。迁移或持久化一旦失败，后续访问可能再次执行相关步骤，所以迁移函数必须幂等——重复执行也要得到一致结果。

另外几点要留心：

- 内置 Preferences 迁移只支持 SP 的 boolean、float、int、long、string 和 string set。
- 指定 `keysToMigrate` 后只能访问这些 key；省略时迁移全部受支持 key。
- DataStore 中已经存在的同名 Preferences key 不会被旧 SP 反复覆盖。
- 迁移尚未完成时，`data.first()` 和更新调用都会等待初始化。
- 迁移完成后继续让旧代码写 SP，会形成两份来源；DataStore 不负责持续双向同步。

### 迁移按数据所有权推进

我们把一次可靠迁移分成四步：

1. **盘点**：列出每个 SP 文件的拥有模块、key 类型、读写频率、跨进程使用、备份策略和回滚要求。
2. **确定唯一写入方**：为每组配置指定一个数据接口，禁止业务代码绕过它直接拿 SP。
3. **迁移并观测**：先迁高风险写入和大文件；记录迁移失败、初始化耗时、DataStore 文件大小和更新延迟。
4. **删除旧路径**：确认活跃版本和独立进程都切换后，移除旧读写。需要支持版本回退时，要提前定义旧版本如何处理已删除的 SP key。

“SP 超过 50 KB 就必须迁移”这样的通用阈值并不存在。文件大小只是一个维度，key 数、启动位置、写频率、设备分布和等待分位数同样要看；按线上 trace 和按相似调用栈归组的 ANR 聚类确定优先级，更可靠。

## MultiProcess DataStore 的实现边界

多进程一致性靠一套协作协议维持。我们从工厂选择看起，再看 1.2.1 的协调机制和测试要求。

### 所有进程必须使用多进程工厂

从 DataStore 1.1.0 起，`MultiProcessDataStoreFactory` 提供正式的多进程支持。若 App 进程和独立 Service 进程共享一个文件，两边都应使用多进程工厂，并指向完全相同的路径。单进程 DataStore 与多进程 DataStore 混用同一文件不受支持。

每个进程仍应只保留一个指向该文件的活跃实例。配置对象必须不可变，迁移也必须能够安全地重复执行。

### 1.2.1 的三类协调机制

AndroidX DataStore 1.2.1 的 Android 实现包含：

- `<file>.lock`：用 `FileChannel` 文件锁协调跨进程读写；进程内再叠一层协程 `Mutex`，避免同一进程自己跟自己冲突。
- `<file>.version`：JNI 把共享计数器映射到多个进程，用原子整数记录版本。
- `FileObserver(MOVED_TO)`：观察目标文件被临时文件替换的事件，提醒其他进程检查版本并刷新。

下面的精简片段对应这三个机制：

```kotlin
override val updateNotifications: Flow<Unit> =
    MulticastFileObserver.observe(file)

override suspend fun <T> lock(block: suspend () -> T): T =
    inMemoryMutex.withLock {
        FileOutputStream(lockFile).use { stream ->
            stream.channel.lock(0L, Long.MAX_VALUE, false).use {
                block()
            }
        }
    }

override suspend fun incrementAndGetVersion(): Int =
    withLazyCounter { it.incrementAndGetValue() }
```

实际源码在文件锁报告死锁错误时还会退避重试，共享读锁也有兼容处理；上面的精简代码只作示意，读真实实现以库为准。

读路径拿不到进程内 mutex 或共享文件锁时，仍可读取当前正式文件，但不会把这次无锁结果作为稳定缓存提交。后续再通过共享版本和文件通知校准缓存。这样，读取不必等待正在生成的 `.tmp` 文件，缓存也只会在稳定快照上更新。

### 写入顺序与版本递增

1.2.1 的 `DataStoreImpl.writeData()` 在持有协调锁和 `writeScope` 时，先递增共享版本，再把新对象写入临时文件。临时文件完成 `sync()` 后，`FileStorage` 才把它原子移动到目标文件；该移动会触发 `MOVED_TO` 通知。

版本先递增是刻意设计：如果先替换文件，随后进程在递增版本前退出，其他进程可能长时间认为缓存仍是最新。版本、锁与文件观察器要一起工作，单拿出任何一个机制都撑不起跨进程事务。

`updateData()` 的 transform 位于跨进程独占锁范围内，应保持短小、确定且无副作用；网络请求、长计算或另一把业务锁会延长所有进程的写等待。DataStore 的事务覆盖一个完整对象，多文件原子提交、字段级更新和历史版本回滚都超出它的能力。

`FileObserver(MOVED_TO)` 只在目标进程还有活跃的 `data` Flow 收集者时用来唤醒刷新；收集者数量回到零后，观察任务随之停止。下一次读取仍会比较共享版本，所以这种通知只是尽力唤醒，别当作必达的事件日志。

不要直接修改 `.preferences_pb`、`.lock`、`.version` 或 `.tmp`。文件锁属于协作式协议，绕过 DataStore 的直接文件写入会破坏版本和通知关系。

### 本地库与测试边界

1.2.1 的 `datastore-core-android` AAR 为 arm64-v8a、armeabi-v7a、x86 和 x86_64 打包了 `libdatastore_shared_counter.so`，Android 运行时加载失败会抛错。主机测试不在 Android 运行时里执行，可以用进程内 shadow counter 顶替；跨进程 `mmap` 的语义，还是要到模拟器或真机上验证。

所以，多进程路径至少要在模拟器或真机 instrumentation 测试里覆盖以下场景：

- 两个进程并发更新同一个 key。
- 写入进程在不同阶段被终止。
- 读取进程长期存活时能否看到新值。
- APK/AAB 经过 R8 处理和 ABI 拆分后，是否仍包含这一本地库。
- Direct Boot 与凭据解锁前后的文件位置是否符合预期。

DataStore 1.2.0 起增加了 Direct Boot 支持 API。Direct Boot 允许部分组件在用户解锁前访问特定存储；只有确需在这一阶段读取的数据才应放进 device-protected storage（设备保护存储区），并且要避开依赖用户凭据保护的敏感内容。

## 仍需保留 SP 时的规则

存量工程一次迁不完，我们可以先约束风险：

1. 不在主线程调用 `commit()`。
2. 不在 Activity 即将 stop、Service 命令收尾或 BroadcastReceiver 返回前集中 `apply()`。
3. 同一批 key 使用一个 Editor 和一次提交，减少整文件重写次数。
4. 不把列表、日志、埋点队列或不断增长的业务对象放进 SP。
5. 复制 `getStringSet()` 的结果后再修改，返回集合本身要保持原样。
6. 监控每个文件的字节数、key 数、写频率、慢 `fsync` 和组件收尾等待。
7. 跨进程数据停止使用 `MODE_MULTI_PROCESS`；选择 MultiProcess DataStore、Room + ContentProvider 或其他有明确一致性协议的方案。
8. 敏感状态要定义持久化失败时的处理，仅靠 `apply()` 的内存可见性是不够的。

拆分 SP 文件可以缩小单次序列化与解析的范围，也会增加首次打开任务和管理成本。加载执行器只有单线程，拆成大量小文件并不会带来并行加载；文件应按数据拥有者和访问阶段划分，避免按 key 随意分文件。

## DataStore、MMKV 与 Room 的选型

| 场景 | 优先评估 | 需要额外验证 |
| --- | --- | --- |
| 官方 Jetpack、协程、少量单进程配置 | DataStore | 首次初始化、全量序列化、错误处理 |
| 少量多进程配置 | MultiProcess DataStore | 文件锁竞争、本地库打包、进程终止 |
| 高频 KV（键值）读写，已有 MMKV 基础设施 | MMKV | 持久性、多进程、升级兼容、备份与安全 |
| 复杂查询、局部更新、事务、大集合 | Room | schema、索引、WAL（Write-Ahead Logging，预写式日志）、迁移 |
| 跨进程统一数据服务 | Room + ContentProvider 或专用 Binder 服务 | IPC（进程间通信）权限、并发、进程生命周期 |

MMKV 是用 `mmap` 与自定义编码格式的第三方键值存储库，在部分高频键值工作负载下可能优于 XML SP。`mmap` 路径仍会发生缺页、脏页回写和持久化操作，性能优势和掉电语义都要在目标设备上实测。选型时还要评估格式演进、加密配置、崩溃恢复和维护成本。

用 ContentProvider 包一层 SP，得到的只是统一入口，SP 整体 XML 写入和 `QueuedWork` 语义都保持原样。既然已经需要复杂的跨进程访问，底层数据模型也应一起调整。

## 给挂起写入添加正确的 Trace

DataStore 的更新是挂起调用，给它加 trace 时要处理线程切换的问题。同步 `Trace.beginSection()`/`endSection()` 要求在同一线程配对；协程可能在挂起后切换线程，所以普通的同步 trace 区间不要跨越 `DataStore.edit()` 调用。

下面的代码用异步 trace 区间记录一次可跨线程的 DataStore 更新：

```kotlin
private val nextTraceCookie = AtomicInteger()

suspend fun updateNightMode(enabled: Boolean) {
    val traceName = "DataStore.updateNightMode"
    val cookie = nextTraceCookie.incrementAndGet()
    Trace.beginAsyncSection(traceName, cookie)
    try {
        context.settingsDataStore.edit { prefs ->
            prefs[booleanPreferencesKey("night_mode")] = enabled
        }
    } finally {
        Trace.endAsyncSection(traceName, cookie)
    }
}
```

这里的 `Trace` 可以用 `androidx.tracing.Trace`；并发请求要使用不同的 cookie，也就是配对 begin/end 的那对整数标识。当前 `androidx.tracing` 版本若支持挂起函数 `traceAsync`，直接用它包装调用也可以。Trace 名称里不要出现用户值或其他敏感信息。

除了时长，建议记录成功、异常类型和调用场景计数。单次 DataStore 更新慢可能来自首次迁移、transform 执行过久、文件同步、跨进程锁竞争或设备 I/O，只有一个总 slice 还不能定位原因。

## 常见误区

### “`apply()` 已异步，不会引起 ANR”

`apply()` 的调用点通常很快返回，但 pending work 会在 Activity/Service 收尾时被 `waitToFinish()` 处理，BroadcastReceiver 的完成回执也可能排在它后面。

### “现代 Activity 在 `onPause()` 等待 SP”

Android 17 的现代 Activity 主路径在 `handleStopActivity()`。`handlePauseActivity()` 中的等待只服务于 pre-Honeycomb 兼容路径。

### “DataStore 不会重写整个文件”

DataStore 不支持部分更新。它会完整序列化当前对象到临时文件并替换目标文件，优势来自非阻塞 API、事务化更新、错误传播和一致性语义。

### “调用 `edit()` 后可以立即忽略结果”

DataStore `edit()` 是挂起函数。它成功返回表示更新完成；异常需要调用方处理。把它放进无人管理的协程作用域会失去失败信号，也可能在作用域取消时丢掉尚未完成的任务。

### “多进程 DataStore 只靠文件锁”

当前 Android 实现同时使用文件锁、共享版本计数器和文件移动通知。所有进程都必须遵守同一协议。

### “换成 MMKV 就不再有磁盘问题”

MMKV 改变编码和访问路径，但脏页持久化、设备抖动、数据损坏与多进程协调仍要处理。

## 小结

SP ANR 的关键链条可以压缩成一句话：

`apply()` 先更新内存并把整份 XML 写入延后；组件收尾时，框架又要求这些 pending work 完成，于是主线程可能执行写盘或等待写盘。

排查时，我们把首次加载等待、主线程写盘、latch 等待和 BroadcastReceiver 回执延迟分开识别。迁到 DataStore 后，线程阻塞和错误语义得到改善，全量序列化、首次初始化、文件同步与多进程锁竞争依然要测量。

Android 17 平台源码负责解释 SP；DataStore 行为应以 App 锁定的 AndroidX 版本为准。对新项目，少量配置优先 DataStore，关系数据与较大集合使用 Room；存量 SP 则按数据所有权分批迁移，并给失败、回滚和跨进程访问留下明确方案。

## 参考资料

- AOSP `frameworks/base/core/java/android/app/SharedPreferencesImpl.java`（`android-17.0.0_r1`）
- AOSP `frameworks/base/core/java/android/app/QueuedWork.java`（`android-17.0.0_r1`）
- AOSP `frameworks/base/core/java/android/app/ActivityThread.java`（`android-17.0.0_r1`）
- AOSP `frameworks/base/core/java/android/content/BroadcastReceiver.java`（`android-17.0.0_r1`）
- AOSP `frameworks/base/core/java/android/content/SharedPreferences.java`（`android-17.0.0_r1`）
- AOSP `frameworks/base/core/java/android/app/ContextImpl.java`（`android-17.0.0_r1`）
- [DataStore guide](https://developer.android.com/topic/libraries/architecture/datastore)
- [DataStore API](https://developer.android.com/reference/kotlin/androidx/datastore/core/DataStore)
- [DataStore release notes](https://developer.android.com/jetpack/androidx/releases/datastore)
- [SharedPreferencesMigration API](https://developer.android.com/reference/kotlin/androidx/datastore/migrations/SharedPreferencesMigration)
- [MultiProcessDataStoreFactory API](https://developer.android.com/reference/kotlin/androidx/datastore/core/MultiProcessDataStoreFactory)
- [AndroidX tracing async sections](https://developer.android.com/reference/kotlin/androidx/tracing/Trace)
- AndroidX DataStore 1.2.1 `DataStoreImpl.kt`、`FileStorage.kt`、`MultiProcessCoordinator.android.kt`、`MulticastFileObserver.android.kt`、`SharedCounter.android.kt`
- [今日头条 ANR 优化实践：告别 SharedPreference 等待](https://mp.weixin.qq.com/s/kfF83UmsGM5w43rDCH544g)
