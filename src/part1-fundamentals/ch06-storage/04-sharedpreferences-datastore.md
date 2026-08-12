---
title: "SharedPreferences 与 DataStore：I/O、ANR 与多进程一致性"
chapter: "6.4"
status: ready-for-review
applicable_versions: "Android 1.0 (API 1) - Android 17 (API 37)"
last_verified: "2026-07-01"
last_verified_against: "AOSP android-17.0.0_r1 SharedPreferencesImpl.java / QueuedWork.java / ActivityThread.java / BroadcastReceiver.java / SharedPreferences.java / ContextImpl.java; AndroidX DataStore core 1.2.1 source/AAR; historical audit notes referenced 1.1.7"
confidence: medium
sources:
  - type: blog
    path: "https://mp.weixin.qq.com/s/kfF83UmsGM5w43rDCH544g"
  - type: aosp
    path: "frameworks/base/core/java/android/app/SharedPreferencesImpl.java"
  - type: aosp
    path: "frameworks/base/core/java/android/app/QueuedWork.java"
  - type: aosp
    path: "frameworks/base/core/java/android/content/BroadcastReceiver.java"
  - type: aosp
    path: "frameworks/base/core/java/android/app/ActivityThread.java"
  - type: official
    path: "https://developer.android.com/topic/libraries/architecture/datastore"
  - type: official
    path: "https://developer.android.com/reference/kotlin/androidx/datastore/core/DataStore"
  - type: official
    path: "https://developer.android.com/jetpack/androidx/releases/datastore"
  - type: androidX
    path: "AndroidX DataStore 1.2.1 DataStoreImpl.kt / FileStorage.kt / MultiProcessCoordinator.android.kt / MulticastFileObserver.android.kt / SharedCounter.android.kt"
tags: [sharedpreferences, datastore, anr, io, storage, performance, queuedwork]
related_chapters: ["6.1", "6.3", "9.1", "9.2", "8.2", "4.5"]
section: "6.4"
pipeline_stage: "ready-for-review"
task6_state: "pending-verification"
task9_state: "reviewed"
last_idle_audit_at: "2026-08-04T18:35:51+08:00"
last_idle_audit_run_id: "20260804-183551-idle-audit-29d2feef"
task2b_state: "fixed"
last_consolidated_at: "2026-08-11"
consolidated_from:
  - "src/part1-fundamentals/ch06-storage/6.03-Android-17-SharedPreferencesImpl-ANR机制.md"
  - "src/part1-fundamentals/ch06-storage/6.1-androidx-datastore--ipc-源码级验证-draft.md"
---

# 6.4 SharedPreferences 与 DataStore：I/O、ANR 与多进程一致性

## `apply()` 返回后的写盘与主线程关系

SharedPreferences（下文简称 SP）适合少量、低频、单进程配置。它的问题不只在 XML 读写速度，还在 API 语义：

- 首次加载由后台线程执行，但调用方第一次读取可能在 `awaitLoadedLocked()` 等待。
- `apply()` 先更新内存并返回，磁盘结果无法反馈给调用方。
- Android 框架会在部分组件收尾点清空 `QueuedWork`，主线程可能执行尚未开始的写盘，也可能等待已经开始的写盘。
- 每次有效修改都要序列化当前整份 map，SP 不支持按 key 增量更新文件。
- 平台接口不支持可靠的跨进程一致性。

Android 17 的 `SharedPreferences` 接口文档已经明确建议：新的小型数据存储需求优先考虑 Jetpack DataStore，关系型数据和较大数据集使用 Room。

源码基线分为两个版本维度：

- 平台实现：Android 17 / API 37 / `android-17.0.0_r1`
- Jetpack 实现：DataStore 不属于 Android 17 平台源码；这里以 AndroidX DataStore 1.2.1 为准

手机升级到 Android 17 不会替 App 自动升级 DataStore，最终行为由应用依赖的 AndroidX 版本决定。

## SP 对象与首次加载

### 同一进程会缓存同一份 SP 实例

`ContextImpl` 使用静态的 `sSharedPrefsCache`，先按包名，再按文件路径缓存 `SharedPreferencesImpl`。同一进程中重复调用相同 Context/文件名，通常拿到同一个对象，不会为每次 `getSharedPreferences()` 重新创建加载任务。

这个缓存只解决进程内对象复用。不同进程有各自的内存 map，也没有一套由 SP 提供的可靠变更通知协议。`MODE_MULTI_PROCESS` 已废弃，Android 17 仍保留的代码只是根据文件变化尝试重新加载，不能提供事务和一致性保证。

### `startLoadFromDisk()` 异步，`getXxx()` 仍可能同步等待

下面的源码片段用于确认 Android 17 的加载执行器与线程名：

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

`corePoolSize=0`、`maximumPoolSize=1` 表示同一进程的 SP 加载任务会在单个工作线程上依次执行。Android 17 的稳定观察点是名为 `SharedPreferences` 的线程；旧版本或厂商修改版仍应以现场线程和调用栈为准。

对象构造后，`startLoadFromDisk()` 把 `loadFromDisk()` 交给该执行器。加载线程会处理 `.bak` 恢复、文件 `stat`、XML 解析，然后设置 `mLoaded` 并唤醒等待者。

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

`getString()`、`getInt()`、`contains()`、`getAll()`，甚至 `edit()` 都会先走这里。后台线程可能正在读盘，主线程则在 `mLock.wait()`。代码还会主动报告一次调用线程的 StrictMode 磁盘读取，即使文件 I/O 发生在另一条线程上。

首次等待通常被以下因素放大：

- XML 文件较大或包含大量 key。
- 同一进程同时首次打开多份 SP，而加载执行器只有一个工作线程。
- 冷启动阶段还有 dex、资源、数据库等 I/O 竞争。
- `/data` 正在 writeback、F2FS GC 或块设备延迟抖动。
- XML 解析或备份恢复失败，异常最终回到调用方。

“在 `Application` 中提前调用 `getSharedPreferences()`”只能提前创建对象并安排加载。若紧接着读取 key，仍可能进入等待。要降低首帧风险，需要把首次使用安排在有余量的阶段，并通过 Trace 验证加载是否在关键路径前完成。

## 从 `edit()` 到 `fsync()`：SP 写入的完整路径

### 第一步：`commitToMemory()` 修改内存状态

`apply()` 和 `commit()` 都先调用 `commitToMemory()`。它在锁内把 Editor 的修改合入 `mMap`，递增内存状态代数，记录受影响的 key 和监听器，并增加 `mDiskWritesInFlight`。

如果已有写盘正在使用旧 map，代码会复制一份 map 后再修改，避免在写盘序列化期间改变同一个对象。这里的“提交”只表示进程内状态已经变化，不等于文件已经持久化。

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

调用方看到的顺序是：内存已更新、写盘任务已安排、监听器收到内存变更，然后 `apply()` 返回。`awaitCommit` 留在 `QueuedWork.sFinishers` 中，直到写盘结束后由 `postWriteRunnable` 移除，或者被框架收尾逻辑取出执行。

`apply()` 没有返回值，调用方无法知道序列化、`fsync()` 或重命名是否失败。适用于重要安全状态或必须确认持久化的业务时，不能只凭“内存已经读到新值”判断写入成功。

### 第三步：`enqueueDiskWrite()` 决定在哪条线程写

`enqueueDiskWrite()` 把文件写入封装成 `writeToDiskRunnable`。Runnable 使用 `mWritingToDiskLock` 串行执行 `writeToFile()`，结束后递减 `mDiskWritesInFlight`，再运行 `postWriteRunnable`。

`commit()` 与 `apply()` 的关键差异如下：

| 维度 | `apply()` | `commit()` |
| --- | --- | --- |
| 返回 | 立即返回 `void` | 等待对应写盘结束，返回 `boolean` |
| 内存可见 | `commitToMemory()` 后立即可见 | 同样先更新内存 |
| 常规写盘安排 | 进入 `QueuedWork`，默认可延迟 100ms | 若当前写是唯一在途写，可由调用线程直接执行 |
| 已有写盘时 | 排队 | 同样排队，随后调用线程等待 latch |
| 监听器 | 写盘完成前即可通知 | 等待本次写盘后通知 |
| 错误信息 | 无磁盘结果 | 只有布尔结果，没有详细失败原因 |
| 生命周期收尾 | pending work/finisher 可能被框架等待 | 调用点已经同步等待 |

因此，“`commit()` 总在当前线程写”和“`apply()` 总在 `queued-work-looper` 写”都不严谨。`commit()` 可能排队再等待；`apply()` 的任务也可能被随后调用 `waitToFinish()` 的线程取走执行。

### 第四步：`writeToFile()` 重写整份 XML

一次有效写入大致经过以下步骤：

1. 检查内存代数与磁盘代数，确认是否需要写。
2. 若原文件存在且没有备份，把原文件重命名为 `.bak`。
3. 创建新的 XML 文件，把 `mapToWriteToDisk` 整体序列化。
4. 对文件描述符执行同步刷新。
5. 更新权限、时间戳和文件大小记录。
6. 成功后删除 `.bak`，更新磁盘代数并释放 `writtenToDiskLatch`。
7. 失败时删除不完整的新文件，保留备份供下次加载恢复。

这套备份协议降低了进程在写入中途退出时留下半份 XML 的风险，但不能把它描述成任意掉电条件下的绝对事务。源码没有在每次替换后同步父目录，文件系统、内核与存储设备仍参与持久性语义。

SP 没有按 key 更新磁盘文件的能力。只修改一个布尔值，也可能重写整份 map。文件大小、序列化成本、`fsync()` 延迟和前序队列长度共同决定耗时。

### 两个日志阈值只负责观测

Android 17 保留两个内部阈值：

- `SharedPreferencesImpl.MAX_FSYNC_DURATION_MILLIS = 256`：单次 `fsync` 超过 256ms 时输出累计直方图；每 1024 次同步也会输出。
- `QueuedWork.MAX_WAIT_TIME_MILLIS = 512`：`waitToFinish()` 超过 512ms 时输出等待直方图；每 1024 次等待也会输出。

这些阈值不会取消写盘，也不会阻止 ANR。它们没有面向普通 App 的 public 调参接口，不能把 256ms 或 512ms 当作系统超时线。

## `apply()` 如何进入组件收尾路径

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

`processPendingWork()` 先取走 `sWork` 并在当前调用线程逐个运行。若主线程调用 `waitToFinish()`，尚未开始的 SP 写盘就可能直接在主线程执行。随后它再运行 finisher；如果写盘已由后台线程取得，finisher 会在 `writtenToDiskLatch.await()` 等待。

`StrictMode.allowThreadDiskWrites()` 会临时放宽这一段的磁盘写策略，所以仅依赖 StrictMode 可能漏掉生命周期收尾阶段由主线程执行的写盘。

### Android 17 的调用点

`android-17.0.0_r1` 中需要区分四类路径：

- **现代 Activity**：`handleStopActivity()` 在 Activity 停止时调用 `QueuedWork.waitToFinish()`。
- **pre-Honeycomb Activity**：兼容路径仍在 `handlePauseActivity()` 调用；现代 App 不应把主路径写成 `onPause()`。
- **Service**：`handleServiceArgs()` 在命令处理后等待，`handleStopService()` 在销毁清理后等待。
- **BroadcastReceiver**：`PendingResult.finish()` 不直接调用 `waitToFinish()`。若发现 `QueuedWork` 仍有任务，它把 `sendFinished()` 排在队尾，AMS 收到完成回执的时间随之推迟。

BroadcastReceiver 的 Java `onReceive()` 返回，不代表系统已经收到完成回执。队列前面的 SP 写盘过慢，仍会提高 broadcast 超时风险。

组件的 ANR 窗口受组件类型、前后台状态和系统版本影响，不能用统一的“超过 5 秒必定 ANR”概括。框架等待点会把原本延后的持久化成本重新带回组件时限。

## 用 traces 与 Perfetto 定位 SP

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

A 类要关联 `SharedPreferences` 加载线程与 XML 解析；B 类要找后台写盘线程及 latch 持有时段；C 类的文件 I/O 已在主线程。混用这三类优化手段，容易只移动耗时而没有消除等待。

Service 栈可能以 `handleServiceArgs()` 或 `handleStopService()` 结尾。BroadcastReceiver 常见的是完成回执延后，未必出现主线程停在 `waitToFinish()` 的相同栈形态。

### Perfetto 中看什么

Perfetto 默认不会自动给每个 Java 方法生成名为 `QueuedWork` 的 slice。采集配置若没有 Java 调用栈或应用自定义 Trace，只搜索方法名可能一无所获。建议组合以下证据：

1. 主线程在组件收尾区间的 Running、Runnable、Sleeping 状态。
2. `SharedPreferences` 与 `queued-work-looper` 线程的调度和 CPU 活动。
3. ART/Java 调用栈采样中是否出现 `awaitLoadedLocked()`、`writeToFile()`、`processPendingWork()`。
4. 文件系统与块 I/O 事件是否和等待区间重合。
5. logcat 中 `SharedPreferencesImpl` 的慢 `fsync` 直方图、`QueuedWork` 的慢等待直方图。
6. App 自己记录的 SP 文件名、key 数、文件字节数、在途写次数和调用场景；不要记录敏感值。

只看到主线程处于 futex wait 还不够。Java monitor、`CountDownLatch`、Binder 和许多其他同步原语都可能落到 futex，需要调用栈确定等待对象。

## DataStore 的异步模型

### 非阻塞不等于写入立刻完成

DataStore 的 `data` 是 `Flow<T>`，`edit()`/`updateData()` 是挂起 API。默认工厂作用域使用 `Dispatchers.IO + SupervisorJob()`，磁盘 I/O 和更新任务在该作用域中执行。调用方线程不会像 SP `commit()` 那样同步做文件 I/O，但调用方协程会挂起，直到更新完成或抛出异常。

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

`setNightMode()` 返回时，这次更新已经经过 DataStore 的串行更新与持久化路径。若写入失败，异常会回到挂起调用方。调用者需要决定重试、提示用户或保留旧状态，不能在 `launch` 后立即把业务操作标记为永久成功。

官方 API 对 DataStore 的承诺包括线程安全、非阻塞和事务化更新。读取不会被写入锁长期阻塞，但第一次收集仍需要完成初始化、迁移和首次读盘；初始化失败会通过 Flow 或更新调用传播。

### DataStore 仍然全量序列化当前对象

DataStore 不支持字段级磁盘更新。官方 API 文档明确说明：任意字段改变后，整个对象都会被序列化并持久化。Preferences DataStore 把键值集合编码为 protobuf；Proto DataStore 使用应用定义的 protobuf schema。两者都不适合不断增长的大数据集。

AndroidX DataStore 1.2.1 的 `FileStorage` 写入路径是：

1. 在更新序列中获得当前数据。
2. 执行 transform，得到不可变的新值。
3. 在 `writeScope` 中递增协调器版本。
4. 将新值完整序列化到 `<file>.tmp`。
5. 对临时文件执行 `FileDescriptor.sync()`。
6. `writeScope` 的写入代码结束后，`FileStorage` 把临时文件原子移动到目标路径。
7. 整个 `writeScope` 成功返回后，写入 actor 才唤醒等待该更新的调用方。

源码仍留有“同步父目录”的待办注释，因此不应把这一实现描述成所有掉电窗口下都不会回退。DataStore 提供的 API 一致性和错误传播显著强于 SP，但存储硬件与文件系统的持久性边界仍存在。

### Preferences 与 Proto 怎么选

| 需求 | 建议 |
| --- | --- |
| 少量、无固定 schema 的键值配置 | Preferences DataStore |
| 有明确字段、枚举、默认值和版本演进 | Proto DataStore |
| 关系查询、局部更新、索引、分页、大集合 | Room |
| 缓存，可丢失且需要容量淘汰 | 专用缓存方案 |

Proto DataStore 的 schema 更利于审查和演进，但 protobuf 不能自动解决业务迁移。字段编号不能复用，删除字段应保留编号；加密、备份排除和敏感数据生命周期也要由应用设计。

### 单例是文件级约束

同一进程、同一路径同时存在多个活跃 DataStore 实例会破坏功能，并在读写时触发 `IllegalStateException`。顶层 `by preferencesDataStore` 属性是一种方便的单例组织方式，但创建多个指向同一文件的 delegate 仍然错误。

自建 `DataStoreFactory` 时，scope 应与应用级数据拥有者同寿命。不要在 Activity、Fragment 或一次请求中重复创建实例，也不要让 `produceFile` 每次返回不同路径。

多进程场景中的“每个进程一个实例”仍然指向同一个 canonical file。所有进程必须使用 `MultiProcessDataStoreFactory`，不能把单进程和多进程工厂混用于同一文件；transform 返回的数据对象也必须保持不可变，否则进程内缓存的 hash 校验会失去意义。

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

`ReplaceFileCorruptionHandler` 只在 Serializer 抛出 `CorruptionException` 时参与恢复，不能吞掉权限、空间不足等任意 I/O 错误。恢复值也要满足业务安全边界。

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

迁移任务在 DataStore 首次可访问之前执行。成功持久化新数据后，cleanup 会从旧 SP 删除已迁移 key；使用 Context/文件名构造器且旧 SP 已空时，还会尝试删除旧文件。若迁移或持久化失败，后续访问可能再次执行相关步骤，所以迁移函数必须幂等。

还要注意以下边界：

- 内置 Preferences 迁移只支持 SP 的 boolean、float、int、long、string 和 string set。
- 指定 `keysToMigrate` 后只能访问这些 key；省略时迁移全部受支持 key。
- DataStore 中已经存在的同名 Preferences key 不会被旧 SP 反复覆盖。
- 迁移尚未完成时，`data.first()` 和更新调用都会等待初始化。
- 迁移完成后继续让旧代码写 SP，会形成两份来源；DataStore 不负责持续双向同步。

### 迁移按数据所有权推进

一次可靠迁移可以分成四步：

1. **盘点**：列出每个 SP 文件的拥有模块、key 类型、读写频率、跨进程使用、备份策略和回滚要求。
2. **确定唯一写入方**：为每组配置指定一个数据接口，禁止业务代码绕过它直接拿 SP。
3. **迁移并观测**：先迁高风险写入和大文件；记录迁移失败、初始化耗时、DataStore 文件大小和更新延迟。
4. **删除旧路径**：确认活跃版本和独立进程都切换后，移除旧读写。需要支持版本回退时，要提前定义旧版本如何处理已删除的 SP key。

没有通用的“SP 超过 50KB 就必须迁移”阈值。文件大小只是一个维度，还要看 key 数、启动位置、写频率、设备分布和等待分位数。以线上 Trace 与 ANR 聚类确定优先级更可靠。

## MultiProcess DataStore 的实现边界

### 所有进程必须使用多进程工厂

从 DataStore 1.1.0 起，`MultiProcessDataStoreFactory` 提供正式的多进程支持。若 App 进程和独立 Service 进程共享一个文件，两边都应使用多进程工厂，并指向完全相同的路径。单进程 DataStore 与多进程 DataStore 混用同一文件不受支持。

每个进程仍应只保留一个指向该文件的活跃实例。配置对象必须不可变，迁移也必须幂等。

### 1.2.1 的三类协调机制

AndroidX DataStore 1.2.1 的 Android 实现包含：

- `<file>.lock`：使用 `FileChannel` 文件锁协调跨进程读写；进程内还有协程 `Mutex`，避免同进程锁冲突。
- `<file>.version`：JNI 将共享计数器映射到多个进程，用原子整数记录版本。
- `FileObserver(MOVED_TO)`：观察目标文件被临时文件替换的事件，提醒其他进程检查版本并刷新。

下面的精简片段用于展示三个锚点：

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

生产源码还包含文件锁死锁错误的退避重试与共享读锁兼容处理，不能用上面的精简代码替换库实现。

读路径拿不到进程内 mutex 或共享文件锁时，仍可读取当前正式文件，但不会把这次无锁结果作为稳定缓存提交。后续由共享版本和文件通知重新校准。这个设计让读取不必等待正在生成的 `.tmp` 文件，同时保证缓存只有在稳定快照上更新。

### 写入顺序要按源码理解

1.2.1 的 `DataStoreImpl.writeData()` 在持有协调锁和 `writeScope` 时，先递增共享版本，再把新对象写入临时文件。临时文件完成 `sync()` 后，`FileStorage` 才把它原子移动到目标文件；该移动会触发 `MOVED_TO` 通知。

版本先递增是刻意设计：如果先替换文件、随后在递增版本前进程退出，其他进程可能长时间认为缓存仍是最新。版本、锁与文件观察器需要一起工作，不能把某一个机制单独视为跨进程事务。

`updateData()` 的 transform 位于跨进程独占锁范围内。它应保持短小、确定且无副作用；网络请求、长计算或另一把业务锁会延长所有进程的写等待。DataStore 的事务边界覆盖一个完整对象，不提供多文件原子提交、字段级更新或历史版本回滚。

`FileObserver(MOVED_TO)` 只在目标进程存在活跃 `data` Flow collector 时用于唤醒刷新；collector 数量回到零后，观察任务会停止。下一次读取仍会比较共享版本，因此通知不是不可丢失的事件日志。

不要直接修改 `.preferences_pb`、`.lock`、`.version` 或 `.tmp`。文件锁属于协作式协议，绕过 DataStore 的直接文件写入会破坏版本和通知关系。

### native library 与测试边界

1.2.1 的 `datastore-core-android` AAR 为 arm64-v8a、armeabi-v7a、x86 和 x86_64 打包 `libdatastore_shared_counter.so`。Android 运行时加载失败会抛错；非 Dalvik 的主机测试可使用进程内 shadow counter，但它不能验证跨进程 `mmap` 语义。

因此，多进程路径应至少在 emulator 或真机 instrumentation test 中覆盖：

- 两个进程并发更新同一个 key。
- 写入进程在不同阶段被终止。
- 读取进程长期存活时能否看到新值。
- APK/AAB 经 R8 与 ABI 拆分后是否仍包含 native library。
- Direct Boot 与凭据解锁前后的文件位置是否符合预期。

DataStore 1.2.0 起增加了 Direct Boot 支持 API。只有确需解锁前读取的数据才应放入 device-protected storage，且其中不应包含依赖用户凭据保护的敏感内容。

## 仍需保留 SP 时的规则

存量工程不可能一次迁完，可以先约束风险：

1. 不在主线程调用 `commit()`。
2. 不在 Activity 即将 stop、Service 命令收尾或 BroadcastReceiver 返回前集中 `apply()`。
3. 同一批 key 使用一个 Editor 和一次提交，减少整文件重写次数。
4. 不把列表、日志、埋点队列或不断增长的业务对象放进 SP。
5. 复制 `getStringSet()` 的结果后再修改，不能原地改变返回集合。
6. 监控每个文件的字节数、key 数、写频率、慢 `fsync` 和组件收尾等待。
7. 跨进程数据停止使用 `MODE_MULTI_PROCESS`；选择 MultiProcess DataStore、Room + ContentProvider 或其他有明确一致性协议的方案。
8. 敏感状态要定义持久化失败处理，不能依赖 `apply()` 的内存可见性。

拆分 SP 文件可以缩小单次序列化与解析范围，也会增加首次打开任务和管理成本。Android 17 的加载执行器是单线程，拆成大量小文件并不会带来并行加载。应按数据拥有者和访问阶段划分，避免按 key 随意分文件。

## DataStore、MMKV 与 Room 的选型

| 场景 | 优先评估 | 需要额外验证 |
| --- | --- | --- |
| 官方 Jetpack、协程、少量单进程配置 | DataStore | 首次初始化、全量序列化、错误处理 |
| 少量多进程配置 | MultiProcess DataStore | 文件锁竞争、native packaging、进程终止 |
| 高频 KV，已有 MMKV 基础设施 | MMKV | 持久性、多进程、升级兼容、备份与安全 |
| 复杂查询、局部更新、事务、大集合 | Room | schema、索引、WAL、迁移 |
| 跨进程统一数据服务 | Room + ContentProvider 或专用 Binder 服务 | IPC 权限、并发、进程生命周期 |

MMKV 使用 `mmap` 与自定义编码路径，部分高频 KV workload 下可能优于 XML SP。`mmap` 仍会发生 page fault、脏页回写和持久化操作，性能优势与掉电语义需要在目标设备上测试。它是第三方依赖，选型时还要评估格式演进、加密配置、崩溃恢复和维护成本。

用 ContentProvider 包一层 SP 只能增加统一入口，不能改变 SP 整体 XML 写入和 `QueuedWork` 语义。若已经需要复杂跨进程访问，底层数据模型也应一起调整。

## 给挂起写入添加正确的 Trace

同步 `Trace.beginSection()`/`endSection()` 要求在同一线程配对。协程可能在挂起后切换线程，不能把普通同步 section 跨在 `DataStore.edit()` 两侧。

下面的代码使用 async section 记录一次可跨线程的 DataStore 更新：

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

这里的 `Trace` 可使用 `androidx.tracing.Trace`，并保证并发请求使用不同 cookie。支持挂起版 `traceAsync` 的 tracing 版本也可以直接包装调用。Trace 名称不要包含用户值或其他敏感信息。

除了时长，建议记录成功、异常类型和调用场景计数。单次 DataStore 更新慢可能来自首次迁移、transform 太重、文件同步、跨进程锁竞争或设备 I/O，只有一个总 slice 还不能定位原因。

## 常见误区

### “`apply()` 已异步，不会引起 ANR”

`apply()` 的调用点通常很快返回，但 pending work 会在 Activity/Service 收尾时被 `waitToFinish()` 处理，BroadcastReceiver 的完成回执也可能排在它后面。

### “现代 Activity 在 `onPause()` 等待 SP”

Android 17 的现代 Activity 主路径在 `handleStopActivity()`。`handlePauseActivity()` 中的等待只服务于 pre-Honeycomb 兼容路径。

### “DataStore 不会重写整个文件”

DataStore 不支持部分更新。它会完整序列化当前对象到临时文件并替换目标文件，优势来自非阻塞 API、事务化更新、错误传播和一致性语义。

### “调用 `edit()` 后可以立即忽略结果”

DataStore `edit()` 是挂起函数。它成功返回表示更新完成；异常需要调用方处理。把它放进无人管理的 scope 会失去失败信号，也可能在 scope 取消时丢掉尚未完成的任务。

### “多进程 DataStore 只靠文件锁”

当前 Android 实现同时使用文件锁、共享版本计数器和文件移动通知。所有进程都必须遵守同一协议。

### “换成 MMKV 就不再有磁盘问题”

MMKV 改变编码和访问路径，但脏页持久化、设备抖动、数据损坏与多进程协调仍要处理。

## 小结

SP ANR 的关键链条可以压缩成一句话：

`apply()` 先更新内存并把整份 XML 写入延后；组件收尾时，框架又要求这些 pending work 完成，于是主线程可能执行写盘或等待写盘。

排查时分别识别首次加载等待、主线程写盘、latch 等待和 BroadcastReceiver 回执延迟。迁移到 DataStore 后，线程阻塞和错误语义得到改善，但全量序列化、首次初始化、文件同步与多进程锁竞争依然需要测量。

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
